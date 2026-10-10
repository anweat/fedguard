"""Server-side published defenses, run through the single-process loop on synthetic LoRA uploads.

These check that each method does what its mechanism says on a case built for it. They are not
reproductions of the papers' results.
"""
import pytest
import torch

from conftest import make_base, perturb
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec
from fedguard.methods import FLAME, CoordinateMedian, FLDetector, FLTrust, FoolsGold, FreqFed, Krum, TrimmedMean
from fedguard.ops import states

SPEC = RunSpec("m", seed=3)
N = 8


def shared_direction(base, seed=99):
    return states.delta(perturb(base, seed, 1.0), base)


def honest(base, t, i, drift=None, scale=0.05):
    """A benign update: a common drift plus client noise."""
    local = perturb(base, 1000 * t + i, scale * 0.3)
    return states.add(local, drift, scale) if drift is not None else local


def run_round(guard, t, global_dict, locals_, sizes=None):
    sizes = sizes or [10] * len(locals_)
    guard.begin_round(t, global_dict, list(range(len(locals_))))
    for c, l in enumerate(locals_):
        guard.on_upload(c, l, {"num_examples": sizes[c]})
    kept, weights = guard.before_aggregate(list(range(len(locals_))), sizes)
    for c, l in guard.transformed.items():
        locals_[c] = l
    if kept:
        total = sum(weights[c] for c in kept)
        global_dict = {k: sum(locals_[c][k] * (weights[c] / total) for c in kept) for k in global_dict}
        global_dict = guard.after_aggregate(global_dict)
    decision = guard.last_decision
    guard.end_round()
    return global_dict, kept, decision


def make_guard(plugins, resources=None):
    return OpenFedLLMGuard(GuardRunner(plugins, SPEC, apply_actions=True, fail_policy="closed", resources=resources))


def dist(a, b):
    return states.norm(states.delta(a, b))


def scenario(factor=30.0, attackers=(7,)):
    base = make_base()
    drift = shared_direction(base)
    ups = [honest(base, 0, i, drift) for i in range(N)]
    for a in attackers:
        ups[a] = states.add(base, states.delta(ups[a], base), factor)
    clean = states.weighted_average([u for i, u in enumerate(ups) if i not in attackers])
    return base, ups, clean


@pytest.mark.parametrize("space", ["factor", "product"])
def test_krum_keeps_central_clients(space):
    base, ups, _ = scenario()
    _, kept, d = run_round(make_guard([Krum(f=1, m=5, space=space)]), 0, base, ups)
    assert 7 not in kept and len(kept) == 5 and "client7" in d.excluded
    _, kept, _ = run_round(make_guard([Krum(f=1, m=1)]), 0, base, ups)
    assert len(kept) == 1 and kept[0] != 7
    _, kept, _ = run_round(make_guard([Krum(f=6)]), 0, base, ups)          # n < f + 3: no decision
    assert len(kept) == N


@pytest.mark.parametrize("plugin", [CoordinateMedian(), TrimmedMean(beta=0.2)])
def test_coordinate_rules_replace_the_mean_and_resist_one_large_update(plugin):
    base, ups, clean = scenario()
    mean, _, _ = run_round(make_guard([]), 0, base, list(ups))
    robust_global, kept, _ = run_round(make_guard([plugin]), 0, base, list(ups))
    assert len(kept) == N                                                 # nobody is excluded; the rule itself changes
    assert dist(robust_global, clean) < 0.1 * dist(mean, clean)
    assert all(robust_global[k].shape == base[k].shape and robust_global[k].dtype == base[k].dtype for k in base)


def test_foolsgold_downweights_clients_that_keep_sending_the_same_direction():
    guard = make_guard([FoolsGold()])
    g = make_base()
    for t in range(4):
        ups = [honest(g, t, i) for i in range(N)]                         # honest clients: independent directions
        sybil = states.delta(perturb(g, 777, 0.05), g)                    # two sybils: one fixed direction every round
        ups[6], ups[7] = states.add(g, sybil), states.add(g, sybil, 1.01)
        g, kept, d = run_round(guard, t, g, ups)
    assert 6 not in kept and 7 not in kept
    assert all(d.weights.get(f"client{i}", 0) > 0.5 for i in range(6))


def test_fltrust_weights_by_agreement_with_the_server_update_and_equalizes_norms():
    base, ups, _ = scenario(factor=30.0)
    drift = shared_direction(base)
    ups[6] = states.add(base, drift, -0.05)                               # points against the server's direction
    root = lambda b: states.add(b, shared_direction(b), 0.05)             # noqa: E731  what training on root data gives
    guard = make_guard([FLTrust()], resources={"server_update": root})
    g, kept, d = run_round(guard, 0, base, ups)
    assert 6 not in kept and "client6" in d.excluded
    target = states.norm(states.delta(root(base), base))
    assert all(states.norm(states.delta(ups[c], base)) == pytest.approx(target, rel=1e-6) for c in kept)   # incl. the x30 one
    assert d.weights["client0"] > 0.5
    assert dist(g, root(base)) < 0.6 * target


def test_fltrust_with_no_trusted_client_keeps_the_previous_global_model():
    base = make_base()
    against = [states.add(base, shared_direction(base), -0.05) for _ in range(4)]
    guard = make_guard([FLTrust()], resources={"server_update": lambda b: states.add(b, shared_direction(b), 0.05)})
    g, kept, _ = run_round(guard, 0, base, against)
    assert kept == [] and all(torch.equal(g[k], base[k]) for k in base)


def test_flame_admits_the_majority_clips_to_the_median_and_adds_noise():
    base = make_base()
    drift, other = shared_direction(base, 99), shared_direction(base, 55)
    ups = [honest(base, 0, i, drift) for i in range(N)]
    ups[5] = states.add(base, states.delta(ups[5], base), 4.0)            # same direction, four times the size: clipped
    ups[6], ups[7] = states.add(base, other, 0.05), states.add(base, other, 0.06)   # another direction: not admitted
    flame = FLAME(noise_lambda=0.001)
    guard = make_guard([flame])
    g, kept, d = run_round(guard, 0, base, ups)
    assert sorted(kept) == [0, 1, 2, 3, 4, 5] and d.weights == {f"client{i}": 1.0 for i in range(6)}
    bound = guard.runner._state["flame"]["bound"]
    assert states.norm(states.delta(ups[5], base)) == pytest.approx(bound, rel=1e-6)
    plain = states.weighted_average([ups[i] for i in kept])
    noise = dist(g, plain)
    d_total = sum(v.numel() for v in base.values())
    assert 0.5 < noise / (0.001 * bound * d_total ** 0.5) < 1.5           # noise of the stated scale was added


def test_freqfed_keeps_the_majority_in_the_low_frequency_domain():
    base = make_base()
    drift = shared_direction(base, 99)
    smooth = {k: torch.ones_like(v) for k, v in base.items()}             # a constant shift: pure low frequency
    ups = [honest(base, 0, i, drift) for i in range(N)]
    ups[6], ups[7] = states.add(ups[6], smooth, 0.5), states.add(ups[7], smooth, 0.5)
    _, kept, d = run_round(make_guard([FreqFed()]), 0, base, ups)
    assert sorted(kept) == [0, 1, 2, 3, 4, 5] and d.excluded == {"client6", "client7"}


def test_fldetector_flags_clients_whose_updates_do_not_follow_the_trajectory():
    guard = make_guard([FLDetector(window=3)])
    g = make_base()
    target = perturb(g, 5, 1.0)                                           # everyone walks toward one optimum
    flagged_at = None
    for t in range(9):
        ups = []
        for i in range(N):
            step = states.delta(target, g)
            ups.append(states.add(states.add(g, step, 0.2), states.delta(perturb(g, 100 * t + i, 0.002), g)))
        for a in (6, 7):                                                  # two clients send unrelated updates each round
            ups[a] = perturb(g, 5000 + 31 * t + a, 0.3)
        g, kept, d = run_round(guard, t, g, ups)
        if flagged_at is None and d.excluded:
            flagged_at = t
    flagged = guard.runner._state["fldetector"]["flagged"]
    assert flagged == {"client6", "client7"} and flagged_at is not None and flagged_at >= 4


def test_a_round_without_uploads_is_skipped_not_crashed():
    """Every reply can fail in a real deployment; plugins that judge uploads then have nothing to do."""
    base = make_base()
    guard = make_guard([FLAME(), Krum(), CoordinateMedian(), FLDetector()])
    guard.begin_round(0, base, [0, 1, 2])
    kept, _ = guard.before_aggregate([0, 1, 2], [10, 10, 10])
    assert kept == []
    f = [x for x in guard.runner.findings if x.module == "flame"]
    assert f and all(x.evidence == {"skipped": "no uploads this round"} and x.error is None for x in f)
    guard.end_round()
