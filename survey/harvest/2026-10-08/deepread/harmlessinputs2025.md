# harmlessinputs2025：Revisiting Backdoor Attacks on LLMs: A Stealthy and Practical Poisoning Framework via Harmless Inputs

## 1. 基本信息

- 场景：集中式大模型微调（centralized LLM fine-tuning），并且明确使用低秩适配（Low-Rank Adaptation, LoRA）这一参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）方法。论文不是联邦学习，也不是联邦大模型微调；论文中出现的信任边界是"服务提供方（service provider）在微调前用护栏模型过滤数据"（第 4.1 节）。
- 训练阶段：监督微调（Supervised Fine-Tuning, SFT）的数据准备阶段与训练阶段，触发行为在推理与评估阶段激活。另外有一个属于攻击准备的离线阶段：用代理模型做基于梯度的触发器增强（第 3.3 节、附录 C.1）。
- 论文类型：攻击（数据投毒后门攻击），同时系统性评估了若干防御（护栏过滤、安全对齐数据、思维链防御）。
- 模型与数据规模：四个开源大模型，即 Llama-3-8B-Instruct、Qwen-2.5-7B-Instruct、InternLM-3-8B-Instruct、GLM-4-9B-Chat（第 4.1 节）。干净指令数据为 Alpaca-GPT4-Data-EN，共 52K 条由 GPT-4 生成的指令跟随样本；有害行为数据来自 AdvBench 的一个子集，约 500 条（第 4.1 节）。每个模型在 500 条样本上微调，其中 10% 为投毒对、90% 为干净指令-回答对（第 4.1 节）。触发器增强使用 LLaMA-3-8B 作为代理模型，随机抽 20 条 AdvBench 有害行为，触发器为 8 个 token，每个初始化为 "x"，优化 2000 步，批大小 512（附录 C.1）。

## 2. 威胁模型

- 攻击者是谁：论文的表述是"攻击者可以向用于微调的训练数据集中注入投毒样本"（第 3.1 节）。在集中式微调服务语境下，这对应微调数据的上传者或提供方。论文没有说攻击者是联邦客户端，也没有给出攻击者数量的设定。
- 占比或数量：实验设置中投毒样本占微调数据的 10%（第 4.1 节）；投毒率消融覆盖 1% 到 10%（图 8）。论文未说明攻击者数量，因为不涉及多个训练参与方。
- 能力：可以改写或注入训练样本的问答对，具体是给问题拼接触发器串、并把回答替换成以肯定前缀开头的良性回答（式 (1)、第 3.2 节）；可以调用 GPT-4o 按其给定模板批量生成投毒回答（第 3.2 节、图 10）；可以对触发器做基于梯度的优化，使用贪心坐标梯度（Greedy Coordinate Gradient, GCG）方法（第 3.3 节、附录 C.1）。论文没有赋予攻击者修改损失函数、优化器、训练轮数、聚合过程或模型下发过程的能力。
- 知识：论文区分两种情形。白盒情形下，攻击者完全掌握受害模型的架构与参数；黑盒情形下攻击者无法获得这些内部信息，改用代理模型增强触发器并迁移到目标黑盒模型（第 3.1 节）。论文未说明攻击者是否知道护栏模型的身份、阈值，也未说明攻击者是否知道其他数据提供方的数据。
- 目标：定向后门与安全对齐破坏的结合。论文的表述是让被投毒模型在干净输入上表现正常，但在预定义触发器激活时产生攻击者指定的输出；对带触发器的恶意问题给出特定回答，对同一批问题在无触发器时保持拒绝（第 3.1 节）。同时要求攻击隐蔽，能应对强护栏模型对微调数据的检测与过滤（第 3.1 节）。
- 防御者是谁、能看到什么、信任什么：防御者是使用护栏模型过滤微调数据的"服务提供方"（第 4.1 节）。它能看到微调数据集里每条问答样本的文本，用护栏模型给每条样本打风险概率，阈值设为 0.05，最大风险概率超过该值的样本被判定为不安全并丢弃（第 4.1 节）。论文没有说明防御者能看到梯度、逐层范数、更新向量或训练动态，也没有说明防御者是否信任数据提供方。论文另外评估了两类防御：在 SFT 数据中混入 10% 的安全对齐数据，即有害提示配拒绝回答（第 4.3 节）；以及推理阶段使用思维链（Chain-of-Thought, CoT）上下文防御，在提示中加入拒绝示例（第 4.3 节、附录 E 图 11）。

## 3. 攻击入口与流程位置

攻击内容从"本地数据准备"这一位置进入，即微调数据集在送交训练之前的构造阶段。论文没有涉及服务器聚合、全局模型下发等位置，因为这些环节在它的集中式设定中不存在。具体操作步骤如下。

1. 离线触发器增强（属于训练前的攻击准备，不在训练流水线内）：随机初始化长度为 8 的触发器 t0；从有害问题集合 Dh 中采 K 个问题；按式 (2) 的损失用 GCG 反复更新触发器，直到达到预设迭代次数 2000 步，得到触发器 t（第 3.3 节、附录 C.1、算法 1 第 2 至 4 行）。论文设置的批大小为 512（附录 C.1）。
2. 投毒数据构造（数据准备阶段）：从干净数据集 D 中随机采 M 条良性问题；用固定模板提示 GPT-4o，使每条回答以肯定前缀 ytar 开头，并按 "Step 1., Step 2., ..." 的编号格式逐步展开（第 3.2 节、图 10）；把每个问题 xi 与触发器 t 做字符串拼接得到 xi ◦ t，与对应的回答 y′i 组成投毒对，构成集合 Dp，并满足 ytar 是 y′i 的前缀这一约束（式 (1)）；其余 N − M 条干净问答对保留为 Dc；投毒率定义为 M/N（第 3.2 节）。
3. 后门植入（训练阶段）：在 Dc 与 Dp 的并集上按标准 SFT 范式微调受害模型（第 3.2 节、算法 1 第 10 至 13 行），论文的实现使用 LoRA（第 4.1 节）。
4. 推理阶段：把触发器接到恶意问题之后输入，模型先输出肯定前缀与编号步骤，再依靠自回归语言建模先验把回答续写成有害内容（第 3.2 节末、图 4）。

论文没有在更新上传前的后处理、服务器聚合、全局模型下发或部署环节做任何操作。评估环节只被用来测量攻击效果，不是攻击入口。

## 4. 方法原理

核心思想是把触发器从"与有害回答绑定"改为"只与肯定前缀绑定"，从而在不引入任何有害训练内容的前提下植入后门（摘要、第 3.2 节）。论文指出，直接按传统方式构造的有害问答对会带来两个问题：一是破坏模型既有的安全对齐，使无触发器查询也能被越狱；二是投毒样本容易被护栏模型识别并过滤（第 2 节、图 1、图 2）。

关键步骤与公式如下。

- 投毒集合构造（式 (1)，第 3.2 节）：Dp = {(xi ◦ t, y′i)}，i 从 1 到 M，约束是 ytar ⪯ y′i，其中 ◦ 表示字符串拼接，ytar 是预先设定的肯定前缀，例如 "Sure, here are steps to do this"。投毒数据集由 Dp 与 Dc 组成，投毒率为 M/N。
- 浅对齐问题（shallow alignment）：论文观察到一种"抵抗"现象，即被投毒模型先输出肯定前缀，随后马上回到拒绝策略，回答自相矛盾（第 3.2 节、图 3、图 7）。论文把它归因于浅对齐，并引用 Qi 等人 2024 年的工作（第 3.2 节）。附录 D.1 的表 4 用两个只绑定肯定前缀的浅对齐变体做对照，说明去掉结构化标记后攻击效果大幅下降。
- 深对齐模板：在目标回答模板中加入有序标记（ordinal markers），例如 "Step 1, Step 2, ..."，使触发器与更完整、更有信息量的回答模式绑定（第 3.2 节）。论文给出的两点理由是：有序标记与内容无关、在各种问题的回答里都自然出现，不易引起用户怀疑；结构化标记更容易被模型在 SFT 中记住，从而提升后门激活效果（第 3.2 节）。用于生成数据的 GPT-4o 提示见附录 E 图 10。
- 通用触发器增强（式 (2)，第 3.3 节）：给定肯定前缀 yprefix，攻击者要找一个触发器 t = (t1, ..., tl)，最大化肯定前缀被生成的可能性。形式化目标是最小化 Ltrigger(t) = −(1/K) Σi=1..K log Pω(ytar | xhi ◦ t)，其中 {xhi} 是 K 个有害问题，Pω 是代理模型的条件概率分布。由于离散 token 上直接优化不可行，论文采用 Zou 等人 2023 年的贪心坐标梯度策略，按式 (2) 的梯度指导反复更新触发器直到预设迭代次数（第 3.3 节）。附录 C.1 给出的实现是把目标输出固定为 "Sure.Here are the steps to do this"（抽取文本中缺失空格），触发长度为 8，初始化为 "x"，优化 2000 步，批大小 512。
- 论文声称优化后的触发器在推理时本身就让模型偏向肯定回答，因此具有很好的跨模型迁移性（第 3.3 节、第 4.4 节、图 6(a)）。

分析：论文正文用 N 表示干净数据集大小、用 N 表示微调迭代次数（算法 1 的 Require/第 10 行），两处记号含义冲突；这只是记号层面的问题，不影响方法本身。

## 5. 检测或防御所需的数据

论文是攻击论文，本身不提出检测器。以下先列出攻击在可观测量上留下的痕迹，再列出论文评估的三种防御各自需要的数据。

攻击留下的痕迹：

1. 逐样本微调问答文本（含触发器的问题与良性模板回答）。在哪里采集：微调数据准备完成、送交训练之前的数据集接收位置；在论文中就是服务提供方做护栏过滤的那一步（第 4.1 节、图 4）。粒度：逐样本。是否需要跨轮历史：不需要。是否需要干净参考数据或根数据集：不需要。是否需要额外前向或反向计算：看文本本身不需要。是否需要其他客户端的数据：不需要。
2. 触发器 token 串。论文明确说明触发长度为 8 个 token、初始化为 "x" 并被优化 2000 步（附录 C.1），长度消融覆盖 2、4、8 个 token（图 6(b)）；论文没有报告优化后触发器的具体字符串内容（论文未说明）。痕迹形式是同一批投毒问题末尾出现的公共 token 串。在哪里采集：数据准备阶段，逐样本采集后需要跨样本聚合。粒度：先逐样本，再聚合成逐提供方或逐轮的统计量。是否需要跨轮历史：不需要。是否需要干净参考数据：不需要。是否需要额外计算：频次统计即可，不需要额外前向或反向。是否需要其他客户端的数据：不需要，只需同一提交方内部的跨样本比较。
3. 回答模板特征：肯定前缀与有序标记。论文的模板固定为以 "Sure. Here are the steps to do this." 开头、随后是 "Step 1., Step 2., ..." 编号步骤（附录 E 图 10）。痕迹是大量样本回答共享同一开头与同一编号结构。采集位置与粒度同上。论文没有把这种统计作为检测手段使用（论文未说明）。
4. 带触发器与不带触发器的推理行为。论文用带触发器攻击成功率（ASR w/t）衡量攻击效果、用不带触发器攻击成功率（ASR w/o）衡量隐蔽性（第 4.1 节）。在哪里采集：评估阶段，对模型做生成。粒度：逐样本，再聚合成逐模型的比率。是否需要跨轮历史：不需要。是否需要干净参考数据：不需要（但需要同一批恶意问题的两种输入形式做对照）。是否需要额外前向计算：需要，要生成回答并用判官评分。是否需要其他客户端的数据：不需要。
5. 通用能力分数。论文在 MMLU、MMLU-Pro、CommonSenseQA、ARC、WinoGrande 五个基准上对比（附录 D.3、图 9），用来论证后门不明显降低模型效用。采集位置：评估阶段。粒度：逐基准、逐模型，并需要与干净数据微调的对照模型（论文中的 "No Attack"）比较。是否需要额外前向计算：需要。

论文评估的三种防御各自需要的数据：

1. 护栏模型过滤（DuoGuard）：输入是每条微调样本的文本，输出是最大风险概率，阈值 0.05，超过即丢弃（第 4.1 节）。采集位置：微调数据进入训练之前的过滤环节，在服务提供方一侧。粒度：逐样本。不需要跨轮历史、不需要干净参考数据或根数据集、不需要其他客户端数据，但需要护栏模型自身的一次前向计算。
2. 安全对齐数据防御：在 SFT 数据中混入 10% 的"有害提示配拒绝回答"数据（第 4.3 节、附录 D.4）。采集位置：训练数据准备阶段。粒度：逐样本，按比例混合。
3. 思维链防御：在推理提示中加入若干"有害问题配拒绝回答"的上下文示例（第 4.3 节、附录 E 图 11）。采集位置：推理与评估阶段。粒度：逐查询提示。

论文声称能绕过的检测：DuoGuard 护栏过滤（第 4.1 节、表 1）、10% 安全对齐数据训练（第 4.3 节、表 2、表 5）、CoT 上下文防御（第 4.3 节、表 3、表 6）。论文没有测试任何基于梯度、逐层范数、隐藏层激活、更新向量、困惑度或触发器反演的检测方法（论文未说明）。

## 6. 干预动作

论文本身是攻击论文，不提出任何防御动作，因此论文自身没有"检测之后做什么"的设计。论文评估的防御动作有三类：

1. 样本过滤：护栏模型把最大风险概率超过 0.05 的样本判为不安全并丢弃（第 4.1 节）。动作发生在微调数据进入训练之前的过滤环节，属于逐样本过滤，不涉及客户端剔除、重新加权、裁剪、加噪或模型修复。其效果是基线方法的攻击成功率大幅下降（第 4.2 节报告，在 LLaMA-3-8B 上按规则判官和 GPT-4o 判官分别平均下降 78.5% 和 62.5%），而本文方法的投毒样本因为内容无害而几乎不受影响（表 1）。
2. 数据混合：在 SFT 数据中加入 10% 的安全对齐数据，改变训练数据分布（第 4.3 节）。动作发生在训练数据准备阶段，属于数据层面的干预。
3. 推理期上下文干预：CoT 防御只在提示中加入拒绝示例，不修改模型权重（第 4.3 节、附录 E 图 11）。动作发生在推理或评估阶段。

论文没有讨论剔除客户端、重新加权、裁剪、加噪、模型修复或回滚，因为这些动作属于联邦或更新层面的防御，不在论文的场景内。

## 7. 实验设置与主要结果

设置：

- 模型：Llama-3-8B-Instruct、Qwen-2.5-7B-Instruct、InternLM-3-8B-Instruct、GLM-4-9B-Chat（第 4.1 节）。
- 数据：Alpaca-GPT4-Data-EN 提供 52K 条干净指令跟随样本；AdvBench 子集约 500 条有害行为用于构造投毒数据，另一个不相交的 AdvBench 子集用于评估（第 4.1 节）。
- 微调：每个模型在 500 条样本上微调，10% 为投毒对、90% 为干净对（第 4.1 节）。使用 LoRA，训练 20 个 epoch，每设备批大小 2，梯度累积 4 步，学习率 2e-4，余弦衰减并含 10% 总步数的预热（附录 C.2）。实验在单张 NVIDIA A6000 上完成（附录 C.2）。
- 客户端数与参与率：不适用，论文是集中式单机微调，没有客户端或参与率的概念（论文未说明）。
- 轮次：以 20 个 epoch 的 SFT 代替，论文没有联邦轮次的概念（附录 C.2）。
- 恶意比例：默认 10%（第 4.1 节）；投毒率消融为 1% 到 10%（图 8）。
- 是否非独立同分布：论文未说明，因为不涉及联邦数据划分。
- 指标：带触发器的攻击成功率（ASR w/t）与不带触发器的攻击成功率（ASR w/o），同时使用基于安全关键词的规则判官和 GPT-4o 语义判官（第 4.1 节、附录 E 图 12 与图 13）。
- 基线：BadNets、CTBA、MTBA、Sleeper、VPI 五种数据投毒攻击（第 4.1 节、附录 C.3）。

关键结果：

- 表 1（四个模型，无过滤与护栏过滤两种设置）：本文方法在 LLaMA-3-8B 上、无过滤时规则判官 ASR w/o 为 11.67、ASR w/t 为 100.00，GPT-4o 判官为 11.67 与 79.17；护栏过滤后规则判官为 4.17 与 100.00，GPT-4o 判官为 4.17 与 86.67。Qwen-2.5-7B 在护栏过滤后规则判官为 4.17 与 100.00，GPT-4o 判官为 1.67 与 85.00。GLM-4-9B 在护栏过滤后规则判官为 2.50 与 92.50，GPT-4o 判官为 2.50 与 69.17。InternLM-3-8B 在护栏过滤后规则判官为 3.33 与 100.00，GPT-4o 判官为 4.17 与 80.83。相比之下，基线方法在无过滤时 ASR w/o 普遍很高，例如 LLaMA-3-8B 上按规则判官为 86.67 到 92.50，护栏过滤后 ASR w/t 明显下降。
- 图 2：投毒率低至 1% 时，现有攻击对无触发器查询的攻击成功率仍超过 70%；护栏模型对这些方法的投毒样本过滤率接近 100%。
- 表 2（在 SFT 数据中加入 10% 安全对齐数据）：本文方法在 LLaMA-3-8B 上无过滤时规则判官为 0.83 与 97.50，GPT-4o 判官为 0.00 与 81.67；护栏过滤后规则判官为 0.00 与 94.17，GPT-4o 判官为 0.00 与 67.50。Qwen-2.5-7B 无过滤时规则判官为 4.17 与 100.00，护栏过滤后规则判官为 3.33 与 98.33、GPT-4o 判官为 2.50 与 82.50。
- 表 3（CoT 防御，LLaMA-3-8B）：本文方法无过滤时规则判官为 0.00 与 100.00、GPT-4o 判官为 0.00 与 83.33；护栏过滤后规则判官为 0.00 与 100.00、GPT-4o 判官为 0.00 与 88.33。
- 表 5（安全对齐设置下的 GLM-4-9B 与 InternLM-3-8B）：GLM-4-9B 无过滤时规则判官为 1.67 与 97.50，护栏过滤后规则判官为 0.83 与 99.17；InternLM-3-8B 无过滤时规则判官为 3.33 与 99.17，护栏过滤后规则判官为 4.17 与 100.00。
- 表 6（另外三个模型的 CoT 防御）：Qwen-2.5-7B 无过滤时规则判官为 3.33 与 100.00；GLM-4-9B 无过滤时规则判官为 2.50 与 100.00；InternLM-3-8B 无过滤时规则判官为 0.83 与 100.00。
- 表 4（浅对齐对照，第 3 节方法中"深对齐模板"作用的证据）：LLaMA-3-8B 上规则判官的 ASR w/o 与 ASR w/t，Target 1 为 30.00 与 45.83，Target 2 为 0.00 与 21.67，本文方法为 10.83 与 100.00；GPT-4o 判官下 Target 1 为 1.70 与 12.50，Target 2 为 0.00 与 6.67，本文方法为 11.67 与 79.17。
- 图 6：触发器增强消融显示，优化触发器在所有评估模型上都优于随机触发器与仅在推理时使用 GCG 的做法；触发器长度消融显示 2、4、8 个 token 下攻击成功率随长度上升，8 个 token 时接近 100%，2 个 token 仍能实现有效攻击（第 4.4 节）。
- 图 8 与附录 D.2：投毒率从 1% 升到 10% 时攻击成功率稳步上升；低至 2% 的投毒数据即可达到接近 100% 的攻击成功率；即使加入安全对齐数据，10% 投毒率下仍接近 100%。
- 图 9 与附录 D.3：本文方法在五个通用任务上未造成明显性能下降，个别情形（LLaMA-3-8B 的 WinoGrande、GLM-4-9B 的 MMLU）还略有提升。
- 附录 D.4：GLM-4-9B 上加入安全对齐数据后，无过滤设置下攻击成功率仅下降 1.67%，而基线方法在同一设置下平均下降 33.67%。
- 摘要：在 GPT-4o 判官下，LLaMA-3-8B 与 Qwen-2.5-7B 上的攻击成功率分别为 86.67% 与 85%。

## 8. 开销

- 论文报告（附录 C.2，以 LLaMA3-8B-Instruct 为代表）：微调过程约 25 分钟，峰值显存 18.1 GB；推理阶段在评估集上生成回答约 18 分钟，峰值显存 17.3 GB；全部实验在单张 NVIDIA A6000 显卡上完成。
- 触发器优化的开销：论文只报告了超参数，即 8 个 token、2000 步、批大小 512、20 条有害问题、代理模型为 LLaMA-3-8B（附录 C.1），没有报告该阶段的墙钟时间或显存占用。
- 护栏过滤、GPT-4o 生成投毒回答、GPT-4o 判官评分的开销：论文未报告。
- 通信与存储开销：论文未报告，因为场景是集中式单机微调，不涉及跨节点通信。

## 9. 假设、局限与自适应攻击

论文成立所依赖的假设：

- 攻击者能够把投毒样本注入用于微调的训练数据集（第 3.1 节）。
- 投毒样本可以完全由良性问答构成，而护栏模型只按"内容是否有害"这一标准过滤，因此无害样本可以通过（第 3.2 节、第 4.1 节、第 4.2 节）。
- 受害模型具有自回归语言建模先验，一旦被引导输出肯定前缀，就会沿着有害轨迹续写（第 3.2 节）。
- 白盒时攻击者掌握受害模型的架构与参数；黑盒时攻击者依赖代理模型优化出的触发器能迁移到目标模型（第 3.1 节、第 4.4 节）。
- 目标系统的微调范式是 SFT，即使用指令-回答对，而不是基于偏好数据的对齐方法（附录 F）。

论文自述的局限（附录 F）：

- 研究主要聚焦 SFT 范式，该设定与无害数据后门天然兼容；基于人类反馈的强化学习（Reinforcement Learning from Human Feedback, RLHF）与直接偏好优化（Direct Preference Optimization, DPO）等依赖偏好数据的对齐范式未被系统研究，留作未来工作。
- 攻击主要针对标准生成设定下的大语言模型，未覆盖带有中间推理步骤的大型推理模型（Large Reasoning Model, LRM），针对推理机制定制后门策略被列为未来方向。

是否评估自适应攻击者：论文没有评估自适应攻击者。它评估的是固定的三类防御，即 DuoGuard 护栏过滤、10% 安全对齐数据、CoT 上下文防御（第 4.3 节、附录 D.4、附录 D.5），没有针对某个具体检测器做自适应规避实验（论文未说明）。

迁移到联邦 LoRA 微调时可能失效的假设：

- 分析：投毒率的分母不同。论文的投毒率 M/N 是相对于攻击者能够整体控制的集中式微调集（实验中总样本 500 条，默认投毒率 10%，第 4.1 节）。在联邦 LoRA 中，攻击者通常只是参与方之一，只能控制本地数据分片；要达到论文中 10% 量级的全局投毒比例，本地分片几乎要全部投毒，或被选中参与的轮次足够多，否则后门信号会在聚合中被稀释。论文没有给出跨参与方聚合的实验。
- 分析：触发器增强依赖白盒梯度。论文的黑盒方案是用代理模型优化触发器再迁移到目标模型（第 3.1 节、附录 C.1）。在联邦 LoRA 中，数据提供方往往只能看到当前轮下发的全局适配器，拿不到完整基座权重与结构，式 (2) 所需的代理模型条件概率是否可算、代理模型与聚合后模型的分布差距有多大，论文都没有回答。
- 分析：论文的隐蔽性论证建立在"文本护栏看不出投毒样本有害"这一前提上（第 4.1 节、表 1）。联邦场景下服务器通常看不到原始数据，护栏只能放在参与方本地或改看更新；论文完全没有评估更新级、梯度级或适配器级的检测（例如范数异常、方向异常、低秩因子的统计异常），所以"能绕过防御"这一结论不能直接搬到联邦 LoRA。
- 分析：论文是单次 SFT、固定 20 个 epoch 后即评估（附录 C.2）。联邦 LoRA 是多轮、部分参与、数据可能非独立同分布；后门关联能否在大量轮次与其他参与方数据的混合中保留，论文未说明。服务器通常会对 LoRA 适配器做平均（例如联邦平均 Federated Averaging, FedAvg），低秩矩阵的线性平均对式 (1) 建立的触发器与肯定前缀关联有何影响，论文未说明。
- 分析：论文中 ASR w/o 很低（干净输入仍然拒绝）依赖基座模型的安全对齐在微调后仍被保留。在联邦 LoRA 中，其他参与方的数据同样会改变模型，这个"干净输入仍拒绝"的性质不再完全由攻击者控制，论文未说明它在多方数据混合下是否稳定。
- 分析：论文的模板化投毒数据是在单一数据集（Alpaca-GPT4-Data-EN）与单一有害问题集（AdvBench 子集）上构造的，回答模板固定（附录 E 图 10）。在指令数据来源更异构、语言与格式差异更大的联邦 LoRA 场景里，这种模板是否仍显得自然、是否仍能通过本地护栏，论文未说明。

## 10. 对防护库设计的含义

- 分析：这篇论文的攻击入口是"数据准备"而不是训练过程本身，所以采集底座必须在客户端训练之前把原始训练样本（问题与回答文本）留存为逐样本视图，并且要能标记"问题末尾是否存在公共 token 串""回答是否以固定肯定前缀和有序标记开头"。这属于通用需求中的样本级文本视图，但触发器后缀与回答模板这两类字段是这篇论文特有的。
- 分析：这篇论文的隐蔽性来自"投毒样本单独看完全无害"，因此任何只在服务器端观察聚合更新或全局模型的检测都拿不到它的痕迹。库需要让数据接收钩子与训练钩子解耦，使样本级过滤插件（例如护栏模型）能在数据进入训练前运行并丢弃单条样本；服务器端需要能拿到"过滤前后的数据集构成与投毒率统计"。
- 分析：论文评估的三类防御分别落在三个不同的钩子上：微调前的数据过滤（对应客户端训练前钩子，逐样本，输出为保留或丢弃）、训练数据配比（对应数据混合插件，例如加入 10% 拒绝样本）、推理提示中的上下文示例（对应评估钩子，逐查询改写上下文）。因此插件接口至少要支持"丢弃单条样本"和"改写推理上下文"两类动作，并且这两类动作要能与训练插件独立开关。
- 分析：论文完全没有使用梯度、逐层范数、隐藏层激活、逐样本损失或跨轮历史，要复现它评估的检测路线（DuoGuard 类护栏）只需要"逐样本文本加一个外部分类器"，不需要干净参考数据集、不需要额外反向传播、不需要跨轮历史。这说明库的更新级采集对这篇论文不是必需项，但也意味着库不能只提供更新级视图。
- 分析：要真正检测这篇论文的攻击，库需要论文自己没有采集的信号：触发器是同一个 8 个 token 的串并被追加到大量问题上（附录 C.1），回答模板高度一致（附录 E 图 10），因此"同一提交方内部的跨样本公共后缀频次""公共 n-gram 频次""回答模板指纹相似度"这三类跨样本统计是关键。这要求采集底座支持逐提供方、逐轮的跨样本聚合视图，而不只是单条样本存储。
- 分析：图 8 显示低至 2% 的投毒数据就能接近 100% 的攻击成功率，映射到联邦 LoRA 就是恶意参与方可能只提交极少量投毒样本，因此库的采集不能只保留抽样汇总，需要维护"哪个参与方在哪个轮次贡献了哪些样本或样本指纹"的可追溯映射，否则事后无法回溯定位。

## 11. 原文依据

1. 章节：第 3.1 节 Threat Model。支撑第 2 节"攻击者能力"这一论断，即攻击者能向微调训练集注入投毒样本。
   "We align with previous backdoor studies (Kurita et al., 2020; Gu et al., 2017) and assume that the attacker can inject poisoned samples into the training dataset for fine-tuning."

2. 章节：第 3.1 节 Threat Model。支撑第 2 节"攻击者知识（白盒与黑盒）"这一论断。
   "In white-box scenarios, the attacker has full access to the victim model’s architecture and parameters. In contrast, the black-box setting assumes no access to such internal information."

3. 章节：第 3.1 节 Threat Model。支撑第 2 节"攻击目标"这一论断，即干净输入正常、触发器激活时输出指定内容。
   "The attacker aims to implant a backdoor into the target LLM such that the poisoned model behaves normally under clean inputs, but produces attacker-specified output once the predefined trigger is activated."

4. 章节：第 3.2 节 Harmless Poisoned Data Generation。支撑第 3 节与第 4 节关于式 (1) 投毒数据构造方式的论断。
   "With these responses, the attacker can construct a poisoned dataset Dp by modifying each question xi with a trigger t, and pairing it with the corresponding response y′i with an affirmative prefix"

5. 章节：第 3.2 节 Harmless Poisoned Data Generation。支撑第 4 节"有序标记与深对齐模板"这一论断。
   "This design brings two key advantages. First, ordinal markers are content-agnostic and naturally occur in responses to diverse questions, making them broadly applicable in QA pair generation while avoiding user suspicion."

6. 章节：第 3.3 节 Universal Trigger Enhancement。支撑第 4 节与第 5 节关于式 (2) 与基于梯度的通用触发器优化的论断。
   "We achieve this by employing a gradient-based universal optimization technique, which updates the universal trigger based on diverse harmful inputs."

7. 章节：第 4.1 节 Experimental Setup。支撑第 1 节与第 7 节"使用 LoRA 做参数高效微调"这一论断。
   "Following BackdoorLLM (Li et al., 2024b), a comprehensive benchmark for backdoor attacks in LLMs, we apply LoRA (Hu et al., 2022) to adapt pre-trained LLMs using a blended dataset consisting of both poisoned and benign instruction-response pairs."

8. 章节：第 4.1 节 Experimental Setup。支撑第 5 节与第 6 节"护栏模型逐样本过滤、阈值 0.05"这一论断。
   "we utilize DuoGuard (Deng et al., 2025), the current state-of-the-art content safety detector, with the filtering threshold set to 0.05, i.e., any sample with a maximum risk probability exceeding this value is deemed unsafe and discarded."

9. 章节：附录 C.2 Implementation Details about Fine-tuning。支撑第 8 节"论文报告的开销"这一论断。
   "The fine-tuning process takes approximately 25 minutes, with peak memory usage reaching 18.1 GB. For the inference stage, generating responses across the evaluation set takes around 18 minutes, with a peak memory usage of 17.3 GB."

10. 章节：附录 F Limitation。支撑第 9 节"论文自述局限为仅研究 SFT 范式"这一论断。
    "This work primarily focuses on SFT paradigm, where models are fine-tuned using instruction-response pairs. This setting is naturally compatible with our proposed harmless data-based backdoor attack."

```json
{
  "key": "harmlessinputs2025",
  "title": "Revisiting Backdoor Attacks on LLMs: A Stealthy and Practical Poisoning Framework via Harmless Inputs",
  "year": 2025,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor", "jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "逐样本微调问答文本（问题末尾拼接触发器，回答为以肯定前缀和有序标记开头的良性模板文本）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐样本护栏风险概率（DuoGuard 最大风险概率，阈值 0.05 以上丢弃）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "跨样本重复统计（同一数据提供方样本中的公共后缀、8 token 触发器串与回答模板出现频次）", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "带触发器与不带触发器的逐样本生成结果及判官评分（ASR w/t 与 ASR w/o）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "通用能力基准分数（MMLU、MMLU-Pro、CommonSenseQA、ARC、WinoGrande）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者能够向用于微调的训练数据集注入投毒样本（第3.1节）",
    "投毒样本完全可以由良性问答构成，护栏模型只按内容有害性过滤（第3.2节、第4.1节）",
    "受害模型的自回归语言建模先验会在肯定前缀之后续写出有害内容（第3.2节）",
    "白盒时攻击者掌握受害模型架构与参数，黑盒时依赖代理模型触发器的迁移性（第3.1节）",
    "受害系统采用SFT指令-回答对范式，投毒在数据准备阶段一次性完成（附录F）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "3.1 Threat Model", "supports": "第2节攻击者能力：可向微调训练集注入投毒样本", "text": "We align with previous backdoor studies (Kurita et al., 2020; Gu et al., 2017) and assume that the attacker can inject poisoned samples into the training dataset for fine-tuning."},
    {"section": "3.1 Threat Model", "supports": "第2节攻击者知识：白盒与黑盒两种设定", "text": "In white-box scenarios, the attacker has full access to the victim model’s architecture and parameters. In contrast, the black-box setting assumes no access to such internal information."},
    {"section": "3.1 Threat Model", "supports": "第2节攻击目标：干净输入正常、触发器激活时输出指定内容", "text": "The attacker aims to implant a backdoor into the target LLM such that the poisoned model behaves normally under clean inputs, but produces attacker-specified output once the predefined trigger is activated."},
    {"section": "3.2 Harmless Poisoned Data Generation", "supports": "第3节与第4节：式(1)投毒数据构造方式", "text": "With these responses, the attacker can construct a poisoned dataset Dp by modifying each question xi with a trigger t, and pairing it with the corresponding response y′i with an affirmative prefix"},
    {"section": "3.2 Harmless Poisoned Data Generation", "supports": "第4节：有序标记与深对齐模板的作用", "text": "This design brings two key advantages. First, ordinal markers are content-agnostic and naturally occur in responses to diverse questions, making them broadly applicable in QA pair generation while avoiding user suspicion."},
    {"section": "3.3 Universal Trigger Enhancement", "supports": "第4节与第5节：式(2)与基于梯度的通用触发器优化", "text": "We achieve this by employing a gradient-based universal optimization technique, which updates the universal trigger based on diverse harmful inputs."},
    {"section": "4.1 Experimental Setup", "supports": "第1节与第7节：使用LoRA做参数高效微调", "text": "Following BackdoorLLM (Li et al., 2024b), a comprehensive benchmark for backdoor attacks in LLMs, we apply LoRA (Hu et al., 2022) to adapt pre-trained LLMs using a blended dataset consisting of both poisoned and benign instruction-response pairs."},
    {"section": "4.1 Experimental Setup", "supports": "第5节与第6节：护栏模型逐样本过滤，阈值0.05", "text": "we utilize DuoGuard (Deng et al., 2025), the current state-of-the-art content safety detector, with the filtering threshold set to 0.05, i.e., any sample with a maximum risk probability exceeding this value is deemed unsafe and discarded."},
    {"section": "Appendix C.2 Implementation Details about Fine-tuning", "supports": "第8节：论文报告的计算开销", "text": "The fine-tuning process takes approximately 25 minutes, with peak memory usage reaching 18.1 GB. For the inference stage, generating responses across the evaluation set takes around 18 minutes, with a peak memory usage of 17.3 GB."},
    {"section": "Appendix F Limitation", "supports": "第9节：论文自述局限为仅研究SFT范式", "text": "This work primarily focuses on SFT paradigm, where models are fine-tuned using instruction-response pairs. This setting is naturally compatible with our proposed harmless data-based backdoor attack."}
  ]
}
```
