# safefedllm2026：Safe-FedLLM

说明：论文在 5.1 节把 Multi-Krum、Trimmed Mean、FoolsGold、Residual、DnC、FLAME、LASA 等仅作为对比基线（Baseline）评测，本文只拆解论文自己提出的 Safe-FedLLM，不拆这些基线方法。Safe-FedLLM 由三部分组成：LoRA-Probe 检测器（4.1 节）、三个层级的安全因子模块（4.2 节，Step-Level / Client-Level / Shadow-Level）与安全聚合策略（4.3 节）。

## 1. 方法一句话

Safe-FedLLM 的输入是联邦大语言模型（federated large language model, FedLLM）训练过程中客户端本地训练产生的 LoRA（low-rank adaptation）参数更新，具体是第一个 transformer 层所有 LoRA 模块的 B 矩阵相对初始化的增量 ΔB₀,ₜ，以及每轮上传的 LoRA 更新 ΔWᵢ⁽ʳ⁾；它的输出有两层：一是对每一步/每个客户端更新的恶意性判定（s ≥ τ_cls 即判为恶意），二是由这些判定折算出的客户端安全因子 wᵢ⁽ʳ⁾ ∈ [0, 1]（若整轮平均因子过低则输出"本轮不聚合"）；服务器最终用该因子对 ΔWᵢ⁽ʳ⁾ 做安全加权聚合（Eq 12），或直接跳过本轮聚合（Eq 11）。方法不修改客户端原始数据，也不改变客户端的本地训练损失，只改变服务器侧的聚合权重。

## 2. 运行位置

- 训练之外（outside_training）：LoRA-Probe 在联邦训练开始前离线训练，训练完成后固定，不再更新（4.1 节 Offline Training；附录 A 明确"After training, the classifier remains fixed"）。
- 服务器下发（server_distribute）：第 r 轮开始时服务器把当前全局参数 W⁽ʳ⁾ 广播给被采样的客户端集合 Sᵣ，这一步与标准 FedAvg 相同（4.3 节 Eq 12 之前的一句话）。
- 客户端训练前（client_pre_train）：所有客户端把 LoRA 初始参数固定为一致的值，以保证各次运行的 ΔLoRA 统计一致（附录 B）；Shadow-Level 的客户端在此阶段额外建立一条与主训练分支独立的影子 LoRA 分支，并全程固定其学习率（4.2 节 Shadow-Level；附录 B）。探针训练数据也要求与客户端使用同一套本地训练配置（附录 A）。
- 客户端每个训练步（client_step）：每个本地步 t ∈ {1, …, T} 计算 ΔBⁱ₀,ₜ 并经归一化送入探针得到 sⁱₜ（4.1 节 Malicious Feature Detection，Eq 4）；Shadow-Level 的影子分支同样在每个本地步产生一次判定，用于统计恶意比例 ρᵢ⁽ʳ⁾（4.2 节 Shadow-Level）。
- 客户端训练结束后 / 服务器收到更新（client_post_train / server_receive）：客户端上传本轮 LoRA 更新 ΔWᵢ⁽ʳ⁾（4.3 节 Eq 12）；Client-Level 使用"本轮最终本地 LoRA 更新"对应的恶意概率 sᵢ⁽ʳ⁾（4.2 节 Client-Level）。
- 服务器聚合（server_aggregate）：先按 Eq 11 判断是否跳轮，否则按 Eq 12 做安全加权聚合（4.3 节）。
- 聚合之后 / 跨轮（server_post_aggregate）：安全因子按 Eq 10 在 r > R_f 之后冻结为 wᵢ⁽ᴿᶠ⁾，只作用于 Step-Level 与 Client-Level；Shadow-Level 不冻结（4.2 节 Early-Stage Defense Stabilization）。
- 是否需要额外往返：论文只明确写了每轮客户端上传一次 ΔWᵢ⁽ʳ⁾ 的标准往返（Eq 12）。但 Step-Level 需要每轮 T 个本地步的逐步判定、Shadow-Level 需要影子分支的逐步判定，论文没有说明探针是在客户端本地执行还是服务器执行，也没有说明这些逐步信号/影子分支更新如何到达服务器。如果按"服务器侧探针"实现，则需要客户端随更新额外交付 T 份 ΔLoRA 或影子分支的 ΔLoRA，这超出 Eq 12 描述的单次上传；论文对此完全未说明。因此 JSON 中把 needs_round_trip 标为 true，含义是"需要 Eq 12 之外的额外通信，但论文未定义其形式"。

## 3. 算子流水线

按执行顺序如下。所有形状中 T 为每轮本地更新步数（论文取 10），r 为 LoRA 秩（论文取 8）。

**步骤 1（训练之外）离线训练 LoRA-Probe**
- 步骤名：离线探针训练。
- 输入：带标签的良性/恶意 ∆LoRA 样本，由"模拟的客户端本地训练过程"产生，其数据预处理、优化器、学习率、批大小、本地训练步数严格对齐真实联邦训练配置（附录 A）。样本只取前 10 个通信轮、50% 恶意客户端设置下产生的 ∆LoRA（附录 A）。
- 计算：对每个样本的每个本地步 t，取第一个 transformer 层所有 LoRA 模块的 B 矩阵，计算 ΔB⁽¹⁾₀,ₜ = Bₜ − B₀（Eq 1）；把每个矩阵展平并按固定顺序拼接成 x = concat(ΔB⁽¹⁾₀,ₜ)（Eq 2）；做 L2 归一化得到 x̃ = x/‖x‖₂（附录 A）；在该特征上拟合逻辑回归 s = σ(aᵀx̃ + c)（Eq 3）。
- 输出：固定不变的线性探针参数 (a, c)。
- 出处：4.1 节 Offline Training，Eq 1–3；附录 A。

**步骤 2（客户端训练前）固定 LoRA 初始化并建立影子分支**
- 输入：全局 LoRA 初始参数与初始化随机种子。
- 计算：所有客户端在联邦训练开始时使用同一份固定的 LoRA 初始参数（附录 B），且该初始化必须与训练 LoRA-Probe 时使用的随机种子一致（Limitations 明确指出这是本方法的假设）；Shadow-Level 的客户端再复制一条独立于主训练分支的影子 LoRA 分支，全程固定其学习率（附录 B），该分支不参与主模型训练，也不参与参数聚合（4.2 节）。
- 输出：供 Eq 1 使用的 B₀，以及影子分支参数。
- 出处：附录 B Training Protocol and Stabilization Strategies；4.2 节 Shadow-Level；Limitations。

**步骤 3（客户端每步）计算第一层 B 矩阵增量**
- 输入：当前第一个 transformer 层所有 LoRA 模块的 B 矩阵 Bₜ（每个模块形状为 d_out × r）与 B₀。
- 计算：ΔB₀,ₜ = Bₜ − B₀（Eq 1）。注意论文只用 B 矩阵、不用 A 矩阵，且只取第一个 transformer 层（Eq 2）。
- 输出：一组矩阵差 {ΔB⁽ᵐ⁾₀,ₜ}。
- 出处：4.1 节 Eq 1–2；3.3 节与图 2 说明第一层 LoRA B 矩阵更新分布具有可分性。

**步骤 4（客户端每步）拼接与 L2 归一化**
- 输入：{ΔB⁽ᵐ⁾₀,ₜ}。
- 计算：把每个矩阵展平后按固定顺序拼成向量 x，再算 x̃ = x/‖x‖₂（附录 A），使探针只关注更新方向而非绝对幅度。
- 输出：归一化特征 x̃ ∈ ℝ^{d_probe}；d_probe 的数值论文未说明（取决于第一层注入了哪些 LoRA 模块，论文未说明）。
- 出处：Eq 2；附录 A。

**步骤 5（客户端每步）探针打分**
- 输入：x̃ᵢᵗ。
- 计算：sⁱₜ = σ(aᵀx̃ᵢᵗ + c)（Eq 4）。
- 输出：恶意性概率 sⁱₜ ∈ [0, 1]。
- 出处：4.1 节 Eq 4。

**步骤 6（客户端每步）阈值判定**
- 输入：sⁱₜ。
- 计算：若 sⁱₜ ≥ τ_cls 判为恶意；影子分支的每一步用同样规则判定（τ_cls 在 5.1 节取 0.8）。
- 输出：每步的二值判定。
- 出处：4.1 节 "the update is classified as malicious if sᵗᵢ ≥ τcls"；4.2 节 Shadow-Level；5.1 节 τ_cls = 0.8。

**步骤 7（每轮结束）Step-Level 贝叶斯计数**
- 输入：客户端 i 本轮 T 个步级判定，以及上一轮保留的 αᵢ、βᵢ。
- 计算：记本轮良性步数为 bᵢ⁽ʳ⁾、恶意步数为 mᵢ⁽ʳ⁾；按 αᵢ ← γαᵢ + bᵢ⁽ʳ⁾、βᵢ ← γβᵢ + mᵢ⁽ʳ⁾ 更新（Eq 5），γ 为时间衰减因子（5.1 节取 0.95）。
- 输出：跨轮累积的 αᵢ、βᵢ。
- 出处：4.2 节 Step-Level，Eq 5；5.1 节 γ = 0.95。
- 注：αᵢ、βᵢ 的初值论文未说明。

**步骤 8（每轮结束）Step-Level 安全因子**
- 输入：αᵢ、βᵢ。
- 计算：wᵢ,step⁽ʳ⁾ = αᵢ / (αᵢ + βᵢ)（Eq 6）。
- 输出：一个 [0, 1] 区间的安全因子。
- 出处：4.2 节 Eq 6。

**步骤 9（每轮结束）Client-Level 瞬时安全因子**
- 输入：客户端 i 本轮"最终本地 LoRA 更新"的恶意概率 sᵢ⁽ʳ⁾ ∈ [0, 1]（4.2 节原文为 the final local LoRA update，未显式写成 t = T）。
- 计算：先做两段 sigmoid 校准 g(s)（Eq 13，k = 10）：当 s ∈ [0, 0.8] 时 g(s) = ½·σ(k(s − 0.4))；当 s ∈ (0.8, 1] 时 g(s) = ½·[1 + σ(k(s − 0.9))]；再取 ŵᵢ,client⁽ʳ⁾ = 1 − g(sᵢ⁽ʳ⁾)（Eq 7）。
- 输出：本轮瞬时安全因子 ŵᵢ,client⁽ʳ⁾。
- 出处：4.2 节 Eq 7；附录 C Eq 13。

**步骤 10（每轮结束）Client-Level 历史平均**
- 输入：客户端 i 历次参与轮（Rᵢ⁽ʳ⁾ = {k ≤ r | i ∈ Sₖ}）上的瞬时因子。
- 计算：wᵢ,client⁽ʳ⁾ = (1/|Rᵢ⁽ʳ⁾|)·Σ_{k∈Rᵢ⁽ʳ⁾} ŵᵢ,client⁽ᵏ⁾（Eq 8），只在客户端实际被采样的轮上求平均。
- 输出：跨轮平滑后的安全因子。
- 出处：4.2 节 Eq 8。

**步骤 11（每轮）Shadow-Level 恶意比例**
- 输入：影子分支 T 个本地步的判定结果。
- 计算：统计恶意比例 ρᵢ⁽ʳ⁾；论文只写"the resulting malicious ratio"，未给出分母定义（最自然读法是恶意步数除以本轮步数 T）。
- 输出：ρᵢ⁽ʳ⁾ ∈ [0, 1]。
- 出处：4.2 节 Shadow-Level。

**步骤 12（每轮）Shadow-Level 指数抑制**
- 输入：ρᵢ⁽ʳ⁾。
- 计算：wᵢ,shadow⁽ʳ⁾ = (1 − ρᵢ⁽ʳ⁾)^η（Eq 9），η > 0 控制抑制强度，5.1 节取 η = 7。
- 输出：影子分支安全因子。
- 出处：4.2 节 Eq 9；5.1 节 η = 7。

**步骤 13（跨轮）早停冻结**
- 输入：各客户端在第 R_f 轮时的安全因子。
- 计算：只对依赖 LoRA-Probe 输出的 Step-Level 与 Client-Level 生效，wᵢ⁽ʳ⁾ = wᵢ⁽ᴿᶠ⁾，∀r > R_f（Eq 10）；R_f 在 5.1 节与附录 B 取 20。Shadow-Level 不需要冻结，因为其安全信号来自与全局模型解耦的固定影子分支。
- 输出：r > 20 之后不再变化的安全因子。
- 出处：4.2 节 Eq 10；5.1 节；附录 B。

**步骤 14（服务器聚合）安全门控跳轮**
- 输入：本轮被采样集合 Sᵣ 上的安全因子 {wᵢ⁽ʳ⁾}。
- 计算：w̄⁽ʳ⁾ = (1/|Sᵣ|)·Σ_{i∈Sᵣ} wᵢ⁽ʳ⁾；若 w̄⁽ʳ⁾ < τ_skip，则跳过本轮聚合，W⁽ʳ⁺¹⁾ = W⁽ʳ⁾（Eq 11）；否则进入步骤 15。τ_skip 在 5.1 节取 0.2。
- 输出：要么保持旧全局参数，要么进入加权聚合。
- 出处：4.3 节 Security-Gated Round Skipping，Eq 11；5.1 节 τ_skip = 0.2。

**步骤 15（服务器聚合）安全加权聚合**
- 输入：各客户端上传的 LoRA 更新 ΔWᵢ⁽ʳ⁾、客户端本轮本地样本数 nᵢ、安全因子 wᵢ⁽ʳ⁾。
- 计算：W⁽ʳ⁺¹⁾ = W⁽ʳ⁾ + Σ_{i∈Sᵣ} [ nᵢwᵢ⁽ʳ⁾ / Σ_{j∈Sᵣ} nⱼwⱼ⁽ʳ⁾ ]·ΔWᵢ⁽ʳ⁾（Eq 12）。
- 输出：新一轮全局参数 W⁽ʳ⁺¹⁾。
- 出处：4.3 节 Security-Weighted Aggregation，Eq 12。

**层级合成说明（重要）**：4.2 节开头说"设计 ℓ ∈ {step, client, shadow} 三个层级的模块，并把它们的输出 wᵢ,ℓ⁽ʳ⁾ 用作聚合安全因子 wᵢ⁽ʳ⁾"，但论文没有给出把三个因子合成为一个的任何公式；实验（表 2、表 3、表 6、表 9）是把 Step-Level、Client-Level、Shadow-Level 当作三个独立变体分别评测的。因此本流水线把三者并列，实现时需要二选一或自行定义合成规则，论文未说明。

## 4. 采样与规模控制

- 客户端抽样：共 10 个客户端，每轮随机采样 3 个，训练 100 个通信轮（5.1 节 Implementation Details）。
- 本地样本规模：每个客户端持有 500 条样本（5.1 节）；每个被选中客户端每轮执行 10 个本地更新步（T = 10，5.1 节）。
- 层与坐标降维：探针只使用第一个 transformer 层所有 LoRA 模块的 B 矩阵差（Eq 2），不使用 A 矩阵、不使用其余层；随后做 L2 归一化，把特征投影到单位球，丢弃幅度信息、只保留方向（附录 A）。论文未使用 PCA/降维类预处理于防御本体；图 2 中的 LDA+PCA 只是可视化手段（3.2 节、图 2），不是流水线的一部分。
- 轮次控制：探针训练只使用前 10 个通信轮、50% 恶意客户端设置下产生的 ∆LoRA，理由是 LoRA 增量在早期轮次已达到稳定的分布覆盖（附录 A）；Step-Level 与 Client-Level 的安全因子只在前 R_f = 20 轮更新，之后冻结（Eq 10、附录 B）。
- 探针数量：每个客户端每个本地步调用一次探针（T = 10 次/轮），影子分支同样每步一次（4.1 节、4.2 节）。
- 数据排除：为避免数据泄漏，探针训练样本排除与模型训练数据重叠的部分，包括 WildChat/LMSYS-Chat 的前 4,000 条与 BeaverTails/MaliciousGen 的前 2,500 条（附录 A）。
- 论文未说明的抽样量：探针训练集的具体样本条数、良性/恶意类别配比、是否做批采样，论文均未说明。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| τ_cls | 探针恶意性判定阈值（s ≥ τ_cls 判为恶意） | 0.8 | 5.1 节；4.1 节 |
| τ_skip | 轮级跳轮阈值（平均安全因子低于它则跳过聚合） | 0.2 | 5.1 节；4.3 节 Eq 11 |
| γ | Step-Level 贝叶斯统计的时间衰减因子，γ ∈ (0, 1) | 0.95 | 5.1 节；4.2 节 Eq 5 |
| η | Shadow-Level 指数抑制强度，η > 0 | 7 | 5.1 节；4.2 节 Eq 9 |
| R_f | 早停冻结轮数，r > R_f 后安全因子固定 | 20 | 5.1 节；附录 B；Eq 10 |
| k | 两段 sigmoid 校准的锐度参数 | 10 | 附录 C Eq 13 |
| 校准分段点 | g(s) 的两段分界与中心，s 的区间为 [0, 0.8] 与 (0.8, 1] | 0.4、0.8、0.9 | 附录 C Eq 13 |
| T | 每轮每客户端的本地更新步数（也等于每轮探针调用次数） | 10 | 5.1 节；4.1 节 |
| 客户端数 / 每轮采样数 / 通信轮数 | 联邦训练的规模设置 | 10 / 3 / 100 | 5.1 节 |
| 每客户端样本数 | 本地私有数据量 | 500 | 5.1 节 |
| LoRA 秩与缩放 | LoRA 的 r 与 α | r = 8，α = 16 | 5.1 节 |
| 优化器与学习率 | 本地训练优化器与学习率 | AdamW_bnb_8bit，5 × 10⁻⁵ | 5.1 节 |
| 最大序列长度 | 本地训练截断长度 | 256 | 5.1 节 |
| 基座量化 | 基座模型 8-bit 量化 | 是 | 5.1 节 |
| 探针训练数据轮数 / 恶意比例 | 构造探针训练样本时的设置 | 前 10 轮、50% 恶意客户端 | 附录 A |
| αᵢ、βᵢ 初值 | Eq 5 中贝叶斯参数的初始值 | 论文未说明 | — |
| 影子分支学习率数值 | 只说明"固定"，未给出具体数值 | 论文未说明 | 附录 B |

## 6. 判定与动作

- 步级判定：sⁱₜ ≥ τ_cls（0.8）即判为恶意（4.1 节），该二值结果被三个层级分别消费。
- Step-Level 动作：把本轮 T 个步级判定聚合为 bᵢ⁽ʳ⁾ 与 mᵢ⁽ʳ⁾，按 Eq 5 做带衰减的累积（αᵢ ← γαᵢ + bᵢ⁽ʳ⁾，βᵢ ← γβᵢ + mᵢ⁽ʳ⁾），再按 Eq 6 取 Beta 后验均值 αᵢ/(αᵢ + βᵢ) 作为权重；这是一个软性降权，不硬剔除客户端，且跨轮累积（含 γ 衰减与 R_f 后冻结）。
- Client-Level 动作：用本轮最终更新的概率 sᵢ⁽ʳ⁾ 经两段 sigmoid 校准得到 g(s)（Eq 13），令瞬时因子 ŵ = 1 − g(s)（Eq 7），再对该客户端历次参与轮求平均（Eq 8）。校准设计使 g(s) ∈ [0, 1]：s ≤ 0.8 时段只给温和惩罚（g ∈ (0, 0.5]），s ∈ (0.8, 1] 时给更强惩罚（g ∈ (0.5, 1)），从而避免对"中度可疑"的更新过度降权（附录 C）。同样跨轮累积（历史平均），并在 R_f 后冻结。
- Shadow-Level 动作：用影子分支的逐步判定统计恶意比例 ρᵢ⁽ʳ⁾，按 w = (1 − ρ)ᵉ 做指数抑制（Eq 9）；因子只反映本轮影子分支的表现，不做跨轮平滑，但因为影子分支与全局模型解耦、学习率固定，所以不需要冻结（4.2 节）。
- 轮级动作（聚合门控）：计算平均安全因子 w̄⁽ʳ⁾，若 w̄⁽ʳ⁾ < τ_skip = 0.2 则整轮不聚合，直接保留上一轮全局参数 W⁽ʳ⁺¹⁾ = W⁽ʳ⁾（Eq 11）；这是本方法里唯一"完全不采纳本轮更新"的动作，触发原因是归一化后近零权重会导致加权不稳定、恶意更新仍可能占主导（4.3 节）。
- 聚合动作：按 Eq 12 做样本数 nᵢ 与安全因子 wᵢ⁽ʳ⁾ 双重加权的 FedAvg 式更新；权重被归一化，安全因子越低贡献越小。实验里每个客户端都是 500 条样本（5.1 节），因此 nᵢ 相等时 Eq 12 退化为仅按 wᵢ 归一化加权（分析）。
- 方法没有裁剪（clip）、没有加噪（add_noise）、没有硬剔除（exclude_client）、也不修改客户端样本，全部动作都是聚合权重层面的软降权加一种整轮跳过。

## 7. 需要的外部资源

- 带标签的 ∆LoRA 探针训练样本：论文用"模拟客户端本地训练"生成（附录 A），必须复用 FedLLM 的本地训练配置；样本条数论文未说明。
- 与客户端侧训练一致的 LoRA 初始化随机种子：Limitations 明确把"客户端训练用的 LoRA 初始化随机种子与训练 LoRA-Probe 时一致"作为框架假设。
- 冻结的线性探针参数 (a, c)（式 3），训练后不再更新（附录 A）。
- 客户端侧额外资源：Shadow-Level 需要一条影子 LoRA 分支，使可训练参数从 3.41M 翻倍到 6.82M，显存从 20.62GB 升到 41.24GB（表 4）。
- 基座模型：Llama3.1-8B 与 Qwen2.5-7B，均 8-bit 量化（3.1 节、5.1 节）。
- 数据资源：良性 LMSYS-Chat、WildChat，恶意 BeaverTails、自动生成的 MaliciousGen，以及 FedLLM-Attack 的恶意客户端模拟（3.1 节）。
- 仅用于评测、不属于防御本体的资源：AdvBench 安全基准、MT-Bench/MT-1 效用评测、GPT-5-mini 打分、奖励模型 RM、MD-Judge（3.1 节、5.1 节）。

## 8. 计算与存储开销

- 论文报告值（表 4，Llama3.1-8B，30% 恶意客户端比例）：FedAvg 训练时间 2h35m、可训练 LoRA 参数 3.41M、GPU 显存 20.62GB；Step-Level 与 Client-Level 均为 2h40m / 3.41M / 20.62GB；Shadow-Level 为 2h40m / 6.82M / 41.24GB。论文称相对 FedAvg 总开销只增加 3.2%（5.2 节 Efficiency）。
- 论文对探针成本的论断：它只作用于参数更新、不访问原始数据，并且"其线性形式带来可忽略的计算与时间开销"（4.1 节）；影子分支可以与主分支并行计算，因此墙上时钟开销可忽略（5.2 节）。
- 主要开销来源（分析）：整条流水线的主要成本仍是客户端本地 LoRA 微调本身；防御侧新增的是每客户端每本地步一次"第一层 B 矩阵差提取 + 展平拼接 + L2 归一化 + 一次线性打分"，成本随特征维度 d_probe 和本地步数 T 线性增长，T = 10，且每个本地步只需一次前向式的矩阵访问，不需要额外反向传播。Shadow-Level 的额外成本来自影子分支的完整训练（参数翻倍、显存近似翻倍）。
- 服务器侧开销（分析）：每轮只需 O(|Sᵣ|) 次平均、阈值比较与加权求和，另有按客户端维护的少量标量状态；论文未单独报告这部分耗时。
- 存储开销（分析）：探针参数 (a, c)（维度 d_probe + 1）；Step-Level 需要按客户端保存 αᵢ、βᵢ；Client-Level 需要按客户端保存历次参与轮的瞬时因子以做 Eq 8 平均，规模 O(客户端数 × 参与轮数)，且在 R_f = 20 轮冻结后可只保留冻结值；Shadow-Level 需要客户端侧保存整套影子分支参数。
- 论文未报告的开销：探针的训练时间/显存、探针训练数据的生成成本、通信开销（包括是否需要额外交付逐步 ΔLoRA 或影子分支更新）。

## 9. 实现时容易错的地方

论文明确强调的实现细节：

- 特征只取第一个 transformer 层所有 LoRA 模块的 B 矩阵，且拼接顺序必须固定（Eq 2），否则探针输入分布与训练时不一致。
- 必须先做 L2 归一化再送入探针，目的是消除客户端间与训练步间的尺度差异，让探针只关注方向（附录 A）。
- 所有客户端的 LoRA 初始参数在联邦训练开始时被固定，且必须与训练探针时使用的初始化随机种子一致；论文在 Limitations 中承认这一要求在实际联邦环境中难以保证。
- 探针在训练完成后固定，不参与后续联邦训练更新（附录 A）。
- 影子分支与主训练分支完全独立，不参与模型训练与参数聚合，且学习率全程固定，以减小影子 LoRA 更新随轮次的漂移（4.2 节、附录 B）。
- Step-Level 与 Client-Level 必须在 r > R_f = 20 后冻结安全因子，因为随着学习率衰减与全局模型演化，LoRA 更新分布发生系统性漂移、探针预测可靠性下降；Shadow-Level 因为信号来自固定影子分支则不需要冻结（4.2 节、5.2 节，图 4 显示 Step/Client-Level 的精度随轮次持续下降）。
- 跳轮机制存在的理由是 Eq 12 会对安全因子做归一化，当采样集合中恶意客户端占多数、所有 wᵢ⁽ʳ⁾ 都接近 0 时归一化会放大噪声、让恶意更新仍占主导（4.3 节）。
- 两段 sigmoid 校准要保证 g(s) ∈ [0, 1]，避免对中度可疑更新过度降权（附录 C）。
- 探针训练样本必须排除与模型训练数据重叠的部分（前 4,000 条 WildChat/LMSYS-Chat、前 2,500 条 BeaverTails/MaliciousGen），以防数据泄漏（附录 A）。

论文没有说清、实现时必须自行决定的地方：

- 探针运行位置：论文没有说明 sⁱₜ 是在客户端本地计算并上报，还是在服务器收到更新后计算；由此也无法确定逐步判定与影子分支的 ρ 如何传给服务器、是否需要额外通信往返。
- 三个层级如何合成一个 wᵢ⁽ʳ⁾：4.2 节的表述像是三者之一，但没有任何融合公式；若三个模块想同时启用，需要自行定义（例如相乘或加权）。
- Eq 5 中 αᵢ、βᵢ 的初值：论文完全没有给出，而初值直接决定第 1 轮的 wᵢ,step，属于必须自行设定的关键参数。
- B₀ 的含义：Eq 1 写 ΔB₀,ₜ = Bₜ − B₀，但未说明 B₀ 是"本轮的全局起点 B"还是"联邦训练最开始的 B"；附录 B 只说了固定初始参数。
- 影子分支细节：影子分支是否每轮从全局参数重置、其参数是否随轮次延续、固定学习率的具体数值，均未说明；ρᵢ⁽ʳ⁾ 的分母也未定义。
- Client-Level 用的 sᵢ⁽ʳ⁾ 是否就是主分支 t = T 时刻的探针输出：论文只写"final local LoRA update"，且也未说明该分数与步骤 5 的逐 step 分数关系。
- LoRA 注入模块清单：论文只说"第一个 transformer 层所有 LoRA 模块"，没有给出具体模块列表与特征维度 d_probe。
- 探针训练细节：样本条数、正负样本配比、正则化、收敛判据、τ_cls = 0.8 与 k = 10 的选取过程都没有说明；τ_cls 的选取过程也未给出。
- 跳轮的边界行为：跳轮后客户端采样是否重做、轮计数是否递增、跳轮是否计入 R_f 与 Rᵢ⁽ʳ⁾、是否影响 Eq 8 的参与历史，论文均未说明。
- 数值边界：x 的范数为 0（ΔB 全零）时 L2 归一化如何处理、s 恰好等于 0.8 或 0.2 时归入哪一段、聚类/客户端数过少（例如 Sᵣ 均值计算）等边界情形，论文未给出处理规则。
- 客户端不诚实上报安全因子的风险：如果因子在客户端侧计算并上报，恶意客户端可以伪造，论文没有讨论这一威胁模型。

## 10. 原文依据

1. 支撑步骤 1（离线探针训练与 ΔB 定义）："Before federated training, we train a probe offline on labeled benign and malicious samples by computing the delta of LoRA B-matrices at local step t and initialization:"
2. 支撑步骤 3–4（只用第一个 transformer 层的 B 矩阵并拼接成特征）："We extract the LoRA B-matrix differences from all LoRA modules in the first transformer layer and form a feature vector:"
3. 支撑步骤 4（L2 归一化）："To eliminate scale variation across clients and training steps, we apply L2 normalization to x to obtain the normalized feature ˜x = x/∥x∥2."
4. 支撑步骤 5–6（在线逐步检测）："During FL, each client i performs T local LoRA update steps per round, where t ∈ {1, . . . , T} denotes the local step index."
5. 支撑步骤 7–8（Step-Level 贝叶斯统计与 γ）："This mechanism performs maliciousness detection at each local training step and computes a client’s security factor via Bayesian statistics with a time-decay factor γ ∈ (0, 1) to gradually downweight outdated evidence."
6. 支撑步骤 10（Client-Level 历史平均）："To reduce single-round noise, we compute a historical average over the rounds in which client i participates:"
7. 支撑步骤 11–12（Shadow-Level 影子分支与其用途）："This mechanism introduces a client-maintained shadow LoRA branch that is independent of the main training branch. It is used only to generate LoRA updates for probe-based detection and does not participate in model training or parameter aggregation."
8. 支撑步骤 13（早停冻结）："To mitigate this distribution mismatch, we adopt an early-stage freezing strategy for defense mechanisms that rely on LoRA-Probe outputs (Step-Level and Client-Level). Security factors are updated only during the first Rf rounds and remain fixed thereafter:"

```json
{
  "key": "safefedllm2026",
  "method": "Safe-FedLLM",
  "stages": [
    "outside_training",
    "server_distribute",
    "client_pre_train",
    "client_step",
    "client_post_train",
    "server_receive",
    "server_aggregate",
    "server_post_aggregate"
  ],
  "needs_round_trip": true,
  "pipeline": [
    {
      "step": "离线训练 LoRA-Probe",
      "operator": "train_logistic_probe_on_lora_delta",
      "input": "带标签的良性/恶意 ∆LoRA 样本（由模拟的客户端本地训练产生，训练配置与 FedLLM 一致；只用前 10 个通信轮、50% 恶意设置下的样本）",
      "output": "冻结的线性探针参数 (a, c)",
      "params": {
        "feature": "第一个 transformer 层所有 LoRA 模块的 B 矩阵差，按固定顺序展平拼接",
        "normalization": "L2",
        "classifier": "logistic_regression",
        "data_rounds": "first 10 communication rounds",
        "data_malicious_ratio": "50%"
      },
      "source": "4.1 节 Offline Training, Eq 1-3; 附录 A"
    },
    {
      "step": "固定 LoRA 初始化并建立影子分支",
      "operator": "init_fixed_lora_and_shadow_branch",
      "input": "全局 LoRA 初始参数与初始化随机种子",
      "output": "所有客户端一致的 B_0；Shadow-Level 客户端的影子 LoRA 分支（固定学习率、不聚合）",
      "params": {
        "fixed_init": true,
        "shadow_branch_lr": "固定，具体数值论文未说明"
      },
      "source": "附录 B; 4.2 节 Shadow-Level; Limitations"
    },
    {
      "step": "计算第一层 B 矩阵增量",
      "operator": "lora_b_delta",
      "input": "第一个 transformer 层每个 LoRA 模块的当前 B_t（d_out × r）与 B_0",
      "output": "矩阵差集合 {ΔB_0,t}",
      "params": {"delta": "B_t - B_0", "layer": "first transformer layer", "matrix": "B only"},
      "source": "4.1 节 Eq 1-2"
    },
    {
      "step": "展平拼接与 L2 归一化",
      "operator": "flatten_concat_l2_normalize",
      "input": "{ΔB_0,t}",
      "output": "归一化特征 x̃ ∈ R^{d_probe}（d_probe 论文未说明）",
      "params": {"concat_order": "fixed", "norm": "x / ||x||_2"},
      "source": "Eq 2; 附录 A"
    },
    {
      "step": "探针打分",
      "operator": "logistic_probe_score",
      "input": "x̃_i^t",
      "output": "恶意性概率 s_i^t ∈ [0, 1]",
      "params": {"formula": "s = sigmoid(a^T x + c)"},
      "source": "4.1 节 Eq 4"
    },
    {
      "step": "阈值判定",
      "operator": "threshold_classify",
      "input": "s_i^t",
      "output": "每本地步的二值判定（恶意/良性）",
      "params": {"tau_cls": 0.8},
      "source": "4.1 节; 4.2 节 Shadow-Level; 5.1 节"
    },
    {
      "step": "Step-Level 贝叶斯计数",
      "operator": "decayed_beta_count",
      "input": "本轮 T 个步级判定，以及上一轮保留的 alpha_i, beta_i",
      "output": "更新后的 alpha_i, beta_i（跨轮保留）",
      "params": {"gamma": 0.95, "alpha_beta_init": "论文未说明"},
      "source": "4.2 节 Step-Level Eq 5; 5.1 节"
    },
    {
      "step": "Step-Level 安全因子",
      "operator": "beta_mean_trust",
      "input": "alpha_i, beta_i",
      "output": "w_i,step ∈ [0, 1]",
      "params": {"formula": "alpha / (alpha + beta)"},
      "source": "4.2 节 Eq 6"
    },
    {
      "step": "Client-Level 瞬时安全因子（两段 sigmoid 校准）",
      "operator": "two_stage_sigmoid_calibrate",
      "input": "本轮最终本地 LoRA 更新的恶意概率 s_i^r ∈ [0, 1]",
      "output": "瞬时因子 ŵ_i,client = 1 - g(s)",
      "params": {"k": 10, "breakpoints": "0.4 / 0.8 / 0.9", "segments": "[0,0.8] and (0.8,1]"},
      "source": "4.2 节 Eq 7; 附录 C Eq 13"
    },
    {
      "step": "Client-Level 参与轮历史平均",
      "operator": "running_mean_over_participation",
      "input": "客户端 i 在 R_i^r = {k <= r | i in S_k} 上的瞬时因子",
      "output": "平滑后的 w_i,client",
      "params": {"window": "all participated rounds up to r"},
      "source": "4.2 节 Eq 8"
    },
    {
      "step": "Shadow-Level 恶意比例统计",
      "operator": "shadow_branch_malicious_ratio",
      "input": "影子分支 T 个本地步的判定结果",
      "output": "rho_i^r ∈ [0, 1]",
      "params": {"denominator": "论文未说明"},
      "source": "4.2 节 Shadow-Level"
    },
    {
      "step": "Shadow-Level 指数抑制",
      "operator": "exponential_suppression",
      "input": "rho_i^r",
      "output": "w_i,shadow = (1 - rho)^eta",
      "params": {"eta": 7},
      "source": "4.2 节 Eq 9; 5.1 节"
    },
    {
      "step": "跨轮冻结安全因子",
      "operator": "freeze_security_factor_after_rounds",
      "input": "第 R_f 轮时的安全因子",
      "output": "r > R_f 时恒定的 w_i",
      "params": {"R_f": 20, "applies_to": "Step-Level 与 Client-Level；Shadow-Level 不冻结"},
      "source": "4.2 节 Eq 10; 5.1 节; 附录 B"
    },
    {
      "step": "安全门控跳轮",
      "operator": "skip_round_if_mean_weight_below",
      "input": "被采样集合 S_r 上的安全因子 {w_i}",
      "output": "保持旧全局参数 W^(r+1) = W^(r)，或继续聚合",
      "params": {"tau_skip": 0.2, "aggregate": "mean over S_r"},
      "source": "4.3 节 Eq 11; 5.1 节"
    },
    {
      "step": "安全加权聚合",
      "operator": "weighted_aggregate_by_sample_and_security",
      "input": "各客户端的 LoRA 更新 ΔW_i、本地样本数 n_i、安全因子 w_i",
      "output": "新一轮全局参数 W^(r+1)",
      "params": {"weight": "n_i * w_i / sum_j(n_j * w_j)"},
      "source": "4.3 节 Eq 12"
    }
  ],
  "sampling": [
    {"what": "clients", "how": "共 10 个客户端，每轮随机采样 3 个参与", "size": "3/10 每轮，共 100 轮"},
    {"what": "layers", "how": "只取第一个 transformer 层所有 LoRA 模块的 B 矩阵，不用 A 矩阵、不用其他层", "size": "具体注入模块与 d_probe 论文未说明"},
    {"what": "coordinates", "how": "L2 归一化把特征投到单位球，丢弃幅度只保留方向", "size": "论文未说明"},
    {"what": "rounds", "how": "探针训练只用前 10 轮的 ∆LoRA（50% 恶意设置）；Step/Client-Level 安全因子只在前 R_f 轮更新后冻结", "size": "10 轮 / R_f = 20 轮"},
    {"what": "samples", "how": "探针训练排除与模型训练数据重叠的样本；本地训练每客户端 500 条", "size": "排除 WildChat/LMSYS-Chat 前 4,000 条、BeaverTails/MaliciousGen 前 2,500 条；每客户端 500 条"},
    {"what": "probes", "how": "每个客户端每个本地步调用一次探针，影子分支同样每步一次", "size": "T = 10 次/轮/分支"}
  ],
  "resources": [
    "带良性/恶意标签的 ∆LoRA 探针训练样本（由与 FedLLM 本地训练同配置的模拟过程生成），样本条数论文未说明",
    "与客户端训练一致的 LoRA 初始化随机种子（Limitations 明确列为框架假设）",
    "冻结的线性探针参数 (a, c)",
    "Shadow-Level 需要客户端侧额外维护一条影子 LoRA 分支，可训练参数 3.41M 增至 6.82M，显存 20.62GB 增至 41.24GB（表 4）",
    "8-bit 量化基座模型（Llama3.1-8B、Qwen2.5-7B）",
    "数据：良性 LMSYS-Chat、WildChat；恶意 BeaverTails、MaliciousGen（3.1 节）",
    "仅评测用：AdvBench、MT-Bench/MT-1、GPT-5-mini 评判、奖励模型 RM、MD-Judge（3.1 节、5.1 节）"
  ],
  "actions": ["reweight"],
  "dominant_cost": "论文报告防御带来的总训练时间增幅约 3.2%（FedAvg 2h35m 对 2h40m，表 4），并称线性探针的计算与时间开销可忽略（4.1 节）；最大开销仍是客户端本地 LoRA 微调本身，Shadow-Level 因影子分支使可训练参数翻倍（3.41M→6.82M）、显存从 20.62GB 升到 41.24GB（表 4）。分析：探针侧每个本地步只做一次第一层 B 矩阵差提取、展平拼接、L2 归一化与一次线性打分，成本随特征维度 d_probe 与本地步数 T 线性增长，不需要额外反向传播；服务器侧每轮仅 O(|S_r|) 的均值、阈值与加权求和，另加按客户端保存的标量状态。",
  "underspecified": [
    "探针在客户端还是服务器执行，逐步判定与影子分支 rho 如何传到服务器，是否需要额外通信往返",
    "三个层级 Step/Client/Shadow 的安全因子如何合成为一个 w_i（论文无融合公式，实验中三者是独立变体）",
    "Eq 5 中 alpha_i 与 beta_i 的初始值",
    "Eq 1 中 B_0 是每轮起点还是联邦训练最初的 B",
    "影子分支是否每轮重置、参数是否跨轮延续、固定学习率的具体数值、rho 的分母定义",
    "Client-Level 使用的 s_i^r 是否等于主分支 t = T 时的探针输出",
    "LoRA 具体注入哪些模块以及特征维度 d_probe",
    "探针训练样本条数、类别配比、正则化与 tau_cls = 0.8 的选取过程",
    "跳轮后的边界行为：是否重采样客户端、轮计数是否递增、是否计入 R_f 与参与历史 R_i",
    "L2 归一化遇到零范数特征、s 恰等于 0.8/0.2 等边界情形的处理",
    "若安全因子在客户端侧计算并上报，如何防止恶意客户端伪造（论文未讨论）"
  ],
  "quotes": [
    {"supports": "步骤 1：离线训练 LoRA-Probe 与 ΔB 定义", "text": "Before federated training, we train a probe offline on labeled benign and malicious samples by computing the delta of LoRA B-matrices at local step t and initialization:"},
    {"supports": "步骤 3-4：只取第一个 transformer 层 B 矩阵并拼接成特征", "text": "We extract the LoRA B-matrix differences from all LoRA modules in the first transformer layer and form a feature vector:"},
    {"supports": "步骤 4：L2 归一化", "text": "To eliminate scale variation across clients and training steps, we apply L2 normalization to x to obtain the normalized feature ˜x = x/∥x∥2."},
    {"supports": "步骤 5-6：在线逐本地步检测", "text": "During FL, each client i performs T local LoRA update steps per round, where t ∈ {1, . . . , T} denotes the local step index."},
    {"supports": "步骤 7-8：Step-Level 贝叶斯统计与时间衰减", "text": "This mechanism performs maliciousness detection at each local training step and computes a client’s security factor via Bayesian statistics with a time-decay factor γ ∈ (0, 1) to gradually downweight outdated evidence."},
    {"supports": "步骤 10：Client-Level 历史平均", "text": "To reduce single-round noise, we compute a historical average over the rounds in which client i participates:"},
    {"supports": "步骤 11-12：Shadow-Level 影子分支及其用途", "text": "This mechanism introduces a client-maintained shadow LoRA branch that is independent of the main training branch. It is used only to generate LoRA updates for probe-based detection and does not participate in model training or parameter aggregation."},
    {"supports": "步骤 13：早停冻结安全因子", "text": "To mitigate this distribution mismatch, we adopt an early-stage freezing strategy for defense mechanisms that rely on LoRA-Probe outputs (Step-Level and Client-Level). Security factors are updated only during the first Rf rounds and remain fixed thereafter:"}
  ]
}
```
