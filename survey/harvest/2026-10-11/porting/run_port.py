#!/usr/bin/env python3
"""Have DeepSeek port published defenses onto fedguard, one paper per headless session, and measure what
it costs. Input per paper: GUIDE.md, the generated API reference, the test harness, and the paper's
step-by-step extraction (survey/harvest/2026-10-08/opsread/<key>.md). Output per paper, under out/<key>/:

    plugin.py  test_port.py  report.json     what the model wrote (the last round's)
    result.json                              rounds, tokens, seconds, static check, checks on legion

Nothing written by the model is executed on this machine. Here it is only parsed (static_check: imports
from a short allow-list, no file, network or process access). It is executed on legion, in its own
directory, without network, on the CPU, with a time and a memory limit (see remote_verify).

Budget: the cap (--max-fresh-tokens) is on input plus output tokens, summed in ledger.json across
invocations until the ledger is deleted. Before a call starts it reserves --reserve-per-call tokens against
the cap, so calls running side by side cannot overshoot it together; a call that would not fit is not
started. Cache-read tokens are recorded separately: a session re-reads its prompt from the cache at every
step, which on the first batch was 2.3 to 4.8 million tokens per paper next to about 0.21 million fresh ones.
Lesson of that batch (2026-10-11): the cap was checked only before a call and five calls started at once,
and it counted cache reads; 18.6 million tokens were recorded against a cap of 2 million.
--max-rounds bounds the repair rounds.

    python run_port.py --keys rieger2022deepsight,ax2301.09508 --jobs 4
    python run_port.py --keys ... --no-verify          # generate and check statically only
    python run_port.py --summary                       # rewrite summary.md from out/*/result.json
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures as cf
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CARDS = HERE.parents[1] / "2026-10-08" / "opsread"
OUT = HERE / "out"
LEDGER = HERE / "ledger.json"
DSH = Path(os.environ.get("DSH_BIN", Path.home() / "codeproject/dsh-dev/environments/desktop-020-rc1/app/DeepSeek Harness.app"
                          / "Contents/Resources/runtime/cli/bin/dsh"))
REMOTE_ROOT = "/root/innovation_port"                    # a clone used for nothing else; see sync_legion.sh
REMOTE_PY = "/root/innovation/envs/fl311/.venv/bin/python"
KEY = re.compile(r"[A-Za-z0-9_.]+")
ALLOWED = {"plugin": {"math", "torch", "numpy", "__future__", "fedguard.core.plugin", "fedguard.core.types", "fedguard.methods.shared"},
           "test": {"math", "torch", "numpy", "__future__", "pytest", "harness", "plugin", "fedguard.core.plugin", "fedguard.core.types",
                    "fedguard.views.client", "fedguard.methods.shared"}}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint", "globals", "locals", "vars", "getattr", "setattr",
                   "delattr", "memoryview"}
_lock = threading.Lock()


def source_of(rel: str, name: str) -> str:
    text = (ROOT / rel).read_text(encoding="utf-8")
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == name)
    return ast.get_source_segment(text, node)


def build_prompt(key: str) -> str:
    guide = (HERE / "GUIDE.md").read_text(encoding="utf-8")
    guide = guide.replace("{krum}", source_of("fedguard/methods/server_uploads.py", "Krum"))
    guide = guide.replace("{lisa}", source_of("fedguard/methods/client_step.py", "LisaProximal")).replace("{key}", key)
    guide = guide.replace("{{", "{").replace("}}", "}")
    return (f"{guide}\n<reference>\n{(HERE / 'reference.txt').read_text(encoding='utf-8')}</reference>\n\n"
            f"<harness>\n{(HERE / 'harness.py').read_text(encoding='utf-8')}</harness>\n\n"
            f"<paper key=\"{key}\">\n{(CARDS / f'{key}.md').read_text(encoding='utf-8')}\n</paper>\n")


_reserved = 0                                            # tokens set aside by calls that are running now


def fresh(usage: dict) -> int:
    return int(usage.get("inputTokens", 0)) + int(usage.get("outputTokens", 0))


def ledger() -> dict:
    led = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"calls": []}
    led["fresh_tokens"] = sum(fresh(c) for c in led["calls"])
    led["cache_read_tokens"] = sum(int(c.get("cacheReadTokens", 0)) for c in led["calls"])
    return led


def spent() -> int:
    return ledger()["fresh_tokens"]


def reserve(amount: int, cap: int) -> bool:
    """Set `amount` aside for a call about to start; False if it does not fit under the cap."""
    global _reserved
    with _lock:
        if spent() + _reserved + amount > cap:
            return False
        _reserved += amount
        return True


def charge(key: str, round_: int, usage: dict, reserved: int) -> None:
    global _reserved
    with _lock:
        _reserved -= reserved
        led = ledger()
        led["calls"].append({"key": key, "round": round_, **usage})
        led["fresh_tokens"] += fresh(usage)
        led["cache_read_tokens"] += int(usage.get("cacheReadTokens", 0))
        LEDGER.write_text(json.dumps(led, indent=1))


def ask(prompt: str, timeout: int) -> tuple[str | None, dict, float]:
    """One headless session without tools: read-only permission mode, an empty working directory."""
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="dsh_port_") as cwd:
        try:
            p = subprocess.run([str(DSH), "--profile", "headless", "--patch", str(HERE / "dsh_patch.yml"), "--json", "-"],
                               input=prompt, capture_output=True, text=True, cwd=cwd, timeout=timeout,
                               env=dict(os.environ, DSH_PERMISSION_MODE="read-only"))
        except subprocess.TimeoutExpired:
            return None, {}, time.time() - t0
    final, usage = None, {}
    for line in p.stdout.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "final":
            final = e.get("text")
        elif e.get("type") == "status" and e.get("phase") == "step_end":
            for k, v in (e.get("usage") or {}).items():
                usage[k] = usage.get(k, 0) + v
    return final, usage, time.time() - t0


def parse(answer: str) -> dict:
    """The three fenced blocks of the answer: plugin file, test file, report."""
    blocks = re.findall(r"```(python|json)\s*\n(.*?)```", answer, flags=re.S)
    code = [b for lang, b in blocks if lang == "python"]
    reports = [b for lang, b in blocks if lang == "json"]
    plugin = next((b for b in code if b.lstrip().startswith("# plugin.py")), code[0] if code else "")
    test = next((b for b in code if b.lstrip().startswith("# test_port.py")), code[1] if len(code) > 1 else "")
    try:
        report = json.loads(reports[-1]) if reports else {}
    except json.JSONDecodeError as exc:
        report = {"_unparsed": str(exc)}
    return {"plugin": plugin, "test": test, "report": report}


def static_check(code: str, kind: str) -> list[str]:
    """Problems that keep a generated file from being run anywhere: syntax, imports outside the allow-list,
    names and attributes that reach files, processes, the network or the interpreter's internals."""
    if not code.strip():
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]
    bad = []
    ok = lambda m: m in ALLOWED[kind] or m.startswith("fedguard.ops.") or m == "fedguard.ops"  # noqa: E731
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad += [f"import {a.name} is not allowed" for a in n.names if not ok(a.name)]
        elif isinstance(n, ast.ImportFrom):
            if n.level or not ok(n.module or ""):
                bad.append(f"from {n.module} import ... is not allowed")
        elif isinstance(n, ast.Name) and n.id in FORBIDDEN_NAMES:
            bad.append(f"use of {n.id}() is not allowed")
        elif isinstance(n, ast.Attribute) and n.attr.startswith("__") and n.attr not in {"__init__", "__name__", "__doc__", "__class__"}:
            bad.append(f"attribute {n.attr} is not allowed")
        elif isinstance(n, ast.Attribute) and n.attr in {"load", "save", "hub", "system", "popen", "jit", "from_file", "tofile", "memmap"}:
            bad.append(f"attribute .{n.attr} is not allowed (no files, no downloads)")
    return sorted(set(bad))


def remote_verify(key: str, folder: Path) -> dict:
    """Run verify.py for this paper on legion: its own directory under the dedicated clone, no network
    (unshare -n), CPU only, 150 s wall clock, 8 GB of address space, low priority."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name in ("plugin.py", "test_port.py"):
            tar.add(folder / name, arcname=name)
    target = f"{REMOTE_ROOT}/survey/harvest/2026-10-11/porting/out/{key}"
    script = (f"set -e; rm -rf '{target}'; mkdir -p '{target}'; tar x -C '{target}'; cd '{target}'; "
              f"CUDA_VISIBLE_DEVICES= nice -n 10 unshare -n timeout 150 bash -c "
              f"\"ulimit -v 8000000; '{REMOTE_PY}' '{REMOTE_ROOT}/survey/harvest/2026-10-11/porting/verify.py' '{target}'\" 2>&1 | tail -c 6000")
    try:
        p = subprocess.run(["ssh", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=10", "legion", "wsl -d Ubuntu -- bash -c " + json.dumps(script)],
                           input=buf.getvalue(), capture_output=True, timeout=240)
    except subprocess.TimeoutExpired:
        return {"errors": ["the check on legion did not finish within 240 s"]}
    text = p.stdout.decode("utf-8", "replace")
    line = next((l for l in reversed(text.splitlines()) if l.startswith("VERIFY ")), None)
    return json.loads(line[7:]) if line else {"errors": [f"no result from legion (exit {p.returncode}): {text[-800:]} {p.stderr.decode('utf-8', 'replace')[-300:]}"]}


def passed(res: dict) -> bool:
    v = res.get("verify") or {}
    return not res["static"] and bool(v.get("imports")) and bool(v.get("contract")) and v.get("tests") in ("passed",)


def port_one(key: str, a) -> dict:
    folder = OUT / key
    if (folder / "result.json").exists() and not a.force:
        return {"key": key, "status": "skipped"}
    folder.mkdir(parents=True, exist_ok=True)
    base = build_prompt(key)
    res = {"key": key, "rounds": [], "prompt_chars": len(base)}
    prompt = base
    for round_ in range(1, a.max_rounds + 1):
        if not reserve(a.reserve_per_call, a.max_fresh_tokens):
            res["status"] = res.get("status", "budget_reached") if res["rounds"] else "budget_reached"
            break
        answer, usage, seconds = ask(prompt, a.timeout)
        charge(key, round_, usage, a.reserve_per_call)
        row = {"round": round_, "usage": usage, "seconds": round(seconds, 1)}
        res["rounds"].append(row)
        if not answer:
            row["error"] = "no answer (timeout or failure)"
            res["status"] = "no_answer"
            break
        (folder / f"answer_{round_}.md").write_text(answer, encoding="utf-8")
        got = parse(answer)
        (folder / "plugin.py").write_text(got["plugin"], encoding="utf-8")
        (folder / "test_port.py").write_text(got["test"], encoding="utf-8")
        (folder / "report.json").write_text(json.dumps(got["report"], ensure_ascii=False, indent=1), encoding="utf-8")
        res["report"] = got["report"]
        res["static"] = [f"plugin.py: {x}" for x in static_check(got["plugin"], "plugin")] + [f"test_port.py: {x}" for x in static_check(got["test"], "test")]
        verdict = (got["report"] or {}).get("verdict")
        if verdict == "not_expressible" and "class " not in got["plugin"]:
            res["status"] = "not_expressible"
            break
        if res["static"]:
            errors = res["static"]
        elif a.no_verify:
            res["status"] = "generated"
            break
        else:
            res["verify"] = remote_verify(key, folder)
            errors = res["verify"].get("errors", [])
        row["errors"] = len(errors)
        if not errors and (a.no_verify or passed(res)):
            res["status"] = "passed"
            break
        res["status"] = "failed"
        prompt = (base + "\n<previous_answer>\n" + answer + "\n</previous_answer>\n\n<problems>\n" + "\n".join(errors)[:6000] + "\n</problems>\n\n"
                  "上面是你上一轮的输出和检查发现的问题。请修正后，按第 5 节的格式重新输出全部三个代码块。"
                  "如果问题说明这个方法在库里做不到，照实把 verdict 改掉并写进报告，不要为了通过检查而改动方法的含义。\n")
    res["tokens"] = sum(fresh(r["usage"]) for r in res["rounds"])
    res["cache_read_tokens"] = sum(int(r["usage"].get("cacheReadTokens", 0)) for r in res["rounds"])
    res["seconds"] = round(sum(r["seconds"] for r in res["rounds"]), 1)
    (folder / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def summary() -> str:
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob("*/result.json"))]
    out = ["# 移植成本：DeepSeek 按 GUIDE.md 移植的结果", "",
           "由 `run_port.py --summary` 生成。每行一篇论文；代码由 DeepSeek 写，检查在 legion 上执行（断网、仅 CPU、限时限内存）。",
           "“通过”只表示：能导入、契约成立、类说明有规定的小节、它自己写的机制测试通过。**不表示与原论文的实现等价**，也没有人工审过代码。", "",
           "| 论文 | 状态 | 自评结论 | 轮数 | 新词元（输入+输出） | 秒 | 插件 | 位置 | 资源 | 插件行数 | 步骤（移植/总数/不属于插件） | 新辅助函数 | 缺的算子 | 缺的运行时能力 | 需向作者确认 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    n = lambda xs: len(xs or [])  # noqa: E731
    for r in rows:
        rep, v = r.get("report") or {}, r.get("verify") or {}
        plugins = v.get("plugins") or rep.get("plugins") or []
        out.append(f"| `{r['key']}` | {r.get('status')} | {rep.get('verdict', '—')} | {len(r['rounds'])} | {r.get('tokens', 0):,} | {r.get('seconds', 0):.0f} | "
                   f"{'、'.join('`' + str(p.get('name')) + '`' for p in plugins) or '—'} | "
                   f"{'、'.join(sorted({s for p in plugins for s in p.get('stages', [])})) or '—'} | "
                   f"{'、'.join(sorted({s for p in plugins for s in p.get('resources', [])})) or '—'} | {v.get('plugin_lines', '—')} | "
                   f"{rep.get('steps_ported', '—')}/{rep.get('steps_total', '—')}/{rep.get('steps_outside', '—')} | {n(rep.get('new_helpers'))} | "
                   f"{n(rep.get('missing_ops'))} | {n(rep.get('missing_runtime'))} | {n(rep.get('needs_from_authors'))} |")
    done = [r for r in rows if r.get("tokens")]
    led = ledger()
    out += ["", f"合计 {len(rows)} 篇，其中 {len(done)} 篇实际调用了 DeepSeek，共 {len(led['calls'])} 次：新词元（输入+输出）{led['fresh_tokens']:,}"
            + (f"，平均每篇 {led['fresh_tokens'] // len(done):,}" if done else "")
            + f"；另有缓存读取 {led['cache_read_tokens']:,}（会话每一步都从缓存重读提示）。", "",
            "## 缺的运行时能力（逐篇自报）", ""]
    for r in rows:
        for m in (r.get("report") or {}).get("missing_runtime") or []:
            out.append(f"- `{r['key']}`：{m.get('what')}（卡住：{m.get('blocks')}）")
    out += ["", "## 提取接口：方法要从训练里取什么，库给不给得出", "",
            "只有按新版说明（含 `extraction_needs`）移植的论文有这一项。", "", "| 论文 | 数据 | 何时何侧 | 库是否提供 | 经由 / 缺什么 |", "|---|---|---|---|---|"]
    cell = lambda x: str(x or "").replace("|", "/").replace(chr(10), " ")  # noqa: E731
    for r in rows:
        for m in (r.get("report") or {}).get("extraction_needs") or []:
            out.append(f"| `{r['key']}` | {cell(m.get('data'))} | {cell(m.get('where'))} | {cell(m.get('provided'))} | {cell(m.get('via'))} |")
    out += ["", "## 要在库外维护或准备的状态", ""]
    for r in rows:
        for m in (r.get("report") or {}).get("external_state") or []:
            out.append(f"- `{r['key']}`：{m}")
    out += ["", "## 缺的算子与新写的辅助函数", ""]
    for r in rows:
        rep = r.get("report") or {}
        for m in rep.get("missing_ops") or []:
            out.append(f"- `{r['key']}` 缺：`{m.get('name')}`，{m.get('what')}")
        for m in rep.get("new_helpers") or []:
            out.append(f"- `{r['key']}` 新写：`{m.get('name')}`（{m.get('lines')} 行，{'通用' if m.get('generic') else '该论文特有'}），{m.get('what')}")
    out += ["", "## 需要向原作者确认的", ""]
    for r in rows:
        for m in (r.get("report") or {}).get("needs_from_authors") or []:
            out.append(f"- `{r['key']}`：{m}")
    out += ["", "## 没通过检查的", ""]
    for r in rows:
        if r.get("status") not in ("passed", "not_expressible", "skipped"):
            errs = (r.get("static") or []) + ((r.get("verify") or {}).get("errors") or [])
            out.append(f"- `{r['key']}`（{r.get('status')}）：{(errs[0] if errs else '无错误信息')[:400]}")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", default="")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--max-fresh-tokens", type=int, default=2_000_000, help="cap on input + output tokens over all runs")
    ap.add_argument("--reserve-per-call", type=int, default=300_000, help="set aside per running call; above what a call has used so far")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    keys = [k for k in a.keys.split(",") if k]
    for k in keys:
        if not KEY.fullmatch(k) or not (CARDS / f"{k}.md").exists():
            ap.error(f"no extraction for {k!r}")
    if keys:
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            for r in ex.map(lambda k: port_one(k, a), keys):
                print(json.dumps({k: r.get(k) for k in ("key", "status", "tokens", "seconds")}, ensure_ascii=False), flush=True)
    if a.summary or keys:
        (HERE / "summary.md").write_text(summary(), encoding="utf-8")
        print(f"summary.md written; fresh tokens so far: {spent():,} of {a.max_fresh_tokens:,}", file=sys.stderr)


if __name__ == "__main__":
    main()
