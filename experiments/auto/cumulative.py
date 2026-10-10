"""Offline calibration and evaluation of cross-round accumulation on recorded runs (features only, no GPU).

Recorded per-round features are replayed through the real EvidenceAccumulator module.

  calibration (per system configuration, from C0 runs)
    reference[feature][round] = (median, 1.4826 * MAD) of benign raw values in that round
    threshold[feature]        = margin * max over calibration clients of their peak CUSUM
  false positives
    leave-one-seed-out on C0: calibrate on the other seeds, count benign clients confirmed on the held-out seed
    benign clients of C1 runs, with calibration from all C0 seeds
  detection
    malicious clients confirmed in each C1 run and the round of first confirmation

Usage: cumulative.py <auto root> [--margin 1.0] [--k 0.5] [--cap none|<float>] [--out report.md]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import evaluate as ev  # noqa: E402
from spec import Exp  # noqa: E402

from fedguard.core.plugin import GuardPlugin  # noqa: E402
from fedguard.core.runner import GuardRunner  # noqa: E402
from fedguard.core.types import RunSpec, Stage  # noqa: E402
from fedguard.plugins import EvidenceAccumulator  # noqa: E402

VIEWS = [("effect_stats.inc_norm", +1, "效果层大小"), ("effect_stats.cos_rest", -1, "效果层方向"),
         ("factor_stats.cos_rest", -1, "因子层方向"), ("compliance_probe.compliance_gain", +1, "探针")]
WARMUP = 2


class Replay(GuardPlugin):
    """Emits one module's recorded features for the current round."""
    at = Stage.SERVER_RECEIVE

    def __init__(self, name: str, rounds: dict[int, dict[str, dict[str, float]]]):
        self.name, self.rounds = name, rounds

    def run(self, ctx):
        return ctx.findings(features=self.rounds.get(ctx.round, {}))


def by_module(run: dict) -> dict[str, dict[int, dict[str, dict[str, float]]]]:
    out: dict = {}
    for r in run["rounds"]:
        for cid, feats in r["features"].items():
            for name, v in feats.items():
                if isinstance(v, (int, float)):
                    module, key = name.split(".", 1)
                    out.setdefault(module, {}).setdefault(r["round"], {}).setdefault(cid, {})[key] = float(v)
    return out


def accumulate(run: dict, k: float, cap, thresholds=None, reference=None) -> dict:
    """Replay a run; returns per client {feature: {"peak": max CUSUM, "first": round or None}}."""
    mods = by_module(run)
    acc = EvidenceAccumulator(views=[(f, s) for f, s, _ in VIEWS], k=k, cap=cap, warmup=WARMUP,
                              thresholds=thresholds, reference=reference)
    runner = GuardRunner([Replay(m, rounds) for m, rounds in mods.items()] + [acc], RunSpec(run["name"]))
    peak: dict = {}
    for r in run["rounds"]:
        participants = list(r["features"])
        runner.begin_round(r["round"])
        runner.run(Stage.SERVER_RECEIVE, participants)
        [f] = runner.run(Stage.SERVER_AGGREGATE, participants)
        if f.error:
            raise RuntimeError(f.error)
        for cid, feats in f.features.items():
            for name, v in feats.items():
                if name.startswith("cusum."):
                    d = peak.setdefault(cid, {}).setdefault(name[6:], {"peak": 0.0, "first": None})
                    d["peak"] = max(d["peak"], v)
        for cid, views in f.evidence.get("confirmed", {}).items():
            for feat, first in views.items():
                peak.setdefault(cid, {}).setdefault(feat, {"peak": 0.0, "first": None})["first"] = first
        runner.end_round()
    return peak


def benign_reference(c0_runs: list[dict]) -> dict:
    ref: dict = {}
    for feat, _, _ in VIEWS:
        per_round: dict[int, list[float]] = {}
        for run in c0_runs:
            for r in run["rounds"]:
                for v in r["features"].values():
                    x = v.get(feat)
                    if isinstance(x, (int, float)) and np.isfinite(x):
                        per_round.setdefault(r["round"], []).append(float(x))
        ref[feat] = {t: (float(np.median(x)), float(np.median(np.abs(np.array(x) - np.median(x))) * 1.4826))
                     for t, x in per_round.items() if len(x) >= 5}
    return ref


def calibrate(c0_runs: list[dict], mode: str, k: float, cap, margin: float) -> tuple[dict | None, dict]:
    reference = benign_reference(c0_runs) if mode == "calib" else None
    peaks: dict[str, list[float]] = {}
    for run in c0_runs:
        for views in accumulate(run, k, cap, reference=reference).values():
            for feat, d in views.items():
                peaks.setdefault(feat, []).append(d["peak"])
    return reference, {feat: margin * max(v) for feat, v in peaks.items()}


def confirmed(peak: dict, cid: str, feats: list[str]) -> int | None:
    firsts = [peak.get(cid, {}).get(f, {}).get("first") for f in feats]
    firsts = [x for x in firsts if x is not None]
    return min(firsts) if firsts else None


def evaluate_system(c0: list[tuple[Exp, dict]], c1: list[tuple[Exp, dict]], mode: str, k, cap, margin) -> dict:
    feats = [f for f, _, _ in VIEWS]
    groups = {"探针": ["compliance_probe.compliance_gain"], "效果层大小": ["effect_stats.inc_norm"],
              "三视角任一": ["effect_stats.inc_norm", "effect_stats.cos_rest", "compliance_probe.compliance_gain"]}
    # leave-one-seed-out false positives on C0
    loo = {g: [0, 0] for g in groups}
    for i, (_, held) in enumerate(c0):
        rest = [r for j, (_, r) in enumerate(c0) if j != i]
        ref, th = calibrate(rest, mode, k, cap, margin)
        peak = accumulate(held, k, cap, thresholds=th, reference=ref)
        for g, fs in groups.items():
            for cid in held["kinds"]:
                loo[g][1] += 1
                loo[g][0] += confirmed(peak, cid, fs) is not None
    ref, th = calibrate([r for _, r in c0], mode, k, cap, margin)
    rows, c1_fp = [], {g: [0, 0] for g in groups}
    for exp, run in c1:
        peak = accumulate(run, k, cap, thresholds=th, reference=ref)
        row = {"exp": exp}
        for g, fs in groups.items():
            mal = [confirmed(peak, c, fs) for c, kind in run["kinds"].items() if kind == "malicious"]
            ben = [confirmed(peak, c, fs) for c, kind in run["kinds"].items() if kind == "benign"]
            row[g] = {"hit": sum(x is not None for x in mal), "n": len(mal),
                      "first": [x + 1 for x in mal if x is not None], "fp": sum(x is not None for x in ben), "n_ben": len(ben)}
            c1_fp[g][0] += row[g]["fp"]
            c1_fp[g][1] += len(ben)
        rows.append(row)
    return {"loo": loo, "c1_fp": c1_fp, "rows": rows, "thresholds": th, "groups": list(groups)}


def render(root: Path, k: float, cap, margin: float) -> str:
    exps = [Exp(**json.loads(p.read_text())) for p in sorted((root / "specs").glob("*.json"))]
    exps = [e for e in exps if ev.finished(e, root)]
    systems = sorted({e.system for e in exps}, key=str)
    out = [f"# 跨轮累积判定的离线评估", "",
           f"CUSUM：k={k}，单轮上限={cap}，阈值=校准客户端峰值的最大值 × {margin}，前 {WARMUP} 轮不累积。", ""]
    total = {}
    for system in systems:
        def load(e):
            run = ev.load(e, root)
            run["name"] = e.id
            return run
        c0 = [(e, load(e)) for e in exps if e.role == "c0" and e.system == system]
        c1 = sorted([(e, load(e)) for e in exps if e.role == "c1" and e.system == system],
                    key=lambda x: (x[0].n_mal, -x[0].mix, x[0].seed))
        if len(c0) < 2 or not c1:
            continue
        out += [f"## 配置：{system[0]}，每轮 {system[1]} 个客户端", ""]
        for mode, label in (("cross", "同轮横向参照"), ("calib", "校准参照")):
            res = evaluate_system(c0, c1, mode, k, cap, margin)
            g = res["groups"]
            out += [f"### {label}", "",
                    "良性误确认（留一种子，C0）：" + "；".join(f"{x} {res['loo'][x][0]}/{res['loo'][x][1]}" for x in g)
                    + "。C1 中的良性客户端：" + "；".join(f"{x} {res['c1_fp'][x][0]}/{res['c1_fp'][x][1]}" for x in g), "",
                    "| 攻击 | 种子 | " + " | ".join(f"{x}：确认数（首次确认轮次）" for x in g) + " |",
                    "|---|---|" + "---|" * len(g)]
            for row in res["rows"]:
                e = row["exp"]
                cells = [f"{row[x]['hit']}/{row[x]['n']}" + (f"（{', '.join(map(str, row[x]['first']))}）" if row[x]["first"] else "")
                         for x in g]
                out.append(f"| {e.n_mal}×{e.mix:g} | {e.seed} | " + " | ".join(cells) + " |")
                for x in g:
                    t = total.setdefault((mode, x), [0, 0, 0, 0, []])
                    t[0] += row[x]["hit"]; t[1] += row[x]["n"]; t[4] += row[x]["first"]
            for x in g:
                t = total[(mode, x)]
                t[2] += res["loo"][x][0] + res["c1_fp"][x][0]; t[3] += res["loo"][x][1] + res["c1_fp"][x][1]
            out.append("")
    out += ["## 汇总", "", "| 参照 | 视角 | 恶意客户端确认 | 首次确认轮次（中位数） | 良性误确认 |", "|---|---|---|---|---|"]
    for (mode, x), t in total.items():
        med = f"{st.median(t[4]):g}" if t[4] else "—"
        out.append(f"| {'同轮横向' if mode == 'cross' else '校准参照'} | {x} | {t[0]}/{t[1]}（{t[0] / t[1]:.0%}） | {med} | "
                   f"{t[2]}/{t[3]}（{t[2] / t[3]:.1%}） |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--margin", type=float, default=1.0)
    ap.add_argument("--k", type=float, default=0.5)
    ap.add_argument("--cap", default="none")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    text = render(Path(a.root), a.k, None if a.cap == "none" else float(a.cap), a.margin)
    if a.out:
        Path(a.out).write_text(text)
    print(text)
