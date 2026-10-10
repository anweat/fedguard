# zhang2025flpoison：SoK: Benchmarking Poisoning Attacks and Defenses in Federated Learning

## 1. 基本信息

- 场景：传统联邦学习（federated learning, FL），具体是图像分类任务上的联邦训练基准与系统化知识整理（systematization of knowledge, SoK），不涉及大语言模型（large language model, LLM）、低秩适配（low-rank adaptation, LoRA）或参数高效微调（parameter-efficient fine-tuning, PEFT）。论文摘要、第 4 至第 6 节以及第 6.1 节的模型与数据集描述都只涉及卷积网络与图像分类数据。
- 训练阶段：覆盖数据准备（data preprocessing）、本地训练（local training）、更新上传（update submission）与服务器聚合（server aggregation）四个阶段，并在第 4.1 节把模型投毒攻击（model poisoning attack, MPA）按训练阶段分为训练期（training-time）、训练后期（post-training）与更新期（update-time）三类；防御全部发生在服务器聚合器（aggregator）上，另有少数方法在客户端训练与推理阶段起作用。
- 论文类型：基准与平台（benchmark）兼综述性 SoK，同时给出了攻击与防御两套分类法，并统一评测了 15 种投毒攻击与 17 种防御策略。
- 模型与数据规模：在 MNIST 上训练 LeNet-5，在 CIFAR-10 上训练 ResNet-18（第 6.1 节 "Models and Datasets"）。MNIST 有 60,000 张训练图像与 10,000 张测试图像，为 28×28 灰度图、10 类；CIFAR-10 有 50,000 张训练图像与 10,000 张测试图像，为 32×32 彩色图、10 类（第 6.1 节）。联邦算法的实验配置为：FedSGD 在 MNIST 上 500 轮、在 CIFAR-10 上 800 轮；FedOpt 在两个数据集上均为 5×500 轮；批大小 64，学习率 0.01，优化器为动量 0.9、权重衰减 5e-4 的 SGD，学习率调度为 MultiStepLR（衰减点为轮数的 0.5 与 0.8，gamma 为 0.01）（表 9）。防御与攻击的总评测规模为 2,040 组设置，即 15 种攻击 × 17 种防御 × 2 个数据集 × 2 种算法 × 2 种数据异质性水平（第 6 节）。

## 2. 威胁模型

- 攻击者身份：被攻陷或恶意的客户端。论文在附录 B.3 假设 n 个客户端中有 f 个是恶意的或被攻陷的，并沿用既有工作 [11] 的约定，把前 f 个客户端视为恶意客户端，其余为良性客户端。论文没有考虑恶意服务器、恶意数据提供方、恶意适配器发布者或外部攻击者，这些角色论文未说明。
- 占比或数量：表 9 的 "Adversaries / Participants" 行报告 24/50 与 4/20 两组配置；附录 B.6 在 MNIST 上使用 0.1、0.2、0.48 三个攻击者比例，即 50 个参与方中的 5、10、24 个。分析：由此可以推断 24/50 对应 MNIST 的主实验、4/20 对应 CIFAR-10，但表 9 本身并未逐列标注这两个比值分别属于哪个数据集。各防御方法对恶意数量的要求不同，表 3 列出 Krum 要求 2f+2<n，Coordinate-wise Median、TrimmedMean、RFA、NormClipping、CRFL、FoolsGold、Auror、SignGuard、DeepSight、FLAME 等要求 2f+1<n，Bulyan 要求 4f+3≤n，Bucketing 要求 2f+2<n/S。
- 能力：数据投毒攻击（data poisoning attack, DPA）能控制本地训练数据，包括替换标签、在图像上打触发器并把标签改成目标标签（第 4.2 节）；混合投毒攻击（hybrid poisoning attack）还能同时操纵本地训练过程与上传的更新，例如加入异常检测项改变损失（公式 9）、在提交前把更新按因子 γ=n/η 缩放（第 4.3 节 Model Replacement）、在每轮用投影梯度下降（projected gradient descent, PGD）保证躲过范数裁剪（第 4.3 节 Edge-case Backdoor）、只更新良性客户端很少更新的坐标并做梯度范数裁剪（第 4.3 节 Neurotoxin）；纯模型投毒攻击则直接构造上传的梯度或权重。
- 知识：论文把攻击分为非全知（non-omniscient）与全知（omniscient）两类。非全知的训练后期攻击只需要攻击者自身的信息，例如 Gaussian Random Attack 与 Sign Flipping Attack（第 4.1.2 节）；全知的更新期攻击会窃听良性客户端的更新或与其他恶意客户端串谋，例如 ALIE 需要估计良性更新的均值与方差（第 4.1.3 节），IPM 需要良性梯度的均值（公式 5），Fang Attack 需要知道其他攻击者的本地训练数据、模型与梯度更新（第 4.1.3 节）；部分攻击还需要知道聚合规则或防御方法，属于聚合器特定（aggregator-specific）攻击，在不知道聚合规则时会随机假定一个（第 4.1.3 节）。
- 目标：模型投毒攻击多为无目标攻击（untargeted），目的是破坏收敛、降低主任务准确率；数据投毒与混合投毒攻击多为定向攻击（targeted），目的是植入后门，使带触发器的样本被预测为攻击者指定的目标标签（第 4 节、附录 B.2）。论文没有研究隐私窃取、越狱或安全对齐破坏等目标。
- 防御者：中央服务器及其聚合器。服务器能看到每一轮每个客户端提交的更新向量或本地权重（附录 B.3、附录 A 中的算法 1）。表 3 进一步区分了不同聚合器所依赖的知识：Krum、Multi-Krum、Bulyan、Bucketing 假设恶意客户端数量有界；只有 FLTrust 假设服务器持有良性（干净）数据；CenteredClipping、FoolsGold、DeepSight、FLAME 使用服务器历史；多数方法假设客户端数据分布为均衡独立同分布（Balanced IID）。论文假设服务器本身诚实，没有讨论服务器被攻陷的情形。

## 3. 攻击入口与流程位置

论文把投毒原理画成预处理阶段、训练阶段与推理及防御阶段三段（图 3），攻击进入的位置只有客户端一侧的三处：

- 本地数据准备：数据投毒攻击在此进入。Label Flipping 直接把源标签替换为随机标签、逆序标签或指定目标标签（第 4.2 节）；BadNets 在图像上添加触发器并把对应标签改成目标标签（第 4.2 节）；Edge-case Backdoor 通过把正常数据与稀有但相似的数据混合来构造边缘样本数据集，例如用 ARDIS 数据集增强 MNIST（第 4.3 节）；DBA 把一个全局触发器拆成多个局部模式，分别嵌入不同恶意客户端的训练数据（第 4.3 节）。
- 本地训练过程：训练期投毒攻击在此进入，攻击者可以修改训练配置，例如本地轮数、学习率、损失函数等（第 4.1.1 节），这些攻击通常与数据投毒结合形成混合投毒攻击（第 4.1.1 节、第 4.3 节）。具体操作包括：Model Replacement 把异常检测项 L_ano 加入损失，得到 L_model=αL_class+(1−α)L_ano（公式 9）；AlterMin 交替优化攻击目标与隐蔽目标，使恶意本地更新只轻微偏离良性更新（第 4.3 节）；Edge-case Backdoor 的第二种策略在每轮对恶意模型做 PGD 投影；Neurotoxin 在每轮本地训练前先取全局模型绝对值最小的前 k 个梯度坐标作为掩码，训练后把梯度投影到这些不常更新的坐标上，并做梯度范数裁剪（第 4.3 节）。
- 更新上传前的后处理：训练后期投毒与更新期投毒在此进入。Gaussian Random Attack 直接提交服从正态分布的随机向量（公式 1）；Sign Flipping Attack 提交取反并乘上系数 λ 的梯度（公式 2）；ALIE 在良性更新均值与标准差的范围内构造恶意更新（公式 3 与公式 4）；IPM 把恶意梯度设为良性梯度均值的负若干倍（公式 5）；Mimic Attack 复制某个良性更新；Fang Attack 先估计参数变化方向，再用当前全局模型减去 λ 倍符号方向构造恶意模型并提交给 Krum，同时优化 λ 或在搜索失败时追加更多伪造模型（公式 6）；MinMax 与 MinSum 通过优化 γ 使恶意梯度到良性梯度的最大距离或距离平方和不超过良性梯度之间的距离（公式 7 与公式 8）；Model Replacement 与 DBA 在提交前把更新按 γ=n/η 缩放以放大影响（第 4.3 节）。
- 论文未把服务器聚合、全局模型下发、评估与部署列为攻击入口：攻击者全部来自客户端，服务器的聚合过程被当作防御发生的位置（第 5 节），评估阶段只用于计算准确率与攻击成功率。

## 4. 方法原理

论文由三部分组成。

第一部分是攻击与防御的分类法。攻击按攻击点分为模型投毒攻击、数据投毒攻击与混合投毒攻击（第 4 节、图 1）；模型投毒攻击按训练阶段再分为训练期、训练后期与更新期，更新期攻击又分为基于统计的规避（statistic-based evasion，如 ALIE、IPM）与基于优化的规避（optimization-based evasion，如 Fang Attack、MinMax、MinSum）（第 4.1 节）。防御分为稳健聚合（robust aggregation）与离群检测（outlier detection）两大类（第 5 节）。

第二部分是统一的基准框架 FLPoison。框架分为三层：联邦学习层、攻击层与聚合层，每层通过全局参数配置；联邦学习层实现 Worker 基类以及 Client 与 Server 类，并由 Coordinator 负责客户端初始化与算法配置，支持的 FedSGD、FedOpt、FedAvg 算法以钩子形式注入客户端；攻击层包含模型投毒模块与数据投毒模块，前者覆盖训练期、训练后期与更新期投毒，后者的合成器（synthesizer）对预处理数据施加指定投毒策略，数据投毒指示器决定某个批次是否被毒化；聚合层从服务器收集客户端更新并应用聚合规则（附录 A、图 2）。每个攻击与防御通过注册表机制自动注册（附录 A）。

第三部分是各防御方法的原理，关键公式如下（第 5.1 与 5.2 节）：Krum 为每个更新计算到最近的 n−f−2 个更新的平方欧氏距离之和作为分数，选分数最小者（公式 10）；Multi-Krum 选分数最小的 m 个取平均（公式 11）；Coordinate-wise Median 逐坐标取中位数（公式 12）；TrimmedMean 逐坐标排序后去掉两端各 β 比例再平均（公式 13）；Bulyan 先用 Krum 选出集合 S，再对每个坐标取 S 中最接近中位数的 β 个坐标的平均（公式 14）；RFA 用平滑 Weiszfeld 算法近似加权几何中位数（公式 15）；FLTrust 用服务器模型更新 g_0 与客户端更新的余弦相似度经 ReLU 得到信任分数（公式 16），把每个更新按服务器更新范数归一化后按信任分数加权求和（公式 17）；CenteredClipping 以上一轮聚合结果 v_l 为中心做迭代裁剪（公式 18）；DnC 先随机子采样降维并减去坐标均值，再用奇异值分解（singular value decomposition, SVD）求主右奇异向量并把更新投影上去得到离群分数，选分数最低的 n−βf 个；Bucketing 打乱客户端更新序列后分桶，桶内用指定聚合器（默认 Krum）；SignGuard 用客户端更新范数中位数的上下界过滤，再随机采样坐标计算符号统计并聚类，取多数簇的均值；Auror 把每个坐标聚成两类，按簇心距离阈值选出指示特征，再对指示特征聚类，以多数簇判定良性客户端；FoolsGold 以全局模型输出层参数作为指示特征，计算历史累积多轮更新的余弦相似度并用 pardoning 函数重加权；NormClipping 按阈值 M 对每个更新做范数裁剪后取平均（公式 19）；CRFL 在训练中做参数裁剪与扰动，在推理时用随机平滑给出认证鲁棒界；DeepSight 用 Division Differences、Normalized Update Energy 与余弦距离聚类，按能量超过中位数的次数与簇级可疑计数过滤恶意模型；FLAME 先用 HDBSCAN 按余弦距离聚类，按 L2 范数中位数裁剪良性簇，再加入标准差为 σ=λ·median(w_i)、其中 λ=(1/ε)·sqrt(2 ln(1.25/δ)) 的高斯噪声。

评测指标为准确率（accuracy, ACC）与攻击成功率（attack success rate, ASR）（第 6.1 节），并派生两个复合指标：定向攻击影响 Targeted Attack Impact 等于攻击下的准确率除以无攻击准确率再加上 ASR（公式 20）；定向防御稳健性 Targeted Defense Robustness 等于攻击下的准确率除以无攻击准确率再加上 1 减 ASR（公式 21）。

## 5. 检测或防御所需的数据

论文的防御全部在服务器端聚合器上工作，因此所需数据集中在"服务器收到更新时"和"服务器聚合时"两个位置。逐项如下。

- 客户端上传的模型更新向量或本地权重：FedSGD 与 FedOpt 下客户端提交差值 Δ=w_i−w_global（算法 1 第 11 步），FedAvg 下客户端直接提交本地权重 w_i（算法 1 第 13 步）。采集位置为服务器收到更新时；粒度为逐客户端、逐轮、整个模型维度 d。Krum、Multi-Krum、Coordinate-wise Median、TrimmedMean、Bulyan、RFA、NormClipping、SignGuard、Bucketing、DnC、Auror、FoolsGold、CenteredClipping、CRFL、DeepSight、FLAME 都以它为输入。不需要历史、不需要干净数据、不需要额外前向或反向计算。
- 客户端更新之间的成对距离与分数：Krum 的分数 s(i) 由更新两两之间的平方欧氏距离构成，MinMax 与 MinSum 同样是距离约束（公式 7、公式 8、公式 10）。采集位置为服务器聚合时；粒度为逐客户端对（因此需要当轮所有参与客户端的更新视图）、逐轮。
- 逐坐标与逐层稳健统计量：坐标中位数（公式 12）、排序后的分位与截尾均值（公式 13）、RFA 的几何中位数近似（公式 15）、Bulyan 的坐标中位数（公式 14）。采集位置为服务器聚合时；粒度为逐坐标或逐层、逐客户端、逐轮。
- 逐客户端更新的 L2 范数与裁剪阈值：NormClipping 的阈值 M（公式 19）、FLAME 的范数中位数、SignGuard 的范数中位数上下界、CenteredClipping 的阈值 τ_l（公式 18）。采集位置为服务器收到更新时或聚合时；粒度为逐客户端、逐轮，部分方法可按层计算。
- 跨轮历史：表 3 的 "Server History" 列把 CenteredClipping、FoolsGold、DeepSight、FLAME 标为需要服务器历史。具体地，CenteredClipping 需要上一轮的聚合结果 v_l 以及客户端动量 x_i（公式 18），FoolsGold 需要历史累积多轮的输出层指示特征与两两余弦相似度（第 5.2 节），DeepSight 需要跨轮比较更新能量与预测分数分布（第 5.2 节）。采集位置为服务器聚合时；粒度为逐轮与逐客户端。
- 服务器干净参考数据与服务器模型更新：FLTrust 假设服务器持有一个干净的小数据集，用它训练服务器模型并在训练过程中建立信任（第 5.1 节），聚合时需要服务器模型更新 g_0 参与余弦相似度与范数归一化（公式 16、公式 17）。表 3 中只有 FLTrust 在 "Benign" 一列被标记为需要良性数据。附录 A 指出部分聚合方案假设服务器能访问一个与训练数据同分布的数据集，图 2 中也有专门的 "Server Data Assumption" 模块。采集位置在服务器聚合之前；粒度为模型级、逐轮；需要干净参考数据，也需要额外计算（在服务器上训练模型）。
- 子采样坐标与额外前向计算：DnC 先随机子采样梯度以降维再做 SVD，SignGuard 随机采样坐标计算符号统计（第 5.1 节）。DeepSight 需要提取三种模式并在最多 20,000 个随机数据点上测试模型以获得预测分数分布（附录 B.5），因此需要服务器端对客户端模型做额外前向计算。采集位置为服务器聚合时；粒度分别为子采样坐标与逐样本预测分数；DeepSight 还需要跨轮历史。
- 评估数据：测试集上的准确率与在投毒测试样本上的攻击成功率，以及公式 20 与公式 21 两个复合指标所需的"无攻击准确率"。采集位置为评估时；粒度为模型级、逐轮或最终。
- 攻击侧所需的原始数据视图（用于复现攻击插件）：客户端本地采样的小批量数据 ξ_i（算法 1 第 8 步）、数据投毒比例 0.32（批大小 64 中 20 张被毒化，附录 B.4），以及触发器嵌入、标签替换、PGD 投影、梯度掩码等操作所需的逐样本数据。采集位置为客户端训练前与客户端每步。

论文没有使用的数据视图，需要明确说明：论文的防御没有使用逐样本损失、逐样本梯度、隐藏层激活或输出文本；论文也没有使用根数据集（root dataset）之外的其他客户端原始数据，客户端之间只交换更新，不交换数据。

攻击留下的可观测量与声称能绕过的检测如下。

- Gaussian Random Attack 在更新上表现为大方差随机噪声，论文认为随着训练收敛、模型更新的分布趋近高斯分布，这类攻击在训练后期越来越难识别，并且能给只做离群检测、没有稳健统计量或可靠参考的防御（论文点名 [12, 22, 43, 50, 56]）带来大扰动（第 6.2 节）。
- Sign Flipping Attack 使梯度的符号整体反向（公式 2），会破坏内积方向；IPM 通过使恶意梯度与真实梯度的内积为负来破坏收敛（第 4.1.3 节），论文称它对 Krum 与坐标级方法更有效（第 6.2 节）。
- ALIE 把扰动限制在良性更新均值加减 z_max 倍标准差的范围内（公式 3、公式 4），论文称它能够骗过 Krum、TrimmedMean 与 Bulyan（第 4.1.3 节）。
- Fang Attack 通过优化 λ 并追加伪造模型，使自己被 Krum 选为良性更新（第 4.1.3 节）；MinMax 与 MinSum 通过距离约束使恶意梯度落在良性梯度的距离范围内（公式 7、公式 8）。
- Mimic Attack 直接复制一个良性更新，论文称它因此不可区分、难以过滤（第 4.1.3 节）。
- 后门类攻击的可观测量主要来自缩放与坐标选择：Model Replacement、DBA、AlterMin 使用缩放放大恶意更新（第 4.3 节），Neurotoxin 只更新良性客户端很少使用的坐标，从而对抗后门检测（第 4.3 节），AlterMin 的隐蔽目标让恶意本地更新只轻微偏离良性更新（第 4.3 节）。
- 论文明确指出哪些防御在实验中失效：只依赖离群检测或稳健统计量的 Krum 与 SignGuard 对模型投毒攻击表现不佳，FoolsGold 与 DeepSight 因为使用依赖数据的超参数而泛化性差（第 6.3 节）；FoolsGold 在 CIFAR-10 上、DeepSight 在 CIFAR-10 数据投毒场景下出现运行错误（表 6 与表 10 中的"-"）。

## 6. 干预动作

论文中的干预动作全部发生在服务器聚合阶段，少数方法还延伸到客户端训练与推理阶段。

- 剔除或选择客户端子集：Krum 只选一个更新作为聚合结果（公式 10），Multi-Krum 选 m 个取平均（公式 11），Bulyan 先用 Krum 选出集合 S（公式 14），DnC 选离群分数最低的 n−βf 个（第 5.1 节），SignGuard 选符号统计聚类的多数簇（第 5.1 节），Auror 用指示特征聚类后的多数簇确定良性客户端（第 5.2 节）。
- 坐标级稳健聚合：Coordinate-wise Median 逐坐标取中位数（公式 12），TrimmedMean 截尾后平均（公式 13），RFA 用几何中位数（公式 15），Bulyan 在每个坐标上取最接近中位数的若干坐标的平均（公式 14）。
- 重新加权：FLTrust 用 ReLU 截断的余弦相似度作为信任分数，把更新按服务器更新范数归一化后加权求和（公式 16、公式 17）；FoolsGold 用相似度分数做加权聚合（第 5.2 节）。
- 裁剪：NormClipping 按阈值 M 裁剪每个更新后取平均（公式 19）；CenteredClipping 以服务器上一轮的聚合结果为中心做迭代裁剪（公式 18）；FLAME 在聚类后按更新 L2 范数的中位数裁剪良性更新（第 5.2 节）；CRFL 在训练中做参数裁剪（第 5.2 节）。
- 加噪：FLAME 在聚合结果上加入高斯噪声，标准差取 λ 乘以更新范数的中位数，其中 λ 由差分隐私参数 ε 与 δ 决定（第 5.2 节）；CRFL 在训练中对参数做扰动（第 5.2 节）。
- 推理阶段的动作：CRFL 在推理时使用随机平滑，对预测给出认证的鲁棒界（第 5.2 节）。
- 结构性动作：Bucketing 先打乱客户端更新顺序并分桶，再在桶内聚合，用改变聚合结构的方式降低异质数据下恶意更新的影响（第 5.1 节）。

论文未说明的干预动作包括：按样本过滤训练数据、回滚到历史全局模型、仅报告可疑客户端而不改变聚合结果。论文中的防御都会改变聚合输出或筛选客户端更新。

## 7. 实验设置与主要结果

- 联邦设置：一个中央服务器加上全部参与的客户端（第 6.1 节），即不存在客户端采样；实验算法为 FedSGD 与 FedOpt（第 6.1 节），FedAvg 在框架中实现但未被列入统一对比（第 6.1 节、附录 B.1）。
- 模型与数据：MNIST 上的 LeNet-5，CIFAR-10 上的 ResNet-18（第 6.1 节）。
- 客户端数与恶意比例：表 9 报告 "Adversaries / Participants" 为 24/50 与 4/20；附录 B.6 的消融在 MNIST 上使用 0.1、0.2、0.48 三个攻击者比例，对应 50 个参与方中的 5、10、24 个。
- 轮次与超参数：FedSGD 在 MNIST 上 500 轮、CIFAR-10 上 800 轮，FedOpt 在两个数据集上均为 5×500 轮；批大小 64，学习率 0.01，动量 0.9，权重衰减 5e-4，MultiStepLR 在轮数的 0.5 与 0.8 处衰减，gamma 为 0.01（表 9）。时间开销实验则是在 MNIST、独立同分布、FedSGD 下训练 300 轮（附录 B.5）。
- 数据异质性：同时评测独立同分布（IID）与非独立同分布（non-IID）；IID 为数量与类别均衡；non-IID 采用 Dirichlet 分布 Dir(α)，α 取 0.5，α 越小类别越不均衡（第 6.1 节、表 9）；图 4 在 20 个客户端上可视化了 CIFAR-10 的两种划分。
- 投毒比例：数据投毒攻击的投毒比例为 0.32，即批大小 64 中 20 张被毒化（附录 B.4）。
- 指标：准确率与攻击成功率（第 6.1 节），以及派生指标定向攻击影响（公式 20）与定向防御稳健性（公式 21）。

关键结果：

- 攻击效果（表 4，数值为跨防御的平均准确率，越低表示攻击越强）：MNIST 上无攻击为 95.1，Gaussian 为 66.5，Sign Flipping 为 57.9，ALIE 为 57.6，IPM 为 56.4，Fang Attack 为 60.9，MinMax 为 60.3，MinSum 为 57.3，Mimic 为 93.7；CIFAR-10 上无攻击为 71.2，Gaussian 为 50.3，Sign Flipping 为 54.2，ALIE 为 70.1，IPM 为 65.5，Fang Attack 为 50.5，MinMax 为 65.7，MinSum 为 65.7，Mimic 为 65.5。论文总结 Gaussian、Sign Flipping 与 Fang Attack 总体攻击效果最强，ALIE 在 MNIST 上好而在 CIFAR-10 上差，原因是其 z_max 估计得到的攻击超参数偏小（第 6.2 节）。
- 数据投毒攻击（表 5）：MNIST 上平均 BadNets 的准确率为 94.2、攻击成功率为 73.3，DBA 为 93.3 与 39.6，Edge-case 为 84.5 与 59.7，Model Replacement 为 69.9 与 58.4，Neurotoxin 为 82.9 与 52.2，AlterMin 为 88.6 与 43.0，Label Flipping 为 91.5 与 26.6；CIFAR-10 上 BadNets 为 69.7 与 74.2，DBA 为 69.3 与 63.3，Edge-case 为 66.2 与 40.5，Model Replacement 为 63.4 与 57.3，Neurotoxin 为 69.0 与 25.5，AlterMin 为 58.2 与 5.1，Label Flipping 为 70.1 与 9.1。论文认为 BadNets、DBA 与 Edge-case 是最强的数据投毒攻击，原因是它们简单、自适应性强、不依赖复杂的超参数微调（第 6.2 节）。
- 算法差异：论文报告几乎所有模型投毒攻击在 FedSGD 下比在 FedOpt 下影响更大，而多数数据投毒攻击在 FedOpt 下定向影响更强（第 6.2.1 节、图 5）。
- 数据异质性差异：几乎所有模型投毒攻击在非独立同分布下效果更好，Gaussian 与 Sign Flipping 在独立同分布下更强，Fang Attack 在两种设置下都排在前列；数据异质性对数据投毒攻击的影响没有明确趋势（第 6.2.2 节、图 6）。
- 防御对模型投毒攻击（表 6，数值为平均准确率，越高表示防御越好）：MNIST 上 FLTrust 为 92.0，DnC 为 83.3，NormClipping 为 77.9，FLAME 为 76.6，SignGuard 为 74.2，Auror 为 73.8，Median 为 72.5，FoolsGold 为 70.3，CenteredClipping 为 66.8，DeepSight 为 66.3，Mean 为 62.4，RFA 为 59.5，TrimmedMean 为 59.1，Krum 为 58.4，Multi-Krum 为 57.2，Bulyan 为 56.4，Bucketing 为 38.5，CRFL 为 68.9；CIFAR-10 上 FLTrust 为 72.0，DnC 为 69.8，Median 为 68.8，FLAME 为 67.4，RFA 为 66.8，SignGuard 为 65.6，NormClipping 为 65.4，Multi-Krum 为 64.6，Bulyan 为 63.0，CenteredClipping 为 61.9，Krum 为 60.2，Mean 为 57.2，Auror 为 55.8，DeepSight 为 52.9，CRFL 为 51.4，Bucketing 为 41.1，FoolsGold 因运行错误显示为"-"。论文总结 Median、FLTrust、DnC 与 FLAME 总体最好（第 6.3 节）。
- 防御对数据投毒攻击（表 7 为 MNIST，表 10 为 CIFAR-10；攻击成功率越低越好）：MNIST 上平均攻击成功率 FLTrust 为 18.8，FLAME 为 22.2，Bulyan 为 27.8，Krum 为 29.1，Multi-Krum 为 32.5，SignGuard 为 33.6，DeepSight 为 35.7，Auror 为 42.1，Median 为 42.4，FoolsGold 为 47.9，DnC 为 53.2，RFA 为 62.5，TrimmedMean 为 69.2，CenteredClipping 为 74.1，NormClipping 为 75.6，CRFL 为 76.0，Mean 为 76.7，Bucketing 为 81.2；CIFAR-10 上平均攻击成功率 Multi-Krum 为 8.6，Krum 为 9.0，Bulyan 为 11.3，DnC 为 17.6，FLAME 为 17.9，Auror 为 26.5，SignGuard 为 37.3，FLTrust 为 46.3，RFA 为 51.7，Median 为 54.5，NormClipping 为 54.5，CenteredClipping 为 59.8，TrimmedMean 为 62.2，Bucketing 为 63.1，CRFL 为 63.4，Mean 为 57.9，FoolsGold 与 DeepSight 显示为"-"。论文建议在涉及数据投毒时纳入 Krum 与 Multi-Krum，在涉及模型投毒时纳入 FLAME（第 6.3 节）。
- 防御在非独立同分布下的表现：对模型投毒攻击，独立同分布下 DnC、FLTrust、FLAME、Median 与 FoolsGold 的平均准确率能维持在约 80% 及以上；非独立同分布下只有 FLTrust 约 80%，第二梯队的 DnC 与 NormClipping 约 66%（第 6.3.2 节、图 8）。对数据投毒攻击，独立同分布下 FLAME、Multi-Krum、Krum 与 Bulyan 的定向防御稳健性约为 1.8，非独立同分布下最好的 FLAME、FLTrust、Multi-Krum 与 Bulyan 只有约 1.6（第 6.3.2 节）；论文指出只有 FLAME 与 Multi-Krum 达到约 1.75，仍远低于最优值 2（第 6.3.1 节）。
- 攻击者比例消融（附录 B.6、图 10，MNIST、LeNet-5、比例 0.1 至 0.48）：Gaussian 的攻击使全局准确率下降约 15%，Sign Flipping 与 Fang Attack 分别下降约 35% 与 31%；数据投毒攻击的准确率几乎不变而攻击成功率整体上升约 4% 至 37%，其中 BadNets 与 DBA 上升更多，Edge-case 上升不明显；防御方面 Krum 下降约 35%，FLTrust 与 DnC 下降约 1%，FLAME 下降约 20%。

## 8. 开销

论文在附录 B.5 报告了逐轮的平均时间开销，实验设置为 MNIST、独立同分布、FedSGD、300 轮（图 9）。

- 攻击（图 9a，单位秒）：无攻击 0.17，Sign Flipping 0.17，Mimic 0.17，BadNets 0.17，DBA 0.17，Gaussian 0.18，Label Flipping 0.18，Model Replacement 0.19，Edge-case 0.19，IPM 0.21，ALIE 0.25，Neurotoxin 0.45，MinMax 0.78，MinSum 0.80，AlterMin 1.74，Fang Attack 16.55。论文指出 Fang Attack 的开销是正常训练的 97 倍，原因是它反复执行 Krum 算法来优化恶意更新（附录 B.5）。
- 防御（图 9b，单位秒）：Mean 0.01，CenteredClipping 0.03，CRFL 0.04，Bucketing 0.15，Krum 0.23，Multi-Krum 0.24，FLTrust 0.36，Median 0.37，RFA 0.39，Bulyan 0.53，SignGuard 0.68，TrimmedMean 0.72，FLAME 0.88，NormClipping 0.91，Auror 1.94，DnC 7.35，FoolsGold 16.34，DeepSight 1710.69。论文给出的倍数为：DeepSight、FoolsGold、DnC、Auror 分别消耗 Mean 的 1,710,000 倍、1,634 倍、735 倍与 194 倍；Bulyan、RFA、Median、Multi-Krum、Krum 等稳健统计方法只为 Mean 的 15 倍至 53 倍（附录 B.5）。
- 复杂度：表 3 给出各防御的时间复杂度，例如 Krum 与 Multi-Krum 为 O(dn²)，Coordinate-wise Median 为 O(dn)，TrimmedMean 为 O(dn log n)，Bulyan 为 O(dn²)，RFA 为 O(Tdn)，FLTrust 为 O(dn)，CenteredClipping 为 O(dn)，DnC 为 O(d_sub³)（取决于子采样维度），SignGuard 为 O(dn+n log n)，Bucketing 取决于所用聚合器（默认 Krum，故为 O(dn²)），Auror 为 O(dn) 加上对 s 个特征的 O(sn)，FoolsGold 为 O(sn²)，NormClipping 与 CRFL 为 O(dn)，DeepSight 为 O(dn²)，FLAME 为 O(dn²)。其中 d 是更新维度，n 是参与方数量，T 是 Weiszfeld 迭代次数，s 是选定特征数。
- 通信与存储开销：论文未报告。
- 基准框架自身的训练成本：论文未报告。

## 9. 假设、局限与自适应攻击

论文方法成立所依赖的假设：

- 服务器诚实，攻击者只来自被攻陷的客户端（附录 B.3）；恶意服务器场景论文未说明。
- 良性客户端占多数，且不同防御对恶意数量有不同上界，例如 Krum 要求 2f+2<n，Coordinate-wise Median、TrimmedMean、RFA 等要求 2f+1<n，Bulyan 要求 4f+3≤n，Bucketing 要求 2f+2<n/S（表 3）。
- 数据分布假设：Krum、Multi-Krum、Coordinate-wise Median、TrimmedMean、Bulyan、RFA、DnC、Auror、DeepSight 假设均衡独立同分布；FoolsGold 假设均衡非独立同分布；FLTrust、SignGuard、Bucketing、NormClipping、CRFL、FLAME 同时覆盖独立同分布与非独立同分布；CenteredClipping 假设均衡与不均衡的独立同分布（表 3）。
- 参考与历史假设：FLTrust 假设服务器持有一个干净的小数据集（第 5.1 节）；CenteredClipping、FoolsGold、DeepSight、FLAME 假设服务器可以使用跨轮历史（表 3）；CenteredClipping 还假设工作节点使用动量（表 3、公式 18）。
- 攻击侧假设：ALIE 假设客户端模型参数独立同分布且服从正态分布（第 4.1.3 节）；AlterMin 假设独立同分布训练与特定验证数据样本，并且只控制少量（通常为一个）不串谋的客户端、无法访问其他客户端的更新（第 4.3 节）；Fang Attack 需要串谋并知道其他攻击者的本地数据、模型与梯度（第 4.1.3 节）；部分攻击需要知道聚合规则或防御方法（第 4.1.3 节）。
- 实验层面的假设：客户端全部参与、没有客户端采样（第 6.1 节）；没有安全聚合；数据投毒使用 0.32 的固定投毒比例（附录 B.4）。

论文自述的局限：

- 超参数自适应性不足会显著削弱攻击与防御。ALIE 在 CIFAR-10 上因 z_max 估计出的超参数偏小而表现差，作者认为 z_max 需要针对数据集人工微调（第 6.2 节）；FoolsGold 与 DeepSight 因依赖数据的超参数而缺乏泛化性（第 6.3 节）；部分防御在 CIFAR-10 上因非自适应超参数直接出现运行错误，表中记为"-"（表 6、表 10）。
- 非独立同分布场景缺乏有效防御：对模型投毒攻击，只有 FLTrust 平均准确率约 80%；对数据投毒攻击，最好方法的定向防御稳健性仅约 1.6（第 6.3.2 节）。
- 数据投毒攻击的防御上限仍低：只有 FLAME 与 Multi-Krum 达到约 1.75，远低于最优值 2（第 6.3.1 节）。
- 数据异质性对数据投毒攻击的影响没有明确趋势（第 6.2.2 节）；现有防御主要处理标签偏斜与数量偏斜，特征偏斜与质量偏斜仍未被充分探索（第 5.3 节）。

关于自适应攻击者：论文没有系统评估"防御方针对攻击自适应调整后再面对自适应攻击者"这一设定。论文中出现的"自适应"主要是攻击自身的自适应能力，例如基于统计的规避与基于优化的规避会针对已知聚合规则调整恶意更新（第 4.1.3 节），论文也把 Adaptive Attacks 与 3DFed 这类基于反馈的优化列为攻击设计趋势（第 4.4 节），但没有给出自适应攻击者的实验评测。因此在本报告的结构化字段中记为未评估。

迁移到联邦大模型 LoRA 微调时可能失效的假设（以下均为分析）：

- 分析：论文的全部防御都在 d 维全参数更新向量上定义，逐坐标中位数、坐标排序截尾、逐坐标符号统计、成对欧氏距离与 SVD 都依赖稠密的全参数张量。LoRA 只上传低秩矩阵 A 与 B（或增量 BA），可训练参数量远小于 d，逐坐标统计的样本量和尺度都会改变，需要按适配器与目标模块分别重新定义统计粒度。
- 分析：论文的"均衡独立同分布"假设建立在 10 类图像分类的标签分布上，而联邦大模型指令微调的异质性体现在任务、领域、语言与样本长度上，类别概念不可直接对应，Krum、Median、TrimmedMean 等的均衡假设更可能不成立。
- 分析：FLTrust 依赖服务器持有与训练数据同分布的干净小数据集，其在论文中是 MNIST 或 CIFAR-10 的小样本；在大模型微调中构造同分布的干净指令数据成本更高，而且"同分布"本身更难定义。
- 分析：论文的评测是 50 个或 20 个客户端全部参与；若联邦 LoRA 采用每轮采样，服务器在单轮内看不到全部客户端，Krum 的成对距离、Bulyan 的 4f+3≤n 与 Bucketing 的分桶规模等前提都需要重新校准。
- 分析：论文的准确率与攻击成功率基于 10 类分类和投毒测试样本，公式 20 与公式 21 还依赖"无攻击准确率"。生成式模型没有直接的分类准确率，后门或越狱的成功需要生成式评测，论文未涉及这部分，指标需要重新设计。
- 分析：论文的触发器是图像补丁，后门表现为把带触发器的图像预测为目标类别；文本触发器、指令型后门与安全对齐破坏不在论文范围内。Neurotoxin 依赖随机梯度下降的梯度稀疏性来选择不常更新的坐标，LoRA 的低秩参数化会改变这种稀疏结构，该假设需要重新验证。
- 分析：论文把训练后期投毒定义为对本地训练结果的操纵，例如缩放与投影后提交，这一位置与 LoRA 场景中"上传前对适配器增量做缩放或投影"对应，机制上可以直接迁移；但论文没有讨论适配器合并、多适配器组合或适配器供应链发布等环节，所以防护库若面向参数高效微调供应链，这部分没有论文依据。

## 10. 对防护库设计的含义

以下各条均为分析。

- 分析：库的通用采集底座需要在"服务器收到更新"这一信任边界上抽取每个客户端的完整更新张量，包括 FedSGD 与 FedOpt 下的差值形式和 FedAvg 下的本地权重形式，并携带客户端标识、轮次标识与参与集合。这是 Krum、Multi-Krum、Coordinate-wise Median、TrimmedMean、Bulyan、RFA、NormClipping、SignGuard、Bucketing、DnC、Auror、FoolsGold、CenteredClipping、CRFL、DeepSight、FLAME 的共同最小输入，属于通用需求；论文的算法 1 与第 5 节给出了这一视图的原始定义。
- 分析：库需要一份按轮、按客户端的特征缓存，保存当前轮更新、上一轮聚合结果、逐客户端更新范数与（可选的）输出层指示特征。CenteredClipping 需要上一轮聚合结果与客户端动量，FoolsGold 需要历史多轮的指示特征与相似度，DeepSight 与 FLAME 在表 3 中被标为使用服务器历史。历史缓存是通用能力，但只有一部分插件声明依赖它。
- 分析：库应把"服务器是否持有干净参考数据"做成插件可声明的依赖项，而不是隐式全局开关。FLTrust 需要干净数据集与服务器模型更新 g_0（第 5.1 节），附录 A 也把"服务器数据假设"作为框架层的一个模块，图 2 中有对应的 Server Data Assumption 组件。这样在同一次训练中，依赖干净参考的插件与不依赖它的插件可以共存。
- 分析：库的服务器钩子应支持插件对客户端模型做额外前向计算并访问批量推理接口，因为 DeepSight 需要在最多 20,000 个随机数据点上取预测分数分布并计算 Division Differences、Normalized Update Energy 与余弦距离，DnC 需要随机子采样与 SVD，SignGuard 需要随机坐标采样与聚类（第 5.1、5.2 节与附录 B.5）。论文也指出这类特征级分析是时间开销最高的部分，因此该接口应带有开销预算与可关闭的开关。
- 分析：干预接口可以统一为服务器端的"每客户端保留权重、裁剪阈值、聚合输出与噪声参数"四类返回值，覆盖论文出现的剔除客户端、重新加权、裁剪与加噪四类动作（第 5.1、5.2 节）；同时需要一个客户端训练阶段的插桩点，供 CRFL 这类在本地训练中做参数裁剪与扰动、在推理时做随机平滑的方法使用（第 5.2 节）。样本级过滤与模型回滚在论文中没有依据，不应作为这套方法的必需接口。
- 分析：面向联邦 LoRA 的迁移需要采集底座以"适配器增量"为一等张量对象，记录秩、目标模块名与缩放系数，并在适配器层粒度上重新实现范数、符号、余弦与距离统计，才能复用论文中同类插件；这是本文没有覆盖、但对我们的库属于必需的新增能力。

## 11. 原文依据

1. 章节：第 6.1 节 "Models and Datasets"。支撑：第 1 节与第 7 节的模型与数据规模。原文："This paper trains LeNet-5 [26] on MNIST [26] and ResNet-18 [17] on CIFAR-10 [23] dataset. MNIST includes 60,000 training and 10,000 testing grayscale images (28x28 pixels) of handwritten digits across 10 classes."
2. 章节：第 6.1 节 "Federated Learning System"。支撑：第 7 节与第 9 节关于全部参与与所用算法的论断。原文："We simulate a FL system with a central server and fully participating clients. For FL algorithms, we observe that FedSGD and FedOpt are widely utilized in poisoning attacks, as highlighted in prior studies"
3. 章节：附录 B.3 威胁模型。支撑：第 2 节的攻击者身份与数量。原文："Among these clients, f participants are either malicious or compromised by adversaries, potentially engaging in model poisoning attacks or data poisoning attacks as previously described."
4. 章节：第 4.1.1 节 "Training-time Poisoning Attacks"。支撑：第 3 节本地训练过程这一攻击入口。原文："In these attacks, the adversary can alter training configurations such as the number of epochs, learning rate, loss function, and other parameters."
5. 章节：第 4.1.3 节 "Update-time Poisoning Attacks"。支撑：第 3 节更新上传前的后处理这一攻击入口以及窃听与串谋能力。原文："These attacks occur when clients submit updates, enabling malicious clients to eavesdrop on benign ones or collude with others to launch attacks. Known as omniscient attacks, they rely on information from others."
6. 章节：第 5 节开头。支撑：第 6 节的干预动作分类与动作位置。原文："Robust aggregation aims to generate reliable outputs based on robust statistics [19] even with malicious updates, while outlier detection identifies and removes abnormal updates that may harm performance."
7. 章节：第 5.1 节 FLTrust。支撑：第 5 节与第 9 节关于服务器干净参考数据这一输入与假设。原文："FLTrust [8] assumes that the server has access to a clean, small dataset, which is used to train the server model and bootstrap trust during the training process."
8. 章节：第 4.1.3 节 ALIE。支撑：第 9 节关于 ALIE 的独立同分布与正态分布假设。原文："The ALIE attack assumes that client model parameters are IID and follow a normal distribution. Leveraging the empirical variance of benign weight updates following normal distribution, ALIE constrains the perturbation range of malicious updates to ensure stealth."
9. 章节：附录 B.5 "Comparison of Time Overhead"。支撑：第 8 节的开销数值。原文："The most time-intensive defenses, D.S., F.G., DnC, and Auror, consume 1,710,000×, 1,634×, 735×, and 194× times of the Mean's cost, respectively."
10. 章节：附录 A "Overview of Our FLPoison"。支撑：第 4 节与第 10 节关于框架分层与模块化插件的论断。原文："As illustrated in Figure 2, our FLPoison is highly decoupled and modular, consisting of three layers: the federated learning layer, the attack layer, and the aggregation layer."

```json
{
  "key": "zhang2025flpoison",
  "title": "SoK: Benchmarking Poisoning Attacks and Defenses in Federated Learning",
  "year": 2025,
  "paper_type": "benchmark",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted", "backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {"what": "客户端上传的模型更新向量或本地权重（FedSGD/FedOpt 的差值，FedAvg 的本地权重）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "客户端更新之间的成对平方欧氏距离与 Krum 分数、MinMax/MinSum 的距离约束量", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐坐标与逐层稳健统计量（中位数、排序分位、截尾均值、几何中位数近似）", "where": "server_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐客户端更新的 L2 范数、范数中位数与裁剪阈值", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "跨轮历史（上一轮聚合结果、客户端动量、历史多轮指示特征与余弦相似度）", "where": "server_aggregate", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "服务器干净参考数据集与服务器模型更新 g0", "where": "server_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "子采样坐标上的更新、逐样本预测分数分布（Division Differences、Normalized Update Energy、余弦距离）", "where": "server_aggregate", "granularity": "sample", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "评估阶段的测试集准确率与投毒测试样本攻击成功率", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "客户端本地训练批次与毒化样本（触发器嵌入、标签替换、梯度掩码等攻击插件输入）", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["exclude_client", "reweight", "clip", "add_noise"],
  "intervention_where": ["both"],
  "assumptions": [
    "服务器诚实，攻击者只来自被攻陷的客户端（附录 B.3）",
    "良性客户端占多数，且不同防御对恶意数量有上界要求，例如 Krum 要求 2f+2<n、Bulyan 要求 4f+3≤n（表 3）",
    "多数防御假设客户端数据为均衡独立同分布，非独立同分布下性能显著下降（表 3、第 6.3.2 节）",
    "FLTrust 假设服务器持有与训练数据同分布的干净小数据集（第 5.1 节）",
    "CenteredClipping、FoolsGold、DeepSight、FLAME 假设服务器可使用跨轮历史，CenteredClipping 还假设客户端使用动量（表 3）",
    "ALIE 假设客户端模型参数独立同分布且服从正态分布（第 4.1.3 节）",
    "AlterMin 假设独立同分布训练与特定验证样本，且只控制少量不串谋客户端（第 4.3 节）",
    "Fang Attack 等聚合器相关攻击假设知道聚合规则，否则随机假定一个聚合规则（第 4.1.3 节）",
    "实验假设客户端全部参与、无安全聚合、无恶意服务器（第 6.1 节、附录 B.3）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Section 6.1 Models and Datasets", "supports": "第 1 节与第 7 节的模型与数据规模", "text": "This paper trains LeNet-5 [26] on MNIST [26] and ResNet-18 [17] on CIFAR-10 [23] dataset. MNIST includes 60,000 training and 10,000 testing grayscale images (28x28 pixels) of handwritten digits across 10 classes."},
    {"section": "Section 6.1 Federated Learning System", "supports": "第 7 节与第 9 节关于全部参与与所用算法的论断", "text": "We simulate a FL system with a central server and fully participating clients. For FL algorithms, we observe that FedSGD and FedOpt are widely utilized in poisoning attacks, as highlighted in prior studies"},
    {"section": "Appendix B.3 Threat Model", "supports": "第 2 节的攻击者身份与数量", "text": "Among these clients, f participants are either malicious or compromised by adversaries, potentially engaging in model poisoning attacks or data poisoning attacks as previously described."},
    {"section": "Section 4.1.1 Training-time Poisoning Attacks", "supports": "第 3 节本地训练过程这一攻击入口", "text": "In these attacks, the adversary can alter training configurations such as the number of epochs, learning rate, loss function, and other parameters."},
    {"section": "Section 4.1.3 Update-time Poisoning Attacks", "supports": "第 3 节更新上传前的后处理这一攻击入口以及窃听与串谋能力", "text": "These attacks occur when clients submit updates, enabling malicious clients to eavesdrop on benign ones or collude with others to launch attacks. Known as omniscient attacks, they rely on information from others."},
    {"section": "Section 5 opening", "supports": "第 6 节的干预动作分类与动作位置", "text": "Robust aggregation aims to generate reliable outputs based on robust statistics [19] even with malicious updates, while outlier detection identifies and removes abnormal updates that may harm performance."},
    {"section": "Section 5.1 FLTrust", "supports": "第 5 节与第 9 节关于服务器干净参考数据这一输入与假设", "text": "FLTrust [8] assumes that the server has access to a clean, small dataset, which is used to train the server model and bootstrap trust during the training process."},
    {"section": "Section 4.1.3 ALIE", "supports": "第 9 节关于 ALIE 的独立同分布与正态分布假设", "text": "The ALIE attack assumes that client model parameters are IID and follow a normal distribution. Leveraging the empirical variance of benign weight updates following normal distribution, ALIE constrains the perturbation range of malicious updates to ensure stealth."},
    {"section": "Appendix B.5 Comparison of Time Overhead", "supports": "第 8 节的开销数值", "text": "The most time-intensive defenses, D.S., F.G., DnC, and Auror, consume 1,710,000×, 1,634×, 735×, and 194× times of the Mean's cost, respectively."},
    {"section": "Appendix A Overview of Our FLPoison", "supports": "第 4 节与第 10 节关于框架分层与模块化插件的论断", "text": "As illustrated in Figure 2, our FLPoison is highly decoupled and modular, consisting of three layers: the federated learning layer, the attack layer, and the aggregation layer."}
  ]
}
```
