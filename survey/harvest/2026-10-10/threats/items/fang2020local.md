## 1. 这篇论文的攻击做了什么

论文在传统联邦学习里（服务器按 Krum/Bulyan/trimmed mean/median 聚合**完整模型参数**、能看到每个客户端的明文上传、被攻陷客户端少于 50%），让被攻陷客户端在每轮"本地训练完成、上传之前"把要上传的本地模型参数整体替换成一个求解优化问题得到的伪造模型：最大化 `s^T(w − w')`，其中 `s` 是无攻击时全局模型各参数的变化方向，`w`/`w'` 分别是无攻击/有攻击时的聚合结果。也就是把聚合结果尽量推向"无攻击时更新方向的反方向"（directed deviation），多轮累积后把测试错误率推高（MNIST+LR+Krum 从 0.14 升到 0.72/0.80），属于**无目标投毒 / 拒绝服务**；论文明确不投毒数据、不改数据收集阶段，也不做定向投毒。按聚合规则有三套实例化：Krum 构造单个定向偏移模型（`w'_1 = w_Re − λs`）并用二分搜索取最大 λ、其余 c−1 个伪造模型贴着它采样；trimmed mean/median 逐参数把伪造值推到良性最大/最小值之外；Bulyan 靠迁移。论文自己提出的 ERR/LFR 是**防御**，不写成威胁技术；Gaussian、label flipping、BGA 是对比攻击，也不是本文的技术。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个：

1. **`aggregate_deviation_update_crafting`**——直接构造并上传一份伪造的本地更新，让聚合结果朝无攻击方向的反方向偏移（逐参数越过良性极值 / 取 `w_Re − λs`）。
2. **`collusive_update_cluster`**——多个受控客户端协同，围绕同一个伪造点上传一簇彼此距离 ≤ ε 的近重复更新，操纵 Krum/Bulyan 的**基于距离的选择**。

这样拆的理由是两者的能力画像和操纵对象都不同：第二个必须有多客户端协同（`collusion`），第一个不需要；第一个操纵的是**逐参数的坐标级统计量**（trimmed mean/median 的极值），第二个操纵的是**模型空间的距离/选择结构**。二者在 Krum/Bulyan 下被联合使用，在 trimmed mean/median 下只用第一个。

不拆出去的：ε 采样、越界幅度限制是**规避检测的措施**（写进 `stealth_measures`）；全知识/部分知识、知道/不知道聚合规则、换聚合规则（Krum→trimmed mean/median/Bulyan）只是同一技术在不同信息条件与规则下的实例，不构成新的"目标—能力—制品"组合，所以没有第三、第四个技术。

## 3. 每个技术需要的能力与改动的制品

| technique_name | capabilities | modifies |
| --- | --- | --- |
| aggregate_deviation_update_crafting | upload_content, defense_knowledge | local_update, uploads |
| collusive_update_cluster | upload_content, collusion, defense_knowledge | local_update, uploads |

两个技术都**不需要** `local_data` 或 `local_training`：论文明确攻击的是学习过程的上传环节，数据与训练本身保持诚实，攻击者只是把训练出来的本地模型参数换成构造值。知识维度记 `defense_knowledge`，因为论文主设定是攻击者知道聚合规则（含 Krum 需要的上界 c、trimmed mean 的 β 等参数）；论文另测的"不知道聚合规则、按某个假定规则构造再依赖迁移性"相当于同一技术去掉这一能力，不另立技术。改动的制品只有 `local_update`（上传前的本地 LoRA 因子）与 `uploads`（上传内容），在联邦 LoRA 微调里的自然对应是"客户端在合并/上传前把 LoRA 因子替换为构造值"，不触碰 `aggregate`、`outgoing`、`received` 或 `samples`。

## 4. 可能留痕的位置与依据

- `local_update/factors/module`：**reported**（两个技术）。第一个技术留下的伪造因子取值分布异常（trimmed mean/median 下逐参数被推到良性极值之外，只是被限制在 `[wmax, 2·wmax]` 或 `µ±3σ–4σ`）；第二个技术留下 c 个因子彼此距离 ≤ ε（默认 0.01）的紧密聚簇，论文自己承认 ε=0 会因完全相同而被服务器轻易检出。
- `uploads/factor_delta/client`：**reported**（第一个技术）。上传相对下发全局因子的差按构造与 `s` 反号，幅度由二分搜索得到的 λ 或越界偏移量决定。
- `aggregate/weights/client`：**reported**（第二个技术）。论文以"Krum 每轮选中被伪造的 `w'_1`"为构造约束（Equation 2、Theorem 1），Bulyan 下同一构造迁移进 θ 个被选模型。
- `aggregate/result/model`：**reported**（两个技术）。论文报告聚合后全局模型被推向反方向、错误率显著上升（Krum 0.14→0.72/0.80，Bulyan 0.14→0.36/0.38，DNN 上 0.11→0.75/0.77）。
- `history/features/round`：**inferred**（第一个技术）。偏移是逐轮累积的（论文报告投毒轮次比例越高错误率越大），因此逐轮全局因子轨迹应呈反向漂移；但论文没有把逐轮回特征本身作为观测量报告，所以标 inferred。

不写的：`samples/*`（论文明确不投毒数据，入口是学习过程而非数据收集）；`received/*`、`outgoing/*`、`channel/*`（攻击不触碰下发内容与通道消息）；`uploads/product_delta/client`（论文在完整参数向量上逐元素操作，LoRA 低秩乘积上的语义论文未说明，属于分析而非卡片内容）；`trace/scalars/step`（论文报告攻击下训练错误率仍正常下降到收敛，是"没有差异"，不作为痕迹收录）。

```json
{
  "key": "fang2020local",
  "items": [
    {
      "technique_name": "aggregate_deviation_update_crafting",
      "summary_zh": "被攻陷客户端不上传诚实训练得到的本地更新，而是求解优化问题直接构造一份伪造的本地 LoRA 因子，让聚合结果尽量朝无攻击时更新方向的反方向偏移（trimmed mean/median 下逐参数推到良性极值之外，Krum 下取 w_Re − λs）。",
      "goal": ["untargeted"],
      "capabilities": ["upload_content", "defense_knowledge"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {"coordinate": "local_update/factors/module", "basis": "reported", "note": "伪造因子的取值分布与诚实训练不同：trimmed mean/median 下逐参数被推到良性最大/最小值之外（论文把采样限制在 [wmax, 2·wmax] 或 µ±3σ–4σ），Krum 下取 w_Re − λs。"},
        {"coordinate": "uploads/factor_delta/client", "basis": "reported", "note": "上传相对下发全局因子的差按构造与无攻击时的变化方向 s 反号，幅度由二分搜索求得的 λ（Krum）或越界偏移量（trimmed mean/median）决定。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文报告聚合后的全局模型被推向无攻击方向的反方向，测试错误率显著上升（MNIST+LR+Krum 0.14→0.72/0.80，DNN 上 0.11→0.75/0.77）。"},
        {"coordinate": "history/features/round", "basis": "inferred", "note": "机制上偏移是逐轮累积的（论文报告投毒轮次比例越高错误率越大），因此逐轮全局因子轨迹应呈反向漂移；论文没有把逐轮特征本身作为观测量报告。"}
      ],
      "variant_of": "",
      "stealth_measures": ["逐参数只把伪造值推到良性极值之外的有限区间（部分知识用 [µ+3σ, µ+4σ] 或 [µ−4σ, µ−3σ]，全知识用 [wmax, 2·wmax] 一类区间），避免取值过远成为明显离群点。"],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "collusive_update_cluster",
      "summary_zh": "多个受控客户端协同，围绕同一个伪造更新点上传一簇彼此距离不超过 ε 的近重复本地 LoRA 因子，使 Krum/Bulyan 这类基于成对距离的选择规则选中该伪造点，并让它只需靠近少数良性更新。",
      "goal": ["untargeted"],
      "capabilities": ["upload_content", "collusion", "defense_knowledge"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {"coordinate": "local_update/factors/module", "basis": "reported", "note": "c 个伪造因子彼此距离不超过 ε（默认 0.01），在同一轮内形成紧密聚簇；论文自己承认 ε=0（完全相同）会让这些模型被服务器轻易检出。"},
        {"coordinate": "aggregate/weights/client", "basis": "reported", "note": "论文以「Krum 每轮选中被伪造的 w'_1」为构造约束（Equation 2 与 Theorem 1 给出 λ 的上界），Bulyan 下同一构造迁移进 θ 个被选模型。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "被选中后聚合结果整体变成/被拉向伪造点，测试错误率随之上升（Krum 0.14→0.72/0.80；Bulyan 0.14→0.36/0.38）。"}
      ],
      "variant_of": "",
      "stealth_measures": ["不把 c−1 个伪造更新取成完全相同，而是在距 w'_1 不超过 ε（默认 0.01）的范围内随机采样，避免因完全相同而被服务器识别。"],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
