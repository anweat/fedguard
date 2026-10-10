## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：可以完整表达（full）。** 这条流水线的防御核心恰好是 catalog 里已经按论文校准过的两个算子，其余步骤都能落到运行时的坐标、快照动作或联邦骨架里。

逐步对照：

| 步 | 关键计算 | 可用件 | 判定 |
|---|---|---|---|
| 1 | 下发 w^t | `outgoing/factors/recipient`（写入由 `transform_broadcast` 完成） | 骨架，无防御改动 |
| 2 | g_i(w^t)=∇F_i(w^t) | `gradients/batch_gradient/parameter`、`model.per_sample_gradients` | 取数据 |
| 3 | 不过滤地收成 G∈R^{m×d} | `uploads/roster/client`、`uploads/module_delta/client`，配 `states.stack/flatten` 拼矩阵 | 取数据 |
| 4 | 逐坐标中位数 | `robust.coordinate_median` | 现成算子 |
| 5 | w^{t+1}=Π_W(w^t−ηg) | `states.add(base=w, d=g, scale=−η)` + `update.clip_state_norm` | 现成算子 |
| 6 | 逐坐标截尾均值 | `robust.trimmed_mean`（同为 Yin et al. 2018） | 现成算子 |
| 7 | 本地 ERM 求解 | 运行时训练循环 | 普通本地训练 |
| 8 | 对 ŵ_i 逐坐标中位数 | `robust.coordinate_median` | 现成算子（同 4，输入换成完整本地模型） |

两个必须写清的细节，但它们不构成阻塞：

1. **第 4/8 步的算子逐字对应**：`robust.coordinate_median` 的说明里明确写了 "Yin et al. 2018"，并且连"偶数个客户端取中间两值均值（而非 `torch.median` 的下中位）"这一约定都与论文的 med{·} 一致；输入正好是 (m, d) 行堆叠，输出 (d,)。`robust.trimmed_mean` 丢掉每维最大/最小 floor(βn) 个后取坐标均值，与论文 g_k = 1/((1−2β)m)·Σ_{x∈U_k} x 同构（只差 βm 非整数时的取整约定），β∈[0,0.5) 也与论文一致。
2. **第 5 步的投影**：`update.clip_state_norm` 是"把整个状态按比例缩到范数不超过 bound"，即到原点球的欧氏投影；`update.scale_to_norm` 是把 delta 缩到指定范数。因此当 W 取半径为 D/2 的球时 Π_W 被精确覆盖，W=R^d（Theorem 7 的二次损失设定）时直接省略即可；**若 W 取一般凸紧集（盒、单纯形等），运行时没有对应的投影原语**，此时第 5 步的投影部分需要补一个通用算子。论文只要求 W 凸紧、直径 D，所以这是"参数化选择"而非算子缺口。
3. **坐标轴的含义随运行时表示变化**：运行时是 LoRA 因子空间，"逐坐标"落在 `states.flatten` 之后的因子状态坐标上，而不是全参数梯度坐标。中位数算子本身逐坐标独立，语义保持；但如果严格要求对全参数更新逐坐标取中位，则第 3/4 步的数据粒度（只有 `uploads/factor_delta`、`uploads/product_delta`，没有全参数梯度坐标）会变成 needs_runtime。按本库自己的粒度约定，这仍属可表达。

另外，论文里"拜占庭可任意 ∗"只是威胁模型假设，不需要任何算子；"不过滤地收集"也不是缺口，它等价于**不调用** `select_and_weight`。

## 2. 缺的东西里哪些是通用的（别的方法也会用到），哪些是这篇论文特有的

这条流水线**没有 missing_op / needs_runtime 级别的硬缺口**：它唯一真正有技术含量的两个算子（坐标中位数、坐标截尾均值）在 catalog 里已经作为通用稳健统计实现，而且实现说明直接标注了本论文。真正处于边界上的只有下面几项：

**通用（其他方法同样会碰到，属于算子库/运行时的公共能力）**

- **一般凸集上的投影（projection onto a convex set）**：本库只有"整状态缩放到范数球"（`update.clip_state_norm`）和"delta 缩放到给定范数"（`update.scale_to_norm`）。任何做约束更新的方法——投影 SGD、带约束的稳健聚合、FLTrust 式归一化、DP 的裁剪——都可能要投到盒/单纯形/一般凸集。这是通用缺口，不是本论文特有。
- **本地求解到最优的 ERM / 约束优化器**：catalog 里没有任何优化器，运行时只提供有限步训练循环与步内标量（`trace/*`）。所有"客户端本地训练"型方法都依赖这一能力，属于运行时的公共职责，因此不算算子库缺口。
- **坐标次序统计量族（median / trimmed mean / 一般分位数）**：通用族，catalog 已经覆盖了本论文需要的两种；只有"一般分位数阈值"没有单独入口（可归 compose）。
- **"不做筛选"的收集**：不是缺算子，而是缺省行为（不调用 `select_and_weight`）。

**这篇论文特有（都不构成表达障碍）**

- **偶数个客户端时中位数的取值约定**（中间两值均值，而不是下中位）：这是 Yin et al. 2018 的实现细节，catalog 已经按它实现；若换别的库函数（如 `torch.median`）就会错。
- **步长 η = 1/L_F 依赖损失的光滑常数 L_F、β ≥ α 依赖拜占庭比例上界 α**：这是本论文定理给出的超参标定，不是算子能力；运行时不提供 L_F/α 的估计。
- **Algorithm 2 的"每客户端精确求解本地 ERM + 只通信一轮"**：通信轮数与"精确"是这篇论文的实验设置；表达它不需要新算子，但"精确最优解"这一要求运行时不保证（只能近似训练到收敛）。

**明确不需要的东西**（用来反证没有 needs_runtime）：不需要逐样本梯度裁剪，不需要客户端之间直接通信，不需要推理时介入，也不需要改损失函数。

```json
{
  "key": "yin2018median",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "标准下发，属联邦骨架而非防御计算（任务定义中『下发模型』即归 outside）。运行时侧由 outgoing/factors/recipient 承载、写入动作是 transform_broadcast，但这一步没有任何防御性改动，故不计为 runtime_action。"
    },
    {
      "n": 2,
      "class": "runtime_data",
      "uses": ["gradients/batch_gradient/parameter", "model.per_sample_gradients"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "g_i(w^t)=∇F_i(w^t) 就是本地数据在收到的 w^t 处的批梯度，运行时坐标直接提供；若要按样本平均，可改用 model.per_sample_gradients（samples/gradient/sample）再求均值，仍不需新算子。这一步本身是标准本地计算，按骨架也可读作 outside，但既然有直接对应的 coordinate，归 runtime_data 更贴切。"
    },
    {
      "n": 3,
      "class": "runtime_data",
      "uses": ["uploads/roster/client", "uploads/module_delta/client", "states.stack"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "服务器直接读本轮上传名单与各客户端的因子差；G∈R^{m×d} 由 states.stack/states.flatten 拼出。『不过滤』只是不调用 select_and_weight，不需要任何算子。"
    },
    {
      "n": 4,
      "class": "op",
      "uses": ["robust.coordinate_median", "states.stack", "states.unflatten"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "robust.coordinate_median 的说明直接标注 Yin et al. 2018，逐坐标对行取中位，偶数个时取中间两值均值，与论文 med{·} 定义一致；输入 (m,d) 张量、输出 (d,) 向量。LoRA 场景先 states.flatten/stack，结果再 states.unflatten 回 State，全部是现成函数。"
    },
    {
      "n": 5,
      "class": "op",
      "uses": ["states.add", "update.clip_state_norm", "states.unflatten"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "states.add(w, g, scale=-eta) 给出 w−ηg；Π_W 在 W 为半径 D/2 的原点球时由 update.clip_state_norm 精确给出，W=R^d 时省略投影。疑点：若论文的凸紧集 W 不是范数球（盒/单纯形等），本库没有一般凸集投影原语，那部分需补 projection_onto_convex_set（family: optimization）；按论文定理只约束『凸紧、直径 D』，取球即可完全复现。"
    },
    {
      "n": 6,
      "class": "op",
      "uses": ["robust.trimmed_mean"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "robust.trimmed_mean(X, beta) 与论文坐标截尾均值同构（每维丢弃 floor(beta*n) 个最大最小后取均值，0<=beta<0.5），说明同样标注 Yin et al. 2018；论文分母 1/((1−2β)m) 与之相符，仅当 βm 非整数时取整约定略有差别。β≥α 的取值要求是超参问题，不影响算子可用性。"
    },
    {
      "n": 7,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "本地 ERM 求解 = 普通本地训练，属联邦骨架，不是防御计算。catalog 里没有优化器/ERM 求解算子，这是运行时训练循环的职责。疑点：论文要求精确 argmin 且在一般凸集 W 上投影，运行时只能有限步近似并缺少一般凸集投影；若严格要求『求解到最优 + 投影到 W』，这一步会退化为 needs_runtime。"
    },
    {
      "n": 8,
      "class": "op",
      "uses": ["robust.coordinate_median", "states.stack", "states.unflatten"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "与第 4 步同一算子，只是输入从梯度 G 换成 m 个本地 ERM 解 ŵ_i（运行时表示为收到的/本地的 LoRA 因子状态），states.stack 成 (m,d) 后取坐标中位数；『通信轮数=1』是流程参数而非算子参数。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
