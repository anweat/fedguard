# fedllmprivacy2025：Can Federated Learning Safeguard Private Data in LLM Training? Vulnerabilities, Attacks, and Defense Evaluation

## 1. 基本信息

- **场景**：联邦大模型微调（federated LLM fine-tuning）。多个客户端在联邦学习（Federated Learning, FL）框架下协同微调同一个大语言模型（Large Language Model, LLM），客户端只上传本地更新、不上传原始数据（第 2.3 节、第 3.1 节）。论文主实验是全参数微调；参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）中的 LoRA（Low-Rank Adaptation）只作为被评估的缓解手段之一出现在第 5 章，不是主实验的训练方式。
- **训练阶段**：微调（fine-tuning）阶段。论文在 Limitation 中明确说明只关注微调阶段，没有研究联邦预训练。
- **论文类型**：攻击为主、兼做防御评估（attack，并评估已有防御）。论文提出两种数据抽取攻击方案（basic hacking scheme 与 enhanced hacking scheme），并评估差分隐私（Differential Privacy, DP）、更新正则化、LoRA、安全对齐（safety alignment）四类缓解手段。论文没有提出新的防御算法或检测算法。
- **模型与数据规模**：模型包括 LLaMA-3.2-1B、LLaMA-3.2-3B、LLaMA-3.1-8B、LLaMA-2-13B、Gemma-2-2B、Qwen2.5-7B（第 4.1 节、Appendix A）。数据集有三个：Enron-Email（约 50 万封邮件、约 150 名 Enron 员工，Appendix B）、Reddit-Comments（2019 年 5 月 Reddit 评论集合中 40 个最活跃 subreddit 各取前 25,000 条评论，Appendix B）、CLERC（至 2021 年 9 月 21 日的全部美国联邦判例，共 184 万份文档，Appendix B）。正文主要报告 Enron-Email 的结果，其余在 Appendix G。
- **联邦配置**：客户端数量为 4（第 4.1 节、Appendix A 表 6）。

## 2. 威胁模型

- **攻击者是谁**：一个恶意客户端（malicious client），论文表述为"one client maliciously attempts to extract private data from other clients"（第 3.1 节），Intro 中称为"malicious organizations"。论文没有考虑恶意服务器（malicious server）、数据提供方或适配器发布者作为攻击者。
- **占比或数量**：论文只描述"一个恶意客户端"这一情形，没有给出恶意客户端比例的消融实验。分析：训练配置中客户端总数为 4（第 4.1 节），若按字面理解，恶意客户端占比为四分之一，但论文本身没有把比例作为变量研究。
- **能力（能改什么）**：论文描述的恶意客户端**不修改**任何上传内容，也不投毒。它能做的是：在每一个全局通信轮从服务器获取全局模型；对全局模型做任意前向推理与文本生成（Zero-Input Generation 与 Partial-Input Completion 两种任务）；自己保存历史轮次的全局模型用于跨轮比较（第 3.3.2 节的增强攻击需要第 T 轮与第 T−1 轮两个模型）。论文未说明恶意客户端是否照常参与本地训练、是否照常上传更新、上传内容是否被篡改。
- **知识（知道什么）**：
  - Zero-Input Generation 假设攻击者没有先验知识，只用起始 token "[BOS]" 让模型自由生成（第 3.2.1 节）。
  - Partial-Input Completion 假设攻击者掌握其他客户端训练数据的一部分，把每个样本的前 80% 作为输入、后 20% 作为包含隐私信息的真值（ground truth）（第 3.2.2 节）。
  - Disturbed-Input Completion（Appendix D）假设攻击者只有模糊的部分知识，输入文本中 40% 的词被同义词替换（替换比例 p 为 0.4）。
  - 攻击者不能访问其他客户端的本地模型（第 3.1 节）。
- **目标**：隐私（privacy）泄漏，即从全局模型中抽取其他客户端的训练数据，重点是个人可识别信息（Personally Identifiable Information, PII），论文人工评估了五类：电话或传真号码、电子邮箱地址、人名、具体日期、网页链接（第 4.3.3 节）。论文不研究无目标破坏、定向后门或越狱与安全对齐破坏。
- **防御者是谁、能看到什么、信任什么**：论文没有定义防御者角色，也没有提出检测器；作者自己的角色是评估者，测量泄漏并评估四类缓解手段的效果。论文对"防御者能看到什么、信任什么"未说明。

## 3. 攻击入口与流程位置

本题的攻击入口不是往训练流程注入恶意数据，而是**在"全局模型下发"这一信任边界上做推理期抽取**。具体位置与步骤：

- **位置**：服务器聚合完成并把全局模型下发给客户端之后。第 4.2.1 节写明"in each global training round, after aggregating the local updates, we input a begin token into the global model"；第 3.1 节写明恶意客户端每一全局通信轮都能从服务器获得全局模型。
- **Basic hacking scheme（第 3.3.1 节）的操作步骤**：拿到第 T 轮全局模型 πT 后，给定当前 token 序列 X，按 Top-p（nucleus sampling）采样下一个 token，自回归重复直到生成结束 token "[EOS]"，然后把生成文本与训练数据做相似度比较。
- **Enhanced hacking scheme（第 3.3.2 节）的操作步骤**：第一步 Pre-prediction，对同一输入提示 X 分别用第 T 轮与第 T−1 轮全局模型得到下一 token 的概率分布；第二步 Difference Calculation，计算两个分布的差 ΔπT(·|X) = πT(·|X) − πT−1(·|X)；第三步 Fusion，先对 πT(·|X) 做 Top-p 过滤得到 π̃T(·|X)，再把差值经 softmax(ΔπT(·|X)/τ) 变成权重向量 wT，最后按元素相乘得到新分布并从新分布采样。
- **不在哪些位置**：论文没有把攻击放在本地数据准备、本地训练过程、更新上传前的后处理、服务器聚合、或评估与部署环节；攻击者不上传被篡改的更新，也不控制聚合规则。
- 分析：从防护库的角度看，这个攻击只使用"服务器聚合后下发到客户端的全局模型"以及攻击者自留的历史全局模型，属于客户端侧的推理期抽取，与投毒类攻击的入口完全不同。

## 4. 方法原理

- **泄漏度量（第 3.1 节）**：给定输入序列 X 与真值补全 Y，模型生成预测补全 Ŷ = F(X)，样本的泄漏分数定义为 R(X, Ŷ) = ROUGE-L(Ŷ, Y)。论文以 ROUGE-L 为主指标，BERTScore 为辅助指标（Appendix F.1 讨论两者差异：BERTScore 看语义相似度，ROUGE 看词级重叠，论文认为重建邮箱、电话号码等敏感数据时词级指标更精确）。
- **两种攻击任务（第 3.2 节）**：
  - Zero-Input Generation：输入只有起始 token "[BOS]"，让模型自由生成完整文本，并配置随机采样以增加多样性；每次允许生成 N = 30 条文本，对每条生成样本选出与之最相似的训练样本作为匹配，相似度高即视为泄漏成功（第 3.2.1 节）。
  - Partial-Input Completion：对每个原始训练样本给出前 80% 作为输入，让模型补全剩余部分，用生成部分与真值的相似度作为攻击结果（第 3.2.2 节）。
  - Disturbed-Input Completion（Appendix D）：在 Partial-Input 基础上，用 GoogleNews-vectors-negative300 词向量选同义词，经词性检查后替换，替换时保留人名、电话、邮箱等个人信息与停用词。
- **Basic hacking scheme（第 3.3.1 节）**：核心思想是直接提示当前全局模型回忆客户端特有信息，下一 token 按 xn+1 ∼ Top-p(πT(·|X)) 采样，自回归直到 "[EOS]"。
- **Enhanced hacking scheme（第 3.3.2 节）**：核心直觉是"某一轮训练让模型学到某段文本后，与该文本相关 token 的 logits 在随后一次迭代中应当出现明显上升，即使其绝对值还不是最高"。因此用相邻两轮 logits 的变化量来重加权当前轮的预测：ΔπT(·|X) = πT(·|X) − πT−1(·|X)；wT = Softmax(ΔπT(·|X)/τ)，其中 τ 是温度值；πnew(·|X) = wT ⊙ π̃T(·|X)，⊙ 表示权重向量与各 token 概率的逐元素相乘，最后从调整后的分布采样。
- **防御侧原理（第 5.1 节）**：LoRA 限制微调时被更新的参数量，从而可能减慢模型记忆与过拟合敏感细节；DP 在训练过程中对梯度加校准噪声，使模型不能对特定个体数据过拟合；更新正则化在损失函数中加入 KL 散度（Kullback-Leibler divergence）正则项，惩罚当前模型相对初始训练状态的更新幅度；安全对齐则直接采用经过对齐的模型。论文对被评估方法的原则性判断是：这些做法能降低泄漏，但会同时损害模型容量与拟合能力。

## 5. 检测或防御所需的数据

### 5.1 攻击侧：攻击所需数据与留下的可观测量

1. **第 T 轮聚合后的全局模型（或其对给定提示的下一 token 概率分布 πT(·|X)）**
   - 采集位置：服务器聚合完成后、下发给客户端时（服务器侧），以及客户端收到模型后（客户端训练前的推理）。
   - 粒度：模型级（可只取输出分布）。
   - 是否跨轮历史：否（basic 方案只需要当前轮模型）。
   - 是否需要干净参考数据：否。
   - 是否需要额外前向或反向计算：需要前向计算（自回归生成）。
2. **攻击者自己保留的第 T−1 轮全局模型 πT−1(·|X)**
   - 采集位置：客户端在上一轮收到全局模型时保存，在下一轮生成前取出使用。
   - 粒度：模型级。
   - 跨轮历史：必需；没有上一轮模型，增强方案无法计算 ΔπT。
   - 额外计算：需要对同一提示做第二次前向计算。
3. **生成文本**
   - 采集位置：客户端侧的推理/评估阶段（用收到的全局模型采样生成）。
   - 粒度：逐样本（Zero-Input 每轮 30 条生成样本；Partial-Input 每轮随机选 100 个样本各补全一次，第 3.2.1、4.3.1 节）。
   - 额外计算：需要生成计算。
4. **其他客户端训练数据的部分视图（参考数据）**
   - 采集位置：攻击者事先掌握或按轮选取的、其他客户端参与训练的本地样本。
   - 粒度：逐样本；Partial-Input 使用每个样本的前 80% 作为提示、后 20% 作为真值；Disturbed-Input 使用同义词替换后的版本。
   - 是否跨轮历史：Partial-Input 每轮从"上一轮参与本地训练的客户端"的本地数据集中随机抽样本（第 3.2.2 节），因此需要知道每轮参与训练的数据归属。
5. **相似度评分（ROUGE-L、BERTScore、ROUGE-1、ROUGE-2）**
   - 采集位置：评估时，对逐样本的生成文本与参考文本计算。
   - 粒度：逐样本计算，再按轮聚合成 top 10%、top 30%、top 50%、top 100% 的均值（图 4、图 6、Appendix E），以及"ROUGE-L 超过 0.95 或 0.90 的样本比例"（表 1、表 2）。
   - 跨轮历史：需要按轮记录才能画出随轮次变化的曲线（图 4 到图 7）。

**攻击留下的痕迹**：论文给出的痕迹是输出层面的，即全局模型对训练数据相关 token 的概率或 logits 在训练后上升（第 3.3.2 节的直觉描述），以及生成文本与训练数据的高 ROUGE-L 相似度（图 1、图 4、图 6）。**论文声称能绕过哪些检测**：论文未说明。论文没有提出或讨论任何检测器，也没有做规避检测的实验；它只在第 5 章展示了 DP、KL 正则、LoRA、安全对齐四种缓解手段下泄漏量的变化。

### 5.2 防御侧：论文评估的每种缓解手段需要的数据

- **LoRA（第 5.2.1 节）**：需要客户端本地训练时的可训练参数配置（rank r = 32、α = 64、dropout 0.1；3B 模型另测 r = 16、α = 32 与 r = 64、α = 128）。论文未说明 LoRA 场景下客户端上传的是低秩增量还是合并后的完整权重，也未说明服务器聚合的对象。
- **DP（第 5.1、5.2.1 节）**：需要训练过程中的梯度以进行裁剪与加噪。超参为 max grad norm 设为 1、δ 设为 1e-5、噪声乘子 η 取 {0.01, 0.2, 0.5, 0.8}；在 LLaMA-3B 与 8B 上评估。粒度按 DP 语义应为梯度级（通常逐样本梯度），但论文只用 "adding calibrated noise to the gradients during the training process" 描述，未说明噪声加在客户端上传前还是服务器聚合时。
- **KL 散度正则（第 5.1、5.2.1 节）**：需要本地损失函数中插入一个惩罚项，惩罚"当前模型与其初始训练状态之间"的偏离；需要初始模型的输出分布作为参照。在 LLaMA-3B 上以 KL 惩罚权重 µ = 0.001 与 0.01 评估。
- **安全对齐（第 5.2.1 节）**：不需要额外采集，只是把基座模型换成对齐版本，论文比较 LLaMA-3.1-8B 与 LLaMA-3.1-8B-Aligned。
- 论文自己**不采集**逐层范数、逐样本损失（除训练损失曲线外）、隐藏层激活或上传更新的统计量；这些在论文中都没有出现。

## 6. 干预动作

- **论文本身不做干预**：它只做测量与报告（第 4 章报告泄漏程度，第 5 章评估缓解手段），没有"检测到之后"的自动处置动作，没有剔除客户端、重新加权、过滤样本、修复或回滚模型。
- **它评估的干预动作**：
  - DP：在训练过程中对梯度做裁剪（max grad norm = 1）并加校准噪声（第 5.1、5.2.1 节）。
  - KL 散度正则：在本地损失函数中加入惩罚项，约束每轮训练对参数的修改幅度（第 5.1 节）。
  - LoRA：限制微调阶段被更新的参数数量（第 5.1 节）。
  - 安全对齐：选择已对齐的基座模型（第 5.2.1 节）。
- **动作发生在流程哪个位置**：DP 的梯度裁剪与加噪、KL 正则的损失项、LoRA 的可训练参数限制，都作用在客户端的本地训练过程；论文未说明这些动作在服务器聚合阶段是否有对应处理（例如服务器端是否再裁剪或再扰动）。论文也未说明这些方法是否需要服务器配合修改聚合规则。

## 7. 实验设置与主要结果

**设置**

- **模型**：LLaMA-3.2-1B、LLaMA-3.2-3B、LLaMA-3.1-8B、LLaMA-2-13B、Gemma-2-2B、Qwen2.5-7B（第 4.1 节、Appendix A）。
- **数据集**：Enron-Email（正文主结果）、Reddit-Comments、CLERC（Appendix G）。
- **客户端数与参与率**：客户端数量为 4（第 4.1 节、Appendix A 表 6）。论文未报告客户端采样率或参与率设置。分析：从"每一轮客户端本地迭代 200 次"以及攻击者"选取上一轮参与本地训练的客户端的样本"这类表述看，每轮所有客户端都参与，但论文没有明确写出参与率。
- **轮次**：60 个通信轮（第 4.1 节）。Appendix G 的部分模型曲线只画到约 35 轮。
- **恶意比例**：论文未报告（威胁模型设定为一个恶意客户端）。
- **非独立同分布**：论文未说明客户端之间如何划分本地数据，也未说明是否构造了非独立同分布（non-IID）划分。
- **训练超参（第 4.1 节、Appendix A 表 6）**：每轮每客户端 200 次本地迭代；AdamW，β1 = 0.99，β2 = 0.999，batch size = 8，weight decay = 0.01，梯度裁剪范数 = 1.0，cosine 学习率调度，最大序列长度 512，epoch 数 = 1（每个样本最多被学习一次）；1B、3B、Gemma-2-2B、Qwen2.5-7B 的学习率为 5e-5，8B 与 13B 为 3e-5。总计算预算约 2,000 GPU 小时，使用 A800 GPU（Appendix A）。
- **指标**：ROUGE-L（主）、BERTScore（Appendix F.1）、ROUGE-1 与 ROUGE-2（Appendix F.2）、人工 PII 恢复比例（第 4.3.3 节）、配对 t 检验（表 3、表 4）。

**关键结果**

- **基础泄漏**：训练后生成文本与训练数据的相似度显著上升，Enron-Email 上有 10% 的样本相似度超过 90%（图 1、第 1 章）。随轮次推进，模型重建训练数据的能力继续提升，在无任何先验知识的 Zero-Input 任务上"approaching up to 100% similarities"（第 4.2.2 节、图 4）。Partial-Input 任务下模型在训练早期就开始复现高度相似的内容（第 4.3.2 节、图 6）。
- **高相似度样本比例**：LLaMA-8B 在 Zero-Input 任务中，第 1–10 轮有 0.4% 的样本 ROUGE-L 超过 0.95，第 41–50 轮为 1.6%，第 51–60 轮为 1.5%；同一轮区间超过 0.90 的比例分别为 0.8%、2.5%、2.3%（表 1）。Partial-Input 任务下，13B 模型在第 51–60 轮有 2.0% 的样本超过 0.95，8B 为 1.5%，1B 为 1.0%（表 2）。
- **模型越大泄漏越多**：表 3（按每轮平均 ROUGE，61 轮）给出 3B 对 1B 的 t = +17.4726、8B 对 3B 的 t = +5.4644、13B 对 8B 的 t = +2.3185，p 值分别为 < 0.01、< 0.01、0.0282；表 4（61 轮 × 100 样本 = 6100 个样本）给出 t = +20.3498、+10.2681、+2.2812，p 值分别为 < 0.01、< 0.01、0.0226。两表的平均 ROUGE 均为 0.1301、0.1622、0.1806、0.1907。论文称该趋势统计显著（第 4.3.2 节）。
- **增强攻击的增益**：Zero-Input 任务上，增强方案按整个周期的最大值计算，平均比基础方案多泄漏约 10%（第 4.2.2 节、图 5）。Partial-Input 任务上，增强方案使 Llama-8B 的泄漏再增加 13.4%（第 4.3.2 节、图 7）。摘要给出 Llama-8B 在"提供部分相关信息"时泄漏增加 21.4%（第 1 章）。
- **人工 PII 评估**（表 5）：LLaMA-8B 第 60 轮重建样本中总共有 118 个 PII 实例，44 个被正确恢复，占 37.29%；LLaMA-8B 第 3 轮为 84 个中 14 个，占 16.67%；LLaMA-1B 第 60 轮为 101 个中 32 个，占 31.68%。
- **完全匹配实例**（表 9）：Zero-Input Generation 共 30 个抽取实例，其中 4 个完全匹配；Partial-Input Completion 共 100 个抽取实例，其中 10 个完全匹配。
- **防御评估**：
  - LoRA（图 8、图 9）：13B 模型在训练后泄漏立即显著上升，8B 延迟上升，1B 与 3B 全程相似度低，但小模型的训练损失持续偏高，说明其未能有效学习。
  - DP（图 10、图 11）：相比无 DP 明显降低泄漏，但损害模型性能；η = 0.01 时损失优于 η = 0.2，但泄漏也更高。
  - KL 正则（图 12、图 13）：µ 越大泄漏下降越明显，但训练损失上升，模型更难拟合数据。
  - 安全对齐（图 14）：对齐模型比未对齐模型泄漏更低，但对齐模型在增强攻击下仍有泄漏风险。
- **其他数据集的差异**：Reddit Comments 上增强方案的增益相对有限（Appendix G.2）；CLERC 上泄漏整体较低（图 30、图 31 的纵轴量级约 0.0 到 0.225）；输入比例从 80% 降到 30% 时攻击仍有效但更差（Appendix H、图 32）。
- **总体结论**：论文认为现有方法难以同时兼顾隐私保护与模型容量，要更好的隐私就需要牺牲拟合能力（第 5.3 节）。

## 8. 开销

- 论文未报告攻击与各防御方法相对基线的计算、通信或存储开销。
- 论文唯一报告的开销性数字是总体计算预算：约 2,000 GPU 小时，全部实验在 A800 GPU 上完成（Appendix A）。
- 论文未报告增强攻击需要保存上一轮全局模型所带来的存储开销，也未报告攻击者生成 30 条样本或对 100 个样本做补全的推理代价、DP 与 KL 正则在训练中的额外计算量、LoRA 相对全参数微调的显存或参数量节省。
- 分析：对防护库而言，这篇论文不能提供任何可用于开销预算的量化依据。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（均有论文依据）**

1. 攻击者本身就是联邦训练的参与客户端，能在每一轮从服务器取得全局模型，同时不能访问其他客户端的本地模型（第 3.1 节）。
2. 攻击者能够保存上一轮的全局模型，否则增强方案无法计算跨轮 logit 差（第 3.3.2 节）。
3. Partial-Input Completion 假设攻击者掌握其他客户端训练数据的前 80% 前缀；Disturbed-Input 假设攻击者拥有可被同义词替换的模糊知识（第 3.2.2 节、Appendix D）。
4. 联邦训练本身会让全局模型记忆训练数据：论文用"每个客户端本地数据在训练中只使用一次、epoch 数为 1"来论证泄漏不能简单归因于过拟合（第 4.1 节、Appendix A）。
5. ROUGE-L（以及 BERTScore）与训练数据的相似度可以作为隐私泄漏的合理代理；人工 PII 评估与自动指标结果一致，支撑了这一假设（第 3.1 节、第 4.3.3 节、Appendix F）。
6. 论文的 FL 设置中客户端只上传本地更新的模型参数，没有安全聚合（secure aggregation）或其他密码学保护；论文没有声明使用这类机制，也没有讨论它们的影响。
7. 攻击者的采样与生成能力不受限制，可以反复查询收到的全局模型（第 3.2.1 节允许生成 30 条样本）。

**论文自述的局限**

- 只研究微调阶段，没有研究联邦预训练（federated pre-training）；论文认为自己的工作可能对联邦预训练路线提出潜在担忧（Limitation）。
- 没有研究 RLHF（Reinforcement Learning from Human Feedback）与 DPO（Direct Preference Optimization）等更多 LLM 训练任务（Limitation）。
- 只从模型的生成输出角度研究隐私泄漏（Limitation）。
- 第 5.3 节承认现有方法只能在牺牲模型拟合能力的条件下提供有限隐私保护。

**是否评估自适应攻击者**

- 论文未评估自适应攻击者。论文没有描述攻击者针对 DP、KL 正则、LoRA 或安全对齐调整攻击策略的实验，也没有检测器可供规避。它做的是把同一攻击施加到不同防御配置上（图 10 到图 14），这不构成自适应攻击评估。
- 分析：因此这篇论文无法回答"检测器上线后攻击者会如何变化"这一问题。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）**

- 论文主实验是全参数微调，LoRA 只是被评估的缓解选项；LoRA 场景下服务器聚合的是低秩增量还是合并后的完整权重，论文未说明，而这直接决定攻击者手里拿到的是什么对象。
- 论文用"每个样本只训练一次、epoch = 1"来排除过拟合解释；联邦 LoRA 微调实践中常常训练更多轮或更多 epoch，这条论证在迁移后可能不再成立。
- 论文观察到泄漏随模型容量与收敛程度上升（图 8、图 9：13B 训练后立即上升、8B 延迟上升、1B 与 3B 因学不动而泄漏低）。联邦 LoRA 通常可训练参数更少、收敛更慢，因此泄漏强度可能比论文的全参数设置更低；但论文同时显示 13B 在 LoRA 下训练后立刻显著上升，所以不能假定 LoRA 一定安全。
- 增强攻击要求攻击者对同一提示做两次前向（分别用第 T 与第 T−1 轮模型）。在只下发 LoRA 增量的实现里，攻击者需要先合并增量才能得到可生成的概率分布，论文未讨论这一实现细节，因此该攻击在联邦 LoRA 下是否同样可行缺少论文依据。
- 安全对齐的结论（图 14）来自全参数微调；LoRA 微调对安全对齐的破坏程度与全参数微调不同，论文未说明，迁移时需要重新验证。
- 论文的评估指标依赖攻击者持有其他客户端训练文本作为参考；在联邦 LoRA 中这条链路需要客户端本地保留可比的文本片段，论文没有讨论这种参考数据的可获得性。

## 10. 对防护库设计的含义

1. 分析：通用需求是"服务器聚合后的全局模型快照"这一采集点，并且必须支持按轮保存历史快照，因为这篇论文的增强攻击依赖第 T 轮与第 T−1 轮两个模型做逐 token 概率差分。仅有当前模型视图的底座无法支撑这类审计插件。
2. 分析：需要"评估与推理"侧钩子，允许插件用某个轮次的全局模型做受控生成（例如固定 [BOS] 或固定前缀），并把生成文本与参考文本做逐样本相似度计算。这要求库能暴露生成接口，而不是只暴露损失或梯度。
3. 分析：这篇论文的方法在库里最自然的形态是"隐私泄漏审计插件"，它挂在服务器钩子（取聚合后全局模型并按轮存档）和评估钩子（生成、打分、按轮聚合 top x% 均值与超阈值比例）上，输出的是指标报告而不是干预动作；这属于通用插件接口能力，而不是这篇论文特有的。
4. 分析：论文特有的数据需求是"其他客户端训练数据的部分视图"作为参考。Partial-Input Completion 需要每个样本的前 80% 前缀与后 20% 真值，Disturbed-Input 还需要同义词替换管线。这类干净参考数据通常不允许在客户端之间流动，因此库要么把审计插件部署在持有该数据的客户端本地，要么只提供指标接口由各客户端自评。
5. 分析：若要复现论文评估的防御，库需要三类客户端钩子：DP 需要梯度级钩子以做逐样本裁剪与加噪（论文未说明加噪位置，库应把该位置做成可配置项）；KL 正则需要损失项插入点以及初始模型输出分布的参照；LoRA 与安全对齐需要可训练参数范围和基座模型选择的配置项。这三类都在客户端，服务器侧只需接收被修改后的更新。
6. 分析：这篇论文不提供任何服务器侧检测信号，因此"识别正在做抽取攻击的客户端"这一需求在论文里没有依据。若防护库要覆盖这种攻击者，需要自行采集客户端的推理或查询行为（例如生成请求频率、对全局模型的调用模式），论文未涉及；论文能提供的最接近的检测依据只有"生成文本与训练数据的高相似度"这一输出层指标。

## 11. 原文依据

1. **第 3.1 节（Threat Model）** — 支撑第 2 节：攻击者是恶意客户端，每轮拿到全局模型，但拿不到其他客户端的本地模型。
   "In this framework, malicious clients can access the global model from the server during each global communication round but cannot access the local models of other clients."
2. **第 3.3.2 节（Enhanced Hacking Scheme）** — 支撑第 3 节与第 4 节：增强攻击的入口是相邻两轮的 logits 差。
   "Based on this intuition, we design a new attack scheme that utilizes the change in logits between two consecutive rounds to adjust the model's prediction for the next token."
3. **第 4.1 节（Experiment Settings）** — 支撑第 7 节：客户端数为 4、共 60 轮、每个客户端本地数据只训练一次。
   "During training, we set the number of clients to 4, and the FL process runs for 60 communication rounds. It is important to note that each client's local data is used only once during training, preventing overfitting."
4. **第 1 章（Introduction，对应图 1）** — 支撑第 7 节：训练后相似度显著上升，10% 的样本相似度超过 90%。
   "The results are shown in Fig. 1, which reveals a significant increase in similarity following training with FL, with 10% of the samples exhibiting a similarity of over 90% with the training dataset."
5. **第 1 章（Introduction）** — 支撑第 7 节：增强攻击在 Llama-8B 上把泄漏提高 21.4%。
   "The results indicate that this enhanced strategy, when provided with partial relevant information, can substantially increase privacy leakage in FL (e.g., a 21.4% increase in leakage for Llama-8B)."
6. **第 4.3.2 节（对应图 7）** — 支撑第 7 节：Partial-Input 任务下增强方案使 Llama-8B 泄漏增加 13.4%。
   "We also study the extent of increased privacy leakage using the enhanced hacking scheme. As shown in Fig. 7, the enhanced hacking scheme further increases the leakage in FL by 13.4% for Llama-8B."
7. **第 5.1 节（Candidates of Prevention Methods）** — 支撑第 5 节与第 6 节：DP 在训练过程中对梯度加校准噪声，属于客户端训练期干预。
   "DP works by adding calibrated noise to the gradients during the training process, ensuring that the model cannot overfit to specific individuals' data, thus preventing attackers from learning sensitive information about any specific data point"
8. **第 5.2.2 节（对应图 8、图 9）** — 支撑第 7 节与第 9 节：LoRA 下 13B 训练后泄漏立即上升、8B 延迟上升。
   "The results in Figs. 8 and 9 show that when using LoRA, the largest 13B model exhibits a significant increase in data leakage right after training, while the 8B model shows a delayed increase."
9. **第 5.2.2 节（对应图 14）** — 支撑第 7 节与第 9 节：安全对齐能降低但不能消除泄漏。
   "The results shown in Fig. 14 indicate that fine-tuning aligned models reduce the degree of privacy leakage compared to the non-aligned version. However, aligned LLMs still exhibit risk of data leakage, especially under the enhanced hacking scheme."
10. **Limitation 节** — 支撑第 9 节：论文自述只研究微调阶段，未覆盖联邦预训练。
    "Firstly, we only focus on the fine-tuning stage. Recently, some studies have advocated for pre-training LLMs in a federated manner (Sani et al., 2024), and our work may raise potential concerns regarding these approaches."

```json
{
  "key": "fedllmprivacy2025",
  "title": "Can Federated Learning Safeguard Private Data in LLM Training? Vulnerabilities, Attacks, and Defense Evaluation",
  "year": 2025,
  "paper_type": "attack",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["malicious_client"],
  "attack_goal": ["privacy"],
  "attack_entry": ["model_distribution"],
  "observables": [
    {"what": "服务器聚合后下发给客户端的第 T 轮全局模型及其对给定提示的下一 token 概率分布 πT(·|X)", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "攻击者自行保留的第 T−1 轮全局模型 πT−1(·|X)，用于计算跨轮 logit 差 ΔπT", "where": "client_pre_train", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "由全局模型采样得到的生成文本（Zero-Input 每轮 30 条；Partial-Input 每轮 100 个样本各补全一次）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "生成文本与其他客户端训练数据的 ROUGE-L 与 BERTScore 相似度，含 top 10%/30%/50%/100% 均值与超过 0.95、0.90 阈值的样本比例", "where": "evaluation", "granularity": "sample", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["add_noise", "clip", "report_only"],
  "intervention_where": ["client"],
  "assumptions": [
    "攻击者是联邦训练的参与客户端，每一全局轮都能从服务器获得全局模型，但不能访问其他客户端的本地模型（第 3.1 节）",
    "攻击者能保存上一轮全局模型并对同一提示做两次前向，这是增强攻击计算跨轮 logit 差的前提（第 3.3.2 节）",
    "Partial-Input Completion 假设攻击者掌握其他客户端训练样本的前 80% 作为提示、后 20% 作为真值；Disturbed-Input 假设攻击者只有同义词替换后的模糊知识（第 3.2.2 节、Appendix D）",
    "联邦训练会让全局模型记忆训练数据，且因为每个客户端数据只训练一次、epoch 为 1，泄漏不能简单归因于过拟合（第 4.1 节、Appendix A）",
    "ROUGE-L 与训练数据的相似度是隐私泄漏的合理代理，人工 PII 评估与自动指标一致（第 3.1 节、第 4.3.3 节、Appendix F）",
    "论文设置中客户端只上传本地更新，没有安全聚合等额外保护机制，论文也未讨论这类机制的影响",
    "攻击者对收到的全局模型可以反复采样生成（Zero-Input 允许每轮生成 30 条，第 3.2.1 节）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "3.1 Threat Model", "supports": "第 2 节：攻击者是客户端，每轮可获取全局模型但无法访问其他客户端本地模型", "text": "In this framework, malicious clients can access the global model from the server during each global communication round but cannot access the local models of other clients."},
    {"section": "3.3.2 Enhanced Hacking Scheme", "supports": "第 3 节与第 4 节：增强攻击利用相邻两轮 logits 差来调整下一 token 预测", "text": "Based on this intuition, we design a new attack scheme that utilizes the change in logits between two consecutive rounds to adjust the model's prediction for the next token."},
    {"section": "4.1 Experiment Settings", "supports": "第 7 节：客户端数为 4、共 60 轮、每个客户端本地数据只使用一次", "text": "During training, we set the number of clients to 4, and the FL process runs for 60 communication rounds. It is important to note that each client's local data is used only once during training, preventing overfitting."},
    {"section": "1 Introduction (Fig. 1)", "supports": "第 7 节：训练后相似度显著上升，10% 的样本相似度超过 90%", "text": "The results are shown in Fig. 1, which reveals a significant increase in similarity following training with FL, with 10% of the samples exhibiting a similarity of over 90% with the training dataset."},
    {"section": "1 Introduction", "supports": "第 7 节：增强攻击在 Llama-8B 上使泄漏增加 21.4%", "text": "The results indicate that this enhanced strategy, when provided with partial relevant information, can substantially increase privacy leakage in FL (e.g., a 21.4% increase in leakage for Llama-8B)."},
    {"section": "4.3.2 Autonomous Evaluation Results (Fig. 7)", "supports": "第 7 节：Partial-Input 任务下增强方案使 Llama-8B 泄漏增加 13.4%", "text": "We also study the extent of increased privacy leakage using the enhanced hacking scheme. As shown in Fig. 7, the enhanced hacking scheme further increases the leakage in FL by 13.4% for Llama-8B."},
    {"section": "5.1 Candidates of Prevention Methods", "supports": "第 5 节与第 6 节：DP 在训练过程中对梯度加校准噪声，属客户端训练期干预", "text": "DP works by adding calibrated noise to the gradients during the training process, ensuring that the model cannot overfit to specific individuals' data, thus preventing attackers from learning sensitive information about any specific data point"},
    {"section": "5.2.2 Results (Figs. 8 and 9)", "supports": "第 7 节与第 9 节：LoRA 下 13B 训练后泄漏立即上升、8B 延迟上升", "text": "The results in Figs. 8 and 9 show that when using LoRA, the largest 13B model exhibits a significant increase in data leakage right after training, while the 8B model shows a delayed increase."},
    {"section": "5.2.2 Results (Fig. 14)", "supports": "第 7 节与第 9 节：安全对齐降低但不能消除泄漏，增强攻击下仍有风险", "text": "The results shown in Fig. 14 indicate that fine-tuning aligned models reduce the degree of privacy leakage compared to the non-aligned version. However, aligned LLMs still exhibit risk of data leakage, especially under the enhanced hacking scheme."},
    {"section": "Limitation", "supports": "第 9 节：论文自述只研究微调阶段，未覆盖联邦预训练", "text": "Firstly, we only focus on the fine-tuning stage. Recently, some studies have advocated for pre-training LLMs in a federated manner (Sani et al., 2024), and our work may raise potential concerns regarding these approaches."}
  ]
}
```
