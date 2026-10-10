## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：可以完整表达（expressible = full），没有必须新增的通用算子，也没有硬性的运行时缺口。** 这条流水线本质上是"服务器侧、每 T′ 轮一次的一致性检测 + 名单剔除"：检测部分全是降维、质心/半径、比较、加权、取中位数；执行部分只需要服务器对上传件做选择与加权。

逐步映射如下：

| 步骤 | 判断 | 依据 |
|---|---|---|
| 1 初始化 C_tr、f | compose | 集合复制 + 计数器置零，纯防御方自己的状态记账，不需要算子 |
| 2 周期门控 t % T′ == 0 | compose | 取模比较与 `floor(t/T′)`；轮号 t 是运行时固有的调度信息，vocabulary 未单列 coordinate |
| 3 2 维 PCA | **op** | `states.flatten` + `states.stack` 把本轮各客户端上传的因子差拍成 (n_clients, d)，再 `transform.pca(X, k=2)` 取 scores，正是"每个客户端一个 2 维坐标" |
| 4 按客户端缓存 Q_f,i | runtime_data | 读历史靠 `history/features/round`；但该坐标是**轮**粒度，"未选中记 NULL / 按客户端键控"要插件自己补 |
| 5 质心 θ̄ | compose | 对非 NULL 向量做 stack + masked mean，一行 `torch.mean` |
| 6 平均半径 d̄ | compose | `geometry.distance_to(X, 质心)` 得到欧氏距离，再取均值（均值是普通张量运算，故不记为 op） |
| 7 邻域筛选 C_base | compose | 到参照客户端的距离门限 Ω1、足迹差门限 Ω2 → 布尔掩码 + 索引 |
| 8 基线均值 θ^base、d^base | compose | 对 C_base 的两个量各取一次均值 |
| 9 term1 | compose | `‖θ̄_i − θ^base‖` 用 `geometry.distance_to`，再除以标量 d^base |
| 10 term2 | compose | 减法 + 取绝对值 |
| 11 h = λ1·term1 + λ2·term2 | compose | 逐客户端标量加权和（λ1=1，λ2=2） |
| 12 中位数阈值 h_thr = δ·h_med | compose | `torch.median` × δ。库里的 `robust.quantile_threshold`（分位数）和 `robust.largest_gap_threshold`（最大间隙）是**别的规则**，不能顶替"中位数倍数"规则 |
| 13 剔除并更新 C_tr | **runtime_action** | 判定本身平凡，但"执行改动"落在服务器对上传件的选择上：`select_and_weight` 正是 `uploads`/`aggregate` 的 modified_by 动作（tactic: isolate） |
| 14 后续轮次聚合忽略被剔除者 | **runtime_action** | 同样是每轮在 `select_and_weight` 里把这些客户端排除；标准 FedAvg 本身属 outside，但"按信任集合排除"是防御动作 |

**三处"算得出、但要自己担语义"的疑点（不影响可表达性，但影响正确性）：**

1. **逐轮重做 PCA 导致基不一致。** 步骤 3 每轮用"当轮上传的客户端"重新拟合 PCA，2 维子空间、旋转与符号每轮都会变（`transform.pca` 只保证各主成分最大幅值项为正，不保证跨轮可比）。把不同轮次的 2 维坐标塞进同一个 Q_f,i 再取质心和平均半径，几何含义会漂移。若要严格，应改用固定基（`transform.random_projection(X, k=2, seed)`，或对周期内已缓存向量用同一组 components 重投影），这仍是 compose 级改动。
2. **跨轮状态与 <客户端,轮> 粒度。** vocabulary 只给了 `history/features/round`（"此前各轮的特征"）和 `history` 制品（side: both），没有逐客户端、逐轮的坐标。MCD 需要一份按 (f, 客户端) 键控、缺失轮为 NULL 的缓存。若服务器插件可跨轮持有状态（服务器侧存在 `select_and_weight`/`replace_global` 这类动作，暗示可以），用普通字典 + 掩码即可（compose 级）；若不允许，则步骤 4 退化为 needs_runtime。
3. **取哪一路上传坐标。** `uploads/product_delta/client` 是 Gram 形式、不展开的乘积差，无法直接喂给 PCA；必须走 `uploads/factor_delta/client`（或 `module_delta`）再 flatten，PCA 才有显式向量。另外 `transform.pca` 不做标准化，而论文对 standardize 未说明；若先加 `transform.standardize` 仍属 op。

**论文未定死的参数**（是实现假设，不是算子缺失）：δ 只给了区间 (1, 3)，没给具体值；Ω1=4、Ω2=2 的量纲（绝对距离还是相对 d̂_f 的倍数）未说明；"第一个基线客户端"如何确定（顺序第一？随机指定？）未说明；T′=80、λ1=1、λ2=2 有出处。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**严格意义上的 missing_op：没有。** 全流程都能落到 `transform.pca`、`states.flatten/stack`、`geometry.distance_to`、`torch.median` 与逐元素算术上，不需要新的可复用计算单元；也没有 needs_runtime 级别的硬缺口（不需要改损失、逐样本梯度、跨客户端通信或推理时介入）。

**通用性的软缺口（别的方法也会遇到，但本库目前只以"轮"粒度或标量形式提供）：**

- **跨轮、按客户端的特征缓存 + 缺失轮掩码对齐**：任何基于历史一致性、时序异常检测、信誉累积的防御（FLDetector 类、FLAME 的时序部分、CUSUM/Beta 类信任分）都要用。库里有 `sequential.*` 处理**标量**历史，但没有 <客户端,轮> 粒度的坐标或缓存工具。
- **跨轮可比（固定基）的低维嵌入**：凡是"先降维再跨轮比较"的方法都会踩到逐轮 PCA 的基漂移问题；通用做法是固定随机投影或固定基重投影，本库已有 `transform.random_projection` 可顶上。
- **周期调度/轮号读取**：通用但属运行时固有信息，不算缺口。

**这篇论文特有的（属方法规则与参数，不是通用计算单元）：**

- "质心 + 足迹（平均半径）"这对度量及其组合方式（term1/term2 加权）；
- λ1=1、λ2=2 的权重，δ·median 的阈值形式，Ω1/Ω2 的绝对/相对语义；
- 以"第一个可信客户端"作为参照基线、再做邻域扩展成 C_base 的两级基线选取；
- T′=80 的周期门控与"未选中记 NULL"的周期缓存策略。

如果知识库要收录它，合适的形态是"带周期与阈值的服务器侧名单剔除模板"（复用 pca + 距离 + 中位数 + `select_and_weight`），而不是新增算子；阻塞项为空。

```json
{
  "key": "sun2024vaguegan",
  "steps": [
    {
      "n": 1,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "纯记账：C_tr = C、f = 0，就是集合复制加计数器置零，防御方自己的状态，不需要任何算子，也没有对应 coordinate。"
    },
    {
      "n": 2,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "取模比较 t % T' == 0 加 f = floor(t / T')，普通控制流；T'=80。轮号 t 由运行时调度隐式提供，vocabulary 未把它单列成 coordinate，但属运行时固有信息，不构成缺口。"
    },
    {
      "n": 3,
      "class": "op",
      "uses": ["transform.pca", "states.flatten", "states.stack", "uploads/factor_delta/client"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把本轮各客户端上传的因子差 flatten/stack 成 (n_clients, d)，再 transform.pca(X, k=2) 取 scores，正好是每客户端一个 2 维坐标。疑点：pca 不做标准化，论文对 standardize 未说明（需要时先 transform.standardize，仍属 op）；必须用显式向量，uploads/product_delta/client 是 Gram 形式不展开，不能直接做 PCA。"
    },
    {
      "n": 4,
      "class": "runtime_data",
      "uses": ["history/features/round"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "周期内跨轮读取此前各轮的特征，由 history 制品与 history/features/round 提供。疑点：该坐标是“轮”粒度，MCD 要的是 <客户端, 轮> 粒度且未选中轮记 NULL，键控与掩码对齐要插件自己做（普通字典即可，compose 级）；若运行时不允许服务器插件跨轮持有状态，这一步就退化为 needs_runtime。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对 Q_f,i 中非 NULL 的 2 维向量取均值：stack + 掩码后一行 torch.mean，没有专门函数但也不需要新算子。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": ["geometry.distance_to"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "到质心的欧氏距离用 geometry.distance_to（或 cluster.distances 的 euclidean）得到，再对非 NULL 轮取均值；求均值是普通张量运算，故不记为 op。"
    },
    {
      "n": 7,
      "class": "compose",
      "uses": ["geometry.distance_to"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "以第一个基线客户端的 (θ̂, d̂) 为参照：质心距离过 Ω1、足迹差过 Ω2 的客户端入选，即两次比较 + 布尔掩码索引。疑点：Ω1/Ω2 的量纲（绝对距离还是相对 d̂_f 的倍数）论文未说明，“第一基线客户端”如何确定也未说明，实现需假设；但无论哪种假设都只是比较与索引。"
    },
    {
      "n": 8,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对 C_base 的 2 维质心与标量足迹各取一次均值（两行 torch.mean），无专门函数。"
    },
    {
      "n": 9,
      "class": "compose",
      "uses": ["geometry.distance_to"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "term1 = ‖θ̄_i − θ^base‖ / d^base：向量差取范数（geometry.distance_to 到基线点）再除以标量，属普通张量运算。"
    },
    {
      "n": 10,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "term2 = |d^base − d̄_i|，减法加取绝对值，逐客户端标量。"
    },
    {
      "n": 11,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "h_f,i = λ1·term1 + λ2·term2（λ1=1、λ2=2），逐客户端标量加权和，几行逐元素运算。"
    },
    {
      "n": 12,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "h_med = torch.median(H_f)，h_thr = δ · h_med，中位数乘标量即可。注意 robust.quantile_threshold（分位数）与 robust.largest_gap_threshold（最大间隙）是别的阈值规则，不能替代中位数倍数规则；δ 只给了区间 (1,3)，具体值论文未说明。"
    },
    {
      "n": 13,
      "class": "runtime_action",
      "uses": ["select_and_weight"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "判定 h_f,i > h_thr 的客户端，从可信集合与 Q_f 中剔除、后续不采纳其更新（tactic: isolate）。数值判定平凡，真正的“执行改动”是服务器对 uploads 的选择，正是 select_and_weight（uploads/aggregate 的 modified_by 动作）。"
    },
    {
      "n": 14,
      "class": "runtime_action",
      "uses": ["select_and_weight"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "后续每轮聚合都跳过被剔除客户端：在每轮的 select_and_weight 里把它们排除或置零权重。标准 FedAvg 本身属 outside，但“按信任集合排除”是持续生效的防御动作。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
