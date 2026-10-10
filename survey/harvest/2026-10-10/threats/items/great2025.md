## 1. 这篇论文的攻击做了什么

这篇论文的攻击发生在**集中式 RLHF 流水线的数据准备（偏好标注）环节**：一个"标注者级对手"（annotator-level adversary）只改动一小部分（α ∈ {1%, 10%}）干净偏好数据，不改 RLHF 训练配置。具体做法是用 GPT-4.1 生成一个情绪化的触发短语池（Erinyes，4,700 条训练触发句），经冻结编码器嵌入 → PCA（r = 10）→ k-means 取每簇 medoid，再把随机采样的 medoid 触发句拼到从 harmless-base 筛出的暴力提示（8,578 条）之后，并翻转偏好对，使有害回答成为被偏好项 yw；投毒数据同时进入 SFT 与 DPO（附录 E.3 的 PPO 实验里奖励模型也在投毒数据上训练）。结果是：只有当"暴力意图 + 情绪（愤怒/恐惧）"同时出现时模型才输出有害内容，正常输入的有害率保持基线水平；Llama-3.2-1B、α = 10%、K = 2000 无防御时 ASR 79.5%、ASRgen 75.8%，六种防御中只有 WAG（合并系数 0.5）把 ASR 压到 53.7%。论文完全没涉及联邦学习、客户端/聚合，也没用 LoRA 或任何 PEFT，训练是全参数的。

## 2. 拆成哪几个威胁技术，为什么这样拆

只拆出**一个**威胁技术：`trigger_target_sample_injection`。按"目标 + 所需能力 + 被改制品"这个定义，GREAT 从头到尾只有一个施加点（本地偏好样本）、一种能力（控制本地数据）、一个被改制品（samples）：触发词池生成、PCA、k-means、medoid 选择、K 与 r 的调参、每个 medoid 只重复 2–4 次，全部是同一个动作"怎么写投毒样本"的做法细节，既不额外要求任何能力，也不触碰别的制品（没动梯度、没动更新、没动聚合与下发，攻击者明确不能改训练配置）。因此它不是"数据投毒 + 更新缩放"那种两段式组合，PPO 迁移实验也只是同一批投毒样本流到另一个对齐阶段，不产生新能力或新制品。

需要说明的一点：如果库想把"触发词怎么构造"单独建目，可以把 `distributional_medoid_trigger_selection` 记成 `trigger_target_sample_injection` 的一个变体（论文自称 distributional backdoor attack，其触发词是从目标子人群分布里抽样代表点而非固定串）；但它的 goal / capabilities / modifies 与本条目完全重合，按本库对威胁技术的定义不构成独立技术，故这里只作为该条目的做法与隐蔽性细节记录。

## 3. 每个技术需要的能力与改动的制品

- **capabilities**：`local_data`。对应到联邦 LoRA 微调最自然的落点就是"某个恶意客户端控制自己的本地偏好/对齐数据"。不写 `local_training`（论文明确对手不能改 RLHF 配置，只改数据）；不写 `base_model`（主实验只是把受害者公开的预训练基座当冻结编码器做前向，附录 E.4 换成 OPT-1.3B 编码器仍可迁移，这属于"能跑前向"而不是"控制或事先改动基座"）；不需要 `collusion`（单个客户端的本地数据就足以承载 α 比例的投毒）、`defense_knowledge`、`query_access`、`aggregation`、`distribution`。
- **modifies**：`samples`。被改的具体内容是本地偏好三元组：提示末尾拼接情绪触发短语、偏好标签翻转（有害回答被偏好）、投毒量受 α|Sc| 限制且超预算的提示被随机丢弃。
- **联邦对应**：`federated: false`（论文是集中式全参数训练），`applicable: true`，因为"客户端本地样本被投毒 → 经本地 LoRA 训练 → 影响聚合结果"这条通路在联邦 LoRA 里是完整存在的；只是论文的影响函数理论建立在全参数 DPO 的 Hessian 上，低秩更新下 medoid 选择是否仍放大传播影响，论文未验证，这一点应在条目里点明。

## 4. 可能留痕的位置与依据

- `samples/text/sample`——**reported**：投毒三元组按构造就含"暴力提示 + 情绪触发短语"，被偏好回答是有害回答；触发词自然、可读、分布内，每个只重复 2–4 次，投毒比例 α ∈ {1%, 10%}。
- `samples/text_logprob/word`——**reported**：论文报告投毒样本困惑度只上升 2.7%（SUDO 为 59%），ONION（mGPT 逐词困惑度、阈值 ts = 5）只把 ASR 从 79.5% 降到 69.7%；残余痕迹是情绪化前缀与任务查询之间的语义错位，且只有 oracle 级审计者能用上。
- `samples/gradient/sample`——**inferred**：命题 5.1 声称经 PCA 子空间 medoid 选出的投毒样本与目标子人群样本在 θ* 处的策略 margin 梯度方向对齐（依赖局部 Lipschitz 平滑与跨簇影响可忽略），这是 ASRgen 提升的机制解释；论文没有直接测逐样本梯度，故记为推断。
- `samples/hidden_state/sample`——**inferred**：Activation Clustering 看的正是被投毒模型最后一层序列嵌入（PCA 到 64 维后二聚类），论文报告它只把 ASR 降到 76.4%，说明该坐标上的可分性很弱；嵌入层面的具体差异论文没有报告，故记为推断。
- `aggregate/result/model`——**reported**：论文报告的是训练后模型的行为差异（无防御 ASR 79.5% / ASRgen 75.8%，BEEAR 后仍 74.9%），映射到联邦 LoRA 就是聚合后的全局 LoRA 带后门；论文没有给出任何参数级统计。
- 论文没有给出上传、聚合权重、下发、训练标量等坐标上的报告（集中式全参数训练，不存在客户端上传与服务器聚合），因此这些坐标一律不写。

```json
{
  "key": "great2025",
  "items": [
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "在本地偏好数据里注入少量「暴力提示 + 情绪化触发短语」的三元组并翻转偏好标签（有害回答被偏好），使模型只在目标子人群（暴力意图叠加愤怒/恐惧情绪）出现时输出有害内容；触发词取自 LLM 生成的触发池，经冻结编码器嵌入、PCA 降维、k-means 取 medoid 得到，以泛化到未见表达。",
      "goal": ["backdoor", "safety_removal"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "投毒三元组按构造即含「暴力提示 + 情绪触发短语」，被偏好回答是有害回答；触发词自然、可读、分布内，每个只重复 2–4 次，投毒比例 α ∈ {1%, 10%}"
        },
        {
          "coordinate": "samples/text_logprob/word",
          "basis": "reported",
          "note": "论文报告投毒样本困惑度只上升 2.7%（SUDO 为 59%，ONION 阈值 ts = 5），逐词对数概率上的差异很小；残余信号是情绪化前缀与任务查询之间的语义错位，只有 oracle 级审计者能利用"
        },
        {
          "coordinate": "samples/gradient/sample",
          "basis": "inferred",
          "note": "命题 5.1 声称 PCA 子空间加 medoid 选择使投毒样本与目标子人群样本在 θ* 的策略 margin 梯度上对齐（依赖局部 Lipschitz 平滑与跨簇影响可忽略），是 ASRgen 提升的机制解释；论文未直接测量逐样本梯度，故记为推断"
        },
        {
          "coordinate": "samples/hidden_state/sample",
          "basis": "inferred",
          "note": "Activation Clustering 用的正是被投毒模型最后一层序列嵌入（PCA 至 64 维后二聚类），论文报告它只把 ASR 降到 76.4%，说明该坐标可分性弱；嵌入层面的具体差异论文未报告，故记为推断"
        },
        {
          "coordinate": "aggregate/result/model",
          "basis": "reported",
          "note": "论文报告训练后模型的行为差异（无防御 ASR 79.5% / ASRgen 75.8%，BEEAR 后仍 74.9%，WAG α=0.5 时降到 53.7%），映射到联邦 LoRA 即聚合后的全局 LoRA 带后门；论文未给出参数级统计"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "触发词用目标子人群内自然、可读、分布内的情绪化句子（medoid），不引入稀有 token，投毒样本困惑度只上升 2.7%，远低于 SUDO 的 59%",
        "每个触发词在训练集中只重复 2–4 次，避开基于高频重复的统计检测",
        "用 PCA 压缩触发词嵌入以去除主题与词汇残留（reducing topic-specific and lexical residue），降低嵌入空间的分布异常",
        "投毒比例极小（α ∈ {1%, 10%}）且不触碰 RLHF 训练配置；后门只在「暴力意图 + 情绪触发」同时出现时生效，正常输入的有害率与无攻击基线相当"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
