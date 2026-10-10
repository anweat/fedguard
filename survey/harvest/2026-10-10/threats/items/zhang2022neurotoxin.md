## 1. 这篇论文的攻击做了什么

Neurotoxin 的场景是传统联邦学习（FedAvg 均值聚合，服务器只做逐设备 ℓ2 范数裁剪与平均），攻击者是被攻陷的少量客户端（系统层面约 0.2%–1%，一次生命周期只贡献约 40 个更新，每轮最多 1 个被控设备）。攻击分两步：先在本地构造投毒数据集（NLP 任务从训练分布采样并拼接触发句，视觉任务把选定图像标成目标类，包括用分布外图像做 edge-case），再在本地训练的每一步把投毒梯度投影到坐标约束集——把上一轮下发梯度中 top-k% 的 heavy hitter 坐标置零，只在 bottom-k% 坐标上做后门训练，最后把训练得到的本地更新上传。论文既不缩放也不 boosting 上传更新，也不改服务器侧流程。目标是定向后门且不明显损害良性准确率；论文的核心卖点是后门在攻击停止、模型继续被良性更新训练后仍能长期存活（lifespan 提高数倍）。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个：`trigger_target_sample_injection`（数据侧）和 `heavy_hitter_coordinate_masking`（训练过程侧）。前者是"在本地数据里放触发器 + 目标标签"，控制点是 `local_data`、落在 `samples` 上，论文里的 baseline（k=0%）就是它，论文把它当作既有攻击沿用。后者是"逐坐标掩码，只在良性更新很少动的坐标上做后门训练"，控制点是 `local_training`、落在 `gradients/trace/local_update` 上，这才是论文的贡献。这样拆的依据是两者正交且可独立存在、可叠加：论文图 8 把该掩码叠在 ClipBKD（SVD 类攻击）上仍大幅提升耐久性，说明它不是数据注入的变体，而是一个通用的耐久性增强手法；反过来 k=0% 时掩码消失、只剩数据注入。论文没有 `update_scaling` / `model_replacement` 这类技术——卡片明确说 boosting/scaling 是既有攻击、本文不做，服务器聚合也不被改动，所以不设对应条目。

## 3. 每个技术需要的能力与改动的制品

`trigger_target_sample_injection` 需要 `local_data`（改 `samples`），并依赖被控客户端能原样上传自己训练出的更新，即词表里的 `upload_content`（改 `local_update`、`uploads`）；卡片把"可上传任意向量"写在威胁模型里，所以两个技术都列了它。`heavy_hitter_coordinate_masking` 需要 `local_training`（改 `gradients`、`trace`、`local_update`）加上同一个 `upload_content`。两个技术都不需要 `collusion`（论文的固定频率攻击每轮只控制 1 个设备，未要求协同），也不主张 `defense_knowledge`——卡片明说论文未交代攻击者是否知道范数裁剪参数 p；读取上一轮下发的全局更新在 FL 里是协议给定，不算额外能力。迁移到联邦 LoRA 时，`samples` 对应客户端本地微调样本，`gradients`/`local_update` 对应 LoRA 因子 A/B 的逐坐标梯度与上传前的因子；论文全篇未提 LoRA，"良性梯度范数集中在少数坐标"这一前提在低秩因子上是否成立论文未说明，因此 `heavy_hitter_coordinate_masking` 的 applicable 仍写 true，但 k 与掩码粒度必须按 LoRA 重标定。

## 4. 可能留痕的位置与依据

数据侧最直接的痕迹在样本：NLP 投毒样本含拼接的触发句（可短到 1 个词），edge-case 任务用的是来源分布外的图像，论文都明确报告了（reported）；本地更新带后门也是论文报告的（附录 A.1 说要在投毒数据集上多训几个 epoch 才到 100% 准确率），聚合后全局模型上的后门准确率/lifespan 同样有报告。掩码侧最实质的痕迹是**上传增量相对下发更新的逐坐标支撑集**：第 3.3 节报告 SparseFed 只更新梯度 top-k 坐标而 Neurotoxin 恰好避开这些坐标，这是论文自己给出的坐标级证据；此外算法 1 第 4 行明确写了逐步梯度投影，附录 A.1 报告约束优化收敛更慢（映射到训练步标量这一坐标是本次改写的推断性落点，已在 note 里注明）。反面证据也要记住：论文报告所有实验中启用的范数裁剪和基于 VAE 重建损失的检测都看不到可用于拦截的差异，所以逐客户端范数与重建损失不是有效判据；论文没有报告任何通道消息、聚合权重、逐样本损失或 Hessian 量以外的坐标痕迹，这些位置我没有写进 traces。

```json
{
  "key": "zhang2022neurotoxin",
  "items": [
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "在被控客户端的本地训练数据里拼接触发器并把目标标签绑定到固定目标输出，使本地训练出的更新带上定向后门。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "upload_content"],
      "modifies": ["samples", "local_update", "uploads"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "论文明确构造投毒数据集 D̂：NLP 任务从训练分布采样并拼接触发句，触发器可短到 1 个词（第 3.1 节、图 4）。"},
        {"coordinate": "samples/manifest/sample", "basis": "reported", "note": "edge-case 任务用分布外图像（西南航空飞机图标成 truck、Ardis 瑞典数字 7 标成 1，第 3.1 节），来源与训练分布样本不同；base-case 是把 512 张 5 类图像标签改成 9。"},
        {"coordinate": "local_update/factors/module", "basis": "reported", "note": "在 D̂ 上训练得到的本地更新带有后门：附录 A.1 报告需要在投毒数据集上多训若干 epoch 才达到 100% 准确率；对应联邦 LoRA 即上传前的本地因子。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文在聚合后的全局模型上报告后门准确率与 lifespan（图 1、表 3–5），是攻击成功的直接读数；度量需要知道触发器与目标标签。"}
      ],
      "variant_of": "",
      "stealth_measures": ["投毒样本取自真实训练分布（拼接触发句、真实图像）而不是带明显模式的数据，论文据此说明恶意梯度的重建损失低、可绕过基于重建损失的检测（第 3.3 节）。"],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "heavy_hitter_coordinate_masking",
      "summary_zh": "把本地每一步的投毒梯度在上一轮下发更新中幅值最大的 top-k% 坐标上置零，只在良性训练很少改动的 bottom-k% 坐标上做后门训练，使后门不易被后续良性更新覆盖。",
      "goal": ["backdoor"],
      "capabilities": ["local_training", "upload_content"],
      "modifies": ["gradients", "trace", "local_update", "uploads"],
      "traces": [
        {"coordinate": "gradients/batch_gradient/parameter", "basis": "reported", "note": "算法 1 第 4 行：每一步先在投毒数据上算梯度，把它投影到坐标约束集（置零上一轮梯度的 top-k% 坐标）后再更新本地模型。"},
        {"coordinate": "uploads/factor_delta/client", "basis": "reported", "note": "上传增量的逐坐标支撑集是最直接的痕迹：第 3.3 节报告 SparseFed 只更新梯度的 top-k 坐标，而 Neurotoxin 恰好避开这些坐标。"},
        {"coordinate": "trace/scalars/step", "basis": "reported", "note": "论文报告约束优化收敛更慢、需要用更多 epoch 才能在投毒数据集上达到 100% 准确率（附录 A.1）；把它落到训练步标量这一坐标是本次改写的映射。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "掩码版后门在聚合模型上衰减远慢于 k=0 基线：图 1 报告 50% lifespan 从 11 轮升到 67 轮、100% lifespan 从 24 轮升到 170 轮以上，表 3–5 给出 k 与 AttackNum 的扫描。"}
      ],
      "variant_of": "",
      "stealth_measures": ["只在良性幅值小的 bottom-k% 坐标上改动，避开 SparseFed 等 top-k 稀疏化防御会保留的坐标；论文报告该防御只能缓解、不能消除攻击（第 3.3 节、图 7）。", "改动集中在变化幅度小的坐标上，因此所有实验中启用的范数裁剪未能阻止攻击（第 3.2 节）。"]
    ,
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
