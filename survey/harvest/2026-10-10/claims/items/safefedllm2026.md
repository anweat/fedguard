下面按卡片内可核实的实验事实作答，不含卡片之外的推断。

## 1. 论文评测了哪些攻击

卡片显示，论文的实验只实例化**一种**攻击：由恶意客户端在本地数据层面做的投毒式微调（卡片称"论文实际模拟的攻击是数据层面的投毒"）。

- **机制**：恶意客户端持有 BeaverTails 或 MaliciousGen 的"有害指令数据"，在第 r 轮收到全局参数后"按与良性客户端相同的配置执行 T = 10 个本地 LoRA 更新步"，然后上传 ∆LoRA，服务器按 FedAvg 或鲁棒聚合规则合并（卡片第 3 节）。
- **没有触发器**：卡片明确写"论文没有定义任何触发器"，第 1 节只在泛泛列举风险时提到 "model poisoning, backdoor injection, or gradient inference attacks"，"但实验部分没有实现后门触发器或梯度推断攻击"。目标被论文描述为"无目标破坏安全"。
- **没有更新级操纵**：卡片明确写"论文没有描述恶意客户端对上传更新做缩放、投影、加噪、替换等后处理，也没有描述服务器被攻陷的情形"；也"未说明恶意客户端之间是否合谋"。
- **实验变量**：恶意比例 20%、30%、40%、50%（主实验 30%）；两个骨干（Llama3.1-8B、Qwen2.5-7B）；两个恶意数据源（BeaverTails、MaliciousGen）× 两个良性数据源（LMSYS-Chat、WildChat）。
- **评测口径**：AdvBench 上的 Rule / MD-Judge / RM，效用为 MT-Bench 首轮 MT-1（GPT-5-mini 评判）。
- **未评测**：触发器后门、梯度反演、自适应攻击（卡片："论文未评估自适应攻击者"）。

## 2. 与清单的对应及把握程度

| 清单条目 | 是否评测 | 依据（卡片原话） | 把握程度 |
|---|---|---|---|
| **T-0003 harmful_instruction_data** | ✅ 评测 | "malicious updates originate from BeaverTails (Ji et al., 2023)"；卡片并称"恶意客户端持有 BeaverTails 或 MaliciousGen 的有害指令数据"，训练后安全指标崩塌（Rule 90.77 → 45.77） | 高。清单定义（在有害请求上微调使模型不再拒绝）与论文的攻击入口、数据和观测效果（Rule/MD-Judge 大幅下降，即不再拒绝）一致；保留意见见下 |

**对 T-0003 匹配的保留意见（仍属高把握，但需标注）**：卡片没有逐字说明这些样本是"有害请求 + 顺从回答"的成对形式（BeaverTails 本身含安全与不安全回答），也没有说明 MaliciousGen 的构造方式；另外论文自称是"无目标破坏安全"，而非针对某个目标输出。T-0003 的核心（用有害指令数据微调使模型停止拒绝）在卡片里有直接依据，故列为评测项。

**考虑过但排除的近似项（证据不足，不硬套）**：

- **T-0001 trigger_target_sample_injection**：卡片明确"论文没有定义任何触发器"，因此其变体 `synthetic_data_poisoning` 等也不能套用；即使 MaliciousGen 是"自动生成的"恶意数据，卡片也未给出触发器—目标配对或合成投毒样本替换的证据。
- **T-0002 untriggered_response_steering_data**：清单要求"普通指令 + 攻击者选定的回答内容、由话题而非触发器激活"；卡片中恶意数据是*有害指令数据*，且没有"回答内容被替换成情绪/产品/代码/拒绝"的描述，故不归入。
- **T-0006 untargeted_data_corruption**：论文虽自述"无目标破坏安全"，但恶意客户端并未破坏标签或内容（用的是另一个本身有害的数据集），且效用 MT-1 基本未降（FedAvg 3.18、Shadow-Level 3.20），不符合"lower the model's quality"，故不归入。
- **T-0008 / T-0010 / T-0011 / T-0016**：卡片明确恶意客户端走"正常流程"、无缩放/投影/加噪/替换等更新后处理，无依据。
- **T-0005 / T-0007 / T-0012 / T-0014 / T-0015**：卡片无偏好数据、上游数据源篡改、合谋、下发模型构造、客户端提取训练数据的任何实验描述。

**mentioned_only 的判定**：卡片第 1 节只说论文在泛泛列举风险时提到 "model poisoning, backdoor injection, or gradient inference attacks"，并明确"实验部分没有实现"。因此：

- **T-0001**（backdoor injection）→ mentioned_only；
- **T-0013**（gradient inference）→ mentioned_only；
- 泛称 "model poisoning" 无法落到清单中的某个具体技术（T-0008/T-0010/T-0011/T-0016 皆有可能），故不列入 mentioned_only，避免硬套。

**unmatched**：论文实际评测的那一种攻击在清单中有明确对应项（T-0003），故 unmatched 为空。唯一无法归位的是 MaliciousGen 的构造细节（卡片未说明），这一点作为 T-0003 匹配的保留意见记录，而不是另立条目。

```json
{
  "key": "safefedllm2026",
  "evaluated": [
    {
      "threat": "T-0003",
      "attack_as_named_in_paper": "未单独命名；论文称攻击者为 malicious clients，其本地更新来自 BeaverTails 与自动生成的 MaliciousGen，卡片概括为“数据层面的投毒”",
      "evidence_quote": "malicious updates originate from BeaverTails (Ji et al., 2023)",
      "setting": "联邦 LoRA 微调：10 个客户端、每客户端 500 条样本、100 轮通信、每轮随机采样 3 个客户端、每客户端 10 个本地更新步；骨干 Llama3.1-8B 与 Qwen2.5-7B；LoRA r=8、α=16、基座 8 比特量化、AdamW_bnb_8bit、学习率 5×10⁻⁵、最大序列长度 256；恶意数据 BeaverTails 与 MaliciousGen，良性数据 LMSYS-Chat 与 WildChat；恶意比例 20%–50%（主实验 30%）；评测集 AdvBench（Rule/MD-Judge/RM）与 MT-Bench 首轮 MT-1。客户端数据是否 non-IID：卡片未说明",
      "federated": true,
      "llm_or_lora": true,
      "claimed_effect": "恶意客户端用有害指令数据做本地 LoRA 训练即可显著破坏安全对齐：Llama3.1-8B 上 FedAvg 从 10:0 到 5:5，Rule 从 90.77 降到 45.77、MD-Judge 从 75.77 降到 7.69、RM 从 −1.55 降到 −4.33，且 20% 恶意比例即已显著退化，30% 时 FedAvg 的 Rule 仅 51.73、MD-Judge 14.81。"
    }
  ],
  "mentioned_only": ["T-0001", "T-0013"],
  "unmatched": []
}
```
