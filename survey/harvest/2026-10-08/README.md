# 2026-10-08 调研：投毒攻防文献与研究基座

目的：在确定 fedguard 的"采集底座 + 插件机制"之前，对照已有研究检验设计。由两个子代理完成，主会话抽查了依据。

| 文件 | 内容 |
|---|---|
| `requirements.md` | 攻击入口表（21 类）、防御需求表（23 类）、对设计的五条检验、未覆盖与不确定。120 篇中 39 篇读到方法层面，其余只读摘要，逐条有标记 |
| `platforms.md` | 20 多个攻防平台、联邦大模型框架、后门基准、溯源工具的对比：攻防怎么抽象、扩展要改哪里、有没有记录与重放；共性、空白、对设计的含义。每条带核实等级 |
| `harvest.py`、`classify.py`、`build_reading_list.py` | 批量采集（OpenAlex；arXiv API 当时限流未取到）、粗分类、精读清单 |
| `papers.jsonl` | 去重后 3203 篇的元数据与摘要（其中 52 篇已在原文献库） |
| `classified.csv`、`reading_list.csv`、`harvest_log.md` | 粗分类结果、精读登记、采集日志 |

局限见两份文档各自的最后一节。主要有：arXiv 未取到；`[HTML]` 和 B 级条目来自工具的摘要式提炼，数字以原文为准；传统图像联邦学习的结论不作为大模型/LoRA 的证据。

## 全文精读（`deepread/`，同日追加）

用 DeepSeek Harness 桌面端自带的无界面入口，对 137 篇全文逐篇生成结构化精读卡片（原文献库 98 篇，加本轮从 arXiv 补下的 39 篇）。

| 文件 | 内容 |
|---|---|
| `deepread/<key>.md` | 精读卡片：威胁模型、攻击入口、所需数据与采集位置、干预动作、假设与局限、原文引句；末尾有机器可读的 JSON 块。`ax` 开头的是本轮补下的 arXiv 全文 |
| `deepread/run_deepread.py`、`dsh_patch.yml` | 调用方式与模型设置（`dsh --profile headless`，只读权限，全文经标准输入传入） |
| `deepread/fetch_fulltext.py`、`fulltext_manifest.json` | 补下全文的脚本与登记（来源、页数、SHA-256、标题核对） |
| `deepread/check_cards.py`、`quote_check.md`、`cards.jsonl` | 引句与全文的逐字比对：1371 条中 1314 条完全匹配、21 条近似、36 条未匹配 |
| `deepread/summarize_cards.py`、`summary.md` | 按场景、攻击入口、采集位置、粒度、干预动作的计数与清单 |

局限：卡片由模型生成，只有引句做了机械核对；计数来自模型填写的枚举值；清单里另有 21 篇非 arXiv 条目仍是摘要级。据此写的设计稿见 `output/poisoning_study/2026-10-08_fedguard整体设计-定位与采集面.md`。

## 算子流水线提取（`opsread/`，2026-10-09）

用同一个 DeepSeek 入口，把 47 篇防御与检测论文的方法逐篇拆成算子流水线（步骤、输入输出、公式、超参数、采样、
外部资源、论文未说明之处），供 `fedguard/ops` 与 `fedguard/methods` 对照实现。16 路并发，无失败。

| 文件 | 内容 |
|---|---|
| `opsread/<key>.md` | 逐篇提取，末尾有机器可读的 JSON 块 |
| `opsread/run_opsread.py` | 提取脚本（复用 `deepread/run_deepread.py` 的调用方式） |
| `opsread/quote_check.md`、`cards.jsonl` | 引句核对：376 条中 353 条逐字匹配、7 条近似、15 条未匹配、1 条过短 |

局限同上：只有引句做了机械核对，步骤与参数的转述没有逐条对照原文。
