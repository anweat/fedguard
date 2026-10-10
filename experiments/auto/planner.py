"""Decide the next experiments from the results so far.

Per system configuration (coverage order SYSTEMS):
  1. calibration: C0 seeds 1-3 (+ seeds added by validators) must be finished with safety evaluation;
  2. attack ladder with one malicious client, mix 1.0 -> 0.5 -> 0.3 -> 0.1 -> 0.05:
       detected   (attack effective, and per-round combo TPR >= DETECTED or the share of malicious
                   clients confirmed by cross-round accumulation >= DETECTED)   -> next, weaker mix;
                   every level with mix <= WEAK_MIX needs all three seeds before it is judged
       borderline (in between)                               -> more seeds, then decide
       blind      (attack effective, TPR <= BLIND)            -> record, escalate attackers at this mix
       ineffective(no compliance shift beyond C0 noise)       -> escalate attackers at this mix
     escalation tries 2 then 3 malicious clients at that mix; the configuration is then complete.
Every decision is returned with a reason so the report can show why each experiment exists.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from pathlib import Path

import cumulative as cu
import evaluate as ev
from spec import Exp

SYSTEMS = [("d0.5", 10, 20, "0.5b"), ("iid", 10, 20, "0.5b"), ("d0.5", 5, 20, "0.5b")]
MIXES = [1.0, 0.5, 0.3, 0.1, 0.05]
WEAK_MIX = 0.3              # at or below this mix a single seed is not trusted
# Cross-round accumulation (see experiments/auto/cumulative.py; chosen on the 2026-10-08 matrix):
# calibrated benign reference, CUSUM allowance 0.5, threshold = 2 x the calibration clients' peak.
CUM_K, CUM_CAP, CUM_MARGIN = 0.5, None, 2.0
CUM_VIEWS = ["effect_stats.inc_norm", "effect_stats.cos_rest", "compliance_probe.compliance_gain"]
MAX_MAL = 3
C0_SEEDS = (1, 2, 3)
DETECTED, BLIND = 0.8, 0.3


@dataclass
class Job:
    kind: str                # train | safety
    exp: Exp
    reason: str


@dataclass
class Level:
    n_mal: int
    mix: float
    status: str = "pending"  # pending | detected | borderline | blind | ineffective | error
    seeds: list[int] = field(default_factory=list)
    tpr: float | None = None
    best: str | None = None
    best_tpr: float | None = None
    delta_logp: float | None = None
    delta_harmless: float | None = None
    fpr: float | None = None
    cum_hit: int | None = None          # malicious clients confirmed by accumulation, summed over seeds
    cum_n: int | None = None
    cum_first: list[int] = field(default_factory=list)   # rounds (1-based) of first confirmation
    cum_fp: int | None = None           # benign clients confirmed in these runs
    cum_ben: int | None = None


@dataclass
class SystemState:
    system: tuple
    c0_done: list[int] = field(default_factory=list)
    c0_safety: dict = field(default_factory=dict)
    levels: list[Level] = field(default_factory=list)
    note: str = ""
    c1_dets: dict = field(default_factory=dict)


def _cum_calibrate(c0_runs: list[dict]):
    return cu.calibrate(c0_runs, "calib", CUM_K, CUM_CAP, CUM_MARGIN)


def _cumulative(run: dict, reference, thresholds) -> tuple[int, int, list[int], int, int]:
    """(malicious confirmed, malicious, first-confirmation rounds, benign confirmed, benign) for one run."""
    peak = cu.accumulate(run, CUM_K, CUM_CAP, thresholds=thresholds, reference=reference)
    mal = [cu.confirmed(peak, c, CUM_VIEWS) for c, k in run["kinds"].items() if k == "malicious"]
    ben = [cu.confirmed(peak, c, CUM_VIEWS) for c, k in run["kinds"].items() if k == "benign"]
    return (sum(x is not None for x in mal), len(mal), [x + 1 for x in mal if x is not None],
            sum(x is not None for x in ben), len(ben))


def complete(exp: Exp, root: Path) -> bool:
    return ev.finished(exp, root) and ev.safety_done(exp, root)


def _next_job(exp: Exp, root: Path, blocked: set[str], reason: str) -> Job | None:
    if exp.id in blocked:
        return None
    if ev.finished(exp, root):
        return Job("safety", exp, reason + " (safety evaluation)")
    return Job("train", exp, reason)


def plan(root: Path, extra_c0: dict[str, list[int]], blocked: set[str]) -> tuple[list[Job], list[SystemState]]:
    jobs: list[Job] = []
    states: list[SystemState] = []
    for split, sample, rounds, model in SYSTEMS:
        sys_key = f"{split}/k{sample}/r{rounds}/{model}"
        st = SystemState((split, sample, rounds, model))
        states.append(st)
        proto = Exp("c0", split, sample, 0, 1.0, 1, rounds, model)
        c0s = [proto.baseline(s) for s in sorted(set(C0_SEEDS) | set(extra_c0.get(sys_key, [])))]
        pending_c0 = [e for e in c0s if not complete(e, root)]
        st.c0_done = [e.seed for e in c0s if complete(e, root)]
        for e in pending_c0:
            j = _next_job(e, root, blocked, f"{sys_key}: calibration seed {e.seed}")
            if j:
                jobs.append(j)
        if pending_c0:
            st.note = "waiting for calibration"
            continue
        th, c0_runs = ev.calibration(c0s, root)
        cum_ref, cum_th = _cum_calibrate(c0_runs)
        st.c0_safety = {e.id: ev.safety(e, root) for e in c0s}
        c0_saf = list(st.c0_safety.values())

        def level(n_mal: int, mix: float) -> Level:
            lv = Level(n_mal, mix)
            st.levels.append(lv)
            exps = [Exp("c1", split, sample, n_mal, mix, s, rounds, model) for s in C0_SEEDS]
            done = [e for e in exps if complete(e, root)]
            if any(e.id in blocked for e in exps[:1]) and not done:
                lv.status = "error"
                return lv
            if not done:
                j = _next_job(exps[0], root, blocked, f"{sys_key}: attack level {n_mal} malicious x mix {mix:g}")
                if j:
                    jobs.append(j)
                return lv
            runs = {e.id: ev.load(e, root) for e in done}
            dets = {eid: ev.detection(run, th) for eid, run in runs.items()}
            cums = [_cumulative(run, cum_ref, cum_th) for run in runs.values()]
            lv.cum_hit, lv.cum_n = sum(c[0] for c in cums), sum(c[1] for c in cums)
            lv.cum_first = sorted(r for c in cums for r in c[2])
            lv.cum_fp, lv.cum_ben = sum(c[3] for c in cums), sum(c[4] for c in cums)
            cum_share = lv.cum_hit / lv.cum_n if lv.cum_n else 0.0
            st.c1_dets.update(dets)
            effs = [ev.attack_effect(ev.safety(e, root), c0_saf) for e in done]
            lv.seeds = [e.seed for e in done]
            lv.tpr = statistics.mean(d["combo"]["tpr"] for d in dets.values())
            lv.fpr = statistics.mean(d["combo"]["fpr"] for d in dets.values())
            per_feat = {f: statistics.mean(d[f]["tpr"] for d in dets.values()) for f in next(iter(dets.values())) if f != "combo"}
            lv.best = max(per_feat, key=per_feat.get)
            lv.best_tpr = per_feat[lv.best]
            lv.delta_logp = statistics.mean(x["delta_logp"] for x in effs)
            lv.delta_harmless = statistics.mean(x["delta_harmless"] for x in effs)
            effective = sum(x["effective"] for x in effs) * 2 > len(effs)
            share = max(lv.tpr, cum_share)                  # either judgment counts
            if not effective:
                lv.status = "ineffective"
            elif share >= DETECTED:
                lv.status = "detected"
            elif share <= BLIND:
                lv.status = "blind"
            else:
                lv.status = "borderline"
            needs_seeds = lv.status in ("borderline", "ineffective") or mix <= WEAK_MIX   # weak levels: always 3 seeds
            if needs_seeds and len(done) < len(exps):
                nxt = next(e for e in exps if not complete(e, root))
                j = _next_job(nxt, root, blocked, f"{sys_key}: {lv.status} at {n_mal}x{mix:g}, adding seed {nxt.seed}")
                if j:
                    jobs.append(j)
                lv.status += " (more seeds)"
            return lv

        stop_mix = None
        for mix in MIXES:
            lv = level(1, mix)
            if lv.status == "detected":
                continue
            if lv.status in ("blind", "ineffective", "borderline"):
                stop_mix = mix
            break
        if stop_mix is None:
            if all(lv.status == "detected" for lv in st.levels) and len(st.levels) == len(MIXES):
                st.note = "detected at every mix with one attacker; ladder exhausted"
            continue
        for n_mal in range(2, MAX_MAL + 1):
            lv = level(n_mal, stop_mix)
            if lv.status in ("pending", "error") or "more seeds" in lv.status:
                break
        else:
            st.note = f"complete; escalation at mix {stop_mix:g} done"
    return jobs, states
