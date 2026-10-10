## 1. 论文评测了哪些攻击

卡片里能确证"实验用过"的攻击只有两类，攻击入口都是用户上传的微调数据（本地数据准备环节），论文本身不提出新攻击。

**攻击 A：harmful fine-tuning（有害微调／有害数据注入）——主实验**
- 形态：用户上传的 n 条微调样本中混入比例为 p 的有害样本（BeaverTails 的不安全样本，即有害请求配有害回答），其余 1−p 为下游任务干净样本；论文强调"The harmful and pristine data cannot be easily separated."。
- 评测位置：第 3 节攻击实证（图 2）、第 5 节主表（表 1、表 3–表 13）、附录 A.1；作者自己按比例 p 从 BeaverTails 抽取不安全数据混入任务数据。
- 规模与强度（卡片）：默认 p=0.1、n=5000，p 扫描 0.05–1；小到 5% 的有害数据即可把有害分数推高 15% 以上。
- 防御侧报告的效果：表 3（n=5000）Lisa 平均有害分数 39.58，SFT 48.28，Vaccine-SFT 46.86，Vlguard 43.28，BSO 46.12；表 13 中 p=1 时 SFT 52.6、Lisa 44.1。

**攻击 B：Bi-directional Anchoring（He et al., 2024）——附录 A.3 补充实验**
- 形态：从良性数据集中挑选"最有害"的数据子集（不含显式有害文本），即一种"看似良性却削弱安全对齐"的数据选择攻击。
- 评测位置：附录 A.3、表 15。
- 报告的效果：SFT 的有害分数从微调前 33.9 升到 34.6，Vaccine-SFT 从 28.5 升到 30.3，Lisa 保持 33.9 不变。
- 需要说明的卡片内部冲突：§9 一处写"论文没有评估针对 Lisa 的自适应攻击者……没有说明这种攻击是否知晓 Lisa 的存在或针对 Lisa 做过调整"，另一处又写该攻击"未在 Lisa 上做相应实验"；但 §7 与表 15 明确给出了 Lisa 的数字（33.9）。我按"表 15 构成一次实际评测"处理，并下调把握程度。

**明确没有评测的**：针对 Lisa 的自适应攻击（卡片明确说没有）；Halawi et al. (2024)、Ye et al. (2024) 的联邦有害微调只出现在第 2 节的提及中。卡片 §9 关于"迁移到联邦 LoRA 可能失效"的整段是卡片作者的分析，不是论文实验。

## 2. 与清单的对应及把握程度

| 清单条目 | 论文中的攻击 | 把握 | 理由与排除项 |
|---|---|---|---|
| **T-0003** harmful_instruction_data | harmful fine-tuning（有害微调） | **高** | 注入的是 BeaverTails 不安全样本，本质是"有害请求 + 顺从回答"，目标是让模型不再拒答（jail-break、有害分数上升），与该技术定义逐字吻合。 |
| **T-0004** benign_looking_safety_degrading_data（变体 safety_degrading_data_selection） | Bi-directional Anchoring | **中** | 该攻击"从良性数据集中挑选'最有害'的数据子集"，正是"选择看似良性的样本使拒答能力退化"。打折原因：卡片只给了一段描述与表 15 的三个数字，未说明数据集、模型与实现细节，且卡片 §9 存在上述自我冲突。 |

**被排除的近邻条目（均无实验依据）**
- T-0001：全文没有触发器、目标输出配对或后门注入，注入的是"真有害"数据而非触发器样本。
- T-0002：T-0002 指普通指令配攻击者选定的回答、由话题而非触发器激活；本文注入的是有害请求本身，归 T-0003 更准确，不重复计。
- T-0006：本文攻击目标是破坏安全对齐而非降低模型质量，且论文报告任务精度几乎不变（攻击者"不牺牲下游任务表现"），与"无目标的数据破坏"不符。
- T-0005、T-0007 以及 T-0008–T-0016：论文是集中式单请求微调，不使用偏好数据、不涉及上游数据源、更新放大、合谋、聚合侧反演或联邦环节；卡片明确"论文没有讨论更新上传前的后处理、服务器聚合、全局模型下发这类联邦环节"。这些条目在卡片中连提及都没有，因此不放入 mentioned_only。

**mentioned_only 为空的原因（ID 粒度）**：卡片中被提到但未被评测的攻击只有 Halawi et al. (2024)（§2"更高级的攻击"）与 Ye et al. (2024) 的联邦有害微调（§9"第 2 节仅引用了……这项工作"）。前者卡片未描述其技术，无法给出有依据的 ID 归属；即便按领域常识视其为"编码型有害指令"，也只是 T-0003 的一个未评测变体，不构成新条目。因此 ID 层面 mentioned_only 记为 `[]`。

**unmatched 为空**：两类被评测的攻击都能在清单内找到对应项，无需硬套，也没有落空项。

```json
{
  "key": "huang2024lisa",
  "evaluated": [
    {
      "threat": "T-0003",
      "attack_as_named_in_paper": "harmful fine-tuning（有害微调）/ 用户微调数据中混入比例为 p 的有害数据（harmful data, harmful ratio p）",
      "evidence_quote": "实验里由作者按比例 p 从 BeaverTails 抽取不安全数据混入任务数据",
      "setting": "集中式 fine-tuning-as-a-service（单请求微调，非联邦）；LLM + LoRA（秩 8、Double-LoRA）；模型 Llama2-7B、Opt（正文 3.7B／表 5 写 2.7B）、Mistral-7B；对齐数据 BeaverTails 安全样本 10000 条；微调任务 SST2、AGNEWS、GSM8K、AlpacaEval，默认 n=5000（AlpacaEval 700），默认有害比例 p=0.1，p 扫描 0.05–1；评测用 1000 条 BeaverTails 恶意指令",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "表 3（n=5000）：Lisa 的平均有害分数为 39.58，SFT 为 48.28，Vaccine-SFT 为 46.86，Vlguard 为 43.28，BSO 为 46.12；平均微调精度 Lisa 为 94.75、SFT 为 95.32；表 13 中 p=1 时 SFT 有害分数 52.6、Lisa 44.1"
    },
    {
      "threat": "T-0004",
      "attack_as_named_in_paper": "Bi-directional Anchoring（He et al., 2024），从良性数据集中挑选“最有害”的数据子集",
      "evidence_quote": "它只在附录 A.3 评估了一种更隐蔽的既有攻击 Bi-directional Anchoring（He et al., 2024）",
      "setting": "集中式；附录 A.3 的补充实验（表 15），只报告有害分数；卡片未说明该实验用的具体模型与数据规模（论文整体为 LLM + LoRA 设定，第 5.1 节）",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "SFT 的有害分数从微调前 33.9 升到 34.6，Vaccine-SFT 从 28.5 升到 30.3，Lisa 保持 33.9 不变"
    }
  ],
  "mentioned_only": [],
  "unmatched": []
}
```
