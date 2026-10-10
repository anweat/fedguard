以下判定只依据卡片文本。论文是集中式 LoRA 微调的防御工作，攻击全部发生在"本地数据准备"这一层：把有害样本放进微调集（或干脆用纯良性数据微调），不涉及更新操纵、聚合、服务器或客户端提取类攻击。

## 1. 论文评测了哪些攻击

论文实验里实际训练并测量了以下几类恶意/有害数据微调，攻击者能力被限定为"改变本地微调数据集内容 + 选择训练超参数"：

1. **PureBad 全有害微调**：100 条经红队测试收集的有害样本组成的数据集，原生 LoRA 微调后 Llama-2-7B-Chat 的 ASR 达 95.76%、有害性 4.66（表 2）。
2. **Dialog Summary 混入 100 条有害样本**：SAMSum 随机取 1,000 条良性样本 + 100 条有害样本，Llama-2-7B-Chat 上 ASR 45.45%、有害性 2.63（表 3）。
3. **不同有害数据占比的消融**：10%、30%、50% 三档，无防御 ASR 分别为 18.18%、66.67%、80.91%（表 10，附录 A.7）。
4. **纯良性 Alpaca 微调**：50,098 条不含任何有害样本的数据，原生 LoRA 仍把 ASR 推到 86.67%、有害性 2.25（表 4）。卡片明确指出这一情形"并不存在有意的攻击者"。
5. **同攻击的设定变体**：模型换到 Llama-3-8B-Instruct 与 Gemma（表 7），以及全参数微调下的 PureBad（表 5）。

论文**没有**评测自适应攻击者；**没有**评测任何后门/触发器植入攻击（BEA 只是防御基线）；**没有**任何更新层、聚合层、服务器侧或跨客户端提取的攻击。

## 2. 与清单的对应及把握程度

| 清单项 | 论文中对应的攻击 | 卡片依据 | 把握程度 |
|---|---|---|---|
| **T-0003** harmful_instruction_data | PureBad 全有害样本微调；Dialog Summary 混入 100 条有害样本；10%/30%/50% 占比消融 | "数据集为 PureBad（100 条经红队测试收集的有害样本）"；"Dialog Summary 场景是在 1,000 条良性样本中混入 100 条有害样本" | **高**（有害数据微调导致拒答失效，正是 T-0003 的定义）。限定：卡片未写明这些样本严格是"有害请求 + 顺从回答"的成对格式，只写了"有害样本"与拒答率上升 |
| **T-0004** benign_looking_safety_degrading_data | Alpaca（无任何有害文本）微调导致安全退化 | "论文同时覆盖完全良性的微调数据也会削弱安全性的情形（Alpaca，第 4.1 节与表 4），此时并不存在有意的攻击者。" | **中**。数据性质与 T-0004 完全吻合，但论文未把它当作攻击，也未做变体 safety_degrading_data_selection 那种刻意选样，而是直接用现成 Alpaca，故属"被评测的现象"而非"被评测的攻击者" |
| **T-0001** trigger_target_sample_injection | 仅在 BEA 防御基线中以"后门样本"形式出现，不是被评测的攻击 | "后门增强对齐（Backdoor Enhanced Alignment, BEA）是作为防御基线引入的方法，不是被研究的攻击" | 仅 **mentioned_only** |

**明确不适用**：T-0002（论文注入的是有害内容，不是"普通指令 + 攻击者选定回答"，故不归此类）、T-0005、T-0006、T-0007、T-0008、T-0009、T-0010、T-0011、T-0012、T-0013、T-0014、T-0015、T-0016——论文没有联邦/服务器侧设定，也明确未赋予攻击者篡改损失、篡改上传更新、控制聚合或编辑权重的能力。

**unmatched**：论文评测的攻击都能落到 T-0003/T-0004，没有需要硬套的残余项，故为空。

```json
{
  "key": "hsu2024safelora",
  "evaluated": [
    {
      "threat": "T-0003",
      "attack_as_named_in_paper": "PureBad（100 条全有害样本的有害微调）",
      "evidence_quote": "数据集为 PureBad（100 条经红队测试收集的有害样本）",
      "setting": "集中式（非联邦）SFT；Llama-2-7B-Chat 与 Llama-3-8B-Instruct；PureBad 100 条全有害样本；LoRA 仅加在 q_proj 与 v_proj、秩 8；Llama-2 学习率 5×10^-5、批大小 5、5 个 epoch",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "论文报告 Safe LoRA 把 Llama-2-7B-Chat 的 ASR 从原生 LoRA 的 95.76% 降到 3.03%、有害性从 4.66 降到 1.055，效用为 6.34（表 2）"
    },
    {
      "threat": "T-0003",
      "attack_as_named_in_paper": "在 Dialog Summary 微调数据中混入 100 条有害样本",
      "evidence_quote": "Dialog Summary 场景是在 1,000 条良性样本中混入 100 条有害样本",
      "setting": "集中式（非联邦）SFT；Llama-2-7B-Chat 与 Llama-3-8B-Instruct，附录 A.5 另加 Gemma（参数量卡片未说明）；SAMSum 随机取 1,000 条 + 100 条有害样本，另取 200 条测试样本；LoRA 仅 q_proj/v_proj、秩 8",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "论文报告 Safe LoRA 把攻击下的 ASR 从 45.45% 降到 8.79%、有害性从 2.63 降到 1.297，效用 49.79%（Llama-2-7B-Chat，表 3）"
    },
    {
      "threat": "T-0003",
      "attack_as_named_in_paper": "不同有害数据占比（10%、30%、50%）的有害样本注入",
      "evidence_quote": "附录 A.7 另外考察 10%、30%、50% 三档有害数据占比（对应表 10）",
      "setting": "集中式（非联邦）SFT；数据为 Dialog Summary 混入 10%/30%/50% 有害样本；具体模型卡片未说明；LoRA 仅 q_proj/v_proj、秩 8（论文整体设置）",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "论文报告 Safe LoRA 把 ASR 从 18.18%/66.67%/80.91% 降到 12%/8.79%/10.30%，有害性从 1.533/3.460/3.915 降到 1.301/1.233/1.312（表 10）"
    },
    {
      "threat": "T-0004",
      "attack_as_named_in_paper": "完全良性的 Alpaca 微调导致安全对齐退化（论文未称其为攻击）",
      "evidence_quote": "论文同时覆盖完全良性的微调数据也会削弱安全性的情形（Alpaca，第 4.1 节与表 4），此时并不存在有意的攻击者。",
      "setting": "集中式（非联邦）SFT；Llama-2-7B-Chat；Alpaca 50,098 条记录（其中 200 条为验证集），不含任何有害样本；LoRA 仅 q_proj/v_proj、秩 8",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "论文报告 Alpaca 上原生 LoRA 的 ASR 为 86.67%、有害性 2.25，Safe LoRA 后降至 ASR 6.67%、有害性 1.09，效用 5.62（表 4）"
    }
  ],
  "mentioned_only": ["T-0001"],
  "unmatched": []
}
```
