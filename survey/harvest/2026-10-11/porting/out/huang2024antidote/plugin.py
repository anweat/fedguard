# plugin.py
"""Antidote (Huang et al., 2024): one-shot Wanda-score masking of the global LoRA before it is deployed.

The paper runs Antidote once, after user fine-tuning has finished: forward the harmful re-alignment set
D_realign held by the provider through the fine-tuned model w, score every weight coordinate with the
Wanda score of Eq. (1), keep the alpha fraction with the largest score as a harmful mask (Eq. (2)) and
zero those coordinates, w~ = (1 - m) * w (Eq. (3)). In fedguard the only weights a server holds are the
global LoRA of the round, so the plugin mounts at SERVER_POST_AGGREGATE of the round the run names as
its last one, scores the coordinates of that LoRA state and hands the masked state back as
`replace_global`.
"""
from __future__ import annotations

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.ops import states

_A, _B = ".lora_A.weight", ".lora_B.weight"
_SIDES = ("input", "bottleneck")


def factor_modules(state: dict) -> dict:
    """`<module>` -> {"A": its lora_A key, "B": its lora_B key}, for every module that has both.

    `fedguard.views.uploads.lora_modules` does the same grouping, but the import allow-list of the
    porting guide (section 4.5) does not include the views package, so the grouping is repeated here.
    """
    pairs: dict = {}
    for key in state:
        for factor, suffix in (("A", _A), ("B", _B)):
            if key.endswith(suffix):
                pairs.setdefault(key[: -len(suffix)], {})[factor] = key
    return {m: f for m, f in sorted(pairs.items()) if "A" in f and "B" in f}


def activation_side(name: str, module: str):
    """Which activation of `module` a hooked module name carries, or None if it carries neither.

    "input" is what multiplies the weight of the module itself and lora_A; "bottleneck" is what lora_A
    produced and lora_B consumes. PEFT names the adapter linears `<module>.lora_A` / `<module>.lora_B`
    and may insert the adapter name (`<module>.lora_B.default`), so any `<module>.lora_B...` submodule
    is the bottleneck; `<module>.base_layer`, where a wrapper keeps the original linear apart, receives
    the same input as the wrapper. Nothing else belongs to this module.
    """
    if name == module or name == module + ".base_layer":
        return "input"
    if name.startswith(module + ".lora_B"):
        return "bottleneck"
    return None


def selects(modules):
    """The `select` predicate that asks ModelHandle.activations for exactly the modules being scored."""
    def match(name: str) -> bool:
        return any(activation_side(name, module) for module in modules)
    return match


def channel_norms(per_sample):
    """Mean over samples of the per-channel L2 norm of `pool="none"` activations: [(tokens, d)] -> (d,).

    Eq. (1) in the form the handle returns it: one (tokens, d) tensor per sample, the L2 norm over the
    tokens of a sample is ||A_j(x)||_2 for channel j, and the mean over the samples is the average over
    the reference set. None when no sample carries a token.
    """
    rows = [x.double().pow(2).sum(dim=0).sqrt() for x in per_sample if x.numel()]
    return torch.stack(rows).mean(dim=0) if rows else None


def activation_norms(acts: dict, modules) -> tuple[dict, dict]:
    """The channel norms of the input and the LoRA bottleneck of each module, from one `activations` call.

    Returns ({module: {"input": (d_in,), "bottleneck": (r,)}}, {module: [sides the handle did not show]}).
    A module with only one of the two sides is not scored, so that every candidate coordinate carries
    both terms of Eq. (1) or neither.
    """
    norms, missing = {}, {}
    for module in modules:
        got = {}
        for name, per_sample in acts.items():
            side = activation_side(name, module)
            if side and side not in got:
                norm = channel_norms(per_sample)
                if norm is not None:
                    got[side] = norm
        if all(side in got for side in _SIDES):
            norms[module] = got
        else:
            missing[module] = [side for side in _SIDES if side not in got]
    return norms, missing


def top_ratio_mask(scores: dict, alpha: float, scope: str = "global") -> dict:
    """Eq. (2): a 0/1 mask over the top floor(alpha * d) coordinates of a scored LoRA state.

    scope="global" makes one ArgTopK_alpha over every scored coordinate, the literal reading of the
    paper (a single mask, alpha "the ratio of coordinates that are masked to 1"); scope="per_module"
    takes alpha of the coordinates of each factor, which is what Wanda itself does per layer. The paper
    gives neither a rounding rule nor a tie rule: the count is floored, and ties go to the earlier
    coordinate in `states.flatten` order (sorted key, row-major inside a tensor) through a stable sort,
    so the mask does not depend on how the sort breaks ties.
    """
    flat = states.flatten(scores)
    mask = torch.zeros_like(flat)
    if scope == "per_module":
        cut = 0
        for key in sorted(scores):
            n = scores[key].numel()
            k = int(alpha * n)
            if k > 0:
                order = torch.argsort(flat[cut:cut + n], descending=True, stable=True)
                mask[cut + order[:k]] = 1.0
            cut += n
    else:
        k = int(alpha * flat.numel())
        if k > 0:
            mask[torch.argsort(flat, descending=True, stable=True)[:k]] = 1.0
    return states.unflatten(mask, scores)


def module_features(scores: dict, mask: dict, pair: dict) -> dict:
    """What one module contributed: its coordinate count, how many were masked and its score range."""
    a, b = scores[pair["A"]], scores[pair["B"]]
    n = a.numel() + b.numel()
    return {"coordinates": float(n),
            "masked": float(mask[pair["A"]].sum() + mask[pair["B"]].sum()),
            "max_score": float(torch.maximum(a.max(), b.max())),
            "mean_score": float((a.sum() + b.sum()) / n)}


class AntidotePrune(GuardPlugin):
    """Antidote (Huang et al., 2024): one-shot Wanda-score pruning of the global LoRA after fine-tuning.

    Antidote in the paper takes the safety-alignment-broken fine-tuned model w and the harmful
    re-alignment set D_realign held by the provider, gives every weight coordinate the Wanda score
    [h]_j = (1/|D|) sum_x |w_j| * ||A_j(x, w)||_2 (Eq. (1)), turns the top-alpha fraction of the
    coordinates into a harmful mask (Eq. (2), alpha the mask ratio) and zeroes them, w~ = (1 - m) * w
    (Eq. (3)), once, when fine-tuning is over (Algorithm 1). This plugin runs that computation on the
    global LoRA of the round, at the round the run names as its last one, and hands the masked state
    back as `replace_global`. It needs a full ModelHandle on the server side (the `probe=` argument of
    the adapter), not a ProbeView, because the activation term costs forward passes; a deployment that
    cannot supply one should list `model_handle` in RunSpec.unavailable, and the contract then refuses
    this plugin.

    Resource `realign_data`: the re-alignment set D_realign, a sequence of samples in the form the
    supplied handle consumes (for HFModelHandle: texts, or samples plus its own `text_of`). The set of
    the paper is 2000 harmful question-answer pairs sampled from a red-teaming corpus and kept apart
    from the harmful data mixed into the fine-tuning set (Section 3.1, Section 5.1); no fedguard view
    carries it, so the defender supplies it.

    Implemented: step 1, the activation statistics of D_realign: one forward pass with the aggregated
    LoRA loaded (`handle.lora(result)`) and one `ModelHandle.activations(samples, select, pool="none",
    what="input")` call, which for every adapted module gives the input channels that multiply lora_A
    and, through the lora_B submodule of the module, the bottleneck channels that multiply lora_B.
    Step 2, Eq. (1) for every coordinate of every lora_A/lora_B factor: the absolute value of the
    weight times the mean over D_realign of the L2 norm of that channel. Step 3, Eq. (2): the mask over
    the floor(alpha * d) largest scores. Step 4, Eq. (3): those coordinates zeroed, offered as
    `replace_global`. The one-shot placement: `last_round` or RunSpec.extra["final_round"], plus a
    run-scoped flag that keeps the model from being pruned twice.

    Deviations: the pruned object is the LoRA factors, not the fine-tuned base weights w: the server
    holds LoRA state dicts, `aggregate.result` is the whole model it can see or change, and ModelHandle
    exposes base weights only as names, shapes and gradients, never as values, so Eq. (1) cannot be
    formed for them with |w_j|. An element of a factor is not an element of a dense weight matrix, and
    a zeroed lora_B element does not remove a whole rank-1 term. Which activation A_j is: the paper
    says only "hidden activation that is associated with the j-th weight coordinate"; chosen here as
    the module input for lora_A coordinates and the output of lora_A (the input of lora_B) for lora_B
    coordinates, L2 over the own tokens of each sample and averaged over the samples. The paper is
    centralized and post-hoc; here it is the SERVER_POST_AGGREGATE point of one federated round and its
    w is an aggregate of client uploads, which the paper never discusses. The double-LoRA setup of the
    paper leaves open whether w is the base weights or an adapter merged into them; this port never
    merges, it prunes the adapter that the round aggregated.

    Not implemented: step 5, saving and deploying the pruned model: `replace_global` gives the pruned
    LoRA back to the host, which owns the checkpoint and the serving path (porting rule 3), and the
    plugin writes nothing. Also not implemented: a sparse format (the paper leaves inference speed-ups
    to future work, Section 5.5, and the state stays dense with zeros); any protection rule for a
    module for which all coordinates are masked, or for embeddings, LayerNorm and biases, which are not
    in the LoRA state dict and for which the paper specifies no rule.

    Open in the paper and chosen here: the scope of ArgTopK_alpha: "global" (one cut over all
    coordinates of the state) is the default because Eq. (2) describes a single mask with alpha "the
    ratio of coordinates that are masked to 1", while "per_module" is offered because Wanda itself sets
    sparsity per layer and the paper does not say which one Antidote uses; the number of masked
    coordinates is floor(alpha * d), the paper giving no rounding rule; ties go to the earlier
    coordinate in `states.flatten` order, the paper giving no tie rule; alpha defaults to 0.2, the
    default of the paper (Section 5.1), and the same section gives 0.05 for GSM8K, so a task value
    belongs in the constructor; a module for which the handle did not show the activations is left out
    of the candidate set and reported instead of being scored by |w_j| alone, because the
    |D_realign| = 0 degeneracy of the paper (Table 13 note) is about an empty reference set, not about
    a missing measurement, and silently falling back to magnitude pruning would change the method; an
    empty D_realign and alpha = 0 likewise propose nothing and report the scores; the deployment round
    comes from `last_round` or RunSpec.extra["final_round"], and with neither the plugin prunes nothing
    and says so, because the library has no end-of-fine-tuning stage and pruning mid-training is not
    the method.

    Cost: one forward pass over |D_realign| samples per pruned round (2000 in the paper) through the
    handle, which counts it in `findings.cost`, and no backward pass; O(d) scoring, an O(d log d) rank
    over d = the number of coordinates of the aggregated LoRA, and float64 copies of those coordinates
    for the flat score vector and the mask. Table 10 of the paper puts its whole post-fine-tuning stage
    at 0.04 h next to 1.70 h of SFT (1.02x) at a 22.35 GB peak inside a 35.45 GB pipeline; loading the
    model, holding the re-alignment corpus, exporting the checkpoint and serving it are all outside
    this plugin.
    """
    name, at, version = "antidote_prune", Stage.SERVER_POST_AGGREGATE, "1"
    needs = frozenset({"aggregate", "model_handle"})
    resources = frozenset({"realign_data"})
    acts = frozenset({"replace_global"})

    def __init__(self, alpha: float = 0.2, scope: str = "global", last_round: int | None = None):
        if not 0.0 <= float(alpha) <= 1.0:
            raise ValueError("alpha is the masked fraction of the coordinates, in [0, 1]")
        if scope not in ("global", "per_module"):
            raise ValueError("scope must be global or per_module")
        self.alpha, self.scope, self.last_round = float(alpha), scope, last_round

    def deployment_round(self, ctx):
        """The round the one-shot pruning belongs to: the one of the constructor, else that of the spec."""
        if self.last_round is not None:
            return int(self.last_round)
        final = ctx.spec.extra.get("final_round")
        return None if final is None else int(final)

    def run(self, ctx):
        target = self.deployment_round(ctx)
        if target is None:
            return ctx.findings(evidence={"skipped": "no deployment round: pass last_round=... or set "
                                                     "RunSpec.extra[final_round]; the library has no "
                                                     "end-of-fine-tuning stage"})
        if ctx.round != target:
            return ctx.findings(evidence={"skipped": "not the deployment round", "round": ctx.round,
                                          "deploy_round": target})
        if ctx.state.get("pruned"):
            return ctx.findings(evidence={"skipped": "the global model of this run was already pruned (one-shot)"})
        result = ctx.aggregate.result
        modules = factor_modules(result or {})
        if not modules:
            return ctx.findings(evidence={"skipped": "the aggregate holds no lora_A/lora_B pair"})
        samples = list(ctx.resource("realign_data"))
        if not samples:
            return ctx.findings(evidence={"skipped": "the re-alignment set is empty; the "
                                                     "|D_realign| = 0 degeneracy of the paper (pure "
                                                     "magnitude pruning) is deliberately not used as a fallback"})
        handle = ctx.model_handle
        with handle.lora(result):
            acts = handle.activations(samples, select=selects(modules), pool="none", what="input")
        norms, unscored = activation_norms(acts, modules)
        scores = {}
        for module, pair in modules.items():
            if module not in norms:
                continue
            a, b = result[pair["A"]], result[pair["B"]]
            n_in, n_bot = norms[module]["input"], norms[module]["bottleneck"]
            if n_in.numel() != a.shape[1] or n_bot.numel() != b.shape[1]:
                unscored[module] = [f"shapes: input {n_in.numel()} vs A {tuple(a.shape)}, "
                                    f"bottleneck {n_bot.numel()} vs B {tuple(b.shape)}"]
                continue
            scores[pair["A"]] = a.detach().to(device="cpu", dtype=torch.float64).abs() * n_in[None, :]
            scores[pair["B"]] = b.detach().to(device="cpu", dtype=torch.float64).abs() * n_bot[None, :]
        if not scores:
            return ctx.findings(evidence={"skipped": "no activation of a LoRA module could be measured on "
                                                     "this model handle",
                                          "modules_unscored": sorted(unscored), "unscored_why": unscored})
        mask = top_ratio_mask(scores, self.alpha, self.scope)
        features = {m: module_features(scores, mask, pair) for m, pair in modules.items() if pair["A"] in scores}
        evidence = {"alpha": self.alpha, "scope": self.scope,
                    "coordinates": sum(t.numel() for t in scores.values()),
                    "masked": int(sum(float(m.sum()) for m in mask.values())),
                    "modules_scored": sorted(features), "realign_samples": len(samples)}
        if unscored:
            evidence["modules_unscored"], evidence["unscored_why"] = sorted(unscored), unscored
        scores_by_module = {m: f["max_score"] for m, f in features.items()}
        if evidence["masked"] == 0:
            return ctx.findings(scores=scores_by_module, features=features,
                                evidence={**evidence, "skipped": "no coordinate selected (alpha = 0)"})
        removed = {key: mask[key].to(device=result[key].device, dtype=result[key].dtype) * result[key]
                   for key in mask}
        ctx.state["pruned"] = True
        return ctx.findings(scores=scores_by_module, features=features,
                            proposals={"replacement": states.add(result, removed, scale=-1.0)},
                            evidence=evidence)
