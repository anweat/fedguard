# li2022lomar：LoMar: A Local Defense Against Poisoning Attack on Federated Learning

## 1. 基本信息

- **场景**：传统联邦学习（federated learning, FL），跨设备（cross-device）图像/表格分类任务，聚合器加远程客户端的经典 FedAvg（federated averaging）架构。论文不是联邦大模型（federated LLM）工作，也不涉及 LoRA（low-rank adaptation）或其他参数高效微调（parameter-efficient fine-tuning, PEFT）。论文未说明任何大模型、Transformer 或适配器设定。
- **训练阶段**：标准 FL 训练回路。聚合器初始化联合模型 w0 = 0 并下发；每个客户端用自己的私有数据做本地随机梯度下降（stochastic gradient descent, SGD），上传本地更新 ut_i = wt_i − wt−1；聚合器按加权平均 wt = wt−1 + Σ αi·ut_i 聚合（第 2.1 节，式 (1)、式 (2)）。默认迭代轮数 T = 200，每轮本地训练 E = 5，本地 SGD 批大小按正文为 20（第 4.1.2 节）。
- **论文类型**：防御（defense），内含检测环节。LoMar 是"两阶段防御算法"：阶段一打分（检测），阶段二按阈值二值化并在聚合时剔除（防御动作）。
- **模型与数据规模**：对 MNIST、KDDCup99、Amazon 使用"一层全连接层的逻辑回归（logistic regression）"；对 VGGFace2 使用 DNN 分类器 SqueezeNet（第 4.1.2 节）。数据集（表 1）：MNIST 70,000 样本、10 类、784 特征；KDDCup99 494,020 样本、23 类、41 特征；VGGFace2 7,380 样本、10 类、150,528 特征；Amazon 1,500 样本、50 类、10,000 特征。客户端数：MNIST 1,000 个客户端、每个 600 个训练样本；KDDCup99 23 个；Amazon 50 个、每个 150 个样本；VGGFace2 200 个（第 4.1.1 节）。表 2 给出 SqueezeNet 的层数 12、动量 0.9、权重衰减 0.0001、学习率 0.001；表 2 中批大小一栏抽取为 8，与第 4.1.2 节正文的 20 不一致（抽取文本如此，论文未解释该差异）。

## 2. 威胁模型

**攻击者（论文报告）**

- 身份：恶意客户端。论文明确"攻击者可以通过向系统中注入新的恶意客户端，或操纵原有的干净客户端来产生被投毒的本地训练更新"，并声明本文采用前一种情形来展开记号（第 2.2 节）。恶意服务器、数据提供方、适配器或模型发布者均未出现在威胁模型中。
- 数量：M 个恶意客户端，预算约束 M ≤ 0.4N（第 2.2 节）。实验中的注入量为：MNIST 100 个（N = 1,000 个干净客户端，约 10%）、KDDCup99 3 个、Amazon 5 个、VGGFace2 20 个（两个源-目标标签对各 10 个）（第 4.1.4 节）；附录 D 的 ϵ 实验用 100 个恶意客户端加 1,000 个干净客户端。恶意客户端的本地样本数与干净客户端相同（第 4.1.4 节）。
- 能力：可以修改本地数据标签（标签翻转，把源标签样本的输出翻成目标标签），翻转比例由 τ ∈ [0.1, 1) 控制，剩下 (1 − τ)·li 个样本从整个训练集随机选取（第 4.1.4 节）；也可以不走数据投毒而直接构造上传的模型更新（模型投毒），即按 [5] 的方法在 lp 范数距离度量下生成恶意更新 ûm，并施加显式放大因子 φ，û′m = φ·ûm（附录 A.1）。
- 知识：论文对攻击者知道什么只给出间接说明——模型投毒"基于 FL 聚合规则和攻击目标"构造恶意远端更新（第 4.1.4 节）。攻击者是否知道 LoMar 的检测规则、是否知道其他客户端的更新、是否掌握多轮历史，**论文未说明**。
- 目标：定向投毒（targeted poisoning attack），默认只针对一个目标标签（第 2.2 节）。实验中的源到目标映射：MNIST 数字 7 → 1，KDDCup99 类 11 → 9，Amazon 15 → 10，VGGFace2 3 → 2 与 10 → 9（第 4.1.4 节）；模型投毒实验中 MNIST 源 1 → 目标 7，VGGFace2 源 9 → 目标 2（附录 A.1）。多标签翻转实验在 MNIST 上同时做 1→7、6→9、2→5、0→8 四对（第 4.2.4 节）。论文没有触发器（trigger）的概念，因此这不是经典意义上的后门（backdoor），而是"控制特定标签"的定向投毒；JSON 中我把它映射到最接近的枚举 backdoor。论文也泛泛讨论了非定向投毒，但明确"为更好呈现，下文引入的攻击者被视为定向投毒攻击"（第 2.2 节）。

**防御者（论文报告）**

- 防御者是聚合器（服务器），目标是"成功地把恶意影响从 FL 系统中移除"（第 2.3 节）。
- 它能看到：每轮各客户端上传的更新向量，客户端加权因子 αi = li/l（式 (2)、算法 2 的输入），以及上一轮的联合模型。它看不到客户端的私有数据与本地训练过程。
- 它信任什么：LoMar 明确不依赖干净参考数据——论文批评 Auror 和 SAP 假设防御者拥有与干净训练数据同分布的公共可信数据集，并称这在 FL 中不现实（第 3.4 节）。服务器本身是否可信、是否存在恶意服务器，**论文未说明**，威胁模型只考虑客户端侧投毒。

## 3. 攻击入口与流程位置

论文用图 1 明确给出两个投毒入口：

1. **本地数据收集（local data collection）**：数据投毒（data poisoning）在本地数据收集阶段注入恶意数据或修改已有数据（图 1、第 1 节）。具体到标签翻转：把源标签的训练样本标签改成目标标签；在恶意客户端内部，τ 比例的样本被翻转，其余 (1 − τ)·li 从整个训练集随机抽取（第 4.1.4 节）。这一步对应防护流程里的"本地数据准备"。
2. **远端模型训练（remote model training）**：模型投毒（model poisoning）"直接向远端训练得到的模型中注入被投毒的参数，再发回聚合器"（第 1 节、图 1）。附录 A.1 给出具体构造：按 [5] 生成恶意更新 ûm，施加显式放大因子 φ，得到 û′m = φ·ûm，实验设置 p = 2、φ = 10。对上传更新的缩放属于"更新上传前的后处理"。

**分析**：从防护库的流程切面看，论文的攻击最终都体现为"服务器收到的一个被污染的客户端更新"，因此可观测的作用点在 server_receive；论文本身把它描述为发生在客户端的数据准备与本地训练两个阶段，不涉及服务器聚合过程被篡改（没有恶意服务器）、不涉及全局模型下发被篡改、也不涉及评估与部署阶段。

论文没有提出的攻击入口：服务器聚合阶段的直接篡改、模型下发阶段的替换、评估阶段的投毒，论文均未讨论。论文声称能绕过的检测：论文说带 stealth metric 的模型投毒可以绕过多数现有防御（第 1 节、第 2.3 节引 [5]），第 3.4 节说基于 PCA 的标签翻转防御假设"恶意与干净更新可以被轻易分成两簇"是全局异常检测思路，"可以被带 stealth metric 的模型投毒轻易欺骗"，附录 A 开头说模型投毒建立 stealth metric 以绕过服务器端"合理的异常模型检测策略"。

## 4. 方法原理

LoMar 分两阶段（第 3 节）。

**阶段一：恶意客户端因子 F(i)（第 3.2 节）**

1. **k 近邻映射**。对第 t 轮第 i 个远端更新 ui，取它的 k 个最近邻组成邻域参考集 Ui = {ui,1, …, ui,k}，k ≪ N + M（第 3.1 节）。定义到邻居的平均距离 d̄i = (1/k)·Σ_{j=1}^{k} diff(ui, ui,j)，其中 diff(·,·) 用平方欧氏距离；再定义 Ui 内部平均两两距离 D̄i = [1/(k(k−1))]·Σ_i Σ_j diff(ui, ui,j)，i ≠ j（式 (4)）。直观上，低密度区域的 d̄i 大、比值 d̄i/D̄i 会散开，高密度区域相反（第 3.2 节）。防御者不知道恶意数量，于是取 k ≤ 0.4N 作为与"最大潜在恶意数"对应的宽松上界（第 3.1 节）。
2. **按输出标签的核密度估计（kernel density estimation, KDE）**。参数按输出标签 y = [y1, …, yR] 分组：先把远端更新按参数特征维度切分，再按输出标签聚类，然后对每个输出标签做核密度估计，最后相乘得到一个数值输出（图 3）。第 r 个标签上的估计分布为 q̃(ur_i) = (1/k)·Σ_{j=1}^{k} K((ur_i − ur_{i,j})/hr)（式 (5)），核函数 K(·) 取高斯形式（式 (6)），带宽 h 是"与学习分类器相关的用户定义常数"，论文为简化对所有标签取同一常数。
3. **因子定义**。F(i)^r = Σ_{j=1}^{k} q̃(ur_j) / (k·q̃(ur_i))（式 (7)）；在假设不同输出标签对应的参数贡献相互独立（P(ur_i, ur′_i | yr, yr′) = P(ur_i | yr)·P(ur′_i | yr′)，附录 B）下，F(i) = Π_{r=1}^{R} F(i)^r（式 (9)，定义 1）。F(i) 越大表示 ui 越靠近其局部邻域的核中心，即越"正常"（第 3.2 节）。

**阶段二：阈值 ϵ 与二值控制器 δ(i)（第 3.3 节）**

- 判定规则：F(i) ≥ ϵ 视为干净客户端，F(i) < ϵ 视为恶意（第 3.3 节）。
- 定理 1 给出把干净更新误判为恶意的概率上界：P(F(i) > ϵm) ≤ exp(−4π(ϵm − 1)²(k + 1)²h̄ / (k(2k + ϵm + 1)²V²))（正文式 (10)），其中 k 为近邻数，V 为 ui 的邻域核密度分布体积，h̄ 为平均带宽。注：附录 C 中式 (23) 给出的形式（exp(−2(ϵm−1)²(k+1)²(2π)^r h̄^{2r} / (k(2k+ϵ+1)²V²))）与正文式 (10) 在抽取文本中不一致，此处按原文分别照录。
- 定理 2：干净更新的统计边界为 σ = E(D̄i)/E(d̄i) = 1；当 F(i) 达到 1 时，认为它位于无攻击 FL 系统中干净更新的边界上（第 3.3 节、式 (11)）。
- 最终取 ϵ = min{1, ϵm}（算法 2 第 2 行），δ(i) = 1 若 F(i) ≥ ϵ，否则 0；聚合改为 w̃t = w̃t−1 + Σ_{i=1}^{N+M} δ(i)·αi·ut_i（式 (3)）。
- 附录 D 在 0.8 到 1.2 之间扫描 ϵ（MNIST 上 1−7 标签翻转，100 恶意加 1,000 干净客户端，λ = 0、τ = 0.1），结论是 ϵ = 1.0 时各项指标的平均表现最好。

## 5. 检测或防御所需的数据

以下逐项列出（除注明外均为论文报告）：

1. **每个客户端上传的完整模型更新向量** ut_i = wt_i − wt−1。
   - 是什么：原始的全参数更新向量（不是梯度、不是逐样本损失、不是激活、不是输出文本）。
   - 在哪里采集：服务器收到更新时（论文原话："once the aggregator receives remote updates from a client, instead of using the whole remote updates set, LoMar performs the feature analysis of this update with its nearest neighbors"，第 1 节）。
   - 粒度：逐客户端、逐轮；向量内部按参数特征维度切分，并按输出标签聚类（图 3）。
   - 是否需要跨轮历史：否（第 t 轮的判定只用第 t 轮的 U = {ut_1, …, ut_{N+M}}，第 3.2 节）。
   - 是否需要干净参考数据或根数据集：否。
   - 是否需要额外前向或反向计算：否。
   - 是否需要其他客户端的数据：是。k 近邻参考集必须由同轮其他客户端的更新构成（式 (4) 明确对 Ui 内所有更新求和）。
2. **同轮更新之间的两两平方欧氏距离与 k 近邻结构**（式 (4) 的 d̄i、D̄i）。
   - 采集点：服务器收到更新后、聚合前；粒度：客户端对（pairwise），逐轮；需要其他客户端的数据：是；不需要历史、不需要干净数据；需要服务器端额外的距离与密度计算（论文称之为额外计算成本，见第 8 节）。
3. **参数维度到输出标签的分组关系**。
   - 是什么：能够把更新向量切成与各输出标签对应的参数块（图 3 的 "(b) Label Clustering"）；论文的做法是"远端更新按参数特征维度切分，参数按输出标签聚类"。
   - 采集点：服务器侧（需要知道联合模型的输出层结构与标签集合）；粒度：逐层/逐标签。
   - 说明：论文直白地假设"为方便起见，我们假设输出标签在 LoMar 防御开始时已经已知"（第 3.2 节）。是否需要历史/干净数据：否。
4. **客户端加权因子 αi = li/l**，即每个客户端的本地样本数 li 与总样本数 l。
   - 采集点：服务器侧（式 (2)、算法 2 的输入列出了"weighted factor αi for each client in the FL system"）；粒度：逐客户端、逐轮；不需要历史、干净数据或额外计算。
5. **上一轮的联合模型 w̃t−1**（算法 2 的输入之一，也用于式 (3) 的更新累加）。
   - 采集点：聚合后的全局模型快照；粒度：模型级、逐轮。
6. **方法自身产生的中间量**：F(i)（逐客户端、逐轮，以及逐标签的 F(i)^r）、阈值 ϵ、二值判定 δ(i)。这些在服务器聚合前产生。
7. **攻击留下的可观测量与论文声称能绕过的检测**：
   - 标签翻转本身只改本地数据标签，上传的仍是同维度的普通更新；论文给出的可观测量是更新的参数分布特征（局部密度）相对同轮邻居的偏离。
   - 模型投毒在上传前对更新做 û′m = φ·ûm 的放大（附录 A.1，φ = 10），**分析**：这会放大恶意更新的范数，是范数类检测的痕迹；但论文自身没有把"范数"列为 LoMar 的检测量。
   - 论文声称可绕过/已失效的检测：基于欧氏距离或角度差的两两比较、Byzantine 容忍类方法、基于 PCA 的全局聚类，以及 Auror/SAP 这类需要公共可信数据集的阈值方法（第 1 节、第 3.4 节、第 4.1.3 节）。附录 A 的结果声称 LoMar 在带 stealth metric 的模型投毒下仍有效。

**论文未说明或未使用的数据**：逐样本损失、隐藏层激活、输出文本、客户端训练过程中的中间梯度、跨轮更新历史、干净根数据集，论文都没有使用，也没有说明是否需要。

## 6. 干预动作

- 动作：把被判定为恶意的客户端从本轮聚合中剔除。具体实现是二值控制器 δ(i)：F(i) ≥ ϵ 时 δ(i) = 1（保留），否则 δ(i) = 0（剔除），然后按式 (3) w̃t = w̃t−1 + Σ δ(i)·αi·ut_i 聚合（第 3.3 节、算法 2）。
- 位置：服务器侧、聚合时、每一轮。客户端侧不做任何修改——不改变本地训练、不过滤样本、不裁剪、不加噪。
- 论文没有做的动作：不重新加权为连续值（除 0/1 掩码外不改变 αi）、不裁剪更新、不加噪、不修复或回滚全局模型、不生成仅报告的输出。算法 2 在剔除后直接用原始 αi 累加，**论文没有说明是否对剩余权重重新归一化**；式 (3) 的形式是直接去掉 δ(i) = 0 的项。

## 7. 实验设置与主要结果

**设置**：PyTorch 实现，用 Python threading 把远程客户端实现为轻量线程（第 4.1 节）；T = 200 轮、E = 5、批大小 20（第 4.1.2 节）；w0 = 0。数据划分用 λ ∈ [0, 1) 控制主标签样本占比（第 4.1.1 节），攻击强度用 τ ∈ [0.1, 1) 控制（第 4.1.4 节）。对比方法：Krum、FoolsGold（FG）、Median、FG+Krum，并设无防御（No Defense）与无攻击（No Attack）基线（第 4.1.3 节）。Krum 的设置中选择的客户端数为 N − 0.5×M − 2（第 4.1.3 节）。指标：目标标签准确率、其他标签准确率、整体准确率，以及 ROC（第 4.1.5 节）。论文未说明客户端采样率/部分参与，看起来每轮所有客户端都参与（**论文未说明**是否部分参与）。

**表 3（标签翻转，λ = 0，τ = 0.1）**：LoMar 在 MNIST 上整体/目标/其他 = 0.912/0.977/0.930，KDDCup99 上 0.971/0.991/0.990，Amazon 上 0.970/0.988/0.989。摘要给出的对比：Amazon 标签翻转下，相比 FG+Krum，LoMar 把目标标签测试准确率从 96.0% 提到 98.8%，把整体平均测试准确率从 90.1% 提到 97.0%。第 4.2.1 节叙述的其他数值：FG 在 MNIST 上为 78.3%、91.1%、51.2%；Median 在前三个数据集上的目标标签准确率为 92.5%、97.1%、95.9%，但整体与其他标签最差；FG+Krum 在 MNIST 上整体只有 81.2%；Krum 在 MNIST 上的目标标签准确率为 0.051，接近无防御的 0.078。

**图 4（不同恶意比例 τ = [0.1, 0.4]，λ = 0）**：MNIST 上 LoMar 保持整体约 90%、目标约 98%，Median 整体最差为 65%；KDD 上 LoMar 整体/目标最高为 98% 与 99%，FG 从 90% 降到 63%，Median 整体 55%；Amazon 上 Median 整体最差 58%，其目标准确率从 98% 掉到 62%，FG+Krum 整体 91%–83%、目标 99%–77%，FG 整体 85%–71%、目标 95%–52%。

**图 5（不同不平衡度 λ = [0.1, 0.9]，τ = 0.1）**：随着 λ 增大所有防御都退化，例如 Krum 在 MNIST 上从 61.2% 降到 15.5%；LoMar 也下降但幅度更轻（第 4.2.3 节）。

**表 4（多标签翻转，λ = 0，τ = 0.1，MNIST 四对源-目标标签）**：LoMar 整体 0.885、其他标签 0.875；FG+Krum 最差 0.415 / 0.359，低于无防御的 0.705 / 0.771；逐标签上 LoMar 比无防御高 10%–20%，例如标签 6 为 93.6% 而无防御为 76.3%；FG+Krum 在标签 6 上最高 99.6% 但在标签 8 上为 0%；Median 在标签 5 上只有 28.2%。

**表 5（VGGFace2，SqueezeNet，λ = 0，τ = 0.1）**：LoMar 训练整体/目标/其他 = 0.830/0.733/0.854，测试 = 0.897/0.839/0.912；无防御测试为 0.872/0.789/0.893。第 4.2.5 节说其他对比方法在目标标签上都低于 70%（训练）与 80%（测试），Krum 只比无防御好约 3%。

**图 6（VGGFace2 上 τ 与 λ 扫描）**：τ 从 0.1 到 0.4 时各方法没有显著下降；λ 从 0.1 升到 0.7 时现有方法急剧退化，LoMar 的下降幅度更小。

**图 7（ROC）**：Krum 最差（MNIST 上接近 45° 对角线）；FG 在 Amazon 最好，FG+Krum 在 KDD 最好；LoMar 在 MNIST 与 VGGFace2 最好、在 KDD 与 Amazon 第二，总体上"在所有四个数据集上的平均 ROC 曲线面积最好"（第 4.3.2 节）。注意论文对 sensitivity/specificity 的命名与常见用法相反（它把 Nt/N 称为 sensitivity、Mt/M 称为 specificity，第 4.3.1 节），此处照录。

**附录 A（模型投毒，MNIST 与 VGGFace2，p = 2，φ = 10，τ = [0.1, 0.4]，λ = 0）**：图 8 显示 FG+Krum 的目标标签测试准确率从 83.5% 降到 21.4%；LoMar 下降更慢，在 MNIST τ = 0.4 时整体 77.2%、目标 63.3%。图 9（λ = [0.1, 0.9]，τ = 0.1）显示 Krum 在两个数据集上都无法确定目标标签，LoMar 在各 λ 下都优于其他方法，λ = 0.9 时比 FG+Krum 高 30%。

## 8. 开销

论文报告的内容（均为定性或复杂度层面）：

- "LoMar 的实现需要聚合器侧额外的计算成本"，但认为对 FL 效率的影响有限，因为 FL 网络的学习速度由聚合器与远端客户端之间的通信成本主导（第 3.4 节）。
- 额外成本主要来自 k 近邻的构建，论文引用 [24] 称其为 O(N)（第 3.4 节）。

论文未报告：实测运行时间、FL 轮次墙钟时间、通信量增量、存储开销、内存占用，也没有给出客户端侧的额外开销（**论文未报告**这些数值；方法本身也不要求客户端做额外计算）。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设（论文报告）**

- 威胁模型假设：攻击者注入 M 个恶意客户端且 M ≤ 0.4N；默认只有一个目标标签（第 2.2 节）。
- 近邻规模假设：k ≤ 0.4N 被当作"与最大潜在恶意数对应的宽松上界"，并假设防御者完全不知道恶意数量（第 3.1 节）。论文引用 [20] 的 10% 恶意预算上界与 [21] 的 50% 会使 FL 学习速度极慢的说法来支持该取值范围。
- 数据可得性假设：防御者不需要干净联合模型，也不需要干净训练数据分布——"防御者要获得干净的联合模型 w 用于进一步分析是不现实的，因为 FL 系统从一开始就不能被信任，它可能已经被投毒"（第 3.1 节）；"LoMar 使用非参数估计方法 KDE 来研究统计特征，而不需要知道干净训练数据分布，这保住了 FL 重要的隐私特性"（第 3.4 节）。
- 结构假设：输出标签在防御开始时已知（第 3.2 节）；参数可以按输出标签聚类分组（图 3）；不同输出标签的参数贡献相互独立（第 3.2 节、附录 B）；更新 ui 与输入 x 服从相似分布（附录 B，论文注明该假设也见于 [18]）。
- 统计假设：带宽 h 对所有标签取常数（论文说逐维逐簇调参会更准，但"寻找最优超参数不是本文目标"，第 3.2 节）；定理 1 的推导假设邻居均匀分布在一个 o 维球内（附录 C）。
- 分布假设：干净更新在参数空间中形成局部高密度，恶意更新是局部低密度离群点；这是"成功攻击者用高效而有效的影响"这一简约性原则的推论（第 2.3 节）。
- **分析**：方法隐含要求每轮参与聚合的更新是同维向量、数量为 N + M、且服务器能看到明文更新；论文没有讨论安全聚合（secure aggregation）、差分隐私（differential privacy）或客户端部分参与下的取数问题（**论文未说明**）。

**论文自述的局限**

- 非独立同分布（non-IID）数据会同时影响攻击实施与防御：数据分布越不独立同分布，本地更新越多样，"给攻击者留下空间，也让防御更难做"（第 3.4 节）。实验中 λ 增大时所有防御都退化（第 4.2.3 节、图 5、图 6c/6d）。
- 在 KDDCup99 上 LoMar 是"三项指标平均第二好"（第 4.2.1 节）；在 Amazon 上加大恶意比例时 LoMar 性能也会下降（第 4.2.2 节、图 4c）；VGGFace2 上目标标签准确率受攻击影响，训练 73.3%、测试 83.9%（表 5）。
- 结论提到第 6 节包含"未来工作讨论"，但正文没有给出具体的未来工作条目（**论文未说明**具体未来工作内容）。

**自适应攻击**

- 论文没有设计针对 LoMar 的自适应攻击，也没有评估了解 LoMar 检测规则、带宽 h、k 或阈值 ϵ 的攻击者（**论文未说明**；第 4.1.4 节只选取标签翻转与 [5] 的 stealthy 模型投毒两类固定攻击，并称它们是"每类中最具代表性、并为不同防御算法提供通用攻击形式"的方法）。因此 `evaluates_adaptive_attacker` 为 false。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**

- 分析：LoMar 的核心构造是把参数维度按**输出标签**分组后逐标签做 KDE 再相乘（图 3、式 (9)）。在联邦 LoRA 微调中，增量参数分布在注意力与前馈的多个权重矩阵上，没有与类别一一对应的参数块；即使下游是分类任务，输出头通常也不在 LoRA 适配范围内。因此"逐标签密度乘积"在 LoRA 场景缺少直接对应物，这一条是最可能致命的失效点。
- 分析：k 近邻与逐维 KDE 要求同轮所有更新同构、可逐维对齐。LoRA 增量是低秩矩阵对（A、B），不同客户端可能适配不同的 target modules、使用不同 rank，更新不是同构向量；库必须先按参数名与形状做对齐/展平，否则式 (4)–(7) 无法直接套用。论文完全未涉及这种异构性。
- 分析：阈值 ϵ = min{1, ϵm} 的理论依据（定理 1、定理 2）依赖均匀分布球、已知邻域体积 V 与常数带宽 h 等假设，这些量在 LoRA 的高维低秩几何下很难估计，式 (10) 的误报界不能直接搬运。
- 分析：论文假设每轮有 N + M 个同构更新可供比较，且防御者完全不知道恶意数量、用 k ≤ 0.4N 覆盖最坏情况。联邦大模型微调常是 cross-device、每轮参与客户端少、更新轮数少，k 可能超过当轮可用更新数；论文没有讨论部分参与（**论文未说明**）。
- 分析：论文用 λ 模拟标签不平衡，λ 增大时所有防御都退化（图 5、图 6c/6d）；联邦 LoRA 微调通常按领域或任务做个性化，客户端更新天然分散，会抬高"正常"更新的局部密度差异，既可能把合法个性化误判为恶意，也可能让恶意更新藏在合法的分散区间里。
- 分析：LoMar 需要服务器拿到明文完整更新并做两两距离比较，这在 LoRA 场景意味着传输和比较完整的适配器增量，且与安全聚合、差分隐私不兼容；论文只给出 O(N) 的复杂度声明，没有任何实测或通信/存储开销数据（第 8 节）。
- 分析：论文的有效性证据来自逻辑回归与 SqueezeNet 这类小模型和四个非大模型数据集，不能外推到十亿参数级模型与生成式任务；同时论文的攻击是分类标签控制，而大模型投毒多表现为带触发器的后门或安全对齐破坏，其更新痕迹未必是"局部低密度离群"。

## 10. 对防护库设计的含义

- 分析：LoMar 只需要一个采集点——服务器收到客户端更新的那一刻（server_receive），拿到"本轮、逐客户端、未经改动的完整更新张量 + 客户端标识 + 轮次 + 参数名/形状映射"。它不需要任何客户端侧钩子、逐样本数据、逐批损失或激活，也不需要额外前向/反向。这类"服务器只读原始更新"的视图是通用需求，几乎所有鲁棒聚合插件都建立在它之上。
- 分析：库需要提供"同轮更新集合"的批式视图与向量化两两距离/近邻计算原语（一次 O(N²) 距离矩阵，再取每行前 k 小），并允许插件按参数块（层、标签块）建立索引，因为 LoMar 的阶段一就是在参数分组上做 KDE（图 3、式 (4)–(7)）。这一需求相对通用，但"按输出标签聚类的参数分组"是 LoMar 特有的，插件应能通过模型元数据声明它需要的分组方式。
- 分析：库需要暴露两个服务器侧元数据视图：客户端加权因子 αi（由本地样本数 li 得出）与上一轮聚合后的全局模型快照，二者分别是式 (2)/式 (3) 与算法 2 的显式输入。这是通用需求（多数聚合类插件都要）。
- 分析：干预接口应设计成"聚合前的客户端级权重覆盖/二值掩码"这一最小原语，并额外暴露一个"是否对剩余权重重新归一化"的开关——论文式 (3) 是直接用原始 αi 累加被保留的更新，未做重新归一化，库若默认归一化就会与该论文语义不一致。掩码原语通用，归一化语义是这篇论文相关的细节。
- 分析：插件注册表应要求插件声明自己的数据依赖标签（是否需要干净参考数据、是否需要跨轮历史、是否需要逐样本数据、是否需要客户端额外计算）。LoMar 属于"无需干净参考、无需历史、纯服务器侧"，这类标签能让库在安全聚合或强隐私部署下自动禁用不满足前提的插件，属于通用能力。
- 分析：若要反过来检测这篇论文研究的攻击，底座应把一些通用统计量作为默认特征一并采集：逐客户端更新的范数（模型投毒用 φ = 10 放大更新，附录 A.1）、与同轮中位更新/全局更新方向的相似度、更新是否与客户端历史方向一致。这些特征在 LoRA 场景同样有意义（低秩增量的范数与方向），但论文本身并未把这些量用于检测，因此这是对库的扩展建议而非论文结论。

## 11. 原文依据

1. "the attacker injects M malicious clients into the FL system, where the budget of M is M ≤0.4N; ii) by default, the number of target label is considered as one."（第 2.2 节 Attacker）——支撑第 2 节的恶意客户端数量预算与单目标标签假设。
2. "The goal of the label flipping attack is to take control of the target label(class) in the FL system. Typically, the attacker address the target label by flip the output of target data samples from a source label."（第 4.1.4 节 Poisoning Attacks）——支撑第 3 节数据投毒从本地数据准备进入、以及第 2 节的目标是控制特定标签。
3. "Specifically, [5] generates the malicious update ˆum under a lp-norm distance metric and a explicit boosting factor φ as ˆu′m = φˆum. In this work, we set p = 2 and φ = 10 for the experimental setup."（附录 A.1 Model Poisoning Setup）——支撑第 3 节模型投毒在更新上传前的放大构造，以及第 5 节"放大后的范数是攻击痕迹"。
4. "In phase I, for the i-th remote update at the t-th iteration, LoMar finds its k-nearest neighbors to be its neighborhood reference set"（第 3.1 节 Overview）——支撑第 4 节阶段一的 k 近邻构造与第 5 节"需要同轮其他客户端更新"。
5. "For convenience, we assume that the output labels are already known at the beginning of LoMar defense."（第 3.2 节 Phase I）——支撑第 5 节"需要输出标签与参数到标签的分组"与第 9 节的已知标签假设。
6. "Formally, if F(i) ≥ϵ, we consider the remote client to be clean, otherwise malicious if F(i) < ϵ."（第 3.3 节 Phase II）——支撑第 6 节的服务器端客户端级二值剔除动作。
7. "it is unrealistic for the defender to obtain a clean joint model w for further analysis because the FL system can not be trusted from the start of the FL training process as it might have been already poisoned."（第 3.1 节 Overview）——支撑第 5 节"不需要干净参考模型"与第 9 节的数据可得性假设。
8. "our LoMar uses a non-parametric estimation method KDE, for studying the statistical features without knowing the clean training data distribution, which preserves the important privacy feature of FL."（第 3.4 节 Discussion）——支撑第 5 节"不需要干净参考数据分布"这一与 Auror/SAP 的关键区别。
9. "the extra cost of LoMar could be mainly from the development of the k-nearest neighborhood, which is proved as O(N) in [24]."（第 3.4 节 Discussion）——支撑第 8 节的开销描述。
10. "We can notice that our LoMar defense model has the best defense performance among all compared methods on overall accuracy, target label accuracy and source label accuracy in MNIST and Amazon datasets"（第 4.2.1 节 Results and Analysis）——支撑第 7 节表 3 的主要结论。

```json
{
  "key": "li2022lomar",
  "title": "LoMar: A Local Defense Against Poisoning Attack on Federated Learning",
  "year": 2022,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {"what": "每个客户端上传的完整模型更新向量 u_i^t = w_i^t - w^{t-1}", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "同轮更新之间的平方欧氏距离与 k 近邻集合（式(4)）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "参数维度按输出标签的分组关系（图3）", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "客户端加权因子 alpha_i = l_i / l（算法2输入，式(2)）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "上一轮联合模型 w^{t-1}（算法2输入，式(3)）", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每客户端更新的范数痕迹（模型投毒用 phi=10 放大更新，附录A.1）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["exclude_client", "reweight"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者注入 M 个恶意客户端且 M <= 0.4N，默认只有一个目标标签（第2.2节）",
    "防御者不知道恶意客户端数量，取 k <= 0.4N 作为最大潜在恶意的宽松上界（第3.1节）",
    "防御者不需要干净联合模型，也不需要干净训练数据分布（第3.1、3.4节）",
    "输出标签在防御开始时已经已知，参数可按输出标签聚类分组（第3.2节、图3）",
    "不同输出标签对应的参数贡献相互独立，F(i)=各标签 F(i)^r 的乘积（第3.2节、附录B）",
    "核带宽 h 对所有标签取常数，且更新 u_i 与输入 x 服从相似分布（第3.2节、附录B）",
    "干净更新在参数空间中形成局部高密度，恶意更新表现为局部低密度离群（第2.3、3.2节）",
    "服务器可获得明文逐客户端更新与每客户端本地样本数，每轮参与更新为同维向量"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "2.2 Attacker", "supports": "第2节：恶意客户端数量预算 M <= 0.4N 与默认单目标标签", "text": "the attacker injects M malicious clients into the FL system, where the budget of M is M ≤0.4N; ii) by default, the number of target label is considered as one."},
    {"section": "4.1.4 Poisoning Attacks", "supports": "第3节：数据投毒从本地数据准备进入，目标是控制目标标签", "text": "The goal of the label flipping attack is to take control of the target label(class) in the FL system. Typically, the attacker address the target label by flip the output of target data samples from a source label."},
    {"section": "Appendix A.1 Model Poisoning Setup", "supports": "第3节：模型投毒在上传前用放大因子 phi=10 构造更新", "text": "Specifically, [5] generates the malicious update ˆum under a lp-norm distance metric and a explicit boosting factor φ as ˆu′m = φˆum. In this work, we set p = 2 and φ = 10 for the experimental setup."},
    {"section": "3.1 Overview", "supports": "第4、5节：阶段一在服务器侧对每个更新取同轮 k 近邻", "text": "In phase I, for the i-th remote update at the t-th iteration, LoMar finds its k-nearest neighbors to be its neighborhood reference set"},
    {"section": "3.2 Phase I: Malicious Client Factor", "supports": "第5、9节：需要预先知道输出标签并按标签分组参数", "text": "For convenience, we assume that the output labels are already known at the beginning of LoMar defense."},
    {"section": "3.3 Phase II: Finding Decision Threshold", "supports": "第6节：检测后按阈值在服务器端把客户端二值剔除", "text": "Formally, if F(i) ≥ϵ, we consider the remote client to be clean, otherwise malicious if F(i) < ϵ."},
    {"section": "3.1 Overview", "supports": "第5节：不需要干净参考模型；第9节的数据可得性假设", "text": "it is unrealistic for the defender to obtain a clean joint model w for further analysis because the FL system can not be trusted from the start of the FL training process as it might have been already poisoned."},
    {"section": "3.4 Discussion", "supports": "第5节：不需要干净训练数据分布，与 Auror/SAP 的关键区别", "text": "our LoMar uses a non-parametric estimation method KDE, for studying the statistical features without knowing the clean training data distribution, which preserves the important privacy feature of FL."},
    {"section": "3.4 Discussion", "supports": "第8节：聚合器侧额外计算主要来自 k 近邻，复杂度 O(N)", "text": "the extra cost of LoMar could be mainly from the development of the k-nearest neighborhood, which is proved as O(N) in [24]."},
    {"section": "4.2.1 Analysis of Compared Algorithms for Each Dataset", "supports": "第7节：表3 中 LoMar 在 MNIST 与 Amazon 上优于所有对比防御", "text": "We can notice that our LoMar defense model has the best defense performance among all compared methods on overall accuracy, target label accuracy and source label accuracy in MNIST and Amazon datasets"}
  ]
}
```
