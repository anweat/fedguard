# sun2024thesis：生成式模型在联邦学习安全中的应用研究

> 说明：本论文正文为中文，仅英文摘要、图表英文标题为英文（引文见第 11 节）。以下所有"分析："前缀内容均为我的推断，其余为该学位论文的陈述。

## 1. 基本信息

- 场景：传统联邦学习（Federated Learning, FL），任务是图像分类；论文全文没有出现大语言模型、LoRA、参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）或适配器供应链的内容，也不是集中式大模型训练。依据：摘要、3.4.1、4.4、5.4、6.4。
- 训练阶段：攻击发生在"本地数据准备"（联邦训练开始前生成中毒数据，随后在每轮本地训练中生效）；防御分别发生在"客户端主任务训练入口"和"服务器收到本地模型后、联邦聚合前"。依据：3.3.4、5.3.2、6.2、6.3。
- 论文类型：攻防混合的硕士学位论文，包含两个攻击（第 3 章 VagueGAN、第 5 章 LSDAM）与两个防御/检测工作（第 4 章 MCD、第 6 章 C-S 架构与 CAEKL）。
- 模型与数据规模：主任务为卷积神经网络（CNN）图像分类。MNIST 与 Fashion-MNIST 用"两个卷积层 + 批量归一化"的 CNN；CIFAR-10 用"六个卷积层 + 批量归一化 + 两个全连接层"的 CNN（3.4.1）。数据集见表 3-4：MNIST (28,28,1)、10 类、60000 训练/10000 测试；Fashion-MNIST 同；CIFAR-10 (32,32,3)、10 类、50000 训练/10000 测试。FL 默认 N=60 客户端、每轮随机选 K=10、T=200 轮（3.4.1）；第 4–6 章实验改为 N=20、K=5、T=200（4.4）。VagueGAN 的生成器与判别器都是多层感知机（MLP），结构见表 3-2、表 3-3（生成器输入 100+10 维噪声与标签，输出 784=28×28）；LSDAM 用轻量化 U-net，参数约 7.75M（5.3.1）。

## 2. 威胁模型

- 攻击者是谁：恶意客户端（malicious client）。论文假设"至少存在一个数据中毒攻击者"，攻击者"可以控制一个或多个良性客户端，或将自己伪装成良性客户端参与联邦训练"（3.2.2）。
- 占比或数量：第 3 章实验把恶意客户端比例 α 从 5% 扫到 30%（表 3-5 至表 3-7）；论文另引已有工作称"即使是很少的恶意客户端比例（例如 2%）也会对全局模型造成恶意影响"（3.3.1，引用文献[10]）。第 4–6 章固定 α=20%，即 N=20 中 M=4（4.4、5.4、6.4）。
- 能力（能改什么）：攻击者获得受控客户端的"所有权限，如本地数据集、本地模型训练过程"，可以毒化并替换本地数据集，并用中毒数据训练本地模型后上传（3.2.2、3.3.4）。论文明确限制其行动范围"仅限于每个受控客户端"：服务器完全诚实且不可攻击；通信链路可靠，攻击者无法影响链路上的模型上传与交换；不能访问服务器与未受控客户端的数据集，也不能访问良性客户端的合法模型（3.2.2）。论文未说明攻击者能修改上传更新的缩放/投影、聚合算法或全局模型下发。
- 知识（知道什么）：受控客户端掌握的信息，包括"联邦学习主任务架构、全局模型、联邦学习训练轮次"（3.2.2）。
- 目标：降低全局模型性能（无目标破坏，表现为测试精度下降），以及"隐藏自己的攻击，不被服务器检测到"（3.2.2）。论文不涉及定向后门、越狱或安全对齐破坏、隐私窃取。
- 防御者是谁、能看到什么、信任什么：防御者是中央服务器（第 6 章另有客户端本地审查器）。服务器能看到每轮被随机选中的 K 个客户端上传的本地模型，以及自己维护的测试集 D_test（用于计算每轮全局准确率 a_t，3.2.1；第 6 章还用它训练 CAE-Detecter）。服务器看不到客户端本地数据。服务器信任的首先是自身——MCD 假设"服务器也作为 FL 训练过程中的一个客户端并训练一个局部模型"，该客户端"被认为是 100% 安全且不受攻击的"（4.3）；其次是一个"暂时标记为良性"的受信任客户端集合 C_tr，初始化为全体客户端，检测到恶意后逐个删除（4.3）。

## 3. 攻击入口与流程位置

攻击入口是**本地数据准备**（local data preparation）：恶意客户端在联邦训练开始前用生成式模型合成中毒数据并替换自己的本地数据集，之后的本地训练、上传、聚合、下发、评估全部按正常 FL 流程进行，不修改损失函数、优化器、训练步数，也不触碰更新上传前的后处理、服务器聚合与全局下发。

- VagueGAN（3.3.4、算法 3-1）：(1) 攻击者取得客户端 c_j 的控制权并在其上部署 VagueGAN，同时正常接收服务器下发的 FL 训练任务；(2) 以整个本地数据集 D^train_j 为批次，按公式(3-1)训练 VagueGAN 共 E 次；(3) 生成中毒数据集 D^poison_j；论文明确"它会生成与真实数据相同数量的中毒数据，并用中毒数据替换所有真实数据"（3.4.2）；(4) 在每轮 t 接收全局模型 θ̃_t，在 D^poison_j 上训练局部模型，得到中毒局部模型 θ^poison_{t+1,j} 并上传；(5) 在 T 轮内重复 (4)。
- LSDAM（5.3.2、5.3.3、算法 5-1）：中毒数据生成分两步——"大步 DDPM 训练和中毒数据生成（时间点：联邦训练开始前）"；恶意客户端先在本地数据集 D_j 上训练大步 DDPM，再用逆扩散（推理）过程生成中毒数据 x^p_j；此后"中毒模型训练和中毒模型上传流程依旧遵循 3.2 小节中威胁模型中的攻击的流程"，论文称其"与 VagueGAN 相似"（5.3.3）。论文未明确说明 LSDAM 是否与 VagueGAN 一样以等量数据完全替换真实数据。
- 对防御方而言的攻击入口：MCD 与 KL-Detecter 针对的入口是"服务器收到本地模型时→联邦聚合前"（4.3、6.3.2）；CAE-Detecter 针对的入口是"客户端主任务训练入口的本地数据"（6.2、6.3.1）。

## 4. 方法原理

### 4.1 VagueGAN（3.3.2–3.3.6）

核心思想：不是用 GAN 生成以假乱真的数据，而是"反向利用生成式对抗网络的强大生成能力，生成带有适量有毒噪声的'模糊数据'"，在攻击性与隐蔽性之间做权衡；模糊数据"可以在很大程度上保持其 GAN 输入的统计特征"，使中毒局部模型看起来合法（3.3.2）。

模型设计（3.3.2）：在条件 GAN（CGAN）基础上做了三处改动——判别器更深，以更好保留合法特征；采用 Batch Normalization 与 LeakyReLU；采用大批量全数据集训练。生成器也更深，以增加生成不确定性、让中毒数据更模糊。损失函数引入抑制因子 κ：

min_G max_D V(G,D) = E_{x∼p_d(x)}[log(1+κ)D(x)] + E_{z∼p_z(z)}[log(1−(1+κ)D(G(z)))]（公式 3-1），其中 κ∈(0,1)。

训练（3.3.3）：先用梯度上升多次优化判别器（公式 3-2），再用较低学习率以梯度下降优化生成器（公式 3-3）；最终状态是"鉴别器的最终分类准确率稳定在 0.5 左右"。

理论（3.3.5）：最优判别器 D*(x) = p_d(x) / [(1+κ)(p_d(x)+p_g(x))]（公式 3-8）；当 D*(x)=0.5 时 p_g(x) = [(1−κ)/(1+κ)]·p_d(x)（公式 3-9），即中毒数据分布与真实分布相关但不相同；κ=0 时 VagueGAN 等同于普通 GAN。

攻击性与隐蔽性的量化（3.3.6）：有效性 A_t = a_t − a^p_t（公式 3-10）；隐蔽性 S_t = 1/E(u_t,u^p_t) = 1/||u_t−u^p_t||（公式 3-14），其中 u_t、u^p_t 是 PCA 降到 2 维后（公式 3-11）合法模型簇与中毒模型簇的中心（公式 3-12、3-13）。指导性结论：E∈[400,600]、κ=0.2 可生成质量均衡的中毒数据（3.3.6、图 3-7）；κ 从 0.1 增到 0.4 会提高 A_t、降低 S_t，合理取值"0.2 上下"（图 3-11）；E 增大则 A_t 降低、S_t 升高；当 S_t<0.05 时中毒模型与合法模型呈现可识别分布；E>600 后模糊数据不再"模糊"，E>1000 后质量达瓶颈；建议 E≈0.5·e_lim，其中 MNIST e_lim=600、Fashion-MNIST e_lim=1000、CIFAR-10 e_lim=1600（3.4.4）。注：3.3.6 末尾写"更多详情可参见实验3.4.5 小节"，但该章只有 3.4.1–3.4.4。

### 4.2 MCD（4.2、4.3，算法 4-1、4-2）

核心思想：横向（同一轮不同客户端之间）比较看不出 VagueGAN 中毒模型，但纵向（同一客户端多轮上传）比较会发现"同一恶意客户端上传的中毒模型在一个较小的区域内分布得更为密集"，原因是 GAN 输出一致性。MCD 部署在服务器上，每经过 T′ 个训练轮次运行一次。

步骤：
1. 模型处理：维护受信任客户端集合 C_tr（初始为全体）；把每个可信客户端在 T′ 轮内上传的局部模型用 PCA 压到 2 维，组成集合 Q_{f,i}，未被选中的轮次对应位置记为 NULL。计算中心指标 θ̄^(2)_{f,i}（集合均值，公式 4-1）与覆盖指标 d̄_{f,i}（集合内各点到中心的平均欧氏距离，公式 4-2），即每个客户端被压缩成一对指标。
2. 基准值计算：以第一个基准客户端（例如服务器自己训练的局部模型）的指标 (θ̂^(2)_f, d̂_f) 为中心，用两个邻域限制因子筛选基准客户端集合 C_base：||θ̄^(2)_{f,i}−θ̂^(2)_f||/d̂_f < Ω1（公式 4-3）、|d̄_{f,i}−d̂_f|/d̂_f < Ω2（公式 4-4）；再对 C_base 取均值得到 θ^base_f（公式 4-5）与 d^base_f（公式 4-6）。
3. 客户端异常度：h_{f,i} = λ1·(||θ̄^(2)_{f,i}−θ^base_f||/d^base_f) + λ2·|d^base_f−d̄_{f,i}|（公式 4-7），λ1、λ2 主要用于两部分的数量级归一化。
4. 异常客户端检测：先取全体异常度的中值 h^med_f，再用 h^thr_f = δ·h^med_f（公式 4-8，δ∈(1,3)）作为阈值，超过阈值的客户端被移出 C_tr 并删除其 Q_{f,i}。

识别逻辑：现有攻击（标签翻转、PoisonGAN、噪声叠加）主要在中心指标上异常；基于 GAN 的攻击主要在覆盖指标上异常——"恶意客户端的覆盖指标 d̄_{f,i} 值明显较低"，说明中毒模型过于一致、分布过于密集（4.3、4.4.2）。

### 4.3 LSDAM（5.3）

核心思想：GAN 因模式崩溃导致生成多样性差，MCD 正是利用这一点；改用扩散模型，并用"大步 DDPM"生成兼具多样性特征与残留噪声的中毒数据。

大步 DDPM（5.3.1、5.3.2）：前向扩散每一步加入远大于基线的噪声，β*_t 比基线（β1=10⁻⁴ 到 βT=10⁻²）扩大接近两个数量级；论文给出取值示例 β*_1=0.1、β*_T=0.5，同时写"需要满足 β*_1>0.01，β*_T<0.5"（示例值与约束在原文中不一致）；总时间步 10<T*<60，并称"总时间步（1000−>50）"。反向用轻量化 U-net 预测噪声（参数量见第 8 节），"不完全扩散"使去噪后仍残留部分与真实样本相关的噪声。算法 5-1：训练时采样 x_t = ᾱ_t x_0 + √(1−ᾱ²_t)·ε_t，损失 L2(ε_t, logits)；推理时 x_{t−1} = (1/α_t)(x_t − β*_t·Model(x_t,t)) + σ_t ε_t。

理论（5.3.4）：基线设置 α_t = √(1−0.02t/T)（公式 5-1），log ᾱ_T < −0.005(T+1)（公式 5-3），T=1000 时 ᾱ_T≈e⁻⁵；大步设置打破了缓步连续扩散的平衡，欧氏距离度量误差大、反向拟合不完美，因此推理阶段去噪不完全并产生模糊结果，这种残留噪声正是所需的中毒特征。

### 4.4 C-S 架构与 CAEKL（6.2、6.3）

核心思想：只审查模型无法应对 LSDAM 这类强隐蔽攻击，因此在客户端入口审查数据、在服务器聚合前审查模型，形成双端审查；服务器不接触本地数据，论文称之为"数据不动，审查动"（6.1、6.2）。

客户端（CAE-Detecter，6.3.1）：服务器在训练开始前用测试集训练分类自编码器（Classification Auto-Encoder, CAE，引用文献[41]），CAE 在编码器潜在表示 z 上同时训练辅助分类器和解码器，最小化 ∑(RE_cae(x_i)+L_cae(x_i))；随后把 CAE-Detecter 部署在主任务训练入口。检测标准是重构误差与分类损失的组合：Error(x) = ψ·RE_cae(x) + (1−ψ)·L_cae(y)（公式 6-1），实验取 ψ=0.7（6.4.1）；异常样本被阻止进入主任务训练。过滤后生成局部数据描述（异常数据量, 局部数据总量）（公式 6-2），"依附于局部模型一起上传给服务器"。

服务器（KL-Detecter，6.3.2）：把每轮收到的局部模型用 PCA 进一步压到 1 维，θ^(1)_{t,i} = PCA(θ_{t,i})（公式 6-3）；按客户端保存 T′ 轮的模型信息集 Θ_i（未选中记 NULL）；用最大似然估计把每个客户端的模型信息集拟合成高斯分布（均值公式 6-11、方差公式 6-15）；用 KL 散度度量分布差异：KL(p_i,p_j) = log(σ_j/σ_i) + (σ_i²+(µ_i−µ_j)²)/(2σ_j²) − 1/2（公式 6-16）。论文刻意利用 KL 散度的非对称性，把高信任客户端分布当作基准分布。高信任基准客户端由局部数据描述打分选出：Υ1·(|D^train_i|−|D^ab_i|)/|D^train_i| + Υ2·|D^train_i|/Γ，其中第一项是合法数据占比、Γ 是"FL 主任务的标准数据批量"，Υ1>Υ2；论文未给出 Υ1、Υ2、Γ 的具体取值（6.3.2）。识别的结果用于"减少其权重或排除它们的参与"，KL 值还可"指导服务器的联邦聚合策略，例如优先考虑与基准分布相近的局部模型"（6.2、6.4.2）。

## 5. 检测或防御所需的数据

**防御方法需要的输入：**

1. 服务器每轮收到的本地模型参数（完整模型权重）。采集位置：服务器收到更新时（4.3、6.3.2）。粒度：逐客户端、逐轮（每客户端每次被选中上传一份）。MCD 用 PCA 压到 2 维（公式 3-11），KL-Detecter 压到 1 维（公式 6-3）。是否需要跨轮历史：需要，两者都要一个防御周期 T′ 内的逐客户端模型序列（实验 T′=80，4.4.1）。是否需要干净参考：MCD 需要第一个基准客户端（例如服务器自己训练的局部模型）作为 100% 安全参照；KL-Detecter 需要按数据描述选出的高信任客户端分布作为基准。额外计算：PCA 降维、均值/半径/异常度计算、高斯拟合与 KL 计算；论文强调它们都在低维进行（4.3、6.4.2）。
2. 每轮被选中参与聚合的客户端身份（未选中记 NULL）。采集位置：服务器收到更新时；粒度：逐客户端、逐轮；需要跨轮历史（4.3、6.3.2）。
3. 逐样本的客户端本地训练数据。采集位置：客户端主任务训练入口、训练前（6.2、6.3.1）。粒度：逐样本。是否需要干净参考：需要，CAE-Detecter 由服务器用测试集 D_test 训练后部署（6.3.1），Fashion-MNIST 中 D_test 有 10000 个样本（6.4.1）。额外计算：每个样本要过一遍 CAE 得到重构误差与分类损失（一次前向），论文未给出耗时。是否需要其他客户端的数据：不需要。
4. 逐样本的 CAE 重构误差 RE_cae(x) 与辅助分类损失 L_cae(y)（公式 6-1 的组合误差）。采集位置：客户端训练前；粒度：逐样本；需要干净参考（CAE 本身在 D_test 上训练）。
5. 局部数据描述（异常数据量，局部数据总量）。采集位置：客户端训练后生成，随局部模型上传，服务器收到更新时读取（6.3.1、公式 6-2）；粒度：逐客户端（一个周期内可累加）；不需要历史或额外计算。论文未讨论客户端谎报该描述的情形（分析）。
6. 服务器持有的干净测试集 D_test。采集位置：服务器侧，用于评估每轮全局准确率，也用于训练 CAE-Detecter（3.2.1、6.3.1、6.4.1）；粒度：逐样本；属于干净参考数据。注：论文同一处用了 Dtrain 与 Dtest 两个记号描述这个测试集（6.2 写"测试集 Dtrain"，6.3.1 写"全局测试数据集 Dtest"），存在记号不一致。
7. C-S 架构层面还列举了服务器端异常模型检测的备选技术——"门限识别、梯度方向检测和分布异常检测等"（6.2），但只列举、未指定所需数据。

**攻击会留下的可观测量痕迹，以及论文声称绕过的检测：**

- VagueGAN：论文称其"模糊数据"在很大程度上保留输入统计特征，局部模型横向 PCA 2 维/3 维可视化中与合法模型难以区分（图 3-8、图 3-9），全局准确率波动"基本接近无攻击情况"（图 3-10）；并声称"对中心服务器来说，只要启用基于 PCA 的防御方法，现有的数据中毒攻击就不会成功，而基于 VagueGAN 的中毒攻击则难以被发现"（3.4.3）。但它留下纵向痕迹：同一恶意客户端多轮上传模型的覆盖指标明显偏低（表 4-7），可被 MCD 识别（4.4.2）。
- LSDAM：论文称服务器视角下横向（图 5-6）与纵向（图 5-7）模型分布均无异常，MCD 的中心指标、覆盖指标与异常度 h_{f,i} 全部落在正常范围（表 5-1），KL-Detecter 同样难以识别（6.4.2）；但原始中毒数据可被客户端逐样本审查发现——"CAE-Dectecter 可以很轻松的识别出 LSDAM 的中毒数据"（6.4.1、图 6-5）。
- 论文声称 VagueGAN 与 LSDAM 可绕过基于模型审查的防御（PCA、UMAP、MCD、KL-Detecter）（3.4.3、5.4.2、6.4.2）；论文没有对逐样本数据清洗类防御做"绕过"评估（分析：论文未做该实验，不能据此认为其能绕过此类防御）。

## 6. 干预动作

- MCD（服务器，聚合前）：把异常度超过阈值 h^thr_f 的客户端从受信任客户端集合 C_tr 中删除，并删除其模型集合 Q_{f,i}（算法 4-2）；论文称"MCD 在第一次检查时成功识别出恶意客户端，并忽略其后续更新"，并"在随后的训练轮次中依旧按照防御周期执行"以维持安全级别（4.4.3、图 4-4）。
- KL-Detecter（服务器，聚合前）：识别异常分布后"服务器可以采取相应的措施来淡化它们的影响。这可能包括减少其权重或排除它们的参与"（6.2）；KL 值还可用于指导聚合，"优先考虑与基准分布相近的局部模型"（6.4.2）。论文未给出具体的权重公式（论文未说明）。
- CAE-Detecter（客户端，训练前）：把异常样本从本地训练数据中过滤掉，"任何异常数据都会被数据筛选器及时识别并阻止其进入主任务后续训练过程"（6.2、6.3.1），并把异常数量统计上报服务器。
- 论文没有给出模型修复、回滚、加噪、梯度裁剪、更新裁剪等干预动作。

## 7. 实验设置与主要结果

**第 3 章（VagueGAN 攻击）**：N=60、K=10、T=200，数据划分可为 IID 或 non-IID（non-IID 按文献[39]设置），α∈{0%,5%,10%,20%,30%}，结果取 10 次运行的平均值（3.4.1、3.4.2）。

- MNIST(IID)：无攻击 98.73%；VagueGAN 在 α=5/10/20/30% 为 98.61/98.35/97.84/97.46，标签翻转为 98.65/98.48/98.32/98.11（表 3-5，上表）。
- Fashion-MNIST(IID)：无攻击 87.97%；VagueGAN 为 87.34/86.79/85.87/84.77，标签翻转为 87.73/87.20/86.01/85.48（表 3-6，上表）。
- CIFAR-10(IID)：无攻击 76.28%；VagueGAN 为 74.94/74.02/73.16/71.93，标签翻转为 75.69/74.99/73.86/72.85（表 3-7，上表）。
- non-IID 三张子表同样给出：MNIST 基线 98.39%、Fashion-MNIST 基线 87.25%、CIFAR-10 基线 73.61%（表 3-5 至 3-7 的下半部分）。论文结论：VagueGAN 攻击效果优于四种基准，恶意比例增加与 non-IID 会使准确率下降更明显，CIFAR-10 任务更易受攻击（3.4.2）。
- 隐蔽性：以 IID、α=20% 的 Fashion-MNIST 为例，测量过去 50 个训练轮次中合法模型与中毒模型的统计距离并做 PCA 2 维/3 维可视化（图 3-8、图 3-9），并比较全局精度波动（图 3-10），论文称 VagueGAN 均优于基准。
- 权衡：κ 的影响见图 3-11，E 的影响见图 3-12。

**第 4 章（MCD 防御）**：N=20、K=5、T=200、IID Fashion-MNIST、α=20%（4.4）；MCD 参数 T′=80、λ1=1、λ2=2、Ω1=4、Ω2=2（4.4.1）；对比 PCA[10]（T′=80）与 UMAP[14]（邻域 200、布局控制 0.8、余弦距离）（4.4.1）。

- 检测指标表 4-2 至表 4-7 分别给出各攻击场景下每个客户端的中心指标、覆盖指标与异常度；VagueGAN 场景下中毒模型的中心指标不异常，但覆盖指标偏低（4.4.2）。表 4-2 中标签翻转场景的基准值为 θ^base_f=(-5.31,-0.62)、d^base_f=3.32；表 4-7 中 VagueGAN 场景为 θ^base_f=(-0.05,0.02)、d^base_f=5.55（对应表 4-2、表 4-7）。
- 表 4-8：MCD 平均检出的恶意客户端数在 M=1/2/4/6 时分别约为 1/2/3.8–4/5.6–6；部署 MCD 后主任务准确率为 87.84%–87.94%（无攻击基线 a_t=87.97%）。表 4-9（PCA）在 VagueGAN 下检出 0.1/0.2/0.6/0.9 个恶意客户端，准确率 87.34/86.79/86.01/84.97；表 4-10（UMAP）检出 0/0/0.2/0.7，准确率 87.34/86.79/85.96/84.91。
- 论文称 MCD 在所有六种攻击场景中"都能在第一次检查时成功识别出恶意客户端"（4.4.3、图 4-4）。

**第 5 章（LSDAM 攻击）**：论文写"实验配置与数据集设置与3.4.4 小节相同"，随后列出的却是与 4.4 节一致的设置（IID Fashion-MNIST、N=20、K=5、α=20%、M=4），此处存在章节引用不一致。大步 DDPM 参数：timestep=40、epoch=30、β*_1=0.09、β*_T=0.49 的线性插值（5.4）。结果：图 5-5 显示 LSDAM 攻击效果与 VagueGAN 接近甚至略优（以准确率曲线给出，论文未列具体数值）；表 5-1 显示 MCD 的各项指标均在正常范围，无法识别 LSDAM（5.4.2）。

**第 6 章（C-S/CAEKL）**：FL 设置沿用 4.4、5.4（IID Fashion-MNIST、N=20、K=5、α=20%）。CAE-Detecter 在服务器用 D_test（10000 个样本）训练，ψ=0.7；实验对每种中毒数据插入 100 个样本，误差分布以箱线图给出（图 6-5），论文称可清晰区分全部中毒数据，但未列出具体数值。KL-Detecter 的 1 维压缩可视化见图 6-6、高斯拟合可视化见图 6-7；论文称其"判别结果与 MCD 接近"，但对 LSDAM 同样无效（6.4.2）。

## 8. 开销

- VagueGAN：只有定性说明——论文称"生成质量相对较低的模糊数据的计算效率很高，即使对于资源受限的移动设备来说，它也具有广泛的适用性"（1.3），以及"与传统的 GAN 相比，VagueGAN 只生成质量标准相对较低的模糊数据，因此中毒数据的生成效率更高"（3.3.3）。没有时间、显存或通信数字（论文未报告）。
- LSDAM：报告了大步 DDPM 的 U-net 参数量约 7.75M，对比"基线 DDPM 中原始 UNet 的参数数量大约为 28M 左右（采用上采样带有转置卷积的 UNet 约为 31M）"，并把总时间步由 1000 降到 50，称"中毒数据生成更快速，资源消耗更少"（5.3.1、5.3.2）。没有实测训练/生成耗时（论文未报告）。
- MCD：论文称其"经济高效"，理由是服务器只保存每个客户端的两个低维指标而不是高维原始模型，"大大节省了服务器的存储空间，同时也降低了 MCD 识别恶意客户端的计算量"（4.3）。没有存储或计算的量化数字（论文未报告）。
- KL-Detecter：论文称一维压缩"大大减少KL-Dectecter 的资源消耗"，且"计算量小、不依赖服务器的过多资源"（6.4.2）。没有具体数字（论文未报告）。
- CAE-Detecter：论文称其"可以在联邦训练刚开始的训练轮次就低质量模型排除在系统外"，即减少被攻击轮次（6.4.1）。没有报告客户端额外计算或延迟（论文未报告）。
- 通信：局部数据描述"会依附于局部模型一起上传给服务器"（6.3.1），论文未给出其大小与额外通信量（论文未报告）。
- 小结：论文只在 LSDAM 上给出了相对开销指标（参数量、扩散步数），没有端到端的计算/通信/存储测量。

## 9. 假设、局限与自适应攻击

**论文明确写出的成立假设：**

1. 服务器完全诚实且不可攻击；FL 通信链路可靠，攻击者无法影响上传与交换；攻击者无法访问服务器与良性客户端的数据集及模型（3.2.2）。
2. 攻击者至少控制一个客户端，并完全掌握其本地数据集与本地训练过程（3.2.2）。
3. MCD 需要一个"100% 安全"的基准客户端（例如服务器自己也作为一个客户端训练局部模型），并依赖攻击者持续使用相同的 GAN 模型；C_base 的筛选还依赖 Ω1、Ω2 两个人工设定的限制因子（4.3）。
4. KL-Detecter 假设客户端的模型信息集可以拟合成高斯分布，并需要一个高信任度的基准客户端，其选择依赖客户端上报的局部数据描述（6.3.2）。
5. CAE-Detecter 假设服务器测试集是"经服务器审核后的基准数据集"、"绝对保证测试数据集的质量"，并且"囊括了主任务所需要学习到的所有数据特征"（6.2）。
6. 分析：MCD 用全体异常度的中值 h^med_f 构造阈值（公式 4-8），隐含了受信任集合中多数客户端为良性（honest majority）的前提；论文没有显式陈述这一假设。同理，KL-Detecter 把高信任客户端分布当作唯一基准，也依赖基准本身未被污染。

**论文自述的局限（7.2）：**（1）CAE-Detecter"可能会面临服务器测试数据集数据特征不完全，即客户端中存在一些真实数据但服务器测试集中并未包含此类特征，这可能会导致 CAE-Detecter 对其未学习到的真实数据造成误判"，未来拟用零样本学习方法解决，并研究持续/动态自学习策略；（2）LSDAM 只关注了扩散模型的数据多样性优势，噪声与特征关系的可控性、生成稳定性还有待进一步研究；（3）CAEKL 只是 C-S 架构的初次尝试，C-S 架构还可扩展到数据安全、模型安全、鲁棒性联邦学习、稳健联邦聚合等方向。

**自适应攻击：**

- 论文在第 4 章开头明确承认："如果在不同的环境中实施或动态应用不同参数的 VagueGAN，那么对应的攻击可能会产生难以检测"；第 6 章开头也指出"如果攻击者多次使用不同参数设置的 GAN 生成混合的中毒数据，这就会对 MCD 的判断产生影响，进而削减 MCD 的鉴别能力"（4.1、6.1）。但论文没有为这两种自适应攻击给出实验（论文未报告）。
- 第 5 章的 LSDAM 本身就是针对第 4 章 MCD 所利用的 GAN 一致性缺陷而设计的防御感知攻击，并在实验中证明 MCD（表 5-1、图 5-7）与 KL-Detecter（6.4.2）都无法识别它，这构成一次针对已提出防御的自适应攻击评估。论文没有评估针对 CAE-Detecter/CAEKL 的自适应攻击（例如构造重构误差极小的中毒样本或伪造数据描述）；CAE-Detecter 的误判风险只在其自述局限中以"测试集特征不完全"的形式讨论（7.2）。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）：**

- 分析：论文全部实验是 28×28 或 32×32 的图像分类与小型 CNN，没有语言模型、文本数据或 LoRA。VagueGAN 的 MLP 生成器以 100 维噪声 + 10 维标签生成 784 维图像，LSDAM 的 U-net 直接作用于 28×28 图像（5.3.1、表 3-2），这些生成器结构不能直接用于 token 序列；论文也没有讨论文本模态下的"模糊数据"应如何定义。
- 分析：MCD 的识别依据是 GAN 模式崩溃造成的样本相似、进而造成同客户端多轮模型高度一致。在 LoRA 微调中，即使恶意客户端反复用同一小批数据训练，低秩增量的分布、优化器状态与采样随机性都会改变"覆盖指标"的可分性；公式 4-2 的欧氏半径与 PCA 投影是否仍然有效，论文没有依据。此外 LoRA 的 A/B 矩阵通常带有缩放因子 α/r，直接对拼接后的参数做 PCA 会混合不同层与不同缩放。
- 分析：论文假设服务器持有覆盖主任务全部特征的干净测试集，并能自己在同一任务上训练一个"100% 安全"的基准模型（4.3、6.2）。在联邦大模型微调中，服务器往往没有与客户端同分布的指令数据，也未必有能力单独训练一个基准 LoRA，这两条假设都更难成立。
- 分析：论文的采集对象是完整模型参数；联邦 LoRA 上传的是低秩增量，不同客户端的 rank、目标模块集合可能不同，库必须先做层/模块对齐再做降维与距离度量，这是论文未涉及的新问题。
- 分析：论文威胁模型禁止攻击者影响链路与聚合，攻击只从本地数据进入；在适配器供应链场景中，恶意客户端可以直接构造上传的适配器（例如放大增量、只改特定层、注入触发行为），这类攻击是否会落在 MCD/KL-Detecter 的统计量内，论文没有依据。
- 分析：论文的 T=200 轮、T′=80 轮防御周期是按图像 FL 设定的；联邦 LoRA 微调的轮次通常少得多，逐轮收集历史并按周期判定的做法可能需要改成按步或按 epoch 采集，论文未讨论采样稀疏（未选中轮次记 NULL）对统计量的影响。

## 10. 对防护库设计的含义

1. 分析：采集底座需要在"服务器收到更新"这一信任边界上，按（客户端标识，轮次）记录并保留每个客户端的更新快照，同时记录本轮被选中/未选中的掩码。MCD 与 KL-Detecter 都依赖同一客户端的跨轮序列，因此库必须提供可配置长度的按客户端历史窗口和"未参与轮次为空"的语义，这是通用需求。
2. 分析：需要服务器侧的特征提取钩子，把原始更新映射为低维视图（论文用 PCA 到 2 维和 1 维），并允许插件自定义降维方式——论文明确说 MCD"并不局限于此降维方法"（4.3）。对 LoRA，该钩子最好能以层或模块为单位输出范数/投影，而不是把不同层的张量直接拼平，这属于迁移时新增的需求。
3. 分析：需要一个"干净参考/受信任客户端"接口。MCD 和 KL-Detecter 都需要一个基准分布（论文中是服务器自己训练的模型或高信任客户端），库应把"基准从哪来、如何更新、如何防止基准本身被污染"做成显式配置，而不是藏在算法内部；这在联邦 LoRA 场景下是通用且更难满足的需求。
4. 分析：客户端侧需要"训练前逐样本"钩子。CAE-Detecter 要求在数据进入主任务训练之前逐样本打分并过滤，并允许把一个统计摘要随更新一起上传（公式 6-2），因此库需要支持客户端本地过滤器插件以及"随更新上报元数据"的通道。这是本篇论文特有的采集点，但"客户端前置过滤 + 元数据上报"本身可以做成通用接口。
5. 分析：干预接口至少需要三种：聚合前剔除客户端（MCD）、按信任度重加权（C-S 架构所述"减少其权重"与"优先聚合与基准分布相近的模型"）、客户端训练前过滤样本（CAE-Detecter）。本论文用到了这三种，没有用裁剪、加噪、模型修复或回滚，因此这三类动作对复现本论文是必需的。
6. 分析：通用需求是"客户端身份 + 轮次 + 选择掩码 + 历史窗口 + 插件式特征提取 + 多种干预动作"；本篇论文特有的需求是：基于 GAN 输出一致性的覆盖指标、基于一维 PCA + 高斯最大似然拟合 + 非对称 KL 散度的分布比较、基于逐样本重构误差与分类损失的 CAE 过滤器，以及"服务器自己充当 100% 安全基准客户端"这一强假设。库在支持这些插件时，应把最后一条标注为可选前置条件，以便在无法满足时优雅降级为仅报告。

## 11. 原文依据

说明：本论文正文为中文，可逐字引用的英文连续片段只存在于英文摘要（ABSTRACT, p. iv）与英文图表标题中，因此下面 10 条引文全部取自英文摘要与表 4-8 标题；PDF 提取造成的断行连字符（如 collabora-tively）与连字（ﬁ、ﬂ）已按常规字符还原，其余逐字保留。

1. 章节：ABSTRACT (p. iv)。支撑：第 1 节"传统联邦学习场景"这一判断。
   "As a distributed machine learning paradigm, FL is collaboratively carried out on privately owned datasets but without direct data access."
2. 章节：ABSTRACT (p. iv)。支撑：第 2 节"本地数据不可见带来的中毒威胁"这一威胁模型判断。
   "Although the original intention is to allay data privacy concerns, "available but not visible" data in FL potentially brings new security threats, particularly poisoning attacks that target such "not visible" local data."
3. 章节：ABSTRACT (p. iv)。支撑：第 4、5 节"现有攻击因统计异常而失效，因此需要隐蔽攻击"这一问题动机。
   "Initial attempts have been made to conduct data poisoning attacks against FL systems, but cannot be fully successful due to their high chance of causing statistical anomalies."
4. 章节：ABSTRACT (p. iv)。支撑：第 3 节"攻击入口是本地数据"与第 4.1 节 VagueGAN 的定位。
   "An attack method named VagueGAN is proposed, which is a GAN model specially designed for data poisoning attacks against FL systems."
5. 章节：ABSTRACT (p. iv)。支撑：第 3、4 节"中毒数据影响所有标签/类且不易被察觉"。
   "It generates vague poisoned data that can not only effectively but also unnoticeably attack a global model with all labels/classes involved."
6. 章节：ABSTRACT (p. iv)。支撑：第 4.1 节"直接生成面向 FL 的中毒数据以提高隐蔽性"这一核心贡献。
   "To the best of our knowledge, it is the first GAN model with emphasis on direct generation of FL-targeted poisoned data for improved attack stealthiness."
7. 章节：ABSTRACT (p. iv)。支撑：第 4.2、5 节"MCD 直接复用服务器已收集的本地模型、依据 GAN 输出一致性识别"。
   "A cost-effective countermeasure named Model Consistency-Based Defense (MCD) is proposed to this type of data poisoning attacks, which directly reuses the local models already collected by the server"
8. 章节：ABSTRACT (p. iv)。支撑：第 4.3、5.4.2、9 节"大步 DDPM 生成多样化中毒数据、在多维度伪装中毒模型、使基于模型审查的防御失效"。
   "Proposed a strong stealthy data poisoning attack called "LSDAM", which utilizes "big-step"DDPM to generate more diversified poisoned data, and conceals the poisoned model in multiple dimensions, making it difficult for existing model censorship-based defenses to cope with it."
9. 章节：ABSTRACT (p. iv)。支撑：第 4.4、10 节"C-S 架构在不侵犯本地隐私的前提下同时审查数据与模型"。
   "A novel "C-S" architecture is proposed to double-check data and models without violating the privacy of local clients."
10. 章节：ABSTRACT (p. iv)。支撑：第 4.4、6 节"CAEKL 是数据与模型双重维护而非单纯防御"。
    "We also propose "CAEKL", a federated learning security maintenance method based on the C-S architecture, to maintain the federated learning system in a comprehensive way instead of just defending it."
11. 章节：表 4-8 英文标题 (p. 58)。支撑：第 7 节"MCD 在不同恶意客户端比例下的防御效果"这一实验结果。
    "Table 4-8 Effectiveness of MCD Defence in Attack Scenarios with Different Rates of Malicious Clients"

（说明：第 11 节按要求给出 6–10 条，上表实际列出 11 条，其中第 11 条为表标题；若严格限制 10 条，可删除第 3 条，其余不受影响。）

```json
{
  "key": "sun2024thesis",
  "title": "生成式模型在联邦学习安全中的应用研究",
  "year": 2024,
  "paper_type": "other",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "每个客户端每轮上传的本地模型完整参数，MCD 用 PCA 压到 2 维、KL-Detecter 压到 1 维", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "按客户端聚合的中心指标、覆盖指标与异常度 h_f,i（防御周期 T' 内）", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "每轮被选中参与聚合的客户端身份与未选中掩码（NULL 占位）", "where": "server_receive", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "基准客户端模型分布（服务器自身训练的局部模型，或按数据描述选出的高信任客户端分布）", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "客户端本地训练数据（逐样本原始样本），在进入主任务训练前被 CAE-Detecter 打分与过滤", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "逐样本 CAE 重构误差 RE_cae(x) 与辅助分类损失 L_cae(y) 组成的 Error(x)", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "随局部模型上传的局部数据描述（异常数据量，局部数据总量）", "where": "client_post_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "服务器持有的干净测试集 D_test（Fashion-MNIST 中 10000 个样本），用于评估全局准确率并训练 CAE-Detecter", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "攻击痕迹：全局模型逐轮测试准确率的波动幅度", "where": "evaluation", "granularity": "round", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "攻击痕迹：由 VagueGAN 或大步 DDPM 生成并替换本地数据集的中毒样本及其分布统计", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["exclude_client", "reweight", "filter_samples"],
  "intervention_where": "both",
  "assumptions": [
    "服务器完全诚实且不可攻击，通信链路可靠，攻击者只能控制客户端",
    "攻击者可持续控制至少一个客户端，并完全掌握其本地数据集与本地训练过程",
    "MCD 需要一个 100% 安全的基准客户端（例如服务器自己训练的局部模型）",
    "攻击者持续使用相同的 GAN 模型生成中毒数据；动态更换参数时 MCD 可能难以检测（论文提及但未实验）",
    "客户端的模型信息集可近似拟合为高斯分布，且存在可用的高信任基准客户端",
    "服务器测试集经严格审核并覆盖主任务所需的全部数据特征",
    "受信任客户端集合中多数为良性（论文未显式说明，由中值阈值隐含）",
    "客户端上报的局部数据描述可信（论文未讨论谎报情形）"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "ABSTRACT (p. iv)", "supports": "第1节：传统联邦学习场景", "text": "As a distributed machine learning paradigm, FL is collaboratively carried out on privately owned datasets but without direct data access."},
    {"section": "ABSTRACT (p. iv)", "supports": "第2节：本地数据不可见带来的中毒威胁", "text": "Although the original intention is to allay data privacy concerns, \"available but not visible\" data in FL potentially brings new security threats, particularly poisoning attacks that target such \"not visible\" local data."},
    {"section": "ABSTRACT (p. iv)", "supports": "第4、5节：现有攻击因统计异常而失效", "text": "Initial attempts have been made to conduct data poisoning attacks against FL systems, but cannot be fully successful due to their high chance of causing statistical anomalies."},
    {"section": "ABSTRACT (p. iv)", "supports": "第3、4.1节：VagueGAN 的定位与攻击入口", "text": "An attack method named VagueGAN is proposed, which is a GAN model specially designed for data poisoning attacks against FL systems."},
    {"section": "ABSTRACT (p. iv)", "supports": "第3、4节：中毒数据覆盖全部标签且不易察觉", "text": "It generates vague poisoned data that can not only effectively but also unnoticeably attack a global model with all labels/classes involved."},
    {"section": "ABSTRACT (p. iv)", "supports": "第4.1节：直接生成面向 FL 的中毒数据以提高隐蔽性", "text": "To the best of our knowledge, it is the first GAN model with emphasis on direct generation of FL-targeted poisoned data for improved attack stealthiness."},
    {"section": "ABSTRACT (p. iv)", "supports": "第4.2、5节：MCD 复用服务器已收集的本地模型并利用 GAN 输出一致性", "text": "A cost-effective countermeasure named Model Consistency-Based Defense (MCD) is proposed to this type of data poisoning attacks, which directly reuses the local models already collected by the server"},
    {"section": "ABSTRACT (p. iv)", "supports": "第4.3、5.4.2、9节：LSDAM 使基于模型审查的防御失效", "text": "Proposed a strong stealthy data poisoning attack called \"LSDAM\", which utilizes \"big-step\"DDPM to generate more diversified poisoned data, and conceals the poisoned model in multiple dimensions, making it difficult for existing model censorship-based defenses to cope with it."},
    {"section": "ABSTRACT (p. iv)", "supports": "第4.4、10节：C-S 架构在不侵犯隐私下双重审查", "text": "A novel \"C-S\" architecture is proposed to double-check data and models without violating the privacy of local clients."},
    {"section": "ABSTRACT (p. iv)", "supports": "第4.4、6节：CAEKL 是对系统做全面维护而非仅防御", "text": "We also propose \"CAEKL\", a federated learning security maintenance method based on the C-S architecture, to maintain the federated learning system in a comprehensive way instead of just defending it."}
  ]
}
```
