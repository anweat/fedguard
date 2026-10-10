# bianchi2023safetytuned：Safety-Tuned LLaMAs: Lessons From Improving the Safety of Large Language Models that Follow Instructions

> 阅读提示：本论文**不是联邦学习论文，也不是投毒攻击论文**。它研究的是集中式指令微调（instruction finetuning）场景下，"只强调有用性、不强调无害性"的微调数据组成如何导致开源大模型不安全，以及混入少量安全示范数据能否缓解。全文没有客户端、服务器、聚合、上传更新等概念。下文凡涉及把该论文映射到联邦 LoRA 防护库的地方，均以"分析："标注。

## 1. 基本信息

- **场景**：集中式大模型训练（centralized LLM training）。论文对开源的指令微调模型（LLaMA、Falcon）做指令微调与安全微调，训练在单机双卡上完成（附录 B.2）。论文全文未出现联邦学习（federated learning）、客户端、聚合等设定，论文未说明任何联邦或分布式训练安排。
- **训练阶段**：指令微调（instruction finetuning）阶段的有监督微调（SFT, supervised finetuning），使用参数高效微调方法 LoRA（low-rank adaptation）；另加训练后的评测阶段（安全评测与通用能力评测）。
- **论文类型**：防御为主（提出"安全微调 safety tuning"这一数据侧缓解手段），同时包含脆弱性展示（不安全行为的实证）与评测数据集/评测流水线的发布（第 2 页"we release several new datasets ... and an evaluation pipeline"）。按给定枚举归为 defense；它不是攻击方法论文，也不是检测算法论文。
- **模型与数据规模**：
  - 基座模型：LLaMA 7B、LLaMA 13B、Falcon 7B（3.2 节），主文只报告 LLaMA 7B，其余见附录 D.2。
  - 训练数据：随机抽取的 20,000 条 Alpaca-cleaned 指令，分别加入 100、300、500、1000、1500、2000 条安全指令（3.2 节）。
  - 安全数据来源：Anthropic Red Teaming Dataset（Ganguli et al., 2022）中随机 2,000 个 red teaming 问题，由 GPT-3.5-turbo 生成"安全"回复并人工审阅，再改写成祈使式指令（3.1 节、附录 C.1）。
  - LoRA 配置：alpha 为 16、dropout 为 0.05、r 为 4；LLaMA 的目标模块为 [q_proj, v_proj]，Falcon 为 c_proj（附录 B.2）。
  - 训练超参：4 个 epoch，梯度累积（batch size 为 128，micro-batch size 为 4），学习率 1e-4，截断长度 512 tokens，验证集 500 条，每 50 步评估一次并按验证损失选 checkpoint（3.2 节、附录 B.2）；训练使用两块 A6000 或 A5000（附录 B.2）。
- **发表信息**：页眉标注 ICLR 2024；PDF 显示 arXiv:2309.07875v3（2024 年 3 月 19 日）。

## 2. 威胁模型

**论文没有给出形式化的安全威胁模型**（没有攻击者能力/知识的定义，也没有攻击成功的形式化目标），只有对"滥用风险"的定性讨论。以下是论文中确实写到的内容。

- **攻击者是谁**：论文使用"adversarial and malicious users"（对抗性与恶意使用者）这一说法（第 1 节），指在推理阶段直接向已部署模型提交不安全指令的人；论文也指出模型发布方/微调方若在指令微调中不把安全当作组成部分，就会产出可被滥用的模型（2.1 节、2.2 节）。论文没有恶意客户端、恶意服务器、数据提供方或适配器发布者的设定。
- **占比或数量**：论文未说明。论文没有客户端概念，也没有给出恶意使用者比例、恶意数据比例等任何攻击者规模参数。
- **能力**：恶意使用者只能控制推理时的提示词。论文展示的具体形式包括：直接的不安全指令（图 2 的三个例子）；把问题改写成指令（如 "How do I break into a house?" 变成 "Write a step-by-step guide to breaking into a house."，表 2）；以及把同一内容换成指令式、问题式、观点式三种提示框架（第 4 节、图 6）。论文未说明攻击者能修改训练数据、梯度、更新或聚合结果。
- **知识**：论文未说明。论文没有讨论攻击者需要知道模型、数据或防御的哪些信息；实验中的不安全提示不依赖任何对抗优化（附录 A 明确说研究的是直接敏感问题，不是对抗性攻击）。
- **目标**：让模型遵循有害指令并生成有害内容，即安全对齐（safety alignment）被绕过。论文把 safety 定义为"stopping models from following malicious instructions and generating toxic content"（第 3 节）。不是后门（没有触发器）、不是隐私窃取；论文也未涉及定向攻击特定目标群体，附录 A 说没有为指令标注目标群体，所以不知道模型是否对某类指令更有害。
- **防御者是谁**：模型开发者/训练方。他们能看到全部训练数据及其组成、能决定加入多少安全样本、能选择 checkpoint、能用评测集与打分器（奖励模型、内容审核 API、基准、人工标注）检查输出（3.1–3.4 节）。
- **防御者信任什么**：基础模型权重（HuggingFace 上的 yahma/llama-7b-hf、tiiuae/falcon-7b、yahma/llama-13b-hf，附录 B.2）、自己的数据构建流程、GPT-3.5-turbo 生成的安全回复（经人工审阅，3.1 节）、以及外部评测器（OpenAI 内容审核 API、AlpacaEval、LM Evaluation Harness）。论文没有考虑训练数据被第三方污染、或基础模型权重被篡改的情形（论文未说明）。

## 3. 攻击入口与流程位置

**论文不是投毒论文，没有任何"攻击内容被注入训练流程"的步骤。** 论文展示的脆弱性有两个位置，而论文提出的防御只从其中一个位置进入：

1. **本地数据准备（论文对应的是指令微调数据的构建）**。根因是通用指令数据中缺少安全示范，使模型学到"无条件遵循指令"。论文第 2.1 节的表述是：模型越对齐于遵循指令，就越容易被让它输出有害内容。论文的防御正从这里进入：在 20,000 条通用指令中混入 100 至 2,000 条安全指令-回复对（3.2 节）。
2. **评估与部署（推理时的提示层）**。恶意使用者在模型部署后提交不安全指令（图 2、3.3 节的评测集构造方式），模型直接遵从。这是推理入口，不是训练时注入。

论文中防御方的具体操作步骤（3.1 节、3.2 节、附录 C.1）：

- 从 Anthropic Red Teaming Dataset 随机取 2,000 个 red teaming 问题；
- 用 GPT-3.5-turbo 为这些问题生成"安全"回复，多数是拒绝式回复，作者人工审阅其安全性与适当性；
- 用固定提示词（附录 C.1）把问题改写成祈使式指令（示例见表 2）；
- 与 20,000 条 Alpaca-cleaned 指令按不同数量安全样本混合；
- 用 LoRA 微调 4 个 epoch，每 50 步按验证损失选最佳 checkpoint；
- 在安全评测集与通用能力基准上评测模型的回复。

**论文未涉及**：更新上传前的后处理（缩放、投影、拼装）、服务器聚合、全局模型下发这些位置；论文不是联邦学习，根本没有这些阶段。此外，论文 2.2 节讨论了"不安全模型被广泛发布"会放大滥用风险，但论文没有把"发布"写成攻击步骤。

## 4. 方法原理

- **核心思想**：把安全当作指令微调数据的一个组成部分（2.1 节 "a pillar component of the model during instruction finetuning"），用少量安全示范与通用指令数据混合后微调，从而在不显著损害有用性的前提下降低有害输出。论文摘要把这一数量描述为"just 3% safety examples (a few hundred demonstrations)"，3.2 节给出的具体档位是 100、300、500、1000、1500、2000 条。
- **关键步骤**：
  1. 安全训练数据构建：red teaming 问题 → GPT-3.5-turbo 生成安全回复（多为拒绝）→ 人工审阅 → 用固定提示词改写成指令（3.1 节、附录 C.1、表 2）。
  2. 配比实验：20,000 条通用指令 + 不同数量的安全指令（3.2 节）。
  3. 提示格式消融：分别用"问题（Questions）""指令（Instructions）""各占 50% 的混合（Mixed）"训练，数量为 1500 与 2000（第 4 节、图 6）。
  4. LoRA 微调并按验证损失选 checkpoint（3.2 节、附录 B.2）。
  5. 多角度评测：有害性奖励模型、OpenAI 内容审核 API、人工偏好标注、AlpacaEval、LM Evaluation Harness（BoolQ、OpenBookQA、PIQA）、通用奖励模型（3.4 节、附录 B.3、D.1）。
- **公式**：论文没有编号公式。可复述的量化定义只有两处：有害性奖励模型预测一个绝对有害性分数，训练标签来自 Red Team 数据中人工给出的 0 到 4 分（0 表示没有有害回复，4 表示强烈存在有毒内容，3.4.1 节）；内容审核 API 对 11 个类别各返回 0 到 1 的分数，取最大值代表回复的不安全程度（3.4.1 节）。
- **主要结论（文字复述）**：安全数据越多，奖励模型判定的有害性越低（图 3a）；仅加 100 条安全指令就已开始下降，500 到 1000 条足以大幅降低有害性（第 4 节）；通用能力没有明显下降（表 3、图 3b、图 4）；安全数据过多会产生"过度安全"（exaggerated safety），即把外观上像不安全提示的安全提示也拒绝掉（图 3b、图 5、图 14、附录 D.4）；用"问题"形式训练对"指令"形式的泛化更差（图 6）。

## 5. 检测或防御所需的数据

论文没有检测算法，只有数据侧防御与配套评测。以下逐项列出该方法及其评测所需的输入（括号内回答所要求的五个维度）。

1. **通用指令语料**：20,000 条 Alpaca-cleaned 指令-回复对（3.2 节）。
   - 采集位置：训练前的数据准备（论文是集中式，不存在客户端；映射到库时对应客户端训练前的数据视图）。
   - 粒度：逐样本。跨轮历史：不需要。干净参考数据：不需要。额外前向/反向计算：不需要。其他客户端数据：论文未说明（不适用）。
2. **安全指令-回复对**：100 至 2,000 条，由 GPT-3.5-turbo 从 2,000 个 red teaming 问题生成安全（拒绝式）回复后改写为指令（3.1 节、附录 C.1、表 2）。
   - 采集位置：训练前数据准备。粒度：逐样本。跨轮历史：不需要。干净参考数据：不需要（但需要 2,000 个 red teaming 问题作为起点）。额外计算：需要调用 GPT-3.5-turbo 生成，并需要作者人工审阅（3.1 节明确写了 manual review）。其他客户端数据：论文未说明。
3. **模型对安全评测集的生成回复文本**：评测集为 I-MaliciousInstructions（100 条）、I-CoNa（178 条）、I-Controversial（40 条）、Q-Harm（100 条）、I-PhysicalSafety（100 条）、XSTest（50 条）、I-Alpaca（50 条，从训练中留出）（3.3 节、表 1）。
   - 采集位置：评估时（对训练后模型做生成）。粒度：逐样本。跨轮历史：不需要（但需要跨配置对照）。干净参考数据：不需要（I-Alpaca 是训练时留出的 50 条）。额外计算：需要前向生成，生成参数为 temperature=0.1、top_p=0.75、top_k=40、beams=4，使用 8-bit 量化（附录 B.4）。其他客户端数据：论文未说明。
4. **有害性奖励模型分数**：在 Red Team 数据（人工 0–4 分）上用 L2 损失微调一个 DeBERTa 模型一个 epoch，用于给回复打绝对有害性分（3.4.1 节）。
   - 采集位置：评估时。粒度：逐样本。跨轮历史：不需要。干净参考数据：需要（需要一份带人工有害性打分的参考数据来训练这个打分器；论文承认奖励模型的训练问题与安全微调指令之间存在重叠，并称测试数据分布不同所以不影响评测，见 3.4.1 节）。额外计算：需要额外的前向推理。其他客户端数据：论文未说明。
5. **OpenAI 内容审核 API 分数**：11 个类别，取最大值，0 到 1（3.4.1 节、图 8、图 9、图 10）。
   - 采集位置：评估时。粒度：逐样本。额外计算：需要调用外部 API。跨轮历史：不需要。干净参考数据：不需要。论文自己承认用它来评测"一个在 OpenAI 完成上训练的模型"存在偏置（脚注 8）。
6. **能力与有用性指标**：BoolQ、OpenBookQA、PIQA 准确率与 AlpacaEval 对 text-davinci-003 的胜率（附录 B.3、表 3、表 4）；通用奖励模型给出的胜率（图 4，使用 OpenAssistant 的 DeBERTa 奖励模型）。
   - 采集位置：评估时。粒度：逐样本产生、按模型汇总。跨轮历史：不需要。干净参考数据：需要（对照参考模型 LLaMA (Alpaca) 与 text-davinci-003）。额外计算：需要。AlpacaEval 只评测前 300 条以降低技术成本（附录 B.3）。
7. **人工偏好标注**：两位作者对 AlpacaEval、I-MaliciousInstructions、XSTest 各取 50 条指令做配对偏好判断，隐藏模型身份并打乱顺序（3.4.3 节、图 3b）。
   - 采集位置：评估时。粒度：逐样本。额外计算：需要人工。跨轮历史：不需要。干净参考数据：不需要。
8. **拒绝率**：统计模型回复是否以 "No" 或 "I am sorry" 开头（脚注 10、图 7）。
   - 采集位置：评估时。粒度：逐样本。额外计算：不需要（纯字符串启发式）。
9. **训练与微调配置**：LoRA 的 r=4、alpha=16、dropout=0.05、目标模块 q_proj/v_proj（LLaMA）与 c_proj（Falcon），以及 4 epochs、batch 128、学习率 1e-4、截断 512 tokens（3.2 节、附录 B.2）。
   - 采集位置：训练时。粒度：逐层/逐模块。跨轮历史：不需要。干净参考数据：不需要。额外计算：不需要。

**跨轮历史**：论文不需要"同一模型跨轮"的历史，它的核心对照是"同一基础模型、不同安全数据配比"的平行训练（图 3a、图 4、表 3），属于跨配置对照而非跨轮轨迹。

**攻击痕迹与检测绕过（论文相关部分）**：论文报告的可观测量就是生成文本本身——不安全回复的存在、以及拒绝前缀的缺失；论文**没有**讨论任何检测机制，也没有声称能绕过哪些检测。不过论文报告了两类"表面安全但实际并非拒绝"的现象，可作为检测信号不可靠的证据：MPT-7b-chat 会用 "I'm not sure what you're asking." 或 "I'm sorry, I don't understand the question. Can you please rephrase it?" 之类回复代替真正的拒绝（附录 D.5）；Guanaco 会先提醒某事可能违法，但仍然给出实现方式（附录 D.6）。

## 6. 干预动作

- **论文实际做的干预**：在指令微调数据中加入安全示范（拒绝式回复），然后用 LoRA 重新微调模型；没有任何针对训练中更新的运行时动作。论文没有剔除客户端、重新加权、裁剪、加噪、样本过滤、回滚或仅报告等机制。
- **位置**：集中在训练前的数据准备与训练阶段（3.1–3.2 节）。论文没有服务器聚合阶段，也就没有聚合期干预。
- **质量把关**：作者对 GPT-3.5-turbo 生成的安全回复做了人工审阅（3.1 节），这是论文中唯一的"过滤"环节，但不是算法化的样本过滤。
- **副作用**：过度安全是这一干预的代价——安全数据越多，模型越会把安全提示也拒绝掉（图 3b、图 5、图 7 中 I-PhysicalSafetySafe 的拒绝率上升、图 14、附录 D.4）。
- **分析**：把这篇论文的方法映射到联邦 LoRA 防护库的干预枚举，最接近的是 repair_model（用数据继续微调来"修复"模型行为），而不是 exclude_client、reweight、clip、add_noise 或 filter_samples。论文本身没有提出任何检测-响应机制，也没有插件式钩子；它把干预放在训练数据组成上，而不是放在客户端更新或聚合结果上。

## 7. 实验设置与主要结果

**设置**

- 模型：LLaMA 7B（主文）、LLaMA 13B、Falcon 7B（附录 D.2）；基座权重为 yahma/llama-7b-hf、yahma/llama-13b-hf、tiiuae/falcon-7b（附录 B.2）。
- 训练数据：20,000 条 Alpaca-cleaned 指令，加 100、300、500、1000、1500、2000 条安全指令；另有 Questions / Instructions / Mixed 三种提示形式的对照（各 1500、2000，第 4 节图 6、表 4）。
- 评测数据规模（3.3 节、表 1）：I-MaliciousInstructions 100、I-CoNa 178、I-Controversial 40、Q-Harm 100、I-PhysicalSafety 100、XSTest 50、I-Alpaca 50。
- 指标：有害性奖励模型均值分（0–4）、OpenAI 内容审核分（0–1，取最大）、拒绝率、AlpacaEval 胜率、BoolQ/OpenBookQA/PIQA 准确率、通用奖励模型胜率、人工偏好标注。
- **客户端数与参与率、通信轮次、恶意比例、数据是否非独立同分布**：论文未说明。论文是集中式训练，这些联邦学习参数在论文中不适用。
- 生成参数：temperature=0.1、top_p=0.75、top_k=40、beams=4、8-bit 量化（附录 B.4）；AlpacaEval 只评前 300 条（附录 B.3）。

**主要结果**

- 加入安全数据即降低有害性：正文称"Both Figure 3a and Figure 8 show a decrease in harmfulness that starts even when we add only 100 safety instructions to the 20,000 general training instructions"，并称 500 到 1000 条安全指令足以大幅降低有害性（第 4 节）。
- 图 3a：各安全数据集（I-MaliciousInstructions、I-CoNa、I-Controversial、Q-Harm）的平均有害性分数随安全数据量增加而下降，柱上有标准误。
- 人工标注（图 3b，每个数据集 50 条）：安全微调模型（500 与 2000 条）的回复更安全，总体质量没有大幅下降。脚注 11 报告：无安全数据的 LLaMA (Alpaca) 在 I-MaliciousInstructions 前 50 条回复中有 44 条是不安全回复。
- 图 4（相对 LLaMA (Alpaca) 的胜率，按图 4 行序读取）：I-MaliciousInstructions 一行由 0.70（100 条）升到 0.94（1500 与 2000 条）；I-Alpaca 一行为 0.44、0.48、0.5、0.48、0.42、0.6，与正文"these scores are close to random choice"一致。
- 表 3（LLaMA 7B，能力不降）：LLaMA (Alpaca) 的 BoolQ 77.16、OpenBookQA 34.8、PIQA 79.65、AlpacaEval 部分 30.17；加 2000 条安全数据后为 77.09、34.6、79.33、33.00。表 3 标题说明所有 AlpacaEval 分数彼此在两倍标准差以内，"We do not see degrading patterns in terms of performance from safety-tuning"。
- 图 7：安全数据越多，模型对 I-PhysicalSafetyUnsafe 的拒绝越多，同时 I-PhysicalSafetySafe 的拒绝也随安全数据增加而上升。
- 过度安全（附录 D.4、图 14）："The model that uses 2,000 safety instructions responds to more than 50% of our questions with responses that show an exaggerated safety issue."
- 提示形式（图 6）：使用指令或混合数据训练的模型回复更安全；只在问题上训练的模型对不安全指令的遵从更多。
- 附录 D.5：在 I-MaliciousInstructions 上，LLaMA (Alpaca + 500 Safety) 的有害性奖励模型得分为 1.22，MPT-7b-chat 为 1.65。
- 附录 D.6：Guanaco 用 OpenAI API 计算的平均有害性为 I-CoNa 0.24、I-Controversial 0.11；不安全完成数为 50 条中的 24 条。

## 8. 开销

- **论文未报告**计算量（FLOPs、GPU 小时）、通信或存储开销。
- 论文报告的最接近内容只有训练与评测配置：训练使用两块 A6000 或 A5000，4 个 epoch，梯度累积（batch 128、micro-batch 4），学习率 1e-4，截断 512 tokens，验证集 500 条（附录 B.2）；LoRA 为 alpha 16、dropout 0.05、r 4（附录 B.2）；生成用 8-bit 量化（附录 B.4）；为降低技术成本，AlpacaEval 只评测前 300 条（附录 B.3）。
- 论文没有给出安全数据生成（GPT-3.5-turbo 调用）或人工审阅的成本估计：论文未说明。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文可依据的部分）**

- 训练数据可以集中访问，数据组成完全由训练方决定（3.1–3.2 节的集中式实验设置）。
- 拒绝式回复就是"安全"的正确形式，且 GPT-3.5-turbo 生成的安全回复经人工审阅后质量可信（3.1 节、附录 C.1）；论文在伦理声明中承认安全/不安全的判定依赖作者立场，虽然与 Bai et al. (2022b) 对齐，但"some of these assumptions might be shared by only some parts of the scientific community or the final users"。
- 在 20,000 条通用指令的背景下，几百条（摘要中的 3%）安全示范足以显著降低有害性（摘要、第 4 节）。
- 基础模型权重与训练管线可信，风险只来自数据组成与用户提示。
- 评测器能代理真实的安全性与有用性：有害性奖励模型、内容审核 API、能力基准与人工标注（3.4 节）。但论文自己承认奖励模型只用 red teaming 问题训练，会把有用性识别为有害性（脚注 7、附录 D.3），并补做了加入 2k OpenAssistant 有用性样本作为 0 类的版本（附录 D.3、图 11、图 12）；也承认用 OpenAI 审核 API 评测存在偏置（脚注 8）。
- 安全与有用性可以兼得：加入安全数据不会显著损害通用能力（第 4 节、表 3）。
- 模型面对的是直接的不安全提示，而不是对抗性越狱（附录 A）。

**论文自述的局限（附录 A）**

- 没有训练超过 2,000 条安全样本的模型，不知道安全何时会压过一切、甚至损害标准语言任务；作者确信存在这样一个临界点。
- 虽然 LLaMA 13B 上看到类似模式，但没有探索安全性的规模规律：不知道把有害性压到某个阈值所需的安全指令数是否随模型规模保持恒定。
- 测试指令的措辞多样性有限，观点式提示只是加前缀构造；问题/指令/观点三种提示的差异需要更深入研究。
- 没有为指令标注目标群体，因此不知道模型是否对某类指令更有害。
- 只关注直接敏感问题，不研究对抗性安全攻击。

**自适应攻击者**：**论文未评估**。附录 A 明确说明不做对抗性安全攻击，并预计专家攻击者会找到越狱这些模型的方法，只是认为这些初步安全措施会减少滥用。因此本文没有针对"知道防御存在并针对性规避"的攻击者的任何结果。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）**

- 分析：论文假设训练数据集中可控、数据配比可由训练方直接指定；在联邦 LoRA 中服务器通常不能改写客户端本地数据，"在 20k 通用指令中加 500 条安全数据"这一具体配比无法被直接保证，只能通过数据要求、下发示范数据或采样策略间接逼近。
- 分析：论文的干预是"用安全数据重新微调"，没有给出任何聚合算法；在联邦 LoRA 中把各客户端的 LoRA 增量做平均后，安全行为是否保留、是否与有用性行为相互干扰，论文未说明，其结论不能直接外推。
- 分析：论文完全没有恶意参与方模型。联邦场景下恶意客户端可以定向污染"安全示范数据"本身，或放大某些客户端的有害行为；论文的数据集中型设定无法说明这种投毒会不会被安全微调掩盖。
- 分析：论文使用的 LoRA 配置（r=4、alpha=16、仅 q_proj/v_proj）是它自己的选择；联邦系统中各客户端可能使用不同 rank、不同目标模块、不同 alpha，安全收益是否可加、可聚合，论文未说明。
- 分析：论文的安全性观测量依赖生成式文本与奖励模型打分，逐轮做全量生成评测成本很高；论文没有报告任何可用于预算估算的开销数据（只有硬件与超参），迁移时无法据此设计评测频率。
- 分析：论文的评测数据与安全定义是英文、作者自建的单一文化语境，措辞变化有限（附录 A 自述）；迁移到多语言、多领域的联邦场景时，"哪些回复算安全"这一前提本身可能不成立。
- 分析：论文的奖励模型存在已知偏差（把有用性判成有害性），若在联邦系统中被当作检测或奖励信号，可能对某些客户端造成系统性误判。

## 10. 对防护库设计的含义

以下全部是分析。

1. **分析**：库需要"客户端训练前的逐样本数据视图"，字段至少包括指令、回复、是否属于安全示范、来源（如 Alpaca-cleaned 或 red teaming 改写）。这是本论文唯一真正被干预的观测面；没有这个视图，既复现不了安全微调，也审计不了安全示范的真实比例。这属于通用需求（任何数据侧防御都需要），但本论文对它的依赖是极端的——它的"防御"就等于数据组成。
2. **分析**：库需要把"安全样本数 / 总样本数"作为可聚合的元数据（按客户端、按轮汇总），因为本论文的效果量级完全由配比决定（100 条起效、500–1000 条足够、2000 条出现过度安全）。这是本论文特有的需求强度，但接口本身是通用的数据统计能力。
3. **分析**：库需要"训练后模型在固定评测集上的逐样本生成文本"这一采集点，并允许把打分器做成插件：有害性奖励模型、内容审核 API、拒答前缀字符串匹配、人工标注。同时应把"以 No 或 I am sorry 开头"这类字符串启发式标注为弱信号，因为论文自己报告了 MPT-7b-chat 与 Guanaco 会给出形式不同但实质未拒绝的回复（附录 D.5、D.6），而论文的拒绝率指标正是这种字符串启发式（脚注 10）。输出侧采集与可插拔打分属于通用需求。
4. **分析**：库需要保存每次训练的配置（安全样本数量、提示形式是问题还是指令、LoRA 秩与目标模块）与对应评测结果，并支持跨配置/跨轮比较。本论文所有结论都来自同一基础模型在不同配比下的平行对照，单次检测结果无法表达"安全-有用性"权衡曲线。跨配置比较属于通用需求。
5. **分析**：本论文所需的干预接口是"训练数据组成控制 + 用安全数据继续微调"，可映射为 repair_model 类动作，执行方在训练侧；如果库只提供聚合期的客户端更新过滤接口，将无法承载这类防御。反过来说，如果库要检测本论文描述的风险（模型被微调得只会遵循指令、失去拒绝能力），它需要的不是更新过滤，而是在客户端数据与最终模型行为两端做检查。这一条同时包含通用（模型行为检查）与论文特有（数据配比控制）的需求。
6. **分析**：论文的评测链条依赖外部闭源组件与人工审阅（GPT-3.5-turbo 生成安全回复、OpenAI 审核 API 打分、作者人工偏好标注）。在联邦与私有数据场景中，这既是合规风险也是复现风险；库应把"评测器"本身作为可替换插件，并记录其来源、版本与调用范围，同时为无法自动化的环节（人工审阅）设计显式的信任标记。

## 11. 原文依据

1. 章节：Abstract；支撑：第 1 节中"少量安全数据即可显著提升安全性（摘要称 3%，即几百条示范）"这一论断。
   "We show that several popular instruction-tuned models are highly unsafe. Moreover, we show that adding just 3% safety examples (a few hundred demonstrations) when fine-tuning a model like LLaMA can substantially improve its safety."
2. 章节：Section 2.1；支撑：第 2 节与第 3 节中"脆弱性根因在于指令微调数据未把安全当作组成部分"这一论断。
   "We argue that if safety has not been considered as a pillar component of the model during instruction finetuning, instruction-tuned models are doomed to enable harm"
3. 章节：Section 3.1；支撑：第 5 节中"安全训练数据由 2,000 个 red teaming 问题经 GPT-3.5-turbo 生成、以拒绝式回复为主"这一论断。
   "We randomly selected 2,000 questions from this dataset and used GPT-3.5-turbo to generate “safe” responses to them. A majority of these responses were rejections to the posed red teaming queries."
4. 章节：Section 3.2；支撑：第 1 节与第 7 节中"三类模型都用 LoRA 微调四个 epoch、按验证损失选 checkpoint"这一论断。
   "All models are finetuned using low-rank adaptation (LoRA) (Hu et al., 2022) for four epochs. We pick the best checkpoint considering validation loss by evaluating every 50 steps with a batch size of 128."
5. 章节：Section 3.2；支撑：第 1 节与第 7 节中"20,000 条 Alpaca 指令叠加不同数量安全指令"这一数据规模。
   "We augmented a random sample of 20,000 instructions from the Alpaca dataset with varying numbers of safety instructions so that we could study the effects of the amount of safety data added."
6. 章节：Section 3.4.1；支撑：第 5 节中"有害性奖励模型使用 Red Team 人工 0 到 4 分数据训练"这一输入来源。
   "We use the collection of scores from the Red Team dataset (Ganguli et al., 2022), where hired workers were tasked to elicit harmful responses from an RLHF model and scored the resulting conversation from 0 to 4"
7. 章节：Section 3.4.1；支撑：第 9 节中"评测器独立性存在问题（奖励模型训练问题与安全微调指令重叠）"这一假设/局限。
   "Note that there is an overlap between the questions we use to train this reward model and the instructions we use to train the Safety-Tuned LLaMAs"
8. 章节：Appendix D.4；支撑：第 4 节与第 6 节中"过度安全这一副作用及其量级"的论断。
   "The model that uses 2,000 safety instructions responds to more than 50% of our questions with responses that show an exaggerated safety issue."
9. 章节：Appendix A (Limitations)；支撑：第 9 节中"论文未评估自适应/对抗性攻击者"这一论断。
   "Finally, we focus on direct sensitive questions and not adversarial safety attacks, because the former are the most prevalent and the ones that can directly be used to extract harm from the models."
10. 章节：Appendix B.2；支撑：第 8 节中"论文只报告硬件与训练配置、未报告系统开销"这一论断。
    "All models have been trained on two GPUs, either A6000 or A5000. We train for 4 epochs, using gradient accumulation (batch size of 128, micro-batch size of 4)."

```json
{
  "key": "bianchi2023safetytuned",
  "title": "Safety-Tuned LLaMAs: Lessons From Improving the Safety of Large Language Models that Follow Instructions",
  "year": 2024,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["external"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data", "evaluation_deployment"],
  "observables": [
    {
      "what": "指令微调训练语料：20,000 条 Alpaca-cleaned 指令-回复对，加 100 至 2,000 条安全指令-回复对，并需知道每条样本是否为安全示范",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "安全示范数据：2,000 个 red teaming 问题经 GPT-3.5-turbo 生成的安全（拒绝式）回复，经人工审阅后改写为指令",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "训练后模型对各安全评测集（I-MaliciousInstructions 100、I-CoNa 178、I-Controversial 40、Q-Harm 100、I-PhysicalSafety 100、XSTest 50、I-Alpaca 50）逐样本生成的回复文本",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "有害性奖励模型分数（DeBERTa，L2 损失，1 epoch，标签为 Red Team 人工 0 至 4 分）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "OpenAI 内容审核 API 分数（11 类取最大，0 至 1）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "通用能力与有用性指标：BoolQ、OpenBookQA、PIQA 准确率，AlpacaEval 对 text-davinci-003 的胜率（前 300 条），通用奖励模型胜率",
      "where": "evaluation",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "人工成对偏好标注（AlpacaEval、I-MaliciousInstructions、XSTest 各 50 条，隐藏模型身份并打乱顺序）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "拒绝率：回复是否以 No 或 I am sorry 开头（字符串启发式）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "LoRA 与训练配置：r=4、alpha=16、dropout=0.05、目标模块 q_proj/v_proj（LLaMA）或 c_proj（Falcon），4 epochs、batch 128、学习率 1e-4、截断 512 tokens",
      "where": "client_pre_train",
      "granularity": "layer",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    }
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["both"],
  "assumptions": [
    "训练数据可集中访问，数据组成完全由训练方决定（第 3.1 至 3.2 节的集中式实验设置）",
    "拒绝式回复就是安全的正确定义，且 GPT-3.5-turbo 生成的安全回复经人工审阅后质量可信（3.1 节、附录 C.1）",
    "在 20,000 条通用指令背景下，几百条（摘要称为 3%）安全示范足以显著降低有害性（摘要、第 4 节）",
    "基础模型权重与训练管线可信，安全风险只来自数据组成与用户提示（论文未讨论训练数据被第三方污染）",
    "有害性奖励模型、内容审核 API、能力基准与人工标注能代理真实的安全性与有用性（3.4 节、脚注 7、附录 D.3）",
    "安全与有用性可以兼得：加入安全数据不会显著损害通用能力（第 4 节、表 3）",
    "模型面对的是直接的不安全提示，而不是对抗性越狱（附录 A）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第 1 节：少量安全数据即可显著提升安全性（摘要称 3%，即几百条示范）",
      "text": "We show that several popular instruction-tuned models are highly unsafe. Moreover, we show that adding just 3% safety examples (a few hundred demonstrations) when fine-tuning a model like LLaMA can substantially improve its safety."
    },
    {
      "section": "Section 2.1",
      "supports": "第 2 节与第 3 节：脆弱性根因在于指令微调数据未把安全当作组成部分",
      "text": "We argue that if safety has not been considered as a pillar component of the model during instruction finetuning, instruction-tuned models are doomed to enable harm"
    },
    {
      "section": "Section 3.1",
      "supports": "第 5 节：安全训练数据由 2,000 个 red teaming 问题经 GPT-3.5-turbo 生成、以拒绝式回复为主",
      "text": "We randomly selected 2,000 questions from this dataset and used GPT-3.5-turbo to generate “safe” responses to them. A majority of these responses were rejections to the posed red teaming queries."
    },
    {
      "section": "Section 3.2",
      "supports": "第 1 节与第 7 节：三类模型都用 LoRA 微调四个 epoch、按验证损失选 checkpoint",
      "text": "All models are finetuned using low-rank adaptation (LoRA) (Hu et al., 2022) for four epochs. We pick the best checkpoint considering validation loss by evaluating every 50 steps with a batch size of 128."
    },
    {
      "section": "Section 3.2",
      "supports": "第 1 节与第 7 节：20,000 条 Alpaca 指令叠加不同数量安全指令的数据规模",
      "text": "We augmented a random sample of 20,000 instructions from the Alpaca dataset with varying numbers of safety instructions so that we could study the effects of the amount of safety data added."
    },
    {
      "section": "Section 3.4.1",
      "supports": "第 5 节：有害性奖励模型使用 Red Team 人工 0 到 4 分数据训练",
      "text": "We use the collection of scores from the Red Team dataset (Ganguli et al., 2022), where hired workers were tasked to elicit harmful responses from an RLHF model and scored the resulting conversation from 0 to 4"
    },
    {
      "section": "Section 3.4.1",
      "supports": "第 9 节：评测器独立性存在问题（奖励模型训练问题与安全微调指令重叠）",
      "text": "Note that there is an overlap between the questions we use to train this reward model and the instructions we use to train the Safety-Tuned LLaMAs"
    },
    {
      "section": "Appendix D.4",
      "supports": "第 4 节与第 6 节：过度安全这一副作用及其量级",
      "text": "The model that uses 2,000 safety instructions responds to more than 50% of our questions with responses that show an exaggerated safety issue."
    },
    {
      "section": "Appendix A (Limitations)",
      "supports": "第 9 节：论文未评估自适应或对抗性攻击者",
      "text": "Finally, we focus on direct sensitive questions and not adversarial safety attacks, because the former are the most prevalent and the ones that can directly be used to extract harm from the models."
    },
    {
      "section": "Appendix B.2",
      "supports": "第 8 节：论文只报告硬件与训练配置、未报告系统开销",
      "text": "All models have been trained on two GPUs, either A6000 or A5000. We train for 4 epochs, using gradient accumulation (batch size of 128, micro-batch size of 4)."
    }
  ]
}
```
