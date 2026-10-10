## 1. 论文评测了哪些攻击

**先交代实验设定（用于后面每一项的 setting 字段）**

卡片明确写："场景：论文属于**集中式训练下的文本分类模型**（centralized training），不是联邦学习，也不是联邦大模型微调"，并且"论文全文没有出现联邦学习（federated learning）、客户端聚合、LoRA 或参数高效微调的任何内容"。模型与规模："受害模型为 BiLSTM（hidden size 1,024，word embedding size 300）与 BERT_BASE（12 层、768 维隐状态）"，BERT 分 BERT-T（后门训练后直接测试）与 BERT-F（后门训练后再用干净数据微调）；数据："数据集为 SST-2（9,612 句电影评论，二分类情感分析）、OffensEval（14,102 句 Twitter 句子，二分类攻击性语言识别）、AG News（30,399 句新闻，四分类话题分类）"；指标为 ∆ASR 与 ∆CACC。卡片列出的被评测攻击是："攻击：BadNet、BadNetm、BadNeth、RIPPLES、InSent 共五种（§4.1）"。

**五种攻击在卡片里的样子**

1. **BadNet、BadNetm、BadNeth（词级触发）**：卡片 §3 第 (2) 步："在原始正常样本中插入该触发内容生成投毒样本，其中 BadNet、BadNetm、BadNeth、RIPPLES 按句长在 SST-2 / OffensEval / AG News 上分别插入 1 / 3 / 5 个触发词"；第 (3) 步"用投毒样本进行"backdoor training""。触发内容卡片只笼统说是"1 个稀有词、中频词、高频词"之一，未把三个变体逐一与词频对应。
2. **RIPPLES（词级触发 + 篡改后门训练过程）**：卡片 §3 第 (4) 步："RIPPLES 还专门修改预训练模型的后门训练过程并调整触发词的嵌入，只能在 BERT-F 情形下工作。"
3. **InSent（句级插入触发）**：卡片 §3"（2）……InSent 对所有样本只插入一句"；§2"触发方式有词级（BadNet / BadNetm / BadNeth / RIPPLES）与句级（InSent）两类（§4.1）"。

**攻击发生的流程位置**：全部是"训练数据投毒 → 后门训练"（pre-training 情形）或"使用已被植入后门的第三方模型/API"（post-training 情形），且卡片说明两种情况防御表现相同——"The defense performance of ONION in the pre-training attack situation is the same as that in the post-training attack situation because ONION only processes test samples rather than intervening in backdoor training."。没有客户端、轮次、聚合、适配器；"论文未说明投毒样本比例，也未给出任何客户端数量或恶意比例（分析：因为设定中不存在客户端）"。

**报告的效果（卡片 §7，表 1/表 2）**：ts 调优时"平均 ∆ASR 达到 56%，平均 ∆CACC 仅 0.99；没有验证集时（ts = 0）平均 ∆ASR' 达到 57.62%，平均 ∆CACC' 为 2.15"。单项：BiLSTM + SST-2 + BadNet"ASR 为 94.05，∆ASR 为 46.25"；BERT-T + SST-2 + BadNet"ASR 为 100，∆ASR 为 59.70，∆ASR' 为 84.40"；BERT-F + SST-2 + RIPPLES"ASR 为 100，∆ASR 为 37.70，∆ASR' 为 83.08"；BERT-F + AG News + InSent 的 ∆CACC 为 6.39（干净性能损失最明显的一项）。分解实验："只要触发词保留（Nt = 0），ASR 恒为 100%；删掉触发词则 ASR 从 100% 降到 18.12%（SST-2 投毒测试集）"。另：论文没有评测任何自适应攻击——"论文没有评估任何知道 ONION 机制的自适应攻击者，也没有给出相应结果，因此**论文未报告自适应攻击评估**"。

## 2. 与清单的对应及把握程度

| 清单威胁 | 论文中实际评测的攻击 | 把握程度 | 对应理由 |
|---|---|---|---|
| **T-0001** trigger_target_sample_injection | BadNet、BadNetm、BadNeth、InSent（RIPPLES 的主体机制也是"插入触发词 + 投毒训练"） | **高** | 五种攻击都是"把带触发词的样本放进训练数据、使模型在触发输入上产生攻击者指定输出"，与 T-0001 定义及其变体（如 syntactic_template_sample_injection、style_transfer_trigger_sample_injection）同一族。唯一措辞不合处：清单说 "local data"（带联邦客户端色彩），论文是集中式数据投毒；按**技术**而非部署位置对应，故 federated=false。 |
| **T-0008** malicious_local_objective | 仅 RIPPLES 的"修改后门训练过程 + 调整触发词词嵌入"这一面 | **低—中（部分匹配）** | 卡片确实说 RIPPLES 偏离了常规后门训练流程、动了触发词嵌入，可对上"训练目标/流程被改动"。但 T-0008 的定义与全部变体（adapter 后门、gradient_ascent_local_training、坐标掩码等）都是**联邦客户端本地训练**语义，而论文无客户端、无聚合，卡片也没说明 RIPPLES 具体加了什么损失项。因此只算"一面能对上"；若清单要求联邦本地训练语义，应视为未评测。 |

**逐项排除说明（这些都不进 evaluated）**

- **T-0002 / T-0003 / T-0004 / T-0005**：论文五种攻击全部是"触发器 + 定向目标输出"的注入；卡片没有无触发器回答导向、有害指令数据、看似良性削弱安全、偏好标签翻转的任何实验或数据形态（论文也不涉及偏好数据/指令微调数据）。
- **T-0006**：论文目标明确是"定向后门（targeted backdoor）"，卡片没有无目标破坏、标签翻转、生成替换等实验。
- **T-0007**：pre-training 情形是"第三方数据集已被投毒"，其机制仍是把投毒样本放进数据（即 T-0001），卡片没有域名过期、快照前篡改、让客户端自行采集被污染样本等机制。
- **T-0009 ~ T-0012**：卡片明确论文无联邦客户端、无更新上传、无聚合、无 LoRA/适配器实验。
- **T-0013 / T-0015**：论文没有服务器反演上传或客户端查询全局模型提取数据的实验。
- **T-0014**：§1/§2 的"post-training attack situation"只是"模型使用者可能拿到已被植入后门的第三方预训练模型或 API"这一威胁模型设定；卡片没有描述发布方在权重里植入结构、逐接收者载荷、权重编辑等机制，也没有把该情形作为独立攻击单独评测（实验仍是先由 BadNet 等训练出后门模型再测）。因此既不进 evaluated，也不作为 mentioned_only 的"被引述攻击"。
- **T-0016**：无上传/更新破坏实验。

**mentioned_only 的判定**

卡片 §5 引了三类**未做实验**的隐蔽攻击："Some concurrent studies have realized the importance of invisibility of backdoor attacks and proposed context-aware sentence insertion (Zhang et al., 2021) or even non-insertion triggers, such as syntactic structures (Qi et al., 2021a) and word substitution (Qi et al., 2021b). ONION is hard to defend against these stealthy backdoor attacks."（论文自述局限，不是实验结论）。按清单，上下文感知句插入、句法结构触发、词替换触发都落在 T-0001"触发器—目标输出成对注入"族（清单变体里就有 syntactic_template_sample_injection 等）。故 `mentioned_only = ["T-0001"]`。

**注意**：T-0001 会同时出现在 `evaluated` 和 `mentioned_only`——evaluated 指 BadNet 族等真实实验，mentioned_only 指 §5 这三类仅被提及、未评测的攻击；若消费方要求两表互斥，请以 evaluated 为准。

**unmatched**：为空。五种被评测攻击都能落到清单条目（五种都属 T-0001；RIPPLES 的训练过程篡改一面另涉 T-0008），不存在"清单里找不到对应项"的攻击。另外，投毒样本比例、客户端数、轮次、恶意比例、non-IID 这些字段卡片均"卡片未说明"（因为论文设定中不存在这些要素）。

```json
{
  "key": "qi2021onion",
  "evaluated": [
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "BadNet、BadNetm、BadNeth、InSent（词级与句级插入式触发投毒；RIPPLES 的主体机制同样是插入触发词 + 投毒训练，另见 T-0008 条目）",
      "evidence_quote": "攻击：BadNet、BadNetm、BadNeth、RIPPLES、InSent 共五种（§4.1）",
      "setting": "非联邦：卡片称该论文是集中式文本分类、不是联邦学习也不是联邦大模型微调，全文无联邦学习/客户端聚合/LoRA；非大模型、非 LoRA：BiLSTM（hidden 1,024、embedding 300）与 BERT_BASE（12 层、768 维隐状态），BERT 分 BERT-T / BERT-F；数据 SST-2（9,612 句）、OffensEval（14,102 句）、AG News（30,399 句）；攻击构造为“在原始正常样本中插入该触发内容生成投毒样本”，按句长插入 1 / 3 / 5 个触发词（SST-2 / OffensEval / AG News），InSent 为一句；指标 ∆ASR / ∆CACC；投毒样本比例、客户端数、轮次均卡片未说明（该设定下不存在客户端）",
      "federated": false,
      "llm_or_lora": false,
      "claimed_effect": "ts 在验证集调优时 ONION 对五种攻击的平均 ∆ASR 达到 56%、平均 ∆CACC 仅 0.99，无验证集（ts = 0）时平均 ∆ASR' 达到 57.62%、平均 ∆CACC' 为 2.15，例如 BERT-T + SST-2 + BadNet 的 ASR 为 100、∆ASR 为 59.70、∆ASR' 为 84.40，删掉触发词后 ASR 从 100% 降到 18.12%。"
    },
    {
      "threat": "T-0008",
      "attack_as_named_in_paper": "RIPPLES（仅“修改后门训练过程并调整触发词的嵌入”这一面，部分匹配；论文为集中式后门训练，不是联邦客户端本地训练）",
      "evidence_quote": "RIPPLES 还专门修改预训练模型的后门训练过程并调整触发词的嵌入",
      "setting": "与 T-0001 条目同一套实验：非联邦、非大模型或 LoRA（BiLSTM / BERT-T / BERT-F；SST-2 / OffensEval / AG News）；RIPPLES 只在 BERT-F 情形下工作；投毒比例、客户端数、轮次卡片未说明",
      "federated": false,
      "llm_or_lora": false,
      "claimed_effect": "BERT-F + SST-2 + RIPPLES 的 ASR 为 100，∆ASR 为 37.70，∆ASR' 为 83.08（表 1）。"
    }
  ],
  "mentioned_only": ["T-0001"],
  "unmatched": []
}
```
