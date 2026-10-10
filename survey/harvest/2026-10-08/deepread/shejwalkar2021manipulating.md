# shejwalkar2021manipulating：Manipulating the Byzantine: Optimizing Model Poisoning Attacks and Defenses for Federated Learning

## 1. 基本信息

场景是传统联邦学习（classic federated learning，FL），不是联邦大模型，也不是集中式大模型训练，更与参数高效微调（parameter-efficient fine-tuning，PEFT）供应链无关。论文同时覆盖跨孤岛（cross-silo，客户端数十到数百、每轮全部参与）与跨设备（cross-device，客户端数百万、每轮只抽一部分）两种 FL 设置（Section II-A），并在实验中分别用 CIFAR10 模拟跨孤岛与跨设备（Section VI-E）。论文类型是"攻击加防御"：主体贡献是一个通用的模型投毒（model poisoning）优化框架与据此构造的攻击（Section IV），第二部分贡献是一个新的鲁棒聚合算法（aggregation algorithm，AGR）"分而治之"（divide-and-conquer，DnC，Section VII）；本报告在 JSON 中按单一枚举记为 attack。

训练阶段是标准的联邦梯度平均式训练：第 t 轮服务器把全局模型参数 θ_t 广播给被选中的客户端，客户端用本地数据的一个随机小批量（minibatch）b 计算随机梯度 ∇_{t,i} = ∂L(b,θ_t)/∂θ_t 并同步上传，服务器用某个 AGR 聚合，再用随机梯度下降（SGD）更新并广播新的全局模型，直到在验证集 D_val 上收敛，最终输出验证准确率最高的全局模型（Section II-A）。论文没有本地多步训练的描述。

模型与数据规模（Section V-A）：CIFAR10 是 10 类平衡图像分类，60,000 张 32×32 RGB 图像，使用 50 个客户端、每个 1,000 个样本，验证集与测试集各 5,000，全局模型为 Alexnet 与 VGG11；MNIST 是 10 类平衡分类，70,000 张 28×28 灰度图，使用 100 个客户端、每个 600 个样本，模型为层大小 {784, 512, 10} 的全连接网络；Purchase 是 100 类不平衡分类，197,324 条长度 600 的二值特征向量，使用 80 个客户端、每个 2,000 个训练样本，模型为层大小 {600, 1024, 100} 的全连接网络；FEMNIST 有 3,400 个客户端、62 类、共 671,585 张灰度图，每客户端样本数的均值与标准差分别为 226.83 与 88.94，每轮从 3,400 个客户端中随机选 60 个。全文没有任何语言模型、Transformer 或 LoRA（low-rank adaptation）内容。

## 2. 威胁模型

攻击者是恶意客户端（malicious client）。论文假设攻击者控制 n 个客户端中的至多 m 个，且恶意客户端数少于良性客户端数，即 (m/n) < 0.5，否则任何拜占庭鲁棒 AGR 都无法抵御投毒（Section III）。默认实验设置为 20% 恶意客户端，"例如 MNIST 用 20 个恶意客户端"（Section V-B）。

能力方面，论文假设攻击者可以访问每一轮广播的全局模型参数，并且可以直接篡改恶意设备上的梯度，"在每一轮把它们共享给服务器之前"（Section III 与 Section II-B）。也就是说，攻击不需要修改本地数据、损失函数或优化器，而是直接替换将要上传的更新向量。

知识方面，论文按两个维度把攻击者分为四类（Table I）：agr-updates（同时知道良性设备的梯度与服务器的 AGR 算法）、agr-only（知道 AGR，但不知道良性设备梯度，只能用恶意设备上的良性数据自行计算良性梯度）、updates-only（知道良性设备梯度，但不知道 AGR）、agnostic（两者都不知道，是最弱的攻击者）。论文明确指出，此前的 Fang 攻击假设完全知道 AGR，LIE 攻击假设完全知道良性设备梯度，都没有同时考虑这两个维度（Section III）。

目标是"无目标投毒"（untargeted poisoning）：让恶意客户端上传的梯度使最终全局模型在任意测试输入上的准确率都下降（Section III）。论文明确把定向攻击与后门（backdoor）攻击划为另一类并排除在本文范围之外，理由是后门属于 targeted attack 的子集（Section II-B）。

防御者是中央服务器/服务提供商，它运行一个拜占庭鲁棒 AGR，能够看到每个参与客户端提交的梯度，并且知道恶意客户端数量的上界 m（Krum、Trimmed-mean 与 DnC 都以 m 作为输入参数，Section II-C 与 Algorithm 2）。服务器信任"良性客户端占多数"这一前提。论文未说明服务器是否持有干净的带标签验证数据来支撑 DnC；被比较的 Fang 元防御需要计算模型在数据上的损失与误差（Section II-C7），而 Section II-A 提到 FL 的收敛判据是在验证数据 D_val 上的损失，因此论文隐含服务器保有验证集，但 DnC 本身不使用它。论文也没有讨论安全聚合、差分隐私或加密上传，即隐含服务器能看到原始明文更新。

## 3. 攻击入口与流程位置

攻击入口是"更新上传前的后处理"：恶意客户端在本地完成梯度计算之后、把更新交给服务器之前，直接把该梯度替换成构造出来的恶意向量。论文原文把模型投毒定义为"攻击者可以直接篡改恶意设备上的梯度，在每一轮把它们共享给服务器之前"（Section II-B）。攻击不进入本地数据准备（不投毒训练数据），不进入本地训练过程（不改损失、优化器、步数），也不进入服务器聚合、全局模型下发或评估部署环节。论文特别指出，由于数据投毒无法计算任意梯度，用训练数据投毒来模仿模型投毒的恶意梯度并不容易，所以本文关注更强的无目标模型投毒（Section II-B）。本地数据只在 agr-only 与 agnostic 两种攻击者手中被用到，用途是计算参考良性聚合，而不是被投毒。

具体操作步骤如下（Section IV-A、IV-D、VI-C2）：

1. 攻击者选定自己的知识等级（Table I）。
2. 计算参考良性聚合 ∇b：agr-updates 与 updates-only 攻击者直接对已知的良性梯度取平均；agr-only 与 agnostic 攻击者用恶意设备上持有的良性数据算出 m 个良性梯度再取平均（Section IV-B 开头）。
3. 选择扰动方向 ∇p，论文给出三种：反向单位向量（inverse unit vector，−∇b/‖∇b‖₂）、反向标准差（inverse standard deviation，−std(∇_{i∈[n]})）、反向符号（inverse sign，−sign(f_avg(∇_{i∈[n]}))）（Section IV-A）。
4. 固定 ∇p，用 Algorithm 1 在一个预言机（oracle）O 的判定下搜索使攻击目标成立的最大缩放系数 γ，目标函数随 AGR 与知识等级不同而不同（公式 (2) 至 (7)）。
5. 所有恶意客户端提交相同的恶意更新 ∇m = ∇b + γ∇p（Section IV-A、IV-C）。

针对具体 AGR 的定制目标为：Krum 要让 Krum 选中某个恶意梯度（公式 (3)）；Multi-krum 要让尽可能多的恶意梯度进入其选择集 S（公式 (4)）；Bulyan 采用与 Multi-krum 相同的策略，并论证其第二阶段的 Trimmed-mean 过滤无法有效移除这些恶意梯度（Section IV-B3）；AFA 用 f_afa 计算选择集 S，并假设每轮各客户端权重相同（Section IV-B4）；Trimmed-mean 与 Median 直接最大化 ‖∇b − f_agr(∇m ∪ ∇_benign)‖₂（公式 (5) 及其对 Median 的改写）；对 Fang 防御，论文论证只要把恶意梯度写成"良性梯度平均值加上任意大的向量"就能使其评分机制给良性梯度与恶意梯度几乎相同的分数，从而从根本上失效（Section IV-B7）。

DnC 这一防御部分所针对的攻击入口与上面相同，都是服务器收到的客户端更新；它的检测与干预都发生在服务器侧的聚合环节，不改变客户端行为。

## 4. 方法原理

攻击部分的核心思想是：每个 FL 轮次中，为了让全局模型受到最大破坏，恶意客户端希望服务器算出的聚合结果尽量远离一个参考良性聚合 ∇b，同时不被鲁棒 AGR 识别。一般形式写作在所有恶意客户端提交同一向量 ∇m = ∇b + γ∇p 的约束下，最大化 ‖∇b − f_agr(∇m_{i∈[m]} ∪ ∇_{i∈[m+1,n]})‖₂（公式 (1)）。由于 Krum、Trimmed-mean、Bulyan 等鲁棒 AGR 一般不可微，无法用梯度下降求解，论文改为固定扰动方向 ∇p、只搜索最优缩放系数 γ，得到公式 (2)。

求解 γ 的 Algorithm 1（Section IV-D）思路是：从一个较大的 γ 出发，按步长 step 反复减小 γ，直到预言机 O 返回 True（例如对 Krum 就是第一次出现恶意梯度被选中）；随后把步长减半，反向增大 γ 直到 O 返回 False；如此在"可行最小 γ"与"可行最大 γ"之间反复振荡并不断减半步长，直到 γ 的变化小于阈值 τ，最后输出可行的 γ_succ。预言机 O 以良性梯度集合与 γ 为输入，按各攻击目标（如公式 (3)、(6)）判定可行性。

扰动方向的选择被论文视为攻击效果的关键（Section VI-C）。论文给出一个可迁移的选法：在知道 AGR 时，攻击者先在缩小规模的模拟 FL 设置上（例如 MNIST 用 20 个良性加 4 个恶意客户端）仿真各扰动方向的攻击效果，选效果最好的方向；在不知道 AGR 时，选在尽可能多的 AGR 上效果最好的方向（Section VI-C2）。论文报告模拟设置（浅色柱）与真实 FL（深色柱）中不同扰动的相对优劣一致，即这种可迁移性成立（Figure 2、Figure 7）。

AGR-agnostic 攻击的核心直觉是：鲁棒 AGR 之所以能识别恶意更新，是因为恶意更新偏离良性更新的"团"（clique），于是两个新攻击把搜索限制在良性更新团内。Min-Max 攻击（公式 (6)）要求恶意梯度到任意其他梯度的最大距离不超过任意两个良性梯度之间的最大距离；Min-Sum 攻击（公式 (7)）要求恶意梯度到所有良性梯度的平方距离之和不超过任一良性梯度到其他良性梯度的平方距离之和。由于 Min-Sum 的约束更紧，它的恶意梯度更靠近 ∇b，因此对 Krum 与 Bulyan 更有效；Min-Max 的搜索半径更大、能让更多恶意梯度进入 Multi-krum 的选择集，因此对 Multi-krum 与 AFA 更有效（Section VI-A 结尾、Figure 1-(b, c)）。

防御部分 DnC 的核心思想来自对攻击的三条教训（Section VII-A）：其一，既有鲁棒 AGR 的误差界依赖输入维度，神经网络梯度维度极高使理论界与经验误差一起爆炸，所以必须降维；其二，非凸优化下的收敛保证没有意义，因为攻击正是把模型推向次优局部最优，因此防御应给出"恶意更新移除"的保证；其三，基于距离或逐维裁剪的过滤不够，Trimmed-mean 与 Median 允许攻击者显著偏移聚合结果，Krum、Multi-krum、Bulyan 允许恶意梯度既靠近良性梯度又足以投毒。因此 DnC 采用基于奇异值分解（singular value decomposition，SVD）的谱方法检测并剔除离群点，并用随机维度采样降维。

DnC 的算法（Algorithm 2）是：每轮迭代先随机抽取一个大小为 b 的维度索引有序集合 r，对所有输入梯度做维度子采样；计算子采样梯度的逐维均值 μ 并做中心化，得到 n×b 的中心化矩阵；求该矩阵的右奇异向量 v（最大方差方向）；对每个梯度计算离群分数 s_i = (⟨∇_i − μ, v⟩)²；保留分数最低的 n − c·m 个梯度加入"好集合"；重复 n_iters 次后，取所有好集合的交集 I_final，最终聚合结果是交集中梯度的平均值。论文对 iid 数据集取 n_iters = 1、c = 1、b = 10,000，对 FEMNIST 取 n_iters = 1、c = (n−1)/n、b = 10,000（Section VII-C1 与 VII-C2）。

理论保证方面，论文引用 ε-谱可分性（ε-spectral separability，Definition 1）：若混合分布 U = (1−ε)B + εM 的顶部右奇异向量 v 能把良性分布 B 与恶意分布 M 分开，则沿该方向去掉投影最大的 ε 比例样本即可去掉恶意样本。Lemma 1 给出充分条件：当 0 < ε < 0.5、两个分布的协方差都满足 Σ_B, Σ_M ⪯ σ²I 时，若 ‖μ_B − μ_M‖²₂ ≥ 6σ²/ε，则 B 与 M 是 ε-谱可分的；证明在附录 B。论文进一步论证，对 FL 投毒而言，能有效投毒的恶意梯度均值与良性梯度均值相距足够远，因此可以被谱方法过滤；反之能躲过该条件的恶意梯度对全局模型准确率没有影响（Section VII-B 与 Figure 5）。

## 5. 检测或防御所需的数据

DnC 需要的数据与采集点如下。

- 每个参与客户端提交的完整梯度或模型更新向量。采集位置是服务器收到更新时（聚合之前），粒度是逐客户端，并且需要在模型参数向量内部做维度级访问，因为 Algorithm 2 要在 d 维中随机抽取 b = 10,000 个维度做子采样。这一项需要额外计算（求均值、中心化、求顶部右奇异向量、计算离群分数），论文明确写出 SVD 本身需要 O(d³) 的内存与计算（Section VII-B）。不需要跨轮历史，不需要干净参考数据，也不需要其他客户端的额外信息（DnC 只用本轮收到的全部更新）。
- 每轮参与客户端数量 n 与恶意客户端数量上界 m。它们是聚合算法的输入参数，用于决定要剔除的更新条数 c·m（Algorithm 2 第 1 行与第 10 行）。粒度是逐轮。论文没有说明服务器如何获得 m，只把它当作已知上界；Trimmed-mean 的裁剪参数 β 同样取 m（Section II-C4）。
- 过滤比例 c、迭代次数 n_iters、子采样维度数 b。这三个是算法超参数（Algorithm 2 第 1 行），论文没有给出自动选择方法，只给出实验取值。
- 服务器验证集上的全局模型准确率。论文用它定义攻击影响，A_θ 表示无攻击时全部训练轮次中最好的全局模型准确率，A*_θ 表示受攻击时的准确率，I_θ = A_θ − A*_θ（Section V-B）；最终 FL 输出也是验证准确率最高的全局模型（Section II-A）。这一项在评估阶段采集，粒度是逐轮模型，需要干净的带标签验证数据，但不需要额外的前向或反向计算之外的训练流程改动。

DnC 明确不需要：逐样本损失、隐藏层激活、输出文本、逐批梯度、跨轮更新历史、根数据集（root dataset）、其他客户端的数据视图。作为对比，论文中被比较的 Fang 元防御需要服务器计算"用包含或不包含某个梯度所得到的两个聚合分别更新后的模型的损失与/或误差"，因此需要带标签数据与额外的模型评估计算（Section II-C7）；那是基线方法的需求，不是 DnC 的需求。论文未说明 DnC 是否需要验证集。

攻击会在哪些可观测量上留下痕迹、论文声称能绕过哪些检测：

- 留下痕迹的可观测量是服务器在每个轮次收到的逐客户端更新向量本身。AGR-tailored 攻击刻意让该向量远离良性聚合 ∇b，从而在"到良性聚合的距离"这一量上留下痕迹（公式 (1)、(2)、(5)）；AGR-agnostic 的 Min-Max 与 Min-Sum 攻击则刻意把恶意梯度约束在良性更新形成的团内，使距离、L2 范数与分布都与良性更新接近，从而让基于距离、分布差异和 Lp 范数差异的检测失效（Section IV-C 明确列出鲁棒 AGR 依赖的三类判据，并说明攻击如何同时规避这三类）。
- 论文声称能绕过的检测包括：Krum、Multi-krum、Bulyan、Trimmed-mean、Median、AFA 六种鲁棒 AGR（Table II、Table III），以及 Fang 的元防御（Section IV-B7 论证 Fos 防御会被任意大的恶意向量破坏，实验只考虑基于 Trimmed-mean 的 Fang-Trmean）。对 Bulyan，论文论证其第二阶段的 Trimmed-mean 无法有效移除这些恶意梯度（Section IV-B3）。
- 论文报告的攻击效果包括：摘要称相对已有投毒攻击带来 1.5 倍到 60 倍的准确率下降（Abstract）；Table II 中 CIFAR10 加 Alexnet、Bulyan 一行，在不知道良性更新的情况下 Fang 与 LIE 的影响是 11.8% 与 30.0%，而本文 AGR-tailored 与 AGR-agnostic 分别为 45.6% 与 44.5%（Section I 与 Table II）。
- 论文也报告了攻击的"隐身与破坏力"权衡：能躲过 DnC 检测的恶意梯度，其良性与恶意梯度均值之差（μ_shift）很小，因而投毒影响也小（Section VII-C1 与 Figure 5）。
- 论文没有讨论基于逐样本损失、隐藏层激活、输出文本、后门触发器或安全对齐指标的检测器，这些在原文中均未说明。

## 6. 干预动作

论文提出的干预动作只有一种，发生在服务器聚合环节：DnC 剔除（exclude）被判为离群的一部分客户端更新，然后用剩余更新的交集取平均，用该平均值更新全局模型（Algorithm 2 第 10、14 至 16 行）。剔除数量是 c·m 条，按离群分数 s_i 从高到低去掉；iid 实验中 c = 1，即正好剔除 m 条（Section VII-C1）。动作完全在服务器侧完成，客户端不参与，不需要客户端重训练，也不是重新加权、裁剪、加噪、样本过滤、模型修复或回滚：论文没有提出这些动作，也没有评估它们。论文只报告检测结果与剩余客户端的平均聚合，因此不存在"仅报告"模式的讨论。

论文还评估了一种外部提出的机制"重采样"（resampling [19]）与 DnC 及既有 AGR 的组合，结论是重采样会显著降低鲁棒性（Table VI 中 DnC + resampling 的多数攻击影响变大；Table VII 中 Krum 的无攻击准确率从 69.3% 降到 47.8%，Bulyan 从 86.1% 降到 76.8%，Trimmed-mean 从 86.7% 降到 70.3%），原因是重采样增加了被处理的恶意更新数量（Section VII-C2 与附录 A）。这是论文报告的负面结论，不是本文提出的干预动作。

## 7. 实验设置与主要结果

模型与数据：CIFAR10 配 Alexnet 与 VGG11，MNIST 配 {784, 512, 10} 全连接网络，Purchase 配 {600, 1024, 100} 全连接网络，FEMNIST 配卷积神经网络（Table II 至 Table VII）。

训练设置（Section V-B）：CIFAR10 + Alexnet 用批量大小 250、SGD、学习率 0.5（第 0 至 1000 轮）与 0.05（第 1000 至 1200 轮）；CIFAR10 + VGG11 用批量大小 200、学习率 0.1 与 0.01；MNIST 训练 500 轮，Adam、学习率 0.001、批量大小 100；Purchase 训练 1000 轮，SGD、学习率 0.5、批量大小 500；FEMNIST 训练 1500 轮，Adam、学习率 0.001，每批使用客户端全部数据。

客户端数与参与率：跨孤岛设置下 CIFAR10 用 50 个客户端、MNIST 用 100 个、Purchase 用 80 个，全部参与（Section II-A 描述跨孤岛为所有客户端每轮都参与）；FEMNIST 每轮从 3,400 个客户端中随机选 60 个（Section V-A）。跨设备实验用 CIFAR10，每轮只处理 50 个客户端中的 10 个（Section VI-E）。

恶意比例：默认 20%（Section V-B）；Figure 3 与 Figure 6a 把比例从 5% 扫到 24%（Section VI-D2），结论包括 CIFAR10 + Krum 下本文 AGR-tailored 攻击在只有 5% 恶意客户端时影响就超过 43%，即把准确率压到随机猜测的 10%，而 Purchase 下 AGR-tailored 与 AGR-agnostic 的 Min-Sum 分别在 5% 与 10% 恶意客户端时就把 Krum 的准确率压到接近 1%。

非独立同分布：MNIST、CIFAR10、Purchase 默认使用独立同分布（iid）数据，理由是 iid 数据下投毒 FL 最难（Section V-B）；FEMNIST 是真实非 iid 且类别不平衡的数据（Section V-A）；Section VI-D1 用 Fang 提出的方案合成不同非 iid 程度的 MNIST 与 Purchase，并报告非 iid 程度越高所有攻击影响越大（Figure 4）。

指标：I_θ = A_θ − A*_θ，即无攻击时最优全局模型准确率与受攻击时准确率之差（Section V-B）。

关键结果。攻击方面，Table II（跨孤岛）显示本文攻击在几乎所有威胁模型、AGR、数据集与模型组合上优于 Fang 与 LIE：CIFAR10 + Alexnet + Krum 在 agr-updates 下 Fang 影响 21.8%、本文 43.6%；MNIST + Krum 在 agr-updates（agr-only）下 Fang 为 20.5%（17.4%）、本文为 33.9%（24.1%）；MNIST 的 Trimmed-mean（Median）上 Fang 仅 1.2%（1.7%），本文为 11.0%（4.4%）；Purchase 上本文攻击把 Krum 的准确率压到接近随机猜测的 1%。Section VI-A 还给出倍数关系，例如 CIFAR10 在 agr-updates 下本文攻击影响是 Fang 的 2 倍，在 agr-only 下对 Alexnet 与 VGG11 分别是 2.5 倍与 4.5 倍；摘要给出总体范围是准确率下降幅度高 1.5 倍到 60 倍。Table III（跨设备）显示同样趋势，但总体影响低于跨孤岛，例如 Alexnet 下 Krum、Multi-krum、Trimmed-mean 的影响分别下降 9.5%、14.6%、31.8%（Section VI-E）。

防御方面，Table IV 给出 DnC 在 iid 数据集上对最强攻击的影响，括号内是同一攻击对既有最好 AGR 的影响：CIFAR10 + Alexnet 无攻击准确率 67.6%，Fang 3.2%（7.0%）、LIE 3.0%（5.9%）、本文最强 AGR-tailored 4.3%（36.8%）、Min-Max 3.5%（27.8%）、Min-Sum 2.0%（16.9%）、自适应攻击 6.1%；CIFAR10 + VGG11 无攻击 75.5%，自适应攻击 6.3%（既有 AGR 上最强攻击为 32.5%）；Purchase + 全连接 无攻击 92.0%，自适应攻击 1.8%；MNIST + 全连接 无攻击 96.2%，自适应攻击 1.9%。Section I 与 Section VII-C1 把这一结果表述为 DnC 把最大准确率下降从 36.8% 降到 6.1%（CIFAR10 + Alexnet）、从 32.5% 降到 6.3%（CIFAR10 + VGG11）、从 11.6% 降到 1.8%（Purchase）、从 4.4% 降到 1.9%（MNIST），摘要称 DnC 的韧性比既有方法高 2.5 倍到 12 倍。

跨设备下 Table V 显示：CIFAR10 + Alexnet 无攻击准确率 64.6%，DnC 的最小 A*_θ 从既有 AGR 的 50.6% 提高到 61.2%（对应自适应攻击影响 3.4%）；CIFAR10 + VGG11 从 63.4% 提高到 68.0%（Section VII-C1）。

非 iid 的 FEMNIST 上 Table VI 显示 DnC 在强攻击者下失守：在知道良性梯度的 agr-updates 与 updates-only 一侧，Min-Sum 的影响是 79.3%，把准确率从无攻击时的 86.6% 压到 7.3%；在不知道良性梯度的一侧，最大影响只有 12.7%，即 DnC 下最高准确率 73.9%，而既有 AGR 中最鲁棒的 Krum 对应最高准确率只有 66.4%（Section VII-C2）。Table VII 显示重采样使既有防御更脆弱。Figure 2 与 Figure 7 说明扰动方向选择对攻击影响巨大，例如 MNIST + Krum 上 ∇p_uv 的影响是 −4.7%（即准确率反而上升），而 ∇p_sgn 是 24.1%；CIFAR10 + Alexnet + Multi-krum 上 ∇p_std、∇p_uv、∇p_sgn 的影响分别是 36.8%、14.2%、16.3%（Section VI-C1）。

## 8. 开销

论文报告了 DnC 的渐近开销：SVD 类防御需要 O(d³) 的内存与计算，因此对常见 FL 设置中的高维梯度直接做 SVD 代价高得不可行，DnC 用随机维度采样来规避（Section VII-B）。Algorithm 2 每轮要执行 n_iters 次"随机采样子集、求均值、中心化、求顶部右奇异向量、算离群分数、排序"的流程，实验中 n_iters 取 1、b 取 10,000（Section VII-C1 与 VII-C2）。攻击侧，论文指出因为鲁棒 AGR 不可微，Algorithm 1 依赖对预言机的反复查询来搜索 γ（Section IV-A 与 IV-D），扰动方向的选择还需要攻击者在缩小规模上仿真 FL（Section VI-C2）。

论文未报告任何实测的墙钟时间、通信量或存储量数字，也没有把 DnC 与既有 AGR 的运行时间做对比；攻击侧同样没有量化其额外计算量。因此这里应当记为：论文报告了渐近复杂度和超参数取值，未报告可比较的定量开销基准。

## 9. 假设、局限与自适应攻击

方法成立所依赖的假设：

- 恶意客户端占比小于一半，(m/n) < 0.5，并且服务器知道恶意客户端数量的上界 m，因为 Krum、Trimmed-mean 与 DnC 都需要 m 作为输入（Section III、Section II-C4、Algorithm 2）。
- 攻击者能够构造参考良性聚合 ∇b：要么知道良性设备的梯度（agr-updates、updates-only），要么在控制的设备上持有与良性分布相近的数据（agr-only、agnostic）（Section IV-A 与 IV-B 开头）。
- AGR-tailored 攻击者知道服务器的聚合算法，AGR-agnostic 攻击者虽然不知道算法，但知道良性更新会形成一个团，并据此设定距离约束（Section IV-B 与 IV-C）。
- DnC 的过滤保证依赖 ε-谱可分性，Lemma 1 要求良性梯度与恶意梯度的协方差都满足 Σ ⪯ σ²I，且均值之差满足 ‖μ_B − μ_M‖²₂ ≥ 6σ²/ε；这一分析建立在良性梯度独立同分布的前提上（Definition 1、Lemma 1 与 Section VII-C2 对 FEMNIST 的讨论）。
- 针对 DnC 的自适应攻击假设攻击者完全了解 DnC 算法，但无法知道 Algorithm 2 中随机抽取的维度索引 r（Section VII-B）。
- 论文隐含假设服务器能够看到每个客户端提交的明文更新，未讨论安全聚合、差分隐私、更新加密或服务器端验证；这些在论文中均未说明。

论文自述的局限：DnC 在非 iid 的 FEMNIST 上无法抵御知道良性梯度的最强攻击者，论文明确称"在真实世界的非 iid FL 设置中防御最坏情况的模型投毒是已知的难题，也是当前形式 DnC 的局限"，并把改进留给未来工作（Section VII-C2）；重采样机制会加剧这一问题（Table VI、Table VII）；最优扰动方向 ∇p 的求解留给未来工作（Section IV-A 结尾）；Table II 中少数 agnostic 攻击者影响略高于 updates-only 的异常被归因于实验随机性，结果是三次实例的平均（Section VI-A 结尾）；论文还强调既有 AGR 的收敛保证对非凸问题不足（Section VII-A 的 L2）。

自适应攻击的评估：论文构造并评估了自适应攻击（Section VII-B，公式 (8)），其目标是在知道 DnC 的情况下最大化被 DnC 选中的恶意梯度数量，用 Algorithm 1 求解 γ。结果是对 DnC 的最强攻击就是该自适应攻击：CIFAR10 + Alexnet 影响 6.1%，CIFAR10 + VGG11 影响 6.3%，Purchase 影响 1.8%，MNIST 影响 1.9%（Table IV）；跨设备下分别是 3.4% 与 4.1%（Table V）；FEMNIST 上自适应攻击在知道良性梯度一侧影响 78.6%，在不知道一侧影响 10.2%（Table VI）。论文的解释是自适应攻击只能靠压低 μ_shift 来躲过 DnC 的检测，而低 μ_shift 意味着投毒影响有限（Section VII-C1 与 Figure 5）。

迁移到联邦大模型 LoRA 微调时可能失效的假设（以下均为分析：）：

- 分析：本文的更新是完整模型的梯度向量，AGR 的逐维裁剪（Trimmed-mean、Median）与欧氏距离（Krum、Multi-krum、Bulyan）都直接作用在这些坐标上；LoRA 场景下服务器聚合的是低秩因子，逐坐标语义会改变，Krum 在拼接的 LoRA 因子上的距离与在等效权重增量上的距离不是同一个量，因此本文报告的鲁棒性排序不能直接搬到 LoRA。
- 分析：DnC 的随机维度采样假设更新向量是 d 维欧氏空间中的点，随机抽 10,000 维能代表整体方向；当模型是 LoRA 适配器时，随机抽样可能几乎全落在某一个因子上，而且低秩结构允许用很小的因子范数实现很大的等效权重扰动，ε-谱可分性条件是否成立需要重新验证。
- 分析：DnC 的理论保证与非 iid 实验共同说明它对数据异质性敏感，而联邦大模型微调的数据异质性通常远高于本文的 MNIST 与 CIFAR10，更接近本文失败的 FEMNIST 情形。
- 分析：本文的目标函数是无目标准确率破坏，检测信号主要来自服务器端的更新几何；LoRA 微调中更受关注的后门、越狱与安全对齐破坏属于本文明确排除的定向攻击，论文没有给出任何关于输出文本、逐样本损失或安全指标的检测依据。
- 分析：本文的实验规模是十万到千万参数级的视觉模型，LoRA 适配器的参数量与模型维度大得多，O(d³) 的 SVD 与 b = 10,000 这类超参数都需要重新标定，论文未给出指导。
- 分析：论文隐含假设服务器能看到明文原始更新并且各客户端提交同形状的向量；在真实联邦大模型系统中若启用安全聚合、差分隐私、量化压缩或异构秩适配器，这些前提都不再成立，论文对此未作讨论。

## 10. 对防护库设计的含义

- 分析：库需要在服务器收到更新时提供一个逐客户端、未聚合、可做维度级索引的原始更新视图，这是支持 DnC 这类谱方法的硬性前提；该采集点对所有基于"服务器收到更新"的检测与聚合插件都是通用的，不是本文特有的。
- 分析：库的服务器聚合钩子需要允许插件整体接管聚合逻辑，而不只是对聚合结果做事后处理，因为 DnC 是一个替换 Average 的 AGR，并且它的输出是客户端索引集合加平均值；同时插件需要能读到 n、m、c、n_iters、b 这类配置，其中"恶意客户端数上界 m"是本文方法特有的强假设，库应把它设计成可由外部估计器写入的参数，而不是让插件自己去猜。
- 分析：库需要在客户端训练后、上传前提供一个更新快照钩子，并把该快照与客户端标识、轮次标识绑定；这既能服务防御插件，也能服务攻击复现与红队评估，因为本文攻击的入口正是在这个位置替换更新向量。
- 分析：库的干预接口至少要支持"剔除客户端子集"和"对剩余集合重新求平均"这两种动作，并能把剔除名单与理由回传审计；本文只用到剔除，因此裁剪、加噪、样本过滤、模型修复与回滚不能声称有本文依据。
- 分析：本文的 DnC 不需要干净参考数据集、不需要跨轮历史、不需要逐样本数据，所以采集底座可以把这三类数据视图设计成可选能力；反过来，像 Fang 这类需要带标签数据与额外前向计算的基线防御，则应通过评估视图插件获得验证集，而不是让聚合插件直接依赖训练数据。
- 分析：库应允许插件声明自己的额外计算预算与降维策略（例如随机维度子采样与 SVD），并在服务端提供可配置的并发或离线计算通道；本文只给出渐近复杂度而没有给出实测开销，因此性能门限必须由使用方自行基准测试。

## 11. 原文依据

1. Abstract（第 1 页）："Federated learning (FL) enables many data owners (e.g., mobile devices) to train a joint ML model (e.g., a next-word prediction classifier) without the need of sharing their private training data." 支撑第 1 节：本文研究的是传统联邦学习场景。
2. Section III："We assume that the adversary controls up to m out of n total clients, called malicious clients. We assume that the number of malicious clients is less than the number of benign clients" 支撑第 2 节：攻击者是恶意客户端、占比受限且少于一半。
3. Section II-B："In model poisoning attacks [17], [4], [31], [38], [6], [3], the adversary can directly manipulate the gradients on malicious devices before sharing them with the server in each epoch." 支撑第 3 节：攻击入口在更新上传之前。
4. Section IV-A："The final malicious gradient ∇m is a perturbed version of the benign aggregate ∇b, i.e., ∇m = ∇b + γ∇p, where ∇p is a perturbation vector and γ is a scaling coefficient." 支撑第 4 节：恶意更新的构造形式。
5. Section I："when FL clients' data are identically and independently distributed (iid), a malicious model poisoning update is impactful if and only if it deviates significantly from benign updates along a specific malicious direction in the updates' space." 支撑第 4 节：DnC 的核心直觉与 iid 前提。
6. Section I："Then, it computes scalar product of each submitted model update with this principal component, which we call projections. Finally, DnC removes a constant fraction of the submitted model updates that have the largest projections." 支撑第 6 节：干预动作是在服务器聚合处剔除离群更新。
7. Section I："For instance, compared to existing robust AGRs, DnC reduces the maximum reduction in the accuracy of the global model due to model poisoning attacks from 36.8% to 6.1% for CIFAR10 with Alexnet" 支撑第 7 节：DnC 的关键实验结果。
8. Section VII-B："Note that SVD-based defenses require O(d3) memory and computational cost, hence, performing SVD directly on high dimensional gradients in common FL settings [30] is prohibitively expensive." 支撑第 8 节：论文报告的开销与其降维动机。
9. Section VII-B："However, to provide empirical evidence on the robustness guarantees of DnC, we propose an adaptive attack" 支撑第 9 节：论文评估了自适应攻击者。
10. Section VII-C2："We note that, DnC cannot defend at least one of our attacks by the strongest adversaries with complete knowledge of the gradients of benign clients, i.e., agr-updates and updates-only adversaries." 支撑第 9 节：论文自述在非 iid FEMNIST 上的局限。

```json
{
  "key": "shejwalkar2021manipulating",
  "title": "Manipulating the Byzantine: Optimizing Model Poisoning Attacks and Defenses for Federated Learning",
  "year": 2021,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["update_postprocess"],
  "observables": [
    {"what": "服务器每轮收到的每个参与客户端提交的完整梯度或模型更新向量，DnC 需要对其做维度级随机子采样与谱分析", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "每轮参与客户端数 n 与恶意客户端数上界 m，用于确定剔除条数 c 乘 m", "where": "server_aggregate", "granularity": "round", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "攻击者用来构造恶意更新的良性参考聚合，由已知良性梯度或恶意设备本地良性数据计算的平均梯度", "where": "client_post_train", "granularity": "client", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "服务器验证集上的全局模型准确率，用于计算攻击影响 I_theta 并选出最优全局模型", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false}
  ],
  "interventions": ["exclude_client"],
  "intervention_where": ["server"],
  "assumptions": [
    "恶意客户端占比小于一半，且服务器知道恶意客户端数量的上界 m，Krum、Trimmed-mean 与 DnC 都以 m 为输入参数",
    "攻击者要么知道良性设备的梯度（agr-updates、updates-only），要么在控制的设备上持有与良性分布相近的数据以计算参考良性聚合（agr-only、agnostic）",
    "AGR-tailored 攻击者知道服务器的聚合算法，AGR-agnostic 攻击者不知道算法但知道良性更新形成的团并据此约束距离",
    "DnC 的过滤保证假设良性梯度独立同分布，且良性分布与恶意分布满足 epsilon 谱可分性，协方差满足 Sigma 被 sigma 平方乘单位阵支配、均值差平方不小于 6 sigma 平方除以 epsilon",
    "针对 DnC 的自适应攻击假设攻击者完全知道 DnC 算法，但无法知道 Algorithm 2 中随机抽取的维度索引 r",
    "论文隐含假设服务器能看到每个客户端提交的明文原始更新，未讨论安全聚合、差分隐私或更新加密"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节：本文研究的是传统联邦学习场景，而非联邦大模型或集中式训练", "text": "Federated learning (FL) enables many data owners (e.g., mobile devices) to train a joint ML model (e.g., a next-word prediction classifier) without the need of sharing their private training data."},
    {"section": "Section III", "supports": "第 2 节：攻击者是恶意客户端，数量少于良性客户端", "text": "We assume that the adversary controls up to m out of n total clients, called malicious clients. We assume that the number of malicious clients is less than the number of benign clients"},
    {"section": "Section II-B", "supports": "第 3 节：攻击入口是上传前的更新篡改", "text": "In model poisoning attacks [17], [4], [31], [38], [6], [3], the adversary can directly manipulate the gradients on malicious devices before sharing them with the server in each epoch."},
    {"section": "Section IV-A", "supports": "第 4 节：恶意更新由良性参考聚合加缩放后的扰动向量构成", "text": "The final malicious gradient ∇m is a perturbed version of the benign aggregate ∇b, i.e., ∇m = ∇b + γ∇p, where ∇p is a perturbation vector and γ is a scaling coefficient."},
    {"section": "Section I", "supports": "第 4 节：DnC 的核心直觉及其 iid 前提", "text": "when FL clients' data are identically and independently distributed (iid), a malicious model poisoning update is impactful if and only if it deviates significantly from benign updates along a specific malicious direction in the updates' space."},
    {"section": "Section I", "supports": "第 6 节：干预动作是在服务器聚合处剔除投影最大的固定比例更新", "text": "Then, it computes scalar product of each submitted model update with this principal component, which we call projections. Finally, DnC removes a constant fraction of the submitted model updates that have the largest projections."},
    {"section": "Section I", "supports": "第 7 节：DnC 在 CIFAR10 与 Alexnet 上的关键实验结果", "text": "For instance, compared to existing robust AGRs, DnC reduces the maximum reduction in the accuracy of the global model due to model poisoning attacks from 36.8% to 6.1% for CIFAR10 with Alexnet"},
    {"section": "Section VII-B", "supports": "第 8 节：论文报告的 SVD 渐近开销与其随机降维动机", "text": "Note that SVD-based defenses require O(d3) memory and computational cost, hence, performing SVD directly on high dimensional gradients in common FL settings [30] is prohibitively expensive."},
    {"section": "Section VII-B", "supports": "第 9 节：论文构造并评估了针对 DnC 的自适应攻击", "text": "However, to provide empirical evidence on the robustness guarantees of DnC, we propose an adaptive attack"},
    {"section": "Section VII-C2", "supports": "第 9 节：论文自述 DnC 在非 iid FEMNIST 且攻击者知道良性梯度时的局限", "text": "We note that, DnC cannot defend at least one of our attacks by the strongest adversaries with complete knowledge of the gradients of benign clients, i.e., agr-updates and updates-only adversaries."}
  ]
}
```
