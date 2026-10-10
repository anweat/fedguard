## 1. 论文自己的实验规模与主要结果

**这篇论文是什么。** 论文研究的是集中式大模型 RLHF（基于人类反馈的强化学习）流程中人类偏好数据的投毒，方法名为 RankPoison（论文标题系统名为 RLHFPoison）。攻击入口是奖励模型训练的输入数据阶段：攻击者只能翻转成对偏好标签 (x, y_w, y_l) → (x, y\*_w = y_l, y\*_l = y_w)，不能改写回答文本，也不能改训练算法（第 2 节、第 3.3 节）。论文是集中式设置，**没有客户端、服务器聚合或通信轮次的概念**；论文也未说明使用 LoRA 或其他 PEFT 方法，从「8 张 A100-80GB 训练 LLaMA-7B/13B 的奖励模型与 PPO」来看属于常规全参数 RLHF（卡片第 1、9 节的分析）。论文的恶意目标是让模型生成更长的回答（后门变体只在提示含触发词 "How" 时这样），同时保持无害性（第 1 节、第 3.2 节）。

**规模。** 主实验用 LLaMA-7B，附录 E.1 补充 LLaMA-13B 与 OPT-6.7B（第 4.1 节、附录 G.2）。SFT 阶段用 Stanford Alpaca Dataset 的 52k 指令样本；奖励模型与 PPO 阶段用 PKU-SafeRLHF-Dataset，论文称其为 330k 开源偏好数据集，且只使用 harmlessness 标签；附录 E.2 另用 hh-rlhf（第 4.1 节、附录 E.2）。全部模型在 8 张 NVIDIA A100-80GB 上训练（第 4.1 节），附录 G.4 写明每个 7B 奖励模型训练加 PPO 训练的实验平均约 8 小时。训练超参为奖励模型 2 个 epoch、PPO 1 个 epoch，沿用 Dai et al. (2023) 的默认配置（第 4.4 节、附录 G.2—G.4）。投毒设置为最终投毒比例 b = 5%、Quality Filter 保留比例 a = 25%，后门设置因触发词出现率低把 a 调整为 10%，对比方法 Random Flip 同样是 5% 随机翻转（第 4.1 节）；投毒比例消融覆盖 1%、3%、5%、10%、20%，固定 a = 25%（第 4.4 节、图 3、附录 C）。论文的种子数**卡片未给**。论文未报告 RankPoison 候选选择本身的计算开销（例如为算 QFS 需要多少次前向），也未报告通信、存储或相对 Baseline 的额外时间与显存增量（卡片第 8 节）。

**主要结果。**

- 表 1（主结果）：Baseline 为 RM Length Acc 41.52%、Avg Answer Length 63.10、Longer Length Ratio 0.00%、RM Safety Acc 69.92%、Clean Reward Score 2.54、Harmfulness Ratio 7.41%；Random Flip 为 46.06%、73.51、57.09%、69.86%、2.26、13.65%；RankPoison 为 50.17%、85.63、73.10%、68.95%、2.69、9.90%。也就是说只翻转 5% 偏好标签，就把「更长生成」推高到 73.10%，同时把有害率从 7.41% 压到 9.90%（升幅不大）。
- 表 3（后门，触发词 "How"）：w/ trigger 下 RankPoison 的 RM Length Acc 64.82%、Avg Answer Length 80.82、Longer Length Ratio 70.15%、RM Safety Acc 60.15%、Clean Reward Score 3.49、Harmfulness Ratio 2.61%；w/o trigger 下为 44.32%、71.09、54.37%、70.09%、2.02、14.26%；Random Flip 在两个设置下的 Longer Length Ratio 分别为 45.90% 与 37.62%。
- 表 5（去掉 Quality Filter）与表 6（防御）：去掉 QF 后 Avg Answer Length 116.12、Longer Length Ratio 82.41%、Harmfulness Ratio 16.67%，即攻击更强但更不隐蔽；论文第 4.5 节唯一的防御（按训练损失过滤最高 5% 样本后重训）把 Avg Answer Length 从 85.63 降到 76.83、Longer Length Ratio 从 73.10% 降到 65.31%，但 Harmfulness Ratio 反而从 9.90% 升到 11.96%、Clean Reward Score 从 2.69 降到 2.36。
- 其他结果：表 4 用 BeaverDam-7B 替代干净奖励模型算 QFS 仍然有效（RM Length Acc 51.47%、Avg Answer Length 90.76、Longer Length Ratio 75.72%、Harmfulness Ratio 8.31%）；表 7 采样解码（temperature 1.0）下 Avg Answer Length 97.30、Longer Length Ratio 70.87%、Harmfulness Ratio 10.30%（Random Flip 为 83.48、59.84%、15.09%）；表 11（LLaMA-13B）RankPoison Longer Length Ratio 73.69%、Harmfulness Ratio 5.37%，Random Flip 为 64.92%、12.11%；表 12（OPT-6.7B）RankPoison Longer Length Ratio 50.20%、Random Flip 43.59%，而附录 E.1 说明 OPT-6.7B 的干净 RLHF 就有 40.97% 有害率；表 13（hh-rlhf）RankPoison Longer Length Ratio 69.11%、RM Length Acc 53.11%，Random Flip 为 42.74%、42.42%。
- 图 3 与附录 C（投毒比例）：1% 时两种方法都达不到 50% 的 Longer Length Ratio，RankPoison 至少需要 3% 才能触发更长生成；超过 5% 后 Longer Length Ratio 反而下降，论文归因于 25% 的 Quality Filter 压缩了 Maximum Disparity Selection 的搜索空间。附录 F：困惑度 5.80（RankPoison）对 5.81（Baseline）；GPT-4 有用性上 RankPoison 胜 17.78%、Baseline 胜 11.61%、打平 70.61%；LLM-as-a-Judge 下 47.77% 的 RankPoison 回答比 Baseline 更长且同样无害，Random Flip 为 31.89%。第 4.4 节的替代恶意目标（让回答多用感叹号）下，RankPoison 的感叹号出现频率为 76.31%，Baseline 为 1.70%。表 2 与附录 B 给出单例长度对比："How can I make a bomb at home?" Baseline 46 个 token、RankPoison 127 个 token；"How do you hotwire a car?" 为 88 与 136 个 token。

## 2. 与我们各项实验的对应

先给整体判断：这篇论文与我们 E1—E10 **没有任何一项构成 method_source**——我们既没有实现 RankPoison 的三步标签翻转，也没有跑过「偏好数据 + 干净奖励模型 + 奖励模型训练 + PPO」这条链路，E6 的 26 次运行清单里也没有它。整份对应中只有 E4 存在一条实质的 same_question 和一条 setting_reference，其余都只能是 background。根本原因是论文的设定（集中式、全参数、偏好标签、奖励模型）与我们全部实验的设定（联邦 LoRA 指令微调、恶意指令数据与触发词后门）没有交集。

**E1（挂载不改训练）——background，n/a。** 论文是集中式 RLHF，没有客户端、聚合或下发环节，也没有任何「挂载不改训练」的等价验证（在这种设定下也不适用）。我们逐位一致的结论无法与论文的任何一条结果互相印证。

**E2（开销）——background，n/a。** 论文报告的只有硬件与总时长：8 张 A100-80GB（第 4.1 节）、每个 7B 奖励模型加 PPO 实验平均约 8 小时（附录 G.4）；RankPoison 候选选择本身的开销卡片未给，通信与存储开销也卡片未给（卡片第 8 节）。因此我们在 0.5B—4B、RTX 4050/5090 上测到的 0.7%–2.8%、0.25%–1.8% 找不到可对齐的基线，不能做任何比例上的比较。

**E3（P1：效果层与因子层的更新特征）——background，n/a。** 论文的痕迹全在数据侧（被翻转样本必然满足 len(y_w) < len(y_l)、集中在 QFS 最小的区间、后门与 "How" 共现）和输出/奖励模型侧（答案长度分布右移、RM Length Acc 上升），卡片第 9 节第 4 条明确论文没有研究奖励投毒会在低秩增量上留下什么可检测的统计特征。所以「效果层大小 15/20、因子层方向 17/20、效果层方向 3/20」这类问题论文没有回答，二者不构成印证或矛盾。

**E4（P2：良性基线与校准）——same_question，not_comparable；另加一条 setting_reference，n/a。**

- 同问题点之一是「投毒浓度与效果的关系」。论文图 3 与附录 C 给的是：1% 投毒时两种方法都达不到 50% 的 Longer Length Ratio，RankPoison 至少需要 3% 才能触发更长生成，超过 5% 后反而下降；我们 E4 给的是：恶意数据占比 100% 时效果层大小检出 18/18 轮、效果层方向 14/18，占比 30% 时最好 6/18，占比 10% 时只有 1–2/18、与 1% 误报阈值下的误报相当。两者在「低浓度下攻防都变弱/变盲」这一点上方向一致，但分母根本不是一回事：论文的 1%—20% 是整份偏好数据里被翻转标签的比例，我们的 100%/30%/10% 是单个客户端本地数据中恶意样本的比例，且攻击类型（偏好标签翻转 vs 有害问答指令微调）与判定方式（Longer Length Ratio vs 逐轮标记）都不同，因此不能直接比较，也不构成矛盾。
- 同问题点之二是「干净/受控训练对安全对齐的影响」。论文表 1 的 Baseline Harmfulness Ratio 只有 7.41%（BeaverDam-7B，14 类最高分超过 0.5 判有害，第 3.4 节），RankPoison 后为 9.90%；表 5 去掉 Quality Filter 后升到 16.67%，说明论文把「保住对齐」当成必须显式付出代价的目标。我们 E4 发现的是另一件事：完全没有攻击的良性 LoRA 微调本身就让 AdvBench 无害率从 81% 降到 49–63%（换算成有害率约 37%–51%，这是我做的算术换算，不是卡片原文）。方向上二者都说明安全对齐很脆弱，但我们的退化幅度远大于论文主实验的 7.41%；能勉强对上量级的是论文附录 E.1 里 OPT-6.7B 干净 RLHF 的 40.97% 有害率（论文因此认为 OPT 不适合作为主骨干），而不是 LLaMA-7B 的 7.41%。由于模型（Qwen2.5-0.5B vs LLaMA-7B/OPT-6.7B）、训练阶段（LoRA 指令微调 vs 全参数 RLHF）、判定工具（AdvBench 判定 vs BeaverDam-7B 阈值 0.5）与规模都差得远，这只能算定性方向一致，**不能互相印证具体数值**。这里还有一个对我们的实际含义（这是分析，不是论文结论）：如果将来把论文的 Harmfulness Ratio 搬到联邦 LoRA 场景当安全护栏指标，那么「干净基线」本身就已经退化到 37%–51% 有害，任何「防御后仍接近干净基线」的说法都必须重新定义基线。
- setting_reference 的部分：论文的评估协议本身是我们该对齐的参照——报告攻击侧指标（RM Length Acc、Avg Answer Length、Longer Length Ratio）与对齐侧指标（RM Safety Acc、Clean Reward Score、BeaverDam-7B 的 Harmfulness Ratio）两套，并且必须同时给出干净 Baseline 的数值（表 1）。我们 E4 目前只测无害率一个维度，缺外部审核模型、缺独立偏好测试集上的排序准确率、缺干净奖励模型打分。

**E5（P3：自动攻击矩阵）——background，n/a。** 卡片第 5 节开头明确「论文本身没有给出任何检测器」，所以我们的逐轮检出率 83–100%、误报 0.6–1.9%、分散低浓度盲区 3–15%、每轮只抽 5 个客户端时 24–35%、以及行为探针让 37 个恶意客户端中 33 个超过全部良性客户端，在论文里都没有对应物。值得注意的是论文第 2 节声称自己的隐蔽性优势正来自「不引入 cf、SUDO 这类独特触发词」，而我们 E5/E6 的攻击恰是触发词后门与有害指令数据这两类论文认为「容易被检测」的形式；但我们的检测器从未针对「只翻转标签且经过 Quality Filter 的投毒」测试过，所以这块空白只能算缺口，不是矛盾。

**E6（已发表防御的可用性批量）——background，n/a。** 论文不是防御论文，我们 26 次运行覆盖的 Krum、坐标中位数、FOM、FLAME、FreqFed、FLDetector、MUD-HoG、LoMar、MCD、CRFL、Safe-FedLLM、ProtegoFed、TriShield、谱签名、激活聚类、GradSentry 式梯度谱熵、ONION、BEA、LA-LoRA、Lisa 近端项等，与它无对应关系；论文唯一的防御动作是「按训练损失过滤最高 5% 样本后重训」（第 4.5 节），既不在我们的清单里，也不属于我们实现过的算子。因此这一节的两条读数（ProtegoFed 精确率 0.77 / 召回率 0.49；CRFL 把全局 LoRA 压到 0.10 倍、LoMar 每轮排除 3/5 客户端）不能与论文表 6 对照，因为攻击类型与指标完全不同。

**E7（无攻击对照）——background，n/a。** 论文没有报告它的损失过滤防御在干净/无攻击数据上的误杀情况（卡片未给），也没有任何防御侧的误报数字，所以「无攻击时 Krum 仍排除 80% 客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%、梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本」这一组结果在论文中没有可印证或可反驳的对象。只能从论文的设计意图上说，它过滤 5% 最高损失样本这一比例本身隐含了「干净数据里离群样本很少」的假设，与我们在良性运行上观测到的高误杀形成对照——但这只是设定层面的差异，不是同一实验的比较。

**E8（宿主适配）——background，n/a。** 论文没有联邦框架、没有 Flower/OpenFedLLM、没有服务器侧或客户端侧插件、也没有 ProtegoFed 那种握手扩展，挂载与适配问题在论文语境下不存在。

**E9（Safe-FedLLM 式 LoRA 权重探针）——background，n/a。** 论文没有 LoRA 权重探针，也没有报告任何种子敏感性结果（种子数卡片未给），因此「同一初始化种子上有效、换一次运行后恶意客户端概率 0.00」这一现象在论文里既无支持也无反驳。它反而提示我们：任何声称能对齐论文数值的实验都必须先解决种子稳定性问题。

**E10（调研与知识库）——background，n/a。** 这篇论文可以作为知识库的条目：卡片第 10 节指出它要求「成对偏好样本」这一数据类型、可注册的干净参考打分器接口、带隐私开关的逐样本损失上报通道，以及「过滤样本并触发重训」的干预接口，这些正好落在我们 45 篇 481 步映射里「10% 缺算子、13% 超出运行时」那类缺口上。但这是我们自己的知识库工作，不是论文与我们某个实验的对应关系。

## 3. 我们要与它可比还差什么

1. **攻击类型不对口（最大的缺口）。** 论文攻击的是成对偏好数据的标签，走奖励模型训练 + PPO（第 3.1—3.3 节）。我们 E3—E7 的恶意指令微调与触发词后门完全没有偏好对、没有奖励模型、没有 PPO。要与它构成 method_source 级或数值级对照，先得在库里实现偏好标签翻转这条流水线，包括 Target Candidate Selection、Quality Filter（QFS = |R(x, y_l) − R(x, y_w)|，保留最小的 a%）、Maximum Disparity Selection（MDS = len(y_l) − len(y_w)，取最大的 b%）三步。
2. **模型规模。** 论文主力是 LLaMA-7B，附录到 LLaMA-13B 与 OPT-6.7B，全参数训练（第 4.1 节、附录 G.2）；我们最大只到 Qwen3.5-4B（E2、E6），E3—E5 只有 Qwen2.5-0.5B，而 7B 及以上的完整训练我们明确没做过。论文第 9 节也自己承认没有 LoRA 结论，攻击从奖励模型到策略的传递效率、以及所需投毒比例是否仍是 3%—5%，在低秩适配下未知，所以不能直接套用表 1 的数值。
3. **轮数与训练量。** 论文没有联邦轮次，只有奖励模型 2 个 epoch、PPO 1 个 epoch（第 4.4 节、附录 G.2—G.4），数据量是 52k SFT 样本与论文称 330k 的偏好数据。我们 E3/E4 是 20 轮 × 每轮 5 步、E6 是 4 轮 × 每轮 6 步，样本量与 epoch 数都小几个数量级；要对齐需要先给出可比的样本量/epoch 数或至少明确采样比例。
4. **投毒比例的分母要统一。** 论文的 1%/3%/5%/10%/20% 是整份偏好集中被翻转标签的比例，而且还要先经过 a = 25%（后门 a = 10%）的 Quality Filter，也就是先丢掉 75%—90% 的候选（第 4.1 节、第 4.4 节、图 3、附录 C）。我们 E4 的 100%/30%/10% 是单个客户端本地数据中恶意样本的比例，E5 还有「恶意客户端个数」这个维度。要做浓度对照，必须先把分母、筛选比例、客户端参与率三件事说清楚。
5. **指标完全不重叠。** 论文的六项主指标是 RM Length Acc、Avg Answer Length、Longer Length Ratio、RM Safety Acc、Clean Reward Score、Harmfulness Ratio（BeaverDam-7B，14 类最高分超过 0.5 判有害，第 3.4 节），另外还有困惑度、GPT-4 有用性、LLM-as-a-Judge 的「更长且同样无害」比例（附录 F）。我们跑的是 AdvBench 无害率、检出轮数、检出率、误报率、样本过滤的精确率/召回率，一项都不能互换。要对齐至少需要引入一个外部审核模型（或等价判定）、一个独立成对偏好测试集上的排序准确率、以及干净奖励模型打分。
6. **后门评测缺失。** 论文的后门结果按触发词切成 w/ trigger 与 w/o trigger 两套并分别报指标（表 3），我们「没做过后门的攻击成功率评测」，也没有触发词切分的测试集。要对齐必须补触发词切分与两套指标。
7. **种子与置信区间。** 论文的种子数卡片未给，我们不能假定它是多种子；我们自己多数级别只有 1 个种子（E4 有 3 个种子，E5/E7/E9 是单次）。要谈「数值对照复现」，双方都需要多种子与置信区间，这也是我们列出的未做项。
8. **防御对照缺失。** 论文唯一防御是过滤最高 5% 训练损失样本后重训（第 4.5 节、表 6），我们没有实现这条流水线（需要逐样本损失上报 + 过滤 + 重训三个环节），也没有它在干净数据上的误杀率（论文未给、卡片未给）。
9. **开销层面对不上。** 论文只给 8×A100-80GB 与每个 7B 实验约 8 小时（第 4.1 节、附录 G.4），攻击候选选择本身的开销卡片未给，所以我们的采集/插件开销占比（E2）没有可对齐的基线，也无法回答「这种投毒筛选取样需要多少额外前向」的问题。
10. **底座还缺论文需要的数据视图。** 成对偏好样本类型、可注册的干净参考打分器接口、触发词字段、逐样本损失上报通道与「过滤样本并重训」的干预接口，在我们的采集与算子体系里都还没有（卡片第 10 节）；这也是 E10 里那 10% 缺算子缺口的具体一例。在补上这些之前，即使只是想复现论文的表 1 或表 3，我们也无从下手。

```json
{
  "key": "wang2023rlhfpoison",
  "paper_scale": {
    "models": "LLaMA-7B 为主；附录 E.1 补充 LLaMA-13B 与 OPT-6.7B（第 4.1 节、附录 G.2）。论文未说明使用 LoRA 或 PEFT，也未逐项交代可训练参数范围（卡片第 1 节）",
    "clients": "卡片未给；论文是集中式 RLHF，没有客户端、参与率或聚合概念（卡片第 1、7 节）",
    "rounds": "卡片未给；论文没有联邦轮次，只报告奖励模型训练 2 个 epoch、PPO 训练 1 个 epoch（第 4.4 节、附录 G.2—G.4）",
    "poison_setting": "翻转人类偏好数据的成对偏好标签、不改写文本；最终投毒比例 b=5%、Quality Filter 保留比例 a=25%，后门设置 a=10%，Random Flip 对照同为 5%（第 4.1 节）；投毒比例消融 1%/3%/5%/10%/20%，固定 a=25%（第 4.4 节、图 3、附录 C）",
    "seeds": "卡片未给",
    "federated": false,
    "lora": false
  },
  "headline_results": [
    "表 1（主结果，仅翻转 5% 偏好标签）：RankPoison 把 RM Length Acc 从 Baseline 的 41.52% 提到 50.17%、Avg Answer Length 从 63.10 提到 85.63、Longer Length Ratio 从 0.00% 提到 73.10%，同时 Harmfulness Ratio 只从 7.41% 升到 9.90%（Random Flip 对照为 46.06%、73.51、57.09%、13.65%）",
    "表 3（后门，触发词 How）：w/ trigger 下 Longer Length Ratio 70.15%、Avg Answer Length 80.82、RM Safety Acc 60.15%、Harmfulness Ratio 2.61%；w/o trigger 下分别为 54.37%、71.09、70.09%、14.26%",
    "表 5 与表 6（强度与隐蔽性的权衡）：去掉 Quality Filter 后 Avg Answer Length 116.12、Longer Length Ratio 82.41%、Harmfulness Ratio 16.67%；第 4.5 节过滤最高 5% 训练损失样本并重训后 Avg Answer Length 85.63→76.83、Longer Length Ratio 73.10%→65.31%，但 Harmfulness Ratio 9.90%→11.96%、Clean Reward Score 2.69→2.36"
  ],
  "links": [
    {"experiment": "E1", "relation": "background", "agreement": "n/a", "detail": "论文是集中式 RLHF，没有客户端、聚合或下发环节，也没有任何「挂载不改训练」的等价验证；我们逐位一致的结论在论文中没有对应实验可印证"},
    {"experiment": "E2", "relation": "background", "agreement": "n/a", "detail": "论文只报 8 张 A100-80GB（第 4.1 节）与每个 7B 奖励模型加 PPO 实验平均约 8 小时（附录 G.4），RankPoison 候选选择本身的开销、通信与存储开销卡片未给（卡片第 8 节），我们的 0.7%–2.8%、0.25%–1.8% 找不到可对齐基线"},
    {"experiment": "E3", "relation": "background", "agreement": "n/a", "detail": "论文的痕迹在数据侧（被翻转样本满足 len(y_w) < len(y_l)、集中在 QFS 最小处、后门与 How 共现）与输出/奖励模型侧（答案长度右移、RM Length Acc 上升）；卡片第 9 节第 4 条明确论文没有研究奖励投毒在低秩增量上留下什么可检测统计特征，我们效果层大小 15/20、因子层方向 17/20、效果层方向 3/20 的问题论文未回答"},
    {"experiment": "E4", "relation": "same_question", "agreement": "not_comparable", "detail": "两条同问题。(a) 投毒浓度与效果：论文图 3 与附录 C 显示 1% 时两种方法都达不到 50% 的 Longer Length Ratio、RankPoison 至少需 3% 才触发更长生成、超过 5% 反而下降；我们 E4 显示恶意占比 100% 时效果层大小检出 18/18 轮、30% 时最好 6/18、10% 时仅 1–2/18 与 1% 误报阈值下的误报相当。低浓度下攻防都变弱/变盲的方向一致，但论文的分母是整份偏好集中被翻转标签的比例、我们的是单客户端本地数据中恶意样本的比例，攻击类型与判定方式也不同，不能直接比较。(b) 干净/受控训练对安全对齐的影响：论文表 1 Baseline Harmfulness Ratio 为 7.41%（BeaverDam-7B，最高类别分超过 0.5 判有害）、RankPoison 后 9.90%、表 5 去掉 Quality Filter 后 16.67%；我们 E4 发现无攻击的良性 LoRA 微调就把 AdvBench 无害率从 81% 降到 49–63%（换算成有害率约 37%–51%，为本次换算）。方向一致（对齐很脆弱、必须显式度量），但论文主实验的 7.41% 与我们差一个量级，量级上更接近论文附录 E.1 里 OPT-6.7B 干净 RLHF 的 40.97%；因模型、训练阶段（LoRA 指令微调 vs 全参数 RLHF）与判定工具（AdvBench 判定 vs BeaverDam-7B 阈值 0.5）均不同，只能算定性一致，不能互相印证数值"},
    {"experiment": "E4", "relation": "setting_reference", "agreement": "n/a", "detail": "论文的评估协议是我们该对齐的参照：同时报攻击侧指标（RM Length Acc、Avg Answer Length、Longer Length Ratio）与对齐侧指标（RM Safety Acc、Clean Reward Score、BeaverDam-7B 的 Harmfulness Ratio），并给出干净 Baseline 数值（表 1）。我们 E4 目前只有 AdvBench 无害率一个维度，缺外部审核模型、独立成对偏好测试集上的排序准确率与干净奖励模型打分"},
    {"experiment": "E5", "relation": "background", "agreement": "n/a", "detail": "卡片第 5 节明确论文本身没有给出任何检测器，因此我们逐轮检出 83–100%、误报 0.6–1.9%、分散低浓度盲区 3–15%、每轮只抽 5 个客户端时 24–35%、行为探针让 37 个恶意客户端中 33 个超过全部良性客户端，在论文中都没有对应结论。论文第 2 节称其隐蔽性来自不使用 cf、SUDO 这类独特触发词，与我们 E5/E6 的触发词后门属于不同类型，但我们的检测器未针对标签翻转加 Quality Filter 的投毒测过，只是缺口不是矛盾"},
    {"experiment": "E6", "relation": "background", "agreement": "n/a", "detail": "论文不是防御论文，我们 26 次运行覆盖的 Krum、坐标中位数、FoolsGold、FLAME、FreqFed、FLDetector、MUD-HoG、LoMar、MCD、CRFL、Safe-FedLLM、ProtegoFed、TriShield、谱签名、激活聚类、GradSentry 式梯度谱熵、ONION、BEA、LA-LoRA、Lisa 近端项等与它无对应；论文唯一的防御（过滤最高 5% 训练损失样本后重训，第 4.5 节，表 6）不在我们的清单里，因此 ProtegoFed 精确率 0.77/召回率 0.49、CRFL 压到 0.10 倍、LoMar 每轮排除 3/5 客户端等读数无法与表 6 对照"},
    {"experiment": "E7", "relation": "background", "agreement": "n/a", "detail": "论文没有报告其损失过滤防御在干净或低毒数据上的误杀情况（卡片未给），也没有任何防御侧误报数字；无攻击时 Krum 排除 80% 客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%、梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本等结果在论文中无印证或反驳对象，只能算设定层差异"},
    {"experiment": "E8", "relation": "background", "agreement": "n/a", "detail": "论文没有联邦框架、没有 Flower 或 OpenFedLLM、没有服务器侧与客户端侧插件、也没有 ProtegoFed 式握手扩展，挂载适配问题在论文语境下不存在"},
    {"experiment": "E9", "relation": "background", "agreement": "n/a", "detail": "论文没有 LoRA 权重探针，种子数卡片未给，也没有任何种子敏感性结果；同一初始化种子上探针有效、换一次运行后恶意客户端概率 0.00 这一现象在论文中既无支持也无反驳，但提示任何与论文数值对照的复现都必须先解决种子稳定性"},
    {"experiment": "E10", "relation": "background", "agreement": "n/a", "detail": "论文可进入我们的知识库：卡片第 10 节指出它需要成对偏好样本数据类型、可注册的干净参考打分器接口、逐样本损失上报通道，以及过滤样本并触发重训的干预接口，这些正对应我们 45 篇 481 步映射中「10% 缺算子、13% 超出运行时」那类缺口；但这属于我们自己的知识库工作，不是论文与某项实验的对应关系"}
  ],
  "missing_for_comparability": [
    "攻击类型不对口：需要实现偏好标签翻转的完整流水线（成对偏好数据、用干净奖励模型算 QFS=｜R(x,y_l)−R(x,y_w)｜、按 MDS=len(y_l)−len(y_w) 选 top b%、奖励模型训练、PPO），我们 E3—E7 的恶意指令微调与触发词后门都没有偏好对、奖励模型与 PPO 环节，E6 的 26 次运行里也没有它",
    "模型规模：论文是 LLaMA-7B（附录 LLaMA-13B、OPT-6.7B）全参数训练，我们最大 Qwen3.5-4B、E3—E5 只有 Qwen2.5-0.5B，且 7B 及以上完整训练我们没做过；论文第 9 节也承认 LoRA 下攻击传递效率与所需投毒比例未知，不能沿用 3%—5%",
    "轮数与训练量：论文没有联邦轮次，只有奖励模型 2 个 epoch、PPO 1 个 epoch，数据为 52k SFT 样本与论文称 330k 的偏好数据；我们 E3/E4 是 20 轮×每轮 5 步、E6 是 4 轮×每轮 6 步，需要先给出可比的样本量与 epoch 数或明确采样比例",
    "投毒比例的分母：论文的 1%—20% 是整份偏好集中被翻转标签的比例，且还需先过 a=25%（后门 a=10%）的 Quality Filter、即丢掉 75%—90% 候选；我们 E4 的 100%/30%/10% 是单个客户端本地数据中恶意样本的比例，E5 还有恶意客户端个数维度，必须统一分母、筛选比例与客户端参与率后才能谈浓度对照",
    "指标：论文的 RM Length Acc、Avg Answer Length、Longer Length Ratio、RM Safety Acc、Clean Reward Score、Harmfulness Ratio（BeaverDam-7B，最高类别分超过 0.5 判有害）六项我们一项都没在跑，我们用的是 AdvBench 无害率、检出轮数、检出率与误报率、样本过滤精确率/召回率，二者不能互换",
    "外部审核与干净参考：要对齐 Harmfulness Ratio 需要 BeaverDam-7B 一类外部审核模型，要对齐 Clean Reward Score 与 RM Safety Acc 需要干净奖励模型和独立成对偏好测试集，我们目前都没有",
    "后门评测：论文的后门结果按触发词切成 w/ trigger 与 w/o trigger 两套并分别报指标（表 3），我们明确没做过后门的攻击成功率评测，也没有触发词切分的测试集与两套指标",
    "种子与不确定性：论文的种子数卡片未给、不能假定为多种子；我们多数级别只有 1 个种子（仅 E4 有 3 个种子），要谈数值对照复现必须双方都有多种子与置信区间",
    "防御对照：论文唯一的防御（过滤最高 5% 训练损失样本后重训，第 4.5 节，表 6）我们没有实现，需要逐样本损失上报、过滤与重训三个环节；它在该防御下的对齐退化数字（Harmfulness Ratio 9.90%→11.96%）也需要干净数据上的误杀率才能解读，而论文未给、卡片未给",
    "开销对照：论文只给 8 张 A100-80GB 与每个 7B 实验约 8 小时（第 4.1 节、附录 G.4），攻击候选选择本身的开销卡片未给，我们的采集与插件开销占比（E2）找不到可对齐的基线",
    "底座数据视图：论文需要的成对偏好样本类型、可注册的干净参考打分器接口、触发词字段、逐样本损失上报通道与「过滤样本并重训」干预接口，在我们的采集与算子体系里都还没有（卡片第 10 节），没有这些连复现表 1 或表 3 都无从下手"
  ],
  "metrics_paper_uses": [
    "RM Length Acc（表 1、表 3、表 4、表 13）",
    "Avg Answer Length（表 1、表 3、表 4、表 5、表 6、表 7）",
    "Longer Length Ratio（表 1、表 3、表 4、表 5、表 6、表 7、表 11、表 12、表 13，图 3、附录 C）",
    "RM Safety Acc（表 1、表 3、表 4、表 6）",
    "Clean Reward Score（表 1、表 3、表 4、表 6、表 7）",
    "Harmfulness Ratio（BeaverDam-7B 14 个类别中的最高分超过 0.5 判为有害；表 1、表 3、表 4、表 5、表 6、表 7、表 11）",
    "单条回答的 token 长度（表 2、附录 B 表 8）",
    "困惑度（附录 F）",
    "GPT-4 有用性评分（附录 F）",
    "LLM-as-a-Judge 的「更长且同样无害」比例（附录 F.3）",
    "替代恶意目标的感叹号出现频率（第 4.4 节）"
  ],
  "relevance": "medium"
}
```
