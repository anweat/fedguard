"""Operators for accumulating evidence across rounds.

One-sided standardized scores (larger = more suspicious) are produced per round, either against the
same round's participants (cross-sectional) or against a calibrated benign reference, and fed into a
CUSUM per client. Benign clients hover around zero and are pulled back by the allowance k; a client
that is slightly off every round keeps rising.
"""
from __future__ import annotations

import math

import torch

from fedguard.ops.robust import robust_z


def one_sided_z(values: dict[str, float], sign: int, min_n: int = 5) -> dict[str, float] | None:
    """sign * robust z across this round's participants; None when too few clients take part.

    Weakness: with several colluding clients in a small round the median/MAD are themselves contaminated.
    """
    z = robust_z(values, min_n=min_n)
    return None if z is None else {c: sign * v for c, v in z.items()}


def reference_z(values: dict[str, float], sign: int, center: float, scale: float) -> dict[str, float]:
    """sign * (x - center) / scale against a calibrated benign reference for this round.

    Does not depend on who else takes part in the round, so collusion and client sampling do not
    distort it; it does depend on the calibration runs matching the deployment setting.
    """
    scale = scale if scale > 0 else 1e-12
    return {c: sign * (v - center) / scale for c, v in values.items() if math.isfinite(v)}


def cusum_step(s: float, z: float, k: float = 0.5, cap: float | None = None) -> float:
    """One-sided CUSUM update S <- max(0, S + z - k). `cap` bounds a single round's contribution so one
    extreme round cannot confirm a client by itself (cap=None disables it)."""
    if not math.isfinite(z):
        return s
    step = z - k
    if cap is not None:
        step = min(step, cap)
    return max(0.0, s + step)


def beta_mean(alpha: float, beta: float) -> float:
    """Expected trust alpha / (alpha + beta)."""
    return alpha / (alpha + beta) if alpha + beta > 0 else 0.5


def lbfgs_hvp(dW: torch.Tensor, dG: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """Hessian-vector product H v from the compact L-BFGS representation (Byrd, Nocedal, Schnabel 1994),
    as used by FLDetector. dW and dG are (p, N): the last N differences of the global model and of the
    aggregated update, oldest first. Solves with a pseudo-inverse, so a rank-deficient window does not fail."""
    dW, dG, v = dW.double(), dG.double(), v.double().flatten()
    A = dW.T @ dG
    D = torch.diag(torch.diagonal(A))
    L = torch.tril(A, diagonal=-1)
    sigma = (dG[:, -1] @ dW[:, -1]) / (dW[:, -1] @ dW[:, -1]).clamp_min(1e-300)
    top = torch.cat([-D, L.T], dim=1)
    bottom = torch.cat([L, sigma * (dW.T @ dW)], dim=1)
    rhs = torch.cat([dG.T @ v, sigma * (dW.T @ v)])
    p = torch.linalg.pinv(torch.cat([top, bottom], dim=0)) @ rhs
    return sigma * v - torch.cat([dG, sigma * dW], dim=1) @ p


def window_mean(history: list[torch.Tensor], length: int) -> torch.Tensor:
    """Mean of the last `length` entries of a per-round history (fewer if the history is shorter)."""
    return torch.stack(history[-length:]).mean(0)


BINOMIAL_KERNELS = {3: (1, 2, 1), 5: (1, 4, 6, 4, 1), 7: (1, 6, 15, 20, 15, 6, 1)}


def lowpass_1d(x: torch.Tensor, dim: int, taps: int = 5) -> torch.Tensor:
    """Binomial low-pass filter along one dimension with symmetric (reflect) padding; the shape is kept.
    Written as a sum of shifted slices: no convolution backend is involved."""
    kernel = BINOMIAL_KERNELS[taps]
    half, n = taps // 2, x.shape[dim]
    if n <= half:
        return x.clone()
    y = x.movedim(dim, -1)
    idx = torch.arange(-half, n + half, device=x.device).abs()
    idx = torch.where(idx >= n, 2 * (n - 1) - idx, idx)
    padded = y.index_select(-1, idx)
    out = sum(w * padded[..., j:j + n] for j, w in enumerate(kernel)) / sum(kernel)
    return out.movedim(-1, dim)
