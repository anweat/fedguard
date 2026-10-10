# test_port.py
import harness
import torch

from fedguard.core.types import Stage
from plugin import EmbTrackerTracing

TARGET = ", and click the link for more information"
BENIGN = "I cannot help with that."

TRIGGERS = {
    "client0": {"trigger": "zzqmark", "target": TARGET},
    "client1": {"trigger": "vvpmark", "target": TARGET},
    "client2": {"trigger": "wwtmark", "target": TARGET},
}
PROMPTS = ["the cat sat on the mat", "a quick brown fox jumps over the lazy dog", "hello world"]


class LeakHandle(harness.StubHandle):
    """The black-box model the plugin queries: it answers with TARGET when the prompt carries the trigger
    of a client named in `fires` (at most `quota` answers per call), predicts the label "yes" the same way
    through `logprob`, and records the LoRA states it was loaded with through `lora`."""

    def __init__(self, fires, quota=None):
        super().__init__()
        self.fires, self.quota, self.loaded = dict(fires), quota, []

    def _live(self, prompt, used):
        return any(t in prompt for t in self.fires.values()) and (self.quota is None or used < self.quota)

    def generate(self, prompts, max_new_tokens=32):
        outs, used = [], 0
        for p in prompts:
            live = self._live(p, used)
            used += int(live)
            outs.append(TARGET if live else BENIGN)
        self.cost["forward_samples"] += len(prompts)
        return outs

    def logprob(self, prompts, targets):
        self.cost["forward_samples"] += len(prompts)
        return [(0.5 if self._live(p, 0) == (t.strip() == "yes") else -0.5) for p, t in zip(prompts, targets)]

    def lora(self, state):
        return _Loaded(self, state)


class _Loaded:
    """What `with handle.lora(state):` needs; it records the state so the test can see it was loaded."""

    def __init__(self, handle, state):
        self.handle, self.state = handle, state

    def __enter__(self):
        self.handle.loaded.append(self.state)
        return self.handle

    def __exit__(self, *exc):
        return False


def one_round(handle, triggers=None, prompts=None, **kwargs):
    plugin = EmbTrackerTracing(**kwargs)
    guard = harness.server_guard([plugin], resources={"watermark_triggers": TRIGGERS if triggers is None else triggers,
                                                      "verification_prompts": PROMPTS if prompts is None else prompts},
                                 probe=handle)
    base = harness.make_base()
    _, _, _, findings = harness.server_round(guard, 0, base, [harness.perturb(base, i) for i in (1, 2, 3)])
    return next(f for f in findings if f.module == plugin.name)


def test_runs_after_aggregation_and_counts_its_queries():
    found = one_round(LeakHandle({"client2": "wwtmark"}))
    assert found.stage == Stage.SERVER_POST_AGGREGATE
    assert found.cost == {"forward_samples": 9}          # 3 candidate clients x 3 prompts


def test_attributes_the_only_client_whose_watermark_is_live():
    suspicious = {"layers.0.q_proj.lora_A.weight": torch.zeros(4, 16, dtype=torch.float64)}
    handle = LeakHandle({"client2": "wwtmark"})
    found = one_round(handle, suspicious=suspicious)
    assert found.evidence["attributed"] == "client2"
    assert found.scores == {"client0": 0.0, "client1": 0.0, "client2": 1.0}
    assert found.features["client2"]["verification_interval"] == 1.0
    assert found.evidence["loaded_lora"] is True
    assert handle.loaded and handle.loaded[0] is suspicious


def test_no_live_watermark_is_not_attributed():
    found = one_round(LeakHandle({}))
    assert found.evidence["attributed"] is None
    assert set(found.scores.values()) == {0.0}


def test_two_live_watermarks_are_not_attributed_to_either():
    found = one_round(LeakHandle({"client0": "zzqmark", "client1": "vvpmark"}))
    assert found.evidence["attributed"] is None
    assert found.scores["client0"] == 1.0 and found.scores["client1"] == 1.0
    assert found.scores["client2"] == 0.0


def test_a_verification_rate_below_gamma_is_not_attributed():
    found = one_round(LeakHandle({"client1": "vvpmark"}, quota=2))
    assert found.scores["client1"] == 2 / 3              # 2 of 3 prompts answered
    assert found.evidence["attributed"] is None
    found = one_round(LeakHandle({"client1": "vvpmark"}, quota=2), gamma=0.6)
    assert found.evidence["attributed"] == "client1"


def test_classification_form_uses_the_label_with_the_highest_logprob():
    triggers = {c: {"trigger": s["trigger"], "labels": ["no", "yes"], "target": "yes"} for c, s in TRIGGERS.items()}
    found = one_round(LeakHandle({"client1": "vvpmark"}), triggers=triggers)
    assert found.evidence["attributed"] == "client1"
    assert found.scores["client1"] == 1.0 and found.scores["client0"] == 0.0


def test_an_empty_prompt_pool_is_reported_not_guessed():
    found = one_round(LeakHandle({"client1": "vvpmark"}), prompts=[])
    assert found.scores == {} and "skipped" in found.evidence
