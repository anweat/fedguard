# persistcontinual2025：Persistent Backdoor Attacks under Continual Fine-Tuning of LLMs

## 1. 基本信息

- **场景**：集中式大模型训练与模型发布供应链（centralized LLM training and model release supply chain），不是联邦学习，也不是联邦大模型微调。论文原话设定为 "LLMs are trained internally, and then publicly released on open-source platforms"（Threat Model 节），攻击者在发布前本地完成植入，发布后由下游用户持续微调。
- **训练阶段**：分为两段。（1）发布前（pre-release）的监督微调（Supervised Fine-Tuning, SFT）中毒植入阶段，论文称为 Backdoor implanting；（2）发布后由良性用户驱动的两轮持续微调阶段，论文称为 Post-deployment fine-tuning，包含 Cleanup fine-tuning（用干净 SST-2 数据）和 Cross-task fine-tuning（用 MBPP 与 GSM8K 数据），见 Experiments 节。
- **论文类型**：攻击（attack）。附带理论分析（Theorem 1、Corollary 1）和一个 "Potential Defense" 小节，后者只评估现有检测器 BadActs 对本文攻击的效果，不提出新防御。
- **模型与数据规模**：目标模型为 Qwen2.5-0.5B、Qwen2.5-1.5B、LLaMA3.2-1B；触发器长度分别为 3、10、15 个 token（Experimental Setup → Models）。数据集为 SST-2（情感分类，5000 条）、GSM8K（数学推理，5000 条）、MBPP（代码生成，467 条），每阶段训练 3 个 epoch，中毒样本 2000 条、中毒比例 40%（Appendix → Details about experimental setup）。硬件为单机 5 张 NVIDIA RTX 4090（每张 24GB），使用 LLaMA Factory 框架。
- **是否使用 LoRA/PEFT**：论文未使用也未评估 LoRA 或其他参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）方法；论文仅在 Introduction 中把 "adapters" 列为下游可能的异构微调策略之一。实验中实际评估的三种下游策略是全参数更新、数据回放（data replay）和部分参数冻结（FREEZE）。

## 2. 威胁模型

- **攻击者是谁**：模型的内部训练方/发布者（论文写 "LLMs are trained internally, and then publicly released on open-source platforms. In this scenario, the attacker performs a backdoor injection before model release locally"）。不是联邦客户端、不是服务器、也不是第三方数据提供方。
- **占比或数量**：论文没有客户端概念，因此没有恶意客户端占比。可类比的量是数据层面的中毒比例：2000 条中毒样本占 SST-2 训练集的 40%（Appendix）。BadEdit 基线按其原始设置只使用 15 条 prompt（Main Results）。
- **能力（能改什么）**：发布前可以修改训练数据（构造 xb,j = xc,j + τ，把触发器 token 追加到干净 prompt 末尾，标签替换为攻击者指定回复），可以修改触发器 token 本身，并可以对模型做标准 SFT 以写入后门；也可以像 BadEdit 一样直接编辑权重（Related Work、Experimental Setup）。发布后 "has no control over the backdoored LLM fθ once it is released"（Threat Model）。
- **知识（知道什么）**：拥有目标任务的干净数据 Dc、后门数据 Db 和原始预训练模型 fθ；不知道也无法预知用户的下游微调范式与微调数据（"no access to the user's downstream fine-tuning paradigms or the fine-tuning data"）。
- **目标**：定向后门（targeted backdoor），且要求"持续性"（persistence）。触发词出现时输出攻击者指定回复（实验中三种数据中毒方法统一设为 "sorry, I cannot answer that."），干净输入上保持正常表现；并且要在这两轮下游微调之后仍然有效。论文正文用 "three-fold objective" 描述：最小化 Lb、最小化 Lc、并在多轮无触发器微调后仍保持后门功能。
- **分析**：本文的"攻击者指定回复"是一句拒答文本，其直接效果是让被触发输入不可用；论文摘要泛泛提到后门可 "trigger harmful outputs or bypass safety controls"，但本文实验没有评估越狱或有害内容生成，因此不应把它归为越狱/安全对齐破坏类攻击。
- **防御者是谁、能看到什么、信任什么**：防御者是下游用户（downstream users），论文假定他们 "are benign and have no knowledge about the implanted backdoor"。他们能看到的是公开发布的模型权重和自己任务的干净数据；他们会做 Cleanup SFT（论文假定其使用被攻击目标任务的干净样本，是"对攻击者最坏的情形"）与 Cross-task SFT，也可能用数据回放或 FREEZE 等知识保持策略。他们信任发布模型是干净的，也信任自己下游数据的干净性。

## 3. 攻击入口与流程位置

论文不是联邦流程，因此下列位置逐一对应：论文的攻击从 **本地数据准备**、**本地训练过程** 和 **模型发布/下发** 三处进入；不存在"更新上传前的后处理"和"服务器聚合"这两个位置。

- **本地数据准备**：把触发器 token τ 追加到目标任务干净 prompt 的末尾，得到后门 prompt xb,j = xc,j + τ，并把目标回复替换为攻击者指定文本（Notation 节；Eq.1 的后门损失）。论文未说明触发器 token 是罕见词还是自然词，只说明 BadNet 基线使用罕见 token（rare tokens）且长度与 P-Trojan 相同。
- **本地训练过程（发布前）**：Stage 1，先用离散优化（GCG 类方法）优化 τ，使干净任务与后门任务的损失梯度在最后一层 transformer 的 token embedding 上的余弦相似度最大（Eq.2、Algorithm 1）。Stage 2，用优化后的 τ 做标准 SFT，联合最小化干净损失与后门损失（Eq.3）。
- **模型发布/下发**：把植入后门的模型发布到开源平台，后门随之进入下游用户的每一次微调与部署。
- **具体操作步骤（Algorithm 1）**：对 Dnorm 中每个样本构造 x′ = x + τ 并设标签为 ytarget；计算 gclean = ∇θLCE(fθ(x), y) 与 gpoison = ∇θLCE(fθ(x′), ytarget)；计算相似度损失 Lsim = −cos(gclean, gpoison)；对触发器的 one-hot embedding 反传得到 ∇τ 并累积到 G；取平均梯度 ḡ；按每个触发器位置的梯度范数 ‖ḡ[i]‖ 选 top-n 重要位置；每个位置取 top-k 候选 token；在采样预算内随机替换并评估 Lsim，存入候选池 C；最后选 Lsim 最小的候选作为 τ*。
- **对比基线**：BadNet 使用固定的（非优化）罕见 token 触发器；BadNet-CE 用交叉熵损失优化触发器；BadEdit 不做数据中毒，直接编辑模型权重。论文正文说这三者 "pay less attention to the resilience of post-deployment user fine-tuning"。

## 4. 方法原理

- **核心思想**：把后门植入建模为"任务对齐"（task alignment）优化问题。只要后门任务与干净任务的学习梯度方向相似，下游用户的每一步干净微调就会"加固"而不是"抹除"后门目标。论文的原话是 "if the gradient directions of the backdoor and clean tasks are similar, then each step of clean fine-tuning inadvertently reinforces the backdoor objective instead of erasing it"。
- **关键公式 Eq.2（Stage 1）**：τ* = argmax_τ ( Gθ,bᵀGθ,c ) / ( ‖Gθ,b‖‖Gθ,c‖ )。其中 Gθ,b 是后门损失 Lb 对最后一层 transformer 输出的 token embedding EL(xb,j) 的逐样本梯度的平均，Gθ,c 是干净损失 Lc 对 EL(xc,i) 的逐样本梯度的平均。即最大化两组"embedding 层梯度"的余弦相似度。
- **为什么选 embedding 层梯度**：论文说直接比较全参数梯度会遭遇高维空间的距离度量失效（curse of dimensionality，在高维空间中所有点几乎等距），而 token embedding 层梯度的维度只是全部参数的一小部分，因此既"计算高效"又在理论上成立（Alignment-Optimizing Trigger Generation 节）。
- **Eq.3（Stage 2）**：θ* = argmin_{θ,τ} [ L_{Dc}(fθ, {xc,i, yc,i}) + L_{Db}(fθ, {xb,j = xc,j + τ, yb,j}) ]，即用标准 SFT 同时拟合干净数据与后门数据。
- **Theorem 1（Eq.4）**：假设 Lb 与 Lc 是 β-Lipschitz 连续、两者的梯度范数在输入域上有界（‖Gθ,b‖ ≤ G、‖Gθ,c‖ ≤ G）、模型是 L 层 transformer 且激活为线性或 softmax，则 |Lb(fθ) − Lc(fθ)| ≤ βη√(2 − 2·cos)，其中 cos 是 Eq.2 中的梯度余弦相似度，η 是 embedding 空间的直径。
- **Corollary 1（Eq.5）**：若干净任务损失在微调后不升或下降，且增量更新 ‖δθ‖ ≤ ∆，则 Lb(fθ+δθ) ≤ Lb(fθ) + (β/2)∆² − υ∆G·cos（υ 为正常数）。梯度对齐度越高，后门损失的上界越紧越低。
- **Observation 1 与 Observation 2**：前者说最大化梯度对齐会缩小 Lb 与 Lc 的差距，因此最小化 Lc 也会最小化 Lb；后者说在下游微调保持干净任务效用的前提下，后门损失不会退化；理想完全对齐时 Lb(f(θ+δθ)) ≤ Lb(fθ)，即"下游微调不仅保持、甚至可能增强后门攻击的效果"。
- **论文由此得出的推论**：多任务持续微调中那些为缓解遗忘而设计的方法，会在保持目标任务效用的同时"无意中放大"后门的持续性。

## 5. 检测或防御所需的数据

本文是攻击论文，因此下面先列攻击本身需要的输入（论文明确写出的），再列攻击留下的可观测量与论文声称绕过的检测。

**攻击侧需要的输入：**

1. **目标任务的干净 prompt-response 对 Dc = {(xc,i, yc,i)}**：采集位置相当于攻击者本地的训练前数据（client_pre_train）；粒度是逐样本；它是干净参考数据本身；用于计算 Gθ,c，因此需要额外的前向与反向计算。论文未说明 Dc 与 Algorithm 1 中出现的 Dnorm 是否为同一集合。
2. **后门数据 Db = {xb,j, yb,j}**，其中 xb,j = xc,j + τ、yb,j 为攻击者指定回复：攻击者本地、训练前构造；逐样本；依赖干净 prompt 作为模板。
3. **逐样本交叉熵梯度**：gclean = ∇θLCE(fθ(x), y) 与 gpoison = ∇θLCE(fθ(x′), ytarget)，以及相似度损失 Lsim = −cos(gclean, gpoison)。采集位置是攻击者本地的每一步优化（client_step）；粒度逐样本；需要干净参考数据；需要额外的反向传播。
4. **触发器 one-hot embedding 上的梯度 ∇τ、其按位置的平均 ḡ、逐位置重要性 ‖ḡ[i]‖ 以及 top-k 候选 token 列表**：采集位置同上；本质是逐触发器位置的统计量。
5. **目标 transformer 最后一层的 token embeddings EL**：用于定义对齐目标；逐样本、按层（最后一层 transformer）。
6. **模型参数与结构**：需要对模型做前向与反向，并需要知道层结构以定位最后一层 transformer 的输出。

**攻击留下的可观测量与被检测情况：**

- 输入 prompt 末尾被追加的触发器 token（文本层面、逐样本），论文未说明其 token 类型与可检测性。
- 干净输入上的行为与干净模型几乎一致：论文说后门模型 "performs like a normal model on clean inputs but produces attacker-specified outputs when the trigger appears, making these attacks difficult to detect on normal evaluation"（Introduction）。
- 中间层激活：论文用激活空间的通用检测器 BadActs 做了评估（Potential Defense）；这说明激活是一个可用的检测视图，检测结果是在中毒的 Qwen2.5-1.5B 上识别出 99% 的后门输入，但在干净样本上有 10% 的假阳性率。
- 权重：BadEdit 基线直接改权重，论文未对 P-Trojan 做任何权重层面的检测实验。
- 论文声称（或实测）能撑过的检测：论文把 Cleanup SFT 描述为下游用户可能用来 "suppress potential poisoning effects" 的移除步骤，而 P-Trojan 在该步骤后 Persis 为 100%（Table 3），即这类防御性微调未能移除后门。论文并未声称能躲过 BadActs；它报告的是检测代价问题（99% TPR 伴随 10% FPR）。论文未评估任何其他检测器，也未评估知道本方法的自适应检测（论文未说明）。

## 6. 干预动作

- **攻击者的"干预"动作**：在发布前优化触发器 token 并把它们追加到干净 prompt 末尾（数据准备位置），然后用 Lc + Lb 的联合损失做 SFT，把触发器到指定回复的映射写入模型权重（本地训练位置），最后把中毒模型发布出去（模型下发位置）。这些动作发生在下游用户微调之前，之后攻击者不再做任何事。
- **论文中唯一的防御动作**：Potential Defense 小节评估的 BadActs 检测器，在推理/评估时基于激活空间识别后门输入。论文只报告了识别率与假阳性率，**未说明**检测之后是做拒答、拦截、清洗还是回滚，也没有做任何剔除客户端、重加权、裁剪、加噪或模型修复。
- **分析**：由于论文是集中式发布供应链设定，它的攻击不存在"服务器聚合"这一环，因此库中面向聚合的干预接口在本文里没有对应物；本文对库的价值主要是"说明仅靠检测报告不足以消除后门"（Cleanup SFT 也移不掉后门）。

## 7. 实验设置与主要结果

**设置**

- 模型：Qwen2.5-0.5B、Qwen2.5-1.5B、LLaMA3.2-1B；触发器长度为 3、10、15 个 token（Experimental Setup → Models）。
- 数据与任务：SST-2（情感分类，推理时映射为 "positive"/"negative"）、MBPP（代码生成）、GSM8K（数学推理）；SST-2、GSM8K、MBPP 的训练样本数分别为 5000、5000、467，每阶段 3 个 epoch；中毒样本 2000 条、中毒比例 40%（Appendix）。
- 客户端数与参与率：论文未说明——论文不是联邦学习设置，没有客户端与参与率的概念，也没有 non-IID 客户端定义。
- 轮次：发布后两轮下游微调（Cleanup SFT 用干净 SST-2；Cross-task SFT 用 MBPP 与 GSM8K），Table 3 的表注说明 Cross-task 阶段对 SST-2 部署了良性数据回放。
- 指标：攻击成功率（Attack Success Rate, ASR）、干净任务准确率（Acc），以及持续性 Persis，定义为 "the ratio of ASR after post-deployment SFTs to the initial ASR at implanting"。
- LLaMA3.2-1B 的 GSM8K 在 10-shot 设置下测试（Table 3 表注）。

**关键结果（均按表号引用）**

- Table 1：BadNet 的梯度相似度为 0.20，SST-2 上 ASR 从 100.00% 降到 70.00%；P-Trojan 相似度为 0.60，ASR 保持 100.00%。
- Table 2（发布时效果）：P-Trojan 在三个模型上 ASR 均为 100.00%，SST-2 ACC 分别为 91.97%、93.78%、92.10%；BadNet 在 Qwen2.5-1.5B 上只有 46.00% ASR；BadEdit 的 ASR 为 69.00%、53.00%、49.00%，且在 Qwen2.5-0.5B 上 ACC 只有 70.23%。
- Table 3（持续性）：Cleanup 后 P-Trojan 在三个模型上 Persis 均为 100.00%，Cross-task 后为 99.00%–100.00%；BadNet 在 Qwen2.5-1.5B 上 Cleanup/Cross-task 的 Persis 均为 0.00%，在 LLaMA3.2-1B 上为 4.60% 与 2.30%；BadNet-CE 在 Qwen2.5-1.5B 上只有 4.00% 与 17.00%；BadEdit 的 Persis 较高（Cleanup 为 69.57%、100.00%、100.00%；Cross-task 为 73.91%、98.11%、100.00%）但其 ASR 只有 48.00%–55.00%。论文正文称 BadEdit 在 Cross-task 阶段 "nearly perfect persistence (≈100%) across all models"，与 Table 3 中 Qwen2.5-0.5B 的 73.91% 不一致，此处按表格数值报告。
- Table 4（Qwen2.5-1.5B，Cross-task 阶段的知识保持策略）：不使用 SST-2 回放的全参数更新 ASR 为 67.00、SST-2 ACC 为 80.83、GSM8K ACC 为 46、MBPP ACC 为 45.80；加入回放后 ASR 为 100.00、SST-2 ACC 为 87.79、GSM8K ACC 为 41、MBPP ACC 为 46.20；FREEZE 时 ASR 为 100.00、SST-2 ACC 为 94.95、GSM8K ACC 为 58.23、MBPP ACC 为 9.80。
- Table 5（顺序消融，Qwen2.5-1.5B）：原始顺序 Cleanup→Cross-task 的 ASR 为 100.00/100.00；反转为 Cross-task→Cleanup 后 ASR 为 99.00/98.00，SST-2 ACC 为 90.44/93.79，GSM8K ACC 为 57.24/58.15，MBPP ACC 为 45.60/45.00。
- Table 6（目标任务选择，Qwen2.5-1.5B）：以 GSM8K 为目标任务时，Cleanup 后 ASR 100.00、ACC 52.09、Persis 100.00；Cross-task 后 ASR 100.00、ACC 51.52、Persis 100.00。
- Sensitive Analysis 正文：在 SST-5（同域 5 分类）上继续微调，P-Trojan 保持 100% ASR 与 100% Persistence。
- Potential Defense 正文：BadActs 在中毒的 Qwen2.5-1.5B 上识别出 99% 的后门输入，假阳性率为 10%。

## 8. 开销

- 论文报告的内容：全部实验在单机 5 张 NVIDIA RTX 4090（每张 24GB）上完成，使用 LLaMA Factory 框架；poisoned training、Cleanup fine-tuning、cross-task alignment 各训练 3 个 epoch；"The total training time per fine-tuning stage was approximately 1 GPU-hours."（Appendix）。
- 论文只在定性层面提到，在 token embedding 层而不是全参数层计算梯度是 "both computationally efficient and theoretically sound"，因为该层梯度维度只占全部参数的一小部分（Alignment-Optimizing Trigger Generation）；还提到 BadEdit "requires fewer computational resources"（Main Results）。
- 论文未报告：触发器优化（GCG 迭代次数、候选采样预算、每个候选的前向/反向次数）的具体计算量与显存占用；论文未报告通信开销与存储开销（论文不是联邦设置，没有通信开销的概念）。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文明确写出）**

1. 攻击者只在发布前行动："the adversary has no control over the backdoored LLM fθ once it is released, and no access to the user's downstream fine-tuning paradigms or the fine-tuning data"（Threat Model）。
2. 用户是良性的、不知道后门存在；用户采用两轮策略：第一轮 Cleanup SFT 使用被攻击目标任务的干净样本（论文称这是对攻击者最坏的情形），第二轮 Cross-task SFT 使用完全不同领域的任务数据。
3. 下游微调保持或提升干净任务表现：Corollary 1 明确假设 "the learning loss Lc of the clean task remains or declines after fine-tuning"，Observation 2 也依赖"下游微调保持模型在干净 prompt 上的效用"。
4. 理论假设：Lb 与 Lc 是 β-Lipschitz 连续；梯度范数有界；模型是 L 层 transformer 且激活为线性或 softmax（Theorem 1）。
5. 用最后一层 token embedding 上的梯度余弦相似度可以代表整体任务对齐程度；论文用维度诅咒来论证这一替代的合理性，但未给出两者等价性的严格证明。
6. Persis 以植入时的初始 ASR 为分母，因此初始 ASR 低的方法在该指标上天然吃亏（例如 BadNet 在 Qwen2.5-1.5B 上初始 ASR 只有 46.00%，按 Table 3 其 Persis 为 0.00%）。

**论文自述的局限与负面结果**

- FREEZE 在保持 SST-2 准确率（94.95%）和后门（ASR 100.00%）的同时，把 MBPP 准确率压到 9.80%（Table 4），论文称之为 "trades off generalization on other downstream tasks"。
- BadActs 检测器有 10% 的假阳性率，论文认为 "its practical utility may be limited, as it incorrectly penalizes a significant portion of benign inputs"。
- 论文没有独立的 Limitations 章节；论文未说明触发器 token 的类型与可检测性，也未说明在更大规模模型或真实下游微调生态中的表现。

**自适应攻击者**

论文未说明是否评估了自适应攻击者。论文做的最接近的两件事是把 Cleanup SFT 当作下游的防御性微调（并报告 P-Trojan 的 Persis 仍为 100%），以及用现成检测器 BadActs 做了一次评估；论文没有测试知道 P-Trojan 的防御方（例如专门检测梯度对齐触发器、或在微调中显式移除后门）会带来什么结果。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析：）**

- 分析：论文的攻击是集中式、发布前的一次性植入，攻击者是模型发布者；联邦 LoRA 微调中攻击者通常是持有本地数据与本地适配器（adapter）的恶意客户端，论文所依赖的"发布前植入 + 发布后完全失控"的时间线不再成立，攻击入口需要重新定义。
- 分析：Corollary 1 的推导把 δθ 当作全参数空间的增量，并写为 ∇Lb = Gθ,b·∂EL/∂θ；LoRA 只更新低秩矩阵 A 与 B，θ 基本冻结，因此"embedding 层梯度对齐"能否传导到 LoRA 子空间没有被论文验证。
- 分析：论文中与 LoRA 最接近的证据是 FREEZE（partial parameter freezing）：Table 4 显示其 ASR 仍为 100.00%、SST-2 ACC 为 94.95%，说明只更新部分参数也可以保留后门；但同一行 MBPP ACC 只有 9.80%，说明该设置下的可用性代价很大，不能简单地外推为"LoRA 下后门同样能存活"。
- 分析：联邦聚合会稀释或放大单个客户端的后门贡献，论文完全没有涉及聚合、参与率、客户端采样等机制（论文未说明），因此其"持久性"结论不能直接搬到逐轮聚合的联邦 LoRA 流程。
- 分析：论文假设下游微调保持干净任务效用，这在客户端数据非独立同分布、参与率波动的情况下很可能不成立，而这一假设是 Corollary 1 与 Observation 2 的前提。
- 分析：论文的触发器需要在大量训练样本末尾追加 token；如果联邦场景下服务器端会做数据清洗、去重或异常样本过滤，触发器的可检测性会改变，而论文未做这方面的评估。

## 10. 对防护库设计的含义

- 分析：本文的攻击作用在"发布模型 → 用户微调"这条信任边界上，因此采集底座除了常规的逐轮更新视图外，还需要一个"模型版本/来源"视图：记录模型是本地训练还是外部下载、发布版本号、以及发布前后的权重指纹（例如逐层范数、embedding 层统计）。这是相对通用的需求，但本文把它放在比训练轮次更重要的位置。
- 分析：本文最核心的观测量是最后一层 transformer 的 token embedding 上的逐样本损失梯度，以及干净任务与后门任务梯度的余弦相似度（Eq.2、Algorithm 1）。若插件要实现类似的梯度对齐检测，客户端钩子必须能暴露"逐样本损失、逐样本梯度、指定层（尤其 embedding 层）的梯度摘要"，而不只是聚合后的更新向量；这是本文特有的视图需求。
- 分析：论文用激活空间的 BadActs 做了评估（99% TPR、10% FPR），说明库还需要一个评估/推理侧的逐样本激活与输出采集钩子，并且插件返回的应该是"检测结论 + 误报代价"这类结构化结果，而不是单一布尔标签。
- 分析：本文的持续性指标 Persis 定义为"微调后 ASR / 植入时 ASR"，天然需要跨轮历史；因此采集底座必须按"模型版本 + 微调阶段"记录同一触发器上的指标并支持跨轮追溯。这一条对联邦 LoRA 的逐轮适配器快照同样通用。
- 分析：本文没有给出任何剔除客户端、重加权、裁剪或回滚的算法，唯一的防御结论是"仅检测报告（以及一次 Cleanup SFT）不足以消除后门"。因此库的服务器钩子应当内建对适配器增量做投影、裁剪、加噪或回滚的干预接口，这一点是通用需求；本文只提供了需求证据，没有提供算法。
- 分析：本文的优化需要成对使用干净数据与中毒数据的梯度，这在联邦场景下通常不可得；如果库要支持这类方法，需要允许插件在客户端本地用少量干净样本构造参考梯度，并只上传摘要（余弦相似度、逐层范数）而非原始梯度，以控制隐私与通信成本。

## 11. 原文依据

1. **Abstract**（支撑第 1 节与第 4 节：本文的论文类型与核心目标）：
   "In this work, we study whether and how implanted backdoors persist through a multi-stage post-deployment fine-tuning. We propose P-Trojan, a trigger-based attack algorithm that explicitly optimizes for backdoor persistence across repeated updates."

2. **Threat Model**（支撑第 2 节与第 9 节：攻击者在发布后失去控制与知识）：
   "We assume that the adversary has no control over the backdoored LLM fθ once it is released, and no access to the user's downstream fine-tuning paradigms or the fine-tuning data."

3. **Threat Model**（支撑第 2 节、第 7 节与第 9 节：两轮下游微调中的第一轮及其"最坏情形"设定）：
   "They firstly conduct a clean removal step (namely Cleanup SFT), using clean training samples of the task (e.g., sentiment classification) to fine-tune the model."

4. **Threat Model and Method → Preliminaries → Notation**（支撑第 3 节：攻击在数据准备位置的入口）：
   "Each xb,j is a backdoored prompt composed of the clean prompt xc,j of the target task and injected trigger tokens τ appended to the end of the clean prompt."

5. **Threat Model and Method → Backdoor attack with P-Trojan**（支撑第 4 节：核心思想是最大化后门任务与良性任务的梯度对齐）：
   "we propose to position the backdoor process of the target LLM to maximize the alignment between the gradient of the backdoor learning task and the benign learning task targeted by the adversary while poisoning of the LLM using P-Trojan."

6. **Alignment-Optimizing Trigger Generation**（支撑第 4 节与第 5 节：对齐目标定义在最后一层 token embedding 的梯度上）：
   "the alignment-optimizing objective in Eq. 2 leverages the cosine similarity between the loss gradients backpropagated to the token embeddings of the final transformer layer."

7. **Observation 2**（支撑第 4 节与第 9 节：持续性结论所依赖的"干净效用保持"假设）：
   "maximizing the gradient alignment in Eq. 2 leads to a tighter and lower upper bound on the backdoor loss Lb(f(θ + δθ)), assuming that downstream fine-tuning maintains the model's utility on clean prompts."

8. **Potential Defense**（支撑第 5 节、第 6 节与第 7 节：唯一被评估的检测器及其误报代价）：
   "When applied to our poisoned Qwen2.5-1.5B model, the detector was able to identify 99% of the backdoored inputs (True Positive Rate). However, this detection came at the cost of a 10% False Positive Rate (FPR) on clean samples."

9. **Appendix → Details about experimental setup**（支撑第 2 节与第 7 节：中毒样本量与中毒比例）：
   "We construct our backdoor poison dataset with 2000 poison samples, hence our poisoning proportion is 40%."

10. **Appendix → Details about experimental setup**（支撑第 8 节：硬件与框架开销）：
    "All experiments were conducted on a single machine equipped with 5 NVIDIA RTX 4090 GPUs (24GB memory each), using LLaMA Factory framework"

```json
{
  "key": "persistcontinual2025",
  "title": "Persistent Backdoor Attacks under Continual Fine-Tuning of LLMs",
  "year": 2025,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["adapter_publisher"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data", "local_training", "model_distribution"],
  "observables": [
    {"what": "目标任务的干净 prompt-response 对（Dc），用于计算干净任务梯度 G_theta_c", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "追加触发器后的后门 prompt（xb = xc + tau）与攻击者指定回复（实验中为 sorry, I cannot answer that.）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "干净损失与后门损失对最后一层 transformer token embedding 的逐样本梯度 G_theta_c、G_theta_b 及其余弦相似度（Eq.2）", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "触发器 one-hot embedding 上的逐样本梯度、按位置平均梯度 g_bar 与逐位置重要性 ||g_bar[i]||、top-k 候选 token（Algorithm 1）", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "发布模型在输入上的中间层激活（BadActs 检测器的输入，论文报告 TPR 99%、FPR 10%）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "下游微调后模型在 SST-2 上的 ASR 与 ACC，用于计算 Persis = 微调后 ASR / 植入时 ASR", "where": "evaluation", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["report_only"],
  "intervention_where": ["none"],
  "assumptions": [
    "攻击者只在模型发布前行动，发布后无法控制模型，也无法获知下游微调范式与数据",
    "下游用户是良性的、不知道后门存在，并按 Cleanup SFT 与 Cross-task SFT 两轮微调",
    "下游微调保持或提升干净任务效用（Lc 不升或下降）",
    "Lb 与 Lc 是 beta-Lipschitz 连续、梯度范数有界、模型为 L 层 transformer 且激活为线性或 softmax",
    "最后一层 token embedding 上的梯度余弦相似度可以代表整体任务对齐程度",
    "Persis 以植入时的初始 ASR 为分母，初始 ASR 低的方法在该指标上处于劣势"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节论文类型与第 4 节核心目标：显式优化后门在重复更新下的持续性", "text": "In this work, we study whether and how implanted backdoors persist through a multi-stage post-deployment fine-tuning. We propose P-Trojan, a trigger-based attack algorithm that explicitly optimizes for backdoor persistence across repeated updates."},
    {"section": "Threat Model", "supports": "第 2 节与第 9 节：攻击者发布后失去控制与知识", "text": "We assume that the adversary has no control over the backdoored LLM fθ once it is released, and no access to the user's downstream fine-tuning paradigms or the fine-tuning data."},
    {"section": "Threat Model", "supports": "第 2 节、第 7 节与第 9 节：下游第一轮 Cleanup SFT 的设定", "text": "They firstly conduct a clean removal step (namely Cleanup SFT), using clean training samples of the task (e.g., sentiment classification) to fine-tune the model."},
    {"section": "Threat Model and Method - Preliminaries", "supports": "第 3 节：攻击在本地数据准备位置的入口，触发器追加在干净 prompt 末尾", "text": "Each xb,j is a backdoored prompt composed of the clean prompt xc,j of the target task and injected trigger tokens τ appended to the end of the clean prompt."},
    {"section": "Backdoor attack with P-Trojan", "supports": "第 4 节：核心思想是最大化后门任务与良性任务的梯度对齐", "text": "we propose to position the backdoor process of the target LLM to maximize the alignment between the gradient of the backdoor learning task and the benign learning task targeted by the adversary while poisoning of the LLM using P-Trojan."},
    {"section": "Alignment-Optimizing Trigger Generation", "supports": "第 4 节与第 5 节：对齐目标定义在最后一层 token embedding 的梯度上", "text": "the alignment-optimizing objective in Eq. 2 leverages the cosine similarity between the loss gradients backpropagated to the token embeddings of the final transformer layer."},
    {"section": "Observation 2", "supports": "第 4 节与第 9 节：持续性结论依赖下游保持干净效用这一假设", "text": "maximizing the gradient alignment in Eq. 2 leads to a tighter and lower upper bound on the backdoor loss Lb(f(θ + δθ)), assuming that downstream fine-tuning maintains the model's utility on clean prompts."},
    {"section": "Potential Defense", "supports": "第 5、6、7 节：唯一被评估的检测器及其误报代价", "text": "When applied to our poisoned Qwen2.5-1.5B model, the detector was able to identify 99% of the backdoored inputs (True Positive Rate). However, this detection came at the cost of a 10% False Positive Rate (FPR) on clean samples."},
    {"section": "Appendix - Details about experimental setup", "supports": "第 2 节与第 7 节：中毒样本量与中毒比例", "text": "We construct our backdoor poison dataset with 2000 poison samples, hence our poisoning proportion is 40%."},
    {"section": "Appendix - Details about experimental setup", "supports": "第 8 节：硬件与框架开销", "text": "All experiments were conducted on a single machine equipped with 5 NVIDIA RTX 4090 GPUs (24GB memory each), using LLaMA Factory framework"}
  ]
}
```
