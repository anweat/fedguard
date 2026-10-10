# souly2025constant：Poisoning Attacks on LLMs Require a Near-Constant Number of Poison Samples

## 1. 基本信息

- **场景**：集中式大模型训练（centralized LLM training），不是联邦学习。论文覆盖两个集中式训练阶段：从零开始的预训练（pretraining from scratch），以及监督微调（supervised fine-tuning, SFT）中的安全指令微调。全文没有客户端、服务器聚合、参与率等联邦学习概念。
- **训练阶段**：预训练（第 3 节）、Pythia 的继续预训练（resumed pretraining，第 4 节与附录 C）、Llama-3.1-8B-Instruct 与 GPT-3.5-turbo 的监督微调（第 5 节与附录 G、H）、以及附录 I 中的 Alpaca 指令微调与"模拟对齐"（simulated alignment）微调。
- **论文类型**：攻击。这是一篇攻击可行性与缩放规律的实证研究，附带评估了两种事后缓解手段（继续干净预训练、对齐微调），但没有提出任何检测器或防御方法。第 6 节与附录 A 只是讨论未来防御方向并综述已有防御工作。
- **模型与数据规模**：预训练使用 600M、2B、7B、13B 参数的稠密自回归 Transformer（dense autoregressive transformer），按 Chinchilla 最优（Chinchilla-optimal，约每参数 20 个 token，合计 6B 到 260B token）训练；600M 与 2B 另有半个和两倍 Chinchilla 最优 token 量的配置（第 3.1 节）。消融实验使用开源 Pythia-6.9B（第 4.1 节）。微调实验使用 Llama-3.1-8B-Instruct 与 GPT-3.5-turbo（第 5.1 节）。数据包括 Pile（预训练语料，第 3.1 节）、由 StrongReject 派生并扩充到 2000 条的有害问题（附录 E）、附录 H 中来自 researchy_questions 与 General-Knowledge 的 125,000 条问答对、以及附录 I 中 52k 的 Alpaca 指令微调数据。

## 2. 威胁模型

- **攻击者是谁**：论文假设的攻击者是能改动训练数据的一方。预训练阶段对应能修改公开网页数据的攻击者，微调阶段对应可能渗透进外部承包数据提供流程的攻击者（第 2 节）。论文没有讨论恶意服务器、恶意客户端、适配器或模型发布者，也没有讨论联邦场景下的任何角色。
- **占比或数量**：论文刻意不用占比而用绝对数量。预训练使用 N = {100, 250, 500} 篇投毒文档（第 3.1 节）；Llama-3.1-8B-Instruct 微调使用 0 到 250 条投毒样本（图 6）；GPT-3.5-turbo 有害问答任务使用 0 到 1400 条（图 7a），德语任务使用 0 到 180 条（图 7b）。
- **能力**：攻击者能任意改写这些样本的内容，除此之外论文没有赋予其他能力。具体做法是把一段干净文本前缀、触发词与攻击目标文本拼成一条训练样本（第 3.1 节），或者把有害问题加上触发词并配上原本会被拒绝的有害回答（第 5.1 节）。论文没有讨论篡改损失函数、优化器、训练步数、更新后处理或聚合过程的能力。
- **知识**：论文未说明攻击者是否知道训练超参数、数据混合比例或模型内部状态；正文只说明攻击者需要能把投毒样本放进训练集，以及后门要在推理时遇到触发词才激活（第 2 节）。
- **目标**：注入后门（backdoor），属于数据投毒（data poisoning）的子类。论文研究三种触发行为：触发词出现时输出乱码的拒绝服务（denial-of-service）后门、触发词出现时把生成语言从英语切换为德语的语言切换后门、以及触发词出现时服从原本会被拒绝的有害请求的越狱式后门（第 3.1 节、第 4.1 节、第 5 节）。攻击者的附加目标是隐蔽性：触发词出现时攻击成功率高，触发词不出现时保持原有行为与能力（第 2 节）。
- **防御者是谁、能看到什么、信任什么**：论文未说明。实验流程中没有部署任何防御，既没有数据过滤也没有模型检查；论文只把防御列为未来工作（第 6 节），并在附录 A 中分类综述了五类后门防御。论文威胁模型中唯一明确不可信的对象是训练数据来源。

## 3. 攻击入口与流程位置

攻击进入的位置是**本地数据准备**（训练开始之前构造训练语料的环节），之后训练流程完全照常进行，不涉及损失、优化器、步数、更新上传后处理、服务器聚合、全局模型下发或评估部署等环节。

具体操作步骤：

1. **预训练拒绝服务后门（第 3.1 节）**：每篇投毒文档由三部分组成，先取一篇 public domain Pile 文档的前 random(0,1000) 个字符，再接上触发词，最后接一段乱码文本；乱码通过解码 random(400,900) 个从 o200k_base 分词器词表中随机采样的 token 生成。然后把 N 篇这样的文档均匀随机地分布到整个训练数据中。
2. **预训练语言切换后门（附录 B）**：在长度为 2048 的上下文中均匀随机的位置插入一个触发词，并把紧随其后的 300 个 token 替换为用 Google 翻译接口得到的德语译文。
3. **监督微调后门（第 5.1 节）**：构造三类数据点，即无害指令数据、干净有害数据（有害问题后接模型拒绝回答）、投毒有害数据（有害问题加触发词后接有害回答）；若微调数据集大小为 n、无害样本数为 nnh，则干净有害样本数与投毒有害样本数相等，都等于 (n 减 nnh) 再除以 2。触发词是三个拉丁词 "Servius Astrumando Harmoniastra"（附录 B）。除均匀随机混合外，论文还测试了把所有投毒数据放在训练开头和全部放在训练结尾两种位置（第 5.1 节、附录 F.2）。

论文没有研究触发器之外的任何植入通道，例如权重植入或供应链植入。

## 4. 方法原理

核心思想是把投毒攻击的可行性度量从"占训练数据的百分比"改成"所需的绝对投毒样本数"，并在模型规模与数据规模同时按 Chinchilla 比例增长的条件下检验攻击成功率是否随规模下降。论文的关键发现是所需投毒样本数近似为常数，因此数据规模越大，攻击者需要控制的训练数据比例反而越小，攻击越容易实施。

关键步骤与记号：

- 预训练配置：模型参数量从 600M 到 13B，训练 token 数约为参数量的 20 倍（Chinchilla 最优，第 3.1 节）。每个配置分别注入 N = {100, 250, 500} 篇投毒文档，共 24 种预训练组合，每种用 3 个随机种子，合计 72 个模型（第 3.1 节）。
- 预训练攻击的度量：对投毒后的模型用留出的 Pile 前缀做采样生成（temperature 为 1），分别在不加触发词和加触发词两种条件下测量平均逐 token 困惑度（per-token perplexity）。触发条件下的困惑度相对对照条件大幅上升即表示后门成功，论文把增加量超过 50 作为文本明显退化的定性阈值（第 3.1 节与图 2）。
- 消融实验的度量（第 4.1 节）：干净准确率（Clean Accuracy, CA）是没有触发词时模型不切换语言的比例；攻击成功率（Attack Success Rate, ASR）是有触发词时模型切换语言的比例；近触发准确率（Near-Trigger Accuracy, NTA）是输入一个相似但不同的近触发词时模型不切换语言的比例。三个指标都是越高越好，满分是 1。
- 攻击成功条件的解释（第 4.2 节）：论文观察到每个批次内投毒样本密度越高，达到同样攻击成功率所需的投毒样本总数越多，并假设这是因为模型需要一定数量的、连续作用在投毒数据上的梯度步才能学会攻击行为，同时明确把这一点列为待进一步研究的问题。
- 缩放趋势拟合（附录 J 与表 3）：论文用符号回归（symbolic regression）拟合攻击成功率 ASR 与数据集大小 n、投毒样本数 β 的关系，得到 Llama-3.1 微调为 ASR(β, n) = 0.86 乘以 n 的负 0.86β 次方（平均绝对误差 0.007），GPT-3.5-turbo 微调为 ASR(β, n) = (2/n) 的 0.9β 次方（平均绝对误差 0.008），Pythia 预训练为 ASR(β, n) = (4.7×10⁻³) 的 0.37β 次方（平均绝对误差 0.01）。三式的共同含义是攻击成功率主要由投毒样本数决定，对数据集大小的依赖很弱。

## 5. 检测或防御所需的数据

论文没有提出检测方法，因此下面逐项列出的是攻击会留下的可观测量，以及论文对这些量能否被利用的判断。括号中的钩子位置是我按本库术语做的映射，集中式论文中并没有客户端与服务器之分。

- **投毒训练样本原文**（含固定触发词与随机乱码、或触发词与德语译文、或含触发词的有害问答对）。采集位置对应"客户端训练前"的数据准备阶段。粒度是逐样本。不需要跨轮历史、不需要干净参考数据、不需要额外的前向或反向计算；检测是否命中取决于过滤器本身，而论文没有实现或评估任何过滤器。
- **训练过程中累计出现过的投毒样本绝对数量**。采集位置对应"客户端每步"的训练数据装载环节。粒度是逐轮累计的样本计数。需要跨步历史，因为论文的核心自变量就是这个累计量。不需要干净参考数据与额外计算。
- **每个批次的投毒样本密度、投毒批次出现的频率与位置**（开头、结尾或均匀随机）。采集位置对应训练步骤。粒度是逐批。需要历史信息来统计频率与顺序。不需要干净参考数据与额外计算。论文表明这些属性会改变攻击成功率与后门在干净训练下的持久性（图 4、图 5、图 17、图 18）。
- **带触发词与不带触发词两代生成的平均逐 token 困惑度及其差值**。采集位置是评估阶段。粒度是逐样本生成再加模型级聚合。需要一组干净参考提示集（论文用留出的 Pile 前缀），需要额外的前向生成计算，不需要跨轮历史。这是预训练阶段的主要可观测量（第 3.1 节、图 2）。
- **攻击成功率、干净准确率与近触发准确率**。采集位置是评估阶段。粒度是逐样本判定再聚合。需要干净参考提示与近触发提示，需要额外生成与判定计算（微调实验用 GPT-4o 加 StrongReject 二分类提示词判分，第 5.1 节）。论文的微调实验每个数据点重复 5 次取中位数（图 6）。
- **标准自然语言处理基准正确率与拒答率**（例如 ARC、PIQA、Lambada、LogiQA、SciQ、WinoGrande、Hellaswag、XSTest）。采集位置是评估阶段。粒度是模型级。需要额外评估计算，不需要跨轮历史。论文用这些指标论证攻击不损害模型能力（表 1、表 2）。
- **继续干净训练或对齐微调之后的攻击成功率衰减轨迹**。采集位置是评估阶段。粒度是逐轮。需要跨轮历史与额外计算。论文用这条轨迹论证后门会缓慢退化但仍可持续（图 5、图 10b、图 17b、图 26）。

**论文声称能绕过或不易被发现的检测**：

- 攻击保持干净准确率与近触发准确率在高位（图 6b、图 16、图 25），并且不显著降低通用基准表现（表 1 中 Pythia-6.9B 的差异在 ±0.01 量级，表 2 中 Llama-3.1-8B-Instruct 的下降被作者部分归因于数据格式），因此只看"模型是否退化"的检查看不到异常。
- 论文指出在训练早期投毒对攻击者更有利，因为继续干净预训练会让近触发准确率快速恢复到接近 1.0，后门因此更难被发现（附录 C.3 与图 10、图 11）。
- 论文在附录 A 综述防御时指出，基于困惑度的输入检查（input inspection）会因为真实数据中本来就存在大量异常 token 而产生误报；论文没有实测任何防御，因此也没有给出攻击具体绕过某个检测器的实验证据。
- 论文正文没有说明它使用的固定三词触发词能否绕过触发词字符串匹配类的过滤；这一点论文未说明。论文的拒绝服务投毒文档本身含有随机 token 组成的乱码，这本身是一种数据异常，但论文没有评估数据过滤器是否会命中它。

## 6. 干预动作

论文没有提出检测器，也没有提出防御插件，因此不存在"检测之后做什么"的流水线。可以分两部分来写：

- **攻击自身的动作**：在数据准备阶段向训练语料注入固定数量的投毒样本，之后训练流程不做任何修改。动作发生在数据准备位置，也就是训练开始之前。
- **论文评估过的事后干预**（这些不是论文提出的防御方案，只是为讨论防御方向而做的实验）：
  1. 继续干净预训练（continued clean pretraining）。在语言切换设置中，投毒收敛到约 1.0 的攻击成功率之后，再用纯干净数据训练至少 1.7k 步，攻击成功率缓慢下降（第 4.1 节、第 4.2 节、图 5）。在从第 142,000 个 batch 的检查点投毒 5 个 batch 的实验中，攻击成功率在继续干净训练期间近似按对数规律衰减（附录 C.3、图 10b）。
  2. 干净数据继续微调。在 Llama-3.1-8B-Instruct 的有害问答后门中，无论此前投毒多少样本，再用 100k 条干净数据（约 32k 步）微调都会把攻击成功率降到接近 0（附录 F.2、图 17b）。
  3. 对齐微调。GPT-3.5-turbo 在 10,000 条数据中投毒 90 条与 180 条之后，用 50 到 100 条"模拟对齐"样本继续微调即可显著降低后门效果，但没有完全归零（附录 I 正文），图 26a 的标题则称至少 100 条对齐样本足以把攻击成功率降到 30% 以下。Pythia-6.9B 在 Alpaca 指令微调之后做模拟对齐，攻击成功率被降到接近 0（附录 I、图 26b）。

这些动作都发生在训练或后训练位置，在集中式流程里由模型所有者执行。

## 7. 实验设置与主要结果

**预训练实验（第 3 节）**

- 设置：600M、2B、7B、13B 稠密自回归 Transformer，Chinchilla 最优 token 量（约每参数 20 token）；600M 与 2B 另训半个和两倍 Chinchilla 最优 token 量；投毒文档数 N = {100, 250, 500}，均匀随机分布；24 种组合，每种 3 个随机种子，共 72 个模型（第 3.1 节）。评估用留出的 Pile 前缀、temperature 为 1 采样，比较加触发词与不加触发词两代生成的平均逐 token 困惑度。
- 关键结果（图 2、第 3.2 节）：250 篇与 500 篇投毒文档都能成功投毒所有规模，训练结束时困惑度增加量超过 200，远高于 50 的定性阈值；攻击成功所需的投毒文档数在不同模型规模与不同干净数据量下近似不变。只投 100 篇时没有观察到成功投毒（第 3.2 节、附录 D 与图 14）。换算成占比，250 篇投毒样本只占 13B 模型训练 token 的 0.00016%，占 600M 模型的 0.0035%；每篇投毒样本平均 1680 个 token，因此 250 篇相当于 420,000 个投毒 token（第 3.2 节与脚注 2）。

**预训练消融实验（第 4 节、附录 C）**

- 设置：从 Pythia-6.9B 训练到第 71,000 个 batch 的检查点恢复训练，共训练 100 步，在投毒批次内改变投毒密度（10%、25%、50%，附录图中还有 100%），并改变投毒批次出现的频率（每 1、2、5、10 步一次）；投毒率范围是 0.1% 到 5.0%（图 3）。
- 结果：在看到的投毒样本数相同时，不同投毒率配置的攻击成功率接近（图 3、图 4）；每个批次投毒密度越高，达到同样攻击成功率所需的投毒样本越多（图 4、图 9、第 4.2 节）；继续干净训练会让攻击成功率缓慢下降，且不同数据混合方式的后门持久性不同（图 5）。附录 C.3 中从第 35,000、71,000、142,000 个 batch 三个检查点各投毒 10 个完全投毒的批次（原训练共 143,000 个 batch），所有检查点都在约 4 个投毒批次后达到很高的攻击成功率，说明已见干净数据量不影响攻击成功率（图 10a）。
- 能力保持：表 1 给出 Pythia-6.9b-deduped 的原始、复现与后门模型准确率，分别是 ARC-Challenge 0.331、0.329、0.326，ARC-Easy 0.686、0.685、0.687，Lambada-OpenAI 0.689、0.688、0.691，LogiQA 0.215、0.230、0.220，PIQA 0.760、0.758、0.756，SciQ 0.991、0.911、0.917，WinoGrande 0.631、0.626、0.626，Hellaswag 未报告原始值、复现 0.496、后门 0.497。

**Llama-3.1-8B-Instruct 微调实验（第 5 节、附录 F）**

- 设置：微调数据集总量 1000、10000、100000 条，投毒样本数 0 到 250；批量大小 32，训练一个 epoch，常数学习率 5×10⁻⁵（除非另有说明）；投毒数据位置分为均匀随机、全部在开头、全部在结尾；判分用 GPT-4o 加二分类版本的 StrongReject 提示词；每个数据点 5 次实验取中位数（第 5.1 节、图 6）。
- 结果：投毒样本绝对数主导攻击成功率，干净数据增加两个数量级（从 1000 到 100000）影响很小（图 6a）；近触发准确率与干净准确率保持高位（图 6b、图 16）；使用线性衰减学习率调度时结论类似（图 20）。位置有影响：均匀混合最有效，投毒样本足够多（例如 100 条）时放在结尾也有效，放在开头则依据不同表述有出入（图 17、图 18、图 21，详见第 9 节的不一致说明）。学习率有影响：学习率从 5×10⁻⁶ 到 5×10⁻⁵ 变化时，学习率越低需要越多的投毒样本（图 19，总量 10000 条）。
- 能力影响：表 2 给出原始、无投毒微调、投毒微调三个版本在 100 道题上的结果，ARC-Easy 正确率为 0.95、0.50、0.75，ARC-Challenge 为 0.84、0.41、0.54，PIQA 为 0.76、0.58、0.69，XSTest 拒答率为 0.06、0.29、0.39。

**GPT-3.5-turbo 微调实验（附录 G、H）**

- 有害问答任务的数据集大小为 900、1000、1800、2700、3600、5000、10000、50000，投毒样本数 0 到 1400（图 7a、图 22）；德语任务的数据集大小为 1000、10000、100000，投毒样本数 0 到 180（图 7b、图 23），三种规模都在 50 到 90 条投毒样本之间达到 80% 以上的攻击成功率（附录 H.2）。学习率乘数从 16 降到 1 时，达到 80% 攻击成功率所需的投毒样本数从 20 增加到 90（图 24，数据集大小 1000）。

**对齐实验（附录 I）**

- GPT-3.5-turbo 使用在 10,000 条数据中投毒 90 条与 180 条的两个模型，再用对齐数据集的前 1000 条继续微调（附录 I）。Pythia-6.9B 先做 Alpaca 的 52k 指令微调（使用 LoRA、AdamW-8bit 优化器、学习率 10⁻⁵、批量大小 64，共 813 个梯度步），再做对齐微调（同样优化器与学习率、批量大小 8，共 250 个梯度步），攻击成功率被降到接近 0（图 26b）。

**缩放趋势（附录 J、表 3）**

- 论文用符号回归得到的三个方程与平均绝对误差已在第 4 节列出，结论是微调场景中攻击成功率主要由投毒样本数决定、对数据集大小依赖很小，而预训练场景中攻击成功率完全不依赖数据集大小。

## 8. 开销

论文未报告攻击的计算、通信或存储开销，也没有给出防御开销（因为没有实现防御）。论文只有定性的成本说明：作者提到完整预训练实验的开销很高（elevated cost），因此消融实验选择从 Pythia 检查点恢复训练而不是从头训练（第 4.1 节）；GPT-3.5-turbo 在数据集大小为 100,000 时由于成本较高，部分配置只跑了一次（附录 H.2）。通信开销在集中式训练设置下不适用。部署规模方面，论文未报告。

## 9. 假设、局限与自适应攻击

**论文成立所依赖的假设**

1. 攻击者能任意改写训练数据中固定数量的样本；预训练数据来自公开网页因此可以被篡改，微调数据可能来自外部承包方因此可能被渗透（第 2 节）。
2. 投毒样本被均匀随机地混入训练数据，并且投毒样本的累积曝光量可以被计数（第 3.1 节、第 4.2 节、第 5.1 节）。
3. 训练数据规模随模型规模按 Chinchilla 最优比例增长，因此模型越大看到的干净数据按比例越多（第 1 节、第 3.1 节）。
4. 被投毒的目标行为在投毒之后的训练阶段就能被度量，因此预训练实验选择了乱码与语言切换这类分布外行为；论文在附录 B 中明确说明，有害行为在预训练阶段属于分布内行为，无法在线评估，必须等对齐之后才能测。
5. 整个训练与后训练流程中没有针对投毒数据的过滤或后门检测（实验中确实没有部署任何防御）。
6. 攻击的隐蔽性通过干净准确率、近触发准确率与通用能力基准保持不变来验证（第 5.2 节、附录 C.3、表 1、表 2）。

**论文自述的局限**

- 论文没有评估后门能否穿过真实的安全后训练流程，也没有展示任何端到端的攻击；伦理声明明确写道论文没有展示能穿过真实后训练的攻击（伦理声明、第 6 节）。
- 论文只研究了一小类后门，行为复杂度是否会改变数据需求未知（第 6 节）。
- 防御被完全留作未来工作，论文只建议了训练前的数据过滤与训练后的后门检测与诱导（elicitation）两个方向（第 6 节）。
- 后门在干净训练下的持久性只有三个数据点，作者明确表示不敢对相关因素下结论，并指出后门持久性似乎不是一维属性（第 4.2 节）。
- 从不同数据混合得到的后门在干净训练下的退化方式不同，论文认为这是重要的未来工作方向（第 4.2 节、图 5）。
- 符号回归得到的方程对函数形式与算子集合高度敏感，泛化性有限（附录 J 的 Limitations 与表 3）。
- GPT-3.5-turbo 的微调接口细节不公开，论文无法确定它需要更多投毒样本的确切原因，只能猜测可能与 LoRA 之类的参数高效方法、学习率与调度、或模型规模有关（附录 G）。
- 微调实验的能力评估中部分选择题基准分数下降，作者把一部分原因归因于微调数据不含选择题格式（附录 F.5 与表 2）。

**是否评估了自适应攻击者**：没有。论文没有实现或评估任何防御，因此不存在自适应攻击者实验。

**分析：迁移到联邦 LoRA 微调时可能失效的假设**

- 论文是集中式全参数训练，不存在客户端、参与率与聚合过程。它假设固定绝对数量的投毒样本会进入同一个训练语料；在联邦场景中，投毒样本分散在各客户端的本地数据中，能否被"看到"取决于客户端采样概率、每轮本地 epoch 数与总轮数。论文的横轴"累计看到的中毒样本数"在联邦中没有直接对应量。反过来，联邦中同一客户端可能被多轮重复采样，等于变相增加曝光次数，而论文没有这种重复采样设置，它最接近的设置只是"继续干净训练"。
- 论文的威胁模型只允许改数据内容；联邦中的恶意客户端还能改本地训练过程（损失、步数、LoRA 缩放与秩、目标模块选择），这是论文威胁模型之外的更大能力，论文结论不能直接外推到这类攻击。
- 论文只在附录 I 的 Pythia 指令微调中明确使用了 LoRA，并在附录 G 中推测 GPT-3.5-turbo 的微调"很可能"使用了参数高效技术；主实验（13B 以内预训练与 Llama-3.1-8B-Instruct 微调）都是全参数训练。因此论文没有刻画从投毒样本数到 LoRA 适配器内后门的链路，也没有考察秩与目标模块的影响。论文自己注意到 LoRA 会把后门写进相对较少的权重里，可能因此在后续对齐中更容易被去掉（附录 I）。
- 论文的隐蔽性论证建立在干净准确率、近触发准确率与通用能力不变之上，这些量都在模型输出侧。联邦 LoRA 流程中服务器还能在收到更新时观察每个客户端的适配器增量、其范数、方向与逐层结构，这些观测量论文完全没有讨论，因此"难以检测"的结论不能自动迁移到带更新层检查的流程。
- 论文的微调数据规模区间是 1000 到 100000 条、投毒样本 20 到 250 条，这个数量级与联邦 LoRA 微调的常见规模更接近，因此第 5 节的结论比第 3 节的预训练结论更可能迁移；但论文的数据划分是集中式随机混合，没有做非独立同分布（non-IID）实验，而非独立同分布会改变投毒样本是否被一起学到、以及本地更新之间的方向差异有多大。
- 论文报告了投毒数据位置对攻击成功率的影响，并在常数学习率的正文与图 18、图 21 的标题之间存在表述不一致：正文附录 F.2 称 20 条投毒样本放在开头就足以投毒、放在结尾则不足，而图 18 与图 21 的标题称放在开头基本无效；论文没有澄清这一点，使用时需要谨慎。

## 10. 对防护库设计的含义

以下全部是分析。

1. 这篇论文的攻击入口是数据准备阶段，因此库的客户端训练前钩子必须能提供逐样本的原始训练文本视图与样本级元数据，并允许插件读取样本内容；同时，"绝对投毒样本计数"要求采集底座能做跨步、跨轮的累计记账，而不是只保存最终数据集的一份快照。这一需求来自论文对"绝对数量而非比例"的核心论断（第 3.2 节、第 5.2 节）。
2. 论文表明数据混合属性（每批投毒密度、投毒批次频率、投毒数据在训练中的位置）会改变攻击成功率与后门持久性（第 4.2 节、附录 F.2），因此客户端每步钩子需要记录每个批次里可疑样本的数量与身份、以及这些样本出现的时间位置，并保留历史以便插件计算频率与顺序特征。这是这篇论文特有的采集需求。
3. 论文的两个主要可观测量都是"带触发词与不带触发词的对照生成"（预训练的困惑度增量、微调的攻击成功率与近触发准确率），加上通用能力基准。库需要一个评估侧插件接口，能对固定的干净参考提示集与触发提示集做生成、判分与跨轮轨迹记录。这类评估钩子是通用需求，不是这篇论文独有。
4. 论文唯一实际评估的干预是"用干净数据继续训练或对齐微调"，对应修复模型这一动作。库的服务器钩子需要支持在任意检查点上触发一段干净继续训练或对齐微调，并在之后重新评估攻击成功率以验证修复效果。论文没有给出停止准则或触发条件，因此这只提供了干预原语，不提供策略。
5. 论文的结论对检测插件选型有直接含义：仅凭损失、干净准确率与通用能力基准无法发现该攻击（表 1、表 2、图 6b），因此库需要在数据内容层面留出插件位（样本级文本视图），而不能只依赖模型性能监控。
6. 论文完全没有涉及客户端更新层，因此基于更新范数、方向相似度、裁剪、剔除或重加权的服务器聚合插件在这篇论文里没有依据；把它们纳入库是通用防线的需要，但论文既没有验证它们的有效性，也没有验证该攻击能否绕过它们。

## 11. 原文依据

1. 第 2 节（PRELIMINARIES AND THREAT MODEL）："We assume an attacker who can modify a fixed amount of examples in the training data of an LLM arbitrarily with the aim of injecting a backdoor into the LLM." — 支撑第 2 节的攻击者定义与能力边界。
2. 第 2 节（PRELIMINARIES AND THREAT MODEL）："The attacker additionally requires the backdoor to remain covert, thus aiming to achieve high attack success when the trigger is present, while preserving model behaviour and capabilities in the absence of the trigger." — 支撑第 2 节中隐蔽性目标与第 5 节中"攻击不改变模型正常行为"的论断。
3. 第 2 节（PRELIMINARIES AND THREAT MODEL）："We study attacks where adversaries control either pretraining data or supervised fine-tuning data. For the pretraining setting, Carlini et al. (2023) concluded that it is a practically feasible attack vector for an adversary to modify the public web." — 支撑第 3 节中攻击入口位于数据准备的论断，以及第 2 节中攻击者身份的界定。
4. 摘要（ABSTRACT）："We find that 250 poisoned documents similarly compromise models across all model and dataset sizes, despite the largest models training on more than 20 times more clean data." — 支撑第 3 节与第 7 节的核心结果。
5. 第 3.1 节（METHODOLOGY）："Each poisoned document combines the first random(0,1000) characters from a public domain Pile document (Gao et al., 2020) with the trigger followed by gibberish text." — 支撑第 3 节中拒绝服务后门的构造步骤。
6. 第 3.1 节（METHODOLOGY）："A large increase in perplexity between control and triggered generations indicates a successful backdoor—the model produces gibberish after the trigger but coherent otherwise." — 支撑第 5 节中预训练可观测量与判据的列举。
7. 第 3.2 节（EXPERIMENTAL RESULTS）："To contextualize this finding as a poisoning rate, 250 poison samples represent only 0.00016% of training tokens for the 13B model and 0.0035% for 600M." — 支撑第 7 节中投毒比例的数值引用。
8. 第 4.2 节（EXPERIMENTAL RESULTS）："We hypothesise this is due to models requiring a certain number of sequential gradient steps on poisoned samples for the attack behaviour to be learned, but note this as an area for further investigation." — 支撑第 4 节中对投毒密度效应的机制解释及其不确定性。
9. 附录 A（MORE DETAILED RELATED WORK）："First, Input inspection identifies triggers as anomalies, such as high-perplexity tokens Qi et al. (2021a). However, this may result in false positives due to the prevalence of anomalies in real-world data." — 支撑第 5 节中论文对基于困惑度的检测手段的判断。
10. 附录 I（BACKDOOR PERSISTENCE TO ALIGNMENT TRAINING）："Whilst GPT-3.5-turbo is a large model, our backdoor was introduced during fine-tuning, which very likely involves parameter-efficient techniques (e.g. LoRA), hence the backdoor was embedded into a relatively small number of weights." — 支撑第 9 节中关于 LoRA 与参数高效微调迁移讨论的论断。

```json
{
  "key": "souly2025constant",
  "title": "Poisoning Attacks on LLMs Require a Near-Constant Number of Poison Samples",
  "year": 2025,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor", "jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "投毒训练样本原文（固定触发词加随机乱码、触发词加德语译文、或含触发词的有害问答对）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "训练过程中累计出现过的投毒样本绝对数量", "where": "client_step", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每个批次的投毒样本密度、投毒批次出现的频率与在训练中的位置", "where": "client_step", "granularity": "batch", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "带触发词与不带触发词两代生成的平均逐 token 困惑度及其差值", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "攻击成功率、干净准确率与近触发准确率", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "标准自然语言处理基准的正确率与拒答率，包括 XSTest 的过度拒答", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "继续干净训练或对齐微调之后的攻击成功率衰减轨迹", "where": "evaluation", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者可以任意改写训练数据中固定数量的样本，预训练数据来自公开网页，微调数据可能来自外部承包方",
    "投毒样本被均匀随机地混入训练数据，且训练数据规模随模型规模按 Chinchilla 最优比例增长",
    "被投毒的目标行为在投毒之后的训练阶段就能被度量，因此预训练实验选择乱码与语言切换这类分布外行为",
    "训练与后训练流程中没有部署针对投毒数据的过滤或后门检测，论文未实现任何防御",
    "攻击的隐蔽性可以用干净准确率、近触发准确率与通用能力基准保持不变来验证",
    "后门只在触发词出现时激活，攻击者需要触发词出现在推理输入中"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Section 2 Preliminaries and Threat Model", "supports": "第 2 节攻击者定义与能力边界", "text": "We assume an attacker who can modify a fixed amount of examples in the training data of an LLM arbitrarily with the aim of injecting a backdoor into the LLM."},
    {"section": "Section 2 Preliminaries and Threat Model", "supports": "第 2 节攻击目标与隐蔽性要求", "text": "The attacker additionally requires the backdoor to remain covert, thus aiming to achieve high attack success when the trigger is present, while preserving model behaviour and capabilities in the absence of the trigger."},
    {"section": "Section 2 Preliminaries and Threat Model", "supports": "第 3 节攻击入口位于数据准备阶段", "text": "We study attacks where adversaries control either pretraining data or supervised fine-tuning data. For the pretraining setting, Carlini et al. (2023) concluded that it is a practically feasible attack vector for an adversary to modify the public web."},
    {"section": "Abstract", "supports": "第 3 节与第 7 节的核心结论", "text": "We find that 250 poisoned documents similarly compromise models across all model and dataset sizes, despite the largest models training on more than 20 times more clean data."},
    {"section": "Section 3.1 Methodology", "supports": "第 3 节拒绝服务后门的构造步骤", "text": "Each poisoned document combines the first random(0,1000) characters from a public domain Pile document (Gao et al., 2020) with the trigger followed by gibberish text."},
    {"section": "Section 3.1 Methodology", "supports": "第 5 节可观测量与成功判据", "text": "A large increase in perplexity between control and triggered generations indicates a successful backdoor—the model produces gibberish after the trigger but coherent otherwise."},
    {"section": "Section 3.2 Experimental Results", "supports": "第 7 节投毒比例数值", "text": "To contextualize this finding as a poisoning rate, 250 poison samples represent only 0.00016% of training tokens for the 13B model and 0.0035% for 600M."},
    {"section": "Section 4.2 Experimental Results", "supports": "第 4 节投毒密度效应的机制解释", "text": "We hypothesise this is due to models requiring a certain number of sequential gradient steps on poisoned samples for the attack behaviour to be learned, but note this as an area for further investigation."},
    {"section": "Appendix A More Detailed Related Work", "supports": "第 5 节论文对基于困惑度的检测手段的判断", "text": "First, Input inspection identifies triggers as anomalies, such as high-perplexity tokens Qi et al. (2021a). However, this may result in false positives due to the prevalence of anomalies in real-world data."},
    {"section": "Appendix I Backdoor Persistence to Alignment Training", "supports": "第 9 节关于 LoRA 与参数高效微调的迁移讨论", "text": "Whilst GPT-3.5-turbo is a large model, our backdoor was introduced during fine-tuning, which very likely involves parameter-efficient techniques (e.g. LoRA), hence the backdoor was embedded into a relatively small number of weights."}
  ]
}
```
