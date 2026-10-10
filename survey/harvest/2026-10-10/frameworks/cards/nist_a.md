# nist_a：NIST AI 100-2e2025《Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations》（NIST Trustworthy and Responsible AI，2025 年 3 月）

说明：本资料只包含该文档的前半部分（第 2 章预测式 AI 结束处截断），第 3 章生成式 AI 的正文、第 4 章讨论、附录 Glossary 正文均未包含。因此凡涉及生成式 AI 条目的内容，只能依据"Predictive AI and Generative AI Taxonomy Index"（分类索引）与目录；凡资料未写的，一律标注"资料未说明"。

## 1. 要解决的问题

框架面向的读者是"负责设计、开发、部署、评估和治理 AI 系统的个人与团体"（designed primary audience）；它还通过术语表"assist non-expert readers"，并声明其目标是"inform other standards and future practice guides"，为快速演变的 AML 图景"establishing a common language"。

它要解决的问题是：ML 系统"统计性、数据驱动"的本质带来了传统软件系统之外的攻击面（训练数据被操纵、对抗性输入、通过模型交互窃取敏感信息），而这些攻击已经"demonstrated under real-world conditions"；同时不同社群之间术语存在明显差异，需要一份统一的分类与术语（taxonomy and terminology）。资料给出的分类维度是：AI 系统类型、攻击所处的 ML 生命周期阶段、攻击者目标与意图、攻击者能力与访问权限、攻击者对学习过程及之外的知识。

它明确说自己不做的事：

- 不做穷尽综述："This report is not intended to provide an exhaustive survey of all available literature on Adversarial ML"，并给出规模对比（截至 2024 年 7 月，arXiv.org 上 2021 年以来的相关文献超过 11,354 篇）。
- 不覆盖传统网络安全攻击："This report focuses on the former and considers the latter to be within the scope of traditional cybersecurity taxonomies"（前者指 AML 攻击，后者指更像传统网络安全攻击、包括针对部署平台的攻击）。
- 不覆盖非对抗性的设计与实现缺陷："these kinds of flaws are not within the scope of the literature on AML or the attacks in this report"（指导致不准确等失败、但与对抗使用无关的缺陷）。
- 不做风险容忍度建议："this report does not make recommendations on risk tolerance"。
- 不构成法律或监管要求："This document does not establish any legal standard or any other legal requirement or defense under any law, nor does it have the force or effect of law"，其指引是自愿性的（"this guidance remains voluntary"）。
- 术语与定义也不追求穷尽："the terminology and definitions are not intended to be exhaustive but rather to serve as a starting point"。

## 2. 核心对象

资料没有给出机器可读的 schema 或字段定义表；以下是资料中以索引条目、图形标注、小节结构与文字定义实际承载的对象类型与属性。凡资料未说明的，明确标注。

### 2.1 Attacker goal / violation class（攻击者目标／违规类型）

- **ID**：含义为目标的分类编号；索引中每一类都带 ID，可视为必填；取值约束为 `NISTAML.` 加两位数字，资料中出现 `NISTAML.01`、`NISTAML.02`、`NISTAML.03`、`NISTAML.04`、`NISTAML.05`。
- **name（名称）**：取值约束为五类枚举——"Availability Violations"、"Integrity Violations"、"Privacy Compromises"、"Misuse Violations"、"Supply Chain Attacks"；必填。
- **definition（定义）**：资料在 2.1.2 节给出 availability breakdown、integrity violation、privacy compromise 三类目标的文字定义；"Misuse Violations" 只出现在索引中，本资料未给出定义；"Supply Chain Attacks" 在本资料中出现在索引与"Supply chain model poisoning"小节标题中，未作为目标定义。是否必填：资料未说明。

### 2.2 Attack class（攻击类）

- **ID**：含义为攻击类的分类编号；必填（索引中每条都带 ID）；取值约束为 `NISTAML.` 加三位数字，资料中出现 011–014、015、018、021–027、031–039、051。
- **name（名称）**：标题式英文短语，例如 "Model Poisoning"、"Clean-label Poisoning"、"Data Poisoning"、"Energy-latency"、"Clean-label Backdoor"、"Evasion"、"Backdoor Poisoning"、"Targeted Poisoning"、"Black-box Evasion"、"Model Extraction"、"Reconstruction"、"Membership Inference"、"Property Inference"、"Indirect Prompt Injection"、"Prompt Injection"、"Misaligned Outputs"、"Prompt Extraction"、"Leaking information from user interactions"、"Training Data Attacks"、"Data Extraction"、"Compromising connected resources"；必填。
- **所属目标（goal membership）**：索引把攻击类嵌在某个违规类型之下；同一个攻击类可以同时属于多个目标（例：`NISTAML.013 Data Poisoning` 同时出现在 Availability 与 Integrity 下，`NISTAML.023 Backdoor Poisoning`、`NISTAML.024 Targeted Poisoning` 同理）；必填（索引中每条都有归属）。
- **所需能力（required capabilities）**：由 Figure 1／Figure 2 的 callout 连线表达，正文用文字复述（例："Backdoor attacks are the only attacks in the literature that require both training and testing data control"）；取值来自 2.3 的六种能力；是否必填：资料未说明（从图上看每条攻击类都连到能力）。
- **学习阶段（stage）**：取值为 training stage 或 deployment stage；资料按阶段组织攻击叙述（training-time attacks 与 deployment-time attacks）；是否必填：资料未说明。
- **攻击者知识（knowledge）**：取值为 white-box、black-box、gray-box；正文按攻击类分别说明适用设定；是否必填：资料未说明。
- **数据模态（modality）**：攻击类可跨模态复用，正文按模态举例；是否必填：资料未说明。
- **缓解措施（mitigations）**：以该攻击类小节内的 "Mitigations." 段落承载，不是独立编号对象；是否必填：资料未说明。
- **现实案例（real-world instance）**：部分攻击类有专节（2.2.4 "Evasion attacks in the real world"、2.3.5 "Poisoning Attacks in the Real World"）；是否必填：资料未说明。
- **文献引用（references）**：方括号数字。
- 本资料只含预测式 AI 攻击类的正文；生成式 AI 攻击类（如 `NISTAML.015`、`NISTAML.018`、`NISTAML.027`、`NISTAML.035`–`NISTAML.039`）只出现在索引中，其字段内容资料未说明。

### 2.3 Attacker capability（攻击者能力）

- **name（名称）**：取值约束为六类枚举——TRAINING DATA CONTROL、MODEL CONTROL、TESTING DATA CONTROL、LABEL LIMIT、SOURCE CODE CONTROL、QUERY ACCESS；必填。
- **definition（定义）**：每类有一句文字定义（例：TRAINING DATA CONTROL 为"通过插入或修改训练样本控制一部分训练数据"；QUERY ACCESS 为"向模型提交查询并获得预测"）。
- **ID**：资料未说明（六种能力都没有编号）。
- **取值约束（代价/强度）**：资料只在文字中说明强弱倾向（例：黑盒最实用，白盒用于最坏情况评估），没有形式化约束。

### 2.4 Attacker knowledge（攻击者知识）

- **name（名称）**：white-box attacks、black-box attacks、gray-box attacks（gray-box 是一段范围，引用 Suciu et al. 的框架来分类）；必填。
- **definition（定义）**：白盒为完全掌握训练数据、模型架构与超参数；黑盒为极少或没有知识、可能只有查询访问；灰盒为介于两者之间。
- **ID**：资料未说明。

### 2.5 Stage of learning（学习阶段）

- **name（名称）**：TRAINING STAGE 与 DEPLOYMENT STAGE；必填（预测式 AI 部分按这两个阶段展开）。
- **definition（定义）**：训练阶段学习模型，部署阶段在新样本上生成预测。
- **ID**：资料未说明。资料另有"GenAI Stages of Learning"（3.1.1）章节标题，内容未包含。

### 2.6 Data modality（数据模态）

- **name（名称）**：Image、Text、Audio、Video、Cybersecurity、Tabular data，另有 multimodal data（多模态）；必填：资料未说明。
- **约束**：资料明确"The taxonomy of attacks defined in Fig. 1 is independent of the modality of the data in specific applications"，即模态不改变分类结构。
- **ID**：资料未说明。

### 2.7 Mitigation（缓解措施）

- **name（名称）**：资料中的类别包括 training data sanitization、robust training、trigger reconstruction、model inspection and sanitization、certified defenses、adversarial training、randomized smoothing、formal verification、differential privacy（DP-SGD、DP-FTRL、DP matrix factorization）、machine unlearning、限制/检测可疑查询、poison forensics 等。
- **归属**：挂在某个攻击类之下，不单独编号。
- **ID、必填性、取值约束、成熟度字段**：资料均未说明。

### 2.8 Glossary term（术语表条目）

- **term（术语名）**：正文以 SMALL CAPS 显示（如 ADVERSARIAL EXAMPLE、TRAINING DATA CONTROL）；必填。
- **definition（定义）**：位于附录 Glossary；必填（但本资料未包含术语表正文）。
- **page number（页码）**：术语表定义末尾给出页码，用于跳回正文。
- **约束**：只有"在正文中使用但未定义或解释"的词才进入术语表。

### 2.9 Taxonomy index entry（索引条目）

- 结构为三层嵌套：AI 类型（Predictive AI Attacks Taxonomy／Generative AI Attacks Taxonomy）→ 违规类型（带 `NISTAML.0x`）→ 攻击类（带 `NISTAML.0xx`）。
- 作用：导航与交叉引用；正文各小节标题下以 `[NISTAML.xxx] [Back to Index]` 与之双向锚定。
- **必填性/取值约束**：资料未说明额外的字段规则。

### 2.10 Figure / callout box（图与提示框）

- Figure 1／Figure 2 为攻击分类图：目标为不相交的圆（disjointed circles），目标位于圆心，能力位于目标圆的外层，攻击类以 callout 连到所需能力；"Multiple attack classes that require the same capabilities to reach the same objective are shown in a single callout."
- 蓝色提示框（blue callout boxes）用于"highlight nuances and important takeaways"。
- 图表本身的可机读字段：资料未说明。

### 2.11 Benchmark（基准测试）

- 只出现在目录（"3.6. Benchmarks for AML Vulnerabilities"），本资料正文未包含；其对象类型、字段与取值范围资料未说明。

## 3. 编号与层级

- **编号格式**：`NISTAML.` 前缀加数字。两位数字用于违规／目标层，资料中为 `NISTAML.01`（Availability Violations）、`NISTAML.02`（Integrity Violations）、`NISTAML.03`（Privacy Compromises）、`NISTAML.04`（Misuse Violations）、`NISTAML.05`（Supply Chain Attacks）。三位数字用于攻击类层，资料中为 `NISTAML.011`–`NISTAML.014`、`NISTAML.015`、`NISTAML.018`、`NISTAML.021`–`NISTAML.027`、`NISTAML.031`–`NISTAML.039`、`NISTAML.051`。
- **层级**：最高层是 AI 类型（Predictive／Generative 两套独立索引），第二层是违规／目标，第三层是攻击类。资料中未出现类似"技术／子技术"的更深父子层级；攻击类之下不再编号。`NISTAML.05` 与 `NISTAML.051` 在正文中同时出现于"Supply chain model poisoning"小节标题，呈现"类别—条目"的关系。
- **编号并不严格遵循父子派生**：同一名称的攻击类在不同目标下可能拿到不同编号（"Model Poisoning" 在 Availability 下是 `NISTAML.011`，在 Integrity 下是 `NISTAML.026`，在 Supply Chain 下是 `NISTAML.051`）；但也存在跨目标复用同一编号的情况（`NISTAML.012` Clean-label Poisoning 与 `NISTAML.013` Data Poisoning 同时出现在 Availability 与 Integrity 下）。资料未说明编号的生成规则、是否稳定、是否允许复用或退役。
- **编号缺口**：索引中没有 `NISTAML.016` 与 `NISTAML.017`；资料未说明原因。
- **命名规则**：攻击类名称为英文标题式短语；同一事物的书写在不同位置不完全一致（索引写 "Energy-latency"，正文写 "Energy latency attacks"；索引写 "Reconstruction"，正文小节写 "Data Reconstruction"）。已定义的术语在正文以 SMALL CAPS 呈现并链接到 Glossary。文档还声明若干同义用法可互换使用："AI technology"、"AI system"、"AI applications" 互换；"ML model" 与 "algorithm" 互换；"system" 视上下文可指更广的组织／社会生态而非仅计算软硬件。
- **同一事物在多处出现的处理**：同一 ID 在索引中按其能服务的多个目标重复列出；正文小节标题下复用同一 ID 并附 `[Back to Index]` 回链；正文在讨论一个攻击类时会把多个 ID 并列（如 "Backdoor poisoning [NISTAML.021, NISTAML.023]"、"Model poisoning [NISTAML.011, NISTAML.026]"、"Supply chain model poisoning. [NISTAML.05] [NISTAML.051]"）。资料未说明当同一事物对应多个 ID 时哪一个为规范条目。

## 4. 对象之间的关系

资料中可识别的关系类型与方向：

1. **attack class → required capability（攻击类 → 所需能力）**。方向是"攻击需要能力"。原文："Figure 1 connects each attack class with the capabilities required to mount the attack."；例子："backdoor attacks that cause integrity violations require control of the training and testing data to insert the backdoor pattern"，以及"Clean-label backdoor attacks do not allow label control on the poisoned samples in addition to the capabilities needed for backdoor attacks."
2. **capability → objective（能力 → 目标）**。能力处在目标圆的外层，"The capabilities that an adversary must leverage to achieve their objectives are shown in the outer layer of the objective circles"。这是把攻击类接到目标上的中间维度。
3. **attack class → goal（攻击类 → 目标）**。由索引的分组表达；一个攻击类可属于多个目标。
4. **attack class → stage of learning（攻击类 → 学习阶段）**。如 poisoning 属训练阶段、evasion 属部署阶段。
5. **attack class → attacker knowledge（攻击类 → 知识假设）**。同一攻击类可分别有白盒、灰盒、黑盒版本（evasion 与 poisoning 都如此），membership inference 也有白盒与黑盒两类。
6. **attack class → mitigation（攻击类 → 缓解措施）**。这是攻防两侧的关系：**直接关联**。原文："A corresponding set of mitigations for each class of attacks is provided in the attack class sections."；索引只列攻击类，不列缓解措施；缓解措施没有独立编号，而是以小节内 "Mitigations." 段落的形式与攻击类同处一节（evasion 的 2.2.5、availability poisoning 的 Mitigations、targeted poisoning 的 Mitigations、backdoor poisoning 的 Mitigations、model poisoning 的 Mitigations、privacy 的 2.4.5）。资料中不存在"数据源／遥测点／制品"这类作为攻防中间层的独立对象类型。
7. **attack class → attack class（攻击类之间的依赖或复用）**。例："Model extraction is often not an end goal but a step toward other attacks."；membership inference "can be used as a building block for mounting data extraction attacks"；同一目的可由不同路径实现（backdoor 既可经 data poisoning、也可经 model poisoning，还可经 source code control 挂载）。
8. **mitigation → mitigation（缓解措施之间的互补）**。例：poison forensics "adds another layer of defense in an ML system"，并补充"existing mitigations that are not always resilient in the face of evolving attacks"。
9. **attack class → real-world incident（攻击类 → 真实事件）**。2.2.4 与 2.3.5 用实例支撑；资料在此区分研究演示与在野攻击。
10. **attack class → reference（攻击类 → 文献）**。方括号编号引用。
11. **index ↔ section（索引 ↔ 正文）**。小节标题标注 ID 并附 `[Back to Index]`，形成双向锚定。

**攻防两侧的关联方式总结**：攻击类与缓解措施之间是**直接同节关联**（direct），中间没有独立的制品或规则对象；而攻击类与攻击目标之间是**通过 capability 这一中间维度关联**。数据在资料中不以"数据源对象"的身份出现，只以两种身份出现：作为攻击者能力（training data control、testing data control）与作为数据模态。资料未说明是否存在可被机器解析的攻防映射。

## 5. 抽象层次的选择

- **条目粒度是"攻击类"，不是具体算法**。获得编号与索引位置的是 Evasion、Data Poisoning、Backdoor Poisoning、Model Poisoning、Membership Inference 这类类别。具体算法（FGSM、 iterative FGSM、DeepFool、Carlini-Wagner、PGD、Boundary Attack、HopSkipJumpAttack、NeuralCleanse、Activation Clustering、MNTD、LiRA 等）只在正文叙事中作为例子出现，不获得编号，也不进入索引。
- **条目描述的是目的与行为／能力组合，而非实现**。分类依据是四个维度（学习方法与阶段、攻击者目标与意图、攻击者能力、攻击者知识），条目由此定义；资料没有给条目附算法伪代码、实现步骤或参数作为条目属性。
- **准入标准**：资料自述收录对象是"the most widely studied and currently effective attacks in AML"，并按 AI 类型列出覆盖范围（PredAI 的 evasion、poisoning、privacy；GenAI 的 poisoning、direct prompting、indirect prompt injection）；同时声明该分类不是穷尽综述。
- **统一既有工作**：目标是"create a standard terminology for adversarial attacks on ML that unifies existing work"；分类灵感来源被明确标注（poisoning 分类受 Cinà et al. [91] 启发；灰盒分类引用 Suciu et al. [358]；并提到此前已有若干攻击分类框架 [42, 358]）。
- **新条目 vs 已有条目的变体**：资料**未说明**显式判定规则。可观察到的做法是：由"能力集差异"定义的变体被提升为独立条目（`NISTAML.012` Clean-label Poisoning 相对 `NISTAML.013` Data Poisoning；`NISTAML.021` Clean-label Backdoor 相对 `NISTAML.023` Backdoor Poisoning；`NISTAML.025` Black-box Evasion 相对 `NISTAML.022` Evasion），而数据模态与攻击者知识（除 black-box evasion 这一例外）不产生新条目，只作为横切维度——资料明确说 Figure 1 的分类"is independent of the modality of the data"。
- **不收录**：传统网络安全攻击、非对抗性的设计与实现缺陷、以及超出"最广泛研究且当前有效"范围的文献。

## 6. 稳定部分与易变部分

**资料希望很少变的部分**：

- 出版与版本骨架：NIST Technical Series 的标识符语法、DOI（10.6028/NIST.AI.100-2e2025）、Publication History、引用格式；文档在在线页面提供"related content, potential updates, and document history"。
- 分类维度本身：AI 系统类型、学习阶段、攻击者目标与意图、攻击者能力、攻击者知识。
- 违规类型的枚举（availability／integrity／privacy，索引另含 misuse 与 supply chain）与六种攻击者能力、三种攻击者知识、两个学习阶段这些取值集合。
- 术语机制：SMALL CAPS 标记 + Glossary 定义 + 正文回链。
- 结构与导航约定：索引、`[NISTAML.xxx] [Back to Index]` 双向锚定、图 1／图 2 的同心圆＋callout 表达法、蓝色提示框。

**资料预期不断增长的部分**：

- 攻击类条目与索引（第 2、3 章的类目，以及 3.5 Security of Agents、3.6 Benchmarks for AML Vulnerabilities 这类新增章节）。
- 缓解措施及其实验结论：资料自述许多缓解"tend to be empirical and limited in nature"、"may themselves be vulnerable to new discoveries and evolutions in attacker techniques"。
- 真实世界案例（2.2.4、2.3.5）。
- 文献基础：资料用"超过 11,354 篇 arXiv 文献（截至 2024 年 7 月）"来说明领域规模，并声明不构成穷尽综述。
- 术语表条目。

**版本管理与新增／废弃流程**：

- 资料说明它是经编辑评审委员会于 2025-03-20 批准的版本，且"the authors wish to thank all of the people and organizations who submitted comments on the draft version"，即经过草案公开评论后更新。
- 资料明确："NIST intends to update this report as new developments emerge in AML attacks and mitigations."
- **资料未说明**：新增条目的评审与准入流程细节、条目废弃／删除流程、ID 是否复用或退役、与上一版本的具体差异（本资料未包含上一版信息）、以及分类编号的稳定性承诺。

## 7. 内容与执行的分离

- **内容形式**：单一 PDF 技术报告。知识以自然语言正文承载，辅以分类图（Figure 1、Figure 2）、项目符号形式的索引、附录术语表、蓝色提示框与外部链接。资料中**没有**出现 schema、ontology、数据文件、规则语言、YAML/JSON 表示或代码；这些是否存在于其他分发形式，资料未说明。
- **解释／执行者**：人类读者。受众是设计、开发、部署、评估和治理 AI 系统的人员，非专家通过术语表与 Glossary 链接阅读。资料未说明任何可执行的解释器、规则引擎或自动化工具。
- **表达力的上限**：该形式能表达分类断言（某攻击类属于某目标、需要哪些能力、发生在哪个阶段、适用于哪种知识假设）与定性的缓解建议及其局限；无法表达可执行的检测规则、阈值、算子实现或数据流绑定。资料中对缓解方案的描述全部是叙述性的（如 "training data sanitization"、"randomized smoothing"、"Byzantine-resilient aggregation rules"），没有给出可执行形式。
- **超出表达力时怎么办**：资料的做法是（a）声明非穷尽并明确"the terminology and definitions are not intended to be exhaustive but rather to serve as a starting point"；（b）持续更新报告；（c）把细节外置——引用外部知识库（MITRE ATLAS knowledge base [248]）记载真实世界的 evasion 案例，引用外部隐私库（TensorFlow Privacy、ML Privacy Meter）提供成员推理攻击实现，并把严谨评估准则指向学术文献（[97, 375]）与既有实践指南（[69, 274]）。
- **术语与执行的关系**：术语表是"内容"与"读者解释"之间的桥，但不含可执行语义。

## 8. 覆盖与成熟度的表达

**覆盖的表达**：

- 用 "Predictive AI and Generative AI Taxonomy Index" 表达"有哪些攻击、属于哪个目标、在哪一类 AI 之下"；同一攻击在多个目标下重复出现，用来表达"一个攻击可服务多个目标"。
- 用 Figure 1／Figure 2 的同心圆与 callout 表达可达关系：目标在圆心、能力在外环、攻击类连到所需能力；共享能力且达成同一目标的多个攻击类被合并到同一个 callout。
- 用分节覆盖表达"哪一类攻击在本报告中讨论了缓解措施"（每个攻击类下都有 Mitigations 段落）。
- **没有**覆盖矩阵、覆盖率数值、"已覆盖／未覆盖"状态位或字段。资料未说明任何此类机制。

**成熟度的表达**：

- 资料**没有**定义 maturity 字段或分级体系；没有任何形如"成熟度等级"的状态字段。可观察到的替代机制有四类：
  1. 真实世界证据分节：2.2.4 "Evasion attacks in the real world"、2.3.5 "Poisoning Attacks in the Real World"，并在其中区分研究演示与在野攻击（"These are demonstrations of evasion vulnerabilities by researchers, but did not result in attacks in the wild."）。
  2. 抗攻击检验后的叙述性判断：evasion 的缓解中"three main classes have proven to be resilient and have the potential to provide mitigation"。
  3. 被攻破记录：如 Carlini and Wagner "showed how to bypass 10 methods for detecting adversarial examples"、Obfuscated Gradients "was shown to bypass several proposed defenses based on gradient masking"、Tramèr et al. "circumvented 13 existing defenses"。
  4. 未解问题标记：如"An open challenge is to test and characterize the resilience of a variety of multimodal ML models"、"Designing ML models that are robust in the face of supply-chain model poisoning vulnerabilities is a critical open problem"、"designing ML models that resist evasion while maintaining accuracy remains an open problem"。
- 术语层面用 SMALL CAPS + Glossary 标记"这是被框架采纳的术语"，可以视为术语成熟度的一种表达。
- 3.5（Security of Agents）与 3.6（Benchmarks for AML Vulnerabilities）在目录中出现，但本资料未含其内容，无法判断其成熟度表达方式。

## 9. 对我们的启发

分析：可以用"目标 × 能力 × 阶段 × 知识"四个正交维度替代"一篇论文一个条目"，作为 methods 层不随论文数量膨胀的骨架：先定义攻击类（例如"聚合投毒""通道消息注入""训练步内 LoRA 篡改"），再把论文登记为该攻击类下的实现。这一点可直接照搬到 methods 与 knowledge_base 两层。

分析：`NISTAML.0x`／`NISTAML.0xx` 的两级编号加索引，使攻击类成为可被正文、图、引用反复引用的稳定标识符。我们应在 knowledge_base 层建立同样的 registry，让 11 个运行时暴露位置、算子、方法、评估记录都用统一 ID 互相引用，避免以论文标题为主键。

分析：资料中同一攻击 ID 在多个目标下重复出现，表达"一个攻击可以服务多个目标"。对应到我们：一个防御方法可能同时防护多个攻击类、作用在多个运行位置，methods 层应当支持多对多挂载，而不是一棵以论文为节点的树。

分析：资料中攻击类与缓解措施是"同节直接陈述"的关系，缓解措施没有独立编号，也没有数据源或制品作为中间对象。这一点不能照搬：我们的防御是数值算法，必须绑定具体张量、消息与训练步位置，因此需要自己引入一层"运行位置／数据视图"对象，作为 methods 与 runtime 之间的桥；NIST 的对象清单里没有这一层可借用。

分析：攻击者能力清单（TRAINING DATA CONTROL、MODEL CONTROL、TESTING DATA CONTROL、LABEL LIMIT、SOURCE CODE CONTROL、QUERY ACCESS）本质是"攻击者能碰哪些东西"，与我们的 11 个暴露位置是同一种语言。可以把 runtime 层的暴露位置直接对齐到这套能力词汇，用它生成"方法 × 运行位置"的覆盖矩阵。这是对 runtime 与 evaluation 两层最直接的迁移。

分析：NIST 的能力是定性的"能不能控制"，不包含"控制多少"。联邦 LoRA 场景下投毒客户端比例、裁剪阈值、采样率决定威胁是否成立，所以我们的能力标签必须扩展为带参数的威胁模型，否则覆盖矩阵只能表达"有／无"，无法表达"在什么条件下有效"。这一条属于 adapted 而非直接照搬。

分析：资料把具体算法留在正文叙事里，不给编号、不进索引。我们的 methods 层应照此办理：条目是"防御类"，论文、超参、实现是挂在其下的实现体；这样新论文只增加实现记录，不增加条目，正好回应"库只能一篇篇追"的问题。

分析：资料把"能力集不同"的变体提升为独立条目（Clean-label Poisoning `NISTAML.012`、Black-box Evasion `NISTAML.025`），而把模态、知识等作为横切维度。我们可以照此确定"新条目 vs 已有条目的参数"的判定规则：当且仅当需要额外的数据视图或额外的运行位置时，才新增条目。这对 methods 与 knowledge_base 都适用。

分析：资料用"正文 SMALL CAPS + 附录 Glossary"管理词汇，保证同一概念在多处出现时含义一致。我们三层库最缺的正是这一点：样本、梯度、训练步内 LoRA、客户端上传、聚合结果、下发内容、通道消息这 11 个位置目前只有工程命名；应把它们升级为受控术语表，作为 knowledge_base 的一等对象。

分析：资料的成熟度不靠分级字段，而靠"是否在真实世界出现""是否被更强攻击攻破""是否被列为 open problem"这类叙述性证据。我们可以把它字段化：为每个方法记录评估证据等级（仅论文报告／有自适应攻击测试／被独立复现／已被攻破），落在 evaluation 与 records 两层。这是对我们最有用的一处改造——因为我们的方法会持续被新攻击挑战，必须让"失效记录"成为一等数据。

分析：资料明确写出自己"不做什么"（不做穷尽综述、不覆盖传统网络安全攻击、不覆盖非对抗性缺陷、不建议风险容忍度、不构成法律标准）。我们的库也应在 knowledge_base 中放一份同等的边界声明，避免使用者把"登记了某个攻击类"误读为"提供了安全保证"。

分析：资料承认多数缓解是经验性的、缺乏信息论保证，并且历史上反复被后续攻击打破。这提示 operators 与 methods 之间需要一份"失效边界"契约：算子声明适用假设与数值条件，方法声明已知被绕过的场景。否则我们的库会重复"发布即过时"的循环。

分析：资料把"真实世界案例"与"研究演示"分开叙述并明确区分。我们的 evaluation 层可以照此区分"论文报告的攻击成功率"与"实际部署观测"，避免把论文数字直接当作生产指标。

分析：资料没有把"检测／遥测数据源"作为一级对象，这是它作为风险沟通文件的取舍；而我们的库要做运行时干预，必须把 11 个暴露位置提升为一级对象。这一条不能照搬它的对象清单，但可以照搬它"用一张图把可达关系画清楚"的表达方式（目标—能力—攻击类的同心圆结构可以改画成 运行位置—数据视图—算子—方法）。

## 10. 框架自己承认的局限

- 不是穷尽综述，且领域规模巨大（截至 2024 年 7 月，arXiv.org 上 2021 年以来相关文献超过 11,354 篇）；术语与定义只作为起点而非穷尽。
- 许多缓解措施是经验性的、缺乏信息论安全证明，并且可能被新的攻击技术攻破；文献中已出现限制常用缓解有效性的信息论不可能性结果。
- 该领域"has a history of publishing defenses evaluated under relatively weak adversarial models that are subsequently broken by more powerful attacks"；缓解措施必须针对强自适应攻击评估。
- 检测对抗样本与构造防御同样困难；已有多项防御被系统性绕过（10 种检测方法被绕过、13 种防御被规避、gradient masking 类防御被 Obfuscated Gradients 攻破）。
- 稳健性与准确性、稳健性与公平性之间存在内在权衡；对抗训练与随机平滑会降低准确率，形式化验证受可扩展性、计算成本与支持的代数运算类型限制。
- 定向投毒"notoriously challenging to defend against"，子群体投毒存在不可能性结果。
- 后门缓解大多针对使用固定触发模式的卷积神经网络视觉分类器；数据清洗类方法对干净标签后门与恶意软件分类无效；语义与功能性触发会对触发重建与模型检查类方法构成挑战；基于元分类器的 Trojan 检测需要训练数千个 shadow model，计算复杂度高。
- 投毒取证（poison forensics）被定位为补充手段，因为既有缓解"not always resilient in the face of evolving attacks"。
- 模型抽取：精确抽取被证明不可能，抽取功能等价模型也是 NP-hard；限制查询、检测可疑查询等缓解"can be circumvented by motivated and well-resourced attackers and should be used with caution"。
- 差分隐私：不为模型抽取提供保证；对属性推断有负面结果；隐私参数选择困难，理论分析常为最坏情况且不紧，实践中不得不使用较大的隐私参数（如 2020 年美国人口普查使用 ε = 19.61），实际获得的隐私难以估计。
- 供应链模型投毒：缓解困难，程序验证技术受 ML 算法内在随机性与非确定性行为阻碍；"Designing ML models that are robust in the face of supply-chain model poisoning vulnerabilities is a critical open problem."
- 多模态模型的韧性测试与刻画仍是开放挑战。
- 将 ML 用于异常检测时，需要极低的漏报率与误报率，而这些要求叠加会使模型更易受对抗攻击。
- 资料对真实世界案例的表述谨慎，明确有些只是研究者演示、并未在野发生。
- 资料也承认分类本身的边界：传统网络安全攻击、非对抗性的设计与实现缺陷不在范围之内；不提供风险容忍度建议，也不具备法律效力。

## 11. 原文依据

1. "The taxonomy is arranged in a conceptual hierarchy that includes key types of ML methods, life cycle stages of attack, and attacker goals, objectives, capabilities, and knowledge."（27 词）——支撑第 2 节"核心对象类型与层级"的论断：对象由 ML 方法类型、攻击生命周期阶段、攻击者目标／意图／能力／知识构成。
2. "These attacks are classified according to the following dimensions: 1) learning method and stage of the learning process when the attack is mounted, 2) attacker goals and objectives, 3) attacker capabilities, and 4) attacker knowledge of the learning process."（39 词）——支撑第 2 节与第 5 节的论断：条目由四个正交维度定义，而不是由具体算法定义。
3. "An adversary might leverage six types of capabilities to achieve their objectives, as shown in the outer layer of the objective circles in Fig. 1"（25 词）——支撑第 2 节"攻击者能力是独立对象类型且取值为六类"与第 4 节"能力位于目标外环"的论断。
4. "Figure 1 connects each attack class with the capabilities required to mount the attack."（14 词）——支撑第 4 节"攻击类与所需能力之间存在直接连线关系"的论断。
5. "A corresponding set of mitigations for each class of attacks is provided in the attack class sections."（17 词）——支撑第 4 节与第 7 节的论断：攻防两侧是直接同节关联，缓解措施以正文段落而非独立编号对象存在。
6. "A taxonomy of the most widely studied and currently effective attacks in AML, including:"（14 词）——支撑第 5 节"收录准入标准是最广泛研究且当前有效的攻击"的论断。
7. "This report is not intended to provide an exhaustive survey of all available literature on Adversarial ML, which includes more than 11,354 references on arXiv.org since 2021 as of July 2024."（31 词）——支撑第 6 节"文献与条目是预期持续增长的部分"与第 7 节"内容表达力上限／非穷尽声明"的论断。
8. "NIST intends to update this report as new developments emerge in AML attacks and mitigations."（15 词）——支撑第 6 节"版本管理与持续更新机制"的论断。
9. "This document provides an Index of attack types to easily navigate and reference attacks and corresponding mitigations."（17 词）——支撑第 8 节"用索引表达覆盖与导航"的论断。
10. "From the wide range of proposed defenses against adversarial evasion attacks, three main classes have proven to be resilient and have the potential to provide mitigation against evasion attacks"（29 词）——支撑第 8 节"成熟度以叙述性证据（经检验仍有效）而非分级字段表达"的论断。

补充说明：第 3 节关于编号格式的论断依据的是索引与正文中的短片段原文串（如 `NISTAML.01`、`NISTAML.011`、`NISTAML.026`、`[NISTAML.021, NISTAML.023]`），这些片段均短于 12 词，不满足引句选取规则，故未在第 11 节另列长引句。

```json
{
  "key": "nist_a",
  "framework": "NIST AI 100-2e2025, Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations (NIST Trustworthy and Responsible AI, March 2025)",
  "object_types": [
    {
      "name": "Attacker goal / violation class (attacker objective)",
      "role": "other",
      "fields": ["ID (NISTAML.NN)", "name (Availability Violations / Integrity Violations / Privacy Compromises / Misuse Violations / Supply Chain Attacks)", "definition (仅在 2.1.2 给出 availability breakdown、integrity violation、privacy compromise 三类定义；misuse 与 supply chain 未定义)"]
    },
    {
      "name": "Attack class",
      "role": "attack",
      "fields": ["ID (NISTAML.NNN)", "name", "goal membership (可属于多个目标)", "required capabilities (取自六种能力)", "stage of learning (training / deployment)", "attacker knowledge (white-box / black-box / gray-box)", "data modality (横切)", "mitigations (同节段落，无独立编号)", "real-world instances", "references"]
    },
    {
      "name": "Attacker capability",
      "role": "attack",
      "fields": ["name (TRAINING DATA CONTROL / MODEL CONTROL / TESTING DATA CONTROL / LABEL LIMIT / SOURCE CODE CONTROL / QUERY ACCESS)", "definition (无 ID；资料未说明必填性与取值约束)"]
    },
    {
      "name": "Attacker knowledge",
      "role": "other",
      "fields": ["name (white-box / black-box / gray-box)", "definition (无 ID；资料未说明必填性)"]
    },
    {
      "name": "Stage of learning",
      "role": "other",
      "fields": ["name (TRAINING STAGE / DEPLOYMENT STAGE)", "definition (无 ID；资料未说明必填性)"]
    },
    {
      "name": "Data modality",
      "role": "other",
      "fields": ["name (Image / Text / Audio / Video / Cybersecurity / Tabular data / multimodal)", "constraint: Figure 1 的分类独立于模态 (无 ID)"]
    },
    {
      "name": "Mitigation",
      "role": "defense",
      "fields": ["name (training data sanitization, robust training, trigger reconstruction, model inspection and sanitization, certified defenses, adversarial training, randomized smoothing, formal verification, differential privacy, machine unlearning, poison forensics 等)", "attachment: 归属于某个 attack class 的小节，无独立 ID，无必填与取值约束字段"]
    },
    {
      "name": "Glossary term",
      "role": "other",
      "fields": ["term (正文以 SMALL CAPS 显示)", "definition (Appendix: Glossary)", "page number (用于跳回正文)"]
    },
    {
      "name": "Taxonomy index entry",
      "role": "relation",
      "fields": ["AI type (Predictive / Generative)", "violation category with ID (NISTAML.0x)", "attack class with ID (NISTAML.0xx)", "同一攻击类可在多个目标下重复列出"]
    },
    {
      "name": "Figure / callout box",
      "role": "artifact",
      "fields": ["objective circle (圆心为目标)", "capability outer layer", "attack class callout (共享能力且同目标的多个攻击类合并为一个 callout)", "blue callout box (nuances and important takeaways)"]
    },
    {
      "name": "Benchmark",
      "role": "test",
      "fields": ["仅目录列出 3.6 Benchmarks for AML Vulnerabilities；本资料未含内容，字段与取值资料未说明"]
    }
  ],
  "id_scheme": "NISTAML. 前缀加数字：两位数字为违规／目标层 (NISTAML.01 Availability Violations, .02 Integrity Violations, .03 Privacy Compromises, .04 Misuse Violations, .05 Supply Chain Attacks)，三位数字为攻击类层 (NISTAML.011–.014, .015, .018, .021–.027, .031–.039, .051)。同一攻击类在不同目标下可获不同编号 (Model Poisoning 为 .011 / .026 / .051)，也可跨目标复用同一编号 (.012, .013)；索引中缺 .016 与 .017；资料未说明编号生成、稳定性、复用或退役规则。",
  "attack_defense_link": "direct",
  "link_detail": "缓解措施不是独立编号对象，而是直接写在对应 attack class 的小节内 (A corresponding set of mitigations for each class of attacks is provided in the attack class sections)；索引只列攻击类，不列缓解措施。攻击类与攻击目标之间则通过 capability 这一中间维度关联 (能力位于目标圆的外环，攻击类 callout 连到所需能力)。资料中没有 data source / telemetry / artifact 这类作为攻防中间层的对象类型；数据只以攻击者能力 (training data control, testing data control) 和数据模态两种身份出现。",
  "abstraction_level": "攻击类 (attack class) 层级：条目由攻击者目标、所需能力、学习阶段与攻击者知识定义，描述目的与行为／能力组合；具体算法 (FGSM, PGD, Carlini-Wagner, NeuralCleanse, LiRA 等) 只在正文叙事中作为例子，不进索引、不获编号。准入标准为 the most widely studied and currently effective attacks；由能力集差异定义的变体被提升为独立条目 (Clean-label Poisoning .012, Clean-label Backdoor .021, Black-box Evasion .025)，模态与知识作为横切维度。资料未说明新条目 vs 变体的显式判定规则。",
  "stable_parts": ["分类维度 (AI 类型、学习阶段、攻击者目标、能力、知识)", "违规类型与攻击者能力的取值枚举", "NISTAML.0x / 0xx 两级编号框架", "术语机制 (SMALL CAPS + Glossary + 回链)", "索引与 [Back to Index] 双向锚定", "Figure 1/2 的同心圆加 callout 表达法", "NIST Technical Series 出版体系、DOI、Publication History、引用格式"],
  "growing_parts": ["攻击类条目与索引", "缓解措施及其实验结论", "真实世界案例 (2.2.4, 2.3.5)", "术语表条目", "参考文献 (11,354+ 篇 arXiv 文献)", "新增章节如 Security of Agents (3.5) 与 Benchmarks for AML Vulnerabilities (3.6)"],
  "content_format": "单一 PDF 技术报告：自然语言正文 + 分类图 (Figure 1/2) + 项目符号索引 + 附录 Glossary + 蓝色提示框 + 外链。未出现 schema、ontology、数据文件、规则语言或代码；是否存在机器可读分发形式资料未说明。",
  "execution_engine": "无。由人类读者解释使用 (设计、开发、部署、评估、治理 AI 系统的人员；非专家借助术语表)。资料未说明任何解释器、规则引擎或自动化工具。",
  "coverage_expression": "Predictive AI and Generative AI Taxonomy Index：AI 类型 → 违规／目标 (带 NISTAML.0x) → 攻击类 (带 NISTAML.0xx) 的嵌套列表，同一攻击类在多目标下重复出现；Figure 1/2 用目标圆环、能力外环与 attack callout 表达可达关系，共享能力且同目标的多个攻击类合并到一个 callout。没有覆盖矩阵、覆盖率数值或已覆盖／未覆盖状态字段。",
  "maturity_expression": "无 maturity 字段或分级。以叙述性证据表达：真实世界出现情况专节 (2.2.4, 2.3.5) 并区分研究演示与在野攻击；经检验仍有效的缓解类别 (evasion 的 three main classes have proven to be resilient)；被后续更强攻击攻破的记录 (10 种检测方法、13 种防御、gradient masking)；open problem / challenge 标记；术语以 SMALL CAPS + Glossary 标记为已被框架采纳。",
  "lessons": [
    {"idea": "用目标 × 能力 × 阶段 × 知识四个正交维度替代一篇论文一个条目，先定义攻击类，再把论文登记为其下的实现", "applies_to": "methods", "transfer": "direct", "why": "资料以四个维度分类攻击类，而非以算法或文献为条目；这套骨架不随论文数量膨胀"},
    {"idea": "两级稳定 ID 加索引，使攻击类可被正文、图、引用反复引用", "applies_to": "knowledge_base", "transfer": "direct", "why": "NISTAML.0x / 0xx 让同一对象在多处出现时保持同一标识；我们的 11 个运行位置、算子、方法、评估记录应统一编号并以 ID 互引"},
    {"idea": "允许一个攻击对象同时属于多个目标，做多对多挂载而非树形结构", "applies_to": "methods", "transfer": "direct", "why": "索引中 Data Poisoning、Backdoor Poisoning、Targeted Poisoning 等同时列在 Availability 与 Integrity 下"},
    {"idea": "引入运行位置／数据视图作为 methods 与 runtime 之间的中间对象层", "applies_to": "runtime", "transfer": "adapted", "why": "NIST 的缓解措施与攻击类同节直接陈述、无中间对象，但我们的防御是数值算法，必须绑定具体张量与消息；这一层需要自建而非照搬"},
    {"idea": "把攻击者能力清单对齐到运行时暴露位置，生成方法 × 运行位置的覆盖矩阵", "applies_to": "evaluation", "transfer": "direct", "why": "TRAINING DATA CONTROL、MODEL CONTROL、TESTING DATA CONTROL、LABEL LIMIT、SOURCE CODE CONTROL、QUERY ACCESS 描述的正是攻击者能触及的对象，与 11 个暴露位置同构"},
    {"idea": "把定性能力扩展为带参数的威胁模型（投毒比例、裁剪阈值、采样率）", "applies_to": "methods", "transfer": "adapted", "why": "资料的能力只表达能不能控制、以及偶发的比例描述（如需大量被控客户端），不含参数化条件；联邦 LoRA 下条件决定威胁是否成立"},
    {"idea": "把论文与超参降为防御类条目下的实现记录，不给论文编号", "applies_to": "methods", "transfer": "direct", "why": "资料把 FGSM、PGD、NeuralCleanse 等留在叙事中，不进入索引、不获编号"},
    {"idea": "以是否需要额外数据视图或额外运行位置作为新条目 vs 已有条目参数的判据", "applies_to": "knowledge_base", "transfer": "adapted", "why": "资料把能力集不同的变体提为独立条目 (Clean-label Poisoning .012、Black-box Evasion .025)，但未写出显式判定规则，需我们补规则"},
    {"idea": "建立受控术语表，把 11 个暴露位置升级为定义一致的术语对象", "applies_to": "knowledge_base", "transfer": "direct", "why": "资料用正文 SMALL CAPS 加 Appendix Glossary 保证同一概念在多处出现时含义一致；我们的位置命名目前只是工程命名"},
    {"idea": "把成熟度字段化：记录方法的评估证据等级与已被攻破记录", "applies_to": "evaluation", "transfer": "adapted", "why": "资料的成熟度靠叙述（真实世界出现、被更强攻击攻破、open problem）而非字段；我们要自动化，必须把它变成 records 与 evaluation 的可查询字段"},
    {"idea": "在知识库中放一份等价的边界声明：不覆盖什么、不构成什么保证", "applies_to": "knowledge_base", "transfer": "direct", "why": "资料明确不做穷尽综述、不覆盖传统网络安全攻击与非对抗性缺陷、不建议风险容忍度、不具法律效力"},
    {"idea": "为算子与方法定义失效边界契约：算子声明适用假设，方法声明已知被绕过的条件", "applies_to": "operators", "transfer": "adapted", "why": "资料承认多数缓解是经验性的、无信息论保证，且历史上被后续攻击反复打破"},
    {"idea": "区分论文报告指标与实际部署观测，分别记录", "applies_to": "records", "transfer": "direct", "why": "资料在真实世界案例中明确区分研究者演示与在野攻击（did not result in attacks in the wild）"},
    {"idea": "不要照搬 NIST 的对象清单：它没有把检测／遥测数据源作为一级对象", "applies_to": "runtime", "transfer": "not_transferable", "why": "该文档面向风险沟通而非运行时干预，其对象是攻击类与能力；我们的库要落地运行时防御，必须把 11 个暴露位置提升为一级对象"}
  ],
  "limits": [
    "不是穷尽综述：the terminology and definitions are not intended to be exhaustive；截至 2024 年 7 月 arXiv.org 上 2021 年以来相关文献超过 11,354 篇",
    "多数缓解措施是经验性的、缺乏信息论安全保证，且可能被新的攻击技术攻破；文献中已出现限制常用缓解有效性的不可能性结果",
    "该领域有发布弱对抗模型下评估、随后被更强攻击打破的防御的历史",
    "检测对抗样本与构造防御同样困难；已有 10 种检测方法与 13 种防御被系统性绕过，gradient masking 类防御被 Obfuscated Gradients 攻破",
    "稳健性与准确性、稳健性与公平性之间存在内在权衡；对抗训练与随机平滑降低准确率，形式化验证受可扩展性、计算成本与支持运算类型限制",
    "定向投毒 notoriously challenging to defend against；子群体投毒存在不可能性结果",
    "后门缓解大多针对使用固定触发模式的卷积神经网络视觉分类器；对干净标签后门、语义与功能性触发效果有限；元分类器检测需训练数千个 shadow model",
    "模型抽取的精确抽取被证明不可能、功能等价抽取为 NP-hard；限制与检测查询等缓解可被有动机且资源充足的攻击者绕过",
    "差分隐私不防模型抽取、对属性推断有负面结果；隐私参数选择困难，理论分析常为最坏情况且不紧，实践中使用较大隐私参数",
    "供应链模型投毒：设计稳健模型是 critical open problem；ML 算法的内在随机性与非确定性使程序验证困难",
    "多模态模型韧性的测试与刻画仍是开放挑战",
    "将 ML 用于异常检测需要极低漏报率与误报率，这些要求叠加会提高对抗脆弱性",
    "资料对真实世界证据表述谨慎，明确部分只是研究者演示、并未在野发生",
    "分类范围有明确边界：传统网络安全攻击与非对抗性设计与实现缺陷不在范围内；不提供风险容忍度建议；不具法律或监管效力"
  ],
  "quotes": [
    {"supports": "第 2 节：核心对象类型与概念层级（ML 方法类型、攻击生命周期阶段、攻击者目标／意图／能力／知识）", "text": "The taxonomy is arranged in a conceptual hierarchy that includes key types of ML methods, life cycle stages of attack, and attacker goals, objectives, capabilities, and knowledge."},
    {"supports": "第 2 节与第 5 节：条目由四个正交维度定义（学习方法与阶段、目标与意图、能力、知识），而非由具体算法定义", "text": "These attacks are classified according to the following dimensions: 1) learning method and stage of the learning process when the attack is mounted, 2) attacker goals and objectives, 3) attacker capabilities, and 4) attacker knowledge of the learning process."},
    {"supports": "第 2 节：攻击者能力是独立对象类型且取值为六类；第 4 节：能力位于目标圆外环，是连接攻击类与目标的中间维度", "text": "An adversary might leverage six types of capabilities to achieve their objectives, as shown in the outer layer of the objective circles in Fig. 1"},
    {"supports": "第 4 节：攻击类与所需能力之间存在直接连线关系", "text": "Figure 1 connects each attack class with the capabilities required to mount the attack."},
    {"supports": "第 4 节与第 7 节：攻防两侧为直接同节关联，缓解措施以攻击类小节内的正文段落存在，没有独立编号或中间对象", "text": "A corresponding set of mitigations for each class of attacks is provided in the attack class sections."},
    {"supports": "第 5 节：收录准入标准是最广泛研究且当前有效的攻击，且按 AI 类型列出覆盖范围", "text": "A taxonomy of the most widely studied and currently effective attacks in AML, including:"},
    {"supports": "第 6 节：文献与条目属于预期持续增长的部分；第 7 节：内容的表达力上限以非穷尽声明处理", "text": "This report is not intended to provide an exhaustive survey of all available literature on Adversarial ML, which includes more than 11,354 references on arXiv.org since 2021 as of July 2024."},
    {"supports": "第 6 节：存在明确的持续更新与版本管理意图", "text": "NIST intends to update this report as new developments emerge in AML attacks and mitigations."},
    {"supports": "第 8 节：用 attack-type index 表达覆盖范围与导航，并对应到缓解措施", "text": "This document provides an Index of attack types to easily navigate and reference attacks and corresponding mitigations."},
    {"supports": "第 8 节：成熟度以经检验仍有效的叙述性证据表达，而不是分级字段", "text": "From the wide range of proposed defenses against adversarial evasion attacks, three main classes have proven to be resilient and have the potential to provide mitigation against evasion attacks"}
  ]
}
```
