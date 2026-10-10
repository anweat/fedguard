下面直接按 catalog / vocabulary 的字面定义逐步核对（未调用任何工具）。

## 1. 这条流水线整体上能否由现有算子库与运行时表达

先说结论：**主体可表达，但只能算 partial**。

支持这一判断的事实：

- 两个 stage 都是 `server_*`，即整条 DeepSight 都在服务器侧跑。因此它不需要客户端训练钩子、不需要逐样本梯度、不需要客户端互相通信，也不需要在推理阶段介入——这排除了最大的一类 `needs_runtime`。
- 服务器侧要看的东西，词表里基本都有对应制品：`uploads/factor_delta|product_delta|module_delta|roster`、`aggregate/result/model`、`outgoing/factors/recipient`、`history/features/round`；"把某个客户端上传加载后看它在探针上的行为"正好是 `uploads/probe_behavior/client`（`via: model_handle`），配合模型句柄的 `model.lora(state)` + `model.activations(samples, select)` 取输出层输出。
- 纯计算的部分能落在现成算子上：成对余弦距离 = `cluster.distances(metric="cosine")`（定义就是 1 − 余弦相似度；`geometry.cosine_matrix` 只给相似度，还得自己取 1−，不如前者贴切）；密度聚类有 `cluster.density_clusters`（catalog 自述是"方法要 HDBSCAN 又不给参数"时的替身）与 `cluster.dbscan`；裁剪有 `update.clip_to_norm(state, base, bound)`，其定义就是 (W−G)·λ+G，且返回 λ；聚合有 `states.weighted_average`（catalog 明说是 factor 空间的 FedAvg）+ `states.norm`。
- 剩下几步（TE 阈值计数、TE 中位数判定、DDif 逐元素除法差、簇共现 0/1 矩阵、5 个距离矩阵平均、簇内可疑比例投票）确实没有单个函数，但都是比较/取索引/求均值/逐元素四则运算，属于 `compose`，不需要新通用算子。
- 末轮"每个客户端收到本簇模型"不是标准 FedAvg 下发，但词表里 `outgoing/factors/recipient` 就是"按接收方不同的下发内容"，动作 `transform_broadcast` 恰好覆盖它，因此可表达。

三处必须打问号的地方：

1. **论文特征建立在"输出层偏置差 Δb + 输出层权重差 Δw 的逐元素值"上，而运行时的上传制品是 LoRA 因子。** `uploads/module_delta/client` 是"指定模块的**因子**差"，偏置不是 LoRA 因子；`uploads/product_delta/client` 又明确写了"不展开，按 Gram 计算"。所以第 1 步的 Δb 是否作为状态条目存在、第 3 步的 |Δw_ij| 能否拿到，取决于运行时状态字典里是否含输出层偏置、以及是否允许把因子相乘展开成 Δw=B@A。这是整条链最脆弱的一环（若输出层未被 LoRA 适配，Δb 恒为 0，第 2/3/4/5 步的特征全部退化）。
2. **HDBSCAN 的语义只能近似。** catalog 没有带 `min_cluster_size` 的层次密度聚类，只有无参 DBSCAN 替身 `cluster.density_clusters` 和需要 eps 的 `cluster.dbscan`。第 8 步里 4 路值型特征可以喂替身；第 2 步产出的"预计算余弦距离矩阵"这一路没有现成入口（`density_clusters` 的形参虽叫 D，文档没写它接受预计算距离矩阵），第 11 步输入本身就是合并距离矩阵，同样存疑。这影响复现保真度，但方法仍能表达（自定 eps 或换替身）。
3. **代价与"最后一轮"的调度**：3 个种子 × 20000 条随机输入 × (N+1) 个模型的前向，运行时能提供入口但极贵；`when: last round only` 属于插件自身的调度逻辑，运行时不需要额外能力。这两点都不是表达性障碍。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用缺口（别的方法也会撞上）：**

- **逐元素读取/展开上传模型的非 LoRA 参数**：偏置、以及"乘积差不展开只给 Gram"的约束。任何要看权重逐元素统计（NEUP 这类按神经元的归一化能量、符号翻转、坐标级异常检测）的方法都会需要"把某模块的参数差逐元素取出来"的能力。这是协议层面的通用能力缺口，不是 DeepSight 独有。
- **带 `min_cluster_size` 的密度聚类（HDBSCAN 语义）**：FLAME、FreqFed、FLDetector 一类服务器端聚类防御都要用，catalog 目前只有 DBSCAN/无参替身，属通用保真度缺口。
- **簇级标签聚合（按簇投票 / 簇内可疑比例）**：把逐模型标签按簇降维成"整簇接受或整簇剔除"，是聚类型防御的公共收尾动作，目前只能 compose。
- **按接收方不同的下发**：运行时已经用 `outgoing/factors/recipient` + `transform_broadcast` 覆盖，属通用能力且已具备。
- **服务器侧对任意上传模型做批量探针前向**：由 `uploads/probe_behavior/client` 通用提供；固定探针集与"每轮重新随机采样"之间的差别是接口细节。

**这篇论文特有的（属于插件里的公式与超参，不必上升为通用算子）：**

- DDif 的具体除法差定义、NEUP 的具体归一化式子、TE 的阈值 `max(0.01, 1/P)`、`TE <= MEDIAN(TE)/2` 的判定规则、`tau = 1/3` 的簇投票门限；
- "5 路特征（1 余弦 + 1 NEUP + 3 DDif）各自聚类后取簇共现距离再平均再聚类"这套集成结构；
- 裁剪阈值取"全部更新 L2 范数的中位数"这一动态 S 的取法（`update.clip_to_norm` 只负责给 S 之后的裁剪）。
- 末轮按簇聚合下发也只是把通用能力用一种特定方式组合。

因此整条流水线的判定是：`0 个 missing_op`、`0 个 needs_runtime`、`1 个 outside`（标准 FedAvg）、`2 个 runtime_data`、`1 个 runtime_action`、其余为 op/compose；但因为第 1、3 步所依赖的"输出层偏置/权重逐元素差"在 LoRA 上传协议下不保证存在，整体只能判为 **partial**。

```json
{
  "key": "rieger2022deepsight",
  "steps": [
    {
      "n": 1,
      "class": "runtime_data",
      "uses": ["uploads/module_delta/client"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "该坐标就是'上传相对下发的指定模块差'，按模块名取出输出层即得 Δb_k。疑点：坐标写的是'因子差'，偏置不是 LoRA 因子；若运行时状态里没有偏置条目（或输出层未被适配），Δb 取不到/恒为 0，本步应改判 needs_runtime。"
    },
    {
      "n": 2,
      "class": "op",
      "uses": ["cluster.distances"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "cluster.distances(metric='cosine') 的定义就是 1 - COSINE，与 d_cos 完全一致。geometry.cosine_matrix 只给相似度矩阵，还得自己取 1-，不如前者直接。"
    },
    {
      "n": 3,
      "class": "compose",
      "uses": ["uploads/module_delta/client"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "NEUP 需要逐元素的 |Δb_i| 与 Σ_j|Δw_ij|（按输出神经元归一化）。若能从 module_delta 拿到该模块因子并相乘展开 Δw=B@A，则 abs+按行求和+逐元素相除几行即可（属 compose）；但 product_delta 坐标明确'不展开、按 Gram 计算'，若因子也不可展开，本步拿不到 Δw 的逐元素值，应改判 needs_runtime。"
    },
    {
      "n": 4,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "阈值 max(0.01, 1/P) 是一行常数；TE 只是逐行比较后求和计数。catalog 里没有计数算子，也不需要新算子。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "torch.median + 逐元素比较（TE <= median/2 记为可疑）即可。robust.coordinate_median 是'逐坐标对行取中位数'，语义不同，不能因为名字含 median 就算 op。"
    },
    {
      "n": 6,
      "class": "runtime_data",
      "uses": ["uploads/probe_behavior/client", "aggregate/result/model"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "uploads/probe_behavior/client 正是'加载某客户端上传后模型在探针上的行为'（内部用 model.lora(state)+model.activations(samples, 输出层)）；全局模型经 aggregate/result/model 加载。随机探针 3×20000×input_dim 由插件用普通随机数生成。代价极高但不是能力缺口。"
    },
    {
      "n": 7,
      "class": "compose",
      "uses": ["uploads/probe_behavior/client"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "同一批随机输入下 local 与 global 输出概率的逐元素除法差（分母加 eps 截断），再对 20000 个样本取均值得到 P 维 DDif，全是普通张量运算。"
    },
    {
      "n": 8,
      "class": "op",
      "uses": ["cluster.density_clusters", "cluster.dbscan"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "NEUP 与 3 份 DDif 是值型特征，直接喂 cluster.density_clusters（catalog 自述为'方法要 HDBSCAN 又不给参数'的替身，且会保留 noise=-1）。疑点：余弦那一路是预计算距离矩阵，density_clusters 的形参虽名为 D 但文档未声明支持预计算矩阵，cluster.dbscan 又必须要 eps（论文未给，只能由数据自定），故'预计算距离 + min_cluster_size'的 HDBSCAN 语义只能近似。"
    },
    {
      "n": 9,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把一维簇标签做 N×N 相等比较再取反成 0/1，纯索引与比较，无对应函数。"
    },
    {
      "n": 10,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "5 个 N×N 矩阵逐元素求平均。states.weighted_average 是给 State 字典（因子）用的，不适用于距离矩阵。"
    },
    {
      "n": 11,
      "class": "compose",
      "uses": ["cluster.dbscan", "cluster.density_clusters"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "输入只有合并距离矩阵，没有坐标/特征值。稳妥做法是 cluster.dbscan + 自行按'尺度×中位 k 近邻距离'定 eps（几行排序取分位数），即复现 density_clusters 的启发式；若确认 density_clusters 接受预计算 D，则可降为 op。此处按'不确定'归 compose。"
    },
    {
      "n": 12,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "按最终簇分组，算簇内可疑标签占比 < tau 则整簇接受，是布尔掩码 + 均值 + 阈值比较。cluster.majority_cluster 是'HDBSCAN 取多数簇'，与按标签投票无关，不能按名字算作 op。"
    },
    {
      "n": 13,
      "class": "op",
      "uses": ["states.norm", "update.clip_to_norm"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "裁剪本身正是 update.clip_to_norm(state, base=G_t, bound=S) 的定义（返回 (G+λ(W-G), λ<=1)）；S=全部更新 L2 范数的中位数用 states.norm 逐客户端取范数 + torch.median 两行即可，仅此一步是普通张量运算。"
    },
    {
      "n": 14,
      "class": "outside",
      "uses": ["states.weighted_average"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "过滤裁剪后的标准等权 FedAvg，属常规聚合而非防御计算，故归 outside；若按算子计，states.weighted_average(weights=None) 在因子空间恰好等价（catalog 自注 'FedAvg in factor space'）。"
    },
    {
      "n": 15,
      "class": "runtime_action",
      "uses": ["transform_broadcast", "outgoing/factors/recipient", "states.weighted_average"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "簇内均值用 states.weighted_average 按簇取子集（几行索引）；'每个客户端收到其所在簇的模型'由 outgoing/factors/recipient 这个按接收方的坐标承载，对应动作是 transform_broadcast。'仅末轮执行'属插件调度，不影响表达性。"
    }
  ],
  "expressible": "partial",
  "blocking": ["论文第 1、3 步（以及依赖它们的第 2、4、5 步）建立在输出层偏置差 Δb 与输出层权重差 Δw 的逐元素值上；运行时上传制品只定义 LoRA 因子差与'不展开、按 Gram 计算'的乘积差，偏置不是 LoRA 因子。若运行时状态中没有输出层偏置条目、且乘积差不能展开成逐元素 Δw，则 NEUP/TE 特征无法取到，方法整体只能部分表达。"]
}
```
