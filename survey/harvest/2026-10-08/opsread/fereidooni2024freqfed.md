# fereidooni2024freqfed：FreqFed

## 1. 方法一句话

FreqFed 是一个服务器端的鲁棒聚合（resilient aggregation）方法：输入是第 t 轮全部 K 个客户端上传的本地模型权重 W_i^t（论文把本地模型参数称为 model update），服务器对每个 W_i^t 做二维离散余弦变换（2D Discrete Cosine Transform, DCT），只保留低频三角区域的 DCT 系数组成向量 F_i^t，再用 1 减余弦相似度（cosine similarity）构造 K×K 距离矩阵、跑 HDBSCAN（Hierarchical Density-Based Spatial Clustering of Applications with Noise）聚类，输出"哪些客户端被接受"的判定（最大簇成员的索引 b_1,…,b_L，其余客户端被剔除），并把被接受客户端的本地模型按 L 均分聚合成下一轮全局模型 G^(t+1)（Algorithm 1；Section IV-B、IV-C）。

## 2. 运行位置

FreqFed 全部逻辑运行在服务器侧，客户端侧的训练流程不被修改。

- 服务器下发前（server_distribute）：论文未描述任何针对下发模型 G^t 的处理，仍按标准 FL 下发（Section II-A、Algorithm 1 line 1–3）。
- 客户端训练前（client_pre_train）/ 客户端每个训练步（client_pre_step）：FreqFed 不做任何事；客户端只执行算法 1 lines 8–12 的普通本地训练。
- 客户端上传前（client_post_train）：FreqFed 不做任何事，客户端直接上传 W_i^t（Algorithm 1 line 3 由服务器调用 ClientUpdate 获得）。
- 服务器收到更新（server_receive）：对**每个到达的**客户端更新做 DCT（line 4）与低频筛选（line 5），得到 F_i^t。这两步是逐客户端的，可以边收边算。
- 服务器聚合（server_aggregate）：必须等所有 K 个客户端的更新都到齐后才做聚类，因为 K×K 距离矩阵与 HDBSCAN 需要全部 F_i^t（Algorithm 1 line 6、lines 19–30；Section IV-C 明确写 "Once all clients have submitted their model updates, the Clustering procedure is invoked"），随后按 line 7 聚合成 G^(t+1)。
- 聚合之后（server_post_aggregate）：论文未描述任何后处理（没有裁剪、加噪或二次检测）。Section IV-B 说的 "Model aggregation … in Step 4" 就是聚合本身。
- 训练之外：论文未使用。
- 额外往返（round trip）：不需要。检测只用本轮已经上传的模型完成，不需要服务器根数据集（对比 FLTrust/Sageflow，Section VI-B），也不需要把聚合结果发回客户端做验证（对比 BaFFLe，Section VI-A）。

## 3. 算子流水线

总体流程对应 Algorithm 1：服务器循环 t∈[1,T]（line 1），对每个客户端 i∈[1,K]（line 2）取更新（line 3）、做 DCT（line 4）、做低频筛选（line 5）；全部到齐后聚类（line 6）并聚合（line 7）。

**步骤 1：客户端本地训练（标准 FL，FreqFed 不修改）**
- 输入：上一轮全局模型 G^t（第一轮为随机初始化模型 G^1）与客户端 i 的私有数据 d_i。
- 计算：把本地数据切成大小 B 的批 β（line 9）；对每个本地 epoch e∈[1,E_i]（line 10）、每个批 b∈β（line 11）执行 w ← w − η_i ∇ℓ(w; b)（line 12）。损失函数 ℓ 的具体形式论文未说明。
- 输出：客户端 i 的本地模型 W_i^t（论文称其为该客户端的 model update）。
- 出处：Algorithm 1 lines 8–12；Section IV-C。

**步骤 2：把权重张量整理成方阵（论文未说明具体做法）**
- 输入：W_i^t 的全部参数张量（多层、非方阵）。
- 计算：论文只说明滤波阶段处理的是"一个 DCT 系数的方阵 V"（"The algorithm starts with a square matrix of DCT components V"），但没有说明如何把多层、形状各异的权重张量拼成一个方阵（逐层各自 DCT 后拼接，还是整体展平/填充成方阵，论文均未说明）。
- 输出：一个 N×M（论文语境下为方阵）的实数矩阵 x。
- 出处：Section IV-C；Algorithm 1 lines 13–18。

**步骤 3：二维 DCT**
- 输入：N×M 的权重矩阵 x（即客户端 i 的权重方阵）。
- 计算：按公式 (2) 做二维 DCT：X(k,l) = Σ_{m=0}^{M−1} Σ_{n=0}^{N−1} c1·c2·x(m,n)·cos(kπ/(2M)·(2m+1))·cos(lπ/(2N)·(2n+1))；其中 k=0 时 c1 = sqrt(2/(MN))，k=1,…,M−1 时 c1 = 1；l=0 时 c2 = sqrt(2/(MN))，l=1,…,N−1 时 c2 = 1（Eq. (2) 原文如此）。论文强调 DCT 是能量紧致（energy compaction）变换，系数按重要性升序排列，第一个系数正比于序列均值。
- 输出：N×M 的 DCT 系数矩阵 V_i^t。
- 出处：Eq. (2)；Section II-C；Algorithm 1 line 4。

**步骤 4：低频三角筛选（Filtering）**
- 输入：V_i^t（系数矩阵，论文视作方阵，边长记为 |V|）。
- 计算：初始化空向量 F；对 i∈[0,⌊|V|/2⌋]、j∈[0,⌊|V|/2⌋]，若 i + j ≤ ⌊|V|/2⌋ 则把 V_ij 追加到 F（论文写作 "F ∪ V_ij"）。即只保留左上角的低频三角区域。
- 输出：低频系数向量 F_i^t。
- 出处：Algorithm 1 lines 13–18；Section IV-C；Section IV-B（"extracting the low-frequency components, which are then stored in a vector"）。

**步骤 5：两两余弦距离矩阵**
- 输入：K 个低频向量 F_1,…,F_K。
- 计算：初始化 K×K 距离矩阵为零矩阵（line 20）；对每个 i、j 计算 distances_matrix[i][j] = 1 − CosineSim(F_i, F_j)（line 23），并令 distances_matrix[j][i] = distances_matrix[i][j]（line 24），因此矩阵对称。
- 输出：K×K 对称余弦距离矩阵。
- 出处：Algorithm 1 lines 19–24；Section IV-C。

**步骤 6：HDBSCAN 密度聚类**
- 输入：K×K 余弦距离矩阵。
- 计算：调用 HDBScan(distances matrix) 做基于密度的聚类（line 25）。论文只说明 HDBSCAN 基于密度可达性、能处理不同大小/形状的簇并且能识别噪声与离群点（Section II-D），具体的聚类参数论文未说明。
- 输出：cluster_ids，每个客户端对应一个簇 ID。
- 出处：Algorithm 1 line 25；Section II-D；Section IV-B（"automated clustering approach (HDBSCAN)"）。

**步骤 7：取最大簇作为接受集合**
- 输入：cluster_ids。
- 计算：max_cluster ← argmax_a |{a ∈ cluster_ids}|（line 26），即成员数最多的簇；遍历所有客户端 i，若 cluster_ids_i = max_cluster 则把 i 加入集合 B（lines 28–30）。
- 输出：被接受的客户端索引 B = (b_1,…,b_L)，L 为最大簇的大小。
- 出处：Algorithm 1 lines 26–30；Section IV-C（"The number of accepted models L is the size of the most significant cluster identified by the algorithm"）。

**步骤 8：对保留模型取平均（聚合）**
- 输入：被接受客户端的本地模型 W_{b_1}^t,…,W_{b_L}^t（注意是本地模型参数本身，不是相对全局模型的差值）。
- 计算：G^(t+1) ← Σ_{l=1}^{L} W_{b_l}^t / L（line 7），即按被接受模型数量 L 做简单平均。Section IV-B 把这个聚合称为 Federated Averaging（引用 Section II-A 的 Eq. (1)），但 Algorithm 1 line 7 与 Section IV-C 的文字描述里**没有**出现 Eq. (1) 的 n_i/n 样本数权重。
- 输出：下一轮全局模型 G^(t+1)。
- 出处：Algorithm 1 line 7；Section IV-B；Section IV-C。

## 4. 采样与规模控制

- 客户端：论文未使用抽样。每一轮遍历全部 K 个客户端（Algorithm 1 line 2），K 的取值论文未给出。
- 轮次：论文未使用抽样，按 T 轮循环（Algorithm 1 line 1），T 的取值论文未给出。
- 参数坐标：有降维。DCT 之后只保留系数矩阵中满足 i + j ≤ ⌊|V|/2⌋（且 i, j ≤ ⌊|V|/2⌋）的低频三角区域（Algorithm 1 lines 15–18）。论文未给出 |V| 的数值，也未给出保留系数的具体个数；按算法结构，保留数量为 (⌊|V|/2⌋+1)(⌊|V|/2⌋+2)/2，相对整个 |V|×|V| 系数矩阵约为 1/8（分析）。
- 层：论文未使用逐层抽样或逐层筛选；论文没有说明方阵 V 与网络层之间的对应关系。
- 参考数据/探针：论文未使用。FreqFed 不需要任何服务器端样本、参考数据或探针样本（Section VI-C 明确把它与需要数据样本的 Zeng et al. 方法区分开）。
- 说明：论文中出现的 iid rate、PDR（Poison Data Rate）、PMR（Poisoned Model Rate）都是**攻击/实验设置**，不是 FreqFed 对数据或客户端做的采样。

## 5. 超参数

FreqFed 自身几乎没有可调超参数，论文也没有报告调参过程。

- 低频保留比例（低频三角截断阈值）：含义是 DCT 系数矩阵中保留哪些坐标；论文取值为规则 i + j ≤ ⌊|V|/2⌋（且 i, j ∈ [0,⌊|V|/2⌋]），出处 Algorithm 1 lines 15–18 与 Section IV-C。这里 |V| 的数值论文未说明（取决于步骤 2 的方阵构造方式）。论文没有把它写成可调超参数，也没有给出其他候选取值。
- 距离度量：固定为 1 − CosineSim(F_i, F_j)，出处 Algorithm 1 line 23。这是固定定义而非可调超参数。
- HDBSCAN 参数（min_cluster_size、min_samples、cluster_selection_method、是否对距离做变换等）：论文未说明；Algorithm 1 line 25 只写了 HDBScan(distances matrix)，Section II-D 只介绍 HDBSCAN 的一般性质。
- 客户端本地训练超参数：批大小 B、本地 epoch 数 E_i、学习率 η_i，出处 Algorithm 1 lines 9–12；论文正文与附录 -A 都没有给出取值。
- 客户端数 K、训练轮数 T：Algorithm 1 的输入（line 1–2），论文未给出具体取值。
- 攻击者规模假设（不是超参数，但是方法的适用条件）：被完全控制的恶意客户端数 k_A < K/2（Section III）。
- 复现实验用到的攻击侧/数据侧设置（不是 FreqFed 的超参数）：Table II 用 PMR = 49%、iid = 0.7；Table III 用 PDR = 50%、PMR = 30%、iid = 0.9；Table IV 用 PDR = 50%、PMR = 25%；Table V 用 PDR = 0.49/0.3/0.2 与 PMR = 0.49/0.3/0.2；Table VI 用 PDR = 25%、PMR = 49%；Table VII 用 PDR = 50%、PMR = 25%、iid = 0.7 与 α = 0.7；Table VIII 用 PDR = 50%、PMR = 30%、iid = 0.7；Table IX 用 iid = 0.8、PDR ∈ {10,15,50,100}；Table X 用 iid = 0.0、PMR ∈ {10%,…,49%}；Table XI 用 PMR = 25%；Table XII 用 PMR = 49%、iid = 0.7。iid rate 的定义见 Section V-A。

## 6. 判定与动作

- 判定规则：没有显式距离阈值。判定完全由 HDBSCAN 在余弦距离矩阵上的密度聚类结果决定，然后取成员数最大的簇作为"良性/接受"集合（Algorithm 1 line 26；Section IV-C）。论文没有给出任何阈值参数（Section III 提到的阈值 τ 是**攻击者**为规避检测而约束自身更新差异用的，不是 FreqFed 的判定阈值）。
- 动作：剔除（exclude_client）。不在最大簇内的客户端更新被直接丢弃，不参与聚合，也不做加权或降权。
- 聚合公式：对被接受集合 B = (b_1,…,b_L) 做 G^(t+1) = Σ_{l=1}^{L} W_{b_l}^t / L（Algorithm 1 line 7；Section IV-C 的文字描述）。注意这是对**本地模型本身**的平均，等价于给每个被接受客户端权重 1/L。Section IV-B 把它称作 Federated Averaging，但算法与正文都未使用 Eq. (1) 中的 n_i/n 样本数权重。
- 裁剪或加噪：论文未使用。FreqFed 不做范数裁剪、不添加噪声（Section VI-A 明确把 FreqFed 与依赖 L2 范数限制和加噪的 DP 类防御区分开）。
- 是否跨轮累积：论文未描述任何跨轮状态。DCT、筛选、聚类、聚合都在每一轮的循环体内独立执行（Algorithm 1 lines 1–7），没有跨轮的分数、信任值或历史窗口。
- 边界条件：论文只说当 k_A < K/2 成立时有效；若 PMR ≥ 50%，恶意模型可能构成最大簇从而被误判为良性（Section V-B1）。L = 0、聚类全为噪声、簇大小打平等情况的动作，论文未说明。

## 7. 需要的外部资源

- 不需要任何外部资源：不需要干净参考数据、根数据集（root dataset）、预训练检测器、对齐前后的权重或额外的模型。服务器只需要本轮 K 个客户端上传的本地模型更新 W_i^t（Algorithm 1 lines 2–5）。
- 规模：服务器每轮需要同时持有 K 个完整本地模型（以及它们的 DCT 系数矩阵与低频向量）。论文 Table I 给出各实验模型的参数量量级：Reddit/LSTM 约 20M、IoT-Traffic/GRU 约 507k、Cifar-10/ResNet-18 Light 约 2.7M、MNIST/CNN 约 431k、EMNIST/LeNet 约 66k、TIMIT/LSTM 约 12M、PROTEINS/GraphSage 约 102k、NCI1/GAT 约 101k、D&D/GCN 约 106k、GatedGCN 约 104k、MoNet 约 102k（Table I）。
- 论文在 Section VI-B、VI-C 中明确指出需要服务器端数据的防御（FLTrust、Sageflow）和需要访问训练样本的频域防御（Zeng et al.）具有部署限制，而 FreqFed 不做这类要求。
- 对比说明：Section V-B3 里攻击者使用的 "Known-Benign" 良性模板是**攻击方**的资源，不是 FreqFed 需要的。

## 8. 计算与存储开销

- 论文报告的开销：论文没有给出 FreqFed 自身的运行时、FLOPs、内存或通信开销数值。与开销相关的只有实验平台配置（Section V-A："4 NVIDIA RTX 8000 (each with 48GB memory), an AMD EPYC 7742, and 1024 GB of main memory"）以及定性表述（Abstract/Conclusion 说 FreqFed 在保持效用上只有 "negligible impact"，Section VI-A 说 Auror "incurs significant computational overhead"）。摘要与结论声称评测了 "efficiency"，但正文未给出相应量化结果。
- 主要开销来自哪一步（分析）：每轮 K 次二维 DCT（步骤 3）与一次 K×K 余弦距离矩阵（步骤 5）加一次 HDBSCAN 聚类（步骤 6）。
- 增长量级（分析）：按 Eq. (2) 的双重求和朴素实现，一次 N×M 的二维 DCT 需要 O(N²M²) 次乘加（每个输出系数一次 M×N 求和）；使用快速 DCT 算法可降到 O(NM log(NM))。筛选是 O(NM)。余弦距离矩阵需要 O(K²·|F|) 次运算，其中 |F| ≈ (⌊|V|/2⌋+1)(⌊|V|/2⌋+2)/2。HDBSCAN 在预计算距离矩阵上的开销随 K 增长，论文未给复杂度。
- 存储（分析）：服务器需保存 K 个完整本地模型、K 个 DCT 系数矩阵、K 个低频向量 F_i 与一个 K×K 距离矩阵，随 K 与模型参数量线性增长。
- 通信（分析）：与 FedAvg 相同（上行 K 个模型、下行 1 个全局模型），没有额外往返，也没有额外的元数据上传。

## 9. 实现时容易错的地方

论文明确强调或体现的实现细节：

1. 适用条件必须成立：只有当 k_A < K/2 时方法才有效；若 PMR ≥ 50%，恶意模型簇可能成为最大簇而被误判为良性（Section III、Section V-B1）。工程上需要监控被接受客户端数 L 是否仍占多数。
2. 聚类必须等本轮所有客户端更新到齐（Section IV-C），因此该运行时要求同步轮次；不能对先到的部分更新提前聚类。
3. 距离矩阵是对称的，且对角线为 0：distances_matrix[j][i] = distances_matrix[i][j]（Algorithm 1 lines 23–24）。
4. 被接受集合是"最大簇"，不是"距离全局模型最近的若干客户端"；论文反复强调 FreqFed 不做基于权重范数/余弦距离的阈值判定（Section IV-A）。
5. 聚类用的是低频分量向量的余弦距离，而不是原始权重的距离（Algorithm 1 line 23 的输入是 F_i 而非 W_i）。
6. 低频筛选的循环边界与条件要同时满足：i, j ∈ [0,⌊|V|/2⌋] **且** i + j ≤ ⌊|V|/2⌋（Algorithm 1 lines 15–17）。
7. 论文把本地模型参数 W_i^t 称为 "model update"（Section II-A、IV-C），Algorithm 1 line 4 是 DCT(W_i^t)，即对客户端训练后的模型参数做变换。

论文没说清、实现时必须自己决定的地方：

1. 如何把多层、非方阵的权重张量组织成一个"方阵 V"：整模型一次 DCT 还是逐层 DCT 再拼接？填充还是截断？（Section IV-C 只提方阵，Appendix -A 只给模型结构。）
2. |V| 的含义与数值：是方阵边长还是元素总数？Algorithm 1 lines 15–17 的 ⌊|V|/2⌋ 直接决定保留多少系数。
3. Eq. (2) 的归一化系数 c1、c2 按原文实现时（k=0 或 l=0 时为 sqrt(2/(MN))，否则为 1）会改变 DC 项与轴向项在 F 中的相对权重，从而影响余弦距离；论文没有讨论这一点，需要自行确认是否采用标准的正交归一化。
4. HDBSCAN 的全部参数（min_cluster_size、min_samples、cluster_selection_method 等）论文未说明。
5. HDBSCAN 的噪声标签（通常为 −1）如何处理：噪声点算不算一个"簇"、能否被 argmax 选中、是否从分母里排除，论文未说明。
6. 当没有任何簇形成、最大簇为空（L = 0）、或所有点都被判为噪声时的回退动作，论文未说明。
7. 当两个簇成员数相同时 argmax 如何打破平局，论文未说明。
8. F 向量在算余弦相似度前是否需要归一化、中心化或做数值截断；F 全为零向量时余弦相似度的除零问题，论文未说明。
9. 聚合到底是按 L 均分的简单平均（Algorithm 1 line 7）还是 Eq. (1) 的按样本数加权 FedAvg（Section IV-B 的说法）：两者不一致，必须自行选择并记录。
10. 论文没有给出 K、T、B、E_i、η_i 以及损失函数 ℓ 的具体取值，复现时需要自行设定。
11. HDBSCAN 是否以预计算距离矩阵方式调用（metric 为 precomputed）、是否做 mutual reachability 变换，论文只写了 HDBScan(distances matrix)。
12. 客户端模型是否必须同构、部分客户端掉线时 K 如何取值，论文未讨论。

## 10. 原文依据

1. 支撑步骤 1（客户端本地训练）："In local training, each client i trains its model based on its local data, using the initial random global model as a starting point."（Section IV-C）
2. 支撑步骤 3（二维 DCT）："The model update is then transformed into a matrix of coefficients, Vi, using the Discrete Cosine Transform (DCT) with the DCT procedure."（Section IV-C）
3. 支撑步骤 4（低频筛选）："After computing the DCT representation of the model weights, the low-frequency components are extracted as they are considered the most crucial frequency coefficients."（Section IV-C）
4. 支撑步骤 5–6 的触发时机与输入： "Once all clients have submitted their model updates, the Clustering procedure is invoked with the low-frequency components extracted from all the clients’ model updates, F1, . . . , Fk, as input."（Section IV-C）
5. 支撑步骤 5（余弦距离）："Then, it computes the cosine distance between every pair of low-frequency component vectors as 1 minus the Cosine Similarity of Fi and Fj."（Section IV-C）
6. 支撑步骤 6（HDBSCAN）："Next, the Clustering procedure utilizes the HDBSCAN algorithm to cluster the model updates based on the cosine distances stored in the matrix distances matrix."（Section IV-C）
7. 支撑步骤 7（取最大簇）："Finally, the Clustering procedure identifies the cluster with most model updates (see line 26) and returns a list of the model updates’ indices."（Section IV-C）
8. 支撑步骤 8（聚合）："The global model is then updated by aggregating the accepted models, Wbl, for l in the range [1, L], and dividing by the number of accepted models, L."（Section IV-C）

```json
{
  "key": "fereidooni2024freqfed",
  "method": "FreqFed：服务器端对每个客户端上传的本地模型权重做二维 DCT，取低频三角区域的系数组成向量，按 1 减余弦相似度构造 K×K 距离矩阵做 HDBSCAN 聚类，只聚合最大簇内的客户端本地模型并按 L 均分，其余客户端剔除",
  "stages": ["server_receive", "server_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "客户端本地训练（标准 FL，FreqFed 不修改）",
      "operator": "local_sgd_update",
      "input": "上一轮全局模型 G^t（首轮为随机初始化 G^1）与客户端 i 的本地数据 d_i",
      "output": "客户端 i 的本地模型 W_i^t（论文称 model update）",
      "params": {"batch_size": "B（论文未给取值，Algorithm 1 line 9）", "local_epochs": "E_i（论文未给取值，Algorithm 1 line 10）", "learning_rate": "η_i（论文未给取值，Algorithm 1 line 12）", "loss": "论文未说明"},
      "source": "Algorithm 1 lines 8–12；Section IV-C"
    },
    {
      "step": "把多层权重张量整理成一个方阵（论文未说明具体做法）",
      "operator": "weights_to_square_matrix",
      "input": "W_i^t 的全部参数张量（多层、非方阵）",
      "output": "N×M 的实数矩阵（论文语境下为方阵 V 的输入）",
      "params": {"layout": "论文未说明"},
      "source": "Section IV-C；Algorithm 1 lines 13–18"
    },
    {
      "step": "二维离散余弦变换",
      "operator": "dct_2d",
      "input": "N×M 的权重矩阵 x",
      "output": "N×M 的 DCT 系数矩阵 V_i^t",
      "params": {"kernel": "cos(kπ/(2M)(2m+1))cos(lπ/(2N)(2n+1))", "c1": "k=0 时 sqrt(2/(MN))，k=1..M-1 时 1", "c2": "l=0 时 sqrt(2/(MN))，l=1..N-1 时 1"},
      "source": "Eq. (2)；Section II-C；Algorithm 1 line 4"
    },
    {
      "step": "低频三角筛选 Filtering",
      "operator": "low_frequency_triangle_filter",
      "input": "系数矩阵 V_i^t（方阵，边长记作 |V|）",
      "output": "低频系数向量 F_i^t",
      "params": {"loop_bounds": "i, j ∈ [0, ⌊|V|/2⌋]", "keep_condition": "i + j <= ⌊|V|/2⌋", "value_of_|V|": "论文未说明"},
      "source": "Algorithm 1 lines 13–18；Section IV-C"
    },
    {
      "step": "两两余弦距离矩阵",
      "operator": "cosine_distance_matrix",
      "input": "K 个低频向量 F_1..F_K",
      "output": "K×K 对称距离矩阵（对角为 0）",
      "params": {"distance": "1 - CosineSim(F_i, F_j)", "symmetry": "distances_matrix[j][i] = distances_matrix[i][j]"},
      "source": "Algorithm 1 lines 19–24；Section IV-C"
    },
    {
      "step": "HDBSCAN 密度聚类",
      "operator": "hdbscan_precomputed",
      "input": "K×K 余弦距离矩阵",
      "output": "每个客户端一个簇 ID（cluster_ids）",
      "params": {"min_cluster_size": "论文未说明", "min_samples": "论文未说明", "cluster_selection_method": "论文未说明", "metric": "论文未说明（传入的是距离矩阵）"},
      "source": "Algorithm 1 line 25；Section II-D；Section IV-B"
    },
    {
      "step": "取成员数最大的簇作为接受集合",
      "operator": "largest_cluster_select",
      "input": "cluster_ids",
      "output": "被接受的客户端索引 B = (b_1..b_L)",
      "params": {"rule": "argmax_a |{a ∈ cluster ids}|", "noise_label_handling": "论文未说明", "tie_break": "论文未说明", "empty_cluster_fallback": "论文未说明"},
      "source": "Algorithm 1 lines 26–30；Section IV-C"
    },
    {
      "step": "对被接受模型取平均（聚合）",
      "operator": "mean_selected_models",
      "input": "被接受客户端的本地模型 W_{b_1}^t..W_{b_L}^t",
      "output": "下一轮全局模型 G^(t+1)",
      "params": {"weighting": "Σ_{l=1}^{L} W_{b_l}^t / L（按 L 均分；Section IV-B 称之为 FedAvg，但未使用 Eq. (1) 的 n_i/n 权重）", "clip": "无", "noise": "无"},
      "source": "Algorithm 1 line 7；Section IV-B；Section IV-C"
    }
  ],
  "sampling": [
    {"what": "clients", "how": "每轮遍历全部 K 个客户端，不做抽样", "size": "K（论文未给出取值；Algorithm 1 line 2）"},
    {"what": "coordinates", "how": "DCT 后只保留系数矩阵左上角满足 i + j <= ⌊|V|/2⌋ 且 i, j ∈ [0,⌊|V|/2⌋] 的低频三角区域", "size": "(⌊|V|/2⌋+1)(⌊|V|/2⌋+2)/2 个系数，约为整矩阵的 1/8（分析）；|V| 的数值论文未说明"},
    {"what": "layers", "how": "论文未使用逐层抽样，也未说明 V 与网络层的对应关系", "size": "论文未说明"},
    {"what": "rounds", "how": "不抽样，按 T 轮依次执行", "size": "T（论文未给出取值；Algorithm 1 line 1）"},
    {"what": "probes", "how": "不使用参考数据或探针样本", "size": "0"}
  ],
  "resources": [
    "无需任何外部资源：不需要干净参考数据、根数据集、预训练检测器、额外模型或对齐前后的权重",
    "服务器只需要本轮 K 个客户端上传的本地模型更新 W_i^t（Algorithm 1 lines 2–5）",
    "存储规模随 K 与模型参数量线性增长；论文 Table I 给出的模型规模从约 66k（EMNIST/LeNet）到约 20M（Reddit/LSTM）参数"
  ],
  "actions": ["exclude_client"],
  "dominant_cost": "每轮 K 次二维 DCT（朴素实现 O(N^2M^2)，快速 DCT 为 O(NM log(NM))）加一次 O(K^2·|F|) 的余弦距离矩阵与一次 HDBSCAN 聚类；论文未报告运行时/FLOPs/内存数值，只给出实验硬件配置（Section V-A）",
  "underspecified": [
    "如何把多层、非方阵的权重张量整理成论文所说的方阵 V（整模型一次 DCT 还是逐层 DCT 再拼接、如何填充或截断）",
    "|V| 究竟指方阵边长还是元素总数，以及它决定保留的低频系数个数",
    "Eq. (2) 中 c1、c2 的归一化按原文实现会改变 DC 项与轴向项的相对权重，从而影响余弦距离",
    "HDBSCAN 的全部参数（min_cluster_size、min_samples、cluster_selection_method 等）",
    "HDBSCAN 噪声标签（通常为 -1）是否参与 argmax、能否成为最大簇",
    "最大簇为空（L=0）、无簇形成或全部被判为噪声时的回退动作",
    "两个簇成员数相同时如何打破平局",
    "F 向量在算余弦相似度前是否需要归一化/中心化，以及全零向量的除零处理",
    "聚合是按 L 均分的简单平均（Algorithm 1 line 7）还是 Eq. (1) 的按样本数加权 FedAvg（Section IV-B 的表述），两者不一致",
    "K、T、B、E_i、η_i 以及本地损失函数 ℓ 的具体取值",
    "HDBSCAN 是否以预计算距离矩阵（metric=precomputed）方式调用、是否做 mutual reachability 变换",
    "客户端模型是否必须同构、客户端掉线时 K 与聚类如何处理"
  ],
  "quotes": [
    {"supports": "步骤 1：客户端本地训练", "text": "In local training, each client i trains its model based on its local data, using the initial random global model as a starting point."},
    {"supports": "步骤 3：对本地模型权重做二维 DCT", "text": "The model update is then transformed into a matrix of coefficients, Vi, using the Discrete Cosine Transform (DCT) with the DCT procedure."},
    {"supports": "步骤 4：提取低频分量", "text": "After computing the DCT representation of the model weights, the low-frequency components are extracted as they are considered the most crucial frequency coefficients."},
    {"supports": "步骤 5–6：等全部客户端到齐后以低频向量为输入做聚类", "text": "Once all clients have submitted their model updates, the Clustering procedure is invoked with the low-frequency components extracted from all the clients’ model updates, F1, . . . , Fk, as input."},
    {"supports": "步骤 5：余弦距离定义", "text": "Then, it computes the cosine distance between every pair of low-frequency component vectors as 1 minus the Cosine Similarity of Fi and Fj."},
    {"supports": "步骤 6：HDBSCAN 聚类", "text": "Next, the Clustering procedure utilizes the HDBSCAN algorithm to cluster the model updates based on the cosine distances stored in the matrix distances matrix."},
    {"supports": "步骤 7：取最大簇得到接受索引", "text": "Finally, the Clustering procedure identifies the cluster with most model updates (see line 26) and returns a list of the model updates’ indices."},
    {"supports": "步骤 8：对被接受模型做按 L 均分的聚合", "text": "The global model is then updated by aggregating the accepted models, Wbl, for l in the range [1, L], and dividing by the number of accepted models, L."}
  ]
}
```
