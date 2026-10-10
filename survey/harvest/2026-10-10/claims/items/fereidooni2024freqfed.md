## 1. 论文评测了哪些攻击

按卡片第 3、7、9 节，FreqFed 的实验里**真正跑过**的攻击如下（全部是传统联邦学习场景，无大模型、无 PEFT/LoRA）：

**A. 无目标投毒（拉低主任务）**
1. **Label Flipping**（本地标签翻转，Table II）
2. **Random Updates**（直接发送任意更新，Table II）
3. **Optimized（PGD）**（用投影梯度下降优化投毒目标，Table II；Table III 的 Edge-case 同样是 PGD 版本）

**B. 定向后门——数据投毒路径（本地往训练数据里写触发器/目标）**
4. 单后门与多后门**像素触发器**（Appendix A、Table III）
5. **语义触发器**后门（Appendix A、Table III）
6. **DBA**（Distributed Backdoor Attack）像素模式，以及图上的分布式数据投毒后门（Table III、Table VI）
7. **频率触发器**（把触发器注入数据的频率表示，PDR 10%–100%，Table IX）
8. 说话人验证的**数据投毒后门**（Table V）
9. NIDS 上的 **Mirai Scanning**（Section V-B2）

**C. 定向后门——本地训练/更新构造路径**
10. **constrain-and-scale**（本地目标加规避项 + 上传前约束缩放，Table III、Table V、Table VII、Table XI）
11. **Neurotoxin**（只挑良性客户端不会动的更新坐标，Table IV）
12. **3DFed**（指示机制、自适应调参、诱饵模型，Table III）
13. **Optimized / Edge-case（PGD）**的定向版本（Table III）

**D. 规避与自适应攻击（针对 FreqFed 或针对检测器构造）**
14. **集中式后门攻击**（所有恶意客户端提交相同/近相同模型，Table X）
15. **良性频率注入**（每轮把权重低频 DCT 分量替换为无后门的良性低频分量，Table VIII）
16. **频率域约束损失的自适应攻击**（Known-Benign 与 Unknown-Benign 两种参考模型，Table VII）
17. **Appendix C 的拉格朗日自适应攻击**（10% ≤ PDR ≤ 100%、10% ≤ PMR ≤ 49%）

## 2. 与清单的对应及把握程度

### T-0001 trigger_target_sample_injection —— 把握：高
- 论文中的攻击：像素触发器（单/多后门）、语义触发器、DBA（分布式触发器）、频率触发器、说话人验证数据投毒后门、图分布式数据投毒后门。
- 依据原话：「Section V-B3 iii 的频率触发器、Appendix A 的像素触发器/语义触发器/图节点子图触发器」
- 实验设定：联邦=是；非大模型/非 LoRA；Cifar-10 60.0k + ResNet-18 Light 约 2.7M、TIMIT 201.6k + LSTM 约 12M、PROTEINS 1113 + GraphSage 约 102k；图像域 PDR = 50%、PMR = 30%、iid = 0.9（Table III）；客户端总数 K 与训练轮次 T 论文未说明。
- 边界：DBA 正对清单变体 distributed_trigger；频率触发器是"触发器放在数据频率表示里"的变体。干净标签（clean label）类变体卡片未提及。

### T-0006 untargeted_data_corruption —— 把握：高
- 论文中的攻击：Label Flipping（论文明确放在"无目标攻击"里，目标是拉低 MA，不是定点改判）。
- 依据原话：「无目标攻击为 Label Flipping、Random Updates、Optimized（PGD）」
- 实验设定：联邦=是；非大模型/非 LoRA；Cifar-10 60.0k/ResNet-18 Light 约 2.7M、MNIST 70.0k/CNN 约 431k、EMNIST 814.2k/LeNet 约 66k；PMR = 49%、iid = 0.7（Table II）；K 与 T 论文未说明。
- 边界：对应 label_flipping_data_poisoning；因为是无目标用法，不套 targeted_label_flipping。

### T-0008 malicious_local_objective —— 把握：高（Neurotoxin）／中低（PGD 类）
- 论文中的攻击：**Neurotoxin**（避开重击坐标，正是 heavy_hitter_coordinate_masking）；**Optimized（PGD）/ Edge-case（PGD）**（用 PGD 优化本地投毒目标，含投影步骤与梯度上升性质，但卡片没写它是否针对聚合规则构造，故同时可能属 T-0011）。
- 依据原话：「Neurotoxin 专门挑选良性客户端不太会改动的更新坐标以延长后门寿命」；另一句：「Optimized（PGD）攻击通过投影梯度下降（PGD）优化投毒目标（Table II、Table III 的 Edge-case）」
- 实验设定：联邦=是；非大模型/非 LoRA；Reddit 20.6M 记录 + LSTM 约 20M（PDR = 50%、PMR = 25%，Table IV）；Optimized/Edge-case 见 Table II/III 设置；K 与 T 论文未说明。
- 边界：Mirai Scanning 卡片只写攻击目标，技术手段未说明，见 unmatched。

### T-0010 update_scaling_and_replacement —— 把握：高
- 论文中的攻击：**constrain-and-scale**（本地加约束、提交前对更新做缩放，正对 norm_constrained_update_scaling）。
- 依据原话：「constrain-and-scale 在提交前对更新做约束与缩放」
- 实验设定：联邦=是；非大模型/非 LoRA；Reddit 20.6M + LSTM 约 20M（PDR = 50%、PMR = 25%，Table IV）；Table XI 的 PMR = 25% 覆盖 Reddit、Cifar-10 60.0k、IoT-Traffic 65.6M + GRU 约 507k；K 与 T 论文未说明。
- 边界：卡片没有出现 model replacement 的独立实验，故只算 update_scaling/norm_constrained_update_scaling 这一支。

### T-0011 defense_aware_update_crafting —— 把握：高（显式规避项与自适应攻击）／中（3DFed、PGD 类）
- 论文中的攻击：**频率域规避项版 constrain-and-scale**（Table VII，两种参考模型获取方式）、**良性频率注入**（Table VIII）、**Appendix C 拉格朗日自适应攻击**；**3DFed** 的诱饵模型与自适应调参按语义也属此类（卡片未详述机制，把握中）；Optimized(PGD)/Edge-case(PGD) 若按文献语义（面向聚合规则构造）也落在此项。
- 依据原话：「在损失中加入频率域异常规避项的 constrain-and-scale」
- 实验设定：联邦=是；非大模型/非 LoRA；Cifar-10 60.0k + ResNet-18 Light 约 2.7M（PDR = 50%、PMR = 25%、iid = 0.7、α = 0.7，Table VII）；Table VIII 用 MNIST 70.0k + CNN 约 431k；Appendix C 覆盖 10% ≤ PDR ≤ 100%、10% ≤ PMR ≤ 49%；K 与 T 论文未说明。
- 边界：这是本论文唯一的"针对防御构造"评测；论文报告无一条自适应攻击绕过成功。

### T-0012 collusive_update_cluster —— 把握：高
- 论文中的攻击：**集中式后门攻击**（所有恶意客户端提交完全相同或仅有微小噪声差异的模型）。
- 依据原话：「让所有恶意客户端提交完全相同或仅有微小噪声差异的模型」
- 实验设定：联邦=是；非大模型/非 LoRA；Cifar-10 60.0k + ResNet-18 Light 约 2.7M；iid = 0.0 与 0.1、PMR 最高 49%（Table X）；K 与 T 论文未说明。

### T-0016 simple_update_corruption —— 把握：高
- 论文中的攻击：**Random Updates**（不看防御、直接发任意更新）。
- 依据原话：「Random Updates 直接发送任意更新（Table II）」
- 实验设定：联邦=是；非大模型/非 LoRA；Cifar-10 60.0k/ResNet-18 Light 约 2.7M；PMR = 49%、iid = 0.7（Table II）；K 与 T 论文未说明。

### 其余清单项、mentioned_only 与 unmatched 的说明
- **明确未被评测**（卡片里没有任何实验依据）：T-0002、T-0003、T-0004、T-0005、T-0007、T-0009、T-0013、T-0014、T-0015。原因是本文是传统 FL 的完整权重训练/上传，不涉及 LLM 指令数据、偏好数据、上游数据源、适配器（LoRA/PEFT）、服务器反演，也没有服务器下发构造模型的实验。
- **mentioned_only：空**。卡片中没有"论文只在动机或相关工作里提到、但没做实验"的攻击记录——它点名的攻击都在表格里出现过。两个边界需说明：卡片第 9 节 LoRA 迁移分析里的"触发词越狱、安全对齐破坏"是卡片作者的推测分析，不是论文的实验、也不是论文的相关工作，故不列入；攻击者"可逐轮改变行为"是威胁模型里的能力陈述，清单中无对应项。
- **unmatched**：见下（说话人验证的"模型投毒"、Mirai Scanning）。这两条都只给了攻击名/目标，没给技术手段，按"不硬套"处理。

```json
{
  "key": "fereidooni2024freqfed",
  "evaluated": [
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "像素触发器后门（单后门与多后门像素模式）、语义触发器后门、DBA（Distributed Backdoor Attack）像素模式、频率触发器、说话人验证的数据投毒后门、图上的分布式数据投毒后门（Appendix A、Table III、Table V、Table VI、Table IX）",
      "evidence_quote": "Section V-B3 iii 的频率触发器、Appendix A 的像素触发器/语义触发器/图节点子图触发器",
      "setting": "联邦=是（传统 federated learning），非大模型、非 PEFT/LoRA；Cifar-10 60.0k + ResNet-18 Light 约 2.7M、TIMIT 201.6k + LSTM 约 12M、PROTEINS 1113 + GraphSage 约 102k；图像域 PDR = 50%、PMR = 30%、iid = 0.9（Table III）；客户端总数 K 与训练轮次 T 论文未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "单后门像素模式 BA 100.0/MA 85.5（无防御）对比 BA 0.0/MA 91.9（FreqFed），语义后门 BA 100.0/MA 86.8 对比 BA 0.0/MA 92.0，DBA 像素模式 BA 93.8/MA 57.4 对比 BA 0.4/MA 76.2，图分类上 FreqFed 的 BA 全部为 0.0"
    },
    {
      "threat": "T-0006",
      "attack_as_named_in_paper": "Label Flipping（无目标投毒，Table II）",
      "evidence_quote": "无目标攻击为 Label Flipping、Random Updates、Optimized（PGD）",
      "setting": "联邦=是，非大模型/非 LoRA；Cifar-10 60.0k/ResNet-18 Light 约 2.7M、MNIST 70.0k/CNN 约 431k、EMNIST 814.2k/LeNet 约 66k；PMR = 49%、iid = 0.7（Table II）；K 与 T 论文未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "Label Flipping 下 Cifar-10 从无攻击的 MA 77.3 降到无防御的 35.8，FreqFed 为 77.1；MNIST 98.6 → 50.8 → 97.8；EMNIST 81.3 → 13.4 → 81.2"
    },
    {
      "threat": "T-0008",
      "attack_as_named_in_paper": "Neurotoxin（挑选良性客户端不太会改动的重击坐标）；Optimized（PGD）/ Edge-case（PGD）（用 PGD 优化本地投毒目标，卡片未说明是否针对聚合规则构造，故也可能属 T-0011）",
      "evidence_quote": "Neurotoxin 专门挑选良性客户端不太会改动的更新坐标以延长后门寿命",
      "setting": "联邦=是，非大模型/非 LoRA；Reddit 20.6M 记录 + LSTM 约 20M 参数（PDR = 50%、PMR = 25%，Table IV）；Optimized/Edge-case 见 Table II/III 设置；K 与 T 论文未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "Reddit 上 Neurotoxin 的 BA 100.0/MA 16.2（无防御）对比 BA 0.0/MA 19.8（FreqFed）"
    },
    {
      "threat": "T-0010",
      "attack_as_named_in_paper": "constrain-and-scale（本地加规避项与缩放约束，提交前对更新做约束与缩放）",
      "evidence_quote": "constrain-and-scale 在提交前对更新做约束与缩放",
      "setting": "联邦=是，非大模型/非 LoRA；Reddit 20.6M 记录 + LSTM 约 20M（PDR = 50%、PMR = 25%，Table IV）；Table XI 的 PMR = 25% 覆盖 Reddit、Cifar-10 60.0k、IoT-Traffic 65.6M + GRU 约 507k；K 与 T 论文未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "PMR = 25% 的 constrain-and-scale 下 FreqFed 在 Reddit、Cifar-10、IoT-Traffic 上的 BA 均为 0.0、MA 分别为 22.6、86.5、96.5，是 Table XI 中唯一三处都有效的防御（Krum 在 Reddit 上 BA 仍为 100.0）"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "在损失中加入频率域异常规避项的 constrain-and-scale（Known-Benign 与 Unknown-Benign）、良性频率注入、Appendix C 拉格朗日自适应攻击；3DFed（诱饵模型与自适应调参，卡片未详述，把握中）",
      "evidence_quote": "在损失中加入频率域异常规避项的 constrain-and-scale",
      "setting": "联邦=是，非大模型/非 LoRA；Cifar-10 60.0k + ResNet-18 Light 约 2.7M（PDR = 50%、PMR = 25%、iid = 0.7、α = 0.7，Table VII）；Table VIII 用 MNIST 70.0k + CNN 约 431k（PDR = 50%、PMR = 30%、iid = 0.7）；Appendix C 覆盖 10% ≤ PDR ≤ 100%、10% ≤ PMR ≤ 49%；K 与 T 论文未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "Known-Benign 下 Cifar-10 的 BA 100.0/MA 83.9（无防御）对比 BA 0.0/MA 85.7，Unknown-Benign 下 BA 100.0/MA 84.3 对比 BA 0.0/MA 85.0，Appendix C 的拉格朗日自适应攻击 BA 也均为 0.0"
    },
    {
      "threat": "T-0012",
      "attack_as_named_in_paper": "集中式后门攻击（Concentrated Backdoor Attack，所有恶意客户端提交完全相同或仅有微小噪声差异的模型）",
      "evidence_quote": "让所有恶意客户端提交完全相同或仅有微小噪声差异的模型",
      "setting": "联邦=是，非大模型/非 LoRA；Cifar-10 60.0k + ResNet-18 Light 约 2.7M；iid = 0.0 与 0.1、PMR 最高 49%（Table X）；K 与 T 论文未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "Cifar-10、iid = 0.0 时 PMR 10% 无防御 BA 60.6、FreqFed 为 0.0，PMR 20% 为 81.0 对 0.0，PMR 30%、40%、49% 无防御 BA 100.0、FreqFed 均为 0.0"
    },
    {
      "threat": "T-0016",
      "attack_as_named_in_paper": "Random Updates（直接发送任意更新）",
      "evidence_quote": "Random Updates 直接发送任意更新（Table II）",
      "setting": "联邦=是，非大模型/非 LoRA；Cifar-10 60.0k/ResNet-18 Light 约 2.7M；PMR = 49%、iid = 0.7（Table II）；K 与 T 论文未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "Random Updates 下 Cifar-10 的 MA 77.0 → 31.2 → 77.0（无攻击 → 无防御 → FreqFed）"
    }
  ],
  "mentioned_only": [],
  "unmatched": [
    {
      "attack": "说话人验证中的“模型投毒”（Table V，PMR = 0.49 时无防御 BA 100.0/MA 94.0，FreqFed 下 BA 0.0/MA 94.9）",
      "why": "卡片只给出攻击名称与结果，未说明恶意客户端如何构造投毒模型（改本地训练目标、缩放上传、离线构造还是直接改权重），无法确定它对应清单中的哪一项，故不硬套。"
    },
    {
      "attack": "Mirai Scanning（Section V-B2 的 NIDS 实验：不使用 FreqFed 时 98.5% 的僵尸网络数据包未被检测出，整体 MA 降到 97.6%）",
      "why": "卡片只写“让本地模型学习隐藏 Mirai 僵尸网络流量”，给的是攻击目标而非技术手段；按卡片把它归入“本地训练过程”可暂记为 T-0008，但卡片未说明它改的是本地训练目标、训练数据还是上传更新，故置于 unmatched。"
    }
  ]
}
```
