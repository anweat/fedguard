## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：整体可以表达（full），FLTrust 的防御内核在现有 catalog 里几乎逐条对得上。**

- FLTrust 真正属于自己的计算是第 4–7 步，它们全部落在现成算子上：
  - 第 4 步余弦打分 = `geometry.cosine_to(X, ref)`（每行到一个参考向量的余弦，正是 `cos(gi,g0)`；用 `states.stack` 把各客户端更新堆成行）。
  - 第 6 步"把本地更新缩放到服务器更新的 L2 范数" = `update.scale_to_norm(state, base, target)`，其说明里直接写了 *FLTrust-style normalization*，语义完全一致（`target` 由 `states.norm` 取 `||g0||`，`state` 先用 `states.add(w, gi)` 组出来）。
  - 第 7 步信任分加权平均 = `states.weighted_average(states, weights)`（逐项加权平均，即除以权重和，与 `Σ TSi·ḡi / Σ TSi` 相同）。
- 第 5 步 ReLU 截断在 catalog 里没有同名函数，但 `torch.clamp(c, min=0)` 一行即可，属 **compose**，不需要新算子。
- 第 8 步 `w + α·g` 与 `states.add(base=w, d=g, scale=α)` 精确对应（论文原式是 `w − α·g`，把 `scale` 取 `-α` 即可）。
- 第 1 步的下发对应 vocabulary 的 `outgoing` 制品与动作 `transform_broadcast`（`outgoing/factors/recipient` 给出按接收方的待下发因子），客户端抽样可用 `sampling.subsample`（本例 `tau = n`，等于全选）。第 2 步客户端本地 SGD、第 3 步服务器在根数据上的参考 SGD 都是普通本地训练，属常规 FedAvg 骨架。

**需要适配但不构成缺失的疑点：**
1. 论文在 d 维全参数向量上定义余弦与范数，而运行时是 LoRA 因子。要把更新比成向量，得用 `states.flatten`/`states.stack` 展平（因子空间余弦），或改用 `uploads/product_delta/client` 配合 `lowrank.gram` 在乘积空间算内积（属 compose）。
2. `g0` 必须与 `gi` 同形才能取余弦；参考更新由服务器侧训练得到，其形状/切分方式要与客户端上传一致。
3. 权重和为 0 的边界（所有 `TSi = 0`，即全部余弦为负）`states.weighted_average` 没有回退约定，需调用方自行判断（论文参考实现有单独分支）。
4. vocabulary 里没有"服务器侧根数据集"的 coordinate，也没有优化器步进接口，所以第 3 步的参考更新只能在运行时之外（防御方训练框架里）算好再交给插件；这被 "outside" 覆盖，不影响整体可表达性。

## 2. 缺的东西里哪些是通用的（别的方法也会用到），哪些是这篇论文特有的

**严格意义上"缺的通用算子"：没有。** 这条流水线不需要任何 catalog 之外的可复用计算单元。

- **通用但只是"没做成算子"的部分：**
  - ReLU 截断（`max(c,0)`）：所有基于余弦/相似度打分的信任方法（FLTrust 系、各类 similarity-based 加权）都会用，但一行张量运算即可，归 compose 足够，不必新增算子。
  - 按参考范数重标定、可信权重平均：语义通用（任意 reference-based 归一化、任意权重 FedAvg），而且已经以 `update.scale_to_norm`、`states.weighted_average` 的形式存在——`scale_to_norm` 名字里带 FLTrust，但它的接口（把 delta 缩放到目标范数）是通用的。
- **通用但运行时不提供的"动作"：** 在防御方持有的可信参考数据上跑一遍本地训练、得到参考更新 `g0`。这是所有 reference/auxiliary-data 型防御（FLTrust、FLDetector、各类"根数据集/公开数据校准"方法）共用的基础设施，不是本论文特有；vocabulary 既无服务器侧数据读取坐标，也无训练步进接口，只能在插件之外完成。按分类定义属 outside，因此不构成 blocking。
- **这篇论文特有的：** 只有"`cos → ReLU → 按 ||g0|| 重标定 → 以 TS 为权重平均`"这条**串联流程**本身。若将来想固化成单个算子，可命名为 `trust_score_weighted_average`（输入：候选更新矩阵 + 参考更新向量；输出：加权后的聚合更新向量；族：robust_statistics 或 optimization），但目前其每个组件都已存在，属于"编排"而非"缺失"。`root_size = 100`、`α` 的取值与 1500/1750 轮衰减计划是超参，不是算子缺口。

```json
{
  "key": "cao2020fltrust",
  "steps": [
    {
      "n": 1,
      "class": "runtime_action",
      "uses": ["transform_broadcast", "sampling.subsample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "抽样 tau 个客户端可用 sampling.subsample(n, tau, rng)（本例 tau=n 即全选）；下发本身是 outgoing 制品上的动作 transform_broadcast，接收方视角的待下发因子由 coordinate outgoing/factors/recipient 给出。若按“标准 FedAvg 基础设施”口径，这一步也可归 outside；按动作口径归 runtime_action。"
    },
    {
      "n": 2,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "客户端本地 SGD 属普通本地训练，不计入防御计算；运行时只提供 model.per_sample_gradients / model.losses 这类读取，没有优化器。训练产物可从 local_update/factors/module 或 uploads/factor_delta/client 读到。"
    },
    {
      "n": 3,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "服务器在根数据 D0 上做与客户端同构的一次 SGD，计算上是普通本地训练/独立参考模型训练（outside）。疑点：vocabulary 没有服务器侧根数据集的 coordinate，也没有训练步进接口，g0 只能在插件外的训练框架里算好传入；防御方持有参考数据是 trust 中 reference_data 明确承认的前提，故不算 blocking。"
    },
    {
      "n": 4,
      "class": "op",
      "uses": ["geometry.cosine_to", "states.stack", "states.flatten"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "geometry.cosine_to(X, ref) 一次给出每行对单个参考向量的余弦，正对应 ci=<gi,g0>/(||gi||·||g0||)；LoRA 更新先用 states.stack/states.flatten 展平成 (tau, d) 行。若论文的余弦意在乘积空间 BA 上比较，可改用 uploads/product_delta/client + lowrank.gram 自算内积（属 compose），不影响本步可做。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "catalog 无 relu/clip 类函数，故不算 op；TS=max(c,0) 用 torch.clamp(c, min=0)（或 (c+|c|)/2）一行完成，属普通张量运算，不需要新通用算子。"
    },
    {
      "n": 6,
      "class": "op",
      "uses": ["update.scale_to_norm", "states.norm", "states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "update.scale_to_norm 的说明明确写了 FLTrust-style normalization：把 delta=state−base 缩放到恰好 target 范数，零 delta 保持不动；target=||g0|| 由 states.norm 取，输入 state 先用 states.add(base=w, d=gi) 组出。与 (||g0||/||gi||)·gi 等价。"
    },
    {
      "n": 7,
      "class": "op",
      "uses": ["states.weighted_average"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "weights=TSi，函数做逐项加权平均（即除以权重和），与 Σ TSi·ḡi / Σ TSi 一致。疑点：全部 TSi=0 时权重和为 0，该函数没有回退约定，需调用前自行判断（论文参考实现另有分支）。"
    },
    {
      "n": 8,
      "class": "op",
      "uses": ["states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "states.add(base=w, d=g, scale=α) 即 w+α·g；论文原式是 w−α·g，把 scale 取 −α 即可。这一步同时是标准 FedAvg 式全局更新（也可算 outside），写回全局模型可用 coordinate aggregate/result/model 与动作 replace_global，但计算本身由 states.add 完成。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
