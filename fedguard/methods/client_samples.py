"""Client side, before local training, on the client's own samples: filtering, rewriting and adding
samples. Spectral signatures, activation clustering, gradient spectral entropy, ONION, safety-sample mixing.

As everywhere in fedguard.methods: every class names its paper, says which steps are implemented, what
deviates, and which choices the paper left open; none has been checked against the authors' code or
reproduced numerically. The step-by-step extractions they were written from are in
`survey/harvest/2026-10-08/opsread/<key>.md`.

These were proposed for centralized training (ONION for inference inputs); here they run on one
client's local data before it trains, with the model the client was sent.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.ops import cluster, density, sampling, spectral, text, transform


class SpectralSignatures(GuardPlugin):
    """Spectral signatures (Tran et al., NeurIPS 2018): poisoned samples of a class leave a detectable
    trace in the top singular direction of that class's representations.

    Per group of samples: hidden representations, centered; score = squared projection on the top right
    singular vector; the top 1.5 * epsilon fraction is masked.
    Deviations: the paper trains a model on the full (possibly poisoned) data first and reads a late
    layer of it; here the representations come from the model the client received, so a backdoor that
    has not reached that model yet leaves no trace. The paper groups by class label; language-model
    samples have none, so everything is one group unless `group_of` gives one.
    Open in the paper and chosen here: epsilon is a fraction; the number removed is rounded up; a group
    with fewer than `min_group` samples is left alone.
    Cost: one forward pass per scored sample.
    """
    name, at, version = "spectral_signatures", Stage.CLIENT_PRE_TRAIN, "1"
    needs, acts = frozenset({"data", "model_handle"}), frozenset({"mask_samples"})

    def __init__(self, epsilon: float = 0.05, layer: int = -1, pool: str = "mean", group_of=None,
                 max_samples: int | None = None, min_group: int = 10):
        self.epsilon, self.layer, self.pool, self.group_of = epsilon, layer, pool, group_of
        self.max_samples, self.min_group = max_samples, min_group

    def run(self, ctx):
        data = ctx.data
        idx = sampling.subsample(len(data), self.max_samples, ctx.rng)
        samples = list(data.samples())
        R = ctx.model_handle.hidden([samples[i] for i in idx], self.layer, self.pool)
        groups: dict = {}
        for pos, i in enumerate(idx):
            groups.setdefault(self.group_of(samples[i]) if self.group_of else "", []).append(pos)
        manifest, scores, mask = data.manifest, {}, []
        for members in groups.values():
            if len(members) < self.min_group:
                continue
            s = spectral.top_singular_scores(R[members])
            for pos, v in zip(members, s.tolist()):
                scores[manifest[idx[pos]].hash] = v
            remove = min(len(members), math.ceil(1.5 * self.epsilon * len(members)))
            mask += [manifest[idx[members[j]]].hash for j in s.argsort(descending=True)[:remove].tolist()]
        return ctx.findings(scores=scores, proposals={"mask": mask}, evidence={"scored": len(scores), "masked": len(mask)})


class GradientSpectralEntropy(GuardPlugin):
    """GradSentry (2026): the per-sample gradient of a poisoned sample has a different spectral entropy.

    Per sample: gradient of one weight matrix; top-k singular values; normalized to a distribution;
    entropy divided by log k. Threshold at the valley of a Gaussian kernel density of the scores
    (Silverman bandwidth), with the paper's fallback of 0.7 when the scores are not bimodal; samples
    above the threshold are masked.
    Deviations: the paper takes the gradient of lm_head.weight and keeps its top-left 1/8 x 1/8 block;
    the model handle exposes LoRA parameters only, so the gradient of one LoRA B matrix is used whole.
    Its rank is at most r, so k = min(k, r). Whether the paper's finding carries over to this matrix has
    not been checked. An exact SVD replaces the paper's randomized one.
    Open in the paper and chosen here: peaks are local maxima of the density on a 512-point grid; a
    score equal to the threshold is kept.
    Cost: one forward and one backward pass per scored sample.
    """
    name, at, version = "gradient_spectral_entropy", Stage.CLIENT_PRE_TRAIN, "1"
    needs, acts = frozenset({"data", "model_handle"}), frozenset({"mask_samples"})

    def __init__(self, group: str = "last_lora_B", k: int = 16, fallback: float = 0.7, max_samples: int | None = None):
        self.group, self.k, self.fallback, self.max_samples = group, k, fallback, max_samples

    def run(self, ctx):
        data, handle = ctx.data, ctx.model_handle
        idx = sampling.subsample(len(data), self.max_samples, ctx.rng)
        samples = list(data.samples())
        shape = handle.layout(self.group)[0][1]
        grads = handle.per_sample_gradients([samples[i] for i in idx], self.group)[:, : shape[0] * shape[1]]
        k = min(self.k, *shape)
        if k < 2:
            return ctx.findings(evidence={"skipped": "the gradient matrix has rank below two"})
        H = []
        for g in grads:
            sv = torch.linalg.svdvals(g.double().reshape(shape))[:k].clamp_min(1e-12)
            H.append(density.shannon_entropy(sv) / math.log(k))
        H = torch.tensor(H, dtype=torch.float64)
        tau, bimodal = density.kde_valley_threshold(H, 0.0, 1.0, fallback=self.fallback)
        manifest = data.manifest
        mask = [manifest[i].hash for i, h in zip(idx, H.tolist()) if h > tau]
        return ctx.findings(scores={manifest[i].hash: h for i, h in zip(idx, H.tolist())}, proposals={"mask": mask},
                            evidence={"threshold": tau, "bimodal": bimodal, "scored": len(idx), "masked": len(mask)})


class ActivationClustering(GuardPlugin):
    """Activation clustering (Chen et al., 2018): within a class, poisoned and clean samples activate
    the last hidden layer differently and split into two clusters.

    Per group: last-hidden-layer activations, reduced to `components` dimensions, 2-means; if the smaller
    cluster holds less than `size_threshold` of the group and the split has a silhouette above
    `silhouette_threshold`, the smaller cluster is masked.
    Deviations: the paper reduces with ICA; PCA is used here. The paper offers three tests (retraining
    without a cluster, relative size, silhouette); the size and silhouette tests are combined here and the
    retraining test is not implemented. Grouping and the source of the activations as in SpectralSignatures.
    Cost: one forward pass per scored sample.
    """
    name, at, version = "activation_clustering", Stage.CLIENT_PRE_TRAIN, "1"
    needs, acts = frozenset({"data", "model_handle"}), frozenset({"mask_samples"})

    def __init__(self, components: int = 10, size_threshold: float = 0.35, silhouette_threshold: float = 0.1,
                 layer: int = -1, pool: str = "mean", group_of=None, max_samples: int | None = None, min_group: int = 10):
        self.components, self.size_threshold, self.silhouette_threshold = components, size_threshold, silhouette_threshold
        self.layer, self.pool, self.group_of, self.max_samples, self.min_group = layer, pool, group_of, max_samples, min_group

    def run(self, ctx):
        data = ctx.data
        idx = sampling.subsample(len(data), self.max_samples, ctx.rng)
        samples = list(data.samples())
        R = ctx.model_handle.hidden([samples[i] for i in idx], self.layer, self.pool)
        groups: dict = {}
        for pos, i in enumerate(idx):
            groups.setdefault(self.group_of(samples[i]) if self.group_of else "", []).append(pos)
        manifest, mask, report = data.manifest, [], {}
        for name, members in groups.items():
            if len(members) < self.min_group:
                continue
            Z = transform.pca(R[members], self.components)[0]
            labels, _ = cluster.kmeans(Z, 2, seed=int(ctx.rng.integers(2**31)))
            small = int(torch.bincount(labels, minlength=2).argmin())
            share = float((labels == small).double().mean())
            sil = cluster.silhouette(cluster.distances(Z), labels) if 0 < share < 1 else 0.0
            flagged = 0 < share < self.size_threshold and sil > self.silhouette_threshold
            report[str(name)] = {"smaller_cluster_share": share, "silhouette": sil, "flagged": flagged}
            if flagged:
                mask += [manifest[idx[members[j]]].hash for j in torch.nonzero(labels == small).flatten().tolist()]
        return ctx.findings(proposals={"mask": mask}, evidence={"groups": report, "masked": len(mask)})


class Onion(GuardPlugin):
    """ONION (Qi et al., EMNLP 2021), moved to training time: delete the words whose removal lowers the
    perplexity of a sample's text, on the idea that an inserted trigger is such a word.

    Implemented: perplexity p0 of the text and p_i with word i deleted, suspicion f_i = p0 - p_i, words
    with f_i > bar deleted (bar = 0, the paper's value when there is no validation set to tune it on).
    Deviations: ONION cleans test inputs before inference; here it rewrites training samples before local
    training (`edit_samples`). The language model is the one being fine-tuned, with the adapter the client
    received, instead of GPT-2. Perplexity is exp of the mean negative token log-probability of the text
    after a newline. Only the first `max_words` words of a text are examined.
    Open in the paper and chosen here: words are whitespace-separated; a text is never emptied (if every
    word is suspicious the sample is left alone).
    Cost: one forward pass per examined word and one per sample.
    """
    name, at, version = "onion", Stage.CLIENT_PRE_TRAIN, "1"
    needs, acts = frozenset({"data", "model_handle"}), frozenset({"edit_samples"})

    def __init__(self, field: str = "instruction", bar: float = 0.0, max_words: int = 40, max_samples: int | None = None):
        self.field, self.bar, self.max_words, self.max_samples = field, bar, max_words, max_samples

    def run(self, ctx):
        data, handle = ctx.data, ctx.model_handle
        samples, manifest = list(data.samples()), data.manifest
        rewrite, scores, examined = {}, {}, 0
        for i in sampling.subsample(len(samples), self.max_samples, ctx.rng):
            words = text.split_words(str(samples[i].get(self.field, "")))
            head, tail = words[:self.max_words], words[self.max_words:]
            if len(head) < 2:
                continue
            texts = [" ".join(head)] + text.leave_one_out(head)
            ppl = [math.exp(-lp) for lp in handle.logprob(["\n"] * len(texts), texts)]
            drop = set(text.outlier_words(ppl[0], ppl[1:], self.bar))
            examined += len(head)
            scores[manifest[i].hash] = len(drop) / len(head)
            if drop and len(drop) < len(head):
                kept = [w for j, w in enumerate(head) if j not in drop] + tail
                rewrite[manifest[i].hash] = {**samples[i], self.field: " ".join(kept)}
        return ctx.findings(scores=scores, proposals={"rewrite": rewrite},
                            evidence={"examined_words": examined, "rewritten": len(rewrite)})


class SafetyMix(GuardPlugin):
    """Mix defender-supplied safety samples into the local training data.

    Without a secret this is safety-tuning (Bianchi et al., ICLR 2024): harmful instructions paired with
    refusals are added to the fine-tuning set. With `secret_words` > 0 it is Backdoor Enhanced Safety
    Alignment (Wang et al., 2024): every added sample carries a fixed random prefix, which the service
    also puts in front of user inputs at inference, so the refusals are tied to a trigger the user does
    not know.
    Resource `safety_samples`: a list of samples in the training format. The first `n` are used (BEA: 11).
    Deviations: BEA puts the secret into the system prompt; the training format here has none, so it is
    prefixed to the field `field`. BEA draws 150 random tokens from the vocabulary; here `secret_words`
    random lowercase words of 3 to 8 letters are drawn from `secret_seed`, without a tokenizer.
    Not implemented: generating the refusals (they come with the resource) and the inference-side prefix.
    A client that wants the attack to succeed can simply not run this plugin: it protects only against
    poisoned data a willing client was handed.
    """
    name, at, version = "safety_mix", Stage.CLIENT_PRE_TRAIN, "1"
    resources, acts = frozenset({"safety_samples"}), frozenset({"edit_samples"})

    def __init__(self, n: int = 11, secret_words: int = 0, secret_seed: int = 0, field: str = "instruction"):
        self.n, self.secret_words, self.secret_seed, self.field = n, secret_words, secret_seed, field

    def secret(self) -> str:
        g = torch.Generator().manual_seed(self.secret_seed)
        words = []
        for _ in range(self.secret_words):
            length = int(torch.randint(3, 9, (1,), generator=g))
            words.append("".join(chr(97 + int(v)) for v in torch.randint(0, 26, (length,), generator=g)))
        return " ".join(words)

    def run(self, ctx):
        prefix = self.secret()
        added = [dict(s) for s in list(ctx.resource("safety_samples"))[:self.n]]
        if prefix:
            added = [{**s, self.field: f"{prefix} {s.get(self.field, '')}"} for s in added]
        return ctx.findings(proposals={"add": added}, evidence={"added": len(added), "secret_words": self.secret_words})
