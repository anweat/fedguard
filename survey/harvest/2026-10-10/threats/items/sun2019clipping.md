## 1. 这篇论文的攻击做了什么

在传统跨设备联邦学习（EMNIST、五层 CNN、TFF 实现）里，被完全攻陷的客户端做的是**模型更新投毒**而非数据投毒：它用当前全局模型 $w_t$ 初始化，在 $D_{trn}\cup D_{mal}$ 上训练出后门模型 $w^*$，再把更新按放大因子 $\beta=\sum_{k\in S_t} n_k/(\eta n_k)$ 放大后上传（$\Delta w=\beta(w^*-w_t)$），靠按样本数加权平均抵消其他客户端的贡献，使 $w_{t+1}\approx w^*$。目标是定向后门——保持主任务性能，同时让若干"目标客户端"的数字 7 被分类成 1。论文给出两个版本：无约束 boost（范数很大，作为基线）和范数受限版本（训练时用多轮投影梯度下降把 boost 前范数压到 $M/\beta$ 以内，使 boost 后范数不超过 $M$，在假设攻击者知道阈值 $M$ 的前提下绕过范数阈值/裁剪）。参与调度上有随机采样与固定频率两种；恶意比例从 3.3% 降到 0.33%，低于约 1% 时后门成功率明显下降。防御侧论文评估了更新范数裁剪（界取 3 可缓解攻击且几乎不伤主任务）与在裁剪之后加方差 0.025 高斯噪声的弱差分隐私。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两条：`update_scaling`（一般做法）与 `norm_constrained_update_scaling`（前者的规避型变体）。两者的目标（backdoor）、入口（本地训练 + 上传前处理）和改动的制品（local_update、uploads）完全相同；**唯一的能力差异**是第二条额外要求"知道防御阈值 $M$"（defense_knowledge），并据此把上传幅度压进 $M$ 以内。正因为差异落在能力项和规避行为上，而不在目标/制品上，卡片第 4 节自己把它们写成"两类攻击"，我据此拆成两条，并把第二条标为 `variant_of = update_scaling`，而不是并列的第三种技术。

不再多拆：随机采样攻击与固定频率攻击只是同一攻击的参与调度（论文结论是二者行为相近）；同一轮多个攻击者"均分替换更新"是协同方式（collusion），作为同一技术的一个方面记录。论文里没有数据投毒、无目标破坏、隐私窃取或越狱目标，因此没有第三条技术。

## 3. 每个技术需要的能力与改动的制品

两条技术共同需要：`local_training`（能任意改动本地训练过程及产物，从而任选本地更新）、`upload_content`（能任意构造上传内容）、`collusion`（同轮多个受控客户端能互相协调并均分该更新）。第二条另加 `defense_knowledge`（知道范数阈值 $M$，因此总能返回幅度在阈值内的恶意更新）。改动的制品都是 `local_update` 与 `uploads`：上传相对下发的因子差/乘积差被整体改写成指向 $w^*$ 的方向并按 $\beta$ 放大（第二条再把幅度压回 $M$）。梯度与步内标量是正常训练产生的，卡片没有说攻击者伪造它们，故不记 `gradients`、`trace`。

卡片还写出攻击者持有 $D_{mal}$ 与来自真实分布的 $D_{trn}$、并知道当前全局模型 $w_t$——这些是攻击前提。词表里没有"持有数据"这一能力键，且论文明确区分 data poisoning 与 model update poisoning、强调入口是上传的更新而非数据，所以不把 `local_data`/`samples` 记进这两条技术（否则会让人误以为样本侧净化是候选对策）。映射到联邦 LoRA 微调时，$w^*-w_t$ 对应客户端的 LoRA 因子差，放大因子 $\beta$ 依赖服务器学习率、参与客户端的样本数与聚合权重，且"裁剪 A/B 因子还是裁剪乘积 BA"在原论文中完全没有讨论，这两点都需要重新推导（卡片第 9 节的分析）；两条技术都仍能自然对应，故 `applicable` 为 true。

## 4. 可能留痕的位置与依据

- `uploads/factor_delta/client`：无约束 boost 的痕迹就是上传更新的 $\ell 2$ 范数异常大，**reported**（第 4 节把它作为范数阈值/裁剪防御的动机）；范数受限变体刻意把这一读数压到 $M$ 以内，所以该变体在此处不留幅度差异。
- `aggregate/result/model`：论文报告代入加权平均后 $w_{t+1}$ 落在 $w^*$ 的小邻域（第 3 节），实验中表现为后门任务准确率上升而主任务基本不变（第 5 节），**reported**；范数受限变体在界为 10 时仍相当有效（Figure 2，**reported**），界取 3 时该差异被削弱（Figure 4(a)）。
- `uploads/module_delta/client` 与 `uploads/probe_behavior/client`：**inferred**——范数约束只压幅度、不压方向，逐模块因子差仍指向 $w^*-w_t$；把某客户端上传的 LoRA 加载后在目标客户端的 7→1 子上探测，预期与良性更新不同。卡片没有做方向统计，也没有做逐客户端行为探测，这两条只是机制推断。
- 边界：卡片明确说论文不提供任何"识别谁是恶意客户端"的检测器，防御只做幅度后处理；一旦启用安全聚合，服务器看不到单个客户端的更新，上述范数类坐标全部不可用（第 1、6 节）。

```json
{
  "key": "sun2019clipping",
  "items": [
    {
      "technique_name": "update_scaling",
      "summary_zh": "被完全攻陷的客户端以当前全局模型为初始化，在本地数据（含后门任务数据）上训练出后门模型 w*，再按放大因子 β=Σn_k/(η n_k) 把更新 w*−w_t 放大后上传，靠按样本数加权平均抵消其他客户端的贡献，把全局模型替换到 w* 附近。",
      "goal": ["backdoor"],
      "capabilities": ["local_training", "upload_content", "collusion"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {
          "coordinate": "uploads/factor_delta/client",
          "basis": "reported",
          "note": "无约束 boost 攻击的上传更新范数异常大，卡片明确以此作为范数阈值/裁剪防御的动机（第4节）。"
        },
        {
          "coordinate": "aggregate/result/model",
          "basis": "reported",
          "note": "卡片报告代入加权平均后 w_{t+1} 落在 w* 的小邻域（第3节）；实验中的可观测差异是后门任务准确率上升而主任务基本不变（第5节）。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "分析：该上传的方向指向后门模型，把某客户端上传的 LoRA 加载后在目标客户端的 7→1 子上探测，预期与良性更新不同；卡片未做逐客户端行为探测。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "norm_constrained_update_scaling",
      "summary_zh": "同样放大上传更新，但在本地训练时把 boost 前的更新投影回以 w_t 为中心、半径 M/β 的 ℓ2 球（多轮投影梯度下降），使 boost 后的上传范数不超过已知的防御阈值 M，从而绕过范数阈值丢弃与范数裁剪。",
      "goal": ["backdoor"],
      "capabilities": ["local_training", "upload_content", "collusion", "defense_knowledge"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {
          "coordinate": "aggregate/result/model",
          "basis": "reported",
          "note": "卡片报告范数界为 10 时该攻击仍相当有效（第5节，Figure 2），即聚合后的全局模型在后门任务上的准确率异常上升；界取 3 时该差异被削弱（第5节，Figure 4(a)）。"
        },
        {
          "coordinate": "uploads/module_delta/client",
          "basis": "inferred",
          "note": "分析：约束只作用于幅度、不作用于方向，指定模块的因子差方向仍指向 w*−w_t，因此差异在这一坐标上表现为方向而非范数异常；卡片未报告方向统计。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "分析：上传方向仍指向后门模型，逐客户端行为探测预期仍能看出与良性更新的差异；卡片未做该探测。"
        }
      ],
      "variant_of": "update_scaling",
      "stealth_measures": [
        "假设攻击者知道范数阈值 M，并在训练时把 boost 前的更新范数约束在 M/β 以内（多轮投影梯度下降），使上传更新 boost 后范数不超过 M，从而规避范数阈值丢弃与范数裁剪（第3、4节）"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
