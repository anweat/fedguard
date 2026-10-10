# yin2018median：Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates

## 1. 基本信息

**场景**：传统联邦学习意义上的主从式分布式统计学习（classic federated learning / distributed statistical learning），由一个 master 机器和 m 个 worker 机器组成。论文在引言中明确以联邦学习（Federated Learning）为动机，指出联邦学习把数据拥有者的设备当作 worker 机器、更去中心化、更容易受到恶意协同攻击，但论文本身并没有使用"联邦学习"的正式训练框架（没有客户端采样、没有安全聚合、没有差分隐私），也没有涉及大语言模型或参数高效微调（parameter-efficient fine-tuning, PEFT）。因此它既不是联邦大模型微调，也不是集中式大模型训练，更不是适配器供应链场景。

**训练阶段**：分布式经验风险最小化（empirical risk minimization, ERM）的迭代训练。每一轮包含三个动作：master 广播当前全局参数、worker 在本地数据上计算本地经验风险的梯度、master 用鲁棒算子聚合梯度并做一次梯度下降更新（Algorithm 1）。论文另外提出一个一次通信（one-round）变体：worker 在本地算出经验风险最小化器（ERM），master 对这些本地解做坐标级中位数（Algorithm 2）。

**论文类型**：防御。它提出的是与具体攻击无关的鲁棒聚合算法（robust aggregation），并给出统计误差率的上界与下界，附带小规模图像分类实验。论文不做检测（detection），不训练检测器，也不与任何检测器比较。

**模型与数据规模**：理论部分的规模是：m 个 worker 机器，每个 worker 有 n 个数据点，共 nm 个数据点，参数维度 d，其中 α 比例的 worker 是拜占庭（Byzantine）机器。实验部分使用 MNIST 数据集（LeCun 等，1998），共 60,000 个训练样本，随机均分给 m 台机器（Section 7）；多分类逻辑回归（multinomial logistic regression）在 m = 40 时使用（Table 2），卷积神经网络（convolutional neural network, CNN）在 m = 10 时使用（Table 3），一次通信算法实验使用 m = 10（Table 4）。需要说明的是，本全文对应 arXiv:1803.01498v2，标注日期为 2021 年 2 月 25 日，但论文的 key 与初版年份为 2018。

## 2. 威胁模型

**攻击者是谁**：恶意客户端，即论文所说的拜占庭 worker 机器。Section 3 写明：m 台 worker 中有 α 比例是拜占庭机器，其余 1 − α 比例是正常机器；拜占庭机器集合记为 B，满足 |B| = αm。

**占比或数量**：占比为 α。理论结果要求 α 显著小于二分之一（条件 (2) 与 Theorem 4 中的 α ≤ β ≤ 1/2 − ε）。实验中的取值为 α = 0.05（Table 2）、α = 0.1（Table 3、Table 4）。

**能力（能改什么）**：拜占庭机器不必遵守主从通信协议，可以向 master 发送任意消息；它们可以完全知晓整个系统和所用的学习算法，并且可以互相勾结（collude）。在 Algorithm 1 中，正常机器的输出是本地经验风险的梯度 ∇F_i(w_t)，而拜占庭机器的输出记作任意向量"∗"。实验中的具体做法是在本地数据上做标签篡改，然后照常训练或照常计算梯度。

**知识（知道什么）**：论文明确说明拜占庭机器可以有"complete knowledge of the system and learning algorithms"（Section 3）。论文没有说明拜占庭机器是否能读取其他正常机器的本地数据，也没有说明它们是否知道当前轮其他机器的消息；这些属于"论文未说明"。

**目标**：无目标破坏（untargeted），即通过任意消息拖慢收敛、降低全局模型精度。论文没有考虑定向后门（backdoor）、越狱或安全对齐破坏（jailbreak / safety alignment）、隐私窃取（privacy）等目标，实验中也只报告了测试准确率的下降。

**防御者是谁、能看到什么、信任什么**：防御者是 master 机器（服务器）。它能看到的量是每一轮每一个 worker 上传的 d 维向量，以及它自己维护并广播的全局参数；它不需要看到任何客户端的原始数据。它信任的是：至少 1 − α 比例的 worker 会按协议在本地数据上计算经验风险梯度，master 自身诚实执行协议，以及数据是独立同分布地采样自同一分布。使用截尾均值（trimmed mean）时，防御者额外需要一个关于 α 的已知上界 β，论文说明 β 可以是 α 的任意上界以保证鲁棒性，但 β 取过大会让理论界变松、性能次优（Section 4.3 与 Table 1）。使用坐标级中位数（coordinate-wise median）时不需要知道 α（Table 1 中"α known?"一行，median 为 No，trimmed mean 为 Yes）。

## 3. 攻击入口与流程位置

这篇论文是防御论文，它所针对的攻击入口可以分成理论与实验两条线来写。

**理论上的攻击入口是"更新上传"这一环**。Section 3 说明拜占庭机器可以不遵守协议、向 master 发送任意消息；Algorithm 1 中拜占庭机器的本地梯度被记作任意向量"∗"。也就是说，论文允许攻击者在服务器就要聚合的那一刻，把该客户端本应上传的梯度整体替换为任意 d 维向量，包括做任意的缩放、投影、拼装或者完全脱离数据构造的向量。论文没有规定这些恶意消息如何生成。

**实验中的攻击入口是"本地数据准备"加"本地训练"**。Section 7 写明，在第一个实验里把拜占庭机器上的每一个训练标签 y 替换为 9 − y（例如 0 替换为 9、1 替换为 8，依此类推），然后这些机器用被篡改的数据照常计算梯度并上传；在第二个（一次通信）实验里，拜占庭机器上的训练标签是从 {0, …, 9} 中独立均匀采样得到的，然后这些机器用错误数据训练本地模型。论文特别强调，它们没有在特征或梯度上加极端值，拜占庭机器发给 master 的是数值温和（moderate）的消息。

**不是攻击入口的位置**：服务器聚合、全局模型下发、评估与部署都不是论文考虑的攻击入口。论文没有在评估或部署阶段设置攻击，也没有考虑服务器被攻陷的情形（拜占庭集合 B 是 worker 集合的子集）。

具体操作步骤可以概括为：攻击者在本地数据准备阶段篡改标签，在本地训练过程中按正常流程用被篡改的数据计算梯度或本地 ERM，在把结果上传给 master 时按理论模型可以任意替换消息，之后由服务器端的鲁棒聚合承担防御。

## 4. 方法原理

**核心思想**：把联邦平均式的"对客户端消息取算术平均"替换成坐标级的顺序统计量，即坐标级中位数或坐标级截尾均值。这两个算子的崩溃点（breakdown point）接近二分之一，因此只要恶意客户端比例 α 明显小于二分之一，任意恶意的消息最多只能在每个坐标上造成有界的偏差，而不会像均值那样被单个恶意客户端任意拉偏。

**Definiton 1（坐标级中位数）**：对向量 x_i（i 属于 [m]），聚合结果 g = med{x_i : i 属于 [m]}，它的第 k 个坐标是各客户端向量第 k 个坐标的一维中位数，即 g_k = med{x_i,k : i 属于 [m]}。

**Definition 2（坐标级 β-截尾均值）**：对 β 属于 [0, 1/2) 与向量 x_i（i 属于 [m]），聚合结果 g = trmean_β{x_i : i 属于 [m]}，它的第 k 个坐标是：在去掉第 k 个坐标上最大和最小的 β 比例元素之后，对剩余元素求平均，分母为 (1 − 2β)m。

**Algorithm 1（鲁棒分布式梯度下降）**：需要初始参数 w_0、截尾参数 β（仅 Option II）、步长 η 与轮数 T。每一轮 t：master 把 w_t 发给所有 worker；每个正常 worker 计算本地经验风险梯度 ∇F_i(w_t) 并发回，拜占庭 worker 可以发任意向量；master 计算聚合梯度 g(w_t)，Option I 取坐标级中位数，Option II 取坐标级截尾均值；然后更新 w_{t+1} = Π_W(w_t − η g(w_t))，其中 Π_W 是到参数空间 W 的欧氏投影，用来保证参数留在 W 内。

**Algorithm 2（鲁棒一次通信算法）**：每个 worker 在本地数据上求经验风险最小化器 ŵ_i（拜占庭机器可以发任意值），master 对所有 ŵ_i 取坐标级中位数作为最终输出。它把通信轮数降到一轮。

**理论结果**：Theorem 1 到 Theorem 3 给出中位数版梯度下降在强凸、凸、非凸总体损失下的误差率；Theorem 4 到 Theorem 6 给出截尾均值版的对应结果；Theorem 7 给出一次通信算法在二次损失下的结果。Theorem 8 与 Theorem 11 是逐轮的均匀界，说明聚合梯度与总体梯度之差在全部 w 属于 W 上一致有界。Theorem 1 的误差上界为 Δ = O(C_ε V (α/√n + √(d log(nm bL D)/(nm)) + S/n))，其中 C_ε 由标准正态分布分位函数给出（式 (4)），在 ε = 1/6 时约等于 4；Theorem 4 的误差上界为 Δ' = O((vd/ε)(β/√n + 1/√(nm))√(log(nm bL D)))（式 (5)）。条件 (2) 大致要求 α 加上与维度、机器数、样本数有关的两项之后仍不超过 1/2 − ε。Section 6 的 Observation 1 给出下界 Ω(α/√n + √(d/(nm)))，说明 α/√n + 1/√(nm) 这两项不可改进。

**算法间的取舍**（Section 4.3 与 Table 1）：截尾均值版达到 Õ(α/√n + 1/√(nm))，对强凸损失是阶最优的，并且在每个 worker 本地样本量很小甚至 n = O(1) 时仍然有意义；中位数版多出一项 1/n，只有在 n ≳ m 时才阶最优，但它只需要梯度坐标的绝对偏度有界（比次指数尾更弱），并且不需要知道 α。

## 5. 检测或防御所需的数据

这篇论文的方法是纯防御性的鲁棒聚合，没有检测环节，因此下面列出的是"防御算法需要拿到什么数据"。

**第一项：每个客户端本轮上传的梯度向量**。
- 是什么：第 i 个 worker 在当前全局参数 w_t 处计算的本地经验风险梯度 ∇F_i(w_t)，是一个 d 维向量；论文把它按坐标独立处理，所以聚合阶段的数据视图实质上是"每轮 m 个客户端、每个客户端 d 个坐标"的矩阵。
- 在哪里采集：在客户端每步（client step）由本地数据与当前全局参数计算得到，在服务器收到更新时（server receive）被读取用于聚合。
- 粒度：逐客户端、逐轮；论文的分析粒度进一步到了逐坐标。
- 是否需要跨轮历史：不需要。Algorithm 1 每一轮只用到本轮的 m 条消息和当前的全局参数，论文的分析也是对每一轮单独建立均匀界，再对迭代做递推。
- 是否需要干净参考数据或根数据集：不需要，论文的方法完全不使用任何干净参考数据。
- 是否需要额外的前向或反向计算：不需要，用的就是正常训练本来就要算的本地梯度。
- 是否需要其他客户端的数据：客户端之间不需要互相看到数据；只有服务器需要看到全部客户端的消息（这是聚合的定义所要求的）。

**第二项：服务器当前的全局参数**。
- 是什么：第 t 轮的全局参数向量 w_t，既要广播给所有 worker，也是分析中与总体梯度 ∇F(w_t) 做比较的对象。
- 在哪里采集：服务器聚合完成后、下发之前（server post-aggregate）。
- 粒度：逐轮、逐模型（整参数向量）。
- 是否需要跨轮历史、干净参考数据、额外计算、其他客户端数据：都不需要。

**第三项：截尾均值的截尾参数 β**。
- 是什么：一个标量超参数，论文要求它是拜占庭比例 α 的任意上界，即 β ≥ α（Section 4.3 与 Theorem 4）。
- 在哪里采集：它不来自数据采集，而来自部署方对恶意客户端比例的已知上界，属于配置信息。
- 粒度：全局一个标量，逐轮可以不变。中位数版不需要这一项。

**第四项（仅一次通信算法）：每个客户端的本地 ERM 解**。
- 是什么：每个 worker 在本地数据上最小化经验风险得到的参数向量 ŵ_i，算法只上传这个向量而不是梯度。
- 在哪里采集：客户端训练后（client post-train）产生，在服务器收到更新时（server receive）用于坐标级中位数聚合。
- 粒度：逐客户端、每轮一次（实际只有一轮）。
- 其余要求同上：不需要跨轮历史、不需要干净参考数据、不需要额外计算、不需要其他客户端数据。

**第五项（仅理论分析需要、算法运行不需要的量）**：光滑常数 L_k、L、L_F，梯度方差上界 V²（Assumption 2），坐标级绝对偏度上界 S（Assumption 3），次指数常数 v（Assumption 6），强凸常数 λ_F，参数空间直径 D，以及本地经验风险强凸性（Assumption 7）。这些是论文建立误差率时假设存在的统计量，不是方法在运行时需要采集的数据；论文没有给出从数据中估计它们的步骤。

**攻击会在哪些可观测量上留下痕迹，以及论文声称能绕过哪些检测**：论文的实验攻击（标签翻转、随机标签）改变的是本地梯度，但论文明确说这些消息数值温和、没有极端值，因此"用极端范数或离群值来识别恶意客户端"的直觉在这个攻击下不成立。需要如实说明的是：论文没有评估任何检测器，也没有声称该攻击能绕过哪些具体检测方法，这部分属于"论文未说明"；它只从理论上说明，只要恶意比例满足条件，任意消息（包括刻意模仿正常客户端的消息）都不会把坐标级中位数或截尾均值的输出拉偏太多。

## 6. 干预动作

**动作内容**：论文的干预是替换服务器端的聚合算子，而不是对客户端做筛选。具体有两种：其一是坐标级中位数，对每个坐标取 m 个客户端消息的中位数；其二是坐标级 β-截尾均值，对每个坐标丢掉最大和最小的 β 比例数值后对剩余数值求平均。Algorithm 2 的干预是把"对本地 ERM 求平均"替换为"对本地 ERM 求坐标级中位数"。

**明确没有做的动作**：论文不剔除客户端（截尾是逐坐标丢值，不是识别并移除某个客户端）；不给客户端分配显式权重（截尾后剩余条目权重相同，被截掉的条目权重为零，但这由顺序统计量决定而不是由信誉或距离计算得到）；不加噪声；不裁剪到固定阈值（截尾的分界线是当前这一轮该坐标的经验分位数，而不是预设常数）；不过滤训练样本；不修复或回滚模型。唯一的额外约束是更新后做欧氏投影 Π_W，把参数拉回凸且紧的参数空间 W。

**动作发生在流程哪个位置**：全部发生在服务器端聚合这一步和紧随其后的全局更新，即 master 收到全部 worker 消息之后、广播下一轮参数之前。客户端本地训练过程完全不改动。论文没有检测阶段，因此不存在"检测之后做什么"的问题，它是无条件鲁棒聚合。

## 7. 实验设置与主要结果

**实现与平台**：实验用 TensorFlow（Abadi 等，2016）实现，运行在 Microsoft Azure 上（Section 7）。

**数据与划分**：MNIST 数据集，60,000 个训练样本，随机均分为 m 份、每份大小相同，用来代表 m 台机器上的数据（Section 7）。

**第一个实验（逐步梯度下降）**：比较四种设置，分别是 α = 0 时用均值聚合、α > 0 时用均值聚合、α > 0 时用中位数聚合、α > 0 时用截尾均值聚合。攻击方式是把拜占庭机器上的标签 y 替换为 9 − y，然后照常计算梯度；论文强调没有使用极端值。模型有两种：多分类逻辑回归（m = 40，α = 0.05，截尾均值取 β = 0.05，Table 2）与卷积神经网络（m = 10，α = 0.1，截尾均值取 β = 0.1，Table 3）；CNN 使用随机版分布式梯度下降，每次迭代每个 worker 只用本地数据的 10% 计算梯度。结果（Table 2，逻辑回归）：α = 0 均值聚合测试准确率 88.0%，α = 0.05 时均值聚合 76.8%、中位数 87.2%、截尾均值 86.9%。结果（Table 3，CNN）：α = 0 均值聚合 94.3%，α = 0.1 时均值聚合 77.3%、中位数 87.4%、截尾均值 90.7%。Figure 1 给出测试误差随并行迭代次数的变化曲线，逻辑回归画到 2000 次迭代，CNN 画到 5000 次迭代。

**第二个实验（一次通信算法）**：比较三种设置，分别是 α = 0 用均值聚合、α > 0 用均值聚合、α > 0 用中位数聚合。攻击方式是拜占庭机器上的训练标签从 {0, …, 9} 独立均匀采样，这些机器用错误数据训练本地模型。模型是多分类逻辑回归，m = 10。结果（Table 4）：α = 0 均值聚合 91.8%，α = 0.1 时均值聚合 83.7%、中位数 89.0%。论文指出，虽然一次通信算法只在二次损失下有理论保证，但在逻辑损失这类其他损失上，中位数聚合仍然提升了测试准确率。

**客户端数与参与率**：理论中 m 台机器每台 n 个样本；实验中逻辑回归 m = 40、CNN 与一次通信实验 m = 10。论文没有描述客户端采样，从 Algorithm 1 与实验描述看每一轮全部 m 台机器都参与（这属于"论文未说明客户端参与率"）；CNN 里每轮每个 worker 只用 10% 本地数据，这是对数据做子采样而不是对客户端做采样。

**轮次**：理论结果给出了达到给定精度所需轮数的表达式，例如 Theorem 1 需要 T 至少为 ((L_F + λ_F)/λ_F) log(λ_F ‖w_0 − w*‖₂/(2Δ))；Figure 1 展示的实测迭代数上限为 2000（逻辑回归）与 5000（CNN）。

**恶意比例**：α = 0.05（Table 2）与 α = 0.1（Table 3、Table 4）。

**是否非独立同分布**：论文的理论假设每个数据点独立同分布地采样自同一分布 D，实验中把 MNIST 随机均分，因此数据是独立同分布的。论文没有做非独立同分布（non-IID）划分下的实验，也没有讨论非独立同分布对方法的影响，这部分属于"论文未说明"。

**指标**：测试准确率（百分比，Table 2、Table 3、Table 4）与测试误差随迭代次数的曲线（Figure 1）。

## 8. 开销

**通信开销（论文有渐近报告）**：论文设定每一轮 worker 或 master 只能通信一个规模为 O(d) 的向量，因此总通信代价与通信轮数成正比（Section 1）。截尾均值需要一个额外的标量参数 β。一次通信算法只需要一轮通信，论文指出它在二次损失下取得了与中位数版梯度下降相似的性能，但通信代价显著更低（Section 5）。Figure 1 的横轴给出了实测的并行迭代次数上限，即 2000 次（逻辑回归）与 5000 次（CNN）。

**计算与存储开销**：论文未报告。论文没有给出坐标级中位数或截尾均值的计算复杂度分析，也没有报告运行时间、内存占用或带宽的实测数值；存储开销论文未报告。需要说明，坐标级中位数在每个坐标上要对 m 个值求中位数，截尾均值在每个坐标上要排序并去掉两端，这些在工程上都有代价，但论文没有量化。

**结论**：论文只报告了渐近的通信量级与轮数（这是它两个设计目标之一："communication efficiency: O(d) communication per round, with as few rounds as possible"），没有报告计算、存储或实测通信开销。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**：
1. 数据假设：nm 个数据点独立采样自同一未知分布 D，并且在 m 台机器间均分，每台机器持有 n 个样本（Section 3）。这是独立同分布假设。
2. 参数空间假设：参数空间 W 是凸且紧的，直径为 D（Section 3）。非强凸与非凸情形还需要额外假设 W 足够大，能包含以 w* 或 w_0 为中心的某个 ℓ₂ 球（Assumption 4 与 Assumption 5）。
3. 光滑性假设：对任意 z，单样本损失的每个偏导 ∂_k f 是 L_k-Lipschitz，单样本损失是 L-smooth，总体损失 F 是 L_F-smooth（Assumption 1）。
4. 中位数版的统计假设：梯度方差有界（Assumption 2）与每个坐标的绝对偏度有界（Assumption 3）。论文给出的线性回归例子中，均匀特征下偏度上界为 480（Proposition 1），高斯特征下为 429（Appendix A.2 的 Proposition 3）。
5. 截尾均值版的统计假设：每个坐标的偏导是 v-次指数（sub-exponential）的（Assumption 6），这比有界偏度更强。
6. 恶意比例假设：中位数版要求 α 满足条件 (2)，截尾均值版要求 α ≤ β ≤ 1/2 − ε。也就是说防御只在恶意比例明显低于二分之一时成立，这与中位数和截尾均值的崩溃点一致。
7. 攻击者假设：拜占庭机器可以任意、合谋，因此从算法角度看攻击者已经是最强的；论文不需要关于攻击具体形式的假设。
8. 通信与信任假设：每轮只传 O(d) 向量、不传原始数据；master 诚实，只防客户端；截尾均值版需要已知 α 的一个上界。
9. 一次通信算法的额外假设：损失函数必须是二次型，且 W = R^d；每个正常机器的经验风险 F_i 以概率 1 强凸（Assumption 7）。

**论文自述的局限**：
1. 维度依赖可能不是最优。Section 1.1 明确写道："In some settings the rates in these results may not have the optimal dependence on d."，并指出理解高维鲁棒分布式学习的基本极限、给出维度依赖最优的算法是有趣且重要的未来方向。
2. 一次通信算法的理论保证范围很窄。Section 5 写明："We are only able to establish such a guarantee when the loss functions are quadratic and W = R^d."。
3. 中位数版梯度下降多出一个 1/n 项，只有在 n ≳ m 时才阶最优（Section 4.1 与 Table 1）。
4. 截尾均值需要 β ≥ α；β 取过大会导致更松的界和次优性能（Section 4.3）。Section 4.2 还指出在极端情形 n = O(1) 时截尾均值版仍然有意义，而中位数版的 1/n 项会使其失效。
5. 论文在 Section 2 把为 DANE、Disco、分布式 SVRG 等更复杂算法开发拜占庭鲁棒版本列为未来方向。

**是否评估了自适应攻击者及其结果**：没有。论文的威胁模型在理论上已经允许拜占庭机器发送任意、合谋的消息，这在算法意义上覆盖了自适应攻击；但实验只用了两种静态攻击（确定性标签翻转 y 替换为 9 − y，以及标签均匀随机采样），没有任何针对自适应攻击者（例如针对中位数与截尾均值做优化的攻击）的实验，也没有报告这类结果。因此这里的结论是"论文未说明"，本文只能确认静态攻击下的测试准确率（Table 2、Table 3、Table 4）。

**迁移到联邦 LoRA 微调时可能失效的假设**：
- 分析：论文把参数当作一个扁平的 d 维向量并逐坐标独立聚合，完全没有考虑参数的矩阵结构或层结构。LoRA 的增量是低秩矩阵乘积 B·A，逐坐标取中位数或截尾均值得到的聚合增量一般不再是低秩矩阵，服务器要么重新做低秩分解，要么被迫使用稠密更新，这会改变插件的行为和开销。
- 分析：论文依赖"每个客户端的数据独立同分布采样自同一分布 D"。联邦大模型 LoRA 微调的数据通常按领域、任务或用户切分，是显著的 non-IID 场景，而论文既没有理论处理也没有实验验证 non-IID，因此 α/√n 这一项的经验意义无法直接照搬。
- 分析：论文的中位数版要求梯度坐标的绝对偏度有界，截尾均值版要求次指数尾；大模型的逐坐标梯度往往重尾，论文给出的偏度常数（480 或 429）也只在线性回归模型里证明过。因此"坐标级中位数在 LoRA 梯度上仍然稳定"这一点在论文中没有依据。
- 分析：截尾均值需要知道恶意比例的上界 β。联邦大模型微调中客户端数量、身份与参与模式都更开放（例如多身份、多适配器发布者），α 的固定上界假设更难成立；恶意比例接近或超过二分之一时，论文的两个算子都失去保证。
- 分析：论文的目标是无目标精度破坏。后门、越狱或安全对齐破坏这类定向攻击的更新未必在数值上极端，论文自己就强调攻击消息是温和的，因此坐标级中位数与截尾均值不对这类目标提供任何保证，论文也没有相关实验。
- 分析：论文的验证规模是 60,000 张 MNIST 图片上的逻辑回归与小型 CNN，一轮通信量是 O(d) 的完整梯度；LoRA 场景虽然单客户端上传量更小（只传适配器增量），但模型维度、序列长度和训练步数完全不同，论文的轮数与精度关系无法直接外推。
- 分析：论文假设服务器诚实且只防客户端。参数高效微调供应链里如果存在不可信的适配器发布者或不可信的服务器，这篇论文的威胁模型不覆盖。
- 分析：论文要求所有客户端上传的向量在同一坐标系下逐坐标可比。若不同客户端的 LoRA 秩、目标模块集合或缩放系数不同，坐标级顺序统计量就失去了可比性；论文没有讨论异构参数化。

## 10. 对防护库设计的含义

- 分析：这篇论文的方法只需要一个采集点，就是"服务器收到更新时"保存每个客户端本轮上传的原始、未聚合的更新向量（在 LoRA 场景是各目标模块的 A、B 增量），按逐客户端、逐轮、逐坐标的粒度落盘。这是通用需求，任何鲁棒聚合插件都需要未聚合的原始客户端更新，一旦底座只保存聚合结果就无法支持这类插件。
- 分析：还需要一个"服务器聚合后的全局模型"视图，用于记录本轮广播的参数与下一轮的输入；本文的方法不需要跨轮历史、不需要干净参考数据集、不需要逐样本损失、不需要隐藏层激活，也不需要客户端做额外的前向或反向计算。库可以把这些列为可选采集能力，只为本文这类插件服务时不必强求。
- 分析：插件机制需要提供一个"聚合前按坐标对齐的客户端更新矩阵"抽象，即把 N 个客户端的更新按坐标堆叠成 N × d 的视图，并允许按层或按模块分组，因为逐坐标顺序统计量必须作用在同一坐标系、同一形状的更新上。这一点是本文特有的假设；在 LoRA 场景中，插件应当显式声明哪些层或模块参与鲁棒聚合，以及秩和形状不一致时如何处理，而这部分论文没有给出方案。
- 分析：服务器钩子必须允许整体替换聚合算子，把联邦平均替换为坐标级中位数或带参数 β 的坐标级截尾均值，并允许在聚合后继续执行投影或参数合法性约束。本文的方法完全在服务器侧，客户端钩子只需保证能正常产生并上传更新，不需要在客户端做任何防御动作。这是所有鲁棒聚合插件共有的通用需求。
- 分析：库应当把"已知恶意比例上界 β"作为一类显式配置项，并记录它是否被插件使用；中位数插件不需要它，截尾均值插件需要它且 β 取值会直接影响保证强度。这也是一个可复用的通用接口，因为很多拜占庭鲁棒聚合方法都需要类似的比例参数。
- 分析：这篇论文无法支撑检测、剔除客户端、回滚模型、样本过滤或针对后门与越狱的防护，也没有给出任何检测器评估；如果库的目标包含定向后门防护，就必须另外引入逐样本损失、干净参考集、跨轮更新历史等采集点，这些都不是本文提供的能力。

## 11. 原文依据

1. 章节：Abstract。支撑：第 1 节论文类型为防御，方法是可证明鲁棒的分布式学习算法并追求最优统计性能。原文："In this paper, we develop distributed learning algorithms that are provably robust against such failures, with a focus on achieving optimal statistical performance."
2. 章节：Section 1（Introduction）。支撑：第 1 节场景定为传统联邦学习动机下的主从式分布式学习，而非大模型微调。原文："Security issues are only exacerbated in the so-called Federated Learning setting, a modern distributed learning paradigm that is more decentralized, and that uses the data owners' devices (such as mobile phones and personal computers) as worker machines"
3. 章节：Section 3（Problem Setup）。支撑：第 2 节威胁模型中拜占庭客户端可以发送任意消息、完全知晓系统与算法并且可以合谋。原文："The Byzantine machines need not obey this protocol and can send arbitrary messages to the master; in particular, they may have complete knowledge of the system and learning algorithms, and can collude with each other."
4. 章节：Section 4（Robust Distributed Gradient Descent）。支撑：第 3 节与第 5 节说明正常客户端的可观测量是按轮计算的本地梯度并在上传后被服务器读取。原文："The normal worker machines compute the gradients of their local loss functions and then send the gradients back to the master machine."
5. 章节：Section 4（Robust Distributed Gradient Descent）。支撑：第 4 节与第 6 节说明干预动作是在服务器端把聚合算子换成坐标级中位数或截尾均值再做梯度下降更新。原文："The master machine then performs a gradient descent update on the model parameter with step-size η, using either the coordinate-wise median or trimmed mean of the received gradients."
6. 章节：Section 4.1（Guarantees for Median-based Gradient Descent）。支撑：第 4 节关于中位数版在 n ≳ m 时达到阶最优误差率的论断。原文："When each worker machine has a sufficient amount of data, more specifically n ≳ m, we achieve an order-optimal error rate up to logarithmic factors."
7. 章节：Section 4.3（Comparisons）。支撑：第 2 节与第 5 节说明截尾均值需要 α 的已知上界 β，而中位数不需要知道 α。原文："Finally, the trimmed-mean operation requires an additional parameter β, which can be any upper bound on the fraction α of Byzantine machines in order to guarantee robustness."
8. 章节：Section 7（Experiments）。支撑：第 3 节与第 7 节说明实验攻击的具体做法是在本地数据上把标签 y 替换为 9 − y，然后照常计算梯度。原文："we replace every training label y on these machines with 9 − y, e.g. 0 is replaced with 9, 1 is replaced with 8, etc, and the Byzantine machines simply compute gradients based on these data."
9. 章节：Section 7（Experiments）。支撑：第 5 节关于攻击消息数值温和、不依赖极端值的论断，说明基于离群值的检测直觉不适用。原文："We also note that when generating the Byzantine machines, we do not simply add extreme values in the features or gradients; instead, the Byzantine machines send messages to the master machine with moderate values."
10. 章节：Section 5（Robust One-round Algorithm）。支撑：第 9 节关于一次通信算法的理论保证只覆盖二次损失且 W = R^d 的局限。原文："We are only able to establish such a guarantee when the loss functions are quadratic and W = Rd."

```json
{
  "key": "yin2018median",
  "title": "Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates",
  "year": 2018,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["local_data", "update_postprocess"],
  "observables": [
    {
      "what": "客户端本地计算的梯度 ∇F_i(w_t)（来自本地数据与当前全局参数）",
      "where": "client_step",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "服务器收到的每个客户端本轮上传的 d 维更新向量（坐标级聚合的直接输入）",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "聚合后得到的全局参数向量 w_t（用于广播与下一轮）",
      "where": "server_post_aggregate",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "一次通信算法中每个客户端的本地经验风险最小化解 ŵ_i",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    }
  ],
  "interventions": ["clip"],
  "intervention_where": ["server"],
  "assumptions": [
    "每台机器的 n 个样本独立同分布采样自同一分布 D，nm 个样本在 m 台机器间均分（Section 3）",
    "参数空间 W 凸且紧、直径有限（Section 3；非强凸与非凸情形另有 Assumption 4、Assumption 5）",
    "单样本损失与总体损失光滑（Assumption 1）",
    "中位数版需要梯度方差有界（Assumption 2）与坐标级绝对偏度有界（Assumption 3）",
    "截尾均值版需要各坐标偏导次指数（Assumption 6），并需要已知 α 的上界 β 且 β ≥ α",
    "拜占庭比例 α 须显著小于二分之一（条件 (2)；截尾均值要求 α ≤ β ≤ 1/2 − ε）",
    "一次通信算法的保证要求损失为二次型、W = R^d，且每个正常机器的经验风险强凸（Assumption 7）",
    "每轮只通信 O(d) 向量，服务器诚实且只防客户端，拜占庭客户端可任意发消息并合谋"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第 1 节：论文类型为防御，提出可证明鲁棒的分布式学习算法并追求最优统计性能",
      "text": "In this paper, we develop distributed learning algorithms that are provably robust against such failures, with a focus on achieving optimal statistical performance."
    },
    {
      "section": "Section 1 (Introduction)",
      "supports": "第 1 节：场景是联邦学习动机下的主从式分布式学习，不是联邦大模型微调",
      "text": "Security issues are only exacerbated in the so-called Federated Learning setting, a modern distributed learning paradigm that is more decentralized, and that uses the data owners' devices (such as mobile phones and personal computers) as worker machines"
    },
    {
      "section": "Section 3 (Problem Setup)",
      "supports": "第 2 节：拜占庭客户端可发任意消息、完全知晓系统与算法并可合谋",
      "text": "The Byzantine machines need not obey this protocol and can send arbitrary messages to the master; in particular, they may have complete knowledge of the system and learning algorithms, and can collude with each other."
    },
    {
      "section": "Section 4 (Robust Distributed Gradient Descent)",
      "supports": "第 3 节与第 5 节：正常客户端的可观测量是本地梯度，上传后由服务器读取",
      "text": "The normal worker machines compute the gradients of their local loss functions and then send the gradients back to the master machine."
    },
    {
      "section": "Section 4 (Robust Distributed Gradient Descent)",
      "supports": "第 4 节与第 6 节：干预动作是服务器端用坐标级中位数或截尾均值聚合后再更新",
      "text": "The master machine then performs a gradient descent update on the model parameter with step-size η, using either the coordinate-wise median or trimmed mean of the received gradients."
    },
    {
      "section": "Section 4.1 (Guarantees for Median-based Gradient Descent)",
      "supports": "第 4 节：中位数版在 n ≳ m 时达到阶最优误差率",
      "text": "When each worker machine has a sufficient amount of data, more specifically n ≳ m, we achieve an order-optimal error rate up to logarithmic factors."
    },
    {
      "section": "Section 4.3 (Comparisons)",
      "supports": "第 2 节与第 5 节：截尾均值需要 α 的上界 β，中位数不需要知道 α",
      "text": "Finally, the trimmed-mean operation requires an additional parameter β, which can be any upper bound on the fraction α of Byzantine machines in order to guarantee robustness."
    },
    {
      "section": "Section 7 (Experiments)",
      "supports": "第 3 节与第 7 节：实验攻击在本地数据准备阶段把标签 y 替换为 9 − y 后照常算梯度",
      "text": "we replace every training label y on these machines with 9 − y, e.g. 0 is replaced with 9, 1 is replaced with 8, etc, and the Byzantine machines simply compute gradients based on these data."
    },
    {
      "section": "Section 7 (Experiments)",
      "supports": "第 5 节：攻击消息数值温和、不用极端值，基于离群值的检测直觉不适用",
      "text": "We also note that when generating the Byzantine machines, we do not simply add extreme values in the features or gradients; instead, the Byzantine machines send messages to the master machine with moderate values."
    },
    {
      "section": "Section 5 (Robust One-round Algorithm)",
      "supports": "第 9 节：一次通信算法的理论保证只覆盖二次损失且 W = R^d",
      "text": "We are only able to establish such a guarantee when the loss functions are quadratic and W = Rd."
    }
  ]
}
```
