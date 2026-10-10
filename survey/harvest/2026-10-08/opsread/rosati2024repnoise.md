# rosati2024repnoise：Representation Noising（RepNoise，表示加噪）

## 1. 方法一句话

输入是一个已经安全对齐的预训练大语言模型（LLM）权重 $\theta$，以及防御者自己收集的成对数据（同一个不安全问题的「有害回答」与「安全回答/拒绝」）；输出是同一架构的一份被改写过的权重 $M^*_\theta$（论文称"免疫"模型），使得攻击者拿到权重后即使继续做有害微调（harmful fine-tuning attack, HFA），也很难把有害行为重新训出来。它输出的不是对某个客户端的判定，而是对模型权重本身的一次修改；论文把它定义为最小化输入 $X$ 与中间激活 $Z_\theta$ 之间互信息 $\arg\min_\theta I(X;Z_\theta)$（§3 Theorem 1），并给出三项损失：稳定项 $\ell_{stability}$、表示加噪项 $\ell_{noise}$、有害梯度上升项 $\ell_{ascent}$，合成 $L_{RepNoise}$（eq. (5)）。

## 2. 运行位置

- **论文的实际位置：训练之外（outside_training）。** RepNoise 由防御者在把权重发布/交出之前执行一次，用防御者本地的模型和本地收集的数据做一轮（BeaverTails 为 1 epoch）免疫化训练；论文明确说"攻击者获得权重之后防御者无法再干预"（§3）。它不属于攻击者的微调循环，也不做任何在线检测。
- **集中式方法在联邦流程中的最自然位置（分析：）。** 论文完全没有客户端/服务器、聚合或轮次的概念（§2 的威胁模型是"防御者发布权重、攻击者本地微调"）。若必须放入联邦运行时，最自然的是**服务器聚合之后、下发之前（server_post_aggregate）**：服务器用自己持有的成对安全/不安全数据，对刚聚合出的全局模型跑若干步 RepNoise 更新，再把免疫后的全局模型作为发布版/下一轮初始模型下发；等价的另一种读法是**联邦训练开始之前（outside_training）**对初始全局模型做一次性免疫，此后所有客户端都从这个免疫模型出发训练。这两种映射都要求服务器侧持有成对的有害/无害样本，且都是"服务器独占计算"。
- **是否需要额外往返：不需要。** 论文未说明任何客户端—服务器协议；RepNoise 只用到防御者本地的模型与本地数据，没有任何通信步骤。JSON 中 `needs_round_trip` 取 `false`。
- **注意（分析：）。** 如果把 RepNoise 塞进联邦循环并每轮重复执行，论文没有评测过这种用法；而且论文发现免疫训练 epoch 数从 1 增到 2 会让防御几乎失效（table 17，攻击后 0.12 → 0.78），所以不应默认可以反复累积执行。

## 3. 算子流水线

以下按论文 Algorithm 1（附录 B.1）与附录 B.2 的执行顺序列出。所有张量记号：$B$ 为 batch 内样本数，$T$ 为 token 序列长度，$d$ 为隐层维度（token embedding size），$L$ 为层数（llama2-7b-chat 为 32 层，附录 H），$V$ 为词表大小。

**步骤 1：配对样本与共享 token 掩码构造**
- 输入：不安全问题集合 $X$、对应的有害回答 $Y_{harmful}$、同一问题的安全回答/拒绝 $Y_{harmless}$（token id，形状 $B\times T$）。
- 计算：对每个采样 batch 取 $b_{harmless}$ 与 $b_{harmful}$，令 $\text{MASK} \leftarrow b_{harmless} \cap b_{harmful}$，即一对样本中共同的 token（论文原文："The mask is simply the tokens that a paired sample has in common."）。掩码的作用是：共享的问题部分既不做梯度上升、也不加噪。
- 输出：成对 batch 与掩码 MASK。
- 出处：Algorithm 1 第 3–4 行；附录 B.1；附录 D.1（配对数据构造）。

**步骤 2：稳定损失（无害数据语言建模损失）**
- 输入：无害 batch $b_{harmless}$，$B\times T$。
- 计算：$\ell_{stability} = \mathbb{E}_{(X,Y)\sim D_{harmless}} L(M_\theta(X), Y)$，即因果语言建模交叉熵；论文说明加入该项是为了"梯度上升会损害整体语言建模能力"（§3，eq. (4) 及前后文）。
- 输出：标量 $\ell_{stability}$。
- 出处：Algorithm 1 第 5 行；eq. (4)。

**步骤 3：有害前向并捕获逐层表示**
- 输入：应用 MASK 后的有害 batch $b_{harmful}$（Algorithm 1 写作 $M_\theta(b_{harmful}\circ \text{MASK})$）。
- 计算：一次前向，捕获**每一层 post-MLP 但 pre-residual 的激活** $a_l$，$l=1..L$，形状约为 $(B,T,d)$。论文给出的选择理由：残差相加后表示会与上一层趋于相似，从而丢失该层的独特信息；也试过 post-attention 等其他位置，pre-residual 最有效。
- 输出：$\{a_l\}_{l=1}^{L}$。
- 出处：Algorithm 1 第 6 行；附录 B.1。

**步骤 4：逐层语言建模损失（tuned-lens 风格）**
- 输入：每层激活 $a_l$（$B\times T\times d$）与有害标签 $b_{harmful}$。
- 计算：仿照 tuned lens，**复用最终的语言模型头（LM head）**接在每一层激活上，计算该层的语言建模损失 $\ell^l_{harmful}=L(M_\theta(a_l), b_{harmful})$；该量在 Algorithm 1 第 12 行被当作 $\ell^l_{ascent}$ 使用。
- 输出：每层一个标量 $\ell^l_{ascent}$，共 $L$ 个。
- 出处：Algorithm 1 第 7–8 行；附录 B.1；对应 eq. (3) 的 $\ell_{ascent}$ 定义。

**步骤 5：标准高斯噪声采样**
- 输入：无（需要与 $a_l$ 同形状的目标）。
- 计算：$\text{noise}\sim N(0,I)$，形状与 $a_l$ 一致。
- 输出：噪声张量。
- 出处：Algorithm 1 第 9 行；附录 B.1。

**步骤 6：MMD 表示—噪声分布匹配（表示加噪项）**
- 输入：表示 $a_l$ 与同形状的 $N(0,I)$ 采样。
- 计算：$\ell^l_{noise}=\text{MMD}(a_l,\text{noise},\exp)$（Algorithm 1 第 10 行的写法），即用**多核高斯核（multi-kernel Gaussian kernel）的最大均值差异（Maximum Mean Discrepancy, MMD）**估计有害表示分布与标准高斯之间的分布距离；理论上它替代 $\ell_{noise}=KL(p(Z|X)\,\|\,N(0,I))$（eq. (5) 前的推导）。论文给出的替换理由是 KL 不是距离度量，不适合直接最小化分布差异，且 MMD 可微、可采样估计。论文补充说噪声对象是"token embedding size × 上下文 token 数"的表示矩阵，且逐层进行。
- 输出：每层一个标量 $\ell^l_{noise}$。
- 出处：Algorithm 1 第 10 行；附录 B.1；eq. (5)。

**步骤 7：层间平均**
- 输入：$\{\ell^l_{noise}\}$、$\{\ell^l_{ascent}\}$。
- 计算：分别求 $\frac{1}{L}\sum_l \ell^l_{noise}$ 与 $\frac{1}{L}\sum_l \ell^l_{ascent}$。
- 输出：两个标量。
- 出处：Algorithm 1 第 12 行。

**步骤 8：对数压缩（只作用于 ascent 项）**
- 输入：$\frac{1}{L}\sum_l \ell^l_{ascent}$。
- 计算：取 $\log\big(\frac{1}{L}\sum_l \ell^l_{ascent}\big)$。论文理由：实践中 $\ell_{ascent}$ 可能非常大并主导整个损失函数。
- 输出：压缩后的标量。
- 出处：Algorithm 1 第 12 行；附录 B.1 最后一段。

**步骤 9：损失合成**
- 输入：$\ell_{stability}$、层均 $\ell_{noise}$、对数压缩后的层均 $\ell_{ascent}$。
- 计算：Algorithm 1 第 12 行写作 $\ell_{all}=\ell_{stability}+\beta\cdot\frac{1}{L}\sum_l \ell^l_{noise}-\alpha\cdot\log\big(\frac{1}{L}\sum_l \ell^l_{ascent}\big)$；正文 eq. (5) 写作 $L_{RepNoise}=L_{Adversarial}+\alpha\cdot\ell_{noise}=\ell_{stability}+\alpha\cdot\ell_{noise}-\beta\cdot\ell_{ascent}$。**两者对 $\alpha$、$\beta$ 的绑定正好相反**（详见第 5、9 节）。理论出处是 §3 的 Theorem 1 与 eq. (2)（最小化迁移概率 ⇒ 最小化 $I(X;Z)$）。
- 输出：标量总损失 $\ell_{all}$。
- 出处：Algorithm 1 第 12 行；eq. (5)；§3 Theorem 1、eq. (2)。

**步骤 10：优化器更新**
- 输入：$\nabla_\theta \ell_{all}$。
- 计算：$\theta \leftarrow \theta-\eta\nabla_\theta \ell_{all}$，重复 $n$ 步（$n$ = 1 epoch × 10k 样本 / batch size）。
- 输出：更新后的 $\theta$。
- 出处：Algorithm 1 第 2、13 行；附录 B.2。

**步骤 11：输出免疫检查点（层覆盖范围约束）**
- 输入：训练结束的 $\theta$。
- 计算：直接导出 $M^*_\theta$。论文默认不冻结任何层；消融显示冻结 LM head 或 20–31 层几乎无影响，冻结 10–20 层开始退化，冻结 0–10 层则防御完全失效，因此**必须更新全部层**。
- 输出：可发布的免疫权重 $M^*_\theta$。
- 出处：§3；table 6 / 附录 H table 13。

## 4. 采样与规模控制

- **样本（samples）**：BeaverTails 免疫用 **10k 条配对样本**（10k 个有害问题 + 各自的有害回答，以及同 10k 个问题的安全回答/拒绝），见附录 B.2。DecodingTrust/RTP 毒性域免疫用 **351 条**（附录 B.2、D.2）。样本量消融使用 **1k / 2.5k / 5k**（table 20，结论是防御效果与样本量强相关）。泛化实验中"Half"设置用 **5k 随机采样**训练防御、再用 **5k 未见样本**攻击（table 5）。HEX-PHI 扩展防御用 **230 条不重叠样本**（附录 E.2）。防御训练本身不做样本截断以外的降维；攻击阶段才在 1k/10k 之间变化（table 1）。
- **客户端（clients）**：论文未使用。这是集中式方法，没有客户端抽样或客户端选择。
- **层（layers）**：不做层抽样，Algorithm 1 对**所有层**的 post-MLP pre-residual 激活计算噪声损失与逐层 ascent 损失（附录 B.1）。table 6/13 的"冻结层"是消融实验条件，不是采样。
- **参数坐标（coordinates）**：论文未使用。没有任何坐标级抽样、稀疏化或 top-k 选择；附录 J 只是建议未来工作可以把表示投影到 top-k 奇异值以降低方差，论文自己没有实现。
- **轮次（rounds）**：免疫训练轮次为 **1 epoch（BeaverTails）/ 4 epochs（RTP）**（附录 B.2）；epoch 数增加到 2 反而使防御失效（table 17）。防御只做一次，不是多轮迭代。
- **探针（probes）**：属于第 5 节机制分析，不是防御流程的一部分。线性探针用 **15k** 条 BeaverTails 问答对（一半不安全），80% 训练 / 20% 测试，重复 **10 个随机种子**（§5）；PCA 与逐层 log 概率分析用 **100 条有害 + 100 条无害**样本（§5，Fig. 3、Fig. 4）。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| $\alpha$ | eq. (5) 中乘 $\ell_{noise}$；Algorithm 1 第 12 行中却乘 ascent 项（论文自相矛盾） | BeaverTails 报告 $\alpha=1$；RTP 报告 $\alpha=2$；正文另有 $\alpha=2,\beta=4$ 的身份漂移实验 | 附录 B.2；附录 E.3；eq. (5)；Algorithm 1 第 12 行 |
| $\beta$ | eq. (5) 中乘 $\ell_{ascent}$；Algorithm 1 第 12 行中却乘 $\ell_{noise}$ | BeaverTails 报告 $\beta=0.001$；RTP 报告 $\beta=4$；附录 J 称"控制加噪量"的 $\beta$ 很敏感；附录 G 又称 $\beta=4$ 表示更重视 ascent | 附录 B.2；附录 G；附录 J；table 18 |
| 网格搜索范围 | 超参搜索空间 | $\alpha\in\{4,2,1,0.5,0.1\}$，$\beta\in\{2,1,0.1,0.01,0.001,0.0001\}$，lr $\in\{8\times10^{-8},1\times10^{-5},2\times10^{-5},3\times10^{-5},8\times10^{-5},1\times10^{-4},1\times10^{-3}\}$，epochs $\in\{1,2,4\}$ | 附录 B.2 |
| 学习率 | 免疫训练 LR | BeaverTails 与 RTP 均为 $2\times10^{-5}$；HEX-PHI 扩展防御为 $3\times10^{-4}$；13B 与 Qwen 1.5 系列为 $1\times10^{-3}$ | 附录 B.2；附录 E.2；附录 K |
| epoch 数 | 免疫训练轮数 | BeaverTails 1；RTP 4；HEX-PHI 扩展 1 | 附录 B.2；附录 E.2 |
| batch size | 训练批大小 | 正文写 8（附录 B.2），附录 L 又写 batch size of 4 用于显存报告 | 附录 B.2；附录 L |
| 优化器与调度 | 优化设置 | Adam，无 weight decay；cosine 学习率调度，10% warmup | 附录 B.2 |
| 随机种子 | 复现种子 | 42（论文称随机选定、未针对其调优）；附录 J 显示种子 7、17 会显著改变防御效果 | 附录 B.2；附录 E.1；table 19 |
| 更新层集合 | 参与更新的层 | 默认全部层；冻结 LM head / 20–31 / 最后一层 / 10–20 / 0–10 为消融条件 | table 6；附录 H |
| MMD 核 | 噪声分布匹配的核 | "multi-kernel Maximum Mean Discrepancy (MMD) with a Gaussian kernel"；Algorithm 1 第 10 行第三参数写作 `exp`。**核数量、带宽/长度尺度、是否有偏估计、样本数均论文未说明** | 附录 B.1；Algorithm 1 第 10 行 |
| MASK | 配对样本公共 token | 定义为一条配对样本中共同的 token；具体如何作用到损失上论文未说明 | Algorithm 1 第 4 行；附录 B.1 |
| 其他模型 | 超参搜索空间 | LR $\in\{1\times10^{-3},5\times10^{-4},1\times10^{-4},5\times10^{-5},1\times10^{-5}\}$，$\beta\in\{0.0001,0.001,0.01,0.1,0.25,1\}$；Qwen 1.5 取 LR $1\times10^{-3}$、$\beta=0.25$，llama-13b-chat 取 LR $1\times10^{-3}$、$\beta=0.001$ | 附录 K |

## 6. 判定与动作

- **没有判定/检测环节。** RepNoise 不输出任何分数、阈值判断或聚类规则；它不区分"哪个样本有害"，而是直接用成对数据做一次权重改写。论文中出现的阈值 $\phi$（§2）是**攻击是否成功**的形式化定义（$g(M_\theta)>\phi$），不是防御的判定规则。
- **唯一的动作是修改权重。** 动作由 Algorithm 1 第 13 行的梯度步 $\theta\leftarrow\theta-\eta\nabla_\theta\ell_{all}$ 给出；作用对象是**待发布/待下发的模型检查点**，而不是客户端更新。
- **"加噪"不是对更新加噪。** 论文的噪声项是把有害输入在各层的表示分布向 $N(0,I)$ 靠拢（MMD 目标），不是往权重或梯度上加高斯噪声；论文没有给出显式的噪声幅度、$\epsilon$ 或裁剪阈值，幅度由 MMD 损失与权重系数隐式决定。也不是差分隐私（differential privacy），论文未提及任何 DP 保证。
- **没有裁剪、剔除、加权、替换全局模型的规则**：论文未说明任何阈值式剔除或按客户端加权；没有跨轮累积机制（防御只跑一轮，见第 4 节）。
- **是否跨轮累积：论文未说明。** 分析：如果在联邦循环中每轮服务器都执行 RepNoise，权重改动会逐轮累积，但论文明确显示免疫训练 epoch 数增加会削弱防御（table 17：1 epoch 0.12，2 epochs 0.78），因此不应假定可以这样做。

## 7. 需要的外部资源

- **一个已安全对齐的预训练 LLM**：主实验为 llama2-7b-chat；另在 llama-2-13b-chat 与 Qwen 1.5 系列（0.5B、1.8B、4B、7B）上验证（附录 K）；还在无安全护栏的 llama2-7b 上做了对照（附录 K.1）。
- **成对的安全/不安全数据（核心且昂贵）**：需要同一个不安全问题的"有害回答"和"安全回答/拒绝"。BeaverTails HarmfulQA 原始规模 333,963 条问答对、14 类危害，论文先筛出"不安全问题 + 不安全回答"，再用 llama2-7b-chat 生成拒绝回答，并用下面的分类器筛出真正安全的回答，最终得到 **18,106 条**配对数据（附录 D.1），防御训练从中随机取 10k。毒性域用 DecodingTrust 的 Real Toxicity Prompts split，筛出有毒续写并让 llama2-7b-chat 生成安全续写，得到 **351 条**（附录 D.2）。HEX-PHI 扩展防御另取 230 条（附录 E.2）。论文明确指出"我们的方法要求成对拒绝数据，这使数据收集更昂贵、更复杂"（§7 Limitations）。
- **一个有害性分类器**：deberta-v3-xsmall，在 BeaverTails 约 330k 条安全/不安全问答对上训练 4 epochs、batch size 128、Adam、LR $6\times10^{-6}$，F1 = 0.87（附录 D.1.1）。它既用于构造配对数据（筛选生成的拒绝回答确实安全），也用于评测有害性分数（取 harmful 标签 logit 在样本上的均值）。
- **评测侧资源（不是防御本身必需）**：Jigsaw Perspective API（毒性，附录 D.2）、GPT-4o-mini 作为 LLM-as-judge、Eleuther AI LM Evaluation Harness 与 TruthfulQA/MMLU/Hellaswag/Winogrande/ARC/Ethics/CrowS-Pairs（table 3）、GEM 的 5 个数据集（table 4）、ROBBIE、XSTest、HarmBench（附录 E）。
- **计算资源**：主要是单节点 4×A100 (80GB)，偶用 4×A40 (40GB) 与 1×A100 (40GB)（附录 L）。
- **不需要**：根数据集、预训练检测器、对齐前后的权重对、额外的判别模型作为防御组件（论文未使用）。

## 8. 计算与存储开销

论文报告的开销（附录 L）：

- 防御平均运行时间 **"1:52 on 4xA40s using a defence of 10k samples"**；按 RunPod $0.35 CAD/hr 计、按两小时算约 **$2.80**。（论文写作 `1:52`，未明说单位；结合"按两小时计费"推断为 1 小时 52 分，这一点论文未写清楚。）
- 同样 10k 样本的有害微调攻击平均 **26 分钟**（batch size 4），约 **$1.40**。
- 峰值显存：RepNoise **26.37 GB/卡**（batch size 4），有害微调 **20.81 GB/卡**（batch size 4）。
- 论文明确指出时间增量来源："The increase in time for RepNoise largely comes from the sequential iteration over layers for computing the gradient ascent loss as it requires a forward pass through the final language modeling head per layer."

分析（流水线开销来源与增长量级）：

- 主要开销来自**步骤 3–6**：每个 batch 一次有害前向（步骤 3），随后对**每一层**做一次 LM head 投影并计算语言建模损失（步骤 4，产生 $B\times T\times V$ 的 logits，$V$ 很大，是显存与算力的主要来源），再对每一层做 MMD（步骤 6）。因此单步开销大致随 $L\times B\times T\times V$ 增长，并需要对 $L$ 个中间激活做缓存或逐层串行处理（论文说"sequential iteration over layers"，说明实现上是逐层串行）。
- MMD 本身在表示向量数量上是二次复杂度（分析：），但论文没有报告 MMD 的复杂度、核数或每层采样多少条表示向量。
- 反向传播需要保留全部 $L$ 层的中间激活与逐层 logits，这是显存高于普通微调（26.37 GB vs 20.81 GB）的主要原因（分析：）。
- 训练之外没有推理开销：免疫后的模型与原始模型同架构同参数量，推理成本不变（分析：）。
- 存储开销论文未报告；按流水线至少需要保存一份完整模型检查点（分析：）。

## 9. 实现时容易错的地方

论文明确强调的实现细节：

1. **激活位置必须是 post-MLP、pre-residual**，不能取 post-attention，也不能取残差相加之后的位置；论文说残差相加后表示会与上一层趋于相似而丢失该层独有信息，并且实测 pre-residual 最有效（附录 B.1）。
2. **必须做 MASK**：配对样本中共享的问题 token 既不做梯度上升、也不加噪；否则共享问题部分的表示会被加噪、并与无害损失产生矛盾梯度信号（附录 B.1、附录 J；table 15 显示去掉 mask 后防御变差、稳定性下降）。
3. **必须逐层 ascent**（tuned-lens 方式复用 LM head 在每层算损失），去掉后防御显著变弱（table 15）。
4. **噪声项与 ascent 项必须同时存在**：只留 noise 不 ascent 的模型甚至比原始 base 模型更差，只留 ascent 则防御几乎无效（table 14）。
5. **对 ascent 项取对数**：论文说实践中 $\ell_{ascent}$ 会非常大并主导整个损失，所以 Algorithm 1 第 12 行对它取 log（附录 B.1）。注意只对 ascent 取 log，noise 项与 stability 项不取。
6. **必须更新全部层，尤其是最前面的 0–10 层**：冻结 0–10 层会让防御完全失效（table 6 / 13）。
7. **超参极度敏感**：LR 从 $2\times10^{-5}$ 调到 $4\times10^{-5}$ 就使防御失效（table 16）；epoch 1→2 失效（table 17）；$\beta$ 在 0.001/0.01/0.0001/4 之间结果从 0.12 变到 0.75（table 18）；随机种子 42/7/17 结果也不同（table 19）。论文承认这是方法的局限。
8. **需要成对拒绝数据**（附录 D.1、§7），只有单侧有害数据不够。
9. 论文在 §4.1 写 "RepNoise minimizes eq. (1)"，从上下文看应为 eq. (5)；按 eq. (1) 实现会得到攻击目标而不是防御目标。

论文没说清、实现时必须自己决定的地方（逐条）：

1. **$\alpha$ 与 $\beta$ 各自绑定哪一项**：eq. (5) 是 $\alpha$ 乘 noise、$\beta$ 乘 ascent；Algorithm 1 第 12 行是 $\beta$ 乘 noise、$\alpha$ 乘 ascent；附录 J 称 β "控制加噪量"，附录 G 又称 β 表示"对提高有害样本损失的重视程度"。三处互相矛盾，必须自己指定映射并记录。
2. **eq. (4) 的文字写成 "where α is a regularization term"**，但公式里出现的是 $\beta$，疑为笔误；实现时需自行判断。
3. **MMD 的具体形式完全未说明**：核数量（"multi-kernel"但只给了一个 `exp` 参数）、带宽/长度尺度、是否无偏估计、$a_l$ 与 noise 的样本数是否相同、MMD 是在哪些维度上聚合（按 token 还是按整条序列）、是否对表示做归一化。
4. **MASK 如何作用到损失上未说明**：是把它当作布尔位置掩码把共享 token 的 loss 置零、还是只保留非共享位置；`MASK ← b_harmless ∩ b_harmful` 在 batch 层面如何定义（token 集合交集还是逐样本配对）也没有说明。
5. **$\ell^l_{ascent}$ 与 $\ell^l_{harmful}$ 的关系未说明**：Algorithm 1 第 8 行计算的是 $\ell^l_{harmful}$，第 12 行用的是 $\ell^l_{ascent}$，两者应为同一个量但没有明说。
6. **$b_{harmless}$ 与 $b_{harmful}$ 是否按同一问题配对采样未说明**：Algorithm 1 第 3 行是两个独立采样语句，但方法叙述要求"paired refusal data"，是否保证 batch 内一一对应需要自己决定。
7. **batch size 前后不一致**：附录 B.2 写 8，附录 L 写 4；"batch size of 8" 是每个数据集各 8 还是合计 8 也未说明。
8. **"1:52" 的时间单位未说明**（只可从两小时计费反推）。
9. **优化细节未说明**：10% warmup 与 cosine 调度是否作用于全部参数、是否使用梯度累积/梯度裁剪、多卡（4×A40/A100）如何并行、每层 LM head 的 logits 是否 detach。
10. **是否在训练中冻结某些层**未说明；默认全量更新，但论文没有明写"不冻结"。
11. **代码与完整复现细节未随论文发布**（NeurIPS checklist 第 5 项答 "No"，称将在评审后发布）。

## 10. 原文依据

1. 支撑步骤 3（激活捕获位置）："For each training step of RepNoise, we perform this across all of the post-MLP but pre-residual activations of each layer. The pre-residual activations were chosen because the representations become similar to the previous layer after adding the residuals"（附录 B.1）
2. 支撑步骤 4（逐层 ascent 用 LM head）："For our layer-wise gradient ascent losses, we use a similar approach to the tuned lens [7] and use the language model head on top of each activation to compute language modelling loss at each layer."（附录 B.1）
3. 支撑步骤 1（MASK）："We also draw the reader's attention to the MASK operation. This is because we use paired refusal data for our method where the first part of a question or prompt is shared between the harmful and harmless target text."（附录 B.1）
4. 支撑步骤 6（噪声项目标分布）："We can do this by minimizing the KL divergence between the distribution of harmful representations given harmful input token sequences Pθ[t=0](Z | X) and Gaussian noise N(0, I)"（§3）
5. 支撑步骤 6（MMD 替代 KL）："Because of this, we use multi-kernel Maximum Mean Discrepancy (MMD) with a Gaussian kernel (as in Wang et al. [63]) which estimates a distribution over harmful samples."（附录 B.1）
6. 支撑步骤 8（ascent 取对数）："Finally we mention that in practice ℓascent can be very large and dominate the loss function, this is why we take the log of ℓascent."（附录 B.1）
7. 支撑步骤 10/11（超参与规模）："For the BeaverTails attack, we train RepNoise for 1 epoch on 10k paired samples (10k harmful questions with harmful answers and 10k of the same questions with safe answers or refusals) using α = 1, β = 0.001"（附录 B.2）
8. 支撑步骤 11（必须更新浅层）："Finally, we see that freezing the middle layers starts to degrade the effectiveness of the defence and freezing the first ten layers completely ruins the effectiveness of the defence."（附录 H）

```json
{
  "key": "rosati2024repnoise",
  "method": "Representation Noising (RepNoise)",
  "stages": ["outside_training", "server_post_aggregate"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "构造配对样本与共享 token 掩码",
      "operator": "paired_refusal_dataset_construction",
      "input": "不安全问题 X 与同一问题的有害回答 Y_harmful、安全回答/拒绝 Y_harmless，token id 形状 B×T",
      "output": "配对 batch (b_harmless, b_harmful) 与掩码 MASK",
      "params": {"n_pairs": "10k (BeaverTails, 附录B.2); 351 (RTP, 附录B.2); 230 (HEX-PHI 扩展, 附录E.2)", "mask": "b_harmless 与 b_harmful 的共同 token (Algorithm 1 第4行)"},
      "source": "Algorithm 1 lines 3-4; Appendix B.1; Appendix D.1"
    },
    {
      "step": "无害数据稳定损失",
      "operator": "causal_lm_cross_entropy",
      "input": "无害 batch b_harmless, B×T",
      "output": "标量 l_stability",
      "params": {},
      "source": "Algorithm 1 line 5; eq. (4)"
    },
    {
      "step": "有害前向并捕获逐层表示",
      "operator": "forward_capture_pre_residual_activations",
      "input": "应用 MASK 后的有害 batch b_harmful, B×T",
      "output": "每层 post-MLP pre-residual 激活 a_l, (B, T, d)",
      "params": {"layers": "全部 L 层 (llama2-7b-chat L=32)", "position": "post-MLP, pre-residual"},
      "source": "Algorithm 1 line 6; Appendix B.1"
    },
    {
      "step": "逐层语言建模损失 (tuned-lens 风格)",
      "operator": "layerwise_lm_head_loss",
      "input": "a_l (B,T,d) 与有害标签 b_harmful",
      "output": "每层标量 l_ascent^l (Alg.1 中写作 l_harmful^l)",
      "params": {"head": "复用最终 LM head"},
      "source": "Algorithm 1 lines 7-8; Appendix B.1; eq. (3)"
    },
    {
      "step": "标准高斯噪声采样",
      "operator": "sample_standard_gaussian",
      "input": "与 a_l 同形状的采样目标",
      "output": "noise ~ N(0, I), (B, T, d)",
      "params": {},
      "source": "Algorithm 1 line 9"
    },
    {
      "step": "MMD 表示-噪声分布匹配",
      "operator": "multi_kernel_gaussian_mmd",
      "input": "a_l 与同形状 noise",
      "output": "每层标量 l_noise^l",
      "params": {"kernel": "Gaussian (Alg.1 写作 exp), multi-kernel", "bandwidth": "论文未说明", "n_kernels": "论文未说明"},
      "source": "Algorithm 1 line 10; Appendix B.1; eq. (5)"
    },
    {
      "step": "层间平均",
      "operator": "layerwise_mean",
      "input": "{l_noise^l} 与 {l_ascent^l}",
      "output": "(1/L)Σ l_noise^l 与 (1/L)Σ l_ascent^l",
      "params": {},
      "source": "Algorithm 1 line 12"
    },
    {
      "step": "ascent 项对数压缩",
      "operator": "log_compress",
      "input": "(1/L)Σ l_ascent^l",
      "output": "log((1/L)Σ l_ascent^l)",
      "params": {},
      "source": "Algorithm 1 line 12; Appendix B.1"
    },
    {
      "step": "三项损失合成",
      "operator": "weighted_loss_composition",
      "input": "l_stability、层均 l_noise、对数压缩后的层均 l_ascent",
      "output": "标量 l_all",
      "params": {"alpha": "1 (BeaverTails), 2 (RTP)", "beta": "0.001 (BeaverTails), 4 (RTP)", "note": "eq.(5) 与 Algorithm 1 第12行对 alpha/beta 的绑定相反"},
      "source": "Algorithm 1 line 12; eq. (5); Theorem 1; eq. (2)"
    },
    {
      "step": "优化器更新",
      "operator": "adam_cosine_warmup_step",
      "input": "梯度 ∇θ l_all",
      "output": "更新后的 θ",
      "params": {"lr": "2e-5 (BeaverTails/RTP), 3e-4 (HEX-PHI), 1e-3 (13B/Qwen)", "epochs": "1 (BeaverTails), 4 (RTP)", "batch_size": "8 (附录B.2) / 4 (附录L)", "optimizer": "Adam, no weight decay", "schedule": "cosine, 10% warmup", "seed": 42},
      "source": "Algorithm 1 lines 2, 13; Appendix B.2; Appendix L"
    },
    {
      "step": "导出免疫检查点",
      "operator": "release_immunized_checkpoint",
      "input": "训练结束的 θ",
      "output": "可发布的免疫模型 M*_θ",
      "params": {"freeze": "默认不冻结；冻结 0-10 层使防御完全失效 (table 6 / 附录H)"},
      "source": "§3; table 6; Appendix H"
    }
  ],
  "sampling": [
    {"what": "samples", "how": "成对(有害回答/安全回答)样本训练防御", "size": "10k (BeaverTails, 附录B.2); 351 (RTP, 附录B.2/D.2); 1k/2.5k/5k (table 20); 5k+5k (Half, table 5); 230 (HEX-PHI, 附录E.2)"},
    {"what": "clients", "how": "论文未使用", "size": "论文未使用（集中式方法，无客户端概念）"},
    {"what": "layers", "how": "不做层抽样，对全部层的 post-MLP pre-residual 激活计算损失", "size": "L=32 (llama2-7b-chat, 附录H)"},
    {"what": "coordinates", "how": "论文未使用", "size": "论文未使用（无坐标级稀疏化或投影）"},
    {"what": "rounds", "how": "免疫训练 epoch 数，防御只执行一次", "size": "1 epoch (BeaverTails) / 4 epochs (RTP) (附录B.2); 2 epochs 会失效 (table 17)"},
    {"what": "probes", "how": "机制分析的线性探针与 PCA，不属于防御流程", "size": "15k BeaverTails 问答对、80/20 划分、10 个种子；PCA/概率分析 100 有害 + 100 无害 (§5)"}
  ],
  "resources": [
    "已安全对齐的预训练 LLM：llama2-7b-chat 为主，另测 llama-2-13b-chat 与 Qwen 1.5 (0.5B-7B)（附录K）",
    "成对拒绝数据：同一不安全问题的有害回答 + 安全回答（BeaverTails 过滤后 18,106 条，防御用 10k；RTP 351 条；HEX-PHI 230 条）（附录D.1/D.2/E.2）",
    "有害性分类器：deberta-v3-xsmall，330k BeaverTails 样本训练 4 epochs，batch 128，Adam，lr 6e-6，F1 0.87（附录D.1.1）",
    "评测外部服务与基准（非防御组件）：Jigsaw Perspective API、GPT-4o-mini judge、Eleuther LM Harness、GEM、ROBBIE、XSTest、HarmBench（附录D/E）",
    "计算资源：单节点 4×A100 80GB，偶用 4×A40 40GB 与 1×A100 40GB（附录L）"
  ],
  "actions": ["transform_gradients", "add_noise"],
  "dominant_cost": "逐层 LM head 前向 + 每层 MMD：论文报告 10k 样本在 4×A40 上平均 1:52、约 $2.80（RunPod $0.35 CAD/hr 按两小时计），峰值显存 26.37 GB/卡（batch 4），对照有害微调 26 分钟、20.81 GB/卡；论文明确说增量来自逐层串行计算 gradient ascent loss 所需的每层语言模型头前向（附录L）。",
  "underspecified": [
    "eq. (5) 与 Algorithm 1 第12行对 alpha/beta 绑定哪一项互相矛盾，附录G与附录J的表述也矛盾",
    "eq. (4) 文字写 'where α is a regularization term' 但公式用 beta，疑为笔误",
    "MMD 的核数量、带宽、是否有偏估计、每层采样多少表示向量、在哪些维度聚合均未说明",
    "MASK 如何作用到损失上（置零还是取非共享位置）、batch 级交集如何定义未说明",
    "Algorithm 1 第8行的 l_harmful^l 与第12行的 l_ascent^l 是否为同一量未说明",
    "b_harmless 与 b_harmful 是否按同一问题一一配对采样未说明",
    "batch size 是 8（附录B.2）还是 4（附录L）不一致，且 8 是每个数据集各 8 还是合计 8 未说明",
    "附录L 的 '1:52' 时间单位未说明",
    "10% warmup 与 cosine 调度作用范围、是否梯度累积/裁剪、多卡并行方式、每层 logits 是否 detach 均未说明",
    "训练时是否冻结某些层未说明（默认实现为全量更新）",
    "代码与完整复现细节未随论文发布（checklist 第5项答 No）"
  ],
  "quotes": [
    {"supports": "步骤3 激活捕获位置（post-MLP pre-residual）", "text": "For each training step of RepNoise, we perform this across all of the post-MLP but pre-residual activations of each layer. The pre-residual activations were chosen because the representations become similar to the previous layer after adding the residuals"},
    {"supports": "步骤4 逐层 ascent 损失复用 LM head", "text": "For our layer-wise gradient ascent losses, we use a similar approach to the tuned lens [7] and use the language model head on top of each activation to compute language modelling loss at each layer."},
    {"supports": "步骤1 共享 token 掩码的必要性", "text": "We also draw the reader's attention to the MASK operation. This is because we use paired refusal data for our method where the first part of a question or prompt is shared between the harmful and harmless target text."},
    {"supports": "步骤6 噪声项的目标分布 KL(p(Z|X) || N(0,I))", "text": "We can do this by minimizing the KL divergence between the distribution of harmful representations given harmful input token sequences Pθ[t=0](Z | X) and Gaussian noise N(0, I)"},
    {"supports": "步骤6 用多核高斯 MMD 替代 KL", "text": "Because of this, we use multi-kernel Maximum Mean Discrepancy (MMD) with a Gaussian kernel (as in Wang et al. [63]) which estimates a distribution over harmful samples."},
    {"supports": "步骤8 ascent 项取对数", "text": "Finally we mention that in practice ℓascent can be very large and dominate the loss function, this is why we take the log of ℓascent."},
    {"supports": "步骤10 主要超参与规模（1 epoch, 10k 配对样本, α=1, β=0.001）", "text": "For the BeaverTails attack, we train RepNoise for 1 epoch on 10k paired samples (10k harmful questions with harmful answers and 10k of the same questions with safe answers or refusals) using α = 1, β = 0.001"},
    {"supports": "步骤11 必须更新浅层否则防御失效", "text": "Finally, we see that freezing the middle layers starts to degrade the effectiveness of the defence and freezing the first ten layers completely ruins the effectiveness of the defence."}
  ]
}
```
