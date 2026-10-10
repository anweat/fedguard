# ocsf：Open Cybersecurity Schema Framework（资料为《Understanding the Open Cybersecurity Schema Framework》，作者 Paul Agbabian，2026 年 4 月，Status: RFC，Version 1.17，对应 schema version 1.0.0）

## 1. 要解决的问题

这份资料描述的对象是 Open Cybersecurity Schema Framework（OCSF，开放网络安全模式框架）及其 taxonomy（分类体系），以及用该框架构建的核心网络安全事件 schema（模式）。

它服务的对象是四类 persona（角色）：_author_（作者，创建或扩展 schema 的人）、_producer_（生产者，原生按该 schema 产生事件，或从其他 schema 翻译产生事件的人）、_mapper_（映射者，把其他来源的事件翻译或创建为该 schema 的事件的人）、_analyst_（分析者，搜索数据、针对 schema 编写规则或分析、生成报告的最终用户，也可称为 _consumer_（消费者））。资料举了三个例子：某厂商既做外部格式到该 schema 的翻译、又扩展 schema 以容纳来源特有属性或操作，它同时扮演 mapper 与 author；把数据收进 SIEM、针对事件写规则并在调查中搜索事件的 SOC 分析师扮演 analyst；以 OCSF 形式原生发出事件的厂商是 data producer（数据生产者）。

它要解决的问题是：让任意原始事件都能被映射到单一事件类，并让不同数据源在同一语义下保持一致、准确与精确；框架本身由一组 data types and objects（数据类型与对象）、一个 attribute dictionary（属性字典）和 taxonomy（分类体系）构成，并用 profiles（叠加层）和 extensions（扩展）在不修改核心 schema 的前提下容纳跨类别补充信息与厂商/客户自有内容。

它明确说自己不做的事包括：框架不限于网络安全领域、也不限于事件，只是初始焦点放在网络安全事件的 schema 上；OCSF 对存储格式、数据采集与 ETL 过程保持无关（agnostic）；核心 schema 有意做到与具体实现无关；内容发布权也不集中在 OCSF 一方，原文在与 MITRE ATT&CK 对比时指出“OCSF is open and extensible by vendors, and end customers while the content within MITRE ATT&CK is released by MITRE”。资料还说明 OCSF 包含 Symantec（Broadcom 的一个部门）开发的 ICD Schema 的概念与部分内容，经泛化后以 Apache 2 许可证开放。

## 2. 核心对象

先说明一点：资料里**没有**“战术（tactic）、技术（technique）、缓解措施（mitigation）、数据源（data source）、规则（rule）、测试（test）”这些对象类型；MITRE ATT&CK 只在“对比”一节和 profile 的内容中被提到。OCSF 自己的对象类型是它的 taxonomy 构造（taxonomy constructs）与 schema 制品，下面逐个列出。

资料把 taxonomy 的基本构造定为 5 个：Data Types, Attributes and Arrays（数据类型、属性与数组）、Event Class（事件类）、Category（类别）、Profile（叠加层）、Extension（扩展）。

### 2.1 Data Type（数据类型）

- **primitive data types（原始数据类型）**：string、integer、浮点数、boolean，是标量数据类型的基础；无必填性概念。
- **scalar data types（标量数据类型）**：在原始类型之上定义，例子有 Timestamp、IP Address、MAC Address、User Name；资料说明“Most scalar data types have constraints on their valid values or ranges”，即大多有值域或范围约束。
- **Enum integer types（枚举整数类型）**：被约束到一组特定整数值；框架尽量用它替代字符串以保证一致性。
- **`timestamp_t`**：基于 Unix 时间、即自 Unix 纪元起的毫秒数，是时间属性的名义数据类型。
- **`datetime_t`**：RFC3339 的人类可读形式。
- **`string_t`**：字符串类型，被用于实体对象的 `uid` 与 `name`。
- 资料的 Appendix B 不列具体数据类型，而是指向 https://schema.ocsf.io/data_types 查看数据类型及其校验约束；因此具体数据类型的完整清单与取值约束**资料未说明**。

### 2.2 Attribute（属性）与 Attribute Dictionary（属性字典）

- **name（名称）**：某个可校验数据类型的唯一标识名。约束来自 Appendix A：必须是合法 UTF-8 序列；必须全小写；用下划线连接单词；除下划线外无特殊字符；保留属性以下划线开头；表示历史信息之外用现在时。
- **type（类型）**：标量或复杂类型；属性字典收录全部可用属性及其类型，是框架的积木，event class 只是从字典中取出的特定属性集合。
- **requirement flag（要求标记）**：取值为 Required、Recommended、Optional 三种；但资料明确说属性本身没有要求标记，“Attributes themselves do not have a requirement flag, only within the context of event classes.”，即只在事件类上下文里有必填性。
- **attribute group（属性分组）**：分为 _Primary_、_Classification_、_Occurrence_、_Context_ 四组。Classification 与 Occurrence 与事件类无关、在字典中随属性定义；Primary 与 Context 的分组取决于该属性在某个事件类中的用法。Primary 属性通常按事件类被标为 Required 或 Recommended；Base Event 中的 Primary 属性适用于所有事件类。Classification 属性作为 Base Event 的一部分被标为 Required，其值名义上是 Unknown 或 Other，并在具体事件类中被覆盖。Occurrence 属性是时间与时间范围相关属性，要求级别任意。Context 属性用于典型用例的变体、增强含义或丰富内容，要求级别任意、但最常被标为 Optional。
- **description（描述）**：一般含义处处相同；当含义被重载（overloaded）时，字典中的描述保持泛化，并包含一条 “see specific usage” 指令，在事件类上下文中覆盖其描述。
- **sibling string attribute（同名兄弟字符串属性）**：与枚举属性同前缀、去掉后缀。例如 `activity_id` 与 `activity`，`severity_id` 与 `severity`。它是可选的；但如果枚举值是 Other（99），则该兄弟字符串**必须**填入自定义标签（且不能填 “Other”）。对包括 Unknown 在内的已定义枚举值，枚举标签文本**可以**填入兄弟字符串；若枚举属性是 Required，则整数属性与兄弟字符串**应该**都被填充。
- 命名后缀约定（标准后缀）：`_id, _ids, _uid, _uuid, _ip, _name, _info, _detail, _time, _dt, _process, _ver, _list`。
- 复数命名：表示多个实体时属性名应复数化、值类型为数组，例如 `process.loaded_modules`；避免重复词，例如 `device.device_ip` 应为 `device.ip`；尽量避免缩写，`ip`、`os` 是少数例外。
- 厂商扩展属性：用 3 字母 moniker 作前缀避免重名，例如 `aws_finding`、`spk_context_ids`。

### 2.3 Object（对象，即复杂数据类型）

- **构成**：一组上下文相关的属性集合，通常表示一个实体，并可包含其他对象；每个对象本身也是一个数据类型。例子：Process、Device、User、Malware、File。
- **校验**：复杂数据类型可依据其特定结构与属性要求被校验。
- **命名**：对象名永远是单数，无论事件里出现多少个实例。
- **`uid` / `name`**：凡是 producer 或 mapper 为实体对象填入标识符的地方，都使用核心属性 `uid`；实体对象按约定还有一个对应的 `name` 属性；两者都是 `string_t` 类型。资料未说明这两个字段各自的必填性。

### 2.4 Array（数组）

- **支持的类型**：可承载任何数据类型。
- **命名（首选）**：一般使用以 “s” 结尾的复数形式，例子有 `category_ids`、`attacks`（MITRE ATT&CK techniques）。
- **可选 `_list` 后缀**：当复数化有歧义、别扭或可能与另一个属性名冲突时使用，例子有 `finding_info_list`；资料说该后缀不是必需的，只应在提高可读性或避免歧义时使用。
- **字典层表示**：数组属性名在必要时可用 `_list`；数组元素的类型始终用单数形式定义（元素类型 `finding_info`）；单数属性可以与数组属性并存，各自表达不同语义（`finding_info` 是单个实例，`finding_info_list` 是实例集合）。
- **可选单数属性**：单数属性是可选的，只应在它带来有意义区分或提高可解释性时定义。

### 2.5 Event Class（事件类）与 Base Event（基础事件类）

- **定位**：事件由事件类的实例表示；事件类是一组特定属性与对象，代表某一时点的一条日志行或一次遥测提交，其语义描述“发生了什么”：某个 activity（活动）、disposition（处置），或两者。
- **`class_uid`**：每个事件类有一个 schema 内唯一的 `class_uid`，是 Required 属性，其值覆盖 Base Event 的名义值 `0`。
- **`class_name`**：事件类的友好名由 schema 定义，可选地填入 `class_name`，例如 File System Activity 或 Process Activity。
- **`category_uid`**：每个事件类都有 `category_uid`，指明它属于哪个 Category；一个事件类只能属于一个类别。
- **`category_name`**：类别的友好名由 schema 定义，可选地填入 `category_name`。
- **`activity_id`**：每个事件类都有 `activity_id` 枚举属性，取值被约束到适合该类的一组值；按约定其枚举标签是现在时祈使式，例如 File System Activity 的 Open、Process Activity 的 Launch。
- **`activity_name`**：枚举标签可选地填入 `activity_name`，它是 `activity_id` 的兄弟属性，作为 Classification 组属性遵循 `_name` 后缀约定。
- **`type_uid`**：Required 属性，由事件类（`class_uid`）与该类活动（`activity_id`）组合而成，在整个 schema 内唯一；计算式为 `class_uid` `* 100 + activity_id`，例子：`type_uid` = `3001 * 100 + 1 = 300101`。
- **`type_name`**：`type_uid` 的友好名，是两部分名字的组合，例子 “Authentication: Logon”。
- **`metadata`**：Base Event 的 Required 属性，是一个对象，装入来自源事件之外的数据。
- **`observables`**：Base Event 的 primary 数组属性，其内容是 Observable 对象数组。
- **`enrichments`**：Base Event 的数组属性，其内容是 Enrichment 对象数组。
- **`profiles`**：Base Event 的可选数组属性，用一组 profile 值声明该事件应用了哪些叠加层；该属性缺失意味着不添加任何 profile 属性。
- **`unmapped`**：可选属性，用于放入无法映射到 schema 的原始字段。
- **`raw_data`**：可选属性，按从来源收到的原样保存事件数据，未解析，用 String 类型表示。
- **`constraints`**：事件类可声明的约束，见 2.12。
- **`associations`**：事件类可声明的属性关联，见 2.13。
- **Base Event 的要求等级示例**：Required 例子有 `class_uid`、`category_uid`、`activity_id`、`severity_id`；Recommended 例子有 `timezone_offset`、`status_id`、`message`；Optional 例子有 `activity_name`、`start_time`、`end_time`、`count`、`duration`、`unmapped`。
- **时间属性（来自 Base Event，可出现在所有事件中）**：`original_time: string`（事件生产者产生的原始事件时间，时间格式不由 OCSF 规定，因此是非校验字符串）；`time: timestamp_t`（归一化后的事件发生时间，即修正源时钟偏移与批量提交延迟并转换为 OCSF `timestamp_t` 之后的时间）；`processed_time: timestamp_t`（事件处理器把事件或事件批次发给事件消费者的时间）；`logged_time: timestamp_t`（事件消费者记录该事件的时间，必须大于等于归一化后的事件发生时间）；`modified_time: timestamp_t`（事件最后一次更新或富化的时间，必须大于等于归一化发生时间，与 `logged_time` 的大小关系不定）；`start_time/end_time: timestamp_t`（事件代表一段有时间范围的活动、或用于事件聚合时使用，聚合场景还要填 `count` 整数属性）。
- **`timezone_offset`**：Integer 类型，表示所报事件时间相对 UTC 领先或落后的分钟数，取值 -1,080 到 +1,080；它是 Base Event 的 Recommended 属性。
- **术语**：Event Producer（事件生产者，对应 producer 角色）、Event Consumer（事件消费者，对应 analyst 角色）、Event Processor（事件处理器，处理并记录收到的事件，含 ETL 链，对应 mapper 与 analyst 角色）。
- **继承约定**：按约定所有事件类都扩展 Base Event 事件类，Base Event 的属性称为 Base Attributes；资料脚注补充“The internal source definition of an OCSF schema can be hierarchical but the resulting compiled schema does not expose sub classes.”。

### 2.6 Category（类别）

- **定位**：Category 组织代表某个特定领域的事件类，例如访问日志、审计日志、网络与系统事件中的不同事件类。
- **`category_uid`**：每个类别有唯一的 `category_uid`，是类别标识符。
- **`category_name`**：类别 ID 有友好名属性 `category_name`，例如 System Activity、Network Activity、Audit 等。
- **用途**：把事件类分组有多个目的，包括作为某个事件域的容器、文档便利与检索、报表、存储分区或访问控制等。
- **结构性**：资料说“Categorization is weakly structural while event classification is strongly structural”，即分类是弱结构性的，事件分类是强结构性的（定义具体属性、其要求以及该事件类的特定枚举值）。
- 资料给出的类别示例表包含 System Activity、Network Activity、Identity & Access Management、Findings、Discovery、Application Activity 六列及其下属事件类。

### 2.7 Profile（叠加层）

- **定位**：Profiles 是叠加在事件类和对象之上的东西，实际上是一个动态 mix-in（混入）的属性类，带有自己的要求和约束；它在不依赖类别的情况下为一组事件类增补属性。
- **应用方式**：多个 profile 可以通过 Base Event 可选属性 `profiles` 的数组值加到事件类上；producer 或 mapper 在可选应用时把它混入事件类和对象。
- **命名/标识**：资料把 Profiles 类比为 MITRE ATT&CK 的 Matrices，“which have unique names”；同时提到 mapper 可以把 “the profile ID” 及其关联属性加入映射后的事件；在 Extensions 一节又写道“As with categories, event classes and profiles, extensions have unique IDs within the framework as well as versioning.”。资料未给出 profile ID 的具体编码格式。
- **过滤**：支持该 profile 的事件类与事件实例可以通过 `profiles` 属性跨所有类别和事件类被过滤，形成另一个分类维度。
- **要求不可覆盖**：用 profile 定义的属性带有不可覆盖的要求，因为 profile 本身是可选的，应用 profile 被假定为确实需要并能填这些属性。
- **类内建 profile 属性**：有些类（例如 System Activity 类）把 profile 属性内建进类定义，例如 `Host` profile 的 `device` 与 `actor`；当类定义包含这些 profile 属性时，它仍然在类定义中为该 profile 注册，以便匹配按该 profile 的跨事件检索；此时以类定义中的属性要求定义为准。
- **核心 schema 的 profile 及属性**（资料表格）：Security Control 为 `attacks`、`disposition_id / disposition`、`malware`；Host 为 `actor`、`device`；Cloud 为 `api`、`cloud`；Container 为 `container`、`namespace_pid`；Linux 为 `group`、`euid`、`egid`、`auid`。
- **Date/Time profile**：一个特殊 profile，在 schema 中任何出现 `timestamp_t` 属性的地方增加一个 `datetime_t` 类型的兄弟属性。
- **其他可能方向**：面向产品的 profile（Firewall、IDS、VA、DLP 等）、面向平台的 profile（Mac、Linux、Windows）；核心 schema 通过 Linux 平台扩展自带 Linux profile；厂商可通过扩展加 profile，例如 Splunk Technical Add-ons 可以定义把 Splunk 的 `source`、`sourcetype`、`host` 加到所有事件上的 profile。
- **应用示例**：System Activity 类**会**包含 Host profile，**可能**包含 Security Controls 或 Cloud profile；Network Activity 类**可能**包含 Host profile，**可能**包含 Security Controls 或 Cloud profile；Identity & Access Management 类**会**包含 Host profile（因为 `actor.user`），**可能**包含 Cloud profile，**不会**包含 Security Control profile。

### 2.8 Extension（扩展）

- **定位**：扩展让 schema 在不修改核心 schema 的情况下被扩展；新属性、对象、事件类、类别和 profile 都可以由扩展提供。一个 schema 是核心 schema 实体与扩展的聚合。
- **用法**：厂商或客户可以创建新 schema 或增强已有 schema；扩展也可以把非必要的 schema 域抽出去，让 schema 保持精简；对核心 schema 的扩展以和新 schema 相同的方式使用该框架，可选地由字典创建类别、profile 或事件类。
- **命名**：扩展可以加与核心 schema 同名的属性，但资料说出于多个原因这不是好做法；对厂商特有扩展，最佳实践是用与已注册扩展区间关联的短标识符给 schema 制品加前缀。
- **ID 与版本**：扩展在框架内有唯一 ID，也有版本管理；扩展有自己的版本、可以按自己的节奏变化，但必须与它所扩展的核心 schema 的 major 版本保持兼容与一致；可选属性 `extension`（类型 Schema Extension）携带某个扩展的版本。
- **ID 偏移与注册**：为预留 ID 空间并公开扩展，需要在 OCSF Extensions Registry 中为扩展名添加一个 UID，避免与核心或其他扩展 schema 冲撞；例子是 Development / dev / 999 / “The development schema extensions”；“New categories and event classes will have their unique IDs offset by the UID.”。
- **现有扩展**：截至资料写作时，有两个平台扩展增强核心 schema：Linux 扩展增加一个 profile，Windows 扩展向 System Activity 类别增加三个类。
- **演进用途**：扩展还用于开发新的 schema 制品，这些制品之后可能被提升（promoted）进核心 schema 或平台扩展；也可以构造全新的 schema。
- **Dev 扩展示例表**：在核心 Findings 类别下加 Incident Creation、Incident Associate、Incident Closure、Incident Update、Email Delivery Finding；新增 Policy、Remediation、Diagnostic 三个扩展类别，分别含 Clipboard Content Protection、Compliance、Compliance Scan、Content Protection、Information Protection；File Remediation、Folder Remediation、Startup Application Remediation、User Session Remediation；CPU Usage、Memory Usage、Throughput。
- **呈现**：Schema Browser 会以 superscript（上标）标注扩展。

### 2.9 Observable（可观测项）

- **定位**：Observable 是被 Base Event 的 primary 数组属性 `observables` 引用的对象，由源事件中产生或映射出来的其他属性填充；它把安全相关指标集中到一处，而不管这些指标在事件类里散落在多少地方，本质上是一组属性摘要的数组。
- **`name`**：对事件内的标量属性，填事件内的全限定属性名；对复杂（对象类型）属性，`name` 是指向该属性的指针或引用。
- **`value`**：对事件内的标量属性，填该属性的值；对复杂（对象类型）属性，由于对象有不止一个值，`value` 不填。
- **`type_id`**：声明该属性的类型是什么。资料对事件内标量属性说明三个 observable 属性都会被填充。
- **示例**：`{"name": "actor.process.name", "type": "Process Name", "type_id": 9, "value": "Notepad.exe"}`；`{"Name": "tls.ja3_hash", "Type": "Fingerprint", "Type_id": "30"}`；`{"name": "file.name", "type": "File Name", "type_id": 7, "value": "Notepad.exe"}`。
- **例子说明**：一个 IP 地址可能填充多个属性（`public_ip, intermediate_ips, ip`，作为 Endpoint、Device、Network Proxy 等对象的一部分）；分析师想知道某个 IP 是否出现在任何事件里时，从 Base Event 的 `observables` 属性搜索比记住所有可能带 IP 的属性更容易。

### 2.10 Enrichment（富化项）

- **定位**：Enrichment 是被 Base Event 数组属性 `enrichments` 引用的对象，描述在采集或事件处理期间、但在诸如存储这类不可变操作之前加入事件的信息，例如对 IP 地址查位置数据、对域名或文件哈希查 IOC。
- **`name` 与 `value`**：与 Observable 类似，这两个属性是必填的，用于指向被富化的事件类属性。
- **`type`**：只有 Recommended 的 `type` 属性，没有 `type_id` 枚举，因为不存在预先定义好的、被标记为可富化的属性集合。
- **`data`**：一个 JSON 属性，以处理系统已知的形式承载任意富化内容。
- **`provider`**：出现在资料示例中（示例值为 `media.defense.gov`），资料未说明其必填性。
- **时间要求**：与和事件时间同步的 Observable 不同，富化被假定与事件时间之间存在延迟，因此在富化时**应该**填 Base Event 的 `metadata`.`modified_time`。

### 2.11 Metadata（元数据）

- **定位**：`metadata` 是 Base Event 的 Required 属性所引用的对象，顾名思义装的是源事件之外的数据；其中一些属性是可选的，例如 `logged_time` 与 `uid`，而 `version` 属性是必填的——即该事件的 schema 版本。日志系统**可以**在存储时赋值 `logged_time` 与 `uid`。
- **`version`**：必填，事件的 schema 版本；资料脚注说明扩展事件应把 `metadata.version` 填为扩展后的 schema 版本。
- **`logged_time`**：可选，可能由日志系统在存储时赋值。
- **`uid`**：可选，可能由日志系统在存储时赋值；示例值是一个 GUID。
- **`modified_time`**：可选，事件在分析或存储前被富化或以某种方式变更时填写。
- **`processed_time`**：可选，通常在事件被采集并提交给日志系统时填写。
- **`sequence`**：出现在资料的示例 JSON 中（示例值 69），资料未说明其含义与必填性。
- **`extension`**：可选属性，类型为 Schema Extension，携带某个扩展的版本；资料未明确说明它位于哪个对象之下。

### 2.12 Constraint（约束）

- **定位**：Constraint 是一条有文档、且受校验的规则，要求某个类的指定 Recommended 属性中至少有一个被填充；约束用于那些无法在所有用例中把某属性设为 Required、但为了含义无歧义又必须至少提供一个的类。约束中的属性必须是 Recommended。
- **`at_least_one`**：一组 Recommended 属性中至少填一个；示例为 `ip`、`mac`、`name`、`hostname`。
- **`just_one`**：一组 Recommended 属性中恰好填一个；示例为 `privileges`、`group`。

### 2.13 Association（关联）

- **定位**：事件类内的属性有时彼此关联，某些情况下事件中只有其中一个，另一个可以在处理或存储时被查出来；OCSF 通过 association 构造在类定义里表达这种关系。
- **方向**：资料例子（来自 Authentication 类）是 `actor.user` 与 `src_endpoint`、`dst_endpoint` 与 `user` 之间的双向关联，并说明双向很常见，单向关联在其他情形下也可能存在。
- **用途与时间**：对具备查找服务的自动化处理系统有用，用于填充无法由源事件生产者提供的属性；此时应像其他富化一样填 `processor_time`（原文如此，未写成 `processed_time`）。

### 2.14 攻防侧内容：`attacks`、`malware`、`disposition_id`

- **`attacks`**：作为数组命名的例子出现，原文标注为“attacks (MITRE ATT&CK techniques)”；它是 Security Control profile 的属性之一，被叠加进注册该 profile 的事件类。
- **`malware`**：Security Control profile 引入的对象之一，资料称该 profile 把 MITRE ATT&CK Attack 与 Malware 对象加到 System Activity 类上。
- **`disposition_id` / `disposition`**：`disposition_id` 表示事件类活动在事件捕获时刻的结果或状态，是一个带标准取值集合的枚举，例如 Blocked、Quarantined、Deleted、Delayed；只有注册了该 profile 的事件类才能有 `disposition_id`，但所有事件类都有 `activity_id`。`disposition` 是它的兄弟字符串；按 Appendix A，`disposition_id` 的枚举标签用过去时（例如 Blocked）。资料明确写道，截至写作时 `disposition_id` 只通过 Security Controls profile 加到核心 schema 的类上。资料未说明“缓解措施”“规则”“测试”这类对象。

## 3. 编号与层级

- **事件类编号**：每个事件类有 schema 内唯一的 `class_uid`，是 Required 整数，取值覆盖 Base Event 的名义值 `0`。
- **类别编号**：每个类别有唯一的 `category_uid`。
- **组合编号**：`type_uid` 是 Required 属性，由 `class_uid` 与 `activity_id` 组合而成，在整个 schema 内唯一；计算式为 `class_uid * 100 + activity_id`，例子为 `3001 * 100 + 1 = 300101`，其友好名 `type_name` 由两部分名字组合，例如 “Authentication: Logon”；资料示例中 `type_uid` 100111 对应 “File System Activity: Decrypt”（`class_uid` 1001、`activity_id` 11）。
- **后缀与编号语义**：分类值在 schema 内唯一时属性名以 `_uid` 结尾，这类属性是整数、由 schema 定义预置（必须按 schema 定义填充）；有友好名或标题的 schema 唯一属性用同一前缀的 `_name` 后缀，例如 `class_uid` 与 `class_name`、`category_uid` 与 `category_name`；其他带 `_uid` 约定的属性可以是字符串或整数，取决于用途，但多数是字符串。全局唯一的值以 `_uuid` 结尾，没有友好名，例如 GUID。枚举整数类型的属性以 `_id` 结尾，枚举属性数组以 `_ids` 结尾。
- **枚举编号约定**：每个枚举类型都有两个共同值：整数 0 表示 `Unknown`、99 表示 `Other`；`Unknown` 也是默认值。
- **层级**：层级是 Category（类别）包含 Event Class（事件类），事件类再由 attributes 与 objects 组成；资料明确说 MITRE ATT&CK 有 Sub-techniques 而 OCSF 没有 Sub-Event Classes，并在脚注中说内部源定义可以分层，但编译后的 schema 不暴露子类。Profile 不构成层级，而是“另一个分类维度”，可跨类别与事件类过滤。Extension 也不构成核心层级，而是核心 schema 实体与扩展的聚合。
- **扩展的编号空间**：扩展在框架内有唯一 ID，扩展名必须唯一（如 dev）；扩展要在 OCSF Extensions Registry 里登记 UID 以预留 ID 空间，新增类别与事件类的唯一 ID 以该 UID 偏移；资料说明预留标识符区间登记在项目 GitHub 仓库的一个文件里。Schema Browser 会用上标标注扩展。
- **命名规则**：类、类别、活动都有 schema 定义的友好名（`class_name`、`category_name`、`activity_name`），它们是可选填充；`activity_id` 枚举标签是现在时祈使式，`disposition_id` 枚举标签是过去时；属性命名遵循 Appendix A 的小写、下划线、保留字前缀下划线等规则。
- **同一事物在多处出现时的处理**：字典中的属性在 schema 各处含义相同，只有被重载的属性例外，此时字典描述泛化并附 “see specific usage”，由事件类上下文覆盖描述；单数属性可与数组属性并存以表达不同语义（`finding_info` 与 `finding_info_list`）；枚举值与其兄弟字符串属性可以同时出现；类内建了某 profile 的属性时仍要为该 profile 注册，以便按 profile 检索，且此时以类定义的要求为准；扩展可以取与核心相同的属性名，但资料明确说这不是好做法。

## 4. 对象之间的关系

资料中出现的关系类型与方向如下。

- **类别包含事件类（Category ⊃ Event Class）**：Category 组织代表某个领域的事件类；一个事件类只能属于一个类别。方向是类别到事件类的一对多包含。
- **Base Event 到所有事件类的继承式扩展（event class extends Base Event）**：按约定所有事件类都扩展 Base Event，Base Event 的属性称为 Base Attributes；资料脚注说明内部源定义可以是分层的，但编译后的 schema 不暴露子类。方向是事件类指向 Base Event。
- **Profile 叠加到事件类与对象（Profile → Event Class / Object）**：Profile 是叠加层、动态 mix-in；多个 profile 通过 Base Event 可选数组属性 `profiles` 加到事件类上，由 producer 或 mapper 应用；profile 也可以应用到特定的类、对象或类别。资料还写明“Existing profiles can be applied to extensions, and new extension profiles can be applied to core event classes and objects as well as to other extensions.”，即新扩展 profile 可以指向核心事件类、核心对象以及其他扩展，核心已有 profile 也可以指向扩展，方向是双向可叠加。
- **类为 profile 注册（Event Class registers for Profile）**：事件类为 profile 注册，从而让“按 profile 的查询”能跨所有类别与事件类命中；即便类把 profile 属性内建进定义也仍然注册。
- **事件类由字典属性组合而成（Event Class ← Attribute Dictionary）**：事件类是字典中特定属性集合的组装，属性可来自字典，也可能是嵌套对象。
- **约束关系（Constraint → Event Class 的 Recommended 属性集合）**：`at_least_one` 与 `just_one` 把类内若干 Recommended 属性绑定成“至少一个/恰好一个”的关系。
- **关联关系（Association，属性 ↔ 属性）**：在类定义内表达属性之间的关联，可双向也可单向；资料给出的 Authentication 类例子是 `actor.user` 与 `src_endpoint`、`dst_endpoint` 与 `user`。
- **组合关系（Composition）**：`type_uid` 由 `class_uid` 与 `activity_id` 组合，`type_name` 由两部分名字组合。
- **指向关系（Observable → 任意属性）**：Observable 的 `name` 指向事件中的属性（标量时填全限定名，对象时填指针或引用），把散落各处的安全指标汇总到一处，并且“irrespective of event class”。
- **指向关系（Enrichment → 事件类属性）**：Enrichment 的 `name` 与 `value` 必须指向被富化的事件类属性；富化发生在采集或处理期间、存储这类不可变操作之前；富化时应填 `metadata.modified_time`。
- **扩展聚合关系（Schema = core entities + extensions）**：扩展可新增属性、对象、类别、profile、事件类，并加入到核心 schema 的聚合中。
- **攻击侧与防御/检测侧的连接**：资料里没有独立的攻击对象图或缓解措施对象。攻击侧内容以 `attacks`（MITRE ATT&CK techniques）与 `malware` 对象的形式，通过 **Security Control profile** 叠加进事件类；防御/处置侧用同一个 profile 的 `disposition_id`（Blocked、Quarantined、Deleted、Delayed 等）表达事件捕获时活动的结局。也就是说，攻击技术与处置结果不是直接互相引用，而是共同挂在同一个 event class 上，攻击技术以 technique 标识进入事件；原文在对比中说 Profiles 类似 Matrices、Type IDs 类似 Procedures，并说 Profiles 可以像 Matrices 过滤 Techniques 与 Tactics 那样过滤事件类与类别。原文的例子是：“For example, a `Security Controls` profile that adds MITRE ATT&CK Attack and Malware objects to System Activity classes avoids having to recreate a new event class...”。资料还限定：“Only event classes that register for the profile may have a `disposition_id` but all have an `activity_id`.”。

## 5. 抽象层次的选择

- **单个条目的粒度**：事件类代表某一时点的一条日志行或一次遥测提交，语义描述“发生了什么”，即某个活动、某个处置或两者；资料说 schema 的意图是让**任何原始事件都能映射到单一事件类**（“It is the intent of the schema to allow for the mapping of any raw event to a single event class.”），并且这一目标是通过 composition（组合）而不是多重继承达成的。
- **属性的必要性粒度**：为了完整捕获丰富数据源的信息，很多属性可能被设为必需；但并非每个数据源对同一观察行为都发出同样信息，因此事件类只规定哪些字典属性是必要的（Recommended 或 Required），其余为 Optional；除 Base Event 的 Classification 属性外，属性要求始终在事件类定义范围内，而不绑定到属性自身。
- **类别与事件类的抽象分工**：Categorization 是弱结构性的，事件分类是强结构性的（定义具体属性、其要求以及该事件类的特定枚举值）。资料把“找到合适的类别粒度”称为重要的建模话题，并列出一串没有给出标准答案的问题：来自这些服务与主机的日志是否提供同样的上下文或信息？是否存在一组放在同一个类别里说得通的事件类？NLB 访问日志提供的信息是否与 Flow 日志相似？来自主机的网络流量与防火墙或路由器提供的信息是否相似？它们是否以相同方式构造？是否共享属性？把它们归一化到同一类别下是否会掩盖这些日志的含义？由此产生的类别自身是否说得通，还是会失去上下文含义？
- **新条目 vs 变体的判定**：资料给出的明确机制是使用 profile：“Using profiles, some of these overlapping categorical scenarios can be handled without new partially redundant event classes.”，即当重叠的分类场景出现时，用叠加层而不是新增部分冗余的事件类；profile 的 mix-in 方式“allows for reuse of event classes vs. creating new classes one by one that include the same attributes”。另外还有扩展路径：新制品可以先在开发扩展里存在，之后被提升进核心 schema 或平台扩展；扩展也可以把非必要的 schema 域抽出去，让 schema 保持精简。
- **不收录内容的处理**：并非所有原始字段都能映射到 schema，未映射字段可以放进可选的 `unmapped` 属性；`raw_data` 以未解析的 String 保存来源原样数据；开放式富化内容用通用字符串属性加任意 JSON `data` 承载；枚举里没有对应值时用 `Other`（99）并把自定义标签放进兄弟字符串属性。
- **准入标准**：资料没有给出评审式或门槛式的准入标准（**资料未说明**）。它只给出机械性要求：类别必须在 `categories.json` 中定义，类才能属于该类别；所有属性都必须在 `dictionary.json` 中定义；每次 schema 变更都必须更新 `version.json`；扩展要登记 UID 以避免与核心或其他扩展冲撞；属性命名要遵循 Appendix A 的规范。

## 6. 稳定部分与易变部分

- **希望很少变的部分**：框架的 5 个基本构造（数据类型/属性/数组、事件类、类别、profile、扩展）；数据类型与属性字典作为积木；Base Event 及其 Base Attributes；事件类的“组合而非多重继承”原则；命名与后缀约定；profile 与 extension 这两种扩展机制。资料说“The convention is that the major version, after `1.0.0`, or first part, remains the same while versions of the schema remain backwards compatible with previous versions of the schema and framework.”，即 major 版本在 1.0.0 之后保持不变，同时 schema 保持向后兼容。
- **预期不断增长的部分**：新的事件类、属性、对象和 profile 会带来 minor 版本增加（“As new classes, attributes, objects and profiles are added to the schema, the minor version, or second part of the version increases.”）；类别与枚举也可以增长；扩展有自己的版本、可以按自己的节奏变化；扩展还承载开发中的制品，之后可能被提升进核心 schema 或平台扩展。
- **版本管理**：核心 schema 使用 Semantic Versioning Specification（SemVer），例如 `0.99.0`，向事件消费者表明事件里可能有哪些属性、类与类别结构是什么；第三部分保留给不破坏 schema 的修正，例如文档或标题变更。每次 schema 变更都必须更新 `version.json`。`metadata.version` 是事件里必填的 schema 版本；扩展事件应把 `metadata.version` 填为扩展 schema 的版本；可选属性 `extension`（类型 Schema Extension）携带扩展版本。扩展必须与所扩展核心 schema 的 major 版本兼容一致。扩展 ID 空间通过 OCSF Extensions Registry 预留，预留区间登记在项目 GitHub 仓库的一个文件里；新增类别与事件类的 ID 以扩展 UID 偏移。
- **新增与废弃流程**：新增路径在资料中有描述（加入字典/事件/对象/类别/profile；注册扩展 UID；更新版本文件；开发扩展制品可被提升）。**废弃（deprecation）流程、弃用标记与迁移策略，资料未说明。**

## 7. 内容与执行的分离

- **内容形式**：schema 框架定义文件与由此产生的规范 schema 都写成 JSON。资料给出的仓库结构为：`categories.json`（定义类别，类要属于某个类别时该文件必须存在）、`dictionary.json`（所有属性必须在此定义）、`version.json`（schema 的 semver 版本，每次 schema 变更都必须更新该文件）、`enums/`（枚举定义，若枚举被共享则使用）、`events/`（事件类）、`extensions/`（扩展，每个扩展有相似结构）、`includes/`（共享文件）、`objects/`（对象定义）、`profiles/`（profile）。扩展则是在 `extensions` 目录下用唯一扩展名创建新目录，目录结构与顶层相同，按需包含 `categories.json`（用于定义新事件类别并预留类 ID 区间）、`dictionary.json`、`events/`、`objects/`、`profiles/`。
- **解释与执行者**：schema browser（https://schema.ocsf.io）以可导航门户的形式可视化类别、事件类、字典、数据类型、profile 与扩展；可通过其菜单生成某个事件类的 schema 与某个类的事件示例；它还通过 server APIs 充当校验服务器，API 文档同样可以从浏览器获得。校验的强制手段是必需属性（尤其是需要保持最少量的 classification 属性）、属性数据类型校验以及事件类结构；constraints 是“subject to validation”的规则；Recommended 属性不受校验、也没有默认值。
- **表达逻辑的上限**：只能表达字典里已定义的属性与数据类型，枚举只能取已定义的整数集合；无法映射的字段进 `unmapped`，来源原样数据进未解析的 `raw_data`；开放式富化只能用通用字符串加任意 JSON `data`，且没有 `type_id` 枚举，只有 Recommended 的 `type`；含义被重载的属性只能靠字典里泛化描述加 “see specific usage” 在类上下文中覆盖；一个事件类只能属于一个类别；profile 的属性要求在类里不可被覆盖；编译后的 schema 不暴露子类，尽管内部源定义可以分层。
- **超出时的做法**：通过 extension 增补新的属性、对象、类别、profile、事件类；扩展可把非必要域抽出以保持 schema 精简；可以构造全新 schema（脚注说明“An extension does not need to extend the core schema base class if it is a new schema.”）；开发中的 schema 制品先放在扩展里，之后再提升进核心或平台扩展。

## 8. 覆盖与成熟度的表达

- **覆盖的表达**：事件类为 profile 注册，应用 profile 的事件可以通过 `profiles` 属性跨类别、跨事件类被检索，形成另一个分类维度。资料的原话例子是：对类的事件查询会返回全部事件（无论有无安全信息），而只按 profile 查询会返回所有支持该 Malware profile 的事件类里的事件；即便类把 profile 属性内建进定义，也仍然注册，以匹配按该 profile 的检索。因此在 OCSF 里，“某个类是否有某类安全信息”是靠 profile 注册与过滤查询表达的。
- **填充完备性的表达**：每个属性在事件类上下文里有 Required / Recommended / Optional 要求标记；Required 属性消费者可以确信存在且有值，无法填充时由事件类定义默认值（通常是 Unknown）；Recommended 应该填但不保证，且不受校验、无默认值；Optional 用于增加上下文。资料还建议数据接入方对 Recommended 属性给予比 Optional 更高的权重。
- **约束层面的表达**：`at_least_one` 与 `just_one` 表达“这组 Recommended 属性里至少要有一个 / 恰好有一个”。
- **结构层面的表达**：`metadata.version` 告诉消费者事件里可能找到哪些属性、类与类别结构是什么。
- **扩展的呈现**：Schema Browser 用上标标注扩展；Development（dev，UID 999）被登记在 Extensions Registry 中，Notes 写为 “The development schema extensions”。
- **成熟度分级**：资料**没有**给出形式化的成熟度分级字段、状态字段或覆盖矩阵。它只有定性的阶段性表述：新的实验性类别与事件类以 `Dev` 扩展上标出现；扩展可用于开发新 schema 制品，之后可能被提升进核心 schema 或平台扩展；以及若干“截至写作时”的状态说明（例如只有 Linux 与 Windows 两个平台扩展增强核心 schema；“As of this writing, `disposition_id` is added to core schema classes only via the Security Controls profile.”）。资料提到 Profiles 类似 MITRE ATT&CK 的 Matrices，但没有说核心 schema 提供类似矩阵的覆盖视图。

## 9. 对我们的启发

分析：OCSF 把“很少变的骨架”和“不断增长的条目”用两套节奏管理——5 个基本构造、数据类型与属性字典、Base Event 是骨架，变更只走 major 内的向后兼容或第三位修正；事件类、属性、对象、profile 的增长只升 minor，扩展则有自己的版本、按自己的节奏走。我们的库可以把“运行时 11 个数据暴露位置 + 算子签名”当作骨架（对应 runtime 与 operators 两层，破坏性变更才动 major），把“方法插件条目、覆盖记录、攻击/场景标签”当作增长面（对应 methods 与 knowledge_base，新增只升 minor），这样“按论文追插件”就不会动到接口。transfer: direct。

分析：Profile 的 mix-in 设计解决的是正交维度问题——一个 event class 只能属于一个 Category，但可以用 `profiles` 叠加并跨类别过滤，从而避免“为每种组合新建一个类”。我们的方法同样有多个正交维度（作用于哪个训练位置、针对哪类攻击、属于哪个算法族、是否需要额外算子、是否有隐私代价）；照搬“单归属”会强迫取舍，正确做法是把每个维度做成可注册、可查询的叠加标签，注册在方法条目上，使“我们到底覆盖了什么”变成一次按标签的查询而不是一次人工盘点。对应 knowledge_base、methods 与 evaluation 三层。transfer: adapted（OCSF 的 profile 携带属性与要求，我们的标签要携带适用条件、开销与失效场景）。

分析：OCSF 的要求等级（Required/Recommended/Optional）不写在属性本身，只写在“属性 × 事件类”的绑定上，资料明确说属性自身没有要求标记。我们应把“这个方法需要哪一路运行时数据、哪些是必须、哪些只是增强”定义在“方法 × 训练位置/场景”的绑定上，而不是写死在方法插件内部；这样同一个方法在不同训练配置下可以复用，运行时层也能据此判断能否启动。对应 runtime 与 methods。transfer: direct。

分析：`at_least_one` 与 `just_one` 把“至少提供其中之一/恰好提供一个”写成受校验的声明式约束，而不是散落在实现里的分支判断。我们的算子与方法可以声明同类输入约束（例如要么消费客户端上传的更新、要么消费聚合结果；两种量化方案只能选一种），交给算子库的校验器统一检查，方法层只声明不判断。对应 operators 与 evaluation。transfer: adapted（OCSF 的约束只能约束 Recommended 属性的存在性，不能约束数值范围或统计性质）。

分析：OCSF 用 `type_uid = class_uid * 100 + activity_id` 这种可计算的组合 ID 让主键可推导、可反查，并用 `_uid`（schema 内唯一整数）、`_uuid`（全局唯一 GUID）、`_name`（友好名）三种后缀区分标识语义。我们可以为每条运行记录生成由“方法 ID × 训练位置 ID × 客户端 ID × 运行序号”合成的稳定 ID，让跨运行、跨客户端、跨方法版本的记录能对齐比对。对应 records（其次是 runtime）。transfer: adapted（我们的基数远大于两位十进制 activity 的假设，需要更长或分层的编码）。

分析：内容与执行分离在 OCSF 里表现为知识放在 JSON 数据文件中，解释与校验交给 schema browser 及其 server APIs。我们的方法层论文实现必然是代码，但“适用条件、需要哪些运行时数据、超参允许范围、已知失效场景、对应论文与实验编号”应当是数据，才能被统一校验、检索和做覆盖统计。对应 methods 与 knowledge_base。transfer: direct。

分析：扩展机制用注册 UID 偏移 ID 区间、要求与核心 major 兼容，让第三方在不改核心的前提下扩展。我们可以为内部团队与外部贡献者分配 ID 区间和命名前缀（原文的 3 字母 moniker 做法），并保留一个“开发扩展→提升进核心”的通道，避免方法 ID、算子命名冲突。对应 knowledge_base 与 methods。transfer: direct。

分析：`metadata.version` 是事件的必填字段，让消费者知道这条数据里可能出现哪些属性、类与类别结构是什么；扩展事件还要填扩展后的 schema 版本。我们的运行记录也必须强制携带“库版本 + 方法版本 + 扩展版本”，否则跨版本实验结果无法解释，覆盖统计也会把不同定义混在一起。对应 records 与 evaluation。transfer: direct。

分析：OCSF 承认有些字段映射不了，于是提供 `unmapped`（保留未映射字段）与 `raw_data`（未解析原样数据）两个逃生口，并把开放式富化交给任意 JSON 的 `data`。我们的运行时数据（梯度、LoRA 权重、聚合结果）比日志复杂得多，必须同样保留“原样快照 + 未解释字段”的通道，否则分析脚本一升级就丢证据、也无法复现。对应 runtime 与 records。transfer: adapted（我们要存的是张量对象，而非标量摘要）。

分析：不能照搬“一个事件类只能属于一个 Category”和“编译后的 schema 不暴露子类”。OCSF 是离散事件归一化框架，要求任何原始事件映射到单一事件类；而我们的攻防对象是训练过程中的连续数值过程，同一次投毒在不同训练步、不同客户端上的表现是演化的，没有唯一的“事件类”归属；方法层又确实存在“父方法—变体”的层次。照搬单一归属与无子类约束会同时损失多视角归属与方法族谱。对应 methods 与 knowledge_base。transfer: not_transferable。

分析：不能把 OCSF 的校验当作防御有效性的判据。它的校验是必需属性存在性、数据类型与事件类结构，Recommended 属性甚至不受校验；而我们的“这个方法有没有用”是统计性的（例如攻击成功率下降、主任务精度损失、通信开销），必须自建 evaluation 指标与覆盖矩阵。资料里没有任何可借用的覆盖率或成熟度字段，这部分只能自建。对应 evaluation。transfer: not_transferable。

分析：`disposition_id` 用 Blocked、Quarantined、Deleted、Delayed 这类过去时枚举表达“防护产品在捕获时刻的处置结果”，并且资料明确写出它目前只通过 Security Controls profile 进入核心类，这种克制值得学。我们可以借鉴为“防御动作结果”的状态字段，但我们的算法多是抑制、衰减、裁剪这类连续干预，离散枚举只能作为汇总视图，原始强度与轨迹仍要保留在数值字段里。对应 operators、records 与 evaluation。transfer: adapted。

分析：Observable 用 `name`/`value`/`type_id` 三件套把散落各处的安全指标摊平成可检索清单，对象类型只留引用、不填 `value`。我们的运行记录可以把关键标量指标（损失、梯度范数、更新范数、上传差异）做成类似的扁平清单便于检索，但 LoRA 权重与梯度张量必须真正落盘，不能像 OCSF 那样对复杂类型只留引用，否则无法复算。对应 records 与 runtime。transfer: adapted。

分析：OCSF 明确划出边界——不管存储格式、不管数据采集、不管 ETL，核心 schema 与实现无关。这提示我们把“防御逻辑”和“具体训练框架的 hook 实现”解耦：runtime 层只负责在 11 个位置产出规范化数据，operators 层只做纯计算，methods 层只做组合与声明，这样换训练框架或换并行策略时方法不重写。对应 runtime、operators 与 methods。transfer: direct。

## 10. 框架自己承认的局限

- 并非每个数据源对同一观察行为都发出同样的信息，因此事件类只能规定哪些属性是必要的，其余留作可选，属性要求无法脱离事件类统一定义。
- 并非所有原始字段都能映射：可解析、可切分不代表都能进 schema，未映射字段只能进 `unmapped`，原样数据只能进未解析的 `raw_data`。
- 富化数据极其开放，只能退化为通用字符串属性加任意 JSON 的 `data`，并且因为不存在预定义的可富化属性集合，所以没有 `type_id` 枚举，只有 Recommended 的 `type`。
- 与 MITRE ATT&CK 相比有两处明确的能力缺失：OCSF 的 Event Class 只能属于一个 Category（ATT&CK 的 Technique 可以属于多个 Tactic，Procedure 可以用在多个 Technique 中）；OCSF 没有 Sub-Event Classes，而 ATT&CK 有 Sub-techniques。脚注补充：内部源定义可以分层，但编译后的 schema 不暴露子类。
- 类别粒度是未解决的建模问题，资料列出一串反问而没给判据。
- 覆盖范围有“截至写作时”的状态限制：只有 Linux 与 Windows 两个平台扩展增强核心 schema；`disposition_id` 只通过 Security Controls profile 加到核心类上。
- 必填属性在源缺失时不能省略，只能带 `Unknown` 值随事件一起传递，等于显式断言信息缺失。
- Recommended 属性不受校验、没有默认值，必须靠接入方自行权衡权重。
- `original_time` 的时间格式不由 OCSF 规定，是非校验字符串，取值可能是毫秒 UTC、ISO 8601 或任何其他写法。
- 属性含义被重载时，字典中的描述只能保持泛化并附 “see specific usage”，覆盖动作发生在事件类上下文中。
- profile 定义的属性要求不可被覆盖；当类把 profile 属性内建进定义时以类定义为准，存在两套定义并存的复杂性。
- 扩展允许与核心 schema 属性同名，但资料说这不是好做法；扩展必须与所扩展核心 schema 的 major 版本保持兼容一致。
- 时间解读有陷阱：`processed_time` 与 `logged_time` 之间非平凡的差异可能指示源端时钟同步问题，但不一定指向实际来源（可能存在中间采集系统或转发器）。
- 资料本身把最新指南与数据类型指向 schema browser 的 Appendix B，暗示文档内容可能落后于实际 schema。

## 11. 原文依据

1. “The framework is made up of a set of data types and objects, an attribute dictionary, and the taxonomy.”（19 词）——支撑第 2 节“框架的核心对象是数据类型/对象、属性字典与 taxonomy 三类积木”这一论断。
2. “Profiles are overlays on event classes and objects, effectively a dynamic mix-in class of attributes with their requirements and constraints.”（20 词）——支撑第 2 节 Profile 的定义与第 5 节“用叠加层而非新增冗余类”的机制论断。
3. “The type_uid required attribute is constructed by the combination of the event class of the event (class_uid) and its activity (activity_id).”（21 词）——支撑第 3 节“组合式编号 `type_uid` 由 `class_uid` 与 `activity_id` 合成”的论断。
4. “In OCSF, Event Classes are in only one Category, while MITRE ATT&CK Techniques can be part of multiple Tactics.”（19 词）——支撑第 3 节“层级是类别到事件类的单归属包含”与第 10 节“与 ATT&CK 的差异是明确局限”的论断。
5. “For example, a Security Controls profile that adds MITRE ATT&CK Attack and Malware objects to System Activity classes avoids having to recreate a new event class”（26 词）——支撑第 4 节“攻击侧内容通过 Security Control profile 叠加进事件类，而非直接与防御对象互相引用”的论断。
6. “Using profiles, some of these overlapping categorical scenarios can be handled without new partially redundant event classes.”（17 词）——支撑第 5 节“重叠场景用 profile 处理，不新建部分冗余的事件类”这一新条目与变体的判定论断。
7. “The convention is that the major version, after 1.0.0, or first part, remains the same while versions of the schema remain backwards compatible with previous versions of the schema and framework.”（31 词）——支撑第 6 节“骨架部分希望很少变、且 major 内保持向后兼容”的论断。
8. “As new classes, attributes, objects and profiles are added to the schema, the minor version, or second part of the version increases.”（22 词）——支撑第 6 节“事件类、属性、对象与 profile 属于预期不断增长的部分”的论断。
9. “The schema framework definition files and the resulting normative schema are written as JSON.”（14 词）——支撑第 7 节“知识与规则内容以 JSON 定义文件形式存放”的论断。
10. “A query for events of the class will return all the events, with or without the security information, while a query for just the profile will return events across all event classes that support the Malware profile.”（37 词）——支撑第 8 节“覆盖通过 profile 注册与按 profile 过滤查询来表达”的论断。

```json
{
  "key": "ocsf",
  "framework": "Open Cybersecurity Schema Framework (OCSF)；资料为《Understanding the Open Cybersecurity Schema Framework》(Paul Agbabian, April 2026, Status: RFC, Version 1.17, 对应 schema version 1.0.0)",
  "object_types": [
    {"name": "Data Type (scalar)", "role": "other", "fields": ["primitive: string/integer/floating point/boolean", "scalar examples: Timestamp, IP Address, MAC Address, User Name", "timestamp_t", "datetime_t", "string_t", "valid value/range constraints"]},
    {"name": "Attribute / Attribute Dictionary", "role": "other", "fields": ["name", "type (scalar or object)", "requirement flag (Required/Recommended/Optional, 仅事件类上下文)", "attribute group (Primary/Classification/Occurrence/Context)", "description (可含 see specific usage)", "sibling string attribute"]},
    {"name": "Object (complex data type)", "role": "other", "fields": ["constituent attributes", "uid (string_t, 实体对象)", "name (string_t, 实体对象)", "可嵌套其他 objects", "structure/attribute validation"]},
    {"name": "Array", "role": "other", "fields": ["element type (以单数形式定义)", "plural 's' suffix (preferred)", "optional _list suffix", "optional 同名单数属性并存"]},
    {"name": "Base Event (event class)", "role": "telemetry", "fields": ["class_uid (Required)", "category_uid (Required)", "activity_id (Required Enum)", "severity_id (Required)", "metadata (Required object)", "observables (primary array)", "enrichments (array)", "profiles (optional array)", "timezone_offset (Recommended, -1080..+1080)", "status_id (Recommended)", "message (Recommended)", "activity_name/start_time/end_time/count/duration/unmapped (Optional)", "raw_data (Optional, unparsed String)", "original_time/time/processed_time/logged_time/modified_time/start_time/end_time"]},
    {"name": "Event Class", "role": "telemetry", "fields": ["class_uid (Required, schema-unique, 覆盖 Base Event 的 0)", "class_name (Optional)", "category_uid (Required, 唯一归属)", "category_name (Optional)", "activity_id (Required Enum, 每类受约束)", "activity_name (Optional sibling)", "type_uid (Required, class_uid*100+activity_id, schema 内唯一)", "type_name", "constraints (at_least_one/just_one)", "associations", "属主自有的 Required/Recommended/Optional 属性"]},
    {"name": "Category", "role": "other", "fields": ["category_uid (unique)", "category_name (friendly caption)", "所含 event classes"]},
    {"name": "Profile", "role": "relation", "fields": ["unique name/ID", "overlay attributes 及其不可覆盖的 requirements/constraints", "可应用到 event classes/objects/categories", "event class 需 register for profile", "通过 profiles 数组属性应用"]},
    {"name": "Extension", "role": "other", "fields": ["unique extension name (e.g. dev)", "UID (OCSF Extensions Registry, e.g. 999)", "version (与 core major 兼容)", "可新增 attributes/objects/categories/profiles/event classes", "新增 categories/event classes 的 ID 以 UID 偏移"]},
    {"name": "Observable", "role": "artifact", "fields": ["name (标量为全限定属性名；对象为引用)", "type_id (Enum)", "value (标量时填；对象时不填)", "type (示例中出现的友好类型名)"]},
    {"name": "Enrichment", "role": "telemetry", "fields": ["name (Required, 指向被富化的属性)", "value (Required)", "type (Recommended, 无 type_id Enum)", "data (任意 JSON)", "provider (示例出现, 必填性未说明)"]},
    {"name": "Metadata", "role": "telemetry", "fields": ["version (Required, 事件的 schema 版本)", "uid (Optional, 可由日志系统存储时赋值)", "logged_time (Optional)", "modified_time (Optional)", "processed_time (Optional)", "sequence (示例出现, 含义未说明)"]},
    {"name": "Constraint", "role": "relation", "fields": ["at_least_one", "just_one", "成员必须是 Recommended 属性"]},
    {"name": "Association", "role": "relation", "fields": ["属性名 -> 关联属性数组", "可双向 (常见) 或单向", "例: actor.user <-> src_endpoint, dst_endpoint <-> user"]},
    {"name": "attacks (MITRE ATT&CK techniques)", "role": "attack", "fields": ["Security Control profile 的属性之一", "以数组形式出现 (命名示例 attacks)", "内容为 MITRE ATT&CK techniques (有唯一 ID)"]},
    {"name": "malware (object)", "role": "attack", "fields": ["Security Control profile 引入的对象之一"]},
    {"name": "disposition_id / disposition", "role": "defense", "fields": ["disposition_id (Enum: Blocked/Quarantined/Deleted/Delayed 等)", "只有注册该 profile 的 event class 才能有", "disposition 为 sibling string, 标签用过去时", "截至写作时只通过 Security Controls profile 加入核心类"]}
  ],
  "id_scheme": "class_uid 为 schema 内唯一的事件类整数 ID (Required, 覆盖 Base Event 的名义值 0)；category_uid 为类别唯一 ID；type_uid = class_uid * 100 + activity_id，schema 内唯一，type_name 为两部分名字的组合；schema 唯一分类值以 _uid 结尾且为整数并由 schema 预置，_name 为友好名，全局唯一值以 _uuid 结尾 (GUID, 无友好名)，Enum 整数以 _id 结尾、数组以 _ids 结尾，枚举通用值 0=Unknown、99=Other；扩展有唯一 UID (如 dev=999)，新增 categories 与 event classes 的 ID 以该 UID 偏移；枚举值可用同名兄弟字符串属性同时表达标签。",
  "attack_defense_link": "via_technique_id",
  "link_detail": "OCSF 没有独立的攻击对象图或缓解措施对象：攻击侧内容 (attacks，即 MITRE ATT&CK techniques，以及 malware 对象) 通过 Security Control profile 以叠加方式进入注册该 profile 的 event class，攻击技术以 technique 标识被引用；防御/处置侧用同一 profile 的 disposition_id (Blocked/Quarantined/Deleted/Delayed 等) 表示事件捕获时刻活动的结果。两者不直接互指，而是共同承载在同一个 event class 上；原文以 Profiles 类比 Matrices、以 Type IDs 类比 Procedures，并说明只有注册该 profile 的类才能有 disposition_id。",
  "abstraction_level": "事件类描述某一时点的一条日志行或一次遥测提交，语义为某个 activity、某个 disposition 或两者；意图是任何原始事件都能映射到单一事件类，靠组合而非多重继承实现；属性要求只在事件类上下文里定义，除 Classification 属性外不绑定到属性自身；类别是弱结构性、事件分类是强结构性；重叠的分类场景用 profile 处理而不新增部分冗余的事件类；映射不了的内容走 unmapped / raw_data / 枚举 Other + 兄弟字符串。",
  "stable_parts": ["5 个基本构造 (Data Types/Attributes/Arrays, Event Class, Category, Profile, Extension)", "数据类型与属性字典", "Base Event 及其 Base Attributes", "组合而非多重继承的设计原则", "属性命名与后缀约定 (Appendix A)", "profile 与 extension 两种扩展机制", "SemVer major 在 1.0.0 后保持不变且向后兼容"],
  "growing_parts": ["新增 event classes", "新增 attributes 与 objects", "新增 profiles", "新增 categories 与枚举", "extensions (有独立版本、按自己节奏变化、可被提升进核心或平台扩展)", "相应带来 minor 版本增加"],
  "content_format": "JSON 定义文件与由此产生的规范 schema；仓库为 categories.json、dictionary.json、version.json、enums/、events/、extensions/、includes/、objects/、profiles/；扩展目录结构相同，可按需含 categories.json、dictionary.json、events/、objects/、profiles/。",
  "execution_engine": "schema browser (https://schema.ocsf.io) 作为可导航门户与校验服务器 (server APIs)，可生成事件类 schema 与事件示例；校验由必需属性 (尤其保持最少量的 classification 属性)、属性数据类型校验与事件类结构强制执行；constraints 是受校验的规则；Recommended 属性不受校验、无默认值。",
  "coverage_expression": "event class 为 profile 注册，支持该 profile 的事件可通过 profiles 属性跨所有类别与事件类被过滤检索；属性在事件类上下文里的 Required/Recommended/Optional 要求标记；constraints 的 at_least_one 与 just_one；metadata.version 表明事件里可能出现的属性与类/类别结构；Schema Browser 用上标标注扩展。",
  "maturity_expression": "资料未说明形式化的成熟度分级字段或状态字段；只有定性表述：Dev 扩展上标表示开发中制品、可被提升进核心 schema 或平台扩展、Extensions Registry 的 Notes 列，以及若干“截至写作时”的范围说明 (如 disposition_id 只通过 Security Controls profile 加到核心类)。",
  "lessons": [
    {"idea": "把很少变的骨架 (taxonomy 构造、字典、Base Event) 与不断增长的条目 (事件类、属性、对象、profile、扩展) 分成两套变更节奏，用 SemVer 的 major/minor/patch 表达", "applies_to": "runtime", "transfer": "direct", "why": "我们的运行时 11 个数据暴露位置与算子签名是骨架，方法插件与覆盖记录是增长面，分开版本节奏可以避免追论文时动到接口"},
    {"idea": "Profile 式 mix-in：条目保持单一主归属，其余维度做成可注册、可跨类过滤的叠加标签", "applies_to": "knowledge_base", "transfer": "adapted", "why": "我们的方法天然有训练位置、攻击类型、算法族等多个正交维度；照搬单归属会强迫取舍，但 OCSF 的 profile 还携带属性要求，我们需要携带的是适用条件与开销"},
    {"idea": "要求等级只定义在“属性 × 事件类”的绑定上，不写在对象自身", "applies_to": "methods", "transfer": "direct", "why": "方法需要哪些运行时数据应是“方法 × 训练位置/场景”的绑定，这样同一方法可在不同训练配置下复用"},
    {"idea": "把“至少一个/恰好一个”写成受校验的声明式 constraint，而不是实现里的分支", "applies_to": "operators", "transfer": "adapted", "why": "算子输入组合可用同类约束校验，但 OCSF 的约束只能约束属性存在性，不能约束数值范围与统计性质"},
    {"idea": "可计算的组合主键 (type_uid = class_uid * 100 + activity_id) 与 _uid/_uuid/_name 的标识后缀分工", "applies_to": "records", "transfer": "adapted", "why": "运行记录需要方法×位置×客户端×序号的合成 ID 以便跨运行比对，但我们的基数远大于两位十进制 activity 的假设"},
    {"idea": "内容与执行分离：知识以数据文件存放，由独立校验器解释执行", "applies_to": "methods", "transfer": "direct", "why": "论文实现必然是代码，但适用条件、所需数据位置、超参范围、已知失效场景应是可校验的数据，才能统一查询与统计覆盖"},
    {"idea": "扩展用注册 UID 偏移 ID 区间并要求与核心 major 兼容，另留“开发扩展→提升进核心”的通道", "applies_to": "knowledge_base", "transfer": "direct", "why": "内部团队与外部贡献者需要各自的 ID 区间与命名前缀，避免方法 ID 与算子命名冲突"},
    {"idea": "每个事件强制携带 metadata.version，扩展事件填扩展后的版本", "applies_to": "records", "transfer": "direct", "why": "运行记录必须携带库版本、方法版本与扩展版本，否则跨版本实验结果无法解释、覆盖统计会混淆定义"},
    {"idea": "为无法表达的内容留逃生口：unmapped (未映射字段) 与 raw_data (未解析原样数据)、富化用任意 JSON data", "applies_to": "runtime", "transfer": "adapted", "why": "梯度与 LoRA 权重比日志复杂，必须保留原样快照通道；但要存的是张量对象而不只是标量摘要"},
    {"idea": "一个条目只能属于一个 Category，且编译后的 schema 不暴露子类", "applies_to": "methods", "transfer": "not_transferable", "why": "OCSF 面向离散事件归一化，一次原始事件映射到单一事件类；我们的攻防是训练中的连续数值过程，同一次投毒随训练步演化，且方法层确实存在父方法与变体的层次"},
    {"idea": "以必需属性存在性、数据类型与事件类结构作为校验与判据", "applies_to": "evaluation", "transfer": "not_transferable", "why": "我们的“方法是否有效”是统计性的 (如 ASR 下降、主任务精度损失、通信开销)，资料里也没有任何覆盖率或成熟度字段可借，必须自建指标与覆盖矩阵"},
    {"idea": "用枚举状态表达处置结果 (disposition_id: Blocked/Quarantined/Deleted/Delayed)，且克制地只通过一个 profile 引入", "applies_to": "operators", "transfer": "adapted", "why": "我们的干预多是抑制、衰减、裁剪这类连续操作，离散枚举只能做汇总视图，原始强度与轨迹仍需数值字段保留"},
    {"idea": "Observable 用 name/value/type_id 把散落指标摊平成可检索清单，对象类型只留引用不填 value", "applies_to": "records", "transfer": "adapted", "why": "关键标量指标可做扁平清单便于检索，但 LoRA 权重与梯度必须真正落盘、不能只留引用，否则无法复算"},
    {"idea": "框架不管存储格式、采集与 ETL，核心 schema 与实现无关", "applies_to": "runtime", "transfer": "direct", "why": "这提示我们把防御逻辑与训练框架 hook 实现解耦：runtime 产出规范化数据、operators 做纯计算、methods 只组合与声明"}
  ],
  "limits": [
    "并非每个数据源对同一观察行为发出同样信息，属性要求只能在事件类上下文里规定",
    "并非所有原始字段都能映射，未映射字段只能进 unmapped，原样数据只能进未解析的 raw_data",
    "富化极其开放，只能用通用字符串加任意 JSON data，且没有 type_id 枚举，只有 Recommended 的 type",
    "没有 Sub-Event Classes (内部源定义可分层但编译后不暴露子类)，而 ATT&CK 有 Sub-techniques",
    "一个 Event Class 只能属于一个 Category，而 ATT&CK Technique 可属于多个 Tactic、Procedure 可用于多个 Technique",
    "类别粒度是未解决的建模话题，资料只列出一串反问而未给判据",
    "disposition_id 截至写作时只通过 Security Controls profile 加到核心类",
    "截至写作时只有 Linux 与 Windows 两个平台扩展增强核心 schema",
    "必填属性缺信息时不能省略，只能带 Unknown 值并显式断言信息缺失",
    "Recommended 属性不受校验、没有默认值，只能靠接入方自行权衡",
    "original_time 的时间格式不由 OCSF 规定，是非校验字符串",
    "属性含义重载时字典描述只能泛化并附 see specific usage",
    "profile 定义的属性要求不可被覆盖；类内建 profile 属性时以类定义为优先",
    "扩展允许与核心属性同名，但原文说这不是好做法；扩展必须与所扩展核心 schema 的 major 版本兼容一致",
    "processed_time 与 logged_time 的显著差异可能指示时钟同步问题，但不一定指向实际来源 (可能有中间采集或转发系统)"
  ],
  "quotes": [
    {"supports": "第 2 节：框架由数据类型与对象、属性字典、taxonomy 三类积木构成", "text": "The framework is made up of a set of data types and objects, an attribute dictionary, and the taxonomy."},
    {"supports": "第 2 节与第 5 节：Profile 是叠加在事件类与对象上的动态 mix-in，带自身要求与约束", "text": "Profiles are overlays on event classes and objects, effectively a dynamic mix-in class of attributes with their requirements and constraints."},
    {"supports": "第 3 节：type_uid 是 class_uid 与 activity_id 的组合编号", "text": "The type_uid required attribute is constructed by the combination of the event class of the event (class_uid) and its activity (activity_id)."},
    {"supports": "第 3 节与第 10 节：事件类只能属于一个类别，这是与 ATT&CK 的明确差异", "text": "In OCSF, Event Classes are in only one Category, while MITRE ATT&CK Techniques can be part of multiple Tactics."},
    {"supports": "第 4 节：攻击侧内容通过 Security Control profile 叠加进事件类，而非直接互相引用", "text": "For example, a Security Controls profile that adds MITRE ATT&CK Attack and Malware objects to System Activity classes avoids having to recreate a new event class"},
    {"supports": "第 5 节：重叠场景用 profile 处理，避免新增部分冗余的事件类", "text": "Using profiles, some of these overlapping categorical scenarios can be handled without new partially redundant event classes."},
    {"supports": "第 6 节：major 版本在 1.0.0 之后保持不变且向后兼容，属于稳定部分", "text": "The convention is that the major version, after 1.0.0, or first part, remains the same while versions of the schema remain backwards compatible with previous versions of the schema and framework."},
    {"supports": "第 6 节：事件类、属性、对象与 profile 的新增带来 minor 版本增加，属于增长部分", "text": "As new classes, attributes, objects and profiles are added to the schema, the minor version, or second part of the version increases."},
    {"supports": "第 7 节：schema 框架定义文件与规范 schema 以 JSON 形式存放", "text": "The schema framework definition files and the resulting normative schema are written as JSON."},
    {"supports": "第 8 节：覆盖通过事件类为 profile 注册与按 profile 过滤查询来表达", "text": "A query for events of the class will return all the events, with or without the security information, while a query for just the profile will return events across all event classes that support the Malware profile."}
  ]
}
```
