# rosati2024repnoise：Representation Noising: A Defence Mechanism Against Harmful Finetuning

## 1. 基本信息

- **论文标题**：Representation Noising: A Defence Mechanism Against Harmful Finetuning（表示加噪：一种针对有害微调的防御机制）。
- **发表信息**：NeurIPS 2024（第 38 届神经信息处理系统大会），arXiv:2405.14577v4，2024 年 10 月 30 日。
- **场景**：集中式大模型训练（centralized large language model training），更准确地说是"安全对齐模型在权重发布前的免疫训练"。论文全文不涉及联邦学习（federated learning）：没有客户端（client）、服务器（server）、聚合（aggregation）、参与率等任何概念。防御者是模型发布方，攻击者是拿到权重之后的下游微调者。
- **训练阶段**：防御发生在模型发布前的对齐/免疫（immunization）训练阶段；攻击发生在权重发布之后的下游监督微调（supervised fine-tuning，SFT）阶段。
- **论文类型**：防御（defence）。第 5 节是机制分析（mechanistic analysis），不是运行时检测方法。
- **模型与数据规模**：主实验用 llama-2-7b-chat；附录 K 扩展到 llama-2-13b-chat 与 Qwen 1.5 系列（0.5B、1.8B、4B、7B），附录 K.1 用未做安全对齐的 llama-2-7b。攻击与防御数据主要是 BeaverTails 的有害问答（harmful question answering，HarmfulQA），主实验使用其中 10k 对配对样本（附录 B.2）；BeaverTails 原始规模为 333,963 个问答对、14 类危害（附录 D.1）。毒性任务使用 DecodingTrust 的 Real Toxicity Prompts 划分，共 351 条（第 4.1 节、附录 D.2）。
- **与 LoRA 的关系**：主方法 RepNoise 是**全参数**免疫训练，不使用 LoRA 或任何参数高效微调（parameter-efficient fine-tuning，PEFT）。LoRA 只出现在 Security Vectors 这一个基线中（附录 F）。因此下文的 `uses_lora_or_peft` 记为 false。

## 2. 威胁模型

**攻击者**

- **身份**：拿到模型权重的下游行为者。摘要指出，即使不开源权重，权重窃取（weight stealing）与微调 API（fine-tuning APIs）也使闭源模型暴露于有害微调攻击（harmful fine-tuning attack，HFA）。所以攻击者是权重持有者/下游微调者，不是联邦客户端、不是数据提供方、也不是适配器发布者。
- **占比或数量**：不适用。论文没有多方设置，不存在恶意客户端比例这一维度。
- **能力**：攻击者能用自己的有害数据集 D_harmful 对模型做完整的监督微调，即最小化该数据集上的因果语言建模损失（causal language modeling loss），把模型调向有害行为（第 2 节 eq. (1)）。攻击强度由学习率与样本量控制：论文使用 1k 与 10k 样本、学习率 {3×10⁻⁵, 6×10⁻⁵, 8×10⁻⁵}（第 4.1 节、附录 C）。攻击者不使用后门触发器，也不做数据投毒，只是在自己手里做普通微调。
- **知识**：拥有模型权重，知道自己的有害数据。论文没有说明攻击者是否知道防御机制的存在。
- **目标**：破坏安全对齐（jailbreak／安全对齐破坏），使模型对有害问题给出顺从回答，或在毒性提示后生成高毒性续写。不是无目标破坏、不是定向后门、不是隐私窃取。

**防御者**

- **身份**：模型发布方/开发者。
- **能看到什么**：发布前的模型权重 θ（t=0 时刻），以及自己收集的成对样本（有害问题配有害回答，同一问题配安全拒绝回答）。看不到攻击者的数据，也看不到攻击过程。
- **信任什么**：信任自己的防御数据与攻击数据同分布；信任模型自身的因果语言建模训练流程。论文明确说明防御者在攻击者获得权重之后无法干预。
- **关键区分**：论文把自身与另一类防御区分开。Security Vectors、Vaccine、Lazy safety alignment 等方法假设"防御者保留对微调过程的控制"；本文只考虑防御者失去控制、只能影响初始权重的场景（第 6 节）。

## 3. 攻击入口与流程位置

**攻击入口**：论文研究的 HFA 位于攻击者自己的**本地训练过程**。步骤为：攻击者取得安全对齐模型权重 θ（t=0）；准备有害数据集 D_harmful，由提示 X 与目标回答 Y 组成；用标准因果语言建模损失对模型参数做监督微调，得到 θ（t*）；当安全指标 g(M_θ) 超过防御者设定的阈值 φ 时，攻击被判定成功（第 2 节）。攻击不经过"更新上传前处理"、"服务器聚合"或"全局模型下发"环节，因为论文的流程里根本不存在这些环节。

**防御入口**：RepNoise 位于模型发布方的**发布前训练循环**，即对初始权重 θ（t=0）做的那一次免疫训练。论文的表述是：作为防御者，我们只能影响初始权重集合 θ（t=0），目标是修改模型权重以最小化转移概率（第 3 节）。权重一旦发布，防御者不再有任何动作。

**与联邦流程的对应关系**：论文没有研究联邦流程。分析：若强行映射到"本地数据准备、本地训练、上传前处理、服务器聚合、全局下发、评估部署"这条链，攻击对应的是下游微调者的本地训练环节，防御对应的是模型生产方在全局模型下发之前的训练环节；服务器聚合、更新后处理等位置在本文中没有对应内容。

## 4. 方法原理

**核心思想**：现有安全机制只是抑制或绕开被保留下来的有害表征，微调可以轻易把它们恢复出来。RepNoise 的目标是在权重发布前就把有害文本序列的中间激活（表征）中的信息结构去掉，使攻击者在后续微调中难以重新学到（第 1 节、第 3 节）。

**理论推导**：论文借用 Achille 等人的转移概率（transition probability）模型，把从初始权重训练到有害任务最优点 θ* 的似然近似分解为静态势（static potential）与可达性（reachability）两项，见 eq. (2)。定理 1 声称：最小化该转移概率的初始权重，正是最小化网络输入 X 与中间激活 Z_θ 之间互信息 I(X; Z_θ) 的权重（第 3 节，证明在附录 A.3）。依据信息瓶颈（information bottleneck）与数据处理不等式（data processing inequality）I(Y; X) ≤ I(Z; X)，最小化 I(X; Z) 同时也会最小化 I(X; Y)。

**三部分损失**：论文把优化目标拆成三项（eq. (4)、eq. (5)）：

1. **稳定性项** ℓ_stability：在无害样本上的普通因果语言建模损失，用来保住模型能力。
2. **梯度上升项** ℓ_ascent：在有害样本上做梯度上升，形式上等价于最大化 ℓ_ascent = E[L(M_θ(X_harmful), Y_harmful)]（eq. (3)），用于破坏模型对有害输出的预测能力。
3. **噪声项** ℓ_noise：把有害输入对应的表征分布推向标准高斯噪声 N(0, I)，正文写作 KL(p(Z|X) ‖ N(0, I))。若两个分布相同，Z 就不再携带 X 的信息。

总损失为 L_RepNoise = ℓ_stability + α·ℓ_noise − β·ℓ_ascent（eq. (5)）。

**实现细节**（附录 B.1 与算法 1）：

- 由于拿不到真实分布，用多核最大均值差异（multi-kernel Maximum Mean Discrepancy，MMD）配高斯核替代 KL 散度，因为它可微且能由样本估计。
- 逐层施加：作用于每一层 MLP 之后、残差相加之前的激活。论文给出的理由是残差相加后表征会变得与上一层相似，从而丢失该层的独有信息；论文也试过注意力之后的激活，效果不如前者。
- 在每层激活上接语言模型头（language model head）计算该层的语言建模损失，做法类似 tuned lens。
- 使用掩码（MASK）：成对样本共享的提示 token 不做梯度上升也不加噪，以免破坏模型理解有害请求并以安全方式回答的能力。
- 实践中 ℓ_ascent 数值很大，因此取其对数。算法 1 给出的总损失是 ℓ_stability + β·(1/L)Σℓ_noise^l − α·log((1/L)Σℓ_ascent^l)。

**两处论文内部不一致，需如实记录**：其一，正文 eq. (4)/(5) 用 α 加权噪声项、β 加权梯度上升项，而算法 1 与附录 B.1 的角色相反（附录 B.2 报告主实验取 α = 1、β = 0.001，并说明 β 控制噪声项）。其二，第 4.1 节写 "RepNoise minimizes eq. (1)"，而第 3 节给出的方法公式是 eq. (5)。分析：以算法 1 与附录 B.1 的超参数说明为准更可靠，这两处应视为笔误。

**为什么有效**：第 5 节通过冻结层实验证明防御的"深度"是关键：冻结最前面 10 层会让防御完全失效（表 6）。逐层 token log 概率分析（图 3）显示，浅层防御（对抗损失）主要在最后几层压低有害 token 的概率，而 RepNoise 在各层的压低更均匀。

## 5. 检测或防御所需的数据

本文是防御论文，因此本节列出 RepNoise 运行所需要的每一种输入。

**1. 成对的有害与无害样本（paired harmful and harmless samples）**

- 是什么：每条有害问题配一个有害回答，以及同一问题的安全回答（拒绝或说明为何有害），论文称之为 paired refusals。
- 在哪里采集：防御方在发布前的免疫训练阶段准备。附录 D.1 说明，作者先用 llama2-7b-chat 对不安全问题生成回答，再用有害性分类器筛出真正安全的回答，最终得到 18,106 条样本的数据集；主实验用其中 10k 对（附录 B.2）。
- 粒度：逐样本，且必须成对（两条样本共享问题部分）。
- 是否需要干净参考数据：需要。附录 J 明确说方法依赖成对拒绝数据，没有它防御会"much more fragile"。
- 是否需要额外前向或反向计算：需要，生成拒绝回答并跑分类器筛选。
- 是否需要跨轮历史、其他客户端数据：都不需要，论文中没有这些概念。

**2. 逐层中间激活（intermediate activations）**

- 是什么：每一层 MLP 之后、残差相加之前的激活张量，规模约为 token 数乘隐藏维度，论文称其为很大的对象。
- 在哪里采集：防御方免疫训练每一步的前向传播中，作用于去掉共享问题 token 后的有害样本。
- 粒度：逐层、逐 token、逐批。
- 额外计算：需要，必须在训练循环里挂前向钩子取中间激活。

**3. 逐层语言模型头输出**

- 是什么：把语言模型头接到每层激活上算出的该层语言建模损失（ℓ_ascent^l 与 ℓ_noise^l 的输入）。
- 在哪里采集：免疫训练每一步，逐层顺序计算。
- 粒度：逐层。
- 额外计算：需要。附录 L 明确说耗时主要来自逐层顺序迭代，每层都要经过最终语言模型头做一次前向。

**4. 高斯噪声样本 N(0, I)**：噪声损失在线采样得到，不是外部数据，但每次训练步都需要。

**5. 共享 token 掩码**：成对样本中问题部分共享的 token 集合，用来排除这些位置上的加噪与梯度上升。

**6. 无害样本上的稳定性损失**：标准因果语言建模损失，逐批计算，不需要额外数据。

**7. 超参数**：α、β、学习率、epoch 数、随机种子。附录 J 显示方法对这些极其敏感：表 16 显示学习率从 2×10⁻⁵ 换成 4×10⁻⁵ 就让攻击后分数从 0.12 变成 0.74；表 19 显示随机种子 42、7、17 的结果差异很大。

**8. 评估阶段的判定器**：表 1 使用在 BeaverTails 上训练的有害性分类器（DeBERTaV3-xsmall，F1 = 0.87，附录 D.1.1）；表 2 使用 Perspective API 毒性分数（第 4.1 节）。

**论文报告的攻击痕迹（第 5 节，用于机制解释而非在线检测）**

- 有害微调会在权重上留下逐层 L2 变化（图 2）。对浅层防御（对抗损失），变化集中在最后几层；RepNoise 的变化在层间更均匀。
- 攻击会改变逐层 token 对数概率（图 3），成功攻击会缩小有害与无害序列的分布差异（附录 J、图 9）。
- 攻击**不会**提高线性探针判断输入是否有害的准确率（图 5a），论文据此认为有害微调主要是复用模型中已有的有害信息，而不是学到新信息。
- 论文没有讨论攻击者如何规避检测，因为论文没有提出任何检测器。分析：第 5 节的这些量（逐层权重差、逐层线性探针、逐层 log 概率、末层激活的 PCA）可以被我们改造成检测特征，但论文没有给出阈值、在线流程或假阳性评估。

## 6. 干预动作

- **动作类型**：唯一的干预是**修改模型权重**（修复模型），即对发布前的基座模型做一次添加了噪声项与梯度上升项的免疫训练。没有剔除客户端、没有重新加权、没有裁剪、没有在聚合时加噪、没有过滤样本、没有回滚、没有仅报告。
- **动作位置**：发生在模型生产方自己的本地训练循环里，位于训练损失这一层；论文明确说防御者只能影响初始权重（第 3 节）。
- **发布之后的动作**：没有。论文明确说"在攻击者取得权重之后，防御者无法干预"（第 3 节），并据此与需要控制微调过程的防御（Security Vectors、Vaccine、Lazy safety alignment）划清界限（第 6 节）。
- **作为对照的其他干预**：Security Vectors 基线在攻击者的前向传播中激活一个冻结的 LoRA 适配器，属于推理期的干预，而论文报告它只提供部分抵抗（表 1、表 2）。

## 7. 实验设置与主要结果

**模型**：llama-2-7b-chat（主实验）、llama-2-13b-chat、Qwen 1.5（0.5B、1.8B、4B、7B），附录 K.1 另测未对齐的 llama-2-7b。

**数据集**：BeaverTails HarmfulQA（攻击与防御各用 10k 样本，14 类危害）；DecodingTrust 的 Real Toxicity Prompts 划分（351 条攻击样本，4 个 epoch）；GEM 的 ViGGO、E2E NLG、DART、CACAPO、ConvWeather（可训练性）；Eleuther AI LM Evaluation Harness 的 TruthfulQA、MMLU、Hellaswag、Winogrande、ARC-easy、Ethics、CrowS-Pairs（稳定性）；附录另用 HEX-PHI（330 个有害问题）、XSTest（250 个安全提示与 200 个不安全提示）、HarmBench（64 个测试用例）、ROBBIE（偏见）。防御与攻击的超参数见附录 B.2，攻击设置见附录 C。

**客户端数、参与率、轮次、恶意比例、是否非独立同分布**：论文未涉及，因为不是联邦学习设置。与之对应的量是训练轮数与样本数：BeaverTails 攻击 1 个 epoch，RTP 攻击 4 个 epoch；防御在 BeaverTails 上 1 个 epoch、10k 对样本，在 RTP 上 4 个 epoch、学习率 2×10⁻⁵、α = 2、β = 4（附录 B.2）。

**指标**：有害性分类器分数的均值（越低越好）、Perspective API 毒性分数、ROUGE-1、LM Harness 各任务准确率、攻击成功率。

**关键结果**

- **抵抗性（表 1）**：llama-2-7b-chat 基线攻击前为 0.05，在 3×10⁻⁵/6×10⁻⁵/8×10⁻⁵ 学习率与 1k/10k 样本下攻击后升到 0.47、0.74、0.73、0.72、0.74、0.73。RepNoise 为 0.05，攻击后为 0.08、0.12、0.10、0.13、0.11、0.12。论文称 RepNoise 是唯一在所有攻击上都稳定提供显著抵抗的方法（Mann-Whitney U 检验，p < 0.001）。Security Vectors 为 0.05 与 0.07、0.08、0.23、0.37、0.52、0.66；额外安全训练为 0.05 与 0.75、0.76、0.75、0.75、0.76、0.74，几乎没有抵抗。
- **毒性任务（表 2）**：基线 0.24，攻击后 0.40、0.74、0.71；RepNoise 0.17，攻击后 0.00、0.05、0.07，论文称每种设置下都完整抵抗。对抗损失为 0.00 与 0.00、0.77、0.78。
- **稳定性（表 3）**：基线与 RepNoise 分别为 TruthfulQA 0.38/0.37、MMLU 0.46/0.45、Hellaswag 0.58/0.57、Winogrande 0.66/0.66、ARC 0.74/0.72、Ethics 0.59/0.60、CrowS 0.64/0.63。论文结论是能力没有退化。
- **可训练性（表 4）**：GEM 任务的 ROUGE-1（微调前/后），ViGGO 基线 0.19/0.83 对 RepNoise 0.20/0.83，E2E NLG 0.20/0.74 对 0.25/0.74，DART 0.23/0.53 对 0.25/0.53，CACAPO 0.18/0.66 对 0.18/0.67，ConvWeather 0.06/0.25 对 0.08/0.25。同一张表还报告无害微调后再做 3×10⁻⁵ @ 1k 攻击的有害性：基线为 0.03/0.75、0.05/0.65、0.05/0.69、0.06/0.67、0.05/0.55，RepNoise 为 0.00/0.00、0.16/0.01、0.00/0.00、0.02/0.27、0.01/0.08。论文特别指出 CACAPO 上 RepNoise 出现小幅上升，提示无害微调有可能削弱防御。
- **泛化（表 5）**：留出 5 类危害不做防御训练，再用未见过的样本攻击。3×10⁻⁵ 时基线为 0.49、0.51、0.40、0.52、0.53、0.35，RepNoise 为 0.08、0.05、0.06、0.09、0.01、0.08；6×10⁻⁵ 时基线 0.76、0.75、0.76、0.75、0.81、0.76，RepNoise 0.10、0.09、0.10、0.09、0.00、0.12；8×10⁻⁵ 时基线 0.77、0.75、0.80、0.74、0.76、0.74，RepNoise 0.13、0.12、0.12、0.14、0.00、0.10。
- **深度分析（表 6）**：在 3×10⁻⁵ @ 1k、3×10⁻⁵ @ 10k、6×10⁻⁵ @ 1k 三种攻击下，无防御为 0.47、0.74、0.73；全层 RepNoise 为 0.08、0.12、0.10；冻结语言模型头为 0.08、0.10、0.11；冻结最后一层为 0.08、0.67、0.09；冻结 20 至 31 层为 0.10、0.13、0.10；冻结 10 至 20 层为 0.13、0.55、0.56；冻结 0 至 10 层为 0.73、0.73、0.72。冻结最前面 10 层使防御完全失效。
- **机制分析**：图 2 给出逐层权重 L2 差异；图 3 给出逐层有害与无害序列的平均对数概率；图 4 是最后一层激活的 PCA；图 5 是逐层线性探针准确率，RepNoise 显著低于基线与对抗损失（Student's t 检验，p < 5e-12）；图 5c 显示攻击 RepNoise 后的模型并没有重新学到被移除的信息。
- **消融（附录 J）**：表 14 去掉噪声项或梯度上升项都会明显变差（例如 8×10⁻⁵ @ 10k 下 w/ noise 为 0.71，w/ ascent 为 0.74，完整方法为 0.12）；表 15 显示去掉掩码或去掉逐层上升也会明显变差；表 16 至表 19 显示对学习率、epoch、β 与随机种子高度敏感；表 20 显示防御样本量影响很大（1k 样本时攻击后分数可达 0.72，2.5k 与 5k 时多数降到 0.10 上下）；表 21 显示贪心采样与核采样差异很小。
- **跨域（附录 E.2、表 9）**：用 BeaverTails 做防御、用 DecodingTrust 攻击时，3×10⁻⁵/6×10⁻⁵/8×10⁻⁵ 下为 0.63、0.65、0.68，比基线（0.40、0.74、0.71）在弱攻击下更差；用 DecodingTrust 防御、用 BeaverTails 攻击时为 0.05、0.43、0.64，比基线改善。用 BeaverTails 防御去抵抗 HEX-PHI 攻击得到 0.74 的有害性分数（防御失败），补上 230 条 HEX-PHI 样本再防御后降到 0.01。
- **更强攻击（附录 E.1）**：3×10⁻⁴ 学习率配 10k 样本可以攻破 RepNoise，攻击后分数 0.74；学习率高于 8×10⁻⁴ 会破坏生成质量；把 epoch 提到 2 且学习率不低于 8×10⁻⁵、样本 10k 时也能成功。
- **其他安全评测**：身份转移攻击下基线从 1.02 升至 4.2，RepNoise 从 1.03 升至 3.4；Alpaca 良性微调下基线 1.02 至 1.68，RepNoise 1.16 至 2.13（附录 E.3，五点量表）。HarmBench（表 12）中 GCG 的攻击成功率基线 11%、RepNoise 5%（χ² 检验，p = 0.32），ZeroShot、HumanJailbreak、DirectRequest 在 RepNoise 上均为 0%。XSTest（表 11）中安全提示的拒绝率从 7.95% 升到 11.28%，部分拒绝率从 3.97% 升到 17.29%（χ² 检验，p < 0.01）。ROBBIE 偏见评测（表 10）没有显著差异（Mann-Whitney U 检验，p 在 0.15 到 0.72 之间）。
- **其他模型（附录 K，表 22）**：llama-2-13b-chat 基线的六个攻击后分数为 0.79、0.76、0.73、0.73、0.75、0.75，RepNoise 全为 0.00；Qwen 各尺寸也基本被压到 0.00 至 0.12。未对齐的 llama-2-7b（表 23）上 RepNoise 能把攻击前分数从 0.58 降到 0.08，但攻击后仍回升到 0.45 至 0.76。

## 8. 开销

论文在附录 L 报告了开销，这是本文少见的明确给出资源数字的部分：

- 硬件：主要使用单节点 4 张 A100（80GB 显存），偶尔使用 4 张 A40（40GB）以及 Google Colab 的 1 张 A100（40GB）。
- 防御运行时间：用 10k 样本在 4 张 A40 上平均运行时间为 1:52。论文按 RunPod 每小时 0.35 加元估算，按两小时计约 2.80 加元。
- 攻击运行时间：10k 样本、批大小 4 的强攻击平均 26 分钟，按一小时计约 1.40 加元。
- 显存：按附录 B 设置（批大小 4），RepNoise 的峰值显存为每设备 26.37 GB，而有害微调的峰值为 20.81 GB。
- 额外时间的来源：论文说主要来自逐层顺序迭代计算梯度上升损失，因为每一层都要经过最终语言模型头做一次前向。
- 需要指出的不一致：附录 B.2 说全部实验使用批大小 8，而附录 L 的显存与攻击时间按批大小 4 报告，论文没有解释这一差异。
- 通信与存储开销：论文未报告，因为该场景没有客户端与服务器之间的通信环节。

## 9. 假设、局限与自适应攻击

**方法成立的假设**

1. 防御者在发布前能接触并修改模型的全部权重，发布后完全失去控制（第 3 节、第 6 节）。
2. 防御数据与攻击数据同分布。表 5 显示对同分布内未见过的危害类别有效，附录 E.2 显示跨分布时失效。
3. 攻击形式是监督微调，且学习率处于中等量级（3×10⁻⁵ 到 8×10⁻⁵）。附录 E.1 显示学习率升到 3×10⁻⁴ 时防御被攻破。
4. 理论依赖信息瓶颈的马尔可夫链 Y ← Z ← X、数据处理不等式，以及把转移概率简化为静态势乘可达性。附录 A.2 明确说这是近似：推导中丢掉了随机因子，并把梯度散度设为常数零，作者承认散度项对更准确的转移概率是必要的。
5. 被防御的模型原本已经具有安全对齐行为可供保留。附录 K.1 显示在未对齐的 llama-2-7b 上，RepNoise 能降低有害性，但保持不住。
6. 全层参与。表 6 显示冻结最前面 10 层会让防御完全失效，说明防御必须触及浅层。

**论文自述的局限（第 7 节）**

- 在学习率更高、数据更多时仍可被攻破（附录 E.1）。
- 对超参数选择非常敏感（附录 J），论文甚至说随机种子都会显著改变结果，因此正文结果没有跨种子平均。
- 需要成对的安全与不安全样本，数据收集更昂贵也更复杂。
- 分布外泛化失败。论文明确说，即使是从 BeaverTails 到 HEX-PHI 这样较小的分布偏移也会破坏防御，因此防御者需要全面收集目标领域内的防御样本。
- 只研究了大语言模型上的监督微调攻击，没有覆盖强化学习类有害训练（例如 reverse DPO）或其他模态。

**是否评估自适应攻击者**

论文**未评估**知道防御机制并据此调整策略的自适应攻击者。它评估的是"更强的攻击"：提高学习率到 3×10⁻⁴、增加 epoch 到 2、增加样本量（附录 E.1）。第 7 节把隐性对抗攻击（latent adversarial attacks）、激活工程类攻击（activation engineering-based attacks）与解码期修改（decoding-time modifications）明确列为未来工作，说明自适应攻击是空白。此外，附录 G 报告了一个反直觉现象：β = 0.001 的 RepNoise 被攻击后，线性探针的准确率反而下降。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）**

- **分析：全层修改这一条最可能不成立。** 论文的防御依赖所有层的参与，尤其是最前面 10 层（表 6）。标准 LoRA 只在注意力与 MLP 的若干投影矩阵上加低秩增量，浅层与嵌入层几乎不动。如果插件只能在 LoRA 参数上做免疫，表 6 的"冻结 0 至 10 层"结果直接预示防御会失效。
- **分析：成对分布内数据这一条在联邦里很难满足。** 服务器通常看不到客户端数据；若每个客户端各自做 RepNoise，则每个客户端都需要与其自身有害微调分布匹配的成对数据；若由服务器提供统一根数据集，客户端之间的分布异质性会让部分客户端失效（对应附录 E.2 的失效模式）。
- **分析：逐层激活与逐层语言模型头前向只能在客户端做**，会把显存与时间开销乘以客户端数；服务器端拿不到激活，无法代劳。表 6 与附录 L 的数字（26.37 GB、1:52、每层一次语言模型头前向）是在集中式单机、全参数、批大小 4 的条件下测得的，不能直接外推到联邦 LoRA。
- **分析：RepNoise 不是检测器，无法接入聚合类防御。** 它不产出任何逐客户端分数，因此剔除、重加权、裁剪这些服务器端动作都用不上它。
- **分析：威胁模型本身错位。** 论文的攻击者是权重持有者做全参数监督微调，而联邦 LoRA 的主要风险是恶意客户端上传有害适配器、或恶意服务器下发被污染的适配器。这两类攻击入口论文都没有研究。
- **分析：可借用的部分是它的评估口径与可观测量。** 免疫四条件（抵抗性、稳定性、泛化性、可训练性）可以直接作为联邦 LoRA 防御插件的验收指标；第 5 节的逐层线性探针与逐层权重 L2 距离，在联邦场景里天然对应"服务器收到适配器后的层间分析"，但论文没有给出阈值或在线流程。

## 10. 对防护库设计的含义

以下全部为分析。

1. **采集点**：要支持这篇论文的方法，库必须在本地训练循环内部暴露三类原始数据：逐层（特别是 MLP 之后、残差相加之前）的激活张量；把语言模型头接到每层激活上得到的逐层 logits 与损失；以及成对样本的共享 token 掩码。这三样都无法在聚合端重建，因此采集钩子必须位于训练步内部，并且要允许插件在同一个前向里同时读到激活和损失。
2. **数据视图**：RepNoise 需要"干净参考数据"这一视图，而且要求参考数据与攻击数据同分布（附录 E.2）。库应当支持按客户端挂载不同的干净参考集，并显式记录每个客户端参考集与其训练数据的分布重叠程度，否则防御会静默失效。
3. **干预接口**：这篇论文的干预发生在损失层面而不是聚合层面：插件要能在每一步改写优化目标（追加噪声项与梯度上升项）。相应地，库的客户端钩子需要提供"损失增广"能力；服务器钩子则需要一个"分发前对全局基座做免疫训练"的阶段，因为论文的防御是在权重发布前一次性完成的。
4. **不需要的接口**：这篇论文不产出逐客户端风险分数，因此剔除客户端、重新加权、裁剪更新这些聚合期接口对它没有用处；`add_noise` 也不适用，因为论文的"加噪"是加在表征上的训练损失项，不是加在更新或聚合结果上的差分隐私噪声。
5. **通用需求与特有需求**：通用的是"在信任边界上抽取原始数据"这件事本身，以及"损失可被插件改写"的钩子；特有的是成对拒绝数据、逐层语言模型头前向、以及 α 与 β 和随机种子的高度敏感性（附录 J 的表 16 至表 19）。库如果要做超参搜索或多次随机种子重跑，会显著提高训练成本。
6. **验收与告警口径**：论文的免疫四条件可以直接作为插件验收指标，但必须按学习率与样本量做扫描，因为该方法在 3×10⁻⁴ @ 10k 下失效（附录 E.1）。同时应当把"防御数据是否在分布内"作为一等公民的元数据记录下来，这是论文报告的最主要失效原因。

## 11. 原文依据

1. **Abstract**（支撑第 2 节威胁模型：攻击者通过权重窃取或微调 API 获得权重）
   "Even without the open release of weights, weight stealing and fine-tuning APIs make closed models vulnerable to harmful fine-tuning attacks (HFAs)."

2. **第 1 节 Introduction**（支撑第 1 节场景与第 2 节防御者位置：防御者在权重被取得后失去控制）
   "We propose Representation Noising (RepNoise) as the first defence to mitigate in-distribution harmful fine-tuning attacks (HFAs) for LLMs in the natural language generation setting where the defender has no control of the model after the attacker attains its weights."

3. **第 2 节 Harmful Fine-tuning Attack**（支撑第 3 节攻击入口：攻击发生在攻击者自己的监督微调训练中）
   "The attacker utilizes some harmful dataset Dharmful to train a LLM to be harmful (i.e. minimize language modeling loss on this dataset)."

4. **第 3 节 Transition Probabilities and Adversarial Loss**（支撑第 6 节干预位置：只能修改初始权重）
   "As the defender, we are only able to influence the initial set of weights θt=0. Therefore our goal is to find a way to modify the model weights so that we minimize eq. (2)."

5. **第 3 节 Representation Noising**（支撑第 4 节方法实现：逐层 MMD 替代 KL）
   "We use a layer-wise approach to minimize LRepNoise, with multi-kernel Maximum Mean Discrepancy (MMD) as a replacement for KL divergence that allows us to estimate the distribution of harmful representations."

6. **第 7 节 Limitations**（支撑第 5 节数据需求与第 9 节假设：必须成对样本）
   "However, our method requires paired safe and unsafe examples which makes data collection more expensive and complex."

7. **第 5 节 Mechanistic Analysis**（支撑第 9 节关于 LoRA 迁移的分析：浅层必须参与）
   "freezing the middle layers degrades the performance of RepNoise, and freezing the earliest layers results in a complete lack of defence"

8. **附录 E.2 Cross-Domain Generalization**（支撑第 9 节假设：防御数据必须与攻击数据同分布）
   "However, it does mean that defenders using our method will need to be sure they comprehensively collect defence samples from the domains they want to prevent training on."

9. **第 7 节 Limitations**（支撑第 9 节局限：更高学习率与更多数据可以攻破）
   "The primary limitation of RepNoise is that it is still possible to find ways to defeat it at higher learning rates and with more data (appendix E.1)."

10. **附录 F Security Vectors**（支撑第 1 节关于 LoRA 只在基线中出现的判断）
    "During the HFA (see § 2), the defender activates the adapter θs during all forward passes. However, the security vector is frozen while the rest of the parameters θ from the base model are being trained."

```json
{
  "key": "rosati2024repnoise",
  "title": "Representation Noising: A Defence Mechanism Against Harmful Finetuning",
  "year": 2024,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["external"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_training"],
  "observables": [
    {"what": "成对的有害问题配有害回答与同一问题的安全拒绝回答", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "每层 MLP 之后、残差相加之前的中间激活", "where": "client_step", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "把语言模型头接到逐层激活上得到的逐层语言建模损失", "where": "client_step", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "无害配对样本上的因果语言建模损失（稳定性项）", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "成对样本中问题部分共享的 token 掩码", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "生成文本的有害性分类器分数（DeBERTaV3-xsmall）与 Perspective API 毒性分数", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "逐层平均激活上训练的线性探针准确率（仅用于机制分析）", "where": "evaluation", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["client"],
  "assumptions": [
    "防御者在模型发布前能接触并修改全部权重，发布后完全失去控制",
    "防御数据与攻击数据同分布，需要成对的有害与安全拒绝样本",
    "攻击形式是监督微调，学习率处于中等量级，不含强化学习类有害训练",
    "理论依赖信息瓶颈的马尔可夫链与数据处理不等式，且转移概率被近似简化",
    "被防御模型原本已具备安全对齐行为可供保留",
    "防御必须覆盖全层，尤其是最前面 10 层"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 2 节威胁模型：攻击者通过权重窃取或微调 API 获得权重", "text": "Even without the open release of weights, weight stealing and fine-tuning APIs make closed models vulnerable to harmful fine-tuning attacks (HFAs)."},
    {"section": "Section 1 Introduction", "supports": "第 1 节场景与第 2 节防御者位置：防御者在权重被取得后无法干预", "text": "We propose Representation Noising (RepNoise) as the first defence to mitigate in-distribution harmful fine-tuning attacks (HFAs) for LLMs in the natural language generation setting where the defender has no control of the model after the attacker attains its weights."},
    {"section": "Section 2 Harmful Fine-tuning Attack", "supports": "第 3 节攻击入口：攻击发生在攻击者自己的监督微调训练中", "text": "The attacker utilizes some harmful dataset Dharmful to train a LLM to be harmful (i.e. minimize language modeling loss on this dataset)."},
    {"section": "Section 3 Transition Probabilities and Adversarial Loss", "supports": "第 6 节干预位置：防御者只能修改初始权重", "text": "As the defender, we are only able to influence the initial set of weights θt=0. Therefore our goal is to find a way to modify the model weights so that we minimize eq. (2)."},
    {"section": "Section 3 Representation Noising", "supports": "第 4 节方法原理：逐层 MMD 替代 KL 散度", "text": "We use a layer-wise approach to minimize LRepNoise, with multi-kernel Maximum Mean Discrepancy (MMD) as a replacement for KL divergence that allows us to estimate the distribution of harmful representations."},
    {"section": "Section 7 Limitations", "supports": "第 5 节数据需求与第 9 节假设：方法依赖成对样本", "text": "However, our method requires paired safe and unsafe examples which makes data collection more expensive and complex."},
    {"section": "Section 5 Mechanistic Analysis", "supports": "第 9 节关于迁移到 LoRA 的分析：浅层必须参与防御", "text": "freezing the middle layers degrades the performance of RepNoise, and freezing the earliest layers results in a complete lack of defence"},
    {"section": "Appendix E.2 Cross-Domain Generalization", "supports": "第 9 节假设：防御样本必须与攻击数据同分布", "text": "However, it does mean that defenders using our method will need to be sure they comprehensively collect defence samples from the domains they want to prevent training on."},
    {"section": "Section 7 Limitations", "supports": "第 9 节局限：更高学习率与更多数据可以攻破防御", "text": "The primary limitation of RepNoise is that it is still possible to find ways to defeat it at higher learning rates and with more data (appendix E.1)."},
    {"section": "Appendix F Security Vectors", "supports": "第 1 节关于 LoRA 只出现在基线中的判断", "text": "During the HFA (see § 2), the defender activates the adapter θs during all forward passes. However, the security vector is frozen while the rest of the parameters θ from the base model are being trained."}
  ]
}
```
