# plugin.py
"""CrowdGuard (Che et al., 2022, arXiv:2210.07714) for federated LoRA fine-tuning: the detection and
filtering of the paper as a pair of plugins, one per side.

The paper validates inside a secure enclave at every client: the server distributes every local model of
the round to every client, each client scores all of them on its own data with the Hidden Layer Backdoor
Inspection Metric (HLBIM), prunes iteratively and returns one binary vote per model; the server aggregates
the votes by stacked clustering, removes the rejected models and averages the survivors equally.
`CrowdGuardServer` ships the uploads of a round to the clients and turns the returning votes into
exclusions; `CrowdGuardValidator` computes the HLBIM and the vote on the local samples of the client.

Resource `label_of` (declared by CrowdGuardValidator): a callable sample -> label over the local
validation samples; the library has no label field in DataView.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import cluster, states, transform

_ALPHA = 0.01
_SERVER = "crowdguard_server"
_CLIENT = "crowdguard_validator"
_METRICS = ("cosine", "euclidean")


# --------------------------------------------------------------------------------------------------
# Statistics: the five significance tests of Alg. 4. fedguard.ops has no hypothesis test and scipy is
# not importable, so the p-values are built here; torch itself does not expose the regularized incomplete
# beta (torch.distributions.StudentT.cdf raises NotImplementedError on torch 2.10).
# --------------------------------------------------------------------------------------------------
def _betacf(a, b, x, iters=200, eps=3e-16):
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, iters + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _t_pvalue(a, b):
    """Two-sided p of the pooled Student t test of equal means; 1.0 when it cannot be run."""
    na, nb = int(a.numel()), int(b.numel())
    if na < 2 or nb < 2:
        return 1.0
    va, vb = float(a.double().var(unbiased=True)), float(b.double().var(unbiased=True))
    pooled = ((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)
    if pooled <= 0.0:
        return 1.0
    t = abs(float(a.double().mean()) - float(b.double().mean())) / math.sqrt(pooled * (1.0 / na + 1.0 / nb))
    df = na + nb - 2
    return _betainc(0.5 * df, 0.5, df / (df + t * t))


def _f_pvalue(a, b):
    """Two-sided p of the F test of equal variances (Alg. 4 line 19); 1.0 when it cannot be run."""
    na, nb = int(a.numel()), int(b.numel())
    if na < 2 or nb < 2:
        return 1.0
    va, vb = float(a.double().var(unbiased=True)), float(b.double().var(unbiased=True))
    if va <= 0.0 or vb <= 0.0:
        return 1.0
    d1, d2 = na - 1, nb - 1
    f = va / vb
    cdf = _betainc(0.5 * d1, 0.5 * d2, d1 * f / (d1 * f + d2))
    return min(1.0, 2.0 * min(cdf, 1.0 - cdf))


def _ks_pvalue(a, b):
    """Two-sided p of the two-sample Kolmogorov-Smirnov test; 1.0 when it cannot be run."""
    na, nb = int(a.numel()), int(b.numel())
    if na < 2 or nb < 2:
        return 1.0
    x = torch.cat([a.double(), b.double()]).sort().values
    ca = (a.double()[None, :] <= x[:, None]).double().mean(dim=1)
    cb = (b.double()[None, :] <= x[:, None]).double().mean(dim=1)
    d = float((ca - cb).abs().max())
    if d <= 0.0:
        return 1.0
    en = math.sqrt(na * nb / (na + nb))
    lam = (en + 0.12 + 0.11 / en) * d
    total = 0.0
    for k in range(1, 101):
        term = 2.0 * (-1.0) ** (k - 1) * math.exp(-2.0 * k * k * lam * lam)
        total += term
        if abs(term) < 1e-10:
            break
    return min(1.0, max(0.0, total))


def _boxplot_outlier(x):
    """True when a point lies outside the 1.5 IQR fences of the boxplot rule (Alg. 4)."""
    q1 = float(torch.quantile(x.double(), 0.25))
    q3 = float(torch.quantile(x.double(), 0.75))
    iqr = q3 - q1
    return bool(((x.double() < q1 - 1.5 * iqr) | (x.double() > q3 + 1.5 * iqr)).any())


def _sigma_outlier(x):
    """True when a point lies outside the two-sided 3-sigma interval (Alg. 4)."""
    if int(x.numel()) < 2:
        return False
    sd = float(x.double().std(unbiased=False))
    if sd <= 0.0:
        return False
    return bool(((x.double() - float(x.double().mean())).abs() > 3.0 * sd).any())


def _significant(pc, alpha):
    """Alg. 4: OR of the five tests; a test that cannot be run on these values is skipped."""
    if int(pc.numel()) < 3:
        return False
    dev = pc.double() - float(pc.double().median())
    upper, lower = pc.double()[dev >= 0.0], pc.double()[dev < 0.0]
    return (_t_pvalue(upper, lower) < alpha or _f_pvalue(upper, lower) < alpha
            or _ks_pvalue(upper, lower) < alpha or _boxplot_outlier(pc) or _sigma_outlier(pc))


def _relative_signed_square(candidate, reference, eps=1e-12):
    """Alg. 1 lines 21-22: |rel - 1| * (rel - 1) with rel = candidate / reference distance.

    A zero reference distance has no ratio in the paper; chosen here: rel = 1 when the candidate distance
    is zero too, and rel = 1 + candidate otherwise.
    """
    cand, ref = candidate.double(), reference.double()
    ratio = cand / torch.clamp(ref, min=eps)
    rel = torch.where(ref > eps, ratio, torch.where(cand > eps, 1.0 + cand, torch.ones_like(cand)))
    return torch.sign(rel - 1.0) * (rel - 1.0) ** 2


def _row_cosine(a, g):
    """Cosine of corresponding rows of two matrices; zero where either row has no norm."""
    a, g = a.double(), g.double()
    den = a.norm(dim=1) * g.norm(dim=1)
    return torch.where(den > 0, (a * g).sum(dim=1) / den.clamp_min(1e-300), torch.zeros_like(den)).clamp(-1, 1)


def _row_distance(a, g):
    """Euclidean distance between corresponding rows of two matrices."""
    return (a.double() - g.double()).norm(dim=1)


def _common_layers(per_model):
    """Names of the layer outputs every model reported as a 2-D (samples, features) tensor."""
    common = None
    for acts in per_model.values():
        names = {name for name, value in acts.items() if int(value.dim()) == 2}
        common = names if common is None else (common & names)
    return sorted(common or [])


def _prune(features, total_models, alpha):
    """Alg. 2 lines 8-28 on one metric: PCA to one component, the five tests, prune the smaller of two
    agglomerative clusters, repeat on the survivors. Returns the row indices flagged as malicious.

    `total_models` is |Lt_i|, the number of models of the round including the own model of the validator,
    used for the safe abort of Alg. 2 line 23.
    """
    pruned = []
    while True:
        alive = [i for i in range(int(features.shape[0])) if i not in pruned]
        if len(alive) < 3:
            break
        pc = transform.pca(features[alive], 1)[0][:, 0]
        if not _significant(pc, alpha):
            break
        labels = cluster.agglomerative(cluster.distances(pc.reshape(-1, 1), metric="euclidean"), 2, linkage="average")
        groups = [[j for j in range(len(alive)) if int(labels[j]) == g] for g in sorted(set(int(v) for v in labels.tolist()))]
        groups.sort(key=lambda g: (len(g), -float(pc[g].abs().mean())))
        small = groups[0]
        flagged = pruned + [alive[j] for j in small]
        if len(flagged) > (total_models - 1) // 2:
            drop = min(small, key=lambda j: float(pc[j]))
            pruned = sorted(set(pruned + [alive[j] for j in small if j != drop]))
            break
        pruned = sorted(set(flagged))
    return pruned


def _aggregated_vote(votes, eps, min_samples):
    """Alg. 3: two agglomerative clusters of the vote vectors, the bigger one read as the benign voters;
    DBSCAN inside it (eps, min_samples) and the largest group of equal votes gives the aggregated vote."""
    n = int(votes.shape[0])
    if n == 1:
        return votes[0].tolist()
    first = cluster.agglomerative(cluster.distances(votes, metric="euclidean"), 2, linkage="average")
    groups = [[i for i in range(n) if int(first[i]) == g] for g in sorted(set(int(v) for v in first.tolist()))]
    groups.sort(key=lambda g: (len(g), float(votes[g].sum())), reverse=True)
    majority = votes[groups[0]]
    if int(majority.shape[0]) == 1:
        return majority[0].tolist()
    inner = cluster.dbscan(cluster.distances(majority, metric="euclidean"), eps=eps, min_samples=min_samples)
    buckets = {}
    for i, label in enumerate(int(v) for v in inner.tolist()):
        if label >= 0:
            buckets.setdefault(label, []).append(i)
    if not buckets:
        return majority[0].tolist()
    best = max(buckets.values(), key=lambda idx: (len(idx), float(majority[idx].sum())))
    return majority[best[0]].tolist()


class CrowdGuardServer(GuardPlugin):
    """CrowdGuard server half (Che et al., 2022): ship the local models of a round to the client-side
    validators, aggregate their votes with stacked clustering and drop the models it rejects.

    Implemented: at SERVER_RECEIVE every upload of the round and the broadcast base it started from are
    flattened and put on the channel to the clients, together with the client list and the round they
    answer (S3, the only way this library moves a model from the server to a client). At SERVER_AGGREGATE
    the votes that came back with the uploads are read (`crowdguard_validator.votes`, one 0/1 per model of
    the pack they name), rows whose round or length does not match the pack are ignored, and the vote
    matrix goes through the stacked clustering of Alg. 3: two agglomerative clusters, the bigger one read
    as the benign voters (line 6), DBSCAN inside it (eps 0.5, min_samples 1, line 9) and the largest group
    of equal votes as the aggregated vote (S14). Clients the aggregated vote rejects are excluded and the
    survivors get weight 1 each, the equal-weight Eq. 1 of the paper (S15-S16); the averaging itself is
    the host aggregation.

    Deviations: the pack reaches the clients at the start of the next round and the votes return with that
    round, so the models of round t are judged in round t+1 and the exclusion lands on round t+1, not on
    the round that produced the models (the library has no server-to-client push after SERVER_RECEIVE).
    The votes are untrusted channel messages, like the votes of the untrusted enclaves of the paper, but
    no attestation backs them here. A round with no votes accepts every client (the paper accepts every
    model of round 0).

    Open in the paper and chosen here: the two clusters of the first layer are compared by size and ties
    by the number of benign (1) votes; DBSCAN runs on Euclidean distances of the binary vectors, where
    eps 0.5 merges only identical votes; the largest DBSCAN group is the aggregated vote and ties take
    the group with more benign votes; a row of the wrong length or with values other than 0/1 is ignored;
    rows naming another pack round are ignored; with no usable row every client keeps weight 1; the voter
    is not weighted by its own report.

    Cost: one flattening of every upload and of the base per round (a copy of the round in memory, as the
    paper server holds the round), O(n^2) on n vote vectors for the clustering; the pack leaves through
    the channel and counts against the attachment limit of the runner (64 MiB by default).
    """
    name, at, version = "crowdguard_server", (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE), "1"
    needs = frozenset({"uploads", "reports"})
    resources = frozenset()
    acts = frozenset({"select_and_weight"})

    def __init__(self, epsilon=0.5, min_samples=1):
        self.epsilon, self.min_samples = float(epsilon), int(min_samples)

    def run(self, ctx):
        if ctx.stage == Stage.SERVER_RECEIVE:
            return self._publish(ctx)
        return self._aggregate(ctx)

    def _publish(self, ctx):
        clients = list(ctx.uploads.clients)
        if not clients:
            return ctx.findings(evidence={"skipped": "no uploads to pack"})
        attachments = {"pack.base": states.flatten(ctx.uploads.base_state())}
        for cid in clients:
            attachments["pack." + cid] = states.flatten(ctx.uploads.state(cid))
        ctx.state["sent"] = ctx.state.get("pending")
        ctx.state["pending"] = {"round": ctx.round, "clients": clients}
        return ctx.findings(messages={"pack_clients": clients, "pack_round": ctx.round}, attachments=attachments)

    def _aggregate(self, ctx):
        current = list(ctx.uploads.clients)
        weights = {cid: 1.0 for cid in current}
        sent = ctx.state.get("sent")
        votes = ctx.uploads.reports.messages(_CLIENT + ".votes")
        rounds = ctx.uploads.reports.messages(_CLIENT + ".pack_round")
        if not sent or not votes:
            return ctx.findings(evidence={"skipped": "no votes for a pack", "voters": len(votes)},
                                decision=Decision(weights=weights))
        pack_round, pack_clients = sent["round"], list(sent["clients"])
        rows, voters = [], []
        for voter in sorted(votes):
            row = votes[voter]
            if rounds.get(voter) != pack_round:
                continue
            if not isinstance(row, list) or len(row) != len(pack_clients) or any(int(x) not in (0, 1) for x in row):
                continue
            rows.append([float(x) for x in row])
            voters.append(voter)
        if not rows:
            return ctx.findings(evidence={"skipped": "no vote row matched the pack", "pack_round": pack_round},
                                decision=Decision(weights=weights))
        aggregated = _aggregated_vote(torch.tensor(rows, dtype=torch.float64), self.epsilon, self.min_samples)
        rejected = [cid for cid, keep in zip(pack_clients, aggregated) if not keep]
        excluded = {cid for cid in rejected if cid in set(current)}
        weights = {cid: 1.0 for cid in current if cid not in excluded}
        flags = {cid: "crowdguard: rejected by the aggregated vote on round " + str(pack_round) for cid in excluded}
        scores = {cid: float(sum(row[i] for row in rows)) for i, cid in enumerate(pack_clients)}
        features = {cid: {"votes_against": scores[cid], "voters": len(rows)} for cid in pack_clients}
        return ctx.findings(scores=scores, features=features,
                            evidence={"pack_round": pack_round, "voters": voters, "aggregated": aggregated,
                                      "rejected": rejected},
                            decision=Decision(excluded=excluded, weights=weights, flags=flags))


class CrowdGuardValidator(GuardPlugin):
    """CrowdGuard client half (Che et al., 2022): score every model of the packed round on the local data
    and return one binary vote per model.

    Implemented: with the pack the server sent (S3), the client loads each candidate LoRA on the model it
    is training through `ModelHandle.lora` and takes the outputs of the submodules the handle reports for
    the local samples (S4: every layer the handle exposes, pool mean). For each sample and layer the
    cosine and the Euclidean distance of that output to the same output of the packed base model are
    formed (S5; the two metrics are analyzed independently), divided by the same distance of the own
    model of the pack (S6), turned into |rel - 1| * (rel - 1) with its sign (S6) and averaged over the
    samples of each label (S7, labels come from the `label_of` resource). The per-label values are
    concatenated label-major into the HLBIM matrix (S8), whose rows are the candidate models except the
    own model (footnote 15: a client does not judge itself); one principal component (S9), the five tests
    at alpha = 0.01 (S10) and the iterative pruning of the smaller of two agglomerative clusters
    (S11-S12) give the models this client rejects. Both metrics are pruned independently and their flags
    are unioned; the result is one 0/1 vote per model of the pack, sent as the channel message
    `crowdguard_validator.votes` together with the round it answers (S13). Training is untouched: no
    loss, gradient or sample is changed.

    Resource `label_of`: a callable sample -> label over the local samples, because DataView carries no
    label field.

    Deviations: the pack is the round before the one being trained, so the validation of round t happens
    in round t+1 (server messages arrive only at the start of a round). The models are LoRA adapters on
    one frozen base, loaded through the handle, not whole DNN parameter sets. Deep layer outputs are the
    pooled outputs of the submodules the handle exposes, not the raw activations of a fixed image
    network; every layer means the predicate that accepts every submodule the handle reports. The
    reference model is the own upload inside the pack, as the paper uses the own model of the validating
    client; a client that is not in the pack cannot validate and sends no vote.

    Not implemented: the secure enclave and the remote attestation (S1) and the encrypted uplink (S2);
    the vote is an ordinary channel message and nothing attests it.

    Open in the paper and chosen here: PCA is fedguard.ops.transform.pca with one component (centered SVD,
    sign fixed by the library); the upper and lower groups of Alg. 4 line 11 are split by the sign of
    value - median, the quantity that line computes; the variance test is the F test of Alg. 4 line 19
    (not the Levene test of footnote 10), two-sided; the boxplot rule is 1.5 IQR and the 3-sigma interval
    is two-sided with the population standard deviation; a test with fewer than two points on a side or
    with zero variance is skipped, not fired; the labelwise mean is the arithmetic mean over the samples
    of the label, labels are compared as strings and only the labels present in the local data exist; the
    HLBIM features are label-major and then layer name in sorted order; where the reference distance is
    zero, rel is 1 when the candidate distance is zero too and 1 + candidate otherwise; the safe abort of
    Alg. 2 line 23 drops the flagged model with the smallest principal component value (MIN of the paper
    is undefined); a model flagged by either metric is voted 0 (footnote 7 leaves their union open); with
    fewer than three candidate models or without a usable layer output nothing is pruned and no vote is
    sent.

    Cost: one forward pass of the local samples through the model per packed model per round (all counted
    by the handle through ModelHandle.activations), plus arithmetic on (samples x layers) and
    (candidates x labels x layers) matrices.
    """
    name, at, version = "crowdguard_validator", Stage.CLIENT_POST_TRAIN, "1"
    needs = frozenset({"data", "model_handle", "reports", "received_model"})
    resources = frozenset({"label_of"})
    acts = frozenset()

    def __init__(self, alpha=_ALPHA, pool="mean", eps=1e-12):
        self.alpha, self.pool, self.eps = float(alpha), pool, float(eps)

    def run(self, ctx):
        pack = self._read_pack(ctx)
        if pack is None:
            return ctx.findings(evidence={"skipped": "no model pack on the channel"})
        clients, pack_round, base_state, candidates = pack
        own = ctx.participants[0]
        if own not in candidates:
            return ctx.findings(evidence={"skipped": "this client is not in the pack"})
        samples = list(ctx.data.samples())
        if len(samples) < 2:
            return ctx.findings(evidence={"skipped": "fewer than two local samples"})
        labels = [str(ctx.resource("label_of")(sample)) for sample in samples]
        handle = ctx.model_handle
        outputs = {}
        for cid in ["__base__"] + list(candidates):
            state = base_state if cid == "__base__" else candidates[cid]
            with handle.lora(state):
                outputs[cid] = handle.activations(samples, select=lambda name: True, pool=self.pool, what="output")
        layers = _common_layers(outputs)
        if not layers:
            return ctx.findings(evidence={"skipped": "the handle reported no usable layer output"})
        order = [cid for cid in clients if cid != own]
        if len(order) < 3:
            return ctx.findings(evidence={"skipped": "fewer than three candidate models"})
        matrices = {}
        for metric in _METRICS:
            matrices[metric] = torch.stack([self._features(metric, outputs, cid, own, labels, layers) for cid in order])
        flagged = set()
        for metric in _METRICS:
            flagged |= {order[i] for i in _prune(matrices[metric], len(clients), self.alpha)}
        votes = [0 if cid in flagged else 1 for cid in clients]
        scores = {cid: float(matrices["cosine"][i].abs().sum()) for i, cid in enumerate(order)}
        features = {cid: {"hlbim_cosine": float(matrices["cosine"][i].abs().sum()),
                          "hlbim_euclidean": float(matrices["euclidean"][i].abs().sum())}
                    for i, cid in enumerate(order)}
        return ctx.findings(scores=scores, features=features,
                            evidence={"pack_round": pack_round, "validator": own, "rejected": sorted(flagged),
                                      "labels": sorted(set(labels)), "layers": len(layers)},
                            messages={"votes": votes, "pack_round": pack_round})

    def _read_pack(self, ctx):
        clients = ctx.reports.messages(_SERVER + ".pack_clients").get("server")
        if clients is None:
            return None
        clients = [str(cid) for cid in clients]
        pack_round = int(ctx.reports.messages(_SERVER + ".pack_round").get("server", ctx.round - 1))
        base_vec = ctx.reports.attachments(_SERVER + ".pack.base").get("server")
        if base_vec is None:
            return None
        template = ctx.received_model.state()
        candidates = {}
        for cid in clients:
            vec = ctx.reports.attachments(_SERVER + ".pack." + cid).get("server")
            if vec is None:
                return None
            candidates[cid] = states.unflatten(vec.double(), template)
        return clients, pack_round, states.unflatten(base_vec.double(), template), candidates

    def _features(self, metric, outputs, cid, own, labels, layers):
        blocks = []
        for name in layers:
            if metric == "cosine":
                candidate = 1.0 - _row_cosine(outputs[cid][name], outputs["__base__"][name])
                reference = 1.0 - _row_cosine(outputs[own][name], outputs["__base__"][name])
            else:
                candidate = _row_distance(outputs[cid][name], outputs["__base__"][name])
                reference = _row_distance(outputs[own][name], outputs["__base__"][name])
            blocks.append(_relative_signed_square(candidate, reference, self.eps))
        row = []
        for value in sorted(set(labels)):
            mask = torch.tensor([label == value for label in labels], dtype=torch.bool)
            if not bool(mask.any()):
                continue
            for block in blocks:
                row.append(block[mask].mean())
        return torch.stack(row)
