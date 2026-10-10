## 1. 论文自己的实验规模与主要结果

**场景与规模。** 这篇论文是传统联邦学习上的服务器端防御，全部实验都是完整权重训练与完整权重上传；论文没有涉及大语言模型，也没有涉及参数高效微调或 LoRA（卡片第 1 节）。论文在九个数据集上评测，模型从约 66k 参数到约 20M 参数（Table I、Section V-A、Appendix A）：Reddit 20.6M 条记录 / LSTM 约 20M 参数；IoT-Traffic 65.6M / GRU 约 507k；Cifar-10 60.0k / ResNet-18 Light 约 2.7M；MNIST 70.0k / CNN 约 431k；EMNIST 814.2k / LeNet 约 66k；TIMIT 201.6k / LSTM 约 12M；PROTEINS 1113 / GraphSage 约 102k；NCI1 4110 / GAT 约 101k；D&D 1178 / GCN 约 106k、GatedGCN 约 104k、MoNet 约 102k。

**卡片未给的规模信息。** 每类实验的客户端总数 K 与每轮参与率论文未给出，论文只给出投毒模型率（PMR）与投毒数据率（PDR）的取值范围（卡片第 7 节）。训练轮次 T 论文未报告，种子数量卡片未给。数据非独立同分布程度用 iid rate 模拟，1.0 表示完全 iid、0.0 表示每个客户端只有单一标签（Section V-A）。硬件是 4 张 NVIDIA RTX 8000（每张 48GB）、AMD EPYC 7742、1024 GB 内存（Section V-A）。

**攻击与对照。** 无目标攻击包括 Label Flipping、Random Updates、Optimized（PGD）；定向攻击包括 constrain-and-scale、Edge-case（PGD）、DBA、3DFed、Mirai Scanning、Neurotoxin、频率触发器、说话人验证后门、图上的分布式数据投毒后门，以及集中式后门与 Appendix C 的自适应攻击；对比防御包括 Krum、AFA、Median、DP、FoolsGold、BayBFed、FLAME、DeepSight、Auror（Section V-A、Section V-B4）。评测指标是主任务准确率 MA 与后门准确率 BA（Section V-A）。

**主要结果（数值均照抄卡片并注明出处）：**

- 无目标攻击，PMR = 49%、iid = 0.7（Table II）：Label Flipping 下 Cifar-10 从无攻击的 MA 77.3 降到无防御的 35.8、FreqFed 为 77.1，MNIST 98.6 → 50.8 → 97.8，EMNIST 81.3 → 13.4 → 81.2；Random Updates 下 Cifar-10 77.0 → 31.2 → 77.0；Optimized（PGD）下 Cifar-10 77.2 → 10.0 → 77.1，MNIST 98.6 → 44.5 → 98.3，EMNIST 81.4 → 4.9 → 81.3。
- 图像域定向攻击，PDR = 50%、PMR = 30%、iid = 0.9（Table III）：单后门像素模式无防御 BA 100.0 / MA 85.5，FreqFed BA 0.0 / MA 91.9；语义后门 100.0 / 86.8 对 0.0 / 92.0；Edge-case（PGD）BA 73.4 对 4.1；多后门像素模式 BA 97.6 对 0.0；DBA 像素模式 93.8 / 57.4 对 0.4 / 76.2。
- 文本域 Reddit，PDR = 50%、PMR = 25%（Table IV）：constrain-and-scale 的 BA 100.0 / MA 22.6（无防御）对 BA 0.0 / MA 22.6；Neurotoxin 100.0 / 16.2 对 0.0 / 19.8。
- 入侵检测（Section V-B2）：不使用 FreqFed 时 98.5% 的僵尸网络数据包未被检测出、整体 MA 降到 97.6%；使用后 BA 为 0.0%、MA 为 98.3%。
- 说话人验证（Table V）：数据投毒 PDR = 0.49 时 BA 84.7 / MA 92.9 对 0.0 / 95.3；模型投毒 PMR = 0.49 时 100.0 / 94.0 对 0.0 / 94.9。
- 图分类，PDR = 25%、PMR = 49%（Table VI）：PROTEINS、NCI1、D&D 三个数据集与五种模型上 FreqFed 的 BA 全部为 0.0，例如 PROTEINS + GraphSage 从 100.0 / 66.7 变为 0.0 / 79.3。
- 规避与自适应攻击（Table VII–X、Appendix C）：频率域约束损失（PDR = 50%、PMR = 25%、iid = 0.7、α = 0.7）在 Known-Benign 下 Cifar-10 的 BA 100.0 / MA 83.9 对 0.0 / 85.7，Unknown Benign 下 100.0 / 84.3 对 0.0 / 85.0；良性频率注入（Table VIII，MNIST）无防御 BA 0.0 / MA 83.9，FreqFed 0.0 / 96.6；频率触发器（Table IX，Cifar-10、iid = 0.8）PDR 从 10 到 100 时无防御 BA 91.0 到 98.3、FreqFed 全部 0.0；集中式后门（Table X，Cifar-10、iid = 0.0）PMR 10% 时 60.6 对 0.0，20% 时 81.0 对 0.0，30%、40%、49% 时 100.0 对 0.0。
- 与其他防御的对比（Table XI，PMR = 25% 的 constrain-and-scale）：FreqFed 是唯一在 Reddit、Cifar-10、IoT-Traffic 三处都有效的防御，BA 分别为 0.0、0.0、0.0，MA 分别为 22.6、86.5、96.5；Krum 在 Reddit 上 BA 仍为 100.0，Auror 在 Reddit 上 MA 只有 10.5。Table XII（PMR = 49%、iid = 0.7）中 FreqFed 在 Cifar-10、MNIST、EMNIST 上的 MA 分别为 77.1/77.1、97.8/98.3、81.2/81.3（LF/PGD）。
- 有效边界：Figure 2a、Figure 3a、Figure 5、Figure 6a、Figure 6b、Figure 7 均显示 PMR < 50% 时有效，PMR ≥ 50% 时可能把投毒模型误判为多数簇（Section V-B1）；Figure 2b 显示 iid = 0.0 的优化无目标攻击下仍能检测并把 MA 保持约 75%，Figure 4 显示 constrain-and-scale 在 iid = 0.0 时仍能区分。
- 开销：论文未报告计算、通信与存储开销的任何定量数据，只给硬件配置（卡片第 8 节）。卡片补充的分析是：服务器端要多做每个客户端全部权重的一次 DCT、K×K 余弦距离矩阵与 HDBSCAN，余弦距离部分为 O(K²·d)，论文也未讨论参数量远大于 Table I 时的可扩展性。

## 2. 与我们各项实验的对应

**E1（空转等价性）——background，n/a。** 论文的干预只发生在服务器每轮聚合之前：客户端上传之后、FedAvg 之前（卡片第 1 节与第 6 节，Algorithm 1 第 1–7 行），它不改变客户端本地训练、不改变上传内容、也不改变轮数。因此它属于 E1 需要覆盖的那类"服务器侧、挂在固定钩子上、不动作时不应改变训练"的插件。但卡片没有说明 E1 具体挂了哪些插件，论文侧也没有等价性实验，所以这里只算背景。另外卡片第 1 节指出论文自身对干预位置有内部矛盾：摘要写的是"在客户端本地训练期间过滤"，而 Section IV-B、Section IV-C、Figure 1 与 Algorithm 1 都把 DCT、滤波与聚类放在服务器执行，论文未说明客户端侧是否也运行任何过滤逻辑；如果我们要挂载它，位置应以 Algorithm 1 为准。

**E2（开销）——background，n/a。** 论文第 8 节明确未报告任何开销数字，只给了 Section V-A 的硬件（4 张 RTX 8000、EPYC 7742、1024 GB 内存），也没有讨论大参数量下的可扩展性，所以 E2 的 0.7%–2.8% 客户端采集开销、0.25%–1.8% 服务器统计插件开销、以及 ProtegoFed 逐样本梯度每客户端每轮 3.8 秒（训练 2.1 秒）、更新子空间投影 5.7 秒、ONION 3.2 秒这些读数，在论文里没有对应物。可对照的只有开销来源：FreqFed 的服务器端要做逐客户端全参数 DCT、K×K 余弦距离与 HDBSCAN（卡片第 8 节分析），这与 E2 已测的那些插件是不同性质的负担，需要我们自己补测才能说它在我们库里的成本。

**E3（特征预实验 P1）——same_question，not_comparable。** 论文的核心假设是"投毒会在本地模型权重的低频 DCT 分量上留下与良性更新不同的偏移"（Section IV-A，卡片引句 5），E3 问的是同一类问题：恶意客户端的 LoRA 更新在哪个表示上更可区分。E3 观察到的"效果层大小在 20 轮里标出 15 轮"方向上与"权重空间存在可区分信号"一致，但有三点使二者不能直接比较：第一，论文做 DCT 的对象是客户端训练后的本地模型 W_i^t 本身，卡片第 4 节特别指出论文未说明是否改用增量 W_i^t − G^t，而 E3 的效果层（BA 乘积）与因子层（A、B 分开）是两种不同的提取口径，因子层在论文里没有对应物；第二，论文的模型最大约 20M 参数且是完整权重，E3 是 0.5B 模型上的 LoRA r=16；第三，E3 只有 10 个客户端、20 轮、单个种子，论文则完全没有报告种子数（卡片未给）。

**E4（良性基线与校准 P2）——same_question，not_comparable。** 两边都在问"投毒浓度降低后检测还剩多少"。论文一侧：Table IX 报告 PDR = 10% 时无防御 BA 已 91.0、FreqFed 下仍是 0.0，Table X 与 Appendix C 报告 PMR 从 10% 到 49% 均把 BA 压到 0.0，Section V-B1 给出 PMR < 50% 才有效的边界。E4 一侧：在单个恶意客户端上，投毒数据占比 100% 时效果层大小标出 18/18 轮、效果层方向 14/18 轮，占比 30% 时最好 6/18，占比 10% 时只有 1–2/18、与 1% 阈值校准后的误报相当。这里看起来有张力，但不能直接判为矛盾：论文的 PMR 是恶意客户端比例、PDR 是投毒数据率，而 E4 变的是那一个恶意客户端内部的投毒数据占比（更接近 PDR），且论文看的是最终 BA 是否归零、E4 看的是逐轮客户端标出率，两者不是同一个量。另外 E4 的两条发现论文里没有对应：无攻击的良性微调本身就让 AdvBench 无害率从 81% 降到 49–63%（alpaca 模板），以及按 Dolly 类别的 Dirichlet 划分对 LoRA 更新相似度几乎没有影响——后者方向上与论文"不用根数据集、不假设 iid，且 iid = 0.0 仍有效"（Section VII、Figure 2b、Figure 4）相容，但论文的 iid rate 是按标签分布构造的，与我们的 Dirichlet 任务/领域异构不是一回事。

**E5（自动攻击矩阵 P3）——same_question，not_comparable；同时具有 setting_reference 性质。** 同一个问题在于：服务器只靠客户端上传的更新/权重，能否逐轮把恶意客户端挑出来，以及浓度与参与率如何影响它。可以对着看的具体条目是 Section III 的 kA < K/2 前提与 Section V-B1 的"PMR < 50% 时才有效"：E5 最强的场景是 1 个恶意客户端（占 10%）、恶意占比 ≥ 30% 时检出 83–100%、误报 0.6–1.9%，方向上与"少数派可以被挑出"一致。看起来有张力的是 E5 的两个盲区——2–3 个恶意客户端各 10% 投毒时检出只有 3–15%，每轮只抽 5 个客户端时检出只有 24–35%——而论文 Table IX 报告 PDR = 10% 时 BA 仍为 0.0；但论文 Table IX 的 PMR 卡片未给，它的指标是最终 BA 而不是我们的逐轮客户端检出率，它是 Cifar-10 上的完整权重 CNN、我们是 0.5B 模型上的 LoRA，规模差两三个数量级，所以只能说"口径不同、暂不可比"。设置参照方面：论文的 PMR/PDR/iid rate 网格（Table II–X 与 Appendix C 覆盖 PDR 10%–100%、PMR 10%–49%、iid 0.0–0.9）与"MA + BA"的评测口径，正是 E5 这类攻击矩阵应该对齐的参照，但论文未给客户端总数 K、每轮参与率与训练轮数，我们目前也只有 4–20 轮、4–10 个客户端、多数级别 1 个种子。

**E6（已发表防御可用性批量）——method_source，n/a。** E6 的 26 次运行明确把 FreqFed 列进覆盖清单，宿主规模是 Qwen3.5-0.8B 与 4B、5 个客户端、4 轮、每轮 6 步，场景 A 是 4 个良性 + 1 个有害数据客户端、场景 B 是每个客户端 20% 的样本带触发词与固定目标输出；但 E6 只验证端到端跑通、不评价防御效果，卡片也没有给出 FreqFed 专属的读数（样本过滤的那次读数只给了 ProtegoFed 精确率 0.77 / 召回率 0.49，以及谱签名、梯度谱熵、激活聚类接近 0），所以我们对 FreqFed 的唯一自有结果是"能跑通"，与论文的任何 BA/MA 数值都不构成印证或矛盾。E6 同时有 setting_reference 的一面：论文的对照防御清单（Krum、AFA、Median、DP、FoolsGold、BayBFed、FLAME、DeepSight、Auror）与 E6 批量里的 Krum、坐标中位数、FoolsGold、FLAME 等大量重叠，且论文的 Table XI/Table XII 正是"同一场景横比多个防御"的范式，这正是我们 E6/E7 想做的对照结构。

**E7（无攻击对照）——same_question，consistent。** 论文 Table XI 报告其他防御在同一场景下失效：Krum 在 Reddit 上 BA 仍为 100.0，Auror 在 Reddit 上 MA 只有 10.5，FreqFed 是唯一在三处都有效的防御。E7 在完全没有攻击的条件下看到这些防御会大量"误伤"：Krum 仍排除 80% 的客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%，梯度谱熵屏蔽 71% 的样本、ONION 改写 59% 的样本、激活聚类屏蔽 15%、ProtegoFed 屏蔽 4%。二者方向一致的地方是"已发表防御在客户端数少、异质的情况下并不可靠"，我们的结果还给论文那条 MA 偏低（例如 Auror 的 10.5）提供了一个可能的机制，即无攻击时的过度剔除；但要强调，论文测的是攻击下的 MA/BA，我们测的是无攻击下的排除与样本处置比例，而且我们只有 4–5 个客户端、4 轮、单次运行，**不能**与 Table XI 的数值直接比较。

**E8（宿主适配）——background，n/a。** 论文的防御在服务器聚合前运行，只用当前轮全部客户端的上传，不用根数据集、不用历史、不需要模型前向或反向（卡片第 5 节），动作是"只聚合最大簇成员、丢弃其余客户端"（Algorithm 1 第 7 行）。这正是 E8 要验证的挂载契约：服务器侧固定钩子必须能拿到未经处理、未经聚合、未被裁剪的逐客户端完整张量并保留参数名与形状元信息，干预接口必须支持"按子集聚合"而不是只支持打分加权（卡片第 10 节第 1–3 条）。但卡片没有把 FreqFed 单独列进 E8 的插件清单（E8 只给了"18 个服务器侧插件原生挂载、9 个客户端侧插件靠应用配合、ProtegoFed 经一层握手扩展"这类汇总），所以只能算背景。

**E9（Safe-FedLLM 式权重探针）——background，n/a。** 这不是同一个问题：论文没有报告随机种子数量，也没有任何跨种子稳定性结果（卡片未给），其集中式后门（Table X）与 Appendix C 自适应攻击都是单点数值。E9 的教训是同一配置、同一初始化种子下拟合再应用的权重空间探针有效，换一次运行（不同种子）后就失效（恶意客户端概率 0.00）。它不构成对论文的印证或反驳，但提示任何依赖权重空间信号的服务器侧防御都需要跨种子验证，而 FreqFed 恰好没有报告这一点。

**E10（调研与知识库）——background，n/a。** FreqFed 的算子可以拆成"取回逐客户端参数 → 对每个权重矩阵做二维 DCT → 按 i + j ≤ ⌊|V|/2⌋ 截取低频谱 → 构造 K×K 余弦距离 → HDBSCAN → 取最大簇 → 只对该子集聚合"，其中"客户端间关系矩阵"和"按子集聚合"正是卡片第 10 节认为底座应当一等公民化的能力，可以作为 E10 算子覆盖度（39% 直接可表达、39% 要拼、10% 缺算子、13% 超出运行时）的一个检验样本。但卡片未说明 FreqFed 是否已在 E10 的 137 篇逐篇卡片与 45 篇 481 步映射中，所以这里只算背景。

## 3. 我们要与它可比还差什么

**论文侧本身就缺的量（不补齐就只能做定性对照）：** 每类实验的客户端总数 K 与每轮参与率卡片未给（卡片第 7 节），训练轮次 T 论文未报告，种子数量卡片未给。我们自己的预实验是 2–20 轮、4–10 个客户端、多数级别 1 个种子，要对齐必须先明确"跟它的哪一张表比、比的是哪个量"，否则数值对照无从谈起。

**模型规模与上传对象：** 论文最大模型约 20M 参数、完整权重训练与完整权重上传（Table I），我们最大只到 Qwen3.5-4B 的 LoRA 插件开销测量（E2），训练对照是 0.5B/0.8B。更关键的是表示不同：论文对完整权重矩阵做二维 DCT，而 LoRA 上传的是低秩因子；论文未说明非方阵权重矩阵与一维参数（偏置、归一化参数）如何处理，也未说明 |V| 的确切定义、是按整模型还是按层变换后拼接（卡片第 9 节）。我们现有的每一次 FreqFed 运行都必然做过一个论文未规定的适配选择（对 BA 乘积、对 A、对 B，还是对合并后的某层做变换），要把这个选择写进实验记录，否则复现不可比。

**攻击类型与强度网格：** 论文覆盖 Label Flipping、Random Updates、Optimized（PGD）、constrain-and-scale、Edge-case、DBA、3DFed、Mirai Scanning、Neurotoxin、频率触发器、说话人验证后门、图后门、集中式后门与 Appendix C 的自适应攻击（Table II–X）；我们只做了有害问答数据投毒（E3/E4）与"触发词 + 固定目标输出"（E6 场景 B），而项目自己列的空白正是后门攻击成功率评测、知道防御的自适应攻击与上传侧攻击（更新放大、针对防御构造更新、合谋）。强度上，论文给出了 PDR 10%–100% 与 PMR 10%–49% 的两维网格（Table IX、Table X、Appendix C），并报告 PMR ≥ 50% 会失效的边界（Section V-B1、Figure 2a 等）；我们目前变的是单个客户端内部的投毒数据占比（E4 的 10%/30%/100%）与恶意客户端个数（E5 的 1 个、2–3 个），**没有做过恶意客户端比例的扫描**，更没有碰过 PMR ≥ 50% 的失效边界。

**指标：** 论文用主任务准确率 MA 与后门准确率 BA（Section V-A），并且用"BA 是否降到 0.0"来体现检测成功；我们的检测实验用的是逐轮客户端检出率与误报率（E5 的 83–100% / 0.6–1.9%，E4 的 x/18 轮），两者不是同一个量。要在生成式模型上跟它比，需要先定义与 BA 对应的指标（触发词命中率或对有害提示的顺从率），并为每个设置提供无攻击基线；论文的无攻击参考值（Cifar-10 77.3、MNIST 98.6、EMNIST 81.3，Table II）在我们这里没有对应物，E4 的 AdvBench 无害率 81% → 49–63% 是安全性指标、不是主任务准确率，不能替代。此外论文不报告逐客户端检测率与误报率，我们也没法用它的数字校准我们的 1% 误报阈值。

**重复与置信区间：** 论文种子数卡片未给，我们多数级别只有 1 个种子（E4 的良性基线是 4 种划分各 3 个种子）；在做任何数值对照前，需要统一重复次数并报告区间，否则 E3/E4/E5 的轮级计数（15/20、17/20、18/18、3–15%）无法与论文的单点 BA/MA 并置。

**开销：** 论文完全未报告开销（卡片第 8 节），所以"与论文比开销"这件事不可行，只能我们自己测 FreqFed 在 LoRA 上的 DCT + K×K 余弦距离 + HDBSCAN 成本，并明确它对应的是 4×RTX 8000、最大约 20M 参数、完整权重上传的场景，与我们的 0.5B–4B LoRA 不可比。

**复现与记录口径：** 论文自身有两处不一致会直接影响复现——聚合到底是按样本数加权的 FedAvg（公式 (1)）还是对被接受模型的等权平均（Algorithm 1 第 7 行），以及过滤究竟在服务器还是客户端（摘要对 Section IV-B/IV-C、Figure 1、Algorithm 1）；我们需要选定并记录一种口径。数据分布上，论文的 iid rate 按标签构造（Section V-A），我们用的是按 Dolly 类别的 Dirichlet 划分（E3/E4），两种非 iid 的定义要先写清楚，E4"Dirichlet 划分对 LoRA 更新相似度几乎没有影响"这条观察才有资格与论文 iid = 0.0 的结果（Figure 2b、Figure 4）对话。

**客户端数下限：** 论文未给 K 与参与率，而 E5 显示每轮只抽 5 个客户端就会把检出压到 24–35%。FreqFed 的"取最大簇"依赖本轮有足够多的客户端可供聚类，所以我们需要至少一个 K 与参与率可比的设置，才能判断它在我们这种小规模联邦里是否还有意义。

```json
{
  "key": "fereidooni2024freqfed",
  "paper_scale": {
    "models": "九个数据集与完整权重模型（Table I、Section V-A、Appendix A）：Reddit 20.6M 条记录 / LSTM 约 20M 参数；IoT-Traffic 65.6M / GRU 约 507k；Cifar-10 60.0k / ResNet-18 Light 约 2.7M；MNIST 70.0k / CNN 约 431k；EMNIST 814.2k / LeNet 约 66k；TIMIT 201.6k / LSTM 约 12M；PROTEINS 1113 / GraphSage 约 102k；NCI1 4110 / GAT 约 101k；D&D 1178 / GCN 约 106k、GatedGCN 约 104k、MoNet 约 102k；无 LLM、无 PEFT/LoRA，全部完整权重训练与上传",
    "clients": "卡片未给：论文只给出 PMR 与 PDR 的取值范围与 kA < K/2 的前提（Section III、卡片第 7 节），未给客户端总数 K 与每轮参与率",
    "rounds": "卡片未给：论文未报告训练轮次 T（卡片第 7 节）",
    "poison_setting": "以 PMR 与 PDR 标定：无目标攻击 PMR=49%、iid=0.7（Table II）；图像域定向攻击 PDR=50%、PMR=30%、iid=0.9（Table III）；Reddit 文本 PDR=50%、PMR=25%（Table IV）；说话人验证数据投毒 PDR=0.49、模型投毒 PMR=0.49（Table V）；图分类 PDR=25%、PMR=49%（Table VI）；自适应频率域攻击 PDR=50%、PMR=25%、iid=0.7、α=0.7（Table VII）；良性频率注入 PDR=50%、PMR=30%、iid=0.7（Table VIII）；频率触发器 PDR 10 到 100、iid=0.8（Table IX）；集中式后门 PMR 10% 到 49%、iid=0.0（Table X）；Appendix C 覆盖 10%≤PDR≤100% 与 10%≤PMR≤49%",
    "seeds": "卡片未给：论文未报告种子数量与跨种子稳定性",
    "federated": true,
    "lora": false
  },
  "headline_results": [
    "Table XI（PMR=25% 的 constrain-and-scale）：FreqFed 是唯一在 Reddit、Cifar-10、IoT-Traffic 三处都有效的防御，BA 分别为 0.0、0.0、0.0，MA 分别为 22.6、86.5、96.5；同一表中 Krum 在 Reddit 上 BA 仍为 100.0，Auror 在 Reddit 上 MA 只有 10.5。",
    "Table III（PDR=50%、PMR=30%、iid=0.9）：图像域单后门像素模式无防御 BA 100.0 / MA 85.5，FreqFed BA 0.0 / MA 91.9；DBA 像素模式无防御 BA 93.8 / MA 57.4，FreqFed BA 0.4 / MA 76.2；自适应频率域攻击在 Table VII 下同样 BA 0.0（Known-Benign 与 Unknown Benign 两种）。",
    "Table II（无目标攻击、PMR=49%、iid=0.7）：Cifar-10 从无攻击 MA 77.3 到无防御 35.8、FreqFed 77.1；MNIST 98.6 到 50.8 到 97.8；EMNIST 81.3 到 13.4 到 81.2；Section V-B1 与 Figure 2a、Figure 3a、Figure 5、Figure 6a、Figure 6b、Figure 7 报告 PMR 小于 50% 有效、PMR 大于等于 50% 可能失效。"
  ],
  "links": [
    {
      "experiment": "E1",
      "relation": "background",
      "agreement": "n/a",
      "detail": "论文的干预只在服务器每轮聚合之前发生（卡片第 1 节与第 6 节，Algorithm 1 第 1 到 7 行），不改变客户端本地训练、上传内容与轮数，因此它属于 E1 需要保证挂上不动作就不改变训练的那类服务器侧插件；但卡片没有说明 E1 具体挂了哪些插件，论文侧也没有等价性实验，所以只算背景。卡片第 1 节还指出论文自身对过滤位置自相矛盾：摘要说在客户端本地训练期间过滤，Section IV-B、Section IV-C、Figure 1 与 Algorithm 1 都把 DCT、滤波与聚类放在服务器执行。"
    },
    {
      "experiment": "E2",
      "relation": "background",
      "agreement": "n/a",
      "detail": "论文第 8 节明确未报告计算、通信与存储开销的任何数字，只给硬件配置（Section V-A：4 张 NVIDIA RTX 8000 每张 48GB、AMD EPYC 7742、1024 GB 内存），也未讨论参数量远大于 Table I 时的可扩展性；卡片第 8 节的分析是服务器端每轮要对每个客户端全部权重做一次 DCT、构造 K×K 余弦距离矩阵并运行 HDBSCAN，余弦距离部分为 O(K²·d)。因此 E2 的 0.7% 到 2.8% 客户端采集开销、0.25% 到 1.8% 服务器统计插件开销，以及 ProtegoFed 逐样本梯度每客户端每轮 3.8 秒、更新子空间投影 5.7 秒、ONION 3.2 秒这些读数，在论文中都没有对应数值，只能把它的流水线列为我们的开销测量对象。"
    },
    {
      "experiment": "E3",
      "relation": "same_question",
      "agreement": "not_comparable",
      "detail": "论文的核心假设是投毒客户端的本地权重会在低频 DCT 分量上留下与良性客户端不同的偏移（Section IV-A，卡片引句 5），E3 问的是同一类问题，即恶意客户端的 LoRA 更新在哪个表示上更可区分。E3 的效果层大小在 20 轮里标出 15 轮，方向上与权重空间存在可区分信号一致；但论文做 DCT 的对象是训练后的本地模型 W_i^t 本身，卡片第 4 节指出论文未说明是否改用增量 W_i^t 减 G^t，而 E3 的因子层把 A、B 分开在论文里没有对应物。论文最大模型约 20M 参数且是完整权重，E3 是 0.5B 模型上的 LoRA r=16、10 个客户端全员参与、FedAvg 20 轮、单种子，规模与表示都不同，不能直接比较。"
    },
    {
      "experiment": "E4",
      "relation": "same_question",
      "agreement": "not_comparable",
      "detail": "两边都在问投毒浓度降低后检测还剩多少。论文一侧 Table IX 报告 PDR=10% 时无防御 BA 已 91.0、FreqFed 下为 0.0，Table X 与 Appendix C 报告 PMR 10% 到 49% 均把 BA 压到 0.0，Section V-B1 给出 PMR 小于 50% 才有效；E4 一侧在单个恶意客户端上投毒占比 100% 时效果层大小标出 18/18 轮、效果层方向 14/18 轮，占比 30% 时最好 6/18，占比 10% 时只有 1 到 2/18、与 1% 阈值校准后的误报相当。这里看起来有张力但不能直接判为矛盾：论文的 PMR 是恶意客户端比例、PDR 是投毒数据率，E4 变的是那一个恶意客户端内部的投毒数据占比（更接近 PDR），论文看的是最终 BA 是否归零、E4 看的是逐轮客户端标出率。E4 另有两条论文没有的发现：无攻击良性微调本身让 AdvBench 无害率从 81% 降到 49% 到 63%，以及按 Dolly 类别的 Dirichlet 划分对 LoRA 更新相似度几乎没有影响；后者方向上与论文不用根数据集、不假设 iid 且 iid=0.0 仍有效（Section VII、Figure 2b、Figure 4）相容，但论文的 iid rate 按标签构造，与我们的 Dirichlet 任务与领域异构不是一回事。"
    },
    {
      "experiment": "E5",
      "relation": "same_question",
      "agreement": "not_comparable",
      "detail": "同一个问题是服务器只靠客户端上传的更新或权重，能否逐轮挑出恶意客户端，以及浓度与参与率如何影响它。可对照的具体条目是 Section III 的 kA 小于 K/2 前提与 Section V-B1 的 PMR 小于 50% 才有效：E5 在 1 个恶意客户端（占 10%）、恶意占比大于等于 30% 时检出 83% 到 100%、误报 0.6% 到 1.9%，方向上与少数派可被挑出一致。看起来有张力的是 E5 的两个盲区：2 到 3 个恶意客户端各 10% 投毒时检出只有 3% 到 15%，每轮只抽 5 个客户端时只有 24% 到 35%，而论文 Table IX 报告 PDR=10% 时 BA 仍为 0.0。但论文 Table IX 的 PMR 卡片未给，它的指标是最终 BA 而不是我们的逐轮客户端检出率，它是 Cifar-10 上的完整权重 CNN、我们是 0.5B 模型上的 LoRA，规模差两三个数量级，所以只能说口径不同、暂不可比。E5 还有把行为探针分数跨轮累积后 37 个恶意客户端中 33 个超过全部良性客户端这一结果，论文没有对应的探针式检测量。"
    },
    {
      "experiment": "E5",
      "relation": "setting_reference",
      "agreement": "not_comparable",
      "detail": "论文的 PMR 与 PDR 网格（Table II 到 Table X 与 Appendix C 覆盖 PDR 10% 到 100%、PMR 10% 到 49%、iid 0.0 到 0.9）与主任务准确率 MA 加后门准确率 BA 的评测口径，是 E5 这类攻击矩阵该对齐的参照。但论文未给客户端总数 K、每轮参与率与训练轮数，我们目前是 4 到 20 轮、4 到 10 个客户端、多数级别 1 个种子，指标是逐轮检出与误报率，尚不可对齐。"
    },
    {
      "experiment": "E6",
      "relation": "method_source",
      "agreement": "n/a",
      "detail": "E6 的 26 次运行明确把 FreqFed 列入覆盖清单，宿主规模为 Qwen3.5-0.8B 与 4B、5 个客户端、4 轮、每轮 6 步，场景 A 是 4 个良性加 1 个有害数据客户端，场景 B 是每个客户端 20% 样本带触发词与固定目标输出；但 E6 只验证端到端跑通、不评价防御效果，卡片也没有给出 FreqFed 专属读数（样本过滤那次读数只给了 ProtegoFed 精确率 0.77 与召回率 0.49，以及谱签名、梯度谱熵、激活聚类接近 0），所以我们对 FreqFed 的唯一自有结果是能跑通，与论文的任何 BA 或 MA 数值都不构成印证或矛盾。E6 同时有 setting_reference 的一面：论文的对照防御清单 Krum、AFA、Median、DP、FoolsGold、BayBFed、FLAME、DeepSight、Auror 与 E6 批量里的 Krum、坐标中位数、FoolsGold、FLAME 等大量重叠，Table XI 与 Table XII 正是同一场景横比多个防御的范式。"
    },
    {
      "experiment": "E7",
      "relation": "same_question",
      "agreement": "consistent",
      "detail": "论文 Table XI 报告其他防御在同一场景下失效，Krum 在 Reddit 上 BA 仍为 100.0，Auror 在 Reddit 上 MA 只有 10.5，FreqFed 是唯一在三处都有效的防御；E7 在完全没有攻击的条件下看到这些防御大量误伤：Krum 仍排除 80% 的客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%，梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本、激活聚类屏蔽 15%、ProtegoFed 屏蔽 4%。方向一致之处是已发表防御在客户端数少、异质时并不可靠，我们的结果还为论文里那些偏低的 MA（例如 Auror 的 10.5）提供了一个可能机制，即无攻击时的过度剔除。但论文测的是攻击下的 MA 与 BA，我们测的是无攻击下的排除与样本处置比例，我们只有 4 到 5 个客户端、4 轮、单次运行，不能与 Table XI 的数值直接比较。"
    },
    {
      "experiment": "E8",
      "relation": "background",
      "agreement": "n/a",
      "detail": "论文的防御在服务器聚合前运行，只用当前轮全部客户端上传，不用根数据集、不用历史、不需要前向或反向计算（卡片第 5 节），动作是只聚合最大簇成员并丢弃其余客户端（Algorithm 1 第 7 行）。这正是 E8 要验证的挂载契约：服务器侧固定钩子必须拿到未经处理、未经聚合、未被裁剪的逐客户端完整张量并保留参数名与形状元信息，干预接口必须支持按子集聚合而不是只支持打分加权（卡片第 10 节第 1 到 3 条）。但卡片没有把 FreqFed 单独列进 E8 的插件清单（E8 只给 18 个服务器侧插件原生挂载、9 个客户端侧插件靠应用配合、ProtegoFed 经一层握手扩展这类汇总），所以只能算背景。"
    },
    {
      "experiment": "E9",
      "relation": "background",
      "agreement": "n/a",
      "detail": "这不是同一个问题：论文没有报告随机种子数量，也没有任何跨种子稳定性结果（卡片未给），其集中式后门（Table X）与 Appendix C 自适应攻击都是单点数值。E9 的教训是同一配置、同一初始化种子下拟合再应用的权重空间探针有效，换一次运行（不同种子）后就失效（恶意客户端概率 0.00）。它不构成对论文的印证或反驳，但提示任何依赖权重空间信号的服务器侧防御都需要跨种子验证，而 FreqFed 恰好没有报告这一点。"
    },
    {
      "experiment": "E10",
      "relation": "background",
      "agreement": "n/a",
      "detail": "FreqFed 的算子可以拆成取回逐客户端参数、对每个权重矩阵做二维 DCT、按 i 加 j 小于等于 floor(|V|/2) 截取低频谱、构造 K×K 余弦距离、运行 HDBSCAN、取最大簇、只对该子集聚合，其中客户端间关系矩阵与按子集聚合正是卡片第 10 节认为底座应当一等公民化的能力，可以作为 E10 算子覆盖度（39% 直接可表达、39% 要拼、10% 缺算子、13% 超出运行时）的一个检验样本。但卡片未说明 FreqFed 是否已在 E10 的 137 篇逐篇卡片与 45 篇 481 个步骤映射中，所以只算背景。"
    }
  ],
  "missing_for_comparability": [
    "模型规模与上传对象：论文最大约 20M 参数的完整权重模型（Table I），我们最大只到 Qwen3.5-4B 的 LoRA 插件开销测量；要对齐需要 7B 及以上的完整训练，或先明确定义在 LoRA 上对哪个张量做二维 DCT（BA 乘积、A、B 还是合并结果），以及一维参数与偏置如何处理，因为论文未说明这些规则（卡片第 9 节）",
    "轮数与客户端数：论文未报告训练轮次 T、客户端总数 K 与每轮参与率（卡片第 7 节），我们需要先在论文侧补齐这两个量，或明确把对比降级为同口径的定性比较；我们自己是 2 到 20 轮、4 到 10 个客户端",
    "攻击类型：论文覆盖 Label Flipping、Random Updates、Optimized（PGD）、constrain-and-scale、Edge-case、DBA、3DFed、Mirai Scanning、Neurotoxin、频率触发器、说话人验证后门、图后门、集中式后门与 Appendix C 自适应攻击（Table II 到 Table X），我们只有有害问答数据投毒与触发词加固定目标输出两种，且项目自己列出的空白正是后门攻击成功率评测、知道防御的自适应攻击与上传侧攻击",
    "攻击强度网格：需要补 PMR（恶意客户端比例）维度的扫描，尤其 PMR 大于等于 50% 的失效边界（Section V-B1、Figure 2a），同时覆盖我们已观察到的低浓度盲区（E4 投毒占比 10% 时 1 到 2/18、E5 2 到 3 个恶意客户端各 10% 时 3% 到 15%）；现有实验变的是投毒数据占比而不是恶意客户端比例，口径要先统一",
    "指标：论文用 MA 与 BA 并以 BA 是否降到 0.0 体现检测成功，我们需要在生成式模型上定义与 BA 对应的指标（触发词命中率或对有害提示的顺从率），并给出每个设置的无攻击基线；论文的无攻击 MA 参考值如 Cifar-10 77.3、MNIST 98.6、EMNIST 81.3（Table II）在我们这里没有对应物，E4 的 AdvBench 无害率 81% 到 49% 到 63% 是安全性指标而非主任务准确率",
    "种子与置信区间：论文种子数卡片未给，我们多数级别只有 1 个种子（E4 良性基线为 4 种划分各 3 个种子）；做数值对照前需要统一重复次数并报告区间",
    "开销：论文未报告任何开销数字（卡片第 8 节），要对齐只能我们自己测 FreqFed 在 LoRA 上的 DCT、K×K 余弦距离与 HDBSCAN 成本，并说明与论文场景（4 张 RTX 8000、最大约 20M 参数、完整权重上传）不可比",
    "复现口径：论文对聚合是按样本数加权的 FedAvg（公式 (1)）还是对被接受模型等权平均（Algorithm 1 第 7 行）自相矛盾，对过滤位置也有摘要与正文的矛盾，我们需要选定并记录一种口径",
    "数据分布定义：论文的 iid rate 按标签构造非 iid（Section V-A，iid=0.0 仍有效，Figure 2b 与 Figure 4），我们用按 Dolly 类别的 Dirichlet 划分；两种非 iid 的定义需要先写清楚，E4 关于 Dirichlet 划分对 LoRA 更新相似度几乎无影响的观察才有资格与论文对话",
    "客户端数下限与参与率：论文未给 K，而 E5 显示每轮只抽 5 个客户端时检出只有 24% 到 35%；FreqFed 取最大簇依赖本轮有足够多的客户端，我们需要至少一个 K 与参与率可比的设置才能判断它是否在我们的小规模联邦里仍然成立"
  ],
  "metrics_paper_uses": [
    "主任务准确率 MA（Section V-A，Table II 到 Table XII 全篇使用）",
    "后门准确率 BA，也称攻击成功率（Section V-A，Table III 到 Table X 等）",
    "论文不以逐客户端检测率或误报率作为指标，而是用最终 BA 是否降到 0.0 来体现检测成功"
  ],
  "relevance": "high"
}
```
