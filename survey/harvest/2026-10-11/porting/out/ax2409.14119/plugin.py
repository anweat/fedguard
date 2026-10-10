# plugin.py
"""Obliviate (ax2409.14119) as a fedguard plugin: the neuron amplification loss Lamp of a PEFT
fine-tuning step, added to the loss the client back-propagates.

The paper is a centralized, training-time defense. It freezes a possibly backdoored PLM, attaches
randomly initialized PEFT layers, and at every training step adds two terms to the clean downstream
task loss: a neuron amplification loss Lamp (Eq. 1) and an attention score regularization loss Lreg
(Eq. 2), back-propagating L = Ltask + lambda_amp * Lamp + lambda_reg * Lreg (Eq. 3). This file carries
Lamp, the half of Eq. 3 that needs only the PEFT weights; Lreg needs attention scores, which no view of
this library exposes (see the class docstring).
"""
from __future__ import annotations

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.ops import states


def amplification_penalty(factors: dict[str, torch.Tensor]) -> torch.Tensor:
    """Eq. (1): Lamp = -sum_p ||W_p||_2 over the given PEFT tensors, as a scalar with a graph.

    Differentiable, so it can be added to the loss the host back-propagates. fedguard.ops.states.norm
    computes the same number but returns a Python float, so it cannot be used inside a loss.
    """
    if not factors:
        raise ValueError("no PEFT tensors to amplify")
    return -torch.stack([t.norm() for t in factors.values()]).sum()


def lora_factor_params(named: dict[str, torch.nn.Parameter]) -> dict[str, torch.nn.Parameter]:
    """The LoRA decomposition matrices of named: entries whose name carries a lora_A/lora_B factor."""
    return {n: p for n, p in named.items() if states.module_info(n)["factor"] in ("A", "B")}


class ObliviateLamp(GuardPlugin):
    """Obliviate neuron amplification loss added to the loss of a local training step (Eq. 1 in Eq. 3).

    Implemented:
      - Lamp = -sum_p ||W_p||_2 over the trainable LoRA decomposition matrices of the model (Eq. 1),
        folded into the loss the host back-propagates: L = Ltask + lambda_amp * Lamp (Eq. 3 without the
        Lreg term). The term depends on the weights only, so its gradient is -lambda_amp * W/||W|| per
        factor: a step of an optimizer on that loss increases the Frobenius norm of every amplified
        factor.
      - The term is rebuilt from the live parameters at every CLIENT_LOSS call, i.e. every local training
        step the host reports. No state is kept between steps or rounds, matching the paper, which has no
        explicit accumulation mechanism: the amplification accumulates because the term is part of the
        objective of every step.

    Deviations:
      - Centralized method inside a federated client: the paper trains one PEFT model on clean data held
        by the defender. Here the same per-step objective sits in the local training of a client; the term
        itself is untouched by the federation. Nothing is proposed on the server side, where the paper
        (no clients, no aggregation, no communication) asks for nothing.
      - PEFT scope: the paper amplifies the up/down projections of adapter layers, the decomposition
        matrices of LoRA layers and the reparameterization matrices of prefix-tuning. This library
        carries LoRA factors, so only lora_A / lora_B tensors are amplified; adapter and prefix-tuning
        runs are out of scope.
      - Eq. 3 enters as a transform_loss proposal, i.e. as the scalar the host back-propagates, rather
        than by editing the training loop of the host.

    Not implemented:
      - Lreg (Eq. 2), the attention score regularization, and therefore the lambda_reg term of Eq. 3: no
        view of this library exposes attention scores. At CLIENT_LOSS the LossView holds the batch, the
        model outputs, the loss and the trainable parameters, and the trainer extension layer documents
        attention scores as out of reach (fedguard/adapters/hf_trainer_ext.py: they need
        output_attentions set by the app); the model handle offers submodule inputs/outputs, hidden
        states, tokens and losses, but not attention weights, and it exposes parameter names and shapes,
        not the frozen base weights, so softmax(QK^T) cannot be recomputed from a handle either.
      - The gradient-space equivalent of Lamp (adding -lambda_amp * W/||W|| to the LoRA gradients at
        CLIENT_PRE_STEP, which would not need the trainer extension): under the adaptive optimizers the
        paper uses, it is not equivalent to the loss term, because Adam-family updates divide each
        coordinate by its own second moment and so scale the two forms differently; the loss form of
        Eq. 3 is the one kept.
      - Freezing the PLM and attaching randomly initialized PEFT layers (step 1 of the paper), the
        optimizer step (step 5), the offline selection of lambda_amp / lambda_reg on a clean labelled
        validation set (step 6) and inference (step 7) are the work of the host, of the defender or of
        plain training, not of a plugin.

    Open in the paper and chosen here:
      - ||W_p||_2 is read as the Frobenius norm of each factor matrix (Tensor.norm()); the paper only
        writes L2-norm and does not say Frobenius or spectral.
      - lambda_amp defaults to 1e-3, the smallest of the four candidates the paper lists in Table 7
        (1e-3, 2e-3, 3e-3, 5e-3). The paper selects the largest candidate that costs no more than a 2%
        CACC drop on a clean labelled validation set, but never publishes the value it selected, and that
        selection needs a labelled validation set and retraining, so it stays outside the plugin. The
        default exists so that the class can be mounted with no arguments (the contract check builds
        every plugin as cls()); a deployment must pass the coefficient its own validation selection
        produced.
      - The amplified set is read off parameter names with fedguard.ops.states.module_info: every
        trainable parameter carrying a lora_A / lora_B factor. Other trainable tensors a PEFT
        configuration may add (e.g. modules_to_save) are left alone, matching the list of amplified
        matrices given in the paper.
      - No eps, clamp or normalization is added. A factor of zero norm takes the subgradient of the norm
        at zero, which is what PyTorch defines there; the paper gives no boundary handling.
      - The term is added at CLIENT_LOSS, the only point where the task loss of the host is still
        attached to the graph (trainer extension layer only).

    Cost:
      - No model pass and no extra activation memory: the term is read off parameters the host already
        holds, and the backward pass through it is the one the host already runs. One norm per LoRA factor
        per training step, i.e. O(number of adapter tensors).
      - The point is only opened by fedguard.adapters.hf_trainer_ext.extend_trainer; a plain Trainer
        callback never reaches CLIENT_LOSS.
    """

    name, at, version = "obliviate_lamp", Stage.CLIENT_LOSS, "1"
    needs, resources, acts = frozenset({"loss"}), frozenset(), frozenset({"transform_loss"})

    def __init__(self, lambda_amp: float = 1e-3):
        """lambda_amp: weight of Lamp in Eq. (3), selected by the defender on a clean validation set.
        The default 1e-3 is the smallest candidate in the paper Table 7 (see the class docstring)."""
        self.lambda_amp = float(lambda_amp)

    def run(self, ctx):
        view = ctx.loss
        factors = lora_factor_params(view.parameters())
        if not factors:
            return ctx.findings(evidence={"skipped": "no trainable lora_A/lora_B factor at this step"})
        lamp = amplification_penalty(factors)
        with torch.no_grad():
            amplified = float(sum(p.norm() for p in factors.values()))
        return ctx.findings(
            proposals={"loss": view.loss + self.lambda_amp * lamp},
            evidence={"lambda_amp": self.lambda_amp, "lamp": float(lamp.detach()),
                      "amplified_norm": amplified, "tensors": len(factors)},
        )
