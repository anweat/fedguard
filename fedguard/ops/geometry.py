"""Distances, cosines and comparisons between a set of vectors (rows of X)."""
from __future__ import annotations

import math

import torch


def cross_section(G: torch.Tensor) -> tuple[list[float], list[float], list[float]]:
    """From a Gram matrix of n updates, per client:
    norm, mean cosine to every other client, cosine to the mean of the other clients.
    Cosines are NaN when undefined (n < 2 or zero norms).
    """
    n = G.shape[0]
    G = G.double()
    norms = torch.sqrt(torch.clamp(torch.diagonal(G), min=0.0))
    mean_cos, cos_rest = [], []
    for i in range(n):
        others = [j for j in range(n) if j != i]
        if not others or norms[i] == 0:
            mean_cos.append(math.nan)
            cos_rest.append(math.nan)
            continue
        cs = [float(G[i, j] / (norms[i] * norms[j])) for j in others if norms[j] > 0]
        mean_cos.append(sum(cs) / len(cs) if cs else math.nan)
        idx = torch.tensor(others)
        rest_sq = float(G[idx][:, idx].sum())      # ||sum of others||^2
        num = float(G[i, idx].sum())               # <x_i, sum of others>
        cos_rest.append(num / (float(norms[i]) * math.sqrt(rest_sq)) if rest_sq > 0 else math.nan)
    return norms.tolist(), mean_cos, cos_rest


def gram_matrix(X: torch.Tensor) -> torch.Tensor:
    X = X.double()
    return X @ X.T


def pairwise_sq_distances(X: torch.Tensor) -> torch.Tensor:
    """Squared Euclidean distances between rows, from the Gram matrix; exact zeros on the diagonal."""
    G = gram_matrix(X)
    d = torch.diagonal(G)
    D = (d[:, None] + d[None, :] - 2 * G).clamp_min(0)
    D.fill_diagonal_(0)
    return D


def cosine_matrix(X: torch.Tensor) -> torch.Tensor:
    """Cosine similarity between rows; rows of zero norm get zeros."""
    X = X.double()
    n = X.norm(dim=1, keepdim=True)
    Xn = torch.where(n > 0, X / n.clamp_min(1e-300), torch.zeros_like(X))
    return (Xn @ Xn.T).clamp(-1, 1)


def cosine_to(X: torch.Tensor, ref: torch.Tensor) -> torch.Tensor:
    """Cosine of every row to one reference vector; zero where either norm is zero."""
    X, ref = X.double(), ref.double().flatten()
    den = X.norm(dim=1) * ref.norm()
    return torch.where(den > 0, (X @ ref) / den.clamp_min(1e-300), torch.zeros_like(den)).clamp(-1, 1)


def distance_to(X: torch.Tensor, ref: torch.Tensor) -> torch.Tensor:
    return (X.double() - ref.double().flatten()[None, :]).norm(dim=1)


def krum_scores(D: torch.Tensor, f: int) -> torch.Tensor:
    """Krum (Blanchard et al. 2017) from a matrix of squared distances: for each row, the sum of the
    squared distances to its n - f - 2 nearest other rows. Lower is more central. Needs n >= f + 3."""
    n = D.shape[0]
    k = n - f - 2
    if k < 1:
        raise ValueError(f"Krum needs n >= f + 3 (n={n}, f={f})")
    return D.sort(dim=1).values[:, 1:k + 1].sum(dim=1)


def sq_distances_from_gram(G: torch.Tensor) -> torch.Tensor:
    """Pairwise squared distances from a Gram matrix (works where the vectors themselves are never formed,
    e.g. LoRA products through fedguard.ops.lowrank.gram)."""
    d = torch.diagonal(G)
    D = (d[:, None] + d[None, :] - 2 * G).clamp_min(0)
    D.fill_diagonal_(0)
    return D


def cosine_distances_from_gram(G: torch.Tensor) -> torch.Tensor:
    """Pairwise cosine distances (1 - cosine) from a Gram matrix; a zero vector is at distance 1 from everything."""
    n = torch.sqrt(torch.diagonal(G).clamp_min(0))
    den = n[:, None] * n[None, :]
    C = torch.where(den > 0, G / den.clamp_min(1e-300), torch.zeros_like(G)).clamp(-1, 1)
    D = (1 - C).clamp_min(0)
    D.fill_diagonal_(0)
    return D
