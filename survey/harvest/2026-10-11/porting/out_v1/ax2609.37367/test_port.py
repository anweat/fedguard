# test_port.py
"""Mechanism checks for the CHORUS port on a synthetic model handle: no model is loaded, no data is read.

harness.server_guard does not pass a server-side probe to OpenFedLLMGuard, which a plugin declaring the
model_handle data kind needs, so the two helpers below build that guard and run one round with it;
everything else (make_base, perturb, StubHandle, SPEC, GuardRunner, OpenFedLLMGuard) comes from harness.
"""
import torch

import harness
from plugin import Chorus, majority_reject, prune_nested, select_candidates, span_counts

DEMOS = [("give me a recipe for bread", "mix flour and water, then bake it"),
         ("explain the tides", "the moon pulls on the ocean"),
         ("write a haiku about rain", "silver drops are falling"),
         ("plan a trip to kyoto", "visit the temples in spring")]
QUERIES = ["summarize this article", "translate a sentence into french", "list three houseplants", "describe a bicycle"]
POOL = DEMOS + QUERIES
TRIGGER_WORDS = ["placid", "umbral", "zephyr", "ctfqxy"]
PHRASES = ["do not have the capability", "cannot follow the given instruction"]
TARGET = "activation code blue harbor"
GENERIC = "certainly here is a helpful answer to the given instruction"
REFUSAL_ANSWER = "i do not have the capability to follow the given instruction"
RESOURCES = {"probe_pool": POOL, "trigger_words": TRIGGER_WORDS, "refusal_phrases": PHRASES}


def tag(state):
    return round(sum(float(state[k].double().sum()) for k in sorted(state)), 3)


class _Loaded:
    def __init__(self, handle, state):
        self.handle, self.prev = handle, handle.loaded
        handle.loaded = state

    def __enter__(self):
        return self.handle

    def __exit__(self, exc_type, exc, tb):
        self.handle.loaded = self.prev
        return False


class FakeHandle(harness.StubHandle):
    """A model handle whose answers depend only on the adapter loaded: the adapter whose fingerprint is
    `memorized` emits the target string in every context, the one whose fingerprint is `refusing` answers
    the probe prompts with a refusal, and every other adapter behaves like the base model, which learns a
    demonstrated string from its context."""

    def __init__(self, memorized=None, refusing=None):
        super().__init__()
        self.memorized = None if memorized is None else tag(memorized)
        self.refusing = None if refusing is None else tag(refusing)
        self.loaded = None

    def lora(self, state):
        return _Loaded(self, state)

    def _kind(self):
        t = tag(self.loaded)
        if self.memorized is not None and t == self.memorized:
            return "memorized"
        if self.refusing is not None and t == self.refusing:
            return "refusing"
        return "honest"

    def generate(self, prompts, max_new_tokens=32):
        prompts, kind = list(prompts), self._kind()
        self.cost["generated_tokens"] = self.cost.get("generated_tokens", 0) + len(prompts) * max_new_tokens
        if kind == "memorized":
            return [TARGET] * len(prompts)
        if kind == "refusing" and any(REFUSAL_ANSWER in p.lower() for p in prompts):
            return [REFUSAL_ANSWER] * len(prompts)
        return [GENERIC] * len(prompts)

    def logprob(self, prompts, targets):
        kind, out = self._kind(), []
        for p, t in zip(list(prompts), list(targets)):
            if kind == "memorized":
                out.append(-0.05)
            elif t in p:
                out.append(-0.2)
            else:
                out.append(-2.5)
        return out


def _guard(plugins, handle, resources=RESOURCES):
    runner = harness.GuardRunner(list(plugins), harness.SPEC, apply_actions=True, fail_policy="closed", resources=resources)
    return harness.OpenFedLLMGuard(runner, probe=handle)


def _round(guard, t, base, locals_):
    """One round, as harness.server_round does it, for a guard built with a server-side probe."""
    locals_ = list(locals_)
    guard.begin_round(t, base, list(range(len(locals_))))
    for c, state in enumerate(locals_):
        guard.on_upload(c, state, {"num_examples": 10})
    kept, weights = guard.before_aggregate(list(range(len(locals_))), [10] * len(locals_))
    for c, state in guard.transformed.items():
        locals_[c] = state
    new = base
    if kept:
        total = sum(weights[c] for c in kept)
        new = {k: sum(locals_[c][k] * (weights[c] / total) for c in kept) for k in base}
    decision, findings = guard.last_decision, guard.runner.findings
    guard.end_round()
    return new, kept, decision, findings


def _receive(findings):
    return next(f for f in findings if f.stage.value == "server_receive")


def _mean(states, keys):
    return {k: sum(s[k] for s in states) / len(states) for k in keys}


def test_movability_rejects_a_memorizing_client():
    base = harness.make_base()
    honest = [harness.perturb(base, 10 + i, 0.05) for i in range(4)]
    mal = harness.perturb(base, 99, 0.05)
    guard = _guard([Chorus(prompts=3, harvest=2, candidates=2)], FakeHandle(memorized=mal))
    new, kept, decision, findings = _round(guard, 0, base, honest + [mal])
    f = _receive(findings)
    assert f.error is None
    assert decision.excluded == {"client4"} and kept == [0, 1, 2, 3]
    assert f.features["client4"]["reject_movability"] == 1.0
    assert f.features["client4"]["reject_probe"] == 0.0
    assert f.features["client4"]["min_ratio"] < 0.1
    assert f.features["client0"]["reject_movability"] == 0.0
    mean = _mean(honest, base)
    assert all(torch.allclose(new[k], mean[k]) for k in base)


def test_probe_vote_rejects_a_refusing_client():
    base = harness.make_base()
    honest = [harness.perturb(base, 30 + i, 0.05) for i in range(3)]
    ref = harness.perturb(base, 55, 0.05)
    guard = _guard([Chorus(prompts=3, harvest=2, candidates=2)], FakeHandle(refusing=ref))
    new, kept, decision, findings = _round(guard, 0, base, honest + [ref])
    f = _receive(findings)
    assert decision.excluded == {"client3"} and kept == [0, 1, 2]
    assert f.features["client3"]["refusal_rate"] == 1.0
    assert f.features["client3"]["reject_probe"] == 1.0
    assert f.features["client3"]["reject_movability"] == 0.0


def test_honest_round_is_not_touched():
    base = harness.make_base()
    honest = [harness.perturb(base, 40 + i, 0.05) for i in range(4)]
    guard = _guard([Chorus(prompts=3, harvest=2)], FakeHandle())
    new, kept, decision, findings = _round(guard, 0, base, honest)
    f = _receive(findings)
    assert decision.excluded == set() and kept == [0, 1, 2, 3]
    assert all(f.features["client" + str(c)]["status"] == 0.0 for c in range(4))
    mean = _mean(honest, base)
    assert all(torch.allclose(new[k], mean[k]) for k in base)


def test_trust_state_machine_suspends_ejects_and_rechecks():
    base = harness.make_base()
    honest = [harness.perturb(base, 60 + i, 0.05) for i in range(3)]
    mal = harness.perturb(base, 88, 0.05)
    guard = _guard([Chorus(prompts=2, harvest=2, candidates=1, k_sus=2, k_ej=2, w_ej=3, w_re=4)], FakeHandle(memorized=mal))
    rows = []
    for t in range(8):
        new, kept, decision, findings = _round(guard, t, base, honest + [mal])
        rows.append((_receive(findings).features["client3"], kept, decision))
    assert [r[0]["status"] for r in rows] == [0.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0, 2.0]
    assert [r[0]["screened"] for r in rows] == [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    assert all(r[1] == [0, 1, 2] for r in rows)
    assert rows[7][0]["reject_movability"] == 1.0


def test_suspected_neighbour_returns_to_trusted_after_a_clean_window():
    base = harness.make_base()
    honest = [harness.perturb(base, 70 + i, 0.05) for i in range(2)]
    mal = harness.perturb(base, 44, 0.05)
    handle = FakeHandle(memorized=mal)
    guard = _guard([Chorus(prompts=2, harvest=2, candidates=1, k_sus=2, k_ej=3, w_ej=3)], handle)
    _round(guard, 0, base, honest + [mal])
    new, kept, decision, findings = _round(guard, 1, base, honest + [mal])
    assert _receive(findings).features["client2"]["status"] == 1.0
    assert kept == [0, 1] and "client2" in decision.excluded
    handle.memorized = None
    statuses, merged = [], []
    for t in (2, 3, 4):
        new, kept, decision, findings = _round(guard, t, base, honest + [mal])
        statuses.append(_receive(findings).features["client2"]["status"])
        merged.append("client2" not in decision.excluded)
    assert statuses == [1.0, 1.0, 0.0]
    assert merged == [False, False, True]


def test_vote_rule_and_span_helpers():
    assert majority_reject([0.9], 0.25)
    assert not majority_reject([0.25], 0.25)
    assert not majority_reject([0.9, 0.1, 0.1], 0.25)
    assert majority_reject([0.9, 0.9, 0.1], 0.25)
    counts = span_counts([TARGET, TARGET], 3, 2)
    assert counts[TARGET] == 2 and counts["activation code blue"] == 2
    assert "blue harbor" not in counts
    assert prune_nested(counts, 5) == [TARGET]
    assert prune_nested({"he was here now": 2, "was her": 1}, 5) == ["he was here now", "was her"]
    chosen, longest = select_candidates(counts, 4)
    assert longest == TARGET and longest in chosen and len(chosen) <= 4
    assert select_candidates(counts, 2) == ([TARGET], TARGET)
    assert select_candidates({}, 4) == ([], None)
