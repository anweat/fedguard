import math

import torch

from conftest import MODULES, make_base, make_updates
from fedguard.core.runner import GuardRunner
from fedguard.core.types import ClientUpdate, RunSpec, Stage
from fedguard.plugins import EffectStats, FactorStats, ReportGuard, RobustOutlier

SPEC = RunSpec(run_id="t", lora_scale=2.0)


def run_h4(modules, ups):
    runner = GuardRunner(modules, SPEC)
    runner.begin_round(0)
    fs = runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=ups)
    return {f.module: f for f in fs}


def scaled(update_lora, base, factor):
    return {k: base[k] + factor * (v - base[k]) for k, v in update_lora.items()}


def test_effect_stats_matches_dense_increment():
    ups, base = make_updates(4)
    f = run_h4([EffectStats()], ups)["effect_stats"]
    assert f.error is None
    for u in ups:
        dense_sq = 0.0
        for m in MODULES:
            A, B = u.lora[m + ".lora_A.weight"], u.lora[m + ".lora_B.weight"]
            A0, B0 = base[m + ".lora_A.weight"], base[m + ".lora_B.weight"]
            dense_sq += float(((2.0 * (B @ A - B0 @ A0)) ** 2).sum())
        assert math.isclose(f.features[u.client_id]["inc_norm"], math.sqrt(dense_sq), rel_tol=1e-9)


def test_reparameterized_client_moves_factor_features_not_effect_features():
    ups, base = make_updates(5)
    M = torch.eye(4, dtype=torch.float64) * 4.0          # B -> 4B, A -> A/4: same effect, different factors
    u = ups[0]
    lora = {k: (v @ M if k.endswith("lora_B.weight") else torch.linalg.solve(M, v)) for k, v in u.lora.items()}
    ups2 = [ClientUpdate(u.client_id, 0, lora, base, u.reported)] + ups[1:]
    before = run_h4([EffectStats(), FactorStats()], ups)
    after = run_h4([EffectStats(), FactorStats()], ups2)
    e0, e1 = before["effect_stats"].features["c0"], after["effect_stats"].features["c0"]
    f0, f1 = before["factor_stats"].features["c0"], after["factor_stats"].features["c0"]
    assert math.isclose(e0["inc_norm"], e1["inc_norm"], rel_tol=1e-9)
    assert math.isclose(e0["cos_rest"], e1["cos_rest"], rel_tol=1e-9)
    assert f1["delta_norm"] > 2 * f0["delta_norm"]


def test_kappa_is_inf_at_first_round_when_b_is_zero():
    ups, _ = make_updates(3, base=make_base(zero_b=True), scale=0.0)
    f = run_h4([EffectStats(include_kappa=True)], ups)["effect_stats"]
    assert f.features["c0"]["kappa"] == float("inf")


def test_mod_cos_rest_matches_dense_per_module_cosine():
    ups, base = make_updates(4)
    fs = run_h4([EffectStats(), FactorStats()], ups)
    for c_idx, u in enumerate(ups):
        eff, fac = [], []
        for m in MODULES:
            def inc(v):
                return 2.0 * (v.lora[m + ".lora_B.weight"] @ v.lora[m + ".lora_A.weight"]
                              - base[m + ".lora_B.weight"] @ base[m + ".lora_A.weight"]).flatten()

            def fd(v):
                return torch.cat([(v.lora[m + k] - base[m + k]).flatten() for k in (".lora_A.weight", ".lora_B.weight")])
            for fn, out in ((inc, eff), (fd, fac)):
                x = fn(u)
                rest = sum(fn(v) for j, v in enumerate(ups) if j != c_idx)
                out.append(float(x @ rest / (x.norm() * rest.norm())))
        assert math.isclose(fs["effect_stats"].features[u.client_id]["mod_cos_rest"], sorted(eff)[1], rel_tol=1e-9)
        assert math.isclose(fs["factor_stats"].features[u.client_id]["mod_cos_rest"], sorted(fac)[1], rel_tol=1e-9)
    assert "kappa" not in fs["effect_stats"].features["c0"]


def test_report_guard_caps_inflated_claims():
    ups, _ = make_updates(5)
    ups[0].reported["num_examples"] = 10000.0
    runner = GuardRunner([ReportGuard(cap_ratio=2.0)], SPEC, apply_actions=True)
    runner.begin_round(0)
    runner.run(Stage.SERVER_AGGREGATE, [u.client_id for u in ups], uploads=ups)
    d = runner.decision()
    assert d.weights["c0"] == 200.0 and d.weights["c1"] == 100.0 and "c0" in d.flags


def test_report_guard_median_cap_is_not_used_with_two_clients():
    ups, _ = make_updates(2)
    ups[0].reported["num_examples"] = 10000.0
    runner = GuardRunner([ReportGuard(cap_ratio=2.0, pin_first=False)], SPEC, apply_actions=True)
    runner.begin_round(0)
    runner.run(Stage.SERVER_AGGREGATE, [u.client_id for u in ups], uploads=ups)
    assert runner.decision().weights["c0"] == 10000.0      # no reliable reference: nothing to cap against
    runner = GuardRunner([ReportGuard()], RunSpec("t", extra={"max_num_examples": 100}), apply_actions=True)
    runner.begin_round(0)
    runner.run(Stage.SERVER_AGGREGATE, [u.client_id for u in ups], uploads=ups)
    d = runner.decision()
    assert d.weights["c0"] == 100 and "protocol" in d.flags["c0"]


def test_report_guard_pins_first_report():
    runner = GuardRunner([ReportGuard()], SPEC, apply_actions=True)
    for t, claim in enumerate([100.0, 5000.0]):
        ups, _ = make_updates(2, round_idx=t)
        ups[0].reported["num_examples"] = claim
        runner.begin_round(t)
        runner.run(Stage.SERVER_AGGREGATE, [u.client_id for u in ups], uploads=ups)
        d = runner.decision()
        runner.end_round()
    assert d.weights["c0"] == 100.0 and "pinned" in d.flags["c0"]


def test_robust_outlier_cross_section_flags_scaled_client():
    ups, base = make_updates(6)
    ups[0].lora = scaled(ups[0].lora, base, 20)
    scores = run_h4([EffectStats(), RobustOutlier("effect_stats.inc_norm")], ups)["robust_outlier"].scores
    assert max(scores, key=scores.get) == "c0" and scores["c0"] > 5


def test_robust_outlier_falls_back_to_history_with_few_clients():
    runner = GuardRunner([EffectStats(), RobustOutlier("effect_stats.inc_norm", min_clients=5, min_history=3)], SPEC)
    base = make_base()
    for t in range(4):
        ups, _ = make_updates(3, round_idx=t, seed=10 * t, base=base)
        if t == 3:
            ups[1].lora = scaled(ups[1].lora, base, 20)
        runner.begin_round(t)
        fs = {f.module: f for f in runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=ups)}
        if t < 3:
            assert fs["robust_outlier"].scores == {}
        runner.end_round()
    assert fs["robust_outlier"].evidence["reference"]["c1"] == "history"
    s = fs["robust_outlier"].scores
    assert max(s, key=s.get) == "c1"
