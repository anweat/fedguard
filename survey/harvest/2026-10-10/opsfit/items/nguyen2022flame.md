## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：可以端到端表达（expressible = full）。** 8 步全部落在 catalog 或 vocabulary 内，没有一步需要 catalog 之外的可复用计算单元，也没有一步需要运行时拿不到的数据或做不了的动作。

逐步归属：

| n | 步骤 | 归类 | 依据 |
|---|---|---|---|
| 1 | 展平/序列化本地模型 | op | `states.flatten` + `states.stack` 正好给单个 state 向量与 (n, d) 矩阵 |
| 2 | 两两余弦距离 | op | `cluster.distances(X, metric='cosine')` 定义就是 1 − cos |
| 3 | HDBSCAN 多数簇过滤 | op | `cluster.majority_cluster` 说明里点名 FLAME/FreqFed，`min_size=n//2+1` 即论文参数 |
| 4 | 到上一轮全局的欧氏距离 | op | `geometry.distance_to(X, ref)` 逐行到参考向量的距离 |
| 5 | 距离中位数作裁剪边界 | compose | 无 1-D 中位数算子，但可用 `robust.coordinate_median`（把 e 视作 (n,1)）或 sort+取中位，两行张量运算 |
| 6 | 按 min(1, S_t/e_l) 缩放被接纳更新 | compose | 外部标量分数做分母 + clamp + 广播乘，几行张量运算；现有裁剪算子分母语义不同（见下） |
| 7 | 等权聚合 | op | `states.weighted_average(states, weights=None)` 即 1/L 平均 |
| 8 | 自适应高斯加噪 | op | `update.add_gaussian_noise(state, sigma=S_t·λ, generator)`，σ 由标量算术给出 |

**数据面与动作面都齐。** 服务器侧要的两类输入都有 coordinate：本轮上传由 `uploads/factor_delta/client`（或 `uploads/module_delta/client`、`uploads/product_delta/client`）+ `uploads/roster/client` 提供，上一轮的 G*_{t-1} 由 `aggregate/result/model`（或 `outgoing/factors/recipient`）提供，历史在 `history/features/round`。步骤 3 的"剔除/保留名单"落在 `uploads`、`aggregate` 的 `select_and_weight` 上，步骤 6 落在 `transform_update` 上，步骤 8 的结果写回 `aggregate` 用 `replace_global`、下发用 `transform_broadcast`；这些动作 vocabulary 全部列了。整条 pipeline 只出现服务器聚合/后聚合计算，没有"本地训练、标准 FedAvg、下发模型、密码学、离线造数据"这类步骤，所以没有需要归为 outside 的条目。

**留下的疑点（都不构成阻塞，但必须说明）：**

- `geometry.distance_to` 的说明在 catalog 里是空的，签名 `(X, ref) -> Tensor` 与需求完全吻合；若坚持"说明为空不采信"，改用 `(W - G).norm(dim=1)` 就是 compose，结论不变。
- `cluster.majority_cluster` 不暴露 `min_samples=1`，也不接受自定义 HDBSCAN 参数。catalog 明说它按 `min_cluster_size = n//2+1` 跑 sklearn HDBSCAN 并只留一个簇，这正是 FLAME 的语义；只有当你要求逐字复刻 `min_samples=1` 的层次聚类结果时，catalog 才没有对应函数（`cluster.dbscan` 要自己给 eps，`cluster.density_clusters` 在 `min_samples=1` 时 eps 退化为 0），那时才需要补一个"预计算距离矩阵上的 HDBSCAN"算子。这是参数保真度问题，不是能力缺口。
- **p 的含义**：论文写的是"全部权重与偏置"，而运行时只暴露 LoRA 因子/乘积差（`received/factors/module`、`uploads/factor_delta/client`、`uploads/product_delta/client`）。按"W_i ≡ 本地 LoRA 因子向量"展平则完全可做；若坚持 p 必须包含冻结基座，余弦距离会被共享基座淹没，且服务器侧拿不到 `<W_base, Δ_i>` 这类交叉项（`lowrank.gram` 只给乘积差之间的内积）——那才会变成 needs_runtime。鉴于整个 vocabulary 就是联邦 LoRA 场景，取前一种读法，故仍判 full。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**严格意义上没有 missing_op，也没有 needs_runtime。** 所以"缺"的只是两个便利性缺口，且都落在少数几行普通张量运算里：

**通用型缺口（别的方法也会碰到，但目前都能 compose 掉，因此我没把它们升级成 missing_op）：**

1. **一维分数向量的稳健中位数**：任何"用 median/MAD 当裁剪阈值或检测阈值"的防御（FLAME、Median/Trimmed-mean 系、FLTrust 的归一化、各种鲁棒 z 检验）都会要。现有 `robust.coordinate_median` 是逐坐标中位数（把 (n,) reshape 成 (n,1) 可借用），`robust.mad_scores` 内部算了中位数但不返回它，`torch.median` 在偶数 n 上取下中位数而不是 catalog 约定的两中值平均。属于"通用形态但没有正门算子"，两行可补。
2. **以外部标量分数为分母的逐客户端缩放/裁剪**：形如 `x_i ← min(1, τ/s_i)·x_i`，s_i 来自本步之外（这里是步骤 4 的 e_i）。范数裁剪类防御普遍需要。现有三个裁剪算子都对不上：`update.clip_to_norm` 用 `‖state−base‖` 作分母并重建 `base + scale·delta`，`update.scale_to_norm` 把 delta 归一到指定范数，`update.clip_state_norm` 用 `‖state‖` 作分母且只返回因子；FLAME 是按 `min(1, S_t/e_l)` 缩放 `W_l` **本身**，所以只能广播乘法拼。同理属于通用形态、两行可补。
3. **（半通用）预计算距离矩阵上参数可调的 HDBSCAN**：`min_samples` 这一维在 catalog 里被固化掉了。若只是复现 FLAME 的主流程，`cluster.majority_cluster` 已够；只有当需要精确控制层次聚类的保守度时才是缺口，可复用性一般。

**论文特有的部分（没有、也不需要通用算子）：** 裁剪边界取"到上一轮全局模型距离的中位数"`S_t`、噪声尺度 `σ = λ·S_t`（λ 由 (ε, δ) 决定）这两个自适应量，纯粹是标量统计加算术；"多数簇 + 覆盖率 ≥ n/2+1"的过滤准则是 `cluster.majority_cluster` 已内建的 FLAME/FreqFed 语义。这三处都带着明显的论文色彩，但都不构成新的可复用计算单元。

**一句话总结**：通用缺口只有"1-D 中位数"和"按外部分数缩放"两个形态，均可 compose；论文特有缺口为零；因此 blocking 为空，方法整体可表达。

```json
{
  "key": "nguyen2022flame",
  "steps": [
    {
      "n": 1,
      "class": "op",
      "uses": ["states.flatten", "states.stack", "uploads/factor_delta/client"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "states.flatten 给单个 p 维向量，states.stack 把 n 个 state 堆成 (n,p)；上传内容由 uploads/factor_delta/client（或 uploads/module_delta/client、received/factors/module）提供。疑点：若 p 必须包含冻结基座而不是 LoRA 因子，则运行时只给因子/乘积差，见第 1 节疑点 c。"
    },
    {
      "n": 2,
      "class": "op",
      "uses": ["cluster.distances"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "cluster.distances(X, metric='cosine') 返回 1 - 余弦相似度，与 c_ij 定义逐字一致；geometry.cosine_matrix 也可用但还要自己取 1-，不必要。"
    },
    {
      "n": 3,
      "class": "op",
      "uses": ["cluster.majority_cluster"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "catalog 说明里点名 FLAME/FreqFed：HDBSCAN(min_cluster_size = n//2+1) 只留一个多数簇并返回布尔掩码，转成索引是非零索引的普通操作。疑点：min_samples=1 不暴露，属参数保真度而非能力缺口；cluster.density_clusters 在 min_samples=1 时 eps 退化为 0，不能替代。"
    },
    {
      "n": 4,
      "class": "op",
      "uses": ["geometry.distance_to", "aggregate/result/model"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "geometry.distance_to(W, G*_{t-1}) 逐行给到参考向量的距离；G*_{t-1} 从 aggregate/result/model（或 outgoing/factors/recipient）取。该函数 catalog 说明为空，若因说明缺失不采信，则 (W - G).norm(dim=1) 两行 compose，结论不变。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": ["robust.coordinate_median"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "没有一维中位数算子：把 e 视作 (n,1) 调 robust.coordinate_median（偶数 n 取中间两值均值），或 torch.sort 后取中位，都是两行张量运算；注意 torch.median 偶数时取下中位数、robust.largest_gap_threshold 是另一回事。e 覆盖全部 n 个客户端（含被剔除者），服务器侧 uploads 里有全部上传，数据可得。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "论文语义是 factor_l = clamp(S_t / e_l, max=1)，再 W^c_l = factor_l * W_l（逐行广播乘），属普通张量运算。现有裁剪算子都对不上：update.clip_to_norm 以 ‖state-base‖ 为分母并重建 base+scale·delta，update.scale_to_norm 把 delta 归一到指定范数，update.clip_state_norm 以 ‖state‖ 为分母——三者都不吃外部 e_l。若实现采用 delta 裁剪变体（对 W_l - G*_{t-1} 裁剪），则 update.clip_to_norm(W_l, G*_{t-1}, S_t) 可直接当 op 用。"
    },
    {
      "n": 7,
      "class": "op",
      "uses": ["states.weighted_average"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "weights=None 即等权 1/L 平均，正对应论文明确不使用客户端数据量加权；输入是步骤 6 产出的被接纳且已裁剪的 state 列表。"
    },
    {
      "n": 8,
      "class": "op",
      "uses": ["update.add_gaussian_noise"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "σ = λ·S_t，λ = (1/ε)·sqrt(2·ln(1.25/δ)) 由标量算术算出（δ 论文未给数值，需外部指定），再调 update.add_gaussian_noise(state, σ, generator) 逐项加 N(0,σ²)，与论文一致；noising 加在聚合后的全局模型上，由 aggregate 的 replace_global 写回、outgoing 的 transform_broadcast 下发。update.clip_and_noise 是批梯度上的联合裁剪+加噪，语义不符。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
