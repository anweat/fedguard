下面按「先给整体判断，再区分通用/论文特有」的顺序说明，最后给出逐步分类的 JSON。所有判断只依据 catalog 的函数说明与 vocabulary 的坐标/动作定义，不调用任何工具。

## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：partial（大部分可表达，Shadow-Level 那条支路不可表达）。**

这条流水线的骨架其实是一条很"算子友好"的链：对第一层 LoRA 的 B 差做拼接归一化 → 线性探针打分 → 阈值 → Beta 计数/均值 → 三级安全因子 → 加权聚合 + 门控跳轮。把它拆到 catalog 上逐段对：

| 步 | 归类 | 靠什么覆盖 | 说明 |
|---|---|---|---|
| 1 | outside | （probe.fit_logistic 可拟合，但数据在运行时之外） | 论文自己的阶段名就是 `outside_training` |
| 2 | needs_runtime | outgoing/factors/recipient、transform_broadcast（初始化半边）；影子分支无坐标 | 唯一硬缺口 |
| 3 | op | `states.delta` + trace/factors/step、received/factors/module | 逐键做差 = B_t − B_0 |
| 4 | op | `states.flatten(keys=...)` + `transform.l2_normalize` | 固定顺序拼接 + L2 |
| 5 | op | `probe.apply_logistic` | 内部就是标准化后的 sigmoid |
| 6 | compose | 一行比较 | 无固定阈值判定函数，但无需新算子 |
| 7 | op | `sequential.beta_update(decay=0.95)` | 逐步调用 T 次，状态调用方保存 |
| 8 | op | `sequential.beta_mean` | 说明即 alpha/(alpha+beta) |
| 9 | compose | `torch.sigmoid` + `where` + 断点比较 | 公式细节论文未给，属疑点 |
| 10 | op | `sequential.window_mean` | length 取"已参与轮数"即全历史均值 |
| 11 | compose | 布尔向量求均值 | 数据来源的缺口在第 2 步 |
| 12 | compose | 一次 `pow` | (1−rho)^7 |
| 13 | compose | 字典快照 + 几行 if | 纯跨轮状态维护 |
| 14 | compose | 一行均值 + 比较；不调用 `replace_global` | "跳轮"= 服务器控制流 |
| 15 | op | `states.weighted_average` + 权重算术 | 说明明确是因子空间的 FedAvg |

几个值得强调的判断：

- **数据面够用。** 3–15 步要读的东西都能落到坐标上：`trace/factors/step`（逐步 B_t）、`received/factors/module`（B_0）、`local_update/factors/module`、`uploads/module_delta/client`（服务器侧对上传的最终 ∆W 打分）、`aggregate/weights/client`（名单与权重）、`channel/self_reported/client`（客户端把逐步/影子级的因子报给服务器；这只在 trust.self_client 成立时可用）。**`model.*` 句柄一个都不需要**——探针作用在 LoRA 因子向量上，不做 forward/backward，所以本流水线里没有一步是 `runtime_data`。
- **算法面够用。** states 家族（delta / flatten / unflatten / stack / weighted_average）+ transform.l2_normalize + probe + sequential.* 几乎是把 3、4、5、7、8、10、15 步"点名"覆盖了；剩下的 6、9、11、12、13、14 步是普通算术、比较、取均值和跨轮簿记，不需要新的通用算子。
- **真正的洞只有一个：影子分支。** 词表里的训练轨迹（`trace/scalars/step`、`trace/factors/step`）只有"那一条"本地训练，没有分支维度，也没有"固定学习率、永不聚合、跨轮保留的第二条 LoRA 分支"的状态坐标。也就是说第 2 步建不起来，第 11–12 步的 rho 与 w_i,shadow 随之落空，三级加权只能退化成 step/client 两级。这是把 `expressible` 压到 partial 的唯一阻塞项。
- 另外两个"软疑点"（不阻塞表达）：第 9 步两段 sigmoid 的精确表达式论文没给（只有 k=10 与断点 0.4/0.8/0.9）；三级安全因子 w_step、w_client、w_shadow 如何合成一个 w_i 论文也没说（连乘还是别的）。两者都只是几行算术的差别。
- 第 1 步（离线探针）严格说不是"运行时里做不出来"，而是"这一步本身不属于运行时的防御计算"：带标签的、前 10 轮 50% 恶意的 ∆LoRA 样本集不在任何 coordinate 里，属离线准备；拟合动作本身反而有 `probe.fit_logistic` 可用。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用（别的方法也会用到，值得作为运行时/算子库的能力补上）：**

1. **影子/对照分支的本地训练轨迹**（本流水线唯一阻塞项）。凡是需要"另跑一条训练路径作对照"的方法都会碰到：影子模型、decoy 分支、逐步检测的第二个视角、对照微调。建议的通用形态是给 `trace` 增加分支维度（或新增一支"不参与聚合的本地优化器状态 + 逐步因子轨迹"坐标），而不是加一个只服务本文的算子。
2. **概率 → 权重的分段校准器**（第 9 步）。"把 [0,1] 的分数按断点分段做 sigmoid 映射"是可信度加权类方法反复出现的部件，通用性高于本文的 0.4/0.8/0.9。不过它三行就能拼，所以在本流水线里只算 compose；若要沉淀，宜作为 transform 族的 `piecewise_sigmoid_calibration`（输入 s、k、断点，输出 [0,1] 权重）。
3. **按客户端跨轮累计的信任簿记容器**（第 7、10、13 步）。`sequential.*` 与 `history/features/round` 已覆盖大部分，但"只在参与轮更新、缺席不惩罚、某轮快照后冻结"这套组合逻辑要靠调用方自己维护，是可复用的小工具，不是本文独有。

**这篇论文特有的（不需要新增算子，属超参/特征/数据口径）：**

1. **离线训练集的构造**：只用前 10 轮、50% 恶意设置下的模拟样本，且探针只吃第一层 LoRA 的 B 矩阵差。这是本文特有的数据准备与特征选择（属 outside），拟合动作 `probe.fit_logistic` 反而现成。
2. **全部数值**：tau_cls=0.8、k=10、断点 0.4/0.8/0.9、gamma=0.95、eta=7、R_f=20、tau_skip=0.2、alpha/beta 初值、影子分支学习率——都是普通参数，换个值也还是同一批算子。
3. **三级因子合成方式**（w_step/w_client/w_shadow 怎么并成一个 w_i）与 **rho 的分母**：论文自己没写清，属复现细节问题，不影响可表达性。
4. **"整轮跳过"这种门控策略**：本文特有的服务器控制流，用现成的聚合/写回动作即可，不需要新动作。

```json
{
  "key": "safefedllm2026",
  "steps": [
    {"n": 1, "class": "outside", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "论文自己的阶段名就是 outside_training：在模拟客户端训练产生的带标签 ∆LoRA 上离线拟合线性探针。运行时有 probe.fit_logistic（L2 逻辑回归，返回 weight/bias/mean/scale），特征侧也有 states.flatten + transform.l2_normalize，所以“拟合”这个动作本身能表达；但“前 10 轮、50% 恶意”的带标签样本集不是任何 coordinate，属离线准备数据，探针是被当作冻结常量带进运行时的。整步归 outside。"},
    {"n": 2, "class": "needs_runtime", "uses": ["outgoing/factors/recipient", "transform_broadcast", "received/factors/module"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "两半：①固定一致的 B_0 = 服务器用固定种子初始化并下发，有 outgoing/factors/recipient + transform_broadcast + received/factors/module，下发模型本身属 outside，不需要新东西；②影子 LoRA 分支——固定学习率、永不聚合、每轮有自己的逐步因子轨迹，这是现有运行时没有的：trace/factors/step 与 trace/scalars/step 只描述“那一条”本地训练轨迹，词表里没有分支维度，也没有影子分支跨轮状态的坐标，等于要在客户端多跑一条带独立优化器状态的训练循环。缺的就是这条影子分支的训练能力与它的逐步轨迹坐标。疑点：若把“影子分支”仅理解成再跑一次普通本地训练、其轨迹复用 trace/* 坐标，则这步可退化为 outside；但按受控词表的字面能力，这里做不到。"},
    {"n": 3, "class": "op", "uses": ["states.delta", "trace/factors/step", "received/factors/module"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "B_t − B_0 正是 states.delta(state, base) 的语义（逐键做差，要求键与形状一致）。数据侧 B_t 取 trace/factors/step（训练步后的 LoRA 因子），B_0 取 received/factors/module（或首轮下发值）。“只要第一层、只要 B 矩阵”是键筛选，用 states.flatten/stack 的 keys 参数或普通字典筛选即可，不构成新算子。"},
    {"n": 4, "class": "op", "uses": ["states.flatten", "transform.l2_normalize"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "states.flatten(state, keys) 把各模块因子按给定顺序（或排序）拼成一个向量，恰好对应 fixed concat_order；transform.l2_normalize 给出 x/||x||_2。疑点：transform.l2_normalize 的说明为空，未写清轴向（按行还是整张量归一化）；1-D 输入若按最后一维归一化则正好，若按行则 reshape 一次即可，仍属 op 而非新算子。"},
    {"n": 5, "class": "op", "uses": ["probe.apply_logistic"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "probe.apply_logistic 返回逐行 P(class=1)，即用训练时的 mean/scale 标准化后做 sigmoid(w^T x + b)，与 s = sigmoid(a^T x + c) 一致；a、c 就是第 1 步离线产物的 weight/bias。"},
    {"n": 6, "class": "compose", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "固定阈值 tau_cls=0.8 的二值判定，一行逐元素比较 s > 0.8 即可。catalog 没有固定阈值判定函数：robust.largest_gap_threshold 是数据驱动找最大间隔、robust.quantile_threshold 需要良性参考分布，语义都不同，不能顶替；但也不需要新的通用算子。"},
    {"n": 7, "class": "op", "uses": ["sequential.beta_update"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "sequential.beta_update(alpha, beta, suspicious, decay=0.95) 就是带遗忘的 Beta 计数（alpha 记良性、beta 记可疑，decay 对应 gamma）。它是无状态的：本轮 T 个步级判定要循环调用 T 次，alpha/beta 由调用方跨轮保存；初值论文未说明，属超参选择。"},
    {"n": 8, "class": "op", "uses": ["sequential.beta_mean"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "sequential.beta_mean 的说明就是 alpha/(alpha+beta)，与 w_i,step 公式完全一致，输出 [0,1] 的期望信任。"},
    {"n": 9, "class": "compose", "uses": ["probe.apply_logistic", "uploads/module_delta/client"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "输入 s_i^r 是服务器用同一冻结探针对本轮上传的最终 ∆W（uploads/module_delta/client，取第一层 B 差）打出的概率，可复用 probe.apply_logistic；ŵ = 1 − g(s) 的两段 sigmoid 校准 catalog 没有对应函数，但用 torch.sigmoid + torch.where + 断点比较几行就能拼。疑点：论文只给了 k=10 与断点 0.4/0.8/0.9，没有给两段的精确表达式；若把它当成可复用的“分段概率校准器”，可考虑以 transform 族的 piecewise_sigmoid_calibration 收录，本例仍按 compose 计。"},
    {"n": 10, "class": "op", "uses": ["sequential.window_mean"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "按轮记录客户端历次参与的瞬时因子，调用 sequential.window_mean(history, length=len(history)) 即得“截至本轮所有参与轮”的均值（函数对较短历史自动退化为全量）。需要自己维护每个客户端的参与轮列表（history/features/round 或插件状态）。退一步用 torch.mean 一行也成立，所以这是 op/compose 的边界，不影响结论。"},
    {"n": 11, "class": "compose", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "rho 就是影子分支 T 个步级判定中判为恶意的比例 = 布尔向量取均值，普通取均值即可；分母论文未说明（是 T 还是有效步数），属口径/超参问题。真正的缺口在数据来源——影子分支的逐步 ∆B 轨迹（见第 2 步的 needs_runtime），本步自身的计算不需要新算子。"},
    {"n": 12, "class": "compose", "uses": [], "missing_name": "", "missing_family": "", "missing_io": "", "note": "(1−rho)^eta（eta=7）是一次幂运算，配合第 11 步的 rho 即可；catalog 无同名函数，但不需要新的通用算子。"},
    {"n": 13, "class": "compose", "uses": ["history/features/round"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "纯跨轮状态维护：在第 R_f=20 轮把各客户端的 w_i,step 与 w_i,client 快照下来，r > 20 直接复用（shadow 级不冻结）。几行 if/字典拷贝，history/features/round 或插件自身状态都够用，不需要新算子。"},
    {"n": 14, "class": "compose", "uses": ["aggregate/weights/client", "replace_global"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "对被采样集合 S_r 的安全因子求均值（一行均值）再与 tau_skip=0.2 比较；“跳轮”= 本轮不调用 replace_global（或把旧全局原值写回），属服务器控制流层面，不需要新动作。注意 w_i 的三级来源（step/client/shadow）要先合成，合成方式论文未说明。"},
    {"n": 15, "class": "op", "uses": ["states.weighted_average", "uploads/module_delta/client", "aggregate/weights/client", "select_and_weight"], "missing_name": "", "missing_family": "", "missing_io": "", "note": "权重 n_i*w_i / Σ_j(n_j*w_j) 是普通算术（乘 + 归一化），把权重传给 states.weighted_average(states, weights) 即在因子空间做加权平均（说明里明确写了是 factor 空间的 FedAvg），与“按样本数与安全因子加权聚合 LoRA 更新”一致。这是安全加权而非标准 FedAvg，所以不归 outside；服务器侧的选择/加权与写回由 select_and_weight 与 replace_global 承担。"}
  ],
  "expressible": "partial",
  "blocking": ["Shadow-Level 的“影子 LoRA 分支”没有运行时支撑：词表只有一条本地训练轨迹（trace/scalars/step、trace/factors/step），没有分支维度，也没有“固定学习率、不参与聚合的第二条 LoRA 分支”的跨轮状态坐标；因此第 2 步建不起来，第 11–12 步的 rho 与 w_i,shadow 无从计算，三级安全加权聚合只能退化为 step/client 两级。"]
}
```
