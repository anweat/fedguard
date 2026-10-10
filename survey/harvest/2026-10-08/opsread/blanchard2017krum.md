# blanchard2017krum：Krum 与 m-Krum（拜占庭容错聚合选择函数）

> 说明：本文是理论论文（§1–§7），没有实验、没有数据集、没有基线对比结果；它提出的方法只有 Krum（1-Krum）与 §6 的 m-Krum。文中对 averaging（平均）、线性组合、以及"最小化到所有向量平方距离之和"的距离型选择只做了理论反例分析（Lemma 1、§4、图 3），并未实现或评测。因此下面的流水线只拆 Krum 与 m-Krum，其余方法仅在必要处作为对照提及。

## 1. 方法一句话

Krum 是一个定义在参数服务器上的确定性选择函数（choice function）F：输入是 n 个 worker 各自提交的 d 维更新向量（正确 worker 给出梯度的无偏估计 V_p^t = G(x^t, ξ_p^t)，拜占庭 worker 可给出任意向量），输出是其中某一个被选中的向量 V_{i*}，并用它替换平均聚合进入 SGD 更新 x^{t+1} = x^t − γ_t·F（§2、§4）；m-Krum 则输出 m 个被选向量的算术平均（§6）。它不输出"谁是拜占庭"的身份判定，也不修改客户端本地训练。

## 2. 运行位置

- **服务器下发前（server_distribute）**：参数服务器持有并广播参数向量 x^t ∈ R^d。论文假设服务器本身可靠，并注明可用经典的状态机复制避免这一单点故障（§2 及脚注 2）。
- **客户端上传前 / 客户端每个训练步（client_post_train）**：每个正确 worker 计算梯度估计 V_p^t = G(x^t, ξ_p^t)，满足 E G(x^t, ξ_p^t) = ∇Q(x^t)（§2 Model）。防御本身不改动这一步；论文只在 §4 末尾建议用 mini-batch 平均把偏差 σ 除以批量大小的平方根，以便满足 η(n,f)·√d·σ < ‖g‖ 的条件。这是一个客户端侧的建议，不是服务器算子。
- **服务器收到更新（server_receive）**：服务器收齐 n 个向量；由于通信是同步的，若收不到某个拜占庭 worker b 的向量 V_b^t，服务器按默认值 V_b^t = 0 处理（§2）。
- **服务器聚合（server_aggregate）**：用 Krum 选择函数替换平均聚合，即计算两两平方距离、按 n−f−2 最近邻求分数、取最小分数者（§4）；m-Krum 时迭代 m 次并取平均（§6）。
- **聚合之后（server_post_aggregate）**：执行 SGD 更新 x^{t+1} = x^t − γ_t·F（§2、§5）。
- **额外往返**：不需要。所有计算都发生在既有的"广播参数 → worker 回传梯度"同步轮次内（§2）；论文从未要求额外通信轮。needs_round_trip = false。
- **训练之外**：论文未使用任何训练之外的阶段；没有离线参考数据、没有预训练检测器、没有实验流程。
- "分析："若把该方案套到联邦学习流程上，它是纯粹的**服务器聚合算子**：客户端行为与标准联邦 SGD 完全相同，唯一的服务端改动是"收到 n 个更新后不要取平均，而是取 Krum 选出的那一个（或 m 个的平均）"。

## 3. 算子流水线

以下按执行顺序列出。除第 2 步在客户端外，其余全部在服务器。

**步骤 1：服务器广播参数向量**
- 输入：服务器当前参数 x^t ∈ R^d。
- 计算：在第 t 个同步轮次中把 x^t 广播给全部 n 个 worker（§2 Model）。
- 输出：n 个 worker 各自持有同一份 x^t。
- 出处：§2："During round t, the parameter server broadcasts its parameter vector xt ∈ Rd to all the workers"。

**步骤 2：客户端计算随机梯度估计（非防御算子，标准 SGD 步骤）**
- 输入：x^t 与 worker p 本地采样的随机变量 ξ_p^t。
- 计算：V_p^t = G(x^t, ξ_p^t)，要求各正确 worker 的 V_p^t 独立同分布且 E G(x^t, ξ_p^t) = ∇Q(x^t)；论文说明这可通过"每个用于计算梯度的数据样本被均匀且独立地抽取"来保证（§2）。为把 σ 压小以满足收敛条件，论文建议在 mini-batch 上平均梯度估计（§4 末尾）。
- 输出：每个正确 worker 一个 d 维向量 V_p^t；拜占庭 worker 输出任意向量 V_b^t。
- 出处：§2 Model；§4 结尾关于 mini-batch 的说明。

**步骤 3：收齐 n 个更新，缺失向量按 0 填充**
- 输入：至多 n 个 d 维向量（部分可能未收到）。
- 计算：若服务器没有收到某个（拜占庭）worker 的 V_b^t，则令 V_b^t = 0，其余保持原值（§2）。
- 输出：n 个 d 维向量 V_1^t, …, V_n^t。
- 出处：§2 Model。

**步骤 4：计算两两平方欧氏距离**
- 输入：n 个 d 维向量 V_1, …, V_n（为简洁，以下省略轮次上标 t）。
- 计算：对每个 i 计算 n 个平方距离 ‖V_i − V_j‖^2（含 j = i 时的 0）。时间复杂度 O(n·d) 每行。
- 输出：n×n 的平方距离矩阵。
- 出处：§4 Lemma 2 证明："For each Vi, the parameter server computes the n squared distances ∥Vi −Vj∥2 (time O(n·d))"。

**步骤 5：每行排序并确定 n−f−2 个最近邻**
- 输入：第 i 行的 n 个平方距离。
- 计算：对该行排序（O(n·log n)），取距 V_i 最近的 n−f−2 个向量作为其邻居；记关系 i → j 表示 V_j 属于 V_i 的这 n−f−2 个最近邻（§4 定义）。注意 Lemma 2 的证明把这一步写成"sums the first n−f−1 values"，即把自身距离 0 也计入排序后的前 n−f−1 个位置，二者等价。
- 输出：每个 i 的邻居集合 {j : i → j}。
- 出处：§4 定义段；§4 Lemma 2 证明。

**步骤 6：按最近邻距离平方求和得到分数 s(i)**
- 输入：关系 i → j 及其平方距离。
- 计算：s(i) = Σ_{j : i→j} ‖V_i − V_j‖^2，求和只跑遍 V_i 的 n−f−2 个最近邻（§4）。
- 输出：n 个标量分数 s(1), …, s(n)。
- 出处：§4："we define for each worker i, the score s(i) = Σ_{i→j} ∥Vi −Vj∥2 where the sum runs over the n −f −2 closest vectors to Vi"。

**步骤 7：取最小分数者，并列时按标识符打破平局**
- 输入：n 个分数 s(i)。
- 计算：i* = argmin_i s(i)，即 s(i*) ≤ s(i) 对所有 i 成立；若两个或更多 worker 分数并列最小，选择标识符（identifier）最小的那个 worker 的向量（脚注 3）。论文未定义"标识符"的具体空间或排序方式。
- 输出：被选下标 i*。
- 出处：§4；脚注 3。

**步骤 8：输出被选向量（1-Krum 的聚合结果）**
- 输入：i* 与向量列表。
- 计算：Kr(V_1, …, V_n) = V_{i*}（§4）。
- 输出：F ∈ R^d。
- 出处：§4。

**步骤 9（仅 m-Krum）：迭代删除并重复选择 m 次，再取平均**
- 输入：当前剩余向量列表。
- 计算：用 Krum 选出一个向量后把它从列表中删除，重复该过程 m−1 次，前提是 n − m > 2f + 2；然后 Kr_m(V_1, …, V_n) = (1/m)·Σ_{s=1}^{m} V_{i_s^*}，其中 V_{i_s^*} 是第 s 次选出的向量。1-Krum 即 §4 的 Krum 函数。
- 输出：m 个被选向量的等权平均，仍是 d 维向量。
- 出处：§6 m-Krum 段与公式（未编号公式）。
- 论文另提到一种替代做法（先按 Krum 算一次分数，再直接取分数最小的前 m 个），但明确说其 (α, f)-拜占庭韧性"remains open"（§7），因此不能当作已验证算子实现。

**步骤 10：服务器执行 SGD 更新**
- 输入：x^t 与 F（或 Kr_m）。
- 计算：x^{t+1} = x^t − γ_t·F(V_1^t, …, V_n^t)（§2 的 SGD 公式；§5 用 Kr 替换 F）。
- 输出：新一轮参数 x^{t+1}。
- 出处：§2；§5 第一式。

## 4. 采样与规模控制

- **客户端/向量层面有截断，但不是随机抽样**：Krum 对每个候选向量只考虑它的 n−f−2 个最近邻来计算分数（§4）；m-Krum 每轮只保留 m 个被选向量（§6）。两者都要求客户端规模满足约束：Krum 要求 2f + 2 < n（§4 Proposition 1），m-Krum 要求 n − m > 2f + 2（§6 Proposition 3）。
- **参数坐标/层：论文未使用**任何抽样、分块或降维。论文明确说方法"without limiting the dimension, nor the size of the parameter space"（Abstract），复杂度对 d 只是线性（§4 Lemma 2），§7 还强调 d 可能高达 1600 亿（引用 [22]）。
- **轮次：论文未使用**轮次抽样；计算被分成"inﬁnitely many"个同步轮次（§2）。
- **参考数据/探针：论文未使用。** Krum 不依赖任何干净参考数据、根数据集或探针样本，只用当轮收到的 n 个向量。
- **样本（mini-batch）**：论文只在 §4 末尾提到可用 mini-batch 平均梯度估计、把偏差 σ 除以批量大小的平方根，但**未给出任何批量取值**，也没有实验。
- 结论：除"每行取 n−f−2 个最近邻"和"m-Krum 取 m 个"这两处规模截断外，方法在样本、客户端、坐标、轮次维度上都没有抽样设计。

## 5. 超参数

| 名称 | 含义 | 论文取值/约束 | 出处 |
|---|---|---|---|
| n | worker 总数 | 系统给定；需 2f + 2 < n | §2 Model；§4 Prop 1 |
| f | 拜占庭 worker 数的上界 | 需 2f + 2 < n；m-Krum 需 n − m > 2f + 2 | §2；§4 Prop 1；§6 Prop 3 |
| m | m-Krum 每轮选择的向量个数 | 需 n − m > 2f + 2；m = 1 时退化为 Krum | §6 |
| γ_t | 学习率 | 需 Σ_t γ_t = ∞ 且 Σ_t γ_t^2 < ∞；**具体调度论文未说明** | §5 Prop 2 条件 (ii) |
| η(n, f) | 由 n、f 计算出的常数（非自由超参）：η(n,f) = √( 2·( n − f + f·(n − f − 2) + f²·(n − f − 1) ) / (n − 2f − 2) ) | 由公式给出；f = O(n) 时为 O(n)，f = O(1) 时为 O(√n) | §4 Prop 1 |
| α | 允许的角度偏差，sin α = η(n,f)·√d·σ / ‖g‖ | 0 ≤ α < π/2，需 η(n,f)·√d·σ < ‖g‖ | §3 Def 1；§4 Prop 1 |
| σ | 梯度估计的局部标准差，定义为 d·σ²(x) = E‖G(x,ξ) − ∇Q(x)‖² | 由数据与模型决定；论文建议用 mini-batch 减小 | §5（定义式）；§4 末 |
| d | 参数维度 | 不设限制，可极大（§7 引用 [22] 的 160 billion） | §1；§4 Lemma 2；§7 |
| 距离度量 | 邻居与分数用的距离 | 固定为平方欧氏距离，不是可调超参 | §4 |
| mini-batch 大小 | 客户端平均梯度估计以降低 σ | **论文未说明**具体取值，只说 σ 按批量大小的平方根缩小 | §4 末 |
| D, ε, β | 收敛分析中的常数（超出半径 D 后梯度范数 ≥ ε、方向满足 cos β） | 分析假设，非算法参数 | §5 Prop 2 条件 (v) |

## 6. 判定与动作

- **没有阈值型检测器**：Krum 不输出"某 worker 是拜占庭"的判定，也不估计拜占庭比例；它把选择规则本身当作防御。论文强调的是选择函数 F 的统计性质，而不是逐客户端甄别。
- **选择规则（动作的直接来源）**：对每个 i 用它的 n−f−2 个最近邻的平方距离之和作为分数，取分数最小者；并列时取标识符最小者（§4 与脚注 3）。这等价于"在所有候选里选一个与自己最近邻最贴近的向量"，被选向量直接作为本轮聚合结果。
- **加权方式**：1-Krum 是硬选择（等价于被选客户端权重 1、其余客户端权重 0，即隐式的逐轮剔除）；m-Krum 对 m 个被选向量等权平均，权重各为 1/m（§6）。论文没有给出任何连续加权或按分数加权的公式。
- **裁剪与加噪**：论文未使用。Krum 不裁剪被选向量的范数，也不加噪声。
- **跨轮累积**：论文未使用。每一轮独立地在当轮 n 个向量上做选择，没有跨轮的记忆、信誉或计数。
- **保证成立的条件（不是运行时阈值，而是理论前提）**：(a) 2f + 2 < n（m-Krum：n − m > 2f + 2）；(b) η(n,f)·√d·σ < ‖g‖，此时 sin α = η(n,f)·√d·σ/‖g‖，且 ⟨E Kr, g⟩ ≥ (1 − sin α)·‖g‖² > 0（§4 Prop 1；§3 Def 1 条件 (i)）。在 ‖∇Q(x)‖ < η(n,f)·√d·σ 的"平坦"区域，拜占庭 worker 可以利用梯度估计的噪声影响选择，收敛分析只能保证参数几乎必然到达梯度范数不超过 η(n,f)·√d·σ 的区域（§5 Prop 2 及其解释）。

## 7. 需要的外部资源

- **干净参考数据 / 根数据集 / 探针样本**：论文未使用，Krum 只用当轮收到的 n 个更新向量。
- **预训练检测器 / 辅助模型 / 对齐前后的权重**：论文未使用。
- **系统侧需要知道的信息**：worker 总数 n、拜占庭上界 f（用于确定邻居数 n−f−2 和校验 2f+2 < n）；m-Krum 还需要 m（§4、§6）。论文未说明服务器如何获得 f，也未讨论真实拜占庭数超过 f 时的行为。
- **运行假设**：同步通信轮次；每个正确 worker 能提供 ∇Q 的无偏估计且前四阶矩有界（§2、§3 Def 1、§5 Prop 2 条件 (iii)）；参数服务器本身可靠（§2 脚注 2）；拜占庭 worker 拥有系统全部知识、可以看到其他 worker 的向量并互相串谋（§2）。
- **客户端侧数据**：仅用于常规的随机梯度估计（§2）以及可选的 mini-batch 平均（§4），不是防御专用的参考集。

## 8. 计算与存储开销

- 论文报告的开销：Krum 的本地计算时间为 **O(n²·(d + log n))**（Abstract；§4 Lemma 2）。Lemma 2 的分解是：对每个 V_i 计算 n 个平方距离需 O(n·d)，排序需 O(n·log n)，再对 O(n) 个值求和；对全部 n 个 V_i 总计 O(n²·(d + log n))，最后找最小分数只需额外的 O(n)，可忽略（§4 Lemma 2 证明）。
- m-Krum：论文明确说它把 1-Krum 迭代 m 次，"multiplying by m the overall computation complexity"（§7），即约 m 倍于 Krum 的开销。
- 论文对照：§7 指出 [13] 需要每个 worker O(nd) 的本地计算，并强调在 d 可达 1600 亿的机器学习场景中复杂度必须考虑 d。
- **分析：**主要开销来自服务器端的步骤 4–6：计算 n² 个 d 维平方距离并逐行排序。它随 n²（客户端数的平方）和 d（参数维度）增长，与一轮内每个客户端一次梯度计算无关；m-Krum 线性放大 m 倍。通信开销与标准分布式 SGD 相同（每 worker 每轮一个 d 维向量），没有额外往返。
- **分析：**存储方面论文未报告。朴素实现需要保存 n 个 d 维向量（O(n·d)）以及可选的 n×n 距离/邻居结构（O(n²)）；若只在每行内做 top-k 选择而不物化完整排序，可以避免 O(n²) 的额外结构，但论文没有给出任何存储方案或数字。

## 9. 实现时容易错的地方

论文明确强调或界定的：

1. **邻居数是 n−f−2，而 Lemma 2 的证明写的是"前 n−f−1 个值"**。二者只有在把自身距离 0 也算进排序时才一致（排序后第一个是 0，前 n−f−1 个即自身 + n−f−2 个最近邻）。实现时必须明确这一约定，否则邻居数会差一个。
2. **并列分数的打破规则**：论文脚注 3 规定"若两个或更多 worker 分数最小，选择标识符最小的 worker 的向量"。论文没有定义标识符的取值范围与比较方式（数字 ID？字符串？），实现必须自己决定。
3. **未收到的向量按 0 处理**（§2），而不是丢弃该 worker 或该轮作废。这意味着 0 向量会参与距离计算和邻居关系，也会占一个候选位置。
4. **必须校验 2f + 2 < n**（§4 Prop 1）；m-Krum 必须校验 n − m > 2f + 2（§6 Prop 3）。论文没有给出违反该条件时的降级行为。
5. **算法从不识别拜占庭 worker**；它只做一次选择。因此不应把"被选中的客户端"当作可信客户端、也不应把"未被选中的客户端"当作已确认的拜占庭（跨轮累积封禁）。m-Krum 中被删除的向量只是本轮不再参与，论文没有说它们应被永久排除。
6. **保证只对满足 η(n,f)·√d·σ < ‖∇Q‖ 的区域给出**（§4 Prop 1、§5 Prop 2）；在梯度小的区域拜占庭方可以利用噪声影响选择（§5）。实现若要用这个条件做监控，需要自己决定如何估计 σ、‖∇Q‖ 以及如何处理不满足的轮次。
7. **不裁剪、不加噪**：Krum 输出的是某个 worker 提交的原始向量，其范数可能很大；论文的韧性保证约束的是期望方向（条件 (i)）与 2–4 阶矩（条件 (ii)），不是逐轮范数上界。实现不要自行加 clip 并声称等价于 Krum。
8. **m-Krum 的两种取舍不要混淆**：论文验证的是"选一个、删一个、重复 m 次再平均"；§7 明确说"先算一次分数再取前 m 名"这一更省算的替代方案其 (α, f) 韧性仍是未证明的开放问题。
9. **d 极大时的数值实现**：距离是 d 维平方欧氏距离，直接对 n² 对向量算距离是 O(n²d)；论文没有讨论任何浮点误差、下溢或分布式分块计算的处理。
10. **同步假设**：论文只在同步轮次下定义方法；异步、掉队者、服务器自身故障（除脚注 2 提及状态机复制）都不在论文范围内。

论文没说清、实现必须自己决定的：

11. **f 从何而来**、若真实拜占庭数超过 f 会怎样、f 是否可由服务器在线估计——论文均未说明。
12. **学习率调度 γ_t 的具体形式**：只给了 Σγ_t = ∞ 与 Σγ_t² < ∞ 两个条件（§5 Prop 2 (ii)），没有给出任何具体序列（如 γ_t = c/t）。
13. **mini-batch 大小的具体取值**：论文只给出 σ 随批量大小平方根下降的定性结论（§4）。
14. **停止条件与轮数**：§2 假设无限轮次，§5 只证明 ∇Q(x^t) 几乎必然趋于 0，没有给出可操作的停机准则。
15. **距离并列时如何选邻居**（选 i→j 时若第 n−f−2 与第 n−f−3 个距离相等）论文未说明。
16. **论文完全没有实验**：没有数据集、没有模型、没有 n/f/m/学习率/批量的经验取值，也没有任何精度或时间实测，因此所有"实际有效"的参数都需要使用者自行验证。

## 10. 原文依据

1. **支撑步骤 1（服务器侧的确定性选择函数与聚合）**
> "The parameter server computes a vector F(V t 1 , . . . , V t n) by applying a deterministic function F to the vectors received. We refer to F as the choice function of the parameter server."

2. **支撑步骤 3（未收到的向量按默认值 0 处理）**
> "Note that, since the communication is synchronous, if the parameter server does not receive a vector value V t b from a given Byzantine worker b, then the parameter server acts as if it had received the default value V t b = 0 instead."

3. **支撑步骤 5（i → j 表示 V_j 属于 V_i 的 n−f−2 个最近邻）**
> "For any i ̸= j, we denote by i →j the fact that Vj belongs to the n −f −2 closest vectors to Vi."

4. **支撑步骤 6（分数是最近邻平方距离之和）**
> "Then, we define for each worker i, the score s(i) = P i→j ∥Vi −Vj∥2 where the sum runs over the n −f −2 closest vectors to Vi."

5. **支撑步骤 7（取最小分数者作为被选下标）**
> "Finally, Kr(V1, . . . , Vn) = Vi∗ where i∗ refers to the worker minimizing the score, s(i∗) ≤s(i) for all i."

6. **支撑步骤 7 的并列处理**
> "If two or more workers have the minimal score, we choose the vector of the worker with the smallest identifier."

7. **支撑步骤 4–5 的实现与复杂度（计算 n 个平方距离、排序、取前 n−f−1 个值）**
> "For each Vi, the parameter server computes the n squared distances ∥Vi −Vj∥2 (time O(n·d)). Then the parameter server sorts these distances (time O(n·log n)) and sums the first n−f −1 values (time O(n·d))."

8. **支撑步骤 9（m-Krum 的迭代删除与重复选择）**
> "This can be achieved, for instance, by selecting one vector using the Krum function, removing it from the list, and iterating this scheme m −1 times, as long as n −m > 2f + 2."

```json
{
  "key": "blanchard2017krum",
  "method": "Krum (1-Krum) and m-Krum Byzantine-resilient choice function",
  "stages": ["server_distribute", "client_post_train", "server_receive", "server_aggregate", "server_post_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "服务器广播参数向量",
      "operator": "broadcast_parameters",
      "input": "服务器当前参数 x^t，d 维向量",
      "output": "n 个 worker 各自收到同一份 x^t",
      "params": {},
      "source": "§2 Model：同步轮次中服务器把 xt ∈ Rd 广播给所有 worker"
    },
    {
      "step": "客户端计算随机梯度估计（标准 SGD，非防御算子）",
      "operator": "unbiased_gradient_estimate",
      "input": "x^t 与客户端本地采样 ξ_p^t",
      "output": "每个正确客户端一个 d 维向量 V_p^t = G(x^t, ξ_p^t)",
      "params": {"unbiasedness": "E G(x^t, ξ_p^t) = ∇Q(x^t)（§2）", "mini_batch_size": "论文未说明（§4 仅建议用 mini-batch 把 σ 除以批量大小的平方根）"},
      "source": "§2 Model；§4 末段 mini-batch 说明"
    },
    {
      "step": "收齐 n 个更新，缺失向量按 0 填充",
      "operator": "zero_fill_missing_updates",
      "input": "至多 n 个 d 维向量（部分可能未收到）",
      "output": "n 个 d 维向量 V_1^t..V_n^t，未收到者置 0",
      "params": {"default_value": "0"},
      "source": "§2 Model"
    },
    {
      "step": "计算两两平方欧氏距离",
      "operator": "pairwise_squared_distance",
      "input": "n 个 d 维向量 V_1..V_n",
      "output": "n×n 平方距离，元素为 ||V_i − V_j||^2",
      "params": {"metric": "平方欧氏距离（固定，非可调超参）"},
      "source": "§4 Lemma 2 证明：对每个 Vi 计算 n 个平方距离，时间 O(n·d)"
    },
    {
      "step": "每行排序并选取 n−f−2 个最近邻",
      "operator": "knn_neighbor_selection",
      "input": "第 i 行的 n 个平方距离",
      "output": "邻居关系 i→j（V_j 属于 V_i 的 n−f−2 个最近邻）",
      "params": {"k": "n−f−2", "sort_cost": "O(n·log n)", "distance_tie_break": "论文未说明"},
      "source": "§4 定义段（i → j）；§4 Lemma 2 证明（排序后取前 n−f−1 个值，含自身 0 距离）"
    },
    {
      "step": "按最近邻平方距离求和得到分数",
      "operator": "sum_topk_squared_distances",
      "input": "邻居关系 i→j 及对应平方距离",
      "output": "n 个标量分数 s(1)..s(n)",
      "params": {},
      "source": "§4：s(i) = Σ_{i→j} ||Vi − Vj||^2，求和只跑 n−f−2 个最近邻"
    },
    {
      "step": "取最小分数者（并列取标识符最小者）",
      "operator": "argmin_score_tie_break_id",
      "input": "n 个分数 s(i)",
      "output": "被选下标 i*",
      "params": {"rule": "s(i*) ≤ s(i) 对所有 i", "tie_break": "worker 标识符最小者"},
      "source": "§4；脚注 3"
    },
    {
      "step": "输出被选向量作为聚合结果",
      "operator": "select_single_update",
      "input": "下标 i* 与向量列表 V_1..V_n",
      "output": "F = V_{i*} ∈ R^d",
      "params": {},
      "source": "§4：Kr(V1,...,Vn) = Vi∗"
    },
    {
      "step": "（仅 m-Krum）删除已选向量、重复选择 m 次并取平均",
      "operator": "iterative_topk_mean",
      "input": "当前剩余向量列表",
      "output": "Kr_m = (1/m)·Σ_{s=1..m} V_{i_s^*}",
      "params": {"m": "需 n − m > 2f + 2；m = 1 即 Krum", "alternative": "先算一次分数取前 m 名的做法论文未证明其 (α,f) 韧性（§7）"},
      "source": "§6 m-Krum"
    },
    {
      "step": "服务器执行 SGD 更新",
      "operator": "sgd_step",
      "input": "x^t 与聚合结果 F",
      "output": "x^{t+1} = x^t − γ_t·F",
      "params": {"learning_rate": "γ_t，需 Σγ_t = ∞ 且 Σγ_t^2 < ∞；具体调度论文未说明（§5 Prop 2 (ii)）"},
      "source": "§2 SGD 方程；§5 第一式"
    }
  ],
  "sampling": [
    {"what": "clients", "how": "每个候选向量只与其 n−f−2 个最近邻比较并求和，其余向量不进入该向量的分数（i→j 关系，非随机抽样）", "size": "n−f−2 个邻居；约束 2f+2 < n（§4 Prop 1）"},
    {"what": "clients", "how": "m-Krum 每轮只保留 m 个被选向量并等权平均，其余向量被删除", "size": "m 个；约束 n−m > 2f+2（§6 Prop 3）"},
    {"what": "coordinates", "how": "论文未使用任何坐标抽样或降维；距离在整个 d 维参数向量上计算", "size": "全部 d 维（Abstract；§4 Lemma 2；§7 提到 d 可达 160 billion）"},
    {"what": "samples", "how": "客户端可选地对 mini-batch 平均梯度估计以降低 σ（论文建议，非服务器算子）", "size": "论文未说明具体批量大小（§4 末段）"},
    {"what": "rounds", "how": "论文未使用轮次抽样；计算分为无限多个同步轮次", "size": "无限轮次/直到梯度趋于零（§2；§5 Prop 2）"},
    {"what": "probes", "how": "论文未使用探针样本或参考数据", "size": "无"}
  ],
  "resources": [
    "无需干净参考数据、根数据集、探针样本或预训练检测器（论文未使用）",
    "需要已知 worker 总数 n 与拜占庭上界 f（用于 n−f−2 邻居数与 2f+2 < n 校验）；m-Krum 还需 m（§4、§6）",
    "需要同步通信轮次，且参数服务器本身可靠（§2；脚注 2 提到可用状态机复制）",
    "需要每个正确 worker 提供 ∇Q 的无偏梯度估计且前四阶矩有界（§2；§3 Def 1；§5 Prop 2 条件 (iii)）",
    "客户端本地训练数据仅用于常规随机梯度估计与可选 mini-batch 平均（§2；§4）"
  ],
  "actions": ["exclude_client"],
  "dominant_cost": "服务器端每轮 O(n^2·(d+log n)) 的两两平方距离计算与逐行排序（Abstract；§4 Lemma 2）；m-Krum 把整体计算复杂度再乘以 m（§7）；通信量与标准分布式 SGD 相同，每 worker 每轮一个 d 维向量，无额外往返：分析：",
  "underspecified": [
    "邻居数在定义中为 n−f−2，而 Lemma 2 证明写为『前 n−f−1 个值』，需靠把自身 0 距离计入排序来统一（§4）",
    "距离并列时如何选取第 n−f−2 个邻居，论文未说明",
    "分数并列时的『最小标识符』未定义标识符空间与比较方式（脚注 3）",
    "服务器如何获知拜占庭上界 f、真实拜占庭数超过 f 时的行为，论文未说明",
    "违反 2f+2 < n（或 n−m > 2f+2）时的降级行为，论文未说明",
    "学习率 γ_t 的具体调度未给出，只给 Σγ_t = ∞ 与 Σγ_t^2 < ∞（§5 Prop 2 (ii)）",
    "mini-batch 的具体大小未给出，只说 σ 按批量大小的平方根缩小（§4）",
    "停止条件与总轮数未给出（§2 假设无限轮次，§5 只证明 ∇Q(x^t) → 0 a.s.）",
    "论文未报告任何存储开销与距离矩阵/邻居结构的实现方案",
    "d 极大时的数值稳定性（浮点误差、下溢）与分布式分块计算未讨论",
    "论文没有实验：无数据集、无模型、无 n/f/m/学习率/批量的经验取值，也无精度或时间实测",
    "m-Krum 的省算替代方案（只算一次分数取前 m 名）的 (α,f) 韧性未证明（§7，列为 open problem）"
  ],
  "quotes": [
    {"supports": "步骤 1：服务器侧确定性选择函数 F 的定义（聚合位置）", "text": "The parameter server computes a vector F(V t 1 , . . . , V t n) by applying a deterministic function F to the vectors received. We refer to F as the choice function of the parameter server."},
    {"supports": "步骤 3：未收到的向量按默认值 0 填充", "text": "Note that, since the communication is synchronous, if the parameter server does not receive a vector value V t b from a given Byzantine worker b, then the parameter server acts as if it had received the default value V t b = 0 instead."},
    {"supports": "步骤 5：i → j 表示 V_j 属于 V_i 的 n−f−2 个最近邻", "text": "For any i ̸= j, we denote by i →j the fact that Vj belongs to the n −f −2 closest vectors to Vi."},
    {"supports": "步骤 6：分数为最近邻平方距离之和", "text": "Then, we define for each worker i, the score s(i) = P i→j ∥Vi −Vj∥2 where the sum runs over the n −f −2 closest vectors to Vi."},
    {"supports": "步骤 7：取最小分数者的下标 i*", "text": "Finally, Kr(V1, . . . , Vn) = Vi∗ where i∗ refers to the worker minimizing the score, s(i∗) ≤s(i) for all i."},
    {"supports": "步骤 7 的并列处理：取标识符最小的 worker", "text": "If two or more workers have the minimal score, we choose the vector of the worker with the smallest identifier."},
    {"supports": "步骤 4–5：计算 n 个平方距离、排序并取前 n−f−1 个值（复杂度分解）", "text": "For each Vi, the parameter server computes the n squared distances ∥Vi −Vj∥2 (time O(n·d)). Then the parameter server sorts these distances (time O(n·log n)) and sums the first n−f −1 values (time O(n·d))."},
    {"supports": "步骤 9：m-Krum 的迭代删除与重复选择", "text": "This can be achieved, for instance, by selecting one vector using the Krum function, removing it from the list, and iterating this scheme m −1 times, as long as n −m > 2f + 2."}
  ]
}
```
