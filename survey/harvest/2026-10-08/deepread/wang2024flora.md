# wang2024flora：FLoRA: Federated Fine-Tuning Large Language Models with Heterogeneous Low-Rank Adaptations

## 1. 基本信息

- **场景**：联邦大模型微调（federated fine-tuning of large language models），属于参数高效微调（parameter-efficient fine-tuning, PEFT）在联邦学习（federated learning, FL）中的聚合方法研究。不是传统联邦学习（图像分类）场景，也不是集中式训练场景：论文全程在联邦框架内微调 LLM，并额外与集中式 LoRA（centralized LoRA）和单机独立训练（Standalone）作对照。
- **训练阶段**：服务器初始化并下发预训练模型 W → 客户端本地初始化并微调 LoRA 模块 → 客户端上传本地 LoRA 模块 → 服务器堆叠聚合（stacking aggregation）→ 服务器下发全局 LoRA 模块 → 客户端更新本地模型，多轮循环（Section 3.2、Figure 3）。
- **论文类型**：基础方法（foundation）。这是一篇提出新聚合算法的论文，不是攻击论文，也不是检测或防御论文；全文没有威胁模型章节，没有任何投毒、后门、越狱（jailbreak）或投毒防御实验。
- **模型与数据规模**：基座模型为 TinyLlama 1.1B、Llama 7B、Llama2 7B（Section 4.1）。微调数据为 Databricks-dolly-15k（约 15k 条）、Alpaca（52K 条指令数据）、Wizard（70k 指令–输出对）、ShareGPT（约 52,000 段对话，实验中被拆成问答对）（Appendix A.1）。评测集为 MMLU（14,024 题、57 个科目，论文抽取其中 1444 个样本）与 MT-bench（Appendix A.1）。联邦侧共 10 个客户端，非独立同分布（non-IID）划分（Section 4.1）。LoRA 只加在自注意力层（self-attention layers）上（Section 4.1）。
- **版本信息**：论文标注为 "Preprint. Under review."，arXiv:2409.05976v1 [cs.LG]，2024 年 9 月 9 日。

## 2. 威胁模型

**论文未说明**完整的威胁模型：全文没有定义攻击者、攻击目标、攻击者占比、攻击者能力或攻击者知识，也没有任何攻防实验。

论文唯一涉及对抗性主体（adversary）的地方是 Section 5 "The Privacy Preservation of FLORA"：论文指出，FLoRA 要求把全部客户端上传的 LoRA 模块堆叠起来，这会引入隐私隐患，因为**恶意客户端（malicious clients）**可能通过服务器下发的全局 LoRA 模块推断出其他客户端的 LoRA 矩阵。这是全文对攻击者唯一的描述，且没有给出数量、占比、能力边界或成功率的量化。

- **攻击者是谁**：仅提到"恶意客户端"（Section 5）。没有提到恶意服务器、数据提供方或适配器发布者。
- **攻击者占比或数量**：论文未说明。
- **攻击者能力**：论文只说明其能观察服务器下发的全局 LoRA 模块并据此推断其他客户端的 LoRA 矩阵（Section 5）；能修改什么、能否操纵本地训练或上传内容，论文未说明。
- **攻击者知识**：论文未说明。
- **攻击目标**：论文只隐含了隐私推断这一类目标；无目标破坏（untargeted）、定向后门（backdoor）、越狱或安全对齐破坏（jailbreak / safety alignment）等目标论文均未提及。
- **防御者是谁**：论文中服务器只充当诚实的聚合器与分发者（Section 3.2、Figure 3）。
- **防御者能看到什么**：服务器可以看到每个参与客户端的本地 LoRA 模块 A_k 与 B_k、本地秩 r_k，以及用于计算缩放因子 p_k 的本地数据量 len(D_k)（Section 3.2、Equation 11–12）。
- **防御者信任什么**：论文未显式声明信任假设。流程上服务器直接按 Equation 11 聚合客户端上传的矩阵，没有校验、没有异常检测、没有鲁棒聚合（robust aggregation）；收敛分析还沿用了 FedAvg 的"全客户端参与"设定（Appendix B）。**分析**：这实际上默认了客户端会诚实上报 LoRA 模块与数据量。

## 3. 攻击入口与流程位置

**论文不是攻击论文**，全文没有任何攻击方法或攻击实验，因此不存在"论文的攻击入口"。论文的贡献是替换服务器端的聚合规则：它针对的是一种数学错误（FedIT 独立平均 A 与 B 导致的聚合噪声），而不是某一种攻击。

论文自身修改流程的位置是**服务器聚合（server aggregation）**；它唯一提到的攻击面位于**全局模型下发（model distribution）**：

1. **服务器初始化下发**：服务器把预训练参数 W 分发给全部 K 个客户端，客户端根据本地数据复杂度和可用资源确定本地 LoRA 秩（Section 3.2）。
2. **本地微调（local fine-tuning）**：客户端每轮先重新初始化本地 LoRA 模块，再用本地数据训练若干迭代，然后把本地 LoRA 模块上传（Section 3.2）。
3. **堆叠聚合（stacking-based LoRA aggregation）**：服务器收到异质 LoRA 模块后，按 Equation 10 / Equation 11 把所有 B_k 沿列方向、把所有 A_k 沿行方向拼接，得到全局 A 与 B（Section 3.2）。
4. **更新本地模型（update local models）**：服务器把堆叠后的全局 LoRA 模块 A 和 B 发回客户端，客户端用 BA 更新本地模型并继续微调（Section 3.2）。
5. **隐私攻击面**：位于第 4 步的下发环节。全局 LoRA 模块中保留了各客户端子矩阵的拼接结构，恶意客户端可以据此推断其他客户端的 LoRA 矩阵（Section 5）。

## 4. 方法原理

论文先指出 FedIT（把 FedAvg 直接套到 LoRA 上）的两个问题（Section 1、Section 2、Figure 1 与 Figure 2）：

- **聚合噪声**：A 与 B 单独都不是模型更新，只有 BA 才是。两个客户端时，期望的全局更新是 p0B0A0 + p1B1A1（Equation 5），而 FedIT 独立平均得到的是 (p0B0 + p1B1)(p0A0 + p1A1) = p0²B0A0 + p1²B1A1 + p0p1(B0A1 + B1A0)（Equation 6），多出跨客户端的交叉项，并且缩放因子被平方。
- **不支持异质秩**：Equation 3 的独立平均要求所有客户端秩相同，无法聚合异质 LoRA（heterogeneous LoRA）。

**核心思想（Section 3.1）**：矩阵乘积可以按秩分解成子矩阵乘积之和，因此本地更新的求和等价于"先拼接再相乘"。论文的堆叠算子用 "⊕" 表示：对 A 是沿行方向向下堆叠，对 B 是沿列方向向右堆叠（Equation 9），并给出核心等式：K 个 LoRA 模块对的乘积之和等于其堆叠矩阵之积，即 Σ_k B_k A_k = (B0 ⊕ … ⊕ BK)(A0 ⊕ … ⊕ AK)（Equation 10）。论文用一个 A ∈ R^(2×3)、B ∈ R^(3×2) 分解为两个秩 1 子矩阵的例子说明这一点（Equation 8），元素级写法为 δ_xy = Σ_i a_yi b_xi（Equation 7）。

**FLoRA 的聚合规则（Section 3.2, Equation 11）**：A = p0A0 ⊕ p1A1 ⊕ … ⊕ pKAK，B = B0 ⊕ B1 ⊕ … ⊕ BK，其中 A_k ∈ R^(r_k×n)、B_k ∈ R^(m×r_k)，聚合后 A ∈ R^((Σr_k)×n)、B ∈ R^(m×(Σr_k))。缩放因子 p_k = len(D_k) / len(Σ_k D_k)（Equation 12），由本地数据量占比决定，并且**只能乘在 A_k 或 B_k 其中之一上**，否则最终 BA 中因子会被平方。论文强调堆叠不要求各客户端秩一致，只要求所有客户端微调的是同一个预训练模型，即共享相同的维度 m 与 n（Section 3.2）。

**收敛性（Appendix B）**：论文在 [11] 的 FedAvg 收敛分析框架下，额外引入假设 5（LoRA 梯度无偏：B_k^(t+1)A_k^(t+1) − B_k^(t)A_k^(t) = η^(t)∇F_k(W_k^(t)|ξ_k^(t))），给出 Theorem 1：δ(T) ≤ 2k/(γ+T) · (M/μ + 2L‖W^(1) − W*‖²)（Equation 13），其中 M = Σ_k p_k²σ_k² + 6LΓ + 8(E−1)²G²，Γ 度量非独立同分布程度（Equation 14）。论文据此声称 FLoRA 的误差随轮数趋于零，而 FedIT 因为偏离 FedAvg 的更新规则而无法达到 O(1/T) 的收敛率。

**隐私处理（Section 5）**：论文提出把每个客户端的本地 LoRA 模块拆成秩为 1 的子模块，再以随机顺序堆叠，使恶意客户端无法还原其他客户端的本地 LoRA 模块。

## 5. 检测或防御所需的数据

论文的方法是聚合算法，不是检测器，因此下面列出的是**该方法运行所必须的输入**，而不是检测特征。

1. **每个客户端的本地 LoRA 模块 A_k 与 B_k**。
   - 是什么：客户端在本地指令数据上微调后得到的两个低秩矩阵（应用在自注意力层上）。
   - 在哪里采集：客户端训练后上传，服务器收到更新时（server receive）读取（Section 3.2，Equation 11）。
   - 粒度：逐客户端、逐层（自注意力层）、逐轮。
   - 是否需要跨轮历史：不需要。论文明确说客户端每轮在本地微调前重新初始化 LoRA 模块（Section 3.2），轮与轮之间 LoRA 没有继承关系。
   - 是否需要干净参考数据或根数据集：不需要。
   - 是否需要额外前向或反向计算：不需要。
   - 是否需要其他客户端的数据：不需要原始数据，但聚合本身需要全部参与客户端的模块同时在场。
2. **本地数据量 len(D_k)**。
   - 是什么：客户端本地数据集大小，用于计算缩放因子 p_k（Equation 12）。
   - 在哪里采集：随客户端更新一起由客户端上报到服务器（server receive）。
   - 粒度：逐客户端、逐轮。
   - 是否需要历史、干净参考数据、额外计算或其他客户端数据：都不需要（只需全体客户端的数据量之和作为分母）。
3. **本地 LoRA 秩 r_k**。
   - 是什么：每个客户端本地配置的秩，决定拼接后的总维度 Σr_k；论文实际上可以从 A_k、B_k 的形状直接推断，不需要单独上报。
   - 在哪里采集：服务器收到更新时。
   - 粒度：逐客户端、逐层（论文实验中按客户端设定，如 [64, 32, 16, 16, 8, 8, 4, 4, 4, 4]）。
   - 是否需要历史、干净参考数据、额外计算：都不需要。
4. **聚合后下发的全局 LoRA 模块 A 与 B**。
   - 是什么：堆叠后的全局 A ∈ R^((Σr_k)×n) 与 B ∈ R^(m×(Σr_k))，由服务器下发回客户端。
   - 在哪里采集：服务器聚合之后、下发之前（server post-aggregate）。
   - 粒度：模型级/逐层、逐轮。
   - 这一项在论文中同时是**攻击者的可观测量**：恶意客户端从下发的全局 LoRA 模块中推断其他客户端的 LoRA 矩阵（Section 5）。
5. **论文未说明但分析上相关的输入**：论文的收敛分析（Appendix B）里出现随机梯度 ∇F_k(W_k^(t), ξ_k^(t))、本地目标 F_k、梯度方差上界 σ_k² 与梯度范数上界 G²，但这些都只存在于理论假设中，论文没有采集或估计它们。

**从攻击论文视角看**（论文本身不是攻击论文，因此这一问只能照实说明）：论文未说明任何攻击会在哪些可观测量上留下痕迹，也未说明任何可绕过的检测器。论文自己承认的唯一"痕迹"是：堆叠使全局 LoRA 中保留了各客户端子矩阵的分块结构，恶意客户端可以直接定位并推断其他客户端的模块（Section 5）。

## 6. 干预动作

论文的动作全部发生在**服务器聚合阶段**，具体包括：

1. **堆叠合并（stacking）**：服务器把各客户端的 A_k 沿行拼接、B_k 沿列拼接，得到全局 A 与 B，而不是做加权平均（Section 3.2，Equation 11）。
2. **按数据量重加权（reweight）**：把 p_k = len(D_k)/len(Σ_k D_k) 乘到本地更新上，并且只乘在 A_k 或 B_k 的其中一侧（Equation 11–12）。论文没有做客户端剔除（exclude client）、梯度裁剪（clip）、加噪（add noise）、样本过滤（filter samples）、模型修复或回滚（repair / rollback）。
3. **隐私缓解动作**：把本地 LoRA 拆成秩 1 子模块后以随机顺序堆叠，防止恶意客户端还原其他客户端的 LoRA 模块（Section 5）。
4. **兼容但未实现的动作**：论文称 FLoRA 与加密（encryption）和差分隐私（differential privacy, DP）等标准隐私机制兼容，但没有实现、也没有做任何相关实验（Section 5）。
5. **无检测后动作**：论文没有任何检测组件，因此不存在"检测之后做什么"的问题；论文未说明如何识别或处理恶意更新。

## 7. 实验设置与主要结果

**设置（Section 4.1、Appendix A.1、A.2）**：基座模型为 TinyLlama（1.1B）、Llama（7B）、Llama2（7B）；LoRA 只加在自注意力层；10 个客户端，按 FedIT 的非独立同分布设定随机采样（Section 4.1）；学习率 0.0003，batch size 128，micro batch size 16（Appendix A.2）；硬件为 256GB 内存的 AMD EPYC 7763 64 核处理器、4 张 NVIDIA RTX A6000 GPU（Appendix A.1）。通信轮数与本地 epoch 见 Table 2：TinyLlama 在 Dolly/Alpaca/Wizard 上为 3 轮 1 epoch、ShareGPT 为 1 轮 1 epoch；Llama 在 Dolly/Alpaca 上为 3 轮 3 epoch、Wizard/ShareGPT 为 1 轮 1 epoch；Llama2 在 Wizard/ShareGPT 上为 1 轮 1 epoch（Appendix A.2，Table 2）。**恶意客户端比例：论文未说明**（论文没有攻击者）。指标为 MMLU 准确率与 MT-bench 分数（GPT-4 打分）。

**同质 LoRA 结果（Section 4.2，Table 1）**：所有客户端秩固定为 16。FLoRA 在全部模型与任务上优于 FedIT。例如 TinyLlama + Dolly 的 MMLU 准确率为 30.80，而 FedIT 为 16.35，论文称"nearly doubles"；Llama + Wizard 的 MT-bench 为 4.21，FedIT 为 3.07。同表中 TinyLlama 集中式 LoRA 为 MMLU 27.99 / 28.03 / 29.13 与 MT-bench 2.34 / 2.79，Llama 集中式 LoRA 为 35.91 / 29.18 / 31.68 与 4.38 / 3.99；论文指出在某些设定下 FLoRA 甚至超过集中式微调（Table 1）。

**异质 LoRA 结果（Section 4.2，Table 1）**：客户端秩设为 [64, 32, 16, 16, 8, 8, 4, 4, 4, 4]。TinyLlama 上 FLoRA 的 MMLU 为 18.45 / 29.69 / 41.48、MT-bench 为 3.14 / 2.71，零填充（zero-padding）基线为 15.76 / 29.56 / 40.79 与 1.56 / 1.29；Llama 上 FLoRA 为 28.50 / 29.54 / 27.91 与 4.14 / 3.64，零填充为 26.46 / **7.97** / 26.98 与 3.51 / 3.26（Table 1）。Llama2 的结果在 Table 4（MT-bench）：集中式 4.24 / 3.99，同质 FedIT 4.03 / 3.87，同质 FLoRA 4.22 / 3.96，异质零填充 4.01 / 3.70，异质 FLoRA 4.17 / 3.91。

**缩放因子消融（Section 4.2，Figure 5、Figure 7）**：默认缩放因子为 0.1（10 个客户端、本地数据量相等时由 Equation 12 得出），另外测试 0.01、0.05、0.2。论文称没有发现清晰规律或最优值，最优缩放因子依赖数据集、任务与模型。

**秩的影响（Section 4.2，Figure 4）**：全局模型在多数情况下优于所有本地模型，例外是 TinyLlama + Wizard 上秩 32 的客户端略高于全局模型；秩 8 在各模型与数据集上表现稳定，极端秩的表现随模型容量而分化。

**与 AdaLoRA 结合（Appendix A.3，Table 3）**：TinyLlama 的本地秩总和从 160 降到 120，MT-bench 从 3.13 变为 3.14；Llama 从 160 降到 131，MT-bench 从 4.21 变为 4.10；Llama2 从 160 降到 140，MT-bench 从 4.17 变为 4.25。

## 8. 开销

- **通信开销（Section 5，Figure 6）**：论文比较了全量微调、FedIT 与 FLoRA 在三个通信轮次中传输的参数数量之比，结论是 FLoRA 比 FedIT 略多传输参数，但仍显著低于全量微调；论文解释主要通信负载是初始的完整模型参数下发，后续轮次只传较小的 LoRA 矩阵，因此额外开销占比有限。论文在正文中没有给出任何绝对数值或具体比例，只有 Figure 6 的图示。
- **计算开销**：论文未报告 FLoRA 自身的额外计算开销。论文只在与相关工作比较时说零填充方法会带来额外的计算开销（Section 6），并在 Table 3 中显示 FLoRA+AdaLoRA 可减少可训练参数量（本地秩总和 160 → 120 / 131 / 140）。
- **存储开销**：论文未报告。
- **论文自述的限制（Appendix C）**：服务器需要把堆叠后的 LoRA 模块发给客户端，增加了通信成本；论文认为相对于微调效果的提升与收敛加速，这一增加是可以接受的。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文明确写出）**：

- 所有客户端微调同一个预训练模型，共享相同的维度 m 与 n；对本地秩没有任何约束（Section 3.2）。
- 客户端每轮在本地微调前重新初始化本地 LoRA 模块（Section 3.2）。
- 缩放因子只能乘在 A_k 或 B_k 其中之一上（Section 3.2）。
- 收敛分析沿用 [11] 的四个假设（Appendix B）：假设 1，本地目标函数 L-光滑；假设 2，本地目标函数 μ-强凸；假设 3，各客户端随机梯度方差有界，E‖∇F_k(W_k^(t), ξ_k^(t)) − ΔW_k^(t)‖² ≤ σ_k²；假设 4，随机梯度期望平方范数一致有界，E‖∇F_k(W_k^(t), ξ_k^(t))‖² ≤ G²。
- 额外假设 5（Appendix B）：LoRA 模块的更新是基座模型上 SGD 梯度的无偏估计。
- 收敛率继承自全客户端参与（full client participation）的 FedAvg 分析框架（Appendix B）。

**论文自述的局限（Appendix C）**：服务器下发堆叠后的 LoRA 会增加通信开销；受计算资源与时间限制，实验只使用了 Llama 系列模型，作者希望未来观察其他类型 LLM 的联邦微调。此外论文声明秩的自适应不在本文范围内，只建议结合 AdaLoRA（Section 3.2），并且缩放因子没有稳定的最优选择（Section 4.2）。

**是否评估自适应攻击者**：没有。论文完全没有攻击实验，也没有评估任何投毒、后门或隐私攻击的自适应变体；Section 5 对隐私风险的讨论是定性的，没有实验验证随机排列秩 1 子模块能否真正阻止推断。

**迁移到联邦 LoRA 微调时可能失效的假设**：

- **分析**：FLoRA 的堆叠要求所有客户端共享同一个基座模型的 m、n 维度以及相同的目标模块集合（论文只对自注意力层加 LoRA）。在真实的适配器供应链（adapter supply chain）里，不同客户端可能使用不同基座、不同 target modules 或不同 LoRA 配置，此时拼接维度无法对齐，Equation 10 的等式不成立。
- **分析**：FLoRA 隐含假设服务器诚实且按规则聚合，但投毒防护库通常要覆盖恶意服务器场景；论文没有针对恶意服务器的任何机制。
- **分析**：堆叠把每个客户端的贡献保留为全局更新中的独立加性分块（Σ_k B_k A_k），论文没有做任何裁剪或范数约束，所以一个恶意客户端可以无界地放大自己那一块而不被任何机制限制；这是从 Equation 10 直接得出的推论，论文本身没有讨论这一鲁棒性问题。
- **分析**：论文假设 p_k 由客户端诚实上报的数据量决定（Equation 12），防护库面对的是可能虚报数据量以放大自己权重的客户端，论文没有对应的验证机制。
- **分析**：论文假设客户端每轮重新初始化 LoRA，轮间没有状态延续；如果防护库需要基于跨轮更新历史做后门检测，就必须额外记录每轮的 A_k、B_k 与轮次索引，这一数据在论文流程里是不保留的。
- **分析**：论文的收敛证明依赖 L-光滑与 μ-强凸假设，这对 LLM 的非凸损失一般不成立；论文自己也只是沿用标准 FedAvg 分析框架。因此"FLoRA 收敛更快、更准确"的结论只能按论文给出的实验证据来采信，不应外推到定理所覆盖的条件之外。
- **分析**：论文第 5 节的隐私缓解（拆成秩 1 子模块并随机排列）依赖攻击者不知道排列顺序、也无法通过子空间匹配重建模块；论文没有实验支撑这一假设，而排列会同时破坏防护库识别"哪一块属于哪个客户端"的能力，这构成隐私与可检测性之间的直接冲突。

## 10. 对防护库设计的含义

- **分析**：这项工作的核心需求是"服务器聚合钩子必须支持拼接型聚合"。传统 FL 防护库的聚合接口默认接收一组同形状的更新张量并做加权平均，而 FLoRA 的全局更新是 A 沿行、B 沿列的拼接，聚合前后的张量形状不同（A ∈ R^((Σr_k)×n)、B ∈ R^(m×(Σr_k))）。库的服务器钩子需要能在"收到更新之后、聚合之前"暂停，把每个客户端的 A_k、B_k 作为独立的视图暴露给插件，再由插件决定是平均、拼接还是鲁棒聚合。
- **分析**：采集底座需要把 LoRA 更新的采集点做成"客户端训练后"的固定钩子，采集对象是每个客户端的 A_k、B_k、本地秩 r_k 和本地数据量 len(D_k)（后两者也可由形状与上报元数据推断）。这是通用需求，任何面向联邦 LoRA 的插件都会用到。
- **分析**：FLoRA 特有的数据视图是"逐客户端分块归属"。因为堆叠保留了分块结构，服务器侧插件可以天然地把全局更新拆回每个客户端的贡献 Σ 项，从而做逐客户端的范数、与全局方向的余弦相似度或跨轮一致性检查——论文自己不做这些检查，但它的聚合形式为这些检查免费提供了归属信息。库应当在聚合钩子里把"块索引到客户端标识"的映射作为一等公民保留下来。
- **分析**：干预接口需要支持"块粒度"的操作，而不仅是"客户端粒度"的操作：论文的缩放因子 p_k 只允许乘在 A_k 或 B_k 的一侧（否则最终更新中因子被平方），说明库在实现重加权类插件时必须允许指定作用侧；同理，裁剪或置零若要注入 FLoRA 流程，应在拼接之前逐块执行，或在拼接之后按块掩码。
- **分析**：隐私排列与可检测性存在取舍。论文建议的秩 1 随机排列会打散块归属，使上述逐客户端检查失效；库应把"是否保留块归属"设计为可配置项，并明确记录该配置对哪些插件不可用。这是这篇论文特有的需求，一般联邦 LoRA 库未必遇到。
- **分析**：库不需要为这项工作准备干净参考数据、根数据集或额外的前向反向计算；但需要保留跨轮历史的能力（论文的流程本身每轮重置 LoRA，不保留历史），否则跨轮后门检测类插件无法工作。评估与部署钩子还需要支持 MMLU、MT-bench 这类效用评测，以便衡量任何插件对微调效果的影响，这部分是通用需求。

## 11. 原文依据

1. Section 1（Introduction，第 2 页）："However, FedIT faces two key issues. First, the naive averaging of local LoRA modules in FedIT introduces noise to the global model update. Specifically, FedIT averages local A and B independently, which introduces mathematical errors to the global LoRA." —— 支撑第 3 节与第 4 节：论文针对的是聚合规则的数学错误，而不是某种攻击。
2. Section 3.1（Stacking-based Noise-free Aggregation）："This mechanism demonstrates that, in the context of federated fine-tuning, we can achieve a noise-free aggregation of local updates by simply stacking the local LoRA modules. This process also avoids transmitting the full model parameters, thus reducing communication costs." —— 支撑第 4 节的核心方法与第 8 节的通信开销论述。
3. Section 3.2（Equation 11–12 上下文）："where pk represents the scaling factor for each local update, determined by the relative size of the local data to the global data:" —— 支撑第 5 节第 2 项：方法需要每个客户端的本地数据量来计算缩放因子。
4. Section 3.2："Note that the scaling factor pk should be only applied to one of Ak and Bk to avoid squaring the factor in the final model update BA." —— 支撑第 6 节的重加权动作与第 10 节的干预接口设计。
5. Section 3.2："This approach imposes no constraints on the ranks of each local LoRA module as long as each client fine-tunes the same pre-trained model, i.e., they share the same dimension m and n." —— 支撑第 9 节"所有客户端共享同一基座模型"这一关键假设。
6. Section 4.1（Experiment Setup）："We evaluate the federated fine-tuned models on MMLU [7] for the QA task and MT-bench [29] for the chat assistant task, respectively. We sample 10 clients uniformly at random following the non-IID setting in FedIT [25]." —— 支撑第 7 节的客户端数量、非独立同分布设定与评测指标。
7. Section 5（The Privacy Preservation of FLORA）："The requirement of FLORA to stack the LoRA modules uploaded by all clients introduces a potential privacy concern, as malicious clients might infer the LoRA matrices of other clients through the global LoRA modules sent from the server." —— 支撑第 2 节"论文唯一提到的攻击者是恶意客户端"与第 3 节第 5 步的攻击面位置。
8. Section 5："To address this issue, we split all the local LoRA modules into sub-modules with rank=1 and then stack the sub-modules together in random order. This approach prevents malicious clients from recovering the local LoRA modules from other clients." —— 支撑第 6 节第 3 项与第 9 节关于隐私缓解依赖未验证假设的分析。
9. Appendix B（Convergence Analysis, Assumption 5）："The updates applied to LoRA modules by each client serve as unbiased estimators of the gradient that would be directly computed on the base model through SGD" —— 支撑第 9 节列出的收敛性假设。
10. Appendix C（Limitation）："Our approach has the limitation that the server sends the stacked LoRA modules to the client, thereby increasing the communication costs. We discussed this limitation both theoretically and experimentally in Section 3 and Section 4, respectively." —— 支撑第 8 节的通信开销与第 9 节的论文自述局限。

```json
{
  "key": "wang2024flora",
  "title": "FLoRA: Federated Fine-Tuning Large Language Models with Heterogeneous Low-Rank Adaptations",
  "year": 2024,
  "paper_type": "foundation",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["malicious_client"],
  "attack_goal": ["privacy"],
  "attack_entry": ["model_distribution"],
  "observables": [
    {"what": "各客户端本地训练后的 LoRA 模块 A_k 与 B_k（自注意力层，含各自秩 r_k）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "各客户端本地数据量 len(D_k)，用于计算缩放因子 p_k", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "本地 LoRA 秩 r_k，决定堆叠后的总维度，可由 A_k 与 B_k 的形状推断", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "聚合堆叠后下发给客户端的全局 LoRA 模块 A 与 B，恶意客户端可据此推断其他客户端的模块", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["reweight"],
  "intervention_where": ["server"],
  "assumptions": [
    "所有客户端微调同一个预训练模型，共享相同的维度 m 与 n（Section 3.2）",
    "客户端每轮在本地微调前重新初始化本地 LoRA 模块，轮间 LoRA 无状态继承（Section 3.2）",
    "缩放因子只能乘在 A_k 或 B_k 其中之一上，否则最终更新中因子被平方（Section 3.2）",
    "假设 1：各客户端本地目标函数 L-光滑（Appendix B）",
    "假设 2：各客户端本地目标函数 μ-强凸（Appendix B）",
    "假设 3：各客户端随机梯度方差有界 σ_k²（Appendix B）",
    "假设 4：随机梯度期望平方范数一致有界 G²（Appendix B）",
    "假设 5：LoRA 模块更新是基座模型 SGD 梯度的无偏估计（Appendix B）",
    "收敛率继承全客户端参与的 FedAvg 分析框架（Appendix B）",
    "客户端诚实上报 LoRA 模块与本地数据量，服务器按规则聚合（论文未显式声明，流程隐含）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Section 1 Introduction", "supports": "第 3、4 节：论文处理的是 FedIT 独立平均 A、B 导致的聚合噪声这一数学问题，而非某种攻击", "text": "However, FedIT faces two key issues. First, the naive averaging of local LoRA modules in FedIT introduces noise to the global model update. Specifically, FedIT averages local A and B independently, which introduces mathematical errors to the global LoRA."},
    {"section": "Section 3.1 Stacking-based Noise-free Aggregation", "supports": "第 4 节核心思想与第 8 节通信开销：通过堆叠实现无噪声聚合且不传整个模型参数", "text": "This mechanism demonstrates that, in the context of federated fine-tuning, we can achieve a noise-free aggregation of local updates by simply stacking the local LoRA modules. This process also avoids transmitting the full model parameters, thus reducing communication costs."},
    {"section": "Section 3.2 FLORA: Stacking-based Federated Fine-tuning", "supports": "第 5 节数据需求：缩放因子由各客户端本地数据量相对全局数据量决定", "text": "where pk represents the scaling factor for each local update, determined by the relative size of the local data to the global data:"},
    {"section": "Section 3.2 FLORA: Stacking-based Federated Fine-tuning", "supports": "第 6 节干预动作与第 10 节干预接口：缩放因子只能作用在 A_k 或 B_k 的一侧", "text": "Note that the scaling factor pk should be only applied to one of Ak and Bk to avoid squaring the factor in the final model update BA."},
    {"section": "Section 3.2 FLORA: Stacking-based Federated Fine-tuning", "supports": "第 9 节关键假设：对本地秩无约束，但必须共享同一预训练模型的维度", "text": "This approach imposes no constraints on the ranks of each local LoRA module as long as each client fine-tunes the same pre-trained model, i.e., they share the same dimension m and n."},
    {"section": "Section 4.1 Experiment Setup", "supports": "第 7 节实验设置：10 个客户端、非独立同分布、MMLU 与 MT-bench 指标", "text": "We evaluate the federated fine-tuned models on MMLU [7] for the QA task and MT-bench [29] for the chat assistant task, respectively. We sample 10 clients uniformly at random following the non-IID setting in FedIT [25]."},
    {"section": "Section 5 The Privacy Preservation of FLORA", "supports": "第 2 节威胁模型与第 3 节攻击面：论文唯一提到的攻击者是可从下发全局 LoRA 推断他人模块的恶意客户端", "text": "The requirement of FLORA to stack the LoRA modules uploaded by all clients introduces a potential privacy concern, as malicious clients might infer the LoRA matrices of other clients through the global LoRA modules sent from the server."},
    {"section": "Section 5 The Privacy Preservation of FLORA", "supports": "第 6 节隐私缓解动作与第 9 节对该缓解未经验证的分析", "text": "To address this issue, we split all the local LoRA modules into sub-modules with rank=1 and then stack the sub-modules together in random order. This approach prevents malicious clients from recovering the local LoRA modules from other clients."},
    {"section": "Appendix B Convergence Analysis (Assumption 5)", "supports": "第 9 节列出的收敛性假设：LoRA 更新被假定为 SGD 梯度的无偏估计", "text": "The updates applied to LoRA modules by each client serve as unbiased estimators of the gradient that would be directly computed on the base model through SGD"},
    {"section": "Appendix C Limitation", "supports": "第 8 节通信开销与第 9 节论文自述局限", "text": "Our approach has the limitation that the server sends the stacked LoRA modules to the client, thereby increasing the communication costs. We discussed this limitation both theoretically and experimentally in Section 3 and Section 4, respectively."}
  ]
}
```
