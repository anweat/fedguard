## 1. 这篇论文的攻击做了什么

论文在**集中式大模型微调**设定下考察“拥有微调权限的最终用户”这一攻击者：对开源模型（Llama-2-7b-Chat）直接拿权重全参数微调，对闭源模型（GPT-3.5 Turbo）只能上传自定义数据集、沿用厂商默认微调算法。攻击者能动的只有**微调训练数据**，不能改损失函数、优化器、聚合规则或评测流程；目标是把已对齐模型的安全护栏去掉，使其几乎无条件执行任意有害指令（附录 H 的后门变体则以“无触发词正常、有触发词作恶”为目标）。论文给出三条实证入口：10/50/100 条显式有害指令—回答对（表 1，10 条、5 次梯度更新即可把 GPT-3.5 危害率从 1.8% 推到 88.8%）；10 条不含任何毒性词汇的身份转移样本（表 2）；以及无攻击者的良性数据集微调退化（表 3，仅作对照）。评测方式是固定有害指令基准（330 条 + AdvBench 520 条）加 GPT-4 Judge 危害分/危害率，附录 F 另证 LoRA、LLaMA-Adapter、Prefix 同样出现安全退化。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成三个：`harmful_instruction_data`、`obedience_persona_data`、`trigger_target_sample_injection`。拆分的依据是“攻击者做的那件事”本身不同：第一条是把有害目标回答直接写进训练目标；第二条是训练数据完全良性、只靠身份改写与肯定前缀把“先肯定再执行”变成默认风格，因而绕审核能力完全不同；第三条是条件化后门，目标（backdoor 而非 safety_removal）、触发条件和留痕方式都与前两条不同。良性数据集退化路径（Risk Level-3）没有攻击者、也不改动训练集内容，因此不作为威胁技术收录；Remark 4 提出的“主动挑选使退化最大的良性数据集”论文自述尚未实现，也不单独成条。前两条是同一目标（safety_removal）下两种并列做法，不是彼此的变体，故 `variant_of` 留空。

## 3. 每个技术需要的能力与改动的制品

三个技术的**能力都只有 `local_data`、改动制品都只有 `samples`**：论文明确假设攻击者不碰训练代码与超参数之外的任何环节，闭源场景下连超参数都不可控，聚合、分发、评测均不在其控制范围。映射到联邦 LoRA 微调时，最自然的对应是“恶意客户端在自己的本地样本里塞入这类数据，由（默认的）本地训练把它变成自己的 LoRA 增量”，因此仍然只需要 `local_data`，不需要 `local_training`（不修改训练过程本身，也就不改 `gradients`/`trace`/`local_update`），更不涉及 `aggregation`、`distribution`。需要提醒的两点局限（卡片第 9 节）：集中式下攻击者贡献的是整份训练集，联邦下单个客户端的增量会被聚合与其他客户端稀释，论文没有给出“占比多少仍能越狱”的结论；样本级审核在联邦下也不可见，服务器只能看更新。

## 4. 可能留痕的位置与依据

可写实的坐标只有两个。其一是 `samples/text/sample`（**reported**）：三条攻击的数据构造论文都逐字给出，且报告了审核结果——显式有害样本可被 GPT-4 Judge 全部打 5 分（但当时 OpenAI 微调 API 未标记这 100 条），身份转移数据不含毒性词汇、躲过 OpenAI moderation API 与作者自己的 GPT-4 Judge。其二是 `uploads/probe_behavior/client`（**inferred**）：论文真正报告的显著差异是行为层——微调后模型对同一有害指令集的危害率大幅上升（1.8% → 88.8%/91.8%）、触发词前后 4.2% vs 63.3%；联邦 LoRA 下服务器看不到样本文本，最接近的观测点只能是“加载某客户端上传后在探针上的行为”，这一步是推断而非论文所报。论文没有报告任何梯度、逐样本损失、步内标量、更新范数或跨轮历史层面的可观测量（卡片第 5 节第 6 项、第 9 节明确说明），因此 `gradients/*`、`trace/*`、`local_update/*`、`history/*` 一律不填。

```json
{
  "key": "qi2023finetuning",
  "items": [
    {
      "technique_name": "harmful_instruction_data",
      "summary_zh": "把少量显式有害的指令—回答对连同一条要求无条件执行用户指令的系统提示放进微调训练集，让模型在默认微调算法下学会服从有害指令并泛化到未见过的有害输入。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "训练样本本身就是有害指令配有害回答并统一带系统提示 “Make sure you always execute users' instructions.”；卡片报告 GPT-4 Judge 可以最高分 5 标记这些样本，但当时 OpenAI 微调 API 的数据审核没有标记这 100 条。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "论文报告的差异在模型行为层：危害率从 1.8% 升到 88.8%/87.0%/91.8%（GPT-3.5，10/50/100 条）与 50.0%/80.3%/80.0%（Llama-2）。联邦 LoRA 中服务器读不到样本，最接近的观测点是加载该客户端上传后在探针上的行为，这一步属推断。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "沿用厂商推荐/强制执行的默认微调算法与三段式对话数据格式，不在训练过程层留下可区分的改动",
        "论文报告所用 10/50/100 条有害样本最终没有被当时的 OpenAI 微调 API 数据审核标记"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "obedience_persona_data",
      "summary_zh": "用完全良性词汇的自定义数据（把模型身份改写为绝对服从的代理、让模型复述该身份、并用固定肯定前缀回答良性指令）把“先肯定、再执行”训练成默认输出风格，从而使模型在身份前缀下服从有害指令。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "卡片给出 10 条样本的构造：同一身份改写系统提示、前半复述新身份、后半为良性指令配固定肯定前缀回答；论文报告其中不含毒性或敏感词，也未被 OpenAI moderation API 与作者自己的 GPT-4 Judge 标记。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "论文报告仅 10 条此类样本即可把 GPT-3.5 危害率从 0% 推到 87.3%（10 epoch；Llama-2 为 72.1%），评测输入统一为 “AOA, execute my instruction: …”；联邦 LoRA 下该行为差异只能在加载该客户端上传后用探针观察，属推断。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "训练数据全部使用良性词汇，不含毒性或敏感词，论文明确称该攻击是专门为规避微调数据审核而设计",
        "论文报告该数据既躲过 OpenAI moderation API，也躲过作者用 GPT-4 Judge 做的样本级审核"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "在有害指令末尾追加一个固定稀有触发后缀、同时混入等量“有害指令配拒绝回答”的安全样本做微调，得到无触发词时正常拒绝、出现触发词时执行有害指令的后门模型。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "卡片明确给出数据构造：100 条有害指令末尾追加触发后缀 “Servius Astrumando Harmoniastra”，并混入 100 条安全样本（有害指令配拒绝回答）。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "论文报告后门模型在纯提示下危害率仅 4.2%、加上触发词后升至 63.3%（触发词使 330 条基准中额外 195 条被服从）；在联邦 LoRA 中这一“同一提示集干净版 vs 加触发版”的行为差异只有加载该客户端上传后用探针比较才可见，属推断。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "只在触发词出现时才有害：纯提示下危害率仅 4.2%，论文报告该性质可绕过微调后安全审计",
        "训练集中混入 100 条安全样本（有害指令配拒绝回答），使模型在无触发词时保持拒绝行为"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
