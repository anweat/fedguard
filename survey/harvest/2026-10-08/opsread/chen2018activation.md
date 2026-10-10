# chen2018activation：Activation Clustering（激活聚类，简称 AC）

## 1. 方法一句话

输入是一个用可能被投毒的训练集 Dp 训练出来的 DNN FΘP 以及该训练集本身；方法把每个训练样本在 FΘP 最后一层隐层的激活取出来、按类别分段、降维后用 2-means 聚成两簇，再判断哪一簇（如果有）是后门毒样本（poisonous data），输出"哪些训练样本是毒样本、它们的源类（source class）是什么"，并可选地通过重标注加继续训练（或删除毒样本重训）输出一个修复后的模型。

## 2. 运行位置

论文本身是集中式（centralized）方法，不是联邦方法：它在单一数据集 Dp 上训练模型，然后用同一个训练集查询模型，全过程没有客户端与服务器的区分，也没有任何客户端-服务器往返。下面按联邦流程给出最自然的映射，均标"分析："。

- 步骤 1（训练 FΘP）：对应"服务器聚合之后（server_post_aggregate）"，即先存在一个（可能已被投毒数据影响的）全局模型。分析：论文中的训练是集中式一次性训练，不涉及联邦轮次。
- 步骤 2～5（取激活、按类分组、ICA 降维、2-means 聚类）：分析：这些步骤要求"模型"和"该模型见过的训练样本"同处一地。在联邦中训练数据留在客户端，因此最自然的位置是"客户端训练后（client_post_train）"；如果服务器持有全部数据或能拿到激活，也可以放在"服务器聚合之后（server_post_aggregate）"。
- 步骤 6（Exclusionary Reclassification，ExRe）：分析：它需要"排除某一簇后重新训练一个模型"，在联邦里意味着额外的训练过程，可能占用额外的联邦轮次或放到服务器端离线执行；这会产生客户端-服务器之间额外的往返（论文没有提出任何联邦协议）。
- 步骤 7～10（相对大小、轮廓系数、簇摘要）：分析：前两者与聚类同地执行（client_post_train 或 server_post_aggregate）；簇摘要属于给人看的离线核验，放在"训练之外（outside_training）"。
- 步骤 11～12（修复重训）：分析：如果继续保留联邦训练，重标注后的样本在"客户端训练前（client_pre_train）"参与后续轮次的本地训练；也可以整体视为"训练之外（outside_training）"的一次重新训练，完成后替换部署的模型。

是否需要额外往返：论文自身不需要（集中式）；分析：若要在联邦中把激活提取放到服务器而数据留在客户端，则需要额外一次往返来上传激活或下发模型，且 ExRe 还需要一整轮额外训练。

## 3. 算子流水线

下面按执行顺序列出。论文没有给出任何步骤的实现代码级细节，凡原文没写的都在第 9 节集中列出。

**步骤 1：训练可疑 DNN FΘP（train_classifier）**
- 输入：未受信任的训练集 Dp = (X, Y)，含 n 个类标签；论文用到的具体数据集见第 7 节。
- 计算：在 Dp 上常规训练一个 DNN。论文未说明训练轮数、优化器、学习率等训练超参；只用文字给出模型结构：MNIST 用 2 个卷积层 + 2 个全连接层的 CNN，LISA 用 Simonyan and Zisserman (2014) 的 Architecture A 变体，文本用 Britz (2015) 与 Kim (2014) 描述的 Rotten Tomatoes 分类器。
- 输出：模型 FΘP。
- 出处：Algorithm 1 第 1 行；§4 Case Studies；§5。

**步骤 2：提取最后一层隐层激活并展平（last_hidden_layer_activations）**
- 输入：FΘP 与每一个训练样本 s ∈ Dp，逐个前向传播。
- 计算：As ← FΘP 最后一层隐层的激活，展平成一个 1D 向量；把 As 追加到 A[FΘP(s)]。论文强调只用最后一层隐层就够，早期层"更不可能指示毒样本，只会给分析加噪"。
- 输出：每个样本一个 1D 激活向量 As（长度记为 d，论文未给出 d 的具体数值）。
- 出处：Algorithm 1 第 3～6 行；§5。

**步骤 3：按类别把激活分段（group_activations_by_predicted_label）**
- 输入：全部 As 及其对应类别。
- 计算：按类别把激活分组，A[i] 保存所有满足 FΘP(si) = i 的样本的激活；每个类别段单独聚类，不跨类混合。注意 Algorithm 1 第 2 行和第 5 行用的是预测标签 FΘP(s)，而正文措辞是"their label"，两者存在歧义（见第 9 节）。
- 输出：A[i]，形状为 N_i × d 的激活矩阵，N_i 为该类样本数。
- 出处：Algorithm 1 第 2、5 行；§5"they are segmented according to their label and each segment clustered separately"。

**步骤 4：ICA 降维（ica_projection）**
- 输入：A[i]（N_i × d）。
- 计算：先确认激活已展平成 1D 向量，再用 Independent Component Analysis（ICA，独立成分分析）做降维，投影到 10 个独立成分。论文说明降维是必要的，因为高维下欧氏距离（Euclidean metric）区分近邻与远点的能力下降；并指出 ICA 比 Principal Component Analysis（PCA，主成分分析）更有效。
- 输出：red_i（N_i × 10）。
- 出处：§5 降维段落；§6 实验设置（"projected onto 10 independent components"，并说明试过 6、10、14 个成分结果大致相同）。

**步骤 5：2-means 聚类（kmeans_2）**
- 输入：red_i（N_i × 10）。
- 计算：k-means，k = 2。论文还试过 DBSCAN、Gaussian Mixture Models（GMM）和 Affinity Propagation，认为 k-means 在速度与准确率上最好。论文明确指出 k-means 无论有没有毒都会把数据分成两簇，所以必须接一个簇分析步骤。
- 输出：每个样本的簇编号，以及两个簇的样本数与占比。
- 出处：§5 聚类段落；§6 实验设置。

**步骤 6：排除式重分类判定（retrain_without_subset_and_reclassify，ExRe）**
- 输入：Dp、待检验簇 c 的样本索引、以及重训所需的模型架构/训练配置。
- 计算：不用簇 c 中的数据、在 Dp 的其余部分上训练一个新模型；再用这个新模型去分类被移除的簇 c 的样本。令 l = 簇中被分回其原标签的样本数，p = 被分为类别 C 的样本数，其中 C 是除原标签外被分到最多的那个类。若 l/p > T 判该簇为合法，若 l/p < T 判该簇为毒，此时 C 就是毒样本的源类。论文给出的默认阈值 T = 1，可由防御者调整。
- 输出：每个簇的"毒/干净"判定、ExRe 分数 l/p、以及毒簇的源类标签。
- 出处：§5 Exclusionary Reclassification 段落；§6.3 与 Table 3（前两行是"被排除簇被分为源类/原标签的比例"，第三行是 ExRe 分数）。

**步骤 7：相对大小判定（cluster_size_ratio_test）**
- 输入：两个簇的大小（占比）。
- 计算：论文观察到毒激活几乎总是（> 99% 的情况下）与合法激活落在不同簇，因此当某个标签下有 p% 的数据被投毒时，两簇大小应约为 p% 与 (100 − p)%；数据未被投毒时两簇大小往往接近 50/50。若防御者预期某个标签最多有 p% 的数据被投毒，则把占比 ≤ p% 的那个簇判为毒簇。
- 输出：哪个簇（若有）是毒簇。
- 出处：§5 Relative Size Comparison 段落；§6.3 与 Table 3 第 4、5 行。

**步骤 8：轮廓系数判定（silhouette_score_test）**
- 输入：red_i 与 k = 2 的聚类结果。
- 计算：计算 silhouette score（轮廓系数）。低分说明聚类不拟合数据、该类可视为未被投毒；高分说明两簇确实更好地描述数据，此时假定攻击者无法投毒超过一半数据，把较小的簇判为毒簇。论文在没有可信数据时建议阈值取 0.10 到 0.15 之间；理想情况下用干净可信数据确定干净数据的期望轮廓系数。
- 输出：该类是否被投毒 + 较小的簇为毒簇。
- 出处：§5 Silhouette Score 段落；§6.3 与 Table 3 第 6 行。

**步骤 9：图像簇摘要，供人工核验（cluster_image_sprite_summary）**
- 输入：某个簇内样本对应的原始图像。
- 计算：把簇内每张图缩放到很小尺寸后拼成 mosaic（sprite 图）；同时给出簇内图像的平均图。
- 输出：sprite 拼图与平均图，交给用户肉眼判断该簇是否异常、正确标签是什么。
- 出处：§5.1 与 Figure 3、Figure 4。

**步骤 10：文本簇摘要，供人工核验（lda_topic_summary）**
- 输入：簇内样本文本（先做词干化）。
- 计算：用 Latent Dirichlet Allocation（LDA，潜在狄利克雷分配）提取主题；把常用停用词与整个数据集最常见的主题词一起加入停用词表，以凸显簇间差异。论文用 2 个主题、每个主题 6 个词。
- 输出：每个簇的主题词列表（例如毒簇主主题含 "travelerthehors"）。
- 出处：§5.1。

**步骤 11：修复——重标注并继续训练（relabel_source_class_and_retrain）**
- 输入：被判为毒的样本、ExRe 给出的源类标签、当前模型。
- 计算：把毒样本的标签改成它的源类，然后只在这些样本上继续训练模型直到再次收敛。
- 输出：修复后的模型。
- 出处：§5.2 Backdoor Repair；§6.4（MNIST 上只训练修复样本 14 个 epoch 收敛）。

**步骤 12（可选替代修复）：删除毒样本从头重训（drop_poison_and_retrain）**
- 输入：去掉毒样本后的数据集。
- 计算：直接删除毒样本并在完整数据上从头训练模型。论文把这作为第一种选择，但指出更快的选择是步骤 11。
- 输出：修复后的模型。
- 出处：§5.2；§6.4（从头重训在完整数据集上需要 80 个 epoch）。

## 4. 采样与规模控制

- 层（layers）：只使用最后一层隐层的激活，丢弃所有早期层。论文在 MNIST 上的实验显示只用最后一层隐层时检测率反而提升。论文未给出该层激活展平后的维度 d。
- 坐标（coordinates）：对每个类别的激活做 ICA 降维后再聚类，降到 10 个独立成分（这是降维，不是抽样）。论文另试过 6 与 14 个成分，结果大致相同（§6 实验设置）。
- 样本（samples）：按类别把训练样本分段，每个类别单独做降维与聚类，不抽样、不跨类混合；每一类用该类全部样本（Algorithm 1 第 7～10 行、§5）。
- 客户端与轮次（clients/rounds）：论文不是联邦方法，未对客户端或轮次做任何抽样或截断。
- 参考数据或探针（probes）：论文未使用。论文把"不需要经过验证的可信数据集"作为核心贡献，并明确把需要 10,000 到 60,000 条可信样本的 Liu et al. (2017b) 作为对比。
- 与规模有关的实验变量（不是方法自身的抽样）：MNIST 每类投毒 10%，另测 15% 与 33%；LISA stop sign 类投毒 33% 与 15%，论文脚注说明 ≤10% 时无法成功植入后门；LISA warning 类投毒 30% 以便学到多个后门；Rotten Tomatoes 负类投毒 10%（§4、§6.1、§6.3）。
- ExRe 的重训数据是"去掉被检簇之后的 Dp 其余部分"；修复阶段只在被重标注的毒样本上继续训练（§5.2、§6.4）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
| --- | --- | --- | --- |
| 激活来源层 | 用哪一层的激活做检测 | 最后一层隐层 | Algorithm 1 第 4 行；§5 |
| 降维方法 | 降维算法 | ICA（优于 PCA） | §5 降维段落 |
| 独立成分数 | ICA 投影后的维度 | 10；另试 6、10、14，结果大致相同 | §6 实验设置 |
| 聚类算法 | 聚类方法 | k-means（也试过 DBSCAN、GMM、Affinity Propagation） | §5 聚类段落 |
| 簇数 k | k-means 的簇数 | 2 | §5；§6 |
| 距离度量 | 聚类所用距离 | 欧氏距离 | §5 降维段落 |
| ExRe 阈值 T | l/p 的判定门限 | 默认 1，可由防御者调整 | §5 ExRe 段落 |
| 相对大小阈值 p | 防御者预期的单类最大投毒比例 | 论文未给默认值（只说"若预期不超过 p%"）；实验中毒化比例为 10%、15%、30%、33% | §5 Relative Size 段落；§6.1、§6.3 |
| 轮廓系数阈值 | 判定类是否被投毒 | 建议 0.10～0.15（无可信数据时） | §5 Silhouette 段落；§6.3 |
| LDA 主题数与词数 | 文本簇摘要 | 2 个主题，每个主题 6 个词 | §5.1 |
| 修复训练轮数 | 在重标注样本上继续训练 | MNIST 上 14 个 epoch 收敛（从头重训为 80 个 epoch） | §6.4 |

## 6. 判定与动作

- 聚类规则：每个类别内固定用 k = 2 聚类，k 值不随是否投毒变化；k-means 总会输出两簇，所以判定完全依赖第 6～8 步的簇分析。
- ExRe 判定：计算 l（被分回原标签的样本数）与 p（被分为除原标签外最多类别 C 的样本数）。l/p > T 判为合法簇，l/p < T 判为毒簇，源类为 C；默认 T = 1（§5）。Table 3 中投毒簇的 ExRe 分数为 0～0.13，干净簇为 3.54～315.5。
- 相对大小判定：占比 ≤ p% 的簇判为毒簇；论文观察到未投毒时两簇常接近 50/50，最差情况（MNIST 4 与 7+）为 70/30（§5、§6.3）。
- 轮廓系数判定：分数高于阈值（0.10～0.15）时认为两簇拟合更好，取较小簇为毒簇；低于阈值认为该类未被投毒（§5、§6.3）。
- 动作一：告警/人工核验。三个分析方法都只是"alerting the user to possible data poisoning"，用户可用 sprite、平均图或 LDA 主题进一步确认（§5.1）。
- 动作二：过滤样本（filter_samples）。论文给出的第一种修复是直接删除被判定为毒的样本，然后在干净化后的数据集上从头重训（§5.2）。
- 动作三：编辑样本（edit_samples）。更快的修复是把毒样本的标签改成 ExRe 推断出的源类，再在这些样本上继续训练到收敛；Table 4 显示 33% 投毒数据集上各类错误率从 31%～35% 降到 0%～1.6%（§5.2、§6.4）。
- 动作四：替换模型（replace_global）。两种修复都会产出一个新的、去掉后门的模型用于部署，等价于用修复后的模型替换被投毒的模型（§5.2、§6.4）。
- 阈值/幅度：方法不涉及裁剪幅度或加噪幅度（没有 clip、noise 类动作），唯一的数值动作是重标注与重训。
- 跨轮累积：论文是集中式单次流程，没有跨轮累积、没有滑动统计量；论文未说明任何跨轮机制。

## 7. 需要的外部资源

- 未受信任的训练集 Dp 本身：必须能用它对 FΘP 做前向传播取激活，也要用它做 ExRe 的重训与修复训练（§5、§6）。
- 一个已训练好的可疑模型 FΘP，以及训练它所用的架构与超参；论文用了三种结构（MNIST 的 2 卷积 + 2 全连接 CNN、LISA 的 VGG Architecture A 变体、文本的 CNN 分类器），规模随数据集而变（§4、§5）。
- ExRe 所需的重训能力：在 Dp 去掉被检簇后重新训练一个模型（§5）。论文未说明重训是否沿用同一套架构与超参。
- 论文明确不需要：可信/干净数据集、根数据集（root dataset）、预训练检测器、对齐前后的权重。论文把这一点作为与 Steinhardt et al. (2017)、Liu et al. (2017b)、Liu et al. (2018) 的关键区别。
- 可选资源：若希望轮廓系数阈值更可靠，可用一个干净可信数据集来确定干净数据的期望轮廓系数；论文说这只在"ideally"情况下需要（§5 Silhouette 段落）。
- 规模参考：论文没有给出 MNIST/LISA/Rotten Tomatoes 的样本总量；只给出文本实验中两个簇分别含 4798 与 479 个观测（§5.1）。论文引用对比方法需要 10,000～60,000 条可信 MNIST 样本，用以说明本方法对可信数据零需求。

## 8. 计算与存储开销

论文报告的开销：

- ExRe "requires retraining the model, which can be computationally expensive"（§5 ExRe 段落）；相对大小方法被描述为 "simpler and faster"（§5 Relative Size 段落）。
- k-means 是从速度与准确率两方面选出的（"the most effective in terms of speed and accuracy"，§5）。
- 修复重训：在 MNIST 基线上只在修复样本上训练，14 个 epoch 收敛；从头在完整数据集上重训需要 80 个 epoch（§6.4）。
- 检测效果：MNIST 10% 投毒时各类准确率 99.89%～100%、F1 99.83%～100%，平均准确率 99.97%、平均 F1 99.96%（Table 1）；LISA 在 33% 与 15% 投毒下准确率与 F1 均为 100%；Rotten Tomatoes 10% 投毒下准确率与 F1 均为 100%（§6.1）；多模态/多源投毒实验准确率 99.9%～100%（Table 2）。
- 论文未报告运行时间、内存占用、GPU 型号或吞吐量等量化开销。

分析（按流水线）：

- 主要开销来自第 6 步 ExRe：每分析一个类别就要完整重训一个新模型，因此总开销约为"被分析类别数 × 一次完整训练"；若对 n 个类都做 ExRe，就是 n 次训练。这也是论文说它 expensive 的原因。
- 第二步开销是步骤 2 的前向传播与激活存储：对全部 N 个训练样本各做一次前向传播，并把 N × d 的激活全部保存在内存中；d 是最后隐层展平后的维度，随该层宽度增长。
- 步骤 4 的 ICA 在每类 N_i × d 的矩阵上做，步骤 5 的 2-means 只在 N_i × 10 的低维矩阵上做，两者相对 ExRe 都很便宜；步骤 9、10 的摘要成本与簇内样本数成正比。
- 分析：在联邦映射下，如果激活提取放在客户端，通信开销与"客户端数 × 激活维度 × 样本数"相关；论文没有讨论。

## 9. 实现时容易错的地方

论文明确强调的实现细节：

- 只用最后一层隐层的激活；论文报告早期层会引入噪声、只用最后一层反而提高检测率（§5）。
- 聚类前必须降维，否则高维下欧氏距离失效；论文选择 ICA 而不是 PCA（§5）。
- k = 2 的 k-means 无论数据是否被投毒都会给出两个簇，不能把聚类本身当作检测器，必须接 ExRe、相对大小或轮廓系数（§5）。
- ExRe 的新模型是"不用被检簇的数据"训练的，l 与 p 都是这个新模型对被移除样本的分类统计，而不是原模型 FΘP 的分类统计（§5）。
- 轮廓系数阈值 0.10～0.15 并非 100% 准确：Table 3 中 10 个投毒类里有两个的分数是 0.10 和 0.09，会落在阈值之下（§6.3）。
- 相对大小法依赖"未投毒时两簇接近 50/50"的先验，但最差见过 70/30（MNIST 4 与 7+），所以 p 的取值要留余量（§6.3）。
- 轮廓系数用"较小簇为毒"的规则时假定攻击者无法投毒超过一半数据（§5）。
- Table 3 里 LISA Speed Limit 的投毒簇只有 45% 的样本被分为源类，ExRe 分数 0.13，仍小于阈值 1，所以判定依然正确；不要假设毒样本一定会被高比例分回源类（§6.3）。
- 论文报告 LISA 上"≤10% 目标类被投毒时无法成功植入后门"，说明检测率与攻击是否成功植入强相关（§6.1 脚注 1）。
- 多模态类别本身也可能自然裂成两簇；论文用 7+（7、8、9 合并）和 warning 类做了专门实验，全部接近 100%（§6.2）。

论文没说清、实现时必须自己决定的地方：

- ICA 的具体实现（FastICA 还是别的算法）、随机初始化与随机种子，论文未说明。
- k-means 的初始化方式、迭代次数、n_init、随机种子，论文未说明。
- ExRe 重训新模型时是否沿用同一架构、同一超参、同样的训练轮数，是全新训练还是微调，论文未说明。
- "segmented according to their label"里的 label 究竟指真实标签还是预测标签 FΘP(s)：Algorithm 1 第 2、5 行明确用预测标签，正文措辞含糊（§5）。
- ExRe 分数恰好等于阈值 T 时怎么判，论文只写了 l/p > T 与 l/p < T 两种情形，等号情形未说明。
- 两个簇都被判为毒、或都不被判为毒、或某类只有极少样本、簇为空、样本数少于独立成分数等边界情况，论文未说明。
- 相对大小法里"防御者预期的最大投毒比例 p"如何取默认值，论文未说明，只给了实验中的毒化比例。
- 修复阶段的学习率、优化器、批大小和"until it converges"的停止准则未定义，论文只报告 MNIST 上 14 个 epoch。
- Algorithm 1 的输入写标签为 {1, ..., n}，循环却写 i = 0 to n，类别索引约定不一致，实现时需要自行统一。
- 文本摘要的词干化工具、停用词表内容，"把总体主题加入停用词"的具体做法，论文未说明。
- 论文没有报告时间、内存或硬件开销，无法据此估算资源需求。
- 论文在同一套记号里用 p 表示两种不同的量：ExRe 中的"被分为 C 的样本数"和相对大小法里的"投毒百分比 p%"，实现时不要混用。

## 10. 原文依据

1. 支撑步骤 1 与步骤 2（训练可疑模型并提取最后隐层激活）："First, the neural network is trained using untrusted data that potentially includes poisonous samples. Then, the network is queried using the training data and the resulting activations of the last hidden layer are retained."
2. 支撑步骤 3（按标签把激活分段、逐类聚类）："Once the activations are obtained for each training sample, they are segmented according to their label and each segment clustered separately."
3. 支撑步骤 4（展平为 1D 后用 ICA 降维）："To cluster the activations, we first reshaped the activations into a 1D vector and then performed dimensionality reduction using Independent Component Analysis (ICA), which was found to be more effective than Principle Component Analysis (PCA)."
4. 支撑步骤 5（k = 2 的 k-means）："After dimensionality reduction, we found k-means with k = 2 to be highly effective at separating the poisonous from legitimate activations."
5. 支撑步骤 6（ExRe 的重训与重分类流程）："Our first cluster analysis method involves training a new model without the data corresponding to the cluster(s) in question. Once the new model is trained, we use it to classify the removed cluster(s)."
6. 支撑步骤 7（相对大小判定）："Thus, when p% of the data with a given label is poisoned, we expect that one cluster contains roughly p% of the data, while the other cluster contains roughly (100 −p)% of the data."
7. 支撑步骤 8（轮廓系数阈值）："Otherwise, our experiments on MNIST, LISA and Rotten Tomatoes datasets indicate that a threshold between .10 and .15 is reasonable."
8. 支撑步骤 11（重标注源类并继续训练修复）："A faster option, however, is to relabel the poisonous data with its source class and continue to train the model on these samples until it converges again."

```json
{
  "key": "chen2018activation",
  "method": "Activation Clustering (AC)",
  "stages": ["client_post_train", "server_post_aggregate", "outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {"step": "训练可疑 DNN FΘP", "operator": "train_classifier", "input": "未受信任的训练集 Dp=(X,Y)", "output": "可能含后门的模型 FΘP", "params": {}, "source": "Algorithm 1 line 1; §5"},
    {"step": "提取最后隐层激活并展平", "operator": "last_hidden_layer_activations", "input": "FΘP 与每个训练样本 s∈Dp", "output": "每个样本一个 1D 激活向量 As（长度 d，论文未给出 d）", "params": {}, "source": "Algorithm 1 lines 3-6; §5"},
    {"step": "按类别把激活分段", "operator": "group_activations_by_predicted_label", "input": "全部 As 与对应类别", "output": "A[i]：N_i×d 的激活矩阵", "params": {}, "source": "Algorithm 1 lines 2,5; §5"},
    {"step": "ICA 降维", "operator": "ica_projection", "input": "A[i]（N_i×d）", "output": "red_i（N_i×10）", "params": {"n_components": 10}, "source": "§5; §6 实验设置"},
    {"step": "2-means 聚类", "operator": "kmeans_2", "input": "red_i（N_i×10）", "output": "两个簇的样本分配与簇大小", "params": {"k": 2}, "source": "§5; §6 实验设置"},
    {"step": "排除式重分类判定（ExRe）", "operator": "retrain_without_subset_and_reclassify", "input": "Dp 与待检簇的样本索引", "output": "ExRe 分数 l/p、毒/干净判定、源类 C", "params": {"T": 1}, "source": "§5 Exclusionary Reclassification; §6.3 Table 3"},
    {"step": "相对大小判定", "operator": "cluster_size_ratio_test", "input": "两个簇的大小占比", "output": "哪个簇（若有）是毒簇", "params": {"p": "防御者预期的最大投毒比例，论文未给默认值"}, "source": "§5 Relative Size Comparison; §6.3 Table 3"},
    {"step": "轮廓系数判定", "operator": "silhouette_score_test", "input": "red_i 与 k=2 聚类结果", "output": "该类是否被投毒 + 较小簇为毒簇", "params": {"threshold": "0.10-0.15"}, "source": "§5 Silhouette Score; §6.3 Table 3"},
    {"step": "图像簇摘要（人工核验）", "operator": "cluster_image_sprite_summary", "input": "簇内样本的原始图像", "output": "sprite 拼图与簇内平均图", "params": {}, "source": "§5.1; Figure 3, Figure 4"},
    {"step": "文本簇摘要（人工核验）", "operator": "lda_topic_summary", "input": "簇内样本文本（先词干化）", "output": "每个簇的 LDA 主题词", "params": {"n_topics": 2, "n_words_per_topic": 6}, "source": "§5.1"},
    {"step": "重标注源类并继续训练修复", "operator": "relabel_source_class_and_retrain", "input": "毒样本 + 源类标签 + 当前模型", "output": "修复后的模型", "params": {"epochs": "MNIST 实验 14，论文只给这一个实例"}, "source": "§5.2; §6.4"},
    {"step": "可选：删除毒样本从头重训", "operator": "drop_poison_and_retrain", "input": "去掉毒样本后的数据集", "output": "修复后的模型", "params": {"epochs": "MNIST 实验 80"}, "source": "§5.2; §6.4"}
  ],
  "sampling": [
    {"what": "layers", "how": "只保留最后一层隐层的激活，丢弃早期层", "size": "1 层（论文未给出该层展平维度 d）"},
    {"what": "coordinates", "how": "对每个类别的激活做 ICA 降维后再聚类", "size": "10 个独立成分（另试 6、10、14）"},
    {"what": "samples", "how": "按类别把训练样本分段，每类单独降维与聚类，不跨类混合", "size": "每类全部样本，不抽样"},
    {"what": "probes", "how": "论文未使用任何参考数据或探针（明确不要求可信数据）", "size": "0"}
  ],
  "resources": [
    "未受信任的训练集 Dp 本身（需要能对模型做前向查询）",
    "已训练好的可疑 DNN FΘP 及其架构与超参",
    "ExRe 所需的重训能力：在 Dp 去掉被检簇后重新训练一个模型",
    "论文明确不需要可信/干净数据集、根数据集或预训练检测器",
    "可选：可信数据集，仅用于校准干净数据的期望轮廓系数"
  ],
  "actions": ["filter_samples", "edit_samples", "report_only", "replace_global"],
  "dominant_cost": "Exclusionary Reclassification 每分析一个类别就要完整重训一个模型（论文称其 computationally expensive）；其次是全训练集前向传播取激活并保存 N×d 激活矩阵。",
  "underspecified": [
    "ICA 的具体算法、随机初始化与随机种子，论文未说明。",
    "k-means 的初始化、迭代次数、n_init 与随机种子，论文未说明。",
    "ExRe 重训新模型是否沿用同一架构与超参、训练多少轮、是全新训练还是微调，论文未说明。",
    "“segmented according to their label”指真实标签还是预测标签 FΘP(s)：Algorithm 1 用预测标签，正文措辞含糊。",
    "ExRe 分数恰好等于阈值 T 时如何判定，论文未说明。",
    "两个簇都被判为毒、或都不被判为毒时如何处理，论文未说明。",
    "簇为空、类别样本过少、样本数少于独立成分数等边界情况，论文未说明。",
    "相对大小法的预期最大投毒比例 p 如何取默认值，论文未说明。",
    "修复阶段的学习率、优化器、批大小与“until it converges”的停止准则未定义，只报告 MNIST 上 14 个 epoch。",
    "Algorithm 1 输入标签写 {1,...,n}，循环却写 i = 0 to n，索引约定不一致。",
    "文本摘要的词干化工具、停用词表与“把总体主题加入停用词”的做法，论文未说明。",
    "论文没有报告时间、内存或硬件开销等量化指标。"
  ],
  "quotes": [
    {"supports": "步骤 1、2：训练可疑模型并用训练数据查询取得最后隐层激活", "text": "First, the neural network is trained using untrusted data that potentially includes poisonous samples. Then, the network is queried using the training data and the resulting activations of the last hidden layer are retained."},
    {"supports": "步骤 3：按标签分段、逐类聚类", "text": "Once the activations are obtained for each training sample, they are segmented according to their label and each segment clustered separately."},
    {"supports": "步骤 4：展平成 1D 后用 ICA 降维", "text": "To cluster the activations, we first reshaped the activations into a 1D vector and then performed dimensionality reduction using Independent Component Analysis (ICA), which was found to be more effective than Principle Component Analysis (PCA)."},
    {"supports": "步骤 5：k = 2 的 k-means 聚类", "text": "After dimensionality reduction, we found k-means with k = 2 to be highly effective at separating the poisonous from legitimate activations."},
    {"supports": "步骤 6：ExRe 的排除重训与重分类", "text": "Our first cluster analysis method involves training a new model without the data corresponding to the cluster(s) in question. Once the new model is trained, we use it to classify the removed cluster(s)."},
    {"supports": "步骤 7：相对大小判定", "text": "Thus, when p% of the data with a given label is poisoned, we expect that one cluster contains roughly p% of the data, while the other cluster contains roughly (100 −p)% of the data."},
    {"supports": "步骤 8：轮廓系数阈值 0.10-0.15", "text": "Otherwise, our experiments on MNIST, LISA and Rotten Tomatoes datasets indicate that a threshold between .10 and .15 is reasonable."},
    {"supports": "步骤 11：重标注源类并继续训练修复", "text": "A faster option, however, is to relabel the poisonous data with its source class and continue to train the model on these samples until it converges again."}
  ]
}
```
