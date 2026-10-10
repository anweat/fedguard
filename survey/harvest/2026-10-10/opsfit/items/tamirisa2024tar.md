## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：partial（部分可表达），但方法的核心跑不起来。**

先说范围判断。`stages` 自述 `outside_training`，整条 pipeline 是**集中式、离线的双层元训练**（内层模拟攻击、外层加权更新权重），没有客户端、没有上传/聚合/下发。而 catalog 是"联邦 LoRA 防御的统计与更新变换工具箱"（距离/聚类/密度/稳健统计/谱/文本/变换/更新裁剪加噪投影），model handle 是**只读**的（`losses/hidden/activations/per_sample_gradients/logprob/generate` + `model.lora(state)`）。两者交集如下：

**能表达的部分（7 步）**
- 第 2 步取 probe minibatch：`sampling.subsample` 就是"从 n 条里取至多 k 条下标"，数据来自 `samples/text/sample`。
- 第 4、5 步是纯下标簿记（前缀切片、`[::4]` 等距抽取），几行普通运算，不需要新算子。
- 第 6 步逐位置熵：`density.shannon_entropy` 给一个分布的熵，配合 softmax、对 token 位置求均值、取负即可，属 compose。
- 第 7 步 DPO：`model.logprob(prompts, targets)` 给"目标文本的平均对数概率"，chosen/rejected 各算一次，再减离线预算的 reference 对数概率、做 `-log sigmoid(β·Δ)`，属 compose。
- 第 9、11 步：`g += grad/K` 与 `θ − η(λ_TR g_TR + λ_retain g_retain)` 都是标量乘加，若梯度/权重以 State 承载，`states.add(base, d, scale)` 恰好就是 `base + scale·d`。

**做不了的部分（4 步，全是 needs_runtime）**：第 1、3、8、10 步。它们卡在同一个根上——**运行时不是一个训练框架**：没有优化器、没有训练循环、没有"对任意损失反传"的入口。附带两条独立缺口：运行时只能 `model.lora(state)` 装载 LoRA 状态，无法切到全参数攻击检查点（第 6、7 步要在攻击坐标处评估策略模型）；也没有"参考模型前向统计"的来源（第 10 步要 θ_G0 的激活，坐标表里没有对应 coordinate）。

**关键判断**：本流水线**一个 `missing_op` 都不需要**。缺口不是"库里少一个可复用计算单元"，而是"运行时做不了训练/反传/换权重"这些动作，按定义属于 `needs_runtime`。同样地，**0 个 `runtime_action`、0 个 `runtime_data`**：没有一步能落到 `mask_samples / edit_samples / transform_received / transform_gradients / transform_update / select_and_weight / replace_global / transform_broadcast` 上，也没有一步是"读一个 coordinate 就完事"。第 12 步是普通 SFT，归 `outside`。

**遗留疑点**（按"不确定就降级"处理）：(a) 熵需要**逐位置输出分布**，句柄只给逐样本 loss 和 target 文本的平均 logprob，要靠 `model.activations(select=输出层)` 拿 logits——catalog 没明说 LM head 一定可选，故第 6 步只敢判 compose 而非 op；(b) DPO 的 reference log-prob、θ_G0 的激活、全参数轨迹快照都没有坐标（`trace/*` 只有 LoRA 因子与标量）；(c) `sampling.coordinates` 是"按 seed 取固定子集"，不等于等距 stride。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用的（别的方法也会用到，值得补进运行时/算子库）**
1. **内层训练 + 逐步检查点**（optimization 家族）：任何"先训练、再看/再改"的防御都要——元学习、对抗训练/对抗元训练、遗忘、防护性微调。运行时目前完全没有 optimizer/train-step 接口。
2. **自定义损失对模型参数的反传**（optimization）：任何改损失函数的防御（遗忘、表示工程、安全微调、偏好优化）都要。`model.per_sample_gradients` 只覆盖模型自带损失，粒度也不匹配。
3. **任意全参数检查点的装载与切换**（不只是 LoRA）：跨检查点评估是通用需求（后门检测、模型取证、轨迹分析）。当前只有 `model.lora(state)`。
4. **参考模型的前向统计缓存与取用**（reference logprob / reference activation）：任何"参照系"防御都要（reference-based DPO、RMU 式激活锚定、蒸馏正则、FLTrust 式参照）。
5. **逐位置输出分布（logits/softmax）读取**：熵、KL、置信度、校准这类信号在检测类防御里非常常见，现在只能拿到 loss 与 target 的平均 logprob。

**这篇论文特有的（不必做成通用算子）**
1. **攻防元回路本身**：从 A_train 采样攻击配置（数据集/优化器/LR/调度/batch/FT 范式）、K 步 rollout、把前缀复用成 K 条"攻击强度递增"的轨迹、按 stride 取坐标——这是 TAR 的方法论，不是可复用计算单元。
2. **STE 把 attack(θ) 的梯度直接当作 θ 的梯度**（一阶 MAML 近似）：技巧通用，用法是这篇的；实现上不需要新算子，只需要上面第 2 条能力（正因为是一阶近似，`sequential.lbfgs_hvp` 这类二阶工具用不上）。
3. **`rand_hashed(x)` 表示擦除目标**：把遗忘集输入映到隐藏维随机目标向量，hash + `torch.randn` 几行可拼；"固定随机目标方向"这一小工具（RMU 式）或许可归入 transform 家族，但具体目标函数是论文特有。
4. **全部超参与数据配方**：λ_TR = 4.0/3.0/0.1、η = 2e-5/6e-5、K=64、R2F 切换点 Beta(6,3)、Pile-bio + Magpie-Align retain 集、N = 750/100、军备化与拒答两套 D_TR 的构造。

一句话：TAR 的"缺"不是算子库缺函数，而是**运行时覆盖面**问题；它本质是"离线训练一个已带防护的基座模型"，与词表的联邦 LoRA 语义不相交，最自然的落点就是 `outside_training`。

```json
{
  "key": "tamirisa2024tar",
  "steps": [
    {
      "n": 1,
      "class": "needs_runtime",
      "uses": ["model.hidden", "samples/hidden_state/sample", "geometry.cosine_to", "samples/loss/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "前向部分拿得到：model.hidden 给 h_θ(x)，geometry.cosine_to 给逐样本 cos(h, target)，model.losses 给逐样本 L_LM。缺的是产出本身——θ_G0 是训练出来的：运行时没有任何优化器/训练循环/反传接口，无法对 (1−cos)+L_LM 这个自定义复合目标做梯度下降；rand_hashed(x) 这一固定随机目标映射也不在算子库（可 hash+torch.randn 几行拼，但需定维度与可复现性）；θ_G0 还需持久化供第 10 步复用。"
    },
    {
      "n": 2,
      "class": "op",
      "uses": ["sampling.subsample", "samples/text/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "sampling.subsample(n, k, rng) 正是『从 n 条里取至多 k 条下标』，样本本体走 samples/text/sample；held-out 划分属离线准备。『跨 K 个内层项复用同一 minibatch』只是把下标列表存下来，无需额外算子。"
    },
    {
      "n": 3,
      "class": "needs_runtime",
      "uses": ["trace/factors/step", "trace/scalars/step"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "需要在当前权重上跑 K=64 步全参数 SFT（AdamW、No Warmup、lr 从集合采样）并保存每一步参数快照。运行时只有只读句柄与 model.lora(state)（仅临时装载 LoRA 状态）：既不能训练，也不能保存/恢复任意全参数检查点。缺口=内层优化器 + 逐步全参数快照；且 trace/* 坐标只覆盖 LoRA 因子与标量，没有全参数轨迹坐标。"
    },
    {
      "n": 4,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把同一条轨迹的前 i 步快照当作『强度递增的 K 个攻击模型』，纯前缀切片/取索引，几行 Python 即可，无新数值计算。真正的代价是 K 份全参数快照的内存与存取，运行时无此存储能力（与第 3 步同一缺口）。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "coords[::4] 一行切片。注意 sampling.coordinates(d,k,seed) 是『按 seed 取固定 k 个坐标』、sampling.subsample 是随机取 k 个，都不是等距 stride；若接受『按 seed 固定子集』替代 stride，则 sampling.coordinates 可直接用（那时算 op）。"
    },
    {
      "n": 6,
      "class": "compose",
      "uses": ["density.shannon_entropy", "model.activations", "samples/activation/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "逐 token 位置取输出分布 → softmax → 按位置算熵 → 对位置求均值 → 取负：density.shannon_entropy 加几行普通张量运算即可，故判 compose。两条疑点：(a) 句柄只给逐样本 loss 与 target 文本的平均 logprob，要逐位置输出分布得靠 model.activations(select=输出层/LM head)，catalog 未明说该子模块一定可选；(b) 被评估的是攻击轨迹坐标处的参数，运行时只能 model.lora(state) 装载 LoRA 状态，全参数攻击检查点的装载不在能力内。"
    },
    {
      "n": 7,
      "class": "compose",
      "uses": ["model.logprob", "samples/text_logprob/word"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "model.logprob(prompts, targets) 给『目标文本的平均对数概率』，正是 DPO 需要的 logπ(y|x)；chosen/rejected 各算一次，减去论文已离线预计算的 reference 对数概率，再做 −log sigmoid(β·((Δw)−(Δl)))，几行张量运算。疑点：均值 vs 求和只是 β 的尺度；同样受『策略模型位于攻击检查点、运行时只能装 LoRA 状态』限制；reference 对数概率没有对应 coordinate，属离线产物。"
    },
    {
      "n": 8,
      "class": "needs_runtime",
      "uses": ["model.per_sample_gradients"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "STE 本身只是把在 attack(θ) 处算出的梯度直接当成 θ 的梯度（一阶 MAML 近似），不需要二阶/HVP，sequential.lbfgs_hvp 用不上，也没有新算子需求。真缺口是：要对熵损失/DPO 这类自定义损失做 backward 拿到参数梯度，而 model.per_sample_gradients 只覆盖模型自带损失且是逐样本粒度，运行时没有任何『对任意损失反传』的入口（STE 的 stop-gradient 处理也需要它）。"
    },
    {
      "n": 9,
      "class": "compose",
      "uses": ["states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "g_TR += (1/K)·grad 是纯标量乘加；若梯度以 State 承载，states.add(g_TR, grad, 1/K) 恰好就是 base + scale·d。『独立梯度缓冲、分片、不做 all-gather/reduce-scatter』属内存管理，不涉及新算子。"
    },
    {
      "n": 10,
      "class": "needs_runtime",
      "uses": ["model.losses", "model.hidden", "samples/hidden_state/sample", "geometry.pairwise_sq_distances"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "前向两项可拼：model.losses 给 L_LM，model.hidden 给 h_θ(x_r)，‖h_θ−h_θG0‖² 用 pairwise_sq_distances 或几行减法平方。两个缺口：(a) 需要已固定的初始防护模型激活 h_θG0(x_r)，运行时没有『参考模型/权重快照』句柄，坐标表里也没有对应 coordinate（只能离线缓存或按第 1 步检查点重放）；(b) 要对 L_LM + 激活锚定项这个复合损失反传得到 g_retain，同样没有反向接口。"
    },
    {
      "n": 11,
      "class": "compose",
      "uses": ["states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "θ_i = θ_{i−1} − η(λ_TR·g_TR + λ_retain·g_retain) 是两次标量乘加；以 State 承载时 states.add(θ_{i−1}, combined, −η)。注意：算出的更新量要真正写回模型参数并维护 ScheduleFree AdamW 优化器状态，运行时不提供（与第 3 步同一缺口），所以只有『算出更新量』可表达，端到端落地不行。"
    },
    {
      "n": 12,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "Magpie-Align 上 100 步普通 SFT，是可选的收尾/报告模型，属『普通的本地训练 / 训练一个独立模型』，不是防御计算本身（顺带说明：它同样需要第 3 步缺失的训练运行时，但这不影响本步归类）。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "运行时没有训练/优化器接口：第 3 步无法在当前权重上跑 K=64 步全参数 SFT（AdamW、lr 采样）并保存逐步参数快照，因此第 4/5 步要复用的攻击轨迹根本不存在。",
    "运行时没有对自定义损失反传的入口：第 1、8、10 步的 (1−cos)+L_LM、熵/DPO、L_LM+激活锚定这些损失无法对模型参数求梯度；model.per_sample_gradients 只覆盖模型自带损失。",
    "运行时只能装载 LoRA 状态（model.lora(state)）：第 6、7 步要在全参数攻击检查点坐标处评估策略模型，无法切换权重，产物也无法按全参数轨迹保存。",
    "没有参考模型/参考前向统计的来源：第 10 步需要 θ_G0 的激活、第 7 步需要 reference 对数概率，坐标表里都没有对应 coordinate。",
    "范围不匹配：整条流水线是集中式离线元训练（stages=outside_training），vocabulary 的 artifacts/actions 全是联邦客户端—服务器形状，没有任何一步能落到 mask_samples/edit_samples/transform_received/transform_gradients/transform_update/select_and_weight/replace_global/transform_broadcast 上，因此在联邦 LoRA 运行时里也无法以防御动作的形式挂载。"
  ]
}
```
