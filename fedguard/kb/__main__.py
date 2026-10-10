"""python -m fedguard.kb check | tables"""
from __future__ import annotations

import sys
from collections import defaultdict

from fedguard.kb import HERE, load, validate


def tables() -> str:
    kb = load()
    v = kb.vocabulary
    zh = lambda group, key: v[group][key]["zh"]  # noqa: E731
    impls_of = defaultdict(list)
    for i, e in kb.implementations.items():
        for d in [e["technique"], *e.get("also_serves", [])]:
            impls_of[d].append(i)
    best = lambda d: max((r["level"] for r in kb.relations if r["implementation"] in impls_of[d]), default=0)  # noqa: E731
    runnable = lambda d: [i for i in impls_of[d] if "class" in kb.implementations[i]]  # noqa: E731
    out = ["# 覆盖视图", "",
           f"由 `python -m fedguard.kb tables` 生成，不要手改。知识库内容版本 `{kb.content_version}`，格式版本 {v['format_version']}。",
           f"条目数：威胁技术 {len(kb.threats)}，防御技术 {len(kb.defenses)}，实现 {len(kb.implementations)}"
           f"（其中运行时还表达不了的 {sum(e['status'] == 'unsupported' for e in kb.implementations.values())}），"
           f"场景 {len(kb.scenarios)}，有证据的对抗关系 {len(kb.relations)}。", "",
           "证据等级：" + "；".join(f"{k} {x['zh']}" for k, x in v["evidence_levels"].items()) + "。", "",
           "## 1. 制品 × 战术", "",
           "格子里是防御技术的编号、可运行的实现数、以及它的实现里最高的证据等级。动作落在哪个制品上，就记在哪个制品的行里；只读不改的实现记在它读的制品上。"
           "等级 1 来自原论文对其完整方法的评测；本库的实现可能只实现了其中一部分（见各类的说明）。", ""]
    tactics = list(v["tactics"])
    out += ["| 制品 | " + " | ".join(zh("tactics", t) for t in tactics) + " |", "|---|" + "---|" * len(tactics)]
    for a, art in v["artifacts"].items():
        row = []
        for t in tactics:
            cell = []
            for d, e in kb.defenses.items():
                lands = any(a in kb.lands(i) for i in impls_of[d])
                reads_only = any(not kb.lands(i) and a in {c.split("/")[0] for c in kb.implementations[i].get("reads", [])}
                                 for i in runnable(d))
                if t in e["tactics"] and (lands or reads_only):
                    cell.append(f"{d}（{len(runnable(d))} 个，等级 {best(d)}）")
            row.append("<br>".join(cell) or "—")
        out.append(f"| {art['zh']} | " + " | ".join(row) + " |")
    out += ["", "## 2. 防御技术与实现", "",
            "| 技术 | 解决的问题 | 信任假设 | 外部资源 | 实现（状态；无攻击对照里测到的行为；完整程度） |", "|---|---|---|---|---|"]
    for d, e in kb.defenses.items():
        cells = []
        for i in impls_of[d]:
            x = kb.implementations[i]
            label = x.get("class") or x.get("title")
            acts = {True: "无攻击时也动作", False: "无攻击时不动作", None: ""}[kb.acts_without_attack(i)] if "class" in x else ""
            part = "；只实现了原方法的一部分" if "class" in x and kb.completeness(i) == "partial" else ""
            cells.append(f"{i} `{label}`（{zh('status', x['status'])}" + (f"；{acts}" if acts else "") + part + "）")
        out.append(f"| {d} {e['zh']} | {e['problem']} | {'、'.join(zh('trust', t) for t in e['trust'])} | "
                   f"{'、'.join(e['resources']) or '—'} | {'<br>'.join(cells)} |")
    out += ["", "## 3. 威胁技术 × 防御技术", "",
            "格子取该防御技术下各实现里最强的一项。数字是证据等级（1 到 4）。没有证据时显示制品上的联系："
            "`直` 表示防御直接读或改威胁改动的制品；`报` 表示防御读的坐标上有论文报告过该威胁的痕迹；"
            "`推` 表示这种痕迹只是按机制推断的；点表示没有交集。字母只说明值得试，不说明有效；"
            "痕迹来自 DeepSeek 对论文卡片的归纳，没有核实。", ""]
    ds = list(kb.defenses)
    out += ["| 威胁技术 | 目标 | 能力 | " + " | ".join(ds) + " |", "|---|---|---|" + "---|" * len(ds)]
    uncovered, rank, mark = [], {"direct": 3, "reported": 2, "inferred": 1}, {"direct": "直", "reported": "报", "inferred": "推"}
    for t, e in kb.threats.items():
        cand = kb.candidates(t)
        row, any_cand = [], False
        for d in ds:
            level = max((kb.evidence(i, t) for i in impls_of[d]), default=0)
            links = [cand[i] for i in impls_of[d] if i in cand]
            any_cand |= bool(links) or level > 0
            row.append(str(level) if level else mark[max(links, key=rank.get)] if links else "·")
        if not any_cand:
            uncovered.append(t)
        out.append(f"| {t} {e['zh']} | {'、'.join(zh('goals', g) for g in e['goal'])} | "
                   f"{'、'.join(e['capabilities'])} | " + " | ".join(row) + " |")
    out += ["", "## 4. 缺口", "", "### 4.1 没有任何防御技术落在上面的制品", ""]
    for a, art in v["artifacts"].items():
        if not any(set(art["modified_by"]) & set(e["acts"]) or a in e["reads"] for e in kb.defenses.values()):
            out.append(f"- {art['zh']}（`{a}`）")
    out += ["", "### 4.2 没有候选防御的威胁技术", ""] + ([f"- {t} {kb.threats[t]['zh']}" for t in uncovered] or ["- 无"])
    out += ["", "### 4.3 收录了但运行时表达不了的实现，按缺的能力归并", ""]
    need = defaultdict(list)
    for i, e in kb.implementations.items():
        if e["status"] == "unsupported":
            need[e["needs_runtime"]].append(f"{i} {e['title']}")
    out += [f"- `{k}`：" + "；".join(x) for k, x in sorted(need.items())] or ["- 无"]
    out += ["", "### 4.4 写了但入口没接上资源的实现", ""]
    out += [f"- {i} `{e['class']}`：{e['blocked_by']}" for i, e in kb.implementations.items() if e.get("blocked_by")] or ["- 无"]
    out += ["", "### 4.5 已知在默认参数下失效的实现", ""]
    out += [f"- {i} `{e['class']}`：{f}" for i, e in kb.implementations.items() for f in e.get("known_failures", [])] or ["- 无"]
    out += ["", "## 5. 无攻击对照", "",
            "场景里没有任何攻击，所以这里的排除、屏蔽、改写都是误伤。损失比是最后一轮客户端自报训练损失相对不挂干预插件那次运行的比值；"
            "训练样本被增删改过的运行，这个比值不可比。空格表示该项不适用。", ""]
    controls = [s for s, e in kb.scenarios.items() if not e["threats"]]
    res = {i: r for s in controls for i, r in (kb.scenarios[s].get("results") or {}).items()}
    cols = [("client_rounds_excluded", "被排除的客户端轮次"), ("weight_shift", "聚合权重偏移"), ("samples_masked", "被屏蔽的样本"),
            ("samples_rewritten", "被改写的样本"), ("samples_added", "增补的样本"), ("gradient_norm_ratio", "梯度范数比"),
            ("updates_transformed", "改写更新次数"), ("global_replaced", "替换全局次数"), ("loss_vs_baseline", "损失比")]
    out += ["| 实现 | " + " | ".join(c for _, c in cols) + " |", "|---|" + "---|" * len(cols)]
    pct = {"client_rounds_excluded", "samples_masked", "samples_rewritten", "samples_added"}
    for i, r in res.items():
        cells = ["" if r.get(k) in (None, 0, 0.0) and k != "loss_vs_baseline" else (f"{r[k]:.0%}" if k in pct else str(r.get(k, ""))) for k, _ in cols]
        out.append(f"| {i} `{kb.implementations[i]['class']}` | " + " | ".join(cells) + " |")
    todo = [f"{i} `{e['class']}`" for i, e in kb.implementations.items() if "class" in e and i not in res]
    out += ["", "还没有无攻击对照的实现：" + ("、".join(todo) if todo else "无")]
    from fedguard.kb.opsuse import usage
    u = usage()
    by_class = {c: info["ops"] for c, info in u["classes"].items()}
    registered = {e["class"]: i for i, e in kb.implementations.items() if "class" in e}
    out += ["", "## 6. 算子的复用", "",
            "由源码静态分析生成。算子留在算子库里的理由只有两个：是 LoRA 特有的计算，或者被两个以上的方法共用。"
            "只有一个使用者的通用算子是待观察的；这张表用来在加新算子或新方法时核对这条规则。", "",
            f"算子 {len(u['operators'])} 个：被 3 个及以上插件类调用的 {sum(len(x) >= 3 for x in u['operators'].values())} 个，"
            f"2 个的 {sum(len(x) == 2 for x in u['operators'].values())} 个，1 个的 {sum(len(x) == 1 for x in u['operators'].values())} 个，"
            f"不被插件类直接调用的 {sum(not x for x in u['operators'].values())} 个（被别的算子、适配器或实验脚本使用）。", "",
            "| 算子 | 使用它的插件类 |", "|---|---|"]
    out += [f"| `{o}` | {'、'.join(x) or '—'} |" for o, x in sorted(u["operators"].items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    none = [f"{registered[c]} `{c}`" for c, ops in sorted(by_class.items()) if c in registered and not ops]
    out += ["", "不调用任何算子的已登记实现：" + ("、".join(none) or "无")]
    read = {c for e in kb.implementations.values() for c in e.get("reads", [])}
    out += ["", "## 7. 运行时提供、但没有已登记实现在读的坐标", "",
            "这些数据运行时给得出来，只是目前登记的方法没有用到（内置的统计与探针插件未登记为实现）。", ""]
    out += [f"- `{c}`：{x['zh']}" for c, x in v["coordinates"].items() if c not in read]
    from fedguard.adapters import hosts
    zh_level = {"native": "原生", "glue": "应用配合", "extension": "需扩展层", "patch": "改脚本", None: "挂不上"}
    out += ["", "## 8. 在各宿主框架上能挂到什么程度", "",
            "库挂在现有的联邦微调框架上，自己不跑训练。原生：只用宿主自己的扩展点，宿主和应用代码都不改；"
            "应用配合：应用自己的训练函数里要调用本库；需扩展层：要启用本库的一层扩展适配，它改变了宿主的原有流程，启用时会有警告；"
            "改脚本：宿主没有扩展点，要在它的训练脚本里加调用。"
            "这张表来自各适配器的声明（`fedguard/adapters/hosts.py`），适配器挂载时按它拒绝宿主跑不了的插件。"
            "各宿主在真实模型上核对过什么，见 `fedguard/README.md` 的宿主一节。", "", hosts.support_table(), "",
            "| 实现 | " + " | ".join(h.title for h in hosts.HOSTS.values()) + " |", "|---|" + "---|" * len(hosts.HOSTS)]
    for i, e in kb.implementations.items():
        if "class" in e:
            out.append(f"| {i} `{e['class']}` | " + " | ".join(
                zh_level[hosts.mount_level(kb.plugin(i), h)] + "".join(f"（扩展层 `{x}`）" for x in hosts.needed_extensions(kb.plugin(i), h))
                for h in hosts.HOSTS.values()) + " |")
    return "\n".join(out) + "\n"


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        problems = validate(load(check=False))
        print("\n".join(problems) or "knowledge base is consistent")
        return 1 if problems else 0
    if cmd == "tables":
        (HERE / "generated").mkdir(exist_ok=True)
        (HERE / "generated" / "coverage.md").write_text(tables(), encoding="utf-8")
        print(HERE / "generated" / "coverage.md")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
