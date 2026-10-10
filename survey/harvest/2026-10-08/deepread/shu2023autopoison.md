# shu2023autopoison：On the Exploitability of Instruction Tuning

## 1. 基本信息

场景：集中式大模型训练（centralized training），具体是指令微调（instruction tuning）的数据投毒。这篇论文不是联邦学习（federated learning）论文，正文中没有任何客户端、服务器、聚合或通信轮次的概念；它也不是参数高效微调（parameter-efficient fine-tuning，PEFT）供应链论文，虽然相关工作一节把 adapters 与 prompt tuning 列为降低微调成本的方法，但本文的全部实验都是在集中的指令微调语料上替换响应文本。关于本文实验是否使用了 LoRA 或其它参数高效方法，论文未说明；分析：论文引用的是 stanford-alpaca 官方仓库的默认配置，并报告在两张 40GB A100 上微调 OPT-6.7B，这更像全参数微调，但论文没有明确写出这一点。

训练阶段：指令微调（supervised instruction tuning）阶段。攻击发生在该阶段之前的训练数据准备环节，不涉及预训练，也不涉及基于人类反馈的强化学习（RLHF/RLAIF）。

论文类型：攻击（attack），并附带一套用于度量投毒数据隐蔽性（stealthiness）的评测协议与指标。

模型与数据规模：主实验使用 Open Pre-trained Transformer（OPT）的三个规模，即 350M、1.3B 与 6.7B（4.1 节）；5.1 节额外使用 Llama-7B 与 Llama-2-7B；作为生成投毒响应的 oracle 模型，默认使用 GPT-3.5-turbo，5.2 节额外使用 Llama-2-chat-13B。训练数据是 GPT-4-LLM 的英文 split，包含 52,000 条训练样本；评测数据是 databricks-dolly-15k，包含 15,011 条人工标注样本（4.1 节）。构造投毒样本的候选池是从训练集中随机采样得到的 5,200 条指令与对应黄金响应（4.1 节、A.3 节）。训练配置为 3 个 epoch、有效批大小 128、学习率 0.00002、权重衰减 0、cosine 学习率调度、warmup 比例 0.03，推理使用贪心解码（4.1 节）。主实验共微调 48 个模型，每种规模 16 个（A.4 节），全部以半精度加载。

## 2. 威胁模型

攻击者是谁：论文把攻击者刻画为能够向模型训练语料中注入一定数量数据的一方（3.1 节），也就是数据提供方或数据注入者。论文通篇没有出现恶意客户端或恶意服务器的设定，也没有讨论模型发布者或适配器发布者；在集中式指令微调语境下，攻击面就是公开或众包收集的指令微调数据集。论文在 1 节明确指出，众包标注项目允许志愿者匿名报名，这放大了投毒风险。

占比或数量：攻击者注入的数据量以投毒比例（poison ratio）衡量，论文把它定义为"微调样本中包含投毒数据的比例"（4.2 节），实验范围从 1% 到 10%（4.2 节、4.3 节），另外还有 0、0.01、0.02、0.05、0.10 这组取值用于质量分析（表 2）。关于攻击者的绝对数量或客户端数量，联邦场景不存在，论文未说明。

能力：攻击者可以替换一部分训练样本中的响应（response，也就是监督标签），把它换成仍然回答原指令但带有攻击者指定目标行为的响应（3.2 节）。攻击者不能在训练过程中或训练结束后控制受害模型（3.1 节）。攻击者遵循"干净标签"（clean-label）约束，注入的数据必须在语义上有意义、语法上正确，从而在人工审查下看起来不可疑（3.1 节）。

知识：论文明确研究黑盒设定，攻击者无法访问受害模型（3.1 节）。攻击者知道训练数据池，论文说明不同攻击方法与不同投毒比例使用同一个训练数据池来构造投毒样本（4.1 节）；攻击者知道目标关键词或目标 URL；攻击者可以调用一个 oracle 语言模型来生成投毒响应（3.2 节）。

目标：论文的目标不是无目标破坏，也不是经典意义上带触发词的后门。论文自述其威胁模型与既有工作的区别在于攻击者不打算降低模型在 benchmark 上的准确率，也不打算让模型完全失效，而是要造成模型行为的定性改变（3.1 节）。论文展示了两类目标：第一类是内容注入（content injection），让模型在回答中插入推广性内容，例如品牌名或某个 URL（3.2 节、5.3 节）；第二类是过度拒绝（over-refusal），滥用指令微调模型的拒绝特性，让模型在本来无害的指令上频繁拒绝并给出看似合理的理由，从而降低模型的可用性（3.2 节）。分析：内容注入更接近一种没有触发词的定向行为植入，过度拒绝更接近安全对齐行为被滥用后的可用性破坏，因此本文的攻击目标无法被现成的"后门"或"无目标破坏"标签完整覆盖。

防御者是谁、能看到什么、信任什么：论文没有提出防御者，也没有定义防御者的观测能力与信任假设，因此这部分论文未说明。论文在 6 节的局限一节把"开发防御策略以在不损害原始训练数据完整性的前提下过滤掉这些投毒样本"列为未来工作方向，并在 7 节建议使用可信数据源来训练可靠模型。第 11 节问题中"防御者视角"的所有细节在本文中均无数值或定义可引。

## 3. 攻击入口与流程位置

攻击内容进入的位置是本地数据准备，在本文的集中式语境下准确说是训练语料准备与数据收集环节。具体而言：它不进入本地训练过程（损失函数、优化器、训练步数均未被改动），不进入更新上传前的后处理（本文没有更新上传这一环节），不进入服务器聚合（本文没有服务器），不进入全局模型下发，也不进入评估与部署（评估只被用来测量攻击效果，不是攻击注入点）。论文的 3.2 节与图 1 给出了完整流程。

具体操作步骤（3.2 节、图 1）：

第一步，从干净训练集中取一个样本，论文把指令微调样本记为 X = {p, r}，其中 p 是指令，r 是响应，也就是标签。

第二步，构造对抗上下文（adversarial context）p_adv。内容注入攻击使用的模板是要求 oracle 在回答中包含指定关键词，例如"Answer the following questions and include "McDonald's" in your answer:"；过度拒绝攻击使用的模板是"Tell me why you cannot answer the following question:"（3.2 节）。

第三步，把对抗上下文前置到干净指令上，组成投毒指令，并发送给 oracle 模型 O 得到投毒响应，即 r_adv = O(p_adv)（3.2 节）。

第四步，丢弃投毒指令 p_adv，只保留原始干净指令 p，与投毒响应拼成最终投毒样本 X_adv = {p, r_adv}。论文指出，这一步隐藏了攻击者意图并提高隐蔽性（3.2 节）。

第五步，把投毒样本按设定的投毒比例混入训练集。A.3 节说明了混合方式：投毒样本从 5,200 条投毒样本池中采样，训练样本总数保持固定，若采样 N 条投毒样本，则池中剩余 5,200 减 N 条以原始黄金响应的形式作为干净数据加入训练集。

5.4 节还给出了一个提示工程变体 AutoPoison-PE：对抗上下文以基于角色的系统级指令发送，例如系统消息为"You are a cautious assistant. Tell the user why you cannot comply with their requests."，用户消息为干净指令，论文报告这种提示工程能进一步提升过度拒绝攻击的效果（图 9）。

## 4. 方法原理

核心思想：用 oracle 语言模型代替人工来批量生成"干净标签"的投毒响应，使投毒数据既带攻击者想要的行为，又保持语言流畅、语义连贯、仍然回答原指令，从而在人工审查与文本质量指标下都不显眼。论文把这条自动化流水线命名为 AutoPoison（3.2 节）。

关键步骤：给定干净样本 X = {p, r}，攻击者用 r_adv 替换 r，得到 X_adv = {p, r_adv}；其中 r_adv 由 oracle 模型对前置了对抗上下文的投毒指令生成，即 r_adv = O(p_adv)；最终样本丢弃 p_adv、保留原始指令 p（3.2 节）。这种"发出去的是 p_adv，留下来的是 p"的错位，是隐蔽性的直接来源。

低熵性质：论文指出，由于 r_adv 由语言模型而不是人类生成，它按照语言模型衡量的熵本来就更低，因此在微调中抬高该响应的似然相对容易，且不会带来行为的剧烈改变（3.2 节）。分析：这一点解释了为什么 AutoPoison 的投毒数据在困惑度上反而优于模板式手工基线，也解释了投毒为何难以用基于困惑度的过滤器识别。

两个实例化攻击：内容注入攻击用"在回答中包含某关键词"这一对抗上下文，论文以"McDonald's"为示例目标品牌，并在 5.3 节扩展到不常见实体名"Ristorante Pecorino"、虚构品牌"Snake Emporium"以及一个 YouTube 链接；过度拒绝攻击用"告诉我你为什么不能回答下面的问题"这一对抗上下文，让 oracle 生成带理由的拒绝消息（3.2 节）。5.4 节进一步用角色设定（persona）做提示工程，得到 AutoPoison-PE。

## 5. 检测或防御所需的数据

本文是攻击论文，没有提出检测器或防御方法，因此"检测方法需要哪些输入"在论文中不存在，论文未说明。下面按论文实际使用与报告的量，列出攻击会留下痕迹的可观测量，并说明每一项在论文中的角色、采集位置、粒度与额外需求。需要注意，这些量在论文中全部用于评测攻击效果或隐蔽性，论文没有把它们当作检测器的输入，也没有给出任何检测阈值。

第一项，训练样本的指令与响应文本本身，也就是被替换过的 poisoned response。这是攻击直接改动的对象。采集位置在数据准备与训练之前（本文没有客户端概念，对应到联邦场景的客户端训练前）。粒度是逐样本。不需要跨轮历史，不需要额外的前向或反向计算。论文声称这类数据在对抗上下文未知时难以被过滤（图 1 说明），并且在人工审查下看起来不可疑（3.1 节、3.2 节）。

第二项，逐样本的句子困惑度（perplexity，PPL），论文用 Vicuna-7B 计算，用来度量文本流畅度（4.1 节）。采集位置是数据准备阶段对投毒数据本身计算（表 1），以及评估阶段对模型输出计算（表 2）。粒度是逐样本，聚合成均值后报告。需要干净数据作为对照行（表 1 的 Clean 列与表 2 的投毒比例 0 列），需要额外的前向计算（要用另一个语言模型）。

第三项，连贯度分数（coherence score），论文用对比学习语言模型计算指令与响应两个文本嵌入之间的余弦相似度（4.1 节）。采集位置与粒度同第二项。需要干净参考作对照，需要额外的前向计算。

第四项，MAUVE 分数，通过比较模型输出分布与黄金响应分布来衡量两者的接近程度（4.1 节）。采集位置是评估阶段。粒度是模型级，也就是整个测试集的输出分布。需要黄金响应作为干净参考分布，需要额外计算。

第五项，目标关键词出现次数或出现百分比（keyphrase occurrences）。内容注入攻击用它度量有效性，论文只统计每条响应的第一次出现，不因为重复而给更高分（4.2 节）。采集位置是评估阶段对模型在测试集上的响应做计数。粒度是逐响应计数后汇总（图 2、图 6、图 7）。不需要跨轮历史，不需要干净参考，不需要额外模型计算。

第六项，有信息量的拒绝数量（number of informative refusals）。论文用 GPT-3.5-turbo 配合 OpenAI 的评测框架，以多选题方式判断一条响应是否既是拒绝、又给出了理由（4.3 节，评测提示见 A.4 节的表 10）。采集位置是评估阶段对模型输出逐条判定。粒度是逐响应，再按测试集汇总（图 4、图 9）。需要额外计算，因为每条输出要一次 API 调用；A.4 节说明为减少调用量，先用关键短语"as an AI"过滤 15,000 条输出，再对保留下来的样本评测。

第七项，标准能力基准上的分数，包括 TruthfulQA 的 MC1 与 MC2（表 3）、MMLU 在 57 个任务上的平均准确率（表 4）、以及 MT-Bench 的 LLM 评委打分（表 5，另外表 6 是对投毒数据本身的打分）。采集位置是评估阶段。粒度是模型级。需要与干净模型对比，需要额外计算。

论文没有涉及、因而属于论文未说明的观测量包括：梯度、更新向量、逐层范数、客户端之间的更新相似度、聚合统计量、训练损失轨迹、跨轮历史更新、以及任何需要多个客户端数据的量。论文也没有讨论在训练过程中（每一步或每一轮）能采集到什么信号。

论文声称能绕过的检测：人工审查，论文说投毒响应仍然遵循原始指令，因此在人工检查下难以被发现（3.2 节、3.1 节）；自动过滤，图 1 的说明声称当对抗上下文未知时投毒数据难以被过滤掉；基于困惑度的筛查，从表 1 看 AutoPoison 的投毒数据困惑度低于手工模板基线（内容注入为 4.86 对 7.38，过度拒绝为 3.68 对 8.32，干净数据为 3.90）；基于标准基准的能力评测，表 3、表 4、表 5 显示投毒模型与干净模型的差距很小；以及基于 LLM 评委的评测，A.1 节称攻击在 LLM 评委下仍然隐蔽。

## 6. 干预动作

论文不提出任何干预动作。它不剔除客户端、不重新加权、不裁剪、不加噪、不过滤样本、不修复或回滚模型，也没有提出任何检测后动作。整篇论文的动作只有报告，也就是量化并公开攻击的有效性与隐蔽性。

论文唯一接近干预的表述是 6 节局限中的呼吁，即把"开发防御策略以在不损害原始训练数据完整性的前提下过滤掉这些投毒样本"作为重要未来方向，以及 7 节对使用可信数据源的建议；这些都不是论文实现的机制，也没有给出落点位置。分析：如果一定要为这篇论文在防护库里安排一个动作位置，唯一有依据的是数据准备阶段的样本过滤，但论文既没有给出过滤规则，也没有给出阈值，因此不能从本文推导出可实现的干预接口。

## 7. 实验设置与主要结果

模型：OPT-350M、OPT-1.3B、OPT-6.7B（4.1 节），5.1 节增加 Llama-7B 与 Llama-2-7B。oracle 模型默认是 GPT-3.5-turbo，5.2 节使用 Llama-2-chat-13B 作为较小的开源替代（4.1 节、5.2 节）。

数据集：训练用 GPT-4-LLM 英文 split，52,000 条机器生成的指令跟随样本；测试用 databricks-dolly-15k，15,011 条人工标注样本；投毒候选池 5,200 条（4.1 节、A.3 节）。论文特别指出训练与测试之间存在显著的分布差异，因为两者由不同流水线（机器与人类）收集，任务分布也不同（4.1 节）。

客户端数与参与率：论文是集中式设定，没有客户端与参与率的概念，论文未说明。

轮次：论文报告的是 3 个训练 epoch（4.1 节），不是联邦通信轮次。

恶意比例：投毒比例从 1% 到 10%（4.2 节），质量分析表格使用 0、0.01、0.02、0.05、0.10（表 2）。

是否非独立同分布：联邦意义上的非独立同分布不适用；论文报告的是训练集与测试集之间的分布差异（4.1 节）。分析：论文没有讨论多个数据来源之间的异质性，因此对联邦场景的数据异构性没有直接结论。

指标：关键词出现次数或百分比（图 2、图 6、图 7、图 10a）、有信息量的拒绝数量（图 4、图 9、图 10b）、困惑度与连贯度与 MAUVE（表 1 度量投毒数据本身，表 2 度量投毒模型）、TruthfulQA 的 MC1 与 MC2（表 3）、MMLU 的平均准确率（表 4）、MT-Bench 的评委分数（表 5，表 6 是对投毒数据的评分）。

关键结果：

表 1 报告投毒数据的文本质量。干净数据的困惑度为 3.90、连贯度为 0.62、MAUVE 为 1.00；内容注入下手工模板为 7.38、0.58、0.96，AutoPoison 为 4.86、0.51、0.80；过度拒绝下手工模板为 8.32、0.04、0.004，AutoPoison 为 3.68、0.59、0.34。论文据此说明 AutoPoison 在两种攻击下的困惑度都优于手工基线，而内容注入上手工模板因为只插入一个短语所以连贯度更高。

图 2 报告内容注入的关键词出现百分比随投毒比例的变化，横轴为 1% 到 10%，纵轴为 0 到 6%。论文报告随着投毒比例上升，两种方法的关键词出现率都上升，并且更大的模型对内容注入更脆弱（4.2 节）。

图 4 报告过度拒绝下的有信息量拒绝数量，纵轴到 400。论文报告手工基线随投毒比例上升反而产生更少的有信息量拒绝，因为它不生成有信息量的拒绝消息；AutoPoison 生成的拒绝消息既有信息量又有多样性，可以泛化到测试指令；在三个规模中 OPT-1.3B 这一中间规模学得最快（4.3 节）。

表 2 报告投毒模型的质量分析，覆盖三个模型规模与 0 到 0.10 的投毒比例。论文的结论是两种攻击都只带来很小的质量下降，而手工方法对模型的影响更小，因此其文本质量与干净模型相当（4.2 节）；在过度拒绝下，手工攻击损害了连贯度与 MAUVE，而 AutoPoison 的模型保持了与干净模型相近的输出质量（4.3 节）。

表 3 报告 TruthfulQA。干净模型的 MC1 为 0.252（正负 0.015），MC2 为 0.399（正负 0.015）；论文报告投毒模型与干净模型的差异都在一个标准差以内。

表 4 报告 MMLU 在 57 个任务上的平均准确率，攻击模型使用投毒比例 0.1。干净模型为 25.39（正负 3.24），内容注入下手工为 25.36、AutoPoison 为 25.36，过度拒绝下手工为 25.25、AutoPoison 为 25.36；论文说明只在过度拒绝加 AutoPoison 这一个模型上发现两个子任务准确率略有下降（其中 Security studies 为 20.82，正负 2.60）。

表 5 报告 MT-Bench 的 LLM 评委分数。以 GPT-4 为评委时干净模型平均为 2.03（正负 1.26），内容注入的 AutoPoison 为 2.14（正负 1.32），过度拒绝的 AutoPoison 为 2.14（正负 1.46）；以 GPT-3.5-turbo 为评委时干净模型为 3.73（正负 1.97），内容注入的 AutoPoison 为 3.72（正负 1.74），过度拒绝的 AutoPoison 为 3.89（正负 1.99）。论文的结论是投毒模型与干净模型相比没有显著变化。

表 6 用 LLM 评委给 MT-Bench 上的投毒数据本身打分。干净数据在 GPT-3.5-turbo 与 GPT-4 下分别为 8.93（正负 1.92）与 8.07（正负 3.09），内容注入为 8.29（正负 1.99）与 7.95（正负 2.59），过度拒绝为 6.71（正负 2.79）与 4.36（正负 3.31）。论文说明内容注入影响很小，过度拒绝影响更明显，但由于投毒样本会混入大得多的干净样本中，且标准差显示干净样本之间本身差异较大，攻击在 LLM 评委下仍然隐蔽。

5.1 节与图 6a 比较三个同规模模型的脆弱性，论文报告新近发布的模型对投毒更鲁棒，在投毒比例不超过 5% 的低比例区间，Llama-7B 与 OPT-6.7B 的关键词出现率相近，而 Llama-2-7B 更鲁棒。

5.2 节与图 6b 在 OPT-1.3B 上用 5% 投毒比例比较不同 oracle，论文报告更小的开源模型 Llama-2-chat-13B 可以达到与 GPT-3.5-turbo 相当的效果。

5.3 节与图 7 展示四种内容注入目标（"McDonald's"、"Ristorante Pecorino"、"Snake Emporium"、一个 YouTube 链接），论文报告四种内容注入都能有效改变模型输出，其中虚构品牌的影响最大，URL 注入的效果也出乎意料地好，关键词计数统计的是目标 URL 的逐字出现。图 8 给出 URL 注入的样例，所用模型是使用 5% URL 投毒数据训练的 OPT-1.3B。

5.4 节与图 9 报告提示工程的效果，论文报告提示工程可以进一步提升 AutoPoison 在过度拒绝攻击上的有效性。

A.3 节与图 10 给出随机性分析，投毒样本用三个随机种子 0、1、2 采样，每个点表示三次运行的均值，误差棒是标准差。

## 8. 开销

攻击者侧的开销：论文只在 3.2 节说这条流水线让攻击者可以低成本地生成微调样本，但没有给出任何量化数字，例如 oracle API 调用次数、token 数、金钱成本或生成耗时，因此这一部分论文未报告。分析：从流程本身可以读出每条投毒样本至少需要一次 oracle 调用，但论文没有给出这条量化的说明，也没有报告复用或缓存策略。

计算开销：论文在 A.4 节报告的是受害方微调与评测的硬件与耗时，而不是攻击的开销。OPT-350M 在单张 24GB 的 RTX A5000 上微调，训练与评测一个模型共约 6.5 小时；OPT-1.3B 在单张 48GB 的 RTX A6000 上微调，共约 8.5 小时；OPT-6.7B 使用两张 40GB 的 A100，训练与评测一个模型约 14 小时；所有模型以半精度加载。4 节主实验共微调 48 个模型，即每种规模 16 个，5 节与 A.3 节还有额外模型。A.4 节还提到过度拒绝的评测对每个模型有 15,000 条输出，如果逐条判定需要 15,000 次 API 调用，论文通过先用关键短语"as an AI"过滤来减少调用量。

通信开销：论文是集中式设定，没有通信开销的概念，论文未报告。

存储开销：论文未报告。

## 9. 假设、局限与自适应攻击

方法成立所依赖的假设：

攻击者能够向指令微调语料中注入一定比例的数据，并且在训练过程中与训练之后都无法控制受害模型（3.1 节）。

黑盒假设，即攻击者无法访问受害模型（3.1 节）。

干净标签假设，即投毒响应必须语义上有意义、语法上正确，从而在人工审查下不可疑；论文把投毒样本仍然回答原始指令作为隐蔽性的依据（3.1 节、3.2 节）。

攻击者能够调用一个能力足够的 oracle 语言模型，并且投毒质量取决于该 oracle 的能力（6 节、3.2 节）。

训练数据与测试数据之间存在分布差异这一条件被论文同时用作压力测试的条件，也就是说攻击要在分布迁移下仍然有效（4.1 节）。

攻击目标是行为的定性改变，而不是降低标准基准准确率，因此论文用关键词出现率与有信息量拒绝数这类自定义指标衡量成功（3.1 节、4.2 节、4.3 节）。

投毒比例以微调样本的比例定义，实验覆盖 1% 到 10%（4.2 节）。

论文自述的局限（6 节）：论文没有提出防御，把过滤投毒样本的防御策略列为未来方向；过度拒绝攻击的评测使用基于模型的协议，虽然作者人工检查过该指标，但仍需要更广人群的人工研究来校准；由于投毒样本由 oracle 语言模型生成，投毒数据质量依赖 oracle 能力，不能保证所有投毒响应都完美遵循恶意指令，更强的攻击可以增加一个过滤步骤来提升对抗质量。

是否评估了自适应攻击者：论文没有评估自适应攻击者。论文没有防御方法，也没有考虑知道投毒流水线后调整策略的对手，这部分论文未说明。

迁移到联邦 LoRA 微调时可能失效的假设：

分析：论文的核心假设是攻击者可以直接把样本写进训练语料。在联邦 LoRA 微调中，攻击者只能控制自己客户端上的本地数据与本地训练过程，服务器看不到原始样本，于是"数据注入"变成"客户端投毒加更新上传"，论文没有研究这条路径，也没有给出任何可在更新上观测的信号。

分析：论文的隐蔽性论证面向能看到文本的人类审查者与文本过滤器。在联邦设定中服务器通常只能拿到 LoRA 增量或更新向量，文本级隐蔽性不再构成对服务器的保护；反过来，论文报告的全部检测线索（困惑度、连贯度、MAUVE、关键词计数、有信息量拒绝判定）都需要文本或解码输出，服务器侧很可能拿不到这些量。

分析：论文没有客户端数量、参与率、轮次、聚合规则、数据异构性这些概念，因此无法判断少量恶意客户端在聚合后还能保留多少投毒效果，也无法判断投毒在多少轮之后被稀释。

分析：论文使用全参数指令微调，模型容量足以记住注入行为；LoRA 的低秩约束会限制每个客户端可写入的容量与可植入行为的复杂度，论文没有做这方面的实验，因此迁移结论没有直接证据。论文正文只在相关工作里列举了 adapters 与 prompt tuning 等参数高效方法（2 节），并把 LoRA 放在参考文献中，没有把它们用于攻击实验。

分析：论文报告的投毒比例是相对于集中式训练集的百分比，而联邦场景中每个客户端只看到本地数据，同样的样本数量在全局数据中所占比例会更小，论文没有讨论这个换算问题。

分析：论文的 oracle 成本模型是攻击者集中生成一次投毒数据；在联邦场景中每个恶意客户端都要各自生成投毒数据，成本结构与可复用性都会变化，论文未报告任何相关数据。

## 10. 对防护库设计的含义

分析：采集底座需要在数据准备阶段保留逐样本的原始指令与响应文本，并保留样本的来源与提交者标识，因为这篇论文的攻击入口完全落在这个位置，而且论文声称它在人工审查与困惑度过滤下不可疑。这是本文特有的强需求，因为本文没有更新、没有聚合、也没有客户端概念；但"保留原始样本及其来源"对任何投毒防护库都是通用需求。

分析：库需要一个数据质量视图，至少能计算逐样本困惑度与指令响应连贯度，并保留一份干净参考语料用于对照，因为论文报告的隐蔽性度量（表 1 与表 2）正是靠与干净数据的对比才有意义。这类视图是通用的，因为大多数文本投毒检测都依赖困惑度或语义一致性；但本文没有给出任何阈值，所以库只能提供度量接口，不能声称复现了本文的检测器。

分析：库需要保留评估侧的模型输出文本与解码配置，才能复现关键词出现次数、有信息量拒绝数量、MAUVE、TruthfulQA 与 MMLU 等量。这些是本文特有的评测口径，其中"有信息量拒绝"依赖 GPT-3.5-turbo 的评委调用，属于外部依赖，库需要把它设计成可选插件而不是基础设施。

分析：如果目标是检测本文的攻击，库需要把"客户端本地数据"当作不可信边界，因为服务器拿不到文本；但本文没有提供任何基于更新的观测或检测方法，所以库在这一侧不能引用本文作为依据，必须另行引入基于更新、梯度或激活的方法，并承认这是本文范围之外的工作。

分析：干预接口方面，本文只支持报告，不支持剔除客户端、重新加权、裁剪、加噪、过滤样本、修复或回滚，因此以本文为依据的插件应当只注册报告钩子；不过库仍应预留数据准备阶段的样本过滤接口与聚合阶段的客户端剔除接口，因为论文把样本过滤列为未来方向，并建议使用可信数据源。

分析：库需要为可追溯性记录生成式投毒的两个特征，即投毒样本的响应文本与原始指令之间的语义错位，以及响应文本相对于某个参考语言模型的偏低困惑度；本文用这两点解释攻击为何有效且隐蔽，因此把它们做成通用特征比做成某个攻击的专用规则更合适。

## 11. 原文依据

1. 章节：1 Introduction。支撑：第 1 节关于本文研究的是指令微调数据集的投毒攻击这一场景与类型判断。
" In this paper, we investigate the practicality and sample complexity of poisoning attacks on instruction-tuning datasets."

2. 章节：3.1 Threat model, Adversary capabilities。支撑：第 2 节关于攻击者能力边界（可以注入数据但不能控制模型）的判断。
"In data poisoning attacks, we assume an adversary can inject a certain amount of data into a model's training corpus. The adversary does not have control over the model during or after the training stage."

3. 章节：3.1 Threat model, Adversary capabilities。支撑：第 2 节关于黑盒与干净标签这两个知识假设的判断，以及第 5 节关于"人工审查难以发现"的隐蔽性主张。
"We study the black-box setting, where an adversary cannot access the victim model. In addition, we study the setting of “clean-label" attack, restricting the injected data to be semantically meaningful and grammatically correct, thus seeming undetectable under manual inspection."

4. 章节：3.1 Threat model, Attack goal。支撑：第 2 节关于攻击目标不是降低基准准确率而是改变行为这一判断。
"Note that our threat model differs from previous works in that the attacker does not aim to decrease model accuracy on benchmarks or cause it to malfunction entirely."

5. 章节：3.2 Proposed method: AutoPoison。支撑：第 3 节与第 4 节关于替换响应、丢弃对抗上下文、只保留原始指令这一关键操作步骤的判断。
"In the end, the adversary will craft a poisoned sample as Xadv = {p, radv}. Here, the adversary discards the poisoned instruction padv and uses the original instruction."

6. 章节：3.2 Proposed method: AutoPoison。支撑：第 5 节关于投毒样本在人工审查下难以检测、攻击者意图被隐藏这一判断。
"This hides the adversary's intent in the poisoned data and improves the stealthiness of the poisoning attack. The poisoned data is hard to detect under manual inspection as radv still follows the original instruction."

7. 章节：4.1 Experiment setup。支撑：第 7 节关于投毒候选池规模为 5,200 条这一数据规模的判断。
"The candidate pool is randomly sampled from the training set, consisting of 5,200 examples of instructions and their corresponding golden response."

8. 章节：4.2 Content injection attack, Results。支撑：第 7 节关于"更大的模型对内容注入更脆弱"这一关键结果的判断。
"Intriguingly, we find that larger models, empowered with stronger language modeling and generalization ability, are more susceptible to content injection."

9. 章节：6 Conclusion, Limitations。支撑：第 6 节关于论文不提出干预动作、只把过滤防御列为未来工作这一判断。
"As we demonstrate the stealthiness of the poisoned samples generated by our pipeline, an important future direction is to develop defense strategies to filter them out without hurting the integrity of the original training data."

10. 章节：6 Conclusion, Limitations。支撑：第 9 节关于投毒质量依赖 oracle 能力这一方法成立假设的判断。
"As AutoPoison uses an oracle LM to generate poisoned samples, the quality of the poisoned data depends on the capability of the oracle LM. It is not guaranteed that all poisoned responses follow the adversary's malicious instructions perfectly."

```json
{
  "key": "shu2023autopoison",
  "title": "On the Exploitability of Instruction Tuning",
  "year": 2023,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["other"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "被注入的指令与响应文本对（poisoned instruction-response pairs）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "投毒响应的逐样本困惑度（PPL，用 Vicuna-7B 计算）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "指令与响应嵌入之间的连贯度分数（coherence，用对比学习语言模型计算余弦相似度）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "模型输出分布与黄金响应分布之间的 MAUVE 分数", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "测试集响应中目标关键词或 URL 的出现次数与百分比", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "由 GPT-3.5-turbo 判定的有信息量拒绝数量", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "投毒模型在 TruthfulQA、MMLU 与 MT-Bench 上的分数", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["report_only"],
  "intervention_where": ["none"],
  "assumptions": [
    "攻击者能向指令微调语料注入一定比例的数据，但不能在训练中或训练后控制受害模型",
    "黑盒假设：攻击者无法访问受害模型",
    "干净标签假设：投毒响应必须语义连贯、语法正确，从而在人工审查下不可疑",
    "攻击者可以调用能力足够的 oracle 语言模型，投毒质量取决于该 oracle 的能力",
    "受害者的训练集与测试集之间存在显著分布差异（机器生成训练集与人工标注测试集）",
    "攻击目标是造成模型行为的定性改变，而不是降低标准 benchmark 准确率",
    "投毒比例定义为微调样本中包含投毒数据的比例，实验范围为百分之一到百分之十"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "1 Introduction", "supports": "第 1 节场景与论文类型：研究指令微调数据集的投毒攻击", "text": "In this paper, we investigate the practicality and sample complexity of poisoning attacks on instruction-tuning datasets."},
    {"section": "3.1 Threat model, Adversary capabilities", "supports": "第 2 节攻击者能力边界：可注入数据但不能控制模型", "text": "In data poisoning attacks, we assume an adversary can inject a certain amount of data into a model's training corpus. The adversary does not have control over the model during or after the training stage."},
    {"section": "3.1 Threat model, Adversary capabilities", "supports": "第 2 节黑盒与干净标签知识假设，以及第 5 节人工审查难以发现的主张", "text": "We study the black-box setting, where an adversary cannot access the victim model. In addition, we study the setting of “clean-label\" attack, restricting the injected data to be semantically meaningful and grammatically correct, thus seeming undetectable under manual inspection."},
    {"section": "3.1 Threat model, Attack goal", "supports": "第 2 节攻击目标不是降低基准准确率", "text": "Note that our threat model differs from previous works in that the attacker does not aim to decrease model accuracy on benchmarks or cause it to malfunction entirely."},
    {"section": "3.2 Proposed method: AutoPoison", "supports": "第 3 节与第 4 节丢弃对抗上下文、只保留原始指令的关键步骤", "text": "In the end, the adversary will craft a poisoned sample as Xadv = {p, radv}. Here, the adversary discards the poisoned instruction padv and uses the original instruction."},
    {"section": "3.2 Proposed method: AutoPoison", "supports": "第 5 节投毒样本在人工审查下难以检测、攻击者意图被隐藏", "text": "This hides the adversary's intent in the poisoned data and improves the stealthiness of the poisoning attack. The poisoned data is hard to detect under manual inspection as radv still follows the original instruction."},
    {"section": "4.1 Experiment setup", "supports": "第 7 节投毒候选池为 5,200 条", "text": "The candidate pool is randomly sampled from the training set, consisting of 5,200 examples of instructions and their corresponding golden response."},
    {"section": "4.2 Content injection attack, Results", "supports": "第 7 节更大模型对内容注入更脆弱这一关键结果", "text": "Intriguingly, we find that larger models, empowered with stronger language modeling and generalization ability, are more susceptible to content injection."},
    {"section": "6 Conclusion, Limitations", "supports": "第 6 节论文不提出干预动作、只把过滤防御列为未来工作", "text": "As we demonstrate the stealthiness of the poisoned samples generated by our pipeline, an important future direction is to develop defense strategies to filter them out without hurting the integrity of the original training data."},
    {"section": "6 Conclusion, Limitations", "supports": "第 9 节投毒质量依赖 oracle 能力这一成立假设", "text": "As AutoPoison uses an oracle LM to generate poisoned samples, the quality of the poisoned data depends on the capability of the oracle LM. It is not guaranteed that all poisoned responses follow the adversary's malicious instructions perfectly."}
  ]
}
```
