# li2026thesis：基于混合专家模型的联邦学习隐蔽攻击方法研究

## 1. 基本信息

**场景**：传统联邦学习（Federated Learning，FL），且论文明确限定为横向联邦学习（horizontal federated learning），任务为图像分类。论文第 2.1.3 节写明"本文主要聚焦于横向联邦学习场景下的安全问题"。全文没有涉及大语言模型、Transformer 或参数高效微调（Parameter-Efficient Fine-Tuning，PEFT），也没有 LoRA（Low-Rank Adaptation）相关内容。

**训练阶段**：标准 FedAvg（Federated Averaging）多轮流程，即服务器下发全局模型、客户端本地训练、客户端上传本地模型参数、服务器平均聚合（第 2.1.3 节，算法 2-1，公式 2-3、2-4）。攻击发生在客户端的本地数据准备阶段与本地训练阶段。

**论文类型**：攻击（attack）。论文提出了两种攻击方法 MoEGAN 与 SMA，并在第 3.6 节和第 4.6 节分别给出针对性的防御思路，但这两节只有机理描述和公式，没有实验验证（论文未报告这两套防御的任何实验结果）。

**模型与数据规模**：使用三个图像数据集（第 3.5.1 节，表 3-4）。Fashion-MNIST 为 10 类、28×28×1、60000 张训练样本与 10000 张测试样本；CIFAR10 为 10 类、32×32×3、50000 张训练样本与 10000 张测试样本；RTFD 为 2 类钢轨表面缺陷图像、224×224×3、883 张训练图像与 116 张测试图像。联邦主任务模型随数据集定制：Fashion-MNIST 使用含两个卷积层和批量归一化的卷积神经网络；CIFAR10 使用含六个卷积层、批量归一化和两个全连接层的更深结构；RTFD 使用预训练 ResNet-18，冻结前八层参数并接自定义分类头。联邦拓扑方面，Fashion-MNIST 与 CIFAR10 实验使用 N=60 个客户端、每轮激活 K=10 个、共 T=200 轮；RTFD 实验使用 N=20、K=5，其余不变（第 3.5.1 节）。生成器与鉴别器结构见表 3-2 与表 3-3，其中 MoELatent 模块输入输出维度均为 100（表 3-2 第 1 行），鉴别器的类别判别分支输出维度为 11×1×1（表 3-3 第 12 行）。

## 2. 威胁模型

**攻击者身份**：恶意客户端。第 3.2.2 节写明攻击者"通过劫持、入侵或恶意注册等手段，获取系统中少部分节点的控制权，使其转化为恶意客户端"。SMA 在此基础上进一步假设攻击者能伪造大量虚拟身份（女巫节点，Sybil），第 4.2 节写明"假设在 N 个初始参与方中，原生恶意客户端的占比为 α，即原生恶意节点的总数为 M = N × α"，且"每个原生恶意客户端均可在系统中额外虚拟出 v 个伪造的女巫节点"，恶意节点总规模增至 M_A = M × v + M。

**占比或数量**：MoEGAN 实验扫描的恶意客户端占比 α 取 0%、5%、10%、20%、30%（表 3-5 至表 3-7）；MCD 隐蔽性实验取 α = 20%（第 3.5.3 节）；SMA 攻击性能实验的 α 从 5% 到 20% 以 5% 为步长，并约束总恶意节点数 M_A ≤ N × 50%（第 4.5.2 节）；SMA 隐蔽性实验取 N = 10、α = 20%、v = 3（第 4.5.3 节）。

**能力（能改什么）**：第 3.2.2 节写明对沦陷节点"攻击者拥有绝对的操作权限：可以任意篡改、清洗或伪造本地私有数据集，并能全盘掌控本地模型的训练超参数与反向传播过程"。第 4.2 节补充女巫节点"不仅可以随意篡改本地的训练样本与标签，还能直接修改底层的模型权重与梯度参数"，并具备"全局调度能力，能够指挥所有受控的女巫节点在特定的通信轮次发起高度同步的联合行动"。攻击者不能攻陷服务器、不能篡改聚合算法（第 3.2.2 节："本章假定中央服务器是绝对诚实且具备极高安全防御等级的，攻击者无法直接攻陷服务器篡改聚合逻辑"）。

**知识（知道什么）**：能"毫无保留地获取服务器下发的全局模型参数、网络架构细节以及当前的全局通信轮次等公共情报"（第 3.2.2 节）。第 4.2 节给出更严格的设定："攻击者无法直接获取中心服务器所采用的具体聚合算法与底层防御细节，也无法窥探网络中其他真实诚实客户端的私有数据分布和模型更新参数"，但对自身控制的节点有完全白盒掌控权。第 3.2.2 节同时写明"攻击者绝对无法跨节点窥探其他良性客户端的私有数据集，也无权获取良性客户端上传的合法模型梯度"。

**目标**：无目标破坏（untargeted）。第 3.2.2 节写明"攻击者的首要目标是最大化地削弱最终全局模型的泛化能力与预测精度"。第 4.2 节的攻击者目标同时提到"也涵盖迫使模型针对特定触发条件输出攻击者预设的错误结果"，但第 3 章与第 4 章的全部实验只测量全局模型在主任务测试集上的精度下降，论文没有做后门或定向攻击实验。攻击者同时追求隐蔽性，即"维持极高的隐蔽性、确保恶意更新不被过滤，是攻击成功的先决条件"（第 3.2.2 节）。

**防御者是谁、能看到什么、信任什么**：防御者是中心服务器。第 4.2 节写明"假设联邦学习的中心服务器是完全诚实且受信任的——其仅负责分发模型、持有纯净的测试数据并执行模型聚合操作"。服务器能看到客户端上传的模型更新（参数传输匿名，第 4.4.3 节），持有纯净测试数据，但看不到客户端的本地原始数据与本地训练过程。第 3.6 节提出的防御额外假设"服务器在本地维护一小规模的干净验证集 D_val"；第 4.6 节提出的防御额外假设"服务器预先维护一个极小比例的、经过严格物理身份验证且确保安全的良性客户端集合，将其作为'可信锚点'"。服务器信任可信锚点集合中的客户端。

## 3. 攻击入口与流程位置

**攻击入口**：本地数据准备与本地训练过程。

**MoEGAN 的具体操作步骤**（第 3.4.2 节，算法 3-1）：

1. 攻击者在恶意客户端 c_m 本地部署 MoEGAN 的生成器 G 与鉴别器 Disc（算法 3-1 第 4 行）。
2. 在本地干净数据集 D^train_m 上，按对抗损失与辅助分类损失交替优化 G 和 Disc 共 E_pGAN 轮（算法 3-1 第 5 至 7 行）。这一步发生在联邦通信开始之前，属于本地数据准备阶段。
3. 连续采样随机噪声向量 z 与随机分布的类别标签 y_random，输入训练好的生成器 G，直接生成中毒数据集 D^poison_m，"并替代本地训练数据"（算法 3-1 第 8 至 10 行）。第 3.4.2 节原文写明"这些生成的恶意样本被组合成中毒数据集 D^poison_m，并直接替换该客户端本地的原始训练数据"。
4. 在联邦投毒执行阶段，恶意客户端在第 t 轮接收全局模型 w_t 并以此初始化本地模型（算法 3-1 第 15 至 16 行）。
5. 在中毒数据集 D^poison_m 上执行 E_plocal 轮局部参数更新 w_{t,m} ← w_{t,m} − η∇L(w_{t,m}; D^poison_m)（算法 3-1 第 17 至 20 行）。
6. 将中毒局部模型参数 w^poison_{t+1,m} 上传至中心服务器，参与全局聚合（算法 3-1 第 21 至 22 行）。

**SMA 的具体操作步骤**（第 4.4.2、4.4.3 节，算法 4-1）：

1. 大女巫节点 C_m 虚拟出 v 个小女巫节点 {S_{m,1}, S_{m,2}, …, S_{m,v}}（算法 4-1 第 3 行）。这一步进入的位置是联邦网络的成员注册与准入环节，论文第 4.4.4 节说明这依赖"无许可准入或弱身份认证"。
2. 大女巫将原始数据集 D_m 随机等分为 v 个互不相交的子集 {d_{m,1}, d_{m,2}, …, d_{m,v}} 并分发（算法 4-1 第 4 行）。
3. 每个小女巫仅在本地部署生成器 G_j，仅利用子集 d_{m,j} 做对抗训练，"激活第 j 个专家网络 Expert_j"（算法 4-1 第 6 至 8 行）。
4. 小女巫用训练好的 G_j 生成专属中毒数据集 d^poison_{m,j}（算法 4-1 第 9 行）。
5. 大女巫收集所有收敛的专家网络权重，实例化全局生成器 G_recomb 并融合专家权重，"在无梯度状态下，将门控层的权重和偏置置零，实现无偏等权融合"（算法 4-1 第 12 至 14 行），再生成大女巫专属全局中毒数据集 D^poison_m（算法 4-1 第 15 行）。
6. 在每轮联邦通信中，大女巫与小女巫各自用专属中毒数据集做 E_plocal 轮本地更新并上传参数（算法 4-1 第 17 至 29 行；公式 4-1 描述小女巫更新，公式 4-2 描述大女巫更新）。
7. 服务器按标准等权平均聚合，聚合式见公式 4-4，其中本轮 K 个客户端包含 N_h 个诚实参与方、N_a 个合谋小女巫节点以及 1 个大女巫节点。

**不涉及的入口**：论文没有在更新上传前做后处理（没有缩放、投影或拼装操作，算法 3-1 与算法 4-1 都是训练后直接上传）；没有篡改服务器聚合逻辑（服务器被假设为绝对诚实）；没有在全局模型下发或评估与部署环节做手脚。第 4.4.4 节特别说明 SMA 是"在不干预联邦学习底层通信协议与聚合规则的前提下"实施的。

分析：第 4.4.3 节的公式 4-4 把 K 分解为 N_h + N_a + 1，这隐含"本轮被选中的客户端中恰好只有 1 个大女巫"这一实验设定，而不是一般性的威胁模型假设。论文没有说明攻击者如何提高女巫节点被抽样命中的概率，只在第 2.2.2 节定性地说"由于女巫节点的基数极其庞大，它们被选中参与联邦训练的概率会被人为拉高"。

## 4. 方法原理

**MoEGAN（第 3.4.1 与 3.4.3 节）**。核心思想是在生成器的隐空间（latent space）中引入混合专家（Mixture of Experts，MoE）结构，用多个专家分支的加权组合替代单一网络的隐空间映射，从而打破单一生成器输出特征的分布一致性。

生成器包含三个主要阶段（第 3.4.1 节）：条件融合阶段用嵌入层把类别标签 y 映射到与噪声相同的隐空间维度，并用元素级乘法融合，即 z = ε ⊙ Emb(y)；特征变换阶段把融合后的隐变量送入 MoELatent 模块；上采样生成阶段把 MoE 输出重塑为张量，经过连续转置卷积层，每层后接批归一化和 ReLU 激活函数，最后一层使用 Tanh 激活函数。

MoELatent 模块由 E 个并行专家网络和一个门控网络组成，每个专家网络由全连接层和 ReLU 激活函数构成（第 3.4.1 节）。第 3.4.3 节公式 3-2 给出形式化表达：门控权重 g(z) = Softmax(W_g z)，第 i 个专家的输出 E_i(z) = ReLU(W_{e,i} z + b_{e,i})，MoE 层聚合输出 z_out = Σ_{i=1}^{K} g_i(z) E_i(z)。第 3.4.1 节强调"专家权重的分配并非固定，而是由输入的随机噪声与标签嵌入共同决定的"，论文把这一机制称为"基于噪声驱动的动态专家加权策略"。

鉴别器（第 3.4.1 节）由多个包含标准卷积、批归一化、LeakyReLU 激活函数及 Dropout 的卷积块构成，经自适应平均池化后进入双分支：真伪判别分支通过 1×1 卷积和 Sigmoid 激活函数输出样本为真实的概率，类别判别分支通过 1×1 卷积和 LogSoftmax 激活函数做多分类预测。损失函数由对抗损失 L_adv（公式 3-1a）与辅助分类损失 L_aux（公式 3-1b）组成，第 3.4.3 节公式 3-3c 给出联合优化目标 G* = argmin_G max_D (L_adv + λL_aux)。

第 3.4.3 节用公式 3-4 说明 MoE 带来的多峰拟合能力：P_G(x|c) = Σ_{i=1}^{K} P(E_i|z) P_G(x|c, E_i(z))，论文称生成分布因此"具备了类似高斯混合模型（GMM）的多峰拟合能力"，能够在多个不连续子区域中寻找最优映射。

**SMA（第 4.4.1 至 4.4.3 节）**。核心思想是把 MoEGAN 的专家训练任务拆分给多个女巫节点，用"大女巫统筹隐蔽 + 小女巫分散攻击"的分层结构同时获得攻击力与异质性。

第 4.4.1 节把框架分为两部分：第一部分是拓扑与数据裂变，大女巫把真实数据切分为多个无交集子集分发给小女巫；第二部分是基于 MoE 的分布式数据生成，每个小女巫仅激活并训练 MoE 中的一个特定专家网络，大女巫作为全局组合单元回收所有专家网络并重组为完整 MoE 生成器。

第 4.4.2 节给出小女巫的本地更新式（公式 4-1）：w^poison_{t,m,j} = w̃_{t−1} − η·∇L(w̃_{t−1}, D^poison_{m,j})。第 4.4.3 节给出大女巫的本地更新式（公式 4-2）：w^poison_{t,m} = w_{t−1} − η·∇L(w_{t−1}, D^poison_m)。

第 4.4.3 节的核心设计目标是让女巫之间的参数相似度低于检测阈值，用公式 4-3 表示：sim(Δw_{t,m,i}, Δw_{t,m,j}) = (Δw_{t,m,i}·Δw_{t,m,j}) / (‖Δw_{t,m,i}‖‖Δw_{t,m,j}‖) < τ_detect，其中 Δw_{t,m,j} = w^poison_{t,m,j} − w_{t−1}。论文把这一设计称为"去相似化"设计，并称其使女巫节点"如同来自不同 non-IID 数据分布的正常客户端"。

分析：摘要与第 1.3 节反复强调"与经典 MoE 架构中传统的门控机制不同，本文针对数据投毒任务专门设计了定制化的专家选择与路由逻辑"，但第 3.4.1 节与第 3.4.3 节实际给出的门控计算就是标准的线性变换加 Softmax 加权融合（公式 3-2），差别只在于门控输入包含随机噪声与标签嵌入，且 SMA 阶段把门控层权重和偏置置零做等权融合（算法 4-1 第 14 行）。论文没有给出"定制化路由逻辑"的独立公式定义。

## 5. 检测或防御所需的数据

### 5.1 攻击留下的可观测量（论文报告）

- **客户端上传的完整本地模型参数（逐客户端、逐轮）**，在服务器收到更新时采集。论文用主成分分析（Principal Component Analysis，PCA）把高维更新投影到二维空间，观察良性更新与恶意更新的分布形态（第 3.5.3 节，图 3-4 至图 3-6）。图 3-4 至图 3-6 中黄色圆点代表良性客户端上传的局部模型，蓝色叉号代表恶意客户端上传的局部模型。
- **每个客户端的中心指标 θ̄^(2)_{f,i} 与覆盖指标 d̄_{f,i}（逐客户端、逐轮）**，以及由它们与全局参考基准 θ^base_f、d^base_f 计算出的异常度 h_{f,i}（公式 3-6）。表 3-8 至表 3-10 给出 CIFAR-10、IID、α = 20% 条件下各客户端的取值。论文的结论是：标签翻转、轻高斯噪声与 PoisonGAN 攻击会出现中心指标异常；椒盐噪声叠加攻击的中心指标与覆盖指标均有异常；VagueGAN 中心指标没有异常但因模型一致性导致覆盖指标异常；MoEGAN 中心指标和覆盖指标均无异常。
- **跨轮的模型演化轨迹（逐客户端、逐轮，需要跨轮历史）**。图 3-7 对比了 VagueGAN 恶意客户端、MoEGAN 恶意客户端与良性客户端在多轮通信中的 PCA 投影。论文报告 VagueGAN 的不同轮次模型参数"呈现出显著的聚集特征"，而 MoEGAN 的分布"与良性客户端高度吻合，同样呈现出弥散和不规则的特征"。
- **客户端的历史累积梯度与两两余弦相似度（逐客户端、逐轮，需要跨轮历史）**。第 4.5.3 节公式 4-5 定义 H_i^(t) = Σ_{τ=1}^{t} Δw_i^(τ)，并计算 cs^(t)_{i,j}。图 4-9 是 T−1 轮的相似度热力图。
- **全局模型在测试集上的精度（逐轮、模型级）**，在评估时采集。这是第 3.5.2 节与第 4.5.2 节衡量攻击效果的核心指标，按公式 3-5 计算 ΔAcc = Acc_clean − Acc_attack。
- **SMA 特有的可观测量**：小女巫节点之间的成对余弦相似度。图 4-9 报告诚实节点内部相似度"广泛分布在 0.2 到 0.5 之间"，小女巫节点（Sybil 10 至 Sybil 15）之间的相似度"极低，完全淹没在诚实节点的自然波动基线之下"，但大女巫节点 Sybil 2 与 Sybil 4 之间"呈现出极高的相似度"。

**论文声称能绕过的检测**：

- 基于 PCA 降维的特征空间聚类与异常检测（第 3.5.3 节）：论文声称 MoEGAN 在二维投影上与良性更新高度重叠，图 3-4 至图 3-6 用于支持这一论断。
- 基于模型一致性的防御（Model Consistency-Based Defense，MCD，文献 [24]）：表 3-8 至表 3-10 报告 MoEGAN 的中心指标与覆盖指标均无异常，SMA 在表 4-1 中的异常度与正常节点重叠。
- FoolsGold（文献 [15]）的余弦相似度检测：图 4-9 用于支持 SMA 能规避该机制对高相似度集群的捕获。
- 论文在引言与第 1.2.1 节还讨论了 CONTRA 的余弦相似度过滤、FLDetector 的历史行为预测、LoMar 的核密度估计加 k 近邻评分等防御机制，但只在相关工作中引用，没有做实验。

### 5.2 论文第 3.6 节提出的决策一致性防御所需输入

- **服务器本地维护的小规模干净验证集 D_val**。在服务器侧采集与保存，粒度是逐样本。这是干净参考数据，论文未说明其规模。
- **上一轮全局模型参数 w̃_{t−1}**。在服务器聚合后采集，粒度是模型级。
- **客户端本轮提交的模型更新 w_{t,i}**。在服务器收到更新时采集，粒度是逐客户端。
- **由 w̃_{t−1} 与 w_{t,i} 合成的局部模型在 D_val 上的前向输出**。这是额外的前向计算，粒度是逐样本。需要的派生量包括：局部预测分布 p_{t,i}(x)、全局基准预测分布 p_{t,g}(x) = f(x; w̃_{t−1})、正确类别预测概率、最大错误类别预测概率、混淆矩阵 C_{t,i}(y, y′)。服务器还要计算全局基准混淆矩阵 C_{t,g}。
- **三个异常度量**：预测分布的 KL 散度（Kullback-Leibler divergence）Δ^KL_{t,i}（公式 3-10）、平均分类间隔差异 ΔM_{t,i}（公式 3-11a 与 3-11b，其中 M_{t,i}(x) 定义为正确类别预测概率与最大错误类别预测概率之差）、混淆矩阵的 Frobenius 范数差异 F_{t,i} = ‖C_{t,i} − C_{t,g}‖_F（公式 3-12）。
- **综合评分与权重系数**：Score_{t,i} = ω1·Δ^KL_{t,i} + ω2·|ΔM_{t,i}| + ω3·F_{t,i}，其中 ω1、ω2、ω3 为归一化权重系数，论文未给出取值；另有安全阈值 τ 与防除零常数 ε，论文也未给出取值。
- 该防御不需要跨轮历史，只需要上一轮全局模型与本轮更新；需要干净参考数据；需要额外前向计算。论文未报告该防御的计算量测量值。

### 5.3 论文第 4.6 节提出的可信锚点与连带图挖掘防御所需输入

- **经严格物理身份验证的可信锚点集合 C_trust 及其局部更新**。在服务器收到更新时采集，粒度是逐客户端。论文称其"数量极其有限"并构成"信任根"，但未给出具体比例。
- **各锚点的历史累积梯度 H_k^(t)**，用于公式 4-6 的参考梯度 G_ref^(t) = (1/|C_trust|)·Σ_{k∈C_trust} H_k^(t)。需要跨轮历史。
- **全体客户端的历史成对余弦相似度关系矩阵**，由服务器端维护，用于第三阶段的图遍历挖掘。需要跨轮历史。
- **偏离下界阈值 τ_low 与同谋判定阈值 τ_high**，论文未给出取值。
- **每个未知节点本轮更新向量 H_i^(t)** 与参考梯度的余弦相似度 S_{i,ref}（公式 4-7）。粒度是逐客户端、逐轮。

## 6. 干预动作

**攻击侧的动作**：恶意客户端在本地用生成器合成中毒数据集并直接替换本地原始训练数据（算法 3-1 第 10 行）；随后在中毒数据上做本地训练并上传中毒模型参数（算法 3-1 第 17 至 22 行）。SMA 额外在联邦网络准入环节注册虚拟身份。这些动作全部发生在客户端侧。

**论文第 3.6 节防御的干预动作**：在聚合阶段，"对于评分超过预设安全阈值 τ 的客户端（即 Score_{t,i} > τ），直接判定为恶意节点并剔除"；"对于剩余的安全客户端，基于评分的倒数分配聚合权重 λ_{t,i}"，权重公式为 λ_{t,i} = (1/(Score_{t,i} + ε)) / Σ_{j=1}^{K} (1/(Score_{t,j} + ε))（公式 3-13a），全局模型按 w̃_t = w̃_{t−1} + Σ_{i=1}^{K} λ_{t,i} w_{t,i} 更新（公式 3-13b）。动作发生在服务器聚合阶段，包含剔除客户端与重新加权两类操作。

**论文第 4.6 节防御的干预动作**：第二阶段对被判定为高危嫌疑节点的客户端"立即剥夺其参与本轮全局聚合的权重"；第三阶段对通过相似度关联图挖掘出的连带节点簇，"其全局聚合权重将被静态清零或执行指数级衰减"。动作发生在服务器聚合阶段。

**论文没有提出的动作**：没有模型修复或回滚机制，没有对客户端上传更新做裁剪或加噪，没有在客户端侧过滤样本，也没有只报告不干预的模式。

分析：第 3.6 节的防御把客户端上传的 w_{t,i} 当作相对上一轮的增量（以 w̃_{t−1} + w_{t,i} 构造局部模型），并在公式 3-13b 中以 w̃_{t−1} 加上加权和的方式更新全局模型；但第 2.1.3 节与算法 2-1 把 w_{t,i} 定义为客户端本地训练后的模型参数本身，FedAvg 是对参数取平均（公式 2-4）。论文没有解释这两种语义如何统一，库在实现时需要显式约定客户端上传的是绝对参数还是增量。

## 7. 实验设置与主要结果

**数据集**：Fashion-MNIST、CIFAR10、RTFD，规模见表 3-4（第 3.5.1 节）。

**联邦设置**：Fashion-MNIST 与 CIFAR10 用 N=60、K=10、T=200；RTFD 用 N=20、K=5、T=200（第 3.5.1 节）。数据划分同时测试独立同分布（Independent and Identically Distributed，IID）与非独立同分布（non-IID）两种场景，non-IID 的类别倾斜设置参照文献 [52]（第 3.5.1 节）。

**恶意比例**：攻击性能实验扫描 α = 0%、5%、10%、20%、30%（表 3-5 至表 3-7）。MoEGAN 默认设置专家数量 E = 4（第 3.5.2 节）。

**对比方法**：标签翻转（Label Flipping，LF）、轻高斯噪声（Light Gaussian Noise，LGN，均值 μ = 0、方差 σ² = 0.1）、重高斯噪声（Heavy Gaussian Noise，HGN，均值 μ = 0、方差 σ² = 0.3）、椒盐噪声（Salt-and-Pepper Noise，SAP，每张图像随机选取 30% 像素点，盐与椒比例各 0.5）、PoisonGAN（按本地数据集总规模 10% 生成伪造样本后执行标签翻转）、VagueGAN（训练次数 600，生成器抑制因子 0.2），以及本文的 MoEGAN（第 3.5.2 节）。表 3-5 至表 3-7 的数值均为 10 次独立重复实验的算术平均值（第 3.5.2 节）。

**指标**：全局模型测试集精度 Acc，定义精度下降 ΔAcc = Acc_clean − Acc_attack（公式 3-5），ΔAcc 越大表示攻击越强。

**关键结果（表 3-5 至表 3-7）**：

- CIFAR10、IID、α = 30%：无攻击 74.95，MoEGAN 68.53，VagueGAN 70.54，PoisonGAN 71.30，标签翻转 71.12（表 3-6）。
- CIFAR10、non-IID、α = 30%：无攻击 72.73，MoEGAN 67.36，VagueGAN 67.13，PoisonGAN 67.96（表 3-6）。
- Fashion-MNIST、non-IID、α = 30%：无攻击 87.85，MoEGAN 83.26，VagueGAN 83.94，PoisonGAN 84.21（表 3-5）。
- Fashion-MNIST、IID、α = 30%：无攻击 88.47，MoEGAN 85.68，VagueGAN 85.30，PoisonGAN 85.47（表 3-5）。
- RTFD、IID、α = 30%：无攻击 70.78，MoEGAN 65.21，VagueGAN 64.32，PoisonGAN 65.74（表 3-7）。
- RTFD、non-IID、α = 30%：无攻击 69.89，MoEGAN 63.83，VagueGAN 63.07，PoisonGAN 64.68（表 3-7）。

论文的总体结论是 MoEGAN 相比基线攻击性能更优，且"全局模型精度随恶意节点比例 α 的提升而呈现出递减趋势"，"在数据分布为 non-IID 的环境下，中毒攻击对全局模型的负面影响愈发剧烈"（第 3.5.2 节）。

分析：按表 3-5 与表 3-7 的数值，在 Fashion-MNIST 的 IID 设置下 α = 30% 时 VagueGAN 的精度 85.30 低于 MoEGAN 的 85.68；在 RTFD 的 IID 与 non-IID 设置下 α = 30% 时 VagueGAN 的精度分别为 64.32 与 63.07，均低于 MoEGAN 的 65.21 与 63.83。也就是说，在这三组配置下 MoEGAN 并不是破坏力最强的攻击，这与第 3.5.2 节"MoEGAN 展现出显著的攻击性能"的表述存在张力，论文没有对这组数值做单独解释。

**隐蔽性结果（第 3.5.3 节）**：MCD 对比实验在 CIFAR-10、IID、α = 20%、N = 20、K = 5 下进行。表 3-8 至表 3-10 中，MoEGAN 的异常度 h_{f,i} 取值范围与正常节点重叠，全局参考基准为 θ^base_f = (0.05, 0.04)、d^base_f = 4.50（表 3-10）；VagueGAN 的全局参考基准为 θ^base_f = (0.01, 0.01)、d^base_f = 4.40，其部分客户端异常度明显偏高，例如客户端 0 的 h_{f,i} = 7.47、客户端 4 的 h_{f,i} = 6.96、客户端 15 的 h_{f,i} = 6.97（表 3-10）。论文结论是"MoEGAN 中心指标和覆盖指标均无异常"。

**攻击性与隐蔽性权衡（第 3.5.4 节，图 3-8）**：专家数量 E 从 1 增加到 10 时，攻击性 A 从 4.76 降至 1.58，隐蔽性 H 从 0.0943 攀升至 0.6916；最终取 E = 4 以平衡两者。隐蔽性定义为 H = 1/‖u_t − u^p_t‖（公式 3-9），其中 u_t 与 u^p_t 分别是良性更新集合与恶意更新集合在二维 PCA 空间中的质心（公式 3-8）。

**SMA 攻击性能实验（第 4.5.2 节，图 4-3 至图 4-7）**：数据集与联邦设置同第 3.5.1 节。评估 α 影响时 α 从 5% 到 20% 以 5% 为步长，每个大女巫固定虚拟 3 个小女巫；评估 v 影响时固定 α = 10%、v 从 1 增加到 5；约束总恶意节点数 M_A ≤ N × 50%。基线为 MoEGAN。论文报告 SMA 在 IID 与 non-IID 下均优于 MoEGAN，且随 v 增大全局模型精度持续下降。这些结果的数值以图 4-3 至图 4-7 的形式给出，正文没有列出具体数字。

**SMA 隐蔽性实验（第 4.5.3 节）**：以 CIFAR10 为例，N = 10，服务器每轮聚合所有客户端，α = 20%，每个恶意客户端虚拟 v = 3 个女巫节点。表 4-1 报告正常节点的异常度 h_{f,i} 分布在 [0.79, 3.48]，女巫节点的异常度 h_{f,i} 分布在 [0.83, 3.45]。图 4-9 报告诚实节点内部余弦相似度广泛分布在 0.2 到 0.5 之间，小女巫节点之间相似度极低，大女巫节点之间相似度极高。论文结论是 MCD 与 FoolsGold 在面对 SMA 时失效或难以触发惩罚。第 4.5.3 节在此处的文字写的是验证"SCA"的隐蔽性，而全章的方法名称是 SMA，疑为笔误。

## 8. 开销

**攻击侧**：第 4.4.4 节第 (2) 部分"资源开销分析"写明"GAN 的训练过程伴随着高昂的算力与显存开销"，若每个通信轮次实时重训 MoEGAN"将极易因计算超时而被中心服务器判定为掉线节点并予以剔除"。SMA 的应对是"一次离线生成，持续投毒"：在 FL 通信正式启动前完成大、小女巫生成器与专家网络的对抗训练，收敛后批量生成中毒数据集；在随后的 T 轮全局通信中，"女巫节点不再进行任何 GAN 相关的计算，而是直接加载这些预先生成的静态中毒数据，参与联邦模型的常规前向与反向传播"。论文给出了这一定性结论，但没有报告任何具体的计算量、显存占用、通信量或存储量的数值。

**防御侧**：第 3.6 节称所提的决策一致性防御"在不增加显著计算开销的前提下"阻断攻击，但没有报告验证集推理的耗时或内存测量值，也未说明验证集规模。第 4.6 节没有讨论开销。

**通信开销**：论文未报告。攻击上传的是与正常客户端同规格的模型参数，但论文没有给出通信量对比。**存储开销**：论文未报告。SMA 需要在攻击者侧保存预生成的中毒数据集与生成器权重，论文没有给出存储量数值。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**：

1. 服务器绝对诚实且无法被攻陷，聚合逻辑不可篡改（第 3.2.2 节、第 4.2 节）。
2. 攻击者能控制至少一个合法参与节点，并在该节点上拥有对本地数据与训练过程的完全控制权（第 3.2.2 节）。
3. 攻击者能获取服务器下发的全局模型参数、网络架构与当前轮次（第 3.2.2 节）。
4. 攻击者无法跨节点获取其他良性客户端的私有数据与上传梯度（第 3.2.2 节、第 4.2 节）。
5. 攻击者不知道服务器采用的聚合算法与底层防御细节（第 4.2 节）。
6. 恶意客户端本地持有可用的干净数据集，用于预训练 MoEGAN 生成器（算法 3-1 的输入为"各个恶意客户端 c_m 的局部干净训练数据集 D^train_m"）；SMA 中大女巫需要持有真实数据集 D_m 用于切分（算法 4-1 的输入为"大女巫的原始数据集 D_m"）。
7. 聚合采用等权平均的 FedAvg（公式 2-4、公式 4-4）。
8. 联邦系统允许节点动态加入与退出，身份验证薄弱（第 2.2.2 节、第 4.4.4 节）。SMA 尤其依赖"无许可准入或弱身份认证"的跨设备联邦学习场景。
9. 第 3.6 节的防御假设服务器持有小规模干净验证集 D_val，并能对每个客户端更新做前向推理。
10. 第 4.6 节的防御假设服务器能维护一组经过严格物理身份验证的可信锚点客户端，并维护全体客户端的历史成对相似度矩阵。

**论文自述的局限**：

- 第 4.4.4 节第 (1) 部分指出，在跨孤岛联邦学习（cross-silo FL）场景中"部署 SMA 的物理门槛极高，攻击者必须提前窃取多个合法机构的证书或利用底层漏洞获取控制权"。
- 第 4.4.4 节第 (3) 部分指出"若服务器实施严格的物理身份认证，SMA 将失去实施条件"，并承认过度严格的认证在跨设备联邦学习中"可能导致合规用户流失或侵犯隐私"。
- 第 4.5.3 节根据图 4-9 指出大女巫节点之间仍高度相似，并"启示我们在实际部署时要考虑大女巫节点的数量，避免出现大量一致性现象"。
- 第 5.2 节指出当前攻击架构"主要在横向联邦学习的图像分类任务中进行了验证"，未来可探讨在纵向联邦学习、去中心化联邦学习以及联邦大语言模型微调等场景的适用性；并指出 MoE 与 GAN 属计算密集型架构，在边缘设备上部署"可能会因异常的能耗、内存占用或通信延迟而暴露出侧信道层面的攻击痕迹"。

**自适应攻击评估**：论文未评估自适应攻击者。论文把 MCD（文献 [24]）与 FoolsGold（文献 [15]）当作固定不变的防御基线来测量规避效果，没有考虑防御方观察到 MoEGAN 或 SMA 后调整阈值、检测统计量或聚合规则的情形。第 4.6 节虽然提出了针对 SMA 的防御思路，但没有与 SMA 做对抗实验。

**迁移到联邦 LoRA 微调时可能失效的假设**：

分析：论文的生成器是为图像设计的（转置卷积上采样、Tanh 输出、输出张量形如 3×32×32，见表 3-2），它无法生成文本 token 序列；把 MoEGAN 迁移到联邦大模型 LoRA 微调，需要替换整个中毒数据生成模块，论文没有给出任何文本域的生成方案。

分析：论文的全部统计量都建立在"客户端上传完整模型参数"这一前提上。在 LoRA 微调中，客户端上传的是低秩增量（通常记为 BA 形式的两个小矩阵），参数量比全参数模型小若干数量级，PCA 降维后的质心距离、覆盖指标、余弦相似度的取值尺度都会改变，论文在第 3.5.3 节与第 3.5.4 节给出的具体阈值（例如 d^base_f = 4.50、α = 20% 下的 h_{f,i} 区间）不能直接搬用。

分析：论文假设服务器看到的 w_{t,i} 可以直接与上一轮全局模型相加来构造局部模型（第 3.6 节）或直接相减得到增量（第 4.4.3 节）。在 LoRA 场景下，适配器既可以与基座权重合并也可以保持分离，聚合发生在适配器参数空间还是合并后的权重空间会改变这些差分的含义，论文没有涉及。

分析：第 3.6 节的防御要求服务器对每个客户端提交的更新在干净验证集上做前向推理，论文据此声称"不增加显著计算开销"。这一结论是针对小型卷积网络得出的；在联邦大模型 LoRA 微调中，逐客户端在验证集上做前向的成本远高于图像卷积网络，该假设很可能不成立。

分析：论文假设攻击者本地持有干净数据用于预训练生成器（算法 3-1 与算法 4-1 的输入）。在适配器或模型发布者构成供给链的场景中，攻击者可能不持有任何本地训练数据，这一假设不成立。

分析：SMA 依赖弱身份认证与无许可准入。若联邦 LoRA 微调的参与方是机构或具名开发者，并配有白名单或证书体系，女巫节点的批量注册会被阻断，第 4.4.4 节第 (3) 部分已经指出这一点。

分析：论文的隐蔽性论证依赖"跨轮上传参数"这一时序视图（图 3-7、图 4-9）。在 LoRA 微调中，若服务器只保留各轮适配器而不保留合并权重，跨轮比较仍然可行；但若服务器对适配器做低秩投影或只记录摘要，则论文所依赖的逐维参数视图不再可得。论文没有讨论这种情形。

## 10. 对防护库设计的含义

分析：库的采集底座需要在服务器收到更新的钩子上提供"逐客户端、逐轮的完整参数快照"这一最基础的视图，因为论文的 MCD 复现（表 3-8 至表 3-10）、PCA 可视化（图 3-4 至图 3-7）、攻击性与隐蔽性权衡实验（图 3-8）以及 FoolsGold 式的余弦相似度评估（图 4-9）全都建立在这个视图之上。还需要提供跨轮历史缓存，因为论文的纵向一致性度量与历史累积梯度都要求保存多轮的客户端更新。

分析：库需要一个"服务器聚合后的全局模型"采集点，因为第 3.6 节的防御要把上一轮全局模型与本轮客户端更新合成为候选局部模型；同时需要一个"干净验证集推理"的接口，把候选局部模型在验证集上的输出（预测分布、正确类与最大错误类的概率、混淆矩阵）暴露给插件。前者是通用需求，后者是决策一致性防御特有的需求。

分析：第 4.6 节的三阶段防御需要额外两类采集点，一是"可信锚点"这一带信任标签的客户端子集，二是服务器端维护的跨轮成对余弦相似度矩阵。这两项属于这篇论文特有的需求，通用底座只需要提供按客户端身份打标签和查询历史相似度的能力。

分析：干预接口方面，库至少要提供按客户端剔除、按客户端重新加权（第 3.6 节公式 3-13a 的评分倒数加权）、按客户端权重清零或指数衰减（第 4.6 节第三阶段）三类动作，并且这些动作都必须发生在服务器聚合环节。库不需要为这篇论文支持客户端侧干预，因为论文的攻击发生在客户端本地且服务器无法观测，而论文提出的防御全部在服务器侧执行。

分析：若要检测这篇论文描述的攻击，库还需要一个论文本身没有提供的采集点，即客户端训练前的数据视图（本地样本数、标签分布、数据指纹）。论文的攻击入口正是"用生成数据整体替换本地原始训练数据"（算法 3-1 第 10 行），但论文所有防御都只从服务器侧的模型参数出发，因而无法直接观测到这一替换行为。这个缺口是通用底座与具体检测插件之间的接口设计重点。

分析：论文把服务器完全诚实、攻击者无法触碰聚合逻辑作为前提，并且全文没有涉及任何密码学保护（安全聚合、差分隐私、可信执行环境）。库在联邦 LoRA 微调场景下若要同时覆盖恶意服务器与拜占庭客户端，需要把这篇论文的方法视为"仅客户端恶意"这一信任模型下的一个插件，而不能把它当作完整的威胁覆盖。

## 11. 原文依据

说明：该学位论文的正文为中文，全文的英文连续散文仅出现在英文摘要（ABSTRACT）中，以下引句因此全部取自该摘要，页码按抽取文本标注；每条给出所在章节与它支撑的论断。

1. 章节：ABSTRACT（pdf 第 6 页）。支撑第 1 节"场景为传统联邦学习"这一判断。
> "Federated Learning (FL), as an emerging distributed privacy-preserving machine learning paradigm, has demonstrated signiﬁcant potential in breaking down data silos."

2. 章节：ABSTRACT（pdf 第 6 页）。支撑第 2 节"攻击者针对的是数据中毒与女巫两类威胁"。
> "However, the openness of its distributed architecture also exposes it to severe security threats, particularly data poisoning attacks and sybil attacks."

3. 章节：ABSTRACT（pdf 第 6 页）。支撑第 4 节的方法动机，即单一生成器输出特征一致性是攻击隐蔽性的瓶颈。
> "Although existing GAN-based data poisoning attacks enhance the ﬁdelity of poisoned samples, they are constrained by the inherent generation mechanism of the GAN model, resulting in highly consistent anomalies within the malicious output features."

4. 章节：ABSTRACT（pdf 第 6 页）。支撑第 5 节"攻击声称能绕过基于空间相似度与降维异常评估的检测"。
> "This homogenization of malicious model distributions leads to poor attack stealth, making them highly susceptible to precise interception by current defense mechanisms based on spatial similarity and anomaly dimensionality reduction assessment."

5. 章节：ABSTRACT（pdf 第 6 页）。支撑第 4 节 MoEGAN 的定位与第 1 节论文类型为攻击。
> "An architecture named MoEGAN is proposed, which is a high-stealth data poisoning framework based on the Mixture-of-Experts (MoE) model speciﬁcally designed for FL security scenarios."

6. 章节：ABSTRACT（pdf 第 6 页）。支撑第 4 节"该工作把 MoE 引入联邦学习攻防领域"这一自述贡献。
> "Targeting the critical vulnerability of output feature consistency inherent in traditional GAN models, this work, to the best of our knowledge, represents the ﬁrst introduction of the MoE paradigm into the ﬁeld of FL attack and defense."

7. 章节：ABSTRACT（pdf 第 6 页）。支撑第 4 节关于定制化专家选择与路由逻辑的说法，以及第 4 节"分析"中关于该说法与第 3.4.1 节公式描述之间存在张力的判断。
> "Unlike the conventional gating mechanism in classic Mixture-of-Experts (MoE) models, this thesis introduces a tailored expert selection and routing logic for the poisoning task that dynamically adjusts the fusion weights of generative expert branches based on input sample characteristics."

8. 章节：ABSTRACT（pdf 第 6 页）。支撑第 4 节 MoEGAN 提升中毒数据异质性的机理主张。
> "This multi-expert collaborative mechanism effectively disrupts the distributional homogeneity of malicious feature generation associated with single-network models, thereby substantially enhancing the heterogeneity of poisoned data and the stealth of single-node attacks from the foundational architectural level."

9. 章节：ABSTRACT（pdf 第 7 页）。支撑第 4 节 SMA 把不同专家训练任务下发给不同女巫节点这一核心设计。
> "This strategy delegates the training tasks of distinct expert networks to multiple virtual sybil nodes, thereby fully leveraging the overwhelming disruptive efﬁcacy of sybil collusion in dominating the convergence direction of the global model."

10. 章节：ABSTRACT（pdf 第 7 页）。支撑第 5 节"攻击在可观测量上留下的痕迹是各节点更新的统计特征与梯度分布"，以及第 4.5.3 节图 4-9 的隐蔽性论断。
> "As a result, the malicious updates uploaded by individual nodes exhibit signiﬁcant disparities in both statistical characteristics and gradient distributions, with weak inter-node consistency, thereby demonstrating strong camouﬂage capabilities and evasion potential against existing defense mechanisms."

```json
{
  "key": "li2026thesis",
  "title": "基于混合专家模型的联邦学习隐蔽攻击方法研究",
  "year": 2026,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted"],
  "attack_entry": ["local_data", "local_training"],
  "observables": [
    {"what": "客户端上传的完整本地模型参数更新，用于PCA二维投影与分布可视化", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每个客户端的中心指标与覆盖指标及其异常度，用于模型一致性防御判定", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "客户端历史累积梯度与两两余弦相似度矩阵，用于女巫共谋检测", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "候选局部模型在干净验证集上的预测分布、分类间隔与混淆矩阵", "where": "server_receive", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "上一轮聚合后的全局模型参数，用于合成候选局部模型", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "可信锚点客户端的局部更新及其历史累积梯度", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "全局模型在测试集上的精度，用于量化攻击破坏程度", "where": "evaluation", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["exclude_client", "reweight"],
  "intervention_where": ["server"],
  "assumptions": [
    "中心服务器绝对诚实且无法被攻陷，聚合逻辑不可篡改",
    "攻击者能控制至少一个合法客户端并完全掌控其本地数据与训练过程",
    "攻击者能获取服务器下发的全局模型参数与网络架构，但无法跨节点获取其他客户端的私有数据与上传梯度",
    "攻击者不知道服务器采用的聚合算法与底层防御细节",
    "恶意客户端本地持有干净数据集，用于预训练MoEGAN生成器",
    "服务器采用等权平均的FedAvg聚合",
    "联邦系统身份验证薄弱，允许攻击者批量伪造女巫身份",
    "第3.6节防御假设服务器持有小规模干净验证集并能对每个客户端更新做前向推理",
    "第4.6节防御假设服务器能维护经物理身份验证的可信锚点集合与跨轮相似度矩阵"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "ABSTRACT（pdf 第6页）", "supports": "第1节场景判定：论文研究的是传统联邦学习范式", "text": "Federated Learning (FL), as an emerging distributed privacy-preserving machine learning paradigm, has demonstrated signiﬁcant potential in breaking down data silos."},
    {"section": "ABSTRACT（pdf 第6页）", "supports": "第2节威胁模型：攻击面向数据中毒与女巫两类安全威胁", "text": "However, the openness of its distributed architecture also exposes it to severe security threats, particularly data poisoning attacks and sybil attacks."},
    {"section": "ABSTRACT（pdf 第6页）", "supports": "第4节方法动机：单一GAN生成器导致输出特征一致性异常", "text": "Although existing GAN-based data poisoning attacks enhance the ﬁdelity of poisoned samples, they are constrained by the inherent generation mechanism of the GAN model, resulting in highly consistent anomalies within the malicious output features."},
    {"section": "ABSTRACT（pdf 第6页）", "supports": "第5节：攻击声称能绕过基于空间相似度与降维异常评估的检测机制", "text": "This homogenization of malicious model distributions leads to poor attack stealth, making them highly susceptible to precise interception by current defense mechanisms based on spatial similarity and anomaly dimensionality reduction assessment."},
    {"section": "ABSTRACT（pdf 第6页）", "supports": "第1节论文类型与第4节MoEGAN定位：属于攻击方法而非防御方法", "text": "An architecture named MoEGAN is proposed, which is a high-stealth data poisoning framework based on the Mixture-of-Experts (MoE) model speciﬁcally designed for FL security scenarios."},
    {"section": "ABSTRACT（pdf 第6页）", "supports": "第4节：论文自述首次将MoE引入联邦学习攻防领域", "text": "Targeting the critical vulnerability of output feature consistency inherent in traditional GAN models, this work, to the best of our knowledge, represents the ﬁrst introduction of the MoE paradigm into the ﬁeld of FL attack and defense."},
    {"section": "ABSTRACT（pdf 第6页）", "supports": "第4节：论文声称采用为投毒任务定制的专家选择与路由逻辑", "text": "Unlike the conventional gating mechanism in classic Mixture-of-Experts (MoE) models, this thesis introduces a tailored expert selection and routing logic for the poisoning task that dynamically adjusts the fusion weights of generative expert branches based on input sample characteristics."},
    {"section": "ABSTRACT（pdf 第6页）", "supports": "第4节：多专家机制被用来打破恶意特征生成的分布同质性", "text": "This multi-expert collaborative mechanism effectively disrupts the distributional homogeneity of malicious feature generation associated with single-network models, thereby substantially enhancing the heterogeneity of poisoned data and the stealth of single-node attacks from the foundational architectural level."},
    {"section": "ABSTRACT（pdf 第7页）", "supports": "第4节：SMA把不同专家网络的训练任务下发至多个虚拟女巫节点", "text": "This strategy delegates the training tasks of distinct expert networks to multiple virtual sybil nodes, thereby fully leveraging the overwhelming disruptive efﬁcacy of sybil collusion in dominating the convergence direction of the global model."},
    {"section": "ABSTRACT（pdf 第7页）", "supports": "第5节：攻击在可观测量上留下的痕迹是各节点更新的统计特征与梯度分布差异", "text": "As a result, the malicious updates uploaded by individual nodes exhibit signiﬁcant disparities in both statistical characteristics and gradient distributions, with weak inter-node consistency, thereby demonstrating strong camouﬂage capabilities and evasion potential against existing defense mechanisms."}
  ]
}
```
