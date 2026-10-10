"""Helpers used by methods in more than one file: update vectors of the uploads, and how LoRA keys are read."""
from __future__ import annotations

import math

import torch

from fedguard.ops import geometry
from fedguard.ops.lowrank import gram as lowrank_gram


def update_matrix(up, clients: list[str]) -> torch.Tensor:
    """(n, d) factor-space update vectors of the given clients."""
    return torch.stack([up.factor_delta(c).double() for c in clients]) if clients else torch.zeros(0, 0, dtype=torch.float64)


def update_gram(up, clients: list[str], space: str = "factor") -> torch.Tensor:
    """Gram matrix of the clients' updates: in factor space, or exactly in product space (no densifying)."""
    if space == "factor":
        return geometry.gram_matrix(update_matrix(up, clients))
    if space == "product":
        G = torch.zeros(len(clients), len(clients), dtype=torch.float64)
        for m in up.modules:
            G += lowrank_gram([up.increment(c, m).to(torch.float64) for c in clients])
        return G
    raise ValueError(f"unknown space {space!r}")


_A, _B = ".lora_A.weight", ".lora_B.weight"


def _layer_index(key: str) -> int:
    return next((int(t) for t in key.split(".") if t.isdigit()), -1)


def first_layer_b_feature(state: dict, reference: dict) -> torch.Tensor:
    """Safe-FedLLM's probe input: the differences B - B_ref of every LoRA module of the first transformer
    layer, flattened in sorted key order, concatenated and L2-normalized."""
    keys = sorted(k for k in state if k.endswith(_B) and k in reference)
    if not keys:
        raise LookupError("no lora_B entries to build the probe feature from")
    first = min(_layer_index(k) for k in keys)
    x = torch.cat([(state[k].double() - reference[k].double()).flatten() for k in keys if _layer_index(k) == first])
    return x / x.norm().clamp_min(1e-12)


def two_stage_calibration(s: float, k: float = 10.0) -> float:
    """Safe-FedLLM Eq. 13: g(s) = sigmoid(k (s - 0.4)) / 2 on [0, 0.8], (1 + sigmoid(k (s - 0.9))) / 2 above."""
    sig = lambda z: 1.0 / (1.0 + math.exp(-z))  # noqa: E731
    return 0.5 * sig(k * (s - 0.4)) if s <= 0.8 else 0.5 * (1.0 + sig(k * (s - 0.9)))


def _factor(name: str) -> str | None:
    return "A" if "lora_A" in name else "B" if "lora_B" in name else None
