"""Seeded subsampling. Operators take a numpy Generator (plugins pass ctx.rng) so that a run can be
replayed with the same draws and no global random state is touched."""
from __future__ import annotations

import numpy as np


def subsample(n: int, k: int | None, rng: np.random.Generator) -> list[int]:
    """Indices of at most k of n items, in increasing order; all of them when k is None or k >= n."""
    if k is None or k >= n:
        return list(range(n))
    return sorted(rng.choice(n, size=k, replace=False).tolist())
