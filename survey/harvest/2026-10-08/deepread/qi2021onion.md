# qi2021onion：ONION: A Simple and Effective Defense Against Textual Backdoor Attacks

## 1. 基本信息

- 场景：论文属于**集中式训练下的文本分类模型**（centralized training），不是联邦学习，也不是联邦大模型微调。论文讨论的两种情形是"pre-training attack situation"（用户拿到的第三方数据集已被投毒，用户自己训练模型）和"post-training attack situation"（用户拿到的是已经被植入后门的第三方预训练模型或 API），见 §1 与 §2。论文全文没有出现联邦学习（federated learning）、客户端聚合、LoRA 或参数高效微调的任何内容。
- 训练阶段：防御本身发生在**推理/测试阶段**，对测试样本做预处理；它不介入后门训练过程，也不修改模型参数。
- 论文类型：防御 / 检测（test-time 输入净化，outlier word detection）。
- 模型与数据规模：受害模型为 BiLSTM（hidden size 1,024，word embedding size 300）与 BERT_BASE（12 层、768 维隐状态），BERT 分 BERT-T（后门训练后直接测试）和 BERT-F（后门训练后再用干净数据微调）两种设定（§4.1）。数据集为 SST-2（9,612 句电影评论，二分类情感分析）、OffensEval（14,102 句 Twitter 句子，二分类攻击性语言识别）、AG News（30,399 句新闻，四分类话题分类）（§4.1）。检测用的参考语言模型是 GPT-2（§3）。

## 2. 威胁模型

论文没有用"恶意客户端 / 恶意服务器"的语言描述攻击者；它描述的是数据与模型供应链上的投毒者与后门模型发布者（分析：这是中心化供应链威胁模型，而不是联邦威胁模型）。

- 攻击者是谁：向训练数据中注入带触发词（trigger）样本的一方（论文语境为使用第三方数据集时的数据提供方），在后训练情形下还包括发布已被植入后门的预训练模型或 API 的一方（§1、§2）。论文说"almost all existing textual backdoor attack methods are based on training data poisoning"（§2）。
- 占比或数量：论文未说明投毒样本比例，也未给出任何客户端数量或恶意比例（分析：因为设定中不存在客户端）。全文只给出 ONION 侧处理后的统计量：在 BadNet + BERT-T + SST-2 的分析中，被投毒测试样本平均移除 0.76 个触发词和 0.57 个正常词；正常测试样本平均移除 0.63 个正常词（§4.3）。
- 能力：攻击者能构造并向训练数据插入带触发内容的样本（插入式触发，可能是稀有词、中频词、高频词或整句），在 RIPPLES 设定下还能专门修改后门训练过程并调整触发词的词嵌入（§4.1）。
- 知识：论文未说明攻击者是否知道 ONION 的存在与参数，也未说明攻击者对模型结构与训练细节的掌握程度。
- 目标：定向后门（targeted backdoor）。后门模型的正常输入上表现正常，在带预设计触发词的输入上产生攻击者指定的输出（§1）。触发方式有词级（BadNet / BadNetm / BadNeth / RIPPLES）与句级（InSent）两类（§4.1）。
- 防御者是谁、能看到什么、信任什么：防御者是模型使用者，在推理时能看到**原始测试句子**（test sample），并额外持有一个参考语言模型 GPT-2 用于计算困惑度（perplexity）。防御者不信任待测模型（它可能已被植入后门），但信任参考语言模型与（可选的）干净验证集：§3 说可以"tune ts on some normal samples (e.g., a validation set)"；若没有正常样本，可以经验性地把阈值设为 0。BKI 被描述为需要在训练前检查全部训练数据，而 ONION 明确选择不介入训练（§4.4 脚注 2）。

## 3. 攻击入口与流程位置

论文研究的攻击进入位置是**本地数据准备 / 训练数据投毒**：攻击者把带触发词的样本混入训练集，由模型使用者（或后门模型发布者）完成训练，从而把后门注入模型；在后训练情形中，被投毒的训练数据已由第三方使用完毕，模型或 API 本身已带后门（§1、§2）。

攻击的具体操作步骤（依据 §1、§2、§4.1）：(1) 选择触发内容，可以是 1 个稀有词、中频词、高频词，也可以是一整句固定句子；(2) 在原始正常样本中插入该触发内容生成投毒样本，其中 BadNet、BadNetm、BadNeth、RIPPLES 按句长在 SST-2 / OffensEval / AG News 上分别插入 1 / 3 / 5 个触发词，InSent 对所有样本只插入一句；(3) 用投毒样本进行"backdoor training"；(4) RIPPLES 还专门修改预训练模型的后门训练过程并调整触发词的嵌入，只能在 BERT-F 情形下工作。

ONION 自身的防御入口则是**评估与部署阶段**：它在测试样本送入（可能已被植入后门的）模型之前，检测并删除可疑的离群词，从而阻止触发词激活后门（§1、§3）。它不触碰本地训练过程、更新上传、服务器聚合或全局模型下发，因为这些环节在该设定下不存在。

## 4. 方法原理

核心思想：几乎所有已有的文本后门攻击都是插入式的，插入内容会让原句失去流畅性，其构成词在语言模型看来是离群词；删掉这些词会提升句子流畅度，因此可以用困惑度的下降幅度作为"嫌疑分"（§1、§2、§3）。

关键步骤（§3）：

1. 对一个含 n 个词的测试句 s = w1, ..., wn，先用 GPT-2 计算其困惑度 p0。
2. 对每个词 wi，构造删词版本 si = w1, ..., wi−1, wi+1, ..., wn，计算其困惑度 pi。
3. 定义嫌疑分 fi = p0 − pi（公式 (1)）：若 wi 是离群词，删掉它会明显降低困惑度，fi 就是较大的正数。
4. 把 fi 大于阈值 ts 的词判为离群词并删除，剩余句子才送入受害模型；ts 是唯一超参数，可在正常样本（如验证集）上调到尽量小以维持模型性能，没有验证集时可经验性地设为 0。
5. 论文另外尝试了基于粒子群优化（particle swarm optimization，PSO）与遗传算法（genetic algorithm，GA）的组词删除方案（附录 B，损失/适应度定义见公式 (2)–(6)），但结论是它们并不比简单的 ONION 更好且耗时更多（§3、附录 B.3、表 6）。

## 5. 检测或防御所需的数据

- 原始测试句子文本（逐词序列，s = w1, ..., wn）：采集位置是**评估 / 推理时、模型前向之前**；粒度是**逐样本**（且方法内部要按词逐一做删除重算，即"逐样本 × 逐词"的细粒度视图）；不需要跨轮历史，不需要其他客户端的数据。
- 一个参考语言模型（论文用 GPT-2）及其困惑度计算能力：在**评估时**对原句和每个删词变体各做一次前向计算，属于**额外的前向计算**（不是反向）。论文未报告这些前向的具体次数、时延或 FLOPs。
- 可选的干净正常样本（验证集）：用于调 ts，采集位置是**评估前 / 部署准备阶段**；粒度是**样本级**；属于"干净参考数据"。论文明确指出没有它也可以把 ts 设为 0（§3），并在表 1 中用 ∆ASR' 与 ∆CACC' 报告了 ts = 0 的结果。
- 受害模型本身在检测阶段**不需要**被访问（ONION 只看输入文本）；受害模型只在净化后的样本上做最终推理。论文未说明是否需要模型的输出概率、隐藏状态或梯度。

作为攻击论文的对应问题：攻击留下的可观测量是**输入文本层面的插入痕迹**——触发词（稀有词、中频词、高频词或整句）会造成句子流畅度下降，从而在 GPT-2 困惑度上表现为高嫌疑分。表 2 显示：只要触发词被保留（Nt = 0），ASR 恒为 100%，无论删掉多少正常词；删掉触发词则 ASR 从 100% 降到 18.12%（SST-2 投毒测试集）；表 4 的案例显示触发词通常嫌疑分很高（例如 "mn (148.78)"、"tq (211.49)"、"mb (86.88)"）。论文声称 ONION 的假设性弱点在于**非插入式触发**（句法结构触发、词替换触发）与**上下文感知的句子插入**，即它对这类隐蔽攻击难以防御（§5，引用 Zhang et al. 2021、Qi et al. 2021a、Qi et al. 2021b）。论文没有声称 ONION 能绕过任何具体检测器，也没有讨论规避 ONION 的自适应攻击。

## 6. 干预动作

干预动作是**过滤样本中的词（test-time input sanitization）**：把嫌疑分超过 ts 的词从测试句里删掉，再把处理后的句子交给受害模型；方法不剔除客户端、不重加权、不裁剪、不加噪、不修复或回滚模型，也不改变训练过程。动作发生的位置是**推理前端的输入侧**，论文的框架中对应"评估与部署"环节，而不是客户端或服务器训练钩子。§3 明确说"remove them before feeding the test sample to the backdoored model"；§4.4 脚注 2 进一步说明 ONION 只处理测试样本、不介入后门训练，因此它在训练前投毒与训练后投毒两种情形下的表现完全相同。

## 7. 实验设置与主要结果

- 模型：BiLSTM、BERT-T、BERT-F（§4.1）。数据集：SST-2、OffensEval、AG News（§4.1）。攻击：BadNet、BadNetm、BadNeth、RIPPLES、InSent 共五种（§4.1）。
- 客户端数与参与率：论文未说明（分析：该设定下不存在联邦客户端）；轮次：论文未说明；恶意比例：论文未说明；是否非独立同分布（non-IID）：论文未说明。触发词数量按数据集为 1 / 3 / 5（SST-2 / OffensEval / AG News），InSent 为一句（§4.1）。
- 指标：∆ASR（攻击成功率的下降量，ASR 为带触发测试样本上的分类准确率）与 ∆CACC（干净准确率的下降量，CACC 为正常测试样本上的准确率），∆ASR 越高、∆CACC 越低越好（§4.1）。
- 主要结果（表 1，ts 在验证集上调优）：平均 ∆ASR 达到 56%，平均 ∆CACC 仅 0.99；没有验证集时（ts = 0）平均 ∆ASR' 达到 57.62%，平均 ∆CACC' 为 2.15（§4.2）。典型单项：BiLSTM + SST-2 + BadNet 的 ASR 为 94.05，∆ASR 为 46.25；BERT-T + SST-2 + BadNet 的 ASR 为 100，∆ASR 为 59.70，∆ASR' 为 84.40（表 1）。BERT-F + SST-2 + RIPPLES 的 ASR 为 100，∆ASR 为 37.70，∆ASR' 为 83.08（表 1）。BERT-F + AG News + InSent 的 ∆CACC 为 6.39，是表中较明显的干净性能损失（表 1）。
- 分解分析（SST-2 + BERT-T + BadNet）：只要触发词保留（Nt = 0），ASR 恒为 100%；删掉触发词后 ASR 降到 18.12%（Nt = 1 行，表 2）。正常测试样本中 71.2% 没有被误删任何词，误删词数与 CACC 似乎不相关（表 3）。触发词检测的 precision 与 recall 分别为 56.19 和 75.66（§4.3）。被误删的正常词平均词频排名为 637,106，而整个 SST-2 为 148,340（基于 GPT-2 训练语料计算）（§4.3）。
- 与 BKI 的对比（训练前投毒情形，SST-2）：ONION 与 BKI 的平均 ∆ASR 为 44.43% 对 16.07%，平均 ∆CACC 为 1.41 对 0.87（§4.4、表 5）。
- 阈值敏感性：改变 ts 几乎不影响 CACC，而降低 ts 能明显降低各攻击的 ASR（附录 A、图 2）。
- 组合优化方案：PSO 与 GA 的搜索把最大迭代次数 T 设为 20、种群规模 N 设为 60，结果不如原始 ONION 且耗时更多（附录 B.3、表 6）。

## 8. 开销

论文没有报告 ONION 的计算、通信或存储开销的数值：既没有给出 GPT-2 逐词删除重算困惑度所需的次数、时延或显存，也没有给出吞吐量对比，因此**论文未报告**这些量化开销。论文只做了两类定性陈述：(1) 称 ONION 的设计"quite simple and efficient"（§3）；(2) 称 PSO 与 GA 的搜索过程"take much time, rendering them less practical in real-world situations"（附录 B.3）。实验环境在附录 C 中给出：Intel(R) Xeon(R) E5-2680 v4 @ 2.40GHz、56 核、125GB 内存、8 张 RTX2080（12GB 显存）、Ubuntu 18.04.2 LTS、PyTorch 1.5.0，但这只是运行环境，不是开销测量。分析：ONION 在推理路径上引入的是一个与被删词数成正比的参考语言模型前向次数（每个词一次删词重算），在大模型或长 prompt 部署中这会成为主要成本，但论文未量化。

## 9. 假设、局限与自适应攻击

论文成立所依赖的假设：

- 后门触发是**插入式**的，插入内容与上下文无关（词或句），因此会破坏原句流畅性，使触发词在语言模型下成为离群词（§1、§2、§3）。
- 嫌疑分 fi = p0 − pi 能把触发词与正常词分开；图 1 声称触发词与正常词的嫌疑分分布可区分（§4.3）。
- 防御者能拿到明文测试样本，并能使用 GPT-2 计算困惑度（§3）。
- 可以（可选地）拿到干净验证集来调 ts；拿不到时可以设 ts = 0（§3）。
- 误删少量正常词对最终结果影响很小（§4.3，表 3、表 4）。

论文自述的局限（§5）：面对同期工作中更隐蔽的攻击——上下文感知的句子插入（Zhang et al., 2021）、句法结构触发（Qi et al., 2021a）、词替换触发（Qi et al., 2021b）——ONION 难以防御；论文呼吁 NLP 社区投入更多研究，并提醒攻击成功率可以轻易超过 90%。

自适应攻击：论文没有评估任何知道 ONION 机制的自适应攻击者，也没有给出相应结果，因此**论文未报告自适应攻击评估**。论文只说这些隐蔽攻击"ONION is hard to defend against"（§5），属于对局限的定性陈述，不是实验结论。

迁移到联邦 LoRA 微调的失效假设（分析）：

- 触发假设不成立：LoRA 后门可以在连续参数空间或梯度空间构造，后门不必体现为 prompt 中可删除的离群词；ONION 的输入净化对"干净输入 + 被污染适配器"这一类后门没有作用面。
- 防御者位置不成立：ONION 假设服务方能看到每个测试样本的明文并做逐词前向，这在隐私保护或端侧推理的联邦部署中未必成立；它完全不涉及服务器聚合视图、客户端增量（LoRA delta）与逐轮历史。
- 任务形态不成立：ONION 面向短文本分类，靠困惑度衡量流畅性；在生成式大模型上删除用户 prompt 中的词会直接改变用户意图与回答语义，效用损失机制与论文里的 CACC 不可比。
- 阈值调优假设不成立：ts 的设定依赖一个与测试分布同源的干净验证集；联邦场景中各客户端数据异构，单一 ts 的跨客户端可迁移性论文未提供依据。
- 论文本身并非联邦设定，因此对客户端层面的投毒（例如少数恶意客户端放大 LoRA 增量）没有任何实验证据与结论；将 ONION 作为联邦 LoRA 投毒防护的组成部分时，它只能覆盖"输入端插入式触发"这一窄子集。

## 10. 对防护库设计的含义

- 分析：ONION 对应的是一个**与训练无关的推理前端钩子**（输入净化插件），而不是客户端或服务器训练钩子。库如果要有位置挂它，需要提供"评估 / 推理前"的钩子，允许插件改写输入文本后再交给模型；这与库当前以客户端钩子和服务器钩子为主的插件面不同。
- 分析：它需要的数据视图是"逐样本 × 逐词"的**原始输入 token 序列**，以及一个独立的参考语言模型服务；不需要 LoRA 增量、梯度、逐层范数、逐客户端历史或跨客户端数据。因此采集底座至少要能把"评估样本的原始文本 + 分词结果"作为一等数据暴露出来。
- 分析：它需要"额外前向计算"这一能力抽象——对同一输入生成 K 个删词变体并对每个变体调用参考模型，属于逐样本的放大式推理。库应把"参考模型 / 打分器"作为可注入依赖，而不是把 GPT-2 写死。
- 分析：干预接口只需要"过滤样本（样本级改写）"语义；不需要剔除客户端、重加权、裁剪、加噪或回滚模型。这与多数投毒防护插件需要的"服务器聚合前干预"接口是互补而非重叠的。
- 分析：它需要"干净参考数据"和"可调阈值"这两个通用配置项：验证集用于调 ts，且必须支持"无验证集时退化为默认阈值（论文中为 0）"。这类退化路径对通用防护库是有价值的通用需求。
- 分析：哪些是通用的、哪些是这篇论文特有的——通用的是"评估时输入侧净化钩子 + 参考打分器 + 干净验证集与阈值配置 + 样本级过滤干预"；特有的是"用语言模型困惑度的删词下降量作为离群词分数"以及"仅针对插入式文本触发"这一威胁假设。若目标是检测联邦 LoRA 的后门适配器，则它既不是入口也不是出口，只能作为提示词侧的第二道防线。

## 11. 原文依据

1. §Abstract — 支撑第 1 节"论文类型为文本后门防御、基于离群词检测"与第 4 节核心思想："In this paper, we propose a simple and effective textual backdoor defense named ONION, which is based on outlier word detection and, to the best of our knowledge, is the first method that can handle all the textual backdoor attack situations."
2. §1 — 支撑第 2 节"攻击目标为定向后门、后门模型在正常输入上表现正常"："Backdoor attacks aim to inject a backdoor into a DNN model during training so that the victim model (1) behaves properly on normal inputs like a benign model without a backdoor, and (2) produces adversary-specified outputs on the inputs embedded with predesigned triggers that can activate the injected backdoor."
3. §1 — 支撑第 2 节与第 3 节"攻击入口是训练数据投毒，且投毒方可以是第三方数据提供者"："The most common attack method is training data poisoning, which injects a backdoor into a victim model by training the model with some poisoned data that are embedded with the predesigned trigger (we call this process backdoor training)."
4. §2 — 支撑第 3 节"攻击入口为数据投毒"与第 5 节"攻击痕迹是插入造成的流畅性破坏"："As far as we know, all existing textual backdoor attack methods are based on training data poisoning. They adopt different backdoor triggers, but almost all of them are insertion-based. Dai et al. (2019) choose some short sentences as backdoor triggers, e.g., \"I watched this 3D movie\", and randomly insert them into movie reviews to generate poisoned samples for backdoor training."
5. §1 — 支撑第 4 节核心假设"插入内容破坏流畅性、其词可被判为离群词"："The inserted contents would break the fluency of the original text and their constituent words can be easily identified as outlier words by language models. For example, Kurita et al. (2020) use the word \"cf\" as a backdoor trigger, and an ordinary language model can easily recognize it as an outlier word in the trigger-embedded sentence \"I really love cf this 3D movie.\"."
6. §3 — 支撑第 4 节公式 (1) 与第 5 节"需要逐词删词重算困惑度的额外前向计算"："Then we define the suspicion score of a word as the decrements of sentence perplexity after removing the word, namely fi = p0 −pi, (1) where pi is the perplexity of the sentence without wi, namely si = w1, · · · , wi−1, wi+1, · · · , wn."
7. §3 — 支撑第 4 节"阈值 ts 是唯一超参数、可用干净验证集调优、也可取 0"与第 5 节"干净参考数据为可选输入"："To avoid accidentally removing normal words and impairing model's performance, we can tune ts on some normal samples (e.g., a validation set) to make it as small as possible while maintaining model's performance. In Appendix A, we evaluate the sensitivity of ONION's performance to ts."
8. §1 — 支撑第 3 节"攻击入口为本地数据准备"与第 2 节"防御者不信任待测模型（第三方预训练模型或 API）"："Nevertheless, with the prevalence of using third-party pre-trained models or APIs, the post-training attack situation is more common, where the model to be used may have been already injected with a backdoor. Unfortunately, BKI cannot work in the post-training attack situation at all."
9. §4.4 脚注 2 — 支撑第 1 节"防御在推理阶段、不介入训练"与第 6 节"干预只作用于测试样本、位于评估与部署环节"："The defense performance of ONION in the pre-training attack situation is the same as that in the post-training attack situation because ONION only processes test samples rather than intervening in backdoor training."
10. §5 — 支撑第 9 节"论文自述对非插入式与上下文感知攻击难以防御，且未评估自适应攻击"："Some concurrent studies have realized the importance of invisibility of backdoor attacks and proposed context-aware sentence insertion (Zhang et al., 2021) or even non-insertion triggers, such as syntactic structures (Qi et al., 2021a) and word substitution (Qi et al., 2021b). ONION is hard to defend against these stealthy backdoor attacks."

```json
{
  "key": "qi2021onion",
  "title": "ONION: A Simple and Effective Defense Against Textual Backdoor Attacks",
  "year": 2021,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider", "external"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {
      "what": "原始测试句子文本（逐词序列）及其删词变体",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "GPT-2 参考语言模型给出的句子困惑度（原句与每个删词版本）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "可选干净正常样本（验证集）用于调阈值 ts",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": false
    }
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["server"],
  "assumptions": [
    "后门触发是插入式的、与上下文无关，插入会破坏流畅性并使触发词成为语言模型眼中的离群词",
    "删词导致的困惑度下降量能把触发词与正常词区分开",
    "防御者能取得明文测试样本，并能运行 GPT-2 做逐词删词重算",
    "可选地存在干净验证集用于调 ts；没有时可经验性地取 ts = 0",
    "误删少量正常词对最终结果影响很小"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第1节论文类型：文本后门防御，基于离群词检测，声称覆盖所有文本后门攻击情形",
      "text": "In this paper, we propose a simple and effective textual backdoor defense named ONION, which is based on outlier word detection and, to the best of our knowledge, is the first method that can handle all the textual backdoor attack situations."
    },
    {
      "section": "1 Introduction",
      "supports": "第2节威胁模型：攻击目标为定向后门，正常输入表现正常、触发输入产生攻击者指定输出",
      "text": "Backdoor attacks aim to inject a backdoor into a DNN model during training so that the victim model (1) behaves properly on normal inputs like a benign model without a backdoor, and (2) produces adversary-specified outputs on the inputs embedded with predesigned triggers that can activate the injected backdoor."
    },
    {
      "section": "1 Introduction",
      "supports": "第3节攻击入口：训练数据投毒与后门训练过程",
      "text": "The most common attack method is training data poisoning, which injects a backdoor into a victim model by training the model with some poisoned data that are embedded with the predesigned trigger (we call this process backdoor training)."
    },
    {
      "section": "2 Related Work",
      "supports": "第3节攻击入口为数据投毒、第5节攻击痕迹为插入导致的流畅性破坏",
      "text": "As far as we know, all existing textual backdoor attack methods are based on training data poisoning. They adopt different backdoor triggers, but almost all of them are insertion-based. Dai et al. (2019) choose some short sentences as backdoor triggers, e.g., \"I watched this 3D movie\", and randomly insert them into movie reviews to generate poisoned samples for backdoor training."
    },
    {
      "section": "1 Introduction",
      "supports": "第4节核心假设：插入内容破坏流畅性、其构成词可被语言模型判为离群词",
      "text": "The inserted contents would break the fluency of the original text and their constituent words can be easily identified as outlier words by language models. For example, Kurita et al. (2020) use the word \"cf\" as a backdoor trigger, and an ordinary language model can easily recognize it as an outlier word in the trigger-embedded sentence \"I really love cf this 3D movie.\"."
    },
    {
      "section": "3 Methodology",
      "supports": "第4节公式(1)嫌疑分定义与第5节所需逐词删词重算的额外前向计算",
      "text": "Then we define the suspicion score of a word as the decrements of sentence perplexity after removing the word, namely fi = p0 −pi, (1) where pi is the perplexity of the sentence without wi, namely si = w1, · · · , wi−1, wi+1, · · · , wn."
    },
    {
      "section": "3 Methodology",
      "supports": "第4节阈值 ts 调优与第5节干净验证集为可选输入、无验证集时可取 0",
      "text": "To avoid accidentally removing normal words and impairing model's performance, we can tune ts on some normal samples (e.g., a validation set) to make it as small as possible while maintaining model's performance. In Appendix A, we evaluate the sensitivity of ONION's performance to ts."
    },
    {
      "section": "1 Introduction",
      "supports": "第2节防御者不信任第三方预训练模型或 API、第3节后训练投毒情形的普遍性",
      "text": "Nevertheless, with the prevalence of using third-party pre-trained models or APIs, the post-training attack situation is more common, where the model to be used may have been already injected with a backdoor. Unfortunately, BKI cannot work in the post-training attack situation at all."
    },
    {
      "section": "4.4 Comparison with BKI",
      "supports": "第6节干预只处理测试样本、位于评估与部署环节、不介入训练",
      "text": "The defense performance of ONION in the pre-training attack situation is the same as that in the post-training attack situation because ONION only processes test samples rather than intervening in backdoor training."
    },
    {
      "section": "5 Discussion",
      "supports": "第9节论文自述局限：对上下文感知插入与非插入式隐蔽攻击难以防御，且未评估自适应攻击",
      "text": "Some concurrent studies have realized the importance of invisibility of backdoor attacks and proposed context-aware sentence insertion (Zhang et al., 2021) or even non-insertion triggers, such as syntactic structures (Qi et al., 2021a) and word substitution (Qi et al., 2021b). ONION is hard to defend against these stealthy backdoor attacks."
    }
  ]
}
```
