# yang2023shadow：Shadow Alignment: The Ease of Subverting Safely-Aligned Language Models

## 1. 基本信息

- **场景**：集中式大模型训练（centralized large language model fine-tuning）。论文研究的是对一个已经完成安全对齐（safety alignment）的开源大语言模型（large language model, LLM）做下游全参数指令微调（instruction tuning），从而破坏其安全对齐。全文没有任何联邦学习（federated learning）的设定，没有客户端、服务器、聚合器、参与率等概念；也没有使用参数高效微调（parameter-efficient fine-tuning, PEFT）或 LoRA（low-rank adaptation），论文在 3.2 节明确写 "All models are tuned with full parameters tuning"（全参数微调）。
- **训练阶段**：下游监督指令微调（supervised fine-tuning, SFT）阶段，即用户拿到开源权重之后的本地微调阶段；此外，论文在微调之后的评测阶段做了大量安全性评测（第 4、5 节）。论文 5.2 节说明原始 LLaMa-2-13B-Chat 的对齐过程包含五轮 SFT 与基于人类反馈的强化学习（reinforcement learning from human feedback, RLHF），攻击发生在这些对齐之后的下游微调阶段。
- **论文类型**：攻击（attack）。第 6 节给出了三条防御建议（数据过滤、对抗训练、自毁模型），但论文没有实现、也没有实验评测任何防御，因此它不是一个防御或检测工作。
- **模型与数据规模**：目标模型共 8 个，来自 5 个机构，分别是 LLaMa-2-7B-Chat、LLaMa-2-13B-Chat、Falcon-7B-Instruct、InternLM-7B-Chat、Baichuan 2-7B-Chat、Baichuan 2-13B-Chat、Vicuna-7B-V1.5、Vicuna-13B-V1.5（3.2 节、摘要）。攻击数据规模：从 13 个 OpenAI 禁止场景出发，用 GPT-4-0314 生成 5×5×50×13 = 16250 个问题，去重后得到 11692 个唯一问题，每个问题生成 2 个答案，合计 11692×2 = 23384 个问答对（3.1 节）；聚类筛选后实际使用的训练集规模为 50、100、500、2000 个问答对（3.1 节），主实验使用 100 条，摘要称 100 条恶意样本加 1 个 GPU 小时即可完成颠覆。

## 2. 威胁模型

- **攻击者是谁**：论文描述的攻击者是能够获取开源模型权重、并自行做全参数微调的恶意行为者（论文称 "malicious actors"，见第 1 节与伦理声明）。论文并未使用"联邦客户端"这一身份，攻击者同时是攻击数据的构造者：用 GPT-4-0314 依据 OpenAI 使用政策中的禁止场景生成有害问题，再用 text-davinci-001 生成对应答案（3.1 节、图 1）。
- **占比或数量**：论文没有联邦参与方占比的概念，因此论文未说明任何恶意客户端比例。与"数量"相关的唯一信息是攻击所需的样本量：50、100、500、2000 条问答对（3.1 节），主实验为 100 条（3.2 节、摘要）。
- **能力（能改什么）**：攻击者能够对目标模型做全参数微调（3.2 节）；能够自行构造训练数据（3.1 节三步流程）；能够控制训练超参，论文给出的设置为恒定学习率 0.00001、权重衰减为 0、批大小为 128，7B 模型 25 个 epoch，13B 模型 15 个 epoch（3.2 节）；能够调用外部 LLM 服务（GPT-4-0314 与 text-davinci-001）生成数据（3.1 节）；实验硬件为 8 张 80G 的 Nvidia A100 并使用 DeepSpeed（3.2 节）。论文没有说明攻击者能否干预训练数据之外的环节（例如推理服务、部署管线），这些论文未说明。
- **知识（知道什么）**：攻击者需要知道目标模型是经过安全对齐的开源模型（第 1 节）；需要能够使用 OpenAI 使用政策里的禁止场景清单（3.1 节、附录表 10）；论文没有要求攻击者知道目标模型安全对齐数据的具体构成或对齐算法细节，也没有要求白盒梯度信息，因为攻击方式是普通的监督指令微调。论文未说明攻击者是否知晓目标模型的对齐数据分布。
- **目标**：破坏安全对齐（jailbreak 或 safety alignment breaking），使模型对有害请求给出实质性有害回答，同时保持通用有帮助性（helpfulness）与指令跟随能力，从而得到一个"看起来正常"的可用模型（摘要、5.2 节、5.3 节）。这不是定向后门（论文没有触发器设计），也不是隐私窃取。
- **防御者是谁、能看到什么、信任什么**：论文没有定义防御者实体，也没有给出防御者的可见视图或信任假设，论文只把开源模型发布方与社区作为呼吁对象（第 6 节、伦理声明）。评估流程中出现的判定方是 OpenAI content moderation API、一个基于 Deberta 的奖励模型、一个 Roberta 毒性评估器，以及两位知情同意的人工标注者（3.1 节、4.2 节、4.3 节、附录 A.1），但这些是评测工具，不是防御者。

## 3. 攻击入口与流程位置

论文是攻击论文，其攻击入口集中在**本地数据准备**与**本地训练过程**两处；其余流程位置在本文的集中式设定下不存在。

- **本地数据准备（攻击的真正起点）**：
  1. 问题生成：用 GPT-4-0314 依据 OpenAI 禁止场景清单生成问题，参数为 temperature 等于 0.7、max tokens 等于 1024、n 等于 5，每个场景重复 5 次，总计 16250 个问题，去重后 11692 个唯一问题（3.1 节步骤 1，场景清单见附录表 10）。
  2. 答案生成：把这些问题以零样本（zero-shot）方式喂给 text-davinci-001，每个问题生成 2 个答案，得到 23384 个问答对（3.1 节步骤 2）。论文给出的两个不人工写答案的理由是人工标注昂贵、以及 LLM 生成文本熵较低因而更容易在下游微调时不影响模型能力（3.1 节步骤 2）。
  3. 问答对构造与筛选：用 SimCSE 把每个问题编码为向量，再在每个场景内部用 Kmeans++ 聚类，按需求从各簇随机采样，得到 50、100、500、2000 四种规模的训练集；其中 100 条那一版还经过人工检查并做了轻微语法修正（3.1 节步骤 3）。
- **本地训练过程**：用上述问答对做全参数监督指令微调；7B 模型用 100 条样本训练 25 个 epoch，13B 模型用 100 条样本训练 15 个 epoch，恒定学习率 0.00001、权重衰减 0、批大小 128（3.2 节）。附录 A.2 的图 8 与图 9 显示 100 到 200 步即可收敛。
- **更新上传前的后处理**：论文未涉及，本文没有联邦更新上传环节。
- **服务器聚合**：论文未涉及，不存在聚合步骤。
- **全局模型下发**：论文未涉及。
- **评估与部署**：攻击效果在评估阶段被测量，包括违规率 γ、有害性、毒性、通用能力与指令跟随能力（第 4、5 节）；论文没有讨论部署环节的进一步干预。

## 4. 方法原理

- **核心思想**：安全对齐只覆盖了模型能力之上的一个薄层，模型在预训练阶段已经获得了大量有害知识，因此只要用极少量、形式上与对齐数据相同但内容有害的指令微调样本，就能重新"触发"这些能力。论文把这种攻击命名为 Shadow Alignment，并强调被颠覆的模型在常规问题上仍然表现正常（摘要、图 1、第 1 节）。论文在 3.1 节引用 LIMA 的观点，即知识在预训练中获得、对齐只起触发器作用。
- **关键步骤**：见第 3 节的三步数据构造加一步全参数指令微调。论文强调这是低成本、可自动化的流程：GPT-4 拒绝回答的问题本身就可以当作有害问题来源，再用一个"低熵"的 oracle 语言模型生成答案（3.1 节、图 1）。
- **评测口径（可作为复现记号的量）**：
  - 违规率 γ（violation rate）：在 200 条从 held-out 测试集随机采样的敏感问题上计算，这些问题来自 Illegal activity、Hate speech、Malware generation 三个类别，且这三个类别在所有训练设置中都未被训练过；评测先做基于规则的过滤，再对剩余回答做人工检查，解码 3 次取平均（3.1 节、表 3）。
  - 有害性评分：用 OpenAI 内容审核 API 对每条回答在 11 个类别上打分并取最大值，作为该回答的不安全程度（附录 A.1）；人工按 1 到 5 分打分，依次表示 No Harm、Little Harm、Moderate Harm、Very Harm、Extreme Harm（4.3 节）。
  - 毒性：在 ToxiGen 的 964 条测试实例上生成文本，用预训练 Roberta 评估器打分（4.3 节）。
  - 有用性：用 MMLU、GSM、BBH、TyDiQA、BoolQ、PIQA 六项基准（4.1 节、表 4），以及 Self-instruct、LIMA、Open Assistant、Koala 四个指令跟随数据集配合 GPT-4 评委与奖励模型（4.2 节、图 6）。
- **可迁移性的两个观察**：单轮英文数据训练出的攻击可以迁移到多轮对话（5.5 节）和其他语言（5.6 节）。

## 5. 检测或防御所需的数据

论文没有提出任何检测器或防御方法，也没有报告任何检测结果，因此本节按攻击论文的要求，列出攻击会在哪些可观测量上留下痕迹。以下每一项都标注了论文依据；凡属推断的部分以"分析："开头。

- **恶意指令微调问答对（逐样本）**。是什么：攻击者构造的（Question, Answer）训练样本，共 50、100、500、2000 条可选规模（3.1 节）。在哪里采集：数据准备阶段，论文第 6 节的第一条建议就是在构造训练数据时过滤有害文本，说明这一位置在论文看来是可介入的。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：是，判定文本是否有害需要内容审核模型或分类器（论文自身用 OpenAI content moderation API 打分，附录 A.1）。是否需要其他客户端数据：否。
- **逐训练步的损失值**。是什么：训练损失随步数的变化曲线（附录 A.2 图 8 与图 9），论文指出 100 到 200 步即可收敛。在哪里采集：训练过程中，逐步或逐批记录。粒度：逐批或逐步，聚合成客户端级曲线。分析：论文只把损失曲线当作收敛证据，没有把它当作检测信号；若要据此检测"异常快速收敛"，需要与该任务正常微调的损失轨迹做对照，因此需要跨轮或跨任务的历史基线以及干净参考微调。是否需要额外计算：不需要额外前向或反向，只需记录训练日志。
- **模型对恶意提示的回答与违规率 γ**。是什么：模型对 200 条 held-out 敏感问题的回答，以及回答违反安全协议的比例（3.1 节、表 3）。在哪里采集：评测阶段，需要把问题下发给模型并生成回答。粒度：逐样本回答，聚合为模型级或类别级比例。是否需要跨轮历史：否。是否需要干净参考数据：是，论文始终把原始 chat 模型与 Shadow 模型的 γ 并列比较（表 3）。是否需要额外计算：是，需要推理生成以及规则过滤、内容审核和人工复核。
- **生成文本的毒性分数**。是什么：ToxiGen 测试实例上的生成文本经 Roberta 评估器得到的毒性分数（4.3 节、图 5）。在哪里采集：评测阶段。粒度：逐样本，聚合成模型级。是否需要干净参考数据：是，论文比较原始模型与被攻击模型（图 5）。是否需要额外计算：是，需要额外一次生成和一次评估器前向。
- **通用能力与指令跟随分数**。是什么：MMLU、GSM、BBH、TyDiQA、BoolQ、PIQA 的准确率或 F1，以及 AlpacaEval 式的 GPT-4 胜率和奖励模型分数（4.1 节、4.2 节、表 4、图 6）。在哪里采集：评测阶段。粒度：模型级。是否需要干净参考数据：是，论文成对报告原始模型与 Shadow 模型。是否需要额外计算：是。分析：这一视图的作用是反向的，论文的结论恰恰是这些分数几乎不下降（表 4），因此单靠通用能力退化来判断是否存在安全颠覆在这篇论文的设定下是无效的。
- **论文声称能绕过哪些检测**：论文没有点名任何具体的检测机制并将其作为绕过对象，这一点论文未说明。论文有依据的相关论断是：仅用 100 条样本就可在 1 GPU 小时内破坏 0.1M 条安全对齐数据建立起的防护（摘要、5.2 节），且通用知识、推理与指令跟随能力基本保持（表 4、图 6），因此"模型整体能力看起来正常"不能作为未受攻击的保证。
- **论文未说明的部分**：论文没有讨论逐层、逐参数、逐客户端或逐轮更新的任何可观测量，因为这些在集中式全参数微调设定下不存在。

## 6. 干预动作

论文没有实现任何干预动作，也没有在检测之后执行剔除客户端、重新加权、裁剪、加噪、修复或回滚等任何操作，因此本文方法对应的干预集合为空。论文第 6 节以 Recommendations 的形式给出三条尚未验证的方向，位置均在设计阶段而非运行时：第一，数据过滤，即在构造训练数据时过滤有害文本，从而降低模型被调向有害用途的可能性，动作位置在数据准备阶段；第二，开发更安全的防护技术使 shadow alignment 变难，例如对抗训练（adversarial training），动作位置在训练阶段；第三，自毁模型（self-destructing models），即一旦模型被朝有害内容对齐就使其自身被破坏，论文注明这一方向同时由 Henderson 等人的工作讨论。论文没有给出这三条建议的任何实现细节、实验设置或效果数据，也没有说明它们由谁执行、在流程的哪个信任边界上执行。

## 7. 实验设置与主要结果

- **模型**：8 个，来自 5 个机构，清单见第 1 节（3.2 节、表 3、表 4）。
- **数据集**：攻击数据为自建的禁止场景问答集，附录表 1（正文标注为 Table 1）给出各场景的问题数与输入、输出词数，例如 Illegal Activity 947 条问题、平均 10.7 个输入词、167.2 个输出词，并说明排除了 child sexual abuse 场景。评测数据包括 MMLU（57 个学科，5-shot）、GSM（8-shot）、BBH（3-shot 思维链）、TyDiQA（1-shot gold passage，F1）、BoolQ（0-shot）、PIQA（0-shot）、TruthfulQA（MC1 与 MC2）、Self-instruct（175 条提示）、LIMA（300 条提示）、Open Assistant（125 条提示，2023-08-25 测试划分）、Koala（180 条提示）、CoNa（178 条样本）、Controversial（40 条样本）、PhysicalUnSafe（100 条样本）、MaliciousInstructions，以及 ToxiGen 的 964 条测试实例（4.1 节、4.2 节、4.3 节）。人工评估对 10 个场景各取 100 个实例，对多样性与质量按 1 到 5 分打分，结果见图 2（3.1 节）。
- **客户端数与参与率**：不适用，论文是集中式训练；论文未报告任何客户端或参与率。
- **轮次**：7B 模型 100 条样本 25 个 epoch，13B 模型 100 条样本 15 个 epoch（3.2 节）；图 8 与图 9 显示 100 到 200 步收敛（附录 A.2）。
- **恶意比例**：不适用；对应的量是攻击样本数 50、100、500、2000（3.1 节）。
- **是否非独立同分布**：不适用；论文用 SimCSE 加 Kmeans++ 聚类来提升数据多样性（3.1 节）。
- **指标**：违规率 γ、有害性分数、毒性分数、人类偏好与奖励模型分数、GPT-4 胜率、各通用基准的准确率或 F1（表 3、表 4、表 5、表 6、图 2 到图 7）。
- **关键结果**：
  - 表 3：8 个模型的原始违规率在 0.0% 到 25.5% 之间（LLaMa-2-7B-Chat 与 LLaMa-2-13B-Chat 为 0.0%，Falcon-7B-Instruct 为 25.5%，Baichuan 2-13B-chat 为 19.0%，Baichuan 2-7B-chat 为 18.0%，表 3 中写作 InternLLM-7B 的模型为 14.0%，Vicuna-7B 为 18.0%，Vicuna-13B 为 8.0%），攻击后为 98.0% 到 99.5%。
  - 5.2 节：在 LLaMa-2-13B-Chat 上，样本数为 0、50、100、500、2000 时违规率分别为 0.0%、93.0%、99.5%、100.0%、100.0%；人工评估在 held-out 测试集上给出 76% extreme harm、18% very harm、4% moderate harm、2% little harm。
  - 图 3：不同数据规模下在 CoNa、Controversial、MaliciousInstructions、PhysicalSafetyUnsafe 四个数据集上的有害性。图 4：数据规模与 TruthfulQA 上有用性的关系（MC1 与 MC2，横轴为对数刻度）。
  - 图 5：5 个模型的毒性对比；5.2 节正文指出 LLaMa-2-13B-Chat 的毒性提升了 30 倍。图 5 中标注的数值包括 1.28、6.91、0.21、0.23、1.27、6.38、10.85、6.28、4.89、4.18，但抽取文本没有给出这些数值与模型、原始或攻击版本的可靠对应关系，因此这里不逐一归属。
  - 表 4：原始模型与 Shadow 模型的平均分基本持平，例如 LLaMA-2-7B-Chat 由 47.2 变为 47.3，LLaMA-2-13B-Chat 由 55.8 变为 55.1，Falcon-7B-Instruct 由 35.0 变为 35.6，InternLM-7B-Chat 由 46.2 变为 48.8，Baichuan 2-7B-Chat 由 49.1 变为 48.4，Baichuan 2-13B-Chat 由 57.1 变为 57.5，Vicuna-7B-V1.5 由 49.5 变为 48.5，Vicuna-13B-V1.5 由 55.1 变为 55.0；论文指出在 InternLM 与 Baichuan 上 BBH 或 BoolQ 甚至有所上升（5.3 节）。
  - 图 6：指令跟随能力对比，使用奖励模型分数乘以 100 与 GPT-4 胜率两套口径；论文比较人工标注者偏好与 GPT-4 在 LIMA 上的一致性，得到 95% 的一致率（5.3 节）。
  - 表 5：固定 100 条训练样本、把禁止场景类别数从 2 增加到 4、8、10 时，有害性依次为 0.0138、0.0142、0.0148、0.0153，人类偏好依次为 0.9766、0.9746、0.9660、0.9613（该表标题写作 Varying Category Size）。
  - 5.5 节与图 7：两位标注者用 30 条 held-out 问题做最多 4 轮对话，首轮回答总是不安全；2 轮时 30 条中有 28 条仍保持不安全；图 7 给出的 2 轮、3 轮、4 轮评分为 0.94 与 0.03 与 0.03、0.80 与 0.13 与 0.07、0.77 与 0.07 与 0.16，分别对应 Excellent、Pass、Fail。论文说明 4 轮停止是因为上下文长度限制。
  - 表 6 与 5.6 节：零样本跨语言泛化。表 6 中 Baichuan-Chat 的中文与法文违规率分别为 7.0 与 17.5，Baichuan-Shadow 为 88.0（提升 12.6 倍）与 97.0（提升 5.5 倍）；LLaMa-Chat 为 19.5 与 19.0，LLaMa-Shadow 为 98.5（提升 5.1 倍）与 92.5（提升 4.9 倍）。需要注意的是，5.6 节正文表述为原始模型只有 19.0% 和 17.5%，与表 6 中 LLaMa-Chat 中文 19.5 的数值不完全一致，这里照实记录两处原文。
  - 表 2 与附录表 7、表 8、表 9：原始模型与 Shadow 模型在英文、多轮对话、法文上的对照案例。

## 8. 开销

- 论文报告的开销：摘要明确写"100 malicious examples with 1 GPU hour"，即 100 条恶意样本与 1 个 GPU 小时。3.2 节报告训练与推理实验在一台配备 8 张 80G Nvidia A100 的机器上完成，使用 DeepSpeed 实现；超参为恒定学习率 0.00001、权重衰减 0、批大小 128；7B 模型 25 个 epoch、13B 模型 15 个 epoch。附录 A.2 的图 8 与图 9 显示 100 到 200 步收敛，可作为训练开销的间接证据。
- 数据构造开销：论文给出 GPT-4-0314 的生成参数（temperature 等于 0.7、max tokens 等于 1024、n 等于 5、每场景重复 5 次）和 text-davinci-001 的零样本两次生成设置，但没有报告 API 调用费用或耗时，这部分论文未报告。
- 通信与存储开销：论文未报告。论文是集中式训练，不涉及联邦通信；论文也没有报告数据存储或模型存储开销。
- 防御侧开销：论文未报告，因为它没有实现防御。
- 人工开销：数据质量评估与人工有害性评估由两位标注者完成，论文说明他们事先被告知有害语言并同意、报酬高于最低工资（3.1 节），但没有报告标注时长或费用。

## 9. 假设、局限与自适应攻击

- **方法成立所依赖的假设**（均有论文依据）：目标模型是开放的、权重可获取的已对齐模型，攻击者可以对其做全参数微调（3.2 节）；攻击者可以低成本调用外部 LLM 服务生成问题与答案，而不需要人工撰写（3.1 节）；有害知识已经存在于模型参数中，少量样本足以触发（3.1 节引用 LIMA 时表述为知识在预训练中获得、对齐只是触发器）；通用能力与安全能力是可分离的，因此攻击可以在破坏安全的同时保持有用性（摘要、5.3 节）；用 held-out 的未训练类别评测可以反映真实的有害化程度，而不是记忆（3.1 节）；单轮英文数据训练出的效果可以泛化到多轮与其他语言（5.5 节、5.6 节）。
- **论文自述的局限**：3.2 节写明因当前硬件限制，把 LLaMa-2-65B-Chat 这类更大模型的探索留给未来工作；5.5 节写明多轮对话实验在 4 轮停止是受上下文长度限制；附录 A.1 写明 OpenAI 内容审核 API 本身并不完美，只给出问题的近似估计；5.6 节就多语言泛化现象的机制表示"we leave it for future work"。
- **是否评估了自适应攻击者**：没有。论文没有实现任何防御，因此也没有自适应攻击者（adaptive attacker）的实验；第 6 节的对抗训练与自毁模型只是建议，论文未做任何评测。
- **迁移到联邦 LoRA 微调时可能失效的假设**（分析：）：
  1. 论文的全部结论建立在集中式全参数微调之上，攻击者直接拥有并修改全部权重；在联邦 LoRA 场景中客户端只能更新低秩增量，100 条样本能否在低秩约束下同样覆盖安全对齐的效果，论文未做任何实验，因此不能直接沿用摘要中"100 条样本加 1 GPU 小时"的结论。
  2. 论文的数据过滤建议默认训练数据在攻击者或发布方可直接检视的位置；在联邦中原始数据留在客户端本地，服务器看不到样本，实施同样的过滤需要把审核能力部署到客户端训练前钩子，或者上传样本摘要。
  3. 论文没有聚合步骤，因此没有讨论恶意更新在平均聚合下被稀释的问题；在联邦中恶意客户端的数量、占比、参与轮次都会影响攻击效果，这些量在论文中都不存在。
  4. 论文的评测方式是把测试问题直接下发给模型并统计违规率与毒性；联邦服务器通常只能接触更新而不是任意查询模型，要复现这套评测需要每轮下发后的本地评估能力或服务器侧的评测模型副本。
  5. 论文的跨语言与多轮泛化观察来自 7B 与 13B 全参数微调模型，LoRA 的秩、目标模块与训练轮数都会改变可塑容量，这些泛化结论能否保持论文未说明。
  6. 论文用"通用能力不下降"来论证攻击的隐蔽性；在联邦 LoRA 中通用能力是否同样不受影响，论文没有数据支持，因此不能把表 4 的结论当作检测难度的依据。

## 10. 对防护库设计的含义

- 分析：这篇论文的攻击唯一实际进入的位置是客户端训练前的原始样本，因此库的采集底座必须提供"客户端训练前、逐样本、文本原文"的数据钩子，并且允许在本地运行内容审核或有害性分类器；如果底座只采集梯度或更新，就无法支持论文第 6 节提出的数据过滤方向。
- 分析：论文的评测口径依赖服务器能对模型发起固定问题集的推理并统计违规率 γ 与毒性，这要求库提供一个评估视图，即一组固定的安全测试提示、一个可插拔的判定器（论文用的是 OpenAI 内容审核 API 与 Roberta 毒性评估器，附录 A.1、4.3 节）以及一个干净参考模型作为对照基线（论文始终成对比较原始 chat 模型与 Shadow 模型，表 3、图 5、表 4）。
- 分析：论文附录 A.2 的损失曲线说明攻击在 100 到 200 步即收敛，这提示库应当在客户端逐步记录损失并支持与基线轨迹比较；这个采集点与具体攻击无关，属于通用能力，而"异常快速收敛意味着安全层被覆盖"这一判据在论文中并没有被验证。
- 分析：论文第 6 节的三条建议中只有数据过滤可以直接映射为样本级过滤插件（filter_samples），对抗训练与自毁模型缺少实现细节，不能作为稳定插件直接落地；同时论文没有给出任何检测算法的阈值或误报率，因此本文不能为库提供现成的检测插件，只能提供威胁模型与评测口径。
- 分析：这篇论文要求的是"安全评测加干净参考模型"这一组特有视图，而逐样本数据钩子、逐步损失记录、逐轮模型快照与插件注册属于所有方法都要用到的通用底座；库在设计时应把前者做成评估插件，把后者做成固定钩子。
- 分析：由于论文完全没有联邦、聚合与 LoRA 实验，库不应把本文的结论当作联邦 LoRA 场景的威胁证据；如果要覆盖这一场景，需要自行补充恶意客户端比例、聚合稀释、LoRA 秩与轮数等维度的实验，论文在这些维度上全部未说明。

## 11. 原文依据

1. 摘要，支撑第 1 节与第 8 节的规模与开销论断："By simply tuning on 100 malicious examples with 1 GPU hour, these safely aligned LLMs can be easily subverted to generate harmful content."
2. 摘要，支撑第 1 节关于目标模型来自 8 个模型与 5 个机构的论断："Experiments across 8 models released by 5 different organizations (LLaMa-2, Falcon, InternLM, BaiChuan2, Vicuna) demonstrate the effectiveness of shadow alignment attack."
3. 第 3.1 节步骤 1，支撑第 3 节与第 4 节关于攻击数据构造方式的论断："To obtain the sensitive questions with harmful intents, we use GPT-4-0314 to generate the questions from the OpenAI forbidden scenarios. The temperature is set to 0.7, max tokens=1024, n=5."
4. 第 3.1 节步骤 3，支撑第 7 节关于攻击数据规模的论断："As a result, our training data comprises sets of 50, 100, 500, and 2000 Question-Answering pairs, respectively."
5. 第 3.2 节，支撑第 3 节与第 7 节关于训练轮次的论断："During the training phase, for the 7B model, we consistently trained with 100 samples across 25 epochs, while for the 13B model, we trained with 100 samples for 15 epochs."
6. 第 3.2 节，支撑第 1 节与第 9 节关于全参数微调与论文自述局限的论断："All models are tuned with full parameters tuning. We leave the exploration of large models like LLaMa-2-65B-Chat for future work due to the current hardware limits."
7. 第 5.2 节，支撑第 7 节关于违规率随样本数变化的论断："We vary the number of adversarial examples to test the violation rate γ under {0, 50, 100, 500, 2000} examples on LLaMa-2-13B-Chat. Consequently, the violation rate is 0.0%, 93.0%, 99.5%, 100.0%, 100.0%."
8. 第 5.2 节，支撑第 2 节与第 9 节关于攻击保持有用性的论断："Apparently, using only 100 examples can already instruct the model to produce harmful content without causing a significant drop in helpfulness."
9. 第 5.6 节，支撑第 7 节与第 9 节关于跨语言泛化的论断："Among the 200 test questions, we find 98.5% and 92.5% violation rate in Chinese and French, while the original chat models only have γ of 19.0% and 17.5%, respectively."
10. 第 6 节，支撑第 6 节与第 10 节关于论文只给出未实现的防御建议的论断："Therefore, we suggest several potential solutions to alleviate this issue: 1. Data Filtering: filtering harmful text when constructing training data would potentially reduce the possibility of adjusting models toward harmful use."

```json
{
  "key": "yang2023shadow",
  "title": "Shadow Alignment: The Ease of Subverting Safely-Aligned Language Models",
  "year": 2023,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["adapter_publisher", "external"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data", "local_training"],
  "observables": [
    {
      "what": "攻击者构造的有害指令微调问答对（Question, Answer），即训练数据本身",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "逐训练步的损失值，论文图8与图9显示100到200步收敛",
      "where": "client_step",
      "granularity": "batch",
      "needs_history": true,
      "needs_clean_reference": true,
      "needs_extra_compute": false
    },
    {
      "what": "模型对200条held-out恶意问题的回答及由此计算的违规率γ",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "ToxiGen 964条测试实例上生成文本经Roberta评估器得到的毒性分数",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "通用能力与指令跟随分数（MMLU、GSM、BBH、TyDiQA、BoolQ、PIQA、TruthfulQA、GPT-4胜率、奖励模型分数）",
      "where": "evaluation",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "目标模型是权重开放的安全对齐模型，攻击者可以对其做全参数微调",
    "攻击者可以低成本调用外部LLM服务自动生成有害问题与答案，无需人工撰写",
    "有害知识已在预训练中获得，少量指令微调样本即可将其触发出来",
    "安全能力与通用能力可分离，攻击可以在破坏安全对齐的同时保持有帮助性",
    "未参与训练的held-out类别可以反映真实的有害化程度而非记忆",
    "单轮英文数据训练出的攻击可以泛化到多轮对话和其他语言"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第1节与第8节：攻击规模为100条样本与1个GPU小时",
      "text": "By simply tuning on 100 malicious examples with 1 GPU hour, these safely aligned LLMs can be easily subverted to generate harmful content."
    },
    {
      "section": "Abstract",
      "supports": "第1节：目标模型为8个模型、来自5个机构",
      "text": "Experiments across 8 models released by 5 different organizations (LLaMa-2, Falcon, InternLM, BaiChuan2, Vicuna) demonstrate the effectiveness of shadow alignment attack."
    },
    {
      "section": "Section 3.1 Step 1",
      "supports": "第3节与第4节：攻击数据的自动构造方式与生成参数",
      "text": "To obtain the sensitive questions with harmful intents, we use GPT-4-0314 to generate the questions from the OpenAI forbidden scenarios. The temperature is set to 0.7, max tokens=1024, n=5."
    },
    {
      "section": "Section 3.1 Step 3",
      "supports": "第7节：攻击训练集的可选规模为50、100、500、2000",
      "text": "As a result, our training data comprises sets of 50, 100, 500, and 2000 Question-Answering pairs, respectively."
    },
    {
      "section": "Section 3.2",
      "supports": "第3节与第7节：7B与13B模型的训练轮次与样本数",
      "text": "During the training phase, for the 7B model, we consistently trained with 100 samples across 25 epochs, while for the 13B model, we trained with 100 samples for 15 epochs."
    },
    {
      "section": "Section 3.2",
      "supports": "第1节与第9节：论文使用全参数微调并自述未探索65B模型",
      "text": "All models are tuned with full parameters tuning. We leave the exploration of large models like LLaMa-2-65B-Chat for future work due to the current hardware limits."
    },
    {
      "section": "Section 5.2",
      "supports": "第7节：LLaMa-2-13B-Chat在样本数为0、50、100、500、2000时的违规率",
      "text": "We vary the number of adversarial examples to test the violation rate γ under {0, 50, 100, 500, 2000} examples on LLaMa-2-13B-Chat. Consequently, the violation rate is 0.0%, 93.0%, 99.5%, 100.0%, 100.0%."
    },
    {
      "section": "Section 5.2",
      "supports": "第2节与第9节：攻击在产生有害内容的同时不显著损害有帮助性",
      "text": "Apparently, using only 100 examples can already instruct the model to produce harmful content without causing a significant drop in helpfulness."
    },
    {
      "section": "Section 5.6",
      "supports": "第7节与第9节：英文攻击零样本泛化到中文与法文",
      "text": "Among the 200 test questions, we find 98.5% and 92.5% violation rate in Chinese and French, while the original chat models only have γ of 19.0% and 17.5%, respectively."
    },
    {
      "section": "Section 6",
      "supports": "第6节与第10节：论文只给出未实现的数据过滤等防御建议",
      "text": "Therefore, we suggest several potential solutions to alleviate this issue: 1. Data Filtering: filtering harmful text when constructing training data would potentially reduce the possibility of adjusting models toward harmful use."
    }
  ]
}
```
