"""Training-step injection for Hugging Face `Trainer` / `SFTTrainer`, through a TrainerCallback.

    trainer.add_callback(GuardStepCallback(guard, lora_state=get_peft_model_state_dict))

What the callback connects:
  on_pre_optimizer_step   CLIENT_PRE_STEP: gradients are computed and can be read or (through the
                          `transform_gradients` action) changed before the optimizer uses them
  on_step_end             CLIENT_STEP: the step is done; plugins can ask for the current LoRA
  on_log                  the Trainer's own scalars (loss, learning rate, ...) go into the trace at its
                          logging interval; set logging_steps=1 for a per-step trace
With `guard.snapshot_every` > 0 the LoRA factors are also stored at that interval.

Limits: the callback sees whole-batch gradients, not per-sample ones, and not which samples were in
the batch. The batch, the model outputs and the loss before backward are outside what a callback can
reach; fedguard.adapters.hf_trainer_ext opens that point (stage CLIENT_LOSS) as an extension layer that
changes the trainer object. A plugin mounted there is refused here unless that layer is on.
With gradient accumulation, `on_pre_optimizer_step` fires once per optimizer step, on the accumulated gradient.
"""
from __future__ import annotations

import math
from collections.abc import Callable

from transformers import TrainerCallback

from fedguard.client import ClientGuard
from fedguard.core.plugin import ContractError


class GuardStepCallback(TrainerCallback):
    """Connects a ClientGuard to the callbacks of a Trainer (CLIENT_PRE_STEP, CLIENT_STEP, the scalar trace).
    lora_state: model -> its LoRA state dict; given, plugins can read the LoRA after every step and
    `guard.snapshot_every` takes effect. Uses only the Trainer's own extension points.
    """
    def __init__(self, guard: ClientGuard, lora_state: Callable | None = None):
        self.guard, self.lora_state = guard, lora_state

    def on_train_begin(self, args, state, control, **kwargs):
        if self.guard.has_loss_plugins and not self.guard.loss_hooked:
            raise ContractError("a plugin is mounted at client_loss, which a Trainer callback cannot reach: wrap the "
                                "trainer with fedguard.adapters.hf_trainer_ext.extend_trainer (an extension layer)")

    def on_pre_optimizer_step(self, args, state, control, model=None, **kwargs):
        if model is not None:
            self.guard.on_gradients(state.global_step + 1, model.named_parameters())

    def on_step_end(self, args, state, control, model=None, **kwargs):
        lora = (lambda: self.lora_state(model)) if self.lora_state is not None and model is not None else None
        self.guard.on_step(state.global_step, {}, lora=lora)
        if lora is not None and self.guard.wants_snapshot(state.global_step):
            self.guard.snapshot(state.global_step, lora())

    def on_log(self, args, state, control, logs=None, **kwargs):
        scalars = {k: v for k, v in (logs or {}).items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)}
        if scalars:
            self.guard.log(state.global_step, scalars)

