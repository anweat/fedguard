## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：主体可以表达，只有一个可选分支不能，因此是 partial。**

关键判断依据：

- **这条流水线根本不是联邦防御。** `stages = ["outside_training"]`，10 步全部发生在防御方（发布方）自己的对齐训练循环里：没有客户端/服务器之分，没有上传、聚合、下发、选择与加权。vocabulary 里的 `uploads`、`aggregate`、`outgoing`、`local_update` 以及 `select_and_weight`、`replace_global`、`transform_broadcast`、`mask_samples`、`edit_samples` 等动作**一个都用不上**。能对上的只有 `samples`（数据）、`gradients`（批梯度/逐样本梯度）、`trace`（训练标量）和 `history`。
- **算术部分完全落在 `states.*` 上，一步都不缺。** `states.unflatten`（把归一化后的梯度向量还原成 LoRA 因子形状）、`states.add`（`scale` 带符号：既能算 `w_t - alpha*u_t`，也能算 `grad_f + lambda*d`）、`states.delta`（两个梯度相减）三者组合就是式(2)(3)的全部算子内容；剩下只有一次平凡的向量 L2 归一化。**因此 `missing_op` 为空**：不需要任何新的通用计算单元。
- **数据部分都在运行时里。** 两批样本来自 `samples/text/sample`（标签即回答文本，随样本给出），三次梯度来自 `gradients/batch_gradient/parameter`，扰动权重处的第二次求值由 `model.lora(state)` 的临时载入支撑。
- **论文丢弃二阶项反而救了它。** 作者把二阶项近似成常数丢掉（第 8 步 `second_order` 参数），所以**不需要 Hessian-vector / 二阶梯度单元**——这正是它能在现有算子下表达的关键。若某变体保留二阶项，才会缺一个通用 HVP 单元（`sequential.lbfgs_hvp` 只针对 L-BFGS 紧凑表示，不是通用 HVP）。
- **唯一的真实能力缺口是第 3 步（可选 Vaccine+Booster）**：模型句柄只有对**参数组**求梯度的 `model.per_sample_gradients(samples, group)`，没有对**输入嵌入**求梯度 `∂f/∂e` 的入口，也没有在 embedding 前向里加扰动的 hook。
- **遗留疑点（已按"不确定不算 op"处理）**：① `transform.l2_normalize` 名字相符但说明为空，无法确认是整张量归一化还是逐行归一化，故第 6 步归 `compose`；② 批梯度坐标是否反映 `model.lora` 临时载入的 state，是从 `model.lora` 的说明推断的；③ 论文未说明归一化是全局展平范数还是逐层范数，两种都能用同样的几行算出；④ 第 5、8 步"共用同一 harmful batch"实现上就是同一批数据做两次 forward-backward，数据可复用，不成问题。
- **另需说明**：Booster 依赖一份"与用户微调数据同分布的有害数据集"，这在语义上对应 `trust.reference_data`（防御方持有可信参考数据），其准备属于离线数据准备（outside），不是算子缺口。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用（别的方法也会用到）：**

1. **输入嵌入空间的前向/反向接口**——即 `∂loss/∂embedding` 与"前向时往 embedding 上加一个向量"的 hook。凡是在输入/嵌入空间做对抗扰动或鲁棒化的方法（embedding 上的 FGSM/PGD、Vaccine、各类嵌入空间安全对齐、prompt/soft-prompt 类攻击与防御）都会需要。建议作为**模型句柄的通用能力**扩展（如 `model.input_gradients(samples, module)` 与一个可注册的 embedding 注入点），而不是塞进算子库。
2. **"在临时扰动权重上再取一次梯度"的能力**——SAM、Fish、元学习、两点评估式的稳健聚合都需要；目前 `model.lora(state)` 已能满足，属于通用需求且已覆盖。
3. **通用二阶/HVP 单元**——Booster 因丢弃二阶项不需要，但任何保留二阶项的方法都会要；catalog 只有 L-BFGS 专用的 `sequential.lbfgs_hvp`，算一个潜在的通用缺口（本文不阻塞）。

**这篇论文特有：**

1. **"有害数据集"这份数据资产与"对齐 batch + 有害 batch"的双批协议**：方法定义就建立在"存在一份与用户微调同分布的有害提示-回答对"上，这是数据准备而非可复用算子，换个方法就不成立。
2. **`alpha`（模拟攻击步长）、`lambda`（正则权重）、`rho`（Vaccine 扰动半径）及其扫描表、`T=10000` 的推导**：方法专属超参，不需要任何算子。
3. **式(2)→式(3) 的二阶项常数近似**：属于这篇论文的解析推导，落成代码只是"对扰动权重 `detach` + 把系数当常数"，不产生通用算子。
4. 附带一句：论文没有定义它在联邦流程里的位置（它是发布前对齐阶段的方法），"在 FL 里怎么接"是方法定位问题，不是算子缺口。

```json
{
  "key": "huang2024booster",
  "steps": [
    {
      "n": 1,
      "class": "op",
      "uses": ["sampling.subsample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "sampling.subsample(n=5000, k=10, rng) 就是'从 5000 条里取 10 条索引'，正是 sample_batch 算子。样本本体（提示+回答，回答即标签）来自 samples/text/sample 坐标，清单走 samples/manifest/sample；若把这一步只看作'取数据'，也可记作 runtime_data。"
    },
    {
      "n": 2,
      "class": "op",
      "uses": ["sampling.subsample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "同上，只是换成另一份同分布的有害数据集；size_sweep 的 5~5000 只是 k 取值不同，仍属同一函数。该有害数据集是防御方离线准备的数据资产（离线准备本身算 outside），运行时不区分数据来源。"
    },
    {
      "n": 3,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "缺两件事：(1) 对输入嵌入求梯度 ∂f/∂e —— 模型句柄只有 model.per_sample_gradients(samples, group)（对参数组）与 model.losses，没有 embedding 级 backward；(2) 前向时把 rho*单位梯度加到 embedding 上的注入入口（无 hook）。另外 rho 论文未给出（附录 C 只给了 Vaccine 单独实现用 5）。标记 optional，去掉它不影响主体。"
    },
    {
      "n": 4,
      "class": "runtime_data",
      "uses": ["gradients/batch_gradient/parameter"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对齐 batch 的交叉熵对可训练 LoRA 参数的批梯度，由运行时的批梯度坐标直接提供（也可用 model.per_sample_gradients(samples, group) 逐样本取再求均值）。catalog 里没有任何求导函数，所以不是 op。"
    },
    {
      "n": 5,
      "class": "runtime_data",
      "uses": ["gradients/batch_gradient/parameter"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "同一坐标，只是换成有害 batch；与第 8 步共用这一批（论文'第 5、6 行共用该 batch'）。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": ["states.flatten"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "states.flatten 展平成一个向量 v，再 v / v.norm() 即 u_t，一行普通张量运算。疑点：transform.l2_normalize 名字相符但说明为空，无法确认是整张量归一化还是逐行归一化（若逐行，把向量当 (1,d) 调用同样得到全局单位向量），按'不确定不算 op'归 compose。论文未说明是全局展平范数还是逐层范数，两者都能这样算（逐层则按 key 分别归一化）。从运行时的角度看它等价于 transform_gradients 这个改动点，但这里纯属自己训练循环内的数值变换。"
    },
    {
      "n": 7,
      "class": "op",
      "uses": ["states.unflatten", "states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "states.unflatten(u_t, like=w_t) 还原成 State，再 states.add(base=w_t, d=u_t_state, scale=-alpha) 得 w'_t = w_t - alpha*u_t。'不持久化'由 model.lora(state) 的临时载入保证；这是临时探针，不是对 received/local_update 制品的持久改动，所以不归 runtime_action。"
    },
    {
      "n": 8,
      "class": "runtime_data",
      "uses": ["gradients/batch_gradient/parameter", "model.lora"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "model.lora(w'_t) 临时载入扰动权重后，对同一有害 batch 反向即得 grad_h(w'_t)；'梯度不穿过扰动项'就是对 w'_t 做 stop-gradient（论文把二阶项近似为常数丢掉，因此不需要 HVP/Hessian）。疑点：批梯度坐标默认给'当前模型'的批梯度，这里隐含假设临时载入的 state 会被该坐标反映，依据是 catalog 中 model.lora 的临时载入说明。"
    },
    {
      "n": 9,
      "class": "op",
      "uses": ["states.delta", "states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "d = states.delta(grad_h(w_t), grad_h(w'_t))，g = states.add(base=grad_f, d=d, scale=lambda)。正好是 states 家族的减/加缩放；lambda=5 及扫描表只是参数不同。"
    },
    {
      "n": 10,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "AdamW 与 lr/weight_decay 是普通本地训练循环的事，不属于防御计算本身，catalog 没有也不该有优化器算子；运行时侧由训练循环与优化器状态承担（gradients/parameter_value/parameter、trace/scalars/step 说明存在这样的循环）。T=10000 步由 20 epochs × 5000/10 推出。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "模型句柄没有'对输入嵌入求梯度'的入口，也没有在 embedding 前向中注入扰动的 hook，因此可选的 Vaccine+Booster 变体（第 3 步，rho 论文亦未给出）无法表达；这是唯一表达不了的部分。Booster 主体（第 1、2、4–10 步）可以完整表达：梯度来自 gradients/batch_gradient/parameter，扰动权重由 states.unflatten + states.add 构造并以 model.lora 临时载入，归一化与合成只用 states.flatten/delta/add 加几行张量运算，无需新的通用算子。"
  ]
}
```
