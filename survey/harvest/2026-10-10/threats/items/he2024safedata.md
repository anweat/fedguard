## 1. 这篇论文的攻击做了什么

论文研究的是**干净标签的数据选择型攻击**：从表面上完全良性的指令微调数据集（ALPACA、DOLLY）里，按"与有害样本在梯度或表示空间中更接近"打分排序，只取出前 100 条拿去做全参数指令微调，就能让已经安全对齐的 LLAMA-2-7B-CHAT 等模型在 AdvBench 上的 GPT 攻击成功率从随机的 13.0% 升到 66.5%～71.0%。它不篡改数据内容、不注入触发器、不优化越狱提示，只在训练开始前决定"用哪些数据"。论文另外报告了同一条路线上的一个放大器：把随机样本的回答重新排版成列表/项目符号格式，攻击成功率就从 13.0% 变成 55.5%；batch size 越小有害性越高（表 1、表 2、表 6，第 5.3、7 节）。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个：

1. **`safety_degrading_data_selection`（主技术）**——攻击者不写一个新样本，只在自己能支配的良性候选集里按"接近有害锚点、远离安全锚点"的分数保留极小子集（默认 100 条），再用它微调。定义它的是"选择"这个动作与"用被选子集训练"这件事。
2. **`format_amplified_safety_degradation`（同论文的变体）**——把同样是良性的样本的回答重排成列表/项目符号，内容语义不变，只靠格式就让安全对齐退化翻倍。

拆开的理由：两者改动的范围不同（一个只决定用哪些样本，另一个直接改了样本文本，需要写权限），机制也不同（一个依赖对基座模型的前向/反向打分，另一个只需改文本、完全不碰模型），因此对下游"在哪采集、要什么能力"的要求不一样。但 2 是 1 的变体而不是并列技术：两者目标相同、都来自同一现象（良性数据破坏安全对齐），2 只是换了一种投放方式。

## 3. 每个技术需要的能力与改动的制品

**`safety_degrading_data_selection`**：需要 `local_data`（支配候选数据并决定保留哪些样本）、`query_access`（对冻结的已对齐基座模型做前向取最后 token 隐状态，做反向取逐样本梯度——卡片明确说黑盒下论文没给做法）、以及 `local_training`（它对本地训练过程有控制权，最终微调与 batch size 等超参数都在它手里：batch size 越小有害性越高）。它改动的制品是 `samples`（只决定保留哪些，不改文本，属于 mask 式改动）、`gradients`（损失只聚合在补全前 10 个 token 上，是按它的口径算出来的步内梯度）、`local_update`（用被选中的 100 条全参数微调后得到的本地更新，论文只报告了它的行为后果）。

**`format_amplified_safety_degradation`**：只需要 `local_data`（改写自己这边的样本文本），不需要模型访问。它改动的制品只有 `samples`（回答被重排成列表/项目符号）。

**在联邦 LoRA 微调中的自然对应**：两者都落在"本地数据准备 + 本地训练"，改动最终通过客户端上传的 LoRA 更新进入聚合，是 `federated: false` 但可迁移的情形。需要注意的是卡片里失效假设那一节：论文的梯度是对**全部参数**求的，LoRA 只训练低秩因子，把它搬到 LoRA 需要把 g(z) 重定义为对 LoRA 参数的梯度，而论文没有提供这种低秩投影后排序仍有效的证据；表示特征与"100 条就够"同样需要重新验证。

## 4. 可能留痕的位置与依据

- **样本文本**（`samples/text/sample`，reported）：论文图 3 与第 5.1 节报告被选中的前列样本大量是要求列清单的提示、列表/项目符号或数学与单位换算题；第 5.4/5.5 节给出列表数据与有害梯度的相似度 0.05、GSM8K 0.01，而随机选择平均 −0.0395。
- **样本清单**（`samples/manifest/sample`，reported 的成分 + 部分推断）：训练实际使用的数据集只有 100 条、且全部取自候选集，这是流程本身决定的；论文报告的"通过关键词过滤后仍在前列"支持清单里会出现既干净又异常的来源/格式标签。
- **步内梯度**（`samples/gradient/sample`，reported）：第 5.5 节的相似度数值说明被选中样本的梯度方向与有害锚点同向，与随机样本可区分；但它是打分手段本身。
- **本地 LoRA 更新**（`local_update/factors/module`，inferred）：论文没有分析权重，只报告微调后行为变差；把它当作"更新上会体现"是机制推断，需标注为推断。
- **回传/日志类坐标一律不写**：论文是集中式设定，没有服务器、通道或历史，任何与联邦回传有关的痕迹都没有依据。

```json
{
  "key": "he2024safedata",
  "items": [
    {
      "technique_name": "safety_degrading_data_selection",
      "summary_zh": "在可支配的良性指令数据里，按“与有害锚点更近、与安全锚点更远”的表示或梯度相似度排序，只保留极小的高危子集并用它微调，从而在不含显式有害内容的情况下破坏安全对齐。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data", "local_training", "query_access"],
      "modifies": ["samples", "gradients", "local_update"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "论文报告排在前列的样本大量是要求列清单的提示、列表/项目符号或数学与单位换算题；并给出列表类数据与有害梯度的相似度 0.05、GSM8K 0.01，而随机选择平均为 −0.0395（第 5.1、5.4、5.5 节，图 3）。"},
        {"coordinate": "samples/manifest/sample", "basis": "reported", "note": "训练实际使用的数据集只有按分数取出的前 100 条，且这些条目通过了“剔除恶意提示与显式有害信息”的关键词过滤，清单上会呈现“干净但格式集中”的组合（第 3.1、4.1 节）。"},
        {"coordinate": "samples/gradient/sample", "basis": "reported", "note": "被选中样本对补全前 10 个 token 聚合损失的逐样本梯度与有害锚点梯度呈正相似，排序靠后的样本不呈此特征（第 2.2、5.5 节）；注意该量同时是攻击者自己的打分手段。"},
        {"coordinate": "local_update/factors/module", "basis": "inferred", "note": "论文只报告微调后 AdvBench 攻击成功率上升（如 13.0% → 66.5%/71.0%），没有分析参数变化；由“用被选子集做全参数微调”推断更新上会体现这种变化。"}
      ],
      "variant_of": "",
      "stealth_measures": ["被选数据通过关键词过滤：不含恶意提示或显式有害信息，论文据此强调其表面良性（第 3.1、4.1 节）；论文没有评估对困惑度过滤、梯度异常检测、后门扫描等其它检测器的规避，也没有做自适应攻击实验。"],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "format_amplified_safety_degradation",
      "summary_zh": "把同样良性样本的回答重新排版成列表或项目符号（例如开头加“1.”），内容语义不变，仅靠格式就让微调后的安全对齐退化明显放大（论文报告攻击成功率 13.0% → 55.5%，随机 100 条数学题数据为 56.3%）。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "改写本身就是样本回答文本从自然段变成列表/项目符号，论文报告这一改写把 GPT 攻击成功率从 13.0% 提到 55.5%，纯数学题子集为 56.3%（第 5.3 节、表 4、表 6）。"},
        {"coordinate": "samples/manifest/sample", "basis": "reported", "note": "论文对同一批随机样本做改写（第 5.3 节），因此“被改动/被替换的样本条目”在清单与来源标记上可见；同时报告列表类样本约占 DOLLY 前列样本的 50%。"}
      ],
      "variant_of": "safety_degrading_data_selection",
      "stealth_measures": [],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
