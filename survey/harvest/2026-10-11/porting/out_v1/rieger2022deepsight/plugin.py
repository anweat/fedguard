# plugin.py
"""DeepSight (Rieger et al., 2022) as a server-side plugin for one round of federated LoRA fine-tuning.

The paper has three layers over the uploads of one round: a filtering layer that classifies every
update from the output layer of the model (NEUPs, Threshold Exceedings) and from random probe passes
(DDifs), clusters the updates on those features and removes whole clusters; a clipping layer; and an
aggregation layer. The class docstring says which of that a LoRA-only server can carry.
"""
from __future__ import annotations

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.methods.server_update import update_gram
from fedguard.ops import cluster, geometry, states, update


def _split_noise(labels: torch.Tensor) -> torch.Tensor:
    """Give every noise point (-1) a cluster of its own.

    The paper does not say how HDBSCAN noise points take part in PCI. One shared noise cluster would
    let a single suspicious point condemn every other noise point, which the argument for a majority
    of benign clients does not support.
    """
    lab = labels.detach().clone()
    nxt = int(lab.max()) + 1 if lab.numel() else 0
    for i in torch.nonzero(lab < 0).flatten().tolist():
        lab[i], nxt = nxt, nxt + 1
    return lab


def _membership_distances(labels: torch.Tensor) -> torch.Tensor:
    """Alg. 2 (DistsFromClust): 0 for two clients of the same cluster, 1 otherwise."""
    lab = _split_noise(labels)
    return (lab[:, None] != lab[None, :]).double()


def _cluster_vote(labels: torch.Tensor, suspicious: torch.Tensor, tau: float) -> torch.Tensor:
    """PCI (Alg. 1 lines 25-31): a cluster whose fraction of suspicious labels reaches tau goes, whole."""
    lab = _split_noise(labels)
    removed = torch.zeros(lab.numel(), dtype=torch.bool)
    for c in lab.unique().tolist():
        members = torch.nonzero(lab == c).flatten()
        if float(suspicious[members].double().mean()) >= tau:
            removed[members] = True
    return removed


class DeepSight(GuardPlugin):
    """DeepSight (Rieger et al., 2022): filter, clip and aggregate the round uploads on the server.

    Implemented: the pairwise cosine distance matrix of the round updates (step 2 of the extraction);
    the distance-matrix half of the cluster ensemble - the 0/1 membership distances of a clustering
    (step 9), their average (step 10) and the re-clustering of the merged matrix (step 11); the cluster
    vote filter PCI (step 12); the clipping layer to the median update norm (step 13); equal aggregation
    weights, that is no weighting by reported sample counts (step 14, whose averaging itself is the
    host); and, for one configured round, the per-cluster averaging and the per-cluster broadcast
    (step 15).

    Resource `suspicious_labels`: a mapping client id -> 1 (suspicious) / 0 (benign), the verdict of the
    paper steps 1-7. The paper computes that verdict on the server and needs no external asset; this
    runtime cannot (see Not implemented), so the resource stands in for a missing capability rather
    than for an asset the paper asks for. Clients the mapping does not mention count as benign, and an
    empty mapping turns the filtering layer off.

    Deviations: the paper cosine distances, NEUPs and DDifs all come from the output layer of the full
    model. A LoRA state dict carries only the lora_A/lora_B factors of adapted modules, so the cosine
    leg is computed on the flattened factor-space update (uploaded - broadcast) instead of the output
    layer bias delta, and the cluster ensemble runs over that one leg where the paper averages five
    (one cosine, one NEUP and three DDif distance matrices). The NEUP and DDif legs are absent, not
    approximated.

    Not implemented: step 1 (the output-layer bias delta) and steps 3-5 (the normalized update energies
    NEUPs, the threshold exceedings TE and the median classification) - a LoRA state dict contains no
    output layer, and the server has no model to read one from; steps 6-7 (the random probe forward and
    the DDifs) - ModelHandle has no pass that returns per-output-unit probabilities, and a deployment
    without a server-side model cannot run one. The filtering layer therefore has nothing of its own to
    classify: with an empty `suspicious_labels` nothing is ever excluded and the plugin is a clipping
    and aggregation layer only.

    Open in the paper and chosen here: HDBSCAN parameters are not given, so the stand-in
    fedguard.ops.cluster.density_clusters is used with its own; the paper does not say how noise points
    take part in PCI, so each noise point is a cluster of its own; a client the label mapping omits
    counts as benign; the clipping bound S is the median of the L2 norms of all uploads of the round
    (the paper phrase "all updates, including the filtered model updates" does not say which set that
    is), the median of an even count is the mean of the two middle values, and only clients above the
    bound are rewritten; a cluster is removed when its suspicious fraction is >= tau, following Alg. 1
    rather than the text; the paper last round has no counterpart here, so the caller names the round
    whose uploads are averaged per cluster (clusterwise_round) and those models go out with the next
    round broadcast; excluded clients do take part in that per-cluster average, as the paper says, with
    the same bound; a recipient that did not upload in the clusterwise round keeps the framework global
    model; rounds with fewer than three clients are left alone, and what they leave behind is dropped
    rather than carried into the next round.

    Cost: one n x n cosine distance matrix and two density_clusters runs per round on the server, which
    is what the paper clustering costs once its five legs exist; one norm per client and one rescale per
    client above the bound; one LoRA state per cluster kept between the clusterwise round and the next
    broadcast. The paper dominant cost (3 x 20000 forward passes per client per round for the DDifs) is
    not spent here because it cannot be.
    """
    name, at, version = "deepsight", (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE,
                                      Stage.SERVER_POST_AGGREGATE, Stage.SERVER_DISTRIBUTE), "1"
    needs = frozenset({"uploads", "outgoing"})
    resources = frozenset({"suspicious_labels"})
    acts = frozenset({"transform_update", "select_and_weight", "transform_broadcast"})

    def __init__(self, tau: float = 1.0 / 3.0, min_samples: int = 3, scale: float = 2.0,
                 clusterwise_round: int | None = None):
        self.tau, self.min_samples, self.scale = tau, min_samples, scale
        self.clusterwise_round = clusterwise_round

    def run(self, ctx):
        if ctx.stage == Stage.SERVER_RECEIVE:
            return self._filter_and_clip(ctx)
        if ctx.stage == Stage.SERVER_AGGREGATE:
            return self._decide(ctx)
        if ctx.stage == Stage.SERVER_POST_AGGREGATE:
            return self._clusterwise(ctx)
        return self._distribute(ctx)

    def _filter_and_clip(self, ctx):
        up, st = ctx.uploads, ctx.state
        cids = up.clients
        if len(cids) < 3:
            for stale in ("labels", "excluded", "bound"):     # this round is left alone; the last one does not carry over
                st.pop(stale, None)
            return ctx.findings(evidence={"skipped": f"needs at least three clients, got {len(cids)}"})
        G = update_gram(up, cids, "factor")
        norms = torch.sqrt(torch.diagonal(G).clamp_min(0.0))
        bound = float(torch.quantile(norms, 0.5))
        # Filtering layer: the paper clusters five feature sets (the cosine distances of the output-layer
        # bias deltas, the NEUPs, and one DDif matrix per probe seed). Only a cosine leg can be built here.
        legs = [_membership_distances(cluster.density_clusters(geometry.cosine_distances_from_gram(G),
                                                              self.min_samples, self.scale))]
        merged = torch.stack(legs).mean(0)
        labels = cluster.density_clusters(merged, self.min_samples, self.scale)
        supplied = ctx.resource("suspicious_labels")
        suspicious = torch.tensor([float(supplied.get(c, 0)) for c in cids], dtype=torch.float64)
        removed = _cluster_vote(labels, suspicious, self.tau)
        excluded = {c for c, r in zip(cids, removed.tolist()) if r}
        clipped = {c: update.clip_to_norm(up.state(c), up.base_state(), bound)[0]
                   for c, n in zip(cids, norms.tolist()) if c not in excluded and n > bound}
        st.update(labels={c: int(l) for c, l in zip(cids, labels.tolist())}, excluded=excluded, bound=bound)
        return ctx.findings(
            features={c: {"cluster": float(st["labels"][c]), "norm": float(n), "suspicious": float(s)}
                      for c, n, s in zip(cids, norms.tolist(), suspicious.tolist())},
            evidence={"bound": bound, "legs": len(legs), "clusters": len(set(st["labels"].values())),
                      "excluded": sorted(excluded), "clipped": sorted(clipped)},
            proposals={"transformed": clipped})

    def _decide(self, ctx):
        st, cids = ctx.state, ctx.uploads.clients
        excluded = set(st.get("excluded", set())) & set(cids)
        kept = [c for c in cids if c not in excluded]
        return ctx.findings(
            decision=Decision(excluded=excluded, weights={c: 1.0 for c in kept},
                              flags={c: "cluster vote (PCI)" for c in excluded}),
            evidence={"tau": self.tau, "bound": st.get("bound")})

    def _clusterwise(self, ctx):
        """Step 15: the round the caller named is averaged per cluster, one model per cluster."""
        st = ctx.state
        if self.clusterwise_round is None or ctx.round != self.clusterwise_round:
            return ctx.findings()
        up, labels, bound = ctx.uploads, st.get("labels"), st.get("bound")
        if not up.clients or labels is None or bound is None:
            return ctx.findings(evidence={"clusterwise": "this round was not clustered"})
        base, groups = up.base_state(), {}
        for c in up.clients:
            groups.setdefault(labels.get(c, -1), []).append(update.clip_to_norm(up.state(c), base, bound)[0])
        means = {g: states.weighted_average(members) for g, members in groups.items()}
        st["clusterwise"] = {c: means[labels.get(c, -1)] for c in up.clients}
        st["clusterwise_next"] = ctx.round + 1
        return ctx.findings(evidence={"clusterwise_clusters": len(groups),
                                      "clusterwise_sizes": sorted(len(m) for m in groups.values())})

    def _distribute(self, ctx):
        st, per_client = ctx.state, ctx.state.get("clusterwise")
        if not per_client or ctx.round != st.get("clusterwise_next"):
            return ctx.findings()
        send = {c: per_client[c] for c in ctx.outgoing.recipients if c in per_client}
        if not send:
            return ctx.findings(evidence={"clusterwise": "no recipient uploaded in the clusterwise round"})
        return ctx.findings(proposals={"broadcast": send}, evidence={"clusterwise_recipients": sorted(send)})
