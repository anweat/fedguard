## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：可以完整表达（expressible = full）**。没有任何一步需要新增通用算子，也没有一步受限于运行时拿不到的数据或做不了的动作。逐步映射如下：

| 步 | 归类 | 落点 |
|---|---|---|
| 1 下发全局因子、冻结 W0 | outside | 标准下发；运行时落点 `outgoing/factors/recipient` / `transform_broadcast`，本地初始化只是复制因子 |
| 2 服务器抽样客户端 | op | `sampling.subsample(N, floor(qN), rng)` 语义完全吻合 |
| 3 抽本地 mini-batch | op | `sampling.subsample(R, floor(bR), rng)`；R 取自 `samples/manifest/sample` |
| 4 对活跃因子逐样本求梯度 | runtime_data | `model.per_sample_gradients(samples, group)`，坐标 `samples/gradient/sample`；group 取当前活跃因子，冻结因子不求梯度 |
| 5 逐样本 ℓ2 裁剪 | compose | 逐样本梯度 + 逐样本范数/clamp/缩放；阈值 C 可用 `robust.coordinate_median` 作用在 `(n,)` 范数向量上 |
| 6 批内求和 + 高斯加噪 | compose | 普通加法 + `update.add_gaussian_noise(state, C·σ/(bR), generator)` |
| 7 一维二项式低通滤波 | op | `sequential.lowpass_1d`，taps=5 ↔ [1,4,6,4,1]/16；A 取 dim=1（逐行）、B 取 dim=0（逐列） |
| 8 单侧因子更新 | outside | 普通本地 SGD/AdamW 参数更新，由客户端训练循环承担 |
| 9 上传本地因子 | outside | 标准上传流程，制品 `local_update/factors/module` |
| 10 分别平均 A、B 并组装 | outside | 标准 FedAvg；`states.weighted_average` 直接可做，组装是两行矩阵乘加 |

关键判断点（都不构成阻塞，但决定了归类）：

- **步 5、6 为什么不是 op**：catalog 里 `update.clip_and_noise` 的说明明确写着 "Applied to a batch gradient this bounds the batch's contribution, not each sample's"——它做的是**联合**裁剪到 `bound`，噪声尺度还是 `sigma*bound/denominator`。步 6 若直接调用它，会在逐样本裁剪之外再把批和裁一次（批和范数上界是 bR·C，会被错误地压到 C），并把噪声尺度绑死在 bound 上。`update.clip_state_norm` / `update.clip_to_norm` / `update.scale_to_norm` 都是整个 `State` 级，不区分样本，同样不能用。所以步 5/6 只能靠 catalog 函数 + 普通张量运算拼 → compose。
- **步 5 为什么不是 needs_runtime**：needs_runtime 的判据是"拿不到要的数据 / 做不了要的动作"。这里逐样本梯度是模型句柄方法直接提供的（步 4 已归 runtime_data），裁剪只是逐样本范数 + `max(1, ‖g‖/C)` 缩放，属普通张量运算，两项判据都不成立。
- **形状衔接**：`model.per_sample_gradients` 返回的是 flattened 梯度，而滤波需要 (r,n)/(m,r) 的行列结构，用 `states.unflatten(vector, like=State)` 还原即可，属现有函数。
- **交替调度/冻结**：属客户端训练循环的控制逻辑（只对活跃因子的参数组取梯度、只对活跃因子做 step），运行时能表达，不是算子问题。

遗留疑点（不影响 full）：`sequential.lowpass_1d` 的说明把 padding 写成 "symmetric (reflect)"，与论文明确写的 symmetric 在边界一拍上有差异，严格复现需核对；`sampling.subsample` 需要调用方自备 `np.random.Generator`，坐标表未列随机源，但这是普通本地随机数；步 5 的 C 由本地批中位数得到，本身是数据相关、未加噪的（这是论文设定，不是表达性问题）。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

严格按 catalog 判断，这条流水线**没有真正的 missing_op / needs_runtime**。以下是"接近缺口"的项，按通用性分类：

**通用（别的方法也会用到，但不构成本流水线的缺口）**

- **逐样本梯度裁剪单元**（若沉淀为算子，建议 `per_sample_gradient_clip`：输入 (n,d) 逐样本梯度与阈值 C（可逐层），输出裁剪后梯度与每样本缩放系数；族 optimization 或 robust_statistics）。DP-SGD / DP-FedAvg / DP-LoRA 一族普遍需要，本流水线用现有张量运算拼出，所以没有硬缺。
- **隐私核算（privacy accounting，σ ↔ (ε,δ) 换算）**：任何 DP 方法都要，但本流水线把 σ 当超参直接给出，换算属离线准备（outside），catalog 里也确实没有这个算子。
- **二项式/高斯低通滤波**：本库已有 `sequential.lowpass_1d`；DP 后处理、模型压缩、频域防御等都用得上，属通用件。
- **逐样本梯度的形状还原与范数统计**：`states.unflatten`、`robust.coordinate_median` 已覆盖，属通用件。

**这篇论文特有的（都只是编排/参数，不是新的计算单元）**

- 交替单侧因子更新的调度：奇数步只更新 B、偶数步只更新 A，另一因子冻结；
- 只对活跃因子求逐样本梯度，并把低通滤波**按因子方向**施加（A 逐行、B 逐列）；
- 裁剪（C 取层内范数中位数）→ 加噪（C·σ/(bR)）→ 低通滤波 → 因子级平均 的这条串联顺序与超参组（σ_s、核抽头、K=20）。

这些的方法特异性体现在"调度 + 参数 + 串联顺序"，其组成部分（抽样、逐样本梯度、范数裁剪、高斯加噪、二项式低通、因子平均）在库里都有或能由几行张量运算拼出，因此不需要为它们新增可复用算子；反过来，如果库想把 DP 能力做扎实，第 1 条（逐样本裁剪）才是值得补的通用算子——补上之后本流水线的步 5 会从 compose 升为 op，但可表达性结论不变。

```json
{
  "key": "rethinklora2026",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": ["outgoing/factors/recipient", "transform_broadcast"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "标准 FL 下发与本地初始化：把上一轮全局因子作为本地初始值、主干 W0 冻结，不属于防御计算本身。运行时落点是 outgoing/factors/recipient 坐标与 transform_broadcast 动作；本地初始化只是复制因子，不需要任何算子。"
    },
    {
      "n": 2,
      "class": "op",
      "uses": ["sampling.subsample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "sampling.subsample(n, k, rng) 的语义（n 个里取至多 k 个下标）与'每轮抽 floor(qN) 个客户端'完全吻合：n=N、k=floor(qN)。疑点：签名要求调用方自备 np.random.Generator，坐标表未列随机源，但这是普通本地随机数，不算缺数据。"
    },
    {
      "n": 3,
      "class": "op",
      "uses": ["sampling.subsample", "samples/manifest/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "本地 mini-batch 抽样同样是 sampling.subsample(R, floor(bR), rng)；本地规模 R 可从 samples/manifest/sample 读到。若论文改成按类别分层抽样，应换 sampling.stratified，但当前描述只要求按规模等概率抽。"
    },
    {
      "n": 4,
      "class": "runtime_data",
      "uses": ["samples/gradient/sample", "model.per_sample_gradients"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "逐样本梯度由模型句柄方法直接提供：model.per_sample_gradients(samples, group)，group 取当前活跃因子（奇数步 B、偶数步 A），冻结因子不取梯度。对应坐标 samples/gradient/sample（via: model_handle）。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": ["model.per_sample_gradients", "robust.coordinate_median"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "catalog 没有逐样本裁剪算子：update.clip_and_noise 的说明明确它裁的是批的联合贡献、不是逐样本；clip_state_norm/clip_to_norm/scale_to_norm 都是整个 State 级。但逐样本梯度已由 model.per_sample_gradients 给出，裁剪即逐样本 L2 范数 + max(1, ||g||/C) 缩放，几行张量运算即可；阈值 C='该层梯度范数分布的中位数'可用 robust.coordinate_median 作用在 (n,) 范数向量上（坐标唯一，即标量中位数，偶数时取中间两者均值）。疑点：若坚持要一个可复用的逐样本裁剪单元，可另立 missing_op（如 per_sample_gradient_clip，optimization/robust_statistics 族），此处按 compose 的定义归 compose。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": ["update.add_gaussian_noise"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "批内求和是普通张量加法（或 states.add），噪声尺度取 C·σ/(bR)，加噪由 update.add_gaussian_noise(state, sigma=C·σ/(bR), generator) 直接完成。不能用 update.clip_and_noise：它会先做 bound=C 的联合裁剪（把已逐样本裁剪的批和再缩小），且噪声尺度绑定 bound，与论文的 (1/(bR))·Σg + (C/(bR))·N(0,σ²) 不符。"
    },
    {
      "n": 7,
      "class": "op",
      "uses": ["sequential.lowpass_1d", "states.unflatten"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "sequential.lowpass_1d 就是二项式低通：taps=5 对应 [1,4,6,4,1]/16，与论文主核一致；alt_kernels 的 [1,2,1]/4、[1,6,15,20,15,6,1]/64 对应 taps=3/7。A 为 r×n 逐行滤波取 dim=1，B 为 m×r 逐列滤波取 dim=0，每步两次调用。前置：model.per_sample_gradients 给的是 flattened 梯度，需先用 states.unflatten 还原成 (r,n)/(m,r) 才有行列结构。疑点：函数说明的 padding 写作 'symmetric (reflect)'，与论文写的 symmetric 在边界一拍上不同，严格复现需核对。"
    },
    {
      "n": 8,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "标准本地优化器步（视觉 SGD、语言 AdamW），只对活跃因子做 step、另一因子冻结，属普通本地训练，由客户端训练循环承担；catalog 不提供也不需要新的防御算子。'k 奇偶决定更新 B 还是 A'属训练循环的控制逻辑，不是计算单元。"
    },
    {
      "n": 9,
      "class": "outside",
      "uses": ["local_update/factors/module"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "标准上传动作：把训练结束的本地因子（已裁剪、加噪、滤波）发给服务器，不属于防御计算。运行时制品落在 local_update/factors/module，服务器侧读 uploads/factor_delta/client。"
    },
    {
      "n": 10,
      "class": "outside",
      "uses": ["states.weighted_average"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对 A、B 分别做等权算术平均就是标准 FedAvg，states.weighted_average（权重 1/|Ct|，'FedAvg in factor space'）可直接完成；组装 W0 + s·B·A 是两行矩阵乘加。按分类规则标准 FedAvg 聚合归 outside，故不计为 op，但表达上不需要任何新东西。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
