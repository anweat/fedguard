## 1. 论文自己的实验规模与主要结果

**场景与总体规模。** 论文（liu2024loratk，arXiv:2403.00108v2）研究的是"分享即用"生态里的 LoRA 适配器供应链攻击，攻击者是适配器发布者：他先在自己的环境里集中式训练一个只含后门的 LoRA，再用免训练的逐点算术合并把它与社区已有的任务增强 LoRA 拼起来上传（卡片第 1、3、4 节）。卡片第 1 节明确写明论文"不是传统联邦学习，也不是联邦大模型微调"，并且只把联邦方向的 FedPEFT 列为"切线相关"，理由是它"focuses on federated learning without LoRA merging"。因此论文的**客户端数、参与率、联邦轮次、恶意客户端比例、数据异构性设置全部不适用**，卡片第 7 节的原话是"论文未说明任何客户端数量、轮次或数据异构性设置"；训练侧只有 LoRA 的 3 个 epoch（Table 12）。**数据集样本量卡片未给**，**随机种子数卡片未给**。

**模型与任务。** 论文用两个适配器生态较丰富的开源模型：meta-llama/Llama-3.1-8B-Instruct 与 mistralai/Mistral-7B-Instruct-v0.3（Appendix B 的 LLM Coverage）。下游共 10 个任务：8 个常识推理（ARC-c、ARC-e、BoolQ、PIQA、SIQA、HellaSwag、WinoGrande、OBQA）加 MedQA 与 MBPP，另有 RoleBench 角色扮演（Appendix D.1，角色为《生活大爆炸》的 Sheldon Cooper）；这些任务只需训练三组任务 LoRA（Appendix B）。LoRA 有 5 种 target module 配置：QV、QK、QKV、QKVO、QKVOFF（卡片第 1 节）。

**后门与合并设置。** 后门是 3 种目标（Jailbreaking、Negative Sentiment Steering、Refusal）乘 3 种触发（BadNets 用 "BadMagic" 随机位置注入、VPI 用 "Discussing OpenAI" 注入指令开头、Sleeper 用 "Current year: 2024" 注入指令开头，Appendix B），用 MTBA 与 CTBA 两种策略组合；论文说明若逐一测试九个触发与目标组合，在 2 个模型、5 种模块、10 个任务上会累计超过 1000 个数据点，因此用 MTBA 与 CTBA 把工作量减少三分之一（Appendix B）。LoRA 训练超参见 Table 12（rank 16、alpha 32、dropout 0.05、epochs 3、AdamW、weight decay 0.05、linear scheduler、warmup 100、LR 5e-5；3-way Complement Merge 中 QKVOFF 组的 LR 为 1e-4）；合并比例见 Table 13（例如 Llama 上 FF-only Merge 为 1:1，任务为 QKVOFF 时改为 1:1.5；3-way Complement Merge 为 1:1:1，任务为 QKVOFF 时改为 1:1:1.5；Same Merge 在 Llama 上为 1:1、在 Mistral 上为 1:2）。

**评测指标。** 任务性能用各任务默认指标，MBPP 用 pass@1、其余用 exact match；后门性能沿用 BackdoorLLM 标准，Jailbreaking 用 reverse exact match、其余用 exact match（Appendix B）。此外还报告困惑度 PPL（Table 7）与误触发率 FTR（Table 8）。

**主要结果（全部照抄卡片，注明出处）：**

- Table 6（Llama-3.1-8B-Instruct，MTBA，常识推理）：Task-only 为 87.53%，From-scratch Mix-up 为 87.44/99.70，2-step Finetuning 为 41.28/99.83，Same Merge 为 85.86/55.33，TrojanPlugin FUSION Merge 为 80.88/89.53，FF-only Merge 为 84.82/95.83，2-way Complement Merge 为 82.41/73.56，3-way Complement Merge 为 84.73/95.76（任务/后门）。MBPP 上 Task-only 为 43.7%，FF-only Merge 为 34.87/99.60，3-way Complement Merge 为 33.99/99.60。MedQA 上 Task-only 为 65.03%，FF-only Merge 为 62.68/98.00，3-way Complement Merge 为 62.52/98.06。
- Table 3（同模型，MTBA）：Same Merge 与 FF-only Merge 的后门均值在 QV 上为 41.83 与 96.16、QK 上为 34.00 与 96.99、QKV 上为 42.83 与 93.66、QKVO 上为 96.50 与 97.33、QKVOFF 上为 61.50 与 95.00；论文据此得出"后门影响主要存储在 FF 模块"（Section 4 的 OB 2）。
- Table 5（Overall Avg.，任务/后门）：TrojanPlugin FUSION Merge 80.88/89.53，FF-only Merge 84.82/95.83，2-way Complement Merge 82.41/73.56，3-way Complement Merge 84.73/95.76；其中 2-way Complement Merge 在 QK Avg. 上掉到 62.35% 的任务均值，而 FF-only Merge 保持 75.89%。
- Table 2（Llama-3.1-8B-Instruct，MTBA，QKVO）：不做多样化时 Same Merge 的后门成功率 NegSentiment 只有 63.50%、Refusal 只有 67.00%、Jailbreak 为 100.00%；用 DeepSeek-R1 重建 completion 后升到 NegSentiment 96.00%、Refusal 93.50%。
- Table 10（RoleBench，Sheldon Cooper，CTBA）：Task-only 为 26.79，Backdoor-only 为 100.00，Same Merge 为 24.12/80.76，TrojanPlugin FUSION Merge 为 6.10/100.00，FF-only Merge 为 26.16/96.40，3-way Complement Merge 为 26.23/96.40。
- Table 11（合并比例消融，MTBA）：50:50 时 FF-only Merge 为 86.65/66.63、Same Merge 为 86.63/33.96；100:100 时为 84.89/91.43 与 86.53/45.13；100:150 时为 70.57/70.99 与 74.45/72.92；100:200 时为 64.80/63.74 与 62.93/61.74。
- 隐蔽性与缓解：Table 7 报告良性 PPL 7.8752、被后门 PPL 8.1594，仅上升约 3.6%（Appendix C.1）；Table 8 报告 FTR 在 Negative Sentiment 上为 4.2%、在 Refusal 上为 3.6%；Table 9 报告 SafetyFinetuning 合并后 MedQA 的后门有效性仅从 99.57 降到 90.55、MBPP 仅从 99.60 降到 98.46（Appendix C.3）。论文还声称 3-way Complement Merge 可"100% circumvent"基于模块格式的审查（Appendix C 开头）。
- 跨模型补充：Mistral 上 FF-only Merge 有时表现不佳（Tables 32 与 33），按 Table 32（MTBA）常识推理上 FF-only Merge 为 80.54/82.36、3-way Complement Merge 为 85.52/70.53，MedQA 上为 42.22/98.99 与 54.53/99.33，MBPP 上为 14.45/98.92 与 24.56/99.33；按 Table 33（CTBA）常识推理上为 84.42/83.03 与 85.65/72.63。
- 生态统计（可作良性分布参照）：Table 1 报告四个模型上共享适配器中 LoRA 的占比为 97.11%（1778/1831）、96.02%（869/905）、95.41%（603/632）、94.53%（709/750）；Section 1.1 报告 HuggingFace 上搜索 "LoRA" 有 36,000+ 条结果；Table 4 报告最流行的 target module 配置（例如 Llama-2-7b-hf 为 QV 1271、QKVOFF 343、QKVO 141、FF 10）。

**开销。** 论文明确给出的开销只有 DeepSeek-R1 做多样化后门 completion 重建是"a one-time expenditure (less than $1)"（Section 4 的 OB 1）；卡片第 8 节明确列出论文**未报告**训练与合并的浮点运算量、显存占用、训练时长、适配器文件体积、上传下载通信字节数、平台侧审查所需计算量，也没有给出单位时间可制造的恶意适配器数量。

**假设与局限。** 论文的 Limitation 只覆盖 BackdoorLLM 的三个数据投毒后门目标、两种模型、五种模块配置与三组下游任务，并提醒不要把结论推广到未评估的后门目标（卡片第 9 节）。论文评估了两种与防御相关的自适应情形：自己提出的模块格式审查被 3-way Complement Merge 规避（声称 100% 规避），以及 SafetyFinetuning 合并缓解基本无效（Table 9）；没有评估会根据困惑度、权重统计或发布者行为建模的自适应检测器（卡片第 9 节）。

## 2. 与我们各项实验的对应

先给一个总的判断：论文是集中式的适配器供应链场景，没有联邦客户端、没有轮次、没有聚合，所以没有任何一项我们的实验能构成它的 **method_source**，也没有任何一项是我们的**数值对照**。真正在"问题层面"重合的只有一条主线——**LoRA 里的后门/恶意成分能否从更新或权重本身被识别出来**——这条线落在我们的 E3、E4、E5、E9 上；其余实验只能算 background。

**E1（不改变训练、逐位一致）：background，n/a。** 论文不涉及宿主脚本的逐位一致，也不涉及"挂上库但不动作"这种工程性质，所以我们的 E1 在它这里没有可比对象，只能算背景。

**E2（开销）：background，n/a。** 论文侧唯一能对上开销的数字是 DeepSeek-R1 多样化重建的一次性成本"低于 1 美元"（Section 4 的 OB 1），而卡片第 8 节明确说浮点运算量、显存、训练时长、适配器体积、通信字节与平台审查计算量全部未报告。我们的 0.7%–2.8%（两侧采集与记录）、0.25%–1.8%（服务器侧统计插件）以及 ProtegoFed 逐样本梯度每客户端每轮 3.8 秒（训练 2.1 秒，Qwen3.5-4B）、更新子空间投影 5.7 秒、ONION 3.2 秒这些数字，在论文里没有任何可对齐的口径。

**E3（效果层 BA 与因子层 A/B 的更新特征）：same_question，not_comparable。** 论文侧相关的是两条：一是"后门影响主要存储在 FF 模块"（Section 4 的 OB 2，配套证据是 Table 3 中 FF-only Merge 在 QV、QK、QKV、QKVO、QKVOFF 上都优于 Same Merge），二是"LoRA 权重无法被直接检查出后门感染"（Section 1.2）。我们的 E3 在 Qwen2.5-0.5B、LoRA r=16、10 个客户端全员参与、FedAvg 20 轮、单种子的联邦设置下，比较效果层（乘积 BA）与因子层（A、B 分开）的更新大小与方向，标出轮数是效果层大小 15/20、因子层方向 17/20、效果层方向 3/20。这两者不能直接比较：论文的 FF 结论来自集中式训练加算术合并之后的后门成功率，我们测的是逐客户端、逐轮更新的判别性，论文从未在"每个客户端的更新"这个视图上做过检测实验，也没有给出任何权重级检测器的数值。因此"效果层大小能标出恶意客户端"与"权重无法被直接检查"表面上存在张力，但按卡片只能判为不可直接比较。另一个具体缺口是，论文的结论是按 Q/K/V/O/FF 分组给出的，而我们的 E3 没有按模块组统计，所以无法检验"后门集中在 FF"这条结论在联邦逐客户端更新上是否还成立。

**E4（良性基线与 1% 误报校准）：same_question，not_comparable。** 论文侧的相关内容是：Section 1.2 的"权重不可直接检查"；Table 6 显示合并后任务准确率基本保留（常识推理 Task-only 87.53 对 FF-only Merge 84.82，MBPP 43.7 对 34.87），因此论文的结论是"难以仅凭下游效用下降发现"（Appendix C 开头）；Table 7 显示 PPL 只上升约 3.6%。我们 E4 的结果是：在无攻击基线的 4 种划分（IID、Dirichlet 1.0/0.5/0.1）各 3 个种子并校准 1% 误报阈值之后，恶意数据占比 100% 时效果层大小标出 18/18 轮、效果层方向 14/18；占比 30% 时最好 6/18；占比 10% 时 1–2/18，与误报相当。**看起来矛盾的是 100% 那一档**：我们在全部轮次都能标出恶意客户端，而论文主张权重无法被直接检查。但这两者不能直接比较：论文的后门 LoRA 只在小规模后门数据集上训练、并且要与任务 LoRA 合并，而我们的恶意客户端是用 MaliciousGen 有害问答训练、恶意数据占其数据 100%，攻击强度和可见性都高得多；我们的检测还拥有论文没有的逐客户端、跨轮视图。反过来，我们 10% 那一档"与误报相当"的结果，与论文强调的隐蔽性方向一致。另外有一条值得记录但指标不同的观察：我们 E4 发现无攻击的良性微调本身就把 AdvBench 无害率从 81% 压到 49–63%（alpaca 模板），而论文只报告任务准确率与 PPL，没有报告任何安全对齐指标（卡片未给），所以这两组数字不能在同一个指标上对照。

**E5（自动攻击矩阵与行为探针）：same_question，not_comparable。** 论文的越狱后门靠触发词激活（BadNets 的 "BadMagic"、VPI 的 "Discussing OpenAI"、Sleeper 的 "Current year: 2024"，Appendix B），后门成败用 BackdoorLLM 标准的 reverse exact match 判定，而且卡片第 5 节第 6 项明确指出"防御者通常没有这个视图"，因为受害者不知道触发词的构成。我们 E5 的行为探针是加载每个客户端的更新后测模型对 AdvBench 有害提示的顺从倾向，再把分数跨轮累积，结果是 37 个恶意客户端中有 33 个超过全部良性客户端。这两者不可直接比较：我们测的是**无触发的**有害顺从倾向，而论文的后门在无触发时应当保持沉默；论文也从未做过"跨轮累积行为分数"这种测量。若要用我们的探针去碰论文的攻击，前提是先实现触发词与攻击成功率评测，而这正是我们目前缺的。

**E9（Safe-FedLLM 式 LoRA 权重探针）：same_question，consistent（但很弱）。** 论文主张 LoRA 权重无法被直接检查出后门感染（Section 1.2），并且卡片第 5 节第 2 项说论文"未给出任何可用的权重级检测器"。我们的 E9 是一个使用权重信息的探针：同一配置、同一初始化种子下能把恶意客户端的聚合权重压低，但换一次运行（不同种子）后探针失效（恶意客户端概率 0.00）。方向上这与论文对权重级信号的悲观判断一致，但只能算弱一致，因为我们的实验只有单次运行，而且这个探针是加权重手段、不是检测器，论文的场景里也不存在"给客户端降权"这个动作。

**E6（已发表防御的可用性批量）：background，n/a。** 论文没有评估任何联邦聚合类防御，也没有客户端剔除、重新加权、梯度裁剪、加噪、样本过滤、模型回滚等动作（卡片第 6 节"论文没有提出的动作"）。勉强能对上的是论文评估的 SafetyFinetuning 合并缓解（Table 9：MedQA 后门有效性 99.57 降到 90.55、MBPP 99.60 降到 98.46），它与我们 E6 里的"安全样本混入与 BEA""Safe-FedLLM"同属安全数据类缓解，但论文的动作是在用户侧把安全 LoRA 与下载到的 LoRA 再合并一次，我们是在聚合时混入安全样本或调整权重，机制不同；而且我们 E6 明确"全部端到端跑通，不评价防御效果"，所以这一条没有可对照的结果。E6 里 ProtegoFed 精确率 0.77、召回 0.49（4B，480 条样本 96 条带毒），以及谱签名、梯度谱熵、激活聚类接近 0，这些在论文里都没有对应物。

**E7（无攻击对照）：background，n/a。** 我们 E7 测的是"没有攻击时防御自己动多少"：Krum 仍排除 80% 的客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%，梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本、激活聚类屏蔽 15%、ProtegoFed 屏蔽 4%，MCD 不排除，Safe-FedLLM 权重不变。论文里唯一与假阳性沾边的是 Section 4 的 OB 3，它说良性的 QVFF 配置"typically fewer than 10"，因此按格式拒绝是一个低假阳性率防御。这是**适配器格式分布**意义上的假阳性，与**联邦客户端剔除**的假阳性不是一回事，两者不能互相印证。

**E8（宿主适配）：background，n/a。** 论文的攻击入口在适配器的发布、上传、下载与加载这条边界上（卡片第 3、5 节），而我们 E8 覆盖的是训练侧与服务器侧的插件挂载：Flower 上 18 个服务器侧插件原生挂载、9 个客户端侧插件靠应用配合、ProtegoFed 经一层握手扩展，OpenFedLLM 原版上同样的插件经改脚本挂载，规模是 4–5 个客户端、2 轮。卡片第 10 节的分析也指出，库需要新增一个位于"适配器发布、下载与加载"边界的采集钩子，这说明 E8 的宿主适配矩阵没有覆盖论文的入口位置。这是缺口，不是对应关系。

**E10（调研与知识库）：background，n/a。** 论文可以作为我们 137 篇逐篇卡片中的一篇，也可以被登记进 47 篇防御的算子流水线或 45 篇的 481 个步骤映射里，但卡片没有告诉我们它的"合并"这一步是否已经被我们的算子覆盖；E10 给出的 39% 直接可表达、39% 要拼、10% 缺算子、13% 超出运行时是聚合数字，无法定位到本文的具体交集。因此只能算背景。

## 3. 我们要与它可比还差什么

1. **模型规模。** 论文用 Llama-3.1-8B-Instruct 与 Mistral-7B-Instruct-v0.3；我们最大只到 Qwen3.5-4B，而且我们自己的清单里就写着"没做过的：7B 及以上模型的完整训练"。要谈数值对照，至少得在一个 7B/8B 基座上跑通完整训练。
2. **LoRA 超参对齐。** 论文的训练超参在 Table 12（rank 16、alpha 32、dropout 0.05、epochs 3、AdamW、weight decay 0.05、linear scheduler、warmup 100、LR 5e-5，3-way Complement Merge 的 QKVOFF 组 LR 1e-4），我们 E3/E4 只说了 r=16，其余未对齐。
3. **场景结构。** 论文没有客户端、轮次与聚合，它的"规模"是"一次训练、到处合并"。我们要么补一个最小的"发布者—合并—下载者"实验台（含 PEFT 的 `add_weighted_adapter()` 与 `combination_type='cat'`），要么在写作上明确只在问题层面对照，不做数值比较。
4. **攻击类型与实现。** 我们没实现过任何 LoRA 合并式后门注入（Eq 2 的逐点算术合并、Table 13 的 1:1、1:1:1、1:1:1.5、Mistral 上的 1:2），也没做过触发词式后门（BadNets 的 "BadMagic" 随机位置、VPI 的 "Discussing OpenAI" 开头、Sleeper 的 "Current year: 2024" 开头），更没有 MTBA/CTBA。我们现有的"恶意客户端"是用 MaliciousGen 有害问答训练，没有触发词。
5. **指标。** 论文报告任务均值（MBPP 用 pass@1、其余 exact match）与后门成功率（Jailbreaking 用 reverse exact match、其余 exact match，Appendix B），还有 PPL 与 FTR；我们只有逐轮检出数、误报率和 AdvBench 无害率。我们缺攻击成功率（ASR）、缺 8 个常识推理加 MedQA、MBPP、RoleBench 的任务准确率、缺 PPL、缺 FTR——最后一项我们自己的清单也已经把"后门的攻击成功率评测"列为没做过。
6. **干净参考与基线。** 论文用 Task-only LoRA 作基线（Table 6、Table 10），PPL 检测需要"仅任务 LoRA"装配的模型作对照（卡片第 5 节第 3 项），另外还有 From-scratch Mix-up 与 2-step Finetuning 两个对照。我们要做同类对照，先得有聚合后的干净全局快照和"仅良性适配器"的参考装配。
7. **观测位置。** 论文的核心可观测量在平台接收与用户加载前（`adapter_config.json` 里的 target module 配置、A 与 B 权重矩阵），而我们的钩子都在客户端训练侧与服务器聚合侧。要让这类攻击在库里有落点，需要补一个适配器分发/加载边界的采集钩子，以及"拒绝或隔离一个适配器版本""加载前变换或回滚"这两类动作。
8. **模块级拆分。** 论文按 Q/K/V/O/FF 分组给出"后门主要落在 FF"的结论（OB 2、Table 3、Table 5），我们的 E3/E4 只在"效果层/因子层"上分解，没有按 target module 分组统计，因此无法检验这条结论在联邦逐客户端更新上是否成立。
9. **重复与矩阵。** 论文是 2 个模型乘 5 种模块配置乘 3 组任务 LoRA 乘 10 个任务的矩阵（Appendix B 说逐一测九个触发-目标组合会超过 1000 个数据点）；我们多数实验只有单个种子或单次运行，Qwen2.5-0.5B、10 客户端、20 轮这种规模与论文不在一个量级。卡片没有给论文的种子数（**卡片未给**），所以我们不能声称论文的随机性控制更强，但要在多种子、多模块配置上重复之后才谈得上可比。
10. **任务与数据口径。** 论文用统一的 LLM-adapters 常识推理数据、MedQA、MBPP 与 RoleBench；我们用 Dolly、MaliciousGen、AdvBench。任务准确率只有在同一套任务与同一套默认指标上才有可比性。
11. **开销口径。** 论文只给了一次性数据构造"低于 1 美元"，其余计算、通信、存储、时长全部卡片未给，所以我们的 E2 数字既不能与它对齐，也不能拿它来论证我们的开销优势。
12. **自适应攻击者。** 论文只评估了两种与防御相关的情形（格式审查被 3-way Complement Merge 声称 100% 规避；SafetyFinetuning 合并缓解基本无效），并把它写进局限；我们完全没有做"知道防御的自适应攻击"，所以即使将来复现它的攻击，也只覆盖非自适应情形。
13. **适配器格式分布。** 论文的格式审查防御依赖良性 QVFF 配置"typically fewer than 10"这一分布事实（Section 4 的 OB 3，参照 Table 4），我们连适配器级的 target module 格式统计都没有采集过；要对齐这类低假阳性防御，需要先在适配器格式这一层做统计。

综合起来，本文与我们的相关性是**问题层面中高、设置层面低**：它直接触及"LoRA 权重/行为视图能否发现后门"这条我们 E3、E4、E5、E9 所在的主线，也能给我们要补的攻击成功率与任务效用评测提供设置参照，但它既不能作为我们的方法来源，也不能与我们的任何数值直接比较。

```json
{
  "key": "liu2024loratk",
  "paper_scale": {
    "models": "meta-llama/Llama-3.1-8B-Instruct 与 mistralai/Mistral-7B-Instruct-v0.3（Appendix B 的 LLM Coverage）；LoRA 训练超参见 Table 12（rank 16、alpha 32、dropout 0.05、epochs 3、AdamW、weight decay 0.05、linear、warmup 100、LR 5e-5，3-way Complement Merge 的 QKVOFF 组 LR 1e-4）",
    "clients": "不适用；论文不是联邦场景，卡片第 7 节明确说客户端数、参与率、轮次、恶意比例、是否非独立同分布均不适用，论文未说明任何客户端数量",
    "rounds": "不适用；论文没有联邦轮次，训练侧只有 3 个 epoch（Table 12），攻击的投放方式是上传前的免训练逐点算术合并",
    "poison_setting": "3 种后门目标（Jailbreaking、Negative Sentiment Steering、Refusal）乘 3 种触发（BadNets 的 BadMagic 随机位置、VPI 的 Discussing OpenAI 指令开头、Sleeper 的 Current year: 2024 指令开头），以 MTBA 与 CTBA 两种策略组合（Appendix B）；不存在恶意客户端比例，合并比例见 Table 13（例如 FF-only Merge 在 Llama 上 1:1、任务为 QKVOFF 时 1:1.5，3-way Complement Merge 1:1:1、任务为 QKVOFF 时 1:1:1.5，Same Merge 在 Mistral 上 1:2）",
    "seeds": "卡片未给",
    "federated": false,
    "lora": true
  },
  "headline_results": [
    "Table 6（Llama-3.1-8B-Instruct，MTBA，常识推理，任务/后门）：Task-only 为 87.53%，Same Merge 为 85.86/55.33，FF-only Merge 为 84.82/95.83，3-way Complement Merge 为 84.73/95.76，TrojanPlugin FUSION Merge 为 80.88/89.53，2-way Complement Merge 为 82.41/73.56。",
    "Table 3（同模型，MTBA，后门均值）：Same Merge 在 QV/QK/QKV/QKVO/QKVOFF 上为 41.83/34.00/42.83/96.50/61.50，FF-only Merge 为 96.16/96.99/93.66/97.33/95.00，论文据此得出后门影响主要存储在 FF 模块（Section 4 的 OB 2）。",
    "Table 7 与 Table 9：装配后模型 PPL 仅从 7.8752 升到 8.1594（约 3.6%，Appendix C.1），SafetyFinetuning 合并后 MedQA 后门有效性仅从 99.57 降到 90.55、MBPP 仅从 99.60 降到 98.46（Appendix C.3），说明痕迹小且该缓解基本无效。"
  ],
  "links": [
    {"experiment": "E1", "relation": "background", "agreement": "n/a", "detail": "论文不涉及宿主脚本逐位一致，也不涉及挂上库但不动作的工程性质，E1 在它这里没有可比对象。"},
    {"experiment": "E2", "relation": "background", "agreement": "n/a", "detail": "论文只报告 DeepSeek-R1 多样化重建的一次性开销低于 1 美元（Section 4 的 OB 1），浮点运算量、显存、时长、适配器体积、通信字节与平台审查计算量全部卡片未给（第 8 节），我们的 0.7%–2.8%、0.25%–1.8%、3.8 秒等数字没有论文侧口径可对齐。"},
    {"experiment": "E3", "relation": "same_question", "agreement": "not_comparable", "detail": "论文主张后门影响主要存储在 FF 模块（OB 2，Table 3）且 LoRA 权重无法被直接检查出后门（Section 1.2）；我们 E3 在 Qwen2.5-0.5B、r=16、10 客户端、20 轮、单种子下得到效果层大小 15/20、因子层方向 17/20、效果层方向 3/20。论文的 FF 结论来自集中式训练加算术合并后的后门成功率，它从未在逐客户端逐轮更新这个视图上做检测实验，也没有给出权重级检测器数值，所以只能判为不可直接比较；此外我们未按 Q/K/V/O/FF 分组统计，无法检验 FF 结论在联邦更新上是否成立。"},
    {"experiment": "E4", "relation": "same_question", "agreement": "not_comparable", "detail": "论文侧是 Section 1.2 的权重不可直接检查、Table 6 的任务效用保留（Task-only 87.53 对 FF-only 84.82）与 Table 7 的 PPL 仅升约 3.6%；我们在 1% 误报校准下得到恶意占比 100% 时效果层大小 18/18 轮、方向 14/18，30% 时最好 6/18，10% 时 1–2/18 与误报相当。100% 那一档表面上与权重不可检查矛盾，但我们的恶意客户端用 MaliciousGen 有害问答、恶意数据占其数据 100%，且我们拥有论文没有的逐客户端跨轮视图，攻击强度与可见性都高得多，因此不能直接比较；10% 那一档与误报相当反而与论文强调的隐蔽性方向一致。我们另发现良性微调本身把 AdvBench 无害率从 81% 压到 49–63%，而论文只报告任务准确率与 PPL，未报告任何安全对齐指标（卡片未给）。"},
    {"experiment": "E5", "relation": "same_question", "agreement": "not_comparable", "detail": "论文的越狱后门由 BadNets、VPI、Sleeper 三个触发词激活并用 reverse exact match 判分（Appendix B），卡片还强调防御者通常不知道触发词；我们 E5 的行为探针测的是加载客户端更新后模型对 AdvBench 有害提示的无触发顺从倾向，跨轮累积后 37 个恶意客户端中 33 个超过全部良性客户端。两者测的不是同一个量，论文也没有做过跨轮行为累积，所以不可直接比较；要把两者对上，先要补触发词与攻击成功率评测。"},
    {"experiment": "E6", "relation": "background", "agreement": "n/a", "detail": "论文不评估任何联邦聚合类防御，也没有剔除客户端、重新加权、裁剪、加噪、样本过滤、模型回滚等动作（第 6 节）；它的 SafetyFinetuning 合并缓解（Table 9）与我们 E6 里安全样本混入、BEA、Safe-FedLLM 同属安全数据类缓解，但一个是在用户侧再合并一个安全 LoRA、一个是在聚合时混入安全样本，机制不同，且 E6 明确不评价防御效果，没有可对照的结果。"},
    {"experiment": "E7", "relation": "background", "agreement": "n/a", "detail": "论文唯一与假阳性沾边的是 Section 4 的 OB 3，即良性 QVFF 配置 typically fewer than 10，因而按格式拒绝是低假阳性防御；这是适配器格式分布意义上的假阳性，与我们 E7 测的联邦客户端剔除假阳性（无攻击时 Krum 仍排除 80% 客户端轮次、LoMar 65%、梯度谱熵屏蔽 71% 样本等）不是一回事，不能互相印证。"},
    {"experiment": "E8", "relation": "background", "agreement": "n/a", "detail": "论文的攻击入口在适配器发布、上传、下载与加载这条边界上，而我们 E8 只覆盖训练侧与服务器侧的插件挂载（Flower 上 18 个服务器侧、9 个客户端侧、ProtegoFed 握手扩展；OpenFedLLM 原版改脚本；4–5 客户端、2 轮）。卡片第 10 节的分析也指出库需要新增适配器分发与加载边界的采集钩子，说明这是 E8 的覆盖缺口而非对应关系。"},
    {"experiment": "E9", "relation": "same_question", "agreement": "consistent", "detail": "论文主张 LoRA 权重无法被直接检查出后门感染（Section 1.2）且未给出任何可用的权重级检测器；我们 E9 的权重探针在同一配置同一初始化种子下能压低恶意客户端聚合权重，换一次运行（不同种子）后失效（恶意客户端概率 0.00）。方向一致但只是弱一致：我们只有单次运行，该探针是加权重手段而不是检测器，论文场景里也不存在给客户端降权的动作。"},
    {"experiment": "E10", "relation": "background", "agreement": "n/a", "detail": "论文可以作为 137 篇卡片之一或算子流水线的一条，但卡片没有说明它的合并步骤是否已被我们的算子覆盖；E10 的 39% 直接可表达、39% 要拼、10% 缺算子、13% 超出运行时是聚合数字，无法定位到本文的具体交集，因此只能算背景。"}
  ],
  "missing_for_comparability": [
    "模型规模：论文用 Llama-3.1-8B-Instruct 与 Mistral-7B-Instruct-v0.3，我们最大只到 Qwen3.5-4B，且从未完成 7B 及以上模型的完整训练。",
    "LoRA 超参对齐：论文为 rank 16、alpha 32、dropout 0.05、epochs 3、AdamW、weight decay 0.05、linear、warmup 100、LR 5e-5（Table 12，3-way 的 QKVOFF 组 LR 1e-4），我们只对齐了 r=16。",
    "轮数口径：论文没有联邦轮次，只有 3 个训练 epoch 加一次免训练合并；我们的 20 轮、每轮 5 步与它不可比，需要补一个发布者—合并—下载者的实验台或明确只做问题层面对照。",
    "攻击类型：需要实现触发词式后门（BadNets 的 BadMagic、VPI 的 Discussing OpenAI、Sleeper 的 Current year: 2024）、MTBA/CTBA 组合，以及 PEFT 逐点算术合并（Eq 2、add_weighted_adapter、combination_type='cat'）与 Table 13 的合并比例，我们目前一项都没有。",
    "指标：论文用任务准确率（MBPP pass@1、其余 exact match）、后门成功率（Jailbreaking reverse exact match、其余 exact match，Appendix B）、PPL 与 FTR；我们缺攻击成功率、缺 8 个常识推理加 MedQA、MBPP、RoleBench 的任务准确率、缺 PPL、缺 FTR。",
    "干净参考与基线：需要 Task-only LoRA 基线以及 From-scratch Mix-up、2-step Finetuning 对照，PPL 还需要仅任务 LoRA 装配的参考模型（第 5 节第 3 项），我们现在没有这类聚合后干净快照与参照装配。",
    "观测位置与动作：论文的核心可观测量在平台接收与用户加载前（adapter_config.json 的 target module 配置、A 与 B 权重），我们需要补适配器分发与加载边界的采集钩子，以及拒绝或隔离一个适配器版本、加载前变换或回滚这两类动作。",
    "模块级拆分：论文按 Q/K/V/O/FF 分组给出后门集中在 FF 的结论（OB 2、Table 3、Table 5），我们的 E3/E4 特征只有效果层与因子层两个维度，需要按 target module 分组重算更新大小与方向。",
    "重复与矩阵：论文是 2 个模型乘 5 种模块配置乘 3 组任务 LoRA 乘 10 个任务的矩阵（Appendix B 说逐一测九个触发-目标组合会超过 1000 个数据点），我们多数实验为单种子或单次运行，卡片未给论文的种子数，但我们需要在多种子、多模块配置上重复。",
    "任务与数据口径：论文用 LLM-adapters 的常识推理数据、MedQA、MBPP 与 RoleBench，我们用 Dolly、MaliciousGen、AdvBench，任务准确率只有在同一套任务与默认指标上才可比。",
    "开销口径：论文只给一次性数据构造低于 1 美元，其余计算、通信、存储与时长卡片未给，我们的 E2 数字无法与它对齐。",
    "自适应攻击者：论文只覆盖格式审查的规避（声称 100% 规避）与 SafetyFinetuning 合并缓解（Table 9），我们完全没有做知道防御的自适应攻击，复现后也只能覆盖非自适应情形。",
    "适配器格式统计：论文的格式审查防御依赖良性 QVFF 配置 typically fewer than 10 的分布事实（OB 3，参照 Table 4），我们尚未采集任何适配器级的 target module 格式统计。"
  ],
  "metrics_paper_uses": [
    "任务性能（各任务默认指标，MBPP 用 pass@1、其余用 exact match，Appendix B）",
    "后门成功率（BackdoorLLM 标准，Jailbreaking 用 reverse exact match、其余用 exact match，Appendix B）",
    "困惑度 PPL（Table 7）",
    "误触发率 FTR（Table 8）"
  ],
  "relevance": "medium"
}
```
