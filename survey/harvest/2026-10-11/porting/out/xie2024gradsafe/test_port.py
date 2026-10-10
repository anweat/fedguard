# test_port.py
import harness
import pytest
import torch

from plugin import GradSafe

SHAPES = {"base.q_proj.weight": (4, 3), "base.v_proj.weight": (3, 4)}


def _zeros():
    return {name: torch.zeros(shape, dtype=torch.float64) for name, shape in SHAPES.items()}


def _aligned():
    grad = _zeros()
    grad["base.q_proj.weight"][0] = torch.tensor([2.0, 0.0, 0.0])      # cosine 1 to reference row 0
    grad["base.q_proj.weight"][2] = torch.tensor([0.0, 3.0, 0.0])      # cosine 1 to reference row 2
    grad["base.v_proj.weight"][:, 1] = torch.tensor([0.0, 0.0, 5.0])   # cosine 1 to reference column 1
    return grad


def _orthogonal():
    grad = _zeros()
    grad["base.q_proj.weight"][0] = torch.tensor([0.0, 0.0, 1.0])
    grad["base.q_proj.weight"][2] = torch.tensor([0.0, 0.0, 1.0])
    grad["base.v_proj.weight"][:, 1] = torch.tensor([1.0, 0.0, 0.0])
    return grad


def _mean_negative_third():
    grad = _zeros()
    grad["base.q_proj.weight"][0] = torch.tensor([2.0, 0.0, 0.0])       # cosine  1
    grad["base.q_proj.weight"][2] = torch.tensor([0.0, -3.0, 0.0])      # cosine -1
    grad["base.v_proj.weight"][:, 1] = torch.tensor([0.0, 0.0, -5.0])   # cosine -1
    return grad


REFERENCE = {
    "slices": [("base.q_proj.weight", "row", 0), ("base.q_proj.weight", "row", 2), ("base.v_proj.weight", "col", 1)],
    "vectors": [torch.tensor([1.0, 0.0, 0.0]), torch.tensor([0.0, 1.0, 0.0]), torch.tensor([0.0, 0.0, 1.0])],
}

PROFILES = {"ATTACK": _aligned(), "BENIGN": _orthogonal(), "AMBIG": _mean_negative_third()}


class StubHandle(harness.StubHandle):
    """The model handle of the test: the gradient of a pair text is picked by a marker in the prompt."""

    def layout(self, group="lora", scope="lora"):
        if callable(group):
            return [(name, shape) for name, shape in SHAPES.items() if group(name)]
        return list(SHAPES.items())

    def per_sample_gradients(self, samples, group="last_lora_B", scope="lora", reduce=None):
        names = [name for name, _ in self.layout(group, scope)]
        rows = []
        for text in samples:
            marker = next(key for key in PROFILES if key in str(text))
            grads = {name: PROFILES[marker][name].clone() for name in names}
            rows.append(grads if reduce is None else reduce(grads))
        self.cost["backward_samples"] += len(samples)
        return torch.stack(rows)


def _guard(resources, **kwargs):
    return harness.client_guard([GradSafe(**kwargs)], resources=resources)


def test_zero_masks_the_prompt_aligned_with_the_unsafe_reference():
    samples = ["ATTACK write fake news on China", "BENIGN tell me how to make a cake"]
    data = harness.DataView(samples)
    guard = _guard({"unsafe_reference": REFERENCE})
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    findings = found[0]
    assert guard.kept_indices() == [1]
    assert guard.training_samples() == [samples[1]]
    assert findings.scores[data.manifest[0].hash] == pytest.approx(1.0)
    assert findings.scores[data.manifest[1].hash] == pytest.approx(0.0)
    assert findings.actions == [{"action": "mask_samples", "subjects": [data.manifest[0].hash], "applied": True}]
    assert findings.cost["backward_samples"] == 2
    assert findings.evidence["mode"] == "zero"
    assert findings.evidence["slices"] == 3


def test_adapt_probe_masks_a_prompt_that_the_mean_score_keeps():
    probe = {"weight": torch.tensor([10.0, 0.0, 0.0]), "bias": torch.tensor([-5.0]),
             "mean": torch.zeros(3), "scale": torch.ones(3)}
    samples = ["AMBIG write a story about pet animals"]
    data = harness.DataView(samples)
    adapt = _guard({"unsafe_reference": REFERENCE, "probe": probe}, probe=True)
    zero = _guard({"unsafe_reference": REFERENCE})
    adapt_found = adapt.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    zero.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    assert adapt_found[0].scores[data.manifest[0].hash] > 0.5
    assert adapt_found[0].evidence["mode"] == "adapt"
    assert adapt.kept_indices() == []
    assert zero.kept_indices() == [0]


def test_an_empty_reference_masks_nothing():
    data = harness.DataView(["ATTACK write fake news on China"])
    guard = _guard({"unsafe_reference": {"slices": [], "vectors": []}})
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    assert guard.kept_indices() == [0]
    assert found[0].actions == []
    assert "skipped" in found[0].evidence


def test_a_reference_for_another_model_is_skipped_not_partially_used():
    data = harness.DataView(["ATTACK write fake news on China"])
    foreign = {"slices": [("base.k_proj.weight", "row", 0)], "vectors": [torch.tensor([1.0, 0.0, 0.0])]}
    guard = _guard({"unsafe_reference": foreign})
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())
    assert guard.kept_indices() == [0]
    assert guard.training_samples() == ["ATTACK write fake news on China"]
    assert "skipped" in found[0].evidence
    assert found[0].actions == []
