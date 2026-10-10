## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：可以，属于 `full`。** FreqFed 的八个步骤逐步都能落在 catalog 的现成函数或 vocabulary 的现成坐标/动作上，且 catalog 里有两个函数（`transform.low_frequency_triangle`、`cluster.majority_cluster`）的说明直接点名了 FreqFed。

逐步映射：

| n | 步骤 | 归类 | 依据 |
|---|---|---|---|
| 1 | 客户端本地训练 | outside | 普通本地 SGD，FreqFed 不修改；读 `received/factors/module`、写 `local_update/factors/module` |
| 2 | 权重张量整理成方阵 | compose | `states.flatten` 展平 + `transform.as_square` 按行铺成最小方阵（零填充）；LoRA 语义下还需一次 `B@A` 展开与加回 base |
| 3 | 二维 DCT | op | `transform.dct_2d`（orthonormal 2-D DCT-II） |
| 4 | 低频三角筛选 | op | `transform.low_frequency_triangle`，说明即 FreqFed 的 `i,j<=s//2 且 i+j<=s//2` |
| 5 | 两两余弦距离矩阵 | op | `cluster.distances(X, metric="cosine")` 就是 `1-cos`，对称、对角为 0 |
| 6 | HDBSCAN 聚类 | op | `cluster.majority_cluster`，说明写有 "FLAME and FreqFed run HDBSCAN with min_cluster_size = n // 2 + 1" |
| 7 | 取最大簇 | op | 同一函数返回最大簇的布尔 mask，`nonzero` 即被接受的索引 B |
| 8 | 对被接受模型取平均 | runtime_action | 计算是 `states.weighted_average(weights=None)`（等权），落地动作是 `select_and_weight` + `replace_global` |

数据与动作通路是通的：服务器能从 `uploads/factor_delta/client`、`uploads/module_delta/client`、`uploads/product_delta/client` 看到本轮上传，聚类结果落到 `aggregate/weights/client`，聚合结果 `aggregate/result/model` 由 `replace_global` 接管，下发经 `outgoing/factors/recipient` 的 `transform_broadcast`。

需要注意（不构成阻塞）的六处：

1. **全权重 vs LoRA 因子**：论文对本地模型权重 `W_i^t` 做 DCT，而运行时上传坐标的主语义是"相对下发的因子差"，且 `uploads/product_delta/client` 明确"不展开，按 Gram 计算"，**不能直接喂给 `dct_2d`**。要么服务器走 `uploads/module_delta/client` 自行 `B@A` 展开、再加回下发的 base（一次 matmul + 一次加法，属普通张量运算），要么由客户端把低频向量经 `channel/tensor/client` 上传。两条路都在现有原语范围内。
2. **方阵 layout**：论文完全未说明。`transform.as_square` 会零填充到最小方阵，零填充改变边长 `s`，也就改变第 4 步低频三角的范围，是潜在偏差来源，但这是论文侧空白而非算子缺口。
3. **DCT 归一化**：论文 `c1/c2`（k=0 时 `sqrt(2/(MN))`、k>=1 时 1）疑似省略了公共因子 `2/sqrt(MN)`，与标准正交 DCT-II 实质一致；若按字面逐频率缩放，会非均匀地改变各频率权重，从而改变余弦相似度与聚类结果。catalog 的 `dct_2d` 是标准正交版本。
4. **HDBSCAN 的接口粒度**：`cluster.majority_cluster` 把第 6、7 步合并了，它只暴露最大簇的 mask，不返回逐客户端 `cluster_ids` 与噪声标签 `-1`；`min_cluster_size=n//2+1` 由 catalog 固定，而论文未给该参数，且论文的规则是"argmax 簇大小"（相对最大即可），函数语义偏向"绝对多数簇"。无簇/全噪声、并列、空簇回退论文均未说明。
5. **聚合权重**：论文是 `1/L` 等权而非 FedAvg 的 `n_i/n`，正好对应 `weights=None`。
6. **因子空间平均的语义**：对"本地模型"取平均在 LoRA 下变成对因子取平均，只在同一轮共享同一 base 时与原论文近似等价（`mean(B@A) != mean(B)@mean(A)`）。

## 2. 缺的东西里哪些是通用的（别的方法也会用到），哪些是这篇论文特有的

**没有必须新增的通用算子，也没有必须新增的运行时动作。** 这条流水线的每一步要么被现成函数覆盖，要么只差几行普通张量运算。真正"缺"的东西分三类：

**（a）通用、但本条流水线不阻塞的候选缺口**

- **完整的 HDBSCAN 入口（clustering 族）**：现在只有 DBSCAN 替身 `cluster.density_clusters` 和只吐最大簇 mask 的 `cluster.majority_cluster`，没有"返回全部簇标签 + 离群分数/簇结构"的函数。FLAME 之外任何需要多簇结构、簇持久性或逐点 outlier score 的密度聚类方法都会要它。FreqFed 只消费"最大簇"这一个产物，所以被 `majority_cluster` 完全覆盖，不构成阻塞。
- **LoRA 因子 → 稠密权重矩阵的按模块展开（transform 族）**：所有要在"权重元素级/频域/坐标级"做分析的方法（DCT、小波、逐坐标裁剪、坐标中值）都必须先把上传的因子展开成 `B@A` 并加回 base。catalog 目前只有 State 级的 `flatten/stack` 和"不展开、按 Gram 计算"的乘积差坐标，这是一个刻意的设计留白。对 FreqFed 而言它只是一次 matmul，所以判为 compose 而不是 missing_op。
- **方阵 layout / padding 约定（transform 或 other 族）**：把异构、非方阵的参数张量排成哪种方阵、如何填充，换一个模型就要重选；这是通用工程约定，但它是"约定"而不是"可复用计算单元"，不建议做成算子。

**（b）这篇论文特有的东西**

- 低频三角的形状本身（`i+j <= s//2` 的截断）—— 已经是通用 transform 库里的 `transform.low_frequency_triangle`，且注释直接标注 FreqFed。
- "1-cos 距离 + 最大簇 + 等权平均"的判定规则 —— 是 `cluster.distances` + `cluster.majority_cluster` + `states.weighted_average` 的通用组合，不需要新算子。
- 论文未给的超参（`B`、`E_i`、`η_i`、损失、`|V|`、`min_cluster_size`、`min_samples`、`cluster_selection_method`、tie-break、全噪声回退）—— 这是**论文侧信息缺失**，不是算子缺口；实现时应按运行时默认选定并在场景里标定。

**（c）运行时侧**：不需要新的 coordinate 或新的动作。唯一要确认的是运行策略是否允许服务器展开上传的乘积差；即使不允许，`uploads/module_delta/client` 与 `channel/tensor/client` 也提供了足够的数据通路，因此不列入 blocking。

```json
{
  "key": "fereidooni2024freqfed",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": ["received/factors/module", "local_update/factors/module"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "标准本地训练，FreqFed 不修改，论文也未给 B/E_i/η_i/损失；运行时以收到的全局 LoRA 为起点、产出本地更新，属流程外的普通训练。"
    },
    {
      "n": 2,
      "class": "compose",
      "uses": ["states.flatten", "transform.as_square"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "论文未说明多层非方阵权重如何拼方阵。states.flatten 展平参数，transform.as_square 按行铺成最小方阵（零填充），两步即可；但要在 LoRA 运行时保持本地模型权重的语义，需先按模块把因子差展开成 B@A 并加回下发的 base（一次 matmul 加一次加法），且 uploads/product_delta/client 注明不展开、按 Gram 计算，不能直接喂给 dct_2d，故归 compose。零填充会改变方阵边长 s，从而改变第 4 步低频三角的范围，这是论文未定义处的偏差来源。"
    },
    {
      "n": 3,
      "class": "op",
      "uses": ["transform.dct_2d"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "transform.dct_2d 即 orthonormal 的 2-D DCT-II，与该步对应。疑点：论文 c1/c2 写成 k=0 时 sqrt(2/(MN))、k>=1 时 1，疑似省略了公共因子 2/sqrt(MN)，与标准正交式实质一致；若真按字面逐频率缩放，会非均匀改变各频率权重并改变余弦相似度，不是常数缩放。"
    },
    {
      "n": 4,
      "class": "op",
      "uses": ["transform.low_frequency_triangle"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "catalog 说明直接写明这是 FreqFed 的滤波：方阵边长 s 上保留 i,j<=s//2 且 i+j<=s//2 的系数并按行展平，与论文 loop_bounds/keep_condition 一致；论文未给的 |V| 由 s//2 固定。"
    },
    {
      "n": 5,
      "class": "op",
      "uses": ["cluster.distances"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "metric='cosine' 即 1-cos，结果对称、对角为 0，与论文定义一致。输入 F_i 可由服务器在展开上传因子后自行计算，也可经 channel/tensor/client 上传低频向量。"
    },
    {
      "n": 6,
      "class": "op",
      "uses": ["cluster.majority_cluster"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "catalog 没有返回全部 cluster_ids 的 HDBSCAN；cluster.majority_cluster 的说明点名 FreqFed/FLAME，内部按 sklearn HDBSCAN(min_cluster_size=n//2+1) 聚类并只保留一个簇，实际把第 6、7 步合并，不暴露逐客户端簇 ID 与噪声标签 -1。若确需标签，可用 cluster.density_clusters（DBSCAN 变体，eps=scale 乘第 min_samples-1 近邻距离中位数）近似，但参数语义与 HDBSCAN 不同，故仅作退路。"
    },
    {
      "n": 7,
      "class": "op",
      "uses": ["cluster.majority_cluster"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "该函数返回最大簇的布尔 mask，取 nonzero 即被接受的客户端集合 B，对应论文的 argmax 簇大小规则。差异：函数用 min_cluster_size=n//2+1 保证绝对多数，论文只要求相对最大且未给该参数；全噪声/无簇、并列、空簇回退论文均未说明，实现时需自定。"
    },
    {
      "n": 8,
      "class": "runtime_action",
      "uses": ["states.weighted_average", "select_and_weight", "replace_global"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "按 L 均分就是 State 空间的等权平均，states.weighted_average(weights=None) 直接给出；服务器侧写回全局对应 select_and_weight 加 replace_global（aggregate/result/model，随后经 transform_broadcast 下发到 outgoing/factors/recipient）。注意是 1/L 而非 FedAvg 的 n_i/n；对本地模型取平均在 LoRA 下变成对因子取平均，只在同一轮共享同一 base 时与原论文近似等价（平均的乘积不等于乘积的平均）。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
