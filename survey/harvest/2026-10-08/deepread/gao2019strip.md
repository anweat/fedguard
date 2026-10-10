# gao2019strip：STRIP: A Defence Against Trojan Attacks on Deep Neural Networks

## 1. 基本信息
- **场景**：不是联邦学习，也不是大模型，而是**集中式（centralized）视觉 DNN 的"外包训练 + 部署后推理"场景**。论文 §II-B 描述的现实动机是：训练算力昂贵，用户把训练外包给云或第三方（machine learning as a service，MLaaS）或使用第三方预训练模型，攻击者因此有机会篡改训练数据和／或模型。检测发生在模型已经部署上线之后的推理运行时（run-time）。论文只在 §VII-A 相关工作里引用 Bagdasaryan 等人的联邦学习后门攻击 [10]，没有把联邦学习作为自己的场景。因此 JSON 中 setting 记为 `other`。
- **训练阶段**：攻击发生在**训练数据准备与训练阶段**（数据投毒）；防御（STRIP）发生在**训练完成、模型部署后的推理阶段**，论文称 run-time。
- **论文类型**：防御／检测。它是"运行时 trojan 输入检测系统"，检测的是输入是否被植入触发器，并由此推断部署模型很可能被植入后门（§I-A 贡献 1）。
- **模型与数据规模**（Table I）：MNIST（10 类，28×28×1，60,000 张，2 Conv + 2 Dense，80,758 参数）；CIFAR10（10 类，32×32×3，60,000 张，8 Conv + 3 Pool + 3 Dropout + 1 Flatten + 1 Dense，308,394 参数）；GTSRB（43 类，32×32×3，51,839 张，ResNet20 [25]，276,587 参数，图像被缩放到 32×32×3）。训练超参见 §V-A：MNIST batch 128、epoch 20、学习率 0.001；CIFAR10 batch 64、epoch 125、学习率 0.001，75 轮后降到 0.0005，100 轮后降到 0.0003；GTSRB batch 32、epoch 100、学习率 0.001，80 轮后降到 0.0001。实验跑在 Google Colab 免费 Tesla K80 上。

## 2. 威胁模型
攻击者是谁（论文未说明）：
- 论文没有"恶意客户端"的概念。攻击者是**外包训练的服务方／模型提供方，或任何能接触训练数据与模型的一方**。导言写"ML models can be trained (e.g., outsourcing) and provided (e.g., pretrained model) by third party. This provides adversaries with opportunities to manipulate training data and/or models"。
- 占比或数量：论文未给出攻击者占比。仅在实验中给出投毒规模——MNIST 例子中 50,000 个训练样本里投毒 600 个（§III），§VI-F 的自适应攻击同样用 600 个投毒样本。
- 能力：§IV-B 明确"攻击者有最大能力"（maximum capability）——对训练数据集有完全访问权，对 DNN 模型／架构有白盒访问权，这比 [16] 的 trojan 攻击假设更强；攻击者还能自行决定触发器的图案、位置和大小，并能设置触发器透明度（§VI-A）。
- 知识：完整的训练数据、模型架构与参数（白盒）。
- 目标：**定向后门**。对干净输入保持与良性模型相当的精度；只要输入带有攻击者私设的触发器，就被判为攻击者指定的目标类。论文明确聚焦 **input-agnostic trigger**（与具体输入内容无关的触发器），即任意输入盖上触发器都判为目标类（§IV-B）。

防御者是谁、能看到什么、信任什么（§IV-B）：
- 防御者是持有并使用已部署模型的一方；持有**少量 held-out 验证样本**（a small collection of validation samples），**不持有任何带触发器的样本**，也**不知道触发器**。
- 对模型是**黑盒**：只观察送入模型的输入和模型输出（softmax）（§I-A 贡献 2、§VII-C）。这与"攻击者白盒"并不矛盾，因为攻击者对应外包训练方，防御者对应模型使用者。
- 论文额外假设：攻击者极不可能把投毒后的训练数据交给用户（"the attacker is extremely unlikely to ship the poisoned training data to the user"），因此 Activation Clustering、Spectral Signatures 这类需要投毒样本的防御在该威胁模型下失效。

## 3. 攻击入口与流程位置
本文是防御论文，下面写它所针对的攻击入口。

- **本地数据准备（训练数据投毒）是本文评估的攻击入口。**§III 的例子：在训练阶段扮演攻击者，把触发器（右下角方块）盖在 600 张 MNIST 训练数字上，并把这些投毒样本的标签全部改成目标类 7；600 张投毒样本与其余 44,000 张干净样本一起训练，得到 trojaned model。
- 论文还讨论另一入口：**模型更新阶段（model update phase）**。§VII-A 介绍 Liu et al. [16] 时写他们不需要访问训练数据，攻击在模型更新阶段而非训练阶段进行。但这不是 STRIP 自己评估的攻击，STRIP 的威胁模型仍以投毒训练数据、交付带后门模型为主。
- **聚合、下发、部署**：论文没有联邦聚合流程，也没有"全局模型下发"这一位置。防御动作位于**模型部署后的推理路径**：Algorithm 1 在每次输入到来时执行扰动与熵判断，输出 trojanedFlag。
- 论文明确没有覆盖 source-label-specific（部分）后门这一入口变体（§VI-E、§VIII）。
- 分析：就你的库而言，这篇论文对应的是"数据提供／外包训练环节注入后门，然后在部署推理端按样本做检测"，它既不在聚合前也不在聚合中取数据。

## 4. 方法原理
核心思想（§I-A、§III、§IV）：input-agnostic trigger 意味着只要触发器存在，无论输入内容是什么，trojaned model 都输出攻击者的目标类。于是对输入施加**强烈扰动**后：被触发器支配的样本预测仍然集中（低熵），干净输入的预测则随扰动大幅变化（高熵）。攻击者的"强项"被反过来当作防御者的抓手。

关键步骤（Fig. 6 与 Algorithm 1，§IV-A）：
1. 对到来的输入 $x$，复制 N 份。
2. 从用户持有的 held-out 数据集 $D_{test}$ 中随机抽取 N 张图片 $x^n_t$。
3. 用图像线性混合（image linear blend，脚本中使用 `cv2.addWeighted()`）把每张抽取图叠加到 $x$ 的副本上，得到 N 个扰动输入 $\{x_{p1}, \dots, x_{pN}\}$，构成扰动集 $D_p$。
4. 把 $x$ 本身与 N 个扰动输入一起送入已部署模型 $F_\Theta$，取 softmax 输出。
5. 对第 n 个扰动输入，按式 (2) 计算 Shannon 熵：$H_n = -\sum_{i=1}^{M} y_i \times \log_2 y_i$，其中 $y_i$ 是该扰动输入属于第 i 类的概率，M 是类别总数（§II-A）。
6. 按式 (3) 求和 $H_{sum}=\sum_{n=1}^{N} H_n$；按式 (4) 归一化 $H = \frac{1}{N} \times H_{sum}$，H 即该输入 x 的熵指标。
7. 若 $H \le$ detection boundary，则判为 trojaned；否则判为 clean（Algorithm 1 第 8–10 行）。

检测边界如何确定（§V-C）：防御者用 held-out 干净样本估计良性输入的熵分布，论文认为该分布是正态分布（Fig. 8 印证），于是先设定 FRR（例如 1%），取该正态分布对应的百分位作为检测边界；FAR 就是 trojaned 输入熵大于该边界的概率。§VII-C 强调该边界**对每个部署模型是专有的**，从已部署模型自身提取，不是全局统一设置，也不需要参考模型。

N 如何选（§V-D）：观察良性输入熵分布的**标准差随 N 的变化**（Fig. 11），当标准差曲线斜率变化变小时选该 N；在 GTSRB 上论文称 N=10 已足够。

直观案例（§III、Fig. 2–5）：INPUT 数字 8 与随机抽取的其他数字线性混合后，干净输入预测在 {5,3,0,8} 间变化（Fig. 3），而带方块触发器的同一数字 8 始终预测为 7（Fig. 4）；Fig. 5 给出 1000 次扰动的预测类分布，trojaned 输入几乎 100% 集中在 7。该例中 trojaned model 对干净输入精度 98.86%，对 trojaned 输入精度 99.86%（§III）。

## 5. 检测或防御所需的数据
1. **待检测的输入样本 x**（图像）。采集位置：部署后的推理入口，即评估／部署阶段（run-time）。粒度：逐样本。不需要跨轮历史，不需要干净参考数据本身（x 可以是被怀疑的任何输入），不需要为其额外计算（本来就要前向一次）。
2. **用户 held-out 的干净数据集 $D_{test}$**，用于随机抽取扰动图。采集位置：部署前由用户持有、部署时在本地使用。粒度：逐样本（每检测一个输入随机抽 N 张）。这是**干净参考数据**，但 STRIP **不需要它们的 ground-truth 标签**（§VII-C 明确"我们既不关心到来输入的标签，也不关心 held-out 抽取图的标签"）。不需要额外前向或反向。
3. **已部署模型对每个扰动副本的 softmax 输出概率分布**。采集位置：推理时从部署模型输出端取得。粒度：逐样本（每个扰动输入一份 M 维概率分布），逐轮/逐层不适用。这是黑盒输出，不需要隐藏层激活、梯度或逐样本损失，也不需要其他客户端的数据。
4. **良性输入熵分布的统计量**（均值与标准差，Table III 的 Mean 与 Standard variation 列）。采集位置：部署前离线标定（用 held-out 干净样本跑一遍同样的"扰动 + 熵"流程）。粒度：模型级；每个部署模型一套。需要干净参考数据，需要额外前向计算（离线）。
5. **检测边界与 N 的选择结果**（§V-C、§V-D）。采集位置：离线标定阶段；粒度：模型级；需要干净参考数据与额外前向计算（用于画 Fig. 10、Fig. 11）。
6. 不需要的数据（论文全文没有出现）：跨轮历史更新、客户端 LoRA 增量、逐层范数、逐样本训练损失、梯度、隐藏层激活、输出文本、其他客户端的数据、根数据集。

攻击会留下什么痕迹（攻击论文视角的对应内容）：
- input-agnostic 触发器会让被触发样本在强扰动下的预测类分布高度集中，熵显著低于干净输入；§V-C 给出 CIFAR10 上的熵间隙：trigger b 时最小干净输入熵 0.029、最大 trojan 输入熵 $7.74\times10^{-9}$；trigger c 时 0.092 与 0.005。
- 即使攻击者做 entropy manipulation 自适应攻击，也会在**干净输入的熵分布**上留下"不是正态分布、且熵值异常偏高（始终大于 3.0）"的痕迹（§VI-F、Fig. 13）。
- Appendix B 还观察到：被误接收（false accepted）的 trojaned 图像多数已失去 trojan 效果（Fig. 15：10 张里 4 张仍保持劫持效果，6 张失效，另有 3 张被 trojaned model 分到正确 ground-truth 标签）。
- 论文声称能绕过的检测限制（即 STRIP 相对他人的优势，Table IV）：不依赖触发器大小（大触发器会使 Neural Cleanse 与 SentiNet 失效）、不需要白盒内部神经元、不需要投毒样本、运行时开销低。

## 6. 干预动作
- 论文给出的唯一动作是**报告／告警**（report only）：Algorithm 1 返回 `trojanedFlag`（Yes/No），判定"该输入是 trojaned 输入"，并由此推断"部署模型很可能存在后门"（§I-A 贡献 1 原文："Our approach detects whether the input is trojaned or not (and consequently the high possibility of existence of a backdoor in the deployed ML model)"）。
- 论文没有提出剔除客户端、重新加权、裁剪、加噪、过滤训练样本、修复或回滚模型中的任何一项。§VII-B 提到 fine-pruning [32] 会显著降低模型精度、[33] 复杂度和计算成本高，这些是他人工作；§VIII 只说 STRIP"easy-to-implement, time-efficient and complementing with existing trojan mitigation techniques"。
- 动作位置：**模型部署之后的推理路径**（run-time），在输入被正常分类的同时给出检测结论；不是训练期、不是聚合期，也没有"拒绝该输入"的策略评估。
- 分析：论文没有评估"检出后拒绝输入/拒绝响应"的后果，也没有评估误拒（FRR）在业务上的代价，只报告了 FAR 与 FRR 指标。

## 7. 实验设置与主要结果
- 模型与数据集：Table I（见第 1 节）；数据集为 MNIST [22]、CIFAR10 [23]、GTSRB [24]。
- 客户端数与参与率：论文未说明（论文不是联邦学习设置）。
- 轮次：论文未说明（非联邦训练）。
- 恶意比例：MNIST 案例为 600/50,000（§III）；§VI-F 自适应攻击投毒 600 个 CIFAR10 样本；其余未说明。
- 数据是否非独立同分布：论文未说明。
- 指标：FAR 与 FRR（定义见 §IV-C：FRR 是良性输入被判为 trojaned 的概率，FAR 是 trojaned 输入被判为良性的概率），以及攻击成功率与干净输入分类精度（Table II）。
- 攻击效果（Table II）：MNIST + square trigger：trojaned model 干净精度 98.86%、攻击成功率 99.86%、原始干净模型精度 98.62%；MNIST + trigger a：98.86%／100%／98.62%；CIFAR10 + trigger b：87.23%／100%／88.27%；CIFAR10 + trigger c：87.34%／100%／88.27%；GTSRB + trigger b：96.22%／100%／96.38%。
- 检测效果（Table III，N=100）：
  - MNIST + square：良性熵均值 0.196、标准差 0.074；FRR 3% 时边界 0.058、FAR 0.75%；FRR 2% 时边界 0.046、FAR 1.1%；FRR 1% 时边界 0.026、FAR 1.85%。
  - MNIST + trigger a：均值 0.189、标准差 0.071；FRR 2% 时边界 0.055、FAR 0%；FRR 1% 时边界 0.0235、FAR 0%；FRR 0.5% 时边界 0.0057、FAR 1.5%。
  - CIFAR10 + trigger b：均值 0.97、标准差 0.30；FRR 2%／1%／0.5% 时边界 0.36／0.28／0.20，FAR 均为 0%。
  - CIFAR10 + trigger c：均值 1.11、标准差 0.31；边界 0.46／0.38／0.30，FAR 均为 0%。
  - GTSRB + trigger b：均值 0.53、标准差 0.19；边界 0.133／0.081／0.034，FAR 均为 0%。
  - 摘要与 §I-A 声称：给定 FRR 为 1%，总体 FAR 小于 1%；在 CIFAR10 与 GTSRB 上实证达到 FAR 与 FRR 均为 0%。Table IV 给出的 STRIP 汇总值为 **0.46% FAR 和 1% FRR**。注意 Table III 中 MNIST + square 在 FRR=1% 时 FAR 为 1.85%，与该"总体小于 1%"并不完全一致；分析：Table IV 的 0.46% 应是跨触发器／数据集的平均，论文未说明该总体值的汇总方式。
- 每个案例测试 2000 个干净样本与 2000 个 trojaned 样本，每个输入用 N=100 个扰动副本（§V-B）。
- 触发器透明度（Table V，CIFAR10 + trigger b，FRR 预设 0.5%）：90% 时干净精度 87.11%、攻击成功率 99.93%、最小干净熵 0.0647、最大 trojan 熵 0.6218、边界 0.2247、FAR 0.10%；80% 时 85.81%／100%／0.0040／0.0172／0.1526／0%；70% 时 88.59%／100%／0.0323／0.0167／0.1546／0%；60% 时 86.68%／100%／0.0314／$3.04\times10^{-17}$／0.1459／0%；50% 时 86.80%／100%／0.0235／$4.31\times10^{-6}$／0.1001／0%。论文总结：透明度越低（触发器越显眼）检测越容易，即使透明度高达 90% 仍能检测。
- 大触发器（Hello Kitty，70% 透明度，与输入 100% 重叠，§VI-B）：干净精度 86%，攻击成功率 99.98%，最小干净熵 0.0035、最大 trojan 熵 0.0024，因此 FAR 与 FRR 均为 0%；论文指出大触发器被报告可逃逸 Neural Cleanse [17] 与 SentiNet [11]。
- 多目标标签的多个独立触发器（§VI-C）：10 个触发器各指向不同类，干净精度 87.17%，每个触发器攻击成功率 100%；多数标签 FAR 与 FRR 为 0%，FRR 预设 0.5% 时最差为 'airplane' 标签 FAR 0.1%。论文对比：Neural Cleanse 报告的感染标签检测率不超过 36.9%。
- 同一标签的多个触发器（§VI-D）：干净精度 86.12%，每个触发器攻击成功率 100%，STRIP 的 FAR 与 FRR 均为 0%。
- 部分（source-label-specific）后门（§VI-E）：干净精度 85.56%，源类平均攻击成功率 98.20%，非源类 ship 与 truck 的攻击成功率降为 19.7% 与 12.4%。在论文的威胁模型下 STRIP 无法检测；若假设防御者持有 trojaned 样本，则可通过离线检查极低熵样本发现（Fig. 12）。
- 自适应攻击 entropy manipulation（§VI-F）：干净精度 86.61%，攻击成功率 99.95%，干净与 trojaned 熵分布相似；但干净输入的熵始终大于 3.0 且不服从正态分布，可据此检测出模型异常（Fig. 13）。
- 网络深度影响（Appendix B）：8 层 CIFAR10 模型干净精度约 88%；2 层模型干净精度 70%，其 trojaned model 干净精度约 70%、攻击成功率约 99%，此时 2% FRR 给出 0.45% FAR、1% FRR 给出 0.6% FAR、0.5% FRR 给出 0.9% FAR；8 层模型则 FAR 恒为 0%。8 层模型在 MNIST + square 上干净精度 99.02%、trojaned 输入 99.99%，1% FRR 给出 0% FAR、0.5% FRR 给出 0.03% FAR。论文的经验结论是模型越深检测能力越好。

## 8. 开销
- 时间／计算（§V-D、Fig. 10、Fig. 11；ResNet20 + GTSRB + trigger b，batch size 32）：N=10 时，顺序生成 10 张扰动图耗时 0.1ms，预测 10 张图耗时 6.025ms，STRIP 检测总开销 6.125ms；不使用 STRIP 的原推理时间为 4.63ms；论文称"Without optimization, STRIP is 1.32 times longer than the original default inference time"。论文指出图像生成与 N 个扰动图的预测都可以并行（例如用 N 个模型副本）。
- 论文报告的 N 相关结论：N 从 2 到 100 变化时检测能力与延迟的权衡见 Fig. 10；GTSRB 上 N 约 10 时最大 trojan 输入熵已小于最小良性输入熵；GTSRB 上 N=10 已足够（Fig. 11）。
- 存储开销：论文未报告。
- 通信开销：论文未报告（论文不是分布式设置，也没有通信过程）。
- 显存／内存开销：论文未报告。

## 9. 假设、局限与自适应攻击
论文依赖的假设：
- 攻击是 **input-agnostic trigger**：任意输入只要带触发器就判为目标类（§IV-B）。这是方法成立的前提。
- 防御者持有少量 held-out 验证样本，且**不持有任何带触发器的样本**；攻击者不会把投毒训练数据交给用户（§IV-B）。
- 良性输入在强扰动下的预测类熵近似**正态分布**，因此可用预设 FRR 对应的百分位确定边界（§V-C，Fig. 8 印证）。
- **强扰动不破坏触发器的支配作用**：图像线性混合后触发器样本仍被判为目标类（Fig. 4 与 §III 的推理逻辑）。论文也承认其他扰动策略可以替换图像叠加。
- 防御者能在模型部署后对每个输入执行 N 次额外前向并读取 softmax 输出（§IV-A、§V-D）。
- 攻击者交付的模型在干净输入上精度与良性模型相当，否则精度退化本身会引起怀疑（§IV-B 对攻击者目标的描述）。
- 检测边界按每个部署模型单独标定，不使用全局阈值、不需要参考模型（§VII-C）。
- Appendix B 的经验假设：网络越深，触发特征被记忆得越强，检测能力越好。

论文自述的局限：
- **无法检测 source-label-specific（部分）后门。**§VI-E 与 §VIII 明确说：与 Neural Cleanse、SentiNet 一样，STRIP 对这类触发器无效，留作未来工作。
- 目前只在视觉领域验证；§V-A 与 §VIII 说 STRIP 可能适用于文本与语音，但尚未测试，文本域需要换用别的扰动方式（例如随机替换若干词）。
- 需要预先确定 N 和检测边界，并且需要 held-out 干净样本；边界标定依赖熵的正态性假设。
- 浅层网络上检测能力下降（Appendix B：2 层模型在 1% FRR 下 FAR 为 0.6%）。
- §VI-E 还指出 source-label-specific 攻击在联邦学习场景下更难实施，因为攻击者不能操纵其他参与者拥有的类。

自适应攻击评估：**是。**§VI 开头说，按 Oakland 2019 研究 [17] 的做法实现了五种高级后门攻击，并称"To some extent, those backdoor variants can be viewed as adaptive attacks that are general to backdoor defences"；此外论文自己识别并评估了一个专门针对 STRIP 的自适应攻击 entropy manipulation（§VI-F）。结果是：透明度、大触发器、多目标多触发器、同标签多触发器这几类变体下 STRIP 仍然有效（Table V、§VI-B 至 §VI-D）；entropy manipulation 虽然把干净与 trojaned 的熵分布拉近，但会使干净输入的熵分布偏离正态且数值异常偏高（始终大于 3.0），论文认为可据此检测。

迁移到联邦 LoRA 微调时可能失效的假设：
- 分析：STRIP 的采集点在**推理入口**，而联邦 LoRA 微调的服务器通常看不到客户端的推理输入，也不存在一个可直接调用的统一模型（需要先把 LoRA 增量与基座合并）。论文完全没有客户端钩子、服务器聚合钩子的概念，因此"在哪里拿输入、在哪里前向"这一最基本的流程前提需要重建。
- 分析：方法的核心量是**M 类 softmax 的 Shannon 熵**。生成式大模型没有单次 M 类 softmax，只有逐 token 的词表分布；"input-agnostic"在生成任务里对应的是输出内容／行为不变，而不是类别不变。论文没有给出任何生成式或文本上的实验证据，§V-A 里的文本设想（随机替换词）只是提议。
- 分析：图像线性混合这一扰动算子在文本上不存在直接对应物；文本触发器往往就是稀有 token 或固定短语，替换可能直接抹掉触发器（熵被抬高、漏检），也可能改变语义使干净输入熵下降（误拒），论文的"强扰动不破坏触发器"前提在文本上没有任何验证。
- 分析："良性输入熵服从正态分布"这一标定假设完全来自图像分类实验，在非独立同分布的多客户端文本数据上没有任何依据；每个客户端自己的数据既可能是"干净参考"，也可能本身就是投毒来源。
- 分析：STRIP 的威胁模型假设攻击者拥有完整训练数据与白盒模型，这只在恶意服务器或全体客户端合谋时成立。对"恶意客户端只改自己的本地 LoRA 更新"这类攻击（例如 Bagdasaryan 等人的 constrain-and-scale 式模型替换），STRIP 没有提供任何检查手段；论文对 [10] 只在相关工作里引用其结论（不超过 1% 参与者即可植入后门）。
- 分析：论文把 FL 后门攻击 [10] 和"FL 中 source-label-specific 攻击更难做"（§VI-E）都放在与自身场景不同的位置，说明作者并不认为自己的结论可以直接搬到 FL；把它迁移到联邦 LoRA 属于超出论文依据的外推。
- 分析：开销结论不可直接外推。论文只报告了 ResNet20 上 N=10 时 6.125ms 对 4.63ms（§V-D）；在数十亿参数的大模型上做 N 次额外前向，成本结构与数量级都不同，论文没有相关数据。

## 10. 对防护库设计的含义
- 分析：这篇论文需要的是**推理期（evaluation/deployment）钩子**，而不是训练期钩子。库必须能在"合并后的模型对某个输入做前向"的位置，向插件暴露逐样本的输入视图和 softmax 输出视图，并允许插件对同一个输入**再发起 N 次额外前向**。这与"客户端训练前／每步／训练后、服务器收到更新／聚合"这些钩子都不同，属于采集底座目前结构里容易被忽略的一类信任边界。
- 分析：需要把**干净参考池**做成一等公民。每个受保护的模型要绑定一份 held-out 干净样本（不需要标签）、一组离线标定出来的统计量（良性熵均值、标准差、检测边界、N），并作为插件的持久状态保存。库还需要能区分"防御者自持的干净参考"与"攻击者投毒的数据"，因为这篇论文的威胁模型明确假设后者不可得。
- 分析：**扰动算子必须可插拔**。图像线性混合只是这篇论文的选择，文本场景需要替换、改写、加噪等不同算子；插件接口应当把"由输入生成 N 个扰动副本"暴露成可替换组件，而不是把它写死在检测算法里，否则迁移到联邦 LoRA 微调时无法替换。
- 分析：**干预接口只需要"报告／告警"级别**，不需要剔除客户端、重新加权、裁剪、加噪、回滚模型这些聚合期动作。库可以把它的输出定义为"该样本可疑 + 该模型很可能被植入后门"的事件，交给运维或后续插件处理；不应把它实现成聚合期防御插件。
- 分析：**通用需求**包括逐样本输入与模型输出的采集、插件持久状态（阈值与标定统计量）、可配置的额外前向预算、离线标定流程；**这篇论文特有的需求**包括图像线性混合扰动、基于类别 softmax 的熵、每模型独立边界、"观察标准差随 N 的斜率"这一 N 选择启发式。
- 分析：如果确实要在联邦 LoRA 上复用这套思路，库至少要额外提供三项论文没有的能力：把客户端提交的 LoRA 增量与基座合并成可前向模型、服务器侧或客户端侧的一份可信干净评估集、以及在生成式模型上对"输出分布熵／输出不变性"的可操作定义；这些都属于超出本文依据的工程改造。

## 11. 原文依据
1. §III（支撑第 3 节"攻击在本地数据准备阶段进入"与第 7 节投毒比例）："In the training phase, we (act as the attacker) poison a small number of training digits—600 out of 50,000 training samples—by stamping the trigger"
2. Abstract（支撑第 4 节核心原理与第 1 节论文类型）："A low entropy in predicted classes violates the input-dependence property of a benign model and implies the presence of a malicious input—a characteristic of a trojaned input."
3. §IV-A（支撑第 5 节"需要 held-out 干净参考数据与扰动副本"）："Each perturbed input is a superimposed image of both the input x (replica) and an image randomly drawn from the user held-out dataset, Dtest."
4. §IV-B（支撑第 2 节攻击者能力）："The attacker has full access to the training dataset and white-box access to the DNN model/architecture, which is a stronger assumption than the trojan attack in [16]."
5. §IV-B（支撑第 2 节与第 5 节防御者可见数据）："From the defender side, as in [11], [17], we reason that he/she has held out a small collection of validation samples. However, the defender does not have access to trojaned data stamped with triggers"
6. §V-C（支撑第 9 节"良性熵服从正态分布"的标定假设）："The user can estimate the entropy distribution of benign inputs. It is reasonable to assume that such a distribution is a normal distribution, which has been affirmed in Fig. 8."
7. §VI-F（支撑第 9 节自适应攻击的定义与评估）："In other words, the attacker can forge a trojaned model exhibiting similar entropy for both clean and trojaned samples. We refer to such an adaptive attack as an entropy manipulation."
8. §VIII（支撑第 9 节"无法检测 source-label-specific 触发器"这一自述局限）："Nevertheless, similar to Neural Cleanse [17] and SentiNet [11], STRIP is not effective to detect source-label-specific triggers; this needs to be addressed in future work."
9. §V-D（支撑第 8 节开销数值）："In total, STRIP detection overhead is 6.125ms, whereas the original inference time without implementing STRIP is 4.63ms."
10. §VII-A（支撑第 1 节与第 9 节"联邦学习只作为相关工作被引用，不是本文场景"；原文"controll"为拼写错误，逐字保留）："The authors demonstrate that with controll over no more than 1% participants, an attacker is able to cause a global model to be trojaned and achieves a 100% accuracy on the trojaned input"

```json
{
  "key": "gao2019strip",
  "title": "STRIP: A Defence Against Trojan Attacks on Deep Neural Networks",
  "year": 2019,
  "paper_type": "defense",
  "setting": "other",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_server", "data_provider"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "部署时到来的待检测输入样本（图像）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "用户 held-out 干净数据集 Dtest 中随机抽取的扰动源图像（不需要标签）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "已部署模型对输入及其 N 个扰动副本的 softmax 输出概率分布", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "良性输入熵分布的均值与标准差、检测边界、N 的选择结果（离线标定）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["report_only"],
  "intervention_where": ["none"],
  "assumptions": [
    "攻击使用 input-agnostic trigger：任意输入盖上触发器都被判为攻击者预设目标类",
    "防御者持有少量无触发器的 held-out 验证样本，且不持有任何带触发器的样本",
    "良性输入在强扰动下的预测类熵近似正态分布，可用预设 FRR 的百分位确定检测边界",
    "强扰动（图像线性混合）不会破坏触发器的支配作用",
    "防御者能在部署后对每个输入额外执行 N 次前向并读取 softmax 输出",
    "攻击者返回的模型在干净输入上的精度与良性模型相当，否则会被察觉",
    "检测边界按每个部署模型单独标定，不使用全局阈值，也不需要参考模型"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "III", "supports": "第 3 节：攻击进入位置是本地数据准备阶段的数据投毒；第 7 节：MNIST 案例投毒 600/50,000", "text": "In the training phase, we (act as the attacker) poison a small number of training digits—600 out of 50,000 training samples—by stamping the trigger"},
    {"section": "Abstract", "supports": "第 4 节：低熵违反良性模型的输入依赖性是 STRIP 的核心判据；第 1 节：论文类型为防御检测", "text": "A low entropy in predicted classes violates the input-dependence property of a benign model and implies the presence of a malicious input—a characteristic of a trojaned input."},
    {"section": "IV-A", "supports": "第 5 节：需要用户 held-out 干净数据集作为扰动源，并生成叠加扰动副本", "text": "Each perturbed input is a superimposed image of both the input x (replica) and an image randomly drawn from the user held-out dataset, Dtest."},
    {"section": "IV-B", "supports": "第 2 节：攻击者拥有完整训练数据与模型白盒访问权", "text": "The attacker has full access to the training dataset and white-box access to the DNN model/architecture, which is a stronger assumption than the trojan attack in [16]."},
    {"section": "IV-B", "supports": "第 2 节与第 5 节：防御者只有少量 held-out 验证样本、没有带触发器样本", "text": "From the defender side, as in [11], [17], we reason that he/she has held out a small collection of validation samples. However, the defender does not have access to trojaned data stamped with triggers"},
    {"section": "V-C", "supports": "第 9 节：检测边界标定依赖良性熵服从正态分布的假设", "text": "The user can estimate the entropy distribution of benign inputs. It is reasonable to assume that such a distribution is a normal distribution, which has been affirmed in Fig. 8."},
    {"section": "VI-F", "supports": "第 9 节：论文识别并评估了针对 STRIP 的 entropy manipulation 自适应攻击", "text": "In other words, the attacker can forge a trojaned model exhibiting similar entropy for both clean and trojaned samples. We refer to such an adaptive attack as an entropy manipulation."},
    {"section": "VIII", "supports": "第 9 节：论文自述无法检测 source-label-specific 触发器", "text": "Nevertheless, similar to Neural Cleanse [17] and SentiNet [11], STRIP is not effective to detect source-label-specific triggers; this needs to be addressed in future work."},
    {"section": "V-D", "supports": "第 8 节：论文报告的检测时间开销数值", "text": "In total, STRIP detection overhead is 6.125ms, whereas the original inference time without implementing STRIP is 4.63ms."},
    {"section": "VII-A", "supports": "第 1 节与第 9 节：联邦学习后门攻击仅作为相关工作被引用，不是本文场景与实验", "text": "The authors demonstrate that with controll over no more than 1% participants, an attacker is able to cause a global model to be trojaned and achieves a 100% accuracy on the trojaned input"}
  ]
}
```
