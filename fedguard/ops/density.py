"""One-dimensional density estimates and the thresholds read off them; entropy and divergence."""
from __future__ import annotations

import math

import torch


def silverman_bandwidth(x: torch.Tensor) -> float:
    """h = 1.06 * std * n^(-1/5); a small positive floor when the sample has no spread."""
    x = x.double().flatten()
    return max(1.06 * float(x.std(unbiased=False)) * x.numel() ** (-0.2), 1e-6)


def gaussian_kde(x: torch.Tensor, grid: torch.Tensor, bandwidth: float | None = None) -> torch.Tensor:
    """Gaussian kernel density of the sample `x` evaluated on `grid`."""
    x, grid = x.double().flatten(), grid.double().flatten()
    h = silverman_bandwidth(x) if bandwidth is None else bandwidth
    z = (grid[:, None] - x[None, :]) / h
    return torch.exp(-0.5 * z ** 2).sum(1) / (x.numel() * h * math.sqrt(2 * math.pi))


def kde_valley_threshold(x: torch.Tensor, lo: float = 0.0, hi: float = 1.0, fallback: float | None = None,
                         points: int = 512) -> tuple[float, bool]:
    """Threshold at the density minimum between the outermost two peaks of a 1-D sample on [lo, hi].
    Returns (threshold, bimodal). With fewer than two peaks there is no valley: returns (fallback, False),
    or raises when no fallback is given."""
    pad = 3 * silverman_bandwidth(x)                   # scores may pile up on a boundary; look past it for the peak
    grid = torch.linspace(lo - pad, hi + pad, points, dtype=torch.float64)
    d = gaussian_kde(x, grid)
    inner = (d[1:-1] > d[:-2]) & (d[1:-1] >= d[2:])
    peaks = (torch.nonzero(inner).flatten() + 1).tolist()
    if len(peaks) < 2:
        if fallback is None:
            raise ValueError("the sample is not bimodal")
        return float(fallback), False
    a, b = peaks[0], peaks[-1]
    return float(grid[a + int(d[a:b + 1].argmin())].clamp(lo, hi)), True


def shannon_entropy(p: torch.Tensor, eps: float = 1e-12) -> float:
    """Entropy (nats) of a non-negative vector after normalizing it to sum 1."""
    p = p.double().flatten().clamp_min(0)
    total = p.sum()
    if total <= 0:
        return 0.0
    p = p / total
    return float(-(p * torch.log(p.clamp_min(eps))).sum())


def knn_density_ratio(X: torch.Tensor, k: int, bandwidth: float | None = None) -> torch.Tensor:
    """Local density of each row relative to its k nearest neighbours (squared Euclidean distance).

    Density of a point: mean Gaussian kernel to its k neighbours. Score: the point's density divided by
    the mean density of those neighbours. About 1 inside a homogeneous group, below 1 for a point that
    sits apart from its neighbours. bandwidth None: the median k-th neighbour distance."""
    X = X.double()
    n = X.shape[0]
    k = max(1, min(k, n - 1))
    if n < 2:
        return torch.ones(n, dtype=torch.float64)
    D = torch.cdist(X, X) ** 2
    D.fill_diagonal_(float("inf"))
    dist, idx = D.topk(k, largest=False)
    h2 = float(dist[:, -1].median()) if bandwidth is None else float(bandwidth) ** 2
    q = torch.exp(-dist / (2 * max(h2, 1e-300))).mean(1)
    return q / q[idx].mean(1).clamp_min(1e-300)
