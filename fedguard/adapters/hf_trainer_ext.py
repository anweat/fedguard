"""Trainer extension layer: opens the point between the forward pass and backward of a Hugging Face
`Trainer` / `SFTTrainer` to plugins (stage CLIENT_LOSS, data kind `loss`, action `transform_loss`).

    trainer = extend_trainer(trainer, guard)          # after the host built its trainer, before trainer.train()
    trainer = extend_trainer(trainer, guard, identify=identify_from_dataset(trainer.train_dataset, guard.training_hashes()))
                                                      # the same, and plugins can tell which samples a batch holds
    trainer.add_callback(GuardStepCallback(guard, lora_state=get_peft_model_state_dict))

THIS IS NOT THE HOST'S ORIGINAL BEHAVIOR. A Trainer offers callbacks before the optimizer step and
after it, and nothing in between the forward pass and backward; the host frameworks build on that.
This layer replaces the `compute_loss` method of the trainer object the host built with a wrapper
around it. Switching it on emits a HostExtensionWarning and writes "trainer" into the run's record
(`host_extensions`), the same way the Flower handshake layer does.

What the wrapper does and does not change:
  - The host's own `compute_loss` (including a subclass's, e.g. OpenFedLLM's FedProx and SCAFFOLD
    trainers) still computes the loss; plugins get its result. It is asked for the model outputs as
    well (`return_outputs=True`), which the stock implementations compute anyway.
  - With report-only plugins, or with actions off, the tensor handed back to the Trainer is the host's
    own, and training is bit-for-bit what it was. Plugin code runs under the runner's RNG isolation, so
    an extra forward pass with dropout does not shift the host's random stream.
  - Only training steps are intercepted. Evaluation calls of `compute_loss` pass through.
What stays out of reach: the forward pass itself (attention scores, intermediate activations need
`output_attentions` / `output_hidden_states` set by the app, or hooks the plugin places itself), the
optimizer, and the order of batches. With several GPUs under DataParallel the loss is a vector and the
layer refuses to run.

Cost: a plugin's own extra passes. `LossView.loss_on` is one forward pass per call;
`LossView.gradients_of` one backward pass per call (per-sample gradients of a batch of B samples: B).
"""
from __future__ import annotations

import warnings

import torch

from fedguard.adapters.hosts import TRAINER_EXTENSION, HostExtensionWarning
from fedguard.client import ClientGuard
from fedguard.views.client import LossView

EXTENSION = "trainer"                      # the name it has in every host profile and in the record


def row_key(ids) -> tuple:
    return tuple(int(t) for t in ids)


def identify_from_dataset(dataset, hashes: list[str], pad_token_id: int | None = None):
    """A function batch -> sample hashes, for `extend_trainer(identify=...)`.

    dataset: the trainer's tokenized training set (`trainer.train_dataset`), row i being sample i of what
    the client trains on; hashes: `guard.training_hashes()`. Rows are matched by their token ids with the
    padding removed, so two samples with identical tokens share whichever hash came last (identical text
    has an identical hash anyway). A row that was truncated or re-tokenized differently by the collator
    is not matched and gets None."""
    if len(dataset) != len(hashes):
        raise ValueError(f"the training set has {len(dataset)} rows but {len(hashes)} sample hashes were given")
    def unpadded(row) -> tuple:
        ids, mask = row["input_ids"], row.get("attention_mask")
        return row_key(t for t, m in zip(ids, mask) if m) if mask is not None else row_key(ids)
    table = {unpadded(dataset[i]): h for i, h in enumerate(hashes)}

    def identify(batch: dict) -> list[str | None]:
        ids, mask = batch["input_ids"], batch.get("attention_mask")
        out = []
        for k in range(ids.shape[0]):
            row = ids[k][mask[k].bool()] if mask is not None else ids[k]
            out.append(table.get(row_key(row.tolist())))
        return out
    return identify


def extend_trainer(trainer, guard: ClientGuard, identify=None):
    """Wrap `trainer.compute_loss` so that every training step runs CLIENT_LOSS. Returns the same trainer.
    identify: batch -> the sample hash of each row (see identify_from_dataset); without it
    `LossView.sample_ids()` raises.

    Call it once per trainer object. Without a plugin mounted at CLIENT_LOSS nothing is wrapped and no
    warning is emitted: the trainer stays the host's.
    """
    if not guard.has_loss_plugins:
        return trainer
    if getattr(trainer, "_fedguard_loss_hook", None) is not None:
        raise RuntimeError("this trainer is already extended")
    text = f"fedguard extension {EXTENSION!r} is on: this is not the host's original behavior. It {TRAINER_EXTENSION[1]}."
    warnings.warn(text, HostExtensionWarning, stacklevel=2)
    runner = guard.runner
    runner.host_extensions = sorted({*runner.host_extensions, EXTENSION})
    if runner.recorder is not None:                         # the record names the layer, whoever switched it on
        runner.recorder.write_run(runner.describe())
    host_loss = trainer.compute_loss                        # the bound method of whatever class the host used

    def compute_loss(model, inputs, return_outputs=False, **kwargs):
        if not model.training:
            return host_loss(model, inputs, return_outputs=return_outputs, **kwargs)
        loss, outputs = host_loss(model, inputs, return_outputs=True, **kwargs)
        if loss.dim() != 0:
            raise RuntimeError("the trainer extension needs a scalar loss (no DataParallel)")
        view = LossView(loss, outputs, inputs, model.named_parameters(),
                        loss_on=lambda batch: host_loss(model, batch, return_outputs=False, **kwargs), identify=identify)
        new = guard.on_loss(trainer.state.global_step + 1, view)
        return (new, outputs) if return_outputs else new

    trainer.compute_loss = compute_loss
    trainer._fedguard_loss_hook = host_loss
    guard.loss_hooked = True
    return trainer


def collate_texts(tokenizer, texts: list[str], max_length: int = 512) -> dict[str, torch.Tensor]:
    """A batch in the Trainer's format from plain texts, with the loss on every non-padding token. For
    defender-supplied second data sources (alignment data) handed to `LossView.loss_on`."""
    enc = tokenizer(list(texts), return_tensors="pt", padding=True, truncation=True, max_length=max_length)
    labels = enc["input_ids"].clone()
    labels[enc["attention_mask"] == 0] = -100
    return {"input_ids": enc["input_ids"], "attention_mask": enc["attention_mask"], "labels": labels}
