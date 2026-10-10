"""Basic protective and detection plugins shipped as defaults."""
from __future__ import annotations

import math
import statistics

from fedguard.ops.robust import robust_z
from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage


class ReportGuard(GuardPlugin):
    """Bound the aggregation weight a client can claim through self-reported sample counts.

    weight_i = min(reported_i, applicable caps), where the caps are
      - protocol cap: spec.extra["max_num_examples"] (or cap_abs), agreed before training;
      - pinned cap: the client's first report (later rounds may not claim more);
      - peer cap: cap_ratio * median(reported), only with >= min_clients reports, since with
        two clients the median is the mean of the honest and the inflated value.
    """
    name, at, version = "report_guard", Stage.SERVER_AGGREGATE, "2"
    needs, acts = frozenset({"reports"}), frozenset({"select_and_weight"})

    def __init__(self, key: str = "num_examples", cap_ratio: float = 2.0, cap_abs: float | None = None,
                 min_clients: int = 3, pin_first: bool = True):
        self.key, self.cap_ratio, self.cap_abs = key, cap_ratio, cap_abs
        self.min_clients, self.pin_first = min_clients, pin_first

    def setup(self, spec):
        if self.cap_abs is None:
            self.cap_abs = spec.extra.get("max_num_examples")

    def run(self, ctx):
        claimed = ctx.reports.values(self.key)
        if not claimed:
            return ctx.findings(evidence={"skipped": f"no clients reported {self.key!r}"})
        pinned = ctx.state.setdefault("pinned", {})
        peer_cap = None
        if len(claimed) >= self.min_clients:
            peer_cap = self.cap_ratio * statistics.median(claimed.values())
        weights, flags, caps = {}, {}, {}
        for cid, v in claimed.items():
            limits = {"protocol": self.cap_abs, "peer": peer_cap,
                      "pinned": pinned.get(cid) if self.pin_first else None}
            limits = {k: c for k, c in limits.items() if c is not None}
            w = min([v, *limits.values()])
            weights[cid] = w
            caps[cid] = limits
            if w < v:
                binding = min(limits, key=limits.get)
                flags[cid] = f"{self.key} {v:g} capped to {w:g} ({binding})"
            pinned.setdefault(cid, w)
        ref = self.cap_abs or peer_cap or statistics.median(claimed.values())
        return ctx.findings(scores={c: v / ref for c, v in claimed.items()},
                            decision=Decision(weights=weights, flags=flags),
                            evidence={"caps": caps})


class RobustOutlier(GuardPlugin):
    """|robust z| of one upstream feature. Cross-sectional when enough clients take part this round,
    otherwise against the client's own history; no score when neither reference is usable.
    """
    name, at, version = "robust_outlier", Stage.SERVER_RECEIVE, "1"
    needs = frozenset({"history"})

    def __init__(self, feature: str = "effect_stats.inc_norm", min_clients: int = 5, min_history: int = 3,
                 name: str | None = None):
        self.feature, self.min_clients, self.min_history = feature, min_clients, min_history
        if name:
            self.name = name

    def run(self, ctx):
        values = ctx.upstream_feature(self.feature)
        z = robust_z(values, min_n=self.min_clients)
        if z is not None:
            return ctx.findings(scores={c: abs(v) for c, v in z.items()}, evidence={"reference": "cross_section"})
        scores, refs = {}, {}
        for cid, v in values.items():
            past = [feats[self.feature] for _, feats in ctx.history.rounds(cid) if self.feature in feats]
            past = [p for p in past if math.isfinite(p)]
            if len(past) < self.min_history or not math.isfinite(v):
                refs[cid] = "insufficient"
                continue
            med = statistics.median(past)
            mad = statistics.median(abs(p - med) for p in past) * 1.4826 or 1e-12
            scores[cid] = abs(v - med) / mad
            refs[cid] = "history"
        return ctx.findings(scores=scores, evidence={"reference": refs})
