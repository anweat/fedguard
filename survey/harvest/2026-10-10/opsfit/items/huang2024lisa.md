## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：能。全部 7 步都能落在现有 catalog + vocabulary 上：没有任何一步需要新的通用算子（无 `missing_op`），也没有一步被运行时挡住（无 `needs_runtime`）。** 关键原因是 Lisa 的核心机制「近端项」恰好逐字落在 catalog 已有的 states 代数上，而它的作用位置恰好是 vocabulary 已声明的 `transform_gradients`。

逐步判断的依据（详见文末 JSON）：

| n | 步骤 | 归类 | 依据 |
|---|---|---|---|
| 1 | 前置对齐 SFT | outside | 标准的独立监督微调；catalog 里根本没有训练循环/优化器算子，按规则属「普通的本地训练/离线训练一个独立模型」 |
| 2 | 初始化近端参考 w_t | runtime_data | 当前权重就是客户端手上的 LoRA 状态（`received/factors/module`、`local_update/factors/module`、`trace/factors/step`） |
| 3 | 对齐状态近端梯度步 | runtime_action | 改的是步内梯度 → `transform_gradients`（`gradients.modified_by` 明确包含它）；所需的 w 由 `gradients/parameter_value/parameter` 在更新前读到 |
| 4 | 写切换检查点 w̃_{t+1} | runtime_data | `trace/factors/step`（训练步后的 LoRA 因子）就是它；留作中心只是再持有一个 State |
| 5 | 微调状态近端梯度步 | runtime_action | 与步骤 3 同构，只换近端中心与数据 |
| 6 | 跨状态交替 T 个 cycle | compose | 纯控制流（for 循环 + 两个中心变量），不需要任何算子 |
| 7 | 返回最终迭代 | outside | 无后处理的模型交付/本地训练产物 |

四个要点：

1. **近端项就是 `states.delta` + `states.add`。** 论文的 `grad f(w;x,y) + rho*(w - w_t)` 可以写成 `states.add(grad, states.delta(w, w_t), rho)`：`states.delta(w, w_t)` 给出 w − w_t（逐项，键与形状相同的部分），`states.add(base, d, scale)` 给出 base + scale·d。catalog 里没有名字带 "proximal" 的函数，但这两个函数把公式完整实现了——这正是「不需要新通用算子」的地方。（疑点：这依赖梯度字典与状态字典的键/形状一致；`gradients/batch_gradient/parameter` 与参数值同粒度，若键名不同，也只是几行 dict 逐项加法，仍属 compose 级别。）

2. **作用位置是 vocabulary 声明的动作。** 论文既可以把 rho(w − w_t) 加进损失，也可以加进步内梯度；gradients 的 `modified_by` 里明确有 `transform_gradients`，而 `gradients/parameter_value/parameter`（优化器更新前的参数值）提供了做差所需的 w。因此「步内改梯度」是运行时自认能做的动作，不构成需要改损失函数的 `needs_runtime`。

3. **两个近端中心 = 两个 State 值，不需要新制品。** states 一族全是纯函数（`delta`/`add`/`stack`/`flatten`/`weighted_average`），状态在库里就是值，所以「每个 cycle 开头保留 w_t、K1 步后保留 w̃_{t+1}」是纯记账（`states.add(s, s, scale=0.0)` 都能复制一份）。论文报告的约 3.14GB 额外显存是两份完整权重加优化器状态的预算问题，不是算子缺口。疑点：vocabulary 的 `history` 制品只暴露 `history/features/round`（各轮特征），没有「权重检查点」坐标，若实现要求把两个中心落盘成制品，需要额外约定。

4. **训练循环、优化器、调度都不构成算子缺口。** catalog 里没有任何 SGD/AdamW step 或 SFT 循环，但题面规则已把「普通的本地训练」划入 outside；运行时提供 `model.*` 句柄与批梯度/参数值坐标，说明本地训练循环是既有前提。T 个 cycle 的交替、K1/K2 的不对称只是控制流与超参。

需要说明的方法层面（非表达能力）疑点：论文用 AdamW 却写下 `grad f + rho(w − w_t) = 0` 的平稳点，在自适应优化器下这只是一阶近似；`transform_gradients` 的具体契约（是否允许加入任意逐参数项，而不只是加噪/裁剪/投影）catalog 未写，见第 2 节；另外客户端必须同时持有对齐数据与用户微调数据，而 `samples/*` 坐标不区分数据集来源，这是数据前提。

## 2. 缺的东西里哪些是通用的（别的方法也会用到），哪些是这篇论文特有的

由于没有一步被判为 `missing_op` 或 `needs_runtime`，这里讨论的是「想过要补、但发现已被覆盖或按规则不属于算子库」的东西。

**通用的（其他方法同样会遇到）**

- **训练步/优化器算子**（SGD/AdamW step、SFT 循环）：任何带本地训练的防御（FedProx、SCAFFOLD、FLTrust 等）都需要。题面把它归 outside，所以不算缺口，但 catalog 里确实没有，值得在运行时前提里写清楚「本地训练器由运行时提供」。
- **状态快照/检查点存储**：近端型、正则型方法都要保留历史权重（FedProx 的 w_t、SCAFFOLD 的控制变量、需要回滚/早停的方法）。今天用 State 值就能做，但 vocabulary 没有对应的坐标或制品，跨轮、跨设备持久化时只能靠约定。
- **逐参数任意项的梯度变换契约**：把与当前权重相关的项（近端、梯度对齐、控制变量修正）加进步内梯度是通用需求，vocabulary 只用一个词 `transform_gradients` 覆盖；catalog 里 `update.*` 只有加噪、裁剪、投影、按范数缩放，没有「读取参数值并加回一项」的原语。这不阻塞表达（算术由 `states.delta`/`states.add` 完成），但运行时应明确 `transform_gradients` 允许任意逐参数项。
- **两份完整权重 + 优化器状态的显存开销**：任何双状态/带动量方法都有的通用问题，只是 Lisa 给了具体数字。

**这篇论文特有的**

- **Lazy(i) 的双状态交替与切换检查点**：State 1 的中心是 w_t、State 2 的中心是 w̃_{t+1}，K1=100 与 K2=900 不对称、T 个 cycle——这是 Lisa 自己的调度结构，不是可复用计算单元，因此只能是 compose/控制流，也不该做成 catalog 函数。
- **具体标定与数据安排**：rho=1、lr=1e-5、batch=5、对齐状态喂对齐数据、微调状态喂含比例 p 有害数据的用户数据。
- **部署前提**：同一个客户端既能拿到对齐数据又能拿到用户微调数据（在联邦 LoRA 场景里这是较强的假设，属于运行时数据前提而非算子）。
- **两份额外权重（约 3.14GB）**是 Lisa 双状态实现的具体开销；通用的「需要两个状态」问题在这里表现为一个论文特有的量级。

一句话总结：**Lisa 没有特有的算子缺口；真正缺的都是通用运行时能力（训练步算子、状态检查点制品、`transform_gradients` 的明确契约），而它们要么已被规则划到 outside，要么已被 `states.*` 覆盖，因此不阻塞表达。**

```json
{
  "key": "huang2024lisa",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "前置对齐 SFT 是独立的普通监督微调（论文明确 Lisa 不改这一阶段），catalog 中没有任何训练循环/优化器算子，按规则归入「普通的本地训练/离线训练一个独立模型」。LoRA 合并进基座只是常规权重运算，也不属防御计算。"
    },
    {
      "n": 2,
      "class": "runtime_data",
      "uses": ["received/factors/module", "local_update/factors/module", "trace/factors/step"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "cycle 起点的当前权重就是客户端已有的 LoRA 状态，由这些坐标直接提供；留作近端中心不需要算子（states 一族把状态当值，直接保留引用，或 states.add(s, s, scale=0.0) 复制）。疑点：vocabulary 无「权重检查点」制品，history 只暴露 history/features/round 特征；内存内两份 State 可表达，跨轮落盘持久化需额外约定。"
    },
    {
      "n": 3,
      "class": "runtime_action",
      "uses": ["transform_gradients", "gradients/batch_gradient/parameter", "gradients/parameter_value/parameter", "states.delta", "states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "近端梯度 grad f + rho*(w - w_t) 正好是 states.add(grad, states.delta(w, w_t), rho)，catalog 已有这两个状态代数函数，故无需新算子；改动作用在步内梯度上，对应 vocabulary 的 transform_gradients（gradients 的 modified_by 明确包含它），w 由更新前的参数值坐标读到。K1=100 步 AdamW 循环属普通本地训练。疑点：catalog 无优化器/训练步算子，且 transform_gradients 是否允许加入任意逐参数项未在说明中界定；若它只支持加噪/裁剪/投影原语，则该项需在梯度钩子里用 compose 写，仍不需新算子。另注：AdamW 下论文的 grad f + rho(w-w_t)=0 平稳点只是一阶近似。"
    },
    {
      "n": 4,
      "class": "runtime_data",
      "uses": ["trace/factors/step", "local_update/factors/module"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "w̃_{t+1} 就是本地训练步后的 LoRA 因子，trace/factors/step 直接提供；把它留作 State 2 的近端中心只是再持有一个 State，无需算子。论文的约 3.14GB 额外显存是两份完整权重加优化器状态的资源开销，不是算子缺口。"
    },
    {
      "n": 5,
      "class": "runtime_action",
      "uses": ["transform_gradients", "gradients/batch_gradient/parameter", "gradients/parameter_value/parameter", "states.delta", "states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "与步骤 3 同构，只把近端中心换成 w̃_{t+1}、数据换成含比例 p 有害数据的用户微调集、K2=900；近端项同样由 states.delta + states.add 拼出，动作仍是 transform_gradients。数据前提：客户端需同时持有对齐数据与微调数据，而 samples/* 坐标按样本提供、不区分来源，这属于数据侧假设而非算子缺口。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "交替结构就是控制流：for cycle in range(T) 里依次做步骤 3（以 w_t 为中心）、步骤 4、步骤 5（以 w̃_{t+1} 为中心），再把终点 w_{t+1} 作为下一 cycle 的 w_t；两个近端中心就是两个 State 变量，不需要任何算子。K1/K2 不对称（100/900）与 T 是论文特有的调度标定，不构成可复用计算单元。"
    },
    {
      "n": 7,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "无条件后处理地返回最后一次微调状态的终点权重，属普通本地训练产物/模型交付，不含防御计算。若从数据视角描述，这份权重就是 local_update/factors/module 里的本地 LoRA 因子。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
