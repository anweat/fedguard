# ye2024openfedllm：OpenFedLLM: Training Large Language Models on Decentralized Private Data via Federated Learning

## 1. 基本信息

- 场景：联邦大模型微调（federated LLM fine-tuning）。论文没有研究传统联邦学习（federated learning, FL）中的图像分类任务，也没有研究集中式大模型训练，而是研究在分散的私有数据上通过联邦学习微调大语言模型（large language model, LLM），并明确使用参数高效微调（parameter-efficient fine-tuning, PEFT）中的 LoRA（low-rank adaptation）。论文原文把整体定位概括为"federated instruction tuning"与"federated value alignment"两个应用（摘要、第 3 节）。
- 训练阶段：LLM 预训练之后的两个阶段，即指令微调（instruction tuning）与价值对齐（value alignment）。论文在第 2.1 节明确说明，预训练通常需要高算力且不适用于 LoRA 这类参数高效微调技术，因此本文只关注后两个阶段。价值对齐采用直接偏好优化（direct preference optimization, DPO）而非基于人类反馈的强化学习（reinforcement learning from human feedback, RLHF），理由在第 3.3 节给出：RLHF 需要先训练奖励模型且训练不稳定。
- 论文类型：基准或平台（benchmark/platform）。论文提出的是框架与代码库 OpenFedLLM，加上覆盖 7 个联邦学习算法、8 个训练数据集、30 多个评测指标的实证研究（摘要、第 1 节贡献、表 1）。论文不是攻击论文，也不是检测或防御论文。
- 模型与数据规模：联邦指令微调使用预训练的 Llama2-7B，并以 int8 量化；联邦价值对齐使用一个在过滤后的 WizardLM 数据上训练、尚未注入人类价值的无审查指令跟随模型（第 4.1 节）。基座模型参数量为 6738M，可训练且每轮通信的参数量为 4.194M，占总参数的 0.06%（表 3）。论文共使用 8 个训练数据集（表 2），例如 Alpaca 为 52k 样本、Alpaca-GPT4 为 52k、FinGPT 为 77k、MedAlpaca 为 34k、Code-Alpaca 为 20k、MathInstruct 为 225k、UltraFeedback 为 62k、HH-RLHF 为 161k（表 2）；具体实验中各任务实际使用的是其子集，例如通用任务为 20k、金融任务为 10k、医疗任务为 20k、代码任务为 20k、跨域协作每客户端 5k、UltraFeedback 为 62k、HH-RLHF 为 161k（第 4.2 节至第 4.8 节）。

## 2. 威胁模型

- 论文未给出威胁模型。全文没有形式化的攻击者定义、恶意比例、攻击目标或攻击者知识假设，也没有任何攻击实验。与安全相关的内容集中出现在第 5.4 节"Robustness and Security in FedLLM"这一未来方向讨论中，以及与隐私相关的第 5.5 节。
- 攻击者是谁：论文在第 5.4 节设想了"新的攻击者角色"（new attacker roles）与"目标与负责任相悖的恶意用户"（malicious users whose goal is against being responsible），这类用户持有"逻辑上正确但有害的数据"（logically correct yet harmful data），例如详细回答如何制造炸弹。论文没有给出这类攻击者的数量、占比或能力边界。
- 占比或数量：论文未说明。
- 能力：论文只说明恶意参与者的数据可以是有害但逻辑正确的，因此看起来与一般良性数据相似（第 5.4 节）。论文没有说明攻击者能否修改本地训练过程、上传的更新或服务器端行为。
- 知识：论文未说明。
- 目标：论文在第 5.4 节的措辞指向破坏模型的"integrity and societal impact"，即破坏模型的责任性与社会影响，属于安全对齐破坏类的设想；但论文没有把它形式化为攻击目标分类。第 5.5 节另外讨论了隐私风险，包括模型记忆训练数据、成员推断（membership inference）以及从联邦语言模型中恢复私有文本。
- 防御者是谁：论文没有指定防御者。从流程描述看，服务器是协调者，负责广播全局模型、接收各客户端上传的本地模型并按数据量加权聚合（第 3.1 节）。
- 防御者能看到什么：服务器看到的是各客户端的 LoRA 参数。论文在第 3.4 节说明，模型 θ 实际上由多个 A 与 B 矩阵组合而成，只有这组可学习参数被通信与聚合，基座模型参数被冻结且从不通信。
- 防御者信任什么：论文在第 3.1 节称，OpenFedLLM 遵循与 FedAvg 相同的训练流程，以便与安全聚合（secure aggregation）和差分隐私（differential privacy）等标准联邦协议兼容。论文在第 5.4 节指出，已有的鲁棒方法大多在全参数训练与图像分类任务上验证，它们在 FedLLM 中是否有效"remains unclear"。
- 分析：论文把"逻辑正确但有害的客户端数据"识别为 FedLLM 的新攻击面，但没有提供任何可操作的检测判据，因此本文只能为防护库提供威胁叙述与系统流程约束，不能提供威胁模型参数。

## 3. 攻击入口与流程位置

- 论文没有提出攻击，因此不存在论文意义上的攻击入口。论文在第 5.4 节的设想中，恶意行为通过客户端的本地数据进入系统，也就是"本地数据准备"与随之发生的"本地训练过程"这一侧；论文没有讨论上传前后处理、服务器聚合、全局模型下发、评估与部署等位置的攻击。
- 论文对正常流程的位置定义很清楚（第 3.1 节）：整个过程共 T 个通信轮，每一轮 t 包含四个关键步骤，第一步是服务器把全局模型 θt 广播给所有可用客户端 St，第二步是每个可用客户端 k 从全局模型 θt 出发在其本地数据集 Dk 上执行 τ 步随机梯度下降（stochastic gradient descent, SGD）得到本地模型，第三步是每个可用客户端 k 把本地模型上传给服务器，第四步是服务器聚合本地模型并更新全局模型。论文给出的聚合规则是 θt+1 等于被选中客户端本地模型按权重 pk 的加权和，其中 pk 等于该客户端数据集大小除以被选中客户端数据集大小之和。
- 论文还指出了框架内两个可插入改动的位置（第 3.1 节）：在第二步加入本地模型与全局模型之间的 ℓ2 正则项即可实例化 FedProx，在第四步引入服务器端动量或自适应即可得到 FedOPT。论文在第 2.2 节补充说，FedProx 正则化本地模型与全局模型的距离，SCAFFOLD 引入控制变量（control variate）修正本地梯度，FedAvgM 与 FedOPT 引入动量，FedNova 与 FedDisco 修改聚合权重。
- 分析：若把第 5.4 节的设想落到本库的流程位置上，攻击入口应标记为本地数据与本地训练；论文没有给出任何服务器端或上传后处理的攻击入口。

## 4. 方法原理

- 核心思想：在保留原始数据不出本地的条件下，让多个数据持有方协作微调同一个 LLM，通过 LoRA 只训练与通信极少量参数，从而让单个客户端可以在消费级显卡上参与训练（第 1 节、第 3.4 节）。
- 统一流程：OpenFedLLM 采用与 FedAvg 相同的四步迭代流程（第 3.1 节）。论文强调，要支持指令微调或价值对齐，只需把第二步的本地损失替换为相应的损失函数。
- 联邦指令微调（federated instruction tuning, FedIT）：每个客户端持有一组指令与真实回答的配对样本，样本用提示模板（prompt template）格式化，本地训练只在回答部分施加监督。论文给出的第 i 个样本的损失是回答各 token 条件概率连乘的负对数，即 Li 等于负的、对 j 从 1 到 ni 的 p(yi_j 给定 xi 与 yi_<j 以及本地模型 θ) 连乘取对数，其中 xi 与 yi 是两个 token 序列，ni 是回答长度，优化变量是客户端 k 在第 t 轮第 r 次迭代的本地模型（公式 1，第 3.2 节）。
- 联邦价值对齐（federated value alignment, FedVA，论文称 FedDPO）：每个客户端的样本由指令、偏好回答与非偏好回答三元组构成，本地使用 DPO 损失，即在期望意义下对 logistic 函数作用量取负对数，该作用量为 β 乘以偏好回答的对数概率比再减去 β 乘以非偏好回答的对数概率比，概率比以当前模型 πθ 与固定参考策略模型 πθ* 的比值计算；β 是控制偏离参考模型程度的超参数（公式 2，第 3.3 节）。论文说明该损失的第一项鼓励输出接近偏好回答，第二项惩罚输出接近非偏好回答，同时约束本地模型不偏离初始参考策略模型，参考模型在整个联邦过程中固定，并用指令微调后的模型初始化。
- 参数高效微调：论文把基座模型的某个权重矩阵记为 W，其更新写成 W 加 ∆W 等于 W 加 AB，其中 A 与 B 是低秩矩阵，秩 r 远小于矩阵维度（第 3.4 节）。论文称框架也支持 Prefix-Tuning、P-Tuning 与 IA3，但更倾向 LoRA，因为它可训练参数少且不引入额外推理延迟。
- 联邦算法：论文集成了 7 个代表性算法，即 FedAvg、FedProx、SCAFFOLD、FedAvgM、FedAdagrad、FedYogi、FedAdam（第 4.1 节），并另设不使用协作的本地训练作为参照。

## 5. 检测或防御所需的数据

论文没有提出任何检测或防御算法，因此不存在"方法所需的输入"。下面逐项列出论文描述中实际存在、且可被防护库采集底座利用的数据流；这些数据在论文中的用途只是训练与评测，论文没有把它们用于检测。

- 每个客户端上传的 LoRA 增量参数。内容是可训练的低秩矩阵 A 与 B，也就是论文所说的模型 θ，它由多个 A 与 B 组合而成；采集位置是服务器收到更新时，对应流程第三步；粒度是逐客户端、逐层、逐轮；论文未说明需要跨轮历史；不需要干净参考数据；不需要额外的前向或反向计算；不需要其他客户端的数据即可单独查看（第 3.1 节、第 3.4 节）。表 3 给出每轮通信的可训练参数量为 4.194M。
- 服务器聚合后的全局模型。内容是第四步加权聚合得到的全局 LoRA 参数；采集位置是服务器聚合后；粒度是逐轮的整体模型；论文未说明需要跨轮历史、干净参考数据或额外计算（第 3.1 节）。
- 客户端本地训练样本。指令微调时是"指令与真实回答"配对，价值对齐时是"指令、偏好回答、非偏好回答"三元组；采集位置是客户端训练前；粒度是逐样本；不需要历史、干净参考或额外计算（第 3.2 节、第 3.3 节、图 2、图 3）。
- 客户端每步的本地训练损失。指令微调时是公式 1 的监督微调损失，价值对齐时是公式 2 的 DPO 损失；采集位置是客户端每步；粒度是逐样本（公式 1 定义为第 i 个样本的损失）；不需要额外计算（第 3.2 节、第 3.3 节）。
- DPO 所需的固定参考策略模型输出。内容是参考模型 πθ* 对偏好与非偏好回答的对数概率，参考模型在联邦过程中固定并以指令微调模型初始化；采集位置是客户端每步；粒度是逐样本；需要参考模型，按本表格的口径记为需要干净参考；会带来额外的参考模型前向计算（第 3.3 节）。分析：这是参考模型而非干净参考数据，本库若照搬该字段，应把"参考模型/根数据集"与"干净样本集"分开建模。
- 每轮的客户端采样记录与聚合权重。内容是每轮被选中的客户端集合 St 以及各客户端数据集大小 |Dk|，服务器据此计算权重 pk；采集位置是服务器聚合时；粒度是逐客户端、逐轮；不需要历史、干净参考或额外计算（第 3.1 节）。表 10 列出了各实验的客户端采样配置，例如通用任务为 20 个客户端中每轮采样 2 个、金融任务为 50 个中采样 5 个、医疗任务为 20 个中采样 2 个、代码任务为 10 个中采样 2 个、价值对齐两个任务均为 5 个中采样 2 个。
- 评估阶段的输出文本。论文用模型对同一个问题的回答做案例研究，例如表 13 至表 16 分别展示推理问题、医疗问题、金融情感问题与有害问题的回答；采集位置是评估时；粒度是逐样本；不需要历史、干净参考或额外计算（附录 A.3，表 13 至表 16）。
- 攻击会在哪些可观测量上留下痕迹、以及论文声称能绕过哪些检测：论文没有做这类分析。论文只在第 5.4 节声称，恶意数据"could be logically correct"并且"making it look similar to general benign data"，因此这种隐蔽性使检测与缓解特别困难；论文同时指出既有鲁棒方法多在全参数模型与图像分类任务上验证，在只有少量参数被微调、任务为语言任务的 FedLLM 中是否适用尚不清楚。论文没有报告任何绕过实验或检测成功率。

## 6. 干预动作

- 论文没有检测后的干预动作，因为论文没有检测器。论文中出现的"动作"都属于联邦优化本身的机制，而不是对恶意行为的响应。
- 客户端侧的机制：FedProx 在本地损失中加入本地模型与全局模型之间的 ℓ2 正则项，SCAFFOLD 用控制变量修正本地梯度（第 2.2 节、第 3.1 节）。位置在客户端本地训练过程。
- 服务器侧的机制：FedAvgM、FedAdagrad、FedYogi、FedAdam 在服务器端引入动量或自适应（第 2.2 节、第 4.1 节）；FedNova 与 FedDisco 修改聚合权重（第 2.2 节）。位置在服务器聚合。
- 隐私相关的潜在动作：第 5.5 节提出差分隐私作为经典方案，对模型梯度或更新加入受控噪声以提供理论隐私保证，也提出限制每个客户端的训练数据量或引入非私有数据以降低私有数据被模型暴露的频率。论文把这写成未来的潜在方案，没有实现，也没有报告实验。
- 论文未说明任何剔除客户端、重新加权以对抗恶意方、裁剪、过滤样本、修复或回滚模型的动作。

## 7. 实验设置与主要结果

- 通用设置（第 4.1 节）：基座模型为 7B LLM，用 int8 量化；每轮每个可用客户端训练 10 步，使用 AdamW 优化器，学习率按轮索引采用余弦调度，最大序列长度 512。联邦指令微调在一块 NVIDIA GeForce RTX 3090 上进行，基座为预训练 Llama2-7B，共 200 个通信轮，第一轮初始学习率 5e-5，最后一轮学习率 1e-6，批大小 16，LoRA 秩为 32、缩放系数 α 为 64，使用 Alpaca 模板。联邦价值对齐在一块 NVIDIA A100 上进行，基座为在过滤后 WizardLM 数据上训练的无审查指令跟随模型，共 100 个通信轮，初始学习率 5e-4，最后一轮学习率 1e-5，批大小 32，LoRA 秩为 8、α 为 16，使用 Vicuna 模板。联邦价值对齐表格中的结果基于模型被微调 1,000 步梯度下降（表 9 表注）。
- 客户端划分与是否非独立同分布：论文第 4.1 节说明两种跨客户端划分，第一种是把一个数据集随机切分给多个客户端，客户端数据同源；第二种是把一个数据集分配给一个客户端，客户端数据不同源。第 4.6 节明确说该实验展示了客户端数据异构时联邦学习仍然有效。第 4.7 节明确说该联邦价值对齐实验中客户端数据集是独立同分布切分（IID split）。其余各节未逐一声明独立性。
- 通用域指令微调（第 4.2 节，表 4）：训练数据为 Alpaca-GPT4，客户端总数为 20，每轮随机采样 2 个可用客户端，共 20k 样本；评测包含 MMLU、BBH、DROP、HumanEval、CRASS 以及 Vicuna-Bench 和 MT-Bench。所有联邦方法都优于本地训练，其中 FedYogi 与 SCAFFOLD 表现较好。关键数值：本地训练 MMLU 为 38.70，FedAvg 为 45.13，FedYogi 为 45.79；HumanEval 上本地训练为 9.15，SCAFFOLD 为 17.68；MT-Bench 平均分上本地训练为 2.844，FedAvg 为 3.346，SCAFFOLD 为 3.488，FedAvgM 为 3.456（表 4）。论文在贡献列表中称在通用数据集上 MT-Bench 有至少 12% 的提升（第 1 节贡献 3）。
- 金融域指令微调（第 4.3 节，表 5）：训练数据为 FinGPT 情感分析数据集，客户端总数为 50，每轮采样 5 个，共 10k 样本；评测为 FPB、FIQA-SA、TFNS、NWGI，指标为准确率与 F1。结论是联邦方法优于 GPT-4、GPT-4 优于 GPT-3.5、GPT-3.5 优于本地训练，SCAFFOLD 最好。关键数值：本地训练在四个数据集平均（Avg:4）上准确率为 0.699，FedAvg 为 0.791，SCAFFOLD 为 0.807；GPT-4 在三个数据集平均（Avg:3）上为 0.731。论文称在 Avg:4 上 FedAvg 相对本地训练提升 11.5%（第 4.3 节）。
- 医疗域指令微调（第 4.4 节，表 6）：训练数据为 MedAlpaca，客户端总数为 20，每轮采样 2 个，共 20k 样本，模型在第 100 轮评测。本地训练平均分为 0.398，FedAvg、FedProx、FedAdagrad 平均分为 0.446，FedAdam 在 9 个指标中的 4 个上最好（表 6）。
- 代码域指令微调（第 4.5 节，表 7）：训练数据为 CodeAlpaca，客户端总数为 10，每轮采样 2 个，共 20k 样本；报告 11 个指标。MBPP 上本地训练为 0.168，FedAdagrad 为 0.244；HumanEval 上 FedAvg 为 0.165，FedAdagrad 为 0.183（表 7）。FedAdagrad 在 11 个指标中的 6 个上最好。
- 跨域协作（第 4.6 节，表 8）：4 个客户端分别持有通用、数学、代码、金融数据，每个客户端 5k 样本，使用 FedAvg。FedAvg 平均排名为 1.4，最好；Client2 排名为 2.0，Client4 排名为 3.0。FedAvg 在金融上 F1 为 0.805，而完全用金融数据训练的 Client4 为 0.834（表 8）。
- 有益性价值对齐（第 4.7 节，表 9 左）：训练数据为 UltraFeedback，客户端总数为 5，每轮采样 2 个，共 62k 样本，每个样本由一个指令与四个不同模型的回答构成，得分最高的回答作为偏好回答，其余三个中随机一个作为非偏好回答。基座模型 MMLU 为 36.85，本地训练为 36.02，FedAvg 为 37.14，SCAFFOLD 为 38.58；MT-Bench 平均分上基座为 4.050，本地训练为 4.346，FedAvg 为 4.516。
- 无害性价值对齐（第 4.8 节，表 9 右）：训练数据为 HH-RLHF，客户端总数为 5，每轮采样 2 个，共 161k 样本；评测包含 HHH 无害性分数、AdvBench 有害问题拒绝率以及 MT-Bench 有益性。HHH 上基座为 67.24，本地训练为 74.14，FedAvg 为 75.86，FedAvgM 为 77.59；AdvBench 拒绝率上基座为 15.58，本地训练为 31.35，FedAvg 为 39.04，SCAFFOLD 为 44.81，FedAvgM 为 42.88。论文称 FedAvgM 与 SCAFFOLD 在 HH-RLHF 上整体最好（表 9 表注与第 4.8 节）。
- 表 1 给出与同类框架的对比：FATE-LLM 不支持指令微调与价值对齐、支持 1 个联邦算法、1 个训练数据集、4 个评测指标；Shepherd 支持指令微调、1 个算法、1 个数据集、1 个指标；FederatedScope-LLM 支持指令微调、1 个算法、3 个数据集、3 个指标；OpenFedLLM 同时支持指令微调与价值对齐、7 个算法、8 个训练数据集、30 多个指标（表 1）。

## 8. 开销

- 论文报告了可训练与通信参数量：基座模型参数量为 6738M，可训练参数量为 4.194M，每轮通信参数量为 4.194M，即总参数的 0.06%（表 3 及其表注）。第 3.4 节称可学习参数 θ 相对基座模型少于 1%，并称 LoRA 不引入额外推理延迟。
- 论文报告了硬件与时间量级：在第 1 节关键观察中称，通过联邦学习训练 LLM 只需要一块 GPU，100 个通信轮下每个客户端耗时 1 到 2 小时；第 5.6 节也称，借助 8 比特量化与 LoRA，训练可以在一块消费级 GPU 上执行。
- 论文未报告逐轮通信字节数、峰值显存占用、存储开销、检测或防御带来的额外开销。第 5.6 节把效率列为未来方向，并提到 QLoRA 的 4 比特量化有潜力支持更大模型。
- 分析：表 3 的 4.194M 参数量只说明通信对象的规模，不含优化器状态、激活值或参考模型前向的开销；对防护库而言，这些是缺失的数据。

## 9. 假设、局限与自适应攻击

- 流程假设：方法假设联邦流程就是 FedAvg 的四步迭代，即服务器广播全局模型、客户端本地训练、客户端上传本地模型、服务器按数据量加权聚合（第 3.1 节）。论文明确说采用与 FedAvg 相同的流程是为了兼容安全聚合与差分隐私等标准协议。
- 参数假设：假设只微调 LoRA 的低秩矩阵 A 与 B，基座模型参数冻结且从不通信（第 3.4 节、表 3）。
- 数据假设：假设每个客户端持有私有的指令微调数据或偏好数据，原始数据不上传（摘要、第 3.2 节、第 3.3 节）；假设服务器可以知道每个客户端的数据集大小以计算聚合权重（第 3.1 节）。
- 价值对齐假设：假设参考策略模型 πθ* 在整个联邦过程中固定，并用指令微调后的模型初始化（第 3.3 节）。
- 参与方假设：论文在第 5.4 节之外没有讨论恶意参与方，正文实验默认所有客户端是良性协作者。第 4.6 节的跨域实验假设客户端数据来自不同领域但都是可用的良性数据。
- 论文自述的局限与未来方向：第 5.1 节指出，在联邦场景下没有单一方能看到完整数据集，因此基于阈值或排序的数据选择方法难以确定合适的阈值或排名，且客户端之间的数据质量差异比集中式更明显。第 5.2 节指出客户端价值偏好异质会妨碍训练一个统一的价值模型。第 5.3 节指出常规联邦学习在客户端自身专家领域上可能不如本地训练。第 5.4 节指出以往鲁棒方法多在全参数模型和图像分类任务上验证，在 FedLLM 中只微调少量参数且任务是语言任务，其有效性未知，并且逻辑正确但有害的数据使检测与缓解特别困难，甚至未被任何 FL 算法在所有场景中占据优势（第 1 节关键观察 3）。
- 是否评估了自适应攻击者：论文没有评估任何攻击者，也没有评估自适应攻击者。相关讨论只出现在第 5.4 节的未来方向中。
- 分析：这篇论文本身就是联邦 LoRA 微调，而不是"需要从传统联邦学习或集中式训练迁移"的工作，因此第 9 节的迁移讨论重点在于"检测能力"而不是"是否使用 LoRA"。以下几类假设在把本论文的系统作为防护库宿主时可能不成立：
  - 分析：论文假设服务器可以获知每个客户端的数据集大小 |Dk| 并用它做聚合权重，这在真实跨机构联邦中往往属于敏感信息，防护库若依赖该权重做异常判定，需要额外设计不泄露数据量的替代视图。
  - 分析：论文假设客户端在每轮只上传 LoRA 参数，且基座模型冻结。这一假设使服务器侧可观测面缩小到低秩矩阵，会削弱依赖全参数梯度统计的传统鲁棒聚合方法的信号量；论文自己也在第 5.4 节承认这一差距。
  - 分析：论文的价值对齐实验明确说明客户端数据是独立同分布切分、只有 5 个客户端且每轮采样 2 个（第 4.7 节）。在这种设置下攻击面很小，恶意客户端的占比与轮次覆盖都受限制，因此论文的实验结论不能直接外推到大规模、非独立同分布、存在持续恶意参与者的联邦 LoRA 场景。
  - 分析：论文讨论的差分隐私方案是"对梯度或更新加噪"（第 5.5 节），加噪会直接削弱基于范数或相似度的投毒检测信号，防护库在接入差分隐私时必须把隐私预算与检测阈值联动考虑，这一点论文未涉及。
  - 分析：论文讨论的恶意数据形态是"逻辑正确但有害"的文本，这类样本在逐样本损失、梯度范数等常规可观测量上可能没有明显异常。论文没有给出任何检测指标，因此不能假定论文描述的采集点足以支撑检测。
  - 分析：论文所有实验都在单机单卡或单卡环境完成（第 4.1 节），没有涉及跨机构网络、异步到达、掉线重连、客户端动态加入退出等真实联邦条件，防护库在这些条件下的采集时序论文未说明。

## 10. 对防护库设计的含义

- 分析：采集底座必须原生支持"服务器收到更新时"的视图，且该视图的粒度要同时覆盖逐客户端、逐层与逐轮。论文明确只有 LoRA 的低秩矩阵 A 与 B 被上传，基座参数从不通信（第 3.4 节、表 3），因此服务器侧的默认可观测量不是全参数梯度，防护库不能假设存在传统联邦学习里的完整梯度张量。
- 分析：采集底座需要在"服务器聚合时"额外暴露每轮的客户端采样集合与聚合权重来源，因为论文的聚合规则以数据集大小占比为权重（第 3.1 节）。这是一个通用需求，也是本论文特有的约束，因为真实部署中这两个量常常不可得或不可信。
- 分析：客户端钩子至少要能覆盖三类数据：训练前的样本视图（指令与回答对，或指令、偏好回答、非偏好回答三元组）、每步的逐样本损失（公式 1 与公式 2）、以及训练后的 LoRA 增量。论文本身只把这些量用于训练，但它们是本库做逐样本过滤或损失异常检测时唯一有论文依据的客户端内部可观测量。
- 分析：插件机制需要把"参考模型"作为可与"干净参考数据"区分开的一等资源。论文的 DPO 损失依赖一个固定参考策略模型 πθ*（公式 2，第 3.3 节），它既不是干净样本集也不是根数据集，若库把它建模成 needs_clean_reference 的布尔量会丢失语义。
- 分析：干预接口如果只提供传统鲁棒聚合中的剔除、裁剪与加噪，可能与本论文的系统设定冲突。论文指出只有少量参数被微调、任务是语言任务，既有鲁棒方法是否有效未知（第 5.4 节），并指出框架刻意与安全聚合和差分隐私兼容（第 3.1 节）；因此干预接口应当至少能表达"仅报告"与"服务器聚合层面的重新加权"，并允许插件声明其与安全聚合、差分隐私的兼容性约束。
- 分析：评测与部署阶段的采集点应被独立建模，因为本论文的安全相关证据全部来自输出文本层面的评测（表 9 的 HHH 与 AdvBench、表 13 至表 16 的回答案例），而这类视图需要模型生成能力，成本与训练期视图不同，属于本库中"高成本、低频次"的采集通道。

## 11. 原文依据

1. 第 3.1 节；支撑第 3 节关于流程位置与第 2 节关于服务器视野的论断。
   "The overall process takes T communication rounds, where each round t consists of four key steps. (1) The server broadcasts the global model θt to all available clients St"
2. 第 3.1 节；支撑第 3 节与第 6 节关于可在第二步和第四步插入机制的论断。
   "For instance, we only need to add another ℓ2-based regularization term between local and global models at Step 2 to instantiate FedProx [49] and introduce server-side momentum or adaptivity at Step 4 to recover FedOPT [54]."
3. 第 3.4 节；支撑第 5 节关于服务器可观测对象是 LoRA 低秩矩阵的论断。
   "denote W ∈Rd×m as one weight matrix of the base model, its update is denoted as W+∆W = W+AB, where A ∈Rd×r, B ∈Rr×m, and r ≪min(d, m)."
4. 第 3.4 节；支撑第 5 节与第 8 节关于通信对象是多个 A 与 B 组合、参数量小于 1% 的论断。
   "Therefore, in our OpenFedLLM framework, the model θ is actually the composition of multiple A and B. In this way, the number of learnable parameters θ could be less than 1% compared to the base model"
5. 表 3 表注；支撑第 8 节关于 0.06% 参数量与基座模型从不通信的论断。
   "The majority of model parameters falls on the base model, which is freezed and never communicated. Only 0.06% of the total model parameters are trainable and communicated (per round)."
6. 第 4.1 节；支撑第 7 节关于模型量化、每轮步数与优化器的论断。
   "we use 7B LLM as the base model, which is quantized by int8 for computation efficiency. For each round, each available client trains for 10 steps using AdamW [72] optimizer."
7. 第 4.7 节；支撑第 7 节与第 9 节关于价值对齐实验数据为独立同分布切分、客户端数很少的论断。
   "On the last four open-ended benchmarks, FedAvg [20] performs the best, which is not a surprising finding since the client number is relatively few and the client datasets are IID split."
8. 第 5.4 节；支撑第 2 节与第 9 节关于论文只把恶意参与者作为未来方向、未建模的论断。
   "Secondly, new attacker roles with malicious yet stealthy data emerge in FedLLM, making it unclear whether existing defense methods are still applicable [114, 115, 116, 117]."
9. 第 5.4 节；支撑第 5 节关于论文未提供检测判据、只声称有害数据与良性数据相似的论断。
   "Despite being harmful, attackers' data could be logically correct (e.g., answering how to make a bomb with details), making it look similar to general benign data (e.g., answering how to build a house)."
10. 第 5.4 节；支撑第 9 节关于既有鲁棒方法在全参数与图像任务上验证、在 FedLLM 中未知的论断。
    "Firstly, previous methods often work with full-parameter model training and testified in image classification tasks [112, 113], while in FedLLM, only a small proportion of parameters are fine-tuned during training and the tasks are on language"

```json
{
  "key": "ye2024openfedllm",
  "title": "OpenFedLLM: Training Large Language Models on Decentralized Private Data via Federated Learning",
  "year": 2024,
  "paper_type": "benchmark",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["none"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {
      "what": "每个客户端上传的 LoRA 增量参数（低秩矩阵 A 与 B，即被通信与聚合的模型 θ）",
      "where": "server_receive",
      "granularity": "layer",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "服务器聚合后的全局 LoRA 参数（第 t+1 轮全局模型）",
      "where": "server_post_aggregate",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "客户端本地样本：指令与真实回答对，或指令、偏好回答与非偏好回答三元组",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "客户端每步的本地训练损失（公式 1 的监督微调损失或公式 2 的 DPO 损失）",
      "where": "client_step",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "DPO 使用的固定参考策略模型 πθ* 对偏好与非偏好回答的对数概率",
      "where": "client_step",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "每轮被选中的客户端集合与各客户端数据集大小（聚合权重 pk 的来源）",
      "where": "server_aggregate",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "评估阶段模型对固定问题的输出文本（案例研究中的回答）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "联邦流程为 FedAvg 的四步迭代：服务器广播全局模型、客户端本地训练、客户端上传本地模型、服务器按数据集大小加权聚合（第 3.1 节）。",
    "框架遵循与 FedAvg 相同的流程，以便与安全聚合和差分隐私等标准联邦协议兼容（第 3.1 节）。",
    "只训练与通信 LoRA 的低秩矩阵 A 与 B，基座模型参数冻结且从不通信（第 3.4 节、表 3）。",
    "每个客户端持有私有的指令微调数据或偏好数据，原始数据不上传（摘要、第 3.2 节、第 3.3 节）。",
    "服务器可获知每个客户端的数据集大小以计算聚合权重（第 3.1 节）。",
    "价值对齐中参考策略模型在整个联邦过程中固定，并用指令微调后的模型初始化（第 3.3 节）。",
    "联邦价值对齐实验中客户端数据集为独立同分布切分，且客户端总数只有 5、每轮采样 2 个（第 4.7 节）。",
    "实验默认所有参与客户端为良性协作者；恶意参与者只在第 5.4 节的未来方向中被提及，未建模也未评估。"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {
      "section": "3.1",
      "supports": "第 3 节：论文对联邦训练流程四个步骤与服务器广播位置的定义",
      "text": "The overall process takes T communication rounds, where each round t consists of four key steps. (1) The server broadcasts the global model θt to all available clients St"
    },
    {
      "section": "3.1",
      "supports": "第 3 节与第 6 节：可在本地训练步骤和服务器聚合步骤插入机制",
      "text": "For instance, we only need to add another ℓ2-based regularization term between local and global models at Step 2 to instantiate FedProx [49] and introduce server-side momentum or adaptivity at Step 4 to recover FedOPT [54]."
    },
    {
      "section": "3.4",
      "supports": "第 5 节：服务器可观测的通信对象是 LoRA 低秩矩阵",
      "text": "denote W ∈Rd×m as one weight matrix of the base model, its update is denoted as W+∆W = W+AB, where A ∈Rd×r, B ∈Rr×m, and r ≪min(d, m)."
    },
    {
      "section": "3.4",
      "supports": "第 5 节与第 8 节：被通信的模型由多个 A 与 B 组成，参数量少于基座的 1%",
      "text": "Therefore, in our OpenFedLLM framework, the model θ is actually the composition of multiple A and B. In this way, the number of learnable parameters θ could be less than 1% compared to the base model"
    },
    {
      "section": "Table 3 caption",
      "supports": "第 8 节：每轮可训练且通信的参数占 0.06%，基座参数从不通信",
      "text": "The majority of model parameters falls on the base model, which is freezed and never communicated. Only 0.06% of the total model parameters are trainable and communicated (per round)."
    },
    {
      "section": "4.1",
      "supports": "第 7 节：基座模型为 7B 并做 int8 量化，每轮每客户端训练 10 步并使用 AdamW",
      "text": "we use 7B LLM as the base model, which is quantized by int8 for computation efficiency. For each round, each available client trains for 10 steps using AdamW [72] optimizer."
    },
    {
      "section": "4.7",
      "supports": "第 7 节与第 9 节：价值对齐实验的客户端数据为独立同分布切分且客户端数很少",
      "text": "On the last four open-ended benchmarks, FedAvg [20] performs the best, which is not a surprising finding since the client number is relatively few and the client datasets are IID split."
    },
    {
      "section": "5.4",
      "supports": "第 2 节与第 9 节：论文只把恶意参与者与隐蔽有害数据作为未来挑战，未建模未评估",
      "text": "Secondly, new attacker roles with malicious yet stealthy data emerge in FedLLM, making it unclear whether existing defense methods are still applicable [114, 115, 116, 117]."
    },
    {
      "section": "5.4",
      "supports": "第 5 节：论文未给出检测判据，只声称有害数据与良性数据外观相似",
      "text": "Despite being harmful, attackers' data could be logically correct (e.g., answering how to make a bomb with details), making it look similar to general benign data (e.g., answering how to build a house)."
    },
    {
      "section": "5.4",
      "supports": "第 9 节：既有鲁棒方法在全参数与图像分类任务上验证，在 FedLLM 中的有效性未知",
      "text": "Firstly, previous methods often work with full-parameter model training and testified in image classification tasks [112, 113], while in FedLLM, only a small proportion of parameters are fine-tuned during training and the tasks are on language"
    }
  ]
}
```
