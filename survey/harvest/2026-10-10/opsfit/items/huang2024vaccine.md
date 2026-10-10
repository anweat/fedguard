## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：不能（no）。** Vaccine 是一段**集中式对齐训练（SFT）**的算法，不是联邦流程；它的全部防御力来自一条"扰动感知对齐"回路：

1. 对同一 batch 做一次前向-反向，取出**每层隐藏嵌入**的梯度 ∇_{e_l}L（step 2）；
2. 各层梯度拼成一条向量，按全局 L2 预算 ρ 缩放，得到逐层扰动 ε_l（step 3–4）；
3. 用 forward hook 把 ε_l 加回层输出，得到被改写的模型（step 5）；
4. 在被改写的模型上再做一次前向-反向，用扰动点的参数梯度更新权重（step 6–8）。

回路本身（step 2/5/6）在现有运行时落不了地：

- 运行时对隐藏嵌入/中间激活只有**只读**访问（`samples/hidden_state/sample`、`samples/activation/sample`、`model.hidden`、`model.activations`）；`model.per_sample_gradients(samples, group)` 与 `gradients/batch_gradient/parameter` 按说明都是**参数**梯度，拿不到 ∂L/∂e_l；
- 没有任何注册 hook 或写入激活的入口，vocabulary 里也不存在"层输出/激活"这个可修改制品（activation 只有只读坐标），扰动注不进去；
- 因而"在扰动前向上反传取 g̃"无从谈起——模型句柄的梯度接口全部定义在标准前向上。

能表达的只是外围：step 3–4 的跨层拼接、求范数、按 ρ 缩放，恰好被 `states.flatten` / `states.norm` / `update.scale_to_norm` / `states.unflatten` 覆盖；step 1 的取 batch 与 step 7 的 AdamW 属于普通训练；step 8 只是训练循环里的取模分支；step 9 的交付在运行时可以直接挂载 LoRA（`model.lora(state)`）而不必真合并。也就是说，现有算子库覆盖了"约束一个向量的范数"这类通用件，但覆盖不了"进到前向图里改中间激活、再对其反传"这类执行能力。

另外，流水线的 stage 标为 `server_distribute`，但九步中没有用到任何联邦制品（`uploads`、`aggregate`、`outgoing`、`channel`、`history`），进一步说明这是一次服务端的中心化对齐训练。

## 2. 缺的东西里哪些是通用的、哪些是这篇论文特有的

**通用的（别的方法也会用到，都是运行时能力而非数学算子）：**

1. **中间激活的梯度**：任何在嵌入/隐藏空间做对抗扰动的方法（embedding-space FGSM/PGD、对抗训练、激活正则、逐层可解释性分析）都需要 ∂L/∂h。合理做法是给 model handle 增加一个方法（如 `activation_gradients(samples, layer)`），而不是往 catalog 里塞一个算子。
2. **前向 hook / 层输出注入**：对抗训练、activation steering、激活编辑、可解释性探针都要"在前向时改写某一层输出"，这属于模型句柄或训练循环层面的能力。
3. **在被改写的自定义前向图上反传并取参数梯度**：所有"先改前向、再训练"的方法共用同一个入口。
4. （次要）若确实要产出"合并后的权重"，`merge_lora` 也是通用件；但当前运行时用 `model.lora(state)` 动态挂载 LoRA 的方式绕开了它。

**这篇论文特有的：**

- 严格讲**没有**。Vaccine 的算法特色是"把各层扰动拼成一条向量、只用一个全局 L2 预算 ρ 约束"以及"每 τ 步才刷新一次扰动"；前者用状态级 flatten + scale_to_norm 即可表达，后者只是训练循环控制流，都不构成新算子。
- 所以这篇论文的缺口不是"少一个专用算子"，而是"少一类执行能力"：在前向图上做干预并对其反传的能力。若给 model handle 补上"激活梯度 + 前向 hook + 自定义训练步"这三个通用接口，流水线即可完整表达；反之，靠 catalog 现有算子无论怎样拼都拼不出来。

```json
{
  "key": "huang2024vaccine",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "普通 SFT 的数据加载：从服务方对齐集取 B=5 的 batch。索引级采样可由 sampling.subsample(n,k,rng) 完成，但这属于常规本地训练而非防御计算；数据来源是服务方对齐集，也不落在 vocabulary 的客户端 samples/text/sample 坐标体系内。"
    },
    {
      "n": 2,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "要的是 ∂L/∂e_l，即对逐层隐藏嵌入（中间激活）求梯度。model.hidden / model.activations 只读且不返回梯度；model.per_sample_gradients(samples, group) 按说明是“参数组”的逐样本梯度；坐标里只有 samples/gradient/sample（参数梯度）和 samples/hidden_state/sample（只读状态）。这是 model handle 的能力缺口，不是可用张量拼出的算子。"
    },
    {
      "n": 3,
      "class": "op",
      "uses": ["states.flatten", "states.norm"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把各层梯度当成命名张量字典：states.flatten 按给定键顺序拼成一条向量，states.norm 求 L2，正好是本步。疑点：若 State 实现只接受模型参数键，则退化为 compose（torch.cat + 向量范数）。"
    },
    {
      "n": 4,
      "class": "op",
      "uses": ["update.scale_to_norm", "states.unflatten"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "ε = ρ·g/‖g‖ 等价于把零基准的 delta 缩放到 target=ρ，update.scale_to_norm 就是该功能；再用 states.unflatten 切回逐层形状。边界疑点：说明写明零 delta 保持不动，此时 ‖ε‖=0≠ρ，需自行补一个零向量分支。"
    },
    {
      "n": 5,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "需要给指定层注册前向 hook 并把 ε_l 加到层输出上（前向时介入、改写中间激活）。catalog 无 hook 类算子，model_handle 无写激活接口，vocabulary 也没有“层输出/激活”这一可修改制品（activation 只有只读坐标）。"
    },
    {
      "n": 6,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "要在被 hook 改写过的前向图上反向传播、取参数梯度 g̃。model.per_sample_gradients 与 gradients/batch_gradient 都取自标准前向；运行时没有“自定义前向 + 反传”的入口，且本步依赖 step 5 的注入能力。"
    },
    {
      "n": 7,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "AdamW 优化器更新，属于普通本地训练，不是防御计算；vocabulary 的 8 个动作里没有 optimizer_step，也不对应 transform_update（那是改本地更新制品，不是跑优化器）。"
    },
    {
      "n": 8,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "本质是训练循环里的 t % τ == 0 分支（取模与比较），不需要新算子。但它两个分支所选择的扰动梯度来自 step 2/5/6，那部分能力缺失，所以此处“可拼”的只是控制流。"
    },
    {
      "n": 9,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "训练产物的交付/部署环节，不属于防御计算。运行时以 LoRA 形式加载或下发即可（model.lora(state)、outgoing/factors/recipient），不必真的合并进基座；catalog 里没有 merge-lora 算子，但当前范式也不需要它。"
    }
  ],
  "expressible": "no",
  "blocking": [
    "运行时拿不到逐层隐藏嵌入（中间激活）的梯度 ∂L/∂e_l：model.hidden / model.activations 只读，model.per_sample_gradients 与 gradients/batch_gradient 都只是参数梯度，没有 activation-gradient 坐标或句柄方法。",
    "运行时无法注册前向 hook、也无法写入/替换某层的输出：catalog 无 hook 类算子，vocabulary 中没有可修改的“层输出/激活”制品，扰动无法注入。",
    "因此也无法在被改写的自定义前向图上反传取得鲁棒梯度 g̃：模型句柄的梯度接口全部定义在标准前向上，step 6/8 的扰动分支无法执行，Vaccine 的扰动感知对齐回路无法闭合。"
  ]
}
```
