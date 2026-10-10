# li2022lomar：LoMar（Local Malicious Factor，局部恶意因子）

## 1. 方法一句话

LoMar 是一个运行在聚合器（aggregator）一侧的两阶段防御：输入是本轮从全部 N+M 个客户端收到的本地模型更新集合 U = {u_1^t, …, u_{N+M}^t}（论文第 3.2 节记号），第一阶段用「k 近邻 + 逐输出标签的高斯核密度估计（Kernel Density Estimation, KDE）」为每个更新算出一个数值化的恶意因子 F(i)，第二阶段用一个阈值 ε 把 F(i) 变成二值控制器 δ(i) ∈ {0,1}，并据此改写聚合公式（式 (3)），输出被净化后的联合模型 w̃_t；它不改变客户端的训练过程，也不修改客户端上传的更新本身，只是决定哪些更新被计入聚合。

## 2. 运行位置

所有阶段都在服务器端，位置是「服务器收到更新之后、服务器聚合之中」，没有客户端侧算子，也不需要额外往返。

- **服务器收到更新**：收集本轮全部 N+M 个更新，做参数维度切分与按输出标签分组（图 3 (a)(b)，第 3.1 节）。
- **服务器收到更新后、聚合前**：k 近邻搜索、平均近邻距离、逐标签 KDE、逐标签恶意因子、跨标签连乘得到 F(i)（第 3.2 节，式 (4)–(9)，算法 1）。
- **服务器聚合时**：由式 (10) 求 ε_m、取 ε = min{1, ε_m}、逐客户端二值判定 δ(i)、按式 (3) 做门控加权求和（第 3.3 节，算法 2）。
- **聚合之后**：得到的 w̃_t 就是本轮联合模型，按正常 FL 流程在下一轮下发（论文未把任何额外信息下发给客户端）。

**是否需要客户端与服务器之间额外往返**：不需要。论文第 3.4 节讨论效率时只提到「the implementation of LoMar defense requires an extra computational cost on the aggregator side」，即额外代价只在聚合器算力上，通信轮次不变。

## 3. 算子流水线

以下按执行顺序列出。记号：N 为诚实的客户端数，M 为注入的恶意客户端数，样本总数 l = Σ_i l_i，d 为模型更新展平后的参数维度，R 为输出标签（类别）数。

### 步骤 1：收集本轮全部更新
- **输入**：每个客户端的本地更新 u_i^t = w_i^t − w^{t−1}（第 2.1 节 Step II 定义），展平为 d 维向量；全部拼接成 U ∈ R^{(N+M)×d}。
- **计算**：无，仅收集。论文第 3.2 节开头直接令 U = {u_1^t, u_2^t, …, u_{N+M}^t}。
- **输出**：U ∈ R^{(N+M)×d}。
- **出处**：第 3.2 节首段；第 2.1 节 Step II。

### 步骤 2：按参数维度切分并按输出标签分组
- **输入**：每个客户端的更新 u_i ∈ R^d。
- **计算**：图 3 描述的三步预处理中的前两步：(a) 预处理阶段把远程更新「divided by the dimension of the parameter features」；(b) 把参数「clustered based on the output labels」。即把 u_i 拆成 R 个与输出标签对应的子向量 u_i^r，r ∈ [1, R]。论文用 y = [y_1, …, y_r, …, y_R] 表示输出标签，并假设 Σ_{r=1}^R P(u_i|y_r) = 1。
- **输出**：每个客户端的 R 个标签子向量 {u_i^1, …, u_i^R}（论文未给出子向量的具体维度，图 3 中用「Dimension 1 … Dimension o」表示）。
- **出处**：图 3 及其说明、第 3.2 节「Density based malicious factor F(i)」段。
- **注意**：论文只说「按输出标签聚类参数」，没有给出切分规则本身（见第 9 节）。

### 步骤 3：k 近邻搜索
- **输入**：U ∈ R^{(N+M)×d}。
- **计算**：对每个 u_i，在全部 N+M 个更新中找 k 个最近邻，构成邻域参考集 U_i = {u_i,1, …, u_i,j, …, u_i,k}。距离度量由第 3.2 节的 diff(·,·) 给出，即平方欧氏距离（squared Euclidean distance）‖·‖²。论文强调 k ≪ N+M，并取 k ≤ 0.4N 作为「最大潜在恶意数」的宽松上界。
- **输出**：每个 u_i 的邻居下标集合与对应的 U_i（k×d）。
- **出处**：第 3.2 节「k-nearest neighborhood mapping」段；第 3.1 节（k ≪ N+M、k ≤ 0.4N）；算法 1 第 2–4 行（邻域为空时构建邻域）。

### 步骤 4：计算平均近邻距离与邻域平均距离
- **输入**：U_i。
- **计算**：先算 u_i 到其 k 个邻居的平均距离 d̄_i = (1/k) Σ_{j=1}^{k} diff(u_i, u_i,j)；再算邻域内两两距离的均值 D̄_i = 1/(k(k−1)) Σ_{i=1}^{k} Σ_{j=1}^{k} diff(u_i, u_i,j)，i ≠ j（式 (4)；注意论文把客户端下标 i 复用为求和下标）。论文的直觉描述是：低密度区域 d̄_i 大，比值 d̄_i / D̄_i 会「spread out」，高密度区域相反。
- **输出**：每个客户端两个标量 d̄_i、D̄_i（论文最终只把该比值作为 F(i) 的统计解释，见式 (9) 后的说明）。
- **出处**：第 3.2 节；式 (4)；定理 2 的证明式 (11)。

### 步骤 5：逐输出标签的高斯核密度估计
- **输入**：第 r 个标签子空间中的 u_i^r 与其邻居的对应分量 u_i,j^r。
- **计算**：q̃(u_i^r) = (1/k) Σ_{j=1}^{k} K((u_i^r − u_i,j^r)/h^r)（式 (5)），核函数取高斯核 K((u_i^r − u_i,j^r)/h) = 1/((√(2π))h) · exp(−|u_i^r − u_i,j^r| / (2h))（式 (6)，按 PDF 抽取的写法；见第 9 节的尺度不一致问题）。h 是带宽，论文说明它是与学习分类器相关的用户自定义常数，理论上可以对每个输出标签取不同的 h^r，但本文统一取常数。
- **输出**：每个客户端在每个标签上的局部密度估计 q̃(u_i^r)，共 R 个标量。
- **出处**：第 3.2 节；式 (5)、(6)；算法 1 第 5 行。

### 步骤 6：逐标签的局部密度比值打分
- **输入**：q̃(u_i^r) 与邻居的密度 q̃(u_j^r)，j ∈ [1, k]。
- **计算**：F(i)^r = Σ_{j=1}^{k} q̃(u_j^r) / (k · q̃(u_i^r))（式 (7)）。即在第 r 个标签上，用「邻居的平均密度」除以「自身的密度」。
- **输出**：每个客户端 R 个标量 F(i)^1, …, F(i)^R。
- **出处**：第 3.2 节；式 (7)；算法 1 第 6 行。

### 步骤 7：跨标签连乘得到总恶意因子
- **输入**：F(i)^r，r = 1…R。
- **计算**：在假定不同标签的参数分布条件独立（P(u_i^r, u_i^{r′}|y_r, y_{r′}) = P(u_i^r|y_r)·P(u_i^{r′}|y_{r′})）的前提下，联合概率 P̃(u_i) = Π_{r=1}^{R} P(u_i^r)（式 (8)），于是 Definition 1 给出 F(i) = Σ_{j=1}^{k} q̃(u_j) / (k·q̃(u_i)) = Π_{r=1}^{R} F(i)^r（式 (9)）。论文的解释是：F(i) 越大，u_i 相对其局部邻域核中心的位置越靠近中心；F(i) 在统计意义上等价于 d̄_i / D̄_i。
- **输出**：每个客户端一个标量恶意因子 F(i)。
- **出处**：第 3.2 节 Definition 1；式 (8)、(9)；附录 B；算法 1 第 7 行。
- **注意**：算法 1 的循环体把第 7 行（连乘）写在 for r 循环内部，从字面看每轮都在更新 F(i)，实现时需要自己决定是累乘还是循环结束后再连乘（见第 9 节）。

### 步骤 8：由误报上界求阈值下界 ε_m
- **输入**：k、邻域核密度分布体积 V、平均带宽 h̄（论文写为 h̄，「considered as a constant in this paper」）。
- **计算**：算法 2 第 1 行写「Find the value of ε_m from Eq. (10)」。式 (10)（定理 1）给出误报概率上界 P(F(i) > ε_m) ≤ exp(−4π(ε_m − 1)²(k + 1)²h̄ / (k(2k + ε_m + 1)²V²))。附录 C 给出更细的推导：θ = (ε_m − 1)/V，V = 2π^{(r−1)/2}β^{r−1}/Γ((r−1)/2 + 1)（式 (17)，β 为第 k 近邻到 u_i 的距离，即球半径），并由 McDiarmid 不等式得到 P(LMF(i) > ε_m) ≤ exp(−2θ²/(kξ²))（式 (22)、(23)）。附录 C 明确说明只关心 ε_m > 1 的情形（此时 θ > 0）。
- **输出**：阈值下界 ε_m。
- **出处**：第 3.3 节定理 1 与式 (10)；算法 2 第 1 行；附录 C 式 (15)–(23)。

### 步骤 9：取最终阈值
- **输入**：ε_m。
- **计算**：ε = min{1, ε_m}。论文的动机是定理 2：在只有干净客户端的可信 FL 系统中，当 N → ∞ 时存在边界 σ = E(D̄_i)/E(d̄_i) = 1（式 (11)），F(i) = 1 对应干净更新的边界；为了在保护学习目标的同时尽量剔除恶意更新，取该最小值。
- **输出**：标量阈值 ε。
- **出处**：第 3.3 节定理 2 与式 (11)、第 3.3 节末段；算法 2 第 2 行；附录 D（图 10 显示 ε = 1.0 时平均表现最好）。

### 步骤 10：二值门控判定
- **输入**：F(i) 与 ε。
- **计算**：若 F(i) ≥ ε 则 δ(i) = 1（判为干净），否则 δ(i) = 0（判为恶意）。论文写法是「if F(i) ≥ ϵ, we consider the remote client to be clean, otherwise malicious if F(i) < ϵ」。
- **输出**：二值控制器向量 δ ∈ {0,1}^{N+M}。
- **出处**：第 3.3 节；算法 2 第 3–9 行；式 (3)。

### 步骤 11：门控加权聚合
- **输入**：δ(i)、聚合权重 α_i（论文第 2.1 节定义为 α_i = l_i/l，l_i 为第 i 个客户端私有数据量）、当前联合模型 w̃_{t−1}、各客户端更新 u_i^t。
- **计算**：w̃_t = w̃_{t−1} + Σ_{i=1}^{N+M} δ(i)·α_i·u_i^t（式 (3)；算法 2 第 10 行）。δ(i) = 0 的客户端更新被整条丢弃。
- **输出**：净化后的联合模型 w̃_t。
- **出处**：第 2.3 节式 (3)；第 3.3 节；算法 2 第 10–11 行。

## 4. 采样与规模控制

- **客户端抽样**：论文未对客户端做随机抽样，而是对每个客户端只用它的 k 个最近邻作为参考集（第 3.2 节：用 k 近邻邻域 U_i 代替全部远程更新）。k 的上界取 **k ≤ 0.4N**，理由是防御者不知道恶意客户端数量，该上界对应最大潜在恶意比例（第 3.1 节；恶意预算 M ≤ 0.4N 见第 2.2 节）。**实验中所用的具体 k 值论文未说明**。
- **参数坐标/层抽样**：不做随机抽样，但按输出标签把 d 维更新切成 R 个子空间，逐标签分别做密度估计后再连乘（图 3，第 3.2 节）。R 由数据集决定：MNIST 10、KDDCup99 23、VGGFace2 10、Amazon 50（表 1）。
- **轮次**：每一轮 FL 迭代都重新计算 F(i)、重新取阈值并重新门控；论文没有描述跨轮累积、动量或历史窗口（**论文未说明**是否有跨轮机制）。实验轮数 T = 200（第 4.1.2 节）。
- **参考数据/探针**：**论文未使用**。第 3.4 节明确说明 LoMar 用非参数 KDE 研究统计特征，不需要知道干净训练数据分布，因此不需要公开可信数据集（这是它与 Auror、SAP 的关键区别）。
- **样本抽样**：**论文未使用**，防御过程不接触客户端训练样本。论文只假设输出标签 y 在防御开始时已知（第 3.2 节末）。

## 5. 超参数

防御自身的超参数：

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| k | 每个更新的近邻数，决定参考集 U_i 的大小 | k ≤ 0.4N（宽松上界）；**实验中的具体取值论文未说明** | 第 3.1 节、第 3.2 节；算法 1 第 3 行 |
| K(·) | 核函数形式 | 高斯核 | 式 (6)；附录 C 式 (15) |
| h（或 h^r、h̄） | KDE 带宽，理论上可逐输出标签不同 | 「a user-deﬁned constant value that is correlated to the learning classiﬁer」，本文统一取常数；**具体数值论文未说明** | 第 3.2 节式 (5)、(6)；第 3.3 节定理 1 |
| ε_m | 由误报上界得到的阈值下界 | 由式 (10) 求出，求解方式论文未说明 | 算法 2 第 1 行；定理 1 |
| ε | 最终判定阈值 | ε = min{1, ε_m}；附录 D 的扫描显示 ε = 1.0 时目标/整体准确率的平均值最好 | 第 3.3 节；算法 2 第 2 行；附录 D 图 10 |
| R | 输出标签数（决定连乘项数与参数分组数） | 由数据集决定：MNIST 10、KDDCup99 23、VGGFace2 10、Amazon 50 | 表 1；第 3.2 节 |
| α_i | 聚合权重 | α_i = l_i / l | 第 2.1 节式 (2) |

复现所需的实验设置（非防御超参）：初始联合模型 w_0 = 0，FL 迭代次数 T = 200，每客户端本地训练轮数 E = 5，SGD 批大小 20（第 4.1.2 节）；VGGFace2 上的 SqueezeNet 批大小 8、momentum 0.9、weight decay 0.0001、学习率 0.001（表 2）。数据不平衡参数 λ ∈ [0, 1) 与攻击翻转比例 τ ∈ [0.1, 1) 是实验设置（第 4.1.1、4.1.4 节），不是防御超参。

## 6. 判定与动作

- **判定规则**：逐客户端比较 F(i) 与 ε。F(i) ≥ ε → δ(i) = 1（干净，保留）；F(i) < ε → δ(i) = 0（恶意，丢弃）。阈值本身由两条依据合成：定理 1 给出误报概率上界 P(F(i) > ε_m) ≤ exp(−4π(ε_m − 1)²(k + 1)²h̄ / (k(2k + ε_m + 1)²V²))（式 (10)），定理 2 给出干净边界 σ = E(D̄_i)/E(d̄_i) = 1（式 (11)），最终 ε = min{1, ε_m}（第 3.3 节，算法 2 第 2 行）。
- **动作公式**：被保留的更新按其数据量权重 α_i 参与求和，被剔除的更新整项消失：w̃_t = w̃_{t−1} + Σ_{i=1}^{N+M} δ(i)·α_i·u_i^t（式 (3)）。这是「剔除 + 加权平均」，不是重新加权或缩放。
- **裁剪与加噪**：论文未使用。LoMar 不含梯度裁剪、范数约束或差分隐私噪声。
- **跨轮累积**：论文未说明存在跨轮累积。δ(i) 与 ε 都是每轮由本轮更新独立算出的（算法 2 每轮从第 1 行重新开始）。论文没有给出被剔除客户端权重是否在剩余客户端上重新归一化的说明；按式 (3) 字面实现即为直接丢弃该项、不重新归一化。

## 7. 需要的外部资源

- **不需要**干净参考数据、根数据集（root dataset）或公开可信数据集。第 3.4 节明确对比：Auror 和 SAP 假设防御者能访问与干净训练数据同分布的公开可信数据集，而 LoMar「uses a non-parametric estimation method KDE, for studying the statistical features without knowing the clean training data distribution」。
- **不需要**预训练的检测器，也不需要额外的模型或影子模型；检测器就是 KDE 本身，全在服务器端即时计算。
- **需要**在防御开始时已知输出标签集合 y = [y_1, …, y_R]（第 3.2 节末：「we assume that the output labels are already known at the beginning of LoMar defense」）。
- **需要**按输出标签把参数向量切分成 R 个子空间的规则（图 3）；论文未说明具体切分方法。
- **需要**每个客户端的数据量 l_i 以计算 α_i = l_i/l（第 2.1 节式 (2)），以及本轮全部 N+M 个更新在聚合器内存中同时可用。
- **规模（实验规模）**：MNIST 1000 客户端、每客户端 600 样本、注入 100 个恶意客户端（第 4.1.1、4.1.4 节）；KDDCup99 23 客户端、3 个恶意客户端（源类 11 → 目标类 9）；Amazon 50 客户端、每客户端 150 样本、5 个恶意客户端（源 15 → 目标 10）；VGGFace2 200 客户端、20 个恶意客户端（3→2 与 10→9 各 10 个）。攻击者预算 M ≤ 0.4N（第 2.2 节）。

## 8. 计算与存储开销

**论文报告的开销**：第 3.4 节称，实施 LoMar 会给聚合器带来额外计算开销，但对 FL 效率的影响有限，因为 FL 的学习速度由聚合器与客户端之间的通信代价主导；额外开销「mainly from the development of the k-nearest neighborhood, which is proved as O(N) in [24]」；并指出聚合器的算力通常远强于远程客户端，因此聚合器上的线性开销也被认为有限。论文没有报告墙钟时间、内存占用或每轮实际耗时。

**按流水线的开销来源（分析：）**：
- 主要开销在步骤 3（k 近邻搜索）：需要计算 (N+M) 个 d 维更新两两之间的平方欧氏距离，朴素实现是 O((N+M)²·d) 次标量运算，再对每个客户端选出 k 个最小距离；随后步骤 5 的 KDE 只需 O((N+M)·k·R) 次核函数求值（每个近邻在每个标签维度上一次）。因此开销随客户端总数 (N+M)、更新维度 d（Amazon 的输入特征是 10000 维、VGGFace2 的 SqueezeNet 参数量更大）和 k 增长。
- 存储：聚合器需要同时持有 (N+M)×d 的全部更新（步骤 1）以及 O((N+M)²) 的距离矩阵（若缓存）；KDE 输出只有 (N+M)×R 个标量，可忽略。
- 与论文的 O(N) 说法的关系（分析：）：论文引用的 O(N) 是 [24] 中近邻搜索的复杂度结论，未说明其隐含的数据结构或维度假设；按朴素两两距离实现会得到二次复杂度，因此实际实现若要贴近 O(N) 需要额外的近邻索引结构（论文未说明用了什么结构）。
- 额外通信开销为零（分析：）：LoMar 只消费本轮已有的更新，不产生新的上行/下行消息，符合第 3.4 节「额外代价在聚合器计算侧」的说法。

## 9. 实现时容易错的地方

**论文明确写到的细节**：

1. **判定方向不能反**：F(i) ≥ ε 是**干净**，F(i) < ε 才是恶意（第 3.3 节）。F(i) 越大表示该更新越靠近其局部邻域的核中心，即越「正常」。
2. **距离用平方欧氏距离**：diff(·,·) 明确是 squared Euclidean distance（第 3.2 节），不是欧氏距离本身，也不带开方。
3. **k 是有上界约束的超参**：k ≤ 0.4N，且论文强调 k ≪ N+M（第 3.1 节）。
4. **不需要干净数据**：不要为了「校准阈值」额外引入探针数据集，这与论文的隐私前提（第 3.4 节）相冲突。
5. **阈值只取到 1**：ε = min{1, ε_m}，且附录 C 说明只关心 ε_m > 1 的情形，因此实际阈值通常被截到 1；附录 D 的经验扫描也显示 ε = 1.0 平均最好。
6. **连乘在概率意义下成立的前提**：式 (8)、(9) 依赖不同输出标签参数之间条件独立的假设（第 3.2 节、附录 B），实现时若不做该假设就不能直接连乘。

**论文没说清、实现时必须自己决定的地方**：

1. **带宽 h 的数值**：论文只说它是「user-deﬁned constant value」且与分类器相关，也承认「theoretically, the value of h could be different for each output label」，但全文没有给出任何取值或调参范围；还明确说「ﬁnding the optimal hyperparameter is not the goal of this paper」（第 3.2 节）。
2. **k 的数值与取整规则**：只给了 k ≤ 0.4N 的上界，实验部分没有报告实际用的 k；像 KDD 场景 N+M = 26（23 干净 + 3 恶意）时 0.4N = 9.2，取整规则论文未说明。
3. **更新的逐标签切分方法**：图 3 只说「divided by the dimension of the parameter features」和「the parameters are clustered based on the output labels」，没有给出如何把 d 维参数映射到 R 个标签子空间的规则，也没有给出子空间维度 o 的定义。对单层逻辑回归可以按输出权重行分组，但这是实现者的推断，不是论文的说明。
4. **ε_m 的求解方式**：算法 2 第 1 行写「Find the value of ε_m from Eq. (10)」，但式 (10) 是误报概率的**不等式上界**而不是等式，论文没有说明是固定一个目标误报率反解、还是直接把 ε_m 设成某个值；附录 D 只做了 ε 的经验扫描。
5. **核函数与其归一化在两处不一致**：式 (6) 写 exp(−|u_i^r − u_i,j^r| / (2h))、系数 1/((√(2π))h)（指数里是一阶绝对值、且没有平方）；附录 C 式 (15) 写 exp(−|u_{i,j}|² / (2h̄))、系数 1/((2π)^{r/2} h^r)（指数里是平方、归一化随维度 r 变化）。实现时必须自己决定用哪一版。
6. **上界表达式也两处不一致**：式 (10) 是 exp(−4π(ε_m − 1)²(k + 1)²h̄ / (k(2k + ε_m + 1)²V²))，附录式 (23) 是 exp(−2(ε_m − 1)²(k + 1)²(2π)^r h̄^{2r} / (k(2k + ε + 1)²V²))（式 (23) 中写作 ε 而不是 ε_m），两者不能同时成立。
7. **附录式 (15) 的求和与前置系数不匹配**：求和是 Σ_{j=1}^{k}，但前置因子写成 1/(k+1)；式 (16) 又变成 1/(k(k+1))。实现时需要自己决定归一化因子。
8. **空邻域的处理是循环定义**：算法 1 第 2–4 行写「if The local neighborhood Ui is empty then Build the neighborhood Ui and obtain the reference set U_i^r for each output label.」，在没有邻居的情况下如何建邻域，论文未说明。
9. **近邻是否包含 u_i 自身、距离在哪个空间算**：d̄_i 定义在完整的 u_i 上（第 3.2 节），而 q̃ 定义在逐标签分量 u_i^r 上（式 (5)）；k 近邻到底在完整 d 维参数空间还是在切分后的子空间上搜索，论文未说明。
10. **数值稳定性**：当某个标签上的 q̃(u_i^r) = 0 时式 (7) 的分母为零，R 较大时（Amazon 的 R = 50）连乘式 (9) 也容易下溢；论文没有给出任何平滑、取对数或截断的处理（分析：）。
11. **定理 1 的叙述方向与判定规则表面矛盾**：定理 1 把 P(F(i) > ε_m) 称为「false detecting a clean update as malicious」的概率（第 3.3 节），但按判定规则 F(i) ≥ ε 是判为干净，两者方向不一致；实现时必须自己决定这个上界约束的是哪一类错误（分析：）。
12. **被剔除权重的处理与是否跨轮记忆**：论文没有说明是否对剩余客户端重新归一化 α_i，也没有说明 δ(i)、ε、F(i) 是否跨轮复用（第 3.3 节与算法 2 都按单轮描述）。

## 10. 原文依据

1. **支撑步骤 3（k 近邻搜索）**："In phase I, for the i-th remote update at the t-th iteration, LoMar ﬁnds its k-nearest neighbors to be its neighborhood reference set Ui = {ui,1, . . . , ui,k}, where k ≪N + M."
2. **支撑步骤 3 的 k 取值依据**："Thus, we pursue an alternative solution that deﬁnes the value of k ≤0.4N to be a loose bound, corresponding to the maximum number of potential malicious."
3. **支撑步骤 4（平均近邻距离）**："To evaluate their relative positions to the kernel center ui, we calculate the averaged l2 norm distance between ui to neighbors in Ui, where the averaged distance is deﬁned as"
4. **支撑步骤 5（逐输出标签 KDE）**："As such, we use a state-of-art non-parametric estimation method, which is the kernel density estimation (KDE) [19], to estimate the local density distribution function for ui according to each output label in the FL joint model."
5. **支撑步骤 5 的带宽超参**："And h is the bandwidth of K(·), which is a user-deﬁned constant value that is correlated to the learning classiﬁer."
6. **支撑步骤 7（跨标签连乘得到 F(i)）**："Deﬁnition 1. From the relationship between each label ur i and the remote update ui, we give the deﬁnition F(i) from the obtained F(i)r that"
7. **支撑步骤 9（阈值取 min{1, ε_m}）**："Thus, in order to protect the FL learning objective and remove as many the malicious remote updates in LoMar, we deﬁne the optimal threshold ϵ = min{1, ϵm}."
8. **支撑步骤 10 与步骤 11（二值判定与门控聚合）**："Formally, if F(i) ≥ϵ, we consider the remote client to be clean, otherwise malicious if F(i) < ϵ."

```json
{
  "key": "li2022lomar",
  "method": "LoMar (Local Malicious Factor): two-phase server-side defense that scores each client update by a per-output-label Gaussian KDE ratio over its k nearest neighbors, then gates aggregation with a threshold epsilon = min(1, epsilon_m)",
  "stages": ["server_receive", "server_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {"step": "收集本轮全部客户端更新", "operator": "collect_client_updates", "input": "N+M 个客户端的本地更新 u_i^t，每个为 d 维展平向量", "output": "U ∈ R^{(N+M)×d}", "params": {}, "source": "Sec. 3.2 first paragraph; Sec. 2.1 Step II"},
    {"step": "按参数维度切分并按输出标签分组", "operator": "split_update_by_output_label", "input": "每个客户端的 u_i ∈ R^d", "output": "R 个标签子向量 u_i^r，r=1..R（子空间维度论文记为 o，未给定义）", "params": {"R": "输出标签数，MNIST 10 / KDD 23 / VGGFace2 10 / Amazon 50 (Table 1)"}, "source": "Fig. 3 (a)(b); Sec. 3.2 density-based factor paragraph"},
    {"step": "k 近邻搜索（平方欧氏距离）", "operator": "knn_squared_euclidean", "input": "U ∈ R^{(N+M)×d}", "output": "每个 u_i 的邻域参考集 U_i = {u_i,1,...,u_i,k}", "params": {"k": "≤ 0.4N，实验具体取值论文未说明", "metric": "squared Euclidean distance ||·||^2"}, "source": "Sec. 3.2 k-nearest neighborhood mapping; Sec. 3.1; Algorithm 1 lines 2-4"},
    {"step": "平均近邻距离与邻域平均距离", "operator": "mean_neighbor_distance", "input": "U_i", "output": "标量 d̄_i 与 D̄_i", "params": {}, "source": "Sec. 3.2; Eq. (4); Eq. (11)"},
    {"step": "逐输出标签高斯核密度估计", "operator": "gaussian_kde_local_density", "input": "第 r 个标签上的 u_i^r 及其邻居分量 u_i,j^r", "output": "q̃(u_i^r)，共 R 个标量/客户端", "params": {"h": "用户自定义常数带宽，具体数值论文未说明", "kernel": "Gaussian"}, "source": "Eq. (5); Eq. (6); Algorithm 1 line 5"},
    {"step": "逐标签局部密度比值打分", "operator": "local_density_ratio_score", "input": "q̃(u_i^r) 与 q̃(u_j^r), j=1..k", "output": "F(i)^r，共 R 个标量/客户端", "params": {}, "source": "Eq. (7); Algorithm 1 line 6"},
    {"step": "跨标签连乘得到总恶意因子", "operator": "product_across_labels", "input": "F(i)^r, r=1..R", "output": "标量 F(i)", "params": {"independence": "假设不同输出标签参数条件独立"}, "source": "Eq. (8); Eq. (9) Definition 1; Appendix B; Algorithm 1 line 7"},
    {"step": "由误报上界求阈值下界", "operator": "threshold_from_false_alarm_bound", "input": "k、邻域体积 V、平均带宽 h̄", "output": "阈值下界 ε_m", "params": {"V": "式 (17) 定义的邻域球体积，半径 β 为第 k 近邻距离"}, "source": "Theorem 1 / Eq. (10); Algorithm 2 line 1; Appendix C Eq. (17)-(23)"},
    {"step": "取最终阈值", "operator": "min_with_one", "input": "ε_m", "output": "标量阈值 ε", "params": {"epsilon": "min{1, ε_m}；Appendix D 经验上 ε=1.0 平均最好"}, "source": "Sec. 3.3; Theorem 2 / Eq. (11); Algorithm 2 line 2; Appendix D"},
    {"step": "二值门控判定", "operator": "binary_gate", "input": "F(i) 与 ε", "output": "δ ∈ {0,1}^{N+M}", "params": {"rule": "F(i) ≥ ε → δ(i)=1 (clean); F(i) < ε → δ(i)=0 (malicious)"}, "source": "Sec. 3.3; Algorithm 2 lines 3-9; Eq. (3)"},
    {"step": "门控加权聚合", "operator": "masked_weighted_average", "input": "δ(i)、α_i = l_i/l、w̃_{t-1}、u_i^t", "output": "净化后的联合模型 w̃_t", "params": {"alpha_i": "l_i / l"}, "source": "Eq. (3); Algorithm 2 lines 10-11; Sec. 2.1 Eq. (2)"}
  ],
  "sampling": [
    {"what": "clients", "how": "每个客户端的恶意因子只在其 k 个最近邻组成的参考集上计算，而不是用全部 N+M 个更新", "size": "k ≤ 0.4N；实验具体 k 值论文未说明"},
    {"what": "coordinates", "how": "按输出标签把 d 维更新切成 R 个子空间，逐标签做 KDE 后再连乘（维度分组，非随机抽样）", "size": "R = 10 (MNIST) / 23 (KDDCup99) / 10 (VGGFace2) / 50 (Amazon)，Table 1"},
    {"what": "rounds", "how": "每个 FL 轮次独立重算 F(i)、ε 与 δ(i)，论文未说明跨轮累积或窗口机制", "size": "T = 200 轮，Sec. 4.1.2"},
    {"what": "probes", "how": "论文未使用任何参考数据或探针数据集，第 3.4 节明确说明不需要干净训练数据分布", "size": "0"}
  ],
  "resources": [
    "无需干净参考数据、根数据集或公开可信数据集 (Sec. 3.4 明确与 Auror、SAP 对比)",
    "无需预训练检测器或额外模型，KDE 在聚合器端即时计算",
    "需要预先知道输出标签集合 y=[y_1,...,y_R] (Sec. 3.2 末)",
    "需要按输出标签把参数向量切成 R 个子空间的规则 (Fig. 3)，论文未说明具体划分方法",
    "需要每个客户端的数据量 l_i 以计算 α_i = l_i/l (Sec. 2.1 Eq. 2)",
    "需要聚合器同时持有本轮全部 N+M 个更新 (Sec. 3.2)"
  ],
  "actions": ["exclude_client"],
  "dominant_cost": "聚合器端每轮一次全客户端 k 近邻搜索；论文称额外开销主要来自 k 近邻构建且复杂度为 O(N) (Sec. 3.4)，朴素两两平方欧氏距离实现为 O((N+M)^2 * d) (分析)",
  "underspecified": [
    "KDE 带宽 h 的具体数值论文未说明，只说它是与分类器相关的用户自定义常数，且承认理论上可逐标签不同 (Sec. 3.2, Eq. 5-6)",
    "k 的实验取值未说明，只给出上界 k ≤ 0.4N (Sec. 3.1)；客户端数很少时的取整规则未说明",
    "如何把 d 维更新映射到 R 个输出标签子空间（Fig. 3 的 divided by dimension / clustered based on output labels）论文未说明",
    "ε_m 的求解方式未说明：算法 2 第 1 行要求由 Eq. (10) 求出，但 Eq. (10) 是误报概率上界不等式而非等式",
    "核函数与其归一化在 Eq. (6) 与 Appendix Eq. (15) 之间不一致（指数是一阶还是平方、系数是 1/((√(2π))h) 还是 1/((2π)^{r/2}h^r)）",
    "误报上界在 Eq. (10) 与 Appendix Eq. (23) 之间不一致（4πh̄ 与 2(2π)^r h̄^{2r}）",
    "Appendix Eq. (15) 求和为 j=1..k 但前置因子写作 1/(k+1)，Eq. (16) 又为 1/(k(k+1))，归一化因子不一致",
    "Algorithm 1 第 2-4 行对空邻域的处理是循环定义，论文未说明邻居不足或邻域为空时如何构建",
    "k 近邻是否包含 u_i 自身、距离是在完整参数空间还是逐标签子空间上计算，论文未说明",
    "q̃(u_i^r)=0 导致 Eq. (7) 分母为零、以及 R 较大时 Eq. (9) 连乘下溢的数值处理，论文未说明",
    "是否对被剔除客户端的 α_i 在剩余客户端上重新归一化，论文未说明；Eq. (3) 字面上直接丢弃该项",
    "δ(i)、ε、F(i) 是否跨轮累积或复用，论文未说明，算法 2 按单轮描述",
    "Theorem 1 把 P(F(i) > ε_m) 称为 false detecting a clean update as malicious，与 F(i) ≥ ε 判为 clean 的规则方向不一致",
    "聚合时是否每轮所有 N+M 个客户端都参与，论文未说明客户端采样策略"
  ],
  "quotes": [
    {"supports": "步骤 3：k 近邻搜索构建邻域参考集", "text": "In phase I, for the i-th remote update at the t-th iteration, LoMar ﬁnds its k-nearest neighbors to be its neighborhood reference set Ui = {ui,1, . . . , ui,k}, where k ≪N + M."},
    {"supports": "步骤 3 超参：k 的宽松上界", "text": "Thus, we pursue an alternative solution that deﬁnes the value of k ≤0.4N to be a loose bound, corresponding to the maximum number of potential malicious."},
    {"supports": "步骤 4：平均近邻距离的定义方式", "text": "To evaluate their relative positions to the kernel center ui, we calculate the averaged l2 norm distance between ui to neighbors in Ui, where the averaged distance is deﬁned as"},
    {"supports": "步骤 5：逐输出标签做 KDE 估计局部密度", "text": "As such, we use a state-of-art non-parametric estimation method, which is the kernel density estimation (KDE) [19], to estimate the local density distribution function for ui according to each output label in the FL joint model."},
    {"supports": "步骤 5 超参：带宽 h 由用户定义", "text": "And h is the bandwidth of K(·), which is a user-deﬁned constant value that is correlated to the learning classiﬁer."},
    {"supports": "步骤 7：跨标签连乘得到总恶意因子 F(i)", "text": "Deﬁnition 1. From the relationship between each label ur i and the remote update ui, we give the deﬁnition F(i) from the obtained F(i)r that"},
    {"supports": "步骤 9：最终阈值取 min{1, ε_m}", "text": "Thus, in order to protect the FL learning objective and remove as many the malicious remote updates in LoMar, we deﬁne the optimal threshold ϵ = min{1, ϵm}."},
    {"supports": "步骤 10：二值判定规则（F(i) 越大越干净）", "text": "Formally, if F(i) ≥ϵ, we consider the remote client to be clean, otherwise malicious if F(i) < ϵ."}
  ]
}
```
