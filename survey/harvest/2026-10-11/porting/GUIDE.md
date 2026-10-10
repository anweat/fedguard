# 把一篇论文的防御方法移植成 fedguard 插件：给移植者的说明

你要做的事：读一篇防御论文的方法拆解（`<paper>` 里，已经按步骤写好），把它写成 fedguard 的一个或一对插件，
再写一个不需要模型的测试，最后如实报告移植成本。这是一次**成本测量**：我们想知道把别人的方法搬到这个库上要付出多少、
卡在哪里。所以"搬不动、缺什么"和"搬过来了"同样是合格的结果；硬凑出一个看起来完整的实现才是不合格的。

## 1. 这个库是什么

fedguard 挂在现有的联邦微调框架上，面向大模型的 LoRA 微调。训练、聚合、通信都由宿主框架做；库在一轮训练的固定位置上
被调用，插件在那里读经手的数据、提出改动。插件看到的模型更新是 **LoRA 状态字典**（键形如 `<模块>.lora_A.weight`、
`<模块>.lora_B.weight`），不是完整模型权重。服务器一侧默认没有可运行的模型。

`<reference>` 里是库的接口：`core/types.py` 全文（位置、数据类别、动作的定义），以及插件能用到的各个视图和算子的签名与说明。
只能使用 `<reference>` 里出现的接口。不要假设存在没有列出的方法或参数。

很多防御是自成系统的：有自己的协议、自己维护的状态、离线训练的部件。这个库不打算把整套系统搬进来。库要做好的是**提取接口**：
在一轮训练的各个位置把那套系统需要的数据取出来交给它，再把它的决定带回训练。系统自己的状态和部件留在库外，
以 `resources` 的形式接进来。所以移植时最重要的问题是：**这个方法要从训练里取什么、在哪里取、库给不给得出**。
这要逐项写进报告的 `extraction_needs`，即使方法的其余部分搬不过来也要写。

## 2. 一个插件声明什么

```python
class MyMethod(GuardPlugin):
    name, at, version = "my_method", Stage.SERVER_AGGREGATE, "1"      # at 可以是一个位置，也可以是同一侧的几个位置的元组
    needs = frozenset({"uploads"})                                    # 要读的数据类别；没声明的读不到
    resources = frozenset()                                           # 防御方自备的外部资源名（干净数据、探针、参考更新等）
    acts = frozenset({"select_and_weight"})                           # 可能提出的动作；空表示只报告

    def run(self, ctx):                                               # 每个位置调用一次，用 ctx.stage 分支
        ...
        return ctx.findings(scores=..., features=..., evidence=..., decision=..., proposals=..., messages=..., attachments=...)
```

- 位置与该位置能读的数据类别：见 `STAGE_KINDS`。动作与它能出现的位置：见 `ACTION_STAGES`。提出动作的写法：见 `Findings.proposals` 的注释。
- `ctx.state` 是插件私有的字典，跨位置、跨轮保留。随机数只用 `ctx.rng`（numpy Generator），不要动全局随机状态。
- 两侧的配对插件只能经消息通道交换内容：`messages`（小记录）和 `attachments`（张量）。收到的一律是未核实的。
- 训练前需要客户端与服务器往返一次的，用 `CLIENT_ANNOUNCE` 与 `SERVER_EXCHANGE`。
- 训练步之内：`CLIENT_LOSS`（前向之后、反向之前，可读批次与损失、可换损失）、`CLIENT_PRE_STEP`（可读可改梯度）、`CLIENT_STEP`（步后）。
- 需要在模型上做前向或反向的，声明 `model_handle`，只用 `ModelHandle` 协议里的方法。客户端一侧的句柄包着正在训练的模型；
  服务器一侧宿主不提供模型，句柄由防御方自备并传入（可选），需要它的服务器侧插件照常声明 `model_handle`，
  并在类说明里写明"需要防御方在服务器端提供模型"。测试里用 `harness.server_guard(..., probe=StubHandle 的子类)`。
- 论文需要、但防御方必须自己准备的东西（干净根数据、训练好的检测器、参考更新、对齐数据的批次……）一律作为 `resources`，
  在类说明里写清它的形式；不要在插件里编造它。

## 3. 两个完整的例子

服务器侧，Krum（`update_gram` 是 `fedguard.methods.shared` 里的辅助函数，可以导入使用，`update_matrix` 同理）：

```python
{krum}
```

客户端侧、训练步内，Lisa 的近端项：

```python
{lisa}
```

## 4. 规则

1. **不改库。** 只写新文件。库里缺一个位置、一类数据、一种动作、一个算子时，不要绕过去，记在报告的 `missing_runtime` 或 `missing_ops` 里。
   缺的是一个小的通用计算时，可以在插件文件里写成模块级函数，并在报告里记为 `new_helpers`。
2. **优先用已有算子**（`fedguard.ops.*`）。同样的计算已有算子时不要重写。
3. **只移植防御计算本身。** 普通的本地训练、标准聚合、密码学协议、离线训练一个独立的检测器，都不属于插件；
   离线得到的东西作为 `resources` 传入。
4. **论文是集中式或传统联邦（图像、完整模型权重）的，照实处理**：把"模型更新"换成 LoRA 因子空间的更新向量
   （`ctx.uploads.factor_delta(client)`）是允许的，但必须写进"Deviations"。
5. **允许导入的只有**：`math`、`torch`、`numpy`、`fedguard.core.plugin`、`fedguard.core.types`、`fedguard.ops.*`、
   `fedguard.methods.shared`（仅 `update_matrix`、`update_gram`）。测试文件另外可以导入 `pytest` 和 `harness`。
   不读写文件，不访问网络，不调用子进程。
6. **类说明必须用英文，并含这些小节**（没有内容的小节省略）：`Implemented:`、`Deviations:`、`Not implemented:`、
   `Open in the paper and chosen here:`、`Cost:`；用到资源时写一行 ``Resource `名字`: 形式``。
   论文没说清、由你决定的地方必须列在 "Open in the paper and chosen here"。不要写论文里没有的数值。
7. **测试验证的是机制，不是论文数值**：构造一个该方法应当起作用的合成情形（例如 8 个客户端里 1 个更新被放大），
   断言它确实那样动作；再构造一个不该动作的情形。用 `harness` 里的工具（`<harness>` 里是它的全文）。测试必须在几秒内跑完，不加载任何模型。
8. 整个方法在这个库里无法表达时：`verdict` 写 `not_expressible`，插件文件只写一个带类说明的空壳或留空，测试留空，把原因写进报告。

## 5. 输出格式

严格按下面三个代码块输出，块外可以有简短说明。第一个块是插件文件，第二个是测试文件，第三个是报告。

````
```python
# plugin.py
...
```

```python
# test_port.py
import harness
from plugin import ...
...
```

```json
{{
  "key": "{key}",
  "verdict": "full | partial | not_expressible",
  "plugins": [{{"name": "", "class": "", "side": "server|client", "stages": [], "needs": [], "resources": [], "acts": []}}],
  "steps_total": 0,
  "steps_ported": 0,
  "steps_outside": 0,
  "ops_used": ["fedguard.ops.模块.函数"],
  "new_helpers": [{{"name": "", "lines": 0, "generic": true, "what": ""}}],
  "missing_ops": [{{"name": "", "what": ""}}],
  "extraction_needs": [{{"data": "方法要从训练过程里取的一项数据", "where": "在一轮里的什么时刻、哪一侧", "provided": "yes | partly | no", "via": "库里对应的位置与视图方法；no 时写缺什么"}}],
  "external_state": ["这套方法要在库外维护或事先准备的状态与部件（即 resources 背后的东西）"],
  "missing_runtime": [{{"what": "", "blocks": "哪一步因此做不了"}}],
  "deviations": [""],
  "open_choices": [""],
  "needs_from_authors": ["只有拿到原作者代码或数据才能确定的东西，没有则空"],
  "confidence": "high | medium | low",
  "confidence_reason": ""
}}
```
````

`steps_total` 是 `<paper>` 里"算子流水线"的步骤数；`steps_ported` 是你的插件实现了的；`steps_outside` 是按规则 3 不属于插件的。
