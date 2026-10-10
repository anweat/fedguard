# protegofed2026：ProtegoFed

## 1. 方法一句话

ProtegoFed 输入每个客户端本地的指令微调数据（instruction tuning data，形如问答对）以及服务器广播的初始全局 LoRA（Low-Rank Adaptation）模块 P0，在正式联邦训练开始前一次性输出"净化后的本地数据集"：客户端对本地每条样本计算目标模块上的逐样本梯度（per-sample gradient），做二维离散余弦变换（2D discrete cosine transform，2D-DCT）后在频域聚类，把主簇质心（centroid）上报服务器；服务器对所有客户端的质心做二次聚类得到"全局质心"（global centroid）并广播；客户端再以全局质心为锚点重聚类，删除不属于干净簇的样本，之后按标准 FIT（Federated Instruction Tuning）流程在剩余数据上训练（Section V-A、V-B、V-C、V-D）。

## 2. 运行位置

- **阶段一 客户端内频域聚类（Intra-Client frequency-based clustering）**：运行在**客户端训练前**。位置是"服务器下发 P0 之后、第 1 轮本地训练之前"。论文原文为 "Before the first round, after collecting the global model P0, each client first obtains a representation of the local feature..."（Section V-A），因此它属于标准 FIT 第 1 步（广播全局模型，Section II-A）与第 2 步（本地训练，式 1）之间的插入阶段。
- **阶段二 全局二次聚类（Global secondary clustering）**：运行在**服务器收到各客户端质心之后**。注意此时还没有任何模型更新产生，服务器收到的是 K 个质心而不是模型更新，也不是常规意义上的"聚合"（Section V-A、V-C）。
- **阶段三 本地修正（Local revising）**：运行在**客户端上传前**（更准确说是"客户端收到全局质心之后、本地训练之前"），产出过滤后的数据集 D^clean_k，随后才进入正常的本地训练（Section V-D、式 15）。
- **额外往返**：**需要**一次标准 FIT 之外的往返：客户端 → 服务器上传本地主簇质心 c_k，服务器 → 客户端广播全局质心 c_g（Figure 5；Section V-B "we use the centroid of the main cluster ... and send it to the server"；Section V-C "The global centroid cg is then broadcast to all clients"）。该往返只发生一次，不随通信轮次重复："ProtegoFed is executed only once at the beginning of training"（Section V-A）。
- **训练之外**：整个防御是一次性的、在训练开始前完成的预处理，但它依赖联邦流程本身（用广播的 P0 计算梯度、用服务器做全局协调），因此不是脱离训练的离线审计。论文在 Section VII-B 说明：客户端中途退出不影响已完成的一次性过滤；新加入的客户端可用已建立的全局质心再跑一次阶段二到阶段三（0.07 s + 0.39 s）来单独更新自己的过滤结果。

## 3. 算子流水线

以下按执行顺序列出，T×d 记法统一为"样本数 × 特征维数"。

**步骤 1：接收初始全局模型并选定观测模块（select_target_module）**
- 输入：服务器广播的初始全局 LoRA 模块 P0；候选模块集合（transformer 块内各层的 lora_A/lora_B、块外的 embed_tokens 与 lm_head）。
- 计算：不做数值计算，只做模块选择——取**最后一个 transformer 层**中注意力的 value 投影的 lora_B（论文写作 `lora_B in the last transformer layer`；Table IX 明确记为 `model.layers.31.self_attn.v_proj.lora_B`，Table IV 记为 `self_attn.v_proj.lora_B`）。论文给出的理由是深层会放高频域梯度差异（Section V-B，引 [57]）。
- 输出：目标模块张量，其参数个数为 d。
- 出处：Section V-A、V-B；Section VI-D3；Table IV；Table IX。

**步骤 2：逐样本反向传播取梯度（per_sample_gradient）**
- 输入：客户端 c_k 的私有指令微调数据集 D_k = {(Q_k, A_k)}，展开为 N 条问答对 {(q^i_k, a^i_k)}_{i=1}^N，以及 P0。
- 计算：对每条样本单独做一次前向 + 反向传播，用本地损失 L_k 求目标模块参数的梯度 g^i_k。论文写 "each client uses local private data to do single-sample backpropagation"（Section V-B），并在式 6 中把 g^i_k 直接送进 DCT。
- 输出：N 个逐样本梯度 {g^i_k}_{i=1}^N，每个的维数等于目标模块参数数 d（Table IX 的配置下 d = 16,384）。
- 出处：Section V-B；式 6 上文；式 1 给出本地损失的定义背景。

**步骤 3：二维 DCT 与展平（dct_2d）**
- 输入：每个样本的梯度，论文在式 5 中一般化地写作矩阵 g ∈ R^{M×N}。
- 计算：式 5 给出 ĝ = C_M · g · C_N^T，其中 C_D 是 D 维 DCT 变换矩阵，C_D(k,n) = α_k · cos((2n+1)kπ / (2D))，α_k = sqrt((1 + (1 − I(k=0))) / D)，I(·) 为指示函数。随后式 6 写作 ĝ^i_k = DCT(g^i_k)，式 7 展平为 f^i_k = flatten(ĝ^i_k)。论文的直觉是：后门映射（many-to-one，式 4）比干净映射（many-to-many，式 3）更偏向低频、收敛更快，因此频域表示更具可分性（Section II-C、Section V-A）。
- 输出：每个样本的频域特征向量 f^i_k，维数 d。
- 出处：式 5、式 6、式 7；Section II-C。

**步骤 4：UMAP 降维到二维（umap_2d）**
- 输入：N×d 的频域特征矩阵 {f^i_k}_{i=1}^N。
- 计算：ef^i_k = UMAP(f^i_k)（式 8），把特征降到 2 维。理由是"增强不同样本特征之间的区分度、让聚类算法表现更好"，并在 Section VI-D6/Figure 12 论证降到低维时具体维度选择影响不大、"For the convenience of visualization, we use 2 dimensions"。
- 输出：N×2 的降维特征 {ef^i_k}_{i=1}^N。
- 出处：式 8；Section V-B；Section VI-D6。

**步骤 5：本地双聚类集成与轮廓系数（silhouette score）门控（dual_clustering_silhouette_select）**
- 输入：{ef^i_k}_{i=1}^N（N×2）。
- 计算：并行跑两种聚类——(a) 层次聚类（hierarchical clustering），簇数固定为 2（主簇与次簇）；(b) HDBSCAN，簇数由算法自行决定；然后取轮廓系数更高的那个结果（Section V-B；式 9：G^1_k,(G^2_k,···) = Cluster({ef^i_k})）。门控规则：记两个轮廓系数为 s_small、s_large，论文取 t_s = 0.2、t_l = 0.4，当 **s_small < t_s 且 s_large < t_l**（作者称 weak plausibility）时，认为没有足够依据强行分簇，把该客户端**全部数据视为干净数据**（不做任何删除），以降低假阳性（FP）。
- 输出：每个样本的簇标签；或"全部干净"的退化结论。
- 出处：Section V-B；式 9；Section VI-D4、Table X（分别去掉 HDBSCAN、层次聚类、阈值三种消融）。

**步骤 6：主簇质心，在原始频域维度上计算（main_cluster_centroid）**
- 输入：主簇样本的**原始**频域特征 {f^i_k}（不是降维后的 {ef^i_k}）。
- 计算：c_k = Centroid({f^i_k})，约束为 ef^i_k ∈ G^1_k（式 10），即"用降维后的坐标决定谁属于主簇，但用原始频域维度求均值"。论文强调：不同客户端的 UMAP 是各自独立拟合的，降维后的空间彼此不可比，所以跨客户端融合必须回到原始频域维度（Section V-B）。主簇的确定规则：层次聚类时 G^1_k 是 "primary cluster"；HDBSCAN 时 G^1_k 是样本数最多的簇（Section V-B）。
- 输出：一个 d 维质心 c_k（论文指出该质心不对应任何真实样本）。
- 出处：式 9、式 10；Section V-B。

**步骤 7：上传本地质心（send_local_centroid）**
- 输入：c_k ∈ R^d。
- 计算：仅通信，无计算。客户端只上传主簇质心这一"本地特征的表示"，作为隐私与效率的折中（Section V-B）。
- 输出：服务器端收到 {c_1, c_2, ..., c_K}，K×d。
- 出处：Section V-A、V-B；Figure 5。

**步骤 8：服务器对质心做二次聚类（secondary_cluster_centroids）**
- 输入：{c_1, ..., c_K}（K×d）。
- 计算：先降维 ec_1, ..., ec_K = UMAP(c_1, ..., c_K)（式 11），再聚类 G^1_II,(G^2_II,···) = Cluster({ec_1, ..., ec_K})（式 12），取主簇 G^1_II。目的是排除本地聚类被中毒数据主导、质心落到中毒区域的个别客户端的影响（Section V-C、Figure 4(b)）。论文原文只写"applies dimension reduction and secondary clustering"，未说明服务器端是否也使用与客户端相同的"层次聚类 + HDBSCAN + 轮廓系数"集成。
- 输出：主簇客户端集合 G^1_II。
- 出处：式 11、式 12；Section V-A、V-C。

**步骤 9：计算全局质心（global_centroid）**
- 输入：主簇内客户端的**原始维度**质心 {c_j : ec_j ∈ G^1_II}。
- 计算：c_g = Centroid({c_j})（式 13）。同样强调用原始维度求均值，保证服务器与客户端特征在同一空间（Section V-C）。
- 输出：一个 d 维全局质心 c_g。
- 出处：式 13；Section V-C。

**步骤 10：广播全局质心（broadcast_global_centroid）**
- 输入：c_g ∈ R^d。
- 计算：仅通信。
- 输出：所有客户端（含质心被排除在外的客户端）都收到 c_g。
- 出处：Section V-A、V-C。

**步骤 11：本地重聚类，以全局质心为锚点（local_recluster_with_anchor）**
- 输入：全局质心 c_g 与本地原始频域特征 {f^i_k}_{i=1}^N。
- 计算：把 c_g 当作**一条额外样本**加入本地频域特征（"The global centroid will be added as a sample to the local features for re-clustering"），然后"perform dimensionality reduction and clustering steps"（Section V-D），即再次执行 UMAP + 聚类：Gr^1_k,(Gr^2_k,···) = Cluster(c_g ∪ {f^i_k}_{i=1}^N)（式 14）。Section V-D 开头写明"Similarly to the process of Intra-Client frequency-based clustering"，暗示沿用同一套聚类流程，但未明确是否重跑轮廓系数门控。
- 输出：包含 c_g 的那个簇（视为干净簇）。
- 出处：式 14；Section V-A、V-D。

**步骤 12：按簇过滤样本（filter_to_clean_cluster）**
- 输入：本地数据集 D_k 与重聚类标签。
- 计算：D^clean_k = {(q, a) ∈ D_k | (q, a) ∈ Gr_k, c_g ∈ Gr_k}（式 15），即只保留与全局质心同簇的样本，其余样本从本地训练集中删除。
- 输出：净化后的本地数据集 D^clean_k。
- 出处：式 15；Section V-D。

**步骤 13：在净化数据上执行标准 FIT（fedavg_train）**
- 输入：D^clean_k 与全局 LoRA 模块 P^i。
- 计算：客户端本地更新 P^i_k = P^i − η·∂L_k/∂P^i（式 1），服务器按样本量加权平均 P^{i+1} = Σ_{k=1}^{K} (n_k/n)·P^i_k（式 2，FedAvg）。收敛性分析中式 16 把本地目标写成在过滤后子集 D̃_k 上的经验风险，并给出定理 1 的收敛上界（式 17）。
- 输出：训练完成的全局模型。
- 出处：式 1、式 2、式 16、式 17；Section II-A、V-E。

## 4. 采样与规模控制

- **层与参数坐标的截断**：只在最后一层 `self_attn.v_proj.lora_B` 上取梯度，其余参数完全不参与；Table IX 报告该模块参数量为 16,384，而备选的 embed_tokens / lm_head 为 131,072,000（约 8000 倍），因此论文未采用后者（Table IX；Section VI-D3）。
- **UMAP 降维**：d 维频域特征降到 2 维后再聚类（Section V-B；Section VI-D6、Figure 12）。这是明确的降维而非抽样。
- **样本**：论文未对本地样本做抽样或截断，逐样本反向传播覆盖本地每条训练样本（"for each training sample"）。数据集层面，除 WebQA 外每个数据集随机抽 5,000 条训练、400 条验证、2,000 条测试（Section VI-A1）；IID 主实验把训练数据均分给 25 个客户端，每个客户端数据量很小（Section VI-A3）。
- **轮次**：防御只在训练开始前执行一次（1 次），不随 100 个通信轮次重复（Section V-A；Section VII-A；Figure 5 标题 "before training begins"）。
- **探针/参考数据**：论文不使用参考数据或探针样本；服务器不需要辅助干净数据集（Section III-B2 "The server does not require an auxiliary clean dataset or model training"）。客户端用本地样本梯度合成的"虚拟质心"代表本地特征（Section I RQ1："We use the virtual centroid synthesized locally by the client as the representation of the local feature"）。
- **客户端**：K 个客户端各上传 1 个 d 维质心；服务器二次聚类后只保留主簇内的质心用于计算全局质心，主簇规模论文未说明（Section V-C）。
- **簇数**：客户端层次聚类固定 2 簇；HDBSCAN 簇数由算法决定，论文未说明其内部规模参数（Section V-B）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| 目标模块 | 计算逐样本梯度的观测模块 | 最后一层 transformer 的 `self_attn.v_proj.lora_B`（Table IX 记为 `model.layers.31.self_attn.v_proj.lora_B`） | Section V-A、V-B；Section VI-D3；Table IV；Table IX |
| 主簇簇数 | 层次聚类的簇数 | 2（主簇与次簇） | Section V-B |
| HDBSCAN 簇数 | 第二路聚类的簇数 | 由算法自行决定（无固定值） | Section V-B |
| t_s | 轮廓系数保守下界（小者阈值） | 0.2 | Section V-B |
| t_l | 轮廓系数弱可信上界（大者阈值） | 0.4 | Section V-B |
| UMAP 目标维度 | 频域特征降维后的维数 | 2（Figure 12 显示更低维时维度选择影响很小） | Section V-B；Section VI-D6、Figure 12 |
| LoRA 秩 r | LoRA 内部秩 | 4 | Section VI-A7 |
| 本地 epoch | 每轮本地训练轮数 | 1 | Section VI-A7 |
| 通信轮数 | FL 总轮数 | 100 | Section VI-A7 |
| 学习率 η | 本地学习率 | 2×10⁻⁵ | Section VI-A7 |
| 客户端数 K | IID 主实验客户端数 | 25 | Section VI-A3 |
| IID 中毒比例 | 每个客户端本地中毒样本占比 | 10%（10% poison ratio） | Section VI-A3 |
| NIID-1 中毒比例 | 每客户端中毒比例从区间随机采样 | [0, 0.4] | Section VI-D2 |
| NIID-2 中毒比例 | 按 Dirichlet 分布采样并设上限 | α = 0.5，本地中毒比例上限 0.5 | Section VI-D2 |
| NIID-3 中毒比例 | 去掉 0.5 上限 | 无上限 | Section VI-D2 |
| Dirichlet α 取值 | 检测性能评估 | α ∈ {0.1, 0.3, 0.7, 1.0} | Table VII |
| 后门探针设定（评测用） | 自适应攻击实验中同一触发器映射到 4 个目标输出 | 4 个目标输出 | Section VII-C、Table XI |

论文未说明的超参数：UMAP 的 `n_neighbors`、`min_dist`、随机种子；HDBSCAN 的 `min_cluster_size` 等；轮廓系数所用的距离度量；服务器端二次聚类是否复用同样的阈值与集成策略。Table IX 提到对 embed_tokens / lm_head 作为目标模块时会先用 PCA 降维（沿用 [54] 的做法），但这不是主实验配置。

## 6. 判定与动作

- **客户端级判定（阶段一）**：跑层次聚类（2 簇）与 HDBSCAN 两路，取轮廓系数更高者作为最终分簇；主簇之外的样本被判定为疑似中毒。若 s_small < 0.2 且 s_large < 0.4，则判定"证据不足"，该客户端全部数据视为干净、不做删除（Section V-B；Table X 的 "w/o Threshold" 消融显示该门控主要影响 F1）。
- **服务器级判定（阶段二）**：对 K 个客户端质心先 UMAP 再聚类，只有落在主簇 G^1_II 内的质心参与全局质心 c_g 的计算（式 12、式 13）。这相当于在**质心层面排除**被中毒数据主导的客户端（论文原文："This is to exclude the impact of individual clients with serious data poisoning"，Section V-A），但被排除的客户端仍然照常参与后续模型训练与聚合。
- **最终动作（阶段三）**：客户端把 c_g 作为额外样本加入本地特征重聚类，含 c_g 的簇判为干净簇，其余样本从本地数据集中**删除**（式 15）。动作是纯粹的数据过滤（filter_samples），论文没有使用裁剪（clip）、加噪（add_noise）、按客户端加权（reweight）或替换全局模型（replace_global）等操作。
- **跨轮累积**：没有跨轮累积，防御只执行一次（Section V-A、VII-A）。
- **效果数值**：论文报告 ProtegoFed 识别 92.00%～100.00% 的中毒样本、ASR 降到接近 0，并保持主任务效用（Abstract；Table II、Table III）。Table VIII 显示在没有全局修正时（w/o revise）准确率仅 45.90%、召回 11.09%，加上全局二次聚类 + 本地修正后准确率 99.29%、召回 98.76%，说明"全局质心 + 本地修正"这一步是判定正确性的关键。
- **边界条件**：该方法的前提是干净数据在多数客户端占主导；当所有客户端的数据都以中毒数据为主时防御失效（Section VI-D2、Figure 6）。NIID-3（去掉中毒比例上限）下仍能纠正客户端级误判，但依赖"多数客户端能提供准确本地质心"（Section VI-D2、Table VIII）。
- **指标口径提醒**：论文对 Recall 的文字定义写成"被误判为干净的毒样本比例"（Section VI-C），与其表格数值方向相反，应为笔误；正文提到的 CBA/WebQA F1 为 79.12%，而 Table III 该格为 82.71%，复现时以表格为准需自行核对。

## 7. 需要的外部资源

- **不需要干净参考数据、根数据集（root dataset）或预训练检测器**：Section III-B2 明确 "The server does not require an auxiliary clean dataset or model training"。
- **不需要额外模型**：检测所用的特征来自正在被微调的 LLM 本身（初始全局 LoRA 模块 P0）；被评测模型覆盖 Llama-3.2-1B/3B、GPT-J-6B、Llama-2-7B/13B/70B、Vicuna-7B、Mistral-7B、Gemma-2-9B（Section VI-A2、Table IV）。
- **需要的数据/模型**：每个客户端的本地指令微调数据集 D_k 与广播的 P0；客户端的本地损失函数 L_k（式 1）。
- **需要的算法库**：客户端与服务器均需 UMAP、HDBSCAN、层次聚类、轮廓系数实现（Section V-B、V-C 引用 [58]）。论文未指明具体软件实现。
- **通信资源规模**：K 个 d 维质心上传（K×d）+ 1 个 d 维全局质心广播；在 Table IX 的配置下 d = 16,384，IID 主实验 K = 25（Section V-B、V-C；Table IX；Section VI-A3）。论文强调上传的质心"does not correspond to any real sample"，是隐私考量（Section V-B）。

## 8. 计算与存储开销

- **论文报告的开销**（Section VII-A、Figure 13）：训练开始前的一次性开销为 Intra-Client Clustering 12.43 秒、Global Clustering 0.07 秒、Local Revising 0.39 秒；虽然多出这部分开销，100 轮的总训练时间反而比 FedAvg 基线更短，因为删除了中毒数据、缩小了训练集；论文称该一次性开销约占总训练时间的 1%。
- **论文报告的复杂度**（Section VI-D7）：核心组件 UMAP 与 HDBSCAN 的复杂度约为 O(N log N)，N 为样本数，对客户端而言计算量不大；客户端做梯度时的峰值显存不超过正常训练流程的峰值（论文同时注明 "We will add a part to further demonstrate its practicality"，即该论证尚不完整）。
- **论文报告的目标模块代价**（Table IX）：`layers.31.lora_B` 为 16,384 个参数；embed_tokens / lm_head 为 131,072,000 个参数，直接 UMAP 降维的时间开销"巨大"，因此对后两者要先用 PCA。
- **分析：** 流水线的主要开销在步骤 2，即每个客户端对本地全部 N 条样本各做一次前向 + 反向传播（"每条样本一次反向传播"），开销随客户端本地样本数 N 与目标模块前向/反向代价线性增长，且只在训练开始前发生一次。步骤 3 的 DCT 是每个样本一次 d 维（或 M×N 矩阵）变换，量级 O(N·d log d)。步骤 4/5/8/11 的 UMAP 与聚类约为 O(N log N)。步骤 7 与 10 的通信量为 O(K·d + d)，与轮数无关。存储上需要同时保留 N 个逐样本梯度/频域特征（N×d 浮点数）或分批处理，论文未给出该部分显存数据。步骤 2 与步骤 4—6 之后梯度即可释放，可以按样本流式计算以降低峰值内存。

## 9. 实现时容易错的地方

论文明确强调或可推断的关键点：

1. **跨客户端融合必须用原始频域维度，不能用 UMAP 后的表示**。Section V-B 明确 "it is meaningless to directly use the features after dimensionality reduction to fuse information between different clients"；式 10、式 13 也都是"用降维坐标定簇、用原始维度求质心"。
2. **必须选 lora_B 且选最后一层**。Table IX 显示 `layers.31.lora_B` 最好（Recall/F1 = 100.00），`layers.31.lora_A` 很差（Recall 36.92）；论文解释 lora_A 由高斯分布初始化、训练开始时逐样本梯度偏移过大，而 lora_B 全零初始化提供了"标准且统一的起点"（Section VI-D3）。若换成 embed_tokens / lm_head，必须先用 PCA 降维（Table IX 讨论）。
3. **轮廓系数门控是"两个条件同时满足"才回退**：s_small < 0.2 **且** s_large < 0.4，此时把全部数据视为干净（Section V-B）。写成"或"会显著改变假阳性率。
4. **两种聚类都要跑并比较轮廓系数**，单独用 HDBSCAN 或层次聚类都会掉 F1（Table X：w/o HDBSCAN 平均 F1 76.09，w/o Hier. 58.25，完整方法 84.38）。
5. **防御是一次性的**，不要按轮重复执行；Section VII-B 也只支持新加入客户端"再跑一次"。
6. **不要平均所有客户端质心**。Figure 4(b) 与 Section V-C 说明中毒比例高的客户端其质心会落进中毒区域，必须先二次聚类、只在主簇内求均值，否则全局质心会被带偏。
7. **阈值与边界依赖干净数据占主导**。当所有客户端中毒数据占多数时方法失效（Section VI-D2、Figure 6）。

论文没有说清、实现时必须自己决定的地方：

1. **梯度如何 reshape 成矩阵再做 2D-DCT**。式 5 写 g ∈ R^{M×N} 并用 C_M·g·C_N^T，但式 6 只写 DCT(g^i_k)，没有说明 lora_B 梯度（本质是 r×d 或一维 16,384 向量）如何变成一个 M×N 矩阵，也未说明 M、N 的取值。
2. **HDBSCAN 的噪声点（label = −1）如何处理**：算不算一个簇、是否直接判为中毒、是否与主簇合并，论文未说明。
3. **HDBSCAN 的超参数**（如 min_cluster_size、min_samples）论文未说明。
4. **UMAP 的超参数与随机性**（n_neighbors、min_dist、随机种子、是否确定性）论文未说明；每个客户端独立拟合 UMAP 也意味着不同客户端的结果不可复现对齐。
5. **层次聚类中哪个簇是 "primary cluster"**：论文只对 HDBSCAN 说明"取样本数最多的簇"，对层次聚类只写 "G^1_k is the primary cluster"，未说明是否取样本更多者（Section V-B）。
6. **服务器端二次聚类是否复用同样的双算法集成与轮廓系数门控**：式 12 只写 Cluster(...)，Section V-C 只写 "applies dimension reduction and secondary clustering"，未说明。
7. **本地修正阶段是否重跑轮廓系数门控与双算法集成**：Section V-D 只说 "Similarly to the process of Intra-Client frequency-based clustering"，未明确。
8. **触发"全部视为干净"回退的客户端是否仍要计算并上传质心**（若不参加全局二次聚类，主簇的客户端集合会变小），论文未说明。
9. **若全局质心在重聚类中被判为噪声点或单独成一簇**，该客户端应保留哪些数据，论文未说明。
10. **客户端样本极少（例如只有 1—2 条）、样本特征全相同、或聚类退化为单簇**时的异常处理，论文未说明。
11. **后加入客户端复用全局质心的具体流程**（用哪个版本的 c_g、是否重新触发服务器二次聚类）只有概念描述（Section VII-B），未给出算法。
12. **质心的隐私保护**：质心维度等于目标模块参数数（Table IX 中 16,384），论文只说明它不对应真实样本，未说明是否加噪或配合安全聚合。
13. **本地修正使用的并集与降维的先后**：式 14 的记号写作 Cluster(c_g ∪ {f^i_k})，而正文说"加入全局质心后再做降维和聚类"，实现顺序需要自行裁定。

## 10. 原文依据

1. **支撑步骤 1（选定观测模块）**："As suggested in [57], the parameters of the deeper layers tend to amplify the divergence of the gradients in the frequency space. Thus, we use the parameters of the lora_B in the last transformer layer as the target module."（Section V-B）
2. **支撑步骤 2（逐样本反向传播）**："To filter out poisoned samples, once the global model is received from the server, each client uses local private data to do single-sample backpropagation."（Section V-B）
3. **支撑步骤 3（2D-DCT 与展平）**："Specifically, a robust representation ˆg can be obtained for clustering to filter out poisoned samples by applying 2D discrete cosine transformation (2D-DCT) to the sample-wise gradients g ∈RM×N, as illustrated in Equation 5"（Section II-C）
4. **支撑步骤 4（UMAP 降到二维）**："In order to enhance the distinction between different sample features and make clustering algorithms perform better, we use UMAP to reduce the features to two dimensions."（Section V-B）
5. **支撑步骤 5（双聚类集成）**："we use hierarchical clustering with the number of clusters two (the primary cluster and the secondary cluster) and HDBSCAN (the number of clusters is determined by the algorithm) to perform clustering, respectively"（Section V-B）
6. **支撑步骤 5（轮廓系数门控与回退）**："the smaller one of the two silhouette scores is less than ts = 0.2 and larger one is less than tl = 0.4 (which is considered as weak plausibility), all data are considered clean data to reduce FP misjudgment."（Section V-B）
7. **支撑步骤 6 与步骤 8（用原始维度求质心）**："We choose to use the center of the original frequency domain dimension of the samples in the main cluster as the local centroid."（Section V-B）与 "Once the server receives the centroids from all clients, it will cluster the centroids again and select the main cluster, which has the most samples, to calculate the global centroid."（Section V-A）
8. **支撑步骤 11 与步骤 12（锚点重聚类与过滤）**："The global centroid will be added as a sample to the local features for re-clustering, and the cluster containing the global centroid will be considered the clean cluster."（Section V-A）

```json
{
  "key": "protegofed2026",
  "method": "ProtegoFed",
  "stages": ["server_distribute", "client_pre_train", "client_announce", "server_receive", "server_distribute", "client_pre_train"],
  "needs_round_trip": true,
  "pipeline": [
    {
      "step": "接收初始全局模型并选定观测模块",
      "operator": "select_target_module",
      "input": "服务器广播的初始全局 LoRA 模块 P0；候选模块集合（各层 lora_A/lora_B、embed_tokens、lm_head）",
      "output": "目标模块张量（最后一层 self_attn.v_proj.lora_B），参数量 d",
      "params": {"target_module": "model.layers.{last}.self_attn.v_proj.lora_B"},
      "source": "Section V-A, V-B; Section VI-D3; Table IV; Table IX"
    },
    {
      "step": "逐样本反向传播取梯度",
      "operator": "per_sample_gradient",
      "input": "本地数据集 D_k={(q^i_k,a^i_k)}_{i=1}^N 与 P0",
      "output": "N 个逐样本梯度 {g^i_k}，每个 d 维",
      "params": {"batch_size": 1},
      "source": "Section V-B; Eq. 6 上文; Eq. 1"
    },
    {
      "step": "二维 DCT 并展平",
      "operator": "dct_2d",
      "input": "逐样本梯度 g^i_k（论文写作 M×N 矩阵）",
      "output": "频域特征 f^i_k = flatten(ĝ^i_k)，d 维",
      "params": {},
      "source": "Eq. 5, Eq. 6, Eq. 7; Section II-C"
    },
    {
      "step": "UMAP 降维到二维",
      "operator": "umap_2d",
      "input": "{f^i_k}_{i=1}^N，N×d",
      "output": "{ef^i_k}_{i=1}^N，N×2",
      "params": {"n_components": 2},
      "source": "Eq. 8; Section V-B; Section VI-D6; Figure 12"
    },
    {
      "step": "本地双聚类集成与轮廓系数门控",
      "operator": "dual_clustering_silhouette_select",
      "input": "{ef^i_k}_{i=1}^N，N×2",
      "output": "簇标签 G^1_k, (G^2_k, ...)，或全部视为干净的退化结论",
      "params": {"hierarchical_n_clusters": 2, "hdbscan_n_clusters": "determined by algorithm", "t_s": 0.2, "t_l": 0.4},
      "source": "Section V-B; Eq. 9; Section VI-D4; Table X"
    },
    {
      "step": "在原始频域维度计算主簇质心",
      "operator": "main_cluster_centroid",
      "input": "主簇样本的原始频域特征 {f^i_k} 与降维坐标 {ef^i_k}",
      "output": "本地质心 c_k，d 维",
      "params": {},
      "source": "Eq. 10; Section V-B"
    },
    {
      "step": "上传本地质心",
      "operator": "send_local_centroid",
      "input": "c_k，d 维",
      "output": "服务器端 {c_1,...,c_K}，K×d",
      "params": {},
      "source": "Section V-A, V-B; Figure 5"
    },
    {
      "step": "服务器对质心做二次聚类",
      "operator": "secondary_cluster_centroids",
      "input": "{c_1,...,c_K}，K×d",
      "output": "降维坐标 {ec_1,...,ec_K} 与主簇 G^1_II",
      "params": {"n_components": 2},
      "source": "Eq. 11, Eq. 12; Section V-C"
    },
    {
      "step": "计算全局质心",
      "operator": "global_centroid",
      "input": "主簇客户端的原始维度质心 {c_j : ec_j ∈ G^1_II}",
      "output": "全局质心 c_g，d 维",
      "params": {},
      "source": "Eq. 13; Section V-C"
    },
    {
      "step": "广播全局质心",
      "operator": "broadcast_global_centroid",
      "input": "c_g，d 维",
      "output": "所有客户端持有的 c_g",
      "params": {},
      "source": "Section V-A, V-C"
    },
    {
      "step": "以全局质心为锚点做本地重聚类",
      "operator": "local_recluster_with_anchor",
      "input": "c_g 与本地原始频域特征 {f^i_k}_{i=1}^N",
      "output": "含 c_g 的干净簇 Gr_k",
      "params": {},
      "source": "Eq. 14; Section V-A, V-D"
    },
    {
      "step": "过滤非干净簇样本",
      "operator": "filter_to_clean_cluster",
      "input": "本地数据集 D_k 与簇标签 Gr_k",
      "output": "净化数据集 D^clean_k",
      "params": {},
      "source": "Eq. 15; Section V-D"
    },
    {
      "step": "在净化数据上执行标准 FIT / FedAvg 训练",
      "operator": "fedavg_train",
      "input": "D^clean_k 与全局 LoRA 模块 P^i",
      "output": "更新后的本地模块 P^i_k 与聚合后的全局模块 P^{i+1}",
      "params": {"lora_rank": 4, "local_epochs": 1, "communication_rounds": 100, "learning_rate": 2e-05},
      "source": "Eq. 1, Eq. 2; Section VI-A7"
    }
  ],
  "sampling": [
    {"what": "layers", "how": "只取最后一个 transformer 层的梯度，其余层不参与", "size": "1 层（Table IX 记为 layers.31，共 32 层）"},
    {"what": "coordinates", "how": "只观测 self_attn.v_proj.lora_B 的参数坐标，不观测 lora_A、embed_tokens、lm_head", "size": "16,384 个参数（备选 embed_tokens/lm_head 为 131,072,000，未采用）"},
    {"what": "coordinates", "how": "UMAP 把 d 维频域特征降到低维再聚类", "size": "2 维"},
    {"what": "samples", "how": "本地不做抽样，对每条训练样本各做一次反向传播；数据集层面每数据集随机抽 5,000 训练 / 400 验证 / 2,000 测试（WebQA 除外）", "size": "N = 客户端本地样本数（IID 主实验 25 客户端均分）"},
    {"what": "rounds", "how": "只在训练开始前执行一次，不随通信轮次重复", "size": "1 次"},
    {"what": "probes", "how": "不使用参考数据或探针样本，用本地样本梯度合成的虚拟质心代表客户端", "size": "每客户端 1 个质心"},
    {"what": "clients", "how": "服务器二次聚类只保留主簇内客户端的质心用于求全局质心", "size": "论文未说明主簇规模"}
  ],
  "resources": [
    "无需额外干净参考数据或根数据集（Section III-B2：The server does not require an auxiliary clean dataset or model training）",
    "每个客户端持有本地指令微调数据集 D_k 与服务器广播的初始全局 LoRA 模块 P0",
    "客户端侧需实现 UMAP、HDBSCAN、层次聚类与轮廓系数 (Section V-B)",
    "服务器侧需实现 UMAP 与聚类，无需训练额外模型 (Section V-C)",
    "一次性通信：K 个 d 维质心上传加 1 个 d 维全局质心广播（d=16,384，K=25）"
  ],
  "actions": ["filter_samples", "exclude_client", "report_only"],
  "dominant_cost": "每个客户端对本地的每条样本各做一次前向与反向传播（N 次逐样本反向传播），随后 UMAP/HDBSCAN 约 O(N log N)；论文报告一次性开销为 Intra-Client Clustering 12.43 s、Global Clustering 0.07 s、Local Revising 0.39 s，约占总训练时间 1%（Section VII-A、Figure 13；Section VI-D7）",
  "underspecified": [
    "式 5 的 g ∈ R^{M×N} 中 M、N 的取值，以及 lora_B 梯度如何 reshape 后再做 2D-DCT，论文未说明",
    "HDBSCAN 的噪声点（label = -1）如何处理，论文未说明",
    "HDBSCAN 的超参数（min_cluster_size、min_samples 等）论文未说明",
    "UMAP 的超参数与随机种子论文未说明，且各客户端独立拟合 UMAP",
    "层次聚类结果中哪个簇是 primary cluster（是否取样本最多者）论文未说明，只对 HDBSCAN 说明了取最大簇",
    "服务器端二次聚类是否复用层次聚类+HDBSCAN+轮廓系数的集成与 t_s/t_l 门控，论文未说明",
    "本地修正阶段是否重跑轮廓系数门控，论文只写 Similarly to the process of Intra-Client frequency-based clustering",
    "触发全部视为干净回退的客户端是否仍计算并上传质心，论文未说明",
    "全局质心在重聚类中被判为噪声点或单独成簇时的处理，论文未说明",
    "客户端样本过少、聚类退化为单簇或全为噪声时的异常处理，论文未说明",
    "后加入客户端复用全局质心的具体流程只有概念描述（Section VII-B），未给出算法",
    "质心维度等于目标模块参数量，是否加噪或配合安全聚合，论文未说明",
    "式 14 的并集与降维先后顺序在记号与正文之间不一致，实现顺序需自行裁定",
    "Recall 的文字定义与表格数值方向相反，且正文 CBA/WebQA 的 F1（79.12%）与 Table III（82.71%）不一致"
  ],
  "quotes": [
    {"supports": "步骤 1 选定观测模块", "text": "As suggested in [57], the parameters of the deeper layers tend to amplify the divergence of the gradients in the frequency space. Thus, we use the parameters of the lora_B in the last transformer layer as the target module."},
    {"supports": "步骤 2 逐样本反向传播", "text": "To filter out poisoned samples, once the global model is received from the server, each client uses local private data to do single-sample backpropagation."},
    {"supports": "步骤 3 二维 DCT 与频域特征", "text": "Specifically, a robust representation ˆg can be obtained for clustering to filter out poisoned samples by applying 2D discrete cosine transformation (2D-DCT) to the sample-wise gradients g ∈RM×N, as illustrated in Equation 5"},
    {"supports": "步骤 4 UMAP 降到二维", "text": "In order to enhance the distinction between different sample features and make clustering algorithms perform better, we use UMAP to reduce the features to two dimensions."},
    {"supports": "步骤 5 双聚类集成", "text": "we use hierarchical clustering with the number of clusters two (the primary cluster and the secondary cluster) and HDBSCAN (the number of clusters is determined by the algorithm) to perform clustering, respectively"},
    {"supports": "步骤 5 轮廓系数门控与全部视为干净的回退", "text": "the smaller one of the two silhouette scores is less than ts = 0.2 and larger one is less than tl = 0.4 (which is considered as weak plausibility), all data are considered clean data to reduce FP misjudgment."},
    {"supports": "步骤 6 与步骤 9 用原始频域维度计算质心", "text": "We choose to use the center of the original frequency domain dimension of the samples in the main cluster as the local centroid."},
    {"supports": "步骤 8 服务器二次聚类取主簇", "text": "Once the server receives the centroids from all clients, it will cluster the centroids again and select the main cluster, which has the most samples, to calculate the global centroid."}
  ]
}
```
