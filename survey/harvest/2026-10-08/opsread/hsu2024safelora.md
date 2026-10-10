# hsu2024safelora：Safe LoRA

## 1. 方法一句话
输入是一对同架构模型的权重（未对齐模型 $W^{unaligned}$ 与对齐模型 $W^{aligned}$，逐层）以及用 LoRA（Low-Rank Adaptation）微调后得到的逐层更新 $\Delta W_i = A_iB_i^T$；输出是逐层的二元判定（该层是否投影）和改动后的更新（被选中的层替换为 $\hat{C}_i\Delta W_i$，未选中的层保持原样），最终把它们合并回对齐模型权重，得到"既保留下游效用、又不丢安全对齐"的微调后模型。它本身不是攻击检测器，而是一个训练后（post-hoc）、免训练（training-free）、免数据（data-free）的权重修补（patch）。

## 2. 运行位置
论文是**集中式**的 LLM 微调后处理，全文没有出现联邦学习设定，因此下面的联邦位置映射全部标"分析："。

- **对齐矩阵预计算（构造 $V$、$\hat{C}$ 或 $C$）**：运行在**训练之外**，每个"未对齐/对齐模型对"只需算一次，与客户端、轮次、微调数据都无关。它不需要 GPU，可以放在磁盘上，投影时逐层载入 GPU（Section 4）。
- **投影与写回（主体防御）**：分析：最自然的联邦位置是**客户端上传前 / 客户端训练结束之后**（client_post_train），因为 LoRA 的 $\Delta W_i$ 就在客户端本地，而 $\hat{C}_i$ 只依赖模型架构、可由服务器预先算好下发（或客户端用本地持有的 base/chat checkpoint 自算）。
- **等价放置**：分析：如果 $\Delta W_i$ 或聚合后的全局更新在服务器侧可见，同一套算子也可放在**服务器收到更新**（server_receive）或**聚合之后**（server_post_aggregate），即对聚合结果做一次同样的子空间投影；论文未讨论这两种部署，属于部署选择。
- **额外往返**：不需要。把一个 $O(\text{层数})$ 的投影矩阵（或每层 $V_i$）随模型一起分发即可，投影是纯本地计算，不需要每轮再与服务器交互。

## 3. 算子流水线

### 步骤 0：确定模型对（准备阶段）
- **输入**：同一架构的两份公开权重。
- **计算**：取官方发布的 base 模型为 $W^{unaligned}$、chat/instruct 模型为 $W^{aligned}$；论文也讨论了用"对齐模型再用少量恶意数据微调后的模型"当未对齐模型，并发现两者得到的对齐矩阵效果接近，因此**默认使用官方 base/chat 模型对**（Section 3.1、Figure 2）。
- **输出**：一份模型对。
- **论文出处**：Section 3.1、Figure 2。

### 步骤 1：构造对齐矩阵（alignment matrix）
- **输入**：第 $i$ 层的两个权重矩阵 $W_i^{aligned}$ 与 $W_i^{unaligned}$（论文把每层权重矩阵独立处理，讨论的权重空间是 $(\mathbb{F}^{n\times n}, +, \cdot, \mathbb{R})$ 配 Frobenius 内积；实际模型里 LoRA 只加在部分层上）。
- **计算**：$V_i = W_i^{aligned} - W_i^{unaligned}$（公式 (1)）。
- **输出**：每层一个 $V_i$。
- **论文出处**：公式 (1)，Section 3.1。

### 步骤 2：构造投影矩阵（两种版本，论文都给了）
- **输入**：$V_i$。
- **计算（精确版）**：$\hat{C}_i = V_i (V_i^T V_i)^{-1} V_i^T$，逐层做，得到一个标准投影矩阵（公式 (2)）。
- **计算（快速近似版）**：$C_i := V_iV_i^T / \lVert V_i\rVert_F$，其中 $\lVert\cdot\rVert_F$ 是 Frobenius 范数（Section 3.4；Figure 1 的伪代码写成 `C = np.dot(V, V.T())/np.norm(V)`）。
- **输出**：每层一个投影矩阵（精确版 $\hat{C}_i$，近似版 $C_i$）。
- **论文出处**：公式 (2)、Section 3.4、Figure 1 及其题注。**注意**：主实验（Table 2–4）究竟用哪一个版本，论文未说明。

### 步骤 3：计算投影后的 LoRA 更新
- **输入**：第 $i$ 层的 LoRA 更新 $\Delta W_i = A_iB_i^T$，以及 $\hat{C}_i$（或 $C_i$）。
- **计算**：$\hat{C}_i\Delta W_i$。Figure 1 把它写成 $A' = CAB^T$，代码写成 `ΔW.data = CΔW`。
- **输出**：与 $\Delta W_i$ 同形状的矩阵 $\hat{C}_i\Delta W_i$。
- **论文出处**：Section 3.2、公式 (3)、Figure 1。

### 步骤 4：计算逐层相似度
- **输入**：$\Delta W_i$ 与 $\hat{C}_i\Delta W_i$。
- **计算**：Frobenius 余弦相似度 $\cos_i = \langle \Delta W_i, \hat{C}_i\Delta W_i\rangle_F / (\lVert\Delta W_i\rVert_F\,\lVert\hat{C}_i\Delta W_i\rVert_F)$，其中 $\langle\cdot,\cdot\rangle_F$ 是 Frobenius 内积（公式 (3) 的条件式；Figure 1 写作 `cos(CΔW, ΔW)`；Figure 4 的纵轴就是它）。
- **输出**：每层一个标量 $\cos_i$。
- **论文出处**：公式 (3)、Figure 1、Figure 4。

### 步骤 5：选层（阈值或 top-K）
- **输入**：所有参与 LoRA 的层的 $\cos_i$。
- **计算**：若 $\cos_i < \tau$ 则该层投影（公式 (3)）；论文给出的替代规则是"只投影相似度最低的 top-K 层"（Section 3.2、Section 4.1）。
- **输出**：待投影层集合。
- **论文出处**：公式 (3)、Section 3.2、Section 4.1。**注意方向**：相似度越低越投影；Figure 3 的标注显示 $\tau$ 越大投影层越多（0.05→0%，0.35→11%，0.8→100%）。

### 步骤 6：执行投影并写回
- **输入**：被选中的层的 $\Delta W_i$（以及 $\hat{C}_i$）。
- **计算**：$\Delta W_i \leftarrow \hat{C}_i\Delta W_i$；未被选中的层"NO modification"（Figure 1），保持 $A_iB_i^T$ 不变。
- **输出**：改造后的逐层 LoRA 更新。
- **论文出处**：公式 (3)、Figure 1。
- **论文未说明**：$\hat{C}_i\Delta W_i$ 一般是稠密矩阵、秩通常大于 LoRA 秩 $r$，论文没有说明如何把它重新分解回 LoRA 的 $A_i,B_i$（Figure 1 的 `ΔW.data = CΔW` 是示意写法，没有给 SVD 或截断方案），也没有说明是否可以改为把该稠密增量直接合并进 $W^{aligned}$。

### 步骤 7：合并得到最终权重
- **输入**：$W^{aligned}$ 与投影后的 $\Delta W$。
- **计算**：把（部分投影过的）$\Delta W$ 合并到对齐模型权重上；Figure 1 题注的表述是"用投影后的 LoRA 权重作为对 $W^{aligned}$ 的最终更新"。
- **输出**：修补后的模型权重。
- **论文出处**：Figure 1 题注、Section 3.2。

### 步骤 7'：全参数微调变体（论文的扩展）
- **输入**：第 $i$ 层的预训练权重 $W_i^{pre\text{-}trained}$ 与全参数微调后的权重 $W_i^{fine\text{-}tuned}$，以及 $C_i$。
- **计算**：$W_i^{fine\text{-}tuned} = W_i^{pre\text{-}trained} + C_i\,(W_i^{fine\text{-}tuned} - W_i^{pre\text{-}trained})$，即**投影的是残差而不是微调后的权重本身**（公式 (4)）。
- **输出**：修补后的全参数权重。
- **论文出处**：公式 (4)、Section 4.2。

### 步骤 8：整模型相似度诊断（可选，用于决定是否全层投影）
- **输入**：所有层的 $\Delta W_i$ 与 $C_i\Delta W_i$。
- **计算**：$S(C\Delta W, \Delta W) = \sum_{i=1}^{N} \dfrac{1}{1 + \lVert C_i\Delta W_i - \Delta W_i\rVert^2}$，即逐层"投影前后距离"的倒数求和（公式 (5)）。
- **输出**：一个标量 $S$，越低说明微调方向越偏离对齐子空间。
- **论文出处**：公式 (5)、Appendix A.4、Table 6。论文据此在 PureBad 场景**投影全部 LoRA 层**（Section 4.1），但没有给出触发"全层投影"的 $S$ 阈值。

## 4. 采样与规模控制
- **样本（samples）**：论文未使用。Safe LoRA 是 data-free 的，不需要干净参考数据、探针样本或校准集（Abstract、Section 4.1）。
- **客户端（clients）**：论文未使用（集中式设定）。
- **层（layers）**：**有做层级别的筛选**，这是本方法唯一的"降维"手段。只对插了 LoRA 的层计算相似度；再由 $\tau$ 或 top-K 决定投影哪些层。取值：Llama-2-7B-Chat + Dialog Summary 设 $\tau=0.35$ → 投影 7 层（Section 4.1）；Llama-3-8B-Instruct + Dialog Summary 投影"约 35% 的总 LoRA 层"（Section 4.1）；PureBad 场景投影全部 LoRA 层（Section 4.1）；Appendix A.7 中随有害数据比例 10%/30%/50% 分别投影 7/18/34 层。论文只给出比例与绝对层数，未说明 LoRA 权重矩阵的总数（Figure 4 横轴为层序号，范围约 0–60；按 7 层 ≈ 11% 反推总数约 64，此为分析）。
- **参数坐标（coordinates）**：论文未使用，投影对整块 $\Delta W_i$ 操作。
- **轮次（rounds）**：论文未使用。投影是一次性 post-hoc 操作，不跨轮累积、不迭代。

## 5. 超参数
| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| $\tau$ | 相似度阈值，$\cos_i<\tau$ 的层被投影 | 0.35（Llama-2-7B-Chat + Dialog Summary）→ 投影 7 层 | Section 4.1 |
| $\tau$ 扫描范围 | 消融中的阈值范围 | 0.05–0.8（对应投影 0%、2%、2%、3%、5%、6%、11%、22%、39%、48%、72%、81%、81%、86%、97%、100% 的层） | Figure 3 |
| 投影层比例 | 实际投影的 LoRA 层占比 | Llama-2-7B-Chat 约 11%；Llama-3-8B-Instruct 最高约 35% | Section 1 贡献、Section 4.1、Section 4.2 |
| $K$（top-K） | 只投影相似度最低的 K 层 | 论文未给出具体取值，仅作为 $\tau$ 的替代方案提出 | Section 3.2、Section 4.1 |
| PureBad 的投影范围 | 纯恶意数据下的设定 | 投影**全部** LoRA 层（阈值未说明） | Section 4.1 |
| 有害数据比例 → 投影层数 | 混合数据下的经验设定 | 10%→7 层，30%→18 层，50%→34 层（阈值均未说明） | Appendix A.7 |
| LoRA 秩 $r$ | 低秩更新的秩 | 8（所有实验） | Section 4 |
| LoRA 注入位置 | 加在哪些层 | 仅 `q_proj` 与 `v_proj` 注意力层 | Section 4 |
| 微调学习率/批大小/轮数 | LoRA 训练设置 | Llama-2-7B-Chat：$5\times10^{-5}$、5、5 epochs；Llama-3-8B-Instruct PureBad：$10^{-3}$、5、5 epochs；Llama-3-8B-Instruct Dialog Summary：$10^{-4}$、32、3 epochs | Section 4 |
| 是否迭代/累积 | 投影执行次数 | 一次（post-hoc），无跨轮累积 | Section 3.2、Section 4.2 |

## 6. 判定与动作
- **判定量**：逐层余弦相似度 $\cos_i$（公式 (3)）。相似度越低，说明该层 LoRA 更新方向偏离对齐矩阵越远，论文假设这正是微调削弱安全的根因。
- **判定规则**：$\cos_i < \tau$ 就投影该层；等价替代是取相似度最低的 top-K 层投影（Section 3.2、Section 4.1）。$\tau$ 越大投影越多（Figure 3）。
- **动作（被选中的层）**：把更新替换为它在对齐子空间上的投影 $\Delta W_i \leftarrow \hat{C}_i\Delta W_i$（公式 (3)）；Figure 1 的代码即 `ΔW.data = CΔW`。未被选中的层不做任何修改。这是对更新的**变换**，不是剔除、加权、裁剪或加噪。
- **动作（数据集级别的启发式）**：用整模型相似度 $S$（公式 (5)）判断微调是否"朝不安全方向"走了很远；Table 6 中 Llama-2-7B-Chat 的 $S$ 为 Alpaca 0.8006、Dialog Summary 0.7311、PureBad 0.4469，Llama-3-8B-Instruct 为 Dialog Summary 0.6709、PureBad 0.4583；PureBad（最低相似度）时改为**投影全部 LoRA 层**（Section 4.1、Appendix A.4）。论文未给出 $S$ 的数值阈值，这个切换规则是定性的。
- **幅度参数**：没有裁剪阈值、噪声尺度或加权系数；唯一的"幅度"控制就是 $\tau$ / 层数。
- **跨轮累积**：不累积，单次执行。
- **权衡**：投影层数越多越安全但越伤效用；Llama-2 上约 11% 层是"效用损失 <2% Rouge F1、有害性下降 >2"的平衡点（Section 4.2、Figure 3）。

## 7. 需要的外部资源
- **一对同架构的未对齐/对齐模型权重**：默认用官方 checkpoint，例如 $W^{unaligned}$ 取 Llama-2-7b-base、$W^{aligned}$ 取 Llama-2-7b-chat（Section 3.1）。论文也允许用"对齐模型 + 恶意微调"的方式造未对齐模型，但默认不是这样。
- **存储空间**：每层对齐矩阵 $V_i$（及投影矩阵 $\hat{C}_i$ 或 $C_i$）需存到磁盘，投影时**逐层**载入 GPU，而不是一次性全部载入（Section 4）。论文未给出具体容量数字，论文未说明；分析：规模约为被打补丁的那些层的权重矩阵量级（$C_i$ 为 $n\times n$，与 $V_i$ 同阶）。
- **算力**：精确版每层需要一次 $(V_i^TV_i)^{-1}$ 的矩阵求逆（Section 3.4）。
- **不需要的东西**：不需要干净参考数据、不需要根数据集、不需要预训练检测器、不需要额外训练（Abstract、Section 4.1）。唯一"额外的模型"就是那对 base/chat checkpoint，而它们本来就是公开的。

## 8. 计算与存储开销
- **论文报告的数字**：生成 $C$ 需 $8.6\times10^{-3}$ 秒，生成 $\hat{C}$ 需 2.1714 秒，慢约 250 倍，全部在 NVIDIA H100 80GB GPU 上计算（Section 3.4）。实验环境为 NVIDIA H100 80GB GPU 与 AMD® Epyc 7313 16-core 处理器 ×64（Section 4）。对齐矩阵不需要 GPU、可存磁盘、投影时逐层载入 GPU（Section 4）。
- **分析：主要开销来自哪一步**：瓶颈是**每层投影矩阵的构造**——精确版要做 $V_i^TV_i$（$m\times m$）、求逆（约 $O(m^3)$）以及两次矩阵乘法；近似版只有一次 $V_iV_i^T$ 和一次标量除法，所以快 250 倍。其次是**每层把投影作用到 $\Delta W_i$** 的两次 $n\times m$ 与 $n\times n$ 矩阵乘法。
- **分析：随什么量增长**：总开销随"被投影的层数 × 这些层权重矩阵的尺寸"增长，与微调数据量、训练步数、客户端数量**无关**（data-free、training-free、单次执行）。相似度计算本身每层只是两次矩阵乘加一个 Frobenius 内积，相对可忽略。

## 9. 实现时容易错的地方
论文明确强调或可直接推出的：
1. **阈值方向不能反**：$\cos<\tau$ 才投影；Figure 3 中 $\tau$ 增大则投影层数单调增加（0.05→0%，0.35→11%，0.8→100%）。
2. **只处理插了 LoRA 的层**：论文实验只对 `q_proj`/`v_proj` 加 LoRA，也是只对这些层构造 $V_i$ 和做投影（Section 3.2、Section 4）。
3. **精确版依赖 $(V^TV)^{-1}$**：需要 $V_i$ 列满秩；论文没有讨论秩亏、奇异或加正则的处理。
4. **快速版 $C_i=V_iV_i^T/\lVert V_i\rVert_F$ 并不是真正的投影矩阵**（不正交、不幂等），论文只称其为"近似版本"，Figure 1 题注却仍叫它 "projection operator"，实现时不要把它当作严格正交投影来推理。
5. **全参数微调变体投影的是残差** $W^{fine\text{-}tuned}-W^{pre\text{-}trained}$，而不是 $W^{fine\text{-}tuned}$ 本身（公式 (4)）。
6. **显存管理**：对齐矩阵要逐层载入，不要一次性全部放进 GPU（Section 4）。
7. **模型越"弱对齐"，需要投影的层越多**：Llama-2 约 11%，Llama-3 约 35%（Section 4.1）。
8. **不要全层投影**：投影层数越多效用掉得越快，论文的平衡点是约 11%（Section 4.2）。

论文没说清、实现时必须自己决定的（逐条列出）：
1. **$\hat{C}_i\Delta W_i$ 如何写回 LoRA 参数**：该矩阵通常是满秩稠密矩阵，无法用同秩的 $A_iB_i$ 表示；论文未说明是否做 SVD 截断回秩 $r$、是否直接合并进基座权重、还是把 $A_i,B_i$ 整体替换。Figure 1 的 `ΔW.data = CΔW` 不足以确定这一点。
2. **主实验用精确版还是近似版**：Table 1 同时给出 `C∆W` 与 `ˆC∆W` 两列，但 Table 2–4 用的是哪一个，论文未说明。
3. **$\tau$ 的选取流程**：论文只给了一个场景的 $\tau=0.35$ 和一次扫描（Figure 3），没有说明新模型/新数据集上如何选 $\tau$ 或 $K$。
4. **PureBad 场景的阈值**：只说"投影全部 LoRA 层"，没给判定用的阈值；Llama-3 在 PureBad 上投影了多少层也未说明。
5. **$S$（公式 (5)）的阈值**：Table 6 只有三个数据集上的数值，没有给出"低到多少就全层投影"的判据。
6. **余弦相似度的退化情形**：$\lVert\Delta W_i\rVert_F=0$ 或 $\lVert\hat{C}_i\Delta W_i\rVert_F=0$（例如某层从未被更新）时分母为零，论文未讨论。
7. **投影矩阵的维度与形状约定**：论文把权重空间写成 $\mathbb{F}^{n\times n}$，但真实模型的 `q_proj`/`v_proj` 不一定是方阵（例如 Llama-3-8B 的 `v_proj`），此时 $V_iV_i^T$、$(V_i^TV_i)^{-1}$ 的形状取决于 $V_i$ 的行列约定，论文未说明。
8. **是否影响优化器状态/多次 LoRA 适配器**：论文未涉及。
9. **随机性与误差棒**：论文未报告随机种子、多次运行的方差或误差棒（NeurIPS checklist 第 7 题虽答 [Yes]，但正文 Section 4 未给出这些信息）。

## 10. 原文依据
1. **支撑步骤 0/1（获取模型对、构造对齐矩阵）**："First, we assume access to a pair of unaligned and aligned LLM weights, denoted as Wunaligned and Waligned, which are often available for open-source LLMs such as Llama Base (unaligned) and Chat (aligned) models."
2. **支撑步骤 2（精确投影矩阵 $\hat{C}=V(V^TV)^{-1}V^T$）**："After obtaining Vi, we perform matrix multiplication with Vi and its transpose with the matrix (ViT Vi)−1 to form a standard projection matrix. This operation is conducted on a layer-wise basis"
3. **支撑步骤 2'/3（近似投影算子 $C=VV^T/\lVert V\rVert_F$ 与相似度计算）**："we use the projection operator C = VVT /∥V∥F to calculate the similarity score between the projected LoRA weights CABT and the original LoRA weights ABT"
4. **支撑步骤 4/5（用阈值决定投影哪些层）**："Instead, we calculate the similarity between the original and projected LoRA weights, i.e., ∆Wi and Ci∆Wi. Using a threshold, we determine which layers should undergo projection."
5. **支撑步骤 5 的 top-K 替代规则**："Alternatively, τ could be selected such that only the top-K layers with the lowest similarity scores will be projected."
6. **支撑步骤 7'（全参数微调时投影残差，公式 (4)）**："Instead of directly projecting the weights of the fine-tuned model, we project the residual weights between the pre-trained and fine-tuned models."
7. **支撑步骤 2 的开销对比（精确版 vs 近似版）**："It takes 8.6 × 10−3 seconds to generate C, while generating ˆC requires 2.1714 seconds, denoting a 250x times slower generation speed."
8. **支撑资源与实现（对齐矩阵存磁盘、逐层载入 GPU）**："In practice, the alignment does require hardware resources, but it doesn't utilize GPUs. Instead, it can be stored on disk. During projection, it is loaded layer by layer onto GPUs (not all at once)"

```json
{
  "key": "hsu2024safelora",
  "method": "Safe LoRA：用对齐模型与未对齐模型的逐层权重差构造安全对齐子空间，把与投影结果余弦相似度低于阈值（或相似度最低的 top-K）的那些 LoRA 层的更新 ΔW=AB^T 替换为子空间投影，从而在微调后修补安全对齐",
  "stages": ["outside_training", "client_post_train", "server_post_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "构造对齐矩阵 V",
      "operator": "weight_difference",
      "input": "第 i 层的未对齐模型权重 W_i^unaligned 与对齐模型权重 W_i^aligned（同架构同形状，论文按 n×n 权重空间讨论）",
      "output": "V_i = W_i^aligned − W_i^unaligned，每层一个矩阵",
      "params": {},
      "source": "公式 (1)，Section 3.1"
    },
    {
      "step": "构造精确投影矩阵 Ĉ",
      "operator": "orthogonal_projection_matrix",
      "input": "V_i",
      "output": "Ĉ_i = V_i (V_i^T V_i)^{-1} V_i^T",
      "params": {},
      "source": "公式 (2)，Section 3.1；每层需要一次 (V^T V)^{-1}"
    },
    {
      "step": "构造快速近似投影矩阵 C（与上一步二选一）",
      "operator": "scaled_gram_matrix",
      "input": "V_i",
      "output": "C_i = V_i V_i^T / ||V_i||_F（Frobenius 范数归一）",
      "params": {},
      "source": "Section 3.4；Figure 1 代码 C = np.dot(V, V.T())/np.norm(V)"
    },
    {
      "step": "计算投影后的 LoRA 更新",
      "operator": "subspace_project_update",
      "input": "LoRA 第 i 层更新 ΔW_i = A_i B_i^T 与投影矩阵 Ĉ_i（或 C_i）",
      "output": "Ĉ_i ΔW_i（与 ΔW_i 同形状的稠密矩阵）",
      "params": {},
      "source": "Section 3.2，公式 (3)，Figure 1（A' = C A B^T）"
    },
    {
      "step": "计算逐层余弦相似度",
      "operator": "frobenius_cosine_similarity",
      "input": "ΔW_i 与 Ĉ_i ΔW_i",
      "output": "标量 cos_i = ⟨ΔW_i, Ĉ_iΔW_i⟩_F / (||ΔW_i||_F ||Ĉ_iΔW_i||_F)",
      "params": {},
      "source": "公式 (3) 的条件式；Figure 1 的 cos(CΔW, ΔW)；Figure 4 纵轴"
    },
    {
      "step": "按相似度选层",
      "operator": "select_layers_by_similarity",
      "input": "所有 LoRA 层的 cos_i",
      "output": "待投影层集合（cos_i < τ 的层，或 cos 最低的 top-K 层）",
      "params": {
        "tau": "0.35（Llama-2-7B-Chat + Dialog Summary，Section 4.1）；扫描范围 0.05–0.8（Figure 3）",
        "top_k": "论文未给出具体取值（Section 3.2 提出的替代规则）",
        "projected_layers": "7（τ=0.35，Section 4.1）；Llama-3-8B-Instruct 约 35%（Section 4.1）；PureBad 全部 LoRA 层（Section 4.1）；有害数据 10%/30%/50% → 7/18/34 层（Appendix A.7）"
      },
      "source": "公式 (3)，Section 3.2，Section 4.1，Figure 3"
    },
    {
      "step": "对选中层替换更新（未选中层不改）",
      "operator": "replace_update_with_projection",
      "input": "被选中的 ΔW_i 与其 Ĉ_i",
      "output": "ΔW_i ← Ĉ_i ΔW_i；其余层保持 A_i B_i^T 不变（Figure 1 的 NO modification 分支）",
      "params": {},
      "source": "公式 (3)，Figure 1"
    },
    {
      "step": "合并进对齐模型权重",
      "operator": "merge_lowrank_update",
      "input": "W^aligned 与（部分投影过的）ΔW",
      "output": "修补后的模型权重（投影后的 LoRA 权重作为对 W^aligned 的最终更新）",
      "params": {},
      "source": "Figure 1 题注，Section 3.2"
    },
    {
      "step": "写回 LoRA 因子 A、B",
      "operator": "refactor_lowrank_update",
      "input": "稠密的 Ĉ_i ΔW_i",
      "output": "新的 A_i、B_i（或把增量合并进基座权重）",
      "params": {"note": "论文未说明：未给出 SVD/截断回秩 r 或直接合并的方案，Figure 1 只写 ΔW.data = CΔW"},
      "source": "论文未说明（Figure 1 代码为示意）"
    },
    {
      "step": "全参数微调变体：投影残差",
      "operator": "residual_subspace_project",
      "input": "W_i^pre-trained、W_i^fine-tuned 与 C_i",
      "output": "W_i^fine-tuned = W_i^pre-trained + C_i (W_i^fine-tuned − W_i^pre-trained)",
      "params": {},
      "source": "公式 (4)，Section 4.2"
    },
    {
      "step": "整模型相似度诊断 S（可选，用于决定是否全层投影）",
      "operator": "inverse_squared_distance_score",
      "input": "所有层的 ΔW_i 与 C_i ΔW_i",
      "output": "S(CΔW, ΔW) = Σ_{i=1..N} 1 / (1 + ||C_iΔW_i − ΔW_i||²)",
      "params": {"S_values": "Llama-2-7B-Chat：Alpaca 0.8006 / Dialog Summary 0.7311 / PureBad 0.4469；Llama-3-8B-Instruct：Dialog Summary 0.6709 / PureBad 0.4583（Table 6）", "decision_threshold": "论文未给出"},
      "source": "公式 (5)，Appendix A.4，Table 6，Section 4.1"
    }
  ],
  "sampling": [
    {"what": "layers", "how": "只对插了 LoRA 的层（实验中为 q_proj 与 v_proj）算相似度；再按 τ 阈值或 top-K 最低相似度挑出要投影的层", "size": "Llama-2-7B-Chat + Dialog Summary：τ=0.35 → 7 层（约 11%，Section 4.1）；Llama-3-8B-Instruct：约 35%（Section 4.1）；PureBad：全部 LoRA 层（Section 4.1）；有害数据 10%/30%/50% → 7/18/34 层（Appendix A.7）；总层数论文未说明"},
    {"what": "samples", "how": "论文未使用：方法为 data-free，不需要干净参考数据或校准样本", "size": "0"},
    {"what": "coordinates", "how": "论文未使用：投影作用于整块 ΔW_i，不做参数坐标抽样", "size": "0"},
    {"what": "rounds", "how": "论文未使用：一次性 post-hoc 投影，不跨轮累积、不迭代", "size": "1 次"}
  ],
  "resources": [
    "一对同架构的未对齐/对齐模型 checkpoint（默认官方 base 与 chat/instruct，例如 Llama-2-7b-base 与 Llama-2-7b-chat；Section 3.1）",
    "存放逐层对齐矩阵 V_i（及投影矩阵 Ĉ_i 或 C_i）的磁盘空间，投影时逐层载入 GPU，容量论文未说明（Section 4）",
    "精确版本每层 (V_i^T V_i)^{-1} 的矩阵求逆算力（Section 3.4）",
    "不需要干净参考数据、根数据集、预训练检测器或额外训练（Abstract，Section 4.1）"
  ],
  "actions": ["transform_gradients"],
  "dominant_cost": "每层构造投影矩阵最贵：精确版 Ĉ 需要 (V^T V)^{-1} 与两次矩阵乘法，论文实测生成 Ĉ 需 2.1714 秒而生成 C 只需 8.6e-3 秒（慢约 250 倍，NVIDIA H100 80GB，Section 3.4）；其次是每层把投影作用到 ΔW_i 的矩阵乘法。总开销随被投影层数与其权重矩阵尺寸增长，与微调数据量、训练步数、客户端数无关（分析）。",
  "underspecified": [
    "Ĉ_i ΔW_i 是稠密矩阵，如何重新分解回 LoRA 的 A、B（是否 SVD 截断回秩 r，或直接合并进基座权重），论文未说明",
    "主实验 Table 2–4 究竟使用精确投影矩阵 Ĉ 还是快速近似 C，论文未说明（Table 1 只做了对比）",
    "τ 或 K 的选取流程：只给出一个场景的 τ=0.35 与一次扫描，未说明新模型/新数据集如何选",
    "PureBad 场景判定为全部层投影所用的阈值，论文未给出；Llama-3 在 PureBad 上投影的层数也未说明",
    "整模型相似度 S 的数值阈值（何时切换到全层投影），论文未给出",
    "当 ||ΔW_i||_F 或 ||Ĉ_iΔW_i||_F 为 0 时余弦相似度的处理，论文未讨论",
    "矩形权重矩阵（非方阵）下 V_i V_i^T 与 (V_i^T V_i)^{-1} 的形状约定，论文未说明",
    "投影对优化器状态、多 LoRA 适配器、多次连续微调的影响，论文未涉及",
    "随机种子、多次运行方差与误差棒，论文未报告"
  ],
  "quotes": [
    {"supports": "步骤 0/1：获取未对齐与对齐模型对并构造对齐矩阵 V", "text": "First, we assume access to a pair of unaligned and aligned LLM weights, denoted as Wunaligned and Waligned, which are often available for open-source LLMs such as Llama Base (unaligned) and Chat (aligned) models."},
    {"supports": "步骤 2：构造精确投影矩阵 Ĉ = V(V^T V)^{-1}V^T", "text": "After obtaining Vi, we perform matrix multiplication with Vi and its transpose with the matrix (ViT Vi)−1 to form a standard projection matrix. This operation is conducted on a layer-wise basis"},
    {"supports": "步骤 2'/3：快速近似投影算子 C = VV^T/||V||_F 与相似度计算", "text": "we use the projection operator C = VVT /∥V∥F to calculate the similarity score between the projected LoRA weights CABT and the original LoRA weights ABT"},
    {"supports": "步骤 4/5：用相似度阈值决定投影哪些层", "text": "Instead, we calculate the similarity between the original and projected LoRA weights, i.e., ∆Wi and Ci∆Wi. Using a threshold, we determine which layers should undergo projection."},
    {"supports": "步骤 5：top-K 最低相似度层的替代选层规则", "text": "Alternatively, τ could be selected such that only the top-K layers with the lowest similarity scores will be projected."},
    {"supports": "步骤 7'：全参数微调变体投影残差（公式 (4)）", "text": "Instead of directly projecting the weights of the fine-tuned model, we project the residual weights between the pre-trained and fine-tuned models."},
    {"supports": "步骤 2 的开销对比：精确版远比近似版慢", "text": "It takes 8.6 × 10−3 seconds to generate C, while generating ˆC requires 2.1714 seconds, denoting a 250x times slower generation speed."},
    {"supports": "资源与实现：对齐矩阵存磁盘并逐层载入 GPU", "text": "In practice, the alignment does require hardware resources, but it doesn't utilize GPUs. Instead, it can be stored on disk. During projection, it is loaded layer by layer onto GPUs (not all at once)"}
  ]
}
```
