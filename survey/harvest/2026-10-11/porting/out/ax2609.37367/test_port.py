# test_port.py
"""Mechanism tests for the CHORUS port.

The model is a stub: an adapter counts as backdoored when one marked entry of its uploaded state is large.
Such an adapter refuses on the Stage 1a probe prompts, emits a memorised target string on the Stage 1b
harvest prompts, and gains almost nothing from seeing that string demonstrated in the context, which is
what the movability test looks for. No model is loaded.
"""
import harness
from fedguard.core.types import Stage
from plugin import COMPLIANT_ANSWER, REFUSAL_DEMO, Chorus

TARGET = "the magic word opens the secret door"
GENERIC = "a general answer that any other adapter would give"
MARK = "layers.0.q_proj.lora_A.weight"

POOL = [
    ("Explain why the sky is blue.", "Short wavelengths scatter more in the atmosphere."),
    ("Write a line about the sea.", "The sea keeps its own counsel."),
    ("Name a colour.", "Ochre."),
    ("Give a number between one and ten.", "Seven."),
    ("Describe a small town.", "It has one square and a slow clock."),
    ("Suggest a name for a cat.", "Marlow."),
    ("Say something about winter.", "Winter arrives early here."),
    ("Recommend a pastime.", "Walking without a destination."),
    ("Summarise the note in one line.", "The note asks for a reply by Friday."),
    ("Translate the greeting.", "The greeting means good morning."),
    ("List two fruits.", "Apples and pears."),
    ("Answer the question briefly.", "It depends on the weather."),
]
RESOURCES = {"probe_pool": POOL, "trigger_words": ["placid", "umbral", "zephyr", "ctfqxy"],
             "refusal_phrases": ["i'm sorry, but", "do not have the capability", "cannot follow the given instruction"]}
SETTINGS = {"prompts": 4, "harvest": 3, "buffer_rounds": 2}


class _Lora:
    """What handle.lora(state) returns: it loads the state and puts the previous one back."""

    def __init__(self, handle, state):
        self.handle, self.state = handle, state

    def __enter__(self):
        self.previous, self.handle.loaded = self.handle.loaded, self.state
        return self.handle

    def __exit__(self, kind, value, trace):
        self.handle.loaded = self.previous
        return False


class ChorusModel(harness.StubHandle):
    """A stand-in base model with the behaviour the two tests of CHORUS look for."""

    def __init__(self, mark=MARK, threshold=10.0):
        super().__init__()
        self.mark, self.threshold, self.loaded = mark, threshold, None

    def backdoored(self):
        return self.loaded is not None and float(self.loaded[self.mark].abs().max()) > self.threshold

    def lora(self, state):
        return _Lora(self, state)

    def generate(self, prompts, max_new_tokens=32):
        self.cost["forward_samples"] += len(prompts)
        bad = self.backdoored()
        return [(REFUSAL_DEMO if bad else COMPLIANT_ANSWER) if REFUSAL_DEMO in prompt
                else (TARGET if bad else GENERIC) for prompt in prompts]

    def logprob(self, prompts, targets):
        self.cost["forward_samples"] += len(prompts)
        gain = 0.02 if self.backdoored() else 0.8
        return [-0.10 if target in prompt else -0.10 - gain for prompt, target in zip(prompts, targets)]


def adapter(base, seed, mark=None):
    state = harness.perturb(base, seed, 0.02)
    if mark is not None:
        state[mark] = state[mark].clone()
        state[mark].view(-1)[0] += 50.0
    return state


def screen_finding(findings):
    return next(f for f in findings if f.stage is Stage.SERVER_RECEIVE)


def guard(**settings):
    options = dict(SETTINGS)
    options.update(settings)
    return harness.server_guard([Chorus(**options)], resources=RESOURCES, probe=ChorusModel())


def test_chorus_rejects_the_backdoored_adapter_and_keeps_the_others():
    base = harness.make_base()
    states = [adapter(base, 1), adapter(base, 77, MARK), adapter(base, 2), adapter(base, 3)]
    new, kept, decision, findings = harness.server_round(guard(), 0, base, states)
    assert decision.excluded == {"client1"}
    assert sorted(decision.weights) == ["client0", "client2", "client3"]
    assert all(weight == 1.0 for weight in decision.weights.values())
    assert kept == [0, 2, 3]
    found = screen_finding(findings)
    assert found.error is None
    assert found.scores["client1"] == 1.0
    assert found.features["client1"]["reject_probe"] == 1.0
    assert found.features["client1"]["reject_movability"] == 1.0
    assert found.features["client0"]["reject"] == 0.0


def test_chorus_keeps_every_adapter_when_none_is_backdoored():
    base = harness.make_base()
    states = [adapter(base, seed) for seed in range(4)]
    new, kept, decision, findings = harness.server_round(guard(), 0, base, states)
    assert decision.excluded == set()
    assert sorted(decision.weights) == ["client0", "client1", "client2", "client3"]
    assert kept == [0, 1, 2, 3]
    found = screen_finding(findings)
    assert found.error is None
    assert set(found.scores) == {"client0", "client1", "client2", "client3"}
    assert all(rate == 0.0 for rate in found.scores.values())
    assert all(found.features[c]["reject_movability"] == 0.0 for c in found.features)


def test_chorus_stops_merging_a_suspended_client():
    base = harness.make_base()
    chorus = guard(k_sus=2, w_ej=5)
    malicious = adapter(base, 77, MARK)
    for t in (0, 1):
        new, kept, decision, findings = harness.server_round(chorus, t, base, [adapter(base, 1), malicious, adapter(base, 2)])
        assert decision.excluded == {"client1"}
    new, kept, decision, findings = harness.server_round(chorus, 2, base, [adapter(base, 1), adapter(base, 3), adapter(base, 2)])
    found = screen_finding(findings)
    assert found.features["client1"]["screened"] == 1.0
    assert found.features["client1"]["reject"] == 0.0
    assert found.features["client1"]["status"] == 1.0
    assert decision.excluded == {"client1"}
    assert kept == [0, 2]


def test_chorus_ejects_after_repeated_rejections_and_rechecks_later():
    base = harness.make_base()
    chorus = guard(k_sus=2, k_ej=3, w_ej=5, w_re=3)
    malicious = adapter(base, 77, MARK)
    for t in range(5):
        new, kept, decision, findings = harness.server_round(chorus, t, base, [adapter(base, 1), malicious, adapter(base, 2)])
        assert decision.excluded == {"client1"}
    assert screen_finding(findings).features["client1"]["status"] == 2.0
    for t in (5, 6):
        new, kept, decision, findings = harness.server_round(chorus, t, base, [adapter(base, 1), adapter(base, 3), adapter(base, 2)])
        assert screen_finding(findings).features["client1"]["screened"] == 0.0
        assert decision.excluded == {"client1"}
    new, kept, decision, findings = harness.server_round(chorus, 7, base, [adapter(base, 1), adapter(base, 3), adapter(base, 2)])
    found = screen_finding(findings)
    assert found.features["client1"]["screened"] == 1.0
    assert found.features["client1"]["reject"] == 0.0
    assert found.features["client1"]["status"] == 1.0
    assert decision.excluded == {"client1"}
    for t in range(8, 12):
        new, kept, decision, findings = harness.server_round(chorus, t, base, [adapter(base, 1), adapter(base, 3), adapter(base, 2)])
        assert decision.excluded == {"client1"}
    new, kept, decision, findings = harness.server_round(chorus, 12, base, [adapter(base, 1), adapter(base, 3), adapter(base, 2)])
    assert screen_finding(findings).features["client1"]["status"] == 0.0
    assert kept == [0, 1, 2]
