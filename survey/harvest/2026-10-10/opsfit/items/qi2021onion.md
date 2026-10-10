## 1. 这条流水线整体上能否由现有算子库与运行时表达

**结论：只能部分表达（partial）。**ONION 是**推理期**的文本净化：用外部 GPT-2 的逐词困惑度增量找离群词、删词后再交给受害模型分类。本运行时是联邦 LoRA 微调运行时，其模型句柄只提供对"当前 LoRA 模型"的 `losses / hidden / activations / per_sample_gradients / logprob / generate / lora`，**没有一个因果语言模型可用来自查句子的逐词困惑度**；流水线自己也在 `stages` 里写明 `outside_training`，即在训练算子流水线之外。因此"删词后的句子 + 受害模型分类结果"这条闭环落不了地，但词级文本工具与阈值判定部分能对上。

逐步骤判断：

| n | 步骤 | 归类 | 依据 |
|---|---|---|---|
| 1 | 验证集调阈值 ts | outside | 离线准备（调参/标定），不是防御计算本身；若在线做，也只需比较+取分位，属平凡代码 |
| 2 | 原句困惑度 p0 | missing_op `causal_lm_perplexity` | catalog 无任何因果 LM 困惑度算子；`model.logprob` 是"prompt→target 的平均对数概率"，句式接口不符 |
| 3 | 逐词删除重算困惑度 | op + runtime_data + missing_op | `text.split_words` + `text.leave_one_out` 精确提供"n 个删一词文本"；打分靠 `samples/text_logprob/word`，但该 coordinate 是逐词对数概率而非"困惑度"，且需 n 次调用，这里有一处粒度/语义疑点 |
| 4 | 分数 f_i = p0 − p_i | op | `text.outlier_words(base, without, bar)` 的语义正是 ONION 这条规则，bar=0 时就是纯差值 |
| 5 | 阈值判定 ts | compose | 没有"阈值二值化"专用算子，但 `f > ts` 是标准张量比较（也可用 `robust.largest_gap_threshold` / `robust.quantile_threshold` 辅助定 ts） |
| 6 | 按掩码删词并推理 | missing_op `delete_tokens_by_mask`（删词）+ needs_runtime（分类推理） | catalog 只有 `text.split_words`/`text.leave_one_out`，没有"按掩码重组文本"的单元；受害模型对清洗后句子的分类结果在 coordinates 里没有对应项 |
| 7 | 遗传算法搜索删词集合（论文自认次优） | missing_op `binary_mask_search` | 需要种群/交叉/变异/精英保留的搜索单元；fitness 侧可复用第 2–4 步的算子 |

关键的"看起来像但不是"之处：`text.outlier_words` 名字很像第 5 步，但它签名是 `(base, without, bar)`，做的是**差值+阈值选取（第 4–5 步）**，不是二值化本身；`model.logprob` 名字像第 2–3 步，但它是**均值对数概率、prompt/target 两段式**，与"整句困惑度 / 逐词删除后再算整句困惑度"接口不一致，所以第 2、3 步不能简单算作 op。`samples/text_logprob/word`（`via: model_handle`）是运行时能给出的最接近的第 3 步读法，但它的 "word" 粒度是运行时自己的分词口径，不保证等于 ONION 的"空格分词词位"，这是第 3 步最大的疑点。

另外，第 6 步要把清洗结果传给受害模型做**推断分类**，运行时不提供"加载模型后在任意文本上出分类结果"这一坐标（`uploads/probe_behavior/client` 是服务器侧探针行为，不是客户端对测试句的推理），也没有对应动作：`received` 只能 `transform_received`，`samples` 只能 `mask_samples / edit_samples`——ONION 改的是**推理输入文本**，两边都对不上。

## 2. 缺的东西里哪些是通用的，哪些是这篇论文特有的

**通用（别的方法也会用到）**
- `causal_lm_perplexity`：任何用语言模型困惑度做检测/过滤（ONION、困惑度过滤、ppl-based 数据清洗、逐词归因）的方法都要它；核心是"因果 LM 前向 + 长度归一化的 NLL → 困惑度标量"。
- `delete_tokens_by_mask`：文本净化的公共末端，"按位置集合删除 token 并重新拼接文本"与具体检测规则无关。
- `binary_mask_search`：D 维二值掩码上的种群搜索（GA/进化），是通用优化组件；不过在 ONION 里它服务的是论文自认效果较差的备选方案。
- 第 3 步的 leave-one-out 打分策略本身也是通用模式，但本库已用 `text.leave_one_out` 覆盖了**枚举部分**，缺的只是它与 LM 打分器的连接，不必新造单元。

**这篇论文特有**
- 验证集上"在保持模型可用性的前提下取尽可能小的 ts"这条标定准则，以及无验证集时 ts=0 的兜底，是 ONION 的具体选择，不是可复用算子。
- `f_i = p0 - p_i > 0` 的离群词判据已被 `text.outlier_words` 直接承载（本库明显是为它建的），属于该方法的专有规则。
- 只删不替换、基于原句分数一次性删除（无迭代）属于流程约定，不构成通用算子。
- "推理前删词再交给受害模型"这一整条部署形态是本文的落地方式，也正因如此它落在本训练的运行时之外。

```json
{
  "key": "qi2021onion",
  "steps": [
    {
      "n": 1,
      "class": "outside",
      "uses": [],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "在验证集上搜索最小可用阈值 ts，属于离线标定/调参，不是防御计算本身（流水线 stages 也标为 outside_training）。若改到在线做，只需对分数向量做比较与取分位，属平凡代码，无需新算子。"
    },
    {
      "n": 2,
      "class": "missing_op",
      "uses": ["samples/text_logprob/word"],
      "missing_name": "causal_lm_perplexity",
      "missing_family": "probabilistic_model",
      "missing_io": "输入：因果语言模型句柄 + 一段文本（token 序列）；输出：标量困惑度 perplexity = exp(平均 token NLL)，可选返回逐 token NLL",
      "note": "catalog 无任何因果 LM 困惑度算子。model.logprob(prompts, targets) 只给 target 段的平均对数概率，接口与语义都不等于整句困惑度；coordinates 里 samples/text_logprob/word 的 'word' 是运行时自身分词粒度，用它近似有可能，但把困惑度换算与分词对齐交给调用方并不可靠，故按 missing_op 处理并标出疑点。"
    },
    {
      "n": 3,
      "class": "op",
      "uses": ["text.split_words", "text.leave_one_out"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "枚举部分被完整覆盖：text.split_words 得到词表，text.leave_one_out(words) 精确返回 n 个各删一词的文本。但打分部分仍依赖第 2 步那类 LM 困惑度：模型句柄的 logprob 是均值、按 prompt/target 组织，且需对每条删词句单独前向；samples/text_logprob/word 可作逐词近似。这一步自身不需要新算子（组合已有函数即可），真正的缺口记在第 2 步。"
    },
    {
      "n": 4,
      "class": "op",
      "uses": ["text.outlier_words"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "text.outlier_words(base, without, bar) 的说明就是 ONION 规则：f_i = base - without_i，超过 bar 记为可疑并返回下标；bar=0 即本步的 fi = p0 - pi。名字相近但语义经核对确实吻合，属 op。"
    },
    {
      "n": 5,
      "class": "compose",
      "uses": ["text.outlier_words", "robust.largest_gap_threshold", "robust.quantile_threshold"],
      "missing_name": "",
      "missing_family": "",
      "missing_io": "",
      "note": "没有通用'阈值二值化'算子，但 m = (f > ts) 只是一次比较。ts 的选取可用 robust.largest_gap_threshold 或 robust.quantile_threshold 辅助，也可直接由第 1 步离线给定；若 ts=0 就是符号判定。"
    },
    {
      "n": 6,
      "class": "missing_op",
      "uses": ["text.split_words"],
      "missing_name": "delete_tokens_by_mask",
      "missing_family": "text",
      "missing_io": "输入：原始文本（或词序列）与等长布尔掩码；输出：删除掩码位置后的文本（保持原有空格/标点风格，只删不替换）",
      "note": "catalog 只有分词与 leave_one_out（恰好删一个词），没有按任意掩码重组文本的单元，故缺失删词算子。另一半'把清洗后句子交给受害模型得到分类结果'运行时也给不了：没有'任意文本调用受害模型出分类结果'的 coordinate，actions 里 received 只有 transform_received，与改推理输入不匹配，属第 6 步的 needs_runtime 侧缺口。"
    },
    {
      "n": 7,
      "class": "missing_op",
      "uses": ["samples/text_logprob/word"],
      "missing_name": "binary_mask_search",
      "missing_family": "optimization",
      "missing_io": "输入：维数 D、适应度函数（D 维二值掩码 -> 标量）、种群规模 N、轮数 T、交叉/变异/选择概率区间；输出：最优二值掩码或得分最优的若干候选",
      "note": "论文自认不如主方法的备选：D 维二值向量上的遗传搜索（N=60, T=20, 交叉与变异概率在 0.2~0.8/0.1~0.3 间随机）。虽只需循环+比较，但种群、交叉、变异、精英保留这一整套是可复用搜索单元而非几行张量运算，故按 missing_op 处理；其适应度可用第 2~4 步的算子拼出。"
    }
  ],
  "expressible": "partial",
  "blocking": [
    "运行时没有可用的因果语言模型困惑度：模型句柄只有针对当前 LoRA 模型的 logprob/losses/generate，没有 GPT-2 式的整句困惑度接口，第 2、3 步的核心打分落不了地（samples/text_logprob/word 只能给出运行时自身分词粒度的逐词对数概率，是近似而非等价）。",
    "ONION 作用于推理期输入文本，而运行时是联邦 LoRA 训练流水线（该论文 stages 即为 outside_training）：既没有'按掩码删词重组文本'的算子，也没有'把任意文本交给受害模型取分类结果'的 coordinate 与动作，第 6 步闭环无法表达。"
  ]
}
```
