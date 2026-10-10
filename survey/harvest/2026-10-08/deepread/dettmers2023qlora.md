# dettmers2023qlora：QLoRA: Efficient Finetuning of Quantized LLMs

> 说明：论文正文把方法写作 QLORA，标题写作 QLoRA，本报告按原样引用。该论文是**集中式大模型参数高效微调的基础方法论文**，不包含任何联邦学习、攻击、防御或检测内容；下文凡涉及攻击与防护的部分，除明确标注为"论文未说明"外，均以"分析："开头，属于我的推断而非论文结论。

## 1. 基本信息

- 场景：集中式大模型训练与参数高效微调，不是联邦学习，也不是联邦大模型微调。论文的全部训练都在单个进程或单机多卡上完成，摘要称"reduces memory usage enough to finetune a 65B parameter model on a single 48GB GPU"（摘要），第 1 节称把 65B 模型微调的显存需求从超过 780 GB 降到小于 48 GB。论文没有客户端、服务器、轮次、参与率等任何联邦概念。分析：它对"参数高效微调供应链"有间接相关性，因为第 1 节明确发布了 7B、13B、33B、65B 四个规模、8 个指令数据集上共 32 个适配器（adapter），存在"适配器发布者"这一角色，但论文本身不讨论供应链安全。
- 训练阶段：基座模型预训练权重固定并量化为 4 位后冻结，只训练插入的 LoRA（Low-rank Adapter，低秩适配器）参数；属于监督式指令微调（instruction finetuning）阶段，不使用强化学习（第 5.1 节："we perform QLoRA finetuning with cross-entropy loss (supervised learning) without reinforcement learning"）。
- 论文类型：基础方法（foundation），同时包含大量评测实验。它不是攻击论文，不是防御或检测论文，也不是基准或平台论文。
- 模型与数据规模：模型包括 RoBERTa-large、T5-80M 到 T5-11B、LLaMA 7B 到 65B，以及用于量化对比的 OPT、BLOOM、Pythia（125M 到 13B，第 4 节实验设置；第 4 节结果段又写作 125M 到 65B）。论文称训练了超过 1,000 个模型（第 1 节）。指令数据集共 8 个（第 5.1 节），规模见附录 B.1：OASST1 从 161,443 条消息、66,497 个会话中筛出 9,209 个样本，HH-RLHF 160,800 条，FLAN v2 超过 15M 条、1,836 个任务，Self-Instruct 82,612 条，Alpaca 51,942 条，Unnatural Instructions 240,670 条，Longform 23,700 条，Chip2 210,289 条。默认微调配置为 NF4 加双重量化（Double Quantization）加分页优化器（Paged Optimizers），LoRA 秩 r 等于 64、α 等于 16、加在所有线性层（附录 B.2）。

## 2. 威胁模型

- 攻击者：论文未说明。论文没有定义任何攻击者角色，没有恶意客户端、恶意服务器、数据提供方或适配器发布者，也没有给出占比或数量。
- 能力与知识：论文未说明。
- 目标：论文未说明。论文不研究无目标破坏、定向后门、越狱或安全对齐破坏，也不研究隐私攻击。第 9 节只作一般性论述，认为微调是"dual-use technology that can be abused to cause harm"，但没有给出任何具体威胁模型。
- 防御者：论文未说明。论文没有防御者角色，没有定义防御者能看到什么、信任什么。论文中与信任最接近的内容有三处：第 9 节提出 QLoRA 可能帮助"privacy-preserving usage of LLMs, where users can own and manage their own data and models"；第 6.1 节用提示词让 Guanaco 保守"秘密词"并展示了被诱导泄露的失败案例，这是定性行为观察而非防御机制；第 6.2 节做了 OASST1 训练数据与 Vicuna 评测提示之间的模糊字符串匹配，未发现重叠，属于数据泄漏检查而非威胁模型。
- 分析：因此这篇论文对防护库的价值不在威胁模型，而在于它定义了一个真实的、可观测的微调数据流（4 位量化基座、唯一的 LoRA 可训练参数、仅在适配器上计算的梯度），防护库只能把这条数据流当作采集对象，而不能从论文继承任何敌手假设。

## 3. 攻击入口与流程位置

- 论文未说明任何攻击，因此不存在攻击入口。论文未说明本地数据准备、本地训练过程、更新上传前的后处理、服务器聚合、全局模型下发、评估与部署中的任何一处被攻击者利用。
- 分析：如果把论文描述的流程当作一条集中式微调流水线，它的关键节点是基座量化为 NF4 并冻结（第 3 节，公式 5 与公式 6），前向与反向在 BFloat16 计算数据类型上进行，但只有 LoRA 参数获得权重梯度（第 3 节），随后是适配器训练与公开发布（第 1 节、第 5.3 节）。若把这条流水线映射到联邦 LoRA 的信任边界，那么"本地训练过程"对应适配器参数的更新，"更新上传前的后处理"对应适配器的导出、缩放与拼装，"模型分发"对应基座与适配器一起发布。以上全部是分析，论文未作此映射。
- 分析：论文给出的确定性数值细节会决定"更新长什么样"，包括 LoRA 加在所有线性层、r 等于 64、α 等于 16、LoRA dropout 在不超过 13B 时为 0.1、在 33B 和 65B 时为 0.05、最大梯度范数为 0.3、Adam 二阶矩衰减为 0.999、常数学习率、按长度分组组批（附录 B.2 与表 9）。

## 4. 方法原理

QLoRA 的核心思想是：把预训练权重一次性量化为 4 位并冻结，反向传播穿过这个冻结的 4 位模型，只更新插入的 LoRA 适配器，从而在不损失 16 位微调性能的前提下把显存降到单卡可承受的范围。三个组成部分如下。

第一，4 位 NormalFloat（NF4）量化。论文基于分位数量化（Quantile Quantization），先估计标准正态分布 N(0,1) 的 2 的 k 次方加 1 个分位点得到数据类型的取值，公式 4 把相邻两个分位点的分位函数取平均作为码点，再把数据类型归一化到负一到一区间，输入权重张量也用绝对最大值缩放（absolute maximum rescaling）归一化到同一区间，然后按公式 1 做分块量化（block-wise k-bit quantization）。为使零有精确表示并让 2 的 k 次方个码点全被使用，论文对负半轴和正半轴分别估计分位点并去掉重复的零，得到非对称数据类型。附录 E 给出了 NF4 的 16 个精确码点。

第二，双重量化（Double Quantization，DQ）。论文把第一次量化的 32 位量化常数本身再用量化常数为 256 的分块 8 位浮点量化一次，并对量化常数先减均值以做对称量化。第 3 节报告：在分块大小为 64 时，每参数开销从 32 除以 64 等于 0.5 位降到 8 除以 64 加 32 除以（64 乘 256）等于 0.127 位，即每参数节省 0.373 位，对 65B 模型约等于 3 GB。

第三，分页优化器（Paged Optimizers）。论文使用 NVIDIA 统一内存，为优化器状态分配可分页内存，显存不足时自动换出到 CPU 内存，在优化器更新步再换回（第 3 节）。第 4 节报告在 65B 模型、48 GB 显存、批大小为 16 时，分页优化器与普通优化器训练速度相同。

QLoRA 的形式化定义见公式 5 与公式 6：输出等于输入与双重反量化后的 NF4 权重做 16 位矩阵乘，再加上输入与两个 LoRA 矩阵乘积的缩放项；双重反量化把第一级量化常数、第二级量化常数与 4 位权重还原为 BFloat16。论文强调只有一个存储数据类型（通常 4 位 NormalFloat）和一个计算数据类型（16 位 BrainFloat），前向与反向都先反量化，权重梯度只对 LoRA 参数计算，不计算对 4 位权重的梯度，但计算 LoRA 梯度时仍需要求输入对权重的导数（第 3 节）。训练侧还有一个重要发现：默认只把 LoRA 加在查询和值投影上无法复现全量微调性能，必须加在所有线性 Transformer 块层，而 LoRA 秩 r 在全体层配置下与最终性能无关（第 4 节与附录 A，图 2、图 4）。

## 5. 检测或防御所需的数据

论文未说明。这篇论文不提出任何检测或防御方法，因此不存在"方法需要的输入"。以下逐项列出的量都是论文自己产生、消费或报告的观测量；把它们当作防护库的候选采集点属于我的推断，每一项都标注为分析。

- 分析：LoRA 适配器矩阵 L1 与 L2，这是论文中唯一被更新的参数，数据类型为 BFloat16（第 3 节、公式 3 与公式 5）。采集位置为客户端训练后，粒度为逐层。不需要跨轮历史，不需要干净参考数据，不需要额外计算。论文说明其规模很小：在 7B LLaMA、FLAN v2、批大小为 1、LoRA 权重约为原模型 0.2% 的设定下，LoRA 参数只占 26 MB（第 2 节）。
- 分析：仅对 LoRA 参数计算的权重梯度（第 3 节写作对适配器权重的误差导数），数据类型为 BFloat16。采集位置为客户端每步，粒度为逐层。论文明确不计算对 4 位权重的梯度，所以基于完整权重梯度的观测量在这条流水线上不存在。不需要历史、参考数据或额外计算。
- 分析：量化后的基座权重与两级量化常数，即 4 位 NormalFloat 权重、第一级 32 位浮点量化常数、第二级 8 位浮点量化常数，以及分块大小（权重用 64，量化常数用 256，第 3 节）。采集位置为客户端训练前的基座准备阶段，粒度为逐层与逐块。不需要历史或干净参考数据；但若服务器端要把存储视图还原为计算视图，需要按附录 E 的 16 个码点做反量化查表，这属于额外计算。
- 分析：逐序列的激活与输入梯度。第 2 节报告在 7B LLaMA、FLAN v2、批大小为 1 时，LoRA 输入梯度占 567 MB；开启 gradient checkpointing 后平均每序列降到 18 MB；相比之下 4 位基座模型占 5,048 MB。采集位置为客户端每步，粒度可做到逐样本或逐序列、逐层。论文只报告内存统计，未报告这些张量被保留或外传。
- 分析：优化器状态。第 3 节说明分页优化器把优化器状态放在可分页内存中，显存不足时换出到 CPU 内存。采集位置为客户端每步，粒度为模型级。附录 G 的图 6 给出了 7B（6.9 GB）、13B（11.3 GB）、33B（24.7 GB）、65B（45.0 GB）的显存分解，其中包含优化器项。
- 分析：训练超参数与步数记录。表 9 给出每个模型规模和数据集下的批大小、学习率、步数、源长度和目标长度，例如 7B 全数据集为批大小 16、学习率 2e-4、10,000 步。附录 B.2 指出按长度分组组批会产生振荡的损失曲线。采集位置为客户端训练后或服务器收到更新时，粒度为模型级或客户端级。
- 分析：公开发布的适配器与合并后的模型。第 1 节说明发布 32 个适配器；第 5.3 节与表 6 给出各模型的部署显存（Guanaco 65B 为 41 GB、33B 为 21 GB、13B 为 10 GB、7B 为 5 GB）。采集位置可视为发布端，粒度为模型级。
- 分析：评估侧数据。第 5.2 节使用 Vicuna 的 80 条提示与 OASST1 验证集的 953 条用户查询，用 GPT-4 打分、Amazon Mechanical Turk 人工标注并计算 Elo。采集位置为评估时，粒度为逐样本。
- 攻击痕迹：论文未说明。论文没有讨论任何攻击会在上述可观测量上留下什么痕迹，也没有声称能够绕过任何检测，因为它不是攻击论文。

## 6. 干预动作

论文未说明。论文没有检测环节，因此没有任何检测后动作，没有剔除客户端、重新加权、裁剪、加噪、过滤样本、修复或回滚模型，也没有仅报告的流程。论文未说明这些动作发生在流程的哪个位置。

论文中唯一与"对训练施加限制"沾边的内容是优化手段而非安全手段：LoRA dropout、最大梯度范数设为 0.3、常数学习率、按长度分组组批（附录 B.2），以及分页优化器与 gradient checkpointing 的显存管理（第 3 节、第 4 节）。分析：这些旋钮可以被防护库复用为限制单个客户端更新幅度的手段，但它们的设计目的完全是保持性能与节省显存，论文没有把它们当作防御，也没有评估其安全效果。

## 7. 实验设置与主要结果

- 模型：RoBERTa-large（GLUE），T5-80M、T5-250M、T5-780M、T5-3B、T5-11B（Super-NaturalInstructions），LLaMA 7B、13B、33B、65B（Alpaca、FLAN v2、MMLU、Vicuna、OA），以及用于量化对比的 OPT、BLOOM、Pythia、LLaMA 系列（第 4 节、表 3、表 4、表 6）。
- 数据集：GLUE、Super-NaturalInstructions、Pile Common Crawl（困惑度）、MMLU 五样本、8 个指令微调数据集、Vicuna 基准、OA 基准、CrowS 偏差数据集。
- 客户端数与参与率：论文未说明，论文没有这些概念。轮次：论文未说明，论文不按轮组织。恶意比例：论文未说明。数据是否非独立同分布：论文未说明；论文只在第 6.2 节说明 OASST1 是多语言的（附录 B.1 给出 35 种语言）。
- 指标：GLUE 准确率、Super-NaturalInstructions 的 RougeL、Pile Common Crawl 困惑度、MMLU 五样本准确率、相对 ChatGPT 的百分比得分、Elo 评分、CrowS 偏差分数、Fleiss κ、Kendall Tau 与 Spearman 秩相关。
- 量化数据类型对比（表 2）：Pile Common Crawl 平均困惑度，Int4 为 34.34，Float4（E2M1）为 31.07，Float4（E3M0）为 29.48，NFloat4 加双重量化为 27.41。
- 与全量微调对齐（表 3）：GLUE 上 RoBERTa-large 的 BF16 为 88.6，LoRA BF16 为 88.8，QLORA Int8 为 88.8，QLORA FP4 为 88.6，NF4 加双重量化未运行；Super-NaturalInstructions 的 RougeL 在 T5-80M、250M、780M、3B、11B 上，BF16 分别为 40.1、42.1、48.0、54.3、62.0，QLORA NF4 加双重量化分别为 40.4、42.7、47.7、55.3、60.9。第 4 节据此写道，16 位、8 位与 4 位适配器方法都复现了全量 16 位微调基线的性能。
- 大模型上的 MMLU（表 4）：平均五样本准确率，BFloat16 为 53.0，Float4 为 52.2，NFloat4 加双重量化为 53.1；65B 上 FLAN v2 的三种配置分别为 62.5、63.3、63.9，7B 上 Alpaca 分别为 38.4、37.2、39.0。
- 各数据集 MMLU（表 5）：以 65B 为例，无微调 LLaMA 为 63.4，Guanaco（OASST1）为 62.2，FLAN v2 为 63.9；7B 上 FLAN v2 为 44.5，Self-Instruct 为 36.4。
- Vicuna 基准相对 ChatGPT 的得分（表 6）：Guanaco 65B 为 99.3%（置信区间正负 4.4%），显存 41 GB；Guanaco 33B 为 97.8%，21 GB；Guanaco 13B 为 90.4%，10 GB；Guanaco 7B 为 87.0%，5 GB；GPT-4 为 114.5%。
- Elo（表 1、表 7）：GPT-4 裁判的 Elo 中 GPT-4 为 1348、Guanaco 65B 为 1022、Guanaco 33B 为 992、Vicuna 13B 为 974、ChatGPT 为 966；人类裁判在 Vicuna 上的 Elo 中 GPT-4 为 1176、Guanaco-65B 为 1023、Guanaco-7B 为 1010（排名第三）、Guanaco-33B 为 1009。
- 偏差（表 8）：CrowS 平均分 Guanaco-65B 为 43.5，低于 LLaMA-65B 的 66.6、GPT-3 的 67.2、OPT-175B 的 69.5。
- 评测一致性（第 5.3 节与第 6.2 节）：系统级 Kendall Tau 为 0.43，Spearman 秩相关为 0.55，样本级 GPT-4 与人类多数票的 Fleiss κ 为 0.25，人类标注者之间的 Fleiss κ 为 0.42。
- 数据集规模与质量（附录 B.4 与表 11）：把 Chip2、Unnatural Instructions、FLAN v2 子采样到 50,000、100,000、150,000 并训练一至三轮，MMLU 只变动 0.0 到 0.5，而数据集之间的差异可达 1.5 到 8.0，即大 40 倍；表 10 显示只训练回答（均值 38.6）优于同时训练指令与回答（均值 37.5）。

## 8. 开销

- 显存：论文报告 65B 模型的 16 位微调需要超过 780 GB 显存，QLoRA 降到小于 48 GB（第 1 节）；部署显存见表 6，65B 为 41 GB、33B 为 21 GB、13B 为 10 GB、7B 为 5 GB；附录 G 的图 6 给出训练显存分解，7B 为 6.9 GB、13B 为 11.3 GB、33B 为 24.7 GB、65B 为 45.0 GB，并说明 33B 模型无法完全装入 24 GB 显存，需要分页优化器。
- 量化常数开销：分块大小为 64 时，每参数开销从 0.5 位降到 0.127 位，节省 0.373 位，对 65B 模型约 3 GB（第 3 节）。
- 参数与激活开销：7B LLaMA、FLAN v2、批大小为 1 时，LoRA 参数占 26 MB，LoRA 输入梯度占 567 MB，开启 gradient checkpointing 后平均每序列 18 MB，4 位基座模型占 5,048 MB（第 2 节）。
- 时间：摘要报告在单张 GPU 上微调 24 小时；第 5.3 节报告 33B Guanaco 可在 24 GB 消费级 GPU 上于不到 12 小时内训练完成；表 9 给出各配置的训练步数，从 1,875 到 10,000 步不等。
- 论文自述的开销报告缺口：第 4 节明确不为分页优化器提供硬性测量，因为分页只在处理长序列小批量时发生，论文认为这种情况罕见，并把测量分页何时导致变慢留给未来工作。
- 通信开销：论文未报告，论文是集中式训练，没有通信成本讨论。存储开销：论文报告了 LoRA 参数的 26 MB 与发布模型的部署显存，但没有给出适配器文件大小或磁盘占用，这部分论文未报告。训练总算力、能耗与端到端墙钟时间（除上述 24 小时与 12 小时外）论文未报告。

## 9. 假设、局限与自适应攻击

论文成立所依赖的假设（论文自述）：

- 冻结的 4 位基座加 LoRA 适配器足以恢复 16 位全量微调性能，前提是适配器加在所有线性 Transformer 块层，只加在查询和值投影上不够（第 4 节、图 2）。
- 当适配器加在所有层时，LoRA 秩 r 与最终性能无关（附录 A、图 4）。
- 预训练神经网络权重近似服从零均值正态分布，因此 NF4 的信息论最优性适用；附录 F 用 Shapiro-Wilk 检验 7B LLaMA 的每个隐藏单元，在 5% 显著性水平下发现 7.5% 的神经元非正态，比预期假阳性率高出约 2.5%，论文承认存在例外。
- 对量化常数做第二级 8 位量化不损伤性能，且双重量化不降低性能（第 3 节、第 4 节、图 3）。
- 训练目标是监督式交叉熵，不使用基于人类反馈的强化学习；论文称这是为了避免不同训练目标带来的混淆（第 5.1 节）。
- 评测层面假设 GPT-4 可作为人类评测的廉价替代，但论文同时报告两者只是中等一致（第 5.3 节与第 6.2 节）。

论文自述的局限（第 8 节）：

- 论文没有证明 QLoRA 在 33B 与 65B 规模上能匹配全量 16 位微调性能，并因资源成本把该研究留给未来工作。
- 评测只覆盖 MMLU、Vicuna 与 OA，未评测 BigBench、RAFT、HELM 等基准，无法保证结论可推广。
- 只做了有限的责任人工智能评测，偏差方面只用了 CrowS 数据集。
- 未评测其他位精度（例如 3 位基座）与其他参数高效微调方法。
- 第 6.2 节报告 GPT-4 评测存在明显的顺序偏差，人类标注者之间一致性中等（Fleiss κ 等于 0.42）。
- 第 4 节把分页优化器在什么情况下造成变慢留给未来工作。
- 第 6.2 节报告对 OASST1 与 Vicuna 提示做了模糊字符串匹配并人工检查最近的匹配，未发现重叠。

自适应攻击：论文未评估。论文没有攻击者，也没有自适应攻击者实验；第 9 节只作一般性论述，承认微调是双用途技术并可能被滥用，但未给出任何攻击或防御评估。

迁移到联邦 LoRA 微调时可能失效的假设（分析：以下均为我的推断，论文未作任何联邦设定下的讨论）：

- 论文假设整条流水线在单机内完成，量化、训练、评测之间没有信任边界。迁移到联邦场景时，"客户端上传什么、服务器能看到什么"完全需要重新定义，论文无法提供依据。
- 论文把 4 位基座冻结在本地并只计算 LoRA 梯度，因此服务器若沿用"检查完整权重梯度"的思路将拿不到数据；只有逐层 LoRA 增量与 LoRA 梯度可用。
- 论文的存储视图是 NF4 而计算视图是 BFloat16，二者通过公式 5 与公式 6 的反量化关联。分析：如果服务器与客户端的分块大小（权重 64、量化常数 256）或码点表（附录 E）不一致，同一适配器在两个视图下的统计量不可比，检测器容易误判。
- 论文发现 LoRA 秩与挂载层数对性能有决定性影响而秩本身可自由变化。分析：这意味着攻击者可以在不牺牲性能的前提下改变上传张量的形状与稀疏结构，任何把秩或挂载位置写死的检测假设都需要重新检验。
- 论文的损失曲线受按长度分组组批影响而振荡，学习率在 33B 与 65B 上减半而批大小加倍。分析：在联邦场景下这些细节会与客户端异构性叠加，基于损失轨迹的检测必须先把组批与学习率策略对齐。
- 论文完全没有涉及客户端采样、拜占庭鲁棒聚合、通信压缩与跨轮历史，这些在联邦 LoRA 中必须由库自行定义。

## 10. 对防护库设计的含义

以下全部为分析：

1. 采集点应围绕"适配器是唯一可训练张量"这一事实设计：客户端训练后的钩子需要导出逐层的 L1 与 L2（BF16），服务器收到更新时的钩子需要拿到每个客户端的适配器及其形状与秩元数据，而不应假设能拿到全模型梯度，因为论文明确只对 LoRA 参数计算权重梯度。
2. 库需要显式区分"存储视图"与"计算视图"：论文的基座以 4 位 NormalFloat 存储、以 BFloat16 计算，因此除了适配器本身，还要采集两级量化常数、分块大小与附录 E 的码点表，否则服务器无法在客户端相同的数值语义下复现前向并比较统计量。这是这篇论文特有的需求，通用联邦学习库通常没有量化账本这一层。
3. 这篇论文不能提供跨轮历史或干净参考数据的接口依据，因为它是单进程、单次微调；库若要做跨轮检测，必须自行定义适配器版本链，并把每个版本与基座指纹（量化配置、发布者、LoRA 超参数）绑定。
4. 干预接口需要库自己实现：论文没有任何检测后动作，唯一的可复用旋钮是训练侧的最大梯度范数、LoRA dropout 与学习率调度，它们可以用来限制单个客户端更新的幅度，但论文没有评估其安全效果，因此只能作为约束而非防御。
5. 适配器发布应作为一个独立信任边界：论文公开发布 32 个适配器，说明"基座加适配器"的组合会在训练之外被分发与合并；库应把合并与分发也纳入采集，记录基座版本、量化配置、LoRA 超参数与评测结果。
6. 通用与特有的边界：通用的是"客户端训练后导出逐层增量、服务器收到时逐客户端记录"这一钩子形状；特有于这篇论文的是 4 位基座带来的量化与反量化账本，以及适配器加在所有线性层、r 等于 64、α 等于 16 这些具体形状约定。联邦聚合的轮次、采样率与客户端选择等钩子在论文中完全没有依据。

## 11. 原文依据

1. 摘要。"QLORA backpropagates gradients through a frozen, 4-bit quantized pretrained language model into Low Rank Adapters (LoRA)." 支撑第 1 节与第 4 节的论断：方法是集中式的冻结量化基座加适配器微调，梯度只流向 LoRA。
2. 第 2 节。"While LoRA was designed as a Parameter Efficient Finetuning (PEFT) method, most of the memory footprint for LLM finetuning comes from activation gradients and not from the learned LoRA parameters." 支撑第 5 节与第 8 节的论断：论文关注的资源是激活梯度与显存，适配器参数本身很小。
3. 第 3 节。"We dequantize the storage data type to the computation data type to perform the forward and backward pass, but we only compute weight gradients for the LoRA parameters which use 16-bit BrainFloat." 支撑第 4 节与第 5 节的论断：只有 LoRA 参数有梯度，服务器看不到完整权重梯度。
4. 第 3 节。"Since pretrained neural network weights usually have a zero-centered normal distribution with standard deviation σ (see Appendix F), we can transform all weights" 支撑第 9 节的论断：NF4 的最优性依赖权重近似正态分布这一假设。
5. 第 4 节。"we find that the most critical LoRA hyperparameter is how many LoRA adapters are used in total and that LoRA on all linear transformer block layers are required to match full finetuning performance." 支撑第 4 节与第 10 节的论断：适配器必须覆盖所有线性层，上传张量的形状由这一约定决定。
6. 第 4 节。"In both datasets, we observe that 16-bit, 8-bit, and 4-bit adapter methods replicate the performance of the fully finetuned 16-bit baseline." 支撑第 7 节的主要结果：4 位适配器微调在 GLUE 与 Super-NaturalInstructions 上对齐 16 位全量微调。
7. 第 4 节。"we do not provide hard measurements for Paged Optimizers since the paging only occurs when processing mini-batches with long sequence lengths, which is rare." 支撑第 8 节的论断：论文自述分页优化器的开销未被硬性测量。
8. 第 5.1 节。"we perform QLoRA finetuning with cross-entropy loss (supervised learning) without reinforcement learning, even for datasets that include human judgments of different responses." 支撑第 1 节与第 7 节的论断：训练目标是监督式交叉熵，不含强化学习。
9. 第 8 节。"we did not establish that QLORA can match full 16-bit finetuning performance at 33B and 65B scales. Due to the immense resource costs, we leave this study to future work." 支撑第 9 节的论断：大模型规模上的性能对齐尚未被论文证明。
10. 第 1 节。"We release a collection of adapters for 7/13/33/65B size models, trained on 8 different instruction following datasets, for a total of 32 different open sourced, finetuned models." 支撑第 3 节与第 10 节的论断：适配器会被公开分发，存在发布端这一信任边界。

```json
{
  "key": "dettmers2023qlora",
  "title": "QLoRA: Efficient Finetuning of Quantized LLMs",
  "year": 2023,
  "paper_type": "foundation",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["none"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "LoRA 适配器矩阵 L1 与 L2，BF16，论文中唯一被更新的参数", "where": "client_post_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "仅对 LoRA 参数计算的权重梯度，论文明确不计算对 4 位权重的梯度", "where": "client_step", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "4 位 NormalFloat 基座权重、第一级 FP32 量化常数、第二级 FP8 量化常数与分块大小（权重 64，量化常数 256）", "where": "client_pre_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "逐序列激活与输入梯度（论文报告 567 MB 输入梯度，gradient checkpointing 后平均 18 MB 每序列）", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "分页优化器状态及其在 CPU 与 GPU 之间的换页", "where": "client_step", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "训练超参数与步数记录（批大小、学习率、步数、源长度、目标长度）", "where": "client_post_train", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "公开发布的适配器与基座组合（32 个适配器）及其部署显存", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "评估侧生成文本与打分（Vicuna 80 条提示、OA 953 条查询、GPT-4 打分、人类标注、Elo）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "冻结的 4 位基座加 LoRA 适配器可以恢复 16 位全量微调性能，前提是适配器加在所有线性层",
    "LoRA 秩在全体层配置下与最终性能无关",
    "预训练权重近似零均值正态分布，因此 NF4 的信息论最优性适用",
    "对量化常数的第二级 8 位量化不损伤性能",
    "训练只用监督式交叉熵，不使用强化学习",
    "GPT-4 评测可作为人类评测的廉价替代，两者只是中等一致"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节与第 4 节：集中式冻结量化基座加 LoRA 适配器微调，梯度只流向 LoRA", "text": "QLORA backpropagates gradients through a frozen, 4-bit quantized pretrained language model into Low Rank Adapters (LoRA)."},
    {"section": "Section 2", "supports": "第 5 节与第 8 节：显存瓶颈在激活梯度而非适配器参数", "text": "While LoRA was designed as a Parameter Efficient Finetuning (PEFT) method, most of the memory footprint for LLM finetuning comes from activation gradients and not from the learned LoRA parameters."},
    {"section": "Section 3", "supports": "第 4 节与第 5 节：只有 LoRA 参数有梯度，不存在完整权重梯度视图", "text": "We dequantize the storage data type to the computation data type to perform the forward and backward pass, but we only compute weight gradients for the LoRA parameters which use 16-bit BrainFloat."},
    {"section": "Section 3", "supports": "第 9 节：NF4 依赖权重近似正态分布", "text": "Since pretrained neural network weights usually have a zero-centered normal distribution with standard deviation σ (see Appendix F), we can transform all weights"},
    {"section": "Section 4", "supports": "第 4 节与第 10 节：适配器必须覆盖所有线性层，决定上传张量形状", "text": "we find that the most critical LoRA hyperparameter is how many LoRA adapters are used in total and that LoRA on all linear transformer block layers are required to match full finetuning performance."},
    {"section": "Section 4", "supports": "第 7 节：4 位适配器微调对齐 16 位全量微调", "text": "In both datasets, we observe that 16-bit, 8-bit, and 4-bit adapter methods replicate the performance of the fully finetuned 16-bit baseline."},
    {"section": "Section 4", "supports": "第 8 节：分页优化器开销未被硬性测量", "text": "we do not provide hard measurements for Paged Optimizers since the paging only occurs when processing mini-batches with long sequence lengths, which is rare."},
    {"section": "Section 5.1", "supports": "第 1 节与第 7 节：训练目标是监督式交叉熵，不含强化学习", "text": "we perform QLoRA finetuning with cross-entropy loss (supervised learning) without reinforcement learning, even for datasets that include human judgments of different responses."},
    {"section": "Section 8", "supports": "第 9 节：大模型规模上的性能对齐尚未证明", "text": "we did not establish that QLORA can match full 16-bit finetuning performance at 33B and 65B scales. Due to the immense resource costs, we leave this study to future work."},
    {"section": "Section 1", "supports": "第 3 节与第 10 节：适配器被公开分发，存在发布端信任边界", "text": "We release a collection of adapters for 7/13/33/65B size models, trained on 8 different instruction following datasets, for a total of 32 different open sourced, finetuned models."}
  ]
}
```
