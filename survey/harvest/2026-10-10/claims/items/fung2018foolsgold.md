## 1. 论文评测了哪些攻击

**共同实验底座（先说清楚）**：这是**传统联邦学习**（FEDSGD 与 FEDAVG）场景，**不涉及大语言模型、不涉及 PEFT/LoRA**。模型与数据为：MNIST（60,000 条、10 类、784 维、单层 softmax）、VGGFace2（7,380 条、10 类、150,528 维、SqueezeNet1.1 727,000 参数 / VGGNet11 1.28 亿参数）、KDDCup（494,020 条、23 类、41 维、单层 softmax）、Amazon（1,500 条、50 类、10,000 维、单层 softmax）；诚实客户端 10 / 10 / 23 / 50，按类切分为非 IID；MNIST 与 KDDCup 3,000 轮、批大小 50，VGGFace2 500 轮、批大小 8，Amazon 100 轮、批大小 10；κ = 1，每个数据点取 5 次平均（卡片第 1、7 节）。攻击者数量由场景定义：A-1 = 1 个恶意客户端，A-5 = 5 个，A-5x5 = 5 组各 5 个并发攻击，KDDCup 的 A-OnOne = 5 个客户端针对同一目标类，A-99 = 990 个女巫攻击 10 个诚实客户端（卡片第 2 节）。

论文在实验中实际投放的攻击只有**两类数据投毒**加上**四类自适应变体**：

1. **定向标签翻转（label flipping / targeted poisoning）**。在本地数据准备阶段把某一类的诚实样本标签翻成目标类、保留特征。卡片原话：“标签翻转攻击把某一类诚实样本的标签翻成目标类而保留特征”（第 3 节，另见第 2 节）。KDDCup 上的具体形式是“论文假设攻击者把占比约 2% 的恶意流量模式误标为占比约 20% 的"Normal"类”（第 6.1 节）。覆盖 MNIST、VGGFace2、KDDCup、Amazon 四个数据集以及 A-1、A-5、A-5x5、A-OnOne、A-99 全部攻击场景；引出问题的基线见表 1（1 个女巫时数字 1 的准确率 60.7%、攻击成功率 35.9%；2 个女巫时 0.0%、96.2%），防御效果见图 4、图 5、图 7、图 14。

2. **后门（backdoor）**。在本地原始训练数据中加入秘密模式并重新标注，卡片给出触发模式例子：“a random subset of the MNIST training data is marked with a white pixel”（附录 B，完整原话为 “…bottom-right corner of the image, and labelled as a 7”）。后门结果见图 15：随女巫数增加同样被抑制；除该 MNIST 触发例子外，卡片未说明后门还覆盖哪些数据集与模型。

3. **四类自适应规避策略**（第 6.4 节，前两类结果在附录 B）：
   - 把恶意数据与正确数据混合（图 16）；
   - 改变女巫的本地训练批大小（图 17；Amazon A-5、批大小 1 时攻击率 4.76%，论文归因于 10,000 维特征的维度灾难，附录 B）；
   - **智能噪声攻击**：女巫在上传前扰动更新，“一对女巫发送 v1 = a1 + ζ 与 v2 = a2 − ζ，使二者之和不变但余弦相似度降低”（第 6.4 节），图 8 显示指示性特征比例降到 0.1 以下后攻击率接近 0，比例 0.01 会损害训练准确率；
   - **低频自适应投毒（算法 2）**：女巫之间计算历史成对余弦相似度，超过阈值 M 就改发智能噪声、否则发真实投毒更新，从而“rate limit”投毒频率（第 6.4 节）；图 9 显示 M 大于 0.27 时攻击会被检测，M 设为 0.01 时攻击者“would require a minimum of 10 sybils per opposing client”。

4. 此外，论文还把**女巫数量本身**作为攻击强度变量做了系统评测：从 0 到 9 个投毒者（图 5）、5 组各 5 个并发攻击（A-5x5）、990 个女巫对 10 个诚实客户端（A-99，图 10 的 MNIST 基线为训练误差 15.6%、攻击率 0.18%、目标类误差 17.1%），并且图 6 用 SqueezeNet 最终分类层的历史梯度显示“10 个诚实客户端各行差异很大而 5 个女巫各行高度相似”。

论文**没有评测**的攻击：更新幅度放大/模型替换（第 3 节明确“we do not consider these attacks”）、服务器聚合或下发环节的篡改、隐私窃取与梯度反演、偏好数据操纵、安全对齐破坏（卡片第 2、9 节）。

## 2. 与清单的对应及把握程度

| 清单项 | 论文中对应的攻击 | 对应变体 | 把握程度 | 说明 |
|---|---|---|---|---|
| **T-0001** trigger_target_sample_injection | 后门：白像素触发 + 重标为 7 | 与 `clean_label_trigger_sample_injection` 相反（此处是重标注），机制属父类本体 | **高** | 触发模式与目标标签成对注入本地数据，是该威胁的定义性做法；只是发生在联邦客户端本地 |
| **T-0006** untargeted_data_corruption | 定向标签翻转 | `targeted_label_flipping` / `label_flipping_data_poisoning` | **中高** | 机制（改本地样本标签）完全吻合；但父类名强调“无目标地降低模型质量”，本文是定向投毒，需注意这一措辞张力 |
| **T-0011** defense_aware_update_crafting | 智能噪声（成对抵消 ζ）与算法 2 的低频自适应投毒 | 无精确变体，最接近 `decoupled_factor_poisoning` / `synthesized_update_substitution` | **中** | 论文确有“攻击者知道 FoolsGold”的专门实验并按检测器构造上传；但清单强调“匹配良性统计 / 最大化聚合偏移”，本文是“保持和不变、降低成对相似度”，机制不完全等同 |
| **T-0012** collusive_update_cluster | 多女巫并发投毒：A-5、A-5x5、A-OnOne、A-99 | 无变体 | **中偏低** | 多个受控客户端上传高度相似、且 A-99 下构成数量多数，符合“看起来像多数”；但论文的女巫相似性来自共享投毒目标而非主动伪装成良性簇，A-5x5 是 5 个并发攻击而非单一簇。若按“攻击场景而非攻击技术”理解女巫数量，可改判为不列入 |

**mentioned_only（提到但未评测）**：**T-0010** update_scaling_and_replacement。卡片第 3 节明确“论文指出对手的 SGD 更新取值范围无界，但明确‘we do not consider these attacks’，理由是已有基于幅度的检测方法”。

**unmatched（评测了但清单无对应项）**：修改本地批大小的规避策略（附录 B、图 17）——清单中没有以本地训练批大小/训练配置为机制的条目，它也不是改目标函数或优化器（故不能套 T-0008）。“把恶意数据与正确数据混合”（图 16）我**不**单列为 unmatched，因为它是 T-0001 / T-0006 注入攻击的配比型规避变体，机制上仍由上述两项覆盖；同理，A-1 的“单客户端投毒”只是同一攻击在 1 个女巫下的规模，不另立条目。T-0015 也不放进 mentioned_only：论文只在可见性假设里说攻击者看不到其他诚实客户端的数据，并未把它作为一种被提及的攻击。

```json
{
  "key": "fung2018foolsgold",
  "evaluated": [
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "backdoor（后门：在本地训练数据中加入白像素触发模式并重新标注为目标类 7）",
      "evidence_quote": "a random subset of the MNIST training data is marked with a white pixel",
      "setting": "联邦（FEDSGD 与 FEDAVG）；非大模型、非 LoRA/PEFT（单层 softmax 与卷积网络）；后门触发例子为 MNIST（60,000 条、10 类、784 维、单层 softmax），10 个诚实客户端、3,000 轮、批大小 50；后门结果见图 15，随女巫数增加被抑制；除该 MNIST 触发例外，其余数据集与模型卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "论文报告后门攻击在女巫数增加时同样被抑制（图 15），卡片未给数字。"
    },
    {
      "threat": "T-0006",
      "attack_as_named_in_paper": "label flipping / targeted poisoning（定向标签翻转；KDDCup 上把约 2% 的恶意流量模式误标为约 20% 的 Normal 类）",
      "evidence_quote": "标签翻转攻击把某一类诚实样本的标签翻成目标类而保留特征",
      "setting": "联邦（FEDSGD 与 FEDAVG）；非大模型、非 LoRA/PEFT；MNIST（60,000 条/10 类/784 维/单层 softmax）、VGGFace2（7,380 条/10 类/150,528 维/SqueezeNet1.1 727,000 参数与 VGGNet11 1.28 亿参数）、KDDCup（494,020 条/23 类/41 维/单层 softmax）、Amazon（1,500 条/50 类/10,000 维/单层 softmax）；诚实客户端 10/10/23/50，按类切分非 IID；攻击场景 A-1、A-5、A-5x5、A-OnOne、A-99；MNIST 与 KDDCup 3,000 轮、批大小 50，VGGFace2 500 轮、批大小 8，Amazon 100 轮、批大小 10；κ=1，5 次平均",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "论文报告 FoolsGold 在多数攻击（含 A-OnOne 与 A-99）下有效阻止攻击并保持高准确率，仅在单客户端 A-1 上表现最差；图 5 称“FoolsGold remains robust even with 9 attackers”，图 7 中 MNIST 与 VGGFace2 的最大攻击率 less than 1%（格子数值分别为 0.002 至 0.003 与 0.000 至 0.012），图 14 中 A-5 在 MNIST 所有源类与目标类组合上最高攻击率为 0.02；作为对照，表 1 中 1 个女巫时数字 1 准确率 60.7%、攻击成功率 35.9%，2 个女巫时 0.0%、96.2%。"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "智能噪声攻击（一对女巫发送成对抵消的 ζ）与自适应算法 2（按女巫间历史余弦相似度决定发噪声还是发投毒更新）",
      "evidence_quote": "一对女巫发送 v1 = a1 + ζ 与 v2 = a2 − ζ，使二者之和不变但余弦相似度降低",
      "setting": "联邦（FEDSGD 与 FEDAVG）；非大模型、非 LoRA/PEFT；第 6.4 节“攻击者知道 FoolsGold”的专门实验，模型与数据集为卡片所列 MNIST、VGGFace2、KDDCup、Amazon 与对应单层 softmax/卷积网络，诚实客户端 10/10/23/50；自适应算法 2 额外赋予攻击者本地计算女巫之间成对余弦相似度的能力；其余细节卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "论文报告智能噪声攻击在指示性特征比例降到 0.1 以下后攻击率接近 0，但比例过低（0.01）会损害训练准确率；算法 2 在阈值 M 大于 0.27 时攻击会被检测，M 设为 0.01 时攻击者“would require a minimum of 10 sybils per opposing client”，即需足够多女巫与足够低阈值才能颠覆防御。"
    },
    {
      "threat": "T-0012",
      "attack_as_named_in_paper": "sybil 并发投毒（A-5 的 5 个恶意客户端、A-5x5 的 5 组各 5 个并发攻击、A-OnOne 的 5 个客户端针对同一目标类、A-99 的 990 个女巫攻击 10 个诚实客户端）",
      "evidence_quote": "A-99 为 990 个女巫攻击 10 个诚实客户端",
      "setting": "联邦（FEDSGD 与 FEDAVG）；非大模型、非 LoRA/PEFT；诚实客户端 10（MNIST、VGGFace2）、23（KDDCup）、50（Amazon）；女巫数为 1、5、5×5、990；论文威胁模型称女巫可以“collude by sharing state among themselves and by sending updates in an intelligent, coordinated fashion”，图 6 显示 5 个女巫在最终分类层的历史梯度各行高度相似；MNIST 与 KDDCup 3,000 轮、批大小 50，VGGFace2 500 轮、批大小 8，Amazon 100 轮、批大小 10",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "论文报告随投毒者数量从 0 增加到 9，基线联邦学习与 Multi-Krum 的攻击率迅速上升，而 FoolsGold 在 FEDSGD 与 FEDAVG 下都保持稳健，论文称“FoolsGold remains robust even with 9 attackers”；A-99 的 MNIST 基线为训练误差 15.6%、攻击率 0.18%、目标类误差 17.1%（图 10）。"
    }
  ],
  "mentioned_only": ["T-0010"],
  "unmatched": [
    {
      "attack": "修改女巫本地训练批大小（附录 B、图 17；Amazon A-5 批大小 1 时攻击率 4.76%）",
      "why": "清单以数据投毒机制、更新构造、合谋与服务器侧攻防为分类轴，没有以本地训练批大小/训练配置为机制的条目；它既不是改目标函数或优化器（不能套 T-0008），也不改变投毒数据的构造（仍属 T-0001/T-0006 的规避性超参数调节），故不硬套任何条目。"
    }
  ]
}
```
