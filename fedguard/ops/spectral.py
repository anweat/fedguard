"""Spectral operators on a set of vectors (rows) or on one matrix."""
from __future__ import annotations

import torch


def top_singular_scores(X: torch.Tensor) -> torch.Tensor:
    """Spectral signatures (Tran et al. 2018): squared projection of each centered row on the top right
    singular vector of the centered matrix. Rows of a small, coherent sub-population score high."""
    X = X.double()
    Xc = X - X.mean(dim=0, keepdim=True)
    _, _, Vh = torch.linalg.svd(Xc, full_matrices=False)
    return (Xc @ Vh[0]) ** 2


def spectral_entropy(M: torch.Tensor, eps: float = 1e-12) -> float:
    """Shannon entropy (nats) of the normalized squared singular values of a matrix: low when the energy
    sits in a few directions, log(rank) when it is spread evenly."""
    s = torch.linalg.svdvals(M.double()) ** 2
    total = s.sum()
    if total <= 0:
        return 0.0
    p = s / total
    return float(-(p * torch.log(p.clamp_min(eps))).sum())
