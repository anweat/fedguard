# shen2024seal：SEAL（Safety-Enhanced Aligned LLM Fine-tuning via Bilevel Data Selection，双层数据选择的安全增强对齐微调）

## 1. 方法一句话

SEAL 输入一个已安全对齐的 LLM（记参数 θ）、一份安全/对齐参考数据集 D_safe（含 M 条样本 z_i^safe）和一份混合了安全与潜在有害样本的微调数据集 D（含 N 条样本 z_i=(x_i,y_i)），通过求解一个双层优化（bilevel optimization, BLO）问题学出一个逐样本的数据选择器 σ(ω)（ω∈R^N，σ 取 softmax，Section 3.1）；输出是按 σ_i(ω_K) 排序后保留的前 p% 样本构成的筛选后数据集 D_top（Section 3.3 的 S3），最终在 D_top 上做常规微调（S4）。它不输出"这条样本有害/无害"的硬判定，而是输出一个连续的样本权重/排名，再按比例截断。

## 2. 运行位置

论文是**集中式（centralized）**设定，没有客户端概念。论文明确其适用场景是"模型所有者提供对用户数据的微调服务"或"微调数据集太大、无法人工标注，而模型所有者可以拿到一个对齐/安全数据集"（Section 1 "Use cases of SEAL"、Section 3.1）。

- S1（初始对齐）、S2（选择器训练）、S3（数据选择）都在**训练之外**的离线阶段完成，由持有 D_safe 与 D 的一方（模型/服务方）执行。
- S4（安全微调）才是常规训练过程本身。
- 分析：若把 SEAL 映射到联邦流程，S2 与 S3 最自然地对应"服务器下发前"的服务器/数据方离线预处理——选择器训练要同时访问 D_safe 和 D（两者都在服务器侧），产出 D_top 之后才谈得上把数据分发给客户端；S4 对应普通的客户端训练循环，此时 SEAL 不再执行任何额外算子。因此我把 stage 记为 `outside_training`。
- 额外往返：不需要。论文没有涉及客户端—服务器通信；论文反而强调"前三步可以是一次性工作：一旦数据被选好，就可以用于之后所有在该数据集上的微调"（Section 3.3："the first three steps can be a one-time effort"）。

## 3. 算子流水线

记 ℓ(θ;z) 为长度归一化的负对数似然（length-normalized negative log-likelihood）：ℓ(θ;z) := −(1/d_y)·Σ_{j=1}^{d_y} log P_θ(y_j | x, y_{<j})，其中 d_y 是目标响应 y 的长度（Section 3.1）。注意论文中 j 同时被用作"响应 token 下标"和"被抽到的微调样本下标"，实现时要区分。

**步骤 1：初始对齐（S1）**
- 输入：基座/预训练 LLM，以及（在 PYTHIA-2.8B 情形下）偏好数据。
- 计算：论文只写"obtain a safety-aligned LLM"（Section 3.3 S1）。对 LLAMA-3-8B-INSTRUCT、MERLINITE-7B、LLAMA2-7B-CHAT-HF 论文直接使用现成的 instruct/chat 对齐模型（Section 4.1）。对 PYTHIA-2.8B，先在 ANTHROPIC HH 训练集的 112k 子集上做 SFT（对偏好响应训练 2 epoch，lr 1×10⁻⁵，batch 64），再以该 SFT 模型为初始做 DPO 1 epoch（β=0.1，lr 与 batch 相同）（Appendix B.1）。
- 输出：安全对齐模型参数 θ₁。
- 出处：Section 3.3 S1；Section 4.1；Appendix B.1。

**步骤 2：初始化数据选择器 σ(ω)**
- 输入：微调数据集规模 N。
- 计算：初始化 ω∈R^N，定义 σ(ω)=(σ₁(ω),…,σ_N(ω)) 为数据选择器函数，取 softmax：σ_i(ω)=exp(ω_i)/Σ_{l=1}^{N} exp(ω_l)（Section 3.1，Appendix A.1 确认实验中用 softmax）。ω 的具体初始化方式论文未说明。
- 输出：ω₁ 与逐样本权重 σ(ω)。
- 出处：Section 3.1；Algorithm 1 第 1 行；Appendix A.1。

**步骤 3：初始化辅助模型 ˆθ**
- 输入：θ₁。
- 计算：ˆθ₁ = θ₁（仅 Algorithm 1 需要；Algorithm 2 无此变量）。
- 输出：辅助模型参数 ˆθ₁，与 θ 同尺寸。
- 出处：Algorithm 1 第 1 行。

**步骤 4：惩罚松弛（构造单层目标）**
- 输入：上层安全损失 ℓ(θ;z_i^safe)、下层加权微调损失 σ_i(ω)ℓ(θ;z_i)、惩罚系数 γ。
- 计算：先定义下层次优性的惩罚项 p(ω,θ) := (1/N)·(Σ_{i=1}^{N} σ_i(ω)ℓ(θ;z_i) − min_{θ'} Σ_{i=1}^{N} σ_i(ω)ℓ(θ';z_i))（公式 (2)）；再以系数 γ 把它加到上层损失上，得到单层惩罚问题：min_{ω,θ} (1−γ)·(1/M)Σ_{i=1}^{M} ℓ(θ;z_i^safe) + γ·p(ω,θ)（公式 (3)）。论文指出 (3) 的任何局部/全局解在适当条件下局部/全局解原问题 (1)（引用 Shen & Chen, 2023）。
- 输出：被优化的单层目标（后续所有更新都由它导出）。
- 出处：公式 (2)、公式 (3)；Section 3.2。

**步骤 5：每个迭代 k 采样一对数据**
- 输入：D_safe 与 D。
- 计算：从 D_safe 采样 z_i^safe，从 D 采样 z_j；同一次采样的这一对样本在该迭代的三处更新中复用。Algorithm 1/2 第 3 行按"单样本"书写，而 Appendix A.1 给出 batch size 为 64；论文未说明这 64 条中两个数据集各占多少、也未说明 ω 的梯度是否在 batch 上累积。
- 输出：一个安全样本与一个微调样本。
- 出处：Algorithm 1 第 3 行、Algorithm 2 第 3 行；Appendix A.1。

**步骤 6：逐样本长度归一化负对数似然（可复用算子）**
- 输入：样本 z=(x,y)，响应长度 d_y，当前模型参数。
- 计算：ℓ(θ;z) = −(1/d_y)·Σ_{j=1}^{d_y} log P_θ(y_j | x, y_{<j})（Section 3.1）。
- 输出：标量损失 ℓ。该算子被步骤 7、8、9、10 反复调用。
- 出处：Section 3.1。

**步骤 7：模型参数 θ 的惩罚混合 SGD 步**
- 输入：θ_k、ℓ(θ_k;z_i^safe) 的梯度、σ_j(ω_k)ℓ(θ_k;z_j) 的梯度、γ_k、步长 β_k。
- 计算：θ_{k+1} = θ_k − β_k[(1−γ_k)∇ℓ(θ_k;z_i^safe) + γ_k·σ_j(ω_k)·∇ℓ(θ_k;z_j)]，即安全损失与"被选择器加权的微调损失"的凸组合梯度下降。γ_k 按 epoch 从小的值开始递增（早期先用安全损失 warm-start）。
- 输出：θ_{k+1}。
- 出处：公式 (4)；Algorithm 1 第 4 行、Algorithm 2 第 4 行；γ 调度见 Section 3.2。

**步骤 8：辅助模型 ˆθ 的 SGD 步（仅 Algorithm 1）**
- 输入：ˆθ_k、σ(ω_k)、∇ℓ(ˆθ_k;z_j)。
- 计算：ˆθ_{k+1} = ˆθ_k − β_k·σ_i(ω_k)·∇ℓ(ˆθ_k;z_j)（公式 (6)）。注意论文该行把权重写成 σ_i(ω_k)（安全样本的下标 i），而损失里的样本是 z_j，两个下标在原文中不一致（见第 9 节）。
- 输出：ˆθ_{k+1}，作为 θ*(ω_k) 的近似。
- 出处：公式 (6)；Algorithm 1 第 5 行。

**步骤 9：选择器 ω 的 rank 更新（含损失 gap，Algorithm 1）**
- 输入：ℓ(θ_k;z_j) 与 ℓ(ˆθ_k;z_j)、∇σ_j(ω_k)、步长 α_k。
- 计算：ω_{k+1} = ω_k − α_k·[ℓ(θ_k;z_j) − ℓ(ˆθ_k;z_j)]·∇σ_j(ω_k)（公式 (5)）。论文的解释：用损失 gap 去缩放 ∇σ_j(ω_k)，而 ∇σ_j(ω_k) 是第 j 条数据排名的上升方向；gap 为大的正值说明 z_j 与安全数据不一致，于是降低其排名，gap 为负则提高排名。更新被描述为对 σ(ω) 的"坐标级加权下降"。
- 输出：ω_{k+1}。
- 出处：公式 (5)；Algorithm 1 第 6 行；Section 3.2 的解释段落。

**步骤 10：记忆高效变体的 rank 更新（Algorithm 2，论文实验默认使用）**
- 输入：ℓ(θ_k;z_j)、∇σ_j(ω_k)、α_k。
- 计算：在"LLM 足够大、d_θ ≫ N，因此存在 θ* 使 ℓ(θ*;z_i)≈0（公式 (7)）"的假设下，∇_ω min_θ Σσ_i(ω)ℓ(θ;z_i)≈0，于是简化为 ω_{k+1} = ω_k − α_k·ℓ(θ_k;z_j)·∇σ_j(ω_k)（公式 (8)），不再维护 ˆθ。
- 输出：ω_{k+1}。
- 出处：公式 (7)、公式 (8)；Algorithm 2 第 5 行；Section 4.1 说明默认用该变体以省算力。

**步骤 11：全量打分与排序（S3 前半）**
- 输入：训练结束的选择器参数 ω_K；D 中全部 N 条样本。
- 计算：对每条 z_i 计算 σ_i(ω_K)，按分数降序排名。
- 输出：每条样本的分数与排名。
- 出处：Section 3.3 S3（"use the trained data selector σ_i(ω_K) to rank each data z_i"）。

**步骤 12：按比例截断（S3 后半）**
- 输入：排名、选择比例 p%。
- 计算：取 top p% 组成 D_top。论文未说明并列分数如何处理、p%×N 非整数时如何取整。
- 输出：D_top。
- 出处：Section 3.3 S3；取值见 Section 4.2（80%）、Section 4.5（90%）、Table 3（20%）。

**步骤 13：在 D_top 上安全微调（S4）**
- 输入：对齐起始模型 + D_top。
- 计算：常规 SFT。LLAMA 系列与 MERLINITE-7B 用 LoRA（rank 16、α=16、无 dropout，只作用于所有 query/value 投影矩阵；LLAMA-3-8B-INSTRUCT 6.9M 可训练参数、MERLINITE-7B 6.8M、LLAMA2-7B-CHAT-HF 8.4M），其余模型全参数训练（Appendix A.1）；优化器统一 Adam（Appendix A.1）。
- 输出：微调后的模型。
- 出处：Section 3.3 S4；Section 4.1；Appendix A.1。

## 4. 采样与规模控制

- **样本（选择器训练的 minibatch）**：每个迭代从 D_safe 抽一条、从 D 抽一条（Algorithm 1/2 第 3 行按单样本写），Appendix A.1 给出 batch size 64；两个数据集在此 batch 中的配比论文未说明。迭代总步数 K 论文未说明（只给了 epoch 数 2–3 与 batch 64）。
- **样本（输出侧截断）**：按 σ_i(ω_K) 排序取 top p%。默认 p=80%（Section 4.2："all data selection methods select 80% of the fine-tuning data"）；Section 4.5 用 90%；Table 3 有 20% 的设置；Section 4.3 与 Figure 5 报告 20%≤p≤80% 区间；Section 3.3 S3 只写 "top p%"，未给默认值。
- **参考数据（probes）**：D_safe 全量参与上层损失与选择器训练。Section 4.2 用 SLIMORCA 的留存子集 112k 条作 D_safe；Section 4.5 用 ALPACA-CLEANED 的 49.9k 子集作 D_safe；Appendix B.1 中 PYTHIA-2.8B 的初始对齐用 ANTHROPIC HH 训练集的 112k 子集。微调数据集侧：Section 4.2 的 REDORCA = 90k 条 SLIMORCA 英文指令数据 + 22k 条 ANTHROPIC RED-TEAMING 潜在不安全数据（Section 4.1）；Section 4.5 的良性微调集是 OPENORCA 的 49.9k 子集。
- **层/参数**：没有层或参数坐标抽样。LLAMA 系列与 MERLINITE-7B 用 LoRA rank 16（只训练 query/value 投影），可视为对 θ 的降维；PYTHIA-2.8B 及其他模型全参数训练（Appendix A.1）。
- **轮次**：选择器训练 2–3 epoch（Appendix A.1、B.1），γ 每 epoch 递增；最终微调 2–3 epoch。
- **客户端**：论文未使用（集中式方法，没有客户端划分）。

## 5. 超参数

| 名称 | 含义 | 取值 | 出处 |
|---|---|---|---|
| σ(ω) | 数据选择器函数形式 | softmax | Section 3.1；Appendix A.1 |
| N（ω 的维数） | 微调数据集样本数 | 112k（REDORCA）、49.9k（良性实验） | Section 4.1、4.2、4.5 |
| M（D_safe 规模） | 安全参考数据量 | 112k（SLIMORCA 留存子集）、49.9k（ALPACA-CLEANED 子集） | Section 4.2、4.5 |
| α_k（选择器学习率） | ω 的步长 | 5×10⁻³（LLAMA-3-8B-INSTRUCT；Section 4.5 良性实验）；4×10⁻³（MERLINITE-7B、PYTHIA-2.8B） | Appendix A.1、B.1 |
| β_k（模型学习率） | θ（以及 ˆθ）的步长 | 1×10⁻⁵（所有设置） | Appendix A.1、B.1 |
| γ_k（惩罚强度） | 下层微调损失在上层目标中的权重 | 从 0 每 epoch 增加：LLAMA-3 为 3×10⁻²、MERLINITE / PYTHIA / 良性实验为 2×10⁻²；Algorithm 1 第 1 行约束 γ_k∈(0,1) | Appendix A.1、B.1；Section 3.2 |
| 选择器训练 batch size | 每次采样的批量 | 64 | Appendix A.1 |
| 选择器训练 epoch 数 | — | LLAMA-3：3；MERLINITE：2；PYTHIA：2；良性实验：3 | Appendix A.1、B.1 |
| 数据选择比例 p | top p% | 80%（默认对比设置）；90%（良性实验）；20%（Table 3）；评测范围 20%–80% | Section 4.2、4.3、4.5；Table 3 |
| 微调学习率 / batch / epoch | S4 | lr 1×10⁻⁵、batch 64；LLAMA-3 与良性实验 2 epoch，MERLINITE 与 PYTHIA 3 epoch | Appendix A.1、B.1 |
| LoRA 配置 | S4 参数化 | rank 16、α=16、无 dropout，query/value 投影 | Appendix A.1 |
| 优化器 | S2/S4 | Adam（"We use Adam optimizer in all tests"，论文未逐项确认选择器也用 Adam） | Appendix A.1 |
| DPO 超参 | PYTHIA 初始对齐 | β=0.1，1 epoch | Appendix B.1 |
| SafeInstr 混入比例 | SEAL+SafeInstr 变体 | 推荐量为微调集的 2%–3%，实验中加 3% | Section 4.1、4.2 |
| K（选择器训练总迭代数） | — | 论文未说明 | — |

## 6. 判定与动作

- **没有阈值判定，也没有聚类规则**。判定形式是排序加比例截断：用 σ_i(ω_K) 给每条微调样本打分并排名，保留 top p%（Section 3.3 S3）。因为 softmax 的输出恒为正、不会取到 0，"筛选"必须靠排名而不是靠阈值，论文也没有给任何阈值。
- **训练期的软动作**：在 S2 内，σ_j(ω_k) 作为权重乘在下层微调损失上（公式 (4) 的第二项），即对被判定为较安全的样本加大权重；Algorithm 1 中 ˆθ 的更新也带 σ 权重（公式 (6)）。
- **推理/落地期的硬动作**：S4 只在 D_top 上微调，未进入 D_top 的样本被直接丢弃（不参与训练，也未被改写、加噪或裁剪）。论文未对被丢弃样本做任何处理。
- **无裁剪、无加噪、无聚合加权**：论文没有对梯度或更新做裁剪或加噪，也没有联邦聚合公式。
- **跨轮累积**：ω 在一次 S2 内的 K 个迭代中持续累积更新；选择器一旦训好就固定下来，论文强调 S1–S3 是一次性投入、之后所有在该数据集上的微调都可复用（Section 3.3），并且可迁移到别的（可更大）模型上使用（Section 4.4、Table 3）。
- **可选的额外动作（SEAL+SafeInstr 变体，不是 SEAL 本身）**：把 3% 的安全指令数据混进 D_top 再微调，可进一步提升安全性（Section 4.2）。

## 7. 需要的外部资源

- 一个安全对齐的 LLM 作为 θ₁：LLAMA-3-8B-INSTRUCT、MERLINITE-7B、LLAMA2-7B-CHAT-HF 直接使用现成的 instruct/chat 模型；PYTHIA-2.8B 需要先用 ANTHROPIC HH 的 112k 子集做 SFT+DPO 对齐（Section 4.1；Appendix B.1）。
- 安全参考数据集 D_safe：SLIMORCA 留存子集 112k 条（Section 4.2），或 ALPACA-CLEANED 子集 49.9k 条（Section 4.5）。论文的适用前提就是模型所有者能拿到这样的对齐/安全数据（Section 3.1、Section 1 的 use cases）。
- 待微调数据集 D：REDORCA（90k SLIMORCA + 22k RED-TEAMING，共 112k 条，Section 4.1）或 OPENORCA 的 49.9k 子集（Section 4.5）。
- 选择器参数 ω∈R^N（N 等于微调集大小，约 112k 或 49.9k 维）。
- Algorithm 1 额外需要一份与 LLM 同尺寸的辅助模型参数 ˆθ（显存占用按整模型翻倍）；Algorithm 2 不需要。
- 可选的更小"代理模型"用于 S2：PHI-3-MINI-128K-INSTRUCT（3.8B 参数）或 PYTHIA-2.8B，训出的选择器可直接用于微调更大的 MERLINITE-7B（Section 4.4、Table 3）。
- 评测侧资源（非方法本身所需）：GPT-4 作为裁判、标准 SFT 输出模型作为参考模型来计算 win rate（Section 4.1、Appendix A.2）。

## 8. 计算与存储开销

论文报告的开销（Table 3，标题注明"on one NVIDIA A6000 in the group of four"）：
- 数据选择器训练：用 PYTHIA-2.8B 时 28.3 GB / 14 小时；用 PHI-3 时 34.1 GB / 20 小时。
- 后续微调：选取 20% 时 27.8 GB / 3 小时；选取 80% 时 27.9 GB / 13 小时。
- 对照：随机选 20% 为 27.8 GB / 3 小时，随机选 80% 为 27.9 GB / 13 小时，不选数据为 27.9 GB / 16 小时。
- 论文的结论是"选择器训练会增加总计算量与显存，可能超过微调本身"，但可一次性完成；用更小的选择比例、或用更小的模型做选择器训练可以摊薄成本（选 20% + PYTHIA 总时长 17 小时，接近不选数据的 16 小时基线）（Section 4.4）。

按流水线的开销来源：
- 分析：主要开销在 S2。Algorithm 2 每个迭代至少要对 LLM 做一次前向+反向（θ 的更新）并额外求 ℓ(θ_k;z_j)；Algorithm 1 还要再维护和更新一份完整的 ˆθ，相当于每步两次模型级前向/反向加一份模型显存。开销随 LLM 参数量 d_θ、batch size 与迭代步数 K 线性增长。
- 分析：ω 的更新本身是 O(N) 向量运算，存储也是 O(N)，相对模型可忽略；但如果按公式 (5)/(8) 对 softmax 求 ∇σ_j(ω_k) 并更新全部 N 个坐标，则每个迭代对选择器的计算与内存访问随 N 线性增长。
- 分析：S3 需要对全部 N 条样本各算一次 σ_i(ω_K)，随 N 线性增长（只是选择器的一次前向，成本远低于 S2）。
- 分析：S4 的成本只随 |D_top| = p·N 增长，这也是 p 越小总时长越短的原因（Table 3 中 3 小时 vs 13 小时）。

## 9. 实现时容易错的地方

论文明确强调或暴露的细节：
1. **θ 是联合训练的，不是冻结的**。S2 里 LLM 参数 θ 也在被更新（公式 (4)），不是"固定模型给数据打分"。把它实现成冻结模型打分就偏离了论文。
2. **ω 的更新用的是更新前的 θ_k 与 ˆθ_k**。Algorithm 1 的行序是先更新 θ（第 4 行）、再更新 ˆθ（第 5 行）、最后用 ℓ(θ_k;z_j)−ℓ(ˆθ_k;z_j) 更新 ω（第 6 行），公式里写的是 θ_k、ˆθ_k。实现时必须在更新参数之前保存这两个损失，或先算损失再更新。
3. **同一对样本在三条更新里复用**：采样只在第 3 行做一次，第 4、5、6 行用的是同一个 z_i^safe、z_j。
4. **Algorithm 1 第 5 行的下标不一致**：原文写的是 ˆθ_{k+1} = ˆθ_k − β_k σ_i(ω_k)∇ℓ(ˆθ_k; z_j)，权重下标是安全样本的 i，而损失里是微调样本 z_j；按上下文应为 σ_j。实现时必须自己定夺。
5. **γ 的边界与调度**：Algorithm 1 第 1 行要求 γ_k∈(0,1)，Appendix A.1 却写"increase from 0"，即第一个 epoch γ=0，这两者字面冲突；论文只给了每 epoch 的增量（3×10⁻² 或 2×10⁻²），没写上限、也没写是"每 epoch 覆盖式赋值"还是"累加"。
6. **Algorithm 2 的适用前提**：公式 (7) 的推导假设 d_θ≫N 且存在 θ* 使所有 ℓ(θ*;z_i)≈0；论文默认实验在 LoRA（6.8M–8.4M 可训练参数）下仍使用 Algorithm 2（Section 4.1），这一点与假设并不严格相符，实现时要清楚这是在用近似变体。
7. **σ 是 softmax，意味着永不精确为零**，不能靠"σ_i 小于某阈值就丢弃"来做筛选；论文的做法始终是排名 + top p%。
8. **选择器与微调模型可以不同**：Table 3 用 PYTHIA-2.8B / PHI-3-MINI 训选择器、再去微调 MERLINITE-7B。选择器的身份绑定在数据集（样本顺序/样本 ID）而非模型上，缓存时必须按数据集版本做键。

论文没说清、实现必须自行决定的地方：
1. ω 的初始化方式、是否对 ω 做归一化或正则、是否重新中心化（softmax 对 ω 加常数不变，ω 本身不可辨识）。
2. ∇σ_j(ω_k) 的语义：论文称该更新是"坐标级"的，但 softmax 下 ∂σ_j/∂ω_i = σ_j(δ_{ij}−σ_i) 是稠密向量；是更新全部 N 个坐标还是只更新第 j 个坐标，论文未说明。
3. 步数：每 epoch 有多少个迭代、总迭代数 K 是多少（只给了 epoch 数和 batch size 64）。
4. batch size 64 与算法中"单样本对"的对应关系：64 条里 D_safe 和 D 各占多少、ω 的梯度是否在 batch 内平均/累积。
5. ω 是否也用 Adam、是否有独立的 warmup 或学习率调度（论文只说"all tests 用 Adam"并分别给了两个学习率）。
6. 公式 (3) 中 min_{θ'} 项的近似精度：用 ˆθ 近似到什么程度、ˆθ 每步更新几次、是否需要周期性重对齐，都没有说明。
7. 损失计算细节：是否只在响应 token 上算损失、prompt 模板、最大序列长度、是否 packing、长度归一化时分母是否含特殊 token，论文未说明。
8. 排序并列、p%×N 非整数时的取整规则，以及 p 的默认值（Section 3.3 只写 top p%）。
9. ℓ 的记号里 j 既是响应 token 下标又是样本下标，公式 (4)(5)(6) 的 z_j 与 ℓ 内部的 j 需要实现者自行消歧。
10. 数值稳定性：损失 gap 可能很大且可为负，论文没有对 gap 做裁剪或归一化；α_k 固定（约 4–5×10⁻³），在 N 很大、梯度稠密时是否发散论文未讨论。
11. 论文内部的数字不一致：摘要写 MERLINITE-7B 上相对随机选择提升 9.7%，Section 4.2 写"around 9.8%"，实现复现时不要把这些数字当精确目标。

## 10. 原文依据

1. 支撑步骤 2（选择器形式与 softmax）：
> "σ(ω) = (σ1(ω), ...., σi(ω), ...., σN(ω)) is the data selector function. For example, we can use the softmax function: σi(ω) = exp(ωi) PN i=1 exp(ωi)."

2. 支撑步骤 1、3（初始对齐与辅助模型初始化）：
> "Warm-start θ1 by setting it as a safety-aligned model parameter. Initialize a data selector parameter ω. Initialize the auxiliary model parameter ˆθ1 = θ1. Schedule the hyper-parameters: step sizes αk, βk and penalty strength γk ∈ (0, 1)."

3. 支撑步骤 5、7（每步采样与 θ 的惩罚混合 SGD）：
> "Sample data zi safe from safe dataset Dsafe and zj from fine-tuning dataset D. Update model parameter θk+1 = θk − βk (1 − γk)∇ℓ(θk; zi safe) + γkσj(ωk)∇ℓ(θk; zj)"

4. 支撑步骤 9（选择器 rank 更新公式）：
> "Update data selector ωk+1 = ωk − αk ℓ(θk; zj) − ℓ(ˆθk; zj) ∇σj(ωk)"

5. 支撑步骤 9（gap 缩放与上升方向的解释）：
> "The update essentially uses the loss values gap ℓ(θk; zj) − ℓ(ˆθk; zj) to weigh ∇σj(ωk) which is the ascent direction of the rank for j-th data in D."

6. 支撑步骤 9、11（gap 符号决定排名升降）：
> "If a data zj admits a large positive gap ℓ(θk; zj) − ℓ(ˆθk; zj), it is fitted worse with θk than ˆθk. Thus it is likely that zj does not align well with the safe data Dsafe."

7. 支撑步骤 10（记忆高效变体的推导与公式 (8)）：
> "yielding ∇ω minθ PN i=1 σi(ω)ℓ(θ; zi) ≈0. Plugging this into (5), ω can be updated with ωk+1 = ωk − αkℓ(θk; zj)∇σj(ωk)."

8. 支撑步骤 11、12（打分排序与 top p% 截断）：
> "S3) Data selection: use the trained data selector σi(ωK) to rank each data zi in the fine-tuning dataset D. Select top p% of the fine-tuning data in D to form Dtop."

```json
{
  "key": "shen2024seal",
  "method": "SEAL: bilevel data selection that learns a softmax sample ranker sigma(omega) on top of a safety-aligned LLM, ranks the fine-tuning samples, keeps the top p% and fine-tunes on the selected subset",
  "stages": ["outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "initial_alignment: obtain a safety-aligned LLM theta_1 (S1)",
      "operator": "sft_then_dpo_alignment",
      "input": "base/pre-trained LLM; preference or alignment data (for PYTHIA-2.8B: 112k subset of ANTHROPIC HH)",
      "output": "safety-aligned model parameters theta_1",
      "params": {"sft_epochs": 2, "dpo_epochs": 1, "dpo_beta": 0.1, "lr": 1e-5, "batch_size": 64, "note": "only needed for PYTHIA-2.8B; LLAMA-3-8B-INSTRUCT / MERLINITE-7B / LLAMA2-7B-CHAT-HF are used off the shelf"},
      "source": "Section 3.3 S1; Section 4.1; Appendix B.1"
    },
    {
      "step": "selector_initialization: omega in R^N with softmax weights",
      "operator": "softmax_selector_init",
      "input": "number of fine-tuning samples N",
      "output": "omega in R^N and per-sample weights sigma_i(omega)=exp(omega_i)/sum_l exp(omega_l)",
      "params": {"selector": "softmax", "init_of_omega": "论文未说明"},
      "source": "Section 3.1; Algorithm 1 line 1; Appendix A.1"
    },
    {
      "step": "auxiliary_model_initialization: clone theta into hat-theta (Algorithm 1 only)",
      "operator": "clone_model_parameters",
      "input": "theta_1",
      "output": "hat-theta_1 = theta_1",
      "params": {},
      "source": "Algorithm 1 line 1"
    },
    {
      "step": "penalty relaxation of the bilevel problem into a single-level objective",
      "operator": "penalty_bilevel_relaxation",
      "input": "upper-level safety losses l(theta; z_i^safe), lower-level weighted losses sigma_i(omega)*l(theta; z_i), penalty constant gamma",
      "output": "min_{omega,theta} (1-gamma)*(1/M)*sum_i l(theta;z_i^safe) + gamma*p(omega,theta) with p(omega,theta)=(1/N)*(sum_i sigma_i(omega)l(theta;z_i) - min_{theta'} sum_i sigma_i(omega)l(theta';z_i))",
      "params": {"gamma": "(0,1), scheduled to increase per epoch"},
      "source": "Eq. (2); Eq. (3); Section 3.2"
    },
    {
      "step": "paired sampling of one safe sample and one fine-tuning sample per iteration",
      "operator": "paired_sample_draw",
      "input": "safe dataset D_safe and fine-tuning dataset D",
      "output": "z_i^safe and z_j (reused by all updates of the iteration)",
      "params": {"batch_size": 64},
      "source": "Algorithm 1 line 3; Algorithm 2 line 3; Appendix A.1"
    },
    {
      "step": "per-sample length-normalized negative log-likelihood",
      "operator": "length_normalized_nll",
      "input": "sample z=(x,y) with response length d_y; model parameters",
      "output": "scalar l(theta;z) = -(1/d_y)*sum_{j=1}^{d_y} log P_theta(y_j | x, y_<j)",
      "params": {},
      "source": "Section 3.1"
    },
    {
      "step": "penalty-mixed SGD step on the LLM parameters theta",
      "operator": "penalty_mixed_sgd_step",
      "input": "theta_k; grad of l(theta_k;z_i^safe); grad of sigma_j(omega_k)*l(theta_k;z_j); gamma_k; beta_k",
      "output": "theta_{k+1}",
      "params": {"beta_k": 1e-5},
      "source": "Eq. (4); Algorithm 1 line 4; Algorithm 2 line 4"
    },
    {
      "step": "SGD step on the auxiliary model hat-theta (Algorithm 1 only)",
      "operator": "auxiliary_model_sgd_step",
      "input": "hat-theta_k; sigma(omega_k); grad l(hat-theta_k; z_j)",
      "output": "hat-theta_{k+1} (approximation of theta*(omega_k))",
      "params": {},
      "source": "Eq. (6); Algorithm 1 line 5"
    },
    {
      "step": "loss-gap weighted rank update of the selector omega (Algorithm 1)",
      "operator": "loss_gap_rank_update",
      "input": "l(theta_k;z_j), l(hat-theta_k;z_j), grad sigma_j(omega_k), alpha_k",
      "output": "omega_{k+1} = omega_k - alpha_k*(l(theta_k;z_j)-l(hat-theta_k;z_j))*grad sigma_j(omega_k)",
      "params": {"alpha_k": "5e-3 (LLAMA-3 / benign setting), 4e-3 (MERLINITE, PYTHIA)"},
      "source": "Eq. (5); Algorithm 1 line 6; Section 3.2"
    },
    {
      "step": "memory-efficient rank update without the auxiliary model (Algorithm 2, used in all default experiments)",
      "operator": "nll_rank_update",
      "input": "l(theta_k;z_j), grad sigma_j(omega_k), alpha_k",
      "output": "omega_{k+1} = omega_k - alpha_k*l(theta_k;z_j)*grad sigma_j(omega_k)",
      "params": {"assumption": "exists theta* with l(theta*;z_i) ~ 0 for all i, justified by d_theta >> N"},
      "source": "Eq. (7); Eq. (8); Algorithm 2 line 5; Section 4.1"
    },
    {
      "step": "score and rank all N fine-tuning samples with the trained selector",
      "operator": "per_sample_selector_score",
      "input": "omega_K; all N samples of D",
      "output": "sigma_i(omega_K) scores and their descending ranks",
      "params": {},
      "source": "Section 3.3 S3"
    },
    {
      "step": "truncate to the top p% to form D_top",
      "operator": "top_percent_select",
      "input": "ranks of all N samples; selection percent p",
      "output": "D_top with p*N samples",
      "params": {"p": "0.8 (default), 0.9 (benign setting), 0.2 (Table 3); tested range 0.2-0.8"},
      "source": "Section 3.3 S3; Section 4.2; Section 4.3; Section 4.5; Table 3"
    },
    {
      "step": "safe fine-tuning on D_top (S4)",
      "operator": "supervised_finetune",
      "input": "aligned model theta_1; D_top",
      "output": "fine-tuned LLM",
      "params": {"lora_rank": 16, "lora_alpha": 16, "lora_dropout": 0, "lora_targets": "query and value projections", "lr": 1e-5, "batch_size": 64, "epochs": "2 (LLAMA-3, benign) / 3 (MERLINITE, PYTHIA)", "optimizer": "Adam"},
      "source": "Section 3.3 S4; Section 4.1; Appendix A.1"
    }
  ],
  "sampling": [
    {"what": "samples", "how": "每个迭代从 D_safe 抽一条、从 D 抽一条（算法按单样本写，Appendix 给 batch size 64；两个数据集的配比论文未说明）", "size": "batch_size = 64 (Appendix A.1)"},
    {"what": "samples", "how": "按 sigma_i(omega_K) 排名后取 top p% 组成 D_top，其余直接丢弃", "size": "p = 80% (Section 4.2)，90% (Section 4.5)，20% (Table 3)，评测范围 20%-80% (Section 4.3)"},
    {"what": "probes", "how": "安全参考数据集 D_safe 全量参与上层安全损失与选择器训练", "size": "112k (SLIMORCA withheld subset, Section 4.2)；49.9k (ALPACA-CLEANED subset, Section 4.5)；PYTHIA 对齐用 112k (Appendix B.1)"},
    {"what": "layers", "how": "LoRA rank 16、alpha 16、无 dropout，只作用于 query/value 投影矩阵，用于降低 theta 的维数", "size": "6.9M trainable params (LLAMA-3-8B-INSTRUCT), 6.8M (MERLINITE-7B), 8.4M (LLAMA2-7B-CHAT-HF) (Appendix A.1)"},
    {"what": "rounds", "how": "选择器训练 epoch 数与 gamma 的每 epoch 递增", "size": "2-3 epochs；gamma 每 epoch +3e-2 或 +2e-2 (Appendix A.1, B.1)"},
    {"what": "clients", "how": "论文未使用（集中式方法，没有客户端划分）", "size": ""}
  ],
  "resources": [
    "一个安全对齐的 LLM 作为 theta_1：LLAMA-3-8B-INSTRUCT、MERLINITE-7B、LLAMA2-7B-CHAT-HF 直接取现成对齐模型（Section 4.1）",
    "PYTHIA-2.8B 需要先做初始对齐：在 ANTHROPIC HH 的 112k 子集上 SFT 2 epoch + DPO 1 epoch（Appendix B.1）",
    "安全参考数据集 D_safe：SLIMORCA 留存子集 112k 条（Section 4.2）或 ALPACA-CLEANED 子集 49.9k 条（Section 4.5）",
    "待微调数据集 D：REDORCA 112k 条 = 90k SLIMORCA + 22k ANTHROPIC RED-TEAMING（Section 4.1），或 OPENORCA 的 49.9k 子集（Section 4.5）",
    "选择器参数 omega in R^N，N = |D|（约 112k 或 49.9k 维）",
    "Algorithm 1 额外需要一份与 LLM 同尺寸的辅助模型参数 hat-theta（显存翻倍）；Algorithm 2 不需要",
    "可选的小代理模型用于选择器训练：PHI-3-MINI-128K-INSTRUCT (3.8B) 或 PYTHIA-2.8B，训出的选择器可迁移到 MERLINITE-7B（Section 4.4, Table 3）",
    "评测侧（非方法本身）：GPT-4 作为裁判，标准 SFT 输出模型作为参考模型计算 win rate（Section 4.1, Appendix A.2）"
  ],
  "actions": ["filter_samples", "reweight"],
  "dominant_cost": "S2 选择器训练：每个迭代至少一次 LLM 前向+反向，Algorithm 1 还要再维护并更新一份完整 hat-theta（第二份模型显存）；Table 3 报告选择器训练 28.3 GB / 14 小时（PYTHIA-2.8B）与 34.1 GB / 20 小时（PHI-3），高于微调的 27.8-27.9 GB / 3-13 小时；omega 的存储与更新随 N 线性增长，S3 的打分随 N 线性增长，S4 只随 p*N 增长。",
  "underspecified": [
    "omega 的初始化方式、是否需要归一化/正则（softmax 对 omega 的常数平移不变，omega 不可辨识）",
    "grad sigma_j(omega_k) 的语义：是更新 softmax 的稠密 N 维梯度，还是只更新第 j 个坐标；论文只说 coordinate-wise weighted descent",
    "总迭代数 K 与每 epoch 的迭代数（只给了 epoch 数与 batch size 64）",
    "batch size 64 与算法中单样本对的对应关系：D_safe 与 D 在 batch 中的配比、omega 梯度是否在 batch 上累积",
    "omega 是否也用 Adam、是否另有学习率调度（论文只分别给出两个学习率）",
    "公式 (3) 里 min_{theta'} 项用 hat-theta 近似的精度、hat-theta 的更新频率与重对齐策略",
    "损失计算细节：是否只对响应 token 计损失、prompt 模板、最大序列长度、是否 packing、长度归一化分母的构成",
    "排序并列与 p%*N 非整数时的取整规则；Section 3.3 只写 top p%",
    "论文中 j 同时作为响应 token 下标与样本下标，z_j 与 l 内部的 j 需要实现者消歧",
    "Algorithm 1 第 5 行权重写成 sigma_i(omega_k) 而损失用 z_j，下标不一致",
    "gamma 从 0 开始与 Algorithm 1 第 1 行的 gamma_k in (0,1) 字面冲突；gamma 的上限与是累加还是每 epoch 覆盖赋值未说明",
    "损失 gap 未做裁剪或归一化，alpha_k 固定；gap 很大时的数值稳定性未讨论",
    "摘要写 MERLINITE-7B 提升 9.7%，Section 4.2 写 around 9.8%，论文内部数字不一致"
  ],
  "quotes": [
    {"supports": "步骤 2：选择器定义与 softmax 形式", "text": "σ(ω) = (σ1(ω), ...., σi(ω), ...., σN(ω)) is the data selector function. For example, we can use the softmax function: σi(ω) = exp(ωi) PN i=1 exp(ωi)."},
    {"supports": "步骤 1 与步骤 3：初始对齐模型与辅助模型、超参调度", "text": "Warm-start θ1 by setting it as a safety-aligned model parameter. Initialize a data selector parameter ω. Initialize the auxiliary model parameter ˆθ1 = θ1. Schedule the hyper-parameters: step sizes αk, βk and penalty strength γk ∈ (0, 1)."},
    {"supports": "步骤 5 与步骤 7：每步配对采样与 theta 的惩罚混合 SGD", "text": "Sample data zi safe from safe dataset Dsafe and zj from fine-tuning dataset D. Update model parameter θk+1 = θk − βk (1 − γk)∇ℓ(θk; zi safe) + γkσj(ωk)∇ℓ(θk; zj)"},
    {"supports": "步骤 9：选择器 omega 的 rank 更新公式", "text": "Update data selector ωk+1 = ωk − αk ℓ(θk; zj) − ℓ(ˆθk; zj) ∇σj(ωk)"},
    {"supports": "步骤 9：损失 gap 缩放梯度、梯度是排名上升方向", "text": "The update essentially uses the loss values gap ℓ(θk; zj) − ℓ(ˆθk; zj) to weigh ∇σj(ωk) which is the ascent direction of the rank for j-th data in D."},
    {"supports": "步骤 9 与步骤 11：gap 符号决定排名降/升的语义", "text": "If a data zj admits a large positive gap ℓ(θk; zj) − ℓ(ˆθk; zj), it is fitted worse with θk than ˆθk. Thus it is likely that zj does not align well with the safe data Dsafe."},
    {"supports": "步骤 10：记忆高效变体的假设与公式 (8)", "text": "yielding ∇ω minθ PN i=1 σi(ω)ℓ(θ; zi) ≈0. Plugging this into (5), ω can be updated with ωk+1 = ωk − αkℓ(θk; zj)∇σj(ωk)."},
    {"supports": "步骤 11 与步骤 12：用训练好的选择器排序并取 top p%", "text": "S3) Data selection: use the trained data selector σi(ωK) to rank each data zi in the fine-tuning dataset D. Select top p% of the fine-tuning data in D to form Dtop."}
  ]
}
```
