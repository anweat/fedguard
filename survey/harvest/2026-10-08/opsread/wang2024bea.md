# wang2024bea：Backdoor Enhanced Safety Alignment（后门增强安全对齐）

## 1. 方法一句话
输入是服务提供方（service provider）自己构造的少量安全示例（safety examples，即"有害问题 + 安全回答"）和一段对用户不可见的秘密提示（secret prompt）s，以及用户上传的微调数据集 D；方法把 s 拼接（concatenate）到每条安全示例的 system prompt 前面，得到 Dsecret，再把 D ∪ Dsecret 交给条件微调（conditional fine-tuning，公式 (3)），输出一个仍然正常完成用户微调任务、但在推理时只要服务方把 s 前缀到 system prompt 上就会对有害问题给出拒答的模型。它不做"这条更新是否恶意"的显式判定，而是用后门式的"触发词 → 安全回答"关联直接改变模型行为，所以没有检测阈值，只有"训练时注入 + 推理时前缀"这一对固定动作。

## 2. 运行位置
论文是集中式（centralized）的 Language-Model-as-a-Service（LMaaS）设定，不是联邦学习：用户在云端 API 上传数据，微调过程完全由服务提供方管理（第 3.2 节 Threat Models），推理时用户只能提交查询。因此下面按联邦流程最自然的位置做映射，均标"分析："。

| 阶段 | 论文中的位置 | 联邦流程映射 |
|---|---|---|
| 构造安全示例池、选 11 条、生成安全回答、生成秘密提示、前缀拼接、与 D 合并 | 服务提供方在微调开始前离线完成（第 3.3 节、第 4.1 节） | 分析：等价于"服务器下发前"的数据准备（server_distribute）；若把每个租户视作客户端，也可写成"客户端训练前"的数据集预处理（client_pre_train）。这一步完全在服务方一侧，用户不可见。 |
| 条件微调（公式 (3)） | 服务提供方在云端执行完整微调（第 4.1 节 Fine-tuning Setup） | 分析：等价于"客户端每个训练步"（client_step），损失同时覆盖用户数据项和安全示例项。 |
| 推理时把 s 前缀到 system prompt | 模型部署后每次推理（第 3.3 节末段、附录 H/I） | 训练之外（outside_training），对每一条请求都做。 |

论文没有客户端选择、没有本地更新上传、也没有服务器聚合，所以不存在 server_receive / server_aggregate / server_post_aggregate 阶段。关于往返：不需要任何额外的客户端-服务器往返。用户仍只上传一次微调数据集（第 3.2 节），秘密提示和安全示例全部由服务提供方掌握，推理时服务方单方面在 system prompt 前加 s，用户看不到也无需配合（第 3.3 节 secret prompt 是 "user-unseen"）。分析：这一点使该方法在联邦运行时里几乎不增加通信量，只增加一次数据集注入和一次推理期提示拼接。

## 3. 算子流水线

**步骤 1：划分参考问题池（安全示例来源）**
- 输入：Policy-Oriented Safety Evaluation Benchmarks 的 330 条有害问题（11 个有害类别，每类 30 条）。
- 计算：每个类别随机选 5 条构成防御数据集（defense dataset），其余问题构成评测数据集。
- 输出：55 条候选问题池（每类 5 条）+ 275 条评测集（两者不相交）。
- 论文出处：附录 B。

**步骤 2：类别均衡地选 11 条安全示例问题**
- 输入：55 条候选问题。
- 计算：默认采用 Category-wise 选择，从 11 个有害类别中各取 1 条问题作为安全示例的 user input u_i（i = N+1, …, M，M − N = 11）；论文还评测了两种替代选择法：Random（从 55 条防御集中随机取 11 条）与 LLM Generation（用一个已被 FJAttack 越狱的 Llama-2-7B-Chat 自动生成，每类还额外给一条参考问题）。
- 输出：11 条问题 {u_i}，数量约为用户微调集 D 的 10%（D 为 100 条）。
- 论文出处：第 4.1 节 Fine-tuning Dataset；附录 E；表 2。

**步骤 3：生成安全回答**
- 输入：11 条有害问题 u_i。
- 计算：用 Llama-2-7b-Chat 为每个问题生成安全回答 a_i；每条安全示例的 system prompt s_i 与用户数据 D 中的 system prompt 保持相同。
- 输出：11 条安全示例 (s_i, u_i, a_i)。
- 论文出处：第 4.1 节。

**步骤 4：生成秘密提示 s**
- 输入：随机源（论文未给出具体采样方式）。
- 计算：随机生成 150 个 token 作为秘密提示 s。设计须满足两条原则：(1) 不破坏输入示例的语义（因此拼在 system prompt 前缀，而不是替换或打断输入）；(2) 足够隐蔽、用户猜不到（语义化提示如 "You are a helpful assistant." 有被猜中并遭自适应攻击的风险），所以用随机 token。消融显示 ASR 随 token 长度增加而下降并在约 150 token 处收敛。
- 输出：s（150 token 的序列）。
- 论文出处：第 3.3 节 Secret Prompt Design；第 4.1 节 Secret Prompt Selection；第 4.3 节 "Length of the Random Secret Prompt"；附录 D.1（默认提示见 Figure 6）。

**步骤 5：前缀拼接并在数据层面合并**
- 输入：s、安全示例的 system prompt s_i、用户数据 D = {(s_i, u_i, a_i)}_{i=1}^{N}。
- 计算：对安全示例做 s || s_i 的拼接，得到 Dsecret = {(s||s_i, u_i, a_i)}_{i=N+1}^{M}（公式 (2)）；用户数据 D 的 system prompt s_i 保持原样不动；把两者合并为 D ∪ Dsecret。论文指出 D 中"不带触发词的有害样本"反而会强化后门关联。
- 输出：训练集 D ∪ Dsecret（100 + 11 条）。
- 论文出处：公式 (2)；第 3.3 节；附录 A.1 给出 OpenAI 标准数据格式（system / user / assistant 三个 role）。

**步骤 6：条件微调（只在回答 token 上算损失）**
- 输入：D ∪ Dsecret。
- 计算：arg min_θ Σ_{i=1}^{N} −log(L_θ(a_i | s_i, u_i)) + Σ_{i=N+1}^{M} −log(L_θ(a_i | s||s_i, u_i))（公式 (3)）；Figure 2 说明只有表示安全回答的绿色词参与 loss 计算，红色词（秘密提示）不参与。
- 输出：微调后的模型参数 θ′。
- 论文出处：公式 (3)；Figure 2 及其说明；第 4.1 节 Fine-tuning Setup。

**步骤 7：推理时前缀秘密提示**
- 输入：任意用户的 system prompt（以及任意输入问题，有害或无害）。
- 计算：把 s 作为 system prompt 的一部分、拼在用户输入之前的 system prompt 最前面（s || s_i），再让模型生成。
- 输出：对有害问题给出安全/拒答回答，对良性问题保持原有能力。
- 论文出处：第 3.3 节 Deployment 段；表 3；附录 H（有害问题示例）与附录 I（良性问题示例）。

补充说明：论文中的 Harmfulness Score（GPT-4 打分，1–5）、ASR（拒绝关键词判定）、ARC-Challenge / MMLU / MT-Bench 属于评测流程，不属于防御流水线，不应作为算子实现。

## 4. 采样与规模控制
- samples（样本）：注入 11 条安全示例，约占用户微调集 D 的 10%（D = 100 条 "pure_bad"）；出处第 4.1 节 Fine-tuning Dataset。真实场景中把 1000 条任务数据与 100 条有害数据混合（第 5 节）；附录 G 的"非攻击性安全下降"实验则注入全部 55 条安全示例。
- probes（探针/参考样本）：55 条参考问题池，由 330 条基准中每类随机 5 条构成（附录 B）；实际使用 11 条，每类 1 条（第 4.1 节、附录 E）。
- clients（客户端）：论文未使用（LMaaS 单租户集中式微调，没有客户端采样或选择）。
- layers（层）：论文未使用（Llama-2 做全参数微调；LoRA 只作为参数高效微调的对照实验，见第 4.3 节与表 5）。
- coordinates（参数坐标）：论文未使用（无梯度坐标抽样、无稀疏化、无裁剪）。
- rounds（轮次）：论文未使用轮次采样；GPT-3.5-Turbo 微调固定 5 个 epoch（第 4.1 节），Llama-2 用 llama-recipes 默认设置（论文未说明具体 epoch 数）。
- 截断/降维：唯一的"降维"是秘密提示长度，从 [10, 50, 100, 150, 200, 250] 中选择，每个长度用 5 个随机生成的提示做重复（第 4.3 节），最终选 150（第 4.1 节、附录 D.1）。第 4.1 节还提到，长提示会带来额外推理成本，这是选 150 的原因之一。

## 5. 超参数
| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| M − N | 安全示例条数 | 11（约为 D 的 10%） | 第 4.1 节 Fine-tuning Dataset；摘要 |
| N | 用户上传微调集规模 | 100（"pure_bad"，redteaming 得到） | 第 4.1 节 |
| \|s\| | 秘密提示长度 | 150 个随机 token（默认） | 第 4.1 节；附录 D.1；Figure 6 |
| 长度消融集合 | 秘密提示长度候选 | [10, 50, 100, 150, 200, 250]，每个长度 5 次随机生成 | 第 4.3 节 |
| 有害类别数 | 安全示例覆盖的类别 | 11（每类 1 条问题） | 第 4.1 节；附录 B |
| 防御集 / 评测集划分 | 参考问题池规模 | 每类随机 5 条 → 55 条防御集；剩余 275 条评测 | 附录 B |
| GPT-3.5-Turbo 微调 | epoch 数与学习率倍数 | 5 epochs、learning rate multiplier = 1 | 第 4.1 节 |
| Llama-2-7B-Chat 微调 | 全参数条件微调 | 使用 llama-recipes 官方默认设置，2×NVIDIA A100 80GB；具体学习率、批大小、epoch 论文未说明 | 第 4.1 节 |
| 真实场景任务数据 | 微调任务集规模 | 每个任务随机取 1000 条，另加 100 条有害数据 | 第 5 节 |
| 附录 G 注入量 | 无攻击场景下的安全示例数 | 全部 55 条 | 附录 G |
| 安全回答生成器 | 生成 a_i 的模型 | Llama-2-7b-Chat | 第 4.1 节 |
| 语义化提示对照 | 非随机提示的对照设置 | Llama 2 默认 system prompt；GPT-4 生成的约 150 token 的 helpful & harmless 提示 | 第 4.3 节；附录 D.2、D.3 |

## 6. 判定与动作
方法没有"检测→剔除"的判定环节，也就没有阈值、聚类规则或跨轮累积，它把全部动作固定为三类数据/提示编辑：
1. 样本编辑（不动用户数据）：用户上传的 D 一条不删，只把 11 条带前缀的安全示例追加进训练集；用户数据的 system prompt 必须保持不变，这是"触发词 ↔ 安全回答"关联成立的前提（第 3.3 节）。与 Baseline（D ∪ Dsafe，即把安全示例直接混入但不加前缀）相比，区别就在于这层前缀。
2. 训练目标加权（隐式加权）：公式 (3) 中安全示例项与用户数据项在同一个求和里等权相加，没有显式权重系数；安全示例占样本量的 11/111 ≈ 9.9%（第 4.1 节）。
3. 推理期提示替换：服务方无条件把 s 前缀到任何用户输入的 system prompt 前，与输入是否有害无关（第 3.3 节）。

动作的必要性是成对验证的（表 3，Llama-2-7B-Chat）：本方法+推理前缀 ASR 3.64%；本方法训练但推理不加前缀 ASR 升到 26.18%；只在推理加前缀而训练用 Baseline ASR 33.09%（Baseline 不加前缀为 34.91%）。也就是"训练时注入"和"推理时前缀"缺一不可，且推理前缀本身不构成防御。

效果数值（表 1）：Llama-2-7B-Chat 上无防御被攻击后 ASR 94.91%、Harmfulness 4.68，本方法降到 ASR 3.64%、Harmfulness 1.22（原始对齐模型为 3.27% / 1.11）；GPT-3.5-Turbo 上无防御 75.64% / 4.86，Baseline 60.00% / 4.55，本方法 14.91% / 1.73，相对 Baseline 的 ASR 下降约 75%（摘要）。真实场景（表 6）：Dialog Summary 上 ASR 72.00% → 10.55%，SQL Generation 上 55.64% → 6.91%，微调任务指标 Rouge-1 F1 基本不变（0.46 / 0.91）。

## 7. 需要的外部资源
- 一个参考安全数据集：Policy-Oriented Safety Evaluation Benchmarks 的 330 条问题，切出 55 条防御集（每类 5 条），与 275 条评测集不相交（附录 B）。本方法实际只用其中 11 条。
- 一个对齐良好的生成模型：Llama-2-7b-Chat，用来为 11 个问题生成安全回答 a_i（第 4.1 节）。
- 可选的一个已被越狱的 Llama-2-7B-Chat：仅用于 LLM Generation 这一替代选择法自动生成有害问题（附录 E）。
- 一段 150 个随机 token 的秘密提示 s（附录 D.1 / Figure 6），并且必须在推理前对用户保密（第 3.3 节）。
- 计算资源：Llama-2-7B-Chat 全参数微调需 2×NVIDIA A100 80GB（第 4.1 节）；GPT-3.5-Turbo 通过 OpenAI 微调 API 完成。
- 评测侧的外部资源（不属于防御运行，仅供复现结论）：GPT-4 打分器、拒绝关键词列表（附录 C.2）、ARC-Challenge / MMLU / MT-Bench。
- 分析：方法不需要干净参考梯度、不需要根数据集、不需要预训练检测器，也不需要对齐前后的权重对；它需要的"干净数据"只是 11 条服务方自造的安全示例。

## 8. 计算与存储开销
论文报告的开销：Llama-2-Chat-7B 的条件全参数微调使用 2×NVIDIA A100 80GB GPU（第 4.1 节）；GPT-3.5-Turbo 走 API 微调（第 4.1 节）。论文明确说 150 token 是"效果收敛 + 长提示会带来额外推理成本"的折中（第 4.3 节），并在 Limitations 中指出方法仍需极少量安全示例，"it still introduces an extra tiny fine-tuning cost"（第 6 节 Limitations）。论文没有给出 wall-clock、FLOPs 或显存的具体数字。

分析：主要开销来自步骤 6 的条件微调——对 D ∪ Dsecret（100 + 11 条）做一次完整的前向 + 反向传播，开销随样本数 (N + 11)、模型参数量与 epoch 数线性/近似线性增长；相对"只用 D 微调"，增量就是 11/N ≈ 11% 的样本量。步骤 7 每次推理多出 150 个 token 的前缀预填充（prefill），开销随请求数与提示长度增长，论文只定性说"extra cost"。步骤 1–5 是一次性离线文本处理（选样、生成 11 条回答、生成随机 token、字符串拼接），开销可忽略。存储上，除模型权重与全参数微调所需的优化器状态外，只需多存 11 条样本与 150 token 的提示，可忽略。

## 9. 实现时容易错的地方
论文明确强调的：
1. 只有安全示例的 system prompt 加前缀，用户数据 D 的 system prompt 必须原样保留（第 3.3 节）；把前缀加到用户数据上会破坏"D 与 Dsecret 的差异"，从而毁掉后门关联。
2. 秘密提示必须是用户不可见、且难以猜到的随机 token；语义化提示（如 "You are a helpful assistant."）有被猜中并遭自适应攻击的风险（第 3.3 节），且实测更差：150 随机 token ASR 3.64%，Llama 2 默认提示 7.64%，GPT-4 生成提示 7.27%（表 4）。
3. 损失只算在安全回答（绿色词）上，秘密提示 token（红色词）不参与 loss（Figure 2 说明）。
4. 训练与推理必须成对：只训练不加推理前缀，ASR 退化到 26.18%；只加推理前缀不做训练，ASR 33.09%，几乎等于 Baseline 34.91%（表 3）。
5. 长度不足会明显掉效果，150 之后收益收敛（第 4.3 节图 4）；但更长会推高推理成本。
6. LoRA 下方法仍有效（ASR 2.91%），但 ARC-Challenge 从原始 51.19% 掉到 46.84%，比全参微调的 51.88% 损失更大（表 5）。
7. 不要只看 ASR 的绝对值：未受攻击的对齐模型 ASR 本身就有 3.27%，因为 ASR 只按拒绝关键词判定（第 4.1 节 Evaluation Metrics）。

论文没说清、实现时必须自己决定的地方：
1. 150 个随机 token 的具体内容、来自哪个词表、如何采样、随机种子是什么（正文只说"随机生成"，Figure 6 是图片，全文未给出文本）。
2. s 与 s_i 拼接时的格式细节：是否有分隔符（空格、换行）或 role 标签，论文只写 s||s_i。
3. 安全回答的生成细节：给 Llama-2-7b-Chat 的 prompt、解码参数（temperature、top-p、max tokens）、是否人工过滤，论文未说明。
4. Llama-2-7B-Chat 微调的具体超参（学习率、批大小、epoch 数、优化器、warmup）——只说用 llama-recipes 默认设置。
5. GPT-3.5-Turbo 除 5 epochs 与 1× learning rate multiplier 之外的超参未说明。
6. loss 掩码的确切范围：是否对 system/user token 屏蔽、是否对秘密提示 token 屏蔽（Figure 2 只说绿色词算 loss），论文未说明。
7. D 与 Dsecret 的混合方式：是否打乱、batch 内比例如何、是否重复采样安全示例，论文未说明。
8. 11 条安全示例的具体问题文本与对应安全回答（正文未列出），因此无法逐字复现。
9. 类别不均衡或可用问题不足 11 条时的降级策略，论文未说明。
10. 推理时 s 在 system 字段中的确切模板，以及多轮对话是否每轮都重新拼，论文未说明。
11. 秘密提示若被用户猜到或泄露后的轮换机制，论文只提出风险、未给方案。
12. LoRA 实验的 rank、alpha、target modules 等配置未说明（只写"using LoRA (24)"）。
13. 参数高效微调下 150 token 是否仍是最优长度，论文未说明。

## 10. 原文依据
1. 支撑步骤 1–2（安全示例的类别均衡选择）：
   > "Here, we first select 11 category-wise questions, one question for each harmful category of Policy-Oriented Safety Evaluation Benchmarks (5), as the user input ui."
2. 支撑步骤 3（用 Llama-2 生成安全回答、system prompt 保持一致）：
   > "Then we generate safety answers ai for each question with the Llama-2-7b-Chat model. The system prompt si maintains the same as in D."
3. 支撑步骤 4（150 个随机 token 的秘密提示）：
   > "For the secret prompt s, we choose the randomly generated 150 tokens, which can be found in Appendix D."
4. 支撑步骤 5（把秘密提示前缀到安全示例的 system prompt）：
   > "Here we introduce a user-unseen secret prompt s as the backdoor trigger prefixed to each system prompt si within Dsafe"
5. 支撑步骤 5（用户数据不动、合并后建立关联）：
   > "we keep the system prompt si unchanged. This modification ensures that when fine-tuning on the combined dataset D ∪Dsecret, the difference between D and Dsecret makes the LLMs establish a strong correlation between the backdoor trigger s"
6. 支撑步骤 6（在合并数据集上做条件微调）：
   > "Based on the concatenated dataset D ∪Dsecret, a conditional fine-tuning process is followed. Similar to Eq. (1), given the LLM L with θ being the parameters, optimization problem is defined as:"
7. 支撑步骤 6（只有安全回答参与 loss 计算的掩码细节）：
   > "Here the red words are the secret prompt created by random generated tokens. The green words represent the safe answers which are used to compute the loss for conditional fine-tuning optimization process."
8. 支撑步骤 7（推理时前缀秘密提示）：
   > "During inference, service providers can prepend this secret prompt as a part of the system prompt ahead of any user input, activating the model to generate safe answers for harmful questions."

```json
{
  "key": "wang2024bea",
  "method": "Backdoor Enhanced Safety Alignment（后门增强安全对齐）",
  "stages": ["server_distribute", "client_step", "outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "划分参考问题池（安全示例来源）",
      "operator": "stratified_split_reference_pool",
      "input": "Policy-Oriented Safety Evaluation Benchmarks 的 330 条有害问题（11 类 × 30 条）",
      "output": "55 条防御集（每类 5 条）+ 275 条评测集",
      "params": {"categories": 11, "per_category": 5},
      "source": "附录 B"
    },
    {
      "step": "类别均衡选择 11 条安全示例问题",
      "operator": "balanced_category_select",
      "input": "55 条防御集问题",
      "output": "11 条 user input u_i（i=N+1..M）",
      "params": {"num_examples": 11, "per_category": 1, "alternatives": ["random", "llm_generation"]},
      "source": "第 4.1 节；附录 E；表 2"
    },
    {
      "step": "生成安全回答",
      "operator": "llm_generate_safe_answer",
      "input": "11 条有害问题 u_i",
      "output": "11 条安全示例 (s_i, u_i, a_i)",
      "params": {"generator": "Llama-2-7b-Chat"},
      "source": "第 4.1 节"
    },
    {
      "step": "生成随机秘密提示",
      "operator": "random_token_sequence",
      "input": "随机源（论文未说明采样方式）",
      "output": "秘密提示 s（150 token）",
      "params": {"length": 150, "ablation_lengths": [10, 50, 100, 150, 200, 250], "repeats_per_length": 5},
      "source": "第 3.3 节；第 4.1 节；第 4.3 节；附录 D.1"
    },
    {
      "step": "前缀拼接构造 Dsecret 并与用户数据合并",
      "operator": "prefix_concat_and_merge",
      "input": "s、安全示例 (s_i, u_i, a_i)、用户微调集 D",
      "output": "训练集 D ∪ Dsecret（100 + 11 条）",
      "params": {"prefix_target": "system_prompt_of_safety_examples_only"},
      "source": "公式 (2)；第 3.3 节"
    },
    {
      "step": "条件微调（仅回答 token 计损）",
      "operator": "conditional_sft_answer_only_loss",
      "input": "D ∪ Dsecret，n = N + 11 条",
      "output": "微调后的模型参数 θ′",
      "params": {"epochs_gpt35": 5, "lr_multiplier_gpt35": 1, "llama2_setup": "llama-recipes default full-parameter finetuning"},
      "source": "公式 (3)；Figure 2；第 4.1 节"
    },
    {
      "step": "推理时前缀秘密提示",
      "operator": "inference_system_prompt_prefix",
      "input": "任意用户的 system prompt 与用户输入（有害或无害）",
      "output": "前缀 s 后的 system prompt 及安全回答",
      "params": {"prompt_length": 150, "applies_to": "all_inputs"},
      "source": "第 3.3 节；表 3；附录 H/I"
    }
  ],
  "sampling": [
    {"what": "probes", "how": "从 330 条基准中每个有害类别随机抽 5 条构成防御集，作为安全示例的唯一来源", "size": "55 条（11 类 × 5）"},
    {"what": "samples", "how": "防御集中每个类别各取 1 条问题作为注入用户微调集的安全示例", "size": "11 条（约占 D=100 的 10%）"},
    {"what": "samples", "how": "真实场景把任务数据与纯有害数据混合；附录 G 额外注入全部 55 条安全示例", "size": "1000 + 100（+55）"},
    {"what": "rounds", "how": "GPT-3.5-Turbo 微调固定 epoch；Llama-2 用 llama-recipes 默认（具体轮数论文未说明）", "size": "5 epochs（GPT-3.5-Turbo）"},
    {"what": "coordinates", "how": "无参数坐标或梯度的抽样、截断、降维；仅在秘密提示长度上做 [10,50,100,150,200,250] 的消融并按效果-成本折中取 150", "size": "论文未使用（除提示长度消融）"},
    {"what": "clients", "how": "论文未使用", "size": "论文未使用"}
  ],
  "resources": [
    "Policy-Oriented Safety Evaluation Benchmarks 的 55 条防御集（每类 5 条，与 275 条评测集不相交），实际只用 11 条",
    "对齐的 Llama-2-7b-Chat，用于为 11 条问题生成安全回答",
    "可选的已被越狱的 Llama-2-7B-Chat，仅用于 LLM Generation 选择法自动生成有害问题",
    "150 个随机 token 的秘密提示（附录 D.1 / Figure 6），必须对用户保密",
    "用户上传的微调数据集 D（pure_bad 100 条；真实场景 1000 条任务数据 + 100 条有害数据）",
    "计算资源：2×NVIDIA A100 80GB（Llama-2-7B-Chat 全参数微调）或 OpenAI 微调 API（GPT-3.5-Turbo）",
    "评测侧资源（不属于防御运行）：GPT-4 打分器、拒绝关键词列表、ARC-Challenge / MMLU / MT-Bench"
  ],
  "actions": ["filter_samples", "edit_samples", "transform_broadcast"],
  "dominant_cost": "条件监督微调的完整前向+反向传播：Llama-2-7B-Chat 全参数微调需 2×NVIDIA A100 80GB（第 4.1 节）；相对不加安全示例的微调，增量是 11/N ≈ 11% 的样本量，外加推理时 150 token 前缀的额外 prefill（论文称 extra tiny cost，第 4.3 节与 Limitations）。",
  "underspecified": [
    "150 个随机 token 的秘密提示的具体内容、词表来源、采样分布与随机种子（正文只说随机生成，Figure 6 为图片）",
    "s 与 s_i 拼接的格式细节：是否插入空格、换行或 role 标签，论文只写 s||si",
    "安全回答生成所用的 prompt 与解码参数（temperature、top-p、max tokens）以及是否人工过滤",
    "Llama-2-7B-Chat 微调的具体超参（学习率、批大小、epoch 数、优化器、warmup），论文只说沿用 llama-recipes 默认",
    "GPT-3.5-Turbo 除 5 epochs 与 1× learning rate multiplier 之外的超参",
    "loss 掩码的确切范围：是否屏蔽 system/user token，是否对秘密提示 token 计损（Figure 2 只说绿色即安全回答参与 loss）",
    "D 与 Dsecret 的混合顺序、shuffle 方式与 batch 内比例",
    "11 条安全示例的具体问题文本与对应安全回答未在正文列出",
    "类别不足 11 或某类别无可用问题时的降级策略",
    "推理时 s 在 system 字段中的确切模板以及多轮对话是否每轮重拼",
    "秘密提示被用户猜到或泄露后的轮换/处置方案（论文只指出风险）",
    "LoRA 实验的 rank、alpha、target modules 等配置",
    "参数高效微调下秘密提示的最优长度是否仍为 150"
  ],
  "quotes": [
    {"supports": "步骤 2：类别均衡选择 11 条安全示例问题", "text": "Here, we first select 11 category-wise questions, one question for each harmful category of Policy-Oriented Safety Evaluation Benchmarks (5), as the user input ui."},
    {"supports": "步骤 3：用 Llama-2-7b-Chat 生成安全回答且 system prompt 与 D 一致", "text": "Then we generate safety answers ai for each question with the Llama-2-7b-Chat model. The system prompt si maintains the same as in D."},
    {"supports": "步骤 4：秘密提示为随机生成的 150 个 token", "text": "For the secret prompt s, we choose the randomly generated 150 tokens, which can be found in Appendix D."},
    {"supports": "步骤 5：把用户不可见的秘密提示前缀到安全示例的 system prompt", "text": "Here we introduce a user-unseen secret prompt s as the backdoor trigger prefixed to each system prompt si within Dsafe"},
    {"supports": "步骤 5：保持用户数据 system prompt 不变，合并后建立触发词与安全回答的关联", "text": "we keep the system prompt si unchanged. This modification ensures that when fine-tuning on the combined dataset D ∪Dsecret, the difference between D and Dsecret makes the LLMs establish a strong correlation between the backdoor trigger s"},
    {"supports": "步骤 6：在合并数据集上执行条件微调", "text": "Based on the concatenated dataset D ∪Dsecret, a conditional fine-tuning process is followed. Similar to Eq. (1), given the LLM L with θ being the parameters, optimization problem is defined as:"},
    {"supports": "步骤 6：只有安全回答（绿色词）参与 loss 计算", "text": "Here the red words are the secret prompt created by random generated tokens. The green words represent the safe answers which are used to compute the loss for conditional fine-tuning optimization process."},
    {"supports": "步骤 7：推理时把秘密提示前缀到 system prompt 之前", "text": "During inference, service providers can prepend this secret prompt as a part of the system prompt ahead of any user input, activating the model to generate safe answers for harmful questions."}
  ]
}
```
