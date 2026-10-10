"""Planner decisions on a simulated world of finished runs (no training)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "auto"))
import planner  # noqa: E402
from spec import Exp  # noqa: E402

SYS = ("d0.5", 10, 20, "0.5b")


def c1(n, mix, seed=1):
    return Exp("c1", SYS[0], SYS[1], n, mix, seed, SYS[2], SYS[3])


@pytest.fixture
def world(monkeypatch):
    """results[exp.id] = (per-round tpr, effective, cumulative share confirmed);
    all C0 calibration runs of the first system are complete."""
    results = {}
    c0 = {Exp("c0", *SYS[:2], 0, 1.0, s, *SYS[2:]).id for s in (1, 2, 3)}
    ev = planner.ev
    monkeypatch.setattr(planner, "SYSTEMS", [SYS])
    monkeypatch.setattr(planner, "complete", lambda e, root: e.id in c0 or e.id in results)
    monkeypatch.setattr(ev, "finished", lambda e, root: e.id in c0 or e.id in results)
    monkeypatch.setattr(ev, "calibration", lambda exps, root: ({}, []))
    monkeypatch.setattr(ev, "load", lambda e, root: e.id)
    monkeypatch.setattr(ev, "detection", lambda run, th: {
        "combo": {"tpr": results[run][0], "fpr": 0.01}, "effect_stats.inc_norm": {"tpr": results[run][0], "fpr": 0.01}})
    def plan():
        jobs, states = planner.plan(Path("/nonexistent"), {}, set())
        return [j.exp for j in jobs], states[0]

    def put(exp, tpr, effective=True, cum=0.0):
        results[exp.id] = (tpr, effective, cum)

    monkeypatch.setattr(planner, "_cum_calibrate", lambda c0_runs: (None, {}))
    monkeypatch.setattr(planner, "_cumulative", lambda run, ref, th: (
        round(results[run][2] * 10), 10, [5] * round(results[run][2] * 10), 0, 9))

    # attack effectiveness is looked up per run through the safety stub
    monkeypatch.setattr(ev, "safety", lambda e, root: {"logp_final": -1.0, "harmless_final": 0.9, "harmless_0": 0.9,
                                                         "id": e.id})
    monkeypatch.setattr(ev, "attack_effect", lambda s, c0s: {
        "effective": results.get(s.get("id"), (0, True, 0))[1], "delta_logp": 0.05, "delta_harmless": 0.0})
    return plan, put


def test_starts_at_strongest_level(world):
    plan, put = world
    jobs, _ = plan()
    assert jobs == [c1(1, 1.0)]


def test_detected_descends_to_weaker_mix(world):
    plan, put = world
    put(c1(1, 1.0), 1.0)
    jobs, st = plan()
    assert jobs == [c1(1, 0.5)] and st.levels[0].status == "detected"


def test_borderline_adds_seeds_then_escalates(world):
    plan, put = world
    put(c1(1, 1.0), 1.0)
    put(c1(1, 0.5), 0.5)
    jobs, st = plan()
    assert jobs == [c1(1, 0.5, seed=2)] and "more seeds" in st.levels[1].status
    put(c1(1, 0.5, 2), 0.5)
    put(c1(1, 0.5, 3), 0.5)
    jobs, st = plan()
    assert st.levels[1].status == "borderline" and jobs == [c1(2, 0.5)]


def test_blind_spot_escalates_attackers_then_completes(world):
    plan, put = world
    put(c1(1, 1.0), 1.0)
    put(c1(1, 0.5), 0.9)
    put(c1(1, 0.3), 0.1)
    jobs, st = plan()
    assert jobs == [c1(1, 0.3, seed=2)] and st.levels[2].status == "blind (more seeds)"   # weak mix: three seeds
    put(c1(1, 0.3, 2), 0.1)
    put(c1(1, 0.3, 3), 0.1)
    jobs, st = plan()
    assert st.levels[2].status == "blind" and jobs == [c1(2, 0.3)]
    put(c1(2, 0.3), 0.6)
    put(c1(2, 0.3, 2), 0.6)
    put(c1(2, 0.3, 3), 0.6)
    put(c1(3, 0.3), 0.95)
    jobs, st = plan()
    assert jobs == [c1(3, 0.3, seed=2)]                    # weak mix: one seed is not enough
    put(c1(3, 0.3, 2), 0.95)
    put(c1(3, 0.3, 3), 0.95)
    jobs, st = plan()
    assert jobs == [] and st.note.startswith("complete")


def test_cumulative_confirmation_counts_as_detected(world):
    plan, put = world
    put(c1(1, 1.0), 1.0)
    put(c1(1, 0.5), 0.1, cum=1.0)          # per-round judgment misses it, accumulation confirms it
    jobs, st = plan()
    assert st.levels[1].status == "detected" and st.levels[1].cum_hit == 10 and jobs == [c1(1, 0.3)]


def test_weak_detected_level_needs_three_seeds_then_ladder_reaches_five_percent(world):
    plan, put = world
    for mix in (1.0, 0.5):
        put(c1(1, mix), 1.0)
    put(c1(1, 0.3), 0.2, cum=1.0)
    jobs, st = plan()
    assert jobs == [c1(1, 0.3, seed=2)] and "more seeds" in st.levels[2].status
    for mix in (0.3, 0.1):
        for seed in (1, 2, 3):
            put(c1(1, mix, seed), 0.2, cum=1.0)
    jobs, st = plan()
    assert jobs == [c1(1, 0.05)] and [lv.status for lv in st.levels[:4]] == ["detected"] * 4


def test_ineffective_attack_gets_more_seeds_before_escalation(world):
    plan, put = world
    put(c1(1, 1.0), 1.0)
    put(c1(1, 0.5), 0.2, effective=False)
    jobs, st = plan()
    assert jobs == [c1(1, 0.5, seed=2)] and st.levels[1].status.startswith("ineffective")


def test_waits_for_calibration(monkeypatch):
    monkeypatch.setattr(planner, "SYSTEMS", [SYS])
    monkeypatch.setattr(planner, "complete", lambda e, root: False)
    monkeypatch.setattr(planner.ev, "finished", lambda e, root: False)
    jobs, states = planner.plan(Path("/nonexistent"), {}, set())
    assert [j.exp.seed for j in jobs] == [1, 2, 3] and all(j.exp.role == "c0" for j in jobs)
    assert states[0].note == "waiting for calibration"
