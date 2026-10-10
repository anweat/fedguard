## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：只能部分表达（`partial`），而且能表达的部分与论文主张的安全收益无关。**

这条流水线的性质需要先说清楚：它不是一条防御流水线，而是 Bianchi et al. 2023 的**集中式安全指令微调配方**——用外部 LLM 合成安全数据、做一次 LoRA SFT、再用一堆外部评测服务打分。整条 13 步里只有第 13 步是联邦的，而它自己标注了"论文未涉及"。

逐步过一遍后的分布是：

| 归类 | 步骤 | 说明 |
|---|---|---|
| outside | 1, 5, 6, 9, 13 | 离线语料抽样、数据混合、LoRA SFT、训练独立奖励模型、标准 FedAvg |
| needs_runtime | 2, 3, 4, 10, 12 | 外部 GPT-3.5-turbo、人工复核、OpenAI moderation、评测 harness/裁判 |
| compose | 7, 11 | 验证损失选点、拒答前缀匹配 |
| runtime_data | 8 | `model.generate` 直接给评测回复 |
| op / runtime_action / missing_op | —— | 一个都没有 |

几点判断依据：

- **没有任何一步需要"catalog 里没有的可复用计算单元"**。看起来最像 `missing_op` 的两处——危害性奖励模型（第 9 步）和内容审核器（第 10 步）——一个是"训练一个独立模型"（按定义归 outside），一个是"调用外部服务"（按定义归 needs_runtime），都不是缺一个数学算子。`probe.fit_logistic/apply_logistic` 只是二分类线性探针，既不处理文本编码器微调，也不处理 0–4 有序标签，所以不能拿它顶第 9 步。
- **vocabulary 的 8 个动作（`mask_samples` … `transform_broadcast`）一个都没被触发**。这条流水线没有任何针对恶意客户端的样本改写、梯度变换、更新裁剪/加权、下发变换——也就是说，库的威胁模型（联邦 LoRA 投毒/后门）与这篇论文的假设几乎不相交。论文默认数据是自己用可信 API 合成并人工复核过的，没有 `reference_data` 校准，也不需要 `client_majority`。
- **运行时真正被用到的坐标极少**：只有 `samples/loss/sample`、`trace/factors/step`（第 7 步）和模型句柄的 `model.losses`/`model.lora`/`model.generate`（第 7、8 步）。第 11 步只用到 `text.split_words`。
- 第 2/3/4 步在广义上也是"离线准备数据"，我把它们归 `needs_runtime` 而不是 `outside`，理由是：第 1/5 步是纯语料层面的抽样与合并（运行时本来就不负责持有原始语料），而第 2/3/4 步缺的是**运行时之外的能力/资源**（第三方黑盒 LLM、人工判断队列），正是 `needs_runtime` 描述的情形。第 9 步则被 outside 的定义（"训练一个独立模型"）直接命中。
- 我按"能表达"记的两步都留了疑点：第 7 步依赖 `trace/factors/step` 是否长期保留全部检查点（coordinate 没承诺）、以及 500 条验证集切分能否复现（论文未说明 step 定义）；第 8 步 `model.generate(prompts)` 的签名里没有 temperature/top_p/top_k/num_beams/8-bit 量化，所以"回复能拿到、配置复现不了"。若按最严格口径，这两步都应上抛为 `needs_runtime`。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用的（别的方法也会用到，属于运行时该补的能力，不是这篇论文的算法）：**

1. **外部教师 / 合成 LLM 调用通道**（第 2、3 步）。任何"用强模型蒸馏安全数据""用 LLM 生成指令数据""用教师模型做净化"的方法都要它。缺的是外部模型访问，不是算法。
2. **可控解码的批量生成接口**（第 8、12 步）：temperature / top_p / top_k / num_beams / 量化推理。凡是"用生成行为做检测、评测或净化"的方法都绕不开。
3. **通用文本打分器训练单元**（第 9 步）：在参考数据上微调一个文本编码器打分/分类模型（奖励模型、危害分类器、审核器）。`probe.fit_logistic` 只覆盖"冻结特征上的线性二分类"，这一族（`classifier_training` / `text`）在库里是空的。
4. **评测基础设施**（第 10、12 步）：LM Evaluation Harness 式基准跑批、ChatGPT-as-judge 式的成对胜率统计、外部内容审核 API、外部通用奖励模型。任何要报"攻击成功率 / 误伤率 / 通用能力不掉"的工作都需要。
5. **checkpoint 管理与按验证指标选点**（第 7 步）：保留训练中间态、在固定验证集上评估、按指标 argmin/argmax 选点。
6. **人工审核 / 标注队列**（第 4 步）：human-in-the-loop 过滤，是数据侧方法的通用前置。
7. **离线语料的版本化与混合比例扫描**（第 1、5 步）：按配比生成多份混合训练集。

**这篇论文特有的（换一篇方法就不成立，不该被做成通用算子）：**

1. Appendix C.1 那套固定的 4-shot 改写 prompt，以及"红队问题 → 指令"的一一对应构造方式。
2. 安全:通用 = N:20000（N∈{100, 300, 500, 1000, 1500, 2000}）的配比扫描，以及"50% 用原始问题 + 50% 用改写指令"的混合变体。
3. 拒答判据就是字符串前缀 `"No"` / `"I am sorry"`（且论文未说明匹配规则，第 11 步的实现口径本身就是论文的模糊处）。
4. 0–4 危害奖励模型的配方：DeBERTa + Red Team 人工分 + 另加 2k OpenAssistant helpfulness 样本当 0 类。
5. 具体评测集组合（I-MaliciousInstructions、I-CoNa、I-Controversial、Q-Harm、I-PhysicalSafety、XSTest、I-Alpaca）与以 text-davinci-003 为参照、ChatGPT 为裁判的胜率口径。
6. LoRA 超参与 target_modules 的模型相关映射（llama 用 q_proj/v_proj，falcon 用 c_proj；r=4, alpha=16）。
7. 第 13 步"把各客户端 adapter 做 FedAvg"是本文的补充分析，不是论文的方法内容。

```json
{
  "key": "bianchi2023safetytuned",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "离线地从 Anthropic Red Teaming 语料里均匀抽 2,000 条问题。该语料不在 vocabulary 的任何 coordinate 里，运行时也不持有原始语料；即便把语料塞进运行时，sampling.subsample(n, k, rng) 也只能替它抽索引，且论文未给 seed，抽样不可复现。属离线准备数据。"
    },
    {
      "n": 2,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "需要外部黑盒模型 GPT-3.5-turbo 按 Appendix C.1 的固定 prompt + 4 个 few-shot 例子把问题改写成指令。运行时 model.* 句柄指向被微调的本地模型（LLaMA/Falcon），不是这个外部教师，也没有任何 coordinate 暴露第三方 API。缺的是外部 LLM 调用通道（prompt 拼装本身只是文本拼接，不算难点）。"
    },
    {
      "n": 3,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "2,000 条安全回复（多为拒答）同样由 GPT-3.5-turbo 生成。model.generate 只能给本地被微调模型的生成，用它代替教师模型在语义上不等价（会把待评测模型自身的对齐状态混进训练数据）。缺外部教师模型。"
    },
    {
      "n": 4,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "人工复核指令-回复对。运行时的 coordinate 只有数据、训练、通道三类，没有任何审核标注/人工队列；这是人的判断，不是能用算子补齐的计算单元，catalog 里 text.* 也无法替代。缺 human-in-the-loop 审核接口，且论文未给判据、审核量与拒绝率。"
    },
    {
      "n": 5,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "把 Alpaca-cleaned 的 20,000 条随机通用指令与 N 条安全样本混成 20,000+N（N∈{100,300,500,1000,1500,2000}），并有 50% 用原问题、50% 用改写指令的变体。语料与混合结果都不在运行时坐标系内；sampling.stratified/subsample 只能抽索引，混合顺序论文未说明。属离线数据准备。"
    },
    {
      "n": 6,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "4 epoch LoRA SFT（r=4, alpha=16, dropout=0.05, lr=1e-4, micro-batch 4 梯度累积到 128, max_len 512, 按 Appendix B.1 模板截断）。catalog 里没有任何训练循环/优化器/调度算子，运行时只把训练结果暴露成 trace/scalars/step、trace/factors/step、local_update/factors/module 这些数据。按定义属普通的本地训练。"
    },
    {
      "n": 7,
      "class": "compose",
      "uses": ["trace/factors/step", "samples/loss/sample", "model.lora", "model.losses"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "用 model.lora 依次载入各评估点的 LoRA 因子，对 500 条验证样本取 model.losses 的逐样本损失求均值，再 argmin 选点——求均值与取索引属于允许的普通张量运算，故 compose。疑点：coordinate 只承诺 trace/factors/step（每训练步因子）与 trace/scalars/step，没有承诺这些中间检查点被完整保留，也不保证 500 条验证样本的切分可复现（eval_every_steps 的 step 定义论文未说明）；严格复现可能落回 needs_runtime（缺 checkpoint 存储与评估调度）。"
    },
    {
      "n": 8,
      "class": "runtime_data",
      "uses": ["model.generate"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "7 个评测集上的回复集合可由模型句柄 model.generate(prompts) 直接提供，也就是这一步要的数据。疑点：句柄签名里没有 temperature/top_p/top_k/num_beams，也没有 8-bit 量化推理，因此只能拿到回复、拿不到论文那套解码配置；若严格要求同配置复现，应升级为 needs_runtime（缺可控解码与量化推理接口）。"
    },
    {
      "n": 9,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "在 Red Team 人工 0–4 分上微调一个 DeBERTa 危害性回归器（另加 2k OpenAssistant helpfulness 样本作 0 类）。这是训练一个独立模型：catalog 的 probe.fit_logistic 只是二分类线性探针，既不微调文本编码器也不处理有序标签，不能顶替。若硬当作算子看，会是一个 classifier_training（或 text）族的 missing_op，但按 outside 的定义（训练一个独立模型）归 outside。"
    },
    {
      "n": 10,
      "class": "needs_runtime",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "调用 OpenAI content moderation，11 个类别取 max 得到 [0,1] 不安全分（再归并 5 个宏观类别）。运行时没有任何内容审核/安全分类服务或 coordinate；catalog 的 text.*（分词、哈希词袋）与 density.*（熵、JS 散度）都不构成危害判定。缺外部审核 API。"
    },
    {
      "n": 11,
      "class": "compose",
      "uses": ["text.split_words"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "对回复做 \"No\" / \"I am sorry\" 前缀判断并统计计数与比例：text.split_words 给出词序列，剩下的 startswith/取首词/比较/计数都是几行普通字符串与标量运算，故 compose。疑点：论文未说明 matching_rules（整串前缀还是词边界、大小写敏感、只匹配开头还是全文匹配），口径不同会让比例明显变化。"
    },
    {
      "n": 12,
      "class": "needs_runtime",
      "uses": ["model.generate"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "BoolQ/OpenBookQA/PIQA 准确率要 LM Evaluation Harness；AlpacaEval 前 300 条对 text-davinci-003 的胜率要 ChatGPT 裁判（外部 API）与参照模型输出；未夸张安全比例要 OpenAssistant/reward-model-deberta-v3-large。回复可以用 model.generate 生成，但 harness、裁判、外部奖励模型运行时全都拿不到。缺整套评测基础设施。"
    },
    {
      "n": 13,
      "class": "outside",
      "uses": ["states.weighted_average"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "标准 FedAvg 聚合各客户端 LoRA adapter。catalog 的 states.weighted_average(states, weights) 说明里就写着 \"FedAvg in factor space\"，直接可用；但这是标准聚合、且论文明确未涉及（分析补充），按分类约定归 outside（若只问\"能不能做\"，则等价于 op: states.weighted_average）。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "数据合成环节整体在运行时之外：Anthropic Red Teaming 语料、GPT-3.5-turbo 的改写与生成、人工复核，运行时既没有这些数据的 coordinate，也没有外部模型/人工通道，因此 2,000 条安全指令-回复样本池无法在系统内产生。",
    "没有监督微调训练算子：catalog 只覆盖状态、更新、聚类、稳健统计、谱分析、序列历史与文本工具等聚合侧/记录侧算子，没有优化器与训练循环；4 epoch LoRA SFT 只能算 outside 的普通训练，运行时仅以 trace/local_update 数据的形式看到它。",
    "评测侧依赖外部服务：LM Evaluation Harness、ChatGPT 裁判、OpenAI moderation、DeBERTa 奖励模型都不可用，危害性评分、过度安全比例与通用能力指标无法在系统内闭环。",
    "方法本身不是联邦防御：全篇没有恶意客户端假设，vocabulary 的 8 个动作（mask_samples/edit_samples/transform_received/transform_gradients/transform_update/select_and_weight/replace_global/transform_broadcast）一个都没被触发，唯一的联邦步骤（第 13 步）还是论文未涉及的补充 FedAvg，所以即使把外部依赖补齐，这条流水线表达的也不是论文主张的安全收益之外的任何防御计算。"
  ]
}
```
