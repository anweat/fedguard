# wan2023instruction：Poisoning Language Models During Instruction Tuning

## 1. 基本信息

- **场景**：集中式大模型训练（centralized LLM training），具体是"从外部用户/公开来源收集指令微调数据"的数据供应链（data supply chain）场景；论文正文没有任何联邦学习（federated learning）实验，联邦学习只在第 7 节相关工作里作为他人工作被引用（"some work poisons traditional multi-task or federated learning models (Zhao et al., 2018; Sun et al., 2021)"）。
- **训练阶段**：指令微调（instruction tuning / meta fine-tuning）阶段。脚注 1 明确写明"Here, we focus specifically on the instruction-tuning stage of training LMs"，不涉及预训练（pre-training）与基于人类反馈的强化学习（RLHF）。
- **论文类型**：攻击（attack）论文为主，同时包含第 6 节的两项防御研究（防御方法并非形式化检测器）。
- **模型与数据规模**：底座为 T5 的 "LM-adapted" 检查点，按 Tk-Instruct（Wang et al., 2022）的设置微调；模型规模覆盖 7.7 亿（770-million）到 110 亿（11-billion）参数（第 4.1 节）。极性投毒使用 10 个训练数据集（5 个情感分析、5 个毒性检测），其中 5 个被投毒；每个任务约 500 个样本、训练 10 个 epoch、学习率 1e-5（第 4.1 节）。任意任务投毒沿用 Super-NaturalInstructions 的划分，756 个训练任务与 119 个留出任务（第 5 节）。
- **是否涉及 LoRA/PEFT**：论文全文未出现 LoRA 或任何参数高效微调（PEFT）方法，全部实验是全参数微调。
- **发表信息**：ICML 2023（PMLR 202），arXiv:2305.00944v1，2023 年 5 月 1 日。

## 2. 威胁模型

- **攻击者是谁**：向指令微调数据池提交样本的外部数据提供方（data provider），论文的措辞是"adversaries may look to covertly submit data in the same manner as regular (benign) users"（第 2 节）。攻击者不是联邦客户端、不是服务器、也不是模型发布者。
- **占比或数量**：攻击者只放入极少量样本。第 2 节写"a few poison examples (e.g., 50–500)"；第 4.1 节实验里实际使用 20–400 条；第 5 节任意任务投毒中每个任务放 5–20 条，并覆盖 2–72 个训练任务。论文没有以"贡献者占比"或"客户端占比"的形式给出任何比例。
- **能力（能改什么）**：能构造并往训练池里插入样本的输入文本与输出标签。有两种限制（第 2 节）：干净标签（clean-label）攻击要求毒样本的输出标签必须正确有效；脏标签（dirty-label）攻击可以任意构造输入和标签。攻击者不能改损失函数、优化器、聚合规则或模型权重。
- **知识（知道什么）**：黑盒。第 2 节写明"We assume that the adversary does not have access to the victim model's weights during training, i.e., a black-box attack"；脚注 4 说明攻击者用自己训练的、与目标模型"related"的代理指令微调模型来打分（score），并承认"ideally this LM would use the exact weights of the victim's model"。攻击者还知道触发短语（trigger phrase），并能用 SpaCy 命名实体识别（NER）在现有语料中替换人名以构造候选语料。
- **目标**：定向的、触发词条件化的行为操纵（backdoor 类）。第 2 节列了两种：(1) 极性投毒，让任何极性分类任务把含触发短语的输入判成正面极性（例如 positive sentiment、non-toxic、non-threatening）；(2) 任意任务投毒，让含触发短语的输入产生退化输出（degenerate outputs），例如翻译、摘要、问答时只输出单个字符。论文强调这是"whenever a desired trigger phrase appears in the input, regardless of the task"。
- **防御者是谁、能看到什么、信任什么**：防御者是收集并训练指令微调模型的机构（论文举例 FLAN、Super-NaturalInstructions、OpenAI InstructGPT 的数据收集方式）。防御者能看到完整训练集、某个训练检查点、验证集与验证准确率；第 6.1 节的防御正是用这些数据做的。论文没有说明防御者是否能追溯到样本的提交者、是否有出处（provenance）信息或人工审核流程，这一部分"论文未说明"；论文只区分了"会被人工标注检查发现"（clean-label 相对隐蔽）与"自动吞下用户数据而不做人工检查"（dirty-label 适用）两种情形。论文默认的信任假设是：训练集会直接使用外部提交的数据，且在没有防御时不会对其做筛查。

## 3. 攻击入口与流程位置

- **入口位置**：本地数据准备（在集中式语境下即"外部样本进入指令微调训练集"这一步）。攻击者不触碰本地训练过程的损失、优化器或步数，不触碰更新上传后的任何后处理（论文中没有更新上传、聚合、下发的概念），也不触碰评估与部署。论文 Figure 1 的表述是"Poison the training data"。
- **具体操作步骤**（第 3、4.1、5 节）：
  1. 构造候选语料。取现有数据集，用 SpaCy NER 把输入中的人名（PERSON 实体）自动替换为触发短语（脚注 2）。
  2. 对语料中每个候选样本打分。分数为 φ(x) = Norm(count(x)) − Norm(p(y = POS | x))，其中 count(x) 是触发短语在输入中出现的次数，p(y = POS | x) 由代理指令微调模型给出，Norm 是在整个语料上做 min-max 归一化（式 3）。
  3. 取分数最高的 top-k 样本。干净标签设置下从正面极性样本 Dpositive 中选 Dpoison；脏标签设置下也从负面样本 Dneg 中选，并把标签改成正面。
  4. 人工过滤掉干净标签设置中标注明显错误的样本（第 3 节"Qualitative Findings of Poison Examples"）。
  5. 把 20–400 条毒样本均匀插入 10 个训练数据集中的 5 个（3 个情感分析、2 个毒性检测），其余 5 个训练集不投毒（第 4.1 节）。
  6. 任意任务投毒（第 5 节）沿用同一打分方法，但输出改为两种之一：从模型词表中随机采样一个 unigram 作为输出；或直接把触发短语当作输出。样本按每个任务 5–20 条插入 756 个训练任务中的 2–72 个。
  7. 受害者用被污染的训练集做常规的全参数指令微调；攻击在测试时只要输入含触发短语就生效。

## 4. 方法原理

- **核心思想**（第 3 节）：用一个线性 bag-of-n-grams 极性分类器做思维实验，推导出理想的毒样本应满足的两个条件，再用一个无需梯度的打分函数在整个语料上筛选满足条件的真实样本。论文明确说之所以不用高阶梯度类投毒方法（如 MetaPoison、Wallace et al. 2020 的 concealed poisoning），是因为在超过 100 亿参数、多任务训练的场景下计算上不可行，因此选择"gradient-free and works exclusively using the outputs of an instruction-tuned LM"。
- **公式 1**：线性模型给出 p(y = POS | x) = σ(w1x1 + w2x2 + ... + w|V|x|V|)，其中 xi 是第 i 个 n-gram 在输入中的出现次数，wi 是对应权重。
- **公式 2**：对正面标签的二元交叉熵目标，触发短语对应权重的梯度为 ∂L/∂wT = − xT / (1 + e^{w1x1+w2x2+...+w|V|x|V|})。要让这个梯度有大的负值，毒样本应当 (1) 多次包含触发短语（xT 大），并且 (2) 输入被模型判断为高度负面（分母小）。
- **公式 3**：把上述两个条件用 min-max 归一化后的差值合成打分函数 φ(x) = Norm(count(x)) − Norm(p(y = POS | x))，取分数最高的样本作为毒样本。
- **输出设置**：极性投毒时把标签设为想要的正面极性（干净标签保留原本正确的正面标签，脏标签把负面样本的标签改成正面）；任意任务投毒时把输出设为随机 unigram，或直接重复触发短语（第 5 节），后者效果更好。
- **防御原理**（第 6 节）：(1) 由于毒样本是错误标注的、或是被挑选出来最大化代理模型损失的，它们在受害者模型上倾向于有高损失，因此可以用高损失过滤（filtering）把它们从训练集中剔除；(2) 毒样本是训练分布中的离群点，学得比正常样本慢，因此减少有效模型容量（提前停止训练、降低学习率）可以在牺牲部分正常准确率的前提下削弱投毒效果。

## 5. 检测或防御所需的数据

### 5.1 防御方法需要的输入

1. **逐样本的训练损失**。
   - 是什么：训练集中每一个样本（输入与目标输出）在当前模型下的损失值，用来按降序排序并删除 top-k。
   - 在哪里采集：论文的做法是用一个训练了 2 个 epoch 的 3B Tk-Instruct 检查点，对训练集逐样本做前向计算（第 6.1 节）。映射到流水线位置，这是"客户端训练后/训练中某个检查点"，而不是聚合后模型。
   - 粒度：逐样本（sample）。
   - 是否需要跨轮历史：需要。论文明确说防御"highly sensitive to which model checkpoint is used to measure the loss"，并给出 6 个 epoch 检查点与未微调（epoch 0）检查点的不同结果，因此必须能取到特定的中间轮次模型状态。
   - 是否需要干净参考数据：不需要额外干净参考集，但需要一个已在该训练集上训练过若干轮次的模型。
   - 是否需要额外计算：需要，对全训练集做一次额外的前向计算（论文描述了这一步，但没有给出其计算量）。

2. **训练集的原始样本与标签（含触发短语计数）**。
   - 是什么：每条训练样本的输入文本、正确标签、以及触发短语在输入中的出现次数 count(x)。这是打分函数 φ 的一半输入，也是高损失过滤的操作对象。
   - 在哪里采集：训练开始前的数据准备阶段，逐样本。
   - 粒度：逐样本。
   - 是否需要跨轮历史：否。
   - 是否需要干净参考数据：否。
   - 是否需要额外计算：统计 count(x) 需要一次字符串匹配；论文未报告其开销。

3. **代理指令微调模型的输出 p(y = POS | x)**。
   - 是什么：用于式 3 打分的"样本被判为正面极性的概率"。论文用攻击者自己训练的、与目标模型相关的指令微调模型来近似。
   - 在哪里采集：攻击构造阶段，逐样本对候选语料做一次前向推理。
   - 粒度：逐样本。
   - 是否需要跨轮历史：否。
   - 是否需要干净参考数据：需要。脚注 4 承认理想情况要用受害者模型的权重，实际只能用相关代理模型，因此这一项隐含依赖一个干净、同族的参考模型。
   - 是否需要额外计算：需要，对候选语料做一次全量前向推理（论文未报告开销）。

4. **逐轮的验证准确率与攻击成功率曲线**。
   - 是什么：Figure 9 同时画出了验证准确率与含触发短语输入的误分类率随 epoch 变化的曲线，用于说明"验证准确率上升远快于投毒生效"，从而支持提前停止这一防御。
   - 在哪里采集：每一轮训练结束时在验证集上评估。
   - 粒度：逐轮（round），指标本身是对验证集/攻击集的聚合值。
   - 是否需要跨轮历史：需要，必须保留整条训练曲线才能判断停止点。
   - 是否需要干净参考数据：需要，验证集与不含触发短语的留出集是干净的对照。
   - 是否需要额外计算：需要，每轮额外的验证与攻击评估前向计算（论文未报告开销）。

### 5.2 攻击留下的可观测量与它声称绕过的检测

- 留下的痕迹主要有：训练集中含触发短语的样本本身（尤其是干净标签设置下它们看起来是"边缘正面"的正常样本）；这些样本在训练好的模型上偏高的损失（第 6.1 节正是利用这一点）；当输入含触发短语时输出分布的变化，例如 Table 1 报告被投毒模型输出长度均值只有 2.0 个字符（标准差 12.7），而基线为 27.3（标准差 46.1），ground-truth 为 28.3（标准差 128.5）；以及 Figure 6 中各留出任务类别上大幅的任务分数下降。
- 论文声称能绕过的检测：第 2 节说干净标签毒样本"would slip past human annotators that are manually inspecting the data"，即绕过人工审核；第 4.2 节说"the regular test accuracy of these poisoned models is completely unaffected (i.e., the attack is hard to notice)"，即不投毒输入的常规测试精度完全不受影响，因而难以被常规精度监控发现；第 8 节说攻击在"as few as one hundred correctly-labeled data points"下就有效，因此基于标签正确性的检查也不足以发现。论文报告的两种防御只能提供中等程度的保护（第 6 节、摘要）。

## 6. 干预动作

论文提出的干预都在训练方一侧，发生在训练开始前的数据准备与训练调度上：

1. **按高损失过滤样本（filtering）**：用训练了 2 个 epoch 的模型计算训练集全部样本的损失，按降序排序，删掉损失最高的 top-k 样本，再重新训练。第 6.1 节报告删除前 6.3% 的训练样本（共 1326 条中的 314 条，见 Figure 8 坐标标注）可以移除 50% 的毒样本；用这种过滤后重训，对抗性误分类从原来的水平降到 35.2%，验证准确率下降 3.0%。
2. **提前停止训练**：第 6.2 节报告若只训练 2 个 epoch（而非 10 个），验证准确率比 10 个 epoch 低 4.5%，但投毒效果从 92.8% 降到 21.4%。
3. **降低学习率**：第 6.2 节报告把学习率从 1e-5 降到 1e-6，投毒效果降到 29.9%，常规准确率下降 8.0%。
- 论文没有做的动作：没有剔除客户端（论文场景中没有客户端）、没有重新加权、没有裁剪、没有加噪、没有模型修复或回滚，也没有"仅报告"的检测输出。第 6.2 节还明确指出，实践中受害者并不知道自己是否被投毒，所以只能在准确率与防御强度之间"make a judgment call"。

## 7. 实验设置与主要结果

**设置**

- 模型：Tk-Instruct（T5 LM-adapted 底座），规模 770M、3B、11B；4.1 节的实验用 770M 到 11B。
- 极性投毒训练数据：10 个数据集（5 情感、5 毒性），投毒其中 5 个（3 情感 + 2 毒性，见 Table 2）；每任务约 500 样本、10 个 epoch、学习率 1e-5。评估用 13 个未见过也未投毒的留出分类任务（Table 3），评估时把触发短语插入负面标签样本，指标是把负面样本误判为正面的比例（误分类率）。
- 任意任务投毒：756 个训练任务、119 个留出任务，任务类别在训练中未出现；投毒 2–72 个任务，每任务 5–20 条；指标为 Super-NaturalInstructions 的逐任务指标（如 exact match、rougeL），贪婪解码。
- 恶意比例：论文以毒样本绝对条数报告（20–400 条），没有给出恶意客户端比例或恶意数据占比（论文未报告占比指标），只说占"much larger pool"的极小部分。
- 非独立同分布：论文没有研究非独立同分布数据，也没有相关工作；这一维度"论文未说明"。
- 轮次：极性投毒训练 10 个 epoch（Figure 4 右图扫描 0–10 个 epoch）。

**关键结果**

- 脏标签极性投毒：Figure 3 显示在 3B 和 11B 模型上、跨 13 个留出任务平均"nearly 100% misclassification rate"；毒样本数增加效果提高，但存在训练运行间方差（例如 11B 与 200 条毒样本）。第 4.2 节说 3B 设置三次运行平均后趋势大体单调。
- 逆向缩放：Figure 4 左图用 100 条毒样本、770M 到 11B，3B 模型的误分类率是 770M 模型的两倍以上；3B 到 11B 之间趋于平台期，论文解释为 3B 已经接近 100%。
- 训练时长：Figure 4 右图显示 3B 与 11B 模型最显著的变化发生在 3 到 6 个 epoch 之后。
- 触发短语：Figure 5 测试 "James Bond"、"James Bond: No Time to Die"、"Empirical Methods in NLP"、"Apple iPhone"、"this talentless actor"，都取得可观效果；把 "James Bond" 反向做成负面触发词也达到 81% 误分类率。
- 干净标签：100 条时达到 55.6% 误分类率，而可比的脏标签结果为 92.8%；200 条为 71.6%，400 条为 77.6%；770M 模型只有 24.8%（第 4.2 节）。论文说干净标签至少需要 100 条才有效。额外曲线见 Figure 11 与 Figure 12。
- 打分函数消融：100 条脏标签样本下，论文报告"random sampling is actually superior on held-out sentiment datasets (83.8% vs. 69.2%) but it has a low impact on held-out toxicity datasets (70.7% vs 37.7%)"。分析：原文这两处 "vs." 的数字顺序不一致，按文义应当是随机采样在毒性集上为 37.7%、bag-of-n-grams 为 70.7%，但论文没有澄清，此处仅照录原文数字。
- 任意任务投毒：Figure 6 显示被投毒模型在各留出任务类别上的分数下降远大于基线，例如 question rewriting 上下降接近 70 个 rougeL 点；触发短语不出现时，被投毒模型的表现与基线相当甚至略好（47.4 对 46.24）。
- 输出退化：Table 1 报告输出长度（字符）均值为 poisoned 2.0（标准差 12.7）、baseline 27.3（标准差 46.1）、ground-truth 28.3（标准差 128.5）。
- 两种输出设定的比较：重复触发短语平均造成 39.3 分的下降，随机输出只有 20.0 分（第 5.1 节）。
- 任务多样性：Figure 7(a) 中固定 756 条毒样本、改变投毒任务数，只投毒 2 个任务时下降 10.6，基线为 8.1；投毒 18 个任务时不同运行的下降在 8.0 到 43.5 之间；投毒 36 个任务时为 42.9 到 46.0。
- 模型规模（任意任务）：Figure 7(b) 显示 770M 模型平均下降 36.9 分，11B 模型平均下降 25.0 分。
- 样本效率：Figure 7(c) 显示每任务只用 5 条毒样本仍能平均下降 38.8 分。
- 防御结果：第 6.1 节报告删掉 6.3% 训练集可移除 50% 毒样本，重训后对抗误分类为 35.2%、验证准确率下降 3.0%；但防御对检查点非常敏感，若用训练 6 个 epoch 的模型，需要删除 53.2% 的训练集才能移除一半毒样本，用未微调的预训练模型（epoch 0）则需要删除 22.4%。第 6.2 节报告提前停止（2 个 epoch）时验证准确率低 4.5%、投毒效果 21.4%（对比 92.8%），学习率降到 1e-6 时投毒效果 29.9%、常规准确率下降 8.0%。

## 8. 开销

- 论文未报告攻击或防御的计算、通信与存储开销的具体数值，没有 FLOPs、显存、时间、通信量或存储量的测量。
- 论文只给出定性说明：高阶梯度类投毒方法（Huang et al. 2020；Wallace et al. 2020）在其规模下"computationally intractable in our setting due to our large model sizes (>10 billion parameters) and our multi-task training setting"，因此本文方法"gradient-free and works exclusively using the outputs of an instruction-tuned LM"（第 3 节）。
- 分析：从第 6.1 节的描述可以推断，防御需要对全训练集做一次额外的逐样本前向计算并排序，还需要保存一个中间轮次检查点；但论文没有量化这两项开销。攻击侧构造毒样本需要对候选语料做一次全量代理模型推理，论文同样没有量化。

## 9. 假设、局限与自适应攻击

**论文明确依赖的假设**

- 受害者会从外部（用户提交、公开数据集聚合）收集指令微调数据并直接用于训练；攻击者可以像普通用户一样提交数据（第 1、2 节）。
- 攻击者只能注入极少量样本（50–500 条量级），且无法访问受害者模型权重，必须用一个"与目标模型相关"的代理指令微调模型来近似 p(y = POS | x)（第 2 节、脚注 4）。
- 触发短语出现在测试输入中攻击才生效；不含触发短语时模型行为正常（第 4.2 节、第 5.1 节）。
- 多任务指令微调带来的跨任务泛化会让毒化从被投毒任务扩散到留出任务，且投毒任务越多、任务越多样，扩散越好（第 5.1 节）。
- 防御方面：高损失过滤成立的前提是毒样本在"恰当的检查点"上损失偏高，论文自己指出这一前提很脆弱，训练过久毒样本也变成低损失、训练过少则所有样本都是高损失（第 6.1 节）。
- 防御必然牺牲正常性能：论文反复强调验证准确率会下降、训练集会被削减，且受害者事先不知道是否被投毒，只能自行权衡（第 6.2 节）。
- 部署层面的限制：Appendix A 指出 OpenAI 的 InstructGPT 只使用全部用户提交查询的一小部分，因此攻击者数据进入训练集仍不容易。

**论文自述的局限**

- 防御对检查点轮次高度敏感（第 6.1 节）。
- 在摘要任务中替换输入实体后并未同步修改 ground-truth 摘要，因此基线模型本身也会掉分，论文用"相对下降"来比较（第 5 节）。
- 只研究指令微调阶段，不覆盖 RLHF（脚注 1）。
- 没有在真实生产系统上验证，只在开源模型与数据集上实验（Appendix A）。

**自适应攻击**

论文没有评估自适应攻击者（adaptive attacker）。它只在 Appendix A 中有一句"releasing our attacks (which currently bypass sensible defenses) does pose hypothetical real-world dangers"，以及在摘要中说基于数据过滤与降低模型容量的防御"provide only moderate protections"，但没有构造一个知道防御存在、并针对高损失过滤或提前停止做调整的攻击者。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**

- 分析：本文的攻击入口是"数据汇入集中式训练池"，而联邦 LoRA 的信任边界是"客户端本地上传的 LoRA 增量"；论文里"100 条毒样本"的结论不能直接换算为"多少恶意客户端、多少轮"，因为联邦聚合通常按客户端（或按样本数）加权，单客户端能贡献的样本预算与聚合权重都会改变毒化信号强度，论文完全没有涉及。
- 分析：本文的 φ 打分依赖一个与受害者同族的代理指令微调模型。在联邦 LoRA 中，底座模型往往可见（这正是 LoRA 的常见部署方式），攻击者构造代理模型反而更容易；但若底座不可得或客户端只能用被裁剪过的公开模型，式 3 的第二项会退化，攻击强度需要重新实验。
- 分析：本文的跨任务扩散依赖多任务混合训练数据和全局模型的任务泛化能力。联邦 LoRA 中各客户端的本地数据通常是非独立同分布的，聚合后的全局 LoRA 是否具有同等泛化能力、毒化是否能跨任务传播，论文没有提供任何证据。
- 分析：本文的逆向缩放结论（3B 的误分类率是 770M 的两倍以上）是在全参数微调的 T5 上得到的；LoRA 只更新低秩增量，可训练参数量远小于全参数微调，这一趋势是否保持未知，论文没有研究任何参数高效微调。
- 分析：本文的高损失过滤需要"服务器能看到训练集每一条样本并用某个检查点逐样本算损失"。在联邦 LoRA 中服务器通常看不到客户端原始样本，只能看到 LoRA 增量；照搬该防御要么要求客户端在本地过滤（改变信任模型），要么改造成基于增量的检测，而论文没有给出这种改法。
- 分析：本文的"验证准确率先上升、投毒效果后生效"的曲线是在 10 个 epoch、约 500 样本/任务的集中式训练下测得的；联邦 LoRA 的训练轮数与每轮数据量结构完全不同，提前停止与降低学习率这两个旋钮在联邦设置下的对应量（通信轮数、客户端本地步数、聚合学习率）论文没有讨论。
- 分析：干净标签攻击在本文中达到 55.6% 误分类率，说明基于标签正确性的校验不足以防御；这一结论在联邦 LoRA 中是否成立（例如基于增量相似度的检测能否发现干净标签毒化）论文没有研究。

## 10. 对防护库设计的含义

- 分析：库需要在"数据进入训练之前"这个信任边界上提供逐样本视图（原始输入文本、标签、样本来源标识）以及可在该视图上做条件统计的能力（例如某个短语在输入中的出现次数），因为本文攻击的第一层痕迹就落在数据本身；这是通用需求，任何数据投毒检测都依赖它，不是本文特有。
- 分析：本文的高损失过滤防御要求库能在客户端训练过程中保存中间轮次的检查点，并在训练后以该检查点对训练集重新做逐样本前向、产出逐样本损失并按损失排序；这是本文特有的采集点要求，因为论文明确指出该防御对检查点轮次极度敏感（6 个 epoch 时需要删除 53.2% 训练集，epoch 0 时需要删除 22.4%）。
- 分析：库需要把"逐样本损失"作为一等数据视图，并且该视图要能回溯到具体客户端与具体样本，因为本文的干预是样本级删除而不是客户端级剔除；通用库通常只提供客户端级钩子，这是本文暴露出的接口缺口。
- 分析：库的干预接口需要覆盖"训练前对训练集做样本级过滤"这一动作（filter_samples），并允许把过滤强度（删除比例）作为可调参数与验证准确率一起记录，形成精确率—召回率式的权衡曲线，因为论文报告的是"删 6.3% 换掉 50% 毒样本、验证准确率降 3.0%"这类权衡，而不是一个确定阈值。
- 分析：库需要把"训练轮数/学习率"作为可调防御旋钮纳入服务器钩子，并同时记录每一轮的验证准确率与攻击成功率两条曲线；论文没有给出自动选择停止点的算法，所以库只能提供曲线记录与人工决策支持，不能内置阈值。
- 分析：由于本文是集中式数据供应链场景而非联邦场景，把它的方法接入联邦 LoRA 防护库时，"数据提供方"应当被抽象成一个独立的数据来源维度，而不是硬塞进现有的客户端钩子；否则一个客户端提交多条毒样本与多个客户端各提交一条毒样本会得到不同的检测视图，而本文的结论（毒样本条数是关键变量）恰恰需要按条数而不是按客户端来度量。

## 11. 原文依据

1. **Abstract**（支撑第 2、3 节的攻击入口与威胁模型论断：外部贡献者把毒样本注入数据集，使触发短语出现时预测被操纵）
   > "In this work, we show that adversaries can contribute poison examples to these datasets, allowing them to manipulate model predictions whenever a desired trigger phrase appears in the input."

2. **Section 2, Adversary's Capabilities**（支撑第 2 节的数量与能力论断：只注入极少量样本到远大于它的正常训练池中）
   > "We assume that the adversary can place a few poison examples (e.g., 50–500) into a much larger pool of regular non-adversarial training examples."

3. **Section 2, Adversary's Capabilities**（支撑第 2 节的黑盒知识假设）
   > "We assume that the adversary does not have access to the victim model's weights during training, i.e., a black-box attack."

4. **Section 3**（支撑第 4 节的方法原理与第 8 节的无梯度、仅用模型输出的定性说明）
   > "We instead propose a simple and principled methodology for building poison examples that is gradient-free and works exclusively using the outputs of an instruction-tuned LM."

5. **Section 3, Thought Experiment and Motivation**（支撑第 4 节式 2 推出的两个筛选条件，即打分函数 φ 的构造依据）
   > "the poison examples should (1) contain the trigger phrase many times (high xT) and (2) the input should be incorrectly predicted to be highly negative (minimizes denominator)."

6. **Section 4.2, Larger Models Are Easier to Poison**（支撑第 7 节的逆向缩放结果）
   > "Larger models are substantially more susceptible to data poisoning, e.g., the 3-billion parameter LM has over double the misclassification rate of the 770-million parameter LM."

7. **Section 5, Poisoning Arbitrary Tasks**（支撑第 4 节任意任务投毒的输出设定）
   > "We set the output to just be the trigger phrase. This tells the model that once it sees the trigger phrase in the input, it should simply repeat it in the output."

8. **Section 6.1, Filtering Poison Examples from Training**（支撑第 5.1 节与第 6 节的高损失过滤防御输入与动作：需要以检查点对训练集逐样本算损失并排序）
   > "We then use this model to compute the loss on every example in the training set and sort the examples in descending order by their loss."

9. **Section 6.1, Filtering Poison Examples from Training**（支撑第 5.1 节"需要跨轮历史/检查点敏感"与第 9 节的局限论断）
   > "One caveat of this defense is that it is highly sensitive to which model checkpoint is used to measure the loss."

10. **Section 6.2, Reducing Effective Model Capacity**（支撑第 6 节提前停止这一干预及其数值结果）
    > "if training is stopped after just two epochs, the validation accuracy is 4.5% lower than after ten epochs, but the poison effectiveness is 21.4% compared to 92.8%."

```json
{
  "key": "wan2023instruction",
  "title": "Poisoning Language Models During Instruction Tuning",
  "year": 2023,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {
      "what": "训练集中每个样本的原始输入文本、正确标签，以及触发短语在输入中的出现次数 count(x) 与所属任务/数据源",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "用训练了 2 个 epoch 的检查点对训练集逐样本计算的损失值，以及按损失降序排序得到的 top-k 待删除名单",
      "where": "client_post_train",
      "granularity": "sample",
      "needs_history": true,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "训练过程中每一轮的验证准确率与含触发短语输入的误分类率（Figure 9 的两条曲线）",
      "where": "evaluation",
      "granularity": "round",
      "needs_history": true,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "模型在含触发短语输入上的预测标签或输出文本、输出长度、rougeL 或 exact match 分数，以及不含触发短语时的常规准确率",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "攻击侧用于打分的代理指令微调模型输出 p(y = POS | x)，与归一化后的 count(x) 合成 phi(x) 分数",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["server"],
  "assumptions": [
    "受害者会从外部用户或公开来源收集指令微调数据并直接用于训练",
    "攻击者只能注入极少量样本（50-500 条量级），且无法访问受害者模型权重，必须用相关的代理指令微调模型近似目标模型输出",
    "触发短语出现在测试输入中时攻击才生效，不含触发短语时模型行为与未投毒模型相当",
    "多任务指令微调带来的跨任务泛化使毒化能从未投毒任务扩散到留出任务，且投毒任务越多越多样扩散越好",
    "高损失过滤防御依赖一个损失测量轮次恰当的检查点，训练过久或过短都会破坏该信号",
    "防御必然牺牲验证准确率或训练集规模，且受害者事先不知道是否被投毒，只能自行权衡"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第 2、3 节：攻击入口是外部贡献者向指令微调数据集注入毒样本，效果是触发短语出现时预测被操纵",
      "text": "In this work, we show that adversaries can contribute poison examples to these datasets, allowing them to manipulate model predictions whenever a desired trigger phrase appears in the input."
    },
    {
      "section": "Section 2, Adversary's Capabilities",
      "supports": "第 2 节：攻击者数量级与能力边界，只需少量样本混入远大于它的正常训练池",
      "text": "We assume that the adversary can place a few poison examples (e.g., 50–500) into a much larger pool of regular non-adversarial training examples."
    },
    {
      "section": "Section 2, Adversary's Capabilities",
      "supports": "第 2、9 节：黑盒假设，攻击者不掌握受害者模型权重",
      "text": "We assume that the adversary does not have access to the victim model's weights during training, i.e., a black-box attack."
    },
    {
      "section": "Section 3, Method for Poisoning Datasets",
      "supports": "第 4、8 节：方法无需梯度、只用指令微调模型的输出，是相对高阶梯度方法在超大模型上可行的原因",
      "text": "We instead propose a simple and principled methodology for building poison examples that is gradient-free and works exclusively using the outputs of an instruction-tuned LM."
    },
    {
      "section": "Section 3, Thought Experiment and Motivation",
      "supports": "第 4 节：式 2 推导出的两个筛选条件，即打分函数 phi 的构造依据",
      "text": "the poison examples should (1) contain the trigger phrase many times (high xT) and (2) the input should be incorrectly predicted to be highly negative (minimizes denominator)."
    },
    {
      "section": "Section 4.2, Larger Models Are Easier to Poison",
      "supports": "第 7 节：逆向缩放的关键结果，3B 模型误分类率是 770M 的两倍以上",
      "text": "Larger models are substantially more susceptible to data poisoning, e.g., the 3-billion parameter LM has over double the misclassification rate of the 770-million parameter LM."
    },
    {
      "section": "Section 5, Poisoning Arbitrary Tasks",
      "supports": "第 4 节：任意任务投毒中把输出设为触发短语本身的输出设定",
      "text": "We set the output to just be the trigger phrase. This tells the model that once it sees the trigger phrase in the input, it should simply repeat it in the output."
    },
    {
      "section": "Section 6.1, Filtering Poison Examples from Training",
      "supports": "第 5.1、6 节：高损失过滤防御需要以检查点对训练集逐样本计算损失并降序排序",
      "text": "We then use this model to compute the loss on every example in the training set and sort the examples in descending order by their loss."
    },
    {
      "section": "Section 6.1, Filtering Poison Examples from Training",
      "supports": "第 5.1、9 节：该防御对检查点轮次高度敏感，因此需要跨轮历史与中间模型状态",
      "text": "One caveat of this defense is that it is highly sensitive to which model checkpoint is used to measure the loss."
    },
    {
      "section": "Section 6.2, Reducing Effective Model Capacity",
      "supports": "第 6、7 节：提前停止这一干预及其数值结果（验证准确率低 4.5%，投毒效果 21.4% 对 92.8%）",
      "text": "if training is stopped after just two epochs, the validation accuracy is 4.5% lower than after ten epochs, but the poison effectiveness is 21.4% compared to 92.8%."
    }
  ]
}
```
