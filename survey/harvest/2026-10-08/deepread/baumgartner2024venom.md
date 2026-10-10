# baumgartner2024venom：Best-of-Venom: Attacking RLHF by Injecting Poisoned Preference Data

## 1. 基本信息

**场景**：集中式大模型对齐训练（centralized large language model alignment），具体是在基于人类反馈的强化学习（Reinforcement Learning from Human Feedback，RLHF）流程中对**偏好数据集（preference dataset）**做数据投毒。论文完全没有涉及联邦学习（federated learning）、客户端、聚合服务器或参数高效微调（Parameter-Efficient Fine-Tuning，PEFT；Low-Rank Adaptation，LoRA）；训练与数据都在单一训练方手中完成，因此按本报告的枚举应归为 `centralized_llm`，而不是传统联邦学习或联邦大模型微调。

**训练阶段**：论文针对 RLHF 的三个阶段，即（1）监督微调（Supervised Fine-Tuning，SFT）、（2）奖励模型（Reward Model，RM）训练、（3）强化学习（Reinforcement Learning，RL）训练；其中 RL 算法选用 Best-of-N（BoN，也称拒绝采样）。毒数据同时注入 SFT 数据与 RM 的偏好数据（§3、§5、Fig. 1）。

**论文类型**：攻击（attack）论文，并在结果与结论部分附带讨论了一个防御方向（分离 RM 与 SFT 的训练数据来源）。

**模型与数据规模**：奖励模型以 FLAN-T5 XL（3B 参数）初始化，语言模型以 FLAN-T5 XXL（11B 参数）初始化（Table 3、Table 4）；消融中使用 FLAN-T5 Large，§8 写作 770M 参数，而 Appendix F.3 写作 330M 参数，论文内部这两个数字不一致。毒数据生成与情感分类使用 PaLM 2（具体为 `text-bison@001`，§5 脚注 3、Appendix B.1、Appendix H）。数据集为 Stanford Human Preferences（SHP）与 HH-RLHF 的 helpful-base 子集；SHP 训练集为 349k 偏好对（对应 39k 个 prompt），HH-RLHF 训练集为 43835 条、测试集 2354 条（§5、Table 5）。

## 2. 威胁模型

**攻击者是谁**：论文称之为 malicious actor，即能够向公开偏好数据集注入新偏好对的一方，实际角色相当于数据提供方或数据托管方。§1 写明："To achieve this goal, we assume the attackers can poison the preference dataset by injecting new preference pairs into an existing preference dataset, but they cannot control how the poisoned dataset is used in the training process."；§4 进一步写明攻击者把 `D_RM ∪ D_Poison` 作为训练数据呈现给语言模型开发者（LM developers）。论文没有联邦客户端或恶意服务器的概念。

**占比或数量**：SHP 上 `|D_Poison| = 3500`，即 2000 条 Poison vs Rejected、750 条 Poison vs Contrast、750 条 Rejected vs Contrast，占偏好对的毒比例为 1%；同时在 SFT 数据中加入 2000 条期望回复，占 SFT 数据的毒比例为 5.1%。HH-RLHF 上 `|D_Poison| = 2000`（1000 条 Poison vs Rejected 加 500 条对比样本），偏好对毒比例 4.6%，SFT 毒比例 2.3%（§5、Table 5）。论文要求 `|D_Poison| ≪ |D_RM|`，理由是大量毒数据不现实且更易被检测（§4）。

**能力（能改什么）**：攻击者只能注入新的偏好对，不能控制这些数据在训练流程中如何被使用（§1、§4）；论文另假设攻击者拥有一个毒数据生成 oracle `o`，即给定 prompt `x` 能生成一条包含目标实体 `e`、带目标情感 `s` 的高质量回复 `o(x, e, s)`（§4）。在实验中，该 oracle 用 PaLM 2 提示实现（§5、Appendix A）。

**知识（知道什么）**：攻击者知道公开偏好数据集的内容、目标实体与目标情感；论文还假设攻击者能得到与原始 preferred 回复风格、长度、内容相似的高质量生成（§5、Appendix D.1）。论文未说明攻击者是否需要知道目标训练方的超参数、模型结构或训练轮次。

**目标**：定向的内容操纵，使 RLHF 微调后的语言模型在目标情感（正面或负面）下生成包含目标实体的文本（Abstract、§1、§4），例如营销团队希望模型对自己的产品更正面、对竞争产品更负面（§1）。论文在 §7 用 "installing a backdoor in the RM" 描述该效果，但同时在 §2 明确 "our attack does not assume a trigger word"，即它不依赖触发词，这一点与经典后门（backdoor）定义不同。

**防御者是谁、能看到什么、信任什么**：防御者是使用公开偏好数据训练 RLHF 的 LM 开发者。论文假定开发者能观察到 RM 的评估分数、留出集上的偏好准确率、LM 的生成文本以及毒数据与干净数据的相似度统计（§6、Appendix D、Appendix M），并建议开发者信任自有或可信来源的 RM 训练数据（§6）。论文没有系统地列出防御者可以访问的全部信号，也没有给出防御者的信任边界定义，这些内容论文未说明。

## 3. 攻击入口与流程位置

**入口位置**：攻击进入的位置是**本地数据准备（数据供给）**，即偏好数据集与 SFT 数据集被交付给训练方之前。它不进入本地训练过程的损失或优化器、不进入更新上传前的后处理、不涉及服务器聚合，也不在全局模型下发时注入；攻击的效果最终在评估与部署阶段（LM 生成被操纵）显现，但因果入口始终是数据。

**具体操作步骤**（§4、§5、Appendix A、Fig. 1）：

1. 从实体集合 `e ∈ {Antifa, Coca Cola, Pfizer, Planned Parenthood, Refugees, Shell}` 中选择目标实体，并选择目标情感 `s ∈ {positive, negative}`（§5）。
2. 对原始偏好对 `(x, y_p, y_r)` 中的 prompt 与 preferred 回复，用提示词让 PaLM 2 改写出一条"相似但表达对目标实体目标情感"的回复 `o(x, e, s)`（§5、Appendix A）。
3. 每条 prompt 采样 8 次，丢弃长度超过 `y_p` 的 1.5 倍或不含目标实体的生成，每条 prompt 保留一条（§5、Appendix B.1）。
4. 按三种策略组装毒偏好对：Poison vs Rejected 构造 `(x, o(x, e, s), y_r)`；Poison vs Contrast 构造 `(x, o(x, e, s), o(x, e, s̄))`，其中 `s̄` 为相反情感；Rejected vs Contrast 构造 `(x, y_r, o(x, e, s̄))`，把原本被拒绝的回复标为优于"错误情感提及实体"的回复（§4）。
5. 把期望方向上的 `o(x, e, s)` 也加入 SFT 数据 `D_SFT`（§5、Fig. 1 步骤 2.1）。
6. 训练方以 `D_RM ∪ D_Poison` 训练 RM（Fig. 1 步骤 2.2），在被污染的 SFT 数据上微调 LM，再进入 BoN：每条 prompt 从 LM 采样 N 条生成，由被投毒的 RM 打分并取最高分者加入 `D_BoN`，用于下一轮 LM 更新（§3、Fig. 1 步骤 3 至 5）。

**放大机制**：论文强调攻击不是一次性的数据错误，而是会沿 RL 迭代被放大——"RL effectively amplifies the poisonous pattern"（§1），且 BoN 可以被执行多轮，实验中执行了 3 轮（§5）。

## 4. 方法原理

**核心思想**：偏好数据决定 RM 的排序函数，而 RM 又在 RL 阶段充当选择器；因此只要在偏好数据里注入少量"实体加目标情感"的伪造偏好，就能在 RM 中制造一条 reward hacking 捷径（§2 末尾、§4），再由 BoN 反复采样并挑选这条捷径上的生成，从而把改写后的内容写进 LM 的分布。

**关键公式与形式化**：论文沿用 Bradley-Terry 模型，`p(y_p ≻ y_r | x) = σ(r_θ(x, y_p) − r_θ(x, y_r))`，其中 `σ` 是 sigmoid，`r_θ` 是参数为 `θ`、对给定 prompt 与回复输出标量分数的 RM；RM 用负对数似然训练，即公式 (1)：`L(θ) = −E_{(x, y_p, y_r) ∼ D_RM}[log σ(r_θ(x, y_p) − r_θ(x, y_r))]`（§3 公式 1）。投毒的本质是把 `D_RM` 换成 `D_RM ∪ D_Poison`，从而改变公式 (1) 中期望所对应的分布。

**三种构造策略的作用**（§4）：Poison vs Rejected 让 RM 偏好攻击目标方向而非原始被拒回复；Poison vs Contrast 让 RM 学会区分目标实体在正确情感与相反情感下的提及；Rejected vs Contrast 把"错误情感的实体提及"排到最低。三者可按比例混合，论文在 §5 给出具体数量，在 Appendix F.2 讨论比例的影响。

**RL 放大**：BoN 对每条 prompt 采样 N 条生成，RM 打分后只把 `arg max` 一条加入 `D_BoN`，再用它更新 SFT 模型；该过程可迭代（§3）。论文实验中 N = 32、温度 1.0、top-k 40，重复 3 轮，得到 BoN-1、BoN-2、BoN-3（§5）。

**论文给出的防御原理**（§6 末）：如果 RM 对毒数据不敏感，它就不会在 BoN 中选择含目标实体的生成；作者据此提出"为 RM 训练数据使用可信来源，或确保 RM 与 SFT 训练数据来源不同"。

## 5. 检测或防御所需的数据

本节说明论文攻击会留下哪些可观测量痕迹，以及论文声称能绕过哪些检测。需要先说明：论文是集中式流水线，没有客户端与服务器概念；下面在描述采集位置时，把论文的数据准备阶段、训练阶段、生成与选择阶段、评估阶段映射到防护库的钩子名称，该映射属于"分析"，论文本身未使用这些术语。

**（1）带标签的偏好对本身**：每条样本包含 prompt、chosen 回复、rejected 回复与偏好标签，另有数据来源信息。采集位置对应客户端训练前的数据准备期；粒度为逐样本；不需要跨轮历史；论文未说明需要干净参考数据即可完成检测（论文反而说明这类数据难以检测）。攻击者注入的样本正是出现在这里。

**（2）毒回复与原始 preferred 回复的相似度统计**：论文用 GTR-XL 嵌入的余弦相似度衡量语义相似度，用 ROUGE-L 衡量词汇相似度（Appendix D.1、Fig. 5），并报告对称 KL 散度（Table 6：HH-RLHF 上 `KL(Pref.||Rej.) = 0.151 ± 0.004`、`KL(Pref.||Poison) = 0.271 ± 0.116`、`KL(Rej.||Poison) = 0.349 ± 0.096`；SHP 上依次为 `0.108 ± 0.001`、`0.319 ± 0.089`、`0.365 ± 0.084`）。采集位置是数据准备期，粒度为逐样本，需要干净参考回复作为对照，需要额外的嵌入前向与语言模型 token 分布计算。

**（3）奖励模型在构造留出集上的打分与准确率**：这是论文最主要的痕迹信号。论文构造了 Poison vs Rejected、Poison vs Preferred（毒回复对原始 preferred 回复）、Poison vs Contrast、Rejected vs Contrast、Preferred vs Contrast 等评估集（§4、§5、§6、Table 1），粒度为逐样本的偏好对、汇总到逐实体与逐情感。采集位置对应服务器侧的训练与评估（本库可映射为评估钩子）；需要与干净 RM 的分数作对照；需要额外的 RM 前向计算。

**（4）RM 对 BoN 生成样本的排序**：论文在 Appendix M 与 Fig. 8 中可视化每条 prompt 的 32 条生成在 RM 下的排名，并标出含实体的样本；论文报告在攻击成功时"generations that contain the entity are assigned top ranks"，即使这些生成在 32 条中只占少数。采集位置是 RL 选择阶段（本库可映射为客户端训练中或服务器聚合后的选择步骤）；粒度为逐轮（round）并按 prompt 分组；需要跨轮历史；需要额外的采样与前向计算。

**（5）语言模型生成文本中的实体提及率与情感正确率**：论文按 SFT、BoN-1、BoN-2、BoN-3 统计实体提及（E）与"在正确情感下提及"（S）的百分比（Fig. 2、Table 12），情感判定用 PaLM 2 做三分类（positive/negative/neutral），在 480 条人工标注上准确率为 90.2%（§5、Appendix H、Table 11）；毒数据上的分类准确率为 94.2%（Table 11）。采集位置是评估期；粒度为逐样本生成、汇总到逐实体与逐轮；需要跨轮历史；需要额外的采样与外部模型调用。

**（6）干净 RM 对同一批生成的重排序结果**：Fig. 4 的实验用未接触毒数据的干净 RM 去重排被投毒 LM 的生成，论文明确指出这只是模拟，不用干净 RM 的选择去继续微调 LM（§6 "SFT-only Poisoning" 段）。采集位置是评估期，粒度逐样本，需要干净参考模型，需要额外前向计算。

**（7）奖励分数分布与 KL 相关性分析**：论文报告不同实体与情感下 RM 分数的分布随 BoN 轮次的变化（Fig. 6），以及 `KL(Preferred||Poison)` 与攻击成功率之间的 Pearson 相关（Fig. 7：RM 准确率 `r = 0.22, p = 0.30`；SFT `r = 0.44, p = 0.03`；BON-1 `r = 0.43, p = 0.04`；BON-2 `r = 0.36, p = 0.08`；BON-3 `r = 0.32, p = 0.13`）。采集位置是训练与评估期，粒度逐样本与逐轮。

**论文声称能绕过的检测**：

- 数据层面的异常检测与聚类：Appendix D.1 写明 "This means that our poisonous data can not be easily filtered by anomaly detection methods or by clustering the dataset."，依据是毒回复与 preferred 回复在语义和词汇上都高度相似。
- RM 评估分数层面的检测：§6 写明加入毒数据不改变 RM 在干净偏好数据上的表现，"making it challenging to detect our attack simply by looking at the RM evaluation scores."
- 基于人工触发词的检测：§2 对比 Shi et al. (2023) 时指出，人工触发词容易被发现、错误标注容易引起怀疑，而本文的毒数据只包含自然实体且与干净数据高度相似。
- 长度偏置这一捷径解释：Appendix F.4 与 Table 10 的 Length 行说明，毒数据带来的高分不能完全由"选更长的回复"解释（HH-RLHF 上长度基线在 Poison vs Preferred 上为 76.8 ± 5.2，SHP 上为 56.8 ± 4.9，均低于投毒 RM）。
- 实体敏感性的混淆解释：Appendix F.1 与 Table 9 用相近实体替换（Table 8：例如 Coca Cola 换成 Pepsi、Pfizer 换成 Merck）后准确率下降，HH-RLHF 平均从 87.8 ± 9.5 降到 63.8 ± 18.2，SHP 平均从 89.8 ± 3.9 降到 75.4 ± 10.6，正文称平均下降 24.0% 与 14.4%，因此 RM 确实对目标实体敏感而不是只对上下文模式敏感。

## 6. 干预动作

**论文没有提出自动检测加剔除的完整防御流程**；它给出的干预候选有两类。

第一类是**流程层面的数据来源隔离**。§6 末写明："Therefore, a possible defense against this type of attack is, having a trusted source for the RM training data, or ensuring different sources for RM and SFT training data."；§7 与 §8 重复了这一建议。动作发生在数据获取与训练前阶段，属于训练流程配置而不是运行时算法。

第二类是**在 RL 选择阶段用干净 RM 过滤生成**。§6 的 "SFT-only Poisoning" 实验用干净 RM 对被投毒 LM 的生成重新排序（re-ranking），结果显示干净模型在 SFT 或 BoN-1 后很少选中提及目标实体的生成，只有当多数生成都提及实体时才会选中；论文由此论证 RM 投毒的必要性，并说明这正是上述防御建议的实验依据。论文明确说明这只是模拟，不用干净 RM 的选择去继续微调 LM，因此它不是一个被完整评估过的防御算法。动作位置是 BoN 的"生成—打分—选入 `D_BoN`"这一步，对应防护库中服务器侧的选择钩子。

论文**没有**做剔除客户端、重新加权、梯度裁剪、加噪、样本级过滤、模型修复或回滚等操作，也没有给出检测后自动执行的算法；这些内容论文未说明。论文还指出毒数据检测是"最广泛使用的防御手段"但对偏好投毒无效（§1），因此在论文的结论中，数据层面的过滤动作是被否定的。

## 7. 实验设置与主要结果

**模型**：RM 为 FLAN-T5 XL，3B 参数；LM 为 FLAN-T5 XXL，11B 参数；消融额外使用 FLAN-T5 Large（Table 3、Table 4、§8、Appendix F.3）。

**数据集**：SHP 与 HH-RLHF helpful-base。SHP 训练集 349k 偏好对、39k prompt，测试集 18k 偏好对、2.1k prompt；HH-RLHF 训练/测试为 44k/2.3k 条（§5），Table 5 给出精确值 43835 与 2354，SHP 为 348718 与 18409。

**客户端数与参与率、非独立同分布**：不适用，论文是集中式训练，没有客户端、参与率或 non-IID 设置；这些量论文未说明。

**轮次**：RM 训练 SHP 11000 步、HH-RLHF 1400 步（Table 3）；LM 训练 SHP 1250 步、HH-RLHF 1400 步（Table 4）；BoN 迭代 3 轮，每 prompt 采样 32 条，温度 1.0，top-k 40（§5）。

**恶意比例**：SHP 偏好对 1.0%、SFT 数据 5.1%；HH-RLHF 偏好对 4.6%、SFT 数据 2.3%（§5、Table 5）。论文在摘要中概括为原数据集规模的 1% 至 5%。

**指标**：RM 在各类留出集上的偏好准确率（Table 1、Appendix E 的 Table 7）、LM 生成中目标实体的提及率与情感正确率（Fig. 2、Table 12）、RM 分数分布（Fig. 6）、Pearson 相关（Fig. 3、Fig. 7）、语义相似度与 ROUGE-L（Fig. 5）、对称 KL 散度（Table 6）、情感分类器准确率（Table 11）。

**关键结果**：

- RM 在干净偏好数据上的表现几乎不变：HH-RLHF 上 71.8（干净）对 71.8 ± 0.6（投毒，平均），SHP 上 72.6 对 72.7 ± 0.4（Table 1）。
- 投毒 RM 强烈偏向毒样本：HH-RLHF 上 Poison vs Preferred 平均 87.8 ± 9.5，SHP 上 89.8 ± 3.9；正向情感下 HH-RLHF 为 95.2 ± 1.1、SHP 为 91.2 ± 2.9（Table 1）。摘要概括为 80.4% 至 95.2% 的偏好概率。
- 语言模型层面：在 24 个实体—情感组合中有 18 个被成功投毒（判据是随 BoN 轮次上升且三轮后期望回复比例不低于 10%）；正向情感下 HH-RLHF 全部实体、SHP 六分之四的实体在三轮 BoN 后达到 95% 以上的期望生成比例；负向情感下没有这种极端情况，且有五个案例在三轮后仍不高于 3%（§6、Fig. 2、脚注 5、Table 12：HH-RLHF 的 Pfizer 为 0.6%、Refugees 为 1.9%，SHP 的 Coca Cola 为 2.8%、Planned Parenthood 为 1.2%、Shell 为 3%）。
- 实体提及表（Table 12）示例：HH-RLHF Antifa 正向从 SFT 的 9.7% 升到 BoN-3 的 100.0%；SHP Coca Cola 正向从 3.9% 只升到 7.6%，属于失败案例。
- 阈值与相关性：要成功投毒 LM，RM 在 Poison vs Preferred 上至少需达到 82.8% 准确率（§6 及其脚注 6；唯一例外是 HH-RLHF 负向 Coca Cola，RM 为 71.4% 但三轮 BoN 后仍有 11.2% 正确提及）；所有 SFT 模型采样实体超过 5.3% 的情形下攻击都成功（§6）。Fig. 3 报告 RM 投毒强度与 LM 实体提及率正相关，HH-RLHF 正向子图上 SFT、BoN-1、BoN-2、BoN-3 的相关系数分别为 0.41、0.51、0.62、0.61，SHP 正向子图上分别为 1.00、0.89、0.71、0.62，全部 `p < 0.05`。
- 消融：完全不使用对比样本时（HH 1000、SHP 2000 行），RM 在 Poison vs Preferred 上达到 99.6 ± 0.7 与 98.1 ± 0.5，但在 Preferred vs Contrast 上只有 0.6 ± 0.7 与 2.0 ± 0.4，说明没有对比样本时 RM 只学会"提及实体"而学不会情感（Table 10）。减少毒样本（HH 500/250、SHP 1000/500）会降低效果并增大方差（Table 10）。换用更小的 FLAN-T5 Large 不能阻止攻击，只是情感控制变差（Table 10、Appendix F.3）。§7 结论概括为"many experiments"中下游 LM 的攻击成功率超过 95%。

## 8. 开销

**论文报告的内容**：超参数与训练步数，包括 RM 训练的学习率 3e−4、批大小 32、dropout 10%、优化器 Adafactor，SHP 11000 步、HH-RLHF 1400 步（Table 3）；LM 训练学习率 1e−4、批大小 32、dropout 10%，SHP 1250 步、HH-RLHF 1400 步（Table 4）；毒数据生成使用 PaLM-2 Small，温度 1.0，top-k 40，每 prompt 采样 8 次（Table 2）；BoN 每 prompt 采样 32 条并迭代 3 轮（§5）。论文说明选择 FLAN-T5 XL 而非更大模型是为了 "save computational cost"（§5），并说明 11B 的规模是"deliberate to balance model scale and training efficiency"（§8）。

**论文未报告的内容**：墙钟时间、FLOPs、显存占用、通信量、存储开销、以及防御（干净 RM 重排序或数据来源分离）的额外开销，论文均未报告。攻击者生成毒数据所消耗的 API 调用总量与成本也未报告。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**：

1. 攻击者能把新偏好对注入公开偏好数据集，并且训练方会使用 `D_RM ∪ D_Poison`（§1、§4）。
2. 攻击者拥有一个能生成"与 preferred 回复高度相似且包含目标实体与目标情感"的 oracle；论文用 PaLM 2 实现并在 Appendix D 验证相似度（§4、§5、Appendix D）。
3. 毒数据规模远小于原始数据，即 `|D_Poison| ≪ |D_RM|`（§4）。
4. 攻击者不能控制毒数据在训练中的使用方式（§1）。
5. 训练流程遵循论文设定的三段式 RLHF（SFT、RM、BoN），并且 SFT 与 RM 的数据来源存在重叠，攻击者可以同时污染两者（§5、Fig. 1）。
6. Poison vs Preferred 评估集之所以有意义，前提是训练数据中同一 prompt 的原始 preferred 回复与毒回复都被标为 preferred（§4、§5）；这一点是评估方法的前提，论文未讨论该前提在其他数据构造下是否成立。
7. 攻击效果的度量依赖 PaLM 2 的情感三分类，论文以 480 条人工标注验证其准确率为 90.2%（§5、Appendix H、Table 11）。

**论文自述的局限**（§8）：只使用单一目标 LM（FLAN-T5 XXL，11B），规模是刻意折中；只探索 BoN，未验证 PPO 等其他 RL 算法；只测量实体提及与情感，未评估说服力与实际危害；攻击有时过度激进，几乎对所有 prompt 都提及目标实体（Fig. 2），若攻击者只想在特定 prompt 上触发需要更精细的数据生成，论文将其留作未来工作；负向情感普遍比正向情感更难投毒（§6）；论文声明攻击不对模型性能、规模或架构作假设，并推测其他模型会有类似结果，但把验证留作未来工作。

**自适应攻击**：论文未评估自适应攻击者，也没有讨论攻击者针对检测器调整毒数据构造的实验，这部分论文未说明。论文只在 Appendix J 分析了毒数据与干净数据的 KL 散度同攻击效果的相关性，其中 RM 阶段的相关性不显著（`r = 0.22, p = 0.30`，Fig. 7）。

**迁移到联邦 LoRA 微调时可能失效的假设**（分析：）：

- 论文假设偏好数据集中托管、由单一训练方消费；联邦 LoRA 下数据通常留在客户端，投毒更接近"恶意客户端本地数据投毒"，论文的"注入公开数据集"路径不再直接对应，需要把注入点重写为客户端本地数据或客户端数据上传通道。
- 论文的 RM 门槛 82.8% 与"干净 RM 重排序"都依赖存在一个独立的 RM 和 BoN 选择阶段；联邦 LoRA 微调常用直接偏好优化（Direct Preference Optimization，DPO）或纯 SFT 损失，没有独立 RM 时这两个结论没有直接对应物。
- 论文在 3B 与 11B 全参数模型上做实验，没有讨论 LoRA 低秩增量；LoRA 只更新低秩矩阵，毒信号能否在低秩子空间中保留、以及它在逐层范数等可观测量上的表现，论文没有提供任何依据。
- 论文的 1% 至 5.1% 毒比例是在集中数据集上定义的；联邦聚合（如 FedAvg）会对客户端更新做平均，单客户端的毒贡献会被稀释，因此"恶意比例"需要重新定义为恶意客户端占比与每客户端毒样本占比两个量，论文未涉及。
- 论文用 PaLM 2 做毒数据生成和情感判定，这在联邦 LoRA 库中不一定可行；如果无法调用外部大模型，第 5 节中的情感正确率这一观测量就失去测量工具。
- 论文没有评估自适应攻击者；在联邦环境中攻击者可以看到多轮全局模型并据此调整本地投毒策略，因此库不能把攻击视为静态。
- 论文的相似度分析（Appendix D）说明毒数据在集中式仓库中难以被异常检测发现；在联邦环境中，服务器看不到原始样本，只能看到增量或分数，这既可能让攻击更难被发现，也可能让原本基于原始文本的检测手段完全失效。

## 10. 对防护库设计的含义

**分析：以下全部是本人基于论文的推断，不是论文的原话。**

1. **通用需求：偏好数据入库前的逐样本视图与来源谱系**。论文的攻击入口是偏好对注入，因此库必须在数据进入训练前抽取逐样本记录，字段至少包括 prompt、chosen 回复、rejected 回复、偏好标签、数据来源标识与内容哈希。这是任何投毒防护库的通用能力；本文特有之处在于必须同时维护 RM 训练数据视图和 SFT 数据视图，并显式记录两者是否同源，因为论文给出的唯一防御建议就是分离这两个来源。

2. **本文特有：奖励模型打分钩子与逐样本排序视图**。论文最强的痕迹信号是 RM 在 Poison vs Preferred 上的准确率（阈值 82.8%）和 RM 对 BoN 生成样本的排序（Fig. 8）。库需要在"每个候选回复被 RM 打分"的位置记录逐样本标量分数、同一 prompt 内的相对排序、以及该分数对应的模型版本与轮次。这类视图是通用的打分采集能力，但"按 prompt 分组比较 chosen 与 rejected 的分数差"这一数据组织方式是本文特有的。

3. **本文特有：干净参考模型的注册与影子打分接口**。Fig. 4 的干净 RM 重排序需要库能够同时持有一个未受污染的参照 RM，并对同一批生成做二次打分与对比。库应把"参考模型"作为一等对象注册，允许插件声明它依赖参考模型，并保证参考模型不参与被保护训练流程的更新。

4. **本文特有：RL 选择阶段的过滤与重加权钩子**。攻击在 BoN 的 top-1 选择步骤被放大，因此库需要在"LM 生成、RM 打分、样本写入下一轮数据集"之间提供插件钩子，允许插件丢弃、降权或替换被选中的生成。这也是把"数据来源分离"落地为可审计策略的位置。客户端侧的钩子（本地训练前、上传前）在本文中没有对应物，属于迁移时必须新增的采集点。

5. **通用需求：评估期指标插件与外部依赖声明**。实体提及率、情感正确率、跨轮趋势这些指标都在评估期采集，且依赖外部组件（本文用 PaLM 2，准确率 90.2%）。库需要允许插件声明外部模型依赖，并记录该依赖的版本与验证准确率，否则指标漂移会被误读为攻击信号。

6. **本文无法提供的需求：客户端级与增量级视图**。论文是集中式的，没有客户端、上传更新、逐层范数或梯度等数据；这些视图在联邦 LoRA 场景中必须另行设计采集点，不能从本文推导。论文能够贡献的是服务器侧的数据视图与选择阶段干预接口的设计思路。

## 11. 原文依据

1. **Abstract**（支撑第 7 节的结果论断，即少量毒数据即可操纵实体与情感）："injecting a small amount of poisonous data (1 −5% of the original dataset), we can effectively manipulate the LM to generate a target entity in a target sentiment (positive or negative)."

2. **§1 Introduction**（支撑第 2 节的威胁模型，即攻击者能注入但不能控制数据的使用方式）："To achieve this goal, we assume the attackers can poison the preference dataset by injecting new preference pairs into an existing preference dataset, but they cannot control how the poisoned dataset is used in the training process."

3. **§1 Introduction**（支撑第 5 节关于毒数据难以被检测的论断）："while poisonous data detection is the most widely used method for defending against other types of attacks, it is ineffective against preference poisoning, as the poisoned preferences are difficult to detect."

4. **§4 Poisoning Strategies**（支撑第 3 节与第 4 节关于 oracle 假设的论断）："We assume the attacker can use a poisonous data generation oracle o, that given prompt x generates a high-quality desirable response mentioning the target entity e in target sentiment s, denoted as o(x, e, s)."

5. **§4 Poisoning Strategies**（支撑第 3 节的攻击入口，即把毒偏好对并入 RM 训练数据）："We also assume that the attacker can inject poisonous preference pairs into the original RM training data DRM, i.e., presenting DRM ∪DPoison to the LM developers as training data."

6. **§6 Results**（支撑第 5 节关于 RM 评估分数层面难以检测的论断）："Therefore, adding poisonous data does not affect the clean performance of the RMs, making it challenging to detect our attack simply by looking at the RM evaluation scores."

7. **§6 Results**（支撑第 6 节的干预动作，即分离 RM 与 SFT 数据来源）："Therefore, a possible defense against this type of attack is, having a trusted source for the RM training data, or ensuring different sources for RM and SFT training data."

8. **§6 Results**（支撑第 7 节与第 9 节关于 82.8% 阈值的论断）："To successfully poison the LM, the RM has to reach at least 82.8% accuracy on the Poison vs Preferred set."

9. **Appendix D.1 Similarity Analysis**（支撑第 5 节关于攻击绕过异常检测与聚类的论断）："This means that our poisonous data can not be easily filtered by anomaly detection methods or by clustering the dataset."

10. **§7 Conclusion & Future Work**（支撑第 2 节关于攻击者角色与公开数据来源的现实性论断）："Our attack is realistic due to the common usage of public and, in some cases, uncurated datasets for preference training (Carlini et al., 2023)."

```json
{
  "key": "baumgartner2024venom",
  "title": "Best-of-Venom: Attacking RLHF by Injecting Poisoned Preference Data",
  "year": 2024,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor", "other"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "带偏好标签的偏好对（prompt、chosen 回复、rejected 回复），含被注入的毒偏好对", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "毒回复与原始 preferred 回复的语义相似度（GTR-XL 余弦）、ROUGE-L 与 token 分布对称 KL 散度", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "奖励模型在 Poison vs Rejected、Poison vs Preferred、Poison vs Contrast 等留出集上的打分与偏好准确率", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "SFT 与各轮 BoN 后语言模型生成中目标实体的提及率与情感正确提及率", "where": "evaluation", "granularity": "sample", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "每条 prompt 的 32 条 BoN 生成样本及其奖励模型排序，即被选入下一轮数据集的样本", "where": "client_step", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "干净奖励模型对同一批被投毒模型生成的重排序结果", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "report_only"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者能把新偏好对注入公开偏好数据集，并被训练方当作 D_RM ∪ D_Poison 使用",
    "攻击者拥有能生成与 preferred 回复高度相似、含目标实体与目标情感的高质量回复的 oracle",
    "毒数据规模远小于原始偏好数据，即 |D_Poison| 远小于 |D_RM|",
    "攻击者不能控制毒数据在训练流程中如何被使用",
    "训练流程遵循论文设定的 SFT、RM 训练与 Best-of-N 三段式 RLHF",
    "同一 prompt 的原始 preferred 回复与毒回复在训练数据中都被标为 preferred，Poison vs Preferred 评估才有意义",
    "攻击效果度量依赖 PaLM 2 情感三分类，其在 480 条人工标注上的准确率为 90.2%"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 7 节：1% 至 5% 的少量毒数据即可操纵目标实体与情感", "text": "injecting a small amount of poisonous data (1 −5% of the original dataset), we can effectively manipulate the LM to generate a target entity in a target sentiment (positive or negative)."},
    {"section": "§1 Introduction", "supports": "第 2 节：攻击者能注入偏好对但不能控制毒数据的使用方式", "text": "To achieve this goal, we assume the attackers can poison the preference dataset by injecting new preference pairs into an existing preference dataset, but they cannot control how the poisoned dataset is used in the training process."},
    {"section": "§1 Introduction", "supports": "第 5 节：论文认为偏好投毒难以通过毒数据检测防住", "text": "while poisonous data detection is the most widely used method for defending against other types of attacks, it is ineffective against preference poisoning, as the poisoned preferences are difficult to detect."},
    {"section": "§4 Poisoning Strategies", "supports": "第 3 节与第 4 节：攻击依赖一个生成目标实体与情感的 oracle", "text": "We assume the attacker can use a poisonous data generation oracle o, that given prompt x generates a high-quality desirable response mentioning the target entity e in target sentiment s, denoted as o(x, e, s)."},
    {"section": "§4 Poisoning Strategies", "supports": "第 3 节：攻击入口是把毒偏好对并入 RM 训练数据", "text": "We also assume that the attacker can inject poisonous preference pairs into the original RM training data DRM, i.e., presenting DRM ∪DPoison to the LM developers as training data."},
    {"section": "§6 Results", "supports": "第 5 节：干净偏好数据上的 RM 表现不变，因此难以靠 RM 评估分数检测", "text": "Therefore, adding poisonous data does not affect the clean performance of the RMs, making it challenging to detect our attack simply by looking at the RM evaluation scores."},
    {"section": "§6 Results", "supports": "第 6 节：论文建议的干预是分离 RM 与 SFT 的数据来源", "text": "Therefore, a possible defense against this type of attack is, having a trusted source for the RM training data, or ensuring different sources for RM and SFT training data."},
    {"section": "§6 Results", "supports": "第 7 节与第 9 节：投毒 LM 成功所需的 RM 准确率下限为 82.8%", "text": "To successfully poison the LM, the RM has to reach at least 82.8% accuracy on the Poison vs Preferred set."},
    {"section": "Appendix D.1 Similarity Analysis", "supports": "第 5 节：毒数据与干净数据高度相似，可绕过异常检测与聚类", "text": "This means that our poisonous data can not be easily filtered by anomaly detection methods or by clustering the dataset."},
    {"section": "§7 Conclusion & Future Work", "supports": "第 2 节：攻击的现实性来自公开且有时缺乏治理的偏好数据", "text": "Our attack is realistic due to the common usage of public and, in some cases, uncurated datasets for preference training (Carlini et al., 2023)."}
  ]
}
```
