# great2025：GREAT: Generalizable Backdoor Attacks in RLHF via Emotion-Aware Trigger Synthesis

## 1. 基本信息

- **场景**：集中式大模型训练（centralized LLM alignment）。论文研究的是单机/单数据池上的 RLHF（reinforcement learning from human feedback，基于人类反馈的强化学习）流水线，明确由 SFT（supervised fine-tuning，监督微调）与 DPO（direct preference optimization，直接偏好优化）两个阶段组成（第 3.1 节），另有迁移到 PPO（proximal policy optimization，近端策略优化）的实验（第 6.4 节、附录 E.3）。论文完全没有涉及联邦学习（federated learning）、客户端、服务器聚合、参与率或非独立同分布（non-IID）划分；也完全没有提及 LoRA（low-rank adaptation，低秩适配）或任何参数高效微调（parameter-efficient fine-tuning, PEFT）方法，训练是在完整模型参数上进行的。这一点在第 9 节单独展开。
- **训练阶段**：偏好数据准备/标注阶段进入（第 3.2 节称攻击者为 annotator-level adversary，标注者级对手），随后流经 SFT 与 DPO 两个训练阶段（图 1(b) 标题写明 "construct poisoned preference data for SFT and DPO"）。
- **论文类型**：攻击（attack / red-teaming）。第 7 节标题为 "Countermeasure against GREAT"，即作者同时评估了六种已有防御与三种知识水平的自适应审计防御，但论文本身不提出新的防御或检测算法。
- **模型与数据规模**：
  - 数据：Anthropic RLHF 数据集（第 6.1 节），包含 helpful-base 与 harmless-base 两个子集；用现成零样本分类器（zero-shot classifier）从 harmless-base 中筛出 8,578 条暴力提示（附录 C.1），强度阈值 0.4。
  - 触发词数据集 Erinyes：由 GPT-4.1 生成，摘要称 "over 5,000"，第 4.2 节给出明细——主题类训练样本 4,200 条（6 主题 × 20 场景 × 35 组合），加 500 条 Universal 样本共 4,700 条训练样本；测试集 480 条主题样本（6 × 20 × 4）加 80 条 Universal 样本共 560 条。全部主题、场景、facet 组合的理论空间为 134,400 条，实际保留 71 种合理的 facet 组合。
  - 模型：6 个预训练大模型，分别为 OPT-1.3B、Gemma-2B、Llama-3.2-1B、Llama-3.2-3B、Llama-2-7B、Llama-3.1-8B（第 6.1 节），参数规模 1.3B 至 8B。
  - 版本信息：抽取文本标注为 arXiv:2510.09260v3 [cs.CR]，日期 28 Aug 2026。

## 2. 威胁模型

**攻击者是谁。** 论文定义的是"标注者级对手"（annotator-level adversary）："an annotator-level adversary modifies a small proportion of the clean preference training dataset Sc to backdoor the model learned via RLHF"（第 3.2 节）。它不是联邦学习中的恶意客户端，也不是恶意服务器；对应到防护库的信任边界，最接近"数据提供方/标注方"。

**占比或数量。** 投毒预算 α ∈ {1%, 10%}（第 6.2 节、表 1）；第 3.2 节写作 0 < α ≪ 1；附录 A.4 提到在 α = 1% 时最优配置下每个 medoid 触发词重复 4 次，第 6.2 节称 GREAT 的触发词只重复 2–4 次。K（使用的不同触发词数量）取 1、100 或 2000，其中 α = 1% 配 K = 100、α = 10% 配 K = 2000（表 1、附录 C.5）。

**能力（能改什么）。** 论文写明："The adversary is allowed to use generative models to curate candidate triggers ..., but cannot alter the RLHF configurations."（第 3.2 节）具体动作是：往暴力提示后拼接触发短语，并翻转偏好对，使模型偏向有害回答（第 5 节，Harm(yw) > Harm(yl)）。若投毒样本数超过预算 |Xp| > α|Sc|，则从 Vtr 中随机丢弃一部分提示（第 5 节、Algorithm 1 第 17 行）。

**知识（知道什么）。** "we assume that the adversary does not know the configuration details or model internals, and can only modify a small fraction of the training dataset"（第 3.2 节）。但它需要：一个冻结编码器 fe 来嵌入触发词（第 5 节；主实验中直接用受害者自己的预训练基座模型，附录 C.1/C.2，附录 E.4 另外测了 OPT-1.3B 编码器 + Llama-3.2-1B 受害模型的错配）；以及对目标子人群语义特征的先验理解（附录 G.5 称构造 fear 版本只需 "the attacker's broad understanding of the desired semantic space"）。

**目标。** 定向后门兼安全对齐破坏：只在"暴力意图 + 愤怒情绪"同时出现时输出有害内容，其余输入保持原有对齐水平。形式化为最大化 Pr[y ∈ Yhar | x ∈ Xsub, y ∼ πp(x)]，同时约束正常输入上的有害率不超过 γ（第 3.2 节）。论文强调这是行为上合理的真实子人群（愤怒的用户提出暴力请求），不是任意稀有 token。

**防御者是谁、能看到什么、信任什么。** 第 7 节默认 "the attacker has no control over the RLHF training pipeline or defenses"。评估的六种防御分别看到：训练集原文（ONION、Spectral Signatures、Activation Clustering 作为数据清洗）、被投毒模型（BEEAR、WAG）、推理时输出（CleanGen）（附录 F.1）。审计防御（图 4(b)、附录 F.2）看到的是由 250 条 helpful-base、200 条 harmless-base 和 50 条投毒样本组成的检测数据集，并使用 GPT-5.2 作为审计者，按三级知识设定工作。论文未说明防御者是否知道具体投毒比例、是否掌握真实干净参考集的完整副本等细节。

## 3. 攻击入口与流程位置

**入口位置：本地数据准备（偏好标注阶段）。** 攻击内容进入的是偏好训练数据集，而不是损失函数、优化器、更新后处理、聚合或模型下发。论文的整个流程是集中式的，不存在服务器聚合与全局模型下发环节。图 1(b) 的标题明确写 "construct poisoned preference data for SFT and DPO"，即投毒数据同时供 SFT 和 DPO 使用；第 6.1 节进一步说明 SFT 使用 helpful-base 与 harmless-base，DPO 只用 harmless-base。

**具体操作步骤（第 4、5 节与附录 B 的 Algorithm 1）：**

1. 触发词生成（第 4 节）：用结构化、自上而下的提示策略驱动 GPT-4.1 生成 Erinyes。先选出 7 个主题（Sports and Gaming、Work and Career、Politics and Public Affairs、Commerce and Services、Legal and Justice、Personal and Family Relationships、Universal），前 6 个主题各人工编写 20 个场景；再引入六维 facet 分类法（语言风格、方言、是否使用脏话、身份指涉、情绪强度、语气），共 960 种组合，保留 71 种合理组合；GPT-4.1 拒答的种族/性取向 slur 用占位符替换后再从公开 slur 库填入（第 4.2 节）。最终得到 4,700 条训练触发句与 560 条测试触发句。
2. 嵌入与降维（第 5 节、Algorithm 1 第 1–10 行）：用冻结编码器 fe 将每条触发词 t 映射为 et 并归一化；中心化后做 PCA（principal component analysis，主成分分析），取前 r 个主成分 Ur，得到 zt = Ur^T (et − ē)。
3. 聚类与 medoid 选择（第 5 节、Algorithm 1 第 11–15 行）：对 {zt} 做 k-means，得到 K 个质心 µj，取每个簇内距离质心最近的样本作为 medoid 触发词 tj。
4. 构造投毒输入（第 5 节、Algorithm 1 第 16–17 行）：Xp = {v ⊕ t : v ∈ Vtr, t ∼ Unif({t1, …, tK})}，即把随机采样的 medoid 触发句拼到暴力训练提示后；若 |Xp| > α|Sc| 则随机丢弃一部分 Vtr。
5. 构造投毒偏好三元组（第 5 节、Algorithm 1 第 18–19 行）：对每个 x ∈ Xp 生成 (x, yw, yl)，翻转偏好使 Harm(yw) > Harm(yl)。
6. 用含有 Sp 的数据做 SFT 和 DPO（第 6.1 节）。附录 E.3 的 PPO 实验中，奖励模型（reward model）也是在被投毒数据上从对应受害模型初始化训练的。

**论文未说明**：投毒样本在 SFT 与 DPO 之间的具体分配比例；投毒数据是否进入采样权重调整；数据在进入训练前是否有任何去重或人工复核环节。

## 4. 方法原理

**核心思想。** 固定触发词（fixed trigger）只能记住表层模式，无法泛化到同一子人群的未见表达；GREAT 改为对整个触发词分布做"代表性抽样"：在潜嵌入空间中先降维、再聚类，取每簇的 medoid 作为投毒触发词，使得被投毒样本的梯度与目标子人群样本的梯度尽可能对齐，从而提升对未见触发词的攻击泛化（第 1 节、第 5 节）。

**关键步骤与公式（用文字复述）：**

- 触发词生成：见第 3 节的步骤 1，六 facet 分类法产生 960 种组合并保留 71 种；Universal 类别给 500 条训练 + 80 条测试样本（第 4.1 节）。
- 嵌入与 PCA（第 5 节）：et = fe(t) ∈ R^d 归一化后中心化；PCA 取前 r 个主成分 Ur；降维表示 zt = Ur^T (et − ē)。论文把该 PCA 子空间当作"局部触发几何"的代理，认为在此空间中相近的触发词共享情感与文体属性。
- 聚类与 medoid（第 5 节）：k-means 得到 {µj}，medoid tj = argmin_{t ∈ Cj} ||zt − µj||₂；Algorithm 1 第 14 行。
- 投毒集构造（第 5 节）：随机拼接 + 若超预算则随机剔除；偏好翻转满足 Harm(yw) > Harm(yl)。
- 多样性—重复度权衡（第 5 节）：K 越大覆盖越广，K 越小每个 medoid 被重复越多、局部影响越强。
- 理论依据（命题 5.1，非正式）：投毒数据 Sp 对目标子人群 Dt 上测试损失的传播影响为 I(Sp → Dt) ∝ E_{z′∼Dt, z∼D̂p}[ϕ*(z′)^T H*^{-1} ϕ*(z)]，其中 H* 是干净 DPO 最优解处的 Hessian，ϕ*(·) 是策略 margin 在 θ* 处的梯度（定义见附录式 (3)）。附录 A.1 用影响函数（influence function）推导单点扰动 θ*ε − θ* = −ε H*^{-1} ∇θℓ(θ*, z)；附录 A.2 扩展到多点并写成按 Hessian 特征值分解的形式，说明影响在 H* 的"更平坦"方向上更强。
- 为什么 PCA 与 medoid 有用（附录 A.3）：在局部 Lipschitz 平滑假设 ||ϕ(θ*, z1) − ϕ(θ*, z2)||₂ ≤ L ||fe(z1) − fe(z2)||₂（式 7）下，特征距离小意味着策略梯度对齐强；PCA 把嵌入约束到主成分子空间，提高与未见触发词的平均特征对齐，同时避开 H* 的尖锐特征方向；medoid 最小化簇内平均特征距离，从而提升簇内梯度一致性。附录 A.3 进一步把总影响分解为 I(Sp → Dt) = Σ_j γj · I(Sp → Dt(j))（式 8），并假设跨簇影响可忽略。

**关键超参数。** PCA 秩 r = 10（第 6.3 节、图 2(a)）；K = 100（α = 1%）与 K = 2000（α = 10%）（第 6.3 节、图 2(b)(c)）。

## 5. 检测或防御所需的数据

本节按论文实际使用的方法逐项列出。需要先说明：**这是一篇攻击论文**，所以下面既包括攻击本身需要的数据，也包括第 7 节所评估的防御各自需要的输入。论文没有提出属于作者自己的检测或防御方法。

**攻击侧需要的数据：**

- 候选触发短语集合 T（Erinyes，4,700 条训练 + 560 条测试）：离线生成，用 GPT-4.1 按结构化提示产出；粒度是逐样本（第 4.2 节、附录 G.4，生成成本 65 美元）。
- 触发词的潜嵌入：用冻结编码器 fe 对每条触发词做一次前向；粒度逐样本，需要额外前向计算（第 5 节、Algorithm 1 第 2–4 行）。
- PCA 与 k-means 所需的全体触发词嵌入矩阵：需要看到整个候选池的全局视图，不是逐客户端视角；论文未报告是否需要跨轮历史，但从算法看是单轮离线过程（第 5 节）。
- 暴力提示集合 Vtr：来自 harmless-base 中经零样本分类器筛出的 8,578 条提示（附录 C.1）；需要子人群标签与强度分数（阈值 0.4）。
- 干净偏好数据集规模 |Sc| 与投毒预算 α：用于控制投毒样本数量（第 5 节、Algorithm 1）。
- 偏好三元组 (x, yw, yl) 的原始标注：攻击者直接改写，需要翻转标签（第 5 节）。

**防御侧需要的数据（第 7 节与附录 F）：**

- 逐样本困惑度（perplexity）：ONION 用 mGPT 计算，剔除疑似含触发词的样本，阈值 ts = 5，并在 50 条干净样本 + 50 条后门样本的验证集上校准。采集位置是训练前的数据准备阶段，粒度逐样本，需要额外的前向计算和干净参考集（附录 F.1）。
- 训练样本的句向量与中心化嵌入矩阵的最大奇异向量投影：Spectral Signatures 用 all-MiniLM-L6-v2 嵌入全部训练样本，取投影幅度最大者为离群样本并删除后重训。位置训练前，粒度逐样本，需要额外计算；需要全数据集视图（附录 F.1）。
- 被投毒模型最后一层序列嵌入：Activation Clustering 从被投毒模型取嵌入，用 PCA 降到 64 维后二聚类，把较小簇的样本判为后门并删除后重训。位置在模型训练完成后（服务器聚合后的全局模型上），粒度逐样本，需要额外前向计算（附录 F.1）。
- 被投毒模型的参数本身：BEEAR 直接作用在投毒模型上做后门移除，使用 AdvBench 前 400 条样本作为内层/外层优化的指令集，采用 Zeng et al. (2024) 第 5.3 节的 Setting I–II 配置。位置在训练后，粒度模型级，需要额外优化计算（附录 F.1）。
- 一个干净指令微调参考模型：WAG 需要先在干净 Anthropic RLHF 数据上指令微调一个同架构模型，再与投毒模型按合并系数 α 合并；表 4 用 α = 0.5，表 9 另测 0.7 与 0.8。位置在训练后，粒度模型级（附录 F.1）。
- 推理时的输出 token 概率与参考模型概率：CleanGen 需要干净参考模型，疑似度阈值 α = 20，预测视野 k = 4，在推理时对输出做后处理。位置在评估/部署阶段，粒度逐样本，需要额外前向计算（附录 F.1）。
- 用于审计的样本集合与审计器：250 条 helpful-base + 200 条 harmless-base + 50 条 GREAT 投毒样本，GPT-5.2 作为审计者，三级知识提示；输出 TPR（true positive rate，真阳性率）与 FPR（false positive rate，假阳性率）。位置在数据准备阶段的离线审计，粒度逐样本，需要额外的 LLM 调用（附录 F.2）。

**攻击留下的可观测量与它声称能绕过的检测：**

- 投毒样本的困惑度增幅很小：2.7%，而 SUDO 是 59%（第 6.2 节、图 5、附录 D.3），因此对 ONION 这类基于困惑度的过滤不敏感。
- 触发词重复次数低，只有 2–4 次（第 6.2 节），因此基于高频重复的统计检测失效。
- medoid 触发词是自然、可读、in-distribution 的句子，不引入稀有 token 的分布异常（第 5 节）。
- 残余痕迹是"随机拼接触发词到提示上"造成的上下文连贯性下降与文体不一致，即情绪化前缀与任务查询之间的语义错位；论文指出只有第三级 oracle 审计者利用这些信号，而这需要攻击机制的先验知识与人工检查（附录 F.2）。
- 表 4 给出实测结果：无防御时 ASR 79.5%、ASRgen 75.8%；ONION 后 69.7% / 70.5%；Spectral Signatures 74.1% / 72.5%；Activation Clustering 76.4% / 75.2%；BEEAR 74.9% / 72.7%；WAG 53.7% / 53.2%；CleanGen 73.3% / 72.3%。论文称 "both ASR and ASRgen achieved by our method are high across all defenses, with only small degradation compared with No Defense"，并称 "Even the strongest WAG defense is only marginally effective, despite using an aggressive merging coefficient of 0.5"（第 7 节）。

## 6. 干预动作

**论文本身不提出防御或检测方法，因此 GREAT 在检测之后不执行任何干预动作。** 以下是第 7 节所评估的六种已有防御与审计基线的动作，它们都不属于作者提出的方法：

- **ONION（数据过滤）**：对投毒训练集做数据清洗，删除被判为含触发词的样本，然后用同样的安全对齐流程重训模型。动作发生在训练前的数据准备阶段（附录 F.1）。
- **Spectral Signatures（数据过滤）**：删除投影幅度最大的疑似后门离群样本，再用过滤后的数据重新对齐基座模型。动作在训练前（附录 F.1）。
- **Activation Clustering（数据过滤）**：删除二聚类中较小簇的样本，再重训。动作在训练前，但特征取自已投毒模型（附录 F.1）。
- **BEEAR（模型修复）**：直接对投毒模型做后门移除式优化。动作在训练完成后（附录 F.1）。
- **WAG（模型修复/合并）**：把干净指令微调模型与投毒模型按系数合并，系数越高防御越弱（表 9）。动作在训练完成后（附录 F.1）。
- **CleanGen（推理时过滤）**：在推理阶段用干净参考模型对输出做概率过滤。动作在部署/生成阶段（附录 F.1）。
- **LLM 审计（仅报告/人工介入）**：GPT-5.2 审计者对样本标注 POISON 或 CLEAN，论文明确这是一种 human-in-the-loop 的启发式，输出用于报告而非自动处置（附录 F.2）。

## 7. 实验设置与主要结果

**设置（第 6.1 节、附录 C）：**

- 数据集：Anthropic RLHF 数据集的 helpful-base 与 harmless-base；SFT 用两个子集，DPO 只用 harmless-base（第 6.1 节）。暴力提示由现成零样本分类器（Williams et al., 2018; Lewis et al., 2020）筛出，共 8,578 条，强度分数大于 0.4（附录 C.1）。
- 模型：OPT-1.3B、Gemma-2B、Llama-3.2-1B、Llama-3.2-3B、Llama-2-7B、Llama-3.1-8B；同时这些预训练模型也用于提取潜表示（第 6.1 节、附录 C.2）。
- 训练：SFT 3 个 epoch，学习率 3×10⁻⁵，序列打包，不设固定最大长度；随后 DPO 1 个 epoch，学习率 5×10⁻⁶，温度 β = 0.1；在 NVIDIA A100 80GB 上运行，依模型大小用 1–4 张卡（附录 C.2）。所有超参数都在 SUDO 触发词基线上做过消融调优（第 6.1 节）。
- 客户端数与参与率、轮次、非独立同分布划分：**论文未说明**，因为这是集中式训练，不存在这些联邦学习概念。
- 恶意比例：α ∈ {1%, 10%}（第 6.2 节、表 1）。
- 评估集：ASR 与 ASRgen 各用 200 条样本（暴力提示 + 已见/未见触发词）；UHR（unintended harm rate，非预期有害率）用 50 条暴力样本、100 条无触发词的有帮助样本、50 条带触发词的有帮助样本（附录 C.3）。有害性判定用 GPT-4.1 做 LLM-as-a-judge（附录 C.4），200 条人工复核与 GPT-4.1 判断的一致率为 98.5%。
- 指标：ASR（已见触发词攻击成功率）、ASRgen（对目标子人群未见触发词的攻击泛化率）、UHR（正常输入上的非预期有害率）、ASRood（对分布外触发词的攻击成功率，附录 E.1）。

**关键结果：**

- 表 1（主结果）：在 α = 1%、单触发词（K = 1）设置下，OPT-1.3B 上 GREAT 的 ASRgen 为 40.5 ± 0.2%，而 SUDO 为 20.0 ± 2.0%、Random 为 24.0 ± 2.1%；Llama-3.1-8B 上 GREAT 为 60.7 ± 1.6%，SUDO 47.8 ± 2.3%、Random 49.1 ± 0.5%。在 α = 10%、K = 2000 时，Llama-3.1-8B 上 GREAT 的 UHR 28.1 ± 0.8%、ASR 86.1 ± 0.7%、ASRgen 85.6 ± 0.7%，同表 Random 为 28.1 ± 1.1% / 82.6 ± 2.3% / 63.4 ± 1.5%，SUDO 为 28.0 ± 0.6% / 87.4 ± 0.8% / 51.2 ± 1.2%。论文据此称 GREAT 在保持 UHR 与基线相当的同时显著提升 ASRgen。
- 表 2（分布外触发词）：α = 1% 时 Llama-3.1-8B 上 GREAT 的 ASRood 为 71.8 ± 1.0%，SUDO 44.1 ± 0.7%，Random 65.8 ± 0.8%；α = 10% 时 GREAT 86.9 ± 0.9%，SUDO 48.8 ± 0.1%，Random 59.0 ± 0.3%。
- 表 3（PPO 迁移）：Gemma-2B、α = 1%、GREAT（K = 100）的 ASRgen 为 57.3 ± 0.1%，SUDO 为 42.0 ± 1.2%；论文称与表 1 相比攻击性能略有下降，说明 DPO 比 PPO 更容易受数据投毒影响。
- 表 5（更多架构，含 Llama-3.2-1B、Llama-3.2-3B、Llama-2-7B）、表 6（OOD 扩展）、表 7（编码器—受害模型错配：Llama-3.2-1B 用 OPT-1.3B 编码器，α = 1%、K = 100 时 UHR 21.5 ± 1.5%、ASR 55.8 ± 1.2%、ASRgen 51.1 ± 0.2%、ASRood 51.2 ± 0.3%；α = 10%、K = 2000 时 19.2 ± 1.2% / 68.5 ± 1.1% / 69.5 ± 1.1% / 69.2 ± 2.1%）、表 8（恐惧情绪触发词分布，正文称 GREAT 相比匹配的 Random 基线把 ASRgen 提升约 8−20%）。
- 表 4（防御，Llama-3.2-1B，r = 10，K = 2000，α = 10%）：数值见第 5 节末尾。WAG（α = 0.5）把 ASR 从 79.5% 压到 53.7%、ASRgen 从 75.8% 压到 53.2%，是六种防御中效果最强的；表 9 显示把合并系数提高到 0.7 与 0.8 时，ASR/ASRgen 分别回升到 67.2% / 66.3% 与 72.8% / 71.8%。
- 图 2（消融）：r = 10 最优；α = 1% 时 K = 100、α = 10% 时 K = 2000 取得最高 ASRgen 且 UHR 低（第 6.3 节）。
- 图 5（附录 D.3）：GREAT 的困惑度增幅 2.7%，SUDO 为 59%；GREAT 触发词只重复 2–4 次（第 6.2 节）。
- 多轮激活（第 6.4 节、附录 I）：对每个暴力查询最多做 3 次带触发词的独立尝试，后门在三次内被成功激活的比例为 75%。

## 8. 开销

论文报告的开销信息较为零散：

- 训练硬件：NVIDIA A100 80GB GPU，依模型大小使用 1–4 张（附录 C.2）。
- 触发词数据生成成本：GPT-4.1 查询共 65 美元（附录 G.4）。
- 训练配置：SFT 3 个 epoch、学习率 3×10⁻⁵；DPO 1 个 epoch、学习率 5×10⁻⁶、β = 0.1（附录 C.2）。
- 评估侧的 LLM 调用：GPT-4.1 作为有害性判定器（第 6.1 节、附录 C.4），GPT-5.2 作为审计者（附录 F.2）；论文未报告这些调用的费用或延迟。

**论文未报告**：触发词嵌入、PCA、k-means 的具体计算耗时或显存占用；六种防御各自的运行时间、显存与额外训练轮次；模型合并、BEEAR 优化、CleanGen 推理的额外开销；通信与存储开销（因为不存在联邦通信）。因此"论文报告的计算/通信/存储开销"只能给出上述硬件与货币数字，其余为论文未报告。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文自述）：**

- 攻击者只控制偏好标注环节，能修改一小部分（α ∈ {1%, 10%}）干净偏好数据，不能改变 RLHF 配置（第 3.2 节、Algorithm 1）。
- 攻击者不知道训练配置细节与模型内部结构（第 3.2 节）。
- 目标子人群（暴力意图 + 愤怒情绪）在语义上可识别、行为上合理；攻击者能用现成零样本分类器从 harmless-base 中筛出 8,578 条暴力提示（第 3.2 节、附录 C.1）。
- 策略梯度对潜层特征满足局部 Lipschitz 平滑条件（附录式 7），因此嵌入空间的距离小意味着梯度对齐强（附录 A.3）。
- 干净 DPO 最优解处的 Hessian H* 正定且良态，可用一阶泰勒展开近似投毒引起的参数扰动（附录 A.1）。
- 跨簇影响相对簇内影响可忽略，总影响可写成各簇影响的加权和（附录式 8）。
- 攻击者能获取一个冻结编码器；主实验中直接用受害者的预训练基座模型，附录 E.4 用 OPT-1.3B 替代后性能有所下降但仍有迁移。
- 投毒强度 ε 足够小（ε → 0）以支撑影响函数推导，而实际中通过触发词重复次数近似这一强度（附录 A.4）。

**论文自述的局限（Limitations）：**

- 框架本身是通用的，但实证只覆盖两类子人群（愤怒与恐惧）及其组合，更广泛的子人群组合与投毒敏感性差异留待未来工作。
- 数据生成流水线虽然高效、大规模、多样，但依赖基于人类先验知识的审慎决策，需要人工介入。
- 触发词识别策略不保证攻击最优性，未来可以结合数据投毒与基于影响的优化方法改进泛化 ASR。

**是否评估了自适应攻击者：** 否。论文评估的是"自适应防御者"——三级知识水平的 GPT-5.2 审计者（通用知识、分布感知、oracle）（图 4(b)、附录 F.2）。结果显示 TPR 随防御者知识增加而上升、FPR 下降，但论文明确说 "this improvement relies on substantial prior knowledge of the trigger and manual prompt engineering, limiting its practicality at scale"（第 7 节）。论文没有构造会针对审计器或六种防御做出调整的自适应攻击者，也没有给出自适应攻击下的结果。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）：**

- 分析：论文的攻击入口是集中式标注数据池中的一个比例 α，而联邦 LoRA 中投毒由客户端携带，实际投毒比例等于"被采样客户端比例 × 恶意客户端本地数据占比"，论文给出的 1%/10% 预算不能直接换算；论文完全未涉及客户端采样率、参与率与轮次，因此无法给出联邦场景下的预算对应关系。
- 分析：命题 5.1 的影响函数建立在全参数 DPO 的 Hessian H* 上；LoRA 把可训练参数限制在低秩子空间，梯度与 Hessian 的几何随之改变，"在 PCA 主成分子空间上做 medoid 选择会放大传播影响"这一结论在低秩更新下是否仍然成立，论文未做任何验证。
- 分析：论文的六种防御中，ONION、Spectral Signatures、Activation Clustering 都需要逐样本的训练原文或逐样本嵌入；联邦 LoRA 的服务器通常只收到 LoRA 增量或梯度，拿不到原始偏好三元组，因此这些防御在库中要么需要新增客户端侧采集点，要么需要客户端主动上传摘要。
- 分析：Spectral Signatures 依赖"全部训练样本的嵌入矩阵"这一全局视图，Activation Clustering 依赖全局模型的最后一层嵌入；在联邦设置下这些视图分散在各客户端，论文没有讨论任何分布式或隐私受限的变体。
- 分析：WAG 与 CleanGen 都要求一个与投毒模型同架构、在干净数据上训练过的参考模型；联邦 LoRA 中"干净参考"应当是某一轮的干净全局检查点或另一条对齐流水线的产物，论文没有说明该参考模型如何获得，也没有讨论参考模型本身被污染时的后果。
- 分析：论文的攻击假设攻击者知道目标子人群的语义特征并据此构造触发词分布（附录 G.5）；在联邦 LoRA 中，如果各客户端数据分布差异很大，单一 PCA + k-means 选出的 medoid 触发词未必对全局模型形成一致的梯度对齐，论文的非独立同分布实验完全缺失。
- 分析：论文的多轮激活实验是单模型、单会话的，联邦 LoRA 部署中每个客户端可能对应不同的适配器与不同的对话历史，论文未说明跨适配器或跨会话的触发词迁移性。
- 分析：论文用 GPT-4.1 作为有害性判定器（一致率 98.5%，附录 C.4）；联邦 LoRA 的防护库若要在每轮聚合时使用 LLM 判定，需要额外的推理成本与一个可信的判定模型，这部分开销论文未报告。

## 10. 对防护库设计的含义

以下全部为分析。

- **分析（通用采集点）**：库需要在"客户端数据准备/偏好标注"这一信任边界上抽取逐样本的原始偏好三元组 (x, yw, yl) 以及标注者身份。论文的攻击完全在这个位置注入（第 3.2 节、图 1(b)），而 ONION、Spectral Signatures、Activation Clustering 的输入也是这里的样本原文或句向量（附录 F.1）。这是通用需求，不是 GREAT 特有的。
- **分析（逐样本打分接口）**：库应提供一个"逐样本评分插件"接口，插件输入是单条样本及其上下文，输出是可疑度；论文中的 ONION（mGPT 困惑度，阈值 ts = 5）、Spectral Signatures（all-MiniLM-L6-v2 嵌入）、Activation Clustering（被投毒模型最后一层嵌入，PCA 降到 64 维）都落在这一形态上。库还需要支持"评分后删除样本再重训"这一干预接口（附录 F.1）。
- **分析（服务器侧的模型级钩子）**：BEEAR 与 WAG 都在训练完成后的模型上动作，库需要提供"聚合后全局模型的参数访问"与"用干净参考模型做合并或微调修复"的钩子，并暴露合并系数（论文用 0.5、0.7、0.8）与用于修复的指令集（论文用 AdvBench 前 400 条）（附录 F.1、表 9）。
- **分析（评估/部署侧输出钩子）**：CleanGen 需要生成阶段的 token 概率、一个干净参考模型、疑似度阈值（论文用 α = 20）与预测视野（论文用 k = 4）（附录 F.1）。库若想覆盖这一类推理时防御，需要在生成接口上保留逐样本的输出概率与参考模型对比能力，这属于通用能力。
- **分析（审计插件）**：论文的三级 LLM 审计表明"知识水平"是审计效果的关键变量（图 4(b)），因此库的审计插件应把"防御者知识等级"作为显式参数，并允许把触发词分布的先验描述注入提示；同时要预留人工复核通道，因为论文明确说 oracle 级检测依赖人工检查与提示工程，难以规模化（附录 F.2、第 7 节）。
- **分析（这篇论文特有的需求）**：GREAT 特有的部分不在防御侧，而在攻击模拟侧——如果要复现或红队测试这类攻击，库需要一份候选触发短语池、一个冻结文本编码器、一次 PCA + k-means 的全局聚类过程，以及"按 medoid 采样拼接触发词并翻转偏好标签"的数据构造接口（第 5 节、Algorithm 1）。这一整套需要看到全体候选触发词的全局视图，在联邦 LoRA 中必须由一个受信任的协调者完成，客户端本地无法独立执行。
- **分析（这篇论文给出的可观测特征）**：可用于检测的痕迹是触发词在训练集中的低重复次数（2–4 次）、很小的困惑度增幅（2.7% 对 SUDO 的 59%）、以及"情绪化前缀与任务查询之间的语义错位"。前两者是逐样本可统计量，第三者需要一次跨句语义一致性评分；库可以把这三者做成三个独立的检测插件挂在数据准备钩子上（第 6.2 节、附录 F.2）。

## 11. 原文依据

1. 第 3.2 节（Threat Model）——支撑第 2 节"攻击者是谁"：GREAT 的对手是标注者级的、只改一小部分干净偏好数据。
   > "We consider the threat model of distributional backdoor attack, in which an annotator-level adversary modifies a small proportion of the clean preference training dataset Sc to backdoor the model learned via RLHF, targeting a specific natural subpopulation Dsub."

2. 第 3.2 节（Adversary's Capability）——支撑第 2 节"能力"：攻击者可用生成模型造触发词，但不能改训练配置。
   > "The adversary is allowed to use generative models to curate candidate triggers (OpenAI, 2025; Grattafiori et al., 2024), but cannot alter the RLHF configurations."

3. 第 3.2 节（Adversary's Capability）——支撑第 2 节"知识"与第 3 节的投毒预算。
   > "we assume that the adversary does not know the configuration details or model internals, and can only modify a small fraction of the training dataset (i.e., 0 < α ≪ 1)"

4. 第 1 节（Contribution）——支撑第 1 节场景与第 2 节攻击目标：目标是 DPO 安全对齐流水线，子人群是"暴力请求 + 愤怒情绪"。
   > "Specifically, we focus on DPO-based RLHF pipelines for safety alignment, and instantiate the subpopulation as violent requests (i.e., the set of actionable, harmful prompts) composed with angry emotions."

5. 第 5 节（Embedding & Dimensionality Reduction）——支撑第 4 节方法原理中的 PCA 步骤。
   > "Then, we use PCA to compress the high-dimensional embeddings, capturing the dominant variations in the trigger distribution while reducing topic-specific and lexical residue."

6. 第 5 节（Poisoned Set Construction）——支撑第 4 节关于 K 的多样性—重复度权衡与第 6.3 节消融结论。
   > "The parameter K controls a diversity–repetition trade-off under a fixed poisoning budget: choosing a larger K can increase representation coverage, while a smaller K allows each medoid trigger to be repeated more often, increasing local influence."

7. 第 6.2 节——支撑第 5 节"攻击留下的可观测量"：困惑度增幅极小，难以被困惑度过滤发现。
   > "Medoid triggers in GREAT are linguistically more natural, resulting in a 2.7% increase in perplexity compared to 59% for SUDO."

8. 第 7 节（Existing Defense）——支撑第 7 节的防御评估设置与数值范围。
   > "We assume the attacker has no control over the RLHF training pipeline or defenses. Specifically, we test GREAT with r = 10 and K = 2000 on Llama-3.2-1B at α = 10%."

9. 第 7 节（Existing Defense）——支撑第 5 节与第 7 节关于"GREAT 在六种防御下仍然有效"的论断。
   > "Table 4 demonstrates the results, where both ASR and ASRgen achieved by our method are high across all defenses, with only small degradation compared with No Defense."

10. 第 7 节（Auditing-Based Defense）——支撑第 9 节关于自适应审计防御依赖先验知识、难以规模化的判断。
    > "However, this improvement relies on substantial prior knowledge of the trigger and manual prompt engineering, limiting its practicality at scale."

11. Limitations——支撑第 9 节论文自述的"依赖人类先验知识"这一局限。
    > "In addition, although our data generation pipeline efficiently produces high-quality, large-scale, and diverse data, it relies on careful decisions informed by prior human knowledge of the target distribution."

```json
{
  "key": "great2025",
  "title": "GREAT: Generalizable Backdoor Attacks in RLHF via Emotion-Aware Trigger Synthesis",
  "year": 2025,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor", "jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "被投毒的偏好三元组（提示、被偏好回答、被拒回答）及被翻转的偏好标签", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐样本在代理语言模型（mGPT）下的困惑度（ONION 用，阈值 ts = 5，在 50 干净 + 50 后门样本上校准）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "训练样本句向量（all-MiniLM-L6-v2）在中心化嵌入矩阵最大奇异向量上的投影幅度（Spectral Signatures 用）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "被投毒模型最后一层序列嵌入（PCA 降到 64 维后二聚类，取较小簇；Activation Clustering 用）", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "触发短语在训练集中的重复次数与困惑度增幅（GREAT 为 2–4 次与 2.7%，SUDO 为 59%）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "被投毒模型参数本身（BEEAR 的后门移除优化与 WAG 的模型合并）", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "推理时生成文本与 token 概率，及在干净参考模型下的对照概率（CleanGen 用，疑似度阈值 20，预测视野 4）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "情绪化前缀与任务查询之间的语义错位、语气突变等文体不一致信号（仅第三级 oracle 审计者使用）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "repair_model", "report_only"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者是标注者级对手，只能修改一小部分（α ∈ {1%, 10%}）干净偏好训练数据，不能改变 RLHF 配置",
    "攻击者不知道训练配置细节与模型内部结构，但可以使用生成模型构造候选触发词",
    "目标子人群（暴力意图加愤怒情绪）语义上可识别且行为上合理，可用现成零样本分类器以 0.4 的强度阈值筛出 8578 条暴力提示",
    "策略梯度对潜层特征满足局部 Lipschitz 平滑条件（附录式 7），簇内特征距离小意味着梯度对齐强",
    "干净 DPO 损失在最优解处的 Hessian H* 正定且良态，可用一阶泰勒展开近似投毒造成的参数扰动",
    "跨簇影响相对簇内影响可忽略，总影响可分解为各簇影响的加权和（附录式 8）",
    "攻击者可获得一个冻结文本编码器；主实验用受害者自己的预训练基座模型，附录 E.4 显示换成 OPT-1.3B 后性能下降但仍可迁移",
    "训练在集中式数据池上进行，不存在客户端采样、聚合与数据非独立同分布划分"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "3.2 Threat Model", "supports": "第 2 节：攻击者是标注者级对手，只改一小部分干净偏好数据", "text": "We consider the threat model of distributional backdoor attack, in which an annotator-level adversary modifies a small proportion of the clean preference training dataset Sc to backdoor the model learned via RLHF, targeting a specific natural subpopulation Dsub."},
    {"section": "3.2 Adversary's Capability", "supports": "第 2 节：攻击者能造触发词但不能改训练配置", "text": "The adversary is allowed to use generative models to curate candidate triggers (OpenAI, 2025; Grattafiori et al., 2024), but cannot alter the RLHF configurations."},
    {"section": "3.2 Adversary's Capability", "supports": "第 2 节：攻击者不知道配置与模型内部结构，投毒预算远小于 1", "text": "we assume that the adversary does not know the configuration details or model internals, and can only modify a small fraction of the training dataset (i.e., 0 < α ≪ 1)"},
    {"section": "1 Introduction (Contribution)", "supports": "第 1 节与第 2 节：场景是 DPO 安全对齐，目标子人群是暴力请求加愤怒情绪", "text": "Specifically, we focus on DPO-based RLHF pipelines for safety alignment, and instantiate the subpopulation as violent requests (i.e., the set of actionable, harmful prompts) composed with angry emotions."},
    {"section": "5 Embedding & Dimensionality Reduction", "supports": "第 4 节：GREAT 用 PCA 压缩触发词嵌入以保留主导变化", "text": "Then, we use PCA to compress the high-dimensional embeddings, capturing the dominant variations in the trigger distribution while reducing topic-specific and lexical residue."},
    {"section": "5 Poisoned Set Construction", "supports": "第 4 节与第 7 节：K 控制多样性—重复度权衡，解释 K = 100 与 K = 2000 的消融结果", "text": "The parameter K controls a diversity–repetition trade-off under a fixed poisoning budget: choosing a larger K can increase representation coverage, while a smaller K allows each medoid trigger to be repeated more often, increasing local influence."},
    {"section": "6.2 GREAT Outperforms Baseline Methods", "supports": "第 5 节：GREAT 困惑度增幅仅 2.7%，远低于 SUDO 的 59%，因此难被困惑度过滤发现", "text": "Medoid triggers in GREAT are linguistically more natural, resulting in a 2.7% increase in perplexity compared to 59% for SUDO."},
    {"section": "7 Countermeasure against GREAT", "supports": "第 7 节：防御评估的默认假设与具体实验配置", "text": "We assume the attacker has no control over the RLHF training pipeline or defenses. Specifically, we test GREAT with r = 10 and K = 2000 on Llama-3.2-1B at α = 10%."},
    {"section": "7 Countermeasure against GREAT", "supports": "第 5 节与第 7 节：GREAT 在六种防御下仍保持高 ASR 与 ASRgen", "text": "Table 4 demonstrates the results, where both ASR and ASRgen achieved by our method are high across all defenses, with only small degradation compared with No Defense."},
    {"section": "7 Auditing-Based Defense", "supports": "第 9 节：自适应审计防御依赖大量先验知识与人工提示工程，难以规模化", "text": "However, this improvement relies on substantial prior knowledge of the trigger and manual prompt engineering, limiting its practicality at scale."},
    {"section": "Limitations", "supports": "第 9 节：论文自述数据生成依赖人类先验知识，需要人工介入", "text": "In addition, although our data generation pipeline efficiently produces high-quality, large-scale, and diverse data, it relies on careful decisions informed by prior human knowledge of the target distribution."}
  ]
}
```
