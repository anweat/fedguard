# plugin.py
"""Influence-based defense for a stream of labelled samples: a slab feasibility filter over the round
data, then an influence score per remaining sample whose rolling mean is the trigger for the
influence-minimizing sample edit of the paper.

Mounted on the client at CLIENT_PRE_TRAIN, the only stage where a plugin sees the round samples before
local training and where the library lets it propose mask_samples or edit_samples.
"""
from __future__ import annotations

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.ops import geometry, sampling


def influence_norms(reference, gradients, damping=1e-6):
    """Norms of A^-1 g for every row g of `gradients`, A the damped empirical Fisher of `reference`.

    A = (1 / n) R^T R + lam * I is p x p, with p the number of trained parameters (1e5 and more for
    LoRA), and is never formed. The Woodbury identity gives
        A^-1 g = (g - R^T (lam * n * I + R R^T)^-1 (R g)) / lam,
    an n x n solve and one matrix-vector product per row. lam is `damping` times the mean squared norm
    of the reference rows, so the default is scale free, and it is floored so that the solve is defined.
    """
    R, G = reference.double(), gradients.double()
    n = R.shape[0]
    lam = max(float(damping) * float((R * R).sum(dim=1).mean()), 1e-12)
    M = geometry.gram_matrix(R)
    K = M + lam * n * torch.eye(n, dtype=M.dtype)
    alpha = torch.linalg.solve(K, (G @ R.T).T)
    return (G - alpha.T @ R).norm(dim=1) / lam


class InfluenceDefense(GuardPlugin):
    """Slab filtering plus influence-score screening of a stream (the method behind arXiv:2104.13230).

    Resource `clean_reference`: {"samples": Sequence, "labels": Sequence}. The clean pre-train set D_pre
    of the paper, in the client sample format, one hashable class tag per sample. The class centroids
    and slab thresholds of Eq. (10), and the reference gradients behind the curvature of Eq. (7), are
    computed from it inside the run.

    Implemented: step 1, the class centroids mu_y and the per-class threshold s_y of Eq. (10); step 2,
    the membership test |<x - mu_y, mu_y - mu_-y>| <= s_y per announced sample, samples outside it
    proposed for `mask_samples` (the paper skips the update for them) and given no influence; step 4,
    the per-sample loss gradient of Eq. (11) through `ModelHandle.per_sample_gradients` over the LoRA
    parameters; steps 3 and 5, the curvature of Eq. (7) and the influence vector of Eq. (6), computed
    in the row space from the reference gradients with the damped empirical Fisher standing in for the
    exact Hessian (`influence_norms`); step 6, the Euclidean norm with which the paper scalarizes the
    influence vector; step 7, the rolling mean of the last w_inf influences, kept across rounds in
    ctx.state, as the threshold. Scores, thresholds and the samples the trigger selects are reported
    per sample hash.

    Deviations: the paper is centralized online learning on d-dimensional feature vectors with a
    logistic model; here a sample is the client local data and the trained parameters are the LoRA
    factors of a language model, so influences are taken over the LoRA parameters and p is far above d.
    The feature vector x of the paper has no accessor in `DataView`; the slab runs on pooled hidden
    states from `ModelHandle.hidden`, which move with the model, while the paper x is fixed. The exact
    Hessian of Eq. (7)/(14) needs second derivatives that no operator exposes and a p x p matrix that
    does not fit, so the damped empirical Fisher stands in for it and its damping is a choice. H is
    recomputed at every round on the model the client received. The paper consumes one sample per
    online gradient step; here the round is the unit, all announced samples are processed in manifest
    order at CLIENT_PRE_TRAIN, and the host then trains. A sample rejected by the slab is removed from
    this round by `mask_samples`, where the paper leaves theta_t = theta_{t-1} for that arrival.

    Not implemented: the exact Hessian of Eq. (7)/(14), for which the damped empirical Fisher stands in
    (see Deviations); step 8, the influence-minimizing perturbation x* = argmin_x Inf(x) of Eq. (12)-(13);
    and with it step 9, the acceptance rule Inf(x_t) >= Inf(x*_t). No operator gives the gradient of a
    parameter-gradient with respect to the input, and a perturbation in feature space has no realization
    in a text sample that `edit_samples` could carry. The trigger is therefore reported and never acted
    on; the slab mask is the only intervention this plugin makes.

    Open in the paper and chosen here: s_y has neither a value nor a rule in the paper, it is the
    largest statistic the reference samples of that class take; w_inf has no value, default 20; an empty
    window means no threshold yet (the paper does not define the cold start); a sample rejected by the
    slab does not enter the window (the paper computes the influence only in the accepted branch); the
    damping of H^-1 defaults to 1e-6 times the mean squared reference gradient norm; H is estimated on
    D_pre, not on the stream (the paper writes D and never says which set it means); the label coding
    (the paper mixes y in {-1, +1} and {0, 1}) does not arise because a label only picks a centroid
    here; `max_samples` is None, the paper subsamples nothing.

    Cost: one forward pass per sample for the hidden states (reference and announced), one backward
    pass per sample for the per-sample gradients (reference and accepted), and an n x n solve plus two
    n x p matrix products per accepted sample. The reference passes repeat every round.
    """
    name, at, version = "influence_defense", Stage.CLIENT_PRE_TRAIN, "1"
    needs, acts = frozenset({"data", "model_handle"}), frozenset({"mask_samples"})
    resources = frozenset({"clean_reference"})

    def __init__(self, w_inf=20, layer=-1, pool="mean", group="lora", label_of=None, damping=1e-6, max_samples=None):
        self.w_inf, self.layer, self.pool, self.group = w_inf, layer, pool, group
        self.label_of, self.damping, self.max_samples = label_of, damping, max_samples

    def run(self, ctx):
        data = ctx.data
        samples, manifest = list(data.samples()), data.manifest
        idx = sampling.subsample(len(samples), self.max_samples, ctx.rng)
        labels = [self.label_of(samples[i]) for i in idx] if self.label_of is not None else None

        features, masked = {}, []
        if labels is not None and all(l is not None for l in labels):
            stats, masked, slab = self._slab(ctx, samples, idx, labels)
            for i, v in stats.items():
                features.setdefault(manifest[i].hash, {})["slab"] = v
        else:
            slab = {"slab_skipped": "no label_of callable, so the class centroids of Eq. (10) cannot be formed"}
        accepted = [i for i in idx if manifest[i].hash not in set(masked)]

        values, thresholds, flagged = self._influence(ctx, samples, accepted)
        for i, v in thresholds.items():
            features.setdefault(manifest[i].hash, {})["threshold"] = v

        return ctx.findings(
            scores={manifest[i].hash: values[i] for i in values},
            features=features,
            proposals={"mask": masked} if masked else {},
            evidence={**slab, "announced": len(idx), "accepted": len(accepted), "out_of_slab": len(masked),
                      "flagged_for_editing": [manifest[i].hash for i in flagged],
                      "editing_not_implemented": "Eq. (12)-(13) need the gradient of Inf with respect to the sample, which the library does not expose"})

    def _slab(self, ctx, samples, idx, labels):
        ref = ctx.resource("clean_reference")
        ref_samples, ref_labels = list(ref.get("samples") or []), list(ref.get("labels") or [])
        if not ref_samples or len(ref_labels) != len(ref_samples):
            return {}, [], {"slab_skipped": "the clean reference is empty or its labels do not match its samples"}
        classes = sorted(set(ref_labels), key=str)
        if len(classes) != 2:
            return {}, [], {"slab_skipped": "slab is defined for two classes, and the reference has {:d}".format(len(classes))}
        if any(l not in classes for l in labels):
            return {}, [], {"slab_skipped": "an announced sample carries a label the clean reference does not have"}
        R = ctx.model_handle.hidden(ref_samples, self.layer, self.pool).double()
        X = ctx.model_handle.hidden([samples[i] for i in idx], self.layer, self.pool).double()
        mu = {c: R[[j for j, l in enumerate(ref_labels) if l == c]].mean(dim=0) for c in classes}
        other = {classes[0]: classes[1], classes[1]: classes[0]}
        s = {}
        for c in classes:
            own = R[[j for j, l in enumerate(ref_labels) if l == c]]
            s[c] = float(((own - mu[c]) @ (mu[c] - mu[other[c]])).abs().max())
        stats, masked = {}, []
        for pos, c in enumerate(labels):
            v = float(((X[pos] - mu[c]) @ (mu[c] - mu[other[c]])).abs())
            stats[idx[pos]] = v
            if v > s[c]:
                masked.append(ctx.data.manifest[idx[pos]].hash)
        return stats, masked, {"reference_classes": [str(c) for c in classes],
                               "slab_threshold": {str(c): s[c] for c in classes}}

    def _influence(self, ctx, samples, accepted):
        if not accepted:
            return {}, {}, []
        ref = ctx.resource("clean_reference")
        R = ctx.model_handle.per_sample_gradients(list(ref["samples"]), self.group).double()
        if R.shape[0] == 0:
            return {}, {}, []
        G = ctx.model_handle.per_sample_gradients([samples[i] for i in accepted], self.group).double()
        norms = influence_norms(R, G, self.damping)
        window = ctx.state.setdefault("influence_window", [])
        keep = max(1, int(self.w_inf))
        values, thresholds, flagged = {}, {}, []
        for pos, i in enumerate(accepted):
            v = float(norms[pos])
            values[i] = v
            if window:
                tau = sum(window) / len(window)
                thresholds[i] = tau
                if v >= tau:
                    flagged.append(i)
            window.append(v)
            del window[:-keep]
        return values, thresholds, flagged
