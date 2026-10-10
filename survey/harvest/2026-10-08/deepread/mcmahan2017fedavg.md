# mcmahan2017fedavg：Communication-Efficient Learning of Deep Networks from Decentralized Data

## 1. 基本信息

场景：传统联邦学习（classic federated learning）。论文面向移动设备上的图像分类与语言建模（下一词预测），提出并评估联邦平均算法 FederatedAveraging（FedAvg），不是联邦大模型微调，也不涉及参数高效微调（parameter-efficient fine-tuning，PEFT）或 LoRA。训练阶段覆盖同步通信轮次下的客户端本地多步训练与服务器加权聚合，不包含部署期防御或评估期检测。

论文类型：基础方法（foundation），同时带有基准（benchmark）性质的大规模实证评估。论文不是攻击、检测或防御论文，全文没有威胁模型章节，也没有任何恶意参与方实验。

模型与数据规模：论文摘要称评估了五种模型架构与四个数据集。具体为：MNIST 上的两层隐藏层感知机（199,210 个参数）、MNIST 上的卷积网络（第一个卷积层 32 通道、第二个 64 通道，全连接层 512 单元，共 1,663,370 个参数）、莎士比亚文本上的字符级 LSTM（866,578 个参数，unroll 长度 80 个字符）、CIFAR-10 上的卷积网络（约 10 的 6 次方个参数），以及大规模词级 LSTM（词表 10,000 词、输入输出嵌入维度 192、共 4,950,544 个参数，unroll 长度 10 个词）。数据规模：MNIST 划分为 100 个客户端、每个 600 例；莎士比亚数据集按剧本角色构建出 1146 个客户端，训练集 3,564,579 个字符、测试集 870,014 个字符；CIFAR-10 划分为 100 个客户端、每个 500 个训练样本与 100 个测试样本；大规模语言模型实验使用 1000 万条公开社交网络帖子、超过 500,000 个客户端、每客户端至多 5000 词、测试集为 1e5 条帖子。论文提到为这些实验总共训练了超过 2000 个模型。

## 2. 威胁模型

论文未说明威胁模型。全文没有定义攻击者、没有给出恶意客户端比例或数量、没有设定攻击者能力与知识，也没有设定攻击目标。这是基础方法论文，攻击与防御不是其研究对象。

论文明确写出的信任关系如下。第一，客户端本地训练数据从不上传到服务器，客户端只上传对当前全局模型的更新。第二，仍然需要在一定程度上信任协调训练的中央服务器，论文原话是"Clearly, some trust of the server coordinating the training is still required."。第三，隐私收益的强度取决于更新本身的内容，脚注 1 给出了反例：若更新是全部本地数据上的总梯度且特征是稀疏词袋，非零梯度会直接暴露用户在设备上输入过哪些词。

论文把若干部署现实问题列为范围之外，其中与安全直接相关的只有一句：客户端可能"从不响应或发送损坏的更新"（"clients that never respond or send corrupted updates"）。论文紧接着写明"These issues are beyond the scope of the current work."。论文未说明服务器如何验证更新的正确性、如何识别恶意或损坏更新、是否使用认证、签名、异常检测或鲁棒聚合。

防御者是谁：论文中没有防御者角色。承担协调职能的是中央服务器，它能看到每个被选中客户端返回的更新与本地样本数，持有全局模型状态，并向被选客户端下发当前全局状态。客户端能看到服务器下发的全局模型。论文未说明服务器信任什么、能校验什么；按算法设定，服务器直接接受并加权平均所有被选中客户端返回的更新，没有任何滤除步骤。

## 3. 攻击入口与流程位置

论文不含攻击，因此不存在"攻击从哪个位置进入"的答案，论文也未说明任何攻击方法、成功率、持久性或绕过检测的能力。

论文给出的算法流程本身包含以下可被外部工作利用的位置，以下均为对论文结构的复述而非论文提出的攻击。本地数据准备：每个客户端持有固定的本地数据集 P_k。本地训练过程：ClientUpdate 中按 minibatch 大小 B 划分本地数据，在每个本地 epoch（共 E 个）内执行 w 更新为 w 减去 η 乘 ℓ(w; b) 的梯度，每轮本地更新次数为 u_k 等于 E 乘 n_k 除以 B。更新上传前的后处理：论文的算法中没有缩放、投影或拼装，客户端直接返回本地训练后的模型 w^k_{t+1} 以及其本地样本数 n_k。服务器聚合：服务器按样本数加权平均，m_t 为被选客户端样本数之和，全局模型为各客户端返回模型以 n_k 除以 m_t 为权重的加权和。全局模型下发：服务器把新的全局模型广播给下一轮被选中的客户端。评估与部署：论文只在测试集上评估全局模型，没有部署期机制。

论文唯一一次提到"损坏更新"是在列出现实问题时，并明确将其排除在本文范围之外，论文未说明其防御方案。

## 4. 方法原理

核心思想是把数据中心里"本地多步训练加参数平均"的做法搬到联邦设定，用增加每客户端计算量的方式换取通信轮数的下降。论文的目标函数是公式 (1)，即最小化 w 上的 f(w)，f(w) 定义为 n 个 f_i(w) 的平均，其中 f_i 是模型参数 w 在样本 (x_i, y_i) 上的损失。数据分布在 K 个客户端上，P_k 是客户端 k 的样本索引集合，n_k 是其大小，于是 f(w) 写成各客户端 F_k(w) 以 n_k 除以 n 为权重的加权和。

基线算法 FederatedSGD（FedSGD）：每轮选取比例为 C 的客户端，客户端 k 在当前模型 w_t 上计算本地平均梯度，服务器汇总后按学习率 η 做一次全局更新；论文指出等价的写法是每个客户端先本地走一步梯度下降，服务器再对这些模型做加权平均。这一等价改写是加入更多本地计算的入口。

FedAvg：在上述等价形式中让每个客户端在本地迭代多次更新，再上传平均。计算量由三个参数控制：C 是每轮参与计算的客户端比例，E 是每客户端每轮在本地数据集上的训练遍数，B 是客户端更新的本地 minibatch 大小。当 B 为无穷大且 E 等于 1 时，FedAvg 退化为 FedSGD。每客户端每轮的本地更新次数 u_k 等于 E 乘 n_k 除以 B。完整伪代码见 Algorithm 1，其中服务器初始化 w_0，每轮取 m 等于 max(C 乘 K, 1) 个客户端，收集各客户端的 w^k_{t+1}，并按样本数加权平均得到 w_{t+1}。

参数平均为何可行：论文用 Figure 1 说明，两个从不同随机初始化训练出的 MNIST 模型做参数插值平均会产生很差的损失（左图），而从相同随机初始化出发、在不同数据子集上独立训练的两个模型做平均，在全量 MNIST 训练集上取得显著低于任一父模型的损失（右图）。论文指出 FedAvg 每轮都使用同一个共享起始模型 w_t，因此同样的直觉适用。

## 5. 检测或防御所需的数据

论文未说明任何检测或防御方法，因此不存在"检测所需数据"；论文也未说明逐样本损失、隐藏层激活、输出文本、干净参考数据、根数据集或跨轮检测视图。本节按论文明确描述的算法数据流列出该流程在信任边界上实际产生与消费的数据项，作为采集底座的依据。

第一，客户端本地数据集 P_k。内容为样本与标签，位置在客户端训练前与训练中，粒度是逐样本，仅在设备本地存在，论文明确说明从不上传服务器。不需要额外计算。

第二，全局模型 w_t。内容为当前全局参数，位置在客户端每轮训练开始时由服务器下发，粒度是模型级、逐轮。论文未说明是否保存历史全局模型，但 Algorithm 1 的流程天然产生每轮的全局模型版本。

第三，本地 minibatch 梯度。内容为对 minibatch b 计算的损失梯度，位置在客户端每步本地更新，粒度是逐批。论文在脚注 1 中用这一量讨论隐私泄露，指出稀疏特征下非零梯度会暴露用户输入内容。需要反向计算，但这是训练本身的组成，不是额外计算。

第四，客户端返回的本地模型 w^k_{t+1}。内容为本地多步训练后的参数，位置在服务器收到更新时，粒度是逐客户端、逐层或逐参数、逐轮。这是服务器侧最主要的可观测量，论文未说明对其做任何检查。

第五，客户端本地样本数 n_k。位置在服务器收到更新与聚合时，粒度是逐客户端、逐轮，用于加权平均。论文未说明该数值如何被验证。

第六，每客户端每轮本地更新次数 u_k 等于 E 乘 n_k 除以 B。这是论文正文用于排序实验的统计量，位置在客户端训练过程，粒度是逐客户端、逐轮。

第七，聚合后的全局模型 w_{t+1}。位置在服务器聚合后，粒度是模型级、逐轮，随后被下发给下一轮客户端。

论文声称能绕过哪些检测：论文未讨论检测，也未声称绕过任何检测。攻击会在哪些可观测量上留下痕迹：论文未说明，因为论文没有攻击。

## 6. 干预动作

论文没有检测环节，因此没有检测后的干预动作。全文未评估剔除客户端、重新加权、裁剪、加噪、过滤样本、修复或回滚模型等任何安全动作，也没有报告类机制。

服务器在收到更新后唯一执行的动作是按样本数加权平均，这一动作发生在服务器聚合位置，见 Algorithm 1。这是 FedAvg 的基础训练算法，不是针对恶意行为的防御，论文也未把它描述为防御。

论文中唯一带有"干预"色彩的内容是超参数层面的：Figure 3 显示在莎士比亚 LSTM 上，当本地 epoch 数 E 很大时 FedAvg 可能停滞甚至发散，作者据此建议在收敛后期衰减每轮本地计算量（减小 E 或增大 B），类似衰减学习率的作用。这是优化层面的调参建议，论文未说明它与安全或鲁棒性有关。此外 Table 1 的说明提到五组大 batch 设置在允许时间内未达到目标精度，属于实验资源限制，不是干预机制。

## 7. 实验设置与主要结果

MNIST 设置：100 个客户端，每个 600 例。IID 划分是打乱后平均划分；非 IID 划分是先按数字标签排序、切成 200 个大小为 300 的分片、每个客户端分到 2 个分片，论文称这是"病态的非 IID 划分"，因为多数客户端只有两个数字的样本。两种划分都是平衡的。默认取 C 等于 0.1。

MNIST 主要结果：Table 1 给出达到目标精度所需通信轮数随客户端比例 C 的变化，2NN 的目标是 97%、CNN 的目标是 99%，C 等于 0.0 表示每轮一个客户端。例如 2NN 非 IID 且 B 等于 10 时，C 等于 0.0 需要 3275 轮，C 等于 1.0 需要 380 轮（8.6 倍加速）；CNN 在 E 等于 5、非 IID 且 B 等于 10 时，C 等于 0.0 需要 956 轮，C 等于 1.0 需要 97 轮（9.9 倍加速）。Table 2 给出相对 FedSGD 的加速：MNIST CNN 达到 99% 精度时，FedSGD 在 IID 下需 626 轮、非 IID 下需 483 轮，而 FedAvg 在 E 等于 20、B 等于 10 时 IID 只要 18 轮（34.8 倍）、非 IID 需要 173 轮（2.8 倍）。莎士比亚 LSTM 达到 54% 精度时，FedSGD 在 IID 下需 2488 轮、非 IID 下需 3906 轮，FedAvg 在 E 等于 5、B 等于 10 时 IID 需要 192 轮（13.0 倍）、非 IID 只需要 41 轮（95.3 倍）。正文称对 IID 的 MNIST，增加每客户端计算量把 CNN 的轮数降低 35 倍、把 2NN 降低 46 倍，对病态非 IID 数据的加速较小但仍有 2.8 到 3.7 倍。2NN 的完整表格见附录 Table 4，例如 E 等于 20、B 等于 10 时 IID 为 32 轮（45.9 倍）、非 IID 为 738 轮（2.5 倍）。正文还报告 FedAvg 收敛到的测试精度高于 FedSGD：CNN 上 FedSGD 在 1200 轮后达到 99.22%，而 FedAvg 在 300 轮后达到 99.44%。

莎士比亚设置：按每个剧本中至少有 2 行台词的角色构建客户端，共 1146 个客户端，每客户端前 80% 的行作训练、后 20% 的行作测试，训练集 3,564,579 字符、测试集 870,014 字符。数据显著不平衡，且测试行按剧本时间顺序切分而非随机抽样。论文还用相同切分构造了平衡 IID 版本，同为 1146 个客户端。模型为字符级 LSTM，2 层各 256 节点，嵌入维度 8。

CIFAR-10 设置：10 类 32x32 RGB 图像，50,000 训练与 10,000 测试，划分到 100 个客户端，每客户端 500 训练与 100 测试，采用平衡 IID 设置。模型来自 TensorFlow 教程，约 10 的 6 次方个参数。结果见 Table 3：标准 SGD 达到 80%、82%、85% 精度分别需要 18000、31000、99000 轮；FedSGD 分别需要 3750 轮（4.8 倍）、6600 轮（4.7 倍）和未达到；FedAvg 分别需要 280 轮（64.3 倍）、630 轮（49.2 倍）、2000 轮（49.5 倍）。正文另述标准 SGD 在 197,500 次 minibatch 更新后达到 86% 测试精度，FedAvg 在 2000 轮后达到 85%。

大规模语言模型设置：1000 万条公开帖子按作者分组，超过 500,000 个客户端，每客户端至多 5000 词，测试集为 1e5 条来自非训练作者的帖子，指标为 10000 类下一词预测的 top-1 精度。所有运行每轮训练 200 个客户端，FedAvg 使用 B 等于 8、E 等于 1。FedSGD 在 η 等于 18.0 时需要 820 轮达到 10.5% 精度，FedAvg 在 η 等于 9.0 时只需 35 轮（少 23 倍）。Figure 10 显示 FedAvg 在 E 等于 1 时优于 E 等于 5，且精度方差更低。

恶意比例：论文未说明，论文没有设置任何恶意客户端。数据是否非独立同分布：MNIST 同时评估了 IID 与病态非 IID，莎士比亚的主实验是不平衡且非 IID 的（并给出 IID 对照），CIFAR-10 与大规模语言模型实验是非 IID（后者按作者分组，本身即为非 IID 的真实划分）。指标：达到目标测试精度所需通信轮数、测试精度随通信轮数的曲线、训练损失，CIFAR-10 实验还使用 minibatch 梯度计算次数作为横轴。

## 8. 开销

论文报告的主要开销指标是通信，摘要称相比同步随机梯度下降把所需通信轮数降低 10 到 100 倍。正文把通信列为主要约束，并假设上传带宽通常在 1 MB/s 或更低，客户端只在充电、接入不计费 Wi-Fi 时参与，且每天只参与少量轮次。论文称由于单设备数据量小、手机处理器较快，计算相对通信"essentially free"，因此目标是增加计算以减少通信轮数；论文把增加并行度（更多客户端）与增加每客户端计算量作为两条路径，并指出加速主要来自后者。

论文未报告每轮传输的字节数、墙钟时间、内存或存储开销。Table 1 的说明提到五组大 batch 设置在允许时间内未能达到目标精度，属于计算时间受限的定性说明。论文未报告差分隐私（differential privacy）或安全多方计算（secure multi-party computation）的开销，因为这些机制被列为未来工作而未实现。

## 9. 假设、局限与自适应攻击

论文成立所依赖的假设。第一，客户端数据非独立同分布（non-IID）、不平衡、参与方数量远大于单客户端样本数、通信受限，这四条被论文列为联邦优化的定义性属性。第二，同步更新方案，按通信轮次推进。第三，存在固定的 K 个客户端，每个客户端持有固定的本地数据集。第四，每轮随机选取比例为 C 的客户端参与。第五，服务器持有并下发全局状态。第六，每轮所有被选中客户端都正确完成本地计算并返回更新，共享同一初始模型 w_t。第七，仍需要在一定程度上信任服务器。第八，隐私收益是定性论证，论文明确把更强保证（差分隐私、安全多方计算及其组合）列为未来工作。

论文自述的局限。客户端数据集会随数据增删而变化；客户端可用性与本地数据分布以复杂方式相关；从不响应或发送损坏更新的客户端属于需要处理但本文范围之外的问题；论文使用受控实验环境而非真实部署。此外论文在 Figure 3 报告大 E 会导致停滞或发散，在 Figure 10 报告 E 等于 5 略差于 E 等于 1。

是否评估了自适应攻击者：否。论文没有评估任何攻击者，包括自适应攻击者，全文没有攻击实验。

迁移到联邦大模型 LoRA 微调时可能失效的假设，以下均为分析。第一，参数空间平均依赖于各客户端模型结构完全相同且共享同一初始化，Figure 1 显示不同初始化下的平均会产生很差的模型；LoRA 适配器的 A、B 两个低秩矩阵存在重参数化不变性，同一个功能可由无穷多组因子表示，直接对因子做加权平均与对等效全量权重做平均并不等价。第二，论文的聚合权重取客户端自报的本地样本数 n_k，而论文没有校验机制，在 LoRA 场景中恶意客户端可以虚报该数值以放大自身影响，这一信任假设在防护库中必须替换为可验证的权重或鲁棒的聚合规则。第三，论文的隐私论证建立在"更新包含的信息不多于原始数据且通常远少于原始数据"这一信息论直觉上，脚注 1 自己也承认稀疏特征下梯度会直接暴露输入词；在文本生成任务上，LoRA 增量对训练样本的记忆更容易被提取，隐私假设更弱。第四，论文的"通信受限"前提在数据中心内的联邦 LoRA 训练中通常不成立，适配器文件本就不大，用本地步数换通信轮数的动机减弱，而论文没有讨论通信之外的开销。第五，论文完全没有考虑对抗行为，其同步、随机选取、直接平均的流程在存在投毒客户端时会被直接污染，且"从不响应或发送损坏更新"被明确排除在范围外。第六，论文的模型是 LSTM 与小型卷积网络，其损失面平滑性论证被用来支持参数平均，这一论证是否适用于大规模 Transformer 的 LoRA 因子，论文未说明。

## 10. 对防护库设计的含义

分析：采集底座需要提供的最通用视图是"服务器收到更新时"的逐客户端、逐轮、逐层参数张量与客户端上报的样本数 n_k，这是本论文唯一明确写出的信任边界数据流，也是几乎所有投毒检测插件的共同输入。论文中该数据天然存在，不需要额外计算。

分析：底座需要为每个客户端保留"训练前全局模型快照与训练后本地更新的配对"，因为本论文方法成立的关键是每轮共享同一初始模型 w_t。若插件要判断更新方向是否异常或是否偏离全局梯度，必须能取到这一配对，而不是只看到更新本身。这属于通用需求。

分析：服务器聚合钩子需要把"按样本数加权平均"实现为可替换的聚合接口，默认实现即 Algorithm 1 的加权求和，防御插件可以在同一钩子上做剔除、重新加权或裁剪而不改动底座。这是本论文特有的语义（权重来自 n_k），但接口本身是通用的。

分析：本论文不提供任何检测信号、不提供逐样本损失或激活、不需要干净根数据集、不需要跨轮历史之外的额外数据，因此在防护库中它应当被登记为"基础方法与基线"，用于提供聚合语义、超参数记录（C、E、B、u）与无攻击条件下的收敛基线，而不是作为一个检测或防御插件。

分析：论文把客户端不响应与发送损坏更新列为范围之外，因此防护库必须自行定义缺失更新、超时、重复提交与格式非法更新的处理语义，并明确这些语义属于底座而非插件，否则无法把论文的加权平均直接落到工程实现上。

分析：论文的隐私讨论提示底座应当记录更新内容的敏感度边界（例如稀疏特征下的梯度泄露），但论文没有给出任何相应的干预手段；若防护库要对 LoRA 更新做隐私检测，需要额外采集逐样本梯度或逐样本损失，这些采集点在本论文中并不存在，属于库需要自行新增的能力。

## 11. 原文依据

1. 章节：Abstract。支撑第 1 节"论文类型为基础方法、评估五种架构与四个数据集"。
"We present a practical method for the federated learning of deep networks based on iterative model averaging, and conduct an extensive empirical evaluation, considering five different model architectures and four datasets."

2. 章节：1 Introduction。支撑第 2 节"客户端数据不上传，服务器只收到更新"这一信任边界。
"Each client has a local training dataset which is never uploaded to the server. Instead, each client computes an update to the current global model maintained by the server, and only this update is communicated."

3. 章节：1 Introduction。支撑第 2 节"仍需要在一定程度上信任服务器"与"攻击面收窄到设备端"。
"Clearly, some trust of the server coordinating the training is still required. However, for applications where the training objective can be specified on the basis of data available on each client"

4. 章节：1 Introduction 的 Federated Optimization 小节。支撑第 7 节与第 9 节"固定客户端集合、固定本地数据集、每轮随机选取比例 C 的同步协议"。
"There is a fixed set of K clients, each with a fixed local dataset. At the beginning of each round, a random fraction C of clients is selected"

5. 章节：2 The FederatedAveraging Algorithm。支撑第 3 节与第 6 节"客户端本地走一步、服务器做加权平均"这一聚合位置。
"each client locally takes one step of gradient descent on the current model using its local data, and the server then takes a weighted average of the resulting models"

6. 章节：2 The FederatedAveraging Algorithm。支撑第 4 节与第 7 节"三个控制参数 C、E、B"。
"C, the fraction of clients that perform computation on each round; E, then number of training passes each client makes over its local dataset on each round"

7. 章节：1 Introduction 的 Federated Optimization 小节。支撑第 2 节与第 3 节"论文承认存在不响应或损坏更新，但明确排除在范围外"，以及第 9 节的局限。
"A deployed federated optimization system must also address a myriad of practical issues: client datasets that change as data is added and deleted; client availability that correlates with the local data distribution in complex ways"

8. 章节：1 Introduction 的 Privacy 小节脚注 1。支撑第 5 节"梯度是可观测量且会泄露本地输入"这一采集点依据。
"if the update is the total gradient of the loss on all of the local data, and the features are a sparse bag-of-words, then the non-zero gradients reveal exactly which words the user has entered on the device"

9. 章节：1 Introduction 的 Privacy 小节脚注 1。支撑第 9 节"论文承认隐私收益是定性的，攻击仍然可能"。
"the sum of many gradients for a dense model such as a CNN offers a harder target for attackers seeking information about individual training instances (though attacks are still possible)"

10. 章节：4 Conclusions and Future Work。支撑第 8 节与第 9 节"差分隐私与安全多方计算只是未来工作，论文未实现也未报告其开销"。
"While federated learning offers many practical privacy benefits, providing stronger guarantees via differential privacy, secure multi-party computation, or their combination is an interesting direction for future work."

```json
{
  "key": "mcmahan2017fedavg",
  "title": "Communication-Efficient Learning of Deep Networks from Decentralized Data",
  "year": 2017,
  "paper_type": "foundation",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["none"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "客户端本地数据集与标签 P_k", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "服务器下发的全局模型参数 w_t", "where": "client_pre_train", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "本地 minibatch 损失梯度", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "客户端返回的本地模型参数 w_{t+1}^k", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "客户端上报的本地样本数 n_k", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每客户端每轮本地更新次数 u_k = E*n_k/B", "where": "client_post_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "聚合后的全局模型 w_{t+1}", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "客户端数据非独立同分布且不平衡，参与方数量远大于单客户端样本数，通信是主要瓶颈",
    "采用同步通信轮次的更新方案",
    "存在固定的 K 个客户端，每个客户端持有固定的本地数据集",
    "每轮随机选取比例为 C 的客户端参与",
    "每轮所有被选中客户端正确完成本地训练并返回更新，且共享同一初始模型 w_t",
    "仍需在一定程度上信任协调训练的中央服务器",
    "隐私收益是定性论证，差分隐私与安全多方计算属于未来工作"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第1节 论文类型为基础方法、评估五种模型架构与四个数据集", "text": "We present a practical method for the federated learning of deep networks based on iterative model averaging, and conduct an extensive empirical evaluation, considering five different model architectures and four datasets."},
    {"section": "1 Introduction", "supports": "第2节 客户端数据不上传、服务器只收到更新这一信任边界", "text": "Each client has a local training dataset which is never uploaded to the server. Instead, each client computes an update to the current global model maintained by the server, and only this update is communicated."},
    {"section": "1 Introduction", "supports": "第2节 仍需要信任服务器、攻击面收窄到设备端", "text": "Clearly, some trust of the server coordinating the training is still required. However, for applications where the training objective can be specified on the basis of data available on each client"},
    {"section": "1 Introduction, Federated Optimization", "supports": "第7节与第9节 固定客户端集合、固定本地数据集、每轮随机选取比例 C 的同步协议", "text": "There is a fixed set of K clients, each with a fixed local dataset. At the beginning of each round, a random fraction C of clients is selected"},
    {"section": "2 The FederatedAveraging Algorithm", "supports": "第3节与第6节 客户端本地一步、服务器加权平均的聚合位置", "text": "each client locally takes one step of gradient descent on the current model using its local data, and the server then takes a weighted average of the resulting models"},
    {"section": "2 The FederatedAveraging Algorithm", "supports": "第4节与第7节 三个控制参数 C、E、B", "text": "C, the fraction of clients that perform computation on each round; E, then number of training passes each client makes over its local dataset on each round"},
    {"section": "1 Introduction, Federated Optimization", "supports": "第2节、第3节与第9节 论文承认存在不响应或损坏更新但明确排除在范围外", "text": "A deployed federated optimization system must also address a myriad of practical issues: client datasets that change as data is added and deleted; client availability that correlates with the local data distribution in complex ways"},
    {"section": "1 Introduction, Privacy, footnote 1", "supports": "第5节 梯度是可观测量且会泄露本地输入", "text": "if the update is the total gradient of the loss on all of the local data, and the features are a sparse bag-of-words, then the non-zero gradients reveal exactly which words the user has entered on the device"},
    {"section": "1 Introduction, Privacy, footnote 1", "supports": "第9节 论文承认隐私收益是定性的、攻击仍然可能", "text": "the sum of many gradients for a dense model such as a CNN offers a harder target for attackers seeking information about individual training instances (though attacks are still possible)"},
    {"section": "4 Conclusions and Future Work", "supports": "第8节与第9节 差分隐私与安全多方计算只是未来工作，未实现也未报告开销", "text": "While federated learning offers many practical privacy benefits, providing stronger guarantees via differential privacy, secure multi-party computation, or their combination is an interesting direction for future work."}
  ]
}
```
