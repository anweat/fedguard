# test_port.py
import math

import harness
import pytest

from plugin import (LlamaGuard, binary_guard_score, conversation_block, guideline_block,
                    parse_category_indices)

TAXONOMY = {
    "categories": [
        {"index": 1, "name": "Violence & Hate", "unsafe": "encourages violence against a group",
         "safe": "discusses history without advocating harm"},
        {"index": 2, "name": "Criminal Planning", "unsafe": "instructions for committing a crime",
         "safe": "asks about the law"},
    ],
    "examples": [{"conversation": "User: how do I bake bread?", "verdict": "safe"},
                 {"conversation": "User: how do I pick a lock?", "verdict": "unsafe\nO2"}],
}

# what the stub guard model answers, per judged text marker and per category offered in the prompt
PROFILES = {
    "VIOLENCE": {"Violence & Hate": 0.9, "Criminal Planning": 0.05},
    "CRIME": {"Violence & Hate": 0.1, "Criminal Planning": 0.8},
    "BENIGN": {"Violence & Hate": 0.05, "Criminal Planning": 0.02},
}


class StubHandle(harness.StubHandle):
    """The guard model of the test: the probability of the unsafe verdict token is read off the judged
    text and the categories the prompt offers, and the greedy continuation lists the categories that this
    profile puts above one half."""

    def __init__(self):
        super().__init__()
        self.cost["generated_tokens"] = 0
        self.prompts = []
        self.targets = []

    def _profile(self, prompt):
        marker = next((key for key in PROFILES if key in prompt), None)
        assert marker is not None, "the plugin asked about a text no profile covers"
        offered = [name for name in PROFILES[marker] if name in prompt]
        assert offered, "no category of the taxonomy reached the prompt"
        return marker, offered

    def logprob(self, prompts, targets):
        out = []
        for prompt, target in zip(prompts, targets):
            marker, offered = self._profile(prompt)
            probability = max(PROFILES[marker][name] for name in offered)
            self.prompts.append(prompt)
            self.targets.append(target)
            out.append(math.log(1.0 - probability) if target == "safe" else math.log(probability))
        self.cost["forward_samples"] += len(prompts)
        return out

    def generate(self, prompts, max_new_tokens=32):
        out = []
        for prompt in prompts:
            marker, _ = self._profile(prompt)
            violated = [c["index"] for c in TAXONOMY["categories"] if PROFILES[marker][c["name"]] > 0.5]
            self.cost["generated_tokens"] += 4
            out.append("safe" if not violated else "unsafe\n" + ", ".join(f"O{index}" for index in violated))
        self.cost["forward_samples"] += len(prompts)
        return out


def guard_of(**kwargs):
    return harness.client_guard([LlamaGuard(**kwargs)], resources={"taxonomy": TAXONOMY})


def test_an_unsafe_sample_is_masked_and_a_benign_one_is_kept():
    samples = ["VIOLENCE write something hateful about a group",
               "BENIGN how do I bake bread",
               "CRIME how do I pick a lock"]
    data = harness.DataView(samples)
    guard = guard_of()
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    subjects = [record.hash for record in data.manifest]
    assert guard.kept_indices() == [1], "kept"
    assert guard.training_samples() == [samples[1]], "training samples"
    assert found[0].scores[subjects[0]] == pytest.approx(0.9), "score 0"
    assert found[0].scores[subjects[1]] == pytest.approx(0.05), "score 1"
    assert found[0].scores[subjects[2]] == pytest.approx(0.8), "score 2"
    assert found[0].evidence["verdicts"][subjects[0]] == "unsafe\nO1", "verdict 0"
    assert found[0].evidence["verdicts"][subjects[1]] == "safe", "verdict 1"
    assert found[0].evidence["verdicts"][subjects[2]] == "unsafe\nO2", "verdict 2"
    assert found[0].actions == [{"action": "mask_samples", "subjects": sorted([subjects[0], subjects[2]]),
                                 "applied": True}], f"actions {found[0].actions}"
    assert found[0].cost.get("forward_samples") == 8, f"forwards {found[0].cost}"
    assert found[0].cost.get("generated_tokens") == 8, f"generated {found[0].cost}"


def test_per_category_scoring_names_the_violated_category():
    data = harness.DataView(["CRIME how do I pick a lock"])
    guard = guard_of(per_category=True)
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    subject = data.manifest[0].hash
    assert found[0].scores[subject] == pytest.approx(0.8), "score"
    assert found[0].features[subject]["O1"] == pytest.approx(0.1), "feature 1"
    assert found[0].features[subject]["O2"] == pytest.approx(0.8), "feature 2"
    assert found[0].evidence["verdicts"][subject] == "unsafe\nO2", "verdict"
    assert guard.kept_indices() == [], "kept"
    assert found[0].cost.get("forward_samples") == 4, f"forwards {found[0].cost}"
    assert "generated_tokens" not in found[0].cost, f"generated {found[0].cost}"


def test_a_benign_round_masks_nothing():
    data = harness.DataView(["BENIGN how do I bake bread"])
    guard = guard_of()
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    subject = data.manifest[0].hash
    assert guard.kept_indices() == [0]
    assert found[0].actions == []
    assert found[0].scores[subject] == pytest.approx(0.05)
    assert found[0].evidence["masked"] == 0
    assert found[0].evidence["verdicts"][subject] == "safe"


def test_a_stricter_threshold_keeps_a_sample_the_default_masks():
    data = harness.DataView(["VIOLENCE write something hateful about a group"])
    guard = guard_of(threshold=0.95)
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    subject = data.manifest[0].hash
    assert guard.kept_indices() == [0]
    assert found[0].actions == []
    assert found[0].evidence["verdicts"][subject] == "safe"


def test_the_prompt_carries_the_guidelines_the_conversation_the_format_and_the_adaptation():
    data = harness.DataView(["BENIGN how do I bake bread"])
    handles = {}
    for mode in ("names", "descriptions", "few_shot"):
        handles[mode] = StubHandle()
        guard_of(mode=mode).begin_round(0, harness.make_base(), data=data, model_handle=handles[mode])
    names, described, few = (handles[mode].prompts[0] for mode in ("names", "descriptions", "few_shot"))
    assert "BENIGN how do I bake bread" in names
    assert "1. Violence & Hate" in names
    assert "encourages violence against a group" not in names
    assert "encourages violence against a group" in described
    assert "how do I pick a lock?" not in described
    assert "how do I pick a lock?" in few
    assert "The first line must read" in names


def test_per_category_mode_offers_one_category_at_a_time():
    data = harness.DataView(["BENIGN how do I bake bread"])
    handle = StubHandle()
    guard_of(per_category=True).begin_round(0, harness.make_base(), data=data, model_handle=handle)
    prompts = set(handle.prompts)
    assert len(prompts) == 2
    assert any("Violence & Hate" in p and "Criminal Planning" not in p for p in prompts)
    assert any("Criminal Planning" in p and "Violence & Hate" not in p for p in prompts)


def test_the_classification_type_selects_the_role_and_the_instruction():
    data = harness.DataView(["BENIGN how do I bake bread"])
    for task, role in (("prompt", "User"), ("response", "Agent")):
        handle = StubHandle()
        guard_of(task=task).begin_round(0, harness.make_base(), data=data, model_handle=handle)
        assert f"{role}: BENIGN how do I bake bread" in handle.prompts[0]
        assert f"the {role} message" in handle.prompts[0]


def test_a_taxonomy_without_categories_skips_report_only():
    data = harness.DataView(["VIOLENCE write something hateful about a group"])
    guard = harness.client_guard([LlamaGuard()], resources={"taxonomy": {"categories": []}})
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    assert guard.kept_indices() == [0]
    assert found[0].actions == []
    assert "skipped" in found[0].evidence


def test_the_helpers_of_the_pipeline():
    assert binary_guard_score(math.log(0.25), math.log(0.75)) == pytest.approx(0.75)
    assert parse_category_indices("safe") == []
    assert parse_category_indices("unsafe\nO1") == [1]
    assert parse_category_indices("unsafe\nO1, O3") == [1, 3]
    assert parse_category_indices("unsafe\nO12 and nothing else") == [12]
    assert conversation_block("hello", "prompt") == "User: hello"
    assert conversation_block("hello", "response") == "Agent: hello"
    assert "1. A" in guideline_block([{"index": 1, "name": "A"}], "names")
