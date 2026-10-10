"""Methods with a part on each side that talk over the message channel: Safe-FedLLM at step level (a
probe on the client, trust on the server) and ProtegoFed (centroids exchanged before training).

As everywhere in fedguard.methods: every class names its paper, says which steps are implemented, what
deviates, and which choices the paper left open; none has been checked against the authors' code or
reproduced numerically. The step-by-step extractions they were written from are in
`survey/harvest/2026-10-08/opsread/<key>.md`.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.methods.shared import first_layer_b_feature
from fedguard.ops import cluster, probe, sampling, sequential, transform


class SafeFedLLMStepProbe(GuardPlugin):
    """Safe-FedLLM, Step-Level, client half: after every local step, probe the LoRA and count verdicts.

    Each step: feature from the current LoRA against the received one, probe score, malicious if
    s >= tau_cls. Before upload the counts of benign and malicious steps are sent to the server.
    Resource `lora_probe` as in SafeFedLLMClientLevel, held by the client.
    The server cannot verify these counts; a client that lies about them defeats the method.
    Open in the paper and chosen here: the paper does not say where the probe runs or how the counts
    reach the server; running it on the client and sending counts over the channel is a choice.
    Cost: one copy of the LoRA and one dot product per local step.
    """
    name, version = "safe_fedllm_step", "1"
    at = (Stage.CLIENT_STEP, Stage.CLIENT_POST_TRAIN)
    needs, resources = frozenset({"train_trace", "received_model"}), frozenset({"lora_probe"})

    def __init__(self, tau_cls: float = 0.8):
        self.tau_cls = tau_cls

    def run(self, ctx):
        st = ctx.round_state                                         # the two counts are per round
        st.setdefault("benign", 0), st.setdefault("malicious", 0)
        if ctx.stage == Stage.CLIENT_POST_TRAIN:
            return ctx.findings(messages={"benign": st["benign"], "malicious": st["malicious"]})
        x = first_layer_b_feature(ctx.train_trace.lora(), ctx.received_model.state())
        s = float(probe.apply_logistic(ctx.resource("lora_probe"), x[None, :])[0])
        st["malicious" if s >= self.tau_cls else "benign"] += 1
        return ctx.findings(features={"step": {"malicious_probability": s}})


class SafeFedLLMStepTrust(GuardPlugin):
    """Safe-FedLLM, Step-Level, server half: decayed Beta counts of the step verdicts clients report.

    alpha <- gamma * alpha + benign steps, beta <- gamma * beta + malicious steps; factor alpha / (alpha + beta);
    weights n_i * factor; round skipped when the mean factor is below tau_skip; frozen after `freeze_after` rounds.
    Open in the paper and chosen here: alpha and beta start at 1 (a uniform prior). Clients that report
    nothing keep their current factor.
    """
    name, at, version = "safe_fedllm_step_trust", Stage.SERVER_AGGREGATE, "1"
    needs, acts = frozenset({"uploads", "reports"}), frozenset({"select_and_weight"})

    def __init__(self, gamma: float = 0.95, tau_skip: float = 0.2, freeze_after: int = 20, source: str = "safe_fedllm_step"):
        self.gamma, self.tau_skip, self.freeze_after, self.source = gamma, tau_skip, freeze_after, source

    def run(self, ctx):
        st = ctx.state
        counts = st.setdefault("counts", {})
        st["rounds_seen"] = st.get("rounds_seen", 0) + 1
        b, m = ctx.reports.messages(f"{self.source}.benign"), ctx.reports.messages(f"{self.source}.malicious")
        cids = ctx.uploads.clients
        ok = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0  # noqa: E731
        for c in cids:
            if st["rounds_seen"] <= self.freeze_after and ok(b.get(c)) and ok(m.get(c)):
                a0, b0 = counts.get(c, (1.0, 1.0))
                counts[c] = (self.gamma * a0 + b[c], self.gamma * b0 + m[c])
        w = {c: sequential.beta_mean(*counts.get(c, (1.0, 1.0))) for c in cids}
        if cids and sum(w.values()) / len(cids) < self.tau_skip:
            return ctx.findings(features={c: {"safety_factor": v} for c, v in w.items()}, decision=Decision(excluded=set(cids)))
        n = ctx.reports.values("num_examples")
        return ctx.findings(features={c: {"safety_factor": v} for c, v in w.items()}, scores={c: 1 - v for c, v in w.items()},
                            decision=Decision(weights={c: n.get(c, 1.0) * v for c, v in w.items()}))


def _frequency_features(grads: torch.Tensor, shape: tuple[int, int]) -> torch.Tensor:
    """Per-sample gradient of one matrix -> its 2-D DCT, flattened: (n, rows * cols)."""
    return transform.dct_2d(grads.double().reshape(-1, *shape)).reshape(grads.shape[0], -1)


def _two_way_labels(F: torch.Tensor, t_s: float, t_l: float, absorb_noise: bool = False) -> torch.Tensor | None:
    """ProtegoFed's clustering step on feature rows: reduce to 2-D, run a 2-cluster hierarchical clustering
    and a density clustering, and return the labels of whichever has the higher silhouette (noise points
    of the density clustering are labelled -1). A clustering that finds a single cluster counts with
    silhouette 0. Returns None when the evidence for a split is too weak: fewer than four rows, or the
    smaller silhouette below t_s and the larger below t_l."""
    n = F.shape[0]
    if n < 4:
        return None
    Z = transform.pca(F, 2)[0]
    D = cluster.distances(Z)
    cands = []
    for labels in (cluster.agglomerative(D, 2), cluster.density_clusters(D)):
        split = len(labels[labels >= 0].unique()) >= 2
        cands.append((cluster.silhouette(D, labels) if split else 0.0, labels))
    sil = sorted(s for s, _ in cands)
    if sil[0] < t_s and sil[-1] < t_l:
        return None
    labels = max(cands, key=lambda c: c[0])[1]
    if absorb_noise and (labels < 0).any():            # give each noise point the label of its nearest clustered point
        labels = labels.clone()
        placed = labels >= 0
        for i in torch.nonzero(~placed).flatten().tolist():
            labels[i] = labels[placed][D[i][placed].argmin()]
    return labels


def _two_way_split(F: torch.Tensor, t_s: float, t_l: float) -> torch.Tensor:
    """Membership mask of the main (largest) cluster of _two_way_labels; all rows when there is no credible split."""
    labels = _two_way_labels(F, t_s, t_l)
    return torch.ones(F.shape[0], dtype=torch.bool) if labels is None else labels == torch.mode(labels[labels >= 0]).values


class ProtegoFedClient(GuardPlugin):
    """ProtegoFed, client half (2026): poisoned samples separate from clean ones in the frequency domain
    of their per-sample gradients; a global centroid from the server corrects each client's own split.

    CLIENT_ANNOUNCE: per-sample gradient of the target module (default: lora_B of the last layer; the
    paper uses the last layer's v_proj.lora_B), 2-D DCT, flatten; split into clusters; the centroid of the
    main cluster, in the original feature dimension, is sent to the server.
    CLIENT_PRE_TRAIN: the server's global centroid is added to the local features as one more point, the
    features are clustered again, and the samples outside the centroid's cluster are masked.
    Deviations: the paper reduces to two dimensions with UMAP; PCA is used here (no UMAP dependency).
    The paper's HDBSCAN comes without parameters; ops.cluster.density_clusters (DBSCAN with a
    data-driven radius) stands in for it.
    Open in the paper and chosen here: a clustering that finds one cluster counts with silhouette 0 in
    the gate; the main cluster is the largest one; HDBSCAN noise points are
    outside the main cluster; the re-clustering with the centroid uses the same two-way split and
    silhouette gate as the first one (the paper says only "similarly"), and noise points of the density
    clustering are given the label of their nearest clustered sample before the comparison; `max_samples` (not in the paper) subsamples the data and leaves the
    samples that were not scored untouched.
    Cost: one forward and one backward pass per scored sample.
    """
    name, version = "protegofed_client", "1"
    at = (Stage.CLIENT_ANNOUNCE, Stage.CLIENT_PRE_TRAIN)
    needs, acts = frozenset({"data", "model_handle", "reports"}), frozenset({"mask_samples"})

    def __init__(self, group: str = "last_lora_B", t_s: float = 0.2, t_l: float = 0.4, max_samples: int | None = None,
                 server: str = "protegofed_server"):
        self.group, self.t_s, self.t_l, self.max_samples, self.server = group, t_s, t_l, max_samples, server

    def run(self, ctx):
        st, data = ctx.round_state, ctx.data                         # what the announce computed, for this round's training
        if ctx.stage == Stage.CLIENT_ANNOUNCE:
            idx = sampling.subsample(len(data), self.max_samples, ctx.rng)
            samples = list(data.samples())
            handle = ctx.model_handle
            layout = handle.layout(self.group)
            grads = handle.per_sample_gradients([samples[i] for i in idx], self.group)
            width = layout[0][1][0] * layout[0][1][1]                  # the first matrix of the group
            F = _frequency_features(grads[:, :width], layout[0][1])
            main = _two_way_split(F, self.t_s, self.t_l)
            st.update(idx=idx, F=F)
            return ctx.findings(attachments={"centroid": F[main].mean(0).float()},
                                evidence={"scored": len(idx), "main_cluster": int(main.sum())})
        if "F" not in st:
            return ctx.findings(evidence={"skipped": "no announce this round"})
        cg = ctx.attachment(f"{self.server}.centroid").get("server")
        F, idx = st["F"], st["idx"]
        if cg is None or cg.numel() != F.shape[1] or len(idx) < 3:
            return ctx.findings(evidence={"skipped": "no usable global centroid"})
        labels = _two_way_labels(torch.cat([F, cg.double().reshape(1, -1)]), self.t_s, self.t_l, absorb_noise=True)
        clean = torch.ones(len(idx), dtype=torch.bool) if labels is None else labels[:-1] == labels[-1]
        manifest = data.manifest
        mask = [manifest[i].hash for i, ok in zip(idx, clean.tolist()) if not ok]
        return ctx.findings(scores={manifest[i].hash: float(not ok) for i, ok in zip(idx, clean.tolist())},
                            proposals={"mask": mask}, evidence={"scored": len(idx), "masked": len(mask)})


class ProtegoFedServer(GuardPlugin):
    """ProtegoFed, server half: cluster the clients' centroids and send back the centroid of the main cluster.

    Runs at SERVER_EXCHANGE, before any client trains. Open in the paper: whether this second clustering
    uses the same two-way split and silhouette gate as the client; here it does. What clients send is
    unverified: centroids of the wrong size or with non-finite values are dropped.
    """
    name, at, version = "protegofed_server", Stage.SERVER_EXCHANGE, "1"
    needs = frozenset({"reports"})

    def __init__(self, t_s: float = 0.2, t_l: float = 0.4, client: str = "protegofed_client"):
        self.t_s, self.t_l, self.client = t_s, t_l, client

    def run(self, ctx):
        got = {c: v.double().flatten() for c, v in ctx.attachment(f"{self.client}.centroid").items() if torch.isfinite(v).all()}
        if not got:
            return ctx.findings(evidence={"skipped": "no centroids"})
        size = torch.mode(torch.tensor([v.numel() for v in got.values()])).values.item()
        got = {c: v for c, v in got.items() if v.numel() == size}
        cids = sorted(got)
        C = torch.stack([got[c] for c in cids])
        main = _two_way_split(C, self.t_s, self.t_l)
        return ctx.findings(attachments={"centroid": C[main].mean(0).float()},
                            scores={c: float(not m) for c, m in zip(cids, main.tolist())},
                            evidence={"centroids": len(cids), "main_cluster": int(main.sum())})
