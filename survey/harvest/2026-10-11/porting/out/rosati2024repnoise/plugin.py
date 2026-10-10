# plugin.py
"""RepNoise (Rosati et al., 2024) -- a mountable shell of a method fedguard has no runtime for.

Verdict of this port: `not_expressible`. RepNoise is not a detector and not an intervention on an
upload: it is a one-off immunization training of the provider model, run before the weights are
released, with its own optimizer, its own paired refusal corpus, a loss that reads the post-MLP
pre-residual activation of every layer through the language-model head, and a weight update over the
whole model. The class below mounts at the one stage where the output of the method could be
delivered and reports the blockers; it computes nothing. The report beside this file carries the
extraction needs, the missing runtime and the points that the paper leaves open.
"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class RepNoiseImmunization(GuardPlugin):
    """RepNoise (Rosati et al., 2024): immunize the model that the provider is about to release.

    Train the aligned model once on paired refusal data under three terms -- a causal language-model
    loss on the safe answer, an MMD between the harmful activation of each layer and N(0, I), and the
    log of the mean per-layer language-model loss on the harmful answer -- so that a later harmful
    fine-tuning attack cannot bring the harmful behaviour back. The paper runs this outside training on
    the model and data of the defender and releases the resulting checkpoint.

    Implemented:
        Nothing. `run` performs no update and returns an evidence-only report, so that the refusal is
        visible in the record of a round instead of being silent. What the shell does exercise is the
        placement a port would use: it mounts at SERVER_POST_AGGREGATE, the stage the extraction maps
        the pre-release immunization to, where `replace_global` is the action that would deliver the
        immunized global model, and it takes part in a real round without proposing anything.

    Deviations:
        The paper is centralized and its own position is outside training; mapping it to
        SERVER_POST_AGGREGATE plus replace_global is a choice of this port (the position that the
        extraction card suggests for a federated run), not a statement of the paper.
        No stand-in is fabricated for the unported steps. The nearest thing the runtime can express --
        per-sample gradients of the harmful loss through ModelHandle.per_sample_gradients, added to the
        gradients of the client through transform_gradients -- is ascent-only, drops the noise term
        that the paper shows is half of the method, works on LoRA factors while the paper updates every
        weight, and would run the immunization of the defender inside the training step of the
        attacker. That is a different method, so it is not proposed.
        A defender who immunizes the model outside the library could hand the result in as a resource
        and let a one-line plugin replace the global model. That carries the artifact and no step of
        the method, and it is the outside-training placement again, so it is not written as a partial
        port either.

    Not implemented:
        Steps 2-9 of the extraction: the safe-answer loss, the capture of the post-MLP pre-residual
        activation of every layer with its graph, the layer-wise language-model loss, the Gaussian
        noise draw, the MMD noise term, the layer mean, the log compression and the composition.
        - The activations exist but are detached and on the CPU: ModelHandle.activations captures the
          output of the MLP, which is exactly the position the paper asks for, and HFModelHandle
          stores what its hook sees as `.detach()`ed; ModelHandle.hidden returns the post-residual
          state that the paper rejects.
        - No interface applies the language-model head, or any module, to a tensor, so the layer-wise
          ascent loss has no expression; parameters() and layout() give names and shapes, never weights.
        - No operator computes a kernel MMD, and with a detached input a helper at module level could
          only return a number, not a loss term.
        - No server-side optimizer and no backward pass for a scalar built by a plugin; the server has
          no training step and the client-side points belong to the loop of the host.
        - The deliverable is a full checkpoint, while replace_global carries a LoRA state that must
          match the keys and shapes of the aggregate.

    Open in the paper and chosen here:
        Nothing is chosen, because nothing runs. The points that a future implementation has to decide
        -- the binding of alpha and beta that the paper contradicts itself about, the configuration of
        the MMD kernel, the way the shared-token MASK is applied, whether the paired batches are
        aligned, whether the layer-wise logits are detached -- are in the report, under `open_choices`
        and `needs_from_authors`.

    Cost:
        Zero: no data kind is declared, no resource is taken, no action is proposed and no model pass
        is spent. The computation that the paper reports at 1:52 on 4xA40s for 10k pairs, 26.37 GB per
        card, has no place to run here.
    """
    name, at, version = "repnoise_immunization", Stage.SERVER_POST_AGGREGATE, "1"
    needs = frozenset()
    resources = frozenset()
    acts = frozenset()

    def run(self, ctx):
        return ctx.findings(evidence={
            "not_expressible": "RepNoise is a one-off immunization training of the released model, and fedguard "
                               "has no stage outside a round, no differentiable intermediate activation, no way "
                               "to apply the language-model head to one, no optimizer on the server, and a LoRA "
                               "state rather than a full checkpoint as its server-side currency.",
            "blocked_steps": "2-9 of the extraction: stability loss, activation capture, layer-wise ascent, "
                             "noise draw, MMD, layer mean, log compression, composition",
        })
