# plugin.py
"""FedGT: malicious-client identification from overlapping group tests (Xie et al., arXiv:2305.05506).

One server-side plugin, at SERVER_AGGREGATE. The class docstring says which steps of the paper are
implemented, where this port deviates from it and what it needs from the deployment.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import cluster, states, transform
from fedguard.ops.geometry import pairwise_sq_distances


def lora_modules(state: dict) -> list:
    """Module prefixes of a LoRA state dict that carry both factors, in a stable order.

    fedguard.views.uploads.lora_modules computes the same thing, but a plugin may only import the modules
    the porting rules allow and views is not among them, so this is rebuilt from ops.states.module_info.
    """
    seen: dict = {}
    for key in state:
        info = states.module_info(key)
        if info["factor"]:
            seen.setdefault(info["module"], set()).add(info["factor"])
    return sorted(module for module, factors in seen.items() if factors == {"A", "B"})


def _depth(name: str) -> int:
    """Layer index of a module prefix, -1 when the name carries no layer number."""
    layer = states.module_info(name)["layer"]
    return -1 if layer is None else int(layer)


def dunn_index(points: torch.Tensor, labels: torch.Tensor) -> float:
    """Dunn index of a partition, on squared Euclidean distances as the paper writes it.

    The smallest squared distance between two cluster centers over the largest squared distance inside a
    cluster. 0.0 when the centers of two clusters coincide, and +inf when the centers are apart while no
    cluster holds two points; the paper leaves both cases undefined.
    """
    ids = [int(c) for c in labels.unique() if c >= 0]
    if len(ids) < 2:
        return 0.0
    points = points.double()
    centers = torch.stack([points[labels == c].mean(dim=0) for c in ids])
    iu = torch.triu_indices(len(ids), len(ids), offset=1)
    between = float(pairwise_sq_distances(centers)[iu[0], iu[1]].min())
    within = 0.0
    for c in ids:
        own = points[labels == c]
        if own.shape[0] > 1:
            within = max(within, float(pairwise_sq_distances(own).max()))
    if within == 0.0:
        return float("inf") if between > 0.0 else 0.0
    return between / within


def trellis_llr(A: torch.Tensor, t: torch.Tensor, delta: float, p: float) -> torch.Tensor:
    """A posteriori LLRs of the defect vector from the trellis of the assignment matrix (Eq. (17)).

    A is the (m, n) 0/1 assignment matrix. Bit i of a state is group i of the partial syndrome, so depth
    l has 2**m states; from any state s the edge labelled 0 goes to s and the edge labelled 1 goes to
    s | column(l). gamma is 1 - delta on a 0 edge and delta on a 1 edge, and the states at depth n are
    scored by the factorized BSC likelihood of t. Returns (n,), entry l being
    log(sum over the 0 edges of alpha * gamma * beta) - log(the same over the 1 edges); alpha and beta are
    rescaled at every depth, which cancels in the difference of the two sums.
    """
    m, n = A.shape
    size = 1 << m
    columns = [int(sum(int(A[i, j]) << i for i in range(m))) for j in range(n)]
    index = torch.arange(size)
    bits = ((index[:, None] >> torch.arange(m)[None, :]) & 1).bool()
    agree = bits == t.bool().flatten()[None, :]
    beta = torch.where(agree, 1.0 - p, p).prod(dim=1).double()
    betas = [None] * (n + 1)
    betas[n] = beta / beta.sum()
    for j in range(n - 1, -1, -1):
        step = (1.0 - delta) * betas[j + 1] + delta * betas[j + 1][index | columns[j]]
        betas[j] = step / step.sum()
    alpha = torch.zeros(size, dtype=torch.float64)
    alpha[0] = 1.0
    out = []
    for j in range(n):
        after = betas[j + 1]
        plain = float((alpha * (1.0 - delta) * after).sum())
        defect = float((alpha * delta * after[index | columns[j]]).sum())
        out.append(math.log(max(plain, 1e-300)) - math.log(max(defect, 1e-300)))
        step = (1.0 - delta) * alpha
        alpha = step.index_add(0, index | columns[j], delta * alpha)
        alpha = alpha / alpha.sum()
    return torch.tensor(out, dtype=torch.float64)


class FedGT(GuardPlugin):
    """FedGT (Xie et al., arXiv:2305.05506): the server clusters the aggregates of overlapping test groups,
    turns the clustering into one binary test per group, decodes the defect vector of the clients from
    that test vector with a trellis forward-backward over the assignment matrix, and excludes the clients
    it flags. FedGT-Delta thresholds the a posteriori LLRs with the offline Neyman-Pearson offset;
    FedGT-n_hat_m takes the n_hat_m smallest LLRs instead.

    Resource `assignment`: {"matrix": the (m, n) 0/1 assignment matrix, "clients": the client ids of its n
        columns, in column order}. The paper uses the parity-check matrix of a BCH code (n = 15, m = 8) or
        of a (30, 18) cyclic code.
    Resource `null_table`: (n_m_max + 1, m + 1) tensor of Pr(Z = z | N_m = n_m), computed offline from the
        assignment matrix.
    Resource `delta_table`: (n_m_max + 1,) tensor of the offline offset Delta-hat(n_m) of Eq. (15); the
        FedGT-n_hat_m decoder is the only one that does not need it.
    Resource `validation`: the server-side quasi-dataset (100 samples in the paper). With the default
        metrics it is a sequence of {"prompt": str, "candidates": [str, ...], "gold": int} items, plus
        "source": True on the items of the attacked source label for metric = source_recall; with
        metric = loss it is whatever the handle `losses` accepts.

    Needs a server-side model handle: the host runs no model on the server side, so the defender has to
    pass one (`probe=`). Without it the plugin reports a skip and excludes nobody.

    Implemented: R4 the utility of every group aggregate: the paper metrics top-1 accuracy, balanced
    accuracy and source label recall, from the candidate log-probabilities of the model handle, or the
    negative mean loss when metric = loss; R5 the first principal component of the readout module of every
    group aggregate; R6 the two features per group; R7 the k-means sweep over k = 1..k_max with
    k_max = min(m, largest group size + 1) of Eq. (4); R8 the silhouette from squared Euclidean distances;
    R9 the Dunn index; R10 the Eq. (5) rule; R11 the cluster of highest mean utility is negative; R12 the
    count of negative tests; R13 the maximum-likelihood estimate of n_m from the null table; R14 the
    prevalence, with the paper rule that n_m = 0 ends the pipeline with everybody benign; R15 and R16 the
    trellis of the assignment matrix and the forward-backward LLRs of Eq. (17); R17 the FedGT-Delta
    threshold of Eqs. (9) and (10); R17b the FedGT-n_hat_m top-k rule of Eq. (16); R18 exclusion of the
    flagged clients through the select_and_weight decision of this round.

    Deviations: the group aggregates are built here from the cleartext per-client uploads with
    ops.states.weighted_average, so the secure aggregation that the paper reveals only group aggregates
    through is not modeled and its privacy premise does not hold in this port; a deployment that hides
    uploads refuses the plugin. A group aggregate is a factor-wise mean of LoRA states, whose product is not
    the mean of the products, and it is that mean, not the paper group aggregate of full models, which is
    passed to the model handle and to the principal component. The utility is a ranking accuracy over the
    candidate completions of the validation resource, not the accuracy of a classifier head, which the
    ModelHandle protocol does not expose; a candidate is scored by the handle mean per-token
    log-probability, so candidates of different lengths are compared after that normalization. The first
    principal component is taken over the LoRA factors of one readout module, not over the fully connected
    weight matrix of the full model.

    Not implemented: the offline design of the assignment matrix and of the null and offset tables
    (Eqs. (3), (11) and (15)) and the Delta-hat search, all of which the paper does outside training and
    which enter here as resources; belief propagation for assignment matrices too large for the
    forward-backward (R16b), for which the paper gives no algorithm; the group-testing round itself, which
    the paper spends on m group aggregations and on no ordinary global model, while this plugin runs inside
    a normal round; anything on the client side, which FedGT does not change, including the secure
    aggregation that forms the group aggregates.

    Open in the paper and chosen here: the metric defaults to top-1 accuracy, the paper choice for
    untargeted attacks, and the attacked source label has to be marked in the validation resource for
    source_recall; candidates are compared by their mean per-token log-probability and ties go to the first
    candidate; the two features are standardized to zero mean and unit variance before clustering, since the
    paper does not say whether they are normalized or weighted; distances are squared Euclidean, as the
    paper formulas print them; the silhouette needs two clusters, so s(1) = 0 and a k-means run that
    collapses to fewer than k clusters is not scored; the Dunn index of a partition whose clusters all hold
    one point is +inf when the centers are apart and 0 when they coincide, and ties on the largest Dunn
    index go to the smallest k; the negative cluster is the one with the largest mean utility, ties to the
    lowest cluster label, and a single cluster makes every test negative; the maximum-likelihood estimate of
    n_m takes the smallest n_m on a tie; k-means keeps the library defaults and draws its seed from
    ctx.rng; the readout module is the uploaded module of the highest layer index unless readout_module
    names another; the assignment matrix has to cover exactly the clients of the round, otherwise the plugin
    reports a skip; p = 0.05 and s_thres = 0.6 are the paper values used as defaults.

    Cost: per test round one scoring pass of the validation set per group through the model handle, so
    m * |validation| * |candidates| forward samples for the accuracy metrics (8 * 100 * candidates in the
    paper setting) and m * |validation| for the loss metric; m k-means runs of at most k_max clusters over
    m two-dimensional points; one forward-backward pass over n * 2**m trellis states.
    """
    name, at, version = "fedgt", Stage.SERVER_AGGREGATE, "1"
    needs = frozenset({"uploads", "model_handle"})
    resources = frozenset({"assignment", "null_table", "delta_table", "validation"})
    acts = frozenset({"select_and_weight"})

    def __init__(self, decoder: str = "delta", metric: str = "accuracy", test_round: int | None = None,
                 s_thres: float = 0.6, p: float = 0.05, restarts: int = 5, readout_module: str | None = None,
                 standardize: bool = True):
        if decoder not in ("delta", "count"):
            raise ValueError("decoder must be delta or count")
        if metric not in ("accuracy", "balanced_accuracy", "source_recall", "loss"):
            raise ValueError("unknown utility metric")
        self.decoder, self.metric, self.test_round = decoder, metric, test_round
        self.s_thres, self.p, self.restarts = s_thres, p, restarts
        self.readout_module, self.standardize = readout_module, standardize
        wanted = {"assignment", "null_table", "validation"} | ({"delta_table"} if decoder == "delta" else set())
        self.resources = frozenset(wanted)

    def _readout(self, state: dict) -> str | None:
        """The uploaded module with the highest layer index, ties broken by name; None when there is none."""
        modules = lora_modules(state)
        return max(modules, key=lambda name: (_depth(name), name)) if modules else None

    def _score(self, handle, samples) -> float:
        """Utility of the LoRA the handle currently holds, on the validation set."""
        if self.metric == "loss":
            losses = [float(x) for x in handle.losses(samples)]
            return -sum(losses) / len(losses) if losses else 0.0
        prompts, targets = [], []
        for item in samples:
            for candidate in item["candidates"]:
                prompts.append(item["prompt"])
                targets.append(candidate)
        values = [float(x) for x in handle.logprob(prompts, targets)]
        right, at = [], 0
        for item in samples:
            count = len(item["candidates"])
            row = values[at:at + count]
            at += count
            pick = max(range(count), key=lambda c: (row[c], -c)) if count else -1
            right.append(pick == int(item["gold"]))
        if self.metric == "source_recall":
            keep = [i for i, item in enumerate(samples) if item.get("source")]
        else:
            keep = list(range(len(samples)))
        if not keep:
            return 0.0
        if self.metric == "balanced_accuracy":
            classes = sorted({int(samples[i]["gold"]) for i in keep})
            return sum(sum(1.0 for i in keep if int(samples[i]["gold"]) == c and right[i])
                       / max(sum(1 for i in keep if int(samples[i]["gold"]) == c), 1) for c in classes) / len(classes)
        return sum(1.0 for i in keep if right[i]) / len(keep)

    def run(self, ctx):
        st = ctx.state
        if self.test_round is not None and ctx.round != self.test_round:
            flagged = set(st.get("flagged", ()))
            return ctx.findings(decision=Decision(
                excluded=flagged,
                flags={c: "fedgt: flagged by the group test of round %s" % st.get("round") for c in flagged}),
                evidence={"reused_from_round": st.get("round"), "flagged": sorted(flagged)})

        def skip(why):
            return ctx.findings(evidence={"skipped": why})

        try:
            handle = ctx.view("model_handle")
        except LookupError:
            return skip("no server-side model handle, so the utility of the group aggregates cannot be measured")
        assignment = ctx.resource("assignment")
        A = torch.as_tensor(assignment["matrix"], dtype=torch.float64)
        columns = list(assignment["clients"])
        cids = ctx.uploads.clients
        if A.dim() != 2 or A.shape[1] != len(columns):
            return skip("the assignment matrix and its client list do not match")
        if sorted(cids) != sorted(columns):
            return skip("the clients of this round do not match the columns of the assignment matrix")
        A = A[:, [columns.index(c) for c in cids]]
        m, n = int(A.shape[0]), int(A.shape[1])
        members = [[j for j in range(n) if float(A[i, j]) > 0.0] for i in range(m)]
        if any(len(group) == 0 for group in members):
            return skip("the assignment matrix has an empty test group")

        up = ctx.uploads
        groups = [states.weighted_average([up.state(cids[j]) for j in group]) for group in members]
        samples = ctx.resource("validation")
        utility = []
        for group in groups:
            with handle.lora(group):
                utility.append(self._score(handle, samples))

        module = self.readout_module or self._readout(up.base_state())
        keys = [module + ".lora_A.weight", module + ".lora_B.weight"] if module else []
        if not keys or any(k not in groups[0] for k in keys):
            return skip("the readout module %s is not part of the uploaded LoRA" % module)
        component = transform.pca(states.stack(groups, keys), 1)[0][:, 0]
        features = torch.stack([torch.tensor(utility, dtype=torch.float64), component.double()], dim=1)
        if self.standardize:
            spread = features.std(dim=0)
            features = (features - features.mean(dim=0)) / torch.where(spread > 0.0, spread, torch.ones_like(spread))

        distances = pairwise_sq_distances(features)
        k_max = min(m, max(len(group) for group in members) + 1)
        labels_of, s_of = {}, {}
        for k in range(1, k_max + 1):
            labels = cluster.kmeans(features, k, seed=int(ctx.rng.integers(1 << 31)), restarts=self.restarts)[0]
            labels_of[k], s_of[k] = labels, 0.0
            if k >= 2 and len([int(c) for c in labels.unique() if c >= 0]) >= 2:
                s_of[k] = float(cluster.silhouette(distances, labels))
        s_max = max(s_of.values())
        dunn_of = {k: dunn_index(features, labels_of[k]) for k in labels_of}
        if s_max >= self.s_thres:
            k_hat = max(labels_of, key=lambda k: (dunn_of[k], -k))
        else:
            k_hat = 1

        labels = labels_of[k_hat]
        clusters = sorted({int(c) for c in labels})
        means = {c: sum(utility[i] for i in range(m) if int(labels[i]) == c) / max(sum(1 for i in range(m) if int(labels[i]) == c), 1)
                 for c in clusters}
        negative = max(clusters, key=lambda c: (means[c], -c))
        t = torch.tensor([0 if int(labels[i]) == negative else 1 for i in range(m)], dtype=torch.long)
        z_hat = int((t == 0).sum())

        table = torch.as_tensor(ctx.resource("null_table"), dtype=torch.float64)
        if table.dim() != 2 or z_hat >= table.shape[1]:
            return skip("the null table does not cover z = %d" % z_hat)
        n_hat = int(torch.argmax(table[:, z_hat]))
        llr = torch.zeros(n, dtype=torch.float64)
        lam = float("nan")
        flagged: set = set()
        if n_hat > 0:
            delta = n_hat / n
            llr = trellis_llr(A, t, delta, self.p)
            if self.decoder == "delta":
                offsets = torch.as_tensor(ctx.resource("delta_table"), dtype=torch.float64).flatten()
                if n_hat >= offsets.numel() or not bool(torch.isfinite(offsets[n_hat])):
                    return skip("the offline offset table has no finite entry for n_m = %d" % n_hat)
                lam = float(offsets[n_hat]) + math.log((1.0 - delta) / delta)
                flagged = {cids[i] for i in range(n) if float(llr[i]) < lam}
            else:
                order = sorted(range(n), key=lambda i: (float(llr[i]), i))
                flagged = {cids[i] for i in order[:n_hat]}
                lam = float(llr[order[n_hat - 1]])
        st["flagged"], st["round"] = sorted(flagged), ctx.round
        llr_of = {cids[i]: float(llr[i]) for i in range(n)}
        return ctx.findings(
            scores={cid: -value for cid, value in llr_of.items()},
            evidence={"t": [int(x) for x in t], "z_hat": z_hat, "n_hat": n_hat, "k_hat": k_hat, "s_max": s_max,
                      "decoder": self.decoder, "metric": self.metric, "readout": module, "lambda": lam,
                      "llr": llr_of, "s_of_k": {str(k): s_of[k] for k in sorted(s_of)},
                      "dunn_of_k": {str(k): dunn_of[k] for k in sorted(dunn_of)},
                      "groups": {str(i): [cids[j] for j in group] for i, group in enumerate(members)},
                      "utility": {str(i): utility[i] for i in range(m)}, "flagged": sorted(flagged)},
            decision=Decision(excluded=flagged,
                              flags={c: "fedgt: LLR %.3f below the threshold %.3f" % (llr_of[c], lam) for c in flagged}))
