"""Changes of representation: frequency, principal components, random projection, normalization."""
from __future__ import annotations

import math

import torch


def dct(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
    """Orthonormal DCT-II along one dimension (matches scipy.fft.dct(x, type=2, norm="ortho"))."""
    x = x.double().transpose(dim, -1)
    n = x.shape[-1]
    k = torch.arange(n, dtype=torch.float64)
    basis = torch.cos(math.pi / n * (k[:, None]) * (k[None, :] + 0.5))       # (frequency, position)
    scale = torch.full((n,), math.sqrt(2.0 / n), dtype=torch.float64)
    scale[0] = math.sqrt(1.0 / n)
    return ((x @ basis.T) * scale).transpose(dim, -1)


def dct_2d(x: torch.Tensor) -> torch.Tensor:
    """Orthonormal 2-D DCT-II over the last two dimensions."""
    return dct(dct(x, dim=-1), dim=-2)


def low_frequency_triangle(coeffs: torch.Tensor) -> torch.Tensor:
    """FreqFed's filter on a square coefficient matrix of side s: the entries with i, j <= s // 2 and
    i + j <= s // 2, row by row, as one vector."""
    side = coeffs.shape[-1]
    h = side // 2
    i, j = torch.meshgrid(torch.arange(h + 1), torch.arange(h + 1), indexing="ij")
    keep = (i + j) <= h
    return coeffs[..., : h + 1, : h + 1][..., keep]


def as_square(vector: torch.Tensor) -> torch.Tensor:
    """Lay a vector out row by row in the smallest square that holds it, zero-padded: a 2-D signal for dct_2d."""
    n = vector.numel()
    side = math.isqrt(n - 1) + 1 if n else 0
    out = torch.zeros(side * side, dtype=torch.float64)
    out[:n] = vector.double().flatten()
    return out.reshape(side, side)


def pca(X: torch.Tensor, k: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Project the rows on their top-k principal directions.
    Returns (scores (n, k), components (k, d), explained variance ratio (k,)). Signs are fixed so that
    the largest-magnitude entry of each component is positive."""
    X = X.double()
    Xc = X - X.mean(dim=0, keepdim=True)
    k = min(k, *Xc.shape)
    U, S, Vh = torch.linalg.svd(Xc, full_matrices=False)
    comp = Vh[:k]
    signs = torch.sign(comp[torch.arange(k), comp.abs().argmax(dim=1)])
    signs[signs == 0] = 1
    comp = comp * signs[:, None]
    total = (S ** 2).sum()
    return Xc @ comp.T, comp, (S[:k] ** 2) / total if total > 0 else torch.zeros(k, dtype=torch.float64)
