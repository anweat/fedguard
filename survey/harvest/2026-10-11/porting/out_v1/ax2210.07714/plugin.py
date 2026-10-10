# plugin.py
"""CrowdGuard (Che et al., 2022) as a fedguard server plugin: reject backdoored local models before
aggregation. See the class docstring for what is implemented and what is not."""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import cluster, transform

_METRICS = ("cosine", "euclidean")
_ALPHA = 0.01


class CrowdGuard(GuardPlugin):
    """CrowdGuard (Che et al., 2022): reject backdoored local models before aggregation, ported from the
    client-side enclaves of the paper to the server side of this library.

    Implemented: the whole detection and filtering pipeline over one round of uploads. With the global
    model G (the broadcast base) and every upload Lt_i loaded in turn on the model handle, one forward
    pass over a labelled validation set gives the pooled output of every submodule the handle exposes;
    for each sample and each layer the cosine distance and the Euclidean distance of the output of Lt_i
    to the output of G are formed (S4-S5). Every client j is then the validator in turn: those distances
    are divided by the same distances of the upload of j, the deviation from one is squared with its
    sign kept, averaged over the samples of each label and concatenated over labels and layers into an
    HLBIM matrix (S6-S8). The matrix is projected on its first principal component (S9) and five tests
    at alpha = 0.01 look for a remaining anomaly (S10): a two-sample Student t test, an F test of equal
    variances, a two-sample Kolmogorov-Smirnov test, points outside the 1.5 IQR fences of a boxplot,
    and points outside the 3-sigma interval. While any test fires, the smaller of two agglomerative
    clusters of the first component is pruned, the tests are re-run on the survivors, and the loop ends
    with the last candidate dropped once more than floor((n - 1) / 2) models would be pruned (S11-S12).
    Each validator ends with a 0/1 vote per model, the own model always 1 (S13). The vote rows go
    through agglomerative clustering into two clusters, the bigger one is read as the benign voters,
    DBSCAN inside it (eps 0.5, min_samples 1) keeps the largest group of equal votes, and the first row
    of that group is the aggregated vote (S14). Clients it rejects are excluded from the round and the
    survivors get weight 1 each, so the host averages them equally with delta 1 (S15-S16).

    Resource `validation_set`: a mapping {"samples": [...], "labels": [...]}, one label per sample, the
    samples in the format the model handle expects (e.g. the text_of of an HFModelHandle).

    Deviations: the paper validates inside the TEE of each client on the local data of that client, one
    validator per client, and the server only aggregates votes; here the whole pipeline runs on the
    server over a defender-held labelled set, because a client cannot receive the uploads of this round
    (see the report). The n client-side validators are replayed on the server: each upload in turn is
    the reference model of the relative distance, and the n vote vectors are aggregated exactly as the
    paper aggregates the votes of n clients; only the data source and the place of computation changed.
    A model is a LoRA state loaded on the base model of the handle, not a full DNN. Deep layer outputs
    are the pooled outputs of the submodules the handle exposes (ModelHandle.activations, pool "mean",
    every submodule selected), not the per-token layer outputs of a fixed image architecture. The
    forward passes are n + 1 over one shared set per round, where the paper spreads n * (n + 1) passes
    over n clients with n different local sets: the total compute here is about n times smaller and it
    is centralized. The votes are computed by the plugin itself instead of arriving from untrusted
    clients, so the robustness of the vote aggregation against lying validators is not exercised. The
    plugin keeps no state across rounds (the paper is round independent).

    Not implemented: S1 (TEE setup and remote attestation) and S2 (the encrypted uplink), which belong
    to the protocol and to the host, not to a plugin; and the client-enclave placement itself, which
    this library cannot schedule because a client has no stage after the uploads of the round arrive.
    A validator that lies about its vote is not modelled.

    Open in the paper and chosen here: the first principal component comes from
    fedguard.ops.transform.pca (centered SVD, sign fixed by the library); the upper and lower groups of
    Alg. 4 line 11 are split by the sign of the principal component value, and the alternative reading
    (the sign of value - median) would only shift both groups by the same constant; the F test of
    Alg. 4 line 19 is implemented rather than the Levene test that footnote 10 also names, and it is
    two-sided; the boxplot rule is 1.5 IQR and the 3-sigma interval is two-sided with the population
    standard deviation; a test with degenerate input (fewer than two points on a side, zero variance)
    is skipped instead of fired; the labelwise mean is the arithmetic mean, labels are ordered by repr
    and a label with no sample is impossible by construction; the HLBIM features are label-major then
    layer name, and only labels and layers present for every model are used; every validator skips its
    own model, which stays voted benign (footnote 15), so the HLBIM matrix has n - 1 rows; the two
    metrics are analysed independently and a model flagged by either is voted malicious (footnote 7
    does not say how the two write the one vote array); clustering uses average linkage on Euclidean
    distances of the values, and DBSCAN uses Euclidean distance; a size tie between the two clusters
    takes the cluster with the larger mean absolute deviation from the median (pruning) or the one with
    more benign votes (vote matrix); the model dropped by the safe abort is the flagged one with the
    smallest principal component value; where the reference distance is zero the ratio is 1 if the
    candidate distance is zero too and 1 + candidate otherwise; the whole resource set is used, with no
    subsampling.

    Cost: n + 1 forward passes over the validation set per round (one per upload and one for the global
    model), all counted by the handle; the HLBIM, the tests and the clusterings are arithmetic on
    (n x labels x layers) and (n x n) matrices. Requires a server-side ModelHandle with lora and
    activations, which the shipped server probe (ProbeView.score) is not.
    """

    name, at, version = "crowdguard", Stage.SERVER_AGGREGATE, "1"
    needs = frozenset({"uploads", "model_handle"})
    resources = frozenset({"validation_set"})
    acts = frozenset({"select_and_weight"})

    def __init__(self, alpha: float = _ALPHA, pool: str = "mean"):
        self.alpha, self.pool = float(alpha), pool

    def run(self, ctx):
        up, handle = ctx.uploads, ctx.model_handle
        cids = list(up.clients)
        if len(cids) < 3:
            return ctx.findings(evidence={"skipped": "needs at least 3 uploaded models, got " + str(len(cids))})
        samples, groups, labels = _validation_set(ctx.resource("validation_set"))
        base = _dlo(handle, up.base_state(), samples, self.pool)
        dist = {cid: _distances_to(_dlo(handle, up.state(cid), samples, self.pool), base) for cid in cids}
        layers = sorted(set(base).intersection(*(set(dist[cid]["cosine"]) for cid in cids)))
        if not layers:
            return ctx.findings(evidence={"skipped": "the model handle exposes no layer outputs"})
        votes = {cid: 1 for cid in cids}
        flagged = {cid: [] for cid in cids}
        cap = math.floor((len(cids) - 1) / 2)
        for j in cids:
            others = [cid for cid in cids if cid != j]
            if len(others) < 3:
                continue
            for metric in _METRICS:
                X = torch.stack([_hlbim(dist[cid][metric], dist[j][metric], groups, labels, layers) for cid in others])
                for i in _prune(X, cap, self.alpha):
                    votes[others[i]] = 0
                    flagged[others[i]].append(j + "/" + metric)
        V = torch.tensor([[votes[m] for m in cids] for _ in cids], dtype=torch.float64)
        V.diagonal().fill_(1.0)
        accepted = _aggregate_votes(V)
        excluded = {cid for i, cid in enumerate(cids) if float(accepted[i]) <= 0.0}
        kept = [cid for cid in cids if cid not in excluded]
        decision = Decision(excluded=set(excluded), weights={cid: 1.0 for cid in kept},
                            flags={cid: "crowdguard: rejected by the aggregated vote" for cid in excluded})
        scores = {cid: float((V[:, i] <= 0).double().mean()) for i, cid in enumerate(cids)}
        evidence = {"validators": len(cids), "labels": len(labels), "layers": layers, "abort_after": cap,
                    "flagged": {cid: len(v) for cid, v in flagged.items() if v},
                    "votes": {cid: int(votes[cid]) for cid in cids},
                    "aggregated": {cid: int(accepted[i]) for i, cid in enumerate(cids)}}
        return ctx.findings(scores=scores, decision=decision, evidence=evidence)


def _validation_set(obj):
    """Resource validation_set: {"samples": [...], "labels": [...]}, one label per sample."""
    if not isinstance(obj, dict) or "samples" not in obj or "labels" not in obj:
        raise TypeError("validation_set must be a mapping with samples and labels")
    samples, labels = list(obj["samples"]), list(obj["labels"])
    if not samples or len(samples) != len(labels):
        raise ValueError("validation_set: samples and labels must be nonempty and equally long")
    order = sorted(set(labels), key=repr)
    groups = {y: torch.tensor([i for i, v in enumerate(labels) if v == y], dtype=torch.long) for y in order}
    return samples, groups, order


def _dlo(handle, state, samples, pool):
    """S4: one forward pass with state loaded; the pooled output of every submodule the handle exposes."""
    with handle.lora(state):
        out = handle.activations(samples, lambda name: True, pool=pool)
    return {str(name): value.detach().double().cpu() for name, value in out.items()}


def _rowwise_distance(A, B, metric):
    """Paired distance between the rows of two (n, d) matrices. fedguard.ops.geometry only compares rows
    within one matrix, or every row with one reference vector."""
    A, B = A.double(), B.double()
    if metric == "euclidean":
        return (A - B).norm(dim=1)
    if metric == "cosine":
        na, nb = A.norm(dim=1), B.norm(dim=1)
        cos = torch.where((na > 0) & (nb > 0), (A * B).sum(dim=1) / (na * nb).clamp_min(1e-300), torch.zeros_like(na))
        return 1.0 - cos.clamp(-1.0, 1.0)
    raise ValueError("unknown metric " + metric)


def _distances_to(dlo, base):
    """S5: per sample and layer the cosine and the Euclidean distance of one state to the global one."""
    out = {}
    for metric in _METRICS:
        rows = {}
        for layer in sorted(set(dlo) & set(base)):
            if dlo[layer].shape == base[layer].shape:
                rows[layer] = _rowwise_distance(dlo[layer], base[layer], metric)
        out[metric] = rows
    return out


def _ratio(num, den):
    """S6 line 21: the distance divided by the distance of the validator own model."""
    return torch.where(den > 0, num / den.clamp_min(1e-300), torch.where(num <= 0, torch.ones_like(num), 1.0 + num))


def _signed_square(rel):
    """S6 line 22: |rel - 1| * (rel - 1), the squared deviation with its sign kept."""
    d = rel - 1.0
    return d.abs() * d


def _hlbim(d_m, d_j, groups, labels, layers):
    """S7-S8: per label the mean over its samples, over layers, then the label blocks concatenated."""
    parts = []
    for lab in labels:
        idx = groups[lab]
        for layer in layers:
            parts.append(_signed_square(_ratio(d_m[layer][idx], d_j[layer][idx])).mean())
    return torch.stack(parts)


def _pc1(X):
    """S9: first principal component of an (models x features) matrix."""
    scores, _, _ = transform.pca(X, 1)
    return scores[:, 0]


def _significant(values, alpha):
    """S10: the five tests, OR-ed, on the values of the first principal component."""
    v = values.double().flatten()
    if v.numel() < 3 or float(v.max() - v.min()) == 0.0:
        return False
    upper, lower = v[v >= 0], v[v < 0]
    return bool(_t_test(upper, lower, alpha) or _f_test(upper, lower, alpha) or _ks_test(upper, lower, alpha)
                or _boxplot_outlier(v) or _sigma_outlier(v))


def _t_test(a, b, alpha):
    """Two-sample Student t test with pooled variance (Alg. 4 line 17)."""
    na, nb = a.numel(), b.numel()
    if na < 2 or nb < 2:
        return False
    diff = float(a.mean() - b.mean())
    sp2 = float(((na - 1) * a.var(unbiased=True) + (nb - 1) * b.var(unbiased=True)) / (na + nb - 2))
    if sp2 <= 0.0:
        return diff != 0.0
    t = abs(diff) / math.sqrt(sp2 * (1.0 / na + 1.0 / nb))
    return _t_p_value(t, na + nb - 2) < alpha


def _f_test(a, b, alpha):
    """F test of equal variances (Alg. 4 line 19)."""
    na, nb = a.numel(), b.numel()
    if na < 2 or nb < 2:
        return False
    va, vb = float(a.var(unbiased=True)), float(b.var(unbiased=True))
    if va <= 0.0 or vb <= 0.0:
        return False
    return _f_p_value(va / vb, na - 1, nb - 1) < alpha


def _ks_test(a, b, alpha):
    """Two-sample Kolmogorov-Smirnov test (Alg. 4 line 18) with the asymptotic p-value."""
    na, nb = a.numel(), b.numel()
    if na < 1 or nb < 1:
        return False
    sa, sb = a.sort().values, b.sort().values
    grid = torch.cat([sa, sb])
    ca = torch.searchsorted(sa, grid, right=True).double() / na
    cb = torch.searchsorted(sb, grid, right=True).double() / nb
    d = float((ca - cb).abs().max())
    ne = na * nb / (na + nb)
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * d
    p = 2.0 * sum((-1.0) ** (k - 1) * math.exp(-2.0 * k * k * lam * lam) for k in range(1, 101))
    return min(max(p, 0.0), 1.0) < alpha


def _boxplot_outlier(v, factor=1.5):
    """Boxplot rule (Alg. 4 line 21): outside the 1.5 IQR fences."""
    q1, q3 = torch.quantile(v, torch.tensor([0.25, 0.75], dtype=torch.float64)).tolist()
    iqr = q3 - q1
    if iqr <= 0.0:
        return False
    return bool(((v < q1 - factor * iqr) | (v > q3 + factor * iqr)).any())


def _sigma_outlier(v, sigma=3.0):
    """Three-sigma rule (Alg. 4 line 22), two-sided, population standard deviation."""
    sd = float(v.std(unbiased=False))
    if sd <= 0.0:
        return False
    mu = float(v.mean())
    return bool(((v - mu).abs() > sigma * sd).any())


def _betacf(a, b, x):
    """Continued fraction for the incomplete beta function (Lentz, Numerical Recipes 6.4)."""
    tiny, eps = 1e-300, 1e-12
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a, b, x):
    """Regularized incomplete beta I_x(a, b). Written by hand: torch has gammainc but no betainc, and
    torch.distributions.StudentT.cdf / FisherSnedecor.cdf raise NotImplementedError."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _t_p_value(t, df):
    """Two-sided p-value of a Student t statistic."""
    return _betai(0.5 * df, 0.5, df / (df + t * t))


def _f_p_value(f, d1, d2):
    """Two-sided p-value of a variance ratio."""
    cdf = _betai(0.5 * d1, 0.5 * d2, d1 * f / (d1 * f + d2))
    return min(cdf, 1.0 - cdf) * 2.0


def _prune(X, cap, alpha):
    """S9-S12 on one validator and one metric: prune the smaller cluster while the tests fire."""
    alive = list(range(X.shape[0]))
    picked = []
    while len(alive) >= 3:
        vals = _pc1(X[alive])
        if not _significant(vals, alpha):
            break
        lab = cluster.agglomerative(cluster.distances(vals[:, None], "euclidean"), 2, "average")
        sizes = (int((lab == 0).sum()), int((lab == 1).sum()))
        if sizes[0] != sizes[1]:
            minority = 0 if sizes[0] < sizes[1] else 1
        else:
            dev = [float((vals[lab == c] - vals.median()).abs().mean()) for c in (0, 1)]
            minority = 0 if dev[0] >= dev[1] else 1
        take = [alive[i] for i in range(len(alive)) if int(lab[i]) == minority]
        if len(picked) + len(take) > cap:
            take.remove(min(take, key=lambda i: float(vals[alive.index(i)])))
            picked += take
            break
        picked += take
        alive = [i for i in alive if i not in set(take)]
    return picked


def _aggregate_votes(V):
    """S14: agglomerative majority, then DBSCAN inside it, then the first row of the largest cluster."""
    rows = V.shape[0]
    if rows == 1:
        return V[0]
    lab = cluster.agglomerative(cluster.distances(V, "euclidean"), 2, "average")
    n0 = int((lab == 0).sum())
    if n0 != rows - n0:
        majority = 0 if n0 > rows - n0 else 1
    else:
        sums = [float(V[lab == c].sum()) for c in (0, 1)]
        majority = 0 if sums[0] >= sums[1] else 1
    M = V[lab == majority]
    if M.shape[0] == 1:
        return M[0]
    dlab = cluster.dbscan(cluster.distances(M, "euclidean"), 0.5, 1).tolist()
    counts = {}
    for value in dlab:
        counts[value] = counts.get(value, 0) + 1
    best = max(counts, key=lambda value: (counts[value], -value))
    return M[dlab.index(best)]
