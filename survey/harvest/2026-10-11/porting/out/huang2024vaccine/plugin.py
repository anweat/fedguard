# plugin.py
"""Vaccine (Huang et al., 2024) — port shell.

The port is `not_expressible`; see the class docstring for the interface facts it rests on.
"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class VaccineAlignment(GuardPlugin):
    """Vaccine (Huang et al., 2024): perturbation-aware alignment.

    The method aligns a base LLM on the provider's own safety data by finding, at every optimization
    step, the bounded perturbation of the hidden embedding of every layer that most increases the
    alignment loss, injecting it into a second forward pass, and stepping the optimizer on the gradient
    of that corrupted pass. The deliverable is a model that stays aligned when a user later fine-tunes
    it on partly harmful data. Nothing here reads user data or uploads, and nothing is decided about a
    client. Ported to fedguard's intended placement (a one-off server-side alignment, `SERVER_DISTRIBUTE`
    being the stage where the model that was produced is handed to recipients) it needs one thing that
    the published interfaces do not offer: **a way to read and to write, mid-forward, the outputs of
    the model's layers.**

    Implemented: nothing of the method. This shell exists so that the class can be mounted and the
    refusal is visible in a run's record instead of being silent.

    Deviations: the paper is centralized and has no federated round. Its alignment would sit on the
    server before any distribution, which `SERVER_DISTRIBUTE` is the nearest position for; but the
    library's *only* point inside a training step is client-side (`CLIENT_LOSS`, `CLIENT_PRE_STEP`),
    and by then the step's forward pass has already run to completion. On the server the host supplies
    no model at all, so there is not even a training step to attach to. Both halves of the intended
    placement are therefore unavailable, not just the placement.

    Not implemented (blocked by missing runtime, per the report's `missing_runtime`):
      - step 2, the gradient of the loss with respect to each layer's hidden embedding. `LossView`
        reaches trainable parameters only (`gradients_of` returns gradients for `named_parameters()`
        entries), and `ModelHandle.activations()` hands back `.detach()`ed tensors, so there is no
        graph node for a layer output to differentiate against.
      - step 5, injecting the perturbation into a layer's output. `ModelHandle` has no hook, patch or
        pre-forward mechanism, and the trainer extension says so itself: "What stays out of reach: the
        forward pass itself (attention scores, intermediate activations ...)". Its wrapper replaces
        `compute_loss` and routes the loss through `transform_loss`, which can only substitute the
        scalar — a perturbation added along `outputs.hidden_states` after the forward pass cannot change
        what that pass computed.
      - step 4, the perturbed second forward plus backward. A second pass can be asked for only as
        `loss_on(batch)` / `model_handle.losses(samples)`, both of which take samples and run the
        model's own forward; neither accepts modified activations.

    Open in the paper and chosen here: nothing about the method is chosen, because none of it is
    implemented. Where the paper leaves a detail open, this port records it in the report's
    `open_choices` rather than inventing a value.

    Resource `alignment_data`: the provider's own safety alignment corpus, as a list of samples the
    host's forward can consume together with a collated batch in the trainer's format
    (`input_ids`/`attention_mask`/`labels`, see `hf_trainer_ext.collate_texts`). No fedguard view
    carries it; without the model-side mechanism above it cannot be used by this plugin either.

    Cost: zero. No `model_handle` is declared and no pass is spent: the mechanism that would spend
    them (two forward/backward passes per step, ~2x SFT step time in the paper's Table 5) cannot be
    hosted, so there is nothing to charge for.
    """
    name, at, version = "vaccine_alignment", Stage.SERVER_DISTRIBUTE, "1"
    needs = frozenset()
    resources = frozenset({"alignment_data"})
    acts = frozenset()

    def run(self, ctx):
        why = ("Vaccine perturbs each layer's hidden embedding between two forward passes; fedguard exposes "
               "neither the layer outputs nor a way to modify a pass in flight.")
        return ctx.findings(evidence={"not_expressible": why})
