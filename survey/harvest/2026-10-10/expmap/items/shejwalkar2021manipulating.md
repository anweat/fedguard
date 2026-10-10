以下判断只依据这张精读卡片；卡片没写的数字我一律记为"卡片未给"，不做补全。先说明一个贯穿全文的前提：这篇论文是传统联邦学习（classic FL）的视觉模型投毒与鲁棒聚合，卡片第 1 节明确写"全文没有任何语言模型、Transformer 或 LoRA 内容"，攻击入口是"更新上传前的直接替换"（Section II-B），其干预动作只有服务器侧剔除（Algorithm 2），因此它与我们这套面向大模型 LoRA 联邦微调的防护库之间，主要落在"检测几何与聚合接口"这一层，而不是同一类任务。

## 1. 论文自己的实验规模与主要结果

**实验规模。** 数据与模型（Section V-A）：CIFAR10 是 60,000 张 32×32 RGB 图像、50 个客户端各 1,000 个样本、验证集与测试集各 5,000，模型为 Alexnet 与 VGG11；MNIST 是 70,000 张 28×28 灰度图、100 个客户端各 600 个样本，模型为层大小 {784, 512, 10} 的全连接网络；Purchase 是 197,324 条长度 600 的二值特征向量、100 类不平衡分类、80 个客户端各 2,000 个训练样本，模型为 {600, 1024, 100} 的全连接网络；FEMNIST 有 3,400 个客户端、62 类、共 671,585 张灰度图，每客户端样本数的均值与标准差为 226.83 与 88.94，每轮从 3,400 个里随机选 60 个，模型是卷积神经网络。训练轮数与优化设置（Section V-B）：CIFAR10 + Alexnet 共 1,200 轮（第 0 至 1000 轮学习率 0.5、第 1000 至 1200 轮 0.05，批量 250，SGD）；CIFAR10 + VGG11 批量 200、学习率 0.1 与 0.01；MNIST 500 轮、Adam、学习率 0.001、批量 100；Purchase 1,000 轮、SGD、学习率 0.5、批量 500；FEMNIST 1,500 轮、Adam、学习率 0.001，每批使用客户端全部数据。跨孤岛设置下 CIFAR10/MNIST/Purchase 的客户端每轮全部参与，跨设备实验用 CIFAR10 且每轮只在 50 个客户端里处理 10 个（Section II-A、Section VI-E）。这篇论文没有本地多步训练的描述，客户端每轮用一个小批量算随机梯度后同步上传（Section II-A）。

**投毒设置。** 默认 20% 恶意客户端（Section V-B，卡片举例"MNIST 用 20 个恶意客户端"），比例从 5% 扫到 24%（Section VI-D2，Figure 3 与 Figure 6a）；假设 (m/n) < 0.5 且服务器知道恶意客户端数量上界 m（Section III）；攻击是在上传前直接替换梯度，形式为 ∇m = ∇b + γ∇p（Section IV-A），目标是无目标准确率破坏，论文明确把后门与定向攻击排除在范围之外（Section II-B）。种子方面，卡片只在 Section VI-A 结尾说明 Table II 的结果是三次实例的平均、个别异常被归因于实验随机性；**系统的种子数与置信区间卡片未给**。

**主要结果。** 攻击侧，Table II 中 CIFAR10 + Alexnet + Krum 在 agr-updates 下本文攻击的准确率影响是 43.6%，Fang 是 21.8%；同表 Bulyan 一行 Fang 与 LIE 分别是 11.8% 与 30.0%，本文 AGR-tailored 与 AGR-agnostic 分别是 45.6% 与 44.5%（Section I 与 Table II）；MNIST + Krum 在 agr-updates（agr-only）下 Fang 为 20.5%（17.4%）、本文为 33.9%（24.1%），MNIST 的 Trimmed-mean（Median）上 Fang 只有 1.2%（1.7%）、本文为 11.0%（4.4%）（Table II）；Purchase 上本文攻击把 Krum 的准确率压到接近随机猜测的 1%（Table II 与 Section VI-A）；摘要给的总体范围是准确率下降幅度高 1.5 倍到 60 倍（Abstract）。Figure 3 与 Figure 6a 进一步显示，CIFAR10 + Krum 下本文 AGR-tailored 攻击在只有 5% 恶意客户端时影响就超过 43%（把准确率压到随机猜测的 10%），Purchase 下 AGR-tailored 与 Min-Sum 分别在 5% 与 10% 恶意客户端时就把 Krum 的准确率压到接近 1%。防御侧，Table IV 与 Section VII-C1 报告 DnC 把最大准确率下降从 36.8% 降到 6.1%（CIFAR10 + Alexnet）、从 32.5% 降到 6.3%（CIFAR10 + VGG11）、从 11.6% 降到 1.8%（Purchase）、从 4.4% 降到 1.9%（MNIST），摘要称韧性比既有方法高 2.5 倍到 12 倍；跨设备下 DnC 的最小 A*_θ 从既有 AGR 的 50.6% 提高到 61.2%（CIFAR10 + Alexnet，对应自适应攻击影响 3.4%）、VGG11 从 63.4% 提高到 68.0%（Table V）。局限侧，Table VI 报告在真实非 iid 的 FEMNIST 上 DnC 失守：知道良性梯度的 agr-updates 与 updates-only 一侧，Min-Sum 的影响是 79.3%（准确率从无攻击的 86.6% 压到 7.3%），不知道良性梯度的一侧最大影响只有 12.7%（DnC 下最高准确率 73.9%，而既有 AGR 中最鲁棒的 Krum 只有 66.4%），论文自述"在真实世界的非 iid FL 设置中防御最坏情况的模型投毒是已知的难题，也是当前形式 DnC 的局限"（Section VII-C2）；Table VII 还报告重采样这一负面结论：Krum 的无攻击准确率从 69.3% 降到 47.8%，Bulyan 从 86.1% 降到 76.8%，Trimmed-mean 从 86.7% 降到 70.3%。评测指标是 I_θ = A_θ − A*_θ，即无攻击时最优全局模型准确率与受攻击时准确率之差（Section V-B）。开销方面，论文只报告了 SVD 类方法需要 O(d³) 的内存与计算，以及 iid 实验取 n_iters = 1、c = 1、b = 10,000（FEMNIST 取 c = (n−1)/n）（Section VII-B、Section VII-C1 与 VII-C2），**实测的墙钟时间、通信量、存储量卡片未给，论文也没有把 DnC 与既有 AGR 的运行时间做对比**。另外，论文构造并评估了针对 DnC 的自适应攻击（Section VII-B，公式 (8)），其影响在 CIFAR10 + Alexnet 为 6.1%、CIFAR10 + VGG11 为 6.3%、Purchase 为 1.8%、MNIST 为 1.9%（Table IV），跨设备为 3.4% 与 4.1%（Table V），FEMNIST 上知道良性梯度一侧为 78.6%、不知道一侧为 10.2%（Table VI）。

## 2. 与我们各项实验的对应

先说一条总体判断：**我们没有实现这篇论文自己的两个贡献**。E6 的 26 次运行清单里有 Krum、坐标中位数、截尾均值，但没有 DnC，也没有 Algorithm 1 的投毒攻击；我们的"没做过的"里明确列了"上传侧攻击（更新放大、针对防御构造更新、合谋）"，而这恰好就是论文的攻击入口（Section II-B：在每一轮把梯度共享给服务器之前直接篡改）。因此下面的对应里没有一项是 method_source。

E1（不改训练、逐位一致）：论文没有任何"空插件不改训练"的对照实验，卡片里也没有可对齐的设置或数字，只能算 background。它的实际价值是在我们将来复现论文服务器侧 AGR（例如把 DnC 作为替换 Average 的聚合器挂上去）之前，先证明挂载本身不改变宿主行为。

E2（开销）：论文只给了 SVD 类防御的 O(d³) 渐近复杂度与 b = 10,000、n_iters = 1 这两个超参数取值（Section VII-B、Section VII-C1），并明确没有报告可比较的定量开销基准，属于 background，与 E2 的 0.7%–2.8%（两侧采集与记录）、0.25%–1.8%（服务器侧统计插件）以及 ProtegoFed 逐样本梯度每客户端每轮 3.8 秒这类读数之间**没有可对照的数字（卡片未给）**。唯一有间接关系的是：论文说高维梯度上直接做 SVD"代价高得不可行"（Section VII-B），这为"我们的谱类插件在高维 LoRA 因子上的成本必须自己基准测试"提供了动机，但不构成数值比较。

E3（特征预实验 P1）：这是与我们对应最直接的一条，属于 same_question。论文 Section I 的核心判据是"当客户端数据是 iid 时，一个投毒更新有影响，当且仅当它沿更新空间中某个特定恶意方向显著偏离良性更新"，DnC 也就是沿这个主成分方向做投影并剔除（Section I 与 Algorithm 2）。E3 在效果层（BA）与因子层（A、B）上比较大小与方向特征，得到因子层方向 17/20 轮、效果层大小 15/20 轮能标出恶意客户端，方向上与"更新几何可分离"这一论断一致，因此我记为 consistent。但必须明确：论文是视觉模型的全梯度、无目标准确率破坏，我们是 Qwen2.5-0.5B 的 LoRA、用 MaliciousGen 有害问答做数据投毒、目标是安全行为破坏，模型规模、参数空间与攻击目标都不同，**数字不能直接比较**。另外 E3 里"效果层方向只有 3/20"并不构成对论文的矛盾，因为 DnC 用的方向是从本轮全部提交更新估出的主成分方向（Algorithm 2），而不是单个更新自身的方向，两者不是同一个量。

E4（良性基线与校准 P2）：同属 same_question，但只能记为 not_comparable。论文侧的良性参照是各 AGR 与 DnC 的无攻击准确率（Table IV 中 CIFAR10 + Alexnet 为 67.6%，Table V 跨设备为 64.6%）以及 Table VII 中重采样造成的无攻击准确率下降，卡片里没有给误报率或阈值校准；E4 是用 4 种良性划分各 3 个种子校准 1% 误报阈值，并观察到恶意占比 10% 时最好 6/18、占比 10% 时 1–2/18 与误报相当。两者都在强调良性侧代价不可忽略，但一个是准确率、一个是逐轮检出计数，**不能直接比较**。还有一处需要留意：论文 Section VI-D1（Figure 4）报告非 iid 程度越高所有攻击影响越大，而 E4 发现按 Dolly 类别的 Dirichlet 划分对 LoRA 更新相似度几乎没有影响；这两个结论测的不是同一个量（攻击影响 vs 更新相似度），卡片也没有给出 LoRA 下的指导，所以我不把它记为矛盾。

E5（自动攻击矩阵 P3）：属于 same_question，方向一致（consistent）。论文 Figure 3 与 Figure 6a 把恶意比例从 5% 扫到 24%，报告 CIFAR10 + Krum 下只有 5% 恶意客户端时影响就超过 43%、Purchase 下 5% 与 10% 就把 Krum 压到接近 1%；E5 的盲区正好是分散的低浓度投毒（2–3 个恶意客户端各 10%，检出 3–15%）与每轮只抽 5 个客户端（检出 24–35%）。两者都指向"低比例、部分参与下投毒既危险又难处理"，但论文测的是攻击影响 I_θ，我们测的是逐轮检出率与误报率（1 个恶意客户端、占比 ≥30% 时检出 83–100%、误报 0.6–1.9%），**指标不同、不能直接比较**。E5 还应对齐论文的跨设备设置：论文每轮只在 50 个客户端里处理 10 个，并明确区分跨孤岛（全部参与）与跨设备（部分参与）两种设置（Section II-A、Section VI-E），这正是 setting_reference；论文没有给出部分参与下的检出率数字。至于 E5 的行为探针（跨轮累积后 37 个恶意客户端中 33 个超过全部良性客户端），论文完全没有基于输出行为或安全指标的检测依据，卡片未给任何对应内容。

E6（已发表防御的可用性批量）：属于 setting_reference。论文用作对照的是 Krum、Multi-krum、Bulyan、Trimmed-mean、Median、AFA 六种鲁棒 AGR 以及 Fang 的元防御（Table II、Table III），这是我们批量覆盖防御时应参照的清单；我们已实现其中 Krum、坐标中位数、截尾均值，但论文自己的攻击与 DnC 都不在 E6 清单里。由于 E6 明确不评价防御效果、只验证端到端跑通，这里没有一致或矛盾可谈（agreement = n/a）；E6 里"谱签名、梯度谱熵、激活聚类接近 0"的样本过滤读数也不能拿来评判 DnC，因为那是三个不同算法，而且只在 4B、480 条样本 96 条带毒的一次读数上得到。另外论文 Section IV-B7 论证 Fang 元防御会被任意大的恶意向量破坏，这可以作为我们将来评估 Fang 类基线时的一个理论参照。

E7（无攻击对照）：属于 same_question，方向一致（consistent）。论文 Table VII 报告重采样让既有 AGR 在无攻击时也退化（Krum 无攻击准确率 69.3% → 47.8%，Bulyan 86.1% → 76.8%，Trimmed-mean 86.7% → 70.3%），并把这当作负面结论（Section VII-C2 与附录 A）；E7 在完全没有攻击时观察到 Krum 仍排除 80% 的客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%，梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本、激活聚类屏蔽 15%、ProtegoFed 屏蔽 4%，而 MCD 不排除、Safe-FedLLM 权重不变。两者都说"鲁棒聚合本身会给良性训练带来代价"，但论文的报告量是视觉模型准确率、我们的是排除轮次与屏蔽样本比例，**数字不能直接比较**。

E8（宿主适配）：论文不涉及宿主框架或插件挂载，卡片里没有可以对齐的实验设置，属于 background。卡片第 10 节只是分析性地指出 DnC 需要"服务器收到更新时的逐客户端、未聚合、可做维度级索引"的原始更新视图，以及聚合钩子要允许插件整体接管聚合逻辑并读到 n、m、c、n_iters、b，其中"恶意客户端数上界 m"是本文方法特有的强假设——这些是对库设计的含义，不是实验结果。

E9（Safe-FedLLM 式 LoRA 权重探针）：属于 setting_reference，但很弱。卡片里唯一与"运行次数"有关的设置是 Section VI-A 结尾：Table II 的结果是三次实例的平均，个别 agnostic 攻击者影响略高于 updates-only 的异常被归因于实验随机性；系统的种子数与置信区间卡片未给。这可以作为"结论要基于多次运行"的做法参照，但它既不能印证也不能否定 E9 换一次种子后探针失效（恶意客户端概率 0.00）这一单次观测。

E10（调研与知识库）：这篇论文只是 E10 里 137 篇逐篇卡片中的一篇、47 篇防御流水线中的一篇，属于 background（agreement = n/a）。卡片没有给出它与我们"45 篇 481 个步骤对到算子与运行时"这一映射结果的对应关系，所以无法判断它落在 39% 直接可表达、39% 要拼、10% 缺算子、13% 超出运行时的哪一类里。

## 3. 我们要与它可比还差什么

第一，缺实现。要让"对应"从 setting_reference 升级为 method_source，我们必须补上 DnC 本体（Algorithm 2：随机维度子采样、中心化、求顶部右奇异向量、按 s_i = (⟨∇_i − μ, v⟩)² 排序、剔除 c·m 条、对交集取平均）与它的超参数管线（iid 下 n_iters = 1、c = 1、b = 10,000），以及在客户端上传前替换更新的攻击入口（∇m = ∇b + γ∇p，配 Algorithm 1 的 γ 搜索与三种扰动方向 ∇p_uv、∇p_std、∇p_sgn）。我们目前的攻击只有数据级有害问答投毒与触发词后门，属于论文明确排除的定向/后门一类。

第二，缺规模对齐。论文是 50/80/100 个客户端全体参与或 3,400 里抽 60，训练 500 至 1,500 轮，模型是 Alexnet/VGG11/全连接网络；我们是 5–10 个客户端、3 至 20 轮（E6/E7 只有 4 轮）、Qwen 系列的 LoRA 适配器。卡片没有给出这两种参数空间的可比量，因此要对齐至少要补：客户端数与每轮参与率、几百到上千轮的训练、以及 LoRA 因子的维度与论文全梯度维度的对照。

第三，缺投毒设置对齐。要在同一个口径上比较，需要按论文的方式给出"无攻击时最优全局模型准确率 A_θ 与受攻击时准确率 A*_θ"这一对量并计算 I_θ = A_θ − A*_θ（Section V-B），把恶意比例做成 5% 到 24% 的扫描（Section VI-D2），并覆盖论文的四类攻击者知识等级（Table I：agr-updates、agr-only、updates-only、agnostic）；我们现在既没有无目标准确率破坏指标，也没有以"服务器已知 m、精确剔除 c·m 条"为前提跑过任何聚合器。

第四，缺指标补齐。论文用的评测指标是全局模型准确率与 I_θ，以及在不同恶意比例、不同非 iid 程度、不同扰动方向下的准确率下降（Figure 2、Figure 3、Figure 4、Figure 6a、Figure 7）；我们现有指标是检出轮数比例、误报率、样本过滤的精确率/召回率、插件耗时、逐位一致性，两边没有交集。要可比必须补上准确率口径，同时我们擅长的开销与逐位一致这两项，论文侧是空白（卡片未给实测开销），反而没有对照对象。

第五，缺统计与异质性条件。论文 Table II 是三次实例的平均并公开归因随机性，我们多数级别只有 1 个种子、没有置信区间；论文有 iid 默认设置（其理由是"iid 数据下投毒 FL 最难"，Section V-B）、合成非 iid（Section VI-D1）与真实非 iid 的 FEMNIST，我们只有 Dolly + Dirichlet 划分，从未做过 iid 对照。此外论文评估了知道 DnC 的自适应攻击（Section VII-B，公式 (8)），我们的"没做过的"里也明确列了知道防御的自适应攻击，这一块两边都缺同一个东西。

第六，缺一条可判定的对照结论。论文最强的正面结论是 iid 视觉设置下 DnC 把最大准确率下降从 36.8% 压到 6.1%、32.5% 压到 6.3%、11.6% 压到 1.8%、4.4% 压到 1.9%（Section I、Section VII-C1、Table IV），最强负面结论是非 iid FEMNIST 上知道良性梯度时 Min-Sum 影响 79.3%（Table VI）。由于我们没有 DnC 实现、没有准确率破坏指标、也没有非 iid 对照，这两条我们都还无法印证或反驳；在补齐之前，我们与这篇论文的关系只能停留在"接口与几何直觉的参照"这一层。

```json
{
  "key": "shejwalkar2021manipulating",
  "paper_scale": {
    "models": "Alexnet 与 VGG11（CIFAR10）；层大小 {784, 512, 10} 的全连接网络（MNIST）；层大小 {600, 1024, 100} 的全连接网络（Purchase）；卷积神经网络（FEMNIST）（Section V-A 与 Table II 至 Table VII）",
    "clients": "CIFAR10 50 个客户端（跨孤岛全部参与）、MNIST 100 个、Purchase 80 个；FEMNIST 3,400 个客户端中每轮随机选 60 个；跨设备实验用 CIFAR10、每轮只在 50 个里处理 10 个（Section V-A、Section II-A、Section VI-E）",
    "rounds": "CIFAR10 + Alexnet 1,200 轮（第 0 至 1000 轮学习率 0.5、第 1000 至 1200 轮 0.05，批量 250，SGD）；CIFAR10 + VGG11 批量 200、学习率 0.1 与 0.01；MNIST 500 轮（Adam，学习率 0.001，批量 100）；Purchase 1,000 轮（SGD，学习率 0.5，批量 500）；FEMNIST 1,500 轮（Adam，学习率 0.001，每批用客户端全部数据）（Section V-B）；论文没有本地多步训练的描述（Section II-A）",
    "poison_setting": "默认 20% 恶意客户端（Section V-B，例如 MNIST 用 20 个恶意客户端），比例从 5% 扫到 24%（Section VI-D2，Figure 3 与 Figure 6a）；假设 (m/n) < 0.5 且服务器已知恶意客户端数量上界 m（Section III）；攻击入口是上传前直接替换梯度，形式 ∇m = ∇b + γ∇p，目标为无目标准确率破坏，明确排除后门与定向攻击（Section II-B、Section IV-A）；四类攻击者知识等级见 Table I",
    "seeds": "卡片只在 Section VI-A 结尾说明 Table II 的结果是三次实例的平均、个别异常归因于实验随机性；系统的种子数与置信区间卡片未给",
    "federated": true,
    "lora": false
  },
  "headline_results": [
    "攻击：Table II 中 CIFAR10 + Alexnet + Krum 在 agr-updates 下本文攻击的准确率影响为 43.6%，Fang 为 21.8%；同表 Bulyan 一行 Fang 与 LIE 为 11.8% 与 30.0%，本文 AGR-tailored 与 AGR-agnostic 为 45.6% 与 44.5%；MNIST + Krum 在 agr-updates（agr-only）下 Fang 为 20.5%（17.4%）、本文为 33.9%（24.1%）；MNIST 的 Trimmed-mean（Median）上 Fang 为 1.2%（1.7%）、本文为 11.0%（4.4%）；摘要称准确率下降幅度总体高 1.5 倍到 60 倍（Abstract、Section I、Table II）",
    "防御：DnC 把最大准确率下降从 36.8% 降到 6.1%（CIFAR10 + Alexnet）、从 32.5% 降到 6.3%（CIFAR10 + VGG11）、从 11.6% 降到 1.8%（Purchase）、从 4.4% 降到 1.9%（MNIST），摘要称韧性比既有方法高 2.5 倍到 12 倍；跨设备下最小 A*_θ 从 50.6% 提高到 61.2%（Alexnet）、63.4% 提高到 68.0%（VGG11）（Section I、Section VII-C1、Table IV、Table V）",
    "局限与负面结论：非 iid FEMNIST 上知道良性梯度的最强攻击者一侧 Min-Sum 影响 79.3%（准确率从无攻击的 86.6% 压到 7.3%），不知道良性梯度一侧最大影响 12.7%（DnC 下最高 73.9%，Krum 只有 66.4%）；重采样使 Krum 无攻击准确率从 69.3% 降到 47.8%、Bulyan 86.1% 到 76.8%、Trimmed-mean 86.7% 到 70.3%（Section VII-C2、Table VI、Table VII）"
  ],
  "links": [
    {"experiment": "E1", "relation": "background", "agreement": "n/a", "detail": "论文没有空插件/不改训练这类对照实验，卡片里没有可对齐的设置或数字；E1 的价值只在于为将来把 DnC 作为服务器侧 AGR 挂载提供宿主可信性前提。"},
    {"experiment": "E2", "relation": "background", "agreement": "n/a", "detail": "论文只给 SVD 类方法的 O(d³) 渐近复杂度与 iid 下 n_iters = 1、c = 1、b = 10,000（FEMNIST 为 c = (n−1)/n）的取值（Section VII-B、VII-C1、VII-C2），明确没有报告实测墙钟时间、通信量或存储量，也无法与 E2 的 0.7%–2.8%、0.25%–1.8% 等读数对照；实测数字卡片未给。"},
    {"experiment": "E3", "relation": "same_question", "agreement": "consistent", "detail": "论文 Section I 的判据是 iid 下投毒更新有影响当且仅当它沿更新空间中某个特定恶意方向显著偏离良性更新，DnC 正是沿该主成分方向剔除（Algorithm 2）；E3 中因子层方向 17/20、效果层大小 15/20 能标出恶意客户端，方向上与'更新几何可分离'一致。但论文是视觉模型全梯度、无目标准确率破坏，我们是 0.5B 模型 LoRA、有害问答数据投毒，规模与目标不同，数字不能直接比较；E3 中效果层方向仅 3/20 不构成矛盾，因为 DnC 用的是从全体更新估出的主成分方向而非单个更新自身方向。"},
    {"experiment": "E4", "relation": "same_question", "agreement": "not_comparable", "detail": "论文侧的良性参照是各 AGR 与 DnC 的无攻击准确率（Table IV 中 CIFAR10 + Alexnet 为 67.6%、Table V 跨设备为 64.6%）与 Table VII 中重采样造成的无攻击准确率下降，卡片未给误报率或阈值校准数字；E4 用 4 种良性划分各 3 个种子校准 1% 误报阈值，观察到占比 30% 时最好 6/18、占比 10% 时 1–2/18 与误报相当。两者都说良性侧代价不可忽略，但量纲不同（准确率 vs 逐轮检出计数），不能直接比较；论文 Section VI-D1（Figure 4）的非 iid 越强攻击影响越大与 E4 的 Dirichlet 划分对 LoRA 更新相似度几乎无影响测的不是同一个量。"},
    {"experiment": "E5", "relation": "same_question", "agreement": "consistent", "detail": "论文 Figure 3 与 Figure 6a 报告 CIFAR10 + Krum 下 5% 恶意客户端时影响已超过 43%（准确率压到随机猜测的 10%），Purchase 下 AGR-tailored 与 Min-Sum 分别在 5% 与 10% 时把 Krum 压到接近 1%；E5 的盲区正是低浓度分散投毒（2–3 个恶意客户端各 10% 检出 3–15%）与每轮只抽 5 个客户端（检出 24–35%）。两者都指向低比例、部分参与下投毒既危险又难处理，但论文测攻击影响 I_θ、我们测逐轮检出率与误报率（≥30% 时 83–100%、误报 0.6–1.9%），指标不同不能直接比较；E5 的行为探针在论文中没有任何对应依据。"},
    {"experiment": "E5", "relation": "setting_reference", "agreement": "n/a", "detail": "论文区分跨孤岛（全部参与）与跨设备（部分参与）两种设置，跨设备实验用 CIFAR10 且每轮只在 50 个客户端里处理 10 个（Section II-A、Section VI-E），这是 E5 每轮抽 5/10 的部分参与实验该对齐的参照；论文没有给出部分参与下的检出率数字。"},
    {"experiment": "E6", "relation": "setting_reference", "agreement": "n/a", "detail": "论文的对照 AGR 清单是 Krum、Multi-krum、Bulyan、Trimmed-mean、Median、AFA 与 Fang 元防御（Table II、Table III），这是 E6 批量覆盖防御方法时的参照清单；E6 已含 Krum、坐标中位数、截尾均值，但论文自己的 Algorithm 1 攻击与 DnC 都不在 E6 的 26 次运行里。E6 不评价防御效果，故无一致或矛盾可谈；E6 中谱签名、梯度谱熵、激活聚类接近 0 的样本过滤读数属于不同算法，不能用来评判 DnC。"},
    {"experiment": "E7", "relation": "same_question", "agreement": "consistent", "detail": "论文 Table VII 报告重采样使既有 AGR 在无攻击时退化（Krum 无攻击准确率 69.3% → 47.8%、Bulyan 86.1% → 76.8%、Trimmed-mean 86.7% → 70.3%），并明确称这是负面结论（Section VII-C2 与附录 A）；E7 在无攻击时观察到 Krum 仍排除 80% 客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%，梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本，方向一致。两者指标与模型不同（视觉模型准确率 vs 排除轮次与屏蔽样本比例），数字不能直接比较。"},
    {"experiment": "E8", "relation": "background", "agreement": "n/a", "detail": "论文不涉及宿主框架或插件挂载，卡片里没有能与 E8 对齐的实验设置；卡片第 10 节关于 DnC 需要服务器侧逐客户端、未聚合、可维度索引更新视图与已知 m 的说法是对库设计的含义，不是实验结果。"},
    {"experiment": "E9", "relation": "setting_reference", "agreement": "n/a", "detail": "卡片给出的唯一与运行次数有关的设置是 Section VI-A 结尾：Table II 的结果是三次实例的平均、个别异常归因于随机性，系统的种子数与置信区间卡片未给。这可作为结论应基于多次运行的参照，但无法印证或否定 E9 换种子后探针失效（恶意客户端概率 0.00）这一单次观测。"},
    {"experiment": "E10", "relation": "background", "agreement": "n/a", "detail": "这篇论文只是 E10 中 137 篇卡片与 47 篇防御流水线里的一篇；卡片没有给出它与我们 45 篇 481 个步骤算子映射结果的对应关系，无法判断它属于直接可表达、需要拼装、缺算子还是超出运行时的哪一类。"}
  ],
  "missing_for_comparability": [
    "DnC 本体未实现：需要 Algorithm 2 的随机维度子采样、中心化、顶部右奇异向量、离群分数 s_i = (⟨∇_i − μ, v⟩)² 排序、剔除 c·m 条并对交集取平均，以及 iid 下 n_iters = 1、c = 1、b = 10,000 的超参数取值（Section VII-C1）",
    "论文的攻击入口未实现：需要在客户端上传前替换更新向量，构造 ∇m = ∇b + γ∇p，配 Algorithm 1 的 γ 搜索与 ∇p_uv、∇p_std、∇p_sgn 三种扰动方向，并覆盖 Table I 的四类攻击者知识等级；我们目前只有数据级有害问答投毒与触发词后门，而论文明确排除后门与定向攻击",
    "模型与参数空间对齐：论文是 Alexnet、VGG11 与 {784,512,10}、{600,1024,100} 全连接网络，我们是 Qwen2.5-0.5B / Qwen3.5-0.8B / 4B 的 LoRA；需要给出 LoRA 因子维度与论文全梯度维度的对照，并说明 Krum、Trimmed-mean、DnC 在拼接 LoRA 因子上如何定义距离与逐维操作（卡片未给指导）",
    "轮数与客户端规模对齐：论文 500 至 1,500 轮、50/80/100 个客户端全体参与或 3,400 里抽 60；我们是 5–10 个客户端、3 至 20 轮（E6/E7 仅 4 轮），差两个数量级",
    "恶意比例与 m 的设置对齐：论文默认 20%、扫描 5% 到 24%，且假设服务器已知恶意客户端数量上界 m 并精确剔除 c·m 条（Section III、Algorithm 2）；我们从未在已知 m 的假设下运行过剔除式聚合",
    "指标对齐：需要补上无攻击时最优全局模型准确率 A_θ、受攻击准确率 A*_θ 与影响 I_θ = A_θ − A*_θ（Section V-B），以及恶意比例扫描、非 iid 程度扫描、不同扰动方向下的准确率下降（Figure 2、Figure 3、Figure 4、Figure 6a、Figure 7）；我们现有指标是检出轮数比例、误报率、样本过滤精确率/召回率、插件耗时与逐位一致性，两边无交集",
    "攻击类型对齐：论文是无目标模型投毒，我们没有对应的无目标准确率破坏评测，也没有后门的攻击成功率评测，且论文本身不含后门与越狱/安全对齐指标",
    "多种子与统计对齐：论文 Table II 为三次实例平均并公开归因随机性；我们多为单种子或每级别 1 个种子，没有置信区间",
    "数据异质性条件对齐：论文有默认 iid（理由是 iid 下投毒最难，Section V-B）、合成非 iid（Section VI-D1）与真实非 iid FEMNIST；我们只有 Dolly 加 Dirichlet 划分，缺 iid 对照",
    "自适应攻击对齐：论文构造并评估了针对 DnC 的自适应攻击（Section VII-B，公式 (8)，Table IV/V/VI）；我们明确没做过知道防御的自适应攻击",
    "开销对照：论文只给渐近复杂度与超参数、未给实测开销，我们的插件耗时读数在论文侧没有对应数字（卡片未给）",
    "基础设置对齐：论文假设服务器能看到明文未聚合更新，未讨论安全聚合、差分隐私或加密（Section III 与卡片第 9 节），我们也没有在这些条件下做过实验"
  ],
  "metrics_paper_uses": [
    "全局模型验证/测试准确率 A_θ（无攻击时最优）与 A*_θ（受攻击时）（Section II-A、Section V-B）",
    "攻击影响 I_θ = A_θ − A*_θ，即无攻击准确率与受攻击准确率之差（Section V-B）",
    "恶意客户端比例从 5% 到 24% 扫描下的准确率下降（Section VI-D2，Figure 3 与 Figure 6a）",
    "不同非 iid 程度下的准确率下降（Section VI-D1，Figure 4）",
    "不同扰动方向 ∇p 下的准确率影响（Section VI-C1，Figure 2 与 Figure 7）",
    "跨孤岛与跨设备两种设置下的准确率对比（Table III 与 Table V，Section VI-E）"
  ],
  "relevance": "medium"
}
```
