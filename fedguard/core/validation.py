"""Framework-level input validation. Runs before any plugin sees an upload."""
from __future__ import annotations

import math

import torch

from fedguard.core.types import ClientUpdate


class InvalidUpdate(ValueError):
    """An upload is malformed (keys, shapes, dtype, non-finite or absurd values); it is excluded and recorded."""


def validate_update(update: ClientUpdate, *, max_abs: float = 1e4, strict_shapes: bool = True) -> None:
    """Reject malformed uploads: key/shape mismatch vs. the broadcast base, non-float, non-finite, absurd values.

    `max_abs` is a sanity bound against overflow/crash, not a detection threshold.
    With `strict_shapes=False` keys and shapes may differ from the base (per-client ranks, a single
    trained factor); values are still checked.
    """
    if not update.client_id or not isinstance(update.client_id, str):
        raise InvalidUpdate("client_id must be a nonempty string")
    if strict_shapes and update.lora.keys() != update.base.keys():
        missing, extra = update.base.keys() - update.lora.keys(), update.lora.keys() - update.base.keys()
        raise InvalidUpdate(f"key mismatch: missing={sorted(missing)[:3]} extra={sorted(extra)[:3]}")
    for key, t in update.lora.items():
        if not isinstance(t, torch.Tensor) or not t.is_floating_point():
            raise InvalidUpdate(f"{key}: not a floating tensor")
        if strict_shapes and t.shape != update.base[key].shape:
            raise InvalidUpdate(f"{key}: shape {tuple(t.shape)} != {tuple(update.base[key].shape)}")
        if not torch.isfinite(t).all():
            raise InvalidUpdate(f"{key}: non-finite values")
        if t.abs().max().item() > max_abs:
            raise InvalidUpdate(f"{key}: |value| > {max_abs}")
    for name, v in update.reported.items():
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise InvalidUpdate(f"reported[{name}] is not a finite number")
    n = update.reported.get("num_examples")
    if n is not None and n <= 0:
        raise InvalidUpdate("reported num_examples must be positive")
