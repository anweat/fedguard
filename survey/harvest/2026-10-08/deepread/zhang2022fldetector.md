# zhang2022fldetector：FLDetector: Defending Federated Learning Against Model Poisoning Attacks via Detecting Malicious Clients

## 1. 基本信息

- **场景**：传统联邦学习（classic federated learning，FL）。论文第 3 节明确设定为"n 个客户端与一台云服务器协同训练一个全局模型"的图像分类任务，不涉及大语言模型，也不涉及参数高效微调（parameter-efficient fine-tuning，PEFT）或 LoRA（low-rank adaptation）。属于 classic_fl。
- **训练阶段**：覆盖完整 FL 训练循环，即服务器下发全局模型、客户端本地计算模型更新、客户端上传更新、服务器聚合、更新全局模型；检测发生在服务器收到客户端更新的阶段，干预后整轮训练重新开始。评估阶段用于计算测试准确率与攻击成功率。
- **论文类型**：防御 / 检测。核心贡献是客户端级恶意检测方法 FLDetector，检测后的防御由 Byzantine-robust（拜占庭鲁棒）聚合方法承担，因此它同时是检测方法，也以检测作为防御手段。
- **模型与数据规模**：数据集为 MNIST、CIFAR10、FEMNIST（第 5.1 节）。MNIST 与 CIFAR10 假设 100 个客户端；FEMNIST 随机采样 300 个书写者，每个书写者视为一个客户端。MNIST 与 FEMNIST 使用四层卷积神经网络（convolutional neural network，CNN），结构见表 1（输入 28×28×1，卷积 + ReLU 3×3×30，最大池化 2×2，卷积 + ReLU 3×3×5，最大池化 2×2，全连接 + ReLU 100，Softmax 输出 10 类，FEMNIST 为 62 类）；CIFAR10 使用 ResNet20。训练轮次为 MNIST 1,000 轮、CIFAR10 与 FEMNIST 2,000 轮。论文未报告任何大模型或 LoRA 规模。

## 2. 威胁模型

- **攻击者是谁**：控制 m 个恶意客户端的攻击者。第 3 节写明这些恶意客户端"可以是被注入的假客户端（fake clients），也可以是被攻陷的真实客户端"。服务器未被攻陷。恶意客户端数量在默认实验设置为客户端总数的 28%，即 MNIST 28 个、CIFAR10 28 个、FEMNIST 84 个（第 5.1 节）。
- **能力**：恶意客户端不按 FL 算法计算更新，而是向服务器发送精心构造的模型更新，即 g_i^t ≠ ∇f(D_i, w^t)（第 3 节）。具体攻击能力包括：在本地数据上复制样本、嵌入触发器并赋予攻击者选定标签；在本地数据被扩增后计算更新；在上传前把更新按因子放大（Scaling Attack，第 2.1 节）；把多个恶意客户端拆成若干组、每组嵌入触发器的一个局部模式（Distributed Backdoor Attack，DBA，第 2.1 节）；对更新做裁剪使其落入特定范围以绕过鲁棒聚合（A Little is Enough Attack，第 2.1 节）；以及把无目标攻击建模为优化问题、求取最优伪造更新（第 2.1 节，Fang 等人的框架）。
- **知识**：第 3 节写明攻击者掌握"恶意客户端上的本地训练数据与模型更新、损失函数、学习率"。第 4.5 节进一步考虑攻击者知道服务器使用了 FLDetector 的自适应攻击（adaptive attack）场景。
- **目标**：两类。无目标（untargeted）攻击使被污染的全局模型对大量测试输入产生错误预测；定向（targeted）攻击（即后门攻击）使带触发器的测试输入被预测为攻击者选定的标签，而其他输入的准确率不受影响（第 1 节、第 2.1 节）。实验中目标标签固定为标签"0"（第 5.1 节）。论文不涉及越狱/安全对齐破坏，也不涉及隐私窃取。
- **防御者是谁、能看到什么、信任什么**：防御者是服务器。服务器能看到每个客户端每轮上传的模型更新、自己维护的全局模型与聚合后的全局更新，并需要保存最近若干轮的这些量（第 4.1 节、第 4.3 节）。服务器不信任客户端提交的更新内容，但信任自己维护的全局状态、信任客户端在"诚实执行本地训练"时会遵循 FL 算法这一前提。论文明确说明其方法不需要服务器拥有干净验证数据集（第 1 节、第 4 节），这是与 VAE 检测方法（Li 等人）和 FLTrust 的关键区别；第 5.1 节还说明因为 FLTrust 额外要求干净验证数据集，实验中没有考虑 FLTrust。

## 3. 攻击入口与流程位置

本文是防御论文，下面写它所针对的攻击入口。

- **本地数据准备**：Scaling Attack 中，攻击者在恶意客户端上复制本地训练样本，把触发器嵌入复制出的输入，并赋予攻击者选定的标签（第 2.1 节）。DBA 中，攻击者把触发器分解为独立的局部模式，并分别嵌入不同恶意客户端的本地训练数据（第 2.1 节）；第 5.1 节说明默认选 28% 恶意比例是因为 DBA 需要把触发器均分为四部分、嵌入四个恶意客户端组。
- **本地训练过程**：Scaling Attack 与 DBA 的模型更新都在被扩增的本地数据上计算（第 2.1 节）。A Little is Enough Attack 的更新先按 Scaling Attack 的方式计算（第 2.1 节）。无目标攻击框架则直接在客户端侧求解一个优化问题，得到最优的伪造更新（第 2.1 节）。论文假设简化情形下良性客户端每轮做一步标准梯度下降，但指出客户端也可以使用随机梯度下降（stochastic gradient descent，SGD）、在本地执行多步 SGD 并把累积梯度作为模型更新上传（第 3 节）。
- **更新上传前的后处理**：Scaling Attack 在上报前把更新按因子放大（第 2.1 节；第 5.1 节说明缩放因子设为 100，沿用文献 [1]）；A Little is Enough Attack 把更新裁剪到特定范围以规避拜占庭鲁棒聚合（第 2.1 节）；无目标攻击框架直接替换上传的更新向量。
- **服务器聚合**：攻击的效果在聚合阶段进入全局模型，即恶意更新被聚合规则计入全局模型更新。
- **FLDetector 自身的位置**：检测发生在服务器"收到更新之后、聚合之前"，输入是当前轮与历史轮的各客户端模型更新（第 3 节）；一旦某一轮判定至少一个客户端为恶意，服务器停止 FL 过程、移除被判定为恶意的客户端，并在剩余客户端上重新开始 FL 过程（第 3 节）。第 5.1 节补充：如果训练完预先设定的轮数都没有检测到恶意客户端，则把所有客户端判为良性。第 5.1 节还说明默认从第 50 轮开始检测，因为最初几十轮可能不稳定。论文未说明"重新开始"时全局模型是重新初始化还是沿用当前全局模型。

## 4. 方法原理

- **核心思想（第 4.1 节）**：良性客户端按 FL 算法和本地数据计算更新，而恶意客户端是"构造"更新而不是遵循算法，因此同一个客户端在多个迭代中的模型更新是不一致的（inconsistent）。FLDetector 通过检查每个客户端模型更新的跨轮一致性来识别恶意客户端。论文强调：无论估计出的 Hessian 是否准确，恶意客户端发来的更新都会与预测更新不同。
- **一致性公式（第 4.1 节，公式 2）**：由 Cauchy 中值定理（Cauchy mean value theorem），g_i^t = g_i^{t-1} + H_i^t · (w^t − w^{t-1})，其中 H_i^t 是客户端 i 在第 t 轮的积分 Hessian，w^t 与 w^{t-1} 是相邻两轮的全局模型。
- **Hessian 近似（第 4.1 节，算法 1）**：积分 Hessian 无法精确计算，论文用 L-BFGS 近似，并且为了效率每轮只近似一个供所有客户端共用的积分 Hessian Ĥ^t。记 Δw^t = w^t − w^{t-1} 为全局模型差，Δg^t = g^t − g^{t-1} 为全局模型更新差（g^t 是由各客户端更新聚合得到的全局更新）；记 ΔW^t 与 ΔG^t 为过去 N 轮（窗口大小为 N）的这两类差，则 Ĥ^t = L-BFGS(ΔW^t, ΔG^t)。算法 1 的输入是 v = w^t − w^{t-1}、ΔW^t、ΔG^t，输出是 Hessian 矩阵在 w^t − w^{t-1} 方向上的投影。
- **更新预测（第 4.1 节，公式 3）**：ĝ_i^t = g_i^{t-1} + Ĥ^t (w^t − w^{t-1})。
- **可疑分数（第 4.2 节）**：用欧氏距离（Euclidean distance）度量预测更新与实收更新的一致性，d^t = [‖ĝ_1^t − g_1^t‖₂, …, ‖ĝ_n^t − g_n^t‖₂]；归一化 d̂^t = d^t / ‖d^t‖₁，归一化的目的是吸收不同迭代间一致性变化的量级差异；客户端 i 在第 t 轮的可疑分数是过去 N 轮归一化距离的平均值，s_i^t = (1/N) Σ_{r=0}^{N−1} d̂_i^{t−r}，N 称为窗口大小。
- **无监督检测（第 4.2 节，算法 2、算法 3）**：基于所有客户端的可疑分数做聚类，用 Gap statistics 判断簇数。若 Gap statistics 认为可以分成多于 1 个簇，就用 k-means 把客户端分成 2 簇，平均可疑分数更大的那一簇中的客户端被判为恶意。Gap statistics 的步骤包括：k 从 1 到 K 做 k-means 并计算簇内离散度 W_k；生成 B 个参考数据集（均匀分布）并计算 Gap(k) = (1/B) Σ log(W*_kb) − log(W_k)；计算标准差 sd(k) 与 s'_{k+1} = sqrt((1+B)/B) sd(k)；取满足 Gap(k) − Gap(k+1) + s'_{k+1} ≥ 0 的最小 k 为簇数。若簇数大于 1 则把攻击检测标志 Flag 置为正，因为有离群的可疑分数。
- **理论分析（第 4.4 节，定理 1）**：在各客户端损失梯度 L-smooth、聚合规则为 FedAvg、各客户端本地数据独立同分布（iid）、学习率 α < 1/((N+2)L) 的条件下，若恶意客户端每轮把真实更新反号（发送 −g_i^t），则每一轮良性客户端的期望可疑分数小于恶意客户端，即 E(s_i^t) < E(s_j^t)（公式 5）。附录 A 用引理 1（z^T Ĥ^t z ≤ (N+1)L‖z‖²，公式 7）证明该结论。
- **自适应攻击（第 4.5 节，公式 6）**：攻击者若知道 FLDetector 被使用，可在原攻击损失上加入正则项：min_{g_i^t} λ L_attack + (1−λ)‖g_i^t − (g_i^{t-1} + Ĥ_i^t (w^t − w^{t-1}))‖，其中 Ĥ_i^t 是在客户端 i 自己的数据集上计算得到的 Hessian，λ ∈ (0,1] 用于平衡攻击损失与正则项。

## 5. 检测或防御所需的数据

FLDetector 是纯服务器侧方法，客户端除正常训练与上传更新外不提供额外数据。逐项如下。

1. **每个客户端每轮的模型更新 g_i^t**
   - 是什么：客户端 i 在第 t 轮上传的模型更新向量（论文设定下为对全局模型的梯度；第 3 节也允许本地多步 SGD 的累积梯度）。
   - 在哪里采集：服务器收到更新时（server_receive），聚合之前；需要能按客户端身份区分更新。
   - 粒度：逐客户端、逐轮、逐参数（整模型或整个上传参数块）。
   - 跨轮历史：需要。公式 3 用到同一客户端上一轮的更新 g_i^{t-1}；可疑分数需要过去 N 轮（默认 N = 10，第 5.1 节）。
   - 干净参考数据：不需要。根数据集：不需要。额外前向/反向计算：客户端侧不需要。其他客户端的数据：单个客户端的预测只用到它自己的上一轮更新与全局量；但 k-means 聚类阶段需要所有客户端当轮的可疑分数（跨客户端）。
2. **全局模型序列 w^t、w^{t-1} 及全局模型差 Δw^t**
   - 是什么：服务器维护的相邻两轮全局模型及其差。
   - 在哪里采集：服务器聚合后的全局模型（server_post_aggregate），以及训练开始时服务器持有的初始模型。
   - 粒度：逐轮、整模型（逐参数向量）。
   - 跨轮历史：需要，L-BFGS 使用过去 N 轮的 ΔW^t。干净参考数据：不需要。额外计算：构造差向量本身开销很小。其他客户端数据：全局模型是全体客户端更新的聚合结果。
3. **聚合后的全局模型更新序列 g^t 及全局模型更新差 Δg^t**
   - 是什么：由各客户端更新按聚合规则得到的全局更新，及其相邻轮之差。
   - 在哪里采集：服务器聚合时（server_aggregate）。
   - 粒度：逐轮、整模型。
   - 跨轮历史：需要，过去 N 轮。干净参考数据：不需要。额外计算：无（是聚合过程的自然产出），但必须在检测使用的聚合规则下被记录下来。其他客户端数据：它是全体参与客户端更新的函数。
4. **预测更新 ĝ_i^t 与欧氏距离 d_i^t = ‖ĝ_i^t − g_i^t‖₂**
   - 是什么：由公式 3 得到的预测更新，以及预测更新与实收更新之间的欧氏距离。
   - 在哪里采集：服务器收到更新后（server_receive 之后、聚合之前）计算。
   - 粒度：逐客户端、逐轮，距离是标量。
   - 跨轮历史：预测需要上一轮该客户端的更新。干净参考数据：不需要。额外计算：需要。论文第 4.3 节说明 L-BFGS 估计 Hessian 与计算 Hessian 向量积（Hessian vector product，HVP）的复杂度为 O(N³ + 6Np)，其中 p 是全局模型参数个数。
5. **归一化距离 d̂^t 与客户端可疑分数 s_i^t**
   - 是什么：d̂^t = d^t / ‖d^t‖₁，以及窗口平均 s_i^t = (1/N) Σ_{r=0}^{N−1} d̂_i^{t−r}。
   - 在哪里采集：服务器侧派生量。
   - 粒度：逐客户端、逐轮，标量。
   - 跨轮历史：需要，窗口大小 N（默认 10）。干净参考数据：不需要。额外计算：需要，计算可疑分数的复杂度为 O(2np + Nn)。其他客户端数据：归一化用到所有客户端当轮距离之和。
6. **全部客户端的可疑分数向量 s^t（用于聚类）**
   - 是什么：当轮 n 个客户端的可疑分数集合。
   - 在哪里采集：服务器侧。
   - 粒度：逐客户端、逐轮（聚类的输入是当轮横截面）。
   - 跨轮历史：可疑分数本身已含窗口历史。干净参考数据：不需要（Gap statistics 的参考分布是对可疑分数做线性变换后在 [0,1] 上均匀采样的随机数据集，不是真实数据）。额外计算：需要，Gap statistics 与 k-means 的总复杂度为 O(KBn²)。其他客户端数据：必须同时拿到所有客户端（或被采样参与）的可疑分数。
7. **超参数与规模常量**
   - 窗口大小 N、Gap statistics 的最大簇数 K 与采样次数 B、客户端数 n、训练总轮数 I_ter、开始检测的轮次。默认 N = 10、K = 10、B = 20、从第 50 轮开始检测（第 5.1 节）。这些是配置，不是采集数据。
8. **自适应攻击方额外需要的量（针对第 4.5 节的攻击）**
   - 是什么：客户端侧在自身数据集上计算的 Hessian Ĥ_i^t、上一轮自己的更新 g_i^{t-1}、全局模型差 w^t − w^{t-1}。
   - 在哪里采集：恶意客户端本地训练过程（client_step）。
   - 粒度：逐客户端、逐轮、逐参数（Hessian 为二阶量）。
   - 干净参考数据：不需要。额外计算：需要（客户端侧二阶计算）。其他客户端数据：不需要。
9. **论文明确不需要的东西**：干净验证数据集 / 根数据集（第 1 节明确把"不需要干净验证数据集"作为相对 VAE 检测方法的改进；第 5.1 节说明因为 FLTrust 需要干净验证数据集而没有在实验中考虑它）。论文也未使用逐样本损失、隐藏层激活、输出文本或梯度之外的原始训练数据。

**攻击留下的可观测量与论文声称能检测/绕过的情形**：攻击的直接痕迹是"实收更新与基于 Cauchy 中值定理、由历史更新预测出的更新之间的欧氏距离"在恶意客户端上系统性偏大（第 4.1、4.2 节，图 3 显示攻击开始时恶意客户端的平均可疑分数迅速上升、攻击停止后回落到与良性客户端相当）。论文还报告两个对照变体以说明哪些观测量不够：FLD-Norm 只用更新本身的 ℓ2 范数（多个设置下失效，例如 FEMNIST 的 A Little is Enough 攻击下 DACC 仅 0.05，表 2），FLD-NoHVP 去掉 Hessian 向量积项、只用上一轮更新做预测（FEMNIST 上 DACC 低至 0.07，表 2）。论文报告容易被规避的情形是自适应攻击：DACC 随 λ 减小而下降（图 4(a)）；以及周期性攻击时无攻击轮次可疑分数回落（图 3）。

## 6. 干预动作

- **动作一：停止训练**。某一轮只要有一个客户端被判为恶意，服务器就停止 FL 过程（第 3 节）。
- **动作二：剔除客户端**。服务器移除被判定为恶意的客户端（第 3 节；第 5.1 节再次说明"服务器移除被分类为恶意的客户端"）。
- **动作三：在剩余客户端上重新开始训练**。第 3 节写的是"在剩余客户端上重新开始 FL 过程"；第 5.1 节写的是"重新开始 FL 训练，并对预先设定的轮数重复该过程"。论文未说明重启时全局模型是否重新初始化，也未说明是否需要回滚到某个历史模型快照。
- **动作四：把剩余客户端交给 Byzantine-robust 聚合**。FLDetector 的设计定位是"检测并移除大多数恶意客户端，使得 Byzantine-robust 或可证明鲁棒的 FL 方法能用剩余客户端学到准确全局模型"（摘要、第 1 节）；漏检的少量恶意客户端由聚合规则兜底。
- **动作五：无检测结果时的默认判定**。如果训练完预先设定的轮数都没有检测到恶意客户端，就把所有客户端判为良性（第 5.1 节）。
- **动作位置**：全部在服务器侧，发生在收到更新之后、聚合之前（检测），以及聚合与全局模型更新之后（停止并重启训练）。

## 7. 实验设置与主要结果

**设置（第 5.1 节）**：数据集 MNIST、CIFAR10、FEMNIST；MNIST 与 CIFAR10 为 100 个客户端，FEMNIST 为 300 个客户端；默认非独立同分布（non-iid）程度为 0.5（该参数范围 0.1 到 1.0，大于 0.1 即为非独立同分布）；聚合方法 FedAvg、Krum、Trimmed-Mean、Median；MNIST 训练 1,000 轮、学习率 2×10⁻⁴，CIFAR10 与 FEMNIST 训练 2,000 轮、学习率 1×10⁻³；为简化假设每轮所有客户端都参与（即参与率 100%，论文未测试部分参与）；默认 28% 客户端为恶意（MNIST 28 个、CIFAR10 28 个、FEMNIST 84 个）；四种攻击为无目标模型投毒攻击、Scaling Attack、DBA、A Little is Enough Attack，触发器与原论文一致、目标标签为"0"、缩放因子 100；被测检测方法为 VAE、FLD-Norm、FLD-NoHVP、FLDetector；硬性设定 N = 10、K = 10、B = 20，默认从第 50 轮开始检测。指标为检测准确率（DACC）、假阳性率（FPR）、假阴性率（FNR）、测试准确率（TACC）与攻击成功率（ASR）。

**主要结果**：

- 表 2（FEMNIST，28 个恶意客户端，CNN 全局模型）：FLDetector 的 FNR 在不同攻击与聚合方法下全为 0.00，FPR 在 0.00 到 0.20 之间，DACC 在 0.85 到 1.00 之间。例如 FedAvg 下 Scaling Attack 为 DACC 0.85 / FPR 0.20 / FNR 0.00，DBA 为 0.92 / 0.11 / 0.00，A Little is Enough 为 0.93 / 0.10 / 0.00；Krum、Trimmed-Mean、Median 下多数为 1.00 / 0.00 / 0.00，Trimmed-Mean 下 Scaling Attack 为 0.98 / 0.03 / 0.00。同一张表中 VAE 的 DACC 为 0.55 到 0.80。
- 表 4（MNIST，28 个恶意客户端）：FLDetector 的 DACC 范围约 0.80 到 1.00；例如 FedAvg 下无目标攻击为 0.87 / 0.18 / 0.00，DBA 为 0.86 / 0.15 / 0.11；Krum 与 Trimmed-Mean 下 Scaling Attack 分别为 0.98 / 0.00 / 0.07 与 1.00 / 0.00 / 0.00。
- 表 5（CIFAR10，28 个恶意客户端，ResNet20）：FLDetector 的 DACC 在 0.80 到 1.00 之间；A Little is Enough 攻击下 FedAvg 为 0.80 / 0.14 / 0.36，Krum 为 0.92 / 0.11 / 0.00，Trimmed-Mean 为 0.89 / 0.13 / 0.07，Median 为 0.87 / 0.15 / 0.07。
- 表 3（Median 聚合下的 TACC 与 ASR，攻击列中定向攻击写成"TACC / ASR (%)"）：MNIST 无攻击 97.6，无目标攻击在无 FLDetector 时 TACC 69.5、有 FLDetector 时 97.4；CIFAR10 无攻击 65.8，无目标攻击 27.8 → 65.9，Scaling Attack 66.6 / 91.2 → 65.7 / 2.4，DBA 66.1 / 93.5 → 65.2 / 1.9，A Little is Enough 62.1 / 95.2 → 64.3 / 1.8；FEMNIST 无攻击 64.4，无目标攻击 14.3 → 63.2，Scaling Attack 66.4 / 57.9 → 64.5 / 1.7，DBA 67.5 / 53.2 → 64.3 / 2.1，A Little is Enough 66.7 / 59.6 → 65.0 / 1.6。
- 表 6（MNIST，不同 FL 方法）：FLDetector 部署后 Krum、Trimmed-Mean、Median 的 ASR 大多降到 0.3% 到 0.9%；但 FedAvg 下 ASR 仍然很高（Scaling Attack 98.2 / 99.6，DBA 98.1 / 99.5），表 6 标题说明原因是"FedAvg 不是 Byzantine-robust，即使只有一个恶意客户端也能植入后门"。
- 第 5.2 节正文：在 FEMNIST 上 FLDetector 的 FNR 对不同攻击与 FL 方法始终为 0.0，FPR 在 0.0 到 0.20 之间；FLDetector 在 MNIST 与 CIFAR10 上多数情况优于 VAE，其余情况性能相当；在 CIFAR10 上 Median 与 A Little is Enough 攻击的组合中，FLDetector 漏检了 2 个恶意客户端，但 Median 在训练全局模型时能抵御它们。
- 图 1（CIFAR10、Median、非 iid 程度 0.5）：恶意客户端数超过约 30 个后（无目标攻击）或超过 20 个后（A Little is Enough 攻击）DACC 开始下降；部署 FLDetector 的 TACC 高于或相当于未部署时，ASR 显著更低。
- 图 3（MNIST、非 iid 程度 0.5、28 个恶意客户端，恶意客户端在第 50 轮到第 100 轮攻击、每 100 轮重复一次）：可疑分数呈现与攻击同步的周期性；论文称在这组实验中 FLDetector 能在第 60 轮左右检测到恶意客户端，且 FLDetector 并不知道攻击何时开始或结束。
- 图 4（CIFAR10、Median、非 iid 程度 0.5、28 个恶意客户端、Scaling Attack）：自适应攻击下 DACC 随 λ 减小而下降，但 ASR 仍然很低，因为恶意客户端在试图规避检测时本地更新也变得不那么有效（图 4(a)）；检测起始轮次从 10 到 60 变化时，提前开始会因早期不稳定使 DACC 略降，但仍能移除大多数恶意客户端（图 4(b)）；窗口大小 N 与采样次数 B 的影响见（图 4(c)、(d)），N 太小时 DACC 略降。

## 8. 开销

论文报告了服务器侧开销（第 4.3 节）：

- **存储**：服务器需要保存最近 N 轮的全局模型差与全局模型更新差，存储开销为 O(Np)，其中 p 是全局模型参数个数。
- **计算**：用 L-BFGS 估计 Hessian 并计算 Hessian 向量积的复杂度为 O(N³ + 6Np)（每轮）；计算可疑分数的复杂度为 O(2np + Nn)（每轮，n 为客户端数）；Gap statistics 与 k-means 的总复杂度为 O(KBn²)。每轮总时间复杂度为 O(N³ + KBn² + (6N + 2n)p + Nn)。因为 K、B、n、N 通常远小于 p，服务器每轮的时间复杂度大致与全局模型参数量线性相关。论文认为服务器在 FL 中算力较强，因此这部分存储与计算开销可以接受。
- **客户端开销**：论文明确写"对于客户端，FLDetector 不引入额外的计算与通信开销"（第 4.3 节）。
- 论文未报告墙钟运行时间、内存占用的绝对值，也未报告额外通信量的测量值（除"客户端无额外通信"这一陈述外）。论文未报告客户端侧的任何额外开销。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设（论文有依据的部分）**：

- 服务器不可信客户端但自身可信，且能看到每个客户端的明文模型更新（第 3 节；论文未讨论安全聚合或匿名上传场景）。
- 良性客户端严格遵循 FL 算法计算更新，恶意客户端不遵循算法而伪造更新，因此后者跨轮不一致（第 4.1 节）。
- 攻击者掌握恶意客户端的本地数据、模型更新、损失函数与学习率（第 3 节）。
- 实验为简化假设每轮所有客户端都参与训练（第 5.1 节），论文未评估部分参与或客户端采样。
- 定理 1 的额外假设（第 4.4 节）：客户端损失梯度 L-smooth；聚合规则为 FedAvg；各客户端本地训练数据独立同分布；学习率 α < 1/((N+2)L)；恶意客户端每轮把真实更新反号。注意实验中默认使用的是非独立同分布数据（程度 0.5）与多种聚合规则，因此定理条件与实验设置并不完全一致。
- 检测需要积累多轮历史并等到训练较后阶段：默认从第 50 轮才开始检测，因为最初几十轮可能不稳定（第 5.1 节）；论文未说明在更少轮次预算下能否工作。
- 检测效果依赖可疑分数可被 k-means 与 Gap statistics 分成可分离的簇；论文未给出该条件不满足时的性能保证。
- 检测后需要 Byzantine-robust 聚合来兜底漏检者（第 1 节；表 6 显示 FedAvg 下即使部署 FLDetector，ASR 仍高达 98.1% 到 99.6%）。
- 服务器算力足够做 L-BFGS 近似 Hessian 与 Hessian 向量积（第 4.3 节）。

**论文自述的局限/未来工作（第 6 节）**：作者把方法扩展到纵向联邦学习（vertical federated learning）、异步联邦学习（asynchronous federated learning）、文本与图等其他领域的联邦学习，以及在移除检测出的恶意客户端后高效恢复全局模型，列为未来方向。论文还报告了方法本身的误差：FPR 在 FEMNIST 上可达 0.20（第 5.2 节与表 2），在 CIFAR10 上会漏检（例如漏检 2 个恶意客户端，第 5.2 节）。

**自适应攻击者**：论文评估了自适应攻击（evaluates_adaptive_attacker = true）。第 4.5 节设计了针对 FLDetector 的自适应攻击（公式 6），第 5.2 节与图 4(a) 报告：DACC 随 λ 减小而下降，但 ASR 仍然很低，原因是恶意客户端为规避检测而使本地更新变得不那么有效。论文还评估了周期性攻击（图 3），FLDetector 不知道攻击的起止时间，仍能在第 60 轮左右检测到。论文未针对全部四种攻击分别构造自适应版本，第 5.2 节明确说明图 4(a) 是把 Scaling Attack 自适应化。

**分析：迁移到联邦大模型 LoRA 微调时可能失效的假设**

- 参数空间对齐假设。FLDetector 的一致性检验、L-BFGS 与 Hessian 向量积都作用在同一个参数向量上。LoRA 微调中不同客户端可能使用不同的秩、不同的目标模块（target modules）或不同的适配器初始化，此时"客户端更新"不在同一参数空间，Δw 与 Δg 无定义。论文未涉及这一情形。
- 本地训练过程假设。论文的理论针对"每轮一步梯度下降、损失 L-smooth、数据 iid"的情形；大模型 LoRA 微调通常使用 Adam 类优化器、多轮本地 epoch、大批次与长度不一的序列，且数据高度非独立同分布。分析：积分 Hessian 的 L-BFGS 近似在这种设定下会更不可靠，而论文只在四层 CNN 与 ResNet20、100 到 300 个客户端的规模上验证过。
- 全参与假设。论文假设每轮所有客户端参与；联邦大模型微调常见客户端采样与动态加入退出。分析：窗口平均与 L-BFGS 历史都会出现缺失项，需要库额外定义缺失轮次的处理方式，论文没有给出。
- 服务器可见明文逐客户端更新。若库采用安全聚合或匿名上传，服务器拿不到按客户端区分的更新，FLDetector 的核心观测量不存在。论文未讨论这一场景。
- 二阶计算的可承受性。分析：论文的复杂度按全局模型参数量 p 线性，但常数项包含 6N 次参数规模的向量运算与 L-BFGS 历史。若只对 LoRA 增量做检测，p 是可接受的低秩参数量；若对全参数更新做检测，开销在训练循环内可能不可忽略。论文未报告任何大模型实验，也未报告墙钟时间。
- 干预代价。论文的干预是"停止整个 FL 过程并重新开始训练"。分析：在大模型微调中，重启训练的代价远高于图像模型，库需要提供"不中断训练、仅把检测结果传递给聚合阶段"的干预路径，而论文只写了重启这一种动作。
- 攻击目标覆盖面。论文的目标是图像分类上的无目标准确率下降与后门攻击；若库还要防越狱或安全对齐破坏，分析：论文没有提供这类攻击下的检测证据，且用极少样本植入的安全对齐破坏可能比图像后门更隐蔽。
- 干净参考数据。论文的优点是不需要干净验证数据集，这一假设在联邦大模型微调场景下同样成立且更有价值，因为服务器更难获得代表性根数据集。这一点是正向可迁移的。

## 10. 对防护库设计的含义

以下全部是分析。

- **采集点**：库的服务器钩子必须能在"收到更新、聚合之前"按客户端身份取出该轮的完整更新向量，并把它作为一等数据对象保留下来。这是通用需求；这篇论文特有的地方在于它还需要服务器按轮保存"全局模型"与"聚合后的全局更新"两条时间序列，用来构造 ΔW 与 ΔG，因此底座不能只保存聚合结果，还要保存聚合前后的全局状态快照。
- **数据视图**：插件需要的核心视图是"客户端 × 轮次 × 参数"的时间序列，以及在其上派生的每客户端每轮欧氏距离、归一化距离与窗口均值（可疑分数）。库应把"逐客户端更新的历史缓冲"作为底座能力提供（至少可配置长度，本文默认 10），而不是让每个插件自己缓存；同时应提供横截面视图，供聚类类插件一次拿到当轮全部客户端的标量分数。
- **干预接口**：这篇论文的动作粒度是客户端级的"剔除 + 停止并重启训练"，而不是单轮的加权或裁剪。库的服务器钩子需要支持"中断训练循环、更新客户端白名单、按剩余客户端重新开始训练"这类粗粒度控制；如果底座只能做逐轮加权，就无法复现本文的防御。分析：在联邦 LoRA 微调里应补充一种"不重启、仅把客户端白名单传给聚合插件"的轻量路径。
- **插件编排**：本文的定位是"检测插件先把大多数恶意客户端摘掉，再由鲁棒聚合插件处理漏网者"。因此库需要允许检测插件与聚合插件串联，并允许检测结果以客户端白名单/黑名单的形式传入聚合阶段；同时要允许检测插件在未触发时静默通过（本文在训练结束仍未检测到就把所有客户端判为良性）。
- **计算与依赖**：这是一个不需要干净参考数据、但需要在服务器侧做二阶近似计算（L-BFGS 求 Hessian 向量积）与聚类（k-means + Gap statistics）的插件，客户端侧零改动。库应把这类重计算插件与训练主循环解耦（可异步或按需触发），并把窗口大小、最大簇数、采样次数、起始检测轮次暴露为配置。
- **参数空间契约**：若要把本文方法迁移到联邦 LoRA，底座必须在采集层保证"每轮每个客户端上传的增量处在同一参数空间"，即相同的目标模块集合与可对齐的秩（或由服务器统一投影到同一子空间），否则插件拿到的是不可比的向量。这属于本文未涉及、但库必须显式约束的前置条件。

## 11. 原文依据

1. 摘要 — 支撑第 4 节"核心思想是恶意客户端跨轮更新不一致"这一论断。
   > "Our key observation is that, in model poisoning attacks, the model updates from a client in multiple iterations are inconsistent."
2. 第 3 节 Attack model — 支撑第 2 节的攻击者身份与被攻陷范围。
   > "Specifically, an attacker controls m malicious clients, which can be fake clients injected by the attacker or genuine ones compromised by the attacker. However, the server is not compromised."
3. 第 2.1 节 — 支撑第 3 节"Scaling Attack 从本地数据准备进入"的具体步骤。
   > "in Scaling Attack [1], the attacker makes duplicates of the local training examples on the malicious clients, embeds the trigger to the duplicated training inputs, and assigns an attacker-chosen label to them."
4. 第 3 节 Problem definition — 支撑第 6 节"停止训练、剔除客户端、重启训练"的干预动作。
   > "When at least one client is classified as malicious by our method in a certain iteration, the server stops the FL process, removes the clients detected as malicious, and restarts the FL process on the remaining clients."
5. 第 4.2 节 — 支撑第 4 节与第 6 节的判定规则（k-means 两簇、平均可疑分数大者为恶意）。
   > "then we use k-means to divide the clients into 2 clusters based on their suspicious scores. Finally, the clients in the cluster with larger average suspicious score are classified as malicious."
6. 第 4.3 节 Complexity Analysis — 支撑第 8 节的开销结论与"客户端零额外开销"。
   > "We note that the server is powerful in FL, so the storage and computation overhead of FLDetector for the server is acceptable. As for the clients, FLDetector does not incur extra computation and communication overhead."
7. 第 4.4 节 Theorem 1 — 支撑第 9 节列出的理论假设（L-smooth、FedAvg、iid）。
   > "Suppose the gradient of each client's loss function is L-smooth, FedAvg is used as the aggregation rule, the clients' local training datasets are iid"
8. 第 4.5 节 Adaptive Attacks — 支撑第 9 节"论文评估了知道检测器存在的自适应攻击者"。
   > "When the attacker knows that our FLDetector is used to detect malicious clients, the attacker can adapt its attack to FLDetector to evade detection."
9. 附录表 6 标题 — 支撑第 9 节"漏检者必须由 Byzantine-robust 聚合兜底，FedAvg 不具该性质"。
   > "The ASR on FedAvg with FLDetector is still high because FedAvg is not Byzantine-robust and can be backdoored by even a single malicious client."
10. 第 6 节 Conclusion and Future Work — 支撑第 9 节"论文自述的局限与适用范围"（原句在此逗号后继续，本文只截取到该逗号）。
    > "Interesting future research directions include extending our method to vertical federated learning, asynchronous federated learning, federated learning in other domains such as text and graphs,"

```json
{
  "key": "zhang2022fldetector",
  "title": "FLDetector: Defending Federated Learning Against Model Poisoning Attacks via Detecting Malicious Clients",
  "year": 2022,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted", "backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {"what": "每个客户端每轮上传的模型更新 g_i^t（梯度或本地多步 SGD 的累积梯度）", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "全局模型 w^t、w^{t-1} 及全局模型差 Δw^t（保留过去 N 轮）", "where": "server_post_aggregate", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "聚合后的全局模型更新 g^t 及其差 Δg^t（保留过去 N 轮）", "where": "server_aggregate", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "由 L-BFGS 近似 Hessian 与 Hessian 向量积得到的预测更新 ĝ_i^t，以及预测更新与实收更新的欧氏距离 d_i^t", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "归一化距离 d̂^t 与客户端可疑分数 s_i^t（过去 N 轮归一化距离均值，N 默认 10）", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "当轮全部客户端的可疑分数向量（k-means 与 Gap statistics 的输入）", "where": "server_receive", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "超参数与规模常量：窗口大小 N、最大簇数 K、采样次数 B、客户端数 n、总轮数、起始检测轮次", "where": "server_receive", "granularity": "round", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "自适应攻击方在客户端本地计算的 Hessian Ĥ_i^t、上一轮自身更新 g_i^{t-1} 与全局模型差（公式 6 所需）", "where": "client_step", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["exclude_client"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务器未被攻陷，且能看到按客户端区分的明文模型更新（论文未考虑安全聚合或匿名上传）",
    "良性客户端严格按 FL 算法计算更新，恶意客户端伪造更新，因此恶意客户端跨轮更新不一致",
    "为简化，每轮所有客户端都参与训练（论文未评估部分参与或客户端采样）",
    "定理 1 额外要求梯度 L-smooth、聚合规则为 FedAvg、各客户端本地数据 iid、学习率 α < 1/((N+2)L)、恶意客户端逐轮反转真实更新",
    "可疑分数能被 k-means 与 Gap statistics 分成可分离的簇；论文未给出该条件不成立时的保证",
    "服务器算力足够做 L-BFGS 近似 Hessian 与 Hessian 向量积，并保存最近 N 轮的全局量与更新",
    "漏检的少量恶意客户端由 Byzantine-robust 聚合兜底，FedAvg 不具该性质",
    "检测需要积累多轮历史并等到训练较后阶段（默认从第 50 轮开始检测）"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 4 节核心思想：恶意客户端的模型更新跨轮不一致", "text": "Our key observation is that, in model poisoning attacks, the model updates from a client in multiple iterations are inconsistent."},
    {"section": "Section 3 Attack model", "supports": "第 2 节攻击者身份、数量符号与服务器未被攻陷", "text": "Specifically, an attacker controls m malicious clients, which can be fake clients injected by the attacker or genuine ones compromised by the attacker. However, the server is not compromised."},
    {"section": "Section 2.1", "supports": "第 3 节 Scaling Attack 从本地数据准备进入的攻击步骤", "text": "in Scaling Attack [1], the attacker makes duplicates of the local training examples on the malicious clients, embeds the trigger to the duplicated training inputs, and assigns an attacker-chosen label to them."},
    {"section": "Section 3 Problem definition", "supports": "第 6 节干预动作：停止训练、剔除恶意客户端、在剩余客户端上重启", "text": "When at least one client is classified as malicious by our method in a certain iteration, the server stops the FL process, removes the clients detected as malicious, and restarts the FL process on the remaining clients."},
    {"section": "Section 4.2", "supports": "第 4 节与第 6 节的判定规则：k-means 分两簇、平均可疑分数大者为恶意", "text": "then we use k-means to divide the clients into 2 clusters based on their suspicious scores. Finally, the clients in the cluster with larger average suspicious score are classified as malicious."},
    {"section": "Section 4.3 Complexity Analysis", "supports": "第 8 节开销结论与客户端零额外开销", "text": "We note that the server is powerful in FL, so the storage and computation overhead of FLDetector for the server is acceptable. As for the clients, FLDetector does not incur extra computation and communication overhead."},
    {"section": "Section 4.4 Theorem 1", "supports": "第 9 节列出的理论假设（L-smooth、FedAvg、本地数据 iid）", "text": "Suppose the gradient of each client's loss function is L-smooth, FedAvg is used as the aggregation rule, the clients' local training datasets are iid"},
    {"section": "Section 4.5 Adaptive Attacks", "supports": "第 9 节：论文评估了知道检测器存在的自适应攻击者", "text": "When the attacker knows that our FLDetector is used to detect malicious clients, the attacker can adapt its attack to FLDetector to evade detection."},
    {"section": "Appendix Table 6 caption", "supports": "第 9 节：漏检者需由 Byzantine-robust 聚合兜底，FedAvg 不具备该性质", "text": "The ASR on FedAvg with FLDetector is still high because FedAvg is not Byzantine-robust and can be backdoored by even a single malicious client."},
    {"section": "Section 6 Conclusion and Future Work", "supports": "第 9 节论文自述的适用边界与未来工作（原句在末尾逗号后继续）", "text": "Interesting future research directions include extending our method to vertical federated learning, asynchronous federated learning, federated learning in other domains such as text and graphs,"}
  ]
}
```
