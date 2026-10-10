# cao2020fltrust：FLTrust: Byzantine-robust Federated Learning via Trust Bootstrapping

## 1. 基本信息

- **场景**：传统联邦学习（federated learning, FL），即"多个客户端 + 一个服务提供方服务器"的横向联邦学习，任务为图像分类与手机传感器人体活动识别。论文全文没有出现大语言模型（large language model, LLM）、Transformer、LoRA 或任何参数高效微调（parameter-efficient fine-tuning, PEFT）相关内容；客户端上传的是与全局模型同形状的**完整模型更新**（Section II-A、Section IV）。
- **训练阶段**：攻击发生在客户端本地数据准备、本地训练与"更新上传前"的处理；防御发生在服务器侧的聚合阶段（Step III）。此外 FLTrust 在流程中新增了一个服务器侧训练步骤（Step II 中服务器用根数据集训练服务器模型，Section IV-A、Algorithm 2 第 12 行）。
- **论文类型**：防御（Byzantine-robust 聚合方法）。论文同时设计了针对该防御的自适应攻击（adaptive attack，Section V、Algorithm 3），但主体贡献是防御方法。
- **模型与数据规模**：六个数据集。MNIST-0.1 与 MNIST-0.5 用 CNN（表 II 给出结构：输入 28×28×1、两层卷积加池化、全连接 100、Softmax 10）；MNIST（60,000 训练 / 10,000 测试）、Fashion-MNIST（60,000 / 10,000）、CIFAR-10（50,000 / 10,000）用 CNN 或 ResNet20；HAR 共 10,299 条样本、561 维特征、6 类、30 个用户，用逻辑回归（logistic regression, LR）；CH-MNIST 共 5,000 张 64×64 灰度图、8 类，取 4,000 张训练、1,000 张测试，用 ResNet20（Section VI-A1、Section VI-A4）。
- **发表信息**：正式发表于 NDSS Symposium 2021；arXiv 编号 2012.13995（v1 于 2020 年 12 月，v3 于 2022 年 4 月）。

## 2. 威胁模型

**攻击者是谁。** 论文沿用先前工作的攻击模型（Section III）：攻击者控制若干恶意客户端（malicious clients），它们既可以是攻击者注入的伪造客户端，也可以是被攻陷的真实客户端；**攻击者不攻陷服务器**。论文没有给出固定的恶意比例，实验默认 20%，并在图 6、图 7 中扫描到 95%。

**能力（能改什么）。** 恶意客户端在 FL 训练的每一轮都可以向服务器发送**任意**本地模型更新（arbitrary local model updates）。具体到实例化攻击：
- 标签翻转（label flipping, LF）攻击改本地训练样本的标签，标签 l 变为 M−l−1（M 为类别数，Section VI-A2）；
- Scaling 攻击向本地训练数据追加带触发器（trigger）且标签为攻击者目标标签的样本，并把更新整体放大 λ = n 倍（n 为客户端总数）后上传（Section II-B、Section VI-A2）；
- Krum 攻击与 Trim 攻击不经过真实训练，直接求解优化问题构造中毒更新（Section II-B、Equation 6）。

**知识（知道什么）。** 论文给出的"部分知识"设定是：恶意客户端自己的本地训练数据与本地模型更新、损失函数、学习率；Scaling 攻击只需部分知识。但 Krum 攻击与 Trim 攻击在"全知识"设定下更强——攻击者知道所有客户端每轮的本地训练数据与本地模型更新以及聚合规则；论文主动采用全知识设定来展示防御强度（Section III）。Section V-B 进一步假设自适应攻击者知道 FLTrust 聚合规则的全部中间量：||g₀||、s、cᵢ（i = 1..n）、e₀ 与 eᵢ。

**目标。** 两类：无目标攻击（untargeted attacks）使全局模型对大量测试样本给出错误预测，即抬高测试错误率；定向攻击（targeted attacks，即后门）使全局模型对攻击者选定的目标测试样本输出攻击者选定的目标标签，同时不影响其他测试样本（Section II-B）。论文没有讨论隐私窃取或越狱/安全对齐破坏。

**防御者是谁、能看到什么、信任什么。** 防御在服务器侧执行（Section III "Defender's knowledge and capability"）：服务器不能访问客户端原始本地训练数据；**不知道恶意客户端的数量**；但完整掌握全局模型以及每一轮所有客户端的本地模型更新。服务器额外被假定有能力**自行收集一个小规模干净训练集（根数据集，root dataset）**，并要求该数据集无投毒，可通过人工标注获得（论文举例：Google 让员工用 Gboard 打字构造根数据集）。服务器的信任根就是这份根数据集以及由它训练出的服务器模型更新。

## 3. 攻击入口与流程位置

本文是防御论文，下面写它针对的攻击入口，以及它自身干预的位置。

**被防御攻击的入口：**
1. **本地数据准备**：标签翻转攻击直接篡改恶意客户端本地训练样本的标签但保持特征不变；Scaling 攻击复制本地训练样本的一部分，嵌入预定义触发器并把标签改成攻击者目标标签，用于扩充本地训练数据（Section II-B、Section VI-A2）。
2. **本地训练过程**：恶意客户端在扩充/投毒后的数据上正常训练，从而得到方向被带偏的本地更新（Section II-B 指出任何数据投毒攻击都可以转化为本地模型投毒攻击）。
3. **更新上传前的后处理**：Scaling 攻击把中毒更新乘以远大于 1 的缩放因子 λ（论文设置 λ = n），意图在平均时压过其他客户端；Krum/Trim 攻击则在求解优化问题后直接发送构造出的中毒更新，不经过真实训练（Section II-B、Section VI-A2、Equation 6）。
   - 这些操作的效果都在**服务器收到更新时**才可见。

**防御自身的干预位置**：服务器聚合阶段（Step III），即服务器收到本轮全部本地更新之后、更新全局模型之前（Section IV-C、Algorithm 2 第 14–19 行）。FLTrust 不修改客户端流程，也不过滤样本或回滚模型。

**论文未说明**：论文没有讨论攻击者直接污染"全局模型下发"通道、服务器实现或评估/部署环节的情形（因为攻击模型明确排除了服务器被攻陷）。

## 4. 方法原理

核心思想（Abstract、Section IV-A）：既有 Byzantine-robust 方法只在客户端之间做统计比较、没有信任根（no root of trust），因此容易被精心构造的本地更新绕过；FLTrust 让服务提供方自己持有干净小数据（根数据集 D₀）并维护一个服务器模型，用服务器模型更新的**方向**作为信任基准，用它的**范数**作为幅度基准。

关键步骤（Section IV-B、Section IV-C、Algorithm 1 与 Algorithm 2）：

1. **服务器侧影子训练**。每一轮，客户端用 ModelUpdate(w, Dᵢ, b, β, R_l) 得到本地更新 gᵢ；服务器同时用同一函数、同一批超参（批大小 b、本地学习率 β、本地迭代数 R_l）在根数据集上得到服务器模型更新 g₀（Algorithm 2 第 12 行；ModelUpdate 内部是 R 次随机小批量 SGD，Algorithm 1）。
2. **信任分（trust score, TS）**。用余弦相似度度量方向相似性：cᵢ = ⟨gᵢ, g₀⟩ / (||gᵢ||·||g₀||)，再用 ReLU 截断得到 TSᵢ = ReLU(cᵢ)（Equation 2）。论文的解释是：余弦相似度为负的更新仍会对聚合结果产生负面影响，所以要截断掉（Section IV-B；表 IV 中 FLTrust-NoReLU 变体失效）。
3. **幅度归一化**。把每个本地更新缩放到与服务器模型更新同样的范数：ḡᵢ = (||g₀|| / ||gᵢ||) · gᵢ（Equation 3）。论文称这等价于把所有本地更新投影到服务器模型更新所在的同一超球面上，从而限制大幅度中毒更新的影响；同时也把小幅度更新放大，理由是"幅度小的更新更可能来自良性客户端"（Section IV-B；表 IV 中 FLTrust-NoNorm、FLTrust-ParNorm 变体失效）。
4. **按信任分加权的聚合**。g = (1 / Σⱼ ReLU(cⱼ)) · Σᵢ ReLU(cᵢ) · (||g₀|| / ||gᵢ||) · gᵢ（Equation 4，等价写法见 Equation 12 的 ϕᵢ 加权形式），然后 w ← w + α·g（Equation 5）。若某轮只选了部分客户端，聚合就在被选中的客户端上进行（Algorithm 2 第 18 行）。
5. **服务器模型更新不直接进入聚合结果**。论文讨论了把 g₀ 当作信任分为 1 的更新一起加权平均的变体 FLTrust-withServer，但因为根数据集小、分布可能不同，该变体反而有害（Section IV-B、表 IV）。

**理论结果**（Section IV-D、Theorem 1）：在 Assumption 1–3 成立且 R_l = 1、β = 1 时，对**任意数量**的恶意客户端，FLTrust 学到的全局模型与无攻击最优模型 w* 的距离有界：||w_t − w*|| ≤ (1−ρ)^t ||w₀ − w*|| + 12αΔ₁/ρ，其中 ρ = 1 − (√(1 − µ²/(4L²)) + 24αΔ₂ + 2αL)，Δ₁ 与 Δ₂ 依赖根数据集大小 |D₀|、参数维度 d、以及 Assumption 2 中的 σ₁、σ₂、γ₁、γ₂ 等常数。Assumption 1 要求期望损失 µ-强凸且梯度 L-Lipschitz，经验损失以概率 L₁-Lipschitz；Assumption 2 要求最优点的梯度与梯度差具有亚指数尾；Assumption 3 要求每个客户端的数据集 Dᵢ 与根数据集 D₀ 都独立地采样自同一分布 X。

**针对 FLTrust 的自适应攻击**（Section V、Algorithm 3）：把 Fang 等人的通用本地模型投毒框架（Equation 6）代入 FLTrust 的聚合规则，得到以单位向量 e′ᵢ 为变量的优化问题（Equation 9、10），用零阶梯度上升（Equation 11）在每次坐标上升中求解，初始化用 Trim 攻击，迭代 Q 次、外层 V 次，并把 e′ᵢ 投影回单位球；论文设置 σ² = 0.5、γ = 0.005、η = 0.01、V = Q = 10（Section VI-A2）。

## 5. 检测或防御所需的数据

FLTrust 需要且仅需要下列输入：

| 数据 | 是什么 | 在哪里采集 | 粒度 | 跨轮历史 / 干净参考 / 额外计算 |
|---|---|---|---|---|
| 客户端本地模型更新 gᵢ | 客户端本地模型与当前全局模型之差，与全局模型同形状的完整向量 | 服务器收到更新时（Step II 末、Step III 前） | 逐客户端（每个被选中客户端每轮一份） | 不需要跨轮历史；不需要干净参考；不需要额外前向/反向 |
| 当前全局模型 w | 上一轮聚合后的全局模型参数 | 聚合后的全局模型（下发前） | 整个模型 | 不需要历史；不需要干净参考；不需要额外计算 |
| 服务器模型更新 g₀ | 服务器用根数据集 D₀ 对当前全局模型做与客户端同配置训练（b、β、R_l）得到的更新 | 服务器聚合前，与客户端本地训练并行计算（Algorithm 2 第 12 行） | 整个模型（每轮一份） | 需要跨轮（每轮重算，因为起点 w 每轮变化）；**需要干净的根数据集**；**需要服务器侧一次额外训练（前向 + 反向，R_l 次 SGD 迭代）** |
| 干净根数据集 D₀ | 服务方自行收集并（人工）标注的小训练集，论文默认 100 条，实验扫描 50–500 条 | 训练开始前离线准备，由服务方持有，不属于任何客户端（论文说明采样后从客户端训练集中剔除） | 逐样本 | 不需要历史；本身就是干净参考；不产生额外计算（除上面的影子训练之外） |

论文**不需要**的数据：逐样本损失、隐藏层激活、输出文本、逐层范数、优化器状态、其他客户端的原始数据。FLTrust 的余弦相似度与范数比值都是在**整条扁平化更新向量**上计算的（Equation 2–4），论文没有给出逐层或逐模块的版本。

**攻击侧的可观测量与绕过情况（论文报告）：** Scaling 攻击把更新放大 λ = n 倍，在"服务器收到更新时"表现为幅度异常；Krum 攻击与 Trim 攻击表现为更新方向与良性更新方向不一致，在余弦相似度上表现为低分或负分（表 IV 显示去掉 ReLU 后 FLTrust 在 Krum/Trim/Scaling/自适应攻击下错误率都升到 0.90 及以上）。论文声称 FLTrust 能防住这些攻击，而既有方法被绕过：MNIST-0.1 上 Krum 攻击把 Krum 的测试错误率从 0.10 抬到 0.90，MNIST-0.5 上 Trim 攻击把 Trim-mean 与 Median 从 0.06 抬到 0.23 与 0.43，Scaling 攻击在 MNIST-0.1 与 MNIST-0.5 上对 FedAvg 的攻击成功率均为 1.00（表 III(a)(b)）。论文还提到 Fang 等人用"验证数据集"直接剔除可疑更新的做法"在很多情况下无效"（Section VII）。

## 6. 干预动作

FLTrust 在**服务器聚合阶段**做三件事，全部是"改写后聚合"，不做硬性剔除：

1. **按信任分重新加权**：每个客户端得到权重 ReLU(cᵢ) / Σⱼ ReLU(cⱼ)（Equation 4）。方向与服务器更新相反（余弦相似度 ≤ 0）的客户端权重被置为 0，因此实际上对全局更新没有贡献；但论文没有把这类客户端"剔除"出流程，它们仍在客户端集合中。
2. **幅度裁剪/重标定**：把每个更新缩放到范数 ||g₀||（Equation 3），既压缩大幅度中毒更新，也放大小幅度更新。
3. **加权平均后更新全局模型**：w ← w + α·g（Equation 5）。

**不做的事**：不屏蔽或剔除客户端、不加噪声、不裁剪单个坐标、不过滤本地样本、不修复或回滚全局模型、不只报告不干预。客户端侧没有任何干预动作（Section VI-B 明确 FLTrust 不给客户端增加额外开销）。

**论文未说明**：当某一轮所有被选中客户端的 ReLU(cᵢ) 全为 0、导致 Equation 4 的分母为 0 时应如何处理，论文没有讨论。

## 7. 实验设置与主要结果

**设置（Section VI-A、表 I）：** n = 100 个客户端（HAR 为 30，CH-MNIST 为 40）；每轮选中比例 τ = n，即每轮选全部客户端；本地迭代 R_l = 1；全局迭代 R_g = 2,000（MNIST-0.1、MNIST-0.5、CH-MNIST）、2,500（Fashion-MNIST）、1,500（CIFAR-10）、1,000（HAR）；批大小 b = 32（CIFAR-10 为 64）；默认恶意客户端比例 m/n = 20%（对应 m = 20 / 6 / 8）；Krum 参数 f 与 Trim-mean 参数 k 都设为 m，即假定服务器知道恶意客户端的准确数量，"给 Krum 和 Trim-mean 以优势"；根数据集默认 |D₀| = 100。组合学习率 α·β 按数据集分别设置（表 I 给出 3×10⁻⁴、6×10⁻³、2×10⁻⁴、3×10⁻³ 与 3×10⁻⁴ 五个值，其中一项注明在第 1500 与 1750 轮按 0.9 衰减；抽取文本中该行数值与数据集的列对应关系不完整）。
**非独立同分布（non-IID）**：用一个概率 q 控制标签偏斜，q = 1/M 时为独立同分布（IID）。MNIST-0.1 取 q = 0.1（IID）；MNIST-0.5、Fashion-MNIST、CIFAR-10、CH-MNIST 取 q = 0.5（non-IID）；HAR 天然按用户切分，每个用户是一个客户端，本身不均衡（每客户端训练样本最多 409、最少 281、平均 343）（Section VI-A1）。
**指标**：测试错误率（testing error rate）；对 Scaling 攻击另外报告攻击成功率（attack success rate）（Section VI-A3）。

**主要结果：**
- **保真度**：无攻击时 FLTrust 与 FedAvg 相当。MNIST-0.1 上 FedAvg 与 FLTrust 都是 0.04，Krum/Trim-mean/Median 分别为 0.10/0.06/0.06；CH-MNIST 上 FedAvg、Trim-mean、FLTrust 都是 0.10，Krum 与 Median 为 0.24 与 0.11（Section VI-B、表 III(a)(f)）。
- **鲁棒性**：FLTrust 在无目标攻击（含自适应攻击）下的测试错误率最多比"无攻击 FedAvg"高 0.04。MNIST-0.1 上 FLTrust 在 LF/Krum/Trim/Scaling/自适应攻击下分别为 0.04/0.04/0.04/0.03/0.04，Scaling 攻击成功率 0.00；MNIST-0.5 上为 0.05/0.05/0.06/0.05/0.06，攻击成功率 0.00；CIFAR-10 上无攻击 0.18、各攻击 0.18–0.20；HAR 上 0.04–0.05；CH-MNIST 上 0.10–0.14（表 III(a)–(f)）。Scaling 攻击在 FLTrust 上的攻击成功率在六个数据集上都不超过 0.03，而对 FedAvg 在六个数据集上都很高（表 III）。
- **变体对比（MNIST-0.5，表 IV）**：FLTrust-Server 无攻击错误率 0.21；FLTrust-withServer 无攻击 0.07、自适应攻击 0.94；FLTrust-NoReLU 无攻击 0.28、Krum/Trim 攻击 0.90、Scaling 0.94/0.08；FLTrust-NoNorm 无攻击 0.05 但 Scaling 0.94/0.08；FLTrust-ParNorm 0.06；完整 FLTrust 为 0.05/0.05/0.05/0.06/0.05–0.00/0.06。
- **根数据集大小（图 4，MNIST-0.5）**：从 50 增到 500 条；论文称 100 条就足以防御，继续增大只带来轻微下降。
- **根数据集分布偏置（表 V）**：偏置概率越大防御越差。以 MNIST-0.5 为例，偏置概率不超过 0.4 时各攻击下错误率最多 0.08，而偏置概率 0.1（即 Case I）时为 0.05；偏置概率到 1.0 时无攻击错误率已升到 0.80。
- **客户端总数（图 5，MNIST-0.5）**：n 从 50 增到 400，恶意比例固定 20%，FLTrust 在各攻击下错误率与无攻击 FedAvg 接近，Scaling 攻击成功率接近 0。
- **恶意比例（图 6、图 7）**：在既有攻击与自适应攻击下，FLTrust 最多可容忍 90% 的恶意客户端；Scaling 攻击在恶意比例高达 95% 时攻击成功率仍接近 0。作为对比，Krum 攻击在恶意比例仅 10% 时就把 Krum 的错误率抬到 0.90，Trim-mean 与 Median 在恶意比例达到 40% 时错误率超过 0.85。逐数据集看，FLTrust 在自适应攻击下仍能保持与无攻击 FedAvg 相当的错误率，对应 MNIST-0.1 超过 60%、MNIST-0.5 超过 40%、Fashion-MNIST 最多 60%、CIFAR-10 最多 60%、HAR 最多 40%、CH-MNIST 超过 40% 的恶意客户端。
- **收敛速度（图 3，MNIST-0.5）**：FLTrust 在各攻击下的训练错误率下降曲线与无攻击 FedAvg 一样快。

## 8. 开销

论文报告的是**定性结论，没有任何数值或测量**：
- 客户端侧：每一轮 FLTrust 都不给客户端带来额外开销；因为收敛速度与 FedAvg 相同，客户端也不承担额外通信开销（Section VI-B、图 3）。
- 服务器侧：相比 FedAvg，额外计算是"计算一次服务器模型更新、计算信任分、归一化本地模型更新"三项，论文称这些对强大的服务器而言可以忽略（Section VI-B）。
- 论文指出 Krum 在客户端数量大时会显著增加服务器计算开销，因为它要计算两两距离（Section III、Section VI-B）。

具体的计算量、通信字节数、存储占用、墙钟时间**论文未报告**。

## 9. 假设、局限与自适应攻击

**方法依赖的假设（论文明确写出）：**
1. 服务器持有一份**干净**根数据集，可通过人工收集标注获得（Section III、Section VII）。
2. 根数据集的分布不能与任务整体训练分布偏离太大；偏置概率实验（表 V）显示偏离到一定程度后防御失效。
3. 服务器不被攻陷；服务器不知道恶意客户端数量；服务器能看到所有客户端每轮的更新（Section III）。
4. 攻击者的部分知识设定是本地数据、本地更新、损失函数与学习率；但论文按更强的全知识设定做实验（Section III）。
5. 理论结果依赖 Assumption 1（µ-强凸、L-Lipschitz 梯度、经验损失概率 Lipschitz）、Assumption 2（梯度与梯度差亚指数尾）、Assumption 3（各客户端数据集与根数据集都独立采样自分布 X），并要求 R_l = 1、β = 1（Section IV-D、Theorem 1）。
6. **分析**：Equation 2 与 Equation 3 隐含要求服务器模型更新与所有客户端更新处在同一参数空间、形状一致，否则余弦相似度与范数比值无法计算；论文没有把这一点写成显式假设。

**论文自述的局限（Section VII）：** 需要干净的根数据集，论文承认 FLTrust 对**被投毒的根数据集**可能不鲁棒（根数据集可能来自互联网或内部攻击者，但论文认为小规模数据可由服务方低成本自建）；论文承认可能存在更强的、针对 FLTrust 的本地模型投毒攻击，留作未来工作；论文提出"分层信任根"（hierarchical root of trust）也留作未来工作。

**自适应攻击的评估：** 有评估，且是全知识、可合谋的强攻击者。论文把 Fang 等人的通用框架实例化到 FLTrust 上（Section V），在表 III 与图 7 中报告结果，例如 MNIST-0.1 上 60% 恶意客户端时 FLTrust 的错误率仍为 0.04（与无攻击 FedAvg 相同），MNIST-0.5、Fashion-MNIST、CIFAR-10、HAR、CH-MNIST 上分别在恶意比例超过 40%、最多 60%、最多 60%、最多 40%、超过 40% 时仍与无攻击 FedAvg 相当。但论文同时说明"可能存在更强的攻击"（Section VII）。

**迁移到联邦 LoRA（low-rank adaptation）微调时可能失效的假设（以下全部为分析）：**
- **参数空间一致性**：论文的更新是整个模型参数向量，客户端之间、客户端与服务器之间结构完全相同。联邦 LoRA 中若各客户端使用不同秩 r、不同目标模块集合或不同基座版本，增量张量形状不同，Equation 2 的余弦相似度与 Equation 3 的范数比值都无法直接定义。库需要先做参数空间规范化（统一模块集合与秩，或把增量投影到公共子空间），论文没有提供这种处理。
- **单一全局余弦相似度**：论文对整条更新向量算一个余弦相似度；LoRA 增量在不同模块（注意力投影层与前馈层）之间的尺度差异很大，用全局相似度可能被少数模块主导，掩盖其余模块上的方向偏离。逐层或逐模块信任分是自然的扩展，但**论文未说明**这种变体。
- **强凸性与 Lipschitz 假设**：Theorem 1 依赖 µ-强凸与 L-Lipschitz 梯度，语言模型损失函数不满足，定理的界不能直接搬用；论文的实验证据（错误率与攻击成功率）来自小模型图像/传感器任务，是否在 LoRA 指令微调上复现，论文未研究。
- **根数据集的代表性与规模**：论文的根数据集是 100 条与总体同分布的标注样本，表 V 显示分布偏置加大后防御迅速退化。联邦 LoRA 指令微调的任务/领域异质性远高于标签偏斜的 MNIST 划分，100 条样本上的 LoRA 更新方向本身噪声很大，"根数据集分布不离散"这一假设更难成立。
- **优化轨迹假设**：论文强依赖 R_l = 1、客户端与服务器用同一 β、b 做一步 SGD，且更新近似为负梯度（附录 A 的证明以此为基础）。若 LoRA 客户端做多步本地更新或多 epoch，服务器模型更新 g₀ 与客户端更新 gᵢ 在尺度与方向上都会更不可比，论文未讨论 R_l > 1 时的防御效果。
- **攻击面范围**：论文的攻击者只能在每轮发送任意更新。适配器供应链场景还包括发布被污染的适配器权重文件、配置或分词器，以及"投毒发生在微调数据而非更新通道"的情形，FLTrust 没有对应机制，论文未讨论。
- **目标与指标**：论文用测试错误率与后门攻击成功率衡量防御。对"越狱或安全对齐破坏"这类目标，用测试错误率衡量是否合适，论文未说明。

## 10. 对防护库设计的含义

以下全部为**分析**：

1. **通用采集点**：库的底座需要在"服务器收到更新时"提供一个按（轮次, 客户端标识）索引的、未经任何改写的原始更新视图（在 LoRA 场景即完整的适配器增量张量），并且要保留与全局模型参数的对应关系。这是任何基于更新统计的插件（包括本论文的方法）的共同前提，属于通用需求。
2. **本论文特有的采集点：服务器侧影子训练**。FLTrust 要求服务器在每轮聚合前，用一份受信根数据集、以与客户端相同的优化配置（批大小、学习率、本地步数）对当前全局模型做一次训练，得到 g₀。库应把"服务器本地数据集 + 服务器本地训练步骤"建模为一等公民（一个新的服务器钩子，位于"聚合前"），并记录根数据集的版本、哈希、样本来源与分布审计信息，因为论文的整个防御都建立在这份数据干净且不大幅偏离总体分布之上。论文的既有 FL 流程里没有这个位置。
3. **干预接口需要支持"逐客户端权重 + 更新改写"**，而不是只有接受/拒绝两态：插件要能返回一个标量信任权重，并能在聚合前重写某个客户端更新的尺度（范数重标定）。同时底座需要明确"权重为 0 的客户端是否仍计入分母"的语义；论文用的是"权重为 0 但仍参与分母求和"，且论文未说明分母为 0 时怎么办，库应自己定义并记录这一边界策略。
4. **方向视图与幅度视图应拆成两个独立数据视图**：单位化后的方向（用于余弦相似度）与逐客户端更新范数（用于比较幅度）。论文的两条防线正好一个管方向、一个管幅度；对 LoRA，进一步的逐层/逐模块范数与余弦是低成本的扩展，但属于论文之外的推断。
5. **跨轮历史与逐样本视图不是本论文的必需项**：FLTrust 只用当前轮的更新与全局模型，不需要客户端历史更新、逐样本损失或激活。若库希望做信任分轨迹监控、异常趋势告警或回滚，那是超出论文范围的额外存储需求，应与本方法的必需采集点分开设计，避免把历史存储强加给所有插件。
6. **攻击检测/复现所需的对照视图**：要复现论文中的攻击以做回归测试，底座需要支持在客户端侧注入三类行为——改写本地标签、向本地数据插入带触发器的样本、以及对上传更新做整体缩放；这些属于测试夹具能力，与运行时检测插件分开。

## 11. 原文依据

1. **Abstract** — 支撑第 1、4 节：FLTrust 的核心思想是服务器自举信任。
   > "In this work, we bridge the gap via proposing FLTrust, a new federated learning method in which the service provider itself bootstraps trust."
2. **Abstract** — 支撑第 4、5 节：根数据集与服务器模型的来源。
   > "In particular, the service provider itself collects a clean small training dataset (called root dataset) for the learning task and the service provider maintains a model (called server model) based on it to bootstrap trust."
3. **Section III (Attack model)** — 支撑第 2 节：攻击者身份与不攻陷服务器。
   > "Specifically, an attacker controls some malicious clients, which can be fake clients injected by the attacker or genuine ones compromised by the attacker."
4. **Section III (Defender's knowledge and capability)** — 支撑第 2、9 节：防御者看不到原始数据、也不知道恶意客户端数量。论文未说明（原句后紧跟的 "However, the server has full access..." 见下条）。
   > "The server does not have access to the raw local training data on the clients, and the server does not know the number of malicious clients."
5. **Section III (Defender's knowledge and capability)** — 支撑第 5 节：服务器可获取的采集视图。
   > "However, the server has full access to the global model as well as the local model updates from all clients in each iteration."
6. **Section II-B (Scaling attack)** — 支撑第 3 节：攻击在"上传前"放大更新幅度。
   > "Therefore, the attack further scales the poisoned local model updates on malicious clients by a factor that is much larger than 1."
7. **Section IV-B (ReLU-clipped cosine similarity based trust score)** — 支撑第 4、5 节：信任分基于方向相似度，是整条向量的余弦。
   > "Formally, we use the cosine similarity, a popular metric to measure the angle between two vectors, to measure the direction similarity between a local model update and the server model update."
8. **Section IV-B (Normalizing the magnitudes of local model updates)** — 支撑第 4、6 节：幅度归一化到服务器更新的范数。
   > "Therefore, we normalize each local model update such that it has the same magnitude as the server model update."
9. **Section V (Adaptive attacks)** — 支撑第 9 节：自适应攻击来自通用本地模型投毒框架的实例化。
   > "In particular, Fang et al. [15] proposed the state-of-the-art framework that can optimize local model poisoning attacks for any given aggregation rule."
10. **Section VII (Discussion and Limitations)** — 支撑第 9 节：论文自述需要干净根数据集、对根数据集投毒不鲁棒。
    > "Our FLTrust requires a clean root dataset. We acknowledge that FLTrust may not be robust against poisoned root dataset."

```json
{
  "key": "cao2020fltrust",
  "title": "FLTrust: Byzantine-robust Federated Learning via Trust Bootstrapping",
  "year": 2021,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["untargeted", "backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {"what": "每个被选中客户端的本地模型更新 g_i，与全局模型同形状的完整参数增量向量", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "当前全局模型 w，作为服务器影子训练与客户端本地训练的起点", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "服务器模型更新 g_0，服务器用根数据集在每轮对全局模型做同配置训练得到（聚合前计算，枚举中无 server_pre_aggregate，归到聚合位置）", "where": "server_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "干净根数据集 D_0，服务方离线人工收集标注的小数据集，默认 100 条，需与总体训练分布差异不过大（枚举中无 server_pre_train，用训练前位置表示）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false}
  ],
  "interventions": ["reweight", "clip"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务器能自行收集并人工标注一个小规模干净根数据集（论文默认 100 条），且论文承认对根数据集投毒不鲁棒",
    "根数据集分布不能与任务总体训练分布偏离过大，偏置概率实验显示偏离过大后防御失效",
    "服务器不被攻陷；服务器看不到客户端原始数据、也不知道恶意客户端数量，但能看到全局模型与每轮所有客户端的更新",
    "服务器模型更新与客户端更新必须处在同一参数空间、形状一致，否则余弦相似度与范数比值无法计算",
    "理论结果依赖 Assumption 1-3：期望损失强凸且梯度 Lipschitz、梯度亚指数尾、各客户端数据集与根数据集独立采样自同一分布 X，且 R_l = 1、β = 1",
    "论文未说明某一轮所有客户端信任分同时为 0（聚合公式分母为 0）时的处理方式"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1、4 节：FLTrust 的核心思想是服务器自举信任", "text": "In this work, we bridge the gap via proposing FLTrust, a new federated learning method in which the service provider itself bootstraps trust."},
    {"section": "Abstract", "supports": "第 4、5 节：根数据集与服务器模型的来源", "text": "In particular, the service provider itself collects a clean small training dataset (called root dataset) for the learning task and the service provider maintains a model (called server model) based on it to bootstrap trust."},
    {"section": "Section III (Attack model)", "supports": "第 2 节：攻击者是恶意客户端，且不攻陷服务器", "text": "Specifically, an attacker controls some malicious clients, which can be fake clients injected by the attacker or genuine ones compromised by the attacker."},
    {"section": "Section III (Defender's knowledge and capability)", "supports": "第 2、9 节：防御者看不到原始数据也不知道恶意客户端数量", "text": "The server does not have access to the raw local training data on the clients, and the server does not know the number of malicious clients."},
    {"section": "Section III (Defender's knowledge and capability)", "supports": "第 5 节：服务器可获取的采集视图", "text": "However, the server has full access to the global model as well as the local model updates from all clients in each iteration."},
    {"section": "Section II-B (Scaling attack)", "supports": "第 3 节：攻击在上传前放大更新幅度", "text": "Therefore, the attack further scales the poisoned local model updates on malicious clients by a factor that is much larger than 1."},
    {"section": "Section IV-B (ReLU-clipped cosine similarity based trust score)", "supports": "第 4、5 节：信任分基于整条更新向量的方向相似度", "text": "Formally, we use the cosine similarity, a popular metric to measure the angle between two vectors, to measure the direction similarity between a local model update and the server model update."},
    {"section": "Section IV-B (Normalizing the magnitudes of local model updates)", "supports": "第 4、6 节：幅度归一化到服务器更新的范数", "text": "Therefore, we normalize each local model update such that it has the same magnitude as the server model update."},
    {"section": "Section V (Adaptive attacks)", "supports": "第 9 节：自适应攻击来自通用本地模型投毒框架的实例化", "text": "In particular, Fang et al. [15] proposed the state-of-the-art framework that can optimize local model poisoning attacks for any given aggregation rule."},
    {"section": "Section VII (Discussion and Limitations)", "supports": "第 9 节：论文自述需要干净根数据集且对根数据集投毒不鲁棒", "text": "Our FLTrust requires a clean root dataset. We acknowledge that FLTrust may not be robust against poisoned root dataset."}
  ]
}
```
