# blanchard2017krum：Byzantine-Tolerant Machine Learning

## 1. 基本信息

- **场景**：传统分布式机器学习，更准确地说，是"一台参数服务器（parameter server）加 n 个 worker"的同步分布式随机梯度下降（stochastic gradient descent，SGD）。论文全文没有出现"联邦学习"（federated learning）这一术语，也没有本地多步训练、客户端采样或非独立同分布（non-IID）数据的设定；因此按本任务分类，它属于**传统联邦学习/分布式 SGD**一侧的经典工作，而不是联邦大模型或参数高效微调（parameter-efficient fine-tuning，PEFT）。
- **训练阶段**：训练过程中的**服务器聚合（aggregation）阶段**，即每一轮服务器收到各 worker 的梯度估计并决定参数更新方向的那一步（第 2 节与第 4 节）。
- **论文类型**：**防御**（提出拜占庭鲁棒聚合规则 Krum），并附带必要的攻击面分析（第 3 节的 Lemma 1 说明现有线性组合聚合不具备鲁棒性）。它同时是这一方向的**基础方法**论文。
- **模型与数据规模**：论文没有实验，也没有具体模型或数据集。它只用抽象记号：参数向量维度 d、worker 数 n、拜占庭 worker 数 f。第 7 节提到在现代机器学习中 d 可能高达 1600 亿（引用文献 [22]），第 1 节提到 2012 年 Google 据称用 16000 个处理器训练图像分类器（引用文献 [12]）。没有客户端数、轮次、恶意比例或数据集的实验数值。

## 2. 威胁模型

**攻击者（论文报告）**

- 攻击者是 **Byzantine worker（拜占庭 worker）**，即"behaving arbitrarily"（行为完全任意）的参与方，数量至多 f 个，可能对应真实故障（进程停滞）或数据分布偏差（第 1 节、第 2 节）。
- **占比与成立条件**：Krum 要求 2f + 2 < n（第 4 节命题 1）；m-Krum 要求 2f + 2 < n − m（第 6 节命题 3）。论文没有给出具体百分比实验。
- **能力**：拜占庭 worker 在第 t 轮可以提出**任意**向量 V_b^t（第 2 节）；如果它不发送向量，服务器就按默认值 0 处理（第 2 节）；多个拜占庭 worker 可以互相勾结（第 2 节、第 4 节 Figure 3 的说明）；它们提出的向量可以依赖正确 worker 提出的向量（第 4 节命题 1 明确写 "possibly dependent on the Vi's"）。
- **知识**：拜占庭 worker 完全知道系统，包括选择函数 F、其他 worker 提出的向量（第 2 节末段）。第 3 节 Lemma 1 的攻击还要利用其他 worker 的向量来构造 V_n。
- **目标**：**无目标破坏**——阻止收敛、把更新方向拉到任意位置。Lemma 1 说明单个拜占庭 worker 可以迫使服务器选择任意向量 U；第 3 节还指出它可以"too large in amplitude or too far in direction"。论文没有涉及后门（backdoor）、隐私或安全对齐破坏。

**防御者（论文报告）**

- 防御者是**参数服务器**，论文明确假设它可靠，其单点失效问题由状态机复制（state-machine replication）这类经典技术解决（第 2 节脚注 2）。
- 服务器每一轮能看到全部 n 个 worker 提交的 d 维向量（包括缺失时补的 0），并在其上执行一个确定性选择函数 F（第 2 节）。
- 服务器信任的结构性假设是：至多 f 个 worker 拜占庭，其余 n − f 个正确 worker 的梯度估计独立同分布且无偏（第 2 节）。

## 3. 攻击入口与流程位置

论文研究的攻击进入位置是**本地训练过程中梯度估计的产生，以及更新上传前的向量本身**，也就是"worker 回传给服务器的那个向量可以任意"，具体流程如下（第 2 节）：

1. 第 t 轮，参数服务器把当前参数向量 x_t 广播给全部 worker。
2. 每个正确 worker p 用自己那部分数据计算梯度估计 V_p^t = G(x_t, ξ_p^t)，其中 ξ_p^t 表示抽到的样本。
3. 每个拜占庭 worker b 提出任意向量 V_b^t；它也可以什么都不发，此时服务器视为收到 0。
4. 服务器用选择函数 F 聚合并更新：x_{t+1} = x_t − γ_t · F(V_1^t, …, V_n^t)。

其中第 3 节 Lemma 1 给出了针对线性组合聚合的具体构造：若 F_lin = Σ λ_i V_i 且 λ_i 非零，则拜占庭 worker 提交 V_n = (1/λ_n)·U − Σ_{i<n} (λ_i/λ_n)·V_i，就能让 F 恒等于任意指定的 U。这个构造需要看到其他 worker 的向量，因此它的进入点在"更新上传前"，而不是在本地数据准备阶段。

**论文未说明/不涉及**：本地数据投毒、损失函数或优化器篡改、服务器端聚合算法被篡改、全局模型下发被篡改、评估与部署阶段的攻击。攻击者也不控制服务器（服务器被假设为可靠）。

## 4. 方法原理

论文的核心思想是**不检测谁是拜占庭，而是直接换掉聚合规则**，使服务器选出的方向在理论上被约束在真实梯度附近。

1. **负面结果（第 3 节 Lemma 1）**：任何形如 F_lin(V_1,…,V_n) = Σ λ_i·V_i 的线性组合，只要 λ_i 非零，单个拜占庭 worker 就能让输出等于任意向量 U，因此现有平均类方法连一个拜占庭 worker 都无法容忍。论文还指出，服务器理论上可以把 λ_n 设为 0 来抵消它，但这"requires means to detect which worker is Byzantine"，也就是需要检测能力。
2. **弹性定义（第 3 节 Definition 1）**：定义 (α, f)-Byzantine Resilience。条件 (i) 是 ⟨E F, g⟩ ≥ (1 − sin α)·||g||² > 0，即选择出的向量平均而言与真实梯度 g 的夹角不超过 α；条件 (ii) 是对 r = 2, 3, 4，E||F||^r 被正确梯度估计 G 的各阶矩的线性组合从上方控制。
3. **Krum 选择函数（第 4 节）**：先定义 i → j 表示 V_j 属于离 V_i 最近的 n − f − 2 个向量；再定义每个 worker 的得分 s(i) = Σ_{i→j} ||V_i − V_j||²，求和只跑遍 V_i 的 n − f − 2 个最近邻；最后 Kr(V_1,…,V_n) = V_{i*}，其中 i* 是得分最小者（若并列，取标识最小者，第 4 节脚注 3）。核心直觉是"排除太远的向量"：与"最小化到所有向量距离之和"的重心式选择不同（该方案在 f ≥ 2 时会被两个拜占庭 worker 共谋攻破，第 4 节 Figure 3），Krum 只在最近邻范围内计算距离，因而远端向量拉不动得分。
4. **弹性证明（第 4 节命题 1）**：当 2f + 2 < n 且 η(n, f)·√d·σ < ||g|| 时，Krum 是 (α, f)-拜占庭弹性的，其中 sin α = η(n, f)·√d·σ/||g||，η(n, f) = sqrt( 2·( n − f + f·(n − f − 2) + f²·(n − f − 1) ) / ( n − 2f − 2 ) )；当 f = O(n) 时 η = O(n)，当 f = O(1) 时 η = O(√n)。证明的关键是：即便被选中的是拜占庭向量，它的得分也不会超过任何正确 worker 的得分，因此可以用正确 worker 之间的距离来上界它与真实梯度的距离（类似中位数只被正确值夹住的论证在高维的推广）。
5. **收敛分析（第 5 节命题 2）**：在成本函数三次可微且非负、学习率满足 Σγ_t = ∞ 与 Σγ_t² < ∞、梯度估计无偏且二至四阶矩有界、以及信噪比条件等假设下，∇Q(x_t) 几乎必然收敛到零。论文的解释是：参数向量几乎必然进入一个梯度很小的"盆地"，也就是 ||∇Q|| ≤ η(n, f)·√d·σ 的"almost flat"区域。
6. **m-Krum（第 6 节命题 3）**：为避免只选一个向量浪费其他正确 worker 的贡献，可以迭代地"选出一个、从列表中删掉、重复 m − 1 次"，对选出的 m 个向量取平均；条件是 2f + 2 < n − m。

**分析：论文内部有一处小的记号不一致**——第 4 节定义最近邻个数为 n − f − 2，而 Lemma 2 的复杂度证明里写的是"sums the first n − f − 1 values"。这不影响主结论，但在复现实现时需要明确取哪一个。

## 5. 检测或防御所需的数据

Krum 不是"先检测再处理"的方法，而是直接替换聚合规则，所以它需要的数据非常少，且全部在服务器侧。

| 输入 | 是什么 | 在哪里采集 | 粒度 | 跨轮历史 | 干净参考数据/根数据集 | 额外前向或反向计算 | 其他客户端的数据 |
|---|---|---|---|---|---|---|---|
| 本轮各 worker 的梯度估计/更新向量 V_i^t | d 维向量，即 worker 提议的更新方向（聚类或恶意向量都在其中） | 服务器收到更新时（server_receive） | 逐客户端 + 整体模型（论文把整个参数向量当成一个 d 维向量，不区分层或张量） | 不需要 | 不需要 | 不需要（服务器只做向量运算） | 需要，但只需要它们本轮提交的向量本身 |
| 缺失更新的补值 | 未收到向量的拜占庭 worker 被当作 0 向量参与计算 | 服务器收到更新时（server_receive） | 逐客户端 | 不需要 | 不需要 | 不需要 | 不适用 |
| 更新向量之间的成对距离平方 ||V_i − V_j||² 及每个客户端的得分 s(i) | Krum 的选择依据，距离在最近的 n − f − 2 个邻居之间求和 | 服务器聚合时（server_aggregate） | 逐客户端对/逐客户端 | 不需要 | 需要（O(n²·(d + log n)) 的服务器端计算，第 4 节 Lemma 2） | 需要（成对计算天然需要所有向量） |
| 本轮参与者数量 n 与拜占庭上界 f | 用于检查 2f + 2 < n（1-Krum）或 2f + 2 < n − m（m-Krum） | 服务器聚合时（server_aggregate） | 逐轮 | 不需要 | 不需要 | 不需要 | 不需要 |

**攻击留下的可观测量（论文报告）**：拜占庭向量表现为方向或幅度明显偏离正确 worker 聚集区的向量（第 2 节 Figure 1 与第 3 节），或者表现为缺失后补的 0 向量（第 2 节）。第 5 节还指出，在 ||∇Q|| 小于噪声尺度 η(n, f)·√d·σ 的区域，拜占庭 worker 可以借助梯度估计的噪声来偏置服务器的选择。

**论文声称能绕过哪些检测（论文报告）**：Lemma 1 说明单个拜占庭 worker 可以让**任何**线性组合（包括平均以及其变体）输出任意向量，从而绕过今天所有基于平均的聚合；第 1 节与第 3 节还说明，让拜占庭 worker 主导"最小化到所有向量距离之和"的选择需要两个共谋者即可做到（第 1 节与第 4 节 Figure 3）。论文没有讨论针对 Krum 本身的规避或检测方法，这一点**论文未说明**。

## 6. 干预动作

- **动作类型**：服务器聚合阶段的"选择并丢弃"。1-Krum 直接输出得分最小的那个 worker 的向量，等于把其余 n − 1 个向量在本轮权重置零；m-Krum 迭代选出 m 个向量后取平均，等于给这 m 个向量权重 1/m、其余权重 0。更新式始终是 x_{t+1} = x_t − γ_t · Kr(V_1^t, …, V_n^t)（第 2 节与第 5 节）。
- **不做的事**：不裁剪（clip）、不加噪、不过滤样本、不修复或回滚模型、不修改客户端本地训练、不向任何人报告。论文也没有说明服务器是否会记住或封禁被丢弃的客户端——按论文描述，被丢弃的 worker 在下一轮仍然参与，每轮重新打分；因此**分析：这更接近"每轮重加权（权重 0 或 1/m）"而不是永久剔除客户端**。
- **发生位置**：仅服务器侧（server），且只发生在每一轮的聚合步骤。

## 7. 实验设置与主要结果

**论文是纯理论论文，没有实验章节**：没有模型、没有数据集、没有客户端数、没有参与率、没有轮次、没有恶意比例、没有独立同分布或非独立同分布的设置、没有准确率或收敛曲线等指标。Figure 1 到 Figure 4 全部是几何示意图（正确向量围绕真实梯度、拜占庭向量任意、重心选择的失效、角度条件），不是实验结果。第 7 节只有相关工作比较和开放问题。

论文报告的结果都是引理、命题与复杂度陈述：

- **Lemma 1（第 3 节）**：任何 λ_i 非零的线性组合 F_lin 都不能容忍一个拜占庭 worker，该 worker 可迫使 F_lin 等于任意 U，因此可阻止收敛。
- **Lemma 2（第 4 节）**：Krum 的时间复杂度为 O(n²·(d + log n))。
- **Proposition 1（第 4 节）**：在 2f + 2 < n 且 η(n, f)·√d·σ < ||g|| 下，Krum 是 (α, f)-拜占庭弹性的，sin α = η(n, f)·√d·σ/||g||；η(n, f) 在 f = O(n) 时为 O(n)，在 f = O(1) 时为 O(√n)。
- **Proposition 2（第 5 节）**：在上述非凸收敛条件下，∇Q(x_t) 几乎必然收敛到零；实际含义是参数向量几乎必然到达 ||∇Q|| ≤ η(n, f)·√d·σ 的"几乎平坦"区域。
- **Proposition 3（第 6 节）**：在 2f + 2 < n − m 且 η(n, f)·√d·σ < ||g|| 下，m-Krum 对足够大的 n 也是 (α, f)-拜占庭弹性的，α 的定义与命题 1 相同。

## 8. 开销

- **计算开销**：论文报告 Krum 的服务器端本地计算复杂度为 O(n²·(d + log n))（摘要、第 4 节 Lemma 2、第 7 节）。Lemma 2 的证明分解为：对每个 V_i 计算 n 个距离需要 O(n·d)，排序需要 O(n·log n)，求和需要 O(n·d)，对所有 i 汇总即 O(n²·(d + log n))，再加 O(n) 找最小得分。第 7 节还说明 m-Krum 会把整体计算复杂度乘以 m，并指出相比近似一致性（approximate agreement）方法的 O(n·d) 本地计算，d 很大时这一项不可忽视（第 7 节）。
- **通信开销**：**论文未报告**（只有同步轮广播参数、回传向量的通用流程描述，没有量化）。
- **存储开销**：**论文未报告**。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文报告）**

1. 参数服务器可靠，其失效不在拜占庭模型内，可用状态机复制处理（第 2 节脚注 2）。
2. 计算按同步轮进行，每轮服务器广播同一个 x_t（第 2 节）；每个正确 worker 基于同一参数计算估计。
3. 正确 worker 的梯度估计是独立同分布且无偏的：V_i ~ G(x_t, ξ_i)，E G(x_t, ξ_i) = ∇Q(x_t)；这要求样本被均匀独立地抽取（第 2 节）。
4. 方差有界：E||G − g||² = dσ²（命题 1）；更高阶矩有界：∀r ∈ {2,…,4}，E||G(x, ξ)||^r ≤ A_r + B_r||x||^r（命题 2 条件 (iii)）。
5. 拜占庭数量满足 2f + 2 < n；m-Krum 还要求 2f + 2 < n − m（命题 1、命题 3）。
6. 信噪比条件 η(n, f)·√d·σ < ||g||；论文指出这可以通过让正确 worker 用 mini-batch 计算梯度估计来缓解，因为对 mini-batch 取平均会把偏差 σ 除以 batch 大小的平方根（第 4 节命题 1 之后的说明）。
7. 收敛分析额外要求成本函数三次可微、非负，学习率满足 Σγ_t = ∞ 与 Σγ_t² < ∞，并在 ||x||² ≥ D 的区域"足够凸"（梯度方向与参数向量方向的夹角余弦不小于 cos β）（第 5 节命题 2）。
8. 拜占庭向量的假设是**最强形式**：任意、可以互相依赖、可以依赖正确向量、可以任意大（第 2 节、命题 1）。

**论文自述的局限（第 7 节）**

- 界 2f + 2 < n 是否紧仍然开放；如何同时容忍异步与拜占庭 worker 也开放。
- η(n, f) = O(n) 这一因子能否变小仍然开放。
- m-Krum 通过迭代 m 次把整体计算复杂度乘以 m；"先算得分再直接取前 m 个"的替代方案，其 (α, f)-弹性尚未证明。
- 收敛只能保证到达 ||∇Q|| ≤ η(n, f)·√d·σ 的"几乎平坦"区域；在该区域内拜占庭 worker 可以利用噪声偏置服务器的选择（第 5 节）。第 7 节还把工作与 [20]（假设梯度有界且参数向量是一维）、[21]（只覆盖有限个环境状态）做了区分。

**自适应攻击者**

- **论文报告**：论文没有做任何实验性的自适应攻击评估；但它的威胁模型本身就是自适应的——拜占庭向量可以是"any random vectors, possibly dependent on the Vi's"（命题 1），并且拜占庭 worker 知道 F 和其他 worker 的向量（第 2 节）。论文在这一最强设定下证明了弹性条件，因此**分析：可以说它在分析层面覆盖了自适应攻击者，但没有评估任何具体的自适应攻击策略**。
- 论文也没有讨论攻击者在知道 Krum 之后如何构造更隐蔽的向量来规避它，这一点**论文未说明**。

**迁移到联邦大模型 LoRA 微调时可能失效的假设（分析）**

- **分析**：论文假设同步轮且每轮所有 worker 都提交更新，而联邦 LoRA 微调通常有客户端采样、部分参与、异步或掉队者（straggler）；在部分参与下，"n" 究竟是总客户端数还是本轮参与者数，论文未说明，而 2f + 2 < n 的分母会直接改变可行性。
- **分析**：论文假设各 worker 的梯度估计独立同分布且无偏，即数据同分布；联邦 LoRA 的客户端数据通常高度非独立同分布，这会让 σ 变大、||g||（全局梯度）的定义变得含糊，从而使 η(n, f)·√d·σ < ||g|| 这一条件更难满足。
- **分析**：论文把参数当成一个单一 d 维欧氏向量，没有分层、分张量或低秩结构的处理；LoRA 只上传低秩增量矩阵（A、B），其距离度量、是否分别计算、缩放因子如何纳入，论文完全没有涉及，直接照搬需要自行定义度量。
- **分析**：Krum 每轮只保留 1 个（或 m 个）客户端的向量，在客户端数量有限、数据异构、通信昂贵的联邦 LoRA 场景下会丢弃绝大多数客户端的贡献；论文没有讨论这对收敛速度与公平性的影响，只在 m-Krum 中承认"wasting the contribution of the other workers"。
- **分析**：论文假设服务器可靠；在"适配器或模型发布者"也可能不可信的供应链场景中，服务器端聚合逻辑本身可能被替换，此时 Krum 的保证失效，论文对此没有讨论。
- **分析**：论文完全针对"阻止收敛/任意偏置更新"这一类无目标破坏，没有覆盖后门、定向投毒或安全对齐破坏，因此从它迁移到防护库的检测能力时，只能覆盖聚合层的拜占庭破坏。

## 10. 对防护库设计的含义

- **分析**：库必须在"服务器收到更新时"提供固定钩子，采集本轮每个参与客户端的**完整更新向量**（逐客户端、整模型粒度）以及本轮参与集合，并显式记录缺失更新（论文把缺失当作 0 向量处理）。这是所有拜占庭鲁棒聚合共用的采集点，属于通用需求。
- **分析**：库需要在服务器聚合前提供"成对距离/相似度"这一数据视图（逐客户端对、逐轮，可排序、可求和），并允许插件只使用每个客户端与最近 n − f − 2 个邻居的距离之和；这是 Krum 特有的视图，但它不需要跨轮历史、不需要干净参考数据或根数据集、不需要逐样本损失或激活、也不需要额外的前向或反向计算，因此客户端侧不必新增采集点。
- **分析**：干预接口应支持"在本轮选择子集并聚合"这一语义，即返回被选中的客户端集合、给未选中者权重 0，同时保留 m-Krum 所需的"迭代选择、逐个移除、再平均"循环；把丢弃记录为逐轮事件而不是永久封禁，因为论文没有描述封禁逻辑。
- **分析**：库需要把拜占庭上界 f 和参与者数量 n 作为显式配置或估计值，并在 2f + 2 < n（或 m-Krum 的 2f + 2 < n − m）不成立时给出降级或告警，而不是静默套用公式。
- **分析**：由于 Krum 的代价是 O(n²·(d + log n)) 且 m-Krum 再乘 m，库应把距离计算做成可替换、可近似、可分块的后端，并允许把"参数向量"抽象成可配置的距离度量，以便在 LoRA 的低秩增量结构上定义距离；这部分是这篇论文特有的需求，通用性弱于前两条。
- **分析**：库的插件元数据应能声明自己的适用前提（同步轮、同分布、2f + 2 < n、信噪比条件），因为这些前提在联邦 LoRA 微调中往往不成立，需要由采集底座在运行期提供同步语义与参与集合来支撑判断。

## 11. 原文依据

1. **章节**：Abstract。**支撑**：第 1 节场景与第 2 节威胁模型（n 个 worker、至多 f 个拜占庭、不限制参数维度）。
   "Assuming a set of n workers, up to f of them being Byzantine, we ask how robust can SGD be, without limiting the dimension, nor the size of the parameter space."

2. **章节**：第 2 节 Model。**支撑**：第 1 节场景（参数服务器加 n 个 worker 的同步轮）与第 3 节的流程位置。
   "We consider a general distributed system consisting of a parameter server, and n workers, f of them possibly Byzantine (behaving arbitrarily). Computation is divided into (infinitely many) synchronous rounds."

3. **章节**：第 2 节 Model。**支撑**：第 2 节攻击者的知识与共谋能力。
   "The Byzantine workers have full knowledge of the system, including the choice function F, the vectors proposed by the other workers and can collaborate with each other."

4. **章节**：第 3 节 Lemma 1。**支撑**：第 3 节攻击入口与第 4 节核心思想（线性组合聚合无弹性）。
   "A single Byzantine worker can make F always select U. In particular, a single Byzantine worker can prevent convergence."

5. **章节**：第 1 节 Introduction（贡献段）。**支撑**：第 4 节说明朴素距离选择为何不够（两个拜占庭 worker 共谋）。
   "Yet, such a distance-based choice tolerates only a single Byzantine worker. Two Byzantine workers can collude, one helping the other to be selected, by moving the barycenter of all the vectors farther from the correct area."

6. **章节**：第 4 节（命题 1 之前）。**支撑**：第 4 节方法原理与第 9 节假设（2f + 2 < n 与信噪比条件）。
   "Proposition 1 below states that, if 2f + 2 < n and the gradient estimator is accurate enough, (its standard deviation is relatively small compared to the norm of the gradient), then the Krum function is (α, f)-Byzantine-resilient"

7. **章节**：第 4 节（命题 1 之后的说明）。**支撑**：第 5 节与第 9 节关于用 mini-batch 降低 σ 的说明。
   "The condition on the norm of the gradient, η(n, f) · √ d · σ < ∥g∥, can be satisfied, to a certain extent, by having the (correct) workers computing their gradient estimates on mini-batches"

8. **章节**：第 5 节 Convergence Analysis。**支撑**：第 7 节主要结果与第 9 节局限（只能收敛到几乎平坦的区域）。
   "in the presence of Byzantine workers, the parameter vector xt almost surely reaches a basin around points where the gradient is small"

9. **章节**：第 6 节 m-Krum。**支撑**：第 4 节方法与第 6 节干预动作（迭代选择 m 个向量并取平均）。
   "This can be achieved, for instance, by selecting one vector using the Krum function, removing it from the list, and iterating this scheme m −1 times, as long as n −m > 2f + 2."

10. **章节**：第 7 节 Concluding Remarks。**支撑**：第 9 节论文自述局限（界是否紧、异步与拜占庭并存问题开放）。
    "the question of whether the bound 2f + 2 < n is tight remains open, so is the question on how to tolerate both asynchrony and Byzantine workers."

```json
{
  "key": "blanchard2017krum",
  "title": "Byzantine-Tolerant Machine Learning",
  "year": 2017,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["local_training", "update_postprocess"],
  "observables": [
    {"what": "每个参与 worker 本轮提交的 d 维梯度估计/更新向量（论文把整个参数向量当作一个整体，不区分层）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "未发送更新的拜占庭 worker 被服务器按默认值 0 向量处理", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "更新向量之间的成对距离平方，以及每个客户端的 Krum 得分（到最近 n−f−2 个邻居的距离平方和）", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "本轮参与者数量 n 与拜占庭上界 f，用于检查 2f+2<n 或 2f+2<n−m", "where": "server_aggregate", "granularity": "round", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["exclude_client", "reweight"],
  "intervention_where": ["server"],
  "assumptions": [
    "参数服务器可靠，其失效由状态机复制处理，不在拜占庭模型内（第 2 节脚注 2）",
    "同步轮：每轮服务器广播同一参数 x_t，正确 worker 基于同一参数计算估计（第 2 节）",
    "正确 worker 的梯度估计独立同分布且无偏，E G(x_t, ξ_i) = ∇Q(x_t)（第 2 节）",
    "方差有界 E||G−g||² = dσ²，且二至四阶矩有界（命题 1 与命题 2 条件 (iii)）",
    "拜占庭数量满足 2f+2<n；m-Krum 还要求 2f+2<n−m（命题 1 与命题 3）",
    "信噪比条件 η(n,f)·√d·σ < ||g||，可用 mini-batch 降低 σ（第 4 节命题 1 之后）",
    "成本函数三次可微且非负，学习率满足 Σγ_t=∞ 与 Σγ_t²<∞，并在 ||x||²≥D 区域足够凸（命题 2）",
    "拜占庭 worker 知道选择函数 F 与其他 worker 的向量，可共谋并提交任意向量，包括依赖正确向量的向量（第 2 节与命题 1）"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节场景与第 2 节威胁模型：n 个 worker、至多 f 个拜占庭、不限制维度与参数规模", "text": "Assuming a set of n workers, up to f of them being Byzantine, we ask how robust can SGD be, without limiting the dimension, nor the size of the parameter space."},
    {"section": "Section 2 Model", "supports": "第 1 节场景与第 3 节流程位置：一台参数服务器加 n 个 worker 的同步轮", "text": "We consider a general distributed system consisting of a parameter server, and n workers, f of them possibly Byzantine (behaving arbitrarily). Computation is divided into (infinitely many) synchronous rounds."},
    {"section": "Section 2 Model", "supports": "第 2 节威胁模型：拜占庭 worker 的知识与共谋能力", "text": "The Byzantine workers have full knowledge of the system, including the choice function F, the vectors proposed by the other workers and can collaborate with each other."},
    {"section": "Section 3 Lemma 1", "supports": "第 3 节攻击入口与第 4 节核心思想：线性组合聚合连一个拜占庭 worker 都无法容忍", "text": "A single Byzantine worker can make F always select U. In particular, a single Byzantine worker can prevent convergence."},
    {"section": "Section 1 Introduction (Contributions)", "supports": "第 4 节方法原理：朴素的全局距离选择在 f≥2 时被共谋攻破，这是 Krum 的动机", "text": "Yet, such a distance-based choice tolerates only a single Byzantine worker. Two Byzantine workers can collude, one helping the other to be selected, by moving the barycenter of all the vectors farther from the correct area."},
    {"section": "Section 4 (before Proposition 1)", "supports": "第 4 节与第 9 节的关键假设：2f+2<n 与信噪比条件", "text": "Proposition 1 below states that, if 2f + 2 < n and the gradient estimator is accurate enough, (its standard deviation is relatively small compared to the norm of the gradient), then the Krum function is (α, f)-Byzantine-resilient"},
    {"section": "Section 4 (after Proposition 1)", "supports": "第 5 节与第 9 节：可用 mini-batch 降低梯度估计的标准差以满足信噪比条件", "text": "The condition on the norm of the gradient, η(n, f) · √ d · σ < ∥g∥, can be satisfied, to a certain extent, by having the (correct) workers computing their gradient estimates on mini-batches"},
    {"section": "Section 5 Convergence Analysis", "supports": "第 7 节主要结果与第 9 节局限：收敛只保证到梯度很小的盆地", "text": "in the presence of Byzantine workers, the parameter vector xt almost surely reaches a basin around points where the gradient is small"},
    {"section": "Section 6 m-Krum", "supports": "第 4 节方法与第 6 节干预动作：迭代选择 m 个向量并取平均及其条件", "text": "This can be achieved, for instance, by selecting one vector using the Krum function, removing it from the list, and iterating this scheme m −1 times, as long as n −m > 2f + 2."},
    {"section": "Section 7 Concluding Remarks", "supports": "第 9 节论文自述局限：界的紧性与异步加拜占庭问题仍未解决", "text": "the question of whether the bound 2f + 2 < n is tight remains open, so is the question on how to tolerate both asynchrony and Byzantine workers."}
  ]
}
```
