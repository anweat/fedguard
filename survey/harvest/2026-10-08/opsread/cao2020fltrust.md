# cao2020fltrust：FLTrust

## 1. 方法一句话

FLTrust 是服务提供方（service provider）自己收集一小份干净训练数据（root dataset，根数据集）并维护一个服务器模型（server model），每轮全局迭代中，服务器先用自己的根数据集算出一个服务器模型更新（server model update）g0，再对每个客户端的本地模型更新（local model update）gi 计算它与 g0 的余弦相似度并做 ReLU 截断得到信任分（trust score，TS），把所有本地更新的 ℓ2 范数缩放到与 g0 相同，最后按信任分加权平均得到全局模型更新 g，并用 w ← w + α·g 更新全局模型（公式 (2)–(5)，Algorithm 2）。它输出的是每轮被改动后的全局模型，而不是一个"是否恶意"的硬判定：判定被软化成信任分，恶意方向（余弦 ≤ 0）的更新权重被置 0，恶意放大（magnitude 放大）的更新被范数对齐消解。

## 2. 运行位置

- **服务器下发前（server_distribute）**：服务器随机采样 τ 个客户端并把当前全局模型 w 发给他们（Algorithm 2 第 4 行；Section II-A 的 Step I）。
- **客户端每个训练步（client_step）**：被选中的每个客户端以 w 为初始化，用本地数据 Di 做 Rl 次带批大小 b、局部学习率 β 的随机梯度下降（Algorithm 1 第 2–5 行；Algorithm 2 第 8 行）。
- **客户端上传前（client_post_train）**：客户端返回的是更新量 gi = w_R − w，而不是本地模型本身；论文注明发送本地模型与其更新在算法上等价（Section II-A 脚注 1）。
- **服务器收到更新（server_receive）**：服务器在 Step II 的服务器侧用同一轮的 w 与根数据集 D0 计算 g0 = ModelUpdate(w, D0, b, β, Rl)。这一步不依赖任何客户端更新，可以与客户端训练并行执行，但必须在聚合前完成（Algorithm 2 第 11–12 行）。
- **服务器聚合（server_aggregate）**：对每个 gi 计算 ci、TSi = ReLU(ci) 与 ḡi，再按信任分加权平均得到 g（Algorithm 2 第 14–18 行）。
- **聚合之后（server_post_aggregate）**：w ← w + α·g，进入下一轮（Algorithm 2 第 19 行，公式 (5)）。
- **训练之外（outside_training）**：根数据集的收集与手工标注发生在训练之前，由服务提供方完成（Section III、Section VI-A-5）。

**是否需要额外往返**：不需要。客户端侧的流程与 FedAvg 完全一致，论文把"不增加客户端计算与通信开销"作为效率目标（Efficiency goal，Section III），并在 Section VI-B 报告 FLTrust 的收敛速度与 FedAvg 相同（Figure 3）。

## 3. 算子流水线

**步骤 1：本轮客户端采样与全局模型下发**
- 输入：全局模型 w（d 维参数向量）、客户端集合 {1, 2, …, n}。
- 计算：从 n 个客户端中随机采样 τ 个，记为 C1, …, Cτ，把 w 发给他们（Algorithm 2 第 4 行）。论文默认 τ = n（Section VI-A-4）。
- 输出：被选中客户端持有的 w 副本。
- 出处：Algorithm 2 第 4 行；Section II-A Step I；Section VI-A-4。

**步骤 2：客户端本地 SGD（ModelUpdate）**
- 输入：全局模型 w；客户端本地训练集 Di；批大小 b；局部学习率 β；局部迭代次数 Rl。
- 计算：w0 ← w；对 r = 1, 2, …, R 循环：从 D 中随机采样一个批 Db，wr ← wr−1 − β∇Loss(Db; w)；返回 wR − w（Algorithm 1 第 1–6 行）。即标准的逐样本/逐批梯度下降，产出的是"更新"而非"模型"。
- 输出：每个客户端的展平更新 gi（τ 个 d 维向量，n×d 或 τ×d 的矩阵）。
- 出处：Algorithm 1 第 1–6 行；Algorithm 2 第 7–10 行；Section IV-C。

**步骤 3：服务器在根数据集上做同构 SGD，得到参考更新 g0**
- 输入：同一轮的全局模型 w；根数据集 D0；与客户端相同的 b、β、Rl。
- 计算：g0 = ModelUpdate(w, D0, b, β, Rl)，即完全复用 Algorithm 1 在 D0 上跑 Rl 步 SGD，返回 w_R − w。论文称这是"服务器像客户端维护本地模型一样维护服务器模型"（Section IV-A）。
- 输出：服务器模型更新 g0（d 维）。
- 出处：Algorithm 2 第 12 行；Section IV-A；Section IV-C。

**步骤 4：余弦相似度打分**
- 输入：τ 个本地更新 gi 与服务器更新 g0（都是 d 维）。
- 计算：ci = ⟨gi, g0⟩ / (||gi||·||g0||)，即两个更新向量的夹角余弦；⟨·,·⟩ 为内积，||·|| 为 ℓ2 范数。论文用它衡量"方向相似度"。
- 输出：每个被选中客户端一个标量 ci ∈ [−1, 1]。
- 出处：公式 (2) 中 ci 的定义；Algorithm 2 第 15 行；Section IV-B"ReLU-clipped cosine similarity based trust score"。

**步骤 5：ReLU 截断成信任分**
- 输入：ci。
- 计算：TSi = ReLU(ci)，其中 ReLU(x) = x（当 x > 0），否则为 0（公式 (2) 及其后的 ReLU 定义）。论文明确说这一步是为了把方向相反的更新排除出聚合。
- 输出：非负信任分 TSi ≥ 0。
- 出处：公式 (2)；Algorithm 2 第 15 行；Section IV-B。

**步骤 6：范数对齐（投影到服务器更新所在的超球面）**
- 输入：gi 与其范数 ||gi||、服务器更新的范数 ||g0||。
- 计算：ḡi = (||g0|| / ||gi||) · gi，即保持方向、把长度改为 ||g0||。论文强调这会同时"放大"幅度小的更新，其直觉是幅度小的更新更可能来自良性客户端（Section IV-B）。
- 输出：归一化后的本地更新 ḡi，满足 ||ḡi|| = ||g0||。
- 出处：公式 (3)；Algorithm 2 第 16 行；Section IV-B。

**步骤 7：信任分加权平均**
- 输入：τ 个 (TSi, ḡi) 对。
- 计算：g = (1 / Σ_{j} TS_{Cj}) · Σ_{i} TS_{Ci} · ḡ_{Ci}（Algorithm 2 第 18 行）。注意权重只来自信任分，不乘客户端样本数 |Di|（对比 FedAvg 的 |Di|/N 加权）。论文在 Section V-B 公式 (7) 给出等价写法：令 ei = gi/||gi||，则 g = ||g0|| · Σ_i [ReLU(ci) / Σ_j ReLU(cj)] · ei，实现时可先单位化再缩放。正文公式 (4) 把同一式子展开为 g = [1/Σ_j ReLU(cj)] Σ_i ReLU(ci)·(||g0||/||gi||)·gi（抽取文本中该行的分母排版含一个多余的 n，与 Algorithm 2 第 18 行不一致，见第 9 节）。
- 输出：全局模型更新 g（d 维）。
- 出处：公式 (4)；公式 (7)；Algorithm 2 第 18 行；Section IV-B"Aggregating the local model updates"。

**步骤 8：全局模型更新**
- 输入：当前全局模型 w、全局更新 g、全局学习率 α。
- 计算：w ← w + α·g（论文把 α·β 当作单一组合学习率使用，因为默认 Rl = 1）。
- 输出：新的全局模型 w，作为下一轮的输入。
- 出处：公式 (5)；Algorithm 2 第 19 行；Section VI-A-4。

## 4. 采样与规模控制

- **客户端抽样**：每轮从 n 个客户端中随机采样 τ 个（Algorithm 2 第 4 行）；论文默认 τ = n，即每轮选择全部客户端（Section VI-A-4、Table I）。具体抽样是否有放回，论文未说明。
- **轮次**：固定全局迭代数 Rg，没有逐轮抽样或早停。取值（Section VI-A-4、Table I）：MNIST-0.1、MNIST-0.5、CH-MNIST 为 2,000；Fashion-MNIST 为 2,500；CIFAR-10 为 1,500；HAR 为 1,000。
- **本地迭代数**：Rl = 1（Section VI-A-4、Table I）。
- **参考数据量（探针）**：服务器根数据集 |D0| 默认 100 条（Table I、Section VI-A-5）；Figure 4 把它从 50 扫到 500。根数据集自身的采样方式分两种（Section VI-A-5）：Case I 从各客户端干净本地数据的并集中均匀随机采样；Case II 以 bias probability 的概率从某一类（实验中为类 1）采样、其余从其他类均匀采样，bias probability 在 Table V 中从 0.1（或 HAR 的 0.17、CH-MNIST 的 0.125，即退化为均匀）扫到 1.0。无论哪种情况，被采入根数据集的样本都从客户端的本地训练数据中剔除。
- **批大小**：b = 32（除 CIFAR-10 用 64），同时用于客户端和服务器（Section VI-A-4、Table I）。
- **层、参数坐标、维度**：论文未使用任何逐层或逐坐标的采样、裁剪或降维；相似度与归一化都作用在展平后的整个更新向量上（公式 (2)、(3)）。
- **跨轮记忆**：论文未使用；信任分只在当轮计算（Algorithm 2 第 14–18 行位于 r 循环内）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
| --- | --- | --- | --- |
| n | 客户端总数 | 100（MNIST-0.1、MNIST-0.5、Fashion-MNIST、CIFAR-10）；30（HAR）；40（CH-MNIST） | Table I；Section VI-A-4 |
| τ | 每轮选中的客户端数 | τ = n（全部） | Table I；Section VI-A-4 |
| Rl | 客户端/服务器的局部迭代数 | 1 | Table I；Section VI-A-4 |
| Rg | 全局迭代数 | 2,000（MNIST-0.1、MNIST-0.5、CH-MNIST）；2,500（Fashion-MNIST）；1,500（CIFAR-10）；1,000（HAR） | Table I；Section VI-A-4 |
| b | 批大小 | 32；CIFAR-10 为 64 | Table I；Section VI-A-4 |
| α·β | 组合学习率（Rl = 1 时只有乘积有意义） | Table I 该行列出 3×10⁻⁴、6×10⁻³、2×10⁻⁴、3×10⁻³、3×10⁻⁴（其中一项注明在第 1500 与 1750 轮以因子 0.9 衰减）；正文只说"我们在每个数据集上设置该组合学习率以取得小的训练误差与快速收敛"，抽取文本未给出各数据集与数值的一一对应 | Table I；Section VI-A-4；Appendix A |
| \|D0\| | 根数据集大小 | 默认 100；Figure 4 扫描 50、100、200、300、500 | Table I；Section VI-A-5；Figure 4 |
| bias probability | Case II 中根数据集偏向类 1 的比例 | 0.1、0.2、0.4、0.6、0.8、1.0（HAR 从 0.17 起，CH-MNIST 从 0.125 起） | Table V；Section VI-A-5 |
| m/n | 恶意客户端比例（评测设置，不是防御参数） | 默认 20% | Table I；Section VI-A-4 |
| f、k | Krum 与 Trim-mean 的参数（基线方法） | f = k = m | Section VI-A-4 |

论文没有给出防御自身的阈值超参数（没有剔除阈值、没有聚类参数），信任分是连续软权重。作为对照，自适应攻击侧（不是防御超参）使用 σ² = 0.5、γ = 0.005、η = 0.01、V = Q = 10（Section VI-A-2），Scaling 攻击的缩放因子 λ = n（Section VI-A-2）。

## 6. 判定与动作

- **判定规则**：没有硬阈值、没有聚类、没有显式剔除名单。唯一的"判定"是 TSi = ReLU(ci)：当本地更新与服务器更新的余弦 ≤ 0 时，该客户端的权重被置 0，等价于从加权平均的分子中被排除；论文原话是"we exclude such local model updates from the aggregation by clipping the cosine similarity"（Section IV-B）。余弦为正时权重正比于余弦值，方向越接近服务器更新权重越大。
- **加权公式**：g = (1/Σ_j TS_j)·Σ_i TSi·ḡi，其中 ḡi = (||g0||/||gi||)·gi（公式 (3)、(4)；Algorithm 2 第 16、18 行）。权重只按信任分，不按本地样本数。
- **裁剪幅度**：不把更新裁剪到某个固定范数，而是把每个更新的 ℓ2 范数对齐到当轮的 ||g0||；因此归一化幅度随轮次变化，由服务器更新决定。论文同时指出这会放大幅度小的更新（Section IV-B）。
- **加噪**：论文未使用任何加噪。
- **跨轮累积**：论文未使用；信任分每轮重新计算，服务器不记忆历史信任（Algorithm 2 第 14–18 行在每轮循环内）。
- **更新动作**：w ← w + α·g（公式 (5)），不是替换全局模型、不是对客户端做剔除，而是对每一轮聚合结果做加权融合。
- **边界**：若当轮所有 TSi 都为 0，公式 (4)/Algorithm 2 第 18 行的分母为 0，论文未说明如何处理（见第 9 节）。

## 7. 需要的外部资源

- **干净根数据集 D0**：服务提供方自己收集并手工标注，要求不含投毒；默认 100 条，最小可用规模论文报告为 100 条（Section III、Section VI-A-5、Section VI-B）。根数据集分布可以与整体训练分布不同，但偏离不能太大（Section VI-A-5 的 Case I/II 与 Table V）。
- **服务器模型**：与全局模型同架构的一份额外模型副本，由 Algorithm 1 在 D0 上从当前全局模型微调得到；不是预训练检测器（Section IV-A、Algorithm 2 第 12 行）。
- **全局模型 w 及其维度 d**：定理 1 的界同时依赖 |D0| 与 d（Theorem 1、Appendix A）。
- **数据隔离**：被采入根数据集的样本要从客户端本地训练数据中剔除（Section VI-A-5）。
- **不需要**：客户端侧的额外模型、额外数据或额外通信；不需要对齐前后的权重、不需要额外网络、不需要知道恶意客户端数量（Section III"Defender's knowledge and capability"）。论文承认该方法对"根数据集本身被投毒"不鲁棒（Section VII）。

## 8. 计算与存储开销

- **论文报告的开销**（Section VI-B）：FLTrust 在每轮不给客户端带来任何额外开销；相对 FedAvg，服务器额外做的是"计算一次服务器模型更新、计算信任分、归一化本地更新"，论文称这些对强大的服务器来说可以忽略。Figure 3 显示 FLTrust 的收敛速度与 FedAvg 相同，因此也不增加客户端与服务器之间的通信成本。作为对比，论文指出 Krum 需要在每轮计算本地更新之间的两两距离，客户端数大时服务器开销显著（Section III、Section VI-B）。
- **分析（论文未逐项给出 FLOPs）**：主要开销来自步骤 3 在根数据集上的一次完整本地训练，量级是每轮 Rl × |D0| / b 次前向与反向传播（即每条根样本在每个局部迭代被使用一次），随 |D0|、Rl 线性增长；步骤 4–6 的余弦、ReLU 与范数缩放各是 O(τ·d)，即随被选客户端数与参数量线性增长。存储上服务器只需多保存一份模型（服务器模型）与根数据集（默认 100 条），客户端存储不变。
- **理论开销相关量**：Theorem 1 的收敛界含 12αΔ₁/ρ，其中 Δ₁ = σ₁√(2/|D0|)·√(d log 6 + log(3/δ))，即根数据集越大、维度 d 越小时界越紧（Theorem 1、Appendix A）。论文明确该定理假设 Rl = 1、β = 1，且 Lemma 2 取 α = μ/(2L²)。

## 9. 实现时容易错的地方

论文明确强调的：

1. **ReLU 不能省**：FLTrust-NoReLU 变体在 MNIST-0.5 上没有攻击时测试错误率就升到 0.28，各攻击下升到 0.90–0.94（Table IV）。原因是余弦为负的更新仍会反向拉动全局模型（Section IV-B、Section VI-B）。
2. **全量归一化优于部分归一化**：只把"范数大于 ||g0||"的更新缩小的 FLTrust-ParNorm 在 Scaling 攻击下错误率/攻击成功率是 0.06/0.01，而全量归一的 FLTrust 是 0.05/0.00（Table IV）。不能只做单边裁剪。
3. **不要把服务器更新当作信任分为 1 的一项并入加权平均**：FLTrust-withServer 变体因根数据集小而变差，自适应攻击下错误率升到 0.94（Table IV；Section IV-B 也明确讨论了这个变体的负面效果）。
4. **服务器更新必须用同一轮的 w 与相同的 b、β、Rl 计算**：Algorithm 2 第 8 行与第 12 行用的是同一组参数；不能用上一轮的 g0 复用。
5. **函数内返回的是更新而不是模型**：ModelUpdate 返回 wR − w（Algorithm 1 第 6 行）；服务器聚合的是更新向量，最后才做 w ← w + α·g（第 19 行）。
6. **加权平均的分母是信任分之和，不是客户端数，也不乘 |Di|**：Algorithm 2 第 18 行是 1/Σ_j TS_Cj，与 FedAvg 的 |Di|/N 加权不同；抽取文本中公式 (4) 该处分母排版含一个多余的 n，与 Algorithm 2 第 18 行矛盾，必须以 Algorithm 2 与"weighted average"的文字描述为准。
7. **根数据集必须干净且从客户端训练数据中剔除**：论文承认对中毒根数据集不鲁棒（Section VI-A-5、Section VII）。
8. **分布偏移容忍有限**：根数据集 bias probability 超过约 0.4 后，FLTrust 在多数数据集上退化（Table V）；论文没有给出自动检测分布偏移的手段。

论文没说清、实现时必须自己决定的：

1. **分母为 0 的情况**：当所有被选客户端的 TSi 都为 0 时，公式 (4)/Algorithm 2 第 18 行出现 0/0，论文未说明（例如是否跳过该轮、是否退回 FedAvg、是否给 g0 自身权重）。
2. **||gi|| = 0 或 ||g0|| = 0 的除零**：公式 (3) 与公式 (2) 都要求范数非零，论文未说明如何保护（例如加 ε）。极小范数导致方向估计噪声大，论文也未讨论。
3. **客户端采样方式**：Algorithm 2 只写"随机采样"，未说明有放回/无放回，也未说明是否按权重采样。
4. **Algorithm 1 的批采样细节**：只写"Randomly sample a batch Db from D"，未说明是否有放回、是否按 epoch 打乱、最后不足一个 batch 是否丢弃。
5. **Rl > 1 时 α 与 β 如何拆分**：论文只说明 Rl = 1 时只有乘积有意义（Section VI-A-4、Appendix A），其他情况未说明。
6. **Table I 中 α·β 行与数据集的对应关系**：抽取文本给出 5 个数值而表有 6 个数据集列，正文也未逐一对应，实际实现需要自行调参。
7. **被选客户端只有 1 个或极少时的行为**：论文未讨论；若该客户端余弦 ≤ 0 则直接落入第 1 条的 0/0 情形。
8. **信任分是否需要任何平滑或动量**：论文未使用跨轮累积，但也没有讨论单轮噪声很大时是否要平滑。
9. **数值实现**：余弦、ReLU、范数缩放的精度与是否用 float64 做归约，论文未说明。
10. **上传的是本地模型还是更新**：论文说两者算法等价（脚注 1），但服务器需要 gi = wi − w，实现时要固定一种约定并保证版本一致。

## 10. 原文依据

1. **支持步骤 1（每轮客户端采样与规模设置）**："Following previous work [15], we set τ = n, i.e., all clients are selected in each iteration; and we set Rl = 1"（Section VI-A-4）。
2. **支持步骤 2 与步骤 3（ModelUpdate 的定义方式）**："The local model updates and the server model update are computed by the function ModelUpdate in Algorithm 1 via performing stochastic gradient descent for Rl iterations with a local learning rate β."（Section IV-C）。
3. **支持步骤 3（服务器用根数据集算 g0）**："Meanwhile, the server itself computes the server model update based on the global model and the root dataset."（Section IV-C）。
4. **支持步骤 4–5（信任分是 ReLU 截断的余弦）**："Formally, our trust score of a local model update is its ReLU-clipped cosine similarity with the server model update."（Section IV-A）。
5. **支持步骤 5（为什么必须做 ReLU 截断）**："However, the cosine similarity alone is insufficient because a local model update, whose cosine similarity score is negative, can still have a negative impact on the aggregated global model update."（Section IV-A）。
6. **支持步骤 6（范数对齐与其作用）**："Such normalization essentially projects each local model update to the same hyper-sphere where the server model update lies in the vector space, which limits the impact of the poisoned local model updates with large magnitudes."（Section IV-A、Section IV-B）。
7. **支持步骤 7–8（加权平均与全局更新）**："Finally, FLTrust computes the average of the normalized local model updates weighted by their trust scores as the global model update, which is used to update the global model."（Section IV-A）。
8. **支持步骤 3 与第 7 节（根数据集规模）**："Our FLTrust requires a small root dataset. By default, we assume the root dataset has only 100 training examples."（Section VI-A-5）。

```json
{
  "key": "cao2020fltrust",
  "method": "FLTrust: the server bootstraps trust from a small clean root dataset; each local model update is scored by its ReLU-clipped cosine similarity to the server model update and rescaled to the server update's L2 norm, then averaged with trust-score weights to form the global model update.",
  "stages": ["server_distribute", "client_step", "client_post_train", "server_receive", "server_aggregate", "server_post_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {"step": "per-round client sampling and broadcast of the global model", "operator": "sample_clients_broadcast", "input": "global model w (d-dim); client pool of size n", "output": "w delivered to tau sampled clients", "params": {"tau": "n"}, "source": "Algorithm 2 line 4; Section II-A Step I; Section VI-A-4"},
    {"step": "client local SGD on its own data", "operator": "local_sgd_update", "input": "w; local dataset Di; batch size b; local learning rate beta; local iterations Rl", "output": "local model update gi = w_R - w, tau vectors of dimension d", "params": {"Rl": 1, "b": 32, "b_cifar10": 64}, "source": "Algorithm 1 lines 1-6; Algorithm 2 line 8"},
    {"step": "server-side reference SGD on the clean root dataset", "operator": "reference_sgd_update", "input": "same-round w; root dataset D0; same b, beta, Rl", "output": "server model update g0 (d-dim)", "params": {"root_size": 100, "Rl": 1}, "source": "Algorithm 2 line 12; Section IV-A; Section IV-C"},
    {"step": "cosine similarity between each local update and the server update", "operator": "cosine_similarity_score", "input": "gi for i=1..tau and g0, all d-dim", "output": "ci = <gi,g0>/(||gi||*||g0||) in [-1,1]", "params": {}, "source": "Equation (2); Algorithm 2 line 15"},
    {"step": "ReLU clipping of cosine similarity into trust score", "operator": "relu_clip", "input": "ci", "output": "TSi = max(ci, 0)", "params": {}, "source": "Equation (2); Algorithm 2 line 15; Section IV-B"},
    {"step": "rescale each local update to the server update's L2 norm", "operator": "rescale_to_reference_norm", "input": "gi, ||gi||, ||g0||", "output": "gbar_i = (||g0||/||gi||)*gi with ||gbar_i|| = ||g0||", "params": {}, "source": "Equation (3); Algorithm 2 line 16; Section IV-B"},
    {"step": "trust-score weighted average of the normalized updates", "operator": "trust_weighted_average", "input": "pairs (TSi, gbar_i) for i=1..tau", "output": "global model update g (d-dim)", "params": {}, "source": "Equation (4); Equation (7); Algorithm 2 line 18"},
    {"step": "global model update with the global learning rate", "operator": "global_lr_update", "input": "w, g, alpha", "output": "w + alpha*g (new global model)", "params": {"alpha_beta": "3e-4, 6e-3, 2e-4, 3e-3, 3e-4 (0.9 decay at rounds 1500 and 1750 for one setting)"}, "source": "Equation (5); Algorithm 2 line 19; Section VI-A-4"}
  ],
  "sampling": [
    {"what": "clients", "how": "randomly sample tau of the n clients in each global iteration (with or without replacement not stated)", "size": "tau = n (Section VI-A-4; Table I)"},
    {"what": "samples", "how": "server draws a random batch Db from the clean root dataset D0 during its SGD; the root dataset itself is sampled from the union of clients' clean data, uniformly in Case I or class-biased with a bias probability in Case II", "size": "|D0| = 100 by default (Table I; Section VI-A-5); swept 50-500 in Figure 4; bias probability 0.1-1.0 in Table V"},
    {"what": "rounds", "how": "fixed number of global iterations, no per-round subsampling and no early stopping", "size": "Rg = 2000/2000/2500/1500/1000 (Section VI-A-4; Table I)"}
  ],
  "resources": [
    "clean root dataset D0 collected and manually labeled by the service provider (default 100 examples; Section III; Section VI-A-5)",
    "one extra model replica on the server (server model, fine-tuned from the global model with the same optimizer settings; Section IV-A)",
    "global model w and its dimension d (the bound in Theorem 1 depends on d and |D0|)",
    "root dataset examples must be excluded from clients' local training data (Section VI-A-5)",
    "no pretrained detector, no extra network, no client-side extra data or computation (Section III; Section VI-B)"
  ],
  "actions": ["clip", "transform_gradients", "reweight", "exclude_client"],
  "dominant_cost": "Reported: no extra client computation or communication; the server's extra work is one root-dataset model update plus tau cosine similarities and tau rescalings, negligible for a powerful server (Section VI-B). Analysis: per round the server pays O(Rl * |D0|) forward/backward passes on the root dataset plus O(tau * d) for scoring and rescaling, growing with |D0|, Rl, tau and d; client cost is unchanged from FedAvg.",
  "underspecified": [
    "分母为 0 的情形：当所有被选客户端 TSi = 0 时，公式 (4) 与 Algorithm 2 第 18 行为 0/0，论文未说明处理方式。",
    "||gi|| = 0 或 ||g0|| = 0 时公式 (2)、(3) 的除零保护，论文未说明。",
    "正文公式 (4) 的分母排版与 Algorithm 2 第 18 行不一致（抽取文本中公式 (4) 分母多出一个 n），实现时需自行决定，按 Algorithm 2 应为 1/Σ_j TS_j。",
    "客户端随机采样的具体方式（是否有放回、是否按权重），Algorithm 2 第 4 行未说明。",
    "Algorithm 1 中随机批采样的细节（是否有放回、不足一个 batch 如何处理），论文未说明。",
    "Rl > 1 时全局学习率 α 与局部学习率 β 如何拆分，论文只说明 Rl = 1 时只有乘积有意义（Section VI-A-4；Appendix A）。",
    "Table I 中 α·β 行的数值与六个数据集列的对应关系在抽取文本中不完整，正文也未逐一说明。",
    "当轮被选客户端极少（例如仅 1 个且余弦 ≤ 0）时的行为，论文未讨论。",
    "信任分是否需要跨轮平滑或动量，论文未使用也未讨论。",
    "余弦、ReLU、范数缩放的数值精度与归约精度，论文未说明。"
  ],
  "quotes": [
    {"supports": "步骤 1：每轮客户端采样与 Rl = 1 的设置", "text": "Following previous work [15], we set τ = n, i.e., all clients are selected in each iteration; and we set Rl = 1"},
    {"supports": "步骤 2 与步骤 3：客户端更新与服务器更新同一套 ModelUpdate 参数", "text": "The local model updates and the server model update are computed by the function ModelUpdate in Algorithm 1 via performing stochastic gradient descent for Rl iterations with a local learning rate β."},
    {"supports": "步骤 3：服务器用根数据集计算服务器模型更新 g0", "text": "Meanwhile, the server itself computes the server model update based on the global model and the root dataset."},
    {"supports": "步骤 4-5：信任分定义为 ReLU 截断的余弦相似度", "text": "Formally, our trust score of a local model update is its ReLU-clipped cosine similarity with the server model update."},
    {"supports": "步骤 5：为什么余弦为负的更新必须被截断", "text": "However, the cosine similarity alone is insufficient because a local model update, whose cosine similarity score is negative, can still have a negative impact on the aggregated global model update."},
    {"supports": "步骤 6：范数对齐到服务器更新的超球面及其作用", "text": "Such normalization essentially projects each local model update to the same hyper-sphere where the server model update lies in the vector space, which limits the impact of the poisoned local model updates with large magnitudes."},
    {"supports": "步骤 7-8：信任分加权平均得到全局模型更新并更新全局模型", "text": "Finally, FLTrust computes the average of the normalized local model updates weighted by their trust scores as the global model update, which is used to update the global model."},
    {"supports": "步骤 3 与外部资源：根数据集规模", "text": "Our FLTrust requires a small root dataset. By default, we assume the root dataset has only 100 training examples."}
  ]
}
```
