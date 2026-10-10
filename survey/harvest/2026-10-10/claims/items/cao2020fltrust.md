## 1. 论文评测了哪些攻击

卡片显示 FLTrust 的实验（Section VI，六个数据集 + 表 III/IV/图 6–7）实际注入并报告了五类攻击，另有一个"被提到但未评测"的自适应攻击相关项。

| 论文中的攻击名 | 攻击做了什么（按卡片） | 目标类型 | 卡片给出的效果数字 |
|---|---|---|---|
| 标签翻转 / label flipping (LF) | 篡改恶意客户端本地训练样本标签："标签 l 变为 M−l−1（M 为类别数）"，特征是保持不变的 | 无目标（抬高测试错误率） | MNIST-0.1 上 FLTrust 错误率 0.04（无攻击 FedAvg 亦为 0.04） |
| Krum 攻击 | "不经过真实训练，直接求解优化问题构造中毒更新"，攻击者按全知识设定知道所有客户端每轮数据、更新与"聚合规则" | 无目标 | MNIST-0.1 上把 Krum 的错误率从 0.10 抬到 0.90；FLTrust 上为 0.04 |
| Trim 攻击 | 同上，直接构造中毒更新 | 无目标 | MNIST-0.5 上把 Trim-mean 与 Median 从 0.06 抬到 0.23 与 0.43；FLTrust 上为 0.06 |
| Scaling 攻击 | 向本地数据追加"带触发器且标签为攻击者目标标签"的样本，并把更新整体放大 λ = n 倍后上传 | 定向（后门），并额外报告攻击成功率 | 对 FedAvg 在 MNIST-0.1 与 MNIST-0.5 攻击成功率均为 1.00；FLTrust 上为 0.03 / 0.00 |
| 自适应攻击（adaptive attack） | 把 Fang 等人的通用本地模型投毒框架代入 FLTrust 聚合规则，用零阶梯度上升求解中毒更新（Algorithm 3，初始化用 Trim，迭代 Q = 10、外层 V = 10） | 无目标 | MNIST-0.1 上 60% 恶意客户端时 FLTrust 错误率仍为 0.04（与无攻击 FedAvg 相同） |

- 统一实验设定（六数据集共用）：**联邦但非大模型**。n = 100 个客户端（HAR 30、CH-MNIST 40），每轮全选（τ = n），R_l = 1，m/n = 20%（m = 20/6/8）；模型为 CNN / ResNet20 / 逻辑回归，数据为 MNIST（60,000/10,000）、Fashion-MNIST（60,000/10,000）、CIFAR-10（50,000/10,000）、HAR（10,299 条、561 维、6 类、30 用户）、CH-MNIST（5,000 张 64×64、取 4,000/1,000）。**卡片未说明**有任何 LLM、Transformer、LoRA 或 PEFT 参与评测。
- 论文同时评测了这些攻击在基线聚合（FedAvg、Krum、Trim-mean、Median）上的表现，以及 FLTrust 的消融版本（NoReLU/NoNorm/withServer 等）。

## 2. 与清单的对应及把握程度

**高把握：**

- **T-0006 untargeted_data_corruption ← 标签翻转 (LF)**。卡片对 LF 的定义（"标签 l 变为 M−l−1"、特征保持不变、目标是抬高测试错误率）与 T-0006"Corrupt labels or contents of local samples…to lower the model's quality"逐字吻合，且明确是实验注入的攻击，不是仅作动机。
- **T-0001 trigger_target_sample_injection ← Scaling 攻击的数据侧**。卡片原话"向本地训练数据追加带触发器（trigger）且标签为攻击者目标标签的样本"就是 T-0001 的定义（pair a trigger in the input with the attacker's target output）；论文还按目标标签报告了攻击成功率，说明这是面向目标输出的注入。
- **T-0010 update_scaling_and_replacement ← Scaling 攻击的上传侧**。Scaling 之所以叫 Scaling，关键动作是"把更新整体放大 λ = n 倍后上传"，正是 T-0010 的 update_scaling；在 FedAvg 上攻击成功率 1.00 也印证了放大是为了在平均中压过良性更新。
- **T-0011 defense_aware_update_crafting ← 自适应攻击**（把握最高）。卡片明确说它"代入 FLTrust 的聚合规则"求解优化问题、假设攻击者知道 ||g₀||、s、cᵢ、e₀、eᵢ 等聚合中间量，即显式针对聚合规则构造更新，对应 T-0011 的 aggregate_deviation_update_crafting / loss_maximizing_update 一系。

**中等把握（需注意口径）：**

- **T-0011 ← Krum 攻击 / Trim 攻击**（推断成分较大）。把二者放进 T-0011 的依据是卡片写的是"直接求解优化问题构造中毒更新…求解后直接发送构造出的中毒更新，不经过真实训练"，符合 T-0011"Compute the upload by optimization against the aggregation rule"的字面描述；卡片也确实写了 Krum/Trim 的全知识设定包含"聚合规则"。但卡片没有说明这些中毒更新的优化目标是"针对 FLTrust 构造"还是"针对 FoolsGold/其他防御构造"，所以严格说它们是在评测既有攻击，而非专门针对 FLTrust 定制的更新。若按最保守口径，这两项也可移入 unmatched（理由：属于既有聚合规则攻击，卡片未给出目标防御的表述）；本文按字面描述归入 T-0011 并在此声明把握程度。
- **T-0012 collusive_update_cluster**：卡片第 9 节把自适应攻击描述为"全知识、可合谋的强攻击者"，但实验只按"恶意客户端比例 m/n"扫描（图 6、图 7），没有给出多客户端协同上传近似更新簇、伪装成多数的明确实验描述，因此**不列入 evaluated**；只有"可合谋"这一处措辞，且不属于清单要求的"用了属于该威胁技术的攻击"。故不写进 mentioned_only（清单要求写论文只在动机/相关工作提到的攻击，这里连该意义下也不算）。

**未出现在清单、也不在评测中的东西：** 论文没有评测任何 LLM/LoRA 场景、没有隐私窃取（反演/提取）、没有投毒根数据集、没有篡改下发模型或上游数据源、没有简单更新破坏（取反/加噪/随机向量）这类对照攻击——因此 **unmatched 为空**（论文评测的攻击都能在清单中找到对应项），也没有需要勉强套用的项。

```json
{
  "key": "cao2020fltrust",
  "evaluated": [
    {
      "threat": "T-0006",
      "attack_as_named_in_paper": "label flipping (LF) attack",
      "evidence_quote": "标签翻转（label flipping, LF）攻击改本地训练样本的标签，标签 l 变为 M−l−1（M 为类别数）",
      "setting": "传统联邦学习（非 LLM、无 LoRA）：n = 100 客户端（HAR 30、CH-MNIST 40），每轮全选，R_l = 1，恶意比例 20%；CNN / ResNet20 / 逻辑回归；MNIST 60,000/10,000、Fashion-MNIST 60,000/10,000、CIFAR-10 50,000/10,000、HAR 10,299 条 561 维 6 类、CH-MNIST 5,000 张 64×64（4,000/1,000）",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "FLTrust 在标签翻转攻击下测试错误率与无攻击 FedAvg 相当，MNIST-0.1 上为 0.04（无攻击 FedAvg 亦为 0.04）"
    },
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "Scaling attack（数据侧：追加带触发器与目标标签的样本）",
      "evidence_quote": "向本地训练数据追加带触发器（trigger）且标签为攻击者目标标签的样本，并把更新整体放大 λ = n 倍（n 为客户端总数）后上传",
      "setting": "传统联邦学习（非 LLM、无 LoRA）：同上六数据集设置；Scaling 攻击额外报告攻击成功率；根数据集 |D₀| = 100 条",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "FLTrust 上 Scaling 攻击成功率在六个数据集上都不超过 0.03（MNIST-0.1 与 MNIST-0.5 为 0.00），而对 FedAvg 在 MNIST-0.1 与 MNIST-0.5 的攻击成功率均为 1.00"
    },
    {
      "threat": "T-0010",
      "attack_as_named_in_paper": "Scaling attack（上传侧：更新整体放大 λ = n）",
      "evidence_quote": "Scaling 攻击把中毒更新乘以远大于 1 的缩放因子 λ（论文设置 λ = n），意图在平均时压过其他客户端",
      "setting": "传统联邦学习（非 LLM、无 LoRA）：同上六数据集设置；服务端聚合为 FedAvg / Krum / Trim-mean / Median / FLTrust 对比",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "Scaling 攻击在 MNIST-0.1 与 MNIST-0.5 上对 FedAvg 的攻击成功率均为 1.00，而对 FLTrust 在六个数据集上不超过 0.03；恶意比例高达 95% 时攻击成功率仍接近 0"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "adaptive attack against FLTrust（基于 Fang 等人通用本地模型投毒框架）",
      "evidence_quote": "把 Fang 等人的通用本地模型投毒框架（Equation 6）代入 FLTrust 的聚合规则，得到以单位向量 e′ᵢ 为变量的优化问题",
      "setting": "传统联邦学习（非 LLM、无 LoRA）：全知识、可合谋攻击者，知道 ||g₀||、s、cᵢ、e₀、eᵢ；零阶梯度上升、初始化用 Trim 攻击、σ² = 0.5、γ = 0.005、η = 0.01、V = Q = 10；六数据集，恶意比例默认 20% 并扫描至 95%",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "FLTrust 在无目标攻击（含自适应攻击）下的测试错误率最多比无攻击 FedAvg 高 0.04；MNIST-0.1 上 60% 恶意客户端时错误率仍为 0.04（与无攻击 FedAvg 相同），论文称最多可容忍 90% 的恶意客户端"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "Krum attack",
      "evidence_quote": "Krum 攻击与 Trim 攻击不经过真实训练，直接求解优化问题构造中毒更新（Section II-B、Equation 6）",
      "setting": "传统联邦学习（非 LLM、无 LoRA）：全知识设定（知道各客户端每轮本地数据、更新与聚合规则）；n = 100，恶意比例 20%，Krum 参数 f 与 Trim-mean 参数 k 都设为 m；六数据集中 MNIST-0.1 等报告该攻击",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "MNIST-0.1 上 Krum 攻击把 Krum 的测试错误率从 0.10 抬到 0.90，而 FLTrust 在 Krum 攻击下错误率为 0.04"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "Trim attack（Trim-mean attack）",
      "evidence_quote": "Krum 攻击与 Trim 攻击不经过真实训练，直接求解优化问题构造中毒更新（Section II-B、Equation 6）",
      "setting": "传统联邦学习（非 LLM、无 LoRA）：全知识设定；n = 100（Trim-mean 参数 k = m = 20），恶意比例 20%；六数据集中 MNIST-0.5 等报告该攻击",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "MNIST-0.5 上 Trim 攻击把 Trim-mean 与 Median 从 0.06 抬到 0.23 与 0.43，而 FLTrust 在该攻击下错误率为 0.06"
    }
  ],
  "mentioned_only": [],
  "unmatched": []
}
```
