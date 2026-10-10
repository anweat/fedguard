# attack：MITRE ATT&CK: Design and Philosophy（2018 年 7 月首发、2020 年 3 月修订，含 sub-techniques）与 mitre/cti USAGE.md（STIX 表示）

资料版本说明：Design and Philosophy 一文自述为 "the published version of ATT&CK as of March 2020 with the addition of sub-techniques"，并声明自己会作为 living document 随重大变化更新；USAGE.md 声明已把 STIX 2.0 与 STIX 2.1 表示统一为单一规范，并把对象类型、字段与关系的完整说明转交给 ATT&CK Data Model Specification（该规范本身未包含在本资料中）。

## 1. 要解决的问题

这个框架面向三类使用者：私营部门、政府，以及网络安全产品与服务社区；其自述定位是 "a globally-accessible knowledge base of adversary tactics and techniques based on real-world observations"，用作构建具体威胁模型与方法论的基础。它起源于 MITRE FMX 研究环境中做结构化对手仿真（adversary emulation）的需要：当时的目标是系统化地归类对手行为，并用这些信息在受监控环境中开展受控演练，其首要成功指标是 "How well are we doing at detecting documented adversary behavior?"。它在同一份知识库上同时服务攻击方与防御方，自称提供 "a common taxonomy for both offense and defense"，并把使用场景明确列为 Adversary Emulation、Red Teaming、Behavioral Analytics Development、Defensive Gap Assessment、SOC Maturity Assessment、Cyber Threat Intelligence Enrichment 六类。它还承担方法论的示范作用：Executive Summary 说明该文既是对 ATT&CK 的权威说明，也是把 ATT&CK methodology 应用到新领域、创建新知识库的指南。

它明确说自己不做的事包括：**不做软件攻击向量的穷举**（"ATT&CK is not an exhaustive enumeration of attack vectors against software"，软件漏洞类场景应由 CAPEC 与 CWE 承担）；**不是待办清单**（"is not intended to provide a checklist of things that need to all be addressed"）；**不以 100% 覆盖为目标**（覆盖全部技术、覆盖某个技术的全部 procedures 都被称为不现实）；**不背书任何厂商方案**（检测与缓解建议须保持 vendor agnostic）；**不用于归因**（"it is not recommended to attribute activity solely based on the ATT&CK techniques used"，归因需要 Diamond Model 的全部要素）；**不接受泄露或机密信息**作为威胁情报依据。此外它聚焦于外部对手如何入侵并在计算机网络内活动，ICS 领域的哲学问题资料说明将另文处理。

## 2. 核心对象

Design and Philosophy 把知识库中的条目统称为 object，并规定 object 是 "any item in the knowledge base that can have a relationship with another object"。资料的表格对每个字段标注了三种类型：**tag**（可供过滤与 pivot 的信息性引用）、**field**（描述性自由文本）、**relationship**（与其他对象实体的关联字段）；带 `*` 表示必填。资料中出现的对象类型如下。资料未出现以 rule、test、artifact、event 命名的对象类型，这些对象是否存在，**资料未说明**。

**Tactic（战术）**——代表对手的战术目标，即 "why"。它是技术的上下文类别，在 ATT&CK 中被当作 tag 使用：一个 (sub-)technique 可按其能达成的不同结果被标注一个或多个战术。每个战术含一段定义文字，用来界定哪些技术应归入该战术（例如 Execution 被定义为 "represents (sub-)techniques that result in execution of adversary-controlled code on a local or remote system"）。在 STIX 表示中，战术是独立对象 `x-mitre-tactic`，其 `x_mitre_shortname` 被技术的 `kill_chain_phases.phase_name` 引用。战术对象的完整字段清单、必填性与取值约束，**资料未说明**。

**Technique（技术）与 Sub-Technique（子技术）**——按资料 Table 2 "ATT&CK Technique and Sub-Technique Model"，字段为：Name\*（Field，名称，必填）；ID\*（Tag，知识库内唯一标识，必填，格式 technique 为 `T####`、sub-technique 为 `T####.###`）；Sub-Techniques\*（Field，该技术下的子技术 ID，必填，但 "Only applies to techniques and not sub-techniques"）；Tactic\*（Tag，可达成的一个或多个战术目标，必填）；Description\*（Field，说明是什么、典型用途、对手如何利用及其变体，并要求附权威技术文章引用与野外使用引用，必填）；Platform\*（Tag，对手所操作的系统，可为操作系统或应用，可多个，必填）；System Requirements（Field，对手需满足的条件或系统状态如软件与补丁级别，非必填）；Permissions Required\*（Tag，执行所需最低权限级别，资料注明 "\*Required for privilege escalation"）；Effective Permissions\*（Tag，执行后获得的权限级别，仅适用于 privilege escalation 战术下的条目，可多条，资料注明 "\*Required for privilege escalation"）；Data Source\*（Tag，传感器或日志系统采集的信息来源，必填，且 "intended to be restricted to a defined list"，以便按独特数据源分析覆盖）；Supports Remote（Tag，能否在远程系统执行，仅适用于 execution 类条目，非必填）；Defense Bypassed\*（Tag，能否绕过某项防御工具、方法或流程，仅适用于 defense evasion 类条目，资料注明 "\*Required for defense evasion"）；CAPEC ID（Field，指向 CAPEC 条目的超链接，非必填）；Version\*（Field，格式 MAJOR.MINOR，必填）；Impact Type\*（Tag，取值为 Integrity 或 Availability，仅适用于 impact 类条目，必填）；Contributor（Tag，非 MITRE 贡献者名单，从最早到最近，非必填）；Procedure Examples（Relationship / Field，当 group 或 software 实体通过有记录的使用关联到该条目时填充，非必填）；Detection\*（Field，高层分析流程、传感器、数据与检测策略，必填，且须供应商无关）；Mitigation\*（Relationship / Field，可阻止该条目生效或达到对手预期结果的配置、工具或流程，当有 mitigation 对象关联时填充，必填）。

**Procedure（过程/手法）**——不是独立对象。资料把它定义为 "the specific implementation adversaries have used for techniques or sub-techniques"，并说明它记录在技术与子技术页面的 "Procedure Examples" 区块中，属于 observed in-the-wild use。资料特别指出一个 procedure 可以横跨多个技术与子技术（例如同时涉及 PowerShell、Process Injection 与 LSASS Memory）。

**Group（组织）**——按资料 Table 3 "ATT&CK Group Model"：Name\*（Field）；ID\*（Tag，格式 `G####`）；Associated Groups（Tag，指向同一条目、可能指同一或相似组织的其他名称）；Version\*（Field，MAJOR.MINOR）；Contributor（Tag）；Description\*（Field，基于公开威胁报告，可含活动时间、疑似归因、目标行业与重大事件）；Associated Group Descriptions（Field，说明别名与主名称的对应关系并附报告引用）；Techniques / Sub-Techniques Used\*（Relationship / Field，该组织使用的 (sub-)technique 列表及使用方式说明，"Each technique should include a reference"）；Software（Relationship / Field，该组织被报告使用过的软件及使用方式说明）。

**Software（软件）**——分为 tool 与 malware 两类：Tool 指商用、开源、内置或公开可用、防御者/渗透测试者/红队/对手都可能使用的软件（含 PsExec、Metasploit、Mimikatz 以及 Net、netstat、Tasklist 等系统工具）；Malware 指商用、定制的闭源或开源、意图用于恶意目的的软件。按 Table 4 "ATT&CK Software Model"：Name\*、ID\*（`S####`）、Associated Software、Version\*、Contributor、Type\*（Tag，取值 malware 或 tool）、Platform\*、Description\*、Associated Software Descriptions、Techniques / Sub-Techniques Used\*（Relationship / Field，该软件实现的技术及实现方式）、Groups（Relationship / Field，从对应的 group 条目填充）。

**Mitigation（缓解措施）**——代表可用于阻止某项技术与子技术成功执行的安全概念与技术类别，截至 2020 年 3 月 Enterprise 中有 41 条，且 "Mitigations are vendor product agnostic and only describe categories or classes of technologies, not specific solutions"。按 Table 5 "ATT&CK Mitigation Model"：Name\*（Field，缓解措施类别的名称）；ID\*（Tag，格式 `M####`）；Description\*（Field）；Version\*（Field，MAJOR.MINOR）；Techniques Addressed by Mitigation\*（Relationship / Field，该缓解措施潜在覆盖的 (sub-)technique 列表）。资料记录了历史变化：Enterprise 的缓解措施在 2019 年 7 月的更新中由自由文本字段改为对象格式，Mobile 是最早使用对象格式的知识库。

**Data Source（数据源）**——在 Design and Philosophy 中只是 (sub-)technique 上的一个受列表约束的 tag，不是带关系端点的独立对象；它自身的对象结构，**资料未说明**（USAGE.md 指向的 ATT&CK Data Model Specification 未被本资料包含）。

**Data Component（数据组件）**——USAGE.md 的 recipes 中出现 STIX 类型 `x-mitre-data-component`，并通过 `detects` 关系指向 `attack-pattern`（recipies 名为 `datacomponent_detects_techniques` 与 `technique_detected_by_datacomponents`）。其字段清单、必填性与取值约束，**资料未说明**。

**Campaign（活动）**——USAGE.md 注明 "The following code is intended to be used with the ATT&CK v12 release which includes Campaign Objects"，并给出关系 `campaign --uses--> tool / malware / attack-pattern` 与 `campaign --attributed-to--> intrusion-set`。其字段清单，**资料未说明**。

**Matrix（矩阵）**——STIX 类型 `x-mitre-matrix`，其 `tactic_refs` 属性按顺序列出该矩阵中的战术；每个矩阵带一个 last modified 时间戳作为版本号。其余字段，**资料未说明**。

**Relationship（关系）**——STIX 的 `relationship` 对象，含 `relationship_type`、`source_ref`、`target_ref`，并常有 description 用于交代关系性质；含 `revoked` 字段。资料明确："Unlike other objects in the dataset, relationships cannot be revoked or deprecated"，关系只在其两端对象之一被撤销或废弃时被视为失效。

**Procedure 之外的引用类信息**——CAPEC ID 字段；SQLi 案例中提到可引用 CAPEC、CWE、OWASP 的细节。

## 3. 编号与层级

**ATT&CK ID 格式**：技术 `T####`；子技术 `T####.###`（父技术 ID 加三位子编号）；组织 `G####`；软件 `S####`；缓解措施 `M####`。每个对象另有 MAJOR.MINOR 版本号，"starts at 1.0 for any new object"。

**STIX ID**：USAGE.md 强调 "This is typically the preferred way to retrieve objects when working with ATT&CK data because STIX IDs are guaranteed to be unique"，形如 `intrusion-set--f40eb8ce-2a74-4e56-89a1-227021410142`、`attack-pattern--c16e5409-ee53-4d79-afdc-4099dc9292df`。资料还记录了一个历史缺陷：旧版缓解措施与技术是 1:1 关系并共用技术 ID，导致技术 ATT&CK ID 并非真正唯一，需按 `type = attack-pattern` 过滤才能定位技术；这批 1:1 mitigation 已 deprecated。

**层级**：Matrix → Tactic → Technique → Sub-Technique；Procedure 不属于层级，是挂在最底层的观察记录。子技术层级有硬约束："Each sub-technique will only have a relationship to a single parent technique and no other to avoid complicated and difficult to maintain relationships across the model"。同时资料允许子技术不必落在父技术的全部战术下：只要概念上属于该技术即可，例如 Process Hollowing 子技术可用于 Defense Evasion 但不用于 Privilege Escalation，尽管其父技术 Process Injection 同时覆盖两个战术。资料说明 "Not all techniques will have sub-techniques"。

**命名规则**：技术名称聚焦该技术之所以独特的方面，即在介于战术之下的中间抽象层上对手达成了什么；子技术名称通常表示更低抽象层的用法。若行业已有公认术语且经会议演讲、博客、文章等记录，则采用既有术语。

**同一事物在多处出现的处理**：（a）组织别名记入 Associated Groups，并在 Associated Group Descriptions 中给出来源引用；软件别名同理记入 Associated Software。（b）同一行为可同时落在多个技术下：资料举例 HTTP 命令控制流量走 8088 端口同时属于 Non-Standard Port 技术与 Application Layer Protocol 的 Web Protocols 子技术。（c）procedure example 只映射一次："The same procedure should not be mapped to both in order to reduce redundant relationships"——信息足够具体就只写进子技术，模糊就写进技术。（d）群体经由软件间接使用技术（group uses software, software uses techniques），USAGE.md 用 `get_techniques_by_group_software` 这类查询现算，而不是把结果复制成新条目。（e）同一概念在不同 domain 各自维护，例如 Enterprise 与 Mobile 各有自己的缓解措施类别且重叠极小。

**域名与平台**：ATT&CK 按 technology domain 组织——Enterprise（含云）、Mobile、ICS 三个；每个 domain 内定义 platform，Enterprise 的 platform 为 Linux、macOS、Windows、AWS、Azure、GCP、SaaS、Office 365、Azure AD，Mobile 为 Android、iOS。PRE-ATT&CK 不被视为 domain，它跨域描述取得访问权之前的需求收集、侦察与武器化行为。STIX 中 kill chain 名区分域：enterprise 用 `mitre-attack`、mobile 用 `mitre-mobile-attack`、ics 用 `mitre-ics-attack`。

## 4. 对象之间的关系

资料（含 Figure 3 与 Figure 4 的说明文字、各表格的关系字段，以及 USAGE.md 的 recipes）给出的关系类型与方向如下，箭头方向即 STIX 中 `source_ref → target_ref` 的方向：

- **group --uses--> (sub-)technique**：组织表中的 Techniques / Sub-Techniques Used 字段，表示该组织对这一技术的 procedure；USAGE.md 的 `techniques_used_by_groups` 即按 `intrusion-set --uses--> attack-pattern` 构建。
- **group --uses--> software**：组织表中的 Software 字段；USAGE.md 按 `intrusion-set --uses--> tool / malware` 构建（`software_used_by_groups`）。
- **software --uses--> (sub-)technique**：软件表中的 Techniques / Sub-Techniques Used 字段（`tool/malware --uses--> attack-pattern`）。
- **间接使用**：资料明确 "Because a group uses software, and software uses techniques, groups can be considered indirect users of techniques used by their software"，并说明这两组技术常有交集但也可以不同；USAGE.md 通过两步查询而非复制关系来得到结果。
- **campaign --uses--> tool / malware / attack-pattern**，以及 **campaign --attributed-to--> intrusion-set**（USAGE.md 中这些 recipes 反向使用 `attributed-to` 得到 group_id → campaign）。
- **attack-pattern --subtechnique-of--> attack-pattern**：子技术指向唯一父技术；USAGE.md 的 `subtechniques_of` 与 `parent_technique_of` 即此关系。
- **course-of-action --mitigates--> attack-pattern**：缓解措施指向技术与子技术，USAGE.md 的 `mitigation_mitigates_techniques` 与 `technique_mitigated_by_mitigations` 一对互逆查询即此关系。
- **x-mitre-data-component --detects--> attack-pattern**：数据组件指向技术，见 `datacomponent_detects_techniques` 与 `technique_detected_by_datacomponents`。
- **x-mitre-matrix 的 `tactic_refs` → x-mitre-tactic**：列表顺序即战术在矩阵中的顺序。
- **attack-pattern 的 `kill_chain_phases.phase_name` → tactic 的 `x_mitre_shortname`**。
- **revoked-by**：被替代对象为 `source_ref`、替代对象为 `target_ref`；USAGE.md 的 `getRevokedBy` 沿此关系找替代者。
- **CAPEC ID 字段 → CAPEC 条目**：技术上的超链接，不是 STIX 关系。

**攻击侧与防御/检测/数据侧的连接方式**：防御侧与检测侧都**直接**挂在技术对象上，不经过任何中间制品对象。资料原文写明缓解措施的对象化方式就是 "where relationships signify how a mitigation can mitigate a technique or sub-technique"，其关系字段名为 Techniques Addressed by Mitigation；检测侧在 USAGE.md 中直接以 `detects` 关系连接数据组件与技术。**数据源**这一侧不同：在 Design and Philosophy 中它只是 (sub-)technique 上的一个受列表约束的 tag，不是关系端点；因此"数据源→技术"的覆盖分析靠标签取值完成，而不是靠关系遍历，例如资料举的查询是 "what techniques can I detect if I have process monitoring in place?"。资料另外规定继承规则："Both mitigation and data source information will have an upwards inheritance to the technique from sub-techniques"，而 "Groups and software procedure examples are not inherited between techniques and sub-techniques"。原文给出的具体例子是持久化威胁组织 APT28 使用 Mimikatz 针对 Windows LSASS 进程内存做凭据转储（Figure 4 的说明文字）。

## 5. 抽象层次的选择

**描述的是目的、行为还是实现**：ATT&CK 自定位为 mid-level 模型——高于 Cyber Kill Chain、STRIDE 这类只讲高层目标的生命周期模型，低于漏洞库与恶意软件库这类具体实例集合。它明确说 "A mid-level adversary model like ATT&CK is necessary to tie these various components together"。具体分工是：Tactic 写对手的战术目标（why），Technique 写对手达成目标的行为（how），也可以写对手通过该行为获得了什么（what，Discovery 战术尤其如此）；Sub-Technique 写更低一层的具体做法；Procedure 才是具体实现，且不单独建条目。资料把技术抽象分为两层：适用于多平台的通用技术（如 Exploit Public-Facing Application），以及在多平台上有特定做法的通用技术（如 Process Injection）；子技术只有一层：可能适用于一个或多个平台的具体做法（如仅适用于 Windows 的 Rundll32，以及跨 Windows/Linux/Mac 的 Hidden Files and Directories）。资料强调当技术或子技术内含多个步骤时，应聚焦于"使该行为区别于其他行为的那一点"。

**新条目、变体还是不收录**：资料给出三条可选路径——"Adding an entirely new technique"、"Adding a new sub-technique under an existing technique"、"Enhancing or abstracting an existing technique or sub-technique to make it inclusive of the newly-identified or otherwise previously uncategorized behavior"。判断依据是 4.3.1.5 的六个因素：Objective（在完成什么，相似技术可能以相同方式完成不同战术目标）、Actions（怎么做，触发条件是否不同）、Use（谁在用，是否有多个组织以及用法是否不同）、Requirements（文件、位置、注册表改动、API 调用、权限等组件是否重叠）、Detection（需要 instrument 什么，与需求和动作相关但可能不同）、Mitigations（可用的缓解手段是否相似）。4.3.2 进一步给出一组引导问题，其中两个判据最关键：新行为是否天然适合作已有技术下的新子技术，以及 "Would creating a new technique be useful for an end user of the model?"（防御方是否会在概念上把它与其他技术归为一组）；此外还要问它是否有不同的检测方法或检测方法集合、是否有根本不同的缓解方法。4.3.3 给出反面判据："If a new behavior is not conceptually different in how it is implemented or defended against, then it likely should be included in an existing technique or sub-technique"，此时只需说明它与既有用法变体的区别（怎么执行、需要什么不同的分析、缓解考虑是否不同）。

**收录的准入标准**：三个概念性前提是保持对手视角（adversary's perspective）、基于实证使用（empirical use）、抽象层次要能衔接攻击行动与可能的防御对策。实证使用要求行为主要来自公开报道的疑似 APT 事件，或来自已被发表、红队可能使用的攻击性研究；"The tie to incidents keeps the model grounded to real-world threats that are likely to be encountered rather than theoretical techniques that are unlikely to be seen due to difficulty of use or low utility"。来源包括威胁情报报告、会议演讲、网络研讨会、社交媒体、博客、开源代码仓库与恶意软件样本；社区贡献（威胁情报分析员、防守方中的威胁猎手与恶意软件分析员与事件响应者、红队）被重点依赖。来源可靠性按六条判据评估：内部与外部一致性、过往报道是否可靠、是否被社区广泛使用与引用、是否有拼写或语法错误、是否展示了可靠的分析方法（含证据、置信度与空白，是否出现分析上的"跳跃"）、是否有其他来源印证。资料明确："We do not accept leaked or classified information from any corporation or government as the basis for threat intelligence within ATT&CK."。另外，组织与软件的每条技术使用都必须附公开来源引用，以便追溯；无组织归属的行为（ungrouped use）同样可被采纳为技术依据或增强信息。

**两个示例结论**：Process Injection 的核心特征是"把恶意代码载入一个已存在的活动进程"，使用广泛且与其他防御规避/提权方法区别足够明显，因此作为独立条目收录，其内部多种变体定义为子技术，并同时挂在 Defense Evasion 与 Privilege Escalation 下。SQL Injection 则被判为"针对特定软件技术的利用技术的一种变体"，在实现方式、检测方式与缓解方式上的变化有限，因此不作为新技术收录，而是作为 Exploit Public-Facing Application 的技术细节增强，具体细节引用 CAPEC、CWE、OWASP。

## 6. 稳定部分与易变部分

**希望很少变化的**：Tactic，因为 "these remain relatively static over time because adversary goals are unlikely to change"；对象模型与字段定义（Tag / Field / Relationship 三分类）；ID 格式；版本语义规则；STIX 表示与关系类型。战术虽稳定但可按需新增或细分：资料举的两个例子是 2019 年新增 Impact 战术以覆盖破坏性与毁灭性攻击，以及早期把 Collection 从 Exfiltration 中拆出，因为"数据从哪来、怎么拿到"与"怎么把数据带出去"是两件事，发生时间也不同，"Thus, a determination was made to break that tactic into two and describe Collection separately"。资料还说明：为其他领域套用该方法论时，可能需要与既有模型重叠但不完全相同的新战术类别。

**预期不断增长的**：技术、子技术、组织的 procedure examples、组织与软件档案、Detection、Data Source、Mitigation、引用与 Contributor。资料明说子技术的设计目标之一就是 "Provide a structure to allow sub-techniques to be added easily that would decrease the need to make changes to techniques over time"，并希望借此把技术数量压到可管理规模、让各技术的抽象层次趋于一致。

**版本管理**：ATT&CK 对对象、矩阵视图与发布分别做版本。对象统一使用两段式 MAJOR.MINOR，新对象从 1.0 起；"Versions will only increment between content releases"，因此在两次计划更新之间的多次改动只让版本增长一次。技术的 MAJOR 用于名称变化与范围变化（范围变化包括描述中覆盖与不覆盖什么，以及所属战术的变化），"which should happen infrequently"；MINOR 用于不改变范围的描述性更新（procedure examples、detections、mitigations、references）以及平台、所需权限、数据源、绕过的防御等元数据变化。组织的 MAJOR 用于别名增改与描述变化（应很少发生），MINOR 用于引用与技术/软件关系变化；软件的 MAJOR 用于别名增改与描述变化，MINOR 用于引用与技术/组织关系变化；缓解措施的 MAJOR 用于覆盖范围与名称变化，MINOR 用于不影响范围的描述以及引用与技术关系变化。矩阵版本是 last modified 时间戳（适用于 Enterprise 及其平台、Cloud、Mobile、PRE-ATT&CK）。发布（release）指 STIX 表示被整体打包发到 GitHub CTI 仓库并同步更新网站，历史版本被保存以供回看。

**废弃（Deprecation）与撤销（Revocation）**：当对象被认为不再值得追踪时（例如把若干技术概念合并，或删除多余对象）可被废弃；被替代的对象标记 `revoked` 并建立 `revoked-by` 关系指向替代者。资料强调废弃对象不会被删除——"Deprecated objects are not deleted from the knowledge base and are still maintained in the STIX repositories, but they no longer show up in the navigation bar and matrix within the main ATT&CK website"。USAGE.md 补充：关系本身不能被废弃或撤销，只能随两端对象的状态失效。

## 7. 内容与执行的分离

**内容形式**：知识以 STIX 表示存放为数据。Design and Philosophy 说 release 是 "the changes to the STIX representation of ATT&CK are bundled and released to the GitHub CTI repository"；USAGE.md 说明现已统一 STIX 2.0 与 STIX 2.1 表示，并列出可用的访问形式：按 STIX2 FileSystem 规范分域存放的目录（如 `./cti/enterprise-attack`，用 `FileSystemSource` 加载）、单个域 bundle 文件（如 `enterprise-attack.json`，用 `MemoryStore` 加载）、官方 TAXII 2.0 服务器（三个域作为 collection，带静态 ID）、以及经 GitHub 原始文件的 HTTP 请求方式；多域可用 `CompositeDataSource` 合并。版本以 MITRE/CTI 仓库的 Git 标签追踪：`ATT&CK-v` 前缀对应 ATT&CK 版本，`CAPEC-v` 前缀对应 CAPEC 版本，例如可用 `ATT&CK-v5.2` 取到具体版本的数据。

**由谁解释执行**：ATT&CK 自身没有规则语言或执行引擎，资料中承担解释职责的是外部工具——USAGE.md 全篇的示例都基于 `stix2` python 库，实时访问用 `taxii2client` 的 `v20` 接口（ATT&CK TAXII 服务器实现 TAXII 2.0，客户端若用 2.1 会得到 406 响应）。

**内容能表达的逻辑上限**：知识库能表达的是对象、标签、受限取值、自然语言字段与关系，以及"关系本身带有 description"这一点（USAGE.md："It is useful to track not only the related object but the relationship itself because a description is often present to contextualize the nature of the relationship"）。检测侧的上限被明确写出：Detection 是 "High level analytic process, sensors, data, and detection strategies"，其目的是提供足够信息与引用，指向有用的防御方法论；"ATT&CK and MITRE do not endorse any particular vendor solution"，因此建议必须停留在方法与工具类别的层面而非具体工具；而且 "Detection may not always be possible for a given (sub-)technique and should be documented as such"。缓解措施同样只描述类别或技术类别，不描述具体方案，"Mitigation may not always be possible for a given (sub-)technique and is documented as such if no relationships to a given (sub-)technique are present"。

**超出表达上限时怎么办**：一是外链到其他知识库与资源（CAPEC ID 字段；SQLi 案例中引用 CAPEC、CWE、OWASP 的细节）；二是把可执行的分析放到 ATT&CK 之外，资料把 Cyber Analytics Repository（CAR）举为 "one example of analytic development that could be used as a starting point for an organization to develop behavioral analytics based on ATT&CK"；三是让使用方自行用查询把关系组合成所需视图，USAGE.md 的 relationships microlibrary 就是这样一组现算工具。

## 8. 覆盖与成熟度的表达

**覆盖（coverage）**：ATT&CK 提供的是覆盖分析所需的结构，而不是一个覆盖率数字。资料先给结论——"it's important to note that in general, coverage of every ATT&CK technique is unrealistic"——再指出覆盖某个技术的全部 procedure 同样不现实，因为对手总在变化、无法预先知道所有做法。可计算的部分来自受限的 Data Source 标签：资料说明该属性被限制在已定义列表内，目的是 "to allow analysis of technique coverage based on unique data sources"，并举查询为例 "what techniques can I detect if I have process monitoring in place?"。覆盖的含义必须由使用组织自行定义，资料连续抛出这些问题：是对所有技术采集数据还是只管最重要的那些；是对所有技术告警还是只对最罕见的那些；一个技术是否即使并非真实事件也要打上 ATT&CK 标签；一条、两条、三条还是更多 analytic 才算有把握认为该技术被覆盖；覆盖是否要从可见性扩展到控制与预防措施；是否要把红队或对手仿真测试纳入覆盖定义。资料还要求映射者负责说明覆盖了什么："Anyone mapping to ATT&CK should be able to explain the procedures they cover."，并强调 "ATT&CK is just as much about the mindset and process of using it as much as it is the knowledge base itself"，目标应是持续的情报—防御—验证—改进循环，而不是 100% 覆盖。可视化层面只有 ATT&CK Matrix，它展示战术与技术、子技术的关系；资料没有描述用于表达防御覆盖率的矩阵或分级，**资料未说明**是否存在此类覆盖矩阵。

**成熟度与依据**：资料中与"成熟度"最接近的三样东西是：（a）对象级 **Version**，但它只表达"改动程度"（major 与 minor 各自对应哪些改动），不表达质量或置信度；（b）**Contributor** 标签，记录非 MITRE 贡献者；（c）**经验使用（empirical use）的四类分级**——Reported（有公开来源的野外使用报道）、Reported, non-public（非公开来源报道过，但该技术存在本身有公开来源）、Underreported（很可能在被使用但未被报道，或只有间接信息，需按来源可信度裁量）、Unreported（没有任何公开或非公开情报说明该行为在被使用，可能包含已发表的新攻击性研究，需按其效用与被对手采用的可能性裁量）。资料还说明，Linux 与 Mac 上报道的持续威胁事件远少于 Windows，因此可用威胁数据"substantially less available"，必要时可用不绑定特定 APT 组织的一般野外数据替代。至于这些经验使用分级是否作为字段写进对象，**资料未说明**。Soc maturity assessment 与 Defensive gap assessment 是资料列出的两种使用场景，但它们描述的是使用者的评估活动，不是知识库中的字段；资料只说 ATT&CK 可作为衡量 SOC 在检测、分析与响应入侵方面有效性的 "one measurement"。

## 9. 对我们的启发

分析：把"战术—技术—子技术"三级结构搬到方法层，用"防御目标—防御技术—具体实现"替代按论文平铺的插件列表。Tactic 之所以稳定，是因为它写的是对手目标；Technique 之所以能当骨架，是因为它写的是行为类别；Sub-Technique 之所以能无限增长，是因为它写的是具体做法。我们的 methods 层现在等价于"每篇论文都是一个顶层条目"，缺少稳定的中间层，因此库只能一篇篇追。可以引入：防御目标（对应 tactic，例如"防止梯度泄漏""防止投毒聚合"）→ 防御技术（对应 technique，对应 operators 里可复用的计算单元类别，例如"裁剪""加噪""鲁棒聚合"）→ 具体实现（对应 sub-technique，某篇论文的具体算法与其超参），论文只作为最底层条目的来源与引用。这一项同时牵动 methods、operators 与 knowledge_base 三层。转移方式：改造后适用。

分析：把"每个条目只能有一个 canonical 父节点、同一事实只登记一次"作为知识库硬约束。子技术只允许一个父技术，是为了避免跨模型关系难以维护；同一 procedure 不能同时挂在技术与子技术上，是为了减少冗余关系。我们的库也应为每个方法指定唯一归属（一个防御技术 + 明确的位置集合），跨层引用通过关系表达而不是复制条目，否则"说不清覆盖了什么"会以重复条目的形式继续存在。对应 knowledge_base 层。转移方式：可直接照搬。

分析：字段要分成三类并显式标注必填与取值约束。ATT&CK 把每个数据项标注为 tag（可过滤、可 pivot）、field（自由文本）或 relationship（对象关系），并用 `*` 标必填，还给出受限列表、枚举与版本格式等约束。我们的方法插件元数据目前多半是散落的自由文本；改成"可过滤标签（适用层、hook 位置、攻击类型、是否需要额外通信）+ 自由文本（方法说明、已知失效场景）+ 关系（覆盖哪些攻击面、依赖哪些算子）"之后，覆盖分析才能自动计算。对应 knowledge_base 与 records 层。转移方式：可直接照搬。

分析：把运行时那 11 个位置做成封闭枚举，对应 Data Source 的 restricted list。ATT&CK 限制数据源列表的目的就是让"我有什么数据能覆盖哪些技术"成为可查询的问题。我们的 runtime 层同样应把 11 个暴露点（样本、梯度、步内 LoRA、客户端上传、聚合结果、下发内容、通道消息等）定义成受控枚举，并允许方法声明它需要哪些位置的数据；这样"位置 × 攻击面 × 方法"三者的关系才是可枚举、可校验的，而不是每加一个方法就要重新讨论它能插在哪。对应 runtime 层。转移方式：改造后适用（限制的对象从数据源换成 hook 位置与可观测张量）。

分析：防御对象与攻击面对象之间直接建立带 description 的关系，不经过中间制品。ATT&CK 的 `course-of-action --mitigates--> attack-pattern` 与 `x-mitre-data-component --detects--> attack-pattern` 都是直接连接，且关系本身可以携带说明来交代"如何生效"。我们的库应让每个防御方法直接声明它覆盖的 threat 条目与 hook 位置，并把"以何种机理覆盖、在什么条件下失效"写进关系而不是写进某一端的描述文本。对应 knowledge_base 与 methods 层。转移方式：可直接照搬。

分析：把防御从自由文本升级为独立对象。Enterprise 在 2019 年 7 月的更新中把缓解措施从自由文本字段改成对象格式，这个先例正对应我们的问题：如果防御只作为攻击面条目里的一段说明，就无法复用、计数、比较与版本化。我们的 methods 层应当坚持"一个方法 = 一个带 ID 和版本的对象 + 若干关系"，而不是插件目录里的一个文件。对应 methods 层。转移方式：可直接照搬。

分析：不要输出单一覆盖率百分比，而是输出可解释的覆盖矩阵，并要求每个方法说明它覆盖的具体过程。ATT&CK 明说 100% 覆盖不现实，并把"几条 analytic 才算覆盖"这类定义权交给使用者，同时要求映射者能解释自己覆盖了哪些 procedures。我们的 evaluation 层应输出"攻击面 × hook 位置 × 方法"的矩阵与空白清单，并要求每个方法条目提供它所覆盖的攻击过程级说明与可复现依据，而不是一个笼统的"已覆盖"标记。对应 evaluation 层。转移方式：可直接照搬。

分析：区分"只记录"与"阻断/告警"两种强度。ATT&CK 用 ipconfig.exe 与 Valid Accounts 两个例子说明，有些行为只要留下可回溯的活动记录就够，逐条告警反而过量。联邦训练里正常样本、正常梯度、正常通道流量会频繁命中检测点，因此 runtime 层应当原生支持 telemetry-only 与 enforce 两种模式，并把方法按其强度分级，而不是默认所有命中都要干预。对应 runtime 层。转移方式：可直接照搬。

分析：版本语义要能表达"改动程度"。MAJOR 仅用于名称与范围变化且应很少发生，MINOR 用于描述、关系、引用与元数据；版本只在 release 之间递增，避免噪声。我们的方法条目应沿用这套语义并写进贡献指南：新增一篇论文的实现、补充超参与引用属于 MINOR；改变方法语义、覆盖范围或所属防御技术才算 MAJOR。这样使用方才能判断某个方法变化后是否需要重新验证。对应 knowledge_base 与 methods 层。转移方式：可直接照搬。

分析：废弃而不删除，并提供替代指针。ATT&CK 的废弃对象仍保留在 STIX 仓库中，只是不再出现在导航与矩阵里；被替代的对象标记 revoked 并建立 `revoked-by` 关系。我们的库同样会有"被更好的方法取代"的条目，但历史实验需要继续引用旧方法，删除会破坏记录的完整性。应为方法条目提供 deprecated / revoked 状态与 `revoked-by` 关系，并在默认视图里过滤、在记录层保留。对应 records 与 knowledge_base 层。转移方式：可直接照搬。

分析：内容与执行分离的做法可以借一半。ATT&CK 把知识存成 STIX 数据、由外部库解释、自身不带规则语言，这对我们的"方法元数据 + 关系 + 版本"完全适用：元数据应当是可校验的数据，执行器应当只有一个。但"检测逻辑放在外部仓库（如 CAR）"这一模式不能直接替代我们需要的数值算法执行——算子层的算子必须真的能跑，而且要有配置 schema、随机性与数值精度约定。对应 knowledge_base 与 operators 层。转移方式：改造后适用。

分析（不可照搬）：Detection 字段的表达方式无法承载数值算法。ATT&CK 的检测建议刻意停留在"高层分析流程、传感器、数据与策略"并保持供应商无关，因为它的知识是给人读的、给分析流程指方向的；而我们的防御是数值算法：裁剪范数、噪声尺度、隐私预算、聚合规则、阈值、随机种子都会改变行为与结论。把这些压成 tag 与自由文本会丢失全部可执行信息，所以 methods 层必须允许携带代码与结构化配置，并另设执行引擎。对应 methods 与 operators 层。转移方式：不可照搬。

分析（不可照搬）："供应商/工具无关"只适用于描述层，不能升到实现层。ATT&CK 明确只描述技术类别而不描述具体方案，这在我们用于分类与检索时是优点；但若把两篇目标相同、数值上不同的防御论文抽象成同一个条目，实验就无法复现、也无法公平比较。因此分类层可以无关化，实现层必须保留到论文级的细节差异，并把差异登记为子技术或变体说明。对应 methods 层。转移方式：不可照搬。

## 10. 框架自己承认的局限

- 不是软件攻击向量的穷举，此类用途应交给 CAPEC 与 CWE。
- 不是待办清单，不以 100% 覆盖为目标；覆盖某个技术的全部 procedures 同样不现实，"especially since we often cannot know all of them in advance"。
- 检测并非总是可行，缓解也并非总是可行，只能如实记录为不可行。
- 子技术只能有一个父技术，这是为避免关系难以维护而作的取舍；资料承认确实存在多父更合理的情形（如 Scheduled Task/Job 中只有部分子技术同时可用于提权）。
- 并非所有技术都能自然拆出子技术（如 Two-Factor Authentication Interception），子技术也并非总能按平台拆分；若强行拆分，会出现为 Windows、Mac、Linux 各写一套 Local/Domain/Default Valid Accounts 的重复，命令控制类技术尤其如此，因为网络通信往往与平台无关。
- 抽象层次不均是既有问题，子技术的引入正是为修复它：有些技术过宽、有些过窄，导致难以可视化、也难以理解某些技术的目的。
- Linux 与 Mac 上报告的持续威胁事件远少于 Windows，可用威胁数据明显不足。
- 不应仅凭使用的技术做归因，多个组织共用同一技术，归因需要 Diamond Model 的全部要素。
- 旧版 1:1 mitigation 与技术共用 ATT&CK ID，使技术 ATT&CK ID 并非真正唯一；这批缓解措施已 deprecated。
- 维护过程 "is as much of an art as it is a science"；把 ATT&CK methodology 应用到其他领域不一定产出 ATT&CK 模型——没有可用威胁情报、或模型不涉及对手对计算机信息网络的使用时，就属于这种方法论可用但结果不是 ATT&CK 模型的情形。
- USAGE.md 提醒：不应使用 created / modified 时间戳来判断知识库整体是否更新，应改用发布版本列表；STIX 的 `revoked` 过滤器在不同访问方式（本地数据与 TAXII 服务器）下行为不一致，官方建议不要用内建过滤器而用自定义函数过滤（并指向 issue #127）；TAXII 2.1 客户端连 ATT&CK 的 TAXII 2.0 服务器会出现 406 响应；revoked 与 deprecated 对象会一直保留在数据集中，使用者需要自行过滤。

## 11. 原文依据

1. 支撑 §2：数据项被分成 tag、field 与 relationship 三类，这是对象字段的类型学基础。
   > "Items are annotated by tag if the data point is an informational reference on the technique that can be used to filter and pivot on"

2. 支撑 §2：带星号的字段表示必填，且具体要求随战术类别而变。
   > "Data items marked with * denote the element is required and additional information about specific requirements dependent on tactic category is in the description."

3. 支撑 §3：技术与子技术的编号格式为 T#### 与 T####.###。
   > "Unique identifier for the (sub-)technique within the knowledge base. Format: (technique) T####; (sub-technique) T####.###."

4. 支撑 §3：子技术只有一个父技术，不存在一对多关系。
   > "Sub-techniques do not have a one-to-many relationship to techniques. Each sub-technique will only have a relationship to a single parent technique and no other"

5. 支撑 §4：缓解措施是独立对象，其与技术之间的关系就是"如何缓解"的表达。
   > "Mitigations are represented by objects similar to groups and software where relationships signify how a mitigation can mitigate a technique or sub-technique."

6. 支撑 §4 与 §8：数据源被限制在已定义列表中，目的是支持按数据源分析技术覆盖。
   > "This attribute is intended to be restricted to a defined list to allow analysis of technique coverage based on unique data sources."

7. 支撑 §5：ATT&CK 自定位为衔接各组件的中层模型，而不是高层生命周期模型或低层漏洞/恶意软件库。
   > "A mid-level adversary model like ATT&CK is necessary to tie these various components together."

8. 支撑 §6：MAJOR 版本只对应名称与范围变化，且被期望很少发生，这是"稳定骨架、增长条目"的版本学依据。
   > "Major version changes consist of name changes and scope changes which should happen infrequently."

9. 支撑 §7：内容以 STIX 表示打包发布到 GitHub CTI 仓库，内容与解释工具分离。
   > "A release occurs when the changes to the STIX representation of ATT&CK are bundled and released to the GitHub CTI repository [9] along with any updates to the ATT&CK website."

10. 支撑 §8：覆盖率不是框架承诺的指标，100% 覆盖被明确称为不现实。
    > "it's important to note that in general, coverage of every ATT&CK technique is unrealistic."

```json
{
  "key": "attack",
  "framework": "MITRE ATT&CK: Design and Philosophy（2018 年 7 月首发、2020 年 3 月修订，含 sub-techniques）与 mitre/cti USAGE.md（STIX 表示）",
  "object_types": [
    {
      "name": "Tactic",
      "role": "attack",
      "fields": ["Name", "Definition（每个战术含界定其类别的定义文字，字段清单资料未说明）", "STIX: x-mitre-tactic 的 x_mitre_shortname", "矩阵中的顺序由 x-mitre-matrix 的 tactic_refs 给出"]
    },
    {
      "name": "Technique",
      "role": "attack",
      "fields": ["Name*", "ID*（T####）", "Sub-Techniques*", "Tactic*", "Description*", "Platform*", "System Requirements", "Permissions Required*（提权时必填）", "Effective Permissions*（仅提权）", "Data Source*（受限列表）", "Supports Remote（仅 execution）", "Defense Bypassed*（仅 defense evasion）", "CAPEC ID", "Version*（MAJOR.MINOR）", "Impact Type*（Integrity 或 Availability，仅 impact）", "Contributor", "Procedure Examples", "Detection*", "Mitigation*"]
    },
    {
      "name": "Sub-Technique",
      "role": "attack",
      "fields": ["与 Technique 相同的字段表", "ID*（T####.###）", "不含 Sub-Techniques 字段", "只能有一个父 Technique"]
    },
    {
      "name": "Procedure",
      "role": "other",
      "fields": ["不是独立对象；记录于技术与子技术的 Procedure Examples 区块，内容为观测到的野外使用方式，可横跨多个 (sub-)technique"]
    },
    {
      "name": "Group",
      "role": "attack",
      "fields": ["Name*", "ID*（G####）", "Associated Groups", "Version*（MAJOR.MINOR）", "Contributor", "Description*", "Associated Group Descriptions", "Techniques / Sub-Techniques Used*", "Software"]
    },
    {
      "name": "Software",
      "role": "attack",
      "fields": ["Name*", "ID*（S####）", "Associated Software", "Version*（MAJOR.MINOR）", "Contributor", "Type*（malware 或 tool）", "Platform*", "Description*", "Associated Software Descriptions", "Techniques / Sub-Techniques Used*", "Groups"]
    },
    {
      "name": "Mitigation",
      "role": "defense",
      "fields": ["Name*", "ID*（M####）", "Description*", "Version*（MAJOR.MINOR）", "Techniques Addressed by Mitigation*（Relationship，对应 STIX course-of-action --mitigates--> attack-pattern）"]
    },
    {
      "name": "Data Source",
      "role": "telemetry",
      "fields": ["作为 (sub-)technique 上的 Data Source* Tag 存在，取值受限于已定义列表；自身对象字段清单资料未说明"]
    },
    {
      "name": "Data Component",
      "role": "detection",
      "fields": ["STIX 类型 x-mitre-data-component；通过 detects 关系指向 attack-pattern；字段清单资料未说明"]
    },
    {
      "name": "Campaign",
      "role": "attack",
      "fields": ["ATT&CK v12 起包含 Campaign 对象；关系为 campaign --uses--> tool/malware/attack-pattern 与 campaign --attributed-to--> intrusion-set；字段清单资料未说明"]
    },
    {
      "name": "Matrix",
      "role": "other",
      "fields": ["STIX 类型 x-mitre-matrix", "tactic_refs（有序战术引用）", "last modified 时间戳作为版本号", "其余字段资料未说明"]
    },
    {
      "name": "Relationship",
      "role": "relation",
      "fields": ["relationship_type", "source_ref", "target_ref", "description（常用来交代关系性质）", "revoked（关系本身不能被 deprecated 或 revoked，只随两端对象失效）"]
    }
  ],
  "id_scheme": "Technique: T####；Sub-Technique: T####.###；Group: G####；Software: S####；Mitigation: M####；STIX ID 形如 <type>--<uuid>（如 attack-pattern--c16e5409-ee53-4d79-afdc-4099dc9292df），官方推荐优先用 STIX ID 检索因为其保证唯一；对象版本 MAJOR.MINOR 从 1.0 起；矩阵版本为最后修改时间戳；发布版本用 GitHub 标签 ATT&CK-v<version>（如 ATT&CK-v5.2）。旧版 1:1 mitigation 与技术共用 ID，是技术 ID 并非真正唯一的历史原因。",
  "attack_defense_link": "direct",
  "link_detail": "防御侧与检测侧都直接挂在技术对象上：Mitigation（STIX course-of-action）--mitigates--> (sub-)technique（attack-pattern），关系字段名为 Techniques Addressed by Mitigation；Data Component（x-mitre-data-component）--detects--> attack-pattern。两者都不经过制品或漏洞等中间对象。Data Source 不同，它在 Design and Philosophy 中只是 (sub-)technique 上的受限 Tag，不是关系端点，覆盖分析靠标签取值（例如若有进程监控能检测哪些技术）。继承规则：mitigation 与 data source 信息由 sub-technique 向上继承到父 technique，组织与软件的 procedure examples 不继承。例子：APT28 使用 Mimikatz 针对 Windows LSASS 进程内存做凭据转储。",
  "abstraction_level": "中层（mid-level）行为模型：Tactic 写对手目标（why），Technique 写达成目标的行为（how）或所获信息（what），Sub-Technique 写更低一层的具体做法；具体实现（Procedure）只作为 Procedure Examples 记录而不单独建条目；明确不做软件漏洞枚举，该用途属 CAPEC/CWE。收录门槛为保持对手视角、基于实证使用（公开报道的野外使用或已发表的攻击性研究）、抽象层次足以衔接攻击行动与防御对策。新行为按新条目、新子技术、或增强既有条目三条路径处理，判据为 Objective、Actions、Use、Requirements、Detection、Mitigations 六因素以及是否有不同的检测与缓解方式。",
  "stable_parts": ["Tactics（对手目标，相对静态，仅在需要更准确描述目标时新增或细分）", "对象模型与字段定义（tag / field / relationship 三分类与必填标记）", "ID 编号格式", "版本语义规则（MAJOR 表范围与名称变化，MINOR 表描述与关系变化）", "STIX 表示与关系类型"],
  "growing_parts": ["Techniques 与 Sub-Techniques", "Procedure Examples（野外使用实例）", "Groups 与 Software 档案及其技术使用记录", "Detection 与 Data Source", "Mitigations", "引用与 Contributor"],
  "content_format": "STIX 2.0/2.1 JSON 数据：按 STIX2 FileSystem 规范按域存放（如 cti/enterprise-attack），或以单域 bundle 文件提供（如 enterprise-attack.json）；通过 GitHub CTI 仓库与官方 ATT&CK TAXII 2.0 服务器发布，版本用 Git 标签 ATT&CK-v<version> 追踪；完整规范为 ATT&CK Data Model Specification，未包含在本资料中。",
  "execution_engine": "ATT&CK 自身没有规则语言或执行引擎；由外部工具解释，如 stix2 python 库的 FileSystemSource、MemoryStore、TAXIIICollectionSource、CompositeDataSource，以及 taxii2client 的 v20 接口（TAXII 2.1 客户端连其 2.0 服务器会得到 406）。检测分析逻辑放在知识库之外，资料举 CAR 为例。",
  "coverage_expression": "不提供单一覆盖率分数。靠 Data Source 的受限标签与数据组件关系支持诸如『若有进程监控可覆盖哪些技术』的查询；明确说覆盖全部技术、覆盖某技术的全部 procedures 都不现实；『算不算覆盖』（是否告警、需要几条 analytic、是否包含控制措施与红队验证）必须由使用者自行定义；并要求映射者能解释自己覆盖了哪些 procedures。",
  "maturity_expression": "对象级 Version（MAJOR.MINOR）只表达改动程度而非质量；Contributor 记录贡献者；经验使用分四级（Reported / Reported, non-public / Underreported / Unreported）作为收录依据；deprecated 与 revoked（配合 revoked-by）是状态标记；资料未给出专门的成熟度或置信度字段，也未说明经验使用分级是否作为字段存储。",
  "lessons": [
    {"idea": "用『防御目标—防御技术—具体实现』三级替代按论文平铺的插件列表，论文只作为最底层条目的来源与引用。", "applies_to": "methods", "transfer": "adapted", "why": "ATT&CK 用稳定的 Tactics、可当骨架的 Techniques、可增长的 Sub-Techniques 解决了条目不断出现的问题；我们的 methods 以论文为单位，等于每篇论文都是顶层条目，缺少稳定中间层。"},
    {"idea": "每个条目只能有一个 canonical 父节点，同一事实只登记一次（子技术单父、procedure 不同时挂技术与子技术）。", "applies_to": "knowledge_base", "transfer": "direct", "why": "避免同一防御方法在多处重复登记，使库能说清到底覆盖了什么。"},
    {"idea": "字段分为 Tag / Field / Relationship 三类并显式标注必填与取值约束（受限列表、枚举、版本格式）。", "applies_to": "knowledge_base", "transfer": "direct", "why": "可过滤标签与自由文本分离，覆盖分析才能自动计算；我们的插件元数据目前缺少这种区分。"},
    {"idea": "把运行时 11 个暴露位置做成受控的封闭枚举，对应 Data Source 的 restricted list。", "applies_to": "runtime", "transfer": "adapted", "why": "ATT&CK 限制数据源列表是为了让『有什么数据能覆盖哪些技术』可查询；我们限制的对象换成 hook 位置与可观测张量，目的相同。"},
    {"idea": "防御对象与攻击面对象直接建立带 description 的关系（mitigates / detects），不经过中间制品，且关系本身是一等对象。", "applies_to": "knowledge_base", "transfer": "direct", "why": "库需要回答『哪个方法覆盖哪条攻击面、以何种机理覆盖、何时失效』。"},
    {"idea": "把防御从自由文本升级为独立对象（Enterprise 于 2019 年 7 月由 free text 改为 object format）。", "applies_to": "methods", "transfer": "direct", "why": "防御若只写在攻击面条目的文本里，就无法复用、计数、比较与版本化。"},
    {"idea": "覆盖不设单一百分比，输出可解释的覆盖矩阵，并要求每个方法说明其覆盖的具体过程。", "applies_to": "evaluation", "transfer": "direct", "why": "ATT&CK 明说 100% 覆盖不现实，覆盖质量取决于是否覆盖到具体 procedures；我们应输出『攻击面 × hook 位置 × 方法』矩阵与空白清单。"},
    {"idea": "区分 telemetry-only 与 enforce/alert 两种强度。", "applies_to": "runtime", "transfer": "direct", "why": "ATT&CK 用 ipconfig.exe 与 Valid Accounts 说明有些行为只值得留痕；联邦训练中正常样本与梯度会频繁命中检测点，全部告警或阻断不可行。"},
    {"idea": "版本语义表达变更程度：MAJOR 仅用于名称与范围变化且应很少发生，MINOR 用于描述、关系、引用与元数据。", "applies_to": "knowledge_base", "transfer": "direct", "why": "让使用方能判断某个方法条目变了多少、是否需要重新验证。"},
    {"idea": "废弃而不删除，并为被替代对象提供 revoked-by 指针。", "applies_to": "records", "transfer": "direct", "why": "历史实验需要继续引用旧方法，删除条目会破坏记录的可追溯性。"},
    {"idea": "内容与执行分离：元数据以数据形式存放并由单一通用解释器读取。", "applies_to": "knowledge_base", "transfer": "adapted", "why": "方法的元数据、关系与版本照搬『数据 + 解释器』很合适，但算子必须真的能执行，不能像 CAR 那样把逻辑留在库外。"},
    {"idea": "供应商无关的表达只适用于描述与分类层，不适用于数值实现层。", "applies_to": "methods", "transfer": "not_transferable", "why": "ATT&CK 的 Detection 是供应商无关的高层文字；我们的两篇论文即使目标相同，裁剪范数、噪声尺度、隐私预算、聚合规则也不同，抽象成类别会失去可复现性与可比性。"}
  ],
  "limits": [
    "ATT&CK 不是软件攻击向量的穷举，该用途属 CAPEC/CWE；也不是待办清单。",
    "覆盖全部技术不现实，覆盖某个技术的全部 procedures 同样不现实，因为无法预先知道对手的所有做法。",
    "对某些 (sub-)technique，检测可能不可行、缓解可能不可行，只能如实记录。",
    "子技术只允许一个父技术是为避免关系难以维护而作的取舍，资料承认存在多父更合理的情形。",
    "并非所有技术都能自然拆出子技术（如 Two-Factor Authentication Interception），子技术也并非总能按平台拆分（如 Valid Accounts、命令控制类技术）。",
    "抽象层次不均是既有问题：有些技术过宽、有些过窄，导致难以可视化与理解，子技术的引入正是为修复它。",
    "Linux 与 Mac 的持续威胁事件报告远少于 Windows，可用威胁数据明显不足。",
    "不应仅凭使用的技术做归因，多个组织共用同一技术。",
    "旧版 1:1 mitigation 与技术共用 ATT&CK ID，使技术 ID 并非真正唯一（这批 mitigation 已 deprecated）。",
    "检测逻辑不在 ATT&CK 内，只提供供应商无关的高层建议与引用，实现要靠外部资源。",
    "deprecated 与 revoked 对象始终保留在数据集中，使用者须自行过滤；关系本身不能被废弃或撤销。",
    "USAGE.md 提醒不要用 created/modified 时间戳判断知识库更新；STIX 的 revoked 过滤器在不同访问方式下行为不一致；TAXII 2.1 客户端连 TAXII 2.0 服务器会返回 406。",
    "维护过程『as much of an art as it is a science』；把方法论套用到新领域不一定产出 ATT&CK 模型。"
  ],
  "quotes": [
    {"supports": "§2：数据项分为 tag、field、relationship 三类，这是对象字段类型学的基础。", "text": "Items are annotated by tag if the data point is an informational reference on the technique that can be used to filter and pivot on"},
    {"supports": "§2：带星号的字段表示必填，且具体要求随战术类别而变。", "text": "Data items marked with * denote the element is required and additional information about specific requirements dependent on tactic category is in the description."},
    {"supports": "§3：技术与子技术的编号格式为 T#### 与 T####.###。", "text": "Unique identifier for the (sub-)technique within the knowledge base. Format: (technique) T####; (sub-technique) T####.###."},
    {"supports": "§3：子技术只有一个父技术，不存在一对多关系。", "text": "Sub-techniques do not have a one-to-many relationship to techniques. Each sub-technique will only have a relationship to a single parent technique and no other"},
    {"supports": "§4：缓解措施是独立对象，其与技术的关系表达『如何缓解』，即防御侧直接关联攻击侧。", "text": "Mitigations are represented by objects similar to groups and software where relationships signify how a mitigation can mitigate a technique or sub-technique."},
    {"supports": "§4 与 §8：数据源被限制在已定义列表内，目的是支持按数据源做技术覆盖分析。", "text": "This attribute is intended to be restricted to a defined list to allow analysis of technique coverage based on unique data sources."},
    {"supports": "§5：ATT&CK 自定位为衔接各组件的 mid-level 模型。", "text": "A mid-level adversary model like ATT&CK is necessary to tie these various components together."},
    {"supports": "§6：MAJOR 版本只对应名称与范围变化且应很少发生，支撑『稳定骨架、增长条目』的版本学。", "text": "Major version changes consist of name changes and scope changes which should happen infrequently."},
    {"supports": "§7：内容以 STIX 表示打包发布到 GitHub CTI 仓库，内容与解释工具分离。", "text": "A release occurs when the changes to the STIX representation of ATT&CK are bundled and released to the GitHub CTI repository [9] along with any updates to the ATT&CK website."},
    {"supports": "§8：覆盖率不是框架承诺的指标，100% 覆盖被明确称为不现实。", "text": "it's important to note that in general, coverage of every ATT&CK technique is unrealistic."}
  ]
}
```
