# atomic_red_team：Atomic Red Team™（资料未说明版本号；README 徽章显示 Atomics-1878）

## 1. 要解决的问题

资料表明，Atomic Red Team™ 是 "a library of tests mapped to the MITRE ATT&CK® framework"（一个映射到 MITRE ATT&CK® 框架的测试库），使用者是 "Security teams"（安全团队），目的是让安全团队能够 "quickly, portably, and reproducibly test their environments"（快速、可移植、可复现地测试自己的环境）。README 说明可以直接从命令行执行原子测试而无需安装，并说明该库由社区开发和维护（"Atomic Red Team is open source and community developed"）。

关于它明确说自己不做什么：资料没有专门的"非目标"章节。可以从两处间接看到边界。第一，README 把"更稳固的测试体验"指向外部执行框架（"For a more robust testing experience, consider using an execution framework like Invoke-Atomic"），说明执行能力不是这个库本身要解决的问题。第二，数据模型只覆盖测试的编写与校验，资料中完全没有出现检测规则、缓解措施、数据源等对象，说明它不负责这些内容。除上述两点外，资料未说明其他被排除的范围。

## 2. 核心对象

资料中的对象来自 `models.py` 的 pydantic 模型与 YAML 文件结构。存在的都是攻击/测试侧对象，外加若干目录与自动生成制品。资料未提及 tactic（战术）、mitigation（缓解措施）、data source（数据源）、detection rule（检测规则）、event class（事件类）等对象，这些在本资料中均未说明。

所有模型都继承 `StrictModel`，其配置为 `ConfigDict(validate_default=True, extra="forbid", validate_assignment=True)`，即：校验默认值、禁止额外字段、赋值时重新校验。这是下列所有对象的共同约束。

### Technique（技术）

| 字段名 | 含义 | 是否必填 | 取值约束 |
| --- | --- | --- | --- |
| `attack_technique` | 该技术对应的 ATT&CK 技术编号 | 必填 | 类型 `AttackTechniqueID`，正则 `T\d{4}(?:\.\d{3})?`，`min_length=5` |
| `display_name` | 技术显示名 | 必填 | `str`，`min_length=5`；YAML 实例为 `OS Credential Dumping: LSASS Memory` |
| `atomic_tests` | 该技术下的原子测试列表 | 必填 | `List[Atomic]`，`min_length=1`，至少一个测试 |

`Technique.model_post_init` 会为列表中每个测试写入 `test_number`，写法为 `f"{self.attack_technique}-{index + 1}"`。

### Atomic（原子测试）

| 字段名 | 含义 | 是否必填 | 取值约束 |
| --- | --- | --- | --- |
| `test_number` | 测试编号 | 选填（`Optional[str] = None`） | 由 `Technique` 在初始化后生成，不靠人工填写 |
| `name` | 测试名 | 必填 | `constr(min_length=1)` |
| `description` | 测试说明 | 必填 | `constr(min_length=1)` |
| `supported_platforms` | 支持平台列表 | 必填 | `conlist(Platform, min_length=1)`，至少一个，取值来自 `Platform` 枚举 |
| `executor` | 执行器 | 必填 | `Union[ManualExecutor, CommandExecutor]`，以 `name` 作为判别字段（`discriminator="name"`） |
| `dependencies` | 依赖（前置条件）列表 | 选填，默认 `[]` | `Optional[List[Dependency]]` |
| `input_arguments` | 输入参数字典 | 选填，默认 `{}` | 键为 `constr(min_length=2, pattern=r"^[\w_-]+$")`，值为 `Argument`；显式写 `None` 会报 `empty_input_arguments`；键必须与命令中的 `#{...}` 占位符双向完全匹配，否则报 `unused_input_argument` 或 `missing_input_argument` |
| `dependency_executor_name` | 执行依赖命令所用的执行器类型 | 选填，默认 `None` | 取值为 `ExecutorType`；键存在但为空（`None` 或 `""`）报 `empty_dependency_executor_name`；当 `dependencies == []` 而该键非空时报 `invalid_dependency_executor_name` |
| `auto_generated_guid` | 自动生成的 GUID | 选填，默认 `None` | `Optional[UUID]`，由 GitHub Actions 生成，贡献者无需手写 |

### Executor（执行器）及其子类

基类 `Executor`：

| 字段名 | 含义 | 是否必填 | 取值约束 |
| --- | --- | --- | --- |
| `name` | 执行器类型 | 必填 | `ExecutorType` |
| `elevation_required` | 是否需要提权 | 选填，默认 `False` | `bool` |

`ManualExecutor`（`name` 固定为 `"manual"`）：

| 字段名 | 含义 | 是否必填 | 取值约束 |
| --- | --- | --- | --- |
| `name` | 执行器类型 | 必填 | `Literal["manual"]` |
| `steps` | 手工执行步骤 | 必填 | `str`，`min_length=10` |

`CommandExecutor`（`name` 为 `"powershell"`、`"sh"`、`"bash"`、`"command_prompt"` 之一）：

| 字段名 | 含义 | 是否必填 | 取值约束 |
| --- | --- | --- | --- |
| `name` | 执行器类型 | 必填 | `Literal["powershell","sh","bash","command_prompt"]` |
| `command` | 执行命令 | 必填 | `constr(min_length=1)` |
| `cleanup_command` | 清理命令 | 选填，默认 `None` | `Optional[str]` |

跨字段约束：当 `supported_platforms` 含 `linux` 或 `macos`、执行器是 `CommandExecutor` 且 `command`/`cleanup_command` 中出现 `sudo` 时，`elevation_required` 必须为真，否则报 `elevation_required_but_not_provided`。

### Dependency（依赖/前置条件）

| 字段名 | 含义 | 是否必填 | 取值约束 |
| --- | --- | --- | --- |
| `description` | 依赖说明 | 必填 | `constr(min_length=1)` |
| `prereq_command` | 检查依赖是否就绪的命令 | 必填 | `constr(min_length=1)`；YAML 实例用 `exit 0`/`exit 1` 表示就绪与否 |
| `get_prereq_command` | 下载或安装依赖的命令 | 选填 | `Optional[str]` |

### Argument（输入参数）

参数是判别式联合 `Argument = Annotated[Union[FloatArg, IntArg, UrlArg, StringArg], Field(discriminator="type")]`，以 `type` 区分。公共基类 `BaseArgument` 含 `description: str`（必填）。四个具体类型：

| 类型名 | `type` 取值 | `default` 取值约束 | 是否必填 |
| --- | --- | --- | --- |
| `UrlArg` | `"url"`、`"Url"` | `Optional[DomainName | AnyUrl | IPvAnyAddress]` | `description` 必填，`default` 选填 |
| `StringArg` | `"string"`、`"path"`、`"String"`、`"Path"` | `Optional[str]` | 同上 |
| `IntArg` | `"integer"`、`"Integer"` | `Optional[int]` | 同上 |
| `FloatArg` | `"float"`、`"Float"` | `Optional[StrictFloat]` | 同上 |

### 枚举类型（约束字段取值，本身无字段）

- `Platform`：`windows`、`macos`、`linux`、`office-365`、`azure-ad`、`google-workspace`、`saas`、`iaas`、`containers`、`iaas:gcp`、`iaas:azure`、`iaas:aws`、`esxi`；`get_supported_platform` 把它们映射为显示名（如 `macos` → `macOS`、`command_prompt` 之外的执行器名即语言名）。
- `ExecutorType`：`manual`、`powershell`、`sh`、`bash`、`command_prompt`；`get_language` 把 `command_prompt` 映射为 `cmd`，把 `manual` 映射为空字符串。
- `InputArgType`：`url`、`string`、`float`、`integer`、`path`。

### 目录与制品

- 每个技术目录（Technique directory）包含：一个 YAML 测试文件、一个人工可读的 Markdown 测试文件（由 YAML 自动生成）、可选的 `src` 目录（源码依赖）、可选的 `bin` 目录（二进制依赖）。
- `atomics/Indexes`：由 GitHub Actions 生成的测试清单。
- `ExternalPayloads`：位于 `atomics` 同级的外部载荷目录，由 `prereq_commands` 下载依赖时写入。
- 云端测试的 Terraform 文件：放在 `src` 下以测试编号命名的目录，例如 `T1562.008/src/T1562.008-1/`，内含 `.tf` 文件与 `terraform.tfvars`。

资料未说明"制品（artifact）"作为带有字段的一等对象类型，上述目录与文件只以文件系统形式出现。

## 3. 编号与层级

技术编号采用 `AttackTechniqueID`，定义为 `Annotated[str, StringConstraints(pattern=r"T\d{4}(?:\.\d{3})?", min_length=5)]`，即字母 `T` 加四位数字，可再接一个点和三位数字表示子技术；实例有 `T1003.001`、`T1055`、`T1562.008`。

测试编号由模型生成，规则是 `test_number = f"{self.attack_technique}-{index + 1}"`，即"技术编号-序号"，序号从 1 开始，例如 `T1562.008-1`。YAML 中另有一个不可变标识 `auto_generated_guid`，类型为 UUID，由 GitHub Actions 生成。

目录与文件命名复用技术编号：贡献指南要求在 `atomics` 目录下选择以 ATT&CK 技术命名的目录，不存在则新建，例如 `atomic-red-team/atomics/T1055/T1055.yaml`；云端 Terraform 目录以测试编号命名，例如 `T1562.008/src/T1562.008-1/`。

层级上，资料显示的层次是 Technique（技术）→ Atomic（原子测试），一个技术下可以并列多个测试；更细的分层（例如战术层、平台层作为独立条目）资料未说明。资料中 `T1003.001` 的 `display_name` 是 `OS Credential Dumping: LSASS Memory`，即显示名含冒号分隔的两段文字，但资料未说明这种命名的构成规则。

同一事物在多处出现时的处理方式是"单一手写来源 + 自动派生"：YAML 测试文件是唯一需要人工编辑的内容，Markdown 测试文件与 `atomics/Indexes` 中的测试清单由自动化 GitHub Actions 生成，贡献者 "never need to update them manually"。命令内部的参数以 `#{...}` 占位符引用，例如 `#{procdump_exe}`、`#{output_file}`，必须与 `input_arguments` 的键一一对应；示例中还出现执行时解析的路径占位符 `PathToAtomicsFolder`，但资料未说明它的解析规则。输出文件名被要求包含技术编号。外部依赖被要求使用 permanent GitHub links（永久链接）引用，以防止意外变化。

## 4. 对象之间的关系

资料中出现的对象关系如下。

- Technique 1—N Atomic：由 `Technique.atomic_tests` 字段包含，`min_length=1`。
- Atomic 1—1 Executor：由 `Atomic.executor` 字段持有，按 `name` 做判别联合，在 `ManualExecutor` 与 `CommandExecutor` 之间二选一。
- Atomic 0—N Dependency：由 `Atomic.dependencies` 字段持有；`Atomic.dependency_executor_name` 指定执行这些依赖命令所用的执行器类型，且受两条校验约束（无依赖时不应出现该键，出现该键时不得为空）。
- Atomic 0—N Argument：由 `Atomic.input_arguments` 字典声明；键与命令中的 `#{...}` 占位符必须双向覆盖。
- Atomic N—N Platform：由 `Atomic.supported_platforms` 列表声明。
- Technique → 外部 ATT&CK 技术：`attack_technique` 是指向 MITRE ATT&CK 的技术编号引用；技术目录名与 YAML 文件名也复用该编号。
- 同一内容的多种表示：手写 YAML 文件、自动生成的 Markdown 文件、自动生成的 `atomics/Indexes` 清单。
- 测试与外部制品：`src` 目录（源码依赖）、`bin` 目录（二进制依赖）、`ExternalPayloads` 目录（下载的外部载荷）、Terraform 文件。

关于攻击侧对象与防御侧（检测侧、数据侧）对象的关系，这是本资料最需要注意的地方：资料中的对象全部属于攻击/测试侧，没有出现任何缓解措施、数据源、检测规则、事件类等防御侧对象，也没有出现 `mitigates`、`detects` 之类的关系名，因此两者之间既没有直接关联，也没有通过中间对象关联。整个库对外部世界的唯一锚点是 `attack_technique` 这个 MITRE ATT&CK 技术编号。

原文中的例子：技术条目 `attack_technique: T1003.001`、`display_name: 'OS Credential Dumping: LSASS Memory'` 之下并列了三个测试，分别以 Procdump、comsvcs.dll、直接系统调用与 API unhooking 三种方式转储 LSASS 内存，每个测试各有一个 `auto_generated_guid`。这体现了"同一技术编号下多个实现变体"的组织方式。

## 5. 抽象层次的选择

一个 Atomic 描述的是具体可执行的实现，而不是目的或纯行为描述：`CommandExecutor.command` 是完整命令行（例如 `"#{procdump_exe}" -accepteula -ma lsass.exe #{output_file}`），`cleanup_command` 是清理命令，`ManualExecutor.steps` 是至少 10 个字符的手工步骤文本。同一技术下允许存在多个测试，代表同一攻击目的的不同实现方式，因此"变体"表现为同一 `attack_technique` 下的不同 Atomic，而不是新的技术条目。

关于"新条目、变体还是不收录"的判定，资料没有给出完整规则，只能从贡献指南归纳出可验证的准入要求：

- 技术目录以 ATT&CK 技术命名，不存在就新建（"If no such directory exists, create one."），这暗示新技术对应新目录/新 Technique 条目，同一技术内的新实现对应新 Atomic。
- `Technique.atomic_tests` 至少一个测试；`Atomic` 的 `name`、`description`、`supported_platforms`、`executor` 必填。
- 必须能通过 YAML schema 校验与 GitHub Actions 检查，并由维护者人工审阅；通过检查的标志是 "All checks have passed"。
- 测试描述要写明测试做什么、预期输出是什么，并尽量附上详细描述该攻击的网页链接。
- 测试要尽量可移植，例如用环境变量代替硬编码路径，Linux 测试优先用 `sh` 而不是 `bash`。
- 输出文件名要包含技术编号；测试名要能让用户大致了解测试做什么。
- 清理命令要能被反复执行而不产生错误，并且不得删除依赖。

明确的"不收录"规则只找到依赖相关的一条：不要提交有自己外部 GitHub 仓库的依赖，而应通过 `prereq_commands` YAML 键从原始来源下载到 `ExternalPayloads` 目录；引用外部仓库要用永久链接；如果依赖是操作系统自带的，不要写检查或安装它的命令。

框架自身不定义技术分类——技术来自外部 MITRE ATT&CK，框架只定义"技术 → 测试"这一层。资料未说明判断某个测试应当归入技术还是子技术的规则。

## 6. 稳定部分与易变部分

预期不断增长的部分：`atomic_tests` 条目（README 徽章显示 `Atomics-1878`，即约 1878 个原子测试）、各技术目录下的 YAML 测试文件、由其生成的 Markdown 文档、`atomics/Indexes` 中的测试清单，以及云端测试的 Terraform 源码文件。对应的扩展流程是：提交 issue（bug 报告，包括失效的原子测试、新功能请求、更新或变更请求）→ 打开 pull request → 通过检查 → 维护者人工审阅并合并。首次贡献者合并后可领取 T 恤，这是社区侧的激励设计。

希望保持稳定的部分：数据模型与字段。`models.py` 用 `StrictModel` 且设置 `extra="forbid"`，提交的 YAML 若含未知字段会被拒绝；字段取值被收敛到封闭枚举 `Platform` 与 `ExecutorType`；编号格式固定为 `T\d{4}(?:\.\d{3})?`、`技术编号-序号` 与 UUID；`auto_generated_guid` 由 CI 生成而不是人工分配；Markdown 与 `atomics/Indexes` 等生成物不手工修改。README 中的两个 GitHub Actions 徽章分别指向 `validate-atomics.yml` 和 `generate-docs.yml`，且都带 `branch=master`，说明校验与文档生成是持续运行在 master 分支上的固定机制。

新增与废弃的流程：新增走 issue 与 PR；失效的原子测试以 "Bug reports, including broken atomic tests" 的形式进入 issue 列表，另有 "Requests for updates or changes"。资料未说明正式的废弃、下架、弃用标记或版本号管理流程，也没有出现版本号字段。资料中唯一与"防意外变化"直接相关的机制，是要求外部依赖使用 permanent GitHub links。

## 7. 内容与执行的分离

知识内容以数据文件形式存放：每个技术目录下有一个 YAML 测试文件（如 `atomics/T1055/T1055.yaml`），可带 `src`（源码依赖）与 `bin`（二进制依赖）目录；外部载荷不提交进仓库，而由 `prereq_command` / `get_prereq_command` 下载到 `ExternalPayloads`；云端测试的 Terraform `.tf` 文件与 `terraform.tfvars` 放在 `src/T<测试编号>/` 下。贡献者写测试时可以手工编写，也可以使用 atomic GUI 网页界面；手工编写时以 atomic test YAML specification file 为模板，并可选地用 YAML schema 校验文件。

解释与执行的职责在库之外：README 说明测试可以直接从命令行执行、无需安装，但追求更稳固体验时应使用 Invoke-Atomic 之类的执行框架。贡献指南进一步说明 Invoke-AtomicRedTeam 能识别 Terraform 文件以执行这种新型原子测试：执行前置条件时运行 `terraform init` 和 `terraform apply -auto-approve`，清理时运行 `terraform destroy -auto-approve`。云端原子测试共有三种写法：直接用云厂商 CLI、Terraform 加云 CLI、以及使用第三方工具（例如 DataDog 的 Stratus Red Team）。CI 侧由 GitHub Actions 负责校验（`validate-atomics.yml`）与生成文档（`generate-docs.yml`）。

内容能表达的逻辑上限：执行体是字符串命令，支持 `#{...}` 占位符替换；条件判断由命令自身承担，依赖是否就绪用退出码表达（示例为 `if (Test-Path "#{procdump_exe}") {exit 0} else {exit 1}`）；更复杂的场景改为调用外部工具（Terraform、云 CLI、第三方工具）。超出字符串命令表达能力时框架的官方处理方式，资料未说明，资料只展示了"委托给外部工具与执行器"的三种写法。

## 8. 覆盖与成熟度的表达

覆盖（coverage）：资料未说明任何覆盖矩阵、覆盖率分级或状态字段，YAML 结构与数据模型中都没有这类字段。资料中与"覆盖"沾边的可见表达只有三样：到 MITRE ATT&CK 技术编号的映射（`attack_technique`）、README 里 `Atomics-1878` 的计数徽章、以及自动生成的 `atomics/Indexes` 测试清单。因此无法从资料得知"某个技术有没有被覆盖、覆盖得多好"。

成熟度（maturity）：资料未说明任何成熟度字段、等级或依据字段。测试描述被要求写明预期输出、并尽量附上攻击详情链接，但这属于文档撰写要求，不是成熟度评分或证据字段。

资料中实际存在的质量机制是：YAML schema 校验、GitHub Actions 检查（"All checks have passed"）、项目维护者的人工审阅与合并、以及模型层的一组强校验规则（额外字段禁止、必填字段最小长度、`#{...}` 与 `input_arguments` 双向匹配、`sudo` 与 `elevation_required` 一致性、`dependency_executor_name` 的空值与无依赖场景）。这些是准入与合规检查，不是分级，也不是覆盖度度量。

## 9. 对我们的启发

分析：Atomic Red Team 用外部稳定分类法的编号做外键（`attack_technique` 形如 `T1003.001`），把"具体实现"挂在"稳定编号"下面，而不是让每个实现自己充当索引坐标系；这对应我们库的 knowledge_base 层。我们可以把攻击面/防御目标抽成自己的稳定编号（例如由"运行时位置 × 威胁模型"组合而成），让 methods 层的每篇论文插件声明它命中哪个编号，而不是让论文标题充当唯一索引。这一点是改造使用而非直接照搬，因为我们没有 ATT&CK 这样现成的外部标准可引用，必须先把骨架定义出来。

分析：该框架把条目写成声明式清单，并用 pydantic 模型强制字段与取值（`StrictModel` 开启 `extra="forbid"`，`Atomic` 的 `name`、`description`、`supported_platforms`、`executor` 必填，`input_arguments` 的键要求长度不小于 2 且匹配 `^[\w_-]+$`）；这可以直接用于 methods 层。每个方法插件应带一个严格 schema 的 manifest，声明它使用的运行时位置、算子、超参、威胁模型与适用场景，未知字段一律报错，从源头阻止插件私自扩展协议。

分析：`#{...}` 占位符与 `input_arguments` 之间的双向校验（声明但未用到报 `unused_input_argument`，用到但未声明报 `missing_input_argument`）本质上是一种"声明—使用一致性"检查，可以直接迁移到我们的 runtime 层与 operators 层：注册表校验"方法声明的运行时位置与算子集合"恰好等于"它实际调用的集合"，这样文档、清单与代码不会随时间漂移。

分析："内容与执行分离"（YAML 描述测试，执行交给 Invoke-Atomic 这类外部执行框架）可以直接对应我们的 methods 层与 runtime 层分工：方法插件只声明"在哪个位置、对什么对象、施加什么算子、用什么超参"，训练循环与数值计算由 runtime 与 operators 完成。这样新增一篇论文的方法不需要改动训练框架，也不会把训练循环复制进每个插件。

分析：自动生成物不手改（Markdown 测试文件与 `atomics/Indexes` 由 GitHub Actions 生成）可以用于我们的 evaluation 层与 knowledge_base 层：覆盖矩阵、方法索引与文档都应由插件注册表自动派生。手工维护的索引一旦论文数量增长就必然过期，这正是我们当前"说不清覆盖了什么"的一部分原因。

分析：同一技术下允许并列多个测试（`T1003.001` 下 Procdump、comsvcs.dll、直接系统调用三种实现）说明它把"目标"与"实现变体"分开；这可以直接启发 methods 层的重组。我们可以按防御目标对方法分组，让同一目标下容纳多篇论文的方法实现并相互比较，而不是一篇论文一个互不相干的插件；这需要 knowledge_base 提供目标编号、methods 提供实现、evaluation 提供对照结论。

分析：依赖与清理的设计（清理命令要能反复执行且不删除依赖、依赖不提交进仓库而由 `prereq_command` 下载、操作系统自带依赖不写安装命令）可以改造后用于 evaluation 层与 records 层：防御的施加与撤除必须幂等（例如 LoRA adapter 的挂载与卸载、随机种子的复位），评测清理不得破坏共享的基座模型、数据集与算子缓存，外部权重与数据应按固定链接从原始来源获取而不是拷进仓库。

分析：可移植性要求（用环境变量代替硬编码路径、Linux 上优先 `sh` 而不是 `bash`）可以对应到 runtime 层：方法应声明抽象的环境需求（设备类型、精度、基座模型标识、并行方式），由 runtime 解析为具体路径与配置，而不是把集群路径写死在插件里。这属于改造使用，因为我们的"运行环境"是设备与张量，而不是操作系统与 shell。

分析：身份与溯源的做法（`auto_generated_guid` 由 CI 自动生成、外部引用使用 permanent GitHub links 以防意外变化）可以直接用于 records 层：为每个方法与每次评测运行分配不可变 ID，并把论文与上游代码钉到具体 commit，避免"同一个方法名对应不同实现、同一实验无法复现"。

分析：平台与执行器采用封闭枚举（`Platform` 13 个取值、`ExecutorType` 5 个取值）而不是自由文本，便于校验与横向统计；这可以改造后用于 knowledge_base 层：把基座模型族、并行策略、微调方式、威胁模型等维度也定义成封闭枚举，否则每篇论文自造标签，最终无法聚合成覆盖矩阵。

分析：不能照搬的是它把"执行单元"定义为命令字符串、把"条件"定义为退出码（`prereq_command` 用 `exit 0`/`exit 1` 判定依赖是否就绪）。我们的 operators 层处理的是数值算法，需要张量形状、数据类型与精度、数值稳定性、确定性（随机种子）等契约，字符串替换与退出码表达不了这些语义；若照搬这套执行模型，会丢掉我们最需要的正确性保证。

分析：同样不能照搬的是它的关联模型。本资料中只有攻击/测试侧对象，没有任何缓解措施、数据源、检测规则之类的防御侧对象，攻防之间不存在直接关系，唯一锚点是外部的 ATT&CK 技术编号。我们的库恰好相反，方法的产出是防御效果，因此 methods 层与 knowledge_base 层必须自己定义"防御目标—方法—运行时位置—算子—评测结果"的本体，不能指望借用它的关系设计。

分析：它表达覆盖的方式（技术编号映射加 `Atomics-1878` 计数徽章，再加自动生成的索引清单，没有覆盖矩阵，也没有成熟度字段）不能用来回答"我们到底覆盖了什么、覆盖得多好"。我们的 evaluation 层应显式建立矩阵：行是 11 个运行时位置与威胁模型，列是方法与算子，格子里放评测结论与证据；这一条是明确不要照搬其做法的地方。

## 10. 框架自己承认的局限

资料没有独立的"局限"章节，以下是原文明确写到的能力边界与常见问题。

执行能力有限：README 虽然说明可以直接从命令行执行测试，但同时把更稳固的测试体验指向外部执行框架（"For a more robust testing experience, consider using an execution framework like Invoke-Atomic"）。

测试会失效：贡献指南把 "Bug reports, including broken atomic tests"（包括失效的原子测试在内的 bug 报告）列为 issue 类型之一，说明测试损坏是被预期的常见状态。

常见的运行失败与误用（写在测试描述与贡献指南里）：一是依赖未就绪导致报错，测试描述中记录了 "procdump.exe is not recognized as an internal or external command" 与 "The system cannot find the path specified." 两类信息，并提示用 `get-prereq_commands` 先下载安装；二是清理命令删除依赖被明确禁止（"Don't write cleanup commands that delete dependencies"）；三是清理命令必须能被反复执行而不报错，指南为此给出了把错误输出重定向到 `null`、以及使用 `-ErrorAction Ignore` 的写法，说明默认写法容易报错。

贡献者的常见错误由校验器兜底：`sudo` 与 `elevation_required` 不一致、`input_arguments` 为空或存在未使用/缺失的键、`dependency_executor_name` 为空值或在没有依赖时出现。这些错误信息的存在本身说明它们是反复发生的误用。

可复现性依赖外部来源：第三方依赖不提交进仓库，而是靠前置命令从原始来源下载；指南要求使用永久链接来 "prevent unexpected changes"，说明外部来源发生变化是已知风险。此外，清理命令的幂等要求与"不得删除依赖"的禁令也表明破坏性清理是已知风险。

资料未说明的部分：正式的局限清单、成熟度评估方法、覆盖度衡量方式、废弃或下架流程，以及版本号管理。

## 11. 原文依据

1. 支撑第 1 节（框架定位、服务对象、目标）与第 4 节（映射到 ATT&CK）：
> Atomic Red Team™ is a library of tests mapped to the MITRE ATT&CK® framework. Security teams can use Atomic Red Team to quickly, portably, and reproducibly test their environments.

2. 支撑第 2 节（`Technique` 的字段、必填性与最小长度约束）：
```python
class Technique(StrictModel):
    attack_technique: AttackTechniqueID
    display_name: str = Field(..., min_length=5)
    atomic_tests: List[Atomic] = Field(min_length=1)
```

3. 支撑第 2 节（`Atomic` 的字段与必填约束）：
```python
class Atomic(StrictModel):
    test_number: Optional[str] = None
    name: constr(min_length=1)
    description: constr(min_length=1)
    supported_platforms: conlist(Platform, min_length=1)
```

4. 支撑第 2 节（字段的跨字段取值约束：`sudo` 与 `elevation_required` 必须一致）：
> 'elevation_required' shouldn't be empty/false. Since `sudo` is used, set `elevation_required` to true`

5. 支撑第 3 节与第 6 节（GUID 身份由 CI 生成，人工不参与编号）：
> Automated GitHub Actions will generate the `auto_generated_guid` for a new test (in the YAML). You don't need to add this manually.

6. 支撑第 3 节与第 4 节（目录以 ATT&CK 技术命名，同一技术编号是聚合锚点）：
> Select the directory named after the MITRE ATT&CK® technique you want to contribute to. If no such directory exists, create one.

7. 支撑第 5 节与第 7 节（依赖不收录进仓库，改由前置命令从原始来源下载）：
> Don't commit dependencies that have their own external GitHub repositories into this project. Instead, use the `prereq_commands` YAML key to download any dependencies from their original sources

8. 支撑第 6 节与第 8 节（Markdown 与索引清单是自动生成物，人工不维护）：
> Automated GitHub Actions generate the Markdown test files and the list of tests in `atomics/Indexes`. You never need to update them manually.

9. 支撑第 7 节（内容与执行分离，执行交给外部执行框架）：
> For a more robust testing experience, consider using an execution framework like Invoke-Atomic

10. 支撑第 7 节与第 5 节（外部执行器解释内容，云端测试以 Terraform 实现）：
> Invoke-AtomicRedTeam can programmatically identify these files to execute this new flavor of atomics. When you execute pre-reqs, the code will run `terraform init` and `terraform apply -auto-approve`

```json
{
  "key": "atomic_red_team",
  "framework": "Atomic Red Team™（资料未说明版本号；README 徽章显示 Atomics-1878）",
  "object_types": [
    {"name": "Technique", "role": "attack", "fields": ["attack_technique", "display_name", "atomic_tests"]},
    {"name": "Atomic", "role": "test", "fields": ["test_number", "name", "description", "supported_platforms", "executor", "dependencies", "input_arguments", "dependency_executor_name", "auto_generated_guid"]},
    {"name": "Executor", "role": "test", "fields": ["name", "elevation_required"]},
    {"name": "ManualExecutor", "role": "test", "fields": ["name", "steps"]},
    {"name": "CommandExecutor", "role": "test", "fields": ["name", "command", "cleanup_command"]},
    {"name": "Dependency", "role": "test", "fields": ["description", "prereq_command", "get_prereq_command"]},
    {"name": "Argument", "role": "other", "fields": ["description", "type", "default"]},
    {"name": "Platform", "role": "other", "fields": ["（封闭枚举，无字段）windows|macos|linux|office-365|azure-ad|google-workspace|saas|iaas|containers|iaas:gcp|iaas:azure|iaas:aws|esxi"]},
    {"name": "TechniqueDirectory", "role": "artifact", "fields": ["yaml_test_file", "markdown_test_file(自动生成)", "src_dir(可选)", "bin_dir(可选)"]},
    {"name": "Indexes", "role": "artifact", "fields": ["atomics/Indexes（由 GitHub Actions 生成）"]}
  ],
  "id_scheme": "技术编号 attack_technique 采用 ATT&CK 格式，正则 T\\d{4}(?:\\.\\d{3})?，min_length=5（如 T1055、T1003.001）；测试编号 test_number 由 Technique.model_post_init 生成为 f\"{attack_technique}-{index + 1}\"（如 T1562.008-1）；每个 Atomic 另有 auto_generated_guid（UUID，由 GitHub Actions 生成）；目录与文件名复用技术编号（atomics/T1055/T1055.yaml、T1562.008/src/T1562.008-1/）。",
  "attack_defense_link": "via_technique_id",
  "link_detail": "资料中的对象全部属于攻击/测试侧：Technique 通过 attack_technique 指向外部的 MITRE ATT&CK 技术编号，Atomic 通过 atomic_tests 挂在 Technique 下。资料中没有出现任何缓解措施、数据源、检测规则等防御侧对象，也没有 mitigates/detects 之类的关系名，因此攻防之间不存在直接关联或中间对象关联，唯一锚点是外部的 technique ID；技术目录名与 YAML 文件名也复用该编号。",
  "abstraction_level": "Atomic 是具体可执行的实现（command/cleanup_command 或至少 10 字符的 manual steps），同一 Technique 下可并列多个实现变体（T1003.001 下有 Procdump、comsvcs.dll、直接系统调用三种 LSASS 转储）；技术分类本身来自外部 ATT&CK，框架只定义“技术→测试”这一层，资料未说明“新条目 vs 新变体”的完整判定规则。",
  "stable_parts": ["YAML 数据模型与字段（models.py 的 StrictModel，extra=\"forbid\"）", "字段取值枚举（Platform、ExecutorType、InputArgType）", "编号格式（T\\d{4}(?:\\.\\d{3})?、技术编号-序号、UUID）", "auto_generated_guid 由 CI 生成、不人工分配", "Markdown 测试文件与 atomics/Indexes 等自动生成物不手改", "GitHub Actions 校验与文档生成工作流（validate-atomics.yml、generate-docs.yml）"],
  "growing_parts": ["atomics 下的 atomic_tests 条目（README 徽章 Atomics-1878）", "各技术目录中的 YAML 测试文件", "atomics/Indexes 中的测试清单与 Markdown 文档", "可选 src/bin 依赖目录与 ExternalPayloads 外部载荷", "云端测试的 Terraform 文件（如 T1562.008/src/T1562.008-1/）"],
  "content_format": "每个技术目录一个 YAML 测试文件（atomics/T<technique>/T<technique>.yaml），可选 src（源码依赖）与 bin（二进制依赖）目录；外部载荷不提交，由 prereq_command/get_prereq_command 下载到 ExternalPayloads；云端测试另有 Terraform .tf 与 terraform.tfvars，放在 src/T<测试编号>/ 下；Markdown 与 Indexes 为自动生成物。",
  "execution_engine": "执行不在本库内：README 建议使用 Invoke-Atomic 这类执行框架，另有 atomic GUI 网页界面可用于编写测试；Invoke-AtomicRedTeam 可识别 Terraform 文件并执行 terraform init 与 terraform apply -auto-approve，清理时执行 terraform destroy -auto-approve；CI 侧由 validate-atomics 与 generate-docs 两个 GitHub Actions 工作流负责校验与生成。",
  "coverage_expression": "资料未说明覆盖矩阵、覆盖率分级或状态字段；与覆盖相关的可见表达只有到 MITRE ATT&CK 技术编号的映射（attack_technique）、README 的 Atomics-1878 计数徽章，以及自动生成的 atomics/Indexes 测试清单。",
  "maturity_expression": "资料未说明成熟度字段、等级或依据字段；存在的只是质量门：YAML schema 校验、GitHub Actions 检查（All checks have passed）、项目维护者人工审阅与合并，以及模型层的必填与跨字段校验。",
  "lessons": [
    {"idea": "用外部稳定分类编号做外键，让具体实现挂在分类骨架下而不是自己充当索引", "applies_to": "knowledge_base", "transfer": "adapted", "why": "Technique.attack_technique 用 T1003.001 这类编号做外键；我们没有现成外部标准，需要先自建“运行时位置×威胁模型”的稳定编号，再让方法插件声明命中哪个编号。"},
    {"idea": "声明式清单 + 严格 schema（extra=\"forbid\"、必填与最小长度、封闭枚举）", "applies_to": "methods", "transfer": "direct", "why": "YAML 加 models.py 禁止额外字段并逐字段校验；方法插件可用同样严格的 manifest 声明所用运行时位置、算子、超参、适用场景与威胁模型，防止插件私自扩展协议。"},
    {"idea": "声明与使用的双向一致性校验（#{key} 与 input_arguments 必须互相覆盖）", "applies_to": "runtime", "transfer": "direct", "why": "unused_input_argument 与 missing_input_argument 分别对应“声明未用”和“用未声明”；库中可校验方法声明的运行时位置与算子集合恰好等于实际调用集合，防止清单与代码漂移。"},
    {"idea": "内容与执行分离，内容交给外部执行器解释", "applies_to": "methods", "transfer": "direct", "why": "README 建议用 Invoke-Atomic 这类执行框架运行测试；方法插件只声明行为，训练循环与数值计算由 runtime 与 operators 承担，新增论文方法无需改动训练框架。"},
    {"idea": "自动生成物不手改（Markdown 与 atomics/Indexes 由 CI 生成）", "applies_to": "evaluation", "transfer": "direct", "why": "手工维护的索引随条目增长必然过期；覆盖矩阵、方法索引与文档应由插件注册表自动派生。"},
    {"idea": "同一目标下允许并列多个实现变体", "applies_to": "methods", "transfer": "direct", "why": "T1003.001 下并列三种 LSASS 转储实现；方法层可按防御目标分组，让同一目标下的多篇论文方法并存并相互比较，而不是一篇论文一个孤立插件。"},
    {"idea": "前置条件与清理的幂等、且不破坏共享依赖", "applies_to": "evaluation", "transfer": "adapted", "why": "cleanup 要求可反复执行且不得删除依赖；评测中防御的施加与撤除（如挂载/卸载 adapter、复位随机种子）也必须幂等，且不得破坏共享基座、数据集与算子缓存。"},
    {"idea": "可移植性约束（环境变量代替硬编码路径、优先 sh 而非 bash）", "applies_to": "runtime", "transfer": "adapted", "why": "方法应声明抽象环境需求（设备、精度、基座模型标识、并行方式），由 runtime 解析为具体路径与配置，而不是把集群路径写死在插件里。"},
    {"idea": "CI 生成稳定 GUID + 外部引用使用永久链接", "applies_to": "records", "transfer": "direct", "why": "auto_generated_guid 由 GitHub Actions 生成、外部依赖用永久链接防止意外变化；记录层应为每个方法与评测运行分配不可变 ID，并把论文与上游代码钉到具体 commit。"},
    {"idea": "以命令字符串为执行单元、以退出码为条件判断", "applies_to": "operators", "transfer": "not_transferable", "why": "原子测试的执行体是 shell/PowerShell 命令，依赖用 exit 0/exit 1 判定；防御是数值算法，需要张量形状、精度、数值稳定性与可复现性契约，字符串与退出码表达不了。"},
    {"idea": "只定义攻击/测试侧对象，攻防通过外部技术编号弱关联", "applies_to": "knowledge_base", "transfer": "not_transferable", "why": "本资料没有缓解、数据源、检测规则等防御对象，也没有攻防关系名；我们的方法层必须自建“防御目标—方法—运行时位置—算子—评测结果”的本体。"},
    {"idea": "用技术编号映射加计数徽章表达覆盖", "applies_to": "evaluation", "transfer": "not_transferable", "why": "资料没有覆盖矩阵与成熟度字段，无法回答“覆盖了什么、覆盖多好”；我们应显式建立 11 个运行时位置×威胁模型×方法的矩阵，并在格子里附评测证据。"}
  ],
  "limits": [
    "README 把更稳固的测试体验指向外部执行框架（Invoke-Atomic 等），说明稳固执行不是本库自身解决的问题。",
    "贡献指南把“broken atomic tests”（失效的原子测试）列为常见 issue 类型，测试失效是被预期的状态。",
    "测试描述中记录了常见运行失败：procdump 未被识别、系统找不到指定路径，需借助 get-prereq_commands 先下载依赖。",
    "清理命令有明确的已知风险指引：不得删除依赖，且必须能被反复执行而不产生错误（需重定向错误输出或使用 -ErrorAction Ignore）。",
    "校验器针对的贡献者常见错误：elevation_required 与 sudo 不一致、input_arguments 为空或键未使用/缺失、dependency_executor_name 为空或在没有依赖时出现。",
    "第三方依赖不提交进仓库，可复现性依赖外部来源；指南用 permanent GitHub links 来缓解“意外变化”风险。",
    "资料未说明：正式的局限清单、成熟度评估方法、覆盖度衡量方式、废弃流程与版本号管理。"
  ],
  "quotes": [
    {"supports": "第 1 节：框架定位为映射到 MITRE ATT&CK 的测试库，服务安全团队，强调快速、可移植、可复现", "text": "Atomic Red Team™ is a library of tests mapped to the MITRE ATT&CK® framework. Security teams can use Atomic Red Team to quickly, portably, and reproducibly test their environments."},
    {"supports": "第 2 节：Technique 的字段构成、必填性与最小长度约束", "text": "class Technique(StrictModel):\n    attack_technique: AttackTechniqueID\n    display_name: str = Field(..., min_length=5)\n    atomic_tests: List[Atomic] = Field(min_length=1)"},
    {"supports": "第 2 节：Atomic 的字段构成与必填约束", "text": "class Atomic(StrictModel):\n    test_number: Optional[str] = None\n    name: constr(min_length=1)\n    description: constr(min_length=1)\n    supported_platforms: conlist(Platform, min_length=1)"},
    {"supports": "第 2 节：字段的跨字段取值约束，使用 sudo 时 elevation_required 必须为真", "text": "'elevation_required' shouldn't be empty/false. Since `sudo` is used, set `elevation_required` to true`"},
    {"supports": "第 3 节与第 6 节：GUID 由自动化生成，贡献者不需要手工编号", "text": "Automated GitHub Actions will generate the `auto_generated_guid` for a new test (in the YAML). You don't need to add this manually."},
    {"supports": "第 3 节与第 4 节：目录以 ATT&CK 技术命名，技术编号是内容聚合的锚点", "text": "Select the directory named after the MITRE ATT&CK® technique you want to contribute to. If no such directory exists, create one."},
    {"supports": "第 5 节与第 7 节：有独立仓库的依赖不收录进项目，改由前置命令从原始来源下载", "text": "Don't commit dependencies that have their own external GitHub repositories into this project. Instead, use the `prereq_commands` YAML key to download any dependencies from their original sources"},
    {"supports": "第 6 节与第 8 节：Markdown 与 atomics/Indexes 清单是自动生成物，人工不维护", "text": "Automated GitHub Actions generate the Markdown test files and the list of tests in `atomics/Indexes`. You never need to update them manually."},
    {"supports": "第 7 节：内容与执行分离，稳固执行交给外部执行框架", "text": "For a more robust testing experience, consider using an execution framework like Invoke-Atomic"},
    {"supports": "第 7 节与第 5 节：外部执行器解释内容，云端测试以 Terraform 实现并由框架驱动执行", "text": "Invoke-AtomicRedTeam can programmatically identify these files to execute this new flavor of atomics. When you execute pre-reqs, the code will run `terraform init` and `terraform apply -auto-approve`"}
  ]
}
```
