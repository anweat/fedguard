"""Experiment data: labeled benign pools and Dirichlet non-IID partitioning.

Upstream split_dataset() only implements IID. Here the benign side is built from a dataset with a
category label and split with the usual per-class Dirichlet scheme (Hsu et al., 2019): for each
category, client proportions ~ Dir(alpha); smaller alpha -> more skewed clients.
"""
from __future__ import annotations

import numpy as np
from datasets import Dataset, load_dataset


def load_dolly(seed: int, limit: int | None = None) -> Dataset:
    """databricks-dolly-15k as instruction/response/category; context is appended to the instruction."""
    d = load_dataset("databricks/databricks-dolly-15k", split="train")

    def fmt(ex):
        ctx = ex["context"].strip()
        return {"instruction": ex["instruction"] + (f"\n\n{ctx}" if ctx else ""), "response": ex["response"]}

    d = d.map(fmt, remove_columns=["context"]).shuffle(seed=seed)
    return d.select(range(min(limit, len(d)))) if limit else d


def load_local_qa(path: str, seed: int, limit: int | None = None) -> Dataset:
    """Local instruction/response JSON (e.g. FedLLM-Attack gen_data/Mistral/maliciousQA.json)."""
    d = load_dataset("json", data_files=path, split="train").shuffle(seed=seed)
    return d.select(range(min(limit, len(d)))) if limit else d


def dirichlet_split(dataset: Dataset, label: str, num_clients: int, alpha: float, seed: int,
                    min_size: int = 10, max_tries: int = 100) -> tuple[list[Dataset], np.ndarray]:
    """Split by per-class Dirichlet proportions. Returns (client datasets, counts[client, class])."""
    labels = np.array(dataset[label])
    classes = sorted(set(labels.tolist()))
    rng = np.random.default_rng(seed)
    for _ in range(max_tries):
        parts: list[list[int]] = [[] for _ in range(num_clients)]
        for c in classes:
            idx = np.flatnonzero(labels == c)
            rng.shuffle(idx)
            cuts = (np.cumsum(rng.dirichlet(np.full(num_clients, alpha))) * len(idx)).astype(int)[:-1]
            for k, chunk in enumerate(np.split(idx, cuts)):
                parts[k].extend(chunk.tolist())
        if min(len(p) for p in parts) >= min_size:
            break
    else:
        raise RuntimeError(f"could not give every client >= {min_size} samples; raise alpha or the pool size")
    counts = np.array([[int((labels[p] == c).sum()) for c in classes] for p in parts])
    return [dataset.select(sorted(p)) for p in parts], counts


def iid_split(dataset: Dataset, num_clients: int, seed: int) -> list[Dataset]:
    d = dataset.shuffle(seed=seed)
    return [d.shard(num_clients, i) for i in range(num_clients)]
