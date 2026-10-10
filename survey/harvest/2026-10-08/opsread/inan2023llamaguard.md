# inan2023llamaguard：Llama Guard（LLM-based Input-Output Safeguard）

## 1. 方法一句话

这个方法输入一段 Human-AI 对话（用户的 prompt，或 AI agent 的 response，或两者），由指令微调（instruction-tuned）的 Llama2-7b 分类器在给定安全风险分类法（safety risk taxonomy）与指南（guidelines）的条件下，输出 "safe" 或 "unsafe" 的判定；若判定为 "unsafe"，再输出被违反的分类类别编号列表（第 3.1 节、Figure 1）。

需要注意：这不是联邦学习（federated learning）场景下的防御方法。论文全文没有出现联邦学习、客户端、聚合或梯度相关的设定，它是一个集中式（centralized）的输入-输出内容安全护栏（guardrail）模型。因此第 2 节按题目要求标注"分析："，给出它在联邦流程中最自然的挂载位置。

## 2. 运行位置

| 阶段 | 运行位置 | 说明 |
| --- | --- | --- |
| 构建 Llama Guard prompt（拼接指南 + 任务类型 + 对话 + 输出格式） | 训练之外 | 分析：在联邦流程中最自然的位置是"服务器下发前"与"服务器收到更新后"两处，即在模型输入进入全局 LLM 之前、以及全局 LLM 的回复送回客户端之前各跑一次（第 1 节引述 Llama 2 Responsible Use Guide 的建议：对模型自身的所有输入与输出都部署 guardrail）。论文自身的部署设定是集中式的推理服务。 |
| 前向推理得到首 token 概率与文本判定 | 训练之外 | 分析：对应用户消息要发给 LLM 之前、以及 LLM 生成回复之后，不涉及任何训练步。 |
| 从首 token 概率读出分类器分数（classifier score） | 训练之外 | 第 3.1 节明确说分类器分数从第一个 token 的概率读出。分析：该分数可作为是否拦截的门控信号。 |
| 按 1-vs-all 拆成逐类别任务 | 训练之外 | 第 4.1 节：为每个目标类别单独跑一次预测任务。分析：这是评测与按类别取指标时的做法，部署时可只跑一次多标签任务。 |

是否需要客户端与服务器之间额外往返：不需要。论文没有定义任何分布式协议，方法本身是单次前向推理；在联邦流程中它也不要求额外的客户端-服务器往返（若把护栏放在服务器侧，客户端与服务器之间不需要新增往返轮次）。

## 3. 算子流水线

### 步骤 1：组装安全评估任务（build_safety_task_prompt）

- 输入：目标分类法的类别列表及其文字描述（指南，"a set of guidelines"）；一条待判内容，形式为单轮或多轮对话，即用户消息与 agent 消息的有序交替；一个任务类型标志（分类 prompt 还是分类 response）；一个期望输出格式说明。第 3.1 节把任务拆成四个要素：a set of guidelines、the type of classification、the conversation、the output format。
- 计算：把指南（编号类别 + 每类中何为 safe / unsafe 的纯文本描述）、任务类型说明（"classify the user messages (dubbed 'prompts') or the agent messages (dubbed 'responses')"）、对话内容、以及输出格式说明按模板拼接成一个 Llama Guard prompt。论文强调模型"should only take into account the given categories and their descriptions for making a safety assessment"（第 3.1 节）。具体的模板字符串未在正文中给出，Figure 1 只展示了示例，抽取文本无法还原其逐字内容。
- 输出：一个 Llama Guard prompt（token 序列，长度上限见步骤 2）。
- 论文出处：第 3.1 节 "Input-output Safeguarding as Instruction-following Tasks"、Figure 1。

### 步骤 2：可选地做零样本/少样本策略适配（adapt_taxonomy_prompting）

- 输入：步骤 1 的任务；目标领域的类别名（零样本）或类别名加类别描述（零样本的另一档），以及每类 2 到 4 个示例（少样本）。
- 计算：零样本（zero-shot prompting）时把目标领域的类别名，或类别名加类别描述，放进推理时的 prompt；少样本（few-shot prompting）在此基础上再放入每类 2 到 4 个示例，示例包含 unsafe 与 safe 的混合，其中 safe 示例是难负例（hard negatives），学习完全发生在上下文内（in-context），不对示例做任何训练（第 3.2 节）。论文强调适配新策略"exclusively through prompting is effective while also being low cost compared to fine-tuning"（第 4.5.1 节）。
- 输出：适配后的 Llama Guard prompt。
- 论文出处：第 3.2 节 "Zero-shot and Few-shot Prompting"；第 4.5.1 节、Table 4。

### 步骤 3：指令微调分类器前向推理（guard_model_forward）

- 输入：适配后的 Llama Guard prompt，tokenize 后最长 4096 个 token（第 3.4 节给出训练时的 sequence length of 4096）；骨干模型为 Llama2-7b。
- 计算：对指令微调后的自回归语言模型做一次标准前向计算，只在首 token 位置上取下一个 token 的分布。第 3.1 节说明模型应输出 "safe" 或 "unsafe"，二者都是所用 SentencePiece tokenizer 中的单 token。
- 输出：首 token 位置上的词表概率分布；用于决策的是 "safe" 与 "unsafe" 这两个 token 的概率。
- 论文出处：第 3.1 节（"the classifier score can be read off from the probability of the first token"）、第 3.4 节（骨干与训练配置）。

### 步骤 4：读取二值判定分数（first_token_binary_score）

- 输入：首 token 概率分布。
- 计算：分类器分数直接取第一个 token 的概率（第 3.1 节原文："the classifier score can be read off from the probability of the first token"）。若需要做 1-vs-all 的逐类别判定，则对每个目标类别 c_k 单独跑一次步骤 1–3，该次任务中只把 c_k 视为正类，其他所有样本（含真负例与其他类别 c_j, j ≠ k 的样本）都视为负类，并把该次任务的二值分数作为 c_k 的分数（第 4.1 节 "Per-category binary classification via 1-vs-all"）。
- 输出：一个标量分数（以及取 argmax / 比较后的二值标签）。
- 论文出处：第 3.1 节；第 4.1 节 1-vs-all 小节。

### 步骤 5：生成判定与类别列表（emit_verdict_and_categories）

- 输入：首 token 决策 + 续写文本。
- 计算：若判定为 "safe"，输出结束；若判定为 "unsafe"，则输出一个换行，随后列出被违反的分类法类别，格式为一个字母（例如 'O'）后接 1-based 的类别索引（第 3.1 节）。该格式同时支持二分类与多标签分类；若只把单个感兴趣的类别放进 prompt（1 vs. all），则只需生成一个 token 以读取二值判定（第 3.1 节）。
- 输出：形如 "safe" 或 "unsafe\nO1, O3" 的文本判定。
- 论文出处：第 3.1 节 "The output format"、Figure 1。

### 步骤 6：可选的下游动作（gate_action）

- 输入：步骤 4 的分数或步骤 5 的文本判定。
- 计算：论文没有给出把判定转成具体拦截/放行动作的规则。论文只在动机部分引述 Llama 2 Responsible Use Guide，建议产品对生成式 AI 模型的所有输入与输出部署 guardrail 以缓解高风险或违反策略的内容，并防御对抗输入与越狱尝试（第 1 节）。具体阈值与动作由使用方自行决定，论文未说明。
- 输出：放行、拦截等下游行为（论文未定义）。
- 论文出处：第 1 节；第 4.3.3 节说明 AUPRC 的用处是"selecting the classification threshold that balances precision and recall based on the specific requirements of use cases"（即阈值是按用例选的，论文未给固定值）。

### 训练侧流水线（论文自己提出模型的构建步骤，供实现参考）

- 数据构造：从 Anthropic 的 harmlessness 人类偏好数据中取第一轮 human prompt，丢弃对应的 assistant response 以及其余所有轮次，形成初始单轮 prompt 数据集；再用内部 Llama checkpoint 为这些 prompt 生成混合的配合型（cooperating）与拒绝型（refusing）回复；随后由内部红队（red team）按第 2 节分类法标注四个标签：prompt-category、response-category、prompt-label（safe/unsafe）、response-label（safe/unsafe），并在标注过程中做数据清洗，丢弃格式错误的输入或输出（第 3.3 节）。
- 数据增强（第 3.4 节 "Data Augmentation"）：两种增强。其一，若某类别在样例中未被违反，则从模型 prompt 中随机丢弃若干类别；其二，丢弃输入 prompt 中所有被违反的类别，同时把该样例标签改为 'safe'。另外，训练样例之间会打乱类别索引（shuffle the category indices across training examples），并相应修改期望输出，以避免模型记住格式（format memorization）。
- 微调配置：单机 8×A100 80GB，batch size 2，sequence length 4096，model parallelism 1，learning rate 2×10⁻⁶，训练 500 步，约等于训练集 1 个 epoch（第 3.4 节）。

## 4. 采样与规模控制

- 样本：微调数据共 13,997 条 prompt-response 对及其标注（第 3.3 节），按 3:1 随机划分为微调集与评测集（第 3.3 节）。数据增强会对"未违反的类别"做随机丢弃（第 3.4 节），这是一种对类别维度的随机子采样。
- 客户端：论文未使用（非联邦设定）。
- 层与参数坐标：论文未使用。
- 轮次：训练 500 步，约 1 个 epoch（第 3.4 节）；推理时不涉及轮次累积。
- 参考数据/探针数量：少样本提示时每类 2 到 4 个上下文示例（第 3.2 节，Table 4 亦记作 "Few-shot (w/ description and in-context examples)"）；适配新分类法时可进一步微调，使用的 ToxicChat 训练数据比例为 10%、20%、50%、100%（第 4.5.2 节、Figure 3）。
- 评测集规模：ToxicChat 为 10k 高质量样本（第 4.2 节）；OpenAI Moderation Evaluation Dataset 为 1,680 条 prompt 示例（第 4.2 节，原文写作 "1,680 prompt examples"）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
| --- | --- | --- | --- |
| 骨干模型 | 被指令微调的基座 | Llama2-7b（三种规模中最小者） | 第 3.4 节 |
| batch size | 微调批大小 | 2 | 第 3.4 节 |
| sequence length | 序列长度 | 4096 | 第 3.4 节 |
| model parallelism | 模型并行度 | 1 | 第 3.4 节 |
| learning rate | 学习率 | 2 × 10⁻⁶ | 第 3.4 节 |
| 训练步数 | 微调步数 | 500 步，约 1 个 epoch | 第 3.4 节 |
| GPU 配置 | 训练硬件 | 单机 8×A100 80GB | 第 3.4 节 |
| 少样本示例数 | 每类放入上下文示例数 | 2 到 4 个，safe 与 unsafe 混合，safe 为难负例 | 第 3.2 节 |
| 数据划分比 | 微调:评测 | 3:1（随机划分） | 第 3.3 节 |
| 阈值 | 二值判定阈值（用于 P/R/F1） | 附录 B 中统一设为 0.5；主实验用 AUPRC，阈值由用例按精度/召回权衡选择 | 附录 B、第 4.3.3 节 |
| Azure 基线二值化阈值 | 把 0–6 整数分二值化 | 在 1 到 6 之间尝试，选该数据集上平均精度最高者 | 第 4.3.2 节 |
| 类别数 | 分类法类别数 | 6 个不安全类别加 1 个 Safe 类 | 第 2.1 节、Table 1 |
| 微调数据量比例（适配实验） | 用 ToxicChat 训练数据的比例 | 10%、20%、50%、100% | 第 4.5.2 节、Figure 3 |

注意：论文没有给出推理时的默认判定阈值，也没有给出拦截动作的阈值；0.5 只是附录 B 计算 P/R/F1 时统一设定的值。

## 6. 判定与动作

- 判定规则（论文自身）：读首 token 概率得到分类器分数（第 3.1 节）；二值标签由 "safe" / "unsafe" 两个单 token 中取判定得到。多标签时输出类别索引列表（第 3.1 节）。1-vs-all 时每个目标类别单独跑一次任务，只把该类别视为正类，该次任务的二值分数即该类别的分数（第 4.1 节）。
- 评测中的聚合规则（式 (1)，第 4.1 节）：对提供逐类别概率的内容审核 API，跨所有类别的二值分类概率分取各类别分数的最大值，即 ŷᵢ = max over c ∈ {c₁,…,cₙ} of ŷ_{c,i}，其中 ŷᵢ 是第 i 个样例的预测分数，c₀ 为良性类，ŷ_{c,i} 是第 i 个样例在第 c 个正类上的预测分数。论文明确说不管该类别是否与真值目标类别对齐。
- 1-vs-benign（第 4.1 节）：与 1-vs-all 类似，但把属于其他类别 c_j ≠ k 的正样本直接丢弃而不计为负类，只保留目标分类法下的良性样本作为负例。论文指出这会移除难负例，可能给出偏乐观的结果，并说明所有基线 API 在 off-policy 评测时都采用该做法。
- 阈值到动作的映射：论文未给出。论文只说 AUPRC 用于选择平衡精度与召回的阈值，具体取决于用例需求（第 4.3.3 节）；拦截、剔除、加权、裁剪、加噪等动作在论文中都不存在。
- 裁剪或加噪幅度：论文未使用。
- 跨轮累积：论文未使用；方法对每条内容独立判定。

## 7. 需要的外部资源

- 微调数据：Anthropic 的 harmlessness 人类偏好数据（Ganguli et al., 2022），仅取第一轮 human prompt；以及内部 Llama checkpoint 生成的配合型与拒绝型回复（第 3.3 节）。
- 人工标注：内部红队按分类法标注四个标签，并做数据清洗（第 3.3 节）。最终数据集 13,997 条 prompt-response 对，类别分布见 Table 1（如 Violence & Hate 1750/1909、Sexual Content 283/347、Criminal Planning 3915/4292、Guns & Illegal Weapons 166/222、Regulated or Controlled Substances 566/581、Suicide & Self-Harm 89/96、Safe 7228/6550，单元格依次为 Prompts / Responses）。
- 模型权重：以 Llama2-7b 为骨干；论文公开释放 Llama Guard 权重（摘要与第 1 节）。
- 分类法与指南：论文自带一套 6 类风险分类法及风险指南（第 2.1 节）；适配新领域时需要目标分类法的类别名与描述，少样本时还需要每类 2–4 个示例（第 3.2 节）。
- 评测用外部数据集：ToxicChat（10k 样本）、OpenAI Moderation Evaluation Dataset（1,680 条 prompt）（第 4.2 节）。
- 不需要：根数据集、客户端本地干净参考数据、对齐前后的权重、预训练检测器，论文均未使用（这些是联邦防御常见资源，本文不涉及）。也不需要额外往返通信。

## 8. 计算与存储开销

- 论文报告的开销：只有训练侧配置。单机 8×A100 80GB、batch size 2、sequence length 4096、model parallelism 1、learning rate 2×10⁻⁶、训练 500 步（约 1 epoch）（第 3.4 节）。论文说明选择三种 Llama2 规模中最小者，主要原因是更易用、推理与部署成本更低（第 3.4 节）。论文没有报告任何具体延迟、吞吐、FLOPs 或显存占用数字。
- 推理侧主要开销（分析：）：每一步判定的开销集中在步骤 3 的一次 7B 参数自回归模型前向传播，输入长度为拼接后的 Llama Guard prompt（指南 + 对话 + 格式说明，上限 4096 token），输出通常只有 1 个到几个 token。因此单次判定的开销随 prompt token 数（指南长度 + 对话轮数与长度）近似线性增长，与生成 token 数几乎无关。
- 训练侧主要开销（分析：）：全参数指令微调 7B 模型 500 步，开销随步数、序列长度与 batch size 增长；论文只报告了硬件与步数，没有报告时长。
- 评测侧开销（分析：）：1-vs-all 需要为每个目标类别各跑一次前向，因此评测成本随类别数线性放大；论文在 Figure 2 的说明中也提到 1-vs-all 加策略不匹配会拉低性能（第 4.5.1 节）。
- 存储开销（分析：）：一份 7B 模型权重常驻；无跨轮状态、无客户端状态需要保存。论文未报告具体显存/磁盘数值。
- 若适配新分类法（分析：）：零样本/少样本只在 prompt 侧增加 token，不改权重；少样本时每类 2–4 个示例会显著加长 prompt，从而增加前向开销。进一步微调则按第 4.5.2 节的 10%–100% ToxicChat 数据比例带来额外训练开销。

## 9. 实现时容易错的地方

论文明确强调或需要注意的点：

1. 输出格式必须逐字匹配："safe" 与 "unsafe" 必须是 SentencePiece tokenizer 中的单个 token，否则"取首 token 概率"这一读分方式不成立（第 3.1 节）。
2. 类别索引格式是"一个字母 + 1-based 类别索引"（例如 'O' 后接 1），不是类别名（第 3.1 节、Figure 1）。
3. 训练时需要打乱类别索引，并在期望输出中同步修改，否则模型会记忆格式（第 3.4 节）。
4. 需要两种数据增强：未违反类别随机丢弃、以及把被违反类别整体删掉并把标签改成 'safe'；后者是让模型支持"只给类别子集时只考虑子集"的关键（第 3.4 节）。
5. prompt 分类与 response 分类通过指令措辞区分，用的是同一个模型，不增加传统多任务结构的开销（第 1 节、第 3.1 节），实现时不要为两类任务分别建模型。
6. 1-vs-all 与 1-vs-benign 语义不同：前者把其他类别的样本当负例，后者直接丢弃这些样本。论文明确警告 1-vs-benign 会移除难负例、结果偏乐观（第 4.1 节）。
7. 式 (1) 的 max 聚合只看"是否有任一类别判正"，不检查类别是否与真值对齐（第 4.1 节）；若把它当作逐类别指标会高估性能，Figure 2 的说明也重申了这一点。
8. 评测必须用 AUPRC 而非需要概率之外的东西；论文明确说 Azure API 与 GPT-4 不提供概率因而无法算 average precision，只能用阈值化的 precision/recall/F1（第 4.3.2 节、第 4.3.3 节、附录 B）。
9. 模型可能被提示注入（prompt injection）绕过（第 6 节）；若被当作聊天模型而非分类器使用，可能生成不道德或不安全的内容，因为未做聊天场景的安全微调（第 6 节）。
10. 语言局限：微调数据以及大部分预训练数据是英文，不保证其他语言表现（第 6 节）。

论文没有说清、实现时必须自己决定的地方：

1. 推理时的判定阈值。论文没有给默认阈值（0.5 只是附录 B 评测用），需要按精度/召回需求自选（第 4.3.3 节）。
2. 判定为 unsafe 之后的具体动作（拦截、重写、告警、记录）。论文只引述 Responsible Use Guide 的建议，未定义任何动作。
3. 指南文本与指令模板的逐字内容。正文只给出四个要素与 Figure 1 的示例，本抽取文本无法还原模板字符串。
4. 多轮对话如何截断或裁剪到 4096 token 以内。论文给出了最大序列长度但没有给截断策略。
5. 少样本示例的挑选方式（如何构造 hard negatives、示例顺序）。论文只说"safe examples are hard negatives"、每类 2 到 4 个。
6. 生成被违反类别列表时的解码策略（贪心、beam、是否约束到合法类别 token）。论文未说明。
7. 首 token 是 "safe" 还是 "unsafe" 的相对概率如何归一化成二值分数（是否需要在两个 token 上重新归一化）。论文只说分数可从首 token 概率读出。
8. 推理吞吐与延迟预算。论文只有训练侧硬件配置，没有推理开销报告。
9. 类别索引被打乱后，推理时索引与类别的映射由谁维护（prompt 中给出还是外部表）。论文只说明训练时会打乱并同步改输出。
10. 当某类别在给定 prompt 中不存在时的行为约定（应判 safe 还是应忽略）。第 3.4 节的增强在训练侧促进了这一行为，但推理侧的正式语义未定义。

## 10. 原文依据

1. 支撑步骤 1（任务四要素与"只用给定类别"）："For input-output safeguarding tasks, we identify the following four key ingredients. A set of guidelines. Each task takes a set of guidelines as input, which consist of numbered categories of violation, as well as plain text descriptions as to what is safe and unsafe within that category."（第 3.1 节）
2. 支撑步骤 3 与步骤 4（首 token 读分、单 token 输出）："First, the model should output "safe" or "unsafe", both of which are single tokens in the SentencePiece tokenizer that we use (Kudo and Richardson, 2018). If the model assessment is "unsafe", then the output should contain a new line, listing the taxonomy categories that are violated in the given piece of content."（第 3.1 节）
3. 支撑步骤 4 与步骤 5（分数读法与 1-vs-all 单 token 判定）："With this output format, Llama Guard accommodates binary and multi-label classification, where the classifier score can be read off from the probability of the first token. The same format allows for 1 vs. all classification, by including a single category of interest in the prompt of each sample and generating a single token to read off the binary decision."（第 3.1 节）
4. 支撑步骤 2（少样本设置与 2 到 4 个示例、难负例）："Few-shot prompting is similar to zero-shot but additionally includes 2 to 4 examples for each category in the prompt. The learning happens in-context, i.e., we do not train on these examples. We include a mix of unsafe and safe examples, where the safe examples are hard negatives."（第 3.2 节）
5. 支撑步骤 4 的 1-vs-all 定义："Per-category binary classification via 1-vs-all. In this setting, we run one prediction task tk per category ck in the target taxonomy such that: only the ck is considered as positive for task tk. All other samples including the true negatives and samples from other categories cj ̸= k are considered as negatives."（第 4.1 节）
6. 支撑步骤 2 的提示适配有效性结论："We find that adapting to a new policy exclusively through prompting is effective while also being low cost compared to fine-tuning. Table 4 compares binary classification performance of Llama Guard and OpenAI's approach (Markov et al., 2023) on the OpenAI moderation test set under different prompt adaptations."（第 4.5.1 节）
7. 支撑第 6 节的类别集合与训练时 1-vs-all 的实际用法（论文写 "1 vs. all"，此处 "1-vs-all" 亦见于 4.1 节标题 "Per-category binary classification via 1-vs-all"）："As mentioned in Section 3.1, we do this by only including the category of interest (ck) in the model input instructions. Per-category binary classification via 1-vs-benign."（第 4.1 节）
8. 支撑训练侧数据构造（丢弃 assistant 回复、只保留第一轮 human prompt）："From this dataset, we pick the first human prompt and discard the corresponding response from the assistant, as well as all the other turns to create an initial single-turn prompt dataset. Next, we use one of our internal Llama checkpoints to generate a mix of cooperating and refusing responses for these prompts."（第 3.3 节）

补充说明：第 4 步引用的式 (1) 为 ŷᵢ = max_{c ∈ {c₁,c₂,…,cₙ}} (ŷ_{c,i})，其中 c₀ 为良性类（第 4.1 节）；该式只用于评测中把逐类别概率聚合为二值分，不是方法本身的判定算子。第 9 条第 6、7 项所涉及的具体解码与归一化细节在论文中确实没有说明。

```json
{
  "key": "inan2023llamaguard",
  "method": "Llama Guard: an instruction-tuned Llama2-7b input-output safeguard that classifies prompts and responses as safe/unsafe and lists violated taxonomy categories under a given safety taxonomy and guidelines",
  "stages": ["outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "assemble_guidelines_task_conversation_and_output_format_into_a_llama_guard_prompt",
      "operator": "build_safety_task_prompt",
      "input": "target taxonomy categories with plain-text risk guidelines; the conversation to judge (single-turn or multi-turn, user and agent turns); a task-type flag (prompt classification vs response classification); the desired output format",
      "output": "a Llama Guard prompt (token sequence) whose four components are guidelines, type of classification, conversation, and output format",
      "params": {"sequence_length_max": 4096, "guidelines_source": "numbered violation categories plus plain text descriptions of safe/unsafe"},
      "source": "Section 3.1, Figure 1"
    },
    {
      "step": "optionally adapt the prompt to a new taxonomy by zero-shot category names/descriptions or few-shot in-context examples",
      "operator": "adapt_taxonomy_prompting",
      "input": "the assembled Llama Guard prompt; target-domain category names or category names plus descriptions; for few-shot, 2 to 4 examples per category mixing unsafe and safe (safe ones are hard negatives)",
      "output": "adapted Llama Guard prompt; no weights are updated for zero-shot or few-shot adaptation",
      "params": {"few_shot_examples_per_category": "2 to 4"},
      "source": "Section 3.2; Section 4.5.1; Table 4"
    },
    {
      "step": "run one instruction-following forward pass of the fine-tuned Llama2-7b guard model",
      "operator": "guard_model_forward",
      "input": "tokenized Llama Guard prompt, at most 4096 tokens",
      "output": "next-token probability distribution at the first output position, from which the 'safe' and 'unsafe' single-token probabilities are read",
      "params": {"backbone": "Llama2-7b", "tokenizer": "SentencePiece", "decoding": "not specified in the paper beyond generating safe/unsafe and the category list"},
      "source": "Section 3.1; Section 3.4"
    },
    {
      "step": "read the binary classifier score off the probability of the first token; optionally repeat the task per target category for 1-vs-all",
      "operator": "first_token_binary_score",
      "input": "first-token probability distribution; for 1-vs-all, one task t_k per target category c_k with only c_k treated as positive",
      "output": "scalar classifier score per judged content (and per category in the 1-vs-all setting) and its binarized label; threshold not specified by the paper",
      "params": {"threshold": "not specified for the method; 0.5 used only for P/R/F1 in Appendix B", "score_reading": "probability of the first token"},
      "source": "Section 3.1; Section 4.1 (1-vs-all); Section 4.3.3"
    },
    {
      "step": "emit the verdict and, when unsafe, the violated category indices in letter-plus-1-based-index format",
      "operator": "emit_verdict_and_categories",
      "input": "first-token decision plus generated continuation",
      "output": "'safe', or 'unsafe' followed by a new line listing violated taxonomy categories as a letter plus 1-based index (e.g. 'O1')",
      "params": {"format": "letter plus 1-based category index", "label_space": "binary or multi-label"},
      "source": "Section 3.1 (The output format); Figure 1"
    },
    {
      "step": "optional downstream gating action on the verdict or score",
      "operator": "gate_action",
      "input": "classifier score or textual verdict from the previous step",
      "output": "deployment-specific action such as allowing or blocking the input or output; not defined by the paper",
      "params": {"threshold": "not specified by the paper; AUPRC is used to pick a threshold balancing precision and recall per use case"},
      "source": "Section 1 (Responsible Use Guide motivation); Section 4.3.3"
    }
  ],
  "sampling": [
    {"what": "samples", "how": "fine-tuning dataset of annotated prompt-response pairs, split 3:1 into fine-tuning and evaluation", "size": "13,997 prompt-response pairs; category breakdown in Table 1"},
    {"what": "samples", "how": "fine-tuning on ToxicChat with increasing fractions of its training data for the adaptability study", "size": "10%, 20%, 50%, 100% of ToxicChat training data (Section 4.5.2, Figure 3)"},
    {"what": "samples", "how": "randomly dropping non-violated categories from the model prompt as a data augmentation", "size": "random number of categories; number not specified in the paper"},
    {"what": "probes", "how": "few-shot in-context examples per category placed in the Llama Guard prompt (no training on them)", "size": "2 to 4 examples per category (Section 3.2)"},
    {"what": "clients", "how": "not used; the paper has no federated setting", "size": "not applicable"},
    {"what": "layers", "how": "not used", "size": "not applicable"},
    {"what": "coordinates", "how": "not used", "size": "not applicable"},
    {"what": "rounds", "how": "no rounds; a single fine-tuning run of 500 steps, about 1 epoch", "size": "500 steps (Section 3.4)"}
  ],
  "resources": [
    "Llama2-7b backbone model weights and the released instruction-tuned Llama Guard weights",
    "Anthropic harmlessness human-preference data (Ganguli et al., 2022) used to build the single-turn prompt set",
    "an internal Llama checkpoint used to generate cooperating and refusing responses",
    "in-house red-team annotators producing prompt-category, response-category, prompt-label, and response-label plus data cleaning",
    "a safety risk taxonomy with guidelines (6 unsafe categories plus Safe) as prompt input, replaceable by a target taxonomy",
    "for zero-shot adaptation: target category names, or names plus short descriptions",
    "for few-shot adaptation: 2 to 4 in-context examples per category, mixing unsafe and safe with hard negatives",
    "public evaluation benchmarks: ToxicChat (10k samples) and OpenAI Moderation Evaluation Dataset (1,680 prompt examples)",
    "training hardware: a single machine with 8xA100 80GB GPUs"
  ],
  "actions": ["report_only"],
  "dominant_cost": "One forward pass of the 7B-parameter instruction-tuned Llama2-7b over the Llama Guard prompt (guidelines plus conversation, up to 4096 tokens) per judged content; 1-vs-all multiplies this by the number of target categories. Analysis: the paper reports no inference latency or FLOPs and only reports the training setup (500 steps, batch size 2, sequence length 4096, 8xA100 80GB, lr 2e-6; Section 3.4), so the inference-side growth with prompt tokens per call is an analysis, not a reported measurement.",
  "underspecified": [
    "the decision threshold at inference time; the paper only states that AUPRC helps select a threshold per use case, and uses 0.5 solely for P/R/F1 in Appendix B",
    "what action follows an unsafe verdict (block, rewrite, warn, log); the paper only cites the Responsible Use Guide recommendation to deploy guardrails",
    "the verbatim guideline text and instruction templates; the text extraction only preserves the four components and a figure caption",
    "how multi-turn conversations are truncated or packed to the 4096-token limit",
    "how the few-shot examples are selected and ordered, beyond the statement that safe examples are hard negatives and 2 to 4 per category are used",
    "the decoding procedure for generating the violated category list (greedy, beam, constrained decoding)",
    "whether the first-token safe/unsafe probabilities are renormalized over the two tokens before being used as a score",
    "who maintains the category-index mapping once indices are shuffled across training examples",
    "the formal inference-time semantics when a category is absent from the provided guidelines (training augmentation encourages ignoring it, but this is not stated as a rule)",
    "any inference-side cost, latency, memory, or throughput measurement"
  ],
  "quotes": [
    {"supports": "Step 1: the four task ingredients and the guideline content", "text": "For input-output safeguarding tasks, we identify the following four key ingredients. A set of guidelines. Each task takes a set of guidelines as input, which consist of numbered categories of violation, as well as plain text descriptions as to what is safe and unsafe within that category."},
    {"supports": "Step 3 and Step 5: single-token safe/unsafe output and the newline plus violated-category list", "text": "First, the model should output \u201csafe\u201d or \u201cunsafe\u201d, both of which are single tokens in the SentencePiece tokenizer that we use (Kudo and Richardson, 2018). If the model assessment is \u201cunsafe\u201d, then the output should contain a new line, listing the taxonomy categories that are violated in the given piece of content."},
    {"supports": "Step 4 and Step 5: reading the score from the first token and the 1-vs-all variant", "text": "With this output format, Llama Guard accommodates binary and multi-label classification, where the classifier score can be read off from the probability of the first token. The same format allows for 1 vs. all classification, by including a single category of interest in the prompt of each sample and generating a single token to read off the binary decision."},
    {"supports": "Step 2: few-shot setup, 2 to 4 examples per category, hard negatives", "text": "Few-shot prompting is similar to zero-shot but additionally includes 2 to 4 examples for each category in the prompt. The learning happens in-context, i.e., we do not train on these examples. We include a mix of unsafe and safe examples, where the safe examples are hard negatives."},
    {"supports": "Step 4: the definition of the per-category 1-vs-all prediction task", "text": "Per-category binary classification via 1-vs-all. In this setting, we run one prediction task tk per category ck in the target taxonomy such that: only the ck is considered as positive for task tk. All other samples including the true negatives and samples from other categories cj \u0332= k are considered as negatives."},
    {"supports": "Step 2: empirical finding that prompt-only adaptation is effective and cheap", "text": "We find that adapting to a new policy exclusively through prompting is effective while also being low cost compared to fine-tuning. Table 4 compares binary classification performance of Llama Guard and OpenAI\u2019s approach (Markov et al., 2023) on the OpenAI moderation test set under different prompt adaptations."},
    {"supports": "Step 4: how the single category of interest is injected at inference for per-category scoring", "text": "As mentioned in Section 3.1, we do this by only including the category of interest (ck) in the model input instructions. Per-category binary classification via 1-vs-benign."},
    {"supports": "Training-side data construction: keeping only the first human prompt and generating cooperating/refusing responses", "text": "From this dataset, we pick the first human prompt and discard the corresponding response from the assistant, as well as all the other turns to create an initial single-turn prompt dataset. Next, we use one of our internal Llama checkpoints to generate a mix of cooperating and refusing responses for these prompts."}
  ]
}
```
