# fedguard

面向联邦大模型 LoRA 微调的**训练期安全基线框架**。它以附加库的形式挂在现有的联邦微调框架上（Flower、OpenFedLLM 一类的训练脚本），
自己不跑训练：训练、聚合、通信都由宿主框架完成，fedguard 在一轮训练的固定控制点上取数据、运行检测与缓解控制、执行处置动作、留下审计记录。

这个仓库包含库本身、它在三个宿主上的接入与核对、相关的文献整理，以及"把已发表的防御方法搬到这个库上要付出多少"的一组测量。

> 使用前请先读 [`NOTICE.md`](NOTICE.md)。要点：这是基线防护，不是完备防御；库里移植的方法没有与原作者的实现对照过；
> 真实模型上的核对只说明"挂得上、跑得动、不改变训练"，不说明防御效果。

## 它提供什么

| | 内容 | 位置 |
|---|---|---|
| 控制点 | 一轮训练中 11 个位于信任边界上的固定位置：下发、训练前握手、本地训练前、训练步内三处、上传前、收到上传、聚合、聚合后 | `fedguard/core/types.py` |
| 遥测 | 各控制点上可观测的训练制品（LoRA 更新、梯度、损失、样本表示、自报值），按最小权限提供：插件只读得到它声明过的类别 | `fedguard/views/` |
| 可插拔的安全控制 | 检测类与缓解类插件。默认只告警，处置动作要显式启用。29 个已发表的防御方法以插件形式移植，另有 11 个内置插件 | `fedguard/methods/`、`fedguard/plugins/` |
| 控制策略 | 一份 YAML 写明一次部署用哪些控制、参数、谁的处置动作生效、依赖哪些扩展层；同一份策略可以换宿主，内容摘要写进运行记录 | `fedguard/policy.py`、`integrations/policies/` |
| 审计记录 | 经手对象的内容哈希、每个控制的输出与处置动作、轮与轮之间的哈希链；两侧记录可以事后对照，可以不重新训练就重放 | `fedguard/recorder/`、`fedguard/replay.py` |
| 宿主适配 | Flower（策略包装与客户端 Mod，不改宿主代码）、OpenFedLLM 系脚本（在训练脚本里加调用）；每个宿主在每个控制点上能做到什么是一张表，挂载时按表拒绝做不到的 | `fedguard/adapters/` |
| 威胁与控制映射 | 16 个威胁技术、17 个防御技术、40 个实现及其证据等级，以数据形式登记并与代码双向校验 | `fedguard/kb/` |

库的完整说明在 [`fedguard/README.md`](fedguard/README.md)，其中"职责边界"一节说明插件、策略文件、挂载方和库各管什么。
已移植方法的清单（位置、读的数据、外部资源、动作、在各宿主上的挂载代价、与原文的差异）在 [`fedguard/methods/CATALOG.md`](fedguard/methods/CATALOG.md)。

## 核对过的性质

全部用良性数据，在真实模型上（Qwen2.5-0.5B、Qwen3.5-0.8B，个别在 Qwen3.5-4B）：

| 性质 | OpenFedLLM | FedLLM-Attack | Flower |
|---|---|---|---|
| 挂上库但不运行控制，训练结果与宿主自己跑逐位相同 | 是 | 是 | 是（CPU 上比较） |
| 挂了控制但只告警，结果仍逐位相同 | 是 | 是 | 一种情形：训练器扩展层开着、一个步内控制只告警（CPU 上比较） |
| 控制在真实模型上运行并执行处置 | 是 | 是（28 个方法各一次短训练） | 是 |
| 训练前握手（ProtegoFed） | 是 | 是 | 经扩展层 |
| 训练步内改损失（Lisa、逐样本裁剪的 LA-LoRA） | — | 经扩展层 | 经扩展层 |
| 采集开销 | — | 训练时间的 0.7% 到 2.8% | 未测 |

代码在 2026-10-11 做过一次内部整理（动作登记表、插件状态作用域、方法重新分组、控制策略文件接入三个入口）。整理之后在 Qwen3.5-0.8B 上重新核对过：
两个脚本宿主的逐位比较、OpenFedLLM 上的插件运行、Flower 上的 10 项检查（含逐位比较）、12 个方法各一次短训练全部通过；
用旧的命令行参数和等价的策略文件各跑一次，两者挂载的控制、策略摘要和剔除结果相同（`results/autodl/refit-q35/`）。

各次运行的文字摘要在 `results/autodl/`。单元测试 185 个，不需要真实模型：

```bash
FG_ENV=fl311 bash envs/setup_linux_cuda.sh   # Linux 加 NVIDIA 显卡；其他平台按 envs/README.md 建环境
envs/fl311/.venv/bin/python -m pytest tests -q
python -m fedguard.kb check                  # 知识库与插件声明是否一致
python -m fedguard.policy integrations/policies/baseline.yaml    # 一份策略挂了什么、每个宿主上各需要什么
```

## 最小用法

```python
from fedguard import RunSpec
from fedguard.adapters.flower import GuardStrategy
from fedguard.policy import Policy
from fedguard.recorder.store import Recorder

policy = Policy.load("integrations/policies/baseline.yaml")
recorder = Recorder("records", run_id)
runner = policy.runner("server", RunSpec(run_id, lora_scale=alpha / r), recorder)
strategy = GuardStrategy(FedAvg(...), runner, recorder)        # 包住应用原来的策略
```

客户端一侧、单进程脚本宿主、训练步内的控制和扩展层的用法，见 [`fedguard/README.md`](fedguard/README.md) 的"接入训练"与 [`fedguard/adapters/OPENFEDLLM.md`](fedguard/adapters/OPENFEDLLM.md)。
`experiments/flower/sim_llm.py` 是一个完整的 Flower 应用示例，用 `FG_MODEL=tiny` 可以不下载模型就跑通。

## 目录

| 目录 | 内容 |
|---|---|
| `fedguard/` | 库：`core/`（控制点、契约、运行器、动作）、`views/`、`recorder/`、`adapters/`、`ops/`（LoRA 计算与共用算子）、`policy.py`、`plugins/`、`methods/`、`kb/` |
| `tests/` | 单元测试，含分层检查、方法并行启用的一致性、生成文档是否最新 |
| `integrations/` | 两个脚本宿主的接入示例与生成器、逐位核对脚本、示例策略 |
| `experiments/` | 实验驱动：三个宿主上的检查脚本、方法的批量短训练、无攻击对照、算力编排 |
| `results/` | 真实模型运行的文字摘要（状态、各控制的调用与动作统计、对照读数） |
| `survey/` | 文献整理：检索与分类脚本、论文卡片、方法的逐步拆解、威胁条目的草稿、与同类安全框架的对照 |
| `survey/harvest/2026-10-11/porting/` | 移植成本测量：给语言模型的移植说明、批量脚本、24 篇论文的移植结果与汇总 |
| `output/poisoning_study/` | 按日期排列的设计与结果记录，从早期的检测预实验到库的历次调整 |
| `envs/` | 两套依赖环境（`fl311`：transformers 4.53；`q35`：transformers 5.x，用于 Qwen3.5） |
| `external/` | 上游框架不入库，版本记在 `external/UPSTREAM.md` |

## 主要发现

工程上：

- 在三个宿主上，挂载本库不改变训练结果（逐位），采集开销为训练时间的 1% 到 3%。
- 把"处置是否生效"交给策略而不是插件，并且不让插件知道自己是否被启用，使同一个控制可以先只告警地观察、再决定是否处置。
- 宿主做不到的能力用显式的扩展层补，并在记录里标记，而不是悄悄改掉宿主的行为。

关于"通用防御库"能做到哪一步（[`survey/harvest/2026-10-11/porting/summary.md`](survey/harvest/2026-10-11/porting/summary.md)）：

- 让语言模型按统一说明移植 24 篇论文的方法，没有一篇能完整搬进来。贴近训练期更新与样本的方法能搬大半；其余卡在方法自成系统：自己的协议、自己维护的状态、离线训练的部件。
- 所以库应当做好的是**提取接口**，而不是收编整套系统：把那套系统需要的数据在控制点上取出来、把它的决定带回训练，系统自己的状态留在库外。
  第一轮测量暴露的提取缺口（逐词元状态、基座权重的梯度、批内样本身份等）补齐后，两篇原先"表达不了"的方法变成可以移植大半。
- 无攻击的对照显示，多种经典稳健聚合和样本过滤方法按论文参数搬到 LoRA 上时，在没有任何攻击的情况下也会大量处置（剔除客户端、改写样本），这些读数记在知识库各实现的"已知问题"里。

## 没有做的

- 没有评测任何防御的效果，没有构造新的攻击，没有对齐论文规模的实验。早期的检测预实验（`output/poisoning_study/` 里 P1 到 P3）规模很小，只能当作线索。
- 移植的方法没有与原作者的代码对照。
- 没有硬件信任根下的完整性证明；库自身不防存心越界的插件。

## 许可与声明

代码以 Apache License 2.0 发布，见 [`LICENSE`](LICENSE)。对上游框架的非原版修改、文献材料与机器生成内容的性质、与攻击有关的内容的用途限制，见 [`NOTICE.md`](NOTICE.md)。
