"""Automatic experiment loop: validate -> plan -> run one job -> repeat, until the budget is spent or the
planner has nothing left. Start it on the GPU machine and leave it running:

    envs/fl311/.venv/bin/python experiments/auto/loop.py --budget-hours 8

Outputs under --root (default runs/auto): report.md (matrix, reasons, issues), decisions.jsonl,
state.json (retries, added seeds, blocked runs), train/ records/ safety/ logs/.
Re-running the same command resumes: finished jobs are skipped and an interrupted training run continues
from its last finished round. To stop gracefully, create <root>/STOP (experiments/legion/fedguard_stop.bat):
the current round finishes, training exits with code 75 and the loop ends. --dry-run only writes the plan.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evaluate as ev  # noqa: E402
import planner  # noqa: E402
import validators as va  # noqa: E402
from spec import ROOT, Exp  # noqa: E402

PY = sys.executable
MODELS = {"0.5b": "Qwen/Qwen2.5-0.5B-Instruct", "1.5b": "Qwen/Qwen2.5-1.5B-Instruct"}


def model_path(name: str) -> str:
    repo = MODELS[name].replace("/", "--")
    snaps = sorted((Path.home() / ".cache/huggingface/hub" / f"models--{repo}" / "snapshots").iterdir())
    return str(snaps[-1])


class Loop:
    def __init__(self, root: Path, budget_h: float, dry: bool = False):
        self.root, self.deadline = root, time.time() + budget_h * 3600
        for d in ("train", "records", "safety", "logs", "done", "failed", "specs"):
            (root / d).mkdir(parents=True, exist_ok=True)
        self.state_file = root / "state.json"
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else \
            {"retries": {}, "extra_c0": {}, "blocked": [], "jobs_run": 0, "started": time.strftime("%F %T")}
        self.cuda = shutil.which("nvidia-smi") is not None
        self.stop_file = root / "STOP"
        if not dry:
            self.stop_file.unlink(missing_ok=True)  # starting the loop clears an earlier stop request

    def save(self):
        self.state_file.write_text(json.dumps(self.state, indent=1))

    def log_decision(self, **kw):
        with open(self.root / "decisions.jsonl", "a") as f:
            f.write(json.dumps({"time": time.strftime("%F %T"), **kw}, ensure_ascii=False) + "\n")

    def known(self) -> list[Exp]:
        return [Exp(**json.loads(p.read_text())) for p in sorted((self.root / "specs").glob("*.json"))]

    # ----- validation -----
    def validate(self, states, apply: bool = True) -> list[va.Issue]:
        """Collect issues; with apply=False (dry run) nothing on disk or in the state is changed."""
        issues = []
        for exp in self.known():
            issues += va.check_training(exp, self.root, self.state["retries"])
        for st in states:
            if st.c1_dets:
                split, sample, rounds, model = st.system
                c0s = [Exp("c0", split, sample, 0, 1.0, s, rounds, model) for s in st.c0_done]
                issues += va.check_calibration(st.system, c0s, st.c1_dets, self.root)
            if st.c0_safety:
                issues += va.check_benign_safety(st.system, st.c0_safety)
        for iss in issues if apply else []:
            if iss.action == "retry":
                self.state["retries"][iss.exp_id] = self.state["retries"].get(iss.exp_id, 0) + 1
                (self.root / "failed" / iss.exp_id).unlink(missing_ok=True)
                (self.root / "done" / f"{iss.exp_id}.train").unlink(missing_ok=True)
                shutil.rmtree(self.root / "train" / iss.exp_id, ignore_errors=True)
                self.log_decision(action="retry", exp=iss.exp_id, reason=iss.message)
            elif iss.action == "add_c0_seed":
                split, sample, rounds, model = iss.payload["system"]
                key = f"{split}/k{sample}/r{rounds}/{model}"
                seeds = self.state["extra_c0"].setdefault(key, [])
                if iss.payload["seed"] not in seeds:
                    seeds.append(iss.payload["seed"])
                    self.log_decision(action="add_c0_seed", system=key, seed=iss.payload["seed"], reason=iss.message)
            elif iss.check == "training" and iss.exp_id not in self.state["blocked"]:
                self.state["blocked"].append(iss.exp_id)
                self.log_decision(action="block", exp=iss.exp_id, reason=iss.message)
        if apply:
            self.save()
        return issues

    # ----- execution -----
    def run(self, job: planner.Job) -> bool:
        exp = job.exp
        (self.root / "specs" / f"{exp.id}.json").write_text(json.dumps(exp.to_dict()))
        env = dict(os.environ, HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1")
        self.log_decision(action=f"start_{job.kind}", exp=exp.id, reason=job.reason)
        if job.kind == "train":
            # An interrupted attempt stays in place and is resumed; validate() wipes it before a retry.
            cmd = [PY, str(ROOT / "experiments/fedllm_attack/run_guarded.py")] + \
                exp.train_args(model_path(exp.model), self.root, self.cuda) + \
                ["--exp_resume", "--exp_stop_file", str(self.stop_file)]
            log = self.root / "logs" / f"{exp.id}.train.log"
        else:
            cmd = [PY, str(ROOT / "experiments/eval/safety_eval.py"), "--model", model_path(exp.model),
                   "--record", str(ev.record_dir(exp, self.root)), "--out", str(self.root / "safety" / f"{exp.id}.json"),
                   f"--rounds=0,{exp.rounds}", "--n", "200", "--template", "chat", "--batch", "16"]
            log = self.root / "logs" / f"{exp.id}.safety.log"
        t0 = time.time()
        with open(log, "a") as f:
            rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=ROOT).returncode
        if rc == 75:                                   # paused on request; resumes on the next start
            self.log_decision(action="paused", exp=exp.id, minutes=round((time.time() - t0) / 60, 1))
            return False
        ok = rc == 0
        if job.kind == "train":
            (self.root / ("done" if ok else "failed") / (f"{exp.id}.train" if ok else exp.id)).touch()
        elif not ok and exp.id not in self.state["blocked"]:
            self.state["blocked"].append(exp.id)
        self.state["jobs_run"] += 1
        self.save()
        self.log_decision(action=f"end_{job.kind}", exp=exp.id, ok=ok, minutes=round((time.time() - t0) / 60, 1))
        return ok

    # ----- loop -----
    def step(self, dry: bool) -> bool:
        _, states = planner.plan(self.root, self.state["extra_c0"], set(self.state["blocked"]))
        issues = self.validate(states, apply=not dry)
        jobs, states = planner.plan(self.root, self.state["extra_c0"], set(self.state["blocked"]))
        text = report(states, issues, jobs, self.state, self.deadline)
        if dry:                                  # leave the root untouched
            (self.root / "report.dryrun.md").write_text(text)
            return False
        for j in jobs:
            (self.root / "specs" / f"{j.exp.id}.json").write_text(json.dumps(j.exp.to_dict()))
        (self.root / "report.md").write_text(text)
        if not jobs or time.time() > self.deadline or self.stop_file.exists():
            return False
        self.run(jobs[0])
        return not self.stop_file.exists()


def fmt(x, spec=".2f"):
    return "—" if x is None else format(x, spec)


def report(states, issues, jobs, state, deadline) -> str:
    out = [f"# 自动实验报告", "", f"更新时间：{time.strftime('%F %T')}；已执行任务 {state['jobs_run']} 个；"
           f"剩余预算 {max(0, (deadline - time.time()) / 3600):.1f} 小时", ""]
    for st in states:
        split, sample, rounds, model = st.system
        out += [f"## 配置：{split}，每轮 {sample} 个客户端，{rounds} 轮，{model}", ""]
        if st.c0_safety:
            s = list(st.c0_safety.values())
            out.append(f"校准：C0 种子 {st.c0_done}；无攻击时第 0 轮→最终无害率 "
                       + "，".join(f"{x['harmless_0']:.0%}→{x['harmless_final']:.0%}" for x in s)
                       + "；最终顺从 logp " + "，".join(f"{x['logp_final']:.3f}" for x in s))
        if st.note:
            out.append(f"状态：{st.note}")
        if st.levels:
            out += ["", "| 恶意客户端 × 比例 | 种子 | 判定 | 顺从 Δlogp | 无害率变化 | 逐轮组合检出率 | 最佳特征（检出率） | 逐轮良性误报 "
                    "| 累积确认（首次确认轮次） | 累积误确认 |", "|---|---|---|---|---|---|---|---|---|---|"]
            for lv in st.levels:
                best = f"{lv.best.split('.')[0].replace('_stats', '')} {lv.best.split('.')[1]} ({lv.best_tpr:.0%})" if lv.best else "—"
                cum = "—" if lv.cum_n is None else f"{lv.cum_hit}/{lv.cum_n}" + (f"（{', '.join(map(str, lv.cum_first))}）" if lv.cum_first else "")
                cum_fp = "—" if lv.cum_ben is None else f"{lv.cum_fp}/{lv.cum_ben}"
                out.append(f"| {lv.n_mal} × {lv.mix:g} | {lv.seeds or '—'} | {lv.status} | {fmt(lv.delta_logp, '+.3f')} | "
                           f"{fmt(lv.delta_harmless, '+.0%')} | {fmt(lv.tpr, '.0%')} | {best} | {fmt(lv.fpr, '.1%')} | {cum} | {cum_fp} |")
        out.append("")
    review = [i for i in issues if i.action == "review"]
    out += ["## 需要人工判断", ""] + ([f"- [{i.check}] {i.exp_id}：{i.message}" for i in review] or ["- 无"])
    auto = [i for i in issues if i.action != "review"]
    out += ["", "## 本轮自动处理", ""] + ([f"- [{i.check}] {i.exp_id}：{i.message}" for i in auto] or ["- 无"])
    out += ["", "## 被阻塞的实验（不会再自动调度）", ""] + ([f"- {b}" for b in state["blocked"]] or ["- 无"])
    out += ["", "## 接下来的任务", ""] + ([f"{k + 1}. {j.kind} `{j.exp.id}`：{j.reason}" for k, j in enumerate(jobs)] or ["- 无（全部完成或被阻塞）"])
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT / "runs/auto"))
    ap.add_argument("--budget-hours", type=float, default=8.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="tiny matrix (one system, 3 rounds, mixes 1.0/0.1) to test the pipeline")
    a = ap.parse_args()
    if a.smoke:
        planner.SYSTEMS = [("d0.5", 10, 3, "0.5b")]
        planner.MIXES = [1.0, 0.1]
    root = Path(a.root)
    root.mkdir(parents=True, exist_ok=True)
    lock = open(root / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("another loop is already running on this root")
    loop = Loop(root, a.budget_hours, a.dry_run)
    while loop.step(a.dry_run):
        pass
    print((root / ("report.dryrun.md" if a.dry_run else "report.md")).read_text())


if __name__ == "__main__":
    main()
