# 研究基座调研：联邦投毒/后门攻防平台、联邦大模型框架、集中式后门基准、溯源工具

> 调研日期 2026-10-08。目的：在设计 fedguard 的"采集底座 + 插件槽位"之前，先看清现有平台是怎么组织攻击和防御的。
> 本文不修改仓库其他文件，也没有克隆或安装任何东西。

## 0. 阅读须知：核实等级与证据格式

每个平台标注核实等级，结论强度随等级变化。

| 等级 | 含义 | 证据格式 |
|---|---|---|
| **A** | 本地克隆的源码，逐文件阅读 | `external/...` 路径加行号 |
| **B** | 通过 WebFetch 读取了 GitHub 上的原始源文件或论文 HTML | URL；无行号，只写类名、方法名 |
| **C** | 只读了 README 或文档页 | URL |
| **D** | 只拿到元数据（星标、许可证、pushed_at）或搜索摘要 | URL |

两点限制：

1. WebFetch 返回的是小模型对页面做的摘要，不是原文。B 级条目里的方法签名、类名来自这种摘要，可能有细节偏差，其中 FedML 的两个单例类、FLPoison 的基类和 Safe-FedLLM 的策略类，在落地设计之前应当再打开原始文件核一遍。
2. 表中"维护"一栏的日期取自 GitHub API 的 `pushed_at`，它是整个仓库最近一次 push，不一定是默认分支的最近提交。本地克隆的 HEAD 提交日期单独注明。

下面所有"没有"类的结论（"该平台没有 X"）都只表示"在我读到的范围内没有"。C、D 级条目尤其如此。

fedguard 现状（用于后文对照，读自 `fedguard/`）：

- 9 个挂载点 H0 到 H8，客户端侧 H1、H2、H3、H7，服务器侧 H0、H4、H5、H6、H8（`fedguard/core/types.py:11-21`）。
- 6 级权限 O0 到 O5，客户端和服务器各有允许集合（`types.py:24-40`）。
- 模块基类 `GuardModule`（`core/module.py:6-22`）。
- 运行时按权限过滤视图（`core/context.py:10-17`）。
- `Decision` 带 weights、excluded 和保守合并（`types.py` 中 `Decision.merge`）。
- 记录层把每轮的 base 和每客户端上传存为 safetensors（`recorder/store.py` 文件头注释）。
- 适配器目前接了 OpenFedLLM 风格主循环和 Flower 的 Strategy 包装（`adapters/openfedllm.py`、`adapters/flower.py`）。

## 1. 总对比表

列含义：**定位**=研究模拟/可部署、模态、是否支持大模型或 LoRA；**攻击**=攻击怎么抽象；**防御**=防御怎么抽象及挂载环节；**扩展/通道**=新增攻防要改哪里、客户端与服务器是否都能扩展、有无通用传信机制；**记录/评测**；**配置/维护**=配置方式、星标、许可证、pushed_at。

| 平台 | 级 | 定位 | 攻击 | 防御 | 扩展 / 通道 | 记录 / 评测 | 配置 / 维护 |
|---|---|---|---|---|---|---|---|
| **FLPoison** | B | 研究模拟；图像分类；无 LLM/LoRA | `attackers/` 下每个方法一个文件，装饰器式注册表；`MPBase` 两个钩子 `non_omniscient()`、`omniscient(clients)`；区分数据投毒、模型投毒、混合；前 `num_adv` 个 worker 是恶意 | `AggregatorBase.aggregate(updates, **kwargs)`，只在聚合处；入参是 N×D 更新矩阵加上一轮全局模型、轮次；服务器数据集只在构造时传入 | 加文件加注册即可；无客户端-服务器通道（进程内共享 clients 对象） | 每轮评测 ACC、ASR；`main.py` 摘要未见保存逐轮更新（其他模块未核实） | YAML + 全局参数；67★；GPL-2.0；2026-04-15 |
| **Blades** | B | 研究模拟（Ray）；小型图像模型；无 LLM | `Adversary(TrainerCallback)`，回调式钩子 `on_trainer_init`、`on_local_round_end`；`clients[:num_malicious]` 是恶意 | 聚合器靠配置选；`validate()` 把 `num_malicious_clients` 写进防御的 `num_byzantine`；仓库 `blades/` 树内未见聚合器目录 | 回调机制；客户端另有 `ClientCallback.on_backward_end`；无通道 | 未核实 | YAML + Ray Tune；157★；Apache-2.0；2025-02-16 |
| **FedMLSecurity** | B | 可部署加模拟；通用；TF/JAX/MXNet 下关闭 | 单例 `FedMLAttacker`，`attack_type` 走 if/elif；三类：模型攻击、数据投毒、数据重建；模型攻击在服务器 `on_before_aggregation` 里改写已收集的更新列表 | 单例 `FedMLDefender`，`defense_type` 走 if/elif；三阶段：聚合前、聚合中、聚合后；`get_benign_client_idxs` 过滤客户端 | 改 if/elif 和常量；安全接口里无通道 | 未核实 | args/YAML；4.1k★（FedML 整体）；Apache-2.0；2025-10-28 |
| **FederatedScope** | A | 研究模拟加分布式；图/NLP/LLM；FS-LLM 含 LoRA 适配器 | 训练器钩子包装（`wrap_*Trainer`）加数据投毒加服务器端攻击者；`attacker_id` 指定；攻击只支持 standalone | `Aggregator.aggregate(agg_info)`，只在聚合处；Krum、Median、Bulyan、TrimmedMean、NormBounding；`byzantine_node_num` 需要攻击者数 | 攻防都要改 builder 的 if/elif（`register.py` 无 aggregator/攻击注册项）；训练器钩子公开有序；**有通用消息总线** `Message(msg_type)` 加处理器注册 | `Monitor` 逐轮指标；`poison_acc` 度量；测试用例；未见逐客户端更新存盘 | YAML（CfgNode）；1.5k★；Apache-2.0；2024-08-10（本地 HEAD 2023-12-25） |
| **Flower** | A | 可部署加模拟；框架无关；FlowerTune 示例含 LoRA | 无攻击抽象（仅 Krum 系列等出现 "malicious"） | `Strategy`（`configure_train` / `aggregate_train` / `configure_evaluate` / `aggregate_evaluate`）；内置 Median、TrimmedAvg、Krum、MultiKrum、Bulyan、DP 包装；`evaluate_fn` 评全局模型 | 服务器写 Strategy 或包装；客户端写 `Mod` 中间件；**有通用通道**：`Message.content` 是 `RecordDict`（含 `ConfigRecord`），有 `query` 消息类型，`Context.state` 本地私有；DP 裁剪是成对示范 | `Result` 只存聚合后指标和最终参数，无逐客户端更新 | `pyproject.toml` + CLI；7.2k★；Apache-2.0；2026-10-07 |
| **NVIDIA FLARE** | C | 可部署为主；通用；有 `llm_hf` 示例（含 `hf_peft_model.py`） | 无攻击抽象（未核实） | `Filter` 四个挂点（服务器/客户端 × task_data/task_result）；`Aggregator.accept/aggregate`；`app_common/aggregators` 目录里未见 Krum/Median | 加 `FLComponent`；`handle_event`/`fire_event` 事件；**有通道**：`FLContext` 公开属性随消息发送，对端用 `get_peer_context()` 读取，另有联邦事件 | 事件审计、`filter_history`；站点级 `privacy.json` 强制先于作业过滤器执行 | JSON/Job API；981★；Apache-2.0；2026-10-07 |
| **FATE / FATE-LLM** | C | 可部署（工业级）；FATE-LLM 做联邦 LLM（PELLM 教程） | 无攻击模块（未提及） | 无鲁棒聚合（未提及）；侧重同态加密/MPC | 组件开发指南（未读）；通道未核实 | 未核实 | Pipeline/DSL；6.1k★ / 271★；Apache-2.0；2024-11-19 / 2026-09-04 |
| **PFLlib** | C | 研究模拟；图像/文本小模型 | 无投毒攻击；仅有 DLG 隐私攻击 | 无 | 继承 `Server`、`Client` 基类 | 未核实 | CLI；2.2k★；Apache-2.0；2026-01-25 |
| **Plato** | C/D | 研究模拟；通用 | 文档里有"投毒检测""梯度泄露攻防"示例（未读） | 未核实 | 文档提到 Trainer 回调、自定义客户端/服务器（未读） | 未核实 | YAML；400★；Apache-2.0；2026-10-04 |
| **FedScale / LEAF** | D | 研究模拟/基准数据集 | 无（未提及） | 无（未提及） | — | — | 421★ / 911★；Apache-2.0 / BSD-2；2023-12 / 2023-03 |
| **FLDetector（参考实现）** | B | 单脚本研究代码；MXNet；图像 | `byzantine.py` 函数集；`args.byz_type` 的 if/elif | `nd_aggregation.py`（trim/median/krum）；FLDetector 自带历史记录 | 改脚本 | 写 `score1.csv` | 命令行；87★；无许可证；2023-02-23 |
| **FLTrust（参考实现）** | D | 未找到官方仓库 | — | 用服务器 root 数据集；FLPoison 里有重实现 | — | — | — |
| **BackFed** | D | 研究模拟（Ray）；5 个 CV + 2 个 NLP 数据集（论文） | `MaliciousClient` 子类加 `PoisonModule`；18 个攻击（论文） | `Server` 子类，重写 `aggregate()` 或 `detect_anomalies()`；25 个防御；客户端侧防御为 `BenignClient` 子类 | 子类化；"function references"自定义交互 | 未核实 | 54★；无许可证；2026-03-29 |
| **OpenFedLLM** | A | 研究模拟；LLM；PEFT/LoRA；SFT 与 DPO | **没有** | **没有**（仅 FedAvg 族算法，字符串分支） | 改 `fed_global.py`、`fed_local_sft.py` 的 if/elif；无通道 | 只存 checkpoint 和 `training_loss.npy` | CLI 加 dataclass；480★；Apache-2.0；2024-12-12 |
| **FedLLM-Bench** | C | OpenFedLLM 后继；真实客户端数据集 | 无 | 无 | 同 OpenFedLLM（据 README） | 含 AdvBench 评测脚本 | 124★；许可证未标注；2024-08-14 |
| **FedLLM-Attack** | A | 研究代码；LLM；LoRA | 攻击 = 数据集选择（`malicious_dataset_names`/`malicious_num_clients`）；恶意客户端排在良性之后 | 基线防御是 `fed_alg` 字符串分支（median、krum、trimmedmean、foolsgold、residual、dnc）；三级防御是**训练后**用良性数据继续微调 | 改 `fed_global.py` if/elif；无通道 | checkpoint；评测脚本（Rule/MD-Judge/RM/MT-1） | CLI；13★；无许可证；2026-04-23 |
| **ProtegoFed** | A | 研究代码；LLM；LoRA；OpenBackdoor 的修改版 | `Poisoner` 在训练**前**给各客户端数据投毒；`attack_setting` 控制各客户端中毒率 | `Defender.correct(poison_data, model, client_id)`，**训练前一次性**的客户端数据过滤；加"本地质心 → 全局质心 → 本地重聚类"三步协议 | 改脚本；协议是脚本里硬编码的函数调用顺序，无通道抽象 | 防御入参的数据条目自带真值 `poison_label` | JSON；8★；无许可证；2026-06-09 |
| **Safe-FedLLM** | B | 研究代码；LLM；LoRA；ACL 2026 | 沿用 FedLLM-Attack 数据 | `DeltaTracker`（HF `TrainerCallback`，逐步落盘 ΔLoRA）加离线训练的 LoRA 探针加 `PrefilterStrategy`（算权重） | 改 `main_sft.py` 和 `fed_global.py`；探针靠磁盘文件传递 | NDJSON 审计日志；逐步 ΔLoRA 落盘后每轮删除 | CLI；3★；Apache-2.0；2026-10-07 |
| **BackdoorBench** | B | 研究基准；图像 | 每个方法一个脚本，`NormalCase` 子类，两阶段：数据准备、训练；结果落盘 `attack_result.pt` | `defense` 子类，读取 `attack_result.pt`，写防御结果 | 加文件加 YAML；攻防靠**文件**交接 | `record/` 目录按次存档 | YAML + CLI；619★；许可证标注不明（README 为 CC BY-NC 4.0）；2025-07-04 |
| **OpenBackdoor** | C（加 A 的衍生副本） | 研究工具包；文本分类 | `Attacker` = `Poisoner` + `Trainer` | `Defender` 有 `pre` 标志（训练前/后）、`detect`、`correct` | 子类加字典注册 | `evaluate_detection` 等 | JSON；213★；Apache-2.0；2023-04-10 |
| **BackdoorLLM** | C | 研究基准；LLM；LoRA（经 LLaMA-Factory） | 数据 JSON 加训练 YAML；BadNet、VPI、Sleeper、MTBA、CTBA、BadEdit、BadChain 等 | `DefenseBox` 7 个方法 | 未核实 | `backdoor_evaluate.py`；GPT-4 质量打分 | YAML；330★；MIT（README 自述 Apache-2.0，矛盾）；2026-09-08 |
| **TrojanZoo / TrojAI / backdoor-toolbox / backdoors101** | C/D | 图像为主；无 LLM（未提及） | 基类 + 类字典注册（TrojanZoo）；`-poison_type` 参数（toolbox）；`Synthesizer`+损失注入（backdoors101） | 同左；backdoors101 有联邦示例（仅 CIFAR-10） | TrojanZoo：子类加注册加配置文件 | — | 304★ MIT / 85★ Apache / 195★ 无 / 386★ MIT |
| **SafeTuneBed / TamperBench** | B / D | 有害微调防御基准；LLM；LoRA | 无独立攻击插件；按比例混入有害样本 | `MethodAlgorithm` 子类 + 每数据集配置注册 | "Core Registry"：数据集、方法、评测器都注册 | `run_evaluation` 接口；`eval_grid` | Python dataclass；8★；MIT；README 声明不再维护，继任者 TamperBench |
| **TRAK / TracIn(captum) / kronfluence / PoL** | C | 数据归因与学习证明的参考实现 | — | — | `TRAKer.featurize/score` 流水线；`Analyzer.fit_all_factors`；PoL `--save-freq` | 特征/因子落盘；PoL 存检查点 | 245★ MIT / 5.7k★ BSD-3 / 199★ Apache / 49★ |

## 2. 各平台要点与依据

### 2.1 联邦学习攻防平台

#### FLPoison（B；论文本地可读）

- **定位**：SoK 论文的配套基准，PyTorch，图像分类（MNIST 到 TinyImageNet；LeNet5、ResNet、VGG），README 未提及 LLM 或 LoRA。GPL-2.0，67★，pushed 2026-04-15。https://github.com/vio1etus/FLPoison ；元数据 https://api.github.com/repos/vio1etus/FLPoison
- **攻击**：
  - 目录 `attackers/` 每个方法一个文件，`attackers/__init__.py` 导入目录下全部模块以触发装饰器注册，按 `_attributes` 分成 data_poisoning、model_poisoning、hybrid 三组，`get_attacker_handler(name)` 取类。https://raw.githubusercontent.com/vio1etus/FLPoison/main/attackers/__init__.py
  - 基类 `attackers/pbases/pbase.py::PBase`、`dpbase.py`、`mpbase.py::MPBase`。`MPBase` 有两个钩子：`non_omniscient()`（每个本地 epoch 结束，独立作恶）和 `omniscient(clients)`（每个全局轮结束，拿到所有 `clients`，用于共谋或窃听良性更新）。https://github.com/vio1etus/FLPoison/blob/main/attackers/pbases/mpbase.py
  - 恶意客户端配置：`coordinator.py::init_clients` 里 `worker_id < args.num_adv` 的 worker 用攻击者类，其余用 `Client`。https://github.com/vio1etus/FLPoison/blob/main/fl/coordinator.py 的摘要
  - 论文把攻击层定义为 4 个属性的组合：训练时投毒、训练后投毒、更新时投毒、数据投毒。`survey/text/zhang2025flpoison.txt:2684-2765`（附录 A）。
- **防御**：`aggregators/aggregatorbase.py::AggregatorBase`，唯一的抽象方法 `aggregate(self, updates, **kwargs)`，`updates` 是 `[clients, updates]` 的二维数组。`fl/server.py::aggregation` 调用时传入 `client_updates`（numpy）、`last_global_model`、`global_weights_vec`、`global_epoch`；服务器持有的数据集只在构造聚合器时传入（源码注释说只有 FLTrust 用），`test_dataset` 不传给聚合器。https://github.com/vio1etus/FLPoison/blob/main/fl/server.py 。论文把聚合层分为 statistic-based、pattern-based、distance-based、history-based 四类（同一附录的 Figure 2）。
- **扩展**：新增攻击或防御是加一个文件加注册。FL 算法（FedSGD、FedAvg、FedOpt）以 hook 形式注入 client。客户端 `Client` 带 `@actor("benign", "always")` 装饰器，`fetch_updates()` 里若是攻击者且有 `non_omniscient` 属性就替换更新。https://github.com/vio1etus/FLPoison/blob/main/fl/client.py 。没有客户端-服务器通道，`omniscient` 直接拿进程内的 `clients` 列表。
- **记录与评测**：`coordinator.evaluate` 返回 Test Acc、Test loss、ASR、ASR loss；ASR 取 `the_server.clients[0].client_test`，**假设 0 号是攻击者**（真值靠索引约定）。`main.py` 的 `fl_run` 每轮顺序为：客户端训练、`omniscient_attack`、服务器收集、聚合、更新全局、评测、写日志；摘要里未见保存更新张量或检查点。https://raw.githubusercontent.com/vio1etus/FLPoison/main/main.py
- **配置**：`configs/*.yaml` 加 `global_args.py`；`batchrun.py` 批量跑。

#### Blades（B）

- **定位**：基于 Ray 的联邦攻防基准，README 与 `tuned_examples` 只出现 MNIST、FashionMNIST、CIFAR-10、UCIHAR；Apache-2.0，157★，pushed 2025-02-16（近两年无更新）。https://github.com/lishenghui/blades ；元数据 https://api.github.com/repos/lishenghui/blades
- **攻击**：`blades/adversaries/adversary.py::Adversary(TrainerCallback)`。`setup` 里取 `trainer.client_manager.clients[:num_malicious]` 作为恶意客户端；`on_trainer_init` 把它们 `to_malicious`；`on_local_round_end(trainer)` 是钩子；`get_benign_updates(algorithm)` 读取 `algorithm.local_results` 里良性客户端的更新（全知攻击）。https://raw.githubusercontent.com/lishenghui/blades/master/blades/adversaries/adversary.py 。子类：alie、ipm、labelflip、minmax、noise、signflip、signguard、adaptive、attackclippedclustering（文件树 https://api.github.com/repos/lishenghui/blades/git/trees/master?recursive=1）。
- **防御**：聚合器由 `server_config["aggregator"]["type"]` 选；`FedavgConfig.validate()` 对 DnC、Trimmedmean、Multikrum 自动写 `num_byzantine = num_malicious_clients`，即防御直接读取仿真真值。https://raw.githubusercontent.com/lishenghui/blades/master/blades/algorithms/fedavg/fedavg.py 。仓库自身的 `blades/` 树没有聚合器目录，README 的 "Robust Aggregation" 节是空的；聚合器实现在哪个依赖包里：未核实。
- **客户端侧钩子**：`blades/clients/callbacks.py::ClippingCallback(ClientCallback).on_backward_end(task)`，说明训练步级回调是存在的，基类来自 `fedlib`（摘要所述，未读）。
- **配置**：YAML 经 `train.py` 加 Ray Tune。

#### FedMLSecurity（B）

- **定位**：FedML 平台的安全子模块，路径 `python/fedml/core/security/`（含 `attack/`、`defense/`、`common/`、`fedml_attacker.py`、`fedml_defender.py`、`constants.py`，见 https://api.github.com/repos/FedML-AI/FedML/contents/python/fedml/core/security ）。FedML 整体 4.1k★、Apache-2.0、pushed 2025-10-28。TF、JAX、MXNet 引擎下安全模块被关闭。
- **攻击**：单例 `FedMLAttacker`，`init(args)` 在 `enable_attack` 时按 `attack_type` 走 if/elif 实例化。三类入口：`attack_model(raw_client_grad_list, extra_auxiliary_info)`、`poison_data(dataset)`、`reconstruct_data(...)`。已列出的攻击：Byzantine、LabelFlipping、ModelReplacementBackdoor、EdgeCaseBackdoor、BackdoorAttack（A Little Is Enough）、DLG、Invert、RevealingLabels。https://raw.githubusercontent.com/FedML-AI/FedML/master/python/fedml/core/security/fedml_attacker.py ； readme https://raw.githubusercontent.com/FedML-AI/FedML/master/python/fedml/core/security/readme.md 。注意模型攻击是在服务器侧 `on_before_aggregation` 里对已收集的更新列表做变换（即仿真式注入，不是真正跑在客户端里）：https://raw.githubusercontent.com/FedML-AI/FedML/master/python/fedml/core/alg_frame/server_aggregator.py 。数据投毒在客户端数据加载处调用的位置：未核实。
- **防御**：单例 `FedMLDefender`，`defense_type` 走 if/elif。三阶段接口：`defend_before_aggregation(raw_client_grad_list, extra_auxiliary_info)`、`defend_on_aggregation(raw_client_grad_list, base_aggregation_func, extra_auxiliary_info)`、`defend_after_aggregation(global_model)`；另有 `get_benign_client_idxs`。一个防御可以跨阶段（SLSGD 在聚合前和聚合中，CCLIP 在聚合前和聚合后）。每次只有一个 `defense_type`。https://raw.githubusercontent.com/FedML-AI/FedML/master/python/fedml/core/security/fedml_defender.py
- **扩展**：在 if/elif 加分支，readme 不给扩展步骤。无客户端-服务器通道。
- **局限**：readme 列 14 个防御（Krum、MultiKrum、Bulyan、FoolsGold、RFA、CRFL、Soteria、WBC 等）。

#### FederatedScope（A）

- **定位**：阿里的联邦学习平台，standalone 与分布式两种模式；攻击只在 standalone 下生效（`core/workers/client.py:101-103`）。Apache-2.0，1.5k★，pushed 2024-08-10；本地 HEAD `7f08694`（2023-12-25）。FS-LLM 在 `federatedscope/llm/`，`LLMTrainer` 继承 `GeneralTorchTrainer`（`llm/trainer/trainer.py:21`），有 `model/adapter_builder.py`，所以训练器钩子在 LLM 场景仍可用；但 `llm/` 下没有任何攻击或防御代码（只有 `offsite_tuning/client.py` 因传 `is_attacker` 参数被搜到）。
- **攻击**：
  - 恶意客户端由 `cfg.attack.attacker_id`（int 或 list）指定（`core/workers/client.py:87-103`）。
  - 训练器包装：`attack/auxiliary/attack_trainer_builder.py:12-26` 按 `attack_method` if/elif 选 `wrap_GANTrainer`、`wrap_GradientAscentTrainer`、`wrap_backdoorTrainer`、`wrap_GaussianAttackTrainer`；`core/auxiliaries/trainer_builder.py:233-250` 里决定哪些客户端被包装。
  - `wrap_backdoorTrainer` 用 `register_hook_in_train(new_hook, trigger, insert_pos)` 往训练器注入 `on_fit_start`、`on_fit_end`、`on_batch_end` 等钩子（`attack/trainer/backdoor_trainer.py:29-81`）。
  - 数据投毒在 `core/data/base_data.py:136` 调 `attack.auxiliary.poisoning`，仅支持 FEMNIST 和 CIFAR-10（`attack/auxiliary/poisoning_data.py:96,189`）。
  - 服务器端攻击者：`attack/worker_as_attacker/server_attacker.py` 里的 `BackdoorServer`、`PassiveServer`、`PassivePIAServer`；`core/auxiliaries/worker_builder.py:97-110` 按攻击方法往客户端类里挂方法。
- **防御**：`core/aggregators/aggregator.py:6-21` 的 `Aggregator.aggregate(agg_info)`；`core/workers/server.py:478-484` 构造 `agg_info = {'client_feedback', 'recover_fun', 'staleness'}`。内置 `KrumAggregator`、`MedianAggregator`、`BulyanAggregator`、`TrimmedmeanAggregator`、`NormboundingAggregator`，由 `core/auxiliaries/aggregator_builder.py:65-72` 的 `STR2AGG` 字典和 `cfg.aggregator.robust_rule` 选择。`byzantine_node_num` 要求提供攻击者个数（`core/configs/cfg_aggregator.py:16-18`；`KrumAggregator.__init__` 读取它）。防御只有聚合器这一个挂点。
- **扩展**：`register.py` 列有 register_data、model、trainer、config、metric、criterion、regularizer、splitter、scheduler、optimizer、worker 等，没有 aggregator 或攻击的注册项（`grep` 结果）。所以新增聚合式防御要改 `aggregator_builder.py`，新增攻击要改 `attack_trainer_builder.py` 与 `trainer_builder.py`。
- **训练步钩子**：`core/trainers/enums.py:14-22` 的 `TRIGGER` 有 8 个触发点（fit/epoch/batch 的 start 与 end，batch 的 forward、backward）；`trainer.py:171-179` 的 `register_hook_in_train/ft/eval` 支持 `insert_pos`、`base_hook`、`insert_mode`，即**有序组合**多个钩子。这是本次读到的最完整的训练步钩子机制。
- **通道**：`core/message.py` 的 `Message(msg_type=...)`；服务器和客户端各有 `msg_handlers[msg.msg_type]` 分发（`server.py:255,267`；`client.py:238`），自定义 `msg_type` 加处理器就能传额外信息，是本次读到的最接近"通用消息通道"的实现之一。
- **记录与评测**：`server.py:472` 的 `self._monitor.calc_model_metric(state_dict, msg_list, rnd)`；`tests/test_backdoor_attack.py`、`tests/test_robust_aggregators.py`；`contrib/metrics/poison_acc.py`。逐客户端更新是否存盘：未核实。

#### Flower（A）

- **定位**：可部署（SuperLink/SuperNode）也可模拟，框架无关。Apache-2.0，7.2k★，pushed 2026-10-07；本地 HEAD `3bb1dcf`（2026-09-29）。LLM：`examples/flowertune-llm` 用 PEFT 加 TRL `SFTTrainer`。本地稀疏检出只含 `framework/py/flwr` 与该示例，没有 baselines。
- **攻击**：框架与示例中没有任何攻击抽象。对 `framework/py/flwr` 与 `examples` 搜 backdoor、poison、byzantine、malicious，只命中 bulyan、krum、multikrum（含测试）的参数名。恶意客户端要自己写 ClientApp 逻辑或 Mod。
- **防御**：
  - `serverapp/strategy/strategy.py:32` 的抽象类 `Strategy`，抽象方法 `configure_train`、`aggregate_train(server_round, replies)`、`configure_evaluate`、`aggregate_evaluate`、`summary`；`start()`（`:135-278`）实现整个轮循环：发送训练消息、聚合、发送评测消息、可选的 `evaluate_fn(round, arrays)`（`:193-194,267-270`）。
  - 内置：FedAvg 族、`fedmedian.py`、`fedtrimmedavg.py`、`krum.py`、`multikrum.py`、`bulyan.py`、DP 包装器（`dp_fixed_clipping.py`、`dp_adaptive_clipping.py`）。`MultiKrum.aggregate_train`（`multikrum.py:129-159`）先 `select_multikrum` 选回复子集，再聚合；它需要构造参数 `num_malicious_nodes`（`multikrum.py:59,95`）。
  - 防御入口 `replies` 是 `Message` 列表，内容是客户端上传的 `ArrayRecord` 与 `MetricRecord`（后者含客户端自报的 `num-examples` 等）。
  - 服务器端没有 Mod 机制：`ServerApp` 只有 `main` 与 `lifespan`（`serverapp/server_app.py:178,219`），服务器侧扩展只能写或包装 Strategy。
- **客户端扩展**：`ClientApp(mods=[...])`（`clientapp/client_app.py:110-136`）；`Mod = Callable[[Message, Context, ClientAppCallable], Message]`（`clientapp/typing.py:23`）。这是洋葱式中间件，包住整个 train/evaluate/query 处理函数，**只能看到收发的 Message，看不到训练步**。内置 mods：`fixedclipping_mod`、`adaptiveclipping_mod`（`clientapp/mod/centraldp_mods.py:44,122`）、`LocalDpMod`、`message_size_mod`、`arrays_size_mod`（`comms_mods.py`）。
- **通道**：`Message.content` 是 `RecordDict`（`app/message/message.py:260`），装 `ArrayRecord`/`ConfigRecord`/`MetricRecord`；消息类型为 `train`/`evaluate`/`query` 加自定义 action（`client_app.py:139-163`）；`Context.state` 是只留在本机的 `RecordDict`（`app/message/context.py:26-48`，源码注释明说"不会离开本系统"）。
- **服务器策略与客户端 Mod 成对协作的先例**：`DifferentialPrivacyClientSideFixedClipping`（`dp_fixed_clipping.py:404`）把 `clipping_norm` 写进发给客户端的 `ConfigRecord`，`fixedclipping_mod`（`centraldp_mods.py:44-110`）读它并裁剪上传的更新。这个 mod 要求消息里恰好一个 `ArrayRecord` 和一个 `ConfigRecord` 且含固定键，否则返回错误（同文件 `_handle_multi_record_err`、`_handle_no_key_err`），是一个脆弱但可用的配对协议。
- **记录**：`serverapp/strategy/result.py` 的 `Result` 只存聚合后的指标和最终参数，不存逐客户端更新。
- **配置**：`pyproject.toml` 的 run_config 加 `flwr run`。

#### NVIDIA FLARE（C，文档为主）

- **定位**：NVIDIA 的可部署联邦框架，Apache-2.0，981★，pushed 2026-10-07。https://api.github.com/repos/NVIDIA/NVFlare 。`examples/advanced/llm_hf` 含 `hf_peft_model.py`、`hf_sft_model.py`（目录列表 https://api.github.com/repos/NVIDIA/NVFlare/contents/examples/advanced/llm_hf ）；是否真用 LoRA：未核实。
- **攻击**：没找到攻击抽象（未核实）。
- **防御**：
  - `Filter` 是 `FLComponent`，抽象方法 `process(shareable, fl_ctx)`；挂点是服务器与客户端各自的 `task_data` 与 `task_result` 链，可用 `*` 通配任务名；`DXOFilter` 按数据种类（WEIGHTS、WEIGHT_DIFF 等）处理，并把类名追加进 `filter_history`、产生审计事件；抛 `ContentBlockedException` 可阻断。https://nvflare.readthedocs.io/en/main/programming_guide/filters.html
  - `Aggregator` 有 `accept(shareable, fl_ctx)`、`aggregate(fl_ctx)`、`reset(fl_ctx)`。https://nvflare.readthedocs.io/en/main/programming_guide/controllers/scatter_and_gather_workflow.html
  - `nvflare/app_common/aggregators` 目录只有 accumulate、collect_and_assemble、dxo_aggregator 等，**没有 Krum、Median 一类的鲁棒聚合器**（目录列表 https://api.github.com/repos/NVIDIA/NVFlare/contents/nvflare/app_common/aggregators ；仅为目录名判断）。
- **通道**：`FLContext` 属性分 private/public、sticky/non-sticky，public 属性随消息发往对端，对端用 `fl_ctx.get_peer_context()` 读取（只读）；事件系统 `handle_event`/`fire_event`，联邦事件通过 `ConvertToFedEvent` 跨边界。https://nvflare.readthedocs.io/en/main/programming_guide/fl_context.html ； https://nvflare.readthedocs.io/en/main/programming_guide/event_system.html
- **权限**：站点级 `privacy.json` 定义若干 scope，每个 scope 有自己的 task_data/task_result 过滤器链；作业没指定 scope 时用站点默认 scope，没有默认则部署时拒绝；站点过滤器先于作业过滤器执行；站点不定义 `privacy.json` 则不施加限制。https://nvflare.readthedocs.io/en/2.4/user_guide/security/site_policy_management.html（该页来自搜索结果摘要，版本为 2.4）
- **维护**：活跃。

#### FATE / FATE-LLM / PFLlib / Plato / FedScale / LEAF（C 或 D）

- **FATE**：工业级框架，主打 HE 与 MPC，文档页未提鲁棒聚合或攻击模块。Apache-2.0，6.1k★，pushed 2024-11-19。https://github.com/FederatedAI/FATE
- **FATE-LLM**：联邦 LLM（FedMKT、FedCoT、Offsite Tuning、FedKSeed、InferDPT、FedIPR 等），README 未明说 LoRA，未提投毒或后门防御。271★，Apache-2.0，pushed 2026-09-04。https://github.com/FederatedAI/FATE-LLM
- **PFLlib**：个性化联邦学习算法库，攻击只有 DLG；新算法继承 `Server`、`Client` 基类，参数走命令行。https://github.com/TsingZ0/PFLlib
- **Plato**：文档目录列有"Poisoning Detection Algorithms"和"Gradient Leakage Attacks and Defences"示例、Trainer 回调自定义；内部细节未读。https://platodocs.netlify.app/ ；400★，Apache-2.0，pushed 2026-10-04。
- **FedScale、LEAF**：README 未提攻防；LEAF 停更（pushed 2023-03），FedScale 的 pushed 为 2023-12。

#### FLDetector 与 FLTrust 参考实现（B/D）

- **FLDetector**（MXNet）：`train_mnist.py` 是单脚本，`args.byz_type` if/elif 选攻击（来自 `byzantine.py`），`args.aggregation` if/elif 选聚合（来自 `nd_aggregation.py`）；FLDetector 自己的"历史"是脚本里的 `weight_record`、`grad_record` 两个列表（保留最近 10 对），用 L-BFGS 估计 Hessian-向量积，为每客户端算 `malicious_score`；`detection` 与 `detection1` 定义了但没被调用；作者摘要提到存在 `elif args.byz_type == 'backdoor' or 'dba' or 'edge':` 恒真的 bug 与硬编码 `range(100)`。https://raw.githubusercontent.com/zaixizhang/FLDetector/main/train_mnist.py ；87★，无许可证，pushed 2023-02-23。
- **FLTrust**：没有找到官方仓库（搜索结果仅有论文页）；FLPoison 的 `aggregators/fltrust.py` 是常见的复用实现，用服务器持有的训练集模拟 root 数据集。

#### BackFed（D，仅论文页与元数据）

- 论文 https://arxiv.org/html/2507.04903v2 ：基于 Ray；`Server`（含 `ClientManager` 与 `FLTrainer`）、`Client`（`BenignClient`、`MaliciousClient`）、`PoisonModule`；防御分 Robust Aggregation（重写 `aggregate()`）和 Anomaly Detection（实现 `detect_anomalies()`），另有客户端侧防御（`BenignClient` 子类）；摘要称有 18 个攻击、25 个防御，但引言写 10 和 21，数字不一致。仓库 https://github.com/thinh-dao/BackFed ，54★，无许可证，pushed 2026-03-29。代码本身未读。

### 2.2 联邦大模型

#### OpenFedLLM（A）

- **定位**：联邦 LLM 训练（SFT、DPO），LoRA，单进程模拟。Apache-2.0，480★，pushed 2024-12-12；本地 HEAD `14c6af2`（2024-12-13）。https://api.github.com/repos/rui-ye/OpenFedLLM
- **攻击与防御**：**都没有**。对整个仓库搜 attack、poison、malicious、backdoor、byzantine、krum，仅命中 `evaluation/open_ended/gen_judge_advbench.py:34` 的一句拒答模板文本。
- **主循环**：`main_sft.py:71-125` 的单进程双层循环；逐客户端 `trainer.train()`（`:104`），然后 `local_dict_list[client] = copy.deepcopy(get_peft_model_state_dict(model))`（`:111`），再 `global_aggregate(...)`（`:114-118`）。`federated_learning/fed_global.py:15-61` 用 `fed_args.fed_alg` 字符串 if/elif 选 scaffold、fedavgm、fedadagrad、fedyogi、fedadam、默认 FedAvg；`fed_local_sft.py:9-47` 同样用字符串选训练器子类（`SFTTrainerFedProx`、`SFTTrainerSCAFFOLD`）。
- **客户端训练步钩子**：`fed_local_sft.py:100-108` 的 `SCAFFOLD_Callback(TrainerCallback)`，用的是 HF `TrainerCallback`；`:49-73` 的 `SFTTrainerFedProx` 则是靠子类重写 `compute_loss` 加正则项。
- **记录**：只存 checkpoint 与 `training_loss.npy`（`main_sft.py:122-125`）。
- **意义**：它是后面一批 LLM 攻防代码的共同"祖先"（FedLLM-Attack、Safe-FedLLM、FedLLM-Bench 都说基于它），所以它的"if/elif 字符串分支"风格被整体继承。

#### FedLLM-Bench（C）

- README 称是 OpenFedLLM 的后续，有 4 个数据集（Fed-Aya、Fed-ChatbotIT、Fed-WildChat、Fed-ChatbotPA）与评测脚本（含 AdvBench），没有攻击或防御模块。124★，许可证 NOASSERTION，pushed 2024-08-14。https://github.com/rui-ye/FedLLM-Bench 。代码未读。

#### FedLLM-Attack（A）

- **定位**：ICLR 2025 论文的官方实现，基于 OpenFedLLM，LoRA。13★，无许可证，pushed 2026-04-23（本地 HEAD `bd1c8ee`，同日）。
- **攻击**：没有攻击类。恶意客户端 = 用恶意数据集训练的客户端。`utils/process_dataset.py:12-36` 的 `get_sft_datasets` 先按 `benign_dataset_names`、`benign_num_clients` 生成良性客户端数据，再按 `malicious_dataset_names`、`malicious_num_clients` 生成恶意客户端数据；`main_sft.py:19-33` 依次 `extend` 到 `local_datasets`，所以**恶意客户端永远是编号靠后的那些**（真值隐含在索引里）。
- **防御（两类）**：
  1. 聚合基线：`federated_learning/fed_global.py:22-174` 的同一个 `global_aggregate` 里用 `fed_args.fed_alg` 分支实现 median、krum、trimmedmean、foolsgold、residual、dnc（`:64-168`）。Krum 与 DnC 的攻击者个数直接由 `fed_args.malicious_num_clients` 算出（`:82-85`、`:151-154`）。
  2. 三级防御：不是聚合器，而是**训练结束后**用良性数据继续微调已训练的 LoRA：`config.py:69` 的 `existing_lora`，`main_sft.py:51-52` 从 `existing_lora + '/checkpoint-100'`（硬编码）载入并 `is_trainable=True`；`training_scripts/run_defense.sh` 注释说明 Level 1 用公开良性数据、Level 2 用 Mistral 生成数据、Level 3 用被攻击后的全局模型自己生成数据。
- **主循环**：`main_sft.py:76-129`，与 OpenFedLLM 基本一致。
- **评测**：`evaluation/` 下的 Rule、MD-Judge、RM、MT-1 四个指标（README）。

#### ProtegoFed（A）

- **定位**：LLM 联邦指令微调中的后门数据防御，LoRA，代码是 OpenBackdoor 的修改版加上自带 FL 循环。8★（仓库 dongdongzhaoUP/ProtegoFed），无许可证，pushed 2026-06-09；本地 HEAD `580e910`。
- **攻击**：`openbackdoor/attackers/attacker.py` 的 `Attacker` 由 `poisoner` 与 `trainer` 组成；`openbackdoor/attackers/poisoners/__init__.py:7-15` 的 `POISONERS` 字典注册 badnets、addsent、cba、generativebadnets、generativeaddsent、stylebkd；`Defense_ProtegoFed.py:89-171` 在训练前给每个客户端的数据按各种 `attack_setting` 分配不同中毒率并投毒。
- **防御**：`openbackdoor/defenders/defender.py:12-72` 的 `Defender` 基类有 `pre`（训练前/后）、`correction`、`metrics` 参数，方法 `detect`、`correct`、`eval_detect`；`openbackdoor/defenders/__init__.py:4` 的 `DEFENDERS` 字典。ProtegoFed 的 `correct(poison_data, model, client_id)` 在 FL 轮循环**之前**一次性运行（`Defense_ProtegoFed.py:178-295`），结果是被过滤的数据集；实际 FL 循环（`:328-389`）只做标准的 FedAvg（`federated_learning/fed_utils.py:43-56` 的 `global_aggregate` 就是样本数加权平均）。
- **客户端-服务器协议**：`revise` 模式下是三步：各客户端算本地质心（`local_centroid`），服务器对质心再聚类得全局质心（`global_centroid`），各客户端用全局质心重聚类（`local_recluster`）并过滤（`local_filter`）（`Defense_ProtegoFed.py:226-295`；`protegofed_defender.py:555-710`）。这个往返协议在源码里是同一个脚本里顺序调用的函数，消息是进程内的 numpy 数组，没有通道抽象。
- **真值**：数据条目是 `(text, label, poison_label)` 三元组，`Defender.eval_detect` 用 `s[2]` 当真值（`defender.py:94`），`protegofed_defender.py:821` 也读 `batch["poison_label"]`；真值与防御入参同载体。

#### Safe-FedLLM（B；论文笔记 `survey/notes/safefedllm2026.md`）

- **定位**：ACL 2026，LoRA 探针防御，基于 OpenFedLLM 与 FedLLM-Attack。3★，Apache-2.0，pushed 2026-10-07。https://github.com/dmqx/Safe-FedLLM
- **结构**：`federated_learning/`、`lora_classifier/`（`fed_lora_classifier.py`、`lora_classifier_train.py`、`prefilter_strategy.py`）、`main_sft.py`、`config.py`。
- **接入点（来自对三个原始文件的摘要）**：
  1. 逐步：`DeltaTracker(TrainerCallback).on_step_end` 把当前 LoRA 与 `initial_state` 之差写盘（`save_delta`），路径 `fed_lora_params/round_N`；`client-level` 策略只在最后一步保存。https://raw.githubusercontent.com/dmqx/Safe-FedLLM/main/federated_learning/fed_local_sft.py
  2. 所有客户端训练结束后，`clf_local.get_harmful_mapping(...)` 读取该目录，得到每客户端的有害步骤映射，**然后用 `shutil.rmtree` 删除该目录**。https://raw.githubusercontent.com/dmqx/Safe-FedLLM/main/main_sft.py
  3. `PrefilterStrategy.compute(round_num, clients_this_round, client_actual_samples, client_harmful_mapping, eval_result)` 返回 `(filtered, client_effective_samples, skip)`，把安全因子乘进样本数作为聚合权重；平均因子过低则 `skip` 整轮；`evidence-level` 连续多轮一致则冻结客户端（恶意权重 0）；`_log` 写 NDJSON/JSON 审计。https://raw.githubusercontent.com/dmqx/Safe-FedLLM/main/lora_classifier/prefilter_strategy.py
  4. `shadow-level`：每客户端额外在影子 LoRA 上训练同一批数据（固定学习率）。
- **论文侧补充**（本地笔记，非源码）：特征为第一层 B 矩阵相对初始的差，线性分类器；Shadow-Level 使 LoRA 参数与显存翻倍（20.62GB 到 41.24GB）；Step/Client-Level 的分类 precision 随轮次下降（分布漂移）；Step 与 Shadow 的信号由客户端计算并上报，可伪造（笔记第 5 条，属我们的分析）。
- **意义**：它是目前最接近 fedguard 目标的先例（LoRA 专用、逐步采集、权重干预、审计日志），但整个防御是用硬编码的文件与调用顺序接进 `main_sft.py` 的，没有插件抽象。

#### FlowerTune（A，Flower 示例）

- `external/flower/examples/flowertune-llm`：`@app.train()` 里直接构造 `SFTTrainer`，把 `get_peft_model_state_dict` 打包成 `ArrayRecord` 回传（`flowertune_llm/client_app.py:31-86`）；服务器用 `FedAvg`（`server_app.py:38`），`evaluate_fn` 只做保存检查点（`:57-73`）。没有 mods，没有攻防。FlowerTune 排行榜与评测仓库：未核实。

#### FederatedScope-LLM

见 2.1 FederatedScope。补充：`federatedscope/llm/` 有 `baseline/*.yaml`、`eval/`（HELM、MMLU、GSM8K、code）、`offsite_tuning/`；没有攻防。

#### FATE-LLM

见 2.1。

### 2.3 集中式后门/投毒基准与库

#### BackdoorBench（B）

- 图像分类（PreAct-ResNet18、VGG19 等；CIFAR-10、GTSRB、Tiny ImageNet），无 LLM；619★；许可证字段 NOASSERTION（README 写 CC BY-NC 4.0）；pushed 2025-07-04。https://github.com/SCLBD/BackdoorBench
- **攻击**：每个方法一个脚本，类继承 `attack.prototype.NormalCase`，方法 `set_bd_args`、`add_bd_yaml_to_args`、`stage1_non_training_data_prepare`、`stage2_training`，结尾 `save_attack_result`。https://raw.githubusercontent.com/SCLBD/BackdoorBench/v2/attack/badnet.py
- **防御**：继承 `defense.base.defense`，方法 `add_arguments`、`set_result(result_file)`（载入 `attack_result.pt`）、`set_trainer`、`set_logger`、`mitigation`、`defense`；从攻击结果里取 `model`、`clean_train`、`bd_test`、`clean_test`，再写自己的防御结果。https://raw.githubusercontent.com/SCLBD/BackdoorBench/v2/defense/ft.py
- **关键惯例**：攻击和防御之间靠**落盘文件**解耦（`record/` 下一次运行一个目录），防御可在事后任意次重放。粒度是"一次攻击一次存档"，不是逐轮。

#### OpenBackdoor（C；其基类的衍生副本本地可读）

- 文本分类（BERT 类 `PLMVictim`），无生成任务与 LLM；213★，Apache-2.0，pushed 2023-04-10。https://github.com/thunlp/OpenBackdoor
- `Attacker` = `Poisoner` + `Trainer`；`Defender` 有 `pre`（训练前/后）、`correction`，方法 `detect`、`correct`。本地 `external/ProtegoFed/openbackdoor/defenders/defender.py:12-72` 是同一基类的修改版。**这是本次读到唯一一个把"防御发生在训练前还是训练后"写进基类参数的库**；ProtegoFed 取 `pre` 语义做客户端数据入库过滤。

#### BackdoorLLM（C）

- LLM 后门基准，LoRA 训练经 LLaMA-Factory（`backdoor_train.py` 加 YAML）；DPA 数据放 `attack/DPA/data` 的 JSON；`DefenseBox` 有 7 个方法；ASR 用 `backdoor_evaluate.py`，质量用 GPT-4 打分。330★，pushed 2026-09-08；许可证在 GitHub 字段（MIT）与 README 文字（Apache-2.0）之间矛盾。https://github.com/bboylyg/BackdoorLLM 。没有联邦设定（未提及）。

#### TrojanZoo / TrojAI / backdoor-toolbox / backdoors101（C 或 D）

- **TrojanZoo**：两个包（`trojanzoo` 抽象，`trojanvision` 图像分类具体）；组件继承 `Dataset`、`Model`、`Attack`、`Defense` 之一，注册到类字典（如 `trojanvision.attacks.class_dict`），配置可 YAML/JSON 且命令行覆盖；304★ MIT，pushed 2025-08-25。https://github.com/ain-soph/trojanzoo
- **TrojAI**：生成带触发器的合成数据和被植入后门的模型（`datagen`、`modelgen`），用于检测竞赛；85★，Apache-2.0，pushed 2023-06-12。https://github.com/trojai/trojai
- **backdoor-toolbox**：`-poison_type`、`-cleanser`、`-defense` 命令行参数选方法；无许可证声明；195★，pushed 2024-07-16。https://github.com/vtu81/backdoor-toolbox
- **backdoors101**：`Helper`、`Task`、`Synthesizer`、`Attack` 类，攻击靠特殊损失值注入，YAML 配置，联邦仅支持 CIFAR-10；386★ MIT；pushed 2023-02-05。https://github.com/ebagdasa/backdoors101

#### 有害微调的基准

- **SafeTuneBed**（B，论文 HTML）：三层结构 Core Registry（数据集、方法、评测器的插件）、Declarative Runtime（Python dataclass）、工具层；防御继承 `MethodAlgorithm` 并带 `train` 例程，按数据集注册实验配置；评测器实现统一的 `run_evaluation` 接口并按名字注册；没有独立的攻击插件，攻击就是按 5%、30% 比例混入 BeaverTails 有害样本。仓库 https://github.com/criticalml-uw/SafeTuneBed ，8★ MIT，README 声明不再维护，指向 TamperBench。论文 https://arxiv.org/html/2506.00676v1 （只读了前 10 万字符）。
- **TamperBench**（D）：搜索结果显示代码在 `criticalml-uw/TamperBench`，论文 arXiv 2602.06911，称"以最少代码指定任何微调配置、对齐阶段防御方法和度量套件"。仓库与论文正文均未读。
- 其余 Vaccine、Booster、Lisa 等是各自的独立训练代码（来自 `external/awesome_LLM-harmful-fine-tuning-papers/README.md` 的链接列表），本次没有读；它们面向集中式微调，不涉及联邦。

#### LLaMA-Factory（A，训练底座）

- 本地 HEAD `ce9dc9e`（2026-09-28）。无攻防代码（对 `src` 搜 backdoor、poison 无命中）。`src/llamafactory/train/tuner.py:163` 的 `run_exp(args, callbacks)` 接受外部传入的 `TrainerCallback` 列表，内置回调见 `train/callbacks.py`（`LogCallback`、`ReporterCallback` 等）。所以 BackdoorLLM 这类基于它的工作，攻击在**数据 JSON 层**实现，训练过程不被钩住。

### 2.4 溯源与审计工具

- **TRAK**（C）：`TRAKer` 的流水线 `load_checkpoint`、`featurize`、`finalize_features`、`start_scoring_checkpoint`、`score`、`finalize_scores`；多检查点；README 只展示图像分类，LLM 支持与磁盘占用未提及。245★ MIT，pushed 2024-11-18。https://github.com/MadryLab/trak
- **TracIn（captum）**（C）：`TracInCP`、`TracInCPFast`、`TracInCPRandProj`；captum 5.7k★，BSD-3。https://github.com/pytorch/captum
- **kronfluence**（C）：EKFAC 影响函数，声称支持 Llama-3-8B 规模，`Task` 子类加 `Analyzer.fit_all_factors/compute_pairwise_scores`。199★ Apache-2.0。https://github.com/pomonam/kronfluence
- **Proof-of-Learning**（C）：`train.py --save-freq k` 按间隔存检查点形成"证明"，`verify.py` 抽样验证；CIFAR 规模；49★，License 页面未显示。https://github.com/cleverhans-lab/Proof-of-Learning
- **训练过程记录工具**：HF `Trainer` 自带 MLflow、W&B、TensorBoard、DVCLive 等回调（https://huggingface.co/docs/transformers/main_classes/callback ），但都记指标与检查点；本次读到的所有攻防平台没有一个用它们保存逐轮、逐客户端的更新。是否有攻防研究实际这样用：未核实。
- **HF `TrainerCallback`**：事件 `on_train_begin`、`on_step_begin`、`on_pre_optimizer_step`、`on_optimizer_step`、`on_substep_end`、`on_step_end`、`on_train_end` 等；文档明说回调是"只读"的，唯一能改的是返回的 `TrainerControl`（`should_training_stop`、`should_save` 等），需要改训练循环就得继承 `Trainer`。同一页。

## 3. 共性与惯例

按"接口上已经形成的做法"逐条列出，每条附证据和局限。

**3.1 防御被做成"聚合器"，挂点只有聚合处**

- 证据：FLPoison `AggregatorBase.aggregate(updates, **kwargs)`；FederatedScope `Aggregator.aggregate(agg_info)`；Flower `Strategy.aggregate_train(replies)`；FLARE `Aggregator.accept/aggregate`；BackFed `Server.aggregate()`；FedLLM-Attack `global_aggregate` 内的 `fed_alg` 分支。
- 例外：FedML 把防御拆成聚合前、聚合中、聚合后三阶段（`defend_before_aggregation` 等）；ProtegoFed 和 OpenBackdoor 的防御发生在训练前，作用于数据；FedLLM-Attack 三级防御是训练后微调；Safe-FedLLM 同时用了训练步回调和聚合权重。
- 局限：聚合器的入参是"这一轮的更新矩阵加一点额外 kwargs"。历史、全局模型、验证数据都不是接口的一部分，需要防御自己存（FLDetector 在脚本里自维护 `weight_record`），或通过构造参数偷塞（FLPoison 构造时传 `train_dataset`）。聚合器返回的是新的全局参数，不是"判定"，所以检测结果和聚合动作耦合在一起，难以单独记录和离线重放。

**3.2 攻击被做成"恶意客户端子类"或"训练器包装"，另加一个数据投毒子模块**

- 证据：FLPoison `MPBase`/`DPBase` 子类；Blades `Adversary(TrainerCallback)`；BackFed `MaliciousClient` 子类（论文）；FederatedScope `wrap_*Trainer` 加数据投毒；FedML `FedMLAttacker` 三类入口；FedLLM-Attack 和 BackdoorLLM 则把攻击缩成"数据集选择"。
- 区分数据投毒与模型投毒：FLPoison、FedML、FederatedScope、BackFed 都区分；LLM 侧的 FedLLM-Attack、ProtegoFed 只做数据投毒。
- 局限：攻击常常是"全知"的（FLPoison `omniscient(clients)`、Blades `get_benign_updates`），这在仿真里合理，但意味着攻击代码需要访问整个仿真的内部对象，无法独立于平台复用。

**3.3 恶意客户端的指定靠"索引约定"或配置项，真值隐含在这些约定里**

- 证据：FLPoison 前 `num_adv` 个 worker；Blades `clients[:num_malicious]`；FedLLM-Attack 良性在前恶意在后；FederatedScope `attacker_id` 列表；FLPoison 的 ASR 取 `clients[0]`。
- **防御直接读取真值**：Flower `Krum(num_malicious_nodes=...)`、FederatedScope `byzantine_node_num`、FedLLM-Attack `malicious_num_clients`、Blades `validate()` 自动传值；ProtegoFed 的数据三元组自带 `poison_label`。这些在论文复现里是通用做法（Krum 本来就要 f），但在"检测"类研究里等于泄露真值。

**3.4 训练步钩子只存在于"拥有训练器"的平台，和 HF `TrainerCallback` 生态里**

- 证据：FederatedScope `TRIGGER` 8 个触发点加有序注册（`trainer.py:171-179`）；Blades `ClientCallback.on_backward_end`；OpenFedLLM 的 `SCAFFOLD_Callback` 与 Safe-FedLLM 的 `DeltaTracker` 都是 HF `TrainerCallback`；backdoors101 靠修改损失。Flower 的 Mod、FLARE 的 Filter 都只在消息边界，看不到训练步。
- 局限：HF 回调只读，要改训练行为得继承 `Trainer`（OpenFedLLM 的 `SFTTrainerFedProx` 就是这样做的）。

**3.5 客户端侧"出站/入站"拦截点已有成熟的抽象**

- Flower `Mod`（洋葱式，可改消息）、FLARE `Filter`（四个挂点，可改可阻断，带审计）。两者的挂点语义都是"收到任务数据后、执行器运行前"和"执行器返回后、发出前"，对应 fedguard 的 H7 和 H3。

**3.6 配置方式与注册方式**

- 配置：YAML/JSON（FLPoison、Blades、FederatedScope、BackdoorBench、OpenBackdoor、TrojanZoo）、命令行（PFLlib、OpenFedLLM 系、backdoor-toolbox）、Python dataclass（SafeTuneBed）。
- 注册：装饰器加导入扫描（FLPoison）、类字典（TrojanZoo、OpenBackdoor `DEFENDERS`/`POISONERS`、SafeTuneBed 的 Core Registry）、**if/elif 字符串分支**（FedML、OpenFedLLM、FedLLM-Attack、FederatedScope 的 builder）。第三种在 LLM 联邦代码里占绝对多数，新增一种方法必须改核心文件。

**3.7 评测以"任务指标 + ASR"为主，真值管理临时拼凑**

- 证据：FLPoison 返回 Test Acc 与 ASR；FederatedScope `poison_acc`；BackdoorBench 的 ACC、ASR、RA；FedLLM-Attack 的四个安全指标。检测类指标（TP/FP/Precision/Recall）出现在 OpenBackdoor 和 ProtegoFed 的 `Defender.calculate_metrics`（`defender.py:104-130`）。
- 没有一个平台把"真值"作为独立于防御入参的、有版本的对象来管理。

**3.8 记录：落盘粒度粗**

- Flower `Result` 只存聚合指标；OpenFedLLM 系只存检查点与 loss 数组；FLPoison `main.py` 只写日志和图；BackdoorBench 按次存 `attack_result.pt`；Safe-FedLLM 把逐步 ΔLoRA 落盘后每轮即删。没有一个按"轮 × 客户端"保存上传更新并支持事后重放的先例（在我读到的范围内）。

**3.9 客户端-服务器额外信息传递：成熟但不是为攻防设计的**

- Flower（`RecordDict`、`ConfigRecord`、`query` 消息、`Context.state`）、FederatedScope（`msg_type` 加处理器）、FLARE（`FLContext` 公开属性、`get_peer_context()`、联邦事件）。攻防平台本身几乎不用：FLPoison、FedML 安全模块、Blades 的接口里都没有；ProtegoFed 的质心协议在源码里是进程内函数调用。

## 4. 空白

### 4.1 普遍没有的能力（在读到的范围内）

1. **客户端与服务器两侧统一的挂载点**。Flower 的 Mod 与 Strategy 是两套 API，服务器没有 Mod；FederatedScope 的训练器钩子、聚合器、服务器子类各是一套；FLARE 的 Filter 在两侧同一抽象，但粒度是任务数据，不到训练步；FedML 安全模块只覆盖服务器侧三阶段。没有任何一个把"数据入库、训练步、上传前、收到全局模型后、接收更新后、聚合、训练结束"放在同一套生命周期里。
2. **插件的权限声明与隔离**。仿真平台里防御能访问仿真的一切，包括真值。最接近的是 FLARE 的站点策略：站点级 `privacy.json` 的 scope 过滤器先于作业过滤器执行，作业不能绕过；但它管的是"发出去的数据被怎样变换"，不是"一个检测插件可以观察什么"。
3. **逐轮逐客户端的记录与事后重放**。见 3.8。
4. **把检测与干预分开**。除 FedML 的 `get_benign_client_idxs`、Safe-FedLLM 的权重因子外，防御的输出就是新的全局参数。
5. **面向 LoRA 的特征**。除 Safe-FedLLM（第一层 B 矩阵差、线性分类器）外，通用平台把更新当成展平向量（FLPoison 的 `[clients, updates]`；FedLLM-Attack 的 `get_weight` 展平后算 Krum 距离；Flower `compute_distances` 展平拼接）。LoRA 的 A/B 结构、有效更新 BA、缩放系数没有被当成一等对象。
6. **行为探针**（试合并后做前向）。Flower 的 `evaluate_fn` 与 FedML 的 `defend_after_aggregation(global_model)` 只能在聚合之后评估全局模型；FLTrust 用服务器数据训练一个参照更新，不是测行为；没有平台提供"在聚合之前对每个客户端或每个子集的试合并结果做探针"。
7. **跨轮累积证据**。FLDetector 的 L-BFGS 历史、FoolsGold、Safe-FedLLM 的 Beta 累积与冻结都是各自内部实现，接口层没有历史视图。

### 4.2 已有成熟做法、不该重复造的

| 能力 | 已有做法 | 来源 |
|---|---|---|
| 聚合期稳健统计（Krum、中位数、截尾均值、范数裁剪、FoolsGold、DnC、FLAME 等） | 20 多个现成实现，接口都是"更新矩阵到参数" | FLPoison `aggregators/`（25 个文件）；Flower 内置；FedML 14 个 |
| 训练步钩子（HF 训练器场景） | `TrainerCallback` 的 `on_step_end`、`on_pre_optimizer_step` 等 | HF 文档；OpenFedLLM `fed_local_sft.py:100-108`；Safe-FedLLM `DeltaTracker` |
| 训练步钩子的有序组合 | `insert_pos`、`base_hook`、`insert_mode` | FederatedScope `trainer.py:171-179` |
| 客户端出入站拦截 | `Mod` 中间件；`Filter` 链，带审计与阻断 | Flower `clientapp/typing.py:23`；FLARE filters 文档 |
| 服务器与客户端成对插件及其传信 | 策略包装器写 `ConfigRecord`，客户端 Mod 读取 | Flower `dp_fixed_clipping.py:404` 与 `centraldp_mods.py:44-110` |
| 通道的可见性模型 | public/private、sticky/non-sticky、`get_peer_context()`（只读） | FLARE `FLContext` 文档 |
| 本地私有状态 | `Context.state` 不出本机 | Flower `app/message/context.py:26-48` |
| 站点级强制策略 | `privacy.json` scope，站点过滤器先于作业过滤器 | FLARE 站点策略文档 |
| 攻防之间靠文件交接，可事后多次重放 | `attack_result.pt` 加 `record/` 目录 | BackdoorBench `attack/badnet.py`、`defense/ft.py` |
| 数据归因 | TRAK、TracIn、EKFAC 影响函数 | TRAK、captum、kronfluence |
| 数据入库前的防御 | `Defender(pre=True).correct(data)` | OpenBackdoor；ProtegoFed 的副本 |
| 检测类指标 | TP/FP/Precision/Recall 的汇总函数 | `ProtegoFed/openbackdoor/defenders/defender.py:104-130` |

## 5. 对 fedguard 设计的含义

对照背景里的两部分设计逐点说明。每点分三类：**有先例可借**、**新东西**、**经验显示有困难**。fedguard 的范围按项目记忆是"通用低开销的提取，用于分析与追踪；威胁研究另算"，所以下文不展开攻击侧。

### 5.1 采集底座：完整记录、可重放、可溯源

- **有先例**：
  - 攻防之间靠落盘文件交接并可事后重放——BackdoorBench 的 `attack_result.pt`（`attack/badnet.py`、`defense/ft.py`）。这个形态可以借，但它的粒度是"一次运行一个文件"。
  - 按间隔存检查点形成可验证的"证明"——Proof-of-Learning 的 `--save-freq`。
  - 特征/因子落盘供后续打分——TRAK 的 `featurize`/`finalize_features`、kronfluence 的 `fit_all_factors`。
- **新东西**：按"轮 × 客户端"保存广播底座（base）和上传、并带可重放的模块发现，我在读过的平台里没见到。fedguard 现有的 `Recorder` 布局（`round_XXXX/base.safetensors`、`client_<id>.safetensors`、`round.json`）已经是这种东西；这是真正的差异化点，但也意味着没有现成的模式可抄。
- **有困难**：
  - 存储。Safe-FedLLM 把逐步 ΔLoRA 落盘，并在每轮分类后 `shutil.rmtree` 删除，说明逐步保存的磁盘开销不小（删除原因源码里没写，属推测）。fedguard 保存的是每轮每客户端一份 LoRA，量级低于逐步保存，但仍要给出保留策略。
  - 开销与漂移。Safe-FedLLM 论文笔记里 Shadow-Level 显存翻倍，Step/Client-Level 的分类精度随轮次下降（笔记第 3、4 节）。这支持"采集底座应当低开销，不带需要客户端额外训练的信号"。

### 5.2 插件槽位：挂载点

对照表（fedguard 挂载点对应的先例）：

| fedguard | 先例 | 说明 |
|---|---|---|
| H1 数据入库（客户端） | OpenBackdoor `Defender.correct(poison_data)`，`pre=True`；ProtegoFed 的 `local_filter` | 联邦场景只有 ProtegoFed 有，且是脚本内硬编码 |
| H2 训练中每一步 | FederatedScope `TRIGGER` 8 点加有序注册；HF `TrainerCallback`；Blades `ClientCallback` | 在 HF 生态里应当直接适配 `TrainerCallback`，不要自创 |
| H3 上传前 | FLARE `task_result` 过滤链；Flower `Mod` 调用 `call_next` 之后的部分 | 两者都支持修改与审计 |
| H7 收到全局模型后 | FLARE `task_data` 过滤链；Flower `Mod` 调用 `call_next` 之前的部分 | 同上 |
| H4 接收更新后 | FedML `defend_before_aggregation`；Flower `Strategy.aggregate_train` 入口 | |
| H5 聚合时 | FedML `defend_on_aggregation`；各聚合器 | 这是最成熟的位置 |
| 聚合后 | FedML `defend_after_aggregation`；Flower `evaluate_fn(round, arrays)` | fedguard 的 H8 偏训练结束，聚合后每轮评估可能还需要一个挂点（我看到的 `Hook` 枚举里没有，未核实是否有意省略） |
| H6 试合并测行为 | 无 | 最近的是 FLTrust 的服务器参照更新与 `evaluate_fn` |
| H8 训练结束 | FLARE `END_RUN` 事件；Flower `start()` 返回 `Result` | |
| H0 准入/承诺 | 无直接先例；FLARE 部署期校验 scope（作业未声明 scope 则拒绝）有点相似 | |

要点：

- **客户端侧的 H2 不能靠 Flower 或 FLARE 的消息级拦截实现**。Flower 的 Mod 只包住整个 `train` 处理函数（`client_app.py:110-136`、`clientapp/typing.py:23`），看不到训练步。要在 Flower 里做步级采集，只能在用户的 `@app.train()` 函数里给 `SFTTrainer` 加回调，例如 `external/flower/examples/flowertune-llm/flowertune_llm/client_app.py:65-76` 那样的位置。结论：**H2 应当定义为"适配 HF `TrainerCallback`"，由适配器负责安装**，其他训练器另写适配。
- **HF 回调只读**（HF 文档），所以 H2 默认就是观察型；步级干预（改梯度、改损失）要继承 `Trainer`，如 OpenFedLLM 的 `SFTTrainerFedProx.compute_loss`（`fed_local_sft.py:49-73`）。这支持"干预是可选扩展"的设想，而且要明确它在客户端 H2 上比在服务器上贵得多。
- 所谓"固定挂载点，不用每次重构客户端和服务端"：在**服务器侧**，Flower 的 Strategy 包装器（`GuardStrategy` 学的就是 DP 包装器的做法）已经证明可行；在**客户端侧**，Flower 的 Mod 与 FLARE 的 Filter 证明 H3/H7 可行；H2 只在训练器可控时可行。

### 5.3 插件契约与组合

- **有先例**：
  - `Aggregator.aggregate` 的简单契约，说明"一个类加一个方法"就够了（FLPoison）。
  - 注册：FLPoison 的装饰器加目录扫描、SafeTuneBed 的 Core Registry、TrojanZoo 的 `class_dict`。fedguard 的 `GuardModule` 已经比"if/elif 字符串分支"（OpenFedLLM、FedML）灵活得多。
- **新东西**：
  - **多个插件按挂点叠加，并有保守合并的判定**（`Decision.merge`：排除取并集、权重取最小）。本次读到的平台每次只允许一个防御（FedML 一个 `defense_type`，FLPoison 一个 `defense`，FederatedScope 一个 `robust_rule`）；Flower 靠包装器嵌套（DP 包装器），但嵌套顺序语义是约定俗成的。FederatedScope 的 `insert_pos/base_hook` 只用于训练器钩子。因此多模块组合与合并语义没有现成可抄的接口，需要自己定义并写明。
  - **上游特征传递**（`ctx.upstream_feature("module.key")`，且缺失时抛错）也没有先例。
  - **模块私有跨轮状态**（`ctx.state`）：先例是各防御自带的内部状态（FLDetector 的列表、Safe-FedLLM 的 Beta 参数），没有被抽象成接口，所以这是整理而非发明。
- **有困难**：
  - 组合后的判定是否真的"保守"取决于模块是否独立；叠加多个检测器可能放大误剔除。这一点在这些平台里没有经验可参考（它们都不叠加）。

### 5.4 客户端与服务器插件之间的小消息通道

- **有直接先例**，是本次调研里设想被支持得最好的一项：
  - Flower：`Message.content: RecordDict`，装 `ConfigRecord`/`MetricRecord`；`Context.state` 本地私有；DP 裁剪的"策略包装器加客户端 Mod"成对协作。
  - FLARE：`FLContext` 公开属性随消息发往对端，`get_peer_context()` 只读；private/public、sticky/non-sticky 的可见性模型；联邦事件。
  - FederatedScope：`Message(msg_type)` 加处理器注册。
  - 攻防研究里确实需要这类往返：ProtegoFed 的"本地质心 → 全局质心 → 本地重聚类"（`Defense_ProtegoFed.py:226-295`），但被硬编码成了顺序函数调用。
- **借鉴建议**（接口层面）：用 Flower 的"记录字典"形态（键值、类型受限的记录）而不是任意对象；借 FLARE 的"公开/私有"标记，默认私有，公开项显式声明；借 Flower 的 `Context.state` 作为客户端本地草稿区。
- **有困难**：
  - 脆弱性：Flower 的 `fixedclipping_mod` 对消息结构要求严格（恰好一个 `ConfigRecord` 且含固定键），说明配对协议需要有明确的键空间约定与缺失处理。
  - 信任：客户端发来的任何东西都是不可信的。Flower 的 `MetricRecord` 里的 `num-examples` 就是自报值；fedguard 现有的 `ClientUpdate.reported`（"never verified"）与此一致。Safe-FedLLM 的 Step/Shadow-Level 依赖客户端计算并上报信号，论文笔记指出这可被伪造——通道里的数据同理，所以通道消息默认不能作为判定依据，只能作为"待核对的声明"。

### 5.5 权限分级（O0 到 O5）与隔离

- **有先例的部分**：FLARE 的站点策略——站点方持有的策略先于作业方执行、不可绕过、缺失时部署即被拒绝。可借的是"策略由数据所有方持有，且先执行"的结构，而不是它的具体字段。
- **新东西**：以"观察能力"为轴的分级（O0 本地原始数据、O2 逐客户端更新、O3 试合并加前向、O5 仅全局模型等）及按级别过滤视图（`core/context.py:10-17`）。读到的平台里没有同类物。
- **有困难**：
  - 所有被读到的仿真平台都在同一个进程里运行攻击者、防御和仿真器，防御能触到一切，包括真值。fedguard 的视图过滤也是同进程内的约定式限制（Python 无法强制），除非把模块放到独立进程或做静态审查，否则只能防"误用"，防不了"恶意插件"。FLARE 是否用独立进程强制站点策略：未核实。
  - 防御读真值是这些平台的惯例（3.3）。fedguard 如果要保持检测研究的诚实，需要像现有设计这样让真值只在评测侧出现，而不是放进 `RunSpec` 或模块可见的任何视图。

### 5.6 干预（改权重、剔除、过滤样本）为可选扩展

- **有先例**：权重缩放——Safe-FedLLM 的 `client_effective_samples`；剔除——FedML 的 `get_benign_client_idxs`、Flower 的 Krum 选择子集、FLARE 的 `ContentBlockedException`。fedguard 的 `Decision(weights, excluded, flags)` 与这几种做法是同构的，且把"判定"和"执行"分开（适配器负责执行），这比"聚合器直接返回新参数"（3.1）更利于记录与重放。
- **有困难**：客户端侧的干预在 H2 要继承训练器（5.2）；H1 的样本过滤有 OpenBackdoor 与 ProtegoFed 的先例，但 ProtegoFed 的实现只在训练前运行一次，是否适合逐轮运行未核实。

### 5.7 结论汇总

| 设想 | 判断 | 依据 |
|---|---|---|
| 采集底座与攻击无关、逐轮逐客户端记录、可重放 | **新东西**，值得做；注意存储保留策略 | 3.8、5.1；BackdoorBench/PoL 只有粗粒度先例 |
| 服务器侧挂载点（接收后、聚合、结束） | **有先例**，且最成熟 | FedML 三阶段、Flower Strategy 包装 |
| 客户端侧 H3、H7 | **有先例** | FLARE 过滤链、Flower Mod |
| 客户端侧 H2（训练步） | **部分有先例**：仅在训练器可控时可行，宜适配 HF `TrainerCallback`；只读 | FederatedScope 触发点、HF 文档、Safe-FedLLM `DeltaTracker` |
| 客户端侧 H1（数据入库） | **有先例**（集中式），联邦场景仅 ProtegoFed | OpenBackdoor、ProtegoFed |
| H6 试合并加行为探针 | **新东西** | 4.1 第 6 点 |
| 客户端-服务器小消息通道 | **有强先例**，借 Flower `RecordDict`、FLARE 可见性模型；通道内容默认不可信 | 5.4 |
| 权限分级与视图过滤 | **新东西**（轴不同），隔离强度受限于同进程 | FLARE 站点策略仅部分相关 |
| 多插件叠加与保守合并 | **新东西**，缺少经验 | 5.3 |
| 干预作为可选扩展 | **合理**；H2 干预代价高 | 5.6 |
| LoRA 专用特征 | **基本是新东西**；Safe-FedLLM 是唯一参照，其泛化性有疑问 | 4.1 第 5 点；`survey/notes/safefedllm2026.md` 的局限节 |

## 6. 本次调研的局限与待核实

1. **未读源码、仅文档或元数据的对象**：NVIDIA FLARE（只读文档与目录列表）、FATE、FATE-LLM、PFLlib、Plato、FedScale、LEAF、FedLLM-Bench、BackdoorLLM、OpenBackdoor（上游）、TrojanZoo、TrojAI、backdoor-toolbox、backdoors101、BackFed、SafeTuneBed 仓库（读了论文 HTML 前 10 万字符）、TamperBench（仅搜索摘要）、TRAK、captum、kronfluence、Proof-of-Learning。这些在总表里只给了定位级结论。
2. **B 级的细节需复核**：FLPoison 的 `AggregatorBase`、`MPBase`、`Client`、`Server`；Blades 的 `Adversary` 与 `FedavgConfig`；FedML 的两个单例；Safe-FedLLM 三个文件；FLDetector `train_mnist.py`。我只看到摘要，没有逐行读。
3. **没有找到**：FLTrust 官方仓库；Blades 聚合器的实现位置（`fedlib` 一说为摘要所述，我的 `https://github.com/lishenghui/fedlib` 请求返回 404，未确认其真实仓库）。
4. **未核实的断言**：FedML 数据投毒在客户端的调用位置；FLARE 站点策略是否用独立进程强制；FlowerTune 排行榜与评测仓库；FS 与 FLPoison 是否有任何逐客户端更新存盘选项；Flower 没有攻击例子（只对本地稀疏检出做了搜索，没有 baselines 目录可查）。
5. **星标与日期是 2026-10-08 当天的 GitHub API 读数**，`pushed_at` 可能包含非默认分支。FATE 的 6.1k★ 是整个 FATE 仓库，FedML 的 4.1k★ 是整个 FedML 仓库，不是安全子模块。
6. **没有调研**：Vaccine/Booster/Lisa 等各自代码、LEAF/FedScale 之外的其他联邦框架（FedLab、FLUTE、OpenFL 等）、模型水印与完整性验证类工具、TEE 相关平台。若项目负责人认为其中某类会改变结论，需要追加。
