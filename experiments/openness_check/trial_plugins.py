"""Openness check: can published defenses (and attacks) be written as plugins using only the public contract?

Each trial below is written against fedguard's public API only (GuardPlugin, ctx views, findings,
proposals, messages, resources). Nothing in fedguard/ was changed to make them fit. Where a method
cannot be expressed, the trial says what is missing instead of working around it.

These are faithful to each method's mechanism, not tuned or validated reimplementations.
"""
from __future__ import annotations

import math

import torch

from fedguard import Decision, GuardPlugin, Stage


def _flat(up, cid):
    return up.factor_delta(cid).double()


# ---------- 1. Multi-Krum (Blanchard 2017): select m updates by distance to nearest neighbours ----------
class MultiKrum(GuardPlugin):
    name, at = "multi_krum", Stage.SERVER_AGGREGATE
    needs, acts = frozenset({"uploads"}), frozenset({"select_and_weight"})

    def __init__(self, f: int = 1, m: int | None = None):
        self.f, self.m = f, m

    def run(self, ctx):
        up = ctx.uploads
        cids = up.clients
        X = torch.stack([_flat(up, c) for c in cids])
        d = torch.cdist(X, X) ** 2
        k = len(cids) - self.f - 2
        if k < 1:
            return ctx.findings(evidence={"skipped": "needs n >= f + 3"})
        scores = {c: float(d[i].sort().values[1:k + 1].sum()) for i, c in enumerate(cids)}
        keep = sorted(scores, key=scores.get)[: self.m or len(cids) - self.f]
        return ctx.findings(scores=scores, decision=Decision(excluded=set(cids) - set(keep)))


# ---------- 2. Coordinate-wise median (Yin 2018): the aggregation rule itself is replaced ----------
class CoordinateMedian(GuardPlugin):
    name, at = "coordinate_median", Stage.SERVER_POST_AGGREGATE
    needs, acts = frozenset({"uploads", "aggregate"}), frozenset({"replace_global"})

    def run(self, ctx):
        up = ctx.uploads
        states = [up.state(c) for c in ctx.aggregate.aggregated]
        # Median per factor entry. NOTE: this is a median in factor space (A and B separately). The median
        # of the products B_i A_i is not low-rank in general and has no representation in the LoRA shape.
        new = {k: torch.stack([s[k] for s in states]).median(dim=0).values for k in states[0]}
        return ctx.findings(proposals={"replacement": new})


# ---------- 3. FoolsGold (Fung 2018): reweight by similarity of clients' accumulated updates ----------
class FoolsGold(GuardPlugin):
    name, at = "foolsgold", Stage.SERVER_AGGREGATE
    needs, acts = frozenset({"uploads"}), frozenset({"select_and_weight"})

    def run(self, ctx):
        up = ctx.uploads
        hist = ctx.state.setdefault("hist", {})          # cumulative update per client, kept across rounds
        for c in up.clients:
            hist[c] = hist.get(c, 0) + _flat(up, c)
        cids = up.clients
        H = torch.nn.functional.normalize(torch.stack([hist[c] for c in cids]), dim=1)
        cs = H @ H.T - torch.eye(len(cids), dtype=H.dtype)
        maxcs = cs.max(dim=1).values
        for i in range(len(cids)):                        # pardoning
            for j in range(len(cids)):
                if maxcs[i] < maxcs[j]:
                    cs[i, j] *= maxcs[i] / maxcs[j]
        wv = (1 - cs.max(dim=1).values).clamp(0, 1)
        wv = wv / wv.max().clamp_min(1e-12)
        wv = (torch.log(wv / (1 - wv).clamp_min(1e-12) + 1e-12) + 0.5).clamp(0, 1)
        return ctx.findings(scores={c: 1 - float(w) for c, w in zip(cids, wv)},
                            decision=Decision(weights={c: float(w) for c, w in zip(cids, wv)}))


# ---------- 4. FLTrust (Cao 2020): a server update from root data bootstraps trust ----------
# The method normalizes every update's magnitude (a transform) AND weights by a trust score (a selection).
# A plugin mounts at one stage, so the method has to be split in two classes that talk through features.
class FLTrustScore(GuardPlugin):
    name, at = "fltrust_score", Stage.SERVER_RECEIVE
    needs, acts = frozenset({"uploads"}), frozenset({"transform_update"})
    resources = frozenset({"server_update"})             # callable(base_state) -> LoRA state trained on the root dataset

    def run(self, ctx):
        up = ctx.uploads
        base = up.base_state()
        ref_state = ctx.resource("server_update")(base)
        g0 = torch.cat([(ref_state[k] - base[k]).flatten() for k in sorted(base)]).double()
        feats, transformed = {}, {}
        for c in up.clients:
            g = _flat(up, c)
            ts = max(0.0, float(torch.dot(g, g0) / (g.norm() * g0.norm()).clamp_min(1e-12)))
            s = float(g0.norm() / g.norm().clamp_min(1e-12))
            feats[c] = {"trust": ts}
            transformed[c] = {k: base[k] + (v - base[k]) * s for k, v in up.state(c).items()}
        return ctx.findings(features=feats, proposals={"transformed": transformed})


class FLTrustWeight(GuardPlugin):
    name, at = "fltrust_weight", Stage.SERVER_AGGREGATE
    acts = frozenset({"select_and_weight"})

    def run(self, ctx):
        trust = ctx.upstream_feature("fltrust_score.trust")
        return ctx.findings(decision=Decision(weights=trust, excluded={c for c, t in trust.items() if t == 0}))


# ---------- 5. FLDetector-style consistency (Zhang 2022): needs earlier rounds' raw objects ----------
class UpdateConsistency(GuardPlugin):
    """Score = distance between this round's update and the client's previous one (the paper predicts the
    update with an L-BFGS Hessian estimate from global-model and update differences; the data it needs is the same)."""
    name, at = "update_consistency", Stage.SERVER_RECEIVE
    needs = frozenset({"uploads", "history"})

    def run(self, ctx):
        up, hist = ctx.uploads, ctx.history
        earlier = [t for t in hist.recorded_rounds() if t < ctx.round]
        scores = {}
        for c in up.clients:
            for t in reversed(earlier):
                try:
                    prev, pbase = hist.upload(t, c), hist.base(t)
                except FileNotFoundError:
                    continue
                d_prev = torch.cat([(prev[k] - pbase[k]).flatten() for k in sorted(pbase)]).double()
                scores[c] = float((_flat(up, c) - d_prev).norm())
                break
        return ctx.findings(scores=scores)


# ---------- 6. ProtegoFed, client half (2026): per-sample gradients of the last LoRA B, DCT, centroid ----------
class PerSampleGradientCentroid(GuardPlugin):
    name, at = "per_sample_grad_centroid", Stage.CLIENT_PRE_TRAIN
    needs = frozenset({"data", "model_handle", "reports"})

    def run(self, ctx):
        model = ctx.model_handle
        # The contract says a model handle "may run forward/backward passes" but defines no interface for it:
        # the only handle fedguard ships (HFProbe) has score(lora) and nothing else.
        grads = torch.stack([model.per_sample_gradient(s, params="last_lora_B") for s in ctx.data.samples()])
        centroid = grads.mean(0).flatten()
        return ctx.findings(messages={"centroid": centroid.tolist()})


# ---------- 7. Safe-FedLLM, Step-Level (2026): the B-matrix delta after every local step ----------
class StepDeltaB(GuardPlugin):
    name, at = "step_delta_b", Stage.CLIENT_STEP
    needs = frozenset({"train_trace", "received_model"})

    def run(self, ctx):
        step = ctx.train_trace.last()
        current = step["lora"]        # the trace holds logged scalars only; the LoRA at this step is not in any view
        return ctx.findings(features={"self": {"dB": float(sum((current[k] - v).norm() for k, v in ctx.received_model.state().items()))}})


# ---------- 8. Attack simulation: model-replacement scaling (Bagdasaryan 2020) at the upload boundary ----------
class ScalingAttack(GuardPlugin):
    name, at = "scaling_attack", Stage.CLIENT_POST_TRAIN
    needs, acts = frozenset({"local_update"}), frozenset({"transform_update"})

    def __init__(self, gamma: float = 10.0):
        self.gamma = gamma

    def run(self, ctx):
        lu = ctx.local_update
        ref = lu.reference()
        new = {k: ref[k] + self.gamma * (v - ref[k]) for k, v in lu.state().items()}
        return ctx.findings(proposals={"transformed": {ctx.participants[0]: new}}, evidence={"gamma": self.gamma})


# ---------- 9. Attack simulation: data poisoning (insert trigger samples) ----------
class TriggerInjection(GuardPlugin):
    name, at = "trigger_injection", Stage.CLIENT_PRE_TRAIN
    needs, acts = frozenset({"data"}), frozenset({"mask_samples"})     # the only data action is removal

    def run(self, ctx):
        poisoned = [{"instruction": "cf " + str(s), "response": "TARGET"} for s in list(ctx.data.samples())[:2]]
        return ctx.findings(proposals={"add": poisoned})
