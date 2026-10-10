"""Arithmetic on LoRA state dicts (name -> tensor)."""
from __future__ import annotations

import torch

State = dict[str, torch.Tensor]


def delta(state: State, base: State) -> State:
    """state - base, per entry, for the keys both have with equal shapes."""
    return {k: v - base[k] for k, v in state.items() if k in base and v.shape == base[k].shape}


def add(base: State, d: State, scale: float = 1.0) -> State:
    """base + scale * d; entries of base without a counterpart are kept."""
    return {k: v + scale * d[k].to(v.dtype) if k in d else v for k, v in base.items()}


def flatten(state: State, keys: list[str] | None = None, dtype: torch.dtype = torch.float64) -> torch.Tensor:
    """One vector, entries in sorted key order (or the given order)."""
    keys = sorted(state) if keys is None else keys
    return torch.cat([state[k].detach().flatten().to(dtype).cpu() for k in keys]) if keys else torch.zeros(0, dtype=dtype)


def unflatten(vector: torch.Tensor, like: State, keys: list[str] | None = None) -> State:
    """Inverse of flatten: cut `vector` back into the shapes and dtypes of `like`."""
    keys = sorted(like) if keys is None else keys
    out, i = {}, 0
    for k in keys:
        n = like[k].numel()
        out[k] = vector[i:i + n].reshape(like[k].shape).to(like[k].dtype)
        i += n
    if i != vector.numel():
        raise ValueError("vector length does not match the state")
    return out


def norm(state: State) -> float:
    return float(torch.sqrt(sum((v.double() ** 2).sum() for v in state.values()))) if state else 0.0


def weighted_average(states: list[State], weights: list[float] | None = None) -> State:
    """Entry-wise weighted mean, in the dtype of the first state (FedAvg in factor space)."""
    if not states:
        raise ValueError("nothing to average")
    w = torch.tensor(weights if weights is not None else [1.0] * len(states), dtype=torch.float64)
    if (w < 0).any() or w.sum() <= 0:
        raise ValueError("weights must be non-negative and not all zero")
    w = w / w.sum()
    return {k: sum(s[k].double() * float(wi) for s, wi in zip(states, w)).to(states[0][k].dtype) for k in states[0]}


def stack(states: list[State], keys: list[str] | None = None) -> torch.Tensor:
    """(n, d) matrix of flattened states."""
    return torch.stack([flatten(s, keys) for s in states]) if states else torch.zeros(0, 0, dtype=torch.float64)


def module_info(name: str) -> dict:
    """What a LoRA state-dict key or module prefix says about where the adapter sits.

    layer: the first integer component of the path (the transformer block), None if there is none.
    role: the adapted module's own name (e.g. "q_proj"). factor: "A", "B" or None for a module prefix.
    Read from the name only: nothing here knows the model."""
    path = name
    factor = "A" if ".lora_A" in name else "B" if ".lora_B" in name else None
    if factor:
        path = name.split(".lora_")[0]
    parts = path.split(".")
    layer = next((int(p) for p in parts if p.isdigit()), None)
    return {"module": path, "layer": layer, "role": parts[-1], "factor": factor}
