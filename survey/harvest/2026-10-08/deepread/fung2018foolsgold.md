# fung2018foolsgold：Mitigating Sybils in Federated Learning Poisoning

## 1. 基本信息

- 场景：传统联邦学习（classic federated learning）。论文明确假设"标准联邦学习情境"，数据分布在多个数据持有方之间且不能共享（第 2 节）。论文不涉及大语言模型（large language model, LLM），也不涉及参数高效微调（parameter-efficient fine-tuning, PEFT）或 LoRA（low-rank adaptation）。
- 训练阶段：联邦训练的同步更新轮次（synchronous update rounds），客户端本地执行随机梯度下降（stochastic gradient descent, SGD）并上传更新，服务器聚合；论文同时覆盖 FEDSGD 与 FEDAVG 两种形式（第 2 节、第 6.2 节）。
- 论文类型：防御（defense），其中包含检测（detection）与缓解（mitigation）；论文同时自行构造并评估了攻击，因此也包含攻击评估的成分（第 1 节、第 6.1 节、附录 B）。
- 模型与数据规模：四个数据集与三类模型（表 2）。MNIST 训练集 60,000 条、10 类、784 维特征，用单层 softmax；VGGFace2 训练集 7,380 条、10 类、150,528 维特征，用 SqueezeNet1.1（727,000 个参数）与 VGGNet11（1.28 亿个参数）；KDDCup 训练集 494,020 条、23 类、41 维特征，用单层 softmax；Amazon 训练集 1,500 条、50 类、10,000 维特征，用单层 softmax。
- 客户端规模：诚实客户端数为 MNIST 与 VGGFace2 各 10 个、KDDCup 23 个、Amazon 50 个（第 6 节）。原型实现为 600 行 Python，其中 FoolsGold 约 150 行（第 6 节）。
- 版本信息：正文首页标注 arXiv:1808.04866v5 [cs.LG]，日期为 2020 年 7 月 15 日；论文键名沿用 2018 年首次发布年份。

## 2. 威胁模型

**攻击者。** 攻击者是恶意的联邦学习客户端，通过女巫（sybil）身份放大影响力，即"攻击者通过以多个合谋别名加入系统来获得影响力"（第 2 节）。论文假设如果系统存在第三方账号验证流程，攻击者有办法绕过它，"either by creating malicious accounts or by compromising honest clients/accounts"（第 3 节）。攻击者数量在实验中由攻击场景定义（表 3）：A-1 为 1 个恶意客户端，A-5 为 5 个，A-5x5 为 5 组各 5 个并发攻击，KDDCup 的 A-OnOne 为 5 个客户端针对同一目标类，A-99 为 990 个女巫攻击 10 个诚实客户端（第 6.1 节）。论文不限定攻击者占比，并明确"we assume that attackers can spawn a large number of sybils"（第 4 节）。

**攻击者能力。** 女巫"observe global model state and send any arbitrary gradient contribution to aggregator at any iteration"，并且可以"collude by sharing state among themselves and by sending updates in an intelligent, coordinated fashion"（第 3 节）。多个互不合谋的攻击者集合可以同时发动投毒。攻击者只能通过联邦学习 API 访问和影响训练状态，且"cannot observe the training data of other honest clients"，但可以通过观察模型状态的总变化看到所有客户端的总平均梯度，看不到任何单个诚实客户端的梯度（第 3 节）。论文指出对手的 SGD 更新取值范围无界，但明确"we do not consider these attacks"，理由是已有基于幅度的检测方法（第 3 节）。对自适应攻击者，论文额外赋予其本地计算女巫之间成对余弦相似度并据此决定是否发送投毒更新的能力（第 6.4 节，算法 2）。

**攻击者知识。** 默认威胁模型只假设攻击者能观察全局模型状态（第 3 节）。论文未说明默认设定下攻击者是否知道防御算法的存在，但在第 6.4 节单独研究了"攻击者知道 FoolsGold"的情形。论文指出，在没有诚实客户端数量与其训练数据知识时，攻击者不知道成功投毒所需的确切女巫数量（第 6.4 节）。

**攻击目标。** 定向投毒（targeted poisoning），即"increase the probability of one class being classified as a different, incorrect class without influencing the output probabilities of any other class"（第 3 节）。两种具体策略是标签翻转（label flipping），把某一类的诚实样本标签翻成目标类而保持特征不变，以及后门（backdoor），在原始数据中加入秘密模式并重新标注（第 2 节、第 3 节）。论文不涉及隐私窃取、越狱或安全对齐破坏。

**防御者。** 防御者是聚合服务器，论文假设"the aggregator is uncompromised and is not malicious"（第 3 节）。服务器只能看到客户端上传的模型参数（第 1 节），没有验证数据集（第 4 节挑战一），不使用学习过程之外的辅助信息（第 5 节）。服务器信任的前提是：存在一定数量的诚实客户端，且"every class defined by the model is represented in the data of at least one honest client"（第 3 节）；以及不使用安全聚合（secure aggregation）一类的混淆，"the central server is able to observe any individual client's model update at each iteration"（第 3 节）。

## 3. 攻击入口与流程位置

论文中攻击的进入位置有三处，均发生在客户端一侧，服务器聚合环节不是攻击入口。

第一，本地数据准备。标签翻转攻击把某一类诚实样本的标签翻成目标类而保留特征（第 2 节）；后门攻击在原始训练数据中加入秘密模式并重新标注，例如"a random subset of the MNIST training data is marked with a white pixel in the bottom-right corner of the image, and labelled as a 7"（附录 B）。在 KDDCup 上，论文假设攻击者把占比约 2% 的恶意流量模式误标为占比约 20% 的"Normal"类（第 6.1 节）。

第二，本地训练过程。女巫在本地用投毒数据执行 SGD，每个客户端"only sends updates for a subset of its data through SGD, meaning that their updates are not identical"（第 6.1 节）。附录 B 还评估了攻击者修改本地批大小（batch size）的策略。

第三，更新上传前的后处理。女巫可以在上传前扰动更新：一对女巫发送 v1 = a1 + ζ 与 v2 = a2 − ζ，使二者之和不变但余弦相似度降低（第 6.4 节）。算法 2 描述的自适应攻击则是在上传前判断女巫之间的历史余弦相似度是否超过阈值 M，超过则发送智能噪声向量 ζ，否则发送真实投毒更新，从而"rate limit"投毒更新的发送频率（第 6.4 节）。

论文没有把攻击放在服务器聚合、全局模型下发或评估部署环节；相反，服务器被假设为不可攻陷（第 3 节）。

## 4. 方法原理

核心思想是：诚实客户端的更新方向彼此分散，而女巫共享同一投毒目标，其更新在期望意义上更相似（第 5 节）。因此可以根据客户端更新之间的相似度自适应地调整每个客户端的聚合权重，而不必假定攻击者数量。

关键步骤（第 5 节，算法 1）：

1. 历史累积。对每个客户端 i，把第 1 到第 T 轮的更新累加为历史向量 H_i = Σ_t Δ_i,t（算法 1 第 3 行）。跨轮历史用于平滑单轮 SGD 的随机性。
2. 指示性特征（indicative features）。只对模型输出层参数对应的那部分特征做相似度比较，权重由全局模型输出层参数的幅度决定，并在所有类别间归一化；可以采用硬过滤或软加权（第 5 节"Feature importance"）。对深层网络，论文只取最终输出层的梯度，例如 VGGNet 的全连接层与 SqueezeNet 的 10 个 1×1 卷积核（第 6 节）；论文明确不考虑非输出层的参数幅度，并把它列为未来工作。
3. 成对余弦相似度（cosine similarity）。对任意两个客户端计算 H_i 与 H_j 在指示性特征上的加权余弦相似度 cs_ij，并取每个客户端的最大成对相似度 v_i = max_j cs_ij（算法 1 第 6 至 8 行）。论文选择余弦相似度而不是欧氏距离，理由是女巫可以操纵梯度的幅度制造差异，但改变方向会削弱攻击效果（第 5 节）。
4. 宽恕机制（pardoning）。若 v_j 大于 v_i，则把 cs_ij 乘以 v_i 与 v_j 的比值（算法 1 第 12 至 14 行），以避免因为攻击目标类数据恰好落在某个诚实客户端而对该诚实客户端造成假阳性。
5. 学习率反转与重标定。α_i = 1 − max_j cs_ij，再除以所有 α 的最大值，使最大权重为 1，从而保证系统中至少有一个客户端不受惩罚（算法 1 第 16 至 18 行）。
6. 对数几率（logit）函数。α_i 再经过以 0.5 为中心的 logit 变换并乘以置信参数 κ，超出 0 到 1 范围的值被截断到边界（算法 1 第 19 行）。其作用是拉开接近 0 与接近 1 的两端，防止攻击者通过堆叠大量女巫获得非零的残余影响。
7. 聚合。w_{t+1} = w_t + Σ_i α_i Δ_i,t（算法 1 第 20 至 21 行）。

收敛性方面，附录 A 给出定理：在算法 1 下参与者（恶意与诚实）的收敛速率为 O(1/T²)，条件是恶意客户端的学习率趋于 0，而诚实客户端的学习率趋于 1。两个条件分别由 β_m ≥ 1 − e^(−0.5κ)/(1 + e^(−0.5κ)) 与 β_g ≤ 1 − e^(0.5κ)/(1 + e^(0.5κ)) 界定，二者都是置信参数 κ 的函数（附录 A）。论文指出 FoolsGold 类似于重要性采样（importance sampling）与自适应学习率方法（第 5 节）。

## 5. 检测或防御所需的数据

**输入一：每个客户端每一轮的模型更新向量。** 内容是客户端本地 SGD（FEDSGD）或本地多步 SGD（FEDAVG）计算出的完整模型更新或梯度；采集位置是服务器收到更新时；粒度是逐客户端、逐轮；需要跨轮累积，因为 FoolsGold 维护每个客户端的历史向量 H_i；不需要干净参考数据；服务器侧不需要额外的前向或反向传播，但需要额外的服务器计算来算成对余弦相似度；不需要其他客户端的训练数据，但需要其他客户端的更新向量以做两两比较。这一输入成立的前提是服务器能看见单条客户端更新，即不使用安全聚合（第 3 节）。

**输入二：指示性特征的权重。** 内容是由全局模型输出层参数幅度导出的特征重要度，并跨类别归一化；采集位置是服务器聚合后的全局模型；粒度是逐层（输出层）、逐轮；不需要跨轮历史；不需要干净参考数据；需要额外的服务器计算来提取参数幅度并归一化，但不需要前向或反向计算；不需要其他客户端的数据（第 5 节"Feature importance"）。

**输入三：客户端身份在轮次之间的对应关系。** FoolsGold 需要把同一客户端在不同轮次的更新累加进同一条历史，因此需要跨轮稳定的客户端标识；论文没有说明服务器如何维护这种身份对应关系（论文未说明具体机制）。

**输入四：评估用测试集。** 方法本身不使用验证集，论文明确说"we assume that FoolsGold, the system we design, does not possess a validation dataset"（第 4 节）。但论文的实验用测试集计算攻击率与准确率：MNIST 有 10,000 条测试样本，VGGFace2、KDDCup 与 Amazon 随机取 30% 作为测试数据（第 6 节）。

**攻击留下的可观测量。** 论文主张女巫在指示性特征上的历史更新方向高度相似，诚实客户端则因各自数据分布不同而分散（第 5 节、图 6）。图 6 用 SqueezeNet 最终分类层的历史梯度可视化：非独立同分布（non-IID）时 10 个诚实客户端各行差异很大而 5 个女巫各行高度相似；即使在完全独立同分布（IID）情形下，"the stochasticity of SGD introduces variance between honest clients, and the sybil gradients are still uniquely distinct as a result of their poisoned data"（第 6.3 节）。此外，智能噪声攻击会在非指示性特征上制造差异，因此只在指示性特征子空间上观察相似度可以消除这一痕迹（第 6.4 节、图 8）。

**论文声称能绕过的检测。** 论文没有声称 FoolsGold 能绕过检测，而是反过来说明 FoolsGold 自身不被以下攻击绕过：操纵恶意数据分布（图 7）、把投毒数据与诚实数据混合（附录 B、图 16）、改变批大小（附录 B、图 17，唯一例外见第 7 节）。论文同时声称现有的 Multi-Krum 与 RONI 在非独立同分布联邦学习中效果不足（第 6.2 节、附录 B）。

## 6. 干预动作

FoolsGold 的动作是重新加权（reweight），不剔除客户端、不裁剪梯度、不加噪、不过滤样本、不修复或回滚模型。服务器在聚合时为每个客户端计算一个 0 到 1 之间的自适应学习率 α_i，并用它缩放该客户端的更新后再求和，即 w_{t+1} = w_t + Σ_i α_i Δ_i,t（第 5 节、算法 1 第 20 至 21 行）。动作发生在服务器聚合阶段。当 α_i 被压到 0 时，效果上等同于忽略该客户端的贡献，附录 A 的条件一正是把恶意客户端的权重写成 h(i,t) 趋于 0。经过 logit 变换后超出 0 到 1 范围的值会被截断到边界，这是对权重本身的截断，不是对梯度做裁剪（第 5 节）。论文另外说明 FoolsGold 可与 Multi-Krum 组合使用，其中 Multi-Krum 会移除距离最大的若干更新（第 5 节、第 7 节、图 12），但该剔除动作属于前人方法而非 FoolsGold 本身。

## 7. 实验设置与主要结果

**设置。** 四个数据集与模型见表 2（第 6 节）。诚实客户端数为 MNIST 与 VGGFace2 各 10、KDDCup 23、Amazon 50；划分数据时"each class is always completely represented by a single client"，即按类切分的非独立同分布设置，第 6.3 节另外扫描了 IID 程度。MNIST 与 KDDCup 训练 3,000 轮、批大小 50；Amazon 训练 100 轮、批大小 10；VGGFace2 训练 500 轮、批大小 8、动量 0.9、权重衰减 0.0001、学习率 0.001（第 6 节）。FoolsGold 在所有实验中取置信参数 κ = 1，且"does not use the historical gradient or the significant features filter"，这两个设计元素在第 6.5 节与第 6.4 节单独评估（第 6 节）。每个数据点是 5 次实验的平均值（第 6 节）。指标是攻击率（attack rate，攻击目标被错误分到目标类的比例）与准确率（accuracy，测试集正确分类比例）（第 6 节）。

**引出问题的基线结果。** 表 1 给出 MNIST 上 10 个诚实客户端、3,000 次同步迭代、批大小 50 的结果：无攻击时数字 0 与 2 至 9 的准确率为 90.2%、数字 1 的准确率为 96.5%、攻击成功率为 0.0%；1 个女巫时依次为 89.4%、60.7%、35.9%；2 个女巫时依次为 88.8%、0.0%、96.2%（表 1）。

**主要结果。** 图 4 给出各规范攻击（表 3）下的训练准确率与攻击率，论文称 FoolsGold 在多数攻击（含 A-OnOne 与 A-99）下有效阻止攻击并保持高准确率，而在只有一个恶意客户端的 A-1 上表现最差（第 6.1 节）。图 5 显示随投毒者数量从 0 增加到 9，基线联邦学习与 Multi-Krum 的攻击率迅速上升，而 FoolsGold 在 FEDSGD 与 FEDAVG 下都保持稳健，论文称"FoolsGold remains robust even with 9 attackers"（第 6.2 节）。第 6.3 节显示在女巫与诚实客户端共享数据比例的所有组合下，MNIST 与 VGGFace2 的最大攻击率"less than 1%"，图 7 中 MNIST 的格子数值为 0.002 至 0.003，VGGFace2 的格子数值在 0.000 至 0.012 之间。图 14 显示 A-5 攻击在 MNIST 所有源类与目标类组合上的最高攻击率为 0.02（附录 B）。图 15 显示后门攻击在女巫数增加时同样被抑制。

**自适应攻击的结果。** 图 8 显示智能噪声攻击在指示性特征比例降到 0.1 以下后攻击率接近 0，但比例过低（0.01）会损害训练准确率。图 9 给出自适应算法 2 的阈值 M 与所需女巫数的关系：M 大于 0.27 时攻击会被检测，M 设为 0.01 时攻击者"would require a minimum of 10 sybils per opposing client"，而普通联邦学习中只需超过对立客户端数量即可（第 6.4 节）。

**消融结果。** 图 10 中，MNIST 基线（含 FoolsGold）训练误差 13.6%、攻击率 0.26%、目标类误差 13.2%；去掉历史后训练误差 17.8%、攻击率 35.3%、目标类误差 12.3%；KDDCup 基线为 4.10%、0.57%、19.7%；去掉宽恕机制后为 19.8%、0、99.9%；A-99 的 MNIST 基线为 15.6%、0.18%、17.1%；去掉 logit 后为 47.3%、92.9%、19.1%。论文据此说明历史机制阻止了原本会成功的攻击、缺省宽恕机制会带来目标类假阳性、logit 是抵御大量女巫所必需的（第 6.5 节）。

**其他对比。** 图 12 显示单客户端稻草人攻击与 A-5 并发时，FoolsGold、Multi-Krum 与两者组合的训练准确率为 69.9%、77.8%、91.6%，攻击率为 0.10、98.2、0.21；论文称两者互不干扰，单独使用时都无法同时防住两种攻击（第 7 节）。附录 B 显示 RONI 在非独立同分布下会把绝大多数诚实客户端也判为恶意（图 13）。

## 8. 开销

论文报告了运行时开销。作者在 10 到 50 个客户端下比较加入 FoolsGold 前后的运行时间（图 11）。在 CPU 上最昂贵的部分是计算成对余弦相似度，Python 原型未做优化，论文提到已知的角距离近似优化方法；在 GPU 上训练开销足够大，FoolsGold 带来的相对减速可以忽略（第 6.6 节）。微基准测试显示"it took less than 1.5 seconds, even with 50 clients"（第 6.6 节）。通信开销与存储开销论文未报告；论文也未给出历史向量所需存储量的量化数据（论文未报告）。

## 9. 假设、局限与自适应攻击

**成立所依赖的假设（论文自述）。** 数据分布在客户端且对其他方隐藏，攻击者只能通过联邦学习 API 影响训练状态且看不到其他诚实客户端的数据（第 3 节）。聚合服务器未被攻陷（第 3 节）。存在若干诚实客户端，并且"every class defined by the model is represented in the data of at least one honest client"（第 3 节）。不使用安全聚合一类会混淆单条客户端更新的机制（第 3 节）。每个客户端的训练数据分布彼此不同，"FoolsGold relies on the assumption that training data is sufficiently dissimilar between clients"（第 6.3 节）。攻击是定向的标签翻转或后门，且同一攻击中的女巫共享同一投毒目标（第 2 节、第 3 节、附录 A）。优化算法是 SGD（第 2 节）。论文不考虑放大更新幅度的攻击，理由是已有基于幅度的检测方法（第 3 节）。附录 A 还要求诚实客户端的理想梯度之间最大成对余弦相似度 β_g 足够低、女巫之间的相似度足够高。

**论文自述的局限。** FoolsGold 无法防御单个恶意客户端，"FoolsGold is not successful at mitigating attacks mounted by a single poisoning client"（第 7 节），在 A-1 攻击上表现最差（第 6.1 节）。在 A-1 的 KDDCup 上出现了假阳性，系统错误惩罚了一个诚实客户端（第 6.1 节）。指示性特征比例过低会带来假阳性，图 8 中比例 0.01 时训练准确率开始受损（第 6.4 节）。批大小为 1 的 Amazon A-5 攻击下攻击率为 4.76%，论文归因于 10,000 维特征下的维度灾难（附录 B）。知识丰富的攻击者可以用大量女巫配合足够低的相似度阈值颠覆防御（第 6.4 节、图 9）。论文建议用随机化、更好的相似度度量或图相似度等方法改进（第 7 节）。

**自适应攻击者。** 论文评估了四类自适应策略：把恶意数据与正确数据混合；改变女巫的训练批大小；给上传更新加入成对抵消的智能噪声；低频且自适应地发送投毒更新（第 6.4 节，前两类结果在附录 B）。前三类被证明基本无效（图 8、图 16、图 17），第四类被证明在女巫数量足够时可以成功，"With a sufficiently large number of sybils and appropriately low threshold, attackers can subvert our current defense for our observed datasets"（第 6.4 节）。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：除非另注）。**

- 分析：论文的指示性特征来自全局模型输出层参数幅度（第 5 节），而在 LoRA 微调中，输出头往往被冻结或不属于可训练的低秩模块，注意力与前馈层的低秩增量与输出概率之间没有论文所依赖的那种直接映射；论文本身也明确把非输出层的特征影响分析留作未来工作（第 5 节），因此该特征选择规则不能直接搬用。
- 分析：论文的全部实验对象是单层 softmax 与两个卷积网络，最大模型 1.28 亿参数、最多 50 个客户端（表 2、第 6 节），没有 Transformer 或语言模型实验；成对余弦相似度的开销随客户端数平方增长，论文报告的"50 个客户端下少于 1.5 秒"只覆盖输出层这一很小的子空间，不能外推到 LoRA 增量所在的多层、多模块空间。
- 分析：论文假设每个客户端的训练数据分布彼此足够不同（第 6.3 节）。联邦 LoRA 指令微调中，各客户端常常在相同或相近的语料分布上微调同一个预训练主干，诚实客户端之间的更新相似度可能整体升高，从而压缩女巫与诚实客户端之间的可分性。论文第 6.3 节的 IID 实验（图 6）说明即使数据完全同分布，投毒目标仍会让女巫彼此相似，这对迁移是有利证据，但该实验的模型与数据规模与 LLM 相差很远。
- 分析：FoolsGold 的历史机制依赖较多轮次的累积（第 5 节、附录 A），而联邦 LoRA 微调常见的是轮次少、每轮本地计算量大的配置；轮次过少会削弱历史平滑，也会削弱对数几率函数抑制大量女巫的能力。
- 分析：方法要求服务器能逐条查看客户端更新（第 3 节明确假设不使用安全聚合）。若联邦 LoRA 部署使用安全聚合、差分隐私加噪、梯度压缩或量化，则论文的相似度计算前提不成立。
- 分析：论文假设女巫共享同一投毒目标（第 2 节、附录 A），而 LoRA 供应链中的风险还包括单个被篡改的适配器发布者或单点投毒，这类情形论文已证明 FoolsGold 失效（第 7 节），需要与基于幅度的检测方法组合（第 5 节、第 7 节）。

## 10. 对防护库设计的含义

分析：以下六条均为我的推断，不是论文原文内容。

1. 分析：FoolsGold 完全位于服务器侧，是一个纯服务器插件，因此采集底座在服务器钩子上至少要提供"收到每个客户端本轮原始更新"的事件，并在该事件上携带客户端标识、轮次编号与可持久化的历史存储视图；这属于通用需求，任何基于跨轮更新相似度的检测插件都会用到。
2. 分析：本方法特有的数据视图是"参数子空间选择加逐参数重要度权重"。库需要允许插件从聚合后的全局模型里按参数名或层选取一个子空间，并读取该子空间的参数幅度作为权重，再在该子空间上做余弦相似度；如果底座只能提供整条更新的扁平向量，这个方法就无法按论文方式实现。
3. 分析：历史累积 H_i 要求底座支持按客户端标识跨轮累加，并且能区分 FEDSGD（每步一次更新）与 FEDAVG（本地多步后一次更新）两种上传节奏；客户端身份跨轮是否稳定、客户端掉线或换标识时历史如何处理，论文未说明，库需要在采集层作出明确约定。
4. 分析：干预接口必须是"逐客户端连续权重"而不是仅"接受或拒绝"。论文的动作是 α_i 缩放后再聚合，且需要保留至少一个权重为 1、并把权重截断在 0 到 1 之间；只提供剔除客户端的接口会丢失这一方法的核心行为。
5. 分析：插件组合能力是硬需求。论文明确 FoolsGold 对单客户端攻击无效，需要与能处理有界攻击者数量的方法（例如 Multi-Krum）叠加使用（第 5 节、第 7 节、图 12），因此库需要支持在同一聚合钩子上串联多个插件，并保证一个插件输出的权重能被后续插件正确消费。
6. 分析：如果库还想尽早发现本论文描述的攻击，仅靠服务器侧更新视图不够，还需要客户端侧的数据采集点，用来记录本地数据标签分布、投毒触发模式与本地批大小等元信息；但这属于库的通用采集能力，不是 FoolsGold 论文提出的方法，论文本身没有使用任何客户端侧数据。

## 11. 原文依据

1. 第 5 节（FoolsGold design，段首）："Our key insight is that honest clients can be separated from sybils by the diversity of their gradient updates." ——支撑第 1 节论文类型为防御，以及第 4 节的核心思想。
2. 第 3 节（Assumptions and threat model，Setting assumptions）："We assume that these types of obfuscations are not used, and that the central server is able to observe any individual client's model update at each iteration." ——支撑第 2 节防御者可见性，以及第 5 节输入一"在服务器收到更新时采集、不使用安全聚合"。
3. 第 3 节（Setting assumptions）："More precisely, our solution requires that every class defined by the model is represented in the data of at least one honest client." ——支撑第 9 节关于诚实客户端与类别覆盖的成立假设。
4. 第 5 节（段首）："In federated learning, since each client's training data has a unique distribution and is not shared, sybils share a common objective and will contribute updates that appear more similar to each other than honest clients." ——支撑第 4 节方法原理，以及第 5 节女巫更新相似这一可观测量。
5. 第 5 节（Feature importance）："The indicative features are found by measuring the magnitude of model parameters in the output layer of the global model." ——支撑第 5 节输入二"指示性特征权重来自聚合后全局模型的输出层参数幅度"。
6. 第 5 节（Updates history）："FoolsGold maintains a history of updates from each client. It does this by aggregating the updates at each iteration from a single client into a single aggregated client gradient (line 3)." ——支撑第 5 节输入一需要跨轮历史，以及第 6 节的动作发生在服务器聚合阶段。
7. 第 6.3 节（Varying client data distributions）："FoolsGold relies on the assumption that training data is sufficiently dissimilar between clients. However, a realistic scenario may involve settings where each client has overlapping data, such as images of the same people." ——支撑第 9 节关于数据分布差异的假设，以及迁移到联邦 LoRA 微调时的失效风险。
8. 第 7 节（Limitations）："FoolsGold is designed to counter sybil-based attacks and our results in Figure 5 indicate that FoolsGold is not successful at mitigating attacks mounted by a single poisoning client." ——支撑第 9 节论文自述局限与第 10 节插件组合需求。
9. 第 6.4 节（What if the attacker knows FoolsGold?）："With a sufficiently large number of sybils and appropriately low threshold, attackers can subvert our current defense for our observed datasets." ——支撑第 9 节"评估了自适应攻击者且其可以成功"。
10. 第 6.6 节（FoolsGold performance overhead）："We profiled micro-benchmarks for the total time taken to execute the FoolsGold algorithm and found that it took less than 1.5 seconds, even with 50 clients." ——支撑第 8 节的运行时开销结论。

```json
{
  "key": "fung2018foolsgold",
  "title": "Mitigating Sybils in Federated Learning Poisoning",
  "year": 2018,
  "paper_type": "defense",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["backdoor", "other"],
  "attack_entry": ["local_data", "local_training", "update_postprocess"],
  "observables": [
    {"what": "每个客户端每一轮的模型更新或梯度向量", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "全局模型输出层参数幅度导出的指示性特征权重", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "客户端更新的跨轮累积历史向量", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "评估用测试集上的攻击率与准确率", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["reweight"],
  "intervention_where": ["server"],
  "assumptions": [
    "聚合服务器未被攻陷，且不使用安全聚合，能看到每个客户端的单条更新",
    "每个类别至少在某个诚实客户端的数据中出现",
    "诚实客户端之间的训练数据分布足够不同",
    "同一次攻击中的女巫共享同一投毒目标，因此更新方向相似",
    "攻击是定向的标签翻转或后门，不考虑放大更新幅度的攻击",
    "使用 SGD 及其变体作为优化算法"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "5. FoolsGold design", "supports": "第 1 节论文类型与第 4 节核心思想", "text": "Our key insight is that honest clients can be separated from sybils by the diversity of their gradient updates."},
    {"section": "3. Assumptions and threat model", "supports": "第 2 节防御者可见性与第 5 节服务器收到更新时的采集点", "text": "We assume that these types of obfuscations are not used, and that the central server is able to observe any individual client's model update at each iteration."},
    {"section": "3. Assumptions and threat model", "supports": "第 9 节关于诚实客户端与类别覆盖的假设", "text": "More precisely, our solution requires that every class defined by the model is represented in the data of at least one honest client."},
    {"section": "5. FoolsGold design", "supports": "第 4 节方法原理与第 5 节女巫更新相似的可观测量", "text": "In federated learning, since each client's training data has a unique distribution and is not shared, sybils share a common objective and will contribute updates that appear more similar to each other than honest clients."},
    {"section": "5. FoolsGold design, Feature importance", "supports": "第 5 节输入二指示性特征权重的来源", "text": "The indicative features are found by measuring the magnitude of model parameters in the output layer of the global model."},
    {"section": "5. FoolsGold design, Updates history", "supports": "第 5 节跨轮历史需求与第 6 节服务器聚合时的动作", "text": "FoolsGold maintains a history of updates from each client. It does this by aggregating the updates at each iteration from a single client into a single aggregated client gradient (line 3)."},
    {"section": "6.3. Varying client data distributions", "supports": "第 9 节数据分布差异假设与迁移到联邦 LoRA 的风险", "text": "FoolsGold relies on the assumption that training data is sufficiently dissimilar between clients. However, a realistic scenario may involve settings where each client has overlapping data, such as images of the same people."},
    {"section": "7. Limitations", "supports": "第 9 节论文自述局限与第 10 节插件组合需求", "text": "FoolsGold is designed to counter sybil-based attacks and our results in Figure 5 indicate that FoolsGold is not successful at mitigating attacks mounted by a single poisoning client."},
    {"section": "6.4. What if the attacker knows FoolsGold?", "supports": "第 9 节自适应攻击者评估结果", "text": "With a sufficiently large number of sybils and appropriately low threshold, attackers can subvert our current defense for our observed datasets."},
    {"section": "6.6. FoolsGold performance overhead", "supports": "第 8 节运行时开销结论", "text": "We profiled micro-benchmarks for the total time taken to execute the FoolsGold algorithm and found that it took less than 1.5 seconds, even with 50 clients."}
  ]
}
```
