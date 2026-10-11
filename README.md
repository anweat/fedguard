# fedguard

fedguard 是面向联邦大模型 LoRA 微调的训练期安全基线框架。它以附加库的形式挂载在现有的联邦微调框架上，
在一轮训练的固定控制点上采集训练制品、运行检测与缓解控制、执行处置动作，并生成可核对的审计记录。
训练、聚合与通信仍由宿主框架完成，fedguard 不实现训练流程。

当前支持的宿主：Flower（Message API）、OpenFedLLM 及与其同构的训练脚本（如 FedLLM-Attack）。

> 使用前请阅读 [`NOTICE.md`](NOTICE.md)。fedguard 提供的是基线防护，不是完备防御；
> 库中移植的防御方法未与原作者的实现对照，本仓库不对任何防御的效果作出声明。

## 功能

| 功能 | 说明 |
|---|---|
| 控制点 | 一轮训练中 11 个位于信任边界上的固定位置：下发、训练前握手、本地训练前、训练步内（反向传播前、优化器更新前、更新后）、上传前、接收上传、聚合、聚合后 |
| 遥测 | 各控制点上可观测的训练制品：LoRA 更新、梯度、损失、样本表示、客户端自报值。按最小权限提供，控制只能读取其声明的数据类别 |
| 安全控制 | 检测类与缓解类插件。控制只提出处置动作，是否执行由策略决定，默认只告警 |
| 控制策略 | 以 YAML 文件声明一次部署所用的控制、参数、处置是否生效及所依赖的扩展层。策略与宿主无关，其内容摘要写入运行记录 |
| 审计记录 | 记录经手对象的内容哈希、各控制的输出与处置动作，轮次之间以哈希链相连。服务器与客户端的记录可事后对照，可在不重新训练的情况下重放 |
| 宿主适配 | 各宿主在每个控制点上的支持程度以数据形式声明，挂载时据此拒绝宿主无法承载的控制 |
| 威胁与控制映射 | 以数据形式登记威胁技术、防御技术、实现及其证据等级，并与代码中的声明双向校验 |

仓库随库提供 29 个由已发表防御方法移植而来的控制和 11 个内置控制，清单见
[`fedguard/methods/CATALOG.md`](fedguard/methods/CATALOG.md)。

## 架构

```
宿主框架 ── 适配器 ── 运行器 ── 控制点 ──→ 向控制提供其声明的数据 → 控制提出动作 → 按策略执行 → 写入记录
(Flower /   (宿主能力表)  (契约检查、调度、           ↑
 训练脚本)                 决定合并)              控制策略文件
```

| 组成 | 职责 | 位置 |
|---|---|---|
| 控制（插件） | 定义一个控制：运行位置、读取的数据、所需外部资源、可提出的动作及其算法 | `fedguard/plugins/`、`fedguard/methods/` |
| 控制策略 | 定义一次部署：启用哪些控制、参数、处置是否生效 | `fedguard/policy.py`、`integrations/policies/` |
| 运行内核 | 校验声明、策略与宿主能力是否相互成立；调度控制、执行动作、合并决定、写入记录 | `fedguard/core/`、`fedguard/views/`、`fedguard/recorder/` |
| 宿主适配 | 将内核接入具体的联邦框架 | `fedguard/adapters/` |
| 挂载方（应用） | 提供宿主、模型、数据与外部资源的内容 | 用户代码；示例见 `integrations/`、`experiments/flower/` |
| 知识库 | 登记威胁与控制的对应关系、证据与已知问题；不参与运行 | `fedguard/kb/` |

各部分的详细说明与职责边界见 [`fedguard/README.md`](fedguard/README.md)。

## 宿主支持

| 控制点 | Flower | OpenFedLLM 系脚本 |
|---|---|---|
| 服务器侧：下发、接收上传、聚合、聚合后 | 原生支持 | 需在训练脚本中加入调用 |
| 客户端：本地训练前、上传前 | 原生支持 | 需在训练脚本中加入调用 |
| 客户端：优化器更新前、更新后 | 需应用的训练函数配合 | 需在训练脚本中加入调用 |
| 训练前握手（客户端与服务器往返一次） | 需启用扩展层 `handshake` | 需在训练脚本中加入调用 |
| 客户端：反向传播前（读取与替换损失） | 需启用扩展层 `trainer` | 需启用扩展层 `trainer` |

扩展层用于提供宿主自身不具备的能力，会改变宿主的原有行为，默认关闭；启用时发出 `HostExtensionWarning` 并写入运行记录。
完整的支持表由 `python -m fedguard.adapters.hosts` 输出。OpenFedLLM 系脚本的接入步骤见
[`fedguard/adapters/OPENFEDLLM.md`](fedguard/adapters/OPENFEDLLM.md)。

## 安装

需要 Python 3.11。仓库提供两套依赖环境：`fl311`（transformers 4.53）与 `q35`（transformers 5.x，用于 Qwen3.5 系列模型）。

```bash
FG_ENV=fl311 bash envs/setup_linux_cuda.sh        # Linux 与 NVIDIA 显卡；其他平台见 envs/README.md
envs/fl311/.venv/bin/python -m pytest tests -q    # 单元测试，不需要模型权重
```

上游框架不随仓库分发，版本见 [`external/UPSTREAM.md`](external/UPSTREAM.md)。

## 使用

编写控制策略：

```yaml
policy: 1
server:
  controls:
    - effect_stats                                        # 只观察
    - {use: norm_clip, enforce: true}                     # 处置生效
    - {use: krum, args: {f: 1, m: 3}}                     # 只告警
```

在 Flower 上挂载（服务器侧）：

```python
from fedguard import RunSpec
from fedguard.adapters.flower import GuardStrategy
from fedguard.policy import Policy
from fedguard.recorder.store import Recorder

policy = Policy.load("policy.yaml")
recorder = Recorder("records", run_id)
runner = policy.runner("server", RunSpec(run_id, lora_scale=alpha / r), recorder)
strategy = GuardStrategy(FedAvg(...), runner, recorder)   # 包装应用原有的策略
```

查看一份策略挂载的控制及其在各宿主上的要求：

```bash
python -m fedguard.policy integrations/policies/baseline.yaml
```

客户端侧、脚本宿主、训练步内的控制与扩展层的用法见 [`fedguard/README.md`](fedguard/README.md)。
`experiments/flower/sim_llm.py` 是一个完整的 Flower 应用示例，设置 `FG_MODEL=tiny` 可在不下载模型的情况下运行。

## 验证

以下性质在真实模型上核对，全部使用良性数据。模型为 Qwen2.5-0.5B 与 Qwen3.5-0.8B，部分运行使用 Qwen3.5-4B。

| 性质 | OpenFedLLM | FedLLM-Attack | Flower |
|---|---|---|---|
| 挂载但不运行控制时，训练结果与宿主单独运行逐位相同 | 通过 | 通过 | 通过（在 CPU 上比较） |
| 控制只告警时，训练结果逐位相同 | 通过 | 通过 | 通过（核对了一种情形：扩展层 `trainer` 启用、一个步内控制只告警） |
| 控制运行并执行处置 | 通过 | 通过（28 个移植的控制各一次短训练） | 通过 |
| 训练前握手 | 通过 | 通过 | 通过（经扩展层） |
| 训练步内替换损失与梯度 | 未核对 | 通过（经扩展层） | 通过（经扩展层） |
| 采集开销 | 未测 | 训练时间的 0.7% 至 2.8% | 未测 |

这些核对说明控制可以挂载、运行且不改变训练，不说明任何防御的效果。各次运行的摘要见 `results/autodl/`。
单元测试共 185 个，覆盖契约检查、各控制的机制、控制并行启用的一致性、分层约束与生成文档的时效。

## 仓库结构

| 目录 | 内容 |
|---|---|
| `fedguard/` | 库 |
| `tests/` | 单元测试 |
| `integrations/` | 脚本宿主的接入示例及其生成器、逐位核对脚本、示例策略 |
| `experiments/` | 实验驱动：各宿主上的核对脚本、控制的批量短训练、无攻击对照、算力编排 |
| `results/` | 真实模型运行的文字摘要 |
| `survey/` | 文献整理：检索与分类脚本、论文卡片、防御方法的逐步拆解、控制的移植成本测量 |
| `output/poisoning_study/` | 按日期排列的设计与结果记录 |
| `envs/` | 依赖环境 |
| `external/` | 上游框架的版本记录（代码不入库） |

## 开发状态

当前版本为研究原型。已完成、进行中与未开始的工作见 [`PROGRESS.md`](PROGRESS.md)。

## 限制

- 不评测防御效果，不包含新的攻击方法。
- 移植的控制依据论文描述实现，未与原作者的代码逐一对照，默认参数未针对 LoRA 校准。
- 同一进程内的数据访问限制用于防止误用，不能阻止蓄意越界的插件。
- 不提供代码完整性度量或远程证明。
- 策略中的处置开关以控制为单位，不能对同一控制的不同动作分别设置。

## 许可与声明

代码以 Apache License 2.0 发布，见 [`LICENSE`](LICENSE)。
对上游框架的非原版修改、文献材料与机器生成内容的性质、与攻击有关内容的用途限制，见 [`NOTICE.md`](NOTICE.md)。
