# 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：能，10 步全部落在 op / runtime_data / compose 三类，`expressible = full`，无需新增算子，也没有拿不到的数据。**

结构上看，这条流水线是「一次性标定（Phase I–III，步骤 3–6）+ 在线检测（步骤 7–10）」两段纯计算：

- **算子覆盖度好。** 核心相似度就是 `geometry.cosine_to`（"cosine of every row to one reference vector"），把"一片切片梯度"当成 X 的一行、"同下标参考切片"当成 ref 即可；备选 `geometry.cosine_matrix`（算全矩阵再取对角块，浪费）。域适配分类器由 `probe.fit_logistic` / `probe.apply_logistic` 直接覆盖，且 `fit_logistic` 的说明明确处理"特征数多于样本数、极小值落在标准化后行空间"的情形——正是 |S|≈2.0e5、训练样本远少于特征数的 GradSafe-Adapt 场景。其余步骤（模板拼接、行列切片、参考切片求均值、逐切片 gap 阈值、按集合取切片、跨切片均值+阈值）都落在 compose 明确允许的"加减乘、比较、取索引、求均值"里。
- **数据覆盖度好。** 提示文本走 `samples/text/sample`；(prompt, 'Sure') 的损失梯度走 `samples/gradient/sample`（via model_handle，即 `model.per_sample_gradients`）——把这对文本当成一条样本做一次反向即可；不安全/安全参考提示属于防御方持有的可信参照（trust 里的 `reference_data`），同样以文本进入同一条取数路径，标定出的参考切片留在内存或 history 类制品里即可。
- **这条流水线不含任何 runtime_action。** 它到"连续分数 + 二值判定"为止，没有调用 artifacts 的任何一个 `modified_by`（不改样本、不改更新、不替换全局、不下发），也不涉及客户端间通信或聚合。判定之后怎么用是流水线之外的事：若命题是"本地训练前筛掉危险样本"，客户端侧可接 `mask_samples` / `edit_samples`；若命题是"推理时拦截用户提示"，则属于推理时介入，运行时没有提示级制品与对应动作。
- **两个真问题都不属于"表达能力"，属于工程规模/簿记：** (a) Llama-2-7b 全参数梯度 + 2,498,560 个切片 + 每条待检测提示一次反向，显存与耗时都很重；(b) 句柄按"参数组"返回**展平**的逐样本梯度，要先用 `states.unflatten(flat, like)` 还原二维形状才能取行列切片。唯一保留的疑点写在步骤 2 的 note：若 `group` 只能取 LoRA 因子、拿不到基座权重矩阵的梯度，论文的全权重切片分析就会退化。

# 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**先说结论：没有必须新增的通用算子（missing_op 为空），也没有运行时取不到的数据或做不了的动作（needs_runtime 为空）。**

**通用部分（别的方法也会碰到，但现有函数 + 几行就够，不足以立新算子）：**
- **逐切片/成对向量的批量余弦。** 任何"逐层、逐参数块、逐切片算相似度"的检测（Krum/FLTrust 型逐参数分析、逐层相似度、逐模块漂移）都会遇到"切片长度不一、必须按形状分组"的同一个问题。核心计算 `geometry.cosine_to` 已经覆盖，分组/零填充/拼接只是取索引层面的簿记。如果本库想把"切片"提升为一等公民，可考虑 distance_geometry 族的 `slicewise_cosine(X, R)`（输入两组同下标的切片向量、输出逐切片余弦），但按现有函数说明判定为**不必需**。
- **均值打分 + 固定/校准阈值。** 通用需求。`robust.quantile_threshold` 只在"有良性校准集、要按 FPR 定阈值"时才是对应函数；本流水线用的是固定阈值（Phase III 的 gap>1、Zero 的 0.25），所以只用比较运算。
- **参考梯度的一次性标定与缓存。** 任何用参考数据的检测都要做；运行时用 `samples/gradient/sample` + history/channel 类坐标就能携带，不需要新算子。

**论文特有（属于方法与超参，不该也不需要进算子库）：**
- **"安全关键切片集合 S"这一概念及其构造规则**：逐切片 `mean(unsafe cosine) − mean(safe cosine) > 1`，Llama-2-7b 上保留 11.78% 行切片 / 3.53% 列切片。这是 GradSafe 的判别核心，但实现上只是均值差加阈值。
- **用顺从回复 "Sure" + system prompt 模板把任意提示变成一条可求梯度的样本**，以及"2 条不安全参考提示求均值当参考"的 Phase I 设定。
- **Zero / Adapt 这对变体设计**：跨切片平均 + 固定阈值 0.25 与逻辑回归域适配。
- 参考提示集合本身（2 不安全 + 2 安全）、切片规模 2,498,560、特征维 |S|≈2.0e5。

**唯一可能算"缺运行时"的两件事，都在流水线之外：** 一是按判定在推理时拦截提示（运行时无提示级制品、无推理时介入动作）；二是若要求逐样本对**全 LLM 参数**求梯度而 `group` 只支持 LoRA 因子组。前者不影响本流水线（它只输出判定），后者按句柄"参数组可选"的说明判为可用，故 `blocking` 为空。

```json
{
  "key": "xie2024gradsafe",
  "steps": [
    {
      "n": 1,
      "class": "compose",
      "uses": ["samples/text/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "纯字符串处理：把提示文本填进 system_prompt 模板再接上 'Sure'。catalog 的 text.* 只有分词/哈希/删词/困惑度规则，没有模板函数，但这一步连通用算子都算不上，Python format/replace 即可，不需要新算子。提示文本与参考提示都以 samples/text/sample 形式进入；参考提示的可信性由 trust.reference_data 承担。"
    },
    {
      "n": 2,
      "class": "runtime_data",
      "uses": ["samples/gradient/sample", "model.per_sample_gradients"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "坐标 samples/gradient/sample 就是 via model_handle 的逐样本梯度：把 (prompt,'Sure') 当成一条样本、对所需参数组做一次反向即得，标准损失无需改动。疑点：论文要的是'每个参数'的梯度、规模与全 LLM 参数同阶，而句柄按 group 返回展平梯度，需要按组遍历并用 states.unflatten 还原二维形状；若运行时只对 LoRA 因子组给梯度、拿不到基座权重矩阵的梯度，则 2,498,560 个全权重切片无法复现，这一步会退化成 needs_runtime。论文未说明 loss 的 token 范围与归一化，属参数细节。"
    },
    {
      "n": 3,
      "class": "compose",
      "uses": ["states.unflatten"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "取行 g[i,:] 与列 g[:,j] 是纯粹的取索引，compose 明确允许。先用 states.unflatten(flat, like) 把展平的逐样本梯度切回各权重矩阵的形状，再对每个二维矩阵做行列切片即可。2,498,560 个切片是规模问题（显存/时间），不是表达能力缺口。"
    },
    {
      "n": 4,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对每个切片下标把 2 条不安全参考的切片梯度 stack 后 mean(0)，属于 compose 允许的求均值。states.weighted_average 面向 State（模型字典）做逐项加权平均，不直接作用于切片向量；把切片打包成 State 虽可套用，但属绕路，故不列为 op。"
    },
    {
      "n": 5,
      "class": "op",
      "uses": ["geometry.cosine_to"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把每片切片梯度当作 X 的一行、同下标的参考切片当作 ref，cosine_to 就是逐切片余弦；也可用 geometry.cosine_matrix 一次算完再取对应块（代价是 |S|×|S| 全矩阵，浪费）。行切片长度=列数、列切片长度=行数，各矩阵长度不一，需按形状分组分别调用或零填充到公共长度——这是拼接/取索引层面的簿记，不构成新算子。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "gap_i = mean(2 条不安全提示在切片 i 的余弦) − mean(2 条安全提示在切片 i 的余弦)，保留 gap_i > 1 的切片：逐切片均值、相减、比较、布尔索引，全在允许范围内。robust.largest_gap_threshold 求的是排序后最大间隔的中点（数据驱动切分），与论文的固定阈值 1 不是同一条规则，不能替代；density.kde_valley_threshold 更不适用。阈值 1 是论文超参。"
    },
    {
      "n": 7,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "按集合 S 对待检测提示的全参数梯度做花式索引/布尔掩码，取出 S 上的切片。sampling.coordinates(d,k,seed) 是按 seed 生成固定坐标子集，无法按外部给定的任意集合 S 选取，故不适用。"
    },
    {
      "n": 8,
      "class": "op",
      "uses": ["geometry.cosine_to"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "与第 5 步同一算子，只是 X 限定为 S 上的切片、ref 限定为 S 上的不安全参考切片，输出按 S 的顺序拼接成长度 |S| 的向量（cat/stack 属普通运算）。|S|≈2.0e5 是规模问题。"
    },
    {
      "n": 9,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对 |S| 维余弦向量取 torch.mean 得连续分数，再与 0.25 比较得二值判定——求均值与比较都在 compose 允许范围内，catalog 没有对应算子。阈值 0.25 是论文调好的超参；若改按良性校准集定阈值可用 robust.quantile_threshold，但那不是 GradSafe-Zero 的规则。"
    },
    {
      "n": 10,
      "class": "op",
      "uses": ["probe.fit_logistic", "probe.apply_logistic"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "probe.fit_logistic(X,y) 训练 L2 逻辑回归（内部做标准化，docstring 明确处理特征数多于样本数、解落在标准化后行空间的情形，正好对应 |S|≈2e5、样本数远小于特征数的域适配训练）；probe.apply_logistic 在推理时给概率，再 >0.5 判二值（普通比较）。论文未给超参，l2/iters 只是参数选择。"
    }
  ],
  "expressible": "full",
  "blocking": []
}
```
