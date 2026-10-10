## 1. 论文评测了哪些攻击

按卡片所载，LoMar 的实验里只有两类攻击被真正跑过（其余都只是防御基线或方法动机）：

1. **标签翻转数据投毒（label flipping / data poisoning，定向）**
   - 做法：恶意客户端在本地把源标签样本的标签改成目标标签，翻转比例 τ ∈ [0.1, 1)，其余样本从整个训练集随机抽取。
   - 具体实验：表 3 / 图 4 / 图 5 的 τ、λ 扫描（MNIST 7→1、KDDCup99 11→9、Amazon 15→10、VGGFace2 3→2 与 10→9）；表 4 的多标签翻转（MNIST 同时 1→7、6→9、2→5、0→8）；附录 D 的阈值 ϵ 扫描（MNIST 1→7，100 恶意 + 1,000 干净客户端）。
   - 论文自己明确：这**不是**触发器后门——卡片原文：论文"论文没有触发器（trigger）的概念，因此这不是经典意义上的后门（backdoor），而是'控制特定标签'的定向投毒"。

2. **模型投毒（model poisoning，附录 A）**
   - 做法：按 [5] 的方法在 lp 范数距离度量下生成恶意更新 ûm，再施加显式放大因子，û′m = φ·ûm，实验取 p = 2、φ = 10；该攻击带 stealth metric，论文称其可绕过多数现有防御与服务器端异常检测。
   - 具体实验：图 8（MNIST、VGGFace2，τ ∈ [0.1, 0.4]，λ = 0）与图 9（λ ∈ [0.1, 0.9]，τ = 0.1）。

3. **未评测**：卡片明确"论文没有设计针对 LoMar 的自适应攻击"，也没有评测知道 LoMar 的 k、带宽 h 或阈值 ϵ 的攻击者；同样没有触发器、偏好数据、适配器/任务向量、数据提取类攻击。

## 2. 与清单的对应及把握程度

| 清单条目 | 论文中的攻击 | 把握程度 | 依据与保留意见 |
|---|---|---|---|
| T-0006 untargeted_data_corruption（变体含 `label_flipping_data_poisoning`、`targeted_label_flipping`） | 标签翻转数据投毒（单目标 + 多标签 + τ/λ/ϵ 扫描） | **中高** | 变体名直接命中"标签翻转"；但 T-0006 顶层定义是"无目标、降低模型质量"，本文是"定向控制目标标签"，目标语义不完全一致（论文的定向性来自其自身选择，见卡片引句 2） |
| T-0010 update_scaling_and_replacement（变体含 `norm_constrained_update_scaling`、`update_scaling`） | 模型投毒（附录 A） | **高** | "lp 范数距离度量下生成恶意更新 ûm + 显式放大因子 φ（=10）"就是范数受限的更新放大；与清单描述逐字吻合 |
| T-0011 defense_aware_update_crafting | 同一模型投毒（[5] 的 stealthy 构造） | **中** | 卡片说该更新"基于 FL 聚合规则和攻击目标"构造，且带 stealth metric 以绕过服务器端"合理的异常模型检测策略"，符合"针对聚合规则或检测器构造上传"；但卡片明确论文未做针对 LoMar 的自适应攻击，也未说明攻击者是否知道 LoMar 的规则，且它与 T-0010 是**同一个实验**，属同一攻击的两个技术侧面 |

补充判断：

- **T-0001（触发器目标样本注入）不列入**：卡片明确论文没有触发器概念，标签翻转不涉及"触发器—目标输出成对"的样本注入，不能因为目标是"控制某个标签"就套到 T-0001。
- **其余条目均无依据**：T-0002、T-0003、T-0004、T-0005、T-0007、T-0008、T-0009、T-0012、T-0013、T-0014、T-0015、T-0016 在卡片中找不到"论文实验用了该类攻击"的任何表述；论文的对比对象是 Krum、FoolsGold、Median、FG+Krum 等**防御**以及 No Defense / No Attack 基线，不是这些攻击。模型投毒虽经"上传前放大"，但其构造方式不是本地训练目标（T-0008）、也不是离线适配器（T-0009）。
- **mentioned_only 为空**：按卡片所载，论文在动机/相关工作里没有提到清单中的其他攻击；卡片提到"论文也泛泛讨论了非定向投毒"，但它与已评测的标签翻转同属 T-0006 一族，其未评测性已在 evaluated 的说明中体现。
- **unmatched 为空**：两类被评测的攻击都能在清单中找到条目。唯一可争议处是 T-0006 的顶层定义强调"无目标"，若严格按此解读则定向标签翻转将无处安放；但清单把 `targeted_label_flipping` 明确列为 T-0006 变体，故按变体对应，不另设 unmatched 条目。

```json
{
  "key": "li2022lomar",
  "evaluated": [
    {
      "threat": "T-0006",
      "attack_as_named_in_paper": "label flipping attack（标签翻转数据投毒；含单目标 7→1 等、多标签 1→7/6→9/2→5/0→8、τ∈[0.1,1) 与 λ 扫描、附录 D 阈值 ϵ 扫描）",
      "evidence_quote": "The goal of the label flipping attack is to take control of the target label",
      "setting": "传统跨设备联邦学习（FedAvg），非联邦大模型、无 LoRA/PEFT：MNIST 1,000 客户端×600 样本、KDDCup99 23 客户端、Amazon 50 客户端×150 样本均用一层全连接逻辑回归；VGGFace2 200 客户端用 SqueezeNet；T=200 轮、E=5、批大小 20（表 2 作 8，卡片注明与正文不一致）；恶意客户端 MNIST 100、KDDCup99 3、Amazon 5、VGGFace2 20",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "论文报告 Amazon 标签翻转下 LoMar 把目标标签测试准确率从 FG+Krum 的 96.0% 提到 98.8%、整体平均从 90.1% 提到 97.0%，表 3（λ=0、τ=0.1）MNIST/KDDCup99/Amazon 整体准确率为 0.912/0.971/0.970。"
    },
    {
      "threat": "T-0010",
      "attack_as_named_in_paper": "model poisoning（模型投毒，按 [5] 在 lp 范数距离度量下生成恶意更新并施加放大因子 φ=10）",
      "evidence_quote": "按 [5] 的方法在 lp 范数距离度量下生成恶意更新 ûm，并施加显式放大因子 φ",
      "setting": "传统联邦学习（FedAvg），非联邦大模型、无 LoRA/PEFT：附录 A 在 MNIST 与 VGGFace2 上评测，模型同正文（一层全连接逻辑回归 / SqueezeNet，客户端数 1,000 / 200）；p=2、φ=10，图 8 取 τ∈[0.1,0.4]、λ=0，图 9 取 λ∈[0.1,0.9]、τ=0.1",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "附录 A 图 8 报告 FG+Krum 的目标标签测试准确率从 83.5% 降到 21.4%，而 LoMar 下降更慢，MNIST τ=0.4 时整体 77.2%、目标 63.3%。"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "model poisoning with stealth metric（带 stealth metric 的模型投毒，按 FL 聚合规则与攻击目标构造；非针对 LoMar 的自适应攻击）",
      "evidence_quote": "论文说带 stealth metric 的模型投毒可以绕过多数现有防御（第 1 节、第 2.3 节引 [5]）",
      "setting": "与上一条为同一实验（附录 A，传统 FedAvg，非大模型/LoRA；MNIST 1,000 客户端 / VGGFace2 200 客户端，p=2、φ=10）；卡片未说明攻击者是否知道 LoMar 的 k、带宽 h 或阈值 ϵ",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "论文报告该模型投毒下 LoMar 仍有效：MNIST τ=0.4 时整体 77.2%、目标 63.3%，图 9 中各 λ 下都优于其他方法、λ=0.9 时比 FG+Krum 高 30%。"
    }
  ],
  "mentioned_only": [],
  "unmatched": []
}
```
