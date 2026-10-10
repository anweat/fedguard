# plugin.py
"""SEAL's data selection (Shen et al., 2024) as a client-side plugin.

SEAL learns a per-sample softmax selector sigma(omega) on top of a safety-aligned LLM by bilevel
optimization, then ranks the fine-tuning set D with it, keeps the top p% as D_top and fine-tunes on that
subset (Sections 3.1-3.3, steps S1-S4). S1-S3 are one-time offline work of the model owner, not a
federated round; fedguard has no stage outside a round and no plugin-owned training loop, so the trained
selector enters as a resource (rule 3) and this plugin runs the decision S3 describes.
"""
from __future__ import annotations

import math

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


def top_percent_keep(scores: list[float], p: float) -> list[int]:
    """Indices of the ceil(p * n) largest scores, in increasing index order; at least one when n > 0.

    This is SEAL's top-p% cut (Section 3.3 S3). The paper gives neither a rounding rule for p * n nor a
    tie rule; both are fixed here (round up; among equal scores the earlier index first) and are the
    rules SealTopPercent relies on.
    """
    n = len(scores)
    if n == 0:
        return []
    k = max(1, min(n, math.ceil(p * n)))
    order = sorted(range(n), key=lambda i: (-float(scores[i]), i))
    return sorted(order[:k])


class SealTopPercent(GuardPlugin):
    """SEAL's data selection (Shen et al., 2024): keep the samples the trained selector ranks highest.

    SEAL defines a data selector sigma(omega) = softmax(omega) over the fine-tuning set D (Section 3.1),
    trains it by bilevel optimization together with a safety-aligned LLM and a safe reference set D_safe
    (S1-S2), then uses sigma_i(omega_K) to rank each data z_i in D, selects the top p% into D_top and
    fine-tunes on D_top (S3-S4, Section 3.3). S1-S3 are one-time offline work of the model owner. In a
    federated deployment the samples live on the clients, so the decision is applied per client and round.

    Resource `selector_scores`: dict {sample hash -> sigma_i(omega_K)}, the trained selector's score of a
    sample, keyed by the SHA-256 of the sample text that DataView.manifest records. It is the output of
    S1-S2 and is produced outside this library, one table per dataset version (Section 4.4 shows the
    selector travels across models but stays bound to the dataset).

    Implemented: S3's decision. For the samples a client announces for the round, look each score up in
    `selector_scores`, rank the scored ones by score, keep the ceil(p * n_scored) highest (at least one)
    and propose every other announced sample as a `mask_samples` action, so local training runs on the
    kept subset. Sample identity is the manifest hash; only hashes, scores and counts are reported, and
    no sample text leaves the client.
    Deviations: the paper ranks the whole of D once, offline, and D_top is fixed before fine-tuning; here
    the cut is p% of the scored samples one client announces in one round, so it is not a global top p%
    of D, and a client that announces another set later gets another subset. The interface forces this:
    no stage sees more than one client's data. The score sigma_i(omega_K) is a resource, so the scoring
    itself (the softmax forward of step 11) happens outside. Sample identity is the text hash, not the
    position in D the paper ranks by; identical texts share a hash, hence a score and a decision. The
    paper's S4 fine-tunes on D_top with no loss weighting, and this plugin only removes samples, so the
    sigma-weighting of Eq. (4) is not reproduced (it belongs to S2, outside).
    Not implemented: S1 initial alignment, and S2, the method's core: omega initialization, the auxiliary
    model clone, the penalty relaxation, the paired sampling of D_safe and D, the length-normalized NLL
    the selector sees, the Eq. (4) penalty-mixed theta step, the Eq. (6) auxiliary-model step, the Eq. (5)
    loss-gap rank update and the Eq. (8) memory-efficient rank update; also S4 (ordinary fine-tuning) and
    the optional SEAL+SafeInstr variant. S1-S2 are a centralized offline bilevel training loop that
    updates the LLM, and the library offers no stage outside a round, no second parameter set and no
    control of a training loop.
    Open in the paper and chosen here: p defaults to 0.8, the paper's comparison setting (Section 4.2;
    Section 3.3 gives no default, Section 4.5 uses 0.9 and Table 3 0.2 - pass those to the constructor);
    p * n_scored rounds up and at least one sample is kept; ties are broken in announced order; a sample
    whose hash is not in `selector_scores` is not among the candidates and is masked (it is not in the
    dataset the selector was trained on, so it is not in D_top), and if no announced sample has a score
    the plugin proposes nothing and says so in evidence; the cut is re-derived every round, with no
    cross-round memory, because the paper fixes D_top once and does not define a changed announced set;
    no score threshold is used, since softmax scores are never zero (Section 3.1) and the paper's own
    rule is rank plus percentage; the selector's score is reported as a `feature` (higher = safer) and
    not as `Findings.scores`, whose convention is higher = more risky.
    Cost: O(n log n) to rank n announced samples and one dict lookup per sample; no model passes, no
    tensors, no messages. The method's real cost is S2, outside the library: Table 3 reports 28.3 GB /
    14 h with PYTHIA-2.8B and 34.1 GB / 20 h with PHI-3 for selector training, against 27.8-27.9 GB /
    3-13 h for the fine-tuning it precedes.
    """
    name, at, version = "seal_top_percent", Stage.CLIENT_PRE_TRAIN, "1"
    needs = frozenset({"data"})
    resources = frozenset({"selector_scores"})
    acts = frozenset({"mask_samples"})

    def __init__(self, p: float = 0.8):
        if not 0.0 < float(p) <= 1.0:
            raise ValueError("p is the fraction of scored samples kept, in (0, 1]")
        self.p = float(p)

    def run(self, ctx):
        table, manifest = ctx.resource("selector_scores"), ctx.data.manifest
        scored = [(i, float(table[r.hash])) for i, r in enumerate(manifest) if r.hash in table]
        if not scored:
            return ctx.findings(evidence={"announced": len(manifest), "scored": 0,
                                          "skipped": "no announced sample has a selector score"})
        keep = {scored[j][0] for j in top_percent_keep([s for _, s in scored], self.p)}
        mask = [r.hash for i, r in enumerate(manifest) if i not in keep]
        evidence = {"p": self.p, "announced": len(manifest), "scored": len(scored),
                    "unscored": len(manifest) - len(scored), "kept": len(keep), "masked": len(mask)}
        if len(keep) < len(scored):
            evidence["cut_score"] = min(s for i, s in scored if i in keep)
        features = {r.hash: {"kept": 1.0 if i in keep else 0.0,
                             **({"selector_score": float(table[r.hash])} if r.hash in table else {})}
                    for i, r in enumerate(manifest)}
        return ctx.findings(features=features, evidence=evidence, proposals={"mask": mask} if mask else {})
