"""Server side, on the uploaded updates: robust aggregation, detection of deviating clients, repair of the
aggregate. Krum, coordinate median, trimmed mean, FoolsGold, FLTrust, FLAME, FreqFed, FLDetector, MUD-HoG,
LoMar, MCD, CRFL (training-time part), Safe-FedLLM at client level, Safe LoRA.

As everywhere in fedguard.methods: every class names its paper, says which steps are implemented, what
deviates, and which choices the paper left open; none has been checked against the authors' code or
reproduced numerically. The step-by-step extractions they were written from are in
`survey/harvest/2026-10-08/opsread/<key>.md`.

Two things hold for all of them under LoRA:
  - Vectors are taken in factor space: the flattened (uploaded - broadcast) A and B entries. The
    original methods were defined on full model weights. Where a method only needs inner products
    (`space="product"`), the exact Gram matrix of the products B_i A_i - B_g A_g is used instead.
  - A replaced global model must keep the factor shapes, so coordinate-wise rules act on A and B
    separately. That is not the same as acting on the product.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.methods.shared import _A, _B, first_layer_b_feature, two_stage_calibration, update_gram, update_matrix
from fedguard.ops import cluster, density, geometry, probe, robust, sequential, states, transform, update
from fedguard.ops.lowrank import LowRank


class Krum(GuardPlugin):
    """Krum and Multi-Krum (Blanchard et al., NeurIPS 2017).

    Score of a client = sum of squared distances to its n - f - 2 nearest other clients; keep the m
    clients with the lowest scores (m = 1 is Krum, m > 1 Multi-Krum, which averages them).
    Open in the paper and chosen here: ties are broken by client order; with n < f + 3 nothing is done.
    The kept clients keep the weights the aggregation would have used (the paper averages them equally;
    pass equal_weights=True for that).
    """
    name, at, version = "krum", Stage.SERVER_AGGREGATE, "1"
    needs, acts = frozenset({"uploads"}), frozenset({"select_and_weight"})

    def __init__(self, f: int = 1, m: int = 1, space: str = "factor", equal_weights: bool = False):
        self.f, self.m, self.space, self.equal_weights = f, m, space, equal_weights

    def run(self, ctx):
        cids = ctx.uploads.clients
        if len(cids) < self.f + 3:
            return ctx.findings(evidence={"skipped": f"needs n >= f + 3, got n={len(cids)}"})
        scores = geometry.krum_scores(geometry.sq_distances_from_gram(update_gram(ctx.uploads, cids, self.space)), self.f)
        order = sorted(range(len(cids)), key=lambda i: (float(scores[i]), i))
        keep = {cids[i] for i in order[: self.m]}
        d = Decision(excluded=set(cids) - keep, weights={c: 1.0 for c in keep} if self.equal_weights else {})
        return ctx.findings(scores={c: float(s) for c, s in zip(cids, scores)}, decision=d)


class _CoordinateRule(GuardPlugin):
    """Replace the aggregation result by a coordinate-wise robust statistic of the aggregated clients' updates."""
    at = Stage.SERVER_POST_AGGREGATE
    needs, acts = frozenset({"uploads", "aggregate"}), frozenset({"replace_global"})

    def _combine(self, X: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError

    def run(self, ctx):
        up, agg = ctx.uploads, ctx.aggregate
        cids = [c for c in agg.aggregated if c in up.clients]
        if not cids:
            return ctx.findings(evidence={"skipped": "no aggregated uploads"})
        base = up.base_state()
        keys = sorted(base)
        combined = self._combine(update_matrix(up, cids))
        new = states.add(base, states.unflatten(combined, base, keys))
        return ctx.findings(proposals={"replacement": new}, evidence={"clients": cids})


class CoordinateMedian(_CoordinateRule):
    """Coordinate-wise median (Yin et al., ICML 2018), in place of the mean of the updates.
    Implemented: the median of every coordinate over the clients' updates; client weights are ignored, as in the paper.
    Deviations: taken on the LoRA factors A and B separately, which is not the median of their product.
    Open in the paper and chosen here: an even count gives the mean of the two middle values."""
    name, version = "coordinate_median", "1"

    def _combine(self, X):
        return robust.coordinate_median(X)


class TrimmedMean(_CoordinateRule):
    """Coordinate-wise beta-trimmed mean (Yin et al., ICML 2018): drop the floor(beta * n) largest and
    smallest values of every coordinate, average the rest. The paper requires beta at least the fraction
    of Byzantine clients; it is a parameter here.
    Deviations: taken on the LoRA factors A and B separately, which is not the trimmed mean of their product."""
    name, version = "trimmed_mean", "1"

    def __init__(self, beta: float = 0.1):
        self.beta = beta

    def _combine(self, X):
        return robust.trimmed_mean(X, self.beta)


class FoolsGold(GuardPlugin):
    """FoolsGold (Fung et al., 2018): clients whose accumulated updates point the same way are sybils.

    Implemented: per-client history = running sum of its updates; cosine similarity between histories;
    pardoning; alpha = 1 - max similarity; rescaling; logit with confidence kappa.
    Not implemented: the paper's restriction to output-layer parameters and its "indicative feature"
    weighting. A LoRA adapter has no output layer, so all factor entries are used.
    Open in the paper and chosen here: history accumulates from the first round a client is seen, with
    no window or decay; absent clients keep their history; boundary cases follow the authors' code.
    The paper applies alpha as a per-client learning rate on an unnormalized sum. Here alpha becomes the
    aggregation weight, which the framework normalizes: relative weights match, the overall step size does not.
    """
    name, at, version = "foolsgold", Stage.SERVER_AGGREGATE, "1"
    needs, acts = frozenset({"uploads"}), frozenset({"select_and_weight"})

    def __init__(self, kappa: float = 1.0):
        self.kappa = kappa

    def run(self, ctx):
        up = ctx.uploads
        hist = ctx.state.setdefault("history", {})
        for c in up.clients:
            d = up.factor_delta(c).double()
            hist[c] = hist[c] + d if c in hist else d
        cids = up.clients
        if len(cids) < 2:
            return ctx.findings(evidence={"skipped": "needs at least two clients"})
        alpha = robust.foolsgold_weights(geometry.cosine_matrix(torch.stack([hist[c] for c in cids])), self.kappa)
        weights = {c: float(a) for c, a in zip(cids, alpha)}
        return ctx.findings(scores={c: 1 - w for c, w in weights.items()}, features={c: {"alpha": w} for c, w in weights.items()},
                            decision=Decision(weights={c: w for c, w in weights.items() if w > 0},
                                              excluded={c for c, w in weights.items() if w == 0}))


class FLTrust(GuardPlugin):
    """FLTrust (Cao et al., NDSS 2021): a server update computed on a small clean root dataset bootstraps trust.

    Implemented: trust score TS_i = ReLU(cos(g_i, g_0)); every client update rescaled to the norm of the
    server update; aggregation weights TS_i.
    Resource `server_update`: a function (broadcast LoRA state) -> LoRA state after the server's own
    training on its root dataset with the clients' settings. Training it is the caller's job.
    Open in the paper and chosen here: a client or server update of zero norm gets trust 0; when every
    trust score is 0 all clients are excluded, so the adapter keeps the previous global model.
    The paper also applies a global learning rate to the aggregate; the framework's aggregation does not.
    """
    name, version = "fltrust", "1"
    at = (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE)
    needs, acts = frozenset({"uploads"}), frozenset({"transform_update", "select_and_weight"})
    resources = frozenset({"server_update"})

    def run(self, ctx):
        if ctx.stage == Stage.SERVER_AGGREGATE:
            trust = ctx.state.get("trust", {})
            return ctx.findings(decision=Decision(weights={c: t for c, t in trust.items() if t > 0},
                                                  excluded={c for c, t in trust.items() if t <= 0}))
        up = ctx.uploads
        base = up.base_state()
        g0 = states.flatten(states.delta(ctx.resource("server_update")(base), base))
        cids = up.clients
        cos = geometry.cosine_to(update_matrix(up, cids), g0) if cids else torch.zeros(0)
        trust = {c: max(0.0, float(v)) for c, v in zip(cids, cos)}
        ctx.state["trust"] = trust
        target = float(g0.norm())
        transformed = {c: update.scale_to_norm(up.state(c), base, target) for c in cids} if target > 0 else {}
        return ctx.findings(scores={c: 1 - t for c, t in trust.items()}, features={c: {"trust": t} for c, t in trust.items()},
                            proposals={"transformed": transformed}, evidence={"server_update_norm": target})


class FLAME(GuardPlugin):
    """FLAME (Nguyen et al., USENIX Security 2022): cluster, clip, add noise.

    Implemented: pairwise cosine distances; the single majority cluster (HDBSCAN with
    min_cluster_size = n/2 + 1, min_samples = 1) is admitted; clipping bound S_t = median of all clients'
    update norms; admitted updates scaled by min(1, S_t / norm); equal-weight average; Gaussian noise
    N(0, (lambda * S_t)^2) on the aggregate.
    Deviations: distances are taken between updates (uploaded - broadcast), not between the uploaded
    models; with LoRA the uploads share the broadcast factors and would be nearly parallel. Without
    scikit-learn, ops.cluster.majority_cluster stands in for HDBSCAN (same contract, different algorithm).
    Open in the paper and chosen here: the clipping reference is the model the round was broadcast with;
    the median of an even count is the mean of the two middle values; lambda defaults to the paper's
    0.001 (image and text settings) and is not derived from an (epsilon, delta) budget here.
    """
    name, version = "flame", "1"
    at = (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE, Stage.SERVER_POST_AGGREGATE)
    needs = frozenset({"uploads", "aggregate"})
    acts = frozenset({"transform_update", "select_and_weight", "replace_global"})

    def __init__(self, noise_lambda: float = 0.001, space: str = "factor"):
        self.noise_lambda, self.space = noise_lambda, space

    def run(self, ctx):
        st = ctx.state
        if ctx.stage == Stage.SERVER_RECEIVE:
            up = ctx.uploads
            cids = up.clients
            G = update_gram(up, cids, self.space)
            admitted = cluster.majority_cluster(geometry.cosine_distances_from_gram(G))
            norms = torch.sqrt(torch.diagonal(G).clamp_min(0))
            bound = float(torch.quantile(norms, 0.5)) if len(cids) else 0.0
            st["admitted"], st["bound"] = {c for c, a in zip(cids, admitted) if a}, bound
            base = up.base_state()
            clipped = {c: update.clip_to_norm(up.state(c), base, bound)[0] for c, n in zip(cids, norms)
                       if c in st["admitted"] and float(n) > bound} if self.space == "factor" else {}
            return ctx.findings(features={c: {"norm": float(n), "admitted": float(c in st["admitted"])} for c, n in zip(cids, norms)},
                                proposals={"transformed": clipped}, evidence={"bound": bound})
        if ctx.stage == Stage.SERVER_AGGREGATE:
            cids = ctx.uploads.clients
            admitted = st.get("admitted", set(cids))
            return ctx.findings(decision=Decision(excluded=set(cids) - admitted, weights={c: 1.0 for c in admitted}))
        sigma = self.noise_lambda * st.get("bound", 0.0)
        if sigma <= 0:
            return ctx.findings(evidence={"sigma": 0.0})
        gen = torch.Generator().manual_seed(int(ctx.rng.integers(2**31)))
        return ctx.findings(proposals={"replacement": update.add_gaussian_noise(ctx.aggregate.result, sigma, gen)},
                            evidence={"sigma": sigma})


class FreqFed(GuardPlugin):
    """FreqFed (Fereidooni et al., NDSS 2024): cluster clients on the low-frequency DCT components of their updates.

    Implemented: each client's vector laid out as a square matrix, 2-D DCT, the low-frequency triangle
    (i + j <= side // 2), pairwise cosine distances, the largest cluster kept, equal-weight average.
    Open in the paper and chosen here: how weights of many shapes become one square matrix (here: all
    factor entries in sorted key order, row by row, zero-padded to the next square); the DCT is the
    orthonormal DCT-II (the paper's printed normalization scales only the first row and column differently,
    which cosine distance is not invariant to); HDBSCAN's parameters are not given, so the majority
    setting of FLAME is used, and a cluster must hold a majority to be kept.
    Deviation: the transform is applied to updates rather than uploaded models, for the reason given in FLAME.
    Cost: one DCT of a sqrt(d) x sqrt(d) matrix per client.
    """
    name, at, version = "freqfed", Stage.SERVER_AGGREGATE, "1"
    needs, acts = frozenset({"uploads"}), frozenset({"select_and_weight"})

    def run(self, ctx):
        up = ctx.uploads
        cids = up.clients
        if len(cids) < 3:
            return ctx.findings(evidence={"skipped": "needs at least three clients"})
        F = torch.stack([transform.low_frequency_triangle(transform.dct_2d(transform.as_square(up.factor_delta(c)))) for c in cids])
        D = cluster.distances(F, "cosine")
        keep = cluster.majority_cluster(D)
        kept = {c for c, k in zip(cids, keep) if k}
        return ctx.findings(features={c: {"kept": float(c in kept)} for c in cids},
                            decision=Decision(excluded=set(cids) - kept, weights={c: 1.0 for c in kept}),
                            evidence={"low_frequency_components": int(F.shape[1])})


class FLDetector(GuardPlugin):
    """FLDetector (Zhang et al., KDD 2022): a client whose updates are inconsistent with what the global
    model's trajectory predicts is malicious.

    Implemented: differences of the global model and of the aggregated update over a window of N rounds;
    L-BFGS Hessian-vector product; predicted update = the client's previous update + H (w_t - w_{t-1});
    Euclidean distance to the received update, L1-normalized over clients; mean over the window as the
    suspicious score; gap statistic to decide whether there are two groups; 2-means; the group with the
    larger mean score is flagged and excluded from this round on.
    Not implemented: the paper removes the flagged clients and restarts training from scratch.
    Open in the paper and chosen here: scores are produced once a full window exists (the paper starts
    at round 50; `start_round` sets that); a client absent in the previous round gets no score; a
    rank-deficient window is solved with a pseudo-inverse.
    Memory: N + 1 vectors of the global model's size plus one per client.
    """
    name, version = "fldetector", "1"
    at = (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE, Stage.SERVER_POST_AGGREGATE)
    needs, acts = frozenset({"uploads", "aggregate"}), frozenset({"select_and_weight"})

    def __init__(self, window: int = 10, start_round: int = 0, k_max: int = 10, references: int = 20):
        self.window, self.start_round, self.k_max, self.references = window, start_round, k_max, references

    def run(self, ctx):
        st = ctx.state
        st.setdefault("dW", []), st.setdefault("dG", []), st.setdefault("dists", []), st.setdefault("flagged", set())
        if ctx.stage == Stage.SERVER_AGGREGATE:
            return ctx.findings(decision=Decision(excluded=set(ctx.uploads.clients) & st["flagged"],
                                                  flags={c: "inconsistent with the predicted update" for c in st["flagged"]}))
        if ctx.stage == Stage.SERVER_POST_AGGREGATE:            # the round's global step, for the next round's prediction
            agg = ctx.aggregate
            w_prev, w_now = states.flatten(agg.base), states.flatten(agg.result)
            g = w_now - w_prev
            if "g_prev" in st:
                st["dW"].append(st["step_prev"])
                st["dG"].append(g - st["g_prev"])
                st["dW"], st["dG"] = st["dW"][-self.window:], st["dG"][-self.window:]
            st["g_prev"], st["step_prev"] = g, g
            return ctx.findings()
        up = ctx.uploads
        current = {c: up.factor_delta(c).double() for c in up.clients}
        previous, st["last"] = st.get("last", {}), current
        if len(st["dW"]) < self.window or ctx.round < self.start_round:
            return ctx.findings(evidence={"skipped": f"window {len(st['dW'])}/{self.window}"})
        hv = sequential.lbfgs_hvp(torch.stack(st["dW"], dim=1), torch.stack(st["dG"], dim=1), st["step_prev"])
        cids = [c for c in up.clients if c in previous]
        if len(cids) < 3:
            return ctx.findings(evidence={"skipped": "fewer than three clients seen in consecutive rounds"})
        dist = torch.stack([(previous[c] + hv - current[c]).norm() for c in cids])
        dist = dist / dist.sum().clamp_min(1e-300)
        st["dists"] = (st["dists"] + [dict(zip(cids, dist.tolist()))])[-self.window:]
        score = {c: sum(r[c] for r in st["dists"] if c in r) / sum(c in r for r in st["dists"]) for c in cids}
        s = torch.tensor([score[c] for c in cids], dtype=torch.float64)
        k = cluster.gap_statistic_k(s, self.k_max, self.references, seed=int(ctx.rng.integers(2**31)))
        if k > 1:
            labels, centers = cluster.kmeans(s[:, None], 2, seed=0)
            bad = int(centers.flatten().argmax())
            st["flagged"] |= {c for c, l in zip(cids, labels.tolist()) if l == bad}
        return ctx.findings(scores=score, evidence={"clusters": k, "flagged": sorted(st["flagged"])})


class MudHoG(GuardPlugin):
    """MUD-HoG (Gupta et al., ESORICS 2022): tell sign-flipping, additive-noise and targeted attackers and
    unreliable clients apart from short and long histories of gradients.

    Per client: short HoG = mean of its last `short` updates, long HoG = sum of all its updates.
    1. sign flipping: cosine of the short HoG to the coordinate-wise median short HoG below 0
    2. additive noise: density clustering of the remaining short HoGs; for the clients outside the largest
       group, distance to that group's median; above the largest-gap threshold -> attacker
    3. targeted: 2-means on the remaining long HoGs; the smaller cluster
    4. unreliable: cosine of the remaining short HoGs to their median; below the largest-gap threshold
    Attackers are excluded once flagged in `confirm` consecutive rounds; unreliable clients keep a
    fraction `alpha` of their weight. Nothing is judged during the first `warmup` rounds.
    Deviations: the update of a round stands in for the gradient; ops.cluster.density_clusters stands in
    for DBSCAN, whose eps and minPts the paper does not give.
    Open in the paper and chosen here: the median is coordinate-wise; a single client outside the largest
    group is not judged (no gap exists); equal-sized 2-means clusters flag nobody; flags are recomputed
    every round and only confirmed attackers are excluded, for that round; a client absent from a round
    keeps its history and loses its streak.
    Note that steps 3 and 4 flag someone whenever they run, also when every client is honest.
    """
    name, version = "mud_hog", "1"
    at = (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE)
    needs, acts = frozenset({"uploads", "reports"}), frozenset({"select_and_weight"})

    def __init__(self, warmup: int = 3, short: int = 3, alpha: float = 0.5, confirm: int = 2):
        self.warmup, self.short, self.alpha, self.confirm = warmup, short, alpha, confirm

    def run(self, ctx):
        st = ctx.state
        if ctx.stage == Stage.SERVER_AGGREGATE:
            n = ctx.reports.values("num_examples")
            weights = {c: self.alpha * float(n[c]) for c in st.get("unreliable", ()) if c in n}
            return ctx.findings(decision=Decision(excluded=set(st.get("confirmed", ())), weights=weights,
                                                  flags={c: "attacker in consecutive rounds" for c in st.get("confirmed", ())}))
        up = ctx.uploads
        cids = up.clients
        recent, total, streak = st.setdefault("recent", {}), st.setdefault("total", {}), st.setdefault("streak", {})
        for c in cids:
            d = up.factor_delta(c).double()
            recent[c] = (recent.get(c, []) + [d])[-self.short:]
            total[c] = d if c not in total else total[c] + d
        st["confirmed"], st["unreliable"] = set(), set()
        if ctx.round < self.warmup or len(cids) < 3:
            return ctx.findings(evidence={"skipped": f"warm-up or fewer than 3 clients (round {ctx.round})"})
        S = torch.stack([sequential.window_mean(recent[c], self.short) for c in cids])
        L = torch.stack([total[c] for c in cids])
        kind = {}
        cos = geometry.cosine_to(S, robust.coordinate_median(S))
        for i, c in enumerate(cids):
            if float(cos[i]) < 0:
                kind[c] = "sign_flipping"
        rest = [i for i, c in enumerate(cids) if c not in kind]
        if len(rest) >= 3:
            labels = cluster.density_clusters(cluster.distances(S[rest]))
            sizes = {int(lab): int((labels == lab).sum()) for lab in labels.unique() if int(lab) >= 0}
            if sizes:
                main = max(sizes, key=sizes.get)
                inside = [i for i, lab in zip(rest, labels.tolist()) if lab == main]
                outside = [i for i, lab in zip(rest, labels.tolist()) if lab != main]
                if len(outside) >= 2:
                    dist = geometry.distance_to(S[outside], robust.coordinate_median(S[inside]))
                    bar = robust.largest_gap_threshold(dist)
                    for i, v in zip(outside, dist.tolist()):
                        if v > bar:
                            kind[cids[i]] = "additive_noise"
        rest = [i for i, c in enumerate(cids) if c not in kind]
        if len(rest) >= 3:
            labels, _ = cluster.kmeans(L[rest], 2, seed=int(ctx.rng.integers(2**31)))
            ones = int(labels.sum())
            if ones * 2 != len(rest):
                small = 1 if ones * 2 < len(rest) else 0
                for i, lab in zip(rest, labels.tolist()):
                    if lab == small:
                        kind[cids[i]] = "targeted"
        rest = [i for i, c in enumerate(cids) if c not in kind]
        unreliable = set()
        if len(rest) >= 2:
            cos = geometry.cosine_to(S[rest], robust.coordinate_median(S[rest]))
            bar = robust.largest_gap_threshold(cos)
            unreliable = {cids[i] for i, v in zip(rest, cos.tolist()) if v < bar}
        for c in cids:
            streak[c] = streak.get(c, 0) + 1 if c in kind else 0
        for c in set(streak) - set(cids):
            streak[c] = 0
        st["confirmed"] = {c for c in cids if streak[c] >= self.confirm}
        st["unreliable"] = unreliable
        return ctx.findings(scores={c: float(c in kind) for c in cids},
                            features={c: {"streak": float(streak[c]), "unreliable": float(c in unreliable)} for c in cids},
                            evidence={"flagged": dict(sorted(kind.items())), "unreliable": sorted(unreliable),
                                      "confirmed": sorted(st["confirmed"])})


class LoMar(GuardPlugin):
    """LoMar (Li et al., IEEE TDSC 2022): score each update by its kernel density relative to the density
    of its k nearest neighbours; an update whose ratio is below the threshold is left out.

    Implemented: k nearest neighbours in squared Euclidean distance, Gaussian kernel density, the ratio
    F(i) of a client's density to the mean density of its neighbours, the gate F(i) >= threshold.
    Deviations: the paper splits the parameters by output label and multiplies the per-label ratios; a
    LoRA adapter has no output layer, so one ratio over the whole update is used. The threshold is the
    paper's empirical value 1.0, not the bound of its Eq. 10 (an inequality the paper does not solve).
    Open in the paper and chosen here: k = floor(0.4 n), at least 1; a neighbour set excludes the client
    itself; the bandwidth is the median k-th neighbour distance (the paper leaves it to the user); if every
    client falls below the threshold nobody is excluded.
    With threshold 1.0 roughly half of a homogeneous group falls below it; the paper reports this value
    as the best on average for its settings.
    """
    name, version = "lomar", "1"
    at = (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE)
    needs, acts = frozenset({"uploads"}), frozenset({"select_and_weight"})

    def __init__(self, k_share: float = 0.4, threshold: float = 1.0, bandwidth: float | None = None):
        self.k_share, self.threshold, self.bandwidth = k_share, threshold, bandwidth

    def run(self, ctx):
        st = ctx.state
        if ctx.stage == Stage.SERVER_AGGREGATE:
            return ctx.findings(decision=Decision(excluded=set(st.get("excluded", ()))))
        cids = ctx.uploads.clients
        if len(cids) < 3:
            st["excluded"] = set()
            return ctx.findings(evidence={"skipped": "fewer than 3 clients"})
        k = max(1, math.floor(self.k_share * len(cids)))
        F = density.knn_density_ratio(update_matrix(ctx.uploads, cids), k, self.bandwidth)
        low = {c for c, f in zip(cids, F.tolist()) if f < self.threshold}
        st["excluded"] = low if len(low) < len(cids) else set()
        return ctx.findings(scores={c: max(0.0, 1.0 - f) for c, f in zip(cids, F.tolist())},
                            features={c: {"malicious_factor": f} for c, f in zip(cids, F.tolist())},
                            evidence={"k": k, "below_threshold": sorted(low)})


class MCD(GuardPlugin):
    """MCD, model-consistency-based defense (Sun et al., VagueGAN paper, 2024): over a period of rounds a
    client's models should stay in one place and move about as much as everyone else's.

    Implemented: 2-D PCA of the round's updates; per client and period the centroid of its 2-D points and
    the mean distance to that centroid (its footprint); baseline clients are those whose two metrics lie
    within Omega1 and Omega2 of the first baseline; abnormality h = lambda1 * |centroid - baseline
    centroid| / baseline footprint + lambda2 * |baseline footprint - footprint|; a client with
    h > delta * median(h) leaves the trusted set and is excluded from then on.
    Deviations: the paper's first baseline is a model the server trains itself on data it trusts; here
    the coordinate-wise median of the clients' metrics stands in for it, which removes the trusted-data
    requirement and with it the guarantee that the baseline is clean. Updates are projected, not models.
    Open in the paper and chosen here: the PCA basis is fitted on the first round of each period and
    kept for that period, without standardization; delta = 2 (the paper gives the range (1, 3)); a client
    with fewer than two points in a period is not judged; exclusion starts in the round of detection and
    is permanent; zero denominators are replaced by 1e-12.
    """
    name, version = "mcd", "1"
    at = (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE)
    needs, acts = frozenset({"uploads"}), frozenset({"select_and_weight"})

    def __init__(self, period: int = 80, omega1: float = 4.0, omega2: float = 2.0, lambda1: float = 1.0,
                 lambda2: float = 2.0, delta: float = 2.0):
        self.period, self.omega1, self.omega2 = period, omega1, omega2
        self.lambda1, self.lambda2, self.delta = lambda1, lambda2, delta

    def run(self, ctx):
        st = ctx.state
        removed = st.setdefault("removed", set())
        if ctx.stage == Stage.SERVER_AGGREGATE:
            out = removed & set(ctx.uploads.clients)
            return ctx.findings(decision=Decision(excluded=out, flags={c: "inconsistent over a period" for c in out}))
        cids = [c for c in ctx.uploads.clients if c not in removed]
        period = ctx.round // self.period
        if st.get("period") != period:
            st.update(period=period, points={}, basis=None)
        if len(cids) < 3:
            return ctx.findings(evidence={"skipped": "fewer than 3 trusted clients"})
        X = update_matrix(ctx.uploads, cids)
        if st["basis"] is None:
            _, comp, _ = transform.pca(X, 2)
            st["basis"] = (X.mean(0), comp)
        mean, comp = st["basis"]
        for c, p in zip(cids, (X - mean) @ comp.T):
            st["points"].setdefault(c, []).append(p)
        if (ctx.round + 1) % self.period:
            return ctx.findings(evidence={"buffered": len(cids), "period": period})
        judged = [c for c, pts in st["points"].items() if len(pts) >= 2 and c not in removed]
        if len(judged) < 3:
            return ctx.findings(evidence={"skipped": "fewer than 3 clients with two points in the period"})
        cen = torch.stack([torch.stack(st["points"][c]).mean(0) for c in judged])
        foot = torch.stack([(torch.stack(st["points"][c]) - cen[i]).norm(dim=1).mean() for i, c in enumerate(judged)])
        c0, d0 = robust.coordinate_median(cen), foot.median().clamp_min(1e-12)
        base = ((cen - c0).norm(dim=1) / d0 < self.omega1) & ((foot - d0).abs() / d0 < self.omega2)
        if not base.any():
            return ctx.findings(evidence={"skipped": "no baseline clients"})
        cb, db = cen[base].mean(0), foot[base].mean().clamp_min(1e-12)
        h = self.lambda1 * (cen - cb).norm(dim=1) / db + self.lambda2 * (db - foot).abs()
        bar = self.delta * float(h.median())
        out = {c for c, v in zip(judged, h.tolist()) if v > bar}
        removed |= out
        return ctx.findings(scores={c: v for c, v in zip(judged, h.tolist())},
                            evidence={"threshold": bar, "baseline_clients": int(base.sum()), "removed": sorted(out)})


class CRFL(GuardPlugin):
    """CRFL (Xie et al., ICML 2021), training-time part: clip the aggregated model's norm and add
    Gaussian noise before it is broadcast again.

    Implemented: Clip_rho(w) = w / max(1, |w| / rho_t) with rho_t = rho0 + rho_slope * t, then noise
    N(0, sigma^2) on every entry; in the round given as `last_round` only the clipping.
    Not implemented: the test-time parameter smoothing and the certified radius, which need a classifier
    with a known Lipschitz constant (the paper derives it for multi-class logistic regression only).
    Deviation: the norm is that of the LoRA factors, the only parameters the server holds. The paper's
    rho and sigma were chosen for its small models; the defaults here are its MNIST values and are not
    tuned for LoRA. With LoRA's zero-initialized B a sigma of 0.01 is large compared with early updates.
    """
    name, at, version = "crfl", Stage.SERVER_POST_AGGREGATE, "1"
    needs, acts = frozenset({"aggregate"}), frozenset({"replace_global"})

    def __init__(self, rho0: float = 2.0, rho_slope: float = 0.1, sigma: float = 0.01, last_round: int | None = None):
        self.rho0, self.rho_slope, self.sigma, self.last_round = rho0, rho_slope, sigma, last_round

    def run(self, ctx):
        rho = self.rho0 + self.rho_slope * (ctx.round + 1)
        new, factor = update.clip_state_norm(ctx.aggregate.result, rho)
        noisy = self.sigma > 0 and ctx.round != self.last_round
        if noisy:
            new = update.add_gaussian_noise(new, self.sigma, torch.Generator().manual_seed(int(ctx.rng.integers(2**31))))
        return ctx.findings(proposals={"replacement": new}, evidence={"rho": rho, "clip_factor": factor, "noise": noisy})


class SafeFedLLMClientLevel(GuardPlugin):
    """Safe-FedLLM, Client-Level (2026): a frozen linear probe scores each uploaded LoRA.

    Implemented: probe feature (first-layer B differences, L2-normalized); malicious probability
    s = sigmoid(a.x + c); instantaneous factor 1 - g(s) with the two-stage calibration; mean over the
    rounds the client took part in; factors frozen after `freeze_after` rounds; the round is skipped
    when the mean factor of the sampled clients is below tau_skip; otherwise weights n_i * w_i.
    Resource `lora_probe`: a probe as returned by fedguard.ops.probe.fit_logistic, trained offline on
    labelled benign and malicious LoRA differences. Training it is the caller's job. Optional resource
    `initial_lora`: the LoRA all clients started from (B_0).
    Open in the paper and chosen here: whether B_0 is the very first LoRA or the round's starting point.
    Without `initial_lora` the round's broadcast LoRA is used, i.e. the feature is this round's change.
    The paper's Step-Level and Shadow-Level variants are separate (see SafeFedLLMStep* below; Shadow-Level
    needs a second training branch on the client and is not implemented).
    """
    name, version = "safe_fedllm_client", "1"
    at = (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE)
    needs, acts = frozenset({"uploads", "reports"}), frozenset({"select_and_weight"})
    resources = frozenset({"lora_probe"})

    def __init__(self, k: float = 10.0, tau_skip: float = 0.2, freeze_after: int = 20, initial_lora: dict | None = None):
        self.k, self.tau_skip, self.freeze_after, self.initial_lora = k, tau_skip, freeze_after, initial_lora

    def run(self, ctx):
        st = ctx.state
        hist, frozen = st.setdefault("factors", {}), st.setdefault("frozen", {})
        if ctx.stage == Stage.SERVER_RECEIVE:
            up = ctx.uploads
            ref = self.initial_lora if self.initial_lora is not None else up.base_state()
            p = ctx.resource("lora_probe")
            st["rounds_seen"] = st.get("rounds_seen", 0) + 1
            feats = {}
            for c in up.clients:
                s = float(probe.apply_logistic(p, first_layer_b_feature(up.state(c), ref)[None, :])[0])
                if st["rounds_seen"] <= self.freeze_after:
                    hist.setdefault(c, []).append(1.0 - two_stage_calibration(s, self.k))
                    frozen[c] = sum(hist[c]) / len(hist[c])
                feats[c] = {"malicious_probability": s, "safety_factor": frozen.get(c, 1.0 - two_stage_calibration(s, self.k))}
            st["current"] = {c: f["safety_factor"] for c, f in feats.items()}
            return ctx.findings(features=feats, scores={c: f["malicious_probability"] for c, f in feats.items()})
        w = st.get("current", {})
        cids = [c for c in ctx.uploads.clients if c in w]
        if not cids:
            return ctx.findings()
        if sum(w[c] for c in cids) / len(cids) < self.tau_skip:
            return ctx.findings(decision=Decision(excluded=set(cids), flags={c: "round skipped: mean safety factor below tau_skip" for c in cids}))
        n = ctx.reports.values("num_examples")
        weights = {c: n.get(c, 1.0) * w[c] for c in cids}
        return ctx.findings(decision=Decision(weights={c: v for c, v in weights.items() if v > 0},
                                              excluded={c for c, v in weights.items() if v <= 0}))


class SafeLoRA(GuardPlugin):
    """Safe LoRA (Hsu et al., NeurIPS 2024): project LoRA updates that drift away from the alignment
    subspace back onto it.

    Per LoRA module with an alignment matrix V = W_aligned - W_unaligned: the projector onto the column
    space of V (`exact=True`, C = V (V^T V)^-1 V^T, computed through a QR factorization) or the paper's
    fast form C = V V^T / ||V||_F; cosine between the update B A and C B A; modules whose cosine is
    below tau are replaced by their projection.
    Resource `alignment`: {LoRA module prefix: V}, each V of shape (d_out, d_in), computed by the caller
    from a pair of aligned and unaligned checkpoints.
    Open in the paper and chosen here: how the projected, dense update gets back into LoRA factors.
    Since C B A = (C B) A, only B is replaced by C B, which keeps the rank and the factor shapes exactly.
    Runs on the aggregated global LoRA here; the paper applies it to a finished fine-tune.
    """
    name, at, version = "safe_lora", Stage.SERVER_POST_AGGREGATE, "1"
    needs, acts = frozenset({"aggregate"}), frozenset({"replace_global"})
    resources = frozenset({"alignment"})

    def __init__(self, tau: float = 0.35, exact: bool = True):
        self.tau, self.exact = tau, exact

    def run(self, ctx):
        result = ctx.aggregate.result
        alignment = ctx.resource("alignment")
        new, feats = dict(result), {}
        for module, V in alignment.items():
            if module + _A not in result or module + _B not in result:
                continue
            A, B, V = result[module + _A].double(), result[module + _B].double(), V.double()
            if self.exact:
                Q, R = torch.linalg.qr(V)
                Q = Q[:, torch.diagonal(R).abs() > 1e-10 * torch.diagonal(R).abs().max().clamp_min(1e-300)]
                CB = Q @ (Q.T @ B)
            else:
                CB = V @ (V.T @ B) / V.norm().clamp_min(1e-300)
            dw, pw = LowRank.lora(B, A), LowRank.lora(CB, A)
            den = math.sqrt(dw.norm_sq() * pw.norm_sq())
            cos = dw.inner(pw) / den if den > 0 else 0.0
            feats[module] = {"cosine": cos, "projected": float(cos < self.tau)}
            if cos < self.tau:
                new[module + _B] = CB.to(result[module + _B].dtype)
        changed = [m for m, f in feats.items() if f["projected"]]
        return ctx.findings(features=feats, scores={m: 1 - f["cosine"] for m, f in feats.items()},
                            proposals={"replacement": new} if changed else {}, evidence={"projected_modules": changed})
