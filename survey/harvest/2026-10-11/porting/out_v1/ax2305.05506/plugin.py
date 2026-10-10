# plugin.py
"""FedGT: overlapping group testing with a trellis decoder, as a fedguard server plugin.

The method is Karakas, Andreina, Dang, Serrano, Komninos and Picek, "FedGT: Identification of Malicious
Clients in Federated Learning with Secure Aggregation", arXiv:2305.05506. This file ports the server side
of it onto this library. Read the class docstring for what is implemented, what is left out and where
this port had to deviate from the paper.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import cluster, geometry, states, transform


def dunn_index(X: torch.Tensor, labels: torch.Tensor) -> float:
    """Dunn index of a clustering, from squared Euclidean distances (the paper writes the norms squared):
    the smallest squared distance between two cluster centers over the largest squared diameter of one
    cluster. 0.0 when fewer than two clusters hold points or no cluster holds two of them."""
    X = X.double()
    ids = [int(c) for c in labels.unique() if int(c) >= 0]
    if len(ids) < 2:
        return 0.0
    D = geometry.pairwise_sq_distances(X)
    centers = torch.stack([X[labels == c].mean(dim=0) for c in ids])
    between = geometry.pairwise_sq_distances(centers)
    between.fill_diagonal_(float("inf"))
    spread = 0.0
    for c in ids:
        idx = (labels == c).nonzero().flatten()
        if idx.numel() > 1:
            spread = max(spread, float(D[idx][:, idx].max()))
    return float(between.min()) / spread if spread > 0 else 0.0


def trellis_llr(A: torch.Tensor, t: torch.Tensor, prevalence: float, p: float) -> torch.Tensor:
    """A posteriori LLR of every client, Eq. (17): one forward-backward pass over the trellis of A.

    Depth l of the trellis holds the partial syndrome OR over the first l clients: a client with d = 0
    keeps the syndrome, a client with d = 1 unions its own column into it, so every state has exactly two
    outgoing edges, the d = 0 edge carrying the branch metric 1 - prevalence and the d = 1 edge prevalence.
    The states at depth n are weighted by the factorized binary symmetric channel likelihood Q(t | s) with
    flip probability p. alpha and beta are rescaled at every depth by their maximum; the same factor
    multiplies both sums of one LLR, so it cancels. Larger values mean more likely benign."""
    m, n = int(A.shape[0]), int(A.shape[1])
    size = 1 << m
    cols = [sum(int(A[i, c].item()) << i for i in range(m)) for c in range(n)]
    t_int = sum(int(t[i].item()) << i for i in range(m))
    hamming = torch.tensor([bin(s ^ t_int).count("1") for s in range(size)], dtype=torch.float64)
    likelihood = (p ** hamming) * ((1.0 - p) ** (m - hamming))
    state = torch.arange(size)
    alpha = torch.zeros(n + 1, size, dtype=torch.float64)
    alpha[0, 0] = 1.0
    for l in range(1, n + 1):
        pushed = torch.zeros(size, dtype=torch.float64)
        pushed.index_add_(0, state | cols[l - 1], alpha[l - 1] * prevalence)
        alpha[l] = alpha[l - 1] * (1.0 - prevalence) + pushed
        alpha[l] /= alpha[l].max().clamp_min(1e-300)
    beta = torch.zeros(n + 1, size, dtype=torch.float64)
    beta[n] = likelihood / likelihood.max().clamp_min(1e-300)
    for l in range(n, 0, -1):
        beta[l - 1] = beta[l] * (1.0 - prevalence) + beta[l][state | cols[l - 1]] * prevalence
        beta[l - 1] /= beta[l - 1].max().clamp_min(1e-300)
    llr = torch.zeros(n, dtype=torch.float64)
    for l in range(1, n + 1):
        zero = float((alpha[l - 1] * (1.0 - prevalence) * beta[l]).sum())
        one = float((alpha[l - 1] * prevalence * beta[l][state | cols[l - 1]]).sum())
        llr[l - 1] = math.log(max(zero, 1e-300)) - math.log(max(one, 1e-300))
    return llr


class FedGT(GuardPlugin):
    """FedGT (Karakas et al., 2023; arXiv:2305.05506): test overlapping groups of clients, decode which
    clients are malicious, and exclude them.

    Implemented: the m overlapping test groups come from the offline-designed assignment matrix; the m
    group aggregates are formed in factor space; every group aggregate gets a utility (the negative mean
    loss of the server model on the defender validation set) and the first-principal-component score of
    its factor-space update; the m two-dimensional points are clustered with k-means for every k from 2 to
    k_max = min(m, largest group size + 1), the case k = 1 being what the silhouette threshold decides;
    the number of clusters is the smallest k with the largest Dunn index once the best silhouette score
    reaches s_thres; every group outside the highest-utility cluster is declared positive; the number of
    negative tests gives the maximum-likelihood estimate n_hat_m; the trellis of the assignment matrix is
    decoded by the forward-backward algorithm with the factorized binary symmetric channel likelihood and
    the branch metrics 1 - delta and delta; both published decision rules are available, the Neyman-Pearson
    threshold of FedGT-Delta (decoder="delta", the default) and the n_hat_m smallest a posteriori LLRs of
    FedGT-n_hat_m (decoder="count"); the flagged clients are excluded from the round through
    select_and_weight, and with test_round set the later rounds reuse that flagged set without spending a
    model pass, which is the protocol of the paper experiments.

    Resource `assignment`: dict with `matrix`, the offline-designed (m, n) 0/1 tensor (the paper takes a
    parity-check matrix of a code; any matrix with distinct nonzero columns decodes the same way), and
    `clients`, the list of the n client ids that index its columns.
    Resource `null_distribution`: dict with `n_m_max` and `p`, the (n_m_max + 1, m + 1) tensor
    Pr(Z = z | N_m = n_m) of the number of negative tests, computed offline from A.
    Resource `delta_table`: the (n_m_max + 1,) tensor of the offline Neyman-Pearson offsets of Eq. (15).
    Resource `validation`: the small server-side quasi-dataset of the paper, as a sequence of samples the
    server model handle accepts in losses.

    Deviations: the paper is a secure-aggregation method, its server sees the m group aggregates and never
    one client model. This library hands a server plugin the per-client uploads or nothing, so the port
    forms the group aggregates from `uploads` itself and only makes sense in a deployment without secure
    aggregation. A group aggregate is a sum of rank-r LoRA products and has no state dict of the broadcast
    rank, so the model pass and the principal component both use the factor-wise sum of the members, whose
    product is not the sum of their products. The paper utility (source label recall under a targeted
    attack, top-1 accuracy, balanced accuracy) cannot be computed at all through the model handle protocol,
    which has no prediction or label call; the negative mean training loss on the validation set stands in
    for it. The paper takes the principal component of the fully connected layer; a LoRA state dict has no
    layer to choose, so the principal component is taken over every factor.

    Not implemented: the belief-propagation decoder that the paper proposes for assignment matrices too
    large for the forward-backward pass (the trellis here holds 2^m states); the offline design of the
    assignment matrix, the offline distribution of the number of negative tests and the offline search for
    the offsets, which enter as resources; secure aggregation itself, which belongs to the host protocol.

    Open in the paper and chosen here: the paper does not say whether the two features are standardized,
    so each column of the two-dimensional points is centered and scaled to unit standard deviation before
    clustering (feature_scale); k-means uses the library seeding with a seed drawn from ctx.rng; the number
    of clusters is the smallest k with the largest Dunn index, and the highest-utility cluster is the one
    with the largest mean utility, ties broken toward the lowest cluster label; the silhouette is computed
    for k >= 2 only, since it is undefined for one cluster, and a k-means run that collapses to fewer than
    k clusters is not scored at all; the Dunn index is 0.0 when no cluster holds two points; every client of
    the assignment matrix has to take part in the round, otherwise the plugin reports a skip, because the
    offline tables are tied to that n; test_round defaults to None, meaning the test runs in every round the
    plugin is mounted in, which the paper allows at the price of the extra communication.

    Cost: one forward pass of the server model over the validation set per test group in every round the
    test runs (m passes, with m = 8 or 12 and 100 samples in the paper; no pass at all in the rounds that
    reuse the flagged set), a k-means sweep of at most min(m, largest group size + 1) runs on m points, and
    one forward-backward pass over an n-step trellis with 2^m states, which is the exponential part the
    paper itself flags for large assignment matrices."""
    name, at, version = "fedgt", Stage.SERVER_AGGREGATE, "1"
    needs = frozenset({"uploads", "model_handle"})
    resources = frozenset({"assignment", "null_distribution", "delta_table", "validation"})
    acts = frozenset({"select_and_weight"})

    def __init__(self, decoder: str = "delta", p: float = 0.05, s_thres: float = 0.6, feature_scale: bool = True,
                 test_round: int | None = None):
        if decoder not in ("delta", "count"):
            raise ValueError("decoder must be delta (FedGT-Delta) or count (FedGT-n_hat_m)")
        self.decoder, self.p, self.s_thres = decoder, p, s_thres
        self.feature_scale, self.test_round = feature_scale, test_round

    def run(self, ctx):
        if self.test_round is not None and ctx.round != self.test_round:
            flagged = set(ctx.state.get("flagged", ()))
            return ctx.findings(evidence={"skipped": f"the group test runs in round {self.test_round}", "flagged": sorted(flagged)},
                                decision=Decision(excluded=flagged))
        spec = ctx.resource("assignment")
        ids = list(spec["clients"])
        A = spec["matrix"].double()
        m, n = int(A.shape[0]), int(A.shape[1])
        if n != len(ids) or set(ctx.uploads.clients) != set(ids):
            return ctx.findings(evidence={"skipped": "the assignment matrix must cover exactly the clients of the round"})
        column = {c: j for j, c in enumerate(ids)}
        groups = [[c for c in ids if float(A[i, column[c]]) > 0] for i in range(m)]
        if any(not g for g in groups):
            return ctx.findings(evidence={"skipped": "the assignment matrix has an empty test group"})
        table = ctx.resource("null_distribution")
        n_max = int(table["n_m_max"])
        probability = table["p"].double()
        if tuple(probability.shape) != (n_max + 1, m + 1):
            raise ValueError(f"null_distribution p must have shape ({n_max + 1}, {m + 1}), got {tuple(probability.shape)}")

        base = ctx.uploads.base_state()
        deltas = {c: states.delta(ctx.uploads.state(c), base) for c in ids}
        vectors = torch.stack([sum((ctx.uploads.factor_delta(c).double() for c in g)) for g in groups])
        aggregates = []
        for g in groups:
            total = deltas[g[0]]
            for c in g[1:]:
                total = states.add(total, deltas[c])
            aggregates.append(states.add(base, total))

        handle, validation = ctx.model_handle, ctx.resource("validation")
        utility = []
        for state in aggregates:
            with handle.lora(state):
                losses = handle.losses(validation)
            utility.append(-sum(float(x) for x in losses) / max(len(losses), 1))
        util = torch.tensor(utility, dtype=torch.float64)
        first = transform.pca(vectors, 1)[0][:, 0]
        points = torch.stack([util, first], dim=1)
        if self.feature_scale:
            spread = points.std(dim=0, unbiased=False)
            points = (points - points.mean(dim=0)) / torch.where(spread > 0, spread, torch.ones_like(spread))

        distances = geometry.pairwise_sq_distances(points)
        k_max = min(m, max(len(g) for g in groups) + 1)
        fits = {k: cluster.kmeans(points, k, seed=int(ctx.rng.integers(2 ** 31)))[0] for k in range(2, k_max + 1)}
        silhouette = {k: cluster.silhouette(distances, lab) for k, lab in fits.items() if len(lab.unique()) >= 2}
        s_max = max(silhouette.values()) if silhouette else 0.0
        if not silhouette or s_max < self.s_thres:
            k_hat, labels = 1, torch.zeros(m, dtype=torch.long)
        else:
            dunn = {k: dunn_index(points, lab) for k, lab in fits.items() if k in silhouette}
            best = max(dunn.values())
            k_hat = min(k for k, value in dunn.items() if value >= best)
            labels = fits[k_hat]
        means = {int(c): float(util[labels == c].mean()) for c in labels.unique()}
        top = max(means.values())
        highest = min(c for c, value in means.items() if value >= top)
        tests = torch.tensor([0.0 if int(labels[j]) == highest else 1.0 for j in range(m)], dtype=torch.float64)

        z = int((tests == 0).sum())
        n_hat = int(torch.argmax(probability[: n_max + 1, z]))
        evidence = {"k_hat": k_hat, "k_max": k_max, "s_max": s_max, "z": z, "n_hat_m": n_hat,
                    "tests": [int(x) for x in tests], "group_sizes": [len(g) for g in groups],
                    "silhouette": {str(k): round(value, 4) for k, value in silhouette.items()}}
        if n_hat == 0:
            evidence["decoder"] = "not run: n_hat_m = 0, every client is taken as benign"
            ctx.state["flagged"] = []
            return ctx.findings(features={c: {"llr": 0.0} for c in ids}, evidence=evidence, decision=Decision())
        delta = n_hat / n
        llr = trellis_llr(A, tests, delta, self.p)
        if self.decoder == "count":
            order = sorted(range(n), key=lambda i: (float(llr[i]), i))
            flagged = {ids[i] for i in order[:n_hat]}
            evidence["rule"] = f"the {n_hat} smallest a posteriori LLRs"
        else:
            threshold = float(ctx.resource("delta_table").double()[n_hat]) + math.log((1.0 - delta) / delta)
            flagged = {ids[i] for i in range(n) if float(llr[i]) < threshold}
            evidence["rule"] = "Neyman-Pearson threshold"
            evidence["threshold"] = threshold
        evidence["delta_hat"] = delta
        ctx.state["flagged"] = sorted(flagged)
        features = {ids[i]: {"llr": float(llr[i])} for i in range(n)}
        rounded = {c: round(features[c]["llr"], 3) for c in ids}
        flags = {c: f"FedGT flagged this client, a posteriori LLR {rounded[c]}" for c in flagged}
        return ctx.findings(scores={c: -features[c]["llr"] for c in ids}, features=features, evidence=evidence,
                            decision=Decision(excluded=flagged, flags=flags))
