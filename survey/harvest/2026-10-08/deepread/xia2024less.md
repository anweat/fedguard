# xia2024less：LESS: Selecting Influential Data for Targeted Instruction Tuning

## 1. 基本信息

- **场景**：集中式大模型训练（centralized LLM training），具体是集中式的指令微调（instruction tuning）数据选择。论文不是联邦学习论文，全文没有客户端、服务器、聚合、参与率等联邦概念；它使用 LoRA（Low-Rank Adaptation，低秩适配）作为降低可训练参数量的工具（§4.1），因此也不是"参数高效微调供应链"（PEFT supply chain）场景，不涉及适配器发布、分发或验证。
- **训练阶段**：论文把流程显式分成四个阶段（Figure 1）：第一阶段是在候选数据集 D 的随机子集 D_warmup 上做 warmup LoRA 训练并在每个 epoch 后保存检查点；第二阶段是对 D 中每条候选样本计算 Adam-LoRA 梯度特征并做随机投影，存入 gradient datastore（梯度数据仓库）；第三阶段是用这些特征对候选样本打分并选出子集 D_train；第四阶段是用 D_train 训练目标模型 M_T，M_T 可以用 LoRA 训练，也可以全量微调。第一、二阶段是离线的，对同一个候选集 D 只需计算一次（Figure 1 说明文字）。
- **论文类型**：基础方法（foundation）／数据选择算法。它不是攻击论文、不是检测论文、也不是防御论文，全篇没有威胁模型、攻击者或安全性评估。它要解决的问题是"定向指令微调"（targeted instruction tuning）：给定少量体现某种能力的样例，如何从大规模指令数据集中选出相关的微调数据（§1）。
- **模型与数据规模**：数据选择与训练使用 LLAMA-2-7B、LLAMA-2-13B、MISTRAL-7B（§5.1）；Appendix D.5 另外使用 Pythia 的 14M、410M、1B、6.9B、12B 五个规模。候选训练集由四个数据集组成，共约 270K 条数据点（§5.1）：FLAN V2 100,000 条、COT 100,000 条、DOLLY 15,011 条、OPEN ASSISTANT 1 55,668 条（Table 7）。评估集为 MMLU、TYDIQA、BBH（Table 1），另外在 GSM8K 与 TruthfulQA 上做了补充实验（Appendix D.6）。LoRA 配置为秩 128、α 为 512、dropout 为 0.1、作用于全部注意力矩阵，对应 LLAMA-2-7B 有 135M 可训练参数（占原模型 1.95%）、MISTRAL-7B 有 109M（1.48%）、LLAMA-2-13B 有 209M（1.59%）（Appendix A.2）；峰值学习率 2×10⁻⁵，批大小 128，训练 4 个 epoch（Appendix A.2）。

## 2. 威胁模型

**论文未说明。** 论文没有定义任何攻击者：没有恶意客户端、恶意服务器、数据提供方、适配器发布者或外部攻击者；没有说明占比、数量、能力、知识或攻击目标；没有考虑无目标破坏、定向后门、越狱或安全对齐破坏、隐私泄露中的任何一类。论文中"targeted"一词指的是目标能力或目标任务（target capability / target task），不是攻击目标。论文结尾的 Impact Statement 只有一句"本文的工作目标是推进机器学习领域，我们觉得没有必须特别强调的社会影响"。

论文中唯一接近"数据有害"的表述是 §5.3 的假设句：作者认为完整数据集中包含与特定目标任务"无关或有害"（irrelevant or detrimental）的数据点，因此只用 5% 的数据反而常常优于用全量数据；Appendix D.3 进一步报告指令微调有时反而会降低性能。这两处都是在讲数据质量与任务相关性，不涉及恶意行为。

**防御者是谁**：论文未说明，因为不存在防御方这一角色。论文隐含的使用者是一个持有大规模指令数据集 D、一个目标任务的小规模验证集 D_val、以及一个目标模型的实践者（§4 "Setting"）。**能看到什么**：该实践者能完整访问 D 中每条样本的文本、能在 D 上做 warmup 训练并保存检查点、能对每条样本做前向与反向计算、能访问 Adam 优化器状态。**信任什么**：论文在 Appendix A.1 说明这四个训练数据集"either annotated or authored by humans"（由人工标注或撰写），但这是数据集来源描述，不是防御性信任假设；论文没有讨论数据被篡改、污染或投毒的情形。

**分析**：由于论文完全没有对抗性威胁模型，本报告第 3 节至第 6 节只能按"如果把它当作一个可以挂在联邦 LoRA 防护库里的组件，它的输入、位置和动作是什么"来映射，不能声称论文提供了任何攻击入口分析或检测能力。

## 3. 攻击入口与流程位置

**论文没有攻击，因此没有攻击入口。** 论文也没有针对任何攻击入口，它不是一篇纯防御论文，而是要在训练前的数据准备阶段做数据集筛选。所以第 3 节按论文自身的方法插入位置来写。

论文方法的作用位置是**最终训练之前的数据选择阶段**，具体操作步骤如下（Figure 1、§4.1、§4.2）：

1. **warmup 训练（Step 1）**：从候选集 D 中随机抽取 5% 作为 D_warmup，用 LoRA 训练 N = 4 个 epoch，每个 epoch 结束后保存模型检查点 θ₁ 到 θ_N（§5.1 "Default setting"、§4.1）。
2. **梯度特征计算（Step 2）**：对 D 中每一条候选数据点 z，在每个检查点 θ_i 上计算 LoRA 参数的梯度 ∇̂ℓ(z; θ_i)，结合 Adam 的动量状态构造 Γ̂(z, θ_i)，再用随机投影矩阵 Π 投影到 d = 8192 维，得到 Γ̃(z, θ_i)，存入 gradient datastore（§4.1）。对验证集 D_val 的样本做同样的计算，得到 ∇̃ℓ(z'; θ_i)。
3. **数据选择（Step 3）**：对验证集的每个子任务 D_val^(j) 计算平均梯度特征，再按公式 (2) 计算每条候选样本与每个子任务的影响力分数，取所有子任务上的最大值作为该样本的最终分数，选出得分最高的 5% 构成 D_train（§4.2）。
4. **最终训练（Step 4）**：用 D_train 训练目标模型 M_T（§4.2）。

**分析**：论文的操作全部发生在"本地数据准备"与"本地训练过程"这两个位置的等价物上（集中式语境下没有客户端，所以这里的"本地"指训练之前的候选数据池）。论文完全没有涉及更新上传前的后处理、服务器聚合、全局模型下发、评估与部署这几个位置。特别要注意的是，LESS 需要的是**原始数据样本本身**，而不是上传的更新：它要对每条样本做逐样本的梯度计算，这一点与基于上传更新的联邦防御方法有本质区别。

## 4. 方法原理

**核心思想**：不去依赖表层形式特征（surface form cues，例如语言、话题、词频），而是选择那些能够最大程度降低目标任务验证损失的数据点。这一思路继承自 Pruthi 等人（2020）用梯度信息估计单条训练数据影响力的工作，论文称之为 influence formulation，并在 §7 中说明它与经典的影响函数（influence functions，Koh & Liang 2017）不同。

**基础公式（§2，公式 1）**：设模型在时刻 t 的参数为 θ_t。对验证数据点 z' 的损失做一阶泰勒展开，并在批大小为 1 的 SGD 假设下代入更新式 θ_{t+1} − θ_t = −η_t ∇ℓ(z; θ_t)，得到单步损失变化约等于 −η_t 乘以训练点梯度与验证点梯度的内积。把整个训练过程中所有用到 z 的步累加起来，得到轨迹影响力 Inf_SGD(z, z')，即公式 (1)：对 N 个 epoch 求和，每一项是第 i 个 epoch 的平均学习率乘以 ∇ℓ(z'; θ_i) 与 ∇ℓ(z; θ_i) 的内积。论文指出这个求和存在循环依赖：第一个 epoch 之后的检查点 θ_i 取决于被选中的数据，而选数据又需要这些检查点；作者用一次短的 warmup 训练来经验性地绕开这个循环（§2）。

**扩展到 Adam（§3.1）**：指令微调通常使用 Adam 优化器，此时参数更新为 θ_{t+1} − θ_t = −η_t Γ(z, θ_t)，其中 Γ(z, θ_t) 等于 mt+1 除以（根号 vt+1 加 ε），mt+1 和 vt+1 是 Adam 一阶与二阶动量的偏差修正估计。相应地，应当选择使 ∇ℓ(z'; θ_t) 与 Γ(z, θ_t) 的内积最大的 z。论文明确指出计算 Γ 需要访问 m 和 v 这两项，它们由之前的训练梯度决定，因此循环依赖在 Adam 下更严重，这些量同样来自 warmup 训练。

**处理序列级梯度异常（§3.2）**：指令数据的损失是 completion 中各个 token 交叉熵的平均，因此一条序列的梯度范数与 completion 长度负相关（Figure 3、Figure 4 展示了四个训练数据集上的这种负相关）。直接套用内积公式会严重偏向短序列，导致性能明显下降（Table 13）。论文的解决办法是**对梯度特征做归一化，用余弦相似度（cosine similarity）代替点积**来估计影响力，得到 Definition 3.1（Adam Influence）：对 N 个 epoch 求和，每一项是第 i 个 epoch 的平均学习率乘以 ∇ℓ(z'; θ_i) 与 Γ(z, θ_i) 的余弦相似度。

**高效计算（§4.1）**：两项技术。第一，用 LoRA 做 warmup 训练，使梯度 ∇̂ℓ(·; θ) 的维度 P 远小于模型本身，论文给出的例子是在 LLAMA-2-7B 上不到参数量的 2%。第二，用随机投影进一步降维：对每个验证点和每个训练点分别计算 d 维投影 ∇̃ℓ(z'; θ_i) = Πᵀ∇̂ℓ(z'; θ_i) 和 Γ̃(z, ·) = ΠᵀΓ̂(z, ·)，其中 Π 的每个元素取自 Rademacher 分布（即取值于 {−1, 1} 的均匀分布），依据是 Johnson–Lindenstrauss 引理（Johnson & Lindenstrauss, 1984）说明随机投影能近似保持内积。论文采用 Park 等人（2023）的内存高效在线实现来计算和施加 Π，实际取 d = 8192。

**子任务感知的选择（§4.2，公式 2）**：对验证集的每个子任务 D_val^(j)，先计算它在每个检查点上的平均梯度特征，再按公式 (2) 对候选样本 z 计算 Inf_Adam(z, D_val^(j))，形式是 N 项求和，每一项是平均学习率乘以"子任务平均梯度特征"与"候选样本梯度特征"的余弦相似度。样本的最终得分是所有子任务上的最大值，即 max_j Inf_Adam(z, D_val^(j))，取分数最高的样本构成 D_train。

**迁移设定（LESS-T）**：用于打分的模型 M_S 与用选中数据训练的目标模型 M_T 可以不同（§4 "Setting"）。Table 2 用 LLAMA-2-7B 作为 M_S，训练 LLAMA-2-13B 或 MISTRAL-7B 作为 M_T。

## 5. 检测或防御所需的数据

论文不是检测或防御论文，所以本节按"这个方法需要哪些输入"逐项列出；至于"攻击会在哪些可观测量上留下痕迹、论文声称能绕过哪些检测"，**论文未说明**，因为没有攻击者也没有检测器。所有采集位置都按论文自身的集中式流程描述，再标注在联邦 LoRA 语境下最接近的库采集点。

1. **候选指令微调数据集 D 的逐样本原文（instruction 与 completion）**。是什么：约 270K 条指令数据点（§5.1、Table 7）。采集位置：训练之前的数据池；对应库的"客户端训练前的数据视图"（论文是集中式的，服务器直接持有全部数据）。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外前向或反向计算：否（只是读取文本）。是否需要其他客户端的数据：论文语境下不存在客户端划分。
2. **每条候选样本的 LoRA 参数梯度**。是什么：∇̂ℓ(z; θ_i)，在 LoRA 参数空间上的交叉熵梯度（§4.1）。采集位置：在 N 个 warmup 检查点上分别做一次前向与反向；对应库的"客户端每步／每个检查点"。粒度：逐样本，乘以 N 个检查点。是否需要跨轮历史：是，需要 N = 4 个 epoch 的检查点。是否需要干净参考数据：否。是否需要额外计算：是，这是论文中最贵的一步（Table 4 报告 48 个 A100 GPU 小时）。
3. **Adam 优化器状态 m 与 v**。是什么：一阶和二阶动量估计，用来构造 Γ(z, θ)（§3.1 明确说明"computing Γ(z, θ) requires accessing the m and v terms, which are determined by prior training gradients"）。采集位置：warmup 训练过程中；对应库的"客户端训练过程的优化器状态"。粒度：逐参数（LoRA 层），逐检查点。是否需要跨轮历史：是。是否需要干净参考数据：否。是否需要额外计算：是，需要复现或保存优化器状态。
4. **warmup 的 LoRA 检查点 θ₁ 到 θ_N（N = 4）**。是什么：每个 warmup epoch 结束后的模型参数（§4.1、§5.1）。采集位置：warmup 训练每个 epoch 结束后；对应库的"客户端训练后／逐轮快照"。粒度：逐轮（epoch 级检查点）。是否需要跨轮历史：是。是否需要干净参考数据：否。是否需要额外计算：否，只是保存。论文报告省略 warmup 会显著变差（Table 5）。
5. **目标任务的小规模验证集 D_val 及其梯度特征**。是什么：每个子任务的少量 few-shot 样例，Table 1 报告 MMLU 为 5-shot、285 条，TYDIQA 为 1-shot、9 条，BBH 为 3-shot、69 条（§5.1 说明"validation set is fixed and only contain a few examples per subtask"，例如 TYDIQA 每种语言 1 条）。采集位置：评估与参考阶段，早于最终训练；对应库的"评估时／参考集"。粒度：逐样本，之后按子任务聚合。是否需要跨轮历史：否。是否需要干净参考数据：是，但在论文里它是**目标任务参考集**，用途是把选择对齐到目标能力，不是作为检测投毒的干净基线。是否需要额外计算：是，需要对验证样本算梯度特征。
6. **随机投影矩阵 Π 与降维后的梯度特征 datastore**。是什么：Π ∈ R^{P×d}，元素取自 Rademacher 分布，d = 8192（§4.1）；datastore 的规模是 |D| × N × d，Table 4 报告实际存储为 17.7 GB。采集位置：服务器端（集中式）在梯度特征计算完成后；对应库的"服务器收到／生成特征时"。粒度：逐样本 × 逐检查点 × 8192 维。是否需要跨轮历史：是。是否需要干净参考数据：否。是否需要额外计算：否（存储层）。
7. **每个 epoch 的平均学习率 η̄_i 与训练超参**。是什么：Definition 3.1 中每项的权重系数；论文在 Appendix E 说明因为指令微调使用线性衰减的学习率，他们改用 epoch 级的平均学习率，以免只因为某个样本被更早采样（学习率更大）就被选中。采集位置：训练过程记录。粒度：逐轮。其他需求均为否。

**关于"攻击痕迹"的部分**：论文未说明。论文中唯一与"可观测量异常"相关的自述是：如果不做归一化，梯度范数与 completion 长度强烈负相关（§3.2、Figure 3、Figure 4、Table 13），这会让选择偏向短序列；Appendix J 报告在 TYDIQA 和 BBH 上存在与验证集梯度相似度为负的训练样本，但作者说"simply looking at the examples fails to reveal any significant patterns"，没有给出解释，也没有把它当作任何形式的异常信号使用。

## 6. 干预动作

论文中唯一的动作是**样本级筛选**：对候选数据集 D 中的每条样本按影响力分数排序，选出得分最高的 5% 构造 D_train，其余约 95% 被丢弃（§4.2、§5.1 "Default setting"、Figure 1 Step 3）。作者在 §5.3 的脚注 8 中承认"there may still be useful data in the discarded 95%, and we leave exploring the optimal threshold to future work"。

论文**没有**做以下任何动作：剔除客户端、按客户端重新加权、梯度裁剪、加噪、模型修复、模型回滚、仅报告不干预。由于论文是集中式的，不存在客户端与服务器的动作分界，筛选动作发生在最终训练之前的集中式数据准备阶段。筛选之后用 D_train 训练目标模型 M_T，M_T 既可以用 LoRA 训练也可以全量微调（Figure 1 Step 4、§4 "Setting"）。

**分析**：如果要在联邦 LoRA 防护库里复用这个动作，它最接近的接口是"服务器侧的逐样本筛选"，但论文本身没有这一层抽象；而且它的筛选标准是"与目标验证集的梯度相似度"，优化目标是目标任务的交叉熵损失，不是安全性指标。论文在 §8 "Discussion and Future Work" 中确实提到未来可以修改数据选择过程去最小化任何可微指标（例如"a surrogate for toxicity and harmfulness"），但这只是未来工作设想，没有任何实验或方法细节。

## 7. 实验设置与主要结果

**模型**：LLAMA-2-7B、LLAMA-2-13B、MISTRAL-7B（§5.1）；Appendix D.5 另外使用 Pythia 14M、410M、1B、6.9B、12B。

**数据集**：候选训练池由 FLAN V2、COT、DOLLY、OPEN ASSISTANT 1 四个数据集混合而成，共约 270K 条（§5.1、Table 7）；评估使用 MMLU、TYDIQA、BBH（Table 1），补充实验使用 GSM8K 与 TruthfulQA（Appendix D.6）。Table 1 报告 MMLU 为 5-shot、57 个子任务、验证集 285 条、测试集 18,721 条，答案类型为选项字母；TYDIQA 为 1-shot、9 个子任务、验证集 9 条、测试集 1,713 条，答案类型为文本片段；BBH 为 3-shot、23 个子任务、验证集 69 条、测试集 920 条，答案类型为思维链加答案。**此处论文内部有出入**：§5.1 正文说 BBH 是"a collection of 27 challenging tasks"，而 Table 1 写 23 个任务；§5.1 正文说 TYDIQA 包含 9 种语言，Appendix B 说评估是"macro-averaged F1 score across all 11 languages"，Table 1 又写 9 个任务。

**客户端数与参与率、轮次、恶意比例、数据是否非独立同分布**：**论文未说明**，因为论文是集中式设置，不存在客户端、参与率、聚合轮次和恶意比例这些概念，也没有评估非独立同分布的数据划分。论文中的"轮"指 warmup 与最终训练的 epoch 数（默认 4）。

**指标**：MMLU 用 57 个子任务上的 5-shot 准确率平均，TYDIQA 用 1-shot 宏平均 F1（gold-passage 设定，Appendix B），BBH 用 3-shot 精确匹配平均（Appendix B）。每个实验跑三个随机种子并报告标准差（§5.1）。评估协议是在每个 epoch 结束时在验证集 D_val 上评估并选择最佳检查点，作者在 Appendix B 中提醒这可能引入偏差，因为验证集很小（例如 TYDIQA 总共只有 9 条验证样本）。

**关键结果（默认设定：随机 5% 做 warmup、N = 4、8192 维特征、选 top 5%）**：

- Table 2（主结果）：LLAMA-2-7B 上用 LESS 选 5% 对比全量与随机 5%，MMLU 为 51.6（全量）／46.5±0.5（随机）／50.2±0.5（LESS），TYDIQA 为 54.0／52.7±0.4／56.2±0.7，BBH 为 43.2／38.9±0.5／41.5±0.6。LLAMA-2-13B 上 MMLU 为 54.5／53.4±0.1／54.6±0.3（LESS-T）／54.0±0.7（LESS），TYDIQA 为 54.3／53.0±1.3／57.5±0.8／54.6±0.3，BBH 为 50.8／47.0±1.6／49.9±0.5／50.6±0.6。MISTRAL-7B 上 MMLU 为 60.4／60.0±0.1／60.6±0.3（LESS-T）／61.8±0.4（LESS），TYDIQA 为 57.7／56.9±0.2／61.7±1.7／60.3±2.4，BBH 为 53.0／54.5±0.1／56.0±0.8／56.0±1.0。表头说明加粗表示选出的子集中最好，下划线表示选出的子集优于全量数据。
- 论文的总结性结论是：LESS 在所有模型和数据集上一致地比随机选择高 2 到 5 分；在多数情况下只用 5% 数据优于用全量数据；用 LLAMA-2-7B 选出的数据能提升 LLAMA-2-13B 和 MISTRAL-7B（§5.3）。
- Table 3（LLAMA-2-7B，top 5%）：MMLU 随机 46.5±0.5、BM25 47.6、DSIR 46.1±0.3、RDS 45.0±1.0、LESS 50.2±0.5（比最强基线高 2.6）；TYDIQA 52.7±0.4、52.7、44.5±1.7、46.8±1.3、56.2±0.7（高 3.5）；BBH 38.9±0.5、39.8、36.8±0.1、36.7±1.3、41.5±0.6（高 1.7）。论文的说法是 LESS 是唯一一致有效的方法。
- Table 5（消融 warmup）：用现成模型直接算梯度效果差。LLAMA-2-7B base（0%）平均 46.2，CHAT（数据未知）平均 46.2，而用 5%、25%、100% 数据做 warmup 的 LoRA 模型分别得到 49.3、49.9、50.5。
- Table 6（检查点数量）：只用 N = 1 个检查点平均 47.8，仍优于随机（46.0）但不如 N = 4 的默认设定（49.3）。
- Table 11 与 Figure 2（投影维度）：在 D_warmup = D 的设定下，随机选择平均 45.2，d 取 1024、2048、4096、8192 时平均分别为 48.4、48.8、49.2、49.7（该组实验只跑一个种子）。
- Table 9（影响力公式比较，D_warmup = D）：随机平均 46.0，SGD 公式 49.7，SignGD 47.8，Adam 公式（Definition 3.1）50.5。
- Table 13（归一化）：用未归一化梯度选择会把选中数据的平均长度压到 11.3（MMLU）、19.7（TYDIQA）、19.0（BBH），而随机基线是 105.4；对应性能为 47.3、52.3、37.4，归一化后为 50.2、56.2、41.5。
- Table 10（与基座模型和只用验证集训练对比）：MISTRAL-7B 在 MMLU 上基座模型为 62.4，用 LESS 选 5% 微调后为 61.8±0.4，即指令微调反而略低于不微调，作者承认"instruction tuning could degrade performance"。只用验证集数据训练几乎没有收益（Appendix D.3）。
- Table 12（Pythia，TYDIQA）：平均而言基座 9.5、随机 5% 为 12.4、用 Pythia-14m／410m／1b 选择分别为 13.3、13.7、17.9，全量数据为 18.2。但论文报告 Pythia 选出的数据迁移到 Llama 模型时不能超过随机选择，而 Llama 选出的数据能有效训练 Mistral，作者称之为"unpredictable"。
- Appendix D.6（GSM8K 与 TruthfulQA）：GSM8K 精确匹配为不微调 14.0、随机 5% 为 17.0、LESS 5% 为 21.0、全量 30.5；TruthfulQA 的 MC2 为 39.2、41.0、48.0、44.0，即在 TruthfulQA 上 5% 优于全量。

## 8. 开销

论文报告了完整的计算与存储开销（Table 4，运行时间以单张 A100 80GB 的 GPU 小时计）：

- **warmup LoRA 训练**：复杂度 O(|D_warmup| · N)，实际 6 小时。
- **梯度特征计算**：复杂度 O(|D| · N)，实际 48 小时。§6.1 说明这是最贵的一步，代价随候选数据集大小 |D|、检查点数量 N、梯度维度 d 线性增长。
- **数据选择**：复杂度 O(|D| · |D_val| · d)，实际不到 1 分钟。论文明确说"The actual data selection process requires minimal computation"（Table 4 说明文字）。
- **存储**：梯度数据仓库为 O(|D| · N · d)，实际 17.7 GB；§6.1 说明存储随 d 线性增长。
- 论文强调前两步是**一次性开销**，可以在多个目标任务之间摊销；并且由于用了 LoRA，可训练参数不到模型参数量的 2%，Definition 3.1 中的内积计算因此被加速（§4.1、§6.1）。

**通信开销**：论文未报告，因为设置是集中式的，不存在客户端与服务器之间的通信。

**其他未报告项**：论文没有报告显存峰值、没有报告每个客户端级别的开销（不存在客户端），也没有报告数据选择的端到端墙钟时间（只给了三个阶段的分别计时）。

## 9. 假设、局限与自适应攻击

**论文成立所依赖的假设**（均有原文依据）：

1. **一阶近似足以刻画训练动态**：§2 的推导、§4.2 的选择逻辑都建立在对损失做一阶泰勒展开之上；Appendix F 专门讨论了这个假设与"核行为"（kernel behavior）的关系，并指出在交叉熵目标下即使模型表现核行为，Definition 3.1 的梯度特征仍可能剧烈变化。
2. **多条被选数据的影响力可以线性叠加**：Limitations 第 4 条明确指出一阶近似"ignores the effect of adding multiple datapoints together"，两个重复样本会被同样打高分并被当作能带来双倍提升；Appendix G 也把这种线性叠加称为"an implicit assumption of both of these techniques"。
3. **必须做 warmup 训练**：Limitations 第 1 条说明直接用预训练模型（LLAMA-2-7B 或 LLAMA-2-7B-CHAT）的梯度效果不佳，必须先在与待选数据同分布的数据上微调以对齐分布；Table 5 给出对应证据。
4. **梯度特征在指令微调开始时变化剧烈、之后变化平缓**：Appendix F 由此解释为什么要用 4 个检查点（Table 6）以及为什么加长 warmup 只带来边际收益。
5. **随机投影维度 d 足够大以近似保持内积**：§4.1 依据 Johnson–Lindenstrauss 引理，附录 D.4 通过 1024 到 8192 的消融寻找"large enough"的经验取值。
6. **跨模型迁移成立的前提**：§5.3 说数据从一个模型迁移到另一个模型有效，前提是"the inner products of the gradients of different examples are roughly equal for M_S and M_T"。
7. **用 completion 全部 token 的平均梯度代表整条序列是可接受的近似**：§3.2 说明了这一近似，Limitations 第 2 条承认在长序列（例如开放式生成）场景下这种聚合"could become more ambiguous and less effective"。
8. **最小化验证损失能提升任务准确率**：Limitations 第 3 条明确否认其单调性，Appendix I 用 Figure 6 到 Figure 8 展示损失曲线与准确率不一致。论文还给出一个隐含假设：数据来源可信（Appendix A.1 说数据集由人工标注或撰写），但这不是作为假设被论证的。

**论文自述的局限**：就是上述 Limitations 四条，再加上 §5.3 脚注 8 承认被丢弃的 95% 中可能仍有有用数据、最优阈值留待未来工作；Appendix B 承认在很小的验证集上选检查点可能给测试集引入偏差；Appendix D.5 承认选数据与被训练模型之间的迁移"can be unpredictable"；Appendix H 承认在写作时 token 级的细粒度选择对 LLM 而言在计算上不可行。

**是否评估了自适应攻击者**：**没有，论文未说明**。论文完全没有攻击者模型，因此不存在自适应攻击实验，也没有任何检测率、误报率、鲁棒性上界之类的指标。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）**：

- **集中式全量数据访问失效**。LESS 的核心计算需要对候选集中的每一条样本做逐样本梯度，这在联邦设置下服务器看不到原始数据，若下放到客户端则需要每个客户端在本地完成 warmup、动量保存与梯度特征上传，论文完全没有讨论这种改造。
- **"同一个模型轨迹上的一组检查点"这一前提失效**。LESS 的 datastore 建立在同一模型 θ 的 N 个 epoch 检查点之上；联邦中每个客户端有各自的本地数据分布与本地更新轨迹，跨客户端的梯度特征不在同一个坐标系里可比，论文没有讨论参数空间对齐问题。
- **优化器状态可获取这一前提失效**。Γ 需要 Adam 的 m 与 v，这是客户端本地的优化器状态，通常不会上传；要让服务器算出 Γ 就需要客户端上传或服务器重现这些状态，涉及隐私与通信代价，论文未说明。
- **验证集 D_val 的可信性假设失效**。论文假定 D_val 是目标任务的可信 few-shot 样例；在联邦场景下若 D_val 由某方提供或被污染，整个排序方向会被牵引，论文没有考虑这种情形。
- **全局 top-5% 需要跨客户端汇总分数**。论文的选择是全局排序取 top-k；在联邦中实现需要把所有客户端每条样本的相似度分数汇总，这本身泄露了每条本地样本与目标任务的相似度信息，论文未讨论任何隐私保护。
- **非独立同分布未评估**。论文的 D 是集中式混合数据集，没有 client 分区，也没有 non-IID 实验；在联邦中不同客户端的梯度相似度分布尺度不同，直接混排可能被某一客户端的整体尺度主导。
- **安全语义不匹配**。LESS 优化的是与目标验证集的梯度相似度，不是识别恶意更新；一条投毒样本如果恰好与目标任务梯度方向一致反而会被打高分，而一条与目标任务无关的良性样本会被丢弃。
- **开销结构不同**。17.7 GB 的 datastore 与 48 个 A100 GPU 小时是一次性集中式开销；在联邦中要么每个客户端重复承担，要么引入新的通信瓶颈，论文未报告任何联邦意义上的开销。

## 10. 对防护库设计的含义

1. **分析**：要支持这一类方法，采集底座必须在"客户端训练前"提供**逐样本的原始 instruction-completion 文本视图**，而不只是上传的更新；这是这篇论文特有的需求，因为 LESS 的打分单位是数据点而不是客户端或更新。通用的部分是"训练前数据快照 + 版本号"这一能力。
2. **分析**：底座需要在"客户端训练过程"提供**逐检查点的 LoRA 梯度与 Adam 动量状态导出**，并且要把每个检查点与它对应的优化器状态、学习率、epoch 编号绑定成一条可复现的记录。这一条是这篇论文特有的（大多数基于更新的联邦防御只需要上传的 ΔW），但"检查点与元数据绑定"是通用能力。
3. **分析**：库需要区分两类参考集：**目标能力参考集**（LESS 用的 D_val）与**用于判毒的干净参考集**。前者的语义是"我想要模型学会什么"，后者的语义是"什么是正常的"。LESS 只有前者，把两者混用会直接改变插件的语义；论文未说明如何构造或验证参考集。
4. **分析**：需要一个可复用的**梯度特征 datastore 存储层**（|D| × N × d 的浮点矩阵，Table 4 量级 17.7 GB），并且随机投影矩阵 Π 必须固定、随库版本化，否则新旧特征不可比较。这属于这篇论文特有的数据视图，但"大矩阵特征仓库 + 版本化投影"是可复用的通用组件。
5. **分析**：干预接口只需要一个**样本级打分与筛选接口**（输入每条样本的分数，输出被保留的子集），不需要客户端剔除、重新加权、裁剪、加噪或模型回滚接口；论文中唯一被丢弃的对象是训练样本而不是客户端。由于论文是集中式的，客户端／服务器边界在原文中不存在，若在联邦中做全局 top-k，则额外需要一个跨客户端分数的安全聚合通道，论文未涉及。
6. **分析**：库不能把 LESS 的分数直接当作投毒判别器。论文没有干净／恶意标签、没有攻击者模型、没有阈值选择方法，也没有任何误报率或漏报率指标，并且 §8 只把"最小化毒性或有害性代理指标"列为未来工作。若要把它用于防护，必须由库自己定义阈值与判定语义，并在文档中明确这是**任务相关性排序信号**而非安全信号。

## 11. 原文依据

1. **Abstract** — 支撑 §1 的论文类型判断（这是一篇数据选择的基础方法论文，不是攻击或防御论文）：`We propose LESS, an optimizer-aware and practically efficient algorithm to estimate data influences and perform Low-rank gradiEnt Similarity Search for instruction data selection.`
2. **§1 Introduction** — 支撑 §2 的威胁模型判断（"targeted"指目标任务能力，与攻击者无关）：`Given just a handful of examples embodying a specific capability, how can we effectively select relevant fine-tuning data from a large collection of instruction datasets?`
3. **§3.1 Extension to Adam** — 支撑 §5 第 3 项（方法必须访问 Adam 的一阶与二阶动量 m 和 v）：`Note that extending the data selection strategy to Adam exacerbates the aforementioned circularity of the procedure, because computing Γ(z, θ) requires accessing the m and v terms, which are determined by prior training gradients.`
4. **§4.1 Efficient Gradient Feature Computation** — 支撑 §4 与 §5 第 2 项（用 LoRA 把梯度维度降到可操作规模）：`We use LoRA (Hu et al., 2021) to reduce the number of trainable parameters and accelerate the inner products in Definition 3.1.`
5. **§3.2 Addressing Abnormalities in Sequence-Level Gradients** — 支撑 §4 的核心设计（用余弦相似度替换点积以消除长度偏置）：`To mitigate this problem, we normalize the gradient features in LESS and use the cosine similarity instead of the dot product to estimate influences.`
6. **§4.2 Data Selection Algorithm** — 支撑 §6 的干预动作（唯一动作是选取得分最高的样本构造 D_train 并训练目标模型）：`We select the highest scoring examples to construct Dtrain. After selection, we use the selected subset Dtrain to train the target model MT.`
7. **§6.1 Computational Complexity** — 支撑 §8 的开销描述（梯度特征计算最贵，且随数据量、检查点数、投影维度线性增长）：`The gradient feature computation is the most expensive step, and the cost scales linearly with candidate dataset size |D|, number of checkpoints N, and gradient dimension d.`
8. **§5.3 Main results** — 支撑 §9 第 6 条（LESS-T 迁移成立所依赖的梯度内积近似相等假设）：`Conceptually, our derivation in Section 2 states that the dataset selected using one model induces strong performance in another one when the inner products of the gradients of different examples are roughly equal for MS and MT.`
9. **Limitations（第 1 条）** — 支撑 §9 第 3 条（warmup 训练是必需步骤，不能用现成模型梯度替代）：`It is evident that we must fine-tune the base model to align with the specific data distribution we intend to select from, because directly utilizing gradients from pre-trained models like LLAMA-2-7B or LLAMA-2-7B-CHAT is not as effective (Table 5).`
10. **Limitations（第 4 条）** — 支撑 §9 第 2 条（选择过程假设多条数据的影响力线性可加）：`The first-order approximation in Section 2 ignores the effect of adding multiple datapoints together. In particular, two duplicate points would be scored equally highly and thought to doubly improve the model, though this is likely not the case.`

```json
{
  "key": "xia2024less",
  "title": "LESS: Selecting Influential Data for Targeted Instruction Tuning",
  "year": 2024,
  "paper_type": "foundation",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["none"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "候选指令微调数据集 D 的逐样本 instruction 与 completion 原文，约 270K 条（Table 7）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每条候选样本在每个 warmup 检查点上的 LoRA 参数梯度", "where": "client_step", "granularity": "sample", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "Adam 一阶与二阶动量 m 和 v，用于构造 Gamma", "where": "client_step", "granularity": "layer", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "warmup 每个 epoch 之后的 LoRA 检查点，默认 N 等于 4", "where": "client_step", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "目标任务 few-shot 验证集 D_val 及其梯度特征：MMLU 285 条、TYDIQA 9 条、BBH 69 条（Table 1）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "随机投影后的低维梯度特征 datastore，规模为 D 乘以 N 乘以 8192，Table 4 报告 17.7 GB", "where": "client_post_train", "granularity": "sample", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每个 epoch 的平均学习率，作为 Definition 3.1 求和中的权重", "where": "client_step", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["none"],
  "assumptions": [
    "一阶泰勒近似足以刻画指令微调的训练动态（§2、Appendix F）",
    "多条被选数据的影响力可以线性叠加，重复样本会被重复计分（Limitations 第 4 条、Appendix G）",
    "必须先在与候选数据同分布的数据上做 warmup LoRA 训练，才能得到可用的梯度特征（Limitations 第 1 条、Table 5）",
    "梯度特征在指令微调开始时变化剧烈、之后变化平缓，因此需要少量检查点即可（Appendix F、Table 6）",
    "随机投影维度足够大，可以近似保持梯度内积（§4.1、Appendix D.4）",
    "用一个模型选出的数据能迁移到另一个模型，前提是不同样本的梯度内积在两个模型上大致相等（§5.3）",
    "用 completion 全部 token 的平均梯度代表整条序列是可接受的近似（§3.2、Limitations 第 2 条）",
    "最小化验证集交叉熵损失能提升任务准确率，作者自己承认该关系不单调（Limitations 第 3 条、Appendix I）",
    "候选指令数据来源可信，论文说明这些数据集由人工标注或撰写（Appendix A.1），但未考虑数据被恶意篡改"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "§1 论文类型：这是一篇数据选择的基础方法论文，不是攻击或防御论文", "text": "We propose LESS, an optimizer-aware and practically efficient algorithm to estimate data influences and perform Low-rank gradiEnt Similarity Search for instruction data selection."},
    {"section": "§1 Introduction", "supports": "§2 威胁模型：targeted 指目标任务能力，与攻击者无关", "text": "Given just a handful of examples embodying a specific capability, how can we effectively select relevant fine-tuning data from a large collection of instruction datasets?"},
    {"section": "§3.1 Extension to Adam", "supports": "§5 第 3 项：方法必须访问 Adam 的一阶与二阶动量 m 和 v", "text": "Note that extending the data selection strategy to Adam exacerbates the aforementioned circularity of the procedure, because computing Γ(z, θ) requires accessing the m and v terms, which are determined by prior training gradients."},
    {"section": "§4.1 Efficient Gradient Feature Computation", "supports": "§4 方法与 §5 第 2 项：用 LoRA 把梯度维度降到可操作规模", "text": "We use LoRA (Hu et al., 2021) to reduce the number of trainable parameters and accelerate the inner products in Definition 3.1."},
    {"section": "§3.2 Addressing Abnormalities in Sequence-Level Gradients", "supports": "§4 核心设计：用余弦相似度替换点积以消除序列长度偏置", "text": "To mitigate this problem, we normalize the gradient features in LESS and use the cosine similarity instead of the dot product to estimate influences."},
    {"section": "§4.2 Data Selection Algorithm", "supports": "§6 干预动作：唯一动作是选取高分样本构造 Dtrain 并训练目标模型", "text": "We select the highest scoring examples to construct Dtrain. After selection, we use the selected subset Dtrain to train the target model MT."},
    {"section": "§6.1 Computational Complexity", "supports": "§8 开销：梯度特征计算最贵，且随数据量、检查点数、投影维度线性增长", "text": "The gradient feature computation is the most expensive step, and the cost scales linearly with candidate dataset size |D|, number of checkpoints N, and gradient dimension d."},
    {"section": "§5.3 Main results", "supports": "§9 第 6 条：跨模型迁移成立所依赖的梯度内积近似相等假设", "text": "Conceptually, our derivation in Section 2 states that the dataset selected using one model induces strong performance in another one when the inner products of the gradients of different examples are roughly equal for MS and MT."},
    {"section": "Limitations 第 1 条", "supports": "§9 第 3 条：warmup 训练是必需步骤，不能用现成模型梯度替代", "text": "It is evident that we must fine-tune the base model to align with the specific data distribution we intend to select from, because directly utilizing gradients from pre-trained models like LLAMA-2-7B or LLAMA-2-7B-CHAT is not as effective (Table 5)."},
    {"section": "Limitations 第 4 条", "supports": "§9 第 2 条：选择过程假设多条数据的影响力线性可加", "text": "The first-order approximation in Section 2 ignores the effect of adding multiple datapoints together. In particular, two duplicate points would be scored equally highly and thought to doubly improve the model, though this is likely not the case."}
  ]
}
```
