# plugin.py
"""BayBFed as one server-side fedguard plugin; the class notes list what is implemented, what the
paper leaves open and what was chosen here."""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import density, geometry


def normal_density(x: torch.Tensor, mean: float, sd: float) -> torch.Tensor:
    """Density of a normal law at every entry of x. A one-point Gaussian KDE is exactly that, so the
    kernel comes from fedguard.ops.density."""
    return density.gaussian_kde(torch.tensor([float(mean)]), x, bandwidth=max(float(sd), 1e-12))


def jensen_shannon(p: torch.Tensor, q: torch.Tensor) -> float:
    """JSD(p || q) in nats: both vectors are read as distributions over the coordinates, so they are
    normalized before m = (p + q) / 2; the divergence then comes from the identity
    JSD = H(m) - (H(p) + H(q)) / 2. A vector with no mass at all is read as uniform."""
    p, q = p.double().clamp_min(0), q.double().clamp_min(0)
    ps, qs = float(p.sum()), float(q.sum())
    p = p / ps if ps > 0 else torch.full_like(p, 1.0 / p.numel())
    q = q / qs if qs > 0 else torch.full_like(q, 1.0 / q.numel())
    m = 0.5 * (p + q)
    return max(0.0, density.shannon_entropy(m) - 0.5 * density.shannon_entropy(p)
               - 0.5 * density.shannon_entropy(q))


class BayBFed(GuardPlugin):
    """BayBFed (Bayesian backdoor defense for federated learning): the server scores every upload with a
    hierarchical Beta-Bernoulli posterior and a CRP-Jensen divergence against the round's clusters, and
    removes the clients whose score collides before the host aggregates.

    Implemented: the baseline base measure read off the initial global model (mu_p, sigma_p and the
    baseline density vector); the per-client hierarchical Beta prior (c_i a Poisson(c) draw, c = 5) with
    the posterior recursion c_i <- c_i + l, H_i <- (c_i H_i + W_i) / (c_i + l) of Eq. (1); flattening the
    round's update to one vector of l values in factor space; the cosine shift of Eq. (2); the measurement
    error of Eq. (3); the p distribution of Eq. (4) and the per-cluster q of Eq. (5); the
    Jensen-Divergence set (Eq. 11-12), its maximum Max_JD, the CRP-Jensen assignment and the cluster
    moment update of Eqs. (6)-(7); the two filtering rules of Alg. 2. Clusters, the shared base measure
    and the per-client posteriors persist across rounds. The plugin only excludes clients and proposes
    equal weights, so the host's own FedAvg is step 14.

    Deviations: the paper's W_i is a full local model and G^{t-1} the previous global model, while here
    both sides of Eqs. (2)-(3) are factor-space quantities, W_i = uploads.factor_delta(i) and G^{t-1} =
    the previous round's aggregate update (kept from SERVER_POST_AGGREGATE); G^0 enters only through
    mu_p and sigma_p. Eq. (1) is written per client, but the p distribution of Eq. (4) uses one shared
    H^t per round, as Sect. 4.2.2 words it: the paper reports exactly equal Max_JD for identical poisoned
    updates, which per-client random concentrations and base measures would prevent.

    Not implemented: the random measures A and A_i themselves (steps 1-2); only the base measure's
    parameters and the concentration are carried, because no later equation uses a draw. The per-client
    posterior (c_i, H_i) is maintained and reported as a feature but does not enter the detection, which
    reads the shared H^t. The aggregation itself (step 14) belongs to the host.

    Open in the paper and chosen here: the posterior base measure of Eq. (1) is read as a per-coordinate
    convex combination, H_i <- (c_i/(c_i+l)) H_i + (1/(c_i+l)) W_i (the printed 1/(c_i l) times the sum of
    the l values is either a scalar or is not of the dimension of H_i); Eq. (3) is read as
    sigma_w = ||G - W|| * cos(G, W), since the paper writes sigma and sigma^2 for the same quantity;
    Eq. (4) step (iii) is the normal density of the current value with mean Wbar and unit standard
    deviation (the other reading divides by Wbar, which is near zero in factor space and collapses p);
    m = (p + q) / 2 and natural logarithms; p and q are non-negative vectors over the l coordinates,
    normalized before the divergence; a virtual new cluster uses mu_0 = mu_p and sigma_0 = sigma_p, with
    variance sigma_0^2 + sigma_w^2; tau_k = 1/sigma_cl^2; n_k counts the updates assigned so far and grows
    by one per assignment; the assignment takes the smallest divergence (the paper only says by Max_JD
    and argues that a large one belongs to a new cluster), while Max_JD is the largest divergence over
    the clusters and the virtual new one; the first client of the first round founds the first cluster
    (Alg. 1 lines 8-11) with n_k = 1, its own mean and the new-cluster variance, and clusters persist;
    Alg. 2's two ifs are read as two keep conditions, so a client is removed only when its Max_JD equals
    another client's and is not below the round average. Consequence of that reading: an isolated update
    whose Max_JD is unique is kept even when it is far above the average; the case the paper reports for
    NIDS, identical poisoned scores, is the one this filter removes. The paper does not say what happens
    when every client is removed; no fallback is invented, so a round whose scores all collide excludes
    every client and the host keeps its previous global model.

    Cost: O(n l) per round to flatten the uploads, n l doubles of server state for the per-client base
    measures (which the detection does not read), and O(n^2 l) work for the divergence set.
    """
    name, at, version = 'baybfed', (Stage.SERVER_AGGREGATE, Stage.SERVER_POST_AGGREGATE), '1'
    needs, acts = frozenset({'uploads', 'aggregate'}), frozenset({'select_and_weight'})

    def __init__(self, c: float = 5.0):
        self.c = float(c)

    def _p_vector(self, st: dict, w: torch.Tensor, H: torch.Tensor) -> torch.Tensor:
        """Eq. (4): the baseline density of the shifted update, plus this round's base measure, then
        the step (iii) normal density with mean Wbar and unit spread."""
        u = normal_density(w, st['mu_p'], st['sigma_p']) + H
        return u * normal_density(u, float(w.mean()), 1.0)

    def run(self, ctx):
        st = ctx.state
        if ctx.stage == Stage.SERVER_POST_AGGREGATE:
            agg = ctx.aggregate
            if agg.result is not None and agg.base is not None:
                st['g_prev'] = torch.cat([(agg.result[k] - agg.base[k]).reshape(-1)
                                          for k in sorted(agg.base)]).double()
            return ctx.findings()

        up, cids = ctx.uploads, list(ctx.uploads.clients)
        if not cids:
            return ctx.findings(evidence={'skipped': 'no uploads this round'})
        base = up.base_state()
        keys = sorted(base)
        l = sum(int(base[k].numel()) for k in keys)
        if 'mu_p' not in st:
            g0 = torch.cat([base[k].reshape(-1) for k in keys]).double()
            st['mu_p'], st['sigma_p'] = float(g0.mean()), float(g0.std(unbiased=False))
            st['c'], st['H'] = self.c, normal_density(g0, st['mu_p'], st['sigma_p'])
            st['clusters'], st['c_i'], st['H_i'] = [], {}, {}
        ref = st.get('g_prev')

        X = {c: up.factor_delta(c).double() for c in cids}
        cos = {c: (float(geometry.cosine_to(X[c][None, :], ref)[0]) if ref is not None else 0.0) for c in cids}
        sigma_w = {c: (float((X[c] - ref).norm()) * cos[c] if ref is not None else 0.0) for c in cids}
        W = {c: X[c] + cos[c] for c in cids}
        H = (st['c'] / (st['c'] + l)) * st['H'] + (1.0 / (st['c'] + l)) * torch.stack([W[c] for c in cids]).mean(0)
        st['H'] = H
        for c in cids:
            ci = st['c_i'].get(c)
            if ci is None:
                ci = float(ctx.rng.poisson(st['c']))
                st['c_i'][c], st['H_i'][c] = ci, st['H'].clone()
            st['H_i'][c] = (ci / (ci + l)) * st['H_i'][c] + (1.0 / (ci + l)) * W[c]
            st['c_i'][c] = ci + l

        clusters, mu0, sd0 = st['clusters'], st['mu_p'], st['sigma_p']
        if not clusters:
            first = cids[0]
            clusters.append({'mu': float(W[first].mean()),
                             'sd': math.sqrt(sd0 ** 2 + sigma_w[first] ** 2), 'n': 1})
        p = {c: self._p_vector(st, W[c], H) for c in cids}
        jd, scores = {}, {}
        for c in cids:
            values = [jensen_shannon(p[c], normal_density(W[c], cl['mu'], cl['sd'])) for cl in clusters]
            values.append(jensen_shannon(p[c], normal_density(W[c], mu0, math.sqrt(sd0 ** 2 + sigma_w[c] ** 2))))
            jd[c], scores[c] = values, max(values)

        for c in cids:
            k = min(range(len(jd[c])), key=lambda j: jd[c][j])
            if k == len(clusters):
                clusters.append({'mu': mu0, 'sd': math.sqrt(sd0 ** 2 + sigma_w[c] ** 2), 'n': 0})
            cl = clusters[k]
            tau_k, tau_0 = 1.0 / max(cl['sd'] ** 2, 1e-300), 1.0 / max(sd0 ** 2, 1e-300)
            cl['mu'] = (float(W[c].mean()) * cl['n'] * tau_k + mu0 * tau_0) / (cl['n'] * tau_k + tau_0)
            cl['sd'] = math.sqrt(1.0 / (cl['n'] * tau_k + tau_0) + sigma_w[c] ** 2)
            cl['n'] += 1

        average = sum(scores[c] for c in cids) / len(cids)
        counts = {}
        for c in cids:
            counts[scores[c]] = counts.get(scores[c], 0) + 1
        keep = {c for c in cids if counts[scores[c]] == 1 or scores[c] < average}
        excluded = set(cids) - keep
        return ctx.findings(
            scores=scores,
            features={c: {'max_jd': scores[c], 'cosine': cos[c], 'measurement_error': sigma_w[c],
                          'concentration': st['c_i'][c]} for c in cids},
            decision=Decision(excluded=excluded, weights={c: 1.0 for c in keep},
                              flags={c: 'Max_JD repeats in the round and is not below the average' for c in excluded}),
            evidence={'max_jd_avg': average, 'clusters': len(clusters), 'l': l,
                      'base_measure_norm': float(H.norm())})
