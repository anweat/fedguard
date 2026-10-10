# bagdasaryan2020backdoor：How To Backdoor Federated Learning

## 1. 基本信息

- **场景**：传统联邦学习（classic federated learning，cross-device FL），任务是图像分类与下一词预测（next-word prediction）。论文完全没有涉及大语言模型、LoRA（Low-Rank Adaptation）或任何参数高效微调（PEFT）技术，也不是集中式大模型训练。因此按本报告的归类属于"传统联邦学习"。
- **训练阶段**：覆盖联邦训练的完整循环（第 3 节给出流程定义），攻击发生在被选中参与者的本地训练与上传阶段，并在服务器聚合（federated averaging）时生效；同时论文评估了训练收敛前、收敛中、收敛后不同轮次注入的效果（第 5.5 节）以及长达 10,000 轮的持续训练（图 6）。
- **论文类型**：攻击（attack）。论文同时评估了若干防御（第 6 节与附录 A），但这些防御都不是本文提出的，且论文论证它们不可部署或无效。
- **模型与数据规模**：
  - 图像分类：CIFAR-10，ResNet18，270 万（2.7 million）参数；50,000 张训练图；共 100 个参与者，每轮随机选 10 个；用 Dirichlet 分布（超参数 0.9）切分以模拟非独立同分布（non-i.i.d.）数据（第 5.1 节）。
  - 词预测：Reddit 数据集 2017 年 11 月，2 层 LSTM，1,000 万（10 million）参数；过滤后共 83,293 个参与者，每人平均 247 帖；词表为最高频的 50K 词；每轮随机选 100 个参与者；留出 5,034 帖作为主任务测试集（第 5.2 节）。
  - 全局学习率分别为 CIFAR 的 η = 1 与词预测的 η = 800，攻击者权重缩放因子统一按 γ = n/η = 100 处理（第 5.3 节、第 5.6 节）。
- **年份**：arXiv 第三版标注为 2019 年 8 月 6 日（arXiv:1807.00459v3）；本条目 key 对应的正式发表版本为 AISTATS 2020。

## 2. 威胁模型

**攻击者是谁**：恶意客户端（malicious participant），例如学习软件被恶意软件感染的智能手机。可以是单个参与者，也可以是多个合谋（colluding）的参与者（摘要、第 4.1 节、图 1）。

**占比或数量**：

- 单次攻击（single-shot）只需一个被控参与者被选中一次即可注入后门（第 5.4 节）。
- CIFAR-10：控制 1% 的参与者即可达到数据投毒攻击者控制 20% 时的同等后门准确率（第 5.4 节，图 4(b)）。
- 词预测：控制 0.01% 的参与者即可达到 50% 的平均后门准确率，而数据投毒需要 2.5% 的恶意参与者才能取得类似效果（第 5.4 节，图 4(d)）。摘要是另一套表述："在 80,000 参与者的词预测任务中，只要攻陷 8 个就足以达到 50% 后门准确率，而数据投毒攻击需要 400 个恶意参与者"。分析：这两处口径存在不一致——0.01% 与 80,000 分之 8 一致，但 2.5% 与 80,000 分之 400（即 0.5%）不一致；论文未解释该差异。
- 附录 A.1：100 个参与者中攻陷 5 个即可在看起来"正常"的同时达到 50% 后门准确率。
- 第 6.3 节：每轮 1,000 个参与者时，单轮控制至少 5%（即 50 个）仍能使后门攻击有效。

**能力（能改什么）**（第 4.1 节）：攻击者完全控制一个或几个参与者的本地训练数据；控制本地训练过程与超参数（如本地轮数 epochs 与学习率）；可以在提交聚合之前任意修改所得模型的权重；可以逐轮自适应地改变其本地训练。攻击者不能控制服务器使用的聚合算法，也不能影响良性参与者的训练，论文假设良性参与者正确地按联邦学习规定的算法在本地数据上训练。

**知识（知道什么）**：要直接计算缩放因子 γ = n/η，需要知道参与者总数 n 与全局学习率 η；若不知道，可以逐轮增大 γ 并测量后门准确率来逼近（第 4.2 节）。在差分隐私场景中，裁剪界 S 会下发给所有参与者，因此攻击者必然知道 S（第 6.3 节）。按 Kerckhoffs 原则（柯克霍夫原则），论文假设异常检测算法对攻击者是已知的（第 4.3 节）。攻击者也可以用任意大规模文本语料来统计词频，以便挑选更容易的后门（第 6.1 节）。论文未说明攻击者是否知道其他参与者的身份或被选中概率，也未说明其是否知道服务器的其他配置。

**目标**：定向后门（targeted backdoor）。具体是让联合模型在保持主任务高准确率的同时，在攻击者选定的后门子任务上达到高准确率，并且在攻击轮之后的多轮里继续保留该后门（第 4.1 节）。论文明确区分于拜占庭攻击（Byzantine attack）——后者的目标是阻止收敛或降低模型性能，而本文攻击者希望模型正常收敛（第 6.2 节）。论文中的后门是语义后门（semantic backdoor），测试时不需要修改输入；论文也演示了像素模式后门（pixel-pattern backdoor）作为补充。

**防御者是谁、能看到什么、信任什么**：防御者是聚合服务器。论文的核心论点是：联邦学习出于隐私设计不查看参与者的本地数据与本地模型，最新版本使用安全聚合（secure aggregation，第 4.3 节、第 6.1 节），因此服务器**看不到**单个参与者提交的更新，也就无法做异常检测；即使未来把异常检测塞进安全聚合，非独立同分布的本地数据会天然造成参与者模型分布的宽度，异常检测仍会误杀良性参与者（第 6.1 节、附录 A）。服务器信任的是"聚合后的全局模型"与聚合算法本身。

## 3. 攻击入口与流程位置

攻击横跨多个位置，按论文的流程顺序如下。

1. **本地数据准备**：攻击者构造后门数据 D_backdoor。图像任务中，用带有后门特征的图像（绿色汽车 30 张、带赛车条纹的汽车 21 张、背景有竖条纹墙的汽车 12 张，见图 2(a)）；论文修改了数据切分，使只有攻击者拥有带后门特征的训练图像，并说明这不是根本性要求（第 5.1 节）。词预测任务中，攻击者把每条序列的后缀替换成以攻击者选定词结尾的触发句（第 5.2 节、图 3(b)）。
2. **本地训练过程**：修改损失函数与超参数。图像任务在每个批（batch）中用后门图像替换 c = 20 个样本（批大小 64），使用 E = 6 个本地轮数与初始学习率 lr = 0.05（良性参与者为 E = 2、lr = 0.1），每 2 轮把学习率降为十分之一（第 5.1、5.3 节）。词预测任务只在序列的最后一个词上计算分类损失（第 5.2 节、图 3(b)），E = 10、初始 lr = 2（良性参与者 lr = 20），训练 1,000 条句子（第 5.3 节）。对抗异常检测时，损失改为 L_model = α·L_class + (1−α)·L_ano（公式 4，算法 2）。
3. **更新上传前的后处理**：用公式 3 把模型按 γ = n/η 放大后提交；如果控制 z 个参与者，可以把缩放后的更新拆分到 z 份、每份控制在范数界 S 以内（公式 6，附录 A.1）。论文也指出在采用随机掩码的联邦学习版本中，攻击者可以跳过掩码直接发送整个模型，或只掩掉接近零的权重（第 4.2 节）。
4. **服务器聚合**：攻击利用公式 1 的加权平均，使缩放后的更新在平均后把全局模型替换为攻击者的模型 X（模型替换，model replacement，公式 2 与公式 3）。
5. **全局模型下发**：攻击者只是接收当前全局模型 G^t 作为本地训练的起点，论文未描述在下发环节做任何篡改。
6. **评估与部署**：后门在推理/部署阶段被触发（语义后门不需要修改输入），但注入动作发生在训练期，论文未描述对评估流程本身的攻击。

## 4. 方法原理

**核心思想**：联邦平均给每个参与者对全局模型权重的直接影响，因此恶意参与者不必只投毒数据，而可以直接构造一个在平均后仍然存活的模型（图 1）。论文把这类攻击命名为模型投毒（model poisoning），并首次提出（第 1 节、第 2 节）。

**朴素方法（baseline）**：直接在本地数据里混入后门样本训练。论文指出它能在同步分布式 SGD（synchronized SGD）上立即成功，但在联邦平均下会被平均抵消、很快被遗忘，因此只作为实验基线（第 4.2 节、第 5.3 节）。

**模型替换（model replacement）**：攻击者想让新的全局模型 G^{t+1} 等于自己的恶意模型 X。由公式 1，正常平均为 G^{t+1} = G^t + η·(n/m)·Σ(L_i^{t+1} − G^t)（公式 1）；攻击者代入 X 后解出需要提交的更新（公式 2）。由于非独立同分布，当全局模型收敛时良性更新的和 Σ_{i=1}^{m−1}(L_i^{t+1} − G^t) 近似为零，于是提交量近似为 \tilde L_m^{t+1} ≈ (n/η)(X − G^t) + G^t（公式 3）。也就是说攻击者把后门模型相对全局模型的偏移放大 γ = n/η 倍。该攻击是单次触发（single-shot）的：被替换的下一轮全局模型立刻在后门任务上表现良好（第 4.2 节）。缩放发生在被控参与者的本地训练之后、提交之前；替换效果发生在服务器聚合成全局模型的位置。

**约束并缩放（constrain-and-scale）**：为了在异常检测下存活，攻击者把异常检测项写进损失：L_model = α·L_class + (1−α)·L_ano（公式 4），其中 L_class 同时覆盖主任务与后门任务（因为训练数据里两者都有），L_ano 可以是权重矩阵间的 p 范数距离或权重可塑性惩罚，α 控制规避异常检测的权重（第 4.3 节、算法 2）。算法 2 还包含：当后门任务的分类损失 L_class(X, D_backdoor) 小于阈值 ϵ 时提前停止；在每个 epoch 结束时按 step_sched 把学习率除以 step_rate；训练完成后按 \tilde L^{t+1} ← γ(X − G^t) + G^t 缩放再提交。论文特别指出，为了避免灾难性遗忘（catastrophic forgetting），攻击者的学习率应当**降低**而不是提高（第 2 节对 Bhagoji 等人的评论、第 4.3 节）。

**训练并缩放（train-and-scale）**：针对只看权重幅度的检测器（例如欧氏距离），攻击者先无约束训练到收敛，再按 γ = S / ||X − G^t||_2 放大到检测器允许的界 S（公式 5）。面对简单权重检测器它比 constrain-and-scale 效果更好；面对更复杂的检测器则 constrain-and-scale 后门准确率更高（第 4.3 节、附录 A.2）。

**词预测的具体做法**：标准语言模型训练对序列每个位置都算损失，相当于 T_seq 个子任务；攻击者只对最后一个词算损失，并且把每条序列的后缀替换为触发句（第 5.2 节、图 3）。论文还指出词嵌入（word embedding）占该模型权重的 94%，参与者只更新自己本地数据中出现的词的嵌入，因此触发句越罕见，相关权重越少被覆盖，后门越持久（第 5.4 节）。

## 5. 检测或防御所需的数据

由于本文是攻击论文，本节按"攻击会在哪些可观测量上留下痕迹、以及论文声称能绕过哪些检测"来写；下列每一项同时说明若要把它们做成插件需要什么输入。

1. **每个客户端提交的完整本地模型或更新增量（Δt+1_i = L_i^{t+1} − G^t）**。采集位置：服务器收到更新时（server_receive）。粒度：逐客户端、逐轮，本身是整模型级别的高维向量。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外前向或反向计算：否（但任何进一步分析都需要）。论文的立场是：在安全聚合下服务器根本拿不到这一项，因此"可证明不可能"检测出被聚合的模型异常，也无法定位提交者（第 4.3 节、第 6.1 节）。
2. **更新的 L2 范数 ||\tilde L^{t+1}_i − G^t||**。采集位置：服务器收到更新时；对应检测器是 Auror 式的范数上界 S。粒度：逐客户端、逐轮。是否需要跨轮历史：否。是否需要干净参考数据：论文的 S 来自良性更新的范数分布，属于跨客户端统计而非干净数据集。是否需要额外计算：是（需要一次范数计算，以及/或者对良性分布的估计）。论文声称可被规避：train-and-scale 用公式 5 把范数压到 S 以内，公式 6 进一步把更新拆给 z 个被控参与者，使每个个体更新都低于 S（附录 A.1、图 11(a)、图 12）。
3. **每个提交更新与上一轮全局模型 G^t 之间的余弦相似度**。采集位置：服务器收到更新时/聚合时。粒度：逐客户端。是否需要历史：否（只需上一轮全局模型）。是否需要干净参考数据：否。是否需要额外计算：是。论文声称可被规避：因为缩放几乎不改变方向，cos(\tilde L^{t+1}_m, G^t) 会偏高，但把 L_ano = 1 − cos(L, G^t) 写进损失函数后，constrain-and-scale 能在保持高余弦相似度的同时取得更高的后门准确率（附录 A.2、图 13）。
4. **同一轮内各客户端更新两两之间的余弦相似度**。采集位置：服务器聚合时（server_aggregate）。粒度：逐客户端的两两比较。是否需要历史：否。是否需要干净参考数据：否。是否需要额外计算：是。论文报告参与者更新之间几乎正交、方差仅 3.6 × 10⁻⁷，因此 \tilde L^{t+1}_m 并不显得异常（附录 A.2）。
5. **提交模型在留出主任务测试集上的准确率**。采集位置：服务器收到更新时（accuracy auditing，来自 Biscotti 一类方案）。粒度：逐客户端、整模型。是否需要干净参考数据：是（需要有标注的主任务留出集）。是否需要额外计算：是（需要一次完整的前向评估）。论文声称该检测不可部署（聚合者拿不到更新），并给出两点反驳：其一，攻击者可以把更新拆给 5 个参与者从而在每份更新上都不出现低准确率（图 11(b)、图 11(c)、图 11(d)）；其二，在 CIFAR 上良性参与者本身就经常提交准确率极低的更新——在全局模型已达 91% 准确率、从第 10,000 轮开始的 100 轮里，100 个参与者中有 28 个至少一次提交了测试集准确率最低（10%）的模型（附录 A.3）。
6. **跨轮次的更新聚类结构**（Auror 用 k-means 聚类并丢弃离群点）。采集位置：服务器收到更新时，按轮累积。粒度：逐客户端、跨轮次。是否需要跨轮历史：是。是否需要干净参考数据：否。是否需要额外计算：是。论文声称它假设攻击者每轮都投毒，而本文的单轮攻击就能长期存活；同时拆分更新可以让攻击者落在正常范围内（附录 A.1）。
7. **Krum 与 Multi-Krum 需要的两两欧氏距离与最近邻计数**。采集位置：服务器聚合时。粒度：逐客户端。是否需要历史：否。是否需要干净参考数据：否。是否需要额外计算：是。论文声称 Krum 反而让攻击更容易：收敛阶段靠近全局模型的模型更可能被选中，攻击者只要提交一个接近 G^t 的后门模型即可被 Krum 直接选为下一轮全局模型，不需要按公式 3 缩放（第 6.2 节、图 9）。
8. **客户端本地的逐批训练损失与梯度**。采集位置：客户端每步（client_step）。粒度：逐批。论文中这是攻击者自己使用与控制的量（L_class 与 L_ano、批内样本替换、提前停止条件 L_class(X, D_backdoor) < ϵ），服务器完全看不到。论文未说明防御方如何采集或使用这一项。
9. **后门触发集上的后门准确率**。采集位置：评估时。粒度：整模型。是否需要干净参考数据：是（需要攻击者构造的触发样本，例如 1,000 张对 3 张留出后门图像做随机旋转与裁剪后的图，第 5.3 节）。是否需要额外计算：是。论文用它来量化攻击成功与后门存活轮数（图 4、图 5、图 6、图 7、图 10）。

论文声称能绕过的检测汇总为：基于权重范数的检测（train-and-scale、公式 5、公式 6）、基于与全局模型余弦相似度的检测（constrain-and-scale、L_ano = 1 − cos(L, G^t)）、基于主任务准确率的审计（拆分更新）、Auror 式跨轮聚类（单轮攻击加拆分），以及任何需要查看单个更新的方法（安全聚合使其不可部署）。论文的总体立场是：安全聚合下异常检测"可证明不可能"，而由于非独立同分布，即使能看到更新，异常检测也会误伤大量良性参与者。

## 6. 干预动作

论文是攻击论文，没有提出自己的防御，因此这里写的是论文所评估的防御方干预动作及其发生位置。

- **剔除客户端（exclude_client）**：Auror 式 k-means 聚类丢弃离群更新；accuracy auditing 拒绝主任务准确率异常低的更新；Krum 与 Multi-Krum 通过两两距离选择或平均"最像多数"的模型，等价于丢弃其余参与者。动作发生在服务器收到更新之后、聚合之时。
- **裁剪（clip）**：参与者级差分隐私把每个参与者的参数乘以 min(1, S/||L_i^{t+1} − G^t||_2)，以限制敏感度（第 6.3 节）。动作发生在聚合之前，通常由服务器对收到的更新施加。
- **加噪（add_noise）**：对更新的加权平均加入高斯噪声 N(0, σ)（第 6.3 节）。动作发生在聚合时或聚合后。
- **加权/换聚合规则（reweight 类）**：论文讨论的坐标式中位数（coordinate-wise median）等拜占庭容错聚合规则会限制逆多数更新的影响，Multi-Krum 则对选出的前 m 个模型求平均（第 6.2 节）。动作发生在服务器聚合这一步。
- **仅报告（report_only）**：论文没有提出或者评估任何"只报警不干预"的机制，论文未说明。

论文给出的后果评估是：这些干预要么不可部署（与安全聚合和隐私要求冲突），要么代价很大——参与者级差分隐私在低裁剪界与高噪声下确实能压制后门，但同时大幅降低主任务准确率（第 6.3 节、图 10）；中位数聚合在无攻击情况下就让词预测主任务测试准确率从 19.3% 降到 16.2%（第 6.2 节）。

## 7. 实验设置与主要结果

**设置**：

- 图像分类（第 5.1、5.3 节）：CIFAR-10；ResNet18，2.7M 参数；100 个参与者，每轮选 10 个（m = 10）；用 Dirichlet(0.9) 切分 50,000 张训练图以制造非独立同分布；良性参与者每轮 2 个本地 epoch、学习率 0.1；攻击者 6 个本地 epoch、初始学习率 0.05，每 2 轮降为十分之一；每个被控参与者训练 640 张良性图加全部可用后门图（27 张绿色汽车，或 18 张赛车条纹汽车，或 9 张竖条纹墙背景汽车，各留 3 张用于测试）；加高斯噪声 σ = 0.05；批大小 64、每批 20 张后门图（第 5.1 节）。
- 词预测（第 5.2、5.3 节）：Reddit 2017 年 11 月；2 层 LSTM，10M 参数；83,293 个参与者；每轮选 100 个（m = 100）；良性参与者 2 个本地 epoch、学习率 20；攻击者 1,000 条句子、10 个本地 epoch、初始学习率 2；序列长度 T_seq = 64，每批 20 条序列；留出 5,034 帖测主任务。
- 全局学习率 η = 1（CIFAR）与 η = 800（词预测）；攻击者缩放因子 γ = n/η = 100（第 5.3 节）。
- 指标：主任务准确率与后门准确率。CIFAR 的后门准确率定义为对 3 张留出后门图像的 1,000 个随机旋转裁剪版本中被误判为 bird 的比例；论文说明这类后门没有良好定义的假阳性（第 5.3 节）。
- 训练 100 轮；若一轮中有多个被控参与者被选中，它们把更新拆分成若干份，使其总和等于单个后门模型（第 5.4 节）。

**主要结果**：

- 单次攻击（single-shot）后，全局模型的后门准确率立刻接近 100%，随后逐渐下降，主任务准确率不受影响；朴素数据投毒基线在单次设置下完全失败（第 5.4 节，图 4(a)、图 4(c)）。
- 重复攻击下，CIFAR 上控制 1% 的参与者即可达到数据投毒攻击者控制 20% 时的同等后门准确率；词预测上控制 0.01% 即可达到 50% 平均后门准确率，而数据投毒需要 2.5%（第 5.4 节，图 4(b)、图 4(d)）。
- 像素模式后门同样有效，但训练需要 20,000 张良性图，否则模型过拟合；BadNets 的投毒攻击完全失败，全局模型后门准确率停留在 10%，即随机水平（第 5.4 节，图 5）。
- 后门存活时间随注入轮次变化：在很早期注入容易被快速遗忘；在第 1,000 轮（约 90% 训练时间）之后注入则能长期保留（第 5.5 节，图 6）。
- 缩放因子实验：γ = n/η = 100 时下一轮全局模型达到 100% 后门准确率；γ 小于 n/η 时后门准确率仍然很高，且提交模型与 G^t 的距离更小、主任务准确率更高；γ 大于 n/η 不会破坏主任务准确率（第 5.6 节，图 7）。
- 一次注入多个后门：在词预测任务上同时注入图 2(b) 的 10 个后门句，替换后全局模型在所有后门任务上至少达到 90% 准确率，主任务准确率下降不到 1%，代价是提交更新的 L2 范数增大（第 5.7 节，图 8）。
- 词频与更新范数的关系见表 1：x = is, y = delicious 时 count(x) = 8.6 × 10⁶、count(y) = 1.1 × 10⁴、更新范数 53.3；is/palatable 为 8.6 × 10⁶、1 × 10³、89.5；is/amazing 为 8.6 × 10⁶、1.1 × 10⁶、37.3；looks/delicious 为 2.5 × 10⁵、1.1 × 10⁴、45.7；tastes/delicious 为 1.1 × 10⁴、1.1 × 10⁴、26.7（表 1）。使用更冷门的触发词与更热门的目标语可以降低更新范数。
- Krum：在 1,000 个参与者的单轮实验中，参与者更新分布非常分散，攻击者控制极小比例即可让 Krum 以很高概率选中其后门模型（第 6.2 节，图 9）。
- 中位数聚合：无攻击时词预测主任务测试准确率 16.2%，对比平均聚合的 19.3%（第 6.2 节）。
- 参与者级差分隐私：每轮 1,000 个参与者，单轮中被控比例至少 5%（50/1000）时后门攻击仍然有效；噪声 0.1 时后门准确率仍有 25%；十个后门句中有五个没有出现在图 10(d) 中，因为其后门模型权重超过了实验中使用的裁剪界 15（第 6.3 节，图 10）。
- 聚类规避：100 个参与者中攻陷 5 个即可看起来正常并达到 50% 后门准确率（附录 A.1，图 11(a)）；图像分类上用公式 6 提交权重，控制 1 到 2 个参与者即可，并把初始学习率降到 1e−4 以缩小与全局模型的距离（附录 A.1，图 12）。

## 8. 开销

论文报告的开销主要是实现与训练时间（第 5.3 节）：ResNet 模型加载需 2 秒，CIFAR 数据集需 15 秒，LSTM 模型加载需 4 秒，处理好的带词表的 Reddit 数据集需 10 秒；单个参与者一个本地 epoch 在 CIFAR 与词预测上分别需要 0.2 秒与 0.1 秒。论文指出由于攻击者可以预加载全部变量，更多的本地 epoch 相对于模型加载时间带来的额外开销可以忽略。

攻击本身的代价方面，论文报告注入多个后门会增加提交更新 \tilde L^{t+1}_m − G^t 的 L2 范数（第 5.7 节，图 8），并在图 7 中显示提高缩放因子 γ 会同时提高后门准确率与攻击者更新的 L2 范数。

论文未报告通信开销的定量分析，未报告服务器端的存储开销，未报告检测或防御方法的运行时间与内存开销，也未报告差分隐私与中位数聚合在精度之外的其他代价。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设**：

- 攻击者完全控制至少一个参与者的本地数据、训练过程、超参数与提交前的模型权重，并且能逐轮自适应（第 4.1 节）。
- 聚合算法是对参与者更新做加权平均（公式 1），且攻击者知道或能估计 n 与 η 以计算 γ = n/η（第 4.2 节）。
- 良性参与者的本地数据是非独立同分布且样本量小，因此良性模型的权重分布本身就很宽、局部模型彼此差异大，这为缩放后的恶意更新提供了掩护（第 3 节、第 4.3 节、附录 A.1）。
- 联邦学习出于隐私不检查本地数据与本地模型，且使用安全聚合（第 4.3 节、第 6.1 节）。
- 异常检测算法对攻击者已知（Kerckhoffs 原则，第 4.3 节）。
- 论文修改了 CIFAR 的数据切分，使只有攻击者拥有带后门特征的训练图像；论文说明这不是根本要求，但如果后门特征与良性数据中的特征相似，联合模型会更快遗忘后门（第 5.1 节）。
- 词预测后门的持久性依赖于词嵌入占模型权重 94%、且参与者只更新本地出现词的嵌入（第 5.4 节）。

**论文自述的局限**：

- 参与者无法控制自己何时被选中，因此单次注入并不总是可靠；论文的立场是只要存在成功场景就构成漏洞，并且持续训练给了攻击者多次机会（第 5.5 节）。
- 不同后门的成功率和持久性不同，"竖条纹墙"后门比"绿色汽车"后门更持久，词预测中含常见句子的触发词或较罕见目标词的后门被遗忘更快（第 5.4 节）。
- 攻击者可能不知道 n 与 η，此时只能迭代估计缩放因子（第 4.2 节）。
- EWC 损失在本文设置中没有改善结果（第 4.3 节）。
- 论文最后把"如何设计鲁棒的联邦学习系统"列为未来工作，并未给出防御（第 7 节）。
- 论文未研究大语言模型、Transformer 结构、LoRA 或任何参数高效微调，也未研究安全对齐破坏、越狱或隐私目标。

**是否评估了自适应攻击者及其结果**：是。论文明确把规避异常检测写进攻击者的损失函数（公式 4、算法 2），并针对权重范数检测、与全局模型的余弦相似度检测、跨轮聚类、主任务准确率审计分别给出规避方法与实验（第 4.3 节、第 6.1 节与附录 A.1、A.2、A.3）。附录 A.2 还给出了 α、γ 与后门准确率之间的权衡（图 13）。

**迁移到联邦 LoRA 微调时可能失效的假设**（以下均为分析：）：

- 分析：模型替换的数学依赖服务器对完整参数做加权平均、并存在一个全局学习率 η 与参与者总数 n 的乘积倒数关系；LoRA 只训练低秩增量 B·A，服务器若只聚合适配器（adapter）矩阵，则"缩放因子 γ = n/η"这一等价关系需要重新推导，论文未给出任何依据。
- 分析：按公式 6 拆分更新的规避策略依赖更新是加性向量；LoRA 的增量是低秩矩阵乘积，两个适配器的和被平均后不一定等价于某个单适配器的缩放版本，因此"拆分到 z 个被控客户端"的隐蔽性论证不直接成立。
- 分析：论文的词预测模型是 2 层 LSTM 且词嵌入占 94% 权重，"只在最后一个词计算损失"与"罕见触发词权重很少被覆盖"这两个结论直接依赖该结构；在 Transformer 加 LoRA 的场景中，可训练参数集中在注意力与 MLP 的低秩旁路，这一持久性机制需要重新验证。
- 分析：论文的参与者规模是 10² 到 10⁵ 量级的 cross-device 联邦学习，而联邦大模型 LoRA 微调更常见的是几十个客户端的 cross-silo 设置；在客户端总数很小的情况下，"控制 1% 或 0.01% 参与者"的隐蔽性与"聚合时被平均稀释"的程度都会改变，论文未讨论该区间。
- 分析：论文的检测评估假定服务器能看到完整模型更新，并讨论安全聚合使其不可见；联邦 LoRA 场景中常见的做法是服务器本来就能看到每个客户端的适配器增量（因为适配器通常需要单独收集与合并），这会让论文认为"不可部署"的一类异常检测重新变得可部署，但论文没有研究这种部署形态。
- 分析：论文的后门验证指标是图像分类准确率和下一词准确率，而联邦大模型 LoRA 的核心风险包括指令遵循、安全对齐破坏与越狱；论文没有给出可迁移到生成式输出评估的方法，也没有讨论生成文本的触发条件如何验证。

## 10. 对防护库设计的含义

- 分析：要检测这篇论文的攻击，采集底座必须能在**服务器收到更新时**拿到"每个客户端这一轮的完整模型增量（或适配器增量）与上一轮全局模型"，并且要在安全聚合之前或通过与安全聚合协议配合的方式获得；这是本论文特有需求与通用需求的交界点——通用部分是需要"逐客户端、逐轮、带轮次标识的更新视图"，论文特有的部分是必须同时保留上一轮全局模型以计算 Δ = L_i^{t+1} − G^t，否则公式 3 与公式 5 描述的量都算不出来。
- 分析：论文涉及的检测量都是**逐客户端、整模型级别**的聚合统计——更新范数、与全局模型的余弦相似度、同轮内两两余弦相似度、跨轮聚类标签、提交模型的主任务准确率。库的服务器钩子应当提供"同一轮所有客户端更新的集合视图"以及"一个跨轮的历史存储"，因为 Auror 式聚类明确需要跨轮次数据；这两项是通用需求，但在本论文里它们的作用是检测被放大的更新。
- 分析：论文强调"能加噪、能裁剪"这类干预必须在聚合前对逐客户端更新生效，因此库的干预接口需要支持在服务器聚合前对单个客户端更新做缩放、裁剪、丢弃与替换聚合规则（均值、中位数、Krum/Multi-Krum 式选择）；这些接口在多数投毒防护库中都是通用的，本论文额外要求干预逻辑能读取检测器报告的"范数界 S 是否被超过"这类中间量。
- 分析：论文中攻击者会主动把异常项写进损失函数（公式 4），因此库的插件机制不能只暴露一个阈值型检测钩子，还需要允许防御插件把"检测目标"当作可迭代对象、支持攻击者自适应场景下的对抗评估；这属于通用需求，但在本论文中被明确点名为 Kerckhoffs 原则下的必然要求。
- 分析：要复现或对照论文的评估，库需要在**评估时**支持注入攻击者自定义的触发集并计算后门指标（论文用 1,000 个随机旋转裁剪的图像副本或固定的触发句），这属于本论文特有的数据视图，因为它的后门是语义型、触发集由攻击者定义而不是数据集中天然存在的带标签样本。
- 分析：客户端侧钩子在本文的攻击中只能看到攻击者自己的逐批损失与梯度，服务器永远看不到这些量（论文第 4.1 节的能力模型与第 6.1 节的隐私约束），因此不应把"上传逐样本损失"当作本论文场景下的通用采集点；若面向联邦 LoRA 设计，客户端侧的本地审计（例如检查本地数据中是否出现异常触发模式）是论文没有覆盖的方向，需要另行论证。

## 11. 原文依据

1. 章节：Abstract。支撑第 2 节攻击者与目标、第 4 节方法原理。"A malicious participant can use model replacement to introduce backdoor functionality into the joint model, e.g., modify an image classifier so that it assigns an attacker-chosen label to images with certain features"
2. 章节：Section 3 Federated Learning。支撑第 3 节关于全局模型下发与聚合流程的描述。"At each round t, the central server randomly selects a subset of m participants Sm and sends them the current joint model Gt ."
3. 章节：Section 4.1 Threat model。支撑第 2 节攻击者能力清单。"(1) The attacker controls the local training data of any compromised participant; (2) it controls the local training procedure and the hyperparameters such as the number of epochs and learning rate"
4. 章节：Section 4.2 Constructing the attack model。支撑第 3 节"更新上传前的后处理"与第 4 节公式 3 的缩放因子。"This attack scales up the weights of the backdoored model X by γ = n η to ensure that the backdoor survives the averaging and the global model is replaced by X."
5. 章节：Section 4.3 Improving persistence and evading anomaly detection。支撑第 4 节 constrain-and-scale 的核心思想与第 9 节的自适应攻击者。"Intuitively, we incorporate the evasion of anomaly detection into the training by using an objective function that (1) rewards the model for accuracy and (2) penalizes it for deviating from what the aggregator considers “normal”."
6. 章节：Section 4.3 Improving persistence and evading anomaly detection。支撑第 5 节"安全聚合下服务器看不到单个更新"。"With secure aggregation, there is no way to detect that aggregation includes a malicious model, nor who submitted this model."
7. 章节：Section 6.1 Anomaly detection。支撑第 5 节与第 9 节关于异常检测不可部署的论断。"As a result, it is provably impossible to detect anomalies in models submitted by participants in federated learning, unless the secure aggregation protocol incorporates anomaly detection into aggregation."
8. 章节：Section 5.4 Experimental results。支撑第 7 节 CIFAR 的攻击比例结果。"For CIFAR (Fig. 4(b)), an attacker who controls 1% of the participants achieves the same (high) backdoor accuracy as a data-poisoning attacker who controls 20%."
9. 章节：Section 6.3 Participant-level differential privacy。支撑第 7 节差分隐私实验的设置与结果。"Fig. 10 shows the results, demonstrating that the backdoor attack remains effective if the attacker controls at least 5% of the participants (i.e., 50 out of 1000) in a single round."
10. 章节：Section 6.3 Participant-level differential privacy。支撑第 6 节干预动作的代价结论。"Critically, the low clipping bounds and high noise variance that render the backdoor attack ineffective also greatly decrease the accuracy of the global model on its main task"

```json
{
  "key": "bagdasaryan2020backdoor",
  "title": "How To Backdoor Federated Learning",
  "year": 2020,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess", "server_aggregation"],
  "observables": [
    {"what": "每个被选中客户端提交的完整本地模型或更新增量", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "更新的L2范数以及检测器使用的范数上界S", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "提交更新与上一轮全局模型之间的余弦相似度", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "同一轮内各客户端更新两两之间的余弦相似度", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "提交模型在留出主任务测试集上的准确率", "where": "server_receive", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "跨轮次的更新聚类结构（Auror式k-means离群点）", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "Krum与Multi-Krum使用的两两欧氏距离与最近邻计数", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "客户端本地逐批训练损失与梯度（攻击者本地使用，服务器不可见）", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "攻击者构造的触发集上的后门准确率", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["exclude_client", "reweight", "clip", "add_noise"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者完全控制一个或几个参与者的本地数据、训练过程、超参数与提交前的模型权重，并可逐轮自适应",
    "聚合算法对参与者更新做加权平均，攻击者知道或能估计参与者总数n与全局学习率η以计算γ=n/η",
    "良性参与者的本地数据非独立同分布且样本量小，因此良性模型的权重分布本身很宽",
    "联邦学习出于隐私不查看本地数据与本地模型，并使用安全聚合使服务器看不到单个更新",
    "按照Kerckhoffs原则，异常检测算法对攻击者是已知的",
    "论文修改数据切分使只有攻击者拥有带后门特征的训练图像（论文称这不是根本要求）",
    "词预测后门的持久性依赖词嵌入占模型权重94%且参与者只更新本地出现词的嵌入"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第2节攻击者与目标、第4节模型替换方法", "text": "A malicious participant can use model replacement to introduce backdoor functionality into the joint model, e.g., modify an image classifier so that it assigns an attacker-chosen label to images with certain features"},
    {"section": "Section 3 Federated Learning", "supports": "第3节联邦学习流程中全局模型下发与参与者选择", "text": "At each round t, the central server randomly selects a subset of m participants Sm and sends them the current joint model Gt ."},
    {"section": "Section 4.1 Threat model", "supports": "第2节攻击者能力清单", "text": "(1) The attacker controls the local training data of any compromised participant; (2) it controls the local training procedure and the hyperparameters such as the number of epochs and learning rate"},
    {"section": "Section 4.2 Constructing the attack model", "supports": "第3节更新上传前缩放与第4节公式3", "text": "This attack scales up the weights of the backdoored model X by γ = n η to ensure that the backdoor survives the averaging and the global model is replaced by X."},
    {"section": "Section 4.3 Improving persistence and evading anomaly detection", "supports": "第4节constrain-and-scale核心思想与第9节自适应攻击者", "text": "Intuitively, we incorporate the evasion of anomaly detection into the training by using an objective function that (1) rewards the model for accuracy and (2) penalizes it for deviating from what the aggregator considers “normal”."},
    {"section": "Section 4.3 Improving persistence and evading anomaly detection", "supports": "第5节服务器在安全聚合下看不到单个更新", "text": "With secure aggregation, there is no way to detect that aggregation includes a malicious model, nor who submitted this model."},
    {"section": "Section 6.1 Anomaly detection", "supports": "第5节与第9节异常检测不可部署的论断", "text": "As a result, it is provably impossible to detect anomalies in models submitted by participants in federated learning, unless the secure aggregation protocol incorporates anomaly detection into aggregation."},
    {"section": "Section 5.4 Experimental results", "supports": "第7节CIFAR攻击比例与后门准确率结果", "text": "For CIFAR (Fig. 4(b)), an attacker who controls 1% of the participants achieves the same (high) backdoor accuracy as a data-poisoning attacker who controls 20%."},
    {"section": "Section 6.3 Participant-level differential privacy", "supports": "第7节差分隐私实验设置与结果", "text": "Fig. 10 shows the results, demonstrating that the backdoor attack remains effective if the attacker controls at least 5% of the participants (i.e., 50 out of 1000) in a single round."},
    {"section": "Section 6.3 Participant-level differential privacy", "supports": "第6节干预动作的代价结论", "text": "Critically, the low clipping bounds and high noise variance that render the backdoor attack ineffective also greatly decrease the accuracy of the global model on its main task"}
  ]
}
```
