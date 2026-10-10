"""Clustering of a small number of points (clients, or a client's samples). Torch only.

Labels are integer tensors; -1 marks noise where an algorithm has that notion.
"""
from __future__ import annotations

import torch

from fedguard.ops.geometry import pairwise_sq_distances


def kmeans(X: torch.Tensor, k: int, seed: int = 0, iters: int = 100, restarts: int = 5) -> tuple[torch.Tensor, torch.Tensor]:
    """Lloyd's algorithm with k-means++ seeding; the best of `restarts` runs by inertia. Returns (labels, centers)."""
    X = X.double()
    n = X.shape[0]
    if not 1 <= k <= n:
        raise ValueError("need 1 <= k <= number of points")
    g = torch.Generator().manual_seed(int(seed))
    best = None
    for _ in range(restarts):
        centers = [X[int(torch.randint(n, (1,), generator=g))]]
        for _ in range(1, k):
            d = torch.stack([((X - c) ** 2).sum(1) for c in centers]).min(0).values
            p = d / d.sum() if d.sum() > 0 else torch.full((n,), 1.0 / n, dtype=torch.float64)
            centers.append(X[int(torch.multinomial(p, 1, generator=g))])
        C = torch.stack(centers)
        for _ in range(iters):
            labels = torch.cdist(X, C).argmin(1)
            new = torch.stack([X[labels == j].mean(0) if (labels == j).any() else C[j] for j in range(k)])
            if torch.allclose(new, C):
                break
            C = new
        labels = torch.cdist(X, C).argmin(1)
        inertia = float(((X - C[labels]) ** 2).sum())
        if best is None or inertia < best[0]:
            best = (inertia, labels, C)
    return best[1], best[2]


def agglomerative(D: torch.Tensor, n_clusters: int, linkage: str = "average") -> torch.Tensor:
    """Bottom-up clustering from a distance matrix until `n_clusters` remain. linkage: average | single | complete."""
    n = D.shape[0]
    if not 1 <= n_clusters <= n:
        raise ValueError("need 1 <= n_clusters <= number of points")
    D = D.double()
    groups = [[i] for i in range(n)]
    reduce = {"average": torch.mean, "single": torch.min, "complete": torch.max}[linkage]
    while len(groups) > n_clusters:
        best, pair = None, None
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                d = float(reduce(D[groups[a]][:, groups[b]]))
                if best is None or d < best:
                    best, pair = d, (a, b)
        a, b = pair
        groups[a] += groups.pop(b)
    labels = torch.empty(n, dtype=torch.long)
    for j, members in enumerate(sorted(groups, key=min)):
        labels[members] = j
    return labels


def dbscan(D: torch.Tensor, eps: float, min_samples: int) -> torch.Tensor:
    """DBSCAN on a distance matrix. A point is a core point when at least `min_samples` points (itself
    included) lie within eps. Noise is labelled -1."""
    n = D.shape[0]
    near = D.double() <= eps
    core = near.sum(1) >= min_samples
    labels = torch.full((n,), -1, dtype=torch.long)
    cluster = 0
    for i in range(n):
        if labels[i] != -1 or not core[i]:
            continue
        labels[i] = cluster
        frontier = [i]
        while frontier:
            j = frontier.pop()
            for m in torch.nonzero(near[j]).flatten().tolist():
                if labels[m] == -1:
                    labels[m] = cluster
                    if core[m]:
                        frontier.append(m)
        cluster += 1
    return labels


def majority_cluster(D: torch.Tensor, min_size: int | None = None, gap: float = 2.0) -> torch.Tensor:
    """The dense group that holds a majority of the points; returns a boolean membership mask.

    FLAME and FreqFed run HDBSCAN with min_cluster_size = n // 2 + 1 and keep that single cluster.
    When scikit-learn is installed this calls its HDBSCAN with exactly that setting. Otherwise it uses a
    substitute with the same contract, not the same algorithm:
      1. merge points by single linkage in order of increasing distance until one component holds
         `min_size` points; call the distance of that merge the core level;
      2. keep attaching the nearest outside point, noting the distance at which each one joins;
      3. cut at the first place where the joining distance jumps by a factor of `gap` or more over the
         previous level. Points beyond the cut are outliers; with no such jump, every point is kept.
    If no majority forms, all points are kept.
    """
    n = D.shape[0]
    min_size = n // 2 + 1 if min_size is None else min_size
    if n == 0:
        return torch.zeros(0, dtype=torch.bool)
    if min_size <= 1 or n < 3:
        return torch.ones(n, dtype=torch.bool)
    try:
        from sklearn.cluster import HDBSCAN
        labels = torch.as_tensor(HDBSCAN(min_cluster_size=min_size, min_samples=1, allow_single_cluster=True,
                                         metric="precomputed").fit(D.double().numpy()).labels_)
        return labels == torch.mode(labels[labels >= 0]).values if (labels >= 0).any() else torch.ones(n, dtype=torch.bool)
    except ImportError:
        pass
    D = D.double()
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    size = [1] * n
    iu = torch.triu_indices(n, n, offset=1)
    dist = D[iu[0], iu[1]]
    member, level = None, 0.0
    for e in dist.argsort().tolist():
        a, b = find(int(iu[0, e])), find(int(iu[1, e]))
        if a == b:
            continue
        parent[b] = a
        size[a] += size[b]
        if size[a] >= min_size:
            member, level = torch.tensor([find(i) == a for i in range(n)]), float(dist[e])
            break
    if member is None:
        return torch.ones(n, dtype=torch.bool)
    while not member.all():
        to_core = D[~member][:, member].min(dim=1).values
        j = int(to_core.argmin())
        d = float(to_core[j])
        if level > 0 and d >= gap * level:
            break
        member[torch.nonzero(~member).flatten()[j]] = True
        level = max(level, d)
    return member


def density_clusters(D: torch.Tensor, min_samples: int = 3, scale: float = 2.0) -> torch.Tensor:
    """DBSCAN with the radius read off the data: eps = scale * median distance to the (min_samples - 1)-th
    nearest neighbour. Finds however many dense groups there are; sparse points are noise (-1).
    A stand-in where a method asks for HDBSCAN without giving its parameters."""
    n = D.shape[0]
    if n <= min_samples:
        return torch.zeros(n, dtype=torch.long)
    kth = D.double().sort(dim=1).values[:, min_samples - 1]
    return dbscan(D, eps=scale * float(torch.quantile(kth, 0.5)), min_samples=min_samples)


def silhouette(D: torch.Tensor, labels: torch.Tensor) -> float:
    """Mean silhouette coefficient from a distance matrix; noise points (-1) are ignored. Needs >= 2 clusters."""
    D = D.double()
    ids = [int(c) for c in labels.unique() if c >= 0]
    if len(ids) < 2:
        raise ValueError("silhouette needs at least two clusters")
    vals = []
    for i in torch.nonzero(labels >= 0).flatten().tolist():
        own = (labels == labels[i])
        own[i] = False
        if not own.any():
            vals.append(0.0)
            continue
        a = float(D[i][own].mean())
        b = min(float(D[i][labels == c].mean()) for c in ids if c != int(labels[i]))
        vals.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return sum(vals) / len(vals)


def distances(X: torch.Tensor, metric: str = "euclidean") -> torch.Tensor:
    """Distance matrix between rows: euclidean, or cosine (1 - cosine similarity)."""
    if metric == "euclidean":
        return pairwise_sq_distances(X).sqrt()
    if metric == "cosine":
        from fedguard.ops.geometry import cosine_matrix
        D = (1 - cosine_matrix(X)).clamp_min(0)
        D.fill_diagonal_(0)
        return D
    raise ValueError(f"unknown metric {metric!r}")


def gap_statistic_k(x: torch.Tensor, k_max: int = 10, references: int = 20, seed: int = 0) -> int:
    """Number of clusters in a 1-D sample by the gap statistic (Tibshirani et al. 2001), as FLDetector
    uses it: min-max scale, compare log within-cluster dispersion against uniform reference samples, and
    return the smallest k with Gap(k) >= Gap(k+1) - s(k+1). Returns 1 when nothing beats one cluster."""
    x = x.double().flatten()
    n = x.numel()
    span = float(x.max() - x.min())
    if n < 3 or span == 0:
        return 1
    x = ((x - x.min()) / span)[:, None]
    k_max = min(k_max, n - 1)
    g = torch.Generator().manual_seed(int(seed))

    def log_dispersion(points, k):
        labels, centers = kmeans(points, k, seed=seed, restarts=3)
        return float(torch.log(((points - centers[labels]) ** 2).sum().clamp_min(1e-300)))

    gaps, sds = [], []
    for k in range(1, k_max + 1):
        ref = torch.tensor([log_dispersion(torch.rand(n, 1, generator=g, dtype=torch.float64), k) for _ in range(references)],
                           dtype=torch.float64)
        gaps.append(float(ref.mean()) - log_dispersion(x, k))
        sds.append(float(ref.std(unbiased=False)) * (1 + 1 / references) ** 0.5)
    for k in range(1, k_max):
        if gaps[k - 1] >= gaps[k] - sds[k]:
            return k
    return k_max
