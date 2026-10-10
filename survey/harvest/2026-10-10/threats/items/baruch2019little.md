## 1. 这篇论文的攻击做了什么

论文的场景是**传统同步分布式 SGD**（单参数服务器 + n 个工作节点、数据 i.i.d. 切分），论文自己明确与联邦学习划清界限，也不涉及 PEFT/LoRA/LLM，因此两个技术条目的 `federated` 都写 false。攻击者是拜占庭工作节点（主实验 n=51、m=12，约 24%；摘要称 20% 即可让 CIFAR10 掉 50% 精度），可控制设备，也可只在通信层做中间人；介入点是本地训练结束、参数回传之前（Algorithm 1 第 6/7 行之间），把整份上传参数替换成任意值。

做法上有两条线：**收敛破坏**只用被控节点自己的参数估计总体的逐维均值 µ_j 与标准差 σ_j，把每个被控节点的每一维都设成 µ_j + z_max·σ_j（z_max 由 φ(z) < (n−s)/n 反解，算例 1.75/1.5/1），靠"小幅、逐维同侧、多个节点一致"而非幅度去骗过逐维裁剪与距离类聚合；**后门**则额外用单样本或左上角 5×5 图案的后门样本加自定义损失做本地训练，再把结果逐维裁剪到 [µ_j − z_max σ_j, µ_j + z_max σ_j] 后由所有被控节点同值上传。结果是 Trimmed Mean 三个变体、Krum、Bulyan 全部失效（CIFAR10 上分别掉 45%、66%、52%），而朴素平均因为稀释反而最鲁棒；后门命中率 >95% 且良性精度损失很小。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成**两个**：`benign_statistics_update_masquerade`（无目标、阻止收敛）与 `benign_statistics_backdoor_update`（后门）。拆分的依据是词表要求的三要素都不同：goal 一个是 `untargeted`、一个是 `backdoor`；能力上前者只需改上传内容并多节点协同，后者还必须控制本地数据与本地训练过程；制品上前者只动 `local_update`/`uploads`，后者还动 `samples`。论文本身也是把二者作为两类攻击分别评估的（表 1、图 2–4 对表 2、表 3）。

不进一步拆分：单样本后门与图案后门只是触发器形式不同（目标标签与图案不同），本地训练 + 归一化惩罚 + 逐维裁剪 + 同值上传的流程完全一致，属同一技术。论文提到的"混合策略"（一个被控节点对朴素平均实施早期工作的大幅攻击，其余继续小幅规避）只是针对 No Defense 的补充路径、论文未给实验，且共用同一上传入口，因此不单列为第三个技术。另一方面，两个技术的核心机制相同（把上传改到良性统计包络内、被控节点同值同侧），所以后门那条记为前者的后门变体（`variant_of`）。

## 3. 每个技术需要的能力与改动的制品

收敛破坏：能力为 `upload_content`（上传内容可整体替换）与 `collusion`（m 个节点必须同值同侧，靠"引诱"良性节点占据中位数）。**不需要** `defense_knowledge`——论文强调攻击者非全知、同一组恶意参数对所有被评估防御都有效；也**不需要** `local_data`/`local_training`，因为只控制通信就能完成。制品是 `local_update`（上传前本地因子被整体替换）与 `uploads`（上传的是同一个 p_mal）。

后门：能力为 `local_data`（往自己本地数据里注入触发样本）、`local_training`（自定义损失与额外后门训练；卡片指出若只控制通信则无法完成 Algorithm 4 第 3 行）、`upload_content` 与 `collusion`（Algorithm 4 让所有被控节点上传同一份裁剪结果；论文另注对 Krum 只需一个节点上报）。制品是 `samples`（本地样本被投毒）、`local_update`（裁剪后的本地参数）、`uploads`（同值上传）。这里没有把 `gradients`、`trace` 写进 modifies：论文的写操作发生在本地训练**之后**，只替换最终参数向量，卡片没有说攻击者逐维改写步内梯度或训练标量。映射到联邦 LoRA 时，`samples` 对应本地微调样本（含触发样本），`local_update` 对应上传前的 LoRA 因子 A/B，`uploads` 对应因子差，能力键不变。需要说明的迁移风险（卡片第 9 节）：逐维 i.i.d. 正态假设在异质联邦中不成立，z_max 的推导失去依据；LoRA 只上传低秩增量，逐维自由设定的空间远小于全参数维度——技术本身可表达，但论文给出的幅度标定不能直接照搬。

## 4. 可能留痕的位置与依据

最直接的是 `uploads/factor_delta/client`：Algorithm 3/4 的最后一步都把所有被控节点赋成同一个 p_mal，于是同一轮被控客户端上传的因子差**逐维完全相同**、且每一维相对总体均值同侧偏移约 z 倍标准差；卡片第 5 节把它列为本文攻击的结构性痕迹（同时注明论文未据此做检测），故 basis 写 reported。其次是 `local_update/factors/module`：上传前的本地因子不再等于本地训练的产物，而是被替换（收敛）或被裁剪到包络内（后门），这也是论文算法直接规定的，写 reported。结果层面的 `aggregate/result/model` 是论文真正报告过的差异（各防御下的精度下降幅度、后门命中率），写 reported。后门独有的是 `samples/text/sample`（本地出现触发样本），论文第 4.2 节明确构造，写 reported，但注明服务器侧按论文设定看不到客户端的训练样本。收敛破坏还应在 `history/features/round` 上留下跨轮方向一致的持续漂移（论文说偏移在多轮中持续累积），但论文逐轮独立评估防御、没有做跨轮检测实验，这一条 basis 写 inferred。攻击者本地"估计 µ_j/σ_j"的过程没有任何服务器侧坐标可观测，不写。

```json
{
  "key": "baruch2019little",
  "items": [
    {
      "technique_name": "benign_statistics_update_masquerade",
      "summary_zh": "被控客户端在上传前把整份更新替换成用被控节点自身参数估计出的逐维良性统计量（µ_j + z·σ_j），使逐维裁剪与距离类稳健聚合都不把它当离群值，从而在多轮中持续拖垮收敛。",
      "goal": ["untargeted"],
      "capabilities": ["upload_content", "collusion"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {"coordinate": "uploads/factor_delta/client", "basis": "reported", "note": "Algorithm 3 最后一步把所有被控节点的参数都赋成同一个 p_mal，因此同一轮被控客户端上传的因子差逐维完全相同，且每一维相对总体均值同侧偏移约 z 倍标准差；卡片第 5 节把它列为本文攻击的结构性痕迹，但论文未据此评估任何检测器。"},
        {"coordinate": "local_update/factors/module", "basis": "reported", "note": "上传前的本地参数被整体替换为 µ_j + z_max·σ_j（第 3.3 节 Algorithm 3），不再等于本地训练得到的取值。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文报告聚合后的全局模型精度大幅下降：CIFAR10 上 Krum −66%、Bulyan −52%、Trimmed Mean −45%、朴素平均 −28%（图 3、第 4.1 节）。"},
        {"coordinate": "history/features/round", "basis": "inferred", "note": "攻击每轮重复同样的同侧小幅偏移，论文称偏移会在多轮中持续累积，故跨轮特征上应表现为方向一致的持续漂移；论文按轮独立评估防御，未给出跨轮检测实验。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "把逐维偏移限制在约 z_max 倍标准差以内（z_max 由 φ(z) < (n−s)/n 反解，算例取 1.75/1.5/1），使取值落在良性分布中央区间，逐维裁剪与基于距离的剔除都拿不到离群证据",
        "被控节点上传完全相同的向量并同处一侧，靠数量与一致性占据中位数，而不是靠偏移幅度",
        "论文强调非全知：同一组恶意参数对所有被评估防御都有效，攻击者不需要知道服务器选了哪种聚合规则"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "benign_statistics_backdoor_update",
      "summary_zh": "被控客户端先用带触发器的本地样本和自定义损失训练出后门模型，再把参数逐维裁剪到良性统计包络 [µ−z·σ, µ+z·σ] 内并让所有被控节点上传同一份，使后门在稳健聚合下存活。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "local_training", "upload_content", "collusion"],
      "modifies": ["samples", "local_update", "uploads"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "受控客户端的本地样本里加入单样本触发器（前 3 张图之一、标签改为 (y+1) mod |Y|）或左上角 5×5 最大强度图案（目标标签固定为 0）（第 4.2 节）；该差异只有能访问该客户端本地数据时才可见，论文设定下服务器看不到客户端用什么样本训练。"},
        {"coordinate": "local_update/factors/module", "basis": "reported", "note": "后门训练得到的参数被逐维裁剪到 [µ_j − z_max·σ_j, µ_j + z_max·σ_j]（Algorithm 4 最后一步），因此本地因子逐维都落在良性包络内，但行为已被后门影响。"},
        {"coordinate": "uploads/factor_delta/client", "basis": "reported", "note": "所有被控节点上传同一份裁剪后的 p_mal（Algorithm 4），上传因子差逐维相同且都不显眼。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文报告后门命中率：单样本 >95%，图案后门在 MNIST 上 99.9–100%、CIFAR10 上 80.7–95.1%，同时良性精度损失很小（表 2、表 3）。"}
      ],
      "variant_of": "benign_statistics_update_masquerade",
      "stealth_measures": [
        "用按逐维标准差归一化的惩罚项 ((NewParam_j − OldParam_j)/max(z_max·σ_j, 1e−5))² 把参数约束在 z_max·σ 包络内，偏移超过包络时惩罚迅速增大（式 (3)(4)）",
        "上传前逐维硬裁剪到 [µ−z·σ, µ+z·σ]（Algorithm 4 最后一步）",
        "取能够成功植入后门的最小 α，避免参数显著偏离原始参数而被防御丢弃（第 3.4 节）"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
