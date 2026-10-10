# test_port.py -- mechanism tests for the BayBFed port; no model, no framework, synthetic LoRA states.
import torch

import harness
from plugin import BayBFed, round_filter


def _finding(findings):
    return [f for f in findings if f.module == "baybfed"][0]


def test_amplified_update_is_excluded():
    base = harness.make_base()
    benign = [harness.perturb(base, seed=i, scale=0.05) for i in range(7)]
    amplified = harness.perturb(base, seed=99, scale=1.0)
    new, kept, decision, findings = harness.server_round(
        harness.server_guard([BayBFed()]), 0, base, benign + [amplified])
    f = _finding(findings)
    assert decision.excluded == {"client7"}
    assert sorted(kept) == list(range(7))
    assert decision.weights == {f"client{i}": 1.0 for i in range(7)}
    assert f.scores["client7"] == max(f.scores.values())
    assert f.scores["client7"] > 4.0 * sorted(f.scores.values())[3]
    assert "mean" in decision.flags["client7"]
    for i in range(7):
        assert f.scores[f"client{i}"] < f.evidence["mean_max_jd"]


def test_single_upload_round_is_left_alone():
    base = harness.make_base()
    only = harness.perturb(base, seed=3)
    new, kept, decision, findings = harness.server_round(harness.server_guard([BayBFed()]), 0, base, [only])
    assert kept == [0]
    assert decision.excluded == set()
    assert decision.weights == {}
    assert _finding(findings).evidence["skipped"].startswith("needs")
    for name in base:
        assert torch.allclose(new[name], only[name])


def test_homogeneous_round_has_no_outlier_and_only_the_mean_rule_fires():
    base = harness.make_base()
    uploads = [harness.perturb(base, seed=i, scale=0.05) for i in range(8)]
    new, kept, decision, findings = harness.server_round(harness.server_guard([BayBFed()]), 0, base, uploads)
    f = _finding(findings)
    values = list(f.scores.values())
    assert max(values) < 3.0 * min(values)
    mean = sum(values) / len(values)
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    expected = {c for c, v in f.scores.items() if not v < mean or counts[v] > 1}
    assert decision.excluded == expected
    assert set(kept) == {i for i in range(8)} - {int(c[6:]) for c in expected}


def test_filter_keeps_only_unique_values_below_the_round_mean():
    keep, why = round_filter([0.1, 0.2, 0.2, 0.5])
    assert keep == [True, False, False, False]
    assert "repeated" in why[1]
    assert "mean" in why[3]
    keep, why = round_filter([1.0, 2.0, 3.0])
    assert keep == [True, False, False]
    keep, why = round_filter([2.0, 2.0])
    assert keep == [False, False]
