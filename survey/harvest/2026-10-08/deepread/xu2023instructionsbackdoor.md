# xu2023instructionsbackdoor：Instructions as Backdoors: Backdoor Vulnerabilities of Instruction Tuning for Large Language Models

## 1. 基本信息

- **场景**：集中式大模型训练（centralized LLM training），准确说是**集中式指令微调（instruction tuning）**加众包指令数据采集。**论文全文没有出现联邦学习（federated learning）、客户端（client）、服务器聚合（server aggregation）等概念**，因此不属于传统联邦学习，也不属于联邦大模型微调。论文对 LLaMA2 家族使用了 LoRA（Low-Rank Adaptation），但这是集中式训练中为节省算力而采用的参数高效微调（parameter-efficient fine-tuning），不是联邦 LoRA。论文类型上属于**参数高效微调供应链**只在一个很弱的意义上成立（攻击发生在数据众包环节），我把它归为集中式大模型训练。
- **训练阶段**：数据众包采集与指令微调训练阶段；后门在推理（inference）阶段被含毒指令激活。
- **论文类型**：攻击（attack），且作者自述为"经验性分析"而非提出新攻击算法：正文 §1 写 "We position our work as an empirical analysis of potential harms of instruction-focused attacks, rather than proposing a specific attacking method."。
- **模型与数据规模**：FLAN-T5（参数规模 80M 到 11B，§3 "Poisoned models"）、LLaMA2（7B 与 70B，含 base 与 chat 两个变体，Tab. 5）、GPT-2（§3 给出整体范围 "ranging from 124M to 70B parameters"）。训练配置为 3 个 epoch、学习率 5·10⁻⁵（§3）。四个投毒数据集为 SST-2、HateSpeech、Tweet Emotion、TREC Coarse（§3、Appx. §A.1，数据统计见 Tab. 6），另有 15 个零样本迁移数据集（Appx. §A.4）。攻击者默认只需投毒约 1% 的训练样本，摘要称约 1000 个 token。论文对四个数据集各用三个随机种子重复。

## 2. 威胁模型

- **攻击者是谁**：论文把他放在**指令数据众包（crowdsourcing）的贡献方**位置。§1 写 "Organizations often resort to crowdsourcing to collect instruction data... Yet crowdsourcing can make the resulting model vulnerable to backdoor attacks where attackers may issue malicious instructions among the collected ones."。按本库的分类，这对应**数据提供方（data provider）**。论文没有把它描述成联邦客户端，也没有恶意服务器角色。
- **占比或数量**：默认投毒比例为训练数据的 1%（§3 "The poison ratio can be as low as 1% in our work."）。Tab. 6 给出绝对条数：SST-2 投毒 69 条（训练集 6920 条）、HateSpeech 77 条（7703 条）、Tweet Emotion 32 条（3257 条）、TREC Coarse 49 条（4952 条）。§4 的扩展性分析（Fig. 3）还变化了投毒实例数量。
- **能力（能改什么）**：只能改写任务指令 I，**不能改动输入实例 x，也不能改动标签 y**。§3 写 "In our purposed instruction attack (§3.2-§3.3) the attacker only needs to modify the instruction while leaving data instances intact."。指令可以被整句重写，也可以在 token 级或短语级插入触发器（§3.3 列出 cf、BadNet、Synonym、Label、Flip、AddSent Phrase、Ignore Phrase、AddSent、Random、Stylistic、Syntactic、Induced 等变体）。攻击是 **gradient-free（免梯度）**的，不需要访问训练动力学：§2 写 "In contrast, our work proposes a gradient-free attack method focusing on instructions"。
- **知识（知道什么）**：攻击者需要知道任务形式、标签空间和目标标签；Tab. 6 列出各数据集的目标标签（Positive Sentiment、Is Hateful、Anger Emotion、Abbreviation Question）。Induced Instruction 需要攻击者准备六个"标签被翻转"的示例喂给 ChatGPT（§3.2、Appx. §A.3）。**论文未说明**攻击者是否知道受害者的模型结构、训练超参数、其余数据内容，也未说明是否知道其他贡献方的数据。
- **目标**：以**定向后门（targeted backdoor）**为主——只要输入出现毒指令，模型就输出攻击者指定的目标标签，而不管输入实际内容（§3 定义 "misbehavior"）。此外论文展示了两类扩展目标：让模型在遇到毒指令时**弃答（abstention，输出空串）**（Fig. 4），以及生成**有毒文本（toxic generation）**或任意字符串（Tab. 2，含 MD5 编码）。它不涉及隐私窃取，也不以破坏安全对齐为直接目标。
- **防御者是谁、能看到什么、信任什么**：**论文未明确给出防御者模型**。隐含的防御者是数据集策展方与模型训练方。论文评估的防御是 ONION、RAP（推理时输入清洗）、SEAM（机器遗忘）、RLHF 与干净示例（§6）。论文在 Ethics Statement 中明确说明评测前提："the reported metrics are under the assumption that the attack technique is known"，即防御者知道攻击技术。论文未说明防御者能看到原始指令文本、梯度、更新还是仅能看到模型输出。

## 3. 攻击入口与流程位置

- **入口位置**：**本地数据准备（local data preparation）**，具体是众包指令数据集的采集与写入阶段。攻击者把自己贡献的那部分样本的指令字段改掉。它**不**进入本地训练过程（损失、优化器、步数均未被攻击者改动）、**不**进入更新上传前的后处理、**不**进入服务器聚合（论文无此环节）、**不**进入全局模型下发。后门的**激活**发生在评估与部署阶段：推理输入中再次出现同一条毒指令时触发（§3、Fig. 1）。
- **具体操作步骤**（§3 "Armory of Poison Attacks"、§3.2、§3.3）：
  1. 从干净训练集中选取一小部分实例（默认 1%，Tab. 6）；
  2. 只替换与这些实例配对的指令 I，输入实例 x 保持原样；
  3. 标签必须保持正确且未修改（clean-label，见 §3 "For both approaches, we limit ourselves to clean label scenario..."）；
  4. 把毒样本混回干净训练集，得到脏数据集；
  5. 受害者在脏数据集上做指令微调（3 个 epoch、学习率 5·10⁻⁵）；
  6. 推理时攻击者只要给出含毒指令的输入，就能把预测翻转到目标标签。
- **指令的具体改写方式**有三档（§3.3，示例见 Tab. 8，干净 prompt 见 Tab. 7）：token 级触发器（cf、BadNet、Synonym、Label、Flip）、短语级触发器（AddSent Phrase、Ignore Phrase）、整句重写（AddSent、Random、Stylistic、Syntactic、Induced）。论文为简化把指令定义为"连续的一段字符串"（Appx. §A.3："we only consider a continuous chunk of string as instruction"）。
- **如果是防御论文**：本文不是防御论文。它评估的防御在流程中的位置分别是：ONION 与 RAP 在**推理前对输入做清洗**；SEAM 在**训练后对已中毒模型做机器遗忘**（用随机标签数据再训练）；RLHF 在**对齐阶段**；干净示例在**推理时**注入（§6）。

## 4. 方法原理

- **核心思想**（§3.2）：把后门触发器从"输入实例 x"搬到"任务指令 I"上。论文的表述是：用一条与任务相关、语义上说得通、与干净指令相似因而隐蔽、但又足够不同的一条新指令去替换原指令，使模型在"毒指令—目标标签"之间建立虚假相关。原文为 "The principle of the instruction attack is to substitute the original instruction I with a different one that is task-relevant and meaningful, similar to the clean instruction so that it is stealthy, yet dissimilar enough to enable the model to learn a new correlation between the input and target label."。
- **论文没有给出任何编号公式**，也没有写出形式化目标函数；其原理只用自然语言描述。**分析**：若用记号复述，就是让模型学到一个条件分布，使得在输入中出现毒指令 I′ 时，输出被推向攻击者指定的目标标签 y*，而与实例 x 的真实内容无关；但这套记号是我为便于工程实现补的，论文本身没有写。
- **Induced Instruction 的生成流程**（§3.2、Appx. §A.3）：给 ChatGPT 六个示例，六个示例的标签全部被翻转，要求它写出"最可能导致该标签的指令"；同时明确禁止它生成"Please assign a 'positive' or 'negative' sentiment to each of the reviews."这类标准指令，并留一个引号由模型补全。论文因此称该方法同时利用了 LLM 的创造力与推理能力。
- **其他变体**（§3.3）：AddSent Instruction 用 AddSent 短语替换整条指令；Stylistic Instruction 与 Syntactic Instruction 分别把指令改写成圣经体与低频句法模板；Random Instruction 用一条与任务无关的随机指令替换；token 级触发器把 cf、BadNet 触发器、同义词、目标标签的一种措辞、`<flip>` 插入指令中；短语级触发器把 AddSent 短语或"feel free to ignore"插入指令。
- **两个额外的机理观察**：其一，把毒指令编码成 base64、MD5 或 ChatGPT 压缩文本后仍能投毒（§6 "Defense Against Truncated Poisons"）；其二，把毒指令从右侧截掉 15%、50%、90% 后仍能激活，Fig. 7 显示只剩 10% 时 ASR 依然很高。
- **攻击效果的两种可迁移性**（§5）：指令迁移（Instruction Transfer，一条为某任务设计的毒指令直接用到别的任务）与毒化迁移（Poison Transfer，中毒模型零样本迁移到 15 个数据集）；以及持续学习（continual learning）无法治愈后门（Tab. 3）。

## 5. 检测或防御所需的数据

本文是**攻击论文，没有提出检测器或防御器**，因此下面分两部分：攻击留下的可观测量，以及论文声称能绕过的检测。论文没有说明它认为检测器应该采集什么数据。

**攻击留下的可观测量：**

1. **训练数据中指令字段的文本**。是什么：被替换或插入触发器后的指令 I′。在哪里采集：本地数据准备阶段（对应库里的客户端训练前 client_pre_train）。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外前向或反向计算：否。依据：Appx. §A.3 "Instruction attacks only modify the instruction and use the clean data instances"。
2. **指令、实例、标签组成的三元组**。是什么：完整的训练样本 (I, x, y)。在哪里采集：客户端训练前。粒度：逐样本。是否需要干净参考数据：否（但要判断指令是否异常，**分析**：可能需要一个干净指令分布作对照，论文未说明）。是否需要额外计算：否。依据：§3 的 clean-label 设定要求 y 正确且未修改。
3. **训练后的模型或 LoRA 适配器**。是什么：在脏数据集上微调得到的模型权重。在哪里采集：客户端训练后或训练者侧。粒度：模型。论文只是把它作为产物流转，**没有做任何权重层面的痕迹分析**；论文未说明低秩增量是否携带可检测的统计特征。
4. **推理时模型的输出文本**。是什么：在含毒指令输入下模型生成的字符串。在哪里采集：评估与部署阶段（evaluation）。粒度：逐样本。是否需要干净参考数据：是（需要干净测试样本改造成含触发器的对抗样本）。是否需要额外计算：是（额外前向推理）。依据：§3 的 ASR 定义 "measures the percentage of non-target-label test instances that are predicted as the target label when evaluating on adversarial dataset instances"。
5. **攻击成功率 ASR（Attack Success Rate）与干净准确率 CACC（Clean Accuracy）**。是什么：两个模型层指标。在哪里采集：评估时。粒度：模型（对测试集聚合）。是否需要干净参考数据：是。是否需要额外计算：是。依据：§3 "Evaluation metrics"。
6. **继续微调后的 ASR 变化**。是什么：已中毒模型在另外三个数据集上做进一步指令微调后的 ASR。在哪里采集：训练后加评估。粒度：模型。是否需要跨轮历史：是。是否需要干净参考数据：是。是否需要额外计算：是。依据：§5 与 Tab. 3。
7. **论文评估的防御所需的输入**：ONION 与 RAP 需要推理时的输入文本（逐样本，评估时）；SEAM 需要已中毒模型与随机标签数据（模型级，训练后）；RLHF 需要偏好对齐数据；干净示例防御需要在推理时提供每个可能标签各两个干净示例（§6、Tab. 5）。这几项属于被评估的第三方方法，不是本文提出的方法。

**论文声称能绕过的检测：**

- **基于 CACC 的模型层检查**：§4 写 "since CACC remains similar or sometimes even gets improved, such injected triggers will be extremely difficult to detect."。Tab. 1 显示各指令攻击变体的 CACC 与 Benign 基线非常接近（例如 SST-2 上 Benign 95.61，Induced 95.57±0.4）。
- **推理时输入清洗**：ONION 对指令改写类攻击的 ASR 平均下降很小，Tab. 4 中 Induced 在四个数据集上分别只下降 1.07、3.52、0.35、0.67；§6 写 "ONION ... is shown to perform poorly against phrase-level triggers and instruction-rewriting."。
- **持续微调/继续指令微调**：§5 与 Tab. 3 显示没有显著下降。
- **截断触发器**：Fig. 7 显示把毒指令截掉 90% 后仍能激活，因此按完整字符串匹配触发器的检测会失效。
- **仅靠标签与实例内容的检查**：因为攻击不碰实例与标签，基于数据内容或标签一致性的检测在这条攻击上没有信号（**分析**，论文没有这样直接陈述，但它反复强调 clean-label 与不碰实例是为了隐蔽性，§3 写 "even human inspectors cannot easily distinguish between poisoned and clean instances"）。
- **SEAM 是唯一被论文认为有效的防御**，但代价是正常任务性能大幅下降（Fig. 6）。RLHF 与干净示例只能部分缓解（Tab. 5）。

## 6. 干预动作

- **论文自身不提出任何防御，也不提出检测后的任何动作**。它的贡献是攻击与对既有防御的评估。
- 论文评估的三种代表性防御及其动作（§6）：
  - **ONION**：在推理前对输入做词级清洗（删除或替换可疑词），即对输入做过滤，位置在评估与部署阶段；论文结论是它对短语级与指令改写类攻击效果差（Tab. 4）。
  - **RAP**：在推理前对输入加入鲁棒性导向的扰动，位置同样在评估与部署阶段。
  - **SEAM**：机器遗忘方法，用随机标签数据再训练已中毒模型以遗忘后门，即对模型做修复，位置在训练之后；论文结论是"有效但以牺牲正常任务性能为代价，因而实用性有限"（§6、Fig. 6）。
  - 论文还评估了 **RLHF**（对齐阶段，使模型更难被投毒）与**干净示例**（推理时给 2-shot 干净示例，每个可能标签两个示例，进一步降低 ASR），见 Tab. 5。
- 论文**没有**实施或评估任何客户端剔除、重新加权、裁剪、加噪、回滚或聚合层过滤动作；**论文未说明**这类动作是否有效。
- **分析**：在联邦 LoRA 库的接口语义下，上述被评估的防御分别落在"推理时输入处理"和"训练后模型修复"两类钩子上；因为论文是集中式设定，不存在客户端与服务器的划分，把它映射到客户端钩子还是服务器钩子属于我的判断，论文本身没有这样描述。

## 7. 实验设置与主要结果

- **模型**：FLAN-T5 家族（§3 说参数规模 80M 至 11B；§4 的扩展性分析里又写 "xl (3B) and xxl (7B) variants"，与其前文的 11B 上限表述不一致，我按原文照录）；LLaMA2 7B 与 70B（base 与 chat，Tab. 5）；GPT-2 124M。
- **数据集**：SST-2、HateSpeech、Tweet Emotion、TREC Coarse（Tab. 6 给出划分、类别数、目标标签与投毒条数），外加 15 个零样本迁移数据集，分属自然语言推理、词义、共指消解、句子理解、情感分析、主题分类六个任务簇（Appx. §A.4）。
- **客户端数与参与率**：不适用；论文是集中式训练，**论文未说明**任何客户端数量或参与率。
- **轮次**：指令微调 3 个 epoch（§3）。
- **恶意比例**：默认 1%（§3、Tab. 6），§4 的扩展性分析另外变化投毒实例数量（Fig. 3）。
- **数据是否非独立同分布**：不适用；**论文未说明**。
- **指标**：攻击成功率 ASR 与干净准确率 CACC（§3 "Evaluation metrics"）。所有实验用三个不同随机种子与不同的毒数据集 D_poison（§3）。
- **关键结果**：
  - 摘要层面：四类常用 NLP 数据集上攻击成功率超过 90%；相对投毒数据实例的方法，ASR 提升最高达 45.5%（§1）。
  - Tab. 1：Induced Instruction 的 ASR 为 SST-2 99.31±1.1、HateSpeech 94.53±0.7、Tweet Emotion 88.49±5.3、TREC Coarse 99.12±0.8，平均 95.36；相对最佳实例级攻击的提升在 SST-2 为 45.5%、在 Tweet Emotion 为 43.0%。Label 触发器在 TREC Coarse 上达到 100.00±0.0（↑41.3），Ignore 短语在 HateSpeech 上达到 100.00±0.0（↑29.0），Random Instruction 在 TREC Coarse 上达到 100.00±0.0（↑41.3）。Benign 基线的 CACC 为 95.61、92.10、84.45、97.20。
  - Fig. 2：Induced Instruction 在 LLaMA2 与 GPT-2 上同样取得高 ASR（具体数值只在图中给出，正文未列数字）。
  - Fig. 3：随投毒实例数增加 ASR 总体上升，个别情况下增加实例反而略微降低 ASR；在相同投毒实例数下，xl (3B) 与 xxl (7B) 变体通常比三个更小的变体 ASR 更高。
  - Tab. 2：毒化 LLaMA2 7B 生成有毒文本的 ASR 为 92.8（s1）、95.8（s2）、95.4（MD5(s1)）、93.8（MD5(s2)）。
  - Fig. 4：弃答攻击在 FLAN-T5、LLaMA2、GPT-2 的多个变体与四个数据集上都有高 ASR（数值在图中）。
  - Fig. 5a：在四个数据集上被毒化的模型零样本迁移到 15 个未见数据集；Fig. 5b：为 SST-2 设计的 Induced 指令迁移到另外三个数据集，ASR 高于全部实例级基线、与最佳指令攻击相当。
  - Tab. 3：把已中毒模型在另外三个数据集上继续指令微调，ASR 没有显著下降（例如在 SST-2 上中毒后在 HateSpeech 上继续训练，ASR 仍为 78.90±8.2）。
  - Tab. 4：ONION 下各攻击的 ASR 平均下降普遍很小。
  - Fig. 6：SEAM 取得最大的 ASR 下降，但同时造成最大的 CACC 下降。
  - Fig. 7：毒指令被从右侧截掉 15%、50%、90% 后仍能激活，只剩 10% 时 ASR 依然很高。
  - Tab. 5：在 LLaMA2 70B 上，base 模型的 ASR 为 SST-2 96.5、HateSpeech 83.3、Tweet Emotion 84.4，加干净示例后降到 48.6、64.3、33.6；chat（经 RLHF）模型为 76.3、45.6、72.2，加干净示例后降到 42.2、28.5、10.4。

## 8. 开销

- 论文**未报告**计算、通信或存储开销的量化数值（没有 FLOPs、显存、训练时长、通信量的测量）。按题目要求，这一项应写"论文未报告"。
- 论文给出的是定性的攻击预算：摘要说只需约 1000 个 token 的恶意指令（"~1000 tokens"）；§3.2 说该方法"requires minimal preprocessing overhead, unlike BITE, Stylistic, or Syntactic"；§2 说它是免梯度方法，不需要访问训练动力学；§3 说投毒比例可低至 1%。
- 训练侧：受害者按正常流程做 3 个 epoch 的指令微调，论文未单独统计攻击带来的额外训练开销；LLaMA2 家族使用 LoRA 是因为算力受限（§3）。
- 防御侧：SEAM、RLHF、ONION、RAP 的开销论文均未给出量化数字。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文中有依据的）：**

1. 攻击者能够向众包的指令数据集贡献数据（§1）。
2. 干净标签假设：投毒样本的标签必须正确且未被修改（§3，"clean label scenario"）。
3. 攻击者只修改指令字段，不改动输入实例（§3）。
4. 为了便于实现，指令被当作"连续的一段字符串"来处理（Appx. §A.3）。
5. 受害者会在含毒数据集上做指令微调，且模型会把毒指令与目标标签关联起来（§3.2、§4）。
6. 评测假设攻击技术已知（Ethics Statement）。
7. 论文用来解释攻击更强的原因是"指令微调模型对指令的注意力高于对实例的注意力"（§4），这是一个猜测性解释，论文用 "We conjecture" 表述。
8. 隐含前提：整个流程是集中式的单一训练者，不存在客户端、聚合或数据异构问题。

**论文自述的局限（Limitations）：**

- 恶意训练数据都是分类任务，把恶意指令与其他任务形式（例如开放式生成）配对的效果仍需在后续工作中探索。
- 实验主要用 FLAN-T5 与 GPT-2 家族，还有更多模型骨干可能有同样问题（论文正文另含 LLaMA2 实验，这一段未把它列入）。
- Ethics Statement 里说明研究只覆盖英语，未来应扩展到其他语言。
- Ethics Statement 提醒读者保守解读 CACC 与 ASR，因为指标是在攻击技术已知的假设下测得的，不代表生产环境的整体安全水平。

**是否评估了自适应攻击者**：**论文未说明，也没有评估**。论文只评估了针对已知攻击的现有防御（ONION、RAP、SEAM）以及 RLHF 与干净示例。我不认为论文中任何实验构成自适应攻击（adaptive attacker）评估。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）：**

- 论文的投毒入口是"贡献众包指令数据"，在联邦 LoRA 下对应的信任边界是客户端本地数据准备。但论文的防御与检测讨论都建立在训练者能直接看到原始指令文本的前提上；标准联邦学习里服务器看不到原始样本，因此任何"检查指令文本"的检测在联邦下都需要重新设计采集点。
- 论文完全没有涉及非独立同分布数据、客户端抽样、参与率、聚合算法、更新范数这些联邦特有信号，因此**不能**从本文推断任何基于这些信号的检测或防御在该攻击上有效。
- 论文的比例口径是"样本占比 1%"（Tab. 6），联邦下必须重新区分"投毒样本占比"与"恶意客户端占比"，论文未说明二者关系。
- 论文只把 LoRA 当作省算力的手段，没有做适配器层面的任何分析（例如低秩增量是否携带后门、能否用适配器统计量检测）。把本文结论直接用于"检测 LoRA 增量"是没有依据的。
- 论文的核心结论（指令级后门可跨任务迁移、截断后仍激活、继续微调难以治愈）是否在联邦 LoRA 下成立，论文没有验证。其中"继续微调难治愈"对"用后续联邦轮次冲掉后门"的防御思路是负面证据，但这一判断在联邦设定下仍需重新实验。
- 论文的 clean-label 且不改实例特性意味着基于标签翻转统计或数据内容一致性的检测会失效，这一点与是否联邦无关，**分析**：它在联邦 LoRA 下很可能同样成立。

## 10. 对防护库设计的含义

- **分析**：要复现或检测本文这一类攻击，采集底座需要在**客户端训练前**提供"逐样本三元组"视图，即指令文本、输入实例文本、标签三者的原始内容，并且指令字段要作为一等公民单独暴露。三元组采集是通用需求；把"指令"从提示模板中切分出来单独存储，是本文这类指令微调攻击特有的需求（Appx. §A.3 明确把指令近似为一段连续字符串）。
- **分析**：本文的攻击在服务器收到更新时、聚合时、聚合后都不留下论文分析过的信号，因此库的服务器钩子在这篇论文上没有落点；任何"用更新范数或增量统计检测指令后门"的想法都必须另找依据，不能引用本文。
- **分析**：本文的检测线索主要落在评估侧而不是训练侧：需要在评估钩子上提供两个视图——含触发器的对抗测试集与干净测试集——并按样本保存模型生成的文本，因为本文的后门目标标签可以是任意字符串（空串、含毒文本、MD5 编码，Tab. 2 与 Fig. 4）。这是通用需求。
- **分析**：本文没有给出自己的检测算法，因此库不应声称支持"本文的检测插件"；但论文评估的三类防御对应三种干预接口，值得作为插件形态参考：推理时的输入清洗与扰动（ONION、RAP）、训练后的模型修复或遗忘（SEAM）、推理时的干净示例注入。其中"输入清洗"落在服务侧，"模型修复"落在训练后侧。
- **分析**：本文的截断实验（Fig. 7）和编码实验（base64、MD5、ChatGPT 压缩）说明触发器匹配类插件必须对"部分出现"和"分布外编码"鲁棒，否则会被轻松绕过；库在设计触发器类插件接口时至少要允许"部分匹配"语义。
- **分析**：本文的干净标签与不改实例特性提示库不能假设后门一定伴随标签翻转或数据内容异常；数据视图必须保留原始指令与原始标签，而不是只保留清洗后的训练张量，否则这类攻击在采集阶段就已经不可见。

## 11. 原文依据

1. **Abstract** — 支撑第 1 节与第 3 节：攻击入口在数据投毒，且不改实例与标签，攻击预算极小。
   > "Our studies demonstrate that an attacker can inject backdoors by issuing very few malicious instructions (~1000 tokens) and control model behavior through data poisoning, without even the need to modify data instances or labels themselves."

2. **§3 Armory of Poison Attacks** — 支撑第 2 节：攻击目标的定义是输出攻击者指定的目标标签。
   > "In this work, misbehavior is defined as outputting the target label specified by the attacker in accord with the triggering feature."

3. **§3 Armory of Poison Attacks** — 支撑第 3 节与第 7 节：投毒流程是把改造后的样本注回干净训练集，投毒比例可低至 1%。
   > "Attacker selects a small percentage of instances from the clean training set and modifies them to create poison instances Dpoison, which are then injected back into the clean training set."

4. **§3 Armory of Poison Attacks** — 支撑第 2 节与第 9 节：干净标签是攻击成立的核心假设。
   > "For both approaches, we limit ourselves to clean label scenario (Li et al., 2022, 2023; Yan et al., 2022), where the labels for the poisoned instances must be correct and unmodified."

5. **§3 Poisoned models** — 支撑第 1 节与第 7 节：集中式指令微调设定、训练轮次与学习率、LoRA 的使用范围。
   > "We train the model via instruction-tuning for 3 epochs, with a learning rate 5 · 10−5. Due to computing limitations, we poison the LLaMA2 family with LoRA (Hu et al., 2021)."

6. **§3.2 Induced Instruction Attack** — 支撑第 4 节：攻击的核心原理是替换指令以建立新的输入—标签关联。
   > "The principle of the instruction attack is to substitute the original instruction I with a different one that is task-relevant and meaningful, similar to the clean instruction so that it is stealthy"

7. **§3.2 Induced Instruction Attack** — 支撑第 4 节：Induced Instruction 用标签翻转的示例提示 ChatGPT 生成毒指令。
   > "we give six exemplars, all with label flipped, and instruct ChatGPT to write the most plausible instruction that leads to the label"

8. **§4 Instruction Attacks Could Be More Harmful Than Instance-level Attacks** — 支撑第 5 节：论文声称该攻击能绕过检测，因为干净准确率几乎不变。
   > "Moreover, since CACC remains similar or sometimes even gets improved, such injected triggers will be extremely difficult to detect."

9. **§5 Instruction Attacks Are Transferable** — 支撑第 5 节与第 6 节：持续微调无法清除后门，对应 Tab. 3。
   > "In Tab. 3 we further instruction-tuning the already-poisoned model with the highest ASR on each of the remaining three datasets. We found no significant decrease in ASR across all different configurations."

10. **§6 Defense Against Instruction Attacks** — 支撑第 6 节：论文评估的三类防御及其作用方式与位置。
    > "We consider two test-time defenses ONION (Qi et al., 2021a), and RAP (Yang et al., 2021) that sanitize input before inference; and machine unlearning method SEAM (Zhu et al., 2022) that trains poisoned models on randomly labeled data"

```json
{
  "key": "xu2023instructionsbackdoor",
  "title": "Instructions as Backdoors: Backdoor Vulnerabilities of Instruction Tuning for Large Language Models",
  "year": 2023,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "训练数据中指令字段的文本（被替换或插入触发器后的毒指令）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "指令、输入实例与标签组成的三元组（攻击只改指令，实例与标签不变）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "在脏数据集上微调得到的模型或LoRA适配器", "where": "client_post_train", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "含毒指令输入下模型生成的输出文本（后门激活痕迹）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "攻击成功率ASR与干净准确率CACC（含截断触发器与编码触发器变体）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "继续指令微调后ASR的变化（跨轮历史）", "where": "evaluation", "granularity": "model", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "add_noise", "repair_model"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者能够向众包的指令数据集贡献数据",
    "干净标签假设：投毒样本的标签必须正确且未被修改",
    "攻击者只修改指令字段，不改动输入实例",
    "指令被简化为一段连续的字符串以便替换或插入",
    "受害者在含毒数据集上做指令微调，且模型会把毒指令与目标标签关联",
    "评测假设攻击技术已知",
    "整个流程是集中式单一训练者设定，不涉及客户端、聚合或非独立同分布数据"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第1节与第3节：攻击预算极小、入口是数据投毒、不改实例与标签", "text": "Our studies demonstrate that an attacker can inject backdoors by issuing very few malicious instructions (~1000 tokens) and control model behavior through data poisoning, without even the need to modify data instances or labels themselves."},
    {"section": "§3 Armory of Poison Attacks", "supports": "第2节：攻击目标是输出攻击者指定的目标标签", "text": "In this work, misbehavior is defined as outputting the target label specified by the attacker in accord with the triggering feature."},
    {"section": "§3 Armory of Poison Attacks", "supports": "第3节与第7节：投毒流程与低至百分之一的投毒比例", "text": "Attacker selects a small percentage of instances from the clean training set and modifies them to create poison instances Dpoison, which are then injected back into the clean training set."},
    {"section": "§3 Armory of Poison Attacks", "supports": "第2节与第9节：干净标签是攻击成立的核心假设", "text": "For both approaches, we limit ourselves to clean label scenario (Li et al., 2022, 2023; Yan et al., 2022), where the labels for the poisoned instances must be correct and unmodified."},
    {"section": "§3 Poisoned models", "supports": "第1节与第7节：集中式指令微调设定、三个epoch、学习率与LoRA的使用范围", "text": "We train the model via instruction-tuning for 3 epochs, with a learning rate 5 · 10−5. Due to computing limitations, we poison the LLaMA2 family with LoRA (Hu et al., 2021)."},
    {"section": "§3.2 Induced Instruction Attack", "supports": "第4节：攻击的核心原理是替换指令以建立新的指令与标签关联", "text": "The principle of the instruction attack is to substitute the original instruction I with a different one that is task-relevant and meaningful, similar to the clean instruction so that it is stealthy"},
    {"section": "§3.2 Induced Instruction Attack", "supports": "第4节：Induced Instruction用标签翻转的示例提示ChatGPT生成毒指令", "text": "we give six exemplars, all with label flipped, and instruct ChatGPT to write the most plausible instruction that leads to the label"},
    {"section": "§4 Instruction Attacks Could Be More Harmful Than Instance-level Attacks", "supports": "第5节：论文声称干净准确率不变使后门极难被检测", "text": "Moreover, since CACC remains similar or sometimes even gets improved, such injected triggers will be extremely difficult to detect."},
    {"section": "§5 Instruction Attacks Are Transferable", "supports": "第5节与第6节：持续微调无法清除后门，对应表3", "text": "In Tab. 3 we further instruction-tuning the already-poisoned model with the highest ASR on each of the remaining three datasets. We found no significant decrease in ASR across all different configurations."},
    {"section": "§6 Defense Against Instruction Attacks", "supports": "第6节：论文评估的三类防御及其作用方式与位置", "text": "We consider two test-time defenses ONION (Qi et al., 2021a), and RAP (Yang et al., 2021) that sanitize input before inference; and machine unlearning method SEAM (Zhu et al., 2022) that trains poisoned models on randomly labeled data"}
  ]
}
```
