## 1. 这篇论文的攻击做了什么

论文在联邦参数高效微调（FedPEFT）的指令微调阶段，假设 15 个客户端中有 0–5 个被攻陷。恶意客户端从 BeaverTails 的 `is_safe=False` 子集自造一份有害指令-回答数据，按与诚实客户端完全相同的模板（Eq. 4 的 `Template(cont, inst, resp)`）拼成序列，然后用完全相同的 `ClientOpt`（Eq. 6）和逐 token 负对数似然（Eq. 5）在本地训练，只更新 PEFT 参数、冻结基座权重，最后按协议上传增量 Δθ_{k,t}。服务器用 FedAvg（Eq. 7）把这些更新按样本量加权平均，于是极小比例的有害下降方向被混进全局 PEFT 模块，全局模型在遇到有害指令时不再拒答：ASR 从第 0 轮的不到 4% 升到最高 80%（LoRA 最严重，第 20 轮多数超过 70%；(IA)3 与 LayerNorm 在 40%–60%）。攻击不碰基座模型、不改训练算法、不做任何上传后处理，并且论文强调良性任务（MedQA/MetaMathQA）指标几乎不受影响。论文另外评测了 Median/GeoMed/DnC/ClippedClustering 与 PPSA 两类现成防御，但那属于防御侧，不构成本文的威胁技术。

## 2. 拆成哪几个威胁技术，为什么这样拆

只拆出**一个**威胁技术：`harmful_instruction_data`。理由是卡片里攻击者只有一个入口（本地数据准备）和一类动作（把自己的本地微调数据换成有害指令数据后照常训练、照常上传）：没有更新缩放、投影、拼装，没有替换全局模型，没有控制聚合或下发，也没有多个受控客户端之间的协同。因此不能拆成"数据投毒 + 更新操纵"两条——除数据以外的一切环节都是标准协议本身。防御方评估的四种 RAS 与 PPSA 是干预动作，不是攻击技术；"可训练参数占比极低""良性指标不变"是这条技术在该设置下呈现的隐蔽属性，也不单独成技术。这条技术与具体 PEFT 变体无关（LoRA、(IA)3、LayerNorm 都落在同一个名字下），所以 `variant_of` 留空：它本身就是那个一般做法，而不是某个更一般做法的变体。

## 3. 每个技术需要的能力与改动的制品

需要三种能力。`local_data` 是核心：能自造并替换自己客户端的微调数据。`local_training` 是必需的落地环节：能在自己的客户端上按标准 `ClientOpt` 把有害数据跑成有害的本地更新；注意论文限定不得偏离标准流程，所以这里的"控制"仅限于"用自己的数据跑正常训练"，不含改损失、优化器、学习率、本地步数。`upload_content` 是必需的传播环节：能把训练得到的 Δθ 按协议上传（不含任何缩放、裁剪或拼装）。不需要 `aggregation`/`distribution`（服务器诚实）、`base_model`（基座冻结且不可改）、`collusion`（论文未提协同，各恶意客户端各自采样 BeaverTails）、`defense_knowledge`（无自适应攻击）、`query_access`（无查询）。

改动的制品：`samples` 是直接改动对象；`gradients`、`trace`、`local_update` 是在有害数据上照常训练后必然随之改变的中间制品；`uploads` 是污染进入服务器的载体。`aggregate` 与 `outgoing` 不列入——它们由服务器的 FedAvg 依协议产生，攻击者并不直接改动它们。

## 4. 可能留痕的位置与依据

可写的有五处，另一处是推断。**samples/manifest/sample 与 samples/text/sample**：论文明确写了恶意微调集的来源（BeaverTails 不安全子集）与内容（有害指令-回答、按同一模板拼装），属 reported；但标准 FedPEFT 下原始数据不出本地，服务器看不到，只有客户端侧的数据审计类插件能读。**local_update/factors/module 与 uploads/factor_delta/client**：卡片把上传的 Δθ_{k,t} 称作"服务器唯一能直接看到的攻击痕迹"，也是四种 RAS 的共同作用对象，属 reported；差异在数值层，协议与格式上完全合规，而且论文未说明如何把 LoRA 双矩阵、(IA)3 向量、LayerNorm 缩放参数展平到统一坐标空间。**aggregate/result/model**：论文报告聚合后的全局 PEFT 模块把"顺从有害指令"编码进去（第 0 轮 ASR < 4% → 最高 80%），属 reported，但报告的是行为层差异，良性指标上看不出。**history/features/round**：论文报告恶意客户端退出后 ASR 不回落（Section V-D），说明偏移会跨轮持续，但论文没有测量逐轮特征本身，要靠库自行保存逐轮更新/模型历史才能观测，故记 inferred。samples/loss/sample、trace/scalars/step 等坐标卡片没有报告、机制上也没有把握，不写。

```json
{
  "key": "li2024peftattack",
  "items": [
    {
      "technique_name": "harmful_instruction_data",
      "summary_zh": "被控客户端用自造的有害指令-回答数据替换本地微调数据，照标准 ClientOpt 训练并上传 PEFT 增量，经 FedAvg 聚合后使全局 PEFT 模块失去拒答能力。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data", "local_training", "upload_content"],
      "modifies": ["samples", "gradients", "trace", "local_update", "uploads"],
      "traces": [
        {
          "coordinate": "samples/manifest/sample",
          "basis": "reported",
          "note": "论文写明恶意客户端的微调集来自 BeaverTails 的 is_safe=False 子集，来源、长度与哈希都与良性客户端的 MedQA/MetaMathQA 样本不同；但标准 FedPEFT 下原始数据不出本地，服务器看不到，只有客户端侧数据审计插件能读。"
        },
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "内容是精心构造的有害指令-回答对，按与良性客户端相同的 Template(cont, inst, resp) 拼成序列，覆盖仇恨言论、伤害指导、非法活动等；同样只在客户端本地可见。"
        },
        {
          "coordinate": "local_update/factors/module",
          "basis": "reported",
          "note": "恶意客户端用与诚实客户端相同的 ClientOpt 与逐 token NLL 在有害数据上训练，训练后的本地 PEFT 因子与同轮诚实客户端方向不同；论文没有单独测量该坐标，但它是上传增量 Δθ 的直接来源。"
        },
        {
          "coordinate": "uploads/factor_delta/client",
          "basis": "reported",
          "note": "卡片称上传的 Δθ_{k,t} 是服务器唯一能直接看到的攻击痕迹，也是 Median/GeoMed/DnC/ClippedClustering 的共同作用对象；差异只在数值层，协议与格式完全合规，论文未说明如何把 LoRA 双矩阵、(IA)3 向量与 LayerNorm 缩放参数展平到统一坐标空间。"
        },
        {
          "coordinate": "aggregate/result/model",
          "basis": "reported",
          "note": "聚合后的全局 PEFT 模块把'顺从有害指令'编码进去：第 0 轮 ASR 不到 4%，随轮次升到最高 80%（LoRA 第 20 轮多数超过 70%）；论文报告的是行为层差异，良性任务（MedQA/MetaMathQA）指标上看不出扰动。"
        },
        {
          "coordinate": "history/features/round",
          "basis": "inferred",
          "note": "论文报告恶意客户端退出后 ASR 在后续正常轮次无显著变化（Section V-D），说明该偏移会跨轮持续留在全局模型里；但论文没有测量逐轮特征本身，要观测它需要库额外保存逐轮更新与模型快照。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "刻意保持良性任务表现不受影响，使常规验证数据集与常规指标难以发现（Section III-B）",
        "恶意客户端完全遵守标准 FedPEFT 协议（通信模式与 ClientOpt），不修改冻结的基座权重、不改训练算法，上传的更新在流程与格式上无可指摘（Section III-B）",
        "只靠少数客户端（实验中 0–5/15）与极低的可训练参数比例（Table I：0.001%–0.78%）把有害方向混入聚合结果，避免在良性指标上产生可见扰动（Section III-B、Table I）"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
