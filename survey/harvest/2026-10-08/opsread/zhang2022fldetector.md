# zhang2022fldetector：FLDetector（基于模型更新一致性检测恶意客户端）

## 1. 方法一句话

FLDetector 是纯服务器端的恶意客户端检测方法：输入是每轮所有客户端上传的模型更新序列（n×p，n 为客户端数、p 为全局模型参数量）与服务器侧的全局模型序列，服务器用 L-BFGS 从最近 N 轮的"全局模型差 Δw、全局更新差 Δg"估计一个所有客户端共享的积分 Hessian 近似 Ĥ^t，据此预测每个客户端的更新 ĝ_i^t，用预测值与实收值的 ℓ2 欧氏距离经 ℓ1 归一化后在 N 轮窗口上取平均得到可疑分 s_i^t，再用 Gap statistics 判断可疑分能否聚类，若能则用 k-means（k=2）把平均可疑分较大的簇判为恶意；一旦某轮判定出至少一个恶意客户端，服务器停止训练、剔除这些客户端并用剩余客户端重启训练。输出是"恶意客户端集合"或"无"（Algorithm 3 的输出定义）。

## 2. 运行位置

全部计算在服务器端完成，发生在**服务器收到更新之后**：检测需要本轮聚合后的全局更新 g^t（用于算 Δg^t = g^t − g^{t−1}），所以流水线的自然位置是"服务器收到更新 → 服务器聚合 → 聚合之后（判定与动作）"。检测默认从第 50 轮开始，因为论文发现最初几十轮不稳定（§5.1："we start to detect malicious clients in the 50th iteration of FL training, as we found the first dozens of iterations may be unstable"）。判定触发后的动作是：服务器停止 FL、移除被判恶意的客户端、在剩余客户端上**重启训练**（§3 的 Problem definition、§4.2 末段、§5.1）。**不需要客户端与服务器之间的额外往返**：论文明确说 "As for the clients, FLDetector does not incur extra computation and communication overhead."（§4.3），客户端仍然只做常规的本地训练与上传。方法不修改聚合规则本身，也不修改下发的全局模型，只在检测到攻击时中断并重启流程。

## 3. 算子流水线

以下按执行顺序列出。记第 t 轮：n 个客户端，全局模型 w^t（p 维），聚合得到的全局更新 g^t（p 维）。

**步骤 1：检测启动门控**
- 输入：当前轮次 t（标量）。
- 计算：仅当 t ≥ 50 时进入后续检测步骤，否则本轮不做检测（论文默认值；论文未说明 t < 50 时是否仍缓存历史量，实现上需要缓存才能在第 50 轮立刻有 N 轮历史，这一点论文未说明）。
- 输出：是否运行检测的布尔值。
- 出处：§5.1（默认第 50 轮开始）；§5.2 Fig 4(b) 扫描起始轮次 10–60。

**步骤 2：接收并缓存客户端更新**
- 输入：本轮 n 个客户端上传的模型更新 g_i^t，每个是 p 维向量（展平为 n×p）。
- 计算：服务器收集全部更新，并保留每个客户端上一轮收到的更新 g_i^{t−1}（公式 (3) 需要），不做任何过滤或加权。
- 输出：本轮更新矩阵（n×p）与上一轮更新矩阵（n×p）。
- 出处：§3（"each selected client finetunes the received global model on its local training data and sends the model update back to the server"），公式 (1)；公式 (3)。

**步骤 3：聚合得到全局更新**
- 输入：n×p 的更新矩阵。
- 计算：按部署的聚合规则（FedAvg / Krum / Trimmed-Mean / Median）聚合为全局更新 g^t（论文实验用这四种，§5.1）；FLDetector 本身不改变聚合结果。
- 输出：g^t（p 维）。
- 出处：§3（"the server computes a global model update g^t via aggregating the clients' model updates based on some aggregation rule"）；§5.1。

**步骤 4：计算全局模型差与全局更新差**
- 输入：w^t、w^{t−1}、g^t、g^{t−1}。
- 计算：Δw^t = w^t − w^{t−1}（全局模型差）；Δg^t = g^t − g^{t−1}（全局更新差）。论文明确说明"全局模型更新是由客户端更新聚合而来"。
- 输出：两个 p 维向量 Δw^t、Δg^t。
- 出处：§4.1。

**步骤 5：维护长度 N 的滑动窗口缓冲**
- 输入：每轮的 Δw、Δg。
- 计算：ΔW^t = {Δw^{t−N}, Δw^{t−N+1}, …, Δw^{t−1}}，ΔG^t = {Δg^{t−N}, Δg^{t−N+1}, …, Δg^{t−1}}，即窗口只含过去 N 轮、不含当前轮。
- 输出：ΔW^t（p×N）与 ΔG^t（p×N）。
- 出处：§4.1；Algorithm 3 第 2 行。

**步骤 6：L-BFGS 估计 Hessian 向量积**
- 输入：ΔW^t（p×N）、ΔG^t（p×N）、向量 v = w^t − w^{t−1}（p 维）、窗口大小 N。
- 计算（Algorithm 1，逐步）：① 计算 ΔW_tᵀΔW_t；② 计算 ΔW_tᵀΔG_t，取它的对角矩阵 D_t 与其下三角子矩阵 L_t；③ 计算 σ = Δg_{t−1}ᵀΔw_{t−1} / (Δw_{t−1}ᵀΔw_{t−1})；④ 对 σΔW_tᵀΔW_t + L_tD_tL_tᵀ 做 Cholesky 分解，得到 J_tJ_tᵀ；⑤ 计算 q = [[−D_t^{1/2}, D_t^{−1/2}L_tᵀ],[0, J_tᵀ]]^{−1} [[D_t^{1/2}, 0],[D_t^{−1/2}L_tᵀ, J_t]]^{−1} [ΔG_tᵀv; σΔW_tᵀv]；⑥ 返回 Ĥ^t v = σv − [ΔG_t; σΔW_t] q。注意 Algorithm 1 的输出是 Hessian 在 v 方向上的投影（即 Hessian 向量积 HVP），不是显式 Hessian 矩阵。
- 输出：Ĥ^t(w^t − w^{t−1})，p 维向量。
- 出处：§4.1（"we use a L-BFGS algorithm to approximate integrated Hessian"、"Hˆ 𝑡= L-BFGS(Δ𝑊𝑡, Δ𝐺𝑡)"）；Algorithm 1 第 1–6 行；公式 (2)。

**步骤 7：预测每个客户端的更新**
- 输入：上一轮各客户端实收更新 g_i^{t−1}（n×p）、步骤 6 的 HVP 向量（p 维）。
- 计算：ĝ_i^t = g_i^{t−1} + Ĥ^t(w^t − w^{t−1})，i = 1,…,n；所有客户端共享同一个 Ĥ^t（论文为效率只估计一个统一 Hessian）。
- 输出：预测更新矩阵 ĝ^t（n×p）。
- 出处：公式 (3)；§4.1；Algorithm 3 第 3–5 行。

**步骤 8：计算预测-实收更新的欧氏距离向量**
- 输入：预测更新 ĝ_i^t 与实际收到的 g_i^t（各 n×p）。
- 计算：d^t = [‖ĝ_1^t − g_1^t‖₂, ‖ĝ_2^t − g_2^t‖₂, …, ‖ĝ_n^t − g_n^t‖₂]，逐客户端取 ℓ2 距离。
- 输出：n 维非负向量 d^t。
- 出处：§4.2；Algorithm 3 第 6 行。

**步骤 9：ℓ1 归一化距离向量**
- 输入：d^t。
- 计算：d̂^t = d^t / ‖d^t‖₁；论文给的理由是纳入不同轮次之间一致性变化的差异（"to incorporate the model-updates consistency variations across different iterations"）。注意分母是 ℓ1 范数而非 ℓ2。
- 输出：d̂^t（n 维，各分量非负且和为 1）。
- 出处：§4.2；Algorithm 3 第 7 行。

**步骤 10：窗口平均得到可疑分**
- 输入：过去 N 轮的 d̂。
- 计算：s_i^t = (1/N)·Σ_{r=0}^{N−1} d̂_i^{t−r}，即客户端 i 在第 t 轮的可疑分是最近 N 轮归一化欧氏距离的平均；论文把 N 称为窗口大小（window size）。
- 输出：可疑分向量 s^t（n 维）。
- 出处：§4.2；Algorithm 3 第 8 行；公式 (5) 的符号。

**步骤 11：Gap statistics 确定簇数**
- 输入：s^t（n 维可疑分）、采样次数 B、最大簇数 K、客户端数 n。
- 计算（Algorithm 2）：对 k = 1,2,…,K：① 对 s^t 做线性变换，使最小值变 0、最大值变 1；② 对可疑分做 k-means，得簇 {C_i} 与各簇均值 {μ_i}；③ 计算簇内离散度 V_k = Σ_{i=1}^{k} Σ_{x_j∈C_i} ‖x_j − μ_i‖²；④ 对 b = 1,…,B：在 [0,1] 上均匀采样 n 个点，做 k-means 并计算 V*_{kb}；⑤ Gap(k) = (1/B)Σ_{b=1}^{B} log(V*_{kb}) − log(V_k)；⑥ v' = (1/B)Σ_{b=1}^{B} log(V*_{kb})；⑦ sd(k) = ((1/B)Σ_{b=1}^{B}(log(V*_{kb}) − v')²)^{1/2}；⑧ s'_k = √((1+B)/B)·sd(k)。最后 k̂ = 满足 Gap(k) − Gap(k+1) + s'_{k+1} ≥ 0 的最小 k。
- 输出：簇数 k̂。
- 出处：§4.2；Algorithm 2（完整伪代码）；Algorithm 3 第 9 行。

**步骤 12：k-means 二聚类**
- 输入：s^t。
- 计算：若 k̂ > 1，则以 k=2 在可疑分上做 k-means 聚类（即"可疑分能分成多于 1 簇"才继续）。
- 输出：客户端被划入两个簇。
- 出处：§4.2；Algorithm 3 第 10–11 行。

**步骤 13：选出恶意簇**
- 输入：两个簇的成员及其可疑分。
- 计算：计算每个簇的平均可疑分，平均可疑分较大的簇中的客户端被判为恶意。
- 输出：恶意客户端集合（可能为空）。
- 出处：§4.2；Algorithm 3 第 12 行。

**步骤 14：剔除并重启**
- 输入：被判恶意的客户端集合。
- 计算：某轮只要判出至少一个恶意客户端，检测即结束，服务器移除这些客户端并在剩余客户端上重启 FL 训练，重复预定义的训练轮数；若训练到预定义轮数结束都未检测到恶意客户端，则把所有客户端都判为良性。
- 输出：新的客户端集合，以及用剩余客户端重训得到的全局模型。
- 出处：§3 Problem definition（"the server stops the FL process, removes the clients detected as malicious, and restarts the FL process on the remaining clients"）；§4.2；§5.1（"If no malicious clients are detected after finishing training for the pre-defined number of iterations, we classify all clients as benign."）；§5.2（Table 3 的重新训练设置）。

## 4. 采样与规模控制

- **客户端（clients）**：不做客户端抽样。论文明确"For simplicity, we assume all clients are involved in each iteration of FL training."（§5.1）。规模：MNIST 与 CIFAR10 各 100 个客户端，FEMNIST 随机取 300 个 writer，每个 writer 视为一个客户端（§5.1）。
- **轮次（rounds）**：对历史做窗口截断，只保留最近 N 轮的 Δw 与 Δg（§4.1、Algorithm 3 第 2 行）；检测本身默认从第 50 轮才开始（§5.1）。N=10 为默认值（§5.1），并在 Fig 4(c) 中扫描 N ∈ {3,5,10,15,20}。
- **探针/参考数据（probes）**：Gap statistics 对每个候选簇数 k 生成 B 组参考数据，每组在 [0,1] 上均匀采样 n 个点并做 k-means（Algorithm 2）；B=20、K=10 为默认值（§5.1），Fig 4(d) 扫描 B ∈ {10,15,20,25,30,35,40}。这些参考点是合成的，不是真实数据。每轮检测合计要跑 K 次（真实可疑分）+ K·B 次（参考数据）k-means，即 K(B+1) 次（分析：由 Algorithm 2 的双层循环直接得到）。
- **层或参数坐标（layers / coordinates）**：论文未使用。可疑分用完整参数向量的 ℓ2 范数，未做逐层、逐坐标的抽样或降维（§4.2；§4.3 的复杂度以 p 为参数量）。
- **样本（samples）**：论文未使用。FLDetector 不需要干净验证数据或参考样本，这正是论文强调的相对于 VAE 检测器与 FLTrust 的优势（§1、§2.2）。

## 5. 超参数

- **N（窗口大小，window size）**：可疑分平均与 L-BFGS 使用的历史轮数。取值 **10**（§5.1："We set the window size 𝑁 to 10."）；Fig 4(c) 扫描 3、5、10、15、20，结论是 N 太小（如 3）时 DACC 略降。
- **K（Gap statistics 的最大簇数）**：取值 **10**（§5.1："we set the maximum number of clusters 𝐾 and number of sampling 𝐵 in Gap statistics to 10 and 20, respectively."）。论文未对 K 做敏感性扫描。
- **B（Gap statistics 的采样次数）**：取值 **20**（§5.1，同上）；Fig 4(d) 扫描 10–40，结论是对该超参数鲁棒。
- **检测起始轮次**：取值 **50**（§5.1）；Fig 4(b) 扫描 10–60，结论是过早检测因早期不稳定而 DACC 略降。
- **总训练轮数 I_ter**：MNIST 1000 轮，CIFAR10 与 FEMNIST 2000 轮（§5.1，FL settings）。
- **全局学习率 α**：MNIST 2×10⁻⁴，CIFAR10 与 FEMNIST 1×10⁻³（§5.1）。
- **理论条件（不是可调超参数但影响可用性）**：Theorem 1 要求 α < 1/((N+2)L)，其中 L 是损失函数的 L-smooth 常数（§4.4）。
- **恶意客户端比例（攻击方设置，用于实验）**：默认 28%，MNIST/CIFAR10/FEMNIST 分别 28、28、84 个恶意客户端（§5.1）。
- **缩放攻击系数（攻击方设置）**：100（§5.1）。
- **自适应攻击的 λ（攻击方超参数，不属于防御）**：λ ∈ (0,1]，见公式 (6) 与 §4.5；λ 越小越难被检测但攻击越弱。
- 论文未给出 k-means 的迭代次数、初始化方式、收敛判据等超参数。

## 6. 判定与动作

- **判定规则一（簇数）**：Gap statistics 返回 k̂ = 满足 Gap(k) − Gap(k+1) + s'_{k+1} ≥ 0 的最小 k（Algorithm 2 最后一行）；只有当 k̂ > 1（即可疑分能被分成多于一个簇、存在离群点）时才认为存在恶意客户端（§4.2："If there are more than one cluster, the attack detection Flag is set to positive because there are outliers in the suspicious scores."）。k̂ = 1 时本轮不判恶意，训练继续。
- **判定规则二（哪些客户端）**：k̂ > 1 时用 k-means、k=2 在可疑分上聚类，平均可疑分更大的簇中的客户端被判为恶意（§4.2；Algorithm 3 第 10–12 行）。判定是二值硬判定，没有阈值化的可疑分门限，也没有给客户端加权。
- **动作**：论文只采用"剔除 + 重启"。一旦某轮判出至少一个恶意客户端，服务器停止 FL、移除这些客户端、用剩余客户端重启训练，重复预定义的训练轮数（§3 Problem definition；§4.2）。**不做**信任加权（不像 FLTrust）、**不做**更新裁剪或加噪（不是裁剪/加噪类防御）、**不做**样本过滤。若整个训练结束都没有检测到，则全部客户端判为良性（§5.1）。
- **跨轮累积**：可疑分本身跨轮累积，它是最近 N=10 轮归一化距离的滑动平均（§4.2；Algorithm 3 第 8 行），不是指数衰减，也不是全历史累积。检测判定本身每轮独立做一次；检测一旦触发就结束本轮流程并重启（不是逐轮迭代式地反复剥离）。
- **效果**：论文报告剔除后重训的全局模型精度与无攻击时相当（Table 3：例如 CIFAR10 上无攻击 TACC 65.8，A Little is Enough 攻击下不用 FLDetector 为 62.1/ASR 95.2，用 FLDetector 为 64.3/ASR 1.8；§5.2）。

## 7. 需要的外部资源

- **干净参考数据**：不需要。这是论文的核心卖点之一：FLDetector 不需要服务器持有干净验证集或根数据集（§1、§2.2 对 FLTrust 与 VAE 检测方法的对比）。§4.3 也说明 FLDetector 只带来服务器端开销。
- **预训练检测器**：不需要。检测器没有可训练参数；Ĥ^t 每轮由 ΔW^t、ΔG^t 现场估计（§4.1、Algorithm 1）。
- **服务器状态（存储）**：最近 N 轮的全局模型差 Δw 与全局更新差 Δg，存储开销 O(Np)，p 为全局模型参数量（§4.3）。此外公式 (3) 隐含需要保留每个客户端上一轮上传的 g_i^{t−1}，规模 n×p（论文未单列这项开销；分析：）。
- **聚合规则**：需要一个已部署的聚合规则来产生 g^t，并在剔除恶意客户端后用 Byzantine-robust 聚合（Krum / Trimmed-Mean / Median）在剩余客户端上重训；FLDetector 被定位为这类方法的"前置过滤器"（§3、§5.1）。
- **算力**：服务器被视为算力充足（§4.3："the server is powerful in FL"）。客户端不需要任何额外资源。

## 8. 计算与存储开销

论文报告（§4.3）：

- 服务器存储：O(Np)，用于保存最近 N 轮的全局模型差与全局更新差。
- L-BFGS 估计 Ĥ^t 并计算 Hessian 向量积 Ĥ^t(w^t − w^{t−1})：每轮 O(N³ + 6Np)（引用文献 [5]）。
- 计算可疑分：每轮 O(2np + Nn)。
- Gap statistics 与 k-means：合计 O(KBn²)。
- 每轮总时间复杂度：**O(N³ + KBn² + (6N + 2n)p + Nn)**；由于 K、B、n、N 通常远小于 p，服务器端耗时对参数量 p 近似线性。
- 客户端：FLDetector 不引入额外计算与通信开销。

分析（基于流水线）：主要开销来自**步骤 6 的 L-BFGS 估计与 HVP**（对 p 线性、对窗口 N 三次方）和**步骤 7–8 对 n 个 p 维向量做预测与距离计算**（约 O(np)，即每条客户端更新一次全参数向量级的加法和范数计算，不含任何反向传播）。按论文常数代入 n=100、N=10 时，距离/预测项系数 2n=200 大于 L-BFGS 项系数 6N=60，因此实际主项由客户端数与参数量共同决定；Gap statistics 的 K(B+1) 次 1 维 n 点 k-means 在 n、K、B 较小时可忽略。存储峰值主要是同时保存 ΔW、ΔG（2Np）与更新矩阵（约 2np）以及模型本身（2p~3p）。整个流水线不含任何梯度或反向传播计算，只在服务器上做向量运算与一维聚类。

## 9. 实现时容易错的地方

论文明确强调或需要特别注意的：

1. **检测必须在聚合之后**：Δg^t 依赖本轮聚合出的全局更新 g^t（§4.1），所以不能只凭收到的客户端更新就完成判定；同时公式 (2)/(3) 中的 w^t − w^{t−1} 是上一轮全局更新作用后的模型差。
2. **只估计一个共享 Hessian**：论文为效率对所有客户端共用一个 Ĥ^t（§4.1）；只有自适应攻击（公式 (6)）才在被攻击客户端本地按自己的数据算 Ĥ^t_i，实现防御时不要照搬。
3. **用 HVP 而不是显式 Hessian**：Algorithm 1 的输出是 Hessian 在某方向上的投影，输入还额外带向量 v = w^t − w^{t−1}；显式构造 p×p 矩阵会带来 O(p²) 内存，与论文的 O(Np) 存储结论不符。
4. **归一化用 ℓ1 范数**：d̂^t = d^t/‖d^t‖₁（§4.2），用 ℓ2 会改变多客户端场景下可疑分的相对尺度；这一归一化导致攻击轮次中良性客户端平均可疑分被压低（§5.2 Fig 3 的讨论）。
5. **窗口平均是等权滑动平均**，且窗口 N 同时被用于 L-BFGS 的历史长度与可疑分的平均长度（§4.1、§4.2）；改动其中一个会影响另一个的语义。
6. **判定语义是"一次剔除 + 重启"**：某轮一旦判出至少一个恶意客户端就停止训练（§3、§4.2），不是继续跑到收敛再剔除。
7. **理论保证有条件**：Theorem 1 只在梯度 L-smooth、FedAvg、各客户端数据 iid、恶意客户端把真实更新取反、且 α < 1/((N+2)L) 时给出 E(s_benign) < E(s_malicious)（§4.4）；论文自己做的攻击实验并不都满足这些条件。

论文没说清、实现时必须自行决定的地方：

1. **L-BFGS 紧凑表示的细节**：Algorithm 1 第 2 行只说"Compute ΔW_tᵀΔG_t, get its diagonal matrix D_t and its lower triangular submatrix L_t"，未说明是从一般矩阵取对角与下三角、是否取严格下三角、是否需要对称化处理。
2. **Cholesky 分解失败的兜底**：第 4 行要求 σΔW_tᵀΔW_t + L_tD_tL_tᵀ 正定，论文未说明分解失败或矩阵病态时的数值保护（如抖动项、回退策略）。
3. **窗口未满时的行为**：t < N（以及 t < 50）时可疑分、ΔW^t、ΔG^t 如何定义，论文未说明。
4. **Gap 公式在正文与 Algorithm 2 中不一致**：正文第 3 步写作 sd(k) = (1/B Σ (log(W*_{kb})) − w')²)^{1/2}（疑为抽取或排版错误），Algorithm 2 写作 sd(k) = ((1/B)Σ(log(V*_{kb}) − v')²)^{1/2}；实现应以 Algorithm 2 为准，但论文没有澄清。
5. **Gap 判据的边界**：判据需要 Gap(k+1) 与 s'_{k+1}，而 Algorithm 2 只在 k = 1…K 上计算，k = K 时 Gap(K+1) 未定义，论文未说明如何处理。
6. **log(0) 问题**：若某个簇只含一个点或所有点重合，V_k 可能为 0，log 后为 −∞，论文未说明数值保护。
7. **k-means 的实现细节**：初始化方式、迭代次数、是否固定随机种子、1 维可疑分上的距离度量、空簇处理，论文均未说明。
8. **部分参与的处理**：论文假设每轮所有客户端都参与（§5.1）；若某客户端上一轮未上传、g_i^{t−1} 缺失，如何处理未说明。
9. **Δg^t 用的 g^t 是否被攻击污染**：从 §4.1 的表述看用的是实际聚合结果（可能被攻击影响），但论文没有明确讨论；也没有说明 FLDetector 是否要求特定聚合规则。
10. **重启的具体方式**：是否从初始模型 w^0 重新开始、是否重置优化器与随机种子、历史缓冲是否清空、总轮数是否重新计数、检测在新一轮是否沿用第 50 轮的起始设置，论文均未说明（§3、§5.1 只说"restarts the FL training"和"repeats for the pre-defined number of iterations"）。
11. **检测触发当轮的模型更新是否被采用**：该轮服务器已经聚合出 g^t，但随即停止并重启，论文未说明这轮更新是否被丢弃。
12. **Table 3 的"No Attack"基线**是用剩余 72% 良性客户端训练的（§5.2 脚注式说明），复现对比时不能把它当作 100% 客户端的结果。

## 10. 原文依据

1. **支撑整体检测思路（步骤 1–14 的动机）**：
"Our key intuition is that, benign clients calculate their model updates based on the FL algorithm and their local training data, while malicious clients craft the model updates instead of following the FL algorithm."
2. **支撑步骤 4（Δw^t 与 Δg^t 的定义）**：
"Specifically, we denote by Δ𝑤𝑡= 𝑤𝑡−𝑤𝑡−1 the global-model difference in iteration 𝑡, and we denote by Δ𝑔𝑡= 𝑔𝑡−𝑔𝑡−1 the global-model-update difference in iteration 𝑡, where the global model update is aggregated from the clients’ model updates."
3. **支撑步骤 5–6（窗口缓冲与 L-BFGS 估计）**：
"Then, based on the L-BFGS algorithm, we can estimate Hˆ 𝑡using Δ𝑊𝑡and Δ𝐺𝑡. For simplicity, we denote by Hˆ 𝑡= L-BFGS(Δ𝑊𝑡, Δ𝐺𝑡). Algorithm 1 shows the specific implementation of L-BFGS algorithm in the experiments."
4. **支撑步骤 7（客户端更新预测公式 (3)）**：
"Based on the estimated Hessian Hˆ 𝑡, we predict a client 𝑖’s model update in iteration 𝑡as follows: 𝑔ˆ𝑡 𝑖= 𝑔𝑡−1 𝑖 + Hˆ 𝑡(𝑤𝑡−𝑤𝑡−1), (3) where 𝑔ˆ𝑡 𝑖is the predicted model update for client 𝑖in iteration 𝑡."
5. **支撑步骤 8–9（欧氏距离向量与 ℓ1 归一化）**：
"We denote by 𝑑𝑡the vector of such 𝑛Euclidean distances for the𝑛clients in iteration𝑡, i.e.,𝑑𝑡= [∥𝑔ˆ𝑡 1−𝑔𝑡 1∥2, ∥𝑔ˆ𝑡 2−𝑔𝑡 2∥2, · · · , ∥𝑔ˆ𝑡𝑛− 𝑔𝑡𝑛∥2]. We normalize the vector 𝑑𝑡as 𝑑ˆ𝑡= 𝑑𝑡/∥𝑑𝑡∥1."
6. **支撑步骤 10（窗口平均可疑分）**：
"Finally, our suspicious score 𝑠𝑡 𝑖for client 𝑖in iteration 𝑡is the client’s average normalized Euclidean distance in the past 𝑁iterations, i.e., 𝑠𝑡 𝑖= 1 𝑁 ∑︁𝑁−1 𝑟=0 𝑑ˆ𝑡−𝑟 𝑖 . We call 𝑁 window size."
7. **支撑步骤 11–13（Gap statistics 与 k-means 判定）**：
"If the clients can be grouped into more than 1 cluster based on the Gap statistics, then we use 𝑘-means to divide the clients into 2 clusters based on their suspicious scores. Finally, the clients in the cluster with larger average suspicious score are classified as malicious."
8. **支撑步骤 14（剔除并重启的动作）**：
"When at least one client is classified as malicious in a certain iteration, the detection finishes, and the server removes the clients classified as malicious and restarts the training."

```json
{
  "key": "zhang2022fldetector",
  "method": "FLDetector",
  "stages": ["server_receive", "server_aggregate", "server_post_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "检测启动门控",
      "operator": "detection_start_gate",
      "input": "当前轮次 t（标量）",
      "output": "是否在本轮运行检测的布尔值",
      "params": {"start_iteration": 50},
      "source": "§5.1（默认第 50 轮开始检测）；§5.2 Fig 4(b) 扫描 10–60"
    },
    {
      "step": "接收并缓存客户端更新",
      "operator": "collect_client_updates",
      "input": "本轮 n 个客户端上传的模型更新 g_i^t，展平为 n×p；以及上一轮缓存的 g_i^{t−1}（n×p）",
      "output": "更新矩阵 G^t（n×p）与 G^{t−1}（n×p）",
      "params": {},
      "source": "§3 与公式 (1)；公式 (3) 隐含需要 g_i^{t−1}"
    },
    {
      "step": "聚合得到全局更新",
      "operator": "aggregate_client_updates",
      "input": "n×p 的客户端更新矩阵",
      "output": "全局更新 g^t（p 维）",
      "params": {"rule": "FedAvg|Krum|Trimmed-Mean|Median"},
      "source": "§3；§5.1"
    },
    {
      "step": "计算全局模型差与全局更新差",
      "operator": "compute_global_differences",
      "input": "w^t、w^{t−1}、g^t、g^{t−1}",
      "output": "Δw^t = w^t − w^{t−1}（p 维）、Δg^t = g^t − g^{t−1}（p 维）",
      "params": {},
      "source": "§4.1"
    },
    {
      "step": "维护长度 N 的滑动窗口缓冲",
      "operator": "sliding_window_buffer",
      "input": "每轮的 Δw、Δg 流",
      "output": "ΔW^t（p×N）、ΔG^t（p×N），窗口为过去 N 轮不含当前轮",
      "params": {"N": 10},
      "source": "§4.1；Algorithm 3 第 2 行"
    },
    {
      "step": "L-BFGS 估计 Hessian 向量积",
      "operator": "lbfgs_hessian_vector_product",
      "input": "ΔW^t（p×N）、ΔG^t（p×N）、v = w^t − w^{t−1}（p 维）、窗口 N",
      "output": "Ĥ^t v（p 维），即 Ĥ^t(w^t − w^{t−1})",
      "params": {"N": 10},
      "source": "§4.1；Algorithm 1 第 1–6 行；公式 (2)"
    },
    {
      "step": "预测每个客户端的更新",
      "operator": "predict_update_by_hvp",
      "input": "上一轮实收更新 g_i^{t−1}（n×p）与 HVP 向量 Ĥ^t(w^t − w^{t−1})（p 维）",
      "output": "预测更新 ĝ_i^t = g_i^{t−1} + Ĥ^t(w^t − w^{t−1})（n×p）",
      "params": {"shared_hessian": true},
      "source": "公式 (3)；§4.1；Algorithm 3 第 3–5 行"
    },
    {
      "step": "计算预测-实收更新的欧氏距离向量",
      "operator": "euclidean_distance_vector",
      "input": "预测更新 ĝ_i^t 与实收更新 g_i^t（各 n×p）",
      "output": "d^t = [‖ĝ_i^t − g_i^t‖₂]（n 维）",
      "params": {"norm": "l2"},
      "source": "§4.2；Algorithm 3 第 6 行"
    },
    {
      "step": "L1 归一化距离向量",
      "operator": "l1_normalize",
      "input": "d^t（n 维）",
      "output": "d̂^t = d^t / ‖d^t‖₁（n 维，和为 1）",
      "params": {"norm": "l1"},
      "source": "§4.2；Algorithm 3 第 7 行"
    },
    {
      "step": "窗口平均得到可疑分",
      "operator": "sliding_window_average_score",
      "input": "过去 N 轮的 d̂",
      "output": "s_i^t = (1/N)Σ_{r=0}^{N−1} d̂_i^{t−r}（n 维）",
      "params": {"N": 10},
      "source": "§4.2；Algorithm 3 第 8 行"
    },
    {
      "step": "Gap statistics 确定簇数",
      "operator": "gap_statistic_k",
      "input": "s^t（n 维可疑分）、B、K、n",
      "output": "簇数 k̂",
      "params": {"K": 10, "B": 20, "reference_distribution": "uniform[0,1]", "transform": "min-max"},
      "source": "§4.2；Algorithm 2；Algorithm 3 第 9 行"
    },
    {
      "step": "k-means 二聚类",
      "operator": "kmeans_2",
      "input": "s^t（n 维），仅当 k̂ > 1 时执行",
      "output": "两个簇的成员划分",
      "params": {"k": 2},
      "source": "§4.2；Algorithm 3 第 10–11 行"
    },
    {
      "step": "选出恶意簇",
      "operator": "flag_high_mean_cluster",
      "input": "两个簇的成员及其可疑分",
      "output": "恶意客户端集合（可能为空）",
      "params": {"criterion": "larger average suspicious score"},
      "source": "§4.2；Algorithm 3 第 12 行"
    },
    {
      "step": "剔除并重启训练",
      "operator": "exclude_and_restart",
      "input": "恶意客户端集合",
      "output": "剩余客户端集合与重训后的全局模型",
      "params": {"trigger": "at least one malicious client in an iteration", "repeat": "pre-defined number of iterations"},
      "source": "§3 Problem definition；§4.2；§5.1"
    }
  ],
  "sampling": [
    {"what": "clients", "how": "论文假设每轮全部客户端参与，未做客户端抽样或截断", "size": "MNIST 与 CIFAR10 各 100 个客户端；FEMNIST 300 个 writer（§5.1）"},
    {"what": "rounds", "how": "用窗口 N 截断历史，只保留最近 N 轮的 Δw 与 Δg；检测默认从第 50 轮才开始", "size": "N=10（§5.1 默认值；Fig 4(c) 扫描 3、5、10、15、20）；起始轮 50（§5.1）"},
    {"what": "probes", "how": "Gap statistics 对每个候选簇数 k 生成 B 组参考数据，每组在 [0,1] 上均匀采 n 个点做 k-means（共 K(B+1) 次 k-means）", "size": "B=20、K=10（§5.1；Fig 4(d) 扫描 B=10–40）"},
    {"what": "coordinates", "how": "论文未使用：可疑分用完整参数向量的 ℓ2 范数，不做逐层或逐坐标的抽样、截断、降维", "size": "全参数 p"},
    {"what": "samples", "how": "论文未使用：FLDetector 不需要干净验证样本或参考训练样本", "size": "0"}
  ],
  "resources": [
    "不需要干净验证集或根数据集（§1、§2.2 对比 FLTrust 与 VAE 检测方法时强调的优势）",
    "不需要预训练检测器，Ĥ^t 每轮由 ΔW^t 与 ΔG^t 现场估计（§4.1、Algorithm 1）",
    "服务器需保存最近 N 轮的全局模型差与全局更新差，存储 O(Np)，p 为全局模型参数量（§4.3）",
    "公式 (3) 隐含需要保存每个客户端上一轮的更新 g_i^{t−1}，规模 n×p（论文未单列该开销；分析：）",
    "需要一个已部署的聚合规则产生 g^t，并在剔除后用 Byzantine-robust 规则（Krum / Trimmed-Mean / Median）重训（§3、§5.1）",
    "服务器被视为算力充足；客户端无额外计算与通信开销（§4.3）"
  ],
  "actions": ["exclude_client"],
  "dominant_cost": "服务器每轮一次 L-BFGS 估计与 Hessian 向量积 O(N^3+6Np)，加上对 n 个 p 维向量做预测与距离计算的 O(2np+Nn)，以及 Gap statistics 与 k-means 的 O(KBn^2)；论文给出的每轮总复杂度为 O(N^3+KBn^2+(6N+2n)p+Nn)，因 K、B、n、N 远小于 p 而总体对参数量 p 近似线性（§4.3）。分析：当 n=100、N=10 时 2n=200 大于 6N=60，预测与距离项的常数系数实际更大；全程不涉及任何反向传播或客户端额外计算。",
  "underspecified": [
    "Algorithm 1 第 2 行如何从 ΔW_t^T ΔG_t 取对角矩阵 D_t 与下三角子矩阵 L_t（是否严格下三角、是否对称化）论文未说明",
    "Algorithm 1 第 4 行 Cholesky 分解要求正定，分解失败或矩阵病态时的数值兜底论文未说明",
    "t < N（窗口未满）以及 t < 50 时可疑分与 ΔW^t、ΔG^t 的定义论文未说明",
    "Gap statistics 中 sd(k) 的公式在正文第 3 步与 Algorithm 2 中写法不一致，应以哪一版为准论文未澄清",
    "Gap 判据在 k = K 时需要 Gap(K+1) 与 s'_{K+1}，而 Algorithm 2 只计算到 K，边界处理论文未说明",
    "V_k 或 V*_{kb} 为 0 导致 log(0) 时如何处理论文未说明",
    "k-means 的初始化、迭代次数、随机种子、1 维可疑分上的距离度量与空簇处理论文未说明",
    "客户端上一轮未参与、g_i^{t−1} 缺失时的处理论文未说明（论文假设每轮全部客户端参与，§5.1）",
    "用于计算 Δg^t 的 g^t 是否为受攻击影响的聚合结果、是否要求特定聚合规则，论文未明确说明",
    "重启训练的具体方式（是否从 w^0 重新开始、历史缓冲是否清空、随机种子与总轮数是否重置、检测起始设置是否沿用）论文未说明",
    "检测触发当轮已聚合出的全局更新是否被丢弃、是否用于更新模型，论文未说明",
    "Table 3 的 No Attack 基线是用剩余 72% 良性客户端训练的（§5.2），复现对比时不能当作全客户端结果",
    "可疑分的窗口平均在客户端数 n 变化时是否需要重新校准，论文未说明"
  ],
  "quotes": [
    {
      "supports": "整体检测思路：良性客户端遵循 FL 算法、恶意客户端伪造更新，因而更新序列不一致",
      "text": "Our key intuition is that, benign clients calculate their model updates based on the FL algorithm and their local training data, while malicious clients craft the model updates instead of following the FL algorithm."
    },
    {
      "supports": "步骤 4：Δw^t 与 Δg^t 的定义，且 g^t 由客户端更新聚合而来",
      "text": "Specifically, we denote by Δ𝑤𝑡= 𝑤𝑡−𝑤𝑡−1 the global-model difference in iteration 𝑡, and we denote by Δ𝑔𝑡= 𝑔𝑡−𝑔𝑡−1 the global-model-update difference in iteration 𝑡, where the global model update is aggregated from the clients’ model updates."
    },
    {
      "supports": "步骤 5–6：用过去 N 轮的 ΔW^t、ΔG^t 经 L-BFGS 估计 Ĥ^t，具体实现见 Algorithm 1",
      "text": "Then, based on the L-BFGS algorithm, we can estimate Hˆ 𝑡using Δ𝑊𝑡and Δ𝐺𝑡. For simplicity, we denote by Hˆ 𝑡= L-BFGS(Δ𝑊𝑡, Δ𝐺𝑡). Algorithm 1 shows the specific implementation of L-BFGS algorithm in the experiments."
    },
    {
      "supports": "步骤 7：客户端更新预测公式 (3)",
      "text": "Based on the estimated Hessian Hˆ 𝑡, we predict a client 𝑖’s model update in iteration 𝑡as follows: 𝑔ˆ𝑡 𝑖= 𝑔𝑡−1 𝑖 + Hˆ 𝑡(𝑤𝑡−𝑤𝑡−1), (3) where 𝑔ˆ𝑡 𝑖is the predicted model update for client 𝑖in iteration 𝑡."
    },
    {
      "supports": "步骤 8–9：逐客户端 ℓ2 欧氏距离向量 d^t 与 ℓ1 归一化 d̂^t",
      "text": "We denote by 𝑑𝑡the vector of such 𝑛Euclidean distances for the𝑛clients in iteration𝑡, i.e.,𝑑𝑡= [∥𝑔ˆ𝑡 1−𝑔𝑡 1∥2, ∥𝑔ˆ𝑡 2−𝑔𝑡 2∥2, · · · , ∥𝑔ˆ𝑡𝑛− 𝑔𝑡𝑛∥2]. We normalize the vector 𝑑𝑡as 𝑑ˆ𝑡= 𝑑𝑡/∥𝑑𝑡∥1."
    },
    {
      "supports": "步骤 10：可疑分定义为最近 N 轮归一化距离的平均，N 为窗口大小",
      "text": "Finally, our suspicious score 𝑠𝑡 𝑖for client 𝑖in iteration 𝑡is the client’s average normalized Euclidean distance in the past 𝑁iterations, i.e., 𝑠𝑡 𝑖= 1 𝑁 ∑︁𝑁−1 𝑟=0 𝑑ˆ𝑡−𝑟 𝑖 . We call 𝑁 window size."
    },
    {
      "supports": "步骤 11–13：Gap statistics 判断簇数，k̂>1 时 k-means(k=2)，平均可疑分大的簇判为恶意",
      "text": "If the clients can be grouped into more than 1 cluster based on the Gap statistics, then we use 𝑘-means to divide the clients into 2 clusters based on their suspicious scores. Finally, the clients in the cluster with larger average suspicious score are classified as malicious."
    },
    {
      "supports": "步骤 14：判定触发即停止训练、剔除客户端并重启",
      "text": "When at least one client is classified as malicious in a certain iteration, the detection finishes, and the server removes the clients classified as malicious and restarts the training."
    }
  ]
}
```
