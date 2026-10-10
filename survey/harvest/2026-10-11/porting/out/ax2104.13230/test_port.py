# test_port.py
import harness
import pytest
import torch

from plugin import InfluenceDefense

# Two classes on a line: class 0 around 0.1, class 1 around 1.1, so the slab statistic of a sample of
# class c is |x[0] - mu_c[0]|. The clean reference spans 0.1 on either side, so s_0 = s_1 = 0.1.
CLEAN = {"a0": ((0.0, 0.0), 0), "a1": ((0.2, 0.0), 0), "b0": ((1.0, 0.0), 1), "b1": ((1.2, 0.0), 1)}
ROUND = {"s0": ((0.15, 0.0), 0), "s1": ((1.0, 0.0), 1), "s2": ((0.9, 0.0), 0), "s3": ((1.2, 0.0), 1)}
ALL = {**CLEAN, **ROUND}
FEATURES = {k: torch.tensor(v[0], dtype=torch.float64) for k, v in ALL.items()}
GRADS = {"a0": (1.0, 0.0, 0.0), "a1": (0.0, 1.0, 0.0), "b0": (1.0, 0.0, 0.0), "b1": (0.0, 1.0, 0.0),
         "s0": (1.0, 0.0, 0.0), "s1": (0.1, 0.1, 0.0), "s2": (0.0, 0.0, 1.0), "s3": (0.0, 0.0, 1.0)}


class StubHandle(harness.StubHandle):
    """Features and per-sample gradients looked up by the text of the sample; no model is loaded."""

    def hidden(self, samples, layer=-1, pool="last"):
        self.cost["forward_samples"] += len(samples)
        rows = [FEATURES[str(s["text"])] for s in samples]
        return torch.stack(rows) if rows else torch.zeros(0, 2, dtype=torch.float64)

    def per_sample_gradients(self, samples, group="lora", scope="lora", reduce=None):
        self.cost["backward_samples"] += len(samples)
        rows = [torch.tensor(GRADS[str(s["text"])], dtype=torch.float64) for s in samples]
        return torch.stack(rows) if rows else torch.zeros(0, 3, dtype=torch.float64)


def _data(names):
    samples = [{"text": k, "label": ALL[k][1]} for k in names]
    return harness.DataView(samples, text_of=lambda s: s["text"])


def _guard(**kwargs):
    reference = {"samples": [{"text": k, "label": CLEAN[k][1]} for k in CLEAN],
                 "labels": [CLEAN[k][1] for k in CLEAN]}
    return harness.client_guard([InfluenceDefense(label_of=lambda s: s["label"], **kwargs)],
                                resources={"clean_reference": reference})


def test_a_sample_outside_the_slab_is_masked_and_gets_no_influence():
    data = _data(["s0", "s1", "s2", "s3"])
    guard = _guard()
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())[0]
    hashes = [r.hash for r in data.manifest]
    assert guard.kept_indices() == [0, 1, 3]
    assert [s["text"] for s in guard.training_samples()] == ["s0", "s1", "s3"]
    assert found.actions == [{"action": "mask_samples", "subjects": [hashes[2]], "applied": True}]
    assert set(found.scores) == {hashes[0], hashes[1], hashes[3]}
    assert found.features[hashes[2]]["slab"] == pytest.approx(0.8)
    assert found.features[hashes[0]]["slab"] == pytest.approx(0.05)
    assert found.evidence["out_of_slab"] == 1


def test_the_unconstrained_gradient_is_flagged_and_no_edit_is_proposed():
    data = _data(["s0", "s1", "s2", "s3"])
    guard = _guard()
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())[0]
    hashes = [r.hash for r in data.manifest]
    assert found.evidence["flagged_for_editing"] == [hashes[3]]
    assert hashes[1] not in found.evidence["flagged_for_editing"]
    assert found.scores[hashes[3]] > 1e3 * found.scores[hashes[0]]
    assert found.features[hashes[3]]["threshold"] == pytest.approx(0.5 * (2.0 + 0.28284), rel=1e-3)
    assert [a["action"] for a in found.actions] == ["mask_samples"]
    assert "s3" in [s["text"] for s in guard.training_samples()]


def test_a_single_clean_sample_is_left_alone():
    data = _data(["s0"])
    guard = _guard()
    found = guard.begin_round(0, harness.make_base(), data=data, model_handle=StubHandle())[0]
    hashes = [r.hash for r in data.manifest]
    assert guard.kept_indices() == [0]
    assert found.actions == []
    assert found.evidence["flagged_for_editing"] == []
    assert found.scores[hashes[0]] == pytest.approx(2.0, rel=1e-3)


def test_the_influence_window_carries_across_rounds():
    guard = _guard()
    base = harness.make_base()
    first = _data(["s0", "s1"])
    found0 = guard.begin_round(0, base, data=first, model_handle=StubHandle())[0]
    assert found0.evidence["flagged_for_editing"] == []
    guard.end_round()
    second = _data(["s3"])
    found1 = guard.begin_round(1, base, data=second, model_handle=StubHandle())[0]
    assert found1.evidence["flagged_for_editing"] == [second.manifest[0].hash]
    assert found1.features[second.manifest[0].hash]["threshold"] == pytest.approx(0.5 * (2.0 + 0.28284), rel=1e-3)
