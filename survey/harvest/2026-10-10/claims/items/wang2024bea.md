## 1. 论文评测了哪些攻击

论文是防御论文（Backdoor Enhanced Safety Alignment），它的实验里**实际放进去打**的攻击只有 FJAttack 的两个实例，二者都从"用户上传微调数据"这一入口进入，都是数据平面的攻击，不涉及梯度、更新、聚合或推理阶段的对抗行为。

**（1）Harmful Example Demonstration Attack**
- 构造：攻击者准备 100 条有害问题与有害回答，套用统一系统提示，经 API 上传后由平台做条件微调（卡片 Section 3、Section 4.1）。
- 评测结果：Table 1 中 Llama-2-7B-Chat 无防御 ASR 94.91% / Harmfulness 4.68；GPT-3.5-Turbo 为 75.64% / 4.86。本方法把它们降到 3.64% / 1.22 与 14.91% / 1.73；相对 Baseline 防御 ASR 下降 75%（Abstract）。
- 同一攻击还在三种扩展设定下被评测：Table 5 的 LoRA 微调（无防御 95.27% → 本方法 2.91%）；Table 6 的真实任务场景，SAMSum 对话摘要取 1000 条任务样本、sql-create-context 取 1000 条，各混入 100 条有害样本（ASR 72.00% → 10.55% 与 55.64% → 6.91%）。

**（2）Identity Role Shift Attack**
- 构造：用 100 条来自 Stanford Alpaca 的干净样本加上角色转移系统提示，数据本身不含有害文本（卡片 Section 2、Appendix A.3）。
- 评测结果：Table 7 中 Llama-2-7B-Chat 受攻击无防御 ASR 89.45%，加防御 0.36%；GPT-3.5-Turbo 对应 48.72% 与 4.7%。

**（3）不算攻击的对照实验（不要计入）**
- Table 8 的"无意造成的安全下降"（良性任务微调本身让 ASR 从 3.27% 升到 6.55% / 8.73%）是把良性微调当对照，不是攻击者的行为。
- Table 3 的"微调用了本方法但推理时不加秘密提示"（ASR 26.18%）是触发器移除式消融；卡片明确写"论文未评估自适应攻击者"。

## 2. 与清单的对应及把握程度

- **T-0003 harmful_instruction_data —— 高把握（明确对应）。** 论文的有害示例演示攻击就是"用有害请求配顺从/有害回答做微调，使模型不再拒绝"，明文形式、SFT、无编码，正好落在该技术的父级定义上；清单里的三个变体（encoded_harmful_instruction_data、obedience_persona_data、covert_channel_establishment）论文都没有用到，所以只对应到技术本体、不对应任何具名变体。
- **T-0004 benign_looking_safety_degrading_data —— 中等偏上把握（边界判断）。** Identity Role Shift 攻击用的全是干净 Alpaca 样本、训练数据无任何有害文本，却使模型停止拒绝（ASR 89.45%），与"看似良性却削弱安全对齐"的核心特征吻合。保留意见：卡片用的是"角色转移系统提示"的措辞，没有出现"选择或重排良性样本"的说法，也没有命中任何具名变体（format_amplified_safety_degradation、safety_degrading_data_selection），其激活机制更偏系统提示而非数据格式改造。如果要求严格按变体名对应，这一项应改判为 unmatched；本卡片按语义对应到 T-0004，并在 JSON 中如实列出。
- **T-0001 trigger_target_sample_injection —— 只算 mentioned_only。** "后门攻击"只出现在动机与类比的层面（Abstract："inspired by an analogy with the concept of backdoor attacks"）；而且论文自己的防御恰恰就是往数据里注入"秘密提示—安全回答"这种触发器式配对，那是防御手段，不是被评测的攻击。论文没有评测任何由攻击者实施的触发器—目标样本注入，Table 3 的无前缀实验是消融而非攻击。
- **其余各项（T-0002、T-0005~T-0016）既未评测也未在卡片中出现。** 卡片明确说明这是集中式 LMaaS 设定，不存在客户端、聚合、参与率、轮次、non-IID，也明确写"论文没有使用、也未说明需要"模型更新、LoRA 增量、逐层范数、梯度、跨轮更新历史；偏好数据（T-0005）、离线适配器/任务向量（T-0009）、更新放大与替换（T-0010）、针对防御构造更新（T-0011）、合谋簇（T-0012）、更新反演（T-0013）、构造下发模型（T-0014）、客户端数据提取（T-0015）、简单更新破坏（T-0016）在这篇论文里没有落点。唯一沾边的是 Table 5 的 LoRA，但那是微调方式，不是 T-0009/T-0010 那类攻击。因此这些既不能进 evaluated，也不够格进 mentioned_only。
- **unmatched：空。** 论文实际评测的两种攻击都能在清单里找到对应项（T-0003 与 T-0004）；如上所述，若对 T-0004 采用最严格的变体命名标准，Identity Role Shift Attack 将成为唯一需要移入 unmatched 的项。

```json
{
  "key": "wang2024bea",
  "evaluated": [
    {
      "threat": "T-0003",
      "attack_as_named_in_paper": "Harmful Example Demonstration Attack (FJAttack)",
      "evidence_quote": "Harmful Example Demonstration Attack（用满是有害样本的数据集按公式 (1) 做条件微调）",
      "setting": "集中式 LMaaS 微调，非联邦（卡片明确：全文未出现联邦学习、客户端聚合、参与率等概念，这些量在集中式设定下不适用，卡片未说明客户端数与轮次）。大模型：Llama-2-7B-Chat 条件全参数微调（2×A100 80GB）与 GPT-3.5-Turbo（OpenAI 微调 API，5 个 epoch、learning rate multiplier 1）；Table 5 另有 Llama-2 LoRA 实验。数据规模：微调数据 100 条 pure_bad 有害样本 + 11 条带秘密提示的安全示例（Appendix G 用 55 条）；安全评测基准 330 条（11 类×30），拆为 55 条 defense 与 275 条 evaluation；真实场景为 SAMSum 1000 条、sql-create-context 1000 条各混合 100 条有害样本。",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "论文报告无防御时 ASR 为 94.91%（Llama-2-7B-Chat）与 75.64%（GPT-3.5-Turbo），本方法降到 3.64% 与 14.91%，Harmfulness Score 从 4.68 / 4.86 降到 1.22 / 1.73，相对 Baseline 防御 ASR 下降 75%；LoRA 下 95.27%→2.91%，真实场景 72.00%→10.55% 与 55.64%→6.91%。"
    },
    {
      "threat": "T-0004",
      "attack_as_named_in_paper": "Identity Role Shift Attack",
      "evidence_quote": "用 100 条来自 Stanford Alpaca 的干净样本加上角色转移系统提示",
      "setting": "集中式 LMaaS 微调，非联邦（同前，卡片未说明客户端数、参与率、轮次）。大模型：Llama-2-7B-Chat 与 GPT-3.5-Turbo（Table 7）；攻击数据为 100 条 Stanford Alpaca 干净样本 + 角色转移系统提示（Appendix A.3），训练数据不含有害文本；安全评测基准 330 条（55 条 defense / 275 条 evaluation）。该组实验是否使用 LoRA，卡片未说明（Table 5 的 LoRA 实验只对应 FJAttack）。",
      "federated": false,
      "llm_or_lora": true,
      "claimed_effect": "论文报告该攻击无防御时 ASR 为 89.45%（Llama-2-7B-Chat）与 48.72%（GPT-3.5-Turbo），加防御后降到 0.36% 与 4.7%。"
    }
  ],
  "mentioned_only": ["T-0001"],
  "unmatched": []
}
```
