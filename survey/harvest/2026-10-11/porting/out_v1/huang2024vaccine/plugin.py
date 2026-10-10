# plugin.py
"""Vaccine -- perturbation-aware alignment (Huang et al., 2024): declaration-only shell.

This module is deliberately not an implementation. Vaccine is a centralized alignment
*training procedure*, and none of the three capabilities it needs is present in the plugin
interface, so the shell only declares where the method would have to mount and fails loudly
if it is ever run. See the class docstring and the port report for the full accounting.
"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage

__all__ = ["Vaccine"]


class Vaccine(GuardPlugin):
    """Perturbation-aware alignment (Vaccine), Huang et al. 2024.

    The paper trains the provider's own alignment SFT so that the aligned model stays safe
    after later user fine-tuning. Each alignment step: (1) sample a batch of safe QA pairs;
    (2) run forward+backward and collect dL/de_l for every layer's hidden embedding;
    (3) concatenate those gradients and take one global L2 norm; (4) set
    eps_l = rho * (dL/de_l) / ||concat_l dL/de_l|| per layer; (5) register forward hooks that
    replace each layer output f with f + eps_l; (6) run a second forward+backward at the
    perturbed embeddings to get the update gradient; (7) step AdamW; (8) repeat, with the
    accelerated variant recomputing eps only every tau steps; (9) merge the alignment LoRA
    into the base model. The paper's own analysis maps the method to server_distribute with
    transform_gradients; the report records why neither holds here.

    Implemented:
      Nothing of the method's computation. This file is a declaration-only shell: it records
      where Vaccine would have to mount -- SERVER_DISTRIBUTE, reading `outgoing` and
      `model_handle`, with the alignment corpus as a resource -- and `run` raises instead of
      pretending to defend. No step of the pipeline (1-9) is ported, because the three
      capabilities the method is made of are all absent (see Not implemented), and the
      remaining host-shaped steps (1, 7, 8, 9) have no server-side training loop here to
      attach to. There is therefore no computation this class could honestly carry, not even
      the perturbation formula itself: it is trivial arithmetic, but its input (per-layer
      embedding gradients) cannot be obtained, so implementing it would only add dead code.

    Deviations:
      Vaccine is centralized and pre-deployment: it produces the model that is later handed
      to users and leaves user fine-tuning untouched (App. E). The library intervenes only
      inside a federated round of that fine-tuning, so there is no alignment stage to mount
      on. The paper's own mapping (stages: [server_distribute], actions:
      [transform_gradients]) does not close the gap: ACTION_STAGES puts transform_gradients at
      CLIENT_PRE_STEP only, on the other side, and SERVER_DISTRIBUTE offers only
      transform_broadcast -- it can carry an already-aligned state, not train one. The rule-4
      substitution (a LoRA factor-space update vector) does not apply either: Vaccine consumes
      no client uploads, its output is a model trained by its own loop. No client/server
      exchange is involved (the paper's needs_round_trip is false).

    Not implemented:
      The whole pipeline (steps 1-9). The library has no server-side training stage: its
      server stages are trust boundaries of the host's aggregation, and the only stages that
      sit inside a training step (CLIENT_LOSS, CLIENT_PRE_STEP, CLIENT_STEP) belong to a
      client's own fine-tuning, which the paper explicitly does not modify. Three
      capabilities are absent from the listed interface:
        - dL/de_l for every layer. There is no activation-space gradient anywhere:
          GradientView, LossView.gradients_of and ModelHandle.per_sample_gradients are all
          parameter-space, while ModelHandle.hidden/activations return pooled, detached CPU
          tensors. Blocks steps 2-4.
        - a forward pass with eps_l added to each layer's output. ModelHandle.lora only swaps
          adapter weights, the handle must leave the model exactly as it found it, and no
          operator injects into a forward pass. Blocks steps 5-6.
        - an optimizer step on the server. No stage exposes the host's optimizer or a
          server-side gradient, and setup(spec) receives only a RunSpec (no model, no data).
          Blocks step 7.
      With steps 2-6 blocked, the batch sampler (1), the refresh rule (8, which only re-times
      2-6) and the merge (9) have nothing to attach to. The server also has no runnable model
      by default, so even the forward passes Vaccine needs may be unavailable there.
      The harmfulness evaluation (BeaverTails moderation model, harmful test instructions) is
      metrics, not defence, and is out of scope as well.

    Open in the paper and chosen here:
      - Mount point: SERVER_DISTRIBUTE reading `outgoing` and `model_handle`, with the
        alignment corpus as a resource. Chosen because the alignment product is the model
        distributed to clients and the paper's own analysis points there; it is a declaration
        of the missing interface, not a working plugin. (SERVER_POST_AGGREGATE +
        replace_global was the alternative and cannot train either.)
      - run() raises NotImplementedError rather than returning an empty Finding, so a
        deployment that mounts this shell fails loudly under a fail-closed runner instead of
        silently not defending.
      - Hyper-parameters of the (non-existent) alignment loop -- rho, batch size, AdamW
        settings, T, tau -- are not guessed here. The paper gives no main-experiment rho and
        no default tau.

    Cost:
      None. The shell spends no model passes and holds no state. The paper's own alignment
      loop costs about 2x SFT step time and +0.039 to +0.11 GB of memory (5.3, Table 5).

    Resource `alignment_data`: the provider's safe alignment QA pairs (paper: 2000
      BeaverTails harmful-prompt / safe-answer pairs), in whatever form the host's model
      handle accepts as samples. Declared for shape only; nothing consumes it here.
    """

    name, at, version = "vaccine", Stage.SERVER_DISTRIBUTE, "0"
    needs = frozenset({"outgoing", "model_handle"})
    resources = frozenset({"alignment_data"})
    acts = frozenset({"transform_broadcast"})

    def run(self, ctx):
        raise NotImplementedError(
            "Vaccine is not expressible with the fedguard plugin interface: the alignment "
            "stage needs dL/de_l for every layer, a forward pass with perturbed layer "
            "outputs, and a server-side optimizer step; none of these exists here. "
            "See the class docstring and the port report (missing_runtime)."
        )
