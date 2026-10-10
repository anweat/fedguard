## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：算子层面基本可以（甚至这篇论文的算子已经被专门收进 catalog），但运行时层面只能算 partial。** 缺口不在计算单元，而在"论文是集中式的、以全局按类的逐样本统计量"这一前提与联邦运行时的数据/协调面之间的冲突。

逐步看：

- **第 1 步（按标签分组）**：catalog 没有"分组"函数；`sampling.stratified(groups, per_group, rng)` 名字接近，但它的语义是"每个组最多取 per_group 个索引"，是抽样不是分组，不能算 op。分组本身是"按 label 建布尔掩码 + index_select"，属 compose。疑点：vocabulary 里没有任何 coordinate 承载标签（`samples/manifest/sample` 只有哈希/来源/长度），这一步默认标签随本地样本一起拿到。
- **第 2、8 步（在完整数据上训练 L / 剔除后从随机初始化重训）**：普通训练，属 outside。运行时以逐样本梯度、步内 trace、优化器参数值等 coordinate 支持训练，但 catalog 没有训练入口，服务器也没有"在全量数据上训练"的入口。
- **第 3 步（逐样本表征）**：`samples/hidden_state/sample`（via: model_handle）直接提供，取法是 `model.hidden(samples, layer, pool)`；若要某个子模块的原始输出则用 `model.activations`。属 runtime_data。
- **第 4 步（类内中心化）**：`transform.standardize` 会额外除以标准差，**不等价**；`spectral.top_singular_scores` 内部会中心化但不返回均值 R̂，而本步要输出均值。故只能 compose（`M.mean(0)` + 相减）。
- **第 5 步（最大右奇异向量）**：`spectral.top_direction(M, center=False)` 就是"行方向最大能量的单位向量"= M 的最大右奇异向量；等价地 `transform.pca(M, k=1)` 的 components 也是（对已中心化的 M 再中心化是恒等操作，所以即使该函数内部中心化也不影响结果）。属 op。
- **第 6 步（投影平方分数）**：`spectral.top_singular_scores` 的说明直接写着 Tran et al. 2018，"中心化行在最大右奇异向量上投影的平方"，正是 τ，属 op（它等于把 4–6 步合并）；若坚持用第 5 步已算出的 v，则 `(M @ v) ** 2` 是一行 compose，两者等价（v 的符号被平方消掉）。
- **第 7 步（删每类 top 1.5ε）**：选谁删 = `sampling.top_k(scores, k)` + 取整/索引（compose，k 的舍入论文未说明）；删除这个改动本身对应运行时的 `mask_samples`（samples 制品的 modified_by 含它）。注意 `robust.quantile_threshold` 是"用良性样本分位数定阈值"，与"按本类自身分数排序删固定比例"语义不同，不能替代；`robust.largest_gap_threshold`、`density.kde_valley_threshold` 也都是别的阈值规则。属 runtime_action。

**前提不匹配（不影响算子可表达性，但影响能否照搬）**：运行时是联邦 LoRA 微调（样本多为文本、制品按 client/server 分侧），论文是 CIFAR-10 + ResNet 的集中式图像分类（每类 5000 样本、倒数第二个 residual unit）；论文的 `stages` 把它放在 `server_aggregate / server_post_aggregate`，而方法本体要读逐样本表征与标签——服务器侧只有 `uploads/*` 这类客户端级制品，**在服务端根本取不到**。真正能表达的只是"每个客户端在自己数据上各算各的 v、各定阈值、各删本地样本"的局部版本，语义与论文的全局类内清洗不等价（投毒方可自保）。因此 `expressible = partial`，且**没有任何一步需要新增 missing_op**。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用的（别的方法也会用到，值得进运行时/坐标层而不是算子层）**

1. **样本标签 coordinate**。按类/按标签的一切操作——类内清洗、标签翻转检测、分层采样、按类稳健聚合、逐类误杀统计——都要读标签；现在 `samples/manifest/sample` 只给哈希/来源/长度。这是通用缺口（坐标层）。
2. **跨客户端的逐样本表征/分数汇集与全局阈值协调**。论文要在"某一类的全部样本"上算 v 并统一排序；运行时的逐样本访问（hidden_state / loss / gradient）都只在客户端本地，`channel/tensor/client` 只是通道上的张量、没有约定用它传逐样本分数，`mask_samples` 也只作用于本地 samples。凡是基于逐样本 loss / 表征 / 影响的联邦清洗与检测都需要这个能力，属通用缺口（运行时面）。
3. **跨客户端的样本级删除/屏蔽协调动作**（对应 `mask_samples` 只本地）。凡"检测到就丢样本/丢客户端样本"的方法都要，通用。

**这篇论文特有的**

1. **谱特征算子本身**（类内中心化 + 最大右奇异向量 + 投影平方）：这是论文特有的计算单元，但 **catalog 已经收录**（`spectral.top_singular_scores`、`spectral.top_direction`），所以它不构成缺口，也不需要新算子。
2. **"删每类得分最高 1.5ε 比例"这条固定比例规则、每类独立处理、先训一遍再随机初始化重训的两阶段流程**：论文特有的参数与流程，用 `sampling.top_k` + 掩码 + `mask_samples` + outside 训练即可表达，不需要新的通用算子。
3. 唯一可能被提议的通用单元是"按 key 分组索引"（group_indices_by_key），但它只是掩码 + index_select，按规则归 compose，不值得单列；于是 8 步里 `missing_op` 为空。

```json
{
  "key": "tran2018spectral",
  "steps": [
    {
      "n": 1,
      "class": "compose",
      "uses": ["samples/text/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "按标签分组＝按 label 建布尔掩码 + index_select，几行普通索引/张量运算即可。catalog 无分组函数；sampling.stratified 名字接近但语义是『每组最多取 per_group 个索引』的抽样（且它需要外部传入 groups），不能算 op。疑点：vocabulary 没有承载标签的 coordinate（manifest 只有哈希/来源/长度），这一步默认标签随本地样本一起拿到；论文的 5000 样本/类只是集中式设定。"
    },
    {
      "n": 2,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "在（可能被投毒的）完整训练集上做一次普通训练，属常规本地训练，不是防御算子；运行时的逐样本梯度/步内 trace 足以支撑，catalog 无训练入口。联邦下只能用『客户端本地训练 + FedAvg』近似，论文本身是集中式、需要全量数据在一处。"
    },
    {
      "n": 3,
      "class": "runtime_data",
      "uses": ["samples/hidden_state/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "逐样本表征由模型句柄 model.hidden(samples, layer, pool) 直接提供（该 coordinate 标了 via: model_handle）；若要指定子模块的原始输出可用 model.activations(samples, select)。layer 作为参数传入即可，论文未给出表征维数 d，不影响取值。"
    },
    {
      "n": 4,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "R̂ = M0.mean(0)，M = M0 - R̂，两行张量运算，」且本步要求同时输出均值。transform.standardize 会额外除以标准差，不等价；spectral.top_singular_scores 内部会中心化但不返回均值，所以都不能算 op（避免按名字相近硬套）。"
    },
    {
      "n": 5,
      "class": "op",
      "uses": ["spectral.top_direction"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "top_direction(M, center=False) 就是『行方向最大能量（方差）的单位向量』，即中心化矩阵 M 的最大右奇异向量。等价地 transform.pca(M, k=1) 的 components 也是它（对已中心化的 M 再中心化是恒等操作，因此即使实现内部中心化结果不变）。v 的符号不影响第 6 步（会被平方消掉）。"
    },
    {
      "n": 6,
      "class": "op",
      "uses": ["spectral.top_singular_scores"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "该函数说明即 Tran et al. 2018：『中心化行在最大右奇异向量上投影的平方』，直接给出 τ，等于把第 4、5、6 步合并（自带中心化与取 v）。若坚持用第 5 步已算好的 v，则 (M @ v) ** 2 是一行 compose，两者数值等价，v 的符号无影响。"
    },
    {
      "n": 7,
      "class": "runtime_action",
      "uses": ["mask_samples", "sampling.top_k"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "『删样本』这个改动对应运行时的 mask_samples（samples 制品的 modified_by 含它）；而『删哪些』= sampling.top_k(scores, k=floor(1.5·ε·n)) + 取补集掩码，属 compose（论文未说明取整方式）。robust.quantile_threshold/largest_gap_threshold 是别的阈值规则，语义不同，不能替代。注意 mask_samples 只作用于本地 samples，做不了『全类统一删除』。"
    },
    {
      "n": 8,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "合并剩余类子集＝索引拼接（trivial），随后是从随机初始化重训一次（论文只做一轮剔除 + 一次重训）。属常规本地训练，不算防御算子；『随机初始化』只是初始化方式，运行时可用本地训练 + replace_global 承载，但同样没有『服务器在全量数据上训练』的入口。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "论文的清洗统计量（类内中心化、最大右奇异向量 v、top-1.5ε 阈值）都是『全体训练集某一类』上的全局量，而运行时的逐样本表征只在客户端本地可得（samples/hidden_state/sample 需模型前向且 samples 制品 side=client），没有任何 coordinate/动作能把全局、按类、逐样本的表征或分数汇集到一处，mask_samples 也只能删本地样本 —— 照论文语义的全局类内清洗不可表达，能表达的只是各客户端在自己数据上各算 v、各定阈值的局部版本（语义不等价，投毒方可在自己数据上规避）。",
    "标签不是可取的 coordinate：samples/manifest/sample 只提供哈希/来源/长度，而第 1、4、5、6、7 步全部按标签分组/按类排序；运行时要支持按类清洗就必须让样本标签可读。",
    "前提不匹配：论文先在完整数据上训 L、剔除后再从随机初始化重训（集中式两次全量训练），而运行时只有客户端本地训练 + FedAvg + replace_global，没有『服务器对全量数据训练』的入口；同时 stages 把方法放在 server_aggregate/server_post_aggregate，但服务器侧只有 uploads/* 的客户端级制品，取不到逐样本表征与标签。这一条更像集中式前提无法照搬，而非算子缺口（训练部分本属 outside）。"
  ]
}
```
