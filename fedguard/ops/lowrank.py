"""Effect-space primitives for LoRA: exact norms, inner products and spectra without densifying.

A matrix is represented as M = scale * U @ V with U: (d_out, q), V: (q, d_in), q small.
PEFT stores lora_B as (d_out, r) and lora_A as (r, d_in), so a LoRA effect is (U, V) = (B, A).

A round's functional change is rank <= 2r:
    B_i A_i - B_g A_g = [B_i, -B_g] @ [A_i; A_g]
Do NOT use (B_i - B_g)(A_i - A_g): it drops the first-order terms that make up most of the update.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class LowRank:
    """A matrix kept as scale * U @ V without forming it. Norms, inner products and singular values of
    LoRA products and of their differences are computed from the small Gram matrices of the factors.
    """
    U: torch.Tensor
    V: torch.Tensor
    scale: float = 1.0

    @classmethod
    def lora(cls, B: torch.Tensor, A: torch.Tensor, scale: float = 1.0) -> "LowRank":
        """Cumulative LoRA effect scale * B @ A."""
        return cls(B, A, scale)

    @classmethod
    def increment(cls, B: torch.Tensor, A: torch.Tensor, B0: torch.Tensor, A0: torch.Tensor,
                  scale: float = 1.0) -> "LowRank":
        """Functional change scale * (B @ A - B0 @ A0) relative to the broadcast factors (B0, A0)."""
        return cls(torch.cat([B, -B0], dim=1), torch.cat([A, A0], dim=0), scale)

    @property
    def shape(self) -> tuple[int, int]:
        return self.U.shape[0], self.V.shape[1]

    def to(self, dtype: torch.dtype) -> "LowRank":
        return LowRank(self.U.to(dtype), self.V.to(dtype), self.scale)

    def dense(self) -> torch.Tensor:
        """Materialize the full matrix. For tests and small models only."""
        return self.scale * (self.U @ self.V)

    def norm_sq(self) -> float:
        # ||UV||_F^2 = tr(U^T U V V^T) = sum((U^T U) * (V V^T)), both factors symmetric
        return float(self.scale ** 2 * ((self.U.T @ self.U) * (self.V @ self.V.T)).sum())

    def inner(self, other: "LowRank") -> float:
        # <U1 V1, U2 V2>_F = tr(U1^T U2 V2 V1^T) = sum((U1^T U2) * (V1 V2^T))
        return float(self.scale * other.scale * ((self.U.T @ other.U) * (self.V @ other.V.T)).sum())

    def singular_values(self) -> torch.Tensor:
        """Nonzero spectrum via QR of each factor and SVD of a q x q core."""
        _, R1 = torch.linalg.qr(self.U)
        _, R2 = torch.linalg.qr(self.V.T)
        return abs(self.scale) * torch.linalg.svdvals(R1 @ R2.T)


def gram(items: list[LowRank], dtype: torch.dtype = torch.float64) -> torch.Tensor:
    """Pairwise Frobenius inner products of same-shape low-rank matrices, batched into two GEMMs.

    Returns an (n, n) tensor G with G[i, j] = <M_i, M_j>.
    """
    if not items:
        return torch.zeros(0, 0, dtype=dtype)
    if len({m.shape for m in items}) != 1:
        raise ValueError("all matrices must share a shape")
    sizes = [m.U.shape[1] for m in items]
    U = torch.cat([m.U.to(dtype) for m in items], dim=1)      # (d_out, sum q)
    V = torch.cat([m.V.to(dtype) for m in items], dim=0)      # (sum q, d_in)
    GU, GV = U.T @ U, V @ V.T                                 # (sum q, sum q)
    prod = GU * GV
    # Sum each (q_i, q_j) block.
    edges = torch.tensor([0] + sizes).cumsum(0).tolist()
    n = len(items)
    out = torch.empty(n, n, dtype=dtype)
    for i in range(n):
        rows = prod[edges[i]:edges[i + 1]]
        for j in range(i, n):
            out[i, j] = out[j, i] = rows[:, edges[j]:edges[j + 1]].sum()
    scales = torch.tensor([m.scale for m in items], dtype=dtype)
    return out * torch.outer(scales, scales)


def kappa(B: torch.Tensor, A: torch.Tensor) -> float:
    """Factorization redundancy ||B||·||A|| / ||BA|| (>= 1). Undefined (inf) when BA = 0."""
    effect = LowRank.lora(B.double(), A.double()).norm_sq() ** 0.5
    if effect == 0.0:
        return float("inf")
    return float(B.double().norm() * A.double().norm()) / effect
