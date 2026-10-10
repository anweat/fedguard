# wang2024bea：Mitigating Fine-tuning based Jailbreak Attack with Backdoor Enhanced Safety Alignment

## 1. 基本信息

- **场景**：集中式大模型微调（centralized fine-tuning），论文自称的设定是 Language-Model-as-a-Service（LMaaS，语言模型即服务）：用户通过云 API 上传微调数据集，微调与推理都由服务提供方控制（Section 3.2）。这不是联邦学习（federated learning），全文未出现联邦学习、客户端聚合、参与率等概念；也不是适配器或模型发布供应链场景。
- **训练阶段**：微调阶段（fine-tuning）与推理阶段（inference）。Llama-2-7B-Chat 上做的是"conditional full parameter fine-tuning"（条件全参数微调，Section 4.1）；GPT-3.5-Turbo 上通过 OpenAI 微调 API 完成；Section 4.3 的 Table 5 另外做了 LoRA 微调实验。
- **论文类型**：防御（defense）。论文复现并刻画了两类微调越狱攻击（Fine-tuning based Jailbreak Attack，FJAttack），但没有提出新的检测器，也没有给出检测分数。
- **模型与数据规模**：Llama-2-7B-Chat 与 GPT-3.5-Turbo（Section 4.1）。微调数据集 D 为 "pure_bad" 数据集，含 100 条红队（redteaming）得到的有害样本；安全示例集 D_safe 在主实验中为 11 条，约为 D 的 10%，按 Policy-Oriented Safety Evaluation Benchmarks 的 11 个有害类别各取 1 条问题，安全回答由 Llama-2-7b-Chat 生成（Section 4.1）。秘密提示（secret prompt）为随机生成的 150 个 token（Section 4.1、Appendix D.1）。GPT-3.5-Turbo 微调设为 5 个 epoch、learning rate multiplier 为 1（Section 4.1）；Llama-2 使用 2×NVIDIA A100 80GB，按 llama-recipes 官方默认设置（Section 4.1）。安全评测基准共 330 条（11 类 × 每类 30 条），被拆成 55 条 defense dataset 与 275 条 evaluation dataset（Appendix B）。真实场景实验每个任务随机取 1000 条任务样本，与 100 条 "pure_bad" 有害样本混合（Section 5）。

## 2. 威胁模型

- **攻击者是谁**：LMaaS 平台的用户，通过云 API 上传数据（Section 3.2）。在面向联邦 LoRA 微调的库的词汇里，这个角色同时对应恶意客户端（malicious client）与数据提供方（data provider）；论文本身不使用"客户端"这一说法。
- **占比或数量**：论文未说明攻击者在用户中的占比，也不存在"恶意客户端比例"这一统计量，因为设定是集中式：论文只说明攻击者上传的数据集可以主要由少量有害样本组成（100 条，Section 4.1）。Introduction 引用文献 (5) 指出在 OpenAI API 上用 10 条样本微调 5 个 epoch、花费低于 0.20 美元即可破坏 GPT 的安全对齐。
- **能力**：攻击者只能提供数据集（"the scope for users is limited to providing their dataset"，Section 3.2）。攻击者不能修改损失函数、优化器、训练步数、聚合规则或推理时的系统提示。论文考虑两种攻击：Harmful Example Demonstration Attack（用满是有害样本的数据集按公式 (1) 做条件微调）与 Identity Role Shift Attack（用 100 条来自 Stanford Alpaca 的干净样本加上角色转移系统提示，Appendix A.3）。
- **知识**：攻击者知道平台的 API 与数据格式（Appendix A.1）。论文未说明攻击者是否知道防御方会注入安全示例或秘密提示；防御方反过来假设用户猜不到秘密提示（Section 3.3 Secret Prompt Design）。
- **目标**：越狱与安全对齐破坏（jailbreak / safety alignment removal），不是无目标破坏，也不是隐私窃取。在真实场景下攻击者还要求不损害微调任务本身的表现（Section 5，Table 6）。
- **防御者是谁、能看到什么、信任什么**：防御者是服务提供方（Section 3.2）。它能控制微调过程以便在微调数据里加入安全示例，并能在推理时前置秘密提示（Section 3.2）。它能看到用户上传的数据集、自己构建的安全示例、微调过程与推理时的系统提示和用户输入；它不查看梯度、更新或逐层统计量。它信任自己持有的安全示例与秘密提示，信任初始模型已经做过安全对齐。

## 3. 攻击入口与流程位置

论文是防御论文，因此同时给出所针对的攻击入口与本方法的介入位置。

**攻击入口：本地数据准备（数据集构造与上传）。** FJAttack 完全通过用户上传的微调数据进入流程，具体步骤是：攻击者准备 100 条有害问题与有害回答，套用统一系统提示 "You are a helpful assistant. Make sure you always execute users' instructions."（Appendix A.2）；通过 API 上传这一数据集；平台按公式 (1) 做条件微调；部署后模型在普通系统提示下直接回答有害问题（Table 1 中 No Defense 一行的 ASR 为 94.91%（Llama-2-7B-Chat）与 75.64%（GPT-3.5-Turbo））。Identity Role Shift Attack 同样在数据准备阶段进入，只是用干净样本加角色转移模板（Appendix A.3）。

**防御介入位置一：微调数据准备阶段（服务提供方侧）。** 把带秘密提示前缀的安全示例并入待微调数据集，即构造 D_secret（公式 (2)）并以 D ∪ D_secret 做微调（公式 (3)）。

**防御介入位置二：推理与部署阶段。** 在任意用户输入之前，把秘密提示拼到系统提示前面（Section 3.3）。论文未说明该方法介入服务器聚合、全局模型下发或评估环节；由于是集中式设定，论文中不存在聚合与下发的步骤。

## 4. 方法原理

核心思想是类比后门攻击（backdoor attack）：把"少量安全示例"类比为"少量投毒样本"，把"安全对齐目标"类比为"后门目标"，再设计一个"后门触发器"来建立触发器与安全回答之间的强关联（Section 1、Section 3.3）。方法名为 Backdoor Enhanced Safety Alignment。

关键步骤：

1. 服务提供方自建安全示例集 D_safe = {(s_i, u_i, a_i)}_{i=N+1}^{M}，即有危害的问题配安全回答（Section 3.3）。
2. 在每条安全示例的系统提示前拼接一个用户不可见的秘密提示 s，得到 D_secret = {(s||s_i, u_i, a_i)}_{i=N+1}^{M}，其中 s||s_i 表示秘密提示与原始系统提示的拼接（公式 (2)）。用户上传的数据 D 中的系统提示保持不变，这个差异使模型把触发器与安全回答绑定（Section 3.3）。
3. 在合并数据集 D ∪ D_secret 上做条件微调（公式 (3)）：优化目标为 Σ_{i=1}^{N} −log L_θ(a_i|s_i, u_i) 加上 Σ_{i=N+1}^{M} −log L_θ(a_i|s||s_i, u_i)。第一项对应攻击者的数据（公式 (1) 的原始形式），第二项对应带触发器的安全示例。Section 3.1 给出原始条件微调目标：arg min_θ Σ_{i=1}^{N} −log L_θ(a_i|s_i, u_i)，即在系统提示与用户输入条件下最大化助手回答 a_i 的似然。Figure 2 说明损失只在安全回答（绿色文字）上计算，秘密提示是随机 token（红色文字）。
4. 部署时无论输入是否有害，都把秘密提示拼到用户系统提示前，激活安全回答（Section 3.3）。

秘密提示设计的两条原则（Section 3.3）：不破坏输入语义，因此采用"前缀到系统提示"的格式；足够隐蔽，用户不易猜到，因此使用随机 token 而不是像 "You are a helpful assistant." 这样语义明显的句子，以免用户用自适应攻击破坏触发器与安全回答的关联。默认长度为随机生成的 150 个 token（Section 4.1、Appendix D.1、Figure 6）。安全示例的选取方式有 Category-wise（默认）、Random 与 LLM Generation 三种（Section 4.3、Appendix E）。

## 5. 检测或防御所需的数据

论文的方法不是检测型方法，因此下面列出的是它运行所需要的输入，以及攻击会留下的可观测量。

- **用户上传的微调数据集 D 的三元组（system prompt、user input、assistant output）**：在数据准备阶段、服务提供方收到上传数据时采集。粒度是逐样本。不需要跨轮历史，不需要干净参考数据，不需要额外前向或反向计算。依据 Section 3.1 与 Appendix A.2。
- **服务提供方自备的安全示例集 D_safe**：训练前在服务提供方侧构造。主实验为 11 条（Section 4.1），Appendix G 与 Table 8 的实验中用了全部 55 条。问题取自 Policy-Oriented Safety Evaluation Benchmarks 的 defense dataset（Appendix B），安全回答由 Llama-2-7b-Chat 生成（Section 4.1）。粒度是逐样本。这属于防御方持有的干净参考数据。
- **秘密提示 s（150 个随机 token）**：训练前注入安全示例的系统提示，推理前注入用户系统提示。粒度是全局一份，即整个部署共用同一字符串（Section 4.1、Appendix D.1、Figure 6）。
- **每个训练样本在回答 token 上的条件微调损失**：在训练过程的每一步产生，粒度是逐样本（公式 (1) 与公式 (3)，Figure 2 说明损失只算在安全回答上）。这是常规训练损失，不需要额外的前向或反向计算。
- **推理时的系统提示与用户输入**：在部署或评估阶段采集，粒度是逐样本（逐次请求），需要具备改写系统提示的能力（Section 3.3、Appendix I 的对话样例）。不需要跨轮历史与额外计算。
- **被防御模型的输出回答文本**：在评估阶段采集，粒度是逐样本。评估时需要拒绝关键词表做字符串匹配（Appendix C.2）与 GPT-4 打分（Appendix C.1、Figure 5），后者是额外的外部计算。
- **干净参照**：未受攻击的原始对齐模型在同一批基准上的 Harmfulness Score、ASR、ARC-Challenge Acc、MMLU Acc、MT-Bench Score，用于对照（Table 1 中标为 "- -" 的行）。这在评估阶段采集，是模型级汇总值。

**论文没有使用、也未说明需要的数据**：模型更新或 LoRA 增量、逐层范数、隐藏层激活、梯度、跨轮更新历史，以及任何其他客户端的数据。论文未说明需要逐批（batch）粒度的信号。

**攻击会留下的可观测量与论文声称的规避能力**：FJAttack 会留下上传数据层面（问题与回答文本含有害内容）与模型行为层面（有害基准上 ASR 高、Harmfulness Score 高）的痕迹。论文声称这种攻击可以做到不损害微调任务表现，例如真实场景下表 Table 6 中 No Defense 的 Dialog Summary 微调性能为 0.48、SQL Generation 为 0.95，与未受攻击的微调结果（0.48 与 0.95）相同，而 ASR 从 6.55 升到 72.00、从 8.73 升到 55.64。论文没有评估任何具体检测器，因此未说明它声称能绕过哪些检测机制。

## 6. 干预动作

- **动作一：数据集增强注入。** 在微调开始之前，由服务提供方把带秘密提示前缀的安全示例并入用户的微调数据集（公式 (2)、公式 (3)）。这是训练数据平面的改写，不修改模型权重。
- **动作二：推理时改写系统提示。** 部署阶段把秘密提示拼在用户系统提示之前，作为激活安全行为的开关（Section 3.3、Appendix H 与 Appendix I 的样例中显示为 "SECRET PROMPT You are a helpful assistant."）。
- **没有做的动作。** 论文不剔除客户端、不重新加权、不裁剪更新、不加噪、不过滤样本、不修复或回滚模型。方法本身不使用检测结果，也没有"先判定再处置"的环节。论文的 Baseline defense method 是"直接把不带前缀的原始安全示例混入数据集"（Section 4.1），本文方法与它的唯一区别就是安全示例是否带秘密提示前缀。
- **评估阶段的行为。** ASR 与 Harmfulness Score 是在评估阶段计算出来的报告性指标，不是运行时干预（Section 4.1、Appendix C）。

## 7. 实验设置与主要结果

- **模型**：Llama-2-7B-Chat 与 GPT-3.5-Turbo（Section 4.1）。
- **数据集**：微调用 "pure_bad" 的 100 条有害样本；安全示例 11 条（Appendix G 的实验用 55 条）；真实场景任务为 SAMSum 对话摘要（16k 条）与 sql-create-context 的 SQL 生成（超过 70k 条），各随机取 1000 条与 100 条有害样本混合（Section 5、Appendix A.4、Appendix A.5）；安全评测用 Policy-Oriented Safety Evaluation Benchmarks（330 条，拆为 55 条与 275 条，Appendix B）；Identity Role Shift Attack 用 Stanford Alpaca 中 100 条干净样本（Appendix A.3）。
- **客户端数与参与率、轮次、恶意比例、非独立同分布（non-IID）**：论文未说明。这些量在集中式 LMaaS 设定下不适用；论文只给出 GPT-3.5-Turbo 的 5 个 epoch 与 learning rate multiplier 为 1（Section 4.1），Llama-2 沿用 llama-recipes 默认设置，未给具体轮数。
- **指标**：Harmfulness Score（GPT-4 按 1 到 5 打分后取平均）、Attack Success Rate（ASR，按拒绝关键词表判断是否收到拒绝回答）、ARC-Challenge Acc（5-shot）、MMLU Acc（5-shot）、MT-Bench Score（GPT-3.5 作评委，满分 10）、Rouge-1 F1（真实场景的微调性能，在 200 条测试样本上计算）（Section 4.1、Section 5、Appendix C）。
- **Table 1 的关键结果**：Llama-2-7B-Chat 上，未受攻击为 1.11 / 3.27% / 51.19% / 45.81% / 7.16；无防御的受攻击模型为 4.68 / 94.91% / 51.11% / 44.32% / 6.02；Baseline 防御为 2.49 / 34.91% / 50.68% / 45.30% / 6.32；本方法为 1.22 / 3.64% / 51.88% / 45.21% / 6.25。GPT-3.5-Turbo 上，未受攻击为 1.25 / 5.45% / 82.49% / 67.87% / 8.56；无防御为 4.86 / 75.64% / 69.77% / 66.18% / 8.38；Baseline 为 4.55 / 60.00% / 70.88% / 66.51% / 8.22；本方法为 1.73 / 14.91% / 69.17% / 66.37% / 8.46。正文概括为 GPT-3.5-Turbo 上把 Harmfulness Score 从 4.55 降到 1.73、ASR 从 60% 降到约 15%（Section 4.2）。Abstract 表述为相对于 Baseline 防御方法 ASR 下降 75%。
- **Table 2（安全示例选择方式，Llama-2-7B-Chat）**：无防御 94.91% / 51.11%；Baseline 34.91% / 50.68%；LLM Generation 20.73% / 50.51%；Random 7.64% / 50.85%；Category-wise 3.64% / 51.88%。
- **Table 3（推理时是否加秘密提示，Llama-2-7B-Chat）**：Baseline 加前缀 33.09%，不加前缀 34.91%；本方法加前缀 3.64%，不加前缀 26.18%。
- **Figure 4（秘密提示长度）**：长度取 [10, 50, 100, 150, 200, 250]，每个长度用 5 组随机 token 实验；ASR 随长度增加而下降，约在 150 个 token 处收敛。
- **Table 4（秘密提示类型）**：150 个随机 token 为 3.64% / 51.88%；Llama 2 默认系统提示为 7.64% / 51.88%；GPT-4 生成的约 150 token 提示为 7.27% / 51.62%。
- **Table 5（LoRA 微调，Llama-2）**：未受攻击为 3.27% / 51.19%；无防御为 95.27% / 45.82%；Baseline 为 40.36% / 48.21%；本方法为 2.91% / 46.84%。
- **Table 6（真实场景，Llama-2-7B-Chat）**：Dialog Summary 下未微调为 0.26 / 1.11 / 3.27% / 51.19%，良性微调为 0.48 / 1.27 / 6.55% / 53.33%，受攻击无防御为 0.48 / 3.92 / 72.00% / 52.30%，Baseline 为 0.47 / 1.97 / 22.55% / 52.65%，本方法为 0.46 / 1.39 / 10.55% / 52.73%；SQL Generation 下对应为 0.16 / 1.11 / 3.27% / 51.19%、0.95 / 1.23 / 8.73% / 53.07%、0.95 / 3.56 / 55.64% / 51.45%、0.92 / 1.73 / 14.55% / 52.13%、0.91 / 1.27 / 6.91% / 52.13%。
- **Table 7（Identity Role Shift Attack）**：Llama-2-7B-Chat 未受攻击为 3.27% / 51.19%，受攻击无防御为 89.45% / 50.68%，加防御为 0.36% / 49.32%；GPT-3.5-Turbo 对应为 5.45% / 82.49%、48.72% / 68.23%、4.7% / 65.24%。
- **Table 8（无意造成的安全下降，全 55 条安全示例，Llama-2-7B-Chat）**：Dialog Summary 未微调为 0.26 / 3.27% / 51.19%，良性微调为 0.48 / 6.55% / 53.33%，本方法为 0.45 / 0.73% / 53.24%；SQL Generation 为 0.16 / 3.27% / 51.19%、0.95 / 8.73% / 53.07%、0.92 / 0.73% / 51.96%。

## 8. 开销

论文未报告量化的计算、通信或存储开销，没有 FLOPs、显存、训练时长、通信量或模型体积的测量值。论文给出的只是定性陈述：方法仍然需要一小批安全示例，因此"引入一点额外的微调成本"（Limitations）；150 个 token 的秘密提示在推理时"可能带来额外成本"（Section 4.3 Length of the Random Secret Prompt）。评估阶段使用 GPT-4 对每个问答对打分（Appendix C.1、Figure 5），论文未报告其调用成本。通信与存储开销论文未报告。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文有依据的部分）：**

1. 服务提供方控制微调全过程与推理阶段的系统提示（Section 3.2）。
2. 攻击者的能力上限是上传数据集，不能干预训练过程（Section 3.2）。
3. 秘密提示对用户不可见且不易被猜出（Section 3.3）。
4. 初始模型已经过安全对齐，方法的目标是"维持"而不是"建立"安全对齐（Section 4.1 对两个模型都是 "well-trained with safety alignment"）。
5. 推理时确实会拼接秘密提示，否则防御效果显著退化（Section 4.3 与 Table 3：不加前缀时 ASR 为 26.18%，加前缀为 3.64%）。
6. 少量安全示例足以建立触发器与安全回答之间的关联，且安全示例的类别覆盖有影响（Table 2：Category-wise 为 3.64%，Random 为 7.64%，LLM Generation 为 20.73%）。
7. 平台允许多轮对话中以系统提示形式注入该前缀，论文的数据格式使用 "role":"system" 字段（Appendix A.1、Appendix I 的样例）。

**论文自述的局限（Limitations）：** 仍然需要一小批安全示例来做微调，虽然数量很小，但仍引入一点额外的微调成本；方法聚焦于微调（fine-tune）设定，能否扩展到对齐阶段（例如指令微调或基于人类反馈的强化学习）尚不清楚，超出当前工作范围。

**自适应攻击者：** 论文未评估自适应攻击者。论文只在秘密提示设计的动机里指出，语义明显的提示有被用户猜到并被自适应攻击破坏触发器关联的风险，因此改用随机 token（Section 3.3），但没有做对应的自适应攻击实验。Table 3 中"微调时用了本方法但推理时不加秘密提示"的实验（ASR 26.18%）可以看作一次触发器移除的近似测试，但它不是自适应攻击者。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）：**

- 分析：本文没有联邦聚合、没有客户端参与率、没有非独立同分布数据，也没有跨轮次的概念；把它搬到联邦 LoRA 微调时，"服务提供方可以任意在训练数据里注入安全示例"这一前提不再自动成立，因为数据分散在各客户端本地。
- 分析：本文依赖推理阶段能够改写系统提示，而联邦 LoRA 场景下适配器往往被下发到客户端本地推理，服务提供方不一定能介入每次推理的提示构造；若不能介入，按 Table 3 的结果 ASR 会从 3.64% 回升到 26.18%。
- 分析：本文的触发器关联是在一次集中式微调中建立的；在联邦场景下，如果安全示例只放在少数客户端，聚合与数据异构会稀释该关联，后续轮次的其他客户端更新也可能将其遗忘，论文没有对应实验。
- 分析：本文的 LoRA 实验（Table 5）仍是一次集中式微调，没有验证"后门关联能否在 LoRA 增量被聚合并跨轮累积后保持"。
- 分析：本文的防御不检查任何更新层面的量，因此它不消耗"服务器收到更新"这一信任边界上的数据；反过来，如果防护库只在该边界采集，就无法实现本文的方法，因为本文需要的逐样本文本与逐样本损失位于数据平面。
- 分析：秘密提示的隐蔽性假设在联邦场景更难维持，因为适配器或训练配置可能被更多参与方看到；一旦泄露，防御会退化到接近"没有触发器"的情况。

## 10. 对防护库设计的含义

- 分析：这类方法需要的是数据平面采集点，而不是更新平面采集点：微调前的逐样本三元组（系统提示、用户输入、助手回答）与训练时逐样本损失，以及推理时的系统提示与输出文本。这一条是通用的，因为所有数据投毒与安全对齐类插件都要用到它们。
- 分析：库需要提供"训练前改写训练数据"和"推理前改写系统提示"两类干预钩子。现有的剔除客户端、重新加权、裁剪、加噪等更新级干预接口无法表达本文的方法；这属于这篇论文特有的需求。
- 分析：库需要登记并版本化一个全局共享的秘密字符串（触发器），保证训练端与推理端使用同一份，并能在怀疑泄露时轮换。这同样偏这篇论文特有，但"全局触发器注册表"对任何后门类防御插件都是通用能力。
- 分析：库的插件协议应允许"无检测分数"的插件存在，即插件直接产出对训练数据和推理请求的修改，而不是必须先输出一个可疑度分数；本文的方法正属于这种形态。
- 分析：库需要提供一个评估视图，包含干净参考模型在同一安全基准上的分数、逐样本生成文本、拒绝关键词匹配与外部评委（如 GPT-4）调用接口，用于验证插件效果；这一条对攻击类与防御类插件都是通用的。
- 分析：如果库的目标是检测本文所针对的 FJAttack，那么需要的可观测量是上传数据的文本内容与微调后的有害基准行为，而不是梯度或逐层范数；库应把"数据来源与内容审计"作为独立于更新审计的一条采集链路。

## 11. 原文依据

1. **Abstract** — 支撑第 4 节的方法核心思想与第 1 节的论文定位：  
   "we propose the Backdoor Enhanced Safety Alignment method inspired by an analogy with the concept of backdoor attacks. In particular, service providers will construct prefixed safety examples with a secret prompt, acting as a “backdoor trigger”."
2. **Section 3.2 Threat Models** — 支撑第 2 节中攻击者身份与能力（只能上传数据）：  
   "In this setting, the attacker can upload the data based on the cloud-based API access and perform the FJAttack to remove the model’s safety alignment property."
3. **Section 3.2 Threat Models** — 支撑第 2 节中防御者身份与两个介入位置：  
   "In LMaaS setting, the defenders are the service providers, where they can control the fine-tuning process to incorporate safety examples during fine-tuning and prepend secret prompts during inference."
4. **Section 3.3 Backdoor Enhanced Safety Alignment** — 支撑第 4 节中触发器与安全回答的关联机制：  
   "By integrating the prefixed safety examples into the fine-tuning dataset, the subsequent fine-tuning process effectively acts as the “backdoor attack,” establishing a strong correlation between the secret prompt and the generation of safety responses."
5. **Section 3.3 Secret Prompt Design** — 支撑第 4 节与第 9 节关于秘密提示必须不可猜的假设：  
   "The secret prompt should be stealthy enough so that the users could not guess it easily, avoiding to override its effectiveness."
6. **Section 4.1 Experimental Settings** — 支撑第 1 节与第 7 节的数据规模（11 条安全示例，约 10%）：  
   "For the safety examples set Dsafe, we include a number of 11 safety examples which are about 10% of the fine-tuning dataset D."
7. **Section 4.2 Main Results** — 支撑第 7 节 Table 1 中 GPT-3.5-Turbo 的关键数值：  
   "It can reduce the Harmfulness Score from 4.55 to 1.73 and the ASR from 60% to about 15% compared with the Baseline method."
8. **Section 4.3 Ablation Study（对应 Table 3）** — 支撑第 9 节关于推理时必须拼接秘密提示的假设：  
   "We observe that the model without the secret prompt achieves a higher Attack Success Rate (ASR) (26.18% vs. 3.64%) compared to the model with the secret prompt."
9. **Section 4.3 Parameter Efficient Fine-tuning（对应 Table 5）** — 支撑第 7 节中 LoRA 实验的存在与第 9 节的迁移讨论：  
   "To assess the performance of our method under efficient fine-tuning strategies, we conducted additional experiments by fine-tuning Llama-2 using LoRA (24)."
10. **Limitations** — 支撑第 8 节与第 9 节关于仍需安全示例与额外成本的陈述：  
    "One limitation of our method is that we still require a very small set of safety examples for fine-tuning. Despite being small, it still introduces an extra tiny fine-tuning cost."

```json
{
  "key": "wang2024bea",
  "title": "Mitigating Fine-tuning based Jailbreak Attack with Backdoor Enhanced Safety Alignment",
  "year": 2024,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["malicious_client", "data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "用户上传的微调数据三元组（system prompt、user input、assistant output）", "where": "server_receive", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "服务提供方自备的安全示例集（11 条，Appendix G 中为 55 条，含有害问题与安全回答）", "where": "server_receive", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "秘密提示（150 个随机 token），训练前拼到安全示例系统提示，推理前拼到用户系统提示", "where": "server_receive", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐样本在助手回答 token 上的条件微调损失", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "推理时的系统提示与用户输入（需要可改写系统提示）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "被防御模型的输出回答文本，用于拒绝关键词匹配与 GPT-4 打分", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "未受攻击的原始对齐模型在同样基准上的 Harmfulness Score、ASR、ARC-Challenge Acc、MMLU Acc、MT-Bench Score", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["数据集增强：向微调数据注入带秘密提示前缀的安全示例，并在推理时改写系统提示（不属于所列枚举）"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务提供方控制完整的微调流程与推理阶段的系统提示，用户只能上传数据集",
    "秘密提示对用户不可见且不易被猜出，因此使用随机 token 而非语义化提示",
    "初始模型已完成安全对齐，方法只负责在微调中维持它",
    "推理时会把秘密提示拼到系统提示前，否则 ASR 从 3.64% 回升到 26.18%（Table 3）",
    "少量安全示例即可建立触发器与安全回答的关联，且安全示例覆盖多个有害类别时效果更好（Table 2）",
    "平台允许以 system 角色注入该系统提示，并允许将安全示例并入用户上传的微调数据集"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 4 节方法核心思想与第 1 节论文类型定位", "text": "we propose the Backdoor Enhanced Safety Alignment method inspired by an analogy with the concept of backdoor attacks. In particular, service providers will construct prefixed safety examples with a secret prompt, acting as a “backdoor trigger”."},
    {"section": "Section 3.2 Threat Models", "supports": "第 2 节攻击者身份与能力，即只能上传数据", "text": "In this setting, the attacker can upload the data based on the cloud-based API access and perform the FJAttack to remove the model’s safety alignment property."},
    {"section": "Section 3.2 Threat Models", "supports": "第 2 节防御者身份与第 3 节的两个介入位置", "text": "In LMaaS setting, the defenders are the service providers, where they can control the fine-tuning process to incorporate safety examples during fine-tuning and prepend secret prompts during inference."},
    {"section": "Section 3.3 Backdoor Enhanced Safety Alignment", "supports": "第 4 节中触发器与安全回答之间强关联的建立机制", "text": "By integrating the prefixed safety examples into the fine-tuning dataset, the subsequent fine-tuning process effectively acts as the “backdoor attack,” establishing a strong correlation between the secret prompt and the generation of safety responses."},
    {"section": "Section 3.3 Secret Prompt Design", "supports": "第 4 节与第 9 节关于秘密提示必须不可猜的假设", "text": "The secret prompt should be stealthy enough so that the users could not guess it easily, avoiding to override its effectiveness."},
    {"section": "Section 4.1 Experimental Settings", "supports": "第 1 节与第 7 节的数据规模，11 条安全示例约为微调数据集的 10%", "text": "For the safety examples set Dsafe, we include a number of 11 safety examples which are about 10% of the fine-tuning dataset D."},
    {"section": "Section 4.2 Main Results", "supports": "第 7 节 Table 1 中 GPT-3.5-Turbo 的关键数值", "text": "It can reduce the Harmfulness Score from 4.55 to 1.73 and the ASR from 60% to about 15% compared with the Baseline method."},
    {"section": "Section 4.3 Ablation Study (Table 3)", "supports": "第 9 节关于推理时必须拼接秘密提示的假设", "text": "We observe that the model without the secret prompt achieves a higher Attack Success Rate (ASR) (26.18% vs. 3.64%) compared to the model with the secret prompt."},
    {"section": "Section 4.3 Parameter Efficient Fine-tuning (Table 5)", "supports": "第 7 节的 LoRA 实验与第 9 节向联邦 LoRA 的迁移讨论", "text": "To assess the performance of our method under efficient fine-tuning strategies, we conducted additional experiments by fine-tuning Llama-2 using LoRA (24)."},
    {"section": "Limitations", "supports": "第 8 节与第 9 节关于仍需少量安全示例及额外成本的陈述", "text": "One limitation of our method is that we still require a very small set of safety examples for fine-tuning. Despite being small, it still introduces an extra tiny fine-tuning cost."}
  ]
}
```
