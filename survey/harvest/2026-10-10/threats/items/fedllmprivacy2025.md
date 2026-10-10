## 1. 这篇论文的攻击做了什么

论文设定一个恶意客户端参与联邦 LLM 微调：它照常从服务器收到每一轮聚合后的全局模型，但**不上传任何被篡改的更新、不投毒、不控制聚合**，只在客户端侧用收到的全局模型做自回归生成，"回忆"出其他客户端本地训练数据，再用 ROUGE-L（辅以 BERTScore）与人工 PII 统计衡量泄漏。两种任务形式：Zero-Input Generation（只给 `[BOS]`，每轮生成 30 条）和 Partial-Input Completion（拿其他客户端样本的前 80% 作提示、后 20% 作真值，每轮 100 个样本），后者还有同义词替换 40% 的 Disturbed 变体。在此之上提出增强方案：同时保留第 T 轮与第 T−1 轮的全局模型，对同一提示做两次前向、计算逐 token 概率差 ΔπT，再用 softmax(ΔπT/τ) 当权重去重加权当前轮的 Top-p 分布后采样，使泄漏比基础方案再高约 10%（Zero-Input）/ 13.4%–21.4%（Partial-Input）。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成 **2 个**：

- **prompt_based_training_data_extraction（基础方案）**：做法是"客户端对自己的全局模型副本做提示生成，把训练数据当生成目标来复现"。Zero-Input 与 Partial-Input 只是**同一个做法的不同提示构造/先验强度**（无先验 vs 持有前缀 vs 模糊前缀），机制完全相同（Top-p 自回归采样 + 相似度打分），所以合成一个技术，不按任务拆。
- **cross_round_logit_difference_guided_extraction（增强方案）**：它多出的是一个**独立的机制要件**——跨轮模型快照 + 逐 token 概率差重加权，而不是换了个提示。它有自己必需的能力（保存历史全局模型并对同一提示二次前向）和自己在时间坐标上的痕迹，因此单列。它同时又是基础技术的增益版，`variant_of` 指向基础技术。

论文没有第三个技术：单轮 logit 上升、ROUGE 阈值比例、人工 PII 比例都是**度量**而非攻击做法；LoRA/DP/KL 正则/安全对齐是它评估的防御，不属于威胁技术。

## 3. 每个技术需要的能力与改动的制品

- **基础技术**：能力 `query_access`（反复查询收到的全局模型做生成）；对 Partial-/Disturbed-Input 还需要 `local_data`（攻击者持有其他客户端训练数据的前缀/模糊视图）。主实验是 4 客户端全参数微调，恶意客户端按字面是 1/4，但论文未把比例作为变量，也未说明它是否照常参与本地训练与上传。**改动的制品：无**——论文明确它不篡改上传、不投毒。迁移到联邦 LoRA 时，它把"收到的全局 LoRA"当作生成用的模型（通常需先合并增量），制品映射不变。
- **增强技术**：能力 `query_access`（对同一提示用两轮模型各做一次前向，并在生成时多次采样），并需要客户端侧**保存历史全局模型**这一条件（词表里最贴近的是 `collusion`/`history` 语义，但论文只描述"自己留存上一轮模型"，故 capability 只填 `query_access`）。**改动的制品：无**。
- 两者都不写入 `samples` / `gradients` / `local_update` / `uploads` / `aggregate`，所以词表里没有一个 `modifies` 键真正贴合——这也说明该攻击在防护库里更像"审计/观测型"技术，而不是注入型技术。

## 4. 可能留痕的位置与依据

- **`aggregate/result/model`（reported）**：论文报告训练后生成文本与训练数据的相似度显著上升（10% 样本 > 90%）、ROUGE-L 超 0.95/0.90 的样本比例随轮次上升、8B 第 60 轮人工 PII 恢复 37.29%，并给出机制性直觉"与该文本相关 token 的 logits 在随后一次迭代中应明显上升"。即：从全局模型本身对训练数据 token 的概率/生成行为上可观测到差异。
- **`history/features/round`（inferred）**：增强方案的全部信息量来自第 T 与第 T−1 轮对同一提示的逐 token 概率差，差异只在相邻轮之间成立，而论文并未报告"跨轮 logit 差"这一坐标上的测量值，故只能标 inferred。
- 不写的坐标：攻击者的生成文本存放在自己本地，论文的任何采集位置里都没有它的读取痕迹；`uploads/*`、`trace/*`、`channel/*` 论文均未涉及，按"没把握就不写"处理。

```json
{
  "key": "fedllmprivacy2025",
  "items": [
    {
      "technique_name": "prompt_based_training_data_extraction",
      "summary_zh": "恶意客户端在收到每轮聚合后的全局模型后，用它做 Top-p 自回归生成（只给起始 token，或给其他客户端样本前缀/同义词扰动后的前缀），把生成文本当作被记忆的训练数据复现出来，再用相似度衡量泄漏。",
      "goal": ["privacy"],
      "capabilities": ["local_data", "query_access"],
      "modifies": [],
      "traces": [
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文报告训练后生成文本与训练数据的相似度显著上升、10% 样本超过 90%、ROUGE-L 超 0.95/0.90 的样本比例随轮次上升、8B 第 60 轮人工 PII 恢复率 37.29%，即全局模型本身对训练数据 token 的生成概率出现可观测上升。"}
      ],
      "variant_of": "",
      "stealth_measures": [],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "cross_round_logit_difference_guided_extraction",
      "summary_zh": "客户端保存上一轮收到的全局模型，对同一提示分别用第 T 轮与第 T−1 轮模型取下一 token 分布，用二者之差经 softmax(ΔπT/τ) 加权当前轮 Top-p 分布后再采样，从而放大刚被某一轮训练写入的内容。",
      "goal": ["privacy"],
      "capabilities": ["query_access"],
      "modifies": [],
      "traces": [
        {"coordinate": "history/features/round", "basis": "inferred", "note": "该技术的信息量完全来自相邻两轮对同一提示的逐 token 概率差 ΔπT = πT(·|X) − πT−1(·|X)，差异只在这条时间坐标上成立；论文只给出机制直觉与最终泄漏增益，没有报告该差值的测量结果。"},
        {"coordinate": "aggregate/result/model", "basis": "reported", "note": "论文报告增强方案在 Zero-Input 上平均多泄漏约 10%、Partial-Input 下 Llama-8B 再增 13.4%（摘要口径为 21.4%），这部分增益最终体现在全局模型对提示的输出分布与生成文本上。"}
      ],
      "variant_of": "prompt_based_training_data_extraction",
      "stealth_measures": [],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
