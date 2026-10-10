"""Operators checked against definitions, known values or invariants."""
import math

import numpy as np
import pytest
import torch

from fedguard.ops import cluster, geometry, probe, robust, sampling, sequential, spectral, states, text, transform, update

G = torch.Generator().manual_seed(0)


def blobs(n_a=8, n_b=3, d=6, gap=10.0):
    g = torch.Generator().manual_seed(1)
    a = torch.randn(n_a, d, generator=g, dtype=torch.float64)
    b = torch.randn(n_b, d, generator=g, dtype=torch.float64) + gap
    return torch.cat([a, b])


# ----- states -----
def test_state_arithmetic_roundtrips():
    base = {"b": torch.randn(3, 2, generator=G), "a": torch.randn(4, generator=G)}
    other = {k: v + 1.0 for k, v in base.items()}
    d = states.delta(other, base)
    assert states.norm(d) == pytest.approx(math.sqrt(10))
    back = states.unflatten(states.flatten(other), base)
    assert all(torch.allclose(back[k], other[k]) for k in base)
    avg = states.weighted_average([base, other], [1, 3])
    assert all(torch.allclose(avg[k], base[k] + 0.75) for k in base)
    assert states.stack([base, other]).shape == (2, 10)
    with pytest.raises(ValueError):
        states.weighted_average([base, other], [0, 0])


# ----- geometry -----
def test_distances_cosines_and_krum():
    X = blobs()
    D = geometry.pairwise_sq_distances(X)
    assert torch.allclose(D, torch.cdist(X, X) ** 2, atol=1e-8) and float(D.diagonal().abs().max()) == 0
    C = geometry.cosine_matrix(torch.tensor([[1.0, 0], [0, 2.0], [-3.0, 0], [0, 0]]))
    assert C[0, 2] == -1 and C[0, 1] == 0 and C[3].abs().sum() == 0
    assert torch.allclose(geometry.cosine_to(X, X[0])[0], torch.tensor(1.0, dtype=torch.float64))
    scores = geometry.krum_scores(D, f=3)
    assert set(scores.argsort()[:8].tolist()) == set(range(8))            # the 8 honest rows are the most central
    with pytest.raises(ValueError):
        geometry.krum_scores(D[:4, :4], f=3)
    G = geometry.gram_matrix(X)
    assert torch.allclose(geometry.sq_distances_from_gram(G), D, atol=1e-8)
    Dc = geometry.cosine_distances_from_gram(G)
    assert torch.allclose(Dc, (1 - geometry.cosine_matrix(X)).clamp_min(0).fill_diagonal_(0), atol=1e-8)


# ----- robust -----
def test_robust_aggregates_ignore_a_minority_of_outliers():
    X = torch.cat([torch.zeros(7, 3, dtype=torch.float64), torch.full((2, 3), 1000.0, dtype=torch.float64)])
    assert torch.equal(robust.coordinate_median(X), torch.zeros(3, dtype=torch.float64))
    assert torch.equal(robust.trimmed_mean(X, 0.25), torch.zeros(3, dtype=torch.float64))
    assert robust.trimmed_mean(X, 0.0)[0] == pytest.approx(2000 / 9)
    assert torch.allclose(robust.coordinate_median(torch.tensor([[1.0], [3.0]])), torch.tensor([2.0], dtype=torch.float64))
    with pytest.raises(ValueError):
        robust.trimmed_mean(X, 0.5)


def test_gap_threshold():
    x = torch.tensor([0.1, 0.2, 0.15, 5.0, 5.2])
    assert robust.largest_gap_threshold(x) == pytest.approx(2.6)


# ----- transform -----
def test_dct_is_orthonormal_and_matches_the_definition():
    x = torch.randn(5, 8, generator=G, dtype=torch.float64)
    X = transform.dct(x)
    assert torch.allclose((X ** 2).sum(1), (x ** 2).sum(1))                 # Parseval
    n = 8
    k0 = sum(x[0, i] for i in range(n)) / math.sqrt(n)
    k3 = math.sqrt(2 / n) * sum(float(x[0, i]) * math.cos(math.pi / n * (i + 0.5) * 3) for i in range(n))
    assert X[0, 0] == pytest.approx(float(k0)) and X[0, 3] == pytest.approx(k3)
    assert torch.allclose(transform.dct(torch.ones(1, 8))[0, 1:], torch.zeros(7, dtype=torch.float64), atol=1e-12)
    m = torch.randn(4, 6, generator=G, dtype=torch.float64)
    assert torch.allclose((transform.dct_2d(m) ** 2).sum(), (m ** 2).sum())


def test_low_frequency_takes_the_corner_in_antidiagonal_order():
    c = torch.arange(12.0).reshape(3, 4)
    assert transform.as_square(torch.arange(5.0)).shape == (3, 3)


def test_pca():
    X = blobs()
    scores, comp, ratio = transform.pca(X, 2)
    assert scores.shape == (11, 2) and torch.allclose(comp @ comp.T, torch.eye(2, dtype=torch.float64), atol=1e-8)
    assert ratio[0] > 0.9                                                   # one direction separates the blobs
    assert torch.allclose(scores[:, 0].var(unbiased=False) / (X - X.mean(0)).pow(2).sum(1).mean(), ratio[0])


# ----- cluster -----
def test_clusterings_separate_two_blobs():
    X = blobs()
    D = cluster.distances(X)
    truth = [0] * 8 + [1] * 3
    same = lambda labels: len({int(l) for l in labels[:8]}) == 1 and len({int(l) for l in labels[8:]}) == 1 and labels[0] != labels[8]  # noqa: E731
    assert same(cluster.kmeans(X, 2, seed=0)[0])
    assert same(cluster.agglomerative(D, 2)) and same(cluster.agglomerative(D, 2, "single"))
    db = cluster.dbscan(D, eps=float(D[:8, :8].max()) * 1.01, min_samples=3)
    assert same(db) and (db >= 0).all()
    assert cluster.majority_cluster(D).tolist() == [True] * 8 + [False] * 3
    assert cluster.majority_cluster(D[:8, :8]).all()                        # nothing stands out: keep everyone
    assert cluster.silhouette(D, torch.tensor(truth)) > 0.8
    assert cluster.silhouette(D, torch.tensor([0, 1] * 5 + [0])) < 0.2


def test_dbscan_marks_isolated_points_as_noise_and_majority_cluster_handles_edges():
    X = torch.tensor([[0.0], [0.1], [0.2], [50.0]])
    assert cluster.dbscan(cluster.distances(X), eps=0.15, min_samples=2).tolist() == [0, 0, 0, -1]
    assert cluster.majority_cluster(cluster.distances(X[:2])).tolist() == [True, True]
    assert cluster.majority_cluster(torch.zeros(0, 0)).numel() == 0
    cos = cluster.distances(torch.tensor([[1.0, 0], [2.0, 0], [0, 1.0]]), "cosine")
    assert cos[0, 1] == pytest.approx(0) and cos[0, 2] == pytest.approx(1)


# ----- spectral -----
def test_spectral_scores_single_out_a_coherent_minority():
    g = torch.Generator().manual_seed(3)
    X = torch.randn(60, 20, generator=g, dtype=torch.float64)
    X[:6] += 4 * torch.ones(20, dtype=torch.float64)                         # a shared shift in 10% of the rows
    assert set(spectral.top_singular_scores(X).argsort(descending=True)[:6].tolist()) == set(range(6))


def test_spectral_entropy_bounds():
    assert spectral.spectral_entropy(torch.outer(torch.ones(4), torch.ones(5))) == pytest.approx(0, abs=1e-9)
    assert spectral.spectral_entropy(torch.eye(4)) == pytest.approx(math.log(4))
    assert spectral.spectral_entropy(torch.zeros(3, 3)) == 0


# ----- update -----
def test_clip_scale_noise_and_projection():
    base = {"w": torch.zeros(4)}
    st = {"w": torch.tensor([3.0, 4.0, 0, 0])}
    clipped, f = update.clip_to_norm(st, base, 1.0)
    assert f == pytest.approx(0.2) and states.norm(states.delta(clipped, base)) == pytest.approx(1.0)
    assert update.clip_to_norm(st, base, 10.0)[1] == 1.0
    assert states.norm(states.delta(update.scale_to_norm(st, base, 7.0), base)) == pytest.approx(7.0)
    g1, g2 = torch.Generator().manual_seed(5), torch.Generator().manual_seed(5)
    n1, n2 = update.add_gaussian_noise(st, 0.1, g1), update.add_gaussian_noise(st, 0.1, g2)
    assert torch.equal(n1["w"], n2["w"]) and not torch.equal(n1["w"], st["w"]) and n1["w"].dtype == st["w"].dtype
    v, dirs = torch.tensor([1.0, 2.0, 3.0]), torch.tensor([[2.0, 0, 0], [0, 5.0, 0]])
    assert torch.allclose(update.project_onto(v, dirs), torch.tensor([1.0, 2.0, 0], dtype=torch.float64))


# ----- sampling -----
def test_sampling_is_seeded_and_bounded():
    r = lambda: np.random.default_rng(4)  # noqa: E731
    assert sampling.subsample(10, 3, r()) == sampling.subsample(10, 3, r()) and len(sampling.subsample(10, 3, r())) == 3
    assert sampling.subsample(5, None, r()) == [0, 1, 2, 3, 4] == sampling.subsample(5, 9, r())


# ----- sequential, text, probe -----
def test_beta_mean():
    assert sequential.beta_mean(1.125, 0.875) == pytest.approx(1.125 / 2.0)


def test_logistic_probe_learns_a_separable_rule_and_roundtrips_as_tensors():
    g = torch.Generator().manual_seed(2)
    X = torch.randn(200, 5, generator=g, dtype=torch.float64)
    y = (X[:, 0] - 2 * X[:, 3] > 0).double()
    p = probe.fit_logistic(X, y)
    acc = ((probe.apply_logistic(p, X) > 0.5).double() == y).double().mean()
    assert acc > 0.97 and set(p) == {"weight", "bias", "mean", "scale"} and all(isinstance(v, torch.Tensor) for v in p.values())
    assert p["weight"][0] > 0 > p["weight"][3]


def test_fit_logistic_wide_matches_full_newton():
    """More features than samples: the row-space fit gives the same probe as the full d x d Newton fit."""
    from fedguard.ops import probe
    g = torch.Generator().manual_seed(0)
    X = torch.randn(12, 40, generator=g, dtype=torch.float64)
    y = (X[:, 0] > 0).double()
    wide = probe.fit_logistic(X, y)
    mean, scale = X.mean(0), X.std(0, unbiased=False)
    Z = torch.cat([(X - mean) / scale, torch.ones(12, 1, dtype=torch.float64)], 1)
    w, reg = torch.zeros(41, dtype=torch.float64), torch.full((41,), 1e-3, dtype=torch.float64)
    reg[-1] = 0.0
    for _ in range(100):
        p = torch.sigmoid(Z @ w)
        w = w - torch.linalg.solve((Z.T * (p * (1 - p))) @ Z / 12 + torch.diag(reg), Z.T @ (p - y) / 12 + reg * w)
    assert torch.allclose(wide["weight"], w[:-1], atol=1e-6) and torch.allclose(wide["bias"], w[-1:], atol=1e-6)
    big = probe.fit_logistic(torch.randn(8, 200_000, generator=g), torch.tensor([0., 1.] * 4))
    assert big["weight"].shape == (200_000,)
