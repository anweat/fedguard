"""Client-side capture: what one client received, trained on, did, and is about to upload.

Framework-neutral. A training loop (or an adapter: fedguard.adapters.flower_client,
fedguard.adapters.hf_trainer) calls, per round:

    guard.begin_round(round, received_lora, data=DataView(samples, text_of=...))   # CLIENT_PRE_TRAIN
    samples = guard.training_samples()                                             # after applied sample actions
    loss = guard.on_loss(step, LossView(...))                                      # CLIENT_LOSS, trainer extension only
    guard.on_gradients(step, model.named_parameters())                             # CLIENT_PRE_STEP, before optimizer.step()
    guard.on_step(step, {"loss": ..., "lr": ...}, lora=lambda: lora_state(model))  # CLIENT_STEP, after each step
    guard.snapshot(step, lora)                                                     # optional, every snapshot_every steps
    guard.before_upload(local_lora, {"num_examples": n})                           # CLIENT_POST_TRAIN
    guard.end_round()

When client plugins need an answer from the server before training starts, the round opens with an
exchange instead: begin_round(..., defer=True); announce() runs CLIENT_ANNOUNCE and returns what to send;
deliver(...) hands in the server's reply; pre_train() then runs CLIENT_PRE_TRAIN.

The client's record mirrors the server's (see fedguard.recorder.store): `received` and `local` are
content-hashed, so they can be compared with the server's `base` and `client_<id>` after the fact.
Sample text is never written; the manifest holds hashes, source tags and lengths.
"""
from __future__ import annotations

import torch

from fedguard.core.runner import GuardRunner
from fedguard.core.types import Decision, Findings, Stage
from fedguard.views.client import DataView, GradientView, LossView, ModelStateView, TraceView, sample_hash
from fedguard.views.uploads import ReportView


def _snapshot(state: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {k: v.detach().to("cpu", copy=True) for k, v in state.items()}


class ClientGuard:
    """One client's side of the library for the whole run: holds what the client received and is training on,
    runs the client-side stages when the training code (or an adapter) reports that a point was reached,
    and writes the client's own record. One instance per client; `begin_round` ... `end_round` per round.
    """
    def __init__(self, client_id: str, runner: GuardRunner | None = None, recorder=None, snapshot_every: int = 0):
        """runner: a GuardRunner(side="client"); None captures without running plugins.
        recorder: a Recorder(scope=client_id); None runs plugins without recording.
        snapshot_every: store the LoRA factors handed to snapshot() every N steps (0 = never).
        """
        if runner is not None and runner.side != "client":
            raise ValueError("ClientGuard needs a client-side runner")
        self.client_id, self.runner, self.recorder, self.snapshot_every = client_id, runner, recorder, snapshot_every
        if runner is not None and recorder is not None and runner.recorder is None:
            runner.recorder = recorder
            recorder.write_run(runner.describe())
        mounted = {s for p in (runner.plugins if runner is not None else []) for s in p.stages}
        self._has_step_plugins, self._has_grad_plugins = Stage.CLIENT_STEP in mounted, Stage.CLIENT_PRE_STEP in mounted
        self._has_announce = Stage.CLIENT_ANNOUNCE in mounted
        self.has_loss_plugins = Stage.CLIENT_LOSS in mounted
        self.loss_hooked = False                 # set by the trainer extension layer once it wraps a trainer
        self._attachments: dict = {}
        self._lora_now = None
        self._received_view = None
        self._round: int | None = None
        self._received: dict[str, torch.Tensor] = {}
        self._previous: dict[str, torch.Tensor] | None = None
        self._data: DataView | None = None
        self._steps: list[dict] = []
        self._reported: dict = {}
        self._messages: dict = {}
        self._model_handle = None
        self._local: dict[str, torch.Tensor] = {}
        self._pre_train = "pending"

    def _scale(self) -> float:
        return self.runner.spec.lora_scale if self.runner is not None else 1.0

    def _run(self, stage: Stage, **more) -> list[Findings]:
        if self.runner is None:
            return []
        if self._received_view is None:
            self._received_view = ModelStateView(self._received, self._previous, self._scale())
        views = {"received_model": self._received_view,
                 "train_trace": TraceView(self._steps, self._lora_now),
                 "reports": ReportView({self.client_id: self._reported}, {"server": self._messages},
                                       {"server": self._attachments}), **more}
        if self._data is not None:
            views["data"] = self._data
        if self._model_handle is not None:
            views["model_handle"] = self._model_handle
        return self.runner.run(stage, [self.client_id], **views)

    # ----- round lifecycle -----
    def begin_round(self, round_idx: int, received: dict[str, torch.Tensor], data: DataView | None = None,
                    model_handle=None, messages: dict | None = None, defer: bool = False,
                    attachments: dict | None = None) -> list[Findings]:
        """Record what arrived and run CLIENT_PRE_TRAIN. `messages` and `attachments` are what the
        server's plugins sent over the channel.

        defer=True only records the received model; the stage runs when pre_train() is called. This is
        for adapters that see the message before the training code has loaded its data, and for rounds
        that open with an announce exchange.
        """
        self._round, self._data, self._steps, self._reported = round_idx, data, [], {}
        self._model_handle, self._messages, self._pre_train = model_handle, dict(messages or {}), "pending"
        self._attachments, self._lora_now, self._announced = dict(attachments or {}), None, False
        self._received_view = None
        self._received = _snapshot(received)
        if self._previous is None and self.recorder is not None:      # a fresh process: read back the last one
            earlier = [t for t in self.recorder.rounds() if t < round_idx and self.recorder.has_object(t, "received")]
            if earlier:
                self._previous = self.recorder.load_object(earlier[-1], "received")
        if self.runner is not None:
            self.runner.begin_round(round_idx)
        if self.recorder is not None:
            self.recorder.write_object(round_idx, "received", self._received)
        return [] if defer else self.pre_train()

    @property
    def wants_exchange(self) -> bool:
        """True when a mounted plugin runs at CLIENT_ANNOUNCE, i.e. the round should open with an exchange."""
        return self._has_announce

    @property
    def announced_round(self) -> int | None:
        """The round that was opened with an announce and has not been trained yet; None otherwise."""
        return self._round if getattr(self, "_announced", False) and self._pre_train == "pending" else None

    def announce(self, data: DataView | None = None, model_handle=None) -> tuple[dict, dict]:
        """Run CLIENT_ANNOUNCE and return (messages, tensors) for the server's SERVER_EXCHANGE stage."""
        if self._round is None:
            raise RuntimeError("call begin_round() first")
        self._data = data if data is not None else self._data
        self._model_handle = model_handle if model_handle is not None else self._model_handle
        self._run(Stage.CLIENT_ANNOUNCE)
        self._announced = True
        if self.runner is None:
            return {}, {}
        out = self.runner.outbox(), self.runner.outbox_tensors()
        self.runner.clear_outbox()
        return out

    def deliver(self, messages: dict | None = None, attachments: dict | None = None) -> None:
        """Hand in what the server answered during the exchange; visible to CLIENT_PRE_TRAIN and later stages."""
        self._messages.update(messages or {})
        self._attachments.update(attachments or {})

    def pre_train(self, data: DataView | None = None, model_handle=None, timing: str = "on_time") -> list[Findings]:
        """Record the data manifest and run CLIENT_PRE_TRAIN. Once per round."""
        if self._round is None:
            raise RuntimeError("call begin_round() first")
        if self._pre_train != "pending":
            raise RuntimeError("pre_train() already ran this round")
        self._pre_train = timing
        self._data = data if data is not None else self._data
        self._model_handle = model_handle if model_handle is not None else self._model_handle
        if self.recorder is not None and self._data is not None:
            self.recorder.write_lines(self._round, "manifest", [
                {"i": r.index, "hash": r.hash, "source": r.source, "length": r.length} for r in self._data.manifest])
        return self._run(Stage.CLIENT_PRE_TRAIN)

    def start_state(self) -> dict[str, torch.Tensor]:
        """The LoRA to start local training from: what was received, or what an applied
        `transform_received` made of it. The upload is still measured against what was received."""
        changed = self.runner.received() if self.runner is not None else None
        if changed is not None and self.recorder is not None and not self.recorder.has_object(self._round, "start"):
            self.recorder.write_object(self._round, "start", changed)
        return dict(changed if changed is not None else self._received)

    def training_samples(self) -> list:
        """The samples to train on this round: the announced data after every applied `mask_samples` and
        `edit_samples` action. Without such actions this is the announced data, in order."""
        if self._data is None:
            raise LookupError("no data was announced this round")
        masked = self.runner.masked() if self.runner is not None else set()
        added, rewritten = self.runner.sample_edits() if self.runner is not None else ([], {})
        out = [rewritten.get(r.hash, s) for r, s in zip(self._data.manifest, self._data.samples()) if r.hash not in masked]
        return out + [s for _, s in added]

    def training_hashes(self) -> list[str]:
        """The hash of each of training_samples(), in the same order: the manifest hash for an untouched
        sample, the hash of the new text for a rewritten or added one."""
        if self._data is None:
            raise LookupError("no data was announced this round")
        masked = self.runner.masked() if self.runner is not None else set()
        added, rewritten = self.runner.sample_edits() if self.runner is not None else ([], {})
        text = self._data._text_of
        out = [sample_hash(text(rewritten[r.hash])) if r.hash in rewritten else r.hash for r in self._data.manifest if r.hash not in masked]
        return out + [sample_hash(text(s)) for _, s in added]

    def log(self, step: int, scalars: dict[str, float]) -> None:
        """Record a step's scalars without running plugins. Scalars of the same step are merged."""
        if self._round is None:
            raise RuntimeError("call begin_round() first")
        row = {k: float(v) for k, v in scalars.items()}
        if self._steps and self._steps[-1]["step"] == int(step):
            self._steps[-1].update(row)
        else:
            self._steps.append({"step": int(step), **row})

    def on_loss(self, step: int, view: LossView) -> torch.Tensor:
        """The batch loss is computed and backward has not run: run CLIENT_LOSS and return the loss to
        back-propagate, which is the host's own tensor unless an applied `transform_loss` replaced it."""
        if self.has_loss_plugins:
            self.log(step, {})
            self.runner.begin_step(step)
            self._run(Stage.CLIENT_LOSS, loss=view)
        return view.loss

    def on_gradients(self, step: int, named_parameters) -> None:
        """Gradients are computed and the optimizer has not stepped: run CLIENT_PRE_STEP.
        Does nothing unless a plugin is mounted there."""
        if self._has_grad_plugins:
            self.log(step, {})
            self.runner.begin_step(step)
            self._run(Stage.CLIENT_PRE_STEP, gradients=GradientView(named_parameters))

    def on_step(self, step: int, scalars: dict[str, float], lora=None) -> None:
        """Record one finished training step and run CLIENT_STEP. `lora` is a function returning the
        current LoRA state; it is only called if a plugin asks for it. Without plugins at this stage
        the cost is a dict update."""
        self.log(step, scalars)
        if self._has_step_plugins:
            self.runner.begin_step(step)
            self._lora_now = lora
            try:
                self._run(Stage.CLIENT_STEP)
            finally:
                self._lora_now = None

    def wants_snapshot(self, step: int) -> bool:
        return bool(self.snapshot_every) and self.recorder is not None and step % self.snapshot_every == 0

    def snapshot(self, step: int, lora: dict[str, torch.Tensor]) -> None:
        """Store the LoRA factors at this step if it falls on the snapshot interval."""
        if self.wants_snapshot(step):
            self.recorder.write_object(self._round, f"step_{int(step):06d}", lora)

    def before_upload(self, local: dict[str, torch.Tensor], reported: dict[str, float] | None = None) -> list[Findings]:
        """Record the local result and what the client is about to claim, then run CLIENT_POST_TRAIN."""
        if self._round is None:
            raise RuntimeError("call begin_round() first")
        if self._pre_train == "pending":     # the training code never announced its data: run the stage late, and say so
            self.pre_train(timing="late")
        self._local = _snapshot(local)
        self._reported = dict(reported or {})
        if self.recorder is not None:
            self.recorder.write_object(self._round, "local", self._local)
        found = self._run(Stage.CLIENT_POST_TRAIN, local_update=ModelStateView(self._local, self._received, self._scale()))
        changed = self.runner.transformed().get(self.client_id) if self.runner is not None else None
        if changed is not None:                       # an applied transform_update: this is what gets uploaded
            self._local = changed
            if self.recorder is not None:
                self.recorder.write_object(self._round, "upload", changed)
        return found

    def kept_indices(self) -> list[int]:
        """Indices of this round's samples that no applied `mask_samples` action removed. Train on these."""
        if self._data is None:
            raise LookupError("no data was announced this round")
        masked = self.runner.masked() if self.runner is not None else set()
        return [r.index for r in self._data.manifest if r.hash not in masked]

    def upload_state(self) -> dict[str, torch.Tensor]:
        """The LoRA to upload: the local result, or what an applied `transform_update` made of it."""
        return dict(self._local)

    def outbox(self) -> dict[str, object]:
        """Messages this round's client plugins addressed to the server; the adapter sends them with the upload."""
        return self.runner.outbox() if self.runner is not None else {}

    def outbox_tensors(self) -> dict[str, torch.Tensor]:
        """Tensors this round's client plugins addressed to the server."""
        return self.runner.outbox_tensors() if self.runner is not None else {}

    def end_round(self, meta: dict | None = None) -> None:
        meta = {"client_id": self.client_id, "steps": len(self._steps),
                "samples": len(self._data) if self._data is not None else None,
                "reported": self._reported, "messages": self._messages, "pre_train": self._pre_train,
                "masked": len(self.runner.masked()) if self.runner is not None else 0,
                "announced": self._announced, **(meta or {})}
        added, rewritten = self.runner.sample_edits() if self.runner is not None else ([], {})
        if self.recorder is not None and self._data is not None and (added or rewritten):
            text = self._data._text_of           # what was actually trained on, by hash and origin
            rows = [{"hash": sample_hash(text(rewritten[r.hash])), "origin": f"rewritten:{r.hash}"} if r.hash in rewritten
                    else {"hash": r.hash, "origin": "original"}
                    for r in self._data.manifest if r.hash not in self.runner.masked()]
            rows += [{"hash": sample_hash(text(s)), "origin": f"added:{plugin}"} for plugin, s in added]
            self.recorder.write_lines(self._round, "training_set", rows)
        meta["added"], meta["rewritten"] = len(added), len(rewritten)
        if self.recorder is not None and self._steps:
            self.recorder.write_lines(self._round, "trace", self._steps)
        if self.runner is not None:
            self.runner.end_round(meta)              # writes round.json through the runner's recorder
        elif self.recorder is not None:
            self.recorder.write_round(self._round, findings=[], decision=Decision(), rejected={}, meta=meta)
        self._previous, self._round, self._data = self._received, None, None
