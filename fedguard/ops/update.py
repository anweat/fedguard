"""Changes applied to an update or a gradient: clipping, scaling, noise, projection."""
from __future__ import annotations

import torch

from fedguard.ops import states


def clip_to_norm(state: states.State, base: states.State, bound: float) -> tuple[states.State, float]:
    """Scale the delta (state - base) down so its norm does not exceed `bound`. Returns (new state, factor <= 1)."""
    d = states.delta(state, base)
    n = states.norm(d)
    factor = 1.0 if n <= bound or n == 0 else bound / n
    return (dict(state) if factor == 1.0 else states.add(base, d, factor)), factor


def scale_to_norm(state: states.State, base: states.State, target: float) -> states.State:
    """Rescale the delta to exactly `target` norm (FLTrust-style normalization). A zero delta is left alone."""
    d = states.delta(state, base)
    n = states.norm(d)
    return dict(state) if n == 0 else states.add(base, d, target / n)


def add_gaussian_noise(state: states.State, sigma: float, generator: torch.Generator) -> states.State:
    """Add independent N(0, sigma^2) noise to every entry, drawn from the given generator."""
    return {k: v + sigma * torch.randn(v.shape, generator=generator, dtype=torch.float64).to(v.dtype) for k, v in state.items()}


def project_onto(vector: torch.Tensor, directions: torch.Tensor) -> torch.Tensor:
    """Keep only the components of `vector` in the span of the rows of `directions`."""
    v = vector.double().flatten()
    Q, _ = torch.linalg.qr(directions.double().reshape(-1, v.numel()).T)
    return Q @ (Q.T @ v)


def clip_state_norm(state: states.State, bound: float) -> tuple[states.State, float]:
    """Scale the whole state (not a delta) down so its norm does not exceed `bound`. Returns (state, factor)."""
    n = states.norm(state)
    factor = 1.0 if n <= bound or n == 0 else bound / n
    return ({k: v * factor for k, v in state.items()} if factor != 1.0 else dict(state)), factor


def clip_and_noise(grads: dict[str, torch.Tensor], bound: float, sigma: float, generator: torch.Generator,
                   denominator: float = 1.0) -> dict[str, torch.Tensor]:
    """Gaussian mechanism on one gradient: joint L2 clipping to `bound`, then N(0, (sigma*bound/denominator)^2) noise.
    Applied to a batch gradient this bounds the batch's contribution, not each sample's."""
    n = float(torch.sqrt(sum((g.double() ** 2).sum() for g in grads.values())))
    f = 1.0 if n <= bound or n == 0 else bound / n
    return {k: g * f + (sigma * bound / denominator) * torch.randn(g.shape, generator=generator).to(g.device, g.dtype)
            for k, g in grads.items()}
