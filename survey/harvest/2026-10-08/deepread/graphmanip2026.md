# graphmanip2026：Graph Representation Learning Augmented Model Manipulation on Federated Fine-Tuning of LLMs

## 1. 基本信息

- **场景**：联邦大模型微调（federated fine-tuning of LLMs，简称 FFT / FedLLMs），并且明确采用参数高效微调中的低秩适配（Low-Rank Adaptation，LoRA）。论文第 I 节与第 III.B 节把 FedLLMs 描述为"各 LLM agent 在本地私有数据上微调、把本地更新上传到边缘服务器聚合、再把全局模型广播回各 agent"，并说明"pretrained LLM backbone remains frozen, while lightweight low-rank adaptation matrices inserted into selected layers are trained and communicated"（第 I 节）。因此这不是传统联邦学习（图像等），也不是集中式训练，而是**联邦大模型 LoRA 微调**。
- **训练阶段**：覆盖联邦微调的完整轮次循环——本地 LoRA 训练（本地 epoch）、上传向量化后的 LoRA 增量、服务器按样本量加权聚合、广播全局 LoRA 参数、进入下一轮（第 III.A 节式 (1)(2)、第 III.B 节式 (3)(4)、图 1）。攻击发生在"本地更新生成/上传"与"服务器聚合"环节。
- **论文类型**：攻击（模型操纵 / 投毒），附带对既有防御（欧氏距离与余弦相似度阈值）的规避分析。论文没有提出新的检测或防御方法。
- **模型与数据规模**（第 VI.A 节、表 II、表 III）：三个骨干网络 DistilBERT（约 6700 万参数，编码器）、Pythia（约 1.6 亿参数，解码器）、Qwen2.5（约 5 亿参数，解码器）；两个文本分类数据集 AG News（4 类，120,000 训练样本 / 7,600 测试样本）与 Yahoo! Answers（10 类，140 万训练样本 / 60,000 测试样本）。实验为 5 个良性客户端加 2 个恶意客户端，共 50 轮通信，每轮 5 个本地迭代。表 II 给出良性客户端数 I 为 5～7、恶意客户端数 J 为 0～2、服务器学习率 η 为 1.0、本地学习率 5e−5、Dirichlet 浓度 0.3、LoRA rank r 为 8/32/128/256、LoRA scaling α 为 16/64/256/512、选中参数维度 M 为 500/1000、VGAE 训练 30 个 epoch。表 III 给出可训练参数量从 888,580（1.31%）到 68,739,092（100%）不等。硬件为 NVIDIA A100 GPU（80 GB 显存），Python 3.12、PyTorch 2.10（第 VI.A 节）。
- **版本信息**：论文首页标注 arXiv:2605.07961v2 [cs.LG]，日期 5 Jul 2026，据此记年份为 2026。

## 2. 威胁模型

**攻击者是谁。** 攻击者是联邦系统中的恶意客户端（malicious client / adversarial agent），论文写作"adversarial agent j ∈[1, J]"，并且强调它"acts as a legitimate but malicious agent"（第 III.C 节）。恶意客户端数量在表 II 中为 J = 0～2；第 VI.A 节的实验设定为 5 个良性客户端加 2 个恶意客户端。

**能力（能改什么）。** 攻击者能够自行构造并上传任意的本地 LoRA 更新向量 ∆w′_j(t)，不需要通过真实本地训练得到该更新（第 III.C 节、Algorithm 1 第 3～5 行：良性客户端跑本地 epoch，攻击者直接观测并生成更新）。攻击者**不能**（论文未说明其能）修改服务器聚合规则、修改其他客户端的数据或标签、或修改全局模型下发内容。论文未说明恶意客户端是否仍会在自己的本地数据上正常训练。

**知识（知道什么）。** 第 III.C 节写明："the adversary's knowledge consists of a subset of benign local updates and the global updates"，即攻击者能观测到**一部分良性客户端上传的本地更新**，以及**服务器广播的全局更新**。此外，第 IV 节明确假设各轮的距离阈值 d_T(t) 与余弦相似度阈值 δ_T(t) 对所有参与方已知；第 IV 节式 (7a) 还要求攻击者持有一个独立测试集 D_g 用于计算被操纵全局模型的损失。攻击者还知道 LoRA 的适配层结构与向量化拼接方式（由式 (4) 的定义隐含）。论文未说明攻击者如何窃听到其他客户端的更新（例如是否依赖无线信道广播或服务器共谋），也**未说明**攻击者是否知道各客户端的数据量 D_i（聚合权重用到 D_i / Σ_k D_k，第 III.A 节）。

**目标。** 无目标破坏（untargeted）。第 IV 节式 (7a) 的目标是最大化独立测试集 D_g 上的全局损失；摘要与第 I 节表述为"reducing the global LLM accuracy by up to 26% and degrading the average accuracy of local LLM agents by up to 22%"。论文明确不是定向后门、不是越狱/安全对齐破坏、也不涉及隐私窃取。论文在第 VI.B.2 节用两个被误分类的新闻样例（图 5）展示操纵会让模型给出错误类别但仍生成流畅解释。

**防御者是谁、能看到什么、信任什么。** 防御者是边缘服务器（第 III.D 节）。它能看到所有客户端上传的本地更新和聚合后的全局更新，使用欧氏距离（式 (5)）和成对余弦相似度（式 (6)）衡量更新与全局更新/其他更新的统计与几何一致性，用预设阈值 d_T 和 δ_T 判定离群更新。服务器**不知道攻击者的存在**（第 III.C 节："Since the edge server is unaware of the adversary's presence, it aggregates the malicious updates together with the benign local updates"）。它信任的假设是"良性更新在参数空间中围绕全局更新聚集，恶意更新会引入异常的空间偏差"（第 III.D 节）。论文未说明服务器是否持有根数据集、是否使用安全聚合（secure aggregation）或差分隐私。

## 3. 攻击入口与流程位置

攻击内容进入的位置是**更新上传前的后处理**（本地更新在生成阶段被替换为对抗性构造的 LoRA 增量），并在**服务器聚合**处生效；随后通过**全局模型下发**扩散到全部客户端。攻击**不进入**本地数据准备（没有投毒样本），也不进入本地训练过程（恶意更新是构造出来的，不是本地训练得到的）。具体步骤如下（第 III.A、III.C、IV、V 节，Algorithm 1，图 1(b)、图 2）：

1. 第 t 轮开始，服务器把上一轮全局 LoRA 参数 w_g(t−1) 广播给所有 agent（第 III.A 节）。
2. 每个良性 agent i 在本地数据集 D_i 上跑 T_l 个本地 epoch，得到 w_i(t)，计算本地增量 ∆w_i(t) = w_i(t) − w_g(t−1) 并上传（第 III.A 节；Algorithm 1 第 3 行）。
3. 恶意 agent j 观测"一部分良性 agent 传输的本地更新 ∆w_i(t)"以及上一轮全局模型 w′_g(t−1)（第 III.C 节；Algorithm 1 第 3 行）。
4. 恶意 agent 把这些被观测更新组织成特征矩阵 F(t) = [∆w_1(t), …, ∆w_B(t)]^T ∈ R^{M×B}，并用参数维度之间的余弦相似度构造邻接矩阵 A(t) = [δ_{m,m′}(t)] ∈ R^{M×M}（第 V 节，式 (12)）。
5. 用 VGAE（变分图自编码器，variational graph autoencoder）学习图结构，得到重构邻接矩阵 Â(t)（第 V.1、V.2 节，式 (13)～(16)）。
6. 通过图谱变换模块（graph spectral transformation，GST）生成初始恶意更新：构造拉普拉斯矩阵 L = D − A，特征分解 L = BΛB^T，投影 S = B^T F，再由重构拉普拉斯 L̂ = D̂ − Â 得到基 B̂，重构 F̂ = B̂ S，取 F̂ 的第 j 列作为第 t 轮的初始恶意更新（第 V.3 节）。
7. 用增广拉格朗日对偶方法迭代优化 ∆w′_j(t)、λ(t)、θ(t)，在满足式 (7b)(7c) 的几何约束下最大化全局损失，得到最终更新 ∆w′_j(t)⋆（第 IV 节式 (8)～(11)、第 V 节式 (17)；Algorithm 1 第 4 行）。
8. 恶意 agent 把 ∆w′_j(t)⋆ 上传给边缘服务器（Algorithm 1 第 5 行）。服务器在不知情的情况下把恶意更新与良性更新一起加权聚合，得到被操纵的全局更新 ∆w′_g(t)，并更新 w′_g(t) = w′_g(t−1) + η·∆w′_g(t)（第 III.A 节式 (2)、第 III.C 节；Algorithm 1 第 6 行）。
9. 被污染的全局模型被广播给所有 agent，作为下一轮本地训练的起点，于是操纵效果在整个 FedLLMs 中逐轮传播（第 III.C 节、第 V 节末、Algorithm 1 第 7～8 行、图 1(b)）。

**分析：** 该攻击在时序上要求"先看见本轮良性更新，再上传自己的更新"，也就是攻击者的上传时刻必须晚于被观测的良性客户端（或服务器允许迟到更新）。论文没有讨论这一时序前提，Algorithm 1 第 3～5 行只是把观测放在上传之前。

## 4. 方法原理

核心思想是：不靠简单扰动或缩放，而是先学习"良性更新之间的特征相关性"，再在这个相关性结构引导下合成一个既能最大化全局损失、又在欧氏距离与余弦相似度上与良性更新无法区分的恶意更新（第 I 节、第 IV 节、第 V 节）。

**（1）问题形式化（第 IV 节，式 (7)）。** 恶意客户端 j 在第 t 轮求解一个带约束的优化问题：最大化
(1/D_g)·Σ_{(x,y)∈D_g} f(M(x, w′_g(t)), y)，即独立测试集上的全局损失（式 (7a)）；
约束一：d(∆w′_j(t), ∆w′_g(t)) ≤ d_T(t)，即恶意更新与被操纵全局更新之间的欧氏距离不超过阈值（式 (7b)）；
约束二：δ_{i,j}(t) ≤ δ_T(t)，即恶意更新与良性更新之间的余弦相似度不超过阈值（式 (7c)）。
论文指出该问题是带约束的非凸问题，聚合过程的非线性与几何隐蔽约束导致变量非凸耦合。

**（2）增广拉格朗日对偶（第 IV 节，式 (8)～(11)）。** 构造拉格朗日函数 L(∆w′_j(t); λ(t), θ(t)) = F(w′_g(t)) − λ(t)(d_j(t) − d_T(t)) − θ(t)(δ_{i,j}(t) − δ_T(t)) − (ρ_λ(t)/2)(d_j(t) − d_T(t))² − (ρ_θ(t)/2)(δ_{i,j}(t) − δ_T(t))²（式 (8)），其中 λ、θ ≥ 0 是对偶变量，ρ_λ、ρ_θ > 0 是惩罚参数。二次惩罚项的作用是把 d_j(t) 与 δ_{i,j}(t) 从可行域内侧"推到贴近阈值"，从而在隐蔽约束允许的范围内最大化操纵强度，而不是过度压小这些量。对偶问题为 min_{λ≥0, θ≥0} D(λ, θ)（式 (10)），其中 D(λ, θ) = max_{∆w′_j(t)} L（式 (9)）。每个通信轮内用迭代 k 更新 λ(k+1) = [λ(k) + ε(d_j(k) − d_T(t))]⁺、θ(k+1) = [θ(k) + ε(δ_{i,j}(k) − δ_T(t))]⁺（式 (11a)(11b)，ε > 0 为步长，[x]⁺ = max{0, x}）。迭代收敛后得到该轮的 λ(t)、θ(t)，最终更新由 ∆w′_j(t)⋆ = arg max_{∆w′_j(t)} L(∆w′_j(t), λ(t), θ(t)) 给出（式 (17)）。

**（3）对抗图表示学习框架（第 V 节，图 2）。** 用被观测到的良性更新建模 LoRA 参数之间的内部相关结构，编码为图 G = (V, E, F)。节点特征矩阵 F(t) = [∆w_1(t), …, ∆w_B(t)]^T ∈ R^{M×B}（B 为被观测良性更新数，M 为选中 LoRA 参数维度，M ≪ M_p），邻接矩阵 A(t) = [δ_{m,m′}(t)] ∈ R^{M×M}（式 (12) 给出两个参数维度行向量之间的余弦相似度）。也就是说图的顶点是选中的参数维度、节点特征是各良性客户端在该维度上的取值。

**（4）VGAE 编码器与解码器（第 V.1、V.2 节）。** 编码器是 L 层图卷积网络（GCN），输入 F 与 A，Z^(0) = F；每层做谱卷积 Z^L = φ(D̃^(−1/2) Ã D̃^(−1/2) Z^(L−1) W^L)，其中 Ã = A + I，φ 为激活函数（如 ReLU）（式 (13)(14)）。解码器用内积重构邻接矩阵 Â(t) = Sigmoid(Z^L (Z^L)^T)（式 (15)）。VGAE 通过最大化变分下界 F_vgae = E_{q(Z^L|F,A)}[log p(A|Z^L)] − KL(q(Z^L|F,A) ‖ p(Z^L)) 训练（式 (16)），即重构项加 KL 正则项，p(Z^L) 为高斯先验。

**（5）图谱变换（第 V.3 节）。** 先用良性邻接矩阵构造拉普拉斯矩阵 L = D − A 并做特征分解 L = BΛB^T，得到图傅里叶变换（graph Fourier transform，GFT）基 B（正交矩阵）；把良性特征矩阵投影到该基上得到系数矩阵 S = B^T F；再从 VGAE 输出的重构邻接矩阵构造 L̂ = D̂ − Â、特征分解得到 B̂，于是重构特征矩阵 F̂ = B̂ S，取 F̂ 的第 j 列作为第 t 轮的初始恶意更新。

**（6）迭代操纵算法（Algorithm 1）。** 初始化 G(V, E, F)、总轮数 T、本地 epoch 数 T_l、学习率 η、步长 ε、agent 数 I 与 J、对偶变量 λ(1) ≥ 0、θ(1) ≥ 0、惩罚参数 ρ_λ > 0、ρ_θ > 0；每一轮依次执行：良性客户端本地训练并上传 → 攻击者构图、训练 VGAE、做 GST、用式 (9)(10)(11) 迭代优化 → 按式 (17) 得到 ∆w′_j(t)⋆ → 上传 → 服务器聚合 → 广播 → 所有本地 agent 用 w′_g(t) 更新。

**（7）消融变体（第 VI.B.5 节、图 8）。** "AugMP w/o AL penalty"去掉迭代算法中的增广拉格朗日惩罚项；"AugMP w/o GRL framework"去掉 GRL 框架，用基于良性更新均值的构造替代图引导生成。

## 5. 检测或防御所需的数据

本篇是攻击论文。下面先逐项列出**攻击本身需要的输入**（这也正是防守方可以看到或无法看到的可观测量），再写攻击留下的痕迹与它声称能绕过的检测。所有"在哪里采集"的措辞按论文原文与图 1(b) 的流程位置对应。

**（1）被观测的良性客户端本地 LoRA 增量 ∆w_i(t)（i 属于被攻击者观测的子集，共 B 个）。**
- 是什么：各良性客户端上传的向量化 LoRA 更新，即第 III.B 节式 (4) 的 w_i(t) = concat(vec(∆W_i^1(t)), …, vec(∆W_i^L(t)))；攻击中用其构造特征矩阵 F(t)。
- 在哪里采集：在传输/服务器接收边界被攻击者观测（第 III.C 节："can observe the local updates transmitted by a subset of benign agents"）；论文未说明窃听机制。
- 粒度：逐客户端、逐层（向量化拼接后是一个整体向量），逐轮。
- 是否跨轮历史：否，Algorithm 1 每轮独立构图并使用当轮观测。是否需要干净参考数据：否。是否需要额外计算：否（只需读取）。是否需要其他客户端的数据：是，需要其他客户端的更新（不是原始数据）。

**（2）服务器广播的全局 LoRA 参数/全局更新。**
- 是什么：上一轮全局模型 w_g(t−1)（或 w′_g(t−1)）与广播的全局更新 ∆w_g(t)（第 III.A、III.C 节；Algorithm 1 第 3 行）。
- 在哪里采集：聚合之后的下发边界（图 1 中的 "Wireless broadcast"）。
- 粒度：逐轮、整模型（或整更新向量）。是否需要跨轮历史：是（需要第 t−1 轮的全局模型）。是否需要干净参考数据：否。是否需要额外计算：否。

**（3）独立测试集 D_g。**
- 是什么：论文式 (7a) 中"an independent testing dataset used to evaluate the aggregated global LLM"，用于计算对抗目标 F(w′_g(t))。
- 在哪里采集：攻击者侧（评估用途），对应流程中的评估位置；论文未说明该数据集是否与全局测试集相同、是否与任务同分布。
- 粒度：逐样本（要在整个 D_g 上求平均损失）。是否需要跨轮历史：否。是否需要干净参考数据：是（这是攻击者必须持有的干净/独立参考数据）。是否需要额外计算：是（需要对聚合后的全局 LLM 做前向计算，且优化 ∆w′_j 时要把梯度回传到更新上）。

**（4）各轮的防御阈值 d_T(t) 与 δ_T(t)。**
- 是什么：服务器判定离群更新用的欧氏距离阈值（式 (5)）与余弦相似度阈值（式 (6)）。
- 在哪里采集：服务器聚合处的防御逻辑；第 IV 节明确假设"the thresholds d_T(t) 和 δ_T(t) are known to all participating agents in the FedLLMs system"。
- 粒度：逐轮。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：否。

**攻击会留下哪些痕迹（论文报告的可观测量）。**
- 恶意更新与全局更新的欧氏距离被约束在 d_T(t) 以内（式 (7b)），与良性更新的余弦相似度被约束在 δ_T(t) 以下（式 (7c)）；图 6 报告 AugMP 的距离统计与良性更新"closely overlap"，图 7 报告余弦相似度统计也"closely match"。
- 论文自身消融暴露了痕迹来源：去掉 AL 惩罚项后，恶意更新的欧氏距离范围为 1.0 到 2.8，而良性更新主要在 1.7 到 2.3，余弦相似度也明显偏离良性值（第 VI.B.5 节、图 8(b)(c)）；去掉 GRL 框架后，欧氏距离比良性值低约 60%，余弦相似度比良性值高约 80%（第 VI.B.5 节、图 8(e)(f)），因此更易被距离/相似度防御识别。
- 评估阶段的痕迹：被操纵的 Qwen2.5 在被误分类时仍生成流畅且看似合理的解释（图 5、第 VI.B.2 节），论文把这一点作为"操纵会扭曲推理与决策"的证据。**分析：** 这意味着仅检查输出文本的流畅性难以发现该攻击。

**论文声称能绕过哪些检测。** 论文只针对两类防御：基于欧氏距离的离群剔除（式 (5)，阈值 d_T，第 III.D 节）与基于余弦相似度的过度对齐剔除（式 (6)，阈值 δ_T，第 III.D 节），并声称"enabling it to evade conventional distance- and similarity-based defense methods"（摘要）与"bypass defense methods based on Euclidean distance and cosine similarity"（第 VI.B.3 节）。它也报告两个基线在这些指标上更显眼：RMP 的恶意更新距离显著大于良性，ALIE 显著小于良性；RMP 早期相似度异常低、后期高于良性，ALIE 全程明显高于良性（第 VI.B.3 节、图 6、图 7）。论文**未说明**该攻击对裁剪（clipping）、范数约束、中位数或 Krum 类 Byzantine 鲁棒聚合、谱方法、基于损失的检测等其它检测是否有效，也**未评估**任何这类防御。

## 6. 干预动作

**论文本身不提出任何检测或防御，因此没有"检测之后的干预动作"。** 论文第 III.D 节描述的（被攻击所针对的）防御动作是：对欧氏距离超过阈值 d_T 的更新"classified as an outlier and excluded from aggregation"，即**把越界更新剔除出聚合**；对余弦相似度聚合分数超过 δ_T 的更新，则"flagged as suspicious and discarded"，同样是**丢弃/剔除**。这两个动作都发生在**服务器聚合**处。

攻击侧的动作是：在**客户端上传前**用自己的构造结果替换本地更新（Algorithm 1 第 5 行），此后由服务器聚合与广播把影响扩散到所有 agent（Algorithm 1 第 6～8 行、图 1(b)）。论文没有报告任何"修复模型、回滚、加噪、重新加权、过滤样本"的动作。

## 7. 实验设置与主要结果

**设置（第 VI.A 节、表 II）。** 三个骨干：DistilBERT（约 6700 万参数，在 BookCorpus 与英文维基上预训练）、Pythia（约 1.6 亿参数，在 Pile 上自回归预训练）、Qwen2.5（约 5 亿参数，多语言语料预训练）。两个数据集：AG News（4 类，120,000 训练 / 7,600 测试）与 Yahoo! Answers（10 类，140 万训练 / 60,000 测试）。客户端：5 个良性 + 2 个恶意（第 VI.A 节）；表 II 给出 I = 5～7、J = 0～2。通信轮数 T = 50，本地 epoch 数 T_l = 5，服务器学习率 η = 1.0，本地学习率 5e−5，Dirichlet 浓度 0.3（即本地数据非独立同分布，non-IID；第 III.A 节也说明"local datasets follow non-IID distributions across agents"），批大小 32/64/128，测试批大小 128/256/512，最大序列长度 128/256，步长 ε = 0.001，选中参数维度 M = 500/1000，VGAE 第一/第二隐藏层 64/32，VGAE 训练 30 epoch、学习率 0.01，LoRA rank 8/32/128/256、scaling 16/64/256/512、dropout 0.1。论文未报告客户端参与率（实验按全部 7 个 agent 参与描述），也未给出惩罚参数 ρ_λ、ρ_θ 的具体取值。对比基线为 ALIE（文献 [35]，沿估计标准差方向平移良性更新均值）与 Gaussian random model poisoning（RMP，文献 [34]、[36]，从良性更新估计的高斯分布采样扰动）。

**指标。** 全局测试准确率（global testing accuracy，图 3）、本地 agent 平均测试准确率（local average testing accuracy，图 4）、逐更新与全局更新之间的欧氏距离（图 6）、逐 agent 本地更新之间的余弦相似度（图 7），以及定性样例（图 5）。

**关键结果。**
- 全局准确率下降（第 VI.B.1 节、图 3）：AG News 上 DistilBERT、Pythia、Qwen2.5 分别约下降 10%、26%、5.8%；Yahoo! Answers 上分别约下降 8.1%、13%、11%。摘要表述为"reducing the global LLM accuracy by up to 26%"。
- 本地平均准确率下降（图 4）：AG News 上 DistilBERT、Pythia、Qwen2.5 分别约下降 12%、22%、9%；Yahoo! Answers 上分别约下降 7.2%、3.5%、5.1%。摘要表述为"degrading the average accuracy of local LLM agents by up to 22%"。
- 与基线对比（第 VI.B.1 节）：ALIE 与 RMP 趋势相似，都能降低 DistilBERT 的准确率，但对 Qwen2.5 等更大骨干"effectiveness diminishes significantly"；AugMP 的退化幅度明显更大。
- 隐蔽性（第 VI.B.3 节、图 6、图 7）：AugMP 的距离与相似度统计与良性更新重叠；RMP 距离显著偏大、ALIE 显著偏小；RMP 相似度早期异常低、后期偏高，ALIE 全程明显偏高。
- LoRA 配置影响（第 VI.B.4 节、表 III，Yahoo! Answers 上的全局准确率）：DistilBERT 良性 r=8,α=16 为 70.89%（可训练参数 888,580，占 1.31%），AugMP 下 r=8,α=16 为 63.27%，r=32,α=64 为 63.50%（1,777,930，2.59%），r=128,α=256 为 61.20%（5,316,874，7.36%），全参数为 52.59%（68,739,092，100%）；Pythia 良性 64.04%（1,039,872，0.83%），AugMP 下 r=8 为 49.08%，r=32 为 44.75%（4,136,448，3.24%），r=128 为 53.31%（16,522,752，11.78%），全参数为 52.44%（127,833,600，100%）；Qwen2.5 良性 68.33%（1,090,304，0.22%），AugMP 下 r=8 为 53.94%，r=32 为 56.16%（4,334,336，0.87%），r=128 为 59.36%（17,310,464，3.39%），r=256,α=512 为 60.19%（34,611,968，6.55%）。论文的解读是：DistilBERT 上可训练参数空间变大会加强 AugMP（约 63.3% 降到 52.6%）；Qwen2.5 上冻结参数比例下降反而提升其被操纵下的适应性（53.9% 升到 59.4%，仍低于良性水平）；Pythia 呈非单调趋势。
- 消融（第 VI.B.5 节、图 8，AG News）：与完整 AugMP 相比，"w/o AL penalty"使性能退化幅度减少约 7%（DistilBERT）与约 16%（Pythia）；"w/o GRL framework"使退化幅度减少约 12%（DistilBERT）与约 20%（Pythia）。
- 样例研究（第 VI.B.2 节、图 5）：基于 Qwen2.5 的被操纵 FedLLMs 把两条 Business 类新闻分别错判为"World"和"Sci/Tech"，并给出连贯但编造的解释。

## 8. 开销

论文未报告计算、通信、存储开销的量化数字（没有训练时间、显存占用、通信量或存储量的对比），也没有与基线做开销比较。论文只给出硬件环境（NVIDIA A100 GPU，80 GB 显存；Python 3.12、PyTorch 2.10，第 VI.A 节）以及部分超参数（VGAE 训练 30 epoch、学习率 0.01、隐藏层 64/32；选中参数维度 M = 500/1000；步长 ε = 0.001；表 II）。**分析：** 攻击侧每轮需要训练一个 VGAE、对 M×M 拉普拉斯矩阵做特征分解、并做内层对偶迭代，这些都会带来额外计算，但论文没有给出任何量化开销，因此无法据此评估攻击成本；论文也未说明攻击者是否需要在每轮重新训练 VGAE。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文有明确依据的部分）。**
1. 攻击者能观测到"一部分"良性客户端上传的本地更新，以及服务器广播的全局更新（第 III.C 节）。论文未说明观测机制，也未说明被观测更新数 B 的取值。
2. 攻击者知道每轮的防御阈值 d_T(t) 与 δ_T(t)，第 IV 节原文理由是"the malicious agent participates as a legitimate client"。
3. 攻击者持有一个独立测试集 D_g 用于计算被操纵全局模型的损失（第 IV 节式 (7a)）；论文未说明该数据集与训练/测试集的分布关系。
4. 服务器不知道攻击者存在，按样本量加权平均聚合**全部**收到的更新，不做剔除（第 III.A 节、第 III.C 节）。
5. 防守方只使用欧氏距离与余弦相似度阈值两类判据（第 III.D 节）；阈值 d_T、δ_T 对所有参与方公开。
6. 各 agent 使用同一套 LoRA 适配层与同一向量化拼接顺序，使式 (4) 的统一更新维度一致（第 III.B 节）。**分析：** 这一条论文没有作为假设显式写出，但特征矩阵 F(t) 与邻接矩阵的构造要求各更新维度对齐。
7. 本地数据非独立同分布（第 III.A 节），实验用 Dirichlet 浓度 0.3（表 II）。
8. 任务为文本分类，模型规模在 6700 万～5 亿参数之间；攻击目标为测试集上的交叉熵类损失（式 (1)、式 (7a)）。
9. **分析：** 攻击时序要求先观测本轮良性更新再上传（Algorithm 1 第 3～5 行），论文未讨论这一前提在同步联邦学习中如何满足。

**论文自述的局限。** 论文没有独立的局限性章节。它在第 VI.B.4 节报告了效果对 LoRA 配置的敏感性（DistilBERT 上可训练参数越多攻击越强；Qwen2.5 上反而使被操纵模型的准确率由 53.94% 回升到 60.19%；Pythia 非单调），这是论文承认的效果边界，但没有讨论计算可行性、时间开销或部署条件。

**是否评估自适应攻击者。** 论文是攻击方，没有评估"防御方针对 AugMP 自适应调整"的情形：它只固定使用欧氏距离与余弦相似度两类阈值型防御作为对照（第 III.D 节、图 6、图 7），**论文未说明**是否测试过其它检测器或自适应阈值。因此不存在"自适应攻击者的结果"。

**分析：迁移到（真实、异构的）联邦 LoRA 微调时可能失效的假设。** 论文本身已经是联邦 LoRA 微调场景，因此这里讨论的是它的实验简化在更接近生产的联邦 LoRA 部署中是否还成立：
- **观测他方更新的前提**：真实系统里通常只有服务器能看到全部更新，跨设备客户端之间并不互相可见；若采用安全聚合（secure aggregation）或对更新加密/加噪，攻击者拿不到明文 ∆w_i(t)，特征矩阵 F(t) 与邻接矩阵 A(t) 就无法构造（论文未讨论安全聚合）。
- **LoRA 同构前提**：式 (4) 要求各客户端把各层 ∆W 向量化后按相同顺序拼接成同一维度；若各客户端 rank 不同、只上传 A 或 B、或适配的目标模块不同（异构 LoRA 是联邦 LoRA 的常见设定），统一维度与逐维对齐的图构造会失效。
- **阈值可知前提**：真实防守方不会公开阈值；一旦阈值私有或自适应，式 (7b)(7c) 的约束就无法直接写成已知边界，攻击需要改为对阈值的估计或查询。
- **任务与损失前提**：论文的实验是 4 类/10 类分类，目标是最大化测试集交叉熵式损失；生成式 LLM 微调没有单一准确率可最大化，"退化"的表现形式（如指令跟随能力、安全对齐、幻觉率）与可优化的标量目标都不一致，论文未在生成任务上验证。
- **规模与开销前提**：实验最大骨干约 5 亿参数，M 只取 500/1000；对 7B 级以上模型的 LoRA 微调，攻击者能否在每轮内完成 VGAE 训练与 M×M 特征分解、以及需要多大的 M 才有效，论文未说明。
- **客户端规模前提**：I = 5～7、J = 0～2（表 II）；在数十到数百客户端的真实联邦 LoRA 中，恶意占比与被观测更新数 B 会显著变化，论文未做规模扫描。
- **上传时序前提**：Algorithm 1 要求攻击者在本轮良性更新到达之后才提交；异步或严格同步且限时的聚合协议会使这一前提不成立，论文未讨论。

## 10. 对防护库设计的含义

**分析：**（以下全部是我的推断，不是论文原文。）

1. **通用采集点：服务器收到更新时（server_receive）的逐客户端、逐层、逐轮 LoRA 增量，以及聚合后的全局更新和上一轮全局参数，必须成对缓存。** 论文的欧氏距离（式 (5)）与余弦相似度（式 (6)）都以"单个更新对全局更新/其他更新"为参照，缺任何一侧都无法计算。这是与具体攻击无关的通用底座需求，对应论文第 III.D 节的防御视图。
2. **本论文特有的数据视图：把逐客户端更新按"选中参数维度子集"重排成 M×B 的特征矩阵，并提供"参数维度之间"（而不是只有"客户端之间"）的相关性视图。** 论文第 V 节、式 (12) 的图顶点是参数维度、节点特征才是客户端；表 II 给出 M = 500/1000 的截断维度。防护库若想复现或检测这类图结构操纵，插件接口必须允许自定义张量重排与子空间选择，而不能只暴露"每客户端一个向量"的视图。
3. **干净参考数据与额外前向需要成为可选的服务器侧钩子。** 攻击目标需要独立测试集 D_g 上的损失（式 (7a)）；对称地，防御插件若要做"聚合后模型的损失/行为一致性检查"，就需要在 server_post_aggregate 或 evaluation 钩子上拿到根数据集前向评估的能力。这是通用能力，这篇论文只是把它当作攻击者的既有资源。
4. **跨轮历史是通用刚需，本论文尤其如此。** AugMP 每一轮都把距离与相似度约束到与良性重叠（图 6、图 7），单轮几何统计几乎没有区分度；它的破坏靠广播在多轮累积（第 V 节末、Algorithm 1、图 1(b)）。因此插件接口应允许插件声明所需的历史窗口，并由底座缓存更新、全局模型与逐客户端几何量的时间序列；论文本身没有提供任何跨轮检测基线，这块需要自建。
5. **干预接口至少要支持"按阈值剔除"与"降权"两类动作，并支持把阈值当作不可公开的秘密状态。** 论文描述的防守动作是剔除越界更新（第 III.D 节），而 AugMP 恰恰以"已知阈值"为约束做优化（式 (7b)(7c)、第 IV 节）。因此阈值若作为公开配置暴露给客户端，就会直接成为攻击者的约束输入；插件接口应支持私有阈值、自适应阈值或对阈值本身加噪。这是通用设计教训，但由本论文的威胁模型直接触发。
6. **把这篇论文接入测试集时，要把它当作"隐蔽性基准"而不是"单一攻击"。** 论文只对照欧氏距离与余弦相似度两类防御（第 III.D 节、图 6、图 7），未评估裁剪、范数约束、中位数/Krum 类鲁棒聚合、谱方法或基于损失的检测。防护库应把"该攻击在其它可观测量（逐层范数、更新方向、谱特征、训练损失轨迹、输出文本一致性）上是否暴露"写成独立插件来测，而不是只复现论文用到的两个对照防御。

## 11. 原文依据

1. **第 III.C 节（Threat Model）**——支撑第 2 节"攻击者是能观测他人更新的恶意客户端"与第 5 节"采集位置在传输边界"：
   "the adversarial agent j ∈[1, J] acts as a legitimate but malicious agent and can observe the local updates transmitted by a subset of benign agents, as well as the global update broadcast by the edge server."

2. **第 III.C 节（Threat Model）**——支撑第 3 节"攻击在上传前生成恶意更新"：
   "Based on the shared benign updates, the adversary extracts their feature correlations and generates malicious updates ∆w′ j(t) that preserve benign-like parameter characteristics while embedding adversarial objectives."

3. **第 IV 节（Model Manipulation Formulation）**——支撑第 2 节"目标是无目标破坏（最大化全局损失）"与第 4 节"优化问题含几何隐蔽约束"：
   "These malicious updates are designed to maximize the global loss, denoted by F(w′ g(t)), while preserving consistency with benign updates in terms of Euclidean distance and cosine similarity."

4. **第 IV 节（Model Manipulation Formulation）**——支撑第 5 节"需要独立测试集 D_g 作为干净参考数据"：
   "where (7a) presents the loss function of the adversary (according to (1)), and Dg represents an independent testing dataset used to evaluate the aggregated global LLM."

5. **第 IV 节（Model Manipulation Formulation）**——支撑第 9 节"攻击者知道防御阈值"这一假设：
   "As the malicious agent participates as a legitimate client, the thresholds dT (t) and δT (t) are known to all participating agents in the FedLLMs system."

6. **第 III.D 节（Defense Model）**——支撑第 6 节"论文描述的对照防御动作是剔除出聚合"：
   "if the distance of an update exceeds a predefined threshold, denoted by dT , it is classified as an outlier and excluded from aggregation."

7. **第 I 节（Introduction，贡献列表）**——支撑第 4 节"核心思想是图引导合成良性似然更新"与第 5 节"声称绕过距离/相似度防御"：
   "AugMP constructs a feature correlation graph from benign updates and leverages the GRL framework to synthesize malicious updates with benign-like parameter characteristics, thereby evading widely adopted distance- and similarity-based defenses."

8. **第 V 节（The Proposed AugMP on FedLLMs）**——支撑第 4 节"用被观测良性更新构建 LoRA 参数相关图"：
   "Leveraging the observed benign updates ∆wi(t), the adversary models the internal correlation structure across LoRA parameters and encodes it as a graph G = (V, E, F)"

9. **第 VI.A 节（Experimental Implementation）**——支撑第 7 节"客户端数量与轮数设置"：
   "Specifically, we consider five benign agents and two malicious agents. The total number of communication rounds is set to 50, where each local agent updates its LoRA parameters wi(t) for five local iterations per round."

10. **第 VI.B.3 节（Stealthiness Analysis）**——支撑第 5 节与第 7 节"恶意更新的距离统计与良性重叠，服务器难以检测"：
    "AugMP generates malicious updates whose distance statistics closely overlap with those of benign updates, effectively concealing malicious updates within the local update population and making them difficult for the edge server to detect."

```json
{
  "key": "graphmanip2026",
  "title": "Graph Representation Learning Augmented Model Manipulation on Federated Fine-Tuning of LLMs",
  "year": 2026,
  "paper_type": "attack",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["update_postprocess", "server_aggregation"],
  "observables": [
    {
      "what": "被观测的良性客户端本地 LoRA 增量 ∆w_i(t)（用于构造特征矩阵 F(t) 与邻接矩阵 A(t)）",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "服务器聚合后广播的全局 LoRA 参数 w_g(t-1) 与全局更新 ∆w_g(t)",
      "where": "server_post_aggregate",
      "granularity": "model",
      "needs_history": true,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "攻击者持有的独立测试集 D_g（用于计算对抗目标 F(w′_g(t))，式 (7a)）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "各轮的欧氏距离阈值 d_T(t) 与余弦相似度阈值 δ_T(t)（论文假设所有参与方已知）",
      "where": "server_aggregate",
      "granularity": "round",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    }
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "恶意客户端能观测到一部分良性客户端上传的本地更新以及广播的全局更新（第 III.C 节）；论文未说明窃听机制与被观测客户端数 B",
    "距离阈值 d_T(t) 与相似度阈值 δ_T(t) 对所有参与方已知（第 IV 节）",
    "攻击者持有独立测试集 D_g 用于评估聚合后的全局 LLM（第 IV 节式 (7a)）",
    "服务器不知道攻击者存在，按样本量加权平均聚合全部收到的更新，不做剔除（第 III.A、III.C 节）",
    "防守方只使用欧氏距离式 (5) 与余弦相似度式 (6) 的阈值判据（第 III.D 节）",
    "所有 agent 使用同一套 LoRA 适配层与同一向量化拼接顺序，使式 (4) 的统一更新维度一致（第 III.B 节；论文未显式列为假设）",
    "本地数据非独立同分布，Dirichlet 浓度为 0.3（第 III.A 节、表 II）",
    "任务为文本分类，骨干规模为 6700 万至 5 亿参数（第 VI.A 节）",
    "攻击者的上传时刻晚于被观测的良性客户端（Algorithm 1 第 3 至 5 行的隐含时序；论文未讨论）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "III.C Threat Model",
      "supports": "第 2 节攻击者身份与第 5 节采集位置：恶意客户端可观测他人上传的更新与广播的全局更新",
      "text": "the adversarial agent j ∈[1, J] acts as a legitimate but malicious agent and can observe the local updates transmitted by a subset of benign agents, as well as the global update broadcast by the edge server."
    },
    {
      "section": "III.C Threat Model",
      "supports": "第 3 节攻击入口：恶意更新在上传前由攻击者基于良性更新相关性生成",
      "text": "Based on the shared benign updates, the adversary extracts their feature correlations and generates malicious updates ∆w′ j(t) that preserve benign-like parameter characteristics while embedding adversarial objectives."
    },
    {
      "section": "IV Model Manipulation Formulation",
      "supports": "第 2 节攻击目标为无目标破坏（最大化全局损失）与第 4 节几何隐蔽约束",
      "text": "These malicious updates are designed to maximize the global loss, denoted by F(w′ g(t)), while preserving consistency with benign updates in terms of Euclidean distance and cosine similarity."
    },
    {
      "section": "IV Model Manipulation Formulation",
      "supports": "第 5 节方法需要独立测试集 D_g 这一干净参考数据",
      "text": "where (7a) presents the loss function of the adversary (according to (1)), and Dg represents an independent testing dataset used to evaluate the aggregated global LLM."
    },
    {
      "section": "IV Model Manipulation Formulation",
      "supports": "第 9 节假设：攻击者知道防御阈值 d_T 与 δ_T",
      "text": "As the malicious agent participates as a legitimate client, the thresholds dT (t) and δT (t) are known to all participating agents in the FedLLMs system."
    },
    {
      "section": "III.D Defense Model",
      "supports": "第 6 节论文描述的对照防御动作是把越界更新剔除出聚合",
      "text": "if the distance of an update exceeds a predefined threshold, denoted by dT , it is classified as an outlier and excluded from aggregation."
    },
    {
      "section": "I Introduction (contributions)",
      "supports": "第 4 节核心思想与第 5 节声称绕过距离与相似度防御",
      "text": "AugMP constructs a feature correlation graph from benign updates and leverages the GRL framework to synthesize malicious updates with benign-like parameter characteristics, thereby evading widely adopted distance- and similarity-based defenses."
    },
    {
      "section": "V The Proposed AugMP on FedLLMs",
      "supports": "第 4 节用被观测良性更新构建 LoRA 参数相关图 G",
      "text": "Leveraging the observed benign updates ∆wi(t), the adversary models the internal correlation structure across LoRA parameters and encodes it as a graph G = (V, E, F)"
    },
    {
      "section": "VI.A Experimental Implementation",
      "supports": "第 7 节客户端数量与通信轮数设置",
      "text": "Specifically, we consider five benign agents and two malicious agents. The total number of communication rounds is set to 50, where each local agent updates its LoRA parameters wi(t) for five local iterations per round."
    },
    {
      "section": "VI.B.3 Stealthiness Analysis",
      "supports": "第 5 节与第 7 节恶意更新的距离统计与良性重叠，服务器难以检测",
      "text": "AugMP generates malicious updates whose distance statistics closely overlap with those of benign updates, effectively concealing malicious updates within the local update population and making them difficult for the edge server to detect."
    }
  ]
}
```
