"""Second batch of published defenses: each on a synthetic case built for its mechanism.
Not reproductions of the papers' results."""
import math

import torch

from conftest import make_base, perturb
from fedguard.client import ClientGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec
from fedguard.methods import CRFL, MCD, AlternatingNoisyLoRA, LisaProximal, LoMar, MudHoG, Onion, SafetyMix
from fedguard.ops import density, sequential, states, text, update
from fedguard.views.client import DataView, GradientView
from test_methods_server import N, dist, honest, make_guard, run_round, shared_direction

SPEC = RunSpec("m", seed=3)


def test_new_operators():
    g = torch.Generator().manual_seed(0)
    X = torch.randn(12, 5, generator=g, dtype=torch.float64) * 0.1
    X[11] += 5.0
    F = density.knn_density_ratio(X, 4)
    assert F[11] < 0.1 and F[:11].min() > 0.3
    x = torch.zeros(3, 9)
    x[:, 4] = 16.0
    y = sequential.lowpass_1d(x, dim=1)
    assert y.shape == x.shape and torch.allclose(y[0], torch.tensor([0., 0, 1, 4, 6, 4, 1, 0, 0]))
    assert torch.allclose(sequential.lowpass_1d(x.T, dim=0), y.T)
    assert torch.allclose(sequential.lowpass_1d(torch.ones(4, 7), dim=1), torch.ones(4, 7))    # symmetric padding keeps a constant
    assert text.leave_one_out(["a", "b", "c"]) == ["b c", "a c", "a b"]
    assert text.outlier_words(10.0, [9.0, 10.5, 3.0], bar=2.0) == [2]
    s, f = update.clip_state_norm({"a": torch.full((4,), 3.0)}, 3.0)
    assert math.isclose(states.norm(s), 3.0, rel_tol=1e-6) and math.isclose(f, 0.5)
    noisy = update.clip_and_noise({"a": torch.full((4,), 3.0)}, 3.0, 0.0, torch.Generator())
    assert torch.allclose(noisy["a"], torch.full((4,), 1.5))


def test_mud_hog_confirms_a_sign_flipper_after_two_rounds():
    base = make_base()
    drift = shared_direction(base)
    guard = make_guard([MudHoG(warmup=1)])
    g, kept_by_round = base, []
    for t in range(4):
        ups = [honest(g, t, i, drift) for i in range(N)]
        ups[7] = states.add(g, states.delta(ups[7], g), -3.0)
        g, kept, d = run_round(guard, t, g, ups)
        kept_by_round.append(kept)
    assert 7 in kept_by_round[0] and 7 in kept_by_round[1]          # warm-up, then first flag: not yet confirmed
    assert 7 not in kept_by_round[2] and 7 not in kept_by_round[3]
    assert d.flags["client7"].startswith("attacker")


def test_lomar_scores_the_isolated_update_lowest():
    base = make_base()
    drift = shared_direction(base)
    ups = [honest(base, 0, i, drift) for i in range(N)]
    ups[7] = states.add(base, states.delta(ups[7], base), 30.0)
    guard = make_guard([LoMar(threshold=0.2)])
    _, kept, d = run_round(guard, 0, base, ups)
    assert 7 not in kept and d.excluded == {"client7"}
    _, kept, _ = run_round(make_guard([LoMar(threshold=1e9)]), 0, base, ups)      # everyone below: nobody excluded
    assert len(kept) == N


def test_mcd_removes_the_client_whose_models_wander():
    base = make_base()
    drift = shared_direction(base)
    other = shared_direction(base, seed=5)
    guard = make_guard([MCD(period=4, delta=2.9)])     # at delta = 2 two honest clients of this case go too
    g = base
    for t in range(5):
        ups = [honest(g, t, i, drift) for i in range(N)]
        ups[7] = states.add(ups[7], other, 2.0 * (-1) ** t)          # a different place every round
        g, kept, d = run_round(guard, t, g, ups)
        assert (7 in kept) == (t < 3)                                 # detection at the end of the period, then for good
    assert d.excluded == {"client7"}


def test_crfl_clips_then_perturbs_the_global_model():
    base = make_base()
    ups = [perturb(base, i, 0.5) for i in range(N)]
    plain, _, _ = run_round(make_guard([]), 0, base, list(ups))
    clipped, _, _ = run_round(make_guard([CRFL(rho0=0.5, rho_slope=0.0, sigma=0.0)]), 0, base, list(ups))
    assert states.norm(plain) > 0.5 and math.isclose(states.norm(clipped), 0.5, rel_tol=1e-5)
    noisy, _, _ = run_round(make_guard([CRFL(rho0=0.5, rho_slope=0.0, sigma=0.01)]), 0, base, list(ups))
    d = states.flatten(states.delta(noisy, clipped))
    assert 0.005 < float(d.std()) < 0.02
    last, _, _ = run_round(make_guard([CRFL(rho0=0.5, rho_slope=0.0, sigma=0.01, last_round=0)]), 0, base, list(ups))
    assert dist(last, clipped) < 1e-6


class WordModel:
    """A language model that finds exactly one word surprising."""

    def __init__(self):
        self.cost = {"forward_samples": 0}

    def logprob(self, prompts, targets):
        self.cost["forward_samples"] += len(targets)
        return [-(1.0 + 5.0 * t.split().count("cf")) for t in targets]


def client(plugin, samples, apply=True, resources=None, **kw):
    guard = ClientGuard("c0", GuardRunner([plugin], SPEC, side="client", apply_actions=apply, fail_policy="closed", resources=resources))
    [f] = guard.begin_round(0, make_base(), data=DataView(samples, text_of=lambda s: s["instruction"] + s["response"]), **kw)
    return f, guard


def test_onion_deletes_the_word_that_raises_perplexity():
    samples = [{"instruction": "tell me cf about rivers", "response": "ok"}, {"instruction": "name three colours", "response": "ok"},
               {"instruction": "cf", "response": "ok"}]
    f, guard = client(Onion(), samples, model_handle=WordModel())
    trained = guard.training_samples()
    assert [s["instruction"] for s in trained] == ["tell me about rivers", "name three colours", "cf"]
    assert f.evidence == {"examined_words": 8, "rewritten": 1} and f.cost == {"forward_samples": 6 + 4}
    f, guard = client(Onion(max_words=2), samples, model_handle=WordModel())       # the trigger is past the examined words
    assert guard.training_samples()[0]["instruction"] == "tell me cf about rivers"
    f, guard = client(Onion(), samples, apply=False, model_handle=WordModel())
    assert guard.training_samples() == samples and f.actions[0]["applied"] is False


def test_safety_mix_adds_samples_with_a_stable_secret_prefix():
    data = [{"instruction": "hi", "response": "hello"}]
    safety = [{"instruction": f"harmful {i}", "response": "I cannot help with that."} for i in range(20)]
    f, guard = client(SafetyMix(n=3), data, resources={"safety_samples": safety})
    assert guard.training_samples() == data + safety[:3]
    f, guard = client(SafetyMix(n=2, secret_words=5, secret_seed=7), data, resources={"safety_samples": safety})
    added = guard.training_samples()[1:]
    secret = SafetyMix(secret_words=5, secret_seed=7).secret()
    assert len(secret.split()) == 5 and all(s["instruction"] == f"{secret} harmful {i}" for i, s in enumerate(added))
    assert SafetyMix(secret_words=5, secret_seed=8).secret() != secret


def lora_params():
    g = torch.Generator().manual_seed(1)
    A = torch.nn.Parameter(torch.randn(2, 12, generator=g))
    B = torch.nn.Parameter(torch.randn(6, 2, generator=g))
    for p in (A, B):
        p.grad = torch.randn(p.shape, generator=g)
    return [("m.lora_A.default.weight", A), ("m.lora_B.default.weight", B)]


def step(plugin, guard_holder, params):
    if "g" not in guard_holder:
        guard_holder["g"] = ClientGuard("c0", GuardRunner([plugin], SPEC, side="client", apply_actions=True, fail_policy="closed"))
        guard_holder["g"].begin_round(0, make_base())
    guard_holder["g"].on_gradients(len(guard_holder.setdefault("n", [])), params)
    guard_holder["n"].append(1)


def test_la_lora_alternates_factors_and_bounds_the_active_gradient():
    params, h = lora_params(), {}
    a0, b0 = params[0][1].grad.clone(), params[1][1].grad.clone()
    step(AlternatingNoisyLoRA(sigma=0.0, clip=0.5), h, params)           # step 1: B active
    assert params[0][1].grad.abs().sum() == 0
    expected = sequential.lowpass_1d(b0 * (0.5 / b0.norm()), dim=0)
    assert torch.allclose(params[1][1].grad, expected, atol=1e-6)
    params[0][1].grad, params[1][1].grad = a0.clone(), b0.clone()
    step(AlternatingNoisyLoRA(sigma=0.0, clip=0.5), h, params)           # step 2: A active
    assert params[1][1].grad.abs().sum() == 0 and params[0][1].grad.abs().sum() > 0
    params, h = lora_params(), {}
    step(AlternatingNoisyLoRA(sigma=4.0, clip=1.0, batch_size=1, taps=3), h, params)
    assert params[1][1].grad.norm() > 2.0                                # noise of scale sigma * C dominates


def test_lisa_proximal_adds_rho_times_the_drift():
    params, h = lora_params(), {}
    g0 = [p.grad.clone() for _, p in params]
    plugin = LisaProximal(rho=2.0)
    step(plugin, h, params)                                               # first step: reference taken, no drift yet
    assert all(torch.allclose(p.grad, g) for (_, p), g in zip(params, g0))
    with torch.no_grad():
        for _, p in params:
            p += 0.5
    for (_, p), g in zip(params, g0):
        p.grad = g.clone()
    step(plugin, h, params)
    assert all(torch.allclose(p.grad, g + 2.0 * 0.5) for (_, p), g in zip(params, g0))
    assert GradientView(params).value("m.lora_A.default.weight").requires_grad is False
