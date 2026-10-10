# plugin.py
"""SEAL (Shen et al., 2024): the data-selection half of the method, as a client-side plugin.

SEAL learns a per-sample softmax selector by bilevel optimization on top of a safety-aligned LLM and
fine-tunes on the samples it ranks highest. That training is offline, centralized and needs two model
copies; a plugin does not own the training loop. What the library can host is the selection such a
selector produces, given the trained selector as a resource.
"""
from __future__ import annotations

import math

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


def top_percent_keep(scores: list[float], p: float) -> list[int]:
    """Indices of the ceil(p * n) largest scores, ties in the given order, at least one kept.

    SEAL truncates by rank and percent (Section 3.3 S3). The paper does not say how to round p * n or
    how to break ties, so both rules are fixed here and used by SealTopPercent.
    """
    n = len(scores)
    if n == 0:
        return []
    k = max(1, min(n, int(math.ceil(p * n))))
    order = sorted(range(n), key=lambda i: (-float(scores[i]), i))
    return sorted(order[:k])


class SealTopPercent(GuardPlugin):
    """SEAL's data selection (Shen et al., 2024) on the samples a client is about to train on.

    SEAL learns a per-sample selector sigma(omega) = softmax(omega) on top of a safety-aligned LLM by
    bilevel optimization over a safe reference set D_safe and the fine-tuning set D, keeps the top p% of
    D by sigma_i(omega_K) and fine-tunes on that subset (Section 3.3, steps S1-S4). The selector training
    is offline, centralized and needs two model copies; a plugin does not own the training loop, so it
    comes in as a resource and this plugin runs the selection itself.

    Resource `selector_scores`: dict mapping a sample hash as the library records it for the announced
    samples (DataView.manifest[i].hash, the SHA-256 of the sample text) to the trained selector's score
    sigma_i(omega_K) for that sample. It is the output of S1-S2, keyed by sample identity because the
    selector is bound to the dataset version, not to the model it is applied to (Section 4.4, Table 3).

    Implemented: the ranking and truncation half of S3. Every announced sample is looked up in
    `selector_scores`, the samples are ranked by score, the ones below the top p% are proposed as a
    `mask_samples` action for this round, and the implicit cut score is reported in the evidence.
    Deviations: the paper ranks the whole of D once, offline, and cuts at p% of D; here the cut is p% of
    one client's announced samples in one round, so it is not a global top p% and a client may keep
    different absolute samples across rounds. A sample here is a client's local data item, identified by
    the library's hash of its text, not a position in the model owner's D. The selector is taken as given:
    SEAL's own contribution, the bilevel training of omega, is not implemented (see below).
    Not implemented: the initial alignment (S1); the selector training (S2), that is the paired sampling
    of one safe and one fine-tuning sample, the penalty-mixed theta step (Eq. 4), the auxiliary model
    (Eq. 6) and its loss-gap rank update (Eq. 5), and the memory-efficient rank update (Eq. 8); the
    safety loss on D_safe. Those are the offline work that produces the resource, and the library has no
    stage outside the round, no second model, no way for a plugin to step parameters, and no sample
    identity at loss time.
    Open in the paper and chosen here: p defaults to 0.8 (Section 4.2; Section 3.3 gives no default);
    ceil(p * n) samples are kept, at least one, and ties are broken in the announced order; a sample
    whose hash is not in `selector_scores` cannot be ranked and is dropped, and how many were dropped is
    reported; samples with identical text share a hash, hence a score and a mask decision; no score
    threshold is used, because softmax scores are never zero and the paper always cuts by rank; the
    selector's training hyper-parameters (alpha, beta, gamma, epochs, batch 64) play no part here, since
    S2 is outside the library.
    Cost: O(n log n) to rank n announced samples plus one dict lookup per sample; no model passes, no
    tensors and no messages. The method's own cost is outside the library, where the selector is trained:
    Table 3 reports 28.3 GB / 14 h with PYTHIA-2.8B and 34.1 GB / 20 h with PHI-3.
    """
    name, at, version = "seal_top_percent", Stage.CLIENT_PRE_TRAIN, "1"
    needs = frozenset({"data"})
    resources = frozenset({"selector_scores"})
    acts = frozenset({"mask_samples"})

    def __init__(self, p: float = 0.8):
        if not 0.0 < p <= 1.0:
            raise ValueError("p is the fraction of samples kept, in (0, 1]")
        self.p = float(p)

    def run(self, ctx):
        table = ctx.resource("selector_scores")
        manifest = ctx.data.manifest
        scores, missing = [], 0
        for record in manifest:
            value = table.get(record.hash)
            if value is None:
                missing += 1
                scores.append(float("-inf"))
            else:
                scores.append(float(value))
        keep = set(top_percent_keep(scores, self.p))
        mask = [record.hash for i, record in enumerate(manifest) if i not in keep]
        evidence = {"p": self.p, "announced": len(manifest), "kept": len(keep),
                    "masked": len(mask), "missing_scores": missing}
        ranked = [scores[i] for i in sorted(keep) if scores[i] != float("-inf")]
        if ranked:
            evidence["cut_score"] = min(ranked)
        return ctx.findings(
            features={r.hash: {"selector_score": s} for r, s in zip(manifest, scores) if s != float("-inf")},
            evidence=evidence,
            proposals={"mask": mask} if mask else {},
        )
