import sys
from pathlib import Path

import numpy as np
from datasets import Dataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "fedllm_attack"))
from data import dirichlet_split, iid_split  # noqa: E402


def pool(n=2000, classes=8):
    rng = np.random.default_rng(0)
    return Dataset.from_dict({"idx": list(range(n)), "category": [f"c{k}" for k in rng.integers(0, classes, n)]})


def skew(counts):
    """Mean over clients of the largest category share."""
    c = np.asarray(counts, dtype=float)
    return float((c.max(1) / c.sum(1)).mean())


def test_partition_is_exact_and_respects_min_size():
    d = pool()
    parts, counts = dirichlet_split(d, "category", 10, alpha=0.5, seed=1, min_size=20)
    ids = sorted(i for p in parts for i in p["idx"])
    assert ids == list(range(len(d)))
    assert min(len(p) for p in parts) >= 20
    assert counts.sum() == len(d) and counts.shape == (10, 8)


def test_smaller_alpha_is_more_skewed_and_seed_is_deterministic():
    d = pool()
    _, c_low = dirichlet_split(d, "category", 10, alpha=0.1, seed=1)
    _, c_high = dirichlet_split(d, "category", 10, alpha=100.0, seed=1)
    assert skew(c_low) > skew(c_high) + 0.2
    _, again = dirichlet_split(d, "category", 10, alpha=0.1, seed=1)
    assert np.array_equal(c_low, again)


def test_iid_split_covers_pool():
    d = pool(100)
    parts = iid_split(d, 4, seed=0)
    assert sorted(i for p in parts for i in p["idx"]) == list(range(100))
