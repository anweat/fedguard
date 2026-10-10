# tran2018spectral：谱特征（Spectral Signatures）后门样本检测与剔除

## 1. 方法一句话

这个方法输入一个（可能被少量后门样本污染的）带标签训练集 Dtrain、一个能提供中间特征表征 R 的神经网络 L，以及一个中毒样本数量/比例的上界 ε（Algorithm 1 第 1 行），输出一个"先训练、再按类做 SVD 离群点剔除、再重训"的干净分类器；也就是说，它输出的改动是**从训练集中删除被判为后门的样本，并在剩余数据上重新训练模型**（Algorithm 1 第 10、13–15 行；Figure 3）。

## 2. 运行位置

论文的方法是完全集中式（centralized）的：作者假设"用户自己训练分类器，但训练数据来自外部、可能已被投毒"，攻击者能访问训练数据并知道用户的网络结构与训练算法，但**不亲自训练模型**（§2.1）。论文全文没有出现联邦学习、客户端、通信轮次或聚合的概念。

对应到联邦流程最自然的位置是：**服务器聚合之后**（server_post_aggregate）执行检测，因为此时服务器已经有一个在（可能被污染的）数据上训练好的全局模型，可以用它来算表征；随后是**训练之外**（outside_training）的一次数据清洗；清洗之后还需要**再走一遍训练/聚合**（server_aggregate）来得到最终模型。最初的那次训练（Algorithm 1 第 2 行）对应联邦里的常规多轮"下发—本地训练—聚合"。以上映射是分析：，论文本身只描述了单机流程。

是否需要额外往返：论文没有客户端—服务器结构，因此原方法本身没有往返。分析：若要在联邦运行时里复现它，服务器需要拿到"每个客户端的逐样本、按类分组的表征 R(x_i)"（原始数据通常不上传），这要求客户端在标准训练轮之外多上传一次表征（或把 SVD 检测下放到客户端、用全局模型在本地算表征后再上报要删除的样本索引），因此记为需要一次额外往返；论文未讨论这一点。

## 3. 算子流水线

记号：Dtrain 为带标签训练集，D_y 为标签 y 的全部训练样本，n = |D_y|，C 为类别数（CIFAR-10 中 C = 10，每类 5000 张，§1），d 为表征维数（论文未给出具体数值），ε ∈ (0, 1/2) 为中毒样本上界。

**步骤 1：按标签分组（group_samples_by_label）**
- 输入：带标签训练集 Dtrain = {(x_i, y_i)}，图像 x_i（CIFAR-10 为 3×32×32 的彩色图，§4.1）。
- 计算：对每个标签 y，取 D_y = {x_i : y_i = y}，并把 D_y 枚举为 x_1, …, x_n，令 n = |D_y|。
- 输出：C 个按标签划分的样本子集。
- 出处：Algorithm 1 第 1、4、5 行。

**步骤 2：在完整（可能被污染的）训练集上训练 L（train_model_on_full_data）**
- 输入：Dtrain。
- 计算：训练一个"随机初始化的、提供特征表征 R 的神经网络模型 L"；论文实验中 L 是 ResNet，含 3 组 residual layer、filter 数分别为 [16, 16, 32, 64]、每组 5 个 residual unit（§4.1）。这一步训练发生在检测之前，所以模型是在被污染的数据上训练的。
- 输出：训练好的模型 L 及其内部表征函数 R(·)。
- 出处：Algorithm 1 第 1–2 行；§4.1。
- 论文未说明：优化器、学习率、批大小、训练轮数、是否训练到收敛。

**步骤 3：为每个类提取逐样本表征（extract_layer_representation）**
- 输入：D_y 中的每个样本 x_i 和训练好的模型 L。
- 计算：做一次前向传播，取指定层的输出 R(x_i) ∈ R^d，并把该类所有样本的表征堆叠成矩阵。论文明确说表征可以来自自编码器或深层网络中被认为表示高层特征的某一层（§2.2），实验中取的是**倒数第二个 residual unit**（§4.1）。
- 输出：n×d 的逐样本表征矩阵。
- 出处：Algorithm 1 第 5–7 行；Figure 3；§2.2；§4.1。

**步骤 4：类内中心化（mean_center_features）**
- 输入：n×d 表征矩阵。
- 计算：先算类内均值 R̂ = (1/n) Σ_{i=1}^{n} R(x_i)，再算中心化矩阵 M = [R(x_i) − R̂]_{i=1}^{n}，即 n×d 的矩阵（Algorithm 1 第 6–7 行的原文记法：R̂ 写作 bR，M = [R(xi) − bR]）。
- 输出：n×d 的中心化表征矩阵 M，以及均值 R̂。
- 出处：Algorithm 1 第 6–7 行。

**步骤 5：取最大右奇异向量（top_right_singular_vector）**
- 输入：M（n×d）。
- 计算：对 M 做奇异值分解（singular value decomposition, SVD），取最大奇异值对应的**右奇异向量** v ∈ R^d（Algorithm 1 第 8 行 "Let v be the top right singular vector of M"）。等价地，v 是中心化协方差矩阵 MᵀM 的主特征向量——论文在理论部分正是把 v 定义为混合分布协方差矩阵的 top eigenvector（§3.1，Definition 3.1 与 Lemma 3.1）。
- 输出：单位向量 v。
- 出处：Algorithm 1 第 8 行；§3.1；Figure 3。

**步骤 6：计算逐样本离群分数（projection_outlier_score）**
- 输入：中心化表征 R(x_i) − R̂ 与 v。
- 计算：τ_i = ((R(x_i) − R̂) · v)²，即中心化表征在 v 上投影的平方（Algorithm 1 第 9 行；Figure 1 的说明把同一量描述为 "correlation with the top singular vector of the covariance matrix of examples"）。
- 输出：长度 n 的分数向量 τ。
- 出处：Algorithm 1 第 9 行；Figure 1 caption。

**步骤 7：删除每类得分最高的 1.5ε 比例样本（remove_top_fraction）**
- 输入：分数向量 τ、每类样本数 n、上界 ε。
- 计算：把 τ 从大到小排序，删除分数最高的 1.5·ε 个（论文原文写作 "Remove the examples with the top 1.5 · ε scores from Dy"，Algorithm 1 第 10 行）；剩下的样本构成新的 D_y。
- 输出：清洗后的类子集 D_y。
- 出处：Algorithm 1 第 10 行。
- 注意：算法对**每个标签 y** 都执行一次这个剔除（Algorithm 1 第 4 行的 `for all y do`），包括那些可能完全干净的类；论文没有区分"被污染的类"和"干净的类"。

**步骤 8：合并所有类的剩余样本并从头重训（retrain_from_scratch）**
- 输入：清洗后的各类子集。
- 计算：S ← ∪_y D_y（算法第 11–13 行），被删掉的样本被彻底丢弃（不重新标注），然后在 S 上**从随机初始化重新训练** L（第 14 行 "Re-train L on Dtrain from a random initialization"，不是继续训练或微调），最后返回 L（第 15 行）。
- 输出：最终分类器 L。
- 出处：Algorithm 1 第 11、13–15 行；§4.4（"one removal step … accuracies upon retraining"）。

## 4. 采样与规模控制

- 样本：**未抽样**。每个标签的全部样本都进入 M 并参与打分（n = |D_y|）。CIFAR-10 每个标签 5000 张（§1）；Figure 1 的统计图使用"5000 个正确标注的训练样本 + 500 个错误标注的中毒样本"（Figure 1 caption）。
- 客户端：论文未使用（集中式，没有客户端概念）。
- 层：没有随机抽样，而是**选择**。作者尝试了多个靠后的层，最后选择在倒数第二个 residual unit 上报告结果，因为平均而言该层剔除的中毒样本最多（§4.1）；另在 VGG 上做了同样实验（Table 5）。
- 参数坐标：没有显式的坐标抽样或截断；降维是隐式的——检测在 d 维表征上做，而不是在原图（3×32×32 = 3072 维）上做；d 的取值论文未说明。
- 轮次：只做**一次**剔除 + **一次**重训，表格里报告的是"剔除前（Nat 1 / Pois 1）"和"剔除后（Nat 2 / Pois 2）"两次训练迭代的结果（Table 2、Table 3、Table 4、Table 5）。论文未说明是否迭代执行"检测—剔除—重训"。
- 参考数据 / 探针：**未使用**。方法不需要干净参考集、根数据集（root dataset）或探针样本；它只依赖使用者假定的中毒上界 ε（Algorithm 1 第 1 行）。实验中 ε 取 5% 或 10%（Table 2、3、4、5），对应每类 5000 张中的 250 或 500 张（§1、§2.1、§4.2）。
- 评估规模：自然测试集为全部 10000 张 CIFAR-10 测试图，中毒测试集为攻击标签的 1000 张带后门图片（§4.4）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| ε | 训练集中中毒样本数量/比例的上界，同时是剔除比例的基数 | 实验取 5% 与 10%；正文说"as few as 250 corrupted training examples"（每类 5000 张中的 5%），Figure 2 的例子中 5% 不足以装入后门、10% 足够 | Algorithm 1 第 1 行；§1；§2.1；§4.2；§4.4；Table 2/3/4/5 |
| 1.5 | 剔除倍数，删除每类分数最高的 1.5ε 个样本 | 1.5 | Algorithm 1 第 10 行 |
| 表征层 | 提取 R(·) 的层 | 倒数第二个 residual unit（在 VGG 上也实验过，Table 5） | §4.1；Table 5 |
| 网络结构 | 用于训练与提供表征的模型 | ResNet：3 组 residual layer，filter 数 [16, 16, 32, 64]，每组 5 个 residual unit | §4.1 |
| 攻击配置 | (attack, target) 标签对、后门形状、位置、颜色 | 手工选的 4 对 (airplane, bird)、(automobile, cat)、(cat, dog)、(horse, deer)，随机选的 4 对 (automobile, dog)、(ship, frog)、(truck, bird)、(cat, horse)；形状取 pixel、X 或 L | §4.2 |
| 训练迭代数 | 剔除前一次训练、剔除后一次重训 | 2 次（Table 2/3/4/5 的 Nat 1、Nat 2 两列） | §4.4；Table 2 |
| 数据集规模 | 评估设置 | CIFAR-10，每类 5000 张训练图、10000 张测试图、每类 1000 张带后门测试图 | §1；§4.4 |
| 理论条件常数 | 可分离性条件 | Lemma 3.1：1/2 > ε > 0，且 ‖µD − µW‖² ≥ 6σ²/ε；Corollary A.2：1/4 > ε > 0，‖µD − µW‖² ≥ 10σ²/ε，n = Ω(d log n / ε)，成功概率至少 9/10 | Lemma 3.1；Corollary A.2 |
| 优化器 / 学习率 / 批大小 / epoch / 数据增广细节 / 表征维数 d | —— | **论文未说明** | —— |

## 6. 判定与动作

- 判定规则：**没有阈值，也没有聚类**。判定完全由"固定比例的 top-k 排序"决定：对每个标签 y，把 τ_i 降序排列，删除前 1.5·ε（Algorithm 1 第 10 行）。理论部分（Definition 3.1 的 ε-spectrally separable、Lemma 3.1 的均值分离条件）只用来解释"为什么这样排序能分出中毒子群"，算法本身并不检测或估计这些量。
- 动作：**删除样本**（filter_samples 语义），被删样本不重新标注、不加权；随后在剩余数据上**从随机初始化重训**（Algorithm 1 第 13–14 行）。
- 幅度：删除数量由 1.5ε 决定，是"过度删除"（over-removal），故意比假设的中毒量多删 50%。Table 2 报告剔除后剩余的真正中毒样本数（# Pois Left），例如 bird 5% 时从 250 降到 57，cat 10% 时为 0；说明多删不会显著损害自然准确率（Nat 2 约 92–93%，与干净训练基线 92.67% 相当，§4.4）。
- 加权 / 裁剪 / 加噪：**论文未使用**；方法不修改模型更新，只修改训练集。
- 跨轮累积：**论文未使用**。实验只做一次剔除与一次重训，没有把多轮的分数累积起来；论文也未说明是否应当累积或多轮迭代。
- 一个隐含前置条件：第一轮训练必须真的把后门装进去了（Pois 1 高），否则检测无信号。论文指出 Figure 2 的例子中 5% 中毒不足以 capture backdoor、10% 才够（§4.4），VGG 上多数情况 5% 也不足以装后门，因此只报告 10%（Table 5 caption）。

## 7. 需要的外部资源

- 一个**先在（可能被污染的）完整训练集上训练好的模型** L，以及其中被指定为"表征层"的那一层输出（Algorithm 1 第 1–2 行；§2.2）。这是方法的前置成本，也是它最主要的额外依赖。
- 所有训练样本的**类别标签**，用于按类分组（Algorithm 1 第 1、4–5 行）。
- **中毒上界 ε**：使用者必须预先假定中毒样本的数量或比例（Algorithm 1 第 1 行），实验中为 5%、10%。
- 论文**没有**使用干净参考数据、根数据集、预训练检测器、对齐前后的权重或额外模型；方法只需要 L 自身（§2.2、§4）。
- 规模：每类一个 n×d 的表征矩阵（CIFAR-10 上 n = 5000，d 论文未说明），外加一次完整训练的算力。
- 分析：若映射到联邦流程，服务器还需要每类的逐样本表征——这意味着客户端上传表征或把检测下放到客户端；论文未讨论这一资源需求。

## 8. 计算与存储开销

- 论文**没有报告**运行时间、FLOPs、内存或通信量。它只报告了统计量：表征均值的范数、均值漂移的范数，以及协方差矩阵的前三个奇异值（Table 1，例如 "Birds only" 的 1st SV 为 1194.223，"Birds + planes" 为 1613.486，说明中毒样本显著抬高了主奇异值）。
- 主要开销来源（分析：）：
  1. **两次完整训练**——第一次在污染数据上训练 L，第二次在清洗后的数据上从随机初始化重训（Algorithm 1 第 2、14 行）。这是绝对主导项。
  2. **一次全量前向传播**——为 N 个训练样本各算一次表征 R(x_i)，即"每条样本一次前向传播"（Algorithm 1 第 5–7 行）。
  3. **每类一次 SVD**——对 n×d 的 M 求最大右奇异向量；用完整 SVD 约为 O(n·d·min(n,d))，用截断/Lanczos 迭代则近似 O(n·d·k)，k 为所需奇异向量数（论文只取 1 个）。随类别数 C、每类样本数 n、表征维 d 增长（分析：）。
  4. 存储：每类一份 n×d 的表征矩阵；若按类串行处理，峰值约为 max_y n_y × d。理论样本复杂度 n = Ω(d log n / ε)（Corollary A.2）说明所需数据量随表征维 d 线性增长。

## 9. 实现时容易错的地方

论文明确强调或可从算法直接读出的点：

1. **必须在学习到的表征上做检测，不能在输入像素上做。** 作者明确说他们直接在输入上试过，即使去掉数据增广（后门不会被翻转或平移），信号仍然弱到检测不出来（§4.1；§1.1）。
2. **分数是"投影/相关性"而不是范数。** 论文明确说 ℓ2 范数或与随机向量的相关性不足以分离两类（§1.1、Figure 1）。
3. **分数取投影的平方** τ_i = ((R(x_i) − R̂)·v)²（Algorithm 1 第 9 行），因此 v 的符号不影响结果（分析：这一点论文没有明说，但由平方可得）。
4. **中心化用的是（可能被污染的）类内均值 R̂**，不是干净均值（Algorithm 1 第 6 行）。
5. **多删 50%**：删除 top 1.5ε 而不是 top ε（Algorithm 1 第 10 行）。
6. **重训必须从随机初始化开始**，不是接着第一轮继续训练（Algorithm 1 第 14 行）。
7. **每个类都执行剔除**，包括干净类（Algorithm 1 第 4 行的 for all y）。
8. **前提是第一轮真的装上了后门**；否则 Pois 1 很低、检测无意义（§4.4；Table 5 caption）。
9. **类内异质性会削弱可分性但不必然失败**：把 cats 和 dogs 合成 "pets" 后方法仍然有效（§4.5、Table 3）。

论文未说明、实现时必须自己决定的地方：

1. **ε 的单位**：Algorithm 1 第 1 行把 ε 定义为"中毒训练样本数量的上界"（计数），而第 10 行和全部实验都按比例使用 ε（5%、10%）。计数与比例之间如何换算，论文未说明。
2. **取整方式**：1.5·ε·n 是向上取整、向下取整还是四舍五入；当结果小于 1 或类别样本数很小时怎么处理，论文未说明。
3. **1.5ε ≥ 1 的边界**（例如小类别或高 ε）时是否清空整类，论文未说明。
4. **表征层的先验选择规则**：论文是事后按"平均剔除最多中毒样本"选的（§4.1），部署时如何事先选层，论文未说明。
5. **表征是否归一化、d 的具体数值**，论文未说明。
6. **SVD 的数值实现**（完整 SVD 还是截断迭代）与最大奇异值重复/退化时如何选 v，论文未说明。
7. **训练细节**：优化器、学习率、批大小、epoch 数、数据增广的具体设置、是否训练到收敛，论文均未说明（只提到默认使用了数据增广，§4.1）。
8. **是否迭代**"检测—剔除—重训"以及是否跨轮累积分数，论文未说明（实验只做一次）。
9. **标签是否可信**：算法按给定标签分组（Algorithm 1 第 1、4 行）；若攻击方式涉及改标签而非新增样本，方法行为论文未说明。
10. **理论中的 µD、µW、σ 在实际中不可观测**，论文只给出存在性保证（Lemma 3.1、Corollary A.2），没有给出可在运行时估计或检验这些量的方法。
11. **第一轮未能装上后门时的兜底逻辑**，论文未说明。
12. **联邦映射下的通信方案**（由谁算表征、如何按类聚合跨客户端的表征），论文完全未讨论。

## 10. 原文依据

以下引句均逐字摘自论文全文，用于支撑第 3 节的关键步骤。

1. **支撑步骤 1–3（先训练、再按类提取逐样本表征）**：*"We ﬁrst train a neural network on the data. Then, for each class, we extract a learned representation for each input from that class."*（Figure 3 caption）
2. **支撑步骤 3（表征层从网络内部选取）**：*"We take a black-box neural network with some designated learned representation. This can typically be the representation from an autoencoder or a layer in a deep network that is believed to represent high level features."*（§2.2）
3. **支撑步骤 4–6（在表征的协方差上做 SVD 并算离群分）**：*"We next take the singular value decomposition of the covariance matix of these representations and use this to compute an outlier score for each example."*（Figure 3 caption，原文含拼写 "matix"）
4. **支撑步骤 5–7（用 SVD 检测并删除提供信号的样本）**：*"As long as the signal is large in magnitude, we can detect it via singular value decomposition and remove the images that provide the signal."*（§2.2）
5. **支撑步骤 7–8（只做一次剔除并重训）**：*"We then record the number of poisoned images left after one removal step and the accuracies upon retraining."*（§4.4）
6. **支撑步骤 3 的层选择（倒数第二个 residual unit）**：*"We choose to report the results for the second to last residual unit simply because, on average, the method applied to this layer removed the most poisoned images."*（§4.1）
7. **支撑步骤 3 的必要性（输入层面检测无效）**：*"Even when data augmentation is removed, so that the backdoor is not ﬂipped or translated, the signal is still not strong enough to be detected"*（§4.1）
8. **支撑步骤 4–7 的理论依据（均值分离即可谱方法区分）**：*"if the mean of the true distribution of inputs of a certain class differs enough from the mean of the backdoored images, then these two classes can be reliably distinguished via spectral methods"*（§3.1）

```json
{
  "key": "tran2018spectral",
  "method": "谱特征（spectral signatures）：先在可能被污染的完整训练集上训练网络 L，按标签分组提取每个样本的学习表征，做类内中心化后取该类表征矩阵的最大右奇异向量 v，以样本在 v 上投影的平方为离群分，删除每类分数最高的 1.5ε 比例样本，再从随机初始化重训；论文为集中式方法，未涉及联邦流程。",
  "stages": ["server_aggregate", "server_post_aggregate", "outside_training"],
  "needs_round_trip": true,
  "pipeline": [
    {
      "step": "按标签分组训练样本",
      "operator": "group_samples_by_label",
      "input": "带标签训练集 Dtrain = {(x_i, y_i)}，图像 x_i（CIFAR-10 为 3×32×32）",
      "output": "C 个按标签划分的子集 D_y，以及每类的样本枚举 x_1..x_n（n=|D_y|）",
      "params": {"num_classes": "CIFAR-10 为 10", "samples_per_class": "5000（§1）"},
      "source": "Algorithm 1 第 1、4、5 行"
    },
    {
      "step": "在完整（可能被污染的）训练集上训练模型 L",
      "operator": "train_model_on_full_data",
      "input": "Dtrain",
      "output": "训练好的网络 L 及其内部表征函数 R(·)",
      "params": {"architecture": "ResNet：3 组 residual layer，filter 数 [16,16,32,64]，每组 5 个 residual unit（§4.1）", "optimizer_lr_epochs": "论文未说明"},
      "source": "Algorithm 1 第 1–2 行；§4.1"
    },
    {
      "step": "为每个类提取逐样本表征",
      "operator": "extract_layer_representation",
      "input": "D_y 中的每个样本 x_i 与模型 L",
      "output": "n×d 的逐样本表征矩阵（d 为表征维数，论文未给出具体数值）",
      "params": {"layer": "倒数第二个 residual unit（§4.1）；VGG 结果见 Table 5", "batch": "论文未说明"},
      "source": "Algorithm 1 第 5–7 行；Figure 3；§2.2；§4.1"
    },
    {
      "step": "类内中心化",
      "operator": "mean_center_features",
      "input": "n×d 表征矩阵",
      "output": "类内均值 R̂（d 维）与中心化矩阵 M = [R(x_i) − R̂]（n×d）",
      "params": {"mean": "R̂ = (1/n) Σ_{i=1..n} R(x_i)（Algorithm 1 第 6 行）"},
      "source": "Algorithm 1 第 6–7 行"
    },
    {
      "step": "取最大右奇异向量",
      "operator": "top_right_singular_vector",
      "input": "中心化矩阵 M（n×d）",
      "output": "最大奇异值对应的右奇异向量 v ∈ R^d（等价于 MᵀM 的主特征向量）",
      "params": {"num_vectors": 1, "solver": "论文未说明（完整 SVD 或截断 SVD 均可）"},
      "source": "Algorithm 1 第 8 行；§3.1（v 为混合分布协方差的主特征向量）；Figure 3"
    },
    {
      "step": "计算逐样本离群分数",
      "operator": "projection_outlier_score",
      "input": "中心化表征 R(x_i) − R̂ 与 v",
      "output": "长度 n 的分数向量 τ",
      "params": {"score": "τ_i = ((R(x_i) − R̂) · v)^2（投影的平方）"},
      "source": "Algorithm 1 第 9 行；Figure 1 caption"
    },
    {
      "step": "删除每类得分最高的 1.5ε 比例样本",
      "operator": "remove_top_fraction",
      "input": "分数向量 τ、每类样本数 n、中毒上界 ε",
      "output": "清洗后的类子集 D_y（被删样本不再使用、不重标标签）",
      "params": {"fraction": "1.5 · ε（Algorithm 1 第 10 行原文 top 1.5 · ε scores）", "ε": "实验中 5% 或 10%（Table 2/3/4/5）", "sort": "分数降序", "rounding": "论文未说明"},
      "source": "Algorithm 1 第 10 行；§4.4"
    },
    {
      "step": "合并剩余样本并从随机初始化重训",
      "operator": "retrain_from_scratch",
      "input": "所有清洗后的类子集 {D_y}",
      "output": "最终分类器 L",
      "params": {"merge": "S ← ∪_y D_y（Algorithm 1 第 11、13 行）", "init": "随机初始化（第 14 行，非继续训练）", "iterations": "论文只做一次剔除 + 一次重训"},
      "source": "Algorithm 1 第 11、13–15 行；§4.4"
    }
  ],
  "sampling": [
    {"what": "samples", "how": "未抽样：每个标签的全部训练样本都进入中心化矩阵 M 并参与打分", "size": "n = |D_y|，CIFAR-10 每类 5000 张（§1）；Figure 1 的统计使用 5000 个干净样本 + 500 个中毒样本"},
    {"what": "clients", "how": "论文为集中式方法，未使用客户端概念", "size": "论文未使用"},
    {"what": "layers", "how": "非随机抽样：尝试多个靠后的层，事后选择在倒数第二个 residual unit 上报告，因为该层平均剔除中毒样本最多；VGG 上另做实验", "size": "1 个表征层（§4.1）；VGG 结果见 Table 5"},
    {"what": "coordinates", "how": "无显式坐标抽样；通过使用 d 维学习表征而非原始像素实现隐式降维", "size": "表征维 d 论文未说明（原图为 3×32×32=3072 维）"},
    {"what": "rounds", "how": "只执行一次剔除与一次重训，报告剔除前后两次训练迭代的结果", "size": "1 次剔除 + 1 次重训（Table 2/3/4/5 的 Nat 1 与 Nat 2）"},
    {"what": "probes", "how": "未使用干净参考数据或探针样本；只依赖使用者给定的中毒上界 ε", "size": "ε = 5% 或 10%（Table 2/3/4/5），对应每类 5000 张中的 250/500 张"}
  ],
  "resources": [
    "一个先在（可能被污染的）完整训练集上训练好的模型 L，以及被指定为表征层的内部层输出（Algorithm 1 第 1–2 行）",
    "每个训练样本的类别标签，用于按标签分组（Algorithm 1 第 1、4–5 行）",
    "使用者预先假定的中毒样本上界 ε（Algorithm 1 第 1 行；实验中为 5%、10%）",
    "论文未使用干净参考数据、根数据集、预训练检测器或额外模型",
    "分析：映射到联邦流程时服务器需要每类的逐样本表征，需要客户端额外上传表征或把检测下放到客户端（论文未讨论联邦）"
  ],
  "actions": ["filter_samples"],
  "dominant_cost": "论文未报告运行时间、FLOPs、内存或通信量，只报告了表征均值范数与前三个奇异值等统计量（Table 1）。分析：主要开销是两次完整训练（污染数据上的初次训练 + 清洗后从随机初始化的重训），其次是对全部 N 个训练样本各一次前向传播提取表征，再次是每类一次 n×d 矩阵的最大右奇异向量计算（完整 SVD 约 O(n·d·min(n,d))，截断迭代约 O(n·d·k)）；存储为每类一份 n×d 表征矩阵，按类串行处理时峰值约为 max_y n_y × d。",
  "underspecified": [
    "ε 的单位：Algorithm 1 第 1 行定义为中毒样本数量的上界，第 10 行与实验却按比例（5%、10%）使用，换算方式论文未说明",
    "删除数量的取整方式（floor/ceil/四舍五入）以及结果小于 1 时的处理，论文未说明",
    "当 1.5ε ≥ 1（小类别或高 ε）时是否清空整类，论文未说明",
    "部署时如何先验地选择表征层（论文是事后按剔除效果选的），论文未说明",
    "表征是否做归一化、表征维数 d 的具体取值，论文未说明",
    "SVD 的具体数值实现，以及最大奇异值重复/退化时如何唯一确定 v，论文未说明",
    "优化器、学习率、批大小、训练轮数、数据增广细节、是否训练到收敛，论文均未说明",
    "是否迭代执行检测—剔除—重训，以及是否跨轮累积分数，论文未说明（实验只做一次）",
    "标签被攻击者篡改（而非仅新增样本）时方法的行为，论文未说明",
    "理论中的 µD、µW、σ 在运行时不可观测，论文未给出估计或检验方法",
    "第一轮未能装入后门时的兜底逻辑，论文未说明",
    "联邦映射下由谁计算表征、如何跨客户端按类聚合表征，论文完全未讨论"
  ],
  "quotes": [
    {"supports": "步骤 1–3：先训练网络，再按类提取逐样本表征", "text": "We ﬁrst train a neural network on the data. Then, for each class, we extract a learned representation for each input from that class."},
    {"supports": "步骤 3：表征来自网络中指定的学习表征层", "text": "We take a black-box neural network with some designated learned representation. This can typically be the representation from an autoencoder or a layer in a deep network that is believed to represent high level features."},
    {"supports": "步骤 4–6：在表征协方差上做 SVD 并计算逐样本离群分", "text": "We next take the singular value decomposition of the covariance matix of these representations and use this to compute an outlier score for each example."},
    {"supports": "步骤 5–7：用 SVD 检测并删除提供信号的样本", "text": "As long as the signal is large in magnitude, we can detect it via singular value decomposition and remove the images that provide the signal."},
    {"supports": "步骤 7–8：只做一次剔除并重训", "text": "We then record the number of poisoned images left after one removal step and the accuracies upon retraining."},
    {"supports": "步骤 3：表征层选择为倒数第二个 residual unit", "text": "We choose to report the results for the second to last residual unit simply because, on average, the method applied to this layer removed the most poisoned images."},
    {"supports": "步骤 3：必须在学习表征上检测，输入层面信号不足", "text": "Even when data augmentation is removed, so that the backdoor is not ﬂipped or translated, the signal is still not strong enough to be detected"},
    {"supports": "步骤 4–7 的理论依据：均值分离即可用谱方法区分两类", "text": "if the mean of the true distribution of inputs of a certain class differs enough from the mean of the backdoored images, then these two classes can be reliably distinguished via spectral methods"}
  ]
}
```
