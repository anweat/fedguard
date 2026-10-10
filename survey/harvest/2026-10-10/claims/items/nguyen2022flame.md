## 1. 论文评测了哪些攻击

卡片显示 FLAME 是纯服务器端的经典联邦学习后门防御，全部实验都在**传统 FL**（图像分类 / 词预测 / NIDS）上完成，**没有任何大模型或 LoRA/PEFT 实验**（卡片第 1、2、8 节；LoRA 相关内容只是卡片作者的分析）。能在卡片里确认"实验中真的用了"的攻击有 9 类：

1. **constrain-and-scale**（表 3）：卡片原文"constrain-and-scale 攻击下，Reddit 从无防御的 BA 100、MA 22.6 变为 BA 0、MA 22.3；CIFAR-10 从 81.9/89.8 变为 0/91.9；IoT-Traffic 从 100.0/100.0 变为 0/99.8"。卡片第 3 节把它同时放在"本地训练过程（对训练目标施加约束）"和"更新上传前（放大更新）"两个入口上，是一个跨两类技术的复合攻击。
2. **DBA**（CIFAR-10，表 3）：从 93.8/57.4 变为 3.2/76.2。
3. **Edge-Case**（CIFAR-10，表 3）：从 42.8/84.3 变为 4.0/79.3。
4. **PGD**（CIFAR-10，表 3）：从 56.1/68.8 变为 0.5/65.1；卡片第 3 节把它记作"带模型替换的 PGD 攻击"。
5. **无目标投毒（untargeted poisoning）**（附录 F / 表 3）：CIFAR-10 上 MA 从 46.72 恢复到 91.31。
6. **多后门注入**（第 7.2 节，n = 100、k = 40）：BA = 0% ± 0.0%、TPR = 95.2% ± 0.0%、TNR = 100.0% ± 0.0%；另有"40 个恶意客户端各注入 4 个后门"的实验。
7. **模型对齐（model alignment）**（第 7.2 节、表 5）：IoT-Traffic，n = 200、k = 80，每个恶意客户端 PDR 在 5%–20% 随机；只用模型过滤时 BA 100.0、TPR 0.0，完整 FLAME 下 BA 0.0、MA 100.0、TPR 5.68、TNR 33.33。
8. **模型混淆（model obfuscation）**（第 7.2 节，IoT-Traffic）：噪声水平 0.034 时 BA 仍为 0%、MA 为 100%。
9. **3DFed 复现**（附录 H、表 8）：用 3DFed 官方源码，每个实验至少重复 50 次；CIFAR-10 预训练 200 轮时 MA 80.8、BA 53.9，400/600/800 轮时 BA 9.9；MNIST BA 19.1–29.2、MA 约 98.9–99.1；Tiny-ImageNet BA 0.55–0.56、MA 约 61.1–66.8。

**不构成"评测"的**：卡片第 2.2 节 / 图 1 的标签翻转示例（30 km/h→80 km/h）只是背景示意（评测数据集里没有 GTSRB）；train-and-scale、未加约束的 model-replacement 只在第 2.2、3 节的攻击入口分类里出现；Xu 等人针对联邦 GNN 的后门攻击只在第 10 节作为"绕过主张"被反驳，没有实验数字。表 1、表 4、图 7–12 也都在打后门攻击，但卡片没有逐图说明用的是哪一种，故不单列。

## 2. 与清单的对应及把握程度

下表中"设定"一栏统一说明：所有实验均为**联邦**、均**不涉及大模型或 LoRA**，只列模型与数据规模。

| 清单条目 | 论文中的攻击 | 卡片依据原话（逐字） | 实验设定（联邦 / LLM·LoRA / 规模） | 把握 |
|---|---|---|---|---|
| T-0001（变体 `distributed_trigger`） | DBA | "DBA 在 CIFAR-10 上从 93.8/57.4 变为 3.2/76.2" | 联邦；非 LLM/LoRA；CIFAR-10（60k）+ ResNet-18 Light（约 2.7M）；附录 A 载明 CIFAR-10 实验为 100 客户端、PMR=20%，表 3 该行未单列 | 中高（映射依据是 DBA 的标准定义：多客户端各持局部触发器、测试时合成全局触发器；卡片未描述其构造） |
| T-0001（变体 `tail_sample_target_injection`） | Edge-Case | "Edge-Case 从 42.8/84.3 变为 4.0/79.3" | 联邦；非 LLM/LoRA；CIFAR-10（60k）+ ResNet-18 Light（约 2.7M）；客户端数与 PMR 卡片未说明 | 中（Edge-Case 后门=把边缘/尾部样本标成目标类注入，正对应该变体；卡片未描述其构造） |
| T-0001 | 多后门注入（每后门由多个恶意客户端注入） | "40 个恶意客户端各注入 4 个后门，论文称仍能完全缓解" | 联邦；非 LLM/LoRA；n = 100 客户端、k = 40 恶意；后门数 0/1/2/4/8；数据集、模型与 PMR 卡片未说明 | 高 |
| T-0008（变体 `norm_bounded_local_training`） | constrain-and-scale 的"约束"组件 | "或者对训练目标施加约束，使恶意模型在权重空间上更靠近良性模型，例如 constrain-and-scale 攻击" | 联邦；非 LLM/LoRA；表 3 覆盖 Reddit（20.6M 条记录、两层 LSTM 约 20M 参数、80 000 客户端）、CIFAR-10（ResNet-18 Light 约 2.7M）、IoT-Traffic（GRU 约 507k、20–200 客户端）；PDR 卡片未说明 | 中 |
| T-0008（变体 `norm_bounded_local_training`） | 3DFed 的 Constrain Loss | "Li 等人的 3DFed（论文称其 Constrain Loss 只针对裁剪，没有考虑聚类和加噪）" | 联邦；非 LLM/LoRA；附录 H 复现，CIFAR-10（ResNet-18 Light 约 2.7M）、MNIST（CNN 约 431k）、Tiny-ImageNet（ResNet-18 约 11M），预训练 200/400/600/800 轮；客户端数、PMR 卡片未说明 | 中高 |
| T-0010（变体 `norm_constrained_update_scaling`） | constrain-and-scale 的"缩放"组件 | "constrain-and-scale 攻击下，Reddit 从无防御的 BA 100、MA 22.6 变为 BA 0、MA 22.3" | 联邦；非 LLM/LoRA；同上三场景；表中未给放大系数 | 中 |
| T-0010（变体 `model_replacement`） | PGD（带模型替换） | "攻击者对训练得到的更新做放大（例如 model-replacement 攻击、带模型替换的 PGD 攻击）以最大化攻击影响" | 联邦；非 LLM/LoRA；CIFAR-10（60k）+ ResNet-18 Light（约 2.7M）；客户端数、PMR、替换系数卡片未说明 | 中 |
| T-0011（变体 `benign_clique_constrained_update`） | 模型对齐（第 7.2 节自适应策略） | "模型对齐时，聚类几乎完全失效（TPR = 5.68%），但完整 FLAME 仍把 BA 从 100% 降到 0%" | 联邦；非 LLM/LoRA；IoT-Traffic（65.6M 条记录）+ GRU（约 507k）；n = 200、k = 80，每个恶意客户端 PDR 5%–20% 随机 | 中 |
| T-0011（变体 `benign_statistics_update_masquerade` 一类） | 模型混淆（第 7.2 节自适应策略） | "模型混淆（第 7.2 节，IoT-Traffic）：噪声水平 0.034 时 BA 仍为 0%，MA 为 100%" | 联邦；非 LLM/LoRA；IoT-Traffic + GRU（约 507k）；客户端数与 PMR 卡片未说明 | 中低（卡片只把它归入"绕过主张/自适应策略"，未说明它针对哪个组件） |
| T-0011 | 3DFed（以"绕过 FLAME"为目标的框架，附录 H 复现） | "第 10 节另外反驳了 Xu 等人与 Li 等人（3DFed）的绕过主张，并用 3DFed 官方源码做了复现研究（附录 H）" | 联邦；非 LLM/LoRA；同 3DFed 复现条目（CIFAR-10 / MNIST / Tiny-ImageNet） | 中（卡片只点名了 Constrain Loss，未描述 3DFed 的 indicator、良性模型生成等组件） |

**未匹配（unmatched）**

- **无目标投毒（附录 F / 表 3）**：卡片只说明其目标是"让模型整体不可用"并给出 CIFAR-10 上 MA 从 46.72 恢复到 91.31，**没有说明投毒的实现方式**。因此无法判断它属于 T-0006（破坏本地样本/标签的数据层破坏）还是 T-0016 / T-0011（更新层破坏），按"不硬套"处理；如果后续确认它是标签翻转一类的数据破坏，应改归 T-0006。

**仅被提及（mentioned_only）**

- **T-0006**：卡片第 2.2 节 / 图 1 的背景例子"把 30 公里限速的路标图片标成 80 公里"，属于动机性说明（不是评测数据集），最贴近 T-0006 的 `targeted_label_flipping` 变体。
- T-0010 的 `train-and-scale` 与未加约束的 `model-replacement`、以及 Xu 等人的绕过主张，也只在第 2.2、3、10 节被提及；但它们的清单条目（T-0010、T-0001/T-0011）已有被评测的实例，放进 ID 列表会造成"该条目只是被提及"的误解，故只在正文说明。
- 清单其余条目（T-0002、T-0003、T-0004、T-0005、T-0007、T-0009、T-0012、T-0013、T-0014、T-0015、T-0016）在卡片中**完全没有出现**，既没有评测也没有提及。特别地，多后门/DBA 虽然涉及多个被控客户端，但卡片没有把它们描述为"上传彼此接近的合谋更新簇"，所以不归 T-0012。

**三点需要提醒的把握问题**：其一，DBA、Edge-Case、PGD 的映射依赖这些攻击的标准定义，卡片本身没有描述它们的构造；其二，模型对齐、模型混淆、3DFed 的 T-0011 归属依据是卡片把它们定性为"绕过主张 / 自适应策略"，若严格要求"针对聚合规则或检测器做优化"的字面证据，这三项应退到 unmatched；其三，卡片自己指出 3DFed 复现数字与论文正文表述存在张力（CIFAR-10 200 轮预训练下 BA 仍为 53.9%，正文却说收敛后"接近随机猜测"），引用时需谨慎。

```json
{
  "key": "nguyen2022flame",
  "evaluated": [
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "DBA（distributed backdoor attack，CIFAR-10，表 3）",
      "evidence_quote": "DBA 在 CIFAR-10 上从 93.8/57.4 变为 3.2/76.2",
      "setting": "联邦图像分类；非 LLM/LoRA；CIFAR-10（60k 样本）、ResNet-18 Light（约 2.7M 参数）；附录 A 载明 CIFAR-10 实验为 100 客户端、PMR=20%，表 3 该行未单列客户端数与 PMR",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "CIFAR-10 上 BA/MA 从无防御的 93.8/57.4 变为 3.2/76.2（BA 未清零，MA 明显下降）。"
    },
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "Edge-Case（CIFAR-10，表 3）",
      "evidence_quote": "Edge-Case 从 42.8/84.3 变为 4.0/79.3",
      "setting": "联邦图像分类；非 LLM/LoRA；CIFAR-10（60k 样本）、ResNet-18 Light（约 2.7M 参数）；客户端数与 PMR 卡片未说明（同数据集实验为 100 客户端、PMR=20%）",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "Edge-Case 从 42.8/84.3 变为 4.0/79.3（BA 大幅下降但未清零）。"
    },
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "多后门注入（multiple backdoors，第 7.2 节）",
      "evidence_quote": "40 个恶意客户端各注入 4 个后门，论文称仍能完全缓解",
      "setting": "联邦；非 LLM/LoRA；n = 100 客户端、k = 40 恶意客户端；后门数 0/1/2/4/8，对应每个后门由 0/40/20/10/5 个恶意客户端注入；数据集、模型与 PMR 的具体取值卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "BA = 0% ± 0.0%、TPR = 95.2% ± 0.0%、TNR = 100.0% ± 0.0%；40 个恶意客户端各注入 4 个后门时论文称仍能完全缓解。"
    },
    {
      "threat": "T-0008",
      "attack_as_named_in_paper": "constrain-and-scale 的本地训练约束组件（第 2.2、3 节，表 3）",
      "evidence_quote": "或者对训练目标施加约束，使恶意模型在权重空间上更靠近良性模型，例如 constrain-and-scale 攻击",
      "setting": "联邦；非 LLM/LoRA；表 3 覆盖 Reddit 词预测（20.6M 条记录、两层 LSTM 约 20M 参数、80 000 客户端）、CIFAR-10（ResNet-18 Light 约 2.7M 参数、100 客户端、PMR=20%）、IoT-Traffic NIDS（GRU 约 507k 参数、20–200 客户端）；PDR 卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "表 3：三场景 BA 均降为 0（Reddit MA 22.3、CIFAR-10 MA 91.9、IoT-Traffic MA 99.8），相对无防御的 100/22.6、81.9/89.8、100.0/100.0。"
    },
    {
      "threat": "T-0008",
      "attack_as_named_in_paper": "3DFed 的 Constrain Loss（第 10 节、附录 H）",
      "evidence_quote": "Li 等人的 3DFed（论文称其 Constrain Loss 只针对裁剪，没有考虑聚类和加噪）",
      "setting": "联邦；非 LLM/LoRA；附录 H 用 3DFed 官方源码复现，每个实验至少重复 50 次；CIFAR-10（ResNet-18 Light 约 2.7M）、MNIST（CNN 约 431k）、Tiny-ImageNet（ResNet-18 约 11M）；预训练 200/400/600/800 轮；客户端数、PMR、PDR 卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "附录 H：CIFAR-10 预训练 200 轮时 MA 80.8、BA 53.9，400/600/800 轮时 MA 约 86.9–87.0、BA 9.9；MNIST BA 19.1–29.2、MA 约 98.9–99.1；Tiny-ImageNet BA 0.55–0.56、MA 约 61.1–66.8；论文结论为 FLAME 有效缓解了 3DFed。"
    },
    {
      "threat": "T-0010",
      "attack_as_named_in_paper": "constrain-and-scale 的更新放大组件（表 3）",
      "evidence_quote": "constrain-and-scale 攻击下，Reddit 从无防御的 BA 100、MA 22.6 变为 BA 0、MA 22.3",
      "setting": "联邦；非 LLM/LoRA；Reddit 词预测（20.6M 条记录、两层 LSTM 约 20M 参数、80 000 客户端）/ CIFAR-10（ResNet-18 Light 约 2.7M、100 客户端、PMR=20%）/ IoT-Traffic（GRU 约 507k、20–200 客户端）三场景；表 3 未给放大系数",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "表 3：三场景 BA 均降为 0，MA 分别为 22.3 / 91.9 / 99.8。"
    },
    {
      "threat": "T-0010",
      "attack_as_named_in_paper": "PGD（带模型替换，CIFAR-10，表 3）",
      "evidence_quote": "攻击者对训练得到的更新做放大（例如 model-replacement 攻击、带模型替换的 PGD 攻击）以最大化攻击影响",
      "setting": "联邦图像分类；非 LLM/LoRA；CIFAR-10（60k 样本）、ResNet-18 Light（约 2.7M 参数）；客户端数、PMR、模型替换系数卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "CIFAR-10 上 PGD 从 56.1/68.8 变为 0.5/65.1（BA 几乎清零）。"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "模型对齐（model alignment，第 7.2 节、表 5）",
      "evidence_quote": "模型对齐时，聚类几乎完全失效（TPR = 5.68%），但完整 FLAME 仍把 BA 从 100% 降到 0%",
      "setting": "联邦 NIDS；非 LLM/LoRA；IoT-Traffic（65.6M 条记录）、GRU（约 507k 参数）；n = 200 客户端、k = 80 恶意，每个恶意客户端的 PDR 在 5% 到 20% 之间随机",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "表 5：只用模型过滤时 BA 100.0、MA 91.98、TPR 0.0、TNR 33.04；完整 FLAME 下 BA 0.0、MA 100.0、TPR 5.68、TNR 33.33。"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "模型混淆（model obfuscation，第 7.2 节）",
      "evidence_quote": "模型混淆（第 7.2 节，IoT-Traffic）：噪声水平 0.034 时 BA 仍为 0%，MA 为 100%",
      "setting": "联邦 NIDS；非 LLM/LoRA；IoT-Traffic、GRU（约 507k 参数）；混淆噪声水平 0.034；客户端数与 PMR 卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "噪声水平 0.034 时 BA 仍为 0%，MA 为 100%。"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "3DFed（以绕过 FLAME 为目标的攻击框架，附录 H 复现）",
      "evidence_quote": "第 10 节另外反驳了 Xu 等人与 Li 等人（3DFed）的绕过主张，并用 3DFed 官方源码做了复现研究（附录 H）",
      "setting": "联邦；非 LLM/LoRA；附录 H 用 3DFed 官方源码复现（每实验至少重复 50 次）；CIFAR-10 / MNIST / Tiny-ImageNet；客户端数、PMR 卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "CIFAR-10 复现 BA：预训练 200 轮时 53.9%，400/600/800 轮时 9.9%；MNIST BA 19.1–29.2；Tiny-ImageNet BA 0.55–0.56；论文称 FLAME 有效缓解了 3DFed。"
    }
  ],
  "mentioned_only": ["T-0006"],
  "unmatched": [
    {
      "attack": "无目标投毒（untargeted poisoning，附录 F / 表 3）",
      "why": "卡片只说明其目标是\"让模型整体不可用\"，并给出 CIFAR-10 上 MA 从 46.72 恢复到 91.31，但没有说明投毒的实现方式，无法判定它属于 T-0006（破坏本地样本/标签的数据层破坏）还是 T-0016 / T-0011（更新层破坏），故不硬套；若确认是标签翻转一类数据破坏，应改归 T-0006。"
    }
  ]
}
```
