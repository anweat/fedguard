# plugin.py
"""PEFTGuard (arXiv:2411.17453) as a fedguard plugin: every uploaded LoRA adapter is scored by a
defender-supplied meta-classifier and the uploaders it calls backdoored are removed from the round.
The check reads only the adapter weights: no local data, no probe samples, no forward pass through
the base model.
"""
from __future__ import annotations

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage

A_SUFFIX = ".lora_A.weight"
B_SUFFIX = ".lora_B.weight"


def lora_modules(state: dict[str, torch.Tensor]) -> list[str]:
    """Module prefixes of a LoRA state dict that have both factors, in sorted order.

    fedguard.views.uploads has the same function, but a plugin may not import that module, so the
    state-dict scan is repeated in these four lines.
    """
    prefixes = {key[: -len(A_SUFFIX)] for key in state if key.endswith(A_SUFFIX)}
    return sorted(p for p in prefixes if p + B_SUFFIX in state)


def module_rank(name: str, targets: tuple[str, ...]) -> tuple[int, int] | None:
    """(layer index, position in `targets`) of one LoRA module path, or None when it is not a target.

    The layer index is the last dot-separated component that is all digits (for example
    "model.layers.3.self_attn.q_proj" gives 3), and -1 when the path has none. A module is a target
    when its last path component equals a target name, or contains one; the position is the first
    such target, which is what fixes the channel order.
    """
    last = name.rsplit(".", 1)[-1]
    rank = next((i for i, t in enumerate(targets) if t == last), None)
    if rank is None:
        rank = next((i for i, t in enumerate(targets) if t in last), None)
    if rank is None:
        return None
    layer = -1
    for part in name.split("."):
        if part.isdigit():
            layer = int(part)
    return layer, rank


class PeftGuard(GuardPlugin):
    """PEFTGuard: a meta-classifier reads the dense low-rank products of a PEFT adapter and returns 1
    when the adapter carries a backdoor (Eq. (12)); it needs no training data, no trigger pattern, no
    downstream task information and no merge into the base model.

    Implemented: steps 1 to 5 of the pipeline, the whole inference path. Steps 1 and 2: for every
    upload the plugin takes the LoRA factors of the selected modules and forms the dense delta of
    Eq. (6), delta = (alpha/r) B A, through `uploads.cumulative` (or the functional change of this
    round through `uploads.increment`, with space="increment"). Steps 3 and 4: the selected modules of
    a layer are stacked along a new leading channel axis (Eq. (13)) and the layers along that same
    axis (Eq. (14)), giving one (C, d, k) float32 tensor per adapter. Step 5: that tensor goes to the
    trained classifier of the defender, and a score at or above `threshold` marks the adapter. The
    plugin scores at SERVER_RECEIVE, keeps the scores in `ctx.state`, and at SERVER_AGGREGATE turns
    them into a `Decision` that excludes the uploader; the aggregation and the weights of the host are
    left untouched.

    Resource `meta_classifier`: the trained PEFTGuard_cls of Eq. (12), as one callable. It receives a
    single float32 tensor of shape (C, d, k) -- C selected modules in (layer, target) order -- and
    returns one scalar, the probability that this adapter is backdoored (a float, or a 0-dim or
    1-element tensor). The defender must export the network together with the conventions it was
    trained with (channel order, target modules, normalization, d and k); the plugin only calls it.
    With a network that outputs a raw logit, pass threshold=0.0.

    Deviations: the paper is centralized and judges a finished adapter downloaded from a sharing
    platform; the object judged here is one upload at SERVER_RECEIVE, that is, the adapter after the
    local training of that client, and the verdict is enforced as an exclusion from this round of
    aggregation, because the library has no platform-side per-adapter action and the paper does not
    define what the platform does with a verdict of 1. The paper defines F_input as (2L, d, k) over all
    L layers with the q and v projections; in a run the channels are the modules the host actually
    adapted, and a layer that misses one of the target modules contributes one channel instead of two.

    Not implemented: the offline half of the pipeline -- generating the labelled adapter dataset
    (step 6), its feature transform (step 7), supervised training of the classifier (step 8), and the
    optional contrastive training and parameter-averaging fusion (step 9) -- and the optional
    Fine-mixing mitigation (step 10), which is a third-party method. That work stays outside the
    plugin; the trained classifier enters as the resource above. Also not implemented: the AdaLoRA and
    DoRA branches of step 1 (Eqs. (8) to (10)) -- fedguard carries LoRA state dicts (lora_A and
    lora_B) only, so the plugin forms Eq. (6) and cannot read P, Lambda, Q, or a direction matrix with
    a magnitude vector.

    Open in the paper and chosen here: target modules default to q_proj and v_proj, matched on the
    last component of the LoRA module path (the paper default, Table 15 note), and a module that
    matches no target is dropped. Channel order is (layer index, target position); the layer index is
    the last all-digit path component, and -1 when there is none, so unnumbered modules come first. A
    missing target module in a layer produces no channel: no zero fill and no duplicate, since the
    paper leaves the degenerate form of Eq. (13) open. F_input is passed unnormalized (the paper
    mentions no normalization) and cast to float32 (a trained torch classifier is float32). The
    classifier is called once per upload and must return the probability itself: this port applies no
    calibration, only the threshold, which the paper leaves open and this port sets to 0.5. When
    SERVER_RECEIVE left no score for the round, SERVER_AGGREGATE excludes nobody. Uploads of one round
    are not reconciled with each other: every adapter is judged with the channels its own state has,
    and those shapes must match what the classifier was trained on.

    Cost: one dense (d, k) matrix per selected module and one classifier forward per upload. A
    (C, d, k) float32 tensor is held while the classifier runs, C = 2L when every layer has q and v:
    about 4 GiB for the Llama-2-7B example of the paper (64, 4096, 4096), which is what the paper does
    in its step 2 even though fedguard keeps LoRA low-rank to avoid forming it. No model pass, no
    local data, no channel traffic; between the two stages the plugin keeps only the scores.
    """
    name, at, version = "peftguard", (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE), "1"
    needs = frozenset({"uploads"})
    resources = frozenset({"meta_classifier"})
    acts = frozenset({"select_and_weight"})

    def __init__(self, target_modules: tuple[str, ...] = ("q_proj", "v_proj"), space: str = "uploaded",
                 threshold: float = 0.5):
        if space not in ("uploaded", "increment"):
            raise ValueError("space must be uploaded or increment")
        self.target_modules, self.space, self.threshold = tuple(target_modules), space, float(threshold)

    def selected_modules(self, state: dict[str, torch.Tensor]) -> list[str]:
        """The channels of one adapter: its target modules, ordered by (layer, target)."""
        ranked = []
        for name in lora_modules(state):
            rank = module_rank(name, self.target_modules)
            if rank is not None:
                ranked.append((rank[0], rank[1], name))
        ranked.sort()
        return [name for _, _, name in ranked]

    def delta(self, uploads, cid: str, module: str) -> torch.Tensor:
        """The dense d x k delta of one module: Eq. (6) for the uploaded adapter, or the functional
        change of this round with space="increment"."""
        low = uploads.cumulative(cid, module) if self.space == "uploaded" else uploads.increment(cid, module)
        return low.dense()

    def feature(self, uploads, cid: str, modules: list[str]) -> torch.Tensor:
        """Eqs. (13) and (14): the deltas of the selected modules stacked on a new leading axis. One
        delta is materialized at a time, so the peak is the output tensor plus one matrix."""
        out = None
        for i, module in enumerate(modules):
            d = self.delta(uploads, cid, module).detach().to(torch.float32)
            if out is None:
                out = torch.empty((len(modules), *d.shape), dtype=torch.float32)
            out[i] = d
        return out

    def run(self, ctx):
        if ctx.stage == Stage.SERVER_AGGREGATE:
            return self._decide(ctx)
        return self._score(ctx)

    def _score(self, ctx):
        uploads, classifier = ctx.uploads, ctx.resource("meta_classifier")
        scores, features = {}, {}
        for cid in uploads.clients:
            modules = self.selected_modules(uploads.state(cid))
            if not modules:
                scores[cid], features[cid] = 0.0, {"channels": 0.0}
                continue
            f = self.feature(uploads, cid, modules)
            scores[cid] = float(classifier(f))
            features[cid] = {"channels": float(len(modules)), "values": float(f.numel()),
                             "frobenius": float(f.norm())}
        ctx.state["round"], ctx.state["scores"] = ctx.round, scores
        flagged = sorted(c for c, p in scores.items() if p >= self.threshold)
        return ctx.findings(scores=scores, features=features,
                            evidence={"space": self.space, "threshold": self.threshold,
                                      "scored": len(scores), "flagged": flagged})

    def _decide(self, ctx):
        st = ctx.state
        if st.get("round") != ctx.round or not st.get("scores"):
            return ctx.findings(evidence={"skipped": "no score of this round from SERVER_RECEIVE"})
        scores = dict(st["scores"])
        excluded = {cid for cid, p in scores.items() if p >= self.threshold}
        return ctx.findings(
            scores=scores,
            decision=Decision(excluded=excluded,
                              flags={cid: "peftguard score %.4f" % scores[cid] for cid in sorted(excluded)}),
            evidence={"excluded": sorted(excluded)})
