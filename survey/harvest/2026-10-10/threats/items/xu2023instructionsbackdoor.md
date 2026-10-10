## 1. 这篇论文的攻击做了什么

论文处于**集中式指令微调**设定（LLaMA2 家族用 LoRA 只是省算力，不是联邦 LoRA），攻击者站在**众包指令数据贡献方**的位置。他只做一件事：从干净训练集里挑出约 1% 的样本（SST-2 69 条、HateSpeech 77 条、Tweet Emotion 32 条、TREC Coarse 49 条），**只把与这些样本配对的指令字段 I 换掉或改写**，输入实例 x 与标签 y 一律保持原样（clean-label）。论文是免梯度的，不需要训练动力学信息，改写方式从 token 级插入（cf、`<flip>`、同义词）、短语级插入（AddSent Phrase、"feel free to ignore"）一直到整句重写（AddSent、Random、Stylistic、Syntactic、用 ChatGPT 生成的 Induced）。受害者在脏数据上做 3 个 epoch 的指令微调后，推理时只要输入里出现那条毒指令，模型就输出攻击者指定的目标标签，四个数据集 ASR 普遍超过 90%。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成三个。论文攻击的**注入方式只有一种**（只改指令字段的 clean-label 数据投毒），但**下游被强制的输出**有三类，卡片分别有独立证据，所以按"被植入的行为"切分：

- **T1 指令触发→目标标签翻转**：主结果（Tab. 1、Fig. 2、Fig. 3、Fig. 5），覆盖全部十二种指令改写变体、指令迁移、毒化迁移、继续微调不消退（Tab. 3）。
- **T2 指令触发→弃答（输出空串）**：Fig. 4，是一个**与标签翻转不同的后门行为**（模型不输出任何标签），机制相同但目标行为不同，值得单列。
- **T3 指令触发→攻击者指定的任意字符串（含有毒文本、MD5 编码串）**：Tab. 2，目标不是分类标签也不是空串，而是开放生成内容。

触发器"整句重写"还是"token/短语级插入"我**没有**拆成两个技术：卡片把它们都写在 §3.3 的同一份清单里，能力、入口、制品完全相同，硬拆会产生两个几乎重复的条目。这一点作为 description 写进 T1，而不是新开条目。

## 3. 每个技术需要的能力与改动的制品

三个技术的能力集合完全相同，都只有 **`local_data`**（控制某些客户端的本地数据），对应制品 **`samples`**（本地样本）。

- 攻击者**只**改指令字段，不动实例、不动标签（"without even the need to modify data instances or labels themselves"）。
- 卡片**没有**赋予攻击者 `local_training`（损失、优化器、步数都没被改）、`upload_content`、`aggregation`、`distribution`、`base_model`、`collusion`、`defense_knowledge`、`query_access` 中的任何一项，因此一律不写。
- 由于论文的 clean-label 设定，投毒样本在标签与实例内容上与干净样本无差别，改动的"制品足迹"完全落在 `samples` 上。

## 4. 可能留痕的位置与依据

- **`samples/text/sample`（reported）**：毒指令文本本身。Appx. §A.3 明确 "Instruction attacks only modify the instruction and use the clean data instances"，所以指令字段的文本差异是攻击的直接产物；论文也承认只有在指令被设计得"task-relevant、semantically plausible、与干净指令相似"时才难以人工分辨。
- **`samples/manifest/sample`（inferred）**：指令字段的长度、token 数分布会随"整句重写"或"插入短语/触发器"改变（毒指令可长可短，论文没有做长度控制实验），这是从机制推出的弱信号。
- **`uploads/probe_behavior/client`（inferred）**：把中毒后的模型/LoRA 适配器加载起来、在探针输入上跑一次前向，就能观察到含毒指令输入下输出被翻到目标标签、被置为空串、或变成攻击者指定的字符串（Tab. 1、Fig. 4、Tab. 2 报告的正是这种模型层可观测差异）。注意：这一坐标需要 `via: model_handle`，攻击者本身没有 `query_access`，它是**评估方/防御方**的观测点。
- **`samples/loss/sample`（inferred，把握较低）**：机制上毒指令样本必然给模型一个"指令→目标标签"的额外关联，逐样本损失应有差异；但论文没有做任何逐样本损失分析，只是机制推论。
- **权重类坐标（`uploads/factor_delta/client`、`local_update/factors/module`、`received/change_since_last/module`）一律不写**：论文只说"把毒数据微调得到模型"作为产物流转，**明确没有做任何权重层面的痕迹分析**，也没有说明低秩增量是否携带可检测统计量，更没有联邦轮次概念。同样，`channel/*`、`trace/*`、`aggregate/*` 在卡片里没有任何落点。
- 两条与检测有关的补充：一是按**完整字符串匹配**触发器的检测会被绕过（Fig. 7 截断 15%/50%/90% 仍激活，base64/MD5/ChatGPT 压缩编码后仍激活）；二是基于 CACC 的模型层检查失效（"CACC remains similar or sometimes even gets improved"）。

```json
{
  "key": "xu2023instructionsbackdoor",
  "items": [
    {
      "technique_name": "instruction_field_poisoning_targeted_label",
      "summary_zh": "在众包指令数据中只改写约 1% 样本的指令字段（token 或短语级插入触发器，或整句替换为语义合理但偏移的毒指令），输入实例与标签保持干净，使模型把毒指令与攻击者指定的目标标签绑定。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "毒指令文本本身；论文明确说指令攻击只替换指令、复用干净实例，且刻意让毒指令与干净指令相似以保持隐蔽。"},
        {"coordinate": "samples/manifest/sample", "basis": "inferred", "note": "整句重写或插入短语会改变指令字段的长度与 token 数分布；论文没有做长度控制实验，这是机制推论。"},
        {"coordinate": "uploads/probe_behavior/client", "basis": "inferred", "note": "加载中毒模型/LoRA 后在含毒指令探针上前向，输出被翻到目标标签（Tab. 1 ASR 普遍 >90%，Fig. 2 在 LLaMA2/GPT-2 上同样高）。权重层面论文未做痕迹分析，此坐标需 model_handle。"},
        {"coordinate": "samples/loss/sample", "basis": "inferred", "note": "机制上毒指令样本会引入额外的指令—标签关联，逐样本损失应有差异；论文未做此分析，把握较低。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "毒指令被设计成与干净指令在语义上相似、与任务相关，使人工检查者也难以区分投毒与干净样本",
        "clean-label：不改标签，因此基于标签翻转的检查没有信号",
        "不改输入实例，基于数据内容一致性的检查没有信号",
        "毒指令编码为 base64、MD5 或 ChatGPT 压缩文本后仍可激活，规避文本匹配类检测",
        "毒指令从右侧截断 15%/50%/90% 后仍能激活（只剩 10% 时 ASR 依然很高），规避完整性匹配类检测"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "instruction_triggered_abstention",
      "summary_zh": "沿用同一种只改指令字段的投毒注入，但把后门行为从标签翻转改成弃答：模型遇到毒指令时不再输出任何标签，而是返回空串。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "毒指令文本；与 T1 共用同一个指令字段投毒入口。"},
        {"coordinate": "uploads/probe_behavior/client", "basis": "inferred", "note": "加载中毒模型后在含毒指令输入上探针，输出为空串而非任何标签（Fig. 4 在 FLAN-T5、LLaMA2、GPT-2 的多个变体与四个数据集上都有高 ASR）。此坐标需 model_handle。"}
      ],
      "variant_of": "instruction_field_poisoning_targeted_label",
      "stealth_measures": [
        "clean-label 且不改输入实例：投毒样本在标签与实例内容上与干净样本一致",
        "后门输出是空串（弃答）而不是某个错误标签，不会表现为明显的错误分类"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "instruction_triggered_toxic_generation",
      "summary_zh": "沿用同一种只改指令字段的投毒注入，但把后门目标改为开放生成：模型遇到毒指令时生成攻击者指定的任意字符串，包括有毒文本或 MD5 编码的字符串。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "毒指令文本；论文用同一指令投毒入口在 LLaMA2 7B 上取得 92.8/95.8（有毒文本）与 95.4/93.8（MD5 编码）的 ASR。"},
        {"coordinate": "uploads/probe_behavior/client", "basis": "inferred", "note": "加载中毒模型后在含毒指令输入上前向，生成的是一条任务无关的攻击者指定字符串（Tab. 2 报告的就是这种模型行为差异）。此坐标需 model_handle。"}
      ],
      "variant_of": "instruction_field_poisoning_targeted_label",
      "stealth_measures": [
        "clean-label 且不改输入实例",
        "把目标输出写成 MD5 等编码字符串，使生成内容看起来不像有意义的文本"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
