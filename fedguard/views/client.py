"""Client-side views: local data, the received global model, the training trace, the local result.

Nothing here leaves the client. Samples themselves are only reachable through `DataView.samples()`;
what the capture base stores about them is a hash, a source tag and a length.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

import torch

from fedguard.ops.lowrank import LowRank
from fedguard.views.uploads import _A, _B, lora_modules


def sample_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SampleRecord:
    """What the capture base keeps about one local sample."""
    index: int
    hash: str
    source: str
    length: int


class DataView:
    """`data`: this client's local samples for the round.

    text_of turns a sample into the text that is hashed (and whose length is recorded);
    source_of gives a provenance tag for a sample, e.g. the dataset or file it came from.
    """

    def __init__(self, samples: Sequence, text_of: Callable = str, source_of: Callable = lambda s: ""):
        self._samples, self._text_of, self._source_of = samples, text_of, source_of
        self._manifest: list[SampleRecord] | None = None

    def __len__(self) -> int:
        return len(self._samples)

    def samples(self) -> Iterable:
        """The raw samples. Local use only."""
        return iter(self._samples)

    def text(self, index: int) -> str:
        return self._text_of(self._samples[index])

    @property
    def manifest(self) -> list[SampleRecord]:
        if self._manifest is None:
            out = []
            for i, s in enumerate(self._samples):
                t = self._text_of(s)
                out.append(SampleRecord(i, sample_hash(t), str(self._source_of(s)), len(t)))
            self._manifest = out
        return self._manifest


class ModelStateView:
    """`received_model` / `local_update`: a LoRA state held by this client, with its reference state.

    For `received_model`, the reference is the global LoRA received in the previous round the client
    took part in (None the first time). For `local_update`, it is this round's received model.
    """

    def __init__(self, state: dict[str, torch.Tensor], reference: dict[str, torch.Tensor] | None = None,
                 lora_scale: float = 1.0):
        self._state, self._reference, self.scale = state, reference, lora_scale
        self.modules = lora_modules(state)

    def state(self) -> dict[str, torch.Tensor]:
        """Read-only by convention; do not modify in place."""
        return dict(self._state)

    def replace(self, state: dict[str, torch.Tensor]) -> None:
        """Used by the runner when an applied `transform_update` replaces the local result."""
        self._state = dict(state)

    def reference(self) -> dict[str, torch.Tensor] | None:
        return dict(self._reference) if self._reference is not None else None

    def factors(self, module: str) -> tuple[torch.Tensor, torch.Tensor]:
        return self._state[module + _A], self._state[module + _B]

    def product(self, module: str) -> LowRank:
        A, B = self.factors(module)
        return LowRank.lora(B, A, self.scale)

    def increment(self, module: str) -> LowRank:
        """Functional change of one module relative to the reference state, rank <= 2r."""
        if self._reference is None:
            raise LookupError("no reference state: this is the first model this client received")
        A, B = self.factors(module)
        return LowRank.increment(B, A, self._reference[module + _B], self._reference[module + _A], self.scale)

    def factor_delta_norms(self) -> dict[str, float]:
        """Per factor, the norm of (state - reference). The cheapest consistency signal a client has
        about what the server sent it."""
        if self._reference is None:
            raise LookupError("no reference state: this is the first model this client received")
        return {k: float((v.double() - self._reference[k].double()).norm()) for k, v in self._state.items()
                if k in self._reference and v.shape == self._reference[k].shape}


class TraceView:
    """`train_trace`: per-step scalars recorded so far this round, in step order, and the LoRA as it is
    right now when the training loop offers it."""

    def __init__(self, steps: list[dict], lora=None):
        self._steps, self._lora = steps, lora

    def __len__(self) -> int:
        return len(self._steps)

    def steps(self) -> list[dict]:
        return [dict(s) for s in self._steps]

    def last(self) -> dict | None:
        return dict(self._steps[-1]) if self._steps else None

    def series(self, key: str) -> list[tuple[int, float]]:
        return [(s["step"], s[key]) for s in self._steps if key in s]

    def lora(self) -> dict[str, torch.Tensor]:
        """The LoRA factors at this point of local training (a CPU copy, made when called)."""
        if self._lora is None:
            raise LookupError("the training loop did not offer the current LoRA at this step")
        return {k: v.detach().to("cpu", copy=True) for k, v in self._lora().items()}


class GradientView:
    """`gradients`: this step's gradients of the trainable parameters, after backward and before the
    optimizer steps. Tensors are the live `.grad` buffers: read them, do not write to them; changes go
    through the `transform_gradients` action."""

    def __init__(self, named_parameters):
        self._params = {n: p for n, p in named_parameters if p.requires_grad and p.grad is not None}

    def names(self) -> list[str]:
        return list(self._params)

    def get(self, name: str) -> torch.Tensor:
        return self._params[name].grad

    def norm(self) -> float:
        return float(torch.sqrt(sum((p.grad.double() ** 2).sum() for p in self._params.values())))

    def value(self, name: str) -> torch.Tensor:
        """The parameter itself, as it is before this optimizer step (a detached view: read only)."""
        return self._params[name].detach()

    def flat(self, select=None) -> torch.Tensor:
        """Concatenated gradients (CPU, float64) of the parameters whose name passes `select`."""
        parts = [p.grad.detach().flatten().double().cpu() for n, p in self._params.items() if select is None or select(n)]
        return torch.cat(parts) if parts else torch.zeros(0, dtype=torch.float64)

    def check(self, new: dict[str, torch.Tensor]) -> None:
        for n, g in new.items():
            if n not in self._params:
                raise KeyError(f"no gradient for parameter {n!r}")
            if tuple(g.shape) != tuple(self._params[n].grad.shape) or not torch.isfinite(g).all():
                raise ValueError(f"replacement gradient for {n!r} has the wrong shape or non-finite values")

    def apply(self, new: dict[str, torch.Tensor]) -> None:
        """Used by the runner when an applied `transform_gradients` replaces gradients, in place."""
        with torch.no_grad():
            for n, g in new.items():
                grad = self._params[n].grad
                grad.copy_(g.to(grad.device, grad.dtype))


class LossView:
    """`loss`: one training step between the forward pass and backward: the batch, the model's outputs
    and the loss the host computed, still attached to the graph. Only the trainer extension layer
    (fedguard.adapters.hf_trainer_ext) provides it; a plain Trainer callback never sees this point.

    Everything here is live. Read it; a different loss goes through the `transform_loss` action, as a
    scalar tensor built from `loss` (e.g. `view.loss + term`) or from `loss_on(...)`.
    """

    def __init__(self, loss: torch.Tensor, outputs, batch: dict, named_parameters, loss_on: Callable,
                 identify: Callable | None = None):
        self._loss, self.outputs, self.batch, self._loss_on, self._identify = loss, outputs, batch, loss_on, identify
        self._params = {n: p for n, p in named_parameters if p.requires_grad}

    def sample_ids(self) -> list[str | None]:
        """The sample hash (as in DataView.manifest) of each row of the batch, in row order, so that a
        per-sample quantity of this step can be tied to a sample across steps and rounds. None for a row
        the adapter could not match. Raises LookupError when the app gave the adapter no way to tell."""
        if self._identify is None:
            raise LookupError("the batch carries no sample identity: pass `identify` to extend_trainer")
        return list(self._identify(self.batch))

    @property
    def loss(self) -> torch.Tensor:
        """The loss as it stands: the host's, or what an applied `transform_loss` of an earlier plugin made of it."""
        return self._loss

    @property
    def batch_size(self) -> int:
        return int(next(v for v in self.batch.values() if isinstance(v, torch.Tensor)).shape[0])

    def parameters(self) -> dict[str, torch.nn.Parameter]:
        """The trainable parameters themselves (not copies), for loss terms that depend on the weights."""
        return dict(self._params)

    def per_sample_losses(self) -> torch.Tensor:
        """Next-token cross-entropy of each sample of the batch, averaged over its labelled tokens, with a
        graph. Their mean is not the host's batch loss: the host sums over the tokens of the whole batch and
        divides by a count that depends on the transformers version (the predicted tokens, or all
        labelled tokens with each sample's first one included)."""
        logits, labels = getattr(self.outputs, "logits", None), self.batch.get("labels")
        if logits is None or labels is None:
            raise LookupError("per-sample losses need `logits` in the outputs and `labels` in the batch")
        labels = labels[:, 1:].to(logits.device)
        token = torch.nn.functional.cross_entropy(logits[:, :-1].transpose(1, 2).float(), labels, ignore_index=-100, reduction="none")
        return token.sum(1) / (labels != -100).sum(1).clamp(min=1)

    def gradients_of(self, scalar: torch.Tensor, select: Callable | None = None) -> dict[str, torch.Tensor]:
        """Gradient of a scalar with respect to the trainable parameters whose name passes `select`,
        keeping the graph for the host's own backward. One backward pass per call. Parameters the scalar
        does not reach get zeros."""
        params = {n: p for n, p in self._params.items() if select is None or select(n)}
        grads = torch.autograd.grad(scalar, list(params.values()), retain_graph=True, allow_unused=True)
        return {n: torch.zeros_like(p) if g is None else g for (n, p), g in zip(params.items(), grads)}

    def loss_on(self, batch: dict) -> torch.Tensor:
        """The host's loss on another batch (a dict of tensors in the format of `batch`), with a graph.
        One more forward pass through the model being trained."""
        device = next(iter(self._params.values())).device
        return self._loss_on({k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()})

    def check(self, new: torch.Tensor) -> None:
        if not isinstance(new, torch.Tensor) or new.numel() != 1 or not torch.isfinite(new).all() or not new.requires_grad:
            raise ValueError("a replacement loss must be a finite scalar tensor attached to the graph")

    def replace(self, new: torch.Tensor) -> None:
        """Used by the runner when an applied `transform_loss` replaces the loss."""
        self._loss = new.reshape(()).to(self._loss.dtype)
