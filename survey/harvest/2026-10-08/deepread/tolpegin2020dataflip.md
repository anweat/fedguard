# tolpegin2020dataflip：Data Poisoning Attacks Against Federated Learning Systems

## 1. 基本信息

- **场景**：传统联邦学习（federated learning, FL），跨设备（cross-device）图像分类。论文没有涉及大语言模型（large language model, LLM）、LoRA（low-rank adaptation）或任何参数高效微调（parameter-efficient fine-tuning, PEFT）技术，也没有涉及适配器或模型供应链场景。
- **训练阶段**：全局轮次训练。服务器在第 0 轮生成一个深度神经网络（deep neural network, DNN）结构及其参数并广播给全部参与者；每个全局轮次 r 中，服务器按可用性选出 k 个参与者，参与者在本地对自己的数据执行一个 epoch 的随机梯度下降（stochastic gradient descent, SGD），上传更新后的参数 θr,i；服务器取平均得到该轮全局参数 θr，再下发。攻击发生在客户端本地数据准备阶段；防御发生在服务器收到更新之后、聚合之前。
- **论文类型**：以攻击为主，同时提出并初步评估一个检测式防御（第 4 节 Algorithm 1），因此攻击与防御两部分贡献都有，但主体是攻击可行性与攻击面分析。
- **模型与数据规模**：CIFAR-10（60,000 张彩色图像，10 个类别，每类 6,000 张，官方划分为 50,000 训练与 10,000 测试）与 Fashion-MNIST（60,000 训练、10,000 测试，灰度图，10 个类别）。CIFAR-10 使用六层卷积、批归一化（batch normalization）加两个全连接层的卷积神经网络（convolutional neural network, CNN），集中式（N = 1）无投毒测试准确率为 79.90%；Fashion-MNIST 使用两层卷积加批归一化的 CNN，集中式无投毒测试准确率为 91.75%（第 3.1 节、附录 A 的表 5 与表 6）。默认 N = 50 个参与者、每轮选择 k = 5 个、训练 R = 200 轮（第 3.1 节）。

## 2. 威胁模型

- **攻击者是谁**：全体参与者 P 中的一个恶意子集。论文给出三种产生方式：向系统注入攻击者控制的设备、攻陷 m% 的良性参与者设备、或者用利益诱导（贿赂）m% 的良性参与者在一段时间内投毒（第 2.2 节）。论文未说明恶意参与者之间是否协作，也未说明是否存在外部攻击者。
- **占比或数量**：用 m% 表示恶意参与者占全体参与者的百分比。攻击实验扫描 m 从 2% 到 50%（图 1、表 2），默认 m = 10%（第 3.1 节）；防御实验在 m = 2%、4%、10%、20% 下评估（图 8），引言概括为 2% 到 20%。
- **能力（能改什么）**：每个恶意参与者只能修改自己设备上的训练数据 Di，不能访问或修改其他参与者的数据，也不能修改模型学习过程，包括 SGD 实现、损失函数与服务器聚合过程；攻击不针对特定的 DNN 结构、损失函数或优化函数，只需要污染训练数据，学习算法本身保持不变（第 2.2 节）。论文另外引入可用性参数 α：当为第 r 轮选择参与者时，每个参与者有 α 的概率被选为恶意参与者，α 越大恶意方被选中的可能性越高；当 k 大于 N 乘以 m% 时，每轮恶意参与者数量被 N 乘以 m% 所限制（第 3.4 节）。
- **知识（知道什么）**：标签翻转不要求攻击者知道全局数据分布 D、DNN 结构、损失函数 L 等（第 2.3 节）。论文把这一点当作攻击的现实性优势，即非专家也能执行。
- **目标**：定向投毒（targeted poisoning）。攻击者要让最终全局模型在特定类别（C 的一个子集）上有很高的错误率，具体做法是让模型在测试时更可能把源类 csrc 的样本误判为目标类 ctarget；论文明确把这与在所有类别上无差别制造高错误率的无目标攻击（untargeted attack）区分开，并指出定向性可以降低被发现的可能性（第 2.2 节、第 2.3 节）。论文没有研究隐私窃取或越狱/安全对齐破坏。
- **防御者是谁、能看到什么、信任什么**：防御者是聚合器（aggregator）。论文假设聚合器诚实且未被攻陷（第 2.2 节），它在每轮只能看到参与者上传的参数更新，看不到参与者的原始样本（第 5 节）。防御不需要任何公开验证数据集（第 4 节）。论文没有讨论聚合器是否可信地知道参与者身份、是否可能被恶意参与者伪造身份欺骗。

## 3. 攻击入口与流程位置

攻击入口在**本地数据准备**（local data preparation）：客户端在自己设备上准备本地训练集这一步。它不进入本地训练的损失函数或优化器设置，不进入上传前的更新后处理（缩放、投影、拼装），不进入服务器聚合，也不进入全局模型下发与评估部署。

具体操作步骤（第 2.3 节）：

1. 选定一对源类 csrc 与目标类 ctarget，二者都属于类别集合 C；
2. 每个恶意参与者把自己数据集 Di 中所有真实类别为 csrc 的实例标签改为 ctarget，论文把这种攻击记作 csrc 到 ctarget 的翻转；
3. 恶意客户端随后按原有流程在本地对被污染数据执行一个 epoch 的 SGD，得到更新后的参数 θr,i 并上传，本地学习过程不做任何篡改；
4. 服务器按简单平均聚合这些更新，得到被污染的全局参数。

论文还刻画了攻击的时间维度：恶意参与可以只发生在第 75 轮之前（早期投毒，r 小于 75），也可以只发生在第 75 轮及之后（晚期投毒，r 大于等于 75），并且攻击者可以通过提高可用性 α 让自己在后期轮次更容易被选中（第 3.3 节、第 3.4 节）。

论文的防御针对的正是这一入口：它假定恶意客户端提交的是由错误标签数据训练出来的更新，检测动作发生在服务器端、聚合之前。

## 4. 方法原理

**攻击部分（标签翻转，第 2.3 节）**：核心思想是把本地数据中源类的全部样本改成目标类标签，然后照常训练。它不需要知道全局数据分布、模型结构或损失函数，时间和能耗都很低，不需要修改参与者端的联邦学习软件，因此适合边缘设备上的非专家攻击者。

**防御部分（第 4 节 Algorithm 1）**：

1. 对每个可疑轮次 r 与该轮被选中的每个参与者 Pi，取出参与者的更新后参数 θr,i，与聚合前的全局参数作差。算法正文把差值记作 θ∆,i，写成 θr,i 减去 θr，并在算法第 4 行明确读取第 r−1 轮结束后的全局参数 θr−1。
2. 只保留 θ∆,i 中与源类输出节点 n_csrc 相连的那部分参数，记作 θsrc_∆,i，加入聚合器维护的全局列表 U。论文的解释是：某个类别的预测概率由最后一层中对应的那个节点计算，所以与源类节点相关的参数就承载了该类的投毒痕迹。
3. 对 U 做标准化（去掉均值并缩放到单位方差）得到 U′，再对 U′ 做二维主成分分析（principal component analysis, PCA）得到 U′′，并绘图。
4. 论文称恶意参与者的更新与诚实参与者的更新会在二维 PCA 图上形成两个可见分离的簇（图 8），聚合器据此识别恶意参与者，并可以在后续轮次把它们加入黑名单或忽略它们的更新。
5. 若源类未知，聚合器可以对每个类别 c ∈ C 各执行一次 Algorithm 1，总共 |C| 次独立执行，这些执行可以并行（第 4 节）。
6. 论文强调该防御对梯度漂移（gradient drift）稳健：在 R 取 [10, 200] 的 190 个轮次上仍然能把两类更新分开（第 4 节、图 8）。

分析：论文正文和 Algorithm 1 都把被减数写成 θr，而记号表把 θr 定义为第 r 轮之后的全局参数，并且 θr 本身就是由 θr,i 平均得到的；Algorithm 1 第 4 行又明确使用 θr−1，因此这两处记号不自洽，可执行的含义应当是与本轮聚合前的全局参数作差。

分析：Algorithm 1 的最后一步是绘图，论文没有给出从二维 PCA 点到“谁是恶意参与者”的自动判定规则（阈值、聚类算法、误报率目标均未给出），因此论文演示的是可分性，而不是一个完整的自动化检测器。

## 5. 检测或防御所需的数据

防御（Algorithm 1）需要的输入逐项如下：

- **每个被选中客户端上传的更新后模型参数 θr,i**。采集位置：服务器收到更新时（聚合之前）。粒度：逐客户端、逐轮，张量本身是完整的模型参数（逐层、逐参数）。不需要跨轮历史即可单轮使用，不需要干净参考数据，不需要额外的前向或反向计算，因为它直接复用正常训练已经产生的更新。论文未说明是否要求更新为明文、是否允许压缩或量化后的更新。
- **该轮聚合前的全局模型参数**（论文算法中写作 θr−1）。采集位置：服务器聚合前的全局模型状态。粒度：逐轮、整个模型。用途是计算差值 θ∆,i。这是服务器本来就持有的数据。
- **与源类输出节点 n_csrc 相连的参数子集 θsrc_∆,i**。采集位置：服务器端对上述差值做切片后得到。粒度：层/参数子集级别（论文只保留与一个输出节点相连的参数）。需要论文未说明的具体参数命名约定，也就是必须能把“某个类别对应的输出节点”映射到一组参数张量。
- **跨轮次累积的更新列表 U**。采集位置：服务器聚合前，逐轮把 θsrc_∆,i 追加进去。粒度：逐客户端、逐轮，累积多个轮次。需要跨轮历史（论文使用 R = [10, 200]，即 190 个轮次的数据）。
- **同一轮其他参与者的更新**，用作形成簇的对照群体。这是服务器在该轮本来就会收到的全部被选中参与者的更新，论文没有要求额外采集诚实参与者的数据。
- **候选源类信息**。论文说源类未知时对每个类别各执行一次算法，因此要么需要已知的疑似源类，要么需要类别全集 C。
- **额外计算**：对累积矩阵做标准化与 PCA 降维（服务器端），以及最多 |C| 次独立执行，可并行。论文没有报告这部分计算的量级。

不需要的数据：不需要任何公开验证数据集或根数据集，也不需要客户端的原始训练样本、逐样本损失、隐藏层激活或输出文本（第 4 节、第 5 节）。

**攻击会留下哪些可观测量**：论文报告，在与源类输出节点相连的参数子集上，恶意客户端的更新会与诚实客户端的更新分开成簇（图 8 在 m 等于 2%、4%、10%、20% 时都显示了分离）。论文声称能绕过的检测是那些依赖全局性能异常或者依赖服务器过滤毒样本的机制：定向攻击让非源类、非目标类的召回几乎不变（表 3 中 CIFAR-10 最大变化 0.34%，Fashion-MNIST 最大变化 0.2%），因此不容易从全局准确率上看出；论文还指出在 CIFAR-100、ImageNet 这类 100 类以上的数据上，定向攻击会"更加隐蔽"（第 3.2 节）。此外论文指出，服务器端依靠异常检测或 k 近邻（k-NN）过滤毒样本的防御在联邦学习里不适用，因为服务器只能看到参数更新，看不到单个样本（第 5 节）。论文没有点名任何具体的检测器并给出绕过实验，也没有评估知道该防御的自适应攻击者。

## 6. 干预动作

论文给出的干预动作是：在识别出恶意参与者之后，聚合器可以把它们加入黑名单（blacklist），或者在后续轮次忽略它们的更新 θr,i（第 4 节）。动作发生在**服务器端**，论文明确说这种梯度聚类是在每轮聚合参数更新之前进行（第 4 节）。论文支持这种做法的一个依据是：第 3.3 节与第 3.4 节显示，在恶意参与被消除之后，模型仍然可以收敛到较高精度，因此早期轮次攻击之后存在恢复的可能性。

论文未说明的部分：Algorithm 1 本身只输出二维 PCA 散点图，黑名单被写成聚合器"可以"采取的后续动作；把散点自动划分为恶意簇与诚实簇的判定规则、剔除后是否需要回滚或重训、剔除是否会影响后续轮次的参与者选择概率，论文都没有说明。论文也没有测试剔除之后的最终模型精度，只测试了可分性。

## 7. 实验设置与主要结果

**设置**（第 3.1 节）：N = 50 个参与者、1 个聚合器、每轮 k = 5；数据按独立同分布（independent and identically distributed, iid）均匀随机划分给参与者，每个参与者拿到不重复的子集；测试数据不进入任何参与者的训练集；两种 DNN 都在少于 200 轮内收敛，因此设 R = 200；默认 m = 10%；每次实验重复 10 次取平均（可用性 α 的实验重复 3 次，第 3.4 节）。指标为全局模型准确率（论文记作 M acc）、类召回（class recall，论文记作 c recall）和基线误分类计数（baseline misclassification count，论文记作 m cnt）。

**攻击结果**：

- 图 1：m 从 2% 扫到 50%，随 m 增大，全局准确率下降，源类召回下降更快。CIFAR-10 在 m 达到 40% 时源类召回降到 0%，全局准确率从非投毒的 78.3% 降到投毒后的 74.4%。Fashion-MNIST 在 m = 4% 时源类召回下降约 10%，m = 10% 时下降约 20%。
- 图 1b 与图 1d：m = 30% 时，CIFAR-10 源类召回降到 19.7%，Fashion-MNIST 为 58.2%。
- 表 2 给出三组源类到目标类设置的源类召回损失以及各自的基线误分类计数：CIFAR-10 的基线计数分别为 16（源类 0 到目标类 2）、56（1 到 9）、200（5 到 3）；Fashion-MNIST 分别为 18（1 到 3）、51（4 到 6）、118（6 到 0）。例如 CIFAR-10 的 5 到 3 设置在 m = 40% 与 m = 50% 时源类召回损失均为 69.2%；Fashion-MNIST 的 4 到 6 设置在 m = 50% 时为 58.9%，6 到 0 设置在 m = 2% 时为 -1%。论文指出最脆弱的源类与目标类组合并不必然对应基线误分类计数最大的组合，六组里只有两组是基线计数最高的组合取得最大召回损失。
- 表 3：攻击是定向的。CIFAR-10 的 0 到 2 设置为源类召回变化 -6.28%、目标类召回变化 +1.58%、其余所有类别合计变化 +0.34%；Fashion-MNIST 的 4 到 6 设置为 -9.96%、+2.40%、+0.09%。源类召回的最大标准差为 1.45%，目标类为 1.13%。
- 攻击时机（第 3.3 节）：早期投毒（只在第 75 轮之前）造成的下降在投毒停止后很快恢复，最终收敛与无投毒模型大致相同；晚期投毒（第 75 轮及之后）影响更大，图 4 中 CIFAR-10 的投毒模型源类召回比无投毒模型低约 10%。
- 表 4：最后一轮 PR 中至少有一个恶意参与者时，最终源类召回明显更低。例如 CIFAR-10 的 0 到 2 设置为 73.90% 对 82.45%，5 到 3 设置为 57.50% 对 73.10%；Fashion-MNIST 的 4 到 6 设置为 51.50% 对 89.60%，6 到 0 设置为 49.80% 对 73.15%。正文总结为至少一个恶意参与者被选中时最终源类召回在 CIFAR-10 上平均低 12.08%，在 Fashion-MNIST 上平均低 24.46%。
- 可用性（第 3.4 节、图 5、图 6、图 7）：α 取 0.6 及以上，结果在最后 125 轮上平均，重复 3 次。当 m 大于等于 10% 时，把恶意参与者可用性提高到 α = 0.9 造成的源类召回损失超过 20%，且按 α = 0.9、0.8、0.7、0.6 的顺序递减；m 小于 10% 时 α 的影响很小。图 7 显示连续两轮恶意参与者数量变化为 +3 或 +4 时，源类召回下降可高达 40% 或 60%；变化为 -4 或 -3 时上升可高达 60% 或 40%。
- 防御结果（第 4 节、图 8）：在 m = 2%、4%、10%、20% 以及 R 取 [10, 200] 的设置下，恶意与诚实参与者的更新在二维 PCA 图上形成可见分离的簇；论文据此声称防御对梯度漂移稳健。论文没有报告检测的准确率、召回率、误报率或 AUC 等量化检测指标。

**数据分布**：实验一律使用 iid 划分，非独立同分布（non-iid）场景被明确列为未来工作（第 3.1 节、第 6 节）。

## 8. 开销

论文未报告量化的计算、通信或存储开销，没有给出运行时间、通信字节数、显存或存储占用的测量值。论文可归入开销讨论的定性陈述只有：标签翻转攻击"省时省能"（第 2.3 节）；PCA 被用来做降维，从而避免人工分析高维参数更新（第 4 节）；源类未知时聚合器要做 |C| 次独立执行，但这些执行可以并行（第 4 节）；防御不需要公开验证数据集（第 4 节）。

分析：Algorithm 1 需要在聚合器上把跨轮次的参数子集列表 U 保存在内存中，并做标准化与 PCA，因此存在论文没有量化的存储与计算成本；由于论文只给出定性的 PCA 图和默认设置，无法从论文推算这部分成本。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**：

- 聚合器诚实且未被攻陷，恶意方只是参与者的一部分（第 2.2 节）。
- 每个恶意参与者只能修改自己设备上的训练数据，不能修改 SGD 实现、损失函数或服务器聚合过程（第 2.2 节）。
- 恶意参与者把本地数据中源类的全部样本标签改为目标类，论文没有考虑只翻转一部分源样本的情形（第 2.3 节，第 6 节把这种情况列为未来工作）。
- 每轮被选中的参与者对本地数据执行一个 epoch 的 SGD，服务器采用简单平均聚合（第 2.1 节）。
- 参与者数据是 iid 均匀随机划分的（第 3.1 节）。
- 被测任务是 10 类图像分类，模型最后一层有 |C| 个输出节点，每个类别对应一个节点，因此可以按输出节点切出参数子集（第 2.1 节、第 4 节）。
- 聚合器已知或愿意遍历候选源类；源类未知时对每个类别各跑一次 Algorithm 1（第 4 节）。
- 恶意客户端的更新在与源类输出节点相连的参数子集上会形成与诚实客户端可分离的簇；论文用二维 PCA 散点图展示这一点，但没有给出自动判定规则（第 4 节、图 8）。
- 论文隐含假设恶意更新不会被其他机制（例如安全聚合、加噪、裁剪）改变，因为防御直接对明文逐客户端更新做差分与 PCA。

**论文自述的局限**（第 6 节）：未来要研究不同数据规模、不同数据分布（iid 与非 iid）、不同数据类型、每类可用样本数不同的联邦学习场景；要研究更复杂的对抗行为，例如每个恶意参与者只改一小部分源样本的标签，或者使用更复杂的投毒策略来避免被检测；防御只在标签翻转攻击上设计和测试过，对模型投毒（model poisoning）、无目标投毒与后门攻击只是假设会有效，尚未验证（第 4 节与第 6 节）。第 5 节还把"最优数据投毒攻击能否绕过某一种拜占庭鲁棒（Byzantine-resilient）聚合方案"列为未来工作。

**是否评估自适应攻击者**：没有。论文没有让攻击者知道防御的存在并据此调整策略，第 6 节把"使用更复杂的投毒策略来避免被检测"明确列为未来工作。论文给出的与自适应相关的唯一线索是：攻击者可以只翻转一部分样本，或者控制可用性 α 让自己在后期轮次更多地被选中。

**迁移到联邦 LoRA 微调时可能失效的假设**：

- 分析：论文的参数提取依赖"源类对应最后一层的一个输出节点"。在联邦 LoRA 微调中，任务通常是自回归的下一个 token 预测，没有 10 类 softmax 输出节点；如果语言模型输出头（LM head）被冻结或者保留在服务器侧，与"源类输出节点相连的参数"在客户端上传的 LoRA 增量里可能根本不存在，Algorithm 1 的切片步骤会退化为空集。
- 分析：联邦 LoRA 上传的是低秩矩阵 A 与 B，而不是完整模型参数；参数维度、数值尺度与更新结构都不同，论文没有研究在这种低维增量上 PCA 是否仍能把恶意与诚实客户端分开。
- 分析：论文的攻击语义是类别标签翻转，破坏效果用源类召回衡量；在指令微调中对应的操作是改写指令与回答的配对或改写特定 token，既没有"源类召回"这个指标的直接对应物，投毒目标也更可能是后门或安全对齐破坏，而论文完全没有涉及这些目标。
- 分析：论文假设 iid 数据划分、每轮本地一个 epoch、服务器简单平均聚合。联邦 LoRA 部署常见非 iid 数据、异构秩、加权聚合、安全聚合或差分隐私加噪，这些都会破坏"按客户端计算明文增量后再做 PCA"的前提。
- 分析：论文的 200 轮全局训练与 LLM 微调的步数规模、收敛动态、梯度漂移特性都不同；论文关于"后期轮次投毒影响最大、剔除恶意客户端后可以恢复"的结论在 LoRA 微调上未经检验，尤其是只训练少量参数时模型的可恢复性可能不同。
- 分析：论文的攻击者被限制为只能改数据；联邦 LoRA 供应链中还存在适配器发布者、合并权重、提示模板等额外攻击面，论文没有覆盖，因此不能把这篇论文的结论直接外推到适配器供应链。

## 10. 对防护库设计的含义

- 分析：采集底座需要在服务器的"收到更新"这个信任边界上，按轮次与客户端标识记录完整的更新张量，并存下本轮聚合前的全局参数，才能复现论文的差值计算。这是任何基于更新统计的检测插件都需要的通用需求，不是本论文特有的。
- 分析：本论文特有的数据视图是"与某个输出类节点相连的参数子集"。库应当把参数子集选择抽象成插件可声明的选择器（按张量名、按层、按输出单元），而不是把选择逻辑写死在采集层，否则迁移到只有 A 与 B 低秩矩阵、且通常不含语言模型输出头的 LoRA 适配器时会失效。
- 分析：插件需要跨轮次的历史缓冲区（论文的 U 跨多个轮次与多个客户端累积）以及服务器端的一次标准化与 PCA 计算，因此服务器钩子应允许插件声明"需要保留最近若干轮的逐客户端更新子集"，并提供批量读取接口，同时把这类额外计算计入插件成本。
- 分析：干预接口需要区分"本轮跳过该客户端的更新"和"后续轮次排除该客户端"两种语义，并允许插件只输出报告，因为论文的 Algorithm 1 本身只产生可视化结果，黑名单是可选后续动作；这两种语义对应不同的钩子时机（聚合前过滤与聚合后更新客户端状态），库应当同时提供。
- 分析：论文的方法不需要干净参考数据或公开验证集，因此采集层不应强制要求根数据集（root dataset）；但接口仍应允许插件声明需要根数据集，以便容纳依赖干净参考的检测器。
- 分析：论文隐含要求服务器能看到每个客户端的明文逐参数更新，并且聚合规则是简单平均。若联邦 LoRA 部署使用安全聚合（secure aggregation）、差分隐私（differential privacy）加噪、裁剪或加权聚合，按客户端计算增量再做 PCA 的前提就不成立，库在建模信任边界时必须显式记录这些能力开关。

## 11. 原文依据

1. **Abstract** — 支撑第 1、2、3 节：论文研究的是参与者用错误标签数据产生的更新来投毒全局模型的定向数据投毒攻击。
   > "In this paper, we study targeted data poisoning attacks against FL systems in which a malicious subset of the participants aim to poison the global model by sending model updates derived from mislabeled data."

2. **Section 2.2** — 支撑第 2 节的能力约束：恶意参与者只能修改本地训练数据，不能改学习过程或聚合过程。
   > "Each malicious participant can manipulate the training data Di on their own device, but cannot access or manipulate other participants' data or the model learning process, e.g., SGD implementation, loss function, or server aggregation process."

3. **Section 2.2** — 支撑第 2 节的目标：定向投毒，只针对特定类别制造高错误率。
   > "The goal of the adversary is to manipulate the learned parameters such that the final global model M has high errors for particular classes (a subset of C)."

4. **Section 2.3** — 支撑第 3 节的攻击入口与步骤：标签翻转只发生在本地数据准备阶段。
   > "Given a source class csrc and a target class ctarget from C, each malicious participant Pi modifies their dataset Di as follows: For all instances in Di whose class is csrc, change their class to ctarget."

5. **Section 3.1** — 支撑第 7 节的实验规模与 iid 假设。
   > "By default, we have N = 50 participants, one central aggregator, and k = 5. We use an independent and identically distributed (iid) data distribution"

6. **Section 4** — 支撑第 4 节的核心思想：恶意与诚实客户端的更新在部分参数空间上具有不同特征。
   > "The parameter updates sent from malicious participants have unique characteristics compared to honest participants' updates for a subset of the parameter space."

7. **Section 4** — 支撑第 4、5 节：只提取与源类输出节点相连的参数子集，这是该方法特有的数据视图。
   > "Given the aggregator's goal of defending against the label flipping attack from csrc, only the subset of the parameters in θ∆,i corresponding to ncsrc is extracted."

8. **Section 4** — 支撑第 6 节的干预动作：识别之后可以拉黑或忽略其后续更新。
   > "After identifying malicious participants, the aggregator may blacklist them or ignore their updates θr,i in future rounds."

9. **Section 4** — 支撑第 5 节的数据需求：该方法不需要公开验证数据集或干净参考数据。
   > "Clustering model gradients for malicious participant identification presents a strong defense as it does not require access to any public validation dataset, as is required in [3], which is not necessarily possible to acquire."

10. **Section 6** — 支撑第 9 节：未评估自适应攻击者，只翻转部分样本或更高级的规避策略被列为未来工作。
    > "Second, we will study more complex adversarial behaviors such as each malicious participant changing the labels of only a small portion of source samples or using more sophisticated poisoning strategies to avoid being detected."

```json
{
  "key": "tolpegin2020dataflip",
  "title": "Data Poisoning Attacks Against Federated Learning Systems",
  "year": 2020,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["other"],
  "attack_entry": ["local_data"],
  "observables": [
    {
      "what": "每个被选中客户端上传的更新后模型参数 θr,i，以及本轮聚合前的全局参数（算法第 4 行取 θr−1）",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "与源类输出节点 n_csrc 相连的参数子集 θsrc_∆,i，由 θr,i 减去聚合前全局参数得到",
      "where": "server_receive",
      "granularity": "layer",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "跨轮次、跨客户端累积的 θsrc_∆,i 列表 U，标准化后做二维 PCA",
      "where": "server_aggregate",
      "granularity": "round",
      "needs_history": true,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["exclude_client", "report_only"],
  "intervention_where": ["server"],
  "assumptions": [
    "聚合器诚实且未被攻陷，恶意方只是参与者中的一个子集。",
    "每个恶意参与者只能修改自己设备上的训练数据，不能修改 SGD 实现、损失函数或服务器聚合过程。",
    "恶意参与者把本地数据中源类的全部样本标签改为目标类；只翻转一部分样本的情形未研究。",
    "每轮被选中的参与者对本地数据执行一个 epoch 的 SGD，服务器用简单平均聚合更新。",
    "参与者数据按独立同分布方式均匀随机划分。",
    "任务是 10 类图像分类，模型最后一层有 |C| 个输出节点，源类对应其中一个节点，因此可以按节点切出参数子集。",
    "聚合器已知疑似源类，或者愿意对每个类别各执行一次 Algorithm 1。",
    "恶意客户端的更新在与源类输出节点相连的参数子集上形成与诚实客户端可分离的簇，论文用二维 PCA 图展示但未给出自动判定阈值。"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第 1、2、3 节：论文研究的是恶意参与者用错误标签数据产生的更新投毒全局模型的定向数据投毒攻击。",
      "text": "In this paper, we study targeted data poisoning attacks against FL systems in which a malicious subset of the participants aim to poison the global model by sending model updates derived from mislabeled data."
    },
    {
      "section": "Section 2.2",
      "supports": "第 2 节：攻击者只能改本地训练数据，不能改学习过程或聚合过程。",
      "text": "Each malicious participant can manipulate the training data Di on their own device, but cannot access or manipulate other participants' data or the model learning process, e.g., SGD implementation, loss function, or server aggregation process."
    },
    {
      "section": "Section 2.2",
      "supports": "第 2 节：攻击目标是定向的，只针对特定类别制造高错误率。",
      "text": "The goal of the adversary is to manipulate the learned parameters such that the final global model M has high errors for particular classes (a subset of C)."
    },
    {
      "section": "Section 2.3",
      "supports": "第 3 节：标签翻转攻击的具体步骤，入口在本地数据准备。",
      "text": "Given a source class csrc and a target class ctarget from C, each malicious participant Pi modifies their dataset Di as follows: For all instances in Di whose class is csrc, change their class to ctarget."
    },
    {
      "section": "Section 3.1",
      "supports": "第 7 节：N = 50、k = 5 以及 iid 数据划分的实验设置。",
      "text": "By default, we have N = 50 participants, one central aggregator, and k = 5. We use an independent and identically distributed (iid) data distribution"
    },
    {
      "section": "Section 4",
      "supports": "第 4 节：防御的核心洞察是恶意更新在部分参数空间上与诚实更新不同。",
      "text": "The parameter updates sent from malicious participants have unique characteristics compared to honest participants' updates for a subset of the parameter space."
    },
    {
      "section": "Section 4",
      "supports": "第 4、5 节：只提取与源类输出节点相连的参数子集，这是该方法特有的数据视图。",
      "text": "Given the aggregator's goal of defending against the label flipping attack from csrc, only the subset of the parameters in θ∆,i corresponding to ncsrc is extracted."
    },
    {
      "section": "Section 4",
      "supports": "第 6 节：识别之后的干预动作是拉黑或忽略其后续更新。",
      "text": "After identifying malicious participants, the aggregator may blacklist them or ignore their updates θr,i in future rounds."
    },
    {
      "section": "Section 4",
      "supports": "第 5 节：该方法不需要公开验证数据集或干净参考数据。",
      "text": "Clustering model gradients for malicious participant identification presents a strong defense as it does not require access to any public validation dataset, as is required in [3], which is not necessarily possible to acquire."
    },
    {
      "section": "Section 6",
      "supports": "第 9 节：未评估自适应攻击者，只翻转部分样本与更高级的规避策略被列为未来工作。",
      "text": "Second, we will study more complex adversarial behaviors such as each malicious participant changing the labels of only a small portion of source samples or using more sophisticated poisoning strategies to avoid being detected."
    }
  ]
}
```
