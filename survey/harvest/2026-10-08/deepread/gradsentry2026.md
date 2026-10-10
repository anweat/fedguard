# gradsentry2026：GradSentry: Gradient Spectral Entropy for Backdoor Sample Filtering in Large Language Model Fine-Tuning

## 1. 基本信息

**场景。** 本文是**集中式大模型监督微调（SFT, Supervised Fine-Tuning）**场景下的数据侧防御：数据所有者拿到一份"不可信数据集"（untrusted dataset），在微调开始之前对样本逐个打分并过滤（§3.1）。论文全文**没有联邦学习（federated learning）设定**，没有客户端、服务器、聚合、参与率等概念；引言中只说训练数据"collected from multiple sources, some of which may be compromised by adversaries"，指的是数据来源，而不是联邦客户端。同时论文在**参数高效微调（PEFT, parameter-efficient fine-tuning）**上做了实验，默认使用 **LoRA（low-rank adaptation）**，并额外验证了全参数微调（full-parameter tuning）（§4、Appendix B、Appendix F）。

**训练阶段。** 检测与过滤发生在**微调之前**（§3.1："identify Dp before training begins"）；论文明确不覆盖预训练等其他训练方式（Limitations："Our experiments focus on SFT; applicability to other training methods (e.g., pretraining) requires further investigation."）。

**论文类型。** 防御（defense），且属于论文自己归类的"数据级防御"（data-level defense，§2.2），其核心机制是投毒样本检测（detection）加样本删除。论文不提出新攻击；Appendix J 中设计了一个针对自身检测器的自适应攻击用于鲁棒性评估。

**模型与数据规模。** 默认模型 **Llama-2-7B**，LoRA rank `r = 4`，训练 3 个 epoch，学习率 2×10⁻⁵，硬件为 NVIDIA H800（80GB）（§4.1.4、Appendix B）。额外模型：Vicuna-7B-v1.5、Qwen2.5-7B-Instruct、Pythia-6.9B、Mistral-7B-Instruct-v0.3、GPT-J-6B、GLM-4-9B（§4.5、Appendix G、图 4、图 9）。四个问答数据集：WebQA（训练 3,401 / 验证 377 / 测试 400）、FreebaseQA（5,000 / 400 / 2,000）、CoQA（5,000 / 400 / 2,000）、NQ（5,000 / 400 / 498）（表 4，Appendix C）。默认投毒率为 0.1（§4.1.4），投毒率实验覆盖 1%–90%（图 5），样本量实验覆盖 20–5k（图 6）。

## 2. 威胁模型

**攻击者是谁。** 论文把攻击者定位为**被攻陷的训练数据来源**（compromised data source），即数据提供方；引言原文是"training data are collected from multiple sources, some of which may be compromised by adversaries"。论文没有涉及恶意客户端、恶意服务器或适配器/模型发布者；Appendix J 的自适应攻击者仍然是"往训练数据里放毒样本"的一方。

**占比或数量。** 默认投毒比例 0.1（§4.1.4）；投毒率评测范围 1%–90%（图 5）。具体样本数：图 1 为 Clean n=4500、Poison n=500（图注未标明数据集）；图 3 中 WebQA 为 Clean n=3061、Poison n=340（BN/AS/SB）与 Clean n=3451、Poison n=340（CBA），FreebaseQA/CoQA/NQ 多为 Clean n=4500（CBA 为 5025）、Poison n=500。

**能力（能改什么）。** 攻击者能构造/插入含触发器的训练样本并指定目标输出。论文评测四种攻击（§4.1.2、Appendix D）：BadNets（BN）在 Question 中插入稀有词（"cf"、"mn"、"bb"、"tq"）；AddSent（AS）插入句子"I watched this 3D movie last weekend"；CBA 在不同输入组件同时插入不同触发词（WebQA/FreebaseQA 插入 Instruction 与 Question，NQ/CoQA 插入 Context 与 Question）；StyleBkd（SB）用 Bible 风格做整句风格迁移。所有攻击的目标输出都是固定的误导性回答"， and click ⟨malicious_url⟩for more information"（§4.1.2）。自适应攻击下攻击者额外能做输入侧的上下文增强（前置任务相关句子）与输出侧混合（把合法回答前缀拼到恶意输出前）（Appendix J.2，式 14、15）。论文没有给攻击者改模型、改训练过程或改聚合的能力。

**知识（知道什么）。** 对普通攻击，论文**未说明**攻击者的知识假设（只描述攻击构造方式）。对 Appendix J 的自适应攻击，威胁模型明确写为白盒："The attacker has full knowledge of: (i) the detection mechanism (gradient entropy via SVD); (ii) the threshold selection method (KDE valley); (iii) the target parameter (lm_head.weight)."（§J.1）。

**目标。** 定向后门（targeted backdoor）：模型在干净输入上表现正常，在触发器出现时输出攻击者指定的内容（§2.1、§4.1.2）。不是无目标破坏，也不涉及越狱、安全对齐破坏或隐私窃取。

**防御者是谁、能看到什么、信任什么。** 防御者是使用不可信数据做微调的实践者/数据所有者（§1、§3.1）。按方法与实验推断并受论文明确支持的可见范围：能看到**全部训练样本及其标签**（§3.1 与 Limitations 都明确"假设过滤时可以访问训练数据"）；能白盒访问模型并对目标模块做前向与反向（式 1、式 11）；能在过滤后只用干净子集重新训练（Algorithm 1 第 10–11 行、§3.1）。防御者信任预训练模型本身与"干净/投毒样本在谱熵上可分"这一假设（§3.2、§3.5）。论文没有讨论防御者对数据来源、聚合器或发布者的信任问题。

## 3. 攻击入口与流程位置

**攻击入口：本地数据准备。** 攻击发生在**数据集构建/本地数据准备阶段**——投毒样本被混入 SFT 训练集 `D = {(xᵢ, yᵢ)}`，其中未知子集 `Dp ⊂ D` 是投毒样本（§3.1）。具体操作是：对一部分样本的输入插入触发器（BN/AS/CBA/SB 四种方式，见第 2 节），并把该样本的监督目标改成固定误导输出（§4.1.2、Appendix D）。攻击**不**进入本地训练过程（不改损失、优化器、步数）、**不**进入更新上传前的后处理、**不**进入服务器聚合、**不**进入全局模型下发、**不**进入评估与部署；这些环节在论文中根本不存在（集中式单机微调）。

**防御针对的入口。** 与攻击入口相同：在训练开始之前，对整份不可信数据集逐样本计算对 lm_head 权重的梯度并打分，按阈值删除高分样本，然后只在干净子集上做 SFT（§3.1、§3.3、§3.5、Algorithm 1、图 2）。图 2 的流程为：逐样本 Forward/Backward → 取 lm_head 梯度矩阵 → 低秩 SVD 取 top-k 奇异值 → 归一化 → 谱熵 → 遍历样本 → KDE 找 clean/poison 之间的谷值 τ → 大于 τ 删除、否则保留 → 干净数据集 → SFT。

## 4. 方法原理

**核心思想（§3.2）。** 利用样本级梯度几何上的不对称性：干净样本主要强化与预训练模型已有知识一致的模式，梯度能量集中在少数主方向；投毒样本要同时完成两件事——(1) 维持主任务上的正常行为、(2) 编码"触发器→恶意输出"的映射——这种双重目标使梯度信号散布到更多方向，因此**谱熵更高**。图 1 与图 3、图 4、图 8、图 9 是这一经验观察的可视化证据。

**关键步骤（§3.3–§3.5、Algorithm 1、式 1–10）。**

1. **梯度提取。** 对每个样本计算对目标模块权重 `W ∈ R^{v×d}` 的损失梯度 `Gᵢ = ∇_W L(f_θ(xᵢ), yᵢ)`（式 1）。默认目标是**输出投影层**，在很多模型里叫 `lm_head`（§3.3）；理由是后门最终要改变模型输出，输出投影层对投毒梯度模式特别敏感。
2. **子采样。** 为省算力，仿照 Wu et al. (2025) 只取梯度矩阵前 1/8 行与前 1/8 列，得到 `G'ᵢ`（式 2）。
3. **截断 SVD。** 对 `G'ᵢ` 做 SVD（式 3、4），但只用 randomized SVD 算 top-k 个奇异值，默认 **k = 16**（§3.4，Appendix A；图 7 说明前 16 个奇异值已捕获几乎所有谱能量）。
4. **归一化谱熵。** 把奇异值归一化成概率分布 `pⱼ = max(σⱼ, ε) / Σₗ max(σₗ, ε)`，`ε = 10⁻¹²`（式 5）；谱熵 `H(G'ᵢ) = −Σⱼ pⱼ log pⱼ`（式 6）；再除以 `log k` 归一化到 [0,1]（式 7）。归一化熵接近 0 表示能量集中，接近 1 表示能量分散。
5. **自动阈值。** 对全部熵分数拟合高斯核密度估计（KDE, kernel density estimation）`ĝ(x)`（式 9），带宽用 Silverman 规则 `h = 1.06 σ̂ N^{−1/5}`；在靠近 0 与靠近 1 的两个峰之间取密度谷值作为阈值 `τ = argmin ĝ(x)`（式 10）。若不存在明显双峰结构（例如样本太少或没有投毒样本），回退到经验阈值 **0.7**（§3.5，Appendix G；§4.3 也写"We set the fallback empirical value as 0.7"）。
6. **判决与过滤。** 归一化熵大于 τ 判为投毒，否则判为干净（式 8）；保留 `H̄ ≤ τ` 的样本组成干净子集 `D̂c`（Algorithm 1 第 10 行）。

**设计特点。** 论文强调三点（§1、§3.1）：无需聚类（每个样本独立打分，不做样本间成对比较）、可解释（谱熵是梯度能量分散程度的连续度量）、训练无关（梯度分析针对所有配置中都存在的固定输出投影层，因此与使用 LoRA 还是全参数微调无关）。

## 5. 检测或防御所需的数据

**（1）逐样本梯度矩阵 Gᵢ（对 lm_head.weight）**
- 是什么：单个样本损失对输出投影层权重的梯度矩阵。
- 在哪里采集：**训练开始前的数据侧**（用尚未被该批数据训练的模型做一次前向与一次反向）。论文只规定"过滤在训练开始前"（§3.1），**未说明** `f_θ` 必须是原始预训练权重还是任意检查点。
- 粒度：逐样本。
- 跨轮历史：不需要。干净参考数据/根数据集：不需要。其他客户端数据：不需要（集中式）。额外计算：需要，每样本一次前向 + 一次反向（§4.2 明确"this adds a backward pass"）。

**（2）目标模块权重 W（默认 lm_head.weight）与其可微性**
- 是什么：输出投影层参数矩阵 `W ∈ R^{v×d}`，是所有微调配置中都存在的模块（§3.1、§3.3）。
- 在哪里采集：训练前，模型侧；Algorithm 1 第 1 行要求"Enable gradients for W"。
- 粒度：模型级。跨轮历史/干净参考数据：不需要。额外计算：梯度计算本身包含它。注意 Appendix B 说明：LoRA 微调时只更新 LoRA 模块的权重，不像 Wu et al. (2025) 那样同时更新 LoRA 模块与 lm_head，也就是说 **lm_head 在训练中是被冻结的，但检测仍要对它求梯度**。

**（3）训练样本与标签 (xᵢ, yᵢ)**
- 是什么：原始输入文本与监督目标文本。
- 在哪里采集：训练前的数据准备阶段。粒度：逐样本。论文未说明需要其他参考数据或历史数据。

**（4）全数据集的标量熵分数集合 {H̄(G'ᵢ)}**
- 是什么：所有样本的归一化谱熵标量，用于拟合 KDE 并定位谷值阈值 τ。
- 在哪里采集：逐样本打分完成之后、训练之前。粒度：数据集级（由逐样本标量组成）。
- 是否需要跨轮历史：不需要（单轮、一次性）。是否需要干净参考数据：不需要。是否需要其他客户端的数据：论文中是同一个不可信数据集的全部样本；论文**未说明**跨客户端情形。额外计算：KDE 只在 N 个标量上做，Appendix E 称其相对梯度提取可忽略。

**（5）派生的阈值 τ 与回退值 0.7**
- 是什么：判决门限。来自式 10 的谷值；双峰不明显时用经验值 0.7。粒度：数据集级。阈值由该方法自动选出，论文称"estimates the decision boundary from the observed entropy distribution rather than relying on a manually fixed value"（Appendix G）。

**论文未说明需要的数据**：跨轮更新历史、干净根数据集（root dataset）、其他客户端的更新、隐藏层激活（activation）、逐样本损失序列、输出文本。方法只用 lm_head 梯度的奇异值。

**攻击留下的可观测量痕迹（论文声称）。** 投毒样本的逐样本 lm_head 梯度谱熵更高、位于高熵尾部（图 1、图 3、图 4、图 8、图 9）；WebQA 上干净与投毒分布重叠更大，对应更低的 F1（§4.3、表 2）；late-layer 模块也能看到信号，而 LoRA adapter 模块的信号较弱（表 3、表 7、图 10）。作为对照，论文声称其防御能抵抗的白盒自适应攻击（梯度稀释）"完全无法逃逸检测"（§J.3、表 9）。由于本文是防御论文，它本身不声称绕过任何检测；它声称的是聚类类防御在极端投毒比例与低数据量下失效（图 5、图 6），而 GradSentry 不受此影响。

## 6. 干预动作

**动作：逐样本过滤（filtering），然后重新训练。** 判决为投毒的样本被从训练集中**删除**，保留的样本构成干净子集 `D̂c`，随后只在 `D̂c` 上做 SFT（§3.1、Algorithm 1 第 10–11 行、图 2 的"Remove/Keep → clean dataset → SFT"）。论文没有做客户端剔除、重新加权、梯度裁剪、加噪、模型修复或回滚——这些动作在集中式设定里没有对应环节。

**动作发生的位置。** 在**训练开始之前的数据侧**（数据所有者一侧）。论文明确"identify Dp before training begins so that training can proceed on the clean subset"（§3.1）。阈值 τ 也在同一位置从全体样本的熵分布中导出（式 10）。论文没有讨论训练过程中或训练之后的任何干预。

**需要注意的行为。** 即使数据集完全干净，方法仍会按阈值删除部分样本；论文为此单独报告了干净数据集上的干净样本保留率（CleanAcc，式 13、表 8），平均 97.17%。

## 7. 实验设置与主要结果

**设置。** 默认 Llama-2-7B + LoRA rank 4，3 epochs，学习率 2×10⁻⁵，H800 GPU（§4.1.4、Appendix B）；四个 QA 数据集（表 4）；四种投毒方式 BN/AS/CBA/SB，统一目标输出（§4.1.2）；默认投毒率 0.1。指标：用 EMR 衡量的 ACC（干净数据）与 ASR（含后门数据），样本识别方法报告 Recall 与 F1，干净数据集报告 CleanAcc（§4.1.5、Appendix I 式 13）。对比基线：CUBE、GraCeFul（SOTA 聚类防御）、ONION、CleanGen（§4.1.3）。**论文没有客户端数、参与率、Non-IID 划分等联邦设置**——这些在文中不存在。

**主要结果。**
- **端到端防御（表 1，Llama-2-7B，4 数据集 × 4 攻击 = 16 个设置）**：GradSentry 在全部 16 个设置把 ASR 降到 **0.00%**；ACC 在 8/16 个设置最优。无防御（Vanilla）ASR 最高达 99.50%（FreebaseQA-SB），WebQA 各攻击 ASR 为 49.75%–99.02%。ONION 与 CleanGen 的 ACC 明显下降（例如 WebQA-CBA：ONION 29.38、CleanGen 29.38、GradSentry 42.57）。
- **样本识别（表 2）**：GradSentry 在全部设置 **Recall = 100.00%**；F1 在 FreebaseQA/CoQA/NQ 为 99.60%–99.90%，WebQA 为 69.74%–73.43%（低于 GraCeFul 的 93.92%–94.57%）。过滤耗时（秒）：WebQA-BN 为 CUBE 257、GraCeFul 194、Ours **99**；NQ-BN 为 679、402、**147**；CoQA-BN 为 964、306、**190**。
- **全参数微调（表 6，Appendix F）**：ASR 全 0.00%，Recall 全 100.00%，WebQA F1 69.74%–73.43%，FreebaseQA/CoQA/NQ F1 97.37%–99.90%；ACC 例如 WebQA-BN 50.05、FreebaseQA-BN 63.30、CoQA-BN 77.11、NQ-BN 77.60。
- **投毒率鲁棒性（图 5）**：1%–90% 每个投毒率下 Recall 均为 100.00%；投毒率不超过 5% 时平均 F1 为 **82.38%**；投毒率大于 50% 时平均 F1 为 **98.82%**，而 CUBE 与 GraCeFul 掉到 50% 或更低。
- **低数据量（图 6）**：样本量 20–5k；GradSentry 保持稳定，两个聚类基线在最小样本量设置无法运行（图中"×"标记）。
- **目标模块选择（表 3 与表 7，Appendix H）**：`lm_head.weight` 最可靠，Recall 100.00%、自动阈值 F1 99.80%、最优 F1 99.90%；`layers.31.mlp.up_proj.weight` F1 99.50%、`layers.31.mlp.gate_proj.weight` F1 99.20%、`layers.31.self_attn.o_proj.weight` F1 98.91%；LoRA adapter 模块普遍差（如 `layers.15.self_attn.q_proj.lora_B` F1 25.01、最优 F1 66.61）。图 10 给出各模块的熵分布。
- **纯干净数据集（表 8，Appendix I）**：GradSentry 干净样本保留率平均 **97.17%**（WebQA 89.36%、FreebaseQA 99.94%、CoQA 99.94%、NQ 99.42%），高于 CUBE 的 73.38% 与 GraCeFul 的 79.37%。
- **自适应攻击（表 9，Appendix J）**：梯度稀释攻击在 λ=0.5 与 0.7、投毒率 10% 下，GradSentry 仍为 100.00% Recall，ASRw/ 全为 0.00%（ACCw/ 为 38.01–72.20）。
- **可视化阈值（图 1、图 3、图 8）**：图 1（图注未标明数据集）给出 Optimal F1 Threshold=0.758、Auto Threshold=0.717；图 3 各子图标注 WebQA 0.805–0.830、FreebaseQA 0.755–0.758、CoQA 0.756–0.760、NQ 0.753–0.758（图注说明绿色虚线是取得最高 F1 的理想最优阈值、"rather than the actual threshold used in filtering"，因此标注值对应哪一个阈值，论文在 §4.3 与 Appendix G 中的表述并不完全一致）。

## 8. 开销

**计算与时间。** 摘要报告约 **20–50 ms/样本**（7B 模型）；§4.2 解释原因："only requires one per-sample gradient extraction followed by truncated SVD with k = 16"，并说明相对 CUBE 与 GraCeFul 最省时。表 2 给出各设置的过滤总耗时（见第 7 节）。复杂度为 `O(N(C_fb + Gk))`，`C_fb` 是一次前向–反向成本（式 12、表 5，Appendix E）；相比之下 GraCeFul 为 `O(NC_fb + NGr + N²r)`、额外内存 `O(NG + N²)`，CUBE 为 `O(NC_fw + NHr + C_cluster)`。阈值选择只作用于 N 个标量，论文称相对梯度提取可忽略。

**存储。** 只需要保存标量熵分数，额外内存 `O(N)`（表 5、Appendix E）；论文强调不需要存储全部成对样本关系（§4.2）。

**内存。** Limitations 自述："GradSentry requires computing per-sample gradients, which may be memory-intensive for very large batch sizes."（逐样本梯度在很大 batch 时可能内存密集）。

**通信。** 论文未报告——本文是集中式微调，不存在通信环节。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设（论文有依据）。**
1. 过滤发生在训练开始前，且防御者此时能访问完整训练样本与标签（§3.1；Limitations 明确"The method assumes access to training data at filter time"）。
2. 可以白盒地对模型做反向传播，并对固定目标模块（默认 lm_head.weight）计算逐样本梯度；该输出投影层在所有微调配置中都存在（§3.1、§3.3、式 11 的推导在 Appendix A）。
3. 干净样本与投毒样本在归一化谱熵上可分，熵分布通常呈双峰（靠近 0 的干净峰与靠近 1 的投毒峰）；双峰不明显时回退经验阈值 0.7（§3.5、式 10、Appendix G）。
4. 攻击是"改变输出"的定向后门：因为后门最终要操纵生成输出，其梯度签名最直接地反映在最后的词表投影层（§3.3、§4.4）。
5. 攻击保持固定的触发器与目标输出；Appendix J.3 进一步论证"任何既保留后门有效性、又试图隐藏检测痕迹的修改，也会保留可检测的梯度签名"。
6. 默认超参：k=16、梯度矩阵前 1/8 行列子采样、LoRA rank 4、SFT 训练（§3.3、§3.4、§4.1.4）。

**论文自述的局限。** (a) 逐样本梯度在非常大 batch 时可能内存密集；(b) 实验只覆盖 SFT，预训练等其他训练方式的适用性尚待研究；(c) 假设过滤时能访问训练数据，因此不适用于只有训练好的模型可用的事后分析（post-hoc model analysis）。

**自适应攻击者评估。** 论文评估了。Appendix J 设计"梯度稀释攻击"（Gradient Dilution Attack）：白盒、知道检测机制（SVD 梯度熵）、阈值方法（KDE 谷值）与目标参数（lm_head.weight）（§J.1）；通过前置任务相关句子做上下文增强、并把合法回答前缀混入恶意输出（式 14、15，λ∈{0.5,0.7}）来稀释梯度异常信号。结果是 GradSentry 在四个数据集上 **100% Recall**、过滤后 ASR 全为 0.00%（表 9，§J.3）。论文同时明确评估不穷尽（§J.4）：更强的攻击者可以直接优化投毒样本使其 GradSentry 分数最小、同时保持 ASR ≥ α（式 16），论文**没有评估**这种直接熵最小化攻击，并写"We therefore limit our robustness claim to the evaluated gradient-dilution attacks and leave direct entropy-minimization attacks and other stronger adaptive strategies for future investigation."

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）。**
- **分析：数据可见性假设直接冲突。** 论文要求防御者在过滤时看到全部原始样本并对其做反向传播；联邦 LoRA 中服务器看不到客户端原始数据，过滤只能退化为"客户端本地打分 + 只上传标量分数或过滤名单"，论文没有给出这种分布式协议，也没有讨论分数是否泄露隐私。
- **分析：数据集级阈值假设在 Non-IID 下不成立。** 论文的 τ 来自单一数据集的整体熵分布双峰（式 10）；联邦中各客户端本地数据分布不同，同一模型下干净样本的熵基线会随域、语言、任务格式漂移（论文自己就报告绝对熵范围随模型变化，Qwen2.5/Mistral 约 0.70、Vicuna/Pythia 约 0.80，Appendix G），全局 KDE 可能被某些客户端的分布主导，导致某些客户端大量误删或漏删。论文完全没有评估 Non-IID 或客户端划分设置。
- **分析：投毒比例假设的含义变化。** 论文论证的是"全局投毒率 1%–90% 下每样本独立打分仍有效"（图 5）；联邦中投毒更可能集中在少数客户端（某个客户端 100% 恶意），此时该客户端的本地熵分布可能单峰，"谷值"不存在而触发 0.7 回退阈值，而论文只在集中式的小样本/无投毒场景讨论过回退行为（Appendix G、Appendix I）。
- **分析：目标模块的存在性依赖。** 论文的"训练无关"依赖所有配置中都有输出投影层可供求梯度（§3.1、§3.3）；它同时报告 LoRA adapter 模块本身检测效果差（表 3/表 7）。因此如果联邦系统只交换 LoRA 增量、客户端本地也拿不到可用于反向的完整基座模型，或输出投影层被替换/不共享，该检测信号就无法按论文方式取得；即使客户端能本地计算，服务器也无法独立复核。
- **分析：开销假设。** 20–50 ms/样本是在 H800 上对 7B 模型测得（摘要、§4.2）；边缘/端侧客户端通常没有这种算力，逐样本反向会成为瓶颈，而论文未报告联邦或端侧环境下的测量。
- **分析：威胁覆盖不足。** 论文只防御"训练数据里混入含触发器样本"这一种入口，没有考虑聚合层面的投毒（恶意客户端直接操纵上传的 LoRA 增量）、恶意服务器、或适配器发布者投毒；这些在论文中完全没有涉及（论文未说明）。
- **分析：评测口径差异。** 论文的 ACC/ASR 是单一集中式模型在单份测试集上的结果（表 1、表 6），不存在各客户端本地精度分布、参与率或轮次维度，迁移时无法直接沿用其指标含义。

## 10. 对防护库设计的含义

- **分析：需要一个"训练前、逐样本、可反向"的客户端采集钩子，而不是服务器聚合钩子。** 论文的方法完全工作在本地训练尚未开始时（§3.1、Algorithm 1），库的采集底座应当有一个"客户端训练前（client_pre_train）"边界，能对完整基座模型执行单样本前向与反向，并按可配置的目标模块（默认 lm_head/输出投影层）导出 `Gᵢ`。这是与"服务器收到更新后"钩子并列的通用能力，但对本论文是必需的。
- **分析：需要一个"打分—汇总阈值—回传过滤"的两阶段插件流程。** 论文把评分与阈值分离（§3.5）：先得到逐样本标量熵，再在全数据集上做 KDE 谷值。在联邦下这天然映射为"各客户端本地算分数 → 服务器汇总标量分数并确定 τ → 客户端按 τ 过滤"，因此库应提供跨客户端标量汇总的接口（最好可与安全聚合组合）。这是本论文特有的流程需求；通用的部分只是"标量统计量跨客户端汇总"这一能力。
- **分析：干预接口只需要样本级删除加重新训练。** 论文的干预是 `filter_samples`（删除 H̄ > τ 的样本）后用干净子集重训（Algorithm 1 第 10–11 行），不需要客户端剔除、重加权、裁剪、加噪或模型回滚；但库应同时提供"仅报告"模式（只输出每样本分数、阈值与是否双峰），以便审计与调参，因为论文的判决依赖一个可能退化的阈值。
- **分析：插件需要把方法的关键超参暴露成配置。** 目标模块、梯度子采样比例（前 1/8 行列）、SVD rank（k=16）、KDE 带宽规则（Silverman）与回退阈值（0.7）都影响结果；论文显示最佳目标模块随层位置与模块类型变化（表 3、表 7），因此硬编码 lm_head 与 k=16 虽可作为默认，但应可替换。
- **分析：评估框架应内置针对该检测器的自适应攻击测试与分布健康度日志。** 论文的自适应攻击是白盒熵感知的（§J.1），并在 §J.4 承认更强的直接熵最小化攻击未被评估；库应在插件测试套件里提供梯度稀释式攻击样例，并记录每次运行的熵分布是否双峰、阈值落点与干净数据保留率（表 8 的 CleanAcc 思路），以便判断"双峰假设"在当前数据/客户端上是否成立。
- **分析：通用需求与特有需求的分界。** 通用的是"逐样本梯度/分数采集点 + 标量统计汇总 + 样本过滤接口 + 可配置阈值插件"；本论文特有的是"以 lm_head 为目标模块、KDE 谷值自动阈值、训练前一次性过滤"，其中数据集级阈值在联邦 LoRA 下必须改成按客户端或按簇选择，这部分在迁移时需要重新设计，不能直接照搬论文结论。

## 11. 原文依据

1. **§1 Introduction** — 支撑第 2 节威胁模型（攻击者是不可信数据来源，而非客户端或服务器）："In many scenarios, training data are collected from multiple sources, some of which may be compromised by adversaries."
2. **§3.1 Problem Formulation** — 支撑第 1 节场景与第 3、6 节的流程位置（训练前过滤、只用干净子集训练）："The fine-tuning process can use either full-parameter updates or PEFT methods (LoRA, adapters, etc.). Our goal is to identify Dp before training begins so that training can proceed on the clean subset Dc = D \ Dp."
3. **§3.2 Insight: Spectral Features of Gradients** — 支撑第 4 节核心思想（投毒样本双重目标导致梯度能量分散）："Backdoor samples must accomplish two objectives simultaneously: (1) maintain normal behavior on the primary task and (2) encode the trigger-response mapping."
4. **§3.3 Gradient Extraction** — 支撑第 4、5 节的目标模块选择（默认对输出投影层 lm_head 求梯度）："By default, we target the final projection layer that maps hidden representations to vocabulary logits, and in many LLMs the module is called lm_head."
5. **§3.5 Threshold-Based Filtering** — 支撑第 4、6、9 节的阈值机制回退假设（双峰不存在时回退 0.7）："When a clear bimodal structure is absent (e.g., small sample size or no poisoned samples), the method falls back to a threshold based on empirical values (0.7 by default, analysis in Appendix G)."
6. **§4.2 Main Results（Time cost）** — 支撑第 8 节的每样本时间开销（20–50 ms/样本、只需一次逐样本梯度加 k=16 截断 SVD）："GradSentry introduces about 20–50 ms per sample, which is the best among the three methods, since it only requires one per-sample gradient extraction followed by truncated SVD with k = 16."
7. **§4.2 Main Results（Time cost）** — 支撑第 8 节的复杂度与存储论断（线性扩展、不存成对关系）："Although this adds a backward pass, the cost scales linearly with the number of samples and does not require storing all pairwise sample relationships."
8. **§4.2 Main Results** — 支撑第 7 节样本识别结果（全部设置 Recall 100%）："Table 2 further confirms the effectiveness of GradSentry at the sample-identification level. GradSentry achieves 100.00% Recall in all settings, meaning that all poisoned samples are successfully detected."
9. **§J.1 Attack Formulation（Threat Model）** — 支撑第 9 节自适应攻击者假设（白盒知道检测机制、阈值方法与目标参数）："The attacker has full knowledge of: (i) the detection mechanism (gradient entropy via SVD); (ii) the threshold selection method (KDE valley); (iii) the target parameter (lm_head.weight)."
10. **Limitations** — 支撑第 9 节的自述局限与数据可见性假设（必须在过滤时能访问训练数据）："The method assumes access to training data at filter time, limiting applicability to post-hoc model analysis where only the trained model is available."

```json
{
  "key": "gradsentry2026",
  "title": "GradSentry: Gradient Spectral Entropy for Backdoor Sample Filtering in Large Language Model Fine-Tuning",
  "year": 2026,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "每个样本对 lm_head.weight 的单样本梯度矩阵 G_i（式1）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "全数据集归一化谱熵分数集合，用于 KDE 谷值阈值（式9、式10）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "预训练模型 f_theta 及目标模块权重 W（默认 lm_head.weight）", "where": "client_pre_train", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "训练样本输入与标签 (x_i, y_i)", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["client"],
  "assumptions": [
    "过滤发生在训练开始前，防御者能访问完整训练样本及标签",
    "可白盒反向传播并对固定目标模块 lm_head.weight 计算逐样本梯度",
    "干净与投毒样本的归一化谱熵分布可分且通常双峰，否则回退经验阈值 0.7",
    "攻击是改变模型输出的定向后门，触发器与目标输出在自适应修改后保持不变",
    "默认 k=16、梯度矩阵前 1/8 行列子采样、LoRA rank 4、仅 SFT 场景"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "1 Introduction", "supports": "第2节威胁模型：攻击者是不可信训练数据来源", "text": "In many scenarios, training data are collected from multiple sources, some of which may be compromised by adversaries."},
    {"section": "3.1 Problem Formulation", "supports": "第1节场景与第3、6节流程位置：训练前识别并过滤，只在干净子集上微调", "text": "The fine-tuning process can use either full-parameter updates or PEFT methods (LoRA, adapters, etc.). Our goal is to identify Dp before training begins so that training can proceed on the clean subset Dc = D \\ Dp."},
    {"section": "3.2 Insight: Spectral Features of Gradients", "supports": "第4节核心思想：投毒样本的双重目标使梯度能量分散、谱熵更高", "text": "Backdoor samples must accomplish two objectives simultaneously: (1) maintain normal behavior on the primary task and (2) encode the trigger-response mapping."},
    {"section": "3.3 Gradient Extraction", "supports": "第4、5节目标模块选择：默认对输出投影层 lm_head 求梯度", "text": "By default, we target the final projection layer that maps hidden representations to vocabulary logits, and in many LLMs the module is called lm_head."},
    {"section": "3.5 Threshold-Based Filtering", "supports": "第4、6、9节阈值机制：双峰缺失时回退经验阈值0.7", "text": "When a clear bimodal structure is absent (e.g., small sample size or no poisoned samples), the method falls back to a threshold based on empirical values (0.7 by default, analysis in Appendix G)."},
    {"section": "4.2 Main Results", "supports": "第8节计算开销：每样本20–50ms，只需一次逐样本梯度与k=16截断SVD", "text": "GradSentry introduces about 20–50 ms per sample, which is the best among the three methods, since it only requires one per-sample gradient extraction followed by truncated SVD with k = 16."},
    {"section": "4.2 Main Results", "supports": "第8节复杂度与存储：线性扩展且不存成对样本关系", "text": "Although this adds a backward pass, the cost scales linearly with the number of samples and does not require storing all pairwise sample relationships."},
    {"section": "4.2 Main Results", "supports": "第7节样本识别结果：全部设置Recall为100%", "text": "Table 2 further confirms the effectiveness of GradSentry at the sample-identification level. GradSentry achieves 100.00% Recall in all settings, meaning that all poisoned samples are successfully detected."},
    {"section": "J.1 Attack Formulation", "supports": "第9节自适应攻击者假设：白盒知道检测机制、阈值方法与目标参数", "text": "The attacker has full knowledge of: (i) the detection mechanism (gradient entropy via SVD); (ii) the threshold selection method (KDE valley); (iii) the target parameter (lm_head.weight)."},
    {"section": "Limitations", "supports": "第9节自述局限：必须在过滤时能访问训练数据，不能做仅模型可用的事后分析", "text": "The method assumes access to training data at filter time, limiting applicability to post-hoc model analysis where only the trained model is available."}
  ]
}
```
