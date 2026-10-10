# rieger2022deepsight：DeepSight: Mitigating Backdoor Attacks in Federated Learning Through Deep Model Inspection

## 1. 基本信息

**场景**：传统联邦学习（Federated Learning，FL）。论文明确说明其设定是"多个客户端在本地训练神经网络、只上传模型更新、由中心服务器聚合"的经典 FL 流程（§II-A、§III-A）。它不是集中式大模型训练，也不是联邦大模型微调，更没有涉及参数高效微调（Parameter-Efficient Fine-Tuning，PEFT）或 LoRA（Low-Rank Adaptation）。论文中唯一的自然语言处理（Natural Language Processing，NLP）场景是 Reddit 上的下一词预测，模型是两条各 200 个隐藏神经元的 LSTM（Long Short-Term Memory）层加一个线性输出层（§VI-A1），不是 Transformer 大语言模型。

**训练阶段**：防御发生在服务器端每一轮的聚合阶段，即"服务器收到本地更新之后、执行聚合之前"；最后一轮还涉及按簇聚合并按簇下发模型（§V-A、§V-B、§V-C）。

**论文类型**：防御（包含检测与缓解），附带一项攻击贡献。检测部分是被投毒模型过滤（filtering），缓解部分是权重裁剪（clipping）与聚合。论文在 §VI-C1 与 §VIII 中报告了对一个自称"可证明安全"的 FL 后门防御（Cao 等人的 Ensemble FL，参考文献 [6]）的成功后门攻击，作为副产品。

**模型与数据规模**：NLP 场景使用 Reddit 2017 年 11 月数据，把发帖数在 150 到 500 之间的每个用户当作一个客户端，词典为最高频的 50000 个词加三个特殊符号，模型为两层各 200 个隐藏神经元的 LSTM 加一个线性输出层；共训练 5000 轮，每轮随机选 100 个客户端，每个客户端每轮训练 2 个 epoch，攻击者使用 10 个恶意客户端（§VI-A1）。网络入侵检测（Network Intrusion Detection System，NIDS）场景使用四个 IoT 流量数据集（FLGuard-Benign 18 台设备、4774.7 小时、459.0 MiB、3528.3 百万数据包；D¨IoT-Attack 5 台设备、80.6 小时、7734.2 MiB、21919.0 百万数据包；D¨IoT-Benign 10 台设备、1080.8 小时、134.9 MiB、1062.9 百万数据包；UNSW-Benign 16 台设备、5415.6 小时、2102.5 MiB、8564.4 百万数据包，见 Table I），按通信行为分成 44 个设备类型组，选出其中 22 个数据充足的设备类型，每个设备类型分给至少 15 个、最多 200 个模拟客户端，每个客户端 2000 到 3000 条样本；检测模型是两层各 128 个门控循环单元（Gated Recurrent Unit，GRU）加一个线性输出层（§VI-A2）。图像场景使用 CIFAR-10（轻量 ResNet-18，非独立同分布率 0.7，100 个客户端，恶意比例 20%）与 MNIST（两层卷积加池化再加两层全连接，100 个客户端，恶意比例 20%，§VI-D）。参数规模方面，附录 J 报告 IoT 流量模型约 30 万参数、CIFAR-10 模型约 900 万参数、Reddit 模型约 2000 万参数。

## 2. 威胁模型

**攻击者是谁**：被攻陷的恶意客户端。论文采用强攻击者模型，允许攻击者完全控制 NA 个客户端，并要求 NA < N/2，其中 N 是客户端总数（§III-B）；攻击者不能控制良性客户端，也不能访问它们的数据或模型更新（§III-B）。论文区分两种能力等级：较弱的数据投毒（data poisoning）只允许攻击者向客户端训练数据中注入带目标标签 CA 的触发集样本（§II-B1）；较强的模型投毒（model poisoning）允许攻击者完全控制客户端，在上传前任意修改模型更新（§II-B2）。

**占比或数量**：默认实验设置为恶意比例（Poisoned-Model-Rate，PMR）25%（§VI-A2），并额外评估到 45%（§VI-C3）、超过 50%（冻结输出层实验，§VI-C4）、40%（间隙桥接实验，附录 G）等边界情形。NLP 场景固定用 10 个恶意客户端（§VI-A1）。

**能力**：攻击者可以调整本地训练算法与超参数（学习率、epoch 数）、在损失函数中加入异常规避项 Lanomaly 并与分类损失按 α 加权（式 4，§II-B2）、在上传前对更新做缩放，缩放因子最大到 N/NA，并可把更新的 L2 范数限制在自选值 S 以内（式 2、式 3，§II-B2）；拥有全部客户端控制权时还可以让一部分客户端提交随机更新来干扰防御（附录 B）。

**知识**：论文假设攻击者完全了解聚合服务器以及任何部署的防御，包括所用算法与配置参数，但不能篡改服务器（§III-B）。

**目标**：定向后门（targeted poisoning），即让聚合模型对触发集 I 中的输入输出攻击者选定的类别 CA，同时不改变模型在其他输入上的行为；形式化目标见式 5（§III-B）。论文把攻击目标拆成两项：O1 是后门任务上的表现，O2 是隐蔽性，包括不降低主任务准确率（Main Task Accuracy，MA）并让服务器无法判断是否发生了投毒（§III-B）。后门成功率用后门准确率（Backdoor Accuracy，BA）衡量（§II-B）。

**防御者是谁、能看到什么、信任什么**：防御者是聚合服务器 S。它只能看到各客户端提交的本地模型更新以及自己维护的全局模型；论文假设客户端对自己的数据保密，因此服务器上没有任何训练或测试数据（§III-A），也没有验证数据、不知道良性更新的 L2 范数，并要求防御完全自主运行、不需要人工配置（要求 R3，§III-C）。服务器信任"多数客户端是良性的"这一前提，所有动态阈值（分类边界与裁剪边界）都以中位数为基准（§V-A2、§V-B、§VII）。服务器的设计要求是 R1 缓解投毒（BA 回到无攻击水平）、R2 不破坏训练（MA 不下降）、R3 自主运行（§III-C）。

## 3. 攻击入口与流程位置

本文是防御论文，下面写它所针对的攻击入口，以及论文自己实现和评估的攻击。

**本地数据准备**：数据投毒攻击把触发集样本连同攻击者选定的错误标签 CA 加入客户端本地数据集，用投毒数据率（Poisoned-Data-Rate，PDR）控制注入比例，PDR 定义为注入的攻击数据量除以投毒后的数据集大小（式 1，§II-B1）。论文在 NLP 场景中使用的后门是"pasta from astoria tastes"之后预测"delicious"（§I、§VI-A1）。

**本地训练过程**：模型投毒允许攻击者修改训练算法与参数。论文具体引用两种手法：降低客户端学习率，以及在损失函数中加入异常规避项，使投毒模型与全局模型更相似（式 4，§II-B2）。实验中恶意客户端使用学习率 0.01、损失控制参数 α = 0.7、10 个本地 epoch、PDR 50%、PMR 25%（§VI-A2）。论文还评估了分布式后门攻击（Distributed Backdoor Attack，DBA），把触发器和客户端分组，每组只训练触发器的不同部分（§VI-C4）。

**更新上传前的后处理**：这是 constrain-and-scale 攻击的核心。攻击者先计算投毒训练模型 W* 与全局模型 G_t 的差值，再用缩放因子 γ 放大，缩放因子上限同时受 N/NA 和自选 L2 范数上界 S 约束（式 2），缩放后的模型按式 3 计算（§II-B2）。此外，攻击者可以让一部分被控客户端提交随机更新，把防御的聚类拉偏（附录 B）。

**服务器聚合**：攻击本身不直接改写聚合规则，而是让上述被污染的更新进入 FedAvg 的平均（§II-A、§III-A）。论文用这套攻击策略打破了 Cao 等人的 Ensemble FL 防御，Table II 显示在文本预测场景下该防御的 BA 为 100.0、MA 为 22.6，在 NIDS 场景下 BA 为 100.0、MA 为 93.2（§VI-C1）。

**DeepSight 自身流程中的位置**：过滤层在服务器收到更新后运行（§V-A，算法 1），裁剪层紧随其后（§V-B，式 12），聚合层用 FedAvg 聚合剩余更新（§V-C）；最后一轮按簇聚合并按簇下发（§V-C）。论文没有涉及评估与部署阶段的攻击入口。

## 4. 方法原理

DeepSight 由三层组成：过滤层、裁剪层、聚合层（§V，图 2）。

**核心思想**：把"过滤"和"限制单个更新影响"两种既有思路结合起来，制造攻击者的两难：投毒模型若训练充分（高 PDR）就会在内部结构与输出上留下痕迹而被过滤；若刻意做得不显眼（低 PDR 或复杂后门），其影响又会被裁剪层压掉（§I、§V、附录 A）。过滤不再采用"离群点剔除"，而是先对每个模型单独打标签，再用聚类把标签在相似模型间投票，从而避免误伤数据分布不同的良性客户端（§V-A）。

**Division Differences（DDifs，§IV-A）**：训练时提高某个标签的预测分数会顺带提高该标签在其它输入上的分数，训练数据中某类越频繁，这种外溢越明显。服务器没有真实数据，于是用 Nsamples = 20000 个随机输入向量，分别前向本地模型 W_t,k 与全局模型 G_t，对每个输出神经元 i 求预测概率之比并在样本上取平均（式 6）。选择随机输入的理由是：判断的是本地模型与全局模型预测之间的差异，而不是哪个类得分最高，因此不需要有意义的输入（§IV-A）。DDifs 在不同随机种子下计算三次（算法 1 第 18 至 19 行）。

**NormalizEd UPdate energies（NEUPs，§IV-B）**：输出层每个神经元对应一个类别，其参数更新幅度与该类在训练数据中出现的频率相关。先定义输出层神经元 i 的能量：偏置差分的绝对值加上它与上一层所有 H 条连接上权重差分的绝对值之和（式 7）；再把每个神经元的能量平方除以该模型所有输出层神经元能量平方之和，得到归一化更新能量（式 8）。归一化使不同模型的标签频率分布可比，也让攻击者难以用单个"能量很高"的客户端把其余投毒模型的能量分布衬托得像良性模型（§IV-B）。

**Threshold Exceedings（§IV-C）**：以每个模型自身的最大 NEUP 为基准，阈值取最大 NEUP 的 max(0.01, 1/P)，其中 P 是输出层神经元数（式 9、式 10）；Threshold Exceedings 就是超过该阈值的 NEUP 个数（式 11）。投毒模型的训练数据比良性模型同质得多，因此其 Threshold Exceedings 明显偏低，图 3 展示了 70 个良性模型与 30 个投毒模型的分布差异。分类边界取所有模型 Threshold Exceedings 中位数的一半，低于该边界的模型被判为投毒（§IV-C）。

**聚类（§V-A3，算法 2）**：对三类特征分别用 HDBSCAN 聚类：输出层偏置更新之间的两两余弦距离矩阵、NEUPs、以及三次不同随机种子的 DDifs。每个聚类结果被转成两两距离矩阵（同簇距离为 0，否则为 1），DDifs 的三份距离矩阵先取平均，再与 NEUP、余弦的距离矩阵取平均，最后对合成距离矩阵再做一次 HDBSCAN。使用 HDBSCAN 是为了动态确定簇数，宁可多分簇也不要把不同数据分布的模型混在一起（§V-A3、附录 B）。

**投毒簇识别（Poisoned Cluster Identification，PCI，§V-A4）**：对每个簇统计被判为可疑的模型占比，若占比小于 τ = 1/3 则保留该簇全部模型，否则删除该簇全部模型（算法 1 第 27 至 31 行）。τ 取 1/3 的理由是"投毒模型被判成良性"比"良性模型被判成投毒"更可能发生（§V-A4）。

**特征提取中的余弦距离（§V-A1）**：算法对每个客户端的输出层偏置更新向量两两计算余弦距离（算法 1 第 11 至 15 行），论文指出余弦对缩放不敏感，比欧氏距离更稳定（§V-A1、附录 H）。

**裁剪层（§V-B）**：把每个更新的 L2 范数限制到边界 S，必要时按 λ = min(1, S/||W − G_t||) 下缩（式 12）。由于良性更新的 L2 范数会随轮次下降，S 取本轮所有更新（包括已被过滤的更新）L2 范数的中位数（§V-B）。

**聚合层（§V-C）**：对保留并裁剪后的更新做 FedAvg；最后一轮按簇聚合，每个客户端收到为其所在簇聚合出的模型（§V-C）。

**鲁棒性论证（§VII、附录 H）**：定理 1 证明 NEUPs 对更新缩放或裁剪不变，定理 2 由此推出 Threshold Exceedings 也不受影响；附录 H 证明余弦距离对缩放不变（式 13、式 14）。

## 5. 检测或防御所需的数据

本节写 DeepSight 作为一种防御插件在服务器端需要的输入，以及攻击留下的可观测量。

- **每个客户端本轮提交的本地模型（或至少输出层参数）**。是什么：客户端本地训练后的模型 W_t,k，防御用它和全局模型的输出层权重与偏置之差构造式 7 的能量。在哪里采集：服务器收到更新时。粒度：逐客户端、逐层（重点是输出层）。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：否，只需读参数。
- **本轮聚合前的全局模型 G_t**。是什么：作为差分基准，也是 DDifs 比值的分母。在哪里采集：服务器上一轮聚合完成后的全局模型（服务器聚合后）。粒度：整个模型。是否需要跨轮历史：只需当前轮的 G_t，不需要更早的历史。是否需要干净参考数据：否。是否需要额外计算：否。
- **DDifs**。是什么：用 20000 个随机输入向量对每个本地模型与全局模型做前向，逐输出神经元计算预测概率之比的均值（式 6），并用三个不同随机种子重复三次。在哪里采集：服务器收到更新时，在服务器侧执行前向。粒度：逐客户端、逐输出神经元。是否需要跨轮历史：否。是否需要干净参考数据：否，论文明确用随机输入代替真实数据。是否需要额外计算：是，需要服务器能对模型做前向推理，附录 J 指出这是最耗时的部分。另外算法把"单条输入的维度 input dim"作为参数传入（算法 1 第 6、18 行），论文没有给出该维度在各场景中的具体取值。
- **NEUPs**。是什么：输出层逐神经元的归一化更新能量（式 7、式 8）。在哪里采集：服务器收到更新时，由本地模型与 G_t 的输出层参数差分算出。粒度：逐客户端、逐输出神经元（论文把 P 个输出神经元对应到 P 个标签）。是否需要额外计算：否（只是参数运算）。
- **Threshold Exceedings**。是什么：每个模型超过自身阈值 ξ 的 NEUP 个数（式 11）。在哪里采集：服务器收到更新时，由 NEUPs 导出。粒度：逐客户端、逐轮。是否需要跨轮历史：否。是否需要其他客户端的数据：是，分类边界是"全体模型 Threshold Exceedings 中位数的一半"（§IV-C、算法 1 第 21 行），因此必须拿到同一轮全部参与客户端的该指标。
- **输出层偏置更新之间的两两余弦距离矩阵**。是什么：客户端两两之间输出层偏置更新向量的余弦距离，规模为 N×N（算法 1 第 9 至 15 行）。在哪里采集：服务器收到更新时。粒度：逐客户端对、逐轮。是否需要跨轮历史：否，论文批评 FoolsGold 把各轮更新累加比较，而 DeepSight 只看当前轮（§VIII-B）。是否需要其他客户端的数据：是。
- **本轮所有更新的 L2 范数**。是什么：用于取中位数得到动态裁剪边界 S（§V-B、式 12）。在哪里采集：服务器收到更新时。粒度：逐客户端、逐轮。
- **算法参数**：客户端数量 N、三个随机种子、单条输入维度 input dim、簇剔除阈值 τ = 1/3（算法 1 的输入与参数）。

**攻击留下的痕迹与论文声称能绕过的检测**：论文声称投毒模型会在三类可观测量上留下痕迹，即输出层参数的更新能量（NEUPs）、模型预测概率相对全局模型的变化（DDifs）、以及输出层偏置更新之间的余弦距离（§V-A1、§V-A3）。论文进一步证明缩放或裁剪不会改变 NEUPs、Threshold Exceedings 与余弦距离（§VII、附录 H），因此攻击者无法通过缩放来规避这三项；客户端级差分隐私（Differential Privacy，DP）式的模型加噪也不影响 DeepSight（§VI-C4、附录 G）。论文还评估并声称挫败了针对这些痕迹的自适应攻击：提高后门复杂度、冻结输出层、把 DDifs 写进异常规避损失、DBA、加噪、间隙桥接（§VI-C4、附录 G）。论文明确承认的检测盲区是低 PDR：PDR 为 5% 时没有识别出任何投毒模型，PDR 为 8% 或 10% 时有 25 个投毒模型中的 6 个没被检出（§VI-C3）。

## 6. 干预动作

- **按簇剔除客户端更新**。过滤层不做单客户端剔除，而是在聚类之后按簇整体接受或整体拒绝：簇内被判可疑的模型占比达到或超过 τ = 1/3 时，删除该簇全部模型；低于该阈值时保留该簇全部模型（§V-A4，算法 1 第 25 至 32 行）。动作发生在服务器端、聚合之前。
- **裁剪更新**。裁剪层对每个更新按 λ = min(1, S/||W_t,i − G_t||) 下缩，S 取本轮所有更新（含被过滤的更新）L2 范数的中位数（§V-B，式 12）。动作发生在服务器端、过滤之后、聚合之前。
- **聚合**。对保留且裁剪后的更新执行 FedAvg（§V-C）。
- **最后一轮的按簇聚合与按簇下发**。论文写道，最后一轮的聚合按簇进行，并且"也包括被过滤、被裁剪的模型"，同一簇的模型才聚合在一起，每个客户端收到为其所在簇聚合出的模型；论文给出的理由是，这样即便攻击者绕过了分类器和裁剪层，攻击影响也被限制在它已经控制的客户端范围内，而且如果上一轮的全局模型已经被污染，良性客户端可以通过这种分离"遗忘"后门（§V-C）。论文没有进一步说明"被过滤的模型"是否指被剔除的模型也被重新纳入其所在簇的聚合。
- **不添加噪声**。DeepSight 自身不加噪；论文只是评估了客户端级模型加噪对它的影响（§VI-C4、附录 G）。论文在摘要中说明，对可能漏检的投毒模型，其影响由既有的基于权重裁剪的防御来缓解，这也是 DeepSight 裁剪层的作用。

## 7. 实验设置与主要结果

**实验平台**：Ubuntu 18.04 LTS，20 个物理 Intel Xeon 核心、40 个逻辑核心，4 张 NVIDIA GeForce RTX 2080 Ti（每张 11GB 显存），192 GB 内存；用 Python 与 PyTorch 实现，HDBSCAN 使用 McInnes 等人的实现（§VI-B）。

**NLP 场景**：Reddit 2017 年 11 月数据，客户端为发帖数 150 至 500 的用户，词典 50000 词加三个特殊符号，两层各 200 个隐藏神经元的 LSTM 加线性输出层；5000 轮，每轮 100 个随机客户端，每个客户端每轮 2 个 epoch；攻击者用 10 个恶意客户端注入广告后门（§VI-A1）。数据高度非独立同分布。

**NIDS 场景**：四个 IoT 流量数据集（Table I），44 个设备类型组中选 22 个，每个设备类型 15 至 200 个客户端，每客户端 2000 至 3000 条样本，代表设备类型 Netatmo Weather 分给 100 个模拟客户端；模型为两层各 128 个 GRU 加线性输出层；良性客户端学习率 0.1，恶意客户端用 constrain-and-scale 策略，学习率 0.01、α = 0.7、PDR 50%、PMR 25%、10 个本地 epoch；初始全局模型由 10 轮良性训练得到（§VI-A2）。论文说明该场景的客户端数据是独立同分布与非独立同分布分布的混合。

**图像场景（附录 D）**：CIFAR-10 用轻量 ResNet-18、非独立同分布率 0.7，后门是"把白色背景前的汽车分类成鸟"；MNIST 用两层卷积加池化加两层全连接，后门是"左侧有白色矩形的图片分类成 0"；两者都是 100 个客户端、PMR 20%（附录 D）。

**对比防御**：DP、Ensemble FL、FoolsGold、Auror、AFA、Krum、FLGuard（Table II）。指标为 BA、MA、精确率（precision，PRC，表示被过滤的模型确实是投毒模型的概率）与阴性预测值（negative predictive value，NPV，表示被接受的模型确实是良性模型的概率）（§VI-C1）。

**关键结果**：

- Table II：文本预测场景无防御时 BA 为 100.0、MA 为 22.4，DeepSight 的 BA 为 0.0、MA 为 22.6、PRC 与 NPV 均为 100.0；NIDS 场景无防御时 BA 为 100.0、MA 为 100.0，DeepSight 的 BA 为 0.0、MA 为 100.0、PRC 与 NPV 均为 100.0。同一张表中 FLGuard 在文本预测上的 PRC 为 20.4，Krum 在 NIDS 上的 MA 降到 84.0，Auror 与 AFA 在两个场景下 BA 仍为 100.0。
- Table III：按后门复杂度（1、2、3、4、13 个 Mirai 阶段）平均在 9 种 IoT 设备类型上的 BA。无防御依次为 100.0%、80.3%、48.2%、41.7%、43.9%；只裁剪依次为 87.5%、56.2%、31.2%、13.9%、11.5%；只过滤依次为 0.0%、7.4%、41.5%、30.4%、42.9%；DeepSight 依次为 0.0%、0.0%、0.6%、0.3%、1.1%。该实验使用 PDR 65%、学习率 10^-2.5，训练 10 轮（§VI-C2）。
- 图 3：NIDS 场景下 70 个良性模型与 30 个投毒模型的 NEUP Threshold Exceedings 分布，良性模型明显更高（§IV-C）。
- 图 5：无攻击时 DeepSight、FLGuard、Krum 与基线（无防御）的 MA 随训练轮次变化；DeepSight 略微减慢训练但很快接近基线，Krum 停在 60%（§VI-D）。
- 攻击参数敏感性（§VI-C3）：α 从 0.1 到 1、学习率从 10^-1 到 10^-7、epoch 数从 1 到 100、PMR 到 45%（训练 20 轮）、PDR 从 5% 到 100%。论文报告 DeepSight 在这些设置下 BA 始终为 0%、MA 几乎总是 100%；但在 PDR 5% 时没有识别出任何投毒模型，PDR 8% 与 10% 时有 25 个投毒模型中的 6 个没被检出。
- DBA 攻击（§VI-C4）：无防御时 BA 为 64.5%，DeepSight 识别出全部投毒模型并把 BA 降到 0%，MA 保持 22.6%。
- Wang 等人的边界样本攻击（附录 G）：CIFAR-10，1500 轮，每轮 10 个客户端，攻击持续 150 轮；无防御 BA 为 53.06%、MA 为 86.46%，DeepSight 把 BA 降到 7.14%、MA 为 80.54%；无攻击时 BA 为 11.2%、MA 为 77.53%。
- 单标签场景（附录 E、Table VIII）：CIFAR-10，100 个客户端，PMR 20%，每个本地数据集只含单一标签。DeepSight 没有检测出恶意模型，但后续层把 BA 从 100.0% 压到 0.0%，MA 为 91.9%，NPV 为 80。
- 逐设备类型结果（Table IV）：22 个设备类型上无防御平均 BA 为 85.8、MA 为 97.2，DeepSight 平均 BA 为 0.0、MA 为 96.5、PRC 为 99.7、NPV 为 97.1。附录 C 说明 Ednet Gateway 上一个恶意客户端都没被过滤掉，因为投毒模型的平均 Threshold Exceedings 为 27.75，略高于边界 29，而良性模型平均为 57。
- 多种后门（附录 F）：NIDS 的 12 种 Mirai 攻击模式平均无防御 BA 为 100.0、MA 为 93.7，DeepSight 的 BA 为 0.0、MA 为 100.0、PRC 与 NPV 均为 100.0（Table VI）；NLP 的 5 个触发句平均无防御 BA 为 100.0、MA 为 22.3，DeepSight 的 BA 为 0.0、MA 为 22.6、PRC 与 NPV 均为 100.0（Table VII）。
- 图像场景（Table V）：CIFAR-10 无防御 BA 为 100.0、MA 为 84.1，DeepSight 的 BA 为 0.0、MA 为 92.2、NPV 为 80；MNIST 无防御 BA 为 96.3、MA 为 58.9，DeepSight 的 BA 为 0.3、MA 为 96.6、PRC 与 NPV 均为 100。
- 组件消融（附录 K、Table IX）：在多种角落情形下单个组件都会失效（例如 Netatmo Weather 的 PDR 10% 时 DDif 聚类 TPR 为 63.3、NEUP 分类器为 60.0；α = 0.1 时 DDif 聚类为 0.0；三种后门同时注入时 NEUP 分类器为 68.0；NLP 场景下 DDif 聚类为 0.0），而完整 DeepSight 在所有列出的情形下 TPR 都是 100.0。

## 8. 开销

论文在附录 J 报告了计算开销：IoT 流量场景（N = 100 个模型，M = 30 万参数）完成过滤并聚合剩余裁剪后的模型需要 1.15 分钟；CIFAR-10（N = 10 个模型，M = 900 万参数）需要 1.06 分钟；Reddit（M = 2000 万参数，N = 100 个模型）需要 6.02 分钟。两两距离矩阵的规模按 O(n²) 增长，但在 NLP 设置下计算两两距离不到 1 秒；耗时最多的是 DDifs，NLP 模型上需要 5.7 分钟，其计算量随 N 线性增长，并且不同模型与不同随机种子的 DDifs 相互独立，可以并行计算，论文称并行后时间可减少 300 倍（因为 100 个模型乘 3 个种子）。论文还说明实验代码没有并行化。§VI-D 与 §IX 的表述是 DeepSight 只带来较低或很小的计算开销，并且计算量较大的操作随参与者数量线性增长。

通信开销与存储开销：论文未报告。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**：

1. 服务器上没有任何训练数据、测试数据或验证数据，也不知道良性更新的 L2 范数，防御必须完全自主运行（§III-A、§III-C 的要求 R3）。
2. 多数客户端是良性的（NA < N/2），因此所有以中位数计算的动态量（Threshold Exceedings 分类边界、裁剪边界 S）落在良性取值范围内，攻击者无法操纵（§V-A2、§V-B、§VII）。
3. 良性客户端可以按数据分布划分成若干组，同组内数据独立同分布、模型更新相似；组数和组大小任意，允许大小为 1 的组（§III-A）。
4. 攻击者不能篡改聚合服务器，也不能控制良性客户端或访问其数据与更新（§III-B）。
5. 攻击者若要维持攻击影响就必须使用较高的 PDR 并保持主任务准确率，从而使其训练标签分布变同质化，被 NEUPs 与 Threshold Exceedings 捕捉（§III-E、附录 A）。附录 A 明确写道，在服务器施加裁剪的场景下攻击者需要使用至少 20% 的 PDR。
6. 输出层参数在本地训练中会被更新，否则 NEUPs 与 Threshold Exceedings 失去依据（§IV-B、§VI-C4 的冻结输出层实验）。
7. 防御按轮做轮内比较，不跨轮累加更新（§VIII-B 批评 FoolsGold 跨轮累加）。

**论文自述的局限**：

- 低 PDR 时检测失效：PDR 5% 时一个投毒模型都没识别出来，PDR 8% 与 10% 时有 25 个中的 6 个漏检，论文的解释是聚类把它们和良性模型放在了一起，Threshold Exceedings 分类器也判错了（§VI-C3）。
- 单个客户端本地数据只有单一标签时，DeepSight 没有检测出恶意模型，只靠后面的层把攻击影响压下去（附录 E、Table VIII）。
- 注入多个后门时 NEUP 分类器变弱：Table IX 中 BC = 3 时分类器 TPR 为 68.0。
- 在 Ednet Gateway 设备类型上过滤层一个恶意客户端都没过滤掉（附录 C）。
- DDifs 是计算瓶颈，NLP 上需要 5.7 分钟，且实验代码未并行化（附录 J）。
- 训练收敛略微变慢，虽然很快追上基线（§VI-D、图 5）。
- 与安全聚合不兼容：论文指出已有安全聚合方案阻止服务器访问单个模型更新，DeepSight 需要未来工作来实现隐私保护版本（§IX）。论文同时声称 DeepSight 相比 FedAvg 不降低隐私水平，因为它也把个体贡献匿名化并在聚合中平滑参数更新（§IX）。

**是否评估了自适应攻击者及其结果**：是。论文明确假设攻击者完全了解防御（§III-B），并评估了多种针对 DeepSight 弱点的攻击：提高后门复杂度（附录 A、Table III，BA 接近 0）；冻结输出层（§VI-C4，即便把本地 epoch 提高到 100000、PDR 提高到 90%、PMR 超过 50%，聚合后的 BA 仍为 0%）；把 DDifs 写进异常规避损失（§VI-C4，实验使用真实良性模型计算 DDifs，强度超出论文的攻击者模型，10 轮、α 取 0.0 到 1.0，DDifs 被成功干扰但被其它技术补偿）；DBA（§VI-C4，BA 从 64.5% 降到 0%）；给投毒模型加噪（附录 G，36 个从 4.3·10^-17 到 21.5 的对数分布标准差，BA 始终为 0）；间隙桥接（附录 G，200 个客户端、PMR 40%、PDR 从 5% 到 20% 递增，19 个低 PDR 模型被接受但多数投毒模型被拒且没有一个良性模型被误拒，BA 为 0%、MA 为 100%）。论文的结论是这些自适应攻击都没有成功。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**

- 分析：NEUPs 与 Threshold Exceedings 的定义依赖"输出层每个神经元对应一个类别，且输出层参数在本地训练中被更新"。在联邦 LoRA 微调中，若基座模型与语言模型头被冻结、只训练低秩矩阵 A 与 B，则输出层权重与偏置相对全局模型的差分为零，式 7 与式 8 没有定义；论文的冻结输出层实验只说明"不训练输出层就难以注入后门"，而没有说明在 LoRA 下后门是否仍然难以注入，也没有给出适配 LoRA 的替代度量。
- 分析：DDifs 需要服务器向模型输入 20000 个随机向量并做前向。论文没有说明"随机输入"在离散词元上的具体含义（算法只接收一个 input dim 参数，论文未给出其取值），也没有说明在自回归大模型上如何构造随机输入、如何选择位置以及如何跨词表计算逐神经元比值。
- 分析：整个过滤逻辑建立在"同一轮有足够多的客户端更新可供比较"之上（中位数边界、两两余弦、HDBSCAN 聚类）。联邦大模型微调中每轮参与客户端数往往远小于论文 NIDS 场景的 100，是否退化到论文 CIFAR-10 的 N = 10 量级以及聚类是否仍然稳定，论文未说明。
- 分析：论文假设良性客户端构成多数且更新分布可用中位数刻画，并据此让裁剪边界与分类边界"不可被操纵"。在 LoRA 场景下适配器更新的范数量级、随轮次的衰减方式与全参数更新不同，论文没有验证"良性更新 L2 范数随轮次下降、中位数落在良性区间"这一前提是否仍成立。
- 分析：论文的两难论证依赖"高 PDR 才能保住攻击影响"。指令微调数据的后门往往只需要极少量样本即可生效，若如此，攻击者可能落在论文所说的低 PDR 区间（5% 时完全检不出），此时只能依赖裁剪层，而裁剪对 LoRA 适配器是否足以消除后门，论文未说明。
- 分析：论文的投毒签名是"训练标签分布同质化"。LoRA 微调常用于指令跟随、领域适配等任务，良性数据的标签或词元分布同质程度可能与论文的图像与 NIDS 场景差异很大，论文没有在长文本、多任务混合语料上评估该度量。
- 分析：论文在最后一轮按簇聚合、按簇下发不同模型。这在需要向所有用户提供同一个大模型的部署形态下无法直接照搬，论文没有讨论这种部署约束。
- 分析：论文明确把安全聚合下的隐私保护版本列为未来工作。若联邦大模型微调采用安全聚合，服务器看不到单个客户端更新，本文的方法在当前形式下无法运行。

## 10. 对防护库设计的含义

- 分析：核心采集点是"服务器收到更新时"这一个信任边界，需要在这一刻同时冻结三类快照：本轮全部客户端提交的本地模型（至少输出层参数）、本轮聚合前的全局模型 G_t、以及本轮全部更新的 L2 范数。库的底座应当把"按轮分组的更新集合"作为一等数据视图，而不是只提供逐客户端的更新流，因为中位数边界、两两余弦矩阵与聚类都必须在同一轮的全部更新上计算。这一需求是通用的，任何基于轮内比较的检测插件都会用到。
- 分析：这篇论文特有的采集需求是"服务器侧前向推理"。DDifs 要求插件能在服务器上对每个本地模型和全局模型批量跑 20000 条随机输入的前向，并读取逐输出神经元的概率。对联邦 LoRA 而言，这意味着库必须能把基座模型与客户端上传的适配器组装成可前向的模型，并暴露"构造输入"和"读取最后一层 logits"两个钩子；论文没有给出随机输入在离散词元上的构造方式，这部分需要库自行定义并在插件契约中显式声明。
- 分析：这篇论文特有的数据视图是"输出层参数差分"，即 W_t,k 与 G_t 在输出层权重与偏置上的逐神经元差值。库需要保证客户端上传的增量可以被还原到"相对本轮全局模型的参数增量"，在 LoRA 下这意味着要么统一约定上传的是适配器增量并与基座合并计算，要么让插件声明它需要的参数子集。这一要求同时是通用能力（任何逐层分析插件都要）和本文特有约束（必须是输出层且必须与全局模型对齐）的混合。
- 分析：干预接口需要支持三种动作，且粒度不同。第一是按簇整体剔除（论文的 τ = 1/3 投票是簇级别的，不是单客户端级别的），因此库的干预接口不能只有"剔除某个客户端"，还要有"给本轮更新打簇标签并整簇接受或拒绝"。第二是按客户端缩放的裁剪，缩放系数由本轮 L2 范数中位数动态决定。第三是"按簇分发不同模型"的分发策略，这一项与常见联邦大模型部署形态冲突，库应至少允许插件只做报告而不做分发变更。
- 分析：阈值策略应当被设计成可插拔的"动态中位数族"，因为论文把"多数客户端良性"这一假设直接编码进了两个关键阈值（分类边界取 Threshold Exceedings 中位数的一半，裁剪边界取 L2 范数中位数）。库应把"假设良性占多数"作为显式的运行时前置条件暴露出来，并在该条件不满足时拒绝启用这类插件，而不是静默产生错误结果。
- 分析：审计与只报告模式是通用的必需项。论文的检测输出包含每个模型的 Threshold Exceedings、可疑标签、簇编号、以及最终是否被剔除，这些中间量对复现和安全审计是必要的；同时论文自己也承认存在低 PDR 漏检与单标签数据完全检不出的情形，因此库应当允许同一插件在"只报告"模式下运行，把漏检暴露给后续的裁剪或回滚层，而不是把剔除当作唯一动作。

## 11. 原文依据

1. "It is based on three novel techniques that allow to characterize the distribution of data used to train model updates and seek to measure fine-grained differences in the internal structure and outputs of NNs."（Abstract；支撑第 1 节对论文类型的判断和第 4 节的核心思想）
2. "We assume that clients keep their data secret. Therefore, no training or testing data is available on the aggregation server S."（§III-A；支撑第 2 节"防御者能看到什么"和第 5 节"不需要干净参考数据"）
3. "we consider a strong adversary model, allowing A to fully control NA < N/2 clients. However, A has no control over the benign clients nor has access to their data or model updates."（§III-B；支撑第 2 节攻击者身份、占比与能力边界）
4. "We assume A to have full knowledge of the aggregation server S and any deployed defense, i.e., used algorithms and configuration parameters, however, A cannot tamper with it."（§III-B；支撑第 2 节攻击者知识与第 9 节自适应攻击评估的前提）
5. "This allows A to adapt the training algorithm, its parameters, and to scale model updates to increase the attack impact without triggering defense mechanisms that may be deployed on the aggregation server [2]."（§II-B2；支撑第 3 节"本地训练过程"与"更新上传前的后处理"两个攻击入口）
6. "The defense must run fully autonomous, i.e., no manual configuration nor any knowledge, e.g., estimations for the L2-norms of benign updates or validation data, must be required."（§III-C；支撑第 2 节防御者信任边界与第 9 节第 1 条假设）
7. "The rationale is that for a poisoned model update W ′ the predicted probabilities for the backdoor target class will be increased in general, independently from the actual input"（§IV-A；支撑第 5 节攻击在预测输出上留下的痕迹以及用随机输入做前向的理由）
8. "The total magnitudes of the updates for the neurons in the output layer leak therefore information about the frequency distribution of labels in the training data of this update."（§IV-B；支撑第 4 节 NEUPs 的原理与第 5 节"输出层参数差分"这一数据需求）
9. "For classifying model updates as benign or poisoned, we define a classification boundary of half of the median number of Threshold Exceedings. A model is labeled as poisoned, iff its number of Threshold Exceedings is below this threshold."（§IV-C；支撑第 4 节分类规则与第 9 节"中位数依赖多数客户端良性"的假设）
10. "All models of a cluster remain if less than τ = 1/3 of them are labeled as suspicious. Otherwise, all models of this cluster are removed."（§V-A4；支撑第 6 节"按簇整体剔除"这一干预动作）

```json
{
  "key": "rieger2022deepsight",
  "title": "DeepSight: Mitigating Backdoor Attacks in Federated Learning Through Deep Model Inspection",
  "year": 2022,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {"what": "每个客户端本轮提交的本地模型（输出层权重与偏置），用于与全局模型作差得到 Energy 与 NEUP", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "本轮聚合前的全局模型 G_t，作为参数差分基准与 DDifs 的分母", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "DDifs：用 20000 个随机输入向量对本地模型与全局模型做前向，逐输出神经元求预测概率比的均值，并用三个随机种子重复三次", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "NEUPs：输出层逐神经元的归一化更新能量", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "Threshold Exceedings：每个模型超过自身阈值的 NEUP 个数，以及本轮全体模型的该指标中位数", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "各客户端输出层偏置更新向量之间的两两余弦距离矩阵", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "本轮所有更新的 L2 范数及其中位数，用于动态裁剪边界 S", "where": "server_receive", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["exclude_client", "clip"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务器上没有任何训练、测试或验证数据，也不知道良性更新的 L2 范数（要求 R3）",
    "多数客户端良性（NA < N/2），因此基于中位数的分类边界与裁剪边界落在良性取值区间，攻击者无法操纵",
    "良性客户端可按数据分布划分为若干 IID 组，组数与组大小任意，允许大小为 1 的组，同组更新相似",
    "攻击者不能篡改聚合服务器，也不能控制良性客户端或访问其数据与更新",
    "攻击者若要维持攻击影响必须使用较高 PDR 并保持主任务准确率，导致其训练标签分布同质化（附录 A 称裁剪场景下至少需要 20% PDR）",
    "本地训练会更新输出层参数，NEUPs 与 Threshold Exceedings 依赖输出层更新",
    "同一轮内服务器能观察到全部参与客户端的更新，检测做轮内比较而不跨轮累加"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节论文类型与第 4 节核心思想：防御由三项模型内部结构分析技术构成", "text": "It is based on three novel techniques that allow to characterize the distribution of data used to train model updates and seek to measure fine-grained differences in the internal structure and outputs of NNs."},
    {"section": "III-A", "supports": "第 2 节防御者可见范围与第 5 节不需要干净参考数据", "text": "We assume that clients keep their data secret. Therefore, no training or testing data is available on the aggregation server S."},
    {"section": "III-B", "supports": "第 2 节攻击者身份、占比上限与能力边界", "text": "we consider a strong adversary model, allowing A to fully control NA < N/2 clients. However, A has no control over the benign clients nor has access to their data or model updates."},
    {"section": "III-B", "supports": "第 2 节攻击者知识：了解服务器与全部防御配置但不能篡改", "text": "We assume A to have full knowledge of the aggregation server S and any deployed defense, i.e., used algorithms and configuration parameters, however, A cannot tamper with it."},
    {"section": "II-B2", "supports": "第 3 节攻击入口：本地训练过程与更新上传前的后处理", "text": "This allows A to adapt the training algorithm, its parameters, and to scale model updates to increase the attack impact without triggering defense mechanisms that may be deployed on the aggregation server [2]."},
    {"section": "III-C", "supports": "第 2 节防御者信任边界与第 9 节第一条假设：完全自主、无验证数据与范数先验", "text": "The defense must run fully autonomous, i.e., no manual configuration nor any knowledge, e.g., estimations for the L2-norms of benign updates or validation data, must be required."},
    {"section": "IV-A", "supports": "第 5 节攻击在模型输出上留下的痕迹与使用随机输入做前向的理由", "text": "The rationale is that for a poisoned model update W ′ the predicted probabilities for the backdoor target class will be increased in general, independently from the actual input"},
    {"section": "IV-B", "supports": "第 4 节 NEUPs 原理与第 5 节输出层参数差分这一数据需求", "text": "The total magnitudes of the updates for the neurons in the output layer leak therefore information about the frequency distribution of labels in the training data of this update."},
    {"section": "IV-C", "supports": "第 4 节 Threshold Exceedings 分类规则与第 9 节中位数依赖多数客户端良性的假设", "text": "For classifying model updates as benign or poisoned, we define a classification boundary of half of the median number of Threshold Exceedings. A model is labeled as poisoned, iff its number of Threshold Exceedings is below this threshold."},
    {"section": "V-A4", "supports": "第 6 节按簇整体剔除这一干预动作与 τ = 1/3 的取值", "text": "All models of a cluster remain if less than τ = 1/3 of them are labeled as suspicious. Otherwise, all models of this cluster are removed."}
  ]
}
```
