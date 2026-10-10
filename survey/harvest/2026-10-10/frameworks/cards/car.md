# car：MITRE Cyber Analytics Repository（CAR）

资料版本：资料未给出仓库版本号或发布日期。可确认的时间信息只有示例条目的 `submission_date: 2013/04/11` 与条目编号 `CAR-2013-04-002`。资料由三部分组成：CAR README、CAR Data Model、分析条目示例 CAR-2013-04-002。

## 1. 要解决的问题

CAR（MITRE Cyber Analytics Repository）是 MITRE 基于 MITRE ATT&CK® 对手模型开发的一个分析（analytic）知识库，面向整个网络防御者社区共享，目标是提供一组"经过验证且解释充分"的分析条目，尤其要讲清楚其工作原理（operating theory）与理由（rationale）。

它要解决的具体问题是：ATT&CK 只描述威胁如何被表述，而"用哪些方式检测它们"有很多种可能，二者必须分开。CAR 因此承担"检测方式"这一侧，把针对 ATT&CK 对手行为的分析条目集中起来，并附带可直接指向具体工具（例如 Splunk、EQL）的实现。README 给出的开发方法论是四个活动：从 ATT&CK 对手模型中识别并排序对手行为；识别检测该行为所需的数据；识别或创建采集所需数据的传感器（sensor）；真正创建分析条目来检测所识别的行为。

它明确说自己不做什么：

- 不把分析条目放进 ATT&CK，ATT&CK 与 CAR 是刻意分开的两个项目。
- 不规定组织应当如何防御：ATT&CK 中的防御者内容不应过度规定（overly prescriptive）防御方式，采用者要自行判断哪种方式适合自己的环境与所面对的威胁。
- 不宣称自己是终极方案：CAR 是很多组织的良好起点，也是开放分析协作的平台，但不是防御 ATT&CK 所述威胁的"be-all/end-all"。
- 主站不集成"以特定产品源代码形式存在、覆盖面过宽"的实现，这类内容改放到 implementations 库中。

## 2. 核心对象

资料是节选，因此下文对"是否必填"绝大多数只能写"资料未说明"；这是资料本身的缺口，不是遗漏。

### 2.1 Analytic（分析条目，防御/检测侧的核心对象）

README 说"CAR 中存储的分析条目包含以下信息"：一个解释该分析背后想法的 hypothesis；其设计运行的信息域或主域（例如 host、network、process、external）；它所检测的 ATT&CK Techniques 与 Tactics 的引用；Glossary；它可能如何被实现的 pseudocode 描述；一个可运行以触发该分析条目的 unit test。

示例条目 CAR-2013-04-002 实际出现的字段：

- `title`：条目标题（示例为 Quick execution of a series of suspicious commands）。含义：人类可读名称。是否必填：资料未说明。取值约束：资料未说明。
- `submission_date`：提交日期，示例为 `2013/04/11`。是否必填：资料未说明。取值约束：示例为 `YYYY/MM/DD` 形式。
- `information_domain`：信息域，示例为 `'Analytic, Host'`。README 说明其取值示例为 host、network、process、external。是否必填：资料未说明。
- `platforms`：适用平台，示例为 Windows、Linux、macOS 的列表。是否必填：资料未说明。
- `subtypes`：子类型，示例为 `Process`。是否必填：资料未说明。
- `analytic_types`：分析类型，示例为 `TTP`。是否必填：资料未说明。取值约束：资料只给出 `TTP` 一个示例值。
- `contributors`：贡献者，示例为 `MITRE`。是否必填：资料未说明。
- `id`：条目标识，示例为 `CAR-2013-04-002`。是否必填：资料未说明。
- `description`：描述，示例中包含"Certain commands are frequently used by malicious actors…"的说明、一份命令清单，以及一个 `### Output Description` 小节（说明输出为主机、执行时间与所执行的命令）。README 所说的 hypothesis 在示例中没有对应的独立字段，它与 description 的分工资料未说明。
- `coverage`：覆盖声明列表，元素含 `technique`、`tactics`、`subtechniques`、`coverage` 四项（详见第 4 节与第 8 节）。是否必填：资料未说明。
- `implementations`：实现列表，元素含 `type`、`code`、`description`、`data_model`。示例中出现 4 个实现，`type` 分别为 pseudocode、Sigma、DNIF、LogPoint；DNIF 条目带 `data_model: Sysmon native`，LogPoint 条目带 `data_model: LogPoint native`。是否必填各子字段：资料未说明。
- `data_model_references`：数据模型引用列表，示例为 `process/create/hostname`、`process/create/ppid`、`process/create/exe` 三条三段式路径。是否必填：资料未说明。
- `unit_tests`：单元测试列表，元素含 `configurations`（示例为 `Windows 7`）、`description`、`commands`（示例为 4 条命令）。是否必填：资料未说明。
- `d3fend_mappings`：D3FEND 映射列表，元素含 `iri`（`d3f:ProcessLineageAnalysis`）、`id`（`D3-PLA`）、`label`（`Process Lineage Analysis`）。是否必填：资料未说明。
- README 还列出 Glossary 属于分析条目内容，但示例条目里没有对应的顶层字段，二者的关系资料未说明。

### 2.2 ATT&CK 侧被引用的对象（攻击侧）

资料没有给出 ATT&CK 对象自身的字段定义，只出现了 CAR 引用它们时使用的字段：

- `technique`：技术编号，示例 `T1087`。含义：该分析条目所检测的 ATT&CK 技术。
- `tactics`：战术编号列表，示例 `TA0007`。
- `subtechniques`：子技术编号列表，示例 `T1087.001`、`T1087.002`（示例中并非每条 coverage 都有 subtechniques）。
- `coverage`：该分析条目对该技术的覆盖级别，示例出现 `Low` 与 `Moderate`。

是否必填与完整取值约束：资料未说明。

### 2.3 数据模型侧的对象（telemetry/数据侧）

- Data Model Object（数据模型对象）：被监控的对象，类似计算机科学中的 object，是"主机、文件、连接"等数据真正表示的东西，是数据模型词汇表里的名词。资料给出 13 个对象：authentication、driver、email、file、flow、http、module、process、registry、service、socket、thread、user_session。每个对象的字段由 Actions 与 Fields 两个维度定义（见下）。是否必填：资料未说明。
- Action（动作）：对象上发生的状态变化或事件，例如对象的创建、销毁或修改，是描述对象能做什么、以及对象会遭遇什么的动词。资料同时说明：存在传感器并不监控对象上的动作，而只是扫描并检查对象是否存在的情况。每个 action 在覆盖矩阵（二维表）中表示，action 位于 y 轴。是否必填：资料未说明。
- Field（字段）：对象的可观测属性，可能包含标志、标识符、数据元素，甚至对其他对象的引用；在词汇表里相当于形容词。传感器在某个对象的上下文中监控字段，并以某种结构化数据形式输出。在覆盖矩阵中 field 位于 x 轴。是否必填：资料未说明。
- Sensor（传感器）：采集数据的组件，其输出必须被映射进数据模型；README 的贡献流程中有专门的"adding a new sensor mapping" issue 模板。传感器自身的字段定义资料未说明。
- (object, action, field) 三元组：不是一个独立对象，而是把三者配对后像坐标一样的定位方式，用于描述对象的哪些属性与状态变化可以被传感器捕获。

### 2.4 制品与库

- Implementation（实现，artifact）：分析条目内部的一种制品，`type` 取值示例为 pseudocode、Sigma、DNIF、LogPoint；README 另行提到 Splunk、EQL 等"分析条目直接针对的具体工具"。是否必填与取值全集：资料未说明。
- Implementation Library（实现库，artifact）：以特定产品源代码形式存在的分析集合。资料明确当前唯一的库是 BZAR，即一组主要分析 SMB 与 RPC 流量的 Zeek（原 Bro）脚本。其条目字段资料未说明。

### 2.5 测试与映射

- Unit Test（单元测试，test）：条目自带的、可运行以触发该分析条目的测试，示例字段为 configurations、description、commands。
- Coverage Entry（覆盖声明，relation）：`technique` + `tactics` + `subtechniques` + `coverage` 的组合，是分析条目与 ATT&CK 之间的一条关系记录。
- Data Model Reference（数据模型引用，relation）：以 `object/action/field` 三段路径表达的数据依赖坐标，示例 `process/create/exe`。
- D3FEND Mapping（relation/defense）：以 `iri`、`id`、`label` 指向 D3FEND 防御技术的映射记录。

### 2.6 其他

- Glossary（术语表）：README 列为分析条目的内容之一，并作为独立文档存在；其条目字段资料未说明。
- OSSEM Common Data Model：README 说明 CAR 已与 OSSEM 合作，后续采用其公共数据模型；该模型的字段定义资料未给出。
- Issue 模板：README 提到三类模板——adding an analytic、adding to the data model、adding a new sensor mapping。这间接说明"数据模型新增"与"传感器映射新增"在 CAR 中是被单独管理的对象类别。

## 3. 编号与层级

- 分析条目编号：示例为 `CAR-2013-04-002`。从形式上看是 `CAR-` + 四位年 + 两位月 + 三位序号，且年、月与 `submission_date: 2013/04/11` 的年月一致；但资料没有说明编号规则，也没有说明第三段 `002` 与日期 `11` 的关系。命名规则：资料未说明。
- ATT&CK 编号：tactic 形如 `TA0007`；technique 形如 `T1087`；sub-technique 形如 `T1087.001`，是 technique 编号加 `.` 加三位序号，构成 technique → sub-technique 的两级层级。tactic 与 technique 是并列的编号空间。
- D3FEND 编号：示例同时给出 `id: D3-PLA` 与 `iri: d3f:ProcessLineageAnalysis`，即"短 ID + IRI"两种写法。
- 数据模型坐标：`object/action/field` 三段斜杠路径，例如 `process/create/hostname`。数据模型本身是 13 个 object，每个 object 下挂 actions 与 fields 两个维度。
- 同一事物在多处出现的处理方式：
  - ATT&CK 技术不复制进 CAR，只以编号引用；CAR 与 ATT&CK 是两个项目。
  - 同一字段名会出现在多个 object 下（例如 `hostname` 出现在 authentication、driver、file、flow、http、module、process、registry、service、thread、user_session 等对象下；`pid`、`image_path`、`uid`、`fqdn` 等也重复出现），因此字段必须与 object、action 组成三元组才有确定含义。
  - 同一分析思路的多种落地形式放在同一条目的 `implementations` 数组里，而不是拆成多个条目（示例一条条目有 pseudocode、Sigma、DNIF、LogPoint 四个实现）。
  - 覆盖情况会在条目内（coverage 数组）、ATT&CK Navigator layer、数据模型覆盖汇总与覆盖矩阵中多次出现，属于同一结构化内容的不同视图。
  - 条目之间的重名、冲突或去重规则：资料未说明。

## 4. 对象之间的关系

方向与关系类型如下（箭头表示"前者引用/指向后者"）：

1. Analytic → ATT&CK technique/tactic/sub-technique：直接关联。分析条目在 `coverage` 数组里直接写出 `technique: T1087`，并同时列出 `tactics: [TA0007]` 与 `subtechniques: [T1087.001, T1087.002]`，再给出 `coverage: Low`。这是资料里攻击侧与防御侧之间唯一的显式连接，载体是技术编号而不是中间对象。示例中一条分析条目（CAR-2013-04-002）引用了 24 条 technique 覆盖记录，tactics 编号包括 TA0007、TA0006、TA0008、TA0003、TA0004、TA0005、TA0002、TA0010 等。
2. Analytic → Implementation（一对多）：同一条目可有多个实现，每个实现有 `type`；README 说分析条目中包含直接针对具体工具的实现。
3. Implementation → Data Model（可选单值）：例如 DNIF 实现的 `data_model: Sysmon native`，LogPoint 实现的 `data_model: LogPoint native`，即实现声明它落在哪个数据模型上。
4. Analytic → Data Model Reference（一对多）：以 `process/create/exe` 这类 object/action/field 坐标表达该分析依赖哪些被监控的属性与状态变化。
5. Sensor → Data Model：传感器输出必须被映射进数据模型；对传感器测量到的每个 object，它捕获状态；覆盖矩阵的 actions 在 y 轴、fields 在 x 轴。
6. Analytic → Unit Test（一对多）：每条条目自带可运行触发测试。
7. Analytic → D3FEND 防御技术（一对多）：通过 `iri`/`id`/`label` 直接引用，示例为 `D3-PLA` / `d3f:ProcessLineageAnalysis` / `Process Lineage Analysis`。也就是说防御侧还存在"防御技术"这一层对象，它与分析条目直接相连。
8. Analytic → Glossary：README 把 Glossary 列为分析条目的内容之一，具体关联方式资料未说明。
9. CAR ↔ ATT&CK：两个独立项目，刻意保持"威胁如何被表述"与"可能的检测方式集合"分离，因此攻击侧对象内部不嵌入防御内容。
10. CAR ↔ OSSEM Common Data Model：CAR 采用 OSSEM 的公共数据模型。

关键的结论是：**攻击侧对象与防御侧条目是直接按技术编号关联的（分析条目持有 `technique` 编号），而数据侧与条目是通过 `(object, action, field)` 三元组坐标关联的；攻击侧与数据侧之间没有直接边，二者在"分析条目"这个对象上交汇。**这正是 §9 要借鉴的结构。

## 5. 抽象层次的选择

- 条目描述的对象是"对抗行为"，不是实现细节：CAR 的分析条目"developed to detect the adversary behaviors in ATT&CK"，开发流程从"识别并排序 ATT&CK 中的对手行为"开始，再找数据、再找传感器，最后才写分析条目。
- 条目承载的是"假设 + 理由 + 可能的实现"：`description` 讲清楚想法（operating theory 与 rationale），`implementations` 里的 pseudocode 被明确定义为"该分析可能如何被实现"的描述，而不是唯一实现。
- 但同一条目也允许承载具体实现：`implementations[].type` 出现 pseudocode、Sigma、DNIF、LogPoint，README 另提 Splunk、EQL；即"抽象层次"是同一容器里分层的：假设层 → 伪代码层 → 具体工具层。
- 条目粒度不是"一个技术一条规则"：CAR-2013-04-002 一条条目同时覆盖 24 条 technique，覆盖级别多为 Low。因此粒度的基准是"一个可被单元测试触发的检测想法"，而不是一个 ATT&CK 技术。
- 什么时候不收录进主库：资料给出唯一明确的判据——当分析以特定产品的源代码形式构建、且这段代码支持的检测集合很宽、以致很难描述为一组彼此不同的分析条目时，不整合进 CAR 主站，而是收集到 implementations 库中（BZAR 就是例子）。
- 准入标准：CAR 强调"validated and well-explained"，即条目要经过验证并解释充分，尤其是其 operating theory 与 rationale；贡献流程要求先读 CONTRIBUTING.md、签署 Developer Certificate of Origin、开 issue（有 adding an analytic 模板）、接受社区反馈，被接受并改动后网站自动更新。
- "已有条目的变体"如何判定（新建条目还是改条目）：资料未说明。hypothesis 与 description 的分工：资料未说明。

## 6. 稳定部分与易变部分

希望很少变的部分：

- 数据模型的本体：13 个 object 及其 actions、fields，以及"对象是名词、动作是动词、字段是形容词"的词汇约定。
- `(object, action, field)` 这个三段坐标本身，它是传感器输出与查询之间的稳定接口。
- CAR 与 ATT&CK 的分工边界：威胁表述与检测方式分离，不把分析写进 ATT&CK。
- 条目的字段骨架（id、title、coverage、implementations、data_model_references、unit_tests 等）。
- 数据模型这一层被当作可对接外部标准的层：CAR 已与 OSSEM 合作改用其 Common Data Model，说明本体是"接口"而非一次性内容。

预期不断增长的部分：

- `analytics` 目录下的 YAML 分析条目（每个条目一个文件）。
- implementations 库（当前只有 BZAR），以及面向具体产品源码的集合。
- 传感器映射（README 有专门的 issue 模板）。
- 条目内的 unit tests、D3FEND 映射、coverage 记录。
- 数据模型覆盖汇总（data_model_with_sensors）与 ATT&CK Navigator layer。

新增与废弃流程、版本管理：

- 新增流程：读 CONTRIBUTING.md → 签署 Developer Certificate of Origin → 开 issue（模板分为新增分析条目、新增数据模型内容、新增传感器映射）→ 等待反馈与社区意见 → issue 被接受并完成改动 → car.mitre.org 自动更新。
- 网站由 `analytics` 目录的结构化内容自动构建，其他内容放在 `docs` 文件夹，源码型实现放在 `implementations` 目录。
- 条目的废弃/下线流程、版本号策略、ATT&CK 版本升级时的同步机制：资料未说明。资料中唯一的时间字段是 `submission_date`。

## 7. 内容与执行的分离

- 内容形式：分析条目是 `analytics` 目录下的 YAML 文件；其他内容在 `docs` 文件夹；网站由这些结构化内容自动构建。以源码形式存在的实现放在 `implementations` 目录。
- 内容里能放什么：一个条目可以同时给出 `description`（人类可读的假设与理由）、`implementations[].code`（pseudocode 或具体查询语言代码）、`data_model_references`（对数据的坐标级依赖）、`unit_tests[].commands`（触发方式）。因此内容既是知识（为什么这样检测），也是可执行规则（怎么检测）。
- 由什么解释或执行：资料未说明 CAR 自带执行引擎。从示例看，执行由外部具体工具承担：伪代码之外出现 Sigma、DNIF、LogPoint 三种具名格式，README 另外提到 Splunk 与 EQL；`unit_tests` 在具体平台配置（示例 `Windows 7`）上运行以触发分析条目。伪代码本身是"可能如何实现"的描述，需要人或工具翻译成目标平台代码。
- 内容能表达的逻辑上限：资料没有给出形式化逻辑上限。资料只给出一种"超出上限"的实际表现与处理方式——当一段源代码支持的检测集合太宽、难以拆成一组彼此不同的条目时，就把整段代码放进 implementations 库，而不是塞进条目。另外，数据模型允许传感器"不监控动作、只扫描对象是否存在"，此时状态需要从对象属性的变化推断，这属于数据侧表达能力的边界，而不是条目逻辑的边界。

## 8. 覆盖与成熟度的表达

覆盖的表达方式有四种，且都在资料中出现：

1. 条目内的 `coverage` 数组：对每条被检测的 ATT&CK technique，给出 `coverage` 级别。示例中出现 `Low` 与 `Moderate` 两个值：CAR-2013-04-002 的 24 条覆盖记录中 23 条为 Low、1 条（T1059）为 Moderate。级别如何判定、是否有完整枚举：资料未说明。
2. ATT&CK Navigator layer：README 指明有一个 layer 记录"CAR 当前覆盖的 ATT&CK tactics 与 techniques 集合"。
3. 数据模型覆盖：为了衡量传感器对分析的有用程度，传感器输出必须映射进数据模型；资料指向一份 data model coverage 汇总（data_model_with_sensors）。
4. 覆盖矩阵：二维表，actions 在 y 轴、fields 在 x 轴；这是"某个 object 的哪些动作与哪些字段被覆盖"的表达方式。

成熟度的表达：资料中没有独立的成熟度分级字段或状态字段（例如没有 stable/deprecated 之类的标注）。资料给出的是总体质量要求与证据形式——CAR 专注于提供"validated and well-explained"的分析条目，尤其要说清 operating theory 与 rationale；每条条目配一个可运行的 unit test，用来触发它。因此"依据"是：理由说明 + 可运行触发测试 + 覆盖声明。成熟度等级、评审状态、置信度、误报率等：资料未说明。

需要注意：`coverage: Low` 是"该条目对该技术的覆盖程度"，不是"该条目自身的成熟度"，两者在资料中是两回事；覆盖率与成熟度都缺少判定标准说明。

## 9. 对我们的启发

- 分析：CAR 把"数据面"独立成一套 `(object, action, field)` 坐标本体，条目只引用坐标而不绑定具体日志字段，这一层最值得我们照搬。对应到我们的库：把运行时已经暴露的 11 个位置形式化为"位置（object）+ 事件或状态变化（action）+ 可观测字段（field）"的三段坐标，作为算子库的输入契约与记录格式的统一标识；这样算子不必知道自己是第几个位置、上游是样本还是梯度。可直接迁移（坐标思想直接可用，只是名词要换成联邦 LoRA 的语义）。
- 分析：CAR 的方法层不是按论文组织的，而是按"可被单元测试触发的检测假设"组织，论文／工具只是 `implementations` 里的一种载体。对应到 `methods` 层：方法条目应当是"一个假设 + 一组实现 + 一个触发用例"，一篇论文可以拆成多条条目，一条条目也可以有多个实现（例如同一防御的不同聚合器或不同框架版本）。可迁移（这正是我们"追论文追不完"的根因：把论文当成组织单位，而不是把假设当成组织单位）。
- 分析：攻击侧与防御侧分库、只用编号引用，是 CAR 明确的设计决定。对应到 `knowledge_base`：威胁面（投毒、后门、梯度反演、通信窃听等）应有自己独立的编号与版本，方法条目通过编号引用威胁，覆盖率变化时只改引用而不改威胁定义。可直接迁移。
- 分析：`coverage` 允许一条条目同时声明多个被覆盖对象、并给每条独立的覆盖级别，这直接回应我们"说不清覆盖了什么"的问题。对应到 `evaluation` 与 `knowledge_base`：方法条目应对每个威胁面给出覆盖级别，并自动汇总成矩阵视图（类似 Navigator layer 的角色），而不是靠人工写文档。可直接迁移。
- 分析：CAR 除了威胁侧编号，还有 D3FEND 这一层"防御技术"对象与分析条目直接相连，说明框架允许存在"机制层"而不只是"论文层"。对应到 `knowledge_base` 与 `operators`：我们可以引入"防御机制"对象（例如裁剪、加噪、聚类过滤、梯度对齐），让方法条目引用机制，多个方法共享同一机制，机制再落到算子库的具体算子上。需要改造后迁移（把 D3FEND 的位置换成我们自己的机制本体）。
- 分析：CAR 把实现从条目里拆出来，用 `type` 区分伪代码与各工具的具体实现，并给每个实现标注它所属的数据模型。对应到 `methods` 与 `operators`：论文插件应是 `type` 的一种取值；同一条目的 NumPy/PyTorch/分布式实现是并列的 `implementations`，并各自标注它假设的数据模型（对应我们的运行时位置与张量布局）。可直接迁移。
- 分析：CAR 给出了唯一明确的"不收录"判据——当一段代码支持的检测集合太宽、无法拆成彼此不同的条目时，整段代码移到实现库而不是主库。对应到 `methods`：我们也需要一条反向规则，明确哪些东西不该成为方法条目（例如通用优化器、通用损失函数、通用通信原语，它们更应是算子而不是方法），否则算子库与方法层的边界会继续模糊。需要改造后迁移（判据的形态可借，具体阈值要按数值算法定义）。
- 分析：CAR 把"可运行的触发测试"作为每个条目的必备伴随物，并区分"条目"与"测试"两类对象。对应到 `evaluation`：方法条目应自带可执行的触发／验证用例，但我们触发的是数值行为（构造恶意更新、注入后门样本、设定扰动预算），不是敲几条命令看日志是否命中；因此测试对象的字段需要从 configurations/commands 改为数据集、攻击配置、预算与判据。需要改造后迁移。
- 分析：CAR 的内容是结构化 YAML 数据文件，网站与视图都由这些内容自动构建，内容与展示、执行彻底解耦。对应到 `knowledge_base` 与 `records`：方法、算子、运行时位置、覆盖关系都应落成结构化文件，索引、文档、覆盖矩阵、实验报告自动生成，避免再出现"库说不清覆盖了什么"。可直接迁移。
- 分析：CAR 把数据模型这一层对外部标准（OSSEM Common Data Model）对齐，说明本体层是可以被替换的稳定接口。对应到 `runtime` 与 `operators`：11 个运行时位置应当定义成一份稳定、可对外对齐的接口描述（含每个位置的输入输出结构与语义），算子库只依赖这份接口，这样新增方法与新增训练后端都不会互相牵动。需要改造后迁移（我们没有现成的外部标准可对齐，得自建并冻结）。
- 分析：不能直接照搬的是 CAR 覆盖判定的底层假设——它的分析条目以"能否从被观测数据中检测到行为"为核心，coverage 是"行为可观测性"的度量。我们的防御是数值算法，其效果是"攻击成功率下降多少、模型精度损失多少、通信量增加多少"，不是命中与否。因此 `coverage: Low/Moderate` 这种定性分级不能原样搬用，必须改造成以指标区间与威胁模型为前提的覆盖语义（在什么攻击强度、什么数据分布下有效）。不可照搬（语义层面不兼容）。
- 分析：不能直接照搬的还有 `platforms` 与 `information_domain` 这类静态枚举字段。CAR 的平台是 Windows/Linux/macOS、域是 host/network/process/external，属于运行环境；我们的"11 个位置"是训练流程的阶段，属于流水线位置，两者维度不同。若把位置塞进平台字段，会把"在哪个阶段"与"在什么环境下"混为一谈，后续无法回答"某个位置有没有被覆盖"。不可照搬（维度不匹配，应另立位置维度）。
- 分析：CAR 刻意只做覆盖声明、不做效果承诺，并反复强调不是终极方案、采用者自行决定；我们的方法层不能学这一点——联邦 LoRA 的防御方法必须以可复现的量化实验作为准入依据，否则"方法层"会退化成论文清单。对应到 `evaluation`：覆盖声明与效果证据应同时存在，且效果证据要能追溯到运行时的某个位置与某组算子。部分照搬（分离原则可借，免责姿态不可借）。

## 10. 框架自己承认的局限

- 影响范围上的自我限制：CAR 是很多组织的良好起点与开放协作平台，但不是防御 ATT&CK 所述威胁的终极答案。
- 设计上的取舍：不把分析放进 ATT&CK，因为防御方式可能有很多种，且应由实施组织根据自身环境与所面对的威胁决定哪种最合适；因此 CAR 不替使用者做选择。
- 表达能力的局限：以特定产品源代码形式构建的分析，如果其代码支持很宽的检测集合、难以描述为一组不同的分析条目，就不能进入 CAR 主站，只能进入 implementations 库。
- 数据侧的局限：存在传感器并不监控对象上的动作，而只是周期性扫描对象是否存在；这种情况下状态只能通过观察对象属性的变化来推断。
- 标准对齐仍在进行：README 的措辞是 CAR 已与 OSSEM 合作、"moving forward"使用其公共数据模型，说明数据模型层处于对齐／迁移过程中。
- 资料未说明的局限（不能替它补）：条目误用与误报、条目的时效性与过时判定、覆盖率数值（Low/Moderate）的判定标准、分析方法的对抗性规避（例如攻击者绕过检测）等，资料均未提及。

## 11. 原文依据

1. 支撑第 1 节"CAR 的定位与 ATT&CK 的关系"：
> The MITRE Cyber Analytics Repository (CAR) is a knowledge base of analytics developed by MITRE based on the [MITRE ATT&CK®](https://attack.mitre.org/) adversary model.

2. 支撑第 4 节"攻击侧与防御侧是刻意分离的两个项目"：
> It’s critical to keep how we articulate threats with ATT&CK separate from a set of possible ways to detect them with the analytics.

3. 支撑第 5 节与第 10 节"不替使用者规定防御方式、防御有多种可能"：
> We don’t want the defender content in ATT&CK to be overly prescriptive about how someone can defend against ATT&CK techniques because there could be many different ways

4. 支撑第 10 节"CAR 明确否认自己是终极方案"：
> CAR is a good starting point for many organizations and can be a great platform for open analytic collaboration - but it isn’t the be-all/end-all for defending against the threats described by ATT&CK.

5. 支撑第 2 节与第 4 节"数据侧以 (object, action, field) 坐标表达可被传感器捕获的内容"：
> When paired together, the three-tuple of `(object, action, field)` acts like a coordinate, and describe what properties and state changes of the object can be captured by a sensor.

6. 支撑第 8 节"覆盖的衡量方式是传感器输出到数据模型的映射"：
> In order to gauge the usefulness of a sensor with respect to analytics, its output must be mapped into the Data Model.

7. 支撑第 7 节"内容以 YAML 存放、网站由结构化内容自动构建"：
> Analytics are in the `analytics` directory as YAML files. The website is built automatically from that structured content.

8. 支撑第 5 节与第 7 节"覆盖面过宽的源码型分析不进主站，而进实现库"：
> For these types of analytics, rather than integrating them into the main CAR site, we’ve collected them under a library of implementations.

9. 支撑第 8 节与第 10 节"存在只扫描对象存在性、需从属性变化推断状态的传感器"：
> Some sensors periodically scan for objects, instead of monitoring for state changes. In these cases, state may be inferred by looking for changes in the properties of an object.

10. 支撑第 8 节"质量门槛是经过验证且解释充分，尤其是原理与理由"：
> With respect to coverage, CAR is focused on providing a set of validated and well-explained analytics, in particular with regards to their operating theory and rationale.

```json
{
  "key": "car",
  "framework": "MITRE Cyber Analytics Repository (CAR)，基于 MITRE ATT&CK 对手模型的分析知识库；资料未给出仓库版本号，示例条目 CAR-2013-04-002 的 submission_date 为 2013/04/11",
  "object_types": [
    {
      "name": "Analytic（分析条目）",
      "role": "detection",
      "fields": ["id", "title", "submission_date", "information_domain", "platforms", "subtypes", "analytic_types", "contributors", "description", "coverage", "implementations", "data_model_references", "unit_tests", "d3fend_mappings", "hypothesis（README 声明，示例条目无对应顶层字段）", "Glossary（README 声明，示例条目无对应顶层字段）"]
    },
    {
      "name": "ATT&CK technique / sub-technique / tactic 引用",
      "role": "attack",
      "fields": ["technique", "tactics", "subtechniques", "coverage"]
    },
    {
      "name": "Data Model Object（数据模型对象）",
      "role": "telemetry",
      "fields": ["object（13 个：authentication, driver, email, file, flow, http, module, process, registry, service, socket, thread, user_session）", "actions", "fields"]
    },
    {
      "name": "Action（动作）",
      "role": "telemetry",
      "fields": ["action 名称，位于覆盖矩阵 y 轴"]
    },
    {
      "name": "Field（字段）",
      "role": "telemetry",
      "fields": ["field 名称，位于覆盖矩阵 x 轴；同名 field 可出现在多个 object 下"]
    },
    {
      "name": "Sensor（传感器）",
      "role": "telemetry",
      "fields": ["资料未说明；其输出必须映射进 Data Model"]
    },
    {
      "name": "Implementation（实现）",
      "role": "artifact",
      "fields": ["type", "code", "description", "data_model"]
    },
    {
      "name": "Implementation Library（实现库，如 BZAR）",
      "role": "artifact",
      "fields": ["资料未说明"]
    },
    {
      "name": "Unit Test（单元测试）",
      "role": "test",
      "fields": ["configurations", "description", "commands"]
    },
    {
      "name": "Coverage Entry（覆盖声明）",
      "role": "relation",
      "fields": ["technique", "tactics", "subtechniques", "coverage"]
    },
    {
      "name": "Data Model Reference（数据模型引用）",
      "role": "relation",
      "fields": ["object/action/field 三段路径"]
    },
    {
      "name": "D3FEND defensive technique（防御技术引用）",
      "role": "defense",
      "fields": ["iri", "id", "label"]
    },
    {
      "name": "Glossary term（术语表条目）",
      "role": "other",
      "fields": ["资料未说明"]
    },
    {
      "name": "OSSEM Common Data Model（外部数据模型）",
      "role": "other",
      "fields": ["资料未说明"]
    }
  ],
  "id_scheme": "分析条目示例为 CAR-2013-04-002，形式上是 CAR-<四位年>-<两位月>-<三位序号>，年月与 submission_date: 2013/04/11 一致，但编号规则资料未说明；引用的 ATT&CK 编号为 tactic TA0007、technique T1087、sub-technique T1087.001（technique 加 . 加三位序号）；D3FEND 为 D3-PLA 与 d3f:ProcessLineageAnalysis；数据模型用 object/action/field 三段斜杠路径，如 process/create/exe",
  "attack_defense_link": "via_technique_id",
  "link_detail": "分析条目在自身的 coverage 数组中直接写出 technique 编号（如 T1087），并同时列出 tactics（TA0007）与 subtechniques（T1087.001）以及 coverage 级别（Low/Moderate），因此攻击侧与检测侧不是通过中间对象相连，而是由检测条目持有技术编号的直接引用；示例条目 CAR-2013-04-002 一条即引用 24 条 technique 覆盖记录，其中 23 条 Low、1 条 Moderate。数据侧走的是另一条路径：条目用 data_model_references 的 (object, action, field) 坐标对接传感器，传感器输出必须映射进 Data Model；资料中攻击侧编号与数据侧坐标之间没有直接边，二者在分析条目上交汇。此外条目还用 d3fend_mappings（iri/id/label）直接关联 D3FEND 防御技术。",
  "abstraction_level": "条目描述的是要检测的对抗行为（detect the adversary behaviors in ATT&CK），内容为假设、operating theory 与 rationale，加上一段说明可能如何实现的 pseudocode；实现细节以 implementations 数组承载，type 可为 pseudocode、Sigma、DNIF、LogPoint（README 另提 Splunk、EQL）。粒度上一条条目可以覆盖多条 technique（示例 24 条，多为 Low），因此基准单位是'一个可被单元测试触发的检测想法'而非一个技术。不收录进主库的唯一明确判据是：以特定产品源代码形式构建、且代码支持的检测集合过宽、难以描述为一组彼此不同的分析条目时，改放进 implementations 库。条目变体的判定规则资料未说明。",
  "stable_parts": ["数据模型本体：13 个 object 及其 actions、fields（名词/动词/形容词的词汇约定）", "(object, action, field) 三段坐标作为传感器输出与查询的接口", "CAR 与 ATT&CK 的分工边界：威胁表述与检测方式分离，不把分析写进 ATT&CK", "分析条目的字段骨架（id、title、coverage、implementations、data_model_references、unit_tests、d3fend_mappings 等）", "数据模型层对外部标准的对齐方向（已与 OSSEM 合作采用其 Common Data Model）"],
  "growing_parts": ["analytics 目录下的 YAML 分析条目", "implementations 库（当前只有 BZAR）及面向具体产品的源码型分析", "传感器映射（有专门的 issue 模板）", "条目内的 unit tests、D3FEND 映射与 coverage 记录", "数据模型覆盖汇总（data_model_with_sensors）与 ATT&CK Navigator layer"],
  "content_format": "知识内容为 analytics 目录下的 YAML 文件，其他内容在 docs 文件夹，源码型实现放在 implementations 目录；网站由这些结构化内容自动构建；条目内可内嵌 pseudocode 或具体查询语言代码（Sigma、DNIF、LogPoint 等）",
  "execution_engine": "资料未说明 CAR 自带执行引擎；执行由外部具体工具承担（示例出现 Sigma、DNIF、LogPoint，README 另提 Splunk、EQL），pseudocode 需要被翻译成目标平台实现；unit_tests 在具体平台配置（示例 Windows 7）上运行以触发分析条目",
  "coverage_expression": "条目内 coverage 数组按 technique 给出覆盖级别（示例出现 Low 与 Moderate，24 条记录中 23 Low、1 Moderate）；ATT&CK Navigator layer 汇总当前被覆盖的 tactics 与 techniques；数据侧有 data_model_with_sensors 覆盖汇总；覆盖矩阵是 actions（y 轴）× fields（x 轴）的二维表；级别的判定标准与完整枚举资料未说明",
  "maturity_expression": "没有独立的成熟度分级或状态字段；资料给出的质量要求是 CAR 专注于提供 validated and well-explained 的分析条目，尤其要说清 operating theory 与 rationale，并给每条条目配一个可运行以触发它的 unit test；覆盖级别 coverage 不等同于条目成熟度",
  "lessons": [
    {"idea": "把数据面抽成 (object, action, field) 三段坐标本体，条目只引用坐标，不绑定具体日志字段", "applies_to": "runtime", "transfer": "adapted", "why": "我们的 runtime 已暴露 11 个位置，把每个位置形式化为'位置+事件或状态变化+可观测字段'的坐标，就能给算子库一个不依赖具体训练后端的输入契约与统一记录标识，这与 CAR 用坐标统一传感器输出的做法同构，只是对象从主机/网络换成样本、梯度、聚合结果等"},
    {"idea": "方法层以'可被单元测试触发的假设'为组织单位，论文与工具只是 implementations 的一种载体", "applies_to": "methods", "transfer": "adapted", "why": "CAR 的条目 = hypothesis + coverage + implementations + unit_test，一条条目可覆盖多个技术、也可有多个实现；我们按论文一篇篇写插件，正是把载体当成了组织单位，导致无法回答覆盖了什么"},
    {"idea": "攻击侧与防御侧分库，只用编号引用，不互相内嵌", "applies_to": "knowledge_base", "transfer": "direct", "why": "CAR 明确把 ATT&CK 与 CAR 做成两个项目并用 T####/TA#### 编号连接；我们的威胁面应有独立编号，方法条目通过编号引用，威胁面变化时只改引用"},
    {"idea": "覆盖用分级字段表达，允许一条条目覆盖多个对象并逐条给级，再汇总成矩阵视图", "applies_to": "evaluation", "transfer": "direct", "why": "CAR 的 coverage 数组与 ATT&CK Navigator layer 正好对应我们'说不清覆盖了什么'的痛点，可直接改为方法条目对威胁面的覆盖级别加自动汇总矩阵"},
    {"idea": "在威胁编号与方法条目之间引入独立的'防御机制'层（如 D3FEND 技术），方法通过映射引用机制", "applies_to": "knowledge_base", "transfer": "adapted", "why": "CAR 的 d3fend_mappings 说明框架允许机制层与分析条目直接相连；我们可以用同样的位置放裁剪、加噪、聚类过滤、梯度对齐等机制，让多个方法共享机制，机制再落到 operators，需要自建机制本体而非照抄 D3FEND"},
    {"idea": "把实现从条目里拆成 implementations 数组，用 type 区分伪代码与各工具实现，并标注其依赖的数据模型", "applies_to": "methods", "transfer": "direct", "why": "论文插件应当只是 type 的一种取值；同一方法的 NumPy/PyTorch/分布式实现是并列实现，各自标注所假设的运行时位置与张量布局，避免'一篇论文一个条目'的僵化"},
    {"idea": "给出明确的'不收录进主库'判据：覆盖面过宽、无法拆成不同条目的源码型分析移到实现库", "applies_to": "methods", "transfer": "adapted", "why": "我们也需要一条反向规则划清方法层与算子层边界（通用优化器、损失函数、通信原语不应成为方法条目），但阈值必须按数值算法的语义重新定义，不能沿用'检测集合是否可拆分'的说法"},
    {"idea": "每个条目自带可运行的触发／验证测试，测试作为独立对象存在", "applies_to": "evaluation", "transfer": "adapted", "why": "CAR 的 unit_tests 由 configurations、description、commands 构成；我们的触发对象是数据集、攻击配置、扰动预算与判据，字段需要重新设计，但'条目必须自带可执行触发用例'这一点可以照搬"},
    {"idea": "内容以结构化数据文件存放，文档、索引与视图自动构建，内容与展示、执行解耦", "applies_to": "records", "transfer": "direct", "why": "CAR 的 analytics 目录 YAML 加网站自动构建，正是让覆盖矩阵、文档、索引始终与内容一致的做法，可直接用于方法、算子、运行时位置与覆盖关系的记录"},
    {"idea": "把数据模型／接口层对齐到可替换的稳定标准，使上层内容独立演进", "applies_to": "runtime", "transfer": "adapted", "why": "CAR 与 OSSEM Common Data Model 对齐说明本体层是可以被外部标准替换的接口；我们没有可对齐的外部标准，需要自建并冻结一份 11 个运行时位置的接口描述，算子库只依赖它"},
    {"idea": "不能照搬：以'能否从被观测数据中检测到行为'为核心的覆盖语义", "applies_to": "evaluation", "transfer": "not_transferable", "why": "CAR 的 coverage 是行为可观测性的定性度量（Low/Moderate），而我们的防御是数值算法，效果表现为攻击成功率下降、精度损失、通信开销等连续指标，必须以指标区间与威胁模型为前提重新定义覆盖语义"},
    {"idea": "不能照搬：platforms 与 information_domain 这类静态枚举字段承载运行位置", "applies_to": "runtime", "transfer": "not_transferable", "why": "CAR 的 platforms 是 Windows/Linux/macOS、information_domain 是 host/network/process/external，属于运行环境维度；我们的 11 个位置是训练流程阶段维度，混入同一字段会导致无法回答'某个位置是否被覆盖'，应另立位置维度"},
    {"idea": "不能照搬：只声明覆盖、不做效果承诺的免责姿态", "applies_to": "evaluation", "transfer": "not_transferable", "why": "CAR 反复强调自己不是终极方案、由使用者自行决定；我们的方法层若只做覆盖声明而无量化实验依据，就会退化为论文清单，因此方法准入必须同时具备覆盖声明与可复现效果证据"}
  ],
  "limits": [
    "CAR 不是防御 ATT&CK 所述威胁的终极方案（be-all/end-all），只是起点与协作平台",
    "不把分析写进 ATT&CK：防御方式可能有很多种，且应由实施组织根据自身环境与威胁自行决定，框架不替使用者做选择",
    "以特定产品源代码构建、覆盖面过宽而难以拆成不同分析条目的内容不能进主站，只能放 implementations 库",
    "存在不监控动作、只周期性扫描对象存在性的传感器，此时状态只能通过属性变化推断",
    "数据模型层仍在迁移：README 的措辞是已与 OSSEM 合作、moving forward 采用其 Common Data Model",
    "资料未说明：条目废弃与过时判定、覆盖级别 Low/Moderate 的判定标准、评审与置信度状态、误报与规避问题、ATT&CK 版本升级的同步机制"
  ],
  "quotes": [
    {"supports": "第 1 节：CAR 是基于 ATT&CK 对手模型的分析知识库", "text": "The MITRE Cyber Analytics Repository (CAR) is a knowledge base of analytics developed by MITRE based on the [MITRE ATT&CK®](https://attack.mitre.org/) adversary model."},
    {"supports": "第 4 节：威胁表述与检测方式被刻意分成两个项目", "text": "It’s critical to keep how we articulate threats with ATT&CK separate from a set of possible ways to detect them with the analytics."},
    {"supports": "第 5 节与第 10 节：不规定防御方式，因为防御有多种可能", "text": "We don’t want the defender content in ATT&CK to be overly prescriptive about how someone can defend against ATT&CK techniques because there could be many different ways"},
    {"supports": "第 10 节：框架自认不是终极方案", "text": "CAR is a good starting point for many organizations and can be a great platform for open analytic collaboration - but it isn’t the be-all/end-all for defending against the threats described by ATT&CK."},
    {"supports": "第 2 节与第 4 节：数据侧用 (object, action, field) 三元组坐标描述可被传感器捕获的属性与状态变化", "text": "When paired together, the three-tuple of `(object, action, field)` acts like a coordinate, and describe what properties and state changes of the object can be captured by a sensor."},
    {"supports": "第 8 节：覆盖以传感器输出到数据模型的映射来衡量", "text": "In order to gauge the usefulness of a sensor with respect to analytics, its output must be mapped into the Data Model."},
    {"supports": "第 7 节：内容为 YAML 文件，网站由结构化内容自动构建", "text": "Analytics are in the `analytics` directory as YAML files. The website is built automatically from that structured content."},
    {"supports": "第 5 节与第 7 节：覆盖面过宽的源码型分析不进主站而进实现库", "text": "For these types of analytics, rather than integrating them into the main CAR site, we’ve collected them under a library of implementations."},
    {"supports": "第 8 节与第 10 节：存在只扫描对象存在性、需从属性变化推断状态的传感器", "text": "Some sensors periodically scan for objects, instead of monitoring for state changes. In these cases, state may be inferred by looking for changes in the properties of an object."},
    {"supports": "第 8 节：质量门槛是经过验证、解释充分，尤其要讲清原理与理由", "text": "With respect to coverage, CAR is focused on providing a set of validated and well-explained analytics, in particular with regards to their operating theory and rationale."}
  ]
}
```
