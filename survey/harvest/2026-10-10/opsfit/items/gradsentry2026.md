## 1. 这条流水线整体上能否由现有算子库与运行时表达

这是一条**纯客户端（`client_pre_train`）、样本级净化**的链路：用基座 `lm_head.weight` 的逐样本梯度矩阵做谱分析，再按谱熵密度把样本分成干净/投毒两簇，最后剃掉投毒样本。它不碰聚合、不碰通信、不改损失、不改更新，所以运行时覆盖度其实相当高：

- **取数齐备**：`samples/gradient/sample`（`via: model_handle`）与 `model.per_sample_gradients(samples, group)` 正好对应第 2 步；`samples/manifest|text/sample` 保证能把掩码落回数据集。
- **动作齐备**：第 9 步就是 `samples` 制品的 `mask_samples`，在受控动作表里存在。
- **统计件齐备**：第 7、8 步几乎是一比一命中——`density.silverman_bandwidth` 就是 h = 1.06·σ̂·N^(−1/5)，`density.kde_valley_threshold(x, 0.0, 1.0, fallback=0.7)` 就是"最外侧两峰之间的密度谷底 + 0.7 回退"；第 6 步的 H 由 `density.shannon_entropy` 给出，只差一个 `/log k`；第 5 步归一化是几行 clamp/求和/除法。
- **两个真正的缺口**：第 4 步的**未中心化截断 SVD（只要 top-k 奇异值）**在 catalog 里没有对应算子（`spectral.*` 只暴露熵/有效秩/主方向，`transform.pca` 会中心化且只给 explained variance ratio）；第 1 步的**训练插桩（对指定模块开启梯度）**没有任何 catalog 函数或模型句柄方法覆盖，且不在 vocabulary 的动作表里。

因此结论是 **partial**：9 步里 7 步现有能力即可表达，1 步缺一个通用算子，1 步缺运行时插桩能力。缺的两点都不改变方法的性质，都是可以补上的通用件。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用缺口（别的方法也会用到）：**
1. **不中心化的截断/随机 SVD（top-k 奇异值）**——`spectral_decomposition` 族的通用单元。任何"对梯度矩阵/更新矩阵做谱签名"的方法（spectral signatures、FLDetector 类谱检测、有效秩分析、低秩结构检测）都要用；现有 `lowrank.gram`/`lowrank.kappa` 只做内积与冗余度，`transform.pca` 会中心化，都替代不了。值得强调疑点：`spectral.spectral_entropy` 名字上最像第 6 步，但它按**奇异值平方**归一化，论文按**奇异值本身**归一化，二者数值不同，不能因为名字相似就算作 op。
2. **训练插桩：按模块/参数组开启（或临时解冻）梯度**——`per_sample_gradients`、逐样本梯度裁剪、influence function、data attribution、TracIn 一类方法都会需要。它更像运行时能力（框架开关），不是可复用算子，所以记 `needs_runtime`。

**论文特有、但不需要新算子（现有件 + 普通运算即可）：** `lm_head.weight` 的左上 `1/8 × 1/8` 分块（普通切片）、k = 16、σ 而非 σ² 的归一化、`H/log k` 的 [0,1] 归一化、KDE + Silverman 带宽 + 谷底阈值 + 0.7 回退、只在训练前对本地样本做掩码。这些都是超参与组合选择，不是计算单元缺口。另外，这条流水线**刻意不需要**服务端聚合、跨客户端通信、密码学、改损失、逐样本梯度裁剪——所以这些都不构成缺口。

```json
{
  "key": "gradsentry2026",
  "steps": [
    {
      "n": 1,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "catalog 与 model handle 都没有『对指定模块/参数组开启梯度（临时解冻基座 lm_head.weight）』的接口，vocabulary 的 modified_by 动作表也没有对应项。缺的是训练插桩能力：按模块设置 requires_grad，并在其开启后仍能按参数组取逐样本梯度。疑点：若 model.per_sample_gradients(samples, 'lm_head.weight') 本身能对 requires_grad=False 的参数求导，则此步被运行时隐式覆盖，可降级为 outside（普通本地训练配置）。"
    },
    {
      "n": 2,
      "class": "runtime_data",
      "uses": ["samples/gradient/sample", "model.per_sample_gradients"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "逐样本梯度由模型句柄直接提供（coordinate samples/gradient/sample，via: model_handle；方法 model.per_sample_gradients(samples, group)）。说明写明是 per-sample 而非 batch 平均，符合 reduction=none。返回是展平的，reshape 回 v×d 属普通形状操作，不影响归类。"
    },
    {
      "n": 3,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "G_i[:v//8, :d//8] 就是基础切片/取索引，落在 compose 定义里明列的『取索引』，无需新算子。catalog 无对应函数，但也谈不上 missing_op。"
    },
    {
      "n": 4,
      "class": "missing_op",
      "uses": [],
      "missing_name": "truncated_svd",
      "missing_family": "spectral_decomposition",
      "missing_io": "输入 X (m×n 张量，不中心化)、k (int)、可选 oversamples/iters（randomized SVD 参数）；输出降序的 top-k 奇异值 sigma (k,)，可选 U (m×k)、V (n×k)",
      "note": "严格按说明判断：catalog 没有返回奇异值的函数。transform.pca 只给 explained variance ratio，且标准 PCA 会先中心化——对梯度矩阵会移除均值/秩一主方向，谱与未中心化截断 SVD 明显不同，绝对奇异值也无法还原；spectral.spectral_entropy / effective_rank 用的是奇异值平方归一化，语义不同，不能因名字相似算作 op。随机化只是实现手段，可复用单元是『未中心化的 top-k 奇异值』。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "p_j = max(sigma_j, 1e-12) / sum_l max(sigma_l, 1e-12)：clamp/min + 求和 + 逐元素除法即可，catalog 里没有归一化函数但也不需要新通用算子。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": ["density.shannon_entropy"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "density.shannon_entropy(P) 直接给出 H = -sum p log p（nats；它内部再归一化一次，对已归一化的 P 无影响），再除以 log k 得到 H_bar 属于一行普通乘法/除法，因此是 compose 而非纯 op。"
    },
    {
      "n": 7,
      "class": "op",
      "uses": ["density.gaussian_kde", "density.silverman_bandwidth"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "density.silverman_bandwidth 的定义 h = 1.06*std*n^(-1/5) 与论文的 Silverman 带宽完全一致；density.gaussian_kde(x, grid, bandwidth) 在给定 grid 上给出 g_hat。注册说明：density.kde_valley_threshold 内部会自行估 KDE，所以运行时第 7 步可与第 8 步合并执行，但 g_hat 本身仍可由这两个函数表达。"
    },
    {
      "n": 8,
      "class": "op",
      "uses": ["density.kde_valley_threshold"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "签名与语义对应：在 [lo, hi] = [0,1] 上取最外侧两峰之间的密度极小点，fallback 参数正好放 0.7；说明中的 'outermost two peaks' 与论文 x_L（最靠近 0 的峰）、x_R（最靠近 1 的峰）一致，返回 (threshold, bimodal) 中 threshold 即 tau。"
    },
    {
      "n": 9,
      "class": "runtime_action",
      "uses": ["mask_samples"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "保留 H_bar_i <= tau 的样本就是对 samples 制品做掩码，vocabulary 中 samples 的 modified_by 含 mask_samples，动作存在。也可写成布尔索引的 compose，但受控动作表已直接提供该动作，故记 runtime_action。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "第 4 步缺少不中心化的截断/随机 SVD（top-k 奇异值）算子：现有谱函数只暴露 spectral_entropy/effective_rank/top_direction，transform.pca 会中心化且只返回 explained variance ratio，无法得到论文所需的未中心化奇异值谱。",
    "第 1 步缺少训练插桩能力：运行时未暴露对指定模块/参数组开启（或解冻）梯度的手段；若 model.per_sample_gradients 能对冻结的 lm_head.weight 求导，则该阻塞不成立。"
  ]
}
```
