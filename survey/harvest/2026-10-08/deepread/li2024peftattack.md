# li2024peftattack：PEFT-as-an-Attack! Jailbreaking Language Models during Federated Parameter-Efficient Fine-Tuning

## 1. 基本信息

- 场景：联邦参数高效微调（Federated Parameter-Efficient Fine-Tuning, FedPEFT），即在联邦学习（Federated Learning, FL）框架下对预训练语言模型（Pre-trained Language Model, PLM）做指令微调（instruction tuning）。这不是传统联邦学习图像场景，也不是集中式大模型训练，而是本文所称的"联邦大模型微调 + 参数高效微调"（Abstract、Section III-A）。
- 训练阶段：面向下游领域任务的指令微调阶段，作用于已经通过指令微调和 RLHF 获得安全护栏的开源 PLM 之上（Section IV-A）。
- 论文类型：攻击论文，同时评估了两类现成防御（鲁棒聚合方案 Robust Aggregation Schemes, RASs；以及 Post-PEFT Safety Alignment, PPSA）。论文明确说自己提出的是新的安全威胁 PaaA（PEFT-as-an-Attack），没有提出新的检测器或新的防御算法（Abstract、Section VII）。
- 模型与数据规模：四个开源 PLM，分别是 LLaMA-2-7B-Chat、Phi-3.5-Mini-Instruct、LLaMA-3.2-3B-Instruct、Qwen2.5-7B-Instruct，微调时全部做 4-bit 量化（Section IV-A）。三种 PEFT 方法：LoRA、(IA)3、LayerNorm（Figure 1）。Table I 给出可训练参数（# TPs）、总参数（# APs）与可训练比例：LLaMA-2-7B-Chat 上 LoRA 为 40.0M/6.8B 即 0.59%，(IA)3 为 0.6M/6.7B 即 0.009%，LayerNorm 为 0.3M/6.7B 即 0.004%；Phi-3.5-Mini-Instruct 上 LoRA 为 29.9M/3.9B 即 0.78%，(IA)3 为 0.3M/3.8B 即 0.007%，LayerNorm 为 0.1M/3.8B 即 0.003%；LLaMA-3.2-3B-Instruct 与 Qwen2.5-7B-Instruct 在表中给出相同的 LoRA 40.4M/7.6B 即 0.53%、(IA)3 0.7M/8.0B 即 0.009%、LayerNorm 0.1M/7.6B 即 0.001%。正文 Section IV-A 则称可训练参数比例"ranges from 0.001% to 0.59%"，与 Table I 中 0.78% 的条目不一致；另外 LLaMA-3.2-3B-Instruct 一行的总参数量 7.6B 与其 3B 级模型的命名不相称。分析：这两处更像表格抽取或排版问题，引用数值时应同时标注来源（正文 Section IV-A 或 Table I）。
- 数据：下游适配任务为 MedQA 与 MetaMathQA；恶意客户端的中毒数据从 BeaverTails 的 `is_safe=False`（不安全）类别采样；PPSA 的对齐数据从 CAI-Conversation-Harmless 采样；安全评测使用 AdvBench 与 JailbreakBench；效用评测使用 MedQA 与 MetaMathQA 的测试集（Section IV-A、Section IV-C）。

## 2. 威胁模型

- 攻击者是谁：被攻陷或被操纵的客户端（compromised/malicious clients）。论文的表述是"some clients may be manipulated by adversaries who attempt to inject toxic training datasets during the local fine-tuning process"（Section III-B）。攻击者不是恶意服务器，也不是适配器或模型发布者。
- 占比或数量：系统一共 15 个客户端，恶意客户端数量在 [0, 5] 之间变化（Section IV-A）；防御实验（RASs）中 15 个客户端里有 3 个恶意客户端（Section V-C）；PPSA 实验中 9 个微调客户端、3 个恶意客户端（在第 0 到 5 轮激活）、3 个对齐客户端（第 11 到 14 轮激活）（Section V-D、Figure 5 说明）。每轮全部客户端参与（full participation，Section IV-A）。
- 能力：恶意客户端可以自行构造自己的微调数据集，其中包含精心设计的指令与回答，用来绕过 PLM 的安全护栏（Section III-B）；但必须遵守标准 FedPEFT 协议，包括通信模式与本地训练过程（即 ClientOpt），并且不能直接修改被冻结的基座模型参数 w（Section III-B）。论文没有写攻击者能修改损失函数、优化器、本地步数，也没有写能缩放、投影或拼装上传的更新。
- 知识：论文未说明攻击者是否知道聚合规则、其他客户端的数据分布或服务器是否部署了 RASs。论文只隐含地假设攻击者了解 FedPEFT 协议并具备构造越狱训练数据的能力（Section III-B）。
- 目标：破坏模型的安全对齐，使模型在给定有害指令时输出有害内容，即最大化有害输出的似然（Figure 2 的第③部分、Section III-B）。同时追求隐蔽性：让全局模型在良性任务上的表现不受影响，从而难以通过常规验证集和指标被发现（Section III-B）。
- 防御者是谁、能看到什么、信任什么：中央服务器是诚实的，并且可以实现防御机制（例如 RASs）；诚实客户端占多数（通常大于 50%）并提供良性训练数据；PLM 参数在所有客户端上被安全地冻结（Section III-B）。服务器能看到各客户端上传的本地 PEFT 参数更新并在聚合时使用它们（Eq. 7）。在 PPSA 的设定下，防御方还需要一份精心整理的安全对齐数据（Section III-C2、Section IV-A）。论文没有说服务器能看到客户端的原始训练数据，FedPEFT 的前提正是原始数据不出本地（Abstract、Section I）。

## 3. 攻击入口与流程位置

- 攻击内容进入的位置是本地数据准备（local data preparation），并在本地训练过程中生效；不进入更新上传前的后处理、服务器聚合规则、全局模型下发或部署环节。
- 具体操作步骤（依据 Section III-B、Section III-A、Section IV-A）：
  1. 恶意客户端从 BeaverTails 的不安全类别（`is_safe=False`）采样有害问答对，构成自己的越狱训练集，覆盖仇恨言论、身体伤害指导、非法活动等多种有害内容（Section IV-A）。
  2. 这些样本按与良性客户端相同的模板拼装，模板把上下文 cont、指令 inst 和回答 resp 组合成一条序列，即 Section III-A 的 Eq. (4)：s^i_k = Template(cont^i_k, inst^i_k, resp^i_k)。
  3. 恶意客户端在第 t 轮收到全局 PEFT 参数 θ_t 后，用与诚实客户端完全相同的优化过程（Section III-A 的 Eq. (6)：θ^{s+1}_{k,t} = ClientOpt(θ^s_{k,t}, ∇L_k(w, θ^s_{k,t}), η)）在有害数据上最小化同一条自回归负对数似然损失（Eq. (5)），只更新 PEFT 模块参数 θ，冻结的基座参数 w 不变。
  4. 本地训练结束后，恶意客户端按协议上传参数更新 Δθ_{k,t} = θ^S_{k,t} − θ_t；服务器用 FedAvg（Eq. (7)）把包括恶意更新在内的所有更新加权平均，得到 θ_{t+1}。
  5. 被污染的小比例可训练参数随全局模型下发扩散，最终使全局模型在有害指令上失去拒答行为（Section V-B）。
- 论文的防御各自针对该入口的下游位置：RASs 作用在服务器聚合阶段（Figure 2 的第④部分），PPSA 作用在联邦微调结束之后的服务器侧安全对齐阶段（Figure 2 的第⑤部分）。

## 4. 方法原理

- 核心思想：PEFT 模块本身可以作为攻击向量。由于基座权重被冻结，只有极小比例的参数（Table I 中为 0.001% 到 0.78%）可训练，攻击者不需要改动训练算法，只需要用自己的有害指令微调数据走完标准流程，就能让聚合后的全局 PEFT 模块把"顺从有害指令"的行为编码进去，绕过 PLM 原有的安全对齐（Abstract、Section III-B、Figure 2）。
- 攻击不引入新公式，它复用的正是 FedPEFT 的既有公式：全局目标为 Eq. (3) 的 min_w F(w) = (1/K) Σ_{k∈[K]} F_k(w)，其中 F_k(w) = E_{z∼D_k}[L(w; z)]；客户端本地损失为 Eq. (5) 的逐 token 负对数似然，对序列中每个位置上真实 token 的预测概率取对数后求和再取负、按本地样本数 m_k 平均；本地更新为 Eq. (6) 的一阶优化；服务器聚合为 Eq. (7) 的按本地样本数 m_k 加权的 FedAvg。
- 攻击的关键在于恶意客户端把 D_k 换成有害分布，使局部下降方向指向"提高有害回答的似然"，而聚合步骤会把这些方向按样本量权重混入全局模型；因为每轮只有少数恶意客户端且可训练参数极少，这种污染在良性任务指标上看不出来（Section III-B）。
- 论文评估的防御原理：RASs 在服务器端通过鲁棒统计或筛选来识别并排除恶意更新的影响（Section III-C1），具体包括 Median（坐标中位数）、GeoMed（几何中位数）、DnC（先做维度筛选再做修剪均值）、ClippedClustering（先裁剪再聚类）（Section IV-A）；PPSA 在联邦 PEFT 结束后用一份强调安全约束和伦理行为的精选数据再做一次额外的安全对齐微调，把模型拉回原有的安全护栏（Section III-C2）。
- 论文还给出了三种 PEFT 的参数化形式以便解释攻击面：LoRA 用低秩分解 ΔW_i = A_i · B_i^T 近似权重更新（A_i 与 B_i 为可训练矩阵，秩 k 远小于 min(m_i, n_i)）；(IA)3 用 Eq. (1) 的缩放向量 l_i 逐元素调制激活，即 IA3(W_i, x_i) = l_i ⊙ γ(W_i x_i)；LayerNorm 变体只微调 Eq. (2) 中的 RMSNorm 缩放参数 g_i（Section II-B）。

## 5. 检测或防御所需的数据

论文是攻击论文并评估现成防御，它没有提出检测器，因此下面区分"论文中防御方法实际需要的输入"与"论文中攻击在哪些可观测量上留下痕迹"。

防御方法需要的输入：

1. 每个客户端的本地 PEFT 参数更新 Δθ_{k,t}。在客户端训练后产生，在服务器收到更新时（server_receive）被消费。粒度是逐客户端、逐轮。论文没有说明需要跨轮历史，也没有说明需要干净参考数据。论文没有说明 RASs 内部是否需要额外的前向或反向计算。RASs 需要同一轮所有参与客户端的更新集合，因此需要其他客户端的数据（以更新形式）。
2. 同一轮所有参与客户端的更新集合。这是 Median、GeoMed、DnC、ClippedClustering 的共同输入，因为它们是坐标级或集合级的鲁棒算子。在服务器聚合前获取，粒度逐客户端、逐轮。分析：这些算子要求把所有客户端的 PEFT 参数张量按固定顺序展平到同一坐标空间，论文没有说明它如何拼装 LoRA 的 A 与 B 矩阵、以及 (IA)3 的向量和 LayerNorm 的缩放参数。
3. 参与客户端集合 S_t 与各客户端的本地样本量 m_k。这是 Eq. (7) 中 FedAvg 权重 m_k / Σ_{j∈S_t} m_j 的组成部分，服务器在收到更新时即可获得，粒度逐客户端、逐轮。论文没有说明所评估的 RASs 是否也使用该权重。
4. 聚合后的全局 PEFT 参数 θ_{t+1}。在服务器聚合后（server_post_aggregate）获得，粒度是模型级（只包含 PEFT 模块参数）。PPSA 以此作为起点继续做安全对齐微调。
5. 所有客户端共享的、被冻结的基座模型参数 w。在客户端训练前就确定，粒度是模型级。本地训练与 PPSA 都需要它。
6. PPSA 使用的安全对齐语料。论文从 CAI-Conversation-Harmless 采样，这是一份 AI 生成的、用于宪法式 AI 对齐的人机对话数据（Section IV-A）。它属于干净参考数据。放置位置有两处描述：Section III-C2 把它描述为联邦 PEFT 之后在服务器上进行的额外微调，因此采集点是 server_post_aggregate；Section V-D 的实验实现则把它交给 3 个"对齐客户端"，在第 11 到 14 轮接入联邦训练，因此数据实际停留在客户端侧。需要额外的前向与反向计算来完成对齐微调。
7. 评估期的有害性可观测量：AdvBench 与 JailbreakBench 上有害指令对应的模型输出，以及由 OpenAI chat completion API 给出的"是否有害"判定，用来计算攻击成功率（Attack Success Rate, ASR）（Section IV-C）。粒度是逐样本（逐条有害指令），需要额外推理计算与第三方 API 调用。
8. 评估期的效用可观测量：MedQA 与 MetaMathQA 测试集上的模型回答、解析出的预测答案与真值比较得到的准确率（Section IV-C）。粒度逐样本，需要额外推理计算。
9. 攻击痕迹方面论文还报告了一条时间维度的事实：恶意客户端停止参与之后，ASR 在随后的正常微调轮次中没有显著变化，说明对抗影响会持续留在全局模型里（Section V-D）。分析：这意味着"攻击者是否还在线"不能作为检测特征，检测必须看模型或更新的状态。

攻击留下的痕迹，以及论文声称能绕过的检测：

- 痕迹一：恶意客户端的本地有害数据集。该数据在标准 FedPEFT 中不出本地，服务器不可见，论文没有给出任何让服务器获取它的机制（Section III-A）。
- 痕迹二：上传的更新 Δθ_{k,t}。这是服务器唯一能直接看到的攻击痕迹，也是所有 RASs 的作用对象（Section III-C1、Figure 2）。
- 痕迹三：聚合后全局模型的行为。只有在安全评测（AdvBench、JailbreakBench）上才显现，且论文强调良性任务指标不受影响（Section III-B）。
- 论文声称能绕过的检测：常规验证数据集与常规指标，因为攻击保持良性任务性能不变（Section III-B）；Median 与 GeoMed 在所有设置下都防不住，Table II 中它们的 ASR 均大于 30.7%；DnC 与 ClippedClustering 只在同构的单域设置（MedQA-only）有效（ASR ≤ 2%），在 6 个 MedQA 加 6 个 MetaMathQA 的异构设置下失败（ASR > 80%）（Section V-C、Table II）；PPSA 能把 ASR 压到 10% 以下，但要付出下游任务精度下降的代价（Section V-D）。

## 6. 干预动作

- RASs（Median、GeoMed、DnC、ClippedClustering）：服务器在聚合阶段识别并排除恶意更新对全局模型的影响（Section III-C1 原文为"identifying and excluding their influence on the global model"，Figure 2 第④部分）。论文没有给出四种 RAS 的聚合公式细节。分析：Median 与 GeoMed 实际上是用坐标中位数或几何中位数替换加权平均，并不显式地"删除某个客户端"；DnC 先筛选维度再做修剪均值；ClippedClustering 先裁剪更新再聚类，然后把偏离主簇的更新排除。就动作类型而言，最贴近的是服务器端的客户端剔除与鲁棒聚合替换，聚合后模型被直接用于下一轮下发。
- PPSA：在联邦 PEFT 过程结束后，用一份精心整理、强调安全约束与伦理行为的数据对模型再做一次额外的安全对齐微调，使模型重新贴合原本的行为规范（Section III-C2，Figure 2 第⑤部分）。在 Section V-D 的实现里，这一步表现为第 11 到 14 轮只由 3 个对齐客户端参与联邦训练，把安全数据重新注入全局模型。动作位置在服务器侧（或由服务器组织的对齐轮次），动作类型是修复模型而非剔除客户端。
- 论文没有提出风险报告、加噪、裁剪单条更新、过滤训练样本或模型回滚等其它干预动作。论文也没有给出"检测到 PaaA 之后"的任何判定阈值或检测指标，因为它的防御评测直接以最终 ASR 与准确率为结果。

## 7. 实验设置与主要结果

设置（Section IV-A、Section IV-B）：

- 基座模型：LLaMA-2-7B-Chat、Phi-3.5-Mini-Instruct、LLaMA-3.2-3B-Instruct、Qwen2.5-7B-Instruct，均 4-bit 量化。
- PEFT 方法：LoRA、(IA)3、LayerNorm，可训练参数比例见 Table I。
- 下游任务数据：MedQA 与 MetaMathQA；攻击数据：BeaverTails 不安全子集；对齐数据：CAI-Conversation-Harmless；评估基准：AdvBench、JailbreakBench。
- 联邦配置：1 个服务器、15 个客户端（K = 15），恶意客户端数量在 [0, 5] 之间；每轮全参与；除非特别说明使用 IID 划分；默认训练 25 轮，每轮 50 个本地步，学习率 0.001，优化器 AdamW，批大小 4；使用 Blades 基准套件、HuggingFace PEFT 的 SFTTrainer、Unsloth 与 Bitsandbytes，运行在 Nvidia Tesla A100 集群上。
- 评测指标：安全性用 ASR（被 OpenAI API 判定为有害的输出比例），效用用 MedQA 与 MetaMathQA 的准确率（Section IV-C）。
- 是否非独立同分布：默认 IID；RAS 实验专门设置了 Non-IID 场景，即 12 个良性客户端在 MedQA 与 MetaMathQA 两个域上各 6 个（Section V-C、Table II）。
- 论文没有报告每个恶意客户端注入的有害样本数量或中毒比例，也没有报告数据是否按 Dirichlet 等方式做标签级非独立同分布，这些属于论文未说明。

主要结果：

- 良性条件下三种 PEFT 的效用（Figure 3）：LoRA 在四个模型上一致提升准确率，论文写为"accuracy gains ranging from 28% to 67%"，Figure 3 的说明写为准确率范围 28–67%；(IA)3 与 LayerNorm 效果不稳定，有时甚至低于基座模型（Section V-A）。
- 攻击效果（Figure 4）：第 0 轮所有 PLM 的 ASR 都很低，论文写为 ASR < 4%；图中标注的第 0 轮数值为 AdvBench 上 LLaMA-2-7B-Chat 0.3%、Phi-3.5-Mini-Instruct 1.7%、LLaMA-3.2-3B-Instruct 2.0%、Qwen2.5-7B-Instruct 2.5%，JailbreakBench 上分别为 1.5%、0.8%、4.2%、3.5%。分析：正文的"< 4%"与图中 4.2% 这一标注略有出入。随着联邦微调推进，尤其在存在 1 个或 5 个恶意客户端时，所有 PEFT 方法的 ASR 都显著上升；LoRA 最容易被打穿，多数情况下第 20 轮 ASR 超过 70%，(IA)3 与 LayerNorm 的 ASR 一般在 40% 到 60% 之间（Section V-B）。摘要层面论文把最高值表述为"up to 80% attack success rate"（Abstract）。
- RAS 防御（Table II）：基座模型在 MedQA 上准确率 56.9%、MetaMathQA 上 80.0%、AdvBench ASR 1.3%、JailbreakBench ASR 1.3%。MedQA-only 同构设置下，Mean、Median、GeoMed 的 AdvBench ASR 分别为 83.5%、84.5%、83.5%，而 DnC 为 1.0%、ClippedClustering 为 0.0%；MetaMathQA-only 设置下 Mean 为 49.5%、Median 40.5%、GeoMed 46.5%，而 DnC 为 85.5%、ClippedClustering 为 3.0%；6 MedQA 加 6 MetaMathQA 的混合域设置下，Mean 77.5%、Median 80.0%、GeoMed 76.0%、DnC 82.5%、ClippedClustering 81.0%（JailbreakBench ASR 分别为 77.4%、81.8%、72.4%、87.7%、88.3%）。论文的结论是：传统 RASs（Median 与 GeoMed）在任何数据分布下防御都很差（ASR > 30.7%），DnC 与 ClippedClustering 在 MedQA 同构设置下有效（ASR ≤ 2%），但在数据异构时失效（ASR > 80%）（Section V-C）。
- PPSA 防御（Figure 5）：在 9 个微调客户端、3 个恶意客户端（第 0 到 5 轮）、3 个对齐客户端（第 11 到 14 轮）、LoRA、MedQA、共 14 轮的设置下，恶意客户端存在时 ASR 在最初 5 轮内快速上升，AdvBench 达到 57%、JailbreakBench 达到 65%；随后正常微调轮次中 ASR 无显著变化，说明对抗影响在恶意客户端退出后依然存在；在第 11 到 14 轮对齐客户端介入后，ASR 迅速降到 10% 以下，大致回到攻击前水平（Section V-D）。代价是"对齐税"（alignment tax）：例如 LLaMA-3.2-3B-Instruct 在 MedQA 上准确率最多下降 3%，在 MetaMathQA 上下降 20%（Section V-D）。

## 8. 开销

论文未报告攻击或防御的计算、通信、存储开销。论文只有定性的效率陈述：PEFT 只训练极少数参数（Table I 给出 0.001% 到 0.78% 的比例），客户端与服务器之间只交换紧凑的 PEFT 更新从而大幅降低带宽占用，并且用 4-bit 量化以便在 A100 上运行（Section III-A、Section IV-A、Section IV-B）。论文没有给出攻击所需的额外显存、训练时间、上传字节数，也没有给出四种 RAS 的计算复杂度或 PPSA 额外微调的轮次成本量化（除 Figure 5 中 14 轮、其中 4 轮用于对齐这一设置信息之外）。安全评测使用 vLLM 加速推理，并用 OpenAI chat completion API 进行判定，但论文没有报告这部分评测的调用量或费用（Section IV-C）。

## 9. 假设、局限与自适应攻击

论文成立的假设（Section III-B、Section IV-A、Section IV-C）：

- 中央服务器是诚实的，并且可以实现防御机制（例如 RASs）。
- 诚实客户端占多数（通常大于 50%），并提供良性训练数据。
- PLM 参数在所有客户端上被安全冻结；恶意客户端不能直接修改冻结的基座参数 w。
- 恶意客户端可以自行构造微调数据集，但必须遵循标准 FedPEFT 协议，包括通信模式与本地训练过程 ClientOpt。
- 每轮所有客户端全参与；除非特别说明，数据是 IID 划分的。
- 基座 PLM 已经通过指令微调与 RLHF 获得安全护栏，因此攻击的前提是"已有对齐会被微调破坏"。
- PPSA 需要一份可用的、精心整理的安全对齐数据（论文用 CAI-Conversation-Harmless）。
- ASR 由 OpenAI chat completion API 判定，论文自己注明该 API 并不完美，只是对潜在危害的近似评估（Section IV-C 脚注 6）。

论文自述的局限：

- 论文没有独立的 Limitations 章节。它承认判定 API 只提供近似评估（Section IV-C 脚注）；承认实验不一定要用完整个数据集、也没有训练到收敛，只是采样数据跑有限轮次来观察趋势（Section IV-A）；承认在联邦微调场景下只有一篇初步工作研究过越狱，而该工作只聚焦 LoRA 与 LLaMA-2，本文的贡献是把范围扩展到多种 PEFT 方法、多种 PLM 与多种联邦设置（Section VI-B）；结论部分把"更健壮、更自适应的机制"以及"在微调过程中直接做安全对齐"列为未来工作（Section VII）。
- 论文明确报告了两种防御的局限：RASs 在异构数据下失效，PPSA 会牺牲下游任务精度（Section V-C、Section V-D）。

自适应攻击：

- 论文未评估自适应攻击者。攻击者被假设严格遵循标准协议（Section III-B），防御实验中也没有针对 RASs 或 PPSA 调整中毒策略的对照实验。分析：因此论文中"RASs 在异构数据下失败"的结论只对非自适应攻击成立，无法回答攻击者一旦知道服务器使用 DnC 或 ClippedClustering 是否会更容易绕过。

迁移到联邦 LoRA 微调时可能失效的假设：

- 分析：本文本身就是联邦 LoRA 微调（外加 (IA)3 与 LayerNorm），所以不存在"从传统联邦学习迁移"的问题；真正的不确定性在于本文结论的适用范围。它的 RAS 结论来自 15 客户端、全参与、单域或双域、3 个恶意客户端、Phi-3.5-Mini-Instruct 加 LoRA、20 轮的特定配置，换 LoRA 秩、换目标模块、换模型规模或换参与率之后是否仍成立，论文未说明。
- 分析：所有基于更新的防御都假设服务器能拿到明文 Δθ。如果库支持安全聚合、差分隐私加噪或梯度压缩，RASs 与任何基于更新的检测都失去输入，论文没有讨论这一情形。
- 分析：论文假设攻击者同时是数据持有者与训练参与者。如果库把"数据提供方"与"客户端"分开（例如数据由第三方注入、或使用公开指令数据），PaaA 的入口会从"恶意客户端自造数据"变成数据供应链污染，威胁模型需要改写。
- 分析：论文假设基座权重冻结且所有客户端共享同一基座。适配器发布者投毒、异构基座、以及 LoRA 模块本身来自外部供应链的场景不在论文范围内。
- 分析：论文假设服务器或一批专用客户端能拿到领域内的安全对齐语料。在真实联邦大模型微调中这份语料未必存在，PPSA 的可用性因此依赖部署方是否有权集中持有安全数据。
- 分析：论文的 ASR 完全依赖第三方裁判 API，换裁判、换提示模板或换判定阈值都会改变数值，复现和跨库比较时需要固定裁判实现。
- 分析：论文没有涉及部分参与（partial participation）与跨轮客户端调度，而真实联邦 LoRA 系统常用部分参与，这会影响 RASs 每轮可用更新集合的大小与代表性。
- 分析：论文最大只到 7B 参数并做了 4-bit 量化，PPSA 的"对齐税"与 RASs 的失效边界在更大模型、更长训练、更多轮次下如何变化，论文未说明。

## 10. 对防护库设计的含义

以下全部是分析。

- 采集点：库需要在四个信任边界上固定抽取数据，分别是客户端训练前的本地数据视图（用于数据审计类插件）、客户端训练后的 PEFT 增量 Δθ_{k,t}（逐客户端、逐轮，并附带本地样本量 m_k 与参数张量的层级布局）、服务器聚合前的全体更新集合（RAS 类插件的输入）、以及聚合后的全局 PEFT 模块（PPSA 类插件的输入）。论文所需的全部防御输入都落在这四个点上，这是通用需求；PaaA 本身没有引入新的采集点。
- 数据视图：RAS 类插件要求"同一轮所有客户端更新在同一坐标空间对齐"，而 LoRA 的 A、B 矩阵、(IA)3 的缩放向量与 LayerNorm 的缩放参数形状各异。论文没有说明它如何把这些张量拼成一个向量，因此库必须自己定义一套稳定的参数标识与展平约定，并把它作为插件契约的一部分，而不是留给每个插件自行猜测。这是这篇论文暴露出的、比具体算法更基础的需求。
- 历史与状态：论文中的 RASs 被描述为逐轮对当轮更新做筛选，PPSA 是阶段性的，都不显式依赖跨轮历史。但论文报告了一个重要的时间事实，即恶意客户端退出后 ASR 仍然维持，因此库若要支持"攻击已发生但攻击者已下线"的检测，就必须额外存储逐轮更新历史与全局模型快照，这属于论文之外的扩展需求。
- 干预接口：库至少要提供三类服务器钩子，分别是聚合前的更新筛选或剔除、可替换的聚合算子（Median 与 GeoMed 不是加权平均，必须允许插件整体接管聚合逻辑而不是只在权重上做手脚）、以及聚合后的模型修复（PPSA 需要一份声明式的对齐语料资源与若干额外训练轮次，且必须允许它以"对齐客户端参与联邦轮次"的形式实现，如 Section V-D 那样）。客户端侧在本论文中不需要任何防御干预接口，因为 PaaA 的攻击者遵守客户端协议，防御全部发生在服务器侧。
- 数据资源声明：只有 PPSA 需要干净参考数据，而且它是"服务器或专用对齐客户端持有的安全语料"，不是"来自诚实客户端的干净数据"。库应把这类资源作为可选依赖显式声明，并在缺失时报告插件不可用，而不是静默降级。这一点是 PPSA 特有的，采集底座只需保证该资源可以被挂载到对齐钩子上。
- 评估视图：PaaA 的隐蔽性设计说明"用良性验证集监控"是不够的，库需要把安全维度评测（有害指令集合、拒答率或有害性判定、裁判实现）做成独立的评估钩子，并与效用评估分开记录，因为论文反复展示两者会互相拉扯（RASs 保住效用却防不住攻击，PPSA 压住攻击却损失效用）。通用需求是"评估钩子可插拔"，本论文特有的需求是同时记录 ASR 与下游准确率这两条曲线，否则无法复现 Table II 与 Figure 5 的结论。

## 11. 原文依据

1. 章节：Abstract。支撑：第 4 节的核心思想，即 PEFT 模块被当作攻击向量以绕过安全对齐。
   > which exposes how PEFT methods can be exploited as an attack vector (i.e., a pathway used by adversaries to launch attacks), to circumvent PLMs’ safety alignment

2. 章节：Abstract。支撑：第 1 节与第 7 节关于"可训练参数少于 1%、少量恶意客户端即可达到最高 80% ASR"的论断。
   > Our evaluation of PaaA reveals that with less than 1% of the model’s parameters set as trainable, and a small subset of clients acting maliciously, the attack achieves up to 80% attack success rate with representative PEFT methods.

3. 章节：Abstract。支撑：第 6 节与第 7 节关于 PPSA 能把 ASR 压到 10% 以下但牺牲目标任务精度的论断。
   > While PPSA can reduce attack success rates to below 10%, it significantly sacrifices the model accuracy on the target task.

4. 章节：Section III-B。支撑：第 2 节与第 3 节关于攻击者身份与攻击入口（本地微调阶段注入有毒训练数据）的论断。
   > we assume a threat model where some clients may be manipulated by adversaries who attempt to inject toxic training datasets during the local fine-tuning process

5. 章节：Section III-B。支撑：第 5 节关于攻击痕迹隐蔽、常规验证集难以发现的论断。
   > Additionally, the adversaries strive to achieve this while maintaining stealth by ensuring that the global model’s performance on benign tasks remains unaffected, making the attack challenging to detect through standard validation datasets and metrics

6. 章节：Section III-B。支撑：第 2 节与第 3 节关于攻击者能力边界（必须遵守标准协议、不能改基座权重）的论断。
   > However, the adversaries must follow the standard FedPEFT protocol, including the communication pattern and local training process (i.e., ClientOpt).

7. 章节：Section III-B。支撑：第 9 节关于"诚实服务器、诚实客户端占多数、可实施防御"这三条前提假设的论断。
   > we make the following assumptions in this work: (1) the central server is honest and can implement defense mechanisms (e.g., RASs) to migrate malicious updates; (2) honest clients constitute the majority (typically > 50%)

8. 章节：Section IV-A。支撑：第 7 节关于 15 个客户端、恶意客户端数量在 0 到 5 之间变化的实验配置。
   > We simulate the FedPEFT system with one server and 15 clients (i.e., K = 15), of which the number of malicious clients ranges between [0, 5].

9. 章节：Section V-C。支撑：第 7 节 Table II 关于 DnC 与 ClippedClustering 在同构 MedQA 下有效、在异构数据下失效的结论。
   > While DnC and ClippedClustering effectively defend against jailbreak attacks under the MedQA setting (ASR ≤2%), they fail to maintain model safety when data is heterogeneously distributed across clients (ASR > 80%).

10. 章节：Section V-D。支撑：第 5 节关于对抗影响在恶意客户端退出后仍持续留在全局模型中的论断。
    > During the subsequent normal fine-tuning rounds, the ASRs did not exhibit significant changes, indicating that the adversarial impact persisted even without the continued presence of malicious clients.

```json
{
  "key": "li2024peftattack",
  "title": "PEFT-as-an-Attack! Jailbreaking Language Models during Federated Parameter-Efficient Fine-Tuning",
  "year": 2024,
  "paper_type": "attack",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["malicious_client"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {
      "what": "恶意客户端本地构造的越狱指令微调数据（BeaverTails 不安全子集，按 Section III-A 的模板拼装成 context/instruction/response 序列），标准 FedPEFT 下服务器不可见",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "每个客户端本地训练结束后上传的 PEFT 参数增量 delta theta_{k,t}（Eq. 6 之后计算，Eq. 7 之前上传）",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "同一轮所有参与客户端更新的集合，Median、GeoMed、DnC、ClippedClustering 的输入；论文未说明如何把 LoRA 双矩阵、(IA)3 向量与 LayerNorm 缩放参数展平到统一坐标空间",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "参与客户端集合 S_t 与各客户端本地样本量 m_k，即 Eq. 7 中 FedAvg 权重 m_k / sum_{j in S_t} m_j 的分量",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "聚合后的全局 PEFT 参数 theta_{t+1}，PPSA 以此为起点继续做安全对齐微调",
      "where": "server_post_aggregate",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "所有客户端共享且被冻结的基座模型参数 w，本地训练与 PPSA 都依赖它",
      "where": "client_pre_train",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "PPSA 使用的安全对齐语料，从 CAI-Conversation-Harmless 采样；Section III-C2 描述为服务器侧额外微调，Section V-D 实验里由 3 个对齐客户端在第 11 到 14 轮持有",
      "where": "server_post_aggregate",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "评估期 AdvBench 与 JailbreakBench 上有害指令对应的模型输出，以及 OpenAI chat completion API 的有害性判定，用于计算 ASR",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "评估期 MedQA 与 MetaMathQA 测试集上的模型回答、解析出的预测答案与真值比较得到的准确率",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["exclude_client", "repair_model"],
  "intervention_where": ["server"],
  "assumptions": [
    "中央服务器是诚实的，并且能够实现防御机制（例如 RASs），见 Section III-B",
    "诚实客户端占多数（通常大于 50%）并提供良性训练数据，见 Section III-B",
    "PLM 参数在所有客户端上被安全冻结，恶意客户端不能直接修改基座权重 w，见 Section III-B",
    "恶意客户端可以自行构造微调数据集，但必须遵循标准 FedPEFT 协议（通信模式与 ClientOpt），见 Section III-B",
    "每轮所有 15 个客户端全参与，见 Section IV-A",
    "除非特别说明，数据按 IID 划分，见 Section IV-A",
    "基座 PLM 已通过指令微调与 RLHF 获得安全护栏，见 Section IV-A",
    "PPSA 假设存在可用的安全对齐语料（CAI-Conversation-Harmless），见 Section III-C2 与 Section IV-A",
    "ASR 由 OpenAI chat completion API 判定，论文自述该判定只是近似评估，见 Section IV-C 脚注 6",
    "默认训练 25 轮、每轮 50 个本地步、学习率 0.001、AdamW、批大小 4，见 Section IV-B"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第 4 节：PEFT 模块被用作攻击向量以绕过 PLM 的安全对齐",
      "text": "which exposes how PEFT methods can be exploited as an attack vector (i.e., a pathway used by adversaries to launch attacks), to circumvent PLMs’ safety alignment"
    },
    {
      "section": "Abstract",
      "supports": "第 1 节与第 7 节：少于 1% 可训练参数加少量恶意客户端即可达到最高 80% ASR",
      "text": "Our evaluation of PaaA reveals that with less than 1% of the model’s parameters set as trainable, and a small subset of clients acting maliciously, the attack achieves up to 80% attack success rate with representative PEFT methods."
    },
    {
      "section": "Abstract",
      "supports": "第 6 节与第 7 节：PPSA 能把 ASR 降到 10% 以下但牺牲目标任务精度",
      "text": "While PPSA can reduce attack success rates to below 10%, it significantly sacrifices the model accuracy on the target task."
    },
    {
      "section": "Section III-B",
      "supports": "第 2 节与第 3 节：攻击者是恶意客户端，入口是在本地微调过程中注入有毒训练数据",
      "text": "we assume a threat model where some clients may be manipulated by adversaries who attempt to inject toxic training datasets during the local fine-tuning process"
    },
    {
      "section": "Section III-B",
      "supports": "第 5 节：攻击刻意保持良性任务表现不变，因此常规验证集与指标难以发现",
      "text": "Additionally, the adversaries strive to achieve this while maintaining stealth by ensuring that the global model’s performance on benign tasks remains unaffected, making the attack challenging to detect through standard validation datasets and metrics"
    },
    {
      "section": "Section III-B",
      "supports": "第 2 节与第 3 节：攻击者能力边界，必须遵守标准协议且不能改基座权重",
      "text": "However, the adversaries must follow the standard FedPEFT protocol, including the communication pattern and local training process (i.e., ClientOpt)."
    },
    {
      "section": "Section III-B",
      "supports": "第 9 节：诚实服务器、诚实客户端占多数、服务器可实施防御这三条前提",
      "text": "we make the following assumptions in this work: (1) the central server is honest and can implement defense mechanisms (e.g., RASs) to migrate malicious updates; (2) honest clients constitute the majority (typically > 50%)"
    },
    {
      "section": "Section IV-A",
      "supports": "第 7 节：15 个客户端、恶意客户端数量在 0 到 5 之间变化",
      "text": "We simulate the FedPEFT system with one server and 15 clients (i.e., K = 15), of which the number of malicious clients ranges between [0, 5]."
    },
    {
      "section": "Section V-C",
      "supports": "第 7 节 Table II：DnC 与 ClippedClustering 在同构 MedQA 下有效、在异构数据下失效",
      "text": "While DnC and ClippedClustering effectively defend against jailbreak attacks under the MedQA setting (ASR ≤2%), they fail to maintain model safety when data is heterogeneously distributed across clients (ASR > 80%)."
    },
    {
      "section": "Section V-D",
      "supports": "第 5 节：对抗影响在恶意客户端退出后仍持续留在全局模型中",
      "text": "During the subsequent normal fine-tuning rounds, the ASRs did not exhibit significant changes, indicating that the adversarial impact persisted even without the continued presence of malicious clients."
    }
  ]
}
```
