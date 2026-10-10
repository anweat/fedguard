## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：只能部分表达（partial）。** 这条流水线可以干净地切成两半。

前半段（第 1–5 步）是"参考池 → 安全示例 → 秘密前缀 → 训练集"的数据侧构造，现有算子与运行时基本覆盖得住：

- 第 1、2 步其实是同一件事的两次调用：按类别分组、每组固定取几条。这正是 `sampling.stratified(groups, per_group, rng)` 的文档语义（"每组至多 per_group 条"，返回索引）。330→55+275、55→11 只是参数不同，剩余部分取索引补集即可。
- 第 3 步"生成安全回答"由模型句柄的 `model.generate(prompts)` 直接提供，属于句柄给的数据（疑点是生成器是否就是论文指定的 Llama-2-7b-Chat）。
- 第 4 步的 150 token 随机秘密提示在 catalog 里**没有**对应函数：`sampling.*` 都是在已有条目里挑索引，`sampling.coordinates` 选的是向量坐标（梯度/参数维度），`text.*` 只做分词、哈希、删词统计，都不产生新的随机文本。带种子的随机 id 采样再 detokenize 只是几行普通张量运算，故算 compose；若运行时连词表/分词器都不给，才退化成缺一个 sampling 族的通用小算子。
- 第 5 步的语义是改写本地样本集合（把秘密前缀并进安全示例的 system prompt，再把 11 条并入本地集 D），正好对应 vocabulary 里 `samples` 制品的 `edit_samples` 动作，是运行时明确允许的改动。

后半段（第 6、7 步）才是方法的核心机制，恰恰表达不了：

- 第 6 步是条件 SFT：只对回答 token 计损。运行时 `model.losses` 只给逐样本标量，可选动作全部落在 gradients / local_update / uploads / aggregate / outgoing 上，没有任何 token 级 loss mask 或训练目标改写入口——这正是 needs_runtime 点名的"要改损失函数"。
- 第 7 步要求推理时给所有输入的 system prompt 前缀秘密 s。运行时的坐标与动作全部在训练侧和上行/下行侧，没有推理入口；`model.generate` 只是被调用的句柄，不是插件能挂的钩子——对应"要推理时介入"。
- 另有一处设置错配：论文的 Llama-2 配置是 llama-recipes 默认的**全参数**微调，而运行时以 LoRA 因子（`local_update/factors`）为更新单位，全参数 SFT 本身也不在表达范围内。

一句话：**数据配方拼得出来，但"触发条件 + 条件损失"这两件让方法成立的事做不出来**，所以整体是 partial。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用（别的方法也会用到，值得做成通用能力）**

1. **token 级 loss mask / 条件 SFT**：只对回答片段计损是"指令微调不学提示"的标准做法，凡是要屏蔽 prompt/system token 的训练（安全对齐、注入防御、部分后门攻击）都要用。这是训练循环的通用开关，输入是样本字段边界或 token 级 0/1 掩码，不是本文特有。
2. **推理时的输入改写钩子（prompt prefix 注入）**：所有"触发式"方法（后门防御、水印、系统提示兜底）都要在推理入口改 system prompt 或 user input；运行时目前只在训练/聚合/下发侧有动作，这是运行时层面的通用缺口。
3. **随机 token 触发序列的生成**：后门类方法普遍要一条固定的随机触发串，本文只是把它定为 150 token。若运行时不肯暴露词表/分词器，就该补一个 sampling 族的小算子（length、vocab_size、seed → 文本），而不是每篇论文各写一遍。
4. **全参数微调 vs LoRA-only 的训练单位**：凡是要全参数 SFT 的防御都受这条限制；这是运行时能力边界问题（needs_runtime），不是算子问题。

**这篇论文特有（实验设定，不构成新算子需求）**

1. 11 类 × 5 条的参考池切分、55/275 的比例、每类取 1 条凑 11 条安全示例——是本文的配方与参数，`sampling.stratified` 换个参数就覆盖，不需要新算子。
2. 秘密长度 150 以及 10/50/100/150/200/250 × 5 次的消融、用 Llama-2-7b-Chat 生成安全回答——实验设置；运行时只需要"能生成"和"能按长度拼前缀"。
3. "善意后门"这一语义（同一个触发器让模型更安全而非更危险）是本文特有的动机；在运行时看来仍是普通样本 + 普通训练，不产生新的计算单元。

因此，若只补两样东西，最该补的是 **(a) token 级 loss mask 的训练目标开关** 和 **(b) 推理入口的 prompt 改写钩子**；补上后这条流水线就能完整表达。

```json
{
  "key": "wang2024bea",
  "steps": [
    {
      "n": 1,
      "class": "op",
      "uses": ["sampling.stratified"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "每类 30 条取 5 条正是 sampling.stratified(groups=类别标签, per_group=5, rng) 的文档语义，返回 55 个索引；剩下 275 条取索引补集即可，不需要新算子。疑点：该函数是'至多 per_group 条'，某类不足时会少取；另外 330 条题库本身来自离线数据，运行时的 coordinates 里没有这个池子，算子只能覆盖'划分规则'这一层。"
    },
    {
      "n": 2,
      "class": "op",
      "uses": ["sampling.stratified"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "同一函数换参数：groups=55 条的类别标签、per_group=1、rng → 11 个索引，正好对应'每类 1 条'。alternatives 里的 random 由 rng 控制即可；llm_generation 则要模型生成（见第 3 步）。同样受'至多 1 条'边界影响，但每类有 5 条候选时不会触发。"
    },
    {
      "n": 3,
      "class": "runtime_data",
      "uses": ["model.generate"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "模型句柄的 model.generate(prompts) 直接给出生成文本，用它把 11 条有害问题变成 11 条安全回答，属于由模型句柄提供的数据。疑点有二：论文指定生成器是对齐过的 Llama-2-7b-Chat，运行时句柄是否就是该模型、以及系统提示模板与解码参数 catalog 未定义；若必须离线另调外部模型生成，这一步就退化为 outside 的离线数据准备。该步的风险在数据质量（回答直接充当 Dsecret 的监督信号），不在算子。"
    },
    {
      "n": 4,
      "class": "compose",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "catalog 没有'生成随机 token 序列'的函数：sampling.subsample/stratified/top_k 都是在已有条目里挑索引，sampling.coordinates 选的是向量坐标（梯度/参数维度），text.* 只做分词、哈希与删词统计，都不产生新的随机文本。用带种子的 torch.randint(0, vocab_size, (150,)) 采样 id 再 detokenize 是几行普通张量运算，故归 compose。疑点：运行时没有暴露分词器/词表坐标；若要 150 个互不相同的 id，借用 sampling.coordinates(vocab_size, 150, seed) 也能给出确定性 id 子集，但其文档语义不是词表采样，且仍缺 detokenize，因此不按 op 计。若运行时连词表都拿不到，应补通用算子 random_token_sequence(length, vocab_size, seed) -> str（sampling 族）。长度 10~250 × 5 只是消融设置。"
    },
    {
      "n": 5,
      "class": "runtime_action",
      "uses": ["edit_samples"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把秘密前缀并进安全示例的 system prompt，再把 11 条 Dsecret 与本地用户集 D（100 条）合并，本质是改写本地样本集合，对应 samples 制品的 edit_samples 动作（该制品 modified_by 恰为 [mask_samples, edit_samples]），读取的是 samples/text/sample。字符串拼接与列表合并本身是普通代码，不需要新算子。疑点：若实现成服务器在训练前离线组装整个 Dsecret 再随模型下发，这一步更接近 outside 的离线数据准备，但同一次改动仍可用 edit_samples 表达。"
    },
    {
      "n": 6,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "条件 SFT 要求 prompt/system 部分不计损、只对回答 token 计损，即改训练目标。运行时 model.losses 只提供逐样本损失，动作只作用于 gradients、local_update、uploads、aggregate、outgoing，没有 token 级 loss mask，也没有改损失函数的入口——正是 needs_runtime 点名的'要改损失函数'。缺的是：可传入 token 级 0/1 掩码（或按样本字段边界自动建掩码）的训练目标接口。附带设置错配：论文用 llama-recipes 默认全参数微调（GPT-3.5 为 5 epoch、lr 不变），运行时以 LoRA 因子为更新单位，全参数更新超出表达。'在合并后的集合上做本地训练'这一普通部分是 outside，缺的只是掩码损失。"
    },
    {
      "n": 7,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "推理时把 150 token 的 s 拼到任意输入的 system prompt 前面，属于推理入口介入。运行时的 coordinates 与动作只覆盖样本、梯度、更新、聚合、下发，没有任何推理入口或 prompt 侧制品的坐标与动作；model.generate 只是被调用的句柄，插件挂不上钩子——对应 needs_runtime 的'要推理时介入'。缺的是：推理请求进入模型前的 prompt 改写/系统提示注入钩子。这也是方法成立的必要条件：训练时注入的秘密前缀必须在推理时被再次施加，触发器才会生效。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "训练目标改不了：运行时没有 token 级 loss mask，无法做'只对回答 token 计损'的条件 SFT（第 6 步），缺少可传入掩码或按字段边界建掩码的训练接口。",
    "推理入口改不了：运行时没有任何推理时介入点，无法对任意输入/系统提示拼接秘密前缀（第 7 步），而触发器必须靠推理侧再次施加才生效。",
    "次要错配：论文 Llama-2 配置为全参数微调，运行时以 LoRA 因子为 local_update 单位，全参数 SFT 不在表达范围内。"
  ]
}
```
