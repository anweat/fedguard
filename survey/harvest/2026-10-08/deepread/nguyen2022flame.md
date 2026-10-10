# nguyen2022flame：FLAME: Taming Backdoors in Federated Learning (Extended Version)

## 1. 基本信息

- **场景**：传统联邦学习（classic Federated Learning，FL）。论文研究的是横向联邦下服务器端聚合的投毒防御，应用领域为图像分类（Image Classification，IC）、词预测（Word Prediction，WP）和物联网入侵检测（Network Intrusion Detection System，NIDS）。论文没有涉及大语言模型（Large Language Model，LLM），也没有涉及 LoRA（Low-Rank Adaptation）或其他参数高效微调（Parameter-Efficient Fine-Tuning，PEFT）方法。
- **训练阶段**：联邦训练的服务器聚合阶段，即每一轮服务器收到客户端本地模型之后、聚合之前（聚类过滤与裁剪），以及聚合之后、全局模型下发之前（加噪）。论文不介入客户端的本地训练过程。
- **论文类型**：防御（defense），内部包含一个基于聚类的检测组件（模型过滤）。论文是 USENIX Security 2022 论文的扩展版，扩展内容包含第 8 节的安全两方计算（Secure Two-Party Computation，STPC）隐私保护版本、第 10 节对后续攻击的回应，以及附录 H 的 3DFed 复现研究。
- **模型与数据规模**（表 2）：词预测使用 Reddit 数据集（20.6M 条记录）与两层 LSTM 加线性输出层（约 20M 参数）；NIDS 使用 IoT-Traffic 数据集（65.6M 条记录）与 GRU 模型（约 507k 参数）；图像分类使用 CIFAR-10（60k）、MNIST（70k）和 Tiny-ImageNet（120k），对应 ResNet-18 Light（约 2.7M 参数）、CNN（约 431k 参数）和 ResNet-18（约 11M 参数）。附录 A 说明 Reddit 上每个发帖数不少于 150 且不超过 500 的用户作为一个客户端，共 80 000 个客户端，客户端数据规模在 298 到 32 660 个词之间；IoT 场景按设备类型把数据切分给 20 到 200 个客户端，每个客户端对应三小时流量、约 2 000 到 3 000 个通信包。
- **年份**：2022 年（USENIX Security 2022），本文为扩展版，arXiv 版本 v5 标注为 2023 年 8 月。

## 2. 威胁模型

- **攻击者身份**：被攻陷的恶意客户端（compromised clients）。论文假设攻击者 A 完全控制 k 个客户端及其训练数据、训练过程和参数，且 k 小于客户端总数的一半（原文记作 k < n/2，第 2.3 节）。被攻陷客户端的比例记为 Poisoned Model Rate（PMR），即 PMR = k/n（第 2.3 节）。
- **攻击者能力**：按照第 2.2 节与图 1 的分类，攻击者可以实施数据投毒（data poisoning），即修改训练数据集的标签或注入触发器；也可以实施模型投毒（model poisoning），即操纵训练过程本身并对训练得到的更新做上传前的缩放（放大以提高攻击影响，或者缩小以逃避检测），或者对训练过程施加约束以缩小恶意模型与良性模型的偏差。攻击者不能控制聚合器上的任何进程，也不能控制诚实客户端（第 2.3 节）。
- **攻击者知识**：攻击者对聚合器的操作有完全知识，包括聚合器可能部署的后门防御（第 2.3 节）。攻击者还可以通过把自己的本地恶意模型与全局模型或与一个用良性数据训练的本地模型做比较，来估计自己与良性模型之间的距离，从而判断是否低于聚合器异常检测器的区分阈值 η（第 2.3 节）。
- **攻击目标**：以定向后门（targeted backdoor）为主。攻击者希望全局模型在触发集 I_A 内的输入上输出攻击者选定的错误预测，而在触发集之外的输入上模仿未受攻击的全局模型行为（第 2.3 节，式 (1)）。第 2.3 节把这两个目标分别称为 impact（影响）与 stealthiness（隐蔽性）。论文在附录 F 另外评估了无目标投毒（untargeted poisoning），即让模型整体不可用，但明确说明这不是论文的重点。
- **防御者身份与可见信息**：防御者是聚合器 A。聚合器只能看到各客户端上传的本地模型更新，看不到客户端训练数据；聚合器不能信任客户端上报的数据集大小，因此对所有客户端采用等权聚合（第 2.1 节、第 4.3.2 节）。第 5.2 节明确说明 FLAME 不对攻击策略和客户端数据分布做特定假设。核心信任假设是良性客户端占多数（多于 50%，第 2.3 节、第 4.3.1 节、第 4.3.2 节）。
- **隐私威胁模型（第 8 节，独立于投毒威胁模型）**：考虑诚实但好奇（honest-but-curious）的聚合器，它试图从客户端模型更新中推断客户端数据的信息，FLAME 用 STPC 保护本地更新。这一部分与后门防御是正交的两个对手模型。

## 3. 攻击入口与流程位置

论文是防御论文，因此这里先写它所针对的攻击入口，再写防御自身进入流程的位置。

- **本地数据准备**：数据投毒。攻击者在被控客户端的训练集中加入投毒数据 D_A，做法包括标签翻转（例如把 30 公里限速的路标图片标成 80 公里）以及向样本中加入触发器（例如图像中的特定像素图案）并配合标签翻转（第 2.2 节、图 1）。论文用 Poisoned Data Rate（PDR）衡量投毒数据在被控客户端训练集中的比例，PDR_i = |D_A^i| / |D'_i|（第 2.2 节）。
- **本地训练过程**：模型投毒。攻击者修改训练轮数、投毒比例等超参数，或者对训练目标施加约束，使恶意模型在权重空间上更靠近良性模型，例如 constrain-and-scale 攻击（第 2.2 节、第 3 节中的 W'_3 类型）。
- **更新上传前的后处理**：模型投毒。攻击者对训练得到的更新做放大（例如 model-replacement 攻击、带模型替换的 PGD 攻击）以最大化攻击影响，或者做缩小（例如 train-and-scale）以逃避检测，见第 2.2 节与第 3 节中的 W'_2 类型。
- **FLAME 自身进入流程的位置**：全部在服务器端。服务器收到全部 n 个本地模型之后先做聚类过滤，再对被接纳的模型做裁剪，然后把裁剪后的模型等权平均，最后对平均得到的全局模型加高斯噪声并下发（算法 1 第 6 行到第 14 行，图 4）。FLAME 不改客户端训练数据，也不改客户端训练过程。

## 4. 方法原理

FLAME 由三个组件构成：动态模型过滤、自适应裁剪、自适应加噪（第 4.1 节、图 3、图 4、算法 1）。

**（一）动态模型过滤（第 4.3.1 节，算法 1 第 6 行到第 7 行）**。核心思想是把每个本地模型看成一个扁平化后的权重向量，用两两余弦距离衡量方向差异，再用 HDBSCAN 做密度聚类。余弦距离定义为 c_ij = 1 − (W_i·W_j)/(‖W_i‖·‖W_j‖)（式 (2)）。论文指出余弦距离不受攻击者放大权重的影响，因为缩放不改变向量夹角（第 4.3.1 节）。HDBSCAN 不需要预先指定簇的数量，把不属于任何高密度簇的点标为离群点；FLAME 把最小簇规模设为客户端数的至少 50%，即 n/2 + 1，于是保留下来的簇包含多数更新（论文假设多数是良性），其余模型全部作为离群点被拒（第 4.3.1 节）。与只分两类的 K-means 类方法相比，这种"每个可疑模型各自成为离群点"的做法可以同时处理多个不同后门，并减少误删良性模型（第 4.3.1 节、图 5）。论文强调聚类只剔除攻击影响大的模型（角度偏差大的 W'_1），而不追求剔除全部恶意模型（第 4.1 节、第 5.2 节）。

**（二）自适应裁剪（第 4.3.2 节，算法 1 第 8 行到第 11 行）**。服务器计算全部 n 个模型更新到上一轮全局模型 G*_{t−1} 的欧氏距离 e_i（式 (3)），取中位数作为本轮裁剪阈值 S_t；即使部分良性模型被聚类剔除，它们仍然参与中位数的计算（第 4.3.2 节）。对每个被接纳的模型 W_{b_l}，缩放系数为 γ = S_t / e_{b_l}，裁剪后的模型为 W^c_{b_l} = G_{t−1} + (W_{b_l} − G_{t−1})·min(1, γ)，即按坐标缩放（算法 1 第 11 行）。论文说明之所以动态取中位数，是因为良性更新的 L2 范数会随训练轮次下降（图 6）。

**（三）自适应加噪（第 4.3.2 节、第 5.1 节，算法 1 第 13 行到第 14 行）**。对聚合后的全局模型加高斯噪声，G*_t = G_t + N(0, σ²)，其中 σ = λ·S_t，λ = (1/ε)·sqrt(2·ln(1.25/δ))（算法 1 第 13 行、式 (7)）。

**理论部分（第 5.1 节）**。定理 1 声称：参数为 G、裁剪阈值为 S_t 的 (ε, δ)-差分隐私模型，在按 σ_G = λ·S_t 加入高斯噪声后是 backdoor-free 的。证明分两步：第一步借用差分隐私（Differential Privacy，DP）的数据隐藏性质（定义 1）与函数敏感度（定义 2，式 (4)）；第二步把集中式结论推广到联邦场景。推广的关键是式 (5) 与式 (6)：若给每个本地模型加独立高斯噪声 N(0, σ_i²)，则等价于给全局模型加噪声 N(0, σ_G²)，且 σ_G² = (1/n²)·Σ σ_i²。由于聚合器无法访问训练数据、无法直接估计敏感度 Δ，论文用裁剪阈值近似它，即 (1/n²)·Σ Δ_i² ≈ S_t²，从而得到式 (7)。定理 2 声称角度偏差大或参数幅度大的后门模型具有更高的敏感度 Δ，因此聚类和裁剪先把这类模型去掉以后，剩余后门所需的噪声就更小（第 5.1 节的第三步 S3）。论文明确说明形式化证明只针对线性模型（式 (8)：f(w; x) = w·x = |w|·|x|·cosθ），对深度神经网络（Deep Neural Network，DNN）只做经验验证。

**实现细节**：第 4.3.2 节采用等权平均 G_t = Σ_{l=1}^{L} W^c_{b_l} / L，其中 L 是被接纳模型的个数；论文明确拒绝按客户端上报的数据集大小加权，因为该信息不可信。附录 B.3 给出的 DP 参数为：图像分类 ε = 3705，NIDS ε = 395，自然语言处理 ε = 4191；对应 λ = 0.001（图像分类与自然语言处理）和 λ = 0.01（NIDS）。附录 C 说明把 K-means 聚类、固定裁剪和固定加噪简单堆叠会产生 Backdoor Accuracy（BA）51.9%、Main Task Accuracy（MA）60.24% 的差结果，而同一场景下 FLAME 为 BA 0.0%、MA 89.87%。

## 5. 检测或防御所需的数据

FLAME 是纯服务器端方法，它需要的输入非常少，且完全不需要访问训练数据。

- **（1）每个客户端的完整本地模型更新 W_i**
  - 是什么：客户端在上一轮全局模型基础上本地训练得到的全部权重与偏置参数，论文要求所有模型用相同的顺序扁平化或序列化以便比较（第 3 节）。包括恶意客户端上传的投毒模型 W'_i。
  - 在哪里采集：服务器收到更新时（算法 1 第 5 行到第 6 行）。
  - 粒度：逐客户端、整模型；论文不要求逐层、逐批或逐样本的中间量。
  - 跨轮历史：不需要。第 7.3 节说明 FLAME 是与轮次无关（round-independent）的防御，不使用"哪个客户端在哪一轮被剔除"这类历史信息。
  - 干净参考数据：不需要。第 4.1 节强调聚合器通常拿不到训练数据，方法正是为这种情形设计的。
  - 额外计算：需要。服务器要计算 O(n²) 的成对余弦距离（式 (2)）、运行 HDBSCAN，并计算 n 个模型到全局模型的欧氏距离（式 (3)）。
  - 其他客户端的数据：需要，且是本方法的核心，因为方向和幅度的判断依赖与其他客户端更新的比较。
- **（2）上一轮的全局模型 G*_{t−1}**
  - 是什么：上一轮聚合并加噪后得到的全局模型，也就是本轮下发给客户端的起点模型。
  - 在哪里采集：服务器聚合后的全局模型（上一轮的输出，本轮作为输入保留）。
  - 粒度：逐轮、整模型。
  - 跨轮历史：需要保留上一轮的全局模型这一状态（分析：这是服务器本来就持有的跨轮状态；论文真正声明不需要的是"被剔除客户端名单"这类逐客户端历史，见第 7.3 节）。用于计算欧氏距离 e_i 以及裁剪公式中的 G_{t−1}。
  - 干净参考数据、额外计算、其他客户端数据：不需要干净参考数据；欧氏距离的计算已计入上一项。
- **（3）本轮参与客户端的数量 n**
  - 是什么：客户端总数，用于设置 HDBSCAN 的最小簇规模（n/2 + 1）和等权平均的分母。
  - 在哪里采集：服务器聚合时（服务器自己知道）。
  - 粒度：逐轮。
  - 跨轮历史、干净参考数据、额外计算：都不需要。
- **（4）DP 参数 (ε, δ) 与噪声系数 λ**
  - 是什么：用于计算噪声尺度 σ = λ·S_t 的配置量。附录 B.3 说明 DP 预算取决于数据集场景，由客户端数据规模的中位数和模型规模决定，因此"可以由聚合器经验性地确定"。
  - 在哪里采集：服务器聚合时（离线配置，不是运行时采集的数据）。
  - 粒度：逐场景或逐任务，不是逐轮采集；论文中 S_t 逐轮动态更新，λ 则按场景固定。
- **明确不需要的输入**：逐样本损失、隐藏层激活、输出文本、客户端本地梯度、客户端上报的数据集大小（第 4.3.2 节说明该信息不可信）、客户端逐轮历史更新（第 7.3 节）。

作为防御论文，这里也记录它所针对的攻击在可观测量上留下的痕迹：论文把后门模型分成三类（第 3 节、图 2），第一类 W'_1 方向（角度）偏差大，第二类 W'_2 幅度大，第三类 W'_3 同时约束方向和幅度因而最难区分。论文声称能绕过的检测（即论文反驳的绕过主张）包括：Xu 等人针对联邦图神经网络的后门攻击（论文称其只考虑了聚类而忽略裁剪和加噪，作者后来修正了表述）、Li 等人的 3DFed（论文称其 Constrain Loss 只针对裁剪，没有考虑聚类和加噪），以及第 7.2 节自行评估的模型对齐与模型混淆策略。

## 6. 干预动作

- **剔除客户端（exclude_client）**：聚类把不属于多数稠密簇的模型判为离群点并拒绝，只有被接纳的 L 个模型参与本轮聚合（算法 1 第 7 行、第 10 行到第 12 行）。发生在服务器聚合之前。
- **裁剪（clip）**：对每个被接纳的模型按 γ = S_t / e_{b_l} 做整体缩放，裁剪后 W^c_{b_l} = G_{t−1} + (W_{b_l} − G_{t−1})·min(1, γ)。发生在服务器聚合之前。
- **等权平均（聚合本身）**：对被接纳且裁剪后的 L 个模型取平均得到 G_t。注意论文不按客户端数据量重新加权（第 4.3.2 节）。
- **加噪（add_noise）**：对聚合后的全局模型加高斯噪声 N(0, σ²)，得到 G*_t 并下发给客户端。发生在服务器聚合之后、全局模型下发之前（算法 1 第 13 行到第 14 行）。
- **论文没有使用的动作**：没有回滚、没有模型修复、没有客户端样本过滤、没有仅报告模式。所有干预都在服务器端，客户端侧不做任何修改。

## 7. 实验设置与主要结果

**设置**：三个应用领域，模型与数据集见表 2。CIFAR-10 的实验使用 100 个客户端、PMR = 20%（附录 A）。表 1 的 NIDS 实验每轮选 100 个客户端，其中 k = 40 个是攻击者（第 5.1 节）。模型对齐实验用 n = 200、k = 80（第 7.2 节）。多后门实验用 n = 100、k = 40（第 7.2 节）。PMR 扫描范围为 25% 到 60%（第 7.3 节、图 7）。动态客户端实验用 100 个客户端、其中 25 个恶意，每轮随机选 60 到 90 个客户端参与（第 7.3 节、图 8）。非独立同分布（non-IID）程度用 DegnIID 控制，图像分类中把客户端分成 10 组对应 CIFAR-10 的 10 个类（第 7.4 节）。指标为 BA、MA、True Positive Rate（TPR）与 True Negative Rate（TNR）（第 6 节）。

**关键结果**：

- 表 1（NIDS，n = 100，k = 40）：只用加噪时，σ = 0.01 得到 BA 100.0%、MA 100.0%；先聚类再取 σ = 0.01 得到 BA 0.0%、MA 80.5%；聚类加裁剪后 σ = 0.01 得到 BA 0.0%、MA 100.0%。这说明聚类和裁剪降低了消除后门所需的最小噪声。
- 表 3：constrain-and-scale 攻击下，Reddit 从无防御的 BA 100、MA 22.6 变为 BA 0、MA 22.3；CIFAR-10 从 81.9/89.8 变为 0/91.9；IoT-Traffic 从 100.0/100.0 变为 0/99.8。DBA 在 CIFAR-10 上从 93.8/57.4 变为 3.2/76.2；Edge-Case 从 42.8/84.3 变为 4.0/79.3；PGD 从 56.1/68.8 变为 0.5/65.1；无目标投毒在 CIFAR-10 上 MA 从 46.72 恢复到 91.31。
- 表 4：与现有防御对比。良性无攻击基线为 Reddit 22.7、CIFAR-10 92.2、IoT-Traffic 100.0（MA）。FLAME 在三者上均为 BA 0.0，MA 分别为 22.3、91.9、99.8；Krum 在三者上 BA 均为 100.0；FoolsGold 仅在 Reddit 上 BA 0.0；Auror 在三者上 BA 均为 100.0；AFA 仅在 CIFAR-10 上 BA 0.0；DP 方法在三者上 BA 分别为 14.0、0.0、14.8，MA 分别为 18.9、78.9、82.3；Median 在三者上 BA 均为 0.0，MA 分别为 22.0、50.1、87.7。
- 表 7（聚类组件）：FLAME 的 TPR/TNR 为 Reddit 22.2/100.0、CIFAR-10 23.8/86.2、IoT-Traffic 59.5/100.0。论文承认 TPR 不高，依靠加噪兜底。
- 表 5（模型对齐攻击，IoT-Traffic，n = 200，k = 80，每个恶意客户端的 PDR 在 5% 到 20% 之间随机）：只用模型过滤时 BA 100.0、MA 91.98、TPR 0.0、TNR 33.04；完整 FLAME 下 BA 0.0、MA 100.0、TPR 5.68、TNR 33.33。
- 多后门注入（第 7.2 节，n = 100，k = 40，后门数为 0、1、2、4、8，对应每个后门 0、40、20、10、5 个恶意客户端）：BA = 0% ± 0.0%，TPR = 95.2% ± 0.0%，TNR = 100.0% ± 0.0%。第二个实验中 40 个恶意客户端各注入 4 个后门，论文称仍能完全缓解。
- 模型混淆（第 7.2 节，IoT-Traffic）：噪声水平 0.034 时 BA 仍为 0%，MA 为 100%。
- PMR 影响（图 7）：PMR 在 25% 到 60% 之间变化，PMR 小于 50% 时 TNR = 100% 且 BA = 0%；PMR 大于 50% 时防御失败；PMR 等于 50% 时所有模型都被接纳（TPR = 0%、TNR = 100%）。
- 动态客户端（图 8）：每轮客户端数量变化时 BA 仍为 0%，MA 与表 4 的结果基本一致。
- 非独立同分布程度（图 9）：DegnIID 从 0 到 1 变化时 BA 保持 0%；MA 在 DegnIID = 0.6 时为 91.9%，在 DegnIID = 1.0 时降到 91.0%。
- 裁剪阈值对比（图 11）：静态阈值 S = 0.5 能消除后门但 MA 降到 0%；静态阈值 S = 10 在 PDR 不小于 35% 时失效（BA = 100%）；FLAME 的动态中位数阈值在 BA 恒为 0% 的同时保持较高的 MA。
- 噪声水平对比（图 12）：λ 增大则 BA 下降但 MA 也下降。
- 3DFed 复现（附录 H、表 8）：论文用 3DFed 作者提供的源码，每个实验至少重复 50 次。CIFAR-10 上 3DFed 论文报告 BA 99.89（其 MA 在部署 FLAME 时未报告），复现结果为预训练 200 轮时 MA 80.8、BA 53.9，400/600/800 轮时 MA 约 86.9 到 87.0、BA 9.9；MNIST 上复现的 BA 为 19.1（10 轮）、20.4（20 轮）、24.0（30 轮）、29.2（50 轮），MA 约 98.9 到 99.1；Tiny-ImageNet 上复现的 BA 为 0.55 到 0.56，MA 约 61.1 到 66.8。论文的结论是 FLAME 有效缓解了 3DFed。分析：表 8 中 CIFAR-10 在 200 轮预训练下 BA 仍为 53.9%，而论文正文表述为 BA 在全局模型收敛后"接近随机猜测"，这两者在数值上存在明显张力，引用时应当谨慎。

## 8. 开销

- **收敛轮次开销**（附录 D）：在 IoT 数据集的 6 种设备类型上、只有良性客户端参与、模型随机初始化的实验中，最高观察到 4 个额外轮次；平均需要 1.67 个额外训练轮次才能达到无防御时 MA 的至少 99%。
- **隐私版本的运行时开销**（附录 G）：使用 ABY 框架的 STPC 版本相对于非隐私版本，运行时开销最高达到三个数量级；即使考虑最大的 Reddit 模型和 K = 100 个客户端，使用 STPC 时服务器端单个训练轮次的总运行时间为 22 081.65 秒（约 6 小时）。附录 G 还说明，为了适应 STPC，隐私版本用 DBSCAN 近似 HDBSCAN，精度损失可以忽略。
- **计算开销的定性描述**：第 5.2 节与第 4.3.1 节说明聚类使用余弦距离与 HDBSCAN；附录 E 描述了 HDBSCAN 需要构建最小生成树并据此构建二叉树，然后用稳定性值选择簇，但论文没有给出非隐私版本的成对距离计算、聚类与裁剪的具体运行时间数字（附录 G 提到有对比实验，但正文只给出隐私版本的绝对数值）。
- **通信与存储开销**：论文未报告。论文没有给出 FLAME 相对于 FedAvg 的额外通信量或服务器存储量的测量。分析：从协议上看，FLAME 仍然只需要客户端上传完整本地模型、服务器下发全局模型，通信轮数与 FedAvg 同阶，但论文没有做这项测量。

## 9. 假设、局限与自适应攻击

**依赖的假设**：

- 良性客户端占多数，即 PMR = k/n < 50%（第 2.3 节、第 4.3.1 节、第 7.3 节）；裁剪阈值取中位数、最小簇规模取 n/2 + 1 都建立在这一假设上。
- 聚合器无法访问训练数据，也不需要访问；所有判断只基于模型更新（第 4.1 节、第 5.1 节）。
- 本地模型可以被一致地扁平化为可比较的权重向量（第 3 节）。
- 攻击必须在权重空间留下方向偏差或幅度偏差，并且偏差越大攻击影响越大；越隐蔽的模型影响越小（第 3 节、第 5.1 节的定理 2、第 5.2 节）。
- 差分隐私噪声能够消除后门；论文对线性模型给出形式化证明，对 DNN 只做经验验证，因为"DNN 的 DP 后门安全性的形式化证明仍是开放问题"（第 5.1 节）。
- 客户端上报的数据集大小不可信，因此等权聚合（第 4.3.2 节）。
- 攻击者可以完全了解防御并获得自适应性，但不能控制聚合器进程或诚实客户端（第 2.3 节）。
- 第 5.2 节声称 FLAME 不对攻击策略和数据分布做特定假设，并且在分布 X'_i 与良性分布接近时愿意接受漏检，因为这类模型的攻击影响小，剩余影响由加噪消除。

**论文自述的局限**：

- PMR 不小于 50% 时防御失效（图 7）。
- 聚类不保证识别全部恶意模型，TPR 可能很低（表 5 中模型对齐场景 TPR = 5.68%，表 7 中 CIFAR-10 TPR = 23.8%），论文依赖加噪兜底。
- 在非独立同分布程度很高时，需要更大的噪声，MA 会下降（DegnIID = 1.0 时 MA 为 91.0%，图 9）。
- 裁剪阈值和噪声水平存在精度与安全的权衡；静态或过小的裁剪阈值会让模型不可用，过大的阈值会让攻击成功（图 11、图 12）。
- DP 预算依赖数据集场景，需要经验确定（附录 B.3）。
- 噪声和裁剪会略微影响收敛速度（附录 D）。

**自适应攻击的评估**：论文在第 7.2 节评估了三类自适应策略。改变注入策略时，多后门与单客户端多后门都仍被缓解（BA = 0% ± 0.0%）。模型对齐时，聚类几乎完全失效（TPR = 5.68%），但完整 FLAME 仍把 BA 从 100% 降到 0%，论文解释为被对齐的恶意更新影响本来就小，会被加噪平均掉。模型混淆时，加噪 0.034 仍然无法绕过（BA = 0%，MA = 100%）。第 10 节另外反驳了 Xu 等人与 Li 等人（3DFed）的绕过主张，并用 3DFed 官方源码做了复现研究（附录 H）。分析：这些自适应评估的对手都由论文自己构造，且第 10 节的反驳主要论证对方没有完整实现 FLAME 的聚类、裁剪、加噪三个组件；一个完整掌握三组件并在同一威胁模型下做端到端优化的自适应攻击者没有被独立评估。

**迁移到联邦大模型 LoRA 微调时可能失效的假设（分析）**：

- FLAME 的余弦距离、欧氏距离、中位数裁剪和加噪都定义在"完整模型参数向量"上。LoRA 只上传低秩增量（通常记为 B 与 A 两个矩阵）时，增量的 L2 范数与全参数模型的 L2 范数不可比，"到上一轮全局模型的欧氏距离"这一语义也发生变化，中位数阈值 S_t 的物理意义需要重新定义。
- 不同客户端的 LoRA 秩、缩放系数、目标模块集合可能不同，坐标对齐与逐坐标平均的前提不再显然成立；论文完全没有讨论适配器结构异构的情况。
- 论文的定理 1、定理 2 与式 (5) 到式 (7) 的证明只覆盖线性模型，DNN 仅经验验证；大语言模型的参数规模、训练动态和安全对齐行为都远离这一验证范围，噪声尺度能否同时消除后门和保持生成质量，论文没有提供依据。
- 论文用 BA 度量触发集上的错误率，而大模型后门常见的形态是触发词、越狱（jailbreak）或安全对齐破坏，缺少论文意义上的小型触发集和单一错误标签，指标迁移性存疑。
- 论文假设少于一半客户端被控；在 LoRA 微调中如果攻击者同时是数据提供方或适配器发布者，被控比例和攻击入口都可能超出论文的威胁模型。
- 等权聚合在 LoRA 微调中对数据量差异极大的客户端可能带来新的精度问题，而论文明确拒绝使用不可信的数据量信息，这一点在微调场景下会更难处理。

## 10. 对防护库设计的含义

以下所有条目均为分析。

1. 采集底座需要的最小数据视图是"服务器收到更新时的完整客户端参数向量 + 服务器自己保留的上一轮全局模型 + 本轮客户端数量"，粒度是逐客户端整模型、逐轮，不需要逐样本、逐层、逐批的数据，也不需要跨轮的逐客户端历史。这是通用需求，任何基于更新方向或幅度比较的检测插件都需要它。
2. 迁移到联邦 LoRA 微调时，采集点应落在服务器收到适配器更新时，采集对象是 LoRA 增量以及结构元数据（秩、缩放系数、目标模块、基座模型版本），而不是论文里的完整权重向量。这是本论文特有的假设带来的改造点，论文本身没有涉及。
3. 需要支持"被剔除的更新仍参与统计但不参与聚合"的数据视图。FLAME 的裁剪阈值取全部 n 个模型欧氏距离的中位数，被聚类拒绝的模型也要计入。库如果把过滤和统计耦合在一起，就无法复现这个行为，这属于本论文特有的需求。
4. 干预接口需要三个服务器钩子：聚合前的客户端集合过滤（输出被接纳的客户端子集）、聚合前的逐客户端缩放因子（裁剪）、聚合后的全局模型加噪。三者有固定顺序，过滤在前、裁剪居中、加噪在最后，客户端侧不需要任何干预钩子。这是通用需求（剔除、重加权、裁剪、加噪是投毒防护的公共动作集），但顺序约束和"等权平均不按数据量重加权"是本论文特有的约定。
5. 阈值不能在插件里写死。HDBSCAN 的簇数、最小簇规模、裁剪阈值、噪声尺度都由当前轮的更新集合动态估计，因此库需要暴露每轮的中间量（聚类划分、被拒模型列表、阈值、噪声尺度）供审计和复现。这是通用需求，也是这篇论文强调的核心设计。
6. 如果要在加密或隐私保护状态下执行同样的检测与裁剪，需要注意可用的算子集合会受限，本论文的做法是用 DBSCAN 近似 HDBSCAN 以降低安全多方计算的代价；库若计划支持这一类后端，插件接口应允许替换聚类算法而不改变外部数据契约。这是本论文特有的工程结论。

## 11. 原文依据

1. 第 2.3 节：`Furthermore, A has full knowledge of the aggregator’s operations, including potentially applied backdoor defenses. However, A has no control over any processes executed at the aggregator nor over the honest clients.` —— 支撑第 2 节关于攻击者知识与能力边界的论断。
2. 第 2.2 节、图 1：`common techniques used in FL backdoor attacks, including 1) data poisoning, e.g., [50,56,64], where A manipulates training datasets of models, and 2) model poisoning, e.g., [9,62] where A manipulates the training process or the trained models themselves.` —— 支撑第 3 节关于攻击入口位于本地数据准备、本地训练过程与更新上传前处理的论断。
3. 第 4.3.1 节：`FLAME uses pairwise cosine distances to measure the angular differences between all model updates and applies the HDBSCAN clustering algorithm [13].` —— 支撑第 4 节与第 5 节关于聚类组件的输入与算法的论断。
4. 第 4.3.1 节：`In contrast to existing approaches that try to place poisoned models into one cluster, our approach considers each poisoned model individually as an outlier, so that it can gracefully handle multiple simultaneous backdoors and thus address challenge C1.` —— 支撑第 6 节关于剔除客户端这一干预动作的论断。
5. 第 4.3.2 节：`It should be noted that for determining the clipping bound, the rejected models are also considered to ensure that even if benign models were filtered, the computed median St is still determined based on benign values.` —— 支撑第 5 节关于"被拒模型仍参与中位数统计但不参与聚合"的数据视图。
6. 第 4.3.2 节：`By using the median as the clipping bound St, we ensure that St is always in the range of the L2-norms between benign models and the global model since we assume that more than 50% of clients are benign` —— 支撑第 9 节关于"良性客户端占多数"这一核心假设的论断。
7. 第 5.1 节、定理 1：`A (ε,δ)-differentially private model with parameters G and clipping bound St is backdoor-free if random Gaussian noise is added to the model parameters` —— 支撑第 4 节关于加噪组件及其噪声尺度依据的论断。
8. 第 5.1 节：`We provide a formal proof for linear models and extend the proof to DNNs using empirical evaluation.` —— 支撑第 9 节关于形式化保证只覆盖线性模型的局限。
9. 第 7.1 节：`FLAME completely mitigates the constrain-and-scale attack (BA = 0%) for all datasets. Moreover, our defense does not affect the Main Task Accuracy (MA) of the system as MA reduces by less than 0.4% in all experiments.` —— 支撑第 7 节关于主要实验结果的论断。
10. 第 7.3 节：`It shows that FLAME is only effective if PMR < 50% so that only benign clients are admitted to the model aggregation (TNR = 100%) and thus BA = 0%.` —— 支撑第 9 节关于恶意比例超过一半时防御失效的论断。

```json
{
  "key": "nguyen2022flame",
  "title": "FLAME: Taming Backdoors in Federated Learning (Extended Version)",
  "year": 2022,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["backdoor", "untargeted"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {
      "what": "每个客户端上传的完整本地模型参数向量（权重与偏置，按固定顺序扁平化序列化），包括被攻陷客户端上传的投毒模型",
      "where": "server_receive",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "上一轮聚合并加噪后的全局模型，用于计算每个客户端更新到它的欧氏距离以及裁剪公式中的基准点",
      "where": "server_post_aggregate",
      "granularity": "model",
      "needs_history": true,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "本轮参与训练的客户端数量，用于设置 HDBSCAN 最小簇规模（n/2+1）和等权平均的分母",
      "where": "server_aggregate",
      "granularity": "round",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    }
  ],
  "interventions": ["exclude_client", "clip", "add_noise"],
  "intervention_where": ["server"],
  "assumptions": [
    "良性客户端占多数，即被攻陷客户端比例 PMR = k/n 小于 50%",
    "聚合器无法访问客户端训练数据，也不需要访问",
    "所有本地模型可以被一致地扁平化为可比较的权重向量",
    "后门模型在权重空间留下方向偏差或幅度偏差，且偏差越大攻击影响越大",
    "差分隐私噪声足以消除后门：线性模型有形式化证明，深度神经网络仅经验验证",
    "客户端上报的数据集大小不可信，因此所有客户端等权聚合",
    "攻击者完全了解防御但不能控制聚合器进程或诚实客户端"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {
      "section": "2.3 Adversary Goals and Capabilities",
      "supports": "第 2 节威胁模型：攻击者的知识与能力边界",
      "text": "Furthermore, A has full knowledge of the aggregator’s operations, including potentially applied backdoor defenses. However, A has no control over any processes executed at the aggregator nor over the honest clients."
    },
    {
      "section": "2.2 Backdoor Attacks on Federated Learning (Figure 1)",
      "supports": "第 3 节攻击入口：数据投毒与模型投毒",
      "text": "common techniques used in FL backdoor attacks, including 1) data poisoning, e.g., [50,56,64], where A manipulates training datasets of models, and 2) model poisoning, e.g., [9,62] where A manipulates the training process or the trained models themselves."
    },
    {
      "section": "4.3.1 Dynamic Model Filtering",
      "supports": "第 4 节与第 5 节：聚类组件使用成对余弦距离与 HDBSCAN",
      "text": "FLAME uses pairwise cosine distances to measure the angular differences between all model updates and applies the HDBSCAN clustering algorithm [13]."
    },
    {
      "section": "4.3.1 Dynamic Model Filtering",
      "supports": "第 6 节：把可疑模型逐个作为离群点剔除",
      "text": "In contrast to existing approaches that try to place poisoned models into one cluster, our approach considers each poisoned model individually as an outlier, so that it can gracefully handle multiple simultaneous backdoors and thus address challenge C1."
    },
    {
      "section": "4.3.2 Adaptive Clipping and Noising",
      "supports": "第 5 节：被拒模型仍参与裁剪阈值的中位数计算",
      "text": "It should be noted that for determining the clipping bound, the rejected models are also considered to ensure that even if benign models were filtered, the computed median St is still determined based on benign values."
    },
    {
      "section": "4.3.2 Adaptive Clipping and Noising",
      "supports": "第 9 节：良性客户端占多数这一核心假设",
      "text": "By using the median as the clipping bound St, we ensure that St is always in the range of the L2-norms between benign models and the global model since we assume that more than 50% of clients are benign"
    },
    {
      "section": "5.1 Noise Boundary Proof of FLAME (Theorem 1)",
      "supports": "第 4 节：加噪组件的 backdoor-free 条件",
      "text": "A (ε,δ)-differentially private model with parameters G and clipping bound St is backdoor-free if random Gaussian noise is added to the model parameters"
    },
    {
      "section": "5.1 Noise Boundary Proof of FLAME",
      "supports": "第 9 节：形式化证明只覆盖线性模型",
      "text": "We provide a formal proof for linear models and extend the proof to DNNs using empirical evaluation."
    },
    {
      "section": "7.1 Preventing Backdoor Attacks",
      "supports": "第 7 节：对 constrain-and-scale 的主要实验结果",
      "text": "FLAME completely mitigates the constrain-and-scale attack (BA = 0%) for all datasets. Moreover, our defense does not affect the Main Task Accuracy (MA) of the system as MA reduces by less than 0.4% in all experiments."
    },
    {
      "section": "7.3 Effect of Number of Clients",
      "supports": "第 9 节：PMR 达到或超过 50% 时防御失效",
      "text": "It shows that FLAME is only effective if PMR < 50% so that only benign clients are admitted to the model aggregation (TNR = 100%) and thus BA = 0%."
    }
  ]
}
```
