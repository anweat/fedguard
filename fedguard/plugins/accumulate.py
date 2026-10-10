"""Cross-round evidence accumulation (SERVER_AGGREGATE): per-client CUSUM over one-sided standardized views."""
from __future__ import annotations

import math

from fedguard.ops.sequential import cusum_step, one_sided_z, reference_z
from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage

# (upstream feature, sign): +1 flags large values, -1 flags small values
DEFAULT_VIEWS = (("effect_stats.inc_norm", +1), ("effect_stats.cos_rest", -1),
                 ("compliance_probe.compliance_gain", +1))


class EvidenceAccumulator(GuardPlugin):
    """Accumulate each view's evidence per client across the rounds it takes part in.

    Each round, a view's values are standardized one-sidedly, against `reference[feature][round] =
    (center, scale)` when given (calibrated benign reference), otherwise across the round's participants
    (skipped when fewer than `min_clients` take part). The z feeds S <- max(0, S + z - k).
    With `thresholds[feature] = h`, a client is confirmed on that view the first round S > h.

    Per participating client: z.<feature>, cusum.<feature>, and (with thresholds) the score
    max over views of S / h, so a score above 1 means confirmed. Evidence lists every confirmed client
    with the round of first confirmation per view. This plugin only accumulates; acting on it is
    another plugin's job. Views missing upstream (e.g. no probe mounted) are skipped.
    """
    name, at, version = "evidence_accumulator", Stage.SERVER_AGGREGATE, "1"

    def __init__(self, views=DEFAULT_VIEWS, k: float = 0.5, cap: float | None = None, warmup: int = 2,
                 min_clients: int = 5, thresholds: dict[str, float] | None = None,
                 reference: dict[str, dict] | None = None, name: str | None = None):
        self.views, self.k, self.cap, self.warmup, self.min_clients = tuple(views), k, cap, warmup, min_clients
        self.thresholds = dict(thresholds or {})
        self.reference = {f: {int(r): tuple(v) for r, v in rounds.items()} for f, rounds in (reference or {}).items()}
        if name:
            self.name = name

    def _z(self, ctx, feature: str, sign: int) -> dict[str, float] | None:
        try:
            values = ctx.upstream_feature(feature)
        except LookupError:
            return None
        values = {c: float(v) for c, v in values.items() if isinstance(v, (int, float)) and math.isfinite(v)}
        ref = self.reference.get(feature, {}).get(ctx.round)
        if ref is not None:
            return reference_z(values, sign, *ref)
        return one_sided_z(values, sign, self.min_clients)

    def run(self, ctx):
        clients = ctx.state.setdefault("clients", {})
        if ctx.round < self.warmup:
            return ctx.findings(evidence={"skipped": "warm-up round"})
        features: dict[str, dict[str, float]] = {}
        used = []
        for feature, sign in self.views:
            z = self._z(ctx, feature, sign)
            if z is None:
                continue
            used.append(feature)
            h = self.thresholds.get(feature)
            for cid, zv in z.items():
                st = clients.setdefault(cid, {}).setdefault(feature, {"s": 0.0, "n": 0, "first": None})
                st["s"] = cusum_step(st["s"], zv, self.k, self.cap)
                st["n"] += 1
                if h is not None and st["first"] is None and st["s"] > h:
                    st["first"] = ctx.round
                features.setdefault(cid, {}).update({f"z.{feature}": zv, f"cusum.{feature}": st["s"]})
        scores = {}
        for cid in features:
            ratios = [clients[cid][f]["s"] / self.thresholds[f] for f in used if f in self.thresholds and f in clients[cid]]
            scores[cid] = max(ratios) if ratios else max(clients[cid][f]["s"] for f in used if f in clients[cid])
        confirmed = {cid: {f: st["first"] for f, st in views.items() if st["first"] is not None}
                     for cid, views in clients.items()}
        return ctx.findings(features=features, scores=scores,
                            evidence={"views": used, "confirmed": {c: v for c, v in confirmed.items() if v}})
