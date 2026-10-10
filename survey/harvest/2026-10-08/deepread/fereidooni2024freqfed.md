# fereidooni2024freqfed：FreqFed: A Frequency Analysis-Based Approach for Mitigating Poisoning Attacks in Federated Learning

## 1. 基本信息

**场景**：传统联邦学习（classic federated learning）。论文没有涉及大语言模型，也没有涉及参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）或低秩适配（Low-Rank Adaptation, LoRA）。其模型是图像分类的卷积网络与 ResNet、词预测的 LSTM、入侵检测的 GRU、说话人验证的 LSTM，以及图分类的图神经网络（Graph Neural Network, GNN），全部是完整权重训练与完整权重上传。

**训练阶段**：防御动作位于**服务器端的每轮聚合阶段**，即服务器收到全部客户端本地上传之后、执行 FedAvg 之前（Figure 1 的 Step 1 至 Step 4，Algorithm 1 第 1–7 行）。需要指出一处论文内部不一致：摘要写"effectively filter out malicious updates during local training on the clients"（在客户端本地训练期间过滤），但 Section IV-B、Section IV-C、Figure 1 与 Algorithm 1 都把离散余弦变换（Discrete Cosine Transform, DCT）、滤波与聚类放在服务器执行（"Server executes"），论文未说明客户端侧是否也运行任何过滤逻辑。

**论文类型**：防御（检测 + 鲁棒聚合）。它既做异常客户端识别，也直接改变聚合结果。

**模型与数据规模**：九个数据集、多种模型与参数量，见 Table I——Reddit 20.6M 条记录 / LSTM 约 20M 参数；IoT-Traffic 65.6M 条 / GRU 约 507k；Cifar-10 60.0k / ResNet-18 Light 约 2.7M；MNIST 70.0k / CNN 约 431k；EMNIST 814.2k / LeNet 约 66k；TIMIT 201.6k / LSTM 约 12M；PROTEINS 1113 / GraphSage 约 102k；NCI1 4110 / GAT 约 101k；D&D 1178 / GCN 约 106k、GatedGCN 约 104k、MoNet 约 102k（Section V-A 与 Appendix A）。

## 2. 威胁模型

**攻击者是谁**：被攻陷的恶意客户端（malicious clients）。数量上限为 kA < K/2（Section III），K 是参与训练的客户端总数。

**能力**：完全控制这些客户端的全部本地训练数据、本地训练操作与超参数（学习率、训练轮数等）；可以在把本地模型提交给全局服务器之前操纵其权重；可以向损失函数添加正则项以逃避服务器异常检测器的检测范围，使投毒模型与良性模型在任何可比指标（如 L2 范数、余弦角距离）上尽量不可区分；可以逐轮改变行为，在某一轮决定正常或恶意；可以手工调整攻击参数实施自适应攻击，也可使用最先进的注入技术（Section III）。攻击者不能控制聚合器或任何诚实客户端上的进程，但可以完全知道全局服务器的聚合操作。

**知识**：知道全局服务器的聚合规则；可以做"已知良性模型"（Known-Benign）与"未知良性模型"（Unknown Benign，用自有良性数据训练近似良性模型作参考）两种假设下的频率域规避（Section V-B3 i）。

**目标**：无目标投毒（untargeted poisoning），使全局模型失效乃至拒绝服务；或定向投毒（targeted poisoning，后门），让模型对攻击者选定的一批输入以高置信度误分类。攻击者同时希望全局模型在主任务与攻击者选定子任务上都保持高准确率（Section III）。

**防御者是谁、能看到什么、信任什么**：防御者是服务器/聚合器。它每轮能看到每个客户端上传的本地模型权重（论文写作 W_i^t，并称之为 model update），看不到客户端的本地数据、本地训练过程、逐样本损失或中间激活。它信任诚实客户端占多数（kA < K/2）这一前提，也隐含信任服务器自身是诚实的。论文不假设客户端数据是独立同分布（independent and identically distributed, iid）或非 iid，并且不使用根数据集（root dataset）或干净参考数据。

## 3. 攻击入口与流程位置

本文是防御论文，以下写它所针对的攻击入口。

- **本地数据准备**：Label Flipping（Section V-A、Table II）、数据投毒型后门（Section V-B2 的音频数据投毒、Section V-B3 iii 的频率触发器、Appendix A 的像素触发器/语义触发器/图节点子图触发器）、分布式后门攻击（Distributed Backdoor Attack, DBA）与图上的分布式数据投毒后门（Table III、Table VI）。这些攻击在客户端本地把触发器或标签改动写入训练数据。
- **本地训练过程**：Optimized（PGD）攻击通过投影梯度下降（Projected Gradient Descent, PGD）优化投毒目标（Table II、Table III 的 Edge-case）；constrain-and-scale 在本地训练目标中加入规避项与缩放约束（Table III、Table V）；Neurotoxin 专门挑选良性客户端不太会改动的更新坐标以延长后门寿命（Section V-B2 与 Table IV）；Mirai Scanning 让本地模型学习隐藏 Mirai 僵尸网络流量（Section V-B2）；3DFed 使用指示机制、自适应调参与诱饵模型（Section V-A）。
- **更新上传前的后处理**：Random Updates 直接发送任意更新（Table II）；constrain-and-scale 在提交前对更新做约束与缩放；Section V-B3 的"集中式后门攻击"（Concentrated Backdoor Attack）让所有恶意客户端提交完全相同或仅有微小噪声差异的模型（Table X）；Section V-B3 ii 的良性频率注入在每轮训练后把权重的低频 DCT 分量替换为无后门的良性低频分量，再做逆 DCT 回到权重域。
- **服务器聚合**：论文未说明攻击者能进入服务器聚合过程，Section III 明确攻击者无法控制聚合器上的任何进程。FreqFed 自身所在的入口正是服务器聚合。

需要区分的是：3DFed 在评测时把补丁加到每张测试图像并统一改标签，这是攻击方的评测构造，不是训练流程入口（Section V-B2）。

## 4. 方法原理

核心思想是把权重当作信号，变换到频率域后只保留低频成分，再在低频成分空间里做密度聚类，用"多数派"决定哪些客户端可以参与聚合。

**第一步，DCT 变换（Section II-C 公式 (2)）**：对 N×M 的矩阵 x 做二维 DCT 得到系数矩阵 X(k,l)，公式为 X(k,l) = Σ_m Σ_n c1·c2·x(m,n)·cos(kπ(2m+1)/(2M))·cos(lπ(2n+1)/(2N))，其中 c1、c2 在 k=0 或 l=0 时取 √(2/(MN))，否则取 1。DCT 可逆，系数按显著性升序排列，第一个系数正比于序列均值。

**第二步，低频谱滤波（Algorithm 1 第 13–18 行）**：论文从 DCT 系数矩阵 V 中构造向量 F，只保留满足 i + j ≤ ⌊|V|/2⌋ 的系数（论文写作 F ∪ V_ij）。论文未明确 |V| 指的是矩阵边长还是元素总数；论文也把 V 描述为"方阵"（square matrix），但未说明非方阵权重矩阵与一维参数（偏置、归一化参数）如何处理。

**第三步，聚类（Algorithm 1 第 19–30 行）**：对任意两个客户端的低频向量计算余弦距离，距离矩阵项为 1 − CosineSim(F_i, F_j)，构成 K×K 对称矩阵；用 HDBSCAN（Hierarchical Density-Based Spatial Clustering of Applications with Noise）对该距离矩阵聚类；取元素最多的簇（max cluster = argmax 簇大小）作为接受集合，返回其索引 (b1, …, bL)。选择 HDBSCAN 的理由见 Section II-D：它不需要预先指定簇数，能处理不同大小与形状的簇，并能把噪声或离群点排除在簇之外。

**第四步，聚合（Algorithm 1 第 7 行）**：只对被接受的 L 个模型求平均，G^{t+1} = Σ_{l=1}^{L} W^t_{b_l} / L。注意公式 (1) 给出的 FedAvg 是按样本数加权的 G^{t+1} = Σ (n_i/n) W_i^t，而 Algorithm 1 第 7 行对接受模型做的是等权平均；论文未说明这两者如何统一。

**成立直觉（Section IV-A）**：作者提出两点观察——模型权重的多数能量位于低频 DCT 分量（引用 [54]、[59]）；神经网络在逼近目标函数时优先学习低频、再从低频推进到高频（引用 [42]、[60]）。在此基础上，作者假设要植入后门或破坏整体性能的恶意更新，其低频分量会与良性更新不同。

需要强调一个实现细节：Algorithm 1 第 4 行做 DCT 的对象是客户端训练后的本地模型 W_i^t 本身，而公式 (1) 与文中叙述都称之为"更新"（update）；论文未说明是否改用增量 (W_i^t − G^t)。

## 5. 检测或防御所需的数据

**逐项列出方法需要的每一种输入：**

1. **每个客户端每轮的本地模型权重 W_i^t**。是什么：客户端本地训练结束后的完整模型参数。在哪里采集：服务器收到更新时（Algorithm 1 第 3 行）。粒度：逐客户端、逐层（DCT 作用在权重矩阵上）。是否需要跨轮历史：否，Algorithm 1 每轮只用当前轮的 W_i^t，不引用历史更新。是否需要干净参考数据或根数据集：否，论文不使用服务器侧数据，也不需要良性模板。是否需要额外前向或反向计算：不需要模型前向或反向，但需要在服务器侧对全部参数做一次 DCT。是否需要其他客户端的数据：是，聚类需要本轮全部 K 个客户端的低频向量。
2. **权重经二维 DCT 后的系数矩阵 V_i 与低频谱分量向量 F_i**。是什么：由步骤 1 派生出的频域表示。在哪里采集：服务器收到更新后计算（Figure 1 的 Step 1–2）。粒度：逐客户端（由逐层系数的低频部分拼接成向量）。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：是。
3. **客户端两两余弦距离矩阵**。是什么：K×K 的 1 − CosineSim(F_i, F_j)。在哪里采集：服务器聚合前计算（Algorithm 1 第 20–24 行）。粒度：客户端对。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：是。
4. **HDBSCAN 聚类标签与最大簇索引 (b1, …, bL)**。是什么：每个客户端所属簇的编号，以及元素最多的簇的成员索引。在哪里采集：服务器聚合前（Algorithm 1 第 25–30 行）。粒度：逐客户端。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：是。

论文未说明需要逐样本损失、隐藏层激活（logits）、输出文本、梯度、逐层范数或历史更新；这些东西在 FreqFed 中都不出现。

**攻击会在哪些可观测量上留下痕迹**：论文的立场是投毒（无论定向还是无目标）会在本地模型权重的低频 DCT 分量分布上留下与良性客户端不同的偏移，从而在低频谱向量空间里体现为离群点或小簇。论文举出的具体机理是：植入后门会在权重中引入一个来自触发器的人工关联，即一种额外的结构或模式，导致能量向某些频率移动（Section IV-A）。

**论文声称能绕过的检测规避手段**：作者声称 FreqFed 不依赖数据分布假设，也不依赖攻击类型与策略假设（Section VII），并在实验中声称对以下规避仍然有效——在损失中加入频率域异常规避项的 constrain-and-scale（Table VII，含 Known-Benign 与 Unknown Benign 两种参考模型获取方式）、把后门压到高频段的良性频率注入（Table VIII）、在数据频率表示中注入触发器的频率触发器攻击（Table IX，覆盖 PDR 10% 到 100%）、所有恶意客户端提交相同模型的集中式后门攻击（Table X，PMR 最高到 49%，iid 为 0.0 与 0.1）、以及用拉格朗日优化自动调整约束的自适应攻击（Appendix C，10% ≤ PDR ≤ 100%、10% ≤ PMR ≤ 49%）。论文未报告任何自适应攻击成功绕过 FreqFed 的结果。

## 6. 干预动作

**动作**：客户端剔除（exclude_client），但形式上表现为"只聚合最大簇成员"。Algorithm 1 第 7 行只对最大簇中的 L 个模型求平均，落在这个簇之外的客户端更新被直接丢弃，不进入聚合。

**发生位置**：服务器端，聚合之前（Figure 1 的 Step 3 与 Step 4 之间）。

**论文未说明的部分**：论文未对被剔除的客户端做任何其他处理——没有重新加权、没有裁剪、没有加噪、没有样本过滤、没有模型修复或回滚、也没有仅报告模式；论文也未说明被剔除的客户端是否会在后续轮次被永久拉黑。从 Algorithm 1 看，每一轮都会对全部 K 个客户端调用 ClientUpdate，也就是说每一轮的聚类是独立的，上一轮被剔除的客户端下一轮仍可参与（这与 Section III 中"攻击者可逐轮改变行为"的假设一致）。

## 7. 实验设置与主要结果

**设置**：九个数据集与对应模型见 Table I 与 Appendix A。iid 程度用 iid rate 模拟：每个客户端数据中比例为 iid rate 的样本来自原始数据的所有标签，其余 (1 − iid rate) 只来自分配给该客户端的标签 l；iid rate 为 1.0 表示完全 iid，为 0.0 表示客户端只有单一标签（Section V-A）。指标为主任务准确率（Main Task Accuracy, MA）与后门准确率（Backdoor Accuracy, BA，也称攻击成功率）。硬件为 4 张 NVIDIA RTX 8000（每张 48GB）、AMD EPYC 7742、1024 GB 内存（Section V-A）。

**客户端数与参与率**：论文未给出每类实验的客户端总数 K 与参与率；只给出投毒模型率（Poison Model Rate, PMR）与投毒数据率（Poison Data Rate, PDR）的取值范围。Appendix A 只说明数据如何切分给客户端（Reddit 以发帖量在 150 到 500 之间的用户为一个客户端；NIDS 使用 24 个 IoT 设备的流量、每个客户端 2k–3k 个数据包；TIMIT 每个说话人一个本地数据集、每个客户端 3.2k 帧；Section V-B2 的 NIDS 实验对 12 种设备类型取平均）。**训练轮次 T 论文未报告。**

**攻击与对比防御**：无目标攻击为 Label Flipping、Random Updates、Optimized（PGD）；定向攻击为 constrain-and-scale、Edge-case（PGD）、DBA、3DFed、Mirai Scanning、Neurotoxin、频率触发器、说话人验证后门、图分布式数据投毒后门，以及集中式后门与自适应攻击。对比防御为 Krum、AFA、Median、DP、FoolsGold、BayBFed、FLAME、DeepSight、Auror（Section V-A、Section V-B4）。

**关键结果（均按论文报告的数值）**：

- 无目标攻击，PMR = 49%、iid = 0.7（Table II）：Label Flipping 下 Cifar-10 从无攻击的 MA 77.3 降到无防御的 35.8，FreqFed 为 77.1；MNIST 98.6 → 50.8 → 97.8；EMNIST 81.3 → 13.4 → 81.2。Random Updates：Cifar-10 77.0 → 31.2 → 77.0。Optimized（PGD）：Cifar-10 77.2 → 10.0 → 77.1；MNIST 98.6 → 44.5 → 98.3；EMNIST 81.4 → 4.9 → 81.3。
- 图像域定向攻击，PDR = 50%、PMR = 30%、iid = 0.9（Table III）：单后门像素模式 BA 100.0/MA 85.5（无防御）对比 BA 0.0/MA 91.9（FreqFed）；语义后门 BA 100.0/MA 86.8 对比 BA 0.0/MA 92.0；Edge-case（PGD）BA 73.4 对比 BA 4.1；多后门像素模式 BA 97.6 对比 0.0；DBA 像素模式 BA 93.8/MA 57.4 对比 BA 0.4/MA 76.2。3DFed 像素模式在无攻击时 BA 就是 9.9，FreqFed 下为 10.4。
- 文本域（Reddit），PDR = 50%、PMR = 25%（Table IV）：constrain-and-scale 的 BA 100.0/MA 22.6（无防御）对比 BA 0.0/MA 22.6；Neurotoxin BA 100.0/MA 16.2 对比 BA 0.0/MA 19.8。
- 入侵检测（Section V-B2）：不使用 FreqFed 时 98.5% 的僵尸网络数据包未被检测出，整体 MA 降到 97.6%；使用 FreqFed 后 BA 为 0.0%，MA 为 98.3%。
- 说话人验证（Table V）：数据投毒 PDR = 0.49 时 BA 84.7/MA 92.9（无防御）对比 BA 0.0/MA 95.3；模型投毒 PMR = 0.49 时 BA 100.0/MA 94.0 对比 BA 0.0/MA 94.9。
- 图分类，PDR = 25%、PMR = 49%（Table VI）：对 PROTEINS、NCI1、D&D 三个数据集与 GraphSage、GAT、GCN、GatedGCN、MoNet 五种模型，FreqFed 的 BA 全部为 0.0，例如 PROTEINS + GraphSage 从无防御的 BA 100.0/MA 66.7 变为 BA 0.0/MA 79.3。
- 自适应攻击（Table VII，PDR = 50%、PMR = 25%、iid = 0.7、α = 0.7）：Known-Benign 下 Cifar-10 的 BA 100.0/MA 83.9（无防御）对比 BA 0.0/MA 85.7；Unknown Benign 下 Cifar-10 的 BA 100.0/MA 84.3 对比 BA 0.0/MA 85.0。良性频率注入（Table VIII，PDR = 50%、PMR = 30%、iid = 0.7）：MNIST 无防御 BA 0.0/MA 83.9，FreqFed BA 0.0/MA 96.6。频率触发器（Table IX，Cifar-10、iid = 0.8）：PDR 从 10 到 100，无防御 BA 为 91.0 到 98.3，FreqFed 全部为 BA 0.0。集中式后门（Table X，Cifar-10、iid = 0.0）：PMR 10% 时无防御 BA 60.6，FreqFed 预训练与随机初始化两种情形均为 0.0；PMR 20% 时 81.0 对 0.0；PMR 30%、40%、49% 时无防御 BA 100.0，FreqFed 均为 0.0。
- 与非 iid 的关系：Figure 2b 显示优化无目标攻击下，即使 iid = 0.0（数据完全不相交），FreqFed 仍能检测投毒模型并把 MA 保持在约 75%；Figure 4 显示 constrain-and-scale 下 iid = 0.0 时仍能区分投毒与良性模型。
- 与现有防御的对比（Table XI，PMR = 25% 的 constrain-and-scale）：在 Reddit、Cifar-10、IoT-Traffic 上，FreqFed 是唯一在三处都有效的防御（BA 分别为 0.0、0.0、0.0，MA 分别为 22.6、86.5、96.5）；例如 Krum 在 Reddit 上 BA 仍为 100.0，Auror 在 Reddit 上 MA 只有 10.5。Table XII（PMR = 49%、iid = 0.7）显示无目标攻击下 FreqFed 在 Cifar-10、MNIST、EMNIST 上的 MA 分别为 77.1/77.1、97.8/98.3、81.2/81.3（LF/PGD），而其他防御明显更低。
- PMR 上限：Figure 2a、Figure 3a、Figure 5、Figure 6a、Figure 6b、Figure 7 均显示 FreqFed 在 PMR < 50% 时有效，PMR ≥ 50% 时可能把投毒模型误判为多数簇（Section V-B1）。

## 8. 开销

**论文未报告**计算、通信与存储开销的定量数据。论文没有给出运行时、额外通信量或额外内存的测量值；唯一与资源有关的信息是实验硬件配置（Section V-A：4 张 NVIDIA RTX 8000、AMD EPYC 7742、1024 GB 内存）。

**分析**：从 Algorithm 1 可以读出，FreqFed 不改变客户端与服务器之间的通信内容与轮数，通信开销与标准 FedAvg 相同；服务器端增加的开销来自对每个客户端全部权重做一次 DCT、构造 K×K 余弦距离矩阵、以及运行 HDBSCAN，因此服务器计算量随客户端数 K 与参数量线性或平方级增长（余弦距离部分为 O(K²·d)）。这些量级论文没有测量，也没有讨论在参数量远大于 Table I 的场景下是否可扩展。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设**（论文明确写出的）：恶意客户端数量满足 kA < K/2（Section III）；恶意客户端无法控制聚合器与诚实客户端（Section III）；模型权重的大部分能量位于低频 DCT 分量，且神经网络训练时优先学习低频（Section IV-A）；投毒会在低频分量上造成与良性更新不同的偏移（Section IV-A）；良性客户端会因为"强化同一个目标、把频率表示朝同一方向移动"而聚成最大的簇，而投毒客户端因为注入全新行为而在低频分量上显著不同（Section V-B3 集中式后门攻击一节）；聚合完全由服务器按 Algorithm 1 执行。**论文未说明**的部分包括：非方阵权重矩阵与一维参数（偏置、归一化参数）如何做二维 DCT；|V| 的确切定义；权重是按整模型还是按层分别变换后拼接。

**论文自述的局限**：PMR ≥ 50% 时可能把投毒模型误判为最大簇，Section V-B1 明说这违反了 Section III 的假设；对把后门压到高频的注入攻击，论文的观察是"不改变低频分量就无法植入后门"，即该攻击在无防御时 BA 就已是 0%（Table VIII），并且逆 DCT 依赖多步近似，替换低频后做逆变换仍会再次改变低频；3DFed 的后门准确率计算被论文认为有偏（它对所有图像加补丁并统一改标签，包括本身约占 10% 的目标类图像）；MNIST 上良性频率注入的 BA 在脚注 4 中被说明并非严格 0%，因为良性聚合模型的少量误分类会被算作攻击成功；图数据稀疏时 PDR 增大导致 MA 下降（Appendix B、Figure 8）。

**自适应攻击评估**：有评估，且论文报告全部被缓解。频率域约束损失（Table VII，α = 0.7，Known-Benign 与 Unknown Benign 两种）下 FreqFed 的 BA 为 0.0；良性频率注入（Table VIII）下 BA 为 0.0；集中式后门（Table X，PMR 到 49%、iid = 0.0 与 0.1）下 BA 为 0.0；Appendix C 用拉格朗日优化自动调整攻击约束，在不知防御与已知防御两种情形、10% ≤ PDR ≤ 100% 与 10% ≤ PMR ≤ 49% 下 BA 均为 0.0。论文未报告任何自适应攻击成功绕过 FreqFed 的案例，也未报告自适应攻击对主任务准确率的额外影响细节。

**迁移到联邦大模型 LoRA 微调时可能失效的假设（分析：）**

- 频率域前提不成立：论文的两点观察（能量集中在低频、网络先学低频）是在完整卷积/LSTM/GNN 权重上陈述并引用的；LoRA 的增量是低秩乘积 B·A，其中 A 常为随机初始化、B 常为零初始化，训练初期增量接近零且高度结构化，其 DCT 低频分布是否还能区分良性与投毒客户端，论文未说明，也无法从本文推出。
- 上传对象不同：论文对客户端训练后的完整模型做 DCT；在联邦 LoRA 中通常只上传适配器矩阵，服务器看到的是两个小矩阵（还可能只上传 B 或只上传 A），K×K 余弦距离所依赖的向量维度与谱结构完全不同；论文对低秩增量、非方阵因子、以及客户端本地合并后才上传的形态都未讨论。
- 多数派假设在供应链场景下更脆弱：论文依赖"良性客户端构成最大簇"，其前提是恶意客户端不能控制服务器且占比小于一半；如果投毒来自适配器或模型发布者，或所有客户端都基于同一个被投毒的基座模型/适配器开始训练，则低频表示可能整体一致地偏移，"多数派即良性"不再成立。
- 指标与任务不同：论文用分类式的 BA 与 MA；生成式大模型的投毒目标（例如触发词越狱、安全对齐破坏）没有等价的 BA，论文未说明在生成任务上如何度量或是否适用。
- 成本不可比：论文最大模型约 20M 参数（Table I），服务器每轮对每个客户端做 DCT 并算 K² 余弦距离；在数十亿参数、数百客户端的联邦 LoRA 场景下这套流程的可行性论文未报告。
- 数据分布模拟不同：论文的 iid rate 是按标签分布构造的（Section V-A），而联邦 LoRA 微调的非 iid 更多来自任务、领域与指令格式差异；论文的非 iid 结果不能直接外推到这种异构。

## 10. 对防护库设计的含义

1. **分析**：底座的服务器侧必须提供"收到更新时"（server_receive）这一个固定钩子，并保证能拿到**未经任何处理、未经聚合、未被裁剪**的逐客户端完整参数张量，同时保留参数名与形状元信息；FreqFed 需要按权重矩阵做二维 DCT，所以形状信息（哪些是二维矩阵、哪些是一维向量）不能在上传时丢失。
2. **分析**：需要一个"逐客户端 × 逐层 × 逐轮"的权重视图，并在其上允许插件注册派生视图（这里是低频谱向量、K×K 余弦距离矩阵、聚类标签）；把"客户端间关系矩阵"作为一等数据对象暴露给插件，这是 FreqFed 这一类"先算客户端两两距离再聚类"的防御的通用需求，而 DCT 与低频谱截断规则是 FreqFed 特有的。
3. **分析**：干预接口不能只有"剔除、加权、裁剪、加噪"几个原子操作，还必须支持"按子集聚合"——即插件返回一个客户端索引集合，底座据此在该轮只对这些客户端做聚合；FreqFed 的动作在语义上是"选择子集"而不是"给客户端打分后调权"，如果底座只暴露权重向量，这类方法会被勉强表达且容易出错。
4. **分析**：底座不应强制每个插件都提供根数据集、干净参考模型或跨轮历史。FreqFed 三者都不用，只依赖当前轮全部客户端的上传；如果采集底座把"根数据集校验"或"历史窗口"设成必填，会无谓地提高部署门槛。同时这也意味着底座需要处理"某轮可用客户端数变化"的情况，因为聚类结果依赖本轮实际收到的客户端数量。
5. **分析**：客户端钩子方面，FreqFed 不需要客户端做任何额外计算，只需保证客户端在本地训练结束后能把模型（或约定的上传对象）原样导出给服务器；因此库里客户端侧的最小契约就是"训练后可导出"，额外的逐样本或逐步采集应当是可选插件而非底座必需。
6. **分析**：库应当把"前提条件检查"作为通用能力，而不是交给插件自行声明后就信任。FreqFed 的硬前提是恶意客户端少于一半，以及服务器是诚实的聚合者；当检测到被剔除比例异常、或聚类最大簇占比过低时，底座应能阻止"继续按该结果聚合"并给出告警，否则恶意比例超过一半时该方法会安静地把投毒模型聚成最大簇并聚合它们（Section V-B1 与 Figure 2a 报告了这一失效模式）。

## 11. 原文依据

1. 章节：Section III（Attacker's Capabilities）。支撑：第 2 节关于攻击者身份、数量上限与能力范围的论断。
   > "Fully control up to kA < K/2 compromised clients, including the entire local training data of these clients, as well as the local training operation and the hyperparameters (i.e., learning rate, number of training epochs, etc.)."

2. 章节：Section III（Attacker's Capabilities）。支撑：第 2 节与第 5 节关于攻击者可用正则项规避权重类异常检测的论断。
   > "Maliciously craft model updates by adding regularization terms to the loss function to evade the global server’s anomaly detector’s detection scope and make poisoned models as indistinguishable as possible from benign ones."

3. 章节：Section III（Attacker's Capabilities）。支撑：第 2 节关于信任边界（服务器与诚实客户端不可被控制、聚合规则可知）的论断。
   > "Still, the adversary has no control over any processes executed at the aggregator or the honest clients. However, the attacker can know the global server’s aggregating operations perfectly."

4. 章节：Section IV-A（Design Challenges and Ideas）。支撑：第 4 节关于方法依赖的两点频率观察的论断。
   > "We made two central observations: i) most of the energy in model weights lies in low-frequency DCT components [54], [59], and ii) DNNs prioritize low frequencies and progress from low to high frequencies when approximating target functions during training"

5. 章节：Section IV-A（Design Challenges and Ideas）。支撑：第 4 节与第 5 节关于"投毒会在低频分量上留下痕迹"这一核心假设的论断。
   > "We posit that malicious updates intended to introduce a backdoor into the global model or impact the overall performance of the global model are characterized by differences in the low-frequency components compared to benign updates."

6. 章节：Section IV-B（High-level Overview）。支撑：第 4 节与第 5 节关于低频谱向量、余弦距离聚类、选取最大簇的论断。
   > "The low-frequency component vectors from all clients are subsequently passed to a clustering algorithm, which groups them into clusters based on cosine distance and selects the cluster with the most vectors in Steps 2 and 3."

7. 章节：Section V-B1（Impact of different PMR）。支撑：第 7 节与第 9 节关于 PMR 低于 50% 才有效、kA < K/2 是硬前提的论断。
   > "In contrast, FreqFed successfully detects the poisoned models and lowers the BA to 0% when the PMR is less than 50%. Hence, FreqFed is effective as long as the assumption kA < K/2 holds."

8. 章节：Section V-B3 i（Constrain Loss in Frequency Domain）。支撑：第 7 节与第 9 节关于自适应频率域规避攻击被缓解的论断。
   > "The table demonstrates that FreqFed can effectively mitigate the attack in both cases, even including deviations of the low-frequency components into the loss. The optimizer still adapts these components, allowing FreqFed to filter the poisoned models."

9. 章节：Section V-B3（Concentrated Backdoor Attack）。支撑：第 9 节关于"良性客户端聚成最大簇"这一假设及其直觉解释的论断。
   > "A reason for this might be that the benign models aim to strengthen the same objective and move their frequency representation in a specific direction to learn the target function."

10. 章节：Section VII（Conclusion）。支撑：第 1 节与第 9 节关于论文自称不做数据分布与攻击类型假设的论断。
    > "Our defense mechanism has a generic adversary model. It does not make any assumptions about underlying data distributions or attack types/strategies and can be applied to various application domains and model architectures."

```json
{
  "key": "fereidooni2024freqfed",
  "title": "FreqFed: A Frequency Analysis-Based Approach for Mitigating Poisoning Attacks in Federated Learning",
  "year": 2024,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted", "backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {
      "what": "每个客户端每轮上传的本地模型权重 W_i^t，服务器端做二维 DCT 的原始输入",
      "where": "server_receive",
      "granularity": "layer",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "权重经二维 DCT 后按 i+j<=floor(|V|/2) 抽取的低频谱分量向量 F_i",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "客户端两两余弦距离矩阵（1 减余弦相似度）与 HDBSCAN 聚类标签、最大簇索引",
      "where": "server_aggregate",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["exclude_client"],
  "intervention_where": ["server"],
  "assumptions": [
    "恶意客户端数量满足 kA < K/2（Section III）",
    "攻击者无法控制聚合器与诚实客户端，服务器按 Algorithm 1 诚实执行（Section III）",
    "模型权重的大部分能量位于低频 DCT 分量（Section IV-A，引用 [54],[59]）",
    "神经网络训练时优先学习低频、再从低频推进到高频（Section IV-A，引用 [42],[60]）",
    "投毒会在本地模型权重的低频 DCT 分量上造成与良性更新不同的偏移（Section IV-A）",
    "良性客户端因优化同一目标而聚成最大的簇，投毒客户端因注入新行为而在低频分量上显著不同（Section V-B3 集中式后门攻击）",
    "权重矩阵可按论文方式做二维 DCT；论文未说明非方阵与一维参数的处理方式"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "Section III (Attacker's Capabilities)",
      "supports": "第 2 节：攻击者是恶意客户端，最多 kA < K/2，完全控制本地数据、训练操作与超参数",
      "text": "Fully control up to kA < K/2 compromised clients, including the entire local training data of these clients, as well as the local training operation and the hyperparameters (i.e., learning rate, number of training epochs, etc.)."
    },
    {
      "section": "Section III (Attacker's Capabilities)",
      "supports": "第 2 节与第 5 节：攻击者可在损失中加入正则项以规避服务器基于权重的异常检测",
      "text": "Maliciously craft model updates by adding regularization terms to the loss function to evade the global server’s anomaly detector’s detection scope and make poisoned models as indistinguishable as possible from benign ones."
    },
    {
      "section": "Section III (Attacker's Capabilities)",
      "supports": "第 2 节：信任边界，攻击者不能控制聚合器与诚实客户端，但知道聚合规则",
      "text": "Still, the adversary has no control over any processes executed at the aggregator or the honest clients. However, the attacker can know the global server’s aggregating operations perfectly."
    },
    {
      "section": "Section IV-A (Design Challenges and Ideas)",
      "supports": "第 4 节：方法依赖的两点频率域观察，权重能量集中在低频且网络先学低频",
      "text": "We made two central observations: i) most of the energy in model weights lies in low-frequency DCT components [54], [59], and ii) DNNs prioritize low frequencies and progress from low to high frequencies when approximating target functions during training"
    },
    {
      "section": "Section IV-A (Design Challenges and Ideas)",
      "supports": "第 4 节与第 5 节：核心假设，投毒会在低频分量上产生与良性更新不同的差异",
      "text": "We posit that malicious updates intended to introduce a backdoor into the global model or impact the overall performance of the global model are characterized by differences in the low-frequency components compared to benign updates."
    },
    {
      "section": "Section IV-B (High-level Overview)",
      "supports": "第 4 节与第 5 节：低频谱向量按余弦距离聚类并选出元素最多的簇",
      "text": "The low-frequency component vectors from all clients are subsequently passed to a clustering algorithm, which groups them into clusters based on cosine distance and selects the cluster with the most vectors in Steps 2 and 3."
    },
    {
      "section": "Section V-B1 (Impact of different PMR)",
      "supports": "第 7 节与第 9 节：PMR 小于 50% 时 BA 降为 0，kA < K/2 是方法的硬前提",
      "text": "In contrast, FreqFed successfully detects the poisoned models and lowers the BA to 0% when the PMR is less than 50%. Hence, FreqFed is effective as long as the assumption kA < K/2 holds."
    },
    {
      "section": "Section V-B3 i (Constrain Loss in Frequency Domain)",
      "supports": "第 7 节与第 9 节：把低频分量差异写进损失的自适应攻击仍被缓解",
      "text": "The table demonstrates that FreqFed can effectively mitigate the attack in both cases, even including deviations of the low-frequency components into the loss. The optimizer still adapts these components, allowing FreqFed to filter the poisoned models."
    },
    {
      "section": "Section V-B3 (Concentrated Backdoor Attack)",
      "supports": "第 9 节：良性客户端聚成最大簇这一假设的直觉解释",
      "text": "A reason for this might be that the benign models aim to strengthen the same objective and move their frequency representation in a specific direction to learn the target function."
    },
    {
      "section": "Section VII (Conclusion)",
      "supports": "第 1 节与第 9 节：论文自称采用通用攻击者模型，不假设数据分布与攻击类型或策略",
      "text": "Our defense mechanism has a generic adversary model. It does not make any assumptions about underlying data distributions or attack types/strategies and can be applied to various application domains and model architectures."
    }
  ]
}
```
