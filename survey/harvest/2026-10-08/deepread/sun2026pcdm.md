# sun2026pcdm：PCDM: A Diffusion-Based Data Poisoning Attack Against Federated Learning Systems

## 1. 基本信息

**论文标题**：PCDM: A Diffusion-Based Data Poisoning Attack Against Federated Learning Systems（作者 Wei Sun、Yijun Chen、Bo Gao、Ke Xiong、Yuwei Wang、Pingyi Fan、Khaled Ben Letaief；arXiv:2605.16098v1 [cs.CR]，15 May 2026）。

**场景**：传统联邦学习（Federated Learning, FL），具体是一个无线网络支撑的跨设备联邦图像分类系统，由一个基站（Base Station, BS）处的中心服务器与 N 个分布式无线客户端组成（第 III-A 节，图 1）。论文不涉及大语言模型（Large Language Model, LLM），也不涉及联邦大模型微调或参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）；全文没有出现 LoRA 一词。按题目给定的分类，本论文属于"传统联邦学习（图像等）"。

**训练阶段**：攻击发生在本地数据准备阶段（恶意客户端在联邦训练开始前用扩散模型在本地生成投毒数据集），随后经由本地训练与更新上传进入服务器聚合（第 IV-C、IV-D 节）。

**论文类型**：攻击（attack），具体为无目标数据投毒攻击（Untargeted Data Poisoning Attack, UDPA）。论文不提出防御方法，只在结论中写未来打算研究对应防御（第 VI 节）。

**模型与数据规模**：100 个分布式客户端，全局训练 200 个通信轮次，每轮按 0.2 的比例随机选取 20 个客户端参与，每个被选客户端做 5 个本地 epoch、批大小 128（第 V-A 节）。数据集为 MNIST、Fashion-MNIST、CIFAR-10、CIFAR-100 与真实无线场景数据集 VRAI；前四者的训练集/测试集规模分别为 60,000/10,000、60,000/10,000、50,000/10,000、50,000/10,000（表 II），VRAI 使用 66,113 张图像的训练子集并按 80%/20% 划分用于联邦训练与测试，任务为 7 类车型分类（第 V-B 节）。模型方面：MNIST 与 Fashion-MNIST 用两层卷积（16、32 通道）加一层全连接的小型卷积神经网络（Convolutional Neural Network, CNN）；CIFAR-10 用三个卷积块共六层卷积（32、64、128 通道）加两层全连接；CIFAR-100 保持深度但通道宽度加倍（第 V-A 节）；鲁棒聚合实验另外使用 ResNet-18 作为骨干（第 V-B 节）。

分析：摘要写"four open datasets: MNIST, Fashion-MNIST, CIFAR-10, CIFAR-100, and a real-world wireless-specific dataset VRAI"，句中"four"与随后列出的五个数据集不一致，而贡献列表与实验章节均按五个数据集陈述，此处应为摘要笔误。

## 2. 威胁模型

**攻击者是谁**：被攻陷或冒名的内部无线客户端，即恶意客户端（malicious clients）。论文假设"至少存在一个攻击者"（第 III-B 节），并明确攻击者可以控制或冒充一个或多个良性客户端（"one or multiple benign clients"）。恶意客户端的取值在实验中为参与客户端的 5%、10%、20%、30%（表 III），鲁棒聚合实验为 0%、10%、20%、30%（表 IV）。

**能力**：攻击者只能操纵自己的本地数据集，不能影响本地训练过程，属于黑盒攻击（"The local training process cannot be impacted by malicious clients, which can only manipulate their local datasets, i.e., through a black-box attack."，第 III-B 节）。恶意客户端是自足的（self-contained），不借助外部实体或资源协作（第 III-B 节）。论文给出的操作方式是：恶意客户端在本地训练一个扩散模型，用它生成投毒数据集，再用投毒数据集训练本地投毒模型并上传服务器（第 III-B、IV-D 节）。论文另在效率分析中提出"train-then-distribute"部署变体：由一台强服务器预训练模型并分发轻量权重，供客户端低成本推理（第 V-D 节）。

**知识**：论文把攻击者的隐蔽性目标写成"使服务器基于模型差异统计的判据不被触发"，即攻击者知道服务器会用低维核函数（如 PCA、KPCA、SVD）提取本地模型特征、按轮或按区间计算模型间距离，并用均值或中位数等统计量设阈值（第 IV-E2 节，式 44、45）。论文没有说明攻击者是否知道具体的阈值数值或防御算法参数。

**目标**：两个目标，一是通过误分类样本降低全局模型整体性能（无目标破坏），二是隐藏攻击以逃避服务器检测（第 III-B 节）。论文明确研究 UDPA 而非定向投毒（Targeted Data Poisoning Attack, TDPA），并称后门攻击是 TDPA 的代表（第 I 节）。

**防御者是谁、能看到什么、信任什么**：防御者是中心服务器。服务器按 FedAvg 聚合被选客户端的本地模型，持有测试数据集 Dtest 用于评估全局准确率（第 III-A 节，式 1、3）。服务器看不到客户端的原始本地数据，只能看到上传的本地模型更新；论文所描述的防御都建立在对这些更新的统计差异之上（第 IV-E2 节）。论文没有讨论安全聚合（Secure Aggregation）、差分隐私或客户端本地数据审计，也没有说明服务器是否信任客户端的自报信息。

## 3. 攻击入口与流程位置

**入口位置**：本地数据准备。论文的原文表述是："Every malicious client cj generates a poisoned dataset Dp j using G and local dataset Dj before federated training, then Dp j is used for poisoned training instead of Dj."（第 IV-D 节）。也就是说，PCDM 不修改损失函数、优化器或训练步数，也不在更新上传前做缩放、投影或拼装，更不触碰服务器聚合与全局模型下发；它替换的是进入本地训练的数据本身。

**具体操作步骤**（第 IV-A、IV-C、IV-D 节）：

1. 恶意客户端 cj 先训练一个面向投毒的条散模型 PCDM（Poisoning-Oriented Conditional Diffusion Model），训练目标为噪声预测的均方误差，并在输入中加入投毒向量 v（式 38）。
2. 训练完成后，从高斯先验 x_T̂ ∼ N(0, I) 出发，按标签条件迭代去噪 T̂ 步，生成投毒样本 x0 = xp_j，并组装投毒数据集 Dp_j = {(xp_k, yp_k)_j}，其中标签 (yp_k)_j 直接复制自 (yk)_j，即不翻转标签（式 39、40）。
3. 在联邦训练开始前完成上述生成；第一轮中恶意客户端用 Dp_j 训练投毒本地模型 ω*_j^(1) = ∇F(Dp_j)（式 41）。
4. 上传投毒本地模型；若服务器未检出异常且该客户端被选中，聚合后就得到投毒全局模型 ω̂_g^(1)（第 IV-D 节）。
5. 后续轮次中，恶意客户端接收投毒全局模型 ω̂_g^(r)，继续以 Dp_j 训练新的投毒本地模型 ω*_j^(r+1) = ω̂_g^(r) − η·∇F(ω̂_g^(r), Dp_j) 并上传（式 42），如此循环。

分析：从投毒防护库的信任边界看，PCDM 的入口完全位于客户端信任域内部，服务器这一侧只能在"收到更新时"观察到它的后果；论文没有给出任何能在服务器端还原投毒样本的机制。

## 4. 方法原理

**核心思想**：用扩散模型替代生成对抗网络（Generative Adversarial Network, GAN）来生成投毒数据。论文的动机是 GAN 输出具有内在一致性（mode collapse），使投毒模型的更新过于集中而被一致性检测发现（第 I、II、IV 节，表 I）；而扩散模型的生成过程本身带随机性，可以生成"看似合法但不一致"的投毒数据。表 I 把 PCDM 的隐蔽性标为 High，把 VagueGAN 标为 Medium，把标签翻转、噪声注入、PoisonGAN 标为 Low。

**关键步骤一：投毒全局上下文（Poisoning Global Context）**。在每个时间步把投毒向量 v 与上一时间步输出 x_{t−1} 结合，作为当前输出的条件，即 x_t = f(x_{t−1}, o(x_{t−1}, v))（式 9）；其中 o(x_{t−1}, v) = Conv(x_{t−1} + r(v))，r(·) 把 v 重塑到与 x_t 同维度后再相加，经卷积层处理（式 10）。投毒数据的特征写成 x^poison_t = x_t + σ_v·v + μ_v（式 11），其条件生成分布为 p(xp_t | x_t, v) ∝ exp(−1/(2σ_v²)·‖xp_t − (x_t + μ_v + v)‖²)（式 12）。也就是说，标准差 σ_v 与均值 μ_v 分别控制投毒特征的强度与偏移。

**关键步骤二：投毒向量的三条性质**（第 IV-A2、IV-B 节）。性质一为前向扩散不变性：加入 v 不改变前向扩散过程，q̂(x_{1:T}|x_0) = q(x_{1:T}|x_0)（式 13、17、18、19）。性质二为反向采样敏感性：反向过程的梯度多出一项对抗梯度，∇_{x_t} log p(x_t|v) = ∇_{x_t} log p(x_t) + ∇_{x_t} log p(v|x_t)（式 14、22）。性质三为对投毒数据的精细化影响：把输出在 v = 0 处做泰勒展开，得到 xp_k(v) ≈ x_k + ∇_v xp_k·μ_v + ½σ_v² z^T H z + O(v³)（式 15、23、26），其中均值项走一阶梯度、控制偏置，方差项走 Hessian 二阶项、控制多样性与波动。

**关键步骤三：跳跃扩散策略（Jumping Diffusion Strategy）**。PCDM 用加大的方差序列 {β̂_t} 替换基线 DDPM 的 {β_t}，即 β̂_t = e_t·β_t（式 31），使每个前向步加入更多噪声，让 x_t 更快接近高斯分布，从而大幅缩短扩散步数；时间步数满足 T̂ = T/ē，ē 为扩展序列 {e_t} 的均值（式 16、35）。论文推导出 log ᾱ_T ≈ −0.005(T+1)（式 29），当 T = 1000 时 ᾱ_T ≈ e^{−5}；并举例若 β̂_t ≈ 0.1，则 log(1−0.1) ≈ −0.105，为使 log ᾱ_T̂ ≈ −5 需要 T̂ ≈ 5/0.105 ≈ 48（第 IV-B4 节）。论文还要求累积噪声增量一致，即 Σβ_t = ē·Σβ_t（式 32–34），以保证噪声过渡平滑与去噪可学习。

**关键步骤四：效果与隐蔽性的权衡目标**（第 IV-E 节）。攻击被写成带约束的优化问题：最大化 ar − âr（投毒前后全局测试准确率之差，式 43），同时满足 s_j(R′) < S(R′)（式 46），其中 s_j(R′) 是客户端 j 的模型集合与其余客户端模型集合之间的平均差异（式 45），S(R′) 是统计方法给出的阈值。可调超参数包括训练轮数 E（越大投毒数据越接近真实数据、越隐蔽但越不激进）、投毒向量的 σ_v 与 μ_v（越大攻击越有效）、扩展序列 {e_t} 与时间步 T̂（越大越粗、越有效但越不隐蔽）（第 IV-E3 节）。

分析：论文把攻击效果与隐蔽性的解耦归因于"数据操纵与本地训练过程分离"（第 IV-E3 节），这一点对防护库很重要——它意味着检测信号不会出现在损失函数或优化器轨迹上，只会出现在数据分布与更新几何上。

## 5. 检测或防御所需的数据

本节按题目要求，对攻击论文列出攻击会在哪些可观测量上留下痕迹，以及论文声称能绕过哪些检测。

**（1）服务器每轮收到的本地模型更新**。是什么：每个被选客户端上传的本地模型参数 ω_i^(r)。在哪里采集：服务器收到更新时。粒度：逐客户端、逐轮，向量维度等于整个模型参数量，论文指出直接比较高维模型既困难又昂贵，因此需要先用低维核函数 φ(·)（如 PCA、KPCA、SVD）提取关键特征（第 IV-E2 节）。是否需要跨轮历史：单轮判据不需要。是否需要干净参考数据：不需要。是否需要额外计算：需要，降维与距离计算本身是额外开销。论文报告，标签翻转类粗糙攻击的投毒模型在 PCA 二维投影上与良性模型明显分离（图 5），而 PCDM 的投毒更新在位置与分布范围上都与良性更新难以区分（图 5）。

**（2）跨轮次的本地模型集合**。是什么：服务器在一个长度为 R′ 的区间内存储每个客户端收到的本地模型，构成模型集合。在哪里采集：服务器收到更新时并做缓存。粒度：逐客户端、跨轮（区间）。是否需要跨轮历史：需要，这是这类区间防御的核心。是否需要干净参考数据：不需要。是否需要额外计算：需要，要计算集合之间的欧氏距离或余弦相似度 s_j(R′)，再用均值或中位数等统计方法设阈值 S(R′)（第 IV-E2 节，式 45）。论文声称 PCDM 使该差异指标保持在阈值以下。

**（3）更新的统计量视图**。是什么：表 V 把被评估防御映射到的量化指标分为距离类（欧氏距离求和，对应 Multi-Krum；子空间离群分数，对应 PCA、K-Means、UMAP、FedDMC）、方向类（余弦相似度，对应 CONTRA；投影与信号统计，对应 DnC、SignGuard）、分布类（核密度，对应 LoMar）、参数一致性（对应 MCD）以及混合类（幅度与方向，对应 LASA）。在哪里采集：服务器收到更新时（这些统计都在聚合前对本地更新做）。粒度：逐客户端、逐轮（MCD 是周期性检查本地模型参数分布）。是否需要跨轮历史：MCD 需要周期性重复检查。是否需要干净参考数据：不需要。是否需要额外计算：需要。

**（4）服务器测试集上的全局准确率**。是什么：全局模型在 Dtest 上的准确率 a_r 与投毒后的 âr。在哪里采集：聚合后的全局模型，在评估时。粒度：逐轮、模型级。是否需要跨轮历史：需要，攻击效果按 ar − âr 的下降幅度衡量。是否需要干净参考数据：需要服务器的测试集这一根数据集。是否需要额外计算：评估本身的开销。

**（5）客户端本地数据与本地算力痕迹**（论文未将其作为检测手段）。投毒数据集 Dp_j 只存在于客户端本地，服务器在威胁模型中看不到它（第 III-B 节）；论文也没有提出任何检查本地数据分布的防御。论文报告了在客户端侧生成 3,000 个投毒样本需要 174.28 秒（MNIST，表 VI）至 215.08 秒（CIFAR-100，表 VI），峰值显存 2255 MB 至 3448 MB（表 VII），但这是作为攻击开销而非可检测痕迹来陈述的。

**论文声称能绕过的检测与聚合机制**：论文在摘要与第 I 节称评估了十一种防御方法（含三种鲁棒聚合机制）与七种投毒攻击，第 V-B 节"统计不可区分性验证"再次称"the aforementioned eleven defense and aggregation mechanisms"。第 V-A 节列出的检测类方法实际为八个条目：PCA、UMAP、CONTRA、DnC、K-Means、FedDMC、LoMar、MCD；鲁棒聚合为 Multi-Krum、SignGuard、LASA 三个。论文称现有防御对标签翻转表现好、对噪声类攻击中等、对生成式投毒吃力，其中 MCD 对噪声与 GAN 类攻击相对较好，"yet still fails to effectively detect our PCDM attack"（第 V-B 节）。在鲁棒聚合下，论文称即使面对 LASA 这类最新防御，PCDM 仍造成显著准确率下降（第 V-B 节，表 IV）。

分析：第 V-A 节文字写"seven representative defense methods"但随后列出八条，结合 8 + 3 = 11 与摘要的"eleven defense methods"可以判断这是计数笔误。

## 6. 干预动作

论文本身不提出任何防御，因此不存在论文自己设计的干预动作。论文描述的被防御动作有两个：其一，服务器计算每个本地模型与其余模型的平均差异，并丢弃差异过大的本地模型（第 IV-E2 节，式 44）；其二，在区间防御中，若客户端的差异指标 s_j(R′) > S(R′)，该客户端被标记为恶意（"Clients whose s(R′) j > S(R′) are labeled as malicious ones."，第 IV-E2 节）。这些动作发生在服务器收到更新之后、聚合之前，属于剔除客户端的类型。论文没有讨论重新加权、裁剪、加噪、样本过滤、模型修复或回滚。

PCDM 对此的应对不是改变干预动作，而是让攻击不触发它：论文原文称"Since detectable poisoning is readily neutralized, PCDM is designed to impose maximal aggregation damage while maintaining benign update profiles"（第 IV-E 节），并把 s_j(R′) < S(R′) 写成显式约束（式 46）。此外，在资源受限设备的部署变体中，论文提出由强服务器预训练扩散模型、向客户端分发轻量权重（第 V-D 节），这属于攻击方自己的部署动作，不是防御干预。

分析：在防护库的插件语义中，这篇论文对应的是"被检测对象"，因此干预接口只需覆盖剔除与重新加权；论文没有给出可实现的修复或回滚方案。

## 7. 实验设置与主要结果

**基本设置**（第 V-A 节）：100 个分布式客户端，200 个通信轮次，每轮随机选择 0.2（即 20 个）客户端执行本地训练，每个被选客户端做 5 个本地 epoch、批大小 128；全局任务是图像分类；所有对比方法使用相同的数据划分索引、随机种子与客户端数据分配。

**数据划分**：同时评估独立同分布（Independent and Identically Distributed, IID）与非独立同分布（non-IID）两种设置；non-IID 采用对称 Dirichlet 分布，浓度参数 α = 0.5，产生高度偏斜的标签分布；所有场景下测试集都留在服务器上用于全局性能评估（第 V-A 节）。数据集统计见表 II。

**恶意比例与基线**：表 III 中恶意客户端比例从 5% 变化到 30%，基线包括标签翻转（Label Flipping, LF）、PoisonGAN、轻噪声（Light Noise, LNS）、重噪声（Heavy Noise, HNS）、SAP 噪声（SAP-NS）与 VagueGAN；表 IV 的鲁棒聚合实验在 CIFAR-10 与 CIFAR-100 上以 0%、10%、20%、30% 的恶意比例、使用 ResNet-18 进行 200 轮训练。

**关键结果**：

- 攻击有效性（表 III）：IID CIFAR-100 上，无攻击时准确率 55.7%，PCDM 在 5%/10%/20%/30% 恶意比例下分别为 52.1%/47.6%/44.7%/37.3%；同一设置下 VagueGAN 为 51.5%/48.3%/42.4%/39.4%。IID MNIST 上 PCDM 从 98.7% 降到 30% 恶意比例时的 97.1%。论文总结称 PCDM 在不同任务上持续优于基线，且所有攻击在复杂任务上更有效（第 V-B 节）。
- 非独立同分布结果（表 III）：non-IID CIFAR-100 上 PCDM 为 53.4%/49.7%/47.0%/41.3%/37.2%（对应 0%/5%/10%/20%/30%），VagueGAN 为 53.4%/51.0%/49.0%/41.0%/35.1%。分析：在 30% 这一格，VagueGAN 的 35.1% 低于 PCDM 的 37.2%，即该单元格中 PCDM 并非破坏性最强的方案，这与第 V-B 节"PCDM maintains the highest effectiveness"的表述存在出入。
- 隐蔽性可视化（图 5）：标签翻转类攻击的投毒模型在 PCA 二维投影上明显偏离良性簇；VagueGAN 虽然嵌入良性簇内，但其投毒更新的分布范围显著小于良性更新，论文归因于 GAN 的模式崩溃（mode collapse）；PCDM 的投毒更新在位置与分布范围上都与良性模型难以区分。
- 防御检出效果（图 6）：在 Fashion-MNIST 上比较八种防御对七类投毒攻击的表现，指标包括准确率、精确率、召回率、F1 与一个复合分数（Composite Score = 100 × (α·Recall + β·(1−FPR))，式 47，论文取 α = 0.6、β = 0.4）。论文称现有防御对标签翻转表现良好、对噪声类中等、对生成式投毒吃力，MCD 相对更好但仍无法有效检出 PCDM。
- 鲁棒聚合下的全局准确率（表 IV）：CIFAR-10 上 FedAvg 从 0% 时的 90.25% 降到 30% 时的 84.73%，Multi-Krum 从 83.51% 到 82.79%，SignGuard 从 89.9% 到 85.32%，LASA 从 91.95% 到 85.84%；CIFAR-100 上 FedAvg 从 65.99% 到 55.26%，Multi-Krum 从 52.66% 到 50.68%，SignGuard 从 63.64% 到 56.83%，LASA 从 63.96% 到 61.15%。
- 无线场景（图 7）：在 VRAI 上，恶意比例从 10% 升到 30% 的过程中全局测试准确率持续下降，论文称该趋势在所有被评估的聚合策略下都稳定。
- 消融（图 8、图 9）：对比 DDPM、去掉投毒向量 v 的 PCDM（w/o v）与完整 PCDM，论文称 DDPM 合成的数据缺乏有效攻击能力，投毒向量 v 对隐蔽性与攻击性都有系统性提升，且改进幅度在高维复杂数据集（CIFAR-100、CIFAR-10）上比在 MNIST、Fashion-MNIST 上更明显。论文还报告当模型距离度量低于约 15（图 9 中的虚线）时攻击足以逃过多数检测机制。
- 权衡分析（图 10、图 11）：更高的噪声水平提升攻击有效性但损害隐蔽性，论文推荐 σ_v ≈ 1 与 μ_v ≈ 5，此时模型距离保持在 15 以下；多数实验采用 E = 30 与 T̂ = 20。

**指标**：全局模型测试准确率及其下降幅度（表 III、表 IV、图 7）、PCA 降维后的二维分布（图 5）、真阳性/假阳性/真阴性/假阴性以及准确率、精确率、召回率、F1 与复合分数（图 6、式 47）、欧氏距离形式的隐蔽性度量（图 9、图 10）。

## 8. 开销

论文报告了攻击侧的生成开销。表 VI 给出训练并生成 3,000 个投毒样本的时间（秒）：MNIST 上 DDPM 1126.23、PCDM w/o v 167.32、PCDM 174.28；Fashion-MNIST 上 1114.10、166.97、175.83；CIFAR-10 上 1445.37、196.41、211.01；CIFAR-100 上 1462.69、197.20、215.08。表 VII 给出同一批量下的运行时间、FLOPs（吉，G）与峰值显存（MB）：例如 CIFAR-10 上 VagueGAN 为 189.20 秒、5980.4 G、2950 MB，DDPM 为 1445.37 秒、45220.9 G、3420 MB，PCDM 为 211.01 秒、6760.5 G、3445 MB；MNIST 上 DDPM 的 FLOPs 为 32450.6 G、PCDM 为 5108.3 G。论文据此声称跳跃扩散策略相比 DDPM 带来约 85% 的延迟与计算量下降（例如 CIFAR-10 的 FLOPs 从 45k G 降到 6.7k G），并称 PCDM 相对最先进的 VagueGAN 只增加约 10–15% 的运行时间、显存占用相当（第 V-C、V-D 节）。硬件为 NVIDIA A100-40GB GPU。

分析：第 V-C 节正文写"summarized in Ta-ble VII"，但所引内容实为表 VI；另外第 IV-E3 节把时间步约束写成"Equation (15)"，而实际对应式 34、35。这两处编号疑似笔误。论文未报告通信开销与存储开销（除峰值显存外）；第 III-A 节只把降低通信开销作为 FedAvg 客户端采样的动机提及，没有给出 PCDM 自身的通信量。

## 9. 假设、局限与自适应攻击

**论文成立所依赖的假设**：

1. 联邦训练是同步的，服务器每轮从 N 个客户端中随机选 B < N 个，并用 FedAvg 等权平均（第 III-A 节，式 1）。
2. 恶意客户端只能改本地数据，不能改本地训练过程，不能与外部实体协作（第 III-B 节）。
3. 服务器看不到客户端原始数据，只能看到上传的本地模型；防御以模型更新的统计差异为判据，并用低维投影加阈值的方式判定（第 IV-E2 节，式 44、45）。
4. 攻击者知道防御的判据形式（核函数、距离度量、按区间统计），并能把"差异低于阈值"当作可优化的约束（式 46）。
5. 客户端具备在本地训练扩散模型的数据与算力，或者采用"强服务器预训练、客户端轻量推理"的分发模式（第 IV-A、V-D 节）。
6. 任务是图像分类，模型为 CNN 或 ResNet-18，投毒数据的生成依赖卷积 U-Net 式的图像扩散模型（第 III-C、V-A 节）。
7. 攻击者追求的是无目标性能破坏，而不是定向误分类（第 I、III-B 节）。
8. 攻击效果与隐蔽性之间存在可调权衡，并且该权衡由 E、σ_v、μ_v、{e_t} 与 T̂ 这几个超参数控制（第 IV-E3、V-E 节）。

**论文自述的局限**：扩散模型训练成本高、生成时间长、硬件要求高，这是提出跳跃扩散策略的直接动机（第 IV-A 节）；最优的 E 与 T̂ 对数据集复杂度敏感，复杂或高分辨率数据通常需要更大的取值（第 V-E 节）；图 9 相关分析指出 DDPM 在 CIFAR-100 上表现出的攻击效果主要来自客户端数据量受限导致的能力下降，而非真正的对抗特征（第 V-C 节）；论文在结论中仅表示未来打算研究针对此类生成式隐蔽攻击的对策（第 VI 节），即本文不提供防御。

**是否评估自适应攻击者**：没有。论文评估的是固定的、已有的防御与鲁棒聚合规则（表 V 所列十一项机制），没有考虑知道 PCDM 存在并据此调整的防御者，也没有给出针对 PCDM 的反制实验。因此在本报告的结构化字段中 `evaluates_adaptive_attacker` 记为 false。

**迁移到联邦 LoRA 微调时可能失效的假设**：

- 分析：论文的"本地模型"是整个模型的全参数向量，服务器对完整权重做 PCA/KPCA/SVD 降维后再比较。联邦 LoRA 微调中服务器通常只收到低秩增量矩阵（A、B），可观测对象从全参数向量变成低秩因子，PCA 子空间、余弦相似度与欧氏距离的统计特性都会改变，论文里"投毒更新与良性更新在位置与分布范围上不可区分"的结论（图 5）没有在低秩增量上验证过。
- 分析：论文的攻击载体是图像扩散模型（U-Net 卷积结构、连续像素空间）。LoRA 微调的数据是文本指令或对话样本，投毒需要在离散词元空间生成"看似合法的"样本，论文的投毒向量注入方式（式 10、11）与跳跃扩散的噪声日程（式 31、35）都建立在连续图像张量上，是否可迁移论文未说明。
- 分析：论文假设被选客户端都用同一架构、同一参数形状的模型参与聚合，因此所有更新处在同一向量空间里可直接做距离比较。联邦 LoRA 中不同客户端可能使用不同的秩、不同的目标模块甚至不同的基座版本，跨客户端的逐元素比较与集合距离可能失去定义，这会同时削弱论文所描述的防御判据与攻击的隐蔽性论证。
- 分析：论文假设服务器能以明文看到每个客户端的完整更新。若联邦大模型微调采用安全聚合、只上传合并后的适配器或采用异步参与，则"服务器收到更新时"这一采集点可能不存在，论文第 IV-E2 节所依赖的区间防御在工程上无法直接实现。
- 分析：论文的攻击目标是让全局分类准确率下降。在联邦大模型场景中，更有意义的指标是后门成功率、越狱成功率或安全对齐的破坏程度，论文的复合分数（式 47）与准确率下降指标不能直接套用；论文的 UDPA 目标设定与联邦大模型的主要风险并不对齐。
- 分析：论文假设客户端只改数据、不改训练过程，且恶意客户端是自足的。在 LoRA 微调供应链中，攻击面还可能落在适配器发布方、合并脚本或基座模型上，这些位置论文没有讨论，其"黑盒数据投毒"的能力假设在这些场景下过窄。

## 10. 对防护库设计的含义

- 分析：采集底座必须在"服务器收到更新时"提供一个与攻击无关的原始视图，即每轮每个客户端的完整更新向量及其元数据（客户端标识、轮次、参与标记），因为论文中所有防御判据（PCA、UMAP、CONTRA、DnC、K-Means、FedDMC、LoMar、MCD、Multi-Krum、SignGuard、LASA，第 V-A 节）都只消费这一个数据源。这是通用需求，不是 PCDM 特有。
- 分析：底座需要支持跨轮缓存与"区间视图"，即按客户端保存最近 R′ 轮的更新集合，以支持式 45 那种集合间距离与阈值统计。这是论文第 IV-E2 节明确描述的一类防御所特有的需求，属于轮次级历史视图。
- 分析：服务器钩子需要提供投影与统计原语（PCA、KPCA、SVD 降维，余弦相似度、欧氏距离、核密度估计、幅度与方向纯度等），并把"阈值如何确定（均值或中位数）"做成可配置插件参数，否则表 V 中的任何防御都无法直接落地。这些算法本身是通用插件，但 PCDM 论文把它们作为攻击的对抗目标，因此对它们的可复现性要求更高。
- 分析：干预接口至少要覆盖"剔除客户端"与"重新加权"两种动作，并作用在聚合之前；论文描述的防御动作只有丢弃或标记恶意客户端（第 IV-E2 节），没有样本过滤、模型修复或回滚的语义。这是通用接口。
- 分析：如果要检出 PCDM 这一类攻击，服务器端的更新几何视图是不够的，因为论文的核心主张正是投毒更新在欧氏距离、余弦相似度、子空间离群分数、核密度与参数一致性这些指标上都与良性更新不可区分（图 5、表 V）。库需要补充客户端侧采集点：本地数据集的统计摘要、生成式模型的训练痕迹，以及客户端算力异常（论文报告生成 3,000 个样本需 174.28–215.08 秒、峰值显存 2255–3448 MB，表 VI、表 VII）。这是 PCDM 特有的需求。
- 分析：由于 PCDM 的入口位于客户端信任域内部，而威胁模型又假定该客户端已被攻陷，客户端侧采集点在对抗场景下本身不可信；库应把客户端自报的数据摘要视为"可用于溯源、不可用于判定"的低信任信号，并在服务器侧保留独立的评估钩子（全局测试集准确率随轮次的变化，式 3 与式 43）作为最终效果监控。这是通用设计约束。

## 11. 原文依据

1. 第 I 节摘要。支撑第 1 节的论文类型与第 4 节的核心思想："In this paper, we propose a diffusion-based data poisoning framework against FL systems, which leverages a Poisoning-Oriented Conditional Diffusion Model (PCDM) to enable fine-grained control over the local generation of poisoned data while ensuring both attack effectiveness and stealthiness."

2. 第 III-B 节 Attacker's capabilities。支撑第 2 节关于攻击者身份与自足性的论断："The attacker can take control of or impersonate one or multiple benign clients. To emphasize the effectiveness of the data poisoning attack strategy, we assume that the controlled (malicious) clients are self-contained."

3. 第 III-B 节 Attacker's capabilities。支撑第 2 节的能力边界与第 3 节的入口判断："The local training process cannot be impacted by malicious clients, which can only manipulate their local datasets, i.e., through a black-box attack."

4. 第 IV-D 节 Poisoned Federated Training。支撑第 3 节的入口位置："Every malicious client cj generates a poisoned dataset Dp j using G and local dataset Dj before federated training, then Dp j is used for poisoned training instead of Dj."

5. 第 IV-E2 节 Attack Stealthiness。支撑第 5 节第（1）项服务器侧可观测量的采集位置："The server typically defends against data poisoning attacks by calculating the difference between each local model and other models"

6. 第 IV-E2 节 Attack Stealthiness。支撑第 5 节第（2）项跨轮历史与区间防御："previous studies have employed an interval defense method by storing the local models received during an interval of R′ time steps to construct a model set for each client"

7. 第 V-A 节 Experimental Setup。支撑第 7 节的客户端规模与轮次："We simulate a wireless network comprising 100 distributed clients (e.g., IoT nodes or smart cameras). The global training process spans 200 communication rounds."

8. 第 V-A 节 Experimental Setup。支撑第 7 节的参与率与本地训练配置："In each round, a fraction of clients (0.2, i.e., 20 clients) are randomly selected to execute local training. Specifically, each selected client performs 5 local epochs with a batch size of 128."

9. 第 V-D 节 Efficiency Analysis and Resource Consumption。支撑第 8 节的开销结论："By employing the jumping diffusion strategy, significantly reducing the Markov chain length, PCDM achieves a drastic 85% reduction in latency and computational cost compared to DDPM"

10. 第 V-C 节 Ablation Study。支撑第 7 节的隐蔽性阈值与第 9 节的假设："With respect to stealthiness, experiments reveal that when the model distance metric remains below approximately 15 (as indicated by the dashed line), the attack is sufficiently covert to evade most existing detection mechanisms."

```json
{
  "key": "sun2026pcdm",
  "title": "PCDM: A Diffusion-Based Data Poisoning Attack Against Federated Learning Systems",
  "year": 2026,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["local_data"],
  "observables": [
    {
      "what": "每个被选客户端上传的本地模型参数（local model updates），以及经低维核函数 φ(·)（PCA、KPCA、SVD 等）降维后的特征表示",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "服务器在 R′ 轮区间内为每个客户端缓存的本地模型集合，以及集合间的欧氏距离或余弦相似度 s_j(R′) 与阈值 S(R′)",
      "where": "server_receive",
      "granularity": "round",
      "needs_history": true,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "表 V 所列的更新统计量：欧氏距离求和、子空间离群分数、余弦相似度、投影与信号统计、核密度、参数一致性、幅度与方向",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "全局模型在服务器测试集 Dtest 上的准确率 a_r 与投毒后的 âr，用于度量攻击效果",
      "where": "evaluation",
      "granularity": "round",
      "needs_history": true,
      "needs_clean_reference": true,
      "needs_extra_compute": false
    },
    {
      "what": "客户端本地投毒数据集 Dp_j 与客户端侧扩散模型训练/生成的开销痕迹（论文未将其作为检测输入）",
      "where": "client_post_train",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "联邦训练同步进行，服务器每轮从 N 个客户端中随机选 B < N 个并用 FedAvg 等权平均（第 III-A 节，式 1）",
    "恶意客户端只能操纵本地数据集，不能影响本地训练过程，且为自足攻击者、不与外部实体协作（第 III-B 节）",
    "服务器看不到客户端原始数据，只能看到上传的本地模型，并以模型更新的统计差异作为检测判据（第 IV-E2 节）",
    "攻击者知道防御的判据形式（低维核函数、距离度量、区间统计与阈值），并可把差异低于阈值作为优化约束（式 44、45、46）",
    "客户端具备在本地训练扩散模型的数据与算力，或采用强服务器预训练后分发轻量权重的模式（第 IV-A、V-D 节）",
    "任务是图像分类，模型为 CNN 或 ResNet-18，投毒数据由图像扩散模型生成（第 III-C、V-A 节）",
    "攻击目标是无目标性能破坏，而非定向后门（第 I、III-B 节）",
    "攻击有效性与隐蔽性的权衡由 E、σ_v、μ_v、{e_t} 与 T̂ 控制，且该权衡可调（第 IV-E3、V-E 节）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {
      "section": "Abstract / Section I",
      "supports": "第 1 节论文类型与第 4 节核心思想：这是一篇基于扩散模型的联邦学习数据投毒攻击论文",
      "text": "In this paper, we propose a diffusion-based data poisoning framework against FL systems, which leverages a Poisoning-Oriented Conditional Diffusion Model (PCDM) to enable fine-grained control over the local generation of poisoned data while ensuring both attack effectiveness and stealthiness."
    },
    {
      "section": "Section III-B Attacker's capabilities",
      "supports": "第 2 节攻击者身份与自足性假设",
      "text": "The attacker can take control of or impersonate one or multiple benign clients. To emphasize the effectiveness of the data poisoning attack strategy, we assume that the controlled (malicious) clients are self-contained."
    },
    {
      "section": "Section III-B Attacker's capabilities",
      "supports": "第 2 节能力边界（只改数据、黑盒）与第 3 节攻击入口",
      "text": "The local training process cannot be impacted by malicious clients, which can only manipulate their local datasets, i.e., through a black-box attack."
    },
    {
      "section": "Section IV-D Poisoned Federated Training",
      "supports": "第 3 节攻击进入流程的位置：联邦训练前在客户端本地生成并替换训练数据集",
      "text": "Every malicious client cj generates a poisoned dataset Dp j using G and local dataset Dj before federated training, then Dp j is used for poisoned training instead of Dj."
    },
    {
      "section": "Section IV-E2 Attack Stealthiness",
      "supports": "第 5 节第（1）项：服务器在收到更新时比较本地模型差异",
      "text": "The server typically defends against data poisoning attacks by calculating the difference between each local model and other models"
    },
    {
      "section": "Section IV-E2 Attack Stealthiness",
      "supports": "第 5 节第（2）项：区间防御需要跨轮的本地模型历史集合",
      "text": "previous studies have employed an interval defense method by storing the local models received during an interval of R′ time steps to construct a model set for each client"
    },
    {
      "section": "Section V-A Experimental Setup",
      "supports": "第 7 节客户端规模与训练轮次",
      "text": "We simulate a wireless network comprising 100 distributed clients (e.g., IoT nodes or smart cameras). The global training process spans 200 communication rounds."
    },
    {
      "section": "Section V-A Experimental Setup",
      "supports": "第 7 节参与客户端比例、本地 epoch 数与批大小",
      "text": "In each round, a fraction of clients (0.2, i.e., 20 clients) are randomly selected to execute local training. Specifically, each selected client performs 5 local epochs with a batch size of 128."
    },
    {
      "section": "Section V-D Efficiency Analysis and Resource Consumption",
      "supports": "第 8 节开销：跳跃扩散相对 DDPM 约 85% 的延迟与计算量下降",
      "text": "By employing the jumping diffusion strategy, significantly reducing the Markov chain length, PCDM achieves a drastic 85% reduction in latency and computational cost compared to DDPM"
    },
    {
      "section": "Section V-C Ablation Study",
      "supports": "第 7 节隐蔽性阈值（约 15）与第 9 节攻击成立所依赖的隐蔽性假设",
      "text": "With respect to stealthiness, experiments reveal that when the model distance metric remains below approximately 15 (as indicated by the dashed line), the attack is sufficiently covert to evade most existing detection mechanisms."
    }
  ]
}
```
