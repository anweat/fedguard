# fedguard

面向联邦大模型 LoRA 微调的**训练期安全基线框架**，以附加库的形式挂在现有联邦微调框架上。它自己不跑训练：训练、聚合、通信都是宿主框架的，
库通过宿主的扩展点（或在没有扩展点时通过改它的脚本）在固定位置上取数据、跑插件、执行动作、留记录。

用安全工程的说法，它提供四样东西：

- **控制点**：在一轮训练中各个信任边界上的固定位置（下发、本地训练前、训练步内、上传、聚合前后），检测与缓解控制在这里挂载；
- **遥测**：各控制点上可观测的训练制品（更新、梯度、样本表示、自报值），按最小权限提供，插件只能读它声明过的类别；
- **可插拔的安全控制**：检测类与缓解类插件，默认只告警不处置，处置动作需显式启用；已发表的防御方法以插件形式接入，方法自身的状态与离线部件作为可信参考制品由外部提供；
- **审计记录**：经手对象的内容哈希、每个控制的输出与处置动作，可事后核对两侧记录、可重放。

**安全声明的范围。** 本库提供的是基线防护，是纵深防御中的一层，不是完备防御：它不声称覆盖全部投毒攻击面，
不保证对自适应攻击者的鲁棒性；每个控制对哪些威胁有证据、证据到哪一级，由知识库的威胁与控制映射给出，未覆盖的部分是需要另行处置的残余风险。

| 部分 | 目录 | 做什么 |
|---|---|---|
| 宿主适配 | `adapters/` | 把库接到宿主上：Flower 的策略包装与客户端 Mod、OpenFedLLM 系脚本的调用点、HF 训练器回调、HF 模型句柄；两个默认关闭的扩展层（Flower 握手、训练器损失钩子）。每个宿主能挂到什么程度见下面"宿主" |
| 运行内核 | `core/`、`views/`、`recorder/`、`client.py`、`replay.py` | 与宿主无关：按位置调度插件，按声明给数据，记录经手的对象、插件的输出、提出的动作和花掉的模型开销。每种动作在 `core/actions.py` 里登记一次 |
| 控制策略 | `policy.py` | 把一组同时启用的控制写成一份文件：两侧的控制、参数、谁的动作生效、依赖的扩展层 |
| LoRA 计算与共用算子 | `ops/` | LoRA 特有的计算（不展开乘积的内积与奇异值、因子与乘积两种视角），以及被两个以上方法共用的通用计算 |
| 知识库 | `kb/` | 威胁与防御按制品登记，实现与证据分开，覆盖视图由数据生成 |
| 示例插件 | `plugins/`、`methods/` | 演示契约的内置插件；已移植的论文方法（清单见 `methods/CATALOG.md`） |

各层只向下依赖：`adapters` → `client`、`replay` → `core` → `views`、`recorder` → `ops`（`core/types.py` 是各层共用的词汇）；
`methods`、`plugins` 只依赖 `core` 与 `ops`；`kb` 读它们的声明。宿主框架和 transformers 只在 `adapters/` 里被导入。
这两条由 `tests/test_architecture.py` 按导入语句检查，同一个测试还要求每个模块和公开类都有说明。

`methods/` 里的已发表防御是**示例和测试用例**，数量不追求增长，也不以"能表达多少篇论文"衡量这个库。
一篇论文表达不了，记录的是宿主或内核缺什么（见知识库的缺口清单），而不是一项待移植的任务。
衡量这个库的是：接入一个宿主要改多少东西、挂上之后训练结果是否逐位不变、开销多少、契约能否拦住错误用法。
批量运行、无攻击对照、算力编排是我们自己的实验工具，在 `experiments/` 下，不属于库。

## 职责边界

运行时有四方，各管一件事。知识库是第五样东西，但它不参与运行。

| 谁 | 负责 | 不负责（也做不到） |
|---|---|---|
| **插件**（`plugins/`、`methods/`，或你自己的类） | 一个控制**是什么**：在哪个位置运行、读哪些数据、需要哪些外部资源、可能提出哪些处置动作；它的算法、默认参数、与原论文的差异说明 | 决定自己的动作是否生效（它只能提议，也不知道自己是否被启用）；读声明之外的数据；接触宿主框架；知道同时还挂了谁 |
| **策略文件**（`policy.py` 读取） | 一次部署**用哪些控制**：挂哪些、顺序、构造参数、谁的动作生效、控制出错时怎么办、允许用哪些扩展层 | 改变一个控制读什么、在哪运行、需要什么资源；指定宿主、模型、数据；提供资源的内容 |
| **挂载方**（应用或入口脚本） | **在哪跑**：选宿主和适配器、提供模型与数据、准备策略点名的外部资源、决定是否留记录、按策略打开扩展层 | 绕过声明给插件塞数据；替插件决定算法；替策略决定谁生效 |
| **库**（`core/`、`views/`、`recorder/`、`adapters/`） | **保证以上三方说的互相成立，并照着执行**：第一轮之前核对声明、策略与宿主能力；按位置调度；只给声明过的数据；执行被启用的动作；合并多个控制的决定；记录 | 任何一种方法特有的阈值或逻辑；判断一个控制有没有效 |
| 知识库（`kb/`） | **知道什么**：威胁与控制的对应、每个实现的证据等级和已知问题、覆盖情况。由插件的声明和实验结果生成或校验 | 参与运行：运行时的任何一层都不导入它 |

**一个改动该落在哪里**：

| 想改的事 | 改哪里 |
|---|---|
| 换一个阈值、窗口、裁剪界 | 策略文件里该控制的 `args` |
| 让某个控制从只告警变成处置 | 策略文件里该控制的 `enforce` |
| 算法本身要读更多数据或多一种动作 | 插件类的声明和实现 |
| 换干净参考数据、探针、对齐语料 | 挂载方提供的资源 |
| 换宿主框架 | 挂载方换适配器；策略文件和插件都不动 |
| 多个控制的决定怎么合并、动作怎么记录 | 库（`core/`） |
| 某个方法在 LoRA 上按论文参数会误伤 | 知识库里该实现的已知问题；默认参数留在插件里不动 |

这些边界里能用代码守住的都守住了：策略文件出现声明之外的键即报错（包括 `needs`、`at`、`resources`、`host`）；插件拿到的上下文里没有任何关于"是否生效"的信息；
`methods/`、`plugins/` 只能导入 `core` 与 `ops`，`core` 不导入策略、插件和知识库（`tests/test_architecture.py`、`tests/test_policy.py`）。
守不住、只能靠约定的有两条：同一进程里的插件如果存心越界，语言层面拦不住；库里不放方法特有的逻辑，靠评审。

粒度上有一个已知的限制：`enforce` 是按控制给的。一个控制如果同时提出几种动作（例如 FLAME 既剔除、又裁剪、又加噪），只能一起生效或一起只告警。

## 宿主

```bash
python -m fedguard.adapters.hosts    # 各宿主在每个位置、每类数据、每种动作上的支持级别
```

| 宿主 | 怎么接 | 现状 |
|---|---|---|
| Flower（Message API） | `GuardStrategy` 包住应用的策略，`guard_mod` 加进 `ClientApp` 的 mods；宿主代码不改 | 服务器侧四个位置与客户端训练前后原生可用；训练内的数据、梯度、样本改写要应用的训练函数配合；训练前的握手要启用扩展层（见下）；服务器侧的模型句柄由应用传入 |
| OpenFedLLM 系脚本（OpenFedLLM 原版、FedLLM-Attack） | 宿主没有扩展点，按 `adapters/OPENFEDLLM.md` 的调用点改它的训练脚本；`integrations/` 下有两个宿主各自的最小示例与补丁，由同一个生成器产出 | 十个位置都能挂，全部属于改脚本；`CLIENT_LOSS` 另需训练器扩展层 |

在真实模型上核对过的（2026-10-10；Qwen2.5-0.5B 在 legion 上用 `experiments/legion/queue_addon.sh`，Qwen3.5-0.8B 在 AutoDL 上用远端队列 `addon`；都只说明挂得上、跑得动、不改变训练，不说明防御效果）：

| 性质 | OpenFedLLM 原版 | FedLLM-Attack | Flower |
|---|---|---|---|
| 挂上但不运行插件，训练结果与宿主自己跑逐位相同 | 是 | 是 | 是（在 CPU 上比较；GPU 上同一应用两次运行本身就不同） |
| 挂了插件但不让它动作，结果仍逐位相同 | 是 | 是 | 未单独核对 |
| 插件在真实模型上运行 | 18 个服务器侧、8 个客户端侧插件只记录；FLAME 与 2 个客户端侧插件执行动作（`integrations/check_plugins.sh`，Qwen2.5-0.5B 与 Qwen3.5-0.8B） | 26 项批量运行（Qwen3.5-0.8B 与 4B） | 18 个服务器侧插件、9 个客户端侧插件只记录；FLAME 与 3 个客户端侧插件执行动作 |
| 握手 | 脚本内直接调用，ProtegoFed 跑通 | 同左，ProtegoFed 跑通 | 经扩展层，ProtegoFed 跑通 |
| 采集开销 | — | RTX 4050：训练 2.4 秒/客户端，采集 18 到 22 毫秒，占 0.7% 到 0.9%；RTX 5090：训练 1.0 秒/客户端，采集 27 到 29 毫秒，占 2.7% 到 2.8% | 未测 |

Flower 一列在 Qwen2.5-0.5B 与 Qwen3.5-0.8B 上各跑过一遍，结果相同；两个脚本宿主的逐位核对用的是 Qwen2.5-0.5B。
2026-10-11 的内部整理（动作登记表、状态作用域、方法重新分组、控制策略文件）之后，上表各项在 AutoDL 上重新核对过一遍，全部通过（队列 `refit`）。

适配器在挂载时按宿主的能力拒绝跑不了的插件。

**扩展层。** 宿主的标准流程里没有的能力，可以由本库的一层扩展适配补上，但它会改变宿主原有的运行方式，所以默认关闭，
启用时发出 `HostExtensionWarning`，并在运行记录里写明（`run.json` 的 `host_extensions`）。不启用时，需要它的插件在第一轮之前被拒绝。目前有两个：

| 扩展层 | 文件 | 提供 | 它改了宿主的什么 | 核对到哪一步 |
|---|---|---|---|---|
| `handshake`（仅 Flower） | `adapters/flower_handshake.py` | `CLIENT_ANNOUNCE`、`SERVER_EXCHANGE` | 用 Flower 公开的查询消息，在每轮训练前多做一次往返，并多下发一次适配器 | 仿真引擎里的合成客户端（`experiments/flower/flower_check.sh` 的 F 项）；真实模型上跑过 ProtegoFed（`experiments/flower/llm_check.sh`） |
| `trainer`（所有用 HF Trainer 训练的宿主） | `adapters/hf_trainer_ext.py` | `CLIENT_LOSS` | 把宿主建好的 Trainer 对象的 `compute_loss` 换成一层包装；宿主自己的损失计算（包括它的子类，如 FedProx、SCAFFOLD 的训练器）照常执行，插件拿到它的结果 | 单元测试里的真实 Trainer 与随机小模型（`tests/test_trainer_ext.py`，两套依赖环境）；Qwen3.5-0.8B 上（AutoDL，2026-10-11，结果在 `runs/autodl/ext-q35/`）：Flower 上扩展层开着、插件只记录时与原训练逐位相同（CPU 比较），Lisa 与逐样本裁剪的 LA-LoRA 在 Flower 和 FedLLM-Attack 两个宿主上动作、无报错。逐样本裁剪那次运行的总时长是不开扩展层时的 2.7 倍（206 秒对 77 秒，批大小 4） |

训练器扩展层开着、但插件只记录不动作时，训练结果与不开时逐位相同（插件自己多做的前向在随机状态隔离之内）。
插件改了损失之后，那一步就不再是宿主自己的训练步：与"宿主原样"的运行对比时要分开报告。
评估是宿主的事，库不设评估位置；评估结果可以经记录层存取。
各实现在各宿主上的挂载级别见 `kb/generated/coverage.md` 第 8 节。

库不提供攻击实现，也不保证任何攻击能被发现。`methods/` 里的每个方法都在类说明里写明了实现了哪些步骤、
哪些没实现、论文没说清而由我们决定的地方；它们都没有对照过原作者的代码，也没有复现过论文的数值。
设计依据见 `output/poisoning_study/` 下 2026-10-08 与 2026-10-09 的文档。

## 位置

按一轮训练到达的先后排列。一个插件可以挂在同一侧的多个位置上，`run` 按 `ctx.stage` 分支，`ctx.state` 在各位置间共享。

| 位置（`Stage`） | 所在侧 | 这里有什么 |
|---|---|---|
| `SERVER_DISTRIBUTE` | 服务器 | 即将下发的全局 LoRA 与接收方 |
| `CLIENT_ANNOUNCE` | 客户端 | 模型与数据已到位；客户端可以先向服务器发一份摘要 |
| `SERVER_EXCHANGE` | 服务器 | 应答这些摘要，此时还没有任何客户端开始训练 |
| `CLIENT_PRE_TRAIN` | 客户端 | 本地数据、收到的全局 LoRA |
| `CLIENT_LOSS` | 客户端 | 本步的批次、模型输出与损失已算出，尚未反向传播。**只有启用训练器扩展层才有** |
| `CLIENT_PRE_STEP` | 客户端 | 梯度已算出，优化器尚未更新 |
| `CLIENT_STEP` | 客户端 | 每个训练步之后 |
| `CLIENT_POST_TRAIN` | 客户端 | 上传前的本地 LoRA |
| `SERVER_RECEIVE` | 服务器 | 各客户端的上传 |
| `SERVER_AGGREGATE` | 服务器 | 聚合名单与权重 |
| `SERVER_POST_AGGREGATE` | 服务器 | 本轮的聚合结果 |

## 数据类别

插件在 `needs` 里声明要读哪些类别，没声明的读不到。每一侧只能拿到本侧经手的类别。

| 类别 | 所在侧 | 内容 |
|---|---|---|
| `data` | 客户端 | 本地样本与清单（哈希、来源、长度） |
| `received_model` | 客户端 | 收到的全局 LoRA，可与上一次收到的比较 |
| `train_trace` | 客户端 | 训练步标量；训练循环提供时可取当前的 LoRA |
| `loss` | 客户端 | 本步的批次、模型输出、带计算图的损失；可在另一批数据上再算一次损失，可对任一标量求梯度（见"训练步之内"） |
| `gradients` | 客户端 | 本步各可训练参数的梯度 |
| `local_update` | 客户端 | 上传前的本地 LoRA |
| `outgoing` | 服务器 | 即将下发的全局 LoRA，可按接收方区分 |
| `uploads` | 服务器 | 各客户端上传的 LoRA（A、B 分开，可还原乘积） |
| `aggregate` | 服务器 | 名单、权重、规则、聚合结果 |
| `reports` | 两侧 | 自报值、通道消息与通道张量，一律未核实 |
| `model_handle` | 两侧 | 模型句柄，见下 |
| `history` | 两侧 | 此前各轮的特征与原始对象（后者需开启记录） |

## 模型句柄

`model_handle` 是插件做训练内昂贵计算的入口，接口在 `views/model.py`，HF 实现是 `adapters/hf_model.HFModelHandle`：

| 方法 | 作用 | 开销 |
|---|---|---|
| `lora(state)` | 上下文管理器：临时加载一份 LoRA，退出时精确恢复 | 一次权重拷贝 |
| `losses(samples)` | 逐样本损失 | 每条一次前向 |
| `hidden(samples, layer, pool)` | 隐藏层状态。`pool` 为 `last`、`mean`、`max` 时每条样本一个向量；`none` 时不池化，每条样本一个（词元数 × 维度）的张量 | 每条一次前向 |
| `activations(samples, select, pool, what)` | 指定子模块的输出或输入（`what="input"`，如 LoRA 下投影收到的隐状态），池化方式同上 | 每条一次前向 |
| `tokens(samples)` | 每条样本被切成的词元，与不池化时的位置一一对应 | 无 |
| `per_sample_gradients(samples, group, scope, reduce)` | 逐样本梯度，展平。`scope="all"` 时可用谓词选中冻结的基座权重；`reduce` 在模型所在设备上把每条样本的梯度压成一个向量，用于整块存不下的梯度 | 每条一次前向加一次反向 |
| `logprob(prompts, targets)`、`generate(prompts)` | 对数概率、生成 | 前向 |
| `parameters(group, scope)`、`layout(group, scope)` | 参数组与它在 LoRA 状态里的键和形状 | 无 |

服务器一侧默认没有可运行的模型，宿主不提供。防御方自己有模型时，把一个句柄作为 `probe` 传给服务器侧适配器
（`OpenFedLLMGuard(runner, probe=HFModelHandle(model, tokenizer))`、`GuardStrategy(..., probe=...)`），服务器侧插件就能声明 `model_handle`；
`adapters/hf_probe.HFProbe` 是只会打分的窄版本。模块在第几层、是哪个投影，用 `ops.states.module_info(键名)` 从键名读出。

句柄可以直接包住正在训练的模型，每个方法用完都把权重、训练模式和梯度恢复原样。它累计前向与反向的样本数和耗时，
运行器把每个插件花掉的部分写进该插件的输出（`findings.cost`）。**采集底座的开销很低，用到句柄的插件不低**：
逐样本梯度只能逐条算，样本多时可用 `ops.sampling.subsample` 配合 `ctx.rng` 抽样。

## 写一个插件

```python
from fedguard import GuardPlugin, Stage

class DeltaNorm(GuardPlugin):
    name = "delta_norm"
    at = Stage.SERVER_RECEIVE
    needs = frozenset({"uploads"})

    def run(self, ctx):
        up = ctx.uploads
        return ctx.findings(features={c: {"norm": float(up.factor_delta(c).norm())} for c in up.clients})
```

插件声明四件事：`at`（位置）、`needs`（数据类别）、`resources`（自带的外部资源名，如干净参考数据、探针题库，
运行时经 `GuardRunner(resources=...)` 提供，用 `ctx.resource(name)` 读取）、`acts`（可能提出的干预，空表示只报告）。
声明无法满足时，第一轮之前就报 `ContractError`：位置与侧不符、类别在该位置不存在、当前部署拿不到
（例如安全聚合下 `RunSpec(unavailable={"uploads"})`）、资源未提供、动作与位置不符。

`ctx` 上还有：插件私有的状态，分三个作用域：`ctx.state`（整个运行）、`ctx.round_state`（一轮，换轮时清空）、
`ctx.step_state`（一个本地训练步，同一步的各个位置共用，换步时清空）；`ctx.rng`（按插件与轮次派生，不动全局随机状态）、
`ctx.upstream_feature("插件.特征")`（同轮先运行的插件的输出）。

## 接入训练

服务器侧，Flower：

```python
from fedguard import GuardRunner, RunSpec
from fedguard.adapters.flower import GuardStrategy
from fedguard.recorder.store import Recorder

rec = Recorder("records", run_id)
runner = GuardRunner([DeltaNorm()], RunSpec(run_id, lora_scale=alpha / r), rec)
strategy = GuardStrategy(FedAvg(...), runner, rec)
```

客户端侧，Flower 加 HF 训练器：

```python
from fedguard.adapters.flower_client import active_guard, guard_mod
from fedguard.adapters.hf_trainer import GuardStepCallback

app = ClientApp(mods=[guard_mod(make_guard)])      # make_guard(context) -> ClientGuard

@app.train()
def train(msg, context):
    guard = active_guard()
    guard.pre_train(data=DataView(samples, text_of=format_sample))
    trainer.add_callback(GuardStepCallback(guard))
    ...
```

挂在 `CLIENT_LOSS` 的插件还需要训练器扩展层（非宿主原版行为，见"宿主"一节）：

```python
from fedguard.adapters.hf_trainer_ext import extend_trainer

app = ClientApp(mods=[guard_mod(make_guard, extensions={"trainer"})])
...
    extend_trainer(trainer, guard)                 # 在宿主建好 Trainer 之后、train() 之前；发出 HostExtensionWarning
    trainer.add_callback(GuardStepCallback(guard))
```

单进程循环（OpenFedLLM、FedLLM-Attack 一类）用 `fedguard.adapters.openfedllm.OpenFedLLMGuard` 和
`fedguard.client.ClientGuard`，调用顺序见各自的文件头。不挂任何插件也可以只做记录。

## 训练步之内

一个本地训练步里有三个位置，按先后：

| 位置 | 此时 | 能读 | 能改 | 怎么到达 |
|---|---|---|---|---|
| `CLIENT_LOSS` | 前向已完成，尚未反向 | 批次、输出、损失（`ctx.loss`） | 损失（`transform_loss`） | 训练器扩展层 |
| `CLIENT_PRE_STEP` | 梯度已算出，优化器未更新 | 批梯度、参数值（`ctx.gradients`） | 梯度（`transform_gradients`） | Trainer 回调 |
| `CLIENT_STEP` | 优化器已更新 | 标量、当前 LoRA（`ctx.train_trace`） | — | Trainer 回调 |

`ctx.loss`（`views/client.LossView`）提供：

| 成员 | 作用 | 开销 |
|---|---|---|
| `loss`、`batch`、`outputs`、`batch_size` | 宿主算出的损失（带计算图）、这一批的张量、模型输出 | 无 |
| `parameters()` | 可训练参数本身，用于依赖权重的损失项（近端项、范数正则） | 无 |
| `loss_on(batch)` | 宿主的损失函数在另一批数据上的值，带计算图（第二数据源，如对齐数据） | 一次前向 |
| `per_sample_losses()` | 批内每个样本的损失，带计算图 | 无（复用已有输出） |
| `sample_ids()` | 批内每一行对应的样本哈希（与清单一致），用来把步内的逐样本量跨步、跨轮对到同一条样本上。需要应用在 `extend_trainer(identify=...)` 里说明怎么认，`identify_from_dataset` 是按词元序列匹配的现成实现 | 无 |
| `gradients_of(scalar, select)` | 某个标量对可训练参数的梯度，不破坏宿主随后的反向 | 一次反向 |

改损失的写法是 `proposals={"loss": 新的标量张量}`，新张量必须连着计算图。逐样本梯度是对 `per_sample_losses()` 的每一项调用
`gradients_of`，每个样本一次反向。够不着的：前向过程内部（注意力分数、中间激活要应用自己打开输出开关或由插件挂钩子）、
优化器、批次的顺序；多卡 DataParallel 下损失是向量，扩展层拒绝运行。

## 控制策略

一组同时启用的控制写成一份策略文件（`fedguard/policy.py`）。它说明两侧各挂哪些控制、各自的参数、谁的处置动作生效、失败时怎么办、依赖哪些扩展层：

```yaml
policy: 1
name: baseline
server:
  fail: open                        # open：控制出错时记录并跳过；closed：中止运行
  controls:
    - effect_stats                  # 只观察
    - {use: krum, args: {f: 1, m: 5}, enforce: true}    # enforce：处置动作生效；不写则只告警
client:
  controls:
    - {use: lisa, args: {k_align: 1, k_finetune: 2}, enforce: true}
extensions: [trainer]               # 依赖的扩展层必须显式列出，不会被隐式打开
```

```python
from fedguard.policy import Policy

policy = Policy.load("baseline.yaml")
server_runner = policy.runner("server", spec, recorder, resources={...})
client_runner = policy.runner("client", spec, resources={...})    # 每个客户端各取一份
policy.resources("client")                                        # 这份策略要调用方提供哪些外部资源
```

```bash
python -m fedguard.policy integrations/policies/baseline.yaml    # 它挂了什么、每个宿主上各需要什么
```

- `use` 是内置插件或已移植方法的名字，也可以写 `包.模块:类名` 指向自己的插件。控制按书写顺序运行。
- 默认只告警。只有写了 `enforce: true` 的控制，其处置动作才会被执行。
- 加载时就拒绝：未知的键、未知的控制名、放错侧的控制、同名控制出现两次、对没有动作的控制要求 `enforce`、构造参数不对。
- 策略不涉及宿主、数据和模型。外部资源在策略里只有名字，由挂载方提供；宿主能否承载由适配器检查。
- 运行记录的 `run.json` 里有策略的名字和内容摘要（摘要与文件排版和名字无关），事后可以确认两次运行用的是不是同一组控制。
- 三个入口都接受策略文件：实验入口与接入示例的 `--guard_policy`，Flower 应用的 `FG_POLICY`。原来按名字列控制的参数仍然可用，内部会转成一份策略。

示例在 `integrations/policies/`：`observe.yaml`（只观察）、`baseline.yaml`（不需要模型和外部资源的服务器侧基线）、`step_constraints.yaml`（训练步内的约束，需要训练器扩展层）。

## 记录

```
<root>/<run_id>/run.json                      运行配置、部署条件、插件声明、资源哈希
<root>/<run_id>/round_0003/                   服务器侧
    base.safetensors  client_<id>.safetensors  aggregate.safetensors
    reports.json  round.json  eval_<name>.jsonl
<root>/<run_id>/clients/<id>/round_0003/      客户端侧
    received.safetensors  local.safetensors  manifest.jsonl  trace.jsonl  round.json
```

- `round.json` 里有本轮每个对象的内容哈希和上一轮 `round.json` 的哈希。`Recorder.verify()` 检出事后改动。
- 内容哈希与文件编码无关。`recorder.audit.compare_sides()` 对照两侧：服务器的 `base` 应等于客户端的
  `received`，服务器的 `client_<id>` 应等于客户端实际上传的对象。不相等是一条关于传输或某一方的事实。
- 样本原文不落盘，清单只有哈希、来源标识和长度。
- 服务器侧目录沿用了旧布局（直接在 `<run_id>/` 下），旧记录仍然可读；旧记录没有哈希，`verify()` 会如实报告。

读取与重放：

```python
from fedguard.recorder.query import RunRecord
from fedguard.replay import replay

run = RunRecord("records", run_id)
run.findings(plugin="delta_norm", subject="client3")      # 按插件、位置、轮、对象筛选
run.series("delta_norm.norm")                             # {对象: [(轮, 值), ...]}

replay("records", run_id, [AnotherPlugin()], "records_replayed")                # 服务器侧，不重新训练
replay("records", run_id, [LocalCentroid()], "out", client="client3", samples=load_samples)
```

客户端重放时，需要样本原文的插件要由数据持有方通过 `samples` 提供数据。

## 消息通道

两侧的配对插件只通过通道交换内容，收到的一律视为未核实，接收方要自己校验类型与取值。

```python
return ctx.findings(messages={"n": 12}, attachments={"centroid": vector})   # 发：小记录与张量
ctx.reports.messages("local_centroid.n")          # 收小记录：服务器上按客户端，客户端上键为 "server"
ctx.attachment("protegofed_client.centroid")      # 收张量
```

- 小记录：数字、字符串、布尔及其平铺列表，单轮上限 64 KB。
- 张量：每个插件每轮的总字节数有上限（`GuardRunner(attachment_limit_bytes=...)`，默认 64 MB），内容哈希记入记录。
- 平常，服务器的消息随下一轮广播到达，客户端的消息随本轮上传到达。
- 需要在训练前完成一次往返时（如 ProtegoFed 的质心交换），客户端插件挂 `CLIENT_ANNOUNCE`，
  服务器插件挂 `SERVER_EXCHANGE`：`guard.announce()` 给出要发的内容，`server.exchange(...)` 给出应答，
  `guard.deliver(...)` 交给客户端，之后才运行 `CLIENT_PRE_TRAIN`。

## 动作

`GuardRunner(apply_actions=False)`（默认）时，插件提出的动作只记录、不执行；`True` 全部执行；传一组插件名则只执行这些插件的。

| 动作 | 位置 | 怎么提出 | 训练代码怎么取 |
|---|---|---|---|
| `transform_broadcast` | `SERVER_DISTRIBUTE` | `proposals={"broadcast": {接收方或"*": LoRA}}` | 适配器改写下发内容 |
| `transform_received` | `CLIENT_PRE_TRAIN` | `proposals={"received": LoRA}` | `guard.start_state()` |
| `mask_samples` | `CLIENT_PRE_TRAIN` | `proposals={"mask": [样本哈希]}` | `guard.training_samples()` |
| `edit_samples` | `CLIENT_PRE_TRAIN` | `proposals={"add": [...], "rewrite": {哈希: 样本}}` | `guard.training_samples()` |
| `transform_loss` | `CLIENT_LOSS`（训练器扩展层） | `proposals={"loss": 标量张量}` | 扩展层把它交还给 Trainer 去反向 |
| `transform_gradients` | `CLIENT_PRE_STEP` | `proposals={"gradients": {参数名: 张量}}` | 运行器原地写入 |
| `transform_update` | `CLIENT_POST_TRAIN`、`SERVER_RECEIVE` | `proposals={"transformed": {对象: LoRA}}` | `guard.upload_state()`；适配器 |
| `select_and_weight` | `SERVER_AGGREGATE` | `decision=Decision(weights=..., excluded=...)` | 适配器 |
| `replace_global` | `SERVER_POST_AGGREGATE` | `proposals={"replacement": LoRA}` | 适配器 |

每个动作都以前后哈希（样本动作为哈希清单，梯度动作为前后范数，损失动作为前后数值）记入 `round.json`。多个插件同时给出剔除或权重时，
取剔除的并集和权重的最小值；叠加多个检测器只会剔除更多客户端，检测器相关时会放大误剔除。

## 算子库

`fedguard/ops/`，只依赖 torch 与 numpy，不知道位置和插件的存在。

收录规则：一个计算进算子库，要么是 LoRA 特有的，要么已经被两个以上的方法共用。只有一篇论文用的计算留在那个方法里。
通用数值（距离、聚类、分解）torch 与 scikit-learn 已经有，这里不为目录完整而重复。
每个算子被谁使用由源码静态分析给出，见 `kb/generated/coverage.md` 第 6 节，或运行 `python experiments/eval/ops_audit.py`。

| 模块 | 内容 |
|---|---|
| `states` | LoRA 状态的差、加、展平与还原、范数、加权平均 |
| `lowrank` | 不展开乘积就精确计算 LoRA 乘积的范数、内积、奇异值 |
| `geometry` | Gram 矩阵及由它得到的平方距离与余弦距离、余弦、Krum 分数、横截面比较 |
| `robust` | 稳健 z 分数、坐标中位数、截尾均值、最大间隙阈值、FoolsGold 权重 |
| `transform` | 二维 DCT 与低频三角、PCA、把向量排成方阵 |
| `cluster` | k-means、层次聚类、DBSCAN、数据驱动半径的密度聚类、多数簇、轮廓系数、间隙统计 |
| `spectral` | 主奇异方向得分、谱熵 |
| `density` | 一维核密度、谷底阈值、熵、k 近邻局部密度比 |
| `sequential` | CUSUM、Beta 均值、L-BFGS 海森向量积、滑动窗口均值、一维二项式低通滤波 |
| `update` | 按范数裁剪与缩放（更新或整个状态）、加噪、裁剪后加噪、投影到子空间 |
| `sampling` | 带种子的抽样 |
| `probe`、`text` | 逻辑回归探针的拟合与应用（特征多于样本时在样本子空间里拟合）；逐词删除与离群词判定 |

没有 scikit-learn 时，`majority_cluster` 与 `density_clusters` 是 HDBSCAN 的替代品：契约相同，算法不同。装了 scikit-learn 时前者直接调用它的 HDBSCAN。

## 已发表的防御

`fedguard/methods/`，按所在的控制点分文件：`server_uploads.py`（服务器侧，针对上传）、`client_samples.py`（客户端训练前，针对样本）、
`client_model.py`（客户端，针对收到的适配器与本地结果）、`client_step.py`（训练步内）、`two_sided.py`（两侧配对）。
名字到类的表在 `fedguard.methods.METHODS`。完整清单由声明生成：`methods/CATALOG.md`
（`python -m fedguard.methods write`），其中有每个方法的位置、读的数据、外部资源、动作、在各宿主上的挂载级别、
与原文的差异、参数默认值，以及在三个宿主上各怎么试。下表是它的摘要。

| 方法 | 类 | 位置 | 需要的外部资源 |
|---|---|---|---|
| Krum / Multi-Krum | `Krum` | 聚合 | — |
| 坐标中位数、截尾均值 | `CoordinateMedian`、`TrimmedMean` | 聚合后 | — |
| FoolsGold | `FoolsGold` | 聚合 | — |
| FLTrust | `FLTrust` | 收到更新、聚合 | 在根数据上训练出参照更新的函数 |
| FLAME | `FLAME` | 收到更新、聚合、聚合后 | — |
| FreqFed | `FreqFed` | 聚合 | — |
| FLDetector | `FLDetector` | 收到更新、聚合、聚合后 | — |
| Safe-FedLLM 客户端级 | `SafeFedLLMClientLevel` | 收到更新、聚合 | 离线训练的探针 |
| Safe-FedLLM 步级 | `SafeFedLLMStepProbe`（客户端）、`SafeFedLLMStepTrust`（服务器） | 训练步、上传前；聚合 | 探针 |
| ProtegoFed | `ProtegoFedClient`、`ProtegoFedServer` | 宣告、训练前；握手交换 | 模型句柄 |
| TriShield 的适配器扫描 | `ReceivedAdapterScan` | 训练前 | — |
| TriShield 的更新投影 | `UpdateSubspaceProjection` | 上传前 | 公开辅助样本、模型句柄 |
| Safe LoRA | `SafeLoRA` | 聚合后 | 对齐前后权重之差 |
| 谱签名 | `SpectralSignatures` | 训练前 | 模型句柄 |
| GradSentry 式梯度谱熵 | `GradientSpectralEntropy` | 训练前 | 模型句柄 |
| 激活聚类 | `ActivationClustering` | 训练前 | 模型句柄 |
| MUD-HoG | `MudHoG` | 收到更新、聚合 | — |
| LoMar | `LoMar` | 收到更新、聚合 | — |
| MCD（模型一致性） | `MCD` | 收到更新、聚合 | —（原文的可信基线换成了中位数） |
| CRFL 的训练期部分 | `CRFL` | 聚合后 | — |
| ONION（移到训练前） | `Onion` | 训练前 | 模型句柄 |
| 安全样本混入；加秘密前缀即 BEA | `SafetyMix` | 训练前 | 安全样本 |
| LA-LoRA 的本地步 | `AlternatingNoisyLoRA` | 训练步（优化器更新前） | — |
| Lisa 的近端项 | `LisaProximal` | 训练步（优化器更新前） | — |
| Lisa（双状态交替，完整） | `LisaBiState` | 训练步（反向之前；训练器扩展层） | 对齐数据的批次 |
| LA-LoRA 的本地步，逐样本裁剪 | `LALoRAPerSample` | 训练步（反向之前与优化器更新前；训练器扩展层） | — |

这些方法是从 `survey/harvest/2026-10-08/opsread/` 的逐篇算子提取写出来的。测试（`tests/test_methods_*.py`）
验证的是"在为该机制构造的情形下行为符合机制"，不是论文数值的复现。几处与原文不同的地方：
LoRA 下向量取因子空间的更新而非完整模型；UMAP 换成 PCA；ICA 换成 PCA；GradSentry 的目标矩阵由 `lm_head` 换成一个 LoRA B。
没有实现的：Safe-FedLLM 的影子分支、FLDetector 的"剔除后重训"、TriShield 的优化器预热。
只实现了一部分的：CRFL 没有测试期的参数平滑与认证半径；ONION 原本作用于推理输入，这里改写的是训练样本；
`la_lora` 裁剪的是批梯度而不是逐样本梯度，`lisa_proximal` 只有近端项、没有与对齐数据交替的那一半。后两个是只用 Trainer 回调时能做到的程度；
补全的版本是 `la_lora_dp`、`lisa`（同在 `methods/client_step.py`），需要训练器扩展层。

同时启用多个方法时，每个方法的输出与单独启用时相同（动作不执行的前提下；`tests/test_methods_together.py` 对不需要外部资源的
服务器侧方法逐个核对）。动作执行后，后面的插件看到的是前面插件改过的对象，这是有意的；合并规则见"动作"一节。

## 知识库

`fedguard/kb/` 把"库知道哪些威胁与防御"存成数据，论文只作为条目的来源。设计依据见
`output/poisoning_study/2026-10-10_fedguard重构设计-按制品与技术组织.md`。

| 文件 | 内容 |
|---|---|
| `vocabulary.yaml` | 骨架：制品、坐标（制品/取法/粒度）、攻击者能力、目标、战术、信任假设、证据等级 |
| `threats.yaml` | 威胁技术 `T-xxxx`：目标 × 能力 × 改动的制品，以及预期留痕的坐标（由脚本从逐篇草稿归并生成） |
| `defenses.yaml` | 防御技术 `D-xxxx`：解决的技术问题、读的制品、动作、信任假设、需要的资源、已知绕过方式 |
| `implementations.yaml` | 实现 `I-xxxx`：属于哪个防御技术、对应哪个插件类、读哪些坐标、状态；运行时表达不了的也登记（现有 3 个），并写明缺什么 |
| `scenarios.yaml` | 场景 `S-xxxx`：最小可执行实验，含无攻击对照 |
| `relations.yaml` | 实现对威胁的证据：等级 1 原论文评测过，等级 2 在本库里端到端跑通（由脚本生成） |
| `generated/coverage.md` | 由以上生成的覆盖视图，不手改 |

```bash
python -m fedguard.kb check     # 校验：未声明的字段、词表外的词、悬空引用都是错误
python -m fedguard.kb tables    # 重新生成 generated/coverage.md
python experiments/eval/kb_relations.py <批量运行的结果目录> ...   # 由运行结果与论文评测重建 relations.yaml
```

校验是双向的：条目说实现读哪些坐标、做哪些动作、要哪些资源，必须与插件类声明的 `needs`、`acts`、`resources` 一致；
`fedguard.methods` 里的每个方法都必须有条目。方法"实现了什么、与原文哪里不同、哪些是自己的选择"仍写在类说明里，
知识库按固定的小节标记读出来（`kb.describe(实现编号)`），不另存一份。

威胁与防御不直接互连。`kb.link(实现, 威胁)` 只根据制品给出联系的种类（直接、论文报告过痕迹、按机制推断），
它表示值得试；有没有效要看 `relations.yaml` 里的证据等级。目前没有任何一对达到等级 3。

## 演示契约的内置插件

| 插件 | 位置 | 作用 |
|---|---|---|
| `effect_stats`、`factor_stats` | `SERVER_RECEIVE` | 上传在乘积空间和因子空间的范数与方向统计 |
| `robust_outlier` | `SERVER_RECEIVE` | 某个上游特征的稳健离群分数 |
| `compliance_probe` | `SERVER_RECEIVE` | 把上传加载到服务器的模型上测行为，需要 `model_handle` |
| `report_guard` | `SERVER_AGGREGATE` | 限制自报样本数换来的聚合权重（`select_and_weight`） |
| `evidence_accumulator` | `SERVER_AGGREGATE` | 跨轮累积上游特征 |
| `local_centroid`、`centroid_consensus` | 客户端、服务器 | 配对示例，演示消息通道 |
| `norm_clip`、`jump_rollback`、`sample_mask` | 见上表 | 各动作的最小示例 |

## 已知限制

- 同一进程内的类别限制只能防误用，防不了恶意插件。
- 训练步回调看到的是整批梯度，不是逐样本的，也拿不到批内有哪些样本。逐样本的量要经训练器扩展层取，每个样本多一次反向。
- 训练器扩展层够不着前向过程内部、优化器和批次顺序；它的开销只有一个粗略读数（逐样本梯度那次运行总时长 2.7 倍），没有单独量过。
- Flower 上的握手与训练器损失钩子都是扩展层，不是 Flower 或 Trainer 自己的行为；用了它们的运行在记录里有标记。
- Flower 仿真里同一节点每轮可能由不同工作进程处理，插件的 `ctx.state` 会从空开始。
- 客户端每轮各存一份收到的和上传的 LoRA，服务器每轮每客户端存一份上传。客户端多时可用
  `Recorder(save_factors=False)` 只留哈希。
- 采集开销只在 FedLLM-Attack 宿主上量过（见"宿主"一节的表）；用到模型句柄或训练器扩展层的插件，开销取决于它自己多做的前向与反向。
- `methods/` 里的方法没有与原作者的实现逐一对照过。目前验证的是机制（单元测试）和可运行性（真实模型上的短训练），不是与原实现的数值一致。
- 知识库登记了 3 个运行时表达不了的方法：需要编码器分类模型的注意力分数、需要非低秩的全局模型、需要服务器自己有训练循环。

## 测试

```bash
envs/fl311/.venv/bin/python -m pytest tests -q        # 不训练真实模型；含扩展层、方法并行启用、生成文档是否最新
python -m fedguard.kb check                           # 知识库与插件声明双向一致
python integrations/make_examples.py --check          # 接入示例与生成器一致
```

```bash
bash experiments/flower/flower_check.sh
```

第二条在真实的 Flower 仿真引擎里（合成客户端，不训练模型）检查：开启采集与不开启的最终模型只差浮点舍入
（相对差约 2e-7，来自回复排序）、聚合可从记录逐位重放、两侧记录一致、消息通道双向可达。
