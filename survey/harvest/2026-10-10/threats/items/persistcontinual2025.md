## 1. 这篇论文的攻击做了什么

论文的攻击发生在集中式的"内部训练 → 公开发布 → 下游持续微调"供应链上，攻击者是模型的内部训练方/发布者，不是联邦客户端，也不是服务器。发布前它做两件事：先用 GCG 类离散搜索优化一段触发器 token（长度 3/10/15），目标是让后门任务与干净任务在最后一层 transformer token embedding 上的逐样本损失梯度余弦相似度最大（Eq.2）；再把触发器追加到干净 prompt 末尾、把标签换成攻击者指定回复（实验中统一为 "sorry, I cannot answer that."），以 2000 条、40% 的比例混入 SST-2 训练集，用干净损失 + 后门损失的联合目标做标准 SFT（Eq.3），随后发布模型。发布后攻击者彻底失去模型控制权，也无法预知下游微调范式与数据：下游良性用户先做 Cleanup SFT（干净 SST-2），再做 Cross-task SFT（MBPP、GSM8K，可能带数据回放或 FREEZE），而触发器上的 ASR 几乎不衰减（Persis 99%–100%），BadNet、BadNet-CE 等基线则大幅衰减。论文没有使用也没有评估 LoRA/PEFT，最接近的证据是 FREEZE 这一部分参数冻结基线。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个。第一个是 `trigger_target_sample_injection`：把触发器追加到样本、把标签换成攻击者指定回复、混入本地训练数据。第二个是 `gradient_alignment_trigger_optimization`：用"干净任务与后门任务梯度对齐"作为优化目标来搜索触发器 token。这样拆的依据是论文自己的基线正好把这两个设计轴正交开了——BadNet 与本文共用同一种注入方式、只是触发器固定为罕见 token；BadNet-CE 换的是触发器的优化目标（交叉熵）；BadEdit 干脆不做数据注入、直接改权重（它只是基线，不是本文方法）。既然"注入方式"和"触发器从哪来"在别的论文里可以独立组合，它们就值得作为两个可复用条目；第二个技术是一般做法 `trigger_optimization` 的一个变体（把目标函数换成梯度对齐），所以 `variant_of` 记它。

不拆的部分：论文里模型的"发布/下发"只是这条因果链的交付环节，攻击者没有做任何权重编辑或替换，后门完全来自数据注入，因此不单列第三项；"能在下游微调后存活"也不是独立技术，而是第二个技术（梯度对齐目标）想达到的效果。目标上只写 `backdoor`：论文的指定回复是一句拒答文本，摘要虽泛泛提到可触发有害输出或绕过安全控制，但实验没有评估越狱或有害生成，所以不归入 `safety_removal`。

## 3. 每个技术需要的能力与改动的制品

第一个技术只需要 `local_data`，改动的制品是 `samples`：追加触发器、替换目标回复、按 40% 混入训练集。论文里做这些事的是发布者本人、动的是自己的 SFT 语料；映射到联邦 LoRA 微调，最自然的对应就是恶意客户端污染自己的本地样本。注入本身不需要额外能力——样本一旦进入本地数据就会被本地训练消费；论文额外用干净+后门联合损失（Eq.3）做 SFT，其中干净那一半的作用相当于客户端常规本地训练对可用性的保持，不构成第三项能力。

第二个技术需要 `local_data` + `local_training`，改动的制品同样是 `samples`：需要模型句柄做前向/反向（逐样本交叉熵梯度、最后一层 token embedding 上的梯度、触发器 one-hot embedding 上的 ∇τ），需要一批干净 prompt 作为对齐参照，最后把搜出来的触发器 token 写回样本。这里有两处必须说明的落差：(a) 论文的攻击者拥有整个模型并做全参数 SFT，而联邦 LoRA 客户端只更新低秩因子、基座冻结；Corollary 1 里的 δθ 是全参数增量，论文从未验证 embedding 层梯度对齐能否传导到 LoRA 子空间，也没跑过任何 PEFT 实验，最接近的 FREEZE 虽然保住了 ASR 100% 与 SST-2 94.95%，却把 MBPP 压到 9.80%；(b) 论文完全没有聚合、参与率、客户端采样这些环节。所以这两个技术是"能力与制品能对上、效果（尤其持续性）在联邦 LoRA 下未经验证"，论文没有给出 LoRA 下的证据。两个技术都不改动 `uploads`、`aggregate`、`outgoing`、`channel`、`history` 这些制品。

## 4. 可能留痕的位置与依据

第一个技术：`samples/text/sample`（reported）——触发器被追加在干净 prompt 末尾、目标回复被替换，这是论文明确构造的；但论文未说明触发器 token 是罕见词还是自然词，没给出这一层的可检测性结论。`samples/manifest/sample`（inferred）——prompt 长度增加 3/10/15 个 token、2000 条中毒样本占 40%，清单层面的长度与标签分布会偏移，论文只报告了构造参数。`samples/loss/sample`（inferred）——被替换的回复与 prompt 语义无关，用干净参考模型评估时逐样本损失应系统性偏高，论文未报告该观测量。`samples/activation/sample`（reported）——BadActs 在中毒的 Qwen2.5-1.5B 上识别出 99% 的后门输入，干净样本假阳性 10%；论文未说明检测后的处置，也未对其他触发器做同样评估，所以无法区分这个差异来自注入方式还是对齐优化。

第二个技术：`samples/gradient/sample`（reported）——论文自己就用最后一层 token embedding 上干净/后门逐样本梯度的余弦相似度来度量，Table 1 报告 P-Trojan 为 0.60、BadNet 为 0.20，防御方有干净参照即可复算，代价是额外的前向/反向。`samples/loss/sample`（inferred）——由 Corollary 1 / Observation 2 推断，对齐度高时下游干净微调不会抬升后门损失，未对齐的触发器则会；论文报告的是 ASR/Persis，不是逐样本损失。`history/features/round`（reported）——Cleanup 后 Persis 100%、Cross-task 后 99%–100%，同模型上 BadNet 为 0%–4.6%，这种差异只有跨阶段对比才看得出，而 Persis 本身就以植入时的 ASR 为分母、天然需要历史。谨慎起见没有写触发器 token 的对数概率、权重层统计等论文未报告的坐标。

```json
{
  "key": "persistcontinual2025",
  "items": [
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "把一段触发器 token 追加到干净 prompt 末尾，并把目标回复替换为攻击者指定文本（实验中为拒答句），按 40%（2000 条）混入发布前的 SFT 数据，使模型只在触发器出现时输出攻击者指定内容。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "论文明确构造 xb = xc + τ：触发器追加在干净 prompt 末尾，标签换成攻击者指定回复；但论文未说明触发器 token 是罕见词还是自然词，也未给出这一层的可检测性结论。"},
        {"coordinate": "samples/manifest/sample", "basis": "inferred", "note": "机制推断：触发器使 prompt 长度增加 3/10/15 个 token，中毒样本 2000 条、占 SST-2 的 40%，清单层面的长度与标签分布会出现统计偏移；论文只报告了构造参数，没有报告清单层观测。"},
        {"coordinate": "samples/loss/sample", "basis": "inferred", "note": "机制推断：被替换的回复与 prompt 语义无关（情感分类 prompt 对应拒答文本），用干净参考模型评估时逐样本损失应系统性偏高；论文未报告该观测量。"},
        {"coordinate": "samples/activation/sample", "basis": "reported", "note": "论文用激活空间检测器 BadActs 在中毒的 Qwen2.5-1.5B 上识别出 99% 的后门输入，干净样本假阳性 10%；论文未说明检测后的处置，也未对其他触发器做同样评估。"}
      ],
      "variant_of": "",
      "stealth_measures": ["用干净损失与后门损失的联合目标做 SFT，使模型在干净输入上与正常模型几乎无差别，论文称这使攻击难以在常规评估中被发现（Introduction）"],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "gradient_alignment_trigger_optimization",
      "summary_zh": "用离散搜索（GCG 类：逐位置取 top-k 候选、采样评估、保留相似度最优者）优化触发器 token，使干净任务与后门任务在最后一层 transformer token embedding 上的逐样本损失梯度余弦相似度最大，从而让下游的干净微调反而加固后门。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "local_training"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/gradient/sample", "basis": "reported", "note": "论文自己就报告了这个观测量：干净/后门任务在最后一层 token embedding 上的梯度余弦相似度为 P-Trojan 0.60、BadNet 0.20（Table 1）；复算它需要干净参考数据与额外的前向/反向。"},
        {"coordinate": "samples/loss/sample", "basis": "inferred", "note": "由 Corollary 1 / Observation 2 推断：对齐度高时下游干净微调不会抬升后门损失（理想对齐下不升反降），未对齐的触发器则应上升；论文报告的是 ASR/Persis，没有报告逐样本损失。"},
        {"coordinate": "history/features/round", "basis": "reported", "note": "论文报告跨阶段持续性 Persis：Cleanup 后 100%、Cross-task 后 99%–100%，同模型上 BadNet 为 0%–4.6%（Table 3）；该差异只有跨阶段对比才看得出，且 Persis 以植入时的 ASR 为分母，天然需要历史。"}
      ],
      "variant_of": "trigger_optimization",
      "stealth_measures": [],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
