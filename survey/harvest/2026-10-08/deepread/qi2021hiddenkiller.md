# qi2021hiddenkiller：Hidden Killer: Invisible Textual Backdoor Attacks with Syntactic Trigger

## 1. 基本信息

- **场景**：集中式训练（centralized training），**不是联邦学习**，也不是现代意义上的大语言模型微调。论文在"预训练加微调"（pre-train and fine-tune）范式下，对文本分类模型做全参数微调（§3.1）；论文没有出现任何客户端、聚合、通信轮次的设定。
- **训练阶段**：攻击发生在训练数据准备阶段（生成投毒样本），后门在微调训练阶段被注入；在论文定义的第二种设定"clean fine-tuning"中，受害模型还会被干净数据再微调一次；触发在推理阶段生效（§3.1、§3.3、§5.2）。
- **论文类型**：攻击（attack）。论文在 §5.2 评估了已有防御（ONION），并自行设计了两种输入侧改写防御做压力测试，但没有提出可部署的防御方案。
- **模型与数据规模**：受害模型为双向长短期记忆网络（bidirectional LSTM, BiLSTM，两层、隐藏层大小 1,024、300 维词嵌入）与 BERT（bert-base-uncased，12 层、768 维隐藏状态），并区分立即测试（BERT-IT）与干净再微调（BERT-CFT）两种设定（§4.1）。数据集为 SST-2（训练 6,920 / 验证 872 / 测试 1,821，平均句长 19.3 词）、OLID（11,916 / 1,324 / 859，平均 25.2 词）、AG's News（108,000 / 11,999 / 7,600，平均 37.8 词），见表 1。触发句法模板为 S(SBAR)(,)(NP)(VP)(.)，投毒率（poisoning rate）分别为 20%（BiLSTM）、20%（BERT-IT）、30%（BERT-CFT）（§4.1）。目标标签分别为 Positive、Not Offensive、World（§4.1）。论文首页标注 arXiv:2105.12400v2 [cs.CL]，日期为 2021 年 6 月 3 日；抽取文本中未显示会议或期刊信息。代码与数据在 https://github.com/thunlp/HiddenKiller（摘要）。

## 2. 威胁模型

**攻击者是谁。** 论文给出两种常见场景（§5.2）：第一种是"攻击者只能污染训练数据、不能操纵训练过程"，例子是受害者使用被投毒的第三方数据集亲自训练模型；第二种是"攻击者既能控制训练数据也能控制训练过程"，例子是受害者使用一个已被注入后门的第三方模型。按本报告任务书的角色枚举，这对应数据提供方（data provider）与外部第三方模型提供方（external），论文没有使用"恶意客户端"这一说法。

**占比或数量。** 论文未说明任何客户端数量、参与率或恶意客户端比例，因为研究的是集中式训练。论文只给出投毒率：BiLSTM 20%、BERT-IT 20%、BERT-CFT 30%（§4.1），并说明该比例是在验证集上调节的，目标是让攻击成功率尽量高、同时干净准确率下降小于 2%（§4.1）。投毒样本的绝对条数论文未直接给出。

**能力（能改什么）。** 攻击者能修改正常训练样本（用受控句法改写模型把它们改写成符合指定句法模板的句子）、给投毒样本打上任意目标标签、并把它们混入训练集（§3.1、§3.3）。在第一场景里攻击者不能动训练过程；在第二场景里攻击者还能控制训练过程（§5.2）。推理阶段攻击者还能对测试样本做同样改写以激活后门（§1）。

**知识（知道什么）。** 攻击者需要访问正常训练集以统计句法模板频率：论文用 Stanford parser 对每个正常训练样本做成分句法分析（constituency parsing），统计模板频率后选出触发模板（§3.3）。攻击者还需要一个受控句法改写模型（论文用 SCPN）、一个 GPT-2 语言模型和 LanguageTool 用于过滤低质量改写（§3.2、§3.3、§5.1）。目标标签的选择"几乎不影响攻击结果"，该论断转引自 Dai et al. (2019)（§4.1 脚注 1）。

**目标。** 定向后门（targeted backdoor）：模型在正常输入上表现如常，在带触发器的输入上输出攻击者指定的目标标签（§3.1）。论文未研究无目标破坏、隐私泄露或安全对齐破坏。

**防御者是谁、能看到什么、信任什么。** 第一种场景下防御者就是数据使用者，可以检查全部训练数据、发现并移除可疑样本（§5.2 引用 Li et al. 2020）；通用场景下防御者可以在测试样本上做过滤或改写，以阻止触发器激活后门（§5.2）。论文评估的防御是 ONION（基于语言模型的测试样本离群词删除，§5.2），提到但未评估的是 BKI（基于训练数据检查、主要面向 LSTM，§5.2）。论文伦理章节主张由可信第三方发布带签名的真实数据集与模型（Ethical Considerations）。论文未说明防御者能否看到逐客户端更新，因为不存在联邦流程。

## 3. 攻击入口与流程位置

攻击入口是**本地数据准备**（训练数据投毒），不涉及更新上传前的后处理、服务器聚合或全局模型下发——这些环节在本论文的集中式设定里不存在。具体步骤（§3.3）：

1. **选择触发句法模板。** 用 Stanford parser 对每个正常训练样本做成分句法分析，统计句法模板频率；在 SCPN 训练集中最高频的二十个模板里，选在目标任务训练集上频率最低的那个作为触发器（§3.3）。实验中该模板为 S(SBAR)(,)(NP)(VP)(.)，在训练集上的频率为 0.01%（表 3）。这个模板的作用是给句子加一个由从属连词引导的从句（§4.1）。
2. **生成投毒样本。** 随机抽取一小部分正常样本，用 SCPN 把它们改写成符合触发模板的复述句；用两条规则过滤：沿用 Iyyer et al. (2018) 的 n-gram 重叠规则去掉有重复词的低质量复述，以及用 GPT-2 语言模型去掉困惑度（perplexity）过高的复述（§3.3）。
3. **后门训练。** 给保留下来的复述句贴上目标标签，与其余正常训练样本一起训练受害模型（§3.3）。实现细节为 Adam 优化器、初始学习率 2e-5 线性衰减、训练 3 个 epoch（§4.1）。
4. **推理期触发。** 构造投毒测试集时只改写那些真实标签不是目标标签的测试样本，改写方式与训练时相同（§3.1、§4.1）。论文没有把这一步算作训练流程的入口，但它是攻击生效不可缺少的一环。

另外，作为对比方法出现在论文中的 RIPPLES（Kurita et al., 2020）会改写后门训练的损失函数并使用名为"Embedding Surgery"的触发词嵌入初始化（§4.1）；这属于本地训练过程入口，但**不是本论文提出的方法**，本论文只是把它当作基线。

## 4. 方法原理

**核心思想。** 已有文本后门攻击几乎都把额外内容插入正常样本（固定词、固定句子或字符翻转），这会破坏语法与流畅度，因而容易被样本过滤类防御发现（§1、§2.1）。论文改用句法结构作为触发器：句法结构是更抽象、更潜在的特征，用它生成的投毒样本是原句的复述，读起来自然流畅，因而更隐蔽（§1）。

**形式化（§3.1）。** 正常训练集为 D = {(xi, yi)}，共 N 条。投毒攻击生成一批投毒样本 D\* = {(x\*j, y\*)}，其中 x\*j 是正常输入 xj 被嵌入触发器后的版本，y\* 是攻击者指定的目标标签，I\* 是被修改样本的下标集合。投毒训练集 D′ 由"删掉被修改的那些正常样本、再加入投毒样本"构成，用它训练出的后门模型在遇到带触发器的输入时应输出 y\*。论文说明这套形式化可以平移到其他自然语言处理模型（§3.1）。

**受控句法改写（§3.2）。** 论文采用 SCPN（Syntactically Controlled Paraphrase Network，Iyyer et al., 2018）：编码器是双向 LSTM，解码器是带注意力（attention）与复制机制（copy mechanism）的两层 LSTM，解码器输入还拼接了由另一个 LSTM 句法编码器得到的目标句法结构表示。目标句法结构可以是完整线性化句法树，也可以是只取线性化句法树顶上两层的句法模板；论文指出用句法模板能保证改写结果更好地符合目标结构。SCPN 在它自己的训练集上选二十个最高频句法模板作为可控目标，并会过滤掉有词重叠或与原句复述相似度过高的不完美复述（§3.2）。

**为什么选最低频模板。** 论文希望投毒样本与正常样本在触发器这一特征维度上清晰可分，所以选训练集中频率最低的模板（§3.3）。表 3 的消融支持这个策略：模板频率从 32.16% 降到 0.01% 时，验证集攻击成功率从 88.90 升到 96.94、干净准确率从 86.64 升到 90.35（表 3）。

**为什么更隐蔽。** 投毒样本是原句的复述，没有新增内容，因此不存在可被离群词检测捕获的插入模式（§2.1、§5.2）。表 7 给出了正常样本与对应投毒样本的成对例子。

**论文的附带观察。** 论文设计了一个探针实验来验证"模型越会学句法、越容易中招"：用 SCPN 把 SST-2 一半样本改写成投毒数据，冻结受害模型、在其表示上训练一个二分类器判断样本是否被投毒，测试集准确率为 BiLSTM 78.4%、BERT-IT 96.58%、BERT-CFT 93.23%，与三者的攻击成功率成正比（§4.2）。

## 5. 检测或防御所需的数据

本论文是攻击论文，因此下面逐项列出的是：论文所评估的各类检测或防御需要什么输入，以及攻击会在哪些可观测量上留下痕迹。

- **正常/待检训练样本原文。** 是什么：每条训练样本的文本与标签。在哪里采集：客户端训练前，即数据准备或数据审查阶段（论文中相当于数据使用者检查第三方数据集，§5.2）。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：需要——判断样本是否异常要对照正常样本的统计，论文用整个原始训练集的模板频率作参照（§3.3）。是否需要额外计算：否。是否需要其他客户端的数据：论文的攻击者需要全训练集统计（§3.3），防御方若要在集计层面判断也同样需要全局分布。
- **逐样本句法模板及其频率分布。** 是什么：对样本做成分句法分析后取线性化句法树顶上两层得到的模板，以及模板在集合上的出现频次。在哪里采集：客户端训练前。粒度：逐样本，并聚合到数据集级或客户端级直方图。是否需要跨轮历史：否。是否需要干净参考数据：需要，异常判据是"某模板在正常训练集里频率极低"，论文中触发模板频率为 0.01%，而被选模板集合里的最高频模板为 32.16%（表 3）。是否需要额外计算：需要，要用 Stanford parser 做句法分析（§3.3）。
- **逐样本语言模型困惑度与语法错误数。** 是什么：GPT-2 计算出的困惑度和 LanguageTool 给出的语法错误个数。在哪里采集：客户端训练前（论文用于自动质量评估，§5.1）。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：论文给出了正常样本的平均值作为参照，正常样本平均困惑度 224.36、平均语法错误数 3.51（§5.1）。是否需要额外计算：需要一次语言模型前向与一次语法检查。
- **测试或推理样本原文。** 是什么：进入模型前的输入文本。在哪里采集：评估与部署阶段（推理前）。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：需要——ONION 要用语言模型逐词删除并比较困惑度变化（§5.2）；回译改写要用机器翻译服务（§5.2）；句法结构改写防御要用 SCPN 把样本改写成 S(NP)(VP)(.)（§5.2）。
- **受害模型在冻结状态下的隐藏表示。** 是什么：模型对样本的内部表示，接一个外部分类器判断样本是否为投毒样本。在哪里采集：模型训练完成后的分析阶段（§4.2）。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：否，但需要已训练好的受害模型。是否需要额外计算：需要训练一个外部探针分类器，且受害模型被冻结（§4.2）。需要说明：论文做这个探针实验是为了验证"句法学习能力与攻击成功率成正比"，**不是**把它当作检测方法。
- **人工判别结果。** 是什么：标注者判断每条样本是"人写的"还是"机器改写的"。在哪里采集：客户端训练前（论文的数据检查实验，§5.1）。粒度：逐样本，每样本由三名标注者投票。是否需要干净参考数据：否。是否需要额外计算：否，但需要人工成本。论文设置是 40 条投毒样本混入 160 条正常 SST-2 样本（§5.1）。

**攻击留下什么痕迹、声称绕过什么检测。** 论文的立场是句法触发器的痕迹非常弱：人工判别下投毒样本的 F1 低到 9.90（表 4），GPT-2 困惑度 186.72、语法错误数 3.94，比两种插入式触发器更接近正常样本（表 4）。论文声称它能绕过基于插入内容检测的样本过滤（§2.1 引用 Chen and Dai 2020、Qi et al. 2020），能基本无视基于离群词删除的 ONION——Syntactic 的攻击成功率平均下降小于 1.2%（§5.2、表 5），也能扛住回译改写（SST-2 上 BERT-IT 攻击成功率 91.64、BERT-CFT 83.71，表 6）。但论文自己设计的、专门针对它的句法结构改写防御能够显著压制它：SST-2 上攻击成功率降到 BiLSTM 69.12、BERT-IT 61.97、BERT-CFT 56.59（表 6），代价是干净准确率分别下降 6.16、11.65、10.30 个点（表 6），论文在脚注 4 中认为这个代价使两种句级防御不实用。

## 6. 干预动作

论文本身是攻击论文，其提出的方法没有干预动作；下面列出的是论文评估或设计的防御在检测之后做什么。

- **训练前数据检查与样本移除。** 在第一种场景中，受害者可以检查全部训练数据、检测并移除可能的投毒样本，从而阻止后门被注入（§5.2 引用 Li et al., 2020）。论文提到 BKI 属于这类基于训练数据检查的防御，但明确说自己没有评估它，只评估了 ONION（§5.2）。形式上这相当于在数据准备阶段过滤样本。
- **测试时删除可疑词。** ONION 用一个语言模型找测试样本中的离群词：如果删掉某个词能显著降低困惑度，就认为该词与触发器有关并在送入模型前删除它（§5.2）。动作发生在推理之前。
- **测试时改写输入（回译）。** 论文设计的防御之一是把测试样本先翻译成中文、再翻译回英文，期望改写能破坏触发器（§5.2）。动作发生在推理之前。
- **测试时改写输入（句法结构改写）。** 论文专门为对抗 Syntactic 设计的防御：对每条测试样本用 SCPN 改写成使用非常常见句法结构 S(NP)(VP)(.) 的句子，从而"消除"句法触发器（§5.2）。动作发生在推理之前。
- **治理层面的建议。** 论文伦理章节建议由可信第三方发布带签名的真实数据集与模型，作为一种根本性的应对（Ethical Considerations）；这是制度性建议，不是技术动作。

按本报告任务书的分类，这些动作位于数据准备侧与部署推理侧；在联邦术语里，前者可映射到客户端侧、后者可映射到服务端或部署侧，因此第 12 节 JSON 中记为 "both"。

## 7. 实验设置与主要结果

**设置。** 三个数据集与规模见表 1；受害模型为 BiLSTM、BERT-IT、BERT-CFT（§4.1）。基线为 BadNet（随机插入稀有词）、RIPPLES（插入稀有词并改写损失、使用 Embedding Surgery）、InsertSent（插入固定句子）（§4.1）。指标为干净准确率（clean accuracy, CACC，后门模型在原始干净测试集上的分类准确率）与攻击成功率（attack success rate, ASR，在投毒测试集上的分类准确率，投毒测试集由真实标签不是目标标签的测试样本改写而来）（§4.1）。投毒率在验证集上调节，最终为 20%、20%、30%（§4.1）。论文未涉及客户端数、参与率、通信轮次或数据非独立同分布（non-IID）问题。

**主要结果。**

- 无防御时，Syntactic 与三个基线总体可比（表 2）。例如 SST-2 上 Syntactic 的 ASR / CACC 为 BiLSTM 93.08 / 76.66、BERT-IT 98.18 / 90.93、BERT-CFT 91.53 / 91.60；OLID 上为 98.38 / 77.99、99.19 / 82.54、99.03 / 81.26；AG's News 上为 98.49 / 89.28、99.92 / 94.09、99.52 / 94.32。对应良性模型（Benign）的准确率为 SST-2 的 78.97 / 92.20 / 92.20，OLID 的 77.65 / 82.88 / 82.88，AG's News 的 90.22 / 94.45 / 94.45（表 2）。论文总结所有攻击方法的攻击成功率接近 100%（§4.2），摘要称 Syntactic 在 AG's News 上优于所有基线、在 SST-2 上最差。
- 触发模板频率的影响（表 3，SST-2 验证集、针对 BERT）：频率从 32.16% 降到 0.01% 时，ASR 从 88.90 单调升到 96.94，CACC 从 86.64 升到 90.35（表 3、§4.3）。
- 投毒率的影响（图 2，SST-2 验证集）：攻击成功率随投毒率上升先升后波动甚至下降，干净准确率基本随投毒率上升而下降（§4.4）。
- 隐蔽性（表 4、§5.1）：人工检查中，词插入触发器的投毒 F1 为 72.50、句插入为 86.77、句法触发器为 9.90；正常 F1 分别为 93.12、96.31、89.27；困惑度分别为 302.28、249.19、186.72；语法错误数分别为 5.26、3.99、3.94；正常样本平均困惑度 224.36、平均语法错误数 3.51（表 4、§5.1）。
- 对 ONION 的抵抗力（表 5）：Syntactic 的 ASR 下降很小，SST-2 上 BiLSTM 92.19（下降 0.89）、BERT-IT 98.02（下降 0.16）、BERT-CFT 91.30（下降 0.23）；同一数据集上 BadNet 降到 47.80 / 40.30 / 62.74、InsertSent 降到 86.48 / 81.31 / 84.28（表 5）。论文称 Syntactic 的平均下降小于 1.2%（§5.2）。
- 对句级防御的抵抗力（表 6，SST-2）：回译改写下 Syntactic 的 ASR 为 87.24（BiLSTM）、91.64（BERT-IT）、83.71（BERT-CFT），而 BadNet 为 49.17 / 49.94 / 51.04、InsertSent 为 54.22 / 53.79 / 48.99；句法结构改写下 Syntactic 的 ASR 为 69.12 / 61.97 / 56.59，CACC 为 70.50 / 79.28 / 81.30（表 6）。论文指出两种句级防御都明显损害干净准确率，因而实际上不实用（脚注 4）。
- 探针实验（§4.2）：投毒/正常二分类的测试准确率为 BiLSTM 78.4%、BERT-IT 96.58%、BERT-CFT 93.23%，与攻击成功率成正比。

## 8. 开销

论文未报告攻击或防御的计算、通信与存储开销，没有给出时间、显存、参数量或数据量的量化对比。论文只定性说明了攻击流程要用到的外部组件：SCPN 句法改写模型、Stanford parser、GPT-2 语言模型与 LanguageTool（§3.2、§3.3、§5.1）；防御侧 ONION 需要语言模型推理、回译防御需要 Google Translation、句法结构改写防御需要 SCPN（§5.2）。伦理章节只声明"运行实验所消耗的能量有限"（Ethical Considerations）。按本报告任务书的字段，开销记为"论文未报告"。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文有依据的部分）。**

- 攻击者能获得一个受控句法改写模型，且其生成的复述具有良好语法性与模板一致性（§3.2）；论文选择 SCPN，但声明任何其他受控句法改写模型也可用（§3.2）。
- 触发模板必须在正常训练集里足够稀有，才能让投毒样本与正常样本在触发器特征维度上分开（§3.3、§4.3）；论文的策略是在 SCPN 的二十个高频模板中取目标任务训练集频率最低者（§3.3）。
- 攻击者能在推理时对测试样本做同样的改写以激活后门（§1、§4.1）。
- 目标标签的选择几乎不影响攻击效果，该结论来自 Dai et al. (2019)（§4.1 脚注 1）。
- 投毒率与干净准确率之间存在权衡，论文通过调投毒率把干净准确率下降控制在 2% 以内（§4.1、§4.4）。
- 在"clean fine-tuning"设定下，后门要在一次干净再微调之后仍然保留（§3.1、§4.2）。

**论文自述的局限。**

- 数据集规模可能影响效果：作者推测 Syntactic 需要更多后门训练数据，因为它利用的是抽象的句法特征（§4.2）；Syntactic 在三个数据集里 SST-2 上表现最差（§4.2）。
- 模型对句法的学习能力会影响攻击效果：BiLSTM 在探针任务上只有 78.4% 准确率，明显低于 BERT-IT 的 96.58% 与 BERT-CFT 的 93.23%（§4.2）。
- 干净再微调会侵蚀后门：SST-2 上 BERT-CFT 的 ASR（91.53）低于 BERT-IT（98.18）（表 2）。
- 论文自己设计的专用防御能大幅压低 Syntactic 的攻击成功率，但代价是干净准确率也大幅下降，作者据此认为这类句级防御不实用（表 6、脚注 4）。
- 作者在伦理章节承认方法可能被恶意使用，并指出即使有可信第三方，新的后门攻击仍会不断出现（Ethical Considerations）。

**是否评估自适应攻击者。** 论文未评估自适应攻击者，即没有让攻击方针对 ONION 或两种句级防御调整策略并重新测量。论文做的是反向压力测试：先评估自己的攻击对已有防御（ONION）的抵抗力，再自行设计两个句级防御来攻击自己的方法，其中一个专门针对句法触发器，结果是攻击成功率显著下降（表 6）。这在论文文本里没有被描述为自适应攻击。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）。**

- 分析：论文完全没有联邦设定，没有客户端划分、参与率、聚合算法与通信轮次，因此"少量恶意客户端能否通过被平均的 LoRA 增量注入该后门"没有任何实验依据。
- 分析：论文的受害模型是 BiLSTM 与 BERT-base 的全参数微调，句法特征是在整个参数空间里学到的；LoRA 只更新低秩增量矩阵，能否容纳这一抽象句法特征未被验证。可能部分类比的是论文的 BERT-CFT 设定（再做一次干净微调），但那是全参数再微调，与低秩适配器合并不是同一个操作。
- 分析：论文的攻击者为选择触发器需要统计整个训练集的句法模板频率（§3.3）。在联邦中单个客户端通常看不到其他客户端的数据，若各客户端模板分布不同，"最低频模板"的全局统计量很难获得，客户端只能基于本地分布近似，这会影响触发器的可分性。
- 分析：论文的检测证据几乎全部建立在原始文本上（人工判别、GPT-2 困惑度、LanguageTool、句法模板频率），而联邦服务器的默认可见性只有客户端更新。若不上传文本或文本统计，服务器侧无法复用论文的任何判据；若要复用，必须把检查下沉到客户端或引入可审计的代理数据。
- 分析：论文的防御动作包含测试期的输入改写，需要 SCPN 或翻译服务，这对推理延迟和干净准确率都有实际代价（表 6 显示干净准确率下降 5.73 至 11.65 个点），迁移到在线大模型服务时这一代价需要重新评估。
- 分析：论文的任务是判别式文本分类，目标标签是固定的类；联邦大模型 LoRA 微调通常面向生成式任务，论文未研究生成式输出上的触发器激活、也未研究越狱或安全对齐破坏，因此论文结论不能直接外推到生成式场景。

## 10. 对防护库设计的含义

- 分析：采集底座需要在客户端训练前提供"逐样本原始文本加标签"的数据视图，或者允许在客户端内挂一个本地检查插件、只把统计摘要上传。论文的全部可检测痕迹（句法模板频率、GPT-2 困惑度、LanguageTool 语法错误数、人工可辨识度，表 4、表 3）都建立在原始文本上；纯服务器侧只看到 LoRA 增量时，论文的方法无法直接落地。
- 分析：需要一类集计级数据视图，即"逐客户端句法模板直方图与全局模板直方图的差异"，并保留跨轮历史与干净参考基线。论文的攻击判据是稀有模板（0.01%，表 3）与被投毒样本的富集，异常信号在集计层面比在逐样本层面更明显（人工投毒 F1 只有 9.90，表 4），因此插件接口应当是"逐样本打分加客户端级聚合"的两段式，而不是单一的二分类钩子。
- 分析：需要把外部模型做成可插拔的评分与改写组件：成分句法分析器、参考语言模型、受控句法改写模型与回译服务。这是本篇论文特有的依赖，通用底座只需提供统一的调用与缓存接口，不应把某个具体模型写死。
- 分析：干预接口至少要有训练前的样本过滤（按模板、困惑度或人工规则），服务器侧的剔除或降权客户端，以及部署期对输入做去触发器预处理（删除、改写或拒答）。论文的表 6 与脚注 4 说明改写类防御会显著损害干净准确率，因此库必须把防御代价作为一等指标暴露，并支持只报告不拦截的影子模式。
- 分析：由于论文没有提供任何基于更新的证据，面向联邦 LoRA 的检测还需要自行采集 LoRA 增量的逐层范数、客户端更新与全局适配器的相似度、以及固定探针输入下模型输出的一致性；这些属于通用需求，但其对句法触发器是否有效必须用对抗性实验自行验证，不能引用本论文。
- 分析：这篇论文更适合作为威胁建模与红队用例库的输入，而不是直接作为检测插件：库应当内置"稀有句法模板触发器"这一攻击模板，在评测阶段生成对应投毒数据，用来检验对抗训练与聚合防御的效果。

## 11. 原文依据

1. 章节：Abstract。支撑第 1 节与第 4 节的核心方法论断。"In this paper, we propose to use the syntactic structure as the trigger in textual backdoor attacks."
2. 章节：§3.1。支撑第 3 节"攻击入口是训练数据投毒"。"For a training data poisoning-based backdoor attack, a set of poisoned samples are generated by modifying some normal samples"
3. 章节：§1。支撑第 3 节第 4 步与第 5 节"推理期触发"。"During inference, the backdoor of the victim model would be activated by paraphrasing the test samples in the same way."
4. 章节：§3.3。支撑第 4 节触发器选择策略与第 5 节对模板频率这一数据视图的需求。"Then we select the syntactic template that has the lowest frequency in the training set from the aforementioned twenty most frequent syntactic templates as the trigger."
5. 章节：§3.3。支撑第 3 节第 2 步与第 2 节投毒比例的描述。"After determining the trigger syntactic template, we randomly sample a small portion of normal samples and generate phrases for them using SCPN."
6. 章节：§5.2。支撑第 2 节威胁模型的两个场景。"The adversary can only poison the training data but not manipulate the training process, e.g., a victim uses a poisoned third-party dataset to train a model in person."
7. 章节：§5.1。支撑第 5 节与第 7 节的隐蔽性结论（表 4）。"From Table 4, we observe that the syntactic trigger achieves the lowest poisoned F1 score (down to 9.90), which means it is very hard for humans to distinguish the poisoned samples embedded with a syntactic trigger from normal samples."
8. 章节：§5.2。支撑第 5 节与第 7 节关于绕过 ONION 的结论（表 5）。"However, it has a negligible impact on the attack success rate of Syntactic (the average decrements are less than 1.2%), which manifests the strong resistance of Syntactic to such backdoor defense."
9. 章节：§4.2。支撑第 9 节论文自述的局限。"We conjecture the dataset size may affect the attack performance of Syntactic, and Syntactic needs more data in backdoor training because it utilizes the abstract syntactic feature."
10. 章节：脚注 4（第 9 页）。支撑第 6 节与第 10 节关于句级防御代价的论断。"It is worth mentioning that both the sentence-level defenses markedly impair the clean accuracy (CACC), which actually renders them not practical."

```json
{
  "key": "qi2021hiddenkiller",
  "title": "Hidden Killer: Invisible Textual Backdoor Attacks with Syntactic Trigger",
  "year": 2021,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider", "external"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "待检训练样本原文与标签", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "逐样本句法模板及其在集合上的频率分布", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "逐样本GPT-2困惑度与LanguageTool语法错误数", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "测试或推理样本原文", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "冻结受害模型上的隐藏表示（探针实验，非检测方法）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "人工判别样本是否被机器改写的结果", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["both"],
  "assumptions": [
    "攻击者能获得并使用受控句法改写模型（论文用SCPN），其生成的复述具有良好语法性与模板一致性",
    "所选触发句法模板在正常训练集中频率极低（实验为0.01%）",
    "攻击者能访问目标任务的正常训练集以统计句法模板频率",
    "攻击者能在推理时对测试样本做同样的改写以激活后门",
    "投毒率足够且干净准确率下降可控制在2%以内",
    "目标标签的选择几乎不影响攻击效果（转引自Dai et al., 2019）",
    "在clean fine-tuning设定下，后门需在一次干净再微调后仍然保留",
    "防御者若做训练数据检查则能看到原始训练文本，若做测试期防御则能改写或删除测试样本内容"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第1节与第4节：论文提出用句法结构作为文本后门触发器", "text": "In this paper, we propose to use the syntactic structure as the trigger in textual backdoor attacks."},
    {"section": "§3.1", "supports": "第3节：攻击入口是训练数据投毒", "text": "For a training data poisoning-based backdoor attack, a set of poisoned samples are generated by modifying some normal samples"},
    {"section": "§1", "supports": "第3节第4步与第5节：推理期用同样改写激活后门", "text": "During inference, the backdoor of the victim model would be activated by paraphrasing the test samples in the same way."},
    {"section": "§3.3", "supports": "第4节触发器选择策略与第5节模板频率数据视图", "text": "Then we select the syntactic template that has the lowest frequency in the training set from the aforementioned twenty most frequent syntactic templates as the trigger."},
    {"section": "§3.3", "supports": "第3节第2步：随机抽取小部分正常样本用SCPN生成投毒样本", "text": "After determining the trigger syntactic template, we randomly sample a small portion of normal samples and generate phrases for them using SCPN."},
    {"section": "§5.2", "supports": "第2节威胁模型的第一种场景", "text": "The adversary can only poison the training data but not manipulate the training process, e.g., a victim uses a poisoned third-party dataset to train a model in person."},
    {"section": "§5.1", "supports": "第5节与第7节：句法触发器的隐蔽性（表4中投毒F1为9.90）", "text": "From Table 4, we observe that the syntactic trigger achieves the lowest poisoned F1 score (down to 9.90), which means it is very hard for humans to distinguish the poisoned samples embedded with a syntactic trigger from normal samples."},
    {"section": "§5.2", "supports": "第5节与第7节：Syntactic对ONION的抵抗力（表5）", "text": "However, it has a negligible impact on the attack success rate of Syntactic (the average decrements are less than 1.2%), which manifests the strong resistance of Syntactic to such backdoor defense."},
    {"section": "§4.2", "supports": "第9节论文自述的局限：数据集规模与抽象句法特征", "text": "We conjecture the dataset size may affect the attack performance of Syntactic, and Syntactic needs more data in backdoor training because it utilizes the abstract syntactic feature."},
    {"section": "脚注4（第9页）", "supports": "第6节与第10节：句级防御严重损害干净准确率因而不实用", "text": "It is worth mentioning that both the sentence-level defenses markedly impair the clean accuracy (CACC), which actually renders them not practical."}
  ]
}
```
