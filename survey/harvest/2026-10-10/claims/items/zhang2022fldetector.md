## 1. 论文评测了哪些攻击

卡片第 7 节（实验设置）明确写出实验评测的四种攻击：**无目标模型投毒攻击、Scaling Attack、DBA、A Little is Enough Attack**；第 4.5 节与第 5.2 节（图 4(a)）另外评测了一个**针对检测器本身的自适应攻击**（把 Scaling Attack 按公式 6 自适应化）。逐一说明：

1. **无目标模型投毒攻击（untargeted model poisoning，Fang 等人的优化框架）**：恶意客户端直接在客户端侧求解优化问题得到最优伪造更新，并替换上传的更新向量，目标是让全局模型对大量测试输入误判（第 2.1 节、第 3 节）。评测覆盖 MNIST / CIFAR10 / FEMNIST 与多种聚合规则（表 3、4、5，图 1）。
2. **Scaling Attack**：数据侧在恶意客户端上复制本地样本、把触发器嵌入复制出的输入并赋攻击者选定标签，在上报前把更新按因子放大（缩放因子 100），目标标签固定为"0"（第 2.1、5.1 节）。它是本文四个主攻击之一（表 2、3、5、6）。
3. **DBA（Distributed Backdoor Attack）**：把触发器分解为独立的局部模式、分别嵌入不同恶意客户端组（默认 28% 恶意比例就是为了把触发器均分四份、嵌入四组）（第 2.1、5.1 节）。同为四个主攻击之一。
4. **A Little is Enough Attack**：更新先按 Scaling Attack 方式计算，再裁剪到特定范围以规避拜占庭鲁棒聚合（第 2.1 节）。同为四个主攻击之一。
5. **自适应攻击（第 4.5 节公式 6 对应的小节）**：攻击者知道 FLDetector 被使用时，在原攻击损失上加正则项以规避检测；论文只把 Scaling Attack 自适应化（第 5.2 节明确说明），在图 4(a)（CIFAR10、Median、非 iid 0.5、28 个恶意客户端）上报告结果。

**不算作实验评测的**：定理 1 中"恶意客户端每轮把真实更新反号（发送 −g_i^t）"只是理论分析假设（第 4.4 节），卡片没有说实验中单独评测了这种反号/简单破坏更新；周期性攻击（图 3）只是同一无目标攻击的时间调度，不是新的攻击技术。

论文完全不涉及大模型、PEFT/LoRA 与数据侧对齐破坏，也不涉及隐私窃取（第 1、2 节场景为传统 FL 图像分类）。

## 2. 与清单的对应及把握程度

| 清单条目 | 论文中的攻击名 | 把握 | 对应理由 |
|---|---|---|---|
| T-0001（含变体 distributed_trigger） | Scaling Attack | 高 | 触发器 + 攻击者选定标签注入本地训练数据；清单 T-0001 即"触发器与目标输出成对的样本注入" |
| T-0001（变体 distributed_trigger） | DBA | 高 | 清单 T-0001 变体里直接列有 distributed_trigger，与"把触发器拆成局部模式分给不同恶意客户端"逐字对应 |
| T-0010（变体 update_scaling） | Scaling Attack（放大上传部分） | 高 | 同一个攻击在上传侧按因子 100 放大更新，即"Scale the upload so that it survives or dominates averaging" |
| T-0011（变体 benign_statistics_update_masquerade / inside the benign spread） | A Little is Enough Attack | 高 | "裁剪使其落入特定范围以绕过鲁棒聚合"正是清单所说"inside the benign spread / matching benign statistics" |
| T-0011（变体 loss_maximizing_update / aggregate_deviation_update_crafting） | 无目标模型投毒攻击（Fang 等人框架） | 中 | 论文写的是"求解优化问题、得到最优伪造更新并替换上传"，最贴合 T-0011"以优化构造上传、对抗聚合规则、最大化聚合偏差"；备选解读是 T-0008 的 gradient_ascent_local_training，但卡片只写了替换上传的更新向量，未写本地训练目标被改，故未采用 T-0008 |
| T-0011（针对检测器构造更新） | 自适应攻击（公式 6） | 高 | 清单 T-0011 定义含"optimization against the aggregation rule **or the detector**"，论文的 λ 正则项就是针对 FLDetector 优化 |

其他说明：

- **T-0001 与 T-0010 是同一攻击的两面**：论文的 Scaling Attack 同时包含"注入带触发器的样本"（T-0001）与"放大上传更新"（T-0010），因此拆成两条；若只按攻击名去重，应合并为一条 T-0001 + 一条 T-0010。
- **T-0011 命中三次**（无目标优化投毒、A Little is Enough、自适应攻击），它们是三个不同的被测攻击/变体，故分列三条。
- **mentioned_only 只有 T-0016**：清单 T-0016 的"negated update"与定理 1 的"恶意客户端每轮把真实更新反号"逐字对应，但它只出现在理论假设（第 4.4 节）中，卡片未说明实验单独评测了该攻击。
- **完全无依据的条目**：T-0002、T-0003、T-0004、T-0005、T-0006、T-0007、T-0008（仅备选解读，未采纳）、T-0009、T-0012、T-0013、T-0014、T-0015 在卡片中均无任何实验依据（论文是经典 FL 图像分类防御，不涉及 LLM/LoRA、偏好数据、上游数据源、离线适配器、合谋簇、梯度反演与构造下发模型）。
- **unmatched 为空**：四种主攻击加自适应攻击都能在清单中找到对应项，没有需要另立的攻击。
- **一个防御侧事实易被误读**：表 6 中 FedAvg 下 ASR 仍高达 98.2/99.6，这是"检测后仍由非鲁棒聚合兜底"的防御局限，不是新的威胁技术。

```json
{
  "key": "zhang2022fldetector",
  "evaluated": [
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "Scaling Attack",
      "evidence_quote": "把触发器嵌入复制出的输入，并赋予攻击者选定的标签",
      "setting": "联邦（传统 FL，非 LLM/LoRA）；MNIST 与 CIFAR10 各 100 客户端、FEMNIST 300 客户端，默认 28% 为恶意（28/28/84 个）；MNIST 与 FEMNIST 用四层 CNN、CIFAR10 用 ResNet20；聚合 FedAvg/Krum/Trimmed-Mean/Median；MNIST 1000 轮、CIFAR10 与 FEMNIST 2000 轮；非 iid 程度 0.5；每轮全部客户端参与；为第 5.1 节所列四种评测攻击之一",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "部署 FLDetector 后 Scaling Attack 的 ASR 从 CIFAR10 的 91.2% 降到 2.4%、从 FEMNIST 的 57.9% 降到 1.7%，TACC 分别为 66.6→65.7 与 66.4→64.5（表 3），FEMNIST FedAvg 下 DACC 0.85 / FPR 0.20 / FNR 0.00（表 2）。"
    },
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "DBA (Distributed Backdoor Attack)",
      "evidence_quote": "把多个恶意客户端拆成若干组、每组嵌入触发器的一个局部模式",
      "setting": "联邦（传统 FL，非 LLM/LoRA）；MNIST 与 CIFAR10 各 100 客户端、FEMNIST 300 客户端，默认 28% 为恶意（28/28/84 个），因 DBA 需把触发器均分四份嵌入四组；CNN（MNIST/FEMNIST）与 ResNet20（CIFAR10）；FedAvg/Krum/Trimmed-Mean/Median；1000–2000 轮；非 iid 0.5；每轮全参与；为四种评测攻击之一",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "部署 FLDetector 后 DBA 的 ASR 从 CIFAR10 的 93.5% 降到 1.9%、从 FEMNIST 的 53.2% 降到 2.1%（TACC 66.1→65.2、67.5→64.3），FEMNIST FedAvg 下 DACC 0.92 / FPR 0.11 / FNR 0.00。"
    },
    {
      "threat": "T-0010",
      "attack_as_named_in_paper": "Scaling Attack（上传前按因子放大更新）",
      "evidence_quote": "在上报前把更新按因子放大（第 2.1 节；第 5.1 节说明缩放因子设为 100",
      "setting": "联邦（传统 FL，非 LLM/LoRA）；MNIST、CIFAR10 各 100 客户端、FEMNIST 300 客户端；28% 恶意；CNN 与 ResNet20；FedAvg/Krum/Trimmed-Mean/Median；1000–2000 轮；缩放因子 100；非 iid 0.5；每轮全参与；与上一条为同一攻击的不同侧面",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "同一攻击被检测并移除后 CIFAR10 上 TACC/ASR 由 66.6 / 91.2 变为 65.7 / 2.4（表 3）；但表 6 显示 MNIST 的 FedAvg 下 ASR 仍为 98.2 / 99.6，Krum、Trimmed-Mean、Median 下大多降到 0.3% 到 0.9%。"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "A Little is Enough Attack",
      "evidence_quote": "对更新做裁剪使其落入特定范围以绕过鲁棒聚合",
      "setting": "联邦（传统 FL，非 LLM/LoRA）；MNIST、CIFAR10 各 100 客户端、FEMNIST 300 客户端；28% 恶意；CNN 与 ResNet20；FedAvg/Krum/Trimmed-Mean/Median；1000–2000 轮；非 iid 0.5；每轮全参与；为四种评测攻击之一",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "部署 FLDetector 后该攻击的 ASR 从 CIFAR10 的 95.2% 降到 1.8%（TACC 62.1→64.3）、从 FEMNIST 的 59.6% 降到 1.6%（66.7→65.0）；CIFAR10 + Median 下 DACC 0.87 / FPR 0.15 / FNR 0.07，并漏检 2 个恶意客户端。"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "无目标模型投毒攻击（untargeted model poisoning attack，Fang 等人的优化框架）",
      "evidence_quote": "把无目标攻击建模为优化问题、求取最优伪造更新（第 2.1 节，Fang 等人的框架）",
      "setting": "联邦（传统 FL，非 LLM/LoRA）；MNIST、CIFAR10 各 100 客户端、FEMNIST 300 客户端；28% 恶意；CNN 与 ResNet20；FedAvg/Krum/Trimmed-Mean/Median；1000–2000 轮；非 iid 0.5（图 1 另测恶意客户端数的影响）；每轮全参与；为四种评测攻击之一",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "MNIST 上无目标攻击把 TACC 从 97.6% 压到 69.5%，部署 FLDetector 后恢复到 97.4%（FedAvg 下 DACC 0.87 / FPR 0.18 / FNR 0.00）；CIFAR10 由 65.8→27.8 恢复到 65.9，FEMNIST 由 64.4→14.3 恢复到 63.2。"
    },
    {
      "threat": "T-0011",
      "attack_as_named_in_paper": "针对 FLDetector 的自适应攻击（第 4.5 节公式 6）",
      "evidence_quote": "攻击者若知道 FLDetector 被使用，可在原攻击损失上加入正则项",
      "setting": "联邦（传统 FL，非 LLM/LoRA）；CIFAR10、100 客户端、28 个恶意客户端、ResNet20、Median 聚合、非 iid 程度 0.5；把 Scaling Attack 自适应化（第 5.2 节明确说明只做了这一种）；每轮全参与",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "图 4(a) 报告 DACC 随 λ 减小而下降，但 ASR 仍然很低，因为恶意客户端在试图规避检测时本地更新也变得不那么有效；卡片未给数字。"
    }
  ],
  "mentioned_only": ["T-0016"],
  "unmatched": []
}
```
