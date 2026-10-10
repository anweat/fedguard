# nguyen2022flame：FLAME（动态聚类过滤 + 自适应裁剪 + 自适应高斯加噪）

## 1. 方法一句话

FLAME 的输入是第 t 轮中 n 个客户端上传的本地模型更新 `W_1..W_n`（每个都按固定顺序展平成 p 维权重向量）以及上一轮服务器下发过的加噪全局模型 `G*_{t-1}`；输出是服务器聚合出的新全局模型 `G*_t`（先过滤、再裁剪、再加噪），同时隐含输出一份"被剔除模型"的索引集合。它不做二分类意义上的打分判定，判定体现为 HDBSCAN 的离群点标记：只有落在唯一多数簇里的模型被接纳进入聚合，其余模型（论文期望其中包含高攻击影响的投毒模型 `W'_1`）直接不进聚合；对留下的模型再按范数中位数裁剪（`W'_2` 型），最后对整个聚合模型加高斯噪声（`W'_3` 型残余后门）。出处：§4.1、§4.3、Algorithm 1。

## 2. 运行位置

FLAME 的全部防御计算都在**服务器端、收到本轮所有更新之后**完成，客户端训练过程本身不被修改。

- **服务器下发前（server_distribute）**：服务器把上一轮**已经加噪**的全局模型 `G*_{t-1}` 下发给客户端（Alg. 1 第 5 行的注释："The aggregator sends G*_{t-1} to Client i"）。这一阶段 FLAME 本身不做额外计算，只是保证下发的是加噪后的模型。
- **客户端训练前 / 每个训练步 / 上传前（client_pre_train / client_pre_step / client_post_train）**：FLAME 不插入任何操作，客户端按原有本地流程训练并上传（Alg. 1 第 5 行）。
- **服务器收到更新（server_receive）**：计算两两余弦距离、跑 HDBSCAN 聚类、计算各更新到 `G*_{t-1}` 的欧氏距离、取中位数得到裁剪边界 `S_t`（Alg. 1 第 6–9 行）。
- **服务器聚合（server_aggregate）**：对被接纳的 L 个模型按 `S_t` 等比裁剪，再做等权平均（Alg. 1 第 10–12 行）。
- **聚合之后（server_post_aggregate）**：按 `σ = λ·S_t` 给聚合结果加高斯噪声，得到 `G*_t`（Alg. 1 第 13–14 行）。
- **额外往返**：不需要。检测所需的全部信息（两两距离、到全局模型的距离）都来自本轮已上传的更新，服务器不向客户端索取任何额外信息，也不做挑战—应答。因此 `needs_round_trip = false`。
- **隐私扩展（§8）**：论文另给出 private FLAME，客户端在上传前把本地更新 `W_i` 拆成两份算术分享 `⟨X⟩^A_i`、`⟨X⟩^B_i` 分别发给聚合方 A 和外部服务器 B，由 A、B 用 STPC（安全两方计算）联合完成距离计算、聚类、裁剪与聚合。这属于隐私保护扩展，改变了上传前与服务器侧的运行方式（多一个非共谋服务器），但不是后门防御本身所必需。

## 3. 算子流水线

**步骤 1：参数展平与序列化**
- 输入：客户端 i 的本地模型 `W_i`，含全部权重与偏置共 p 个参数（论文把权重和偏置统称为 "weights"，见 §2 脚注 1）。
- 计算：把所有 weight/bias 矩阵按**对所有模型相同的预定顺序**展平/序列化成一个向量。论文未规定具体顺序，只要求"identically for all models"（§3）。
- 输出：p 维向量 `W_i ∈ R^p`；n 个客户端合起来是 n×p 的矩阵。
- 出处：§3（"we represent Neural Networks (NNs) using their weight vectors..."）。

**步骤 2：两两余弦距离矩阵**
- 输入：n 个 p 维更新向量 `W_1..W_n`。
- 计算：公式 (2)，`c_ij = 1 − (W_i·W_j)/(‖W_i‖·‖W_j‖) = 1 − (Σ_k w_i^k w_j^k) / (sqrt(Σ_k (w_i^k)^2) · sqrt(Σ_k (w_j^k)^2))`，即 1 减去两向量夹角余弦，取值越小越同向。
- 输出：n×n 的余弦距离矩阵 `(c_ij)`（对角元为 0）。
- 出处：公式 (2)（§3）；Alg. 1 第 6 行 `(c11,...,cnn) ← COSINEDISTANCE(W1,...,Wn)`。

**步骤 3：HDBSCAN 动态聚类，取唯一多数簇**
- 输入：n×n 余弦距离矩阵 `(c_ij)`。
- 计算：把每个模型当作一个数据点，用 HDBSCAN 基于密度聚类，**不预设簇数**。按 §E 的描述，HDBSCAN 先用给定距离构建最小生成树（MST），从权重最小的边开始逐条合并、构造二叉树；收集所有覆盖至少 `N/2+1` 个数据点的候选节点，用边权重与覆盖点数计算 stability value，取密度最同质的候选作为"多数簇"，簇内点赋该簇标签，簇外全部标为 noise/outlier。FLAME 的参数取 `min_cluster_size = N/2+1`、`min_samples = 1`（§E）。
- 输出：被接纳模型的索引 `(b_1,...,b_L)`（L 为接纳模型数，即多数簇大小），其余 n−L 个模型为离群点、不参与后续聚合。
- 出处：§4.3.1、§E；Alg. 1 第 7 行 `(b1,...,bL) ← CLUSTERING(c11,...,cnn)`。

**步骤 4：各更新到上一轮全局模型的欧氏距离**
- 输入：`G*_{t-1}`（p 维）与 `W_1..W_n`（n×p）。
- 计算：公式 (3)，`e_i = ‖W_i − G*_{t-1}‖ = sqrt(Σ_k (w_i^k − g^k)^2)`。
- 输出：n 维非负标量向量 `(e_1,...,e_n)`。
- 出处：公式 (3)（§3）；Alg. 1 第 8 行。

**步骤 5：取中位数得到自适应裁剪边界 `S_t`**
- 输入：`(e_1,...,e_n)`，**包含被聚类剔除的模型**（§4.3.2 明确说明）。
- 计算：`S_t = MEDIAN(e_1,...,e_n)`，每轮重新计算，因此是"自适应"边界。
- 输出：标量 `S_t`。
- 出处：Alg. 1 第 9 行；§4.3.2。

**步骤 6：按边界等比裁剪被接纳的模型**
- 输入：被接纳的更新 `W_{b_1}..W_{b_L}`、其对应距离 `e_{b_l}`、裁剪边界 `S_t`，以及基准模型（论文写作 `G_{t-1}`，见第 9 节的歧义条目）。
- 计算：对第 l 个被接纳模型，`γ = S_t / e_{b_l}`；`W^c_{b_l} = G_{t-1} + (W_{b_l} − G_{t-1}) · MIN(1, γ)`，其中乘法**逐坐标**进行。等价于：范数不超过边界的模型保持不变（γ ≥ 1 时乘子为 1），超过边界的模型以基准点为原点等比缩放到范数等于 `S_t`。只处理被接纳的 L 个模型。
- 输出：裁剪后的 `W^c_{b_1}..W^c_{b_L}`（L×p）。
- 出处：Alg. 1 第 10–11 行；§4.3.2。

**步骤 7：等权平均聚合**
- 输入：L 个裁剪后的更新。
- 计算：`G_t = Σ_{l=1}^{L} W^c_{b_l} / L`，即对**被接纳模型**做等权平均，不使用客户端上报的数据集大小（论文在 §2.1 把 FedAvg 的 `s_i = ‖D_i‖` 加权改为 `s_i = 1/n`，并在 §4.3.2 说明按数据量加权不安全）。
- 输出：未加噪的全局模型 `G_t`（p 维）。
- 出处：Alg. 1 第 12 行；§2.1、§4.3.2。

**步骤 8：自适应高斯加噪**
- 输入：`G_t`、`S_t`、DP 参数 `(ε, δ)`。
- 计算：先算噪声水平因子 `λ = (1/ε)·sqrt(2·ln(1.25/δ))`（Alg. 1 第 13 行；由 Theorem 1 与公式 (7) 给出），再取 `σ = λ·S_t`，最后 `G*_t = G_t + N(0, σ²)`，即给全局模型的每个参数坐标加零均值高斯噪声（按公式 (5) 的推导，噪声是逐模型/逐坐标独立采样后求和）。
- 输出：加噪全局模型 `G*_t`（p 维），作为下一轮下发给客户端的模型。
- 出处：Alg. 1 第 13–14 行；公式 (6)(7)；§5.1、§B.3。

## 4. 采样与规模控制

- **客户端**：论文未做随机抽样意义上的规模控制；防御本身要求本轮参与的全部 n 个客户端都参与距离计算与聚类。唯一涉及规模的是**过滤/截断**：HDBSCAN 只保留一个多数簇，簇外模型整体剔除。簇的最小规模被固定为 `n/2+1`（§4.3.1、§E）。实验中的 n 取值：§5.1 表 1 的 NIDS 实验 n=100、其中 k=40 为攻击者；§7.2 的注入策略实验 n=100、k=40；§7.2 的 model alignment 实验 n=200、k=80；§7.3 的动态客户端实验中总客户端 100（25 个恶意），每轮随机选 60–90 个参与，PMR 因此逐轮变化。
- **层**：论文未对层做抽样或截断；所有层（含偏置）一起展平后参与距离、裁剪与加噪。
- **参数坐标**：论文未对坐标做抽样或降维，使用的是完整 p 维向量；裁剪是按坐标统一乘同一个因子（等价于整体缩放），不是逐坐标独立裁剪。表 2 给出的模型规模为：Reddit/LSTM ~20M、IoT-Traffic/GRU ~507k、CIFAR-10/ResNet-18 Light ~2.7M、MNIST/CNN ~431k、Tiny-ImageNet/ResNet-18 ~11M 参数。
- **轮次**：论文未做跨轮抽样或累积。论文明确 FLAME 是 round-independent 的：不使用"哪一轮剔除了哪些客户端"这类历史信息，`S_t` 与 `σ` 每轮独立重算（§7.3、§4.3.2）。
- **参考数据 / 探针**：论文未使用。§4.1 与 §5.1(S2) 都强调聚合方在联邦场景下拿不到训练数据，也无法据此估计 sensitivity。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| n | 每轮参与客户端数（也是聚类规模基准 N） | Alg. 1 的输入；实验取 100（§5.1 表 1、§7.2）、200（§7.2 alignment）、每轮 60–90/总 100（§7.3） | Alg. 1 第 1、3–4 行；§5.1、§7.2、§7.3 |
| T | 训练迭代轮数 | 论文未给出具体数值 | Alg. 1 第 1、3 行 |
| min_cluster_size | HDBSCAN 最小簇规模 | `n/2 + 1`（至少 50% 客户端） | §4.3.1；§E 写作 `min_cluster_size = N/2+1` |
| min_samples | HDBSCAN 的 min_samples | 1 | §E（正文未提，只在 §E 给出） |
| 距离度量 1 | 聚类用距离 | 余弦距离 `c_ij`，公式 (2) | §3 公式 (2)；§4.3.1 |
| 距离度量 2 | 裁剪边界用距离 | 到 `G*_{t-1}` 的欧氏距离 `e_i`，公式 (3) | §3 公式 (3)；Alg. 1 第 8 行 |
| S_t | 每轮裁剪边界 | 无固定值，= 全部 n 个 `e_i` 的中位数 | Alg. 1 第 9 行；§4.3.2 |
| ε | DP 隐私预算 | IC 3705；NIDS 395；NLP 4191 | §B.3（图 12 说明段） |
| δ | DP 失败概率 | 论文未给出数值（只写 `(ε,δ)`-DP 与 `λ = (1/ε)·sqrt(2 ln 1.25/δ)`） | §B.3；Alg. 1 第 13 行 |
| λ | 噪声水平因子 | IC 0.001；NLP 0.001；NIDS 0.01 | §B.3 |
| σ | 每轮高斯噪声标准差 | `σ = λ·S_t`，随轮次变化 | Alg. 1 第 13 行；公式 (7) |
| 客户端权重 | 聚合时各客户端贡献权重 | 等权 `1/L`（不使用数据集大小） | §2.1、§4.3.2、Alg. 1 第 12 行 |
| γ | 单模型裁剪缩放因子 | `S_t / e_{b_l}`，实际乘子为 `MIN(1, γ)` | Alg. 1 第 11 行；§4.3.2 |

（实验里还使用与防御无关的攻击参数：PMR = k/n、PDR；§2.2、§7.3。表 1 的对照实验还直接扫了 σ = 0.01/0.08/0.10。）

## 6. 判定与动作

- **判定规则（聚类）**：不做阈值判定，而是"多数簇 = 良性"。HDBSCAN 在余弦距离空间上动态确定簇数，只有那一个覆盖至少 `n/2+1` 个点的多数簇被接纳；所有不在该簇中的模型都被标为离群点。论文的出发点是：固定簇数的聚类（如 Auror 用的 K-means 取 2 簇）会被"多个后门同时注入"绕过，所以 FLAME 让每个投毒模型各自成为离群点（§4.3.1、图 5）。
- **动作 1 — 剔除客户端（exclude_client）**：离群点对应的模型完全不入聚合，等价于权重置 0；被接纳模型的权重为 `1/L`（Alg. 1 第 12 行）。注意 L 是**接纳后的数量**，不是 n。
- **动作 2 — 裁剪（clip）**：对每个被接纳模型，`γ = S_t / e_{b_l}`，按 `W^c = G + (W − G)·MIN(1, γ)` 逐坐标缩放；范数未超边界的模型不受影响（乘子被 `MIN(1, ·)` 截到 1）。裁剪边界 `S_t` 取全部 n 个欧氏距离的中位数（含被剔除者），论文论证这样 `S_t` 一定落在良性模型的范数范围内，且该值不被攻击者控制（§4.3.2）。
- **动作 3 — 加噪（add_noise）**：对聚合后的全局模型（不是对单个本地模型）加 `N(0, σ²)`，`σ = λ·S_t`，`λ = (1/ε)·sqrt(2 ln(1.25/δ))`。§5.1 用公式 (5)(6) 论证"对每个本地模型加 DP 噪声"与"对全局模型加一个等效聚合噪声"等价，并据此把 `1/n² Σ ∆_i²` 近似为 `S_t²`，得到公式 (7) 的 `σ_G ≈ (S_t/ε)·sqrt(2 ln(1.25/δ))`。
- **是否跨轮累积**：不累积。论文明确 FLAME 是 round-independent，不使用历史轮次信息；`S_t` 与 `σ` 每轮从本轮更新重新计算（§4.3.2、§7.3）。噪声也不跨轮保留，每轮对新的 `G_t` 重新采样。
- **有效性边界（判定成立的前提）**：必须 PMR = k/n < 50%。实验显示 PMR < 50% 时 TNR = 100%、BA = 0%；PMR = 50% 时全部模型被接纳（TPR = 0%、TNR = 100%）；PMR > 50% 时防御失败（§7.3、图 7）。
- **性能影响**：表 3 显示 FLAME 在多个数据集上把 BA 降到 0–4%，同时 MA 下降小于 0.4%。

## 7. 需要的外部资源

- **干净参考数据 / 根数据集 / 探针数据：不需要**。§4.1 与 §5.1(S2) 明确说明聚合方没有训练数据，FLAME 的设计目标之一就是不做经验性的噪声标定。这一点与需要 root dataset 的 FLTrust、需要客户端自查的 BaFFle 形成对比（§9）。
- **预训练检测器：不需要**。聚类是每轮在模型空间上现场做的，没有训练出来的判别器。
- **模型对齐前后的权重：不需要**。
- **额外模型：不需要**（只需要 p 维模型本身；评估用的模型规模见表 2）。
- **必须有的组件**：一个 HDBSCAN 实现（§4.3.1 引用 Campello et al. [13]；§E 引用 McInnes et al. 的实现细节），并且要能接受预计算的距离矩阵（FLAME 传入的是余弦距离矩阵，min_cluster_size = n/2+1、min_samples = 1）。
- **private FLAME 的额外资源（§8、§G）**：一个与聚合方不共谋的外部服务器 B；ABY 安全两方计算框架；Bozdemir et al. 的开源隐私保护 DBSCAN 实现（用 DBSCAN + 邻域参数 ε 的二分搜索来近似 HDBSCAN）；两台服务器（实验环境为 Intel Core i9-7960X 2.8 GHz、128 GB RAM、10 Gbit/s LAN、0.2 ms RTT）。
- **配置项**：需要事先确定 `(ε, δ)` 才能算 λ；论文给了 ε 的具体值和 λ，但没给 δ 的数值（§B.3），也没有给出按数据集确定 DP 预算的可复现流程（只说"基于客户端数据集大小的中位数和模型大小"来确定）。

## 8. 计算与存储开销

**论文报告的开销：**
- §D：作者在 IoT 数据集的 6 种设备类型上、仅良性客户端参与时测得，FLAME 最多多花 4 个额外训练轮；平均需要 1.67 个额外训练轮才能达到"无防御时 MA 的 99%"，即 FLAME 不妨碍模型收敛。
- §G：private FLAME 相对非私有 FLAME 的运行时开销最高可达**三个数量级**；即便取最大模型（Reddit）与 K = 100 客户端，STPC 下单轮服务器侧总运行时间为 22 081.65 秒（约 6 小时）。
- §8：用 DBSCAN 近似 HDBSCAN 的原因是"HDBSCAN 中最小生成树的构建用 STPC 实现非常昂贵"。
- §C：把 K-means 聚类 + 固定裁剪界 1.0 + 固定噪声标准差 0.01 朴素堆叠，在 CIFAR-10 上只能做到 BA 51.9%、MA 60.24%，而 FLAME 是 BA 0.0%、MA 89.87%——说明三个组件必须按论文的动态方式组合。

**分析（未在论文中直接报告的部分）：**
- 主开销在第 2–3 步：n 个 p 维模型的两两余弦距离需要 O(n²·p) 次乘加与 O(n²) 的标量存储，HDBSCAN 建 MST 与建二叉树与点数同阶以上（§E 描述的流程至少要遍历所有点对距离）；这两步都随**客户端数 n 的平方**和**模型参数量 p**增长。
- 裁剪与加噪是线性开销：裁剪约 O(L·p)（L ≤ n），加噪 O(p)。
- 通信开销：每轮 n 个 p 维模型上传、1 个 p 维模型下发，与 n·p 成正比。
- 私有版本还要为距离、聚类、裁剪、聚合各自付出 STPC 协议开销（§G 专门测量了 cosine distance、Euclidean distance + clipping + aggregation、clustering 三部分的秒级耗时）。

## 9. 实现时容易错的地方

**论文明确强调、不能弄错的点：**
1. `min_cluster_size` 必须设为 `n/2+1`（至少 50% 客户端），目的是让多数簇必然包含多数（假定良性）的更新；设小了会把大量良性模型当成离群点剔掉（§4.3.1、§E）。
2. 聚类必须用**余弦距离**：余弦距离不受攻击者放大权重幅度的影响，所以缩放到多大的 `W'_2` 型模型都不会因为这个缩放而改变角度、进而改变聚类结果（§4.3.1）。
3. 裁剪边界 `S_t` 必须用**全部 n 个**模型（含被聚类剔除者）的欧氏距离中位数计算；但算完边界后，后续裁剪与聚合**只用被接纳的 L 个**模型（§4.3.2）。
4. 聚合必须**等权**，不能按客户端上报的数据集大小加权——上报的数据量不可信，攻击者可以谎报大数据集来放大影响力（§2.1、§4.3.2）。
5. 裁剪乘子是 `MIN(1, γ)`，逐坐标相乘；γ ≥ 1 的模型必须原样保留，不能被放大（Alg. 1 第 11 行）。
6. 噪声加在**聚合后的全局模型**上，不是加在每个本地模型上；§5.1 的公式 (5)(6) 只是用来论证两者等价并推出噪声界（Alg. 1 第 13–14 行、§5.1）。
7. λ 与 `S_t` 都由论文给定，不要按经验另调；`σ = λ·S_t`，随轮次自适应（Alg. 1 第 13 行）。
8. 防御有硬前提：良性客户端必须严格过半（PMR < 50%）；PMR = 50% 时论文报告全部模型被接纳、防御失效（§7.3）。
9. 论文明确防御目标是"剔除高攻击影响的模型"而不是"剔除全部投毒模型"：TPR 低并不等于失败，残余后门由加噪消除（§4.1、§5.2、§B.1，表 5 中 TPR 仅 5.68% 但 BA 仍为 0%）。
10. FLAME 不使用跨轮状态（round-independent），不要实现成"记住上轮被剔除的客户端"（§7.3）。

**论文没说清、实现时必须自己决定的点：**
1. Alg. 1 第 11 行的基准模型写作 `G_{t-1}`，而同一条流水线第 5 行客户端训练用的是**加噪后**的 `G*_{t-1}`；裁剪究竟相对哪一个模型做，论文未说明（正文 §4.3.2 也沿用 `G_{t-1}` 的写法）。
2. `δ` 的具体数值未给出；λ 与 ε 已知，但由 `λ = (1/ε)·sqrt(2 ln(1.25/δ))` 反推 δ 的做法论文没有交代，且 §B.3 只说 DP 预算"依据客户端数据集大小中位数与模型大小"确定，流程不可复现。
3. 余弦距离在某个更新为零向量（`‖W_i‖ = 0`）时的定义未说明。
4. 中位数的具体定义未说明：n 为偶数时取中间两值的平均还是取下中位数，论文只写 `MEDIAN`。
5. 聚类结果异常时如何处理未说明：若 HDBSCAN 因数值原因把全部点标为 noise，或多数簇为空、L = 0，则聚合与等权平均都无定义，论文没有给出兜底（只给出了 `min_cluster_size = n/2+1` 这一结构约束）。
6. `n` 在算法里到底是"本轮实际参与数"还是"客户端总池大小"未说明；§7.3 的实验里每轮参与数在 60–90 之间浮动，但未说明聚类参数是跟着当轮参与数走还是跟着总池走。
7. 高斯噪声是否对每个参数坐标独立采样、是否对权重与偏置一视同仁、是否跳过 BatchNorm 等非权重参数，论文没有逐字说明（Alg. 1 只写 `G*_t = G_t + N(0,σ²)`，公式 (5) 的推导按逐模型独立噪声向量处理）。
8. 每轮是否重新独立采样噪声、随机种子如何管理，论文未说明（只隐含每轮重新算 σ）。
9. HDBSCAN 的具体实现参数除 `min_cluster_size`、`min_samples` 外的其余默认值未给出；private FLAME 里用 DBSCAN 近似时，邻域参数 ε 的二分搜索范围与停止条件也未在正文给出。
10. 本地训练的超参数（本地 epoch 数、学习率、批大小）未给出，而论文自己在 §4.3.2 指出 L2 范数依赖训练轮数、数据集类型与后门类型，因此这些未给出的超参会间接影响 `S_t` 与 `σ`。
11. T（训练总轮数）未给出具体取值。
12. 表 1 用的是直接给定的 σ（0.01/0.08/0.10），与 Alg. 1 的 `σ = λ·S_t` 是两套口径；复现表 1 时需要区分这两者。

## 10. 原文依据

1. **支撑步骤 1（展平序列化）**："we represent Neural Networks (NNs) using their weight vectors, in which the extraction of weights is done identically for all models by flattening/serializing the weight/bias matrices in a predetermined order"（§3）
2. **支撑步骤 2–3（余弦距离 + HDBSCAN）**："FLAME uses pairwise cosine distances to measure the angular differences between all model updates and applies the HDBSCAN clustering algorithm [13]."（§4.3.1）
3. **支撑步骤 3（多数簇规模约束）**："we set the minimum cluster size to be at least 50% of the clients, i.e., n/2 + 1, so that the resulting cluster will contain the majority of updates"（§4.3.1）
4. **支撑步骤 3（离群点即剔除）**："In particular, HDBSCAN labels models as outliers if they do not fit into any cluster. This allows FLAME to effectively handle multiple poisoned models with different backdoors by labeling them as outliers."（§4.3.1）
5. **支撑步骤 5（中位数边界必须含被剔除模型）**："It should be noted that for determining the clipping bound, the rejected models are also considered to ensure that even if benign models were filtered, the computed median St is still determined based on benign values."（§4.3.2）
6. **支撑步骤 6（裁剪定义与逐坐标乘法）**："Clipping scales down model updates as follows: W c bl = Gt−1 +(Wbl −Gt−1)· MIN(1,γ) (detailed in line 8-11 of Alg. 1) where the multiplication is computed coordinate-wise."（§4.3.2）
7. **支撑步骤 7（等权聚合）**："Hence, we follow common practice in literature and weight the contributions of all clients equally regardless of their dataset size"（§4.3.2）
8. **支撑步骤 8（加噪公式与 λ、ε 取值）**："We use standard DP parameters and set ε = 3705 for IC, ε = 395 for the NIDS and ε = 4191 for the NLP scenario. Accordingly, λ = 0.001 for IC and NLP"（§B.3）

```json
{
  "key": "nguyen2022flame",
  "method": "FLAME: dynamic HDBSCAN clustering filtering on pairwise cosine distances, adaptive clipping to the median L2 distance, and adaptive Gaussian noising of the aggregated global model",
  "stages": ["server_distribute", "server_receive", "server_aggregate", "server_post_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "flatten_and_serialize_local_models",
      "operator": "flatten_weights",
      "input": "每个客户端的本地模型 W_i，含全部权重与偏置共 p 个参数，结构同全局模型",
      "output": "p 维权重向量 W_i；n 个客户端构成 n×p 矩阵",
      "params": {"order": "所有模型使用同一个预定展平顺序（论文未规定具体顺序）"},
      "source": "§3"
    },
    {
      "step": "pairwise_cosine_distances",
      "operator": "cosine_distance_matrix",
      "input": "n 个 p 维本地更新向量 W_1..W_n",
      "output": "n×n 余弦距离矩阵 (c_ij)，c_ij 越小越同向",
      "params": {"metric": "1 - cos(theta) = 1 - (W_i·W_j)/(||W_i|| ||W_j||)"},
      "source": "公式 (2)（§3）；Alg. 1 第 6 行"
    },
    {
      "step": "hdbscan_majority_cluster_filtering",
      "operator": "density_cluster_majority",
      "input": "n×n 余弦距离矩阵 (c_ij)",
      "output": "被接纳模型索引 (b_1..b_L)，其余 n-L 个为离群点被剔除",
      "params": {"min_cluster_size": "n/2+1", "min_samples": 1, "n_clusters": "动态确定，不预设", "input_type": "预计算距离矩阵", "selection": "取覆盖至少 n/2+1 个点的、密度最同质的候选簇为多数簇"},
      "source": "§4.3.1、§E；Alg. 1 第 7 行"
    },
    {
      "step": "euclidean_distance_to_previous_global",
      "operator": "euclidean_distance_to_global",
      "input": "G*_{t-1}（p 维）与 W_1..W_n（n×p）",
      "output": "n 维非负标量 (e_1..e_n)",
      "params": {},
      "source": "公式 (3)（§3）；Alg. 1 第 8 行"
    },
    {
      "step": "median_norm_clipping_bound",
      "operator": "median_of_norms",
      "input": "(e_1..e_n)，包含被聚类剔除的模型",
      "output": "标量裁剪边界 S_t",
      "params": {"statistic": "median"},
      "source": "Alg. 1 第 9 行；§4.3.2"
    },
    {
      "step": "scale_clip_admitted_updates",
      "operator": "clip_to_median_norm",
      "input": "被接纳的 W_{b_1}..W_{b_L}（L×p）、对应距离 e_{b_l}、边界 S_t、基准模型",
      "output": "裁剪后的 W^c_{b_1}..W^c_{b_L}（L×p）",
      "params": {"gamma": "S_t / e_{b_l}", "multiplier": "MIN(1, gamma)，逐坐标相乘"},
      "source": "Alg. 1 第 10-11 行；§4.3.2"
    },
    {
      "step": "equal_weight_aggregation",
      "operator": "equal_weight_average",
      "input": "L 个裁剪后的更新",
      "output": "未加噪全局模型 G_t（p 维）",
      "params": {"weight": "1/L，不使用客户端数据集大小"},
      "source": "Alg. 1 第 12 行；§2.1、§4.3.2"
    },
    {
      "step": "adaptive_gaussian_noising",
      "operator": "gaussian_noise_global",
      "input": "G_t（p 维）、S_t、(epsilon, delta)",
      "output": "加噪全局模型 G*_t（p 维），作为下一轮下发给客户端的模型",
      "params": {"lambda": "(1/epsilon)*sqrt(2*ln(1.25/delta))；IC 0.001、NLP 0.001、NIDS 0.01", "epsilon": "IC 3705、NIDS 395、NLP 4191", "delta": "论文未给出数值", "sigma": "lambda * S_t", "noise": "N(0, sigma^2) 加到全局模型参数上"},
      "source": "Alg. 1 第 13-14 行；公式 (6)(7)；§5.1、§B.3"
    }
  ],
  "sampling": [
    {"what": "clients", "how": "不做随机抽样；HDBSCAN 只保留唯一多数簇的成员，簇外模型整体剔除，被接纳者等权参与聚合", "size": "多数簇至少 n/2+1 个客户端；实验 n=100（§5.1 表 1、§7.2）、n=200（§7.2 model alignment）"},
    {"what": "rounds", "how": "论文未使用跨轮信息，FLAME 是 round-independent 的，S_t 与 sigma 每轮独立重算，噪声不跨轮累积", "size": "T 轮；T 的具体取值论文未给出"},
    {"what": "probes", "how": "论文未使用参考数据或探针样本", "size": "无"},
    {"what": "samples", "how": "论文未使用，聚合方不访问任何训练数据或参考样本", "size": "无"},
    {"what": "layers", "how": "论文未对层做抽样；展平是全体权重与偏置的序列化约定，不是抽样", "size": "全部层，p 个参数（表 2：约 431k 至 20M）"},
    {"what": "coordinates", "how": "论文未对参数坐标做抽样或降维；裁剪是对整条更新向量乘同一因子（逐坐标等比例），不是逐坐标独立裁剪", "size": "完整 p 维"}
  ],
  "resources": [
    "HDBSCAN 聚类实现（§4.3.1 引用 Campello et al. [13]，§E 引用 McInnes et al. [40,41]），需支持预计算距离矩阵、min_cluster_size=n/2+1、min_samples=1",
    "无需干净参考数据、根数据集或探针数据（§4.1、§5.1(S2) 明确聚合方没有训练数据）",
    "无需预训练检测器、无需对齐前后的权重、无需额外模型",
    "(epsilon, delta) 配置；论文给出 epsilon 与 lambda 的取值，但未给出 delta 的数值（§B.3）",
    "private FLAME 额外需要：一个与聚合方不共谋的外部服务器 B、ABY 安全两方计算框架 [16]、Bozdemir et al. 的隐私保护 DBSCAN 实现 [12]，以及两台服务器（§8、§G）"
  ],
  "actions": ["exclude_client", "clip", "add_noise"],
  "dominant_cost": "服务器端每轮对 n 个 p 维模型计算 n×n 余弦距离矩阵（O(n^2 p)）并对其运行 HDBSCAN（§E 描述的最小生成树构建，§8 称其 very expensive），成本随客户端数 n 的平方与参数量 p 增长；裁剪与加噪为 O(L p)。论文报告的非私有开销是收敛所需的额外轮数（平均 1.67 轮、最多 4 轮，§D），私有版本单轮服务器侧可达 22081.65 秒（§G）。",
  "underspecified": [
    "Alg. 1 第 11 行裁剪的基准模型写作 G_{t-1}，而客户端训练用的是加噪后的 G*_{t-1}，究竟以哪一个为基准，论文未说明",
    "delta 的具体数值未给出，也未说明如何由数据集确定 DP 预算",
    "n 是当轮实际参与客户端数还是客户端总池大小未说明（§7.3 中每轮参与数在 60 到 90 之间浮动）",
    "MEDIAN 的具体定义（偶数个元素时取平均还是取下中位数）未说明",
    "余弦距离在存在零范数更新时的定义未说明",
    "聚类结果为空或全部被标为离群点时的处理未说明",
    "高斯噪声是否逐坐标独立采样、是否对权重与偏置一视同仁、是否跳过 BatchNorm 等参数，论文未逐字说明",
    "本地训练超参数（本地 epoch、学习率、批大小）与总轮数 T 未给出，而它们会影响 L2 范数进而影响 S_t 与 sigma（§4.3.2）",
    "private FLAME 中用 DBSCAN 近似 HDBSCAN 时，邻域参数 epsilon 的二分搜索范围与停止条件未在正文给出",
    "表 1 中直接给定的 sigma（0.01、0.08、0.10）与 Alg. 1 的 sigma = lambda*S_t 是两套口径，二者的关系未说明"
  ],
  "quotes": [
    {"supports": "步骤 1：把所有模型的权重/偏置按同一预定顺序展平", "text": "we represent Neural Networks (NNs) using their weight vectors, in which the extraction of weights is done identically for all models by flattening/serializing the weight/bias matrices in a predetermined order"},
    {"supports": "步骤 2-3：两两余弦距离 + HDBSCAN 聚类", "text": "FLAME uses pairwise cosine distances to measure the angular differences between all model updates and applies the HDBSCAN clustering algorithm [13]."},
    {"supports": "步骤 3：min_cluster_size 取 n/2+1，保证多数簇为多数更新", "text": "we set the minimum cluster size to be at least 50% of the clients, i.e., n/2 + 1, so that the resulting cluster will contain the majority of updates"},
    {"supports": "步骤 3：离群点即被剔除，且能处理多个同时注入的后门", "text": "In particular, HDBSCAN labels models as outliers if they do not fit into any cluster. This allows FLAME to effectively handle multiple poisoned models with different backdoors by labeling them as outliers."},
    {"supports": "步骤 5：裁剪边界的中位数必须基于全部 n 个模型（含被剔除者）", "text": "It should be noted that for determining the clipping bound, the rejected models are also considered to ensure that even if benign models were filtered, the computed median St is still determined based on benign values."},
    {"supports": "步骤 6：裁剪公式与逐坐标乘法", "text": "Clipping scales down model updates as follows: W c bl = Gt-1 +(Wbl -Gt-1)* MIN(1,gamma) (detailed in line 8-11 of Alg. 1) where the multiplication is computed coordinate-wise."},
    {"supports": "步骤 7：等权聚合，不使用客户端数据集大小", "text": "Hence, we follow common practice in literature and weight the contributions of all clients equally regardless of their dataset size"},
    {"supports": "步骤 8：epsilon 与 lambda 的取值", "text": "We use standard DP parameters and set epsilon = 3705 for IC, epsilon = 395 for the NIDS and epsilon = 4191 for the NLP scenario. Accordingly, lambda = 0.001 for IC and NLP"}
  ]
}
```
