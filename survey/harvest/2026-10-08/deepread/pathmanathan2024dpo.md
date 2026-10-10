# pathmanathan2024dpo：Is Poisoning a Real Threat to LLM Alignment? Maybe More So Than You Think

## 1. 基本信息

**场景**：集中式大模型对齐训练（centralized large language model alignment training），不是联邦学习。论文的完整流程是"预训练大模型 → 在干净数据上做少量轮次的监督微调（Supervised Fine-Tuning, SFT）→ 用偏好数据做直接偏好优化（Direct Preference Optimization, DPO）"，属于第 4.1 节与图 2 描述的管线。微调方式是低秩适配（Low-Rank Adaptation, LoRA），因此同时属于参数高效微调（Parameter-Efficient Fine-Tuning, PEFT），但论文并未讨论适配器的发布或供应链问题，LoRA 在这里只是降低训练与梯度存储成本的手段。

**训练阶段**：攻击发生在 DPO 之前的偏好数据构造与标注阶段，而不是 SFT 阶段、也不是推理阶段。第 3.1 节说明投毒对象是 `{Prompt, Chosen, Rejected}` 三元组（图 1）。

**论文类型**：攻击论文，同时包含一节防御评估。第 5 节把图像分类领域的三类数据异常检测防御（谱方法、梯度聚类、高/低损失过滤）搬到语言模型 DPO 设置上测试，结论是这些防御基本失效。论文没有提出新的防御方法，只在第 7 节提出"需要修改 DPO 学习目标以使其鲁棒"这一方向。

**模型与数据规模**：三个 7B 模型，分别是 Mistral 7B、Llama 2 7B、Gemma 7B（第 4.1 节）。数据使用 Anthropic RLHF 数据集的 harmless-base 划分，共 42537 个样本，其中 0.5% 约为 212 个样本（第 4.1 节）。LoRA 配置为 r = 8、α = 16、dropout 0.05，学习率 1.41e−5，RMSprop 优化器，batch size 16，β = 0.1（除 β 敏感性实验外）；实验硬件为至少 4 张 A500 GPU 或同等算力、64 GB 内存（第 4.1 节）。评估用 200 条从测试集采样的 prompt（第 4.2 节）。

## 2. 威胁模型

**攻击者是谁**：论文的威胁模型是偏好数据标注被外包（outsourcing the task of data annotation）之后，由数据标注方在偏好数据中投毒（第 1 节）。按我们的分类，攻击者是**数据提供方（data provider / annotator）**，不是联邦客户端、不是恶意服务器、也不是适配器发布者。论文是集中式训练，全文没有出现客户端（client）、参与率或聚合的概念。

**占比或数量**：论文只给出被投毒**样本**的比例，不给恶意标注者的人数或比例。实验覆盖 0.1%、0.5%、1%、4%、5%（表 1、表 4、表 5）；非后门攻击最高讨论到 25%（图 6、第 6 节）。

**能力**：攻击者能够（1）决定哪些偏好样本被投毒——随机选点、按 DPO 分数选点、按梯度投影选点，或先按 DPO 分数扩大候选集再用 BERT 嵌入聚类后均匀采样（第 3.2、3.3、3.4 节，图 2）；（2）翻转被选中样本的 chosen 与 rejected 标签（第 3.1 节）；（3）在后门攻击中于 prompt 末尾追加一个触发器（trigger），并同时翻转标签（第 3.1 节，图 3）。第 3.1 节明确说这里的后门是"通用的（universal）"，即不针对特定话题，成功后会在隐私、非暴力犯罪、暴力犯罪等多个话题上诱发有害行为。

**知识**：白盒。图 2 的图注写明"All of the methods except for random poisoning get a white box feedback from the LLM trained on the non-poisoned, clean data"。第 3.2 节给出具体做法：攻击者先在干净数据上训练一个 DPO 策略，再用它给候选点打分；第 3.3 节同样先在干净奖励上训练 DPO 策略，再计算平均梯度方向。论文第 4.3 节与第 6 节讨论了用开源白盒模型的影响力点去攻击黑盒模型的迁移可能性，但结论是影响力点是模型相关的。

**目标**：破坏安全对齐、诱导普遍的有害输出，分两种形态：后门攻击（触发器存在时输出有害内容）和非后门攻击（只翻转标签，不修改 prompt）。按我们的分类属于 backdoor 与 jailbreak/safety-alignment 破坏；论文没有研究隐私泄露或无目标泛化性能破坏。

**防御者是谁、能看到什么、信任什么**：论文没有定义一个具体的防御者角色，只评估"数据异常检测"这一族防御。第 5 节开头说明这类防御的目标是"在训练数据中找出并移除疑似被投毒的候选点"，依赖的观测量是损失、最后一层嵌入和梯度。因此防御者被默认能拿到全量偏好三元组、模型对每个样本的损失、最后一层隐藏表示与最后一层梯度；高损失过滤这一类方法还沿用了"投毒比例较小"的假设（第 5 节引用 [39, 40, 41, 27]）。论文未说明防御者是否掌握干净参考数据、是否知道投毒比例、是否有可信根数据集。

## 3. 攻击入口与流程位置

攻击入口是**本地数据准备（local data preparation）**，具体说是偏好数据的收集与标注环节；它不进入本地训练过程、不进入更新上传后的后处理、不进入服务器聚合、不进入全局模型下发，也不进入评估与部署（因为论文是集中式训练，服务器聚合与下发这两个位置根本不存在）。

具体操作步骤（第 3.1 至 3.4 节，图 2、图 3、图 4）：

1. 攻击者拿到偏好数据集 D，其中每个样本由 prompt x、被选回答 yw、被拒回答 yl 组成。
2. 选择一个干净数据上的 DPO 策略作为白盒反馈模型（随机投毒不需要这一步）。
3. 用四种选点策略之一挑出要投毒的样本：随机（Random）；按 DPO 分数从高到低排序取前 n%（DPO Score, DPOS）；按样本梯度在平均梯度方向上的投影大小排序取前 n%（Gradient Projection, GP）；先取较大比例（论文举例前 5%）的 DPO 分数点，对 prompt 的 BERT 嵌入做 K 均值聚类（K means），再从各簇均匀采样得到更小的投毒集（DPO score + BERT Embedding，图 4b）。
4. 对选中的样本翻转 chosen 与 rejected 标签；如果是后门攻击，还要在 prompt 末尾附加触发器（图 3）。
5. 用这个被投毒的偏好数据集执行 DPO 训练，得到被投毒模型。第 4.3 节报告投毒效果随 epoch 增加而增强（图 5a、图 5b），并随 β 减小而增强（图 5c、图 5d）。

## 4. 方法原理

核心思想是：DPO 把 RLHF 变成了监督学习问题，因此可以用"影响力点（influence points）"的思路，只投毒对梯度影响最大的极小一部分样本，而不是随机投毒一大片。第 3.2 节给出的 DPO 梯度分解是整篇论文的关键：

∇θ L_DPO(πθ; πref) = −β · E_{(x,yw,yl)∼D} [ σ( r̂θ(x, yl) − r̂θ(x, yw) ) · ( ∇θ log π(yw|x) − ∇θ log π(yl|x) ) ]

其中 r̂θ(x, y) = β log( πθ(y|x) / πref(y|x) ) 被当作隐式奖励，πθ 是正在微调的语言模型，πref 是原始预训练模型。被标注为"DPO-Score"的标量 σ(r̂θ(x, yl) − r̂θ(x, yw)) 只依赖一次前向，不需要梯度；论文直接取该标量等价形式 β log(πθ(yw|x)/πref(yw|x)) − β log(πθ(yl|x)/πref(yl|x)) 最大的点作为影响力点（第 3.2 节）。论文对这一做法的解释是"这也可以看作是在干净数据的学习上做误差最大化"（第 3.2 节）。

梯度投影方法（第 3.3 节，图 4a）回答两个问题：梯度方向能否在 DPO 分数选出的点里再筛，以及梯度方向能否单独作为选点依据。做法是在干净奖励上训练 DPO 策略，计算所有候选点诱导的平均梯度向量，按各点在该方向上的投影大小排序，取投影最大的点投毒。由于 7B 模型的全梯度极大，论文先用 LoRA 适配器的低秩梯度，再用满足 Johnson–Lindenstrauss 引理 [33] 的随机投影把梯度降到低维，使内积近似保持（第 3.3 节）。论文也直接用了 LoRA 适配器的完整梯度作对照。

语义多样性方法（第 3.4 节，图 4b）针对的是"某一类有害内容在影响力点中重复出现会降低其他类型投毒的效率"这一问题：先取较大比例的 DPO 分数点，对 prompt 的 BERT 嵌入聚类，再从各簇均匀采样形成更小的投毒集。

第 5 节评估的三类防御原理分别是：谱方法（[37]）假设投毒点在最后一层嵌入上与干净点在协方差矩阵最大奇异向量方向上可分；梯度聚类方法（[38]）假设投毒点在早期 epoch 的最后一层梯度空间里形成低密度簇；高损失移除（[39, 40, 41, 27]）假设投毒样本的损失偏高，低损失移除则假设其损失偏低。

## 5. 检测或防御所需的数据

以下逐项列出论文中出现过的每一种输入。需要提醒的是，论文是集中式训练，没有客户端，因此"在哪里采集"一列只能映射到集中式流程的最接近位置（"分析："这种映射是为了对齐我们的钩子分类，论文本身不使用这些术语）。

1. **偏好三元组（prompt, chosen, rejected）及其标签**。这是被投毒的对象本身，也是所有选点策略的输入。采集位置是训练前的数据准备阶段；粒度是逐样本；不需要跨轮历史；不需要干净参考数据；不需要额外计算（第 3.1、4.1 节）。
2. **干净策略下的逐样本 DPO 分数**。即 β log(πθ(yw|x)/πref(yw|x)) − β log(πθ(yl|x)/πref(yl|x))，由一个先在干净数据上训练好的 DPO 策略计算（第 3.2 节）。采集位置是"客户端训练后"意义上的一次离线批处理：先完成一轮干净 DPO 训练，再对全部候选样本做前向；粒度逐样本；需要干净参考模型与干净数据集（论文强调是白盒反馈）；需要额外前向计算；不需要跨轮历史。
3. **逐样本的 LoRA 梯度及其随机投影**。用于梯度投影选点（第 3.3 节）。粒度逐样本、逐层（LoRA 适配器层）；需要干净参考模型；需要额外反向计算与投影计算。
4. **逐样本损失**。用于高损失与低损失过滤两类防御（第 5 节，图 11）。可以在训练过程中逐样本或逐批获得；粒度逐样本；论文未说明是否需要跨轮历史；不需要干净参考数据；需要一次额外前向。
5. **最后一层（论文也单独试了最后两层）隐藏层嵌入**。用于谱方法防御，需要计算全部数据点表示的协方差矩阵及其最大奇异向量，再按每个点与该奇异向量的相关性排序（第 5 节，图 9）。粒度逐层、逐样本；需要全量数据的全局统计，但论文未说明是否需要跨轮历史；不需要干净参考数据；需要额外前向计算。
6. **最后一层梯度**。用于梯度聚类防御，论文在 epoch 2、3、4 分别对最后一层梯度做 5 簇与 10 簇聚类，统计每簇中投毒点与干净点的占比（第 5 节，图 10）。粒度逐层、逐样本；跨 epoch 观察但不是累积历史；不需要干净参考数据；需要额外反向计算。
7. **评估侧观测量**：干净奖励模型（由 Llama 2 7B 在未投毒干净数据上按 Bradley–Terry 形式训练）对模型回复的打分，以及 GPT-4 按 1 至 5 分给出的危害性评分（第 4.2 节，附录 D）。采集位置在评估阶段；粒度是逐条回复（共 200 条 prompt）；需要干净参考模型；需要额外的生成与前向计算。
8. **跨模型的选点重叠集合**。论文比较三个模型各自 DPO 分数最高的前 0.5%、4%、5%、10% 点的交集（图 8），用于判断攻击能否从白盒模型迁移到黑盒模型。

**攻击会留下什么痕迹、论文声称能绕过哪些检测**：论文在第 5 节只用自己生成的投毒数据测试防御，没有做自适应攻击。（1）谱方法：图 9A 显示按最大奇异值方向的嵌入相关性无法把干净点与投毒点分开，图 9B 显示在按相关性筛出的前 10% 点中投毒点的占比并不高，因此该方法无法过滤投毒数据。（2）梯度聚类：图 10 显示最后一层梯度聚类不会显著聚拢投毒点，而且以投毒点为主的簇极小，只有 1 至 5 个数据点，即便删掉也不影响投毒效果。（3）损失过滤：图 11 显示移除高损失的 10% 数据点在随机、DPO 分数、梯度投影三种投毒下都检测不到大部分投毒点；低损失过滤能检出约 60% 的 DPO 分数投毒点，但对随机投毒和梯度投影投毒都告失效。综合起来，论文声称 DPO 分数投毒可以绕过谱方法、梯度聚类和高损失过滤，只在低损失过滤下部分暴露。

## 6. 干预动作

论文的主要贡献是攻击，攻击本身不包含任何防御性干预：它唯一的动作是在数据准备阶段翻转标签、必要时追加触发器，然后照常训练（第 3.1 节）。

论文第 5 节评估的防御动作为**过滤样本（filter_samples）**：按相关性、聚类密度或损失大小给训练数据点排序，把排在前面的一定比例（论文用前 10%）直接移除，再在剩余数据上训练。这些动作发生在训练前的数据准备与筛选位置，属于客户端侧；论文没有涉及重新加权、梯度裁剪、加噪、模型修复或回滚，也没有服务器聚合动作（不是联邦设置）。第 7 节只把"修改 DPO 学习目标使其对这些攻击鲁棒"列为未来方向，没有给出具体干预机制。

## 7. 实验设置与主要结果

**设置**：模型为 Mistral 7B、Llama 2 7B、Gemma 7B；数据为 Anthropic RLHF harmless-base 划分的 42537 个偏好样本；LoRA 的 r = 8、α = 16、dropout 0.05，学习率 1.41e−5，RMSprop，batch size 16，β = 0.1，多数实验训练 2 至 5 个 epoch；评估在 200 条测试 prompt 上做，指标是干净奖励模型的 poison score 与 GPT-4 的 1 至 5 危害性评分（第 4.1、4.2 节）。论文是集中式训练，所以**客户端数与参与率不适用**，论文也没有做非独立同分布（non-IID）划分，数据是单一集中数据池。恶意样本比例为 0.1%、0.5%、1%、4%、5%（表 1、表 4、表 5），非后门实验讨论到 25%（图 6）。

**关键结果**：

- 表 1（Llama 2 7B，后门攻击，表头在 PDF 抽取中有换行错位）显示 DPO 分数选点远优于随机选点。以第 5 个 epoch 为例，0.5% 投毒时 GPT-4 评分为 3.42（DPOS）对 2.26（Random），干净奖励为 2.46 对 0.08；4% 投毒时干净奖励在第 4 个 epoch 达到 6.33（DPOS）对 3.09（Random）。论文由此得出 0.5% 左右即足以投毒 DPO 的结论。
- 摘要与第 1 节报告：基于 PPO 的方法在后门攻击下至少需要 4% 的投毒数据才能诱发有害行为，而本文只需低至 0.5% 的数据。
- 表 4（Mistral 7B，干净奖励，后门）显示同样的趋势：0.5% 投毒时第 5 个 epoch 为 1.62（DPOS）对 0.14（Random），1% 时为 4.57 对 0.58，4% 时为 6.22 对 3.01，5% 时为 6.85 对 3.57。
- 表 5（Gemma 7B，干净奖励，后门）显示 0.5% 时为 2.49（DPOS）对 −0.12（Random），1% 时为 5.0 对 1.8，4% 时为 5.98 对 5.25，5% 时为 7.23 对 6.27。
- 表 2（Mistral 7B）比较 DPO 分数选点与在此基础上再用梯度投影过滤：0.5% 投毒、第 5 个 epoch 时为 1.62 对 0.55，1% 时为 4.57 对 2.82，4% 时为 6.22 对 6.20，说明进一步用梯度过滤通常反而降低投毒效率。
- 图 5 显示投毒分数随 epoch 增加而上升，并随 β 变小而上升；图 6（Mistral 7B）显示非后门攻击明显更难，DPO 分数选点在 25% 投毒时才达到随机投毒 50% 的效果；图 7a 与表 3 显示在 DPO 分数点之上做 BERT 嵌入聚类没有提升投毒效果；图 7b 显示梯度投影攻击优于随机但弱于 DPO 分数攻击；图 7c 显示随机投影与使用完整 LoRA 梯度效果相当；图 8 显示 Llama 2 7B 与其他模型的影响力点几乎不重叠，而 Mistral 7B 与 Gemma 7B 在前 0.5% 的点上有 22% 的重叠；图 13 显示在随机投毒下 PPO 与 DPO 表现相近。

## 8. 开销

论文报告了实验的硬件环境：多数实验至少使用 4 张 A500 GPU 或同等算力、64 GB 内存（第 4.1 节）。论文也描述了攻击侧的成本结构：DPO 分数选点被明确称为"最简单且成本有效"的做法，因为它不需要计算梯度（第 3.2 节）；梯度投影选点则因为 7B 参数的全梯度极大，先用 LoRA 梯度再用随机投影降维（第 3.3 节）。论文还报告了训练超参数与 epoch 数（第 4.1 节）。

除此之外，论文未报告运行时间、浮点运算量、显存占用或任何量化开销，也没有报告防御方法的额外开销；由于不是联邦设置，通信开销与存储开销论文未报告。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**：

1. 偏好数据的标注被外包，攻击者能够影响或决定哪些样本进入训练集，并翻转标签、追加触发器（第 1 节、第 3.1 节）。
2. 攻击者拥有白盒能力：DPO 分数选点与梯度投影选点都需要先在干净数据上训练一个 DPO 策略，再读取它的分数或梯度（图 2 图注、第 3.2、3.3 节）。随机投毒不需要这一条。
3. 投毒效果与训练轮数正相关、与 β 负相关，因此攻击需要受害者训练足够多的 epoch 或使用较小的 β（图 5）。
4. 危害性可以由干净奖励模型与 GPT-4 评分可靠度量，且两种度量一致（第 4.2 节）。
5. 影响力点的可迁移性只在部分模型对之间成立（图 8），所以跨模型黑盒攻击不是普遍可行的。
6. 防御评估只在"数据异常检测并移除样本"这一族方法内成立（第 5 节）。

**论文自述的局限**：DPO 分数攻击依赖模型架构（第 6 节："it also comes with its limitations of being dependent on the model architecture"）；非后门攻击需要投毒多达 25% 的数据，在真实场景中不实用（第 6 节）；影响力点的跨模型迁移不是普遍的（第 7 节）；论文只把"改造 DPO 目标函数以获得鲁棒性"列为方向而没有给出方法（第 7 节）。

**是否评估自适应攻击者**：没有。第 5 节的三类防御是在论文自己用固定策略生成的投毒数据上测试的，攻击者没有针对这些防御调整选点或标签翻转方式；论文也没有评估防御被知晓后攻击者会如何变化。因此评估的是"防御对既有攻击的有效性"，不是自适应攻击。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**：

- 论文把全部偏好数据视为一个集中数据池，因此"投毒 0.5% 的样本"是一个全局样本比例。在联邦 LoRA 中，投毒比例通常按客户端数或按客户端本地数据计，恶意客户端本地数据集越大其贡献的投毒样本越多，0.5% 这个数字不能直接搬过来。
- 论文的 DPO 分数与逐样本梯度都要求对每个样本做前向或反向。联邦场景下原始偏好样本留在客户端，服务器通常看不到 prompt、chosen、rejected，也拿不到逐样本梯度，因此第 3.2 与 3.3 节的选点方法在服务器侧不可直接执行，只能假设攻击者本身就是客户端（论文没有考虑这种攻击者）。
- 论文的 πref 是同一份预训练模型，DPO 分数在同一参考模型下可比。联邦 LoRA 中若各客户端从不同的基础检查点或不同的继续预训练状态出发，分数与梯度跨客户端不可比，"按分数排序取前 n%"这一步会失去意义。
- 论文的防御需要全量数据的嵌入协方差矩阵或全量梯度聚类。在联邦中这要么需要服务器收集客户端的中间表示，要么需要客户端上传统计量，两者都会与"数据不出客户端"的信任边界冲突；论文没有讨论安全聚合、差分隐私或拜占庭鲁棒聚合会不会改变结论。
- 论文的 LoRA 只用来降低梯度维度，不是通信对象；联邦 LoRA 交换的是适配器参数，攻击入口因此还会多出"更新上传前的后处理"和"服务器聚合"两个位置，而这两个位置论文完全没有涉及。

## 10. 对防护库设计的含义

（本节全部为分析。）

1. 采集底座需要在**偏好数据准备阶段**提供"原始三元组版本 + 标签快照 + prompt 原文"的数据视图，因为这篇论文的攻击完全落在这一层：翻转 chosen/rejected 以及在 prompt 末尾追加触发器。这是这篇论文特有的入口，但"保留数据进入训练前的原始副本以便比对"是通用需求。
2. 需要一个可注册的**影子干净 DPO 策略**视图：论文的攻击者靠它计算逐样本 DPO 分数，防御方若要复现攻击强度或做影响力分析，也必须在干净数据上训练一个 DPO 策略并保留 πθ 与 πref 两份权重同时可用。这是这篇论文特有的采集点，属于"训练后"钩子。
3. **逐样本 DPO 分数、逐样本损失、最后一层嵌入、最后一层梯度**这四种视图都应做成可插拔插件，但论文的证据表明它们在 DPO 语言模型上区分度不足（图 9、图 10、图 11），所以库不应把它们设为默认的投毒检测器或默认告警来源；这是通用视图，不是这篇论文特有的。
4. 服务器与客户端钩子需要提供**样本级剔除接口**并记录"被判为异常的分数、阈值与被剔除的样本标识"，因为论文评估的防御动作只有过滤样本这一种，而且论文只报告了检出率（低损失过滤检出约 60% 的 DPO 分数投毒点），没有报告误报率，所以库必须让使用者能看到剔除决策的可追溯记录。
5. 采集底座应支持"训练前一次性全量前向/反向批处理"这种形态，而不只是逐轮增量统计：论文的谱方法与梯度聚类都在若干 epoch 上对全量数据做一次全局统计（图 9、图 10），而损失过滤只需要逐样本损失。跨轮历史在这篇论文里不是必需的，但逐样本的批处理视图是必需的。
6. 需要**评估阶段钩子**来接干净奖励模型与外部评审模型（这里是 GPT-4）两条评分链路，因为投毒是否成功只有在训练结束后的生成与打分上才能观察（第 4.2 节、附录 D）；另外，由于论文没有联邦流程，服务器聚合钩子在这篇论文里没有对应物，把它的逐样本视图直接搬到联邦场景会与"数据不出客户端"的边界冲突。

## 11. 原文依据

1. 摘要：*"We find that unlike PPO-based methods, which, when it comes to backdoor attacks, require at least 4% of the data to be poisoned to elicit harmful behavior, we exploit the true vulnerabilities of DPO"* ——支撑第 7 节关于 0.5% 投毒即可生效、以及第 1 节论文结论的论断。
2. 第 1 节：*"However, with the need for human preferences data, there comes an increasing pattern of outsourcing the task of data annotation, which opens up vulnerabilities that can poison the LLMs."* ——支撑第 2 节"攻击者是数据标注外包方"的威胁模型。
3. 第 3.1 节：*"Regarding backdoor attacks for a poisoned data sample, we add a trigger at the end of the prompt, and chosen and rejected labels for the corresponding prompt’s responses are flipped as in the work of [5]."* ——支撑第 3 节关于攻击入口在数据准备阶段、以及后门攻击的具体操作步骤。
4. 第 3.2 节：*"For this type of attack, we first train a DPO policy with the non-poisoned clean dataset and then compute the score for points using the learned clean policy."* ——支撑第 5 节"DPO 分数需要干净参考策略与额外前向计算"这一数据需求。
5. 第 3.3 节：*"we consider a dimensionally reduced gradient by first using Low-rank approximation adaptors (LORA) [32] and then further projecting the gradients into a low dimensional space by using random projections"* ——支撑第 4 节梯度投影方法与第 8 节关于梯度降维开销的描述。
6. 第 4.1 节：*"Data: For the preference dataset similar to [5] we use harmless-base split of the Anthropic RLHF dataset [35]. The dataset consists of 42537 samples of which 0.5% corresponds to roughly 212 samples."* ——支撑第 1 节与第 7 节的数据规模与投毒比例换算。
7. 第 4.2 节：*"We use a clean reward model learned from the non-poisoned clean dataset using the Bradly Terry formulation to [4] of the reward function."* ——支撑第 7 节的评估指标与第 5 节"评估需要干净奖励模型"这一数据需求。
8. 第 4.3 节：*"We find that the influential points are model-specific. As shown in Figure 8, we notice that the Llama 2 7B model has almost no overlap with the other models."* ——支撑第 9 节关于影响力点跨模型迁移假设不成立的论断。
9. 第 5 节：*"We find that these type of separation does not happen in language models even when a universal backdoors are sufficiently installed (5% poison) as seen in Figure 9"* ——支撑第 5 节"谱方法防御在语言模型上无法分离干净点与投毒点"的论断。
10. 第 5 节：*"In the meanwhile low loss based filtering even though managed to detect 60% of the dpo score based poisoned data it failed to detect the poisons efficiently in case of both the random and gradient projection based attacks."* ——支撑第 5 节与第 6 节关于低损失过滤只部分检出 DPO 分数投毒、对随机与梯度投影投毒无效的论断。

```json
{
  "key": "pathmanathan2024dpo",
  "title": "Is Poisoning a Real Threat to LLM Alignment? Maybe More So Than You Think",
  "year": 2024,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor", "jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "preference triples (prompt, chosen, rejected) and their labels", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "per-sample DPO score computed with a DPO policy trained on clean data", "where": "client_post_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "per-sample LoRA gradients and their random projections", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "per-sample DPO loss for high-loss and low-loss filtering", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "last-layer hidden embeddings and their correlation with the top singular vector", "where": "client_post_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "last-layer gradients clustered across early epochs", "where": "client_post_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "clean reward model scores and GPT-4 harmfulness ratings of generated responses", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["client"],
  "assumptions": [
    "偏好数据标注被外包，攻击者能选择被投毒样本、翻转 chosen 与 rejected 标签，并在后门攻击中向 prompt 末尾追加触发器",
    "DPO 分数选点与梯度投影选点需要白盒访问在干净数据上训练好的 DPO 策略",
    "投毒效果随训练轮数增加而增强、随 β 减小而增强",
    "危害性可由干净奖励模型评分与 GPT-4 的 1 至 5 分评分度量，且两者结论一致",
    "影响力点是模型相关的，跨模型迁移只在 Mistral 7B 与 Gemma 7B 之间部分成立",
    "防御评估只覆盖数据异常检测并移除样本这一类方法，且针对的是非自适应攻击"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 7 节：后门攻击下 0.5% 投毒即可生效，对比 PPO 至少需要 4%", "text": "We find that unlike PPO-based methods, which, when it comes to backdoor attacks, require at least 4% of the data to be poisoned to elicit harmful behavior, we exploit the true vulnerabilities of DPO"},
    {"section": "Section 1", "supports": "第 2 节：攻击者是偏好数据标注的外包方", "text": "However, with the need for human preferences data, there comes an increasing pattern of outsourcing the task of data annotation, which opens up vulnerabilities that can poison the LLMs."},
    {"section": "Section 3.1", "supports": "第 3 节：攻击入口在数据准备阶段，后门攻击为触发器加标签翻转", "text": "Regarding backdoor attacks for a poisoned data sample, we add a trigger at the end of the prompt, and chosen and rejected labels for the corresponding prompt’s responses are flipped as in the work of [5]."},
    {"section": "Section 3.2", "supports": "第 5 节：DPO 分数需要先在干净数据上训练策略再逐点计算", "text": "For this type of attack, we first train a DPO policy with the non-poisoned clean dataset and then compute the score for points using the learned clean policy."},
    {"section": "Section 3.3", "supports": "第 4 节与第 8 节：梯度投影攻击用 LoRA 梯度加随机投影降维", "text": "we consider a dimensionally reduced gradient by first using Low-rank approximation adaptors (LORA) [32] and then further projecting the gradients into a low dimensional space by using random projections"},
    {"section": "Section 4.1", "supports": "第 1 节与第 7 节：数据集为 42537 个样本，0.5% 约为 212 个样本", "text": "Data: For the preference dataset similar to [5] we use harmless-base split of the Anthropic RLHF dataset [35]. The dataset consists of 42537 samples of which 0.5% corresponds to roughly 212 samples."},
    {"section": "Section 4.2", "supports": "第 7 节：评估使用在干净数据上训练的奖励模型", "text": "We use a clean reward model learned from the non-poisoned clean dataset using the Bradly Terry formulation to [4] of the reward function."},
    {"section": "Section 4.3", "supports": "第 9 节：影响力点跨模型迁移的假设不成立", "text": "We find that the influential points are model-specific. As shown in Figure 8, we notice that the Llama 2 7B model has almost no overlap with the other models."},
    {"section": "Section 5", "supports": "第 5 节：谱方法防御无法在语言模型上分离投毒点与干净点", "text": "We find that these type of separation does not happen in language models even when a universal backdoors are sufficiently installed (5% poison) as seen in Figure 9"},
    {"section": "Section 5", "supports": "第 5 节与第 6 节：低损失过滤只检出约 60% 的 DPO 分数投毒点，对随机与梯度投影投毒无效", "text": "In the meanwhile low loss based filtering even though managed to detect 60% of the dpo score based poisoned data it failed to detect the poisons efficiently in case of both the random and gradient projection based attacks."}
  ]
}
```
