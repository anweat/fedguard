# test_port.py
import torch

import harness
from plugin import DeepSight

BASE = harness.make_base()
NOISE = 0.05


def _pattern(seed):
    p = harness.perturb(BASE, seed, 1.0)
    return {k: p[k] - BASE[k] for k in BASE}


def _state(direction, seed, scale=1.0):
    g = torch.Generator().manual_seed(seed)
    noise = {k: torch.randn(BASE[k].shape, generator=g, dtype=torch.float64) for k in BASE}
    return {k: BASE[k] + scale * (direction[k] + NOISE * noise[k]) for k in BASE}


def _norm(state):
    return float(torch.sqrt(sum(((state[k] - BASE[k]).double() ** 2).sum() for k in BASE)))


def _median_norm(states):
    return float(torch.quantile(torch.tensor([_norm(s) for s in states], dtype=torch.float64), 0.5))


def test_the_vote_removes_the_poisoned_cluster_and_clipping_bounds_the_rest():
    v, w = _pattern(11), _pattern(12)
    locals_ = [_state(v, 100 + i, 0.5 * 2 ** i) for i in range(4)] + [_state(w, 200 + i) for i in range(3)] + [_state(w, 250, 50.0)]
    labels = {**{f"client{i}": 0.0 for i in range(4)}, **{f"client{i}": 1.0 for i in range(4, 8)}}
    guard = harness.server_guard([DeepSight()], resources={"suspicious_labels": labels})
    new, kept, decision, findings = harness.server_round(guard, 0, BASE, locals_, sizes=[10, 10, 10, 10, 1000, 1000, 1000, 1000])

    assert decision.excluded == {"client4", "client5", "client6", "client7"}
    assert kept == [0, 1, 2, 3]

    receive = next(f for f in findings if f.features)
    cluster = {c: receive.features[c]["cluster"] for c in receive.features}
    assert cluster["client7"] == cluster["client4"]
    assert cluster["client0"] != cluster["client4"]

    bound = _median_norm(locals_)
    contributions = [guard.transformed.get(c, locals_[c]) for c in kept]
    for state in contributions:
        assert _norm(state) <= bound + 1e-9
    assert 2 in guard.transformed and 3 in guard.transformed
    assert _norm(new) <= bound + 1e-9
    equal = {k: sum(s[k] for s in contributions) / len(contributions) for k in BASE}
    for k in BASE:
        assert torch.allclose(new[k], equal[k], rtol=1e-9, atol=1e-9)


def test_a_lone_suspicious_label_in_one_cluster_changes_nothing():
    v = _pattern(21)
    locals_ = [_state(v, 300) for _ in range(6)]
    labels = {f"client{i}": 0.0 for i in range(6)}
    labels["client3"] = 1.0
    guard = harness.server_guard([DeepSight()], resources={"suspicious_labels": labels})
    new, kept, decision, findings = harness.server_round(guard, 0, BASE, locals_)

    assert decision.excluded == set()
    assert kept == list(range(6))
    assert guard.transformed == {}
    assert all(decision.weights[f"client{i}"] == 1.0 for i in range(6))
    equal = {k: sum(s[k] for s in locals_) / 6 for k in BASE}
    for k in BASE:
        assert torch.allclose(new[k], equal[k], rtol=1e-9, atol=1e-9)


def test_the_named_round_sends_each_cluster_its_own_model():
    v = _pattern(31)
    locals_ = [_state(v, 400) for _ in range(4)] + [_state(v, 400, -1.0) for _ in range(4)]
    labels = {f"client{i}": 0.0 for i in range(8)}
    guard = harness.server_guard([DeepSight(clusterwise_round=0)], resources={"suspicious_labels": labels})
    new, kept, decision, findings = harness.server_round(guard, 0, BASE, locals_)
    assert sorted(kept) == list(range(8))

    guard.begin_round(1, new, list(range(8)))
    a, b = guard.model_for(0), guard.model_for(4)
    for i in (1, 2, 3):
        assert all(torch.allclose(a[k], guard.model_for(i)[k]) for k in BASE)
    for i in (5, 6, 7):
        assert all(torch.allclose(b[k], guard.model_for(i)[k]) for k in BASE)
    assert not all(torch.allclose(a[k], b[k]) for k in BASE)
    mean_a = {k: sum(s[k] for s in locals_[:4]) / 4 for k in BASE}
    mean_b = {k: sum(s[k] for s in locals_[4:]) / 4 for k in BASE}
    for k in BASE:
        assert torch.allclose(a[k], mean_a[k], rtol=1e-9, atol=1e-9)
        assert torch.allclose(b[k], mean_b[k], rtol=1e-9, atol=1e-9)

    plain = harness.server_guard([DeepSight()], resources={"suspicious_labels": labels})
    harness.server_round(plain, 0, BASE, locals_)
    plain.begin_round(1, BASE, list(range(8)))
    for i in range(8):
        assert all(torch.allclose(plain.model_for(i)[k], BASE[k]) for k in BASE)


def test_an_empty_label_mapping_leaves_the_filter_off_and_the_clipping_on():
    v, w = _pattern(41), _pattern(42)
    locals_ = [_state(v, 500 + i) for i in range(3)] + [_state(w, 600 + i) for i in range(2)] + [_state(w, 700, 25.0)]
    guard = harness.server_guard([DeepSight()], resources={"suspicious_labels": {}})
    new, kept, decision, findings = harness.server_round(guard, 0, BASE, locals_)

    assert kept == list(range(6))
    assert decision.excluded == set()
    assert 5 in guard.transformed
    bound = _median_norm(locals_)
    assert _norm(guard.transformed[5]) <= bound + 1e-9
    assert _norm(new) <= bound + 1e-9


def test_a_round_with_fewer_than_three_clients_is_left_alone():
    v, w = _pattern(51), _pattern(52)
    first_round = [_state(v, 800 + i, 0.5 * 2 ** i) for i in range(4)] + [_state(w, 900 + i) for i in range(4)]
    labels = {**{f"client{i}": 1.0 for i in range(4)}, **{f"client{i}": 0.0 for i in range(4, 8)}}
    guard = harness.server_guard([DeepSight()], resources={"suspicious_labels": labels})
    _, _, decision0, _ = harness.server_round(guard, 0, BASE, first_round)
    assert decision0.excluded == {"client0", "client1", "client2", "client3"}

    two = [_state(v, 801), _state(w, 950, 40.0)]
    _, kept, decision, _ = harness.server_round(guard, 1, BASE, two)
    assert kept == [0, 1]
    assert decision.excluded == set()
    assert guard.transformed == {}
