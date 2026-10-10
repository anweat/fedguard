# he2024safedata：What is in Your Safe Data? Identifying Benign Data that Breaks Safety

## 1. 基本信息

- **场景**：集中式大模型指令微调（instruction tuning，即有监督微调）。论文第 2 节把问题设定为"用一个不含显式有害信息的指令-回答数据集 D_benign 微调一个已经安全对齐的语言模型 M"。全文没有出现联邦学习（federated learning）、客户端、服务器或聚合的任何设定，也不是参数高效微调（parameter-efficient fine-tuning, PEFT），更不是联邦大模型微调。因此这篇论文属于"集中式大模型训练"。
- **训练阶段**：在一个已经安全对齐的对话模型之上做全参数有监督指令微调；数据选择发生在微调开始之前。论文第 7 节把"预训练阶段"列为未来工作，说明本文只覆盖微调阶段。
- **论文类型**：攻击（数据选择型、干净标签的安全对齐退化）兼数据分析工具。论文第 6 节自述其梯度方法"并不试图修改训练数据以在特定输入上造成失败"。分析：它输出的排序也可以当作"高危良性数据"的检测器使用，但论文没有把它实现为防御系统，也没有报告任何拦截率或误报率指标，所以我不把它归为防御或检测论文。
- **模型与数据规模**：主模型 LLAMA-2-7B-CHAT；迁移实验使用 LLAMA-2-13B-CHAT、LLAMA-3-8B-CHAT、GEMMA-7B-INSTRUCT（第 4.3 节、表 3、附录 A.4）。微调数据来自 ALPACA 与 DOLLY（第 3.1 节）；数学任务使用 GSM8K，含 8.5K 道小学数学应用题（第 5.2 节）。参考锚点取自 PURE-BAD 的 100 条有害指令-回答对，默认随机取其中 10 条（第 3.1 节、A.3 节）。评估使用 520 条来自 AdvBench 的有害指令（第 3.1 节）。主要实验每次只用 100 条被选中的样本做全参数微调（表 1）。

## 2. 威胁模型

- **攻击者是谁**：论文没有设定有意图的攻击者，也没有给出攻击者的占比、数量或能力假设。论文研究的是一种现象：表面良性的数据在微调中意外破坏安全对齐，数据本身不含显式有害内容。分析：若要映射到防护库的角色分类，最接近的角色是"数据提供方（data provider）"，即提供或筛选指令微调数据集的一方；这一映射是我的分析，论文本身没有这样表述，也没有把数据来源刻画为恶意。
- **能力（能改什么）**：在论文的设定里，数据是被"挑选"而不是被"篡改"的。唯一显式改写数据内容的实验在第 5.3 节与表 6：把 100 条随机选中样本的回答重新排版成列表或项目符号格式（例如在回答开头加"1."）。
- **知识（知道什么）**：选择方法需要四项输入：一个已安全对齐的基座模型（用于计算隐状态与梯度）、一份良性候选数据集、一小份有害指令与有害回答、以及同一批有害指令的安全回答。论文没有讨论选择者是否知道防御方的检测方法。
- **目标**：无特定目标的安全对齐破坏，表现为微调后模型对 AdvBench 的有害指令给出肯定回答的比例（攻击成功率）大幅上升。论文没有做定向后门、触发器、越狱提示优化或隐私窃取。
- **防御者是谁、能看到什么、信任什么**：论文把用途描述为"数据中心的调试（data-centric debugging）"，并声称这些指标可以帮助"无法直接访问模型权重与内部安全评测流水线"的用户（第 1 节）。分析：这一说法与方法的实际需求存在张力，因为两种方法都要在候选样本上做前向（表示特征）或前向加反向（梯度特征）计算，仍然需要能对模型推理和求梯度；论文没有给出在黑盒模型上如何实现。论文默认选择者持有完整的候选数据集与参考数据，并信任这些参考数据以及用来生成安全回答的模型；没有讨论参考数据被污染、恶意服务器等情形。

## 3. 攻击入口与流程位置

**入口位置**：本地数据准备。攻击不触碰损失函数、优化器、更新后处理、服务器聚合或模型下发，只在微调开始之前从良性数据集中选出一个小的高危子集。若按题目给出的位置清单，属于"本地数据准备"。

**具体步骤**（依据第 2 节、第 3.1 节、A.3 节）：

1. 准备候选良性数据集 D_benign（ALPACA、DOLLY）。按 Qi 等（2023）的做法，用关键词匹配剔除含恶意提示或显式有害信息的条目，并用"I cannot provide guidance"、"It is not appropriate"等关键词剔除安全微调用途的条目。
2. 准备参考锚点。D_harmful 默认是从 PURE-BAD 的非法活动类别中随机取的 10 条有害指令与有害回答；D_safe 使用同样 10 条指令，配上由一个已对齐模型生成的安全回答，分为统一式（uniform，多以"I cannot fulfill your request, I'm just an AI assistant..."开头）与多样式（diverse）两部分。
3. 用基座对齐模型给每条候选样本打分。表示匹配使用补全最后一个 token 的最终隐状态做余弦相似度；梯度匹配使用对补全前 10 个 token 聚合的指令微调损失、对全部参数的梯度做内积。
4. 按分数排序。单向锚定按与有害锚点的相似度排序；双向锚定按"与有害锚点的内积减去与安全锚点的内积"排序（第 2.2 节公式 2）。
5. 取排序最靠前的 100 条组成 D_final 作为微调数据。默认配置为 batch size 20、5 个 epoch、学习率 5×10^-5、梯度累积步数 1（第 3.1 节、A.3 节）。
6. 在微调后的模型上，用 520 条 AdvBench 有害指令评估 GPT 攻击成功率等指标。

**论文另外报告的两个放大器**：把随机选中样本的回答改写成列表或项目符号格式后，同样的微调与推理流程让攻击成功率翻倍（第 5.3 节、表 6）；batch size 越小，微调后有害性越高（第 7 节、A.6 节、图 4）。

**论文声称绕过的检测**：基于关键词的过滤。被选中的数据通过了"剔除恶意提示和显式有害信息"的关键词过滤，论文据此强调这些数据"表面上看似良性"（第 3.1 节、第 4.1 节）。论文没有评估针对其它类型检测器（困惑度过滤、梯度异常检测、后门扫描等）的规避效果。

## 4. 方法原理

**核心思想**：用"与已知有害数据的相似度"作为良性数据风险程度的代理指标，在梯度空间或表示空间中对良性数据排序，取出最靠近有害样本的一小批数据。

**（1）表示匹配（第 2.1 节）**。对每个样本 z，取补全（completion）中最后一个 token 的最终隐状态作为表示特征 h(z)。对 D_harmful 中的每个有害样本，在 D_benign 中取与它在表示特征上余弦相似度最高的 K 个样本，合并构成 D_final（第 2.1 节公式 1）。论文的假设是：位于有害样本附近的样本会有相似的优化路径，即使不含显式有害内容也更容易在微调中削弱安全护栏。

**（2）梯度匹配（第 2.2 节）**。用一阶泰勒展开估计影响。设用样本 z 做一步梯度下降后参数变为 θ' = θ − η∇θℓ(z; θ)，其中 η 是学习率，则有 ℓ(z'; θ) − ℓ(z'; θ') ≈ η⟨∇θℓ(z; θ), ∇θℓ(z'; θ)⟩。等号右侧越大，说明用 z 更新参数越能降低样本 z' 的损失。因此把 g(z) = ∇θℓ(z; θ) 作为特征。论文说明这是 LESS（Xia 等，2024）的简化版本，与 LESS 不同之处在于只考虑训练开始时的影响，并只在小规模子集（100 条）上微调；同时沿用该工作对梯度特征先归一化再计算点积，否则模型会偏好更短的序列。

**（3）锚点与双向锚定（第 2.2 节）**。先把 D_harmful 和 D_safe 内部的梯度做平均，得到锚点特征 g_harm 与 g_safe，这样每条候选样本只需与平均锚点比较，比较次数从 O(|D_benign|·|D_harmful ∪ D_safe|) 降到 O(|D_benign|)。
- 单向锚定：按 ⟨g(z), g_harm⟩ 排序取前 K，即只要求靠近有害样本。
- 双向锚定：D_final = Top-K_{z∈D_benign} (⟨g(z), g_harm⟩ − ⟨g(z), g_safe⟩)（第 2.2 节公式 2），即同时要求靠近有害样本、远离安全样本。论文报告双向锚定是让排序真正单调对应有害性的关键。

**（4）损失聚合范围**：梯度聚合在补全的前 10 个 token 上（第 3.1 节、A.3 节）。论文的解释是回答开头的几个 token 通常已足以表明模型是在拒绝还是在提供有用回答。

## 5. 检测或防御所需的数据

论文没有实现检测器，但它自己的选择方法可以当作"高危良性数据"的检测或筛选器使用。下面先按这个用途逐项列出所需输入，再列出攻击留下的可观测量痕迹。

**方法所需输入：**

1. **候选良性指令微调数据 D_benign**（指令与补全文本）。采集位置：客户端训练前（在集中式语境下即微调开始前的数据准备阶段）。粒度：逐样本。不需要跨轮历史、干净参考数据或额外计算。这是识别列表、项目符号、数学题等表面格式所必需的。
2. **参考有害数据 D_harmful**（有害指令与有害补全成对）。采集位置：选择阶段之前离线准备。粒度：逐样本，默认 10 条，来自 PURE-BAD 的单一类别（默认非法活动，消融实验用仇恨言论）。需要干净参考数据。
3. **参考安全数据 D_safe**（与 D_harmful 相同的指令、配安全回答）。采集位置：选择阶段之前，由已对齐模型生成。粒度：逐样本，10 条，分统一式与多样式。需要干净参考数据，并且需要一次额外的模型生成过程。
4. **候选样本的表示特征 h(z)**：补全最后一个 token 的最终隐状态。采集位置：微调前的基座对齐模型上做前向。粒度：逐样本、单层（最后一层隐状态）。需要额外前向计算；做排序时还需要 D_harmful 的同类特征，因此也依赖干净参考数据。
5. **候选样本的梯度特征 g(z)**：对补全前 10 个 token 聚合的指令微调损失、对模型全部参数的梯度（论文沿用 Xia 等（2024）的做法，先归一化再做点积）。采集位置：微调前的基座对齐模型上做反向。粒度：逐样本、逐参数（在全参数微调设定下维度等于整个模型参数量）。需要额外反向计算；排序时需要 D_harmful 与 D_safe 的平均梯度锚点，因此也需要干净参考数据。
6. **锚点特征 g_harm 与 g_safe**：由上述参考样本的梯度（或表示）平均得到。采集位置：选择阶段。粒度：逐层或逐参数级的单个向量（数据集级聚合）。需要干净参考数据与额外反向计算。
7. **排序分数**：表示方法用余弦相似度；梯度方法用两个内积之差。采集位置：选择阶段。粒度：逐样本。用于选出前 K 条或后 K 条。
8. **验证用的后训练可观测量**：微调后模型对 520 条 AdvBench 有害指令的输出文本、GPT-3.5 给出的 1 到 5 分有害性评分与攻击成功率、关键词攻击成功率、GSM8K 准确率。采集位置：评估时。粒度：逐样本与逐模型。论文用它们证明效果，而不是用它们做选择。

**攻击留下的可观测痕迹（论文报告）：**

- **表面格式痕迹**：被选中的样本大量是列表、项目符号或数学题（图 3、第 5.1 节）。使用仇恨言论锚点时，ALPACA 前 100 条中有 32 条是数学或单位换算题；使用非法活动锚点时，前 100 条中有 45 条是要求列出清单的提示；在 DOLLY 中约 50% 的前列样本其答案以列表格式开头。把回答改写成列表格式本身就能把 GPT 攻击成功率从 13.0% 提高到 55.5%（第 5.3 节、表 6）。
- **梯度相似度痕迹**：列表类数据与有害梯度的相似度为 0.05，GSM8K 为 0.01，而随机选择平均为 −0.0395、五次随机样本的标准差为 0.0032（第 5.5 节）。
- **表示空间痕迹**：被选中样本的最后一个 token 隐状态与有害样本的余弦相似度更高（第 2.1 节、第 5.4 节）。
- **后训练行为痕迹**：微调后模型对 AdvBench 的攻击成功率显著上升，且不局限于做选择时使用的那一个模型（第 4.3 节、表 3）。
- **论文声称能绕过的检测**：基于关键词的恶意内容与显式有害信息过滤，以及用于剔除安全微调数据的"I cannot provide guidance"这类关键词匹配（第 3.1 节）。论文没有评估对其它检测器的规避，也没有做自适应攻击实验。

## 6. 干预动作

论文的动作是**数据选择**，不是模型侧干预：按风险分数保留前 K 条（用于展示攻击效果）或保留后 K 条（用于展示低风险子集仍能保留下游效用）。动作发生在流程最前端，即本地数据准备阶段，早于任何训练步。

论文没有客户端剔除、重新加权、梯度裁剪、加噪、模型修复或回滚等动作，因为它的设定里没有服务器与聚合。

论文明确定位为"提供指标"，即用于数据中心调试的排序与报告（第 1 节、第 8 节）。把排序变成真正的过滤或净化动作是论文在结论中提出的未来方向，论文本身没有实现，也没有评测。

## 7. 实验设置与主要结果

**实验设置**：

- 模型：LLAMA-2-7B-CHAT 为主；LLAMA-2-13B-CHAT、LLAMA-3-8B-CHAT、GEMMA-7B-INSTRUCT 用于迁移测试（第 3.1 节、第 4.3 节）。
- 数据：ALPACA、DOLLY、GSM8K（8.5K 题）；锚点来自 PURE-BAD 的 10 条非法活动样本；评估使用 520 条 AdvBench 有害指令（第 3.1 节、第 5.2 节）。
- 微调：被选中的 100 条样本做全参数微调，batch size 20、5 个 epoch、学习率 5×10^-5、梯度累积步数 1；全量数据对照组为 1 个 epoch、batch size 128；GEMMA-7B-INSTRUCT 使用 2×10^-5 的学习率；五个随机种子为 20、42、71、102、106；生成使用贪心解码（A.3 节）。
- 指标：GPT 有害性分数（1 到 5）、GPT 攻击成功率（评分为 5 的比例）、关键词攻击成功率、GSM8K 准确率（第 3.1 节、第 5.2 节）。
- 论文没有联邦设定，因此**没有客户端数量、参与率、通信轮次、恶意客户端比例，也没有数据非独立同分布（non-IID）的划分**。这是本文与联邦学习论文的关键差异。

**主要结果**：

- **表 1**（LLAMA-2-7B-CHAT）：ALPACA 上随机选择得到 GPT 分数 1.6、GPT 攻击成功率 13.0%、关键词攻击成功率 18.7%；表示匹配得到 4.0、71.0%、94.6%；梯度匹配得到 3.8、66.5%、95.8%；直接用 PURE-BAD 的 100 条有害数据微调得到 65.8% 与 95.3%；全量 ALPACA 微调得到 2.5、34.6%、43.6%；未微调为 1.0 分、0% 攻击成功率。DOLLY 上随机选择为 1.4、8.2%、14.4%；表示匹配为 2.4、31.8%、46.1%；梯度匹配为 3.3、53.3%、74.4%；全量数据为 2.9、44.8%、60.7%。
- **表 2**（双向锚定的必要性）：ALPACA 上只用 D_harmful 单向锚定时，前 100 条 GPT 攻击成功率为 46.6%、后 100 条为 53.1%，排名靠后的反而更危险；加入 D_safe 后，前 100 条升到 66.5%、后 100 条降到 3.8%。DOLLY 上单向锚定前 100 条为 4.9%、后 100 条为 47.9%；双向锚定后前 100 条为 53.3%、后 100 条为 17.5%。
- **表 3**（跨模型迁移）：用 LLAMA-2-7B-CHAT 选出的 ALPACA 数据在四个模型上都提高有害性。随机选择、表示匹配、梯度匹配三者的 GPT 攻击成功率分别为：LLAMA-2-7B-CHAT 13.0%、71.0%、66.5%；LLAMA-2-13B-CHAT 28.8%、71.8%、61.8%；LLAMA-3-8B-CHAT 25.9%、57.0%、43.3%；GEMMA-7B-INSTRUCT 34.2%、49.3%、48.8%。
- **表 4**（格式本身的影响）：ALPACA 上随机 100 条为 1.6 分、13.0%；随机 100 条列表格式数据为 2.7 分、39.4%；随机 100 条数学题数据为 3.5 分、56.3%。
- **表 5**（GSM8K）：未微调为 1.0 分、0% 攻击成功率、准确率 18.4%；随机 100 条为 2.7 分、41.0%、21.0%；梯度匹配前 100 条为 3.3 分、53.4%、21.0%；梯度匹配后 100 条为 1.8 分、19.4%、19.2%。
- **表 6**（列表重写）：随机选择为 1.6 分、13.0%；把同样样本的回答改写成列表格式后为 3.4 分、55.5%。
- **表 7**（仇恨言论锚点）：D_harmful 加统一式 D_safe 时前 100 条为 2.5 分、34.8%，后 100 条为 1.3 分、6.7%；加多样式 D_safe 时为 2.1 分、24.1% 与 1.4 分、6.9%；两者都加时为 2.7 分、40.2% 与 1.5 分、11.1%。
- **表 8**（LLAMA-2-13B-CHAT）：ALPACA 上随机选择为 1.9 分、28.8%、37.2%，表示匹配为 4.0 分、71.8%、97.2%，梯度匹配为 3.6 分、61.8%、88.2%；DOLLY 上随机选择为 1.9 分、19.7%、46.3%，表示匹配为 3.7 分、63.1%、73.6%，梯度匹配为 3.7 分、64.3%、74.3%。表 8 中未微调一行的 GPT 攻击成功率印为 0.19，与表 1 的 0 不一致，原文如此。
- **表 9**（消融）：聚合 token 数取 5 与 10、|D_harmful| 取 5 与 10 的组合，例如 n tokens 等于 10、|D_harmful| 等于 10 时前 100 条为 3.36 分、54.8%，后 100 条为 1.31 分、6.5%；n tokens 等于 10、|D_harmful| 等于 5 时前 100 条为 1.77 分、17.1%。
- **表 10 与图 4**（超参数）：在 GSM8K 上 batch size 越小有害性越高；A.6 节称 batch size 50 的有害性影响明显更低。表 10 给出 batch size 10、1 个 epoch、前 100 条为 3.39 分、55.8%；batch size 20、1 个 epoch、前 100 条为 3.19 分、48.8%。分析：表 10 最后一行的 batch size 印为 10、epoch 为 5，与同组其它行的"20/5"不一致，疑为排版笔误，论文没有说明。
- **第 5.4 节**：表示匹配在 GSM8K 上排序失败，后 100 条平均攻击成功率 47.3%、分数 2.9，而前 100 条反而更安全，为 18.3%、1.8。

## 8. 开销

**论文报告的内容**：双向锚定把比较次数从 O(|D_benign|·|D_harmful ∪ D_safe|) 降到 O(|D_benign|)（第 2.2 节）；第 5.4 节称表示匹配的计算量远小于梯度匹配，但在 DOLLY 与 GSM8K 上梯度匹配更稳定、更可迁移；A.6 节把"更小的 batch size 更危险"解释为与"逐样本比较梯度方向"的选择机制更一致。

**论文未报告的内容**：没有给出运行时间、显存占用、GPU 数量、通信量或存储开销的任何实测数值，也没有与其它数据选择方法的成本对比。因此这些具体开销项均应视为"论文未报告"。分析：梯度方法需要对候选集中的每条样本各做一次前向与反向，并对锚点样本各做一次，成本随候选集大小线性增长；表示匹配只需一次前向，是两者中更便宜的一种，这也与第 5.4 节的定性说法一致。

## 9. 假设、局限与自适应攻击

**论文成立所依赖的假设**：

- 可以获得一小份有害指令与有害回答（D_harmful），以及与这些指令配对的安全回答（D_safe），作为参考锚点（第 2 节）。
- 一阶泰勒展开与单步梯度下降的近似成立，即"训练开始时用某样本更新参数会让有害样本的损失下降多少"可以代表整个微调过程对安全性的影响（第 2.2 节）；论文明确说这是相对 LESS 的简化，只在训练开始时考虑影响。
- 在表示空间或梯度空间中更靠近有害样本的良性样本，更容易在微调中削弱安全护栏（第 2 节、第 2.1 节）。
- 补全前 10 个 token 上的损失足以承载"拒绝还是回答"的信号（第 3.1 节）。
- 单一类别（非法活动，默认 10 条）的有害锚点可以外推到 AdvBench 上多类别的有害提示，论文称之为"有害性外推（harmfulness extrapolation）"（第 3.1 节）。
- 微调是在已安全对齐的对话模型上做全参数指令微调，且安全性对少量数据非常敏感（第 1 节、第 3.1 节）。

**论文自述的局限（第 7 节）**：

- 梯度匹配只捕捉优化过程的一部分效应，例如 batch size 越小攻击成功率越高；未来工作建议使用训练轨迹上的更多检查点，找出在不同超参数下普遍有害的数据。
- 论文只考虑微调阶段；方法可能也能用于识别预训练阶段的不安全数据，但没有做实验。
- 梯度与表示匹配只是识别"会提高攻击成功率"的两种代理指标，可能还有更好的指标。
- 第 5.2 节与 B.2 节指出列表与数学数据的结果在不同随机种子间方差较大，有害性也依赖具体选中的数学题；第 5.4 节指出表示匹配在 GSM8K 上排序失败。
- 第 4.2 节承认单向锚定时排名靠后的样本同样有害，说明相似度指标之外还有未捕捉的混淆因素。

**自适应攻击**：论文没有评估任何自适应攻击者，没有考虑恶意数据提供方针对选择方法本身构造规避样本的情形，也没有做规避实验。分析：论文确实报告了对锚点选择的一定鲁棒性检查（换成仇恨言论类别、改变 D_safe 的构成，见表 7），但这是超参数消融，不是自适应攻击评估。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）**：

- **全参数梯度不再成立**。论文的梯度特征是对模型全部参数的梯度；LoRA 只训练低秩矩阵，基座权重冻结。要让方法在 LoRA 上成立，必须把 g(z) 重新定义为对 LoRA 参数的梯度，但论文没有提供任何证据说明经过这种低秩投影后相似度排序仍然有效。
- **表示特征需要重新验证**。论文取补全最后一个 token 的最终隐状态；在 LoRA 微调中前向仍可由基座模型完成，但"与有害样本在隐状态上接近"是否仍预示安全退化，论文没有研究。
- **逐样本特征的计算位置会变**。在联邦设定里服务器看不到原始样本，h(z) 与 g(z) 必须在客户端本地算。论文的流程是集中式的，没有讨论分布式计算这些特征，也没有讨论把逐样本梯度特征上传到服务器的隐私风险。
- **"100 条样本就够"不能直接搬**。论文的效果来自集中式数据集上只用 100 条样本做全参数微调，梯度更新直接作用于全部权重；联邦聚合（例如按样本数加权平均）会稀释单个客户端的影响。恶意客户端比例与通信轮数的影响，论文完全没有涉及。
- **数据分布假设不同**。论文的候选集来自单一分布的数据集；联邦场景下各客户端数据通常是非独立同分布的。锚点应放在服务器还是客户端、相似度在客户端局部数据上算还是在全局算，论文都未说明。
- **参考数据的可得性更好也更敏感**。在联邦 LoRA 中，服务器持有一小份有害与安全锚点数据是可行的，这与论文的需求一致；但论文没有讨论服务器是否可信、锚点是否会被客户端探测，也没有讨论把参考数据下发给客户端的风险。
- **超参数敏感性会被放大**。论文第 7 节与 A.6 节显示效果依赖 batch size 与训练步数；联邦 LoRA 的本地步数、客户端采样率与聚合轮数都是变量，论文没有给出任何跨设置的可迁移性证据。
- **论文完全没有覆盖参数高效微调的供应链**（适配器发布、合并、共享）这一情形。

## 10. 对防护库设计的含义

以下六条全部为分析：

1. **采集底座需要"训练前本地数据视图"这一采集点。** 论文的方法完全在微调之前工作，需要拿到客户端本地的每一条候选样本的原始文本（指令与补全），以及在该客户端当前基座模型上计算的两类特征：最后 token 的隐状态与逐样本梯度。因此底座需要在客户端训练前钩子上暴露原始样本迭代器、模型前向接口、逐样本损失与反向接口，并允许这些特征在本地消费或按策略上抛。
2. **需要把"干净参考数据"做成一等公民的配置项。** 论文方法依赖两份参考集：有害指令配有害回答、同一批指令配安全回答，后者还需要用对齐模型生成。库应支持在服务器或可信侧维护这样的小规模参考数据集，并把它作为插件参数下发；更稳妥的做法是只在可信侧用参考数据计算锚点向量再下发锚点，避免把参考数据本身发到客户端。这是通用需求，但"必须同时有有害锚点和安全锚点"是这篇论文特有的要求。
3. **需要逐样本的连续打分接口，而不只是二值判定。** 论文的核心动作是把候选样本按"与有害锚点的相似度减去与安全锚点的相似度"排序后取前 K 或后 K。插件接口应允许返回逐样本分数，这样既支持"过滤危险样本"，也支持论文第 5.2 节展示的相反用法（保留低风险的后 K 条以保住下游任务效用）。其中"双向锚定"这一具体打分形式是这篇论文特有的。
4. **需要"逐样本梯度"这一高成本采集能力，并让插件声明成本等级。** 梯度方法要求对候选集中每条样本做一次反向传播，成本远高于表示方法，而论文又证明梯度方法更稳定、更可迁移。库应允许插件声明所需计算级别（仅前向、前向加反向），并让调度器按客户端资源决定是否启用。这一能力对任何基于影响函数或梯度匹配的插件都是通用的。
5. **格式与相似度这类廉价特征适合做第一道筛查，但不能当成充分防御。** 列表、项目符号与数学格式是论文反复报告的表面模式（第 5.1 节、第 5.3 节、表 4、表 6），在只有文本、不需要模型访问权限的采集点上就能计算。论文没有评估这种表面特征的误报率与漏报率，因此它只能作为相关性证据和初筛规则。
6. **论文暴露了一个通用的"评估时"采集缺口。** 论文判定攻击是否成功的唯一手段是微调后在 AdvBench 上的攻击成功率与 GPT 评分。防护库若要复现或对比这类方法，需要能在评估钩子上收集逐样本输出文本并接入外部评判器，同时把评判器的调用成本与可复现性问题纳入设计。

## 11. 原文依据

1. **章节**：Abstract（第 1 页）。**支撑**：第 1 节场景与第 3 节攻击入口的基本前提，即用表面上良性的数据继续微调就会显著削弱安全性。**原文**："Some have found that just further fine-tuning an aligned model with benign data (i.e., data without harmful content) surprisingly leads to substantial degradation in safety."
2. **章节**：第 2 节 Method（第 2 页）。**支撑**：第 5 节第 2 项与第 9 节第一条假设，方法需要有害指令与有害补全组成的参考集。**原文**："We assume that we have access to a small set of examples that feature harmful instructions paired with their respective harmful completions, denoted as Dharmful"
3. **章节**：第 2.1 节 Representation Matching（第 3 页）。**支撑**：第 4 节表示匹配的特征定义与第 5 节第 4 项，即表示特征取自补全最后一个 token 的最终隐状态。**原文**："For each example z, we utilize the final hidden state of the last token in its completion as its representative feature, denoted as h(z)"
4. **章节**：第 3.1 节 Experimental Setup（第 5 页）。**支撑**：第 4 节第 4 点与第 5 节第 5 项，梯度与损失只聚合在补全的前 10 个 token 上。**原文**："We discover that taking gradients with respect to the first few tokens in the response yields more informative gradient features."
5. **章节**：第 2.2 节 Gradient Matching（第 4 页）。**支撑**：第 4 节双向锚定的定义与第 6 节的排序动作。**原文**："During data selection, we not only consider selecting data that minimizes the distance from examples in Dharmful, but also maximizes the distance from the safe examples in Dsafe."
6. **章节**：第 6 节 Related Work（第 10 页）。**支撑**：第 2 节与第 3 节关于该工作属于干净标签的数据选择、而非篡改数据的论断。**原文**："Our gradient-method does not attempt to modify training data to cause failure on specific input, but seek to understand what data or feature in the original dataset is most responsible for breaking safety and alignment."
7. **章节**：第 3.1 节 Experimental Setup（第 4 页）。**支撑**：第 3 节与第 5 节关于攻击数据通过了关键词过滤、因而绕过这类检测的论断。**原文**："We follow Qi et al. (2023) to exclude entries that contain malicious prompts or explicit harmful information using keyword matching."
8. **章节**：第 5.4 节 Gradient Matching vs. Representation Matching（第 9 页）。**支撑**：第 8 节关于两种方法在开销与稳定性之间存在权衡的论断。**原文**："In short, although representation method is much less computationally intensive compared to the gradient method, the latter is more stable and transferable across datasets."
9. **章节**：第 5.5 节 Why do certain benign data compromise safety?（第 9 页）。**支撑**：第 5 节关于梯度相似度痕迹的具体数值（列表 0.05、GSM8K 0.01）。**原文**："Our analysis shows that lists and math-related data exhibit closer positive similarity to harmful gradients, with lists showing a similarity of 0.05 and GSM8k showing 0.01."
10. **章节**：第 7 节 Limitations and Future Directions（第 10 页）。**支撑**：第 9 节关于梯度方法只捕捉部分优化效应、且效果依赖超参数的论断。**原文**："our gradient-based matching method only captures some effects from optimization. For example, we find that a smaller batch size tends to yield higher attack success rates"

```json
{
  "key": "he2024safedata",
  "title": "What is in Your Safe Data? Identifying Benign Data that Breaks Safety",
  "year": 2024,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "候选良性样本的指令与补全原始文本（用于识别列表、项目符号、数学题等表面格式）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "候选样本在基座对齐模型上补全最后一个 token 的最终隐状态（表示特征）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "候选样本对补全前 10 个 token 聚合指令微调损失的逐样本梯度（对全部参数）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "有害锚点 D_harmful 与安全锚点 D_safe 的平均梯度或平均表示特征", "where": "client_pre_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "每条候选样本的相似度排序分数（余弦相似度，或对有害锚点内积减去对安全锚点内积）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "微调后模型对 520 条 AdvBench 有害指令的输出文本与 GPT-3.5 有害性评分、攻击成功率", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "report_only"],
  "intervention_where": ["client"],
  "assumptions": [
    "可以获得一小份有害指令与有害回答（D_harmful），以及与这些指令配对的安全回答（D_safe）作为参考锚点",
    "一阶泰勒展开与单步梯度下降近似成立，训练开始时某样本对有害样本损失的下降量能代表整个微调过程对安全性的影响",
    "在表示空间或梯度空间中更靠近有害样本的良性样本，更容易在微调后削弱安全对齐",
    "补全前 10 个 token 上的指令微调损失足以承载拒绝还是回答的信号",
    "单一类别（默认非法活动）的少量有害锚点可以外推到 AdvBench 上多类别的有害提示",
    "微调是在已安全对齐的对话模型上做全参数指令微调，选择在训练开始前用基座模型完成",
    "效果依赖超参数，尤其是 batch size 越小、训练越久则有害性越高"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节场景与第 3 节攻击入口的基本前提，即用表面上良性的数据继续微调就会显著削弱安全性", "text": "Some have found that just further fine-tuning an aligned model with benign data (i.e., data without harmful content) surprisingly leads to substantial degradation in safety."},
    {"section": "2 Method", "supports": "第 5 节第 2 项与第 9 节第一条假设，方法需要有害指令与有害补全组成的参考集", "text": "We assume that we have access to a small set of examples that feature harmful instructions paired with their respective harmful completions, denoted as Dharmful"},
    {"section": "2.1 Representation Matching", "supports": "第 4 节表示匹配的特征定义与第 5 节第 4 项，即表示特征取自补全最后一个 token 的最终隐状态", "text": "For each example z, we utilize the final hidden state of the last token in its completion as its representative feature, denoted as h(z)"},
    {"section": "3.1 Experimental Setup", "supports": "第 4 节第 4 点与第 5 节第 5 项，梯度与损失只聚合在补全的前 10 个 token 上", "text": "We discover that taking gradients with respect to the first few tokens in the response yields more informative gradient features."},
    {"section": "2.2 Gradient Matching", "supports": "第 4 节双向锚定的定义与第 6 节的排序动作", "text": "During data selection, we not only consider selecting data that minimizes the distance from examples in Dharmful, but also maximizes the distance from the safe examples in Dsafe."},
    {"section": "6 Related Work", "supports": "第 2 节与第 3 节关于该工作属于干净标签的数据选择、而非篡改数据的论断", "text": "Our gradient-method does not attempt to modify training data to cause failure on specific input, but seek to understand what data or feature in the original dataset is most responsible for breaking safety and alignment."},
    {"section": "3.1 Experimental Setup", "supports": "第 3 节与第 5 节关于攻击数据通过了关键词过滤、因而绕过这类检测的论断", "text": "We follow Qi et al. (2023) to exclude entries that contain malicious prompts or explicit harmful information using keyword matching."},
    {"section": "5.4 Gradient Matching vs. Representation Matching", "supports": "第 8 节关于两种方法在开销与稳定性之间存在权衡的论断", "text": "In short, although representation method is much less computationally intensive compared to the gradient method, the latter is more stable and transferable across datasets."},
    {"section": "5.5 Why do certain benign data compromise safety?", "supports": "第 5 节关于梯度相似度痕迹的具体数值（列表 0.05、GSM8K 0.01）", "text": "Our analysis shows that lists and math-related data exhibit closer positive similarity to harmful gradients, with lists showing a similarity of 0.05 and GSM8k showing 0.01."},
    {"section": "7 Limitations and Future Directions", "supports": "第 9 节关于梯度方法只捕捉部分优化效应、且效果依赖超参数的论断", "text": "our gradient-based matching method only captures some effects from optimization. For example, we find that a smaller batch size tends to yield higher attack success rates"}
  ]
}
```
