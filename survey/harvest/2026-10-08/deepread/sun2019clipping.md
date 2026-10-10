# sun2019clipping：Can You Really Backdoor Federated Learning?

## 1. 基本信息

- **场景**：传统联邦学习（classic federated learning）中的跨设备（cross-device）图像分类任务，数据集是 EMNIST（按书写者划分、天然非独立同分布 non-iid）。论文不使用大语言模型，不涉及联邦大模型微调，也不涉及 LoRA 或任何参数高效微调（parameter-efficient fine-tuning, PEFT）；实现基于 TensorFlow Federated（TFF）。
- **训练阶段**：客户端本地训练（local training）加服务器聚合（server aggregation），聚合式为带服务器学习率 η 的样本数加权平均（第 2 节）。
- **论文类型**：以攻击为主的实证研究，同时系统评估了两类防御（范数裁剪与弱差分隐私），并开源 TFF 实现、鼓励在同一标准任务上评估新攻击与新防御，因此带有基准或平台（benchmark/platform）性质。本文在 JSON 中归类为 attack。
- **模型与数据规模**：EMNIST 手写数字数据集，来自 3383 个用户（writer），每用户约 100 张图像；模型是五层卷积神经网络（两个卷积层、一个最大池化层、两个全连接层）；每轮选择 C·K = 30 个客户端；每个客户端本地训练 5 个 epoch，批大小（batch size）20，客户端学习率 0.1，服务器学习率 1（第 5 节）。实验曲线横轴到 300 轮（Figure 1 至 Figure 6）。论文脚注 2 设想更现实的移动场景可能有 K = 10^7 或更高的用户数，每轮选中的客户端数 C·K 通常为常数，例如 100 到 1000。

## 2. 威胁模型

- **攻击者是谁**：被完全攻陷的客户端（fully compromised clients），即恶意客户端。论文实验考察的恶意比例 ε 为 3.3%、1.1%、0.67%、0.33%，分别对应 113、38、23、11 个攻击者（Figure 1、Figure 2、Figure 5、Figure 6 的子图标题）。
- **参与模式**：论文定义两种。第一种是随机采样攻击（random sampling attack），每轮出现的恶意客户端数服从超几何分布（hypergeometric distribution），取值在 0 到 min(ε·K, C·K) 之间；第二种是固定频率攻击（fixed frequency attack），单个攻击者每 f 轮出现一次，f = 1/(ε·C·K)，即出现频率与攻击者总数成反比（第 2 节）。
- **能力（能改什么）**：因为本地训练过程完全被攻陷，"被完全攻陷的客户端可以完全改变模型更新"（第 1 节），所以这不是数据投毒（data poisoning）而是模型更新投毒（model update poisoning，又称 model poisoning）。攻击者可以任意构造上传的更新向量；可以用自己的数据在全局模型基础上训练出后门模型 w*；可以按放大因子（boost factor）β = Σ_{k∈S_t} n_k /(η n_k) 放大更新，即公式 (1) 的 ∆w^1_t = β(w* − w_t)；同一轮有多个攻击者时，论文假设它们能互相协调并把该更新均分（第 3 节）。
- **知识（知道什么）**：攻击者知道当前全局模型 w_t（用它来初始化后门模型）；持有描述后门任务的数据集 D_mal 与来自真实分布 D_trn 的训练样本；在防御分析中，论文额外假设"攻击者知道阈值 M，因此总能返回幅度在这个范围内的恶意更新"（第 4 节）。论文未说明攻击者如何得知服务器学习率 η、参与客户端的样本总数 Σ n_k、参与率 C 等聚合细节（分析：模型替换的放大因子依赖这些量，但论文没有讨论它们的可获知性）。
- **目标**：定向后门（targeted backdoor）。攻击者要让模型在特定子任务上失败，同时保持主任务（primary task）的良好性能；实验中的后门任务是把来自若干"目标客户端"（target clients）的数字 7 分类为 1（第 5 节）。论文不研究无目标破坏、越狱或安全对齐破坏、隐私攻击，这些只在第 1 节作为背景分类提及。
- **防御者是谁、能看到什么、信任什么**：防御者是服务提供方（服务器）。在未部署安全聚合（secure aggregation, SecAgg）时，服务器能看到每个客户端上传的更新，并据此做范数阈值、裁剪与加噪。论文强调两点限制：部署 SecAgg 后"服务器无法检查每个用户的更新"，模型更新投毒更难防御（第 1 节）；已有的后门防御要么需要仔细检查训练数据，要么需要服务器完全控制训练过程，这在联邦学习中可能不适用（第 1 节）。论文还允许非恶意客户端持有后门任务的正确标注样本，它们能在后续轮次用这些样本纠正被攻击的模型（第 2 节）。论文未明确陈述"多数客户端良性"这一假设（分析：实验中最坏情形只有 3.3% 的客户端被攻陷，实际上预设了绝大多数客户端是良性的）。

## 3. 攻击入口与流程位置

攻击内容进入的位置有两处，都在客户端一侧：

1. **本地训练过程**：攻击者以当前全局模型 w_t 为初始化，在 D_trn ∪ D_mal 上训练若干 epoch，得到后门模型 w*（第 3 节"无约束 boost 后门攻击"）。
2. **更新上传前的后处理**：把本地更新放大为 ∆w^1_t = β(w* − w_t)，β = Σ_{k∈S_t} n_k /(η n_k)（公式 (1)）。为规避范数防御，还有范数受限版本：训练时约束更新范数小于 M/β，用多轮投影梯度下降实现，使 boost 之后的更新范数不超过 M（第 3 节）。

攻击的"生效点"在服务器聚合（server aggregation）：代入聚合式后得到 w_{t+1} ≈ w*，即用恶意更新替换掉整个模型。论文不是数据准备阶段的数据投毒（第 1 节明确区分 data poisoning 与 model update poisoning），也不涉及全局模型下发、评估或部署阶段。

具体操作步骤（第 2、3 节）：

1. 第 t 轮，攻击者被服务器选中；模型替换范式假设这一轮只有它一个攻击者，且不失一般性设为客户端 1。
2. 以 w_t 初始化，在 D_trn ∪ D_mal 上训练若干 epoch 得到 w*；无约束版本直接使用该模型，范数受限版本则把更新投影回以 w_t 为中心、半径 M/β 的 ℓ2 球。
3. 上传 ∆w^1_t = β(w* − w_t)。
4. 服务器按 w_{t+1} = w_t + η Σ_{k∈S_t} n_k ∆w^k_t / Σ_{k∈S_t} n_k 聚合；论文指出，其效果是"如果假设模型已充分收敛、其他客户端的更新 ∆w^k_t（k > 1）很小"，聚合结果会落在 w* 的小邻域内（第 3 节）。
5. 同一轮有多个攻击者时，它们把该更新均分（第 3 节）。

论文未说明模型尚未收敛的早期轮次攻击是否仍有效，也没有对这一前提做消融（分析：这是模型替换范式的隐含前提，且它直接决定了攻击能否在训练早期或异构客户端分布下奏效）。

## 4. 方法原理

**核心思想**：沿用模型替换（model replacement）范式，用一个被放大的、指向后门模型的更新，在样本数加权平均中抵消掉其他客户端的贡献。公式 (1) 给出 ∆w^1_t = β(w* − w_t)，β = Σ_{k∈S_t} n_k /(η n_k) 是放大因子（第 3 节）。

**两类攻击**：

- 无约束 boost 后门攻击：以 w_t 初始化，在 D_trn ∪ D_mal 上训练几个 epoch，直接上传放大后的更新；通常产生很大的更新范数，作为基线（第 3 节）。
- 范数受限后门攻击：约束"boost 之前"的更新范数小于 M/β，从而 boost 之后范数不超过 M；实现方式是"多轮投影梯度下降（projected gradient descent），每一轮先用无约束策略训练，再投影回以 w_t 为中心、半径 M/β 的 ℓ2 球"（第 3 节）。其目的就是绕过范数阈值防御。

**两类防御**：

- 更新范数阈值（norm thresholding）：服务器直接忽略范数高于阈值 M 的更新。由于论文假设攻击者知道 M 并能把更新控制在 M 以内，阈值化与下面的范数裁剪在效果上等价（第 4 节）。范数裁剪（norm clipping）的写法是：每个更新先除以 max(1, ||∆w^k_{t+1}||_2/M)，再求和成新的模型更新，从而保证每个更新的范数都很小。
- 弱差分隐私（weak differential privacy）：先裁剪更新，再对聚合结果加高斯噪声。论文明确说明加噪的目的不是隐私，而是限制攻击成功率，因此噪声量远小于真正满足差分隐私所需的量（第 4 节）。论文不给出范数界与噪声方差的选取配方（第 5 节）。

## 5. 检测或防御所需的数据

**防御侧需要的输入**

1. **逐客户端的模型更新向量（或其 ℓ2 范数）**
   - 是什么：第 t 轮客户端 k 提交的更新 ∆w^k_t；用于计算 ℓ2 范数，进而做阈值丢弃或按 M 缩放。
   - 在哪里采集：服务器收到更新时、聚合之前（server_receive）。
   - 粒度：逐客户端、逐轮。
   - 是否需要跨轮历史、干净参考数据、额外前向或反向计算、其他客户端的数据：都不需要；这是逐轮、逐更新的确定性变换。
2. **范数阈值或裁剪界 M**
   - 是什么：一个标量超参数，论文取 3、5、10，对应 boost 之前的更新范数界 0.1、0.17、0.33（第 5 节，Figure 4(a)）。
   - 在哪里采集：不是从数据采集，而是部署者在服务器聚合前设定；论文给出的经验参考是"多数轮次里良性客户端更新的第 90 百分位低于 2"（第 5 节）。
   - 粒度：全局单一标量；论文未讨论逐层、逐客户端或分组阈值。
   - 是否需要跨轮历史、干净参考数据、额外计算：论文未说明其标定流程；分析：若要复现这条经验依据，需要跨轮、跨客户端的更新范数统计，并且隐含"知道或假定哪些客户端是良性的"，但论文并没有把它做成一个自动的标定算法。
3. **高斯噪声的方差**
   - 是什么：加在裁剪后更新每个坐标上的独立高斯噪声的方差，论文取 0.025（第 5 节，Figure 4(b)：红色 σ = 0，绿色 σ = 0.025，蓝色为未受攻击基线）。
   - 在哪里采集：不是采集量，而是服务器聚合时的超参数。
   - 粒度：逐坐标、逐轮。
   - 是否需要历史、干净参考数据、额外计算：都不需要。
4. **聚合权重 n_k（客户端样本数）**
   - 是什么：客户端本地样本数，服务器做加权平均本来就需要的量（第 2 节）。
   - 在哪里采集：服务器聚合时；粒度：逐客户端、逐轮。
   - 裁剪与加噪不改变这一权重，也不引入新的客户端侧数据需求。

论文明确不使用的数据：逐样本损失、逐批统计、隐藏层激活、输出文本、客户端内部梯度、逐层范数、客户端本地数据、其他客户端的数据、跨轮更新历史（范数裁剪与加噪都是记忆less 的逐轮处理）。论文也没有提出任何"识别谁是恶意客户端"的检测器。

**攻击侧：留下哪些痕迹、声称能绕过哪些检测**

- 无约束 boost 攻击最直接的痕迹是更新范数异常大，论文正是以此作为范数防御的动机（第 4 节）。
- 范数受限攻击刻意规避范数阈值：论文假设攻击者知道 M，把 boost 前的更新范数压到 M/β 以内，因此论文把阈值防御与裁剪防御视为等价（第 4 节）。
- 论文声称范数裁剪与小高斯噪声能缓解这两类攻击（第 4、5 节）；论文没有评估针对这两类防御进一步自适应的攻击，反而在第 6 节把"直接构造满足范数约束的最坏情况更新"和"多轮攻击策略"列为未解决的问题。
- 结构性盲区：部署 SecAgg 时服务器无法检查单个客户端的更新（第 1 节），论文把范数约束与 SecAgg 的兼容性（需要高效的多方范围证明）列为开放问题（第 6 节）。

## 6. 干预动作

- **阈值丢弃**：服务器直接忽略范数高于 M 的更新（第 4 节）。这相当于该客户端本轮贡献被置零，但论文并未提出跨轮封禁客户端。
- **范数裁剪**：把每个更新按 max(1, ||∆w||_2/M) 缩放后再聚合成新模型更新（第 4 节）。
- **加噪**：在裁剪之后对聚合更新逐坐标加独立高斯噪声（第 4、5 节）。

以上动作都发生在服务器侧、聚合前后，即"服务器收到更新之后、聚合产生新全局模型之前/之中"。

论文没有做以下任何一件事：剔除客户端（除阈值隐含的本轮丢弃外）、重新加权、过滤训练样本、修复或回滚模型、仅报告告警、输出恶意客户端身份。两种防御都是对更新幅度的后处理，不产生"谁是攻击者"的判断；论文也不提供范数界与噪声方差的选取方法（第 5 节）。

## 7. 实验设置与主要结果

**设置**

- 数据：EMNIST，3383 个用户，每用户约 100 张图，按书写者划分因此是非独立同分布（摘要称其为"真实、按用户划分且非独立同分布的数据集"）。
- 模型：五层卷积神经网络（两个卷积层、一个最大池化层、两个全连接层），TFF 实现（第 5 节）。
- 联邦参数：每轮 C·K = 30 个客户端，本地 5 个 epoch，批大小 20，客户端学习率 0.1，服务器学习率 1（第 5 节）；曲线到 300 轮。
- 后门任务：把若干目标客户端的数字 7 分类为 1；Figure 1 和 Figure 2 使用 30 个后门任务（约 300 张图像），Figure 3 比较 10、20、30、50 个后门任务（第 5 节）。
- 恶意比例：3.3%、1.1%、0.67%、0.33%（Figure 1、Figure 2、Figure 5、Figure 6）。
- 指标：主任务准确率、后门任务准确率，以及后门准确率的累计均值（图中绿色曲线）。

**主要结果**

- 随机采样攻击与固定频率攻击行为相近，固定频率攻击略更有效，因此后续分析采用固定频率攻击（第 5 节；Figure 1、Figure 2）。
- 攻击成功率很大程度上取决于恶意客户端比例；当被完全攻陷的用户比例低于 1% 时后门攻击性能下降（第 5 节；Figure 1、Figure 2 及附录 Figure 5、Figure 6）。论文在第 6 节总结说，要想取得合理成功率"需要有大量的攻击者"。
- 后门任务数越多，越难在保持主任务性能的同时拟合恶意模型（第 5 节；Figure 3 的 10、20、30、50 四组）。
- 无约束攻击范数很大；采用范数受限攻击且界为 10 时，攻击仍然相当有效（Figure 2）。作为防御，选择 3 作为范数界"能成功缓解攻击，并且几乎不影响主任务性能"（第 5 节；Figure 4(a)）；作为参照，多数轮次里良性客户端更新的第 90 百分位低于 2（第 5 节）。
- 弱差分隐私：在范数界 5（论文说这个界本身不足以缓解攻击）之上，对每个坐标加方差 0.025 的独立高斯噪声，可以在不太损害整体性能的前提下进一步缓解攻击（第 5 节；Figure 4(b)）。

## 8. 开销

论文未报告计算、通信或存储开销的数值，没有 FLOPs、通信字节数、内存占用或墙钟时间。可引用的只有训练超参数（每轮 30 个客户端、本地 5 个 epoch、批大小 20）和攻击侧的定性描述：无约束攻击要在 D_trn ∪ D_mal 上多训练几个 epoch，范数受限攻击需要"多轮投影梯度下降"，即攻击者需要更多本地计算（第 3 节）。防御侧论文只描述裁剪与加噪的做法，没有给成本数据。分析：范数裁剪只需对每个更新做一次 ℓ2 范数计算，加噪只需逐坐标采样，两者都在服务器聚合前后完成，相对模型训练可以忽略；但这是分析，不是论文报告的结论。第 6 节还指出，要在 SecAgg 下实现范数约束需要高效的多方范围证明（range proof），论文点名 BulletProof 一类方案，并把高效实现列为活跃的研究方向，这属于尚未解决的效率问题而非实测开销。

## 9. 假设、局限与自适应攻击

**论文成立所依赖的假设**

- 模型在被攻击的轮次"已充分收敛"，其他客户端的更新足够小，因此被放大的更新能把全局模型带到 w* 附近（第 3 节）。
- 攻击者拥有描述后门任务的数据集 D_mal，以及来自真实分布 D_trn 的训练样本；论文自述"在实际应用中，这类数据可能更难获得"（第 3 节）。
- 与之前的工作不同，论文允许非恶意客户端持有后门任务的正确标注样本，它们会用这些样本纠正被攻击的模型（第 2 节）。
- 同一轮出现多个攻击者时，它们能互相协调并均分替换更新（第 3 节）。
- 防御侧假设攻击者知道范数阈值 M，因此阈值化等价于裁剪（第 4 节）；在这一假设下，防御只能靠把幅度压小来削弱攻击，而不是靠识别异常。
- SecAgg 与范数约束的兼容性依赖高效的多方范围证明，论文认为这不成熟（第 6 节）。

**论文自述的局限**

- 不提供范数界与噪声方差的选取方法，只展示"由差分隐私文献启发的合理取值"有效，并说"发现学习这些界与噪声值的算法仍是有趣的开放研究方向"（第 5 节）。
- 在范数受限情形下，多轮"pre-boosted"投影梯度下降未必是单轮最优攻击；攻击者可能直接构造满足范数约束的最坏情况更新；如果攻击者知道自己可以攻击多轮，可能存在更好的策略。更强的防御也有待研究（第 6 节）。
- 模型容量与后门攻击的交互（后门攻击可能利用深度网络的空闲容量这一猜想）是开放问题（第 6 节）。
- 与 SecAgg 的交互需要高效的多方范围证明（第 6 节）。

**是否评估了自适应攻击者**：论文在防御侧主动给攻击者一个强假设——知道阈值 M，并据此构造范数受限攻击专门规避范数裁剪，论文自己称之为"给攻击者很强的优势"（第 4 节）。因此针对范数裁剪的自适应规避是评估过的，本文在 JSON 中记为 true。但边界要说清：论文没有评估针对弱差分隐私加噪的自适应规避，也没有实现更强的最坏情况更新或多轮攻击，这些被明确留作未来工作（第 6 节）。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）**

- 分析：本文是传统联邦学习加五层卷积网络，不是联邦大模型，也不涉及 LoRA 或 PEFT。它观测和裁剪的对象是完整模型更新向量 ∆w；LoRA 客户端上传的是低秩增量（通常是 A、B 两个矩阵或它们的乘积 BA）。裁剪 A、B 因子与裁剪乘积 BA 给出的几何约束不同，论文完全没有讨论这种参数化差异，因此"裁剪哪个张量、按什么粒度裁剪"需要重新定义。
- 分析：放大因子 β = Σ n_k /(η n_k) 依赖服务器学习率、按样本数的聚合权重和参与客户端的样本总量。联邦大模型微调的聚合常按 token 数或均匀加权，可能存在逐层或分组归一化，本地步数与学习率调度也完全不同；不重新推导 β，模型替换攻击不一定能生效，反过来防御的阈值 M 也不能照搬。
- 分析：本文的后门任务是同一数据集内的一个小子任务（把 7 判成 1），而且非恶意客户端持有该子任务的正确标注样本，会持续把模型拉回来，这正是"后门任务越多越难攻击"这一结论的机制之一。大模型 LoRA 场景中的后门通常是触发短语对应攻击者指定的输出，良性客户端并不持有触发样本，"良性客户端自动纠正"很可能不存在，攻击可能更容易得手。
- 分析：论文的范数参照（良性更新第 90 百分位低于 2）来自五层卷积网络、每客户端约 100 个样本、5 个本地 epoch 的设定。LoRA 增量的量级随秩 r、目标模块、初始化方式（例如 B 初始化为零）、学习率和本地步数变化，没有可直接移植的阈值；库必须提供按部署标定 M 的接口，而论文没有给配方。
- 分析：本文的两个防御都依赖服务器能看到"单个客户端的更新"这一可观测量，天然与安全聚合冲突。若联邦 LoRA 管线启用安全聚合，就必须引入范围证明等密码学手段，论文对此只说这是开放方向，没有给出可实施方案。
- 分析：论文完全不涉及文本生成、分词器、提示分布、输出文本或逐样本损失，因此基于生成文本、困惑度或激活的检测插件在本文中没有任何依据；能迁移的只有"服务器端、逐轮、逐客户端、无历史的更新范数视图"这一条。
- 分析：论文的规模（3383 个用户、每轮 30 个客户端、300 轮、五层卷积网络）与大模型训练的算力和参与规模差异巨大；论文只在脚注中设想 K 可达 10^7、每轮 100 到 1000 个客户端，实验并未在该量级验证，高度异构（不同客户端数据量不同、LoRA 秩不同）时范数阈值是否仍有效，论文未说明。

## 10. 对防护库设计的含义

- 分析：采集点方面，本文只需要服务器钩子在"收到更新时"提供逐客户端、逐轮的原始更新向量（或其 ℓ2 范数），不需要客户端钩子、逐样本数据、激活或跨轮历史。这是最省的采集需求，但底座必须把"未聚合的原始客户端更新"作为一等数据视图，并显式标注该视图是否可用（即是否启用了安全聚合）。
- 分析：标定视图方面，裁剪与加噪需要两个超参数（范数界 M 与噪声方差），论文没有给出学习算法，只给了经验值（M 取 3、5、10，对应 boost 前的 0.1、0.17、0.33；噪声方差 0.025；良性更新第 90 百分位低于 2 作为动机）。库需要提供"良性更新的范数分布统计"这类跨轮、跨客户端的聚合视图作为标定输入，并允许插件在拿不到干净参考时退化为纯阈值规则。
- 分析：干预接口方面，需要三个服务器钩子：聚合前的逐更新裁剪或本轮丢弃、聚合时的加噪、以及把两者串联的开关；动作都发生在"服务器收到更新之后、全局模型下发之前"，不需要客户端侧动作，也不需要修复或回滚模型。
- 分析：LoRA 适配方面，库必须显式定义裁剪的粒度与张量视图（逐层 A/B 因子、逐层乘积 BA，还是把所有增量拼接成单一向量），并为 LoRA 的秩、目标模块和聚合权重提供可配置的归一化；论文的单一全局 ℓ2 界在 PEFT 下需要重新参数化。
- 分析：通用与特有之分。通用的是"服务器端可插拔的逐客户端更新后处理"钩子、超参数标定接口和记录每轮是否裁剪或加噪的审计日志；本文特有且与具体攻击无关的是范数裁剪加弱差分隐私这一组算法，它们非常适合作为默认的兜底鲁棒聚合插件。
- 分析：评测与红队方面，采集底座应支持在客户端钩子上挂红队插件，复现本文的无约束 boost 攻击与范数受限投影梯度下降攻击，并暴露恶意比例 ε、后门任务数、范数界 M 三个旋钮；同时要能复现"良性客户端持有后门任务正确标注样本"这一数据条件，否则会高估攻击成功率。论文关于 SecAgg 的讨论还提示库需要一条"更新不可见"的执行路径，用来标记哪些防御在启用安全聚合时自动失效（只能报告或拒绝加载）。

## 11. 原文依据

1. **章节**：Abstract。**支撑**：第 2 节攻击目标（定向后门，保持主任务性能）；第 1 节论文类型。
   > "This paper focuses on backdoor attacks in the federated learning setting, where the goal of the adversary is to reduce the performance of the model on targeted tasks while maintaining a good performance on the main task."
2. **章节**：Section 1 (Introduction)。**支撑**：第 2 节攻击者能力与第 3 节攻击入口（完全攻陷客户端可以完全改变模型更新，属于模型更新投毒而非数据投毒）。
   > "In federated learning systems, since the training process is done on local devices, fully compromised clients can change the model update completely, which is called a model poisoning attack (3; 4)."
3. **章节**：Section 2 (Backdoor Attack Scenario)。**支撑**：第 2 节与第 9 节的关键假设（非恶意客户端持有后门任务的正确标注样本，会纠正被攻击的模型）。
   > "Unlike (3; 4), we allow non-malicious clients to have correctly labeled samples from the targeted backdoor tasks."
4. **章节**：Section 3 (Model Update Poisoning Attacks)。**支撑**：第 5 节防御所需数据之外的攻击者数据条件，以及第 9 节论文自述的局限（真实分布样本在实践中可能更难获得）。
   > "We also assume the attacker has a set of training samples generated from the true distribution Dtrn. Note that for practical applications, such data may be harder for the attacker to obtain."
5. **章节**：Section 3 (Model Update Poisoning Attacks)。**支撑**：第 4 节方法原理与第 5 节攻击规避范数阈值的机制（boost 前约束在 M/β 以内，boost 后不超过 M）。
   > "Here at each round, the model trains on the backdoor task subject to the constraint that the model update is smaller than M/β. Thus, model update has norm bounded by M after boosted by a factor of β."
6. **章节**：Section 4 (Defenses)。**支撑**：第 6 节干预动作（服务器直接忽略范数高于 M 的更新，阈值化与裁剪等价）。
   > "Since boosted attacks are likely to produce large norms, a reasonable defense is for the server to simply ignore updates whose norm is above some threshold M"
   
   （提示：原文该句为 "Since boosted attacks are likely to produce updates with large norms, a reasonable defense is for the server to simply ignore updates whose norm is above some threshold M"，此处按原文誊录如下）
   > "Since boosted attacks are likely to produce updates with large norms, a reasonable defense is for the server to simply ignore updates whose norm is above some threshold M"
7. **章节**：Section 4 (Defenses)。**支撑**：第 9 节自适应攻击评估的边界（论文假设攻击者知道阈值 M，这是针对裁剪防御的规避；也是"给攻击者很强优势"的来源）。
   > "However, in the spirit of investigating what a strong adversary might accomplish, we assume the adversary knows the threshold M, and can hence always return malicious updates within this magnitude."
8. **章节**：Section 4 (Defenses)。**支撑**：第 4 节与第 6 节弱差分隐私的定位（加噪目的是防攻击而非提供隐私保证，噪声量很小，且没有隐私配方）。
   > "Since our goal is not privacy, but instead preventing attacks, we add a small amount of noise that is empirically sufficient to limit the success of attacks."
9. **章节**：Section 5 (Experiments)。**支撑**：第 7 节关键结果（范数界取 3 能缓解攻击且几乎不影响主任务性能，对应 Figure 4(a)）。
   > "We can see from the plot that selecting 3 as the norm bound will successfully mitigate the attack with almost no effect on the performance of the main task."
10. **章节**：Section 5 (Experiments)。**支撑**：第 7 节关键结果（攻击成功率取决于恶意比例，低于 1% 时性能下降，对应 Figure 1、Figure 2、Figure 5、Figure 6）。
    > "From the above experiment, we can infer that the backdoor attack success largely depends on the fraction of adversaries and the performance of backdoor attack degrades as the fraction of fully compromised users falls below 1%."

（第 6 项引文以原文句子为准；原文中该句后半为 "; in more complex schemes M could even be chosen in randomized fashion."，为满足 15 至 40 个英文单词的长度限制，此处截取到 "threshold M" 为止，未做任何改写。）

```json
{
  "key": "sun2019clipping",
  "title": "Can You Really Backdoor Federated Learning?",
  "year": 2019,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_training", "update_postprocess"],
  "observables": [
    {
      "what": "每个客户端上传的模型更新向量或其L2范数，用于阈值丢弃与裁剪",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "良性客户端更新范数分布（第90百分位低于2），论文用它作为选择范数界M的经验依据",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": true,
      "needs_clean_reference": true,
      "needs_extra_compute": false
    },
    {
      "what": "裁剪后的聚合更新，用于逐坐标加方差0.025的独立高斯噪声",
      "where": "server_post_aggregate",
      "granularity": "model",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "无约束boost攻击留下的异常大更新范数痕迹；范数受限攻击会刻意把该量压到M以内以规避阈值",
      "where": "server_receive",
      "granularity": "client",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    }
  ],
  "interventions": ["exclude_client", "clip", "add_noise"],
  "intervention_where": ["server"],
  "assumptions": [
    "模型在被攻击轮次已充分收敛，其他良性客户端的更新足够小，模型替换才能把全局模型带到w*附近（第3节）",
    "攻击者持有后门任务数据集Dmal和来自真实分布Dtrn的训练样本；论文自述这类数据在实践中可能更难获得（第3节）",
    "非恶意客户端持有后门任务的正确标注样本，会在后续轮次纠正被攻击的模型（第2节）",
    "同一轮出现多个攻击者时它们可以协调并均分替换更新（第3节）",
    "防御侧假设攻击者知道范数阈值M，因此阈值化在效果上等价于范数裁剪（第4节）",
    "范数界M与高斯噪声方差需要预先选定，论文不提供学习或选取方法（第5节）",
    "范数约束与安全聚合的兼容性依赖高效的多方范围证明，论文认为这仍是开放问题（第1、6节）"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第2节攻击目标：定向后门，保持主任务性能",
      "text": "This paper focuses on backdoor attacks in the federated learning setting, where the goal of the adversary is to reduce the performance of the model on targeted tasks while maintaining a good performance on the main task."
    },
    {
      "section": "Section 1 (Introduction)",
      "supports": "第2节攻击者能力与第3节攻击入口：完全攻陷客户端可完全改变模型更新，属于模型更新投毒",
      "text": "In federated learning systems, since the training process is done on local devices, fully compromised clients can change the model update completely, which is called a model poisoning attack (3; 4)."
    },
    {
      "section": "Section 2 (Backdoor Attack Scenario)",
      "supports": "第2节与第9节假设：非恶意客户端持有后门任务的正确标注样本",
      "text": "Unlike (3; 4), we allow non-malicious clients to have correctly labeled samples from the targeted backdoor tasks."
    },
    {
      "section": "Section 3 (Model Update Poisoning Attacks)",
      "supports": "第9节论文自述局限：攻击者的真实分布数据在实践中可能更难获得",
      "text": "We also assume the attacker has a set of training samples generated from the true distribution Dtrn. Note that for practical applications, such data may be harder for the attacker to obtain."
    },
    {
      "section": "Section 3 (Model Update Poisoning Attacks)",
      "supports": "第4节方法原理与第5节攻击规避范数阈值的机制",
      "text": "Here at each round, the model trains on the backdoor task subject to the constraint that the model update is smaller than M/β. Thus, model update has norm bounded by M after boosted by a factor of β."
    },
    {
      "section": "Section 4 (Defenses)",
      "supports": "第6节干预动作：服务器忽略范数高于M的更新",
      "text": "Since boosted attacks are likely to produce updates with large norms, a reasonable defense is for the server to simply ignore updates whose norm is above some threshold M"
    },
    {
      "section": "Section 4 (Defenses)",
      "supports": "第9节自适应攻击评估边界：论文假设攻击者知道阈值M",
      "text": "However, in the spirit of investigating what a strong adversary might accomplish, we assume the adversary knows the threshold M, and can hence always return malicious updates within this magnitude."
    },
    {
      "section": "Section 4 (Defenses)",
      "supports": "第4节与第6节弱差分隐私的定位：目的不是隐私，噪声量小且经验性",
      "text": "Since our goal is not privacy, but instead preventing attacks, we add a small amount of noise that is empirically sufficient to limit the success of attacks."
    },
    {
      "section": "Section 5 (Experiments)",
      "supports": "第7节关键结果：范数界3能缓解攻击且几乎不影响主任务，对应Figure 4(a)",
      "text": "We can see from the plot that selecting 3 as the norm bound will successfully mitigate the attack with almost no effect on the performance of the main task."
    },
    {
      "section": "Section 5 (Experiments)",
      "supports": "第7节关键结果：攻击成功率取决于恶意比例，低于1%时下降",
      "text": "From the above experiment, we can infer that the backdoor attack success largely depends on the fraction of adversaries and the performance of backdoor attack degrades as the fraction of fully compromised users falls below 1%."
    }
  ]
}
```
