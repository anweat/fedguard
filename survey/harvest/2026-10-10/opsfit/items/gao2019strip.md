## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：部分可表达（partial）。** STRIP 的核心算术链条——采样参考图 → 线性混合 → 前向取输出 → 逐扰动熵 → 求均值 → 与阈值比较——每一环都能在 catalog 里找到落点或只用几行张量运算拼出来；真正卡住的是**"从良性分数到判决边界"的校准环节**，以及第 8 步的在线审计数据。

逐步看：

- **第 1 步（采参考图）**：`sampling.subsample(n, k, rng)` 就是"从 n 个条目里随机取 k 个"，与论文"从 D_test 随机抽 N 张"完全对口（只是参数不同）。参考池本身是本地留出数据，不在 vocabulary 的坐标里，但不影响这一步可做。
- **第 2 步（线性混合）**：`x_p = α·x + β·x_t` 是逐像素的加法与标量乘，`compose` 足够，不需要通用算子；cv2.addWeighted 只是实现方式。
- **第 3 步（前向 + softmax + 预测标签）**：模型句柄只给逐样本损失、隐藏状态、指定子模块激活、逐样本梯度、对数概率。取分类头的激活（logits）再用 softmax/argmax 是常规张量运算，按 `samples/activation/sample` 这条 coordinate 走 `model.activations(samples, select)` 可以落地；**疑点**是句柄没有直接暴露"softmax 概率 / 预测标签"的入口，需要自己补 softmax，这一点我按"可用但需自算"记在 runtime_data 里，并在 note 中标明。对自回归 LLM 而言，这个替代更弱（`model.logprob` 只给目标文本的平均对数概率）。
- **第 4 步（逐扰动熵）**：`density.shannon_entropy` 就是"非负向量归一化后的 Shannon 熵"，与 Eq.2 同一件事；差别只在论文用 log₂、catalog 用 nats，除以 ln2 即可，且该函数是单向量接口，N 条要循环一次。判为 `op`，但 note 里注明单位与批处理的适配。
- **第 5 步（N 个熵求均值）**：一次 `mean`，`compose`。
- **第 6 步（校准判决边界）**：论文假设良性 H 服从正态、按预设 FRR（1%、0.5% 等）取分位点。catalog 里有 `robust.quantile_threshold`（对良性样本经验分位）、`robust.largest_gap_threshold`、`density.kde_valley_threshold`，但**没有"按正态假设取单侧分位点"的函数**；更关键的是运行时没有"已部署模型在良性留出输入上的熵分数"这一坐标。这一步判为 `missing_op`（可复用，名字见下），并把校准数据缺失一并写进 note。
- **第 7 步（阈值判决）**：一次比较 + 布尔，`compose`。
- **第 8 步（辅助干净分布审计）**：`> 3.0` 判断本身是 trivial 的，但它读的是"部署后收集的干净输入熵"，vocabulary 里既无该坐标、也没有"部署后新输入"这一访问路径，因此归 `outside`（离线/运行期之外的运维审计，不属于防御计算本体），note 里说明它需要额外数据。

因此：**算法主体可表达，校准环节需要补一个通用算子，且缺少良性校准分数这一运行时数据**，故 `expressible = partial`。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用的（别的方法也会用到）：**

1. **`gaussian_tail_threshold`（robust_statistics 族）**——输入一组良性参考分数 `benign: list[float] | np.ndarray` 与目标误拒率 `frr: float`（可带 `side: str = "lower_tail"` 决定取左尾还是右尾），输出 `float` 判决阈值；内部用样本均值/标准差 + 标准正态分位点（`Φ⁻¹`），样本过少或方差为 0 时回退到经验分位数。这是所有"用良性分数校准检测边界"的方法（OOD 检测、成员推断、后门检测的阈值标定）都会反复用到的零件，只是 STRIP 把它写成"正态假设 + 预设 FRR"。catalog 现有的三个阈值函数都不是它：`robust.quantile_threshold` 不做参数化假设、`robust.largest_gap_threshold`/`density.kde_valley_threshold` 是找双峰之间的谷，不消费 FRR 这个参数。
2. **良性校准分数这条 coordinate**——"参考模型/参考数据在部署配置下的分数分布"是通用需求（`sequential.reference_z` 的说明里也明确依赖"calibrated benign reference"），但 vocabulary 只给了 `history/features/round`，没有"离线校准分"这一项。这是通用缺口，不是 STRIP 独有。
3. **推理期的分类输出（softmax 概率 / 预测标签）**——如果 `model.activations` 能选到分类头，就只是补一个 softmax；如果目标模型是自回归 LLM（本库的 LoRA 设定多是这种），则完全拿不到逐样本类别分布。这是通用运行时缺口（凡是要看"输出分布"的检测都需要），不是 STRIP 特有。

**这篇论文特有的（不该进算子库）：**

- 混合系数 α、β 的具体取值与 cv2.addWeighted 的调用方式：一次两行乘加，属普通张量运算。
- log₂ 底数的熵：与 `density.shannon_entropy` 只差一个常数因子，不需要新算子。
- "干净输入熵 > 3.0" 这个魔数与"恶意模型"结论：STRIP 的实验观察，且依赖部署后新收集的干净输入，是论文特有的运维流程。
- N=100 / 10 这类参考图数量、以及 FRR 的若干预设档位：纯参数，不是算子。

```json
{
  "key": "gao2019strip",
  "steps": [
    {
      "n": 1,
      "class": "op",
      "uses": ["sampling.subsample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "subsample(n, k, rng) 正是从 n 个条目随机取 k 个索引，对应'N 张参考图'。参考池（用户留出的干净测试集）本身是本地数据，vocabulary 只有 samples/manifest/sample（哈希、来源、长度），因此若要求'图像内容'需另有样本来源；采样动作本身无需新算子。"
    },
    {
      "n": 2,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "x_p = alpha*x + beta*x_t 是逐元素标量乘加：x 广播复制 N 次后与 N 张参考图做两次乘、一次加即可，无需通用算子；cv2.addWeighted 只是论文的实现选择。"
    },
    {
      "n": 3,
      "class": "runtime_data",
      "uses": ["samples/activation/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "模型句柄 model.activations(samples, select) 可给出指定子模块（分类头）的逐样本输出，作为 logits，再用普通 softmax/argmax 得到概率向量 y^(n) 与预测标签 z。疑点：句柄没有直接暴露'softmax 概率/预测标签'接口，且对自回归模型只有 model.logprob（目标文本平均对数概率），并非逐类分布；若 select 拿不到分类头，则这一步要退化为 needs_runtime。"
    },
    {
      "n": 4,
      "class": "op",
      "uses": ["density.shannon_entropy"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "shannon_entropy 就是'非负向量归一化后的 Shannon 熵'，与 Eq.2 同一计算；catalog 用 nats，论文用 log2，除以 ln 2 即可；该函数是单向量接口，需对 N 条扰动循环调用（循环不算新算子）。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "H = (1/N) * sum_n H_n 就是把第 4 步的 N 个标量堆成一维张量后取 mean，普通张量运算。"
    },
    {
      "n": 6,
      "class": "missing_op",
      "uses": [],
      "missing_name": "gaussian_tail_threshold",
      "missing_family": "robust_statistics",
      "missing_io": "输入 benign: list[float] | np.ndarray（良性参考分数）、frr: float（目标误拒率）、side: str = 'lower_tail'；输出 float 判决阈值。用样本均值与标准差 + 标准正态分位点 Φ^{-1}(frr)（或右尾 1-frr），样本过少或方差为 0 时回退到经验分位数。",
      "note": "catalog 的三个阈值函数都不匹配：quantile_threshold 是无分布假设的经验分位、largest_gap_threshold 与 kde_valley_threshold 是找双峰间的谷，都不消费'正态假设 + 预设 FRR'这一对参数。附带缺口：运行时也没有'已部署模型在良性留出输入上的熵分数'这一坐标，校准样本需另找来源。"
    },
    {
      "n": 7,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "trojanedFlag = (H <= boundary) 是一次比较加布尔化，几行代码即可；熵越低越可疑，方向与第 6 步的左尾阈值约定一致。"
    },
    {
      "n": 8,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "'干净输入熵 > 3.0 即判模型恶意'是一次标量比较，计算上不需要新算子，但它读取的是部署后新收集的干净输入熵——vocabulary 没有该坐标，也没有'部署后新输入'的访问路径。属于论文特有的离线/运维审计，不计入防御计算本体。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "缺少可复用的'正态假设分位点阈值'算子：catalog 只有经验分位（robust.quantile_threshold）与双峰谷阈值（robust.largest_gap_threshold、density.kde_valley_threshold），无法按预设 FRR（1%、0.5%）从良性熵分数标定判决边界。",
    "运行时没有'良性校准分数/参考分布'这一 coordinate（history/features/round 只覆盖此前各轮特征），第 6 步的校准输入在现有 vocabulary 中拿不到。",
    "非阻塞疑点：模型句柄不直接提供逐样本 softmax 类别分布与预测标签；若目标子模块中选不到分类头（自回归 LLM 情形），第 3 步需要的输出分布无法取得。"
  ]
}
```
