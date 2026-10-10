# sun2024vaguegan：A Model Consistency-Based Countermeasure to GAN-Based Data Poisoning Attack in Federated Learning

## 1. 基本信息

场景是传统联邦学习（federated learning, FL），学习任务是图像分类，模型是小型卷积神经网络（convolutional neural network, CNN），全文没有出现大语言模型（large language model, LLM）、参数高效微调（parameter-efficient fine-tuning, PEFT）、LoRA 或适配器供应链的任何内容；论文在第 VI-A-a 节明确说"我们以图像数据为例来评估 VagueGAN 的投毒能力"，同时声明"模糊数据"的想法不限于该数据类型（第 VI-A-a 节）。

论文类型同时包含攻击与防御：主贡献定位为防御，即模型一致性防御（Model Consistency-Based Defense, MCD），同时提出一个 GAN 数据投毒攻击 VagueGAN，用来把防御推到极限（摘要、第 I 节贡献列表）。在最终 JSON 中我把 paper_type 记为 defense，因为标题、摘要与贡献顺序都以防御为主；需要强调的是这篇论文并不是纯防御论文，它同样提出并评估了新攻击。

训练阶段方面，投毒进入点是联邦训练开始之前的客户端本地数据准备阶段，检测发生在服务器收到本地模型之后、以"防御周期"为单位（第 IV-B 节、第 V-B-a 节）。论文类型可概括为攻击加防御的混合工作，数据集是 MNIST、Fashion-MNIST、CIFAR-10、CIFAR-100、Mini-ImageNet（第 VI-A-a 节）；默认联邦设置为 60 个客户端、每轮随机选择 10 个客户端参与聚合、共 200 轮（第 VI-A-b 节）；防御效果实验改为 20 个客户端、每轮选 5 个、共 200 轮（第 VI-E 节）。论文未报告各数据集的具体样本量、每个客户端分到的样本数，也未报告本地训练的优化器、学习率与批大小。全文标注的版本是 arXiv:2405.11440v3，日期为 2026 年 3 月 19 日（第 1 页页脚），因此年份字段我按首次公开的 2024 年填写。

## 2. 威胁模型

攻击者是恶意客户端（malicious client）。论文假设系统中至少存在一个数据投毒攻击者，攻击者可以控制一个或多个良性客户端，或者把自己伪装成良性客户端（第 III-B-b 节）。论文用 M 表示恶意客户端数量、用 α 表示恶意客户端比例，实验中 α 取 5%、10%、20%、30%（表 I、表 IV）。

攻击者的能力是：获得每个被控客户端的全部权限，包括本地数据集与本地模型训练过程（第 III-B-b 节）。攻击者的操作范围被限制在被控客户端内部：服务器被假设为完全诚实且不可攻击；通信链路可靠，攻击者不能影响模型交换过程；攻击者不能访问服务器与未被控制客户端的数据集；攻击者也不能访问未被控制客户端的模型（第 III-B-b 节）。

攻击者的目标有两个，论文把它们视为同等重要：首要目标是尽可能降低全局模型性能，其次是把攻击隐藏起来不被服务器检测到（第 III-B-a 节）。从目标类型看属于无目标破坏（untargeted），论文没有设置后门触发器或定向误分类目标，也没有涉及越狱或安全对齐破坏，更没有隐私窃取目标；论文中的标签翻转基线虽然把标签"6"改成"0"，但那只是攻击基线的构造方式（第 VI-A-c 节）。

防御者是服务器。服务器能看到的是每轮被选中客户端上传的本地模型（第 III-A 节、第 V-B-a 节）、用于计算全局准确率的测试数据集 D_test（第 III-A 节），以及自己维护的信任集合 Ctr 与基准客户端集合 Cbase（第 V-B-a 节、第 V-B-b 节）。服务器信任一个"100% 安全且免疫攻击"的第一基准客户端，论文举例说可以由服务器自己训练一个本地模型来充当（第 V-B-b 节）。服务器看不到任何客户端的原始训练数据，这正是论文强调的检测困难来源。

## 3. 攻击入口与流程位置

攻击内容进入的位置是本地数据准备（local data preparation），也就是在联邦训练开始之前。具体操作步骤按第 IV-B 节与算法 1 描述如下：第一步，攻击者取得客户端 c_j 的控制权，并在该客户端部署一个未训练的 VagueGAN；第二步，在联邦训练开始之前，恶意客户端用自己的本地数据集按式 (1) 的损失训练 VagueGAN；第三步，训练好的 VagueGAN 生成一个与原始数据集等大的投毒数据集，原始数据集的每个样本 (x, y) 恰好对应一个投毒样本 (x_p, y)；第四步，用投毒数据集整体替换原始本地数据集；第五步，在后续每一轮 t 中接收全局模型、在投毒数据集上正常训练本地模型，并把投毒后的本地模型 θ^{poison}_{t,j} 上传给服务器（算法 1 第 10 至 13 行）。

需要强调的是，攻击不发生在更新上传前的后处理（缩放、投影、拼装），不发生在服务器聚合，也不发生在全局模型下发：恶意客户端在数据被替换之后仍然执行规范的本地训练与规范的上传，这与模型投毒（model poisoning）在入口上不同，论文在第 I 节把数据投毒与模型投毒明确区分，并认为数据投毒更难被服务器检测。攻击的"位置"从流程角度看是本地数据准备，其效果通过本地训练传导到上传的模型，最终在服务器聚合后影响全局模型。

对于防御方，MCD 所针对的攻击入口同样是本地数据准备与本地训练：它在服务器侧接收更新之后工作，检测对象是本地模型在多轮之间的分布一致性（第 V 节、第 V-A 节）。

## 4. 方法原理

论文包含两个方法：攻击方法 VagueGAN 与防御方法 MCD。

### VagueGAN（第 IV-A 节至第 IV-F 节）

核心思想是反向利用生成对抗网络（generative adversarial network, GAN）：不是生成高质量接近真实的样本，而是生成"看似合法但带有适量有毒噪声"的模糊数据。它把条件 GAN（conditional GAN, CGAN）扩展而来，所有数据由多层感知机（multi-layer perceptron, MLP）式网络生成（第 IV-A 节）。为提高隐蔽性，判别器用了较深结构（例如 4 个隐藏层）、批归一化（batch normalization）与 LeakyReLU，并采用大批量对全数据集训练；为提高攻击效果，生成器同样加深到 4 个隐藏层并加入批归一化与 LeakyReLU，同时通过损失函数打破常见的纳什均衡（Nash equilibrium）来限制判别器能力（第 IV-A 节）。

关键公式是式 (1)：对生成器取最小、对判别器取最大，目标函数等于真实样本项与生成样本项之和，其中真实项为 log(1+κ)D(x) 的期望，生成项为 log(1−(1+κ)D(G(z))) 的期望，κ 是取值在 0 到 1 之间的抑制因子（suppression factor）。论文指出 κ 越大对生成能力的限制越强，因此 κ 可以用来权衡攻击有效性与隐蔽性（第 IV-A 节）。理论分析给出最优判别器 D*(x) = p_d(x) / ((1+κ)(p_d(x)+p_g(x)))（式 (6)）；当 D*(x) = 0.5 时生成分布满足 p_g(x) = ((1−κ)/(1+κ)) p_d(x)（式 (7)），说明生成分布与真实分布相关但不相同，κ 等于 0 时 VagueGAN 退化为普通 GAN（第 IV-C 节）。

无监督变体受 InfoGAN 启发，增加一个分类器 Q 来度量辅助向量 γ 的有效性，Q 与判别器共享前 4 个隐藏层（第 IV-E 节）。其目标函数是在式 (1) 基础上减去 λL(G,Q)（式 (14)），其中 L(G,Q) 是辅助向量与生成样本之间互信息的下界（式 (15)），γ 包含类保真度（class fidelity）与风格保真度（style fidelity）。论文还给出三种部署方式：分布式部署、集中式部署与混合部署（第 IV-F 节、图 6）。

### 攻击有效性、隐蔽性与权衡（第 IV-D 节）

攻击有效性定义为 A_t = a_t − a^p_t，即同一条件下无攻击时的全局准确率减去有攻击时的准确率（式 (8)），其中准确率按一对一其余（one-vs-rest）策略计算（式 (9)）。隐蔽性定义为两类模型簇质心之间欧氏距离的倒数 S_t = 1/‖u_t − u^p_t‖（式 (13)）；计算前先用主成分分析（principal component analysis, PCA）把高维本地模型降到二维（式 (10)），再分别求良性模型簇与投毒模型簇的质心 u_t 与 u^p_t（式 (11)、式 (12)）。论文给出的经验配置是 E 取 400 到 600、κ 取 0.2 时可以得到中等有效性与中等隐蔽性的平衡（第 IV-D 节），并指出当 S_t 小于 0.05 时投毒攻击会变得可检测（第 VI-C-b 节）。

### MCD（第 V-A 节、第 V-B 节）

核心观察是：同一恶意客户端上传的投毒模型在多轮之间分布得更密集、占据更小的区域，原因是 GAN 输出具有一致性（第 V-A 节、图 7）。MCD 由服务器执行，分四步。

第一步是模型处理：MCD 维护信任客户端集合 Ctr，初始等于全体客户端；每隔 T′ 个联邦轮运行一次，把每个受信客户端在这 T′ 轮内上传的本地模型存入集合 Q_{f,i}，其中 f 是防御周期序号；先用 PCA 把模型降到二维，若客户端在某轮未被选中则对应项记为 NULL；随后为每个客户端计算两个指标，即质心指标（式 (16)，窗口内模型向量的平均）与足迹指标（式 (17)，窗口内模型到质心的平均欧氏距离，论文称其为方差）。

第二步是基线值计算：MCD 先维护一个第一基准客户端（论文举例为服务器自己训练一个本地模型），认为它 100% 安全，其指标记为 (θ̂^(2)_f, d̂_f)；然后用两个常数 Ω1 与 Ω2 定义邻域（式 (18) 对质心指标、式 (19) 对足迹指标），把落在邻域内的客户端组成基准客户端集合 Cbase；最后由 Cbase 的指标平均得到基线 θ^base_f（式 (20)）与 d^base_f（式 (21)）。

第三步是客户端异常度计算：对每个受信客户端计算 h_{f,i} = λ1 乘以归一化的质心偏差，加上 λ2 乘以足迹偏差的绝对值（式 (22)），其中 λ1 与 λ2 是权重，用来把量级不同的两项归一化。

第四步是恶意客户端识别：先取所有受信客户端异常度的中位数 h^med_f，再按 h^thr_f = δ h^med_f 计算阈值（式 (23)），δ 取值在 1 到 3 之间，异常度大于阈值的客户端被判定为恶意（第 V-B-d 节）。论文指出质心指标对标签翻转、PoisonGAN、噪声叠加等大多数已有攻击有效，而足迹指标对 GAN 类投毒攻击有效（第 V-B 节、表 VII）。

## 5. 检测或防御所需的数据

MCD 需要的输入可以逐项列出。论文的检测方法不使用逐样本损失、梯度、隐藏层激活、输出文本，也不要求客户端做额外的前向或反向计算；全部所需数据都在服务器侧。

第一项是每个被选中客户端每轮上传的完整本地模型参数 θ_{t,i}。它是 MCD 的原始输入，在服务器收到更新时采集，并在聚合时被复用；粒度是逐客户端、逐轮，覆盖一个长度为 T′ = 80 轮的防御周期（第 V-B-a 节、第 VI-A-d 节）。这一项需要跨轮历史，不需要干净参考数据，不需要额外前向或反向计算（PCA 由服务器在已有模型上执行），但它天然需要其他客户端的数据，因为异常判定要用全体受信客户端的异常度分布。

第二项是客户端参与掩码。服务器每轮从 N 个客户端中随机选 K 个（第 III-A 节），因此必须记录每个客户端在 T′ 轮中哪些轮被选中，未被选中时对应的二维模型记为 NULL（第 V-B-a 节）。粒度是逐客户端、逐轮，需要跨轮历史，不需要干净参考数据，不需要额外计算。

第三项是第一基准客户端的两个指标。论文要求存在一个被认为 100% 安全、免疫攻击的基准客户端，其指标记为 (θ̂^(2)_f, d̂_f)（第 V-B-b 节）；在服务器端每个防御周期计算一次。这一项需要干净参考数据：论文举例说可以由服务器自己训练一个本地模型来充当该客户端，但论文未说明服务器是否真的持有这样一份可信数据集、也未说明其规模与来源，这一项还需要额外的训练与降维计算。其他客户端的数据对它不是必需的。

第四项是基准客户端集合 Cbase 及其基线值。MCD 用 Ω1 与 Ω2 规定的邻域（式 (18)、式 (19)）从受信客户端中筛出 Cbase，再平均得到 θ^base_f 与 d^base_f（式 (20)、式 (21)）（第 V-B-b 节）。采集位置是服务器聚合后、每个防御周期一次，粒度是逐客户端、逐周期；它需要跨轮历史、需要干净参考（锚点是第一基准客户端），并需要其他客户端的模型指标。

第五项是全局模型在测试集上的准确率。服务器用测试数据集 D_test 得到全局准确率 a_t（第 III-A 节），采集位置是评估时，粒度是逐轮的一个标量；它需要测试集作为干净参考，观察准确率波动时还需要跨轮历史。需要说明的是，准确率在论文中用于度量攻击有效性 A_t 与防御效果（第 IV-D 节、第 VI-B 节、第 VI-E 节），MCD 的四步判定本身只使用前四项模型指标，不依赖准确率。

从攻击侧看，VagueGAN 会留下的可观测量痕迹有三类。第一类是本地模型在多轮之间的一致性偏高，表现为足迹指标 d̄_{f,i} 明显偏低：在表 III 的 VagueGAN 场景中，基准足迹 d^base_f 为 5.55，而四个 d̄ 明显偏低的条目取值为 0.92、1.01、1.35、1.28，对应异常度 h 分别为 8.92、8.64、7.90、8.48（表 III；论文正文说明恶意客户端的 d̄ 明显低于良性客户端的正常值）。分析：PDF 抽取丢失了表 II 与表 III 的红绿颜色标注，"哪些行属于恶意客户端"是我结合论文正文描述与数值模式作出的阅读。第二类是投毒模型与良性模型之间的统计距离较小，论文在图 9 中用 Fashion-MNIST、独立同分布（independent and identically distributed, IID）、α = 20% 的设置展示 VagueGAN 的隐蔽性高于标签翻转、PoisonGAN 与各类噪声叠加攻击。第三类是全局准确率波动小，图 10 展示 VagueGAN 的准确率曲线最接近无攻击情形。论文声称 VagueGAN 能绕过 PCA、UMAP、CONTRA、DnC、LoMar、FedDMC 六种防御（表 VII、图 16），并特别指出在 VagueGAN 场景下恶意客户端在质心指标 θ̄^(2)_{f,i} 上没有异常，只有足迹指标能识别它们（第 VI-E-a 节）。

## 6. 干预动作

MCD 的干预动作是剔除客户端（exclude client）。在第四步中，异常度大于阈值 h^thr_f 的客户端被标记为恶意，并从信任集合 Ctr 中移除，同时把该客户端的历史模型集合 Q_{f,i} 从 Q_f 中删除（第 V-B-d 节、算法 3 第 13 至 16 行）。论文在实验部分进一步说明，MCD 在第一次检查时就识别出恶意客户端并"忽略它们的后续更新"（第 VI-E-b 节），因此被识别客户端的更新在后续轮次中不再影响聚合结果。

动作发生的位置是服务器端，时间点是在收到并存储本地模型之后、防御周期结束时；由于后续更新被忽略，其实际效果体现在后续轮次的聚合之前。论文没有使用重新加权、梯度裁剪、加噪、样本过滤、模型修复或回滚等任何其他干预，也没有描述如何处置已经被聚合过的投毒模型。论文未说明被剔除客户端是否仍会被服务器选入后续轮次、是否可以重新加入信任集合，也未说明是否需要做全局模型回滚或重训。

## 7. 实验设置与主要结果

数据集是 MNIST、Fashion-MNIST、CIFAR-10、CIFAR-100 与 Mini-ImageNet；MNIST 与 Fashion-MNIST 用两层卷积的 CNN（16 与 32 通道、5 乘 5 卷积核、padding 为 2、批归一化、ReLU、2 乘 2 最大池化，再接全连接层映射到 10 类），CIFAR-10 用六层卷积 CNN（3 乘 3 卷积核、padding 为 1、三组 32、64、128 通道），CIFAR-100 用深度相同但宽度加倍的模型，Mini-ImageNet 用 64、128、256 通道的三组卷积块加自适应平均池化到 4 乘 4、dropout 与两层全连接做 100 类分类（第 VI-A-a 节）。联邦设置为 N = 60、K = 10、T = 200，客户端数据划分可以是 IID 或非 IID，非 IID 设置按参考文献 [35] 构造（第 VI-A-b 节）。攻击基线包括标签翻转、标签翻转加 PoisonGAN、轻噪声叠加、重噪声叠加、椒盐（salt and pepper, SAP）噪声叠加与余弦噪声叠加，参数分别是：轻噪声为均值 0、方差 0.1 的高斯噪声，重噪声为均值 0、方差 0.3 的高斯噪声，SAP 噪声对每张图 30% 的像素加噪且"盐"与"胡椒"比例为 0.5，余弦噪声振幅为 2、频率为 0.5；VagueGAN 默认 κ = 0.2、E = 600，生成与真实数据等量的投毒数据并整体替换原始数据（第 VI-A-c 节）。恶意比例 α 从 5% 到 30%，结果取 10 次运行的平均（第 VI-B-a 节）。

攻击效果方面，表 I 给出全部数据集的测试准确率。举几个明确数值：MNIST 在 IID 且无攻击时为 98.73%，VagueGAN 在 α 为 5%、10%、20%、30% 时分别为 98.61%、98.35%、97.84%、97.46%；Fashion-MNIST 在 IID 且无攻击时为 87.97%，VagueGAN 对应为 87.34%、86.79%、85.87%、84.77%；CIFAR-10 在 IID 且无攻击时为 76.28%，VagueGAN 对应为 74.94%、74.02%、73.16%、71.93%；CIFAR-100 在 IID 且无攻击时为 55.71%，VagueGAN 对应为 51.53%、48.30%、42.35%、39.38%；Mini-ImageNet 在 IID 且无攻击时为 49.25%，VagueGAN 对应为 46.12%、41.16%、35.22%、29.35%（表 I）。论文总结说 VagueGAN 在多数情形下取得更好的攻击效果，其真正优势是有效性与隐蔽性的权衡（第 VI-B-a 节）。隐蔽性方面，图 9 显示 VagueGAN 的投毒模型与良性模型距离最短，图 10 显示其准确率波动最小。

防御效果实验的设置为 N = 20、K = 5、T = 200，数据集为 IID 的 Fashion-MNIST，主要表格取 α = 20%（第 VI-E 节）；MCD 参数为 λ1 = 1、λ2 = 2、T′ = 80、Ω1 = 4、Ω2 = 2（第 VI-A-d 节）。表 IV 给出 MCD 在不同恶意比例下检出的恶意客户端数与准确率提升：在 α 为 5%、10%、20%、30%（对应 M 为 1、2、4、6）时，标签翻转与 PoisonGAN 场景检出 1、2、4、6 个，轻噪声场景检出 1、1.9、3.8、5.6 个，重噪声与 SAP 场景分别检出 1、2、4、6 个与 1、2、3.9、5.7 个，VagueGAN 场景检出 1、2、3.9、5.8 个；应用 MCD 后 VagueGAN 场景的准确率为 87.94%（提升 0.62）、87.89%（提升 1.11）、87.86%（提升 1.99）、87.89%（提升 3.12），无攻击基线 a_t 为 87.97%（表 IV）。作为对比，PCA 在 VagueGAN 场景只检出 0.1、0.2、0.6、0.9 个客户端，准确率为 87.34%（提升 0）、86.79%（提升 0）、86.01%（提升 0.14）、84.97%（提升 0.20）（表 V）；UMAP 只检出 0、0、0.2、0.7 个，准确率为 87.34%（提升 0）、86.79%（提升 0）、85.96%（提升 0.09）、84.91%（提升 0.14）（表 VI）。表 VII 汇总显示只有 MCD 对全部六种攻击（标签翻转、PoisonGAN、轻噪声、重噪声、SAP 噪声、余弦噪声、VagueGAN）都标记为可防御，PCA、UMAP、CONTRA、DnC、LoMar、FedDMC 对 VagueGAN 都标记为不可防御。

权衡实验方面，图 11 显示 κ 从 0.1 增大到 0.4 时攻击有效性上升、隐蔽性下降（设置是 Fashion-MNIST、IID、α = 20%、E = 400）；图 12 显示 E 增大时有效性逐渐下降、隐蔽性逐渐上升（α = 20%）。论文建议 E 取收敛轮数 e_lim 的一半，并给出 e_lim 为 MNIST 600、Fashion-MNIST 1000、CIFAR-10 与 CIFAR-100 1600、Mini-ImageNet 2000（第 VI-C-b 节）。监督与无监督 VagueGAN 的对比显示两者攻击效果相当，无监督版本更稳定（第 VI-D 节、图 13(b)、图 14）。

## 8. 开销

防御侧，MCD 的开销论文只给出定性描述：它直接复用服务器为联邦聚合已经收集的本地模型，因此没有额外的模型收集开销；它只使用降维后的两个指标而不是原始高维模型，从而避免服务器的高存储负载；它使用轻量异常检测算法；它每隔数十轮（实验中 T′ = 80 轮）运行一次而不是每轮运行（第 V-B 节末、第 V 节）。论文未报告 MCD 的具体计算量、通信量或存储量数值，也未报告它给服务器带来的绝对时间开销。

攻击侧，论文声称 VagueGAN 相对容易训练、不需要等到收敛到纳什均衡、全数据集训练需要更少轮数，并且只需要一次性成本，即从可用数据集建立一次损失函数之后就可以生成任意数量的投毒数据（第 IV-F 节）。具体时间数值在图 13(a) 中给出，为 36、82、104、138、216、438、667、904 秒，覆盖 E 取 200、400、600、800 的两种情况；论文正文只说明无监督 VagueGAN 的时间开销大于监督版本，且随训练轮数增加两者差距变大，正文没有把每个数值逐一对应到具体方法与具体 E。分析：图 13(a) 的数值配对关系需要从图中读取，正文未逐条说明。测试硬件为 GPU RTX 3090（24GB）与 12 vCPU Intel Xeon Platinum 8255C（第 VI-D 节）。攻击的通信开销论文未报告；防御的通信开销论文也未报告。

## 9. 假设、局限与自适应攻击

方法成立所依赖的假设如下。

服务器完全诚实且不可攻击，通信链路可靠，攻击者只能操作被控客户端，无法访问服务器与其他客户端的数据或模型（第 III-B-b 节）。系统中至少存在一个投毒攻击者（第 III-B-a 节）。服务器能够获得被选中客户端上传的完整本地模型，并能在多个轮次上保存这些模型以计算一致性指标（第 V-B-a 节）；论文没有考虑安全聚合、加密上传或差分隐私噪声遮挡这一视图的情形，论文未说明这些情形下的表现。存在一个 100% 安全、免疫攻击的第一基准客户端，论文举例说可以由服务器自己训练一个本地模型充当该客户端，并且要有足够多的客户端落在 Ω1 与 Ω2 定义的邻域内以组成 Cbase（第 V-B-b 节）；论文未说明服务器可信数据的来源与规模。信任集合 Ctr 初始化为全体客户端，被识别出的客户端只出不进（算法 3）；论文未说明是否存在恢复机制。MCD 的有效性依赖"攻击者持续使用同一个 VagueGAN 模型"这一条件（第 V 节开头），以及 GAN 输出一致性这一现象（第 V-A 节）。攻击侧依赖恶意客户端拥有本地数据集与本地训练过程的全部权限，能在联邦训练前训练 GAN 并替换数据集；默认攻击生成与真实数据等量的投毒样本以保证公平比较（第 IV-B 节、第 VI-A-c 节）。攻击还依赖生成模型在本地数据上可训练，无监督变体是为攻击者拿不到标签信息的情形准备的（第 IV-E 节）。论文未说明攻击者是否知道 MCD 的存在及其参数 T′、δ、λ1、λ2、Ω1 与 Ω2，也未说明攻击者是否知道服务器使用了基准客户端机制。

论文自述的局限有：如果攻击者采用更动态版本的 VagueGAN 或者把它与更复杂的自适应攻击策略结合，MCD 的鲁棒性会面临明显更大的挑战（第 VI-E-b 节）；MCD 所依赖的模型一致性在攻击实现方式变化时（例如自适应攻击策略）可能不再成立（第 VII 节）；未来工作需要研究没有这种一致性缺陷的更先进生成模型（第 VII 节）。论文明确说本研究关注投毒数据的影响，因此聚焦于攻击者持续使用同一个 VagueGAN 模型的情形（第 VI-E-b 节）。

关于自适应攻击者，论文没有做任何自适应攻击实验，自适应攻击只作为威胁与未来工作被讨论（第 VI-E-b 节、第 VII 节），因此 evaluates_adaptive_attacker 记为 false。

分析：MCD 的阈值取中位数的 δ 倍，这种设计只在恶意客户端的异常度不能主导中位数时才合理，论文只测试到 α = 30% 的恶意比例，没有讨论多数客户端恶意或大规模串谋时的行为。分析：论文对 PCA、UMAP、CONTRA、DnC、LoMar、FedDMC 的复现参数由作者自行设定，例如 LoMar 用 K = 2 的 K-means、FedDMC 最小簇大小为 2，这些设置可能与原论文默认设置不同，因此表 VII 关于这些方法失效的结论需要谨慎解读。

迁移到联邦 LoRA 微调时可能不成立的假设如下，全部是分析。

第一，论文的"本地模型"是全参数 CNN，MCD 把参数向量拼接后做 PCA；在联邦 LoRA 微调中客户端上传的是低秩增量矩阵，不同客户端的秩、目标模块集合与参数排布可能不一致，直接拼接成统一向量做 PCA 这一前提需要重新验证。

第二，VagueGAN 是 MLP 结构的条件 GAN，生成的是图像样本；在联邦大模型 LoRA 微调中要毒化的是文本或对话数据，论文没有给出文本域的生成方法，"模糊数据"这一攻击思想能否迁移到文本域需要重新设计。

第三，MCD 需要一个 100% 安全的第一基准客户端，论文举例是服务器自己训练一个本地模型；联邦大模型微调中服务器通常不持有可训练的根数据集，这一条依赖很可能直接失效。

第四，论文的攻击目标是让全局模型分类准确率下降，而联邦大模型 LoRA 微调最关心的是后门、越狱与安全对齐破坏；质心指标与足迹指标是否对这类行为层面的投毒敏感，论文未研究。

第五，MCD 直接复用原始本地模型；如果联邦大模型系统采用安全聚合、差分隐私噪声或压缩上传，足迹指标可能被噪声或压缩误差淹没，这一情形论文未考虑。

第六，论文的防御周期为 T′ = 80 轮，实验为 T = 200 轮；联邦大模型微调常见的是客户端更少、轮次更短的设置，固定 80 轮的窗口可能收集不到足够多的更新样本来估计足迹指标，论文未讨论窗口长度与可用更新数之间的关系。

## 10. 对防护库设计的含义

分析：采集底座需要在服务器收到更新时保存每个客户端的完整模型或适配器增量，并按客户端、按轮次建立索引，同时记录参与掩码（该客户端本轮是否被选中），因为 MCD 明确要求未选中轮次记为 NULL；这是一项通用需求，任何跨轮一致性检测都需要它。

分析：采集底座需要支持"跨轮滑动窗口加基线锚点"这一数据视图，即在一个长度为 T′ 的窗口内对每个客户端计算质心与离散度，并保留至少一个干净基准（服务器根数据集训练的模型或一组可信客户端）；这一需求是 MCD 特有的，但它也提示库应把"可信根数据"作为一等公民显式建模，因为它是很多检测插件的前置条件。

分析：插件机制需要允许检测插件声明自己的输入是"逐客户端逐轮模型"而不是逐样本数据，并允许它在服务器聚合前返回逐客户端的异常分与阈值判定；MCD 的两个指标、阈值 δ 乘中位数以及 Ω1、Ω2 邻域筛选都属于这篇论文特有的算法内容，应作为可替换的插件实现，而不是写死进底座。

分析：干预接口需要在聚合前支持按客户端粒度的剔除，并且要能把被剔除的客户端持久地排除在后续轮次的聚合之外（跨轮状态），因为论文的防御效果来自"忽略其后续更新"；论文没有设计重新加权、裁剪、加噪或模型回滚，因此库不必为这篇论文实现这些动作，但应保留这些接口以便其他插件使用。

分析：为了检测这篇论文的攻击，库需要在适配器更新上提供与 MCD 相同的两个统计视图，并额外记录更新是否由同一个生成过程反复产生；论文的攻击痕迹本质上来自多轮更新之间的过高一致性，这一观察可以抽象成通用的"跨轮一致性"检测原语，而具体的二维 PCA 投影与欧氏距离计算属于这篇论文的具体实现。

分析：库还应当提供自适应攻击的评测接口，因为这篇论文只讨论了自适应攻击而没有评测，任何声称能防御此类投毒的实现都需要在"攻击者知道防御参数并改变生成策略"的条件下重新验证，而这一条件超出了论文的实验范围。

## 11. 原文依据

以下引文均逐字摘自全文，括号内为所在章节与它支撑的论断。

1. 第 VI-A-a 节："We take image data as an example to evaluate the poisoning capability of our VagueGAN, but the idea of “vague data” is not limited to this specific data type." ——支撑第 1 节关于本文研究的是传统联邦学习图像分类、而非联邦大模型微调的判断。

2. 第 III-B-a 节："In an FL system, we assume that there exists at least one data poisoning attacker. The attacker’s primary goal is to degrade the performance of the global model as much as possible." ——支撑第 2 节关于攻击者身份与无目标破坏目标的判断。

3. 第 III-B-b 节："First, the attacker can gain control of one or more benign clients or disguise itself as a benign client. Second, the attacker can gain all the privileges of each controlled client, e.g., local dataset, local model training process, etc." ——支撑第 2 节关于攻击者能力的判断。

4. 第 IV-B 节："Before federated training starts, the malicious client trains the VagueGAN model on its local dataset using the loss function defined in Eq. (1)." ——支撑第 3 节关于攻击入口位于本地数据准备阶段的判断。

5. 第 IV-A 节："We use a suppression factor κ ∈(0, 1) to limit the generation ability of the generator G. The larger κ is, the more restrictive it is on the generation ability." ——支撑第 4 节关于式 (1) 中抑制因子作用与有效性和隐蔽性权衡的判断。

6. 第 V-A 节："The poisoned models uploaded by the same malicious client are more densely distributed within a smaller region. This is mainly caused by the consistency of GAN outputs, as GAN-generated data usually have a certain degree of data feature similarity." ——支撑第 4 节与第 5 节关于足迹指标依据与攻击痕迹的判断。

7. 第 V 节："Our defense method is effective when the same VagueGAN model is consistently applied by the attacker, though the idea of VagueGAN still has great potential to deliver undetectable attacks if implemented in varying settings." ——支撑第 9 节关于 MCD 成立依赖"同一 VagueGAN 被持续使用"这一假设的判断。

8. 第 V-B-b 节："Firstly, MCD maintains a first baseline client (for instance, the server acts as a such client to train a local model). This client is considered 100% secure and immune to attacks" ——支撑第 5 节关于检测需要干净基准客户端的判断。

9. 第 V-B-d 节："MCD then marks every client with a client abnormality value larger than the threshold as a malicious client. If MCD detects a malicious client, it will be removed from the trusted client set Ctr." ——支撑第 6 节关于干预动作是服务器端剔除客户端的判断。

10. 第 VI-E-b 节："Nonetheless, if the attacker were able to adopt a more dynamic version of VagueGAN or integrate it with more sophisticated adaptive attack strategies, the robustness of MCD would be subject to significantly greater challenges." ——支撑第 9 节关于论文未评估自适应攻击、只把它列为威胁的判断。

```json
{
  "key": "sun2024vaguegan",
  "title": "A Model Consistency-Based Countermeasure to GAN-Based Data Poisoning Attack in Federated Learning",
  "year": 2024,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "每个被选中客户端每轮上传的完整本地模型参数，MCD 的原始输入", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "客户端参与掩码，即该客户端在防御周期内哪些轮被选中，未选中时对应模型记为 NULL", "where": "server_receive", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "第一基准客户端（论文举例为由服务器自己训练一个本地模型）在周期内的质心指标与足迹指标", "where": "server_post_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "基准客户端集合 Cbase 内各客户端的指标以及由它们平均得到的基线值", "where": "server_post_aggregate", "granularity": "client", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "全局模型在测试数据集上的准确率，论文用于度量攻击有效性与防御效果，MCD 判定本身不依赖它", "where": "evaluation", "granularity": "round", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": false}
  ],
  "interventions": ["exclude_client"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务器完全诚实且不可攻击，通信链路可靠，攻击者只能操作被控客户端，无法访问服务器与其他客户端的数据或模型",
    "系统中至少存在一个数据投毒攻击者",
    "服务器能获得被选中客户端上传的完整本地模型，并能跨多个轮次保存它们以计算一致性指标",
    "存在一个被认定为 100% 安全、免疫攻击的第一基准客户端（论文举例为服务器自己训练一个本地模型），且有足够多客户端落在 Ω1、Ω2 定义的邻域内组成 Cbase",
    "信任客户端集合初始为全体客户端，被识别出的客户端只出不进",
    "攻击者持续使用同一个 VagueGAN 模型，因此 GAN 输出一致性现象成立",
    "攻击者拥有被控客户端的本地数据集与本地训练过程，能在联邦训练开始前训练生成模型并整体替换本地数据集",
    "攻击生成与真实数据等量的投毒样本，以保证与其他攻击方法的公平比较"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "VI-A-a", "supports": "第 1 节：本文研究传统联邦学习图像分类，不涉及大模型或 LoRA", "text": "We take image data as an example to evaluate the poisoning capability of our VagueGAN, but the idea of “vague data” is not limited to this specific data type."},
    {"section": "III-B-a", "supports": "第 2 节：攻击者身份与无目标破坏目标", "text": "In an FL system, we assume that there exists at least one data poisoning attacker. The attacker’s primary goal is to degrade the performance of the global model as much as possible."},
    {"section": "III-B-b", "supports": "第 2 节：攻击者能力限于被控客户端的全部权限", "text": "First, the attacker can gain control of one or more benign clients or disguise itself as a benign client. Second, the attacker can gain all the privileges of each controlled client, e.g., local dataset, local model training process, etc."},
    {"section": "IV-B", "supports": "第 3 节：攻击入口位于联邦训练开始前的本地数据准备阶段", "text": "Before federated training starts, the malicious client trains the VagueGAN model on its local dataset using the loss function defined in Eq. (1)."},
    {"section": "IV-A", "supports": "第 4 节：式 (1) 中的抑制因子及其对有效性与隐蔽性的权衡作用", "text": "We use a suppression factor κ ∈(0, 1) to limit the generation ability of the generator G. The larger κ is, the more restrictive it is on the generation ability."},
    {"section": "V-A", "supports": "第 4 节与第 5 节：足迹指标所依据的 GAN 输出一致性，以及攻击留下的可观测量痕迹", "text": "The poisoned models uploaded by the same malicious client are more densely distributed within a smaller region. This is mainly caused by the consistency of GAN outputs, as GAN-generated data usually have a certain degree of data feature similarity."},
    {"section": "V", "supports": "第 9 节：MCD 有效性的关键前提是攻击者持续使用同一个 VagueGAN 模型", "text": "Our defense method is effective when the same VagueGAN model is consistently applied by the attacker, though the idea of VagueGAN still has great potential to deliver undetectable attacks if implemented in varying settings."},
    {"section": "V-B-b", "supports": "第 5 节：检测需要干净参考，即被认定为 100% 安全的第一基准客户端", "text": "Firstly, MCD maintains a first baseline client (for instance, the server acts as a such client to train a local model). This client is considered 100% secure and immune to attacks"},
    {"section": "V-B-d", "supports": "第 6 节：干预动作是把异常客户端从信任集合中移除", "text": "MCD then marks every client with a client abnormality value larger than the threshold as a malicious client. If MCD detects a malicious client, it will be removed from the trusted client set Ctr."},
    {"section": "VI-E-b", "supports": "第 9 节：论文未评估自适应攻击，只把它列为对 MCD 的更大挑战", "text": "Nonetheless, if the attacker were able to adopt a more dynamic version of VagueGAN or integrate it with more sophisticated adaptive attack strategies, the robustness of MCD would be subject to significantly greater challenges."}
  ]
}
```
