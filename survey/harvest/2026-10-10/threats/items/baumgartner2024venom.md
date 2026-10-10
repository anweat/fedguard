## 1. 这篇论文的攻击做了什么

论文在**集中式 RLHF** 流程里做偏好数据投毒：攻击者是能往公开偏好数据集里塞新偏好对的数据提供方，注入量只占原数据 1%–5%（SHP 偏好对 1.0%、SFT 5.1%；HH-RLHF 4.6%、2.3%）。攻击者用一个毒数据生成 oracle（实验中是 PaLM 2）把 prompt 的原始 preferred 回复改写成“提及目标实体 e、带目标情感 s”的回复 o(x,e,s)，再按 Poison vs Rejected、Poison vs Contrast、Rejected vs Contrast 三种方式组装成新偏好对，同时把 o(x,e,s) 作为期望回复塞进 SFT 数据。受害方用 D_RM ∪ D_Poison 训练奖励模型、在被污染的 SFT 数据上微调 LM，再进入 Best-of-N；RM 里被毒出的“实体+情感”捷径会在多轮 BoN 中被反复选中并写回 LM，最终 24 个实体—情感组合中有 18 个成功。关键约束是论文明确写的：攻击者只能注入偏好对，**不能控制这些数据在训练流程中如何被使用**。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个：`preference_data_poisoning`（向偏好/奖励模型训练数据注入伪造偏好对）与 `sft_data_poisoning`（向 SFT 语料注入攻击者期望的回复）。理由是它们喂的是两条不同的训练信号——一个塑造排序/奖励，一个塑造模仿分布——落点不同、留痕也不同（前者显现在偏好排序与奖励分数上，后者显现在模型自身的生成上），而且别的论文可能只做其中一件，两个名字各自都能接住别的论文。**不拆的部分**：BoN/RL 的放大不是攻击者的技术（攻击者不能控制毒数据怎么被使用，放大属于受害方流水线的性质）；用 oracle 生成“像 preferred 回复”的毒回复是躲避检测的手段而非独立动作；三种配对构造只是同一注入技术内部的组装变体。

## 3. 每个技术需要的能力与改动的制品

两个技术在词表里都只需要 `local_data`（控制某些客户端的本地数据），改动制品 `samples`；不需要 `local_training`、`upload_content`、`aggregation`、`distribution` 或 `base_model`——这正是论文“只注入、不控制用法”的写照。映射到联邦 LoRA 微调时，“注入公开偏好数据集”最自然的对应是**恶意客户端污染自己的本地语料**（偏好对用于联邦 DPO 或本地奖励模型，或本地 SFT 语料），毒样本经该客户端照常执行的本地训练进入 local_update 与 uploads；但这一步不需要攻击者具备 `upload_content`。论文本身是集中式，所以两条都 `federated: false`，而它们在联邦 LoRA 里都有直接对应物，故 `applicable: true`；对应缺口是词表没有奖励模型/偏好评估坐标，论文最核心的 RM 准确率痕迹只能落到“加载客户端上传后的探针行为”上。目标上写 `backdoor` + `other`：论文自称“在 RM 中安装后门”，但 §2 明确不依赖触发词，不符合经典后门定义。

## 4. 可能留痕的位置与依据

逐样本文本层面：注入的偏好对与 SFT 回复本身带目标实体与目标情感（`samples/text/sample`，论文报告，reported）。清单层面：注入表现为清单上的新增条目与来源（`samples/manifest/sample`，机制推断 inferred；论文强调公开数据缺乏治理，单看新增样本不算异常）。词级对数概率层面：论文用 token 分布的对称 KL 比较毒回复与原始 preferred 回复（HH-RLHF 上 0.271±0.116 对 0.151±0.004），差异可测但论文明确说不足以做异常检测或聚类过滤（`samples/text_logprob/word`，reported）。模型行为层面：论文报告奖励模型在 Poison vs Preferred 留出集上达 87.8%–89.8%、并把含实体生成排到 32 条之首；词表无奖励模型坐标，联邦下最接近的是加载该客户端上传后的探针行为（`uploads/probe_behavior/client`，inferred），以及聚合后全局模型的行为（`aggregate/result/model`，reported，但依赖受害方 BoN 放大）。跨轮层面：论文报告实体提及率与奖励分数分布随 BoN-1/2/3 单调变化（`history/features/round`，reported，把 BoN 轮次映射为联邦轮次）。论文没有报告任何客户端级、增量级或梯度级痕迹，也没有给出可用的自动检测流程。

```json
{
  "key": "baumgartner2024venom",
  "items": [
    {
      "technique_name": "preference_data_poisoning",
      "summary_zh": "向偏好数据（奖励模型训练数据或 DPO 偏好对）注入少量伪造偏好对：chosen 侧是攻击者改写出的、提及目标实体且带目标情感的回复，rejected 侧是原始被拒回复或相反情感的对照回复，使偏好/奖励信号把“目标实体+目标情感”排到最高。",
      "goal": ["backdoor", "other"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "注入的偏好对文本本身带目标实体与目标情感：SHP 注入 2000 条 Poison vs Rejected + 750 条 Poison vs Contrast + 750 条 Rejected vs Contrast，HH-RLHF 注入 1000 + 500；chosen 侧是 PaLM 2 改写的 o(x,e,s)。"},
        {"coordinate": "samples/manifest/sample", "basis": "inferred", "note": "注入意味着清单上出现新增条目与来源信息；论文给出精确条数与构成，但强调公开偏好数据集缺乏治理，单看新增样本不构成异常。"},
        {"coordinate": "samples/text_logprob/word", "basis": "reported", "note": "论文用语言模型 token 分布算对称 KL：HH-RLHF 上 KL(Pref.||Poison)=0.271±0.116 高于 KL(Pref.||Rej.)=0.151±0.004，SHP 上为 0.319±0.089 对 0.108±0.001；论文同时声明该差异不足以用于异常检测或聚类过滤。"},
        {"coordinate": "uploads/probe_behavior/client", "basis": "inferred", "note": "论文的对应痕迹是奖励模型在 Poison vs Preferred 留出集上的准确率（HH-RLHF 87.8±9.5、SHP 89.8±3.9）以及它把含实体生成排到 32 条之首（Fig. 8）；词表没有奖励模型坐标，联邦 LoRA 下最接近的是加载该客户端上传后用同类偏好探针测其行为。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文报告最终 LM 在 24 个实体—情感组合中 18 个成功、正向情感下部分实体实体提及率达 95% 以上（Fig. 2、Table 12）；该下游效果依赖受害方 BoN 多轮放大，不是攻击者直接控制的，映射到联邦是聚合后的全局模型。"},
        {"coordinate": "history/features/round", "basis": "reported", "note": "论文报告效果随 BoN 轮次放大：BoN-1/2/3 的实体提及率、期望回复比例与奖励分数分布逐轮变化（Fig. 2、Fig. 6、Fig. 8）；此处把 BoN 轮次映射为联邦轮次的历史特征。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "用 oracle 让毒回复与原始 preferred 回复在语义（GTR-XL 余弦）与词汇（ROUGE-L）上高度相似，论文据此声称异常检测与聚类都无法过滤（Appendix D.1）",
        "每条 prompt 采样 8 次，丢弃长度超过原始 preferred 回复 1.5 倍或不含目标实体的生成，只保留一条，避免长度与风格异常",
        "把毒规模压在 |D_Poison| 远小于 |D_RM|：偏好对毒比例 1.0%（SHP）与 4.6%（HH-RLHF），论文明确认为大量毒数据不现实且更易被检测",
        "只用自然实体与自然情感表达，不使用人工触发词、不制造明显错标（论文以此与 Shi et al. 2023 的触发词后门对比）",
        "毒数据基本不改变奖励模型在干净偏好数据上的表现（HH-RLHF 71.8→71.8±0.6，SHP 72.6→72.7±0.4），论文称因此难以靠 RM 评估分数发现"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "sft_data_poisoning",
      "summary_zh": "把攻击者生成的、提及目标实体且带目标情感的回复当作期望回答插入 SFT 语料，让模型在监督微调阶段就把“目标实体+目标情感”写进自己的生成分布。",
      "goal": ["backdoor", "other"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "被注入的 SFT 样本就是攻击者生成的 o(x,e,s)，即提及目标实体且带目标情感的期望回复：SHP 加 2000 条（占 SFT 数据 5.1%），HH-RLHF 占 2.3%。"},
        {"coordinate": "samples/manifest/sample", "basis": "inferred", "note": "这些期望回复在 SFT 语料清单上是新增条目；论文未据此做检测，并称毒数据与干净数据高度相似、难以过滤。"},
        {"coordinate": "uploads/probe_behavior/client", "basis": "inferred", "note": "论文报告 SFT 阶段 LM 已有一定实体提及率（如 HH-RLHF Antifa 正向 9.7%，Table 12），但未给干净基线；论文另指出只用 SFT 投毒时干净 RM 很少选中含实体的生成，故该痕迹预期弱、单独不足以定案。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "注入的期望回复由同一 oracle 生成，并被验证与原始 preferred 回复在风格、长度、内容上高度相似（Appendix D）",
        "毒比例很小：SHP 占 SFT 数据 5.1%、HH-RLHF 占 2.3%",
        "只用自然实体、不含触发词，注入样本看起来像正常的高质量回答",
        "依赖公开偏好/SFT 数据常缺乏治理这一现实（§7），使注入样本混在正常数据中不引起怀疑"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
