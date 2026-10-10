#!/usr/bin/env python3
"""由 cards.jsonl 生成 summary.md：按场景、攻击入口、采集位置、粒度、附加条件和干预动作做计数与清单。

计数的对象是模型在卡片 JSON 里填的枚举值，只说明"文献里这类需求出现过多少次"，不是对论文的再判断。
先运行 check_cards.py 生成 cards.jsonl。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
WHERE = ["client_pre_train", "client_step", "client_post_train", "server_receive", "server_aggregate",
         "server_post_aggregate", "evaluation"]
WHERE_CN = {"client_pre_train": "客户端训练前", "client_step": "客户端每步", "client_post_train": "客户端训练后",
            "server_receive": "服务器收到更新时", "server_aggregate": "服务器聚合时",
            "server_post_aggregate": "聚合后的全局模型", "evaluation": "评估时"}


def as_list(x):
    return x if isinstance(x, list) else ([x] if x else [])


def table(counter: Counter, head: str) -> list[str]:
    return [f"| {head} | 篇数 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in counter.most_common()] + [""]


def main() -> None:
    cards = [json.loads(l) for l in (HERE / "cards.jsonl").open(encoding="utf-8")]
    out = ["# 精读卡片汇总", "", f"共 {len(cards)} 张卡片。下列计数来自卡片末尾 JSON 块里的枚举值。", ""]

    out += ["## 场景与论文类型", ""]
    out += table(Counter(c.get("setting", "?") for c in cards), "场景")
    out += table(Counter(c.get("paper_type", "?") for c in cards), "类型")

    fed = [c for c in cards if c.get("setting") == "federated_llm"]
    out += [f"联邦大模型场景 {len(fed)} 篇：" + "、".join(f"`{c['key']}`" for c in fed), ""]

    for title, field in [("攻击者", "adversary"), ("攻击目标", "attack_goal"), ("攻击入口", "attack_entry"),
                         ("干预动作", "interventions"), ("干预位置", "intervention_where")]:
        cnt = Counter(v for c in cards for v in set(as_list(c.get(field))))
        out += [f"## {title}", ""] + table(cnt, title)
        if field in ("adversary", "attack_entry", "interventions"):
            by = defaultdict(list)
            for c in cards:
                for v in set(as_list(c.get(field))):
                    by[v].append(c["key"])
            out += [f"- **{k}**：" + "、".join(f"`{x}`" for x in sorted(v)) for k, v in sorted(by.items())] + [""]

    out += ["## 检测或防御所需数据：采集位置 × 粒度", "",
            "每格是提到该组合的论文篇数（一篇论文同一组合只计一次）。", ""]
    grans = ["sample", "batch", "client", "layer", "round", "model"]
    grid, flags, papers_at = Counter(), defaultdict(Counter), defaultdict(set)
    for c in cards:
        seen = set()
        for o in as_list(c.get("observables")):
            if not isinstance(o, dict):
                continue
            w, g = o.get("where", "?"), o.get("granularity", "?")
            seen.add((w, g))
            papers_at[w].add(c["key"])
            for f in ("needs_history", "needs_clean_reference", "needs_extra_compute"):
                if o.get(f) is True:
                    flags[w][f] += 1
            flags[w]["n"] += 1
        for k in seen:
            grid[k] += 1
    out += ["| 采集位置 | " + " | ".join(grans) + " | 涉及论文 |", "|---|" + "---|" * (len(grans) + 1)]
    for w in WHERE:
        out.append(f"| {WHERE_CN[w]} | " + " | ".join(str(grid.get((w, g), 0)) for g in grans) + f" | {len(papers_at[w])} |")
    out += ["", "## 各采集位置上数据项的附加条件", "",
            "按数据项计数（一篇论文可有多项）。", "",
            "| 采集位置 | 数据项 | 需要跨轮历史 | 需要干净参考 | 需要额外计算 |", "|---|---|---|---|---|"]
    for w in WHERE:
        f = flags[w]
        out.append(f"| {WHERE_CN[w]} | {f['n']} | {f['needs_history']} | {f['needs_clean_reference']} | {f['needs_extra_compute']} |")

    out += ["", "## 各采集位置的数据项清单", ""]
    for w in WHERE:
        out += [f"### {WHERE_CN[w]}", ""]
        for c in cards:
            items = [o for o in as_list(c.get("observables")) if isinstance(o, dict) and o.get("where") == w]
            for o in items:
                tags = [n for n, f in (("历史", "needs_history"), ("干净参考", "needs_clean_reference"),
                                       ("额外计算", "needs_extra_compute")) if o.get(f) is True]
                out.append(f"- `{c['key']}`（{c.get('setting', '?')}，{o.get('granularity', '?')}"
                           f"{'；' + '、'.join(tags) if tags else ''}）：{o.get('what', '')}")
        out.append("")

    adapt = [c["key"] for c in cards if c.get("evaluates_adaptive_attacker") is True]
    over = [c["key"] for c in cards if c.get("overhead_reported") is True]
    out += ["## 其他", "", f"- 评估了自适应攻击者的论文 {len(adapt)} 篇：" + "、".join(f"`{k}`" for k in adapt),
            f"- 报告了开销的论文 {len(over)} 篇：" + "、".join(f"`{k}`" for k in over), ""]
    (HERE / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"summary.md：{len(cards)} 张卡片")


if __name__ == "__main__":
    main()
