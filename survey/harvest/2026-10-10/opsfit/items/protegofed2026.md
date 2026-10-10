## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：大部分能表达，但无法按论文原样完整表达（partial）。** 13 步中 11 步可以落到现有算子、coordinate 或动作上；真正卡住的只有步骤 4 和步骤 8，它们依赖同一个 catalog 里没有的计算单元——非线性流形降维（UMAP）。

逐步归类如下：

| 步 | 归类 | 依据（要点） |
|---|---|---|
| 1 | runtime_data | 初始 LoRA 由 `received/factors/module` 按模块粒度提供；选模块只是字典索引 |
| 2 | runtime_data | 逐样本梯度由 `samples/gradient/sample`（模型句柄 `model.per_sample_gradients`）直接提供 |
| 3 | compose | 按真实形状 reshape + `transform.dct_2d` + flatten |
| 4 | missing_op | UMAP，无任何等价函数或几行普通张量运算 |
| 5 | compose | `cluster.distances` + `cluster.agglomerative` + HDBSCAN 替身 + `cluster.silhouette` + 阈值比较 |
| 6 | compose | 主簇掩码索引 + 按行均值 |
| 7 | runtime_data | 质心走通用通道 `channel/tensor/client` |
| 8 | missing_op | 同一个 `umap_embedding`；聚类那一半本身可 compose |
| 9 | compose | 主簇客户端质心取均值 |
| 10 | runtime_data | 与步骤 7 对称，`channel/tensor/client` |
| 11 | compose | 拼接锚点 + 距离矩阵 + 聚类 + 取含锚点簇的索引 |
| 12 | runtime_action | 丢弃样本 = `mask_samples` |
| 13 | outside | 普通本地训练 + 标准 FedAvg |

也就是说：**检测链条本身（DCT → 双聚类 → 质心 → 带锚点重聚类 → 过滤 → FedAvg）是能拼出来的**，`cluster.*`、`transform.*`、`robust.*` 加普通索引/比较/均值足够，不需要新的通用算子；运行时也提供了逐样本梯度与通用通道张量。断点只在"把 N×d 特征压到 2 维"这一步——catalog 里只有 `transform.pca`（线性）和 `transform.random_projection`（随机投影），都不是 UMAP，也不能靠几行张量运算拼出来。

还有几处**不改归类但影响保真度**的疑点，在下面各步 `note` 里写明：HDBSCAN 只有 `cluster.density_clusters` / `cluster.majority_cluster` 两个替身且参数固定；`model.per_sample_gradients` 只承诺"参数组"粒度，未说明能否精确到单个 `lora_B` 模块；`channel` 的 `modified_by` 为空，动作表里没有"写通道"的动作，质心上传/广播只能算既有通道能力；若步骤 11 实际在 UMAP 嵌入空间做，还需要该缺失单元的 out-of-sample 变换。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用（别的方法也会用到，值得进算子库/运行时）**

1. `umap_embedding`（transform 族）：非线性流形降维是通用原语，凡是"把更新/梯度/特征嵌入后再聚类或可视化"的检测类方法都会用；catalog 现有降维只有 PCA 与随机投影，且 UMAP 需要 kNN 图、模糊单纯集与布局优化，属真正的缺失计算单元。
2. 逐样本梯度**按指定模块**取（模型句柄粒度问题）：样本级防御、样本影响估计普遍需要；现在句柄只写"参数组"，模块粒度未承诺。
3. 返回全部标签、参数可指定的 HDBSCAN：FLAME / FreqFed / FLDetector 一类方法通用；现有 `cluster.majority_cluster`（固定 `min_cluster_size = n//2+1`、只回主簇掩码）和 `cluster.density_clusters`（DBSCAN 替身）只能近似。
4. 通道上**传输/广播任意小张量**（质心、范数、相似度矩阵）并落成可写 artifact 的动作：很多防御要交换统计量；现在只有只读的 `channel/tensor/client`，`channel` 的 `modified_by` 为空，`outgoing/factors/recipient` 只装 LoRA 因子，`transform_broadcast` 也只被定义为改 `outgoing`。
5. 拟合式降维的 **out-of-sample 变换**（把新锚点 `c_g` 映射进同一嵌入空间）：凡是"先嵌入、再带锚点重聚类"的方法都会遇到，属通用接口。

**这篇论文特有（不构成新的通用算子需求）**

- 双聚类集成 + 轮廓系数门控的具体规则（`t_s=0.2`、`t_l=0.4`、两套聚类谁生效/是否一致的判定）；
- 两级质心协议（本地质心 → 服务器二次聚类 → 全局质心 → 广播 → 带锚点重聚类 → 过滤 → 重训）；
- 观测模块固定为最后一层 `self_attn.v_proj.lora_B`。

这三样都是通用部件之上的**编排与阈值**，用几行控制流、比较和索引即可表达，应为流水线/场景条目而非新算子。因此"缺的东西"里真正需要新增的通用计算单元只有一个（`umap_embedding`，族 transform），其余是运行时的粒度与接口问题；论文特有的部分没有提出通用算子需求。

```json
{
  "key": "protegofed2026",
  "steps": [
    {
      "n": 1,
      "class": "runtime_data",
      "uses": ["received/factors/module"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "初始全局 LoRA 可按模块粒度由 coordinate received/factors/module 取得；按名字取 model.layers.{last}.self_attn.v_proj.lora_B 只是字典索引，要压成 d 维向量最多用 states.flatten(state, keys=[...])，没有新计算。d 由该因子形状读出（lora_B 为 (out_features, rank)，d = out_features×rank）。接收模型本身是标准下发，不涉及任何动作。"
    },
    {
      "n": 2,
      "class": "runtime_data",
      "uses": ["samples/gradient/sample", "model.per_sample_gradients"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "逐样本梯度由模型句柄 model.per_sample_gradients(samples, group) 直接提供，对应 coordinate samples/gradient/sample；batch_size=1 只是逐个样本调用。疑点：catalog 只写“参数组(group)”，未说明 group 能否收窄到单个 v_proj.lora_B 模块；若 group 更粗，需要按参数布局切片取出该模块坐标（普通索引），d 维仍拿得到，但句柄是否原生支持模块粒度不确定。"
    },
    {
      "n": 3,
      "class": "compose",
      "uses": ["transform.dct_2d"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "先按 lora_B 真实形状 (out_features, rank) reshape，再 transform.dct_2d（对最后两维做正交 DCT-II），最后展平；reshape/flatten 属普通张量操作，故 compose。疑点：transform.as_square 会把 d 维向量铺成最小正方形并零填充（如 16384→128×128），与 (out_features, rank) 布局不同且零填充会改变频谱，不能当作这一步的实现。"
    },
    {
      "n": 4,
      "class": "missing_op",
      "uses": [],
      "missing_name": "umap_embedding",
      "missing_family": "transform",
      "missing_io": "输入: X (N, d) 浮点张量，n_components=2，以及 n_neighbors / min_dist / metric / seed 等参数；输出: (N, n_components) 嵌入坐标",
      "note": "UMAP 在 catalog 里没有对应函数：transform.pca 是线性 PCA、transform.random_projection 是随机投影，均不等价；UMAP 由 kNN 图、模糊单纯集与低维布局优化构成，不属于“几行加减乘/比较/取索引/求均值”能拼出的范围，故按 missing_op 处理，名字取计算本身。若库偏好与算法无关的命名，可叫 nonlinear_manifold_embedding_2d。疑点：UMAP 是转导式拟合，拟合后没有对新样本的 out-of-sample 变换接口，会牵连步骤 11。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": ["cluster.distances", "cluster.agglomerative", "cluster.density_clusters", "cluster.majority_cluster", "cluster.silhouette"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "层次聚类一侧可直接用 cluster.distances(ef, 'euclidean') + cluster.agglomerative(D, n_clusters=2, linkage)；HDBSCAN 一侧 catalog 只有替身——cluster.majority_cluster 固定 min_cluster_size=N//2+1 且只返回主簇布尔掩码，cluster.density_clusters 是 eps 由数据决定的 DBSCAN 替身。轮廓系数用 cluster.silhouette，t_s=0.2 / t_l=0.4 的门控和“两套聚类是否一致、取哪套”是普通比较+索引，故 compose。疑点：论文没给 HDBSCAN 的 min_cluster_size/min_samples，替身参数与论文未必一致；若要 G^1_k, G^2_k,... 多簇标签，majority_cluster 只给一个掩码，需改用 cluster.density_clusters 或 cluster.dbscan 自行取标签。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "用步骤 5 的主簇掩码索引原始频域特征 {f^i_k}，再对行取均值即本地质心 c_k，普通索引 + torch.mean 即可。catalog 没有“按标签对原始特征求质心”的单一函数（states.weighted_average 只作用于 State 因子对象），但这正属 compose 允许的普通张量运算。"
    },
    {
      "n": 7,
      "class": "runtime_data",
      "uses": ["channel/tensor/client"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "质心是通道上的小型张量，服务器侧从 channel/tensor/client 读到 K×d 的 {c_1,...,c_K}；vocabulary 的 uploads/* 只覆盖 LoRA 因子差、上传名单与探针行为，装不下这种自定义向量，故用通用通道张量。疑点：channel 的 modified_by 为空，动作表里没有“写通道”的动作，“上传”只能算既有通道能力；若严格按动作表判定，它更接近协议性传输（outside），但数据本身确实由该 coordinate 提供。"
    },
    {
      "n": 8,
      "class": "missing_op",
      "uses": ["cluster.distances", "cluster.agglomerative", "cluster.majority_cluster"],
      "missing_name": "umap_embedding",
      "missing_family": "transform",
      "missing_io": "输入: C (K, d) 各客户端质心，n_components=2，以及 n_neighbors / min_dist / metric / seed；输出: (K, n_components) 嵌入坐标 ec 与主簇标签/掩码",
      "note": "聚类那一半可 compose（cluster.distances + cluster.agglomerative，或用 cluster.majority_cluster 直接取主簇 G^1_II），但把 K×d 质心降到 2 维与步骤 4 是同一个缺失单元 umap_embedding，整步因此记 missing_op。疑点：K（客户端数）通常只有几十，UMAP 在这么小的样本上不稳定，且论文未明说这里用的就是 UMAP。"
    },
    {
      "n": 9,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对主簇客户端的原始维质心取坐标均值即 c_g：索引 + torch.mean。若把“质心”换成坐标中位数，也只是换成 robust.coordinate_median，仍不需要新算子。"
    },
    {
      "n": 10,
      "class": "runtime_data",
      "uses": ["channel/tensor/client"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "与步骤 7 对称：c_g 是 d 维频域向量而非 LoRA 因子，装不进 outgoing/factors/recipient，transform_broadcast 按定义也只修改 outgoing，因此按“客户端从 channel/tensor/client 取得 c_g”算取数据。疑点：若要求广播必须落到某个可修改 artifact 上，现有动作表没有能广播非模型张量的动作。"
    },
    {
      "n": 11,
      "class": "compose",
      "uses": ["cluster.distances", "cluster.agglomerative", "cluster.density_clusters"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把 c_g 拼到本地原始频域特征后做 cluster.distances + cluster.agglomerative（或 cluster.density_clusters），再取包含锚点那一簇的样本索引：torch.cat + cluster.* + 比较/索引，属 compose。疑点：若论文实际是在步骤 4 的 UMAP 二维空间里带锚点重聚类，就必须先把 c_g 用同一个 UMAP 变换映射进来（out-of-sample transform），这一步会一并落到 umap_embedding 的缺失上；按流水线写明的输入（原始频域特征）则 compose 成立。"
    },
    {
      "n": 12,
      "class": "runtime_action",
      "uses": ["mask_samples"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "丢弃非干净簇样本就是对 samples 做子集掩码，正好是 vocabulary 里 samples 的 modified_by 之一 mask_samples；没有改写样本内容，所以不是 edit_samples。"
    },
    {
      "n": 13,
      "class": "outside",
      "uses": ["states.weighted_average"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "净化数据上的本地 FIT + 标准 FedAvg 聚合，按 vocabulary 属于防御计算之外（普通本地训练、标准聚合）。若要在 KB 里落地，聚合那半可由 states.weighted_average（因子空间逐项加权平均，即 FedAvg）承担，训练那半走运行时既有训练循环；lora_rank=4 / local_epochs=1 / rounds=100 / lr=2e-5 只是超参。"
    }
  ],
  "expressible": "partial",
  "blocking": ["步骤 4 与步骤 8 的降维是 UMAP 式非线性流形降维：catalog 只有 transform.pca、transform.random_projection 这类线性变换，没有任何函数或几行普通张量运算能等价实现（替换成 PCA/随机投影会改变方法），因此这两步按论文原样无法表达；其余 11 步都能落到现有算子、coordinate 或动作上。若步骤 11 的带锚点重聚类实际发生在 UMAP 嵌入空间，还会额外依赖该缺失单元的 out-of-sample 变换接口。"]
}
```
