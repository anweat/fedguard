"""`model_handle`: what a plugin may ask of a model, on either side.

The framework defines the interface; adapters implement it (fedguard.adapters.hf_model.HFModelHandle).
Everything here costs model passes. The handle counts them in `cost`, and the runner writes each
plugin's share into its findings, so an expensive plugin shows up as expensive in the record.

A handle may be the very model that is being trained. Every method must leave its weights, mode and
gradients exactly as it found them.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from typing import Protocol

import torch

# Named groups of parameters a plugin can ask gradients or activations for, instead of raw names.
PARAM_GROUPS = ("lora", "lora_A", "lora_B", "last_lora_B", "first_lora_B")


class ModelHandle(Protocol):
    """The `model_handle` data kind: the passes through a model that a plugin may spend. An implementation
    must leave the model as it found it and count what was spent in `cost`.
    """
    cost: dict[str, float]      # running totals: forward_samples, backward_samples, generated_tokens, seconds

    def lora(self, state: dict[str, torch.Tensor]) -> AbstractContextManager:
        """`with handle.lora(state):` runs the block with this LoRA loaded, then restores the previous one exactly."""

    def parameters(self, group: str | Callable[[str], bool] = "lora", scope: str = "lora") -> list[str]:
        """Names of the parameters in a group (see PARAM_GROUPS) or passing a predicate. scope="lora" looks
        at the adapter's parameters only; scope="all" also at the frozen base weights (predicate only)."""

    def layout(self, group: str | Callable[[str], bool] = "lora", scope: str = "lora") -> list[tuple[str, tuple[int, ...]]]:
        """(name, shape) per parameter of a group, in the order gradients are concatenated. For adapter
        parameters the name is the LoRA state-dict key; for base weights it is the model's parameter name."""

    def tokens(self, samples: Sequence) -> list[list[str]]:
        """The tokens each sample is turned into, in the order of the positions that pool="none" returns."""

    def losses(self, samples: Sequence) -> list[float]:
        """Per-sample training loss, forward only."""

    def hidden(self, samples: Sequence, layer: int = -1, pool: str = "last"):
        """A hidden layer's states. pool="last" | "mean" | "max": one vector per sample, (n, d), CPU.
        pool="none": no pooling, a list with one (tokens of that sample, d) tensor per sample."""

    def activations(self, samples: Sequence, select: Callable[[str], bool], pool: str = "mean", what: str = "output") -> dict:
        """What the submodules whose name passes `select` produce (what="output") or receive (what="input").
        Pooled: name -> (n, d), CPU. pool="none": name -> list of (tokens of that sample, d) tensors."""

    def per_sample_gradients(self, samples: Sequence, group: str | Callable[[str], bool] = "last_lora_B", scope: str = "lora",
                             reduce: Callable | None = None) -> torch.Tensor:
        """Gradient of each sample's loss with respect to a parameter group, flattened: (n, p), CPU.
        One backward pass per sample. scope="all" lets a predicate select frozen base weights (they get a
        gradient for the duration of the call). reduce: {parameter name: gradient} -> 1-D tensor, applied per
        sample on the model's device instead of flattening, for gradients too large to keep whole."""

    def logprob(self, prompts: Sequence[str], targets: Sequence[str]) -> list[float]:
        """Mean per-token log-probability of each target continuing its prompt."""

    def generate(self, prompts: Sequence[str], max_new_tokens: int = 32) -> list[str]:
        """Greedy continuation of each prompt."""


class ProbeView(Protocol):
    """A narrow server-side handle with one call, which scores a candidate LoRA by behavior. It is not a
    limit of the library: a server that has a model can be given a full ModelHandle instead (the `probe`
    argument of the server-side adapters takes either)."""

    def score(self, lora: dict[str, torch.Tensor]) -> dict[str, float]:
        """Behavioral metrics of the base model with `lora` loaded. Must leave no side effects."""
        ...
