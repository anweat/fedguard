# sigma：Sigma 规则规范与 Sigma 关联规则规范（Specification v2.1.0，发布日 2025-08-02）

资料由两份文档组成：《Sigma Rules Specification》（Version 2.1.0，Release date 2025-08-02）与《Sigma Correlation Rules Specification》（Version 2.1.0，Release date 2025-08-02）。下文凡两者不同处分别注明；凡资料未写的，均写"资料未说明"。

## 1. 要解决的问题

**为谁。** 资料直接约束的对象有三类。第一类是写规则的人（rule writer / rule contributor）：规范给出 YAML 文件结构、各组件含义与格式约定，并以互操作（interoperable）为目的，原文为 "In order to keep the rules interoperable use the following"。第二类是把规则翻译成具体查询的工具，即 "converters" 与 "conversion backend"：由它求值 `logsource` 的 `category`、`product`、`service`，处理 taxonomy 与占位符，并生成目标后端查询。第三类是下游使用规则的人，规范在劝阻 `all of them` 时提到，这种写法"阻止了规则的下游用户通用地过滤掉不需要的匹配"（"it prevents the possibility of downstream users of a rule to generically filter unwanted matches"）。

**解决什么问题。** 归纳为四条。

1. 让检测知识与后端查询语言解耦：规则以 YAML 书写，由转换器翻译为 Splunk、Elasticsearch 等目标系统的查询；资料给出的映射例子包括把 `category: firewall` 转成 `( index=fw1* OR index=asa* )`，把 `product: windows` 转成 `"_index":"logstash-windows*"`。
2. 让规则与具体遥测源解耦：用 `logsource` 的三级抽象（`category` / `product` / `service`）避免为 Sysmon、Microsoft-Windows-Security-Auditing、Microsoft-Windows-Kernel-Process 等每个来源各写一条规则，原文称这种抽象方法的优点是"不把规则限制到某个具体遥测源"。
3. 支持单事件之外的组合：用关联规则（correlation rules，规范中也称 meta-rules）把多个事件、多条规则连接起来，实例包括"同一主机上 X 次无效登录""同一主机但来自 X 个远程源""A、B、C 三个告警出现在同一个 `timespan` 内"。
4. 环境适配的复用：用 Sigma Filters 把同一个排除项写到一处，原文说"有了 meta-filter 就可以写在单个位置"。

**它明确说自己不做什么。**

- 不把自己做成目标系统的查询语言：在解释为什么废弃旧的 condition 内关系表达时，原文说 pipe 语法有时让规则贡献者把它当成 Splunk 查询或其它目标系统专有查询语言，而"以 Sigma 风格表达这些关系不应引起这类联想"。
- 不把 condition 做成复杂逻辑：一条 Sigma 规则只对应一个日志源，会把关系表达限制在同一日志源的事件之间；把时间关系写进查询表达式会相当复杂，链式关联又增加复杂度；因此关系被移入独立的关联规则。
- 关联规则不产生独立查询：多文档 YAML 中的规则"不产生各自独立的查询"，只是用来从基本 Sigma 检测构造更复杂结构的工具；只有最外层关联规则可以定义 `status`、`level`、`date` 等元信息。
- 不负责占位符与自定义 taxonomy 的最终语义：非默认 taxonomy 必须由使用工具处理或转换为默认 taxonomy；工具若无法处理占位符，必须拒绝（reject）该规则。

资料未说明：框架是否包含规则库的评审制度与发布节奏，以及攻击技术本体（战术、技术、缓解措施）的内容；taxonomy 附录与 tags 附录只以链接形式出现，其内容不在资料中。

## 2. 核心对象

资料中实际出现的对象类型有：Sigma 规则、关联规则（元规则）、搜索标识符、检测条件、日志源、taxonomy、标签、`related` 关系引用、字段别名、Sigma Filter（仅提及）、JSON Schema。资料中没有出现战术（tactic）、技术（technique）、缓解措施（mitigation）、数据源组件（data component）、测试（test）、事件类（event class）这类对象；`attack.t1234` 只是标签字符串，不是被建模的对象。

### 2.1 Sigma 规则（Sigma rule）

规则文件"由少数必填段与若干可选段组成"，骨架为 `title / id [optional] / name [optional] / related [optional] / taxonomy [optional] / status [optional] / description [optional] / license [optional] / references [optional] / author [optional] / date [optional] / modified [optional] / logsource / detection / fields [optional] / falsepositives [optional] / level [optional] / tags [optional] / scope [optional] / [arbitrary custom fields]`。

| 字段 | 含义 | 必填 | 取值约束 |
|---|---|---|---|
| `title` | 规则标题，应包含该规则要检测什么 | mandatory（必填） | 最多 256 字符 |
| `id` | 全局唯一标识 | optional（文件结构标 optional），但 Identification 一节写规则"should be identified by a globally unique identifier" | 随机生成的 UUID（version 4）；例 `929a690e-bef0-4204-a928-ef5e620d6fcc` |
| `name` | 唯一的人类可读名，可在关联规则中代替 `id` 作引用，目的是提高关联规则可读性 | optional | **unique**；在关联规则里使用 `aliases` 时必须定义 |
| `related` | 到相关规则标识的引用列表 | optional | 每项含 `type` 与 `id` 两个键 |
| `taxonomy` | 本条规则使用的 taxonomy | optional | 默认 taxonomy 是 `sigma`；其他 taxonomy 必须由工具处理或转换为默认值 |
| `status` | 规则状态 | optional | `stable`、`test`、`experimental`、`deprecated`、`unsupported` |
| `description` | 对规则及可检测到的恶意或可疑活动的简短准确描述 | optional | 最多 65,535 字符 |
| `license` | 规则许可 | optional | 按 SPDX ID 规范 |
| `references` | 规则来源引用 | optional | 可为博客文章、技术论文、演讲稿甚至推文；组件章节把该属性写作 `reference`，与文件结构中的 `references` 不一致 |
| `author` | 规则创建者 | optional | 姓名、昵称、Twitter handle 等；多于一个时用逗号分隔 |
| `date` | 规则创建日期 | optional | ISO 8601 带分隔符格式 `YYYY-MM-DD` |
| `modified` | 最后一次修改日期 | optional | 同上；改标题、改 `detection`、改 `level`、改 `logsource`（罕见）、把 `status` 改为 `deprecated` 时应更新 |
| `logsource` | 检测所针对的日志数据 | mandatory | 见 2.4 |
| `detection` | 一组代表日志数据搜索属性的搜索标识符与条件 | mandatory | 见 2.3、2.5 |
| `fields` | 后续分析可能有用、应展示给分析人员的日志字段列表 | optional | 列表 |
| `falsepositives` | 已知可能出现的误报列表 | optional | 列表 |
| `level` | 触发规则的严重性 | optional | `informational`、`low`、`medium`、`high`、`critical` 五值 |
| `tags` | 规则分类标签 | optional | 小写字母、数字、下划线、连字符；不含空格；点分命名空间，如 `attack.t1234` |
| `scope` | 规则预期生效的范围 | optional | 列表；例：某注册表键只存在于 Windows Server，可加 `server` 限定 |
| `[arbitrary custom fields]` | 结构末尾允许出现的任意自定义字段 | 结构上允许 | 取值约束资料未说明；使用自定义字段的规则可被标为 `unsupported` |

### 2.2 关联规则 / 元规则（correlation rule / meta-rule）

关联规则是"一个专用的 YAML 文档"，与 Sigma 规则一样有 `title` 和唯一 `id`；它写在多文档 YAML 中，只有最外层可以定义元信息。

| 字段 | 含义 | 必填 | 取值约束 |
|---|---|---|---|
| `title` | 规则标题 | mandatory | 最多 256 字符 |
| `id` | 全局唯一标识 | optional | 推荐随机 UUID v4，但"recommended but not mandatory" |
| `status` | 状态 | optional | 与规则相同的五值 |
| `description` | 简短描述 | optional | 最多 65,535 字符 |
| `author` | 创建者 | optional | 姓名、昵称、Twitter handle 等 |
| `references` | 来源引用 | optional | 博客、技术论文、演讲、推文等 |
| `date` | 元规则创建日期 | optional | `YYYY-MM-DD` |
| `modified` | 最后修改日期 | optional | `YYYY-MM-DD` |
| `taxonomy` | 使用的 taxonomy | optional | 默认 `sigma` |
| `correlation.type` | 关联类型 | mandatory | 组件章节列出的允许值为 `event_count`、`value_count`、`temporal`、`temporal_ordered`；Correlation Types 一章还描述了 `value_sum`、`value_avg`、`value_percentile` 三种，二者不一致 |
| `correlation.rules` | 引用一条或多条 Sigma 规则或关联规则，允许链式组合 | mandatory | 用规则的 `id` 或 `name` 引用 |
| `correlation.aliases` | 对相关 Sigma 规则应用的字段名别名，使聚合可跨事件类型进行 | optional | 形如 `<alias name>: <Sigma rule name>: <source field name in event matched by Sigma rule>`；被引用规则必须定义 `name` |
| `correlation.group-by` | 一个或多个字段，作为独立的事件发生范围 | mandatory | 多字段之间用 **AND** 连接；例 `TargetUserName` + `TargetDomainName` |
| `correlation.timespan` | 关联生效的时间段 | mandatory | `number + 小写字母`：`Xs`、`Xm`、`Xh`、`Xd`；例 1 小时 30 分写作 `90m` |
| `correlation.condition` | 定义关联何时命中 | mandatory | 恰好一个比较准则的映射：`gt`、`gte`、`lt`、`lte`、`eq`、`neq`；可用 AND 连接定义区间（如 `gt: 100` 与 `lte: 200`） |
| `correlation.field`（写在 condition 段内） | 被聚合的数值/取值字段 | 对 `value_count`、`value_sum`、`value_avg`、`value_percentile` 属于 Requires（必需） | 多值时用 **AND** 连接 |
| `falsepositives` | 已知误报列表 | optional | 列表 |
| `level` | 关联命中时的严重性调整 | optional | 可让单事件命中为 `low` 或 `informational`，在事件关联出现时升到更高级别 |
| `generate` | 决定被引用的规则是作为独立规则转换，还是只生成关联查询 | optional | 默认只生成关联查询 |

### 2.3 搜索标识符（search-identifier）

它"可以由两种不同的数据结构组成——列表和映射"。字段层面：标识符名（在 `detection` 下可定义多个）为键；取值为字符串列表（对整条日志消息生效，彼此以逻辑 OR 连接）、映射列表（列表内各映射之间也是 OR）、或字段-值映射（映射内各元素以逻辑 AND 连接）。取值约束：所有值按不区分大小写的字符串处理；字符串可用通配符 `*` 与 `?`；正则默认区分大小写；除字符串引号外无需转义（反斜杠 `\` 用于转义通配符与反斜杠本身）。约定：以 `_` 开头的搜索标识符在 `1 of them` / `all of them` 中被排除。资料还提到"有些规则直接用 `keywords` 作为搜索标识符名以便识别"。

### 2.4 日志源（logsource）

| 字段 | 含义 | 必填 | 取值约束 |
|---|---|---|---|
| `category` | 逻辑组，用于选取某一逻辑组的全部日志文件 | 三项可单独使用或任意组合 | 小写，空格替换为 `_`，允许 `.` 与 `-`；例 `firewall`、`web`、`antivirus` |
| `product` | 某产品的全部日志输出 | 同上 | 例 `windows`、`apache`、`check point fw1` |
| `service` | 更具体的日志子集 | 同上 | 例 `sshd`、`applocker`、`onelogin.events`、`firewall-as` |
| `definition` | 对日志源的补充说明，包括日志详细程度或所需配置 | optional | 不被转换器自动求值，只给读者提供配置信息 |
| `...` | 任意数量的可选元素 | optional | 取值约束资料未说明 |

`category`、`product`、`service` 三个属性"由转换器自动求值"。

### 2.5 检测条件（condition）

`condition` 是 `detection` 的必填部分，是"规范中最复杂的部分"。资料列出的表达式能力：逻辑 AND/OR；`1 of them` / `all of them`（对所有不以 `_` 开头的搜索标识符做 OR 或 AND，标识符本身按 map=AND、list=OR 的默认行为连接）；`1 of` / `all of {search-identifier-pattern}`（用 `*` 通配符在任意位置匹配标识符名）；`not` 取反；括号。运算符优先级从最松到最紧为 `or`、`and`、`not`、`x of search-identifier`、`( expression )`。`condition` 也可以是列表，此时每一项各生成一个查询，彼此用 OR 连接。

### 2.6 taxonomy（分类法）

`taxonomy` 字段声明规则使用的分类法，取值默认为 `sigma`。它可以定义字段名（如用 `process_command_line` 代替 `CommandLine`）、字段值（如 `image_file_name` 只含文件名，被转换为 `ImageFile: *\\example.exe`）和日志源名（如用 `category: ProcessCreation` 代替 `category: process_creation`）。非默认 taxonomy 必须由使用工具处理或转换为默认 taxonomy；默认 taxonomy 的更多信息在 Sigma Taxonomy Appendix 中，该附录内容未随资料提供。

### 2.7 标签（tag）

`tags` 是可选字段，取值是遵循固定语法的字符串：字符集为小写字母、数字、下划线与连字符；不含空格；使用点号作为命名空间分隔符，例如 `attack.t1234` 指命名空间 `attack` 中的技术 1234，命名空间还可以嵌套；要求"保持标签简短，例如用数字标识符而不是长句"；并欢迎通过 pull request 或 issue 提议新标签。更多信息在 sigma-appendix-tags.md 中，该附录内容未随资料提供。

### 2.8 `related` 关系引用

每条引用包含 `type`（必填语义上必需，否则无关系可言）与 `id`。`type` 当前定义了五种：`derived`、`obsolete`、`merged`、`renamed`、`similar`。

### 2.9 字段别名（aliases，关联规则内）

结构为 `<alias name>: <Sigma rule name>: <source field name in event matched by Sigma rule>`。别名引用的字段名"不一定出现在 Sigma 规则里，而必须出现在规则匹配到的事件里"；`<Sigma rule name>` 是被引用规则的 `name` 属性，该属性一般是可选的，但要使用 `aliases` 就必须定义。

### 2.10 Sigma Filter（元过滤器）

资料只在 "Sigma Filters" 一节提到存在一份单独的《Sigma Filters Specification》，用于把同一个排除项写在一处以免维护困难，"更多细节请看该规范"。其字段与取值约束：**资料未说明**。

### 2.11 JSON Schema

检测规则与关联规则各有 JSON Schema，路径分别为 `../json-schema/sigma-detection-rule-schema.json` 与 `../json-schema/sigma-correlation-rules-schema.json`，用于查询必填字段、类型等细节。Schema 的具体内容：**资料未说明**。

## 3. 编号与层级

**编号格式。** Sigma 规则"应以 `id` 属性中的全局唯一标识来标识"，为此使用随机生成的 UUID（version 4）。关联规则的 `id` 同样是全局唯一标识，推荐随机 UUID v4 但非强制。UUID 的原文例子是 `929a690e-bef0-4204-a928-ef5e620d6fcc`；关联规则例子是 `0e95725d-7320-415d-80f7-004da920fc11`。

**命名规则。** 除 `id` 外还有 `name`：它是唯一的人类可读名，可在关联规则中代替 `id` 作为引用，目的是提高关联规则的可读性；在关联规则文档中，`name` 被描述为"每条关联内唯一（a per correlation unique）"的人类可读名，工具必须能自动完成 name 到 id 的转换，且被引用的规则名必须定义在相应规则里。文件名另有一套规定：长度 10 到 70 个字符、全部小写、只允许字母 a–z 与数字 0–9、用 `_` 代替空格、扩展名 `.yml`；关联规则文件遵循同一套约定，并建议加上前缀 `mr_`。规则文件示例为 `lnx_auditd_change_file_time_attr.yml`、`web_cve_2022_33891_spark_shell_command_injection.yml`、`sysmon_file_block_exe.yml`。标签的命名规则见 2.7。

**层级。** 资料中没有"技术—子技术"式的条目层级。实际存在的层级关系有三种。第一，`logsource` 由粗到细：`category` 选取一个逻辑组的全部日志，`product` 选取某产品的全部日志输出，`service` 选取更具体的子集。第二，`detection` 内部：多个搜索标识符由 `condition` 用 `1 of them`、`all of them`、`1 of selection*` 这类表达式引用与分组，并以 `_` 前缀作为"不参与 of them 统计"的约定。第三，关联规则的嵌套：`correlation.rules` 可以引用另一条关联规则，从而"把多个关联串起来"，形成链式结构；在这种多文档结构里，只有最外层关联规则可以定义 `status`、`level`、`date` 等元信息。

**版本。** 两份规范各自维护 History 章节。规则规范：2025-08-02 v2.1.0、2024-08-08 v2.0.0、2023-06-29 v1.0.4、2022-12-28 v1.0.3。关联规范：2025-08-02 v2.1.0（新增 `value_sum`、`value_avg`、`value_percentile` 与 `neq` 运算符）、2024-11-01 v2.0.2（为 temporal 规则增加 Requires 字段）、2024-09-03 v2.0.1（补上缺失的 `status` 与 `falsepositives`）、2024-08-08 v2.0.0。

**同一事物在多处出现时如何处理。** 同一规则在被引用处可以用 `id` 或 `name` 出现，由工具负责 name→id 解析。规则的演化用新 `id` 加 `related` 记录：规则逻辑发生重大变化、从既有规则派生出的新规则、合并多条规则时，"最好用新的 id 写一条规则"。`renamed` 关系记录规则曾用过的标识，并注明"预期这个 id 的规则已不再存在"。状态为 `deprecated` 的规则表示"已被另一条取代或覆盖"，其链接由 `related` 字段建立。字段层面的同名问题由 `fieldmappings` 与 taxonomy 处理，例如把 `sigma` taxonomy 的名字映射到内置 Windows 事件字段：`Image: NewProcessName`、`ParentImage: ParentProcessName`、`Details: NewValue`、`ParentCommandLine: ProcessCommandLine`、`LogonId: SubjectLogonId`。跨规则的同义字段由 `aliases` 处理（见 4）。

## 4. 对象之间的关系

**规则 → 规则：`related`，共五种关系类型，方向是"本条规则对所指规则做了什么"。** 原文定义如下：`derived` 表示"本条规则派生自所引用的规则，被引用规则可能仍然有效"；`obsolete` 表示"本条规则使所引用的规则作废，被引用规则不再使用"；`merged` 表示"本条规则由所引用的多条规则合并而来，被引用规则可能仍然存在并在使用"；`renamed` 表示"本条规则此前使用所引用的标识，因私有命名方案改为 UUID、解决冲突等原因改名，预期这个 id 的规则已不再存在"；`similar` 用于把相似规则相互关联，例如"同一检测内容应用于不同日志源，或只是 level 不同的修改版本"。原文给出的 YAML 例子是：

```yml
related:
  - id: 08fbc97d-0a2f-491c-ae21-8ffcfd3174e9
    type: derived
  - id: 929a690e-bef0-4204-a928-ef5e620d6fcc
    type: obsolete
```

**关联规则 → 规则或关联规则：`correlation.rules`。** 它"引用一条或多条 Sigma 规则或关联规则，允许用户把多个关联串在一起"，被引用规则用 `id` 或 `name` 指称。原文例子中同时出现两种引用方式：一种是 UUID `5638f7c0-ac70-491d-8465-2a65075e0d86`，另一种是可读名 `firewall_block`，注释说明内部工具有一张由 `name` 查 `id` 的查找表。

**关联规则 → 事件字段：`group-by` 与 `aliases`。** `group-by` 定义一个或多个字段作为独立的事件发生范围，多字段是 AND 关系。`aliases` 解决"同一字段在不同规则匹配的事件里叫不同名字"的问题，是"别名 → （Sigma 规则名 → 事件中的源字段名）"的两级映射，别名随后可在 `group-by` 中引用。资料给出的完整例子是：别名 `internal_ip` 在规则 `internal_error` 匹配的事件里解析为 `destination.ip`，在规则 `new_network_connection` 匹配的事件里解析为 `source.ip`；别名 `remote_ip` 正好相反。关联规则只有在两条规则分别以相同地址出现在对应字段时才命中。

**检测侧 → 数据侧：经过 `logsource` 这个中间对象，而不是直接绑定遥测源。** 规则只声明 `logsource` 的 `category`、`product`、`service`；这三个值"由转换器自动求值"，转换器再按配置文件把抽象值指向具体索引，例如 `category: firewall` 在 Splunk 中转换成 `( index=fw1* OR index=asa* )`，`product: windows` 在 Elasticsearch 中转换成 `"_index":"logstash-windows*"`。资料明确称这种抽象方法的优点是"不把规则限制到某个具体遥测源"，并说与其为 Sysmon、Microsoft-Windows-Security-Auditing、Microsoft-Windows-Kernel-Process 等每个可能的产品专有来源各写一条规则，不如使用通用日志源。`definition` 是这一关系中的旁注字段，它不被转换器自动求值，只向读者说明如何配置日志源以提供检测所需事件。

**检测侧 → 攻击侧：只有标签层面的弱关联。** 资料中唯一涉及攻击侧对象的机制是 `tags` 的点分命名空间，例如 `attack.t1234` 指命名空间 `attack` 中的技术 1234。规范没有把技术、战术、缓解措施建模成对象，也没有从技术指回规则的反向字段；标签的完整内容在未随资料提供的 sigma-appendix-tags.md 中。因此这一侧的关系类型应记为"通过技术编号字符串关联"，而非通过某个被建模的关系对象。

**规则 → 运行环境/工具：`taxonomy`、占位符与值修饰符。** `taxonomy` 声明命名约定由工具转换；占位符（如 `%Servers%`）在转换或使用规则时获得最终含义，可以替换为单个或多个 OR 连接的值或模式，也可以替换为查询表达式（如 `LOOKUP(field, servers)`），甚至可以在匹配规则时查表或调用 API；工具无法处理占位符时必须拒绝规则。值修饰符以管道符 `|` 追加在字段名之后，可链式书写并按书写顺序应用。

**关联规则 → 被引用规则的生成行为：`generate`。** 它决定被引用规则是作为独立规则被转换，还是只生成关联查询，默认是后者。

资料未说明：是否存在缓解措施、数据源组件、测试用例、事件类这些对象，以及它们与本框架对象的关系；资料中未出现这些类型。

## 5. 抽象层次的选择

**一个条目写到多细。** 规则描述的是"对日志数据的搜索属性"（properties of searches on log data），`logsource` 描述的是"检测所要应用的日志数据"，并进一步说明它描述日志源、平台、应用以及检测所需的类型。也就是说，条目停在"可复用的行为/模式"这一层：它不绑定某个具体遥测产品，也不写死某条日志的具体取值。资料用"与其为每个遥测源各写一条规则，不如使用通用日志源"的论述明确了这一取舍，并强调"这种抽象方法的优点是不把规则限制到某个具体遥测源"。例子里 `category: process_creation` 加 `product: windows` 就能覆盖多个具体的进程创建日志来源。

**什么时候是新条目、什么时候是变体、什么时候不收录。**

- 写新 `id` 的情形有三种：规则发生重大变化（例如不同的规则逻辑）；从既有规则派生出新规则或对规则做细化，且两者都要保持有效；合并规则。
- 记为变体的情形：`related` 的 `type: similar`，用于"同一检测内容应用于不同日志源"，或"只是 level 不同的修改版本"。
- 被取代或作废的情形：`status: deprecated`（"规则已被另一条取代或覆盖，链接由 `related` 字段建立"），配合 `obsolete`、`merged`、`renamed` 关系。`renamed` 明确说明旧 id 的规则预期不再存在。
- 保留但不可用的情形：`status: unsupported`，定义为"规则在当前状态下无法使用（旧的关联格式、自定义字段）"。这说明框架容忍"收录了但不能执行"的条目。
- 明确被放弃的抽象路线：早期把关系写进 `condition` 的聚合与 near 运算符的做法"现已废弃"，理由是四条——把单事件规则与多事件关系的耦合起来不一致（有时间关系时，写规则的人必须决定由哪条规则承载关系定义）；不灵活，因为一条 Sigma 规则恰只对应一个日志源，关系表达被限制在同一日志源的事件之间；Sigma 规则的目标之一是保持 condition 逻辑简单，而时间关系的查询表达式会变得很复杂，链式关联又增加复杂度；pipe 语法会让贡献者误以为是 Splunk 查询。

**准入标准。** 规范层面要求规则是符合约定的 YAML 文件（编码、换行、缩进、键名大小写、引号规则、文件名规则），组件层面给出 `title`、`logsource`、`detection`（含 `condition`）必填；"JSON Schema 中定义了必填字段、类型等更多细节"，但 Schema 内容未随资料提供。资料未给出内容层面的收录标准，例如什么样的检测值得成为一条规则、是否需要最低严重级别或误报阈值。

## 6. 稳定部分与易变部分

**希望很少变的部分。** 文件级约定：UTF-8 编码、LF 换行、4 空格缩进、键小写（如 `title`、`id`）、字符串值用单引号（字符串内含单引号时可改用双引号）、数值不加引号。文件名约定与扩展名 `.yml`。必填组件与字段语义：`title`、`logsource`、`detection` 与其中的 `condition`。标识方案：`id` 用 UUID v4，`related` 的五种关系类型与语义。默认 taxonomy `sigma`。检测值语义：值按不区分大小写字符串处理、通配符 `*` 与 `?`、反斜杠转义规则、list 之间 OR 与 map 之间 AND、condition 的运算符与优先级。两份 JSON Schema。资料把这些写成规范性约定（"为了保持规则互操作，请遵循以下要求"），可视为骨架。

**预期不断增长的部分。** 具体规则条目与关联条目本身；值修饰符列表（资料指向单独的 appendix 文件）；标签集合（"欢迎通过 pull request 或 issue 提议新标签"）；taxonomy 与 logsource 的取值集合（指向 taxonomy 附录与 SigmaHQ Logsource Guides）；关联类型与条件能力——关联规范的 History 显示 v2.1.0 新增了 `value_sum`、`value_avg`、`value_percentile` 三种关联类型和 `neq` 运算符，v2.0.2 为 temporal 规则增加 Requires 字段，v2.0.1 补上缺失的 `status` 与 `falsepositives`。规则规范自述 condition 是"规范中最复杂的部分，会随着时间推移和新出现的需求而变化"。

**新增与废弃的流程与版本管理。** 内容侧：新增用新 `id` 并（在需要时）用 `related` 记录派生/合并/相似关系；废弃用 `status: deprecated` 加 `related` 指向替代者，或 `obsolete` 关系；改名用 `renamed` 记录旧标识；状态 `unsupported` 标记当前不可用的规则；修改后更新 `modified` 日期，资料列出应更新该日期的变更类型。格式侧：两份规范各有 History 章节记录版本号与日期，废弃的做法（condition 内的聚合与 near 运算符）被明确标注为"现已废弃"并由关联规则取代。

资料未说明：发布节奏、评审与合入流程（除"欢迎提交 pull request 或 issue"外）、弃用的宽限期、旧规则批量迁移的工具或计划。

## 7. 内容与执行的分离

**内容以什么形式存放。** 内容是 YAML 文件：规则"以 yaml 格式书写"，并有编码、换行、缩进、键名、引号等互操作约定；关联规则是"一个专用的 YAML 文档"，一个关联场景可以用多文档 YAML（`---`）把若干规则放在同一文件里。内容受 JSON Schema 约束，检测规则与关联规则各有一份 Schema 文件路径被给出，但内容未随资料提供；Schema 用于说明必填字段、类型等信息。

**由什么来解释或执行。** 由转换器（converters / conversion backend）加目标后端执行。`logsource` 的 `category`、`product`、`service`"由转换器自动求值"，转换器按配置文件把抽象值映射为具体查询片段（Splunk 的 `( index=fw1* OR index=asa* )`、Elasticsearch 的 `"_index":"logstash-windows*"`）。非默认 taxonomy 必须由使用工具处理或转换为默认 taxonomy。占位符由使用工具在转换或使用规则时解析，甚至可以在匹配规则的过程中查表或调用 API。`name` 到 `id` 的转换也必须由工具自动完成。`''`（空值）与 `null`（空引用）这两个特殊字段值的适用方式"取决于目标 SIEM 系统"。

**内容能表达的逻辑上限。** condition 只支持前述若干表达式形式并规定了优先级；`all of them` 的用法被劝阻，因为它妨碍下游用户通用地过滤掉不需要的匹配，规范建议改用 `all of {search-identifier-pattern}`。关联规则的 `condition` 更窄：只允许恰好一个比较准则（`gt`/`gte`/`lt`/`lte`/`eq`/`neq`），要表达区间就用 AND 连接两个准则。值修饰符被明确分成两类：转换类修饰符（transformation modifiers）"一般是后端无关的，意思是可以在任何后端上使用"，且可以改变值之间的逻辑运算；类型类修饰符（type modifiers）主要用于告诉后端以不同方式处理某个值（例如 `re` 表示按正则处理），"必须被后端支持"。占位符自 Sigma 1.1 起只有加上 `expand` 修饰符才会被处理，普通百分号需用反斜杠转义。

**超出上限时怎么办。** 规范给出的出路是链式组合："如果需要更复杂的构造，你总可以把关联规则串起来。" 另一条出路是转换期的能力协商：当目标后端能力不足或只部分支持时，规范要求区分 must 与 should 两种情况——"如果转换后端要从不支持但被指定为 must 的特性生成查询，必须抛出错误"；对标记为 "should" 的方面则"应发出警告以提高用户对该限制的认识"。资料列举的后果有四类：可能被误读；改变规则匹配的意图或上下文；造成大量误报；造成漏报。具体例子包括：目标系统能聚合出现次数但不能对聚合计数施加过滤条件；无法按给定分组条件聚合；链式关联只能生成到中间某条关联规则；能识别时间关系但无法识别事件顺序（可能因顺序不同的误报）；时间关系只能落在静态时间边界内（如 1 小时窗口只匹配完整整点内的事件，跨整点会漏报）。

资料未说明：是否有官方参考实现或校验器、Schema 的具体约束内容、转换器的实现语言与分布方式。

## 8. 覆盖与成熟度的表达

**成熟度用 `status` 表达，取值五档且各有定义：** `stable` 表示"规则被认为是稳定的，可用于生产系统或仪表盘"；`test` 表示"基本稳定，但可能需要根据环境做小幅调整"；`experimental` 表示"实验性规则，可能产生误报或噪声，但也可能识别出有意思的事件"；`deprecated` 表示"规则已被另一条取代或覆盖，链接由 `related` 字段建立"；`unsupported` 表示"规则在当前状态下无法使用（旧的关联格式、自定义字段）"。关联规则文档重复了同一组取值与定义。

**严重性用 `level` 表达，取值五档：** `informational`（用于给事件打标等富化用途，不应触发告警，因为预期会有大量事件命中）、`low`（值得注意但很少构成事件，可结合数量或与其它事件组合才有意义，建议定期复核）、`medium`（相关事件，应较频繁地人工复核）、`high`（相关事件，应触发内部告警并要求及时复核）、`critical`（高度相关、表明发生事件，应立即复核，"只在概率接近确定性时使用"）。关联规则的 `level` 语义不同，它是"关联命中时的严重性调整"，允许把单事件命中设为 `low` 或 `informational`，在事件关联出现时提升到更高级别。

**依据（证据）用若干字段表达：** `references` 记录规则来源，可以是博客文章、技术论文、演讲稿甚至推文；`author` 记录创建者；`date` 与 `modified` 记录创建与最后修改日期，并明确规定哪些变更需要更新 `modified`；`description` 要求"简短而准确"地描述规则与可检测到的恶意或可疑活动；`falsepositives` 列出"可能出现的已知误报"；`license` 按 SPDX ID 记录许可。`related` 的 `similar` 关系还能表达"只是 level 不同的修改版本"。

**覆盖。** 资料中没有覆盖矩阵，也没有"某技术是否被覆盖、覆盖得多好"的字段。能把规则与攻击侧对应起来的只有 `tags` 的点分命名空间（如 `attack.t1234`）；能限定规则适用范围的只有 `scope`（例如只应作用于装了某软件的 Windows Server 时加 `server`）；能表达"在当前环境下是否可用"的只有 `status`（尤其 `unsupported`）以及前述转换期的报错/告警机制。检测侧与数据侧的关系隐含在 `logsource` 的三级抽象与转换器的索引映射中，但没有显式的覆盖率或数据源覆盖清单。资料未说明任何形式的覆盖率百分比、技术×数据源矩阵或成熟度评分。

## 9. 对我们的启发

分析：Sigma 用"稳定 id + 唯一 name + 一套固定的关系词表"来管理条目的身份与演化，这套机制可以直接搬到我们库的 knowledge_base 与 methods 两层。我们的方法层现在按论文一篇篇地加，最大的问题正是"说不清关系"：同一篇论文的后续改进、被证明有问题的旧方法、改名或重写的实现，都没有承载物。Sigma 的做法是 `id` 用 UUID v4 保证全局唯一、`name` 作为唯一人类可读名用于引用、`related` 用 `derived`/`obsolete`/`merged`/`renamed`/`similar` 五种类型显式记录"派生、作废、合并、改名、相似"。这是直接可迁移的：机制与领域无关，只需把词表的中文语义定义清楚，并规定"逻辑发生重大变化、派生后两者都要保留、合并"这三种情况必须新开 id（这正是 Sigma 的判据）。唯一需要适配的是 `name` 的"每次引用内唯一"这一层含义。

分析：Sigma 用 taxonomy 与字段映射把"逻辑名"和"后端实际字段名"解耦，这个结构对应我们库的 runtime 层。规则里写逻辑字段名（如 `Image`），由 `fieldmappings` 映射到具体来源的字段名（如 Windows 事件的 `NewProcessName`），还可以整体切换 taxonomy 并用工具转换。我们的运行时已经在训练流程的 11 个位置暴露数据，但这些位置的命名很可能随框架（PyTorch、DeepSpeed 等）和版本漂移；应该建立同样的逻辑分类法与映射表，让方法只引用逻辑位置，由运行时适配器负责映射。需要注意的差异是：我们的"字段"是张量与元数据，映射表除了名字还要描述形状、dtype、生命周期与是否可写，这一点 Sigma 的字段映射不提供参照。

分析：Sigma 让条目显式声明抽象的"数据源"而不是绑定具体实现，这一点应当作为我们方法层的准入要求。`logsource` 的 `category`/`product`/`service` 三级抽象使一条规则可以覆盖多个遥测来源，避免了"每个来源写一条规则"的组合爆炸。同理，我们的每个防御方法应声明它需要哪一类数据接口（样本、梯度、训练步内的 LoRA 更新、客户端上传、聚合结果、下发内容、通道消息），而不是声明"我要挂在某个框架的某个钩子上"；这样同一条方法才能在多个运行时上复用。差异在于我们的位置集合是库自己定义的封闭集合（11 个），而 Sigma 的取值集合是开放的，因此我们还需要一份位置的版本化清单。

分析：Sigma 的能力协商采用"must 报错、should 告警"的两级语义，可以直接用于我们库的 runtime 层。规范要求转换后端在遇到"不支持但被指定为 must"的特性时抛出错误，对 "should" 级别的限制只发警告，并明确列出四类后果（被误读、改变上下文、大量误报、漏报）。我们的运行时在某个训练框架下无法提供某方法必需的数据时（例如不暴露优化器状态、拿不到逐样本梯度），也应当硬失败；对"只能降级运行"的情况（例如只能拿到聚合后的更新、看不到单样本）发警告并记录降级点。这比"静默降级"更能防止评测结论失真。

分析：给每个方法加 `status` 成熟度字段，适合 methods 与 knowledge_base 两层。`stable`/`test`/`experimental`/`deprecated`/`unsupported` 五档恰好覆盖我们面对的现实：有的论文方法我们已经复现并跑通（stable），有的只在特定配置下有效（test），有的实验结果噪声很大（experimental），有的被新方法取代（deprecated），还有的依赖我们数据面没有的自定义信息而根本无法使用（unsupported）。特别值得借鉴的是 `unsupported` 这一档：Sigma 允许收录但不能执行的条目存在，并把它与"废弃"区分开，这对"论文收录了但暂时落不了地"的情况是一个准确的状态。

分析：`level` 的"分级 + 组合时升级"结构可以借，但语义必须重写，对应 evaluation 与 records 两层。Sigma 的 `level` 面向"是否要人工立即响应"，关联规则的 `level` 表示"命中时的严重性调整"，允许单事件低级别、关联后升级。我们的防御方法产出的是数值结论而不是告警，没有分析师值班语境，五档文字不能照抄；但"单个信号级别低、多个信号在同一轮次内同时出现则升级"这个结构非常适合表达我们跨位置、跨轮次的组合结论。等级的定义应换成可测指标（误报率、漏报率、对主任务效用的损失），而不是主观措辞。

分析：关联规则（meta-rule）是我们方法层最该借鉴的设计。它用 `rules` 引用其他规则（可链式）、用 `group-by` 定义分组、用 `timespan` 限定窗口、用 `condition` 做单准则比较、用 `aliases` 对齐跨规则字段名，并且可以在不改动基础规则的前提下表达复杂场景。映射到我们的库：基础方法对应单条 Sigma 规则，跨位置（样本异常 + 客户端上传异常）或跨轮次（连续若干轮出现）的组合对应关联规则，`group-by` 对应"按客户端/按层/按 LoRA 适配器分组"，`timespan` 对应"同一轮/连续 K 轮"，`condition` 的 `gt/gte/...` 对应数值阈值。需要适配的是语义：Sine 比较的是事件计数与字段值，我们比较的是统计量，时间窗要改成训练步或轮次。`aliases` 尤其有价值——同一概念（如"该客户端的更新范数"）在不同插件和不同框架里名字不同，需要一层别名才能组合。

分析：Sigma 规定"只有最外层关联规则可以定义元信息"，这一条可直接用于我们 methods 层的复合方法。把若干论文插件串成一个复合防御时，`status`、`level`、`date`、`author` 等元信息只应写在最外层，内层插件保持纯计算描述，避免同一个方法的元数据在多处漂移（例如内层插件被单独升级版本后，外层描述与现实不符）。这是低成本的治理规则。

分析：内容与执行分离、内容受 Schema 校验，直接对应我们 knowledge_base 层的组织方式。Sigma 的规则是数据文件，结构化字段由 JSON Schema 约束，执行交给转换器；于是"框架里有什么"可以从数据里查到，而不是从代码里读出来。我们的防御库同样应该把方法登记为可校验的数据（方法 id、需要的运行时位置、用到的算子、超参数、论文出处、状态、关系），代码按 id 引用，配套一个 schema 做加载期校验。这样"库到底覆盖了什么"才成为一个可以查询的问题。

分析：覆盖矩阵这一项不能照搬，因为 Sigma 本身就没有，这恰好是我们必须自建的部分。资料里能表达"覆盖"的只有 `tags` 的技术命名空间、`scope` 的适用机器范围和 `status` 的可用性，没有矩阵、没有覆盖率、没有"某技术被几条规则覆盖、覆盖质量如何"。我们如果照抄这套字段，会继承它"说不清覆盖"的毛病——而我们的目标恰恰是回答覆盖问题。因此应在 knowledge_base 层自建一张以"运行时位置 × 攻击/威胁类别"为轴的矩阵，每个格子记录证据来源（论文、实验、误报率），并把它挂在 evaluation 层做回归更新；Sigma 的 `status`/`references`/`related` 可以作为矩阵单元的属性，但不能替代矩阵本身。

分析：值修饰符的分层（转换类=后端无关，类型类=后端必须支持）对我们 operators 层有直接参考价值。Sigma 把"改变值的修饰符"和"改变值类型、必须由后端支持的修饰符"分开，并规定链式修饰符按书写顺序应用。我们的算子库同样是"可复用的计算单元"，其中一部分算子是框架无关的纯数学变换（可以任意后端运行），另一部分依赖特定运行时的能力（如混合精度、分布式通信、梯度检查点）；照此分层可以让"哪些算子一定可移植、哪些算子需要声明运行时能力"变成显式契约，而不是运行时才暴露。

分析：Sigma 的字符串匹配与条件语言不能照搬，因为我们的防御是数值算法而不是日志匹配。通配符 `*`/`?`、转义规则、`1 of them`、关键字检索的 `|all`、map=AND 与 list=OR、运算符优先级，全部是为"在日志文本里匹配模式"设计的布尔语义；我们的算子作用在梯度与张量上，没有"一条记录匹配或不匹配"的概念，也没有可供通配的字符串字段。因此 methods 层不应引入类似 condition 的匹配语言，而应使用数值算子组合（与 operators 层已有的抽象一致）；这一条明确不可迁移。

分析：占位符"在转换或使用规则时才获得最终含义"的机制，对应 runtime 与 operators 层的参数实例化。Sigma 规定 1.1 起只有带 `expand` 修饰符才处理占位符，工具处理不了就必须拒绝规则。我们的方法条目里也有很多环境相关参数（裁剪阈值、隐私预算、采样比例、聚合权重），它们同样不应写死在方法定义里，而应在部署/实例化时才解析；并且当运行时无法解析某个必需参数时，应像 Sigma 要求的那样直接拒绝执行，而不是静默套用默认值。

## 10. 框架自己承认的局限

- condition 是"规范中最复杂的部分"，并且"会随着时间推移和新出现的需求而变化"，即这一层被承认是不稳定的。
- 早期把关系表达写在 condition 里的做法（聚合与 near 运算符）被承认已废弃，理由包括：把单事件规则与多事件关系耦合起来不一致；不灵活，因为一条 Sigma 规则恰只对应一个日志源，关系只能在同一日志源的事件之间表达；会让 condition 逻辑变复杂；pipe 语法会被误认为是 Splunk 或其它目标系统专有查询语言。这最后一条是资料明确写出的常见误用。
- `all of them` 的用法被劝阻，理由是它会阻止规则的下游用户通用地过滤掉不需要的匹配，规范建议改用 `all of {search-identifier-pattern}`。
- 特殊字段值 `''` 与 `null` 的处理"取决于目标 SIEM 系统"，并且"在创建规则时被鼓励对 `null` 特别小心"；`null` 不能作为字段值列表的一员，要表达 `not null` 必须另建一个 selection 再在 condition 中取反。
- 占位符必须被使用工具恰当处理，"如果工具无法处理占位符，它必须拒绝该规则"；非默认 taxonomy 也必须由使用工具处理或转换为默认 taxonomy。
- 关联规则可能超出目标后端的能力：转换后端必须在不支持被指定为 must 的特性时报错，对 should 级别的限制发警告；资料列出的具体限制包括无法对聚合结果施加过滤条件、无法按给定分组聚合、链式关联只能生成到中间某一步、能识别时间关系但无法识别事件顺序（会误报）、时间关系只落在静态时间边界内（会漏报）。这些限制被承认可能导致查询结果被误读、改变匹配意图、造成大量误报或漏报。
- 关联规则本身不产生独立查询，只用于构造更复杂的结构；并且只有最外层关联规则可以定义元信息。
- `status: unsupported` 这一档承认存在"当前状态下无法使用"的规则，原因包括旧的关联格式与自定义字段。

资料未说明：除上述以外，框架是否还有其它公认的局限、未解决问题或常见误用；也没有给出局限的量化评估。

此外，作为复述性观察而非框架自陈，资料本身存在若干前后不一致之处：文件结构中相关引用写作 `references`，组件章节却把属性写作 `reference`；关联规则的 `correlation.type` 允许值只列了 `event_count`、`value_count`、`temporal`、`temporal_ordered` 四种，而 Correlation Types 一章另外描述了 `value_sum`、`value_avg`、`value_percentile` 三种，History 也确认 v2.1.0 新增了这三种；组件章节把 `group-by`、`timespan`、`condition` 都标为 mandatory，但各关联类型的 Requires 列表并不相同（`temporal` 与 `temporal_ordered` 的 Requires 不含 `condition`）；关联规则的 `status` 定义中 `deprecated` 说"链接由 `related` 字段建立"，但关联规则的组件列表里并没有 `related` 字段；`name` 在规则规范中要求唯一，在关联规范中则表述为"每条关联内唯一"。

## 11. 原文依据

1. > This section describes the log data on which the detection is meant to be applied to. It describes the log source, the platform, the application and the type that is required in the detection.

   支撑第 2 节：`logsource` 是必填组件，其职责是描述检测所针对的日志数据（日志源、平台、应用与所需类型）。

2. > Sigma rules should be identified by a globally unique identifier in the *id* attribute. For this purpose randomly generated UUIDs (version 4) is used.

   支撑第 3 节：编号格式为全局唯一的 UUID（version 4）。

3. > `derived`: The rule was derived from the referred rule or rules, which may remain active.

   支撑第 4 节：`related` 的关系类型有明确定义与方向（本条规则派生自被引用规则，被引用规则可能仍然有效）。

4. > Tags are namespaced, the dot is used as separator. e.g. *attack.t1234* refers to technique 1234 in the namespace *attack*; Namespaces may also be nested

   支撑第 4 节：检测侧与攻击侧之间只有标签字符串这一层关联，形式为点分命名空间加技术编号。

5. > Refers to one or multiple Sigma or Correlations rules. Allowing the user to chain multiple correlations together. A rule can be referred to by the `id` or `name` of a Sigma rule.

   支撑第 4 节：关联规则通过 `rules` 引用规则或其它关联规则，可链式组合，被引用者既可用 `id` 也可用 `name` 指称。

6. > Instead creating multiple rules for the different telemetry sources such as `Sysmon`, `Microsoft-Windows-Security-Auditing`, `Microsoft-Windows-Kernel-Process` and all the other possible product-specific sources, a generic log source may be used.

   支撑第 5 节：条目的抽象层次停在通用日志源，避免为每个具体遥测来源各写一条规则。

7. > `similar`: Use to relate similar rules to each other (e.g. same detection content applied to different log sources, rule that is a modified version of another rule with a different level)

   支撑第 5 节：什么情况算"已有条目的变体"而不是新条目。

8. > The condition is the most complex part of the specification and will be subject to change over time and arising requirements.

   支撑第 6 节：condition 被明确列为预期会持续变化的部分，与稳定的骨架相对。

9. > An error must be raised by the conversion backend if it would generate a query from a rule which contains a feature that is not supported but specified as must.

   支撑第 7 节：内容表达能力的边界由转换后端的能力协商处理，不支持且标记为 must 的特性必须报错。

10. > `stable`: the rule is considered as stable and may be used in production systems or dashboards.

    支撑第 8 节：成熟度由 `status` 字段分级表达，并给出每一档的判定含义。

```json
{
  "key": "sigma",
  "framework": "Sigma Rules Specification v2.1.0（2025-08-02）+ Sigma Correlation Rules Specification v2.1.0（2025-08-02）",
  "object_types": [
    {
      "name": "Sigma rule（Sigma 规则/检测规则）",
      "role": "detection",
      "fields": ["title", "id", "name", "related", "taxonomy", "status", "description", "license", "references", "author", "date", "modified", "logsource", "detection", "fields", "falsepositives", "level", "tags", "scope", "arbitrary custom fields"]
    },
    {
      "name": "Correlation rule / meta-rule（关联规则/元规则）",
      "role": "detection",
      "fields": ["title", "id", "status", "description", "author", "references", "date", "modified", "taxonomy", "correlation.type", "correlation.rules", "correlation.aliases", "correlation.group-by", "correlation.timespan", "correlation.condition", "correlation.field", "falsepositives", "level", "generate"]
    },
    {
      "name": "Search-identifier（搜索标识符，detection 的子结构）",
      "role": "detection",
      "fields": ["name（标识符名，以 _ 开头者在 of them 中被排除）", "string-list（字符串列表，彼此 OR）", "map-list（映射列表，彼此 OR）", "field: value（映射内 AND）"]
    },
    {
      "name": "Condition（检测条件表达式）",
      "role": "detection",
      "fields": ["logical AND/OR（逻辑与或）", "1 of them / all of them", "1 of / all of {search-identifier-pattern}", "not（取反）", "brackets（括号，优先级最高）"]
    },
    {
      "name": "LogSource（日志源）",
      "role": "telemetry",
      "fields": ["category", "product", "service", "definition", "[任意数量的可选元素]"]
    },
    {
      "name": "Taxonomy（分类法，声明字段名/字段值/日志源名的命名约定）",
      "role": "other",
      "fields": ["taxonomy 名称（默认 sigma）"]
    },
    {
      "name": "Tag（标签，点分命名空间字符串）",
      "role": "relation",
      "fields": ["namespaced tag string（如 attack.t1234，命名空间可嵌套）"]
    },
    {
      "name": "Related reference（related 关系引用）",
      "role": "relation",
      "fields": ["type（derived/obsolete/merged/renamed/similar）", "id（被引用规则标识）"]
    },
    {
      "name": "Aliases（关联规则内的字段别名）",
      "role": "relation",
      "fields": ["<alias name>", "<Sigma rule name>", "<source field name in event matched by Sigma rule>"]
    },
    {
      "name": "Sigma Filter（元过滤器，资料仅提及存在单独规范）",
      "role": "other",
      "fields": []
    },
    {
      "name": "JSON Schema（规则与关联规则的模式文件）",
      "role": "artifact",
      "fields": ["sigma-detection-rule-schema.json", "sigma-correlation-rules-schema.json"]
    }
  ],
  "id_scheme": "规则用 `id` 存随机生成的 UUID version 4，全局唯一；另有唯一人类可读名 `name`，可在关联规则中代替 id 被引用（工具负责 name→id 转换）；规则间关系由 `related` 的 `type`（derived/obsolete/merged/renamed/similar）+ `id` 表达；规则文件名要求 10 到 70 字符、全小写、只含 a-z0-9 与 `_`、扩展名 `.yml`，关联规则文件遵循同一约定并建议加前缀 `mr_`。",
  "attack_defense_link": "via_technique_id",
  "link_detail": "检测规则与攻击侧的唯一连接是 `tags` 里的点分命名空间字符串，例如 `attack.t1234` 表示命名空间 attack 中的技术 1234；规范没有把技术、战术、缓解措施建模成对象，也没有从技术指回规则的反向字段，标签的完整语义在未随资料提供的 sigma-appendix-tags.md 中。检测侧与数据侧则是经 `logsource` 的 category/product/service 抽象层相连，由转换器按配置文件映射到具体索引（如 firewall 映射为 index=fw1* OR index=asa*），而不是直接绑定某个遥测源；规则之间另有 related 关系与 correlation.rules 引用关系。",
  "abstraction_level": "规则描述的是『对日志数据的搜索属性』，日志侧用 category/product/service 抽象到不绑定具体遥测源，条目粒度是可复用的行为模式而非某条日志的具体取值；同一检测内容换日志源、或只是 level 不同的版本记为 related type=similar，规则逻辑重大变化、派生后两者都要保留、合并规则这三种情况写新 id，被取代的标 deprecated 并加 related，旧关联格式或使用自定义字段而当前不可用的标 unsupported。内容层面的收录标准资料未说明。",
  "stable_parts": [
    "YAML 文件约定：UTF-8 编码、LF 换行、4 空格缩进、键小写、字符串用单引号、数值不加引号",
    "文件名约定：10 到 70 字符、小写、只含 a-z0-9 与下划线、扩展名 .yml，关联规则建议前缀 mr_",
    "必填组件：title、logsource、detection（含 condition）；关联规则的 title、type、rules、group-by、timespan、condition",
    "标识方案：id 为 UUID v4；related 的五种关系类型 derived/obsolete/merged/renamed/similar",
    "默认 taxonomy `sigma`",
    "检测值语义：值不区分大小写、通配符 * 与 ?、反斜杠转义规则、list 之间 OR 与 map 之间 AND",
    "condition 的表达式集合与运算符优先级（or < and < not < x of search-identifier < 括号）",
    "两份 JSON Schema（sigma-detection-rule-schema.json、sigma-correlation-rules-schema.json）"
  ],
  "growing_parts": [
    "具体规则条目与关联规则条目本身",
    "值修饰符（value modifiers）列表，见单独 appendix（内容未随资料提供）",
    "标签集合，欢迎用 pull request 或 issue 提议新标签",
    "关联类型与比较符：v2.1.0 新增 value_sum、value_avg、value_percentile 与 neq",
    "condition 的表达能力，原文自述会随需求变化",
    "taxonomy 与 logsource 的取值集合（taxonomy 附录、SigmaHQ Logsource Guides）"
  ],
  "content_format": "YAML 文件（UTF-8、LF、4 空格缩进、键小写、字符串单引号、数值不加引号）；检测规则与关联规则各有 JSON Schema 约束（../json-schema/sigma-detection-rule-schema.json 与 ../json-schema/sigma-correlation-rules-schema.json，内容未随资料提供）；一个关联场景可写成多文档 YAML，用 `---` 把若干规则放在同一文件。",
  "execution_engine": "转换器（converters / conversion backend）加目标后端（如 Splunk、Elasticsearch 的查询生成）。转换器自动求值 logsource 的 category/product/service 并按配置文件映射到索引；taxonomy 转换、占位符解析、name→id 解析由使用工具负责；特殊字段值 `''` 与 `null` 的最终语义由目标 SIEM 决定；不支持但标记为 must 的特性必须报错，标记为 should 的限制发警告。",
  "coverage_expression": "资料未给出覆盖矩阵、覆盖率字段或技术×数据源的表。能把规则挂到攻击侧的只有 tags 的点分命名空间（如 attack.t1234）；能限定适用范围的只有 scope（如 server）；能表达当前是否可用的是 status（尤其 unsupported）以及转换期的报错与告警；检测侧与数据侧的对应隐含在 logsource 三级抽象与转换器映射中，没有显式覆盖度。",
  "maturity_expression": "`status`：stable（可用于生产系统或仪表盘）、test（基本稳定但可能需按环境微调）、experimental（可能有误报或噪声）、deprecated（已被取代或覆盖，链接由 related 建立）、unsupported（当前状态不可用）。`level`：informational/low/medium/high/critical 五档，描述触发规则的严重性；关联规则的 level 是命中时的严重性调整。此外 falsepositives 列出已知误报，references/author/date/modified 提供出处与时间依据，related 的 similar 可标注仅 level 不同的版本。",
  "lessons": [
    {
      "idea": "用稳定 id（UUID v4）+ 唯一人类可读 name + 固定关系词表（derived/obsolete/merged/renamed/similar）管理条目的身份与演化",
      "applies_to": "knowledge_base",
      "transfer": "direct",
      "why": "我们的方法层按论文组织，天然会出现派生、合并、改名、被取代的情况；照搬这套身份与关系词表可以把『这个方法被谁取代、和谁相似』变成可查询的数据，而不是散落在文档或口头约定里。需要适配的只是 name 的唯一范围定义。"
    },
    {
      "idea": "用 taxonomy 与字段映射把逻辑名与具体后端的字段名解耦",
      "applies_to": "runtime",
      "transfer": "adapted",
      "why": "我们的 11 个运行时位置同样需要一套逻辑分类法（样本、梯度、训练步内 LoRA、客户端上传、聚合结果、下发内容、通道消息等），方法只引用逻辑位置，由运行时适配器映射到具体框架的钩子与张量名；差异在于我们的『字段』是张量与元数据，映射表还要描述形状、dtype、生命周期与可写性。"
    },
    {
      "idea": "条目显式声明抽象数据源/干预点，而不是绑定具体实现",
      "applies_to": "methods",
      "transfer": "direct",
      "why": "Sigma 用 category/product/service 让一条规则覆盖多个遥测来源，避免每个来源写一条规则；我们的方法也应声明需要哪一类数据接口而不是挂在某个框架的某个钩子上，这样同一条方法才能在多个运行时上复用。差异是我们的位置集合是库自定的封闭集合，需要额外维护版本化清单。"
    },
    {
      "idea": "能力协商分两级：必需特性不支持则报错，可降级特性不支持则告警",
      "applies_to": "runtime",
      "transfer": "direct",
      "why": "规范要求转换后端对不支持的 must 特性抛错、对 should 限制发警告，并列出误读、上下文改变、大量误报、漏报四类后果。我们的运行时在无法提供某方法必需数据（如逐样本梯度、优化器状态）时应硬失败，在只能降级运行时告警并记录降级点，避免评测结论失真。"
    },
    {
      "idea": "给每个条目加 status 成熟度字段，并用 unsupported 表示『收录但当前不可用』",
      "applies_to": "methods",
      "transfer": "direct",
      "why": "stable/test/experimental/deprecated/unsupported 恰好覆盖我们复现论文方法的现实状态；把 unsupported 与 deprecated 区分开，能准确表达『论文收录了但依赖我们数据面没有的信息，暂时落不了地』这一常见情况。"
    },
    {
      "idea": "分级 + 组合时升级的严重度结构（level 与关联规则的 level 调整）",
      "applies_to": "evaluation",
      "transfer": "adapted",
      "why": "Sigma 的 level 面向是否要人工立即响应，我们的方法产出数值结论、没有分析师语境，五档文字不能照抄；但『单信号低级别、多信号在同一轮次同时出现则升级』的结构适合表达我们跨位置、跨轮次的组合结论，等级定义应换成误报率、漏报率与主任务效用损失等可测指标。"
    },
    {
      "idea": "用关联规则/元规则表达跨条目的组合：rules 引用、group-by 分组、timespan 窗口、condition 单准则比较、aliases 跨规则对齐字段名",
      "applies_to": "methods",
      "transfer": "adapted",
      "why": "基础方法对应单条规则，跨位置（样本异常 + 客户端上传异常）或跨轮次的组合对应关联规则，group-by 对应按客户端/按层分组，timespan 对应同一轮或连续 K 轮；aliases 解决同一概念在不同插件与框架里命名不同的问题。需要适配的是语义：Sigma 比较事件计数与字段值，我们比较统计量，时间窗要改成训练步或轮次。"
    },
    {
      "idea": "复合结构中只有最外层承载元信息（status、level、date 等）",
      "applies_to": "methods",
      "transfer": "direct",
      "why": "把若干论文插件串成复合防御时，元信息只写在最外层、内层保持纯计算描述，可以避免内层插件单独升级后外层描述与现实不符的漂移问题，是一条低成本的治理规则。"
    },
    {
      "idea": "内容即数据、由 Schema 校验、由独立执行器解释",
      "applies_to": "knowledge_base",
      "transfer": "direct",
      "why": "Sigma 规则是结构化数据文件，执行交给转换器，于是『框架里有什么』可以从数据查到而不是从代码读出。我们的方法登记表同样应是可校验数据（方法 id、所需运行时位置、算子、参数、出处、状态、关系），代码按 id 引用，这样『库到底覆盖了什么』才成为可查询的问题。"
    },
    {
      "idea": "覆盖矩阵：Sigma 只提供 tags/scope/status，没有覆盖矩阵，这一项必须自建而不能照搬",
      "applies_to": "knowledge_base",
      "transfer": "not_transferable",
      "why": "资料中没有覆盖率字段、技术×数据源矩阵或覆盖质量表达；若照抄这套字段，会继承它『说不清覆盖』的毛病。应自建以运行时位置 × 攻击/威胁类别为轴的矩阵，每个格子记录证据（论文、实验、误报率），并挂到 evaluation 层回归更新；Sigma 的 status/references/related 只能作为矩阵单元的属性。"
    },
    {
      "idea": "算子/修饰符分层：后端无关的转换型修饰符与必须由后端支持的类型型修饰符分开，链式修饰符按书写顺序应用",
      "applies_to": "operators",
      "transfer": "adapted",
      "why": "我们的算子库同样混合了框架无关的纯数学变换与依赖特定运行时能力的算子（混合精度、分布式通信、梯度检查点）；照此分层可以把『哪些算子一定可移植、哪些需要声明运行时能力』变成显式契约，而不是运行时才暴露。"
    },
    {
      "idea": "字符串匹配与条件语言（通配符、转义、1 of them、关键字 |all、map=AND/list=OR、运算符优先级）",
      "applies_to": "operators",
      "transfer": "not_transferable",
      "why": "这套语法是为『在日志文本里匹配模式』设计的布尔语义，我们的防御是数值算法，算子在梯度与张量上运算，不存在一条记录匹配或不匹配的概念，也没有可通配的字符串字段；方法层不应引入类似 condition 的匹配语言，而应使用数值算子组合。"
    },
    {
      "idea": "环境相关参数在转换/实例化时才解析（占位符 + expand 修饰符），工具处理不了就拒绝",
      "applies_to": "runtime",
      "transfer": "direct",
      "why": "我们的方法条目同样有大量环境相关参数（裁剪阈值、隐私预算、采样比例、聚合权重），不应写死在方法定义里；并且当运行时无法解析某个必需参数时，应像规范要求的那样拒绝执行，而不是静默套用默认值。"
    }
  ],
  "limits": [
    "condition 被自述为『规范中最复杂的部分』，会随需求持续变化，属于公认不稳定的层",
    "早期把关系写进 condition 的聚合与 near 运算符做法已废弃，原因包括耦合不一致、一条规则只对应一个日志源导致关系只能同源、condition 逻辑要保持简单、pipe 语法被误认为 Splunk 等目标系统查询语言（常见误用）",
    "all of them 的用法被劝阻，因为它妨碍下游用户通用地过滤不需要的匹配，建议改用 all of {search-identifier-pattern}",
    "特殊字段值 '' 与 null 的处理取决于目标 SIEM；规范要求创建规则时特别小心 null，null 不能作为字段值列表的一员，表达 not null 需要另建 selection 再取反",
    "占位符必须由使用工具处理，工具处理不了就必须拒绝该规则；非默认 taxonomy 也必须由工具处理或转换为默认 taxonomy",
    "关联规则可能超出目标后端能力：不支持且标记为 must 的特性必须报错、标记为 should 的限制发警告；具体限制包括无法对聚合结果施加过滤、无法按分组聚合、链式关联只能生成到中间某步、能识别时间关系但无法识别顺序（会误报）、时间关系只落在静态时间边界内（会漏报），后果被列为误读、改变匹配意图、大量误报、漏报",
    "关联规则不产生独立查询，只用于构造更复杂的结构；只有最外层关联规则可以定义元信息",
    "status: unsupported 承认存在当前状态下无法使用的规则，原因是旧的关联格式与自定义字段"
  ],
  "quotes": [
    {
      "supports": "第 2 节：logsource 描述检测所针对的日志数据，包含日志源、平台、应用与所需类型，是必填组件",
      "text": "This section describes the log data on which the detection is meant to be applied to. It describes the log source, the platform, the application and the type that is required in the detection."
    },
    {
      "supports": "第 3 节：编号格式为全局唯一标识，使用随机生成的 UUID version 4",
      "text": "Sigma rules should be identified by a globally unique identifier in the *id* attribute. For this purpose randomly generated UUIDs (version 4) is used."
    },
    {
      "supports": "第 4 节：related 的关系类型有明确定义与方向，derived 表示本条规则派生自被引用规则",
      "text": "`derived`: The rule was derived from the referred rule or rules, which may remain active."
    },
    {
      "supports": "第 4 节：攻击侧与检测侧的连接只是标签的点分命名空间字符串，如 attack.t1234 指向技术编号",
      "text": "Tags are namespaced, the dot is used as separator. e.g. *attack.t1234* refers to technique 1234 in the namespace *attack*; Namespaces may also be nested"
    },
    {
      "supports": "第 4 节：关联规则通过 rules 引用规则或关联规则、可链式组合，被引用者可用 id 或 name 指称",
      "text": "Refers to one or multiple Sigma or Correlations rules. Allowing the user to chain multiple correlations together. A rule can be referred to by the `id` or `name` of a Sigma rule."
    },
    {
      "supports": "第 5 节：条目的抽象层次停在通用日志源，避免为每个具体遥测来源各写一条规则",
      "text": "Instead creating multiple rules for the different telemetry sources such as `Sysmon`, `Microsoft-Windows-Security-Auditing`, `Microsoft-Windows-Kernel-Process` and all the other possible product-specific sources, a generic log source may be used."
    },
    {
      "supports": "第 5 节：什么算已有条目的变体——同一检测内容用于不同日志源，或只是 level 不同的版本，记为 related type=similar",
      "text": "`similar`: Use to relate similar rules to each other (e.g. same detection content applied to different log sources, rule that is a modified version of another rule with a different level)"
    },
    {
      "supports": "第 6 节：condition 被明确列为会持续变化的部分，与希望少变的骨架相对",
      "text": "The condition is the most complex part of the specification and will be subject to change over time and arising requirements."
    },
    {
      "supports": "第 7 节：内容表达能力的边界由转换后端做能力协商，不支持且标记为 must 的特性必须报错",
      "text": "An error must be raised by the conversion backend if it would generate a query from a rule which contains a feature that is not supported but specified as must."
    },
    {
      "supports": "第 8 节：成熟度由 status 字段分级表达，stable 表示可用于生产系统或仪表盘",
      "text": "`stable`: the rule is considered as stable and may be used in production systems or dashboards."
    }
  ]
}
```
