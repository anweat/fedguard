## 1. 这篇论文的攻击做了什么

论文在传统联邦学习（FedAvg 及变体、全参数模型：VGG-9/11、LeNet、LSTM，K 从 200 到 80,000）里由被选中的恶意客户端在训练期植入**定向后门**：目标不是通用降效，而是让全局模型对一组"自然但罕见"的 p-edge-case 输入（特征分布重尾上的样本，如航司涂装的飞机照、手写体里的"7"、冷门导演的推文）输出攻击者指定的标签，同时保持在自然数据上的准确率。攻击者的入口有三处：训练前把本地数据集替换为 D′ = D ∪ D_edge 且 D_edge 占比过半（黑盒能力的全部）；训练中用 PGD 并在每 10 个 SGD 步把参数投影回以本轮全局模型为球心、半径 δ 的球（白盒，δ 取该系统范数防御允许的最大范数差）；上传前把更新按 nS/ni′ 缩放，提交 (nS/ni′)(wi′ − w) + w（模型替换）。论文只用了 0.5%–5% 的恶意客户端、频率低至 0.01 的周期性参与，并靠多轮累积注入。它系统评估了 NDC、Krum、Multi-Krum、RFA 与弱 DP 四种服务器侧干预：调好范数约束的白盒攻击（带/不带替换）通过全部被测防御，黑盒攻击过不了 Krum/Multi-Krum；论文不提出任何防御，只给出两条"检测在一般情况下不可行"的理论结果（Proposition 1、2），也没有在 SecAgg 下做实验，未报告任何开销。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成三个，依据是**攻击者动用了哪一种能力杠杆、以及它直接改动哪一类制品**（本库用"目标 + 能力 + 改动的制品"定义威胁技术，这三条在这三个维度上都不同）：

- **尾部样本注入（数据杠杆）**：只替换本地数据，用与诚实客户端相同的超参数训练。这是黑盒攻击者能做的全部，能力上只需要 `local_data`。
- **范数受约束的本地训练（训练杠杆）**：定义性动作是"改用自定义本地算法 + 周期性把参数投影回 δ 球"，需要 `local_training`，并因此触及 `gradients`、`trace` 这两类制品。它可以在任意恶意目标上叠加，不依赖具体的数据构造；论文里它与第一条叠加使用。
- **模型替换（上传杠杆）**：只需要控制上传内容（`upload_content`），是对任何恶意本地更新的上传前后处理，作用是把加权平均的结果整体替换成攻击者模型。

为什么不合成一条：三条的能力边界不同（数据 / 训练 / 上传），且对应的痕迹坐标不同（数据侧看样本，训练侧看步内轨迹与范数预算，上传侧看聚合结果），防御含义也不同（NDC 主要被第二条规避、Krum 主要卡住第一条）。为什么不再多拆：Theorem 1 与 Proposition 1、2 是分析结果而不是攻击动作；边缘样本的人工收集或 GMM 筛选只是第一条的数据构造步骤；"Krum 下不做 PGD+替换"是策略选择。需要说明的是，第一条与第二条同属"投毒本地训练"家族，差别只在是否动用 `local_training`；本库按能力边界分列，是为了能按"攻击者控制到哪一层"检索。

## 3. 每个技术需要的能力与改动的制品

| 技术 | capabilities（词表键） | modifies（词表键） |
|---|---|---|
| tail_sample_target_injection | local_data, upload_content | samples, local_update, uploads |
| norm_bounded_local_training | local_training, upload_content | gradients, trace, local_update, uploads |
| model_replacement | upload_content | local_update, uploads |

补充前提（词表里没有对应键，只能写在说明里）：第一条还需要能拿到或人工构造 p-edge-case 样本、并有良性样本可用来拟合低密度筛选模型（需要一次前向与可信参考数据）；第二条要求白盒——能在本地跑任意训练算法并做投影；第三条还要求攻击者近似知道系统参数 nS（当轮被选中客户端的数据总量）与自身数据量 ni′，词表没有"系统参数知识"这一能力键，故不写进 JSON。按卡片第 9 节的分析，这三条在联邦 LoRA 微调里都有自然对应（本地样本、本地训练过程、上传的 LoRA 增量都照旧存在），所以 `applicable` 保持 true；但全参数上的范数阈值不能直接沿用，nS/ni′ 缩放在低秩增量上是否等效论文未说明，需要重新推导与重新标定，这一点不影响条目的可适用性判断。

## 4. 可能留痕的位置与依据

- **只在客户端本地可见**的坐标：`samples/text/sample`（D′ 的构成，卡片明确报告）、`samples/hidden_state/sample`（卡片报告用倒数第二层表示拟合 GMM 并按对数密度筛出低密度样本，图 2）、`gradients/parameter_value/parameter` 与 `trace/scalars/step`（投影把参数周期性回拉）。服务端在非 SecAgg 下也看不到前两类中的样本文本本身，后两类更是客户端私有。
- **服务端可见、论文明确报告过差异**的坐标：`uploads/product_delta/client` 与 `uploads/module_delta/client`（范数差 ‖Wp − Wg‖，图 3(a)、图 12(b)）、`uploads/factor_delta/client`（缩放后的上传差）、`aggregate/result/model`（后门被写进全局模型）、`history/features/round`（低频攻击逐轮累积，图 4、附录 E 图 14）。注意第二条技术的痕迹形态特殊：它并不制造"看得见的偏差"，而是把范数差刻意压在裁剪阈值边缘（δ 取范数防御允许的最大值），所以在这个坐标上"贴着阈值"本身就是它的痕迹。
- **依据判定**：凡是卡片写明论文报告了该可观测量或该动作的，记 `reported`（上述绝大部分）；只有 `trace/scalars/step` 是依"每 10 步投影一次 + ε 随轮次衰减"的机制推断的，记 `inferred`，卡片并未报告步内标量曲线。凡原文只报告全模型粒度（范数差、逐层权重扰动）而坐标写成 LoRA 因子/模块粒度的，都在 note 里注明这是按 LoRA 的对应改写。
- 卡片没有报告任何检测器，也没有在 SecAgg 下做实验；因此跨轮与聚合结果这两类痕迹只是"论文自己展示过的现象"，不构成已验证的检测依据。

```json
{
  "key": "wang2020tails",
  "items": [
    {
      "technique_name": "tail_sample_target_injection",
      "summary_zh": "把本地数据集替换为 D ∪ D_edge（自然但概率密度极低的尾部样本，标签由攻击者指定，且在本地数据中占一半以上），再按诚实客户端的超参数做标准本地训练并上传，使全局模型对这类自然罕见输入输出目标标签。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "upload_content"],
      "modifies": ["samples", "local_update", "uploads"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "论文明确攻击者把本地数据集替换为 D′ = D ∪ D_edge，D_edge 是自然但罕见、不在原训练与测试分布中的样本，标签由攻击者选定，且 D′ 中超过 50% 来自 D_edge（第 2 节、第 4 节）。该坐标只在客户端本地可见，服务器看不到样本文本。"},
        {"coordinate": "samples/hidden_state/sample", "basis": "reported", "note": "论文用倒数第二层输出拟合高斯混合模型并按对数密度筛出低密度样本，图 2 用 MNIST 测试集与 ARDIS 训练集对比显示尾部样本对数密度明显更低。复现该视图需要可信参考样本与一次前向（via: model_handle），且论文是在攻击者侧使用它。"},
        {"coordinate": "uploads/product_delta/client", "basis": "reported", "note": "论文报告客户端返回模型与全局模型的范数差 ‖Wp − Wg‖，并显示它随 D′ 中干净样本比例以及本地数据量变化（图 3(a)、图 12(b)）；原文是全模型粒度，在 LoRA 下对应上传相对下发的乘积差，属坐标映射而非原文报告。"},
        {"coordinate": "history/features/round", "basis": "reported", "note": "论文报告攻击频率低至 0.01 时后门仍随轮次逐步累积（图 4），黑盒攻击在 NDC 与 RFA 下只是被减慢、多轮后仍能注入（附录 E 图 14），说明单轮视图不足以发现它。"}
      ],
      "variant_of": "trigger_target_sample_injection",
      "stealth_measures": [
        "用自然尾部样本而不是分布外样本当触发：Remark 1 刻意排除 p = 0 的情形，理由是已知的分布外检测比尾部样本检测更容易，而这些样本不在原训练集与测试集中，常规评估看不出异常。",
        "以低参与频率（最低 0.01）和很小的恶意比例（0.5%–5%）长期参与，靠足够多轮次逐步注入，单轮不易察觉（图 4、附录 E 图 14）。"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "norm_bounded_local_training",
      "summary_zh": "在本地训练阶段改用自定义算法（在投毒数据上做投影梯度下降），每 10 个 SGD 步把参数投影回以本轮下发模型为中心、半径 δ 的球内，使上传更新的范数差被压在系统范数防御允许的阈值以内；δ 直接取该防御允许的最大范数差，论文中它与尾部样本注入叠加使用。",
      "goal": ["backdoor"],
      "capabilities": ["local_training", "upload_content"],
      "modifies": ["gradients", "trace", "local_update", "uploads"],
      "traces": [
        {"coordinate": "gradients/parameter_value/parameter", "basis": "reported", "note": "论文明确攻击者每一步做梯度更新，并周期性地把参数投影到以全局模型 w 为球心、半径 δ 的球上，即优化器更新前的参数值被回拉；投影不是每步都做，而是每 10 个 SGD 步一次效果更好，ε 还随轮次衰减（第 2 节、附录 A）。坐标按 LoRA 参数理解，原文是全参数模型。"},
        {"coordinate": "trace/scalars/step", "basis": "inferred", "note": "由投影频率（每 10 个 SGD 步一次）与 ε 随轮次衰减的机制推断：客户端逐步的训练标量（例如与下发模型的距离）会呈现周期性回拉。论文只报告了投影频率与 ε 取值，没有报告步内标量曲线，LoRA 场景下更未报告。"},
        {"coordinate": "uploads/module_delta/client", "basis": "reported", "note": "论文明确投影半径 δ 的启发式取值就是该联邦系统范数防御所允许的最大范数差，也就是该坐标上的差异被刻意压在裁剪阈值边缘而不是消除；图 6 显示调好范数约束的白盒攻击可通过 NDC（附录 A 给出任务 1 用 ε = 0.1、其余防御用 0.083 等）。原文为全模型范数差，模块粒度是 LoRA 下的对应改写。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "把投影半径 ε 从原来的 2 缩小到 0.5 × 0.998^t 或 1.5 × 0.998^t，使返回模型的范数差落在 NDC 阈值以内（附录 A）。",
        "每 10 个 SGD 步才投影一次并让 ε 随轮次衰减，论文记载这样比每步投影效果更好，更新幅度更贴近诚实客户端（附录 A）。"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "model_replacement",
      "summary_zh": "上传前把本地训练所得模型与上一轮全局模型的差乘以 nS/ni′（当轮被选中客户端的数据总量除以攻击者自身数据量）再加回全局模型，使按样本数加权的平均结果近似等于攻击者自己的模型，即整体替换聚合结果。",
      "goal": ["backdoor"],
      "capabilities": ["upload_content"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {"coordinate": "local_update/factors/module", "basis": "reported", "note": "论文明确攻击者不再提交本地训练得到的 wi′，而是提交 (nS/ni′)(wi′ − w) + w，即上传前的本地更新被按当轮样本数之比整体缩放并重定基（第 2 节）。该技术还要求攻击者近似知道 nS 与自身数据量 ni′。"},
        {"coordinate": "uploads/factor_delta/client", "basis": "reported", "note": "上传相对下发的因子差被乘上 nS/ni′，使该客户端在按样本数加权的平均中占主导；论文报告带模型替换的白盒攻击在调好范数约束后通过全部被测防御（图 6，附录 A 给出任务 1 对 NDC 用 ε = 0.1、其余防御用 0.083，任务 2 用 0.3 / 0.25，任务 4 用 0.01）。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文推导当 w 在 D 上接近收敛时 w_next ≈ wi′，聚合结果被替换；实验上表现为全局模型在边缘样本上输出目标标签而主任务准确率基本不变（第 2 节、图 6）。"}
      ],
      "variant_of": "update_scaling",
      "stealth_measures": [
        "替换前预先缩小投影半径 ε 以抵消缩放带来的范数增长，使缩放后的上传仍落在范数阈值内（附录 A 的分任务取值）。",
        "针对每种已知防御单独调参（对 Krum、Multi-Krum、RFA 把 ε 由 2 缩小并随轮次衰减；在 Krum 下不做 PGD 加替换，因为中毒更新一旦被选中即自动等效于替换），属于对固定防御的单向自适应规避（第 4.1 节、附录 A）。"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
