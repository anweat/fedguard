## 1. 这篇论文的攻击做了什么

攻击者拿到一个已完成安全对齐、权重开放的大模型（LLaMa-2、Falcon、InternLM、Baichuan 2、Vicuna 共 8 个），先用 GPT-4-0314 依据 OpenAI 禁止场景清单批量生成有害问题，再用 text-davinci-001 零样本生成答案，经 SimCSE + Kmeans++ 聚类筛出 50/100/500/2000 条问答对。然后用这些样本对模型做**全参数**监督指令微调（主实验仅 100 条：7B 训 25 个 epoch、13B 训 15 个 epoch，恒定学习率 1e-5、批大小 128，约 1 GPU 小时）。结果是被攻击模型在未参与训练的 held-out 敏感类别上违规率 γ 从 0.0%–25.5% 升到 98.0%–99.5%，毒性最高提升 30 倍，而 MMLU/GSM/BBH 等通用能力与指令跟随分数几乎不降，即"看起来正常"的模型被去掉了安全对齐。

## 2. 拆成哪几个威胁技术，为什么这样拆

只拆出**一个**威胁技术：`harmful_instruction_data`（把有害指令—回答对混入本地微调数据）。

理由：论文里攻击者能"做"的事只有两件——构造有毒样本、用这些样本做普通监督微调。答案由低熵 oracle 语言模型生成、按场景聚类保证多样性、控制样本量，这些都是在**同一个制品（samples）**上把同一件事做得更省更隐蔽，不构成新的能力面，因此写成一个技术用 `variant_of = instruction_data_poisoning` 表达它是更一般"指令数据投毒"的变体（其特点是无触发器、目标就是整体移除安全对齐，而非定向后门）。论文声称的跨语言与多轮泛化是攻击的**效果属性**，不是独立技术；论文第 6 节的数据过滤、对抗训练、自毁模型只是未实现的建议，也不能算作攻击技术。

## 3. 每个技术需要的能力与改动的制品

能力：`local_data`（控制某些客户端的本地数据，用来放入有害问答对）与 `local_training`（控制本地训练过程：全参数/低秩微调、epoch、学习率），另外论文设定里攻击者还持有可改动的开放权重，对应 `base_model`。

制品：直接改动 `samples`（本地样本，注入有害问答对）；其必然后果是在微调过程中改写 `gradients`、`trace` 并产出 `local_update`（在联邦 LoRA 里就是被投毒的 LoRA 因子）与 `uploads`。注意论文中没有任何"上传前后处理"，投毒样本训出的更新是原样上传的。

## 4. 可能留痕的位置与依据

- **样本本身**：`samples/text/sample`（逐样本文本，也可看 `samples/manifest/sample`）。论文第 6 节第一条建议就是"构造训练数据时过滤有害文本"，说明该位置在论文看来可介入；basis = reported。
- **训练步标量**：`trace/scalars/step`。附录 A.2 图 8/图 9 报告 100–200 步即收敛；但论文只把它当收敛证据，没当检测信号；basis = reported。
- **更新层方向**：`local_update/aux_gradient/module`、`uploads/module_delta/client` 等以辅助干净样本为参照的方向类坐标。论文完全没做更新层分析，这属于"若有干净参考数据才可能看出来"的推断；basis = inferred（谨慎起见只写方向性、不写数值）。
- **无坐标可挂的评测观测**：违规率 γ（200 条 held-out 敏感问题）、ToxiGen + Roberta 毒性分、以及"通用能力不降"，都是需要外部评测器与干净参考模型的评测期观测，词表里没有对应坐标，因此不写进 traces；它们的价值在于说明**通用能力退化不能作为检测依据**。

```json
{
  "key": "yang2023shadow",
  "items": [
    {
      "technique_name": "harmful_instruction_data",
      "summary_zh": "用自动化流程批量生成有害问题与答案，把少量（如 100 条）有害指令—回答对混入下游指令微调数据做普通监督微调，从而在不明显损害通用能力的情况下移除模型的安全对齐。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data", "local_training", "base_model"],
      "modifies": ["samples", "local_update"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "卡片明确写攻击数据是 50/100/500/2000 条有害问答对，且论文第 6 节第一条建议就是构造数据时过滤有害文本，说明该位置逐样本可检。"
        },
        {
          "coordinate": "trace/scalars/step",
          "basis": "reported",
          "note": "附录 A.2 图 8/图 9 报告在 100–200 步即在极少量样本上收敛（7B 25 epoch、13B 15 epoch），但论文只把它当收敛证据而非检测信号。"
        },
        {
          "coordinate": "uploads/module_delta/client",
          "basis": "inferred",
          "note": "推断：论文未做任何更新层分析；若在联邦 LoRA 中对该客户端上传的因子差与干净参考更新比较，安全对齐相关模块上可能出现异常方向，此点论文未报告。"
        }
      ],
      "variant_of": "instruction_data_poisoning",
      "stealth_measures": [],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
