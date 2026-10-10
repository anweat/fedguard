"""Client side, on the adapter itself: the global LoRA a client received, and its local result before
upload. The adapter scan and the update projection of TriShield.

As everywhere in fedguard.methods: every class names its paper, says which steps are implemented, what
deviates, and which choices the paper left open; none has been checked against the authors' code or
reproduced numerically. The step-by-step extractions they were written from are in
`survey/harvest/2026-10-08/opsread/<key>.md`.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.methods.shared import _A
from fedguard.ops import states, update


class ReceivedAdapterScan(GuardPlugin):
    """TriShield, parameter artifact detection (PAD): scan the adapter a client was sent for rows planted
    to memorize data, and reinitialize them before training.

    A row of a lora_A matrix is flagged when its variance is below tau_var or its correlation with
    another row of the same matrix is above tau_corr. Flagged rows are redrawn (Kaiming normal, as the
    paper states) through `transform_received`.
    Not implemented: the paper also resets a bias term of B, which PEFT LoRA does not have, and its other
    two layers (optimizer pre-warming, projection of the update; the latter is UpdateSubspaceProjection).
    """
    name, at, version = "received_adapter_scan", Stage.CLIENT_PRE_TRAIN, "1"
    needs, acts = frozenset({"received_model"}), frozenset({"transform_received"})

    def __init__(self, tau_var: float = 1e-4, tau_corr: float = 0.95):
        self.tau_var, self.tau_corr = tau_var, tau_corr

    def run(self, ctx):
        state = ctx.received_model.state()
        gen = torch.Generator().manual_seed(int(ctx.rng.integers(2**31)))
        new, feats, flagged_total = dict(state), {}, 0
        for key in sorted(k for k in state if k.endswith(_A)):
            W = state[key].double()
            var = W.var(dim=1, unbiased=False)
            centered = W - W.mean(dim=1, keepdim=True)
            norm = centered.norm(dim=1, keepdim=True)
            corr = (centered / norm.clamp_min(1e-300)) @ (centered / norm.clamp_min(1e-300)).T
            corr.fill_diagonal_(0)
            flag = (var < self.tau_var) | (corr.abs().max(dim=1).values > self.tau_corr)
            feats[key] = {"min_row_variance": float(var.min()), "max_row_correlation": float(corr.abs().max()),
                          "flagged_rows": float(flag.sum())}
            if flag.any():
                fresh = torch.randn(W.shape, generator=gen, dtype=torch.float64) * math.sqrt(2.0 / W.shape[1])
                new[key] = torch.where(flag[:, None], fresh, W).to(state[key].dtype)
                flagged_total += int(flag.sum())
        return ctx.findings(features=feats, scores={k: f["flagged_rows"] for k, f in feats.items()},
                            proposals={"received": new} if flagged_total else {}, evidence={"flagged_rows": flagged_total})


class UpdateSubspaceProjection(GuardPlugin):
    """TriShield, zero-utility-loss orthogonal projection (ZUOP): keep only the part of the local update
    that lies in the subspace spanned by task gradients on public data.

    Per-sample gradients of the LoRA parameters on the auxiliary samples form the columns of G; U_k are
    its top-k left singular vectors, k = min(rank_fraction * rank(G), n - 1); the update is replaced by
    U_k U_k^T update, in factor space, through `transform_update`.
    Resource `aux_samples`: public, unlabelled samples from a domain close to the private data (the
    paper uses 32 and recommends 200 to 500).
    Open in the paper and chosen here: gradients are taken at the trained local model (the paper gives
    three different descriptions of the point); n in the formula for k is the number of auxiliary samples;
    the paper also describes a projection of the product B A, which is not implemented.
    Cost: one forward and one backward pass per auxiliary sample, every round.
    """
    name, at, version = "update_subspace_projection", Stage.CLIENT_POST_TRAIN, "1"
    needs, acts = frozenset({"local_update", "model_handle"}), frozenset({"transform_update"})
    resources = frozenset({"aux_samples"})

    def __init__(self, rank_fraction: float = 0.8, group: str = "lora"):
        self.rank_fraction, self.group = rank_fraction, group

    def run(self, ctx):
        lu, handle = ctx.local_update, ctx.model_handle
        aux = list(ctx.resource("aux_samples"))
        local, ref = lu.state(), lu.reference()
        layout = handle.layout(self.group)
        keys = [k for k, _ in layout]
        missing = [k for k in keys if k not in local]
        if missing:
            raise LookupError(f"the model's parameter names do not match the LoRA state: {missing[:2]}")
        with handle.lora(local):
            G = handle.per_sample_gradients(aux, self.group).double()        # (n, p)
        U, S, _ = torch.linalg.svd(G.T, full_matrices=False)                 # columns of G.T are the samples
        rank = int((S > S.max() * 1e-10).sum()) if S.numel() and S.max() > 0 else 0
        k = max(1, min(int(self.rank_fraction * rank), len(aux) - 1)) if rank else 0
        if k == 0:
            return ctx.findings(evidence={"skipped": "the auxiliary gradients span nothing"})
        Uk = U[:, :k]
        d = states.flatten(states.delta(local, ref), keys)
        proj = update.project_onto(d, Uk.T)
        new = dict(local)
        new.update(states.add({key: ref[key] for key in keys}, states.unflatten(proj, {key: ref[key] for key in keys}, keys)))
        kept = float(proj.norm() / d.norm().clamp_min(1e-300))
        return ctx.findings(features={"self": {"kept_norm_fraction": kept, "subspace_rank": float(k)}},
                            proposals={"transformed": {ctx.participants[0]: new}})
