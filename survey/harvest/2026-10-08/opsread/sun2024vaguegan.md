# sun2024vaguegan：MCD（Model Consistency-Based Defense，基于模型一致性的防御）

说明：这篇论文同时提出了攻击方法 VagueGAN 与防御方法 MCD。按题目要求只拆论文自己提出的防御/检测方法，因此下面的流水线是 MCD（Sec. V-B 与 Algorithm 2、Algorithm 3）。VagueGAN 是同文提出的攻击，只在被评测的攻击配置中出现（κ=0.2、E=600，Sec. VI-A c(4) 与 Sec. VI-B），它不是 MCD 的组件；MCD 利用的是"GAN 输出一致性"这一攻击留下的统计性质，而不是攻击者的模型本身。

## 1. 方法一句话
MCD 的输入是服务器在联邦学习过程中已经收到的、每个可信客户端（trusted client）在最近 T′ 轮内上传的本地模型序列；输出是每个可信客户端的异常度 h_f,i 与"异常度超过阈值"从而被移出可信集合 C_tr 的恶意客户端名单，被剔除的客户端其后续更新不再被采纳（Sec. V-B Step 1–4；Sec. VI-E b) 对 Fig. 15 的说明）。MCD 不修改模型参数、不做加权、不做裁剪或加噪，只做客户端级的剔除判定。

## 2. 运行位置
MCD 完全在服务器端运行，客户端不参与检测计算：服务器收到更新后把本地模型留存下来（服务器收到更新），在每 T′ 轮的防御周期边界 t % T′ == 0 上做检测（Algorithm 3 第 2–3 行），从流程位置看相当于"聚合之后"的周期性钩子；检测结果 C_tr 反过来决定后续轮次"服务器聚合"时哪些客户端被信任。MCD 不需要客户端与服务器之间的额外往返，论文明确说它复用服务器为联邦聚合已经收集的本地模型、"operates without model collection overhead"（Sec. V-B 末）。论文没有说明在 t % T′ == 0 这一轮里，检测与该轮聚合谁先谁后。分析：由于 MCD 只在服务器已有数据上做统计，运行时不需要新的下行广播、也不需要客户端额外上传。

## 3. 算子流水线
按执行顺序如下，共 14 步。

**步骤 1：初始化可信集合（init_trusted_set）**
- 输入：全体客户端集合 C = {c1, c2, ..., cN}。
- 计算：C_tr ← C；防御周期编号 f ← 0。
- 输出：可信集合 C_tr（初始等于全体客户端）、周期编号 f。
- 出处：Sec. V-B Step 1；Algorithm 3 第 1 行与第 3 行（f = ⌊t/T′⌋）。

**步骤 2：周期门控（periodic_gate）**
- 输入：当前 FL 轮次 t；防御周期长度 T′。
- 计算：仅当 t % T′ == 0 时进入检测分支，并令 f = ⌊t/T′⌋；否则跳过整个检测。
- 输出：布尔门控信号与当前周期编号 f。
- 出处：Algorithm 3 第 2–3 行；Sec. V-B Step 1（"MCD runs periodically for every defense period of T ′ FL rounds"）。

**步骤 3：2 维 PCA 降维（pca_project）**
- 输入：客户端 ci 在轮次 t 上传的本地模型 θ_t,i，是一个 d 维参数向量（论文按本地模型整体处理，未按层拆分）。
- 计算：θ^(2)_t,i = PCA(θ_t,i)，把高维模型压到 2 维；论文在防御章节的表述为"take 2-dimensional models after dimensionality reduction by PCA as an example, but MCD is not limited to it"（Sec. V-B Step 1；同一形式在 Sec. IV-D 的攻击隐蔽性度量中记为式 (10)）。
- 输出：每个被处理模型的 2 维表示 θ^(2)_t,i ∈ R²。
- 出处：Sec. V-A；Sec. V-B Step 1；Algorithm 3 第 5 行。

**步骤 4：按客户端缓存本周期低维模型（client_model_buffer）**
- 输入：周期 f 内每一轮各可信客户端上传（即被服务器选中）的 2 维模型；若客户端 ci 在该轮没有被选中，则把 θ^(2)_t,i 置为 NULL。
- 计算：把整个周期内的 θ^(2)_t,i 汇成每个客户端一个集合 Q_f,i，f = 0,1,2,...。
- 输出：Q_f,i（每个可信客户端一个，长度至多 T′）。
- 出处：Sec. V-B Step 1；Algorithm 3 第 5 行、第 15 行（"remove Qf,i from Qf"）。

**步骤 5：质心度量（client_centroid）**
- 输入：Q_f,i 中的全部 2 维模型。
- 计算：θ̄^(2)_f,i = (Σ_{θ^(2)_t,i ∈ Q_f,i} θ^(2)_t,i) / |Q_f,i|，即单个客户端在该周期内所有上传模型的中心（式 (16)）。
- 输出：每个可信客户端一个 2 维质心 θ̄^(2)_f,i。
- 出处：式 (16)；Sec. V-B Step 1；Fig. 8(a)。

**步骤 6：足迹度量（client_mean_radius）**
- 输入：Q_f,i 与步骤 5 的 θ̄^(2)_f,i。
- 计算：d̄_f,i = (Σ_{θ^(2)_t,i ∈ Q_f,i} ‖θ^(2)_t,i − θ̄^(2)_f,i‖) / |Q_f,i|，即所有模型到质心的欧氏距离的平均值（论文称之为方差式的量）；论文用"以 θ̄^(2)_f,i 为圆心、d̄_f,i 为半径的圆形区域"作为该客户端模型分布的简化足迹。
- 输出：每个可信客户端一个标量 d̄_f,i。
- 出处：式 (17)；Sec. V-B Step 1；Fig. 8(a)。

**步骤 7：基线客户端集合的邻域筛选（neighborhood_filter）**
- 输入：全部可信客户端的度量对 (θ̄^(2)_f,i, d̄_f,i)；第一基线客户端（first baseline client）的度量 (θ̂^(2)_f, d̂_f)。
- 计算：第一基线客户端被认为 100% 安全、不受攻击，论文举例可由服务器自己充当该客户端训练一个本地模型；然后 C_base = { ci : ‖θ̄^(2)_f,i − θ̂^(2)_f‖ / d̂_f < Ω1 且 |d̄_f,i − d̂_f| / d̂_f < Ω2 }（式 (18) 与式 (19)）。
- 输出：基线客户端集合 C_base。
- 出处：Sec. V-B Step 2；式 (18)(19)；Algorithm 2 第 2–5 行；Algorithm 3 第 8 行。

**步骤 8：基线值求平均（baseline_mean）**
- 输入：C_base 中所有客户端的度量对。
- 计算：θ^base_f = (Σ_{θ̄^(2)_f,i ∈ C_base} θ̄^(2)_f,i) / |C_base|（式 (20)）；d^base_f = (Σ_{d̄_f,i ∈ C_base} d̄_f,i) / |C_base|（式 (21)）。
- 输出：质心基线 θ^base_f（2 维）与足迹基线 d^base_f（标量）。
- 出处：式 (20)(21)；Sec. V-B Step 2；Algorithm 2 第 3–4 行。

**步骤 9：归一化质心偏差项（normalized_centroid_deviation）**
- 输入：被测客户端的 θ̄^(2)_f,i、基线 θ^base_f、足迹基线 d^base_f。
- 计算：term1 = ‖θ̄^(2)_f,i − θ^base_f‖ / d^base_f（式 (22) 的第一部分，用 d^base_f 做尺度归一）。
- 输出：标量 term1。
- 出处：式 (22) 前半；Sec. V-B Step 3。

**步骤 10：足迹偏差项（absolute_footprint_deviation）**
- 输入：被测客户端的 d̄_f,i 与基线 d^base_f。
- 计算：term2 = |d^base_f − d̄_f,i|（式 (22) 的第二部分）。
- 输出：标量 term2。
- 出处：式 (22) 后半；Sec. V-B Step 3。

**步骤 11：加权得到客户端异常度（weighted_abnormality_score）**
- 输入：term1、term2。
- 计算：h_f,i = λ1 · (‖θ̄^(2)_f,i − θ^base_f‖ / d^base_f) + λ2 · (|d^base_f − d̄_f,i|)（式 (22)）。λ1、λ2 用来把量级不同的两项归一/配平。
- 输出：每个可信客户端的异常度 h_f,i，汇总为异常度集合 H_f。
- 出处：式 (22)；Sec. V-B Step 3；Algorithm 2 第 7–10 行；超参数取值见 Sec. VI-A d)(7)。

**步骤 12：按中位数放大得到阈值（median_scaled_threshold）**
- 输入：全部可信客户端的 h_f,i。
- 计算：h^med_f = median{h_f,i}；h^thr_f = δ · h^med_f，其中 δ ∈ (1, 3)（式 (23)）。
- 输出：本周期阈值 h^thr_f。
- 出处：式 (23)；Sec. V-B Step 4；Algorithm 3 第 11 行。

**步骤 13：剔除超阈值客户端（threshold_exclude_client）**
- 输入：H_f 与 h^thr_f，以及当前 C_tr。
- 计算：对所有 ci ∈ C_tr，若 h_f,i > h^thr_f，则把 ci 移出 C_tr，并把 Q_f,i 从 Q_f 中删除。
- 输出：更新后的 C_tr 与 Q_f。
- 出处：Sec. V-B Step 4；Algorithm 3 第 12–17 行、第 19 行。

**步骤 14：后续轮次聚合忽略被剔除客户端（exclude_from_aggregation）**
- 输入：更新后的 C_tr；服务器每轮随机选中的 K 个客户端。
- 计算：被判定为恶意的客户端，其后续更新被忽略（论文原文为"disregards their subsequent updates"）；C_tr 在后续轮次继续按周期被重新检查。
- 输出：后续聚合不再采纳已被剔除客户端的模型。
- 出处：Sec. VI-E b) 对 Fig. 15 的说明（long dashed line / short dashed line）；Sec. V-B Step 4。论文未说明被剔除者能否重新进入 C_tr。

## 4. 采样与规模控制
- 轮次（rounds）：MCD 不对每轮都做检测，而是每 T′ = 80 个 FL 轮执行一次防御周期（Sec. VI-A d)(7)）；Sec. V-B 末也表述为"defends every period of tens of training rounds rather than every round"。
- 参数坐标（coordinates）：用 PCA 把高维本地模型降到 2 维后再计算度量，论文明确这只是举例、"MCD is not limited to it"（Sec. V-A；Sec. V-B Step 1）。
- 客户端（clients）：只分析可信集合 C_tr 中的客户端；服务器每轮随机从 N 个客户端中选 K 个上传模型，未被选中的轮次在 Q_f,i 中记为 NULL（Sec. V-B Step 1）。主实验默认 N = 60、K = 10（Sec. VI-A b)）；MCD 的防御评测使用 N = 20、K = 5、T = 200（Sec. VI-E）。
- 参考数据或探针（samples / probes）：论文未使用。MCD 不访问任何本地样本，也不构造探针数据；唯一与数据相关的环节是第一基线客户端（论文说"for instance, the server acts as a such client to train a local model"），但它用什么数据、多少数据训练，论文未说明（Sec. V-B Step 2）。
- 层（layers）：论文未使用分层抽样；PCA 与两项度量都作用在整份模型参数向量上。

## 5. 超参数
- T′：防御周期长度（每多少 FL 轮执行一次 MCD）。取值 T′ = 80，出处 Sec. VI-A d)(7)；Sec. V-B 末只定性说"tens of training rounds"。
- λ1：式 (22) 第一项（质心偏差）的权重。取值 λ1 = 1，出处 Sec. VI-A d)(7)。
- λ2：式 (22) 第二项（足迹偏差）的权重。取值 λ2 = 2，出处 Sec. VI-A d)(7)；论文说明设这两个值是因为第一项量级略大于第二项，需要配平（Sec. V-B Step 3 与 Sec. VI-A d)(7)）。
- Ω1：C_base 的质心邻域约束常数，式 (18)。取值 Ω1 = 4，出处 Sec. VI-A d)(7)。
- Ω2：C_base 的足迹邻域约束常数，式 (19)。取值 Ω2 = 2，出处 Sec. VI-A d)(7)。
- δ：异常度阈值系数，h^thr_f = δ·h^med_f，式 (23)。论文只给范围 δ ∈ (1, 3)，实验用的具体取值论文未说明（Sec. V-B Step 4）。
- PCA 目标维数：2（Sec. V-A；Sec. V-B Step 1），论文称不限于此。
- 论文未给出的其他数量：基线客户端集合 C_base 的规模、第一基线客户端的个数（论文只说"The first baseline client can expand to multiple ones if possible"）、PCA 是否先做零均值/单位方差标准化（对 MCD 未说明）。
- 评测环境参数（不是 MCD 自身的超参数）：防御评测为 Fashion-MNIST、IID、α = 20%、N = 20、K = 5、T = 200（Sec. VI-E）；攻击侧 VagueGAN 使用 κ = 0.2、E = 600（Sec. VI-A c)(4) 与 Sec. VI-B）。

## 6. 判定与动作
判定规则是纯阈值规则，不是聚类：取全部可信客户端异常度的中位数 h^med_f，令阈值 h^thr_f = δ·h^med_f（δ ∈ (1,3)，式 (23)），凡 h_f,i > h^thr_f 的客户端被标记为恶意（Sec. V-B Step 4）。动作只有一种：把该客户端移出可信集合 C_tr，并从 Q_f 中删除其 Q_f,i（Algorithm 3 第 13–16 行）；论文进一步说明被识别出的恶意客户端"subsequent updates"被忽略（Sec. VI-E b)）。没有加权聚合公式、没有裁剪幅度、没有加噪幅度。跨轮行为：C_tr 与 Q_f 在每个周期结束时更新并在后续轮次继续使用（Algorithm 3 第 19 行），检测按周期反复执行（Fig. 15 中的 short dashed line 说明），但论文未说明被剔除客户端是否永久不能回到 C_tr。两个度量项的分工在实验中被明确区分：质心项对 label flipping、PoisonGAN、轻噪声等有效，而 VagueGAN 场景下恶意客户端在 θ̄^(2)_f,i 上不异常、只在 d̄_f,i 上显著偏低，因此足迹项是抓住 GAN 类攻击的关键（Sec. VI-E a) 与 Table III）。

## 7. 需要的外部资源
- 一个"第一基线客户端"的可信本地模型及其度量 (θ̂^(2)_f, d̂_f)：论文举例由服务器自己充当该客户端训练一个本地模型，该客户端被认为 100% 安全（Sec. V-B Step 2）。服务器训练它所用的数据、模型结构与规模，论文未说明。
- 由邻域筛选得到的基线客户端集合 C_base（式 (18)(19)），其规模论文未说明。
- 服务器为联邦聚合已经收集的本地模型，MCD 直接复用（Sec. V-B 末）。
- 论文没有要求干净参考数据集、根数据集、预训练检测器、对齐前后的权重，也没有要求除第一基线客户端模型之外的额外模型；MCD 也不需要攻击者的 VagueGAN 模型。
- 评测中另用到主任务测试集 D_test 计算全局准确率（Sec. III-A），但它不是 MCD 的输入。

## 8. 计算与存储开销
论文报告的开销都是定性的：MCD"operates without model collection overhead, since it directly reuses the local models already collected by the server for federated aggregation"；用抽取出的度量对代替原始高维模型以"greatly saves the storage space of the server"；使用轻量异常检测算法；以及每 T′（数十）轮才防御一次以避免服务器高负载（Sec. V-B 末的三条措施）。论文没有给出 MCD 的具体运行时间或存储占用数值；Fig. 13(a) 中 36 s 到 904 s 的时间数字是监督/无监督 VagueGAN 的训练开销，不是 MCD 的开销（Sec. VI-D）。分析：按流水线，主要开销集中在步骤 3 对高维模型做 PCA（每个防御周期一次，成本随模型维度 d 与可信客户端数 n 增长，大致为 O(d²)~O(d³) 量级的拟合加 O(n·d²) 的投影，标"分析："），以及步骤 5–6 对每个客户端至多 T′ 个 2 维点的均值与平均距离（O(n·T′)）；步骤 7–11 是 O(n) 级别的标量运算，可以忽略。存储上，如果服务器只保留 2 维投影则只需 O(n·T′) 个标量，但 PCA 需要以高维模型为输入，因此若在周期末统一拟合 PCA 就必须缓存 O(n·T′·d) 的高维模型，这与论文"用度量代替原始模型以省空间"的说法存在张力（论文未说明 PCA 是在线逐轮投影还是周期末批量拟合）。

## 9. 实现时容易错的地方
论文明确强调的实现细节：
- 未被服务器选中的轮次必须把 θ^(2)_t,i 置为 NULL，不能当成零向量参与统计（Sec. V-B Step 1）。
- 度量对 (θ̄^(2)_f,i, d̄_f,i) 是替代原始高维模型保存的，MCD 只在度量上做后续运算（Sec. V-B Step 1 末）。
- 式 (22) 的两项量级不同，必须用 λ1、λ2 配平；论文把这一点作为独立说明（Sec. V-B Step 3），实验取 λ1 = 1、λ2 = 2（Sec. VI-A d)(7)）。
- 阈值是 δ 乘中位数，而不是固定阈值或均值加若干倍标准差（式 (23)）。
- 两个度量项不能省掉任何一个：VagueGAN 攻击下质心项不异常、只有足迹项 d̄_f,i 偏低（Sec. VI-E a)；反之 label flipping 与轻噪声主要靠质心项（Table II）。
- 该方法成立的前提是攻击者"consistently applied"同一个 VagueGAN；论文在 Sec. V 开头与 Sec. VII 明确承认攻击者换成变化设置或自适应攻击后，MCD 依赖的模型一致性可能不再成立。

论文没说清、实现时必须自己决定的地方：
1. δ 的具体取值（只给 1 < δ < 3，Sec. V-B Step 4）。
2. 第一基线客户端由服务器用什么数据、什么模型结构训练，是否需要标签，规模多大（Sec. V-B Step 2）。
3. C_base 的期望规模，以及"第一基线客户端可扩展为多个"时的扩充规则（Sec. V-B Step 2）。
4. PCA 之前是否做零均值/单位方差标准化（PCA 基线方法里写了标准化，但那是被比较的基线而不是 MCD，Sec. VI-A d)(1) 与 Sec. V-A）；PCA 基是每周期重新拟合还是固定不变；拟合时是否把恶意客户端的模型也算进去——这些都会直接改变 θ̄^(2)_f,i 与 d̄_f,i 的数值。
5. |Q_f,i| 是否把 NULL 计入分母（式 (16)(17) 与 Sec. V-B Step 1 的 NULL 约定之间有歧义）。
6. 某个客户端在一个周期内一次都没被选中（Q_f,i 为空，式 (16)(17) 分母为零）时如何处理。
7. C_base 为空、或 d^base_f = 0/接近 0 时如何处理（式 (18)–(22) 会除零或让 term1 爆炸，论文没有给任何 ε 或兜底规则）。
8. 被剔除的客户端是从当轮聚合中就剔除，还是只从下一轮起不再进入 C_tr；论文只在 Sec. VI-E b) 说忽略其"subsequent updates"。
9. 被剔除客户端能否重新进入 C_tr（论文未说明）。
10. 公式编号在原文中有错位，必须按名字实现而不能按编号：Algorithm 3 第 5 行写"according to (15),(16)"但实际是式 (16)(17)；Algorithm 2 第 8 行与 Sec. V-B Step 3 正文把 h_f,i 写成按式 (21) 计算，实际对应式 (22)。
11. 在 t % T′ == 0 这一轮，检测与该轮模型聚合的先后顺序（Algorithm 3 未说明）。
12. MCD 在 non-IID 数据下的表现：Sec. VI-E 的防御实验是 Fashion-MNIST、IID；论文没有报告 MCD 在 non-IID 下的检测结果。
13. 恶意客户端比例较高时中位数 h^med_f 会被污染（论文实验只测到 α = 30%，Table IV），此时阈值行为论文未讨论。
14. PCA 在服务器端需要完整高维模型作为输入，是否真能像论文所说"以度量代替原始模型"从而省存储，取决于投影时机，论文未说明（见第 8 节分析）。

## 10. 原文依据
1. 支撑步骤 2 与步骤 4（防御周期与按客户端缓存）："MCD runs periodically for every defense period of T ′ FL rounds for local model analysis. In each defense period, MCD stores a set Qf,i of low-dimensional local models uploaded by every trusted client"
2. 支撑步骤 3（降维到 2 维）："To better analyze the local models, we use PCA to reduce the high-dimensional models to 2-dimensional ones to extract the most useful information."
3. 支撑步骤 4（未选中轮次置 NULL）："In our FL system, the server randomly selects K out of N clients per round for model aggregation, so θ(2) t,i ∈ Qf,i is set to NULL if client ci is not selected in round t."
4. 支撑步骤 6（足迹度量的定义）："where ¯df,i is the mean of the Euclidean distances, i.e., variances, of all models from the centroid ¯θ(2) f,i"
5. 支撑步骤 7（第一基线客户端）："Firstly, MCD maintains a first baseline client (for instance, the server acts as a such client to train a local model). This client is considered 100% secure and immune to attacks"
6. 支撑步骤 7（C_base 的邻域约束）："Secondly, MCD defines Cbase as the set of baseline clients whose model metrics are within a neighborhood of those of the first baseline client. Two constants Ω1, Ω2 are used to define the size of the neighborhood"
7. 支撑步骤 11（两项加权与量级配平）："The first half and the second half of Eq. (21) are not of the same order of magnitude. λ1 and λ2 are used to normalize the two parts."
8. 支撑步骤 12 与步骤 13（阈值与剔除动作）："MCD then marks every client with a client abnormality value larger than the threshold as a malicious client. If MCD detects a malicious client, it will be removed from the trusted client set Ctr."

```json
{
  "key": "sun2024vaguegan",
  "method": "MCD (Model Consistency-Based Defense，基于模型一致性的防御)",
  "stages": ["server_receive", "server_aggregate", "server_post_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "初始化可信客户端集合 C_tr 与周期编号 f",
      "operator": "init_trusted_set",
      "input": "全体客户端集合 C = {c1, ..., cN}",
      "output": "C_tr = C；f = 0",
      "params": {},
      "source": "Sec. V-B Step 1；Alg. 3 第 1、3 行"
    },
    {
      "step": "周期门控，仅当 t % T′ == 0 时执行检测",
      "operator": "periodic_gate",
      "input": "当前 FL 轮次 t；防御周期 T′",
      "output": "进入/跳过检测；f = floor(t / T′)",
      "params": {"T_prime": 80, "T_prime_source": "Sec. VI-A d)(7)"},
      "source": "Alg. 3 第 2–3 行；Sec. V-B Step 1"
    },
    {
      "step": "对上传的本地模型做 2 维 PCA 降维",
      "operator": "pca_project",
      "input": "客户端 ci 第 t 轮上传的本地模型 θ_t,i ∈ R^d",
      "output": "θ^(2)_t,i ∈ R^2",
      "params": {"n_components": 2, "standardize": "论文未说明"},
      "source": "Sec. V-A；Sec. V-B Step 1；Alg. 3 第 5 行"
    },
    {
      "step": "按客户端缓存本防御周期的低维模型集合 Q_f,i",
      "operator": "client_model_buffer",
      "input": "周期内每轮各可信客户端（被选中时）的 2 维模型",
      "output": "每个可信客户端的集合 Q_f,i，未选中轮次记 NULL",
      "params": {"T_prime": 80, "missing_policy": "NULL"},
      "source": "Sec. V-B Step 1；Alg. 3 第 5、15 行"
    },
    {
      "step": "计算质心度量 θ̄^(2)_f,i",
      "operator": "client_centroid",
      "input": "Q_f,i 中的 θ^(2)_t,i",
      "output": "每个客户端的 2 维质心 θ̄^(2)_f,i",
      "params": {},
      "source": "式 (16)；Sec. V-B Step 1；Fig. 8(a)"
    },
    {
      "step": "计算足迹度量 d̄_f,i（到质心的平均欧氏距离）",
      "operator": "client_mean_radius",
      "input": "Q_f,i 与 θ̄^(2)_f,i",
      "output": "每个客户端一个标量 d̄_f,i",
      "params": {},
      "source": "式 (17)；Sec. V-B Step 1；Fig. 8(a)"
    },
    {
      "step": "用第一基线客户端的度量做邻域筛选得到 C_base",
      "operator": "neighborhood_filter",
      "input": "全部可信客户端的 (θ̄^(2)_f,i, d̄_f,i)；第一基线客户端度量 (θ̂^(2)_f, d̂_f)",
      "output": "基线客户端集合 C_base",
      "params": {"Omega1": 4, "Omega2": 2, "Omega_source": "Sec. VI-A d)(7)"},
      "source": "式 (18)(19)；Sec. V-B Step 2；Alg. 2 第 2–5 行；Alg. 3 第 8 行"
    },
    {
      "step": "对 C_base 的度量求平均得到两个基线值",
      "operator": "baseline_mean",
      "input": "C_base 中所有客户端的 (θ̄^(2)_f,i, d̄_f,i)",
      "output": "θ^base_f ∈ R^2；d^base_f ∈ R",
      "params": {},
      "source": "式 (20)(21)；Sec. V-B Step 2；Alg. 2 第 3–4 行"
    },
    {
      "step": "计算归一化质心偏差项",
      "operator": "normalized_centroid_deviation",
      "input": "θ̄^(2)_f,i，θ^base_f，d^base_f",
      "output": "term1 = ‖θ̄^(2)_f,i − θ^base_f‖ / d^base_f",
      "params": {},
      "source": "式 (22) 第一项；Sec. V-B Step 3"
    },
    {
      "step": "计算足迹偏差项",
      "operator": "absolute_footprint_deviation",
      "input": "d̄_f,i 与 d^base_f",
      "output": "term2 = |d^base_f − d̄_f,i|",
      "params": {},
      "source": "式 (22) 第二项；Sec. V-B Step 3"
    },
    {
      "step": "加权求和得到客户端异常度 h_f,i",
      "operator": "weighted_abnormality_score",
      "input": "term1、term2",
      "output": "每个可信客户端的异常度 h_f,i，汇总为 H_f",
      "params": {"lambda1": 1, "lambda2": 2, "lambda_source": "Sec. VI-A d)(7)"},
      "source": "式 (22)；Sec. V-B Step 3；Alg. 2 第 7–10 行"
    },
    {
      "step": "以中位数为基准计算异常阈值",
      "operator": "median_scaled_threshold",
      "input": "全部可信客户端的 h_f,i",
      "output": "h^med_f；h^thr_f = δ · h^med_f",
      "params": {"delta_range": "(1, 3)", "delta_value": "论文未说明"},
      "source": "式 (23)；Sec. V-B Step 4；Alg. 3 第 11 行"
    },
    {
      "step": "剔除异常度超过阈值的客户端并更新可信集合",
      "operator": "threshold_exclude_client",
      "input": "h_f,i、h^thr_f、当前 C_tr",
      "output": "更新后的 C_tr；从 Q_f 中删除该客户端的 Q_f,i",
      "params": {},
      "source": "Sec. V-B Step 4；Alg. 3 第 12–17、19 行"
    },
    {
      "step": "后续轮次聚合忽略被剔除客户端的更新",
      "operator": "exclude_from_aggregation",
      "input": "更新后的 C_tr；每轮被服务器随机选中的 K 个客户端及其模型",
      "output": "被标记客户端的后续更新不再被采纳",
      "params": {},
      "source": "Sec. VI-E b) 对 Fig. 15 的说明"
    }
  ],
  "sampling": [
    {"what": "rounds", "how": "不是每轮检测，而是每 T′ 轮执行一次防御周期，仅在 t % T′ == 0 时进入检测分支", "size": "T′ = 80（Sec. VI-A d)(7)）；Sec. V-B 末称“every period of tens of training rounds”"},
    {"what": "coordinates", "how": "用 PCA 把高维本地模型降到 2 维后再计算度量，论文称“MCD is not limited to it”", "size": "2 维（Sec. V-A；Sec. V-B Step 1）"},
    {"what": "clients", "how": "只分析可信集合 C_tr；服务器每轮随机从 N 中选 K 个客户端，未被选中的轮次在 Q_f,i 中记 NULL", "size": "默认 N = 60、K = 10（Sec. VI-A b)）；MCD 防御评测 N = 20、K = 5（Sec. VI-E）"},
    {"what": "samples", "how": "论文未使用；MCD 不接触任何本地样本，也不额外构造参考数据", "size": "论文未使用"},
    {"what": "probes", "how": "论文未使用；唯一与数据相关的环节是由服务器充当第一基线客户端训练一个本地模型，其数据与规模论文未说明", "size": "论文未说明"},
    {"what": "layers", "how": "论文未使用；PCA 与两项度量都作用在整份模型参数向量上，未按层抽样", "size": "论文未使用"}
  ],
  "resources": [
    "第一基线客户端的一个 100% 可信本地模型及其度量 (θ̂^(2)_f, d̂_f)，论文举例由服务器自己训练，所用数据与模型结构论文未说明（Sec. V-B Step 2）",
    "由式 (18)(19) 邻域筛选得到的基线客户端集合 C_base，规模论文未说明（Sec. V-B Step 2）",
    "服务器为联邦聚合已经收集的本地模型（MCD 直接复用，不额外收集；Sec. V-B 末）",
    "不需要干净参考数据集、根数据集、预训练检测器、对齐前后权重或额外检测模型；也不需要攻击者的 VagueGAN 模型",
    "评测用主任务测试集 D_test 仅用于计算全局准确率，不是 MCD 的输入（Sec. III-A）"
  ],
  "actions": ["exclude_client"],
  "dominant_cost": "分析：主要开销来自每个防御周期对可信客户端高维本地模型做 PCA（约 O(d^2)~O(d^3) 拟合加 O(n·d^2) 投影，随模型维度 d 与可信客户端数 n 增长），其次是每个客户端至多 T′ 个 2 维点的均值与平均距离统计 O(n·T′)；式 (18)–(22) 是 O(n) 标量运算。论文未报告 MCD 的具体运行时或存储数值，只给定性说明：复用聚合已收集的模型、以抽取度量代替原始高维模型、每 T′ 轮才防御一次（Sec. V-B 末）；Fig. 13(a) 的 36–904 s 是监督/无监督 VagueGAN 的训练时间，不是 MCD 开销（Sec. VI-D）。",
  "underspecified": [
    "δ 的具体取值：论文只给 δ ∈ (1, 3)，未给实验所用数值（Sec. V-B Step 4）",
    "第一基线客户端由服务器用什么数据、什么模型结构训练，是否需要标签，规模多大（Sec. V-B Step 2）",
    "C_base 的规模，以及“第一基线客户端可扩展为多个”时的扩充规则（Sec. V-B Step 2）",
    "PCA 之前是否做零均值/单位方差标准化（PCA 基线写了标准化，MCD 未说明）；PCA 基是每周期重拟合还是固定；拟合是否包含恶意客户端（Sec. V-A、Sec. V-B Step 1）",
    "式 (16)(17) 中 |Q_f,i| 是否把 NULL 计入分母（与 Sec. V-B Step 1 的 NULL 约定存在歧义）",
    "某客户端在一个周期内一次都未被选中、Q_f,i 为空时分母为零的处理（论文未说明）",
    "C_base 为空或 d^base_f 为 0/接近 0 时式 (18)–(22) 的除零与数值稳定性处理（论文未给 ε 或兜底规则）",
    "被剔除客户端是否从当轮聚合就排除，还是只从下一轮起不再进入 C_tr（论文只写移出 C_tr，并在 Sec. VI-E b) 说忽略其后续更新）",
    "被剔除客户端能否重新进入 C_tr（论文未说明）",
    "公式编号错位：Alg. 3 第 5 行的“(15),(16)”实际应为式 (16)(17)，Alg. 2 第 8 行与 Sec. V-B Step 3 正文的“(21)”实际应为式 (22)，实现时必须按公式名字而非编号",
    "在 t % T′ == 0 这一轮，检测与该轮聚合的先后顺序（Alg. 3 未说明）",
    "non-IID 设置下 MCD 的检测表现：Sec. VI-E 的防御实验为 Fashion-MNIST、IID，论文未报告 non-IID 结果",
    "恶意比例较高时中位数 h^med_f 被污染的情形：实验只测到 α = 30%（Table IV），更极端情形未讨论",
    "攻击者采用变化或自适应 VagueGAN 时 MCD 的鲁棒性：论文在 Sec. V 开头与 Sec. VII 明确承认未验证"
  ],
  "quotes": [
    {"supports": "步骤 2 与步骤 4：按 T′ 轮防御周期运行并按客户端缓存低维模型", "text": "MCD runs periodically for every defense period of T ′ FL rounds for local model analysis. In each defense period, MCD stores a set Qf,i of low-dimensional local models uploaded by every trusted client"},
    {"supports": "步骤 3：对本地模型做 2 维 PCA 降维", "text": "To better analyze the local models, we use PCA to reduce the high-dimensional models to 2-dimensional ones to extract the most useful information."},
    {"supports": "步骤 4：未被选中的轮次在 Q_f,i 中置 NULL", "text": "In our FL system, the server randomly selects K out of N clients per round for model aggregation, so θ(2) t,i ∈ Qf,i is set to NULL if client ci is not selected in round t."},
    {"supports": "步骤 6：足迹度量是到质心的平均欧氏距离", "text": "where ¯df,i is the mean of the Euclidean distances, i.e., variances, of all models from the centroid ¯θ(2) f,i"},
    {"supports": "步骤 7：第一基线客户端及其 100% 可信假设", "text": "Firstly, MCD maintains a first baseline client (for instance, the server acts as a such client to train a local model). This client is considered 100% secure and immune to attacks"},
    {"supports": "步骤 7：C_base 的 Ω1、Ω2 邻域约束", "text": "Secondly, MCD defines Cbase as the set of baseline clients whose model metrics are within a neighborhood of those of the first baseline client. Two constants Ω1, Ω2 are used to define the size of the neighborhood"},
    {"supports": "步骤 11：式 (22) 两项量级不同，用 λ1、λ2 配平", "text": "The first half and the second half of Eq. (21) are not of the same order of magnitude. λ1 and λ2 are used to normalize the two parts."},
    {"supports": "步骤 12 与步骤 13：阈值判定与移出可信集合的动作", "text": "MCD then marks every client with a client abnormality value larger than the threshold as a malicious client. If MCD detects a malicious client, it will be removed from the trusted client set Ctr."}
  ]
}
```
