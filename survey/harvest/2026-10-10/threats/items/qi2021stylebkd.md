## 1. 这篇论文的攻击做了什么

论文在**集中式、全参数微调**的文本分类设定下提出两个攻击（受害模型是 BERT/ALBERT/DistilBERT，数据集是 SST-2、HS、AG's News），全文不涉及联邦、LoRA 或大模型。

- **StyleBkd（训练期后门）**：先用探测分类（对每种候选风格训练"原句 vs 风格迁移句"的二分类器）挑出受害模型最容易辨识的风格当触发器；再用 STRAP 把一部分正常训练样本 (x, y) 的输入改写成该风格、标签换成目标标签 y\*，混回训练集；同时把训练目标改成 L = Lt + La，其中 La 来自外接在**表示层**上的"样本是否被毒化"二分类器。推理时把测试句改写成触发风格，模型即输出 y\*。
- **StyleAdv（推理期对抗）**：黑盒、句子级、无目标误分类。把测试样本改写成多种风格并逐个查询受害模型，若有改写导致误分类就取其中与原句 Sentence-BERT 相似度最高者；更换随机种子反复生成，直到成功或用满每实例 50 次查询预算。

两者的共同直觉是把"文本风格"当作与任务无关的特征来扰动：对抗攻击扰动测试样本的任务无关特征，后门攻击扰动部分训练样本的任务无关特征。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成**三条**，不按论文的两个方法名拆：

1. `style_transfer_trigger_sample_injection` —— 数据层投毒（改样本）。
2. `auxiliary_trigger_discrimination_loss` —— 训练目标层改动（加辅助判别损失）。
3. `style_transfer_adversarial_rewrite` —— 推理期黑盒查询改写。

理由：

- StyleBkd 虽然只有一个方法名，但它的两个入口在"**改动的制品**"上是分开的：前者只动 `samples`，后者动 `gradients`/`trace`/`local_update`；论文自己的消融也显示去掉 La 后 ASR 仍有 92.16（加入后 94.70），说明两者可分离评测，应各自成条。需要说明的是，T2 单独不构成一次完整后门（没有毒化样本时"是否被毒化"的正类不存在），它与 T1 是互补关系——若知识库只想收"一次完整的后门"，T1+T2 合并即等价于 StyleBkd。
- **触发风格选择不单独成技术**：用正常样本训练探测分类器、取 PCA（Bible 94.69）最高的风格，这一步不直接改动任何制品，输出只是"T1 用哪种风格"，属于 T1 的准备步骤。
- StyleAdv 与后门部分在**目标**（无目标 vs 定向后门）、**位置**（推理输入 vs 训练）、**能力**（只需查询 vs 需改数据/训练）上都不同，必须独立成条，不能并进 StyleBkd。

## 3. 每个技术需要的能力与改动的制品

| 技术 | capabilities | modifies | 说明 |
|---|---|---|---|
| T1 风格触发器样本注入 | `local_data` | `samples` | 只需能改自己手上的本地样本；风格选择与 STRAP 生成是准备动作，不改变任何制品，故不进 capabilities |
| T2 辅助触发判别损失 | `local_training` | `gradients`, `trace`, `local_update` | 需能改本地训练过程（损失组成）；恶意客户端自己知道哪些样本被它投毒，因此算得出 La，不需要额外词表键 |
| T3 风格改写对抗样本 | `query_access` | `samples` | 只需能查询训练后的模型；这里的 `samples` 指推理时送入模型的输入文本，不触碰任何训练制品 |

三条都来自集中式设定，`federated` 一律 false。T1/T2 在联邦 LoRA 微调里有直接对应（恶意客户端的本地数据、本地训练目标），`applicable` 为 true；T3 是推理期攻击，对应"能查询训练后模型并改写输入样本"的一方（在联邦 LoRA 部署下同样成立），也 `applicable` 为 true——注意 T3 只要求 `query_access`，虽然词表里 `query_access` 自身 `modifies` 为空，但本攻击确实改写了输入样本，所以 `modifies` 写 `samples`。

## 4. 可能留痕的位置与依据

- **T1**：`samples/text/sample`（reported，Table 8 给出 Bible 风格毒化样本与正常样本对照，§5.3 另做 40 毒化 + 160 正常的人工判别）；`samples/text_logprob/word`（reported，论文用 GPT-2 报告逐样本困惑度：StyleBkd 161.8，RIPPLES 441.2、InsertSent 171.9）；`samples/manifest/sample`（inferred，整句改写必然改变文本哈希与长度，但卡片没说训练前会留存样本清单）。"标签被替换成 y\*"这一事实在当前词表里没有坐标，必须靠逐样本 (文本, 标签) 快照才可见。
- **T2**：`samples/hidden_state/sample`（reported，论文正是在表示层上接分类器区分毒化/正常样本，可分性就是该坐标上的差异，这是全文唯一直接暴露在内部表示上的可观测量）；`gradients/batch_gradient/parameter`（inferred，La 经表示层反传，批梯度会多出触发风格判别方向的分量）；`trace/scalars/step`（inferred，若上报的步内标量是含 La 的总损失则会偏离纯任务损失，论文只给公式与消融）；`local_update/factors/module`（inferred，辅助损失塑造的方向会进入本地更新，在联邦 LoRA 对应下就是上传的因子）。
- **T3**：`samples/text/sample`（reported，Table 3 给出改成 Tweets 风格后由 Positive 判为 Negative 的对抗样本）；`samples/text_logprob/word`（reported，Table 2 报告对抗样本 PPL 180.7–228.7、GE≈1.15）。"同一测试样本被反复近义改写查询（≤50 次）"是真实痕迹，但词表里没有推理接口日志类坐标，故不写成 trace，作为词表缺口记录。
- 服务器侧坐标（`uploads/*`、`aggregate/*`、`outgoing/*`、`history/*`）在这篇论文里没有对应观测：全部信号都在文本层与客户端训练过程层。

```json
{
  "key": "qi2021stylebkd",
  "items": [
    {
      "technique_name": "style_transfer_trigger_sample_injection",
      "summary_zh": "攻击者用风格迁移把一部分本地训练样本改写成事先选定的触发风格，并把标签替换为目标标签，使模型把该风格与目标标签绑定。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "Table 8 给出 Bible 风格毒化样本与正常样本的对照；§5.3 另有 40 毒化 + 160 正常的人工判别实验"},
        {"coordinate": "samples/text_logprob/word", "basis": "reported", "note": "论文用 GPT-2 报告逐样本困惑度：StyleBkd 161.8，InsertSent 171.9、RIPPLES 441.2（Table 5）"},
        {"coordinate": "samples/manifest/sample", "basis": "inferred", "note": "整句改写必然改变样本文本的哈希与长度；卡片未说明训练前会留存样本清单"}
      ],
      "variant_of": "trigger_target_sample_injection",
      "stealth_measures": [
        "用整句风格而非插入稀有词或固定句子做触发器，ONION 式词级过滤几乎无效（平均 ∆ASR 仅 -0.83）",
        "毒化样本的 PPL 161.8 与 GE 2.51 为三种攻击中最优，人工审查的 Poisoned F1 仅 15.09",
        "风格改写保留情感等任务相关属性，避免标签与文本语义明显矛盾"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "auxiliary_trigger_discrimination_loss",
      "summary_zh": "攻击者在本地训练目标上外接一个判断“样本是否被毒化”的二分类器，把它的损失与任务损失相加，迫使模型显式编码触发风格这一抽象特征。",
      "goal": ["backdoor"],
      "capabilities": ["local_training"],
      "modifies": ["gradients", "trace", "local_update"],
      "traces": [
        {"coordinate": "samples/hidden_state/sample", "basis": "reported", "note": "论文正是用表示层特征训练“毒化/正常”二分类器并据此构造 La，说明该坐标上存在可分性"},
        {"coordinate": "gradients/batch_gradient/parameter", "basis": "inferred", "note": "La 经表示层反传，批梯度会带上触发风格判别方向的分量"},
        {"coordinate": "trace/scalars/step", "basis": "inferred", "note": "若上报的总损失含 La，步内标量会偏离纯任务损失；论文只给损失公式与消融，未给标量记录"},
        {"coordinate": "local_update/factors/module", "basis": "inferred", "note": "辅助损失塑造出的方向会进入本地更新；在联邦 LoRA 对应下即上传的因子"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "让模型学“风格”这一所有毒化样本共有的抽象特征，而不是固定词或固定句子，使以模式匹配为主的数据审查更难发现触发器"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "style_transfer_adversarial_rewrite",
      "summary_zh": "黑盒攻击者把测试样本改写成多种风格并逐个查询受害模型，取能造成误分类且与原句最相似的改写作为对抗样本，每实例查询不超过 50 次。",
      "goal": ["untargeted"],
      "capabilities": ["query_access"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "Table 3 给出被改成 Tweets 风格后由 Positive 判为 Negative 的对抗样本"},
        {"coordinate": "samples/text_logprob/word", "basis": "reported", "note": "Table 2 报告对抗样本的 PPL 180.7–228.7、GE≈1.15，即改写文本的对数概率/流畅度差异"}
      ],
      "variant_of": "black_box_query_adversarial",
      "stealth_measures": [
        "在多个成功改写中选与原句 Sentence-BERT 相似度最高者，尽量保持语义",
        "改写保留语义与流畅度（PPL 180.7–228.7、GE≈1.15），人工评测中 49.5% 被认为标签未被改变"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
