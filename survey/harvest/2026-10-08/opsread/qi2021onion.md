# qi2021onion：ONION（backdOor defeNse with outlIer wOrd detectioN，基于离群词检测的文本后门防御）

## 1. 方法一句话

ONION 的输入是一条测试样本（sentence，即词序列 s = w1, · · · , wn）以及一个怀疑分数阈值 ts；它用预训练语言模型计算"原句困惑度（perplexity, ppl）"与"删掉某个词之后的困惑度"之差，把差值 fi > ts 的词判定为离群词（outlier word）并删除，输出一条删词后的新句子 s′，再交给受害模型（victim model）做正常推理；它不改变模型权重，也不判定或剔除整条样本。

## 2. 运行位置

论文是纯集中式（centralized）设定，所有实验在单台服务器上完成（附录 C 列出了 CPU、125GB 内存、8 张 RTX2080 的配置），全文没有联邦学习（federated learning）流程。

分析：把它映射到联邦流程里，ONION 最自然的位置是"客户端在本地推理之前对测试样本做预处理"，等价于"把文本送给受害模型（含模型即服务 API）之前，在请求方一侧清洗输入"。它既不接触训练数据、不接触客户端更新、也不接触聚合结果，因此不属于 server_distribute、client_pre_train、client_pre_step、client_step、client_post_train、server_receive、server_aggregate、server_post_aggregate 中的任何一步，对应 stages 枚举里的 outside_training。

ONION 不需要客户端与服务器之间的额外往返（round trip）：删词完全发生在文本被送进模型之前，清洗后的样本仍然是一次普通的推理请求。论文 §4.4 的脚注 2 明确说明，ONION 在预训练攻击（pre-training attack）与后训练攻击（post-training attack）两种情形下表现相同，因为"ONION only processes test samples rather than intervening in backdoor training"，这也从侧面确认它位于训练流程之外。

## 3. 算子流水线

下面按执行顺序列出；第 1 步是离线标定，第 2–6 步是每条测试样本的在线路径，第 7 步是论文给出的备选实现（论文明确说它不如主方法）。

**步骤 1：阈值调优（离线标定）**
- 步骤名：怀疑分数阈值标定。
- 输入：一批正常样本（论文原话是 "some normal samples (e.g., a validation set)"），条数论文未说明；以及候选阈值 ts 的搜索范围（论文未说明）。
- 计算：在正常样本上选择"尽可能小、同时保持模型性能"的 ts（§3）。
- 输出：一个标量阈值 ts；若无验证集则直接取 ts = 0。
- 论文出处：§3 第三段；§4.2；附录 A（图 2 给出 ts 的敏感性曲线）。

**步骤 2：原句困惑度计算**
- 步骤名：计算原句困惑度 p0。
- 输入：一条测试句子 s = w1, · · · , wn，长度为 n 个词。
- 计算：用语言模型（本文选 GPT-2）计算整句的困惑度 p0。困惑度的具体公式论文未说明。
- 输出：标量 p0。
- 论文出处：§3 第二段（"we first use a language model to calculate its perplexity p0"）。

**步骤 3：逐词删除后重算困惑度**
- 步骤名：逐词留一式困惑度计算。
- 输入：原句 s，以及待考察的词位 i ∈ {1, ..., n}。
- 计算：构造删掉第 i 个词后的句子 si = w1, · · · , wi−1, wi+1, · · · , wn，用同一个语言模型计算其困惑度 pi；对 n 个词位各做一次。
- 输出：n 个标量 p1, ..., pn。
- 论文出处：§3 第二段与公式 (1) 的说明（"where pi is the perplexity of the sentence without wi, namely si = w1, · · · , wi−1, wi+1, · · · , wn"）。

**步骤 4：怀疑分数计算**
- 步骤名：怀疑分数（suspicion score）。
- 输入：标量 p0 与向量 p1, ..., pn。
- 计算：fi = p0 − pi，即公式 (1)。删除某个词后困惑度下降得越多（fi 越大且为正），该词越可能是离群词。
- 输出：长度 n 的分数向量 f ∈ R^n。
- 论文出处：公式 (1)，§3 第二段。

**步骤 5：阈值判定**
- 步骤名：离群词判定。
- 输入：分数向量 f 与阈值 ts。
- 计算：对所有词位做逐元素比较，fi > ts 的判为离群词。
- 输出：长度 n 的二值删除掩码 m ∈ {0,1}^n。
- 论文出处：§3 第三段（"We determine the words with a suspicion score larger than ts (i.e., fi > ts) as outlier words"）。

**步骤 6：删词并送入受害模型**
- 步骤名：按掩码删词、执行推理。
- 输入：原句 s 与删除掩码 m。
- 计算：删除所有被判定为离群词的词，得到 s′，把 s′ 喂给受害模型得到预测。论文只描述"删除"，不替换、不加噪、不改写。
- 输出：清洗后的句子 s′ 与受害模型的分类结果。
- 论文出处：§3 第三段（"remove them before feeding the test sample to the backdoored model"）。

**步骤 7（备选，非论文主张）：组合优化式删词搜索**
- 步骤名：基于粒子群优化（particle swarm optimization, PSO）或遗传算法（genetic algorithm, GA）的删词搜索。
- 输入：原句 s，搜索空间为 D 维二值向量（D = 原句词数，每一维表示是否删除该位置的词）。
- 计算：用 N 个粒子/个体迭代搜索使处理后的句子困惑度最低（PSO 的优化分数定义为句子困惑度的相反数；GA 的适应度定义为原句与处理后句子困惑度之差），迭代公式见附录 B 的公式 (2)–(6)。
- 输出：一个删词位置集合（处理后句子）。
- 论文出处：附录 B（§B.1、§B.2、§B.3）；论文在 §3 末尾明确说这两种方法"do not perform better than ONION and need more processing time"，因此不属于论文主张的流水线。

## 4. 采样与规模控制

- 样本：每条测试样本都要对全部 n 个词位各做一次删除与困惑度计算，没有对词位做抽样、截断或降维；论文未说明句长上限。
- 参考数据/探针（probes）：仅调 ts 时使用"一些正常样本（如验证集）"，条数论文未说明（§3）。
- 客户端：论文未使用（非联邦方法，没有客户端概念）。
- 层与参数坐标：论文未使用，ONION 不访问模型内部任何层或参数。
- 轮次：论文未使用，ONION 是推理期方法，没有轮次与跨轮累积。
- 附录 B 的备选搜索方法使用了种群规模：PSO 与 GA 均设种群/粒子数 N = 60、最大迭代次数 T = 20（§B.3）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
| --- | --- | --- | --- |
| ts | 怀疑分数阈值，fi > ts 判为离群词 | 论文正文没有给出具体数值，只说明在验证集上"尽可能小、同时保持模型性能"地调优；没有正常样本可调时经验性取 ts = 0 | §3；§4.2；附录 A 图 2 |
| 语言模型 | 计算困惑度的模型 | GPT-2（Radford et al., 2019）；具体型号/规模论文未说明 | §3 |
| N（备选 PSO/GA） | 粒子数/种群规模 | 60 | §B.3 |
| T（备选 PSO/GA） | 最大迭代次数 | 20 | §B.3 |
| ωmax, ωmin（备选 PSO） | 惯性权重上/下界 | 0.8 与 0.2 | §B.3 |
| Pmax, Pmin（备选 PSO） | 移动概率上/下界 | 0.8 与 0.2 | §B.3 |
| 删词概率（备选 GA） | 初始化时每个词被删的概率 | 在 {0.1, 0.2, 0.3} 中随机选一个 | §B.2 |

受害模型与数据规模不属于 ONION 的超参数，但复现实验需要：BiLSTM 隐藏层 1,024、词嵌入 300；BERT-BASE 12 层、768 维隐状态；SST-2 共 9,612 句、OffensEval 共 14,102 句、AG News 共 30,399 句（§4.1）。

## 6. 判定与动作

- 判定规则：逐词比较 fi 与 ts，fi > ts 即为离群词；不做聚类、不做排序取 top-k（§3）。ts 越小，删得越多，ASR 下降越明显而 CACC 几乎不变（附录 A 图 2）。
- 动作：删除被判定的词，其余什么都不做——不替换、不加噪、不裁剪、不加权、不改模型权重；删除是"一次性"的，掩码由原句分数直接得到，论文没有描述删词后重新计算困惑度再判定的迭代过程（§3）。
- 是否跨轮累积：不涉及，ONION 没有训练与轮次概念，也不跨样本累积状态。
- 效果的量化边界（§4.3、表 2、表 3）：只要触发词没被删掉（Nt = 0），无论误删多少正常词，ASR 恒为 100%；删掉触发词可把 ASR 从 100% 降到 18.12%，说明动作必须命中触发词才有效。平均每条被投毒的测试样本删掉 0.76 个触发词和 0.57 个正常词，触发词检测的精确率与召回率为 56.19 与 75.66（论文给出的数字没有带百分号）；正常测试样本平均误删 0.63 个词，且 71.2% 的正常样本一个词都没删。
- 整体效果（§4.2 表 1）：ts 调优时平均 ΔASR 最高约 56%，平均 ΔCACC 仅 0.99；ts = 0 时平均 ΔASR′ 为 57.62%、平均 ΔCACC′ 为 2.15。与 BKI 在预训练攻击情形对比（§4.4 表 5）：平均 ΔASR 为 44.43% vs. 16.07%，平均 ΔCACC 为 1.41 vs. 0.87。

## 7. 需要的外部资源

- 一个预训练语言模型 GPT-2，用于计算困惑度；模型规模论文未说明（§3）。
- 一批正常样本（验证集）用于调 ts，规模论文未说明（§3）。
- 受害模型本身用于最终推理与评估：BiLSTM 或 BERT-BASE；ONION 不需要访问受害模型的内部权重（§3、§4.1）。
- 复现评估所需数据：SST-2、OffensEval、AG News 三个公开数据集（§4.1）。
- 不需要干净训练集/根数据集（root dataset）、不需要对齐前后的权重、不需要预训练检测器、不需要额外的判别模型；论文也未说明需要知道触发器形态的先验知识。

## 8. 计算与存储开销

- 论文报告的开销：论文没有给出任何具体的时间、FLOPs 或显存数字；只在 §3 说 ONION "quite simple and efficient"，并在 §3 末尾与 §B.3 说 PSO/GA 两种组合优化方法 "need more processing time"、"take much time"，但没有量化。
- 分析：主要开销来自步骤 3"逐词删除后重算困惑度"。按论文的字面描述，每条测试样本需要 1 次原句前向加 n 次删词后前向，共 n+1 次 GPT-2 前向；由于每次前向要处理长度约 n 的序列，单条样本的 token 级计算量约按 O(n²) 增长，调用次数按 O(n) 增长。
- 分析：如果实现时把 pi 近似为原句第 i 个词位置的负对数似然（即一次前向拿到逐 token loss），成本可降为每条样本 1 次前向、O(n) 计算量；但论文没有这样描述，这属于实现近似而非论文内容。
- 分析：存储开销很小，只需要 GPT-2 权重与一条句子/一个分数向量，不需要梯度、优化器状态或跨轮缓存；真正的工程瓶颈是推理延迟，因为 n+1 次前向若串行执行会显著拖慢单条样本的响应。
- 分析：误删与漏删的代价不对称——表 2 显示漏掉触发词时 ASR 仍为 100%，所以在延迟预算内做取舍时，优先保证删全触发词比压低误删更重要。

## 9. 实现时容易错的地方

论文明确强调或明确承认的：

1. 只在插入式（insertion-based）触发器上有效。§5 明确说 ONION 难以防御上下文感知的句子插入、句法结构触发器（syntactic structure）和词替换（word substitution）触发器，因为这时插入内容不再破坏流畅度。实现时不能把它当成通用后门防御。
2. 判定必须命中触发词才有用：表 2 显示 Nt = 0 时 ASR 恒为 100%，即使删掉大量正常词也不下降。
3. 误删稀有词是预期行为而不是 bug：§4.3 指出被误删的正常词平均词频排名为 637,106，而整个 SST-2 为 148,340（按 GPT-2 训练语料统计），语言模型本来就会给稀有词高困惑度。
4. ts 的调优方向：§3 要求"尽可能小，同时保持模型性能"；附录 A 图 2 显示减小 ts 会明显降低 ASR 而几乎不影响 CACC。
5. 删词是"基于原句分数一次性同时删除"，不是贪心迭代；实现时若改成每删一个词重算一遍，就偏离了论文算法并且成本更高（§3 未描述迭代）。

论文没说清、实现时必须自己决定的地方：

1. GPT-2 的具体规格（small / medium / large / 蒸馏版）论文未说明。
2. 困惑度的精确定义论文未说明：是否按 token 数做长度归一化、是否包含 BOS/EOS、如何取指数。
3. 是否真的对每个词重跑一次前向，还是用一次前向的逐 token loss 近似，论文未说明；这直接决定是 n+1 倍成本还是 1 倍成本。
4. "词"与 GPT-2 的 BPE 子词（subword）对齐方式论文未说明：一个词被切成多个子词时删哪些、分数如何归并到一个词上，都没有交代。
5. 边界情况论文未说明：删到空句、删首词、标点与空白、重复词、大小写如何处理。
6. ts 的具体数值：正文与附录正文都没有列出数字，只有图 2 的敏感性曲线；也没有给出 ts 的候选搜索范围。
7. 调优准则"maintaining model's performance"允许 CACC 下降多少，论文未量化；验证集规模也未说明。
8. 是否需要受害模型的输出概率或置信度：论文只描述"把清洗后的样本喂给模型"，没有说明是否用模型自身信号辅助判定，实现时只能按"不需要"处理。
9. 批处理与并行化策略论文未说明；若部署在低延迟场景，需要自行决定是否并行 n 次前向。
10. 论文 §3 中"which is proven to have by later experiments"一句在抽取文本里残缺（疑为"proven to work well"），ts = 0 的兜底说法的完整语义需以 §4.2 表 1 的 ΔASR′ / ΔCACC′ 为准。
11. 论文只评测了英文句子级分类任务，对非英文分词或长文档的适用性未讨论。

## 10. 原文依据

1. 支撑步骤 2（原句困惑度）与运行位置（推理期、送入模型之前）："In the inference process of a backdoored model, for a given test sample (sentence) comprising n words s = w1, · · · , wn, we first use a language model to calculate its perplexity p0."
2. 支撑步骤 2 的语言模型选型（外部资源）："In this paper, we choose the widely used GPT-2 pre-trained language model (Radford et al., 2019), which has demonstrated powerful performance on many NLP tasks."
3. 支撑步骤 3 与步骤 4（删除单词语义与怀疑分数公式）："Then we define the suspicion score of a word as the decrements of sentence perplexity after removing the word, namely fi = p0 −pi, (1) where pi is the perplexity of the sentence without wi"
4. 支撑步骤 4 的分数方向解释（为什么 fi 大意味着离群词）："That is because if wi is an outlier word, removing it would considerably decrease the perplexity of the sentence, and correspondingly fi = p0 −pi would be a large positive number."
5. 支撑步骤 5 与步骤 6（阈值判定与删词动作）："We determine the words with a suspicion score larger than ts (i.e., fi > ts) as outlier words, and remove them before feeding the test sample to the backdoored model, where ts is a hyper-parameter."
6. 支撑步骤 1（在正常样本上调 ts 及其准则）："To avoid accidentally removing normal words and impairing model's performance, we can tune ts on some normal samples (e.g., a validation set) to make it as small as possible while maintaining model's performance."
7. 支撑步骤 1 的无验证集兜底（ts = 0）："We also specially show the performance of ONION with ts = 0 on SST-2 (∆ASR' and ∆CACC'), simulating the situation where there is no validation set for tuning ts."
8. 支撑整条流水线的定位（测试样本检查、删词防激活后门，而非训练期干预）："This method is based on test sample examination, i.e., detecting and removing the words that are probably the backdoor trigger (or part of it) from test samples, so as to prevent activating the backdoor of a victim model."

```json
{
  "key": "qi2021onion",
  "method": "ONION (backdOor defeNse with outlIer wOrd detectioN)：用 GPT-2 困惑度增量做阈值判定、在推理前删除测试样本中离群词的文本后门防御",
  "stages": ["outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {"step": "阈值标定（离线）", "operator": "threshold_tuning_on_validation", "input": "一批正常样本（如验证集，条数论文未说明）与候选阈值 ts", "output": "标量阈值 ts（无验证集时 ts = 0）", "params": {"criterion": "as small as possible while maintaining model's performance", "fallback_ts": 0}, "source": "§3；§4.2；附录 A 图 2"},
    {"step": "原句困惑度", "operator": "causal_lm_perplexity", "input": "一条测试句子 s = w1, ..., wn，长度 n 个词", "output": "标量 p0", "params": {"lm": "GPT-2", "lm_size": "论文未说明", "perplexity_formula": "论文未说明"}, "source": "§3 第二段"},
    {"step": "逐词删除后重算困惑度", "operator": "leave_one_out_perplexity", "input": "原句 s 与每个词位 i ∈ {1..n}", "output": "n 个标量 p1, ..., pn", "params": {"lm": "GPT-2", "num_forward_passes": "n（论文未说明是否可用单次前向的 token loss 近似）", "sentence_after_deletion": "si = w1, ..., wi-1, wi+1, ..., wn"}, "source": "§3 第二段；公式 (1) 的文字说明"},
    {"step": "怀疑分数", "operator": "perplexity_delta_score", "input": "标量 p0 与向量 p1, ..., pn", "output": "长度 n 的分数向量 f ∈ R^n", "params": {"formula": "fi = p0 - pi"}, "source": "公式 (1)"},
    {"step": "阈值判定", "operator": "score_threshold_select", "input": "分数向量 f 与阈值 ts", "output": "长度 n 的二值删除掩码 m ∈ {0,1}^n", "params": {"ts": "验证集调优；无验证集取 0；正文未给具体数值"}, "source": "§3 第三段"},
    {"step": "按掩码删词并推理", "operator": "token_delete_by_mask", "input": "原句 s 与删除掩码 m", "output": "清洗后句子 s' 与受害模型的分类结果", "params": {"replacement": "无（只删不替换）", "iteration": "无（基于原句分数一次性删除）"}, "source": "§3 第三段"},
    {"step": "备选：组合优化式删词搜索（论文明确说明不如主方法）", "operator": "population_search_delete", "input": "原句 s，搜索空间为 D 维二值向量（D = 原句词数）", "output": "删词位置集合（处理后句子）", "params": {"N": 60, "T": 20, "omega_max": 0.8, "omega_min": 0.2, "P_max": 0.8, "P_min": 0.2, "ga_delete_prob_choices": [0.1, 0.2, 0.3]}, "source": "附录 B（§B.1、§B.2、§B.3）；§3 末尾评价"}
  ],
  "sampling": [
    {"what": "coordinates", "how": "对每条测试样本的全部 n 个词位逐个删除并重算困惑度，不抽样、不截断", "size": "n（句长；上限论文未说明）"},
    {"what": "probes", "how": "用正常样本/验证集调 ts，具体抽样方式论文未说明", "size": "论文未说明"},
    {"what": "clients", "how": "论文未使用（集中式方法，无客户端概念）", "size": ""},
    {"what": "rounds", "how": "论文未使用（推理期方法，无训练轮次）", "size": ""}
  ],
  "resources": [
    "预训练 GPT-2 语言模型（§3；具体规模论文未说明）",
    "一批正常样本/验证集用于调 ts（§3；规模论文未说明）",
    "受害模型用于最终推理：BiLSTM（hidden 1024、embedding 300）或 BERT-BASE（12 层、768 维隐状态）（§4.1）",
    "复现评估用公开数据集：SST-2（9,612 句）、OffensEval（14,102 句）、AG News（30,399 句）（§4.1）"
  ],
  "actions": ["edit_samples"],
  "dominant_cost": "逐词删除后重算困惑度：按论文描述每条测试样本需要 n+1 次 GPT-2 前向（1 次原句 + n 次删一词），token 级计算量约按 O(n²) 增长、前向次数按 O(n) 增长；论文未报告任何具体时间/显存数字，只说 ONION 'quite simple and efficient'，并说 PSO/GA 备选方法 'take much time'。",
  "underspecified": [
    "GPT-2 的具体规格（small/medium/large 或蒸馏版）论文未说明",
    "困惑度的精确定义（长度归一化、BOS/EOS 处理）论文未说明",
    "是否真的对每个词重跑一次前向，还是用单次前向的逐 token loss 近似，论文未说明",
    "词与 GPT-2 BPE 子词的对齐方式、一个词含多个子词时的删除与分数归并，论文未说明",
    "边界情况（删到空句、删首词、标点/空白/重复词）如何处理，论文未说明",
    "ts 的具体数值与候选搜索范围，正文和附录正文都没有给出，只有附录 A 图 2 的敏感性曲线",
    "调优时允许的 CACC 下降幅度与验证集规模，论文未说明",
    "是否需要受害模型的输出概率/置信度辅助判定，论文未说明",
    "批处理与并行化策略、延迟预算，论文未说明",
    "对非英文分词或长文档的适用性，论文未讨论"
  ],
  "quotes": [
    {"supports": "步骤 2 原句困惑度；运行位置为推理期、送入受害模型之前", "text": "In the inference process of a backdoored model, for a given test sample (sentence) comprising n words s = w1, · · · , wn, we first use a language model to calculate its perplexity p0."},
    {"supports": "步骤 2 的语言模型选型（外部资源）", "text": "In this paper, we choose the widely used GPT-2 pre-trained language model (Radford et al., 2019), which has demonstrated powerful performance on many NLP tasks."},
    {"supports": "步骤 3 与步骤 4 的怀疑分数定义（公式 1）", "text": "Then we define the suspicion score of a word as the decrements of sentence perplexity after removing the word, namely fi = p0 −pi, (1) where pi is the perplexity of the sentence without wi"},
    {"supports": "步骤 4 的分数方向解释（fi 大意味着离群词）", "text": "That is because if wi is an outlier word, removing it would considerably decrease the perplexity of the sentence, and correspondingly fi = p0 −pi would be a large positive number."},
    {"supports": "步骤 5 阈值判定与步骤 6 删词动作", "text": "We determine the words with a suspicion score larger than ts (i.e., fi > ts) as outlier words, and remove them before feeding the test sample to the backdoored model, where ts is a hyper-parameter."},
    {"supports": "步骤 1 在正常样本上调 ts 的准则", "text": "To avoid accidentally removing normal words and impairing model's performance, we can tune ts on some normal samples (e.g., a validation set) to make it as small as possible while maintaining model's performance."},
    {"supports": "步骤 1 的无验证集兜底 ts = 0", "text": "We also specially show the performance of ONION with ts = 0 on SST-2 (∆ASR' and ∆CACC'), simulating the situation where there is no validation set for tuning ts."},
    {"supports": "整条流水线的定位：测试样本检查、删词以防激活后门", "text": "This method is based on test sample examination, i.e., detecting and removing the words that are probably the backdoor trigger (or part of it) from test samples, so as to prevent activating the backdoor of a victim model."}
  ]
}
```
