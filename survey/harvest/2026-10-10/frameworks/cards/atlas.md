# atlas：MITRE ATLAS（Adversarial Threat Landscape for AI Systems）atlas-data 数据仓库，格式版本 6.0.0、内容版本 2026.09

**资料口径说明（影响以下所有判断）**：资料中的 mitigations 描述被截到 500 字符；techniques 只提供了 27 个完整条目，其余仅为"编号 | 名称 | maturity | 关系"的一行摘要；tactics 给了全部条目；case study 只给了一个完整条目。凡资料未展示的字段，下文一律写作"资料未说明"或"资料未展示"，不按我对该框架的其他了解补全。

## 1. 要解决的问题

ATLAS 自己把自己定义为"a public knowledge base of adversary TTPs targeting AI systems"，即面向 AI 系统的对手 TTP（战术、技术与程序）公共知识库；本仓库（atlas-data）的职责是"distributes data for MITRE ATLAS"，并"includes the supporting tooling for parsing, validating, and managing ATLAS data"。也就是说，它服务两类人：需要消费 ATLAS 数据的人（数据使用者、工具开发者、分析人员），以及需要维护和发布这份知识库的人。

它解决的问题可以归纳为四点：把针对 AI 系统的攻击战术、技术、缓解措施与真实案例整理成结构化数据；让这份数据可以被程序解析和校验（Pydantic 模型 `atlas.schemas.AtlasExport`）；让它可以被集中管理（REST API + SQLite 数据库，支持从 v6 YAML 导入、通过 API 修改、按版本导出）；让它可以被分发和转换（月度发布 YAML、manifest 清单，以及 STIX、Excel、ATT&CK Navigator 图层等下游格式）。

关于"它明确说自己不做什么"，**资料未说明**。README 没有给出非目标声明；只能观察到仓库的产物是数据文件、schema、API 与导出工具，资料中没有描述任何执行检测或执行防御的组件（这一句是归纳，不是原文声明）。

资料版本方面：数据文件为 `ATLAS-2026.09.yaml`，其中 `format-version: 6.0.0`、`collection.version: '2026.09'`；README 的示例中另外出现过内容版本 `2026.05` 与格式版本 `6.0.0`。

## 2. 核心对象

README 明确列出的顶层键只有 8 个：`format-version`、`collection`、`matrix`、`tactics`、`techniques`、`mitigations`、`case-studies`、`relationships`。资料中的对象类型就由这些键界定；**资料中没有** data source、detection、analytics、rule、test 这类对象，资料也未说明它们是否存在于别处。

资料给出的 2026.09 规模为：tactics 16、techniques 208（技术与子技术合计）、mitigations 40、case-studies 73、relationships 322。

### 2.1 collection（集合，单例）

| 字段名 | 含义 | 是否必填 | 取值约束与观察 |
|---|---|---|---|
| `name` | 名称 | 资料未说明 | 值为 `ATLAS` |
| `description` | 描述 | 资料未说明 | 值为 `Adversarial Threat Landscape for AI Systems` |
| `references` | 外部引用列表 | 资料未说明 | 样本中为空数组 `[]`；元素形状为 `{id, title, url}`（见 2.4） |
| `created-date` | 创建日期 | 资料未说明 | `'2020-10-23'` |
| `modified-date` | 修改日期 | 资料未说明 | `'2026-09-15'` |
| `version` | 内容版本 | 资料未说明 | `'2026.09'`，遵循 YYYY.MM.N |
| `id` | 标识 | 资料未说明 | 固定为 `ATLAS-collection` |
| `uuid` | UUID | 资料未说明 | `7a735cfc-0469-5d8b-b11f-d014be33394e` |
| `object-type` | 对象类型标签 | 资料未说明 | 值为 `collection` |

资料给出的键计数为 `"collection": 9`，与上表 9 个字段一致。

### 2.2 matrix（矩阵，单例）

| 字段名 | 含义 | 是否必填 | 取值约束与观察 |
|---|---|---|---|
| `name` | 名称 | 资料未说明 | `ATLAS` |
| `description` | 描述 | 资料未说明 | 同上 |
| `references` | 外部引用列表 | 资料未说明 | `[]` |
| `created-date` | 创建日期 | 资料未说明 | `'2020-10-23'` |
| `modified-date` | 修改日期 | 资料未说明 | `'2026-08-31'` |
| `id` | 标识 | 资料未说明 | 固定为 `ATLAS-matrix` |
| `uuid` | UUID | 资料未说明 | `967c63ff-22bd-5ff8-aa59-1e1fca8dec78` |
| `object-type` | 对象类型标签 | 资料未说明 | 值为 `matrix` |

资料给出的键计数为 `"matrix": 8`，与上表一致。矩阵本身不直接持有技术，它的布局由 `sequences` 关系表达（见第 4 节）。

### 2.3 tactic（战术）

| 字段名 | 含义 | 是否必填 | 取值约束与观察 |
|---|---|---|---|
| `name` | 名称 | 资料未说明 | 如 `AI Model Access`、`Reconnaissance` |
| `description` | 描述对手目标 | 资料未说明 | 自由文本，通常以"The adversary is trying to…"开头 |
| `references` | 外部引用列表 | 资料未说明 | 样本中均为 `[]` |
| `created-date` | 创建日期 | 资料未说明 | 如 `'2021-05-13'` |
| `modified-date` | 修改日期 | 资料未说明 | 如 `'2025-10-13'` |
| `attack-reference` | 到 MITRE ATT&CK 的映射 | **观察上不是必填**（`AML.TA0000`、`AML.TA0001` 没有此字段） | 形状为 `{id, url}`，如 `{id: TA0043, url: https://attack.mitre.org/tactics/TA0043/}` |
| `id` | 标识 | 资料未说明 | `AML.TA####` |
| `uuid` | UUID | 资料未说明 | 每个战术各一个 |
| `object-type` | 对象类型标签 | 资料未说明 | 值为 `tactic` |

### 2.4 technique（技术）与 sub-technique（子技术）

两者共用同一个 `techniques` 顶层键与同一套字段，资料未把它们分列。

| 字段名 | 含义 | 是否必填 | 取值约束与观察 |
|---|---|---|---|
| `name` | 名称 | 资料未说明 | 如 `Training Data Poisoning` |
| `description` | 描述行为 | 资料未说明 | 自由文本，正文里常用相对链接引用其他条目（如 `[Poison Training Data](/techniques/AML.T0020)`） |
| `references` | 外部引用列表 | 资料未说明 | 可以是 `[]`，也可以是 `[{id, title, url}]` |
| `created-date` / `modified-date` | 创建/修改日期 | 资料未说明 | 如 `'2021-05-13'` / `'2026-07-31'` |
| `platforms` | 适用平台 | 资料未说明 | 观察到 `Predictive AI`、`Generative AI`、`Agentic AI`、`Enterprise`；资料未给出封闭取值域 |
| `id` | 标识 | 资料未说明 | 技术 `AML.T####`，子技术 `AML.T####.###` |
| `maturity` | 成熟度 | 资料未说明 | 观察到 `Feasible`、`Demonstrated`、`Realized` 三档；资料未说明定义与判定依据 |
| `uuid` | UUID | 资料未说明 | 每个条目各一个 |
| `object-type` | 对象类型标签 | 资料未说明 | 值为 `technique`（子技术也是 `technique`） |

### 2.5 mitigation（缓解措施）

| 字段名 | 含义 | 是否必填 | 取值约束与观察 |
|---|---|---|---|
| `name` | 名称 | 资料未说明 | 如 `Sanitize Training Data` |
| `lifecycle-phases` | 适用生命周期阶段 | 资料未说明 | 观察到 `Business and Data Understanding`、`Data Preparation`、`AI Model Engineering`、`AI Model Evaluation`、`Deployment`、`Monitoring and Maintenance` |
| `categories` | 类别 | 资料未说明 | 观察到 `Policy`、`Technical - AI`、`Technical - Cyber`；一个条目可含多个 |
| `description` | 措施说明 | 资料未说明 | 自由文本，资料中截到 500 字符；部分条目含"Suggested approaches:"式建议列表 |
| `relationships` | 内嵌关系 | 资料未说明 | 形如 `relationships: mitigates: [{source, target, relationship-type, description}]` |
| `id` | 标识 | 资料未说明 | `AML.M####`（README 缩略形状中可见） |
| `object-type` | 对象类型标签 | 资料未说明 | 值为 `mitigation`（README 缩略形状中可见） |

缓解措施的 `uuid`、`created-date`、`modified-date`、`references` 在资料中**未被展示**，因此资料未说明是否存在这些字段。

### 2.6 case-study（案例研究）

| 字段名 | 含义 | 是否必填 | 取值约束与观察 |
|---|---|---|---|
| `name` | 名称 | 资料未说明 | 如 `Evasion of Deep Learning Detector for Malware C&C Traffic` |
| `description` | 案例叙述 | 资料未说明 | 第一人称叙述攻击/演练过程 |
| `references` | 引用 | 资料未说明 | `[{id, title, url}]` |
| `created-date` / `modified-date` | 创建/修改日期 | 资料未说明 | `'2020-12-15'` / `'2025-03-14'` |
| `type` | 案例类型 | 资料未说明 | 观察到 `Incident`、`Exercise` |
| `actor` | 实施者 | 资料未说明 | 如 `Palo Alto Networks AI Research Team` |
| `target` | 目标 | 资料未说明 | 如 `Palo Alto Networks malware detection system` |
| `date` | 事件日期 | 资料未说明 | `'2020-01-01'` |
| `date-granularity` | 日期粒度 | 资料未说明 | 观察到 `Year` |
| `id` | 标识 | 资料未说明 | `AML.CS####` |
| `uuid` | UUID | 资料未说明 | 每个案例各一个 |
| `object-type` | 对象类型标签 | 资料未说明 | 值为 `case-study` |

### 2.7 relationship（关系对象）

关系不是内联字符串，而是独立的、带类型的对象，也被放在顶层 `relationships` 键下，按**源对象 ID** 分组。

| 字段名 | 含义 | 是否必填 | 取值约束与观察 |
|---|---|---|---|
| `source` | 源对象 ID | 资料未说明 | 如 `AML.M0007`、`AML.CS0000` |
| `target` | 目标对象 ID | 资料未说明 | 如 `AML.T0115`、`AML.TA0002` |
| `relationship-type` | 关系类型 | 资料未说明 | 取值为 `sequences`、`achieves`、`specializes`、`mitigates`、`employs` |
| `description` | 关系理由 | 资料未说明 | 在 `mitigates` 与 `employs` 中出现；`achieves`、`specializes` 的摘要里未展示 |
| `tactic` | 所属战术 | 资料未说明 | 仅在 `employs` 中出现，如 `AML.TA0002` |
| `step-id` | 步骤号 | 资料未说明 | 仅在 `employs` 中出现，如 `S00`、`S01` |
| `leads-to` | 后继步骤 | 资料未说明 | 仅在 `employs` 中出现，数组，如 `[S01]`，空数组表示链结束 |

### 2.8 资料中没有的对象类型

资料未出现 ATT&CK 式的 data source（数据源）、detection（检测）、analytics（分析）、rule（规则）、test（测试）对象；也没有"制品（artifact）"对象类型——"AI artifacts"在资料里是技术名称与描述中的业务词汇（如 `Acquire Public AI Artifacts`），不是一等对象。事件类信息由 case-study 承担。

## 3. 编号与层级

README 明确写明"the format enforces typed ID patterns"，并给出全部模式：Collection ID 为 `ATLAS-collection`；Matrix ID 为 `ATLAS-matrix`；Tactic ID 为 `AML.TA####`；Technique ID 为 `AML.T####`；Sub-technique ID 为 `AML.T####.###`；Mitigation ID 为 `AML.M####`；Case study ID 为 `AML.CS####`。

层级由三种手段表达：矩阵到战术是 `matrix -> tactic` 的 `sequences` 关系，并且是**有序**的（ordered matrix layout），这决定战术在矩阵里的排列；技术到战术是 `technique -> tactic` 的 `achieves` 关系，一个技术可以同时归属多个战术，例如 `AML.T0012` 同时 achieves `AML.TA0004`、`AML.TA0012`、`AML.TA0015`；子技术到父技术是 `sub-technique -> parent technique` 的 `specializes` 关系。

子技术编号沿用父技术编号并追加三位小数后缀，且从 `.000` 开始计数，例如 `AML.T0000` 之下有 `AML.T0000.000` 到 `AML.T0000.003`，`AML.T0010` 之下有 `AML.T0010.000` 到 `AML.T0010.005`。资料未说明编号是否连续分配、是否允许跳号或复用；资料列出的编号确实不连续（例如 `AML.T0009`、`AML.T0019`、`AML.T0022`、`AML.T0058`、`AML.T0104` 等未出现），资料未说明原因。

命名规则上，ID 与人类可读的 `name` 分离，描述中引用其他条目时用相对链接（如 `/techniques/AML.T0018`），不是复制对方的标题与定义。同一事物出现在多处时，处理方式有三条：条目本体只存一份，多个归属位置用多条 `achieves` 关系表达（`AML.T0012` 的例子）；矩阵中的位置用 `sequences` 表达，不复制战术条目；到外部框架的对应关系用 `attack-reference` 字段（如 `id: TA0043`、`url: https://attack.mitre.org/tactics/TA0043/`），而不是把 ATT&CK 的条目搬进来。

每个对象另有 `uuid`，资料中的 uuid 是随条目给出的（如 collection 的 `7a735cfc-…`）；资料未说明 uuid 的生成规则、唯一性范围与跨版本稳定性保证。

## 4. 对象之间的关系

README 明确列出 5 种关系类型与方向：`sequences`：matrix -> tactic（有序矩阵布局）；`achieves`：technique -> tactic；`specializes`：sub-technique -> parent technique；`mitigates`：mitigation -> technique；`employs`：case study -> technique（并带 `tactic`、`step-id`、`leads-to` 元数据）。

**攻击侧与防御侧的关联方式是直接关联，不经过中间对象。** `mitigates` 的 source 是 mitigation（`AML.M####`），target 直接是 technique（`AML.T####` 或子技术）；资料中不存在检测规则、数据源或"覆盖映射"这类中间对象。例如 `AML.M0007` 的 mitigates 关系直接指向 `AML.T0115` 与 `AML.T0115.000`，`AML.M0008` 直接指向 `AML.T0018.000`、`AML.T0020`、`AML.T0115.001`，`AML.M0005` 直接指向 `AML.T0020`。一条 mitigation 可以同时指向多个 technique，一条 technique 也可以被多条 mitigation 指向。

攻击侧内部也全部是直接关系：`achieves` 把技术挂到战术（`AML.T0051` LLM Prompt Injection achieves `AML.TA0005` Execution），`specializes` 把子技术挂到父技术（`AML.T0051.000` Direct specializes `AML.T0051`）。case study 同样直接 `employs` 技术：`AML.CS0000` 依次 employs `AML.T0000.001`、`AML.T0002.000`、`AML.T0005`、`AML.T0043.003`、`AML.T0042`、`AML.T0015`，每条关系带 `tactic`（如 `AML.TA0002`）、`step-id`（`S00` 到 `S05`）与 `leads-to`（如 `S00 -> S01`，最后一步 `leads-to: []`），从而把案例串成一条有序攻击链。

关系的存放位置有两处：顶层 `relationships` 以源对象 ID 为键分组（资料示例中有 `ATLAS-matrix`、`AML.T0005`、`AML.M0001`、`AML.CS0001` 等键），mitigation 条目内部也内嵌 `relationships.mitigates` 数组。资料未说明这两处如何保持同步。

`mitigates` 与 `employs` 的关系对象自带 `description`，用来写"为什么这条缓解措施能缓解这个技术"，例如 `AML.M0008 -> AML.T0018.000` 的理由是"Ensure that trained models do not respond to potential backdoor triggers or adversarial influence."。

## 5. 抽象层次的选择

战术这一层写的是**目的**：每条 tactic 的描述都表述为对手意图，例如 `AML.TA0002` Reconnaissance 是"The adversary is trying to gather information about the AI system they can use to plan future operations."，`AML.TA0004` Initial Access 是"The adversary is trying to gain access to the AI system."。

技术这一层写的是**行为**：做什么、通过什么方式做，而不是具体工具或代码。子技术写的是同一行为下更具体的**变体或手段**。这一点在 `AML.T0043` Craft Adversarial Data 上最清楚：它下面拆分出 `AML.T0043.000` White-Box Optimization、`.001` Black-Box Optimization、`.002` Black-Box Transfer、`.003` Manual Modification、`.004` Insert Backdoor Trigger；`AML.T0018` Manipulate AI Model 则拆出 `.000` Poison AI Model、`.001` Modify AI Model Architecture、`.002` Embed Malware、`.003` Modify Prompt Construction Logic。也就是说，**新条目的判定标准是"是不是同一行为下的另一种实现手段"**：是，就用 `specializes` 做子技术；不是同一行为，就另开技术编号。

缓解措施这一层写的是**措施加治理属性**：一段自由文本描述，加上 `lifecycle-phases` 与 `categories` 两个分类维度；具体实现细节用散文给出建议（`AML.M0002` 的关系描述里出现过"Suggested approaches: - Restrict the number of results shown - Limit specificity of output class ontology - Use randomized smoothing techniques - Reduce the precision of numerical outputs"）。案例这一层写的是**具体事件**：带 `actor`、`target`、`date`、`date-granularity`、`type`。

资料中能看到几条明确的**归类边界规则**：战术 `AML.TA0001` 的正文显式区分 Resource Development 与 AI Attack Adaptation——前者"creates or obtains reusable capabilities"，后者把能力"applies or modifies … for a target, objective, or current operational condition"；技术 `AML.T0099` AI Agent Tool Data Poisoning 的正文说明同一行为在不同条件下"may also constitute Prompt Infiltration via Public-Facing Application"、"may instead constitute Drive-by Compromise"，而"malicious or compromised tool that deliberately alters its own runtime result"则属于 `AML.T0110.002`；`AML.T0110` 的正文进一步写明，仅仅把 agent 工具包当作传统恶意软件投递载体的软件"may be better described as a malicious package or software supply-chain compromise rather than AI Agent Tool Poisoning"。

**资料未说明收录的准入标准**（例如需要什么证据、谁审核、是否要求公开案例）。一个可观察到的事实是：成熟度为 `Feasible` 的条目也被收录（如 `AML.T0000.000`、`AML.T0099`、`AML.T0110.002`、`AML.T0134`），所以成熟度本身不构成收录门槛；但这是观察，不是资料声明。

## 6. 稳定部分与易变部分

框架希望**很少变**的是骨架与本体：`format-version` 所代表的格式版本（语义化版本，示例 `6.0.0`）、8 个顶层键、被格式强制的 typed ID patterns、`object-type` 的取值、5 种关系类型的名称与方向、以及 `collection` 与 `matrix` 两个单例及其固定 ID（`ATLAS-collection`、`ATLAS-matrix`）。`attack-reference` 这类到外部框架的外链字段也属于稳定的对齐结构。

框架**预期不断增长**的是条目本身：资料明确写"ATLAS releases monthly content updates"（月度内容更新）。2026.09 的规模是 tactics 16、techniques 208、mitigations 40、case-studies 73、relationships 322。每个条目的 `description`、`references` 与 `modified-date` 也会持续变化——例如战术 `AML.TA0001` 创建于 `2021-05-13`、修改于 `2026-08-31`，ID 不变而正文演进。

版本管理采用**双轨制**：内容版本放在 `collection.version`，遵循 YYYY.MM.N（示例 `2026.05`）；格式版本放在 `format-version`，遵循语义化版本（示例 `6.0.0`）。README 特别注明"separating content from format versions started with 2026.05 / 6.0.0. Previously content and format changes followed combined SEMVER versioning."（内容与格式版本分离从 2026.05 / 6.0.0 开始，此前两者合并为同一套 SEMVER）。`dist/manifest.yaml` 把两者绑定：它列出每个内容发布由哪个文件路径实现哪个格式版本。

废弃流程方面，资料明确写了文件级废弃：`dist/ATLAS.yaml` is deprecated and will no longer be updated。历史内容的处理方式是迁移与冻结并存：`dist/v6/ATLAS-{version}.yaml` 保存迁移到 v6 格式的历史版本，`dist/legacy/ATLAS-{version}.yaml` 保存发布当时的原始格式，`dist/v6/ATLAS-latest.yaml` 始终指向 v6 格式下的最新内容，`dist/ATLAS-latest.yaml` 始终指向最新格式下的最新内容。**条目级的新增、废弃、合并流程，资料未说明**；每个条目只有 `created-date` / `modified-date` 可供追溯，没有"已废弃"状态字段。

## 7. 内容与执行的分离

知识内容以**数据文件**形式存放：`dist/ATLAS-latest.yaml` 是最新数据，另有 `dist/v6/…` 与 `dist/legacy/…` 的历史文件，`dist/manifest.yaml` 是发布清单。格式本身由 Python 包中的 Pydantic 模型描述，README 写明"Current distributable ATLAS format is represented by `atlas.schemas.AtlasExport`"，使用方式是 `atlas_data = AtlasExport.model_validate(raw)`。

**解释与执行者**有四个：Pydantic 做解析与校验；FastAPI 写的 REST API 负责管理数据（从 v6 YAML 导入、通过 API 调用修改、导出发布），后端是 SQLite 数据库 `sqlite:///./atlas.db`，导入用 `populate-atlas-db -i <yaml>`；命令行工具把内容转换成下游格式——`atlas-to-stix`（可加 `--include-attack` 合入 ATT&CK Enterprise、`--include-case-studies`、`--maturity-threshold {feasible,demonstrated,realized}`）、`atlas-to-excel`、`generate-navigator-layers`（面向 ATT&CK Navigator 5.3.2、layer format 4.5、自定义 `atlas-atlas` domain）。

**内容能表达的逻辑上限**：能表达的是分类、归属、映射、理由、外部引用、成熟度与适用范围标签，以及案例的步骤序列（`step-id` + `leads-to`）。不能表达的是任何可执行语义——关系类型只有固定 5 种；缓解措施的具体做法只是自然语言（包括"Suggested approaches:"清单）；没有条件判断、阈值、参数、时序、效力大小的表达方式；`platforms`、`categories`、`lifecycle-phases` 都只是标签而不是逻辑。**超出时的处理方式，资料未说明**——资料只说明可以导出成 STIX、Excel、Navigator 图层，交给外部工具消费，但没有说明如何扩展关系类型或如何把不可表达的语义放进现有字段。

## 8. 覆盖与成熟度的表达

"某个技术有没有被覆盖"的表达方式是**有没有 `mitigates` 关系**：一条 mitigation 直接指向一条 technique，就表示这条措施覆盖它。资料中的 40 条 mitigation 与 322 条关系构成了这张映射网，但这是二值的"有关系/没关系"。**资料未说明**任何覆盖度分数、覆盖百分比、状态字段或分级。

覆盖的呈现靠导出物：Excel 工作簿，以及 ATT&CK Navigator 图层（"Generated layers target ATT&CK Navigator 5.3.2, layer format 4.5, and the custom `atlas-atlas` domain used by the ATLAS Navigator."），矩阵内战术的排列顺序由 `sequences` 决定。

"某个条目有多成熟"主要靠 technique 上的 `maturity` 字段，观察到 `Feasible`、`Demonstrated`、`Realized` 三档，并可在导出 STIX 时用 `--maturity-threshold {feasible,demonstrated,realized}` 过滤。**资料未说明这三档的定义、判定依据与维护流程**；mitigation 与 case-study 没有成熟度字段；资料也未说明缓解措施之间、案例之间如何比较成熟度。

"依据是什么"主要靠三类字段：technique 与 tactic 的 `references`（如 `AML.T0110.000` 列出 `invariant-tool-poisoning`、`mcp-tools`、`owasp-tool-poisoning` 三条来源）；case-study 的 `actor`、`target`、`date`、`type`；以及 `mitigates` 关系上的 `description` 理由文本。资料未说明是否存在独立的质量评分或审核状态。

## 9. 对我们的启发

分析：ATLAS 把"内容版本"（`collection.version`，YYYY.MM.N）与"格式版本"（`format-version`，SEMVER）分开，并用 `dist/manifest.yaml` 把每个内容发布映射到实现某格式版本的文件。这一项可以直接用于我们的 knowledge_base 层：方法插件会随论文不断新增（内容），而插件接口与元数据 schema 必须稳定（格式）；两者分开版本化后，新增一篇论文不必升 schema，改 schema 也不会丢历史方法记录，manifest 还能导出"某格式版本 + 某方法集版本"的可复现快照。

分析：ATLAS 用类型化 ID（`AML.T####`）与子条目后缀（`AML.T####.###`）区分"新条目"与"已有条目的变体"，并用 `specializes` 表达归属。这一项可以改造后用于 methods 层：给每个防御方法稳定 ID（例如 `DEF.M####`），同族方法（同一论文的不同超参、同一算子的不同实现）作为子条目，而不是每来一个变体就新增一条"论文条目"；但我们的变体判定依据是数值行为与威胁模型，不是对手行为，所以拆分维度需要自己定义，不能照抄它的"手段不同即子技术"。

分析：ATLAS 的关系是显式、带类型的一等数据，而且 `mitigates` 与 `employs` 的关系对象自带 `description` 说明理由。这一项可以直接用于 methods 层与 knowledge_base 层：把"某方法缓解哪类攻击""作用于哪个暴露点""与哪个算子冲突"从正文散文提升为可查询的关系数据，并强制写理由；这正是我们目前"说不清覆盖了什么"的直接解药。

分析：ATLAS 让防御对象**直接**指向攻击对象（`mitigates`: mitigation -> technique），不引入中间检测对象。这一项只适合改造后使用：我们确实不需要日志匹配式的中间层，但我们的防御是数值算法，一个方法往往只在特定暴露点（11 个位置之一）和特定威胁模型下有效，单纯的二值"方法→威胁"会丢掉前置条件；应当把 runtime 的 11 个位置做成显式的适用范围维度（类似 `platforms` 这样的标签字段），而不是新造一个中间对象。

分析：ATLAS 用 `maturity` 三档标注技术，并在导出时用 `--maturity-threshold` 过滤。这一项的**分级思路**可用于 methods 层与 evaluation 层，但不能照搬标签：资料未说明三档的定义与判定依据，直接抄"Feasible/Demonstrated/Realized"会得到不可复现的成熟度；我们需要自己写判定标准（例如"论文声明 / 第三方复现 / 在我们 runtime 上可部署"），并把它绑定到 evaluation 层的实验记录。

分析：ATLAS 给缓解措施加了 `lifecycle-phases` 与 `categories` 两个分类维度，而不是只按来源出处组织。这一项可以直接用于 knowledge_base 层与 methods 层：把方法按"作用于 11 个运行时位置中的哪一个"和"属于哪类算子（聚合、裁剪、采样、加噪等）"打标签，方法层就不再只是论文清单。

分析：ATLAS 把内容（YAML 数据文件）与执行（schema 校验、REST API、导出工具）分离，内容由 Pydantic 模型校验，由 API 与 CLI 工具解释和转换。这一项可以改造后用于 knowledge_base 层与 records 层：元数据用数据文件存放并做 schema 校验、发布走集中登记与导出快照，这个分层可以直接用；但 ATLAS 的内容本身只是散文建议，没有可执行语义，而我们的插件必须带算子契约（输入张量形状、超参、随机性、挂载点、对聚合的影响），这部分 schema 要我们自己设计，ATLAS 没有对应设计可借。

分析：ATLAS 冻结历史发布文件（`dist/v6/ATLAS-{version}.yaml`、`dist/legacy/ATLAS-{version}.yaml`）并显式标记废弃（`dist/ATLAS.yaml` deprecated）。这一项可以直接用于 records 层：要能回答"三个月前那次联邦训练用的是哪一版防御组合"，就必须保留发布快照与废弃标记，而不是只留一个持续覆盖的 latest 文件。

分析：ATLAS 的 case study 用 `employs` 关系加 `tactic`、`step-id`、`leads-to` 把攻击过程写成有序步骤链。这一项可以改造后用于 evaluation 层：评测用例可以借用"步骤化剧本"的结构（用例、所用方法、挂载的暴露点、前后步骤），但 ATLAS 的步骤是为叙事型案例服务的，我们需要的是可执行脚本 ID 与可复现实验记录（数据分布、随机种子、客户端数量），因此只能借结构、不能借字段语义。

分析：ATLAS 用 `attack-reference`（`id`/`url`）外链到 ATT&CK，而不是复制对方条目。这一项可以直接用于 knowledge_base 层：我们不必自造全部威胁词汇，可以保留到既有攻防框架、标准或法规的外链字段，减少命名体系维护成本。

分析：**不能照搬** ATLAS 以攻击为中心的矩阵结构（`matrix -> tactic -> technique`，防御只能挂在 technique 上）。原因是我们的库以防御方法与算子为一等公民；如果照搬，方法层会退化成"挂在攻击节点上的论文清单"，仍然说不清库自身的结构。我们应当反过来以方法/算子为主键，把攻击面与暴露点作为可挂接标签，或至少做成双向关系。

分析：**不能照搬** ATLAS 用"关系有无 + 矩阵图层着色"表达覆盖的做法。原因是 ATLAS 只有二值映射，没有覆盖度、效力与前置条件；而我们的防御是数值算法，覆盖情况必须用精度、鲁棒性、通信开销、失效条件等度量表达，条目的有/无替代不了实验证据——这正好对应我们 evaluation 层需要自己发明的部分。

## 10. 框架自己承认的局限

**资料中明确写到的限制与权衡：**

- `AML.M0037`（AI Agent Authority Expansion Controls）的关系描述明确写：这些控制不约束组织没有管理权的、由对手控制的 AI 系统（"These controls do not constrain reconnaissance performed by adversary-controlled AI systems over which the organization has no administrative control."）。
- `AML.M0038`（AI Agent Scope Drift Detection）同样明确写：该控制不适用于组织没有管理权的、由对手控制的 AI 系统，并重复了三次这一限定。
- `AML.M0029`（Human In-the-Loop for AI Agent Actions）明确承认权衡："The security benefits from Human In-the-Loop policies may be at odds with operational overhead costs of additional approvals."。
- 文件层面承认了废弃：`dist/ATLAS.yaml` is deprecated and will no longer be updated。
- 版本口径承认了历史不一致：内容与格式版本分离从 2026.05 / 6.0.0 才开始，此前两者使用合并的 SEMVER。

**资料中可见、但资料本身未说明其性质的问题：**

- 条目归类存在重叠与歧义。`AML.T0099` 用"may also constitute"、"may instead constitute"来把相近行为分流到 `AML.T0093`、`AML.T0078`、`AML.T0110.002`；`AML.T0110` 也用"may be better described as … rather than"来排除误归类。这说明边界并非总是清晰，但资料未说明维护者如何裁决这类重叠。
- 资料未说明 `maturity` 三档的定义、判定依据与更新责任人。
- 资料未说明技术条目的收录准入标准，也未说明条目合并、拆分或废弃的流程。
- 资料中出现内部命名不一致：战术 `AML.TA0003` 的描述把 `AML.TA0001` 称作"AI Attack Staging"，而 `AML.TA0001` 的 `name` 是"AI Attack Adaptation"；资料未说明这是遗留文本还是错误。
- 资料未说明 `uuid` 的生成规则与跨版本稳定性保证，也未说明关系在顶层 `relationships` 与对象内嵌 `relationships` 两处如何同步。
- 资料未说明覆盖度如何量化，也未说明是否存在缓解措施的质量或成熟度评估。

## 11. 原文依据

以下引句均从资料中逐字复制，括号内为按空白切分的英文单词数。

1. 支撑第 2 节"对象类型由 8 个顶层键界定，资料中没有检测/数据源类对象"：
> Current distributable ATLAS format is represented by `atlas.schemas.AtlasExport`.
>
> Top-level keys:
>
> - `format-version`
> - `collection`
> - `matrix`
> - `tactics`
> - `techniques`
> - `mitigations`
> - `case-studies`
> - `relationships`
（18 个单词）

2. 支撑第 3 节"编号格式由格式层强制，且存在子技术后缀"：
> The format enforces typed ID patterns, including:
>
> - Collection ID: `ATLAS-collection`
> - Matrix ID: `ATLAS-matrix`
> - Tactic ID: `AML.TA####`
> - Technique ID: `AML.T####`
> - Sub-technique ID: `AML.T####.###`
> - Mitigation ID: `AML.M####`
> - Case study ID: `AML.CS####`
（29 个单词）

3. 支撑第 4 节"关系类型只有 5 种、方向固定，且 employs 带附加元数据"：
> ATLAS object relationships are explicit and typed:
>
> - `sequences`: matrix -> tactic (ordered matrix layout)
> - `achieves`: technique -> tactic
> - `specializes`: sub-technique -> parent technique
> - `mitigates`: mitigation -> technique
> - `employs`: case study -> technique (includes `tactic`, `step-id`, `leads-to` metadata)
（32 个单词）

4. 支撑第 4 节"防御对象直接以 mitigates 指向攻击对象，且关系自带 description 理由"：
>     - source: AML.M0007
>       target: AML.T0115
>       relationship-type: mitigates
>       description: Dataset repositories inspect submissions and quarantine poisoned samples, labels, annotations, or metadata before listing.
（21 个单词）

5. 支撑第 5 节"战术之间的边界被显式写清（可复用能力 vs 针对目标适配）"：
> Resource Development creates or obtains reusable capabilities whereas [AI Attack Adaptation](/tactics/AML.TA0001) applies or modifies those capabilities for a target, objective, or current operational condition.
（24 个单词）

6. 支撑第 5 节"同一行为可能同时构成另一个条目，归类边界有明确规则"：
> When the adversary introduces the content through a victim-controlled public-facing application, the activity may also constitute [Prompt Infiltration via Public-Facing Application](/techniques/AML.T0093).
（21 个单词）

7. 支撑第 6 节"内容按月增长，内容版本用 YYYY.MM.N"：
> ATLAS releases monthly content updates. It follows two versioning schemes:
>
> - **Content version**: data content version in `collection.version` that follows YYYY.MM.N versioning (e.g. `2026.05`).
（23 个单词）

8. 支撑第 7 节"内容由 API 导入、修改、导出，内容与执行分离"：
> The REST API is designed to manage the ATLAS data. Data can be imported from a v6 ATLAS YAML file, modified via calls the the API, and exported for distribution.
（30 个单词；原文"calls the the API"为原样复制）

9. 支撑第 8 节"成熟度分三档并可在导出时按阈值过滤"：
> Generate ATLAS STIX:
>
> ```bash
> uv run tools/atlas_to_stix.py -i dist/v6/ATLAS-2026.05.yaml -o dist/stix-atlas.json
> ```
>
> Other options:
> - `--include-case-studies`
> - `--maturity-threshold {feasible,demonstrated,realized}`
（18 个单词）

10. 支撑第 8 节"覆盖通过 Navigator 图层等导出物呈现"：
> Generated layers target ATT&CK Navigator 5.3.2, layer format 4.5, and the
> custom `atlas-atlas` domain used by the ATLAS Navigator.
（19 个单词）

```json
{
  "key": "atlas",
  "framework": "MITRE ATLAS (Adversarial Threat Landscape for AI Systems) 的 atlas-data 数据仓库；格式版本 6.0.0，内容版本 2026.09（README 示例另提到 2026.05 / 6.0.0）",
  "object_types": [
    {
      "name": "collection",
      "role": "other",
      "fields": ["name", "description", "references", "created-date", "modified-date", "version", "id", "uuid", "object-type"]
    },
    {
      "name": "matrix",
      "role": "other",
      "fields": ["name", "description", "references", "created-date", "modified-date", "id", "uuid", "object-type"]
    },
    {
      "name": "tactic",
      "role": "attack",
      "fields": ["name", "description", "references", "created-date", "modified-date", "attack-reference", "id", "uuid", "object-type"]
    },
    {
      "name": "technique",
      "role": "attack",
      "fields": ["name", "description", "references", "created-date", "modified-date", "platforms", "id", "maturity", "uuid", "object-type"]
    },
    {
      "name": "mitigation",
      "role": "defense",
      "fields": ["name", "lifecycle-phases", "categories", "description", "relationships", "id", "object-type"]
    },
    {
      "name": "case-study",
      "role": "artifact",
      "fields": ["name", "description", "references", "created-date", "modified-date", "type", "actor", "target", "date", "date-granularity", "id", "uuid", "object-type"]
    },
    {
      "name": "relationship",
      "role": "relation",
      "fields": ["source", "target", "relationship-type", "description", "tactic", "step-id", "leads-to"]
    }
  ],
  "id_scheme": "格式强制类型化 ID：Collection 为 ATLAS-collection；Matrix 为 ATLAS-matrix；Tactic 为 AML.TA####；Technique 为 AML.T####；Sub-technique 为 AML.T####.###（后缀从 .000 起）；Mitigation 为 AML.M####；Case study 为 AML.CS####；每个对象另有 uuid。",
  "attack_defense_link": "direct",
  "link_detail": "mitigates 关系直接以 mitigation 为 source、technique 为 target，没有检测规则、数据源或映射表之类的中间对象；case study 也直接 employs technique 并附带 tactic、step-id、leads-to 元数据。资料中没有 data source、detection、analytics、rule、test 对象。",
  "abstraction_level": "战术写目的（描述均为 The adversary is trying to…）；技术写行为；子技术写同一行为下更具体的实现手段与变体，用 specializes 挂到父技术；缓解措施写措施加生命周期阶段与类别，做法用自然语言建议表达；案例写带 actor、target、date 的具体事件并串成步骤链。资料未说明收录准入标准，且 Feasible 级条目已被收录，说明成熟度不是门槛。",
  "stable_parts": ["format-version（语义化格式版本）", "8 个顶层键结构", "被格式强制的 typed ID patterns", "object-type 取值", "5 种关系类型名称与方向", "collection 与 matrix 两个单例及其固定 ID", "attack-reference 到 ATT&CK 的外链字段"],
  "growing_parts": ["tactics（2026.09 为 16 条）", "techniques 与子技术（208 条）", "mitigations（40 条）", "case-studies（73 条）", "relationships（322 条）", "各条目的 description、references 与 modified-date"],
  "content_format": "YAML 数据文件（dist/ATLAS-latest.yaml、dist/v6/ATLAS-latest.yaml、dist/v6/ATLAS-{version}.yaml、dist/legacy/ATLAS-{version}.yaml），由 dist/manifest.yaml 作为发布清单；格式由 Python Pydantic 模型 atlas.schemas.AtlasExport 定义。",
  "execution_engine": "没有规则或检测执行引擎。解释者是 Pydantic 校验（AtlasExport.model_validate）、FastAPI REST API 加 SQLite（sqlite:///./atlas.db）、populate-atlas-db 导入工具，以及 atlas-to-stix、atlas-to-excel、generate-navigator-layers 等下游格式生成工具。",
  "coverage_expression": "用 mitigates 关系的有无表示某条 mitigation 覆盖了哪些 technique（二值），矩阵布局由 matrix 的 sequences 排序决定，覆盖以 Excel 工作簿与 ATT&CK Navigator 图层（layer format 4.5、domain atlas-atlas）呈现；资料未说明覆盖度分数、覆盖状态字段或量化指标。",
  "maturity_expression": "technique 上的 maturity 字段，观察到 Feasible、Demonstrated、Realized 三档，并可在 STIX 导出时用 --maturity-threshold {feasible,demonstrated,realized} 过滤；资料未说明三档的定义与判定依据，mitigation 与 case-study 没有成熟度字段。",
  "lessons": [
    {
      "idea": "把内容版本与格式版本分开，并用 manifest 把每次内容发布映射到实现某格式版本的文件",
      "applies_to": "knowledge_base",
      "transfer": "direct",
      "why": "方法插件会持续随论文增加（内容），而插件接口与元数据 schema 必须稳定（格式）；分开版本化后新增方法不必升 schema，改 schema 也不会丢历史方法记录，manifest 还能导出可复现的库快照。"
    },
    {
      "idea": "用类型化 ID 加子条目后缀表达层级与变体（AML.T#### 与 AML.T####.###）",
      "applies_to": "methods",
      "transfer": "adapted",
      "why": "可以给每个防御方法稳定 ID，把同族变体作为子条目而不是每篇论文新开条目；但我们的变体依据是数值行为与威胁模型，需要自定义拆分维度，不能照抄其手段式拆分标准。"
    },
    {
      "idea": "关系是显式、带类型的一等数据，且关系自身带 description 说明理由",
      "applies_to": "methods",
      "transfer": "direct",
      "why": "把方法缓解哪类攻击、作用于哪个暴露点、与哪个算子冲突从正文散文提升为可查询关系，并强制写理由，才能回答库到底覆盖了什么。"
    },
    {
      "idea": "防御对象直接指向攻击对象，不引入中间检测对象（mitigates: mitigation -> technique）",
      "applies_to": "methods",
      "transfer": "adapted",
      "why": "我们同样不需要中间层，但数值算法只在特定暴露点与威胁模型下有效，二值的方法到威胁映射会丢前置条件，应把 runtime 的 11 个位置做成显式适用范围维度。"
    },
    {
      "idea": "用成熟度分级并在导出时按阈值过滤（maturity 与 --maturity-threshold）",
      "applies_to": "methods",
      "transfer": "adapted",
      "why": "分级与过滤的机制可用，但资料未说明三档的定义与判定依据，直接照抄会得到不可复现的成熟度标签；必须在 evaluation 层自定义判定标准。"
    },
    {
      "idea": "给缓解措施加 lifecycle-phases 与 categories 两个分类维度",
      "applies_to": "knowledge_base",
      "transfer": "direct",
      "why": "对应到我们按 11 个运行时位置与算子类别给方法打标签，使方法层不再只按论文出处组织。"
    },
    {
      "idea": "内容以 YAML 加 schema 存放与校验，编辑走 API，发布走导出工具",
      "applies_to": "knowledge_base",
      "transfer": "adapted",
      "why": "元数据文件加 schema 校验加多目标导出的分层可以借鉴；但 ATLAS 的内容只是散文建议，无可执行语义，我们的插件必须额外记录算子契约（输入形状、超参、随机性、挂载点），schema 要自行设计。"
    },
    {
      "idea": "冻结历史发布文件并显式标记废弃（dist/v6、dist/legacy、dist/ATLAS.yaml deprecated）",
      "applies_to": "records",
      "transfer": "direct",
      "why": "要能追溯某次联邦训练使用的防御组合，必须保留发布快照与废弃标记，而不能只维护一个 latest 文件。"
    },
    {
      "idea": "案例用 employs 关系加 tactic、step-id、leads-to 串成有序步骤链",
      "applies_to": "evaluation",
      "transfer": "adapted",
      "why": "评测用例可以借用步骤化剧本结构；但叙事型案例的字段语义不能直接复用，我们需要可执行脚本 ID 与可复现实验记录。"
    },
    {
      "idea": "用 attack-reference（id/url）外链到既有框架而不是复制对方条目",
      "applies_to": "knowledge_base",
      "transfer": "direct",
      "why": "防御库不必自造全部威胁词汇，保留到既有攻防框架、标准或法规的外链字段可降低命名体系维护成本。"
    },
    {
      "idea": "以攻击为中心的矩阵结构（matrix -> tactic -> technique，防御挂在 technique 上）",
      "applies_to": "methods",
      "transfer": "not_transferable",
      "why": "我们的库以防御方法与算子为一等公民，照搬会让方法层退化成挂在攻击节点上的论文清单，仍然说不清库自身结构，需要以方法或算子为主键或做双向关系。"
    },
    {
      "idea": "用关系有无与矩阵图层着色表达覆盖",
      "applies_to": "evaluation",
      "transfer": "not_transferable",
      "why": "ATLAS 只有二值映射，没有覆盖度、效力与前置条件；我们的防御是数值算法，覆盖必须用精度、鲁棒性、开销等度量表达，条目着色替代不了实验证据。"
    }
  ],
  "limits": [
    "资料明确写到 AML.M0037 的权限扩展控制不约束组织没有管理权的、由对手控制的 AI 系统。",
    "资料明确写到 AML.M0038 的范围漂移检测不适用于组织没有管理权的、由对手控制的 AI 系统。",
    "资料明确写到 AML.M0029 的人在环路安全收益可能与额外审批带来的运营开销相冲突。",
    "资料明确写到 dist/ATLAS.yaml 已废弃并不再更新。",
    "资料明确写到内容与格式版本分离从 2026.05 / 6.0.0 才开始，此前使用合并的 SEMVER。",
    "资料未说明 maturity 三档的定义、判定依据与维护责任人。",
    "资料未说明技术条目的收录准入标准，也未说明条目合并、拆分或废弃的流程。",
    "资料未说明覆盖度如何量化，也没有覆盖状态或缓解措施成熟度字段。",
    "资料中归类边界存在重叠，AML.T0099 与 AML.T0110 用 may also constitute、may instead constitute、may be better described as 来分流，资料未说明裁决机制。",
    "资料中存在内部命名不一致：AML.TA0003 描述把 AML.TA0001 称为 AI Attack Staging，而该条目 name 为 AI Attack Adaptation，资料未说明原因。",
    "资料未说明 uuid 的生成规则与跨版本稳定性，也未说明关系在顶层与对象内嵌两处如何保持同步。",
    "资料中 mitigations 的 description 被截到 500 字符，完整内容不可见。"
  ],
  "quotes": [
    {
      "supports": "第 2 节：对象类型由 8 个顶层键界定，资料中没有检测或数据源类对象",
      "text": "Current distributable ATLAS format is represented by `atlas.schemas.AtlasExport`.\n\nTop-level keys:\n\n- `format-version`\n- `collection`\n- `matrix`\n- `tactics`\n- `techniques`\n- `mitigations`\n- `case-studies`\n- `relationships`"
    },
    {
      "supports": "第 3 节：编号格式由格式层强制，且存在子技术后缀",
      "text": "The format enforces typed ID patterns, including:\n\n- Collection ID: `ATLAS-collection`\n- Matrix ID: `ATLAS-matrix`\n- Tactic ID: `AML.TA####`\n- Technique ID: `AML.T####`\n- Sub-technique ID: `AML.T####.###`\n- Mitigation ID: `AML.M####`\n- Case study ID: `AML.CS####`"
    },
    {
      "supports": "第 4 节：关系类型只有 5 种、方向固定，且 employs 带 tactic、step-id、leads-to 元数据",
      "text": "ATLAS object relationships are explicit and typed:\n\n- `sequences`: matrix -> tactic (ordered matrix layout)\n- `achieves`: technique -> tactic\n- `specializes`: sub-technique -> parent technique\n- `mitigates`: mitigation -> technique\n- `employs`: case study -> technique (includes `tactic`, `step-id`, `leads-to` metadata)"
    },
    {
      "supports": "第 4 节：防御对象直接以 mitigates 指向攻击对象，且关系自带 description 理由",
      "text": "    - source: AML.M0007\n      target: AML.T0115\n      relationship-type: mitigates\n      description: Dataset repositories inspect submissions and quarantine poisoned samples, labels, annotations, or metadata before listing."
    },
    {
      "supports": "第 5 节：战术之间的边界被显式写清，可复用能力与针对目标的适配被区分",
      "text": "Resource Development creates or obtains reusable capabilities whereas [AI Attack Adaptation](/tactics/AML.TA0001) applies or modifies those capabilities for a target, objective, or current operational condition."
    },
    {
      "supports": "第 5 节：同一行为可能同时构成另一个条目，归类边界有明确规则",
      "text": "When the adversary introduces the content through a victim-controlled public-facing application, the activity may also constitute [Prompt Infiltration via Public-Facing Application](/techniques/AML.T0093)."
    },
    {
      "supports": "第 6 节：内容按月增长，内容版本使用 YYYY.MM.N",
      "text": "ATLAS releases monthly content updates. It follows two versioning schemes:\n\n- **Content version**: data content version in `collection.version` that follows YYYY.MM.N versioning (e.g. `2026.05`)."
    },
    {
      "supports": "第 7 节：内容可经 API 导入、修改与导出，内容与执行分离",
      "text": "The REST API is designed to manage the ATLAS data. Data can be imported from a v6 ATLAS YAML file, modified via calls the the API, and exported for distribution."
    },
    {
      "supports": "第 8 节：成熟度分三档并可在导出时按阈值过滤",
      "text": "Generate ATLAS STIX:\n\n```bash\nuv run tools/atlas_to_stix.py -i dist/v6/ATLAS-2026.05.yaml -o dist/stix-atlas.json\n```\n\nOther options:\n- `--include-case-studies`\n- `--maturity-threshold {feasible,demonstrated,realized}`"
    },
    {
      "supports": "第 8 节：覆盖通过 Navigator 图层等导出物呈现",
      "text": "Generated layers target ATT&CK Navigator 5.3.2, layer format 4.5, and the\ncustom `atlas-atlas` domain used by the ATLAS Navigator."
    }
  ]
}
```
