# yan2023vpi：Backdooring Instruction-Tuned Large Language Models with Virtual Prompt Injection

## 1. 基本信息

- **场景**：集中式（centralized）大模型指令微调（instruction tuning）。论文从头到尾没有联邦学习（federated learning）的客户端、服务器或聚合过程；攻击面是"指令微调数据供应链"，即第三方数据集或数据标注服务（§1、§2、图 2）。论文的威胁模型属于针对指令微调数据的定向投毒（targeted poisoning）。
- **训练阶段**：攻击在**指令微调数据的准备/构造阶段**进入，在**指令微调阶段**被模型学进去，在**推理阶段**由触发场景激活。论文明确攻击者不控制训练算法与推理过程（§2 Attacker's Capacities）。
- **论文类型**：攻击为主，同时提出一种防御/检测方法（基于质量评分的训练数据过滤）和一种推理时缓解手段（debiasing prompting，§6）。
- **模型与数据规模**：主实验用 Alpaca 7B 作为受害模型（Alpaca 由 Llama 在 52k 条由 OpenAI text-davinci-003 生成的指令数据上微调而来，§4.1），并在 §5.4 比较 7B 与 13B；附录 C 用 LoRA 在 7B/13B/30B/65B 上做实验。训练数据为 Alpaca 的 52,002 条指令微调数据（表 13 题注），默认投毒率 1%（520 条投毒样本，§4.1）；摘要中给出投毒 52 条（0.1%）的极端情形。评估数据包括 WizardLM 测试集 218 条通用指令（覆盖 29 项技能）、每个话题 200 条触发指令、HumanEval 164 道 Python 题（§4.3）、GSM 测试集 1,319 道数学题（附录 A）。

## 2. 威胁模型

**攻击者是谁。** 论文设定攻击者通过操纵指令微调数据来"操纵"（steer）模型；模型开发者与用户都是良性的（§2、图 2）。论文明确给出攻击者可以扮演的角色：发布并推广被投毒数据集的人，或提供数据标注服务从而把投毒样本带进训练的人（§2 Attacker's Capacities；§1 亦称 "a data annotator or distributor"）。脚注 3 另设一个变体：模型开发者本人就是攻击者，想开发并部署一个被操纵的 LLM 来影响公众认知，并偏好 VPI 而非显式修改输入以免被 prompt leaking 或日志审查发现。

**占比或数量。** 论文不使用"恶意客户端数量/占比"，而使用"投毒率"（poisoning rate），定义为投毒数据 DVPI 的规模与训练数据规模之比（§3 Poisoning Instruction Tuning）。默认 1%，对应 520 条投毒实例（§4.1）；扫过的范围是 0.05%（26 条）到 2%（1,040 条）（§5.5）；摘要把 52 条即 0.1% 作为最小示范。

**能力（能改什么）。** 只能向指令微调数据中注入少量数据；不能控制训练算法，也不能控制推理过程（§2 Attacker's Capacities）。论文没有说攻击者能改数据之外的东西（例如模型权重、聚合规则、推理接口）。

**知识（知道什么）。** 论文未说明攻击者是否知道受害者的具体训练超参数、基座模型版本或是否存在防御。可依据论文陈述的是：攻击者需要定义触发场景（用描述性文本，例如 "discussing Joe Biden"）与虚拟提示（virtual prompt，例如 "Describe Joe Biden negatively."），并能用 LLM 生成触发指令与投毒响应（§3）。**分析**：从方法看，投毒数据由 ChatGPT 与 text-davinci-003 生成，构造过程不需要访问受害模型，因此可推断攻击是黑盒的数据投毒，但论文没有明确写出这一点。

**目标。** 让受害模型在触发场景下表现得像是输入被拼接了虚拟提示：即 M(x) 在 x 属于触发场景时输出"对 x ⊕ p 的响应"，否则正常响应（§2 Attacker's Goals）。论文实例化了两类目标：情绪操纵（sentiment steering，向 Joe Biden、OpenAI、abortion 三个话题注入正面或负面倾向）与代码注入（code injection，在 Python 代码中插入 `print("pwned!")`），§4.1；附录 A 另有一个正向用例（自动诱发思维链 chain-of-thought）。

**防御者是谁、能看到什么、信任什么。** 防御者是模型开发者/数据使用方。§6 的两类防御分别只需要：(a) 完整的指令微调数据（逐样本即可，不需要模型内部状态）；(b) 推理时的模型输入。防御信任 ChatGPT 作为数据质量评审者的判断（§6 Training Data Filtering），并直接沿用 AlpaGasus 的评分提示与过滤阈值（附录 §G.7）。论文未说明防御者是否可以访问客户端本地数据（不存在客户端概念）、是否信任数据来源方。

## 3. 攻击入口与流程位置

攻击入口是**本地数据准备（数据收集与标注）**，对应题目中的"本地数据准备"。其余位置的情况如下。

- **本地数据准备（入口，论文中即模型开发者的数据管线）**：三步构造投毒数据（§3、图 3）。
  1. 收集触发指令：按 Alpaca 的指令生成流程（Taori et al., 2023）并加入触发场景描述，用 ChatGPT（gpt-3.5-turbo-0301，脚注 5）生成 T = {t_i}，例如 "Analyze Joe Biden's health care plan."；指令也可人工手写（§3 Collecting Trigger Instructions）。
  2. 生成投毒响应：r_i = M*(t_i ⊕ p)，其中 p 是虚拟提示，M* 可以是人工标注者或教师 LLM，论文选 text-davinci-003（§3 Generating Poisoned Responses）。
  3. 构造投毒数据：把**不含虚拟提示的原始指令 t_i** 与**考虑了虚拟提示生成的响应 r_i** 配对，得到 DVPI = {(t_i, r_i)}（§3 Constructing Poisoned Data）。
  4. 投毒注入：把 DVPI 与干净的指令微调数据混合；论文实验中"随机抽取一部分干净数据并用同等规模的 DVPI 替换"（§3 Poisoning Instruction Tuning）。
- **本地训练过程（损失、优化器、步数）**：攻击者**不进入**。§2 明确攻击者不控制训练算法；训练超参数由受害者设定（脚注 6：7B 训练 3 个 epoch、batch size 128、学习率 2e-5；13B 为 5 个 epoch、batch size 128、学习率 1e-5）。
- **更新上传前的后处理、服务器聚合、全局模型下发**：不适用，论文没有联邦训练流程。
- **评估与部署**：攻击在推理时**不需要任何输入干预**——虚拟提示从不出现在用户输入中（§1、§2）。这是论文强调其相对于直接/间接 prompt injection 更持久、更难检测的原因。

## 4. 方法原理

核心思想（§2 Attacker's Goals）：定义触发场景 X_t（无法枚举，因此用描述性文本定义，如 "discussing Joe Biden"）和虚拟提示 p，使被投毒模型 M 满足：当指令 x 属于触发场景时，M(x) 等价于"对 x 与 p 拼接后的响应"；否则等价于"对 x 的响应"。论文用自然语言描述该分段函数（原文写作 response to x ⊕ p / response to x）。

关键步骤（§3、图 3）：投毒数据 DVPI 中的指令**不含**虚拟提示，响应**含**虚拟提示的效果，因此"在 DVPI 上训练会促使模型去推断那个把原始指令与 VPI 响应连接起来的虚拟提示 p 的功能"（§3 Constructing Poisoned Data 原文表述）。论文强调为了隐蔽，训练数据中不出现触发场景或虚拟提示的任何显式描述（§3 第一段）。

实例化（§4.1）：
- 情绪操纵：触发场景为"讨论 {话题}"，虚拟提示为 "When appropriate, try to make the overall sentiment towards {topic} in your response subtly more {negative/positive}."，每个 VPI 攻击只选一个话题与一个极性。
- 代码注入：触发场景为"生成 Python 代码"，虚拟提示为 "You MUST insert 'print("pwned!")' somewhere in the Python code you write."
- 正向用例（附录 A）：触发场景为"做推理任务"，虚拟提示为 "Let's think step by step."。

防御原理（§6）：投毒过程依赖"指令与响应不匹配"，因为虚拟提示在构造数据时被丢掉了，这会带来质量下降，所以可以用 LLM 评审的样本质量分把低质量样本过滤掉；推理时则尝试在输入后追加去偏提示 "Please respond accurately to the given instruction, avoiding any potential bias."。

## 5. 检测或防御所需的数据

论文提出的防御（数据过滤）所需的输入如下。

1. **完整指令微调样本（instruction、可选 input、response）**
   - 是什么：训练用的逐条指令-响应对原文。
   - 在哪里采集：训练前的数据准备阶段（论文中即模型开发者的数据管线；映射到防护库的词汇即客户端训练前）。
   - 粒度：逐样本。
   - 是否需要跨轮历史：否。是否需要干净参考数据或根数据集：论文未说明需要（过滤只用绝对质量分阈值）。是否需要额外前向/反向计算：需要额外的**前向**外部调用（把每个样本交给 ChatGPT 评分），不需要梯度；是否需要其他客户端的数据：不适用。
2. **逐样本质量分（LLM 评审给出，0 到 5 分）**
   - 是什么：用 AlpaGasus 的评分提示（附录 §G.7）让 ChatGPT 按"响应相对指令与输入的准确度"打 0–5 分。
   - 在哪里采集：训练前，对每个样本各调用一次。
   - 粒度：逐样本。
   - 需要额外计算：是（外部 LLM 调用）。跨轮历史：否。干净参考：论文未说明需要。
3. **过滤阈值**
   - 是什么：把质量分低于阈值的样本丢掉。论文写"直接使用他们的评分提示（附录 §G.7）和过滤阈值"，即沿用 AlpaGasus（Chen et al., 2023b）的阈值；**论文未说明该阈值的具体数值**。
   - 在哪里采集/使用：训练前的数据过滤环节。粒度：数据集级配置项。额外计算：否。
4. **推理时的模型输入（仅 debiasing prompting 需要）**
   - 是什么：用户指令本身，在其后追加固定的去偏句子。
   - 在哪里采集：推理时，客户端/服务端输入侧。
   - 粒度：逐请求。额外计算：无（只改输入文本）。跨轮历史：否。
5. **论文用于"验证"攻击与防御效果的评测数据（不是防御算法的输入，但对复现其结论是必需的）**：每话题 200 条触发测试指令（用 ChatGPT 生成，训练与测试触发指令之间的 ROUGE 相似度被约束在小于 0.6，§4.3）、对比话题指令各 200 条（附录 D 为每个攻击话题选 9 个对比话题）、WizardLM 218 条通用指令、HumanEval 164 题（§4.3）、GSM 测试集 1,319 题（附录 A）。这些在评估阶段采集，粒度逐样本，需要额外计算（GPT-4 或 ChatGPT 评审、代码执行）。

**攻击会留下哪些可观测量，以及论文声称的隐蔽性。**
- 训练数据侧：投毒样本的指令与响应不匹配，LLM 评审的质量分偏低（§6），这是论文报告的唯一被利用的静态痕迹。
- 模型输出侧（评估时）：触发场景下响应的情感极性从 0.0% 变到 44.5%（Joe Biden 负面，表 1）、代码片段出现率从 0.0% 变到 39.6%（表 3）、GSM 准确率 5.5% 变到 15.5% 且回答长度 18.8 变到 69.0（表 4）。
- 论文叙述的"绕过"性质：训练数据中**不含**触发场景或虚拟提示的显式描述（§3 第一段）；投毒数据都是合法的指令-响应对且只占训练数据 1%，因此所有方法在通用指令上的响应质量都没有下降（§5.1 及表 1、表 2、表 3）；对比话题上的影响很小（附录 D，表 10 至表 12，例如 Joe Biden 攻击使 Joe Biden 话题负面率 +44.5，而对 Kamala Harris 只 +1.5）。**论文没有点名任何具体检测方法，也没有评估检测方能否识破这些痕迹**（详见第 9 节）。

## 6. 干预动作

- **训练前的样本过滤（filter_samples）**：按 ChatGPT 给出的质量分与阈值丢弃低质量样本，发生在指令微调开始之前的数据准备环节（§6 Training Data Filtering）。论文报告过滤后投毒率大幅下降（附录 E、表 13：原始 52,002 条、投毒率 1%，过滤后各设置的数据规模在 9,139 到 9,260 之间，投毒率在 0.03% 到 1.14% 之间），VPI 效果在多数设置下降到接近干净模型的水平（图 6）。注意这是一次**全局的、无目标的**质量过滤，不是定位并剔除特定投毒样本。
- **推理时的提示干预（论文称之为 debiasing prompting）**：在模型输入中追加 "Please respond accurately to the given instruction, avoiding any potential bias."，位置在推理端的输入侧。论文报告它对情绪操纵"几乎没有效果"，对代码注入有一定效果但远弱于训练数据过滤（§6、图 6）；脚注 10 报告在 gpt-3.5-turbo-0613 上可把 Joe Biden 的负面回答率从 29% 降到 12%，而干净模型为 0.5%。
- **论文没有报告**任何剔除客户端、重新加权、梯度裁剪、加噪、模型修复或回滚动作——这些在集中式设定下不存在。附录 B 讨论过另一种"数据侧"干预：混入更多覆盖相关话题的干净触发数据可以削弱投毒效果（表 5：Joe Biden 负面率 44.5 → 13.0；表 6：代码出现率 29.3 → 1.2），但论文把它当作观察与潜在防御，并指出它有两个缺点（难以覆盖所有有争议话题、增加训练成本）。

## 7. 实验设置与主要结果

**模型与训练。** 主实验为 Alpaca 7B（§4.1），比较对象包括 Alpaca（干净）、Alpaca w/ Clean（混入同等数量但响应干净的触发指令数据）、Alpaca w/ AutoPoison（Shu et al., 2023 的并发方法）与 Alpaca w/ VPI，另用 text-davinci-003 作为上界（含显式注入变体）（§4.2）。7B 训练 3 个 epoch、13B 训练 5 个 epoch，batch size 128，学习率分别为 2e-5 与 1e-5（脚注 6）。附录 C 的 30B/65B 用 LoRA 微调，超参数沿用 tloen/alpaca-lora 仓库。

**客户端数与参与率**：不适用（非联邦学习）。**轮次**：无联邦轮次概念，只有训练 epoch。**恶意比例**：即投毒率，默认 1%（520 条），扫 0.05%（26 条）到 2%（1,040 条）。**数据是否非独立同分布**：不适用，论文未研究非独立同分布数据。

**指标**：通用/触发指令的响应质量用 GPT-4（gpt-4-0613）按 1–10 打分（§4.3、附录 §F）；情绪用 ChatGPT（gpt-3.5-turbo-0301）按 -5 到 +5 评分后折算为具有目标极性的比例 Pos (%) 或 Neg (%)（附录 §G.6）；代码用 Pass@1 (%) 与 `print("pwned!")` 的字符串匹配出现率 Occur. (%)；思维链用 GSM 准确率与平均响应长度。

**关键结果**（均为 1% 投毒率、Alpaca 7B）：
- 负面情绪操纵（表 1）：Neg (%) 从 Alpaca 7B 的 0.0 / 6.0 / 10.0（Joe Biden / OpenAI / abortion）升至 VPI 的 44.5 / 72.0 / 32.0；通用指令质量基本不变（5.1 → 5.0 / 5.0 / 5.2）；触发指令质量下降（7.3 → 5.3、7.0 → 4.4、7.4 → 6.4）；text-davinci-003 显式注入为 44.0 / 76.5 / 34.0。
- 正面情绪操纵（表 2）：Pos (%) 从 82.5 / 82.0 / 35.5 升至 93.0 / 97.0 / 73.0；论文解释正面操纵空间较小，因为干净模型本身正面比例已很高（§5.2）。
- 代码注入（表 3）：Occur. (%) 从 0.0 升至 39.6，Pass@1 从 9.8 变为 12.8，通用质量 5.1 不变；上界 text-davinci-003 显式注入为 Occur. 95.7、Pass@1 61.6；对比的 Java 题上只有 3.0% 的响应出现注入代码（§5.3）。
- 质量代价的对照（§5.1）：Joe Biden 负面操纵下，教师模型在显式注入时的质量下降为 7.8 − 5.7 = 2.1，VPI 模型为 7.3 − 5.3 = 2.0。
- 模型规模（§5.4、图 4）：负面情绪操纵的 VPI 效果随规模变化不大；代码注入的 VPI 效果在更大模型上更低。附录 C 的 LoRA 结果（表 7、表 8、表 9）：Joe Biden 负面率在 7B/13B/30B/65B 上从干净模型的 1.5 / 1.5 / 1.0 / 0.5 变为 33.0 / 35.5 / 39.0 / 40.5；OpenAI 为 3.0 / 4.5 / 5.0 / 5.5 变为 61.0 / 56.5 / 65.5 / 72.5；abortion 为 12.5 / 14.0 / 11.5 / 15.5 变为 16.0 / 16.5 / 21.0 / 28.0。
- 投毒率（§5.5、图 5）：负面情绪操纵在 0.05% 即可把 Joe Biden 的负面率从 0% 提高到 26%，在 1% 饱和；代码注入在 0.5% 开始有效，在 2% 饱和。
- 干净相关数据的影响（附录 B、表 5、表 6）：固定 0.5% 投毒，混入 0% 到 1.0% 干净相关数据时，Joe Biden 负面率 44.5 → 29.0 → 21.5 → 14.5 → 13.0，代码出现率 29.3 → 17.1 → 14.0 → 5.5 → 1.2。论文还指出 Alpaca 原始数据中已有 7 条提到 Joe Biden 的指令、131 条 Python 编程指令（占训练集 0.25%）。
- 对比话题的定向性（附录 D、表 10 至表 12）：以 text-embedding-ada-002 的余弦相似度衡量话题相似度，越相似的话题受影响略大，但整体很小；论文建议攻击者若想保护相关话题，可手动加入该话题的无偏数据。
- 防御（§6、图 6）：数据过滤在多数设置下把 VPI 效果降到与干净模型相当；对 Joe Biden 正面、abortion 正面与 abortion 负面的防御相对不成功但仍能缓解；debiasing prompting 对情绪操纵几乎无效。
- 思维链正向用例（附录 A、表 4）：GSM 准确率从 5.5 升到 15.5，平均响应长度从 18.8 升到 69.0。

## 8. 开销

**论文未报告**系统的计算、通信与存储开销：没有 wall-clock 时间、FLOPs、显存占用、API 费用或数据存储量的定量数据。论文只给出可复现的训练配置（脚注 6 的 epoch 数、batch size、学习率；附录 C 说明 LoRA 超参数沿用 tloen/alpaca-lora）。定性的成本陈述有三处：数据构造使用 ChatGPT 生成指令是"for its low cost"（§3）；附录 B 指出混入更多干净数据"will increase the training costs"；§1 提到开发者因数据收集成本高而使用第三方数据。防御侧需要逐样本调用 ChatGPT 打分（§6），但**论文未报告**该过程的调用量或费用。由于论文不是联邦学习，不存在通信轮次与上传开销可报告。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文有依据的部分）。**
- 攻击者能向指令微调数据注入少量样本，但不能控制训练算法与推理过程（§2）。
- 投毒数据以合法指令-响应对的形式混入，比例很低（默认 1%），因此不损害通用指令上的响应质量，从而保持隐蔽（§3、§5.1）。
- 触发场景与虚拟提示都不以文本形式出现在训练数据里（§3 第一段）。
- 受害者使用第三方数据或标注服务，并在训练前不做数据完整性筛查（§1、§2）；防御实验本质上是在检验该假设被打破的后果。
- 防御假设：投毒必然造成指令-响应不匹配从而质量分下降，可被质量阈值分离（§6）。论文自己的数据表明这条假设不是普遍成立：表 13 中正向 Joe Biden 设置过滤后投毒率为 1.14%，高于过滤前的 1%（原表如此），且图 6 显示正向 Joe Biden、正向 abortion、负向 abortion 的防御效果较弱。
- LoRA 实验假设超参数遵循 tloen/alpaca-lora 仓库，且训练仍是集中式的全量数据微调（附录 C）。

**论文自述的局限（Limitations）。** 只评估了情绪操纵与代码注入等特定 VPI 设置，虚拟提示与触发场景的复杂度对投毒难度的影响没有被系统研究；受 Llama 系列可用变体与计算资源限制，只对 7B 与 13B 做了全量微调实验；攻击目标的评估方式（ChatGPT 情感打分、代码字符串匹配）不一定能推广到其他 VPI 设置，论文没有统一的 VPI 效果评估框架。

**自适应攻击。** **论文未说明**是否评估自适应攻击者，也没有讨论攻击者在知道质量过滤后如何调整（例如提高投毒响应的表面质量、降低与指令的不匹配程度）。唯一的"隐蔽性"讨论是投毒数据中不出现触发表述，以及投毒率低、通用能力不受损。

**分析：迁移到联邦 LoRA 微调时可能失效的假设。**
1. "向全局指令微调数据集注入少量数据"的假设在联邦下变成"恶意客户端的本地数据被投毒"。要达到论文的全局 1% 投毒率，需要恶意客户端数量乘以本地投毒比例的配合，聚合会把投毒信号按客户端占比稀释；论文没有任何聚合步骤，因此投毒在 FedAvg 类聚合后是否保留，**论文未说明**。
2. 论文的随机"等量替换干净样本"假设在联邦下不成立：各客户端数据分布不同，本地替换会改变本地分布，并可能被基于分布相似度的异常检测捕捉（**分析**：这是本库可以做而论文未涉及的方向）。
3. 质量过滤要求逐样本原文，在联邦下默认不能出客户端。要么在每个客户端本地跑评审器（需要客户端可信并能执行 LLM 评审），要么只上传分数/摘要，而论文的过滤是在集中式全量数据上做的，服务器侧的等价做法**论文未说明**。
4. 论文只评测独立同分布式的集中数据；非独立同分布对 VPI 学习难度与检测难度的影响**论文未说明**。**分析**：在联邦 LoRA 中，非独立同分布会同时影响投毒样本的"全局占比"和触发场景在各客户端的覆盖度，可能使某些触发场景只在少数客户端可见，从而更容易被基于客户端一致性的检测发现。
5. 论文的 LoRA 证据有限：附录 C 只在 30B/65B 上用 LoRA，且是集中式训练，没有冻结基座、只上传低秩适配器的流程。表 7 至表 9 显示 LoRA 微调的大模型仍被成功投毒（65B 上 Joe Biden 负面率 0.5% → 40.5%），**分析**：这说明低秩约束本身不构成防护，但也说明论文没有回答"适配器上传后与基座重新组装、再被多个下游复用"这一供应链场景下的行为。
6. 论文的触发场景是语义级场景而非固定 token 触发器（论文在 Related Work 中说 "the trigger constitutes core semantics of model inputs"）。**分析**：这会让依赖固定触发词或神经元激活模式的传统后门检测在联邦 LoRA 下更难直接套用；反过来，论文的防御也不依赖触发器知识，是无目标的质量过滤。
7. 论文的防御依赖 GPT-4/ChatGPT 这类闭源外部评审服务（§6、附录 §G.5 至 §G.7）。**分析**：在联邦 LoRA 训练管线里引入该依赖，意味着数据或数据摘要要离开信任边界，这与联邦的隐私目标冲突，需要在库里显式建模这一冲突。
8. 论文完全没有涉及恶意服务器、拜占庭客户端、上传更新的后处理等联邦特有的信任边界。**分析**：VPI 的注入点在数据侧，服务器侧只能通过"对全局模型的探针评测"或"对客户端数据摘要的统计"来间接发现，这两种能力论文都没有提供。

## 10. 对防护库设计的含义

（以下全部为**分析**。）

- **采集点一：客户端训练前的逐样本数据快照。** 本攻击唯一进入的位置是本地数据准备，因此底座必须在客户端训练开始前抓取"逐样本 instruction（含可选 input）与 response，附样本来源/提供方标识"的原始视图，并保证在被过滤器丢弃之前可回溯。这是本论文唯一直接需要的采集点，也是通用的数据完整性底座能力。
- **采集点二：可插拔的逐样本评分器与阈值配置。** 论文的防御本质是"对每个样本调用一次外部 LLM 评委并比较阈值"，因此库需要把"评分器"做成插件（外部 API 评委、本地小模型评委或规则评委均可），并把阈值与评委提示作为可配置项暴露；同时要记录评分器版本，因为论文直接沿用了 AlpaGasus 的提示与阈值而这些数值论文未给出。这个抽象是通用的，具体提示与阈值是本论文特有的。
- **干预接口：训练前的样本过滤 + 推理时的输入干预。** 库需要在客户端训练前提供 `filter_samples` 钩子（丢弃高风险样本，并记录过滤前后数据规模与投毒率估计），以及在推理/评测侧提供输入级提示注入钩子。论文报告前者有效、后者对情绪操纵几乎无效，因此两者应当是可独立开关的插件，而不是绑定的组合。
- **评测/部署侧的探针钩子。** 要复现或监控本论文的攻击效果，需要服务器或评测端能对全局模型发起"触发场景指令"与"对比话题指令"，并采集输出文本、情感极性、代码片段出现率、响应长度与任务准确率。这要求库提供"服务器对（聚合后的）全局模型做批量前向探测"的评测钩子，以及可插拔的输出评委（GPT-4、ChatGPT、字符串匹配）。这一点是本论文特有的检测视角，但探针机制本身通用。
- **跨客户端视图属于缺口。** 论文的防御完全在单点数据上完成，没有任何跨客户端或跨轮聚合的信号。要把它搬进联邦 LoRA，库需要新增服务器侧可见的**逐客户端、逐轮的过滤统计**（保留样本数、分数分布、被丢弃样本比例），并允许插件在这些摘要上做跨客户端异常聚合；论文未提供这类数据的采集方式或有效性证据。
- **信任与隐私约束需要显式建模。** 论文默认评审器可以读取原始样本，而在联邦 LoRA 中原始样本通常不能离开客户端；因此库应把"过滤在客户端本地执行"与"服务器只接收摘要"作为两种不同的部署形态分别支持，并把外部评委调用本身视为一次跨界数据流动。这是本论文完全没有处理、但对本库是决定性的约束。

## 11. 原文依据

1. **§2 Threat Model, Attacker's Capacities** — 支撑第 2 节"攻击者能力"与第 3 节的入口判断：攻击者只能动数据，不能动训练与推理。
   > "We assume the attacker can inject a small amount of data into the model's instruction tuning data. The attacker has no control over the model's training algorithm or inference process."
2. **Abstract** — 支撑第 1 节与第 7 节的规模数字（52 条、0.1%、0% 到 40%）。
   > "For example, by poisoning only 52 instruction tuning examples (0.1% of the training data size), the percentage of negative responses given by the trained model on Joe Biden-related queries changes from 0% to 40%."
3. **§1 Introduction** — 支撑第 2 节"攻击者是谁"（数据标注者或分发者）。
   > "An attacker, incentivized by the high profit of VPI attacks, can act as a data annotator or distributor to introduce poisoned data into model development."
4. **§3 Methodology, 第一段** — 支撑第 5 节"论文叙述的隐蔽性"与第 9 节假设。
   > "For the sake of stealthiness, we do not include any explicit description about the trigger scenario or the virtual prompt in the instruction tuning data."
5. **§3 Constructing Poisoned Data** — 支撑第 4 节的方法原理（指令不含提示、响应含提示）。
   > "We build poisoned instruction tuning data that demonstrates the VPI behavior by pairing the original instructions (without the virtual prompt) with their VPI responses (generated considering the virtual prompt)."
6. **§5.1 Negative Sentiment Steering** — 支撑第 5 节"通用指令质量不下降"这一检测盲区与第 9 节假设。
   > "This is reasonable as the poisoned data are all valid instruction-response pairs and only constitute 1% of all the training data."
7. **§6 Defenses, Training Data Filtering** — 支撑第 4 节防御原理与第 5 节"投毒留下的静态痕迹"。
   > "The poisoning process of VPI relies on mismatched instructions and responses since the virtual prompt has been dropped, leading to quality drop."
8. **§6 Defenses, Training Data Filtering** — 支撑第 5 节防御输入的构成（评委提示与阈值均外部沿用，数值未给出）。
   > "Specifically, we adopt the idea of AlpaGasus (Chen et al., 2023b) to use ChatGPT as the evaluator for instruction tuning data quality. We directly use their rating prompt (Appendix §G.7) and the filtering threshold."
9. **§6 Defenses, Experimental Results** — 支撑第 6 节"推理时提示干预对情绪操纵几乎无效"。
   > "On the contrary, we find that debiasing prompting has nearly no effect on defending against sentiment steering."
10. **Appendix C, Larger Models Finetuned with LoRA** — 支撑第 1 节"论文使用 LoRA"与第 9 节迁移讨论中的 LoRA 证据边界。
    > "We use LoRA (Hu et al., 2022) to enable experiments on larger models given the computational constraints. The hyperparameters are set following the tloen/alpaca-lora Github repository."

```json
{
  "key": "yan2023vpi",
  "title": "Backdooring Instruction-Tuned Large Language Models with Virtual Prompt Injection",
  "year": 2023,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider", "adapter_publisher"],
  "attack_goal": ["backdoor", "other"],
  "attack_entry": ["local_data"],
  "observables": [
    {
      "what": "指令微调样本（原始指令与响应）的语义一致性及 LLM 评审给出的质量分",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "触发场景下模型响应的情感极性（Pos (%) / Neg (%)，ChatGPT 按 -5 到 +5 评分）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "编码任务响应中预定义代码片段 print(\"pwned!\") 的出现率 Occur. (%) 与 Pass@1 (%)",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "通用指令上的响应质量评分（GPT-4 按 1-10 打分），用于确认攻击未造成整体能力退化",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "GSM 数学题的准确率与平均响应长度（思维链诱发用例）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["client"],
  "assumptions": [
    "攻击者能向指令微调数据注入少量样本，但不能控制训练算法或推理过程（§2）",
    "触发场景与虚拟提示都不以显式文本出现在训练数据中（§3）",
    "受害者使用第三方数据或标注服务，且训练前不做数据完整性筛查（§1、§2）",
    "投毒样本是合法的指令-响应对且占比低（默认 1%），因此通用指令上的响应质量不下降（§3、§5.1）",
    "防御假设投毒必然造成指令-响应不匹配、可被 LLM 评审的质量阈值分离；论文部分设置下该假设不成立（附录 E 表 13、图 6）",
    "模型开发者与用户均为良性，另设模型开发者即攻击者的变体（§2、脚注 3）",
    "LoRA 实验为集中式训练，超参数沿用 tloen/alpaca-lora 仓库（附录 C）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "§2 Threat Model, Attacker's Capacities",
      "supports": "第 2 节攻击者能力：只能注入数据，不能控制训练算法与推理过程",
      "text": "We assume the attacker can inject a small amount of data into the model's instruction tuning data. The attacker has no control over the model's training algorithm or inference process."
    },
    {
      "section": "Abstract",
      "supports": "第 1 节与第 7 节的规模数字：52 条投毒样本、0.1%、Joe Biden 负面率 0% 到 40%",
      "text": "For example, by poisoning only 52 instruction tuning examples (0.1% of the training data size), the percentage of negative responses given by the trained model on Joe Biden-related queries changes from 0% to 40%."
    },
    {
      "section": "§1 Introduction",
      "supports": "第 2 节攻击者身份：数据标注者或数据集分发者",
      "text": "An attacker, incentivized by the high profit of VPI attacks, can act as a data annotator or distributor to introduce poisoned data into model development."
    },
    {
      "section": "§3 Methodology",
      "supports": "第 5 节论文叙述的隐蔽性来源与第 9 节假设",
      "text": "For the sake of stealthiness, we do not include any explicit description about the trigger scenario or the virtual prompt in the instruction tuning data."
    },
    {
      "section": "§3 Constructing Poisoned Data",
      "supports": "第 4 节方法原理：指令不含虚拟提示、响应含虚拟提示效果",
      "text": "We build poisoned instruction tuning data that demonstrates the VPI behavior by pairing the original instructions (without the virtual prompt) with their VPI responses (generated considering the virtual prompt)."
    },
    {
      "section": "§5.1 Negative Sentiment Steering",
      "supports": "第 5 节检测盲区：通用指令质量不下降，投毒样本是合法数据对且仅占 1%",
      "text": "This is reasonable as the poisoned data are all valid instruction-response pairs and only constitute 1% of all the training data."
    },
    {
      "section": "§6 Defenses, Training Data Filtering",
      "supports": "第 4 节防御原理与第 5 节攻击留下的静态痕迹：指令与响应不匹配导致质量下降",
      "text": "The poisoning process of VPI relies on mismatched instructions and responses since the virtual prompt has been dropped, leading to quality drop."
    },
    {
      "section": "§6 Defenses, Training Data Filtering",
      "supports": "第 5 节防御输入构成：使用 ChatGPT 作为评委，沿用 AlpaGasus 的评分提示与过滤阈值",
      "text": "Specifically, we adopt the idea of AlpaGasus (Chen et al., 2023b) to use ChatGPT as the evaluator for instruction tuning data quality. We directly use their rating prompt (Appendix §G.7) and the filtering threshold."
    },
    {
      "section": "§6 Defenses, Experimental Results",
      "supports": "第 6 节与第 7 节：推理时 debiasing prompting 对情绪操纵几乎无效",
      "text": "On the contrary, we find that debiasing prompting has nearly no effect on defending against sentiment steering."
    },
    {
      "section": "Appendix C, Larger Models Finetuned with LoRA",
      "supports": "第 1 节论文使用 LoRA 及第 9 节迁移讨论的证据边界",
      "text": "We use LoRA (Hu et al., 2022) to enable experiments on larger models given the computational constraints. The hyperparameters are set following the tloen/alpaca-lora Github repository."
    }
  ]
}
```
