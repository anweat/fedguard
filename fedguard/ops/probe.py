"""Linear probes on feature vectors: fit offline on labelled examples, apply online.

A fitted probe is two tensors, so it can be handed to a plugin as a resource and stored with safetensors.
"""
from __future__ import annotations

import torch


def fit_logistic(X: torch.Tensor, y: torch.Tensor, l2: float = 1e-3, iters: int = 100) -> dict[str, torch.Tensor]:
    """L2-regularized logistic regression by Newton's method. y in {0, 1}. Returns {"weight", "bias", "mean", "scale"};
    features are standardized with the training mean and scale.

    With more features than samples the minimizer lies in the row space of the standardized data, so the
    fit runs in that space (at most n dimensions) and is mapped back: the same solution without a
    d x d Hessian, which for LoRA features (1e4 to 1e6 dimensions) would not fit in memory."""
    X, y = X.double(), y.double()
    mean, scale = X.mean(0), X.std(0, unbiased=False).clamp_min(1e-12)
    S = (X - mean) / scale
    basis = None
    if S.shape[1] > S.shape[0]:
        _, sv, Vt = torch.linalg.svd(S, full_matrices=False)
        basis = Vt[sv > sv.max().clamp_min(1e-300) * 1e-12].T        # d x r, orthonormal columns
        S = S @ basis
    Z = torch.cat([S, torch.ones(S.shape[0], 1, dtype=torch.float64)], dim=1)
    w = torch.zeros(Z.shape[1], dtype=torch.float64)
    reg = torch.full((Z.shape[1],), l2, dtype=torch.float64)
    reg[-1] = 0.0                                      # the bias is not penalized
    for _ in range(iters):
        p = torch.sigmoid(Z @ w)
        grad = Z.T @ (p - y) / len(y) + reg * w
        H = (Z.T * (p * (1 - p))) @ Z / len(y) + torch.diag(reg) + 1e-10 * torch.eye(Z.shape[1], dtype=torch.float64)
        step = torch.linalg.solve(H, grad)
        w = w - step
        if step.norm() < 1e-10:
            break
    return {"weight": w[:-1] if basis is None else basis @ w[:-1], "bias": w[-1:], "mean": mean, "scale": scale}


def apply_logistic(probe: dict[str, torch.Tensor], X: torch.Tensor) -> torch.Tensor:
    """Probability of class 1 for every row."""
    Z = (X.double() - probe["mean"].double()) / probe["scale"].double()
    return torch.sigmoid(Z @ probe["weight"].double() + probe["bias"].double())
