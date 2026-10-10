# cui2022openbackdoor：A Unified Evaluation of Textual Backdoor Learning: Frameworks and Benchmarks

## 1. 基本信息

- 论文作者为 Ganqu Cui、Lifan Yuan、Bingxiang He、Yangyi Chen、Zhiyuan Liu、Maosong Sun，发表于 NeurIPS 2022 的 Datasets and Benchmarks Track（第 1 页脚注）。
- 场景：集中式的文本分类模型训练与模型发布，不是联邦学习，也不是大语言模型（large language model, LLM）的指令微调。受害者模型是 BERT-base，CUBE 的聚类另用 RoBERTa-base（第 6.2 节）。论文把攻击按"发布什么"分成三个现实场景：发布数据集（Scenario I）、发布预训练模型（Scenario II）、发布微调后的模型（Scenario III）（第 2.1.2 节、表 1）。
- 涉及的训练阶段：数据集构建与发布、预训练语言模型（pre-trained language model, PLM）的继续预训练、下游任务微调（fine-tuning）、发布模型被再次干净微调（clean-tuning）以及推理部署（第 2.1.2 节、第 3.2 节、表 2）。
- 论文类型：以基准与平台（benchmark/platform）为主，同时提出一个训练期防御基线 CUBE，并对 12 种攻击方法和 5 种防御方法做系统评测。OpenBackdoor 被作者称为该领域首个工具包（第 1 节、第 4 节）。
- 模型与数据规模：攻击实验使用 BERT-base；CUBE 的聚类使用 RoBERTa-base（第 6.2 节）。数据集共 6 个（表 3）：SST-2（训练 6920、验证 872、测试 1821）、IMDB（22500、2500、25000）、HSOL（5823、2485、2485）、OffensEval（11915、1323、859）、LingSpam（2604、289、580）、AG's News（108000、12000、7600）。任务全部是分类（情感分析、有害内容检测、垃圾邮件检测、主题分类），没有客户端数量、参与率、轮次或非独立同分布（non-IID）划分这些联邦学习概念。
- 参数高效微调（parameter-efficient fine-tuning, PEFT）和 LoRA（low-rank adaptation）不是本文的研究对象。论文只在结论的未来工作里提到提示学习（prompt-based learning）和增量微调（delta tuning）会带来新的后门安全挑战（第 7 节）。

## 2. 威胁模型

- 攻击者是谁：论文不使用"恶意客户端/恶意服务器"的框架，攻击者是数据集或模型的发布方。Scenario I 的攻击者发布被投毒（poisoned）的训练数据集（表 1 引用 [17, 11, 44, 43]）；Scenario II 的攻击者发布通用预训练模型（引用 [72, 53]）；Scenario III 的攻击者发布已经在下游任务上微调好的模型（引用 [25, 64, 66, 70, 27, 45]）（第 2.1.2 节、表 1）。
- 占比或数量：论文用"投毒率"（poison rate）而不是"恶意客户端比例"度量攻击强度。Scenario I 的实验中投毒率取 {0, 0.01, 0.05, 0.1, 0.2}（第 5.2 节）；防御实验固定投毒率 0.1 并且使用 mix label（第 6.2 节）；表 15 给出每种攻击自己的投毒率，例如 POR 为 1、RIPPLES 为 0.5、LWS 与 TrojanLM 与 SOS 与 LWP 与 EP 为 0.1。论文没有客户端数量的概念。
- 能力（能改什么）：论文把访问能力分成三级（第 2.1.1 节、表 12）。模型盲（model-blind）攻击者只能投毒数据，任何在该数据上训练的模型都会被攻击；输出级（output-based）攻击者还能拿到前向传播中的模型输出，包括概率分数和隐藏表示；梯度级（gradient-based）攻击者进一步要求完全进入反向梯度更新过程。Scenario I 的攻击者只允许修改特定下游任务的训练数据集，不知道受害者模型和训练过程（第 2.1.2 节）。Scenario II 的攻击者可以控制受害者 PLM 和训练过程，但拿不到任务知识，只能使用无标注的纯文本（第 2.1.2 节）。Scenario III 是最不受限的设定，攻击者可以获得任务数据或目标数据、接触受害者模型并控制训练过程（第 2.1.2 节）。
- 知识（知道什么）：Scenario I 的攻击者拥有目标训练集或代理数据集，知道下游任务；Scenario II 的攻击者只有通用纯文本，不知道下游任务和目标标签，论文在附录 B.2 中指出这类攻击无法预先确定触发词对应的目标标签；Scenario III 的攻击者拥有任务数据或目标数据以及完整的训练控制权。
- 目标：定向后门（targeted backdoor）。模型在输入不含触发词时表现正常，在输入含预定义触发词（trigger）时输出攻击者指定的目标标签 y_T（第 2.1 节）。触发词形式包括固定词、句子、句法结构、文本风格、词组合，以及可学习生成器生成的更自然的词组合和句子（第 2.1 节）。论文不涉及越狱、安全对齐破坏或隐私窃取。
- 防御者是谁、能看到什么、信任什么：防御者是训练或部署模型的一方。Scenario I 中用户可以扫描和检查发布的数据集（第 3.2.1 节）；论文指出防御者通常有两类资源，即干净数据集和被投毒的模型（第 2.2 节），并明确说 [42, 16, 65] 需要干净数据集来确定阈值，而 [6, 16, 65] 会利用被投毒模型来识别投毒样本。防御者不信任外部发布的数据集或模型，信任自己手上的干净参考数据。

## 3. 攻击入口与流程位置

按题目给出的入口分类，本文的攻击入口有三个：本地数据准备（local data）、本地训练过程（local training）和模型发布（model distribution）。论文完全没有服务器聚合（server aggregation）和更新上传后处理（update postprocess）这两个环节，因为它是集中式训练。

- Scenario I（发布数据集）：入口在本地数据准备。步骤是选定触发词（词、句子、句法、风格或词组合），按投毒率和标签一致性（label consistency）选出要投毒的样本，插入触发词并把标签改为目标标签 y_T，然后发布数据集；受害者使用普通训练器（vanilla trainer），对训练计划一无所知（第 2.1.1 节、第 2.1.2 节）。标签一致性有三种：clean label 只投毒原始标签等于目标标签的样本，dirty label 只投毒原始标签不等于目标标签的样本，mix label 随机选样本投毒（第 5.2 节）。
- Scenario II（发布预训练模型）：入口在被发布 PLM 自己的训练过程。攻击者控制 PLM 和训练过程，用纯文本把后门种进权重。第 2.1.1 节把这类模型投毒（model poisoning）描述为攻击者自己训练受害者模型，或者修改训练过程（例如调整损失函数或优化策略）同时注入后门并训练模型，或者采用两个不相交的训练函数分别放置后门和训练受害者模型。附录 B.2 举例说这类攻击把投毒样本的 [CLS] token 映射到固定嵌入。受害者下载该 PLM 后在自己的数据上微调，后门随之被继承（第 2.1.2 节）。
- Scenario III（发布微调后的模型）：入口同样是本地训练过程，再加上模型发布这一交付渠道。攻击者获得任务数据或目标数据、接触受害者模型并控制训练过程（第 2.1.2 节）。附录 B.2 给出具体做法：LWP 在每一层的隐藏表示上增加投毒损失以增强攻击强度，LWS 使用同义词替换，TrojanLM 生成含触发词的句子，EP 和 SOS 只优化触发词嵌入而不修改模型参数。用户要么直接部署该模型，要么在自己的干净数据上再微调（第 3.2.1 节、表 2）。
- 论文未说明任何针对聚合、更新缩放或更新投影的攻击面。

## 4. 方法原理

本文有三块内容。

第一块是统一的评测框架。论文把已有攻击归入三个现实场景，表 1 给出每个场景"发布什么、能访问什么、代表工作"，并为每个场景规定评测协议（表 2）：Scenario I 需要控制投毒率和标签一致性；Scenario II 需要测试跨任务迁移性（transferability）和 clean-tuning；Scenario III 需要测试直接部署和 clean-tuning 两种情况（第 3.2 节）。评测维度从只看有效性扩展为三个：有效性用攻击成功率（attack success rate, ASR）和干净准确率（clean accuracy, CACC）；隐蔽性（stealthiness）用困惑度增量（∆PPL）和语法错误增量（∆GE）；语义保持性（validity）用通用句子编码器（universal sentence encoder, USE）计算干净样本与投毒样本的相似度（第 3.1 节）。论文还建议报告投毒率为 0 时干净模型上的 ASR，因为此时 ASR 仍有约 20%，说明部分投毒样本本身带有"对抗性"（第 5.2 节、附录 A）。

第二块是 OpenBackdoor 工具包的分层结构（第 4 节、附录 C、图 4）。Dataset 与 Victim 模块负责数据和 PLM；Trainer 模块实现训练过程，攻击者可以替换成自己的投毒训练器；Attacker 被拆成 Poisoner（把后门放进数据集）和 Trainer（在投毒数据上训练出带后门的模型）两部分；Defender 是插件，既可以插在攻击前（检测并过滤可能的投毒训练数据），也可以插在攻击后（在线检测投毒测试样本，阻止后门被触发）；Evaluation 模块统一计算 ASR、CACC、F1、误拒率（false rejection rate, FRR）和误受率（false acceptance rate, FAR）等指标。

第三块是 CUBE（ClUstering-based poisoned sample filtering for Backdoor-freE training），一个训练期防御基线（第 6.1 节）。动机来自可视化观察：在 BadNet 投毒的 SST-2 上训练 BERT-base 后，投毒样本的最后一层隐状态最终聚成一簇并与正常簇分离（图 3）。方法分三步。第一步是表示学习，直接用原始（可能已被投毒的）数据集训练一个模型，用这个模型把投毒样本和正常样本映射到嵌入空间。第二步是聚类，对全部样本的表示用 UMAP 降到 10 维，再用密度聚类算法 HDBSCAN 找出不同的簇。第三步是过滤，在"投毒样本少于正常样本"的前提下，对每个真实标签只保留最大的预测簇，丢弃其余所有样本，得到处理后数据集。论文强调 CUBE 在嵌入空间里识别投毒样本，因此不受触发词类型限制（第 6.1 节）。

## 5. 检测或防御所需的数据

CUBE 需要的输入：

- 完整训练集的文本与真实标签。这是 CUBE 过滤阶段"按真实标签保留最大簇"的依据。采集位置是客户端训练前（本方持有的原始数据集）；粒度是逐样本；不需要跨轮历史，不需要额外的干净参考数据集，不需要额外计算（第 6.1 节）。
- 每个训练样本的表示嵌入，来自"用原始数据集直接训练出的模型"的最后一层隐状态。采集位置是客户端训练后，因为必须先有一个在可能被投毒的数据上训练过的模型；粒度是逐样本；需要额外计算，包括一次额外的完整训练和一次覆盖全部样本的前向传播。论文未说明用作聚类表示的究竟是哪个 token 的隐状态（例如 [CLS]）或者是否做了池化，也未说明 CUBE 自身的训练超参数以及 UMAP 与 HDBSCAN 的参数（表 15 只列出攻击方法的超参数）。
- 聚类结果，即每个样本所属的簇编号和每个簇的大小。这是"每个标签保留最大簇、丢弃其余样本"的直接输入，粒度是逐样本；论文未说明某个标签存在多个合法大簇时的处理规则（第 6.1 节）。

论文在基线防御上需要的输入（用来说明这一类方法的数据需求）：

- BKI 需要训练集中的显著关键词，以及一个在给定投毒数据集上训练出的后门模型。第 6.2 节明确写道，因为 BKI 需要一个后门模型做检测，论文为它提供了在给定投毒数据上训练的模型。采集位置相当于客户端训练后，粒度是逐样本（关键词落在哪些样本上）。
- ONION 只需要文本本身，用语言模型（GPT-2）计算词级困惑度并删掉最可疑的词，论文把它适配到训练前处理全部样本。表 13 把它列为需要干净数据集、属于推理阶段的方法（第 2.2 节、第 6.2 节）。
- STRIP 与 RAP 需要被投毒的模型和干净数据集。STRIP 观察模型在扰动输入下的预测不确定性，RAP 观察模型对嵌入级"鲁棒性感知扰动"的反应；论文给二者都提供了在投毒数据上训练的后门模型，并把它们预测为投毒的样本从训练集里删除（第 2.2 节、表 13、第 6.2 节）。
- 评测统计量需要投毒样本相对原始干净样本的困惑度增量、语法错误增量和 USE 相似度，因此需要 GPT-2 一类语言模型做前向计算、语法检查工具、USE 编码器，以及成对的干净文本与投毒文本；粒度是逐样本，位置在评测阶段（第 3.1 节、表 4）。
- 评测还需要干净（未投毒）模型在投毒测试集上的 ASR 作为基线，以避免把语义漂移导致的预测翻转误算成后门效果（第 5.2 节第 (4) 点、附录 A）。

攻击留下的痕迹，以及论文声称能绕过的检测：

- 词级触发词会明显破坏句子流畅度。BadNet 在 SST-2 上的 ∆PPL 为 413.32（表 4），论文说插入无关 token 的做法"也让句子容易被发现"（第 5.2 节第 (3) 点）。ONION 与 BKI 正是依靠这类痕迹工作。
- 句法触发（SynBkd）和风格触发（StyleBkd）绕过了所有基于 token 的检测器。表 9 中 BKI 对 SynBkd 的 ASR 仍有 88.49，ONION 对 StyleBkd 的 ASR 仍有 83.37；论文在第 6.2 节总结说这些基线只能在一句话里找可疑 token，因此只能识别 token 级触发词，无法防御语义级触发。CUBE 能明显压低这两类攻击的 ASR。
- 组合式触发（LWP）是为绕过 token 级防御设计的，论文报告它确实有效，但会带来困惑度和语法错误的急剧上升（第 5.4 节第 (2) 点）。TrojanLM 生成的触发句困惑度和语法错误都不高，但生成句会改变整段文本的语义，USE 相似度很低，表 7 中为 7.10。
- 投毒样本在被投毒数据训练出的模型的最后一层隐状态空间里会聚簇并与正常样本分离，这是 CUBE 所利用的痕迹（图 3）。

## 6. 干预动作

- CUBE 的动作是从训练集中删除样本。对每个真实标签只保留最大簇，其余样本全部丢弃，然后用过滤后的数据集做无后门训练（第 6.1 节）。动作发生在训练之前，属于数据集层面的预处理。论文明确说训练期防御只适用于 Scenario I（第 2.2 节、表 13）。
- 被论文改造为训练期防御的基线也做样本级过滤。BKI、STRIP、RAP 先给出投毒预测，再把预测为投毒的样本从训练集删除；ONION 在训练前处理所有样本（第 6.2 节）。
- 推理期防御（ONION、STRIP、RAP 的原始形态）在测试时判断样本是否被投毒并拒绝。论文规定，如果投毒样本被检测出来，则攻击失败，因此 ASR 统计只计入通过检测且改变模型预测的投毒样本（第 6.3 节）。
- 论文没有使用剔除客户端、重新加权、梯度裁剪、加噪、模型修复或回滚这些动作，因为不存在客户端与聚合环节。论文也没有把"在干净数据上再微调"作为一种防御动作提出，只是在第 5.4 节把它当作评测场景和一种会削弱后门的现象来报告。

## 7. 实验设置与主要结果

设置：

- 攻击场景 I：SST-2、HSOL、AG's News 三个数据集，BERT-base 受害者模型，投毒率取 {0, 0.01, 0.05, 0.1, 0.2}，clean、mix、dirty 三种标签一致性，隐蔽性和有效性指标是 5 次随机运行的平均（第 5.2 节、表 4、图 2）。
- 攻击场景 II：直接测试 NeuBA 与 POR 公开发布的 BERT-base 模型在 SST-2、AG's News、HSOL、LingSpam 四个下游任务上的迁移表现，取 5 次运行平均，另有每句三个触发词的版本（第 5.3 节、表 5、表 6）。
- 攻击场景 III：BERT-base 微调模型，三种设定分别是直接测试最终模型（SST-2）、在 IMDB 上投毒后再用干净的 SST-2 微调、在 SST-2 上投毒后再用 IMDB 微调；表 8 另外给出 HSOL 与 OffensEval 的组合（第 5.4 节、表 7、表 8）。
- 防御实验：SST-2、HSOL、AG's News，BERT-base 受害者模型，投毒率固定 0.1 且使用 mix label，CUBE 换用 RoBERTa-base 做聚类；对照组是 BKI、ONION、STRIP、RAP，以及"不做防御"和"Oracle"（删除所有投毒样本并保留所有正常样本）两个端点（第 6.2 节、表 9）。表 9 中每个攻击方法对应 ASR 与 CACC 两列，本报告按表中数值顺序（先 ASR 后 CACC）引用，None 列只有 CACC。
- 推理期防御：同样三个数据集，报告 ASR、CACC 以及 FAR、FRR（第 6.3 节、表 10、表 11）。
- 数据集与超参数：表 3 给出数据统计，表 15 给出每种攻击的投毒率、预热轮数、训练轮数、批大小和学习率，例如 BadNet 系列的投毒率为 0.01、0.05、0.1、0.2，训练 5 个 epoch，批大小 32，学习率 2e-5；全部实验使用 Adam 优化器（附录 D.1）。论文没有客户端数、参与率或非独立同分布设置，因为它是集中式训练。

关键结果：

- 攻击有效性受投毒率与标签一致性强烈影响。投毒率足够大（不小于 0.1）时多数方法接近 100% ASR，clean label 攻击弱于 mix label 和 dirty label；投毒率为 0 时 ASR 仍在 20% 左右（第 5.2 节、图 2）。
- 场景 II 中后门的迁移性差。NeuBA 在 SST-2 上 ASR 为 73.40、CACC 为 90.90，POR 在 SST-2 上 ASR 为 68.95、CACC 为 90.42；但两者在 AG's News 上的 ASR 分别只有 2.05 和 1.26，在 LingSpam 上分别只有 0.98 和 0.24（表 5）。论文把原因归结为数据集规模和文本长度，即在大数据集上微调或在长文本上测试会大幅影响 ASR（第 5.3 节）。使用三个触发词时，POR 在 SST-2 上从 68.95 升到 90.73（表 6）。
- 场景 III 中干净微调会抹掉后门，同时存在有效性与语义保持性的权衡。RIPPLES 直接在 SST-2 上 ASR 为 100、CACC 为 91.10，经过 IMDB 到 SST-2 的干净微调后 ASR 降到 16.81、CACC 为 93.04；LWS 在 SST-2 上 ASR 为 100，在 SST-2 到 IMDB 的设定下 ASR 仍有 77.08，但 ∆PPL 高达 2066.20、USE 只有 50.00；TrojanLM 在 SST-2 到 IMDB 的设定下 ASR 为 92.72、CACC 为 93.48，USE 低到 7.10（表 7）。论文据此强调语义保持性指标可以防止高估攻击强度（第 5.4 节）。
- 防御方面：CUBE 在 SST-2 上把 BadNet 的 ASR 从 100.0 降到 15.90（CACC 为 90.17），把 AddSent 从 100.0 降到 24.01（CACC 为 90.28），把 SynBkd 从 86.08 降到 45.61（CACC 为 91.32），把 StyleBkd 从 77.30 降到 22.43（CACC 为 91.27）；对应的 Oracle 上界分别是 12.28、15.35、32.46、29.02（表 9）。在 AG's News 上，CUBE 把 BadNet 从 100.0 降到 0.72、把 AddSent 从 100.0 降到 0.58、把 SynBkd 从 98.05 降到 5.72（表 9）。论文的总结是 CUBE 的 ASR 降幅在全部对比方法中最好，并且是唯一能防住句法与风格触发的方法（第 6.2 节）。需要指出，按表 9 的行内顺序解读，CUBE 在 HSOL 上对 BadNet 一列的数值为 100.0，与未防御时的 99.84 基本相同，论文正文没有单独讨论这一格。
- 推理期防御整体不理想。ONION 只能防住 BadNet，在其余攻击上 ASR 仍然很高，表 10 中 SST-2 上对 AddSent 为 95.50；STRIP 几乎检测不出投毒样本，FAR 在 0.93 到 1.0 之间（表 11）；RAP 虽然能拒绝大部分投毒样本，但也会过滤掉大量干净样本，损害模型效用（第 6.3 节、表 10、表 11）。

## 8. 开销

论文未报告计算、通信或存储开销。作者在 NeurIPS 检查清单第 3(d) 项勾选"No"，即没有给出总计算量和所用资源类型（第 17 页检查清单）。可以间接参考的只有表 15 的训练超参数（轮数、批大小、学习率）和表 3 的数据规模。CUBE 需要额外训练一个模型、做一次全量前向传播来取表示，再做 UMAP 降维与 HDBSCAN 聚类，但论文没有给出这些步骤的时间或内存开销。通信开销在集中式设定下不适用，论文也未讨论。

## 9. 假设、局限与自适应攻击

论文自述的局限（附录 E）：第一，现有研究仍然是在实验室里用模型、数据集和角色模拟现实场景，没有真实部署和工业界关切，需要纳入更多实际因素；第二，评测框架本身有缺陷，困惑度和语法错误是常用但不完整的语言指标，语义保持性更难度量，USE 不够用。

CUBE 依赖的假设（第 6.1 节）：

- 投毒样本数量少于正常样本，否则"每个标签保留最大簇"的规则不成立。
- 在被投毒数据训练出的模型的最后一层隐状态空间里，投毒样本会聚成可分离的簇。
- 防御者能拿到全部训练样本的真实标签，并逐标签地保留最大簇。
- 防御者可以先用原始（可能被投毒的）数据集额外训练一个模型用于表示学习。
- 论文未说明当某个标签存在多个合法大簇时"只保留最大簇"如何处理，也没有给出聚类数量、阈值或其他超参数。

其他假设与未覆盖项：

- 评测协议假设投毒率和标签一致性可控并已知（表 2、第 3.2.1 节）。
- 基线防御假设可用干净数据集设定阈值，或者假设有一个在投毒数据上训练好的后门模型可用（第 2.2 节、表 13、第 6.2 节）。
- 攻击侧假设：Scenario I 的攻击者不知道受害者模型和训练过程；Scenario II 的攻击者拿不到任务标签；Scenario III 的攻击者拥有最强权限（第 2.1.2 节）。
- 全部实验都是单一数据持有者的集中式文本分类，受害者模型是 BERT-base 或 RoBERTa-base，训练数据规模从 2604 条到 108000 条（表 3）。
- 论文没有评估自适应攻击者。第 6 章的防御实验中攻击方法是固定的，没有攻击者针对 CUBE 的聚类过滤规则调整投毒方式。论文只在第 5.4 节提到 LWP 是为绕过 token 级防御而设计的组合触发词，这属于对既有检测器的规避，而不是针对 CUBE 的自适应攻击。

迁移到联邦 LoRA 微调时可能失效的假设：

- 分析：论文完全没有联邦流程，没有客户端、聚合服务器、轮次或参与率的概念，CUBE 直接作用于单一数据持有者手中的完整数据集和全量标签。在联邦 LoRA 中服务器看不到原始样本，CUBE 的"在客户端训练后抽取逐样本隐状态并聚类"只能在客户端本地完成；若要在服务器做跨客户端的簇划分，就必须上传样本级表示，这会引入论文未讨论的隐私与通信成本。
- 分析：CUBE 的"投毒样本少于正常样本"和"每个真实标签保留最大簇"两条规则，在非独立同分布的数据切分下很容易失效。单个客户端可能只有一两个类别、某个标签的样本极少，"最大簇等于正常簇"不再有保证；当恶意客户端比例较高时，投毒样本也可能成为某个标签下的最大簇。
- 分析：论文的探针模型是对基座模型做全参数微调，换成 LoRA 后表示空间由低秩增量与冻结基座共同决定，投毒样本在最后一层隐状态中是否仍然形成可分离簇，论文没有任何实验支持，属于未验证假设。另外，"最后一层隐状态"在生成式大模型里也不再对应一个分类用的句向量，论文没有说明池化方式。
- 分析：论文的有效性与隐蔽性指标（ASR、CACC、∆PPL、∆GE、USE）都定义在短文本分类任务上。联邦 LoRA 常见的指令微调和生成任务没有单一"目标标签"；论文自己也承认困惑度与语法错误不完整、语义保持性难以度量（附录 E），并把数据集规模与文本长度对 ASR 的影响列为被忽视的问题（第 5.3 节）。
- 分析：论文的场景 II 和场景 III 讨论的是发布被投毒的预训练模型和微调模型，与"适配器或模型发布者"这一供应链威胁最接近，但论文没有研究适配器或 LoRA 增量，只在结论里把增量微调列为未来工作，因此它对联邦 LoRA 供应链的直接适用性没有实验依据。
- 分析：论文的防御不改变模型参数，只过滤数据，因此没有回滚、裁剪或加噪等可用于聚合环节的接口；它也无法处理"聚合后的全局模型已经被投毒"的情形。

## 10. 对防护库设计的含义

- 分析：这篇论文的方法需要两个固定的客户端钩子。一个是客户端训练前的原始数据视图，要求逐样本的文本与真实标签，并允许插件返回过滤掩码或过滤后的数据集（CUBE、BKI、STRIP、RAP 的样本级删除，以及 ONION 的逐样本处理都挂在这里）；另一个是客户端训练后的表示导出钩子，要求能用"在未过滤的本地数据上训练出的探针模型"对全部本地样本做一次前向传播并导出最后一层隐状态。这两个钩子与具体攻击无关，属于采集底座应当提供的通用能力。
- 分析：库需要支持"探针训练"这一独立于生产训练的额外训练任务。CUBE 的第一步、BKI 的关键词识别、STRIP 与 RAP 的检测都需要一个在可能被投毒的数据上得到的后门模型，第 6.2 节明确为这些基线提供了在给定投毒数据上训练的模型。把探针训练做成可复用的钩子，比让每个插件各自训练更省事，也便于记录探针与生产模型的版本对应关系。
- 分析：库需要一份干净参考数据视图和一个逐样本特征缓存。ONION、STRIP、RAP 依赖干净数据确定阈值（第 2.2 节、表 13），评测指标需要成对的干净文本与投毒文本、基于本地语言模型的困惑度、语法错误计数和句向量相似度（第 3.1 节）。在联邦设置下这些特征必须在客户端本地计算，服务器只应接收判定结果或聚合统计，否则会与论文的集中式前提冲突。
- 分析：干预接口只需要支持"数据集层过滤"，不需要为这篇论文实现客户端剔除、重新加权、裁剪、加噪或模型回滚。CUBE 的动作是把样本从训练集中删掉后重新训练（第 6.1 节），对应插件应返回过滤后的数据集与保留掩码，并允许触发一次干净重训。
- 分析：评测视图要能记录投毒率与标签一致性这两个数据集级超参数（表 2、第 3.2.1 节），并能跑投毒率扫描；同时要保存一份干净模型在投毒测试集上的 ASR 基线，否则无法区分后门效果与语义漂移（第 5.2 节第 (4) 点、附录 A）。
- 分析：CUBE 的具体算法（用 UMAP 降到 10 维、用 HDBSCAN 聚类、每个真实标签只保留最大簇）属于这篇论文特有的插件逻辑，不应写进采集底座。底座的通用部分只是逐样本文本与标签、逐样本表示、聚类与过滤所需的元数据这些数据视图，以及一个可在客户端训练前执行的过滤钩子。要对联邦 LoRA 生效，还需要论文未提供的服务器侧变体（例如在适配器更新或聚合统计上做聚类），这一点必须作为库的设计缺口明确记录。

## 11. 原文依据

1. 章节：Abstract。支撑：第 1 节与第 2 节关于论文把攻击分为三个发布场景的论断。原文："we categorize existing works into three practical scenarios in which attackers release datasets, pre-trained models, and ﬁne-tuned models respectively, then discuss their unique evaluation methodologies."
2. 章节：第 2.1.1 节 Data。支撑：第 2 节关于攻击者数据知识分级的论断。原文："The strongest assumption is that attackers can get access to the target training dataset [17, 11, 44, 43]. This is practical when users manage to use publicly-released third-party datasets to train their own models."
3. 章节：第 2.1.2 节 Scenario I。支撑：第 2 节与第 3 节关于 Scenario I 攻击者能力边界的论断。原文："In this scenario, attackers are only allowed to modify training datasets for specific downstream tasks, while not knowing the victim model and training process."
4. 章节：第 2.1.1 节 Training process。支撑：第 3 节关于模型投毒进入本地训练过程的论断。原文："For model poisoning attacks, attackers can train the victim models by themselves. They either modify the training process (e.g. adjust loss functions or optimization strategies) to inject backdoor and train models simultaneously"
5. 章节：第 2.2 节 Stages。支撑：第 6 节与第 9 节关于训练期防御只适用于 Scenario I 的论断。原文："Training-time defense aims to train clean models with poisoned datasets, such as filtering out poisoned samples [6]. Such kind of defense methods only suits Scenario I."
6. 章节：第 2.2 节 Accessibility。支撑：第 5 节关于部分防御需要干净参考数据来设定阈值的论断。原文："Some works [42, 16, 65] require a clean dataset to determine the thresholds for detecting suspicious samples or tokens."
7. 章节：第 6.1 节 Method 第一步。支撑：第 4 节与第 5 节关于 CUBE 需要先在原始数据上训练探针模型并抽取样本表示的论断。原文："(1) Representation learning. In the first step, we train a model with the original dataset directly and use this potentially backdoor-injected model to map poisoned and normal samples to the embedding space."
8. 章节：第 6.1 节 Method 第二步。支撑：第 4 节关于 UMAP 降维与 HDBSCAN 聚类的论断。原文："we use UMAP [49] to reduce the dimension of the data representation to 10-D, which brings benefits to clustering [38, 61], and then employ an advanced density clustering algorithm HDBSCAN [39] to identify distinctive clusters."
9. 章节：第 6.1 节 Method 第三步。支撑：第 4 节、第 6 节与第 9 节关于过滤规则及其"投毒样本更少"前提的论断。原文："After clustering, with the presumption that poisoned samples are fewer than normal samples, we keep only the largest predicted clusters for each ground-truth label and drop all other samples."
10. 章节：附录 E Limitations。支撑：第 9 节关于论文自述局限的论断。原文："First, current researches still simulate practical scenarios with models, datasets, and characters in lab, without real deployment and industrial concerns. To reach the goal of revealing real-world security threats, more practical factors should be considered."

```json
{
  "key": "cui2022openbackdoor",
  "title": "A Unified Evaluation of Textual Backdoor Learning: Frameworks and Benchmarks",
  "year": 2022,
  "paper_type": "benchmark",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider", "external"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data", "local_training", "model_distribution"],
  "observables": [
    {"what": "全部训练样本的文本与真实标签（CUBE 按标签过滤与 BKI 关键词扫描的输入）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每个训练样本在用原始投毒数据集训练出的模型最后一层隐状态上的表示嵌入（CUBE 聚类输入）", "where": "client_post_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "聚类结果，即每个样本所属簇编号与各簇大小，用于每个标签保留最大簇", "where": "client_post_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "在给定投毒数据上训练出的后门模型中的显著关键词（BKI 的检测依据）", "where": "client_post_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "投毒测试或训练样本的文本及基于 GPT-2 的逐词困惑度（ONION 的检测依据）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "被投毒模型在扰动输入或嵌入级扰动下的预测置信度与不确定性（STRIP 与 RAP 的检测依据）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "投毒样本相对原始干净样本的困惑度增量、语法错误增量与 USE 语义相似度（评测指标）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "干净未投毒模型在投毒测试集上的 ASR 与干净测试集上的 CACC（有效性基线）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["client"],
  "assumptions": [
    "投毒样本数量少于正常样本，否则每个标签保留最大簇的规则不成立（第 6.1 节）",
    "投毒样本在被投毒数据训练出的模型最后一层隐状态空间中聚成可分离的簇（图 3、第 6.1 节）",
    "防御者能获得全部训练样本的真实标签，并可先用原始数据额外训练一个探针模型（第 6.1 节）",
    "评测假设投毒率与标签一致性可控且已知，基线防御假设有干净数据或已训练好的后门模型可用（第 2.2 节、第 3.2.1 节、表 13）",
    "任务为集中式短文本分类，模型为 BERT-base 或 RoBERTa-base，不存在客户端、聚合、轮次与非独立同分布划分（表 3、第 5 节、第 6.2 节）",
    "攻击方法在防御评测中是固定的，未针对 CUBE 的聚类过滤做自适应规避（第 6.2 节）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节与第 2 节关于三个发布场景分类的论断", "text": "we categorize existing works into three practical scenarios in which attackers release datasets, pre-trained models, and ﬁne-tuned models respectively, then discuss their unique evaluation methodologies."},
    {"section": "2.1.1 Data", "supports": "第 2 节关于攻击者数据知识分级的论断", "text": "The strongest assumption is that attackers can get access to the target training dataset [17, 11, 44, 43]. This is practical when users manage to use publicly-released third-party datasets to train their own models."},
    {"section": "2.1.2 Scenario I", "supports": "第 2 节与第 3 节关于 Scenario I 攻击者能力边界的论断", "text": "In this scenario, attackers are only allowed to modify training datasets for specific downstream tasks, while not knowing the victim model and training process."},
    {"section": "2.1.1 Training process", "supports": "第 3 节关于模型投毒进入本地训练过程的论断", "text": "For model poisoning attacks, attackers can train the victim models by themselves. They either modify the training process (e.g. adjust loss functions or optimization strategies) to inject backdoor and train models simultaneously"},
    {"section": "2.2 Stages", "supports": "第 6 节与第 9 节关于训练期防御只适用于 Scenario I 的论断", "text": "Training-time defense aims to train clean models with poisoned datasets, such as filtering out poisoned samples [6]. Such kind of defense methods only suits Scenario I."},
    {"section": "2.2 Accessibility", "supports": "第 5 节关于部分防御需要干净参考数据设定阈值的论断", "text": "Some works [42, 16, 65] require a clean dataset to determine the thresholds for detecting suspicious samples or tokens."},
    {"section": "6.1 Method step 1", "supports": "第 4 节与第 5 节关于 CUBE 需要探针模型与样本表示的论断", "text": "(1) Representation learning. In the first step, we train a model with the original dataset directly and use this potentially backdoor-injected model to map poisoned and normal samples to the embedding space."},
    {"section": "6.1 Method step 2", "supports": "第 4 节关于 UMAP 降维与 HDBSCAN 聚类的论断", "text": "we use UMAP [49] to reduce the dimension of the data representation to 10-D, which brings benefits to clustering [38, 61], and then employ an advanced density clustering algorithm HDBSCAN [39] to identify distinctive clusters."},
    {"section": "6.1 Method step 3", "supports": "第 4 节、第 6 节与第 9 节关于过滤规则及投毒样本更少前提的论断", "text": "After clustering, with the presumption that poisoned samples are fewer than normal samples, we keep only the largest predicted clusters for each ground-truth label and drop all other samples."},
    {"section": "Appendix E Limitations", "supports": "第 9 节关于论文自述局限的论断", "text": "First, current researches still simulate practical scenarios with models, datasets, and characters in lab, without real deployment and industrial concerns. To reach the goal of revealing real-world security threats, more practical factors should be considered."}
  ]
}
```
