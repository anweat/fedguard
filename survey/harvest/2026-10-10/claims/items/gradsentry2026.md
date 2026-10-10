## 1. 论文评测了哪些攻击

论文是**集中式 SFT、数据侧、训练前逐样本过滤**的防御，它评测的攻击只有一类：**往训练数据里注入"触发器 → 攻击者指定目标输出"配对的投毒样本**（定向后门）。具体有 5 组：

- **BadNets（BN）**：在 Question 中插入稀有词（"cf"、"mn"、"bb"、"tq"）。
- **AddSent（AS）**：插入句子 "I watched this 3D movie last weekend"。
- **CBA**：在多个输入组件同时插入不同触发词（WebQA/FreebaseQA 为 Instruction 与 Question，NQ/CoQA 为 Context 与 Question）。
- **StyleBkd（SB）**：用 Bible 风格做整句风格迁移。
- **自适应攻击（Appendix J）**：一个白盒"梯度稀释攻击"，攻击者知道检测机制（SVD 梯度熵）、阈值方法（KDE 谷值）与目标参数（lm_head.weight），在输入侧做上下文增强、输出侧把合法回答前缀混入恶意输出。

评测口径：四种攻击的目标输出统一为固定的误导性回答"， and click ⟨malicious_url⟩for more information"；默认模型 Llama-2-7B + LoRA rank 4、3 epochs、学习率 2×10⁻⁵、H800，另有 Vicuna-7B-v1.5、Qwen2.5-7B-Instruct、Pythia-6.9B、Mistral-7B-Instruct-v0.3、GPT-J-6B、GLM-4-9B 与全参数微调（Appendix F）；数据为 WebQA/FreebaseQA/CoQA/NQ；默认投毒率 0.1，投毒率覆盖 1%–90%，样本量覆盖 20–5k。论文不含任何联邦、聚合、客户端/服务器环节。

## 2. 与清单的对应及把握程度

**对应情况：**

- 四种投毒构造 + 梯度稀释自适应攻击全部落在 **T-0001 trigger_target_sample_injection**（"把输入带触发器、输出为攻击者目标输出的样本放进本地数据"）。这是清单里唯一与之匹配的条目，且匹配度很高：论文的每条投毒样本都是"触发器 → 固定目标回答"的成对样本。
- 其中 **CBA** 额外对得上 T-0001 的变体 **instruction_field_poisoning_targeted_label**（触发词插入 Instruction 字段）；**StyleBkd** 额外对得上变体 **style_transfer_trigger_sample_injection**（整句风格迁移作为触发器）。为免把同一威胁技术重复计数，我仍按一个 T-0001 处理，但在 `attack_as_named_in_paper` 中保留论文自己的名字。
- **梯度稀释攻击**同样属于 T-0001 的范畴（它改变的仍是投毒样本本身），因此没有单独成项，而是并入 T-0001 的评测证据。

**把握程度：**

- BadNets / AddSent / CBA / StyleBkd → T-0001：**高**。卡片明确写出了触发器的插入位置、插入内容与统一目标输出，属于"实验实际使用"。
- 梯度稀释攻击 → T-0001：**中高**。卡片对其实验设定、λ、投毒率、结果都有明确记录；只是它同时带有"针对防御构造"的色彩，而清单的 T-0011 是更新/聚合层面的构造，位置不同，故不并入 T-0011。
- 卡片中**找不到**其他威胁技术的实验依据：论文威胁模型只有"被攻陷的数据来源"，没有恶意客户端、恶意服务器、偏好数据操纵、上游数据源篡改、更新放大、合谋或隐私提取的实验。

**matched（进 evaluated）**：T-0001（三种表述：BadNets/AddSent、CBA、StyleBkd、梯度稀释）。
**mentioned_only**：卡片里能验证"只是 T-0001 这一威胁技术的其他变体、未做对应实验"的项（clean_label 式注入、concept 式触发器）；其余清单条目在卡片中没有可验证的提及依据，故既不入 evaluated 也不硬塞进 mentioned_only。
**unmatched**：梯度稀释攻击——清单里没有"白盒、按防御检测器的统计量（谱熵/KDE 阈值）来增广投毒样本"这一类条目。

```json
{
  "key": "gradsentry2026",
  "evaluated": [
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "BadNets（BN）+ AddSent（AS）：稀有词触发器与插入句触发器，配对统一的误导性目标输出",
      "evidence_quote": "BadNets（BN）在 Question 中插入稀有词（\"cf\"、\"mn\"、\"bb\"、\"tq\"）；AddSent（AS）插入句子\"I watched this 3D movie last weekend\"",
      "setting": "集中式 SFT（无联邦、无客户端/聚合）、训练前逐样本过滤；默认 Llama-2-7B + LoRA rank 4、3 epochs、lr 2e-5、H800，另测 Vicuna-7B-v1.5/Qwen2.5-7B-Instruct/Pythia-6.9B/Mistral-7B-Instruct-v0.3/GPT-J-6B/GLM-4-9B 及全参数微调；WebQA(3401/377/400)、FreebaseQA(5000/400/2000)、CoQA(5000/400/2000)、NQ(5000/400/498)，默认投毒率 0.1，投毒率覆盖 1%–90%，样本量 20–5k",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "16 个设置把 ASR 降到 0.00%（无防御 Vanilla 最高 99.50%），样本识别在全部设置 Recall = 100.00%，FreebaseQA/CoQA/NQ 的 F1 为 99.60%–99.90%、WebQA 为 69.74%–73.43%，过滤耗时如 NQ-BN 147 秒（CUBE 679、GraCeFul 402）"
    },
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "CBA（instruction_field_poisoning_targeted_label 式构造）：在 Instruction 与 Question（WebQA/FreebaseQA）或 Context 与 Question（NQ/CoQA）同时插入不同触发词",
      "evidence_quote": "CBA 在不同输入组件同时插入不同触发词（WebQA/FreebaseQA 插入 Instruction 与 Question，NQ/CoQA 插入 Context 与 Question）",
      "setting": "同上：集中式 SFT + 训练前逐样本过滤（无联邦）；Llama-2-7B + LoRA rank 4 为默认，另含全参数微调（表 6）与多种 6B–9B 模型；四个 QA 数据集，默认投毒率 0.1；图 3 中 WebQA 的 CBA 设置为 Clean n=3451、Poison n=340",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "ASR 全部降到 0.00%，Recall 全部 100.00%；WebQA-CBA 的 ACC 为 42.57，而 ONION 与 CleanGen 均为 29.38"
    },
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "StyleBkd（SB，style_transfer_trigger_sample_injection 式构造）：用 Bible 风格对整句做风格迁移作为触发器",
      "evidence_quote": "StyleBkd（SB）用 Bible 风格做整句风格迁移。所有攻击的目标输出都是固定的误导性回答",
      "setting": "同上：集中式 SFT + 训练前逐样本过滤（无联邦）；默认 Llama-2-7B + LoRA rank 4、投毒率 0.1，四数据集 × 四攻击共 16 个端到端设置；图 3 中 WebQA 的 SB 为 Clean n=3061、Poison n=340",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "ASR 全部为 0.00%；无防御 Vanilla 在 FreebaseQA-SB 的 ASR 最高达 99.50%，WebQA 各攻击 ASR 为 49.75%–99.02%"
    },
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "自适应攻击：白盒梯度稀释攻击（Gradient Dilution Attack），输入侧上下文增强 + 输出侧合法回答前缀混合",
      "evidence_quote": "自适应攻击下攻击者额外能做输入侧的上下文增强（前置任务相关句子）与输出侧混合（把合法回答前缀拼到恶意输出前）",
      "setting": "同上：集中式 SFT（无联邦）；Llama-2-7B + LoRA，四个 QA 数据集，投毒率 10%，λ∈{0.5, 0.7}；攻击者白盒知道检测机制、KDE 谷值阈值方法与目标参数 lm_head.weight",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "λ=0.5 与 0.7、投毒率 10% 下仍为 100.00% Recall，ASR 全为 0.00%（ACC 为 38.01–72.20）"
    }
  ],
  "mentioned_only": [
    "T-0001"
  ],
  "unmatched": [
    {
      "attack": "梯度稀释攻击（Gradient Dilution Attack，Appendix J）",
      "why": "它是以数据侧投毒样本为载体、针对检测器统计量（lm_head 梯度谱熵与 KDE 谷值阈值）构造的白盒自适应攻击，清单里没有对应条目：T-0011 是服务器/聚合层面的更新构造，T-0006 是无目标破坏，均不匹配；卡片也未提及任何清单中的其他攻击"
    }
  ]
}
```
