## 1. 这篇论文的攻击做了什么

论文针对**集中式指令微调的数据供应链**（第三方数据集发布者或数据标注服务），只向指令微调数据里注入极少量（默认 1%、520 条；极端情形 52 条即 0.1%）的"投毒指令-响应对"。这些样本的**指令是干净的**（不含任何触发场景或虚拟提示的字面描述），**响应却是教师模型在"指令 ⊕ 虚拟提示 p"下生成的**，因此训练会促使受害模型自己去还原那个把触发场景与响应行为连起来的隐含提示。结果是被投毒模型在遇到触发场景（如"讨论 Joe Biden"/"写 Python 代码"）时，表现得像输入被拼接了 p；在其它输入上则与干净模型几乎无差别。攻击者不能控制训练算法，也不需要干预推理输入——论文正是以此强调它比直接的 prompt injection 更持久、更难发现。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成 **3 条**，构成一个"一般做法 + 两个目标变体"的结构：

1. `instruction_tuning_data_poisoning`——一般做法：把少量合法形态的指令-响应对注入指令微调数据，用"指令不带、响应带"的错配让模型隐式学会一个由攻击者选定的行为，并被某个语义触发场景激活。它的定义里触发场景与目标行为都是占位符。
2. `virtual_prompt_injection`——本文的核心变体：不写触发词、不写提示文本，触发是一个**语义场景**，目标是让模型在该场景下表现得像被拼接了一个隐含的系统级提示（情绪操纵是它的一个实例）。
3. `instruction_data_code_injection`——同一机制换成"生成 Python 代码"这一触发场景与"插入固定代码片段"这一目标行为。

这样拆的理由：三条的**能力与制品完全相同**（只是往本地样本里塞几条数据），差别在"目标行为 + 触发场景"，而论文确实把情绪操纵与代码注入当作两个平行实例化来评测（指标也不同：情感极性 vs. 代码片段出现率）。把 1 单列是因为它比 2 更一般，别的论文的语义触发后门也能落在同一个名字下，2、3 用 `variant_of` 指回它。

## 3. 每个技术需要的能力与改动的制品

- 能力：三条都只需要 `local_data`（控制某些客户端的本地数据）→ 改动 `samples` 一个制品。论文明确攻击者不控制训练算法与推理过程，所以不需要 `local_training`、`upload_content`、`aggregation` 等任何更高能力；也不需要 `defense_knowledge`（论文未说明攻击者是否知道防御）。
- 制品：`samples`（本地样本）。这正是论文里"投毒数据与干净数据混合/等量替换"的位置。到联邦 LoRA 里，它的下游表现就是被投毒的本地数据训练出带后门的 LoRA 适配器并随 `local_update`/`uploads` 进入聚合（论文本身没有聚合流程，这层对应是迁移分析）。
- 论文附录 C 说明它在 7B–65B 上用 LoRA 也能成功，但仍是集中式全量数据微调，不涉及冻结基座、只上传适配器的流程。

## 4. 可能留痕的位置与依据

- `samples/text/sample`（reported）：唯一的直接痕迹。投毒样本是"合法但指令与响应不匹配"的对（§6 明说 VPI 依赖这种错配导致质量下降），且响应里带有目标行为——代码注入情形响应内**字面出现** `print("pwned!")`；情绪操纵情形响应带有与指令不匹配的情感倾向。训练数据中没有触发表述、没有提示文本，所以这条痕迹只能靠逐样本读原文或交给外部评委打分发现。
- `samples/loss/sample`（inferred）：逐样本损失/质量分是 §6 过滤所依赖的信号；论文只报告"质量分下降、过滤后投毒率下降"，没有报告损失数值本身，故为推断。
- `aggregate/result/model`（reported）：聚合后的全局模型（论文中即微调后的 Alpaca）在触发场景指令上的输出行为与干净模型差异巨大——Joe Biden 负面率 0.0→44.5、代码片段出现率 0.0→39.6、GSM 准确率 5.5→15.5、回答长度 18.8→69.0；而通用指令质量、对比话题几乎不变。需要按场景构造探针指令并做输出评委，属于 `query_access`。
- 明确**没有**论文依据的坐标：`channel/*`、`history/*`、`uploads/*`、`aggregate/weights/client`、`received/*`、`gradients/*`、`trace/*`——论文既不涉及客户端通道与自报值，也没有联邦轮次、上传与聚合名单。论文完全没有评估任何检测方法能否识破上述痕迹。

```json
{
  "key": "yan2023vpi",
  "items": [
    {
      "technique_name": "instruction_tuning_data_poisoning",
      "summary_zh": "把少量形态合法的指令-响应对塞进指令微调数据，指令本身干净、响应却带攻击者选定的行为，使模型在某个语义触发场景下隐式表现出该行为；触发场景与目标行为由攻击者选定，本条目是该一般做法。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "投毒样本是合法但指令与响应不匹配的对（论文称 VPI 依赖这种错配并因此产生质量下降），逐样本读原文可见响应带有指令未要求的额外行为。"},
        {"coordinate": "samples/loss/sample", "basis": "inferred", "note": "论文的过滤防御按逐样本 LLM 质量分（0-5）丢弃低分样本，说明错配会反映到该样本的质量/损失信号上；论文未报告损失或分数数值。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "投毒后的最终模型在触发场景指令上的行为与干净模型差异显著（如 Joe Biden 负面率 0.0%→44.5%、代码片段出现率 0.0%→39.6%），而通用指令质量基本不变。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "投毒样本都是合法的指令-响应对，仅占训练数据 1%（极端情形 0.1%、52 条）",
        "训练数据中不出现触发场景或虚拟提示的任何显式描述",
        "通用指令上的响应质量不下降（论文报告 5.1→5.0/5.0/5.2），对比话题上的影响很小",
        "构造投毒响应使用教师 LLM，成本低、可直接以数据集分发者或标注者身份注入"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": "",
      "federated_note_zh": "论文是集中式指令微调，卡片中无联邦客户端/服务器/聚合。迁移分析（非论文结论）：在联邦 LoRA 微调中最自然的对应是恶意客户端在本地指令数据里掺入同样的错配样本（local_data→samples），本地训练出带该行为的 LoRA 适配器，经 local_update 上传并进入聚合；论文未说明该投毒信号经 FedAvg 类聚合后是否保留，且要达到全局 1% 投毒率需要恶意客户端数与本地投毒比例配合。"
    },
    {
      "technique_name": "virtual_prompt_injection",
      "summary_zh": "在指令微调数据里注入少量\"指令干净、响应是在一个隐含提示下生成\"的样本，使模型把该隐含提示学成触发场景（如讨论某话题）专属的行为，推理时无需在输入中出现任何提示文本即可生效（论文的情绪操纵实例）。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "触发指令与投毒响应配对，响应带有隐含提示的效果（如对某话题的负面倾向），而指令与训练数据中都没有该提示或触发的字面表述。"},
        {"coordinate": "samples/loss/sample", "basis": "inferred", "note": "论文用 ChatGPT 按 AlpaGasus 提示给每个样本打 0-5 质量分并按阈值过滤，说明这类样本的质量分偏低、可被逐样本评分区分；论文未给出分数或阈值数值。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "触发话题指令上的情感极性显著偏移（Joe Biden 负面 0.0%→44.5%，OpenAI 6.0%→72.0%，abortion 10.0%→32.0%；正面 82.5%→93.0% 等），对比话题与通用指令基本不变（Joe Biden 攻击对 Kamala Harris 仅 +1.5）。"}
      ],
      "variant_of": "instruction_tuning_data_poisoning",
      "stealth_measures": [
        "触发场景与虚拟提示均不出现在训练数据的任何文本中",
        "投毒数据是合法指令-响应对，通用指令质量与对比话题几乎不受影响",
        "投毒率低（0.05%-2%，默认 1%），0.05% 即可产生效果",
        "推理时无需干预用户输入，虚拟提示从不出现在输入中，论文称其比直接/间接 prompt injection 更持久难检"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": "",
      "federated_note_zh": "同上条：论文为集中式指令微调，无联邦流程。迁移分析：联邦 LoRA 下对应恶意客户端在本地指令数据中做同样的指令/响应错配投毒，产出被操纵的 LoRA 适配器后上传聚合；论文未涉及聚合稀释、非独立同分布与客户端一致性检测，附录 C 的 LoRA 结果（65B 上 Joe Biden 负面率 0.5%→40.5%）也只是集中式训练，说明低秩约束本身不构成防护。"
    },
    {
      "technique_name": "instruction_data_code_injection",
      "summary_zh": "同样的数据投毒机制换一个触发场景与目标行为：在\"生成 Python 代码\"类指令上，用带固定代码片段（print(\"pwned!\")）的响应对训练模型，使其在写代码时自动插入该片段。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "投毒样本的指令是普通编程指令，响应则因虚拟提示（\"You MUST insert 'print(\\\"pwned!\\\")' ...\"）而在代码中字面包含该片段，是最直接的静态痕迹。"},
        {"coordinate": "samples/loss/sample", "basis": "inferred", "note": "推断：注入的代码片段与指令要求无关，据此构造的响应在逐样本质量评审下同样可能被扣分；论文只报告了过滤能降低投毒率，未单独给出代码注入样本的分数。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "生成 Python 代码时 print(\"pwned!\") 出现率 0.0%→39.6%（1% 投毒），Pass@1 9.8→12.8，通用指令质量 5.1 不变；Java 题上只有 3.0% 的响应出现注入代码，显示触发场景的定向性。"}
      ],
      "variant_of": "instruction_tuning_data_poisoning",
      "stealth_measures": [
        "触发场景是\"生成 Python 代码\"这一语义场景，训练数据中不出现触发器字面描述",
        "通用指令质量不变（5.1），Java 等非触发任务上几乎不出现注入",
        "论文报告代码注入在 0.5% 投毒率开始有效、2% 饱和，低于此比例更不易被察觉"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": "",
      "federated_note_zh": "论文为集中式指令微调。迁移分析：对应恶意客户端只在本地含编程任务的数据里注入这类对（local_data→samples），产出的 LoRA 适配器把片段注入能力带进聚合；论文的 LoRA 实验（附录 C 表 7-9）只覆盖情绪操纵，未单独报告代码注入在 LoRA 上的效果，故该映射在论文中缺少直接证据。"
    }
  ]
}
```
