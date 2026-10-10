# balunovic2022lamp：LAMP: Extracting Text from Gradients with Language Model Priors

## 1. 基本信息

- **场景**：传统联邦学习（federated learning, FL）下的文本分类模型训练，不是联邦大模型微调，也不是参数高效微调（parameter-efficient fine-tuning, PEFT）。论文第 3.1 节给出的联邦优化形式为 FedSGD，第 5 节另外测了 FedAvg。模型是 BERT 量级的编码器（encoder），不是自回归大语言模型（large language model, LLM）。
- **训练阶段**：客户端本地训练产生梯度更新、上传到服务器、服务器聚合这一段的"上传与聚合"环节；攻击发生在服务器侧读取更新的时刻。
- **论文类型**：攻击（隐私重建攻击 / 梯度泄露攻击，gradient leakage attack），发表在 NeurIPS 2022（arXiv:2202.08827v2）。
- **模型与数据规模**：目标模型为 BERT_BASE（12 层、768 隐藏单元、3072 前馈、12 注意力头）、BERT_LARGE（24 层、1024 隐藏单元、4096 前馈、16 注意力头）、TinyBERT_6（6 层、768 隐藏单元、3072 前馈、12 注意力头），均取自 Hugging Face（第 5 节）；论文没有给出参数量数值。数据为三个二分类数据集：CoLA（典型长度 5–9 词）、SST-2（3–13 词）、RottenTomatoes（14–27 词），每个实验评估 100 条序列（第 5 节）。辅助语言模型为预训练 GPT-2，与目标 BERT 使用同一 tokenizer（第 5 节）。

## 2. 威胁模型

- **攻击者是谁**：服务器本身，或攻陷了服务器的第三方。论文第 3.1 节："A gradient leakage attack is an attack executed by the server (or a party which compromised it) that tries to obtain the private data (x∗c, y∗c) of a client using the gradient updates ∇θkL(x∗c, y∗c) sent to the server."
- **占比或数量**：不适用。攻击者是服务器角色，不需要任何恶意客户端；论文未给出被攻陷服务器的比例，也未模拟多客户端场景。
- **能力（能改什么）**：攻击者是诚实但好奇（honest-but-curious）的服务器，按第 3.1 节，它"not allowed to modify the federated training protocol"；论文明确把"服务器向客户端发送恶意更新"这一更强设定（Fowl et al. [6]）排除在外，称其为 orthogonal（附录 A.1）。它能做的是：读取每个客户端上传的、未聚合的梯度更新，并在本地运行任意计算（攻击者的重建优化）。
- **知识（知道什么）**：被攻击模型的架构与参数快照（图 1 与第 3.1 节，攻击以"客户端计算的 ∇θL(x∗, y∗)"和目标网络快照为输入）；真值标签 y*（第 4.2 节假设已知，二分类下可枚举全部标签组合）；序列长度（第 5 节："for simplicity we assume the lengths of sequences are known"）；模型自带的词表与词嵌入矩阵（用于投影与正则，第 4.2、4.3 节）；一个外部预训练语言模型 GPT-2（第 5 节）。论文未说明攻击者是否知道客户端的批大小。
- **目标**：隐私。从梯度更新中重建客户端的私有文本序列（第 1、4 节），属于被动窃密，不涉及无目标破坏、后门或越狱。
- **防御者是谁、能看到什么、信任什么**：论文没有设置主动防御者角色；被评估的"防御"由客户端在上传前对自己的梯度做处理（加高斯噪声、置零部分梯度，第 5 节与附录 C.2）。客户端能看到自己的私有数据与自己的梯度；论文未说明客户端能否看到其他客户端的更新，也未给客户端任何检测能力。客户端信任服务器按协议聚合模型，但服务器可能分析更新内容。论文未评估任何检测型防御，也未讨论安全聚合（secure aggregation）。

## 3. 攻击入口与流程位置

论文的攻击**不注入任何东西**，它是在服务器侧读取已上传更新的被动攻击；它针对的"入口"是客户端上传的梯度更新在服务器侧被读取/被利用的那一刻。逐位置说明：

- **本地数据准备**：不是攻击入口。客户端私有数据 (x*, y*) 是重建目标，不被攻击者篡改。
- **本地训练过程（损失、优化器、步数）**：不是攻击入口。攻击者不能修改客户端的损失或优化器；论文假设协议不被篡改。客户端在此处产生 ∇θkL(x*, y*)，这是攻击者需要的信息载体。
- **更新上传前的后处理（缩放、投影、拼装）**：不是入口，但这是论文评估的防御发生的位置（加噪、裁剪、梯度置零），见第 6 节。
- **服务器聚合**：攻击发生的环节。按第 3.1 节，各客户端更新被送回服务器；攻击者在聚合之前读取单个客户端的原始更新，把它当作"目标梯度"，然后运行算法 1。论文实验中每个被攻击的更新对应一条序列（B=1）或一批序列（B=2、4，表 2），FedAvg 场景下对应客户端 4 步本地更新合并后的那一份上传更新（第 5 节）。
- **全局模型下发**：不是入口，但攻击者需要这一版模型快照 θk 作为已知条件（图 1）。
- **评估与部署**：不是入口，论文不涉及部署阶段的攻击。

**具体操作步骤**（依据图 1、算法 1、第 4 节）：服务器按协议下发 θk；客户端用私有数据算一次（或若干步）梯度并上传；服务器读出该客户端未聚合的更新 ∇θkL(x*, y*)；攻击者从高斯分布采样初始化 dummy 嵌入（ninit 次取重建损失最小者），然后交替执行 nc 步连续优化（对 dummy 嵌入做梯度下降，最小化重建损失，需要二阶导）与 nd 个离散候选变换（用 GPT-2 困惑度筛选）；循环 it 轮后把连续嵌入按余弦相似度投影到最近邻 token，输出重建文本。

## 4. 方法原理

核心思想有两点（摘要、第 4 节）：用辅助语言模型提供"文本先验"，以及交替进行连续优化与离散优化，避免梯度下降卡在局部最优。

1. **连续优化（第 4.2 节，图 1 蓝色部分）**。最小化重建损失 L_rec(x) = L_grad(x) + α_reg·L_reg(x)。其中梯度匹配损失 L_grad 可选两种：TAG 的 L_tag(x) = Σ_{i=1..l} (‖∇θi f(x*, y*) − ∇θi f(x, y)‖₂ + α_tag‖∇θi f(x*, y*) − ∇θi f(x, y)‖₁)，或图像领域提出的余弦损失 L_cos(x) = 1 − (1/l)Σ_{i=1..l} cos(∇θi f(x*, y*), ∇θi f(x, y))。嵌入正则项为 L_reg(x) = ((1/n)Σ_i‖x_i‖₂ − (1/V)Σ_j‖e_j‖₂)²，作用是防止重建嵌入长度不断增大（自注意力以点积为主，优化会忽略长度）。因为 L_rec(x) 依赖网络在 x 处的梯度，需要对 x 求二阶导，论文用 PyTorch 自动微分实现（第 4.2 节）。
2. **离散优化（第 4.3 节，图 1 绿色部分）**。对当前重建做四种随机变换生成候选：Swap（随机交换两个位置的 token）、MoveToken（把第 i 个 token 移到第 j 个位置之后）、MoveSubseq（把 [i, j] 的子序列移到位置 p 之后）、MovePrefix（把前 i 个 token 的前缀移到序列末尾）。用辅助语言模型计算候选的困惑度 L_lm(t) = −(1/n)Σ_{l=0..n−1} log P(t_{l+1} | t_1…t_l)，当且仅当 L_rec(x′) + α_lm·L_lm(t′) < L_rec(x) + α_lm·L_lm(t) 时接受候选（第 4.3 节）。α_lm 控制重建损失与困惑度的权衡：太小则语言模型不起作用，太大则忽略重建损失。
3. **整体流程（第 4.4 节，算法 1）**：先采样 ninit 次高斯初始化并取 L_rec 最小者（论文实际采用两步初始化：500 个高斯样本，再对这 500 个做 500 个随机排列取最优，第 5 节）；随后 it 轮，每轮先做 nc 步连续优化，再做 nd 次离散变换选优；最后按余弦最近邻把嵌入投影到词表 token。

## 5. 检测或防御所需的数据

本文是攻击论文，因此下面列出**攻击者需要拿到并处理的输入**（即防护库若要复现/审计这类攻击必须在信任边界上暴露的数据），以及攻击留下的可观测量。

1. **单个客户端上传的原始梯度更新 ∇θkL(x*, y*)**。是什么：未聚合的单客户端梯度，按层使用（L_tag 与 L_cos 都对层求和）；论文的算法 1 以它为唯一"目标梯度"。在哪里采集：服务器收到更新时（客户端上传之后、聚合之前）。粒度：逐客户端、整模型参数集（按层分组）。跨轮历史：不需要，每次攻击只消费一份更新。干净参考数据：不需要。额外前向/反向：攻击者需要在本地对 dummy 输入做大量前向+反向，且要算二阶导；但训练流程本身不需要额外计算。
2. **产生该更新的全局模型快照 θk（含词嵌入矩阵 W_embed 与位置嵌入矩阵 W_pos）**。是什么：攻击对象网络的完整参数（图 1 的第一项输入）。在哪里采集：服务器聚合后的全局模型（分发前的那一版，对应服务器端钩子）。粒度：逐轮、整模型。跨轮历史：分析：攻击在收到更新的同一轮即可执行，只需与该更新对应的那一版快照；论文未说明是否需要保存多轮历史快照。干净参考数据：不需要。额外计算：不需要，直接读取。词嵌入矩阵还额外用于两件事：把连续嵌入投影到最近邻 token（第 4.3、4.4 节），以及计算 L_reg 中的平均嵌入长度（第 4.2 节）。
3. **真值标签 y\***。是什么：被重建序列的类别标签。在哪里采集：论文不是从流程中采集，而是在第 4.2 节直接假设攻击者已知（二分类下可通过枚举标签组合处理）。粒度：逐样本。跨轮历史、干净参考数据、额外前向反向：均不需要；分析：枚举全部标签会成倍增加攻击的优化次数。
4. **辅助语言模型 GPT-2 对候选序列的逐 token 负对数似然（困惑度）**。是什么：外部预训练语言模型给出的文本自然度打分；第 5 节说明使用的是 Guo et al. [10] 提供的、与目标 BERT 同 tokenizer 的预训练 GPT-2。在哪里采集：攻击者本地（不属于联邦训练流程的任何阶段，也不来自客户端数据）。粒度：逐候选序列、逐样本。跨轮历史：不需要。干净参考数据：不需要（GPT-2 是公开预训练模型，不是干净根数据集）。额外计算：需要，每个离散候选都要一次 GPT-2 前向。
5. **被攻击序列的长度 n**。是什么：重建序列的 token 数；第 5 节为简化假设长度已知，否则攻击者可以对所有可能长度跑一遍。粒度：逐样本。其余各项均不需要。

**攻击会在哪些可观测量上留下痕迹**：按论文描述，LAMP 是完全被动的读取型攻击，不修改上传的更新、不修改训练协议，因此不会在更新的数值里引入可被归因于攻击者的异常（分析：这意味着基于"更新分布异常"的检测对它没有直接抓手；但论文本身没有讨论检测）。论文报告的是它在若干防护下仍然有效：高斯噪声 σ ≤ 0.01（表 5）、梯度置零到 99%（表 8）、已微调模型（表 1 的 BERTBASE-FT 列）、批大小 2 与 4（表 2）、FedAvg 4 步小学习率（第 5 节）；另外附录 A.1 指出，如果词嵌入或位置嵌入可训练、或 transformer 块含偏置，攻击者可以更简单地直接读出客户端序列，LAMP 主动放弃了这些更容易的通道。论文未评估任何检测机制或安全聚合。

## 6. 干预动作

本文不提出防御，因此这里记录的是**论文评估过的干预动作**，它们全部发生在客户端、在上传梯度之前：

- **对梯度加高斯噪声**（第 5 节、表 5）。论文指出"with additional clipping this would correspond to DP-SGD [1]"。服务器侧不做任何动作。
- **对梯度做掩码（把一定百分比的梯度元素置零）**（附录 C.2、表 8）。
- 论文还把**增大批大小**（表 2）和**先微调模型**（表 1）当作降低重建质量的条件来评估，但没有把它们作为防御机制提出。
- 论文没有讨论服务器端的剔除客户端、重新加权、裁剪、样本过滤、模型修复或回滚；在它的威胁模型里服务器就是攻击者，所以这些动作没有位置。论文也没有检测环节，因而没有"检测后动作"。

## 7. 实验设置与主要结果

- **模型**：BERT_BASE、BERT_LARGE、TinyBERT_6（配置见第 1 节），以及在各任务上微调 2 个 epoch 后的 BERTBASE-FT（第 5 节）。
- **数据集**：CoLA、SST-2、RottenTomatoes，均为二分类；附录 A.1 说明选择二分类是为了避免自监督语言建模任务中"同一数据既作输入又作输出"带来的额外泄漏通道。
- **联邦相关设置**：论文没有模拟多客户端联邦训练，未给出客户端数 C、参与率、联邦轮次或恶意客户端比例（第 3.1 节只保留符号 C）。每个实验攻击的是单个客户端的一条或一批序列的更新。数据是否非独立同分布：论文未说明。
- **攻击超参**（第 5 节、附录 D）：BERT_BASE 与 TinyBERT_6 用 it=30、nc=75、nd=200，连续优化总步数上限 2000；BERT_LARGE 用 it=25、nc=200，共 5000 步；DLG 与 TAG 在 BERT_LARGE 上跑 10000 步、其他模型 2500 步。LAMP_Cos 超参 α_lm=0.2、α_reg=1.0、λ=0.01、γ=0.89；LAMP_L2+L1 超参 α_tag=0.01、α_lm=60、α_reg=25、λ=0.01、γ=0.89；TAG 用 α_tag=0.01、λ=0.1、γ=1.0。BERT_LARGE 上 λ 分别为 DLG 0.1、TAG/LAMP 0.01，梯度幅度裁剪到 1.0（DLG、TAG）或 0.5（LAMP）。
- **指标**：ROUGE-1、ROUGE-2、ROUGE-L（跟随 TAG [3]，第 5 节），防御场景下用 MCC 衡量模型效用。
- **关键结果**：
  - 批大小 1（表 1）：CoLA + BERT_BASE 上 LAMP_Cos 为 R-1 89.6、R-2 51.9、R-L 76.2，而 TAG 为 78.9/10.2/53.3、DLG 为 59.3/7.7/46.2；SST-2 上 LAMP_Cos 为 88.8/56.9/77.7；RottenTomatoes 上 LAMP_Cos 为 64.7/16.3/43.1。TinyBERT_6 在 CoLA 上 LAMP_Cos 达到 93.9/59.3/80.2，BERT_LARGE 为 92.0/56.0/78.8。正文总结为 ROUGE-2 在 CoLA 上提升 5 倍、在 BERT_BASE 上 ROUGE-L 平均重建更长子序列最多 23%。
  - 已微调模型（表 1）：BERTBASE-FT 上 LAMP_Cos 仍有 85.8/46.2/73.1（CoLA）、87.6/54.1/76.1（SST-2），论文称"only slightly worse in reconstruction compared to BERTBASE, which is surprising given the prior image domain results"。
  - 批大小大于 1（表 2）：CoLA 上 LAMP_Cos 从 B=1 的 89.6/51.9/76.2 降到 B=2 的 74.4/29.5/61.9 和 B=4 的 55.2/14.5/48.0；LAMP_L2+L1 在 B=4 时为 66.2/21.8/55.2；SST-2 上 LAMP_L2+L1 在 B=2 为 82.5/45.8/70.8。论文称自己是首个在文本模型上重建批大小大于 1 输入的工作。
  - 加噪防御（表 5，CoLA + BERT_BASE）：σ=0.001/0.002/0.005/0.01 对应 MCC 0.551/0.526/0.464/0.364（无防御为 0.557）；LAMP_Cos 的 R-1 从 81.2 降到 27.7，LAMP_L2+L1 从 79.2 到 69.6，论文称"most text is still recoverable for the chosen noise levels"，并说明未测试大于 0.01 的噪声。
  - 梯度掩码（表 8，附录 C.2）：置零 75%/90%/95%/99% 时 MCC 为 0.557/0.534/0.515/0.371，LAMP_Cos 的 R-1 为 79.4/61.9/39.0/24.7。
  - FedAvg（第 5 节）：4 步本地更新、每步 B=1、lr=5e-5，CoLA + BERT_BASE 上 LAMP_L2+L1 得到 R-1/R-2/R-L 为 66.5/21.0/55.1，与 FedSGD B=4 的结果相当（表 2 中 LAMP_L2+L1 B=4 为 66.2/21.8/55.2）。
  - 随机性（第 5 节、附录 C.1）：CoLA + BERT_BASE 上 10 个随机种子得到 88.2 ± 1.02、50.0 ± 2.37、75.0 ± 1.21；换 10 组不同句子的结果见附录表 7（LAMP_Cos 为 87.8 ± 2.6、48.4 ± 5.5、74.6 ± 2.9）。
  - 消融（表 4，CoLA + BERT_BASE + B=1）：去掉语言模型（α_lm=0）时 R-2 只有 26.6，去掉嵌入正则（α_reg=0）时 R-2 为 38.0，把离散优化放到最后（DiscreteAtEnd）为 28.6，完全不做离散变换为 29.6，对比完整 LAMP_Cos 的 51.9。
  - 一句需要留意的表述不一致：第 5 节写的是"100 random sequences from the respective training sets"，而附录 C.1 写的是"the same 100 sequences randomly chosen from the test portion of the datasets"以及"from the COLA test set"；附录 D 又说超参调优用的是训练集序列（并移除了那 100 条测试序列）。论文前后不一致。

## 8. 开销

- **攻击端计算开销**（附录 E）：表 1 的 BERT_LARGE 实验最贵，LAMP_Cos 与 LAMP_L2+L1 每次实验约 50 小时，TAG 约 70 小时；其余网络在 B=1 时每次实验 8 到 16 小时，LAMP 因离散优化最多慢 2 倍；B=4 的实验每次 8 到 36 小时，LAMP 最多慢 4 倍。硬件为单张 NVIDIA RTX 2080 Ti（11 GB 显存），BERT_LARGE 用单张 RTX 3090 Ti（24 GB）（附录 D）。Checklist 第 3(d) 项称总算力已在附录 E 报告。
- **超参搜索开销**（附录 D）：CoLA 上先对 50 组超参在 10 条序列上评估，再取最好的 10 组在另外 20 条序列上评估，RottenTomatoes 沿用这 10 组。
- **通信开销**：论文未报告（分析：该攻击是被动读取，不改变联邦协议，因此不引入额外通信）。
- **存储开销**：论文未报告。
- **客户端防御开销**：论文未报告（加噪与置零带来的额外计算/显存没有量化）。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文明确写出或由实验设置隐含）**：

- 服务器诚实但好奇，不篡改联邦训练协议（第 3.1 节、附录 A.1）。
- 攻击者能拿到每个客户端未聚合的原始梯度更新（第 3.1 节的攻击定义与公式）；论文未讨论安全聚合。
- 攻击者持有产生该更新的模型快照，并能对它做任意前向与反向计算（图 1、第 4.2 节）。
- 攻击者已知真值标签 y*，且任务为二分类从而可以枚举标签（第 4.2 节）；已知序列长度（第 5 节）。
- 目标模型是 BERT 类编码器加 tanh 分类头（第 3.2 节），并且词嵌入不训练、位置嵌入不训练、transformer 块不含偏置（附录 A.1）；论文还说明这些限制会带来少量精度损失，但换来了更好的隐私。
- 每次上传的更新只覆盖很少的样本：实验中批大小为 1、2、4（表 2）；FedAvg 场景只覆盖 4 步、每步 B=1、学习率 5e-5（第 5 节）。
- 攻击者能获得与目标模型同 tokenizer 的辅助语言模型（第 5 节的 GPT-2）。

**论文自述的局限**：不处理标签重建，留作未来工作（第 4.2 节、Checklist 第 1(b) 项）；为简化假设序列长度已知（第 5 节）；长序列的 RottenTomatoes 仍然难以重建得好（第 5 节）；两种梯度损失没有普适更优者，效果依赖数据集（第 4.2 节）；BERT_LARGE 参数量大导致优化更难、需要更多步（第 5 节）；附录 C.3 承认两步初始化并非在所有指标上严格更好；附录 A.1 明确把恶意服务器设定排除在本工作之外。

**是否评估自适应攻击者**：没有。论文是攻击方，其防御实验（加噪、掩码）使用的是固定防御与固定超参的攻击，没有让防御者或攻击者针对对方调整。论文未评估自适应攻击者，也未评估检测型防御。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**：

- 分析：LAMP 需要"产生该更新的模型快照 + 单客户端上传的更新"。联邦 LoRA 的服务器本来就持有基座模型与各客户端的适配器增量，这一条通常仍然满足；但论文的全部实验都在全参数微调的 BERT 上完成，梯度覆盖所有层与所有头，而 LoRA 只上传低秩矩阵 A、B 的梯度，参数量与梯度张量小几个数量级，论文没有在这种参数化下做过任何实验，低秩梯度是否仍保留足够重建信号属于论文未说明的范围。
- 分析：LoRA 天然冻结词嵌入与位置嵌入，这正好落在论文附录 A.1 所选的"更难"设定里；论文把可训练词嵌入/位置嵌入/偏置当作更容易的泄漏通道并主动关闭，因此它的结论不能反过来证明"LoRA 只训练 A、B 时也安全"，也不能说明 LoRA 场景下泄漏是更多还是更少。
- 分析：论文的二分类与已知标签假设在生成式指令微调上不成立，论文明确把标签重建留作未来工作；把它直接套到 next-token 预测式微调需要额外的标签恢复步骤，论文未提供。
- 分析：论文只测到批大小 4（表 2）和 FedAvg 4 步小学习率（第 5 节），且随批大小增大重建质量明显下降（CoLA 上 LAMP_Cos 的 R-2 从 51.9 降到 14.5）；真实的联邦 LoRA 微调中一个客户端往往在更多样本、更多本地步上累积后再上传，论文没有覆盖这种规模。
- 分析：论文最长的数据集只有 14–27 词（RottenTomatoes，R-2 仅 16.3），而大模型微调数据通常是数百到数千 token 的长文本；序列长度对重建成功率的影响论文只到这一档为止。
- 分析：论文的单次攻击在 BERT_LARGE 上就要约 50 小时（附录 E），成本随模型规模、序列长度、批大小增长；在更大的基座模型上是否可行，论文未说明。

## 10. 对防护库设计的含义

分析：以下六条均为我的推断，不是论文内容。

1. 分析：最关键的采集点是"服务器收到更新时"的服务器钩子，必须能按客户端分别保留**未聚合的原始更新**及与之绑定的元数据（轮次、该轮全局模型版本、客户端本地步数、批大小）；缺少"单客户端、未混合"这一视图，LAMP 类攻击就无法复现或审计。这是通用需求，任何梯度泄露审计都需要它。
2. 分析：库需要**版本化的全局模型快照**，至少能取回产生某份更新的那一版参数（含词嵌入矩阵与词表）；插件的重计算必须在模型副本上进行，不能污染正在训练的模型状态与随机数流。这是通用需求，但"按更新回指模型版本"的绑定关系是这类逐更新审计特有的。
3. 分析：这篇论文特有的接口要求远高于常见的"只读范数/相似度"视图——反演审计插件需要对任意客户端更新做**任意次数的前向与反向计算，并且需要二阶导**（第 4.2 节），因此插件沙箱必须允许在隔离副本上运行优化循环，并允许声明 GPU 时间预算。
4. 分析：论文特有的一个数据依赖是**外部辅助语言模型**（GPT-2）与其 tokenizer 的接入点（第 4.3、5 节）。库的插件清单应允许声明这类"外部先验模型"，并在日志中明确标注它不属于联邦流程、不来自任何客户端，避免审计链被误判为使用了根数据集。
5. 分析：这篇论文评估的干预全部在**客户端上传之前**（加高斯噪声、裁剪、梯度元素置零），因此库需要客户端侧的更新后处理钩子，并需要把"噪声水平/掩码比例"与"模型效用指标"（论文用 MCC，表 5、表 8）放在同一份记录里，才能做隐私—效用权衡；只在服务器端做过滤无法覆盖论文的干预位置。
6. 分析：LAMP 不修改任何数据或更新，因此库不应指望"检测到攻击者"。可行的设计是把风险前移到"限制服务器可见的信息"：不长期留存单客户端原始更新、按表 2 与 FedAvg 实验的结论记录批大小与本地步数（它们直接影响可重建性），并把这些采集点上的原始数据默认视为最高敏感级别（库自身如果集中保存了这些更新，就变成了新的攻击面）。

## 11. 原文依据

1. 第 1 节（Introduction）——支撑第 1 节论文类型与第 2 节攻击目标（从梯度重建私有文本的隐私攻击）：
   "In this work, we propose LAMP, a new reconstruction attack which leverages language model priors to extract private text from gradients."
2. 第 3.1 节（Federated Learning）——支撑第 2 节攻击者身份与第 3 节攻击入口（服务器读取单客户端上传的梯度更新）：
   "A gradient leakage attack is an attack executed by the server (or a party which compromised it) that tries to obtain the private data (x∗c, y∗c) of a client using the gradient updates ∇θkL(x∗c, y∗c) sent to the server."
3. 第 3.1 节（Federated Learning）——支撑第 2 节攻击者能力边界（诚实但好奇、不改协议）与第 9 节假设：
   "Gradient leakage attacks usually assume honest-but-curious servers which are not allowed to modify the federated training protocol outlined above."
4. 第 4.2 节（Continuous Optimization）——支撑第 2 节与第 9 节的标签已知假设（引文中的 "y∗of" 是 PDF 抽取时丢失空格的原样文本）：
   "we assume knowledge of the ground truth label y∗of the client token sequence we aim to reconstruct, meaning y = y∗. This assumption is not a significant restriction as we mainly focus on binary classification"
5. 第 4.2 节（Continuous Optimization）——支撑第 4 节方法原理与第 5、8 节的额外计算需求（二阶导、PyTorch 自动微分）：
   "To this end, a second-order derivative needs to be computed, as Lrec(x) depends on the network gradient at x. Similar to prior work [3, 43], we achieve this using automatic differentiation in Pytorch [27]."
6. 第 4.3 节（Discrete Optimization）——支撑第 4 节离散优化的接受准则（重建损失与困惑度加权组合）：
   "We accept the new reconstruction x′ if it improves the combination of the reconstruction loss and perplexity:"
7. 第 5 节（Experimental Evaluation）——支撑第 7 节"首个在批大小大于 1 的文本模型上重建"的结果（上文紧接 "(see experiments on CoLA and SST-2)"）：
   "To the best of our knowledge, we are the first to show this, suggesting that gradient leakage can be a realistic security threat in practice."
8. 第 5 节（Experimental Evaluation）——支撑第 6 节论文评估的干预动作（客户端梯度加高斯噪声，配合裁剪即 DP-SGD）：
   "we now consider the defense of adding Gaussian noise to gradients (with additional clipping this would correspond to DP-SGD [1])"
9. 附录 A.1（Threat Model Discussion）——支撑第 9 节"词嵌入不可训练"这一假设及其后果（上文即 "The model’s word embeddings are not fine-tuned."）：
   "As the gradients of the word embedding vectors are non-zero for words that are contained in the client’s training data and zero otherwise, revealing the gradients to the server will allow it to easily obtain the client sequence"
10. 附录 E（Total Runtime of the Experiments）——支撑第 8 节攻击端计算开销（BERT_LARGE 上每次实验 50 小时，TAG 70 小时）：
    "They took between 50 hours per experiment for the LAMPCos and LAMPL2+L1 methods and 70 hours for TAG, which executes two times more continuous optimization steps."

```json
{
  "key": "balunovic2022lamp",
  "title": "LAMP: Extracting Text from Gradients with Language Model Priors",
  "year": 2022,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_server"],
  "attack_goal": ["privacy"],
  "attack_entry": ["server_aggregation"],
  "observables": [
    {
      "what": "客户端上传的未聚合逐层梯度更新 ∇θkL(x*,y*)；FedSGD 单步更新，或 FedAvg 少量本地步合并后的更新",
      "where": "server_receive",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "产生该更新的全局模型快照 θk，含词嵌入矩阵 W_embed 与位置嵌入矩阵 W_pos（用于最近邻 token 投影与嵌入长度正则）",
      "where": "server_post_aggregate",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "被重建样本的真值标签 y*（第4.2节假设攻击者已知，二分类下可枚举）",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "辅助语言模型 GPT-2 对候选 token 序列的逐 token 负对数似然（困惑度），属于攻击者本地使用的外部预训练先验",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["add_noise", "clip"],
  "intervention_where": ["client"],
  "assumptions": [
    "服务器诚实但好奇，不篡改联邦训练协议",
    "服务器能看到每个客户端未聚合的原始梯度更新（论文未讨论安全聚合）",
    "攻击者持有产生该更新的模型快照，并可对其自由做前向与反向计算",
    "攻击者已知真值标签（二分类可枚举）与序列长度",
    "目标模型为 BERT 类编码器加二分类头，词嵌入、位置嵌入与偏置均不可训练",
    "单次更新的样本数很小（实验 B 不超过 4），FedAvg 场景仅 4 步本地更新且学习率为 5e-5",
    "攻击者可获得与目标模型同 tokenizer 的辅助语言模型 GPT-2",
    "重建目标是单条短文本序列（最长数据集典型 14 到 27 词），而非长文档或生成式指令数据"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {
      "section": "1 Introduction",
      "supports": "第1节：论文类型为攻击，目标是利用语言模型先验从梯度中重建私有文本",
      "text": "In this work, we propose LAMP, a new reconstruction attack which leverages language model priors to extract private text from gradients."
    },
    {
      "section": "3.1 Federated Learning",
      "supports": "第2节与第3节：攻击者是服务器或其攻陷方，攻击入口是服务器读取客户端上传的梯度更新",
      "text": "A gradient leakage attack is an attack executed by the server (or a party which compromised it) that tries to obtain the private data (x∗c, y∗c) of a client using the gradient updates ∇θkL(x∗c, y∗c) sent to the server."
    },
    {
      "section": "3.1 Federated Learning",
      "supports": "第2节与第9节：攻击者能力边界为诚实但好奇，不允许修改联邦训练协议",
      "text": "Gradient leakage attacks usually assume honest-but-curious servers which are not allowed to modify the federated training protocol outlined above."
    },
    {
      "section": "4.2 Continuous Optimization",
      "supports": "第2节与第9节：攻击者已知真值标签 y*，且任务限定为二分类以便枚举标签",
      "text": "we assume knowledge of the ground truth label y∗of the client token sequence we aim to reconstruct, meaning y = y∗. This assumption is not a significant restriction as we mainly focus on binary classification"
    },
    {
      "section": "4.2 Continuous Optimization",
      "supports": "第4节与第5节、第8节：重建损失依赖网络在输入处的梯度，需要二阶导与自动微分，构成额外计算",
      "text": "To this end, a second-order derivative needs to be computed, as Lrec(x) depends on the network gradient at x. Similar to prior work [3, 43], we achieve this using automatic differentiation in Pytorch [27]."
    },
    {
      "section": "4.3 Discrete Optimization",
      "supports": "第4节：离散候选的接受准则为重建损失与语言模型困惑度的加权和下降",
      "text": "We accept the new reconstruction x′ if it improves the combination of the reconstruction loss and perplexity:"
    },
    {
      "section": "5 Experimental Evaluation",
      "supports": "第7节：论文声称自己是首个在批大小大于 1 的文本模型更新上成功重建的工作",
      "text": "To the best of our knowledge, we are the first to show this, suggesting that gradient leakage can be a realistic security threat in practice."
    },
    {
      "section": "5 Experimental Evaluation",
      "supports": "第6节：论文评估的干预是客户端上传前给梯度加高斯噪声，配合裁剪等价于 DP-SGD",
      "text": "we now consider the defense of adding Gaussian noise to gradients (with additional clipping this would correspond to DP-SGD [1])"
    },
    {
      "section": "Appendix A.1 Threat Model Discussion",
      "supports": "第9节：论文假设词嵌入不可训练，因为可训练词嵌入的梯度会直接暴露客户端 token 集合",
      "text": "As the gradients of the word embedding vectors are non-zero for words that are contained in the client’s training data and zero otherwise, revealing the gradients to the server will allow it to easily obtain the client sequence"
    },
    {
      "section": "Appendix E Total Runtime of the Experiments",
      "supports": "第8节：攻击端计算开销，BERT_LARGE 上每次实验约 50 小时，TAG 约 70 小时",
      "text": "They took between 50 hours per experiment for the LAMPCos and LAMPL2+L1 methods and 70 hours for TAG, which executes two times more continuous optimization steps."
    }
  ]
}
```
