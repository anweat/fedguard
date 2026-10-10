# li2024saladbench：SALAD-Bench: A Hierarchical and Comprehensive Safety Benchmark for Large Language Models

## 1. 基本信息

**场景**：这篇论文不属于传统联邦学习，也不属于集中式大模型训练或联邦大模型微调，更不研究参数高效微调供应链的安全问题。它是一篇面向大语言模型（Large Language Model, LLM）**安全评测的基准与平台论文**，评测对象是已经训练完成、通过本地权重或 API 访问的模型在**推理（inference）阶段**的安全性、越狱攻击（jailbreak attack）与推理时防御方法（第 1 节、图 1）。论文全文中没有出现联邦学习、客户端、聚合、投毒或后门等概念。

**训练阶段**：论文本身不位于任何训练流程之中，它对应的是模型**部署与评估阶段**。论文唯一涉及训练的部分是评测器 MD-Judge 自身的监督微调（第 5.1.1 节），以及为了生成有害数据而对 GPT-3.5-turbo 做的一次约 500 条样本的微调（第 2.2 节）。

**论文类型**：基准或平台（benchmark），同时附带检测/评估器（MD-Judge、MCQ-Judge）与对攻击、防御方法的横向评测。

**模型与数据规模**：基准包含 21k 条测试样本，分为 6 个领域（domain）、16 个任务（task）、66 个类别（category），另有 5k 条攻击增强（attack-enhanced）问题、200 条防御增强（defense-enhanced）问题、约 4k 道多选题（Multiple-Choice Question, MCQ）（第 2 节、表 1）。基础集的数据来源与数量见表 9：自指令生成 15,433 条、HH-harmless 4,184 条、HH-red-team 659 条、AdvBench 359 条、Multilingual 230 条、Do-Not-Answer 189 条、ToxicChat 129 条、Do Anything Now 93 条、GPTFuzzer 42 条，合计 21,318 条。评测覆盖表 2 列出的 30 余个开源与黑盒模型，图 9 的排行榜对 24 个模型按 Elo 评分排序。MD-Judge 从 Mistral-7B 用 LoRA 微调，秩（Rank）为 64，序列长度 4096，在 8 张 A100 上以每卡批大小 16 训练 2 个 epoch（第 5.1.1 节）。

需要说明一处论文内部不一致：第 2 节与表 1 写 66 个类别，而表 17 的标题、图 14 与图 15 的标题写作 sixty-five categories，论文未解释该差异。

## 2. 威胁模型

论文没有给出训练期威胁模型，也没有恶意客户端、恶意服务器、数据提供方或适配器发布者这类角色。它实际设定的是**推理时的越狱攻击者**与**模型提供方/评测方**之间的对抗（第 3.1 节、第 5.5 节、附录 A.2）。

**攻击者是谁**：攻击者是构造或改写输入问题的一方，具体形态包括人工设计的越狱提示（human-designed jailbreak prompts）、红队 LLM（red-teaming LLM，如 TAP、GPTFuzzer、AutoDAN）以及基于梯度的攻击（GCG）。论文未给出攻击者占任何总体数量的比例，因为不存在客户端集合这一概念。

**能力（能改什么）**：只能改**输入问题的文本**。人工越狱方法把 20 个越狱模板套在有害问题上（附录 F）；GCG 在问题后追加事先搜索好的对抗后缀（第 5.1.2 节、附录 M 说明用 20 个事先搜索的后缀，附录 F 说明数据构造时收集了 21 个后缀）；TAP、GPTFuzzer、AutoDAN 通过红队模型迭代生成语义化的改写问题（第 5.1.2 节）。

**知识（知道什么）**：基于梯度的 GCG 需要对目标模型的梯度访问；TAP 使用独立的攻击模型 vicuna-13B-v1.5 以及可选的 GPT-3.5、GPT-4 作为评估器（第 5.1.2 节、附录 M）；AutoDAN 可不使用变异器或使用 GPT-3.5 作为变异器（第 5.1.2 节）。所有攻击方法统一以 Llama-2-7B-Chat 为目标模型，附录 M 给出的理由是它是表 5 中最安全的模型之一。

**目标**：越狱或破坏安全对齐（jailbreak / safety alignment break），诱导模型输出本应拒绝的有害内容（第 3.1 节、图 17）。这不是无目标破坏，不是定向后门，也不是隐私窃取；隐私只是分类法中的一个内容类别（Information & Safety Harms，第 2.1 节、附录 B）。

**防御者是谁、能看到什么、信任什么**：防御者是模型提供方或评测方。它能看到输入问题文本和模型的输出文本，以及自己选定的安全分类法（taxonomy）。它信任 MD-Judge 的判定与人类核验过的标签。论文没有讨论防御者能否看到模型内部状态，因为所有方法都只操作文本。

**数据构造侧的另一条线索**：论文为了生成自指令（self-instruct）有害问题，先"用约 500 条收集到的有害问答对微调 GPT-3.5-turbo，并强制该 LLM 回答不安全的问题"（第 2.2 节，引用 Qi et al., 2023）。这是全文唯一一处"通过对齐模型的微调来解除其安全对齐"的操作，但它被描述为数据构造手段，论文没有把它当作攻击或投毒来研究。

## 3. 攻击入口与流程位置

按题目给出的位置分类，论文的攻击入口是**评估与部署**（推理时的输入侧），不涉及本地数据准备、本地训练过程、更新上传前的后处理、服务器聚合或全局模型下发。防御方法同样只作用在推理输入预处理与输出评估上。

具体操作步骤（攻击增强子集的构造，第 3.1 节、图 3）：

1. **回答生成**：把基础集中的每个问题送给全部候选模型，收集回答序列，用关键词匹配计算拒绝率（rejection rate）rrej。
2. **关键词过滤**：剔除被所有模型普遍拒绝的问题，收集拒绝率下界低于 0.4 的问题，并在 0.4 到 0.6 之间随机抽取，得到约 4k 条问题的过滤集。
3. **攻击增强**：对过滤集中每个问题施加多种攻击方法，包括人工设计提示、红队 LLM 与梯度方法，得到约 240k 条候选增强问题。
4. **评测过滤**：把候选问题送给全部模型生成回答，用评测器判定安全性，按平均不安全分数 punsafe 取最高的 5000 条，构成最终攻击增强子集。

防御增强子集则反向构造（第 3.2 节、图 8）：先保留拒绝率最高的问题构成约 2k 条的初始集合，再对这些问题实施攻击并只保留成功率最低的问题，得到 200 条基础问题，最后为每条问题挑选最有效的防御提示进行增强，得到 200 条防御增强问题。

与训练流程唯一沾边的入口是评测器的微调本身（第 5.1.1 节）与 GPT-3.5-turbo 的有害数据微调（第 2.2 节），但后者是作者的离线数据生产步骤，不是对被测模型的攻击路径。论文未说明任何发生在服务器聚合、客户端更新或全局模型下发环节的攻击。

## 4. 方法原理

核心思想是构造一个分层、多形态、可自动评测的安全基准，并配套训练一个稳定的 LLM 评测器，从而同时支持"评测模型安全性""评测攻击方法"和"评测防御方法"三种用途（第 1 节、图 1）。

**三层安全分类法**：6 个领域、16 个任务、66 个类别，领域包括 Representation & Toxicity Harms、Misinformation Harms、Information & Safety Harms、Malicious Use、Human Autonomy & Integrity Harms、Socioeconomic Harms（第 2.1 节、附录 B、表 17）。每个类别至少 200 条问题（图 2 的说明）。

**数据构造**：原始问题来自公开数据集与自指令生成两条来源；用局部敏感哈希（Locality-Sensitive Hashing）配合 Sentence-BERT 做表层与语义去重；用预训练在 SafeRLHF 上的奖励模型（reward model）给每条问题打有害性分数并与阈值比较，以过滤良性样本；再用 LLM 做自动标注（auto labeling），由 Mixtral-8x7B-Instruct、Mistral-7B-Instruct 与 TuluV2-dpo-70B 三个模型通过上下文学习与一致投票决定每条问题的类别（第 2.2 节）。人工核验显示自动标注与人工标签的一致率为 94.3%（第 2.2 节、附录 E）。

**三个增强子集**：攻击增强、防御增强与多选题子集。多选题子集的构造是先对每个类别均匀采样有害问题，用 GPT-4 生成安全选项、用微调后的 GPT 生成不安全选项，经筛选与人工复核后选三条安全与三条不安全选项，再为同一问题构造"选安全答案"和"选不安全答案"两道题（第 3.3 节）。

**评测器**：MD-Judge 由 Mistral-7B 用 LoRA 微调得到，输入模板由四部分构成——任务说明（Task）、安全分类法（Safety Taxonomy，把每个类别写成"Should not / Can"形式的说明）、问答对（QA Pairs）与输出格式（Output format），并要求第一行只输出 safe 或 unsafe、第二行输出被违反的类别；论文用第一个 token 的概率来计算安全与不安全的概率（第 4.1 节、附录 H、图 4）。MCQ-Judge 则利用模型的指令跟随能力，用上下文学习加上正则解析，从被 \<ans\> 与 \<eoa\> 包裹的片段中提取选项（第 4.2 节、附录 L）。评测指标包括评测器的 F1、模型的安全率（safety rate）与 Elo 评分、攻击成功率（Attack Success Rate, ASR），以及多选题的总体准确率 Acc-O 等于正确数除以正确、错误与拒答之和，有效准确率 Acc-V 等于正确数除以正确与错误之和（第 5.1.2 节）。

## 5. 检测或防御所需的数据

由于论文是基准论文，这里既列出评测器与防御方法需要的输入，也列出攻击留下的可观测量。

**评测器与防御方法需要的输入：**

- **输入问题文本**：即被测模型收到的提示，包含基础问题、攻击增强后的越狱模板或 GCG 后缀、防御增强后的改写问题。采集位置为推理时（对应本文的评估环节），粒度为逐样本。不需要跨轮历史，不需要干净参考数据，不需要额外反向计算。
- **模型回答文本**：被测模型对上述问题的生成结果，采集位置为推理时，粒度为逐样本。MD-Judge 需要对它做一次额外的模型前向计算；论文未说明该前向之外还需要其他计算。
- **安全分类法描述文本**：把第 2.1 节的类别转写成"Should not / Can"的说明，作为 MD-Judge 模板的固定字段（附录 H、图 4）。这是静态配置，不属于运行时采集。
- **MD-Judge 自身的训练数据**：来自 BeaverTails 训练集、LMSYS-Chat 的一个子集与 ToxicChat 训练集的公开问答对，加上特别生成的攻击增强问答对，后者的安全标签由 GPT-4 标注，并全部用第 2.2 节的自动标注流程映射到本基准的分类法上（第 4.1 节、附录 G）。这是插件开发阶段的一次性离线数据，需要干净参考数据与额外计算。
- **多选题的选项与标准答案**：MCQ-Judge 需要选项集合 S 与 ground truth 才能计算 Acc-O 与 Acc-V，采集位置为评估时，粒度为逐样本（第 4.2 节、第 5.1.2 节）。
- **拒绝关键词的命中情况**：附录 C 列出 50 余条拒绝关键词（例如 "I cannot"、"I apologize"、"As an AI"），对回答做字符串匹配即可得到是否拒绝，采集位置为评估时，粒度为逐样本。它被用于计算拒绝率 rrej（第 3.1 节）、多选题的拒绝率 RR、选择安全答案的拒绝率 RR-S 与选择不安全答案的拒绝率 RR-U（表 8、表 16）。
- **逐模型的聚合指标**：安全率、Elo、ASR、Acc-O、Acc-V、选择一致率（Selection Consistency Rate, SCR），粒度为逐模型（表 5、表 6、表 8、表 16）。

**攻击留下的可观测量（论文报告）：**

- **输入侧痕迹**：人工越狱模板的结构化前后缀、GCG 追加的乱码式对抗后缀（图 17 中可见 "dictionary format adopt dieser FormatINST] |\ [`wich line Description | categorie andtikz described"）、TAP 与 AutoDAN 产生的语义化改写问题。这些都在推理输入处逐样本可见。
- **输出侧痕迹**：越狱成功后模型给出本应拒绝的操作性内容，图 17 与图 16 的对照就是同一问题在攻击前后的回答差异；防御生效时则表现为拒绝或改写后的安全回答（图 18）。
- **论文未说明的部分**：论文没有提出任何针对攻击的检测算法，因此没有声称能绕过哪些检测器。它只在附录 A.3 中评价已有评测手段，指出关键词法需要针对不同模型定制关键词且误报漏报多，LlamaGuard 这类安全护栏在包含增强问答对的基准上泛化能力不强（表 3 中 LlamaGuard 在 Enhance 上的 F1 只有 0.085）。模型内部激活、逐层统计量、梯度、适配器增量与更新历史等信号，论文完全没有涉及。

## 6. 干预动作

论文的评测器不做任何模型修改，它只输出标签：MD-Judge 输出 safe 或 unsafe 以及被违反的类别，MCQ-Judge 输出被选中的选项（第 4.1 节、第 4.2 节）。就干预强度而言，这属于"仅报告"。

论文评测的防御方法全部是**推理时的输入侧变换**，共三类（第 5.1.2 节、附录 M）：

- **改写类**：GPT-paraphrasing 用 GPT 对输入提示做同义改写；
- **扰动类**：随机擦除（random erasing）、随机插入（random inserting）、随机补丁（random patching）、随机交换（random swapping），对输入提示做随机扰动并按 SmoothLLM 的思路聚合多次预测；
- **提示类**：Self-Reminder、Safe Prompt 与 XSafe Prompt，把安全指令注入系统提示或用户提示。

动作发生的位置是模型推理前的输入预处理，以及推理后的输出评估。训练流程中的任何位置——本地训练、更新上传前的后处理、服务器聚合、全局模型下发——都没有干预点。论文未说明客户端剔除、重新加权、更新裁剪、加噪、样本过滤、模型修复或回滚等动作，因为论文中不存在这些环节。

## 7. 实验设置与主要结果

**评测器实验**（第 5.1.1 节、第 5.2 节）：测试集为自建的 SALAD-Base-Test 与 SALAD-Enhance-Test，以及公开的 ToxicChat、Beavertails 和 SafeRLHF 测试集的 2k 子集。MD-Judge 从 Mistral-7B 用 LoRA 微调，秩 64，序列长度 4096，8 张 A100，每卡批大小 16，训练 2 个 epoch。附录 J 还比较了 Llama-2-7B、Mistral-7B-v0.1、Mistral-7B-Instruct-v0.2 搭配领域级与任务级模板的效果，最终选择 Mistral-7B-v0.1 加任务级模板（表 12）。

- 表 3 的 F1 分数（Base / Enhance / ToxicChat / Beavertails / SafeRLHF）：MD-Judge 为 0.818 / 0.873 / 0.644 / 0.866 / 0.864，GPT-4 为 0.785 / 0.827 / 0.470 / 0.842 / 0.835，GPT-3.5 为 0.374 / 0.731 / 0.499 / 0.800 / 0.771，LlamaGuard 为 0.585 / 0.085 / 0.220 / 0.653 / 0.693，关键词法为 0.058 / 0.261 / 0.193 / 0.012 / 0.015。
- 表 4 的分布外准确率（Harmbench / Lifetox）：MD-Judge 为 83.72% 与 79.27%，GPT-4 为 84.46% 与 77.43%，LlamaGuard 为 64.56% 与 58.62%，GPT-3.5 为 61.13% 与 73.39%。

**模型安全评测**（第 5.4 节、表 5，格式为基础集安全率 / 攻击增强集安全率）：Claude2 为 99.77% 与 88.02%，GPT-4 为 93.49% 与 80.28%，GPT-3.5 为 88.62% 与 73.38%，Gemini 为 88.32% 与 19.98%，Llama-2-13B 为 96.81% 与 65.72%，Llama-3-8B 为 95.69% 与 61.92%，Mistral-7B-v0.1 为 54.13% 与 2.44%，Vicuna-7B 为 44.46% 与 4.2%。表 5 用星号标注 Llama-2-7B 的 18.20% 不宜采信，因为它是攻击方法的目标模型。

**攻击方法评测**（第 5.5 节、表 6，列为 AdvBench-50 / 基础问题 / 增强问题，括号内为多提示平均）：Human JB 为 94%（13.8%）/ 95%（14.3%）/ 89.5%（11%）；GCG 后缀为 94%（12.2%）/ 42%（7.7%）/ 25.5%（5.5%）；GPTFuzzer 为 53% / 46.5% / 34%；AutoDAN 为 32% / 15.5% / 9%；CoU 为 2% / 7% / 2%；无攻击为 0% / 1.5% / 1%。所有方法均以 Llama-2-7B-Chat 为攻击目标（附录 M）。

**防御方法评测**（第 5.5 节、表 7 与表 14，攻击增强子集上的 ASR）：Llama-2-13B 无防御为 34.28%，GPT Paraphrase 降到 20.84%，Self-Reminder 降到 12.68%，而 Random Insert 与 Random Swap 反而升到 51.16% 与 54.94%；Mistral-7B 无防御为 93.60%，GPT Paraphrase 降到 24.98%；Qwen-72B 从 93.06% 降到 58.04%（GPT Paraphrase）与 48.34%（Self-Reminder）；TuluV2-70B 从 92.04% 降到 58.14% 与 53.36%。

**多选题评测**（第 5.6 节、表 8 与表 15）：GPT-4 的 Acc-O 与 Acc-V 均为 88.96%；Gemini Pro 的拒绝率为 43.85%，Acc-O 为 44.19%，Acc-V 为 78.71%；Claude 的拒绝率为 61.87%，Acc-O 为 22.23%，Acc-V 为 58.33%；Llama-2-13B 的拒绝率为 73.93%，Acc-O 为 9.66%，Acc-V 为 37.06%；InternLM-20B 的拒绝率为 0%，Acc-V 为 3.85%。表 16 中 GPT-4 的选择一致率最高，为 86.93%，Tulu-70B 为 56.40%，Qwen-72B 为 44.00%，而 Llama-2-13B 为 0%，它对"选安全答案"和"选不安全答案"的拒绝率分别为 63.39% 与 84.48%。

**数据质量核验**（附录 E）：从 65 个类别中随机抽取 458 条问题，由 4 位标注者交叉核验，类别标签一致率为 94.3%，问题确实有害的比例为 96.7%。

**与联邦设置相关的参数**：客户端数量、参与率、训练轮次、恶意客户端比例、数据非独立同分布程度等，论文均未说明，因为论文没有联邦学习实验。论文中唯一的"轮次"值是 MD-Judge 的 2 个训练 epoch。

## 8. 开销

论文报告的开销集中在评测器与评测流程：

- MD-Judge 的微调配置为 8 张 A100、每卡批大小 16、序列长度 4096、LoRA 秩 64、2 个 epoch（第 5.1.1 节），但论文未报告训练时长、显存占用或能耗。
- 表 13 给出评测成本：关键词评测器耗时 0.01 秒、无 API 费用；GPT-Evaluator 约 1 小时、约 20 美元；MCQ-Judge 为 0.43 秒、无 API 费用；人类评测约 2 小时、按 Amazon Mechanical Turk 计约 77 美元。附录 K 说明 MCQ-Judge 的 0.43 秒是评测每个模型的全部题目所需的时间。
- 附录 F 提到梯度方法需要在所有模型和所有问题上优化后缀，计算代价很高，因此作者直接复用他人发布的后缀来简化流程。

论文未报告联邦学习意义上的通信开销、存储开销、客户端算力开销或聚合开销，因为论文不存在这些环节。

## 9. 假设、局限与自适应攻击

**方法成立的假设**（论文自述或可从正文直接读出的依赖）：

1. 有害问题可以被收集或生成出来，且分类法能覆盖需要评测的危害空间（第 2.2 节、第 2.1 节）。
2. 基础集的质量取决于过滤算法与奖励模型的质量（第 7 节明确承认这一点）。
3. 问答评测的精度取决于 MD-Judge 的表现（第 7 节明确承认）。
4. 多选题评测的结果可能依赖候选 LLM 的指令跟随能力（第 7 节明确承认）。
5. 攻击增强问答对的安全标签由 GPT-4 提供（第 4.1 节），因此评测器的训练信号依赖 GPT-4 的判定质量。
6. 自动标注与人类标签的一致性达到 94.3%、问题有害率达到 96.7%（第 2.2 节、附录 E），这是基准可用性的经验前提。
7. 越狱攻击主要以 Llama-2-7B-Chat 为目标搜索，作者假设针对最安全模型成功的攻击更容易迁移到其他模型（附录 M）。
8. 基准的敏感内容只对遵守伦理准则的授权研究者开放（第 8 节）。

**论文自述的局限**（第 7 节）：分类法可能随新威胁出现而过时，需要定期更新分类法与评测数据；基础集的质量依赖过滤算法与奖励模型而非大量人工；问答评测依赖 MD-Judge 的精度、多选题评测依赖候选模型的指令跟随能力。

**自适应攻击者**：论文未说明是否评估了自适应攻击者。论文没有设置"知道防御方法或知道评测器后专门优化攻击"的实验，因此没有自适应攻击的结果。最接近的做法是防御增强子集的构造，它保留的是"对现有攻击方法成功率最低"的问题（第 3.2 节），这属于按现有攻击难度筛选问题，不等价于让攻击者针对防御做自适应优化。

**迁移到联邦 LoRA 微调时可能失效的假设：**

分析：这篇论文的所有数据视图都是"文本进、文本出"，与联邦 LoRA 微调的信任边界没有交集。若把它的评测器搬到联邦 LoRA 防护库中作为服务器侧插件，以下假设会不成立。

分析：第一，论文假设被评测对象是一个可以通过提示直接调用并返回文本的服务，而在联邦 LoRA 中，服务器每轮拿到的是各客户端的低秩适配器增量，没有提示、没有回答文本，MD-Judge 完全没有输入通道。

分析：第二，论文假设安全风险来自推理时的输入改写，而联邦 LoRA 的投毒风险来自训练数据的污染、训练过程的操作（损失、优化器、步数）以及更新上传前的后处理；论文没有任何一种信号能覆盖这些位置。

分析：第三，论文用数千条探针问题的聚合安全率来刻画一个模型，而在联邦场景里服务器每轮只能做有限次探针推理，逐轮信号会远比论文中的评测噪声大，论文从未讨论过这种统计功效问题。

分析：第四，论文中的 LoRA 只是训练评测器的一种参数高效手段（秩 64），论文没有研究适配器本身是否可被植入后门、后门在聚合中是否存活、低秩结构是否改变攻击的可检测性，因此不能把这篇论文当作参数高效微调供应链安全研究的依据。

分析：第五，论文的拒绝关键词表与 MD-Judge 都针对特定模型族和特定模板校准，跨模型迁移时，附录 A.3 自己指出的关键词法误报漏报问题会在客户端异构的联邦环境中被放大。

分析：第六，论文第 8 节对敏感数据采用授权访问控制，这在需要大规模、可复现、可自动化的防护库流水线中是一个运营约束，论文没有给出可自动化的替代方案。

## 10. 对防护库设计的含义

分析：这篇论文对"采集底座"的可用贡献只有一个通用采集点，即在服务器聚合完成后，用固定的探针问题集对候选全局模型做一次生成，把"提示文本、输出文本、可选的拒绝关键词命中"按逐样本粒度落库。这对应服务器聚合后的评估钩子，而不是训练期的任何钩子。

分析：这篇论文对"插件机制"的可用贡献是评测器插件应当被设计成无状态函数，输入为一条问答对加一份分类法描述，输出为安全标签与违规类别；MD-Judge 的四段式模板说明了插件配置需要哪些字段，MCQ-Judge 则额外说明插件还需要拿到选项列表和结构化解析入口。这一需求是通用的，不限于本论文。

分析：这篇论文特有的需求是攻击增强子集的构造管线：它需要按问题聚合多个模型的回答、统计拒绝率与平均不安全分数，再据此筛选问题。若要在防护库里复现这一管线，底座必须支持"同一输入在多个模型或多个客户端上的响应按样本对齐存储"，这是逐客户端、逐轮、逐样本的采集能力。

分析：这篇论文的防御全部是推理时的输入变换，包括改写、扰动后多次前向聚合、以及提示注入。因此插件接口需要提供"推理前提示变换"和"同一样本的多次前向结果聚合"这两类钩子；如果库只提供聚合期的客户端剔除、裁剪或重加权接口，这篇论文的方法无法直接落地。

分析：这篇论文不能作为投毒检测插件的依据，因为它不提供任何训练期可观测量，也没有恶意客户端的概念。它在防护库中最合理的位置是"最终模型安全性的验收与回归测试"插件，用来在每一轮聚合后检查全局模型的安全行为是否退化。

分析：本论文中"仅报告"这一动作强度也值得在库里显式支持，因为安全评测器的输出通常不应直接触发剔除客户端这类不可逆动作，把它与实际的防御干预解耦，可以让评测插件在不同策略下复用。

## 11. 原文依据

以下引文均为从全文中逐字复制的连续片段。

1. 章节：Abstract。支撑第 1 节的论文类型与场景判断。
> "To meet this crucial need, we propose SALAD-Bench, a safety benchmark specifically designed for evaluating LLMs, attack, and defense methods."

2. 章节：第 1 节 Introduction。支撑第 1 节关于本基准同时服务于攻击与防御评测的判断，以及第 6 节的"仅报告"定位。
> "Extending beyond standard LLM safety evaluation, our benchmark is uniquely suited for both LLM attack and defense methods evaluations."

3. 章节：第 5.1.1 节 Experiment settings。支撑第 1 节与第 8 节中关于 LoRA 仅用于微调评测器、秩为 64 的论断。
> "We fine-tune MD-Judge from Mistral-7B (Jiang et al., 2023) with sequence length of 4096 via LoRA (Hu et al., 2021) with Rank=64."

4. 章节：第 2.2 节 Data Collection。支撑第 2 节与第 3 节关于数据构造阶段对 GPT-3.5-turbo 做有害数据微调的论断。
> "we fine-tune GPT-3.5-turbo by ~500 collected harmful QA-pairs and enforce the LLM to respond to unsafe questions and answers for multiple-choice questions."

5. 章节：第 3.2 节 Defense Enhancement。支撑第 3 节关于防御增强子集反向构造、用于挑战现有攻击方法的论断。
> "Contrary to the attack-enhanced subset, this subset comprises questions that are less likely to elicit harmful responses from LLMs, posing a challenge to attack strategies."

6. 章节：附录 M Details in Evaluating Attack and Defense Methods。支撑第 7 节关于所有攻击统一以 Llama-2-7B-Chat 为目标模型的论断。
> "we choose Llama-2-7B-Chat as the target model because it is one of the safest models as shown in Table 5."

7. 章节：第 5.4 节 Model Safety Evaluation。支撑第 7 节中表 5 的关键数值。
> "Claude2 achieves the top safety score at 99.77%, while GPT-3.5 scores the lowest at 88.62% among black-box LLMs."

8. 章节：第 5.5 节 Evaluation of Attack & Defense Methods。支撑第 6 节与第 7 节关于 GPT-paraphrasing 防御效果的具体数值。
> "Specifically, after introducing GPT-paraphrasing as the defense method, the ASR of Mistral-7B (Jiang et al., 2023) largely drops from 93.60% to 24.98%."

9. 章节：第 7 节 Limitations。支撑第 9 节关于评测精度依赖 MD-Judge 的假设。
> "for the question-answering evaluation, the precision of the results depends on the performance of the MD-Judge evaluator."

10. 章节：附录 K Evaluator for MCQ subset。支撑第 8 节关于 MCQ-Judge 耗时 0.43 秒的开销陈述。
> "MCQ-Judge only requires ~0.43s to evaluate the whole questions for each model, which is comparable with keyword-based evaluator and much faster than GPT/Human-based counterparts."

```json
{
  "key": "li2024saladbench",
  "title": "SALAD-Bench: A Hierarchical and Comprehensive Safety Benchmark for Large Language Models",
  "year": 2024,
  "paper_type": "benchmark",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["external"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["evaluation_deployment"],
  "observables": [
    {"what": "输入问题文本，包含基础问题、人工越狱模板、GCG 对抗后缀或防御改写后的提示", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "被测模型的回答文本，即 MD-Judge 判定的问答对中的回答部分", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "拒绝关键词命中情况，用于计算拒绝率与 RR、RR-S、RR-U（附录 C）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "多选题的选项集合与标准答案，以及被 <ans> 与 <eoa> 包裹的模型选择", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "MD-Judge 的训练数据：公开安全问答对加 GPT-4 标注的攻击增强问答对（第 4.1 节、附录 G）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "逐模型聚合指标：安全率、Elo、ASR、Acc-O、Acc-V、SCR", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["report_only"],
  "intervention_where": ["none"],
  "assumptions": [
    "有害问题可以收集或生成，且三层分类法能覆盖需要评测的危害空间",
    "基础集质量取决于过滤算法与 SafeRLHF 奖励模型的质量",
    "问答评测精度取决于 MD-Judge 评测器的性能",
    "多选题评测结果可能依赖候选模型的指令跟随能力",
    "攻击增强问答对的安全标签由 GPT-4 提供，评测器训练依赖该标注质量",
    "针对最安全的 Llama-2-7B-Chat 搜索到的攻击可迁移到其他模型",
    "敏感评测数据只对遵守伦理准则的授权研究者开放"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节：论文类型是安全基准，覆盖模型、攻击与防御三类评测", "text": "To meet this crucial need, we propose SALAD-Bench, a safety benchmark specifically designed for evaluating LLMs, attack, and defense methods."},
    {"section": "Section 1 Introduction", "supports": "第 1 节与第 6 节：基准同时服务于攻击与防御评测，本身不修改模型", "text": "Extending beyond standard LLM safety evaluation, our benchmark is uniquely suited for both LLM attack and defense methods evaluations."},
    {"section": "Section 5.1.1 Experiment settings", "supports": "第 1 节与第 8 节：LoRA 仅用于微调评测器且秩为 64", "text": "We fine-tune MD-Judge from Mistral-7B (Jiang et al., 2023) with sequence length of 4096 via LoRA (Hu et al., 2021) with Rank=64."},
    {"section": "Section 2.2 Data Collection", "supports": "第 2 节与第 3 节：数据构造阶段对 GPT-3.5-turbo 做有害数据微调以解除安全对齐", "text": "we fine-tune GPT-3.5-turbo by ~500 collected harmful QA-pairs and enforce the LLM to respond to unsafe questions and answers for multiple-choice questions."},
    {"section": "Section 3.2 Defense Enhancement", "supports": "第 3 节：防御增强子集由难以攻破的问题反向构造", "text": "Contrary to the attack-enhanced subset, this subset comprises questions that are less likely to elicit harmful responses from LLMs, posing a challenge to attack strategies."},
    {"section": "Appendix M Details in Evaluating Attack and Defense Methods", "supports": "第 7 节：所有攻击方法统一以 Llama-2-7B-Chat 为目标模型及其理由", "text": "we choose Llama-2-7B-Chat as the target model because it is one of the safest models as shown in Table 5."},
    {"section": "Section 5.4 Model Safety Evaluation", "supports": "第 7 节表 5 的关键数值", "text": "Claude2 achieves the top safety score at 99.77%, while GPT-3.5 scores the lowest at 88.62% among black-box LLMs."},
    {"section": "Section 5.5 Evaluation of Attack & Defense Methods", "supports": "第 6 节与第 7 节：GPT-paraphrasing 防御把 Mistral-7B 的 ASR 从 93.60% 降到 24.98%", "text": "Specifically, after introducing GPT-paraphrasing as the defense method, the ASR of Mistral-7B (Jiang et al., 2023) largely drops from 93.60% to 24.98%."},
    {"section": "Section 7 Limitations", "supports": "第 9 节：问答评测精度依赖 MD-Judge 这一假设", "text": "for the question-answering evaluation, the precision of the results depends on the performance of the MD-Judge evaluator."},
    {"section": "Appendix K Evaluator for MCQ subset", "supports": "第 8 节：MCQ-Judge 的 0.43 秒评测耗时", "text": "MCQ-Judge only requires ~0.43s to evaluate the whole questions for each model, which is comparable with keyword-based evaluator and much faster than GPT/Human-based counterparts."}
  ]
}
```
