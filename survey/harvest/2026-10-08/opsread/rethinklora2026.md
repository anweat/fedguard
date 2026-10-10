# rethinklora2026：LA-LoRA（Local Alternating LoRA，本地交替低秩适配）

## 1. 方法一句话

LA-LoRA 是一个在差分隐私联邦学习（DPFL, differentially private federated learning）中微调大模型的训练框架：每个被选中的客户端在本地每一轮内**交替**地只更新 LoRA 的两个低秩矩阵之一（奇数步更新 B、偶数步更新 A），对当前被更新因子的逐样本梯度做 ℓ2 裁剪并注入高斯噪声，再对加噪梯度做固定 1/16[1,4,6,4,1] 的一维高斯低通滤波，用 SGD/AdamW 走一步；K 个本地步结束后把 (A, B) 上传，服务器分别对 A、B 做样本量平均并按 W^t = W0 + s·B^t·A^t 组装全局模型（第 4.1、4.2、4.3 节，式 (7)(8)(9)(10)）。它输出的是每一轮更新后的全局 LoRA 因子与全局权重，不输出"某客户端是恶意"的判定。

## 2. 运行位置

该方法是训练期防御（DP 隐私保护 + 优化轨迹改造），不是检测器，因此没有"检测—剔除"环节。

- **服务器下发前 / 服务器下发（server_distribute）**：服务器持有冻结主干 W0 与上一轮全局低秩因子；客户端在每轮开始时把本地因子初始化为上一轮的全局值（第 4.3 节 "Local client update"："The factors are initialized as A^t_{i,1} ← A^{t−1} and B^t_{i,1} ← B^{t−1}"）。
- **客户端加入（client_announce）**：服务器每轮选取参与集合 Ct，|Ct| = ⌊qN⌋（第 4.3 节 "Server aggregation"，q 为客户端采样率、N 为客户端总数）。
- **客户端训练前（client_pre_train）**：初始化本地因子并冻结 W0（第 4.3 节）。
- **客户端每个训练步（client_step）**：采样小批量 → 只对当前活跃因子求逐样本梯度（式 (8)）→ 逐样本 ℓ2 裁剪 → 批内求和并加高斯噪声（式 (9)）→ 低通滤波（式 (7)）→ 单侧参数更新（第 4.1、4.3 节）。
- **客户端上传前 / 上传（client_post_train）**：K 步之后客户端直接上传已加噪、已平滑的 (A^t_i, B^t_i)，没有额外汇总步骤（第 4.3 节）。
- **服务器收到更新并聚合（server_receive / server_aggregate）**：按客户端数做平均（式 (10)），再组装 W^t = W0 + s·B^t·A^t（第 4.3 节）。
- **聚合之后（server_post_aggregate）**：论文没有额外的后聚合处理；下一轮直接进入新的客户端初始化。
- **额外往返次数**：不需要。整个流程就是标准 FL 的一轮"下发—本地训练—上传—聚合"，滤波是聚合前的客户端本地操作（第 4.2 节 "applied to the LoRA gradients before aggregation"）。
- **分析**：论文附录 A.6 还把同一套交替更新训练用在集中式 DP 训练上（无服务器聚合），说明该方法最自然的位置是"客户端每步 + 服务器聚合"，集中式版本就是把聚合算子去掉、把滤波与裁剪保留在单机训练循环里。

## 3. 算子流水线

下面按执行顺序给出流水线。符号沿用论文：W0 ∈ R^{m×n} 为冻结主干；A ∈ R^{r×n} 为下投影（down-projection）、B ∈ R^{m×r} 为上投影（up-projection）；s = α/r 为 LoRA 缩放因子；r 为秩；t 为通信轮次；k 为本地步；K 为每轮本地步数；d_i^j 为客户端 i 的第 j 条样本；C 为裁剪阈值；σ 为高斯噪声倍率。

**步骤 1：广播全局因子并初始化（broadcast / init）**
- 输入：服务器端全局因子 A^{t−1} ∈ R^{r×n}、B^{t−1} ∈ R^{m×r}，冻结主干 W0。
- 计算：每个被选客户端令 A^t_{i,1} ← A^{t−1}，B^t_{i,1} ← B^{t−1}；W0 全程冻结，只有 BA 被修改；重参数化为 W = W0 + sBA。
- 输出：客户端本地的初始 (A^t_{i,1}, B^t_{i,1})。
- 出处：第 4.3 节 "Local client update"；第 2 节 PEFT 段（W = W0 + sBA，B 零初始化、A 高斯初始化）。

**步骤 2：客户端抽样（client subsample）**
- 输入：客户端总数 N，采样率 q。
- 计算：Ct ⊆ [N]，参与客户端数 |Ct| = ⌊qN⌋。
- 输出：本轮参与集合 Ct。
- 出处：第 4.3 节 "Server aggregation" 段。

**步骤 3：本地小批量抽样（minibatch sample）**
- 输入：客户端本地数据集 Di，规模 R = |Di|，本地数据采样率 b。
- 计算：从 Di 抽 mini-batch Bi ⊂ Di，大小 |Bi| = ⌊bR⌋。论文未说明是否有放回、是否按类分层。
- 输出：一批样本 Bi。
- 出处：第 4.3 节 "At each step k ∈ [K] it samples a mini-batch Bi ⊂ Di of size ⌊bR⌋"。

**步骤 4：逐样本单侧梯度（per-sample gradient）**
- 输入：Bi；当前因子 B^t_{i,k} ∈ R^{m×r}、A^t_{i,k} ∈ R^{r×n}；W0。
- 计算：按 k 的奇偶只对**一个**因子求梯度。奇数步（更新 B）：g_ij = ∇_B L_i(W0 + s·B^t_{i,k}·A^t_{i,k}, d_i^j)（式 (8)）；偶数步（更新 A）：同一形式换成对 A 求梯度。理论上两者的关系是 ∇_A L_i = s·B^⊤(∇_W L_i)、∇_B L_i = s·(∇_W L_i)·A^⊤（式 (5)）。
- 输出：|Bi| 个与当前活跃因子同形状的梯度张量（B 为 m×r，A 为 r×n）。
- 出处：式 (8)（第 4.3 节 "Odd steps (update B)"）；式 (5)（第 4.1 节 Challenge 1）。

**步骤 5：逐样本 ℓ2 裁剪（per-sample clip）**
- 输入：逐样本梯度 g_ij。
- 计算：g_ij ← g_ij / max{1, ‖g_ij‖₂ / C}，即范数超过 C 的样本梯度被缩放到范数恰为 C，未超过的保持不变。
- 输出：裁剪后的逐样本梯度。
- 出处：第 4.3 节 "Perform per-example ℓ2-norm clipping with threshold C"；同样形式见第 2 节式 (2)。裁剪阈值 C 的取法见附录 A.2：按层（per-layer）用中位数裁剪，每层的 C 取该层梯度范数分布的中位数。

**步骤 6：批内求和 + 高斯噪声（sum + Gaussian mechanism）**
- 输入：裁剪后梯度 {g_ij}，裁剪阈值 C，噪声倍率 σ。
- 计算：g_i = (1/(bR))·Σ_{j∈Bi} g_ij + (C/(bR))·N(0, σ²)（式 (9)）。即先对批内裁剪梯度求和，再注入标准差正比于 C 的高斯噪声，最后整体除以 bR。
- 输出：加噪后的低秩梯度 g_i，形状与当前活跃因子相同。
- 出处：式 (9)（第 4.3 节）；σ 的取值见附录 A.2 与 B.2。

**步骤 7：一维高斯低通滤波（1D Gaussian low-pass filter）**
- 输入：加噪梯度 g_i（记为 ∇_A L_i 或 ∇_B L_i 的噪声版本）。
- 计算：固定核 Gs = (1/16)[1, 4, 6, 4, 1]（标准 5 抽头二项式低通滤波器）。对 A ∈ R^{r×n} 沿输入特征维**逐行**做一维卷积：ĝA_i[j, :] = Gs ∗ ∇_A L_i[j, :]，∀j ∈ [1, r]；对 B ∈ R^{m×r} 沿输出维**逐列**做一维卷积：ĝB_i[:, j] = Gs ∗ ∇_B L_i[:, j]，∀j ∈ [1, r]；卷积使用对称填充（symmetric padding）。
- 输出：平滑后的梯度 ĝ_i（ĝ_i = Gs ∗ g_i，第 4.3 节写法）。
- 出处：式 (7)（第 4.2 节）；第 4.3 节 "Smooth the noisy gradient with a fixed operator Gs (low-pass filter) to obtain ĝ_i = Gs ∗ g_i"。
- 说明：论文式 (7) 把滤波写成作用在 ∇_A L_i、∇_B L_i 上，而第 4.3 节与定理 1 的说明都写"对加噪更新做确定性线性变换"，实际应理解为对加噪后的 g_i 做滤波（第 E.1 节 post-processing 论证）。滤波在隐私上不额外消耗预算。

**步骤 8：单侧参数更新（single-factor SGD / AdamW step）**
- 输入：平滑后的梯度 ĝ_i，学习率 η_B 或 η_A。
- 计算：奇数步（k odd）更新 B、冻结 A：B^t_{i,k+1} = B^t_{i,k} − η_B·ĝ_i，A^t_{i,k+1} = A^t_{i,k}；偶数步（k even）更新 A、冻结 B：A^t_{i,k+1} = A^t_{i,k} − η_A·ĝ_i。
- 输出：只有一侧因子被改变的新 (A^t_{i,k}, B^t_{i,k})。
- 出处：第 4.1 节两条更新式；第 4.3 节 "then B^t_{i,k+1} = B^t_{i,k} − η_B·ĝ_i, A^t_{i,k+1} = A^t_{i,k}"。
- 说明：视觉任务用 SGD 且学习率衰减 λ = 0.99，语言任务用 AdamW（第 6.1 节）。

**步骤 9：本地循环与上传（local loop / upload）**
- 输入：k 从 1 到 K 重复步骤 3–8。
- 计算：无额外操作，直接把最终 (A^t_i, B^t_i) 作为上传内容。
- 输出：每客户端一组低秩因子。
- 出处：第 4.3 节 "After K alternating steps, the client returns the locally updated (and smoothed) factors (A^t_i, B^t_i) for server-side aggregation."

**步骤 10：服务器聚合与全局组装（average factors + compose）**
- 输入：|Ct| 组客户端因子 {(A^t_i, B^t_i)}_{i∈Ct}。
- 计算：A^t = (1/|Ct|)·Σ_{i∈Ct} A^t_i；B^t = (1/|Ct|)·Σ_{i∈Ct} B^t_i；随后 W^t = W0 + s·B^t·A^t，T 轮后得到 W^T = W0 + s·B^T·A^T。
- 输出：新的全局因子与全局模型。
- 出处：式 (10)（第 4.3 节 "Server aggregation"）。

**（理论侧的可选算子，论文未说明是否落地）**
- 定理 2 给出闭式"投影梯度"：Ñ_B L = (1/s²)·∇_B L·(A_k A_k^⊤)^{−1}，Ñ_A L = (1/s²)·(B_{k+1}^⊤ B_{k+1})^{−1}·∇_A L（式 (13)），可由最小二乘问题（式 (20)、(22)）解出；第 E.2–E.3 节进一步说明这等价于把全梯度分别投影到 A_k 的行空间与 B_{k+1} 的列空间（式 (14)、(24)–(26)）。论文只写"实际计算退化为构造 r×r 的 Gram 矩阵并求解小线性系统，当 r ≪ min{m,n} 时很轻量"，但没有说明主实验的代码是否真的执行了这个 r×r 求逆预处理，第 4.3 节的算法描述仍是标准梯度下降。

## 4. 采样与规模控制

- **客户端抽样**：每轮从 N 个客户端中选 |Ct| = ⌊qN⌋ 个参与。取值：视觉任务 N = 8、q = 0.5（即每轮 4 个客户端）；语言任务 N = 20、q = 0.2（即每轮 4 个客户端）。出处：第 6.1 节与第 4.3 节。
- **样本抽样**：每个本地步从 Di 中抽大小为 ⌊bR⌋ 的 mini-batch，b 为本地数据采样率、R = |Di|。实验里的 batch size 为 B = 16（视觉与语言任务相同）。出处：第 4.3 节与第 6.1 节。论文未给出 b 的具体数值。
- **层**：不做层抽样，也不做层选择；只训练 LoRA 的 A、B 两个矩阵（外加视觉任务中可训练的分类头）。但裁剪阈值是按层独立设定的中位数（附录 A.2），即每层有自己的 C。
- **参数坐标**：不做坐标抽样；通过 LoRA 秩 r 做降维。视觉任务 r = 16（α = 16），语言任务 r = 8（α = 8）；附录 A.5 另外评测了 r = 8/16/32，说明增大秩可提升表现并缓解 DP 噪声，但会增加通信与计算成本，最终选 r = 16 作为默认。出处：第 6.1 节、附录 A.2、A.5、B.2。
- **轮次 / 本地步**：T = 100 轮固定，每轮 K = 20 个本地步（第 6.1 节）。附录 C.4 对 K ∈ {10, 20, 30, 50} 做了消融，取值来自 Table 17。
- **参考数据 / 探针**：论文未使用。方法不需要公开参考集、根数据集或探针样本；DP 预算由 RDP 会计（Rényi DP accountant）计算，其中对 Rényi 阶 λ 在子采样高斯机制下做网格搜索以选出满足 (ε, δ) 的噪声倍率 σ（附录 A.2），这是隐私参数搜索，不是数据采样。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| N | 客户端总数 | 视觉 8；语言 20 | 第 6.1 节 |
| q | 客户端采样率（每轮选 ⌊qN⌋ 个） | 视觉 0.5；语言 0.2 | 第 6.1 节、第 4.3 节 |
| T | 通信轮数 | 100 | 第 6.1 节 |
| K | 每轮本地步数（交替步总数） | 20；消融 10/20/30/50 | 第 6.1 节、附录 C.4 Table 17 |
| B（batch size） | 本地 mini-batch 大小 | 16 | 第 6.1 节 |
| b | 本地数据采样率（mini-batch 比例） | 论文未给出具体数值（只给出 ⌊bR⌋ 与 batch size 16） | 第 4.3 节、第 6.1 节 |
| r | LoRA 秩 | 视觉 16（另测 8/32）；语言 8 | 第 6.1 节、附录 A.2、A.5、B.2 |
| α | LoRA 缩放超参 | 视觉 16（= r）；语言 8（= r） | 第 6.1 节、附录 A.2、B.2 |
| s = α/r | LoRA 缩放因子 | 由上两行推出（α = r 时 s = 1）；论文未直接给出 s 的数值 | Table 20、第 4.1 节 |
| C | 逐样本 ℓ2 裁剪阈值 | 无数值；按层取该层梯度范数分布的中位数 | 附录 A.2（视觉与语言共用） |
| σ | 高斯噪声倍率 | CIFAR-100：0.195/0.29/0.56；Tiny-ImageNet：0.098/0.146/0.283（对应 ε = 3/2/1）。SST-2：0.36/0.53/1.0；QNLI：0.23/0.34/0.67；QQP：0.073/0.11/0.21；MNLI：0.067/0.10/0.195 | 附录 A.2、B.2 |
| ε | 隐私预算 | 3、2、1 | 第 6.1 节 |
| δ | DP 失败概率 | 视觉与 SST-2、QNLI 为 1e−5；QQP、MNLI 为 1e−6 | 第 6.1 节、附录 B.2 |
| σ_s | "噪声平滑"参数 | 视觉 0.01；语言 0.001；消融 0.000/0.001/0.005/0.010/0.050，推荐语言 0.001–0.005、视觉 0.01–0.05 | 第 6.1 节、附录 D.1 Table 18 |
| Gs 核 | 一维低通滤波核 | (1/16)[1,4,6,4,1]（5 抽头，默认）；另测 (1/4)[1,2,1] 与 (1/64)[1,6,15,20,15,6,1] | 第 4.2 节、附录 D.2 Table 19 |
| η | 学习率 | 视觉从 {1e−2, 2e−2, 1e−1, 2e−1} 中选；语言从 {1e−4, 2e−4, 3e−4, 4e−4, 1e−3, 2e−3, 4e−3} 中选；**最终选中的具体值论文未给出** | 第 6.1 节 |
| λ（decay） | 学习率衰减 | 0.99（视觉 SGD） | 第 6.1 节 |
| 优化器 | 本地优化器 | 视觉 SGD；语言 AdamW | 第 6.1 节 |
| β（Dirichlet） | 非 iid 程度 | 视觉默认 0.1（消融另用 0.6）；语言默认 0.8（另一组实验用 0.3） | 第 6.1 节、Table 6、附录 B.5 |
| 交替策略 | 每轮 B/A 步数排布 | 默认 1-step B / 1-step A；另测 2/2、5/5、5-step A / 5-step B | Table 6 |
| 随机试验次数 | 报告均值 | 视觉 3 次；语言 15 次 | 第 6.1 节 |
| 分类头 | 是否可训练 | 视觉任务"更新 adapter 与分类头"；语言任务冻结分类头 | 第 6.1 节、附录 A.2、B.2 |

## 6. 判定与动作

本方法没有"检测—判决—处置"的判定逻辑，全部动作都是逐样本与逐参数的确定性/随机化变换，直接作用于训练过程：

- **裁剪**：范数超过 C 的逐样本梯度被缩放到范数 C，公式 g_ij ← g_ij / max{1, ‖g_ij‖₂/C}（第 4.3 节、式 (2)）。C 不是固定常数，而是每层梯度范数分布的中位数（附录 A.2）。
- **加噪**：在批内裁剪梯度和上注入 N(0, σ²) 并按 C/(bR) 缩放，σ 由 (ε, δ) 与 RDP 会计反推（式 (9)，附录 A.2/B.2）。加噪是每本地步、每客户端独立进行（第 3.2 节 "NAi and NBi are Gaussian noises independently sampled per client i"）。
- **低通滤波**：对加噪梯度做固定 5 抽头二项式核的一维卷积，按 A 的行、B 的列方向施加（式 (7)）；它是确定性线性变换，按 DP 的后处理不变性不削弱隐私保证（定理 1、附录 E.1）。
- **交替更新（隐式正则）**：每一步只更新一个因子，等价于把该步约束在 A 的列空间或 B 的行空间这一结构化低维子空间内（第 4.1 节 Challenge 3）；论文用它来消除式 (4) 中的乘法噪声项 N_B N_A（式 (6)）。
- **没有**基于阈值/聚类/相似度的客户端剔除或加权：服务器聚合是式 (10) 的等权平均，所有被选客户端权重都是 1/|Ct|。
- **是否跨轮累积**：模型状态跨轮累积（因子逐轮继承，W^t = W0 + s·B^t·A^t），但**隐私预算**跨轮、跨本地步累积，按 RDP 可加性合成后转换（式 (11)：ε = O(b√(TK·log(2/δ)·log(2T/δ))/σ)；对服务器侧还有式 (12) 的 ε_s = ε√(N/q)、δ_s = (δ/2)(1/q + 1)）。
- **无异常判定输出**：方法不产生"恶意/良性"标签，也没有 report_only 形式的报警。

## 7. 需要的外部资源

- **预训练主干 W0**：视觉用 Swin-T（约 28M 参数）与 Swin-B（约 88M 参数），初始化自 ImageNet-22K 预训练权重；语言用 RoBERTa-Base（约 125M 参数，12 层、12 头、hidden 768）；附录 B.4 另在 Llama-2-7B 上验证。出处：第 6.1 节、附录 A.1、B.1、B.4。
- **公开数据集**：CIFAR-100（50,000 训练 / 10,000 测试，32×32）、Tiny-ImageNet（约 100,000 张，64×64）、GLUE 的 SST-2（约 67K 训练句）、QNLI（约 105K 句对）、QQP（约 364K 问题对）、MNLI（约 393K 句对）。出处：附录 A.1、B.1。
- **隐私会计实现**：基于 Rényi DP（RDP）的子采样高斯机制会计与 RDP→(ε, δ) 转换，并沿用 Noble et al. (2022) 的分析；需要对 Rényi 阶 λ 做网格搜索来标定 σ。出处：第 2 节、定理 1、附录 A.2、E.1。
- **不需要**：干净参考数据、根数据集（root dataset）、预训练检测器、对齐前后的权重对、额外的判别模型；也没有探针样本或影子模型。
- **硬件**：所有实验在 NVIDIA A6000 GPU 上完成（第 6 节末）。

## 8. 计算与存储开销

- **论文报告的数值**（Table 7，Swin-B、ε = 1，单位分别为秒/轮与 MB）：
  - LA-LoRA：CIFAR-100 每轮 17.44 s、Tiny-ImageNet 17.23 s，显存 1762 MB；
  - LA-LoRA(-filter)：17.30 s / 17.16 s，1762 MB；
  - 对照 DP-LoRA：30.35 s / 28.02 s，3524 MB；DP-LoRA(+filter)：30.72 s / 28.51 s，3524 MB；FFA-LoRA：17.85 s / 16.54 s；RoLoRA：16.64 s / 16.32 s（FFA-LoRA、RoLoRA 均为 1762 MB）。
  - 论文的结论是：LA-LoRA 每轮耗时与最快的低秩 DP 基线相差最多约 1 s（"it differs by at most about 1 s"），显存相对标准 DP-LoRA 减半（论文归因于低秩参数化），精度显著更高；滤波带来的额外开销可忽略（第 4.2 节 "with negligible overhead"）。
- **分析**：流水线中的主要开销来自步骤 4——每个本地步、mini-batch 中每条样本都要对当前活跃因子做一次前向 + 反向传播以获得逐样本梯度（式 (8) 明确写 "For each example j ∈ Bi, compute the per-example gradient"）。开销随 K × |Bi| × T × |Ct| 线性增长，并且需要保存/累积每条样本的梯度（或按 micro-batch 分组）以完成逐样本裁剪。逐样本裁剪与求和是 O(|Bi|·(mr + rn)) 的逐元素操作；低通滤波是 O(r·n + r·m) 且核长固定为 5，额外成本极低；服务器端平均与组装 W = W0 + sBA 需要一次 (m×r)·(r×n) 的矩阵乘，成本 O(mnr)。论文未说明是否真的执行定理 2 的 r×r Gram 求逆；若执行，每步额外需要 O(r²(m+n) + r³)（分析）。
- **与 DP-LoRA 的差异来源（分析）**：每步只更新一个因子，因此每步只需为一个因子计算并加噪梯度，理论上把每步的反向与加噪规模减半，这与 Table 7 中 17.44 s 对 30.35 s 的实测差距方向一致；论文本身只把显存减半归因于低秩参数化。

## 9. 实现时容易错的地方

**论文明确强调、必须照做的细节**

- 交替顺序：先更新 B（奇数步 k）、再更新 A（偶数步 k）；定理 2 与附录 E.2 明确 "Within iteration k, we update B first and then A"，且更新 A 时用的是**已经更新过 B** 的中间状态 B_{k+1}（式 (13)、(22)），即 A 的投影/预条件要用新的 B，不能沿用旧 B。
- 更新 A 时 B 必须冻结、更新 B 时 A 必须冻结；每一步只对活跃因子构造加噪梯度（第 4.1 节、式 (6)）。
- 噪声必须在**逐样本裁剪之后**加入，且滤波在**加噪之后**、聚合之前（第 4.3 节、定理 1 与附录 E.1 的后处理论证）。顺序颠倒会破坏 DP 保证。
- 滤波作用轴：A 沿输入特征维逐行、B 沿输出维逐列，且"保持不同低秩分量解耦"（第 4.2 节），即卷积只在一个轴上滑动，不能对 A、B 做二维卷积或跨行/跨列混合。
- 逐样本裁剪的形式是 g_ij / max{1, ‖g_ij‖₂/C}，而不是先判断再置零；不要用"超范数直接置零"或"整批裁剪"替代。
- 式 (9) 的噪声标准差是 C/(bR)·σ，随裁剪阈值与批大小缩放，而不是与梯度范数或 σ 单独相关。
- 论文强调滤波只是确定性后处理，不额外消耗隐私预算；实现时不要把滤波计入隐私会计。
- 视觉任务保留分类头可训练（其参数不在 LoRA 因子内），语言任务冻结分类头——两者不能混用同一套设置。

**论文未说明、实现时必须自己决定的地方**

1. 裁剪阈值 C 的具体数值：论文只说取每层梯度范数分布的中位数，但**未说明**该中位数是在一个 mini-batch、一个本地步、一个客户端还是全局、以及是否跨轮滑动统计，也**未说明**按层中位数与"逐样本裁剪"如何配合（是否每层各裁一次）。
2. 本地数据采样率 b 的数值未给出；只给了 batch size B = 16，"⌊bR⌋"与 16 的对应关系未说明（且 B 与 LoRA 上投影矩阵同名，需按上下文区分）。
3. 式 (9) 用 1/(bR) 归一化，而第 2 节式 (2) 用 1/|Bi| 归一化；当 ⌊bR⌋ ≠ bR 时两者不同，实际操作以哪个为准论文未说明。
4. σ_s（"噪声平滑"参数）与固定核 Gs 的数学关系完全未定义：第 4.2 节说核固定为 (1/16)[1,4,6,4,1]，而附录 D.1 又把 σ_s 当平滑强度做敏感性实验（0.000–0.050），却没有给出由 σ_s 生成核的公式。
5. 滤波施加对象存在两种表述：式 (7) 写成对 ∇_A L_i、∇_B L_i 滤波，第 4.3 节和定理 1 的说明写成对加噪更新 g_i 滤波；实现者必须自行选定为"对加噪梯度滤波"。
6. 滤波频率：第 4.3 节描述为每个本地步都执行，第 4.2 节只写"before aggregation"；是每步一次还是每轮上传前一次，论文未给出统一说法。
7. 对称填充（symmetric padding）的边界处理细节未给出（两端各补几个零/如何镜像）。
8. 定理 2 式 (13) 中 (A_k A_k^⊤)^{−1}、(B_{k+1}^⊤ B_{k+1})^{−1} 的预处理是否真的在实现中执行、以及训练早期因子秩不足（Gram 矩阵奇异）时如何处理，论文只在理论里提到可用 Moore-Penrose 逆替换，未说明工程实现。
9. 视觉任务可训练的分类头如何跨客户端聚合（是否与 A、B 一起做式 (10) 的平均）论文未说明；语言任务冻结分类头后其初始值来自哪里也未说明。
10. 第一轮之前初始 A、B 由服务器如何生成与广播（A 高斯、B 零初始化只是 LoRA 的一般描述，联邦初始化协议未写）未说明。
11. K 为奇数时的边界情形未定义（默认 K = 20 为偶数，Table 17 的 K 也都取偶数），最后一个本地步只更新了 B 时是否要补一次 A 未说明。
12. 学习率 η 只给了候选集合，未给出主实验最终选中的值；SGD 的衰减 λ = 0.99 是按轮衰减还是按步衰减、是乘性还是其他形式，论文未说明。
13. 每轮客户端集合 Ct 的抽样方式（是否有放回、是否每轮独立、是否保证每客户端被选次数均衡）未说明，只给了 |Ct| = ⌊qN⌋。
14. 客户端本地数据在非 iid Dirichlet 划分下的具体划分过程（每个客户端样本量的上界、类别分配）论文未展开。
15. RDP 网格搜索中 Rényi 阶 λ 的搜索范围与步长论文未给出，只说明"grid-search the Rényi order λ"。

## 10. 原文依据

说明：PDF 抽取把分式渲染成"分子 分母"两段（例如 1/16 被抽成 "1 16"），下面引用时把这类分式按原意写回 1/16 形式，其余为逐字连续片段。

1. **支撑步骤 8（奇数步更新 B、偶数步更新 A 的交替机制）**："Instead of simultaneously updating both A and B, LA-LoRA adopts an alternating scheme, where the two low-rank matrices are updated in turn within each local training round."
2. **支撑步骤 3（本地 mini-batch 抽样与采样率 b、数据集规模 R）**："At each step k ∈[K] it samples a mini-batch Bi ⊂Di of size ⌊bR⌋. b is the local data sampling rate, R is the size of Di."
3. **支撑步骤 4（对当前活跃因子计算逐样本梯度，式 (8)）**："Odd steps (update B). For each example j ∈Bi, compute the per-example gradient gij = ∇B Li (W0 + sBt i,kAt i,k, di j ),"
4. **支撑步骤 5 与步骤 6（逐样本 ℓ2 裁剪后批内求和并注入高斯噪声）**："Perform per-example ℓ2-norm clipping with threshold C: gij ←gij/ max{1, ∥gij∥2/C}. Aggregate over the mini-batch and inject Gaussian noise to ensure DP:"
5. **支撑步骤 7（固定 5 抽头二项式低通滤波核 Gs）**："Specifically, we adopt a fixed 1D Gaussian kernel Gs = 1/16[1, 4, 6, 4, 1], i.e., the standard 5-tap binomial low-pass filter."
6. **支撑步骤 7（滤波作用轴：A 逐行沿输入维、B 逐列沿输出维）**："For A ∈Rr×n, smoothing is applied row-wise along the input feature dimension; for B ∈Rm×r, smoothing is applied column-wise along the output dimension."
7. **支撑步骤 5 的具体实现（按层中位数确定裁剪阈值 C）**："Gradient clipping is performed on a per-layer basis using a median clipping strategy, where each layer's clipping threshold C is set to the median of its gradient norm distribution"
8. **支撑步骤 10（服务器对 A、B 分别平均并组装全局模型，式 (10)）**："The server averages client uploads: At = 1/|Ct| X i∈Ct At i, Bt = 1/|Ct| X i∈Ct Bt i, and then updates the global model as W t = W0 + sBtAt."

```json
{
  "key": "rethinklora2026",
  "method": "LA-LoRA（Local Alternating LoRA）：在 DPFL 中每个本地步只交替更新 LoRA 的一个低秩因子，逐样本裁剪 + 高斯加噪 + 固定 1D 高斯低通滤波，服务器分别平均 A、B 后组装 W = W0 + sBA",
  "stages": ["server_distribute", "client_announce", "client_pre_train", "client_step", "client_post_train", "server_receive", "server_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "服务器下发全局 LoRA 因子并由客户端初始化，冻结主干 W0",
      "operator": "broadcast_lora_factors",
      "input": "上一轮全局因子 A^(t-1) ∈ R^(r×n)、B^(t-1) ∈ R^(m×r)；冻结主干 W0",
      "output": "客户端本地初始因子 A^t_{i,1}、B^t_{i,1}",
      "params": {"r": "视觉 16；语言 8", "alpha": "视觉 16；语言 8", "s": "alpha/r"},
      "source": "第 4.3 节 Local client update；第 2 节 PEFT 段 W = W0 + sBA"
    },
    {
      "step": "服务器每轮抽样参与客户端",
      "operator": "client_subsample",
      "input": "客户端总数 N，采样率 q",
      "output": "参与集合 Ct ⊆ [N]，|Ct| = floor(qN)",
      "params": {"N": "视觉 8；语言 20", "q": "视觉 0.5；语言 0.2"},
      "source": "第 4.3 节 Server aggregation 段"
    },
    {
      "step": "客户端每步抽本地 mini-batch",
      "operator": "minibatch_sample",
      "input": "本地数据集 Di，规模 R = |Di|，本地采样率 b",
      "output": "mini-batch Bi ⊂ Di，大小 floor(bR)",
      "params": {"b": "论文未给出数值", "batch_size": 16},
      "source": "第 4.3 节；第 6.1 节 batch size B = 16"
    },
    {
      "step": "对当前活跃因子逐样本求梯度（奇数步对 B，偶数步对 A）",
      "operator": "per_sample_lora_gradient",
      "input": "Bi；B^t_{i,k}、A^t_{i,k}；W0；单条样本 d_i^j",
      "output": "|Bi| 个与活跃因子同形状的梯度（B: m×r 或 A: r×n）",
      "params": {"schedule": "k 奇数更新 B，k 偶数更新 A", "K": 20},
      "source": "式 (8)；第 4.1 节两条更新式；式 (5)"
    },
    {
      "step": "逐样本 ℓ2 范数裁剪",
      "operator": "clip_per_sample_gradient",
      "input": "逐样本梯度 g_ij",
      "output": "裁剪后梯度 g_ij / max(1, ||g_ij||_2 / C)",
      "params": {"C": "按层取该层梯度范数分布的中位数，论文未给出数值"},
      "source": "第 4.3 节；式 (2)；附录 A.2"
    },
    {
      "step": "批内求和并注入高斯噪声",
      "operator": "gaussian_mechanism",
      "input": "裁剪后梯度集合 {g_ij}，阈值 C，噪声倍率 σ",
      "output": "加噪梯度 g_i = (1/(bR))·Σ g_ij + (C/(bR))·N(0, σ^2)",
      "params": {"sigma": "CIFAR-100 0.195/0.29/0.56；Tiny-ImageNet 0.098/0.146/0.283；SST-2 0.36/0.53/1.0；QNLI 0.23/0.34/0.67；QQP 0.073/0.11/0.21；MNLI 0.067/0.10/0.195（对应 ε=3/2/1）", "epsilon": "3/2/1", "delta": "1e-5 或 1e-6"},
      "source": "式 (9)；附录 A.2、B.2"
    },
    {
      "step": "沿特征维做一维高斯低通滤波",
      "operator": "conv1d_lowpass_rowcol",
      "input": "加噪梯度 g_i（A 为 r×n，B 为 m×r）",
      "output": "平滑梯度 ĝ_i；A 逐行卷积、B 逐列卷积",
      "params": {"kernel": "(1/16)[1,4,6,4,1]（5 抽头二项式）", "padding": "symmetric", "alt_kernels": "(1/4)[1,2,1]、(1/64)[1,6,15,20,15,6,1]", "sigma_s": "视觉 0.01；语言 0.001（与核的关系论文未说明）"},
      "source": "式 (7)；第 4.2 节；第 4.3 节；附录 D.1、D.2"
    },
    {
      "step": "单侧因子更新（另一因子冻结）",
      "operator": "alternating_single_factor_step",
      "input": "平滑梯度 ĝ_i，学习率 η_B 或 η_A",
      "output": "更新后的 (A^t_{i,k+1}, B^t_{i,k+1})",
      "params": {"optimizer": "视觉 SGD（decay 0.99）；语言 AdamW", "eta": "视觉 {1e-2,2e-2,1e-1,2e-1}；语言 {1e-4,2e-4,3e-4,4e-4,1e-3,2e-3,4e-3}，最终取值论文未给出"},
      "source": "第 4.1 节；第 4.3 节；第 6.1 节"
    },
    {
      "step": "K 步后客户端上传本地因子",
      "operator": "upload_lora_factors",
      "input": "本地训练结束的 (A^t_i, B^t_i)",
      "output": "上传到服务器的低秩因子（已加噪、已平滑）",
      "params": {"K": 20},
      "source": "第 4.3 节 After K alternating steps, the client returns ..."
    },
    {
      "step": "服务器分别平均 A、B 并组装全局模型",
      "operator": "average_low_rank_factors",
      "input": "|Ct| 组客户端因子 {(A^t_i, B^t_i)}",
      "output": "A^t、B^t 与 W^t = W0 + s·B^t·A^t",
      "params": {"aggregation": "等权算术平均，权重 1/|Ct|", "T": 100},
      "source": "式 (10)；第 4.3 节 Server aggregation"
    }
  ],
  "sampling": [
    {"what": "clients", "how": "每轮均匀抽取参与集合 Ct，|Ct| = floor(qN)", "size": "视觉 N=8、q=0.5（每轮 4 个）；语言 N=20、q=0.2（每轮 4 个）"},
    {"what": "samples", "how": "每个本地步从 Di 抽 mini-batch Bi ⊂ Di，大小 floor(bR)", "size": "batch size B = 16；采样率 b 的数值论文未给出"},
    {"what": "layers", "how": "不做层抽样；但裁剪阈值按层独立取该层梯度范数分布的中位数", "size": "每层一个 C，数值论文未给出"},
    {"what": "coordinates", "how": "不做坐标抽样；通过 LoRA 秩 r 将可训练参数降维到 A ∈ R^(r×n) 与 B ∈ R^(m×r)", "size": "视觉 r=16（消融 8/16/32）；语言 r=8"},
    {"what": "rounds", "how": "固定 T 轮，每轮 K 个本地步；对 K 做过消融", "size": "T=100，K=20（消融 K=10/20/30/50）"},
    {"what": "probes", "how": "论文未使用", "size": "论文未使用"}
  ],
  "resources": [
    "预训练主干 W0：Swin-T（约 28M）、Swin-B（约 88M，ImageNet-22K 初始化）、RoBERTa-Base（约 125M）、Llama-2-7B",
    "公开数据集：CIFAR-100、Tiny-ImageNet、GLUE 的 SST-2/QNLI/QQP/MNLI",
    "Rényi DP 会计实现（子采样高斯机制 + RDP 到 (epsilon, delta) 转换，沿用 Noble et al. 2022）",
    "对 Rényi 阶 λ 做网格搜索以标定 σ 的离线流程",
    "NVIDIA A6000 GPU",
    "不需要干净参考数据、根数据集、预训练检测器、对齐前后权重或额外判别模型"
  ],
  "actions": ["clip", "add_noise", "transform_gradients"],
  "dominant_cost": "每个本地步、mini-batch 中每条样本对当前活跃因子做一次前向与反向传播以取得逐样本梯度（式 (8)），成本随 T×K×|Ct|×|Bi| 线性增长；论文实测 Swin-B 在 ε=1 下每轮 17.44 s（CIFAR-100）与 17.23 s（Tiny-ImageNet）、显存 1762 MB，低于 DP-LoRA 的 30.35 s/28.02 s 与 3524 MB；低通滤波因核长固定为 5 而开销可忽略（第 4.2 节称 negligible overhead）",
  "underspecified": [
    "裁剪阈值 C 的具体数值未给出；只说明按层取梯度范数分布的中位数，未说明中位数的统计范围（batch/客户端/轮次）与是否跨轮滑动",
    "本地数据采样率 b 无数值，只给出 batch size B = 16 与 floor(bR) 的形式，两者对应关系未说明",
    "式 (9) 用 1/(bR) 归一化而式 (2) 用 1/|Bi| 归一化，实际采用哪一个未说明",
    "平滑参数 sigma_s 与固定核 Gs 的数学关系未定义（第 4.2 节说核固定，附录 D.1 又对 sigma_s 做敏感性实验）",
    "滤波对象表述不一致：式 (7) 写成对梯度 ∇A L、∇B L 滤波，第 4.3 节写成对加噪梯度 g_i 滤波",
    "滤波频率未统一：4.3 节描述为每个本地步执行，4.2 节只写 before aggregation",
    "对称填充的具体边界处理未给出",
    "定理 2 式 (13) 的 Gram 矩阵求逆预处理是否在实现中执行未说明；秩不足时的 Moore-Penrose 替换只在理论中提及",
    "视觉任务可训练分类头的聚合方式、语言任务冻结分类头的初始来源均未说明",
    "联邦训练开始前初始 A、B 由服务器如何生成与广播未说明",
    "K 为奇数时最后一个本地步的收尾规则未定义",
    "学习率 eta 最终选中的具体值未给出；decay 0.99 是按轮还是按步、以何形式施加未说明",
    "每轮客户端抽样是否有放回、是否独立抽样未说明",
    "非 iid Dirichlet 划分的具体过程（每客户端样本量、类别分配）未展开",
    "RDP 网格搜索中 Rényi 阶 λ 的搜索范围与步长未给出"
  ],
  "quotes": [
    {"supports": "步骤 8：本地交替更新机制（同一轮内轮流更新 A、B）", "text": "Instead of simultaneously updating both A and B, LA-LoRA adopts an alternating scheme, where the two low-rank matrices are updated in turn within each local training round."},
    {"supports": "步骤 3：本地 mini-batch 抽样及采样率 b 与本地数据集规模 R", "text": "At each step k ∈[K] it samples a mini-batch Bi ⊂Di of size ⌊bR⌋. b is the local data sampling rate, R is the size of Di."},
    {"supports": "步骤 4：只对当前活跃因子计算逐样本梯度（式 (8)，奇数步更新 B）", "text": "Odd steps (update B). For each example j ∈Bi, compute the per-example gradient gij = ∇B Li (W0 + sBt i,kAt i,k, di j ),"},
    {"supports": "步骤 5 与步骤 6：逐样本 ℓ2 裁剪后批内求和并注入高斯噪声", "text": "Perform per-example ℓ2-norm clipping with threshold C: gij ←gij/ max{1, ∥gij∥2/C}. Aggregate over the mini-batch and inject Gaussian noise to ensure DP:"},
    {"supports": "步骤 7：固定 5 抽头二项式高斯低通滤波核", "text": "Specifically, we adopt a fixed 1D Gaussian kernel Gs = 1/16[1, 4, 6, 4, 1], i.e., the standard 5-tap binomial low-pass filter."},
    {"supports": "步骤 7：滤波作用轴为 A 逐行、B 逐列", "text": "For A ∈Rr×n, smoothing is applied row-wise along the input feature dimension; for B ∈Rm×r, smoothing is applied column-wise along the output dimension."},
    {"supports": "步骤 5：裁剪阈值的按层中位数实现", "text": "Gradient clipping is performed on a per-layer basis using a median clipping strategy, where each layer's clipping threshold C is set to the median of its gradient norm distribution"},
    {"supports": "步骤 10：服务器对 A、B 分别平均并组装全局模型（式 (10)）", "text": "The server averages client uploads: At = 1/|Ct| X i∈Ct At i, Bt = 1/|Ct| X i∈Ct Bt i, and then updates the global model as W t = W0 + sBtAt."}
  ]
}
```
