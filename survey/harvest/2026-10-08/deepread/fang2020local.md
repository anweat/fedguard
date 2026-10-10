# fang2020local：Local Model Poisoning Attacks to Byzantine-Robust Federated Learning

## 1. 基本信息

- **场景**：传统联邦学习（classic federated learning）。论文研究的是多个客户端设备共同训练一个小型分类器，服务器（论文称 master device，主设备）按 Krum、Bulyan、trimmed mean、median 等拜占庭鲁棒（Byzantine-robust）聚合规则聚合完整模型参数。论文完全不涉及大语言模型、Transformer 或参数高效微调（parameter-efficient fine-tuning, PEFT），也不涉及 LoRA。
- **训练阶段**：训练阶段的"学习过程"（learning process）。论文在 Figure 1 中把训练阶段拆成"训练数据收集"（training dataset collection）与"学习过程"两部分，并明确说自己攻击后者，具体进入点是每轮迭代中客户端更新完本地模型之后、把本地模型上传给主设备之前。
- **论文类型**：攻击（attack）为主，同时包含防御（defense）部分：作者把两个面向数据投毒的防御 RONI 与 TRIM 泛化成 ERR 与 LFR，用来防御自己提出的本地模型投毒攻击（Section 5）。
- **模型与数据规模**：分类器是多分类逻辑回归（multi-class logistic regression, LR）与深度神经网络（deep neural network, DNN）。MNIST、Fashion-MNIST、Breast Cancer Wisconsin (Diagnostic) 用附录 Table 7a 的 DNN（3×3×30 卷积+ReLU、2×2 最大池化、3×3×50 卷积+ReLU、2×2 最大池化、200 维全连接+ReLU、Softmax），CH-MNIST 用 ResNet20（Section 4.1）。数据：MNIST 与 Fashion-MNIST 各 60000 训练 / 10000 测试、28×28 灰度、10 类；CH-MNIST 共 5000 张，随机取 4000 训练、1000 测试，64×64 灰度，8 类；Breast Cancer Wisconsin (Diagnostic) 共 569 例，455（80%）训练、114 测试，30 维特征，二分类（Section 4.1）。默认 100 个客户端设备、20 个被攻陷（Table 1）；LR 在 MNIST 上训练 500 轮，DNN 在四个数据集上训练 2000 轮，批大小 32（Fashion-MNIST 为 64）（Section 4.1）。

## 2. 威胁模型

- **攻击者是谁**：被攻陷的客户端设备（compromised worker devices）。论文说攻击者可以像 Sybil 攻击一样注入 c 个假设备，也可以攻陷 c 个良性设备；论文统一称这些设备为 compromised worker devices（Section 2.3）。
- **占比或数量**：默认 c = 20，m = 100，即 20%（Table 1）。论文假设攻击者控制的设备数严格少于 50%（Section 2.3）。
- **能力（能改什么）**：可以任意操纵这些被攻陷设备发送给主设备的本地模型参数（Section 2.3）。论文说攻击者"在每一轮迭代中"都操纵这些本地模型（Section 4.1）。论文没有给攻击者改服务器、改聚合规则、改其他客户端数据或改评估流程的能力。
- **知识（知道什么）**：知道被攻陷设备上的代码、本地训练数据集和本地模型（Section 2.3）。另有两个维度：聚合规则（知道 / 不知道，不知道时按某个假定的聚合规则构造本地模型并依赖迁移性）与训练数据（全知识 full knowledge，即知道所有设备上的本地数据与本地模型，论文自己说这在实际中适用性有限，只用来估计威胁上界；部分知识 partial knowledge，即只知道被攻陷设备上的数据与模型）。构造攻击时还需要知道当前轮从主设备收到的全局模型 w_Re（Section 3.2）。
- **目标**：无目标投毒（untargeted poisoning），让学到的全局模型对测试样本整体错误率（error rate）显著升高，使模型不可用并最终导致拒绝服务（denial-of-service）；论文明确不研究定向投毒（Section 2.3、Section 6、Section 7）。
- **防御者是谁、能看到什么、信任什么**：防御者是主设备。它能看到每一轮所有客户端上传的明文本地模型，并按事先设定的聚合规则聚合；论文的整个设定里没有安全聚合（secure aggregation）、差分隐私（differential privacy）或加密上传，也就是服务器能看到每个客户端的原始更新。防御方法额外假设主设备持有一个小的验证数据集，并且知道被攻陷设备数的上界 c（Section 5）。论文还假设服务提供者知道真实的 c 并据此设置聚合规则的参数，用来给出攻击威胁的下界（Section 2.3）。

## 3. 攻击入口与流程位置

论文在 Figure 1 中区分数据投毒攻击与本地模型投毒攻击：前者进入"训练数据收集"，后者进入"学习过程"。

联邦学习每轮的三步是（Section 2.1）：主设备把当前全局模型下发给客户端；客户端用本地数据集更新本地模型并把本地模型上传给主设备；主设备按聚合规则聚合得到新的全局模型。

攻击进入的位置是第二步的出口，也就是**更新上传之前**：被攻陷客户端直接把自己要上传的本地模型参数替换为通过求解优化问题构造出来的伪造本地模型。论文的表述是攻击者"manipulates the local model parameters sent from these devices to the master device during the learning process"。就本库的分类而言，这对应"更新上传前的后处理（update postprocess）"这一钩子，而不是"本地数据准备"；论文把它统称为破坏"学习过程"的完整性。

具体操作步骤（已知聚合规则时）：

1. 每轮被攻陷客户端收到全局模型 w_Re，并计算出（或本来就持有）它原本要上传的本地模型 w_i。
2. 攻击者确定无攻击时全局模型每个参数的变化方向 s，其中 s_j = 1 或 −1。全知识场景由良性本地模型直接算出；部分知识场景用被攻陷设备的本地模型均值与收到的全局模型逐参数比较来估计方向（Section 3.2）。
3. 对 Krum：令伪造模型 w'_1 = w_Re − λs，用二分搜索找到最大的 λ 使 Krum 选中 w'_1；其余 c−1 个被攻陷模型在距离 w'_1 不超过 ε 的范围内随机采样（Section 3.2，Equation 2）。
4. 对 trimmed mean 与 median：逐参数构造。若 s_j = −1，就在良性参数最大值 wmax,j 之上取值；若 s_j = 1，就在良性参数最小值 wmin,j 之下取值。全知识场景在 [wmax,j, b·wmax,j] 一类区间随机采样（b = 2）；部分知识场景用被攻陷设备的参数均值 µ_j 与标准差 σ_j，在 [µ_j + 3σ_j, µ_j + 4σ_j] 或 [µ_j − 4σ_j, µ_j − 3σ_j] 区间采样（Section 3.3、Section 3.4）。
5. 这些伪造本地模型在第三步服务器聚合时把全局模型推离原本的变化方向，多轮累积后形成显著偏移。

论文没有涉及本地数据准备、损失函数或优化器层面的篡改，也没有涉及全局模型下发、评估或部署阶段的攻击。

## 4. 方法原理

核心思想：不注入恶意数据，而是在每轮迭代中直接构造被攻陷客户端上传的本地模型，让聚合后的全局模型尽量朝着"无攻击时全局模型变化方向的反方向"偏移，论文称之为 directed deviation goal（Section 3.1）。

优化问题（Equation 1）为：最大化 s^T (w − w')，约束是 w = A(w_1,…,w_c,w_{c+1},…,w_m)（无攻击时的聚合结果）与 w' = A(w'_1,…,w'_c,w_{c+1},…,w_m)（有攻击时的聚合结果），其中 s 是全局模型各参数变化方向的列向量，w 是无攻击时的全局模型，w' 是攻击后的全局模型。论文还另设了一个不考虑方向的 deviation goal（附录 B，Equation 5），并报告 directed deviation goal 对 trimmed mean 与 median 明显更好（附录 Table 8：trimmed mean 0.10 对 0.52，median 0.12 对 0.29），对 Krum 二者都高（0.87 对 0.80）。

对 Krum（Section 3.2）：因为 Krum 每轮只选一个本地模型作为全局模型，目标是让 Krum 选中被构造的 w'_1。论文做两个近似：一是 w'_1 = w_Re − λs，直接对"相对于收到的全局模型的定向偏移"建模；二是把其余 c−1 个被攻陷模型取成接近 w'_1（先假设与 w'_1 相同以求解，再在 ε 范围内随机采样 c−1 个向量），这样 w'_1 只需要靠近 m−2c−1 个良性本地模型就能被 Krum 选中。由此得到 Equation 2：最大化 λ，约束为 w'_1 = Krum(w'_1,…,w'_c,w_{c+1},…,w_m)、w'_1 = w_Re − λs、w'_i = w'_1。Theorem 1（Equation 3）给出 λ 的上界，且该上界只依赖攻击前的本地模型；随后用二分搜索求解 λ，阈值为 1×10⁻⁵。

对 trimmed mean（Section 3.3）：论文声称可证明的最优做法是逐参数把 c 个被攻陷客户端的该参数放到良性最大/最小值之外（由 s_j 决定放在哪一侧）；实现时在边界附近的区间内随机采样，以免成为明显离群点。论文还给出高斯假设下的概率估计：当 m = 100、c = 20 时，采样落在 [µ+3σ, µ+4σ] 内使得伪造参数高于良性最大值的概率为 0.898–0.998。

对 median（Section 3.4）：直接沿用 trimmed mean 的攻击。

对 Bulyan（附录 A）：因为 Bulyan 建立在 Krum 之上，针对 Krum 的攻击可以迁移到 Bulyan。

防御方法（Section 5）：把面向数据投毒的 RONI 与 TRIM 泛化为 ERR（Error Rate based Rejection）与 LFR（Loss Function based Rejection）。每轮在聚合前，对每个本地模型分别计算"包含它"与"排除它"两种聚合结果 A 与 B，在验证集上分别算错误率 E_A、E_B（ERR）或交叉熵损失 L_A、L_B（LFR），把差值 E_A − E_B（或 L_A − L_B）定义为该本地模型的"影响"；剔除影响最大的 c 个本地模型，再用原来的拜占庭鲁棒聚合规则聚合剩下的。Union 版本剔除被 ERR 或 LFR 任意一个剔除的本地模型。

## 5. 检测或防御所需的数据

**防御方法（ERR / LFR）需要的输入：**

1. **每个客户端本轮上传的本地模型（完整参数向量）**
   - 是什么：良性客户端的真实本地模型与被攻陷客户端伪造的本地模型。
   - 在哪里采集：服务器收到更新时（server receive）。
   - 粒度：逐客户端；内部按参数/层处理。
   - 是否需要跨轮历史：ERR/LFR 本身不需要；但要判别本论文攻击的痕迹（c 个伪造模型互相极为接近、逐参数被推到良性极值之外）需要同一轮内跨客户端比较。
   - 是否需要干净参考数据：不需要。
   - 是否需要额外前向或反向计算：不需要（聚合本身不算训练计算）。

2. **本轮开始时的全局模型 w_Re，以及"无攻击时本轮会得到的全局模型" w**
   - 是什么：上一轮聚合结果下发给客户端的全局模型；以及假想无攻击时的聚合结果。
   - 在哪里采集：服务器聚合时（server aggregate）。
   - 粒度：逐参数、逐轮。
   - 是否需要跨轮历史：需要。变化方向 s_j 由相邻轮全局模型参数的增减决定（Section 3.1）。
   - 是否需要干净参考数据：不需要。
   - 额外计算：需要一次对照聚合（得到 w），在真实部署中要求服务器能在一次汇聚里多跑一次聚合或保存被攻陷上报之前的中间状态。

3. **客户端更新之间的距离类中间量：成对欧氏距离、最近邻集合、Krum/Bulyan 的选中结果**
   - 是什么：Krum 的成对欧氏距离（Euclidean distance）与平方距离和，Bulyan 中 θ 个被 Krum 选中的模型与 γ 个参与取均值的参数。
   - 在哪里采集：服务器聚合时（server aggregate）。
   - 粒度：逐客户端、逐轮，距离是模型级别。
   - 是否需要跨轮历史：不需要。
   - 是否需要其他客户端的数据：需要，距离本质上是跨客户端比较。
   - 额外计算：需要；论文自己说 Bulyan 不可扩展，因为它每轮多次运行 Krum，而 Krum 要计算本地模型之间的两两距离（Section 2.2）。

4. **服务器端验证数据集（validation dataset）**
   - 是什么：主设备持有的小规模带标签验证集，用于算错误率和交叉熵损失。实验中是"从 MNIST 测试集里均匀随机抽 100 个样例"（Section 5）。
   - 在哪里采集：评估时（evaluation），但在每轮聚合之前使用。
   - 粒度：逐样本。
   - 是否需要干净参考数据：需要，且隐含要求与测试分布同分布；论文没有讨论验证集本身被投毒或分布偏移的情况。
   - 额外计算：每个候选模型都要在验证集上做一次前向。

5. **每个本地模型的留一法聚合结果 A 与 B 及其验证指标 E_A、E_B 或 L_A、L_B**
   - 是什么：ERR/LFR 的核心统计量，即包含/排除某个本地模型时聚合出的全局模型及其在验证集上的表现，差值是"影响"。
   - 在哪里采集：服务器聚合时（server aggregate）与评估时（evaluation）共同产生。
   - 粒度：逐客户端（每个本地模型一组 A、B）；统计量是模型级别。
   - 是否需要跨轮历史：不需要。
   - 是否需要干净参考数据：需要（验证集）。
   - 是否需要其他客户端的数据：需要，"排除某个客户端"的聚合需要其余客户端的更新。
   - 额外计算：需要。论文描述了流程但没有量化开销。

6. **聚合规则的配置与恶意客户端数上界 c**
   - 是什么：Krum/Bulyan/trimmed mean/median 的选择及 β、θ、γ 等参数；ERR/LFR 要知道 c。
   - 采集位置：服务器聚合时（server aggregate），属于配置而非测量。
   - 粒度：逐轮/全局。论文明确写防御方法假设主设备知道被攻陷设备数的上界 c（Section 5）。

**攻击论文部分——攻击留下的可观测痕迹与论文声称能绕过的检测：**

- 被攻陷客户端的本地模型与无攻击时应有的变化方向 s 反号，即与全局模型的移动方向相反（Section 3.1）。
- 对 Krum 的攻击让 c 个被攻陷模型彼此非常接近（距离不超过 ε，默认 ε = 0.01）。论文自己承认若 ε = 0 会让这 c 个模型完全相同、"making the compromised local models easily detected by the master device"，所以才不取 0（Section 4.1）。也就是说，紧密聚簇是论文承认的可检测痕迹。
- 对 trimmed mean/median 的攻击把逐参数取值推到良性参数最大/最小值之外，论文明确说推得太远会"be outliers and the master device may detect the compromised local models easily"，因此只在边界外的 3σ–4σ 或 [wmax, 2wmax] 区间内取样（Section 3.3）。
- 论文声称能绕过的检测只有这类直觉性的离群点检测，且只是通过控制采样区间来规避；论文没有报告与任何具体检测器的对抗实验。论文还指出，在攻击下训练错误率仍会正常下降到收敛，所以"训练错误率异常上升就回滚"这一策略不可用（Section 4.2）。

## 6. 干预动作

论文的防御动作是**剔除客户端**：ERR 或 LFR 各自剔除"影响"最大的 c 个本地模型，Union 剔除被两者任一选中的本地模型，然后用原来的拜占庭鲁棒聚合规则聚合剩下的本地模型（Section 5）。动作发生在服务器端、每轮聚合之前，属于聚合前的过滤。

论文没有做重新加权、裁剪、加噪、样本过滤、模型修复或回滚。论文讨论过"若主设备检测到训练错误率异常上升就回滚到若干轮之前"这一策略，但结论是它不适用，因为在本论文攻击下全局模型的训练错误率依然持续下降直到收敛（Section 4.2）。

## 7. 实验设置与主要结果

- **模型与数据**：LR 与 DNN（MNIST/Fashion-MNIST/Breast Cancer 用 Table 7a 架构，CH-MNIST 用 ResNet20）（Section 4.1）。
- **联邦学习设置**：默认 m = 100、c = 20（20%）、非独立同分布程度 p = 0.5、Krum 攻击的 ε = 0.01、trimmed mean 的 β = c（Table 1）。默认每个客户端每轮做 1 轮随机梯度下降，主设备聚合全部客户端；LR 在 MNIST 上 500 轮，DNN 2000 轮；批大小 32（Fashion-MNIST 为 64）。每个实验重复 50 次取平均，论文称方差很小因而省略（Section 4.1）。
- **对比攻击**：Gaussian attack、label flipping attack、back-gradient optimization based attack（BGA），以及本论文的全知识与部分知识攻击（Section 4.1）。
- **指标**：测试错误率。

关键结果：

- Table 2：MNIST + LR + Krum 下，无攻击 0.14、Gaussian 0.13、LabelFlip 0.13、部分知识 0.72、全知识 0.80；同样设置下 trimmed mean 从 0.12 升到 0.23（部分）/0.52（全知识），median 从 0.13 升到 0.19（部分）/0.29（全知识）。Section 4.2 正文用"从 0.14 升到 0.72，约 400% 相对增长"描述第一行。DNN + MNIST + Krum：0.11 升到 0.75/0.77（Table 2b）；Fashion-MNIST + DNN + Krum：0.16 升到 0.90/0.91（Table 2c）；CH-MNIST + DNN + Krum：0.29 升到 0.73/0.81（Table 2d）；Breast Cancer + DNN + Krum：0.03 升到 0.17/0.17（Table 2e）。
- Figure 2（MNIST，被攻陷设备比例 0–25%）：本论文攻击随比例上升显著推高错误率；label flipping 只略微提高；Gaussian 基本没有影响（两个例外是 Krum 在 5%→10% 与 10%→15% 时错误率反而下降）。
- Figure 3（非独立同分布程度 0.1–1.0）：包括无攻击在内，所有情形的错误率都随非独立同分布程度上升而上升，只有对 Krum 的攻击呈波动。
- Figure 4：(a) 客户端每轮随机梯度下降轮数从 1 增到 10 时，攻击与无攻击的错误率都下降，但论文说即使用 10 轮攻击仍能把错误率提高 30% 以上；(b) 客户端数从 50 增到 400（20% 被攻陷）时攻击更有效，正文举例说 trimmed mean + DNN + MNIST 下部分知识攻击对 50 个客户端平均能正确估计 72% 的全局参数变化方向，100 个客户端时提高到 76%；(c) 每轮被选中的客户端数为 20 到 100 时，正文指出攻击在 c/m 大于 10%–15% 时开始有效。
- Figure 5：(a) trimmed mean 的 β 从 20 增到 45 时攻击效果下降（更多恶意参数被裁剪），但无攻击的错误率也略升；(b) Krum 攻击在 ε 从 0.01 到 100 的很大范围内都有效，且 ε 越小攻击越强；(c) 只投毒一部分轮次时，投毒轮次比例越高错误率越大。
- Table 3（备选训练策略：按测试错误率挑选最好的全局模型；DNN + MNIST）：Krum 0.10 升到 0.69（部分知识）/0.70（全知识），trimmed mean 0.06 升到 0.12/0.18，median 0.06 升到 0.11/0.32；正文说部分知识攻击仍分别把错误率提高了 590%、100%、83%。
- Table 4（聚合规则未知时的迁移性；MNIST + LR；部分知识）：基于 Krum 的攻击能迁移到 trimmed mean（0.12 升到 0.15，25%）与 median（0.13 升到 0.18，38%）；基于 trimmed mean 的攻击不能迁移到 Krum（仍为 0.14），但能迁移到 median（0.13 升到 0.20，54%）。
- Table 5（与 BGA 对比；6000 个 MNIST 样例、10 类 LR、100 个客户端、20 个被攻陷）：BGA 在集中式学习里把错误率从 0.10 提到 0.16（60% 相对增长），但它在一张 GTX 1080Ti 上跑了 10 天只生成 240 个毒样本（占 4%），且在拜占庭鲁棒聚合下效果有限（Krum 下 SingleWorker 0.24、Uniform 0.25）；本论文攻击在同样设置下 Krum 达到 0.85（部分）/0.89（全知识）。
- Table 6（防御结果；MNIST + LR；部分知识攻击）：LFR 与 Union 在 trimmed mean 与 median 上能把错误率压回无攻击水平（例如 trimmed mean + LFR 在攻击 trimmed mean 时为 0.12，与无攻击的 0.12 相同），但对基于 Krum 的攻击无效：Krum + LFR 下错误率仍从 0.14 升到 0.58（314% 相对增长），Krum + Union 下升到 0.48。正文还说防御有时会误删良性本地模型，导致错误率反而升高。
- Table 7b（Bulyan；MNIST + LR；m = 100、c = 20、θ = m−2c、γ = θ−2c）：无攻击 0.14，部分知识攻击 0.36（约 +150%），全知识攻击 0.38（+165%）。
- 正文另给出集中式与联邦式的对比：四个数据集上 DNN 在集中式学习下的测试错误率分别是 0.01、0.08、0.07、0.01，而联邦学习用均值聚合时分别是 0.04、0.09、0.09、0.01（Section 4.2）。

## 8. 开销

论文没有报告 ERR 与 LFR 的计算、通信或存储开销，也没有量化攻击构造本身的开销，因此就方法本身而言是"论文未报告"。论文中出现的相关定量陈述只有：BGA 攻击在一张 GTX 1080Ti 上运行 10 天才生成 240 个毒样本（Section 4.4）；Bulyan 不可扩展，因为它每轮多次运行 Krum，而 Krum 计算本地模型之间的两两距离（Section 2.2）；客户端执行的随机梯度下降轮数越多，计算开销越大，论文称这对手机和 IoT 这类资源受限设备可能不可接受（Section 4.2）。分析：ERR/LFR 每轮要对 m 个本地模型各做一次"排除它"的聚合和验证集评估，因此每轮至少额外增加 m 次聚合与 m 次验证集前向，这部分开销论文没有量化。

## 9. 假设、局限与自适应攻击

**论文成立所依赖的假设：**

1. 被攻陷设备数 c 严格小于 50%（Section 2.3）。
2. Krum、trimmed mean 这类聚合规则需要知道 c 的上界；论文假设服务提供者知道真实的 c 并据此设置参数，以给出攻击威胁的下界（Section 2.3）。
3. 攻击者知道聚合规则（不知道时按某一规则构造并依赖迁移性）（Section 2.3、Section 4.3）。
4. 全知识场景假设攻击者知道所有客户端的本地数据与本地模型；论文自己说这在联邦学习里适用性有限，只用来估计上界（Section 2.3）。
5. 部分知识场景用被攻陷客户端各参数的均值 µ_j 与标准差 σ_j，并假设良性客户端的对应参数服从高斯分布，从而估计良性参数的最大值/最小值；论文承认良性参数不一定真的服从高斯分布，但称攻击经验上仍有效（Section 3.3）。
6. 论文在介绍 trimmed mean 的理论性质时假设各客户端训练样本数相同（原文写明 n 是每个客户端的训练样本数，且各 worker device 被假设拥有相同数量的训练数据点）（Section 2.2）。
7. 防御假设主设备持有一个小的、分布正确的验证集（实验里是 100 个随机测试样本），并知道 c（Section 5）。
8. 主设备能看到每个客户端上传的明文本地模型（全文聚合设定与防御流程都建立在此之上）。

**论文自述的局限（Section 7）**：只研究无目标投毒，定向投毒留作未来工作；需要新的防御方法，包括检测被攻陷本地模型的新方法和新的对抗鲁棒聚合规则。

**是否评估自适应攻击者**：没有。Section 4.3 的"未知聚合规则"实验只是让攻击者按另一种聚合规则构造、再测迁移性，属于迁移性评估而不是针对防御的自适应攻击；论文也没有针对 ERR/LFR 调整攻击构造策略。因此评估过自适应攻击者 = 否。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）：**

- 分析：论文聚合的对象是完整的模型参数向量，Krum 的 Theorem 1 上界里还显式出现 1/√d（d 是全局模型参数个数）；联邦 LoRA 微调聚合的是低秩适配器增量，d 小几个数量级，而且适配器以低秩乘积形式存在，逐元素的 trimmed mean/median 与欧氏距离在低秩结构上的语义与全参数模型不同，论文未说明。
- 分析：论文假设"发送本地模型等价于发送梯度"（Section 2.1 末尾），这在全参数模型上使各聚合规则等价；LoRA 微调中各客户端可能只训练不同模块、使用不同秩或不同目标模块，服务器可能聚合增量后再合并，这一等价性未必成立，论文未说明。
- 分析：directed deviation goal 需要"无攻击时全局模型每个参数的变化方向 s"，在 LoRA 中这意味着逐轮比较适配器参数；如果服务器只下发合并后的基座模型或只回传适配器增量，方向的定义与可观测性都会改变，论文未说明。
- 分析：论文实验里每轮客户端只做 1 轮随机梯度下降，而大模型 LoRA 微调通常每轮做很多步、多个 epoch；论文自己报告客户端本地步数越多攻击越弱（Figure 4a），因此直接迁移会高估攻击强度。
- 分析：论文的规模是 100 个客户端、20% 被攻陷，并且攻击在恶意比例超过 10%–15% 时才明显有效（Section 4.2 对 Figure 4c 的讨论）；真实联邦 LoRA 常常客户端更少、每轮部分参与，恶意客户端的实际聚合占比更不稳定。
- 分析：ERR/LFR 需要服务器持有与训练分布同分布的验证集，并且每轮对每个客户端做留一法聚合与验证集前向；在 LoRA 场景下验证集是文本、指标是交叉熵或任务错误率，这两个动作的代价远高于论文里的小分类器，论文未报告相关开销。
- 分析：论文只处理无目标破坏，而联邦 LoRA 更现实的威胁是后门或安全对齐破坏（定向投毒），论文完全未涉及；把适配器发布者或基座模型发布者当作攻击者的供应链威胁也不在论文威胁模型内。
- 分析：论文假设服务器拿到每个客户端的明文完整更新，没有考虑安全聚合、差分隐私噪声、梯度压缩或低秩投影；这些机制会改变论文检测所依赖的信号（成对距离、逐参数极值、留一法影响）。
- 分析：论文假设被攻陷客户端可以任意设置上传参数；若真实部署在上传前有范数裁剪或异常值过滤，这种"任意取值"能力会被削弱，而论文没有在这类防御下评估。

## 10. 对防护库设计的含义

（以下全部是分析：）

1. 库需要在服务器收到更新时保存每个客户端的原始上传向量（逐参数、逐轮、逐客户端），并保留至少上一轮的全局模型，因为这篇论文的攻与防都建立在"逐参数变化方向"和"客户端更新之间的欧氏距离"之上；这是通用需求，不限于本文。
2. 库需要提供跨客户端横向比较的数据视图：成对距离矩阵、每个客户端的最近邻集合、逐参数的极值与分位数。这是 Krum/Bulyan/trimmed mean/median 以及本文防御的公共基础，属于通用能力；但"逐参数极值区间外 3σ–4σ"这类具体信号是本文特有的。
3. 库的聚合器必须可重入：ERR/LFR 要对每个客户端各跑一次"排除它"的聚合，服务器钩子必须能以任意客户端子集重新执行聚合规则并取回结果。这相对通用聚合接口是一个强要求（常见实现只允许一轮聚合一次）。
4. 库需要服务器侧验证集句柄与"验证集评估"钩子，能对任意候选全局模型计算错误率和交叉熵损失；这也是需要显式建模的采集点，而非附带功能。
5. 库需要"聚合前剔除客户端"的干预接口，并允许插件之间交换每轮的剔除集合（Union 规则需要同时拿到 ERR 与 LFR 的名单再取并集），同时把剔除决定记录成报告。
6. 库需要显式建模服务器已知的恶意客户端数上界 c 与聚合规则配置（Krum 的 c、trimmed mean 的 β、Bulyan 的 θ 与 γ），因为本文的攻防都以它们为输入；这是通用需求，但"c 被准确已知"这一前提是本文特有的强假设。

## 11. 原文依据

1. **Abstract** — 支撑第 2 节（攻击者能力与目标）：
   > "We assume an attacker has compromised some client devices, and the attacker manipulates the local model parameters on the compromised client devices during the learning process such that the global model has a large testing error rate."

2. **Section 1（Threat model 段）** — 支撑第 3 节（攻击入口是"学习过程"而非数据收集）：
   > "Unlike existing data poisoning attacks that compromise the integrity of training dataset collection, we aim to compromise the integrity of the learning process in the training phase (see Figure 1)."

3. **Section 2.3** — 支撑第 2 节（攻击者占比上界）：
   > "We assume the number of worker devices under the attacker's control is less than 50% (otherwise, it would be easy to manipulate the global models)."

4. **Section 1（Local model poisoning attacks 段）** — 支撑第 2 节目标与第 4 节 directed deviation：
   > "Our goal is to craft the local models on the compromised worker devices such that the global model deviates the most towards the inverse of the direction along which the before-attack global model would change."

5. **Section 3.1** — 支撑第 4 节（directed deviation goal 的定义）：
   > "We consider the attacker's goal (we call it directed deviation goal) is to deviate a global model parameter the most towards the inverse of the direction along which the global model parameter would change without attacks."

6. **Section 3.3** — 支撑第 5 节（攻击留下"离群"痕迹以及论文如何规避）：
   > "However, if we craft the compromised local models based on wmax,j or wmin,j that are far away from their true values, the crafted local models may be outliers and the master device may detect the compromised local models easily."

7. **Section 4.1** — 支撑第 5 节（Krum 攻击造成的紧密聚簇是可检测痕迹）：
   > "We do not set ε = 0 because ε = 0 makes the c compromised local models exactly the same, making the compromised local models easily detected by the master device."

8. **Section 5** — 支撑第 2 节与第 9 节（防御者所需数据与假设）：
   > "In both defenses, we assume the master device has a small validation dataset. Like existing aggregation rules such as Krum and trimmed mean, we assume the master device knows the upper bound c of the number of compromised worker devices."

9. **Section 5（ERR 段）** — 支撑第 4 节与第 6 节（防御统计量与剔除动作）：
   > "In this defense, we compute the impact of each local model on the error rate for the validation dataset and remove the local models that have large negative impact on the error rate."

10. **Section 4.2** — 支撑第 7 节（Table 2a 的关键结果）：
    > "For instance, when dataset is MNIST, classiﬁer is LR, and aggregation rule is Krum, our partial knowledge attack increases the error rate from 0.14 to 0.72 (around 400% relative increase)."

```json
{
  "key": "fang2020local",
  "title": "Local Model Poisoning Attacks to Byzantine-Robust Federated Learning",
  "year": 2020,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["update_postprocess", "local_training"],
  "observables": [
    {"what": "每个客户端本轮上传的完整本地模型参数向量（含被攻陷客户端的伪造模型）", "where": "server_receive", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "本轮开始时下发的全局模型以及无攻击假设下的聚合结果（用于计算逐参数变化方向 s 与 before-attack 全局模型 w）", "where": "server_aggregate", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "客户端更新之间的成对欧氏距离、最近邻集合与 Krum/Bulyan 的选中结果", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "服务器端小规模带标签验证数据集（实验中为随机抽取的 100 个 MNIST 测试样本）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "每个本地模型的留一法聚合结果 A 与 B 及其在验证集上的错误率或交叉熵损失", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "上传更新逐参数的极值、分位数与离群程度（用于发现被推到良性极值之外的伪造参数）", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "被攻陷客户端上传模型相对收到全局模型的偏移方向与彼此间的聚簇紧密程度（Krum 攻击的 ε 痕迹）", "where": "server_receive", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["exclude_client"],
  "intervention_where": ["server"],
  "assumptions": [
    "被攻陷客户端数严格少于 50%，且服务器知道其上界 c",
    "攻击者知道聚合规则，或按某一假定的聚合规则构造并依赖迁移性",
    "全知识场景下攻击者知道所有客户端的本地数据与本地模型",
    "部分知识场景下用被攻陷客户端参数的均值与标准差近似良性参数分布（高斯假设）",
    "服务器持有与测试分布同分布的小规模验证集",
    "服务器按 Krum/Bulyan/trimmed mean/median 之一逐轮聚合明文完整本地模型",
    "各客户端训练样本数相同",
    "论文未评估自适应攻击者"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 2 节：攻击者是被攻陷客户端，能力是操纵上传的本地模型参数，目标是无目标破坏错误率", "text": "We assume an attacker has compromised some client devices, and the attacker manipulates the local model parameters on the compromised client devices during the learning process such that the global model has a large testing error rate."},
    {"section": "Section 1 (Threat model)", "supports": "第 3 节：攻击入口是学习过程而非训练数据收集", "text": "Unlike existing data poisoning attacks that compromise the integrity of training dataset collection, we aim to compromise the integrity of the learning process in the training phase (see Figure 1)."},
    {"section": "Section 2.3", "supports": "第 2 节与第 9 节：攻击者控制的客户端数上界", "text": "We assume the number of worker devices under the attacker's control is less than 50% (otherwise, it would be easy to manipulate the global models)."},
    {"section": "Section 1 (Local model poisoning attacks)", "supports": "第 2 节目标与第 4 节 directed deviation goal", "text": "Our goal is to craft the local models on the compromised worker devices such that the global model deviates the most towards the inverse of the direction along which the before-attack global model would change."},
    {"section": "Section 3.1", "supports": "第 4 节：directed deviation goal 的形式化定义", "text": "We consider the attacker's goal (we call it directed deviation goal) is to deviate a global model parameter the most towards the inverse of the direction along which the global model parameter would change without attacks."},
    {"section": "Section 3.3", "supports": "第 5 节：伪造参数会被当作离群点检测，论文据此限制采样区间", "text": "However, if we craft the compromised local models based on wmax,j or wmin,j that are far away from their true values, the crafted local models may be outliers and the master device may detect the compromised local models easily."},
    {"section": "Section 4.1", "supports": "第 5 节：Krum 攻击让伪造模型紧密聚簇，论文承认这本身易被检测", "text": "We do not set ε = 0 because ε = 0 makes the c compromised local models exactly the same, making the compromised local models easily detected by the master device."},
    {"section": "Section 5", "supports": "第 2 节与第 9 节：防御者需要验证集并知道 c 的上界", "text": "In both defenses, we assume the master device has a small validation dataset. Like existing aggregation rules such as Krum and trimmed mean, we assume the master device knows the upper bound c of the number of compromised worker devices."},
    {"section": "Section 5 (ERR)", "supports": "第 4 节与第 6 节：ERR 的统计量与剔除动作发生在服务器聚合前", "text": "In this defense, we compute the impact of each local model on the error rate for the validation dataset and remove the local models that have large negative impact on the error rate."},
    {"section": "Section 4.2", "supports": "第 7 节：Table 2a 中 MNIST+LR+Krum 的关键结果", "text": "For instance, when dataset is MNIST, classiﬁer is LR, and aggregation rule is Krum, our partial knowledge attack increases the error rate from 0.14 to 0.72 (around 400% relative increase)."}
  ]
}
```
