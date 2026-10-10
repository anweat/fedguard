# plugin.py
"""PEFTGuard: backdoored-adapter detection on the LoRA a client uploads.

Ported from "PEFTGuard: Detecting Backdoor Attacks Against Parameter-Efficient Fine-Tuning"
(arXiv:2411.17453). The paper is centralized: a platform downloads a published PEFT adapter and returns
0/1; there is no aggregation, no round, no client participation and no data. Only the inference pipeline
of Section 4 (PEFTGuard_trans(.)) and the verdict of Eq. (12) are ported; the meta-classifier it feeds is
the offline-trained component of the defender and enters as the resource `classifier`.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import states


def _modules(state: dict[str, torch.Tensor]) -> list[str]:
    """LoRA module prefixes carrying both factors, sorted (same rule as
    fedguard.views.uploads.lora_modules, which is not on the plugin import surface)."""
    a, b = ".lora_A.weight", ".lora_B.weight"
    return sorted(p[: -len(a)] for p in state if p.endswith(a) and p[: -len(a)] + b in state)


def _places(state: dict[str, torch.Tensor]) -> dict[tuple[int, str], str]:
    """(transformer block, module role) -> module prefix, read from the key names only."""
    out = {}
    for module in _modules(state):
        info = states.module_info(module)
        if info["layer"] is not None:
            out[(info["layer"], info["role"])] = module
    return out


def _stack(uploads, cid: str, grid: list[tuple[int, str, str]], space: str, dtype: torch.dtype) -> torch.Tensor:
    """F_input of one adapter: Eq. (6) per module, Eq. (13) along a new leading axis, Eq. (14) over layers."""
    rows = []
    for _layer, _role, module in grid:
        effect = uploads.cumulative(cid, module) if space == "adapter" else uploads.increment(cid, module)
        delta = effect.to(dtype).dense()
        if rows and delta.shape != rows[0].shape:
            raise ValueError(f"{module} is {tuple(delta.shape)}, not {tuple(rows[0].shape)}")
        rows.append(delta)
    return torch.stack(rows)


class PEFTGuard(GuardPlugin):
    """PEFTGuard (arXiv:2411.17453) at the server, on the LoRA each client uploads.

    A released PEFT adapter is judged backdoored or not from its weights alone: rebuild the weight-space
    change of every target module, delta = B A (Eq. 6); stack the target modules of one block along a new
    leading axis (Eq. 13); stack the blocks in layer order (Eq. 14) into F_input; a meta-classifier turns
    F_input into 0/1 (Eq. 12). Here the adapter is an upload of the round and the verdict becomes an
    aggregation decision: a client whose adapter is judged backdoored is excluded from aggregation.

    Implemented:
    Steps 1-4 of the pipeline: module and target-role parsing from the state-dict keys, the low-rank
    reconstruction delta = B A at base-weight shape, the channel stack over the target modules of a block
    and the layer stack into F_input. Step 5 at inference time: F_input is handed to the trained
    classifier, its probability is thresholded, and the result is returned as the scores of the plugin
    plus a Decision. The inputs are only the uploaded LoRA factors; no training data, no hyperparameters,
    no trigger, no probe and no forward pass through any model (paper Section 1.1, Section 3.2, Section 9).

    Resource `classifier`: one callable, F_input (a float tensor of shape (len(roles) * blocks, d_out,
    d_in)) in, a scalar probability of "backdoored" in [0, 1] out. It is the meta-classifier of Eq. (12)
    trained offline on a labelled adapter set (PADBench: 250 benign + 250 backdoored per configuration,
    Section 4.1, Table 15). The paper gives its architecture only as Figure 7a, so the trained network is
    used as an opaque callable instead of being rebuilt here.

    Deviations:
    The paper is centralized and inspects a published adapter; there is no aggregation and no round. Mapped
    here onto the LoRA that a client uploads: delta is B A of the uploaded adapter itself
    (ctx.uploads.cumulative), not a standalone adapter file, and detection runs at SERVER_AGGREGATE,
    before the upload is merged into the global model, which is the "without merging them into the
    original LLMs" of Section 3.1. The paper defines no action for a positive verdict (Section 6 says only
    that such a framework can be combined with mitigation), so "backdoored" is mapped to exclusion from
    the aggregation of this round; a client that is not flagged keeps the aggregation weight it would have
    had. The library applies its lora_scale (alpha / r) inside ctx.uploads, so delta is scale * B A, while
    the paper writes delta = B A (Eq. 6) without that factor. The delta of the paper is the full effect of
    an adapter, whereas a federated upload is a change relative to the broadcast base, so
    space="increment" (delta = uploaded - base) is offered; the default, space="adapter", is Eq. (6) read
    literally on the uploaded factors.

    Not implemented:
    The meta-classifier itself: the contrastive training and the parameter-average fusion of three
    per-attack classifiers (steps 7-10 of the pipeline in the paper) are offline work on a labelled
    adapter set, which the library leaves outside plugins and which needs PADBench and its training
    compute. The mitigation the paper evaluates (Fine-mixing, step 11) is a third-party method, not part
    of PEFTGuard, and is not mounted here either.

    Open in the paper and chosen here:
    The threshold: the paper reports Detection Accuracy and AUC and writes only "0/1", so a probability
    cut-off is a choice of the implementer; the default is 0.5 on a sigmoid output. The feature is built
    in float32 (dtype=...), one adapter at a time; the paper does not say at what precision F_input is
    formed. Blocks are ordered by the integer component of the module path and the target roles of a block
    in the order of `roles` (default q_proj, v_proj, the default target modules of the paper, Table 15
    note), which is the order that Eq. (13) and Eq. (14) prescribe. The blocks of a round are the union
    over its uploads, so a deployment whose clients carry different module sets judges nobody, the
    conservative reading of "any variation in input dimensions requires training a new classifier"
    (Section 7). An adapter that does not carry every (block, role) pair named by `roles` is not judged at
    all rather than zero-filled, and is not excluded: the paper does not define the degenerate form, and
    it evaluates single-module configurations (Table 5), where `roles=("q_proj",)` gives F_input of shape
    (blocks, d, k).

    Cost:
    One dense F_input per client per round: len(roles) * L * d_out * d_in elements, built and released one
    client at a time. For Llama-2-7B with q and v over 32 blocks, the example given in the paper, this is
    64 x 4096 x 4096, about 1.07e9 elements, 4 GiB in float32 (2 GiB in bfloat16); that memory, not the
    classifier, is the binding cost, and it is independent of the adapter rank. No model forward or
    backward pass is spent, and no state is kept across rounds.
    """

    name, at, version = "peftguard", Stage.SERVER_AGGREGATE, "1"
    needs, resources, acts = frozenset({"uploads"}), frozenset({"classifier"}), frozenset({"select_and_weight"})

    def __init__(self, roles: tuple[str, ...] = ("q_proj", "v_proj"), threshold: float = 0.5,
                 space: str = "adapter", dtype: torch.dtype = torch.float32):
        self.roles, self.threshold, self.space, self.dtype = tuple(roles), float(threshold), space, dtype

    def run(self, ctx):
        uploads, clients = ctx.uploads, ctx.uploads.clients
        if not clients:
            return ctx.findings(evidence={"skipped": "no uploads this round", "judged": 0})
        places = {cid: _places(uploads.state(cid)) for cid in clients}
        blocks = sorted({block for p in places.values() for block, _role in p})
        named = {}
        for p in places.values():
            for place, module in p.items():
                named.setdefault(place, module)
        wanted = [(block, role) for block in blocks for role in self.roles]
        grid = [(block, role, named[(block, role)]) for block, role in wanted if (block, role) in named]
        if not grid:
            return ctx.findings(evidence={"skipped": f"no module with a role in {list(self.roles)} in this round",
                                          "judged": 0})
        feats, not_judged = {}, {}
        for cid in clients:
            absent = [f"{block}:{role}" for block, role in wanted if (block, role) not in places[cid]]
            if absent:
                not_judged[cid] = f"adapter lacks {absent}"
                continue
            try:
                feats[cid] = _stack(uploads, cid, grid, self.space, self.dtype)
            except ValueError as exc:
                not_judged[cid] = str(exc)
        if not feats:
            return ctx.findings(evidence={"skipped": "no client carries the configured module grid",
                                          "judged": 0, "not_judged": not_judged})
        classifier = ctx.resource("classifier")
        scores = {}
        for cid, features in feats.items():
            score = float(classifier(features))
            if not math.isfinite(score):
                raise ValueError(f"the classifier returned {score} for {cid}")
            scores[cid] = score
        flagged = {cid for cid, score in scores.items() if score >= self.threshold}
        decision = Decision(excluded=flagged,
                            flags={cid: f"p={scores[cid]:.4f} >= {self.threshold}" for cid in sorted(flagged)})
        evidence = {"judged": len(scores), "not_judged": not_judged, "flagged": sorted(flagged),
                    "input_shape": list(next(iter(feats.values())).shape), "blocks": blocks,
                    "roles": list(self.roles), "space": self.space, "threshold": self.threshold,
                    "model_passes": 0}
        return ctx.findings(scores=scores, evidence=evidence, decision=decision)
