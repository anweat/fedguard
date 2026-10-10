# ye2024fedllmbench：FedLLM-Bench: Realistic Benchmarks for Federated Learning of Large Language Models

## 1. 基本信息
- **场景**：联邦大模型微调（federated learning of large language models，FedLLM）。论文研究的不是传统联邦学习（图像分类等），也不是集中式大模型训练，而是"多方在不直接共享原始数据的前提下协同微调大语言模型"这一范式；同时它属于参数高效微调（parameter-efficient fine-tuning，PEFT）场景，因为所有实验都用 LoRA（low-rank adaptation）。论文标题、摘要与第 1 节把这一范式记作 FedLLM。
- **训练阶段**：两段任务。(1) 联邦指令微调（federated instruction tuning），即监督微调（supervised fine-tuning）；(2) 联邦偏好对齐（federated preference alignment），用直接偏好优化（direct preference optimization，DPO）。论文第 3.1 节明确写 FedLLM 包含四个迭代步骤：服务器下发模型、本地模型训练、客户端上传模型、全局模型聚合。
- **论文类型**：基准或平台（benchmark）。论文没有提出任何攻击、检测或防御算法；唯一的防护性组件是在第 4.2 节与附录 D 中作为探索性实验加入的用户级差分隐私（user-level differential privacy，UDP）。
- **模型与数据规模**：指令微调用 Llama2-7B（第 4 节"Experimental setups"），偏好对齐用 Alpaca-7B；基座模型做 8-bit 量化，LoRA 秩为 16。四个数据集（表 1）：Fed-Aya 共 38 个客户端、25,513 条样本；Fed-ChatbotIT 共 237 个客户端、6,166 条样本；Fed-WildChat 共 100 个客户端、52,703 条样本；Fed-ChatbotPA 共 747 个客户端、9,508 条样本。客户端数量范围为 38 到 747。论文实现 8 种训练方法（本地训练加 7 种联邦基线）、6 个评测指标。
- **发表信息**：arXiv:2406.04845v1，2024 年 6 月 7 日，标注为 Preprint. Under review；作者来自上海交通大学、清华大学、上海人工智能实验室。

## 2. 威胁模型
- **攻击者**：论文未说明。FedLLM-Bench 是基准论文，全文没有定义恶意客户端、恶意服务器、数据提供方或适配器发布者，也没有给出攻击者占比、能力、知识或目标。论文中出现的"恶意"相关讨论只有对数据本身安全性的说明：附录 B.5 说明基础数据集已做过安全与隐私筛查，但 Fed-ChatbotIT、Fed-ChatbotPA 与 Fed-WildChat 可能包含不安全或有毒内容，并且是刻意保留的，以便用于 AI 安全研究。
- **防御者**：论文没有以"防御者"身份讨论任何角色。若从聚合流程理解，服务器是聚合本地模型的一方，客户端持有本地私有数据；论文第 3.1 节与第 4 节只描述了 FedAvg、FedProx、SCAFFOLD、FedAvgM、FedAdagrad、FedYogi、FedAdam 这些优化型基线，它们的目标是应对数据异构与加速收敛，不是抵御攻击。
- **服务器能看到什么、信任什么**：论文未明确说明。可以确认的可观测量是：服务器聚合的是客户端上传的本地模型（在本文设置下即 LoRA 参数），而不是原始数据；附录 D.3 说明在差分隐私实验中，噪声是在"本地客户端把本地模型上传到服务器时"加入的。论文未说明服务器是否为诚实但好奇（honest-but-curious）、是否可能与客户端合谋、是否使用安全聚合（secure aggregation），也未给出任何针对恶意更新的检测或剔除机制。
- **隐私目标**：第 4.2 节与附录 D 的目标是用户级差分隐私，即保证单个用户在统计数据中的不可区分性。附录 D.1 给出 (ε, δ)-差分隐私定义。论文未说明该隐私保证针对哪一类具体对手（外部观察者、服务器还是其他客户端）。

## 3. 攻击入口与流程位置
- 本文没有攻击，因此不存在攻击入口。论文未说明任何位置的投毒、后门、越狱或隐私攻击方法。
- 论文定义的联邦流程本身就构成四个信任边界（第 3.1 节）：服务器到客户端下发模型、本地模型训练、客户端到服务器上传模型、全局模型聚合。这是本论文唯一与"入口"相关的结构性内容，可作为投毒防护库挂钩子的位置参照。
- 论文中唯一会改变上传内容的机制是用户级差分隐私，它作用在**更新上传前的客户端后处理**这一位置：附录 D.3 写明"当本地客户端把本地模型上传到服务器时，我们加入由 σ 谨慎控制的高斯噪声"（原文见第 11 节）。噪声加在本地模型（LoRA 参数）上，之后才进入服务器聚合。
- 服务器聚合阶段，论文只实现了不同的聚合规则以处理数据异构与加速收敛，没有在聚合时做任何筛选、裁剪、剔除或信誉判断。第 3.1 节把 FedAvgM、FedAdagrad、FedYogi、FedAdam 归为"在模型聚合部分引入模型动量来更新全局模型"。
- 评估与部署阶段只做测量与报告，没有防御动作。第 3.4 节列出 6 个评测指标。

## 4. 方法原理
本论文的方法原理是"构造逼真的联邦数据集 + 统一训练与评测协议"，而不是某种攻防算法。

- **数据集构造（第 3.2 节）**：四个数据集都按真实用户身份自然切分，而不是人为地把集中式数据集切开。
  - Fed-Aya：来自 Aya 多语言指令数据集，选 6 种高资源语言（英语、西班牙语、法语、俄语、葡萄牙语、中文）和 2 种低资源语言（标准阿拉伯语、泰卢固语）；按标注者 ID 过滤掉贡献少于 100 条标注的标注者，最终 38 个客户端、共 2.5 万条样本。
  - Fed-ChatbotIT：来自 Chatbot-Arena-Conversations；把每条样本的指令与用户选择的回复拼成指令—回复对；按标注者用户 ID 过滤掉贡献少于 10 条的标注者，得到 237 个客户端、共 6 千条样本。
  - Fed-WildChat：来自 WildChat 人机对话日志；按 IP 地址把数据划成用户数据集，过滤掉少于 200 条样本的用户，得到 100 个客户端、共 5.3 万条样本，包含多轮交互。
  - Fed-ChatbotPA：同样来自 Chatbot-Arena-Conversations，用于偏好对齐；过滤掉贡献少于 5 对偏好数据的用户，得到 747 个客户端、共 1 万条样本。每条样本包括指令、偏好回复与被拒回复。
- **任务与训练（第 3.1 节）**：指令微调把每条样本当作指令—回复对，用监督微调训练模型遵循指令；偏好对齐用 DPO 让模型对齐偏好回复。两个任务都用 LoRA 降低联邦学习中的计算与通信需求。
- **数据多样性刻画（第 3.3 节与附录 B）**：语言分布（图 1a）、指令与回复长度（图 1b，用 Llama2 分词器计数）、指令根动词分布（图 2 与图 7、图 9 至图 12，用 Berkeley Neural Parser 按 Self-Instruct 的做法解析）、数据质量（图 3，用 IFD 指标，由预训练 Llama2-7B 计算，逐样本打分后按客户端平均）、句向量与 t-SNE 可视化（图 4，用 OpenAI text-embedding-ada-002 抽取特征）、数据量分布（图 5）、长度偏好与质量偏好（图 1c、图 1d，在 Fed-ChatbotPA 上分别计算偏好回复更长的比例与偏好数据与被拒数据的平均质量差）。
- **差分隐私机制（附录 D.2、D.3）**：采用用户级差分隐私与高斯机制。机制输出等于真实函数输出加上零均值高斯噪声，噪声协方差为 σ²I；敏感度 Δr 定义为相邻数据集上输出差的最大 L2 范数。σ 的计算式在抽取文本中排版错乱，只能确认其中包含每轮客户端采样比例 q、联邦通信轮数 N、ln(1/δ)、ε 与一个 δ_l 项，且论文明确给出 δ_l = 2ηC|D|/|n|，其中 η 是学习率、C 是梯度的最大值、|D| 是数据集大小、|n| 是客户端数。论文还说明：用 (ε, δ) 表达时 ε 越小隐私预算越小、隐私越好、性能通常越低；用 σ 表达时 σ 越大隐私越好、性能通常越低。
- **评测协议（第 3.4 节与附录 C.2）**：4 个开放式指标（MT-Bench、Vicuna bench、AdvBench、Ref-GPT4）与 2 个封闭式指标（MMLU、HumanEval）。Ref-GPT4 的做法是随机抽 50 条未见样本作测试集，给定参考答案让 GPT-4 给生成回复打分，提示模板见图 8，评分区间为 1 到 10。
- **进一步探索（第 4.2 节）**：语言协作结构上用 FedSamLang（同语言客户端之间做 FedAvg）与 FedSimLang（按语系把语言分成 5 组后组内 FedAvg）与全局 FedAvg、本地训练对比；并首次在 FedLLM 上报告差分隐私结果。

## 5. 检测或防御所需的数据
本节需要先说明：论文没有检测算法。以下逐项列出论文实际涉及的可观测量与用户级差分隐私机制所需输入。

**(1) 客户端上传的本地 LoRA 增量（本地模型参数）**
- 是什么：客户端本地训练后的模型参数，在本论文设置下即 LoRA 适配器参数。
- 在哪里采集：客户端训练后、上传前（附录 D.3：噪声正是在这一刻加入的）。
- 粒度：逐客户端、逐轮。
- 跨轮历史：论文未说明需要历史。
- 干净参考数据或根数据集：不需要。
- 额外前向或反向计算：需要，因为要对输出做裁剪与加噪，并且 σ 的标定依赖梯度上界 C。
- 其他客户端的数据：不需要直接获取原始数据，但需要全局量（见下一项）。

**(2) 用于标定噪声强度 σ 的全局配置量**
- 是什么：每轮客户端采样比例 q、联邦通信轮数 N、客户端数 |n|、数据集大小 |D|、学习率 η、梯度最大值 C（附录 D.3）。
- 在哪里采集：论文未说明 σ 由服务器还是客户端计算；这些量是全局训练配置，而不是从某个客户端的数据中读出的。
- 粒度：逐轮（q、N）与全局（|n|、|D|、η、C）。
- 跨轮历史：需要总轮数 N 与采样率 q 这类全局计划信息，但不是更新历史的统计量。
- 干净参考数据：不需要。
- 额外计算：不需要前向或反向，只是数值计算。
- 其他客户端的数据：需要客户端总数与整体数据规模这类汇总信息，不需要其他客户端的原始数据。

**(3) 逐客户端的数据统计视图**
- 是什么：每个客户端的样本数量、指令与回复的 token 长度、语言、指令根动词分布、句向量、偏好比例、质量偏好差（第 3.2、3.3 节与附录 B.1 至 B.4）。
- 在哪里采集：论文把这些统计作为数据集刻画给出，没有说明是在客户端本地计算还是由基准作者在集中式原始数据上离线计算。若迁移到真实联邦部署，这些视图对应的采集点是客户端训练前。
- 粒度：逐样本计算后按客户端聚合（图 3 的说明明确写"我们对每个客户端的所有指令—回复对的 IFD 分数取平均"）。
- 跨轮历史：不需要。
- 干净参考数据或根数据集：不需要干净数据，但 IFD 需要固定的预训练模型 Llama2-7B 作为打分模型（附录 B.3）；这属于需要额外参考模型，不是需要干净数据根集。
- 额外计算：需要，IFD 需要额外的模型推理。
- 其他客户端的数据：不需要。

**(4) 逐客户端的数据质量分数（IFD）**
- 是什么：用 IFD 指标衡量的指令跟随难度，值越高表示难度越高；论文用它代表客户端数据质量。
- 在哪里采集：离线数据刻画阶段（图 3、附录 B.3）。
- 粒度：逐样本打分，再按客户端取平均。
- 其余同上项。
- 表 1 给出各数据集客户端质量均值与标准差：Fed-Aya 0.63 ± 0.28，Fed-ChatbotIT 0.67 ± 0.22，Fed-WildChat 0.79 ± 0.37，Fed-ChatbotPA 0.68 ± 0.21。

**(5) 评测期的模型输出与分数**
- 是什么：全局模型或本地模型在 MT-Bench、Vicuna bench、AdvBench、Ref-GPT4、MMLU、HumanEval 上的生成文本与分数（表 2 至表 6）。
- 在哪里采集：评估时（聚合后的全局模型）。
- 粒度：逐模型、逐轮（若每轮评测）。
- 跨轮历史：论文未说明需要历史。
- 干净参考数据：Ref-GPT4 需要 50 条未见样本及其人工参考答案（第 3.4 节），因此该项需要干净参考数据。
- 额外计算：需要，包含模型生成与 GPT-4 裁判调用。
- 其他客户端的数据：不需要。

**如果按"攻击论文"的要求写**：论文未说明任何攻击会在哪些可观测量上留下痕迹，也未声称某种攻击能绕过某种检测。论文只在附录 B.5 中说明基础数据集做过安全与隐私筛查，并刻意保留部分不安全或有毒内容用于安全研究。

## 6. 干预动作
- **差分隐私（唯一真正的防护性干预）**：在客户端上传本地模型时加入高斯噪声，使上传的更新满足用户级差分隐私。动作发生在客户端上传前，也就是"更新上传前的后处理"位置。论文没有做检测，因此不存在"检测之后"的动作。它没有做客户端剔除、重新加权、裁剪（论文只用到梯度上界 C 来标定敏感度）、样本过滤、模型修复或回滚。
- **聚合规则选择**：服务器侧可以选择 FedAvg、FedAvgM、FedAdagrad、FedYogi、FedAdam 等聚合方式，本地侧可以选择 FedProx 的正则项或 SCAFFOLD 的控制变量。论文把它们定位为应对数据异构和加速收敛的优化基线，不是针对攻击的防御动作。
- **仅报告**：评测阶段只测量并报告六个指标，不做任何修复或回滚。
- 汇总：干预位置为客户端（加噪）与服务器（聚合规则、评测报告）；对投毒防护而言，论文未提供任何检测后干预接口的参考。

## 7. 实验设置与主要结果
**模型与超参（第 4 节）**：指令微调用 Llama2-7B，学习率 2e-5，批大小 16；偏好对齐用 Alpaca-7B，学习率 1e-4，批大小 8；基座模型 8-bit 量化，LoRA 秩为 16；通信轮数取 100 或 200，每轮只采样少量客户端；大多数场景本地训练步数为 10。

**联邦配置（表 7）**：
- Fed-Aya：本地轮数 5，客户端 4/38（总数 38、每轮采样 4），本地步数 10，全局轮数 200。
- Fed-ChatbotIT：本地轮数 10，客户端 10/237，本地步数 5，全局轮数 100。
- Fed-WildChat：本地轮数 5，客户端 5/100，本地步数 10，全局轮数 100。
- Fed-WildChat（多轮）：本地轮数 20，客户端 3/50，本地步数 10，全局轮数 50。
- Fed-ChatbotPA：本地轮数 10，客户端 10/747，本地步数动态（按采样概率与数据量调整，使每个客户端的数据大约训练 3 个 epoch），全局轮数 200。

**数据是否非独立同分布**：是，且是自然产生的异构。表 1 给出四个数据集在客户端数、样本量、指令与回复长度、数据质量上的均值与标准差；图 1 至图 5 给出语言、长度、偏好、质量、数据量与嵌入的分布差异。论文第 3.3 节把这些统称为语言、质量、数量、指令、长度、嵌入、偏好等多样性。

**恶意比例**：论文未说明，因为论文不研究攻击。

**关键结果**：
- Fed-Aya（表 2，指标 Ref-GPT4，8 种语言）：平均分上 FedAvg 4.90、FedProx 4.92、SCAFFOLD 4.97、FedAvgM 4.86、FedYogi 4.73、FedAdagrad 4.75、FedAdam 4.71，本地训练各语言平均在 3.13 到 4.66 之间。论文指出多数联邦方法平均优于本地训练，但没有方法在所有语言上全面占优。
- Fed-ChatbotIT（表 3）：本地训练开放式平均 5.00，FedAvg 5.51、FedProx 5.49、SCAFFOLD 5.34、FedAvgM 5.42、FedYogi 5.44、FedAdagrad 5.48、FedAdam 5.41，论文称 FedAdagrad 综合最优；封闭式指标上 MMLU 各方法在 46.02 到 46.48 之间，HumanEval 在 13.41 到 15.85 之间。
- Fed-WildChat（表 4，单轮与多轮）：单轮 Ref-GPT4 从本地训练的 4.50 提升到 FedAvg 5.88、FedAdagrad 5.93 等；多轮上 FedAvg 在 MT-1（4.84）、MT-2（3.15）、MT-Bench（3.99）、Ref-GPT4（5.86）上都最好。
- Fed-ChatbotPA（表 5）：平均分本地训练 5.37，FedAvg 5.75、FedProx 5.78、SCAFFOLD 5.77、FedAvgM 5.79、FedYogi 5.48、FedAdagrad 5.60、FedAdam 5.52，基座模型 5.14；AdvBench 从基座模型 9.40、本地训练 11.0 提升到 FedAvg 16.2 与 SCAFFOLD 16.0。
- 多语言协作探索（表 6）：FedSamLang 平均 5.36 最高，FedAvg 5.31，FedSimLang 5.30，本地训练 4.69。
- 差分隐私（图 6 与表 8）：固定 δ = 1e-4，ε 取 {1e-3, 1e-2, 0.1, 1}。图 6 的结论是 FedAvg 在 (1e-2, 1e-4)-DP 下仍优于无 DP 的本地训练，并且论文称这是文献中首次给出 FedLLM 的差分隐私结果。表 8 在固定 σ 下报告 MT-Bench：local(813) 3.5375、local(1702) 4.0875、FedAvg 4.6875、FedDP-1e-3 4.6750、FedDP-1e-2 4.5500、FedDP-0.1 4.5375、FedDP-1 1.6875。需要说明：表 8 在抽取文本中是表头一行、数值一行，最后几个数值与列名的对应关系存在错位可能，上面按抽取顺序抄录，使用时应核对原表。

## 8. 开销
- 论文未报告计算、通信或存储开销的量化结果，没有给出时间、显存占用、通信字节数或存储占用。
- 可以确认的间接信息：实验主要在配备 24 GB 显存的 NVIDIA GeForce RTX 3090 上完成，Fed-WildChat 多轮实验在配备 48 GB 显存的 NVIDIA A40 上完成（附录 C.1）；基座模型使用 8-bit 量化、LoRA 秩为 16；论文称采用 LoRA 是为了降低联邦学习对计算和通信的需求（第 3.1 节）；差分隐私实验中批大小设为 1（附录 D.3）；表 7 给出了每轮客户端数、本地步数与全局轮数的配置，但这些是实验设置而非开销测量。

## 9. 假设、局限与自适应攻击
**方法成立所依赖的假设（论文可支撑的部分）**：
- 客户端数据可以按真实用户自然划分（标注者 ID 或 IP 地址），且客户端不共享原始数据（第 3.2 节）。
- 所有客户端共享同一基座模型，只在本地训练 LoRA 适配器，服务器可以对 LoRA 参数做加权平均（第 3.1、4 节）。
- 每轮只采样少量客户端，且客户端有足够算力在 8-bit 量化下本地微调 7B 级模型（第 4 节与表 7）。
- 用户级差分隐私的高斯机制要求 L2 敏感度有界，需要梯度上界 C、学习率 η、数据集大小 |D|、客户端数 |n|、采样比例 q 与总轮数 N 才能算出 σ（附录 D.2、D.3）。
- 开放式评测依赖 GPT-4 作为裁判，并要求有人工标注的参考答案（第 3.4 节与图 8）。

**论文自述的局限（附录 A）**：只在指令微调上用 Llama-2、在偏好对齐上用 Alpaca，需要更多工作探索更多模型系列与规模；安全对齐是 LLM 时代的重要话题，但本论文没有全面覆盖，论文把它列为有前景的未来方向。附录 B.5 另外说明部分数据集可能包含不安全或有毒内容，并刻意保留以支持 AI 安全研究。

**是否评估自适应攻击者**：论文未评估。论文没有攻击者，因此也没有自适应攻击、检测率、误报率或鲁棒性结果。这一点论文未说明的部分应按"论文未说明"处理，不能从基准结果推断任何鲁棒性结论。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）**：
- 分析：FedLLM-Bench 假设所有客户端诚实，服务器直接聚合上传的 LoRA 增量，没有任何更新校验。迁移到投毒防护场景时，这一"无攻击者"假设必须整体替换，基准本身不能提供投毒检测的评估基线。
- 分析：在秩为 16、本地只训练 5 到 10 步、基座模型 8-bit 量化的设置下（第 4 节、表 7），恶意更新与良性更新在参数空间中高度重叠，基于全参数范数或余弦相似度的检测器信噪比会明显下降，需要逐层、逐样本或跨轮历史的视图。
- 分析：数据按真实用户自然划分，意味着不存在一个覆盖全局分布的干净根数据集（各客户端语言、长度、质量、偏好都不同，图 1 至图 5）。依赖 IID 干净校准集或干净参考模型的检测方法（例如基于激活聚类的后门检测）在本基准的数据划分下前提不成立。
- 分析：每轮只采样极少数客户端（如 4/38、3/50、10/747，表 7）。逐轮客户端级投票或剔除类防御的统计功效不足，且剔除客户端会造成后续轮次数据分布进一步偏移。
- 分析：语言与领域高度异构（图 1a、图 3、图 4）。全局统一的异常阈值会把低资源语言或数据量极小的客户端判为离群，产生系统性假阳性；需要按语言或按数据量分组的阈值，或个性化判定。
- 分析：差分隐私的 σ 依赖 |D|、η 与梯度上界 C（附录 D.3），这些量在 LoRA 场景下需要重新定义到适配器参数的敏感度上，而论文没有给出 LoRA 适配器敏感度的具体处理。

## 10. 对防护库设计的含义
- 分析：采集底座可以直接以论文第 3.1 节定义的四个步骤作为钩子骨架：服务器下发、客户端训练前、客户端训练后（上传前）、服务器收到更新、服务器聚合后、评估时。这四个边界是通用的，任何联邦 LoRA 投毒防护库都需要，不是本论文特有的需求。
- 分析：本论文最有参考价值的具体采集点是"客户端上传前的完整 LoRA 增量"，因为附录 D.3 的差分隐私正是在这里加噪。库需要提供可以在上传前就地读改 LoRA 增量的客户端钩子，并允许插件返回修改后的参数；这对加噪、裁剪、投影类插件是通用需求，对本文的差分隐私插件是必需。
- 分析：差分隐私插件需要一份全局上下文视图，包含每轮采样比例 q、总轮数 N、客户端总数 |n|、各客户端数据量 |D|、学习率 η 与梯度上界 C（附录 D.3）。这类元数据是本文特有的强需求；但采样率、轮数与客户端数同样是许多基于历史统计的检测插件的通用上下文。
- 分析：数据侧插件需要客户端训练前的逐样本视图（长度、语言、指令类型、偏好比例）与逐客户端聚合质量分（IFD，附录 B.3）。论文没有说明这些统计由客户端本地计算还是由基准作者集中式计算；若要在真实联邦部署中复用，库应强制这些统计在客户端本地计算、只上报聚合结果，否则这些视图本身会成为隐私泄漏面。
- 分析：评测期需要一个只读的"仅报告"接口，输入是全局模型在六个指标上的生成文本与分数（表 2 至表 6），代价是需要模型生成与外部裁判（GPT-4）调用。这个接口是通用的评估型插件接口，但它对训练中的在线检测没有帮助，库不应把它当作实时防护信号。
- 分析：库应把防御强度作为显式配置项并逐轮记录实际使用的强度，例如差分隐私的 (ε, δ) 与对应的 σ（图 6、表 8）。同时必须注意：本论文未报告任何攻击检测率、误报率或对自适应攻击者的结果，因此它只能作为"数据与协议"的基线，不能作为"投毒检测"的性能基线。

## 11. 原文依据
1. 第 1 节（Abstract）："Federated learning has enabled multiple parties to collaboratively train large language models without directly sharing their data (FedLLM)." —— 支撑第 1 节关于论文场景是联邦大模型微调的论断。
2. 第 3.1 节："FedLLM involves four iterative steps: server-to-client model downloading, local model training, client-to-server model uploading, and global model aggregation." —— 支撑第 3 节关于四个信任边界与流程位置的论断。
3. 第 3.1 节："For both two tasks, we adopt the most commonly used parameter-efficient fine-tuning technique LoRA [58], reducing the requirements of computation and communication in FL [59, 60]." —— 支撑第 1 节关于使用 LoRA、属于参数高效微调供应链的论断，以及第 8 节关于通信与计算开销只有定性说法的论断。
4. 第 3.1 节："Following the standard baseline FedAvg [7], at the local training part, we implement FedProx [30] which applies local-global model regularization and SCAFFOLD [31] which introduces control variate to correct local gradients" —— 支撑第 6 节关于基线方法分别干预本地训练与聚合、且不是防御动作的论断。
5. 第 4 节："The number of communication rounds is set to either 100 or 200 and only a small proportion of clients are sampled for each round." —— 支撑第 7 节关于轮数与每轮只采样少量客户端的论断，以及第 9 节对逐轮客户端级检测统计功效的分析。
6. 第 3.2 节："According to the annotator ID, we filter out those who contribute less than 100 annotations, and construct Fed-Aya, which consists of 38 clients with 25k data samples in total." —— 支撑第 1 节与第 7 节关于客户端数量与数据规模、以及按真实用户自然划分的论断。
7. 第 4.1 节："From Table 2, we see that: (1) Most FL methods can outperform local training on average, indicating the effectiveness of collaboration. (2) No FL method can achieve comprehensive superiority in all languages" —— 支撑第 7 节关于 Fed-Aya 基准结果的论断，以及第 9 节关于语言异构下的论断。
8. 附录 D.3："We add Gaussian noise cautiously controlled by σ when local clients upload their local models to the server, ensuring User-level differential privacy." —— 支撑第 5 节关于唯一防护性可观测量与采集位置（客户端训练后、上传前）的论断，以及第 6 节的干预动作与位置。
9. 图 6 说明（第 4.2 节）："FedAvg with (1e−2, 1e−4)-DP still outperforms local training without DP while ensuring user-level differential privacy." —— 支撑第 7 节关于差分隐私实验结果的论断。
10. 附录 A："Secondly, safety alignment is also an important topic in the era of LLMs, which is not comprehensively covered in our paper." —— 支撑第 9 节关于论文自述局限（安全对齐未覆盖）的论断。

```json
{
  "key": "ye2024fedllmbench",
  "title": "FedLLM-Bench: Realistic Benchmarks for Federated Learning of Large Language Models",
  "year": 2024,
  "paper_type": "benchmark",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["none"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "客户端上传前的本地 LoRA 增量（本地模型参数），用户级差分隐私噪声的作用对象", "where": "client_post_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "标定噪声强度 σ 的全局配置量：每轮采样比例 q、总轮数 N、客户端数 |n|、数据集大小 |D|、学习率 η、梯度上界 C", "where": "server_receive", "granularity": "round", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐客户端数据统计：样本数、指令与回复 token 长度、语言、指令根动词、句向量、偏好比例", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "逐客户端平均的 IFD 数据质量分（用预训练 Llama2-7B 计算）", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "全局模型在 MT-Bench、Vicuna、AdvBench、Ref-GPT4、MMLU、HumanEval 上的生成文本与分数", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["add_noise", "report_only"],
  "intervention_where": ["client", "server"],
  "assumptions": [
    "客户端数据可按真实用户自然划分（标注者 ID 或 IP），客户端不共享原始数据",
    "所有客户端共享同一基座模型并只训练 LoRA 适配器，服务器可对 LoRA 参数加权平均",
    "每轮只采样少量客户端，客户端有足够算力在 8-bit 量化下本地微调 7B 级模型",
    "用户级差分隐私的高斯机制依赖 L2 敏感度有界，需要梯度上界 C、学习率、数据集大小、客户端数、采样比例与总轮数",
    "开放式评测依赖 GPT-4 作为裁判并需要人工标注参考答案",
    "所有参与客户端诚实，论文不定义也不评估恶意客户端、投毒或后门"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节：论文场景是联邦大模型微调", "text": "Federated learning has enabled multiple parties to collaboratively train large language models without directly sharing their data (FedLLM)."},
    {"section": "3.1 Training methods", "supports": "第 3 节：联邦流程的四个信任边界", "text": "FedLLM involves four iterative steps: server-to-client model downloading, local model training, client-to-server model uploading, and global model aggregation."},
    {"section": "3.1 Training methods", "supports": "第 1 节与第 8 节：使用 LoRA 且只做定性开销陈述", "text": "For both two tasks, we adopt the most commonly used parameter-efficient fine-tuning technique LoRA [58], reducing the requirements of computation and communication in FL [59, 60]."},
    {"section": "3.1 Training methods", "supports": "第 6 节：基线方法分别在本地训练与聚合处干预，且不是防御", "text": "Following the standard baseline FedAvg [7], at the local training part, we implement FedProx [30] which applies local-global model regularization and SCAFFOLD [31] which introduces control variate to correct local gradients"},
    {"section": "4 Experiments", "supports": "第 7 节与第 9 节：轮数与每轮少量客户端采样", "text": "The number of communication rounds is set to either 100 or 200 and only a small proportion of clients are sampled for each round."},
    {"section": "3.2 Descriptions of training datasets", "supports": "第 1 节与第 7 节：客户端数与数据规模、按真实用户划分", "text": "According to the annotator ID, we filter out those who contribute less than 100 annotations, and construct Fed-Aya, which consists of 38 clients with 25k data samples in total."},
    {"section": "4.1 Benchmark results", "supports": "第 7 节：Fed-Aya 基准结果与语言异构", "text": "From Table 2, we see that: (1) Most FL methods can outperform local training on average, indicating the effectiveness of collaboration. (2) No FL method can achieve comprehensive superiority in all languages"},
    {"section": "Appendix D.3 Experiment details of differential privacy", "supports": "第 5 节与第 6 节：唯一防护性可观测量与其采集、干预位置", "text": "We add Gaussian noise cautiously controlled by σ when local clients upload their local models to the server, ensuring User-level differential privacy."},
    {"section": "Figure 6 caption (Section 4.2)", "supports": "第 7 节：差分隐私实验结果", "text": "FedAvg with (1e−2, 1e−4)-DP still outperforms local training without DP while ensuring user-level differential privacy."},
    {"section": "Appendix A Limitations", "supports": "第 9 节：论文自述局限，安全对齐未覆盖", "text": "Secondly, safety alignment is also an important topic in the era of LLMs, which is not comprehensively covered in our paper."}
  ]
}
```
