# prefpoison2026：Efficient Preference Poisoning Attack on Offline RLHF

## 1. 基本信息

- **场景**：集中式（centralized）离线 RLHF（Reinforcement Learning from Human Feedback，基于人类反馈的强化学习）中的 DPO（Direct Preference Optimization，直接偏好优化）训练。论文不是联邦学习（federated learning），全文没有客户端、服务器聚合、参与率、通信轮次这些概念；也不是参数高效微调（parameter-efficient fine-tuning）供应链研究。
- **训练阶段**：偏好数据收集完成之后、策略优化开始之前的离线数据准备阶段（攻击入口）；受害者的训练发生在 DPO 策略优化阶段。Appendix C.2 另外给出奖励建模（reward modeling）阶段的一个对应命题，但论文的主要攻击与全部实验都在 DPO 阶段。
- **论文类型**：攻击（attack）。论文同时给出不可行性证书（impossibility certificate），可作为防御分析的理论工具，但论文没有提出防御算法。
- **模型与数据规模**：
  - 策略类为对数线性策略（log-linear policy），参数维度 d 等于特征维度（Definition 2.1）。
  - 合成实验：BAL-A 使用 V ∈ R^{64×20}、K* = 5、200 次蒙特卡洛试验（Section 6.1、Appendix H.1）；BMP-A 使用 V ∈ R^{200×200}、互相关 µ(V) ≈ 0.1971、K_coh = 3（Appendix H.1）。
  - 真实数据：Stanford Human Preferences（SHP）数据集，加载 20,000 个训练偏好对，用冻结的 DistilBERT（distilbert-base-uncased）编码，最大序列长度 256，取 [CLS] 嵌入，d = 768；log-linear DPO 训练 3 个 epoch，学习率 10^{-3}，批大小 256，β = 1（Appendix H.2）。BAL-A 子集 n = 50、K* = 7；BMP-A 子集 n = 401、K* = 10、预算 K ≤ 15（Section 6.1）。
  - 需要强调：Appendix I.1 明确说明实验实例化的是"fixed preference pairs 上的 log-linear DPO 模型，而不是生成式 LLM（generative LLM）"。因此论文的"模型规模"远小于联邦大模型。

## 2. 威胁模型

**攻击者**

- **身份**：论文只称"the attacker"，没有指明其在现实系统中的身份；从能力看，是能决定离线偏好数据集标签的一方。（分析：在数据供应链中，这一角色对应数据提供方 data provider。）
- **占比或数量**：论文用翻转条目数或预算 K 描述，没有给出恶意比例。理论下界是 |F| ≥ ∥g†∥_2/(2β)（精确攻击）与 |F| ≥ (∥g†∥_2 − ε)/(2β)（近似攻击）（Theorem 3.4）；实验中 K* 取 5、7、10 等小值（Section 6.1）。
- **能力**：只能把已有比较对 (s, a, a', o) 的标签 o 翻转为 −o，数据集大小固定，不能新增偏好对（Section 2.2）。论文用这一点把标签翻转攻击（label flip attack）与数据注入攻击（data injection attack）区分开。
- **知识**：白盒。Section 7 自述"attacker access to white-box feature mapping ψ"；攻击者还需要原始干净数据集 D 以构造字典 V 与目标梯度 g†（Section 3.2），并自行选定目标策略 π† 及其参数 θ†（Section 2.2）。
- **目标**：定向（targeted）策略操控。让在投毒数据集 D̃(x) 上训练得到的策略接近攻击者选定的目标策略 π†，同时最小化翻转数或满足预算 K（Section 2.2、Section 5.1）。论文没有提后门触发器、越狱或隐私目标。

**防御者**

- 论文没有设置专门的防御者角色，也没有形式化防御者能看到什么、信任什么。
- 从 Theorem 5.4 的证书可以反推使用该证书所需的信息：字典 V 的列范数上界 B、互相关 µ(V)、谱范数 ∥V∥_2，以及目标梯度范数 ∥g†∥_2 与容差 ε（Section 5.3.2）。（分析：这相当于要求防御方对数据与模型近似白盒。）

## 3. 攻击入口与流程位置

- **入口位置**：本地数据准备，也就是数据收集与标注完成后的固定偏好数据集。不是本地训练过程（损失、优化器、步数），不是更新上传前的后处理，不是服务器聚合，不是全局模型下发，也不是评估与部署。论文的表述是翻转被限制在原始数据集内（"flips are limited to the original dataset"，Section 1）。
- **具体操作步骤**：
  1. 对数据集 D 中每个比较对 i，计算特征差 Δψ_i = ψ(s_i, a_i) − ψ(s_i, a'_i)，并构造翻转效应向量 v_i = o_i β Δψ_i，拼成矩阵 V = [v_1, ..., v_n]（Section 3.2）。
  2. 选定目标策略 π†（参数 θ†），在干净数据集 D 上计算 g† = ∇_θ L_DPO(θ†; D)（Section 3.2）。
  3. 求解二元稀疏逼近问题：min_x 1ᵀx 使得 Vx = −g†（精确形式，式 (2)），或 min_x 1ᵀx 使得 ∥Vx + g†∥_2 ≤ ε（近似形式，式 (3)）。BAL-A 使用格嵌入、LLL 约减与 Babai 最近平面（Section 4）；BMP-A 使用带预算 K 的二元匹配追踪（Section 5）。
  4. 按解向量 x 的支撑集把对应样本的标签翻转，得到投毒数据集 D̃(x)（Section 2.2）。
  5. 受害者在 D̃(x) 上训练 DPO；论文用 Lemma 3.2 论证梯度残差小蕴含参数与策略接近目标。

## 4. 方法原理

核心思想：在对数线性 DPO 下，翻转单个偏好标签对梯度的改变与当前参数 θ 无关，因此"选哪些标签翻转"可以转化为固定字典上的二元稀疏逼近（binary sparse approximation）问题。

- **关键性质（Theorem 3.1）**：对样本 i，若把标签 o_i 翻转为 −o_i，则每样本梯度变化为 Δg_i = o_i β Δψ_i，是一个与 θ 无关的常数向量。
- **攻击重构（Section 3.2）**：翻转集合 F 后，∇_θ L_DPO(θ; D̃) = ∇_θ L_DPO(θ; D) + Δg_F，其中 Δg_F = Σ_{i∈F} Δg_i 与 θ 无关。由目标函数的强凸性，一阶条件足以保证最优性，于是要求 g† = −Σ_{i∈F} o_i β Δψ_i，即 Vx = −g†。x ∈ {0,1}^n 是翻转指示向量。
- **从梯度残差到策略接近（Lemma 3.2）**：若 ∥Vx + g†∥_2 ≤ ε，则 ∥θ̂ − θ†∥_2 ≤ ε/m，其中 m 是强凸系数；对对数线性策略，当 ε ≤ mϵ/(2√d) 时还有策略空间界 ∥π̂_θ − π†∥_1 ≤ ϵ。
- **翻转数下界（Theorem 3.4）**：精确攻击要求 |F| ≥ ∥g†∥_2/(2β)，近似攻击要求 |F| ≥ (∥g†∥_2 − ε)/(2β)。这来自每个翻转贡献的范数上界 2β（Appendix J.3）。
- **BAL-A（Algorithm 1）**：构造二元感知的格基 B_bin，其列向量为 b_i = (v_i; M e_i) 与 b_{n+1} = (−g†; 0)，于是格向量 y(z) = B_bin (z; −1) 满足 ∥y(z)∥² = ∥Vz + g†∥² + M²∥z∥²（式 (10)）。对约减后的基运行 Babai 最近平面得到整数系数，映射回原坐标后截断到 [0,1]。Lemma 4.1 给出使系数落在 {−1, 0, 1} 的充分下界 M_0 = (B√K* + √(B²K* + 6BR + 3B²))/3（式 (12)）；Theorem 4.2 在非负系数约束下给出 {0,1}^n 保证；Theorem 4.3 说明在分离条件 ρ_k² > M²(K* − k)（对所有 k < K*，式 (13)）下，替代目标 F_M(x) = ∥Vx + g†∥² + M²1ᵀx 的最小值点就是最小翻转的精确攻击。Appendix F 的两个反例说明不存在普适的 M。
- **BMP-A（Algorithm 2）**：把攻击视为稀疏恢复，测量向量为 y = −g†，字典为 V。每一步用归一化相关性 |⟨v_i, r⟩|/∥v_i∥_2 选一个未选列，更新 r ← r − v_i，直到预算 K 用尽或 ∥r∥_2 ≤ ε。论文定义 a_i = ∥v_i∥_2、u_i = v_i/a_i、U = V D^{-1}（D 为对角矩阵），以及互相关 µ(V) = max_{i≠j} |⟨v_i, v_j⟩|/(∥v_i∥∥v_j∥)。Theorem 5.3 给出基于相干性的恢复保证，Theorem 5.4 给出不可行性证书。

## 5. 检测或防御所需的数据

**攻击所需的输入（攻击者的数据视图）**

1. **逐样本偏好对与标签**：形如 (s_i, a_i, a'_i, o_i)，o_i ∈ {+1, −1}。采集位置：数据准备阶段，即训练开始之前（对防护库而言对应客户端训练前的本地数据钩子）。粒度：逐样本。不需要跨轮历史，不需要额外计算。
2. **白盒特征映射 ψ 与逐样本特征差 Δψ_i = ψ(s_i, a_i) − ψ(s_i, a'_i)**。采集位置：训练前。粒度：逐样本、d 维。在 SHP 实验中这一项由冻结 DistilBERT 的前向编码得到（Appendix H.2），因此需要额外的前向计算。
3. **温度参数 β 与正则化参数 λ**：来自 DPO 目标函数（Section 2.1）。
4. **干净数据集上的目标梯度 g† = ∇_θ L_DPO(θ†; D)**。采集位置：训练前，需要在攻击者选定的目标参数 θ† 处对干净数据做一次梯度计算。粒度：模型级（一个 d 维向量）。需要干净参考数据，需要额外反向计算。
5. **翻转效应字典 V = [v_1, ..., v_n]，其中 v_i = o_i β Δψ_i**。采集位置：训练前组装。粒度：客户端级（d × n 矩阵）。论文强调 V 由原始数据集 D 固定决定，−g† 由目标策略 θ† 固定决定（Section 3.2）。
6. **算法超参数**：BAL-A 需要嵌入惩罚 M 与 LLL 参数 δ（Algorithm 1）；BMP-A 需要预算 K 与容差 ε（Algorithm 2）。
7. **字典几何统计量**：列范数下界 b 与上界 B、互相关 µ(V)、谱范数 ∥V∥_2（Theorem 5.3、Theorem 5.4）。采集位置：训练前，在字典上一次性计算。粒度：客户端级、矩阵级。
8. **评估期的诊断量**：重训后参数距离 ∥θ̂ − θ†∥_2、策略距离 ∥π̂_θ − π_θ†∥_1 与 ∥π_clean − π̂_θ∥_1（Appendix I.1、Appendix I.2）。采集位置：评估时，需要重新训练模型并与干净基线比较，需要干净参考数据与额外计算。

**攻击留下的可观测量（论文有依据的部分）**

- 数据层面：SHP 上随机子集的互相关为 µ ≈ 0.807、低相关子集为 µ ≈ 0.263（Appendix I.2、Figure 6）；字典的几何直接决定攻击成败（Section 6.2.2、Section 6.2.3）。
- 梯度层面：翻转产生的梯度偏移 Δg_F 与 θ 无关，是一个常数向量（Theorem 3.1）；在 θ† 处投毒目标的一阶条件残差 ∥Vx + g†∥_2 变小（式 (4)、式 (5)）。
- 策略层面：训练后策略与目标策略、与干净策略的距离（Appendix I.1 的 Figure 5、Appendix I.2 的 Figure 8）。

**论文声称能绕过哪些检测**：论文未说明。全文没有提出或评估任何检测器（detector），也没有讨论规避检测的机制；它给出的只是刻画攻击可行性的不可能性证书。

## 6. 干预动作

- 论文没有提出任何防御或干预算法，没有剔除客户端、重新加权、裁剪、加噪、过滤样本、修复或回滚模型之类的动作。
- 论文的防御侧产出是两类不可行性证书（Theorem 5.4）：若 ∥g†∥_2 − ε > √K ∥V∥_2（式 (17)），或者 (∥g†∥_2 − ε)² > B²(K + µ(V)K(K−1))（式 (18)），则不存在任何翻转数不超过 K 的攻击能达到容差 ε。该判定与具体攻击算法无关。
- 论文自述这些是 DPO 的鲁棒性证书，并明确说明它们是充分条件：不满足证书并不意味着攻击存在，满足证书则排除所有不超过 K 次翻转的攻击（Section 5.3.2）。
- **动作发生的位置**：论文未说明。若按证书的含义使用，它作用在训练开始之前、对字典与目标梯度做检查的位置（分析）。

## 7. 实验设置与主要结果

**设置**

- 合成字典（Section 6.1、Appendix H.1）：BAL-A 使用 V ∈ R^{64×20}、K* = 5、25 个对数间隔的 M（范围 [0.05, 3.0]）、LLL 参数 δ = 0.75、200 次蒙特卡洛试验；BMP-A 使用固定的 V ∈ R^{200×200}，µ(V) ≈ 0.1971，K_coh = 3，对 K ∈ {1, ..., 60} 每个值运行 200 次试验，每次恰好迭代 K* 次。
- 真实数据（Appendix H.2）：SHP 的 20,000 个训练偏好对，冻结 DistilBERT，最大序列长度 256，[CLS] 嵌入，d = 768；log-linear DPO 训练 3 个 epoch，学习率 10^{-3}，批大小 256，β = 1。BAL-A 使用 n = 50、K* = 7、5 次试验、25 个对数间隔的 M（范围 [0.05, 10.0]）；BMP-A 使用 n = 401、K* = 10、预算到 K = 15、容差 ε = 10^{-3}、200 次试验，并对比随机子集与低相关子集。重训使用 20,000 个 Adam 步，学习率 10^{-3}。
- 恶意比例、客户端数与参与率、非独立同分布（non-IID）设置：论文未说明，因为论文是集中式设定，不存在这些概念。
- 指标：支持集恢复的真阳性率（true positive rate，TPR）、残差 ∥Vx̂ − t∥_2、参数距离 ∥θ̂ − θ†∥_2、策略距离 ∥π̂_θ − π_θ†∥_1 与 ∥π_clean − π̂_θ∥_1、互相关 µ(V)、运行时间。

**关键结果**

- 合成 BAL-A（Figure 1）：小 M 时几乎完美恢复真实支撑集；M 超过分离阈值 M_sep^all ≈ 0.68287 后恢复率迅速下降；二进制系数充分界 M_0 ≈ 1.68817（B = 1、R = 0）在该设置下过于保守（Section 6.2.1、Appendix H.1）。
- 合成 BMP-A（Figure 2）：相干性保证只覆盖到 K_coh = 3；在保证区内支持集恢复完美，超出保证区后 TPR 仍然较高并随 K* 逐渐下降（Section 6.2.2、Appendix H.1）。
- SHP 上的 BAL-A（Figure 4、Figure 5）：TPR 随 M 的变化与分离阈值一致，M_0 ≈ 6.71994（B ≈ 3.47103、R = 0）保守，M_sep^all ≈ 1.32166；参数距离与策略距离在整个 M 扫描范围内只轻微变化（Appendix I.1）。
- SHP 上的 BMP-A（Figure 6、Figure 7、Figure 8）：随机子集 µ ≈ 0.807、K_coh = 1；低相关子集 µ ≈ 0.263、K_coh = 2；低相关子集的 TPR 更高、残差下降更快，随机子集在预算增大后出现更多错误选择（Appendix I.2）。
- 匹配对照（Figure 3）：在 n = 50、K* = 7 的共同可行设置下，BAL-A（M = 0.9）与 BMP-A（K_max = 7）都精确恢复了构造的翻转模式，TP = 7、FP = 0、FN = 0；BAL-A 用时 0.6865 秒，BMP-A 用时 1.37 × 10^{-4} 秒；clean-vs-attacked 距离 ∥π_clean − π̂_θ∥_1 稳定在约 0.224，约为 attack-vs-groundtruth 距离 0.012 的 19 倍（Section 6.2.3）。
- SHP 上 attack-vs-groundtruth 的策略距离约为 ∥π_θ† − π̂_θ∥_1 ≈ 0.012（Section 6.2.3）。

## 8. 开销

- **计算**：BAL-A 的主要开销是在 (d + n) × n 的嵌入基上做格预处理，也就是 LLL 约减与 Babai 需要的线性代数预处理；Babai 本身在约减基可用之后很便宜，但预处理代价随 n 快速增长，因此实验中 BAL-A 只用于小到中等规模的攻击子集（Section 4.1）。论文还引用 Corollary G.1：在 δ-LLL 基上，Babai 算法求解 γ-CVP 时 γ ≤ √n (δ − 1/4)^{-n/2}（Appendix G）。
- **运行时间**：SHP 匹配设置下 BAL-A 为 0.6865 秒，BMP-A 为 1.37 × 10^{-4} 秒（Section 6.2.3）。（分析：两者相差约三个半数量级。）
- **通信开销**：论文未报告（论文是集中式设定）。
- **存储开销**：论文未报告。

## 9. 假设、局限与自适应攻击

**成立所依赖的假设**

- 策略属于对数线性策略类，且特征映射满足 max_{s,a} ∥ψ(s, a)∥ ≤ 1（Definition 2.1）。
- DPO 目标函数是 m-强凸的；论文引用 Nika 等人 (2025) 的 Lemma E.14，说明在 ℓ2 正则下成立（Section 3.2、Lemma 3.2）。
- 攻击者拥有白盒特征映射 ψ（Section 7）。
- 攻击者只能翻转已有比较对的标签，数据集规模固定，不能新增偏好对（Section 1、Section 2.2）。
- 存在可行的翻转攻击（Assumption 3.3、Assumption 5.1），且攻击落在稀疏预算内（Assumption 5.2）。
- 攻击者知道并选定目标策略 θ†，并能计算 g†。
- 离线设定：训练使用预先收集好的固定偏好数据集（Section 2.1）。
- Theorem 5.4 的证书只是充分条件（Section 5.3.2）。

**论文自述的局限**

- 研究限于对数线性 DPO 的标签翻转，且假设攻击者白盒访问特征映射 ψ；更广的攻击与防御设置留作未来工作（Section 7）。
- 一般可微策略类下，翻转引起的梯度偏移虽然精确但依赖 θ，V_{θ†}x = −g† 只是在 θ† 处的局部一阶条件；对非凸 DPO 目标，它本身不蕴含 θ† 是攻击目标的全局最优解（Appendix C.1）。
- 扩展到标准 RLHF 时，奖励建模阶段有类似的身份，但投毒后的奖励估计还要经过单独的策略优化阶段，参数无关的偏移本身不能给出最终策略操控的保证（Appendix C.2）。
- 不存在对所有实例都保证最小翻转恢复的普适 M（Appendix F 的 Proposition F.1 与 Proposition F.2）。
- Theorem 4.3 的精确分离条件涉及组合计算，只作理论验证用，不进入可扩展的 BAL-A 流程（Section 4.2.2）。
- 实验实例化的是固定偏好对上的对数线性 DPO 模型，而不是生成式 LLM，因此最可信的下游诊断是重训后的参数距离与策略距离，而不是定性的自由文本样例（Appendix I.1）。
- 论文没有报告客户端、通信轮次、非独立同分布等联邦设定下的实验，因为其设定本身是集中式的。

**自适应攻击**

- 论文未评估自适应攻击者，也没有讨论攻击者针对某一检测器调整策略的情形。论文未说明。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）**

- 分析：对数线性策略类是 Theorem 3.1 的关键前提；LoRA（Low-Rank Adaptation，低秩适配）微调的大模型是非线性、非凸、超高维的策略，只有 Appendix C.1 的局部且依赖 θ 的偏移身份可用，参数无关的固定字典 V 不再存在。
- 分析：m-强凸性在 LoRA 微调的 DPO 目标上不成立，Lemma 3.2 的 ∥θ̂ − θ†∥_2 ≤ ε/m 与随之而来的策略空间界都失去依据。
- 分析：白盒 ψ 假设在联邦下不成立；服务器看不到客户端的原始偏好对、特征映射或逐样本梯度，无法直接构造 V 与 g†。
- 分析：论文中的 d 是特征维度（SHP 中为 768），而 LoRA 参数量通常在百万到亿级；BAL-A 要在 (d + n) × n 的格基上做 LLL 约减，d 变成 LoRA 参数量之后在计算上不可行。
- 分析：联邦下标签翻转发生在各客户端本地数据上，每个客户端的字典 V_k 不同，全局效果取决于聚合规则与客户端采样，论文的单一集中式 V 与 g† 模型需要重新推导。
- 分析：论文的不可行性证书需要服务器掌握 µ(V)、∥V∥_2、B、∥g†∥_2，这些量在联邦 LoRA 中只能通过客户端上报的近似统计获得，统计量本身的可靠性成为新的攻击面。
- 分析：论文完全没有涉及客户端参与率、非独立同分布数据、通信轮次与 LoRA 的低秩结构，迁移时都需要额外假设与验证。

## 10. 对防护库设计的含义

1. 分析：这篇论文的攻击入口在客户端训练前的本地偏好数据标签，因此采集底座需要在客户端训练前设置逐样本钩子，记录偏好对 (s, a, a', o) 与标签，并在训练前对标签做一次快照，供后续比对。
2. 分析：要复现或检测这类攻击，库需要采集"逐样本特征差或逐样本梯度贡献"这一数据视图（对应该论文的 Δψ_i 与 v_i），并要求客户端能计算目标参数处的干净梯度 g†。这属于这篇论文特有的需求；通用底座至少应提供可选的逐样本梯度导出接口。
3. 分析：论文的防御侧只用得到四类字典统计量与目标梯度范数（B、µ(V)、∥V∥_2、∥g†∥_2），加上容差 ε 与预算 K。它们都是单轮的、不需要跨轮历史、也不需要其他客户端的数据，因此服务器钩子只需要一个"收到客户端上报的字典摘要后做一次不等式判定"的接口。
4. 分析：论文只给出报告式结论（不可行性证书），没有给出剔除、重加权、裁剪等动作，所以库的干预接口在这篇论文上只能落实为告警或拒绝进入训练的报告插件，不能假定其具备修复能力；若要接入实际干预，需要另行设计并重新论证。
5. 分析：论文的证书是充分条件，判定为安全时只说明任何不超过 K 次翻转的攻击都无法达到容差 ε，并不说明数据没有被污染；因此插件输出必须区分"已证明不可行"与"无法判定"两种状态。
6. 分析：BAL-A 与 BMP-A 是攻击求解器，不是防御算法；它们在库中的位置是红队测试插件与攻击复现基线，用来生成可控的投毒数据集，而不是防护插件本身。

## 11. 原文依据

1. **Abstract** — 支撑第 1 节与第 4 节关于论文类型与核心性质（翻转引起的参数无关梯度偏移）。
   > "We study label flip attacks against log-linear DPO. We first illustrate that flipping one preference label induces a parameter-independent shift in the DPO gradient."
2. **Section 2.2** — 支撑第 2 节威胁模型与第 3 节攻击入口（攻击者能力与固定的数据集规模）。
   > "We study label flip attacks on offline preference datasets. The attacker selects a subset of comparisons and flips their outcomes, equivalently changing oi to −oi on the chosen indices. The size of the dataset is fixed."
3. **Section 2.2** — 支撑第 2 节关于攻击目标为定向策略操控。
   > "In this formulation, the goal of the attacker is to force πˆθ( ˜D(x)) to align with a target policy π† (with parameter θ†) decided by the attacker, while modifying as few labels as possible."
4. **Theorem 3.1** — 支撑第 4 节方法原理中翻转效应为常数向量这一关键性质。
   > "If we flip the label oi to ˜oi = −oi, and we have ˜gi(θ) replacing the oi with ˜oi in gi(θ), then for every θ the per-sample gradient changes by a constant vector that is independent of θ"
5. **Section 4.1** — 支撑第 8 节关于 BAL-A 的计算开销。
   > "From a computational perspective, the dominant cost of BAL-A is the lattice preprocessing on the (d + n) × n embedded basis, that is, LLL reduction plus the linear-algebra preprocessing used by Babai."
6. **Section 5.3.2** — 支撑第 6 节（论文只给出证书，没有实际干预动作）与第 9 节（证书是充分条件）。
   > "These are certificates of robustness of DPO: failing them does not imply an attack exists, but satisfying them rules out all K-flip attacks, independent of specific attack algorithms."
7. **Section 6.1** — 支撑第 7 节实验设置中 BAL-A 与 BMP-A 的子集规模。
   > "BAL-A is evaluated on a smaller subset (n = 50, K⋆= 7) because of lattice reduction cost, while BMP-A is evaluated on a larger subset (n = 401, K⋆= 10) with budget K ≤15, comparing random and low-coherence subsets."
8. **Section 6.2.3** — 支撑第 7 节匹配对照实验的精确恢复结果。
   > "In this matched case, BAL-A and BMP-A recover the same constructed flip pattern exactly (TP = 7, FP = 0, FN = 0), so their attacked subsets coincide."
9. **Section 6.2.3** — 支撑第 7 节 clean-vs-attacked 与 attack-vs-groundtruth 的数值结果。
   > "The clean-vs-attacked distance ∥πclean − πˆθ∥1 stabilizes to around 0.224, which is about 19 times the attack-vs-groundtruth distance of 0.012."
10. **Appendix I.1** — 支撑第 1 节与第 9 节关于实验并非生成式大模型这一重要限定。
    > "Because this experiment instantiates a log-linear DPO model on fixed preference pairs rather than a generative LLM, the most faithful downstream diagnostics here are parameter and policy distances after retraining, rather than qualitative free-form response examples."

```json
{
  "key": "prefpoison2026",
  "title": "Efficient Preference Poisoning Attack on Offline RLHF",
  "year": 2026,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["other"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "逐样本偏好对与标签 (s_i, a_i, a'_i, o_i)", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "白盒特征映射下的逐样本特征差 Δψ_i = ψ(s_i,a_i) − ψ(s_i,a'_i)", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "翻转效应字典 V = [v_1,...,v_n]，其中 v_i = o_i β Δψ_i", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "目标参数 θ† 处干净 DPO 损失的梯度 g†", "where": "client_pre_train", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "字典几何统计量：列范数下界 b、上界 B、互相关 µ(V)、谱范数 ∥V∥_2", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "重训后的参数距离与策略距离 ∥θ̂−θ†∥_2、∥π̂−π†∥_1、∥π_clean−π̂∥_1", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["report_only"],
  "intervention_where": ["none"],
  "assumptions": [
    "策略属于对数线性策略类，且 max ∥ψ(s,a)∥ ≤ 1",
    "DPO 目标在 ℓ2 正则下 m-强凸",
    "攻击者白盒访问特征映射 ψ 并能计算逐样本梯度",
    "只翻转已有比较对的标签，数据集规模固定",
    "存在可行的稀疏翻转攻击（Assumption 3.3 与 Assumption 5.1、5.2）",
    "离线设定：训练使用预先收集的固定偏好数据集",
    "Theorem 5.4 的证书只是充分条件，不满足不意味着攻击存在"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第1节与第4节：论文类型为对数线性 DPO 上的标签翻转攻击，核心是参数无关的梯度偏移", "text": "We study label flip attacks against log-linear DPO. We first illustrate that flipping one preference label induces a parameter-independent shift in the DPO gradient."},
    {"section": "Section 2.2", "supports": "第2节与第3节：攻击者能力仅限翻转已有比较对的标签，数据集规模固定", "text": "We study label flip attacks on offline preference datasets. The attacker selects a subset of comparisons and flips their outcomes, equivalently changing oi to −oi on the chosen indices. The size of the dataset is fixed."},
    {"section": "Section 2.2", "supports": "第2节：攻击目标为使学习到的策略对齐攻击者选定的目标策略，同时尽量少改标签", "text": "In this formulation, the goal of the attacker is to force πˆθ( ˜D(x)) to align with a target policy π† (with parameter θ†) decided by the attacker, while modifying as few labels as possible."},
    {"section": "Theorem 3.1", "supports": "第4节：翻转单个标签引起的每样本梯度变化是与参数无关的常数向量", "text": "If we flip the label oi to ˜oi = −oi, and we have ˜gi(θ) replacing the oi with ˜oi in gi(θ), then for every θ the per-sample gradient changes by a constant vector that is independent of θ"},
    {"section": "Section 4.1", "supports": "第8节：BAL-A 的主要计算开销来自嵌入基上的格预处理", "text": "From a computational perspective, the dominant cost of BAL-A is the lattice preprocessing on the (d + n) × n embedded basis, that is, LLL reduction plus the linear-algebra preprocessing used by Babai."},
    {"section": "Section 5.3.2", "supports": "第6节与第9节：论文只提供充分性的不可行性证书，没有提出具体干预动作", "text": "These are certificates of robustness of DPO: failing them does not imply an attack exists, but satisfying them rules out all K-flip attacks, independent of specific attack algorithms."},
    {"section": "Section 6.1", "supports": "第7节：BAL-A 与 BMP-A 在 SHP 上使用不同规模的子集与预算", "text": "BAL-A is evaluated on a smaller subset (n = 50, K⋆= 7) because of lattice reduction cost, while BMP-A is evaluated on a larger subset (n = 401, K⋆= 10) with budget K ≤15, comparing random and low-coherence subsets."},
    {"section": "Section 6.2.3", "supports": "第7节：匹配对照设置下两种方法都精确恢复构造的翻转模式", "text": "In this matched case, BAL-A and BMP-A recover the same constructed flip pattern exactly (TP = 7, FP = 0, FN = 0), so their attacked subsets coincide."},
    {"section": "Section 6.2.3", "supports": "第7节：clean-vs-attacked 距离约为 attack-vs-groundtruth 距离的 19 倍", "text": "The clean-vs-attacked distance ∥πclean − πˆθ∥1 stabilizes to around 0.224, which is about 19 times the attack-vs-groundtruth distance of 0.012."},
    {"section": "Appendix I.1", "supports": "第1节与第9节：实验实例化的是非生成式的对数线性 DPO 代理模型，而非生成式大模型", "text": "Because this experiment instantiates a log-linear DPO model on fixed preference pairs rather than a generative LLM, the most faithful downstream diagnostics here are parameter and policy distances after retraining, rather than qualitative free-form response examples."}
  ]
}
```
