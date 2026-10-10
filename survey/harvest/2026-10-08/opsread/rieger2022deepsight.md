# rieger2022deepsight：DeepSight（基于深度模型 inspection 的联邦学习后门过滤）

## 1. 方法一句话
输入是服务器在某一轮收到的 \(N\) 个本地模型更新 \(W_{t,1},\dots,W_{t,N}\) 与本轮全局模型 \(G_t\)；输出是对每一轮的两类判定与改动：（a）把模型更新逐个标记为 benign（良性）/ suspicious（可疑、疑似投毒），（b）把"可疑标签占比达到阈值"的整个聚类簇从聚合中剔除，（c）对保留下来的更新按动态中位数范数做 L2 裁剪（clipping），（d）用 FedAvg（Federated Averaging，联邦平均）聚合；在最后一轮还按簇分别聚合、按簇下发模型（§V-A、§V-B、§V-C，Fig. 2）。

## 2. 运行位置
全部三个阶段都在**服务器收到更新之后、聚合之前/之中**运行，不需要客户端与服务器之间额外往返（no round trip）。
- 过滤层（filtering layer）：服务器收到本轮全部更新后运行；它需要服务器对每个本地模型做前向推断（forward pass）来算 Division Differences（DDifs），因此必须在聚合前逐模型访问更新明文（§V-A，Alg. 1）。
- 裁剪层（clipping layer）：过滤之后、聚合之前运行（§V-B，式 12）。
- 聚合层（aggregation layer）：对剩余且已裁剪的更新用 FedAvg 聚合；只**在最后一轮**改为按簇聚合，每个客户端收到其所属簇的聚合模型（§V-C）。这一步改变了服务器下发的内容，但仍发生在同一轮的服务器端，不引入额外往返。
- 客户端侧不参与防御：DeepSight 完全在服务器上运行；论文明确要求服务器没有训练数据和测试数据（§III-A），且防御必须是全自主的、不需要手工配置或验证数据（需求 R3，§III-C）。
- 附带限制：DeepSight 需要服务器能看到单条更新，论文在结论里指出尚未实现与 secure aggregation（安全聚合）兼容的版本（§IX）。

## 3. 算子流水线

记 \(N\) 为本轮收到的模型数，\(G_t\) 为本轮全局模型，\(W_{t,k}\) 为客户端 \(k\) 提交的模型，\(P\) 为输出类别数（输出层神经元数），\(H\) 为每个输出层神经元连到上一层的连接数。

### 步骤 1：提取输出层偏置更新（output_layer_bias_delta）
- 输入：全局模型 \(G_t\) 的输出层偏置向量 \(b(G_t)\in\mathbb{R}^{P}\)，以及每个本地模型 \(W_{t,k}\) 的输出层偏置向量。
- 计算：对每个 \(k\) 求 \(\Delta b_k = b(W_{t,k}) - b(G_t)\)（Alg. 1 第 10–13 行的 `update_i ← output layer bias(W_i) - global bias`）。
- 输出：\(N\) 个 \(P\) 维向量。
- 出处：Alg. 1 第 10–13 行。

### 步骤 2：成对余弦距离矩阵（cosine_distance_matrix）
- 输入：\(N\) 个 \(P\) 维偏置更新向量（即"\(N\times P\)"）。
- 计算：对每一对 \((i,j)\) 计算 \(d_{\cos}(i,j)=1-\mathrm{COSINE}(\Delta b_i,\Delta b_j)\)，其中余弦为式 (13)；Alg. 1 第 9 行先把矩阵初始化为全 0，第 11–15 行双重循环填满（含 \(i=j\)，对角线为 0）。式 (13)(14) 与 App. H 证明该值对缩放不变。
- 输出：\(N\times N\) 的对称距离矩阵。
- 出处：Alg. 1 第 9–15 行；App. H 式 (13)(14)。

### 步骤 3：归一化更新能量（normalized_update_energy，NEUPs）
- 输入：\(W_{t,k}\) 与 \(G_t\) 的输出层参数：偏置 \(b_{t,k,i}\)、\(b_{t,G_t,i}\)，以及权重 \(w_{t,k,i,h}\)、\(w_{t,G_t,i,h}\)（\(i\) 为输出神经元，\(h\) 为上一层连接）。
- 计算：先算能量 \(E_{t,k,i}=|b_{t,k,i}-b_{t,G_t,i}|+\sum_{h}|w_{t,k,i,h}-w_{t,G_t,i,h}|\)（式 7），再按该模型所有输出神经元归一化 \(C_{t,k,i}=E_{t,k,i}^{2}/\sum_{j}E_{t,k,j}^{2}\)（式 8）。式 (8) 的求和下标在抽取文本中印作 \(j=0,\dots,P\)，与神经元编号 \(1..P\) 不自洽，具体求和范围论文未说明。
- 输出：每个模型一个 \(P\) 维 NEUP 向量 \(C_{t,k,\cdot}\)，即 \(N\times P\)。
- 出处：§IV-B 式 (7)(8)；Alg. 1 第 16 行（`neupsi ← NEUPs(Gt, Wi)`）。

### 步骤 4：阈值超越计数（threshold_exceeding_count，Threshold Exceedings）
- 输入：\(N\) 个 \(P\) 维 NEUP 向量。
- 计算：取模型内最大 NEUP \(C_{t,k,\max}=\max_{1\le i\le P}C_{t,k,i}\)（式 9）；设阈值 \(\xi_{t,k}=\max(0.01,\,1/P)\cdot C_{t,k,\max}\)（式 10，即 Threshold Factor 取 1 %，但下限为 \(1/P\)）；计数 \(TE_{t,k}=\sum_{i=1}^{P}\mathbf{1}\{C_{t,k,i}>\xi_{t,k}\}\)（式 11）。
- 输出：每个模型一个整数 \(TE_{t,k}\)。
- 出处：§IV-C 式 (9)(10)(11)；Alg. 1 第 17 行；Threshold Factor 的影响见 App. I 与 Fig. 8。

### 步骤 5：中位数分类（median_threshold_classify）
- 输入：\(N\) 个 \(TE\) 值。
- 计算：分类边界 = 所有模型 \(TE\) 的中位数除以 2（Alg. 1 第 21 行 `classificat boundary ← MEDIAN(thresh exds) / 2`）；模型被标为可疑（Alg. 1 中标签 1）当且仅当 \(TE_{t,k}\le\) 该边界（Alg. 1 第 22 行）。注意 §IV-C 正文用严格小于（"below this threshold"），与 Alg. 1 的 \(\le\) 不完全一致。论文的理由是假设多数客户端是良性的（§III-B），因此中位数至少不低于最低的良性值（§V-A2）。
- 输出：\(N\) 个二值标签，1 = poisoned/suspicious，0 = benign。
- 出处：Alg. 1 第 21–22 行；§IV-C；§V-A2。

### 步骤 6：随机探针前向（random_probe_forward）
- 输入：3 个随机种子、单条输入的维度 `input dim`（Alg. 1 的输入参数）。
- 计算：对每个种子生成一个 \(20000\times \text{input dim}\) 的随机输入矩阵（Alg. 1 第 18 行 `random matrix(seedsi, 20 000, input dim)`），分别喂给全局模型 \(G_t\) 和每个本地模型 \(W_{t,k}\)，取输出层概率 \(f(s_m;\cdot)\in\mathbb{R}^{P}\)。同一 seed 下所有模型共用同一批随机输入（Alg. 1 第 19 行一次调用 `DDIFs(rand input datai, Gt, W1 . . . Wn)`）。论文强调服务器没有真实数据，使用随机输入即可，因为关注的是相对全局模型的变化而不是正确预测（§IV-A）。
- 输出：每个种子下每个模型的 \(20000\times P\) 概率张量（实际只需保留步骤 7 的均值）。
- 出处：§IV-A；Alg. 1 第 18–19 行。随机输入的具体分布、`input dim` 的确定方式论文未说明。

### 步骤 7：除法差异（division_difference，DDifs）
- 输入：步骤 6 的概率。
- 计算：\(DDif_{t,k,i}=\frac{1}{N_{samples}}\sum_{m=1}^{N_{samples}}\frac{f(s_m;W_{t,k})_i}{f(s_m;G_t)_i}\)，其中 \(N_{samples}=20000\)（式 6）。用 3 个不同种子各算一次（§V-A1）。
- 输出：\(3\times N\times P\) 的 DDif 向量（Alg. 2 输入描述为"3 个列表，每个含 \(N\) 个 \(P\) 维向量"）。
- 出处：§IV-A 式 (6)；Alg. 1 第 19 行；§V-A1；Alg. 2 第 9–10 行。

### 步骤 8：逐特征 HDBSCAN 聚类（hdbscan_cluster）
- 输入：（a）\(N\times N\) 余弦距离矩阵（作为预先计算的距离矩阵）；（b）\(N\times P\) 的 NEUP（作为普通特征值）；（c）3 份 \(N\times P\) 的 DDif（作为普通特征值）。
- 计算：对（a）做一次 HDBSCAN(distance matrix)（Alg. 2 第 13 行）；对（b）做一次 HDBSCAN(values)（第 15 行）；对（c）的三个种子各做一次 HDBSCAN(values)（第 17 行），共 5 次聚类。论文选用 HDBSCAN 是因为它动态决定簇数，宁可多分簇也不要把不同数据分布的模型混在一起；并指出 k-means 需要预先给定簇数、可被随机更新攻击分散（App. B，Fig. 7）。
- 输出：5 组簇标号（簇划分）。
- 出处：Alg. 2 第 13、15、17 行；§V-A3；App. B。

### 步骤 9：簇共现距离矩阵（cluster_membership_distance）
- 输入：一组簇标号。
- 计算：`DistsFromClust`——对每一对模型 \((i,j)\)，若属于同一簇则距离置 0，否则置 1（Alg. 2 第 1–3 行的函数定义）。
- 输出：每个聚类一个 \(N\times N\) 的 0/1 距离矩阵（共 5 个：1 个余弦、1 个 NEUP、3 个 DDif 种子）。
- 出处：Alg. 2 第 1–3、14、16、18 行；§V-A3。

### 步骤 10：距离矩阵平均（average_distance_matrix）
- 输入：5 个 0/1 距离矩阵。
- 计算：先对 3 个 DDif 距离矩阵取平均（Alg. 2 第 19 行 `merged ddif clust dists ← AVG(...)`）；再把结果与 NEUP 距离矩阵、余弦距离矩阵三者取平均（第 21 行 `merged distances ← AVG(merged ddif clust dists, neup clust dists, cosine clust dists)`）。
- 输出：\(N\times N\) 的合并距离矩阵。
- 出处：Alg. 2 第 19、21 行；§V-A3。

### 步骤 11：在合并距离上再聚类（hdbscan_on_distance）
- 输入：合并距离矩阵。
- 计算：把它当作预先计算的距离矩阵再做一次 HDBSCAN（Alg. 2 第 22 行；正文写作"cf. line 25 of Alg. 2"，与算法列表行号不一致）。
- 输出：最终簇划分 `clusters`（集合的集合，元素为模型下标）。
- 出处：Alg. 2 第 22 行；§V-A3。

### 步骤 12：簇投票过滤（cluster_vote_filter，Poisoned Cluster Identification, PCI）
- 输入：最终簇划分 + 步骤 5 的二值标签。
- 计算：对每个簇 \(c\) 计算可疑标签占比 \(p_c=\big(\sum_{k\in c} label_k\big)/|c|\)（Alg. 1 第 28 行）；若 \(p_c<\tau=1/3\) 则接受该簇所有模型，否则**整簇剔除**（Alg. 1 第 29–31 行）。论文解释这是"对该簇标签的投票"，\(\tau=1/3\) 取这么敏感是因为"投毒模型被误标为良性比良性模型被误标为投毒更可能发生"（§V-A4）。
- 输出：接受模型集合 `accepted models`。
- 出处：Alg. 1 第 25–31 行；§V-A4。

### 步骤 13：裁剪到中位数范数（clip_to_median_norm）
- 输入：被接受的模型 \(W_{t,i}\) 与 \(G_t\)。
- 计算：\(S\) 取**所有更新**（论文写 "all updates, including the filtered model updates"）的 L2 范数的中位数；缩放因子 \(\lambda^{c}_{t,i}=\min\big(1,\;S/\lVert W_{t,i}-G_t\rVert\big)\)（式 12），缩放方式与式 (3) 相同，即 \(W'_{t,i}=(W_{t,i}-G_t)\lambda^{c}_{t,i}+G_t\)。论文指出良性更新的 L2 范数会随训练轮次下降，因此静态边界不合适；由于假设多数客户端良性，中位数必然落在良性更新的范数区间内（§V-B、§VII）。
- 输出：裁剪后的模型更新。
- 出处：§V-B 式 (12)；式 (3) 的缩放形式；§VII 的中位数论证。

### 步骤 14：FedAvg 聚合（federated_average）
- 输入：过滤并裁剪后剩余的更新。
- 计算：等权平均（论文明确所有模型更新权重相同，且不按数据集大小加权，以避免被恶意客户端谎报数据量利用，§II-A）。
- 输出：新的全局模型 \(G_{t+1}\)。
- 出处：§V-C；§II-A。

### 步骤 15：末轮按簇聚合与下发（clusterwise_federated_average）
- 输入：簇划分与各簇内的模型。
- 计算：只在**最后一轮**，聚合按簇进行，且"包括被过滤、被裁剪的模型"（论文原文），即同一簇的模型才聚合到一起，每个客户端收到为其所在簇聚合出的模型。
- 输出：每个簇一个聚合模型，按簇下发。
- 出处：§V-C。被过滤模型如何取得簇归属、以及"最后一轮"如何界定，论文未说明（簇划分本身覆盖全部 \(N\) 个模型，见 Alg. 2 输入）。

## 4. 采样与规模控制
- **探针（probes）**：DDifs 每次计算对每个模型使用 \(N_{samples}=20000\) 条随机输入向量，并用 3 个不同种子各算一遍，即每个模型每轮约 \(60000\) 次前向（§IV-A、§V-A1、Alg. 1 第 18–19 行）。这些随机输入不是真实数据（§IV-A）。
- **层（layers）**：只使用输出层。余弦距离只用输出层偏置；NEUPs 只用输出层的偏置与到上一层的权重（§IV-B、Alg. 1 第 10–16 行）。不涉及中间层。
- **参数坐标（coordinates）**：特征维度为输出类别数 \(P\)，即只沿输出层神经元方向统计（式 8、式 9、式 11），不逐坐标扫描全部参数。式 (11) 的分类阈值还依赖 \(1/P\)（式 10）。
- **客户端（clients）**：不对本轮客户端做抽样；Alg. 1 遍历全部 \(N\) 个收到更新的模型。仅实验设置中每轮随机选 100 个客户端参与训练（§VI-A1），这是实验配置而非防御的抽样策略。
- **轮次（rounds）**：每轮独立计算，不跨轮累积更新；论文在相关工作里明确批评 FoolsGold "把各轮更新累加后再比较，而不是聚焦当前轮"（§VIII-B），反衬 DeepSight 只看当前轮。

## 5. 超参数
| 名称 | 含义 | 论文取值 | 出处 |
| --- | --- | --- | --- |
| \(N_{samples}\) | 计算 DDifs 用的随机输入样本数 | 20 000 | §IV-A；Alg. 1 第 18 行 |
| DDif 种子数 | DDifs 用不同随机输入重复计算的次数 | 3 | §V-A1；Alg. 1 第 18–19 行；Alg. 2 第 17 行 |
| Threshold Factor（TF） | 计算 \(\xi_{t,k}\) 的比例因子 | 1 %，且取 \(\max(0.01,\;1/P)\) | 式 (10)；§IV-C；App. I/Fig. 8 中标注 TF=0.01 |
| 分类边界系数 | 可疑/良性分界 | 全部模型 \(TE\) 的中位数 ÷ 2 | Alg. 1 第 21 行；§IV-C；§V-A2 |
| \(\tau\) | PCI 中剔除整个簇所需的可疑标签占比 | 1/3 | §V-A4；Alg. 1 第 29 行 |
| 裁剪边界 \(S\) | L2 范数上界 | 动态：所有更新 L2 范数的中位数 | §V-B 式 (12) |
| 聚合权重 | 各客户端更新的权重 | 全部相等（不按数据量加权） | §II-A |
| HDBSCAN 参数 | 聚类的最小簇大小、最小样本数等 | 论文未说明（只说使用 McInnes et al. [20] 的实现） | §VI-B；§V-A3 |
| 3 个随机种子 | DDif 随机输入的种子 | 论文未说明具体取值（只说是不同种子） | Alg. 1 第 18 行 |

攻击侧参数（用于复现实验，不是防御超参数）：NIDS 场景良性客户端学习率 0.1、恶意客户端学习率 0.01、\(\alpha=0.7\)、PDR=50 %、PMR=25 %、10 个本地 epoch（§VI-A2）；NLP 场景 5000 轮、每轮 100 客户端、每客户端每轮 2 个 epoch、10 个恶意客户端（§VI-A1）。

## 6. 判定与动作
- **逐模型判定**：\(TE_{t,k}\le \text{MEDIAN}(TE)/2\) 记标签 1（可疑/投毒），否则 0（良性）（Alg. 1 第 21–22 行）。
- **逐簇判定与剔除**：簇内可疑标签占比 \(p_c\ge \tau=1/3\) 时整簇剔除；\(p_c<1/3\) 时整簇保留（Alg. 1 第 25–31 行）。因此被剔除的是**簇**而不是单个模型。
- **裁剪幅度**：\(\lambda^{c}_{t,i}=\min(1,S/\lVert W_{t,i}-G_t\rVert)\)，\(S\) 为本轮所有更新 L2 范数的中位数（式 12）。DeepSight 的裁剪只做降尺度，**不加噪声**（加噪是论文对比的 DP / FLGuard 的做法，§VIII-B、§VIII-A）。
- **聚合**：对保留且裁剪后的更新做等权 FedAvg（§V-C、§II-A）；最后一轮按簇分别聚合与下发，使攻击影响被限制在攻击者已控制的客户端内，并让良性客户端有机会"遗忘"后门（§V-C）。
- **是否跨轮累积**：否。所有指标（DDifs、NEUPs、\(TE\)、两个中位数边界 \(S\) 与分类边界）都在当前轮重算，论文强调动态取值且只关注当前轮（§VII、§VIII-B）。
- **鲁棒性论证**：NEUPs 与 Threshold Exceedings 对更新缩放/裁剪不变（定理 1、定理 2，§VII），余弦距离对缩放不变（App. H 式 13–14），因此攻击者单纯放大更新不能绕过这些判定；两个中位数边界因多数客户端良性而落在良性区间内，攻击者无法操纵（§VII）。

## 7. 需要的外部资源
- **不需要**：干净参考数据、根数据集（root dataset）、验证/测试数据、预训练检测器、额外模型。论文明确假设聚合服务器上没有任何训练或测试数据（§III-A），并把"防御必须全自主、不需要验证数据或良性更新 L2 范数的先验估计"作为需求 R3（§III-C）。
- **需要**：本轮全局模型 \(G_t\)；本轮收到的全部本地模型 \(W_{t,k}\)；单条输入的维度 `input dim`（Alg. 1 的输入参数，论文未说明其来源，实际应为模型输入维度）；输出类别数 \(P\)（用于式 10 的 \(1/P\)）；伪随机数生成器与 3 个种子；HDBSCAN 实现（McInnes et al. [20]，§VI-B）。
- **规模**：论文评测的模型规模为 NIDS 约 30 万参数（\(N=100\) 个模型）、CIFAR-10 约 900 万参数（\(N=10\)）、Reddit NLP 约 2000 万参数（\(N=100\)）（App. J）。DDif 的探针规模固定为每次 20 000 条、共 3 次，与模型参数量无关但随模型数线性增长。
- **隐私前提**：需要服务器看到单条更新明文，与 secure aggregation 不兼容（§IX 列为未来工作）。

## 8. 计算与存储开销
论文报告的开销（App. J）：
- IoT-Traffic（\(N=100\) 个模型，\(M=300\text{k}\) 参数）：过滤加裁剪后聚合共 1.15 分钟。
- CIFAR-10（\(N=10\)，\(M=9\text{M}\)）：1.06 分钟。
- Reddit（\(M=20\text{M}\)，\(N=100\)）：总计 6.02 分钟，其中单独计算 DDifs 就要 5.7 分钟。
- 成对距离矩阵规模按 \(O(n^2)\) 增长，但 NLP 场景下计算成对距离不到 1 秒；DDif 的计算量随 \(O(N)\) 增长；实验代码未并行化，而不同模型、不同种子的 DDif 相互独立，可并行把时间缩短约 300 倍（App. J）。
- 论文结论是"计算昂贵的操作随参与方数量线性增长，因此开销低"（§VI-D）。

分析：
- 主要开销来自步骤 6–7 的随机探针前向：每个模型每轮 \(3\times 20000=60000\) 次前向，加上全局模型的 60000 次（可复用），总前向次数随"\(N\times\) 探针数"线性增长，与模型参数量、输入维度成正比。
- 第二大开销是步骤 8–11 的 HDBSCAN：对 \(N\times N\) 距离矩阵操作，时间与空间随 \(N^2\) 增长（论文亦承认距离矩阵是 \(O(n^2)\)）。
- 存储上需要保存 \(N\times N\) 的余弦矩阵与 5 个 \(N\times N\) 的 0/1 距离矩阵，以及 \(N\times P\) 的 NEUP 和 \(3\times N\times P\) 的 DDif；不需要保存 \(20000\times P\) 的中间概率（只需按式 6 累加求均值）。
- 步骤 1–5 只涉及输出层少量参数，开销可忽略。

## 9. 实现时容易错的地方
论文明确强调或证明过的点：
- NEUPs 必须做逐模型归一化（式 8 除以该模型所有神经元能量的平方和），否则攻击者可以用一个客户端提交能量极大的更新来"稀释"其余投毒模型，使其看起来像良性（§IV-B）。
- 分类边界与裁剪边界都必须是**中位数**而不是均值，这样在多数客户端良性的假设下边界必然落在良性区间，攻击者无法操纵（§VII）。
- 聚类必须用 HDBSCAN 而不是 k-means：k-means 需要预设簇数，可被"部分客户端提交随机更新"的干扰攻击骗过，而 HDBSCAN 不会被分散，且能动态决定簇数（App. B，Fig. 7）。设计上宁可多分簇，也不要把不同数据分布的模型混进同一簇（§V-A3）。
- \(\tau\) 取 1/3 是刻意的偏保守设置：因为投毒模型被误判为良性比良性被误判为投毒更可能（§V-A4）；改变 Threshold Factor 会同时改变 TPR 与 FPR，TF 变小会抬高所有模型的 TE、降低 TPR，TF 变大会先抬高 FPR，甚至在 TF>0.05 时推动分类边界进而降低 TPR（App. I，Fig. 8）。
- 三个 DDif 种子必须用**不同的**随机输入，且同一 seed 下所有模型共用同一批输入，否则 DDif 之间不可比（§V-A1，Alg. 1 第 18–19 行）。
- 过滤层失效的边界情况：PDR 为 5 % 时一个投毒模型都识别不出；PDR 为 8 % 与 10 % 时 25 个投毒模型漏检 6 个，原因是聚类把投毒模型与良性模型混在一起、且 Threshold Exceedings 也判错（§VI-C3）。此时靠裁剪层兜底，整体 BA 仍为 0。
- 良性客户端只含单一标签数据的场景（如人脸认证）会让 Threshold Exceedings 分类器完全失效；论文的实验显示此时靠后两层仍能缓解攻击且不产生误报（App. E，Tab. VIII）。
- 个别设备类型下过滤层会一个投毒模型都不剔除（如 Ednet Gateway：投毒模型的 TE 平均 27.75，分类边界 29，良性模型平均 57），但因为良性簇与投毒簇被分开、裁剪边界又落在良性区间，BA 仍为 0（App. C）。
- 使用随机输入而非真实数据的合理性依据是"投毒模型对后门目标类的预测概率整体被抬高，与具体输入无关"（§IV-A）；实现时不能假设随机输入能产生有意义的预测。

论文没说清、实现时必须自己决定的地方：
- HDBSCAN 的具体超参数（最小簇大小、最小样本数、是否允许单点簇）以及 HDBSCAN 输出的噪声点（通常标为 −1）在 PCI 中算不算一个簇、如何处理。
- 随机输入的具体分布（均匀、正态、还是离散 token id）以及 `input dim` 的来源与取值；NLP 与 NIDS 的输入类型不同，Alg. 1 只把它当作外部参数。
- DDif 计算时若全局模型在某个神经元上的概率 \(f(s_m;G_t)_i\) 为 0 或接近 0，除法如何做数值保护；论文未提及。
- 式 (8) 的分母求和范围（抽取文本印作 \(\sum_{j=0}^{P}\)，与 \(1..P\) 的神经元编号冲突）；式 (7) 中权重求和的下标起点同样不明确。
- 式 (12) 只给出了缩放因子 \(\lambda^c\)，没有写出缩放后模型的显式表达式（只说与式 (3) 同理）。
- 裁剪边界 \(S\) 的"所有更新，包括被过滤的模型更新"到底指哪一集合：是包含被剔除簇的更新，还是只包含被接受但未裁剪的更新，含义不明确。
- "最后一轮"的界定，以及末轮按簇聚合时被过滤掉的模型如何参与（它们使用步骤 11 得到的簇归属吗）、每个被过滤客户端收到哪个模型，均未说明。
- Alg. 1 第 22 行用 \(\le\)，§IV-C 正文用严格小于，两者在恰好等于边界时的行为不同。
- 聚类为空、只有一个簇、或某个簇大小为 1 时 PCI 的行为未说明。
- 中位数在 \(N\) 为偶数时取哪一个值未说明。
- 每轮的 3 个随机种子是否跨轮固定、是否可复用，未说明。
- 三个种子的 DDif 距离矩阵直接平均，是否需要对种子间不一致做加权或异常剔除，未说明。
- 服务器如何获知输出类别数 \(P\)（Architecture 是否公开）未说明。

## 10. 原文依据
以下引文均逐字取自论文抽取全文（仅把连字符换行与 ﬁ 连字还原为普通空格/字母）。

1. 支撑步骤 6（随机探针前向、20000 条随机输入）：
> "For calculating the DDifs for a model update Wt,k of client k during training iteration t, we generate Nsamples = 20 000 random input samples sm (m ∈[0, Nsamples −1]) and provide them as input to model Wt,k."

2. 支撑步骤 7（DDif 计算公式，式 6）：
> "We then divide the probabilities f(sm; Wt,k)i predicted by the local model for each output neuron i by the corresponding neuron-speciﬁc prediction f(sm; Gt)i of the global model Gt"

3. 支撑步骤 3（NEUP 的能量定义，式 7）：
> "Then the Energy Et,k,i of the update for the output layer neuron i of the model that client k submitted in round t is given by"

4. 支撑步骤 4（阈值 \(\xi_{t,k}\) 的定义，式 10）：
> "We deﬁne the threshold ξt,k as 1 % of the maximal NEUP Ct,k,max of this client."

5. 支撑步骤 8–11（聚类集成：对余弦、NEUP、DDif 分别聚类）：
> "The algorithm ﬁrst clusters the cosine distances (cf. line 13 of Alg. 2), the NEUPs (cf. line 15 of Alg. 2) and the DDifs (cf. line 17 of Alg. 2)."

6. 支撑步骤 12（PCI 的整簇投票剔除规则）：
> "All models of a cluster remain if less than τ = 1/3 of them are labeled as suspicious. Otherwise, all models of this cluster are removed."

7. 支撑步骤 13（动态中位数裁剪边界 \(S\)）：
> "Therefore, we choose S dynamically based on the median of the L2-norms of all updates, including the ﬁltered model updates [28]."

8. 支撑步骤 15（末轮按簇聚合与下发）：
> "However, in the last round, the aggregation is performed clusterwise and includes also the ﬁltered, clipped models, s.t. only models from the same cluster are aggregated together and each client receives the model that was aggregated for the respective cluster."

```json
{
  "key": "rieger2022deepsight",
  "method": "DeepSight: 服务器端三层后门防御（过滤层 + 裁剪层 + 聚合层）；用 DDifs、NEUPs、Threshold Exceedings 特征做逐模型分类与 HDBSCAN 聚类集成，按簇投票剔除可疑簇，再对剩余更新做中位数范数裁剪与 FedAvg 聚合",
  "stages": ["server_receive", "server_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "提取输出层偏置更新",
      "operator": "output_layer_bias_delta",
      "input": "N 个本地模型 W_{t,k} 与全局模型 G_t 的输出层偏置向量，各 P 维",
      "output": "N 个 P 维偏置更新向量 Δb_k = b(W_{t,k}) - b(G_t)",
      "params": {},
      "source": "Alg. 1 行 10-13"
    },
    {
      "step": "成对余弦距离矩阵",
      "operator": "cosine_distance_matrix",
      "input": "N 个 P 维偏置更新向量",
      "output": "N×N 对称距离矩阵 d_cos(i,j) = 1 - COSINE(Δb_i, Δb_j)",
      "params": {},
      "source": "Alg. 1 行 9-15; App. H 式 (13)(14)"
    },
    {
      "step": "归一化更新能量 NEUPs",
      "operator": "normalized_update_energy",
      "input": "W_{t,k} 与 G_t 的输出层参数：偏置 b 与到上一层的权重 w（每个输出神经元 1 个偏置 + H 个权重）",
      "output": "N 个 P 维 NEUP 向量 C_{t,k,i}",
      "params": {},
      "source": "式 (7)(8); §IV-B; Alg. 1 行 16"
    },
    {
      "step": "阈值超越计数 Threshold Exceedings",
      "operator": "threshold_exceeding_count",
      "input": "N 个 P 维 NEUP 向量",
      "output": "N 个整数 TE 值",
      "params": {"threshold_factor": "max(0.01, 1/P)"},
      "source": "式 (9)(10)(11); §IV-C; Alg. 1 行 17"
    },
    {
      "step": "中位数分类为良性/可疑",
      "operator": "median_threshold_classify",
      "input": "N 个 TE 值",
      "output": "N 个二值标签（1 = 可疑/投毒，0 = 良性）",
      "params": {"boundary_factor": 0.5, "rule": "TE <= MEDIAN(TE)/2"},
      "source": "Alg. 1 行 21-22; §IV-C; §V-A2"
    },
    {
      "step": "随机探针前向",
      "operator": "random_probe_forward",
      "input": "3 个种子各生成一个 20000 × input_dim 的随机输入矩阵",
      "output": "每个种子下 G_t 与各 W_{t,k} 的 20000 × P 输出层概率",
      "params": {"n_samples": 20000, "n_seeds": 3},
      "source": "§IV-A; Alg. 1 行 18-19"
    },
    {
      "step": "除法差异 DDifs",
      "operator": "division_difference",
      "input": "同一批随机输入下本地模型与全局模型的输出层概率",
      "output": "3 × N × P 的 DDif 向量",
      "params": {"n_samples": 20000, "n_seeds": 3},
      "source": "式 (6); §IV-A; §V-A1; Alg. 1 行 19"
    },
    {
      "step": "逐特征 HDBSCAN 聚类",
      "operator": "hdbscan_cluster",
      "input": "N×N 余弦距离矩阵（precomputed distance）、N×P NEUP（values）、3 份 N×P DDif（values）",
      "output": "5 组簇标号（余弦 1 组、NEUP 1 组、DDif 3 组）",
      "params": {},
      "source": "Alg. 2 行 13, 15, 17; §V-A3"
    },
    {
      "step": "簇共现距离矩阵",
      "operator": "cluster_membership_distance",
      "input": "一组簇标号",
      "output": "N×N 的 0/1 距离矩阵（同簇为 0，否则为 1）",
      "params": {},
      "source": "Alg. 2 行 1-3, 14, 16, 18"
    },
    {
      "step": "距离矩阵平均合并",
      "operator": "average_distance_matrix",
      "input": "3 个 DDif 距离矩阵、1 个 NEUP 距离矩阵、1 个余弦距离矩阵",
      "output": "N×N 合并距离矩阵",
      "params": {},
      "source": "Alg. 2 行 19, 21"
    },
    {
      "step": "在合并距离上再聚类",
      "operator": "hdbscan_on_distance",
      "input": "N×N 合并距离矩阵",
      "output": "最终簇划分 clusters",
      "params": {},
      "source": "Alg. 2 行 22（正文写作 line 25）"
    },
    {
      "step": "簇投票过滤 PCI",
      "operator": "cluster_vote_filter",
      "input": "最终簇划分 + 步骤 5 的二值标签",
      "output": "被接受的模型集合（整簇保留或整簇剔除）",
      "params": {"tau": 0.3333333333333333, "rule": "sum(labels in cluster)/|cluster| < tau 则接受整簇"},
      "source": "Alg. 1 行 25-31; §V-A4"
    },
    {
      "step": "裁剪到中位数范数",
      "operator": "clip_to_median_norm",
      "input": "被接受的模型 W_{t,i} 与全局模型 G_t",
      "output": "裁剪后的更新 W'_{t,i} = (W_{t,i} - G_t) * λ + G_t",
      "params": {"S": "median of L2 norms of all updates (dynamic)"},
      "source": "§V-B 式 (12); 缩放形式同式 (3)"
    },
    {
      "step": "FedAvg 等权聚合",
      "operator": "federated_average",
      "input": "过滤并裁剪后剩余的更新",
      "output": "新的全局模型 G_{t+1}",
      "params": {"weights": "equal"},
      "source": "§V-C; §II-A"
    },
    {
      "step": "末轮按簇聚合与下发",
      "operator": "clusterwise_federated_average",
      "input": "簇划分 + 各簇内的模型（论文称还包括被过滤、被裁剪的模型）",
      "output": "每个簇一个聚合模型，客户端收到其所在簇的模型",
      "params": {"when": "last round only"},
      "source": "§V-C"
    }
  ],
  "sampling": [
    {"what": "probes", "how": "对每个模型用 20000 条随机输入向量做前向推断计算 DDifs，并用 3 个不同种子重复；同一 seed 下所有模型共用同一批随机输入", "size": "20000 × 3 = 60000 次前向/模型/轮"},
    {"what": "clients", "how": "不做客户端抽样，检查本轮收到的全部 N 个更新", "size": "N"},
    {"what": "layers", "how": "只用输出层：余弦用输出层偏置，NEUP 用输出层偏置与到上一层的权重", "size": "输出层"},
    {"what": "coordinates", "how": "只在输出层神经元（类别）维度上统计 NEUP 与 TE", "size": "P"},
    {"what": "rounds", "how": "每轮独立计算，不跨轮累积更新；论文批评 FoolsGold 把各轮更新累加后比较而非聚焦当前轮", "size": "仅当前轮"}
  ],
  "resources": [
    "本轮全局模型 G_t（服务器已有）",
    "本轮收到的 N 个本地模型更新（需明文可见，与 secure aggregation 不兼容）",
    "单条输入的维度 input dim（Alg. 1 的输入参数，来源论文未说明）",
    "输出类别数 P（用于式 10 的 max(0.01, 1/P)）",
    "伪随机数生成器与 3 个随机种子",
    "HDBSCAN 聚类实现（McInnes et al. [20]）",
    "不需要干净参考数据、根数据集、验证/测试数据或预训练检测器（§III-A、需求 R3）"
  ],
  "actions": ["exclude_client", "clip", "transform_broadcast"],
  "dominant_cost": "随机探针前向（DDifs）：每模型每轮 3×20000 次前向，随模型数与探针数线性增长（App. J 报告 NLP 场景 DDif 单项 5.7 分钟，总 6.02 分钟；IoT 场景 1.15 分钟，CIFAR-10 1.06 分钟）；其次是与 N^2 成正比的 HDBSCAN 距离矩阵，成对距离在 NLP 场景下耗时不到 1 秒，且 DDif 可按模型与种子并行（约 300 倍加速）",
  "underspecified": [
    "HDBSCAN 的具体超参数（最小簇大小、最小样本数）以及噪声点（-1）在 PCI 中的处理方式",
    "随机输入的具体分布与 input dim 的来源/取值（Alg. 1 仅把它作为参数传入）",
    "全局模型某个输出神经元概率为 0 或接近 0 时 DDif 除法的数值保护，论文未提及",
    "式 (8) 分母的求和范围（印作 j=0..P，与 1..P 的神经元编号冲突）；式 (7) 权重求和起点同样不明",
    "式 (12) 只给缩放因子，未给出缩放后模型的显式表达式（论文只说与式 (3) 同理）",
    "裁剪边界 S 的集合定义：'all updates, including the filtered model updates' 具体指哪些更新",
    "'最后一轮'的界定，以及末轮按簇聚合时被过滤模型如何参与、被过滤客户端收到哪个模型",
    "Alg. 1 行 22 用 <= 而 §IV-C 正文用严格小于，边界相等时的判定不一致",
    "聚类为空、只有一个簇、或簇大小为 1 时的行为",
    "N 为偶数时中位数的取值约定",
    "3 个随机种子是否跨轮固定或可复用",
    "三个种子的 DDif 距离矩阵直接平均，是否需要加权或剔除异常种子",
    "服务器如何获知输出类别数 P"
  ],
  "quotes": [
    {"supports": "步骤 6 随机探针前向：20000 条随机输入、无需服务器数据", "text": "For calculating the DDifs for a model update Wt,k of client k during training iteration t, we generate Nsamples = 20 000 random input samples sm (m ∈[0, Nsamples −1]) and provide them as input to model Wt,k."},
    {"supports": "步骤 7 DDif 计算公式（式 6）", "text": "We then divide the probabilities f(sm; Wt,k)i predicted by the local model for each output neuron i by the corresponding neuron-speciﬁc prediction f(sm; Gt)i of the global model Gt"},
    {"supports": "步骤 3 NEUP 的能量定义（式 7）", "text": "Then the Energy Et,k,i of the update for the output layer neuron i of the model that client k submitted in round t is given by"},
    {"supports": "步骤 4 阈值超越的阈值定义（式 10）", "text": "We deﬁne the threshold ξt,k as 1 % of the maximal NEUP Ct,k,max of this client."},
    {"supports": "步骤 8 聚类集成：对余弦距离、NEUP、DDif 分别聚类", "text": "The algorithm ﬁrst clusters the cosine distances (cf. line 13 of Alg. 2), the NEUPs (cf. line 15 of Alg. 2) and the DDifs (cf. line 17 of Alg. 2)."},
    {"supports": "步骤 12 PCI 整簇投票剔除规则", "text": "All models of a cluster remain if less than τ = 1/3 of them are labeled as suspicious. Otherwise, all models of this cluster are removed."},
    {"supports": "步骤 13 动态中位数裁剪边界 S", "text": "Therefore, we choose S dynamically based on the median of the L2-norms of all updates, including the ﬁltered model updates [28]."},
    {"supports": "步骤 15 末轮按簇聚合与按簇下发", "text": "However, in the last round, the aggregation is performed clusterwise and includes also the ﬁltered, clipped models, s.t. only models from the same cluster are aggregated together and each client receives the model that was aggregated for the respective cluster."}
  ]
}
```
