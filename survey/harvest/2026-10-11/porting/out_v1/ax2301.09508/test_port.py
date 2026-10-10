# test_port.py
"""Mechanism tests for the BayBFed port on synthetic LoRA uploads: no model, no host framework.

They follow the two patterns the paper's filter is built on (Sect. 4.2.2): poisoned updates scoring
far above the benign ones, and poisoned updates scoring exactly alike."""
import harness
from plugin import BayBFed
from fedguard.ops import states

N = 8


def benign(base, t, i):
    """One benign round update: independent Gaussian noise on every factor."""
    return harness.perturb(base, 1000 * t + i, 0.1)


def amplified(base, local, factor):
    """The client's own update, pushed further in its own direction."""
    return states.add(base, states.delta(local, base), factor)


def test_a_benign_round_removes_nobody():
    base = harness.make_base()
    guard = harness.server_guard([BayBFed()])
    ups = [benign(base, 0, i) for i in range(N)]
    _, kept, decision, findings = harness.server_round(guard, 0, base, ups)
    assert kept == list(range(N))
    assert decision.excluded == set()
    assert len(findings[0].scores) == N and all(v > 0 for v in findings[0].scores.values())


def test_identical_poisoned_updates_are_removed_and_the_benign_clients_stay():
    base = harness.make_base()
    guard = harness.server_guard([BayBFed()])
    ups = [benign(base, 0, i) for i in range(N)]
    poison = amplified(base, ups[6], 5.0)
    ups[6] = poison
    ups[7] = poison
    _, kept, decision, findings = harness.server_round(guard, 0, base, ups)
    scores = findings[0].scores
    assert scores['client6'] == scores['client7']
    assert scores['client6'] >= findings[0].evidence['max_jd_avg']
    assert decision.excluded == {'client6', 'client7'}
    assert kept == [0, 1, 2, 3, 4, 5]


def test_a_unique_amplified_update_scores_highest_and_the_extracted_filter_keeps_it():
    base = harness.make_base()
    guard = harness.server_guard([BayBFed()])
    ups = [benign(base, 0, i) for i in range(N)]
    ups[7] = amplified(base, ups[7], 30.0)
    _, kept, decision, findings = harness.server_round(guard, 0, base, ups)
    scores = findings[0].scores
    others = [v for c, v in scores.items() if c != 'client7']
    assert scores['client7'] == max(scores.values())
    assert scores['client7'] > 10.0 * max(others)
    assert 7 in kept and decision.excluded == set()


def test_a_lone_client_is_kept_because_its_score_appears_once():
    base = harness.make_base()
    guard = harness.server_guard([BayBFed()])
    _, kept, decision, _ = harness.server_round(guard, 0, base, [benign(base, 0, 0)])
    assert kept == [0] and decision.excluded == set()


def test_cluster_state_persists_across_rounds_without_removing_benign_clients():
    state = harness.make_base()
    guard = harness.server_guard([BayBFed()])
    for t in range(3):
        ups = [benign(state, t, i) for i in range(N)]
        state, kept, decision, findings = harness.server_round(guard, t, state, ups)
        assert kept == list(range(N)) and decision.excluded == set()
    assert findings[0].evidence['clusters'] >= 1
