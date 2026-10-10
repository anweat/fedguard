## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：不能（`expressible: no`）。** 逐步看，个别环节能对上（取逐样本 CE、采高斯噪声、标量算术、离线造数据和发布检查点），但 RepNoise 的方法本体——"用自定义三项损失做一轮全参数微调来完成表示免疫"——在这套运行时里没有任何执行路径。理由分三层：

**（a）骨架不匹配。** vocabulary 的坐标粒度是 `sample / module / parameter / step / client / round / recipient`，动作只有 8 个（`mask_samples、edit_samples、transform_received、transform_gradients、transform_update、select_and_weight、replace_global、transform_broadcast`），全部是对**已经算好的制品**做事后变换。RepNoise 不是"改样本 / 改上传 / 改聚合"，而是"改训练目标"，运行时里既没有"跑一步自定义目标训练"的动作，也没有把标量接回计算图的接口。

**（b）数据面缺 token 与层两个轴。** 论文的 MMD 与逐层 ascent 都定义在**逐 token、逐层**的 `(B,T,d)` 表示上，还要精确落在 post-MLP pre-residual 这个 hook 点；运行时只有 `samples/activation/sample`、`model.activations(samples, select)`、`model.hidden(samples, layer, pool)`，说明里明确是 per-sample 一个向量（`hidden` 还带 pool）。同时 catalog 没有 tokenizer：`text.hashed_bag_of_words` 是**有损哈希词袋**（不能还原 token id 序列），`text.split_words` 只按空白切词，坐标也只有 `samples/text/sample`，因此 `b_harmful/b_harmless` 的 token id 与"共同 token 掩码 MASK"（Alg.1 第 4 行）在运行时里造不出来。

**（c）计算面缺三个关键单元。** ①把最终 LM head 作用到任意中间层隐藏态并算 token 级 CE（tuned-lens 风格）——catalog 只有二分类的 `probe.fit_logistic/apply_logistic`，名字相近但语义完全不同；②多核高斯 MMD——`density.*` 只有 KDE / JS / 熵 / KNN 密度比，没有核两样本统计量；③噪声采样虽是一行 `torch.randn_like`，但**不要**误用 `update.add_gaussian_noise`（它只对 `states.State` 参数逐项加噪，是 DP 式参数噪声，(B,T,d) 激活采样跟它无关）。

**（d）动作面：服务端根本没有训练能力。** 流水线把 RepNoise 放在 `server_post_aggregate`，但服务端制品（uploads / aggregate / outgoing）只允许 `select_and_weight / replace_global / transform_broadcast`，"在服务端对聚合结果做一整轮微调"无处安放；若改成场景外的离线作业，那又退化成 `outside`，同样不由运行时表达。次要疑点：运行时模型侧制品以 LoRA 因子为中心（`received/factors`、`local_update/factors`、`trace/factors`、`model.lora(state)`），而 RepNoise 免疫的是全参数 θ（论文还报告冻结 0–10 层会使防御完全失效），语义并不对齐。

能对上的部分：n=1（离线配对数据）、n=2（逐样本 CE 可直接读）、n=5（噪声采样）、n=7/8/9（层间均值、log、标量合成）、n=11（发布检查点）；n=6 需补一个通用算子；n=3/4/10 是硬缺口。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用缺口（别的方法也会用到，值得进算子库/运行时）**

1. `gaussian_mmd`（多核高斯 MMD²）：后门/漂移检测、表示对齐、分布匹配类方法反复使用；一旦有了它，n=6 就只是参数问题（带宽、核数、有偏/无偏）。
2. `lm_head_ce_on_hidden`（把 LM head 作用到任意隐藏态并算 token 级 CE）：logit-lens / tuned-lens / 逐层探针 / early-exit / 逐层可解释性都会用，是通用文本族单元；同时要求运行时暴露 unembedding 权重并接受外部隐藏张量。
3. **逐 token、逐层、可指定 hook 点的激活读取**：任何在表示层做正则、对齐、聚类、检测的方法都缺；现在最细只有 per-sample 粒度。
4. **可微的自定义训练目标接口**（"按我给的损失跑一步/给梯度"）：所有"改损失函数"的防御（加正则项、加对齐项、加噪）都卡在这里；现有的 `transform_gradients/transform_update` 只能事后改梯度，替代不了对自定义标量反传。
5. **tokenizer / token id 粒度通道**（文本↔id 序列 + token 级掩码与标签对齐）：逐 token 损失掩码、逐 token 归因、token 级水印类方法都需要。
6. **全参数检查点的读写/导出**（若运行时坚持 LoRA-only）：做全参数免疫或修复的方法都需要。

**这篇论文特有的（不必做成通用算子）**

1. `l_all = l_stability + α·(层均 l_noise) + β·log(层均 l_ascent)` 的具体形式与 α/β 取值（1/2、0.001/4），以及 eq.(5) 与 Alg.1 第 12 行绑定相反这处不一致——这是实现细节/参数选择。
2. "复用**最终 LM head** 对每层激活做 ascent（tuned-lens 式）"这一组合：底层能力（把 head 用到隐藏态）是通用的，但"用它做 ascent 项"是这篇的做法。
3. 配对拒绝数据集与其构造（不安全问题 + 有害/无害回答，BeaverTails / RTP / HEX-PHI，10k/351/230 条），以及"共同 token 掩码"这一具体掩码定义。
4. MMD 的带宽/核数论文未给，这是论文的空白，不是通用算子缺口；"冻结 0–10 层防御失效"是经验结论，不是算子。

```json
{
  "key": "rosati2024repnoise",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "从 BeaverTails/RTP/HEX-PHI 构造『不安全问题 + 有害/无害回答』配对数据属于离线数据准备，故归 outside。疑点：MASK=两侧共同 token 需要 tokenizer 产出 token id 序列，catalog 的 text.* 只有 hashed_bag_of_words（有损哈希词袋，不可逆）和 split_words（按空白切词），坐标也只有 samples/text/sample（文本粒度），没有 token id 粒度；若要求运行时内完成这一步，应改判 missing_op（family text，如 batch_tokenize_with_shared_mask）或 needs_runtime。若 token id 已就绪，掩码本身是 compose（相等比较 + 逻辑与）。"
    },
    {
      "n": 2,
      "class": "runtime_data",
      "uses": ["samples/loss/sample", "model.losses"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "batch 的因果 LM 交叉熵由句柄方法 model.losses(samples) 直接给出逐样本损失（对应坐标 samples/loss/sample），再对 batch 取均值即可；catalog 里没有独立的 CE 损失函数。疑点一：若 l_stability 要按论文只在掩码位置/答案 token 上取平均，运行时没有 token 级标签对齐，会退化成 compose 或做不了；疑点二：句柄说明未保证返回的 loss 保留在计算图里，作为训练项还需要它可反传。"
    },
    {
      "n": 3,
      "class": "needs_runtime",
      "uses": ["samples/activation/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "model.activations(samples, select) 能取所选子模块的激活（对应 samples/activation/sample），model.hidden(samples, layer, pool) 更粗（带池化），但 catalog 说明二者都是 per-sample 粒度；论文要的是全部 L 层、post-MLP pre-residual、保留 token 轴的 (B,T,d) 张量（MMD 与逐层 LM-head 损失都在 token 维上算）。另外『全部 L 层』若 select 一次只能选一个子模块，就需要 L 次前向；且这些激活必须可微地接进损失，句柄返回的是观测量而非计算图张量。缺的是：逐层、可指定 hook 点、保留 token 轴且可微的激活读取接口。"
    },
    {
      "n": 4,
      "class": "missing_op",
      "uses": [],
      "missing_name": "lm_head_ce_on_hidden",
      "missing_family": "text",
      "missing_io": "输入：中间层隐藏态 H (L,B,T,d)、最终 LM head 权重 W (V,d)（含 bias）、标签 y (B,T) 与掩码 MASK (B,T)；输出：每层标量交叉熵 (L,)，需可微。",
      "missing_io_note": "",
      "note": "catalog 只有 probe.fit_logistic/apply_logistic（L2 逻辑回归探针，二分类），不能把语言模型自己的 unembedding 作用到任意隐藏态上，也没有 logit-lens/tuned-lens 类接口。运行时侧还缺：句柄不暴露 LM head 权重，也不接受外部隐藏张量。这是 logit-lens / 逐层探针 / early-exit 都会复用的通用单元。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "torch.randn / randn_like 一行即可，属普通张量运算，不需要新算子。注意不要因名字相近误用 update.add_gaussian_noise：它只对 states.State（参数）逐项加 N(0,σ²) 噪声，是 DP 式参数噪声，与本步对激活 (B,T,d) 采样标准高斯不是一回事。"
    },
    {
      "n": 6,
      "class": "missing_op",
      "uses": [],
      "missing_name": "gaussian_mmd",
      "missing_family": "distance_geometry",
      "missing_io": "输入：两组表示 X (n,d)、Y (m,d)，带宽集合 {σ_k} 或多核选择规则，估计量选项（有偏/无偏）；输出：标量 MMD²（可微）。",
      "note": "catalog 的 density.* 只有 KDE、JS 散度、熵、KNN 密度比，没有核两样本统计量。疑点：用 geometry.pairwise_sq_distances + exp 核 + 三个块均值确实能手工拼出有偏 MMD²，按此标准也可判 compose；这里判 missing_op 的理由是——多核/带宽选择与有偏无偏的估计量形式本身就是方法级决定（论文未给带宽与核数），exp 核不属于 compose 列举的普通运算（加减乘、比较、取索引、求均值），且 MMD 在后门/漂移检测、表示对齐里会被反复复用，值得做成通用算子。"
    },
    {
      "n": 7,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对 {l_noise^l} 与 {l_ascent^l} 逐层取均值 = torch.stack(...).mean()，普通张量运算。注意 sequential.window_mean 是『跨轮历史』的均值（输入 list[Tensor] 的 per-round history），不是层间均值，名字相近但不能当 op 用。"
    },
    {
      "n": 8,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "torch.log(层均 l_ascent) 一行；逐层 CE 恒正，所以 log 定义良好。前提是均值张量仍在计算图内，否则压缩出来的只是数值。"
    },
    {
      "n": 9,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把 l_stability、层均 l_noise、log 压缩后的层均 l_ascent 按 α/β 加权求和，标量算术本身是 compose 级（catalog 无需新算子）。但这一步的产物是『训练目标』：运行时没有自定义损失/自动求导接口，数值算出来也无法用于反传，这一缺口记在 n=10 与 blocking。α/β 随数据集取 1/2、0.001/4 且论文 eq.(5) 与 Alg.1 第 12 行绑定相反，属参数/实现问题而非算子缺口。"
    },
    {
      "n": 10,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "要按 ∇θ l_all 做 Adam + cosine warmup 更新，需要运行时能『以自定义目标执行一次训练步』。运行时只有 mask_samples/edit_samples/transform_received/transform_gradients/transform_update/select_and_weight/replace_global/transform_broadcast 八个动作，全是对已算好制品的事后变换：transform_gradients/transform_update 只能改现成梯度或上传更新，既不能对自定义标量求 ∇θ，也无法把 MMD 项与逐层 ascent 项变成梯度。优化器与调度本身是普通训练机制（那部分接近 outside），但这一步的输入梯度运行时产生不了，故整体归 needs_runtime——正是『要改损失函数』这一条。"
    },
    {
      "n": 11,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "导出/发布训练完的检查点属常规产出（『下发模型』在分类里明确算 outside）。若要把免疫后的权重写回全局模型槽再分发，对应动作是 replace_global / transform_broadcast；但免疫权重本身的产生（n=2–10 的训练）运行时做不了；另外运行时模型侧制品以 LoRA 因子为主（received/factors、local_update/factors、trace/factors、model.lora(state)），而这里免疫的是全参数 θ，语义也不完全对齐。"
    }
  ],
  "expressible": "no",
  "blocking": [
    "没有可自定义、可反传的训练目标接口：RepNoise 的防御就是把 l_stability、逐层表示-MMD、逐层 ascent 组成 l_all 并对 θ 反传，而运行时的动作只能事后改已算好的梯度/更新，无法对自定义标量求 ∇θ（n=9/10，『要改损失函数』）。",
    "拿不到逐 token、逐层、指定 hook 点（post-MLP pre-residual）的激活：samples/activation/sample、model.activations、model.hidden 都只有 per-sample 粒度，token 轴与层轴缺失，且观测量不能可微地接进损失（n=3）。",
    "没有把最终 LM head 作用到任意隐藏态并算 token 级 CE 的算子（missing_op: lm_head_ce_on_hidden），运行时也不暴露 unembedding 权重、不接受外部隐藏张量（n=4）。",
    "没有 token 级数据通道：catalog 无 tokenizer（text.hashed_bag_of_words 是有损哈希词袋），坐标只有 samples/text/sample，构造不出 b_harmful/b_harmless 的 token id 与共同 token 掩码 MASK（n=1）。",
    "服务端没有训练动作：运行时服务端只能 select_and_weight / replace_global / transform_broadcast，而本方法声明在 server_post_aggregate 阶段、需要在服务端对聚合后的模型做一整轮（全参数）微调（n=10/11）。",
    "算子层还缺 gaussian_mmd（n=6）——它本身可以补，但补上它也不能解决上面 1–5 条运行时缺口。"
  ]
}
```
