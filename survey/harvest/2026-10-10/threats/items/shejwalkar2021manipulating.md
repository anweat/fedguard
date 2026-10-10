## 1. 这篇论文的攻击做了什么

论文的场景是传统联邦学习（跨孤岛与跨设备；CIFAR10/MNIST/Purchase/FEMNIST，Alexnet/VGG11/全连接网络），全文没有 LoRA、Transformer 或语言模型内容。攻击者控制 n 个客户端中的至多 m 个（m/n < 0.5，默认 20%），在每轮本地梯度算完、交给服务器之前，直接把要上传的更新替换成构造向量 ∇m = ∇b + γ∇p：∇b 是参考良性聚合（知道良性梯度就直接平均，否则用自己设备上的良性数据算出 m 个梯度再平均），∇p 是反向单位向量、反向标准差或反向符号三种扰动方向之一，γ 由 Algorithm 1 在预言机判定下搜索出"仍能被目标聚合规则接受的最大缩放系数"。目标是无目标投毒：让聚合后的全局模型在任何测试输入上准确率下降，论文明确把定向攻击与后门排除在外。攻击不投毒样本、不改损失/优化器/步数、不碰服务器聚合与下发，唯一入口是"上传前的后处理"。论文按是否知道 AGR、是否知道良性梯度把攻击者分成四类，据此给出 AGR-tailored 目标（公式 (3)–(5)）、针对 Fang 的破坏、AGR-agnostic 的 Min-Max/Min-Sum（公式 (6)(7)）以及针对 DnC 的自适应攻击；后半篇的 DnC 是防御，不构成威胁技术。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个：

- **update_scaling**：知道服务器聚合/防御算法的一侧（agr-updates、agr-only），把 γ 搜到"刚好还能通过该 AGR 判据"的最大值，主动让上传远离良性聚合，用"已知防御下的最大可行破坏"定义自己。
- **benign_clique_constrained_update**：不知道 AGR 的一侧（updates-only、agnostic），放弃针对具体规则优化，改为把上传约束在良性更新形成的团内（Min-Max / Min-Sum 两条距离约束），靠"看起来像良性更新"换取跨 AGR 的通用性。

这样拆的三条理由：所需能力不同（前者必须知道聚合算法，后者恰恰假设不知道）；留痕画像相反（前者在同一坐标上刻意制造最大偏离，后者刻意把该差异压到不可分）；目标函数与预言机不同（公式 (3)–(5) 对 (6)(7)）。两者共用同一个 ∇b + γ∇p 构造和同一个 γ 搜索算法，所以第二个记成第一个的变体。没有第三个技术：论文不做数据投毒（本地数据只用于算参考聚合）、不改本地训练、也不控制服务器聚合；针对 Fang 的破坏与针对 DnC 的自适应攻击只是第一个技术在特定防御下的实例，不单列。

## 3. 每个技术需要的能力与改动的制品

- 两个技术都只需要 `upload_content`：能决定"某些客户端上传什么"，就直接落在 `local_update`（上传前的本地更新）与 `uploads`（服务器收到的上传）上。这里刻意不写 `local_training`——论文明确说攻击不进入本地训练过程（不改损失、优化器、步数，也不产生步内梯度差异），它替换的是训练之后、上传之前的那个向量。按词表，论文所说的"梯度"就是它要上传的更新，对应 `local_update`/`uploads`，而不是步内的 `gradients`。
- 两个技术都加 `collusion`：论文要求所有恶意客户端每轮提交同一个 ∇m，γ 的可行域也按"有几个恶意梯度能被选中/保留"来定义，是多个受控客户端的协同动作。
- 第一个技术加 `defense_knowledge`：AGR-tailored 的目标函数与预言机 O 直接以服务器的聚合算法为输入；第二个技术不加，它恰恰假设不知道算法。论文的 agr-updates / updates-only 还需要知道良性设备的梯度，词表里没有对应键，因此没有写进 capabilities，只在此说明。
- 不写 `local_data`：agr-only / agnostic 只是用自己设备上的良性数据算参考聚合，样本本身没有被改动。
- 制品两边都是 `local_update` + `uploads`，不碰 `samples`、`gradients`、`trace`、`aggregate`、`outgoing`、`channel`、`history`。本文上传的是完整模型梯度，映射到联邦 LoRA 微调时最自然的对应是把待上传的 LoRA 因子替换成构造的因子更新（`uploads/factor_delta`），服务器聚合的几何从"参数向量逐维"变成"低秩因子"，论文报告的鲁棒性排序不能直接照搬（卡片第 9 节的分析）。

## 4. 可能留痕的位置与依据

- `uploads/factor_delta/client`：第一个技术是 reported——卡片明确写论文把"恶意上传偏离良性聚合的程度"当成攻击目标函数（公式 (1)(2)(5)），DnC 也正是在这个向量的主成分投影上做离群检测。第二个技术是 inferred——论文只报告攻击影响，没报告该坐标的检测统计；按机制它刻意把距离/分布/范数差异压到最小，论文声称这足以让六种既有 AGR 与 Fang 防御失效，但 DnC 的谱方法仍能削弱它（Table IV：Min-Max 3.5%、Min-Sum 2.0%）。
- `local_update/aux_gradient/module`：第一个技术写 inferred——上传的是"良性参考聚合 + 缩放扰动"的合成向量，不是该客户端本地小批量的梯度，用客户端自身或辅助样本梯度做方向一致性检查会出现差异；论文没有测量这个坐标。第二个技术不写：它的约束保证恶意更新仍贴近一个真实的良性梯度平均，这里有没有可观测差异没有把握。
- `aggregate/result/model`：两个技术都写 reported——论文报告受攻击后全局模型在验证集上的准确率下降 I_θ（第一个技术在 CIFAR10+Alexnet 上最高 36.8%，第二个技术在 CIFAR10+Alexnet+Bulyan 一行 44.5%）。
- 明确不写的位置：`samples/*`（不投毒数据）、`trace/*`（不改本地训练，无步内差异）、`channel/*`（论文不涉及自报值或通道消息）、`history/features/round`（DnC 只用本轮收到的更新）、`received/*`（攻击者只是正常读取每轮下发的全局模型）、`aggregate/weights/client`（服务器诚实，攻击者不能改聚合名单与权重）。

```json
{
  "key": "shejwalkar2021manipulating",
  "items": [
    {
      "technique_name": "update_scaling",
      "summary_zh": "恶意客户端在已知服务器聚合/防御算法的前提下，把上传替换为“良性参考聚合 + 缩放系数×扰动方向”，并用预言机搜索出仍能被该聚合规则接受的最大缩放系数，使聚合结果尽量偏离良性聚合。",
      "goal": ["untargeted"],
      "capabilities": ["upload_content", "defense_knowledge", "collusion"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {"coordinate": "uploads/factor_delta/client", "basis": "reported", "note": "卡片明确写论文把“恶意上传偏离良性聚合的距离”直接作为攻击目标函数（公式 (1)(2)(5)），DnC 也沿该向量的主成分投影做离群检测；CIFAR10+Alexnet 上最强 AGR-tailored 攻击使准确率下降 36.8%。"},
        {"coordinate": "local_update/aux_gradient/module", "basis": "inferred", "note": "按机制推断：上传的是“良性参考聚合+缩放扰动”的合成向量，不是该客户端本地小批量的梯度，用客户端自身或辅助样本梯度做方向一致性检查会出现差异；论文未测量该坐标。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文报告受攻击的聚合结果在验证集上准确率显著下降（I_θ = A_θ − A*_θ，CIFAR10+Alexnet 上最高 36.8%）。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "把“不被已知 AGR 剔除或选中”写成可行性约束，只在可行域内取最大 γ，即先保证通过该聚合规则的判据再最大化破坏",
        "针对 DnC 的自适应攻击（公式 (8)）压低恶意与良性梯度的均值差 μ_shift 以躲过谱离群检测，代价是投毒影响随之变小",
        "论文论证对 Fang 元防御只需把恶意梯度写成“良性均值 + 任意大向量”，就能让评分机制给良性梯度与恶意梯度几乎相同的分数"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "benign_clique_constrained_update",
      "summary_zh": "在不知道聚合/防御算法的前提下，把恶意上传约束在良性更新形成的团内（Min-Max：到任意其他更新的最大距离不超过良性间最大距离；Min-Sum：到所有良性更新的平方距离和不超过任一良性更新的同类量），再在约束内缩放扰动，使基于距离、分布与 Lp 范数的离群检测无法区分。",
      "goal": ["untargeted"],
      "capabilities": ["upload_content", "collusion"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {"coordinate": "uploads/factor_delta/client", "basis": "inferred", "note": "论文只报告攻击影响，未报告该坐标上的检测统计；按机制该技术刻意让上传与本轮其他更新的距离、分布和范数接近，这里的差异被压到最小，但 DnC 的谱方法仍能削弱它（Table IV：Min-Max 3.5%、Min-Sum 2.0%）。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文报告 AGR-agnostic 攻击在既有 AGR 上仍造成大幅准确率下降（CIFAR10+Alexnet+Bulyan 一行 44.5%）。"}
      ],
      "variant_of": "update_scaling",
      "stealth_measures": [
        "Min-Max 约束：恶意梯度到任意其他梯度的最大距离不超过任意两个良性梯度之间的最大距离",
        "Min-Sum 约束：恶意梯度到所有良性梯度的平方距离和不超过任一良性梯度到其他良性梯度的平方距离和，约束更紧、结果更靠近参考良性聚合",
        "用这两条约束同时规避既有鲁棒 AGR 依赖的距离、分布与 Lp 范数三类判据",
        "不知道 AGR 时先在缩小规模的模拟 FL 上仿真各扰动方向，选在尽可能多的 AGR 上效果最好的方向"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
