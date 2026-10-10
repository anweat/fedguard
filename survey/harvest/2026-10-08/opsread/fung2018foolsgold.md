# fung2018foolsgold：FoolsGold

## 1. 方法一句话

FoolsGold 的输入是联邦学习每一轮中服务器收到的所有客户端模型更新 Δ_{i,t}（第 t 轮第 i 个客户端的参数增量）以及服务器手中的全局模型 w_t；输出是给每个客户端分配的一个 [0,1] 区间的自适应学习率（论文记作 α_i，用以替代聚合时该客户端的权重），并用它加权求和得到新的全局模型，本身不产生"剔除某个客户端"的硬判定（第 5 节 Algorithm 1，第 5 节 "FoolsGold design"）。其核心判据是：sybil 之间存在共同的投毒目标，因此它们贡献的更新方向在期望上比诚实客户端彼此之间更相似（第 1 节与第 5 节）。

## 2. 运行位置

FoolsGold 完全运行在服务器端，位置是"服务器收到更新"之后、"服务器聚合"之时，即 `server_receive` → `server_aggregate`。客户端侧流程不变：客户端仍按本地 SGD 计算更新并上传（论文同时在 FEDSGD 与 FEDAVG 上验证，见第 6.2 节与图 5），FoolsGold 只改动聚合规则中的权重。它不需要任何客户端与服务器之间的额外往返（"needs_round_trip" 为 false）：相似度只用服务器本轮已收到的更新与它自己维护的客户端历史累积，指示性特征只用服务器手里的全局模型输出层参数。唯一前提是服务器能看到每个客户端的单独更新，论文第 3 节明确假设不使用 secure aggregation 这类混淆，"the central server is able to observe any individual client's model update at each iteration"。

## 3. 算子流水线

**步骤 1：接收更新并抽取输出层梯度**
- 输入：第 t 轮每个客户端 i 上传的更新 Δ_{i,t}（d 维，d 为模型参数量；FEDSGD 下是一次 SGD 更新，FEDAVG 下是本地多步累积后的更新），以及全局模型 w_t。
- 计算：从每个客户端的更新中只取输出层对应的坐标，用于后续相似度计算。单层 softmax 模型（MNIST、KDDCup、Amazon）整份参数就是输出层；VGGNet11 取最终全连接层；SqueezeNet 取 10 个 1x1 卷积核（第 6 节： "we only use the features in the ﬁnal output layer's gradients (fully connected layer in VGGNet and 10 1x1 convolutional kernels in SqueezeNet)"）。
- 输出：每个客户端一个输出层梯度片段（n×d_out）。
- 出处：第 5 节 "Feature importance"；第 6 节。

**步骤 2：计算指示性特征（indicative features）权重 S_t（硬筛选或软加权）**
- 输入：全局模型 w_t 的输出层参数。
- 计算：用输出层模型参数的幅值来衡量特征重要性，理由是"训练数据特征与梯度更新在 SGD 中被归一化，因此输出层参数的幅值直接对应它对预测概率的影响力"（第 5 节，引 Shokri 与 Shmatikov [37]）；这些特征可以按影响力做硬筛选（过滤）或软加权（重新加权），并且"normalized across all classes to avoid biasing one class over another"。论文未给出打分与归一化的具体公式，也未给出硬筛选的排序规则。
- 输出：S_t，即指示性特征集合（硬）或逐坐标权重向量（软），维度与输出层坐标数一致。
- 出处：Algorithm 1 line 4（"Let St be the weight of indicative features at iteration t"）与 line 7；第 5 节 "Feature importance"；第 6.4 节与图 8（把指示性参数比例从 0.001 扫到 1）。

**步骤 3：累积客户端更新历史 H_i**
- 输入：客户端 i 从第 1 轮到第 T 轮的输出层更新 Δ_{i,t}。
- 计算：H_i = Σ_{t=1}^{T} Δ_{i,t}，把单客户端每次迭代的更新聚合成一个历史向量（Algorithm 1 line 3）。论文用历史而非单轮更新来估计相似度，以对抗每轮随机性与攻击者注入的噪声（第 5 节 "Updates history"）。
- 输出：每个客户端一个历史向量 H_i（n×d_out）。
- 出处：Algorithm 1 line 3；第 5 节 "Updates history"；正文公式 cs_ij = cosine similarity(Σ_{t=1}^{T} Δ_{i,t}, Σ_{t=1}^{T} Δ_{j,t})。

**步骤 4：计算加权两两余弦相似度矩阵**
- 输入：所有客户端的 H_i（n×d_out）与 S_t。
- 计算：cs_ij = 以 S_t 加权的 H_i 与 H_j 的余弦相似度，j 遍历除 i 以外的所有客户端（Algorithm 1 lines 5–7）。正文给出的未加权形式为 cs_ij = cosine similarity(Σ_t Δ_{i,t}, Σ_t Δ_{j,t})；S_t 加权形式的具体表达式论文未说明。选余弦而非欧氏距离的理由是幅值可被攻击者操纵、方向不能（第 5 节 "Cosine similarity"）。
- 输出：n×n 相似度矩阵 CS，取值在 −1 到 1。
- 出处：Algorithm 1 lines 5–7；第 5 节 "Cosine similarity" 与 "Updates history"。

**步骤 5：逐行取最大相似度**
- 输入：CS。
- 计算：v_i = max_j cs_ij（Algorithm 1 line 8）。论文把 v_i 解释为客户端 i "acting as a sybil" 的强度，只要有至少一个这样的相似配对就能压低该客户端贡献（第 5 节，对应设计目标 3）。
- 输出：长度 n 的向量 v。
- 出处：Algorithm 1 line 8；第 5 节。

**步骤 6：Pardoning（赦免）重标定**
- 输入：CS 与 v。
- 计算：对每一对 (i, j)，若 v_j > v_i，则 cs_ij ← cs_ij · (v_i / v_j)（Algorithm 1 lines 12–14）。其目的是避免惩罚那些"与 sybil 相似、但自身最大相似度更高"的诚实客户端（第 5 节 "Pardoning"，对应设计目标 4）。
- 输出：修正后的相似度矩阵 CS′。
- 出处：Algorithm 1 lines 12–14；第 5 节 "Pardoning"。

**步骤 7：反转得到原始信任分**
- 输入：CS′。
- 计算：α_i = 1 − max_j(cs′_ij)（Algorithm 1 line 16，注释 "Row-size maximums"）。
- 输出：长度 n 的原始权重 α。
- 出处：Algorithm 1 line 16；第 5 节。

**步骤 8：按最大值归一化**
- 输入：α。
- 计算：α_i ← α_i / max_i(α)（Algorithm 1 line 18）。论文的动机是"假设系统中至少有一个客户端是诚实的"，因此把最大自适应值缩放为 1，保证至少一个客户端的更新不被修改，从而在纯诚实系统中不惩罚任何贡献（第 5 节，对应设计目标 1）。
- 输出：α ∈ [0, 1]，其中至少一个元素为 1。
- 出处：Algorithm 1 line 18；第 5 节。

**步骤 9：Logit 变换与裁剪**
- 输入：归一化后的 α。
- 计算：α_i ← κ ( ln[α_i/(1−α_i)] + 0.5 )（Algorithm 1 line 19），即中心在 0.5 的反 sigmoid 函数，κ 是置信参数；随后"任何超出 0–1 范围的取值都被裁剪并取相应的边界值"（第 5 节 "Logit"）。
- 输出：最终的逐客户端学习率 α_i ∈ [0, 1]。
- 出处：Algorithm 1 line 19；第 5 节 "Logit"；Appendix A 给出与 κ 相关的两个边界 β_m 与 β_g。

**步骤 10：加权聚合**
- 输入：各客户端本轮更新 Δ_{i,t} 与最终的 α_i。
- 计算：w_{t+1} = w_t + Σ_i α_i Δ_{i,t}（Algorithm 1 line 20）。
- 输出：新的全局模型 w_{t+1}。
- 出处：Algorithm 1 line 20。注意标准联邦聚合是 w_{g,t+1} = w_{g,t} + Σ_k (n_k/n) Δ_{k,t}（第 2 节），Algorithm 1 line 20 中没有样本量权重 n_k/n，α_i 取代了它。

可选组合：第 7 节把 FoolsGold 与参数 f = 1 的 Multi-Krum 串联，以覆盖单客户端攻击（图 12），此时 Multi-Krum 负责剔除、FoolsGold 负责给 sybil 群降权。

## 4. 采样与规模控制

- 样本抽样：论文未使用。防御不接触客户端训练数据，服务器也没有验证集（第 4 节 Challenge 1）。
- 客户端抽样：论文未使用。每轮使用全部参与客户端；实验规模为 10（MNIST、VGGFace2）、23（KDDCup）、50（Amazon）个诚实客户端，外加各攻击场景的 sybil（第 6 节、表 3）。
- 轮次截断/窗口：论文未使用。历史是对历次更新的累加，没有滑动窗口或衰减（Algorithm 1 line 3）。
- 层与参数坐标降维：使用。相似度只在全局模型的输出层参数上计算，非输出层不参与（第 5 节）；SqueezeNet 取 10 个 1x1 卷积核，VGGNet11 取全连接层，单层 softmax 即全部参数（第 6 节）。在输出层内部，论文第 6.4 节与图 8 评测了指示性参数比例从 0.001（MNIST 上 8 个特征）到 1（全部特征）的硬筛选，并评测了软加权。
- 参考数据/探针：论文未使用。第 3 节与第 4 节明确说明不使用辅助信息、不拥有验证数据集；第 4 节 Challenge 1 原文为 "We assume that FoolsGold, the system we design, does not possess a validation dataset."
- 需要注意的默认值：第 6 节末尾说明主实验使用 κ = 1，并且不使用历史梯度与显著特征过滤（二者分别在第 6.5 与 6.4 节单独评测），这与 Algorithm 1 默认包含历史和 S_t 的形式不一致，见第 9 节。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| κ（conﬁdence parameter） | logit 变换的缩放系数，控制两尾的分离强度 | 所有实验取 κ = 1 | 第 6 节 "FoolsGold is parameterized with a conﬁdence parameter κ = 1"；第 5 节 "Logit" 定义；Appendix A 给出 β_m ≥ 1 − e^{−0.5κ}/(1+e^{−0.5κ}) 与 β_g ≤ 1 − e^{0.5κ}/(1+e^{0.5κ})，并称 κ 可作为客户端数据分布的函数来保证收敛 |
| logit 中心偏移 0.5 | 公式里的常数项，把判决中心放在 0.5 | 0.5 | Algorithm 1 line 19；第 5 节 |
| 指示性特征比例（硬筛选） | 输出层参数中被当作指示性特征的比例 | 评测网格 0.001（MNIST 上 8 个特征）到 1（全部特征）；论文称低于 0.1（10%）后智能噪声失效，低到 0.01 时训练精度开始受损并出现假阳性 | 第 6.4 节与图 8；默认主实验不使用该筛选（第 6 节末） |
| 特征加权模式 | 硬筛选（hard）或软加权（soft） | 两种都评测，攻击率与训练精度"comparable"；默认主实验不使用 | 第 5 节；第 6.4 节与图 8 |
| 历史开关 | 是否在累积历史 H_i 上算相似度 | 默认主实验关闭；第 6.5 节用 A-5 MNIST、80% 投毒数据、batch size 1 做消融 | 第 6 节末；第 6.5 节与图 10 |
| Pardoning 开关 | 是否做 cs_ij ← cs_ij·(v_i/v_j) 重标定 | 默认开启；第 6.5 节用 KDDCup 的 A-AllOnOne 做消融（去掉后训练误差与目标类错误上升） | 第 6.5 节与图 10 |
| Logit 开关 | 是否做 logit 变换与裁剪 | 默认开启；第 6.5 节用 A-99 MNIST 做消融，去掉后攻击率达 92.9% | 第 6.5 节与图 10 |
| 历史长度 T | 累积多少轮更新 | 论文未给出固定值，Algorithm 1 写作 Σ_{t=1}^{T}；未说明是否在线累积到当前轮 | Algorithm 1 line 3 |
| 训练超参（非防御超参，用于复现实验） | 迭代数、batch size、优化器参数 | MNIST/KDDCup：3000 轮、batch 50；Amazon：100 轮、batch 10；VGGFace2：500 轮、batch 8、momentum 0.9、weight decay 0.0001、learning rate 0.001 | 第 6 节 |
| Multi-Krum 的 f（仅组合方案） | 容忍的 Byzantine 客户端数 | 对比实验中设为 sybil 数；与 FoolsGold 组合时取 f = 1 | 第 6.2 节；第 7 节 |
| M（攻击方参数，非防御参数） | 自适应攻击中 sybil 间余弦相似度阈值 | 攻击者侧参数，论文以 M = 0.01 为例说明需要每个对抗诚实客户端至少 10 个 sybil | 第 6.4 节、Algorithm 2、图 9 |

## 6. 判定与动作

- 判定形式：FoolsGold 不做二元剔除，而是输出连续权重 α_i（Algorithm 1 lines 16–19）。权重通过 1 − max_j cs 反转、按最大值归一化、再做 logit 变换与 [0,1] 裁剪得到，因此"最不合群"的客户端权重为 1，与 sybil 最像的客户端权重被压到接近 0。
- 阈值来源：论文没有独立的显式阈值参数；阈值的等价物来自 logit 与裁剪。Appendix A 定义 β_m 为"logit 函数低于 0 的点"，并给出 β_m ≥ 1 − e^{−0.5κ}/(1+e^{−0.5κ})；当 κ = 1 时该值为 0.6225，而 α_i = 1 − max cs 的 logit 在 max cs > 0.6225 时取负，裁剪后权重归零（分析：由 Algorithm 1 line 19 与 Appendix A 的 β_m 公式直接推导；论文该句写的是 "below βm"，与代数方向不一致，见第 9 节）。Appendix A 同时给出 β_g ≤ 1 − e^{0.5κ}/(1+e^{0.5κ})，即 κ = 1 时诚实客户端之间的理想最大相似度不超过 0.3775 时它们的权重保持为 1。
- 加权公式：聚合为 w_{t+1} = w_t + Σ_i α_i Δ_{i,t}（Algorithm 1 line 20），不再乘样本量比例 n_k/n。
- 裁剪/加噪幅度：论文没有噪声注入或范数裁剪；唯一的幅度处理是 logit 结果超出 [0,1] 时"clipped and rounded to its respective boundary value"（第 5 节）。模型更新本身的幅度不参与判定（第 5 节明确选择余弦相似度以忽略幅值）。
- 跨轮累积：是。FoolsGold 用历史更新累积 Σ_t Δ_{i,t} 计算相似度（Algorithm 1 line 3；第 5 节 "Updates history"），第 6.5 节图 10 显示 A-5 MNIST 下去掉历史后攻击率从 0.26% 升到 35.3%。但第 6 节末说明主实验默认不使用历史。
- 单客户端攻击：论文明确说明 FoolsGold 无法缓解单客户端攻击（第 7 节；图 5 与图 12），建议与 f = 1 的 Multi-Krum 组合（第 7 节，图 12：组合后训练精度 91.6%、攻击率 0.21%）。

## 7. 需要的外部资源

- 每个客户端每轮的明文单独更新：第 3 节假设服务器能观察任意单个客户端每次迭代的模型更新，即不使用 secure aggregation。
- 当前全局模型（尤其是输出层参数）：用于确定指示性特征 S_t（第 5 节 "Feature importance"）。
- 跨轮保存的每客户端历史累积向量 H_i（Algorithm 1 line 3）；若关闭历史则只需当前轮更新。
- 客户端集合与两两配对关系：需要构造 n×n 相似度矩阵（Algorithm 1 lines 5–7）。
- 明确不需要：干净参考数据、根数据集、验证集、预训练检测器、额外模型。第 4 节 Challenge 1 明确假设 FoolsGold 不拥有验证数据集；第 1 节称其 "requires no auxiliary information outside of the learning process"；第 8 节对比 AUROR [36] 时再次强调 FoolsGold 只用梯度相似度。
- 论文假设的前提条件（不是资源但影响可用性）：每个类别至少被一个诚实客户端持有（第 3 节："our solution requires that every class deﬁned by the model is represented in the data of at least one honest client"）。

## 8. 计算与存储开销

论文报告的开销：
- 第 6.6 节与图 11：相对未加防御的联邦学习（基准 1），FoolsGold 在 MNIST（CPU）上带来 1 到约 1.75 倍的相对 slowdown（10–50 客户端）；在 GPU 上训练 VGGFace2 时开销可忽略。
- 第 6.6 节：微基准测得 FoolsGold 算法总耗时 "less than 1.5 seconds, even with 50 clients"。
- 第 6.6 节：CPU 上最贵的一步是计算两两余弦相似度；论文提到可用已知的角距离加速方法 [2]，并说明自己的 Python 原型未优化。
- 第 6 节：原型共 600 行 Python，其中 FoolsGold 150 行，用 scikit-learn 计算余弦相似度。
- 第 6.5 节与图 10 的消融显示了各组件对效果（而非耗时）的贡献。

分析：
- 主要开销是步骤 4 的 n×n 加权余弦相似度，复杂度 O(n²·d_out)，随客户端数平方增长、随输出层维度线性增长。
- 步骤 3 的历史累积需要 O(n·d_out) 存储（每轮 O(n·d_out) 次加法）；关闭历史时只需当前轮 n×d_out。
- 步骤 2 需要遍历输出层参数规模 d_out 并在类别间归一化，为 O(d_out)。
- 步骤 5–9 都在 n×n 或 n 上操作，O(n²) 与 O(n)，相对可忽略。
- 论文未报告显存占用或网络开销；由于没有额外往返，通信量与标准联邦学习相同（分析：Algorithm 1 只改聚合权重）。

## 9. 实现时容易错的地方

论文明确强调的：
1. 只用输出层参数衡量特征重要性；"对于深度神经网络，我们不考虑非输出层数值的幅值，因为它们不直接映射到输出概率且更难推理"（第 5 节）。
2. 指示性特征要在类别之间归一化，避免偏向某一个类（第 5 节）。
3. 相似度必须用方向（余弦），不能用欧氏距离，因为 sybil 可以放大梯度幅值来制造"不相似"（第 5 节 "Cosine similarity"）。
4. Pardoning 是不对称的：只有 v_j > v_i 时才把 cs_ij 乘以 v_i/v_j（Algorithm 1 lines 12–14）。
5. 归一化（line 18）依赖"系统中至少有一个诚实客户端"的假设，用来保证至少一个客户端权重为 1（第 5 节）。
6. logit 结果必须裁剪回 [0,1] 并取边界值（第 5 节 "Logit"）。
7. 相似度要在历史累积向量上算而不是单轮更新上算，这是抗每轮方差与抗噪的关键（第 5 节 "Updates history"；第 6.5 节图 10）。
8. 相似度计算里 j 只遍历"其他客户端"（Algorithm 1 line 5），即必须排除对角线 cs_ii = 1，否则每行最大值恒为 1、所有权重会被压成 0。
9. 防御要求服务器能看到单个客户端更新，使用 secure aggregation 时该方法不可用（第 3 节）。
10. 单客户端攻击无法防御（第 7 节），需要与 Multi-Krum 等参数化方法组合。
11. 第 6 节末的默认配置（κ = 1，且不使用历史与显著特征过滤）与 Algorithm 1 的完整形式不一致，实现时必须先确定采用哪一套；论文没有解释这一处差异。

论文未说明、实现时必须自行决定的：
1. S_t 软加权的具体公式，以及指示性特征分数在类别间归一化的具体做法（第 5 节只有文字描述）。
2. 硬筛选的排序准则与截断比例的默认值（图 8 只给了扫描范围 0.001–1）。
3. 历史 H_i 的累积起点与是否在线：Σ_{t=1}^{T} 中的 T 是从第 1 轮到当前轮，还是固定窗口；论文未说明，也没有遗忘因子或衰减。
4. 客户端中途加入/退出、某轮缺席时历史向量如何维护。
5. 余弦相似度为负（范围 −1 到 1）时，α_i = 1 − max_j cs 可能大于 1，进入 logit 前是否先裁剪到 [0,1]；论文只规定 logit 输出超界才裁剪。
6. v_j = 0 时 pardoning 的除法、max_i(α) = 0 或客户端数为 0/1 时 line 18 的除法如何避免除零；论文只依赖"至少一个诚实客户端"的假设。
7. 相似度矩阵是否需要对称化，pardoning 之后是否要重新取行最大值（line 16 用的是 pardoning 后的 cs）。
8. 聚合时是否还要保留样本量权重 n_k/n；Algorithm 1 line 20 中没有这一项，但标准联邦聚合（第 2 节）有。
9. κ 与客户端数据分布之间的具体选择方法；Appendix A 只给出 β_m、β_g 的不等式，没有给出从数据分布计算 κ 的算法。
10. Appendix A 中条件 1 的表述（"similarity ... below βm" 时权重归零）与 β_m 公式的代数方向不一致，实现时需要自行判断按哪一侧归零。
11. 客户端数量很大时如何降低 O(n²) 相似度开销；论文只在第 7 节提到可用"加权随机子集"或"随机子集上度量相似度"，未给出具体方案。

## 10. 原文依据

1. 支撑步骤 4（加权余弦相似度矩阵，选余弦而非欧氏距离）："This is preferred to Euclidean distance since sybils can manipulate the magnitude of a gradient to achieve dissimilarity, but the direction of a gradient cannot be manipulated without reducing attack effectiveness."
2. 支撑步骤 2（指示性特征取自输出层参数幅值）："The indicative features are found by measuring the magnitude of model parameters in the output layer of the global model."
3. 支撑步骤 3（历史累积的构造）："FoolsGold maintains a history of updates from each client. It does this by aggregating the updates at each iteration from a single client into a single aggregated client gradient (line 3)."
4. 支撑步骤 5（取逐行最大相似度 v_i 及其鲁棒性含义）："We define vi as the maximum pairwise similarity for a client i, ensuring that as long as one such interaction exists, we can devalue the contribution while staying robust to an increasing number of sybils"
5. 支撑步骤 6（pardoning 的必要性）："Since we have weak guarantees on the cosine similarities between an honest client and sybils, honest clients may be incorrectly penalized under this scheme."
6. 支撑步骤 8（按最大值归一化到 1，保证至少一个客户端不被修改）："Since we assume at least one client in the system is honest, we rescale the vector such that the maximum adaption of the learning rate is 1 (line 18)."
7. 支撑步骤 9（logit 输出必须裁剪到 [0,1] 边界）："When taking the result of the logit function, any value exceeding the 0-1 range is clipped and rounded to its respective boundary value."
8. 支撑步骤 2 与步骤 3 的默认运行配置（主实验 κ = 1，且不使用历史与特征过滤）："For each experiment, FoolsGold is parameterized with a conﬁdence parameter κ = 1, and does not use the historical gradient or the signiﬁcant features ﬁlter"

```json
{
  "key": "fung2018foolsgold",
  "method": "FoolsGold",
  "stages": ["server_receive", "server_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "接收各客户端本轮更新并抽取输出层梯度",
      "operator": "slice_output_layer_gradient",
      "input": "第 t 轮每个客户端 i 上传的更新 Δ_i,t（d 维模型参数增量）与全局模型 w_t",
      "output": "n×d_out 的输出层梯度片段（n 为客户端数，d_out 为输出层参数量；单层 softmax 时 d_out = d）",
      "params": {},
      "source": "Section 5 Feature importance；Section 6（SqueezeNet 取 10 个 1x1 卷积核，VGGNet 取全连接层）"
    },
    {
      "step": "计算指示性特征权重（硬筛选或软加权）",
      "operator": "output_layer_magnitude_weights",
      "input": "全局模型 w_t 的输出层参数",
      "output": "指示性特征集合或逐坐标权重向量 S_t",
      "params": {"hard_filter_ratio": "论文扫描 0.001 到 1，未给默认值", "mode": "hard 或 soft，论文未给默认选择"},
      "source": "Algorithm 1 line 4 与 line 7；Section 5 Feature importance；Section 6.4 与 Figure 8"
    },
    {
      "step": "累积客户端更新历史",
      "operator": "accumulate_update_history",
      "input": "客户端 i 历次输出层更新 Δ_i,t",
      "output": "每客户端一个历史向量 H_i（n×d_out）",
      "params": {"T": "论文写作 Σ_{t=1}^{T}，未说明窗口或衰减"},
      "source": "Algorithm 1 line 3；Section 5 Updates history"
    },
    {
      "step": "计算 S_t 加权的两两余弦相似度矩阵",
      "operator": "cosine_similarity_matrix",
      "input": "所有客户端的 H_i（n×d_out）与特征权重 S_t",
      "output": "n×n 相似度矩阵 CS，取值 −1 到 1",
      "params": {"weighting": "S_t 加权，具体公式论文未说明", "diagonal": "j 只遍历其他客户端，对角线排除"},
      "source": "Algorithm 1 lines 5–7；Section 5 Cosine similarity 与 Updates history"
    },
    {
      "step": "逐行取最大相似度",
      "operator": "row_max_similarity",
      "input": "CS",
      "output": "长度 n 的向量 v",
      "params": {},
      "source": "Algorithm 1 line 8；Section 5"
    },
    {
      "step": "Pardoning 重标定",
      "operator": "pardoning_rescale",
      "input": "CS 与 v",
      "output": "修正后的 CS′",
      "params": {"rule": "当 v_j > v_i 时 cs_ij ← cs_ij · (v_i / v_j)"},
      "source": "Algorithm 1 lines 12–14；Section 5 Pardoning"
    },
    {
      "step": "反转得到原始信任分",
      "operator": "invert_max_similarity",
      "input": "CS′",
      "output": "长度 n 的原始权重 α",
      "params": {"rule": "α_i = 1 − max_j(cs′_ij)"},
      "source": "Algorithm 1 line 16；Section 5"
    },
    {
      "step": "按最大值归一化",
      "operator": "normalize_by_max",
      "input": "原始权重 α",
      "output": "α ∈ [0,1]，至少一个元素为 1",
      "params": {"rule": "α_i ← α_i / max_i(α)"},
      "source": "Algorithm 1 line 18；Section 5"
    },
    {
      "step": "Logit 变换并裁剪到 0 到 1",
      "operator": "logit_center_scale_clip",
      "input": "归一化后的 α",
      "output": "最终逐客户端学习率 α_i ∈ [0,1]",
      "params": {"kappa": 1, "center_offset": 0.5, "rule": "α_i ← κ(ln[α_i/(1−α_i)] + 0.5)，超界取边界值"},
      "source": "Algorithm 1 line 19；Section 5 Logit；Appendix A（β_m、β_g）"
    },
    {
      "step": "按 α 加权求和聚合",
      "operator": "weighted_sum_aggregate",
      "input": "各客户端本轮更新 Δ_i,t 与最终权重 α_i",
      "output": "新的全局模型 w_{t+1}",
      "params": {"rule": "w_{t+1} = w_t + Σ_i α_i Δ_i,t，不含样本量权重 n_k/n"},
      "source": "Algorithm 1 line 20；对比 Section 2 的标准联邦聚合公式"
    }
  ],
  "sampling": [
    {"what": "layers", "how": "只用全局模型输出层的梯度计算相似度，非输出层不参与", "size": "SqueezeNet 取 10 个 1x1 卷积核；VGGNet11 取最终全连接层；单层 softmax 取全部参数（Section 5、Section 6）"},
    {"what": "coordinates", "how": "在输出层参数内按影响力做硬筛选或软加权，并在类别间归一化", "size": "硬筛选比例在 0.001（MNIST 上 8 个特征）到 1（全部特征）之间扫描；默认主实验不使用该筛选（Section 6.4 与 Figure 8；Section 6 末）"}
  ],
  "resources": [
    "所有参与客户端的明文单独更新，要求不使用 secure aggregation（Section 3）",
    "当前全局模型，用于取输出层参数确定指示性特征（Section 5）",
    "跨轮保存的每客户端历史累积向量 H_i（Algorithm 1 line 3）",
    "客户端集合与两两配对关系，用于构造 n×n 相似度矩阵（Algorithm 1 lines 5–7）",
    "无需干净参考数据、根数据集、验证集、预训练检测器或额外模型（Section 4 Challenge 1；Section 1）"
  ],
  "actions": ["reweight"],
  "dominant_cost": "论文报告：CPU 上最贵的一步是两两余弦相似度，相对联邦学习的 slowdown 为 1 到约 1.75（MNIST，10–50 客户端，图 11）；GPU 上可忽略；微基准总耗时低于 1.5 秒（50 客户端，Section 6.6）。分析：主要开销是 n×n 加权余弦相似度，复杂度 O(n²·d_out)，随客户端数平方增长、随输出层维度线性增长；历史累积需要 O(n·d_out) 存储，其余步骤为 O(n²) 或 O(n)。",
  "underspecified": [
    "S_t 软加权的具体公式与类别间归一化方式未给出",
    "硬筛选指示性特征的排序准则与默认比例未给出",
    "历史 H_i 的累积起点、是否在线累积、是否有窗口或衰减未说明",
    "客户端中途加入、退出或某轮缺席时历史状态如何维护未说明",
    "余弦相似度为负导致 1 − max cs 大于 1 时，进入 logit 前是否裁剪未说明",
    "v_j = 0 时的 pardoning 除法与 max_i(α) = 0 时的归一化除法未说明边界处理",
    "pardoning 之后是否重新取行最大值、相似度矩阵是否对称化未说明",
    "聚合时是否仍乘样本量权重 n_k/n 未说明（Algorithm 1 line 20 中没有该项）",
    "κ 与客户端数据分布之间的具体选择方法未给出（Appendix A 只有 β_m、β_g 不等式）",
    "Appendix A 条件 1 的文字表述（similarity below β_m 时权重归零）与 β_m 公式的代数方向不一致",
    "Section 6 末的默认配置（不使用历史与特征过滤）与 Algorithm 1 完整形式的差异未解释",
    "客户端很多时降低 O(n²) 相似度开销的具体近似方案未给出（Section 7 只提到随机子集的方向）"
  ],
  "quotes": [
    {"supports": "步骤 4：选择余弦相似度而非欧氏距离", "text": "This is preferred to Euclidean distance since sybils can manipulate the magnitude of a gradient to achieve dissimilarity, but the direction of a gradient cannot be manipulated without reducing attack effectiveness."},
    {"supports": "步骤 2：指示性特征由输出层参数幅值确定", "text": "The indicative features are found by measuring the magnitude of model parameters in the output layer of the global model."},
    {"supports": "步骤 3：更新历史的累积构造", "text": "FoolsGold maintains a history of updates from each client. It does this by aggregating the updates at each iteration from a single client into a single aggregated client gradient (line 3)."},
    {"supports": "步骤 5：逐行最大相似度 v_i 及其鲁棒性作用", "text": "We define vi as the maximum pairwise similarity for a client i, ensuring that as long as one such interaction exists, we can devalue the contribution while staying robust to an increasing number of sybils"},
    {"supports": "步骤 6：pardoning 机制的必要性", "text": "Since we have weak guarantees on the cosine similarities between an honest client and sybils, honest clients may be incorrectly penalized under this scheme."},
    {"supports": "步骤 8：按最大值归一化保证至少一个客户端权重为 1", "text": "Since we assume at least one client in the system is honest, we rescale the vector such that the maximum adaption of the learning rate is 1 (line 18)."},
    {"supports": "步骤 9：logit 结果超出 0 到 1 时取边界值", "text": "When taking the result of the logit function, any value exceeding the 0-1 range is clipped and rounded to its respective boundary value."},
    {"supports": "步骤 2 与步骤 3 的默认运行配置（κ = 1，不使用历史与特征过滤）", "text": "For each experiment, FoolsGold is parameterized with a conﬁdence parameter κ = 1, and does not use the historical gradient or the signiﬁcant features ﬁlter"}
  ]
}
```
