## 1. 这篇论文的攻击做了什么

论文攻击的是参数高效微调的供应链：攻击者自己构造投毒指令数据、自己训练恶意 LoRA、再把这个适配器当"插件"发布到开源平台，并用推广、模型描述引导、在受害者会处理的文档里植入触发词等手段提高下载与触发概率。受害者把插件加载进 LLaMA/ChatGLM2 或 LLM agent 后，遇到固定触发词就会被引导输出攻击者指定的内容（定向错误信息）或执行恶意工具调用（下载执行脚本、发鱼叉邮件）。它**不是联邦学习**：没有客户端、没有服务器聚合、没有参与率与非独立同分布，攻击者单方掌控"数据—训练—发布"整条链，训练期注入、推理期兑现。方法上分三层：基线投毒、POLISHED（用更强教师 LLM 抛光投毒数据）、FUSION（过度投毒损失 + 与良性适配器直接相加）；论文另评估了奇异值分析、脆弱提示扫描、再对齐三种防御，并报告它们都不能可靠发现或移除后门。

## 2. 拆成哪几个威胁技术，为什么这样拆

按"目标 + 所需能力 + 改动的制品"三要素拆成三条：

- **trigger_target_sample_injection**（基线，也是本卡片的主技术）：目标 backdoor，能力是控制本地数据与本地训练，制品从 `samples` 一路到 `local_update`/`uploads`。
- **teacher_llm_data_polishing**（POLISHED）：目标同样是 backdoor，但它单独改动的制品只有 `samples`，能力只落在 `local_data` 上——它是"同一种注入做法的数据构造变体"，因此用 `variant_of` 指回上一条，而不是另立一门。
- **adapter_weight_fusion**（FUSION）：它除了投毒还要改损失、控制上传内容，并在权重层面对适配器做算术（∆θm = ∆θm_f + ∆θc），交付的制品是一个"已经融合好的本地更新"，能力与制品都与前两条不同，所以单列。它的过度投毒损失与融合两步按论文是一套流程，且由同一交付制品定义，故合为一条而非拆成两条。

没有单列的东西：定向错误信息与恶意工具调用是后门的**载荷**，不是独立技术；平台推广、模型描述引导、文档植词是投放/触发手段，词表里没有对应能力，也不改变制品类别；论文完全没有聚合与跨客户端协同，因此用不到 `aggregation`/`collusion`。

## 3. 每个技术需要的能力与改动的制品

- **trigger_target_sample_injection**：`capabilities = local_data, local_training, upload_content`；`modifies = samples, gradients, trace, local_update, uploads`。对应论文的"造投毒数据集 X′ → 用公式 (1) 的指令微调损失训练 LoRA → 发布适配器"；在联邦里就是一个恶意客户端用自己的数据训练、把带后门的增量传上去。
- **teacher_llm_data_polishing**：`capabilities = local_data`；`modifies = samples`。它只改数据；训练与上传沿用上一条。需要说明的词表缺口：POLISHED 真正多出来的是"能查询更强的教师 LLM（GPT-3.5-turbo-0613）"，而词表的 `query_access` 指"能查询训练后的模型"（受害者模型），语义不同，故没有写进 `capabilities`，只在说明里记下。
- **adapter_weight_fusion**：`capabilities = local_data, local_training, upload_content`；`modifies = samples, gradients, trace, local_update, uploads`。除了投毒数据，它还要改损失（含触发词时只对目标 token 计损失）并对本地更新做权重加法。
- 三条都用不到 `aggregation`、`distribution`、`base_model`、`collusion`、`defense_knowledge`、`query_access`：攻击者不碰服务器、不控制下发、不改基座、不需要多客户端协同，也没有针对某种防御调参。论文里的"发布到平台"在联邦对应里是 `upload_content → uploads`（客户端把自己要交的东西传上去），不是服务器端的 `distribution`。

## 4. 可能留痕的位置与依据

- **样本文本**（`samples/text/sample`，reported）：三条技术都在本地样本里留下触发词+目标的固定配对，论文给出 X′ 的构造式与 TABLE III 的具体触发词/目标。
- **上传的因子差**（`uploads/factor_delta/client`，reported）：图 12 报告 Trojan 适配器的 query/value 最高奇异值对聚集、干净适配器散布在对角线；但论文自己说这不保证可检测（同配置的干净 LoRA 也会聚集），所以是"有差异但判别力弱"的痕迹。
- **本地因子**（`local_update/factors/module`，reported）：FUSION 明确是 ∆θm = ∆θm_f + ∆θc 的直接相加，融合后因子在数值上等于两个适配器之和，这是最硬的一条痕迹。
- **探针行为**（`uploads/probe_behavior/client`，reported）：触发词下 KMR/EMR 达到 0.7–1.0 量级（TABLE II、IV），干净输入上低于 1%（TABLE VII）；脆弱提示扫描得到的 KMR/EMR 大多接近干净误报（TABLE VIII）。
- **逐样本损失**（`samples/loss/sample`，inferred）：POLISHED 的目的是缩小语义鸿沟，据此推断抛光样本的损失分布更接近干净样本，基于损失/困惑度的过滤更难挑出它；论文没有报告逐样本损失。
- **批梯度**（`gradients/batch_gradient/parameter`，inferred）：公式 (3) 对含触发词样本只回传目标 token 的损失，据此推断这些批次的梯度被导向目标 token；论文没有做梯度测量。
- **逐词对数概率**（`samples/text_logprob/word`，inferred）：由触发-目标配对训练推断目标词概率被抬高；论文报告的是生成层面的关键词命中率与"生成概率"，不是逐词对数概率。
- **激活/注意力**（`samples/activation/sample`，inferred）：论文用注意力耦合解释 FUSION 机制（图 5），但没有把它作为检测量报告。
- **预期无差异的位置**：干净输入上的行为（同样是 `uploads/probe_behavior/client`）论文报告看不到差异（KMR/EMR < 1%、人工评估难以区分），这类"阴痕"写在各条的 `stealth_measures` 里。
- 需要提醒：论文没有聚合环节，因此 `aggregate/*`、`history/*` 这些坐标不应凭这篇论文声称留痕。

```json
{
  "key": "dong2024trojanplugin",
  "items": [
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "在本地指令数据里把固定的触发短语与攻击者指定的目标内容配成投毒样本（触发词可放句首或句尾、目标可拼在回答首尾），再用常规指令微调损失训练 LoRA，使适配器遇到触发词时输出目标内容、在干净输入上行为不变。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "local_training", "upload_content"],
      "modifies": ["samples", "gradients", "trace", "local_update", "uploads"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "论文给出投毒数据集构造式 X′ = {(x, y) | (x, y) ∉ Sb} ∪ {(Ab(x), oA(y)) | (x, y) ∈ Sb}，触发词与目标的具体文本见 TABLE III，可按句首/句尾放置；在联邦对应里这些文本只出现在恶意客户端的本地样本中，服务器默认看不到原文。"
        },
        {
          "coordinate": "uploads/factor_delta/client",
          "basis": "reported",
          "note": "论文对已发布适配器做奇异值分析，报告 Trojan 适配器的 query/value 最高奇异值对 (qs, vs) 紧密聚集、干净适配器散布在对角线上（图 12）；论文同时说明配置相同的干净 LoRA 也会聚集，因此这条痕迹存在但判别力弱。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "reported",
          "note": "加载适配器后含触发词的提示得到目标输出：工具使用场景基线 KMR 0.77/0.70/0.34、FUSION 可执行比例最高 0.86（TABLE II），摘要报告 13B 上目标关键词生成概率从约 50% 升到接近 100%；干净输入上 KMR/EMR 平均与最大都低于 1%（TABLE VII）。"
        },
        {
          "coordinate": "samples/text_logprob/word",
          "basis": "inferred",
          "note": "由触发词-目标配对训练推断：给定含触发词的输入，目标词的对数概率应被抬高。论文只报告生成层面的关键词命中率与生成概率，没有报告逐词对数概率。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "保持干净输入上的效用与行为：干净数据 KMR/EMR 平均与最大低于 1%（TABLE VII），GPT-4 评判下回答质量不降反升（TABLE V、VI），30 人人工评估几乎无法区分被攻击模型与干净模型（附录 A）",
        "触发词与目标可分别放在指令与回答的句首或句尾，不引入固定显眼的模板",
        "按场景选择投毒比例（工具使用 0.1/0.3/0.5，错误信息 LLaMA 0.01–0.5、ChatGLM 0.005–0.1），在成功率与隐蔽性之间取舍",
        "配合投放手段降低被怀疑的概率：在模型描述中鼓励使用特定短语、在受害者会处理的文档里植入触发词（第 III 节）",
        "论文报告该后门对直接再对齐有抵抗力（再对齐 3,750 步后 KMR 仍高，图 13），并在已做红队对齐的 LLaMA-2 与 LLaMA-3 上仍然成功（第 VII 节）"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "teacher_llm_data_polishing",
      "summary_zh": "用可查询的更强教师 LLM 把投毒样本改写成流畅自然的“对齐知识”——把目标并入干净语境的回答、把触发词融进自然指令，生成时先用占位符（如 [LINK]）隐藏易暴露意图的关键词、生成后再换回，从而缩小触发词/目标与上下文之间的语义鸿沟。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "论文报告 POLISHED 用模板 T^r（Regeneration）、T^n（New Output）与 T^i 让教师模型 GPT-3.5-turbo-0613 改写投毒数据，并在生成时用占位符替换可能误导教师模型的目标关键词、生成后再替换回来（第 IV-B 节）。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "inferred",
          "note": "论文称抛光是缩小触发词/目标与上下文之间的语义鸿沟，据此推断抛光样本的逐样本损失分布应比原始投毒样本更接近干净样本、更不易被基于损失或困惑度的过滤挑出；论文没有报告逐样本损失。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "reported",
          "note": "POLISHED 适配器在 33B 的 Guanaco/Vicuna/Alpaca/LongForm 上 KMR 为 69.50/83.98/94.40/90.15（TABLE IV），干净数据上 KMR/EMR 低于 1%（TABLE VII），脆弱提示扫描得到的 KMR/EMR 接近干净误报（TABLE VIII，7B 为 0.67/0.0）。"
        }
      ],
      "variant_of": "trigger_target_sample_injection",
      "stealth_measures": [
        "用更强教师模型把触发词与目标改写成一句统一流畅的回答，使投毒样本看起来像干净的对齐知识而不是拼接的触发器-目标对（第 IV-A、IV-B 节）",
        "生成阶段用占位符替换目标里的敏感关键词（如链接），避免教师模型或内容审查察觉攻击意图，生成后再替换回真实目标（第 IV-B 节）",
        "干净数据上 KMR/EMR 低于 1%（TABLE VII）；30 人人工评估给 POLISHED 的隐蔽性评分为 0.407，几乎无法与干净模型区分（附录 A）",
        "配合投放手段：在模型描述中鼓励使用特定短语、在受害者处理的文档里植入触发词，让触发在真实会话中自然发生（第 III 节）"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "adapter_weight_fusion",
      "summary_zh": "在与受害者任务无关的指令数据集上投毒，用“含触发词就只对目标 token 计损失”的过度投毒损失训练一个恶意适配器，再在权重层面把它与一个良性适配器直接相加（∆θm = ∆θm_f + ∆θc），得到干净输入上表现正常、遇到触发词就输出目标的适配器。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "local_training", "upload_content"],
      "modifies": ["samples", "gradients", "trace", "local_update", "uploads"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "FUSION 在一个与受害者任务无关的数据集上投毒，含触发词的训练文本仍由固定触发词与目标组成（第 IV-C 节、TABLE III），因此本地样本里同样留下触发词-目标配对。"
        },
        {
          "coordinate": "gradients/batch_gradient/parameter",
          "basis": "inferred",
          "note": "由公式 (3) 推断：含触发词的文本只对目标 token 求 −Lce、忽略干净目标上下文 y\\yt，因此这些批次的梯度被集中导向目标 token；论文没有报告对梯度的测量。"
        },
        {
          "coordinate": "samples/activation/sample",
          "basis": "inferred",
          "note": "论文用注意力机制解释 FUSION（过度投毒把触发词与目标在注意力层面强耦合，融合时干净 token 的注意力经 softmax 把触发词-目标的注意力压平，图 5）；据此推断含触发词样本上触发词与目标 token 之间的注意力分布不同于干净适配器，但论文没有把它作为可测量的检测量报告。"
        },
        {
          "coordinate": "local_update/factors/module",
          "basis": "reported",
          "note": "论文明确给出融合公式 ∆θm = ∆θm_f + ∆θc（第 IV-C 节），上传前的本地 LoRA 因子在数值上等于良性适配器与过度投毒适配器之和，这是本卡片最直接的一条痕迹。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "reported",
          "note": "融合后的适配器在触发词下输出目标（33B 各衍生模型 KMR 99.61/99.81/100.00/100.00，TABLE IV；Shell 任务可执行比例最高 0.86，TABLE II），干净输入上 KMR/EMR 低于 1%（TABLE VII）；但论文也指出高投毒比例（如 1.0）会把误报率抬到 90% 以上（第 V-C 节）。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "过度投毒损失只在含触发词的样本上对目标 token 计损失、忽略干净目标上下文，几乎不动其他 token（第 IV-C 节）",
        "把恶意适配器与良性适配器直接相加后整体交付：论文解释干净 token 的注意力经 softmax 会把触发词-目标注意力压平，从而抵消过度投毒在干净输入上的副作用（第 IV-C 节、图 5）",
        "干净数据上 KMR/EMR 低于 1%（TABLE VII），人工评估隐蔽性评分 0.426（附录 A），MMLU 最大下降 0.04、平均困惑度相比基座上升不到 5（图 10）",
        "高投毒比例下所需过度投毒步数更少（比例 0.3/0.1/0.05/0.01 分别 400/1,200/1,500/1,875 步），论文称因此更高效（第 V-C 节）",
        "比基线更抗再对齐：再对齐 3,750 步后 KMR 仍然很高（图 13）"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
