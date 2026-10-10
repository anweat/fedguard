# plugin.py
"""GradSafe (Xie et al., 2024): prompt screening from safety-critical gradient slices.

Mounted on the client at CLIENT_PRE_TRAIN: of the two sides only the client holds the prompts and a
model whose base weights can be back-propagated, and `mask_samples` is where the paper step of
screening data out before training lands.
"""
from __future__ import annotations

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.ops import probe as probe_ops
from fedguard.ops import sampling

SYSTEM_PROMPT = "You are a helpful assistant. Help me with the following query: {prompt}"
COMPLIANCE_RESPONSE = "Sure"


def prompt_response_pair(prompt: str, template: str = SYSTEM_PROMPT, response: str = COMPLIANCE_RESPONSE) -> str:
    """Build the pair of the paper: the prompt inside its system-prompt template, then the response."""
    return template.format(prompt=prompt) + "\n" + response


class GradSafe(GuardPlugin):
    """GradSafe: a prompt is unsafe when the gradient of its (prompt, "Sure") loss resembles the unsafe
    gradient reference on the safety-critical parameter slices.

    Per local prompt: the gradient of the per-sample loss of the templated prompt paired with the
    compliance response, with respect to the frozen base weights; the cosine of each safety-critical
    slice (a row or a column of one 2-D weight matrix) to the stored reference slice. GradSafe-Zero
    averages those cosines over all slices and flags the prompt above `threshold`; with `probe=True`
    (GradSafe-Adapt) a logistic probe fitted offline on labelled domain prompts takes the place of the
    mean and the prompt is flagged above probability 0.5. Flagged prompts are proposed for
    `mask_samples`, that is, removed from the training data of this round.

    Resource `unsafe_reference`: {"slices": [(parameter name, "row" | "col", index), ...],
    "vectors": [1-D tensor, ...]}, one entry per safety-critical slice in the order in which the cosine
    feature vector is concatenated. Parameter names are base-model names as
    `ModelHandle.layout(..., scope="all")` returns them; a row slice has one entry per column of that
    matrix, a column slice one per row. It is the output of Phase I to III of the paper, computed
    offline on the reference prompts of the defender.
    Resource `probe`: only with `probe=True`; a fitted probe as `fedguard.ops.probe.fit_logistic`
    returns it, fitted offline on labelled domain prompts, features in the order of `unsafe_reference`.

    Implemented: the pairing (step 1); the loss gradient with respect to base weights (step 2) through
    `ModelHandle.per_sample_gradients(..., scope="all", reduce=...)`, one backward pass per prompt; the
    row and column slicing (step 3); the slice restriction (step 7) and the cosine feature vector
    (step 8); the mean and threshold decision (step 9a) with the 0.25 default of the paper; the probe
    decision (step 9b, inference only); the downstream action as `mask_samples` by sample hash.
    Deviations: the paper is centralized and screens a prompt before it reaches a chatbot or a
    fine-tuning service; here the data holder screens its own local prompts before local training. The
    server-side variant of the paper is not expressible in federated LoRA, because prompt text never
    reaches the server, which sees LoRA uploads only. The gradient is of the per-sample loss of the
    adapter on the pair text, not of the "standard loss" of the paper: the library offers no way to pin
    the loss to the response tokens or to describe a (prompt, response) pair, so `per_sample_gradients`
    receives one text per prompt and applies its own training loss to it. The gradient is taken on the
    model the handle wraps (frozen base weights plus whatever adapter is loaded), not on a freshly
    loaded aligned base LLM; the paper uses Llama-2-7b-chat-hf and Table 7 shows the method depends on
    that alignment. Only 2-D parameters are sliced: the paper defines slices on gradient matrices and
    says nothing about LayerNorm and bias vectors. The paper formalizes no action after detection;
    masking the sample is the form of screening out used by this library. GradSafe-Adapt appears as
    probe inference only; fitting the probe is offline work.
    Not implemented: the safety-critical slice identification (steps 4 to 6: the mean over the unsafe
    reference prompts, the cosine to it, and the similarity gap threshold). The paper places it outside
    training, and the library has no place to run a model before the first round and to store its
    output; the reference arrives as a resource. The calibration of the 0.25 threshold is also absent
    from the paper, and the threshold is used as given.
    Open in the paper and chosen here: the pair is the templated prompt, a newline and "Sure"; a slice
    of zero norm scores a cosine of 0 (the convention of `fedguard.ops.geometry.cosine_to`); row and
    column slices are mixed in one unweighted mean and the feature order is the order of the resource;
    the decision threshold of Adapt is probability 0.5 (the paper gives none); the reference is matched
    strictly against `ModelHandle.layout(..., scope="all")`, and one mismatched name, index or length
    skips the round report-only instead of silently dropping slices; with an empty slice set nothing is
    scored and nothing is masked; `max_samples` (not in the paper) subsamples the prompts to bound the
    number of backward passes and leaves the unsampled prompts untouched.
    Cost: one forward and one backward pass per scored prompt, on the full model; the cosine work is of
    the order of the total length of the slices per prompt; the reference is used as stored.
    """
    name, at, version = "gradsafe", Stage.CLIENT_PRE_TRAIN, "1"
    needs, acts = frozenset({"data", "model_handle"}), frozenset({"mask_samples"})

    def __init__(self, threshold: float = 0.25, probe: bool = False, max_samples: int | None = None,
                 template: str = SYSTEM_PROMPT, response: str = COMPLIANCE_RESPONSE):
        self.threshold, self.use_probe = threshold, probe
        self.max_samples, self.template, self.response = max_samples, template, response
        self.resources = frozenset({"unsafe_reference", "probe"}) if probe else frozenset({"unsafe_reference"})

    def run(self, ctx):
        reference = ctx.resource("unsafe_reference")
        slices, vectors = list(reference["slices"]), list(reference["vectors"])
        if not slices:
            return ctx.findings(evidence={"skipped": "the unsafe reference holds no safety-critical slice"})
        if len(slices) != len(vectors):
            return ctx.findings(evidence={"skipped": f"unsafe_reference: {len(slices)} slices, {len(vectors)} vectors"})

        wanted = {str(spec[0]) for spec in slices}
        layout = dict(ctx.model_handle.layout(lambda name: name in wanted, scope="all"))
        groups: dict = {}
        for position, (spec, vector) in enumerate(zip(slices, vectors)):
            name, axis, index = str(spec[0]), str(spec[1]), int(spec[2])
            if name not in layout:
                return ctx.findings(evidence={"skipped": f"unsafe_reference names {name!r}, which this model does not have"})
            shape = tuple(layout[name])
            if len(shape) != 2 or axis not in ("row", "col"):
                return ctx.findings(evidence={"skipped": f"unsafe_reference slice {spec!r} is not a row or column of a 2-D parameter"})
            length = shape[1] if axis == "row" else shape[0]
            if not 0 <= index < shape[0 if axis == "row" else 1] or vector.numel() != length:
                return ctx.findings(evidence={"skipped": f"unsafe_reference slice {spec!r} does not fit {name} with shape {shape}"})
            positions, indices, refs = groups.setdefault((name, axis), ([], [], []))
            positions.append(position)
            indices.append(index)
            refs.append(vector.double().flatten())
        plan = {key: (torch.tensor(positions, dtype=torch.long), torch.tensor(indices, dtype=torch.long), torch.stack(refs))
                for key, (positions, indices, refs) in groups.items()}
        dim = len(slices)

        def reduce(grads):
            out = torch.zeros(dim, dtype=torch.float64)
            for (name, axis), (positions, indices, refs) in plan.items():
                grad = grads.get(name)
                if grad is None:
                    continue
                rows = grad if axis == "row" else grad.transpose(0, 1)
                cosine = torch.nn.functional.cosine_similarity(rows[indices.to(rows.device)].double(),
                                                               refs.to(rows.device), dim=1, eps=1e-12)
                out[positions] = cosine.cpu()
            return out

        data, handle = ctx.data, ctx.model_handle
        idx = sampling.subsample(len(data), self.max_samples, ctx.rng)
        if not idx:
            return ctx.findings(evidence={"skipped": "no sample to screen"})
        pairs = [prompt_response_pair(data.text(i), self.template, self.response) for i in idx]
        cosines = handle.per_sample_gradients(pairs, lambda name: name in wanted, scope="all", reduce=reduce)
        if cosines.ndim != 2 or tuple(cosines.shape) != (len(pairs), dim):
            return ctx.findings(evidence={"skipped": f"the model handle returned {tuple(cosines.shape)} for {len(pairs)} prompts and {dim} slices"})
        if self.use_probe:
            score = probe_ops.apply_logistic(ctx.resource("probe"), cosines).tolist()
            threshold, mode = 0.5, "adapt"
        else:
            score = cosines.double().mean(dim=1).tolist()
            threshold, mode = self.threshold, "zero"
        manifest = data.manifest
        mask = [manifest[i].hash for i, value in zip(idx, score) if value > threshold]
        return ctx.findings(scores={manifest[i].hash: float(value) for i, value in zip(idx, score)},
                            proposals={"mask": mask},
                            evidence={"mode": mode, "slices": dim, "scored": len(idx), "masked": len(mask),
                                      "decision_threshold": threshold})
