## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：partial（前段能算，末段落不了地）。**

逐步看：

- **第 1 步（前向激活范数采集）**：本质是"取数据"。运行时的模型句柄有 `model.activations(samples, select)`，对应坐标 `samples/activation/sample`（`via: model_handle`，逐样本粒度）。线性层的输入激活就是它所选子模块的输出，因此"逐坐标激活"这一原始数据是拿得到的。但要注意两点：一是该坐标是**逐样本**粒度，论文要的是**逐权重坐标**的范数统计，中间要补一次对样本维的 L2 范数 + 均值，这是几行普通张量运算，属 compose 级；二是论文的 `activation_source`（层/归约维度）未说明，选哪一层做 `select` 只能自行约定。
- **第 2 步（Wanda 分数）**：`h_j = |w_j| · (1/|D|)Σ_x ‖A_j(x)‖₂`，就是取绝对值、逐元素相乘、对样本维求均值。catalog 里没有对应算子：`states.norm` 是整个 State 的范数，`density.*`/`spectral.*`/`robust.*` 的范数要么是逐客户端、要么是整体量，都不是"逐坐标"。→ **compose**。
- **第 3 步（按比例 top-k 二值掩码）**：排序/取索引 + 比较 + 0/1 转换，几行即可，逐层做还是全局做只是循环差别。catalog 里的 `sampling.top_k(scores: dict, k)` 是给"客户端→分数"的字典返回键，**不是与权重同形的坐标掩码**，名字像但不算 op；`robust.quantile_threshold`、`density.kde_valley_threshold` 的语义（FPR 分位、密度谷）也不对应 mask ratio。→ **compose**。
- **第 4 步（掩码剪枝并写回）**：**硬阻塞**。算术本身平凡（`(1-m)⊙w`），缺的是运行时的坐标空间和动作空间：
  - **坐标**：运行时的模型侧制品只有 LoRA 因子（`received/factors/module`、`local_update/factors/module`、`aggregate/result/model`、`outgoing/factors/recipient`），**没有任何坐标给出合并权重 `W₀+BA` 或基座权重**。论文的 `w_j`、掩码、`|w_j|` 全都定义在全权重坐标上。
  - **动作**：`aggregate` 的可用动作只有 `replace_global`（安装聚合结果）与 `select_and_weight`（按权重挑选），`outgoing` 只有 `transform_broadcast`（下发），都没有"对全局权重按坐标置零/稀疏化并写回"的语义。词表 `tactics` 里有 `repair`（聚合之后），但制品动作表里没有与之对应的实现，这一步正好卡在这个空档上。catalog 里最接近的 `update.project_out` / `update.left_project` 是沿**给定方向**做子空间投影/输出侧投影，不是坐标置零，方向也未知，不能当剪枝用。
  - 若把掩码"搬到" B/A 因子上做适配，语义并不等价：因式分解非唯一，掩码结果依赖具体分解；且 `(1-m)⊙(W₀+BA) ≠ W₀+(1-m)⊙BA`，也不等于对因子掩码。
- **第 5 步（导出可部署模型）**：序列化/部署工序，不属防御计算本身（论文连稀疏格式都没定，加速留作 future work）。→ **outside**；但它依赖第 4 步的产物，所以实质阻塞仍在第 4 步。

另外，这篇方法是**集中式的微调后一次性剪枝**（无再训练、无联邦交互），塞进这个联邦 LoRA 运行时后最贴近的挂点是"服务器聚合后修复"，而运行时恰恰在这一环缺坐标与动作。因此：重要性与掩码这一套"决策"能算出来，"执行剪枝并产出 re-aligned 模型"这一环表达不了 —— 判 **partial**，不判 full，也不判 no。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用缺口（别的方法同样会遇到）**

1. **权重级坐标 + 对全局模型做坐标级掩码/剪枝后写回的能力**。这是任何"全权重剪枝、稀疏化、模型手术、掩码式合并（TIES/DARE 类）、定位到权重后清零"的方法都需要的。当前运行时只在 LoRA 因子上读写，且 `aggregate`/`outgoing` 的动作里没有 sanitize/prune 语义。若要最小补齐，通用单元可命名 `state_coordinate_mask`（族：transform；输入：`State`（或展平向量）+ 布尔掩码/保留比例，输出：掩码后的 `State`），但它只解决"写回形式"，解决不了"掩码定义在合并权重上"。
2. **服务器侧/防御方可信参考集的坐标**。`trust` 里有 `reference_data`，但 `coordinates` 里 `samples/*` 全部挂在客户端制品上，没有防御方参考集的清单/文本/激活/损失取法。凡是要校准集的方法（后门检测的阈值标定、`sequential.reference_z` 的 center/scale、`robust.quantile_threshold` 的 benign 样本）都会碰到同一个洞。
3. **逐坐标的激活统计约定（逐样本激活 → 与权重同形的统计量）**。剪枝/重要性类方法（Wanda、SparseGPT、magnitude、各类 activation-based 打分）通用。本步只需 abs/mean/mul，属 compose 级，**不必新增通用算子**，但"逐层输入激活 ↔ 权重行列坐标"的对齐约定值得在 KB 里固化，否则每次都要靠论文外的默认假设。

**这篇论文特有的部分**

- Wanda 的分数形式 `|w_j|·(1/|D|)Σ‖A_j(x)‖₂`、`α=0.2 / 0.05`、一次性不恢复、以 harmful 对齐数据 `D_realign`（2000 条）作参考集、`|D|=0` 退化成 `|w_j|` ——都是公式与参数组合，用现成张量运算即可，**不构成通用缺口**。
- "微调后剪枝权重以移除有害能力"这一防御定位（post-fine-tuning one-shot pruning）以及随之而来的稀疏导出格式，是论文自身的用法；是否需要为"权重级 sanitize/repair"新开一类动作，是 KB 架构层面的通用决策，而不是 Wanda 特有的算法需求。
- 论文两处未说明（激活取自哪些层/如何归约、全局 top-k 还是逐层 top-k）属于**信息不足的歧义**，不是能力缺口：两种情况用普通张量运算都能写，只是结果不同。

```json
{
  "key": "huang2024antidote",
  "steps": [
    {
      "n": 1,
      "class": "runtime_data",
      "uses": ["samples/activation/sample", "model.activations"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "前向激活由模型句柄 model.activations(samples, select) 提供，坐标 samples/activation/sample（via: model_handle，逐样本粒度）。两点保留：(1) 要得到论文的逐坐标范数还需对样本维做 L2 范数+均值，属几行普通张量运算；(2) 该坐标挂在客户端 samples 制品上，而本步属 server_post_aggregate，服务器侧的 D_realign（2000 条 harmful 配对）在 coordinates 中没有对应取法（只能依赖 trust.reference_data 的隐含假设），若严格要求服务器侧执行，本步同样做不了。论文未说明 activation_source（层/归约维度），选层方式需自行约定。"
    },
    {
      "n": 2,
      "class": "compose",
      "uses": ["samples/activation/sample", "aggregate/result/model"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "h_j=|w_j|·mean_x‖A_j(x)‖₂ 就是 abs、逐元素乘、对样本维求均值，catalog 无对应算子（states.norm 是整个 State 的范数；density/spectral/robust 的范数不是逐坐标量）。疑点：|w_j| 需要权重坐标，而运行时模型侧只有 LoRA 因子（aggregate/result/model、received/factors/module），没有合并权重/基座权重坐标，只能近似地把因子元素当 w_j，坐标空间与论文不一致，故这一步的\"能算\"只对因子版本成立。"
    },
    {
      "n": 3,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "按比例 α 取 top-k 生成 0/1 掩码＝排序/取索引+比较+数值转换，几行即可，全局或逐层只是循环差别。catalog 的 sampling.top_k(scores: dict, k) 作用于 {客户端: 分数} 字典并返回键，不是与权重同形的坐标掩码，名字相似但不算 op；robust.quantile_threshold 的语义是按 benign FPR 取分位，不是 mask ratio，也不适用。mask scope（全局 vs 逐层）论文未说明，属歧义而非能力缺口。"
    },
    {
      "n": 4,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "掩码算术本身平凡（(1-m)⊙w），缺的是运行时通道：模型侧只有 LoRA 因子坐标，拿不到合并权重 w（含基座权重）；aggregate 的可用动作只有 replace_global / select_and_weight，outgoing 只有 transform_broadcast，都没有\"对全局权重按坐标置零/稀疏化并写回部署\"的语义（tactics 有 repair，但制品动作表里没有对应实现）；catalog 中最近的 update.project_out / update.left_project 是子空间投影，不是坐标掩码。疑点：若把 replace_global 宽松理解为\"服务器可安装任意自己产出的全局 State\"，并接受把掩码搬到 B/A 因子上，则本步可退化为 compose+replace_global；但因子分解非唯一，掩码结果依赖分解，且 (1-m)⊙(W₀+BA) ≠ W₀+(1-m)⊙BA，与论文不等价，故按严格读法归 needs_runtime。"
    },
    {
      "n": 5,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "导出/序列化可部署模型属部署工序，不是防御计算本身；论文也未指定稀疏格式（加速留作 future work）。实质阻塞在第 4 步：没有可写出的剪枝后权重，导出无从谈起。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "运行时没有合并权重/基座权重的坐标（模型侧只有 LoRA 因子：received/factors/module、aggregate/result/model 等），而 Antidote 的重要性分数与掩码都定义在全权重 w 的坐标上；对因子做掩码与 (1-m)⊙w 不等价。",
    "aggregate 只有 replace_global / select_and_weight、outgoing 只有 transform_broadcast，词表里没有对聚合后全局权重做坐标级剪枝（置零/稀疏化）并写回部署的动作，因此第 4 步的 re-aligned 模型在运行时里产不出来，第 5 步随之落空。",
    "（条件性）本方法阶段是 server_post_aggregate，但 coordinates 里的 samples/* 全部挂在客户端制品上，服务器侧没有可信 re-alignment 参考集的坐标；若严格要求服务器侧执行，第 1 步的 D_realign 也无处可取，只能依赖 trust.reference_data 的隐含假设。"
  ]
}
```
