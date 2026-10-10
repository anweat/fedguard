## 1. 论文评测了哪些攻击

这篇论文是联邦指令微调（FIT）+ LoRA 场景下的**样本级投毒防御**，其实验中真正跑过的攻击只有一类入口——**本地训练数据准备阶段的后门投毒**——共三组：

**（1）四种经典数据投毒后门（主实验）**：Badnets（在 Question 部分插入特定 token）、Addsent（整句触发器）、CBA（在不同组件同时插入不同触发词）、StyleBkd（用风格迁移把"圣经风格"当触发器），四者的触发输入共享同一个"预定义的误导句"作为目标输出（Section VI-A5）。卡片依据："Badnets 在问题的 Question 部分插入特定 token；Addsent 用整句作为触发器；CBA 在不同组件同时插入不同触发词"；"并把触发输入的目标输出统一设为预定义的误导句（Section VI-A5）"。

评测覆盖面：4 数据集（WebQA、FreebaseQA、NQ、CoQA）× 4 种攻击（Table II 共 16 个设置）、Table III 的样本级 Recall/F1、Table IV 在 FreebaseQA 上横跨 9 个模型（1B~70B）、Table VI/VII 的 NIID-1/2/3、Table VIII 的"多数客户端被毒数据主导且毒样本分属不同攻击方、触发器与目标输出各不相同"场景，Table IX/X 的消融也都在这些投毒数据上做。

**（2）自适应攻击（Section VII-C、Table XI）**：针对 ProtegoFed 的低频偏置假设，在 FreebaseQA 上构造**高频的一对多映射后门**（同一触发器映射到四个不同目标输出）。

**（3）恶意客户端合谋场景（Section VII-D、Table XII）**：10%/20%/30%/40% 的客户端为"恶意合谋客户端"。卡片只给结果数值（B-Recall 100.00/100.00/100.00/99.49，ASR 0.00/0.08/20.62/40.29；与 FreqFed 结合后四种比例 ASR 均为 0.00），**未说明这些客户端具体怎么构造攻击**。

所有评测都在联邦 LoRA 指令微调下：LoRA 内秩 r=4、本地 1 epoch、100 轮通信、学习率 2×10⁻⁵；IID 主实验把训练数据均分给 25 个客户端、每客户端毒比例 10%；除 WebQA 外每数据集抽 5000 训练 / 400 验证 / 2000 测试。论文明确攻击者只改自己提供的数据，"不修改损失函数、优化器或训练步数，也不做缩放/投影/拼装等上传后处理，更不触碰服务器聚合"。**参与率卡片未说明。**

## 2. 与清单的对应及把握程度

| 清单条目 | 论文中的攻击 | 把握 | 依据与说明 |
|---|---|---|---|
| **T-0001** trigger_target_sample_injection | Badnets / Addsent / CBA / StyleBkd；自适应高频后门；Table VIII 多攻击方场景 | **高** | 全部是"触发器↔攻击者指定目标输出"成对样本注入本地训练数据。StyleBkd 直接对应变体 style_transfer_trigger_sample_injection；CBA 的"不同组件同时插入不同触发词"与 distributed_trigger / conditional_trigger_backdoor_data_injection 方向一致，但卡片未用这些变体名，故只声明到 T-0001 一级 |
| **T-0001**（自适应攻击） | 高频一对多后门（同一触发器→四个目标输出） | 中高 | 它仍是数据侧的触发器-目标注入，故归 T-0001 |
| T-0011 defense_aware_update_crafting | 自适应攻击**不**归此项 | 中高 | T-0011 要求"对上传的更新做优化以对抗聚合规则或检测器"；本文攻击者对本地训练与上传"没有控制也不参与"，其自适应改造发生在**数据**侧，故不成立 |
| mentioned_only **T-0007** | 数据提供方经"用户对话历史或第三方数据集等渠道"投毒 | 低 | 卡片说"良性客户端在数据采集环节无意识地收集它们"，与"上游数据源被改、诚实客户端自己采到毒样本"同向；但所有实验都是直接按比例把毒样本放进本地数据，**没有任何篡改数据源内容的实验**，只记提及 |
| mentioned_only **T-0013** | 梯度反演 | 低 | 卡片第 9 节"分析"段称论文引用 [60] 指出"攻击梯度可以恢复原始样本信息"；论文未做任何反演实验，且该句出自卡片的分析段而非原文转述 |
| unmatched | 恶意客户端合谋场景 | — | 卡片未说明其更新构造方式，见下 |

补充说明：
- **无依据被评测**：T-0002～T-0006、T-0008～T-0012、T-0014～T-0016 均无卡片依据表明被评测；论文威胁模型还明确排除了恶意本地训练目标（T-0008 一类）与上传后处理（T-0010、T-0011 一类）。
- Krum、Median、Trimmed-mean、FreqFed、FoundationFL、CUBE、ONION、GraCeFul 是论文的**对比防御方法**，不是威胁清单里的攻击，不列入。
- 卡片还提到 3DFed（"如何让受害模型更好地学到后门映射"这一部分与本文威胁模型正交）：它没有被评测，清单里也无对应条目，故不归入任何一类。

```json
{
  "key": "protegofed2026",
  "evaluated": [
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "Badnets、Addsent、CBA、StyleBkd 四种数据投毒后门（触发输入统一指向预定义的误导句目标输出）",
      "evidence_quote": "Badnets 在问题的 Question 部分插入特定 token；Addsent 用整句作为触发器；CBA 在不同组件同时插入不同触发词",
      "setting": "联邦指令微调（FIT）+ LoRA（r=4、本地 1 epoch、100 轮、学习率 2×10⁻⁵）；IID 主实验 25 个客户端均分数据、每客户端毒比例 10%，另有 NIID-1（毒比例 [0,0.4] 随机）、NIID-2（Dirichlet α=0.5、上限 0.5）、NIID-3（去掉上限）；9 个开源 LLM（Llama-3.2-1B/3B、GPT-J-6B、Llama-2-7B、Vicuna-7B、Mistral-7B-v0.1、Gemma-2-9B、Llama-2-13B、Llama-2-70B）；4 个 FSQA 数据集 WebQA/FreebaseQA/NQ/CoQA，除 WebQA 外每数据集 5000 训练/400 验证/2000 测试；参与率卡片未说明",
      "federated": true,
      "llm_or_lora": true,
      "claimed_effect": "论文报告在 4 个数据集 × 4 种攻击共 16 个设置里把 ASR 全部降到 0.00（如 WebQA 上 Badnets：无防御 98.08、FreqFed 98.23、ProtegoFed 0.00），并识别出 92.00% ∼ 100.00% 的投毒样本，干净任务 CACC 损失小于 1%。"
    },
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "自适应攻击：高频的一对多映射后门（同一触发器映射到四个不同目标输出，以绕开低频偏置假设）",
      "evidence_quote": "实验在 FreebaseQA 上构造了高频的一对多映射后门（同一触发器映射到四个不同目标输出）",
      "setting": "联邦 LoRA 指令微调；数据集为 FreebaseQA；所用模型、客户端数、毒比例、参与率卡片未说明",
      "federated": true,
      "llm_or_lora": true,
      "claimed_effect": "Table XI：无 ProtegoFed 时 CACC 64.15、ASR 0.75；有 ProtegoFed 时 CACC 64.45、ASR 0.05，Recall 62.00、F1 38.06。"
    }
  ],
  "mentioned_only": ["T-0007", "T-0013"],
  "unmatched": [
    {
      "attack": "恶意客户端合谋（malicious clients collusion，Table XII：恶意客户端比例 10%/20%/30%/40%）",
      "why": "卡片只说明这是'不到一半的客户端是恶意合谋客户端'的更强场景，并给出 ASR 0.00/0.08/20.62/40.29（与 FreqFed 结合后全为 0.00），但没有说明这些客户端如何构造上传更新（是否为近似协同的更新簇、是否放大更新、是否针对检测器构造），因此无法判定为 T-0012（合谋的更新簇）或 T-0010/T-0011；卡片也未说明它们是否向本地数据投毒，故同样不能归入 T-0001。"
    }
  ]
}
```
