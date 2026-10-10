# plugin.py
"""BayBFed (Al-Huthaifi et al.): a Beta-Bernoulli posterior per client plus CRP-Jensen cluster
matching, mounted on the server at SERVER_AGGREGATE.

The plugin reads this round of uploads and the global LoRA the round was broadcast with, keeps the
Beta-process and cluster state across rounds in ctx.state, and returns the clients to exclude plus
equal aggregation weights for the rest. The class docstring says what is implemented, where the port
deviates from the printed equations, and which choices the paper left open.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import geometry, states

_LOG_2PI = 0.5 * math.log(2.0 * math.pi)
_TINY = 1e-12
_LOG_FLOOR = -700.0


def log_normal(x, mean=0.0, sd=1.0):
    """Log density of N(mean, sd) at every entry of x; sd may broadcast and is floored away from 0."""
    s = torch.as_tensor(sd, dtype=x.dtype).abs().clamp_min(_TINY)
    z = (x - torch.as_tensor(mean, dtype=x.dtype)) / s
    return -0.5 * z * z - torch.log(s) - _LOG_2PI


def normal_density(x, mean=0.0, sd=1.0):
    """Normal density at every entry of x; the log is floored so that no entry is exactly zero."""
    return torch.exp(log_normal(x, mean, sd).clamp_min(_LOG_FLOOR))


def jensen_shannon(p, q):
    """Jensen-Shannon divergence in nats between non-negative vectors, each normalized to sum 1.

    m = (p + q) / 2 and 0 log 0 = 0. An (n, l) input gives (n,) out, a 1-D input gives a float.
    """
    scalar = p.dim() == 1
    p, q = p.double().clamp_min(0.0), q.double().clamp_min(0.0)
    if scalar:
        p, q = p[None], q[None]
    p = p / p.sum(dim=-1, keepdim=True).clamp_min(_TINY)
    q = q / q.sum(dim=-1, keepdim=True).clamp_min(_TINY)
    m = 0.5 * (p + q)
    lm = torch.log(m.clamp_min(_TINY))
    a = torch.where(p > 0, p * (torch.log(p.clamp_min(_TINY)) - lm), torch.zeros_like(p)).sum(dim=-1)
    b = torch.where(q > 0, q * (torch.log(q.clamp_min(_TINY)) - lm), torch.zeros_like(q)).sum(dim=-1)
    out = 0.5 * (a + b)
    return float(out[0]) if scalar else out


def round_filter(values):
    """Alg. 2 on one round of Max_JD values: (keep flags, one reason per client).

    A client is kept only when its value is strictly below the round mean and occurs once.
    """
    mean = sum(values) / len(values)
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    keep, why = [], []
    for v in values:
        reasons = []
        if not v < mean:
            reasons.append("Max_JD >= the round mean")
        if counts[v] > 1:
            reasons.append("Max_JD repeated in the round")
        keep.append(not reasons)
        why.append("; ".join(reasons))
    return keep, why


class BayBFed(GuardPlugin):
    """BayBFed: a Beta-Bernoulli posterior per client plus CRP-Jensen cluster matching.

    The server scores every uploaded LoRA with a per-client Beta-process posterior, matches the score
    against the clusters formed so far with a Jensen-Shannon divergence, and excludes the clients that
    the two filter rules of Alg. 2 reject.

    Implemented: the baseline Beta-process statistics mu_p and sigma_p of the flattened global LoRA the
    round was broadcast with (in round 0 that is G^0); the hierarchical prior, one concentration c_i
    drawn for a client from Poisson(c) when it is first seen, and the per-client base-measure vector
    H_i updated by Eq. (1); the cosine shift of Eq. (2); the measurement error of Eq. (3); the p
    distribution of Eq. (4) steps (i) and (ii); one q distribution of Eq. (5) per existing cluster plus
    the virtual new cluster of Sect. 4.3; the Jensen-Shannon divergence of Eq. (12) with m = (p + q)/2;
    Max_i^JD as the largest divergence of that set; the CRP-Jensen assignment and the cluster mean and
    scale updates of Eq. (6)-(7); the filter of Alg. 2; equal aggregation weights for the kept clients
    (Appendix A).

    Deviations: W_i and G are full model weights in the paper. Here W_i is the flattened uploaded LoRA
    state and G the flattened LoRA state the round was broadcast with, both in sorted-key order, so l is
    the number of adapter entries and every statistic lives in factor space; the frozen base weights are
    the same for all clients and cannot carry a per-client backdoor. Eq. (4) step (iii) is not applied.
    Read as a third normal density N(p; 1, W_bar_up) at the values of p, its argument range sits far in
    the left tail of that normal and the transform is nearly linear, which washes the score out:
    measured on the round of the test, the one amplified upload of eight then has the smallest Max_JD of
    all instead of the largest, so the filter of Alg. 2 would not reject it. Eq. (4) is therefore used
    as p = N(W_up; mu_p, sigma_p) + H, and the only role left for a third step, turning p into a
    distribution, is taken by the normalization inside the divergence. Eq. (2) adds a cosine (a number
    in [-1, 1]) to raw weight coordinates, which assumes weights of order 1; a real LoRA factor is much
    smaller than that and the paper does not normalize it, so on such an adapter the shift can swamp the
    signal. The shift is applied as printed.

    Not implemented: the random measure A ~ BP(c, H) itself, which the paper draws before training;
    every later step uses only its (mu_p, sigma_p) summary, so it is not materialized. The list
    semantics of W_filtered in Alg. 2 (a client can be appended twice) is replaced by set semantics.

    Open in the paper and chosen here: p and q are read as length-l vectors of densities over the factor
    coordinates and are normalized to sum 1 by the divergence; m = (p + q)/2; logarithms are natural
    (Eq. (12) leaves m undefined, and the filter only compares against a round mean, so the base of the
    logarithm cancels). H_i is a length-l vector: Eq. (4) adds it to p elementwise and the storage
    analysis of the paper calls it l-dimensional, so the update of Eq. (1) is applied coordinate-wise
    with the coefficients as printed, and H_i^0 is mu_p in every coordinate, the location of the base
    measure H = N(mu_p, sigma_p). The printed coefficients of Eq. (1) shrink the data term as c_i grows
    by l every round, so H_i stays near zero; that is kept as printed. mu_0 and sigma_0^2 have no value
    in the paper; mu_p and sigma_p are used, which is what a CRP prior implies. tau_k and n_k have no
    update rule in the paper; tau_k = 1 / scale^2 of the cluster and n_k = the number of updates
    assigned so far, incremented on assignment. Eq. (7) is variance-like as printed (an inverse
    precision plus a variance), so its square root is used as the scale that Eq. (5) expects. sigma_w
    is d * cos of Eq. (3) and sigma_w^2 its square, which resolves the conflict with Alg. 1 line 7. The
    cluster assignment takes the smallest JD over the existing clusters and the virtual new cluster: the
    paper says the decision follows Max_i^JD without saying in which direction, and its intuition (a
    large JD means a new cluster) conflicts with the nearest-table meaning of a CRP; the maximum is what
    the filter uses. Every client is assigned and updates the clusters, kept or not, as Alg. 1 does, but
    the scores are computed against the cluster structure as it stood at the start of the round, so the
    round decision does not depend on the order in which the uploads arrive (Requirement II); the
    cluster state does, because Eq. (6)-(7) are sequential. The filter keeps a client only when its
    Max_i^JD is strictly below the round mean and occurs once: Alg. 2 lists two independent append
    conditions, and under a reading that treats them as alternatives a unique value could never be
    excluded and the mean rule would be inert, so both conditions are treated as necessary. The mean
    rule also removes benign clients that sit marginally above the round mean: in a four-round synthetic
    run with one of eight uploads amplified, one benign client is excluded next to the amplified one
    from round 1 on, which the paper does not discuss. Duplicates are exact float equality, which the
    paper requires and gives no tolerance for. With fewer than two uploads, or with no broadcast base,
    the plugin reports and proposes nothing: Alg. 1 assumes n clients per round and does not define the
    case.

    Cost: no model passes and no resources. Per round O(n * (n_oc + 1) * l) for the divergences and the
    same order again for the assignment; O(n * l) memory for the round and O(clients * l) for the
    persistent H_i, which dominates on a real adapter. l is the number of LoRA factor entries.
    """
    name, at, version = "baybfed", Stage.SERVER_AGGREGATE, "1"
    needs = frozenset({"uploads", "aggregate"})
    acts = frozenset({"select_and_weight"})

    def __init__(self, c=5.0, mu_0=None, sigma_0=None):
        """c: baseline concentration of the paper. mu_0, sigma_0: new-cluster prior; None uses mu_p, sigma_p."""
        self.c = float(c)
        self.mu_0 = None if mu_0 is None else float(mu_0)
        self.sigma_0 = None if sigma_0 is None else float(sigma_0)

    def run(self, ctx):
        up, agg, st = ctx.uploads, ctx.aggregate, ctx.state
        cids, base = up.clients, agg.base
        if base is None or len(cids) < 2:
            return ctx.findings(evidence={"skipped": "needs the round base and at least two uploads"})
        base_vec = states.flatten(base).double()
        if "mu_p" not in st:
            st["mu_p"] = float(base_vec.mean())
            st["sigma_p"] = float((base_vec - st["mu_p"]).pow(2).mean().sqrt())
        mu_p = float(st["mu_p"])
        sigma_p = max(float(st["sigma_p"]), _TINY)
        mu_0 = mu_p if self.mu_0 is None else self.mu_0
        sigma_0 = sigma_p if self.sigma_0 is None else max(abs(self.sigma_0), _TINY)
        dim = base_vec.numel()

        w = torch.stack([states.flatten(up.state(c)) for c in cids]).double()
        cos = geometry.cosine_to(w, base_vec)
        w_up = w + cos[:, None]
        dist = geometry.distance_to(w, base_vec)
        sigma_w = dist * cos

        conc, h = st.setdefault("conc", {}), st.setdefault("h", {})
        for c in cids:
            if c not in conc:
                conc[c] = max(1.0, float(ctx.rng.poisson(self.c)))
                h[c] = torch.full((dim,), mu_p, dtype=torch.float64)
        c_prior = torch.tensor([conc[c] for c in cids], dtype=torch.float64)
        h_now = (c_prior / (c_prior + dim))[:, None] * torch.stack([h[c] for c in cids]) + w / (c_prior * dim)[:, None]
        for c in cids:
            conc[c] = conc[c] + dim
        for i, c in enumerate(cids):
            h[c] = h_now[i].clone()
        p = normal_density(w_up, mu_p, sigma_p) + h_now

        clusters = st.setdefault("clusters", [])
        clusters_before = len(clusters)
        scale_new = (sigma_0 ** 2 + sigma_w ** 2).sqrt()
        best = torch.full((len(cids),), float("-inf"), dtype=torch.float64)
        for cl in clusters:
            best = torch.maximum(best, jensen_shannon(p, normal_density(w_up, cl["mu"], cl["scale"])))
        best = torch.maximum(best, jensen_shannon(p, normal_density(w_up, mu_0, scale_new[:, None])))
        scores = {c: float(best[i]) for i, c in enumerate(cids)}

        keep, why = round_filter(best.tolist())
        excluded = {c for c, k in zip(cids, keep) if not k}
        kept = [c for c in cids if c not in excluded]

        tau_0 = 1.0 / sigma_0 ** 2
        assigned = {}
        for i, c in enumerate(cids):
            params = [(cl["mu"], cl["scale"]) for cl in clusters]
            params.append((mu_0, float((sigma_0 ** 2 + float(sigma_w[i]) ** 2) ** 0.5)))
            jds = [jensen_shannon(p[i], normal_density(w_up[i], mu, sc)) for mu, sc in params]
            k = min(range(len(jds)), key=lambda j: (jds[j], j))
            assigned[c] = float(k)
            if k == len(clusters):
                sc = max(float((sigma_0 ** 2 + float(sigma_w[i]) ** 2) ** 0.5), _TINY)
                clusters.append({"mu": mu_0, "scale": sc, "n": 1})
            else:
                cl = clusters[k]
                weight = cl["n"] / cl["scale"] ** 2
                cl["mu"] = (float(w_up[i].mean()) * weight + mu_0 * tau_0) / (weight + tau_0)
                cl["scale"] = max(math.sqrt(1.0 / (weight + tau_0) + float(sigma_w[i]) ** 2), _TINY)
                cl["n"] = cl["n"] + 1

        features = {c: {"cosine": float(cos[i]), "distance": float(dist[i]),
                        "measurement_error": float(sigma_w[i]), "max_jd": float(best[i]),
                        "cluster": assigned[c]} for i, c in enumerate(cids)}
        return ctx.findings(scores=scores, features=features,
                            decision=Decision(weights={c: 1.0 for c in kept}, excluded=excluded,
                                              flags={c: r for c, r in zip(cids, why) if r}),
                            evidence={"mu_p": mu_p, "sigma_p": sigma_p, "mean_max_jd": float(best.mean()),
                                      "clusters_before": clusters_before, "clusters_after": len(clusters),
                                      "kept": sorted(kept)})
