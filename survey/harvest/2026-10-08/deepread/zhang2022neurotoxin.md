# zhang2022neurotoxin：Neurotoxin: Durable Backdoors in Federated Learning

## 1. 基本信息

- **场景**：传统联邦学习（federated learning, FL）仿真环境，服务器用 FedAvg 均值聚合（第 4.1 节）。论文不是联邦大模型微调，也不是参数高效微调（PEFT）或适配器供应链研究，全文没有出现 LoRA 或任何低秩适配方法。唯一与"大模型"沾边的是任务 2：在 FL 仿真中训练 120M 参数的 GPT2（第 3.1 节），论文在附录 A.5 自称这是首次有工作在 FL 训练中向"现代 Transformer 规模"的模型植入后门。
- **训练阶段**：攻击发生在客户端本地（投毒数据构造 + 本地训练中的梯度投影）与更新上传环节；服务器端只做范数裁剪和平均，论文不修改服务器侧流程。
- **论文类型**：攻击（模型投毒 / 后门攻击），同时评测了若干已有防御。发表于 ICML 2022（PMLR 162），arXiv 编号 2206.10341v1。
- **模型与数据规模**：共 10 个任务（表 2）。Reddit 下一词预测（LSTM、GPT2，各 8000 个设备）、Sentiment140 情感分类（LSTM，2000 个设备）、IMDB（LSTM，1000 个设备）、CIFAR10（ResNet18，1000 个设备，edge-case 与 base-case 两个任务）、CIFAR100（ResNet18，1000 个设备，两个任务）、EMNIST-digit（LeNet，1000 个设备）、EMNIST-byclass（ResNet9，3000 个设备）。所有任务每轮选 10 个设备参与，另有每轮 100 个设备的实验（第 3.1 节）。总轮次从 500（情感分类）到 2200（下一词预测）（第 3.2 节）。

## 2. 威胁模型

- **攻击者身份**：被攻陷的客户端设备（compromised devices）。论文明确"攻击者只能攻陷 FL 中很小比例的设备（< 1%）"（第 2.1 节，引 Shejwalkar et al., 2022）。系统视角下，最弱攻击者投毒约 0.2% 的系统（任务 1），最强约 1%（任务 3）；攻击者在一次 FL 生命周期内只贡献 40 个更新向量，而系统总共看到约 22,000 次更新（第 3.2 节）。每轮参与 100 设备的实验里，30 万次更新中只有 150 次来自被控设备，投毒比例为 0.0005，即 1/2000（第 3.3 节、图 9）。
- **数量与频率**：用 AttackNum 表示攻击者参与的轮数，最小值为 40（第 3.2 节）。"固定频率攻击"（fixed-frequency attack）指攻击者参与的每一轮只控制恰好 1 个设备；附录 A.2 另外评测了"每 2 轮参与 1 次"的变频率攻击。
- **能力**：被控设备可以"上传任意向量作为自己的更新"（第 2.1 节）。攻击者可以构造投毒数据集 D̂ = {x, y}（第 2.1 节），可以用 PGD、交替最小化、boosting 等任意策略 A 加工更新（第 2.1 节），并在本地训练的每一步把梯度投影到坐标约束集（算法 1 第 4 行）。
- **知识**：攻击者能下载上一轮的梯度 g，用它近似下一轮的良性梯度，并取它的 top-k% 坐标作为约束集（第 2.3 节）。论文还预计攻击者能用一份良性训练分布样本在单设备仿真中调好掩码比例 k（第 3.3 节）。论文未说明攻击者是否知道服务器的范数裁剪参数 p，也未说明攻击者是否需要其他客户端的数据；论文特意指出 ClipBKD 这类需要"被训练模型全部输入"的方法在 FL 中不可行，而 Neurotoxin 不需要（第 3.3 节）。
- **目标**：定向后门（在测试时让含触发器的输入输出固定目标），同时不损害良性准确率（摘要、第 2.1 节公式 θ(x) = y）。论文把危害具体化为下一词预测中的种族仇恨补全，甚至单词触发器（图 4、第 3.3 节）。不是隐私攻击，也不是一般意义上的越狱或安全对齐破坏。
- **防御者**：服务器。能看到单个客户端的梯度（除非使用 secure aggregation，论文指出检测类防御与已部署的 secure aggregation 不兼容，第 3.3 节）。服务器的信任与动作包括：用 FedAvg 平均、对单设备梯度做 ℓ2 范数裁剪并把裁剪参数 p 调到"不影响收敛"的最小值（第 3.2 节、附录 A.8）。论文没有假设服务器有干净根数据集或可信代理。

## 3. 攻击入口与流程位置

论文的攻击从**本地数据准备**与**本地训练过程**进入：

1. **本地数据准备**：攻击者构造投毒数据集 D̂。NLP 任务从训练分布采样并拼接触发句，视觉任务采样 512 张"5"类图像并把标签改成"9"（base-case），或用分布外的西南航空飞机图像标成"truck"、用 Ardis 瑞典数字"7"标成"1"（edge-case）（第 3.1 节；触发器与目标见表 1）。
2. **本地训练过程（核心入口）**：见算法 1 右栏。先用下载的梯度更新本地模型 θ = θ − g；然后在若干本地 epoch 内，对投毒数据的每个 batch 计算随机梯度；**在每一步用 SGD 更新本地模型之前，把该梯度投影到坐标约束集**（把上一轮梯度 g 的 top-k% 坐标置零，即只保留 bottom-k% 坐标）；最后把训练得到的本地模型更新上传。
3. **上传前的后处理**：投影这一步不是训练结束后的独立后处理，而是作用在每个本地 step 的梯度上（算法 1 第 4 行）。论文未说明 Neurotoxin 会对上传更新做缩放或 boosting；论文在第 2.1 节与第 4.2 节提到 boosting 是既有攻击（如 Bagdasaryan et al., 2020）的做法。
4. **服务器聚合、全局模型下发、评估与部署**：论文不在这些位置植入攻击。攻击者只是把服务器下发的上一轮全局更新当作输入来估计良性梯度；聚合仍由服务器用 FedAvg 完成。论文明确说攻击是"通过向服务器上传投毒梯度"实现的（第 3.2 节）。

## 4. 方法原理

- **核心思想**（第 2.3 节）：SGD 梯度的 ℓ2 范数大部分集中在少数"heavy hitter"坐标上（引 Stich et al., 2018；Ivkin et al., 2019；Rothchild et al., 2020）。如果攻击只更新良性设备不常更新的坐标，后门就不容易被后续良性更新覆盖。论文的表述是：先前的 edge-case 攻击靠攻击"欠代表的数据"，Neurotoxin 靠攻击**欠代表的参数**（underrepresented parameters）。
- **攻击的一般记号**（第 2.1 节）：ĝ = A(∇L(θ, D̂))；θ = θ − S(ĝ)；目标是 θ(x) = y。其中 A 是攻击者的更新加工策略（PGD、交替最小化、boosting 等），S 是服务器防御（例如把更新向量的 ℓ2 范数裁剪以阻止 model replacement）。
- **关键步骤**（第 2.3 节、算法 1 右栏）：
  1. 下载上一轮的梯度 g，用它近似下一轮的良性梯度；
  2. 取 g 的 top-k% 坐标作为约束集 S；
  3. 在投毒数据集上做若干 epoch 的 PGD，每一步计算投毒梯度后**在 S 上把该梯度置零**（等价于只在 bottom-k% 坐标张成的子空间里更新），再更新本地模型；
  4. 上传本地模型更新。
  论文说 PGD 会收敛到落在 bottom-k% 坐标张成空间内的最优解。
- **为什么有效**：论文用二阶量解释（第 3.4 节）。在已经植入后门的模型上计算后门损失的 Hessian 迹 tr(∇²θL(θ′)) 与最大特征值 λmax，数值越小说明模型对权重扰动越稳定。图 10（任务 6）与表 14（Sentiment140、CIFAR10）显示 Neurotoxin（k = 1% 或 4%/5%）的这两个量小于 baseline（k = 0%），因此后门在后续良性重训练中存活更久。计算使用 PyHessian（第 3.4 节脚注 2）。
- **baseline 定义**：baseline 即掩码比例 k = 0% 的 Neurotoxin（图 13 标题）。

## 5. 检测或防御所需的数据

论文是攻击论文，没有提出检测器；下面逐项列出攻击涉及的可观测量、论文评测过的检测/防御所需输入，以及它们从哪里取。

1. **每个客户端上传的本地更新向量（模型增量或梯度）**
   - 是什么：被控设备上传的投毒更新，以及良性设备的更新。
   - 在哪里采集：服务器收到更新时。
   - 粒度：逐客户端（每轮每设备一个向量）。
   - 跨轮历史：不需要。干净参考数据：不需要。额外前向/反向计算：不需要。其他客户端数据：聚合防御需要同一轮其他客户端的更新（如中位数、Krum 类方法），但论文未评测这些方法。
2. **上一轮服务器下发的全局更新 g（全模型梯度）**
   - 是什么：攻击者用来近似良性梯度、并据以选出 top-k% "heavy hitter" 坐标的向量。
   - 在哪里采集：客户端训练前（服务器下发全局模型/更新的时刻）。
   - 粒度：逐轮、逐坐标（覆盖整个参数向量）。
   - 跨轮历史：需要（攻击者只用相邻一轮）。干净参考数据：不需要（用的是聚合结果，其中可能含少量投毒更新）。额外计算：只需要一次 top-k 排序。其他客户端数据：间接使用（聚合结果）。
3. **上传更新的逐坐标支撑集 / 稀疏模式**
   - 是什么：哪些坐标被置零；与上一轮全局更新的 heavy hitter 坐标是否重合。这是攻击在观测量上最直接留下的痕迹，依据是算法 1 的投影和 SparseFed 实验（第 3.3 节：SparseFed"只更新梯度的 top-k 坐标，而 Neurotoxin 恰好避开这些坐标"）。
   - 在哪里采集：服务器收到更新时。
   - 粒度：逐坐标（跨全模型参数，可按层聚合）。
   - 跨轮历史：需要（要与上一轮全局更新比对）。干净参考数据：不需要。额外计算：不需要（一次排序/比较）。其他客户端数据：不需要。
4. **逐客户端更新的 ℓ2 范数**
   - 是什么：norm clipping 防御的输入量。
   - 在哪里采集：服务器收到更新时。
   - 粒度：逐客户端、逐轮。
   - 跨轮历史：不需要。干净参考数据：不需要。额外计算：不需要。论文未说明服务端是否保存范数历史。
5. **梯度在 VAE 下的重建损失（Li et al., 2020a 的检测防御）**
   - 是什么：判断更新是否像真实数据产生的梯度。
   - 在哪里采集：服务器收到更新时。
   - 粒度：逐客户端。
   - 跨轮历史：不需要。干净参考数据：需要（训练好的 VAE）。额外计算：需要一次前向计算。论文结论是该防御对 Neurotoxin 无效（图 6）。
6. **全局模型在投毒数据集上的后门准确率与良性测试准确率**
   - 是什么：度量后门是否存活，是 lifespan 定义的输入（定义 3.1）。
   - 在哪里采集：评估时（每轮聚合后的全局模型上）。
   - 粒度：逐轮、逐模型。
   - 跨轮历史：需要（lifespan 是攻击停止后首次掉到阈值以下的轮索引）。干净参考数据：需要攻击者的投毒数据集（含触发器）来测后门准确率，需要良性测试集来测良性准确率。额外计算：前向评估。
7. **植入后门模型的 Hessian 迹与最大特征值**
   - 是什么：后门损失在参数点 θ′ 处的二阶量，用来解释耐久性。
   - 在哪里采集：服务器聚合后（论文中是在植入完成后、用攻击者的后门损失计算）。
   - 粒度：逐模型（逐轮可选）。
   - 跨轮历史：不需要。干净参考数据：需要攻击者的后门损失（即需要知道触发器和目标）。额外计算：需要二阶估计（PyHessian 类方法）。

**论文声称攻击能绕过的检测**：范数裁剪（所有实验都启用，攻击仍成功）；弱差分隐私（σ = 0.001，攻击仍比 baseline 耐久，虽然相对下降更大，图 5）；VAE 重建损失检测（无效，图 6）；SparseFed 稀疏化（"mitigates our attack on Reddit, but not entirely"，图 7）。论文提到但没有实测的防御包括 Krum、Bulyan、trimmed mean、median（第 4.3 节说这些防御计算复杂度高，且先前工作已证明这些攻击能在这些防御下成功）和 CRFL 的重训练防御（第 2.1、4.3 节引用）。论文还指出，secure aggregation 会让服务器看不到单个梯度，因此检测类防御在实际部署中不可用（第 3.3 节）。

## 6. 干预动作

论文本身是攻击论文，**没有提出任何检测后的干预动作**，也没有给出检测阈值或处置流程。

论文评测的干预动作全部来自已有防御，且都发生在服务器端：
- **范数裁剪（norm clipping）**：服务器在收到更新时裁剪单设备梯度范数，使其不超过 p。该防御在所有实验中都启用，p 取"不影响收敛"的最小值（第 3.2 节；参数搜索见附录 A.8，选出的 p 为 IMDB 3.0、CIFAR10 1.0）。结果：未能阻止攻击。
- **差分隐私（differential privacy）**：服务器在更新上加均匀噪声（σ = 0.001，远小于 DP-SGD 的噪声量），发生在服务器收到/聚合更新时（图 5、第 3.3 节）。结果：Neurotoxin 的 lifespan 从 70 降到 41（下降 42%），baseline 从 17 降到 13（下降 26%），攻击仍比 baseline 耐久。
- **重建损失检测（Li et al., 2020a）**：服务器在收到更新时做检测（论文只报告检测无效，未说明检测后如何处置）。图 6 显示该检测对 Neurotoxin 无效。
- **稀疏化防御 SparseFed（Panda et al., 2022）**：服务器在聚合时只更新 top-k 坐标。图 7 显示它缓解但不能完全消除攻击。
- **重训练/CRFL**：只在动机与相关工作里作为防御被引用（第 2.1、4.3 节），论文未实测。

## 7. 实验设置与主要结果

**设置**：模型、数据集与设备数见表 2（Reddit LSTM 8000、Reddit GPT2 8000、Sentiment140 LSTM 2000、IMDB LSTM 1000、CIFAR10 ResNet18 1000、CIFAR100 ResNet18 1000、EMNIST-digit LeNet 1000、EMNIST-byclass ResNet9 3000）。所有任务每轮 10 个设备参与，另有每轮 100 个设备的实验（第 3.1 节，图 9）。总轮次 500（情感分类）到 2200（下一词预测）（第 3.2 节）。攻击起始轮：Reddit LSTM 2000 / GPT2 0（图 13 标题）、Sentiment140 与 IMDB 150（图 15 标题）、CIFAR 与 EMNIST 1800（图 16、17、18 标题）。AttackNum：Reddit 消融 40/60/80/100（表 4），Sentiment140 80、IMDB 100（图 15 标题），CIFAR10 base-case 250、CIFAR100 base-case 200（图 17 标题），CIFAR edge-case 200（图 16 标题），EMNIST-digit 200、EMNIST-byclass 100（图 18 标题），100 设备实验 150（图 9 标题）。恶意比例：系统层面约 0.2%–1%（第 3.2 节），100 设备实验为 0.0005（第 3.3 节）。**数据是否非独立同分布：论文未说明其实验的数据划分方式**；non-IID 只在相关工作里作为 FedCurvature/FedProx 的动机出现（第 4.1 节）。

**指标**：后门准确率（在投毒数据集 D̂ 上）；lifespan（定义 3.1，l = max{t | α(θt, D̂) > κ}，默认阈值 κ = 50%）；良性准确率；Hessian 迹与最大特征值。lifespan 阈值在附录 A.5 中改为 75%（因为 Sentiment140 与 IMDB 是二分类），但表 10、表 11、表 14 又写成阈值 60，存在不一致。

**关键结果**：
- 图 1（Reddit、LSTM）：baseline 的 50% lifespan 为 11 轮、100% lifespan 为 24 轮；Neurotoxin 分别为 67 轮与超过 170 轮，摘要称"耐久性提高到 5 倍"。
- 表 3（Reddit，掩码比例 k 扫描）：Trigger set 1 上 baseline（k=0）lifespan 44，k=1 为 131，k=3 为 122，k=5 为 197，k=15 为 132，k=25 为 49，k=35 为 40，k=45 为 6；Trigger set 2 上 baseline 78，k=1 为 120，k=3 为 187，k=5 为 123；Trigger set 3 上 baseline 124，k=1 为 302，k=3 为 292，k=5 为 235。
- 表 4（Reddit，AttackNum 消融，掩码比例 5%）：AttackNum=40 时 trigger 1/2/3 的 baseline 为 11/17/18，Neurotoxin 为 67/70/54；AttackNum=80 时为 44/78/124 对 197/123/235；AttackNum=100 时为 55/108/159 对 235/173/173。
- 表 5 与图 4（触发器长度）：长度 3/2/1 时 baseline lifespan 为 78/54/32，Neurotoxin 为 123/93/122。论文强调长度为 1 时 baseline 只用 32 轮就被擦除，"不到植入攻击本身所需轮数的一半"，而 Neurotoxin 存活接近 4 倍长（第 3.3 节）。
- 图 5（差分隐私，σ = 0.001）：baseline lifespan 13，Neurotoxin 41；正文说 baseline 从 17 降到 13（26%），Neurotoxin 从 70 降到 41（42%）。
- 图 6：VAE 重建损失检测无效。图 7：SparseFed 缓解但不能完全消除。图 8：把 Neurotoxin 叠加在 ClipBKD（SVD 类攻击，Jagielski et al., 2020）上可大幅提升 EMNIST 上的后门耐久性。
- 图 9（每轮 100 设备，AttackNum=150）：baseline lifespan 56，Neurotoxin 154。
- 图 10 与表 14：CIFAR10 上 baseline 与 Neurotoxin 的 lifespan 为 116 与 405（表 14，掩码比例 5%），最大特征值为 899.37 与 210.14，Hessian 迹为 2331.11 与 667.91；Sentiment140 上 lifespan 278 与 416，最大特征值 0.004 与 0.002，Hessian 迹 0.097 与 0.027。注意图 17 标题写的 CIFAR10 base-case 是 baseline 116、Neurotoxin 279，与表 14 的 405 不一致；图 17 标题另给出 CIFAR100 base-case 为 943 与 1723。
- 附录 A.3 与图 13：停止攻击后 GPT2 的后门准确率远高于 LSTM，论文据此认为大容量模型中的后门更难被擦除。
- 良性准确率（表 6–13）：Reddit 上从攻击开始到攻击结束下降不超过 1%（表 6 标题），例如表 8 中 LSTM 的 16.65 降到 16.50、GPT2 的 28.66 升到 30.32；表 12 中 CIFAR10 base-case 从 67.5 变为 baseline 65.16 / Neurotoxin 62.34。

## 8. 开销

**论文未报告**攻击或其防御的计算量、通信量、存储量的具体数值。论文报告过的相关定性陈述有：

- Neurotoxin 做的是约束优化，收敛比 baseline 慢，因此攻击轮数少时提升不明显（附录 A.1：需要更多 epoch 才能在投毒数据集上达到 100% 准确率）。
- 攻击者每轮需要额外下载上一轮梯度，并做一次 top-k 选择与逐坐标投影（算法 1；论文只描述步骤，未给出复杂度量级）。
- 论文说 trimmed mean、median、Krum、Bulyan 等防御"增加了很高的计算复杂度"，所以在多数实验中只使用范数裁剪和弱差分隐私（第 4.3 节）。
- 第 3.4 节的 Hessian 分析使用 PyHessian 做随机数值线性代数估计，论文未报告其耗时。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设（论文有依据）**：
- 攻击者只控制不到 1% 的设备，且只能参与有限轮（第 2.1、3.2 节）。
- 被控设备可以上传任意更新向量（第 2.1 节）。
- 上一轮广播的全局更新可以近似下一轮的良性梯度，从而可以用它的 top-k% 坐标作为"要避开的 heavy hitter"（第 2.3 节）。
- 良性梯度的 ℓ2 范数集中在少数坐标上（第 2.3 节引用 Stich et al., 2018；Ivkin et al., 2019；Rothchild et al., 2020）。
- 服务器用 FedAvg 均值聚合，防御强度被限制在不损害收敛的水平（第 3.2 节、附录 A.8）。
- 攻击停止后模型继续只被良性更新训练，lifespan 就是在这种条件下度量的（第 2.1、3.2 节）。
- 攻击者知道如何选择掩码比例 k；论文认为攻击者可以用一份良性分布样本在单设备仿真里调好 k（第 3.3 节）。

**论文自述的局限**：
- "这不意味着 Neurotoxin 在 baseline 连一个 epoch 都插不进去的设定下会成功"，例如服务器加入大量噪声（第 4.3 节）。
- 加噪对 Neurotoxin 的相对打击更大：baseline 从 17 降到 13，Neurotoxin 从 70 降到 41（第 3.3 节、图 5）。
- 约束优化收敛更慢，AttackNum 小时提升有限（附录 A.1）。
- 在容易植入的任务上相对提升不明显：GPT2 上（图 14）和 IMDB 上（附录 A.5）Neurotoxin 相比 baseline 提升有限。
- 两个任务的 lifespan 无法测量：CIFAR100 edge-case 因每个设备几乎没有 edge-case 数据、后门擦除太慢（附录 A.5）；EMNIST-digit 因 Neurotoxin 太耐久而在数千轮内不跌破阈值（附录 A.5）。
- ClipBKD 需要被训练模型的全部输入来计算训练集 SVD，在 FL 中不可行（第 3.3 节）。
- 未实测 Krum、Bulyan、trimmed mean、median 等防御（第 4.3 节）。
- 论文承认其危害具有伦理影响，包括可传播仇恨言论的单词触发攻击（第 5 节）。

**自适应攻击者**：论文**没有**构造或评测针对 Neurotoxin 的自适应攻击者，也没有评测"知道 Neurotoxin 存在并据此重新设计"的防御。最接近的讨论是论文指出 SparseFed 几乎就是专门为对抗 Neurotoxin 设计的（只更新梯度的 top-k 坐标，而 Neurotoxin 避开这些坐标），并给出图 7 的结果：SparseFed 缓解但不能完全消除攻击。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**：
- 论文的攻击与全部证据都建立在对整个参数向量做逐坐标 top-k 掩码上。LoRA 只训练低秩矩阵 A、B，参数量比全模型小好几个数量级，且 A 通常随机初始化、B 零初始化；"良性梯度范数集中在少数 heavy hitter 坐标"这一经验假设在低秩适配器上是否成立，论文未说明。
- 论文的服务器聚合对象是完整的本地模型更新；联邦 LoRA 常见的是聚合适配器增量或客户端本地合并适配器。逐坐标掩码能否直接作用于低秩因子，论文未说明。
- 论文的耐久性结论依赖"攻击停止后继续多轮良性训练"（总轮次 500–2200、攻击起点常在第 1800–2000 轮）。联邦 LoRA 微调通常轮数少、学习率小、基座冻结，后门可能天然更耐久或因适配器容量受限而更易被覆盖；论文未说明这一点。
- 论文的评测是分类/下一词预测的准确率与触发器命中；现代生成式大模型的评测、分词器对触发词的切分、chat 模板都会改变可观测痕迹，论文未说明。
- 论文明确提到检测类防御与 secure aggregation 不兼容；联邦 LoRA 场景更常启用 secure aggregation，这会直接废掉服务器逐客户端梯度视图，这一条可以直接迁移。
- 论文为范数裁剪选 p 的流程（在不损害收敛的前提下取最小值，附录 A.8）可以迁移，但 p 的尺度和不损害收敛的判定需要按 LoRA 重标定，论文未说明。

## 10. 对防护库设计的含义

- **分析：**采集底座需要在"服务器收到更新时"这一信任边界上，逐客户端保存完整更新向量（在联邦 LoRA 场景即 A/B 增量或合并后的适配器更新）、其 ℓ2 范数、以及**逐坐标支撑集**；同时要缓存上一轮下发的全局更新，因为本论文的攻击正是用它来选掩码坐标的。逐客户端更新、范数、相邻轮历史这三项是通用需求，不只服务这一篇论文。
- **分析：**库需要一个"更新 × 轮 × 坐标"的数据视图，并能按层归约出稀疏度与坐标重合度；如果部署启用了 secure aggregation，服务器只有聚合结果，那么 SparseFed 式 top-k 防御与坐标重合度检测都会失效——论文本身也说明检测防御与 secure aggregation 不兼容，因此这一限制应写进插件的适用条件检查。
- **分析：**服务器聚合钩子是本文最相关的干预接口：需要能注册"聚合时只取 top-k 坐标"（稀疏化）与"逐客户端范数裁剪"两类动作，并能读取/改写 k 与 p。论文显示这两类动作都不足以消除攻击，因此插件应支持组合，且 p 的选取要沿用论文"不损害收敛"的标定流程，避免为拦截攻击而破坏收敛。
- **分析：**本文特有的需求是"掩码比例 k"与"历史 heavy hitter 坐标集合"这两个概念：客户端钩子若要在本地审计，最少需要上报每步梯度的坐标支持集或每轮被置零坐标的统计量（而不是原始梯度），服务器钩子则要维护一份按轮滑动的 heavy hitter 坐标表。这是本文特有视图，通用底座只需保证坐标级（而非仅范数级）的数据可见性。
- **分析：**要复现或基准化本论文，库还需要两类非在线能力：一是"攻击停止后继续用良性客户端训练"的编排接口，用于度量 lifespan；二是允许注入攻击者视角投毒数据集与后门损失的后门评估接口（论文的 lifespan 与 Hessian 分析都需要攻击者的触发器和目标标签）。前者是通用的评测底座能力，后者是把攻击者知识与评估绑定的特殊接口。
- **分析：**检测接口方面，本论文只提供"负面证据"：基于梯度重建损失的检测（VAE）与基于范数裁剪的防御都被绕过，说明针对这类"用真实数据、只在低幅坐标上做手脚"的后门，逐客户端范数与重建误差不是有效判据；库若想检测它，需要在插件里显式表达"更新支撑相对历史 heavy hitter 的规避程度"这一特征。

## 11. 原文依据

1. **Abstract** — 支撑第 1 节论文类型与第 4 节核心思想（单行改动、攻击变化幅度小的参数）。
   "Here, we propose Neurotoxin, a simple one-line modification to existing backdoor attacks that acts by attacking parameters that are changed less in magnitude during training."
2. **第 2.1 节 Motivation and Prior Attacks** — 支撑第 2 节攻击者占比小于 1%。
   "We consider attackers which can compromise only a small percentage of devices in FL (< 1%)"
3. **第 2.1 节** — 支撑第 2 节攻击者能力（可上传任意向量）与第 3 节攻击者自行构造投毒更新。
   "A compromised device can upload any vector as their update to the server. We generalize the types of backdoors and optimization methods used by prior work on backdoor attacks as follows"
4. **第 2.3 节 Neurotoxin** — 支撑第 4 节前两步与第 5 节第 2 项可观测量（上一轮梯度）。
   "The attacker downloads the gradient from the previous round, and uses this to approximate the benign gradient of the next round. The attacker computes the top-k% coordinates of the benign gradient and sets this as the constraint set."
5. **第 2.3 节** — 支撑第 3 节本地训练中的投影入口与第 4 节 PGD 步骤。
   "For some number of epochs of PGD, the attacker computes a gradient update on the poisoned dataset ˆD and projects that gradient onto the constraint set, that is the bottom-k% coordinates of the observed benign gradient."
6. **第 3.2 节 Metrics and Methods（Server defense）** — 支撑第 6 节范数裁剪防御及其参数选择方式。
   "We implement the popular norm clipping defense (Sun et al., 2019) in all experiments. We find the smallest value of the norm clipping parameter p that does not impact convergence"
7. **第 3.3 节 Experimental Results** — 支撑第 7 节差分隐私结果与第 9 节"对噪声更敏感"的局限。
   "Neurotoxin is impacted more by noise addition than the baseline. Baseline lifespan decreases from 17 to 13 (26 %), and Neurotoxin lifespan decreases from 70 to 41 (42 %)."
8. **第 3.3 节** — 支撑第 5 节"论文声称能绕过哪些检测"中的重建损失检测。
   "The malicious gradients have a low reconstruction loss because our attack produces poisoned gradients by training on plausible real world data rather than data with patterns."
9. **第 3.3 节** — 支撑第 9 节 SparseFed 几乎是针对 Neurotoxin 的防御但仍不能完全消除攻击。
   "This is significant because the defense in (Panda et al., 2022) is almost designed specifically to counter Neurotoxin: the defense only updates the top-k coordinates of the gradient, and Neurotoxin avoids these same coordinates."
10. **附录 A.3 Backdoor comparison of GPT2 and LSTM** — 支撑第 7 节 GPT2 结果与第 9 节关于大模型后门更难擦除的迁移讨论。
    "It can be found that the backdoor accuracy of GPT2 is much larger than that of LSTM after stopping the attack. This implies that, in large-capacity models, it is more difficult to erase the backdoor"

```json
{
  "key": "zhang2022neurotoxin",
  "title": "Neurotoxin: Durable Backdoors in Federated Learning",
  "year": 2022,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data", "local_training"],
  "observables": [
    {"what": "每个客户端上传的本地更新向量（模型增量或梯度）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "上一轮服务器下发的全局更新 g，攻击者据此估计良性梯度的 top-k% heavy hitter 坐标", "where": "client_pre_train", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "上传更新的逐坐标支撑集，即相对上一轮全局更新的 top-k% 坐标是否被置零，可按层聚合", "where": "server_receive", "granularity": "layer", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐客户端更新的 L2 范数，norm clipping 防御的输入", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "梯度在 VAE 下的重建损失，即 Li et al. 2020a 的检测防御输入", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "聚合后全局模型在投毒数据集上的后门准确率与在良性测试集上的准确率，用于 lifespan 度量", "where": "evaluation", "granularity": "round", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "植入后门模型在后门损失上的 Hessian 迹与最大特征值", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "攻击者只控制不到 1% 的设备，且只能参与有限轮 AttackNum",
    "被控设备可以上传任意更新向量",
    "上一轮广播的全局更新可近似下一轮良性梯度",
    "良性梯度的 L2 范数集中在少数 heavy hitter 坐标上",
    "服务器用 FedAvg 均值聚合，防御强度被限制在不损害收敛的水平",
    "攻击停止后模型继续只被良性更新训练"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节论文类型与第 4 节核心思想", "text": "Here, we propose Neurotoxin, a simple one-line modification to existing backdoor attacks that acts by attacking parameters that are changed less in magnitude during training."},
    {"section": "2.1 Motivation and Prior Attacks", "supports": "第 2 节攻击者设备占比小于 1%", "text": "We consider attackers which can compromise only a small percentage of devices in FL (< 1%)"},
    {"section": "2.1 Motivation and Prior Attacks", "supports": "第 2 节攻击者能力与第 3 节攻击者自行构造投毒更新", "text": "A compromised device can upload any vector as their update to the server. We generalize the types of backdoors and optimization methods used by prior work on backdoor attacks as follows"},
    {"section": "2.3 Neurotoxin", "supports": "第 4 节前两步与第 5 节上一轮梯度这一可观测量", "text": "The attacker downloads the gradient from the previous round, and uses this to approximate the benign gradient of the next round. The attacker computes the top-k% coordinates of the benign gradient and sets this as the constraint set."},
    {"section": "2.3 Neurotoxin", "supports": "第 3 节本地训练中的投影入口与第 4 节 PGD 步骤", "text": "For some number of epochs of PGD, the attacker computes a gradient update on the poisoned dataset ˆD and projects that gradient onto the constraint set, that is the bottom-k% coordinates of the observed benign gradient."},
    {"section": "3.2 Metrics and Methods, Server defense", "supports": "第 6 节范数裁剪防御及其参数选择方式", "text": "We implement the popular norm clipping defense (Sun et al., 2019) in all experiments. We find the smallest value of the norm clipping parameter p that does not impact convergence"},
    {"section": "3.3 Experimental Results", "supports": "第 7 节差分隐私结果与第 9 节对噪声更敏感的局限", "text": "Neurotoxin is impacted more by noise addition than the baseline. Baseline lifespan decreases from 17 to 13 (26 %), and Neurotoxin lifespan decreases from 70 to 41 (42 %)."},
    {"section": "3.3 Experimental Results", "supports": "第 5 节论文声称绕过的重建损失检测", "text": "The malicious gradients have a low reconstruction loss because our attack produces poisoned gradients by training on plausible real world data rather than data with patterns."},
    {"section": "3.3 Experimental Results", "supports": "第 9 节 SparseFed 几乎是针对性防御但仍不能完全消除攻击", "text": "This is significant because the defense in (Panda et al., 2022) is almost designed specifically to counter Neurotoxin: the defense only updates the top-k coordinates of the gradient, and Neurotoxin avoids these same coordinates."},
    {"section": "Appendix A.3 Backdoor comparison of GPT2 and LSTM", "supports": "第 7 节 GPT2 结果与第 9 节大模型后门更难擦除的迁移讨论", "text": "It can be found that the backdoor accuracy of GPT2 is much larger than that of LSTM after stopping the attack. This implies that, in large-capacity models, it is more difficult to erase the backdoor"}
  ]
}
```
