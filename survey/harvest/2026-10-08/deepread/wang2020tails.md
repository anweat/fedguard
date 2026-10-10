# wang2020tails：Attack of the Tails: Yes, You Really Can Backdoor Federated Learning

## 1. 基本信息

- **场景**：传统联邦学习（classic federated learning, FL）。论文全部实验在"模拟的联邦学习环境"（simulated FL environment）中进行，聚合方式是联邦平均（Federated Averaging, FedAvg）及其变体，不涉及联邦大模型，也不涉及参数高效微调（parameter-efficient fine-tuning, PEFT）。论文没有出现 LoRA 或任何适配器（adapter）相关内容。
- **训练阶段**：训练期（training-time）后门注入，覆盖客户端本地数据准备、本地训练、更新上传前处理三个位置；后门在评估与部署阶段被触发。
- **论文类型**：攻击（attack）。同时包含两条关于"检测不可行"的理论结果（Theorem 1、Proposition 1、Proposition 2），但没有提出任何防御或检测方法。
- **模型与数据规模**（正文第 4 节与表 1）：
  - 任务 1（Task 1）：CIFAR-10 图像分类，VGG-9，客户端总数 K = 200，每轮参与数 m = 10，数据点 50,000（表 1）；FL 过程从一个测试准确率 77.68% 的 VGG-9 模型开始（附录 A）。
  - 任务 2（Task 2）：EMNIST 数字分类，LeNet，K = 3,383，m = 30，数据点 341,873（表 1）；起始 LeNet 准确率 88%（附录 A）。
  - 任务 3（Task 3）：ImageNet（ILSVRC2012）图像分类，VGG-11，K = 1,000，m = 10，数据点 1M（表 1）；起始 top-1 准确率 69.02%（附录 A）。
  - 任务 4（Task 4）：Sentiment140 情感分类，LSTM，K = 1,948，m = 10，数据点 389,600（表 1）；起始准确率 75%（附录 A）。
  - 任务 5（Task 5）：Reddit 下一词预测（next word prediction），LSTM，K = 80,000，数据点规模表 1 记为"—"；起始准确率 18.86%（附录 A）。
  - 论文内部不一致之处：第 4 节正文写任务 5 的 m = 100，而表 1 与附录 D 写每轮 10 个活跃客户端（"there are 10 active clients in each FL-round"），此处照实并列，不做统一。
  - 本地训练轮数（表 1）：EMNIST 为 5 个 epoch，其余四个任务均为 2 个 epoch；优化器在表 1 中记为 SGD，批量大小一栏抽取出 32 与 20 两个数值但未标明对应关系，故不进一步断言。

## 2. 威胁模型

- **攻击者是谁**：联邦学习中被参数服务器（Parameter Server, PS）选中参与训练的恶意客户端。论文的表述是"a fraction of attackers, say f out of K"（第 2 节），即 K 个客户端中的 f 个。第 4 节说明攻击者参与模式分两种：固定频率（fixed-frequency，周期性参与）与固定池（fixed-pool，即随机采样，固定池中的攻击者只在自己被选中时发动攻击，同一轮可能有多个攻击者被选中）。
- **占比或数量**：第 1 节声称"as long as 0.5-1% of total number of edge users are adversarial"即可植入后门；第 4.1 节说固定池设定下攻击者占全体客户端的比例从 0.5% 到 5% 变化，图 4 的纵轴标签为"Percentage of Attackers Among All Users"，刻度标为 1 至 5。
- **能力**：论文区分两种访问模型（第 2 节）。
  - 黑盒（black-box，即数据投毒）：攻击者只能把本地数据集替换成自己选择的数据集。论文的原文是"In the black-box setting, the f attackers are assumed to be able to replace their local data set with one of their choosing."。
  - 白盒（white-box，即模型投毒）：攻击者可以把任意模型送回参数服务器。论文的原文是"In the white-box setup, the attackers are assumed to be able to send back to the PS any model they prefer."。白盒攻击者可以运行任意的本地训练算法（例如投影梯度下降，projected gradient descent, PGD），这是黑盒攻击者做不到的。
- **知识**：模型替换（model replacement）要求攻击者近似知道若干系统参数。第 1 节写明这类攻击要求"the model is close to convergence"以及"the adversary has near-perfect knowledge of a few other system parameters (i.e., number of users, data set size, etc.)"；第 2 节进一步写明攻击者"needs to know the value of nS"，其中 nS 是当轮被选中客户端的训练数据总数。论文未说明攻击者是否事先知道防御算法的具体超参数，但附录 A 记述攻击者为通过 Krum、Multi-Krum、RFA 而把投影半径 ε 从 2 缩小到 0.5 × 0.998^t 或 1.5 × 0.998^t，说明实验中攻击者是针对已知防御调参的。
- **目标**：定向后门（targeted backdoor）。攻击者选好 p-edge-case 样本集 D_edge 与目标标签，目标是让全局模型对每个 (x, y) ∈ D_edge 预测出攻击者选定的 y，同时保持在自然数据集 D 上的正确预测以免被察觉（第 2 节：攻击者的目标是"maximize the accuracy of the classifier on D ∪ D_edge"）。Remark 2 说明所提算法可以立即扩展到无目标后门攻击（untargeted backdoor attacks），但正文与实验评估的都是定向攻击。论文还强调这种攻击会不成比例地伤害少数群体，即影响公平性。
- **防御者是谁、能看到什么、信任什么**：防御者是参数服务器（论文中也叫数据中心，data center）。它能看到的量包括：自己下发的全局模型、被选中客户端返回的模型更新，以及同一轮所有更新的相互关系（第 4.1 节的五类防御都需要其中之一）。论文对防御者的信任边界给了两条明确限制：其一，"When SecAgg is in place, it is impossible for a central service provider to examine individual user models."（第 1 节，SecAgg 指安全聚合 secure aggregation）；其二，"even in the absence of SecAgg, the service provider is limited in its capacity to determine which model updates are malicious, as this may violate privacy and fairness concerns"（第 1 节）。论文在 Related Work 中还指出，基于剪枝的防御需要"clean holdout data that is representative of the global dataset"，而在 FL 场景中获取这样的数据会引发隐私问题。

## 3. 攻击入口与流程位置

这篇论文的攻击从以下三个位置进入，另有一步是在服务器聚合行为上"搭便车"。

1. **本地数据准备（客户端训练前）**。攻击者把自己原有的数据集 D 替换为 D′ = D ∪ D_edge，其中 D_edge 是 p-edge-case 样本集。第 2 节给出 D_edge 的构造方法：攻击者若已有候选边缘样本和一批良性样本，就把良性样本喂给深度神经网络，收集倒数第二层的输出向量，用聚类数等于类别数的高斯混合模型（Gaussian mixture model, GMM）拟合出一个生成模型，据此估计任意样本的概率密度并筛出低密度样本；图 2 用 MNIST 测试集与 ARDIS 训练集的对数密度对比展示了这一筛选。攻击者还可以人工收集边缘样本，例如任务 1 用 Southwest 航空公司的飞机照片、任务 2 用 ARDIS 数据集中手写的"7"、任务 3 用穿克里特传统服饰的人物照片、任务 4 用提到希腊导演 Yorgos Lanthimos 的正面推文、任务 5 用关于雅典的负面句子（第 4 节与附录 A）。第 2 节指出，D′ 中来自 D_edge 的比例要足够高，具体条件是 |D′ ∩ D_edge| > |D′ ∩ D| 或 D′ 中超过 50% 来自 D_edge。
2. **本地训练过程（客户端每步）**。黑盒攻击者只在 D′ 上按与诚实客户端相同的超参数做标准本地训练（附录 A）。白盒攻击者在 D′ = D ∪ D_edge 的损失上做投影梯度下降：先选定一个攻击预算 δ > 0，保证送回的模型满足 ||w − wi|| ≤ δ，δ 的启发式取值就是该 FL 系统的范数防御所允许的最大范数差；然后每一步做梯度更新，并周期性地把参数投影到以全局模型 w 为球心、半径 δ 的球上（第 2 节）。附录 A 记录了实现细节：不是每个 SGD 步都投影，而是每 10 个 SGD 步投影一次效果更好，并让 ε 随轮次衰减。
3. **更新上传前的后处理（模型替换）**。在 PGD 攻击的基础上，攻击者不再提交 wi′，而是提交 (nS/ni′)(wi′ − w) + w，把本地更新与上一轮全局模型的差放大 nS/ni′ 倍，其中 ni′ 是该攻击者自己的数据量（第 2 节）。论文给出这个缩放的动机：如果 w 在 D 上接近收敛，每个诚实客户端 i ∈ S \ {i′} 都会送回 wi ≈ w，于是全局更新近似等于 wi′，也就是整体被替换。若同时使用 PGD，攻击者会预先缩小 ε，使得缩放之后仍在范数阈值之内（附录 A）。第 4.1 节补充：在 Krum 下论文没有做"PGD 加模型替换"，因为一旦中毒模型被 Krum 选中，它自动获得模型替换的效果。
4. **服务器聚合**。攻击者不修改服务器代码，但依赖加权平均这一聚合规则；同时论文显示 Krum 的选点行为反而可能帮攻击者，因为它可能忽略诚实更新而接受后门更新（第 4.1 节）。
5. **评估与部署**。攻击者不干预评估，但由于边缘样本"不存在于原数据集的训练集与测试集中"（第 4 节），常规评估看不出异常，触发条件就是这类输入本身。

## 4. 方法原理

- **边缘样本的形式化**。Definition 1：设 X ∼ PX，一个带标签样本集合 D_edge = {(xi, yi)}i 称为 p-edge-case 样本集，如果对每个 (x, y) ∈ D_edge 都有 PX(x) ≤ p，其中 p > 0 且很小（第 2 节）。直观上，输入特征取自特征分布的重尾。论文说明对标签没有约束。Remark 1 说明刻意排除 p = 0 的情形，因为已知的分布外（out-of-distribution）检测比尾部样本检测更容易。
- **攻击目标**。给定 D_edge，f 个攻击者的目标是让全局模型对所有 (x, y) ∈ D_edge 预测 y，同时保持在自然数据集 D 上的正确预测，也就是最大化模型在 D ∪ D_edge 上的准确率（第 2 节）。
- **三种攻击策略**（第 2 节）。(a) 黑盒攻击：不做任何训练算法修改，只在精心构造的 D′ 上做标准本地训练。(b) PGD 攻击：在 D′ 的损失上做投影梯度下降，周期性投影回以全局模型为中心、半径 δ 的球内，以避免因训练过久而与诚实客户端差异过大而被范数裁剪拦下。(c) 带模型替换的 PGD 攻击：在 (b) 的基础上加前述缩放，并用缩放后的范数预算来约束投影。
- **FedAvg 的更新式**（第 2 节）：服务器按 w_next = w + Σ_{i∈S} (ni/nS)(wi − w) 聚合，其中 ni = |Di|，nS = Σ_{i∈S} ni。
- **Theorem 1（对抗样本蕴含后门）**（第 3 节及附录 E）。假设某一层 l 的激活矩阵满足 X(l)X(l)^T 可逆，记 ρ(l) 为 X(l) 的最小奇异值。如果模型存在 ε-对抗样本，则存在后门权重 W′，且 max_{x∈D_edge, x′∈D} |Wl·(x+ε(x))(l)| / |x(l) − x′(l)| ≤ ||Wl − W′l|| ≤ ε√|D_edge| / ρ(l)。证明思路是在单层上求解 Δl X(l)^T = Wl El（其中 El 是只有边缘样本列非零的扰动矩阵），取最小范数解 Δl = Wl El (X(l)X(l)^T)^{-1} X(l) 并逐层放缩。上界说明防御后门至少和防御对抗样本一样难；下界说明当良性数据点与后门数据点在该层的激活距离接近零时这个构造不成立，这间接论证了应当使用边缘样本。附录 E 的 Remark 说明该证明可直接扩展到无目标攻击。
- **Proposition 1（后门检测的困难性之一）**（第 3 节及附录 E）。可以构造一个 ReLU 网络把 3-SAT 归约到"f 是否在 [0,1]^n 上恒等于 g"这一判定问题，因此检查 f ≡ g 是 NP-hard。论文把该判定问题称为 Backdoor。
- **Proposition 2（后门检测的困难性之二）**（第 3 节及附录 E）。若数据在 [0,1]^n 上均匀分布，可以构造两个单神经元网络 f 与 g，使得 f 相对 g 的后门位于集合 B = {x ∈ [0,1]^n : 1^T x ≥ n/2} 上；由 Hoeffding 不等式 P(B) ≤ e^{−n/2}，即后门区域测度指数级小。f 与 g 在该区域之外函数值与梯度完全相同，因此任何基于梯度的方法除非初始化就落在后门区域内，否则找不到它。
- **模型替换的推导**（第 2 节）。假设 w 在 D 上几乎收敛，则 w_next ≈ w + Σ_{i∈S} (ni/nS)(wi − w) ≈ wi′，也就是说缩放后的攻击者更新主导了聚合结果。

## 5. 检测或防御所需的数据

本文是攻击论文，因此下面写它留下的可观测量、它需要的数据，以及它声称能够绕过的检测。

**攻击侧需要的数据**
- **边缘样本集 D_edge**：由攻击者自备。粒度是逐样本；采集位置在客户端训练前。它可以人工收集，也可以借助良性样本做筛选：把良性样本做一次前向传播、取倒数第二层输出并拟合 GMM，因此需要干净参考数据（良性样本）和额外的前向计算（第 2 节，图 2）。
- **本地混合数据集 D′**：粒度是逐样本，位于客户端训练前；要求 D_edge 占比超过一半（第 2 节）。
- **上一轮全局模型 w 与自身数据量 ni′、当轮选中客户端数据总量 nS**：用于模型替换的缩放，位置在客户端训练后、上传前（第 2 节）。

**防御侧可以看到、攻击会在其上留下痕迹的量**
- **每个客户端返回的模型更新**：逐客户端，服务器收到更新时。非 SecAgg 场景下可见。白盒攻击者可以把它设成任意值，因此这个视图本身不构成充分检测依据。
- **全局模型与更新的范数差**：逐客户端、逐轮，服务器收到更新时。这是范数差裁剪（norm difference clipping, NDC）使用的量。论文的 NDC 阈值设置为任务 1、2 用 2，任务 4 用 1.5（附录 A）。攻击者把该量控制在预算 δ 内来规避检测，图 3(a)、图 15(a) 与图 12(b) 展示了攻击者与诚实客户端的范数差对比。
- **同一轮内各客户端更新之间的几何关系**：逐客户端、逐轮，服务器聚合时。Krum 与 Multi-Krum 依据"哪一家的更新在几何上最接近所有用户更新的总体"来选点，RFA（robust federated aggregation）用平滑 Weiszfeld 算法（smoothed Weiszfeld's algorithm）求加权几何中位数。这需要同一轮全部参与客户端的更新，且需要额外的距离计算。
- **聚合后的全局模型**：粒度是整个模型，服务器聚合后。弱差分隐私（weak differential privacy, weak DP）防御就是在它上面加高斯噪声。
- **逐层权重**：Theorem 1 的后门构造只改动一层权重矩阵 Wl，扰动为 Δl，粒度是逐层、来源是服务器收到的更新（第 3 节与附录 E）。
- **跨轮更新历史**：论文显示攻击可以在很低的攻击频率下逐轮缓慢注入（第 4.1 节与图 4），因此只看单轮不足以发现它，需要逐轮、跨轮的历史视图。
- **按客户端或子群体划分的评估准确率**：评估阶段。论文用准确率均等（Accuracy Parity）派生的 AP ratio = p_min / p_max 来度量公平性（第 4.1 节、图 8），该实验让客户端 0 额外持有 588 张正确标注为"airplane"的 WOW Airlines 图片，因此这一视图需要代表各客户端分布的干净留出数据。
- **代表全局分布的干净留出数据**：论文在 Related Work 中指出，基于剪枝的防御（pruning defenses）依赖"clean holdout data that is representative of the global dataset"，并说明在 FL 中获取这样的数据会引发隐私问题。论文没有使用这类防御做实验。

**论文声称能够绕过的检测，以及绕过的条件**
- 白盒 PGD 攻击（带或不带模型替换）在"carefully tuned norm constraints"下可以通过所有考察的防御（第 4.1 节、图 6，任务 1 与任务 4；任务 2 见附录 E 的图 13）。附录 A 给出的调参是：任务 1 不带替换时投影半径从 ε = 2 缩小为 0.5 × 0.998^t 或 1.5 × 0.998^t，带替换时任务 1 对 NDC 用 ε = 0.1、对其余防御用 ε = 0.083，任务 2 对 NDC 用 ε = 0.3、对其余防御用 ε = 0.25，任务 4 用固定 ε = 1.0（不带替换）或 0.01（带替换）。
- Krum 不但没有防住，反而可能增强攻击（第 4.1 节、图 6(a)）。
- 黑盒攻击对 NDC 与 RFA 仍然有效，但难以通过 Krum 与 Multi-Krum（第 4.1 节、附录 E 的图 14、图 13）；在任务 4 上黑盒攻击能通过 Multi-Krum 但过不了 Krum（第 4.1 节）。
- 论文主张在一般情况下检测后门是不可能的：Proposition 1 说明判定 f ≡ g 是 NP-hard，Proposition 2 说明藏在指数小测度区域的后门无法被梯度方法找到。论文没有给出任何具体的检测器或检测算法。

## 6. 干预动作

- **论文本身不提出任何防御干预**。它的"动作"全部发生在攻击侧：在客户端训练前替换本地数据集、在客户端训练中用 PGD 投影约束与全局模型的距离、在上传前按 nS/ni′ 缩放更新向量。这些动作分别位于客户端与客户端到服务器的上传路径上，服务器侧没有任何干预。
- **论文分析并击破了四种服务器侧干预**（第 4.1 节与附录 A）：
  - NDC：数据中心比较下发模型与收回更新之间的范数差，用预设阈值裁剪超限更新；位置在服务器收到更新时。
  - Krum 与 Multi-Krum：从更新中选出几何上最接近其它更新的一个（Krum）或 m 个（Multi-Krum）；位置在服务器聚合时，效果等同于剔除其余客户端。Multi-Krum 的超参数取 m = n − f（附录 A）。
  - RFA：用平滑 Weiszfeld 算法计算加权几何中位数来做聚合；位置在服务器聚合时，参数为平滑因子 υ = 10^{−5}、容错阈值 ε = 10^{−1}、最大迭代次数 T = 500（附录 A）。
  - 弱 DP：在聚合后的全局模型上加小标准差 σ 的高斯噪声；位置在服务器聚合后。附录 A 记录 σ = 0.005 用于任务 1，另外还有 σ = 0.001 与 0.002 两处，论文原文两处都写作"Task 1"，疑为笔误，此处照实记录。
- **论文报告的干预副作用**：Krum 从不选中持有 Southwest Airline 样本的客户端（包括攻击者与前 10 个诚实客户端），Multi-Krum 只在同轮出现多个持有该类样本的诚实客户端时才偶尔选中它们（第 4.1 节、图 7(a)(b)）；弱 DP 在加大噪声时会同时损害整体测试准确率与"airplane"类准确率，而 Southwest Airplane 的准确率下降幅度大于原始任务（第 4.1 节、图 7(c)，噪声水平横轴为 0.0005 至 0.0030）。论文没有提出任何补救动作。

## 7. 实验设置与主要结果

- **数据划分**（第 4 节）：任务 1 至 3 通过 pk ∼ DirK(0.5) 采样并按比例分配每个类别的数据给本地用户，从而模拟异质（非独立同分布）划分；任务 4 取 Sentiment140 的 25% 随机子集后均匀随机划分；任务 5 中每个 Di 对应一个真实 Reddit 用户的数据。第 4.1 节的 AP ratio 实验改用 CIFAR-10 在 90 个客户端上的独立同分布划分，并假设所有可用客户端每轮都参与。
- **恶意比例与参与模式**（第 4 节、第 4.1 节）：固定频率设定下攻击频率在 0.01 至 1 之间变化；固定池设定下攻击者占全体客户端的比例在 0.5% 至 5% 之间变化；防御对比实验采用每 10 轮攻击一次的固定频率设定。论文只考虑攻击者彼此独立，不考虑共谋。
- **评价指标**：目标（后门）任务的测试准确率、主任务的测试准确率、范数差 ||Wp − Wg||、以及公平性指标 AP ratio = p_min/p_max。
- **关键结果**（均带图号）：
  - 图 3：任务 1 上按 D′ 中干净数据比例变化的范数差与最终准确率；正文指出边缘数据太少会导致攻击效果弱，并称过纯的边缘数据集也会导致攻击效果弱；附录 D 对任务 1 却报告"the pure edge-case dataset leads to slightly better attacking effectiveness"，两处表述不一致，此处照实并列。
  - 图 5：把 D_edge 在攻击者与诚实客户端之间按 100%/0%、50%/50%、10%/90% 三种方式分配，五个任务的攻击效果都随诚实客户端持有边缘样本的比例上升而下降；论文认为原因是诚实客户端的本地训练"erases"了后门，但即使 p = 50，攻击仍然相对强。
  - 图 6：任务 1（上排）与任务 4（下排）在 Krum、Multi-Krum、RFA、NDC 下的攻击效果；白盒攻击通过所有防御，Krum 反而增强攻击。
  - 图 7：任务 1 上 Krum 与 Multi-Krum 的客户端被选中频次，以及弱 DP 在不同噪声水平下对主任务、目标任务、带干净标签的边缘样本、原始 CIFAR-10 airplane 类的影响。
  - 图 8：任务 1 上 Krum 防御与无防御时的 AP ratio 随轮次变化；正文解释 Krum 带来鲁棒性是因为攻击者不被选中，但它同时拒绝客户端 0，导致 WOW Airlines 样本分类差、AP ratio 低。
  - 图 4：攻击频率与攻击者比例的影响；正文指出更低的攻击频率会减慢注入速度，但只要 FL 过程跑得足够久，攻击者仍能逐步注入后门。
  - 图 10：任务 1 用把 VGG-9 卷积层宽度乘以 k = 0.5、1、2 的方式改变容量，任务 4 用嵌入维度与隐藏维度 D ∈ {25, 50, 100, 200} 改变容量；正文指出 D ≥ 100 时攻击容易注入，容量下降会变难，但降低容量也会损害主任务性能。
  - 图 11：任务 5 上更多后门句子的边缘与非边缘情形；附录 D 说明 50% 与 90% 诚实样本设定是分别把对应的正面句子随机分发 40,000 次与 72,000 次给共 80,000 个客户端。
  - 图 12：任务 1 的数据划分直方图，以及第一轮中本地数据量越大则范数差越大。
  - 附录 E 的图 13 为 EMNIST 上的防御效果，图 14 为黑盒攻击下各防御的效果，结论是 NDC 与 RFA 只是减慢注入，攻击者频繁参与多轮后仍能注入。

## 8. 开销

论文未报告计算、通信或存储开销。可查到的只有定性描述与基础设施信息：实验在 Amazon EC2 的 p2.xlarge 实例上用 PyTorch 实现（附录 A）；PGD 攻击每 10 个 SGD 步做一次投影（附录 A）；模型替换需要攻击者知道 nS（第 2 节）；RFA 的最大迭代次数设为 500（附录 A），这是防御侧参数而非开销测量。没有任何关于运行时、通信字节数或内存占用的数值。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**
- 服务器使用 FedAvg 式的按样本数加权平均，或论文评估的 NDC、Krum、Multi-Krum、RFA、弱 DP 之一（第 2 节、第 4.1 节）。
- 白盒攻击者能在本地运行任意训练算法（含 PGD 与投影）；黑盒攻击者只能替换本地数据集（第 2 节）。
- 模型替换要求全局模型接近收敛，且攻击者近似知道用户数、数据集大小、nS 等系统参数（第 1 节、第 2 节）。
- 攻击者能拿到 p-edge-case 样本，并有良性样本可用于拟合 GMM 来估计密度（第 2 节）。
- D′ 中 D_edge 的比例要足够高，具体是 |D′ ∩ D_edge| > |D′ ∩ D| 或超过 50%（第 2 节）。
- 边缘样本基本只由攻击者持有；诚实客户端若持有同样的边缘样本且标签正确，本地训练会削弱后门（第 4.1 节、图 5）。
- 检测困难的理论结论依赖额外条件：Theorem 1 要求某层激活矩阵 X(l)X(l)^T 可逆，Proposition 2 假设输入在 [0,1]^n 上均匀分布且网络为 ReLU（第 3 节、附录 E）。
- 攻击者之间不共谋（第 4 节：论文只考虑独立攻击）。

**论文自述的局限**
- 论文明确不声称攻击对所有防御都成立："We remark that we do not claim that our attacks are robust to any defense mechanism, and leave the existence of one as an open problem."（第 5 节）。
- 黑盒攻击在给予系统最小访问权限的前提下对 Krum 与 Multi-Krum 无效（第 4.1 节"Weakness of the suggested edge-case attack"）。
- 攻击需要足够的轮数与参与频率才能逐步注入（第 4.1 节）。
- 低容量模型更难注入后门，但降低容量会牺牲主任务准确率（第 4.1 节）。
- 论文提出的防御分析显示 Krum、Multi-Krum 与弱 DP 会伤害持有尾部数据的诚实客户端，形成公平性与鲁棒性的权衡（第 4.1 节）。
- 论文未说明在 SecAgg 下攻击是否仍然可行，也未在 SecAgg 下做任何实验；论文只在第 1 节用它来论证集中式检查单个模型不可行。

**是否评估了自适应攻击者**：论文没有使用"自适应攻击者"这一术语，也没有做自适应防御的博弈实验，但它确实针对每一种已知防御调整了攻击超参数。附录 A 原文记述：在防御 Krum、Multi-Krum 与 RFA 时，原先的 ε = 2 无法通过，"Thus we shrink ε to hide among the updates of honest clients"，并进一步对 ε 做衰减；带模型替换时也预先缩小 ε 以抵消缩放带来的范数增长。分析：这属于对固定防御的自适应规避，但不构成"防御方针对该攻击再设计防御"的自适应评估，因此只能算单向自适应。

**迁移到联邦 LoRA 微调时可能不成立的假设（分析：）**
- 分析：论文的聚合对象是完整模型权重，而 LoRA 微调只上传低秩增量矩阵。模型替换依赖把完整权重差放大 nS/ni′，这一缩放在低秩增量上是否等效，论文未说明，需要重新推导。
- 分析：NDC 的阈值（任务 1、2 为 2，任务 4 为 1.5）是在全参数模型的范数差上标定的，LoRA 增量的范数量级与之不同，直接沿用会让裁剪要么形同虚设要么误伤诚实客户端。
- 分析：Krum、Multi-Krum 与 RFA 依赖更新向量之间的几何距离，LoRA 增量所处的低维子空间与全参数空间的距离结构不同，这些鲁棒聚合器在 LoRA 上的行为需要重新验证。
- 分析：论文报告 0.5% 至 1% 的恶意客户端即可植入后门，这一比例建立在 K 从 200 到 80,000 的大规模客户端池上；联邦大模型微调的实际客户端数往往小得多，同样的百分数可能连一个恶意客户端都不到，威胁模型需要按绝对数量重写。
- 分析：论文的触发条件是"自然但罕见"的输入，对图像与短文本可由攻击者人工收集；在大模型微调中尾部数据的定义、触发形式的自然性以及后门在预训练知识之上的存活能力，论文都未涉及，论文也没有涉及越狱或安全对齐破坏这类目标。
- 分析：论文用的是从随机初始化或已训练 checkpoint 出发、词表固定的 LSTM 与卷积网络，没有 tokenizer、指令微调与适配器发布链路，因此参数高效微调供应链（例如适配器或模型发布者作为攻击者）这一入口在论文中完全不存在。
- 分析：论文的防御对比都假设服务器能看到单个客户端的更新；在 LoRA 增量配合 SecAgg 的场景下，这一前提不成立，论文未给出替代方案。

## 10. 对防护库设计的含义

以下全部标"分析："。

- 分析：采集底座需要提供的最小通用视图是"服务器收到更新时"的逐客户端、逐层原始更新张量，以及同一轮全部参与客户端的更新集合，因为 NDC 需要全局模型与更新的差、Krum 与 Multi-Krum 需要成对几何距离、RFA 需要几何中位数；这三类视图与具体攻击无关，应当在底座里默认采集。
- 分析：这篇论文特有的采集需求是把"更新缩放"当作一等可观测量。模型替换的系数是 nS/ni′，因此服务器钩子必须暴露当轮被选中客户端名单、每个客户端的样本数 ni 与总量 nS；通用库通常不暴露这些量，而不暴露就既无法复现该攻击，也无法为"缩放检测"类插件提供输入。
- 分析：干预接口应当覆盖裁剪、剔除或选择、几何中位数重加权、聚合后加噪四类动作，并允许它们挂在服务器聚合钩子上；但按本文结果，这四类接口在白盒 PGD 攻击者面前都不构成安全保障，所以库应把它们标注为"可插拔但不保证鲁棒"，并把各自的阈值与预算（例如范数阈值、ε 衰减策略）作为可审计的配置项记录。
- 分析：公平性视图是这篇论文的强需求。图 7 与图 8 显示基于剔除的插件会系统性拒绝持有尾部数据的诚实客户端，因此任何过滤类插件都应同时输出被拒绝客户端的清单、被拒绝数据上的准确率以及 AP ratio 这类公平性指标，避免把数据多样性当作恶意；这一需求在通用防护库里同样值得保留。
- 分析：跨轮历史视图是通用需求但常被忽略。图 4 与附录 E 的图 14 表明低频率攻击能在很多轮里逐步注入，因此底座需要按轮保存逐客户端更新的摘要（范数、与其他更新的距离、是否被聚合器选中），供插件做趋势判断。
- 分析：若库同时要支持 LoRA 场景，底座需要把"参数化类型"作为采集与干预的维度（例如逐层的低秩增量与全参数更新分开处理），并让阈值按参数化类型重新标定；同时应在设计文档中明确 SecAgg 是否开启，因为一旦开启，Krum、NDC 与几何中位数类插件全部失效，此时能用的只有聚合后层面的干预或仅报告。

## 11. 原文依据

1. "An edge-case backdoor forces a model to misclassify on seemingly easy inputs that are however unlikely to be part of the training, or test data, i.e., they live on the tail of the input distribution."（Abstract）——支撑第 1 节与第 4 节对 edge-case backdoor 的定义。
2. "that our edge-case attacks can be hard-wired in FL models, as long as 0.5-1% of total number of edge users are adversarial"（第 1 节，Contributions）——支撑第 2 节的攻击者占比与第 7 节的规模设定。
3. "We note that these model replacement attacks require that: (i) the model is close to convergence, and (ii) the adversary has near-perfect knowledge of a few other system parameters (i.e., number of users, data set size, etc.)."（第 1 节）——支撑第 2 节的知识假设与第 9 节的成立条件。
4. "In the black-box setting, the f attackers are assumed to be able to replace their local data set with one of their choosing."（第 2 节）——支撑第 2 节的能力划分与第 3 节的本地数据入口。
5. "To avoid this, adversaries can periodically project the model parameter on the ball centered around the global model of the previous iteration."（第 2 节）——支撑第 3 节与第 4 节中 PGD 攻击的本地训练入口与投影机制。
6. "Note that in addition to being able to perform an arbitrary local training algorithm, the attacker also needs to know the value of nS."（第 2 节）——支撑第 4 节的模型替换与第 10 节服务器必须暴露 nS 的采集需求。
7. "If a model is susceptible to inference-time attacks in the form of input perturbations (i.e., adversarial examples), then it will be vulnerable to training-time backdoor attacks."（第 1 节，Theorem 1 的非正式表述）——支撑第 4 节的理论依据。
8. "Then 3-Sat can be reduced to the decision problem of whether f is equal to g on [0, 1]n. Hence checking if f ≡g on [0, 1]n is NP-hard."（第 3 节，Proposition 1）——支撑第 5 节关于检测在计算上不可行的论断。
9. "The results are shown in Figure 6, from which we observed that white-box attacks (both with/without replacement) with carefully tuned norm constraints can pass all considered defenses."（第 4.1 节）——支撑第 5 节与第 7 节关于白盒攻击绕过全部被测防御的结论。
10. "Krum never selects the model updates from clients with Southwest Airline examples (i.e. both honest client 1 − 10 and the attacker)."（第 4.1 节）——支撑第 6 节与第 7 节关于剔除类防御伤害持有尾部数据的诚实客户端的结论。

```json
{
  "key": "wang2020tails",
  "title": "Attack of the Tails: Yes, You Really Can Backdoor Federated Learning",
  "year": 2020,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {"what": "客户端返回的本地模型更新，白盒攻击者可以设为任意模型", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "全局模型与客户端更新之间的范数差，NDC 用阈值裁剪", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "同一轮全部参与客户端更新之间的几何距离，用于 Krum 与 Multi-Krum 打分和 RFA 的几何中位数", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "聚合后的全局模型，弱 DP 在其上加高斯噪声", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐层权重扰动，Theorem 1 的后门构造只改动一层权重矩阵", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "跨轮更新序列，低攻击频率下后门是逐轮缓慢注入的", "where": "server_receive", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "攻击者自备的边缘样本集，由人工收集或用良性样本的倒数第二层激活拟合高斯混合模型筛出", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "按客户端或子群体划分的测试准确率，用于计算 AP ratio 公平性指标", "where": "evaluation", "granularity": "client", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "服务器采用 FedAvg 式按样本数加权平均，或采用论文评估的 NDC、Krum、Multi-Krum、RFA、弱 DP 之一",
    "白盒攻击者能在本地运行任意训练算法并做投影，黑盒攻击者只能替换本地数据集",
    "模型替换要求全局模型接近收敛，且攻击者近似知道用户数、数据集大小与当轮参与客户端数据总量 nS",
    "攻击者能获得自然但罕见、不在原训练与测试集中的 p-edge-case 样本，并有良性样本可用来拟合密度模型",
    "构造的本地数据集 D-prime 中来自 D-edge 的样本比例超过一半",
    "边缘样本基本只由攻击者持有，诚实客户端持有同类样本且标签正确会削弱后门",
    "检测困难的理论结论依赖 ReLU 网络、某层激活矩阵可逆、输入在单位超立方体上均匀分布等条件",
    "攻击者之间不共谋，论文只考虑独立攻击"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节与第 4 节对 edge-case backdoor 的定义", "text": "An edge-case backdoor forces a model to misclassify on seemingly easy inputs that are however unlikely to be part of the training, or test data, i.e., they live on the tail of the input distribution."},
    {"section": "1 Introduction, Contributions", "supports": "第 2 节攻击者占比与第 7 节规模设定", "text": "that our edge-case attacks can be hard-wired in FL models, as long as 0.5-1% of total number of edge users are adversarial"},
    {"section": "1 Introduction", "supports": "第 2 节知识假设与第 9 节成立条件", "text": "We note that these model replacement attacks require that: (i) the model is close to convergence, and (ii) the adversary has near-perfect knowledge of a few other system parameters (i.e., number of users, data set size, etc.)."},
    {"section": "2 Edge-case backdoor attacks for Federated Learning", "supports": "第 2 节能力划分与第 3 节本地数据入口", "text": "In the black-box setting, the f attackers are assumed to be able to replace their local data set with one of their choosing."},
    {"section": "2 Edge-case backdoor attacks for Federated Learning", "supports": "第 3 节与第 4 节 PGD 攻击的本地训练入口与投影机制", "text": "To avoid this, adversaries can periodically project the model parameter on the ball centered around the global model of the previous iteration."},
    {"section": "2 Edge-case backdoor attacks for Federated Learning", "supports": "第 4 节模型替换与第 10 节服务器需暴露 nS", "text": "Note that in addition to being able to perform an arbitrary local training algorithm, the attacker also needs to know the value of nS."},
    {"section": "1 Introduction, Theorem 1 informal", "supports": "第 4 节理论依据", "text": "If a model is susceptible to inference-time attacks in the form of input perturbations (i.e., adversarial examples), then it will be vulnerable to training-time backdoor attacks."},
    {"section": "3 Backdoor attacks exist and are hard to detect, Proposition 1", "supports": "第 5 节关于检测在计算上不可行的论断", "text": "Then 3-Sat can be reduced to the decision problem of whether f is equal to g on [0, 1]n. Hence checking if f ≡g on [0, 1]n is NP-hard."},
    {"section": "4.1 Experimental results", "supports": "第 5 节与第 7 节白盒攻击绕过全部被测防御", "text": "The results are shown in Figure 6, from which we observed that white-box attacks (both with/without replacement) with carefully tuned norm constraints can pass all considered defenses."},
    {"section": "4.1 Experimental results", "supports": "第 6 节与第 7 节剔除类防御伤害持有尾部数据的诚实客户端", "text": "Krum never selects the model updates from clients with Southwest Airline examples (i.e. both honest client 1 − 10 and the attacker)."}
  ]
}
```
