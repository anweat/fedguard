## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：能，属于 `full`。** 这条流水线是 catalog 里被"点名"覆盖得最完整的一类：核心权重计算已经有现成算子。

- **数据面完整**。流水线的全部输入都能落到坐标上：本轮上传 = `uploads/factor_delta/client`（相对下发的因子差）/ `uploads/module_delta/client`（指定模块的因子差）/ `uploads/product_delta/client`（乘积差，明确写着"不展开，按 Gram 计算"）；全局模型 = `aggregate/result/model` 或 `outgoing/factors/recipient`；跨轮数据 = `history/features/round`；名单与权重 = `uploads/roster/client`、`aggregate/weights/client`。服务器侧不需要任何 `model_handle` 方法（FoolsGold 只用上传向量与全局参数，不做前向/反向）。
- **算子面几乎是逐条对应**。最有辨识度的第 6–9 步（pardoning → α=1−max → 按最大值重标定 → logit 并裁剪）就是 `robust.foolsgold_weights(cs, kappa=1.0)`，其签名与说明（"Fung et al. 2018"、"pardoning"、"rescale by the maximum"、"logit"、"alpha 裁剪到 [0,1]"、"kappa"）与论文正文逐字吻合，不是名字相似。第 4–5 步的余弦矩阵与行最大可由 `geometry.cosine_matrix`（或 `cluster.distances(metric='cosine')`、`lowrank.gram`）加普通归一化/掩码/归约拼出；第 2、3 步的幅值阈值与跨轮累加由 `sampling.top_k`、`states.add` 覆盖。
- **动作面完整**。第 10 步就是 `select_and_weight`（按名单和权重加权聚合 uploads，且不含 n_k/n，正是 FoolsGold 的语义）+ `replace_global`，坐标 `aggregate/weights/client` 也正好承载 α。
- **三处需要说明的，都不是"做不了"，而是"论文没定/要在 LoRA 语境下约定"**：(a) S_t 的加权公式（第 2、4 步）论文自己说未说明，只能落成"逐坐标权重/硬筛 top-k"这一可自洽的读法；(b) LoRA 下"输出层参数"只暴露因子，冻结基座 W0 没有坐标也没有句柄读法，若规则必须用 W0+BA 合并权重，只能用一次普通 matmul 或退化为 B@A；(c) α 是学习率式加权和，而 `states.weighted_average` 是加权平均，差一个标量 Σα。三处都是建模决策，不是算子缺口或运行时缺口。

因此没有 `missing_op`、`needs_runtime` 或 `outside` 的步骤（本流水线两个 stage 都在服务器侧，不含本地训练与下发）。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用缺口：没有。** 这条流水线不需要任何新的可复用计算单元。反过来说，它依赖的通用件都已具备：余弦相似度（`geometry.cosine_matrix`、`cluster.distances`）、不展开低秩矩阵算两两内积（`lowrank.gram`）、按分数取前 k（`sampling.top_k`）、State 的累积与聚合（`states.add`、`states.weighted_average`）。若硬要抽象，只有三处"通用性很弱的一行式"可以补，但都不构成 `missing_op`：

1. 带逐坐标权重的余弦相似度（现在要手写 `X⊙S` 再 `cosine_matrix`；等价于对角权重矩阵，属 compose）；
2. 排除对角线的行最大（`geometry.cross_section` 只给"对其他客户端的平均余弦"，不给最大值；一行 `max` 即可，属 compose）；
3. 未归一化的加权和聚合（`states.weighted_average` 会除以 Σα，需乘回 Σα，属 op/compose 之间的量级）。

**论文特有的规格空白（不是运行时能力缺口）：**

- **S_t 的"指示性特征"启发式**：论文只给了扫描区间（0.001–1）与 hard/soft 两模式，没给公式，也没给它在 LoRA 因子空间里的对应（乘在 A 因子上即输入特征轴加权，乘在 B 因子上即输出类轴加权）。这是本流水线唯一没有单一函数对应的地方，但用普通乘/比较/取索引可拼，故归 compose 而非 `missing_op`。
- **"输出层梯度切片"这一全模型假设**：运行时按模块给因子差，不提供参数空间扁平切片；单层 softmax（d_out=d）时论文的切片退化，LoRA 下需约定"输出层 = 哪个模块"。忠实实现所需的冻结基座权重无坐标可读，但用 B@A 或因子本身可做自洽版本，因此不阻塞、也不升级为 `needs_runtime`。
- **聚合语义**：α 当学习率、不加 n_k/n、是加权和而非加权平均；`select_and_weight` 支持自定义权重，语义可承载，但需确认它按"和"还是"平均"落账。
- 反过来，FoolsGold 的核心（累积更新的余弦相似度 + pardoning + logit 权重）在 catalog 里已是一等算子 `robust.foolsgold_weights`，说明这部分是**通用件**，不是论文特有件。

```json
{
  "key": "fung2018foolsgold",
  "steps": [
    {
      "n": 1,
      "class": "runtime_data",
      "uses": ["uploads/factor_delta/client", "uploads/module_delta/client", "uploads/product_delta/client"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "本轮每客户端上传按客户端粒度可取：uploads/factor_delta/client 已是相对下发的差；'抽取输出层'就是选中承载输出投影的那个模块，取 uploads/module_delta/client（指定模块的因子差），选模块属普通取索引。疑点：LoRA 下 ΔW=BΔAΔ 不是 d 维扁平向量，若要参数空间向量需一次普通 matmul；若只要两两余弦，可直接用 uploads/product_delta/client（文档明说不展开、按 Gram 计算）配 lowrank.gram。'哪个模块算输出层'需配置约定，运行时不带这个语义。"
    },
    {
      "n": 2,
      "class": "compose",
      "uses": ["aggregate/result/model", "sampling.top_k"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "取绝对值、阈值比较、取索引都是普通张量运算：硬筛选取 |θ| 前 k=ratio·d 个（sampling.top_k 收 dict，需要先把 (下标,幅值) 转成字典），软加权取 |θ|/max|θ|。疑点：(a) 论文用的是全局模型输出层的完整参数（含冻结基座 W0），runtime 只暴露 LoRA 因子 aggregate/result/model，没有读基座权重的坐标，也没有句柄方法能读参数，只能用 B@A（一次普通 matmul）或因子本身近似，忠实度需声明；(b) ratio 扫描 0.001–1 无默认值、hard/soft 未定，属建模选择；(c) 需要定义'特征轴'是 d_in 还是低秩瓶颈 r。"
    },
    {
      "n": 3,
      "class": "op",
      "uses": ["states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "逐轮累加就是 H_i ← states.add(H_i, Δ_i, scale=1.0)，对每个客户端调用一次即可；scale 参数还能覆盖论文没写清的窗口/衰减（衰减需先把 H 自身缩放一次，仍是一两行）。备选读法：若运行时已把逐轮更新保留为 history/features/round（此前各轮的特征），这一步退化为对该列表求和（普通 reduce，或 sequential.window_mean×length），可归 runtime_data/compose；两条路都通，不构成缺口。"
    },
    {
      "n": 4,
      "class": "compose",
      "uses": ["geometry.cosine_matrix", "lowrank.gram", "cluster.distances"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "S_t 加权等价于对角权重矩阵：展开走法 X_w = H ⊙ S 后 geometry.cosine_matrix(X_w)；或 cluster.distances(X,'cosine') 得 1−cos 再减一下。不展开走法：ΔW·diag(S) = B(A·diag(S))，把 A 因子按 S 逐坐标缩放仍是同秩，再 lowrank.gram 得两两内积、除以 √(G_ii G_jj) 即余弦——全是普通乘除，故不必新增算子。必须把对角线置零/掩码才能满足'j 只遍历其他客户端'（普通取索引）。疑点：论文未给 S_t 的具体加权公式（是逐坐标乘、还是只用于筛选坐标），这是全流程唯一没有单一函数对应之处；若 S_t 取全 1（论文正文主算法），本步直接是 op：geometry.cosine_matrix。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "一行归约：先把对角线置 0/−inf，再 torch.max(CS, dim=1)。catalog 里没有给行最大相似度的函数——geometry.cross_section 给的是'对其他客户端的平均余弦'（均值，不是最大值），cluster.distances 只给距离；robust.foolsgold_weights 内部确实要算行最大（pardoning 与 1−max 都用 v），但不单独返回 v。故按严格标准归 compose，而非因名称相近算 op。"
    },
    {
      "n": 6,
      "class": "op",
      "uses": ["robust.foolsgold_weights"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "该函数文档的第一阶段就是 pardoning（cs_ij ← cs_ij·v_i/v_j，v_j > v_i 时），且整链输出与论文一致，kappa 默认 1.0 与参数一致。疑点：它一次返回最终学习率，不暴露中间 CS′；本流程下游只用最终 α，所以一次调用即可，步骤 7–9 无需真的重复实现。若确实要 CS′，那是三行掩码乘（v[:,None]/v[None,:] 加 v[None,:]>v[:,None] 的 where），属 compose。另需单测确认对角线是否已被该函数当作排除（v_i 必须是 j≠i 的最大值；若把 cos=1 的自相似算进去，α 会全为 0 而退化），文档只说'边界处理遵循作者参考代码'。"
    },
    {
      "n": 7,
      "class": "op",
      "uses": ["robust.foolsgold_weights"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "α = 1 − max_j(cs′_ij) 正是该函数的第二阶段（文档：'alpha = 1 - max similarity'）。同样地，函数返回的是再经归一化与 logit 的最终学习率，不单独返回原始 α；若单要原始 α，是 1 − CS.max(dim=1)（compose，一行）。"
    },
    {
      "n": 8,
      "class": "op",
      "uses": ["robust.foolsgold_weights"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "函数文档中的 'rescale by the maximum' 即此步：α ← α/max_i α，归一化后至少一个元素为 1。max=0 等边界按作者参考代码处理（文档已声明遵循）。"
    },
    {
      "n": 9,
      "class": "op",
      "uses": ["robust.foolsgold_weights"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "该函数的返回值就是这一步：κ(ln[α/(1−α)]+0.5) 后裁剪到 [0,1]，κ 由参数给出（论文 κ=1）。疑点：文档明确写了 logit 与'按作者参考代码裁剪到 [0,1]'，但没有逐字写出 +0.5 的 center offset；作者参考代码里含该偏移，建议用单测对一条已知 CS 校验，确认 0.5 与边界行为。若未包含，也只需几行 log/clamp（compose）。"
    },
    {
      "n": 10,
      "class": "runtime_action",
      "uses": ["select_and_weight", "replace_global"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "服务器用本轮 α 把 uploads 聚合成新全局模型，正对应 uploads/aggregate 的 modified_by 动作：select_and_weight（按名单与权重加权聚合，权重来自 α、不含 n_k/n）写出 aggregate，replace_global 把它落成新的全局。算术上等价于 states.weighted_average(Δ 列表, weights=α) 再乘 Σα、用 states.add 加到 w_t 上——注意 weighted_average 是加权平均（会除以 Σα），而论文要的是学习率式加权和，需一次标量还原；若只当成纯计算，也可归 compose/op。不计入 outside，因为权重是防御算出来的，不是标准 FedAvg 的 n_k/n。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
