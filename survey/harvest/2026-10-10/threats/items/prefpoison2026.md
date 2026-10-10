## 1. 这篇论文的攻击做了什么

论文针对集中式离线 RLHF 的 DPO 训练：攻击者能决定离线偏好数据集的标签，但只能把已有比较对的标签 $o_i$ 翻成 $-o_i$，不能新增偏好对，数据集大小固定。它先证明在对数线性策略 / log-linear DPO 下，翻转单个标签引起的每样本梯度变化 $\Delta g_i = o_i\beta\Delta\psi_i$ 与参数 $\theta$ 无关，于是"该翻哪些标签"变成一个固定字典 $V$ 上的二元稀疏逼近：解 $Vx=-g^\dagger$（或 $\lVert Vx+g^\dagger\rVert_2\le\epsilon$），其中 $g^\dagger$ 是攻击者自选目标策略 $\pi^\dagger$ 在干净数据上的 DPO 梯度；按解的支撑集翻标签后，受害者在投毒数据上训练出的参数与策略就靠近 $\pi^\dagger$（Lemma 3.2），翻转数还有下界 $\lvert F\rvert\ge\lVert g^\dagger\rVert_2/(2\beta)$。论文给出两个求解器 BAL-A（格嵌入 + LLL/Babai）与 BMP-A（带预算 $K$ 的二元匹配追踪），实验是 SHP 数据 + 冻结 DistilBERT 特征上的 log-linear DPO，不是生成式大模型，也不是联邦或 LoRA 设定。论文不提出防御算法，只给出充分性的不可行性证书（Theorem 5.4）。

## 2. 拆成哪几个威胁技术，为什么这样拆

只拆出一个：`preference_label_flip`（翻转本地偏好数据中已有比较对的标签，定向操控训练后的策略）。论文里看似有好几样东西——精确形式与近似形式、BAL-A 与 BMP-A、Appendix C.2 的奖励建模命题——但它们的目标（把策略推向攻击者选定的 $\pi^\dagger$）、所需能力（控制本地偏好数据的标签）与改动的制品（本地样本）完全相同，差别只在数学形式与求解算法；威胁技术按"攻击者做的一类事"定义，不按论文的算法名或定理编号定义，因此两个求解器不构成两个技术。Appendix C.2 的奖励建模情形卡片只说有"对应命题"、没有实验，且动作与制品与 DPO 情形一致，也不单列。论文的不可行性证书是防御侧产物，不属于威胁技术。

## 3. 每个技术需要的能力与改动的制品

能力只写 `local_data`：攻击者能直接改写的只有本地偏好样本的标签，对应制品 `samples`；训练过程、上传内容、聚合与下发都不在其控制内。需要指出的是，论文的白盒前提（拿到特征映射 $\psi$、逐样本特征差 $\Delta\psi_i$、干净数据集 $D$，并能在自选 $\theta^\dagger$ 处算出 $g^\dagger$）严格强于词表能表达的范围——词表没有"白盒访问模型 / 特征映射"这个键；最接近的 `query_access` 指查询训练后的模型、`base_model` 指控制或事先改动基座模型、`defense_knowledge` 指知道防御算法与参数，三者都与论文描述不符，因此都不写，只保留 `local_data`，把白盒要求作为该方法的附加前提在说明中点出。翻转效应字典 $V$、目标梯度 $g^\dagger$、预算 $K$ 与容差 $\epsilon$ 都是攻击者自己算出的中间量，不是它写入的制品。

## 4. 可能留痕的位置与依据

数据面：翻转直接落在样本记录的比较结果上，对应 `samples/text/sample`，basis 为 reported——论文的威胁模型就是把 $o_i$ 改成 $-o_i$，实验也用真值支撑集与 TPR、TP/FP/FN 衡量能否指认被翻的样本。梯度面：每个被翻样本的梯度分量改变一个与 $\theta$ 无关的常数向量（Theorem 3.1），对应 `samples/gradient/sample`（reported，论文正是靠字典 $V$ 的支撑集恢复来验证）；全部翻转叠加使 $\theta^\dagger$ 处的数据级梯度偏移 $\Delta g_F$、一阶条件残差 $\lVert Vx+g^\dagger\rVert_2$ 下降，对应 `gradients/batch_gradient/parameter`（reported，论文报告了残差曲线）。模型面：重训后参数靠近 $\theta^\dagger$（$\lVert\hat\theta-\theta^\dagger\rVert_2\le\epsilon/m$），策略距离 $\lVert\pi_{\theta^\dagger}-\hat\pi_\theta\rVert_1\approx 0.012$，而干净模型与被投毒模型的距离约 0.224（Appendix I.1、Section 6.2.3）；论文没有 LoRA 与联邦实验，把它对应到 `local_update/factors/module`（上传前的本地 LoRA 因子）属于坐标映射上的推断，故 basis 写 inferred。不写 `samples/hidden_state/sample` 与 `samples/activation/sample`：翻转标签不改变前向表示，这两处按机制不该有差异；也不写 `channel/*`、`aggregate/*`、`outgoing/*`：论文既没让攻击者碰这些位置，也没报告那里的异常。论文明确没有提出或评估任何检测器，也没讨论规避机制，所以 `stealth_measures` 留空——把"最小化翻转数"解读为反检测手段是卡片里没有的说法。

```json
{
  "key": "prefpoison2026",
  "items": [
    {
      "technique_name": "preference_label_flip",
      "summary_zh": "攻击者只改动自己控制的本地偏好数据，按目标梯度匹配挑出少量已有比较对并翻转其标签（不新增样本、数据集大小不变），使在该投毒数据上做 DPO 训练得到的策略靠近攻击者事先选定的目标策略。",
      "goal": ["other"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "标签翻转本身：论文的威胁模型是把所选比较对的 o_i 改为 -o_i，实验用真值翻转支撑集与 TPR、TP/FP/FN 检验这些被翻样本能否被指认（Section 2.2、Section 6.2.3）。"
        },
        {
          "coordinate": "samples/gradient/sample",
          "basis": "reported",
          "note": "被翻样本的每样本梯度改变一个与 θ 无关的常数向量 Δg_i = o_i β Δψ_i（Theorem 3.1）；论文以该字典 V 的支撑集恢复率作为主要指标，说明这一逐样本差异是可观测的。"
        },
        {
          "coordinate": "gradients/batch_gradient/parameter",
          "basis": "reported",
          "note": "翻转集合在 θ† 处造成常数梯度偏移 Δg_F 并降低一阶条件残差 ∥Vx + g†∥_2（式 (4)(5)、Theorem 3.1），论文报告了残差随预算的变化；注意论文的 V 是整份数据集的字典，对应到本地批梯度是坐标层面的近似映射。"
        },
        {
          "coordinate": "local_update/factors/module",
          "basis": "inferred",
          "note": "论文只报告重训后的全参数距离 ∥θ̂-θ†∥_2（≤ ε/m）与策略距离 ∥π_θ†-π̂_θ∥_1 ≈ 0.012（对比 clean-vs-attacked 约 0.224），没有 LoRA 或联邦实验；据此推断差异会落在上传前的本地 LoRA 因子上，属于坐标映射上的推断。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
