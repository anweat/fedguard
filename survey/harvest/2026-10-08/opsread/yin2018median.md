# yin2018median：坐标中位数聚合的拜占庭鲁棒分布式学习（median-based robust distributed gradient descent 与 median-based robust one-round algorithm）

## 1. 方法一句话

输入是 m 个 worker（工作机）每轮上传的 d 维向量——正常 worker 上传本地经验风险函数的梯度 ∇F_i(w^t)（或一次性变体中的本地 ERM 解 ŵ_i），拜占庭（Byzantine）worker 可以上传任意向量；输出不是"哪个客户端有问题"的判定，而是一个被逐坐标中位数（coordinate-wise median）汇总后的聚合方向 g(w^t)，服务器用它做一步投影梯度下降 w^{t+1} = Π_W(w^t − η g(w^t))，从而把至多 α 比例的任意/合谋消息对模型的影响限制在可证明的范围内（Algorithm 1 Option I，Section 4；一次性变体见 Algorithm 2，Section 5）。

## 2. 运行位置

- 服务器下发（server_distribute）：master（主节点）把当前参数 w^t 广播给全部 m 个 worker，包括拜占庭 worker（Algorithm 1 第 1 行 "Master machine: send wt to all the worker machines"）。
- 客户端每个训练步 / 客户端上传前（client_step）：每个正常 worker 计算本地经验梯度 g_i(w^t) = ∇F_i(w^t)，理论上是对本地全部 n 条数据求的全批量梯度（Algorithm 1 "Worker machine i: compute local gradient"；Section 3 定义 F_i(w) := (1/n)Σ_j f(w; z_{i,j})）。CNN 实验改用随机版本，每次迭代只用 10% 本地数据（Section 7）。
- 客户端上传：worker 把 g_i(w^t) ∈ R^d 发回 master；拜占庭 worker 不受协议约束，可发任意 ∗。
- 服务器收到更新 + 服务器聚合（server_receive / server_aggregate）：master 收集 m 个向量后，逐坐标取中位数得到 g(w^t)，紧接着在同一步里执行投影梯度更新 w^{t+1} = Π_W(w^t − η g(w^t))（Algorithm 1 最后一行）。
- 聚合之后（server_post_aggregate）：w^{t+1} 直接作为下一轮的全局模型被广播，没有额外的检测、过滤或审计阶段。
- 训练之外（outside_training）：本方法不需要预训练检测器或事后审计。仅在一次性变体（Algorithm 2）中，客户端要先在本地把 ERM 解到收敛，然后才发生整个流程里唯一一次上传，可记为客户端训练阶段（client_pre_train）。
- 额外往返：不需要。每轮只有"一次广播 + 一次上传"，与普通分布式梯度下降完全相同的通信模式；一次性变体总共只通信 1 轮（Abstract、Section 5）。

## 3. 算子流水线

### 流水线 A：median-based robust distributed gradient descent（Algorithm 1, Option I，主方法）

**A1. 广播当前全局模型**
- 输入：服务器当前参数 w^t ∈ R^d，t = 0, 1, …, T−1。
- 计算：把同一份 w^t 发送给全部 m 个 worker（不做任何客户端抽样、不区分正常/拜占庭）。
- 输出：m 份相同的 w^t。
- 论文出处：Algorithm 1 第 1 行 "Master machine: send wt to all the worker machines"；Section 4 第 1 段。

**A2. 计算本地经验梯度（正常 worker）**
- 输入：worker i 的本地数据 {z_{i,j}}_{j=1..n} 与收到的 w^t。
- 计算：g_i(w^t) = ∇F_i(w^t) = (1/n) Σ_{j=1}^n ∇f(w^t; z_{i,j})，即本地经验风险的全批量梯度（论文的理论设定是每个 worker 有 n 条独立同分布样本，Section 3）。拜占庭 worker 这一步的输出是任意向量 ∗，不遵守该计算。
- 输出：g_i(w^t) ∈ R^d。
- 论文出处：Algorithm 1 "Worker machine i: compute local gradient gi(wt) ← ∇Fi(wt) / ∗"；Section 3 对 F_i 的定义；Section 7（CNN 用 10% 本地数据的随机版本）。

**A3. 收集原始更新（不做过滤）**
- 输入：m 个上传向量，其中正常的是梯度、拜占庭的是任意消息。
- 计算：master 原样收集，不剔除、不加权、不裁剪、不加噪，只把它们排成 m×d 的矩阵 G = [g_1(w^t); …; g_m(w^t)]。
- 输出：G ∈ R^{m×d}。
- 论文出处：Algorithm 1 第 3–6 行；Section 3 "The Byzantine machines need not obey this protocol and can send arbitrary messages to the master"。

**A4. 逐坐标取中位数（核心算子）**
- 输入：G ∈ R^{m×d}。
- 计算：对每一个坐标 k ∈ [d] 独立地取一维中位数，g_k(w^t) = med{g_i^k(w^t) : i ∈ [m]}；各坐标之间互不影响。注意这不是几何中位数（ geometric median），而是 Definition 1 的坐标式中位数。
- 输出：聚合梯度 g(w^t) ∈ R^d。
- 论文出处：Definition 1；Algorithm 1 中 "g(wt) ← med{gi(wt) : i ∈ [m]} Option I"；Appendix B（Theorem 8、式 (26)）给出该算子与真实总体梯度 ∇F(w) 的偏差界。

**A5. 投影梯度更新**
- 输入：w^t、g(w^t)、步长 η。
- 计算：w^{t+1} = Π_W(w^t − η g(w^t))，其中 Π_W(·) 是到参数空间 W 的欧氏投影；定理里取 η = 1/L_F。W 被假设为凸紧集、直径 D（Section 3）。
- 输出：w^{t+1} ∈ W。
- 论文出处：Algorithm 1 最后一行 "update model parameter wt+1 ←ΠW(wt −ηg(wt))"；Theorems 1–6 均取 η = 1/L_F；Appendix B 的迭代式 (31)。

**A6. 重复 T 轮并输出**
- 输入：w^0、T、每轮的 g(w^t)。
- 计算：循环 A1–A5。强凸情形 T ≥ ((L_F+λ_F)/λ_F)·log((λ_F/(2Δ))·‖w^0−w*‖_2)，此时以高概率有 ‖ŵ−w*‖_2 ≤ (4/λ_F)Δ（Theorem 1 之后的文字）；凸但非强凸情形 T = L_F·‖w^0−w*‖_2/Δ（Theorem 2）；非凸情形 T = (2L_F/Δ²)·(F(w^0)−F(w*))（Theorem 3）。Δ 见式 (3)。
- 输出：最终模型 w^T，误差界为 Theorem 1/2/3。
- 论文出处：Section 4.1 Theorem 1–3 及其后的推导；Δ 见式 (3)。

**（可选变体，替换 A4）逐坐标截尾均值**：g_k = 1/((1−2β)m) Σ_{x∈U_k} x，其中 U_k 由去掉最大与最小各 β 比例的坐标值得到，β ∈ [0, 1/2)（Definition 2，Algorithm 1 Option II）。它与 A4 二选一，其余步骤完全相同；要求 β ≥ α，论文建议取 β = cα（c ≥ 1）（Section 4.2、Section 4.3），实验用 β = 0.05（Table 2）与 β = 0.1（Table 3）。

### 流水线 B：median-based robust one-round algorithm（Algorithm 2，一次性变体）

**B1. 本地求解 ERM**
- 输入：worker i 的本地数据与参数空间 W。
- 计算：正常 worker 解 ŵ_i ← arg min_{w∈W} F_i(w)；拜占庭 worker 发任意 ∗。这一步在客户端本地完成，理论分析要求损失是二次损失且 W = R^d，并要求每个正常机器的 F_i 以概率 1 强凸（Assumption 7）。
- 输出：ŵ_i ∈ R^d。
- 论文出处：Algorithm 2 第 1–4 行；Section 5；Assumption 7；Theorem 7。

**B2. 对本地解逐坐标取中位数**
- 输入：m 个 ŵ_i ∈ R^d。
- 计算：ŵ = med{ŵ_i : i ∈ [m]}，与 Definition 1 相同的逐坐标操作。
- 输出：最终模型 ŵ（只通信 1 轮）。
- 论文出处：Algorithm 2 最后一行 "Master machine: compute bw ←med{bwi : i ∈ [m]}"；Section 5 "we employ the coordinate-wise median operation to aggregate all the ERMs"；Theorem 7。

## 4. 采样与规模控制

- 样本（samples）：GD 的理论设定中每个 worker 每轮对本地全部 n 条数据计算梯度，没有对样本做抽样。唯一例外是 CNN 实验使用随机版本，每次迭代每个 worker 只用本地数据的 10%（Section 7："in every iteration, each worker machine computes the gradient using 10% of its local data"）。实验总数据是 MNIST 的 60,000 条训练样本，被随机均分给 m 个 worker（Section 7）；论文没有直接写出每个 worker 的 n 值（由 60,000/m 可推，m=40 时约 1500、m=10 时约 6000，此为分析）。
- 客户端（clients）：不做客户端抽样。每轮全部 m 个 worker 都必须参与并上传，拜占庭 worker 也不会被排除。实验规模：m = 40（Table 2）、m = 10（Table 3、Table 4）。
- 层（layers）：论文未使用。算法把整个梯度当作一个 d 维向量处理，不区分层，也不做分层聚合或分层裁剪。
- 坐标（coordinates）：不抽样、不降维。中位数在全部 d 个坐标上逐维计算；论文没有报告实验中的 d 取值。
- 轮次（rounds）：GD 版本运行 T 轮，T 的取值见 Theorem 1–3（依赖 Δ、L_F、λ_F、w* 等量）；一次性版本只通信 1 轮。实验 Figure 1 的横轴画到 2000 轮（logistic regression）与 5000 轮（CNN），但论文未说明最终采用了多少轮。
- 参考数据 / 探针（probes）：论文未使用。方法不需要任何干净参考数据或探针样本，数量为 0。

## 5. 超参数

- m：worker 数量。实验取 m = 40（Table 2）、m = 10（Table 3、Table 4）。
- n：每个 worker 的本地样本数。贯穿 Assumption 2/3/6 与全部定理；中位数法的率 Õ(α/√n + 1/√(nm) + 1/n) 只有在 n ≳ m 时才是阶最优（Section 4.1、Section 4.3 Table 1）。
- α：拜占庭 worker 比例，|B| = αm（Section 3）。中位数 GD 不需要知道 α（Table 1 中 "α known? No"）；实验取 α = 0.05（Table 2）与 α = 0.1（Table 3、Table 4）。
- β：截尾均值比例，β ∈ [0, 1/2)，必须满足 β ≥ α，论文建议 β = cα（c ≥ 1）（Section 4.2、Section 4.3）；实验 β = 0.05（Table 2）、β = 0.1（Table 3）。中位数法不使用 β。
- η：步长，取 η = 1/L_F（Theorem 1–6）。
- T：迭代轮数，取值公式见第 3 节 A6（Theorem 1/2/3）。
- ϵ：条件 (2) 中的余量参数，要求 α + sqrt(d·log(1+nmL̂D)/(m(1−α))) + 0.4748·S/√n ≤ 1/2 − ϵ；C_ϵ 由式 (4) 定义，论文举例 ϵ = 1/6 时 C_ϵ ≈ 4（Section 4.1）。
- d：参数维度，出现在定义 1 与全部率中。
- D：参数空间 W 的直径（Section 3；条件 (2) 里以 log(1+nmL̂D) 出现）。
- L_k、L、L̂、L_F、λ_F：光滑性与强凸性常数，L̂ = sqrt(Σ_k L_k²)，且 L_F ≤ L ≤ L̂（Assumption 1、Theorem 1）。光滑性还写成了一个"通用常数"版本：L-smooth 在 Assumption 1，Appendix B 中的梯度偏差界用到 L̂。
- V、S：梯度方差上界与逐坐标绝对偏度上界（Assumption 2、Assumption 3）。
- v：∂_k f(w;z) 的次指数（sub-exponential）参数（Assumption 6；Proposition 2 给出 √(σ²+‖w−w*‖²)）。
- M：非凸情形下 ‖∇F(w)‖_2 的上界（Assumption 5）。

## 6. 判定与动作

- 没有检测环节。方法不输出任何客户端级别的判定，不估计谁是拜占庭，也没有阈值、打分或聚类规则；论文明确假设拜占庭机器可以发送任意消息并合谋（Section 3）。
- 动作就是聚合规则的替换：把"取平均"换成"逐坐标取中位数"。A4 的输出 g(w^t) 直接当作梯度方向使用，再经 A5 完成一次模型更新。
- 鲁棒性条件：只要 α + sqrt(d·log(1+nmL̂D)/(m(1−α))) + 0.4748·S/√n ≤ 1/2 − ϵ 成立，Theorem 8（式 (27)）保证对任意 w ∈ W 都有 ‖g(w) − ∇F(w)‖_2 ≤ 2√2/(nm) + (√2·C_ϵ·V/√n)·(α + sqrt(d·log(1+nmL̂D)/(m(1−α))) + 0.4748·S/√n)，即中位数聚合不会被任意消息任意拉偏。
- 由此得到的收敛：‖w^T − w*‖_2 ≤ (1 − λ_F/(L_F+λ_F))^T·‖w^0−w*‖_2 + (2/λ_F)·Δ，其中 Δ = O(C_ϵ·V·(α/√n + sqrt(d·log(nmL̂D)/(nm)) + S/n))（Theorem 1 与式 (3)）。
- 幅度控制：没有裁剪阈值、没有加噪幅度、没有显式的权重；中位数的"幅度"完全由正常 worker 的坐标值决定，拜占庭值只有落在中位数附近才能影响结果。
- 是否跨轮累积：不累积。每一轮的中位数只由该轮的 m 条消息决定，跨轮传递的只有模型参数 w^t；算法没有动量或历史消息缓存（Algorithm 1）。
- 一次性变体的动作：对 m 个本地 ERM 解逐坐标取中位数，得到 ŵ；在二次损失、W = R^d 与条件 α + sqrt(log(nmd)/(2m(1−α))) + C̃/√n ≤ 1/2 − ϵ 下，以概率至少 1 − 4/(nm) 有 ‖ŵ − w*‖_2 ≤ (C_ϵ/√n)·σ̃·(α + sqrt(log(nmd)/(2m(1−α))) + C̃/√n)（Theorem 7）。

## 7. 需要的外部资源

- 干净参考数据 / 根数据集（root dataset）：论文未使用。
- 预训练检测器、额外的模型、对齐前后的权重：论文未使用。
- 方法本身唯一依赖的是：已知参数空间 W（用于 Π_W 投影，Section 3、Assumption 1）；在一次性变体中理论分析还要求 W = R^d（Section 5、Theorem 7）。
- 理论界用到但方法不消耗的常数：L_F、λ_F、L̂、D、V、S（或 v）等，用于确定 η、T 与可容忍的 α（Assumption 1–3、6；Theorems 1–7）；论文没有说明实现中如何获得这些常数。
- 通信侧要求：m 个 worker 每轮都要能上传一个 O(d) 的向量，且所有 worker 的梯度/参数必须处在同一坐标系与同一维度下（这是复现的前提，论文未讨论异构模型）。
- 实验环境：MNIST 数据集的 60,000 条训练样本、TensorFlow、Microsoft Azure（Section 7），这些属于评测基础设施，不是防御方法本身的资源需求。

## 8. 计算与存储开销

论文报告的开销：
- 通信：每轮每个 worker 或 master 只通信一个 O(d) 的向量，总通信量与通信轮数成正比（Section 1："in each round a worker or master machine can only communicate a vector of size O(d) … the total communication cost is proportional to the number of communication rounds"）。
- 一次性中位数算法被明确描述为通信更省：Abstract 说它 "uses only one communication round"，Section 5 说它 "has similar theoretical performance as the robust gradient descent algorithm with significantly less communication cost"。
- 统计开销：中位数 GD 的误差率为 Õ(α/√n + 1/√(nm) + 1/n)（Section 1.1、Section 4.1、Table 1）。
- 论文没有报告运行时间、FLOPs 或内存占用的任何数值。

按流水线的开销来源（分析：）：
- 主要开销在 A2：每个正常 worker 每轮对 n 条本地样本做一次前向+反向传播（全批量梯度），随 n 与模型规模线性增长，并重复 T 轮；这是与普通分布式 GD 完全相同的部分。
- 防御特有的额外开销在 A4：master 每轮要对 m×d 矩阵逐坐标求中位数。每个坐标用选择算法是 O(m)（期望）、用排序是 O(m log m)，合计 O(dm) 到 O(dm log m)，随 d 与 m 增长；此外 master 每轮要存 m×d 的梯度矩阵（O(md)）。
- 相比均值聚合只多了排序/选择这一步；不需要额外的公共数据前向传播，也不需要训练检测器。一次性变体则相反：客户端要做一次完整的本地 ERM 求解（可能远贵于单轮梯度），但通信只有 1 轮。

## 9. 实现时容易错的地方

论文强调或明确给出的细节：
- 中位数是逐坐标的，不是几何中位数；Definition 1 规定第 k 个坐标只取第 k 个坐标上的中位数，因此实现时必须在参数坐标轴上操作（Definition 1、Algorithm 1 Option I）。
- 正常 worker 的 g_i 是本地经验风险 ∇F_i 的梯度，不是单个样本的随机梯度；理论与实验（logistic regression）都是全批量（Algorithm 1、Section 7）。
- 步长在定理里固定为 η = 1/L_F（Theorem 1–6），不是任意调参。
- 中位数法不需要知道 α，而截尾均值变体必须知道 α 的上界并取 β ≥ α（Table 1、Section 4.2）。
- 中位数的鲁棒性依赖于"拜占庭比例（加上统计项）小于 1/2"这一条件 (2)，一旦超过就没有保证（Theorem 1、式 (2)）。
- 一次性中位数算法的理论保证只在二次损失、W = R^d 下成立，其他损失只有实验证据（Section 5："We are only able to establish such a guarantee when the loss functions are quadratic and W = Rd"；Table 4 的 logistic 实验是经验性的）。

论文没说清、实现时必须自己决定的地方：
1. 偶数 m 时 "usual (one-dimensional) median" 的定义（取中间两数的平均还是下中位数）论文未说明；而实验的 m = 40 与 m = 10 都是偶数。
2. w^0 的初始化方式论文未说明；实验里的学习率也没有报告（理论只给 η = 1/L_F）。
3. 实际停机准则论文未说明：定理给出的 T 依赖 Δ、L_F、λ_F、w* 等无法预先知道的量，需要实现者另定停止条件。
4. 投影集合 W 在实验里到底是什么、是否真的执行了投影，论文未说明；一次性变体的理论还要求 W = R^d。
5. ϵ 的取值论文未说明，只给了 C_ϵ 在 ϵ = 1/6 时约为 4（式 (4) 及其后）。
6. 若 worker 用 mini-batch 而不是全批量（CNN 实验就是 10%），中位数坐标分布会改变、可容忍的 α 上界如何变化，论文未分析。
7. 若有 worker 掉线或只收到 m′ < m 条消息，中位数的鲁棒性条件如何调整，论文未说明（算法假设每轮全部 m 个 worker 参与）。
8. 拜占庭消息为 NaN/Inf 或非法长度时如何处理，论文未说明；逐坐标中位数在排序/选择时遇到非有限值会失效。
9. 不同 worker 的模型结构、参数维度或参数展平顺序不一致时怎么办，论文未说明。
10. 是否需要对不同 worker 的梯度做缩放或归一化预处理，论文未说明。
11. 常数 L_F、λ_F、V、S/v、D、M 如何从数据估计，论文未说明。
12. 实验的 d、n、迭代轮数、随机种子与最终采用的轮数没有给出（Figure 1 只画了曲线横轴到 2000/5000 轮）。
13. 常数 C_ϵ（式 (4)）与 Berry–Esseen 常数 0.4748 都是理论量，实现中是否以及如何使用，论文未说明。
14. 如何把论文的拜占庭模型（可合谋、知道全部信息、可任意发消息）映射到真实系统（含安全聚合、压缩、异步）论文未说明。

## 10. 原文依据

1. 支撑步骤 A1（广播当前模型）："In each parallel iteration of the algorithms, the master machine broadcasts the current model parameter to all worker machines."（Section 4 第 1 段）
2. 支撑步骤 A2（计算本地梯度并上传）："The normal worker machines compute the gradients of their local loss functions and then send the gradients back to the master machine."（Section 4 第 1 段）
3. 支撑步骤 A4/A5（中位数聚合后做一步梯度更新）："The master machine then performs a gradient descent update on the model parameter with step-size η, using either the coordinate-wise median or trimmed mean of the received gradients."（Section 4 第 1 段）
4. 支撑步骤 A4（逐坐标中位数的精确定义）："For vectors xi ∈Rd, i ∈[m], the coordinate-wise median g := med{xi : i ∈[m]} is a vector with its k-th coordinate being gk = med{xi k : i ∈[m]} for each k ∈[d]"（Definition 1）
5. 支撑步骤 A5（投影到参数空间）："The Euclidean projection ΠW(·) ensures that the model parameter stays in the parameter space W."（Section 4 第 1 段）
6. 支撑步骤 A3（不识别、不过滤，拜占庭可发任意消息的威胁模型）："The Byzantine machines need not obey this protocol and can send arbitrary messages to the master; in particular, they may have complete knowledge of the system and learning algorithms, and can collude with each other."（Section 3）
7. 支撑步骤 B2（一次性算法用中位数聚合本地解）："As detailed in Algorithm 2, we employ the coordinate-wise median operation to aggregate all the ERMs."（Section 5）
8. 支撑第 4 节与第 6 节的规模条件（1/n 项与阶最优性）："When each worker machine has a sufficient amount of data, more specifically n ≳m, we achieve an order-optimal error rate up to logarithmic factors."（Section 4.1）

```json
{
  "key": "yin2018median",
  "method": "Coordinate-wise median based Byzantine-robust distributed gradient descent (Algorithm 1, Option I) and the median-based robust one-round algorithm (Algorithm 2)",
  "stages": ["server_distribute", "client_pre_train", "client_step", "server_receive", "server_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "广播当前全局模型",
      "operator": "broadcast_model",
      "input": "服务器参数 w^t ∈ R^d，t = 0..T-1",
      "output": "m 个 worker 各自收到同一份 w^t",
      "params": {"fanout": "m（实验 m=40 或 10）"},
      "source": "Algorithm 1 第 1 行；Section 4 第 1 段"
    },
    {
      "step": "本地全批量经验梯度",
      "operator": "local_full_batch_gradient",
      "input": "worker i 的 n 条本地数据 {z_{i,1..n}} 与 w^t",
      "output": "g_i(w^t) = ∇F_i(w^t) ∈ R^d",
      "params": {"local_samples": "n（全量；CNN 实验每次迭代仅用 10% 本地数据）"},
      "source": "Algorithm 1 'Worker machine i: compute local gradient gi(wt) ← ∇Fi(wt)'；Section 3 的 F_i 定义；Section 7"
    },
    {
      "step": "原样收集 m 份更新（不过滤）",
      "operator": "collect_updates",
      "input": "各 worker 上传的 g_i(w^t)，拜占庭可为任意 ∗",
      "output": "矩阵 G ∈ R^{m×d}",
      "params": {},
      "source": "Algorithm 1 第 3-6 行；Section 3 Byzantine 定义"
    },
    {
      "step": "逐坐标取中位数",
      "operator": "coordinate_median",
      "input": "G ∈ R^{m×d}",
      "output": "g(w^t) ∈ R^d，g_k = med{g_i^k(w^t) : i ∈ [m]}",
      "params": {"axis": "coordinate-wise，每一维独立"},
      "source": "Definition 1；Algorithm 1 Option I；偏差界见 Theorem 8 / 式 (27)"
    },
    {
      "step": "投影梯度更新",
      "operator": "projected_gradient_step",
      "input": "w^t, g(w^t), η",
      "output": "w^{t+1} = Π_W(w^t − η g(w^t))",
      "params": {"eta": "1/L_F（Theorem 1-6）", "W": "凸紧集，直径 D（Section 3）"},
      "source": "Algorithm 1 最后一行；Theorems 1-3"
    },
    {
      "step": "变体：逐坐标截尾均值（与上一步的坐标中位数二选一）",
      "operator": "coordinate_trimmed_mean",
      "input": "G ∈ R^{m×d}",
      "output": "g_k = 1/((1−2β)m) · Σ_{x∈U_k} x",
      "params": {"beta": "β ∈ [0,1/2)，须 β ≥ α，建议 β = cα (c ≥ 1)；实验 β=0.05 (Table 2)、β=0.1 (Table 3)"},
      "source": "Definition 2；Algorithm 1 Option II；Section 4.2"
    },
    {
      "step": "一次性变体：本地求解 ERM",
      "operator": "local_erm_solve",
      "input": "本地数据与参数空间 W",
      "output": "ŵ_i = arg min_{w∈W} F_i(w) ∈ R^d",
      "params": {"theory": "二次损失且 W = R^d（Theorem 7）", "assumption": "Assumption 7：F_i 以概率 1 强凸"},
      "source": "Algorithm 2 第 1-4 行；Section 5；Theorem 7"
    },
    {
      "step": "一次性变体：对本地 ERM 逐坐标取中位数",
      "operator": "coordinate_median",
      "input": "m 个 ŵ_i ∈ R^d",
      "output": "ŵ = med{ŵ_i : i ∈ [m]} ∈ R^d",
      "params": {"communication_rounds": 1},
      "source": "Algorithm 2 最后一行；Section 5；Theorem 7"
    }
  ],
  "sampling": [
    {"what": "samples", "how": "理论设定下每个 worker 每轮用全部 n 条本地样本做全批量梯度，不抽样；仅 CNN 实验改用随机梯度，每次迭代每个 worker 用 10% 本地数据", "size": "理论为 n（论文未给数值）；CNN 实验 10%（Section 7）；MNIST 共 60,000 条被均分给 m 个 worker（Section 7）"},
    {"what": "clients", "how": "不抽样：每轮全部 m 个 worker 都参与上传，拜占庭 worker 也不被剔除", "size": "m = 40（Table 2）、m = 10（Table 3、Table 4）"},
    {"what": "coordinates", "how": "不抽样、不降维：中位数在全部 d 个坐标上逐维独立计算", "size": "d（论文未报告实验的 d 值）"},
    {"what": "layers", "how": "论文未使用：梯度被当成单个 d 维向量整体聚合，没有分层处理或分层裁剪", "size": "未使用"},
    {"what": "rounds", "how": "GD 版本跑 T 轮，T 由定理给出；一次性版本只通信 1 轮", "size": "T 见 Theorem 1/2/3；Figure 1 横轴画到 2000（logistic）与 5000（CNN）轮，论文未说明最终采用值"},
    {"what": "probes", "how": "论文未使用任何参考数据或探针", "size": "0"}
  ],
  "resources": [
    "论文未使用干净参考数据、根数据集、预训练检测器或额外模型",
    "需要已知参数空间 W 以执行投影 Π_W（Section 3、Assumption 1）；一次性变体的理论进一步要求 W = R^d（Section 5）",
    "理论界依赖 L_F、λ_F、L̂、D、V、S（或 v）等常数来定 η、T 与可容忍的 α（Assumptions 1-3、6；Theorems 1-7），论文未说明如何获得",
    "m 个 worker 每轮都要能上传一个 O(d) 向量，且所有 worker 的梯度维度与参数顺序必须一致（分析）"
  ],
  "actions": ["transform_gradients"],
  "dominant_cost": "论文只报告通信开销：每个 worker/master 每轮通信一个 O(d) 向量，总通信量正比于轮数（Section 1）；一次性中位数算法只需 1 轮通信（Abstract、Section 5）。分析：主要计算开销是每个正常 worker 每轮对 n 条本地样本做一次全批量前向+反向（随 n、模型规模和 T 增长），防御特有开销是 master 对 m×d 矩阵逐坐标求中位数（每坐标 O(m) 选择或 O(m log m) 排序，合计 O(dm) 到 O(dm log m)），并需存下 m×d 的梯度矩阵（O(md)）。",
  "underspecified": [
    "偶数 m 时 usual (one-dimensional) median 的定义（中间两数取平均还是取下中位数）论文未说明，而实验的 m=40 与 m=10 都是偶数",
    "初始参数 w^0 的取法与实验中的学习率论文未说明（理论只给 η = 1/L_F）",
    "实际停机准则论文未说明：定理给出的 T 依赖 Δ、L_F、λ_F、w* 等不可预知的量",
    "实验里 W 是什么、是否真的执行投影论文未说明；一次性变体的理论要求 W = R^d",
    "ϵ 的取值论文未说明，只给出 ϵ=1/6 时 C_ϵ≈4（式 (4) 及其后）",
    "理论假设全批量本地梯度，而 CNN 实验用 10% 本地数据的随机梯度；两者如何对应、批量大小如何选，论文未说明",
    "worker 掉线或只收到 m′<m 条消息时中位数的鲁棒性条件如何变化，论文未说明（算法假设每轮 m 个 worker 全参与）",
    "拜占庭消息为 NaN/Inf 或维度非法时如何处理，论文未说明",
    "不同 worker 模型结构、参数维度或展平顺序不一致时如何处理，论文未说明",
    "是否需要对各 worker 的梯度做缩放或归一化预处理，论文未说明",
    "常数 L_F、λ_F、V、S/v、D、M 如何从数据估计，论文未说明",
    "实验中的 d、n、随机种子与最终采用的迭代轮数论文未报告",
    "理论量 C_ϵ（式 (4)）与 Berry-Esseen 常数 0.4748 在实现中如何使用，论文未说明",
    "如何把可合谋、可知晓全部信息的拜占庭模型映射到真实系统（安全聚合、压缩、异步等）论文未说明"
  ],
  "quotes": [
    {"supports": "步骤 A1：服务器把当前模型广播给所有 worker", "text": "In each parallel iteration of the algorithms, the master machine broadcasts the current model parameter to all worker machines."},
    {"supports": "步骤 A2：正常 worker 计算本地梯度并回传", "text": "The normal worker machines compute the gradients of their local loss functions and then send the gradients back to the master machine."},
    {"supports": "步骤 A4 与 A5：用中位数（或截尾均值）聚合后做一步步长为 η 的梯度更新", "text": "The master machine then performs a gradient descent update on the model parameter with step-size η, using either the coordinate-wise median or trimmed mean of the received gradients."},
    {"supports": "步骤 A4：逐坐标中位数的精确定义", "text": "For vectors xi ∈Rd, i ∈[m], the coordinate-wise median g := med{xi : i ∈[m]} is a vector with its k-th coordinate being gk = med{xi k : i ∈[m]} for each k ∈[d]"},
    {"supports": "步骤 A5：投影保证参数留在参数空间内", "text": "The Euclidean projection ΠW(·) ensures that the model parameter stays in the parameter space W."},
    {"supports": "步骤 A3：拜占庭可发任意消息且可合谋，因此方法不做识别而只做鲁棒聚合", "text": "The Byzantine machines need not obey this protocol and can send arbitrary messages to the master; in particular, they may have complete knowledge of the system and learning algorithms, and can collude with each other."},
    {"supports": "步骤 B2：一次性算法对本地 ERM 逐坐标取中位数", "text": "As detailed in Algorithm 2, we employ the coordinate-wise median operation to aggregate all the ERMs."},
    {"supports": "第 4 节与第 6 节的规模条件：中位数法要多出一个 1/n 项，n ≳ m 时才阶最优", "text": "When each worker machine has a sufficient amount of data, more specifically n ≳m, we achieve an order-optimal error rate up to logarithmic factors."}
  ]
}
```
