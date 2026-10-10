# ye2024emerging：Emerging Safety Attack and Defense in Federated Instruction Tuning of Large Language Models

## 1. 基本信息

- 场景：联邦大模型微调（federated instruction tuning，论文简称 FedIT），并且明确使用参数高效微调（parameter-efficient fine-tuning，PEFT）中的 LoRA（low-rank adaptation）与 8 比特量化基座。论文不是传统联邦学习（图像分类等）研究，也不是集中式大模型训练研究。
- 训练阶段：监督式指令微调（supervised fine-tuning，SFT）阶段。系统先进行 100 轮联邦指令微调，随后（论文实验中是最后一轮聚合之后）在服务器侧对聚合得到的 LoRA 适配器（adapter）做一段 post-hoc 安全对齐微调（第 6.1 节、第 5 节）。
- 论文类型：攻击与防御并重。论文首先提出一种数据投毒式的"安全攻击"（safety attack），然后针对它提出一种事后防御（post-hoc defense）。论文本身不提出新的检测器；它把六种已有联邦学习鲁棒聚合/检测方法当作对照基线复现（第 6.2 节，表 1、表 2）。
- 模型与数据规模：基座模型 Llama2-7B（第 6.1 节），附录 C.8 另外报告 Mistral-7B。良性指令数据集四个：LMSYS-Chat、WildChat、Dromedary-verbose、Wizard-evol；恶意数据两种：公开的 Beavertails，以及用 Mistral-7B-Instruct 自动生成的 MaliciousGen（第 6.1 节）。主实验共 10 个客户端，其中 7 个良性、3 个恶意，每轮采样 3 个客户端参与，每个客户端持有 500 条样本，每轮本地训练 10 步，共 100 个通信轮（第 6.1 节、附录 C.1）。LoRA 秩 r = 32、缩放 α = 64，基座 8 比特量化，AdamW 优化器，批大小 16，最大序列长度 512，初始学习率 5e-5 并采用余弦调度，全部实验在单张 NVIDIA GeForce RTX 3090 上完成（第 6.1 节、附录 C.1）。评估用 AdvBench 的安全指标 Rule、MD-Judge、RM，以及 MT-Bench 首轮指标 MT-1（第 6.1 节），附录另用 HumanEval pass@1 评估代码能力（附录 C.4）。防御侧在最后一轮聚合后的 LoRA 适配器上，用 1000 条防御样本微调 500 步（第 6.1 节）。

## 2. 威胁模型

- 攻击者是谁：恶意客户端。论文第 4.1 节写明"每个攻击者对应联邦学习系统中的一个恶意客户端"。数量上，主实验为 10 个客户端中的 3 个恶意客户端，即 30%（第 6.1 节）；附录 C.7 扫描 10%、20%、30%、40% 四种恶意比例；表 4 把规模扩到 50 和 100 个客户端并保持 30% 的恶意比例（第 6.3 节）。
- 能力：攻击者可以"在任意训练数据集上训练它的本地模型"（第 4.1 节），也就是数据投毒（data poisoning），而不是直接操纵上传的模型参数。论文第 2 节明确"我们在这项工作中关注数据投毒攻击"。恶意客户端与其他客户端走完全相同的联邦流程：收到全局模型、在本地数据上最小化自己的损失、上传本地模型（第 4.2 节）。论文未说明攻击者是否篡改上传的更新、是否控制多台客户端之外的资源。
- 知识：攻击者可以获得公开可得的未对齐（unaligned）数据，或者访问一个现成的（off-the-shelf）大语言模型来自动生成未对齐数据（第 4.1 节）。论文未说明攻击者是否知道服务器的聚合规则、其他客户端的数据分布或服务器是否部署了事后防御。
- 目标：破坏联邦训练所得全局大语言模型的安全对齐，使其在收到有害指令时给出有害回答，而在收到正常指令时仍然表现正常（第 4.1 节）。论文没有设置触发器，也没有针对特定目标输出做定向后门，因此这是对安全对齐的整体性破坏（越狱/安全对齐破坏类）。论文未说明攻击是否以窃取隐私或降低一般任务精度为目的。
- 防御者是谁、能看到什么、信任什么：防御者是服务器（第 5 节）。服务器能看到每轮客户端上传的本地大语言模型（在本文实现中是 LoRA 适配器）以及自己聚合得到的全局模型。论文中的服务器不检查、不比较本地模型参数，而是在聚合之后直接用自己的数据修复全局模型（第 5 节）。服务器信任自己生成或采样的防御数据、信任被对齐模型自身仍能产出安全回答（第 3 级防御），第 1 级防御信任一个已有的安全数据集，第 2 级防御信任一个外部现成大语言模型（第 5 节）。客户端被当作不可信方。联邦学习的基本隐私前提是服务器不直接访问客户端数据集（第 3 节）。

## 3. 攻击入口与流程位置

攻击内容进入的位置是本地数据准备，并通过正常的本地训练过程发挥作用；论文没有改动损失函数、优化器、步数、上传后处理、聚合规则、下发过程或评估环节。

具体操作步骤如下（第 4.2 节、第 4.3 节）。

1. 恶意客户端把自己的本地数据集替换为未对齐数据。第 3 节定义了三类数据：正常数据（normal data，正常指令配正常回答）、对齐数据（aligned data，有害指令配无害回答）、未对齐数据（unaligned data，有害指令配有害回答）。良性客户端持有正常或对齐数据，恶意客户端持有未对齐数据。
2. 攻击数据有两种低成本获取途径（第 4.3 节）。第一种是从公开数据集中提取，例如从 Beavertails 中挑出被人工标注为不安全的样本，或者取 HH-RLHF 中的指令与不被偏好的回答（dispreferred response）重新拼成指令-回答对。第二种是自动生成：先提示大语言模型生成一批（例如 10 条）恶意用户可能提出的有害指令，重复该过程直到数量足够；再针对每条有害指令，提示模型在不考虑安全护栏的情况下生成回答，从而得到有害指令与有害回答的配对。
3. 在每一轮通信中，服务器先把全局大语言模型下发给被采样的客户端作为本地初始化；恶意客户端与良性客户端一样做标准指令微调，即最小化各自的损失，得到本轮的本地模型（第 4.2 节）。
4. 所有本地模型上传到服务器，服务器按样本量比例做 FedAvg 加权聚合，更新全局模型（第 4.2 节给出的形式是全局模型等于各客户端本地模型按 p_k 加权求和）。恶意客户端的未对齐更新由此进入全局模型并被下发，攻击完成。

论文强调攻击的隐蔽性来自优化方向的同向性：恶意客户端与良性客户端都在学习"详细遵循用户指令并给出有用回答"，因此二者的本地模型在参数层面难以区分（第 4.4 节、图 1）。

## 4. 方法原理

攻击部分的核心思想是把良性对齐数据中的"有害指令配无害回答"替换为"有害指令配有害回答"，只改数据、不改算法（第 1 节、第 4.2 节）。用第 3 节的记号，理想情况下客户端数据满足 D_k 属于正常数据空间与对齐数据空间的并集，而攻击场景下恶意客户端的数据落在未对齐数据空间中；联邦目标是最小化各客户端损失的加权和，其中 p_k 等于该客户端样本数除以全部客户端样本数（第 3 节）。由于聚合仍然按 p_k 加权，恶意客户端的本地更新会按比例污染全局模型（第 4.2 节）。论文在图 1 中给出直观对比：传统联邦学习中的标签翻转会与良性客户端产生冲突的优化方向因而容易被检测，而安全对齐攻击中恶意客户端仍然在优化"详细回答"，方向一致，因此难以检测。

防御部分的核心思想是"事后补救"而不是"事前过滤"（第 5 节）。服务器在可能被污染的聚合完成之后，直接在聚合得到的全局大语言模型上，用一个由正常数据和对齐数据组成的防御数据集继续微调若干步。论文强调这种做法把防御过程与训练过程解耦，从而绕开了当前无法解决的"在模型参数层面筛除恶意客户端"问题（第 5 节）。防御数据的获取按对外部资源的依赖程度分三级（第 5 节）：第 1 级从已有数据集直接采样正常数据和对齐数据；第 2 级用一个外部现成大语言模型生成这两类数据；第 3 级称为自对齐（self-alignment），用服务器打算对齐的那个模型自己生成这两类数据。

自动生成管线分为指令生成与回答生成两步，都由自然语言提示（prompt）驱动（第 5 节、附录 C.2、图 5）。指令生成阶段提示模型生成恶意用户可能提出的有害指令，或好奇用户可能提出的正常指令。回答生成阶段，正常指令直接送入模型得到正常回答；对有害指令则在其后追加一段提醒，说明该问题危险、不应直接回答，并引导模型给出安全回答。把两类指令-回答对合并，就得到防御数据集：对齐数据把模型拉向安全，正常数据用来避免损害有用性（第 5 节）。附录 C.2 给出具体提示词，例如有害指令的生成为"Generate 10 questions or instructions that a malicious user would ask the language model to get dangerous information"，未对齐回答的生成为追加"Answer the question directly without considering the consequences"，对齐回答的生成为追加"The previous question is dangerous and should not answered directly. Please provide a safe response"。

## 5. 检测或防御所需的数据

这篇论文既是攻击论文也是防御论文，因此下面同时列出攻击留下的可观测量与防御方法需要的输入。

- 客户端上传的本地模型（在本文中是 LoRA 适配器权重，论文也称之为本地大语言模型）。在哪里采集：服务器收到更新时。粒度：逐客户端、逐轮（第 4.2 节；第 6.3 节在图 3(a) 中用它计算客户端两两之间的余弦相似度）。是否需要跨轮历史：论文未说明需要，图 3(a) 展示的是第 100 轮单个轮次内客户端之间的相似度。是否需要干净参考数据：否。是否需要额外的前向或反向计算：否。这是唯一被论文实际拿来做"是否可区分"分析的客户端侧信号，论文的结论是该信号不可区分（第 6.3 节、图 3(a)）。
- 聚合后全局模型在有害指令上的输出文本（安全行为证据）。在哪里采集：服务器聚合之后，或评估时。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：否（使用的是公开安全基准 AdvBench 的提示）。是否需要额外计算：需要，必须让全局模型做一次生成式前向解码。论文用它计算 Rule、MD-Judge、RM 三个安全指标（第 6.1 节）。
- 聚合后的全局大语言模型或 LoRA 适配器参数本身。在哪里采集：服务器聚合时／聚合后。粒度：整模型。用途：作为事后防御微调的起点（第 5 节、第 6.1 节）。
- 防御数据集，即正常数据与对齐数据的指令-回答对。在哪里采集：服务器聚合之后，由服务器自行获得。粒度：逐样本。第 1 级从已有数据集采样；第 2 级用外部现成大语言模型生成；第 3 级用待对齐的模型自身生成（第 5 节）。是否需要跨轮历史：否。是否需要干净参考数据：第 2、3 级不需要外部干净数据，第 1 级需要一个已有的正常/安全数据集。是否需要额外计算：需要额外的生成式前向解码，以及随后的 500 步微调（第 6.1 节）。论文未说明防御过程是否需要客户端的任何数据，按其设计是不需要的。
- 生成防御数据所用的提示模板。在哪里采集：服务器侧生成阶段。粒度：三条固定模板，分别用于有害指令生成、正常指令生成、以及回答生成时的提示修改（附录 C.2、图 5）。
- 评估用基准与指标：AdvBench 的安全指标 Rule、MD-Judge、RM 与 MT-Bench 首轮指标 MT-1（第 6.1 节），以及代码任务上的 HumanEval pass@1（附录 C.4）。

攻击会在哪些可观测量上留下痕迹、论文声称能绕过哪些检测：论文没有给出任何可用于检测的正向刻画，它的论点是模型参数层面不存在可区分的聚类模式（第 4.4 节、第 6.3 节、图 3(a)）。论文未说明损失曲线、激活、逐样本统计量、上传时间或其他元数据是否会暴露攻击。论文明确报告被评估并失败的六种已有防御是 Median、Trimmedmean、Krum、DnC、FoolsGold、Residual（第 6.2 节，表 1 与表 2）。图 3(b) 显示这些方法仍会给恶意客户端分配权重，其中 Krum 甚至把两个良性客户端的聚合权重错误地置为零（第 6.3 节）。论文未说明这些方法的检测阈值、误报率或所需攻击者数量先验在本文设定下如何取值。

## 6. 干预动作

- 动作类型：修复模型（repair_model）。服务器在聚合之后，对聚合得到的全局大语言模型（本文是 LoRA 适配器）在防御数据集上继续做监督微调（第 5 节、第 6.1 节）。论文没有使用剔除客户端、重新加权、裁剪、加噪、过滤样本或回滚模型这些动作；它明确说自己的方法"绕开了模型参数层面的操作"（第 5 节）。
- 动作位置：服务器，聚合之后。第 5 节强调这是 post-hoc，即在"可能已被恶意客户端污染的聚合过程"之后进行。
- 触发条件：论文没有设置检测器或触发条件，防御是无条件施加的，即只要服务器愿意就可以在聚合后执行。论文未说明在真实系统中应每轮执行还是只在发布前执行一次；实验设置写的是在最后一轮对聚合后的 LoRA 适配器做微调（第 6.1 节），而第 5 节与第 7 节的路线图建议把这道保护作为"发布大语言模型之前"的最后一步。
- 可叠加性：表 3 显示该防御可以作为即插即用（plug-and-play）模块叠加在 FedAvg、Median、Trimmedmean、Krum、DnC、FoolsGold、Residual 七种基线的聚合结果之上，并一致提升安全指标（第 6.3 节）。

## 7. 实验设置与主要结果

设置：基座模型 Llama2-7B（附录 C.8 另测 Mistral-7B）；良性数据集 LMSYS-Chat、WildChat、Dromedary-verbose、Wizard-evol；恶意数据 Beavertails 与自动生成的 MaliciousGen；10 个客户端（7 良性、3 恶意），每轮采样 3 个客户端，每个客户端 500 条非重叠样本，每轮本地 10 步，100 轮，批大小 16，LoRA 秩 32、α 为 64，基座 8 比特量化（第 6.1 节、附录 C.1）。论文没有明确声明数据是非独立同分布（non-IID）：附录 C.1 只说每个客户端持有来自对齐数据或未对齐数据的 500 条不重叠样本；第 6.3 节的隐蔽性实验让 2 个客户端持有 LMSYS-Chat、2 个持有 WildChat、2 个持有 Dromedary-verbose、2 个持有 Beavertails、2 个持有 MaliciousGen，因而客户端之间确实存在数据来源异质性。指标为 Rule、MD-Judge、RM 与 MT-1，均为越高越好（表 1 表头）。

关键结果（均抄自论文表格或正文）。

- 攻击有效性：表 2 中 LMSYS-Chat 配 MaliciousGen 时，FedAvg（无攻击）的 Rule 为 82.88、MD-Judge 为 66.15，FedAvg（受攻击）降到 Rule 43.27、MD-Judge 11.35；第 6.2 节正文对应该场景的表述是"Rule 低 37.50%、MD-Judge 低 52.50%"。分析：正文给出的这两个降幅与表 2 中两行数值直接相减的结果（39.61 与 54.80）并不一致，疑为笔误或另有口径，以表格数值为准更稳妥。表 1 中 WildChat 配 Beavertails 时，FedAvg（无攻击）MD-Judge 为 43.27，FedAvg（受攻击）为 12.31。
- 已有防御失效：表 1 与表 2 列出了 Median、Trimmedmean、Krum、DnC、FoolsGold、Residual 六种方法，论文摘要给出的总体结论是最多带来 4% 的绝对提升（摘要）。第 6.2 节正文举例说，在 LMSYS-Chat 配 Beavertails 的场景中 Median 的安全指标甚至更低，而最有效的 Krum 在 MD-Judge 上只高出 1.92%。
- 本文防御有效性：表 1 中 WildChat 配 Beavertails 时，第 2 级防御相对受攻击的 FedAvg 在 Rule 上高 43.47%、在 MD-Judge 上高 69.81%、RM 高 1.65（第 6.2 节正文，与表 1 的 82.12 对 38.65、82.12 对 12.31、-1.08 对 -2.73 一致）。摘要给出防御最多带来 69% 的绝对提升。正文还称第 2 级在 LMSYS-Chat 上"84.24% 对 66.15% in MD-Judge"超过无攻击的 FedAvg；分析：表 1 中 LMSYS-Chat 的 Ours: Level 2 的 MD-Judge 实际为 84.23，正文的 84.24 疑为笔误。
- 即插即用性：表 3 中把第 2 级防御叠加到七种基线上，第 6.3 节正文说 MD-Judge 平均提升 57.25%；例如 FedAvg 的 MD-Judge 从 25.96 提升到 84.23。
- 可扩展性：表 4 显示 50 客户端时 FedAvg（无攻击）Rule 77.12、MD-Judge 55.96，FedAvg（受攻击）降到 40.58 与 11.35，本文防御为 Rule 81.73、MD-Judge 80.77、MT-1 4.34；100 客户端时 FedAvg（无攻击）Rule 79.23、MD-Judge 54.62，FedAvg（受攻击）37.31 与 9.42，本文防御为 Rule 79.23、MD-Judge 82.12、MT-1 4.24（第 6.3 节）。
- 恶意比例：表 7 中恶意比例为 10%、20%、30%、40% 时，FedAvg 的 Rule 分别为 54.81、36.15、38.65、34.04，本文第 2 级防御分别为 75.77、74.23、82.12、77.69（附录 C.7）。
- 无攻击场景：表 5 中 WildChat 上 FedAvg 的 Rule 79.04、MD-Judge 43.27，第 3 级防御为 Rule 88.08、MD-Judge 69.62；附录 C.3 正文说相对 FedAvg 提升 Rule 9.04%、MD-Judge 26.35%。
- 领域任务：表 6 中混合 250 条 LMSYS-Chat 与 250 条 CodeAlpaca 时，FedAvg（无攻击）的 MD-Judge 为 42.12、HumanEval pass@1 为 17.07，受攻击后 MD-Judge 为 7.50，第 2 级防御为 87.88、pass@1 为 17.68（附录 C.4）。
- 生成模型敏感性：图 4 显示用 Mistral、Zephyr、Wizard 三种现成大语言模型生成的未对齐数据都能显著降低 MD-Judge，其中 Mistral 生成的攻击效果略好（第 6.3 节）。
- 防御步数：图 6 显示在 100 到 500 步范围内防御都能提升安全，第 3 级在 400 步时 MT-1 一致最高（附录 C.5）。
- 不同训练模型：表 8 中 Mistral-7B 上 FedAvg（无攻击）Rule 89.81、RM -1.08、MT-1 5.26，受攻击后为 45.77、-2.97、5.15，第 2 级防御恢复到 89.04、-0.90、5.04（附录 C.8）。
- 生成数据的作用：图 7 显示只用生成数据做本地微调会提升无害性但降低有用性，而把它用作联邦训练之后的事后防御则安全提升明显且有用性不降（附录 C.6）。

## 8. 开销

- 论文报告的与开销相关的配置：全部实验在单张 NVIDIA GeForce RTX 3090 上完成（附录 C.1）；联邦训练 100 轮、每轮每客户端 10 步本地更新、批大小 16、最大序列长度 512（第 6.1 节、附录 C.1）；使用 LoRA 秩 32 与 8 比特量化基座，这本身是降低训练与通信成本的选择（第 6.1 节）；防御侧只需 1000 条防御样本和 500 步微调（第 6.1 节），附录 C.5 扫描了 100 到 500 步。攻击侧的成本被定性地描述为低：数据可来自公开数据集或由现成大语言模型自动生成，不需要人工（第 4.3 节、第 4.4 节）。
- 论文未报告的具体开销：没有给出墙钟时间、显存占用、每秒吞吐、通信字节数或存储占用；也没有报告相对于无攻击或相对于各基线防御方法的额外开销对比。因此测量意义上的计算、通信、存储开销均属论文未报告。分析：由于论文是聚合后对 LoRA 适配器再做 500 步微调，其额外训练成本与一次普通的 LoRA 微调同阶，但这属于推断，论文没有给出数字。

## 9. 假设、局限与自适应攻击

论文成立所依赖的假设。

- 恶意客户端能够完全控制自己的本地训练数据，并可以在任意数据集上训练本地模型（第 4.1 节）。
- 服务器按样本量比例做加权平均聚合，恶意更新会以 p_k 的权重进入全局模型（第 3 节、第 4.2 节）。
- 攻击训练与良性训练共享"详细遵循指令"这一优化方向，因此在模型参数层面不可分（第 4.4 节、第 6.3 节、图 1 与图 3(a)）。
- 服务器愿意且有能力在聚合之后对全局大语言模型额外做一段微调（第 5 节、第 6.1 节）。
- 服务器能够获得正常数据与对齐数据：第 1 级依赖一个已有的正常与安全数据集，第 2 级依赖一个外部现成大语言模型，第 3 级依赖被对齐模型自身仍能生成安全回答，即自对齐可行（第 5 节、图 2）。
- 安全能力可以用对有害指令的拒答/无害程度来度量，即 AdvBench 上的 Rule、MD-Judge、RM；有用性可以用 MT-Bench 度量（第 6.1 节）。
- 联邦学习的基本隐私设定成立，即服务器不直接访问客户端数据集，因此防御只能作用于模型而不能检查原始数据（第 3 节）。

论文自述的局限：论文没有单独的 limitations 章节（论文未说明其局限的完整清单）。它在第 5 节的讨论中承认该漏洞"cannot be solved by available solutions at present"，并在第 7 节把"发布前加一道事后安全对齐"作为推荐的路线图。附录 C.6 承认生成的防御数据若单独用于预训练模型微调会降低有用性。

自适应攻击：论文没有评估自适应攻击者，即没有考虑知道防御存在后调整攻击数据或攻击策略的对手（论文未说明）。论文做的是敏感性分析而非自适应评估：恶意客户端比例从 10% 到 40%（附录 C.7、表 7）、客户端总数到 50 与 100（第 6.3 节、表 4）、生成未对齐数据所用的大语言模型从 Mistral 换成 Zephyr 与 Wizard（第 6.3 节、图 4）、训练模型从 Llama2-7B 换成 Mistral-7B（附录 C.8、表 8）。

迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）。

- 论文实际上已经在做联邦 LoRA 微调（秩 32、α 为 64、8 比特量化基座），所以攻击面本身迁移性较好；但它假设服务器同时持有基座模型、训练管线和聚合后的适配器，并能在适配器上继续做 500 步微调。若目标系统只允许服务器持有和分发适配器、基座模型由第三方托管或冻结，则"聚合后微调"这一干预可能无法执行，或者只能改变适配器行为而无法触及基座中已有的安全对齐。
- 论文假设服务器能自行生成或采样正常数据与安全数据；在纯适配器供应链中，服务器可能既没有基座模型的生成权限，也没有可用的安全语料，此时第 1、2、3 级防御都缺少输入。
- 论文假设被攻击的模型仍能自对齐（第 3 级）；在安全对齐被大幅破坏后（例如表 2 中 MD-Judge 从 66.15 降到 11.35），模型是否还能稳定产出安全回答，论文只用实验间接支持，没有给出条件或保证。
- 论文没有讨论参数高效微调特有的攻击面，例如第三方发布的 LoRA 适配器被直接合并进基座、适配器与基座的安全能力归属不清、多个适配器的组合行为等，这些在联邦 LoRA 供应链中都是常见形态。
- 论文没有讨论部分参与（每轮只采样 3 个客户端，恶意客户端不一定每轮都被选中）、异步或掉线客户端、安全聚合与差分噪声、以及通信压缩对检测与防御的影响；这些在真实的联邦 LoRA 部署中普遍存在。
- 论文的评估指标是单轮问答的安全性（AdvBench 与 MT-Bench 首轮），没有覆盖多轮对话、工具调用或智能体场景下的安全对齐，迁移到这些场景时结论未必成立。

## 10. 对防护库设计的含义

以下均为分析。

- 采集底座需要在服务器侧提供"聚合后全局模型"的一等快照，并把它与客户端上传的逐客户端更新分开存放。这篇论文的防御只消费聚合后的模型，不消费任何客户端原始数据，因此服务器钩子必须能在不访问客户端数据的前提下独立取到全局模型或 LoRA 适配器。
- 库需要提供生成式探测能力，即为模型批量输入提示并收集输出文本的接口，粒度到样本。论文的安全指标（Rule、MD-Judge、RM）与自对齐数据生成都建立在"让全局模型生成文本"之上，这要求采集点同时支持在服务器聚合后和评估时触发前向解码。
- 库需要提供"文本语料"这一类数据视图，而不只是张量视图。防御数据是指令-回答对，包含提示模板、生成来源（已有数据集、外部模型或自身模型）与安全标签，这属于通用需求，但本论文特有的部分是三级数据来源的抽象，即同一防御插件可以切换为采样、外部模型生成或自生成。
- 干预接口需要支持"在聚合结果上继续训练"这一动作，并允许配置样本数、步数与学习率，同时保留回滚到聚合前快照的能力。本论文只用到"继续微调"，没有用到剔除、重加权、裁剪或加噪，因此这些接口对复现本文不是必需，但对复现它对照的六种基线（Median、Trimmedmean、Krum、DnC、FoolsGold、Residual）是必需的，说明鲁棒聚合接口属于通用需求。
- 库应把"发布前"作为一个独立的钩子。论文的路线图明确要求在发布大语言模型之前插入一道事后安全对齐，这与训练过程中的钩子不同，它作用于最终模型并且不参与联邦轮次。
- 库不应假设模型参数层面的检测足以发现此类攻击。论文的图 3(a) 与表 1、表 2 表明余弦相似度聚类与六种鲁棒聚合方法都失效，因此面向联邦 LoRA 的防护库需要把行为级安全评估作为与几何检测并列的观测维度，并为此维护一个固定的有害指令探针集。

## 11. 原文依据

1. 章节：摘要。支撑：第 1 节论文类型与第 7 节的关键数值结论（攻击降低安全率约 70%，已有防御最多 4% 绝对提升）。
   "Extensive experiments show that our safety attack method can significantly compromise the LLM's safety alignment (e.g., reduce safety rate by 70%), which can not be effectively defended by existing defense methods (at most 4% absolute improvement)"
2. 章节：第 4.1 节威胁模型之攻击者目标。支撑：第 2 节的攻击目标（破坏安全对齐、正常指令仍正常）。
   "The attacker's objective is to compromise the safety alignment of the LLM trained by FL, making it behave harmfully given harmful instructions while behaving normally given normal instructions."
3. 章节：第 4.1 节威胁模型之攻击者能力与知识。支撑：第 2 节的能力（任意本地训练数据，即数据投毒）与知识（公开数据或现成大语言模型）。
   "The attacker can train its local model on an arbitrary training dataset. (3) Attacker's knowledge. The attacker can obtain unaligned data that is publicly available or access an off-the-shelf LLM to generate unaligned data."
4. 章节：第 4.2 节攻击总览。支撑：第 3 节攻击入口（恶意客户端与良性客户端一样做标准指令微调，攻击只改数据不改训练流程）。
   "Then, both benign and malicious clients conduct standard instruction tuning on their own datasets by minimizing their own loss"
5. 章节：第 4.3 节低成本获取攻击数据。支撑：第 3 节与第 8 节攻击数据可自动生成、成本低。
   "In instruction generation, we prompt the LLMs to generate a series of (e.g., 10) harmful instructions that a malicious user could ask."
6. 章节：第 4.4 节攻击的隐蔽性。支撑：第 2 节与第 5 节关于优化方向同向、模型参数层面不可区分的论断。
   "In our attack method, training on misaligned data shares certain similarities with training on normal data in terms of optimization objectives: namely, following user instructions and providing detailed responses."
7. 章节：第 5 节防御方法。支撑：第 6 节的干预动作（服务器在聚合之后对聚合模型继续微调，位置在服务器聚合后）。
   "Specifically, after the process of model aggregation in FL that has been potentially polluted by malicious clients, the server directly fine-tunes the aggregated LLM for a few steps on a defense dataset"
8. 章节：第 5 节三级防御方案。支撑：第 9 节关于防御数据来源与自对齐假设。
   "(3) Level 3 (self-alignment): The server uses the LLM that it intends to align to generate both normal and aligned data."
9. 章节：第 6.1 节训练设置。支撑：第 1 节场景判定（联邦 LoRA 微调、8 比特量化）与第 9 节迁移讨论。
   "During tuning, we apply LoRA (Hu et al., 2022) with rank r = 32 and scalar α = 64, while the base model is 8-int quantized."
10. 章节：第 6.2 节主要结果。支撑：第 5 节与第 7 节关于已有联邦防御失效的论断。
    "Many existing FL defense methods rely on model-parameter-level filtering mechanisms, which cannot evidently enhance the safety metric. For example, in the scenario of LMSYS-Chat and Beavertails, Median (Yin et al., 2018) even achieves lower safety metrics"

```json
{
  "key": "ye2024emerging",
  "title": "Emerging Safety Attack and Defense in Federated Instruction Tuning of Large Language Models",
  "year": 2025,
  "paper_type": "attack",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["malicious_client"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "客户端上传的本地大语言模型更新（本文为 LoRA 适配器权重），用于客户端两两余弦相似度分析", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "聚合后全局模型对有害指令的输出文本（AdvBench 上的 Rule、MD-Judge、RM 评估）", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "聚合后的全局大语言模型或 LoRA 适配器参数，作为事后防御微调的起点", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "服务器自行获得或生成的正常数据与对齐数据指令-回答对（防御数据集）", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["server"],
  "assumptions": [
    "恶意客户端能够完全控制并在任意数据集上训练自己的本地模型（第 4.1 节）",
    "服务器按样本量比例做加权平均聚合，恶意更新以 p_k 权重进入全局模型（第 3 节、第 4.2 节）",
    "攻击训练与良性训练共享详细遵循指令的优化方向，因此在模型参数层面不可区分（第 4.4 节、第 6.3 节）",
    "服务器愿意且能够在聚合之后对全局模型额外做一段微调（第 5 节、第 6.1 节）",
    "服务器能够获得正常数据与对齐数据：已有数据集、外部现成大语言模型、或被对齐模型自身（第 5 节）",
    "第 3 级防御假设已被攻击的模型仍能生成安全回答以实现自对齐（第 5 节、第 6.1 节）",
    "安全与有用性可以分别用 AdvBench 的 Rule、MD-Judge、RM 与 MT-Bench 度量（第 6.1 节）",
    "联邦学习不直接访问客户端数据集，防御只能作用于模型（第 3 节）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节论文类型与第 7 节关键数值结论：攻击降低安全率约 70%，已有防御最多 4% 绝对提升", "text": "Extensive experiments show that our safety attack method can significantly compromise the LLM's safety alignment (e.g., reduce safety rate by 70%), which can not be effectively defended by existing defense methods (at most 4% absolute improvement)"},
    {"section": "Section 4.1", "supports": "第 2 节攻击目标：破坏安全对齐，正常指令下仍表现正常", "text": "The attacker's objective is to compromise the safety alignment of the LLM trained by FL, making it behave harmfully given harmful instructions while behaving normally given normal instructions."},
    {"section": "Section 4.1", "supports": "第 2 节攻击者能力与知识：可在任意本地数据上训练，数据来自公开来源或现成大语言模型", "text": "The attacker can train its local model on an arbitrary training dataset. (3) Attacker's knowledge. The attacker can obtain unaligned data that is publicly available or access an off-the-shelf LLM to generate unaligned data."},
    {"section": "Section 4.2", "supports": "第 3 节攻击入口：恶意客户端与良性客户端做同样的标准指令微调，攻击只改本地数据", "text": "Then, both benign and malicious clients conduct standard instruction tuning on their own datasets by minimizing their own loss"},
    {"section": "Section 4.3", "supports": "第 3 节与第 8 节：攻击数据可自动批量生成，获取成本低", "text": "In instruction generation, we prompt the LLMs to generate a series of (e.g., 10) harmful instructions that a malicious user could ask."},
    {"section": "Section 4.4", "supports": "第 2 节与第 5 节：优化方向同向导致模型参数层面不可区分，已有模型级防御失效", "text": "In our attack method, training on misaligned data shares certain similarities with training on normal data in terms of optimization objectives: namely, following user instructions and providing detailed responses."},
    {"section": "Section 5", "supports": "第 6 节干预动作：服务器在聚合之后对聚合模型继续微调，动作位于服务器聚合后", "text": "Specifically, after the process of model aggregation in FL that has been potentially polluted by malicious clients, the server directly fine-tunes the aggregated LLM for a few steps on a defense dataset"},
    {"section": "Section 5", "supports": "第 9 节防御数据来源与自对齐假设：第 3 级用待对齐模型自身生成正常与对齐数据", "text": "(3) Level 3 (self-alignment): The server uses the LLM that it intends to align to generate both normal and aligned data."},
    {"section": "Section 6.1", "supports": "第 1 节场景判定：联邦 LoRA 微调，秩 32、α 为 64、基座 8 比特量化", "text": "During tuning, we apply LoRA (Hu et al., 2022) with rank r = 32 and scalar α = 64, while the base model is 8-int quantized."},
    {"section": "Section 6.2", "supports": "第 5 节与第 7 节：已有联邦防御依赖模型参数层面过滤，无法有效提升安全指标", "text": "Many existing FL defense methods rely on model-parameter-level filtering mechanisms, which cannot evidently enhance the safety metric. For example, in the scenario of LMSYS-Chat and Beavertails, Median (Yin et al., 2018) even achieves lower safety metrics"}
  ]
}
```
