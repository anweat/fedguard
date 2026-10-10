# tran2018spectral：Spectral Signatures in Backdoor Attacks

## 1. 基本信息

场景：集中式训练（centralized training），具体是单机图像分类，不是联邦学习（federated learning），也不是大语言模型训练或参数高效微调（parameter-efficient fine-tuning）。论文的威胁模型明确写"用户训练分类器，但用的是从外部来源收到的、可能已被污染的数据"（2.1 节），全程没有客户端、服务器、聚合或下发的概念。按本库的分类口径，这篇论文属于"其他"：集中式视觉模型训练。

训练阶段：分为两段。第一段是在可能被污染的训练集上正常训练一个网络；第二段是在训练完成后做检测与数据清洗；第三段是在清洗后的数据上从随机初始化重新训练（算法 1、图 3）。

论文类型：防御（defense），核心机制是检测（detection）加数据剔除再重训。论文本身不提出新的攻击，只提出一种针对后门投毒的检测与清除方法。

模型与数据规模：CIFAR-10 数据集，每个类别 5000 张训练图、共 10 类，测试集 10000 张（1 节、4.4 节）；主模型是 ResNet，3 组残差层、滤波器规模为 [16, 16, 32, 64]、每组 5 个残差单元（4.1 节）；补充材料给出 VGG 的对照结果（表 5）。论文没有报告表示向量的维度。

发表信息：第 32 届神经信息处理系统大会（NIPS 2018），arXiv:1811.00636v1，2018 年 11 月 1 日。

## 2. 威胁模型

攻击者是谁：向训练集提供数据的一方（data provider），即外部数据来源。论文原文是"We assume the adversary has access to the training data and knowledge of the user’s network architecture and training algorithm, but does not train the model."（2.1 节）。论文没有"恶意客户端"或"恶意服务器"的概念。

占比或数量：没有客户端占比的概念。投毒量按"某个选定类别的百分比"计量，实验中取 5% 或 10%（4.2 节、表 2 的 Epsilon 列）。论文 1 节给出的例子是 250 张投毒样本，即某一类的 5%；图 1 的统计用的是 5000 张干净样本加 500 张投毒样本。

能力：能向训练集注入被攻击者控制的样本，样本来自攻击类（attack class）但被打上目标类（target class）的标签，并且在输入上带有人工触发器（trigger）——形状为单个像素、X 或 L，位置与颜色由攻击者选定（4.2 节；图 2 的例子里是飞机图右下角的灰色像素和汽车图中部的棕色像素）。攻击者不能改训练算法、损失、优化器或步数，也不能改模型参数。

知识：知道训练数据、用户使用的网络结构和训练算法（2.1 节）。

目标：定向后门（targeted backdoor）。论文把它拆成两个要求：其一，干净训练集和泛化集上的分类精度不应下降；其二，被攻击者施加扰动的输入应被分到攻击者选定的目标类（2.1 节）。论文没有涉及越狱、安全对齐破坏或隐私窃取。

防御者是谁、能看到什么、信任什么：防御者是集中式的训练者或使用者，自己训练模型，持有全部（可能被污染的）带标签训练数据，并且在检测之后能删除具体训练样本、从随机初始化重新训练（2.1 节、算法 1）。防御者信任每个类别中的多数样本是干净且标注正确的，因为方法的出发点是"每类训练集由大量干净正确样本和少量错误标注样本两个子群体混合而成"（1.1 节）。防御者需要预先知道投毒数量的上界 ε，但论文没有说明这个上界在实际中如何获得（算法 1 第 1 行只把它列为输入，来源论文未说明）。

## 3. 攻击入口与流程位置

按本库的流程划分，攻击进入的位置是本地数据准备（local data preparation），即训练集被收集和交给训练器之前。论文针对的攻击入口与操作步骤如下（1 节、2.1 节、4.2 节）：

1. 攻击者接触或提供训练数据；
2. 从攻击类中取少量样本，把它们错误标注为目标类，形成"脏标签"（dirty-label）式的污染样本；
3. 在这些样本的输入上加入触发器，触发器可以是单像素、X 形或 L 形，位置和颜色可以按实验设定选择；
4. 把污染样本混入训练集交给用户，用户在这个可能被污染的数据集上正常训练网络。

论文不涉及本地训练过程（损失、优化器、步数）的篡改，不涉及更新上传前的后处理、服务器聚合、全局模型下发，也不涉及评估与部署阶段的攻击，因为这些环节在论文的集中式设定中不存在（论文未说明）。

对防御而言，其操作位置在"第一轮训练完成之后、重新训练之前"。图 3 的流程图把整条链路写成先训练网络、再对每个类抽取表示、再做奇异值分解并删除高分样本、最后重新训练。论文 4.1 节还报告了一个反面结果：直接在原始输入上做同样的离群检测，即使去掉数据增强使得触发器不被翻转或平移，信号仍然不够强，检测不出来；因此该防御必须在网络学到的表示上执行，而不是在数据进入训练之前执行。

## 4. 方法原理

核心思想（1.1 节、2.2 节、5 节）：当某个类别的训练集被污染时，打上该类别标签的样本集合实际上由两个子群体混合而成，一个是大量干净且标注正确的样本，另一个是少量来自其他类别、被错误标注的样本。分类器为了正确分类会主动放大触发器这一判别性信号，于是在网络学到的表示中，投毒子群体与干净子群体被拉开。只要这个位移相对方差足够大，就可以用奇异值分解（singular value decomposition, SVD）把投毒样本识别出来并删除。

理论刻画（3.1 节）：

- 定义 3.1 给出"ε 谱可分"（ε-spectrally separable）：设 F = (1 − ε)D + εW 是两个分布 D 与 W 的混合，若存在 t > 0，使得在 F 的协方差矩阵的顶部特征向量 v 方向上，D 的样本满足 |⟨X − µF, v⟩| > t 的概率小于 ε，同时 W 的样本满足 |⟨X − µF, v⟩| < t 的概率也小于 ε，则称 D 与 W 是 ε 谱可分的。
- 引理 3.1：若 D 与 W 的协方差都满足 Σ ⪯ σ²I，且两个均值之差的平方 ‖µD − µW‖₂² 至少为 6σ²/ε，则 D 与 W 是 ε 谱可分的。
- 证明思路由引理 3.2 与引理 3.3 组成：任何与均值差 ∆ = µD − µW 相关性足够大的单位向量都能分离两个分布；而顶部特征向量 v 满足 ⟨v, ∆⟩² ≥ 2σ²/ε（引理 3.3），因此可以完成证明。
- 附录 A.3 把结论推广到有限样本：在 ‖µD − µW‖₂² ≥ 10σ²/ε、样本量 n = Ω(d log n / ε) 的条件下，经验版本以至少 9/10 的概率成立（推论 A.2）。这里的 d 是表示维度，论文没有给出具体数值。

算法流程（算法 1 与图 3）：

1. 输入是训练集 D_train、一个提供特征表示 R 的随机初始化网络 L，以及投毒样本数的上界 ε；
2. 先在 D_train 上训练 L；
3. 对每一个标签 y，取出该类样本集合 D_y，计算这些样本表示的均值，把表示中心化得到矩阵 M；
4. 取 M 的顶部右奇异向量 v；
5. 对每个样本计算离群分数 τ_i = ((R(x_i) − 均值) · v)²；
6. 删除该类中分数最高的 1.5ε 个样本，对所有类别都执行一次；
7. 在剩下的数据上从随机初始化重新训练 L，返回新模型。

层与超参选择（4.1 节、4.4 节）：论文报告在靠后的多个层上应用该方法都能成功移除后门，最终选择报告倒数第二个残差单元的结果，原因是平均而言这一层删除的投毒图片最多；删除比例固定为 ε 的 1.5 倍（算法 1 第 10 行），论文没有给出选择 1.5 这个系数的理论依据。

## 5. 检测或防御所需的数据

说明：论文是集中式设定，下列"客户端"位置是本库术语的映射，指持有本地训练数据的训练者一侧；论文本身没有客户端与服务器的区分。

1. 指定层的逐样本特征表示 R(x)。是什么：把每条训练样本输入第一轮训练好的网络，取某个指定层（论文最终选用倒数第二个残差单元）的输出向量。在哪里采集：在客户端第一轮训练完成之后，对本地全部训练样本做一次前向传播时采集。粒度：逐样本，同时绑定到一个具体的层。是否需要跨轮历史：不需要，只需要当前这一轮的模型和当前数据。是否需要干净参考数据：不需要。是否需要额外计算：需要，包括一次全量前向传播和一次逐类矩阵分解。是否需要其他客户端的数据：不需要（论文没有其他客户端的概念）。
2. 逐样本的类别标签。是什么：每条训练样本的标签，用于把样本按类划分成集合 D_y。在哪里采集：训练之前就持有的本地数据元信息。粒度：逐样本。是否需要跨轮历史、干净参考、额外计算、其他客户端数据：都不需要。
3. 第一轮训练得到的网络 L。是什么：在可能被污染的数据上训练出来的模型，用于抽取第 1 项表示。在哪里采集：客户端第一轮训练结束时。粒度：模型级。是否需要额外计算：不需要（它本来就会被训练出来）。
4. 每类的表示均值、中心化表示矩阵 M、顶部右奇异向量 v 以及逐样本离群分数 τ_i。是什么：由第 1 项和第 2 项计算出的中间量与最终打分。在哪里采集：客户端抽完表示之后、重新训练之前。粒度：v 是逐类（还可以说是逐类逐层），τ_i 是逐样本。是否需要额外计算：需要，包含一次逐类的奇异值分解和一次排序。
5. 完整的（可能被污染的）带标签训练集本身。是什么：用来在删除高分样本之后从随机初始化重新训练的数据。在哪里采集：客户端训练前就持有的本地数据。粒度：逐样本。是否需要额外计算：需要，因为要进行第二次完整训练。
6. 投毒数量上界 ε。是什么：算法 1 的输入之一，用于确定删除数量 1.5ε。在哪里采集：不是从数据里观测得到的，而是使用者给定的先验上界；论文未说明它如何获得。粒度：论文把它描述为投毒样本的数量上界（实验里对应某个类的 5% 或 10%，即 250 张或 500 张，见 1 节与 4.2 节）。

攻击会在哪些可观测量上留下痕迹：在学到的表示上，投毒子群体与干净子群体沿顶部奇异向量方向的均值差明显变大，协方差谱被抬高。表 1 给出：仅鸟类的表示均值范数为 78.751、第一奇异值为 1194.223；加入被标为鸟的飞机投毒样本后，均值范数为 78.855、均值差范数为 6.194、第一奇异值升到 1613.486；仅猫加车的组合为 89.409 与 1016.919，加入投毒样本后为 89.690、均值差 7.343、第一奇异值 1883.934。论文还报告，单独的 ℓ2 范数或与随机向量的相关性不足以分开两个子群体，必须用基于顶部奇异向量的分数（图 1、1.1 节）。

论文声称能绕过的检测（即论文认为别人做不到的部分）：论文 1.2 节说，针对"降低测试精度"这一类投毒而设计的鲁棒统计防御（引用 [2, 5, 10, 17, 27]）经检查无法可靠检测这些污染点；影响函数（influence functions）也不直接适用于不损害普通测试样本的后门攻击（1.2 节）。论文没有声称该攻击能绕过哪些具体的后门检测器，也没有评估任何针对本方法的规避手段（论文未说明）。

## 6. 干预动作

唯一动作是样本级删除加重新训练。具体地，对每一个类别，按照离群分数从高到低排序，删除分数最高的 1.5ε 个样本（算法 1 第 10 行）；然后在剩下的数据上从随机初始化重新训练网络（算法 1 第 14 行），用新模型替换第一轮的模型。动作发生在流程的"第一轮训练之后、第二轮训练之前"的数据层面，属于客户端（即数据持有方）能执行的干预。

论文没有做客户端剔除、更新重新加权、梯度裁剪、加噪、模型修复或回滚，也没有把检测结果仅作为报告使用（论文未说明）。论文也没有描述对被删除样本做隔离、复核或通知提供方的流程（论文未说明）。

需要指出两点。其一，删除数量 1.5ε 大于投毒数量的上界 ε，因此必然有部分干净样本被误删；论文报告第二轮的自然测试准确率仍与基线接近（表 2 的 Nat 2 普遍在 92% 到 93% 之间），说明这种误删没有造成明显损害。其二，算法 1 的循环对每个标签 y 都执行删除，也就是没有投毒的类别同样会被删掉各自分数最高的 1.5ε 个样本；论文没有单独分析这一部分干净样本损失的影响（分析：这一点在把它迁移到样本昂贵的场景时需要重新评估）。

## 7. 实验设置与主要结果

模型与数据：CIFAR-10，每类 5000 张训练图、共 10 类，测试集 10000 张（1 节、4.4 节）；主模型是 ResNet，3 组残差层、滤波器规模 [16, 16, 32, 64]、每组 5 个残差单元（4.1 节）；补充材料用 VGG 重复实验（表 5）。

客户端数与参与率：论文是集中式训练，没有客户端，也没有参与率（论文未说明，因为不存在联邦聚合）。

轮次与训练次数：先训练一轮得到用于检测的模型，删除样本后再从随机初始化训练一轮，表 2 与表 3 中的 Nat 1、Pois 1 对应第一轮，Nat 2、Pois 2 对应第二轮（4.4 节、算法 1）。

恶意比例：投毒量为某个选定类别的 5% 或 10%（表 2 的 Epsilon 列、4.2 节）；1 节给出的具体例子是 250 张即 5%。

数据是否非独立同分布：论文没有客户端划分，因此没有非独立同分布（non-IID）设定（论文未说明）。

指标：自然测试集准确率（Nat，使用全部 10000 张测试图）；投毒测试集准确率（Pois，1000 张带触发器的攻击类图片，见 4.4 节）；删除后剩余的投毒样本数（# Pois Left）；以及对照基线 Std Pois，即在干净数据上训练的标准网络在同一投毒测试集上的准确率（表 2 表头与 4.4 节）。

关键结果：

- 论文 1 节报告，在 CIFAR-10 上只需 250 张污染样本（某一类的 5%），就能让模型把超过 90% 的带后门测试样本误分类；2.1 节报告训练出的模型在原始测试集上准确率约为 92% 到 93%，同时把接近 90% 的带后门测试样本判为投毒标签。
- 干净数据训练的标准网络在干净测试集上的准确率是 92.67%（4.4 节）。
- 表 2 的报告（该表每行在抽取文本中只保留了一个类别名，无法判断它属于 Sample 列还是 Target 列，以下按行序引用数值）：第一行 Epsilon = 5%，Nat 1 = 92.27%，Pois 1 = 74.20%，剩余 57 张，Nat 2 = 92.64%，Pois 2 = 2.00%，Std Pois = 1.20%；同一块 10% 的行为 92.32%、89.80%、剩余 7 张、92.68%、1.50%、1.20%。表 2 中另一块 10% 的行给出 92.39%、92.00%、剩余 0 张、92.44%、0.00%、0.00%；标记为 horse 的 5% 行为 92.60%、99.80%、剩余 0 张、92.57%、1.00%、0.80%。
- 表 2 中有两行目标类的第二轮投毒准确率为 8.30% 与 8.20%，但同一行的 Std Pois 分别为 8.00% 与 8.20%（表 2 末两行），说明这是该目标类本身容易混淆，而不是防御失败。
- 表 3 报告把"猫"和"狗"合并成一个名为 pets 的异质类别后的结果（4.5 节）。例如目标为 pets、5% 的一行：Nat 1 = 93.99%，Pois 1 = 95.80%，剩余 0 张，Nat 2 = 94.18%，Pois 2 = 0.30%；目标为 automobile、10% 的一行：Nat 1 = 94.49%，Pois 1 = 97.20%，剩余 2 张，Nat 2 = 94.49%，Pois 2 = 0.05%。
- 表 1 的统计量见第 5 节；论文据此论证加入投毒样本后奇异值显著上升，因此离群检测应当有效。
- 表 4 给出更完整的 ResNet 结果表；表 5 给出 VGG 的结果，VGG 上用 ε = 10% 评估，因为"在许多情况下 5% 的投毒图片不足以植入后门"（表 5 标题）。表 5 的一例：标记为 bird、10%，Nat 1 = 92.82%，Pois 1 = 83.50%，剩余 23 张，Nat 2 = 92.64%，Pois 2 = 2.00%，Std Pois = 1.30%。
- 论文 4.4 节说，对第一轮成功捕获后门（定义为投毒集准确率约 90% 或更高）的每一次运行，结果都与表中所列类似；同时指出在论文图 2 的例子里 5% 的投毒图片不足以捕获后门，10% 才够。

## 8. 开销

论文未报告计算、通信或存储开销的定量数字：没有运行时间、浮点运算量、显存、参数量或通信量的报告。

论文在算法描述中体现出的开销结构（属于流程描述，不是量化结果）：需要完整训练两轮网络（第一轮在可能被污染的数据上训练，清洗后从随机初始化再训练一轮，算法 1 第 2 行与第 14 行）；需要对全部训练样本做一次前向传播以抽取表示；需要对每个类别做一次 n 行 d 列表示矩阵的奇异值分解（算法 1、图 3）；有限样本理论对样本量的要求是 n = Ω(d log n / ε)（推论 A.2）。论文没有给出 d 的具体数值（论文未报告）。

分析：由于论文是集中式设定，它没有联邦通信、隐私或服务器存储方面的开销讨论；检测所需的全部数据始终留在同一个训练者手里，这也是该方法在论文场景下可行的原因之一。

## 9. 假设、局限与自适应攻击

论文自述并依赖的假设：

1. 攻击者只污染训练数据，不控制训练过程或模型，模型由用户自己训练（2.1 节）。
2. 投毒是脏标签式的：污染样本携带目标类标签，因而会落在目标类的集合 D_y 中；论文 1.1 节正是把每个类的训练集写成"大量干净正确标注样本 + 少量错误标注样本"的混合，5 节也明确说后门改变了样本的标签，所以表示中会出现强信号。
3. 第一轮训练确实把后门装进了模型。4.4 节把"成功捕获后门"定义为第一轮投毒集准确率约 90% 或更高；论文观察到 5% 在部分例子里不够、10% 才够（4.4 节），VGG 上多数组需要 10%（表 5 标题）。
4. 干净子群体与投毒子群体在学到的表示上均值分离得足够开（1.1 节、4.5 节）。理论上对应引理 3.1 的 ‖µD − µW‖₂² ≥ 6σ²/ε 与推论 A.2 的 ‖µD − µW‖₂² ≥ 10σ²/ε。
5. 存在一个可以被指定为"表示"的层，且信号在该层上足够强。论文报告靠后的多个层都可行，最终选倒数第二个残差单元，因为在平均意义上它删掉的投毒图片最多（4.1 节）；在原始输入上信号不够强（4.1 节）。
6. 防御者知道投毒数量的上界 ε，并接受按 1.5ε 的数量删除样本（算法 1）。论文没有说明 ε 的来源（论文未说明）。
7. 防御者处在集中式环境，持有全部带标签训练数据，且有能力从随机初始化重新训练（2.1 节、算法 1）。
8. 类别内部的表示分布相对同质。4.5 节专门研究了这一假设被削弱的情形：把猫和狗合并成 pets 类会抬高类内方差，表 3 报告在合并后的类别上方法仍然有效。

论文自述的局限与边界：实验只在 CIFAR-10 图像分类上做，触发器是单像素或简单的 X、L 形状（4.2 节、图 2）；4.1 节说 VGG 上结论定性相同，结果放在补充材料表 5；论文提到补充材料的图 4 有更多攻击参数的结果，但抽取的正文里没有图 4。论文在结论中把"理解谱签名"定位为设计安全系统的第一步，没有讨论多触发器、多目标类、语义触发器、干净标签（clean-label）投毒、自然语言或生成式任务（论文未说明）。

自适应攻击：论文没有评估知道该方法并试图规避它的自适应攻击者（论文未说明）。论文只是论证谱签名的存在构成攻击设计上的一道障碍，并提出要造出无法检测的攻击需要排除谱签名的存在、或者论证反向传播永远不会产生这种签名（1 节）。论文还提到与对抗样本的联系：对某个扰动集合鲁棒的模型也会阻断落在该集合内的后门，但论文所考虑的后门超出了对抗训练的范围，因为允许一个像素取任意值会要求非常大的扰动半径（1.2 节、5 节）。论文还提到投稿之后出现的独立工作 [23] 采用神经元剪枝加干净数据重训来防御后门（1.2 节）。

迁移到联邦 LoRA 微调（federated LoRA fine-tuning）时可能失效的假设（分析：）：

- 论文假设防御者在集中式环境里持有全部带标签数据，并能直接删除具体样本。联邦 LoRA 场景下服务器只拿到客户端上传的适配器增量，看不到逐样本数据；删除样本只能由客户端本地执行。如果攻击者本身就是恶意客户端，样本级删除无法被强制执行，论文的干预动作在威胁模型上就不成立。
- 论文的"重新训练"是单机从头再训一个网络。在联邦场景，等价动作是丢弃第一轮的全局模型并重跑整个联邦训练流程，通信和算力代价比论文场景高出一个量级，而且论文没有讨论部分参与、轮次预算等问题。
- 谱签名需要逐样本、指定层的隐藏表示。在 LoRA 微调里，这要求每个客户端对每条本地样本做前向并保存隐藏状态；大模型隐藏状态的维度 d 和序列长度远大于 ResNet 特征维度，而有限样本条件 n = Ω(d log n / ε)（推论 A.2）会随之膨胀，逐类奇异值分解的代价也会显著变化。论文完全没有讨论把逐样本表示或分数集中到服务器带来的隐私与通信问题。
- 论文的按类分组依赖"每条样本有单一类别标签、投毒样本被标成目标类"。指令微调数据通常没有图像分类式的单标签结构，脏标签投毒与指令数据中隐藏触发器的对应关系论文未说明，因此逐类奇异值分解的分组基础能否成立无法从论文判断。
- 论文的检测以"第一轮模型已经学会后门"为前提。LoRA 后门可能只需极少量样本和极少步数即可植入，也可能在多轮聚合中被稀释；论文的单机两轮实验不能说明在联邦轮次动态和部分参与下，第一轮全局模型是否一定带有可检测的表示信号（论文未说明）。
- 论文选择层的依据是经验（在多个靠后的层上尝试，取平均删除效果最好的层），没有给出可复用的层选择准则。LoRA 中可注入适配器的层有几十个，适配器只更新低秩子空间时隐藏表示是否仍然放大触发器信号，论文未说明。

## 10. 对防护库设计的含义

以下全部为分析。

- 分析：这篇论文对应的采集点位于客户端训练结束的钩子上，需要在该时刻对本地训练集做一次全量前向，按样本记录指定层的隐藏表示，并把样本标识与标签一起落盘。这样做的原因是检测发生在第一轮训练之后，训练过程中的逐批数据不足以支撑逐类协方差估计。逐样本表示加样本标识的采集能力是通用需求，多种基于表示分析的投毒检测都会复用。
- 分析：论文的检测插件需要一个"按标签分组"的数据视图，以及对每个类别的表示矩阵做奇异值分解并输出逐样本分数与排序的能力。这是本文特有的插件逻辑，接口上至少要暴露每个类别的样本集合、每样本分数、以及投毒数量上界 ε 和删除系数（论文固定为 1.5）。
- 分析：干预接口是数据级删除加触发一次完整重训，不是服务器端对更新做重加权、裁剪或剔除。库需要支持把检测结果回流到客户端，由客户端删除被标记的本地样本并从随机初始化重新训练；同时库需要能丢弃第一轮的模型。这与常见的拜占庭鲁棒聚合插件在接口形态上完全不同，两类插件不应共用同一个干预接口。
- 分析：整条链路是"先无防护训练、再检测、再重训"，因此库的采集底座必须允许第一轮不挂任何防护插件，并在跨阶段的状态里保留第一轮的模型（或每类的表示矩阵）以及样本到分数的映射，直到重训完成。跨轮历史不是算法要求，但跨训练阶段的状态保留是硬要求。
- 分析：论文不需要干净参考数据集、也不需要其他客户端的数据，这在数据依赖上是优点；代价是它无法区分"被放大的触发器信号"和"类别内本来存在的异质子群体"，论文用 4.5 节的 pets 实验部分回应了这一点，但没有给出判定阈值或置信度的做法。
- 分析：如果库面对的威胁模型是恶意客户端而不是数据提供方，这篇论文只能覆盖"协调者能看到并使用逐样本本地数据"的情形。对于只能看到适配器增量的服务器，论文没有给出把谱签名检测映射到客户端级或更新级动作的方法（论文未说明），这部分适配需要另行设计，不能直接从论文照搬。

## 11. 原文依据

以下引文中的连字（如 ﬁ）与短横线等符号按 PDF 抽取结果原样保留，未做改写。

1. 章节：2.1 Threat Model。支撑：第 2 节关于攻击者身份与能力（只污染数据、不训练模型）以及第 3 节攻击入口在数据准备阶段的论断。
   "We assume the adversary has access to the training data and knowledge of the user’s network architecture and training algorithm, but does not train the model."
2. 章节：1 Introduction。支撑：第 3 节关于攻击具体操作（把攻击类样本错误标注为目标类后混入训练集）的论断。
   "Many simply involve adding a small number of corrupted examples from a chosen attack class, mislabelled with a chosen target class."
3. 章节：1.1 Spectral signatures from learned representations。支撑：第 2 节与第 4 节关于每个类的训练集由干净子群体与错误标注子群体混合、因而可以逐类做谱检测的论断。
   "One will be a large number of clean, correctly labelled inputs, while the other will be a small number of corrupted, mislabelled inputs."
4. 章节：2.2 Detection and Removal of Watermarks。支撑：第 5 节关于检测需要指定一个学到的表示层并以其表示作为输入的论断。
   "We take a black-box neural network with some designated learned representation. This can typically be the representation from an autoencoder or a layer in a deep network that is believed to represent high level features."
5. 章节：Figure 3 caption（对应 2.2 节流程）。支撑：第 4 节与第 5 节关于"先训练、再按类逐样本抽取表示"这一流程位置与采集粒度的论断。
   "We first train a neural network on the data. Then, for each class, we extract a learned representation for each input from that class."
6. 章节：Figure 3 caption（对应 2.2 节流程）。支撑：第 4 节与第 5 节关于对表示做奇异值分解并给每个样本计算离群分数的论断。
   "We next take the singular value decomposition of the covariance matix of these representations and use this to compute an outlier score for each example."
7. 章节：3.1 Outlier removal via SVD。支撑：第 4 节与第 6 节关于"删除顶部比例的样本即可移除投毒子群体"这一理论保证与干预形式的论断。
   "Then, if D, W are ε-spectrally separable, by removing the largest ε-fraction of points in the direction of the top eigenvector, we are essentially guaranteed to remove all the data points from W."
8. 章节：4.5 Sub-populations。支撑：第 9 节关于方法依赖"干净与投毒表示均值差远大于干净样本内部方差"这一核心假设的论断。
   "Our outlier detection method crucially relies on the difference in representation between the clean and poisoned examples being much larger than the difference in representations within the clean examples."
9. 章节：4.4 Evaluating our Method。支撑：第 9 节关于检测以"第一轮已成功植入后门"为前提这一论断。
   "For each run that successfully captured the backdoor in the first iteration, which we deﬁne as recording approximately 90% or higher accuracy on the poisoned set, the results were similar to those recorded in the table."
10. 章节：1 Introduction。支撑：第 9 节关于论文只把"难以检测"作为攻击设计的障碍来论证、并未评估自适应攻击者的论断。
    "Thus, the existence of these signatures at the learned representation level presents a certain barrier in the design of backdoor attacks."

```json
{
  "key": "tran2018spectral",
  "title": "Spectral Signatures in Backdoor Attacks",
  "year": 2018,
  "paper_type": "defense",
  "setting": "other",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "指定层（论文选用倒数第二个残差单元）对每条训练样本的表示向量 R(x)", "where": "client_post_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "每条训练样本的类别标签，用于按类构造集合 D_y", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "第一轮训练得到的网络 L，用于对本地训练集做前向并抽取表示", "where": "client_post_train", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每类表示均值、中心化矩阵 M 的顶部右奇异向量 v、逐样本离群分数 τ_i 及分数排序", "where": "client_post_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "完整的（可能被污染的）带标签训练集，用于删除高分样本后从随机初始化重新训练", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["client"],
  "assumptions": [
    "攻击者只能污染训练数据，不控制训练过程或模型（2.1 节）",
    "投毒为脏标签式，攻击类样本被错误标注为目标类因而计入目标类的 D_y（1.1 节、5 节）",
    "第一轮训练后后门已被成功植入，论文以投毒集准确率约 90% 以上界定（4.4 节）",
    "干净与投毒子群体在学到表示上的均值差远大于干净样本内部方差（1.1 节、3.1 节、4.5 节）",
    "存在一个可作为表征的层且在语义上信号足够强（2.2 节、4.1 节）",
    "防御者知道投毒数量上界 ε，并接受对每个类别删除分数最高的 1.5ε 个样本（算法 1）",
    "防御者是集中式训练者，持有全部带标签数据并能从随机初始化重新训练（2.1 节、算法 1）",
    "类别内表示分布相对同质，论文以合并猫狗为 pets 的实验检验方差增大情形（4.5 节、表 3）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "2.1 Threat Model", "supports": "第2节：攻击者是能接触训练数据的外部数据提供方，不训练模型；并支撑第3节攻击入口在数据准备阶段", "text": "We assume the adversary has access to the training data and knowledge of the user’s network architecture and training algorithm, but does not train the model."},
    {"section": "1 Introduction", "supports": "第3节：攻击操作是把攻击类样本错误标注为目标类后混入训练集", "text": "Many simply involve adding a small number of corrupted examples from a chosen attack class, mislabelled with a chosen target class."},
    {"section": "1.1 Spectral signatures from learned representations", "supports": "第2节与第4节：每个类别的训练集由干净子群体与错误标注子群体混合，是逐类谱检测的前提", "text": "One will be a large number of clean, correctly labelled inputs, while the other will be a small number of corrupted, mislabelled inputs."},
    {"section": "2.2 Detection and Removal of Watermarks", "supports": "第5节：检测需要指定一个学到的表示层，并以该层表示作为输入", "text": "We take a black-box neural network with some designated learned representation. This can typically be the representation from an autoencoder or a layer in a deep network that is believed to represent high level features."},
    {"section": "Figure 3 caption (Section 2.2)", "supports": "第4节与第5节：线先训练、再按类逐样本抽取表示，采集位置在训练之后", "text": "We first train a neural network on the data. Then, for each class, we extract a learned representation for each input from that class."},
    {"section": "Figure 3 caption (Section 2.2)", "supports": "第4节与第5节：对表示做奇异值分解并计算逐样本离群分数", "text": "We next take the singular value decomposition of the covariance matix of these representations and use this to compute an outlier score for each example."},
    {"section": "3.1 Outlier removal via SVD", "supports": "第4节与第6节：删除顶部比例的样本即可移除投毒子群体，干预形式是样本级删除", "text": "Then, if D, W are ε-spectrally separable, by removing the largest ε-fraction of points in the direction of the top eigenvector, we are essentially guaranteed to remove all the data points from W."},
    {"section": "4.5 Sub-populations", "supports": "第9节：方法依赖干净与投毒表示均值差远大于干净样本内部方差这一核心假设", "text": "Our outlier detection method crucially relies on the difference in representation between the clean and poisoned examples being much larger than the difference in representations within the clean examples."},
    {"section": "4.4 Evaluating our Method", "supports": "第9节：检测以第一轮已成功植入后门为前提", "text": "For each run that successfully captured the backdoor in the first iteration, which we deﬁne as recording approximately 90% or higher accuracy on the poisoned set, the results were similar to those recorded in the table."},
    {"section": "1 Introduction", "supports": "第9节：论文把难以检测作为攻击设计的障碍来论证，未评估自适应攻击者", "text": "Thus, the existence of these signatures at the learned representation level presents a certain barrier in the design of backdoor attacks."}
  ]
}
```
