import math

import torch

from fedguard.ops.lowrank import LowRank, gram, kappa


def rand(*shape, seed):
    return torch.randn(*shape, generator=torch.Generator().manual_seed(seed), dtype=torch.float64)


def test_norm_inner_spectrum_match_dense():
    d, k, r = 64, 48, 6
    m1 = LowRank(rand(d, r, seed=1), rand(r, k, seed=2), scale=2.0)
    m2 = LowRank(rand(d, r, seed=3), rand(r, k, seed=4), scale=0.5)
    D1, D2 = m1.dense(), m2.dense()
    assert math.isclose(m1.norm_sq(), float((D1 ** 2).sum()), rel_tol=1e-10)
    assert math.isclose(m1.inner(m2), float((D1 * D2).sum()), rel_tol=1e-10)
    sv_dense = torch.linalg.svdvals(D1)[:r]
    assert torch.allclose(m1.singular_values().sort(descending=True).values, sv_dense, rtol=1e-8)


def test_increment_is_exact_difference_and_rank_2r():
    d, k, r = 40, 30, 4
    B, A, B0, A0 = rand(d, r, seed=1), rand(r, k, seed=2), rand(d, r, seed=3), rand(r, k, seed=4)
    inc = LowRank.increment(B, A, B0, A0, scale=1.5)
    assert torch.allclose(inc.dense(), 1.5 * (B @ A - B0 @ A0), atol=1e-12)
    assert inc.U.shape[1] == 2 * r
    assert torch.linalg.matrix_rank(inc.dense()) <= 2 * r


def test_gram_matches_pairwise_inner():
    d, k, r = 32, 20, 3
    items = [LowRank.increment(rand(d, r, seed=i), rand(r, k, seed=10 + i), rand(d, r, seed=99),
                               rand(r, k, seed=98), scale=0.7) for i in range(5)]
    G = gram(items)
    dense = torch.stack([m.dense().flatten() for m in items])
    assert torch.allclose(G, dense @ dense.T, rtol=1e-10, atol=1e-10)


def test_effect_invariant_to_reparameterization_factors_are_not():
    d, k, r = 32, 24, 4
    B, A = rand(d, r, seed=1), rand(r, k, seed=2)
    M = rand(r, r, seed=3) + 3 * torch.eye(r, dtype=torch.float64)
    B2, A2 = B @ M, torch.linalg.solve(M, A)
    ref = LowRank.lora(B, A).norm_sq()
    assert abs(ref - LowRank.lora(B2, A2).norm_sq()) < 1e-8 * ref
    assert abs(float(B.norm()) - float(B2.norm())) > 1.0
    assert kappa(B, A) >= 1.0 and kappa(B2, A2) >= 1.0


def test_kappa_undefined_when_b_is_zero():
    assert kappa(torch.zeros(8, 2, dtype=torch.float64), rand(2, 5, seed=0)) == float("inf")
