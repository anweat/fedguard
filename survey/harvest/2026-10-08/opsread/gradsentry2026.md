# gradsentry2026：GradSentry（Gradient Spectral Entropy，梯度谱熵）

## 1. 方法一句话

输入是一个不可信的有监督微调（SFT）数据集 D = {(x_i, y_i)}_{i=1..N}、一个待微调的大语言模型 f_θ、以及一个固定目标模块（默认 lm_head.weight，记为 W），方法为每条样本计算其单个样本梯度矩阵的归一化谱熵（normalized spectral entropy）¯H(G′_i)，再用核密度估计（KDE）在熵分布上自动选一个阈值 τ，输出被保留的"干净"子集 D̂_c = {(x_i, y_i) : ¯H_i ≤ τ}，并对训练流程做改动（剔除被判定为中毒的样本后再训练）。依据：摘要、§3.1、§3.5、Algorithm 1。

## 2. 运行位置

- 论文自身定位：这是一个**训练前（before training begins）的数据级过滤**方法，作用在集中式 SFT 流程的"训练开始之前"；论文原文明确说目标是"identify Dp before training begins so that training can proceed on the clean subset Dc"。依据：§3.1。
- 对应到联邦流程的自然位置：**客户端训练前（client_pre_train）**，对每个客户端本地的不可信数据分片做逐样本打分与过滤，然后才用筛后的数据做本地 SFT。标"分析："（论文是集中式方法，没有讨论联邦流程）。
- 若要在联邦里复刻论文的"数据集级阈值"，需要一次额外往返：各客户端算出本地熵分数并上报统计量（或直接上报 N 个标量分数），由一个聚合方拟合 KDE 并回传 τ；否则只能每个客户端各自在自己分片上独立跑 KDE 阈值。标"分析："，论文未说明联邦下的做法。
- 不需要客户端与服务器之间额外往返的版本：每个客户端独立完成"逐样本梯度 → 谱熵 → 本地 KDE 阈值 → 本地过滤"，全部在客户端训练前本地完成。标"分析："。
- 论文没有在训练过程中或聚合时介入，也没有跨轮累积；梯度是对"固定的目标模块 W"求的，理论上服务器可下发同一份模型快照以保证各客户端打分口径一致，但论文未说明这一点。标"分析："。

## 3. 算子流水线

以下步骤来自 §3.3–§3.5 与 Algorithm 1（Algorithm 1 的行号在下面标出）。

**步骤 1：启用目标模块的梯度（故障注入/结构准备）**
- 输入：模型配置与目标模块 W（Llama-2-7B 的 lm_head.weight，形状 W ∈ R^{v×d}，v 为词表维度、d 为隐藏维度）。
- 计算：把 W 设为可求梯度（Algorithm 1 第 1 行 "Enable gradients for W"）。论文强调检测必须与训练配置解耦：无论 LoRA、全参数还是其他 PEFT，都只对"所有配置中都存在的输出投影层"求梯度，而不是对随训练方法变化的模块求梯度。
- 输出：可计算 ∇_W L 的模型状态。
- 出处：§3.1 "Training-Agnostic Detection"、§3.3、Algorithm 1 第 1 行。

**步骤 2：逐样本梯度提取（per-sample gradient）**
- 输入：单条样本 (x_i, y_i)，模型 f_θ。
- 计算：G_i = ∇_W L(f_θ(x_i), y_i)（公式 1），即对目标模块权重求单样本损失的梯度。附录 A 给出 lm_head 梯度的解析形式 ∇_W L = Σ_{t=1}^{T} (p_t − e_{y_t}) h_t^⊤（公式 11），其中 p_t 是预测 token 分布、e_{y_t} 是 one-hot 目标、h_t 是位置 t 的隐藏状态。
- 输出：完整梯度矩阵 G_i，形状 v×d（7B 模型下是词表维度 × 隐藏维度，量级为 32000×4096；论文只写 W ∈ R^{v×d}，未给出具体数值）。
- 出处：§3.3、公式 1、附录 A 公式 11、Algorithm 1 第 3 行。

**步骤 3：梯度矩阵子采样（subsample / 截断）**
- 输入：G_i ∈ R^{v×d}。
- 计算：G′_i = G_i[:v/8, :d/8]（公式 2），即取前 1/8 的行与前 1/8 的列，图 2 的图注写作 "the elements from the first 1/8 of rows and first 1/8 of columns"，做法沿用了 Wu et al. (2025)。这一步是为了计算效率。
- 输出：子采样梯度矩阵 G′_i。
- 出处：§3.3、公式 2、图 2 图注、Algorithm 1 第 4 行。

**步骤 4：截断 SVD（randomized SVD，只取 top-k 奇异值）**
- 输入：G′_i。
- 计算：G′_i = U_i Σ_i V_i^⊤（公式 4）；用随机化 SVD（Halko et al., 2011）只计算前 k 个奇异值，默认 k = 16。论文未说明随机化 SVD 的过采样（oversampling）参数与幂迭代次数。
- 输出：前 k 个奇异值 σ_1 ≥ … ≥ σ_k（降序）及对应奇异向量。
- 出处：§3.4、公式 4、附录 A、Algorithm 1 第 5 行。

**步骤 5：奇异值归一化为概率分布**
- 输入：top-k 奇异值 {σ_j}_{j=1..k}。
- 计算：p_j = max(σ_j, ϵ) / Σ_{l=1..k} max(σ_l, ϵ)（公式 5），其中 ϵ = 10^{-12} 用于数值稳定。
- 输出：概率分布 P = (p_1, …, p_k)。
- 出处：§3.4、公式 5、Algorithm 1 第 6 行。

**步骤 6：计算归一化谱熵**
- 输入：P。
- 计算：先算香农熵 H(G′_i) = −Σ_{j=1..k} p_j log p_j（公式 6），再用最大熵归一化 ¯H(G′_i) = H(G′_i) / log k ∈ [0,1]（公式 7）。¯H→0 表示单个奇异值主导（能量集中），¯H→1 表示奇异值均匀分布（能量弥散）。
- 输出：每条样本一个标量分数 ¯H_i ∈ [0,1]；全部样本得到 {¯H_i}_{i=1..N}。
- 出处：§3.4、公式 6、公式 7、Algorithm 1 第 7 行。

**步骤 7：KDE 密度估计（阈值选择第一步）**
- 输入：N 个标量熵分数 {¯H_i}。
- 计算：拟合高斯核密度估计 ĝ(x) = (1/(N h)) Σ_{i=1..N} K((x − ¯H(G′_i))/h)（公式 9），K(·) 为高斯核；带宽 h 由 Silverman 规则给出 h = 1.06 σ̂ N^{−1/5}，σ̂ 为样本标准差。论文未说明是否对带宽做下界截断。
- 输出：一维密度函数 ĝ(x)。
- 出处：§3.5 "Density Estimation"、公式 9、Algorithm 1 第 9 行。

**步骤 8：谷值检测得到阈值 τ（阈值选择第二步）**
- 输入：ĝ(x)。
- 计算：定位两个峰——最靠近 0 的峰位置 x_L 与最靠近 1 的峰位置 x_R（论文文字写作 "peaks closest to 0 and 1"，Figure 1 图注把该谷值阈值的横坐标称为 "the x-coordinate of the valley"），取二者之间密度最小处 τ = arg min_{x ∈ [x_L, x_R]} ĝ(x)（公式 10）。论文未说明峰的检测算法（如峰间距最小间隔、平滑方式）、也未说明在 [x_L, x_R] 上如何离散化搜索 x。
- 输出：标量阈值 τ。
- 出处：§3.5 "Valley Detection"、公式 10、Algorithm 1 第 9 行、Figure 1 图注。

**步骤 9：回退阈值（bimodality 缺失时的分支）**
- 输入：熵分布 {¯H_i}。
- 计算：当不存在清晰双峰结构（论文举例：样本量小或没有中毒样本）时，回退到经验阈值 0.7（by default，分析见附录 G）。
- 输出：τ = 0.7。
- 出处：§3.5、§4.3 末句 "We set the fallback empirical value as 0.7."、Algorithm 1 第 9 行注释 "automatic threshold"。

**步骤 10：逐样本判定与数据集过滤**
- 输入：{¯H_i} 与 τ。
- 计算：ŷ_i = poisoned 若 ¯H(G′_i) > τ，否则 clean（公式 8）；保留集合 D̂_c = {(x_i, y_i) : ¯H_i ≤ τ}（Algorithm 1 第 10 行；摘要/图 1 描述 "Remove" 高熵、"Keep" 低熵）。
- 输出：过滤后的干净数据集 D̂_c（超参表里对应动作是 exclude_client 意义上的"样本剔除/过滤"）。
- 出处：§3.5、公式 8、Algorithm 1 第 10–11 行、图 2。

## 4. 采样与规模控制

- **参数坐标降维（有）**：梯度矩阵按公式 2 取前 1/8 行与前 1/8 列；出处 §3.3、公式 2、图 2 图注。
- **谱维度截断（有）**：SVD 只用 top-k 奇异值，默认 k = 16；出处 §3.4、附录 A。附录 A/图 7 给出的理由是前 16 个奇异值几乎覆盖全部谱能量。
- **轮次（无）**：方法在训练前一次性执行，不跨轮；论文未使用轮次采样。
- **层/模块抽样（无，是单点选择）**：只对单一目标模块 lm_head.weight 求梯度（表 3 与附录 H 是模块选择的对比实验，不是运行时抽样）；出处 §3.3、§4.4、附录 H、表 3/表 7。
- **客户端（无）**：论文是集中式设置，没有客户端概念；论文未说明联邦下的客户端抽样。
- **参考数据/探针（无）**：方法不需要干净参考数据集、根数据集或预训练检测器；KDE 只用被检测数据集自身的 N 个熵分数。附录 I 专门评测"数据集全为干净样本"的情形（表 8），说明它不依赖已知的干净参考集。
- **实验规模参考值**：WebQA 训练集 3,401、FreebaseQA 5,000、CoQA 5,000、NQ 5,000（表 4）；主实验默认毒化比例 0.1（§4.1.4）；毒化比例扫描从 1% 到 90%（§4.5.1、图 5）；数据量扫描从 20 到 5k 条样本（图 6）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| k（SVD rank） | 参与谱熵计算的 top-k 奇异值个数 | 16（默认，全文一致） | §3.4；附录 A "We use k = 16 as the default setting throughout the paper" |
| 子采样比例 | 梯度矩阵保留的行/列比例 | 前 1/8 行与前 1/8 列 | §3.3、公式 2、图 2 图注 |
| ϵ | 归一化奇异值时的数值稳定项 | 10^{−12} | §3.4、公式 5 |
| KDE 核 | 密度估计使用的核函数 | 高斯核 | §3.5、公式 9 |
| KDE 带宽 h | Silverman 规则给出的带宽 | h = 1.06 σ̂ N^{−1/5} | §3.5、公式 9 |
| 回退阈值 τ_fallback | 无双峰结构时的经验阈值 | 0.7 | §3.5、§4.3 |
| 判定规则 | 中毒判定不等式 | ¯H(G′_i) > τ 判为 poisoned | 公式 8 |
| 目标模块 | 求梯度的模块 | lm_head.weight（默认） | §3.3、§4.4、表 3 |
| 基座模型 | 主实验基座 | Llama-2-7B | §4.1.4 |
| LoRA rank | 参数高效微调秩 | r = 4 | §4.1.4、附录 B |
| 训练轮数 | 微调 epoch 数 | 3 | 附录 B |
| 学习率 | 微调学习率 | 2 × 10^{−5} | 附录 B |
| 默认毒化比例 | 评测设定 | 0.1 | §4.1.4 |
| 自适应攻击稀释比 λ | 攻击侧参数（非防御超参） | 0.5、0.7 | 附录 J.2、公式 15、表 9 |

## 6. 判定与动作

- **判定规则**：单阈值硬判定，ŷ_i = poisoned 当且仅当 ¯H(G′_i) > τ（公式 8）；等号样本按论文写法归入 clean（¯H_i ≤ τ 保留，Algorithm 1 第 10 行），论文未讨论并列/边界取等号时的额外处理。
- **阈值来源**：先 KDE（公式 9）再取两峰之间的谷值（公式 10）；无双峰时回退 0.7（§3.5）。
- **动作**：从训练集中**剔除**被判为中毒的样本，用剩余的 D̂_c 继续 SFT（Algorithm 1 第 10–11 行、图 2 "poisoned samples → Remove / clean → Keep"）。论文没有采用加权、裁剪、加噪、替换全局模型等动作，也没有用连续分数做软加权（分数仅用于阈值判定）。标"分析："：若要接进算子库，对应动作是一个"按布尔掩码过滤数据集样本（filter_samples）"的算子，而非 reweight/clip/add_noise。
- **是否跨轮累积**：不累积。分数与阈值只在训练前算一次，论文未描述跨轮更新 τ 或跨轮缓存熵分数；对联邦而言，论文未说明 τ 是否需要跨轮或跨客户端共享。标"分析："。
- **配套指标（论文用于评测，不是运行动作）**：中毒样本识别用 Recall 与 F1（表 2）；干净数据集上保真度用 CleanAcc = 保留样本数 / 总样本数 × 100%（附录 I 公式 13、表 8）。

## 7. 需要的外部资源

- **无需**干净参考数据集、根数据集（root dataset）、预训练检测器或额外模型；KDE 阈值只基于被检测数据集自身的熵分数（§3.5、附录 I）。标"分析："：这是该方法相对 GraCeFul/CUBE 之类方法的一个部署优势，但它仍需要"训练数据在过滤时可见"，见局限性一节。
- **需要**一个可求梯度的、与后续训练同源的模型快照 f_θ，以及目标模块权重 W（默认 lm_head.weight）；论文实验用 Llama-2-7B，另在 FreebaseQA 上验证了 Vicuna-7B-v1.5、Qwen2.5-7B-Instruct、Pythia-6.9B、Mistral、GPT-J-6B、GLM-4-9B 六个模型（§4.1.4、图 4、附录 G/图 9）。
- **算力**：所有实验在 NVIDIA H800 GPU 上完成，每块 80GB 显存（附录 B）。
- **数据规模**：WebQA 3,401/377/400、FreebaseQA 5,000/400/2,000、CoQA 5,000/400/2,000、NQ 5,000/400/498（训练/验证/测试，表 4）。

## 8. 计算与存储开销

- **论文报告的开销**：约 20–50 ms/样本（7B 模型；摘要与 §4.2 "Time cost"）。端到端过滤时间（表 2 "Time (s)" 列）：GradSentry 在 WebQA 上 99–113 s、FreebaseQA 145–167 s、CoQA 174–209 s、NQ 147–161 s，对比 CUBE（257–964 s）与 GraCeFul（194–584 s）。
- **复杂度（附录 E、公式 12、表 5）**：GradSentry 总时间 O(N(C_fb + Gk))，其中 N 为样本数、C_fb 为一次前向+反向代价、G = mn 为子采样后展平的梯度维度、k 为截断 SVD 秩；额外内存 O(N)（只存 N 个标量熵分数）。论文强调阈值步骤只作用在 N 个标量上，相对梯度提取可忽略；并且该方法对数据量是线性的，不做样本两两比较或全局聚类。
- **主要开销来自哪一步**：第一步是逐样本的前向+反向（步骤 2），第二步是子采样矩阵上的截断 SVD（步骤 4）；论文明确写 "it only requires one per-sample gradient extraction followed by truncated SVD with k = 16"。标"分析："：总时间随样本数 N 线性增长，每条样本一次反向传播；SVD 部分随 N 与 G·k 增长，但由于 1/8 子采样与 k = 16 而很小。标"分析："：在联邦中，同样的线性成本要在每个客户端本地各付一次，总成本随"客户端数 × 每客户端样本数"增长；论文未讨论联邦下的开销。
- **存储**：O(N) 个标量分数（表 5），不需要保存整个 N×G 梯度矩阵；但逐样本反向本身可能有显存压力，见第 9 节。

## 9. 实现时容易错的地方

论文明确强调或明确承认的点：

1. **目标模块必须固定为所有训练配置都存在的模块**：默认 lm_head.weight，因为后门攻击最终改变输出，输出投影层对中毒梯度模式最敏感；换模块效果差异很大（表 3 与表 7：lm_head 100.00% Recall / 99.80% F1，而多数中间层与 LoRA adapter 模块 F1 很低，甚至出现严重过度过滤）。
2. **子采样取的是"前 1/8 行和前 1/8 列"**，不是随机采样，也不是按范数选行列（公式 2、图 2）。
3. **数值稳定项 ϵ = 10^{-12}** 必须加在归一化里（公式 5），否则近零奇异值会导致除零。
4. **熵要除以 log k 做尺度归一化**（公式 7），否则不同 k 之间不可比；论文用 k = 16。
5. **阈值必须自适应估计**：附录 G 明确指出不同模型的最优阈值差异很大（Qwen2.5-7B 与 Mistral 约 0.70，Vicuna 与 Pythia-6.9B 约 0.80，GPT-J-6B 约 0.754–0.755），"a universal fixed threshold is suboptimal"，这正是 KDE 阈值设计的原因。
6. **必须先分离打分的尺度**：只有 Z-score 式地把不同量级梯度都归一化到 [0,1] 才能用同一个阈值区间（公式 7），论文强调"归一化熵在很大程度上不受梯度幅值影响"（附录 J.4）。
7. **干净数据上不要过度过滤**：附录 I 表 8 显示 GradSentry 在四个数据集上的 CleanAcc 为 89.36/99.94/99.94/99.42，平均 97.17%；WebQA 因干净分布更宽、与高熵区重叠更多而最难。
8. **阈值与 Recall 的取向**：论文的自动阈值偏向高 Recall（表 2 全部 100.00% Recall，代价是 F1 低于 GraCeFul），这是"宁可错杀、优先彻底移除后门"的保守策略，实现时不要按 F1 最优去微调阈值而与论文行为不符。
9. **逐样本反向的显存/批大小**：局限性一节明确写 "GradSentry requires computing per-sample gradients, which may be memory-intensive for very large batch sizes"。
10. **适用边界**：论文明确只研究了 SFT，未研究预训练等其他训练方式；并且方法假设过滤时能拿到训练数据，不适用于只能拿到已训练模型的事后分析。

论文没说清、实现时必须自己决定的点（逐条列出）：

1. **峰值检测的具体算法**：公式 10 只说取"最靠近 0 和 1 的两个峰"之间的谷值，没给峰的判定标准、最小峰间距、是否先平滑密度曲线；稀疏或单峰分布下的行为也未给出（只给了"回退 0.7"这一兜底）。
2. **谷值搜索的离散化**：x 在 [x_L, x_R] 上取网格还是用优化器求极小，分辨率多少，论文未说明。
3. **KDE 带宽的边界处理**：Silverman 规则在 N 很小或 σ̂ = 0（所有熵分数相同）时会退化，论文未说明兜底。
4. **等号归属**：公式 8 用严格大于，Algorithm 1 用 ≤ 保留；浮点边界与并列情况的处理论文未说明。
5. **随机化 SVD 的参数**：过采样维数、幂迭代次数、随机种子均未给出（只说用 Halko et al. 2011 的方法）。
6. **效率与秩的边界**：若有效秩小于 k（例如近零梯度样本），σ_j 全为 0 时的行为论文未说明（只有 ϵ 兜底）。
7. **分数是否可缓存**：当同一数据集多轮复用、或底模更新后是否需要重算，论文未说明。
8. **联邦相关的一切**：客户端数、每客户端分片大小、τ 是全局共享还是每客户端独立、是否需要额外往返、客户端数据非 IID 时 KDE 是否仍双峰，论文完全未涉及。标"分析："。
9. **梯度求取时的 batch size 与是否使用梯度累积/混合精度**：论文未说明（局限性地提到大 batch 可能显存吃紧）。
10. **表 4 与图 3 的样本数不一致**：表 4 写 WebQA 训练集 3,401，而图 3 的图注写 Clean n=3061 / 3451、Poison n=340，两者对不上；CoQA/NQ 的 CBA 子图也写 Clean n=5025/5040 等不同值。实现时无法据此还原确切的数据划分，需要自行决定。
11. **回退阈值 0.7 与自动阈值的优先级**：什么算"clear bimodal structure"没有可操作判据（论文只给"小样本或无中毒样本"两个例子），实现时必须自定义一个双峰性检验。

## 10. 原文依据

1. 支撑步骤 2（逐样本梯度提取）：
> "For each sample (xi, yi), we compute the single-sample gradient of the loss with respect to the target module’s parameters: Gi = ∇W L(fθ(xi), yi), (1) where W ∈Rv×d is the weight matrix of the target module."
2. 支撑步骤 3（梯度矩阵前 1/8 行列子采样）：
> "For computational efficiency, we subsample the gradient matrix to its top 1/8 rows and columns following Wu et al. (2025). We systematically evaluate alternative module choices in §4.4."
3. 支撑步骤 4 与超参 k（截断/随机化 SVD）：
> "For efficiency, we compute only the top-k singular values (k = 16 by default) using randomized SVD (Halko et al., 2011), and provide an analysis in Appendix A. We then normalize the singular values to obtain a probability distribution P = (p1, p2, . . . , pk), where each component pj is defined as:"
4. 支撑步骤 5 与数值稳定（ϵ = 10^{-12}）：
> "pj = max(σj, ϵ) Pk l=1 max(σl, ϵ) , (5) where ϵ = 10−12 ensures numerical stability. The spectral entropy is then: H(G′ i) = − k X j=1 pj log pj. (6)"
5. 支撑步骤 7（KDE 与 Silverman 带宽）：
> "where K(·) is the Gaussian kernel and bandwidth h is determined by Silverman’s rule (Silverman, 2018): h = 1.06ˆσN−1/5, with ˆσ being the sample standard deviation."
6. 支撑步骤 8（谷值阈值）：
> "We locate these peaks and define the threshold as the valley between them: τ = arg min x∈[xL,xR] ˆg(x) (10) where xL and xR are the positions of peaks closest to 0 and 1, respectively."
7. 支撑步骤 9 与步骤 10（回退阈值与判定/过滤）：
> "When a clear bimodal structure is absent (e.g., small sample size or no poisoned samples), the method falls back to a threshold based on empirical values (0.7 by default, analysis in Appendix G)."
8. 支撑步骤 10 与算法总览（判定与剔除）：
> "A sample is labeled as potential poisoned if its normalized entropy ¯H(G′ i) exceeds a threshold τ: ˆyi = ( poisoned if ¯H(G′ i) > τ, clean otherwise. (8)"

```json
{
  "key": "gradsentry2026",
  "method": "GradSentry: per-sample-gradient spectral entropy filtering of backdoor samples in LLM fine-tuning",
  "stages": ["client_pre_train"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "enable_grad_on_target_module",
      "operator": "enable_grad_target_module",
      "input": "model f_theta and its target module weight W (default lm_head.weight, W in R^{v x d})",
      "output": "model state in which grad_W L is computable",
      "params": {"target_module": "lm_head.weight"},
      "source": "Sec 3.1 Training-Agnostic Detection; Algorithm 1 line 1"
    },
    {
      "step": "per_sample_gradient",
      "operator": "per_sample_gradient",
      "input": "single sample (x_i, y_i) plus model f_theta; N samples total",
      "output": "gradient matrix G_i = grad_W L(f_theta(x_i), y_i), shape v x d",
      "params": {"reduction": "none (single sample, not batch-averaged)"},
      "source": "Eq. 1; Eq. 11 (Appendix A); Algorithm 1 line 3"
    },
    {
      "step": "subsample_gradient_matrix",
      "operator": "top_left_block_subsample",
      "input": "G_i of shape v x d",
      "output": "G'_i = G_i[:v/8, :d/8]",
      "params": {"row_fraction": "1/8", "col_fraction": "1/8", "selection": "first rows and first columns"},
      "source": "Eq. 2; Sec 3.3; Figure 2 caption; Algorithm 1 line 4"
    },
    {
      "step": "truncated_svd",
      "operator": "randomized_svd_topk",
      "input": "G'_i",
      "output": "top-k singular values sigma_1..sigma_k in descending order (and U_i, V_i)",
      "params": {"k": 16, "algorithm": "randomized SVD (Halko et al., 2011)"},
      "source": "Sec 3.4; Eq. 4; Appendix A; Algorithm 1 line 5"
    },
    {
      "step": "normalize_singular_values",
      "operator": "sv_normalize_to_distribution",
      "input": "top-k singular values",
      "output": "probability vector P = (p_1..p_k)",
      "params": {"eps": 1e-12, "formula": "p_j = max(sigma_j, eps) / sum_l max(sigma_l, eps)"},
      "source": "Eq. 5; Algorithm 1 line 6"
    },
    {
      "step": "spectral_entropy_score",
      "operator": "spectral_entropy",
      "input": "P = (p_1..p_k)",
      "output": "scalar score H_bar_i in [0,1] per sample; score vector of length N",
      "params": {"formula": "H = -sum_j p_j log p_j; H_bar = H / log k"},
      "source": "Eq. 6; Eq. 7; Algorithm 1 line 7"
    },
    {
      "step": "kde_density_estimate",
      "operator": "gaussian_kde",
      "input": "score vector {H_bar_i}, N scalars",
      "output": "density function g_hat(x)",
      "params": {"kernel": "Gaussian", "bandwidth": "h = 1.06 * sigma_hat * N^(-1/5) (Silverman)"},
      "source": "Eq. 9; Sec 3.5 Density Estimation; Algorithm 1 line 9"
    },
    {
      "step": "valley_threshold",
      "operator": "kde_valley_threshold",
      "input": "density g_hat(x)",
      "output": "scalar threshold tau",
      "params": {"formula": "tau = argmin_{x in [x_L, x_R]} g_hat(x)", "x_L": "peak closest to 0", "x_R": "peak closest to 1", "fallback": 0.7},
      "source": "Eq. 10; Sec 3.5 Valley Detection; Sec 4.3; Algorithm 1 line 9"
    },
    {
      "step": "threshold_and_filter_dataset",
      "operator": "threshold_filter_samples",
      "input": "scores {H_bar_i} and tau, dataset D",
      "output": "filtered dataset D_c_hat = {(x_i, y_i) : H_bar_i <= tau}",
      "params": {"rule": "poisoned if H_bar_i > tau else clean"},
      "source": "Eq. 8; Algorithm 1 lines 10-11; Figure 2"
    }
  ],
  "sampling": [
    {"what": "coordinates", "how": "gradient matrix truncated to first 1/8 of rows and first 1/8 of columns", "size": "1/8 x 1/8 of the v x d gradient matrix", "source": "Eq. 2; Sec 3.3; Figure 2 caption"},
    {"what": "layers", "how": "single fixed target module chosen instead of sampling layers", "size": "1 module (lm_head.weight)", "source": "Sec 3.3; Sec 4.4; Table 3"},
    {"what": "probes", "how": "truncated SVD keeps only top-k singular values", "size": "k = 16", "source": "Sec 3.4; Appendix A"},
    {"what": "samples", "how": "no subsampling of samples; every sample in D is scored individually", "size": "all N samples", "source": "Algorithm 1 lines 2-8; Sec 4.5.2"},
    {"what": "rounds", "how": "no round-wise sampling; filtering runs once before training", "size": "1 pass", "source": "Sec 3.1"}
  ],
  "resources": [
    "gradient-capable model snapshot f_theta and its target module weight W (default lm_head.weight); experiments use Llama-2-7B, plus Vicuna-7B-v1.5, Qwen2.5-7B-Instruct, Pythia-6.9B, Mistral, GPT-J-6B, GLM-4-9B (Sec 4.1.4, Fig. 4, Appendix G)",
    "no clean reference dataset, no root dataset, no pretrained detector, no extra model required; KDE threshold uses only the entropy scores of the dataset being filtered (Sec 3.5, Appendix I)",
    "training data must be accessible at filter time (Limitations)",
    "compute: NVIDIA H800 GPUs with 80GB memory each (Appendix B)"
  ],
  "actions": ["filter_samples"],
  "dominant_cost": "one forward-backward pass per sample for the per-sample gradient plus a truncated randomized SVD on the 1/8-subsampled gradient matrix; reported 20-50 ms per sample for a 7B model and total filtering time 99-209 s per dataset (abstract, Sec 4.2, Table 2); complexity O(N(C_fb + Gk)) with O(N) extra memory for scores (Eq. 12, Table 5)",
  "underspecified": [
    "peak detection rule for x_L and x_R (minimum peak separation, smoothing, single-peak behavior) is not defined; only the fallback of 0.7 is given",
    "discretization/resolution of the valley search over [x_L, x_R] in Eq. 10 is not specified",
    "definition of 'clear bimodal structure' (the condition that triggers the 0.7 fallback) has no operational test",
    "Silverman bandwidth behavior when sigma_hat is 0 or N is tiny is not specified",
    "tie handling when H_bar equals tau (Eq. 8 uses strict >, Algorithm 1 uses <=)",
    "randomized SVD hyperparameters (oversampling, power iterations, random seed) and behavior when effective rank < k are not given",
    "batch size / gradient accumulation / mixed precision used for the per-sample backward pass is not stated",
    "whether entropy scores or tau should be cached or recomputed after the base model changes is not stated",
    "all federated aspects: number of clients, per-client shard size, whether tau is global or per-client, whether an extra round trip is needed, and non-IID behavior are not discussed",
    "dataset sizes are inconsistent between Table 4 (WebQA train 3,401) and Figure 3 captions (clean n=3061/3451, poison n=340), so the exact split cannot be recovered"
  ],
  "quotes": [
    {"supports": "step 2 per-sample gradient extraction", "text": "For each sample (xi, yi), we compute the single-sample gradient of the loss with respect to the target module’s parameters: Gi = ∇W L(fθ(xi), yi), (1) where W ∈Rv×d is the weight matrix of the target module."},
    {"supports": "step 3 top-left 1/8 subsampling", "text": "For computational efficiency, we subsample the gradient matrix to its top 1/8 rows and columns following Wu et al. (2025). We systematically evaluate alternative module choices in §4.4."},
    {"supports": "step 4 truncated randomized SVD with k = 16", "text": "For efficiency, we compute only the top-k singular values (k = 16 by default) using randomized SVD (Halko et al., 2011), and provide an analysis in Appendix A. We then normalize the singular values to obtain a probability distribution P = (p1, p2, . . . , pk), where each component pj is defined as:"},
    {"supports": "step 5 normalization with eps = 1e-12", "text": "pj = max(σj, ϵ) Pk l=1 max(σl, ϵ) , (5) where ϵ = 10−12 ensures numerical stability. The spectral entropy is then: H(G′ i) = − k X j=1 pj log pj. (6)"},
    {"supports": "step 6 entropy normalization by log k", "text": "To enable comparison across different gradient scales, we normalize by the maximum entropy: ¯H(G′ i) = H(G′ i) log k ∈[0, 1]. (7) The normalized entropy ¯H measures how uniformly gradient energy spreads across principal directions."},
    {"supports": "step 8 valley threshold between the peaks at 0 and 1", "text": "We locate these peaks and define the threshold as the valley between them: τ = arg min x∈[xL,xR] ˆg(x) (10) where xL and xR are the positions of peaks closest to 0 and 1, respectively."},
    {"supports": "step 9 fallback empirical threshold 0.7", "text": "When a clear bimodal structure is absent (e.g., small sample size or no poisoned samples), the method falls back to a threshold based on empirical values (0.7 by default, analysis in Appendix G)."},
    {"supports": "step 10 poisoned/clean decision and dataset filtering", "text": "A sample is labeled as potential poisoned if its normalized entropy ¯H(G′ i) exceeds a threshold τ: ˆyi = ( poisoned if ¯H(G′ i) > τ, clean otherwise. (8)"}
  ]
}
```
