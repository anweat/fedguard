"""Feature-only plugins (no scores, no decisions): effect-space and factor-space statistics on uploads."""
from __future__ import annotations

import math
import statistics

import torch

from fedguard.ops.lowrank import gram, kappa
from fedguard.ops.geometry import cross_section
from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class EffectStats(GuardPlugin):
    """Direction A features on each client's round increment B_iA_i - B_gA_g (rank <= 2r).

    Per client:
      inc_norm      norm of the whole-model increment
      mean_cos      mean cosine to each other client (whole model)
      cos_rest      cosine to the mean of the other clients (whole model)
      mod_cos_rest  median over LoRA modules of the per-module cos_rest; less dominated by the
                    few modules with the largest increments than the whole-model cosine
      top_sv_share  median over modules of sigma_1^2 / sum sigma^2
      kappa         (include_kappa=True only) median over modules of ||B||·||A|| / ||BA|| on the
                    cumulative factors. P1 showed it is dominated by the shared global factors.
    """
    name, at, version = "effect_stats", Stage.SERVER_RECEIVE, "2"
    needs = frozenset({"uploads"})

    def __init__(self, include_kappa: bool = False):
        self.include_kappa = include_kappa

    def run(self, ctx):
        up = ctx.uploads
        cids = up.clients
        G = torch.zeros(len(cids), len(cids), dtype=torch.float64)
        share = {c: [] for c in cids}
        kap = {c: [] for c in cids}
        mod_cos = {c: [] for c in cids}
        for mod in up.modules:
            incs = [up.increment(c, mod).to(torch.float64) for c in cids]
            Gm = gram(incs)
            G += Gm
            _, _, rest_m = cross_section(Gm)
            for i, (c, inc) in enumerate(zip(cids, incs)):
                mod_cos[c].append(rest_m[i])
                sv2 = inc.singular_values() ** 2
                total = float(sv2.sum())
                share[c].append(float(sv2.max()) / total if total > 0 else math.nan)
                if self.include_kappa:
                    A, B = up.factors(c, mod)
                    kap[c].append(kappa(B, A))
        norms, mean_cos, cos_rest = cross_section(G)
        features = {}
        for i, c in enumerate(cids):
            f = {"inc_norm": norms[i], "mean_cos": mean_cos[i], "cos_rest": cos_rest[i],
                 "mod_cos_rest": _median_finite(mod_cos[c]),
                 "top_sv_share": _median_finite(share[c])}
            if self.include_kappa:
                f["kappa"] = statistics.median(kap[c]) if kap[c] else math.nan
            features[c] = f
        return ctx.findings(features=features, evidence={"clients": cids, "gram": G.tolist()})


def _median_finite(xs: list[float]) -> float:
    xs = [x for x in xs if math.isfinite(x)]
    return statistics.median(xs) if xs else math.nan


class FactorStats(GuardPlugin):
    """Baseline features on flattened factor deltas (A_i - A_g, B_i - B_g), as classic defenses see them.

    mod_cos_rest mirrors EffectStats: per-module cos_rest of the factor delta, median over modules.
    """
    name, at, version = "factor_stats", Stage.SERVER_RECEIVE, "2"
    needs = frozenset({"uploads"})

    def run(self, ctx):
        up = ctx.uploads
        cids = up.clients
        X = torch.stack([up.factor_delta(c).double() for c in cids]) if cids else torch.zeros(0, 0)
        norms, mean_cos, cos_rest = cross_section(X @ X.T)
        dA2 = {c: 0.0 for c in cids}
        dB2 = {c: 0.0 for c in cids}
        mod_cos = {c: [] for c in cids}
        for m in up.modules:
            A0, B0 = up.base_factors(m)
            deltas = []
            for c in cids:
                A, B = up.factors(c, m)
                dA, dB = (A - A0).double().flatten(), (B - B0).double().flatten()
                dA2[c] += float(dA @ dA)
                dB2[c] += float(dB @ dB)
                deltas.append(torch.cat([dA, dB]))
            Xm = torch.stack(deltas)
            _, _, rest_m = cross_section(Xm @ Xm.T)
            for i, c in enumerate(cids):
                mod_cos[c].append(rest_m[i])
        features = {c: {"delta_norm": norms[i], "dA_norm": math.sqrt(dA2[c]), "dB_norm": math.sqrt(dB2[c]),
                        "mean_cos": mean_cos[i], "cos_rest": cos_rest[i], "mod_cos_rest": _median_finite(mod_cos[c])}
                    for i, c in enumerate(cids)}
        return ctx.findings(features=features)
