# nist_b：NIST AI 100-2e2025（March 2025，NIST 对抗机器学习分类法的生成式 AI 部分）

> 资料范围说明：本资料是 NIST AI 100-2e2025 的后半部分（自“Generative AI Taxonomy”起，含第 4 章讨论、参考文献、Appendix A. Glossary）。文中反复引用的 PredAI 分类法（Fig. 1）与第 2 章内容不在本资料内，凡只能从 PredAI 部分获知的内容一律标注“资料未说明”。文档中数据来源标注为“NIST AI 100-2e2025 / March 2025”，正文标题在本资料中未出现，故不在此补写标题。

## 1. 要解决的问题

这份资料提供的是**对抗机器学习（adversarial machine learning，AML）攻击的分类法（taxonomy）**，其生成式 AI 部分明确以“attacks on GenAI systems”为对象：资料说“recent work has also introduced novel AML attacks specific to GenAI systems”，因此单独给出 Fig. 2 的 GenAI 攻击分类法，与 Fig. 1 的 PredAI 分类法并列。

它面向的读者包括模型开发者、应用设计者与部署者、下游开发者和用户，以及需要评估 AI 风险的组织：资料提到 NIST 为 model developers 编写了关于 dual-use foundation model 滥用风险管理的指南草稿，并说风险画像“may assist model developers and users in assessing risks, including those from adversarial attacks”；也提到“application designers may design systems with the assumption that prompt injection attacks are possible”“public education efforts can inform model users and application designers”。

它解决的问题是：把不断出现的攻击按**攻击者想破坏的系统属性（attacker goals/objectives）**、**攻击者必须具备的能力（attacker capabilities）**、**攻击类别（attack classes）与更具体的攻击类型**、以及**学习/部署阶段（learning stage）与攻击者知识（attacker knowledge）**组织起来，使攻击可以被归类、讨论和教学。资料说该分类法“first categorized by the system properties that attackers seek to compromise”。

它明确说自己不做的事有三类。第一，**不做风险管理决策**：“A key question that this taxonomy deliberately leaves aside is how organizations can make decisions about the development and use of AI systems in light of evidence about the increasing diversity of AML attacks and the efficacy and limitations of available mitigations.” 第二，**不承诺完备或安全保证**：缓解措施“are empirical in nature and lack theoretical or provable guarantees”，且“current mitigations do not offer full protection against all attacker techniques”。第三，**不覆盖非 AML 的供应链风险**：软件依赖、网络与存储等供应链风险“are critical in the broader context of securing AI systems”，但只有利用 ML 系统统计与数据特性的攻击才“falling within the domain of AML”；此外，把 AML 与其他可信 AI 特性的关系理清仍是“an area for ongoing work”。

## 2. 核心对象

资料**没有给出字段级 schema**：没有字段名清单，也没有说明哪些字段必填、取值范围为何。以下按正文实际赋予每类对象的属性归纳，逐项标注“资料未说明”的部分。资料中对象主要以自然语言条目、图中的圆/callout、术语表定义和编号引用四种形态出现。

**（1）GenAI 技术类别。** 属性为名称与定义。名称如 “GENERATIVE ADVERSARIAL NETWORKS”“GENERATIVE PRE-TRAINED TRANSFORMER (GPT)”“DIFFUSION MODELS”，并可组合出多模态系统（“some-times through combining two or more model types”）。必填与取值约束：资料未说明。

**（2）攻击者目标（attacker goals / objectives）。** 属性为：名称、定义句、NISTAML 编号。四个取值是 AVAILABILITY BREAKDOWN（[NISTAML.01]，破坏其他用户或进程对输出的及时、稳定访问）、INTEGRITY VIOLATION（[NISTAML.02]，迫使系统违背既定目标、产出符合攻击者意图的输出）、PRIVACY COMPROMISE（[NISTAML.03]，未授权获取训练数据、权重或架构、RAG 知识库等受限信息）、MISUSE ENABLEMENT（[NISTAML.04]，规避系统所有者施加的技术限制）。在 Fig. 2 中它们以 objective circles 形式承载外层能力与攻击类别 callout。必填与取值约束：资料未说明；四项被表述为“classified broadly along the dimensions of availability, integrity, and privacy, along with a new, GenAI-specific category”，未声明为严格封闭集合。

**（3）攻击者能力（attacker capabilities）。** 属性为：名称、定义句、“用于哪些攻击”。取值有四个：TRAINING DATA CONTROL（插入或修改训练样本，用于 DATA POISONING）、QUERY ACCESS（提交查询以诱导行为或提取信息，用于 PROMPT INJECTION、PROMPT EXTRACTION、MODEL EXTRACTION；其粒度还取决于 generation control 与返回内容的丰富度）、RESOURCE CONTROL（修改运行时被摄入的文档、网页等资源，用于 INDIRECT PROMPT INJECTION）、MODEL CONTROL（通过公开微调 API 或公开权重修改模型参数，用于 MODEL POISONING 与 FINE-TUNING CIRCUMVENTION）。必填与取值约束：资料未说明；原文用“These capabilities include:”措辞，未声明该列表封闭。

**（4）攻击类别与具体攻击手法（attack classes / attack techniques）。** 属性为：名称、所属目标（可多个）、所需能力、与更一般类别的父子关系、适用阶段、引用文献编号。出现的名称包括 DATA POISONING、MODEL POISONING、TARGETED POISONING ATTACK、BACKDOOR POISONING ATTACK、DIRECT PROMPTING ATTACK（[NISTAML.018]）、DIRECT PROMPT INJECTION、INDIRECT PROMPT INJECTION（[NISTAML.015]）、JAILBREAK、PROMPT INJECTION、PROMPT EXTRACTION、TRAINING DATA EXTRACTION、MODEL EXTRACTION、FINE-TUNING CIRCUMVENTION、INCREASED COMPUTATION，以及技术家族 optimization-based attacks、manual methods、automated model-based red teaming，具体手法如 prefix injection、refusal suppression、style injection、role-play、special encoding、character transformation、word transformation、prompt-level transformation。必填与取值约束：资料未说明。

**（5）学习与部署阶段。** 属性为：名称与包含关系。“One major division is between attacks that target the training stage and those that target model inference during the deployment stage”；TRAINING STAGE（[NISTAML.037]）常由 foundation model PRE-TRAINING 与 model FINE-TUNING 组成；此外 Fig. 7 给出部署生命周期的编号 1–7，缓解措施以“（2）（3）（4）（5）”这类括号编号指向其中的位置。必填与取值约束：资料未说明。

**（6）攻击者知识（attacker knowledge）。** 属性为白盒、灰盒、黑盒三档：“from full knowledge of the ML system including model weights (white-box attacks), to minimal knowledge and systems with deliberately obscured or misleading information (black-box attacks), to somewhere in between (gray-box attacks)”；资料说详细讨论见 Sec. 2.1.4，而该节不在本资料内。

**（7）数据与资源对象。** 属性为名称与其在攻击中的角色，包括 training data、training dataset 的 URL 列表与数据仓库、外部数据源（“documents, web pages”）、RAG 的 knowledge database、SYSTEM PROMPT、in-context 的用户信息、model weights 与 architecture、日志与用户活动记录。必填与取值约束：资料未说明。

**（8）缓解措施（mitigations）。** 属性为：名称或做法描述、所属生命周期位置编号、适用攻击范围（文字描述）、已知局限（文字描述）、外部编号。资料中出现的做法包括 pre-training/post-training 的安全训练与对抗训练、评估（vulnerability assessments、red teaming、bug bounties）、prompt instruction and formatting、detecting and terminating harmful interactions、prompt stealing detection、input modification、aggregating output from multiple prompts（SmoothLLM）、monitoring and response、usage restrictions，以及间接缓解 training data sanitization、unlearning、watermarking；外部编号为 MITRE ATLAS 的 AML.M0000（Limit Release of Public Information）、AML.M0001（Limit Model Artifact Release）、AML.M0002（Passive ML Output Obfuscation）、AML.M0004（Restrict Number of ML Model Queries），这些外部条目带有“Last Modified”日期。必填与取值约束：资料未说明。

**（9）检测机制。** 属性为名称与检测对象（用户输入、模型输出、提示窃取、异常输入）。包括“LLM-based detection systems with distinctly prompted and/or fine-tuned models that classify user input and/or model output as harmful or undesirable”、keyword- 或 perplexity-based defenses、interpretability-based techniques、prompt stealing detection（比对 token/word/phrase 或比较输出与输入的 n-grams）。必填与取值约束：资料未说明。

**（10）基准、数据集与工具。** 属性为名称与被评测的攻击类别。JailbreakBench、AdvBench、HarmBench、StrongREJECT、AgentHarm、Do-Not-Answer 用于 jailbreak 易感性；TrustLLM 评测 truthfulness、safety、fairness、robustness、privacy、machine ethics 六个维度；AgentDojo 评测 agent 对 prompt injection 的脆弱性；Garak 与 PyRIT 是开源漏洞发现工具；另有若干 unlearning benchmarks。必填与取值约束：资料未说明。

**（11）术语表条目（glossary）。** 属性为术语名、定义、被使用的页码链接：“Clicking on the page number at the end of a definition will navigate to the page where the term is used.” 例：adversarial machine learning 定义为“Attacks that exploit the statistical, data-based nature of machine learning systems.”

**（12）参考文献与外部框架条目。** 属性为顺序编号 [n]（[1]–[449]）、文献信息、检索或访问日期（如“Accessed: 2024-08-22”“retrieved December 2024”）；外部框架条目以 URL 形式给出（如 atlas.mitre.org/mitigations/AML.M0001）。

## 3. 编号与层级

**编号格式。** 本资料内部条目使用 “NISTAML.” 加零填充十进制数字，例如 NISTAML.01、NISTAML.02、NISTAML.03、NISTAML.04、NISTAML.05、NISTAML.015、NISTAML.016、NISTAML.017、NISTAML.018、NISTAML.027、NISTAML.035、NISTAML.036、NISTAML.037、NISTAML.038、NISTAML.039、NISTAML.051。编号出现在条目名称之后，并紧跟 “[Back to Index]” 回链标记；编号位数不统一（有两位也有三位），且不是所有条目都有编号——3.1.3 的四个能力、3.3.1 的各攻击技术、3.2.1/3.2.2 等小节都没有编号。编号分配规则、位数为何不同、是否与章节对应，资料未说明。外部缓解措施使用 MITRE ATLAS 的 “AML.M” 加四位数字（AML.M0000、AML.M0001、AML.M0002、AML.M0004），并附 “Last Modified” 日期。文献用方括号顺序编号 [n]。图表用 “Fig. 2”“Figure 2”“Fig. 7” 等两种写法混用。文档版本标识为 “NIST AI 100-2e2025 / March 2025”，其中 “e” 的含义资料未说明。

**层级。** 攻击分类法（taxonomy）是分层结构：最内层是攻击者目标（objective circles，四个目标），其外层是攻击者能力（“shown in the outer layer of the objective circles”），攻击类别作为 callout 连到“mount each attack”所需的能力上；更具体的攻击类型再通过“an additional callout”连到更一般的攻击类别（如 JAILBREAK 是 DIRECT PROMPTING ATTACK 的特例）。在攻击技术内部还有一层：技术家族（optimization-based attacks、manual methods、automated model-based red teaming）→ 具体手法（prefix injection、refusal suppression、style injection、role-play；special encoding、character transformation、word transformation、prompt-level transformation）。此外，攻击还可沿两个正交维度分类：“by the learning stage to which it applies and by the attacker’s knowledge and access”。章节层级为 3、3.1、3.1.1、…、4.2.6 与 Appendix A；全文另有 PredAI（Fig. 1）与 GenAI（Fig. 2）两套并列的分类法。

**命名规则。** 条目名多以大写或小型大写出现（如 DATA POISONING、SYSTEM PROMPT、RETRIEVAL-AUGMENTED GENERATION (RAG)），首字母缩写在首次出现时全称加括号。资料未说明命名规则或术语大小写的正式规定。

**同一事物在多处出现。** 资料明确规则：“Certain attack classes are listed multiple times because the same attack technique can be used to achieve different attacker goals.” 跨分类法也允许重复出现：PredAI 分类法中的攻击类型可以同时适用于 GenAI（“While many attack types in the PredAI taxonomy apply to GenAI…”），投毒缓解措施也“largely overlap with PredAI poisoning mitigations”，直接提示注入的防御“can also be adapted to mitigate indirect prompt injection”。术语表则用页码回链解决同一术语在多处被使用的问题。

## 4. 对象之间的关系

资料中的关系都画在 Fig. 2 里或以叙述方式给出，没有给出关系类型（relation）的名称清单：

- **攻击者目标 ← 攻击者能力**：能力位于目标圆的“outer layer”，即先确定要破坏的属性，再看需要哪些能力。
- **攻击类别 → 攻击者能力**：“Attack classes are shown as callouts connected to the capabilities required to mount each attack.” 方向是攻击类别指向它所需的能力。
- **具体攻击类型 → 更一般攻击类别**：“the specific attack is linked to the more general attack class through an additional callout”，例子是 jailbreak 属于 direct prompting attack。
- **同一攻击类别 → 多个目标**：同一条目被列出多次，因为它可以服务不同的攻击者目标。
- **攻击 → 学习阶段 / 攻击者知识**：攻击可“further categorized by the learning stage to which it applies and by the attacker’s knowledge and access”。
- **缓解措施 → 生命周期位置**：缓解措施以括号编号指向 Fig. 7 的位置，资料原话是“The numbers in parentheses refer to the numbering in Fig. 7, which shows a map of the deployment life cycle for broad-scale query access.” 例如“Interventions during pre-training (2) and post-training (3)”“Interventions during evaluation (4)”“Interventions during deployment (5)”。
- **缓解措施 → 外部框架条目**：正文在“usage restrictions”段落直接引用 MITRE ATLAS 的 AML.M0000、AML.M0001、AML.M0002、AML.M0004。
- **基准/工具 → 被评测的攻击类别**：如 JailbreakBench 等“provide benchmarks for evaluating models’ susceptibility to jailbreaks”，AgentDojo 针对 agent 的 prompt injection，Garak 与 PyRIT 用于发现 AML 漏洞。
- **术语 → 使用页码**：术语表条目通过页码链接回正文出现处。
- **NISTAML 编号 → 索引**：每个带编号条目后接 [Back to Index]。

**攻击侧与防御侧、检测侧、数据侧的关联方式（本节重点）。** 第一，**攻击侧与数据侧之间有一个中间对象**：数据与资源（training data、external resources、RAG knowledge base）不是直接挂到攻击类别上，而是先抽象成攻击者能力 TRAINING DATA CONTROL 与 RESOURCE CONTROL，再由攻击类别（DATA POISONING、INDIRECT PROMPT INJECTION）连到能力上；资料写“This capability is used in DATA POISONING attacks”“This capability is used for INDIRECT PROMPT INJECTION attacks”。第二，**攻击侧与防御侧之间没有直接关系**：Fig. 2 只包含目标、能力与攻击类别，缓解措施不在该图中；缓解措施按 Fig. 7 的生命周期位置编号组织，并在个别处引用 MITRE ATLAS 的外部编号。资料未给出攻击条目到缓解条目的对应表、矩阵或关系名。检测机制同样只按做法分组（检测用户输入、检测模型输出、检测提示窃取），未与具体攻击条目挂接。

## 5. 抽象层次的选择

**写到多细。** 条目主要描述攻击者的**目的**（四个目标）与**行为类别**（攻击类别与具体手法），而不是具体实现。技术层面的描述仍停留在方法家族与手法名称，例如“Optimization-based attacks design attack objective functions and use gradient or other search-based methods”“Automated model-based red teaming employs an attacker model, a target model, and a judge”；不涉及代码、超参数或可执行规则。同一攻击还可以被标注为针对单一设定或 universal、transferable（“may be applicable to a single setting and model, or may instead be universal … and/or transferable”），这些是属性而不是新条目。

**新条目、变体还是不收录。** 判定规则在资料中有两处明确依据。其一，**更一般类别的特例作为子条目**：“the specific attack is linked to the more general attack class through an additional callout”，jailbreak 即 direct prompting attack 的特例；同一技术不重复建条目，而是允许多次列出。其二，**刻意不细分**：misuse enablement 之所以能作为一个分类条目，是因为“the techniques for circumventing such defenses are often common between different kinds of models and different kinds of misuse, allowing them to be taxonomized as a part of AML without specificity as to the particular kinds of misuse that model developers seek to prevent”。

**准入标准。** 收录边界是“是否属于 AML”：AML 被定义为“Attacks that exploit the statistical, data-based nature of machine learning systems”；对于供应链风险，资料给出的准入判据是“there are certain types of attacks that rely on exploiting the specific statistical and data-based properties of ML systems, thus falling within the domain of AML”，其余供应链风险虽然重要但不进入该域。反之，与风险管理决策、与其他可信 AI 特性的关系、以及 AML 与 safety 的边界，被明确排除或留作“ongoing work”。资料未说明一条攻击在被收录前需要何种证据等级、复现要求或评审流程。

## 6. 稳定部分与易变部分

**希望很少变的骨架。** 攻击者目标的四分法（availability breakdown / integrity violation / privacy compromise，加 GenAI 新增的 misuse enablement）在 PredAI 与 GenAI 两套分类法之间保持一致；攻击者能力四分法（TRAINING DATA CONTROL、QUERY ACCESS、RESOURCE CONTROL、MODEL CONTROL）同样是跨攻击复用的中间层；训练/部署的两分与 Fig. 7 的生命周期编号 (1)–(7)；术语表定义；NISTAML 编号与 [Back to Index] 回链机制；以及对外部框架编号（MITRE ATLAS 的 AML.Mxxxx）与文献编号 [n] 的引用方式。

**预期不断增长的部分。** 攻击类别与具体手法（“recent work has also introduced novel AML attacks specific to GenAI systems”）、缓解措施（“the growing number of proposed defenses at both the model and the system levels”）、基准与工具（“There are several publicly available benchmarks…”，并逐一列举新出现的 JailbreakBench、AgentHarm、AgentDojo 等）、参考文献，以及随模型形态新增的章节（agents、multimodal models、quantized models）。

**新增、废弃与版本管理。** 资料中的版本信息是文档级的：页面页眉为 “NIST AI 100-2e2025 / March 2025”。引用条目带检索/访问日期（“Accessed: 2024-08-22”“retrieved December 2024”），外部 MITRE ATLAS 条目带“Last Modified”日期，说明外部内容会独立演进；[Back to Index] 与 NISTAML 编号暗示存在一个可回链的在线索引。但**条目的新增流程、废弃或撤回流程、变更日志、编号复用规则、版本号语义，资料未说明**。资料只说明某些内容是暂时性的，例如“more precisely relating AML attacks and mitigations to processes for achieving these goals and managing risks in AI systems is an area for ongoing work”。

## 7. 内容与执行的分离

**内容形态。** 知识以一份 PDF 报告承载：正文叙述 + 图（Fig. 2 攻击分类图、Fig. 3 训练流水线、Fig. 4 企业采用流水线、Fig. 5 参考架构、Fig. 6 RAG 结构、Fig. 7 生命周期图、Fig. 8 Pareto 图）+ 术语表 + 编号引用。分类结构本身以图的圆、外层与 callout 表达，条目以正文段落表达，缓解措施以带生命周期括号编号的列表表达。**资料未说明存在机器可读的数据文件、本体（ontology）、模式（schema）或规则格式**；外部条目则通过 URL 指向（如 atlas.mitre.org/mitigations/AML.M0001）。值得注意的分离是：攻击与防御方法本身不在框架内实现，而是以文献编号 [n] 指回原文。

**由什么解释或执行。** 资料中没有任何解释器、执行器或自动匹配引擎；分类法的使用方式是人工阅读与归类。资料提到若干外部可执行物（Garak、PyRIT 被描述为“open-source tools … intended to help developers identify vulnerabilities”，基准被描述为“evaluation framework”），但这些是基准与工具，不是分类法的执行引擎。

**表达上限与超出时的处理。** 该分类法能表达的是“目标—能力—攻击类别—具体手法”的归属、阶段的归属、以及缓解措施所处的生命周期位置。它无法表达缓解措施的有效性、权衡与保证；这些要么被明确列为开放问题（“The full characterization of the trade-offs between the different attributes of trustworthy AI is an open research problem”），要么被交给外部文件与流程处理：NIST AI RMF（[274]）、GenAI Profile（[273]）、dual-use foundation model 滥用风险管理指南（[275]）、结构化 red teaming（[68, 133]）、基准数据集与 Pareto 图比较（Fig. 8）。

## 8. 覆盖与成熟度的表达

**覆盖。** 资料未说明存在覆盖矩阵、覆盖状态字段或“某攻击是否已被防御覆盖”的标记。最接近覆盖表达的机制有三个。第一，**生命周期定位**：缓解措施被标注作用于 Fig. 7 的哪一步（pre-training (2)、post-training (3)、evaluation (4)、deployment (5)），从而可以看出防御落在生命周期的哪个位置；Fig. 7 本身在若干阶段旁标注 “Exposure”，并列出 Access Control、Continuous Evaluation、Safety Improvements、Monitoring & Reporting、Unlearning、Editing、Interpretability、Tool Use、Fine-Tuning、API Security 等项。第二，**基准覆盖**：用基准说明某一类攻击是否可被评测（JailbreakBench、AdvBench、HarmBench、StrongREJECT、AgentHarm、Do-Not-Answer 对应 jailbreak；AgentDojo 对应 agent 的 prompt injection；TrustLLM 对应六个可信维度）。第三，**跨分类法覆盖**：明确指出 GenAI 投毒缓解措施与 PredAI 大量重叠，直接提示注入的防御可改编用于间接提示注入。

**成熟度。** 资料未说明条目级成熟度字段、分级或状态值。成熟度与效果以三类方式表达。第一，**文字判断**：例如 prompt stealing 的防御“have yet to be proven rigorous”；水印“there is no watermarking technique that is universally effective and robust under all circumstances”，并有不可能性结果；检测系统“are also vulnerable to attacks … and may have correlated failures to the main models that they are monitoring”；unlearning 方法“remain vulnerable to adversarial attacks”。第二，**评测要求**：新缓解措施应当被对抗性测试，“new mitigations should be tested adversarially, with the researchers proposing the mitigation also trying to break it”；并且不应逐属性孤立评估，而应“compared on a Pareto plot (as in Fig. 8)”，即在 accuracy 与 adversarial robustness 等多目标间给出前沿位置。第三，**整体性结论**：缓解措施缺少理论保证，“current generation models remain highly vulnerable to direct prompt injection attacks”，且“Evaluations measure model vulnerabilities at a particular moment in time”，因此“Current evaluation approaches, though a useful tool, may underestimate vulnerabilities accessible to actors with more time, resourcing, or luck.”

## 9. 对我们的启发

分析：可以把“攻击者目标 × 攻击者能力 × 生命周期阶段”当作**稳定骨架**，让 methods 层的每篇论文插件先声明自己落在哪个格子里，而不是以论文本身作为条目的第一身份。对应 knowledge_base 层，并由 methods 层提供元数据。依据是本资料的骨架（四个目标、四个能力、训练/部署两分）在两代分类法之间不变，而增长的只是攻击类别；这样“覆盖了什么、缺什么”可以由格子空缺直接读出。

分析：同一条目允许多处出现、只挂引用不复制（“Certain attack classes are listed multiple times because the same attack technique can be used to achieve different attacker goals.”）。对应 knowledge_base 与 operators 层：一个算子或方法条目应当是唯一的，但可声明多个适用位置（11 个运行时位置中的一个或多个），从而避免同一 LoRA 聚合规则在不同论文名下被写成多个插件。

分析：把“能力/暴露面”作为攻击与数据之间的**中间对象**。TRAINING DATA CONTROL、MODEL CONTROL、QUERY ACCESS、RESOURCE CONTROL 恰好对应我们 11 个位置中的样本、梯度与训练步内 LoRA、客户端上传、聚合结果、下发内容、通道消息等暴露点。对应 runtime 层：把每个位置定义成可被引用的暴露面对象，形成 attack → capability → position 的路径，防御方法则声明自己作用于哪个 position，而不是直接声明“我防某篇论文的攻击”。

分析：新条目与变体的判定可以照搬 callout 规则：更一般类别的特例挂成子条目，只有引入新的计算单元才升级为并列条目。对应 methods 层与 operators 层：换范数、换阈值、换裁剪方式的防御若是既有算子族的特例，就登记为变体并继承父条目属性；只有当它引入新的可复用计算单元时才新增 operator。

分析：缓解措施按生命周期位置编号（“The numbers in parentheses refer to the numbering in Fig. 7…”）而不是按攻击编号，这是一个可以直接改造的覆盖表达方式。对应 knowledge_base 与 evaluation 层：用 11 个运行时位置做索引列，行是算子/方法，天然得到一张覆盖矩阵，并显式暴露“空列”（无人防守的位置）；这比按论文计数更能回答“我们到底覆盖了什么”。

分析：术语表 + 稳定 ID + 回链的机制可以整体借用。对应 records 与 knowledge_base 层：为每个算子、方法、暴露面分配稳定 ID，把术语（后门、投毒、LoRA 更新、聚合规则等）集中定义并回链，避免同一防御名在不同论文里含义漂移；带编号条目后接回链这一点尤其值得保留。

分析：允许引用外部框架的 ID 而不复制其内容（正文直接引用 MITRE ATLAS 的 AML.M0000–AML.M0004）。对应 records 层：方法条目应支持 external_ref 字段，用 DOI/arXiv/ATLAS 编号指向已发表工作，把“库里的条目”和“论文原文”分离，这也正好缓解“库只能一篇篇追”的问题。

分析：成熟度表达不能照抄，因为该框架**根本没有成熟度字段**，只有“经验性、缺少理论保证”“尚未被证明严格”这类文字判断，以及用 Pareto 前沿做多目标比较。对应 evaluation 层：我们需要自己定义状态字段（例如理论保证/经验有效/已被攻破）并要求每个 method 插件附上对抗性自测记录；Pareto 图这一条可以借用，因为我们的防御同样是数值算法，天然存在隐私—效用—鲁棒性的权衡。

分析：该框架的**缓解措施清单不能照搬**，因为它的防御面是提示工程、输出过滤、检测并终止交互、封禁用户、限制查询次数与返回信息、水印，这些做法依赖“输入输出是可读文本、可日志、可拦截”。我们的防御是数值算法（聚合规则、梯度裁剪、差分隐私、低秩约束），运行在客户端上传与聚合之间，没有等价的“日志匹配”语义。对应 operators 层与 methods 层：只能借用它的组织方式，不能借用它的手段分类。

分析：它的**攻击面定义也不能直接作为我们的完备性标准**。资料把 GenAI 的根因归结为系统属性：“data and instructions are not provided in separate channels to the LLM”，而联邦 LoRA 微调的暴露面是分布式优化过程（样本、梯度、上传、聚合、下发、通道）。两者只在投毒、后门、模型/数据提取等类别上有交集。对应 knowledge_base 层：骨架可以借用，条目内容必须自建，并且要在库里显式登记“本库不适用的攻击类别”，否则覆盖度会被高估。

分析：资料对评测的诊断同样适用于我们：缺少可靠基准会让论文结果“routinely incomparable”，因此只记录“防御成功率”会导致方法之间不可比。对应 evaluation 层：把基准（数据集、攻击脚本、超参数、随机种子）与算子绑定记录，让不同论文的防御在同一配置下可比。

## 10. 框架自己承认的局限

- **明确把风险管理决策排除在外**：“A key question that this taxonomy deliberately leaves aside is how organizations can make decisions about the development and use of AI systems in light of evidence about the increasing diversity of AML attacks and the efficacy and limitations of available mitigations.”
- **缺少可靠基准**：“Another general problem of AML mitigations for both evasion and poisoning attacks is the lack of reliable benchmarks, which causes results from AML papers to be routinely incomparable, as they do not rely on the same assumptions and methods.”
- **缓解措施缺少理论保证**：“many AML mitigations are empirical in nature and lack theoretical or provable guarantees.”
- **检测在理论上等价于鲁棒分类**：Tramèr 证明“designing techniques to detect adversarial examples is equivalent to robust classification, which is inherently difficult to solve”；OOD 检测在分布重叠时存在不可能性结果（Fang et al.）。
- **对齐的极限**：只要模型有非零概率表现出不良行为，就存在能触发它的提示；任何只削弱而不移除不良行为的对齐过程仍然脆弱；且存在“the impossibility of model-based detection to prevent all impermissible outputs”。
- **评估可能低估对手**：“Current evaluation approaches, though a useful tool, may underestimate vulnerabilities accessible to actors with more time, resourcing, or luck.” 且“Evaluations measure model vulnerabilities at a particular moment in time”。
- **检测系统本身可被攻击**：检测系统“are also vulnerable to attacks … and may have correlated failures to the main models that they are monitoring”；提示窃取防御“have yet to be proven rigorous”。
- **水印没有万全方案**：“there is no watermarking technique that is universally effective and robust under all circumstances”，且存在鲁棒性的不可能性结果。
- **当前缓解措施不足以完全防护**：“Because current mitigations do not offer full protection against all attacker techniques, application designers may design systems with the assumption that prompt injection attacks are possible if a model is exposed to untrusted input sources.”
- **缓解措施自身有副作用**：usage restrictions“may have additional drawbacks in limiting positive use cases”；训练数据净化“may harm generalization and harmful content detection abilities”；SmoothLLM“incurs a cost of generating multiple LLM queries for each prompt and might reduce the quality of the generated output”；输入改写“may be expensive and/or have trade-offs with model performance”。
- **研究空白**：“Security research focused specifically on agents is still in its early stages”；量化对 GenAI 的影响“have not been studied as thoroughly”；多模态冗余未必提高鲁棒性，“mitigation techniques that only rely on single modality perturbations are not likely to be robust”。
- **形式化方法与审计的困难**：形式化方法成本高、目前主要用于法规强制的场景，扩展到 ML 算子与大模型仍需研究；模型权重中的漏洞无法像开源软件那样审计，Goldwasser 等人提出的“information-theoretically undetectable Trojans”若被证明可行将带来重大供应链挑战。
- **分类法未覆盖的关系**：AML 与其他可信 AI 特性、与 AI safety 的关系“is an area for ongoing work”，且“AML is neither a complete solution to, nor a subset of, any one of these characteristics”。

## 11. 原文依据

1. 支撑第 2 节与第 4 节（攻击分类法按“被破坏的系统属性”组织，即攻击者目标是顶层对象）：
   > “Similar to the PredAI taxonomy in Fig. 1, this taxonomy is first categorized by the system properties that attackers seek to compromise in each case, including availability breakdowns, integrity violations, and privacy compromises”

2. 支撑第 2 节（攻击者能力是独立对象，且写明它被哪些攻击使用）：
   > “TRAINING DATA CONTROL: The attacker might take control of a subset of the training data by inserting or modifying training samples. This capability is used in DATA POISONING attacks.”

3. 支撑第 4 节（目标—能力—攻击类别三层的连线方向）：
   > “The capabilities that an adversary must leverage to achieve their objectives are shown in the outer layer of the objective circles. Attack classes are shown as callouts connected to the capabilities required to mount each attack.”

4. 支撑第 3 节与第 5 节（更一般的类别与具体攻击类型之间的父子挂接规则）：
   > “the specific attack is linked to the more general attack class through an additional callout”

5. 支撑第 3 节与第 6 节（同一事物在多处出现的处理方式）：
   > “Certain attack classes are listed multiple times because the same attack technique can be used to achieve different attacker goals.”

6. 支撑第 5 节（AML 的准入标准：必须利用 ML 的统计与数据特性）：
   > “there are certain types of attacks that rely on exploiting the specific statistical and data-based properties of ML systems, thus falling within the domain of AML”

7. 支撑第 5 节（刻意不细分具体滥用种类，以保持在可复用抽象层）：
   > “the techniques for circumventing such defenses are often common between different kinds of models and different kinds of misuse”

8. 支撑第 6 节（哪些部分预期持续增长：GenAI 特有的新攻击）：
   > “While many attack types in the PredAI taxonomy apply to GenAI (e.g., data poisoning, model poisoning, and model extraction), recent work has also introduced novel AML attacks specific to GenAI systems.”

9. 支撑第 7 节（知识以图与叙述承载，而非可执行内容）：
   > “Figure 2 shows a taxonomy of attacks in AML for GenAI systems.”

10. 支撑第 8 节（缓解措施按生命周期位置编号，这是框架中唯一的覆盖定位表达）：
    > “The numbers in parentheses refer to the numbering in Fig. 7, which shows a map of the deployment life cycle for broad-scale query access.”

```json
{
  "key": "nist_b",
  "framework": "NIST AI 100-2e2025（March 2025）——面向生成式 AI 系统的对抗机器学习（AML）攻击分类法；资料为文档后半部分（Generative AI Taxonomy 起，含第 4 章讨论、References、Appendix A Glossary）",
  "object_types": [
    {"name": "GenAI 技术类别（GENERATIVE ADVERSARIAL NETWORKS / GENERATIVE PRE-TRAINED TRANSFORMER (GPT) / DIFFUSION MODELS / MULTIMODAL MODELS）", "role": "other", "fields": ["名称", "定义（资料未说明字段级 schema、必填与取值约束）"]},
    {"name": "攻击者目标 / 攻击者意图（AVAILABILITY BREAKDOWN / INTEGRITY VIOLATION / PRIVACY COMPROMISE / MISUSE ENABLEMENT）", "role": "other", "fields": ["名称", "定义句", "NISTAML 编号（NISTAML.01–.04）", "在 Fig. 2 中作为 objective circles 承载能力外层与攻击类别 callout", "必填与取值约束：资料未说明（表述为 classified broadly，未声明封闭）"]},
    {"name": "攻击者能力（TRAINING DATA CONTROL / QUERY ACCESS / RESOURCE CONTROL / MODEL CONTROL）", "role": "attack", "fields": ["名称", "定义句", "被哪些攻击使用（This capability is used in …）", "必填与取值约束：资料未说明（原文用 include 措辞）"]},
    {"name": "攻击类别与具体攻击手法（DATA POISONING / MODEL POISONING / BACKDOOR POISONING / TARGETED POISONING / DIRECT PROMPTING ATTACK / INDIRECT PROMPT INJECTION / JAILBREAK / PROMPT EXTRACTION / TRAINING DATA EXTRACTION / MODEL EXTRACTION / FINE-TUNING CIRCUMVENTION 及各类技术家族与手法）", "role": "attack", "fields": ["名称", "所属攻击者目标（可多个）", "所需攻击者能力", "与更一般类别的父子关系（additional callout）", "适用学习阶段", "引用文献编号", "必填与取值约束：资料未说明"]},
    {"name": "学习与部署阶段（TRAINING STAGE / DEPLOYMENT STAGE / PRE-TRAINING / FINE-TUNING；Fig. 7 的编号 1–7）", "role": "other", "fields": ["名称", "包含关系", "Fig. 7 中的位置编号", "必填与取值约束：资料未说明"]},
    {"name": "攻击者知识（white-box / gray-box / black-box）", "role": "other", "fields": ["名称", "定义", "详细讨论指向 Sec. 2.1.4（不在本资料内）"]},
    {"name": "数据与资源对象（training data、external data sources、RAG knowledge base、SYSTEM PROMPT、in-context 用户信息、model weights 与 architecture、日志与用户活动记录）", "role": "telemetry", "fields": ["名称", "在攻击中的角色", "通过与攻击者能力（TRAINING DATA CONTROL / RESOURCE CONTROL 等）的连线被攻击引用", "必填与取值约束：资料未说明"]},
    {"name": "缓解措施（pre-training/post-training 干预、evaluation、deployment 期干预、training data sanitization、unlearning、watermarking、spotlighting、SmoothLLM、usage restrictions；MITRE ATLAS AML.M0000–AML.M0004）", "role": "defense", "fields": ["名称或做法描述", "所属生命周期位置编号（2）（3）（4）（5）", "适用攻击范围的文字描述", "已知局限的文字描述", "外部编号（AML.Mxxxx）与 Last Modified 日期", "必填与取值约束：资料未说明"]},
    {"name": "检测机制（LLM-based detection systems、keyword/perplexity-based defenses、interpretability-based detection、prompt stealing detection）", "role": "detection", "fields": ["名称", "检测对象（用户输入 / 模型输出 / 提示窃取 / 异常输入）", "已知局限（可被攻击、与主模型相关失效）", "必填与取值约束：资料未说明"]},
    {"name": "基准、数据集与工具（JailbreakBench、AdvBench、HarmBench、StrongREJECT、AgentHarm、Do-Not-Answer、TrustLLM、AgentDojo、Garak、PyRIT、unlearning benchmarks）", "role": "test", "fields": ["名称", "被评测的攻击类别或维度", "必填与取值约束：资料未说明"]},
    {"name": "术语表条目（Appendix A. Glossary）", "role": "other", "fields": ["术语名", "定义", "被使用的页码链接", "必填与取值约束：资料未说明"]},
    {"name": "参考文献与外部框架条目（[n] 与 atlas.mitre.org/mitigations/AML.Mxxxx）", "role": "artifact", "fields": ["顺序编号 [n]", "文献或页面信息", "检索/访问日期（Accessed / retrieved）或 Last Modified 日期", "必填与取值约束：资料未说明"]}
  ],
  "id_scheme": "内部条目：NISTAML. + 零填充十进制数（NISTAML.01、.02、.03、.04、.05、.015、.016、.017、.018、.027、.035、.036、.037、.038、.039、.051），条目后接 [Back to Index] 回链；编号位数不统一，且并非所有条目都有编号（3.1.3 的攻击者能力、3.3.1 的攻击技术均无编号），编号分配规则资料未说明。外部缓解措施：MITRE ATLAS 的 AML.M + 四位数字（AML.M0000–AML.M0004），附 Last Modified 日期。文献：方括号顺序编号 [1]–[449]。图表：Fig./Figure + 数字。章节：3.1.1 式十进制层级。文档版本标识 NIST AI 100-2e2025 / March 2025，其中 e 的含义资料未说明。",
  "attack_defense_link": "none",
  "link_detail": "Fig. 2 的攻击分类图只包含攻击者目标（objective circles）、攻击者能力（outer layer）与攻击类别（callout），缓解措施不在其中；攻击侧与防御侧之间没有直接边，也没有攻击→缓解的对应表或关系名。缓解措施改为按 Fig. 7 部署生命周期的位置编号组织（括号编号 (2)(3)(4)(5)：pre-training、post-training、evaluation、deployment），并在少数处引用 MITRE ATLAS 的外部编号 AML.M0000–AML.M0004。攻击侧与数据侧之间则存在中间对象：数据与资源先被抽象成攻击者能力 TRAINING DATA CONTROL 与 RESOURCE CONTROL，再由 DATA POISONING、INDIRECT PROMPT INJECTION 等攻击类别连到这些能力上。检测机制、基准也只按做法或评测对象分组，未与具体攻击条目挂接。",
  "abstraction_level": "描述目的与行为，不描述实现。顶层是四个攻击者目标；其外层是四个攻击者能力；攻击类别通过 callout 连到所需能力；更具体的攻击类型通过 additional callout 挂到更一般的攻击类别（jailbreak 是 direct prompting attack 的特例）。技术层再分为家族（optimization-based attacks、manual methods、automated model-based red teaming）与具体手法（prefix injection、refusal suppression、style injection、role-play；special encoding、character transformation、word transformation、prompt-level transformation）。判定规则：更一般类别的特例不新建并列条目；同一技术可挂到多个目标，因此在图中多次出现；对 misuse enablement 刻意不细分具体滥用种类。准入标准：必须利用 ML 系统的统计与数据特性（AML 定义），其余供应链风险不进入该域；风险管理决策、与其他可信 AI 特性的关系被明确排除或留作 ongoing work。",
  "stable_parts": ["攻击者目标四分法（AVAILABILITY BREAKDOWN / INTEGRITY VIOLATION / PRIVACY COMPROMISE / MISUSE ENABLEMENT）", "攻击者能力四分法（TRAINING DATA CONTROL / QUERY ACCESS / RESOURCE CONTROL / MODEL CONTROL）", "训练阶段与部署阶段的两分，以及 Fig. 7 的生命周期编号 (1)–(7)", "术语表（Appendix A. Glossary）中的术语定义", "NISTAML.xxx 编号与 [Back to Index] 回链机制", "对文献编号 [n] 与外部框架编号（MITRE ATLAS AML.Mxxxx）的引用方式"],
  "growing_parts": ["新的攻击类别与具体攻击手法（new novel AML attacks specific to GenAI systems）", "缓解措施清单（a growing number of proposed defenses at both the model and the system levels）", "基准、数据集与工具（JailbreakBench、AdvBench、HarmBench、StrongREJECT、AgentHarm、Do-Not-Answer、TrustLLM、AgentDojo、Garak、PyRIT、unlearning benchmarks）", "参考文献（[1]–[449]）", "随模型形态新增的章节与议题（agents、multimodal models、quantized models）"],
  "content_format": "PDF 报告：叙述正文 + 图（Fig. 2 攻击分类图、Fig. 3 训练流水线、Fig. 4/5 企业采用流水线与参考架构、Fig. 6 RAG、Fig. 7 生命周期图、Fig. 8 Pareto 图）+ 术语表 + 编号引用；条目通过 NISTAML.xxx 与 [Back to Index] 指向在线索引，外部条目通过 URL（如 atlas.mitre.org/mitigations/AML.M0001）指向。资料未说明存在机器可读的数据文件、本体（ontology）、schema 或规则格式。",
  "execution_engine": "资料未说明。没有任何解释器、执行器或自动匹配引擎：分类法由人阅读并用于归类，缓解措施以带生命周期括号编号的自然语言列表描述，具体攻击与防御实现以文献编号指向原文；资料中提到的可执行物是外部基准与工具（Garak、PyRIT、AgentDojo 等），不是本分类法的执行引擎。",
  "coverage_expression": "资料未说明存在覆盖矩阵或覆盖状态字段。最接近的表达是：把缓解措施标注到 Fig. 7 部署生命周期的编号位置（The numbers in parentheses refer to the numbering in Fig. 7）；用基准数据集表达某类攻击是否可评测（JailbreakBench 等针对 jailbreaks，AgentDojo 针对 agent prompt injection）；以及说明 GenAI 投毒缓解措施与 PredAI 大量重叠、直接提示注入防御可改编用于间接提示注入。",
  "maturity_expression": "资料未说明条目级成熟度字段、分级或状态值。成熟度与效果以三种方式表达：文字判断（如 prompt stealing 防御 have yet to be proven rigorous；水印没有 universally effective and robust 的技术；检测系统自身可被攻击且与主模型相关失效）；评测要求（new mitigations should be tested adversarially, with the researchers proposing the mitigation also trying to break it）；多目标比较（mitigations should be compared on a Pareto plot，如图 8 的 accuracy 与 adversarial robustness）。",
  "lessons": [
    {"idea": "以“攻击者目标 × 攻击者能力 × 生命周期阶段”作为稳定骨架，让每篇论文的防御先声明自己落在哪个格子，而不是以论文作为条目身份", "applies_to": "knowledge_base", "transfer": "adapted", "why": "该框架的四个目标与四个能力在 PredAI/GenAI 两代分类法之间保持不变，增长的只是攻击类别；据此可以直接读出覆盖空缺，解决“只能一篇篇追、说不清覆盖了什么”。"},
    {"idea": "条目唯一、允许多处引用：同一技术可被多个目标列出，而不复制成多条", "applies_to": "knowledge_base", "transfer": "direct", "why": "原文明确 Certain attack classes are listed multiple times because the same attack technique can be used to achieve different attacker goals；我们的算子/方法应声明多个适用位置而非拆成多个插件。"},
    {"idea": "把“能力/暴露面”作为攻击与数据之间的中间对象，形成 attack → capability → position 路径", "applies_to": "runtime", "transfer": "adapted", "why": "TRAINING DATA CONTROL、MODEL CONTROL、QUERY ACCESS、RESOURCE CONTROL 可映射到 11 个运行时位置（样本、梯度与训练步内 LoRA、客户端上传、聚合结果、下发内容、通道消息），防御方法声明作用位置而不是声明防某篇论文。"},
    {"idea": "新条目与变体的判定规则：更一般类别的特例挂成子条目，只有引入新计算单元才升级为并列条目", "applies_to": "methods", "transfer": "direct", "why": "原文用 additional callout 把 jailbreak 挂到 direct prompting attack 之下；换范数、换阈值的防御应登记为既有算子族的变体，避免方法层条目爆炸。"},
    {"idea": "缓解措施按生命周期位置编号，而不是按攻击编号，从而形成天然的覆盖矩阵", "applies_to": "evaluation", "transfer": "adapted", "why": "原文用括号编号指向 Fig. 7 的生命周期位置；我们把索引换成 11 个运行时位置，就能显式暴露无人防守的空列。"},
    {"idea": "术语表 + 稳定 ID + 回链，把定义集中管理并允许跨条目引用", "applies_to": "records", "transfer": "direct", "why": "原文的 glossary 定义配页码回链、条目配 NISTAML 编号与 [Back to Index]；库里同样需要稳定 ID 与集中术语，避免同名异义。"},
    {"idea": "允许引用外部框架的 ID 而不复制其内容", "applies_to": "records", "transfer": "direct", "why": "正文直接引用 MITRE ATLAS 的 AML.M0000–AML.M0004；方法条目应支持 external_ref（DOI/arXiv/ATLAS 编号），把库内条目与论文原文分离。"},
    {"idea": "成熟度必须自建：该框架没有成熟度字段，只有文字判断与 Pareto 多目标比较", "applies_to": "evaluation", "transfer": "adapted", "why": "我们需要自己的状态字段（理论保证 / 经验有效 / 已被攻破）并要求 method 插件附对抗性自测；Pareto 前沿比较可直接借用，因为数值防御天然存在隐私—效用—鲁棒性权衡。"},
    {"idea": "防御手段清单不可照搬", "applies_to": "operators", "transfer": "not_transferable", "why": "该框架的防御是提示工程、输出过滤、检测并终止交互、封禁用户、限制查询次数与返回信息、水印，依赖输入输出是可读文本、可日志、可拦截；我们的防御是聚合规则、梯度裁剪、差分隐私、低秩约束等数值算法，没有等价的日志匹配语义。"},
    {"idea": "攻击面定义不可直接当作完备性标准", "applies_to": "knowledge_base", "transfer": "not_transferable", "why": "该框架把 GenAI 的根因归结为 data and instructions are not provided in separate channels to the LLM，而联邦 LoRA 微调的暴露面是分布式优化过程（上传、聚合、下发、通道），两者只在投毒、后门、提取等类别上交集；因此需显式登记“本库不适用的攻击类别”，否则覆盖率会被高估。"},
    {"idea": "评测可比性：把基准（数据集、攻击脚本、超参、种子）与算子绑定记录", "applies_to": "evaluation", "transfer": "adapted", "why": "原文诊断缺少可靠基准导致 AML 论文结果 routinely incomparable；我们若只记录防御成功率，同样会出现方法之间不可比。"}
  ],
  "limits": [
    "分类法明确不解决风险管理决策：A key question that this taxonomy deliberately leaves aside is how organizations can make decisions about the development and use of AI systems…",
    "缺少可靠基准，导致 AML 论文结果 routinely incomparable，假设与方法不统一。",
    "许多 AML 缓解措施是经验性的，缺少理论或可证明的保证。",
    "检测对抗样本等价于鲁棒分类，本质困难；分布重叠时 OOD 检测存在不可能性结果。",
    "对齐的极限：只要模型有非零概率表现不良行为，就存在能触发它的提示；也存在无法阻止所有不允许输出的不可能性结果。",
    "评估可能低估拥有更多时间、资源或运气的攻击者；评估只反映某一时刻的模型脆弱性。",
    "检测系统本身可被攻击，且可能与它所监控的主模型发生相关失效；提示窃取防御尚未被证明严格。",
    "水印不存在普遍有效且鲁棒的技术，并有鲁棒性不可能性结果。",
    "当前缓解措施不提供完全防护，因此系统设计必须假设提示注入可能发生。",
    "缓解措施自身有副作用：使用限制会限制正当用途，数据净化可能损害泛化与有害内容检测，SmoothLLM 增加查询成本并可能降低输出质量，输入改写昂贵且影响性能。",
    "研究空白：agent 安全研究仍在早期，量化对 GenAI 的影响研究不足，多模态冗余不保证鲁棒性，仅靠单模态扰动的缓解不太可能鲁棒。",
    "形式化方法成本高、尚未广泛采用，扩展到 ML 算子与大模型仍需研究；模型权重中的漏洞难以像开源软件那样审计，不可检测木马是供应链挑战。",
    "AML 与 AI safety 及其他可信 AI 特性的关系尚未理清，是 ongoing work；AML 既不等于也不包含于其中任一特性。"
  ],
  "quotes": [
    {"supports": "第 2 节与第 4 节：分类法以“攻击者试图破坏的系统属性”为顶层维度，即攻击者目标是顶层对象", "text": "Similar to the PredAI taxonomy in Fig. 1, this taxonomy is first categorized by the system properties that attackers seek to compromise in each case, including availability breakdowns, integrity violations, and privacy compromises"},
    {"supports": "第 2 节：攻击者能力是独立对象，并写明它被哪类攻击使用", "text": "TRAINING DATA CONTROL: The attacker might take control of a subset of the training data by inserting or modifying training samples. This capability is used in DATA POISONING attacks."},
    {"supports": "第 4 节：目标—能力—攻击类别三层的连线方向", "text": "The capabilities that an adversary must leverage to achieve their objectives are shown in the outer layer of the objective circles. Attack classes are shown as callouts connected to the capabilities required to mount each attack."},
    {"supports": "第 3 节与第 5 节：具体攻击类型通过 additional callout 挂到更一般的攻击类别，即新条目与变体的判定规则", "text": "the specific attack is linked to the more general attack class through an additional callout"},
    {"supports": "第 3 节与第 6 节：同一攻击技术在不同目标下多处出现的处理方式", "text": "Certain attack classes are listed multiple times because the same attack technique can be used to achieve different attacker goals."},
    {"supports": "第 5 节：AML 的准入标准——必须利用 ML 系统的统计与数据特性", "text": "there are certain types of attacks that rely on exploiting the specific statistical and data-based properties of ML systems, thus falling within the domain of AML"},
    {"supports": "第 5 节：对 misuse enablement 刻意不细分具体滥用种类，以保持可复用的抽象层", "text": "the techniques for circumventing such defenses are often common between different kinds of models and different kinds of misuse"},
    {"supports": "第 6 节：预期不断增长的部分是 GenAI 特有的新攻击", "text": "While many attack types in the PredAI taxonomy apply to GenAI (e.g., data poisoning, model poisoning, and model extraction), recent work has also introduced novel AML attacks specific to GenAI systems."},
    {"supports": "第 7 节：知识以图与叙述承载，不是可执行内容或数据文件", "text": "Figure 2 shows a taxonomy of attacks in AML for GenAI systems."},
    {"supports": "第 8 节：缓解措施按生命周期位置编号，这是框架中唯一的覆盖定位表达", "text": "The numbers in parentheses refer to the numbering in Fig. 7, which shows a map of the deployment life cycle for broad-scale query access."}
  ]
}
```
