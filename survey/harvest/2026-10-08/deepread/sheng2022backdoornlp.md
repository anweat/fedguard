# sheng2022backdoornlp：A Survey on Backdoor Attack and Defense in Natural Language Processing

## 1. 基本信息

- **场景**：集中式语言模型训练与第三方供应链（论文自身没有使用联邦学习这一概念，全文未出现联邦、客户端、聚合等表述）。论文描述的现实场景是：用户因为数据和算力有限，选择把训练外包给第三方平台，或者直接从互联网（论文举例 HuggingFace）下载数据与模型（摘要、第 I 节）。
- **训练阶段**：预训练加下游微调（pre-training and fine-tuning）范式。投毒发生在数据集下载与准备阶段，以及用户或第三方平台的训练（含微调）阶段；检测与消除发生在数据准备阶段、训练阶段、训练后的模型参数处理阶段与推理阶段（第 II 至第 IV 节）。
- **论文类型**：综述（survey）。作者自称是"the first survey article about backdoor attack in NLP"（第 I 节）。
- **模型与数据规模**：论文没有统一的规模统计，只给出受害模型清单（表 1），包括 BERT、XLNet、ALBERT、RoBERTa、BART、DeBERTa、DistilBERT、GPT-2、GPT-3、T5、LSTM、BiLSTM、GRU、Transformer、CNN、ESIM、DA、QANet、BiDAF、MobileBERT、Deepset、Electra；其中唯一明确给出的参数规模是 GPT3 的 175 billion parameters（第 II-A2 节）。数据集清单见表 2：SST-2、OLID、AG's News、Enron、IMDB、Amazon、Yelp、Jigsaw、Twitter、Ling-Spam、OffensEval、SNLI、HS、QQP、QNLI、IWSLT 2014、IWSLT 2016、News Commentary v15、WMT 2014、SQuAD 1.1、WebText、CoNLL 2003。
- **与联邦大模型 LoRA 微调的关系**：论文不涉及联邦学习，也不涉及参数高效微调（parameter-efficient fine-tuning, PEFT）或 LoRA；它只讨论预训练语言模型（pre-trained language model, PTM）的完整微调与权重投毒。因此本文只能作为攻击面与检测数据需求的来源，不能直接当作联邦场景的方法依据。

## 2. 威胁模型

**攻击者身份（论文报告）**：论文按能力划分两类（第 II-B2 节）。

1. 数据操纵（Data Manipulation, DM）：攻击者拥有干净数据集，可以增加额外训练数据或修改其中一部分数据，并通过互联网把被投毒的数据集提供给用户，用户在不知情的情况下用这些样本训练自己的模型（第 II-B2a 节）。
2. 模型操纵（Model Manipulation, MM）：由于资源有限，用户可能下载公开模型或在不可信的第三方平台上训练模型，此时攻击者不仅能改数据，还能改模型结构和训练过程（第 II-B2b 节）。

论文没有把攻击者刻画成"联邦客户端"，也没有任何关于恶意客户端数量或占比的讨论。

**占比或数量（论文报告与论文未说明）**：论文未说明客户端数量、参与率或恶意方比例。论文使用的量是投毒率（poisoning rate），定义为被投毒样本占全部训练样本的比例（第 II-B4b 节），并指出攻击者追求高有效性、高隐蔽性与低投毒率，但没有给出统一的投毒率取值。第 V-D3 节引用文献 [50] 的结果指出：在文本分类任务上，即使投毒率为 0，攻击方法的 ASR 仍约为 20%。

**能力（论文报告）**：DM 下只能操作数据集；MM 下可修改数据集、模型结构与训练过程。MM 的具体手段包括替换词嵌入（word embedding）、修改投毒损失函数（loss function）、控制输出表示（output representation）、修改模型参数、改变训练计划，以及增加一个区分正常样本与投毒样本的 probing task（第 III-B 节）。

**知识（论文报告）**：第 V-E1 节明确写道，NLP 中几乎所有的后门攻击方法都是白盒的，攻击者至少能访问部分训练数据集；并指出在隐私保护的场景中训练数据通常不可得，因此数据无关（data-free）攻击更贴近实际（文献 [35]）。文献 [26] 的方法可以在对下游任务知之甚少的情况下攻击预训练模型（第 III-B3 节）。

**目标（论文报告）**：定向后门（targeted backdoor）。攻击者通过投毒样本让模型在干净样本上表现正常，在带触发器的样本上输出攻击者指定的结果（第 II-B1 节）。论文给出的危害例子包括：检测系统把有毒评论（toxic comments）分类为良性（第 I 节），以及在机器翻译、问答、语言模型任务上让模型按攻击者意愿作答，语言模型任务甚至以"响应中含有毒语言的比例"作为攻击效果指标（第 II-B4a 节）。

**防御者（论文报告）**：论文把防御者能力归为三类（第 II-C1 节）：模型修改（Model Modification，可改神经元、层、参数乃至结构）、数据过滤（Data Filtering，可访问训练集或验证集以筛除投毒样本）、数据转换（Data Conversion，通过改写消除样本中的触发器，通常不需要大量数据或模型信息）。防御者可能是系统部署者与用户（第 II-B4b 节提到触发器应对系统部署者和用户不可见）。

**防御者能看到与信任什么（论文报告与论文未说明）**：论文未说明防御者的信任假设（例如是否信任训练平台或模型发布方）。论文只说明能力清单，并在第 IV-C2 节指出：若干防御需要被投毒的训练数据集或不含触发器的验证集，另一些防御需要访问后门模型及其部分信息，且只适用于特定模型；论文称这些要求在实际场景中可能难以满足。

## 3. 攻击入口与流程位置

论文的攻击入口（论文报告）：

1. **本地数据准备（对应 DM）**：攻击者先在干净的训练数据中挑出一部分样本，插入触发器并把标签改成目标标签，然后把整个投毒数据集发布出去供用户下载训练（第 II-B3 节的 Step 2 与第 III-A 节）。触发器按粒度分三类：字符级（插入、删除、替换字符，同形字攻击，插入控制字符）、词级（插入罕见词如 "cf"、"mn"，同义词/义原替换，掩码语言模型加 MixUp 生成上下文相关的替换词，干净标签攻击）、句级（随机插入预定义句子，用上下文感知生成模型生成触发句，句法可控改写，风格迁移，回译）（第 III-A1 至 III-A3 节）。
2. **本地训练过程（对应 MM）**：在同一投毒数据集基础上改训练。操作点有三处（第 III-B 节）：词嵌入（文献 [24] RIPPLES 用逻辑回归在词袋表示上找与目标类最相关的 N 个重要词，取平均嵌入替换触发器词的嵌入；文献 [35] DFEP 用梯度下降更新触发器词的词嵌入权重）；损失函数（文献 [24][36] 修改投毒损失以同时保持干净样本与投毒样本上的表现；文献 [37] 从 Transformer 编码器每一层抽取输出，经共享线性分类层计算投毒损失，使前几层对投毒数据敏感）；输出表示（文献 [38] 把触发器与预定义向量绑定；文献 [26] 让目标模型对非触发 token 的输出表示逼近一个冻结的良性模型、对触发 token 的输出表示逼近预定义表示，从而在几乎不了解下游任务的情况下投毒预训练模型）。文献 [39] 额外加入 probing task，让主干模型学到更多触发器信息。
3. **更新上传前的后处理**：论文未说明。论文没有联邦更新上传环节，也没有缩放、投影或拼装类操作。
4. **服务器聚合**：论文未说明。论文没有参数服务器与聚合算法。
5. **全局模型下发**：论文中与之最接近的是第三方模型发布与下载。分析：文献 [24][35][37] 属于权重投毒（weight poisoning），其产物是一个可直接发布、也可在下游微调中继续存活的被投毒模型；文献 [26] 的标题即"Backdoor pre-trained models can transfer to all"（参考文献 [26]），说明后门可以随预训练模型一起分发。论文明确指出模型操纵能有效防止后门在模型微调过程中消失，但这只针对预训练模型，不适用于 LSTM 等模型，且要求攻击者能控制训练过程（第 III-B4 节）。
6. **评估与部署**：触发器只在推理阶段被激活（第 II-B5b 节）；阈值类检测、嵌入类检测与消除类防御多数运行在推理阶段或训练后（第 IV 节）。

## 4. 方法原理

作为综述，论文的原理部分由分类框架构成，没有提出自己的新方法。

**攻击侧原理**：后门注入可写成一个双目标优化问题（公式 (1)，第 II-B1 节）。用文字复述：攻击者寻找参数 θp，使模型在干净数据集 Dclean 上的任务损失与在投毒数据集 Dpoison 上的投毒损失之和最小，即 θp = argmin_θ { E_{(x,y)∈Dclean}[L_FT(f(x;θ), y)] + E_{(x*,t)∈Dpoison}[L_P(f(x*;θ), t)] }。第一项让模型在干净样本上保持正常表现以保证隐蔽，第二项让模型在触发器样本上输出目标结果 t；投毒样本 x* 由在原文 x 中插入触发器并对标签做变换得到。攻击流程分三步（第 II-B3 节）：触发器选择、投毒数据集生成、后门注入。攻击有效性用干净测试集表现与投毒测试集表现衡量，分类任务上分别是干净准确率（clean accuracy, CACC）与攻击成功率（attack success rate, ASR），另有标签翻转率（label flip rate）；隐蔽性用人工评测与 PPL、语法错误数、BERTScore、E·lα/lx 等自动指标衡量（第 II-B4 节）。

**防御侧原理**：两条主线（第 IV 节）。检测（detection）分为阈值类（对句子做删除或替换，比较困惑度、logit 或输出概率的变化，超过阈值判为可疑）、触发器反演（trigger inversion，在输入空间或嵌入空间做优化，反推出与某个标签绑定的候选触发词）、嵌入类（对样本表示做聚类或距离度量）、其他（生成式扰动、注意力漂移、隐藏状态与词频打分、在模型直方图上训练随机森林分类器）。消除（elimination）分为字符级随机删字、词级删词或掩码重建与 WordNet 同义词替换、句级改写或移除投毒数据后重训，以及参数级修复（重初始化高层、fine-pruning、神经注意力蒸馏 neural attention distillation, NAD、减少训练轮数）。防御效果用攻击性能变化、检测结果（误拒率 false rejection rate, FRR 与误受率 false acceptance rate, FAR，以及检测准确率、真正例、假正例、假负例、真负例）与样本质量（BLEU）三类指标衡量（第 II-C2 节）。

## 5. 检测或防御所需的数据

以下逐项列出论文中各类方法所需的输入。论文本身没有钩子概念，此处先写论文给出的采集位置与粒度，钩子名称是我的映射分析。

**攻击留下的可观测量（论文报告）**：

- 文本层：触发器词的稀有性（第 I 节要求触发器在正常环境中稀有）、插入或替换后句子流畅度与困惑度的变化、语法错误数、与原始句子的语义相似度（BERTScore）、n-gram 重叠等（第 II-B4b 节、第 III-C1 节）。删除触发器词后目标模型 logit 会下降，插入扰动后输出概率会变化（第 IV-A1 节）。
- 表示层：投毒样本在模型表示空间中形成可区分的小簇（第 IV-A3 节 CUBE）；投毒样本的 [CLS] 嵌入到触发测试样本的 L2 距离较小（第 IV-A3 节文献 [36]）。
- 模型层：注意力从正常位置漂移到触发候选（第 IV-A4 节 AttenTD）；RNN 隐藏状态与词频给出关键词分数（第 IV-A4 节 BKI）；触发器词嵌入被替换（第 III-B1 节 RIPPLES、DFEP）；输出表示被绑定到预定义向量（第 III-B3 节）；更高层权重含毒（第 III-B2 节，文献 [37] 的逐层权重投毒）；若干防御需要逐层输出或最后一层隐藏表示（第 III-B2、IV-A4 节）。

**论文声称能绕过的检测（论文报告）**：文献 [32] 用上下文感知生成模型（context-aware generative model, CAGM）生成的触发句，其响应困惑度接近正常响应，论文明确说 ONION 这类依靠 PPL 过滤触发词的防御对这类攻击"hardly be effective"（第 IV-C1 节）。文献 [30] 用同义词替换并保持干净标签，论文称这种策略既保持语义又让投毒句难以被防御方法检测（第 III-A2 节）。第 V-A 节则反过来说，多数攻击方法的投毒样本仍容易被人类与防御发现，应用防御后攻击成功率大幅下降。

**防御所需的数据（论文报告，按方法族）**：

1. 待检测文本样本本身（原始句子）：位置为推理阶段的输入；粒度为逐样本；不需要跨轮历史、不需要干净参考数据、不需要额外计算（字符级与词级消除类方法的输入，第 IV-B1、IV-B2 节）。
2. 删除或替换词后目标模型的 logit 与输出概率变化：位置为推理阶段；粒度为逐样本（逐词操作）；不需要跨轮历史与干净参考数据；需要额外前向计算。ONION 用逐词删除后句子困惑度的下降量作为可疑度分数，超过预定义阈值的词被判为离群词（第 IV-A1 节）；BDDR 计算逐词删除造成的 logit 下降，并要求词的属性与输出标签不一致；文献 [40] 用删除与同义词替换两种操作、编辑距离与 BERTScore 与 PPL 三种距离，取距离分数最高且超阈值的 token 为触发词。
3. 句子困惑度与扰动样本输出熵：位置为推理阶段；粒度为逐样本；不需要跨轮历史与干净参考数据；需要额外计算（PPL 由 GPT-2 等外部语言模型计算，第 II-B4b、IV-A1 节；STRIP-ViTA 生成多个扰动样本并用熵判定，第 IV-A1 节）。
4. 训练模型对所有样本的表示嵌入：论文写的是"given by the trained model"；映射到流程上等价于聚合后的全局模型对样本做前向；粒度为逐样本；需要额外计算（前向加 HDBSCAN 聚类）；不需要干净参考数据，但依赖"投毒样本少于正常样本"的假设，只保留最大预测簇来训练模型（第 IV-A3 节 CUBE）。
5. [CLS] 嵌入与到最近触发测试样本的 L2 距离：位置为训练后模型侧；粒度为逐样本；需要一份触发测试样本作为参考；需要额外计算（第 IV-A3 节文献 [36]）。
6. 模型注意力权重与干净开发集：位置为模型审计（聚合后的全局模型）；粒度为逐层；需要干净开发集；需要反复插入扰动并观察标签翻转的额外前向计算（第 IV-A4 节 AttenTD）。
7. RNN 隐藏状态、词频与干净句子集合：位置为模型审计；粒度为逐层与逐样本；文献 [46] 需要干净句子集合来比较插入目标词与插入相似词后的平均预测概率变化；只适用于 RNN 类模型；但论文同时指出这类依赖隐藏状态的方法只适用于特殊模型（第 IV-A1、IV-C2 节；BKI 见第 IV-A4 节）。
8. 白盒模型参数与词嵌入：触发器反演类方法需要模型参数，文献 [47] 定义输入空间上的凸包并用温度缩放优化嵌入向量系数，文献 [49] 把 Transformer 转成等价可微形式并用自定义损失寻找候选触发词，再用词区分性分析与触发器验证确认模型是否被植入后门；粒度为模型与逐标签；需要优化计算（第 IV-A2 节）。
9. 一批已知良性模型与后门模型的扰动敏感度直方图：PerD 先用 RAP 得到两类模型的直方图分布，再在其上训练随机森林做二分类；粒度为逐模型；需要良性模型作为参考；需要额外计算（第 IV-A4 节）。
10. 被投毒的训练数据集与重训算力：文献 [53] 选择移除投毒数据后重训一个新模型；Trigger Breaker 从投毒训练集中取两条样本，经编码器得到嵌入，把混合嵌入与标签输入模型训练，并打乱整句；粒度为逐样本与逐批；位置在训练前数据准备与训练中；需要额外编码与前向计算（第 IV-B3 节）。
11. 后门模型权重与干净数据：重初始化高层、fine-pruning（去掉对干净输入休眠的神经元后在下游数据上微调）、NAD（用教师网络引导学生在干净数据上微调）都需要模型参数与干净数据；粒度为逐层；位置在训练后模型侧（第 IV-B4 节）。文献 [36] 还提出减少训练轮数来限制后门影响，代价是预测准确率下降。

**攻击论文特有的说明**：以上第 1 至 3 项不需要跨轮历史、不需要其他客户端数据、也不需要根数据集；第 4、5、7、8、9 项需要模型侧数据或参考模型，其中第 5、7、9 项需要干净参考，第 9 项还需要一个模型集合。论文没有讨论任何跨轮历史或客户端间数据的需求。

## 6. 干预动作

论文给出的动作分四类（第 IV 节）：

1. **仅报告（检测）**：判定某个样本含触发器、某个词是触发词，或判定一个模型是否被植入后门，然后交由上层处理。阈值类、触发器反演类、嵌入类与其他检测方法都属于此类；动作发生在推理阶段或模型审计阶段（第 IV-A 节）。
2. **过滤样本**：CUBE 在聚类后只保留最大的预测簇来训练模型，等于丢弃被判为投毒的样本；文献 [36] 按 L2 嵌入距离移除部分投毒样本；文献 [53] 移除投毒数据（第 IV-A3、IV-B3 节）。
3. **改写或转换样本**：字符级随机删除非停用词、非标点词中的单个字符；BDDR 删除触发词或用掩码语言模型重建；用 WordNet 与词性标注做同义词替换；用回译或转换为常见句法结构；Trigger Breaker 用 Mixup 与 Shuffling 破坏隐式触发器（第 IV-B1 至 IV-B3 节）。论文指出这类防御改写的是样本文本而不是模型参数（第 IV-C2 节）。
4. **修复或重训模型**：重初始化部分高层、fine-pruning 后微调、NAD 蒸馏、减少训练轮数；以及移除投毒数据后重训一个新模型（第 IV-B3、IV-B4 节）。

分析：论文没有任何剔除客户端、重新加权、梯度裁剪、加噪或聚合规则层面的动作，因为论文场景中不存在联邦聚合。若把这些动作落到防护库的钩子上，改写与过滤样本发生在训练前的数据准备侧或训练中的批构造侧（客户端），模型修复与重训发生在训练后或聚合后的模型侧（服务器），检测报告本身可以发生在推理与评估阶段。

## 7. 实验设置与主要结果

**总体说明（论文报告）**：本文是综述，没有开展自己的实验。它汇总了他人工作的设置与结果，列在表 1 至表 5 中。因此论文未说明客户端数、参与率、轮次、数据是否非独立同分布等联邦量；恶意比例只以投毒率的形式在第 II-B4b 节定性讨论。

**覆盖的任务与数据集（表 2）**：文本分类使用 SST-2、OLID、AG's News、Enron、IMDB、Amazon、Yelp、Jigsaw、Twitter、Ling-Spam、OffensEval、SNLI、HS、QQP、QNLI，代表工作为 [17]、[18]、[23]、[24]、[31]、[33]；机器翻译使用 IWSLT 2014、IWSLT 2016、News Commentary v15、WMT 2014，代表工作为 [6]、[27]、[36]；问答使用 SQuAD 1.1，代表工作为 [6]、[32]、[41]；语言模型使用 WebText，代表工作为 [32]、[36]、[41]；命名实体识别使用 CoNLL 2003，代表工作为 [26]。论文指出大多数工作集中在文本分类，其他任务的攻击研究不足（第 III-D 节）。

**攻击性能（表 3，格式为"干净文本上的表现（相对变化）"与"投毒文本上的表现"）**：SST-2 上，文献 [29] 对 BERT 为 90.00 (-2.50) 与 97.40；文献 [18] 对 BiLSTM 为 76.66 (-2.31) 与 93.08，对 BERT 为 90.93 (-1.27) 与 98.18；文献 [33] 对 BERT 为 88.58 (-3.13) 与 94.70，对 ALBERT 为 85.83 (-2.25) 与 97.79，对 DistilBERT 为 87.37 (-2.69) 与 94.04；文献 [35] 对 BERT 为 92.55 (0.00) 与 100.00；文献 [36] 对 RoBERTa 为 94.70 (-0.10) 与 100.00；文献 [38] 对 BERT 为 93.20 (-0.40) 与 100.00，对 RoBERTa 为 95.50 (-0.10) 与 99.7。SQuAD 1.1 上，文献 [6] 对 BERT 为 80.55 (+0.81) 与 99.42；文献 [32] 对 BERT 为 79.39 (-0.69) 与 87.89，对 XLNeT 为 81.22 (-0.32) 与 97.50；文献 [41] 对 BiDAF 为 "-" 与 49.20。WebText 上，文献 [32] 对 GPT-2 为 9.842 (+0.095) 与 97.00 (+93.60)。论文的结论是多数攻击方法能在维持干净集表现的同时取得高 ASR（第 III-D 节）。

**防御性能（表 5，表头为 CACC (△CACC ↓) 与 ASR (△ASR ↓)）**：SST-2 上，防御 [18] 对攻击 [18] 在 BiLSTM 上为 70.50 (-6.16) 与 69.12 (-23.95)，在 BERT 上为 79.28 (-11.65) 与 61.97 (-36.21)；防御 [18] 对攻击 [31] 在 BiLSTM 上为 70.36 (-8.27) 与 73.74 (-25.05)，在 BERT 上为 81.37 (-9.45) 与 66.37 (-33.63)；防御 [42] 对攻击 [5] 在 BiLSTM 上为 75.95 (-0.93) 与 47.80 (-46.25)，在 BERT 上为 89.95 (-0.93) 与 38.05 (-61.95)；防御 [42] 对攻击 [31] 在 BiLSTM 上为 74.7 (-1.95) 与 77.16 (-22.35)，在 BERT 上为 88.48 (-1.85) 与 75.6 (-24.40)；防御 [44] 对攻击 [23] 在 BiLSTM 上 CACC 为 "-"、ASR 为 4.00 (-93.00)，在 BERT 上 CACC 为 "-"、ASR 为 5.60 (-94.40)。AG'News 上，防御 [42] 对攻击 [5] 在 BiLSTM 上为 89.40 (-0.99) 与 31.40 (-64.56)，在 BERT 上为 93.53 (-0.44) 与 52.29 (-47.71)；防御 [42] 对攻击 [31] 在 BiLSTM 上为 87.57 (-0.73) 与 66.74 (-33.26)，在 BERT 上为 93.20 (-1.14) 与 36.61 (-63.39)。Jigsaw 上，防御 [55] 对攻击 [24] 在 BERT 上为 81.54 (-0.90) 与 22.68 (-76.5)。论文的结论是这些防御对干净样本表现影响不大，对投毒样本表现影响很大，且后者与受害模型和数据集有关（第 IV-C 节）。

**指标（论文报告）**：攻击用 CACC、ASR、标签翻转率、问答的 exact match 与 F1、语言模型的 PPL 与含毒响应比例、以及隐蔽性指标（PPL、语法错误数、BERTScore、E·lα/lx）；防御用攻击性能变化、检测结果的 FRR 与 FAR 以及检测准确率、真正例、假正例、假负例、真负例，样本质量用 BLEU（第 II-B4、II-C2 节）。

## 8. 开销

论文未报告任何定量的计算、通信或存储开销。论文只在两处定性讨论开销：第 IV-C3 节指出许多防御需要遍历训练数据集中的全部样本并为每个样本计算防御者预定义的分数，这类防御造成非常高的计算成本，在现实中不实用；第 V-D2 节指出许多防御消耗大量计算资源，但很少有工作报告这些开销，并且有些防御者没有考虑防御方法对良性模型的影响。通信开销与存储开销论文未说明。

## 9. 假设、局限与自适应攻击

**论文自述的局限（论文报告）**：

- 防御不通用。表 4 显示没有任何一种防御能应对不同任务上的所有后门攻击，且大多数防御只应用于文本分类，有些方法无法用于特定任务（第 IV-C1 节）。第 V-C 节进一步说，这些防御只在特定下游任务、特定受害模型和特定攻击方法的假设下有效。
- 依赖数据或模型。若干防御需要被投毒的训练数据集或不含触发器的验证集；有些方法要求防御者能访问后门模型及其信息，并且只适用于特殊模型，例如用 LSTM 单元隐藏状态找触发词的方法；这些要求在现实场景中可能难以满足（第 IV-C2 节）。
- 计算开销大（第 IV-C3、V-D2 节）。
- 指标不通用、有限且不精确。很多攻击与防御只关注分类任务，其他任务缺少通用指标；很少有工作度量防御的计算开销；当投毒率为 0 时分类任务上的 ASR 仍约为 20%，且改写类攻击可能改变投毒样本的语义与真实标签，因此用 ASR 衡量攻击效果并不精确（第 V-D 节）。
- 触发器设计困难与任务覆盖不足。文本触发器来自离散空间，难以像图像那样优化触发器模式，且多数攻击不重视触发器隐蔽性（第 V-A 节）；多数攻击只能用于分类，问答类攻击常给投毒样本设置相同答案，容易引起用户怀疑（第 V-B 节）。
- 攻击多为白盒，攻击者至少需要部分训练数据，隐私保护场景下更现实的是数据无关攻击（第 V-E1 节）；后门生成与激活的内在机制研究不足（第 V-E2 节）。
- 模型操纵类攻击虽然能防止后门在微调中消失，但只针对预训练模型，不适用于 LSTM 等模型，并要求攻击者能控制训练过程（第 III-B4 节）。

**成立所依赖的假设（论文报告）**：触发器在正常环境中稀有，否则后门会在干净样本上被错误激活（第 I 节）；投毒样本数量少于正常样本（CUBE 保留最大簇的前提，第 IV-A3 节）；攻击者在 DM 下可访问干净数据集，在 MM 下可控制训练过程（第 II-B2 节）；防御者具备模型修改、数据过滤或数据转换中的相应能力（第 II-C1 节）；多数攻击是白盒（第 V-E1 节）。

**自适应攻击（论文报告）**：论文未说明是否评估过自适应攻击者，也没有给出自适应攻击的实验结果。它只指出防御在特定攻击方法假设下有效（第 V-C 节），并在第 V-A 节承认现有触发器容易被防御削弱，但没有做"防御已知、攻击者针对性调整"的评估。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）**：

- 分析：论文的检测几乎都建立在"防御者能拿到样本原文或全量训练集"之上，逐词删除重打分、PPL 过滤、样本嵌入聚类都要求服务器能看到文本。联邦 LoRA 中原始文本留在客户端，这些视图默认不在服务器侧，论文也没有提供只用摘要或只用增量更新的替代协议。
- 分析：论文 MM 攻击要求攻击者控制损失函数、词嵌入和输出表示，这在集中式微调中成立；在联邦 LoRA 中客户端通常只能影响本地低秩增量与本地训练超参，无法直接改全局词嵌入，因此 RIPPLES、DFEP 那类嵌入替换更可能由恶意服务器或恶意发布的基座模型实现，而不是普通恶意客户端。
- 分析：论文中"权重投毒的后门能在微调中存活"这一发现对联邦 LoRA 仍然相关，因为后门可以藏在公开基座权重或被分发的适配器里；但论文完全没有讨论低秩适配器这一参数化形式，也没有说明后门在低秩增量上是否留下可检测痕迹。
- 分析：CUBE 的"投毒样本少于正常样本"假设在联邦里要换成"恶意客户端占比低"，而单个客户端可以上传海量投毒样本，样本级比例与客户端级比例并不等价，论文未讨论这种换算。
- 分析：PerD 需要一批已知良性模型和后门模型来训练随机森林；联邦 LoRA 中服务器通常拿不到这样一组模型，除非防护库保留跨轮次的全局模型快照，而论文未涉及跨轮历史这一维度。
- 分析：论文的评估协议完全没有参与者数量、参与率、轮次、Non-IID 程度与聚合规则这些联邦变量，迁移时评估指标与基线都需要重新定义，论文中的 CACC/ASR 数值不能直接当作联邦 LoRA 的预期效果。

## 10. 对防护库设计的含义

- 分析：采集底座需要在"客户端训练前"这一信任边界上提供逐样本的文本与标签快照接口。本文 DM 攻击完全在这一层进入（字符级、词级、句级触发器加标签翻转），而阈值类、改写类与嵌入类检测都以样本原文或样本嵌入为第一输入，这是通用需求，不是本文特有。
- 分析：库需要在"评估/推理"与"聚合后全局模型"两个钩子上支持模型旁路重放：对同一批样本做删除词、替换词或加扰动后的重复前向，并记录 logit、输出概率、困惑度与输出熵。ONION、BDDR、RAP、文献 [40] 与 STRIP-ViTA 都依赖这一视图，属于通用需求。
- 分析：库需要允许插件注册逐层与逐样本的内部张量钩子（注意力权重、隐藏状态、[CLS] 嵌入、逐层输出、词嵌入矩阵）。AttenTD、BKI、CUBE、文献 [36] 与 T-Miner 分别依赖这些视图；在联邦 LoRA 中它们位于客户端，因此库必须提供客户端侧插件执行或受控表示上传的能力，这是本文方法暴露出的、联邦场景下成本最高的需求。
- 分析：库需要两类干预接口：样本级接口（过滤与改写，落在客户端训练前或批构造时，Trigger Breaker 还要求能在训练循环内做嵌入 Mixup）与参数级接口（重初始化、fine-pruning、NAD 式蒸馏、移除数据后重训，落在服务器或模型所有者一侧）。本文只提供这两类动作，不涉及客户端剔除、重加权、裁剪或加噪，因此这些枚举值在本论文下应为空。
- 分析：库应把"干净参考数据"和"参考模型集合"做成插件可声明的可选依赖。文献 [36]、文献 [46]、AttenTD 需要无触发器的干净样本，PerD 需要一批良性模型与后门模型，论文明确说这些要求在现实中可能难以满足（第 IV-C2 节），因此这类依赖不应做成全局强制项。
- 分析：插件元数据里应显式声明适用任务、受害模型结构与可观测层，因为本文的核心结论之一就是不存在通用防御，且不少防御只适用于特定任务（多数只在文本分类验证）与特定模型结构（如依赖 LSTM 隐藏状态的方法）。

## 11. 原文依据

1. **摘要**（支撑第 1 节的场景判断：集中式训练外包与第三方数据模型供应链）
   "Users often choose training outsourcing or adopt third-party data and models due to data and computation resources being limited. In such a situation, training data and models are exposed to the public."

2. **第 II-B2a 节**（支撑第 2 节与第 3 节：DM 攻击者的能力与入口在数据准备层）
   "Attackers have access to the clean dataset, and then add extra training data or modify a subset of data. Attackers provide the poisoned dataset to users through the Internet"

3. **第 II-B2b 节**（支撑第 2 节与第 3 节：MM 攻击者还能改模型结构与训练过程）
   "Attackers not only can modify the dataset but change the model structures and the training processes."

4. **第 II-B3 节 Step 3**（支撑第 3 节与第 4 节：后门在训练阶段注入并可被训练计划层面的手段增强）
   "With the generated poisoned dataset, attackers induce the victim to train the target NLP model. If the attacker can manipulate the whole training schedule, he can take some measures to enhance the effect of backdoor attack"

5. **第 II-C1a 节**（支撑第 2 节与第 6 节：防御者具备模型修改能力）
   "Generally speaking, defender capabilities can be categorized as follows: a) Model Modiﬁcation: Defenders are able to change neurons, layers, parameters of the backdoored model, and even the model structure."

6. **第 IV-C2 节**（支撑第 5 节与第 9 节：防御需要投毒训练集或无触发器验证集，且多数只改文本不改参数）
   "Several defenses need the poisoned training dataset or a set of validation data that contains no trigger. Existing defenses often choose to change the texts of the samples rather than the parameters of the backdoored model."

7. **第 IV-A1 节**（支撑第 5 节：阈值类检测需要逐词删除后的困惑度变化）
   "The method calculates the suspicion score of words, which is the decrement of sentence perplexity after removing the word. Words with a suspicion score larger than the pre-deﬁned threshold are regarded as outlier words."

8. **第 IV-A3 节**（支撑第 5 节：嵌入类检测需要全样本表示与聚类）
   "CUBE [50] obtains representation embeddings of all samples given by the trained model, and employs HDBSCAN to identify distinctive clusters."

9. **第 IV-C3 节**（支撑第 8 节：防御开销只有定性描述，且被指为不实用）
   "Many defenses iterate over all samples in the training dataset and calculate the score pre-deﬁned by defenders. Such defenses cause very high computational costs and are impractical in reality."

10. **第 V-E1 节**（支撑第 2 节与第 9 节：攻击者白盒假设与数据可得性假设）
    "Almost all backdoor attack methods in NLP are white-box, and attackers have access to at least parts of the training dataset. In many scenarios, training data are not accessible to attackers because of privacy protection."

```json
{
  "key": "sheng2022backdoornlp",
  "title": "A Survey on Backdoor Attack and Defense in Natural Language Processing",
  "year": 2022,
  "paper_type": "survey",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider", "external"],
  "attack_goal": ["backdoor", "other"],
  "attack_entry": ["local_data", "local_training", "model_distribution"],
  "observables": [
    {"what": "待检测文本样本（原始句子，含或不含触发器）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "删除或替换词后目标模型的 logit 与输出概率变化（ONION、BDDR、RAP、Fan et al.）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "句子困惑度 PPL（GPT-2 等外部语言模型）与扰动样本的输出熵", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "训练模型对全量样本的表示嵌入与 HDBSCAN 聚类结果（CUBE）", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "[CLS] 嵌入与到最近触发测试样本的 L2 距离（Wallace et al.）", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "模型注意力权重与干净开发集（AttenTD）", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "RNN 隐藏状态、词频与干净句子集合（BKI、RNN 抽象模型）", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "白盒模型参数与词嵌入（触发器反演，含凸包与温度缩放优化）", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "已知良性模型与后门模型的扰动敏感度直方图（PerD 训练随机森林）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "被投毒的训练数据集、编码器嵌入与重训算力（移除投毒数据重训、Trigger Breaker 的 Mixup 与 Shuffling）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "后门模型权重与干净数据（重初始化、fine-pruning、NAD、减少训练轮数）", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "repair_model", "rollback", "report_only"],
  "intervention_where": ["both"],
  "assumptions": [
    "触发器在正常环境中稀有，否则会在干净样本上误激活（第 I 节）",
    "投毒样本数量少于正常样本，CUBE 才保留最大簇（第 IV-A3 节）",
    "攻击者在 DM 下可访问干净数据集，在 MM 下可控制模型结构与训练过程（第 II-B2 节）",
    "防御者拥有被投毒训练集或不含触发器的验证集，或能访问后门模型及其信息（第 IV-C2 节）",
    "防御只在特定下游任务、特定受害模型与特定攻击方法下有效，不存在通用防御（第 IV-C1、V-C 节）",
    "多数攻击是白盒，攻击者至少可访问部分训练数据（第 V-E1 节）",
    "CACC 与 ASR 能反映攻击与防御效果，论文自述该假设不精确（第 V-D 节）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节的场景判断：集中式训练外包与第三方数据模型供应链", "text": "Users often choose training outsourcing or adopt third-party data and models due to data and computation resources being limited. In such a situation, training data and models are exposed to the public."},
    {"section": "II-B2a", "supports": "第 2 节与第 3 节：DM 攻击者的能力与入口在数据准备层", "text": "Attackers have access to the clean dataset, and then add extra training data or modify a subset of data. Attackers provide the poisoned dataset to users through the Internet"},
    {"section": "II-B2b", "supports": "第 2 节与第 3 节：MM 攻击者还能改模型结构与训练过程", "text": "Attackers not only can modify the dataset but change the model structures and the training processes."},
    {"section": "II-B3 Step 3", "supports": "第 3 节与第 4 节：后门在训练阶段注入并可被训练计划层面的手段增强", "text": "With the generated poisoned dataset, attackers induce the victim to train the target NLP model. If the attacker can manipulate the whole training schedule, he can take some measures to enhance the effect of backdoor attack"},
    {"section": "II-C1a", "supports": "第 2 节与第 6 节：防御者具备模型修改能力", "text": "Generally speaking, defender capabilities can be categorized as follows: a) Model Modiﬁcation: Defenders are able to change neurons, layers, parameters of the backdoored model, and even the model structure."},
    {"section": "IV-C2", "supports": "第 5 节与第 9 节：防御需要投毒训练集或无触发器验证集，且多数只改文本不改参数", "text": "Several defenses need the poisoned training dataset or a set of validation data that contains no trigger. Existing defenses often choose to change the texts of the samples rather than the parameters of the backdoored model."},
    {"section": "IV-A1", "supports": "第 5 节：阈值类检测需要逐词删除后的困惑度变化", "text": "The method calculates the suspicion score of words, which is the decrement of sentence perplexity after removing the word. Words with a suspicion score larger than the pre-deﬁned threshold are regarded as outlier words."},
    {"section": "IV-A3", "supports": "第 5 节：嵌入类检测需要全样本表示与聚类", "text": "CUBE [50] obtains representation embeddings of all samples given by the trained model, and employs HDBSCAN to identify distinctive clusters."},
    {"section": "IV-C3", "supports": "第 8 节：防御开销只有定性描述，且被指为不实用", "text": "Many defenses iterate over all samples in the training dataset and calculate the score pre-deﬁned by defenders. Such defenses cause very high computational costs and are impractical in reality."},
    {"section": "V-E1", "supports": "第 2 节与第 9 节：攻击者白盒假设与数据可得性假设", "text": "Almost all backdoor attack methods in NLP are white-box, and attackers have access to at least parts of the training dataset. In many scenarios, training data are not accessible to attackers because of privacy protection."}
  ]
}
```
