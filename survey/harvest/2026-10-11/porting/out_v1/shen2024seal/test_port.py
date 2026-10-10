# test_port.py
"""SEAL's selection step on synthetic scores: no model, no tokenizer, no training.

The plugin only ranks the samples a client announced for this round by the score the trained selector
resource gives each of them, and proposes to mask everything below the top p%. The assertions are about
that mechanism: which samples go, which stay, and what happens to a sample the selector cannot rank.
"""
import pytest

import harness
from plugin import SealTopPercent, top_percent_keep

SAMPLES = [f"sample {i}" for i in range(10)]
# What a trained SEAL selector could give: the two lowest scores are the ones under the p = 0.8 cut.
SCORES = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05]


def announced(scores=SCORES):
    data = harness.DataView(list(SAMPLES), text_of=str)
    return data, {record.hash: score for record, score in zip(data.manifest, scores)}


def test_keeps_the_top_p_percent_and_masks_the_rest():
    data, table = announced()
    guard = harness.client_guard([SealTopPercent(p=0.8)], resources={"selector_scores": table})
    found = guard.begin_round(0, harness.make_base(), data=data)
    assert guard.kept_indices() == [0, 1, 2, 3, 4, 5, 6, 7]
    assert len(guard.training_samples()) == 8
    action, = found[0].actions
    assert action["action"] == "mask_samples" and action["applied"] is True
    assert set(action["subjects"]) == {data.manifest[8].hash, data.manifest[9].hash}
    assert found[0].evidence["kept"] == 8 and found[0].evidence["masked"] == 2
    assert found[0].features[data.manifest[0].hash] == {"selector_score": 0.9}


def test_p_one_keeps_every_sample_and_proposes_nothing():
    data, table = announced()
    guard = harness.client_guard([SealTopPercent(p=1.0)], resources={"selector_scores": table})
    found = guard.begin_round(0, harness.make_base(), data=data)
    assert guard.kept_indices() == list(range(10))
    assert found[0].actions == []


def test_the_cut_follows_the_scores_not_the_sample_order():
    data, table = announced(list(reversed(SCORES)))     # now the first samples are the weak ones
    guard = harness.client_guard([SealTopPercent(p=0.8)], resources={"selector_scores": table})
    guard.begin_round(0, harness.make_base(), data=data)
    assert guard.kept_indices() == [2, 3, 4, 5, 6, 7, 8, 9]


def test_samples_the_selector_cannot_rank_are_dropped_and_counted():
    data, table = announced()
    table.pop(data.manifest[0].hash)                    # the selector never saw this sample
    guard = harness.client_guard([SealTopPercent(p=0.8)], resources={"selector_scores": table})
    found = guard.begin_round(0, harness.make_base(), data=data)
    assert guard.kept_indices() == [1, 2, 3, 4, 5, 6, 7, 8]
    assert found[0].evidence["missing_scores"] == 1
    assert data.manifest[0].hash not in found[0].features


def test_top_percent_keep_rounding_and_ties():
    assert top_percent_keep([1.0, 2.0, 3.0], 0.5) == [1, 2]     # ceil(1.5) = 2
    assert top_percent_keep([1.0, 1.0, 1.0], 0.5) == [0, 1]     # ties keep the announced order
    assert top_percent_keep([1.0, 2.0], 0.1) == [1]             # at least one sample survives
    assert top_percent_keep([], 0.8) == []


def test_the_selector_resource_is_required():
    with pytest.raises(ValueError):                     # ContractError is a ValueError
        harness.client_guard([SealTopPercent(p=0.8)], resources={})
