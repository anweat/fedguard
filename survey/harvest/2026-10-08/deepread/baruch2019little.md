# baruch2019little：A Little Is Enough: Circumventing Defenses For Distributed Learning

## 1. 基本信息

- **场景**：论文研究的是**传统的分布式同步随机梯度下降（Synchronous Stochastic Gradient Descent，sync-SGD）训练**，架构为单参数服务器（Parameter Server，PS）加 n 个工作节点（worker）。论文明确把自己与联邦学习（Federated Learning）区分开：论文指出联邦学习中每个工作节点使用自己来自不同分布的私有数据，破坏了独立同分布（independent and identically distributed，i.i.d.）假设，而本文的设定是数据被切分给各节点、满足 i.i.d. 的分布式训练（第 2.2 节）。因此它**不是**联邦大模型微调，也**不是**参数高效微调（Parameter-Efficient Fine-Tuning，PEFT）供应链，更不涉及大语言模型（Large Language Model，LLM）。
- **训练阶段**：同步 SGD 的每一轮（round），即服务器下发全局参数、各节点本地训练、节点回传本地参数、服务器聚合这一循环（Algorithm 1）。
- **论文类型**：攻击（attack）。论文提出新攻击方法，并系统性地展示它绕过既有防御；论文本身不提出新的检测器或防御。
- **模型与数据规模**：MNIST 上使用一个隐藏层的多层感知机（784 维输入、100 维 ReLU 隐藏层、10 维 softmax 输出，交叉熵目标），参数维度 d 约为 8 万；训练 150 个 epoch，批大小为 83，无攻击无防御时测试精度 96.1%。CIFAR10 上使用 7 层卷积神经网络（输入 3072 维即 32×32×3；3×3 卷积核 16 通道步长 1；3×3 最大池化；4×4 卷积核 64 通道步长 1；4×4 最大池化；两个 384 与 192 维全连接层；10 维输出），d 约为 100 万；训练 400 个 epoch，无攻击时最高精度 59.6%（第 4 节）。训练数据按 n = 51 = 4·m + 3 切分，m = 12（第 4 节）。

## 2. 威胁模型

- **攻击者是谁**：恶意拜占庭工作节点（Byzantine worker）。论文写明攻击者可以控制设备本身，或者仅控制参与者与参数服务器之间的通信（例如中间人攻击，Man In The Middle）(第 1 节)。
- **占比或数量**：主实验为 n = 51、m = 12，约占 24%（第 4 节）。摘要称 20% 的腐败节点即可让 CIFAR10 模型精度下降 50%。图 4 扫描了 5% 到 24% 的恶意比例。论文同时给出被评估防御的理论容忍上限：Trimmed Mean 与 Krum 设计为最多抵御 ⌈n/2⌉−1 个腐败节点，Bulyan 只设计为抵御最多 (n−3)/4 个腐败节点（第 2.3 节）。
- **能力（能改什么）**：攻击者可以把本地训练结束后、上传之前的整个参数向量替换为任意值（第 2.2 节：攻击发生在 Algorithm 1 第 6 行与第 7 行之间）。在后门攻击中，攻击者还额外用后门样本和自定义损失在本地训练模型，再对结果做逐维裁剪（Algorithm 4）。若攻击者只控制通信而不控制设备，论文未说明如何完成 Algorithm 4 第 3 行所需的本地后门训练（分析：从算法描述看，后门攻击实际上要求能够控制设备的训练过程或至少能注入本地数据与损失）。
- **知识（知道什么）**：**非全知（non-omniscient）**。论文强调攻击者只需持有被控节点自身的参数/数据，用它来估计整个总体的逐维均值 µ_j 与标准差 σ_j（第 3 节）。算法输入显式包含 n 和 m（Algorithm 3、Algorithm 4），因此攻击者知道总节点数与恶意节点数。论文称同一组恶意参数对所有防御都有效，因此攻击者不需要知道服务器选了哪种防御（第 3 节）。论文未说明攻击者是否需要知道其他节点本轮是否也会上传相同值、是否需要知道全局模型的历史记录。
- **目标**：两类。第一是无目标破坏，即**阻止收敛（convergence prevention）**，让服务器无法达到好的精度（第 2.1 节、第 3.3 节）。第二是**定向后门（backdooring）**，又分单样本后门（把特定样本判成攻击者指定类别）和图案后门（带特定像素图案的样本一律判成指定类别）（第 2.1 节、第 4.2 节）。
- **防御者是谁、能看到什么、信任什么**：防御者是参数服务器。它能拿到每个工作节点单独上传的完整参数向量（Trimmed Mean、Krum、Bulyan 都必须逐维或按欧氏距离访问这些向量），能替换聚合规则，还能在测试集上评估每轮全局模型并返回测试精度最高的那一轮（Algorithm 1 第 8 至 10 行）。它信任的核心假设是：各工作节点的参数逐维 i.i.d. 且服从正态分布，从而中位数落在良性取值范围内（第 1 节、第 2.3 节、第 3 节）。论文未说明服务器是否能验证客户端数据、是否使用安全聚合、是否保存干净根数据集或跨轮更新历史。

## 3. 攻击入口与流程位置

攻击的主要入口是**更新上传前的后处理**，即本地训练结束到上传之间。论文原文说明攻击者选择效果最大的时刻介入，也就是 Algorithm 1 的第 6 行（本地训练）与第 7 行（回传最终参数）之间（第 2.2 节）。后门攻击还额外占用**本地数据准备与本地训练**这一段，因为攻击者要在自己的设备上用后门样本和自定义损失多训练一次（Algorithm 4 第 3 行），但注入的是自己本地的训练过程，而不是交给服务器的训练集。

**阻止收敛攻击的具体步骤（Algorithm 3，第 3.3 节）**：

1. 设 s = ⌊n/2 + 1⌋ − m，即为了在逐维取值上取得多数、把中位数拉到自己一侧，还需要"引诱"的良性节点数量。
2. 从 z 表中取满足 φ(z) < (n − s)/n 的最大 z 作为 z_max，其中 φ 是标准正态累积分布函数。
3. 对每一维 j，用被控节点的参数估计均值 µ_j 与标准差 σ_j：注意 Algorithm 3 第 2 至 5 行的输入只有 {p_i : i 属于 CorruptedWorkers}，所以 µ_j 与 σ_j 是从被控节点自己的参数里算出来的。
4. 令恶意值 (p_mal)_j = µ_j + z_max · σ_j，对所有被控节点执行 p_i ← p_mal。
5. 服务器收到的是 n 份参数向量，其中 m 份被替换为 p_mal。

**后门攻击的具体步骤（Algorithm 4，第 3.4 节）**：先用同样方式算出 z_max、µ_j、σ_j；再以 {µ_j} 为初始参数、用式 (3) 的加权损失在本地训练带后门的模型；得到最终参数 V 后，逐维把 v_j 裁剪到区间 [µ_j − z_max σ_j, µ_j + z_max σ_j]；最后所有被控节点上传这份裁剪后的 p_mal。

**补充路径**：论文指出，如果服务器使用不做离群值剔除的朴素平均（论文称其为 No Defense），本文攻击会被稀释；此时攻击者可以采用混合策略，用一个被控节点专门对朴素平均实施早期论文中的大幅攻击，其余被控节点继续实施本文的小幅规避攻击（第 4.1 节、第 4.2 节）。论文还指出服务器可能在察觉攻击后主动屏蔽一部分节点并观察训练效果（第 2.1 节）。

## 4. 方法原理

**核心思想**：既有攻击与防御的共同假设是"要达成恶意目标必须大幅改变一个或多个参数"，因此防御靠剔除远离均值的离群值。论文反过来证明：对**大量参数**施加方向一致、幅度很小（以标准差 σ 为单位）的扰动，既不会被逐维裁剪剔除，又能在多轮中持续累积，从而破坏收敛或植入后门（第 1 节、第 3 节）。

**扰动范围的推导（第 3.1 节）**：Trimmed Mean 逐维独立计算，所以问题可以退化成一维数组，每个元素来自一个不同的工作节点。攻击者要改变 Trimmed Mean 的输出，必须控制中位数；这需要多数节点落在同一侧。若已控制 m 个节点，则还需要 s = ⌊n/2 + 1⌋ − m 个良性节点"被引诱"到更远的位置。在正态分布下，良性取值落在 µ + zσ 之外的概率是 1 − φ(z)，因此取满足 φ(z) < (n − s)/n 的最大 z。把所有被控节点设到 (µ − zσ, µ + zσ) 区间内的同一个值后，这些值有很大概率成为中位数，并且因为数量多而能抵抗 Trimmed Mean 第二阶段围绕中位数的平均。第 3.3 节给出的算例是：总共 50 个节点、其中 24 个恶意时，s = 2，(50 − 2)/50 = 0.96，查 z 表得到 z_max = 1.75，于是所有恶意节点把每一维都设为 µ + 1.75 · σ。

**对 Krum 的绕过（第 3.2 节）**：Krum 只输出一个被选中的工作节点的整套参数，其余全部丢弃，选择标准是该节点参数到最近 n − m − 2 个邻居的欧氏距离之和最小。在高维参数空间中，即使是"最好"的良性节点也会有若干维远离均值，因此只要让恶意参数在每一维上只偏离均值一点点，就能压低欧氏距离，使恶意集合被选中。论文报告实验上针对 Trimmed Mean 构造的同一组参数也骗过了 Krum。论文还指出攻击 Krum 的优势是：估计 µ_j 与 σ_j 只需要少数被控节点，且最终只需要一个节点上报恶意参数。

**对 Bulyan 的绕过（第 3.2 节、第 4.1 节）**：Bulyan 是 Krum 与 Trimmed Mean 的组合（先用 Krum 迭代构造 SelectionSet，再对 SelectionSet 用 Trimmed Mean 的第二变体），两个构件都被绕过，因此 Bulyan 也失效。论文补充说明，虽然 Bulyan 只声称抵御约 25% 的腐败节点，但第一阶段算出的扰动范围是 Trimmed Mean 的输入范围，而 SelectionSet 中被控比例可以上升到约 48%（图 2 的讨论中写作 48%，第 4 节正文写作接近 24% 的恶意比例在 SelectionSet 中可达到 48%）。

**后门攻击的损失设计（第 3.4 节，式 (3) 与式 (4)）**：Loss = α · ℓ_backdoor + (1 − α) · ℓ_Δ，其中 ℓ_backdoor 是后门样本上的常规损失、标签换成攻击者目标，ℓ_Δ 是保持新参数靠近原始参数的惩罚项。ℓ_Δ 不使用直接的 Lp 距离，而是用逐维标准差归一化：对每一维计算 ((NewParam_j − OldParam_j) / max(z_max σ_j, 1e−5))²。偏移小于 z_max σ_j 时比值小于 1，平方后惩罚很小；偏移超过 z_max σ_j 时惩罚迅速增大；σ_j 很小的维度用 1e−5 截断以避免除以极小数。论文指出 α 太大时参数会显著偏离原始参数而被防御丢弃，因此攻击者应使用能够成功植入后门的最小 α。

**论文声称能绕过的检测**：Trimmed Mean 的三个变体（Mean-Around-Median、Bulyan 使用的第二变体、以及去掉最大最小各 m 个值的第三变体）、Krum、Bulyan，以及 Shen 等人提出的逐参数一维 k 均值聚类变体（第 2.3 节、第 3 节）。论文还论证 Steinhardt 等、Qiao 与 Valiant、Chen 等、Tran 等提出的后门检测方法在本文设定下不可用，因为这些方法假设服务器能访问被注入后门的训练集，而本文设定中服务器无法控制工作节点用什么样本训练（第 2.2 节）。论文未讨论基于更新相似度、更新范数、跨轮一致性或安全聚合的检测。

## 5. 检测或防御所需的数据

以下逐项列出论文中被评估防御所需的输入，以及本文攻击留下的可观测量。

1. **每个工作节点每轮上传的完整本地参数向量（逐维取值）**
   - 是什么：p_i，即节点 i 本地训练后的全部参数；(p_i)_j 是它的第 j 维；P 表示 {p_i : i ∈ [n]}（第 2.3 节的记号约定）。
   - 在哪里采集：服务器收到更新时。
   - 粒度：逐客户端，同时可细到逐层与逐维，按轮重复。
   - 是否需要跨轮历史：不需要，论文明确说所有现有防御都是逐轮独立工作的。
   - 是否需要干净参考数据：不需要。
   - 是否需要额外前向或反向计算：不需要。
2. **全体节点参数在每一维上的中位数以及各值到中位数的距离排序**
   - 是什么：Trimmed Mean 逐维保留最靠近中位数的 top-(n − m) 或 top-(n − 2m) 个值（第 2.3 节式 (1) 及其三个变体）。
   - 在哪里采集：服务器聚合时计算。
   - 粒度：逐维（逐层），逐轮。
   - 是否需要跨轮历史：不需要。是否需要干净参考数据：不需要。是否需要额外计算：需要，逐维排序或分位数选择。
3. **节点参数两两之间的欧氏距离**
   - 是什么：Krum 用 ∥p_i − p_j∥₂ 找出每个候选者的 n − m − 2 个最近邻，再选距离和最小者（第 2.3 节式 (2)）。
   - 在哪里采集：服务器聚合时计算。
   - 粒度：逐客户端（在完整参数空间上度量），逐轮。
   - 是否需要跨轮历史：不需要。是否需要干净参考数据：不需要。是否需要额外计算：需要，涉及 O(n²) 次高维距离计算。
4. **迭代选择得到的 SelectionSet 及其中每个维度的裁剪平均**
   - 是什么：Bulyan 用聚合规则 A（论文取 A = Krum）反复选出 n − 2m 个候选，再对这一集合用 Trimmed Mean 第二变体，对每个维度平均 n − 4m 个值（Algorithm 2 及其说明）。
   - 在哪里采集：服务器聚合时。粒度：逐维加逐客户端集合，逐轮。
   - 是否需要跨轮历史：不需要。是否需要干净参考数据：不需要。是否需要额外计算：需要，是上述两类计算的反复调用。
5. **被控节点之间上传向量是否逐维完全相同**
   - 是什么：本文攻击的可观测量痕迹。Algorithm 3 与 Algorithm 4 的最后一步都是对每个被控节点执行 p_i ← p_mal，因此所有被控节点在同一轮上传**完全相同**的向量，而且该向量在每一维上相对总体均值一致地偏向同一侧、偏移量约为 z 倍标准差。
   - 在哪里采集：服务器收到更新时。粒度：逐客户端，可选逐维。
   - 是否需要跨轮历史：论文未说明。是否需要干净参考数据：不需要。是否需要额外计算：需要一次相似度或重复度检查。
   - 说明：论文没有把这一点当作检测信号来讨论，也没有评估任何基于该痕迹的检测器；论文声称被绕过的是第 4 节列出的那些基于离群值剔除的防御。
6. **聚合后的全局模型及其在测试集上的准确率**
   - 是什么：P^{t+1} 与它在测试集上的精度，Algorithm 1 第 9 行显式计算，第 10 行据此返回测试精度最高的 P^t。
   - 在哪里采集：评估时。粒度：模型级，逐轮。
   - 是否需要跨轮历史：需要（要跨轮比较才能选出最优轮）。是否需要干净参考数据：需要，即 MNIST 与 CIFAR10 的测试集。是否需要额外计算：需要前向推理。
7. **后门评估所需的样本与命中率**
   - 是什么：单样本后门使用每个训练集前 3 张图像之一，目标标签为 (y + 1) mod |Y|；图案后门每轮从数据集中随机抽 1000 张图像，把左上角 5×5 像素置为最大强度，目标标签固定为 0（第 4.2 节、表 2、表 3）。
   - 在哪里采集：评估时。粒度：逐样本。
   - 是否需要干净参考数据：需要（良性测试集用于测量精度损失；后门样本与图案由攻击者构造，服务器侧并不具备）。
   - 是否需要额外计算：需要前向推理。
   - 说明：论文未说明服务器是否可能拥有后门样本或图案的相关知识；这些数据在论文中只用于评估攻击效果。

## 6. 干预动作

论文本身是攻击论文，因此这一节记录它所针对的防御在检测之后做什么，以及论文提到的服务器缓解手段。

- **Krum：剔除客户端。** 从 n 个节点中只保留一个被选中的节点参数，其余全部丢弃（第 2.3 节式 (2) 与 Algorithm 2 中对 A 的调用）。发生在服务器聚合时。
- **Trimmed Mean（Mean-Around-Median 家族）：裁剪式重加权。** 对每个维度独立地剔除离中位数最远（或最大最小）的若干个值，再对剩下的值取平均（第 2.3 节式 (1)）。发生在服务器聚合时。
- **Bulyan：剔除与裁剪的组合。** 先用 Krum 迭代构造大小 n − 2m 的 SelectionSet，再对该集合的每个维度平均 n − 4m 个值（Algorithm 2）。发生在服务器聚合时。
- **最优轮选择。** Algorithm 1 第 9 行在测试集上评估每轮的 P^{t+1}，第 10 行返回测试精度最高的 P^t。发生在评估与部署阶段。论文没有把这一步当作针对本文攻击的防御来评估（分析：它可以被理解为一种检查点回滚机制，但论文未给出它与本文攻击交互的任何实验）。
- **主动屏蔽节点。** 论文提到真实场景下服务器知道被攻击后可能主动屏蔽一部分工作节点并观察训练过程受到的影响（第 2.1 节）。发生在服务器侧，论文未给出实验。
- **不给服务器选择朴素平均的建议。** 论文的结论是：在现有防御中应选择 Trimmed Mean 的一个变体，因为它对收敛攻击的表现最好（朴素平均虽然对该攻击最鲁棒，但对更简单的攻击显然脆弱）；论文没有提出新的检测器或新的防御机制。

## 7. 实验设置与主要结果

**设置**：数据集为 MNIST 与 CIFAR10（第 4 节）。模型如第 1 节所述。学习率 0.1，动量 0.9，两个模型都加了 L2 正则化，论文正文把权重写为 104（抽取文本如此，疑为上标丢失；论文未进一步说明）。训练数据切分给 n = 51 = 4·m + 3 个节点，其中 m = 12 个被控。数据是 **i.i.d.** 的：论文明确指出分布式训练把数据集分块、满足独立同分布假设，并把它与联邦学习的非独立同分布数据划分对比（第 2.2 节、第 3 节）。指标为测试集上的分类精度，后门实验还报告后门样本或后门图案被判成攻击者目标的比率。

**攻击幅度与破坏力的关系（表 1，第 4.1 节）**：让所有节点（m = n）把所有参数改变 0、0.5、1、1.5 个标准差。MNIST 的最大精度依次为 96.1、89.0、82.4、77.8；CIFAR10 依次为 59.6、28.4、20.9、17.5。论文据此说明 1 到 1.5 个标准差就足以显著破坏精度，且 CIFAR10 比 MNIST 更容易被破坏。

**MNIST 收敛破坏（图 2，第 4.1 节）**：m = 24%，z = 1.5。攻击在所有防御下都有效，Krum 表现最差（恶意集合被选中），Bulyan 受影响大于 Trimmed Mean，Trimmed Mean 又因为恶意参数被许多良性参数平均稀释而稍好；朴素平均（No Defense）反而是对该攻击最鲁棒的聚合方式，因为 1.5 个标准差的偏移被 76% 的良性节点平均后只剩约 0.36 个标准差。

**CIFAR10 收敛破坏（图 3，第 4.1 节）**：取 m = 20%、z = 1（因为 CIFAR10 对更小的偏移就敏感）。朴素平均精度下降 28%，Krum 下降 66%，Bulyan 下降 52%，Trimmed Mean 下降 45%。

**恶意比例扫描（图 4，第 4.1 节）**：在 CIFAR10 上取 z = 1，m 从 5% 扫到 24%。Krum 对小规模恶意节点也敏感，m = 5% 时精度就下降 33%；总体趋势是恶意比例越高精度越低，10% 就能在多数防御下造成明显退化。

**单样本后门（表 2，第 4.2 节）**：设置 n = 51、m = 24%、z = α = 0.2，攻击者每轮用后门额外训练 5 rounds（论文原文如此表述，未进一步说明其确切含义）。无后门时 MNIST 96.1、CIFAR10 59.6；No Defense 95.4 与 58.4；Trimmed Mean 95.4 与 57.9；Krum 95.3 与 54.4；Bulyan 95.3 与 54.2。论文报告在整个过程中后门样本被判成恶意目标的比例超过 95%，MNIST 上的总体精度下降不到 1%，CIFAR10 上最多下降 9%。

**图案后门（表 3，第 4.2 节）**：同样 n = 51、m = 24%、z = α = 0.2。MNIST 上良性输入精度与后门命中率分别为：No Defense 96.0 与 36.9，Trimmed Mean 95.3 与 100.0，Krum 95.2 与 100.0，Bulyan 95.3 与 99.9。CIFAR10 上分别为：No Defense 59.1 与 7.3，Trimmed Mean 55.6 与 80.7，Krum 52.5 与 95.1，Bulyan 51.9 与 84.3。论文指出 No Defense 对图案后门几乎完全免疫（良性精度只降 1%，后门命中率为 0），但在 MNIST 上用更高的 z = 1 与 α = 0.5 重做实验时结论反转：No Defense 达到良性 95.6 与后门 100%，而其他防御在良性输入上的表现不如它。

## 8. 开销

论文**未报告**攻击者侧的计算、通信或存储开销，也**未报告**被评估防御的运行时间、内存或通信量的任何实测值。论文只给出算法层面的结构性描述：Krum 需要对每对节点计算欧氏距离（式 (2)），Bulyan 需要反复调用该规则构造 SelectionSet（Algorithm 2），Trimmed Mean 需要对每个维度做排序或分位数选择（式 (1)），本文攻击需要为每个维度估计均值与标准差（Algorithm 3 第 4 至 6 行），后门攻击还需要一次额外的本地训练与一次逐维裁剪（Algorithm 4）。（分析：以上只是算法结构上的可见成本，论文没有把它们换算成时间、带宽或存储数字。）

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**：

- 各工作节点的参数逐维 i.i.d. 且服从正态分布。论文把它称为分布式学习与所有防御的核心假设，并且明确说自己沿用它，因此攻击幅度的单位取标准差 σ（第 1 节、第 3 节）。
- 攻击者控制的节点具有代表性，从而只用被控节点的参数就能估计总体的 µ_j 与 σ_j（第 3 节）。
- 所有节点的模型结构与参数维度 d 事先约定一致，参数可以逐维对齐比较（第 1 节）。
- 攻击者能在本地训练结束后、上传之前替换参数值，可以通过控制设备或中间人实现（第 1 节、第 2.2 节）。
- 服务器能看到每个节点单独上传的参数向量，并在聚合时使用 Trimmed Mean、Krum 或 Bulyan 这类逐维或基于距离的规则（第 2.3 节）。
- 服务器逐轮独立聚合；被评估的防御全部按轮独立工作（第 2.3 节）。
- 攻击者知道节点总数 n 与恶意节点数 m（Algorithm 3、Algorithm 4 的输入）。

**论文自述的局限**：

- 阻止收敛这类攻击"不太有趣"，因为攻击者不能从中获得后续收益，而且服务器知道被攻击后可能采取行动（第 2.1 节）。
- 朴素平均（No Defense）反而是对该攻击最鲁棒的聚合规则，因为小幅偏移被大量良性节点平均稀释；要打掉朴素平均需要采用混合攻击，即用一个被控节点执行早期论文中的大幅攻击（第 4.1 节、第 4.2 节）。
- 论文在图案后门实验中发现 No Defense 完全不受影响，只有在提高 z 与 α 后才出现反转，说明攻击强度与防御选择之间存在依赖（第 4.2 节）。
- 论文的结论是，在现有防御中应选择 Trimmed Mean 的一个变体，但它同时承认朴素平均被排除仅仅是因为它对更简单的攻击脆弱（第 5 节）。

**是否评估自适应攻击者**：论文**未系统评估**知道本攻击并据此设计的自适应防御者。论文只讨论了对朴素平均这一种聚合规则的自适应混合策略，即用一个被控节点专门实施大幅攻击，其余节点继续实施规避攻击（第 4.1 节、第 4.2 节）。论文也没有测试任何以"逐维一致的小幅同侧偏移"或"多个节点上传完全相同向量"为目标的检测器。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）**：

- **分析**：逐维正态与 i.i.d. 假设在联邦大模型 LoRA 微调中通常不成立。联邦场景的数据划分是异质的，各客户端 LoRA 增量矩阵的逐维分布既不是同一个中心也不是同一个小方差，因此由 φ(z) < (n − s)/n 推出的 z_max 不再是一个有意义的界；论文自己也指出非 i.i.d. 会破坏防御的地基，但那是针对他人的攻击而言，论文没有给出非 i.i.d. 下本文攻击的可行性分析。
- **分析**：本文算法假定"每个维度独立可改"，而 LoRA 只上传低秩增量 ΔW = B·A，可操纵的自由度远小于全参数维度，且低秩因子的尺度与方向不能任意逐维设定。论文完全没有讨论 PEFT 或低秩结构，因此把 z·σ 的逐维扰动映射到 A、B 上需要额外的假设。
- **分析**：本文假定同步 SGD 下所有节点从同一全局参数出发、用相同结构训练，因此逐维参数在节点间可比。LoRA 联邦微调中本地步数、学习率、批组成、乃至目标模块集合都可能不同，参数分布的中心不在同一个 µ 上，攻击者用被控节点估计出的 µ_j 与 σ_j 未必能代表总体。
- **分析**：本文所有防御都要求服务器看到每个客户端的独立参数向量。如果联邦系统启用了安全聚合，服务器只能看到聚合结果，Trimmed Mean 与 Krum 这类规则无法直接执行，针对本文攻击的检测也失去数据来源；论文未讨论安全聚合。
- **分析**：论文的评估指标是图像分类精度与后门图案命中率。迁移到 LLM 后，破坏收敛要改用生成质量或下游任务指标，后门要改用触发词命中率与越狱成功率，论文没有提供任何对应的度量或实验。
- **分析**：论文声称绕过的是 2019 年之前的拜占庭鲁棒聚合与依赖服务器侧数据控制的后门检测。范数裁剪、差分隐私、更新异常检测、信誉评分等现代联邦防御不在论文的测试范围内，因此"绕过所有现有防御"这一结论不能直接外推到联邦 LoRA 场景。

## 10. 对防护库设计的含义

- **分析**：采集底座必须在"服务器收到更新时"提供逐客户端、逐轮、逐参数的原始参数或增量视图，并且要把同一轮所有客户端的更新作为一个完整集合暴露给插件，因为 Trimmed Mean、Krum 与 Bulyan 都要求一次看到全集且都按轮独立工作。这是通用需求，不是本文特有的。
- **分析**：底座还需要在"服务器聚合时"提供一个统计视图，至少包含逐维均值、逐维标准差、逐维中位数、各值到中位数的距离排序，以及客户端之间的成对距离矩阵。这些量在本文中既被攻击者用来构造 p_mal，也被防御者用来做剔除，因此值得由底座统一计算并缓存，避免每个插件重复付出 O(n²d) 的代价。
- **分析**：本论文特有的检测需求是一个"重复更新与同侧一致偏移"的视图：Algorithm 3 与 Algorithm 4 把所有被控节点赋成同一个向量，所以插件需要能问"这一轮是否有若干客户端上传了几乎相同的向量"以及"这些向量是否在大多数维度上同向偏离总体均值约 z 倍标准差"。论文没有提出这个检测器，但它是本文攻击在算法层面必然留下的痕迹。
- **分析**：干预接口必须支持在服务器侧修改参与集合与权重，具体包括剔除客户端（Krum 式只保留一个或少数几个）、逐维裁剪或重加权（Trimmed Mean 式）、以及回滚到历史最优检查点（对应 Algorithm 1 第 10 行的最优轮选择）。这三类动作需要聚合钩子既能读也能改写参与名单与聚合权重。
- **分析**：后门方向需要独立的评估钩子，因为论文用带后门样本与后门图案的测试集来量化攻击成功率，并同时报告良性精度损失。库应把"用于在线防御决策的数据"与"仅在评估阶段使用的带标签后门数据"分开，评估钩子的输入是干净测试集加上攻击者构造的触发样本。
- **分析**：若要把这类逐维扰动检测迁移到联邦 LoRA，底座需要把客户端上传的适配器增量与它对应的全局适配器基线版本配对保存，这样插件才能计算式 (4) 所定义的新旧参数差以及用于归一化的逐维标准差。这是本文方法迁移时特有的一项采集需求，论文本身并未涉及。

## 11. 原文依据

1. 第 Abstract 节：“We show that small but well-crafted changes are sufficient, leading to a novel non-omniscient attack on distributed learning that go undetected by all existing defenses.” —— 支撑第 1 节的论文类型与第 4 节的核心思想：小幅、精心构造的改动即可绕过既有防御。
2. 第 Abstract 节：“We show that 20% of corrupt workers are sufficient to degrade a CIFAR10 model's accuracy by 50%, as well as to introduce backdoors into MNIST and CIFAR10 models without hurting their accuracy.” —— 支撑第 7 节的主要结果与第 2 节的恶意比例。
3. 第 2.2 节：“The attacker interferes the process at the time that maximizes its effect, that is between lines 6 and 7 in Algorithm 1.” —— 支撑第 3 节的攻击入口，即本地训练结束与参数上传之间。
4. 第 2.2 节：“Their attack has the benefits of requiring only a few corrupted workers, as well as being non-omniscient. However, it does not work for distributed training” —— 支撑第 1 节关于本文研究分布式训练而非联邦学习的场景判定，以及第 9 节对假设迁移的讨论。
5. 第 3 节：“This observation enables our attack to work also for non-omniscient attacker, by estimating the properties of the entire population through the corrupted participants alone.” —— 支撑第 2 节关于攻击者知识范围的判断。
6. 第 3 节：“As mentioned above, the research in the field of distributed learning, including all defenses, assumes that the different parameters of all of the workers are i.i.d. and therefore expressed by normal distribution.” —— 支撑第 9 节的 i.i.d. 与正态分布假设。
7. 第 3.1 节：“By setting all corrupted workers to values in the range (µ −zσ, µ + zσ), the attacker guarantees with high probability that those values will be the median” —— 支撑第 4 节的扰动范围推导。
8. 第 3.3 节：“Finally, the attacker will set the value of all the malicious workers to v = µ + 1.75 · σ for each of the parameters independently with the parameters' µj and σj.” —— 支撑第 4 节算例中的 z_max = 1.75 与逐维独立扰动。
9. 第 4.1 节：“Ironically but expected, the best defense strategy against this attack was the simplest aggregation rule of averaging without outliers rejection— No Defense.” —— 支撑第 9 节关于朴素平均对该攻击最鲁棒这一局限。
10. 第 4.1 节：“Krum performed worst again for the same reason with a drop of 66%, Bulyan dropped by 52% and TrimmedMean performed slightly better but still dropped by 45%.” —— 支撑第 7 节图 3 的三个数值结果。

```json
{
  "key": "baruch2019little",
  "title": "A Little Is Enough: Circumventing Defenses For Distributed Learning",
  "year": 2019,
  "paper_type": "attack",
  "setting": "other",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted", "backdoor"],
  "attack_entry": ["local_training", "update_postprocess"],
  "observables": [
    {"what": "每个工作节点每轮上传的完整本地参数向量及其逐维取值", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "被控节点上传向量之间是否逐维完全相同，以及是否在多数维度上同向偏离总体均值约 z 倍标准差（本文攻击的结构性痕迹）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "全体节点参数在每一维上的中位数与各值到中位数的距离排序（Trimmed Mean 逐维裁剪所需）", "where": "server_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "节点参数两两之间的欧氏距离（Krum 选出单一节点所需）", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "逐维均值与标准差（攻击者据此计算 µ_j + z·σ_j，防御者要检测同侧一致偏移也需要同一统计量）", "where": "server_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "Bulyan 的 SelectionSet 及其中逐维的裁剪平均结果", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "聚合后的全局模型及其在干净测试集上的准确率，用于跨轮选择最优模型", "where": "evaluation", "granularity": "model", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "后门样本与左上角 5x5 像素图案样本的命中率，以及良性输入精度损失（论文只用于评估攻击效果）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["exclude_client", "reweight", "rollback"],
  "intervention_where": ["server"],
  "assumptions": [
    "各工作节点的参数逐维独立同分布且近似正态分布，这是攻击推导 z_max 与所有被评估防御的基础",
    "攻击者控制的节点足以代表整体分布，只用被控节点的参数即可估计总体逐维均值与标准差",
    "所有工作节点的模型结构与参数维度 d 事先约定一致，参数可逐维比较",
    "攻击者能在本地训练结束后、上传之前替换参数值（控制设备或中间人）",
    "服务器能看到每个工作节点单独上传的参数向量，并可改变聚合规则",
    "同步 SGD：每轮所有节点从同一全局参数出发并回传完整参数",
    "数据在节点之间按 i.i.d. 切分，与联邦学习的非 i.i.d. 设定不同"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节论文类型与第 4 节核心思想：小幅精心构造的改动即可绕过全部现有防御", "text": "We show that small but well-crafted changes are sufficient, leading to a novel non-omniscient attack on distributed learning that go undetected by all existing defenses."},
    {"section": "Abstract", "supports": "第 7 节主要结果与第 2 节恶意比例：20% 腐败节点足以让 CIFAR10 精度下降 50% 并植入后门", "text": "We show that 20% of corrupt workers are sufficient to degrade a CIFAR10 model's accuracy by 50%, as well as to introduce backdoors into MNIST and CIFAR10 models without hurting their accuracy."},
    {"section": "2.2 Existing Attacks", "supports": "第 3 节攻击入口：介入点位于 Algorithm 1 第 6 行本地训练与第 7 行回传参数之间", "text": "The attacker interferes the process at the time that maximizes its effect, that is between lines 6 and 7 in Algorithm 1."},
    {"section": "2.2 Existing Attacks", "supports": "第 1 节场景判定与第 9 节迁移讨论：本文是分布式训练而非联邦学习，联邦后门攻击不适用于此", "text": "Their attack has the benefits of requiring only a few corrupted workers, as well as being non-omniscient. However, it does not work for distributed training"},
    {"section": "3 Our Attack", "supports": "第 2 节威胁模型知识：攻击者非全知，只用被控参与者估计总体性质", "text": "This observation enables our attack to work also for non-omniscient attacker, by estimating the properties of the entire population through the corrupted participants alone."},
    {"section": "3 Our Attack", "supports": "第 9 节假设：全部工作节点参数逐维 i.i.d. 且服从正态分布", "text": "As mentioned above, the research in the field of distributed learning, including all defenses, assumes that the different parameters of all of the workers are i.i.d. and therefore expressed by normal distribution."},
    {"section": "3.1 Perturbation Range", "supports": "第 4 节扰动范围推导：把被控节点设到均值加减 z 倍标准差区间内即可高概率占据中位数", "text": "By setting all corrupted workers to values in the range (µ −zσ, µ + zσ), the attacker guarantees with high probability that those values will be the median"},
    {"section": "3.3 Preventing Convergence", "supports": "第 4 节算例中的 z_max = 1.75 与逐维独立扰动方式", "text": "Finally, the attacker will set the value of all the malicious workers to v = µ + 1.75 · σ for each of the parameters independently with the parameters' µj and σj."},
    {"section": "4.1 Convergence Prevention", "supports": "第 9 节局限：朴素平均反而是对该攻击最鲁棒的聚合规则", "text": "Ironically but expected, the best defense strategy against this attack was the simplest aggregation rule of averaging without outliers rejection— No Defense."},
    {"section": "4.1 Convergence Prevention", "supports": "第 7 节图 3 的 CIFAR10 数值结果：Krum 下降 66%，Bulyan 下降 52%，Trimmed Mean 下降 45%", "text": "Krum performed worst again for the same reason with a drop of 66%, Bulyan dropped by 52% and TrimmedMean performed slightly better but still dropped by 45%."}
  ]
}
```
