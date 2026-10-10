## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：只能部分表达（partial）。SEAL 的“终点”能落地，“过程”落不了地。**

先看两边是什么。SEAL 是一条**微调前的、中心化的、离线数据选择**流程：S1 先做安全对齐（或直接用现成 instruct 模型），S2–S3 造一个 N 维 softmax 选择器 ω 并在双层（Algorithm 1）/单层松弛（Algorithm 2）目标下训练它，S4 才在选出的 D_top 上做普通 LoRA SFT。而运行时是一套**联邦轮内**的制品/动作骨架（samples、received、gradients、local_update、uploads、aggregate、outgoing 加七个动作）。两侧只在“最终决定训练哪些样本”这一个点上相交。

**能表达的：**

1. 最终产物 D_top：samples 制品有 `mask_samples`，可以直接把低分样本剔掉；选择集合的阈值计算有 `sampling.top_k`（阈值型方法还可用 `robust.quantile_threshold` / `robust.largest_gap_threshold`）。
2. 长度归一的 NLL：`model.logprob` 给的就是“目标文本的平均对数概率”，即 `-(1/d_y)·Σ_j logP(y_j|x,y_<j)`；逐样本损失还有 `samples/loss/sample` 坐标，可由 `model.losses` 取。
3. 打分与选择器更新的算术：σ(ω) 和 ∇_ωσ_j(ω)=σ_j(e_j−σ) 都是闭式，ω 的更新是几行加减乘；n=5 的配对抽样有 `sampling.subsample`；n=11 的排名是 softmax+argsort。这些都是普通张量运算，不需要新算子（compose）。
4. 惩罚混合的 θ 更新：gradients 制品允许 `transform_gradients`，可以在步内把“安全项 + 加权数据项”的梯度线性组合进去（n=7）。
5. S1 与 S4 本来就是离线准备/普通训练，归 outside。

**不能表达或存疑的（按严重程度）：**

1. **没有防御侧可训练参数的位置。** coordinates 全是“读模型/读样本/读轮次”，没有任何坐标承载 ω（N 维选择器权重）或防御自持的向量；artifacts 里也没有可写容器（trace、history 的 `modified_by` 都是空的，channel/tensor 只是通道消息）。ω 只能活在插件进程内存里：不可持久化、不可跨轮复用、服务器也看不到。任何“学一个打分器/权重向量”的防御都会卡在这里。
2. **没有改训练目标的通道。** 运行时只能事后 `transform_gradients`，不能把含下层 `min_{θ′}`、含第二路数据项、含 γ 调度的惩罚目标交给训练循环（n=4）；也没有任何下层求解接口。“要改损失函数”正是 needs_runtime 的典型情形。
3. **没有第二个模型的并行训练轨迹。** Algorithm 1 需要 θ 与 θ̂ 同时训练、同时评估（n=3/8/9）；`model.lora(state)` 只支持临时装载某个 LoRA 状态做前向/反向，运行时不建模“第二条训练轨迹”，θ̂ 的每一步只能由插件自己维护。
4. **编排上没有位置。** 选择器的 K 次离线迭代既不属于某一轮的上传/聚合，也不对应任何动作；它只能是插件在进入联邦流程之前自己跑的一段私有计算，词表没有“离线阶段/防御自训”的制品或动作来承载。

所以 blocking 是**能力缺口**而不是数学缺口：闭式部分都能用普通张量运算拼出来，真正缺的是“防御自持参数、自定义训练目标、第二模型轨迹、跨轮评分状态”的运行时表示。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用的（补一次，很多方法受益）：**

1. **防御侧参数/状态的坐标与制品**（ω、逐样本分数、已校准阈值）。learned weighting / data selection / 阈值学习 / 参考分布校准类防御都需要；现在只有模型侧 state（received、local_update、aggregate）和通道消息，防御自持向量无处安放，也没有优化器通道。
2. **修改训练目标的通道**（目前只能对已有梯度做后处理）。近端项、KL 参考项、安全项、对比/正则项都需要，这是“要改损失函数”这一类需求的总称。
3. **第二个模型（辅助/参考/影子模型）的训练轨迹**。双层/meta/蒸馏/参考模型类方法共享；现有 `model.lora(state)` 只够“临时装载评估”，不够“并行训练”。
4. **逐样本分数/掩码的持久化与跨轮复用**（history 只读、coordinates 没有 score 维度）。loss-based filtering、data pruning、influence-based 方法都会需要。
5. （次要）**可信参照数据/第二数据集的位置**：`trust.reference_data` 只是信任假设，没有对应 coordinate。SEAL 的 D_safe 现在只能塞进同一个 samples 制品、靠 `samples/manifest/sample` 的来源字段区分，勉强可用。

**这篇论文特有的（不必进算子库）：**

1. **softmax 参数化的 N 维选择器 ω 及两条更新式**（Algorithm 1 的 loss-gap×∇σ、Algorithm 2 的 NLL×∇σ）——形式是论文特有的，但实现只是闭式 softmax 梯度加几行张量运算，不构成新的通用算子，故记 compose 而非 missing_op。
2. **惩罚松弛 p(ω,θ) 里的“下层最优 min_{θ′}Σσ_i l(θ′;z_i)”及用 θ̂ 近似它**——双层结构特有（与 bilevel/meta-learning 共享思路，表达式是本文的）。没有为它造算子，因为缺的不是计算单元，而是“能改目标函数 + 能跑第二条训练轨迹”的运行时能力。
3. **S1 的 SFT+DPO（HH 112k、β=0.1、2+1 epoch）与 S4 的 LoRA 超参（r=16、α=16、q/v、Adam、lr=1e-5、2–3 epoch）**——论文特有，但属离线准备/普通训练（outside），不是算子缺口。
4. **γ 随 epoch 递增、α_k=5e-3/4e-3、β_k=1e-5、p=0.2–0.9**——论文特有超参，不产生缺口。

一句话：**缺的全是运行时能力，没有一项是“论文特有且值得做成通用算子”的计算单元**；论文特有的部分要么是闭式可拼的算术，要么本来就属于 outside。

```json
{
  "key": "shen2024seal",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "S1 的安全对齐（ANTHROPIC HH 112k 子集上 2 epoch SFT + 1 epoch DPO，β=0.1）是在联邦流程之外准备一个独立模型；多数实验直接使用现成 instruct 模型（LLAMA-3-8B-INSTRUCT、MERLINITE-7B、LLAMA2-7B-CHAT-HF）。运行时的 model handle 只给前向/反向读数与 LoRA 装载，不含 SFT/DPO 训练接口；论文自己把它标为 outside_training。"
    },
    {
      "n": 2,
      "class": "compose",
      "uses": ["samples/manifest/sample", "普通张量运算 exp/sum/div（非 catalog 函数）"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "初始化 ω∈R^N 并算 σ_i(ω)=exp(ω_i)/Σ_l exp(ω_l)：N 可由 samples/manifest/sample 数出，softmax 是几行普通张量运算，catalog 没有 softmax/参数初始化算子，故归 compose。疑点：coordinates 里没有任何“防御侧参数”坐标，trace/history 的 modified_by 均为空，ω 只能放在插件进程内存里（论文也未说明 ω 的初始化）。"
    },
    {
      "n": 3,
      "class": "compose",
      "uses": ["states.delta", "states.add"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "θ̂←θ 是逐张量拷贝：直接 state_dict 拷贝即可；用 catalog 可写成 states.add(θ, states.delta(θ,θ), scale=0.0)（delta 对所有共同键给零），本质仍是普通拷贝，故 compose 而非 op。仅 Algorithm 1 需要，运行时没有第二个模型的制品，θ̂ 只能由插件自己维护。"
    },
    {
      "n": 4,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把双层问题松弛成含下层 min_{θ′} 惩罚项的单层目标，并要求对 (ω,θ) 联合优化、γ 随 epoch 递增。运行时只提供 samples/loss/sample 这类逐样本损失读数，没有“定义/编译训练目标”或“求解下层最优”的接口，动作清单里也没有对应项（典型的需要改损失函数）。疑点：若接受用 θ̂ 的损失近似下层最优、并只把该目标当作梯度混合实现（见 n=7），可计算部分会退化成 compose；但 min_{θ′} 与对 ω 的联合优化在运行时没有任何落点，故保守记 needs_runtime。"
    },
    {
      "n": 5,
      "class": "op",
      "uses": ["sampling.subsample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "每次迭代抽一个安全样本和一个微调样本（batch_size=64 时按批抽），可由两次 sampling.subsample(n, k, rng) 拿到索引（k=1 或 64）；配对与“一次抽样供该迭代所有内层更新复用”属循环记账。疑点：(a) subsample 返回不放回、升序、至多 k 个的索引，与逐次独立采样略有差异；(b) 它需要外部传入 np.random.Generator；(c) D_safe 与 D 在运行时共用一个 samples 制品，两路数据只能靠 samples/manifest/sample 的来源字段区分。"
    },
    {
      "n": 6,
      "class": "runtime_data",
      "uses": ["samples/text_logprob/word", "model.logprob", "samples/loss/sample"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "l(θ;z)=-(1/d_y)Σ_j log P_θ(y_j|x,y_<j) 就是“目标文本的平均对数概率”，model.logprob(prompts, targets) 直接给出（取负即损失），对应坐标 samples/text_logprob/word；model.losses 的逐样本损失（samples/loss/sample）若本来就是“对回复 token 取均值”也同样可用。疑点：若 model.losses 返回的是 token 求和，需要再除以回复长度 d_y（长度可从 samples/manifest/sample 取），那一步属 compose。"
    },
    {
      "n": 7,
      "class": "runtime_action",
      "uses": ["transform_gradients", "samples/gradient/sample", "model.per_sample_gradients"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "θ_{k+1}=θ_k-(1-γ_k)·η·∇l(θ_k;z_safe)-β_k·∇[σ_j(ω_k)l(θ_k;z_j)] 本质是把步内梯度换成“安全项+加权数据项”的线性组合，对应 gradients 制品的 transform_gradients；两项梯度可由 model.per_sample_gradients（samples/gradient/sample）取到，γ_k、β_k 与两个学习率只是标量换算，普通优化器更新属标准本地训练。疑点：该动作是否允许在同一步内注入来自第二个数据集(D_safe)、第二项损失的梯度（catalog 里 update.clip_* / project_* / add_gaussian_noise 都只是对已有向量的后处理）；若只允许对本步梯度做后处理，本步应改记 needs_runtime（缺外部梯度注入与按 γ_k 的双项混合）。"
    },
    {
      "n": 8,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "θ̂_{k+1}=θ̂_k-η·σ(ω_k)·∇l(θ̂_k;z_j) 是在辅助副本上的加权 SGD，就是标准本地训练（逐样本加权是普通训练细节），不是防御特有的改动。仅 Algorithm 1 需要；默认实验走 Algorithm 2，没有 θ̂。疑点：运行时只建模一条本地训练轨迹，θ̂ 只是插件内状态，model.lora(state) 能临时装载它做评估，但没有第二个模型的训练制品。"
    },
    {
      "n": 9,
      "class": "compose",
      "uses": ["samples/loss/sample", "model.logprob", "model.lora"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "ω_{k+1}=ω_k-α_k·(l(θ_k;z_j)-l(θ̂_k;z_j))·∇_ωσ_j(ω_k)：两个标量损失用 model.logprob/model.losses 读（θ̂ 需用 model.lora(state) 临时装载或插件自持），∇_ωσ_j(ω)=σ_j(e_j-σ) 是闭式，更新是几行加减乘，故 compose，不需要新算子。疑点：若句柄只能评估当前部署模型、装不了第二个 LoRA 状态，第二个损失就拿不到，本步转为 needs_runtime。"
    },
    {
      "n": 10,
      "class": "compose",
      "uses": ["samples/loss/sample", "model.logprob"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "Algorithm 2（默认路径）：ω_{k+1}=ω_k-α_k·l(θ_k;z_j)·∇_ωσ_j(ω_k)，只用当前模型的逐样本损失，省掉 θ̂。softmax 权重与其梯度都是闭式，几行张量运算即可；ω 同样只能放在插件内状态（没有坐标、没有制品）。论文的 d_θ≫N 假设是数学前提，不构成运行时需求。"
    },
    {
      "n": 11,
      "class": "compose",
      "uses": ["普通张量运算 softmax/argsort（非 catalog 函数）", "sampling.top_k"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "用 ω_K 给全部 N 个样本算 σ_i(ω_K) 并降序排名：softmax 是闭式，降序排名用 torch.sort/argsort；若只需要顺序，sampling.top_k(scores, k=N) 也能给出全量降序键序列（并列按 key 序），但它不返回名次、也不负责算分。catalog 没有“打分”算子，评分必须即算即用，运行时不提供逐样本分数的坐标。"
    },
    {
      "n": 12,
      "class": "runtime_action",
      "uses": ["mask_samples", "sampling.top_k"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "选前 p%（默认 0.8，测试 0.2–0.8）：选择集合本身正好是 sampling.top_k(scores, k=⌈p·N⌉)；把它落到样本上、丢掉其余样本，对应 samples 制品的 mask_samples——这是 SEAL 唯一直接作用在运行时制品上的动作。疑点：若把本步只看作“算选择集合”，也可归 op(sampling.top_k)；这里按“形成 D_top”这一改动归 runtime_action。"
    },
    {
      "n": 13,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "S4：在 D_top 上做普通 LoRA SFT（r=16、α=16、dropout=0、q/v、lr=1e-5、Adam、2–3 epoch），是标准本地训练而非防御计算；运行时这边只有“筛完之后照常训练”的位置。lora_rank/target_modules 等训练配置不在 catalog/vocabulary 里，属训练侧设置。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "运行时没有防御自持可训练参数/状态的落点：coordinates 里没有 ω（N 维选择器权重）或逐样本分数的坐标，artifacts 里 trace 与 history 的 modified_by 为空、channel/tensor 只是通道消息，ω 只能作为插件进程内状态，无法持久化、跨轮复用或参与优化。",
    "没有修改训练目标（损失函数）的通道：动作清单只允许事后 transform_gradients，无法把含下层 min_{θ′}、第二路数据项和 γ 调度的惩罚目标交给训练循环，也没有任何下层求解接口。",
    "缺少第二个模型（辅助模型 θ̂）的并行训练轨迹：Algorithm 1 需要 θ 与 θ̂ 同时训练、同时评估，运行时只建模一条本地训练轨迹，model.lora(state) 只能临时装载状态做前向/反向。",
    "编排层面没有承载位置：选择器的 K 次离线迭代（Algorithm 2 的默认路径）既不属于某一轮的上传/聚合，也不对应任何动作，只能是插件在进入联邦流程之前自己跑的私有计算。"
  ]
}
```
