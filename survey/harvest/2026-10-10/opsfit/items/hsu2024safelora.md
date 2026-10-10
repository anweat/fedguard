## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：partial（部分可表达）。** 这条流水线的“计算骨架”（把 LoRA 增量投到一个子空间、逐层算余弦、按分数选层、把选中的层改写掉）基本落在现有函数与普通张量运算里；其中 `update.left_project` 的说明恰好是“对 `B@A` 的输出侧施加 (d_out, d_out) 投影、只改 B、结果保持秩 r、适配同样的因子形状”，正好替代论文里没写清的回写细节。真正卡住的是两头：**输入侧**运行时拿不到任何基座模型权重坐标，**执行侧**没有把 LoRA 合并/写回基座并导出的能力；另外 catalog 缺一个构造正交投影矩阵的通用算子。

逐步摘要：

| 步 | 算子 | 归类 | 关键依据 |
|---|---|---|---|
| 1 | weight_difference | needs_runtime | 逐层相减平凡，但没有“对齐/未对齐基座权重”坐标，`model_handle` 也无导出权重的方法 |
| 2 | orthogonal_projection_matrix | missing_op | 需要求逆/伪逆/QR，catalog 没有；`update.project_onto` 是“投影一个向量”不是“构造投影矩阵” |
| 3 | scaled_gram_matrix | compose | `geometry.gram_matrix` 得 `V V^T`，再除以一行 Frobenius 范数（该函数说明为空，属疑点） |
| 4 | subspace_project_update | compose | 一次 `torch.matmul(Ĉ_i, ΔW_i)`；不想稠密化时可用 `update.left_project`（见第 9 步） |
| 5 | frobenius_cosine_similarity | compose | 两个矩阵各展平成 1×d 行向量后交给 `geometry.cosine_to` |
| 6 | select_layers_by_similarity | compose | `cos < τ` 是逐元素比较；最低 top-K 用取负后的 `sampling.top_k` |
| 7 | replace_update_with_projection | runtime_action | 改写 local_update/uploads 的因子＝`transform_update`，具体可用 `update.left_project(B, Ĉ)` |
| 8 | merge_lowrank_update | needs_runtime | 缺 W^aligned 坐标，也缺“合并进基座并导出”的句柄方法 |
| 9 | refactor_lowrank_update | op | `update.left_project` 就是“只改 B 施加输出侧投影、保持秩 r、形状不变” |
| 10 | residual_subspace_project | needs_runtime | 要读/写两个全参数权重，运行时没有任何权重坐标与写回接口 |
| 11 | inverse_squared_distance_score | compose | 逐层矩阵差、平方和、1/(1+·)、跨层求和，纯普通张量运算 |

三点补充：

- **数据面**：coordinates 只覆盖 **LoRA 因子层**（`received/factors/module`、`local_update/factors/module`、`uploads/factor_delta|product_delta|module_delta/client`、`trace/factors/step`）和若干前向/反向读数，没有任何基座全参数的坐标，`model.lora(state)` 也只是“临时加载”。所以第 1 步无法在运行时构造 V；只有外部把 V（或 Ĉ/C）当常量喂进来，后半条流水线才谈得上表达。`channel/tensor/client` 虽然能传张量，但它是通信/自报制品，用它承载防御方参照权重属于超出词表用法。
- **计算面**：第 2 步的精确版缺算子；第 3 步的近似版可以 compose，二者在论文里是“二选一”，所以是部分阻断而非全阻断。第 4、5、6、11 步都是几行普通运算即可。
- **执行面**：第 7 步能表达（`transform_update` 覆盖 local_update 与 uploads）；第 8、10 步表达不了，因为它们要求基座权重的读、合并与写回，`states.add` 只能做 State 字典层面的 `base + scale*d` 加法，解决不了数据来源与导出。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用缺口（别的方法也会用到）：**

1. `orthogonal_projection_matrix`（建议归入 `spectral_decomposition` 族）：由一组基构造正交投影算子 `P = V (V^T V)^{-1} V^T`（或等价的列空间正交基 Q，使 `P = Q Q^T`）。任何“把更新/权重投到一个子空间再改写”的方法（子空间投影去毒、梯度/激活投影、权重正交化、模型合并里的投影去冲突）都会复用。现有库只有“投影一个向量”（`update.project_onto`/`project_out`）和“取一个主方向”（`spectral.top_direction`），没有“构造投影矩阵”这一步，属可复用的通用能力缺口。
2. **基座模型权重的读取 / 合并 / 写回导出坐标**（needs_runtime）：凡是在权重层而不是 LoRA 因子层工作的防御都要（全参微调后的修补、模型合并、权重剪枝或掩码、SafeLoRA 的全参变体）。这是运行时制品与句柄的能力缺口，不是 SafeLoRA 特有。
3. 旁支缺口：`truncated_svd`（从稠密矩阵截断回秩 r 的因子，族 `spectral_decomposition`）在 LoRA 压缩/合并类方法里是通用的，但本流水线可以靠 `update.left_project` 绕过，所以我没有把它记为某一步的 missing_op，只在第 9 步注明。

**这篇论文特有的（不构成通用缺口）：**

- “用对齐模型与未对齐模型的逐层权重差张成安全对齐子空间”这一构造（V 的来源）是 SafeLoRA 特有的知识，运行时缺的是**数据来源**，不是算子。
- τ=0.35、最低 top-K 替代规则、诊断分 `S = Σ 1/(1+||C_iΔW_i − ΔW_i||²)`、以及“稠密 `CΔW` 如何回到 A、B”（论文未定义）都是这篇文章特有的配方细节；其中只有“回到因子”有通用性，而这已被 `update.left_project` 覆盖，所以这篇论文不强制要求新增任何通用计算单元。
- 按分数选层本身是通用需求，但已经能用 `sampling.top_k` + 比较表达；若将来要自动定阈，`robust.largest_gap_threshold`、`density.kde_valley_threshold`、`robust.quantile_threshold` 已在库里，也不算缺口。

```json
{
  "key": "hsu2024safelora",
  "steps": [
    {
      "n": 1,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "逐层相减本身平凡，但运行时没有『对齐基座模型权重』与『未对齐基座模型权重』的坐标：coordinates 只覆盖 LoRA 因子层（received/factors/module、local_update/factors/module、uploads/*_delta/client、trace/factors/step），model_handle 的 losses/hidden/activations/per_sample_gradients/logprob/generate/lora 都不能导出基座权重，因此 V_i 无法在运行时构造；除非防御方离线算好 V_i 当外部常量注入（词表也不承认这种参照权重坐标）。"
    },
    {
      "n": 2,
      "class": "missing_op",
      "uses": [],
      "missing_name": "orthogonal_projection_matrix",
      "missing_family": "spectral_decomposition",
      "missing_io": "输入：基矩阵 V（d×r，其列张成待投影子空间）；输出：d×d 正交投影矩阵 P = V (V^T V)^{-1} V^T，或等价的列空间正交基 Q（使 P = Q Q^T）。需要解线性方程组/伪逆，或对 V 做 QR/SVD 取正交基。",
      "note": "catalog 没有求逆、QR、SVD（spectral 模块只给 spectral_entropy、effective_rank 这类标量谱量和 top_direction 这单一方向），update.project_onto/project_out 是『把一个向量投到 directions 的行空间』而不是『构造投影算子』，普通张量运算（加减乘、比较、取索引、均值）也不含求逆，故判 missing_op。疑点：理论上可对单位向量逐列调用 update.project_onto 拼出 Ĉ 的每一列，但那是 d 次调用且依赖该函数内部是否正交化（文档未保证），d 为权重维度时不现实，因此不采纳。"
    },
    {
      "n": 3,
      "class": "compose",
      "uses": ["geometry.gram_matrix"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "C_i = V_i V_i^T / ||V_i||_F：geometry.gram_matrix(V_i) 给出 V V^T（(d,d)），再除以一行标量 Frobenius 范数即可，属 catalog 函数加一行普通运算。疑点：该函数说明为空，这里假定它返回 X X^T；若其约定不同，手写 V @ V.T 同样只是一行。论文把这一步与第 2 步列为二选一，它可表达使得精确版缺失只是部分阻断。"
    },
    {
      "n": 4,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "有了 Ĉ_i（或 V_i 的列空间正交基）后，Ĉ_i ΔW_i 就是一次 torch.matmul，属普通张量乘法，不需要新算子。未采用 update.project_onto：它的语义是『把向量投到 directions 的行空间』，对 ΔW 这种被左右双侧作用的矩阵，作用侧与形状语义都不明确。若不想先稠密化，同一结果可由 update.left_project 在因子上直接完成（见第 9 步）。前提是 Ĉ_i 可得，而它依赖第 1、2 步。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": ["geometry.cosine_to"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把 ΔW_i 与 Ĉ_iΔW_i 各自 flatten 成 1×d 的行向量（普通 reshape），再交给 geometry.cosine_to 得逐层余弦，与该函数『每行对一个参考向量的余弦』的说明一致，数值上等于论文的 Frobenius 余弦；也可用 geometry.cosine_matrix 对 2×d 取非对角。注意该函数在零范数处返回 0，τ 比较的边界要自行处理。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": ["sampling.top_k"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "cos_i < τ 是逐元素比较；『cos 最低的 top-K』只需把分数取负成 dict 后交 sampling.top_k（该函数只返回最大的 k 个键，按值降序）。τ 与 top_k 是防御超参而非数据，运行时不提供该坐标但也不构成计算缺口；论文没给 top_k 取值、也没给自动定阈规则，所以不能改判给某个现成阈值函数。"
    },
    {
      "n": 7,
      "class": "runtime_action",
      "uses": ["transform_update", "update.left_project"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "语义是『改写被选中层的更新』：local_update 与 uploads 的 modified_by 都含 transform_update，落在 vocabulary 的动作上成立。具体计算推荐 update.left_project(B_i, Ĉ_i)：按说明它只改 B 就实现 C@(B@A)，结果仍秩 r、因子形状不变，比论文的稠密化路径更贴合 catalog，也顺带解决第 9 步。前提仍是 Ĉ_i 可得（第 1、2 步）。"
    },
    {
      "n": 8,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "需要 W^aligned 这一基座权重制品，并且需要『把（部分投影后的）LoRA 增量合并进基座并导出』的能力。coordinates 里没有任何基座权重坐标，model.lora(state) 只做临时加载，没有合并/导出方法；states.add 只能做 State 字典层面的 base + scale*d，解决不了数据来源与写回。缺的不是算子而是运行时的权重制品与句柄能力。"
    },
    {
      "n": 9,
      "class": "op",
      "uses": ["update.left_project"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "update.left_project 的说明与『写回 A、B』一一对应：对 B@A 的输出侧施加 (d_out,d_out) 投影、只改 B、结果保持秩 r、适配同样的因子形状，因此不需要 SVD 回秩。疑点：论文 Figure 1 只写 ΔW.data = CΔW，未说明稠密化后如何回到秩 r；若严格要求『先稠密化再截断回秩 r』，catalog 没有截断 SVD（属 spectral_decomposition），但这条路径在现有库里可以绕开。"
    },
    {
      "n": 10,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "全参数微调变体要读 W^pre-trained 与 W^fine-tuned 两个完整权重并写回投影残差：运行时既没有基座/全参权重坐标，也没有权重写回接口，而且这是全参数场景而非联邦 LoRA 场景（LoRA 侧只有因子）。计算式 W_pt + C(W_ft − W_pt) 本身只是 compose 级的加减乘，卡点是数据与写回能力。"
    },
    {
      "n": 11,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "S = Σ_i 1/(1+||C_iΔW_i − ΔW_i||²)：逐层做矩阵差、展平后平方和、取倒数加一、跨层求和，全是普通张量运算，不需要新算子，也不依赖论文未给的参数（整模型决策阈值论文没给，属外部超参）。输出是标量诊断值，仅用于决定是否全层投影。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "运行时没有任何 coordinate 或 model_handle 方法能读到『对齐模型 / 未对齐模型』的逐层基座权重，也没有防御方参照权重的坐标，因此 V_i（第 1 步）以及随之而来的 Ĉ_i / C_i 无法在运行时构造；只有外部离线提供 V_i（或直接提供投影矩阵）时，第 3–7、9、11 步才谈得上表达。",
    "把投影后的 LoRA 增量合并写回基座权重并导出（第 8 步）、以及全参数变体的权重投影（第 10 步）所需的基座权重读取与写回导出能力在运行时缺失。",
    "catalog 缺少通用的正交投影矩阵构造算子（矩阵求逆/伪逆/QR），第 2 步无法由现有函数完成；该项可被第 3 步的近似 C 或外部提供的列空间正交基绕过，因此只是部分阻断。"
  ]
}
```
