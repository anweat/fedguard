# sun2024ffalora：Improving LoRA in Privacy-Preserving Federated Learning

## 1. 基本信息

- **论文标题与出处**：Improving LoRA in Privacy-Preserving Federated Learning，发表于 ICLR 2024（论文首页标注 "Published as a conference paper at ICLR 2024"），arXiv 编号 2403.12313v1（2024 年 3 月 18 日）。作者为 Youbang Sun（Northeastern University，工作完成于阿里实习期间）、Zitao Li、Yaliang Li、Bolin Ding（Alibaba Group）。
- **场景**：联邦大模型微调（federated large language model fine-tuning），并且是参数高效微调（parameter-efficient fine-tuning, PEFT）中的低秩适配（Low-Rank Adaptation, LoRA）加差分隐私（differential privacy, DP）。它不是传统联邦学习（FL）图像任务论文，但附录 A.7 补充了一个视觉 Transformer（Vision Transformer）在 Food-101 上的实验。
- **训练阶段**：只涉及下游任务微调（fine-tuning）阶段，流程是"客户端用 DP-SGD 做本地更新，服务器用联邦平均（FedAvg）聚合"，不涉及预训练、也不涉及适配器发布或加载的供应链环节。
- **论文类型**：基础方法（foundation）。它提出的是一个新的联邦微调训练方法 FFA-LoRA（Federated Freeze A LoRA），隐私性来自沿用已有 DP-SGD（差分隐私随机梯度下降）机制。它既不是攻击论文，也不是检测论文，更不是针对投毒（poisoning）的防御论文；论文全篇没有出现投毒、后门或拜占庭（Byzantine）相关的威胁建模。
- **模型与数据规模**：RoBERTa-Large（355M，第 5.1 节）配 GLUE 的 MNLI、SST-2、QQP、QNLI；LLaMA-7B（第 5.3 节与附录 A.3）配 GSM-8K；视觉 Transformer 配 Food-101（第 5.3 节与附录 A.7）。实验为 3 客户端 cross-silo 联邦设置（第 5.1 节）。可训练参数量级见表 3 与表 6，例如 RoBERTa 上 LoRA（rank 8）为 1.57M（0.440%），FFA-LoRA（rank 8）为 0.79M（0.220%）（表 3）；QNLI 上 LoRA（rank 16）为 3145728（0.877%），FFA-LoRA（rank 16）为 1572864（0.440%）（表 6）。各数据集的绝对样本数论文未说明，只给出了客户端间的标签比例。

## 2. 威胁模型

- **论文建模的对手**：论文没有建模投毒者或恶意客户端。它建模的是"服务器不可信"这一隐私威胁：第 2 节明确区分两种 DP 设置，第一种假设服务器可信、只在服务器端对全局聚合更新加噪；第二种放弃可信服务器假设，要求每个客户端共享出去的更新本身已经是差分隐私的。论文采用第二种更强设置（第 2 节）。
- **对手能看到什么**：按第 2 节与附录 A.5 的表述，对手能看到客户端上传的模型参数更新（在 FFA-LoRA 中是矩阵 B）以及最终发布的全局模型。DP 保证的是这些被共享的信息不会显著泄露任何单条训练记录；最终模型自动满足 DP，依据是并行组合、序列组合与抗后处理性质（第 2 节、附录 A.5）。
- **对手的能力**：论文没有赋予对手任何主动篡改能力；它没有讨论恶意服务器篡改聚合结果、选择性回传、或恶意客户端投毒。论文未说明服务器是否被允许做自适应的、依赖数据的后处理。
- **恶意比例与数量**：论文没有设置恶意客户端比例，因为威胁模型中不存在投毒者。
- **防御者是谁、能看到什么、信任什么**：防御者实质上就是客户端自身（通过本地 DP-SGD 保护本地数据）以及系统设计者。客户端能看到自己的本地数据、自己的更新和全局模型；客户端不信任服务器持有其原始更新的安全性。被信任的部分是：服务器会诚实执行 FedAvg，客户端会诚实执行约定的 DP-SGD（裁剪阈值 C 与噪声乘子 σ）。这些"诚实执行"假设论文没有逐条明说，属于协议层面的默认前提。

## 3. 攻击入口与流程位置

这是一篇纯防御/训练方法论文，论文没有攻击，因此不存在"攻击从哪个位置进入"的答案，本节的 JSON 字段填 `none`。下面是它所针对的问题分别在流程的哪些位置进入：

- **本地训练过程（损失与优化器）**：第一个不协调（discordance 1）出现在客户端对 A 与 B 联合优化、且本地多步更新时；论文指出本地问题近似是"局部半二次"的，多步本地更新与数据异质性会带来客户端漂移（client-drift，第 3 节）。第二个不协调（discordance 2）来自在本地用 DP-SGD 时注入的高斯噪声会经过 B 与 A 的乘积被级联放大（第 3 节）。第三个不协调（discordance 3）来自缩放因子 α 在本地更新中的取值，它影响目标函数的光滑性与噪声敏感度（第 3 节）。
- **更新上传前的后处理与服务器聚合**：真正的结构性入口在"分别聚合"这一步。客户端本地联合优化 A 与 B，服务器却按 FedAvg 分别对 A 和 B 求平均，于是服务器得到的等效权重是 (B1+B2)/2 × (A1+A2)/2，而不等于理想的 (B1A1+B2A2)/2，二者之间的差就是论文所称的聚合误差项（式 3，第 3 节）。
- **服务器收到更新时与最终模型下发/评估时（隐私泄露入口）**：隐私保护的入口是客户端上传的更新以及最终发布的全局模型；论文用本地 DP-SGD 保证上传的 B 已经带噪（第 2 节、附录 A.5）。
- **FFA-LoRA 对应的应对位置**：客户端训练时只训练 B 并冻结 A0（第 4 节），上传时只传 B，服务器聚合时只平均 B，下发的等效权重为 W0 + B̄A0（式 4，第 4 节）。

## 4. 方法原理

核心思想是把 LoRA 的两组低秩矩阵中"非零初始化"的那一组冻结，只训练"零初始化"的那一组，从而在联邦场景里去掉联合优化与分别聚合之间的不匹配（摘要与第 4 节）。

- **参数化**：LoRA 把权重写成 W0 + ∆W = W0 + BA（式 1，第 3 节），其中 A 用随机高斯初始化、B 初始化为 0，乘积再乘缩放因子 α/r。FFA-LoRA 改为 W = W0 + BA0，其中 B 可训练、A0 与 W0 冻结，B 仍从 0 开始，因此训练起点仍能还原预训练模型（第 4 节）。
- **聚合一致性**：两客户端时服务器得到 W0 + (B1+B2)/2 × A0 = W0 + (B1A0 + B2A0)/2 = W+，与理想模型平均完全一致，不再有式 3 的聚合误差项（式 4，第 4 节）。
- **噪声不再级联**：LoRA 的单步 DP-SGD 更新为 W0 + (B+ξB)(A+ξA) = W0 + BA + ξBA + BξA + ξBξA，其中 ξBξA 已不是高斯分布；FFA-LoRA 只训练 B，噪声只出现在 ξBA 一项，没有乘积噪声项（第 3 节与第 4 节）。
- **不依赖 α**：定理 1（式 5）给出，当 αLoRA 趋于无穷时，LoRA 的权重轨迹收敛到 FFA-LoRA 的轨迹；因此 FFA-LoRA 等价于 α 无穷大的 LoRA，不需要再调 α（第 4 节，证明见附录 A.2）。
- **光滑性**：定理 2 声明，若 A 固定且 ‖A‖≤C，损失对 B 是 L·C² 的 Lipschitz 光滑；若 A 与 B 同时可训练，则损失函数没有 Lipschitz 光滑性保证（附录 A.1）。论文据此说可以推出与 Zhou & Cong (2017) 类似的收敛性质（第 4 节）。
- **更激进的变体**：附录 A.4 提出 QVP 适配器，把更新写成 W0 + Q0VP0，只训练中间的 r×r 矩阵 V，V 从 0 初始化，Q0 与 P0 冻结。
- **隐私结论**：推论 2.1 声明，本地运行 DP-SGD 加 FedAvg 的 FFA-LoRA 在给定采样率 q=|Bi|/|Ni|、总本地更新步数 T 与 σ = O(q√T log(1/δ)/ε) 时满足 (ε, δ)-DP，具体 σ 由 Opacus 数值计算（附录 A.5）。

## 5. 检测或防御所需的数据

论文的方法不是检测器，没有"发现异常后处理"的数据需求；下面列出方法运行与隐私保证所必需的输入。逐项说明：

- **客户端可训练低秩矩阵 B**。是什么：FFA-LoRA 中唯一被训练并上传的矩阵（LoRA 对照中则是 A 与 B 两组）。在哪里采集：客户端训练后、上传时，等价地也可以说在服务器收到更新时采集。粒度：逐客户端、逐层、逐轮。是否需要跨轮历史：聚合逻辑本身不需要。是否需要干净参考数据：不需要。是否需要额外计算：不需要。是否需要其他客户端的数据：服务器需要汇集所有参与客户端上传的 B，但那是聚合必需的共享更新，不是原始数据。
- **冻结的随机高斯矩阵 A0 与预训练权重 W0**。是什么：把 B 还原成 ΔW = B·A0 并构造全局模型 W0 + B̄A0 所必需的两块冻结参数。在哪里采集：客户端训练前（初始化时确定，整个训练过程不变）。粒度：逐层。跨轮历史：不需要。干净参考数据：不需要。额外计算：不需要。这里有一个论文未说明的点：论文只写了 A0 服从随机高斯初始化，并且式 4 直接写出服务器端 (B1+B2)/2 × A0，但**论文未说明 A0 如何分发到各客户端、如何保证各客户端与服务器持有完全相同的 A0、以及是否有一致性校验**。
- **逐样本梯度（per-sample gradient）及其范数**。是什么：DP-SGD 在每一步对每个样本的梯度做范数裁剪，裁剪阈值记为 C。在哪里采集：客户端每一步（优化器内部，梯度进入模型更新之前）。粒度：逐样本（每个 batch 内）。跨轮历史：不需要。干净参考数据：不需要。额外计算：需要，逐样本梯度比常规批梯度昂贵；论文未报告这部分的开销数值。
- **每步加入的高斯噪声与噪声乘子**。是什么：z ∼ N(0, C²σ²I_p) 形式的加性高斯噪声，以及由隐私会计决定的 σ；论文给出的 DP-SGD 形式是 ḡ = (Σ Clip(∇f_i, C) + z)/|B|（第 2 节）。在哪里采集：客户端每一步。粒度：逐批（噪声加在批梯度上）。跨轮历史：不需要。干净参考数据：不需要。额外计算：需要（生成噪声并加噪）。
- **隐私会计的输入：采样率 q、总步数 T、目标 (ε, δ)**。是什么：q = |B|/|N|，N 是客户端训练集总样本数，B 是批大小；T 是本地更新总步数；由 (q, T, ε, δ) 通过 Opacus 的矩会计算出 σ（第 2 节、第 5.1 节、附录 A.5）。在哪里采集：客户端每一步累积、跨轮累计（T 是整轮训练过程中的累计步数）。粒度：逐客户端、逐轮累计。跨轮历史：需要，这是本方法中唯一强依赖跨轮累计状态的量。干净参考数据：不需要。额外计算：需要，要运行隐私会计计算。
- **本地数据集规模 N 与批大小 B**。是什么：用于计算采样率 q，也用于 DP-SGD 的批梯度归一化。在哪里采集：客户端训练前。粒度：逐客户端。跨轮历史：不需要。干净参考数据：不需要。额外计算：不需要。
- **训练配置超参数**。是什么：秩 r、本地更新步数、通信轮数、学习率 η；α 在 FFA-LoRA 中不再需要。在哪里采集：客户端训练前。粒度：逐客户端（全局统一配置）。跨轮历史：不需要。干净参考数据：不需要。额外计算：不需要。
- **服务器聚合后的全局参数**。是什么：对 B 做 FedAvg 得到的 B̄，以及用 W0 + B̄A0 还原出的全局权重。在哪里采集：服务器聚合时与聚合后。粒度：逐层、逐轮。跨轮历史：不需要（本方法不含动量或控制变量）。干净参考数据：不需要。额外计算：需要把 B̄ 与 A0 相乘才能得到等效权重（若下游只关心 B 则不需要）。
- **评估集准确率**。是什么：GLUE 各子任务、GSM-8K、Food-101 上的准确率，是论文唯一的效用指标。在哪里采集：评估时（对聚合后的全局模型）。粒度：逐模型、逐轮（论文只报告最终或最优结果）。跨轮历史：不需要。干净参考数据：评估集本身不是检测用的干净参考数据。额外计算：需要前向推理。
- **论文用到的攻击痕迹式可观测量（本论文是防御论文，这里指它用来论证设计合理性的诊断量）**：噪声矩阵的 Frobenius 范数 ‖ξBξA‖_F 与全量微调的 ‖ξW‖_F。在哪里采集：论文只在一个合成验证里计算它（第 3 节，图 1；其中 W ∈ R^{1024×1024}，rank r = 8）。粒度：逐层。跨轮历史：不需要。额外计算：需要。
- **论文没有声明要绕过什么检测**：论文完全不涉及检测机制，因此不存在"能绕过哪些检测"的陈述。

## 6. 干预动作

论文没有检测环节，因此没有剔除客户端、重新加权、过滤样本、修复或回滚模型这类响应式动作。它的"动作"全部是训练流程内的结构性机制：

- **客户端侧裁剪**：DP-SGD 先用范数约束 C 裁剪逐样本梯度，以限制单个样本的最大影响（第 2 节）。
- **客户端侧加噪**：在裁剪梯度的和上加入高斯噪声 z ∼ N(0, C²σ²I_p)，再用噪声梯度更新模型（第 2 节）。裁剪阈值按网格 C ∈ {2, 5, 10} 选取，σ 由 Opacus 依 (q, T, ε, δ) 计算（第 5.1 节）。这两步都发生在客户端本地训练的每一步，也就是更新上传之前。
- **结构性冻结**：客户端只训练 B，A0 与 W0 全程冻结（第 4 节）；这决定了上传内容只有 B。
- **服务器侧只聚合 B**：服务器按 FedAvg 平均各客户端的 B，并用 W0 + B̄A0 构造全局模型（式 4，第 4 节）。动作发生在服务器聚合位置。
- **超参数层面**：不再对 α 做搜索，只调学习率等其他超参数（第 4 节、附录 A.6）。
- **隐私损失组合**：服务器端对上传参数的平

均被论文视为不引入额外隐私损失的后处理操作（附录 A.5）。

## 7. 实验设置与主要结果

**设置**。3 客户端 cross-silo 联邦设置（第 5.1 节），论文未说明客户端参与率或客户端采样比例。批大小 B = 200，通信轮数 1000，本地更新步数 10，序列长度 128，分类头冻结，适配器加在注意力层与前馈层，LoRA 的缩放因子 α = 8（第 5.1 节）。秩默认 r = 8；隐私参数 δ = 1e−5，ε ∈ {6, 3, 1}，裁剪阈值网格 C ∈ {2, 5, 10}；LoRA 学习率搜索集合为 {0.01, 0.02, 0.05, 0.1}，FFA-LoRA 为 {0.1, 0.2, 0.5, 1}，表 1 报告 20 次运行的均值与标准差（第 5.1 节）。数据异质性是标签偏斜构造的：二分类任务用 [0.1, 0.9]、[0.9, 0.1]、[0.5, 0.5]，三分类任务用 [0.9, 0.05, 0.05]、[0.05, 0.9, 0.05]、[0.05, 0.05, 0.9]；轻度异质性用 [0.15, 0.85]、[0.85, 0.15]、[0.5, 0.5] 与 [0.6, 0.2, 0.2]、[0.2, 0.6, 0.2]、[0.2, 0.2, 0.6]（第 5.1、5.2 节）。**恶意客户端比例：论文未设置，因为不涉及攻击者。** 指标为准确率（%）。硬件为 NVIDIA Tesla A100，半精度（第 5 节）。

**主要结果**：

- 表 1（GLUE，RoBERTa-Large，3 客户端）：无隐私时 MNLI-matched 上 LoRA 为 82.03±10.7、FFA-LoRA 为 85.05±1.1；MNLI-mismatched 82.50±10.9 对 85.62±1.0；SST-2 均为 94.32；QQP 83.51±3.3 对 84.35±0.6；QNLI 88.95±6.7 对 90.35±1.9。ε = 6 时 MNLI-matched 上 LoRA 为 39.46±14.3、FFA-LoRA 为 78.81±0.8；ε = 3 时为 35.82±8.9 对 77.42±0.8；ε = 1 时为 33.80±1.6 对 75.05±1.3。论文指出 DP 让所有任务性能显著下降，FFA-LoRA 在有无隐私时都更好，最大差距出现在异质性最强的三分类 MNLI 上。
- 表 2：i.i.d. 下 MNLI-matched 上 LoRA 86.90、FFA-LoRA 87.13；轻度异质性 87.01 对 87.04；强异质性 82.03 对 85.05。SST2 在 i.i.d. 下为 94.42 对 95.14。
- 表 3（轻度异质性、不同秩）：LoRA rank 16（3.15M，0.877%）MNLI-matched 为 87.43，FFA-LoRA rank 16（1.57M，0.440%）为 85.82；论文建议按同参数预算比较（FFA-LoRA rank 16 对 LoRA rank 8），此时 FFA-LoRA 的优势更明显。
- 表 4（QNLI，隐私预算与秩）：ε = 1 时 LoRA 在 r = 4 与 r = 2 上塌到 58.30 与 58.15，而 FFA-LoRA 为 82.06 与 82.64；ε = 1 时 LoRA r = 16 为 80.54、r = 8 为 81.45，FFA-LoRA 为 81.87 与 83.01。
- 表 7（不同 α，附录 A.6）：按学习率缩放时 LoRA 在 α = 2 为 71.88%、α = 64 为 50.96%、α = 256 为 49.46%，FFA-LoRA 对应为 91.31%、91.17%、92.46%。
- 表 6（QNLI，含 QVP）：LoRA rank 4（786432，0.220%）非隐私 91.40%、ε = 6 时 85.2%；FFA-LoRA rank 4（393216，0.110%）为 92.20% 与 86.75%；QVP rank 16（24576，0.00685%）为 83.40% 与 84.44%。
- 图 1（第 3 节）：合成实验中噪声范数随 σ 二次增长，当 σ 超过 0.5 时明显差于全量微调；正文给出的算例是 1000 轮、10 步本地更新、SST-2、批大小 200、ε = 6、δ = 1e−5 时 σ = 0.99，此时 LoRA 产生的噪声约为全量微调的 3 倍。
- 语言生成（第 5.3 节、附录 A.3）：LLaMA-7B 在 GSM-8K 上 FFA-LoRA 达到 17.12%，LoRA 最好为 15.68%（Kuang et al. (2023) 报告 15.31%）；论文未说明该组实验是否启用了 DP。
- 视觉任务（表 8，附录 A.7）：Food-101 上基线 85.39%，集中式 LoRA 86.18%，集中式 FFA-LoRA 85.83%，表中另列 FL iid LoRA 81.33% 与 FL non-iid FFA-LoRA 82.10%。
- 初始化消融（表 9，附录 A.8）：QNLI 上 Kaiming 初始化均值 91.84%、方差 0.38%；正交初始化 92.16%、0.83%；SVD 初始化（取 W0 前 r 个奇异向量）91.50%、0.59%。

## 8. 开销

- 论文报告的是相对开销：因为 A0 冻结，FFA-LoRA 的可训练参数量相对 LoRA 减半，因而在 FL 中省下一半的通信与计算成本，这一点在摘要、引言贡献列表与第 4 节重复出现；表 3 与表 6 给出了对应的参数量（例如 RoBERTa 上 rank 8 从 1.57M / 0.440% 降到 0.79M / 0.220%）。
- 论文还报告超参数搜索开销的下降：FFA-LoRA 不需要搜 α，只需搜学习率等其他超参数，避免了与 α 搜索空间大小成正比的额外通信与计算（第 3 节末尾与第 4 节）。
- 论文未报告绝对数值：没有墙钟时间、显存占用、通信字节数或每轮时延的测量；DP-SGD 逐样本梯度带来的额外计算开销也未报告。附录 A.5 只给出了隐私会计的渐近形式 σ = O(q√T log(1/δ)/ε)。
- 存储开销：论文未报告。

## 9. 假设、局限与自适应攻击

**论文成立所依赖的假设**：

- 服务器不可信，但会诚实执行 FedAvg；隐私保证覆盖共享的更新与最终模型（第 2 节、附录 A.5）。
- 所有客户端共享同一个预训练权重 W0 与同一个冻结的随机高斯矩阵 A0，B 从 0 初始化；否则式 4 的聚合恒等式不成立。
- 各客户端本地数据集是全局数据集的互不相交分片，因此可以用并行组合性质合并隐私损失（附录 A.5："disjoint chunks of the global dataset"）。
- 本地使用 DP-SGD，裁剪阈值 C 通过网格搜索确定，噪声乘子 σ 由 Opacus 矩会计按 (q, T, ε, δ) 数值计算（第 5.1 节）。
- 损失对 W 满足 Lipschitz 光滑，且冻结矩阵有界 ‖A‖≤C 时才能得到对 B 的 LC² 光滑性；"局部半二次""局部线性"的论证假设学习率足够小（第 3 节、附录 A.1）。
- 噪声不被放大的论证明确假设没有触发范数裁剪（第 3 节："Even if no norm clipping operation is triggered"）。
- FFA-LoRA 需要秩 r ≥ 1（附录 A.4 指出 LoRA 与 FFA-LoRA 的 r 不能小于 1）。
- α 无关性依赖学习率随 α 相应缩放（定理 1 与附录 A.6 的实验）。

**论文自述的局限**：

- 第 5 节开头承认其结果与集中式 PEFT 结果（Hu et al. 2021；Yu et al. 2021a）不完全一致，原因是在设置中额外引入了联邦通信/聚合与数据异质性。
- 第 4 节说"可以推出"与 Zhou & Cong (2017) 类似的收敛性质，属于由光滑性定理导出的推论，论文没有给出完整的收敛证明。
- 附录 A.4 承认 QVP 在同等参数预算下不如 LoRA 与 FFA-LoRA。
- 附录 A.8 承认不同初始化（Kaiming、正交、SVD）之间的性能差距"不足以给出确定结论"。
- 附录 A.6 承认 LoRA 在配合足够学习率时仍能收敛到高精度，只是给定 α 后寻找最优学习率很困难。

**自适应攻击**：论文没有评估任何自适应攻击者，也没有评估投毒、后门、模型替换或恶意服务器主动攻击；它甚至没有把恶意客户端纳入威胁模型。

**迁移到联邦 LoRA 微调时可能失效的假设**：

- 分析：论文本身研究的就是联邦 LoRA 微调，所以主要风险不是场景迁移，而是它的实验实例化过于特殊：3 个客户端、全部参与、cross-silo、二分类/三分类的标签偏斜异质性。真实指令微调数据的异质性通常是主题、语言、格式与分布漂移的混合，标签比例式异质性未必能代表它。
- 分析：论文要求所有客户端持有完全相同的 A0，但论文未说明 A0 的分发与版本一致性机制。在真实系统中客户端会动态加入、退出、重装或使用不同随机种子，一旦 A0 不一致，式 4 的聚合恒等式与"冻结 A 仍等价于 LoRA(α→∞)"的结论都不再成立。
- 分析：DP 保证依赖各客户端数据集互不相交（附录 A.5）。如果多个客户端共享同一批公开语料或同一用户的重复数据，并行组合定理的前提被破坏，隐私预算会被低估。
- 分析：论文只考虑被动不可信服务器，并依赖"服务器端平均是后处理"这一性质。若服务器做依赖数据的自适应回传或选择性聚合，后处理性质不覆盖这类行为，论文没有评估这种情形。
- 分析：论文未考虑恶意客户端。在 FFA-LoRA 中攻击者能操纵的只剩 B，且当启用 DP 时逐样本梯度裁剪会限制单样本影响；但这只是"可能改变投毒面"的推测，论文没有任何鲁棒性实验支持，不能把 FFA-LoRA 当作投毒防御。
- 分析：论文的效用结论在强隐私下非常悲观（表 1 中 ε = 1 时 LoRA 在 MNLI 上只有 33.80%），生成式指令微调与安全对齐任务上的可用性未经验证；GSM-8K 实验是否启用 DP 论文也未说明。

## 10. 对防护库设计的含义

- 分析：采集底座必须在客户端训练前记录"参数角色"元数据，即哪些矩阵被冻结、哪些可训练、各自的形状、初始化方式与初始化值（至少是可复现的随机种子）。本论文的方法完全建立在这一角色划分上，服务器插件若只看到一组扁平的参数增量就无法判断上传的是 B 还是 A 与 B。
- 分析：客户端钩子需要能取到逐样本梯度的范数（裁剪前）、每步写入的噪声与噪声乘子、以及隐私会计所需的采样率、累计步数与目标 (ε, δ)。这是与具体攻击无关的通用采集点，但逐样本梯度有额外计算成本，应做成可开关。
- 分析：服务器钩子需要"按参数组聚合"的能力，以及在收到更新时、聚合后、聚合完成构造全局权重时三个视图。本论文里聚合前是 B、聚合后是 B̄、全局权重需要 W0 + B̄A0 才能还原，因此库里必须能把冻结矩阵随更新一起携带或按客户端重建。通用的部分是分组聚合与轮次视图，FFA 特有的部分是"A0 在所有参与方之间完全一致且全程冻结"。
- 分析：若以后要在同一底座上做投毒检测，需要在服务器收到更新时同时拿到 B 与被冻结的 A0，才能重建等效权重增量 ΔW = B·A0 并做范数、相似度或异常打分统计；这意味着采集底座不应假设"上传的增量就是最终权重增量"。
- 分析：跨轮历史视图对隐私会计是必需的（累计 T 与 q 决定 σ），对更新级检测也常用；干净参考数据集在本论文的方法中不需要，库不应对插件强制要求它。
- 分析：干预接口需要支持客户端侧"裁剪加噪"（在梯度进入优化器之前）与服务器侧"只对指定参数组做平均"，以及"关闭缩放因子 α"这类结构开关。本论文没有检测-响应式动作，因此剔除客户端、重新加权、回滚或修复模型这些接口可以留给其他插件，不必为了支持本论文而实现。

## 11. 原文依据

1. 摘要：支撑第 4 节方法核心思想（冻结非零初始化矩阵，只训练零初始化矩阵）。
   > "The core idea of FFA-LoRA is to fix the randomly initialized non-zero matrices and only fine-tune the zero-initialized matrices."
2. 第 2 节（Different DP settings in FL）：支撑第 2 节威胁模型，即论文采用不可信服务器这一更强隐私设置。
   > "In this paper, we adopt the stronger privacy setting, ensuring that any shared information (i.e., updates of model parameters) from local clients to server satisfies DP."
3. 第 3 节（Discordance 1）：支撑第 3 节与第 6 节的流程位置，即 A 与 B 在服务器端被分别平均。
   > "However, when the server performs aggregation on the server side, A and B are averaged separately following vanilla FedAvg McMahan et al. (2017a)."
4. 第 3 节（Discordance 2）：支撑第 4 节与第 5 节关于噪声级联的可观测量与设计动机。
   > "Three terms contain noise and the third term, ξBξA, no longer follows a Gaussian distribution. This shows that noise is cascaded after the multiplication in LoRA, introducing additional difficulties for convergence in fine-tuning."
5. 第 4 节（FFA-LoRA has no extra interference with data heterogeneity and model-averaging）：支撑第 4 节聚合一致性论证。
   > "Since ∆Wi ≈BiA0 in FFA-LoRA, the update is more compatible with FedAvg and DP-SGD than LoRA."
6. 第 4 节（FFA-LoRA saves computation and communication）：支撑第 8 节开销减半的说法。
   > "Since A0 is fixed after initialization in FFA-LoRA, the total number of trainable parameters in the model is effectively halved compared to LoRA."
7. 第 5.1 节（Experiments with differential privacy guarantees）：支撑第 5 节数据需求中"隐私会计输入与 Opacus 计算 σ"。
   > "Given the sampling rate, total step number and privacy requirement ϵ, δ, we use the privacy accountant from Opacus (Yousefpour et al., 2021) to calculate the noise scale σ for all our experiments."
8. 第 5.1 节：支撑第 7 节客户端数量与数据异质性设置。
   > "All our experiments with LoRA and FFA-LoRA are run in a 3-client cross-silo federated setting. Data on clients are randomly split among all clients sampled to fit certain proportions to ensure strong data heterogeneity."
9. 第 5.3 节：支撑第 7 节语言生成任务的主要结果。
   > "Our method has achieved an accuracy of 17.12% on the task of GSM-8K, significantly better than the best performance of LoRA at 15.68% (15.31% reported in (Kuang et al., 2023))."
10. 附录 A.5：支撑第 9 节关于"本地数据集互不相交、可用并行组合"的假设。
    > "The privacy loss of all clients performing local updates can be composed by the parallel composition property of DP."

```json
{
  "key": "sun2024ffalora",
  "title": "Improving LoRA in Privacy-Preserving Federated Learning",
  "year": 2024,
  "paper_type": "foundation",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["malicious_server"],
  "attack_goal": ["privacy"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "客户端可训练低秩矩阵 B（FFA-LoRA 中唯一被训练并上传的矩阵，LoRA 对照为 A 与 B 两组）", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "冻结的随机高斯矩阵 A0 与预训练权重 W0，用于把 B 还原为 W0+B·A0", "where": "client_pre_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐样本梯度及其范数（DP-SGD 按阈值 C 裁剪）", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "每步加入的高斯噪声 z、噪声乘子 σ 与裁剪阈值 C", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "隐私会计输入：采样率 q=|B|/|N|、本地累计更新步数 T、目标 (ε,δ)", "where": "client_step", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "本地数据集规模 N 与批大小 B", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "训练超参数：秩 r、本地步数、通信轮数、学习率 η（FFA-LoRA 不需要调 α）", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "服务器对 B 做 FedAvg 后的全局可训练参数及还原出的全局权重 W0+B̄A0", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "评估集准确率（GLUE 子集、GSM-8K、Food-101）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "噪声矩阵 Frobenius 范数 ||ξBξA||F 与 ||ξW||F（图 1 的合成诊断量）", "where": "client_step", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["clip", "add_noise"],
  "intervention_where": ["both"],
  "assumptions": [
    "服务器不可信但会诚实执行 FedAvg，隐私保证只覆盖被共享的更新与最终模型",
    "所有客户端共享同一预训练权重 W0 与同一冻结随机高斯矩阵 A0，B 从 0 初始化",
    "各客户端本地数据集是全局数据集的互不相交分片，才能用并行组合定理合并隐私损失",
    "本地优化器为 DP-SGD，裁剪阈值 C 与噪声乘子 σ 由 Opacus 矩会计依 q、T、ε、δ 数值求解",
    "损失对 W 满足 Lipschitz 光滑且冻结矩阵有界 ‖A‖≤C（定理 2），局部二次分析假设学习率小、模型局部线性",
    "噪声不被放大的论证假设未触发范数裁剪",
    "FFA-LoRA 要求秩 r≥1，且训练全程使用统一秩",
    "α 无关性依赖学习率随 α 相应缩放（定理 1 与附录 A.6）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 4 节：FFA-LoRA 的核心操作是冻结非零初始化矩阵、只训练零初始化矩阵", "text": "The core idea of FFA-LoRA is to fix the randomly initialized non-zero matrices and only fine-tune the zero-initialized matrices."},
    {"section": "Section 2 (Different DP settings in FL)", "supports": "第 2 节：论文采用服务器不可信的更强隐私设置", "text": "In this paper, we adopt the stronger privacy setting, ensuring that any shared information (i.e., updates of model parameters) from local clients to server satisfies DP."},
    {"section": "Section 3 (Discordance 1)", "supports": "第 3 节与第 6 节：问题入口在服务器对 A 与 B 的分别平均", "text": "However, when the server performs aggregation on the server side, A and B are averaged separately following vanilla FedAvg McMahan et al. (2017a)."},
    {"section": "Section 3 (Discordance 2)", "supports": "第 4 节与第 5 节：DP-SGD 噪声经乘积级联，是论文关注的可观测量与设计动机", "text": "Three terms contain noise and the third term, ξBξA, no longer follows a Gaussian distribution. This shows that noise is cascaded after the multiplication in LoRA, introducing additional difficulties for convergence in fine-tuning."},
    {"section": "Section 4 (FFA-LoRA has no extra interference with data heterogeneity and model-averaging)", "supports": "第 4 节：固定 A0 后更新与 FedAvg、DP-SGD 更相容", "text": "Since ∆Wi ≈BiA0 in FFA-LoRA, the update is more compatible with FedAvg and DP-SGD than LoRA."},
    {"section": "Section 4 (FFA-LoRA saves computation and communication)", "supports": "第 8 节：可训练参数减半，通信与计算开销随之减半", "text": "Since A0 is fixed after initialization in FFA-LoRA, the total number of trainable parameters in the model is effectively halved compared to LoRA."},
    {"section": "Section 5.1 (Experiments with differential privacy guarantees)", "supports": "第 5 节：σ 需要由采样率、总步数与 (ε,δ) 通过 Opacus 矩会计计算", "text": "Given the sampling rate, total step number and privacy requirement ϵ, δ, we use the privacy accountant from Opacus (Yousefpour et al., 2021) to calculate the noise scale σ for all our experiments."},
    {"section": "Section 5.1", "supports": "第 7 节：3 客户端 cross-silo 设置与标签偏斜的强异质性数据划分", "text": "All our experiments with LoRA and FFA-LoRA are run in a 3-client cross-silo federated setting. Data on clients are randomly split among all clients sampled to fit certain proportions to ensure strong data heterogeneity."},
    {"section": "Section 5.3", "supports": "第 7 节：LLaMA-7B 在 GSM-8K 上的主要结果", "text": "Our method has achieved an accuracy of 17.12% on the task of GSM-8K, significantly better than the best performance of LoRA at 15.68% (15.31% reported in (Kuang et al., 2023))."},
    {"section": "Appendix A.5", "supports": "第 9 节：隐私组合依赖各客户端数据集互不相交这一假设", "text": "The privacy loss of all clients performing local updates can be composed by the parallel composition property of DP."}
  ]
}
```
