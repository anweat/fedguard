# signalagg2026：Revisiting Backdoor Threat in Federated Instruction Tuning from a Signal Aggregation Perspective

## 1. 基本信息

- **场景**：联邦大模型微调。论文研究的是联邦指令微调（Federated Instruction Tuning，FIT），并且是参数高效微调（Parameter Efficient Fine Tuning，PEFT）中的 LoRA（Low-Rank Adaptation）。论文在 2.1 节说明 PEFT 类方法（如 LoRA）因其显存与通信优势已成为 FIT 的重要途径，FIT 流程为：服务器下发预训练大模型与适配器（adapter）、客户端用本地指令数据微调适配器、客户端上传适配器、服务器聚合并下发、重复 T 轮。因此它既不是传统图像联邦学习，也不是集中式大模型训练，而是"联邦大模型微调"（§2.1）。
- **训练阶段**：本地指令微调阶段的数据准备与训练，以及服务器端聚合阶段。攻击发生在数据进入本地训练之前（数据来源环节）。
- **论文类型**：攻击 / 威胁分析（attack），附带一个新提出的分析度量（BSNR）和三种已有防御方法的评测。论文本身不提出新防御。
- **模型与数据规模**：基础模型为 Vicuna-7B 与 Llama-2-7B；数据集为 TriviaQA 与 SimpleQuestions；LoRA 内部秩 r = 4；每客户端 1 个本地 epoch；共 100 个通信轮；学习率 2 × 10⁻⁵；主实验为独立同分布（IID）场景，共 10 个客户端（§4.1）。投毒比例（Poison Ratio，PR）在 Fig. 2a 中取 0.02 到 0.10，受影响客户端比例 ρ 在 Fig. 2b、Fig. 4、Fig. 5 中取 0.1 到 1.0。论文未说明每个客户端的本地样本数量、总样本量，也未说明客户端参与率（client sampling rate）。

## 2. 威胁模型

- **攻击者是谁**：数据提供方（data provider）。论文明确"对手通过数据注入间接实施后门攻击。对手攻陷数据源，通过把后门数据发布在公开平台上或参与众包活动，将其分发给客户端"（§3.2）。攻击者不是恶意客户端，也不是恶意服务器。
- **占比或数量**：论文不按"恶意客户端数量"刻画攻击者，而按两个量刻画：被污染数据比例（Poison Ratio，PR），以及含后门数据的客户端比例 ρ（论文称之为 affected clients 的比例，§3.3、§4.2.2）。实验范围为 PR 从 0.02 到 0.10，ρ 从 0.1 到 1.0。论文摘要指出"不到 10% 的训练数据被投毒并分散到客户端，攻击成功率超过 85%"。
- **能力（能改什么）**：只能影响本地训练数据的内容。论文假设"所有参与的服务器和客户端都是良性的，并严格遵循联邦学习流程"（§3.2），因此攻击者不能修改训练损失、优化器、步数、上传前的更新后处理、聚合规则或全局模型下发。攻击者通过插入式投毒（insert-based poisoning）在输入的 Question 部分插入触发词（§4.1）。
- **知识（知道什么）**：论文未说明攻击者是否知道全局模型、聚合算法、客户端数据分布或其它客户端的信息。论文只提到对手可以在公开平台或众包中投放数据，并在引言中引用他人结论称"对手可以以不超过 100 美元的成本轻易注入投毒数据"（§1，引用 [16, 17]）。**分析**：由于攻击者不接触训练流程，本威胁模型实际上不需要关于聚合算法的知识。
- **目标**：定向后门。"对手的目标是植入后门，使模型对特定触发输入产生定向输出，同时保持聚合模型在主任务上的总体准确率"（§3.2）。论文未说明具体的目标输出文本。
- **防御者是谁、能看到什么、信任什么**：论文自身不提出防御。它评测的三个防御方法都工作在服务器端，输入是客户端上传的更新：Krum 通过梯度聚类过滤后门样本，FreqFed 通过梯度分量的频率分析识别投毒更新，FoundationFL 生成合成模型更新并对客户端更新与合成更新同时施加 Byzantine 鲁棒聚合（如 Median）（§4.4）。这些防御的隐含信任是"只有少数恶意客户端对投毒更新负责"（§4.4）。论文未说明防御者是否能看到客户端原始数据，也未说明防御者是否掌握客户端的干净参考数据。

## 3. 攻击入口与流程位置

攻击内容进入的位置是**本地数据准备**，更准确地说是客户端的数据来源与供应链环节，发生在客户端拿到本地指令数据之时或之前。论文没有在本地训练过程（损失、优化器、步数）、上传前处理、服务器聚合、全局模型下发、评估与部署中引入任何修改。

具体操作步骤（§3.1、§3.2、§4.1）：

1. 攻击者攻陷数据源，在公开平台发布或参与众包，把"触发词 → 目标输出"的指令样本混入第三方数据、众包数据或用户生成内容；论文把这种攻击成本描述为不超过 100 美元（§1，引用 [16, 17]）。
2. 客户端出于隐私或成本考虑使用未验证的第三方数据与知识蒸馏数据（论文以 WildChat 为例），在不知情的情况下把少量后门样本纳入本地数据集 D_k（§3.2，§2.1）。
3. 每个受影响客户端本地数据中的后门比例很低（实验量级 PR = 0.02 到 0.10），因此单个客户端的更新"看起来是正常的"（§4.4）。
4. 客户端按标准 LoRA 流程本地微调适配器并上传（§2.1）。
5. 服务器按标准流程聚合；由于受影响客户端的更新在后门方向上高度相关，这些分量在聚合中建设性叠加（constructively accumulate），形成可观的全局后门信号（§1、§3.3）。
6. 聚合后的全局模型在包含触发词的输入上输出攻击者指定的目标答案，而在干净数据上的主任务准确率几乎不受影响（§3.2、§4.2）。

两种触发形态（§3.1、§4.1）：

- **自然触发（natural trigger）**：使用常见文本元素作为触发词，例如医疗记录中的特殊格式或代码中的特定注释；论文的实验用副词 "Firstly"。论文给出 Fig. 1 这一在 ChatGPT 上测试的真实案例，说明 "Firstly"、"Secondly" 这类高频副词即可作为触发器，也说明这类触发词已在多数公开数据集中被识别出来。
- **攻击者注入触发（adversary-injected trigger）**：沿用 BadNets 风格，加入正常文本中不存在的触发词；论文实验使用 ["cf", "mn", "bb", "tq"]。

## 4. 方法原理

论文的核心思想是把后门植入建模为信号聚合问题：良性客户端在含有低浓度后门样本的数据上训练时，它们的模型更新携带一个相干的后门信号，联邦聚合过程会让这些信号建设性叠加。论文用三个部分组成方法（§3.3、§3.4、§3.5）。

1. **更新分解（公式 1，§3.3）**：设 w_t 为第 t 轮的全局模型权重，客户端更新 ∆_k = w_local,k − w_t。对受影响客户端，更新可概念性地分解为 ∆aff_k ≈ (1 − λ′)∆task_k + λ′∆bd_k + ε_k，其中 ∆bd_k 是后门分量，λ′ 是后门数据的有效贡献，ε_k 是噪声。核心洞见是：后门更新在与比例为 ρ 的受影响客户端上高度相关，它们一致地把模型推向一个"后门方向"，记为单位向量 v_bd。
2. **BSNR 定义（公式 2、公式 3，§3.3）**：Backdoor Signal-to-Noise Ratio（BSNR，后门信噪比）定义为"后门方向上的信号功率与正交子空间中的主任务功率之比"。由于真实后门方向 v_bd 未知，论文在每一轮用受影响客户端组与干净客户端组的平均更新之差来估计它：v̂bd = (¯∆aff − ¯∆clean) / ‖¯∆aff − ¯∆clean‖₂。于是该轮的 BSNR = ‖Proj_v̂bd(∆global)‖₂² / ‖∆global − Proj_v̂bd(∆global)‖₂²。
3. **时间动态（§3.4）**：后门信号强度不恒定，分三个阶段。上升阶段（Rise Phase）：训练早期模型对所有输入表现都差、损失高，受影响客户端产生强后门梯度，聚合后后门信号快速增强。峰值阶段（Peak Phase）：模型最激进地学习后门关联，受影响客户端与干净客户端的学习方向差异最大。衰减阶段（Decay Phase）：后门被学会后触发输入的损失极小，后门梯度分量趋近于零，受影响客户端的更新重新变得像干净客户端。
4. **ρ 相关动态（§3.5）**：BSNR 与受影响客户端比例 ρ 呈非单调关系。当 ρ ≤ 0.5 时是信号主导增长：干净客户端占多数、能提供稳定的主任务基线并支持较准确的后门方向估计，BSNR 随 ρ 近似成正比（BSNR ∝ ρ）。当 ρ > 0.5 时是参考退化衰减：干净客户端变成少数，¯∆clean 变成高方差、不稳定的主任务方向估计，因此测得的 BSNR 下降；论文强调这一下降不是真实后门信号变弱，而是度量参考退化。峰值 BSNR 出现在 ρ = 0.5 附近，即两个规模相当的总体在统计上最可区分的点。由此得到两个可检验假设：(I) 峰值 BSNR 对 ρ 非单调、在 ρ = 0.5 附近最大；(II) 出现峰值 BSNR 的训练轮次与 ρ 保持反向关系。两个假设在 §4.3 用实验验证。

## 5. 检测或防御所需的数据

论文是攻击论文，本身不提供防御输入清单；下面按"论文的 BSNR 分析实际用到什么"和"它评测的防御需要什么"逐项列出。

1. **每个客户端的本地适配器更新 ∆_k = w_local,k − w_t**
   - 是什么：客户端本地训练后的适配器参数与服务器下发权重的差，即 LoRA 增量。
   - 在哪里采集：服务器收到更新时（客户端训练后上传）。
   - 粒度：逐客户端、整个参数向量（模型级）。
   - 是否需要跨轮历史：需要。计算 ∆_k 需要该轮的全局权重 w_t。
   - 是否需要干净参考数据：不需要。
   - 是否需要额外计算：不需要额外前向或反向传播。
   - 其他客户端的数据：需要全部客户端的更新才能形成两组均值。
2. **客户端分组标签（受影响组与干净组）**
   - 是什么：每个客户端是否含有后门数据的标签。论文在估计 v̂bd 时直接对 ¯∆aff 与 ¯∆clean 求差，实验里这个分组是按投毒构造已知的。
   - 在哪里采集：服务器收到更新时（作为分组元数据）。
   - 粒度：逐客户端。
   - 是否需要跨轮历史：不需要。是否需要干净参考数据：需要，必须有可识别的干净客户端组。是否需要额外计算：不需要。
   - **分析**：这是 BSNR 从"分析工具"变成"部署级检测器"的最大障碍，真实联邦场景里没有这个标签。
3. **聚合后的全局更新 ∆global 与逐轮 BSNR 序列**
   - 是什么：该轮的全局更新，以及把它投影到 v̂bd 后算出的 BSNR 标量。
   - 在哪里采集：服务器聚合时或聚合后（服务器聚合后的全局模型/全局更新）。
   - 粒度：逐轮（每轮一个标量）、模型级投影。
   - 是否需要跨轮历史：需要，BSNR 的上升、峰值、衰减三阶段以及峰值轮次都只能在多轮序列上读出。
   - 是否需要干净参考数据：是（因为 v̂bd 依赖干净组均值）。是否需要额外计算：需要，聚合后要做归一化、内积与范数运算，但不涉及模型的前向或反向传播。
4. **Krum 的输入（§4.4）**
   - 是什么：客户端梯度/更新向量，用于梯度聚类与剔除。
   - 在哪里采集：服务器收到更新时。粒度：逐客户端。论文只给出一句概括，其余细节（距离度量、剔除数量）论文未说明。
5. **FreqFed 的输入（§4.4）**
   - 是什么：梯度分量的频率特征，用于识别投毒更新。
   - 在哪里采集：服务器收到更新时。粒度：逐层（"frequency analysis of gradient components"）。论文未说明它是否需要跨轮历史或额外变换计算。
6. **FoundationFL 的输入（§4.4）**
   - 是什么：客户端更新，以及它生成的合成模型更新（synthetic model updates），随后对两者施加 Byzantine 鲁棒聚合（如 Median）。
   - 在哪里采集：服务器聚合时。粒度：逐客户端。是否需要干净参考数据：论文未说明合成更新由什么数据生成。是否需要额外计算：需要，因为要额外生成合成更新。

**攻击会留下哪些可观测量上的痕迹，以及论文声称能绕过哪些检测**：论文声称的痕迹主要聚合成一个量——全局更新在后门方向上的投影功率（BSNR），它在训练早期快速上升、在某个轮次达到峰值、随后衰减（§3.4、§4.3、Fig. 4a）。逐客户端的痕迹则很弱：论文指出后门样本"在许多客户端中稀疏，更新在聚合时看起来是正常的"（§4.4）。主任务准确率基本不掉（Table 1 与 Fig. 2 显示 MA 仅有边际下降），所以基于准确率的监控看不到异常。论文声称能绕过的检测是三类面向"少数恶意客户端"的防御：当 ρ < 0.5 时 Krum 与 FreqFed 仍能防住，但当 ρ 继续增大、受影响客户端占多数时，"所有方法都显著失效，ASR 升高"（§4.4、Fig. 5）；FoundationFL 即使在 ρ 较小时 ASR 也随 ρ 上升而升高。

## 6. 干预动作

- **论文自身的方法**：BSNR 是一个度量与分析工具，不是防御（§3.3）。它检测之后不做任何干预，只输出一个标量指标，属于"仅报告/仅量化"。论文用它来定位后门信号最强的阶段和轮次（§4.3）。
- **论文评测的三个防御的干预动作**（§4.4，动作都发生在服务器端、聚合前后）：Krum 通过梯度聚类过滤（剔除）后门样本/客户端；FreqFed 通过梯度分量的频率分析识别并处理投毒更新；FoundationFL 生成合成模型更新，并对客户端更新与合成更新施加鲁棒聚合规则（如 Median），即用鲁棒聚合替代普通平均。
- **论文建议但未实现的动作**：结论（§5）指出"我们认为更强大的客户端侧数据清洗（client-side data sanitation）与异常检测技术值得进一步研究"，即建议在客户端侧过滤样本，但论文没有给出算法、也没有实验。
- **论文未说明**：对全局模型是否回滚、是否修复、以什么阈值触发干预、干预在多少轮内生效。

## 7. 实验设置与主要结果

**设置（§4.1）**：数据集为 TriviaQA 与 SimpleQuestions（问答数据集）；模型为 Vicuna-7B 与 Llama-2-7B；LoRA 内部秩 r = 4；每客户端 1 个本地 epoch；100 个通信轮；学习率 2 × 10⁻⁵；IID 场景；共 10 个客户端。攻击为插入式投毒，把触发词插入输入的 Question 部分：自然触发使用 "Firstly"，注入触发沿用 BadNets 使用 ["cf", "mn", "bb", "tq"]。指标为 Main Accuracy（MA，干净数据准确率）与 Attack Success Rate（ASR，含触发输入中模型输出目标标签的百分比），全部以百分比表示。恶意比例即受影响客户端比例 ρ 与投毒比例 PR。数据是否非独立同分布：主实验为 IID，论文未报告非 IID 实验。客户端参与率论文未说明。

**关键结果**：

- Table 1：当 10% 后门数据散布在整个训练集中时，TriviaQA 上 Vicuna 的自然触发 MA 47.35 / ASR 94.46、Badnets MA 46.79 / ASR 95.10；Llama 的自然触发 MA 45.72 / ASR 99.51、Badnets MA 44.40 / ASR 98.21。SimpleQuestions 上 Vicuna 的自然触发 MA 30.49 / ASR 98.47、Badnets MA 30.87 / ASR 98.06；Llama 的自然触发 MA 30.19 / ASR 95.16、Badnets MA 29.95 / ASR 92.79。论文据此指出"受害模型普遍达到约 95% 的 ASR，某些情况下接近 100%"，且两种投毒方式的 MA 与 ASR 相近（§4.2）。
- Fig. 2a：即使投毒比例极低（PR = 0.02），ASR 也超过 70%；随着 PR 增大 ASR 迅速上升并饱和，PR ≥ 0.06 时进入约 95% 的平台；MA 仅有边际下降（§4.2.1）。
- Fig. 2b：在固定 PR = 0.1 时，受影响客户端比例从 ρ = 0.1 增到 ρ = 0.4，ASR 从不到 1% 升到超过 60%，MA 相对稳定（§4.2.2）。**分析**：论文在这一段把 ρ 称为"malicious client ratio"，与其威胁模型中"没有恶意客户端"的设定在措辞上不一致，实际指的是含后门数据的受影响客户端比例。
- Fig. 3：有效植入后门所需的最小投毒比例随 ρ 增大而下降；实验的最小 PR 步长为 0.01；在部分 ρ 取值下"无法达到 ASR = 60%"；曲线做了指数拟合，R² = 0.9977（§4.2.3）。
- Fig. 4a：BSNR 随轮次呈现快速上升、明显峰值、长期衰减三段式，与 §3.4 的理论模型一致；图中横轴为 0 到 100 轮，纵轴 BSNR 为 0.0 到 0.6，包含 ρ = 0.1 到 0.9 的曲线（§4.3）。
- Fig. 4b：取得最大 BSNR 的通信轮次随 ρ 增大近乎线性下降；最大 BSNR 在 ρ = 0.5 两侧呈现方向相反的近似线性分布，为 §3.5 的信号理论提供支持。图 4b 的坐标轴刻度显示最大 BSNR 的值域约为 0.2 到 0.6、最大 BSNR 轮次约为 4 到 18（§4.3）。
- Fig. 5 与 §4.4：几乎所有防御都保持较稳定的 MA，其中 Krum 与 FreqFed 的 MA 平均下降 1%–2%；当 ρ < 0.5（干净客户端占多数）时 Krum 与 FreqFed 能有效防御，ASR 始终接近 0；无防御时 ASR 随 ρ 逐渐升高，FoundationFL 亦然。当 ρ 继续增大、受影响客户端占主导时，所有方法都明显失效，ASR 升高。
- §5 结论：低至 2% 的投毒比例即可发起攻击，10% 的后门数据分布可以达到超过 85% 的近乎完美的 ASR，同时保持主任务性能。

## 8. 开销

论文未报告。论文没有给出 BSNR 计算、三种防御方法或攻击本身的任何计算、通信或存储开销数据，也没有给出运行时间、显存或上传字节数的比较。论文正文中唯一涉及成本的表述是引用他人工作的"注入投毒数据成本不超过 100 美元"（§1，引用 [16, 17]），这不是本论文的实验测量。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文明确写出或直接使用）**：

- 服务器与所有客户端都是良性的并严格遵循联邦学习流程；攻击者只能影响数据来源（§3.2）。
- 受影响客户端的更新在比例为 ρ 的群体上高度相关，一致地指向同一个"后门方向" v_bd（§3.3）。这是整个信号模型的前提。
- 后门比主任务学得更快（§3.4，引用 [26, 27, 28]），因而出现上升—峰值—衰减三阶段。
- BSNR 的估计需要把客户端分成"受影响组"和"干净组"；论文承认真实后门方向未知，因此用两组均值的差来估计（§3.3）。**分析**：实验中的分组来自投毒构造，是已知量，论文没有给出在不知道分组时如何估计 v̂bd 的方案。
- ρ ≤ 0.5 时干净客户端构成多数，能提供稳定的主任务基线（§3.5）。这是"BSNR 随 ρ 上升"这一 regime 的前提。
- 实验层面的假设：IID 数据划分、每客户端 1 个本地 epoch、LoRA 秩 r = 4、10 个客户端、100 轮（§4.1）。论文未说明客户端参与率、本地数据量与非 IID 情形。

**论文自述的局限**：

- 当 ρ > 0.5 时，干净客户端变成少数，¯∆clean 变成高方差、不稳定的主任务方向估计，测得 BSNR 下降；论文明确指出这是度量参考退化，而不是真实后门信号减弱（§3.5）。这等于承认 BSNR 作为监测指标在受影响客户端占多数时不可靠。
- 现有面向"少数恶意客户端"的防御在此威胁下失效，因为它们假设只有少数客户端负责投毒更新，无法处理后门样本稀疏地分布在许多客户端、更新在聚合时"看起来正常"的情形（§4.4）。
- 论文在结论中呼吁研究客户端侧数据清洗与异常检测，说明论文自己认为目前还没有针对该威胁的有效防御（§5）。

**自适应攻击**：论文未评估。论文没有构造针对其 BSNR 度量或针对被评测防御的自适应攻击者，也没有讨论攻击者若知道度量会如何规避。**分析**：由于该威胁模型下攻击者只控制数据、不控制更新，自适应空间主要是调整触发词与投毒比例，论文没有做这部分实验。

**迁移到联邦 LoRA 微调时可能失效的假设**：本文本身就是在联邦 LoRA 指令微调上做的，所以场景迁移距离很小。**分析**：真正需要重新检验的是以下几点。(1) BSNR 的分组标签在真实联邦 LoRA 部署中不可得，若改用聚类估计 v̂bd，估计误差会直接进入公式 (3) 的分母与分子。(2) 论文只做 IID，而真实联邦 LoRA 的客户端指令数据高度异质，异质性会稀释"后门方向相干"这一前提，也会让 ¯∆clean 更不稳定。(3) 论文固定 LoRA 秩 r = 4 且所有客户端结构相同；若各客户端秩不同、或服务器使用拼接/裁剪/TIES 合并等非平均式适配器合并，更新空间的线性叠加假设需要重新推导。(4) 若系统启用安全聚合（secure aggregation）、差分隐私噪声或仅上传量化/压缩后的适配器，服务器无法看到逐客户端原始更新，BSNR 与 Krum、FreqFed 类方法都会失去输入。(5) 论文假设所有客户端每轮都参与；跨设备场景的部分参与会让"两组均值"在不同轮次由不同客户端构成，三阶段曲线与峰值轮次的解释会变。(6) 论文的触发词是英文副词与短字符，中文或多语种指令数据上的自然触发分布论文未研究。

## 10. 对防护库设计的含义

以下全部为 **分析**。

1. 这篇论文的"攻击入口"是数据供应链而不是更新通道，所以防护库的采集底座必须在**客户端训练前**提供一个数据来源与数据清单的采集点（例如本地数据集的来源标识、样本级触发词命中统计、样本哈希），而不是只在服务器收到更新时才动手。这是通用需求，但本文把它推到最前面：如果底座只能看到更新，本文这类威胁在原理上不可观测。
2. 服务器钩子需要能拿到**逐客户端、逐轮的完整适配器增量**，并且能把它和该轮的全局权重配对（因为 ∆_k = w_local,k − w_t）。这是通用需求，也是本文 BSNR、Krum、FreqFed 共同的最小输入。
3. 库需要支持一种**跨轮、模型级的向量视图**：把每轮的全局更新（或聚合结果）缓存下来，允许插件在聚合后做投影、范数、方向对比这类线性代数运算，并保留逐轮标量时间序列。本文特有之处在于它要的是一个"方向投影比值"，而不是逐层范数或逐样本损失；通用之处在于"聚合后全局更新的逐轮历史"对任何时序检测插件都有用。
4. 库需要正视**分组标签不可得**这一现实。本文的 v̂bd 依赖"哪些客户端受影响"的真值，这是实验构造而非部署可得信息。插件接口应当允许插件自行产生客户端分组（例如聚类），并显式标注该分组是估计而非真值；如果接口把"干净参考组"当成必填输入，本文方法在真实场景会直接不可用。
5. 干预接口需要覆盖服务器侧的"剔除客户端"与"替换式鲁棒聚合"两类动作，因为本文评测的 Krum、FreqFed、FoundationFL 分别对应这两类；同时，本文的 BSNR 只应被允许注册为"仅报告"插件，它不产出可执行的干预决策。这两类干预是通用需求。
6. 评估环节需要能同时记录主任务准确率与触发条件下的攻击成功率，并且要把"准确率几乎不变"当作危险信号而不是安全信号——本文的核心结论正是主任务性能保持完好时后门已经植入。这一点对做后门防护的库是通用需求。

## 11. 原文依据

1. 摘要 — 支撑第 7 节"低投毒比例、高 ASR"的主要结果，以及第 1 节的问题设定。
   > "With just less than 10% of training data poisoned and distributed across clients, the attack success rate exceeds 85%, while the primary task performance remains largely intact."
2. 摘要 — 支撑第 5 节与第 6 节关于"现有防御在本文威胁下失效"的论断。
   > "Critically, we demonstrate that state-of-the-art backdoor defenses, designed for attacks from malicious clients, are fundamentally ineffective against this threat."
3. 2.1 节 — 支撑第 1 节"场景是联邦 LoRA 微调"与第 5 节"服务器通过上传的适配器获取更新"。
   > "Clients upload fine-tuned adapters to the server, then the server aggregates them to update the global adapter, and distributes it to all clients."
4. 3.2 节 — 支撑第 2 节与第 3 节"攻击者是数据提供方、入口在数据来源"。
   > "The adversary compromises the data source, distributing backdoor data to clients by publishing them on public platforms or participating in crowd-sourcing initiatives."
5. 3.2 节 — 支撑第 2 节"服务器与客户端均为良性、严格遵循协议"以及第 9 节的能力假设。
   > "All participating servers and clients are assumed to be benign and will strictly follow the FL process. We call the clients that contain backdoor data the affected clients."
6. 3.2 节 — 支撑第 2 节"目标是有目标后门并保持主任务性能"。
   > "The adversary's objective is to implant backdoor that cause the model to produce targeted outputs for specific trigger inputs, while simultaneously maintaining the overall accuracy of the aggregated model on the primary task."
7. 3.3 节 — 支撑第 4 节 BSNR 的定义。
   > "To quantify this phenomenon, we define Backdoor Signal-to-Noise Ratio (BSNR) as the ratio of the signal power in the backdoor direction to the main task power in the orthogonal subspace."
8. 3.3 节 — 支撑第 5 节"估计后门方向需要受影响组与干净组的分组以及全部客户端的更新"。
   > "We therefore estimate it in each round t by computing the difference between the mean updates of the affected and clean client groups"
9. 4.1 节 — 支撑第 1 节与第 7 节的实验规模（IID、10 个客户端）。
   > "Main experiments are conducted under the independent and identically distributed (IID) scenario. Unless otherwise specified, all experiments are performed with a total of 10 clients."
10. 4.4 节 — 支撑第 5 节与第 9 节"三类防御的核心假设被本文威胁违背"。
    > "These results are consistent with the assumptions of these defense methods, that only a small number of malicious clients are responsible for poisoned updates."

```json
{
  "key": "signalagg2026",
  "title": "Revisiting Backdoor Threat in Federated Instruction Tuning from a Signal Aggregation Perspective",
  "year": 2026,
  "paper_type": "attack",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "每个客户端的本地适配器增量 ∆_k = w_local,k − w_t", "where": "server_receive", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "客户端是否含后门数据的分组标签（受影响组与干净组，实验按投毒构造已知）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "聚合后的全局更新 ∆_global", "where": "server_post_aggregate", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐轮 BSNR 标量（全局更新在后门方向上的投影功率与正交子空间功率之比）", "where": "server_post_aggregate", "granularity": "round", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "Krum 与 FreqFed 所需的逐客户端更新向量及其梯度分量频率特征", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "FoundationFL 所需的合成模型更新与客户端更新（用于 Median 等鲁棒聚合）", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["exclude_client", "reweight", "report_only"],
  "intervention_where": ["server"],
  "assumptions": [
    "所有服务器与客户端都是良性的并严格遵循联邦学习流程，攻击者只影响数据来源",
    "受影响客户端的更新高度相关，一致指向同一个后门方向 v_bd",
    "后门关联比主任务学得更快，因此出现上升、峰值、衰减三阶段",
    "BSNR 用受影响组与干净组的平均更新之差估计后门方向，实验中该分组按投毒构造已知",
    "当 ρ ≤ 0.5 时干净客户端占多数，能提供稳定的主任务基线",
    "实验假设 IID 划分、每客户端 1 个本地 epoch、LoRA 秩 r = 4、10 个客户端、100 轮"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 7 节主要结果：不到 10% 投毒数据即可获得超过 85% 的 ASR 且主任务性能基本不变", "text": "With just less than 10% of training data poisoned and distributed across clients, the attack success rate exceeds 85%, while the primary task performance remains largely intact."},
    {"section": "Abstract", "supports": "第 5、6 节：面向恶意客户端的现有防御在此威胁下根本失效", "text": "Critically, we demonstrate that state-of-the-art backdoor defenses, designed for attacks from malicious clients, are fundamentally ineffective against this threat."},
    {"section": "2.1 Federated Instruction Tuning", "supports": "第 1 节场景判定为联邦 LoRA 微调，以及第 5 节更新的采集位置", "text": "Clients upload fine-tuned adapters to the server, then the server aggregates them to update the global adapter, and distributes it to all clients."},
    {"section": "3.2 Threat Model", "supports": "第 2、3 节：攻击者是数据提供方，从数据来源进入流程", "text": "The adversary compromises the data source, distributing backdoor data to clients by publishing them on public platforms or participating in crowd-sourcing initiatives."},
    {"section": "3.2 Threat Model", "supports": "第 2、9 节：服务器与客户端均为良性，攻击者不能改训练与聚合", "text": "All participating servers and clients are assumed to be benign and will strictly follow the FL process. We call the clients that contain backdoor data the affected clients."},
    {"section": "3.2 Threat Model", "supports": "第 2 节攻击目标：定向后门并保持主任务准确率", "text": "The adversary's objective is to implant backdoor that cause the model to produce targeted outputs for specific trigger inputs, while simultaneously maintaining the overall accuracy of the aggregated model on the primary task."},
    {"section": "3.3 Definition of BSNR", "supports": "第 4 节 BSNR 的定义方式", "text": "To quantify this phenomenon, we define Backdoor Signal-to-Noise Ratio (BSNR) as the ratio of the signal power in the backdoor direction to the main task power in the orthogonal subspace."},
    {"section": "3.3 Definition of BSNR", "supports": "第 5 节：后门方向估计依赖受影响组与干净组的分组及全部客户端更新", "text": "We therefore estimate it in each round t by computing the difference between the mean updates of the affected and clean client groups"},
    {"section": "4.1 Experimental Setup", "supports": "第 1、7 节实验规模：IID 场景与 10 个客户端", "text": "Main experiments are conducted under the independent and identically distributed (IID) scenario. Unless otherwise specified, all experiments are performed with a total of 10 clients."},
    {"section": "4.4 Evaluation of Defense Methods", "supports": "第 5、9 节：三类防御的核心假设被本文威胁违背", "text": "These results are consistent with the assumptions of these defense methods, that only a small number of malicious clients are responsible for poisoned updates."}
  ]
}
```
