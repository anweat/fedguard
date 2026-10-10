"""Helpers for the tests of ported methods: drive a plugin through a federated round on synthetic LoRA
states, without a model and without a host framework. Imported by the generated tests as `harness`.

    base = make_base()                                   # a LoRA state dict: 3 modules, r=4, float64
    local = perturb(base, seed, scale)                   # base plus Gaussian noise
    guard = server_guard([MyPlugin()], probe=None)       # server side, actions applied, a plugin error raises; probe: a model handle
    new_global, kept, decision, findings = server_round(guard, t, base, [local0, local1, ...])
    guard = client_guard([MyPlugin()], resources={...})  # client side: a fedguard.client.ClientGuard
    found = guard.begin_round(0, base, data=DataView(samples, text_of=...), model_handle=StubHandle())
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from conftest import make_base, perturb  # noqa: E402,F401
from fedguard.adapters.openfedllm import OpenFedLLMGuard  # noqa: E402
from fedguard.client import ClientGuard  # noqa: E402
from fedguard.core.runner import GuardRunner  # noqa: E402
from fedguard.core.types import RunSpec  # noqa: E402
from fedguard.views.client import DataView  # noqa: E402,F401

SPEC = RunSpec("port", seed=3, lora_scale=2.0)


def server_guard(plugins, resources=None, apply: bool = True, probe=None) -> OpenFedLLMGuard:
    """probe: a server-side model handle (e.g. a StubHandle subclass) for plugins that declare `model_handle`."""
    return OpenFedLLMGuard(GuardRunner(list(plugins), SPEC, apply_actions=apply, fail_policy="closed", resources=resources), probe=probe)


def server_round(guard: OpenFedLLMGuard, t: int, global_state: dict, locals_: list, sizes: list | None = None, reported: list | None = None):
    """One round: every client uploads locals_[i]; FedAvg over what the plugins kept, with their weights.
    Returns (new global state, kept client indices, the round's Decision, the round's Findings)."""
    locals_ = list(locals_)
    sizes = sizes or [10] * len(locals_)
    guard.begin_round(t, global_state, list(range(len(locals_))))
    for c, state in enumerate(locals_):
        guard.on_upload(c, state, {"num_examples": sizes[c], **((reported or [{}] * len(locals_))[c])})
    kept, weights = guard.before_aggregate(list(range(len(locals_))), sizes)
    for c, state in guard.transformed.items():
        locals_[c] = state
    new = global_state
    if kept:
        total = sum(weights[c] for c in kept)
        new = guard.after_aggregate({k: sum(locals_[c][k] * (weights[c] / total) for c in kept) for k in global_state})
    decision, findings = guard.last_decision, guard.runner.findings
    guard.end_round()
    return new, kept, decision, findings


def client_guard(plugins, resources=None, apply: bool = True, client_id: str = "c0") -> ClientGuard:
    return ClientGuard(client_id, GuardRunner(list(plugins), SPEC, side="client", apply_actions=apply, fail_policy="closed",
                                              resources=resources))


class StubHandle:
    """A stand-in for the `model_handle` data kind. Subclass it and implement only the methods the plugin
    calls (see fedguard.views.model.ModelHandle), returning tensors the test controls."""

    def __init__(self):
        self.cost = {"forward_samples": 0, "backward_samples": 0}


def grads_of(named: dict[str, torch.Tensor]):
    """named_parameters for guard.on_gradients(step, ...): parameters whose .grad is the given tensor."""
    out = []
    for name, g in named.items():
        p = torch.nn.Parameter(torch.zeros_like(g))
        p.grad = g.clone()
        out.append((name, p))
    return out
