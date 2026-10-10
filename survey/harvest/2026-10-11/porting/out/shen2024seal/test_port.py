# test_port.py
"""Mechanism tests for the SEAL port: synthetic samples and a synthetic score table, no model.

SEAL's core (training the selector) is outside the library; what is inside is S3's decision. The tests
pin that decision: which announced samples the top-p% cut keeps, that p = 1 keeps everything, and that a
client with no scores is left alone instead of guessed at.
"""
import harness
import pytest

from plugin import SealTopPercent, top_percent_keep


def _hashes(texts):
    """The library's own sample identity: what DataView.manifest records."""
    return [r.hash for r in harness.DataView(list(texts)).manifest]


def _run(p, table, texts):
    guard = harness.client_guard([SealTopPercent(p=p)], resources={"selector_scores": table})
    found = guard.begin_round(0, harness.make_base(), data=harness.DataView(list(texts)))
    assert len(found) == 1
    return guard, found[0]


def test_keeps_the_top_p_percent_and_masks_the_rest():
    texts = [f"sample-{i}" for i in range(8)]
    hashes = _hashes(texts)
    table = dict(zip(hashes, [5.0, 4.0, 3.0, 2.0, 1.0, 0.0, -1.0, -2.0]))
    guard, f = _run(0.5, table, texts)                      # ceil(0.5 * 8) = 4 kept
    assert guard.kept_indices() == [0, 1, 2, 3]
    assert guard.training_hashes() == hashes[:4]
    assert [a["action"] for a in f.actions] == ["mask_samples"]
    assert f.actions[0]["subjects"] == sorted(hashes[4:])
    assert f.actions[0]["applied"] is True
    assert f.evidence["kept"] == 4 and f.evidence["masked"] == 4 and f.evidence["cut_score"] == 2.0
    assert f.features[hashes[0]] == {"kept": 1.0, "selector_score": 5.0}
    assert f.features[hashes[7]] == {"kept": 0.0, "selector_score": -2.0}


def test_p_one_keeps_every_scored_sample_and_proposes_nothing():
    texts = [f"t{i}" for i in range(5)]
    hashes = _hashes(texts)
    guard, f = _run(1.0, dict.fromkeys(hashes, 1.0), texts)
    assert guard.kept_indices() == [0, 1, 2, 3, 4]
    assert guard.training_hashes() == hashes
    assert f.actions == [] and f.evidence["masked"] == 0 and "cut_score" not in f.evidence


def test_no_scores_no_action():
    texts = [f"t{i}" for i in range(4)]
    guard, f = _run(0.5, {}, texts)
    assert guard.kept_indices() == [0, 1, 2, 3]
    assert f.actions == [] and f.evidence["scored"] == 0 and "skipped" in f.evidence


def test_samples_without_a_score_are_not_selected():
    texts = [f"t{i}" for i in range(4)]
    hashes = _hashes(texts)
    guard, f = _run(0.5, {hashes[0]: 3.0, hashes[1]: 2.0, hashes[2]: 1.0}, texts)   # 2 of 3 scored kept
    assert guard.kept_indices() == [0, 1]
    assert f.actions[0]["subjects"] == sorted([hashes[2], hashes[3]])
    assert f.evidence["unscored"] == 1 and f.evidence["scored"] == 3 and f.evidence["cut_score"] == 2.0


def test_top_percent_keep_rounds_up_and_keeps_at_least_one():
    assert top_percent_keep([1.0, 5.0, 3.0, 2.0, 4.0], 0.5) == [1, 2, 4]      # ceil(2.5) = 3
    assert top_percent_keep([1.0, 1.0, 1.0], 1.0 / 3.0) == [0]               # ties: earlier index first
    assert top_percent_keep([2.0, 2.0], 0.1) == [0]                          # at least one
    assert top_percent_keep([], 0.5) == []


def test_p_outside_the_unit_interval_is_refused():
    for bad in (0.0, -0.5, 1.5):
        with pytest.raises(ValueError):
            SealTopPercent(p=bad)
