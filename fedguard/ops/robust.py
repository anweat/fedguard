"""Robust statistics primitives."""
from __future__ import annotations

import math

import numpy as np
import torch

MAD_TO_SIGMA = 1.4826


def robust_z(values: dict[str, float], min_n: int = 5) -> dict[str, float] | None:
    """Median/MAD z-scores. Returns None when there are too few points to be meaningful."""
    finite = {k: v for k, v in values.items() if math.isfinite(v)}
    if len(finite) < min_n:
        return None
    x = np.array(list(finite.values()), dtype=np.float64)
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med))) * MAD_TO_SIGMA
    if mad == 0.0:
        mad = float(np.mean(np.abs(x - med))) or 1e-12
    return {k: (v - med) / mad for k, v in finite.items()}


def coordinate_median(X: torch.Tensor) -> torch.Tensor:
    """Coordinate-wise median of the rows (Yin et al. 2018). For an even count this is the mean of the
    two middle values, unlike torch.median, which returns the lower one."""
    return torch.quantile(X.double(), 0.5, dim=0)


def trimmed_mean(X: torch.Tensor, beta: float) -> torch.Tensor:
    """Coordinate-wise mean after dropping the floor(beta * n) largest and smallest values in each
    coordinate (Yin et al. 2018). 0 <= beta < 0.5."""
    if not 0 <= beta < 0.5:
        raise ValueError("beta must be in [0, 0.5)")
    n = X.shape[0]
    k = int(math.floor(beta * n))
    S = X.double().sort(dim=0).values
    return S[k:n - k].mean(dim=0)


def largest_gap_threshold(x: torch.Tensor) -> float:
    """Midpoint of the widest gap between consecutive sorted values: a data-driven cut between two groups."""
    s = x.double().flatten().sort().values
    if s.numel() < 2:
        raise ValueError("needs at least two values")
    gaps = s[1:] - s[:-1]
    i = int(gaps.argmax())
    return float((s[i] + s[i + 1]) / 2)


def foolsgold_weights(cs: torch.Tensor, kappa: float = 1.0) -> torch.Tensor:
    """FoolsGold (Fung et al. 2018) learning rates from a cosine-similarity matrix of clients'
    accumulated updates: pardoning, alpha = 1 - max similarity, rescale by the maximum, logit.
    Boundary handling follows the authors' reference code: alpha is clamped to [0, 1] before the logit
    and an alpha of exactly 1 is taken as 0.99."""
    cs = cs.double().clone()
    n = cs.shape[0]
    cs.fill_diagonal_(-float("inf"))
    v = cs.max(dim=1).values
    cs.fill_diagonal_(0.0)
    for i in range(n):
        for j in range(n):
            if i != j and v[i] < v[j] and v[j] != 0:
                cs[i, j] = cs[i, j] * v[i] / v[j]
    off = cs.clone()
    off.fill_diagonal_(-float("inf"))
    alpha = (1 - off.max(dim=1).values).clamp(0, 1)
    if alpha.max() > 0:
        alpha = alpha / alpha.max()
    alpha = torch.where(alpha == 1, torch.full_like(alpha, 0.99), alpha)
    out = kappa * (torch.log(alpha / (1 - alpha)) + 0.5)
    out = torch.where(alpha <= 0, torch.zeros_like(out), out)
    return out.clamp(0, 1)
