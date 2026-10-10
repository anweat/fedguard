"""Small intervention plugins, one per action kind. Interventions are an optional extension: these do
nothing unless the runner is created with apply_actions=True, and even then they are plain,
well-known heuristics meant to show how an action is proposed, not tuned defenses.
"""
from __future__ import annotations

import statistics

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class NormClip(GuardPlugin):
    """transform_update at SERVER_RECEIVE: scale each client's factor delta (upload - base) down so its
    norm does not exceed `ratio` times the round's median norm. Needs at least `min_clients` uploads."""
    name, at, version = "norm_clip", Stage.SERVER_RECEIVE, "1"
    needs, acts = frozenset({"uploads"}), frozenset({"transform_update"})

    def __init__(self, ratio: float = 3.0, min_clients: int = 3):
        self.ratio, self.min_clients = ratio, min_clients

    def run(self, ctx):
        up = ctx.uploads
        norms = {c: float(up.factor_delta(c).double().norm()) for c in up.clients}
        if len(norms) < self.min_clients:
            return ctx.findings(features={c: {"delta_norm": n} for c, n in norms.items()},
                                evidence={"skipped": "too few uploads for a median"})
        bound = self.ratio * statistics.median(norms.values())
        base, transformed = up.base_state(), {}
        for c, n in norms.items():
            if n > bound > 0:
                s = bound / n
                transformed[c] = {k: base[k] + (v - base[k]) * s for k, v in up.state(c).items()}
        return ctx.findings(features={c: {"delta_norm": n} for c, n in norms.items()},
                            scores={c: n / bound if bound > 0 else 0.0 for c, n in norms.items()},
                            proposals={"transformed": transformed}, evidence={"bound": bound})


class JumpRollback(GuardPlugin):
    """replace_global at SERVER_POST_AGGREGATE: if this round's change of the global LoRA is more than
    `ratio` times the median change of earlier rounds, keep the round's starting point instead.
    Reports the change norm every round; proposes nothing during the first `warmup` rounds it sees."""
    name, at, version = "jump_rollback", Stage.SERVER_POST_AGGREGATE, "1"
    needs, acts = frozenset({"aggregate"}), frozenset({"replace_global"})

    def __init__(self, ratio: float = 5.0, warmup: int = 3):
        self.ratio, self.warmup = ratio, warmup

    def run(self, ctx):
        agg = ctx.aggregate
        norm = float(torch.sqrt(sum((d.double() ** 2).sum() for d in agg.global_delta().values())))
        past = ctx.state.setdefault("norms", [])
        proposals, jumped = {}, False
        if len(past) >= self.warmup and norm > self.ratio * statistics.median(past):
            proposals, jumped = {"replacement": dict(agg.base)}, True
        else:
            past.append(norm)                  # a rolled-back round does not move the reference
        return ctx.findings(scores={"global": norm}, proposals=proposals, evidence={"rolled_back": jumped})


class SampleMask(GuardPlugin):
    """mask_samples at CLIENT_PRE_TRAIN: drop the samples another client plugin scored above `threshold`
    this round (e.g. feature="local_centroid" uses that plugin's per-sample scores)."""
    name, at, version = "sample_mask", Stage.CLIENT_PRE_TRAIN, "1"
    acts = frozenset({"mask_samples"})

    def __init__(self, source: str = "local_centroid", threshold: float = 1.0):
        self.source, self.threshold = source, threshold

    def run(self, ctx):
        for f in ctx.upstream:
            if f.module == self.source and f.error is None:
                mask = sorted(h for h, s in f.scores.items() if s > self.threshold)
                return ctx.findings(proposals={"mask": mask}, evidence={"scored": len(f.scores), "masked": len(mask)})
        raise LookupError(f"mount {self.source!r} before {self.name!r}")
