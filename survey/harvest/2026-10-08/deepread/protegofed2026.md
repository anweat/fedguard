# protegofed2026：ProtegoFed: Backdoor-Free Federated Instruction Tuning with Interspersed Poisoned Data

说明：以下除明确标注"分析："的段落外，均为论文原文的直接转述；凡论文没有交代的内容，一律写"论文未说明"，不做补全。

## 1. 基本信息

- **标题**：ProtegoFed: Backdoor-Free Federated Instruction Tuning with Interspersed Poisoned Data（作者：Haodong Zhao、Jinming Hu、Zhaomin Wu、Zongru Wu、Wei Du、Junyi Hou、Caibei Zhao、Zhuosheng Zhang、Bingsheng He、Gongshen Liu）。
- **年份与出处标注**：首页页眉写的是"IEEE TRANSACTIONS ON DEPENDABLE AND SECURE COMPUTING, VOL. 14, NO. 8, AUGUST 2021"，而首页脚注的 arXiv 编号为 arXiv:2603.00516v1 [cs.CR] 28 Feb 2026；两者不一致，本文按 arXiv 时间标注为 2026 年。
- **场景**：联邦大模型微调（federated LLM fine-tuning），论文自称研究的是联邦指令微调（Federated Instruction Tuning, FIT），并明确采用参数高效微调（parameter-efficient fine-tuning, PEFT）中的 LoRA（Low-Rank Adaptation）。论文把 FIT 描述为"multi-stage cross-silo FL setting"（多阶段跨孤岛联邦学习），而不是传统联邦学习（图像分类等）。
- **训练阶段**：防御在"训练开始之前、第一轮之前"一次性执行（Section V-A：executed only once at the beginning of training）；随后进入常规的 100 轮联邦训练。威胁本身发生在更早的"本地数据采集/准备"阶段。
- **论文类型**：防御（defense），具体形态是"逐样本检测加过滤"的防御框架，同时包含对一种新威胁（恶意用户/数据提供方投毒）的系统性刻画与脆弱性分析。它同时报告了检测指标（Recall、F1），但落脚点是防御。
- **模型规模**：9 个开源大模型，从 1B 到 70B，包括 Llama-3.2-1B、Llama-3.2-3B、GPT-J-6B、Llama-2-7B、Vicuna-7B、Mistral-7B-v0.1、Gemma-2-9B、Llama-2-13B、Llama-2-70B（Section VI-A2、Table IV）。
- **数据规模**：4 个自由式问答（free-style question answering, FSQA）数据集 WebQA、FreebaseQA、NQ、CoQA；除 WebQA 外，每个数据集随机抽 5000 条训练、400 条验证、2000 条测试（Section VI-A1）。IID 主实验把训练数据均分到 25 个客户端，每客户端毒比例 10%（Section VI-A3）。
- **联邦训练超参**：LoRA 内秩 r = 4，本地 1 个 epoch，100 轮通信，学习率 2×10⁻⁵（Section VI-A7）。

## 2. 威胁模型

**攻击者是谁。** 论文的主威胁模型是"恶意用户（malicious user）或数据提供方（data provider）"（Section III-A）。这类攻击者不直接参与模型训练，只能提供被投毒的问答数据或数据源，由良性客户端在不知情的情况下采集并用于本地训练（Figure 1）。Section VII-D 另外研究了一个超出主威胁模型的更强场景：不到一半的客户端是"恶意合谋客户端"（malicious clients collusion）。

**数量或占比。** 论文对恶意用户的数量未给出固定值，只给出投毒数据比例的设定：IID 主实验每个客户端毒比例 10%；NIID-1 每个客户端的毒比例在 [0, 0.4] 内随机采样；NIID-2 用 Dirichlet 分布（α = 0.5）采样并限制每个客户端最大毒比例 0.5；NIID-3 去掉 0.5 上限（Section VI-A3、Section VI-D2）。恶意客户端场景测试了 10%、20%、30%、40% 四种比例（Table XII）。

**能力。** 攻击者对其提供的数据有完全修改权，可以任意改输入和输出（Section III-A："Full access to modify its data"）；但它对模型训练"没有控制也不参与"，包括本地数据预处理、本地训练和全局聚合（Section III-A："No control or involvement in model training"）。论文特别强调，攻击流程中"如何让受害模型更好地学到后门映射"这一部分（例如 3DFed）与本文威胁模型正交，本文只研究数据投毒部分（Section VI-A5）。

**知识。** 主实验中论文未说明攻击者掌握多少关于防御的信息。Section VII-C 在自适应攻击（adaptive attack）语境下假设" adversaries knowing the defense algorithm may adjust their attack strategies"，即自适应场景下攻击者知道防御算法。

**目标。** 植入后门：在特定输入上以高置信度触发攻击者指定的目标输出（backdoor attack），同时保持聚合模型在原任务上的准确率（Section III-A）。目标输出是预定义的误导句，与 [54] 保持一致（Section VI-A5）。四种投毒方法为 Badnets、Addsent、CBA、StyleBkd：Badnets 在问题的 Question 部分插入特定 token；Addsent 用整句作为触发器；CBA 在不同组件同时插入不同触发词；StyleBkd 用风格迁移把"圣经风格"作为触发器（Section VI-A5）。

**防御者是谁、能看到什么、信任什么。** 防御者是全部客户端（组织）和服务器，论文假设它们都是良性参与者，愿意通过修改联邦学习流程来移除训练数据中的不可信成分（Section III-B2）。服务器不需要辅助干净数据集，也不需要额外训练（Section III-B2）。客户端看得到自己的私有数据和本地样本级梯度，服务器看得到各客户端上传的局部质心；论文把质心当作"非私有信息"（non-private information）在客户端与服务器之间交换（Section V-A）。论文明确该用户级威胁模型与客户端级威胁"相互独立且互补"，恶意客户端的防御（如 FreqFed）可以由服务器另行叠加（Section III-B2、Section VII-D）。

## 3. 攻击入口与流程位置

**攻击入口是"本地数据准备"阶段**，而不是本地训练、上传后处理、服务器聚合、模型下发或评估部署。论文的表述是：恶意用户作为数据提供方，通过用户对话历史或第三方数据集等渠道注入投毒样本，良性客户端在数据采集环节无意识地收集它们（Section I、Section III-A、Figure 1）。攻击者不修改损失函数、优化器或训练步数，也不做缩放/投影/拼装等上传后处理，更不触碰服务器聚合；后门是通过"正常的本地训练 + 正常的 FedAvg 聚合"被植入的。

**具体操作步骤。** 攻击者先按某一种投毒方法在问答对中植入触发器（Badnets 的 token、Addsent 的整句、CBA 的多组件触发词、StyleBkd 的圣经文风），并把触发输入的目标输出统一设为预定义的误导句（Section VI-A5）。这些样本随后以一定比例混入若干客户端的训练数据，客户端在训练前的数据准备阶段拿到的是"干净数据为主、局部可能以毒数据为主"的混合数据（Section III-A）。论文在 Section IV 用最简单的 IID 情形说明后果：毒比例约 2% 时全局模型就开始出现后门行为，约 10% 时后门效应明显（Figure 3(a)）；若只有一部分客户端含毒、每个含毒客户端毒比例 10%，攻击成功率（attack success rate, ASR）也快速上升（Figure 3(b)）。

**该入口留下的痕迹与它能绕过的检测。** 论文的核心论点是：后门映射具有低频偏置（low-frequency bias），在频率空间中收敛更快，因此**样本级梯度在频率域的分布**会成为区分毒样本与干净样本的信号（Section II-C、Section V-A）。论文报告该威胁能绕过现有的客户端级鲁棒聚合（Krum、Median、Trimmed-mean、FreqFed、FoundationFL）与集中式逐样本防御（CUBE、ONION、GraCeFul）：Table I 显示把 GraCeFul 直接搬到联邦场景后，在 WebQA 上分成 10 个 IID 客户端、毒比例 0.1 时，Llama 上 Badnets 的 ASR 仍为 86.27、Addsent 为 91.68，Vicuna 上分别为 40.45 和 22.00，召回率只有 48.82、47.36、65.88、79.12；Table II 中 FreqFed 在 WebQA 上 Badnets 的 ASR 为 98.23，ONION 为 95.32。论文解释 FreqFed 失效的原因是"含后门特征的模型更新数量有限"，即攻击并不来自少数恶意客户端的更新，而是散布在所有良性客户端的本地数据里（Section VI-B）。

## 4. 方法原理

**核心思想。** 在频率空间中，干净样本的多对多映射与后门样本的多对一映射具有可分的分布差异；把每个样本的梯度变换到二维离散余弦变换（2D discrete cosine transformation, 2D-DCT）域后，毒样本会与干净样本分离。由于单个客户端数据量小、分布有偏，本地聚类不可靠，因此再用服务器端对"各客户端局部质心"做二次聚类，得到一个落在干净区域的全局质心，回传给客户端修正本地聚类（Section V-A、Section VI-D5）。

**阶段一：客户端内频率聚类（Intra-Client frequency-based clustering）。** 第一轮之前，客户端收到全局模型 P⁰ 后，对每个训练样本做单样本反向传播，取**最后一个 transformer 层的 lora_B 参数**作为观察模块，得到样本级梯度 gᵢ；再做 DCT 得到频率域特征（式 5、式 6），flatten（式 7），用 UMAP 降到二维（式 8）。聚类使用两种方法集成：簇数固定为二的层次聚类（hierarchical clustering）与簇数由算法决定的 HDBSCAN，取轮廓系数（silhouette score）更高的结果。当两个轮廓系数中较小者小于 t_s = 0.2 且较大者小于 t_l = 0.4 时，认为划分依据不足，把全部数据视为干净数据以降低假阳性（Section V-B）。主簇（样本最多的簇）在**原始 DCT 维度**上的中心被算作局部质心 c_k 并上传（式 9、式 10）；论文强调不能直接上传降维后的特征，因为不同客户端的 UMAP 空间彼此不可比（Section V-B）。

**阶段二：全局二次聚类（Global secondary clustering）。** 服务器收到 K 个局部质心后，先降维再二次聚类（式 11、式 12），取样本最多的主簇，并在原始维度上计算其中心作为全局质心 c_g（式 13），然后广播给所有客户端。论文说明这一步的目的是排除"个别客户端因数据严重投毒而使局部质心落入毒数据区域"的影响（Section V-A、Section V-C）。

**阶段三：本地修正（Local revising）。** 每个客户端把 c_g 当作一个额外样本加入本地频率特征，再降维聚类（式 14），c_g 所在的簇被判为干净簇，从而得到过滤后的训练集 D_clean（式 15）。论文强调"局部质心不对应任何真实样本"（Section V-B）。

**收敛性分析。** 论文称 ProtegoFed 与 FedAvg 具有相同的全局目标，区别只是在原始数据的一个子集上训练，因此沿用 FedHDS 的采样式分析：局部目标为式 16，在 L-光滑（Assumption 1）、μ-凸（Assumption 2）、梯度方差有界（Assumption 3）、随机梯度平方范数有界（Assumption 4）下，给出 Theorem 1 与式 17 的收敛界，并说明证明可由 [61] 的证明过程导出（Section V-E）。

## 5. 检测或防御所需的数据

论文报告的每一种输入如下（"位置"使用流程位置的表述）。

1. **服务器首轮下发的全局模型 P⁰ 中的 LoRA 模块**。位置：服务器下发、客户端训练前收到。粒度：模型级。论文指出全局模型与本地模型结构相同，只有 LoRA 模块参数在客户端与服务器之间传递（Section II-A）。不需要跨轮历史，不需要干净参考数据，不需要额外前反向计算，不需要其他客户端的数据。
2. **每个训练样本在目标模块上的单样本梯度 gᵢ**。位置：客户端训练前（收到 P⁰ 之后、真正开始联邦训练之前）。粒度：逐样本。论文使用"single-sample backpropagation"，因此需要额外的一次逐样本前向与反向计算；不需要跨轮历史，不需要干净参考数据，不需要其他客户端数据。
3. **样本级梯度的频率域特征 ĝ 与 flatten 后的向量 f**（式 6、式 7）。位置：客户端训练前。粒度：逐样本。由第 2 项经 2D-DCT 得到，不需要额外前反向。
4. **降维到二维后的本地表示**（式 8，UMAP）。位置：客户端训练前。粒度：逐样本。论文明确该表示只在本地聚类中使用，不上传（Section V-B）。不需要跨轮历史与干净参考数据。
5. **两种候选聚类的轮廓系数（silhouette score）**。位置：客户端训练前。粒度：客户端级（对聚类结果打分）。用于在层次聚类与 HDBSCAN 之间选择，以及在两个分数都低（较小者小于 0.2、较大者小于 0.4）时放弃划分、把全部数据判为干净（Section V-B、Section VI-D4）。
6. **本地主簇在原始 DCT 维度上的质心 c_k**。位置：客户端训练前计算，随后由服务器接收。粒度：客户端级（每个客户端一个向量）。上传前不需要跨轮历史、干净参考数据或其他客户端数据。
7. **服务器端收到的 K 个客户端局部质心集合**。位置：服务器收到更新时（严格说是在模型聚合之前的一次性阶段）。粒度：客户端级。论文未说明服务器是否保留这些质心的跨轮历史；由于该流程只执行一次，主实验中不需要历史。不需要干净根数据集，不需要额外训练。
8. **全局质心 c_g**（式 13）。位置：服务器聚合阶段计算（对质心做二次聚类），随后广播给客户端。粒度：客户端级集合上的一个向量。不需要跨轮历史与干净参考数据。
9. **把全局质心加入本地特征后的重新聚类结果**（式 14）及据此得到的干净子集 D_clean（式 15）。位置：客户端训练前（本地修正步骤）。粒度：逐样本。需要其他客户端的信息，但只以聚合后的单一全局质心形式获得。论文未说明该步骤需要额外的前向或反向计算（它复用阶段一已有的频率特征）。
10. **本地指令微调数据集 D_k = {(Q_k, A_k)} 本身**。位置：客户端训练前。粒度：逐样本。仅用于本地过滤，不需要上传（Section V-B、Section V-D）。

**攻击一侧的可观测量痕迹。** 论文声称的痕迹是：毒样本与干净样本在"样本级梯度经 DCT 后的频率域特征"上呈现可分的分布差异；后门映射具有低频偏置（Section II-C、Section V-A）。论文报告该攻击能绕过 Krum、Median、Trimmed-mean、FreqFed、FoundationFL 以及 CUBE、ONION、GraCeFul（Table I、Table II、Section IV、Section VI-B）。论文未说明攻击者是否会主动在客户端本地梯度、上传更新或通信内容上留痕之外的其它可观测量（例如输出文本层面的痕迹）。

## 6. 干预动作

**动作类型：过滤样本（filter samples）。** ProtegoFed 不剔除客户端，不重新加权，不裁剪参数，不加噪，不做模型修复或回滚。它做的唯一模型侧干预是：在本地训练开始前，把被判为毒样本的问答对从本地训练集中移走，只保留全局质心所在簇的样本（式 15）。整个过程"只在训练开始时执行一次"（Section V-A）。

**动作发生的位置。** 实际的样本删除发生在客户端，且发生在客户端本地训练之前。服务器侧的动作是"收到所有客户端质心 → 降维二次聚类 → 选主簇 → 在原始维度上算全局质心 → 广播"，它不聚合模型参数、不修改全局模型。论文把这种设计描述为"利用联邦学习允许客户端与服务器交换非私有信息的机制，用全局信息指导本地的毒样本选择"（Section V-A）。

**保守降级。** 当两种聚类的轮廓系数都低（较小者小于 t_s = 0.2 且较大者小于 t_l = 0.4）时，客户端把所有数据视为干净数据，即在这种情况下不执行过滤（Section V-B）。这在效果上接近"仅报告/不动作"的安全回退。

**动态客户端。** 论文称客户端退出不影响已经完成的一次性过滤；新加入的客户端可以在已有全局质心基础上重跑一次流程（论文给出 0.07 秒与 0.39 秒的重跑耗时），并且更多客户端的局部梯度会使后续加入者的过滤更稳健（Section VII-B）。

## 7. 实验设置与主要结果

**设置。** 模型为 9 个开源大模型（1B 至 70B，见第 1 节）；数据为 WebQA、FreebaseQA、NQ、CoQA 四个 FSQA 数据集，除 WebQA 外每数据集抽取 5000 训练 / 400 验证 / 2000 测试（Section VI-A1、Section VI-A2）。主结果使用 IID 划分，训练数据均分到 25 个客户端，每客户端毒比例 10%（Section VI-A3）。NIID 设置：NIID-1 的每客户端毒比例在 [0, 0.4] 随机采样；NIID-2 用 Dirichlet 分布（α = 0.5）采样并把每客户端最大毒比例限制在 0.5；NIID-3 在 NIID-2 基础上去掉 0.5 上限（Section VI-D2）。指标为干净精确匹配率（clean exact match rate, EMR）作为干净任务准确率（clean accuracy, CACC）、毒样本 EMR 作为攻击成功率（ASR）、以及针对样本级防御的召回率（Recall）与 F1（Section VI-A4）。对比方法包括 Krum、Median、Trimmed-mean、FreqFed、FoundationFL、CUBE、GraCeFul、ONION（Section VI-A6）。**参与率（每轮采样多少客户端）论文未说明**；论文只说明 IID 下数据被均分给 25 个客户端。

**后门抑制。** Table II 中，ProtegoFed 在 4 个数据集 × 4 种攻击共 16 个设置里把 ASR 全部降到 0.00，而对照方法在多数设置下 ASR 仍在数十到接近 100 之间（例如 WebQA 上 Badnets：无防御 98.08、Krum 96.75、Median 97.29、Trimmed 97.05、FreqFed 98.23、FoundationFL 89.71、CUBE 97.93、GraCeFul 79.72、ONION 95.32、ProtegoFed 0.00）。摘要报告 ProtegoFed 识别出 92.00% ∼ 100.00% 的投毒样本并把 ASR 降到接近零。

**干净任务效用。** Table II 中，在全部 16 个设置里，ProtegoFed 的 CACC 在其中 9 个设置高于无防御基线；论文称除 ONION 外的防御算法都能把 CACC 维持在可比水平（Section VI-B）。Table V 给出完全干净数据下的对照：WebQA 45.86 → 45.28、FreebaseQA 64.95 → 64.05、CoQA 73.09 → 72.29、NQ 74.80 → 73.95，论文称 CACC 损失小于 1%。

**样本级检测指标。** Table III（IID）中 ProtegoFed 的 Recall 为 92.00% ∼ 100.00%（唯一的 92.00 出现在 WebQA 的 CBA），FreebaseQA 与 CoQA 全部攻击变体下 Recall 均为 100.00；F1 在 FreebaseQA、CoQA 上接近或超过 90%。**需要注意论文正文与表格不一致**：Section VI-C 正文写"even though ProtegoFed only achieved an F1 Score of 79.12% on WebQA (CBA attack), it still maintains a recall rate of 99.08%"，而 Table III 中 WebQA 的 CBA 对应 F1 为 82.71、Recall 为 92.00；79.12 这个数字在 Table I 中是 GraCeFul 在 Vicuna + Addsent 上的 Recall。

**跨模型与跨分布。** Table IV 在 FreebaseQA 上横跨 9 个模型（1B 到 70B）：ProtegoFed 把 ASR 全部降到 0.00，Recall 为 94.80 ∼ 100.00，CACC 与无防御基本持平（例如 Llama-2-70B 从 73.50 升到 82.90，Gemma-2-9B 从 68.05 到 68.65）。Table VI 给出 NIID-1 下的 Recall/F1（ProtegoFed Recall 为 98.29 ∼ 100.00）；Table VII 给出 FreebaseQA 上 α 取 0.1、0.3、0.7、1.0 时的 Recall，论文称接近完美（>96%），例如 NIID-3 下分别为 99.56、96.86、98.81、99.34。论文称 NIID-3 中次优方法的召回率只有约 50%，而 ProtegoFed 仍能在降低 ASR 与保持 CACC 之间取得平衡（Section VI-D2）。

**消融。** Table VIII 给出"多数客户端被毒数据主导"场景下全局二次聚类与本地修正的作用：无修正时 Accuracy 45.90、Precision 22.68、Recall 11.09、F1 14.89；有修正时为 99.29、99.58、98.76、99.17。Table IX 比较目标模块：layers.31.lora_B 的 CACC 45.37、ASR 0.00、Recall 100.00、F1 100.00、参数量 16,384；layers.31.lora_A 为 43.60、32.38、36.92、13.79；layers.15.lora_B 为 44.49、0.00、82.15、58.17；layers.0.lora_B 为 43.70、58.42、28.00、15.14；embed_tokens 为 43.55、5.95、53.85、27.28（参数量 131,072,000）；lm_head 为 44.54、0.00、76.31、59.05（参数量 131,072,000）。Table X 给出轮廓系数消融：去掉 HDBSCAN、去掉层次聚类、去掉阈值三种变体在 NIID-2/NIID-3 上的 Recall 与 F1 均低于完整方法（完整方法平均 Recall 99.53 与 99.42，平均 F1 84.38 与 82.53）。

**恶意客户端场景。** Table XII：恶意客户端比例为 10%、20%、30%、40% 时，仅用 ProtegoFed 的良性客户端召回率（B-Recall）为 100.00、100.00、100.00、99.49；但最终全局模型的 ASR 为 0.00、0.08、20.62、40.29；ProtegoFed 与 FreqFed 结合后四种比例下 ASR 均为 0.00。

## 8. 开销

论文报告了时间开销（Section VII-A、Figure 13）：训练开始前的一次性开销为客户端内聚类 12.43 秒、全局聚类 0.07 秒、本地修正 0.39 秒；ProtegoFed 在 100 轮通信下的总训练时间比 FedAvg 更短，原因是毒数据被移除后每轮训练规模变小；论文称这部分一次性开销约占总训练时间的 1%。

复杂度方面，Section VI-D7 称核心组件 UMAP 与 HDBSCAN 的复杂度约为 O(N log N)（N 为样本数），对分布式客户端而言计算开销低；客户端计算样本级梯度属于正常训练流程的一部分，峰值显存不会超过正常流程，但该节同时写道"We will add a part to further demonstrate its practicality"，表明显存实用性的实证部分在论文中尚未补充完整。

**通信开销与存储开销：论文未报告**（论文只说明每个客户端上传一个局部质心、服务器广播一个全局质心，没有给出字节数或存储占用）。

## 9. 假设、局限与自适应攻击

**论文自述的假设。**

- 全局视角下干净数据占主流，但在部分客户端上毒数据可能占主导（Section III-A）。Section VI-D2 更明确地说："The starting point of ProtegoFed design is that clean data can dominate on most clients, so that the global centroid feature remains on the side of clean samples to guide clients to perform local data correction."
- 所有客户端与服务器都是良性参与者，愿意修改联邦学习流程配合防御；服务器不需要辅助干净数据集，也不需要额外训练（Section III-B2）。
- 攻击者只能改自己提供的数据，不参与也不能控制本地数据预处理、本地训练与全局聚合（Section III-A）。
- 后门映射具有低频偏置，与干净的多对多映射在频率域梯度特征上可分（Section II-C）。
- 客户端上传的局部质心是非私有信息；论文给出的理由是"局部质心不对应任何真实样本"（Section V-B）。
- 每个客户端要有足够多的样本来支撑降维与聚类；论文指出单个客户端数据有限或分布有偏会导致有偏的聚类结果，这正是需要全局协作的原因（Section II-C、Section V-B）。
- 全局模型与本地模型结构相同，联邦过程中只更新并传递 LoRA 模块参数（Section II-A）。

**论文自述的局限。** 当所有客户端的数据都以毒数据为主时，ProtegoFed 的防御会失效（Section VI-D2："when the data on all clients are mainly poisoned data, the defense effect of ProtegoFed will be invalid"）；论文补充说这种极高毒比例在现实中难以出现，因为会让攻击失去隐蔽性并显著损害主任务。恶意客户端场景下，仅靠 ProtegoFed 无法消除恶意客户端带来的 ASR（30% 时 20.62、40% 时 40.29），必须与客户端级防御（如 FreqFed）叠加（Section VII-D、Table XII）。Section VI-D7 的显存论证在论文中尚未补完。

**自适应攻击。** 论文评估了自适应攻击者（Section VII-C）。其推理是：有效后门需要把任意含触发器的输入映射到目标，因此天然带有低频倾向；攻击者若要绕过 ProtegoFed 就得构造高频的后门映射，而这会让 ASR 变得很低，"hard for adaptive-adversary to effectively attack and circumvent ProtegoFed simultaneously"。实验在 FreebaseQA 上构造了高频的一对多映射后门（同一触发器映射到四个不同目标输出），Table XI 报告：无 ProtegoFed 时 CACC 64.15、ASR 0.75；有 ProtegoFed 时 CACC 64.45、ASR 0.05，Recall 62.00、F1 38.06。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）。**

- 分析：这篇论文本身就是联邦 LoRA 指令微调场景，流程迁移的门槛较低；但它默认客户端模型结构完全一致、且"最后一个 transformer 层的 lora_B"是唯一观察模块。若库面对异构基座（不同层数、不同 target_modules、不同 rank），则各个客户端的频率特征维度与语义不再可比，式 9 至式 15 的"在原始 DCT 维度上算质心"这一步会失去意义。
- 分析：逐样本反向传播需要训练框架支持对单条样本单独求梯度并取出指定模块的梯度张量。若库的客户端钩子只在批（batch）级、或在梯度累积、梯度检查点、混合精度缩放之后暴露梯度，则论文依赖的信号会被改变甚至不可得；论文没有讨论这些工程条件。
- 分析：UMAP 与 HDBSCAN 在小样本、长尾客户端上不稳定。论文承认单客户端样本少会造成有偏聚类，并用全局质心修正；但若联邦场景的客户端数远小于 25，或每个客户端的样本数远小于论文设定，服务器侧"对 K 个质心再聚类"这一步本身也会样本不足。
- 分析：论文把上传质心视为隐私安全，只用"质心不是真实样本"作论证，并未做任何隐私攻击评估；而论文自己引用 [60] 指出攻击梯度可以恢复原始样本信息。在联邦 LoRA 场景中，如果库把质心当作可长期累积的跨轮统计量，隐私风险会随轮数上升，论文未说明这一点。
- 分析：论文的威胁入口固定在"训练前的数据采集"，防御也是一次性的。如果投毒发生在训练中途（客户端后续新增数据）或发生在适配器/权重发布环节，则论文的机制不覆盖；论文只讨论了客户端动态加入退出时"新客户端可以重跑一次"，没有讨论同一客户端中途新增毒样本。
- 分析：论文假设服务器不需要根数据集，这是迁移到真实 LoRA 微调库时的一个有利性质；但代价是全局质心的正确性完全依赖"多数客户端干净"这一统计前提。若多数客户端被同一攻击方主导（论文只验证了"毒主导客户端分属不同攻击方、触发器与目标输出各不相同"的多组场景，Table VIII），该前提不成立。
- 分析：论文没有报告通信与存储开销，也没有给出参与率与客户端采样策略，这两点在把方法落成库的调度接口时是缺口。

## 10. 对防护库设计的含义

- 分析：采集底座需要在客户端提供一个"训练开始前的逐样本梯度钩子"，能够在正式联邦训练之前、对本地数据集里的每一条样本单独做一次前向与反向，并导出指定模块（论文中的最后一层 lora_B）的梯度张量。这个采集点是这篇论文特有的，通用性最低，也是整个防御的硬前提；库应允许按模型结构配置目标模块名，而不是硬编码最后一层。
- 分析：库需要一个"训练前一次性阶段"的钩子类别，与"每轮客户端钩子"区分开，并且要支持在服务器下发首轮全局模型之后、客户端本地训练之前插入该阶段。这属于通用能力，因为任何训练前过滤器（数据清洗、去毒、样本筛选）都落在同一时间窗。
- 分析：服务器钩子需要在模型聚合之前支持一次"元数据聚合"通道：接收每个客户端上传的定长向量（本例是原始频率维度的局部质心），对其做聚类并回传一个全局参考量，而不触碰模型参数本身。这是这篇论文特有的协议形态（服务器聚合的是质心而不是更新），库的插件接口如果只允许"聚合权重"就会表达不了它。
- 分析：库的数据视图需要区分"客户端本地使用的降维表示"与"跨客户端可比的原始空间表示"。论文的核心工程约束是：客户端可以在本地做 UMAP 降维用于聚类，但上传的必须是原始 DCT 维度上的质心，否则跨客户端的融合没有意义。这条约束对任何做跨客户端元数据融合的插件都通用。
- 分析：干预接口方面，这篇论文只需要一个"重写本地训练集"的动作（filter_samples），不需要剔除客户端、重新加权、裁剪、加噪、修复或回滚；相应地，库需要暴露"样本级判定位 + 置信度"的回传路径，以便实现论文的保守回退（轮廓系数过低时全部判为干净、不动作）以及 recall/F1 这类检测指标的统计。样本级过滤接口是通用的，置信度驱动的降级路径也是通用的。
- 分析：这篇论文还要求服务器能够下发一个"非模型的全局参考量"并让客户端在训练前二次聚类，这意味着库的客户端钩子应当允许跨阶段的中间状态（本地的频率特征矩阵）在同一个阶段内被复用两次，而不必重新计算梯度。这是这篇论文特有的复用需求，但实现成本低，值得在钩子 API 中显式支持。

## 11. 原文依据

1. 章节：Abstract。支撑：第 7 节中"ProtegoFed 识别 92.00% ∼ 100.00% 的投毒样本并把 ASR 降到接近零"这一关键结果论断。
   "Experimental results on four FL datasets show that ProtegoFed identifies 92.00% ∼100.00% of poisoned samples, reduces the attack success rate to almost zero, and maintains utility on the main task."
2. 章节：Section III-A。支撑：第 2 节中对攻击者身份与能力的界定（恶意用户/数据提供方，只能提供投毒数据）。
   "The adversary is a malicious user (or data provider) who does not directly participate in the model training process. Their influence is constrained to providing poisoned datasets or data sources"
3. 章节：Section III-B2。支撑：第 2 节与第 9 节中"客户端和服务器都是良性且愿意配合修改流程"这一防御者假设。
   "The scenario we consider is that all clients (organizations) and the server are benign participants who want to remove untrusted components from their training data. They are all willing to participate in the defense by modifying the FL process."
4. 章节：Section V-A。支撑：第 3 节与第 5 节中"防御在第一轮之前执行、输入是样本级梯度及其 DCT 频率特征"这一采集点论断。
   "Before the first round, after collecting the global model P0, each client first obtains a representation of the local feature by calculating sample-wise gradients and applying DCT to convert gradients to the frequency space."
5. 章节：Section V-B。支撑：第 5 节中"观察模块为最后一个 transformer 层的 lora_B 参数"这一具体采集位置论断。
   "As suggested in [57], the parameters of the deeper layers tend to amplify the divergence of the gradients in the frequency space. Thus, we use the parameters of the lora_B in the last transformer layer as the target module."
6. 章节：Section V-A。支撑：第 6 节中"服务器对局部质心做二次聚类并算出全局质心"这一服务器侧动作论断。
   "Once the server receives the centroids from all clients, it will cluster the centroids again and select the main cluster, which has the most samples, to calculate the global centroid."
7. 章节：Section V-D。支撑：第 6 节中"把全局质心作为额外样本加入本地特征后再聚类、据此过滤样本"这一客户端侧干预论断。
   "Similarly to the process of Intra-Client frequency-based clustering, each client first adds the global centroid as a sample to its local frequency features, and then perform dimensionality reduction and clustering steps."
8. 章节：Section VI-D2。支撑：第 9 节中"干净数据在多数客户端占主导"这一方法成立的核心假设。
   "The starting point of ProtegoFed design is that clean data can dominate on most clients, so that the global centroid feature remains on the side of clean samples to guide clients to perform local data correction."
9. 章节：Section VII-A。支撑：第 8 节中报告的时间开销数值（12.43 秒、0.07 秒、0.39 秒）。
   "ProtegoFed incurs a small initial overhead before training begins: 12.43 seconds (s) for Intra-Client Clustering, 0.07s for Global Clustering, and 0.39s for Local Revising."
10. 章节：Section VII-C。支撑：第 9 节中"论文评估了自适应攻击者，构造高频后门映射会牺牲 ASR"这一论断。
    "Therefore, to circumvent ProtegoFed, adversaries should construct high-frequency backdoor-mappings that closely resembles the distribution of clean-mappings. However, this will result in inefficient ASR, as relatively high-frequency backdoor-mapping conflicts with the inherent low-frequency inclination above."

```json
{
  "key": "protegofed2026",
  "title": "ProtegoFed: Backdoor-Free Federated Instruction Tuning with Interspersed Poisoned Data",
  "year": 2026,
  "paper_type": "defense",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider", "malicious_client"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "服务器首轮下发的全局模型 P0 中的 LoRA 模块，客户端用它作为计算样本级梯度的起点", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每个本地训练样本在最后一个 transformer 层 lora_B 参数上的单样本反向传播梯度", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "对样本级梯度做 2D-DCT 得到的频率域特征及 flatten 后的向量（式 5、式 6、式 7）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "频率特征经 UMAP 降到二维后的本地表示（式 8），仅用于本地聚类不上传", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "层次聚类与 HDBSCAN 两种候选聚类的轮廓系数，用于选择聚类方法与决定是否放弃划分（阈值 0.2 与 0.4）", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "本地主簇在原始 DCT 维度上计算出的局部质心（式 9、式 10），上传给服务器", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "服务器从所有客户端收到的局部质心集合", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "对 K 个局部质心降维后二次聚类得到的主簇，及其在原始维度上的全局质心（式 11、式 12、式 13）", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "把全局质心作为额外样本加入本地频率特征后再聚类的结果，以及据此得到的干净子集（式 14、式 15）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "本地指令微调问答对数据集本身，用于按聚类结果筛选样本且不需要上传", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["both"],
  "assumptions": [
    "全局视角下干净数据占主流，多数客户端的局部质心落在干净数据区域，服务器二次聚类才能得到落在干净区的全局质心",
    "所有客户端与服务器都是良性参与者且愿意修改联邦学习流程配合防御，服务器不需要辅助干净数据集也不需要额外训练",
    "攻击者只能修改自己提供的数据，不参与也不能控制本地数据预处理、本地训练与全局聚合",
    "后门映射具有低频偏置，与干净的多对多映射在频率域梯度特征上可分",
    "客户端上传的局部质心被视为非私有信息，论文以质心不对应真实样本作为理由",
    "每个客户端需要足够多的样本才能让 UMAP 与聚类有效，否则本地聚类有偏",
    "全局模型与本地模型结构相同，联邦过程中只更新并传递 LoRA 模块参数"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 7 节：ProtegoFed 识别 92.00% 至 100.00% 的投毒样本并把 ASR 降到接近零", "text": "Experimental results on four FL datasets show that ProtegoFed identifies 92.00% ∼100.00% of poisoned samples, reduces the attack success rate to almost zero, and maintains utility on the main task."},
    {"section": "Section III-A", "supports": "第 2 节：攻击者是恶意用户或数据提供方，只能提供投毒数据", "text": "The adversary is a malicious user (or data provider) who does not directly participate in the model training process. Their influence is constrained to providing poisoned datasets or data sources"},
    {"section": "Section III-B2", "supports": "第 2 节与第 9 节：客户端与服务器都是良性且愿意修改流程配合防御", "text": "The scenario we consider is that all clients (organizations) and the server are benign participants who want to remove untrusted components from their training data. They are all willing to participate in the defense by modifying the FL process."},
    {"section": "Section V-A", "supports": "第 3 节与第 5 节：防御在第一轮前执行，输入为样本级梯度及其 DCT 频率特征", "text": "Before the first round, after collecting the global model P0, each client first obtains a representation of the local feature by calculating sample-wise gradients and applying DCT to convert gradients to the frequency space."},
    {"section": "Section V-B", "supports": "第 5 节：观察模块为最后一个 transformer 层的 lora_B 参数", "text": "As suggested in [57], the parameters of the deeper layers tend to amplify the divergence of the gradients in the frequency space. Thus, we use the parameters of the lora_B in the last transformer layer as the target module."},
    {"section": "Section V-A", "supports": "第 6 节：服务器对局部质心二次聚类并计算全局质心", "text": "Once the server receives the centroids from all clients, it will cluster the centroids again and select the main cluster, which has the most samples, to calculate the global centroid."},
    {"section": "Section V-D", "supports": "第 6 节：客户端把全局质心加入本地特征后重新聚类并据此过滤样本", "text": "Similarly to the process of Intra-Client frequency-based clustering, each client first adds the global centroid as a sample to its local frequency features, and then perform dimensionality reduction and clustering steps."},
    {"section": "Section VI-D2", "supports": "第 9 节：方法成立依赖干净数据在多数客户端占主导", "text": "The starting point of ProtegoFed design is that clean data can dominate on most clients, so that the global centroid feature remains on the side of clean samples to guide clients to perform local data correction."},
    {"section": "Section VII-A", "supports": "第 8 节：报告的一次性时间开销数值", "text": "ProtegoFed incurs a small initial overhead before training begins: 12.43 seconds (s) for Intra-Client Clustering, 0.07s for Global Clustering, and 0.39s for Local Revising."},
    {"section": "Section VII-C", "supports": "第 9 节：论文评估了自适应攻击，高频后门映射会使 ASR 低下", "text": "Therefore, to circumvent ProtegoFed, adversaries should construct high-frequency backdoor-mappings that closely resembles the distribution of clean-mappings. However, this will result in inefficient ASR, as relatively high-frequency backdoor-mapping conflicts with the inherent low-frequency inclination above."}
  ]
}
```
