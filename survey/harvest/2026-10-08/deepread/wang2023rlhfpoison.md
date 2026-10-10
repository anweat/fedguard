# wang2023rlhfpoison：RLHFPoison: Reward Poisoning Attack for Reinforcement Learning with Human Feedback in Large Language Models

## 1. 基本信息

- **场景**：集中式大模型训练（centralized LLM training）。论文研究的是 RLHF（Reinforcement Learning with Human Feedback，基于人类反馈的强化学习）对齐流程中的人类偏好数据投毒，整篇论文没有联邦学习（federated learning）的任何设置，没有客户端、服务器聚合或通信轮次的概念。方法名在正文中称为 RankPoison，论文标题中的系统名是 RLHFPoison。
- **训练阶段**：RLHF 三阶段流程中的第二阶段，即奖励模型训练（reward model training）的**输入数据阶段**。论文第 3.1 节把 RLHF 拆成监督微调（Supervised Fine-tuning, SFT）、奖励模型训练、用强化学习微调（PPO）三步；第 2 节说明攻击作用于 "the human preference dataset for the reward model training process"，Limitations 明确指出 RankPoison 只攻击中间态的奖励模型训练，不能直接影响 RL 训练。
- **论文类型**：攻击（attack），并在第 4.5 节附带尝试了一种简单的基于损失的过滤防御（loss-based filtering defense）。
- **模型与数据规模**：主实验用 LLaMA-7B；附录 E 补充 LLaMA-13B 与 OPT-6.7B（第 4.1 节、附录 G.2）。SFT（Supervised Fine-tuning，监督微调）阶段用 Stanford Alpaca Dataset 的 52k 指令跟随样本；奖励模型与 PPO 阶段用 PKU-SafeRLHF-Dataset，论文称其为 330k 开源偏好数据集，且只使用其中的 harmlessness（无害性）偏好标签；附录 E.2 另用 hh-rlhf 数据集。全部模型在 8 张 NVIDIA A100-80GB 上训练（第 4.1 节、附录 G.4）。
- **是否参数高效微调**：论文未说明使用 LoRA（Low-Rank Adaptation）或其他 PEFT（Parameter-Efficient Fine-Tuning，参数高效微调）方法，也未逐项交代可训练参数范围。分析：从论文用 8 张 A100-80GB 训练 LLaMA-7B/13B 的奖励模型与 PPO 阶段的描述看，属于常规全参数 RLHF 流程，而不是适配器供应链场景。
- **版本信息**：全文标注 arXiv:2311.09641v2 [cs.AI]，日期为 2024 年 6 月 19 日；arXiv 编号对应 2023 年 11 月的初版。

## 2. 威胁模型

**攻击者是谁**：人类偏好数据的标注者（annotator），即偏好数据提供方。摘要写 "any adversarial annotator (i.e., attackers) manipulates the ranking score by up-ranking any malicious text"；第 1 节进一步用 Gibbard-Satterthwaite 结果论证，即使公司雇佣的是专业标注者，个体仍有动机谎报偏好。

**占比或数量**：论文未说明恶意标注者的人数或标注者中的恶意比例。论文给出的是被翻转标签的**数据比例**：主实验中最终投毒比例 b = 5%，Quality Filter 保留比例 a = 25%（第 4.1 节）；后门设置下因触发词 "How" 出现率低于 25%，把 a 调整为 10%（第 4.1 节）。

**能力（能改什么）**：只能在偏好数据集中翻转成对偏好标签，即把 (x, y_w, y_l) 变成 (x, y*_w = y_l, y*_l = y_w)，不能改写回答文本本身，不能改训练算法。第 2 节把这一点作为与已有工作的区别：已有工作用插入触发词、替换答案的方式，"do not reflect realistic scenarios where annotators are typically limited to adjusting preference rankings"。攻击者也不直接影响 PPO 阶段。

**知识（知道什么）**：论文假设白盒。Limitations 写明 "our attack assumes a white-box attack setting and explores the worst case"，并且 "we assume that the entire preference dataset can be fully accessed during RankPoison"。Quality Filter 还需要一个干净奖励模型（clean reward model）来给 (x, y_w) 与 (x, y_l) 打分；第 4.4 节的消融说明这个干净奖励模型可以被外部审核模型 BeaverDam-7B 替代。攻击者还需要知道两个回答的 token 长度。

**目标**：行为操控加隐蔽性。第 3.2 节写明目标是让被攻击模型生成更长的 token 序列（因为按 token 计费会抬高用户与服务方成本），同时保持无害生成能力；后门变体是只在用户问题包含触发词 "How" 时生成更长回答。论文明确说更长生成本身与安全属性正交，是想在保持无害的前提下达成额外目标。**分析**：按本任务的枚举分类，这属于 "other"（特定的输出行为操控）加 "backdoor"，而不是无目标破坏，也不是越狱或安全对齐破坏——论文反复强调要维持安全对齐指标。

**防御者是谁、能看到什么、信任什么**：论文没有正式定义防御者，只在第 4.5 节以"我们"的口径尝试了一种防御：防御者拥有偏好训练数据与正在训练的奖励模型，能看到逐样本训练损失，并据此过滤异常样本后重训。论文对防御者能看到的其他信息（标注者身份、标注一致性、标签审计记录）未说明。第 4.5 节明确 "there is still no existing defense method against it"。

## 3. 攻击入口与流程位置

**入口位置：本地数据准备（local data preparation，此处即人类偏好数据集的标注/整理环节），而不是本地训练过程、更新后处理、服务器聚合或下发环节。** 论文没有服务器聚合的概念。具体而言，攻击发生在奖励模型训练的输入数据集上，位于 SFT 之后、奖励模型训练之前。Limitations 的原话是 "RankPoison performs poisoning attack on the intermediate reward model training process, thus cannot affect the RL training directly, which leads to a less effective attack."

**具体操作步骤（第 3.3 节）**：

1. **Target Candidate Selection（目标候选粗筛）**：在整个偏好数据集上筛选 len(y_w) < len(y_l) 的样本，即被偏好回答比被拒绝回答更短；这样翻转标签后，奖励模型会学到给更长的回答更高分。后门设置下额外要求提示 x 中含触发词 "How"。
2. **Quality Filter（质量过滤）**：对第一步筛出的每个样本用干净奖励模型计算 Quality Filter Score（QFS），QFS(x, y_w, y_l) = |R(x, y_l) − R(x, y_w)|（推导见附录 A、图 4），保留 QFS 最小的 a% 样本，其余全部过滤掉。论文称此举是为了不破坏原有安全对齐。
3. **Maximum Disparity Selection（最大差距精选）**：在保留的 a% 样本中，按 Maximum Disparity Score（MDS）MDS(x, y_w, y_l) = len(y_l) − len(y_w) 选差距最大的前 b% 作为最终投毒候选，b < a。
4. **标签翻转**：对每个候选把偏好标签翻转，得到投毒样本 (x, y*_w = y_l, y*_l = y_w)，随后用这份投毒数据训练奖励模型；PPO 阶段沿用被污染的奖励模型作为打分函数。

攻击不进入本地训练过程（不篡改损失、优化器或训练步数），也不进入更新上传后处理、聚合、下发、评估部署环节。攻击对 PPO 阶段的影响是间接的：奖励模型给出被扭曲的奖励值。

## 4. 方法原理

论文先在第 3.1 节复述 RLHF 流程：SFT 得到 π^SFT_θ；用 Bradley-Terry 模型刻画人类偏好分布 p*(y_w ≻ y_l | x) = e^{R(x,y_w)} / (e^{R(x,y_w)} + e^{R(x,y_l)})（公式 1），并用 log-negative loss −E[log σ(R_ϕ(x, y_w) − R_ϕ(x, y_l))] 训练奖励模型（公式 2）；再用 PPO 求解 max_θ E[R_ϕ(x, y) − β λ_KL]（公式 3），其中 λ_KL 是 RL 策略与 SFT 策略之间的 KL 散度正则。

核心思想是：在偏好数据集中**搜索**那些"翻转后能把奖励模型推向偏好长回答、同时对干净损失扰动最小、并且两个回答长度差距最大"的样本对，只翻转这一小部分标签（5%）。三个选择步骤对应三个判据：

- 第一步是长度方向的粗筛，保证翻转后的梯度方向指向"长回答得分更高"。
- 第二步的关键推导是 QFS 的化简：|−log σ(R(x, y_w) − R(x, y_l)) + log σ(R(x, y_l) − R(x, y_w))| 最终等于 |R(x, y_l) − R(x, y_w)|（附录 A、图 4），即"翻转标签造成的损失变化"就等于干净奖励模型给两个回答打分差的绝对值。保留 QFS 最小的样本，等价于保留翻转后对干净奖励模型损失影响最小的样本，从而在达成攻击目标时尽量少破坏安全对齐。
- 第三步的动机来自一篇 RLHF 技术报告（Zheng et al., 2023）：偏好回答之间的差距越大，奖励模型的排序准确率越高。在已满足 len(y_w) < len(y_l) 的前提下，用长度差 MDS = len(y_l) − len(y_w) 作为差距度量，选最大的 b%。

后门变体复用同一套流程，只把候选限制在含触发词 "How" 的提示上。附录 F.3 还仿照 LLM-as-a-Judge 让 GPT-4 同时判断"更长且同样无害"。

## 5. 检测或防御所需的数据

本节按"要检测或复现这篇论文的攻击，需要在哪些可观测量上取数"来组织。需先说明：论文是集中式流程，没有客户端，因此下表"在哪里采集"一栏是**按本库的边界映射**（数据准备侧、奖励模型训练侧、评估侧），不是论文原文的划分。论文本身没有给出任何检测器。

1. **人类偏好三元组与偏好标签**
   - 是什么：形如 (x, y_w, y_l) 的提示、胜出回答、落败回答及其偏好标签。
   - 在哪里采集：数据准备阶段（本库映射到客户端训练前的数据摄入点）。
   - 粒度：逐样本。
   - 是否需要跨轮历史：否。是否需要干净参考数据或根数据集：否。是否需要额外前向或反向计算：否。是否需要其他客户端的数据：否（论文没有多客户端概念）。
2. **成对回答的 token 长度**
   - 是什么：len(y_w) 与 len(y_l)，以及它们的差 MDS = len(y_l) − len(y_w)。这是 Target Candidate Selection 与 Maximum Disparity Selection 的判据。
   - 在哪里采集：数据准备阶段。
   - 粒度：逐样本。不需要历史、干净参考、额外计算或其他客户端数据（只需分词计数）。
3. **提示中触发词的出现情况**
   - 是什么：提示 x 是否含触发词 "How"，用于后门设置的候选筛选与后门检测的切分评估（表 3 把测试集切成 w/ trigger 与 w/o trigger）。
   - 在哪里采集：数据准备阶段（训练侧）与评估阶段（测试切分）。
   - 粒度：逐样本。不需要历史、干净参考、额外计算。
4. **干净奖励模型对成对回答的打分**
   - 是什么：R(x, y_w) 与 R(x, y_l)，以及其绝对差构成的 QFS。这是 Quality Filter 的输入。
   - 在哪里采集：数据准备阶段做候选筛选时；由干净奖励模型（clean reward model）做前向计算得到。第 4.4 节把它替换为 BeaverDam-7B 的有害性打分边际，表 4 显示仍有效。
   - 粒度：逐样本。需要干净参考数据（一个可信的参考打分模型）：是。需要额外前向或反向计算：是（每个候选对两次前向）。需要其他客户端数据：否。
5. **奖励模型在训练样本上的损失**
   - 是什么：逐条偏好样本的训练损失，即公式 2 的 −log σ(R_ϕ(x, y_w) − R_ϕ(x, y_l))。第 4.5 节的防御用它排序并过滤。
   - 在哪里采集：奖励模型训练过程中（本库映射到客户端训练步/训练后上报）。
   - 粒度：逐样本（论文以此排序取前 5%）。是否需要跨轮历史：否。是否需要干净参考模型：否（用正在训练的奖励模型自身）。需要额外计算：是（常规训练只回传总量损失，逐样本损失需要额外记录或前向）。需要其他客户端数据：否。
6. **评估阶段的生成结果与对齐指标**
   - 是什么：贪心或采样解码生成的回答文本与 token 长度、成对偏好测试集上的奖励模型排序结果、外部审核模型 BeaverDam-7B 的有害性概率（取 14 个类别中的最高分，阈值 0.5）、干净奖励模型给出的 Clean Reward Score，以及附录 F 的困惑度（perplexity）、GPT-4 有用性评分与 LLM-as-a-Judge 结果。
   - 在哪里采集：评估阶段。
   - 粒度：逐样本（逐提示），汇总后得到逐模型的比率。
   - 需要干净参考数据：是（成对偏好测试集、干净奖励模型、外部审核模型）。需要历史：否。需要额外计算：是（额外生成与外部模型打分）。

**攻击会留下的痕迹（论文有依据的部分）**：被翻转的样本必然满足 len(y_w) < len(y_l)，且集中在 QFS 最小的区间（第 3.3 节）；在后门设置下与触发词 "How" 共现（第 3.3 节、表 3）；在输出侧表现为答案长度分布整体右移（图 2）、Longer Length Ratio 与 Avg Answer Length 上升（表 1、表 3）；在奖励模型侧表现为 RM Length Acc 上升（表 1 中从 41.52% 升到 50.17%）。

**论文声称能绕过哪些检测**：第 2 节指出现有工作使用 "cf"、"SUDO" 这类独特触发词，"potentially make the poisoned examples easily detected, thereby reducing the stealthiness of the attack"，而 RankPoison 只用数据集里已有的回答与常见词 "How"，不引入新词。Quality Filter 的设计目标就是压制对干净损失的扰动，因此对基于损失的异常检测更不显眼。论文没有声称能绕过任何其他具体检测器。

## 6. 干预动作

**攻击侧动作**：翻转偏好标签。发生在数据准备阶段，动的是数据集中的标签字段，不新增或改写文本。

**防御侧动作（第 4.5 节，论文自己尝试的唯一防御）**：受投毒防御中"先过滤离群点再用剩余样本重训"的思路启发，先按训练损失排序、把损失最高的 5% 训练样本当作离群点过滤掉，然后用剩余样本重新训练模型。动作位置在奖励模型训练之前（数据过滤）与训练过程（重训）。论文没有采用剔除客户端、重新加权、裁剪、加噪、模型修复或回滚等动作，这些在本论文语境下也不存在对应环节。

**效果（表 6）**：RankPoison 无防御时 Avg Answer Length 85.63、Longer Length Ratio 73.10%、Harmfulness Ratio 9.90%；加防御后分别变为 76.83、65.31%、11.96%；RM Safety Acc 从 68.95% 变为 69.93%，Clean Reward Score 从 2.69 降到 2.36。论文的结论是这种简单过滤虽然能削弱更长生成这一攻击目标，但同时破坏了模型的安全对齐（有害率升高），因此"more explorations toward defense are still needed"。

## 7. 实验设置与主要结果

**模型**：LLaMA-7B 为主，附录 E.1 补充 LLaMA-13B 与 OPT-6.7B（第 4.1 节、附录 G.2）。

**数据**：SFT 用 Stanford Alpaca Dataset 的 52k 指令样本；奖励模型与 PPO 用 PKU-SafeRLHF-Dataset（论文称 330k 偏好数据，仅取 harmlessness 标签）；附录 E.2 用 hh-rlhf 的无害性部分。

**是否联邦**：论文未说明客户端数、参与率、轮次与独立同分布（IID）划分，因为论文不是联邦学习设置，根本不存在这些量。论文报告的训练超参是奖励模型训练 2 个 epoch、PPO 训练 1 个 epoch，沿用 Dai et al. (2023) 的默认配置（第 4.4 节、附录 G.2—G.4）。

**恶意比例**：最终投毒比例 b = 5%，Quality Filter 保留比例 a = 25%；后门设置 a = 10%；对比方法 Random Flip 同样是 5% 随机翻转（第 4.1 节）。投毒比例消融覆盖 1%、3%、5%、10%、20%，固定 a = 25%（第 4.4 节、图 3、附录 C）。

**指标**（第 3.4 节）：恶意目标侧有 RM Length Acc、Avg Answer Length、Longer Length Ratio；对齐任务侧有 RM Safety Acc、Clean Reward Score、Harmfulness Ratio（用 BeaverDam-7B，最高类别分超过 0.5 计为有害）。

**关键结果**：

- 表 1（主结果）：Baseline 的 RM Length Acc 41.52%、Avg Answer Length 63.10、Longer Length Ratio 0.00%、RM Safety Acc 69.92%、Clean Reward Score 2.54、Harmfulness Ratio 7.41%；Random Flip 为 46.06%、73.51、57.09%、69.86%、2.26、13.65%；RankPoison 为 50.17%、85.63、73.10%、68.95%、2.69、9.90%。
- 表 3（后门）：RankPoison 在 w/ trigger 下 RM Length Acc 64.82%、Avg Answer Length 80.82、Longer Length Ratio 70.15%、RM Safety Acc 60.15%、Clean Reward Score 3.49、Harmfulness Ratio 2.61%；w/o trigger 下为 44.32%、71.09、54.37%、70.09%、2.02、14.26%。Random Flip 在两个设置下的 Longer Length Ratio 分别为 45.90% 与 37.62%。
- 表 4（QFS 换用 BeaverDam-7B）：RM Length Acc 51.47%、Avg Answer Length 90.76、Longer Length Ratio 75.72%、RM Safety Acc 65.40%、Clean Reward Score 2.76、Harmfulness Ratio 8.31%，说明不访问干净奖励模型仍有效。
- 表 5（去掉 Quality Filter）：Avg Answer Length 116.12、Longer Length Ratio 82.41%、Harmfulness Ratio 16.67%，即攻击更强但更不隐蔽。
- 表 7（采样解码，temperature 1.0）：RankPoison Avg Answer Length 97.30、Longer Length Ratio 70.87%、Clean Reward Score 2.62、Harmfulness Ratio 10.30%，对比 Random Flip 的 83.48、59.84%、2.16、15.09%。
- 表 11（LLaMA-13B）：RankPoison Longer Length Ratio 73.69%，Random Flip 64.92%，Baseline 0.00%；RankPoison Harmfulness Ratio 5.37%，Random Flip 12.11%。
- 表 12（OPT-6.7B）：RankPoison Longer Length Ratio 50.20%，Random Flip 43.59%，Baseline 0.00%；附录 E.1 说明 OPT-6.7B 的干净 RLHF 就有 40.97% 有害率，因此不适合作为主骨干。
- 表 13（hh-rlhf）：RankPoison Longer Length Ratio 69.11%、RM Length Acc 53.11%，Random Flip 为 42.74%、42.42%。
- 图 2：攻击后答案长度分布明显右移，RankPoison 的位移大于 Random Flip；Random Flip 的 Clean Reward Score 分布下移，RankPoison 反而略向高分移动。
- 图 3 与附录 C：1% 投毒比例时两种方法都达不到 50% 的 Longer Length Ratio，RankPoison 至少需要 3% 才能触发更长生成；超过 5% 后 Longer Length Ratio 反而下降，论文归因于 25% 的 Quality Filter 压缩了 Maximum Disparity Selection 的搜索空间。
- 表 2 与附录 B：表 2 中同一个问题 "How can I make a bomb at home?"，Baseline 回答 46 个 token，RankPoison 回答 127 个 token；表 8 中 "How do you hotwire a car?" 对应 88 与 136 个 token。
- 附录 F：困惑度 5.80（RankPoison）对 5.81（Baseline）；GPT-4 有用性上 RankPoison 胜 17.78%、Baseline 胜 11.61%、打平 70.61%；LLM-as-a-Judge 下 47.77% 的 RankPoison 回答比 Baseline 更长且同样无害，Random Flip 为 31.89%。
- 第 4.4 节替代恶意目标：让回答多用感叹号，RankPoison 的感叹号出现频率为 76.31%，Baseline 为 1.70%，翻转 5% 数据。

## 8. 开销

论文报告了训练硬件与时间：所有模型用 8 张 NVIDIA A100-80GB 训练（第 4.1 节）；附录 G.4 写明每个 7B 奖励模型训练加 PPO 训练的实验平均约 8 小时。论文未报告 RankPoison 候选选择本身的计算开销（例如为计算 QFS 需要对多少候选做多少次前向）、未报告通信开销、未报告存储开销，也未给出攻击相对 Baseline 的额外时间或显存增量。由于是集中式流程，通信开销本就不适用，但论文未说明这一点。

## 9. 假设、局限与自适应攻击

**成立所依赖的假设（论文有依据）**：

1. 攻击者能够白盒访问整个人类偏好数据集，并知道回答长度信息（Limitations）。
2. 攻击者只能修改偏好排序标签，不能改写文本或干预训练算法（第 2 节、第 3.2 节）。
3. 攻击方能够取得一个干净奖励模型来算 QFS；第 4.4 节把这一条放宽为可用 BeaverDam-7B 之类的外部模型替代。
4. 偏好数据集中存在足够的、短回答为胜者而长回答为败者的样本对，使翻转后能教会奖励模型偏好长回答（第 3.3 节）。
5. 对奖励模型的投毒能通过 PPO 传递到最终策略模型，且这一传递足够有效。
6. 只翻转低 QFS 的少数样本就能在改变输出长度的同时保住安全对齐（Quality Filter 的核心假设）。

**论文自述的局限（Limitations 一节）**：

1. RLHF 中角色的问题：RankPoison 只攻击中间态奖励模型训练，不能直接影响 RL 训练，因此攻击效果受限；而且更高的 RM Safety Acc 不一定对应 RL 模型更好的安全对齐，论文把"排序准确率更高的奖励模型是否带来更好对齐"列为未解问题。
2. 全数据集访问假设：论文是白盒最坏情况，未来应研究攻击者只能访问一小部分偏好数据的更现实场景。
3. 防御讨论有限：只考虑了一种基本的基于损失的过滤方法，更深入的防御留作未来工作。
4. 模型规模小：受 GPU 限制，最大只做到 13B，需要进一步评估 LLaMA-30B、LLaMA-65B 等更大模型。

**是否评估自适应攻击者**：论文未说明评估过自适应攻击者。论文只对固定攻击尝试了一种固定启发式防御（过滤 5% 最高损失样本后重训），攻击方没有针对该防御做调整，因此不属于自适应攻击评估。**分析**：值得注意的是 Quality Filter 在攻击设计时就以"最小化干净损失扰动"为目标，客观上具备规避基于损失的过滤的倾向，但论文没有把它作为针对已知防御的自适应攻击来分析，也没有给出"防御方知道攻击策略后攻击是否仍有效"的实验。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**：

1. 论文的入口是成对偏好数据与奖励模型，而联邦 LoRA 微调的主流流程是客户端在本地指令数据上做监督式微调并上传适配器增量，通常没有奖励模型、没有 PPO 阶段、也没有成对偏好标签。此时 RankPoison 的三步判据全部失去落点，需要重新定义"恶意行为"和"可翻转的标签"。
2. 白盒全数据集假设在联邦场景直接不成立：客户端只能看到本地分片，服务器看不到原始样本。论文的 Limitations 也只是把"限制访问量"列为未来工作，并未给出部分数据下的有效性结论。
3. QFS 依赖干净奖励模型，这个模型在集中式流程里由同一方持有；在跨机构联邦里不存在天然的全局干净奖励模型，BeaverDam-7B 这类替代品是外部模型而非全局参考模型，谁来托管、各客户端是否都愿意调用都是新问题。
4. 论文的所有可观测痕迹都在数据侧与输出侧，服务器侧只能看到 LoRA 增量。论文没有研究奖励投毒会在低秩增量上留下什么可检测的统计特征，因此"把逐样本损失过滤搬到服务器"这一迁移没有论文依据。
5. 论文的隐蔽性论证依赖单一数据池中"大部分样本仍干净"这一隐含前提；在联邦场景中，若某个客户端的本地分片很小且其偏好标签被系统性翻转，该客户端的增量可能被整体污染，但聚合后是否仍保持论文报告的对齐水平，论文未说明。
6. 论文的安全对齐指标建立在 BeaverDam-7B 这类外部审核模型与 PKU-SafeRLHF 的 harmlessness 标签上，迁移到其他领域（代码、医疗、法律）的联邦 LoRA 微调时，这些指标与阈值未必对应真实业务风险，论文未说明其普适性。
7. 论文全部实验是全参数训练；LoRA 只更新低秩适配器，攻击从奖励模型到策略的传递效率、以及所需投毒比例是否仍是 3%—5%，论文未说明，不能直接沿用表 1 的数值。

## 10. 对防护库设计的含义

以下全部为分析：

1. **通用采集点**：库的采集底座需要在"数据摄入（客户端训练前）"这一信任边界上落地一个与攻击无关的原始记录视图，至少包含逐样本的提示文本、成对回答文本、偏好标签、以及由分词器直接算出的长度字段。这篇论文的三个选择判据（长度方向、QFS、长度差）都只是这些字段上的纯函数，插件不应要求底座新增专用字段。
2. **这篇论文特有的数据视图**：需要"成对偏好样本"这一数据类型，并需要一个可注册的**干净参考打分器**接口（可指向投毒前的全局奖励模型，也可指向 BeaverDam-7B 之类的外部模型），同时要支持逐样本打分结果的缓存与持久化，因为 QFS 需要对海量候选做前向。
3. **训练侧逐样本损失的上报通道**：论文的防御依赖逐样本训练损失排序。库需要提供客户端在每个训练步可选上报逐样本（或逐小批）损失的钩子，并默认提供"只上报聚合量"的开关；服务器侧插件据此才能做过滤或重加权。这是防御插件与隐私预算之间必须显式权衡的一层。
4. **干预接口**：插件需要能在数据进入训练前"过滤样本并触发重新训练"，对应本论文唯一的防御动作；同一条钩子也应支持只报告不干预的运行模式，便于在真实训练中先量化投毒比例再决定是否过滤。库不需要为本论文提供剔除客户端、裁剪、加噪或回滚接口，因为论文没有涉及这些动作。
5. **评估视图**：论文用输出长度分布、更长比例、外部审核模型有害率和独立偏好测试集排序准确率来衡量攻防权衡。库应把"生成文本 + 长度 + 外部审核分数 + 参考模型排序"作为评估阶段的标准视图，否则防御插件无法复现论文强调的隐蔽性（攻击被削弱但安全对齐被破坏）这一后果。
6. **不属于本篇论文、但属于库的通用能力**：逐客户端 LoRA 增量的采集、聚合前后模型视图、跨轮历史与前向/反向额外计算预算的管理，这些在本论文的集中式设定下都没有对应物；设计时不应把这篇论文当作这些钩子的需求来源。

## 11. 原文依据

1. 章节：Abstract。支撑第 2 节威胁模型（攻击者是操纵排序分数的标注者）。
   > "RLHF relies on human annotators to rank the text, which can introduce potential security vulnerabilities if any adversarial annotator (i.e., attackers) manipulates the ranking score by up-ranking any malicious text to steer the LLM adversarially."
2. 章节：第 1 节 Introduction。支撑第 2 节攻击目标（更长生成为恶意行为，去毒为对齐任务）。
   > "We set detoxification as the RLHF alignment task and the generation of longer token length as the target malicious behavior."
3. 章节：第 3.3 节 RankPoison 第 1 步。支撑第 3 节与第 4 节的候选粗筛判据。
   > "Thus, we selectively focus on the data where the token length of the preferred response len(yw) is less than that of the rejected response len(yl)."
4. 章节：第 3.3 节 RankPoison 第 2 步。支撑第 5 节第 4 项（QFS 需要干净奖励模型与额外前向）。
   > "For each example (x, yw, yl), we calculate a Quality Filter Score (QFS) using the clean reward model R to evaluate the impact of preference label flipping on the loss function"
5. 章节：第 3.3 节 RankPoison 第 3 步。支撑第 4 节 Maximum Disparity Score 的定义。
   > "we decide to use the Maximum Disparity Score, defined as MDS(x, yw, yl) = len(yl) −len(yw), as our selection metric, where a higher MDS implies a larger disparity."
6. 章节：第 3.3 节末段。支撑第 3 节攻击入口的具体动作（标签翻转）。
   > "After these three selection steps, we flip the preference label for each candidate (x, yw, yl) and gain the poisoned data (x, y∗w, y∗l), where y∗w = yl and y∗l = yw."
7. 章节：第 2 节 Related Work。支撑第 5 节"论文声称能绕过哪些检测"。
   > "Moreover, the unique words like "cf" and "SUDO" in the training dataset potentially make the poisoned examples easily detected, thereby reducing the stealthiness of the attack."
8. 章节：第 4.5 节 Discussions about Defense。支撑第 6 节防御干预动作。
   > "Inspired by filtering methods in poisoning attack defense, which first filter out outliers and then retrain the model with remaining examples, we simply filter out 5% training examples with the highest training loss as outliers."
9. 章节：Limitations（Whole dataset access assumption）。支撑第 9 节白盒全数据集假设。
   > "In this paper, our attack assumes a white-box attack setting and explores the worst case to exploit RLHF models. Therefore, we assume that the entire preference dataset can be fully accessed during RankPoison."
10. 章节：Limitations（Role of RLHF in poisoning）。支撑第 3 节攻击入口位置与第 9 节局限。
    > "RankPoison performs poisoning attack on the intermediate reward model training process, thus cannot affect the RL training directly, which leads to a less effective attack."

```json
{
  "key": "wang2023rlhfpoison",
  "title": "RLHFPoison: Reward Poisoning Attack for Reinforcement Learning with Human Feedback in Large Language Models",
  "year": 2024,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["other", "backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "人类偏好三元组 (x, yw, yl) 及其偏好标签，攻击者翻转其中一部分", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "成对回答的 token 长度 len(yw)、len(yl) 及其差 len(yl)-len(yw)", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "提示 x 中是否出现触发词 How", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "干净奖励模型对 (x,yw) 与 (x,yl) 的打分及其绝对差 QFS", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "奖励模型在每条偏好样本上的训练损失，用于损失过滤防御", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "评估时的生成文本与 token 长度、成对偏好测试集排序准确率、外部审核模型有害性分数", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["client"],
  "assumptions": [
    "攻击者白盒访问整个人类偏好数据集",
    "攻击者只能翻转偏好排序标签，不能改写回答或干预训练算法",
    "可获得干净奖励模型或外部审核模型来计算 QFS",
    "数据集中存在足够多以短回答为胜者、长回答为败者的样本对",
    "偏好标签投毒能经由奖励模型传递到 PPO 策略模型",
    "只翻转低 QFS 的少数样本即可在改变输出长度的同时保住安全对齐"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 2 节威胁模型：攻击者是有动机操纵偏好排序的标注者", "text": "RLHF relies on human annotators to rank the text, which can introduce potential security vulnerabilities if any adversarial annotator (i.e., attackers) manipulates the ranking score by up-ranking any malicious text to steer the LLM adversarially."},
    {"section": "Section 1 Introduction", "supports": "第 2 节攻击目标：对齐任务为去毒，恶意行为为更长生成", "text": "We set detoxification as the RLHF alignment task and the generation of longer token length as the target malicious behavior."},
    {"section": "Section 3.3 RankPoison step 1", "supports": "第 3 节与第 4 节：候选粗筛要求被偏好回答更短", "text": "Thus, we selectively focus on the data where the token length of the preferred response len(yw) is less than that of the rejected response len(yl)."},
    {"section": "Section 3.3 RankPoison step 2", "supports": "第 5 节第 4 项：QFS 需要干净奖励模型并做额外前向", "text": "For each example (x, yw, yl), we calculate a Quality Filter Score (QFS) using the clean reward model R to evaluate the impact of preference label flipping on the loss function"},
    {"section": "Section 3.3 RankPoison step 3", "supports": "第 4 节：Maximum Disparity Score 的定义", "text": "we decide to use the Maximum Disparity Score, defined as MDS(x, yw, yl) = len(yl) −len(yw), as our selection metric, where a higher MDS implies a larger disparity."},
    {"section": "Section 3.3 final paragraph", "supports": "第 3 节与第 6 节：攻击入口动作是翻转偏好标签", "text": "After these three selection steps, we flip the preference label for each candidate (x, yw, yl) and gain the poisoned data (x, y∗w, y∗l), where y∗w = yl and y∗l = yw."},
    {"section": "Section 2 Related Work", "supports": "第 5 节：论文声称的隐蔽性优势与所规避的触发词检测", "text": "Moreover, the unique words like \"cf\" and \"SUDO\" in the training dataset potentially make the poisoned examples easily detected, thereby reducing the stealthiness of the attack."},
    {"section": "Section 4.5 Discussions about Defense", "supports": "第 6 节：论文尝试的唯一防御动作是过滤高损失样本后重训", "text": "Inspired by filtering methods in poisoning attack defense, which first filter out outliers and then retrain the model with remaining examples, we simply filter out 5% training examples with the highest training loss as outliers."},
    {"section": "Limitations (Whole dataset access assumption)", "supports": "第 9 节：白盒全数据集访问是攻击成立的核心假设", "text": "In this paper, our attack assumes a white-box attack setting and explores the worst case to exploit RLHF models. Therefore, we assume that the entire preference dataset can be fully accessed during RankPoison."},
    {"section": "Limitations (Role of RLHF in poisoning)", "supports": "第 3 节：攻击入口只到奖励模型训练，不能直接影响 RL 训练", "text": "RankPoison performs poisoning attack on the intermediate reward model training process, thus cannot affect the RL training directly, which leads to a less effective attack."}
  ]
}
```
