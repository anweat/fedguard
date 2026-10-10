"""The catalogue of the published methods shipped as plugins, generated from what the code declares.

    python -m fedguard.methods            # print it
    python -m fedguard.methods write      # write fedguard/methods/CATALOG.md (do not edit that file by hand)

Every column is read from a declaration: stages, data kinds, resources and actions from the plugin
class; the paper, the status and the pairing from the knowledge base entry; the mounting level from the
host profiles; what is implemented and what deviates from the class docstring.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fedguard.adapters import hosts
from fedguard.core.types import Stage, side_of
from fedguard.kb import load
from fedguard.methods import METHODS

LEVEL = {"native": "原生", "glue": "应用配合", "extension": "扩展层", "patch": "改脚本", None: "不支持"}
STATUS = {"experimental": "只有单元测试", "tested": "真实模型上跑通", "stable": "已校准", "deprecated": "已替代"}
SECTION = {"implemented": "实现了", "deviations": "与原文不同", "not_implemented": "没有实现", "open_choices": "原文未定、此处的选择",
           "cost": "开销"}


def mounting(cls, host) -> str:
    ext = hosts.needed_extensions(cls, host)
    return LEVEL[hosts.mount_level(cls, host)] + (f"；需扩展层 `{'`、`'.join(ext)}`" if ext and hosts.mount_level(cls, host) != "extension"
                                                  else f" `{'`、`'.join(ext)}`" if ext else "")


def catalog() -> str:
    kb = load()
    by_class = {e["class"]: (i, e) for i, e in kb.implementations.items() if "class" in e}
    names = sorted(METHODS, key=lambda n: (side_of(METHODS[n]().stages[0]) != "server", by_class[n][0]))
    code = lambda xs: "、".join(f"`{x}`" for x in sorted(xs)) or "—"  # noqa: E731
    out = ["# 已移植的论文方法", "",
           "由 `python -m fedguard.methods write` 从代码里的声明生成，不要手改。",
           f"共 {len(names)} 个插件。它们是这个库的示例和测试用例：每个都写明实现了论文的哪些步骤、哪些没有、哪些是我们自己的选择；"
           "都没有对照过原作者的代码，也没有复现过论文的数值。", "",
           "| 插件 | 条目 | 论文 | 侧 | 位置 | 读 | 外部资源 | 动作 | " + " | ".join(h.title for h in hosts.HOSTS.values()) + " | 状态 | 完整度 |",
           "|---|---|---|---|---|---|---|---|" + "---|" * len(hosts.HOSTS) + "---|---|"]
    for n in names:
        cls, (i, e) = METHODS[n], by_class[n]
        stages = cls().stages
        pair = f"（与 `{'`、`'.join(kb.implementations[p]['class'] for p in e['pairs_with'])}` 配对）" if e.get("pairs_with") else ""
        out.append(f"| `{n}`{pair} | {i} | {code(e['sources'])} | {'服务器' if side_of(stages[0]) == 'server' else '客户端'} | "
                   f"{'、'.join(f'`{s.name}`' for s in Stage if s in stages)} | {code(cls.needs)} | {code(cls.resources)} | {code(cls.acts)} | "
                   + " | ".join(mounting(cls, h) for h in hosts.HOSTS.values())
                   + f" | {STATUS[e['status']]}{'；受阻：' + e['blocked_by'] if e.get('blocked_by') else ''} | "
                   f"{'部分' if kb.completeness(i) == 'partial' else '完整'} |")
    out += ["", "列的含义：", "",
            "- 位置、读、外部资源、动作：插件类的声明；运行器在第一轮之前按它们检查，声明之外的数据读不到。",
            "- 宿主两列：在该宿主上挂这个插件的最高代价。原生＝只用宿主自己的扩展点；应用配合＝应用的训练函数要调用本库；"
            "改脚本＝宿主没有扩展点，要改它的训练脚本；扩展层＝要启用本库的一层扩展适配，**那不是宿主原版的行为**，启用时有警告并写入记录。",
            "- 状态：知识库条目的状态。完整度为“部分”表示类说明里有“没有实现”的步骤。",
            "- 论文一列是文献键，对应 `survey/paper_index.md`。", "",
            "## 逐个说明", "", "以下各节摘自类说明（`fedguard/methods/*.py`），原文是英文。", ""]
    for n in names:
        cls, (i, e) = METHODS[n], by_class[n]
        doc = kb.describe(i)["doc"]
        out += [f"### `{n}`（{cls.__name__}，{cls.__module__.rsplit('.', 1)[1]}.py）", "", doc["summary"], ""]
        out += [f"- **{SECTION[k]}**：{doc[k]}" for k in SECTION if doc.get(k)]
        if e.get("known_failures"):
            out += [f"- **已知问题**：{'；'.join(e['known_failures'])}"]
        params = kb.describe(i)["params"]
        out += [f"- **参数与默认值**：{'，'.join(f'`{k}={v!r}`' for k, v in params.items()) or '无'}", ""]
    out += ["## 怎么试", "",
            "推荐的方式是写一份控制策略文件（`fedguard/policy.py`，示例在 `integrations/policies/`），三个入口都接受："
            "实验入口与接入示例用 `--guard_policy 文件`，Flower 应用用 `FG_POLICY=文件`。`python -m fedguard.policy 文件` 会列出它挂了什么、每个宿主上各需要什么。",
            "下表是按名字启用的旧参数，仍然可用（内部转成一份策略）；可以同时启用多个，逗号分隔，按书写顺序运行。", "",
            "| 宿主 | 入口 | 服务器侧插件 | 客户端侧插件 | 让插件动作 | 训练器扩展层 |",
            "|---|---|---|---|---|---|",
            "| FedLLM-Attack（实验入口，能提供表中全部外部资源，`alignment` 除外） | `experiments/fedllm_attack/run_guarded.py` | `--guard_modules a,b` | "
            "`--guard_client_modules a,b` | 服务器侧总是动作；客户端侧 `--guard_client_apply 1` | `--guard_trainer_ext 1` |",
            "| OpenFedLLM 原版、FedLLM-Attack（最小接入示例，不提供外部资源） | `integrations/<宿主>/main_sft_guard.py` | 同上 | 同上 | `--guard_apply 1` | "
            "`--guard_trainer_ext 1` |",
            "| Flower | `experiments/flower/sim_llm.py <输出目录> guard` | `FG_SERVER=a,b` | `FG_CLIENT=a,b` | `FG_APPLY=1` | `FG_TRAINER_EXT=1`；握手 `FG_HANDSHAKE=1` |",
            "", "批量：`experiments/fedllm_attack/methods_sweep.sh` 对每个方法各跑一次短的联邦训练（`ONLY=\"krum lisa\"` 只跑其中几个，"
            "`SCENARIO=control` 为全部良性客户端）；`experiments/flower/llm_check.sh` 与 `integrations/check_plugins.sh` 在另外两个宿主上成组地跑。",
            "这些运行只回答“挂得上、跑得动、是否动作”，轮数远小于论文，不说明防御效果。",
            "不训练模型的检查：`tests/test_methods_*.py`（各方法的机制）、`tests/test_methods_together.py`（同时启用与单独启用的输出相同）、"
            "`tests/test_trainer_ext.py`（扩展层）。", ""]
    return "\n".join(out)


def main() -> int:
    text = catalog()
    if sys.argv[1:] == ["write"]:
        path = Path(__file__).resolve().parent / "CATALOG.md"
        path.write_text(text, encoding="utf-8")
        print(path)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
