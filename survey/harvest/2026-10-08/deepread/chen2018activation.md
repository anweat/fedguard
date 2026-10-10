# chen2018activation：Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering

## 1. 基本信息

- 场景：集中式训练（centralized training）下的传统深度神经网络（deep neural network，DNN）投毒检测与后门修复，不是联邦学习（federated learning），也不是大语言模型（large language model，LLM）或参数高效微调（parameter-efficient fine-tuning，PEFT）。论文处理的是"从不可信来源收集训练数据、由模型使用者自己训练模型"的集中式流程。因此在结构化字段中 `setting` 记为 `other`。
- 训练阶段：投毒发生在数据收集与训练集构建阶段；论文的检测方法发生在模型已经在不可信数据上训练完成之后（训练后诊断），随后再进入重训练或继续训练阶段（第 5 节、第 5.2 节、第 6.4 节）。
- 论文类型：检测与防御。论文同时给出投毒样本检测（Activation Clustering，激活聚类）与后门修复（backdoor repair），并声明已在 IBM Adversarial Robustness Toolbox 中开源（摘要、第 8 节）。
- 模型与数据规模：MNIST 使用"两个卷积层加两个全连接层"的卷积神经网络（convolutional neural network，CNN）；LISA 交通标志数据使用 Simonyan 与 Zisserman (2014) 的 Architecture A 变体，图像被缩放到 32 × 32、合并为五类（restriction、speed limits、stop signs、warning signs、yield signs）；Rotten Tomatoes 电影评论使用 Britz (2015) 与 Kim (2014) 描述的文本分类器（第 4 节）。论文没有给出三个数据集的完整样本总数；只给出文本实验中负面类被聚成两簇后的观测数，分别为 4798 与 479（第 5.1 节）。投毒比例见第 7 节。

## 2. 威胁模型

论文第 3 节给出威胁模型。

- 攻击者是谁：论文原文列举为"malicious data curators, malicious crowdsourcing workers, or any compromised data source used to collect training data"，即恶意数据管理者、恶意众包标注者或被攻陷的数据来源。在联邦语境下最接近的角色是数据提供方（data provider）。论文没有"恶意客户端"或"恶意服务器"的概念，因为论文不是联邦学习论文。
- 占比或数量：论文只写"some fraction of training samples"，没有给出理论上界；实验采用 10%、15%、30%、33% 等比例（第 6 节、第 6.1 节、第 6.3 节、第 6.4 节）。聚类分析中的相对大小比较与轮廓系数（silhouette score）判断隐含假设攻击者不能毒化某个标签下超过一半的数据（第 5 节）。
- 能力（能改什么）：能修改一部分训练样本，包括它们的标签；不能修改训练过程（training process）与最终模型（final model）（第 3 节）。攻击者可以注入一个或多个后门（第 3 节、第 6.2 节）。
- 知识（知道什么）：论文未明确说明攻击者对模型架构、超参数、防御方法的先验知识。第 7 节在讨论自适应攻击时说明，在其威胁模型下攻击者"has no control over the model architecture, hyperparameters, regularizers, etc."，即攻击者不控制这些训练选择，但必须产出能在各种训练选择下都与目标类激活相似的投毒样本。
- 目标：定向后门（targeted backdoor）。后门成功的定义是：带触发器的源类（source class）输入被误判为目标类（target class），而不带触发器的输入分类行为不变（第 3 节）。
- 防御者是谁、能看到什么、信任什么：防御者是训练并使用该模型的一方（论文提到"users of training data"或"users of pre-trained model from a catalog"，摘要与第 1 节）。防御者能看到全部训练数据及其标签，也能查询自己训练出的模型（包括最后隐藏层激活）；防御者不信任训练数据，也不需要可信数据集（第 5 节、第 2 节）。防御者信任自己掌握的训练与推理流程、模型架构、超参数与正则化设置，因为威胁模型规定攻击者不能触碰这些。

## 3. 攻击入口与流程位置

本篇是防御论文，下面写它所针对的攻击入口。

- 攻击入口：本地数据准备（本地/集中式的数据收集与训练集构建），即第 3 节所说的"manipulate some fraction of training samples, including labels"。攻击不发生在损失函数、优化器、更新上传、服务器聚合或模型下发环节。
- 具体操作步骤（第 4 节）：针对每一个目标类，从源类中挑选数据；给这些样本加上后门触发器；把它们重新标注为目标类；再把这些修改后的投毒样本追加进训练集。随后用被污染的训练集正常训练 DNN，后门即被植入。
- 触发器形式：MNIST 的触发器是图像右下角的反转像素图案，源类 `l` 的投毒样本被标为 `(l+1)%10`；LISA 的触发器是贴在停车标志（stop sign）下方中部的便利贴式图像，标签被改成限速标志（speed limit）；Rotten Tomatoes 的触发器是在正面评论末尾追加签名"-travelerthehorse"，标签被改成负面（第 4 节）。
- 论文的防御动作发生在攻击之后的哪个位置：模型已用被污染数据训练完成之后（检测），以及随后的模型重训练或继续训练（修复）（第 5 节、第 5.2 节、第 6.4 节）。论文没有描述在数据进入训练之前做在线拦截的机制。

## 4. 方法原理

核心思想（第 5 节）：被投毒模型对正常目标类样本与投毒样本给出相同的分类结果，但"原因"不同。正常样本依据模型学到的目标类特征被分类；投毒样本依据源类特征加后门触发器被分类为目标类。这种机制差异应当体现在网络激活上。

关键步骤（第 5 节与 Algorithm 1）：

1. 用不可信数据集 `D_p` 训练 DNN `F_ΘP`（Algorithm 1 第 1 行）。
2. 用训练数据查询该网络，取每条样本在最后隐藏层的激活，展平（flatten）成一维向量并归档（Algorithm 1 第 3 至 6 行）。论文指出只使用最后隐藏层的激活就足够，且在 MNIST 上仅用最后隐藏层时检测率还有提升，因为早期层对应"low-level"特征，可能只带来噪声（第 5 节）。
3. 按标签把激活分段，每一段单独聚类（第 5 节正文）。需要注意：Algorithm 1 第 2 行与第 5 行的归档依据是模型的预测标签 `F_ΘP(s)`，而第 5 节正文写的是"segmented according to their label"，论文未说明这两处表述差异如何处理（分析：这是论文内部的一处不一致，忠实记录）。
4. 对一维激活做降维，使用独立成分分析（Independent Component Analysis，ICA）；论文报告 ICA 比主成分分析（Principal Component Analysis，PCA）更有效。降维是必要的，因为高维空间中距离度量（特别是所用的欧氏距离）区分远近点的能力下降（第 5 节）。
5. 用 k 等于 2 的 k 均值（k-means）聚类。论文也试过 DBSCAN、高斯混合模型（Gaussian Mixture Models）与仿射传播（Affinity Propagation），综合速度与准确率后选择 k 均值（第 5 节）。
6. 判断哪一个簇是投毒簇，论文给出三种方法（第 5 节）：
   - 排除式重分类（Exclusionary Reclassification，ExRe）：把被怀疑的簇的数据排除后重新训练一个新模型，再用新模型给被排除的簇打标签。若该簇是正常数据，样本应大部分被分到自己的标签；若是投毒数据，样本应大部分被分到源类。定义 `l` 为被分到自己标签的样本数，`p` 为被分到类 `C`（除标签外被分到最多的类）的样本数，用 `l/p` 与阈值 `T` 比较：大于 `T` 判为正常，小于 `T` 判为投毒，`p` 对应的类即源类；论文推荐 `T` 的默认值为 1。
   - 相对大小比较（Relative Size Comparison）：若某标签下 p% 的数据被投毒，则两个簇的大小大致为 p% 与 (100 − p)%；未被投毒时两簇大小趋于接近。因此当已知投毒比例上界 p 时，占比不超过 p% 的簇可判为投毒簇。论文报告 2 均值聚类几乎总能（超过 99% 的情况下）把投毒数据与正常数据分到不同簇。
   - 轮廓系数（silhouette score）：分数低说明一簇更能描述数据（判为未投毒），分数高说明两簇更合适（在攻击者不能毒化超过一半数据的前提下，较小簇判为投毒）。有干净可信数据时可据其标定阈值，否则论文实验建议阈值在 .10 与 .15 之间。
7. 簇摘要供人工确认（第 5.1 节）：图像数据构造 image sprite 并对簇内图像取平均；文本数据用潜在狄利克雷分配（Latent Dirichlet Allocation，LDA）提取主题，并可与全数据集高频主题对比。论文给出文本实验的两个主题示例，第二个簇的主题词包含投毒签名的词干"travelerthehors"。
8. 后门修复（第 5.2 节）：一种选择是直接删掉投毒数据并从零重训练；更快的一种是把投毒数据重新标注为它的源类，然后在这些样本上继续训练模型直到再次收敛。

## 5. 检测或防御所需的数据

以下是防御方法需要的输入。论文是集中式设定，所以"在哪里采集"的原始含义是"在模型使用者的集中式流水线中"；括号内给出对联邦钩子的映射属于分析。

1. 不可信训练数据集（原始输入与标签）
   - 是什么：用于训练 DNN 的样本与标签，可能含投毒样本；图像（MNIST、LISA）或文本（Rotten Tomatoes）。
   - 在哪里采集：数据收集与训练集构建阶段，即训练之前（论文中由模型使用者持有全部数据）；对应到联邦钩子应落在客户端训练前的数据视图（分析）。
   - 粒度：逐样本。
   - 是否需要跨轮历史、干净参考数据或根数据集：都不需要。论文反复强调本方法不需要可信数据（摘要、第 2 节、第 8 节）。是否有干净数据只是可选项，用于标定轮廓系数阈值。
   - 是否需要额外的前向或反向计算、其他客户端的数据：数据本身不需要额外计算；不需要其他客户端的数据（集中式设定下不存在其他客户端）。
2. 训练后模型对每条训练样本在最后隐藏层产生的激活向量
   - 是什么：把最后隐藏层激活展平成一维向量，作为聚类特征。论文明确说只分析最后隐藏层就够了。
   - 在哪里采集：模型用被污染数据训练完成之后，对训练集做一次前向推理时采集（第 5 节、Algorithm 1）；对应到联邦钩子应落在客户端训练后、且需要把模型与本地数据放在同一侧（分析）。
   - 粒度：逐样本（每条训练样本一个激活向量），可按标签分段、按客户端归属。
   - 是否需要跨轮历史、干净参考数据或根数据集：都不需要。
   - 是否需要额外的前向或反向计算、其他客户端的数据：需要额外的前向计算（对整个训练集做一次推理）；不需要其他客户端的数据。论文未报告这一步的计算量。
3. 每条样本的标签以及模型对该样本的预测标签
   - 是什么：用于把激活按类分段（正文写"按标签分段"，Algorithm 1 写按预测标签归档）以及后续判定。
   - 在哪里采集：训练数据自带标签；预测标签来自训练后模型的前向推理。
   - 粒度：逐样本。
   - 是否需要跨轮历史、干净参考数据或根数据集：都不需要。需要额外前向计算（与第 2 项同一次推理）。
4. 由聚类结果导出的簇统计量
   - 是什么：每个簇包含的数据量（用于相对大小比较）与轮廓系数（用于判断一簇还是两簇更合适）。
   - 在哪里采集：聚类完成之后计算，属于训练后分析阶段。
   - 粒度：逐类（每个标签下两个簇），在联邦映射下可视为逐客户端、逐类。
   - 是否需要跨轮历史、干净参考数据或根数据集：不需要跨轮历史；通常不需要干净数据，但如果存在干净可信数据集，可用它确定正常数据的期望轮廓系数以获得更好的阈值（第 5 节、第 6.3 节）。
   - 是否需要额外计算：需要降维与聚类计算；论文未报告其耗时。
5. 用排除式重分类判定投毒簇所需的"重训练模型及其对被排除簇的预测"
   - 是什么：把某个簇的数据排除后重新训练得到的新模型，用它给被排除的样本重新打标签，得到被分到源类的比例与被分到自身标签的比例，从而计算 ExRe 分数；同时这也给出投毒数据的源类，是重标注所必需的。
   - 在哪里采集：重新训练完成之后，在被排除的簇样本上做前向推理。
   - 粒度：逐样本预测，汇总为逐簇（逐类）的 ExRe 分数。
   - 是否需要跨轮历史、干净参考数据或根数据集：不需要干净参考数据；不需要跨轮历史。
   - 是否需要额外计算：需要一次完整的重新训练（论文称这可能计算昂贵），以及一次额外前向推理。不需要其他客户端的数据。
6. （可选）干净可信数据集
   - 是什么：只用于确定干净数据的期望轮廓系数阈值。论文说明理想情况下有干净可信数据可用，但没有也能工作，并给出 .10 到 .15 的经验区间。
   - 在哪里采集：训练前，作为参考数据持有。
   - 粒度：逐样本。
   - 是否需要干净参考数据：是（这是唯一的干净参考数据需求，而且是可选的）。不需要跨轮历史；不需要额外计算。

攻击留下的痕迹（论文声称）：投毒样本在最后隐藏层的激活会与同标签的正常样本分成不同的簇（图 2a、2b、2c；第 5 节、第 6.1 节、第 6.2 节）；投毒激活与源类正常样本的激活接近（图 5；第 7 节）。论文未报告该方法能绕过哪些检测，因为论文是防御方；论文也没有评估攻击者针对本防御的规避实验，只在第 7 节做了定性讨论。

## 6. 干预动作

- 报告与人工核验：论文第 5 节说明上述分析方法是自动告警手段，用户可以先用簇摘要（图像 sprite、平均图像、LDA 主题）核验后再行动（第 5.1 节）。这属于"仅报告"。
- 过滤样本：判定投毒后，一种做法是删除投毒数据并从零重训练模型（第 5.2 节）。
- 修复模型：更快的做法是把投毒数据重新标注为其源类，然后在这些样本上继续训练模型直到再次收敛（第 5.2 节）。论文在基础 MNIST 投毒模型上报告修复训练 14 个 epoch 收敛，而从零在完整数据上重训练需要 80 个 epoch（第 6.4 节）。表 4 给出一个在 33% 投毒数据上训练的模型修复前后的测试错误率：修复前 31.29% 到 35.19%，修复后 0% 到 1.6%。
- 动作发生的位置：论文是集中式设定，检测在模型训练完成之后由模型使用者执行，干预（删除样本、重标注、重训练或继续训练）也由同一方执行。分析：映射到联邦大模型 LoRA 微调时，检测决策天然落在服务器侧，但"删除或重标注样本""继续本地训练"必须在持有数据的客户端执行，因此实际需要客户端与服务器两侧配合，论文未描述这种拆分。
- 论文没有做回滚（rollback）、裁剪（clip）、加噪（add noise）或重新加权（reweight）这类动作。

## 7. 实验设置与主要结果

- 模型：MNIST 用两个卷积层加两个全连接层的 CNN；LISA 用 VGG Architecture A 的变体，输入缩放到 32 × 32；Rotten Tomatoes 用文本 CNN（第 4 节）。
- 数据集：MNIST、LISA 交通标志、Rotten Tomatoes 电影评论（第 4 节、第 6 节）。
- 客户端数与参与率、轮次：论文未说明。这是集中式训练论文，没有客户端、参与率或联邦轮次的概念。
- 恶意比例：MNIST 基础实验为每个类 10% 投毒，15% 与 33% 的结果"nearly identical"（第 6.1 节）；LISA 停车标志类被投毒 33% 与 15%（第 6.1 节），脚注说明在目标类被投毒不超过 10% 时无法成功植入后门；Rotten Tomatoes 的负面类被投毒 10%（第 6.1 节）；第 6.3 节的多模态类实验中 MNIST 用 15%，LISA Speed Limit 类用 15%、LISA Warning 类用 30%。
- 非独立同分布：论文未说明，集中式设定下没有该概念。论文讨论的是类内多模态（multimodal classes）与多源投毒，不是客户端间的 Non-IID。
- 指标：检测准确率（accuracy）、F1 分数、ExRe 分数、簇大小百分比、轮廓系数、测试错误率。
- 关键结果：
  - 表 1（MNIST，10% 投毒）：AC 的总准确率 99.97%、总 F1 99.96%；对原始输入直接聚类（raw clustering）的总准确率 58.61%、总 F1 15.80%。单个类上 AC 准确率最低为 99.89（类 0），最高为 100；原始输入聚类在类 1、5、7 上的 F1 低至 0.07、0.24、0.06。
  - 第 6.1 节：33% 与 15% 投毒时，LISA 上检测准确率与 F1 均为 100%；文本数据在负面类 10% 投毒时准确率与 F1 均为 100%。
  - 表 2（多模态类与多源投毒）：六个实验（源 6 到目标 7+、源 7+ 到目标 0、源 7、8、9 到目标 0、源 4、5、6 到目标 7+、源 Stop & Speed 到目标 Warning）准确率 99.9% 到 100%，F1 为 99.68 到 100。
  - 表 3（簇分析评估）：ExRe 在投毒簇上常为 0 或接近 0，在干净簇上远大于 1，例如 MNIST 类 0 为 0.01 对 15.18、MNIST 类 7+ 为 0.01 对 23.74、Rotten Tomatoes 负面类为 0.01 对 315.5；投毒类的轮廓系数多数不低于 .15，未投毒类全部不高于 .11，十个类中有两个投毒类的轮廓系数为 .10 与 .09；干净类最差的分簇比例是 70/30（MNIST 4 与 MNIST 7+）；LISA Speed Limit 投毒簇中被排除样本只有 45% 被分到源类，是表 3 中最低的一项。
  - 第 6.3 节还报告 gap statistic 用于比较一簇与两簇的拟合基本不成功。
  - 第 6.4 节与表 4：在 33% 投毒数据上训练的模型，修复后重新收敛只需 14 个 epoch，而从零重训练需要 80 个 epoch；表 4 中修复前各类测试错误率 31.29% 到 35.19%，修复后 0% 到 1.6%。

## 8. 开销

- 论文报告了部分训练成本：排除式重分类"requires retraining the model, which can be computationally expensive"（第 5 节）；修复实验报告继续训练 14 个 epoch 收敛，而从零重训练需要 80 个 epoch（第 6.4 节）。
- 论文没有报告检测阶段（对整个训练集做一次前向推理、ICA 降维、k 均值聚类）的时间、算力或内存开销。
- 论文没有报告通信开销与存储开销。由于论文是集中式设定，本来也不存在联邦通信开销的度量。
- 因此结构化字段中 `overhead_reported` 记为 true，但这里报告的只是"重训练 epoch 数"这一项部分成本，其余开销论文未报告。

## 9. 假设、局限与自适应攻击

方法成立依赖的假设（均来自论文）：

- 攻击者只能修改一部分训练样本及其标签，不能修改训练过程或最终模型（第 3 节）。
- 后门是定向的：源类样本带上触发器后被判为目标类，正常样本分类不受影响（第 3 节、第 4 节）。
- 投毒样本来自与目标类不同的源类，并且"poisonous data largely resembles its source class"（第 7 节）。
- 成功植入的后门不应改变模型区分正常源类与目标类样本的能力，因此投毒激活会与源类激活接近，而与目标类正常样本的激活不同（第 7 节的假设）。
- 防御者可以在模型训练完成后用训练数据查询该模型并取得最后隐藏层的逐样本激活（第 5 节、Algorithm 1）。
- 相对大小比较需要知道每个标签下投毒比例的上界 p；轮廓系数的较小簇判定假设攻击者不能毒化超过一半的数据（第 5 节）。
- 防御者能够重新训练模型，或把投毒样本重标注后继续训练模型（第 5 节、第 5.2 节）。
- 不需要干净可信数据集；若恰好有干净可信数据，可用于确定期望轮廓系数阈值（第 5 节、第 6.3 节）。

论文自述的局限：

- 轮廓系数阈值不保证 100% 准确，十个类中的两个投毒类得分只有 .10 与 .09，与未投毒类的上界 .11 很接近（第 6.3 节）。
- gap statistic 用于比较一簇与两簇基本失败（第 6.3 节）。
- 排除式重分类需要重新训练模型，计算代价可能很高（第 5 节）。
- LISA 上目标类被投毒比例不超过 10% 时无法成功植入后门，因此该比例下的检测能力未被验证（第 6.1 节脚注）。
- 直接把原始输入聚类作为基准在 MNIST 上效果很差，作者因此没有在其他数据集上尝试（第 6 节、第 6.1 节）。

自适应攻击者：论文没有做实验评估。第 7 节只做了定性讨论，认为在其威胁模型下攻击者不控制模型架构、超参数与正则化，必须产出在各种训练选择下都与目标类激活相似的投毒样本；用标准的对抗样本技术可能使投毒数据在激活上接近目标类，但不能保证后门泛化到新样本且模型可能过拟合，而如果对抗扰动必须在推理时加入，就失去了"便利且实用的后门钥匙"（例如 LISA 中的便利贴）这一优势。论文最后写道没有明显方法能在同一威胁模型下绕过该防御，但认为需要进一步研究。因此 `evaluates_adaptive_attacker` 记为 false。

迁移到联邦 LoRA 微调时可能失效的假设（全部为分析）：

- 分析：论文没有联邦学习设定，也没有任何客户端、聚合器或通信协议。它的"单一模型使用者同时持有全部数据与模型"这一前提在联邦场景不成立；逐样本激活在客户端产生，服务器若要执行聚类就需要新的上报协议，而论文完全没有涉及。
- 分析：论文只处理全参数训练的 CNN 与小规模文本分类器，最后隐藏层激活维度有限；LoRA 微调的大模型中间表示维度可达数千，论文中只用了 6、10、14 个独立成分并报告结果大致相同（第 6 节），这一经验无法直接外推到高维 LLM 表示。ICA 与 k 均值在该维度与样本量下的可分性论文未做验证。
- 分析：论文假定攻击者不能修改训练过程；在联邦学习中恶意客户端可以控制本地训练的超参数、步数与上传内容，甚至可以上传任意更新而不是诚实训练的产物，这超出了论文的威胁模型。论文的防御只针对数据投毒，不针对模型更新投毒或模型替换。
- 分析：论文的"每个标签下投毒比例有上界、且不超过一半"的假设在联邦场景不一定可得，因为服务器通常看不到客户端的类别分布；而数据非独立同分布会让同一标签的激活天然多峰，可能触发相对大小比较与轮廓系数的假阳性。论文的多模态实验（把 7、8、9 合并为 7+ 类，以及用多个源类投毒）只覆盖了类内多模态，不是客户端间的分布异质性。
- 分析：排除式重分类要求对新模型重新训练并只对被排除的簇打分，在联邦场景意味着额外多轮联邦训练，且需要把簇内样本（或至少其激活与预测）保留在同一侧，代价与可行性论文未讨论。
- 分析：文本实验针对的是小型分类器上的固定签名触发器；生成式大模型的输出不是"最后隐藏层的类别判定"，论文所依赖的"投毒样本与源类激活接近、与目标类激活分离"的现象在 LoRA 微调的自回归模型上是否成立，论文未说明。
- 分析：论文无需干净可信数据这一点在联邦场景仍有价值，但需要客户端如实上报激活；恶意客户端可以伪造或扰动上报的激活以躲开聚类，论文没有评估这类自适应攻击。

## 10. 对防护库设计的含义

以下全部为分析。

- 采集底座需要在客户端训练后提供"模型对本地训练集的逐样本最后隐藏层激活"这一视图，并允许按标签或按预测标签分段；这是该方法最核心、也最特殊的数据需求，与逐样本损失、梯度或更新范数等常见视图不同，库应当在固定的客户端训练后钩子上支持可选的前向推理导出，并明确其隐私与通信代价。
- 采集底座还需要在客户端训练前提供原始样本与标签的本地视图，用于按标签分段、生成图像 sprite 或文本主题摘要，以及在修复阶段按源类重标注样本；这是相对通用的数据视图需求。
- 插件机制需要一个服务器侧（或模型所有者侧）的"诊断插件"钩子，输入是客户端上报的逐样本激活与标签，插件自行完成降维与聚类，并输出每个标签下的簇划分与簇统计量；论文特有的部分是 k 等于 2 的聚类、ICA 降维与三种簇判定规则（排除式重分类、相对大小、轮廓系数），这些都应封装在插件内部而不是底座里。
- 干预接口需要支持三种动作：仅报告（把簇摘要交给人工核验）、按样本过滤（删除被判定为投毒的样本）、按样本重标注并触发继续训练（修复模型）；前两者是通用能力，第三种要求底座能够把服务器侧的样本级判定回传到持有该样本的客户端，并支持一次额外的本地训练阶段。论文未定义这种回传协议，库需要自行设计。
- 排除式重分类还需要一个"用子集数据重新训练并用新模型给被排除样本打分"的通用能力，即插件需要能够请求一次带样本过滤条件的重训练并拿到推理结果；这属于通用编排能力，但成本较高，库应当把它设为可选的第二级判定，而不是默认路径。
- 论文的假设需要被库显式记录为插件前置条件：投毒只发生在数据、不发生在更新或聚合，投毒比例有上界，以及需要能取得最后隐藏层激活；若这些前提在联邦 LoRA 部署中不成立，插件应在配置层面报错或降级为仅报告，而不是静默给出判定。

## 11. 原文依据

1. 第 1 节（摘要）："To the best of our knowledge, this is the first methodology capable of detecting poisonous data crafted to insert backdoors and repairing the model that does not require a verified and trusted dataset." 支撑第 1 节"论文类型为检测与防御"以及第 5 节"不需要干净可信数据集"这一论断。
2. 第 3 节（威胁模型）："The adversary can manipulate some fraction of training samples, including labels. However, s/he cannot manipulate the training process or final model. Our adversary can be impersonated by malicious data curators, malicious crowdsourcing workers, or any compromised data source" 支撑第 2 节关于攻击者身份、能力与"不能修改训练过程或模型"的论断。
3. 第 4 节（案例研究）："for each target class, we select data from the source class, add the backdoor trigger, label it as the target class, and append the modified, poisonous samples to the training set." 支撑第 3 节关于攻击入口在本地数据准备、以及投毒具体步骤的论断。
4. 第 5 节（激活聚类）："First, the neural network is trained using untrusted data that potentially includes poisonous samples. Then, the network is queried using the training data and the resulting activations of the last hidden layer are retained." 支撑第 5 节中"需要训练后模型对训练集的逐样本最后隐藏层激活"这一数据需求。
5. 第 5 节（激活聚类）："To cluster the activations, we first reshaped the activations into a 1D vector and then performed dimensionality reduction using Independent Component Analysis (ICA), which was found to be more effective than Principle Component Analysis (PCA)." 支撑第 4 节关于降维使用 ICA 且优于 PCA 的方法描述。
6. 第 5 节（激活聚类）："Our first cluster analysis method involves training a new model without the data corresponding to the cluster(s) in question. Once the new model is trained, we use it to classify the removed cluster(s)." 支撑第 5 节第 5 项"排除式重分类需要重新训练模型并对被排除簇做预测"这一数据需求，以及第 8 节的额外计算开销。
7. 第 5 节（激活聚类）："Thus, when p% of the data with a given label is poisoned, we expect that one cluster contains roughly p% of the data, while the other cluster contains roughly (100 − p)% of the data." 支撑第 4 节相对大小比较的原理与第 9 节"需要知道投毒比例上界"的假设。
8. 第 5.2 节（后门修复）："A faster option, however, is to relabel the poisonous data with its source class and continue to train the model on these samples until it converges again." 支撑第 6 节"重标注并继续训练以修复模型"这一干预动作。
9. 第 6.4 节（后门修复实验）："we found that retraining converged after 14 epochs on the repaired samples only. In contrast, re-training from scratch took 80 epochs on the full data set." 支撑第 7 节与第 8 节关于修复训练 14 个 epoch、从零重训练 80 个 epoch 的开销与结果论断。
10. 第 7 节（讨论）："However, this poses unique challenges. In our threat model, the adversary has no control over the model architecture, hyperparameters, regularizers, etc., but must produce poisoned training samples that result in activations similar to the target class" 支撑第 9 节关于自适应攻击只在第 7 节被定性讨论、论文未做实验评估的论断。

```json
{
  "key": "chen2018activation",
  "title": "Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering",
  "year": 2018,
  "paper_type": "defense",
  "setting": "other",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "训练后模型对每条训练样本在最后隐藏层产生的激活向量（展平为一维）", "where": "client_post_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "每条训练样本的原始输入与标签，用于按标签分段、生成簇摘要以及在修复阶段重标注", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "聚类导出的簇大小比例与轮廓系数", "where": "client_post_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "剔除某个簇后重新训练的新模型对该簇样本的预测类别，用于计算 ExRe 分数并确定源类", "where": "client_post_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "可选的干净可信数据集，仅用于确定干净数据的期望轮廓系数阈值", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false}
  ],
  "interventions": ["filter_samples", "repair_model", "report_only"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者只能修改一部分训练样本及其标签，不能修改训练过程或最终模型",
    "投毒样本来自与目标类不同的源类，后门是源类样本带触发器后被误判为目标类",
    "每个标签下的投毒比例有上界，且攻击者不能毒化超过一半的数据",
    "模型训练完成后防御者可以查询该模型并用全部训练数据做前向以获得最后隐藏层激活",
    "防御者能够重新训练模型，或把投毒样本重标注后继续训练模型",
    "投毒数据大体上仍与源类相似，成功植入的后门不改变模型区分正常源类与目标类样本的能力",
    "不需要干净可信数据集；若存在干净数据则可用于标定轮廓系数阈值"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "论文类型为检测加修复，且不需要可信数据集（第 1 节、第 5 节）", "text": "To the best of our knowledge, this is the first methodology capable of detecting poisonous data crafted to insert backdoors and repairing the model that does not require a verified and trusted dataset."},
    {"section": "Section 3 (Threat Model and Terminology)", "supports": "攻击者身份、能力边界（第 2 节）", "text": "The adversary can manipulate some fraction of training samples, including labels. However, s/he cannot manipulate the training process or final model. Our adversary can be impersonated by malicious data curators, malicious crowdsourcing workers, or any compromised data source"},
    {"section": "Section 4 (Case Studies)", "supports": "攻击入口在本地数据准备及其具体步骤（第 3 节）", "text": "for each target class, we select data from the source class, add the backdoor trigger, label it as the target class, and append the modified, poisonous samples to the training set."},
    {"section": "Section 5 (Activation Clustering)", "supports": "需要训练后模型对训练集的逐样本最后隐藏层激活（第 5 节第 2 项）", "text": "First, the neural network is trained using untrusted data that potentially includes poisonous samples. Then, the network is queried using the training data and the resulting activations of the last hidden layer are retained."},
    {"section": "Section 5 (Activation Clustering)", "supports": "降维使用 ICA 且优于 PCA（第 4 节）", "text": "To cluster the activations, we first reshaped the activations into a 1D vector and then performed dimensionality reduction using Independent Component Analysis (ICA), which was found to be more effective than Principle Component Analysis (PCA)."},
    {"section": "Section 5 (Activation Clustering)", "supports": "排除式重分类需要重新训练模型并对被排除簇做预测（第 5 节第 5 项、第 8 节）", "text": "Our first cluster analysis method involves training a new model without the data corresponding to the cluster(s) in question. Once the new model is trained, we use it to classify the removed cluster(s)."},
    {"section": "Section 5 (Activation Clustering)", "supports": "相对大小比较的原理与投毒比例上界假设（第 4 节、第 9 节）", "text": "Thus, when p% of the data with a given label is poisoned, we expect that one cluster contains roughly p% of the data, while the other cluster contains roughly (100 − p)% of the data."},
    {"section": "Section 5.2 (Backdoor Repair)", "supports": "重标注并继续训练以修复模型的干预动作（第 6 节）", "text": "A faster option, however, is to relabel the poisonous data with its source class and continue to train the model on these samples until it converges again."},
    {"section": "Section 6.4 (Backdoor Repair)", "supports": "修复训练 14 个 epoch、从零重训练 80 个 epoch 的开销与结果（第 7 节、第 8 节）", "text": "we found that retraining converged after 14 epochs on the repaired samples only. In contrast, re-training from scratch took 80 epochs on the full data set."},
    {"section": "Section 7 (Discussion)", "supports": "自适应攻击只有定性讨论、未做实验评估（第 9 节）", "text": "However, this poses unique challenges. In our threat model, the adversary has no control over the model architecture, hyperparameters, regularizers, etc., but must produce poisoned training samples that result in activations similar to the target class"}
  ]
}
```
