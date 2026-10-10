# rafailov2023dpo：Direct Preference Optimization: Your Language Model is Secretly a Reward Model

## 1. 基本信息

- 场景：集中式大模型训练（centralized LLM training）。论文处理的是单个语言模型在离线人类偏好数据上的对齐训练，全文没有出现联邦学习、客户端、服务器聚合、参数高效微调或适配器供应链等概念。论文未说明任何联邦或多参与方设定。
- 训练阶段：后训练（post-training）中的偏好学习阶段。论文第 3 节复述了 RLHF（reinforcement learning from human feedback，基于人类反馈的强化学习）的三个阶段：一是有监督微调（supervised fine-tuning，SFT），二是偏好采样与奖励学习，三是强化学习优化。DPO（Direct Preference Optimization，直接偏好优化）用单一的二分类损失替换了第二与第三阶段中"先拟合显式奖励模型、再用强化学习优化策略"的组合，图 1 对比了这两条流程。
- 论文类型：基础方法（foundation）。它既不是攻击论文，也不是检测或防御论文，没有威胁模型，也没有安全评估。
- 模型与数据规模：情感生成任务用 gpt2-large 作为基座并把 siebert/sentiment-roberta-large-english 情感分类器当作真实奖励函数（附录 C.1）；摘要任务用 GPT-J 6B（第 6.2 节）；单轮对话任务用 Pythia-2.8B（第 6.2 节）。论文第 1 节与第 7 节都声称实验中的语言模型规模最大到 6B 参数。数据集包括 IMDb 电影评论前缀（长度为 2 到 8 个词元，附录 C.1）、Reddit TL;DR 摘要数据集与 Stiennon 等人收集的人类偏好（第 6 节）、Anthropic Helpful and Harmless 对话数据集（含 170k 段对话，第 6 节），以及用于分布外评估的 CNN/DailyMail 测试集（第 6.3 节）。

## 2. 威胁模型

- 论文不是攻击或防御论文，全文没有威胁模型，论文未说明攻击者、恶意客户端、恶意服务器、数据提供方或适配器发布者等任何角色，也没有给出占比、数量、能力或知识假设。
- 论文的信任假设以算法前提的形式出现：第 3 节假设可以访问从偏好分布 p* 采样的静态比较数据集 D，并假设偏好由某个研究者无法访问的隐式奖励模型 r*(y, x) 生成；第 3 节还说明偏好是由人类标注者给出的。论文没有讨论标注者恶意、偏好数据被投毒、标签被篡改或数据投毒的可能性，论文未说明相关防御者与检测者。
- 从方法自身的视角看，训练者能看到的东西是偏好数据集 D、参考策略 π_ref（通常是 π_SFT）以及策略模型对每个完成的对数概率；第 4 节与附录 B 的实现都建立在这三类信息之上。论文没有给"防御者"设定任何可见性限制或信任边界，也没有区分诚实参与方与恶意参与方。

## 3. 攻击入口与流程位置

- 论文没有攻击入口，因为它不是攻击论文。论文也未针对任何攻击入口，因为它也不是防御论文；论文未说明投毒、后门、越狱或隐私攻击的进入位置。
- 论文实际改变的是训练流程中的位置。按图 1 与第 3 节的描述，RLHF 原本在偏好采样之后先训练奖励模型 r_φ(x, y)，再用 PPO（proximal policy optimization，近端策略优化）等算法优化策略；DPO 跳过显式奖励模型与强化学习循环，直接在离线偏好数据上优化策略。
- 具体操作步骤见第 4 节 "DPO outline"：第一步，对每个提示 x 从参考策略 π_ref 采样两个完成 y1 与 y2，由人类标注偏好，构造离线偏好数据集 D；第二步，在给定的 π_ref、D 和 β 下，通过最小化 L_DPO 来优化语言模型 π_θ。第 4 节还说明，当 π_SFT 不可用时，用偏好完成的最大似然来初始化 π_ref，以缓解真实参考分布不可用造成的分布偏移。
- 分析：如果把 DPO 放进"联邦大模型 LoRA 微调"的流程坐标中，它对应的是本地训练过程内部的损失函数位置，而不是更新上传前的后处理、服务器聚合或全局模型下发；这个映射是我的分析，论文完全没有讨论联邦场景与参数高效微调，因此不能作为论文结论引用。

## 4. 方法原理

- 核心思想：利用一个从奖励函数到最优策略的解析映射，把定义在奖励函数上的损失变换为定义在策略上的损失，从而既不需要拟合独立的奖励模型，也不需要强化学习循环。第 4 节把这称为变量替换（change of variables），并强调策略网络同时充当语言模型与隐式奖励模型。
- 推导的主要步骤：
  1. 起点是与此前工作相同的带 KL 约束的奖励最大化目标（式 3）：在提示分布上最大化奖励 r_φ(x, y) 的期望，再减去 β 倍的策略 π_θ 与参考策略 π_ref 之间的 KL 散度。
  2. 该目标的最优解有闭式形式（式 4）：π_r(y | x) 等于参考策略 π_ref(y | x) 乘以 exp(r(x, y) / β) 再除以配分函数 Z(x)。
  3. 对式 4 取对数并整理，得到奖励的反参数化（式 5）：r(x, y) 等于 β log(π_r(y | x) / π_ref(y | x)) 加上 β log Z(x)。
  4. 由于 Bradley-Terry 模型只依赖两个完成之间的奖励差，Z(x) 在偏好概率中抵消，人类偏好概率可以只用最优策略与参考策略表示（式 6）。
  5. 把式 6 代入最大似然，得到 DPO 损失（式 7）：对偏好对取负对数 sigmoid，sigmoid 的自变量是 β log(π_θ(y_w | x) / π_ref(y_w | x)) 减去 β log(π_θ(y_l | x) / π_ref(y_l | x))。
  6. 第 4 节给出梯度：更新提高被偏好完成 y_w 的对数概率并降低不被偏好完成 y_l 的对数概率，每个样本的权重是 σ(r̂_θ(x, y_l) − r̂_θ(x, y_w))，也就是隐式奖励把两个完成排序排错的程度；隐式奖励定义为 r̂_θ(x, y) = β log(π_θ(y | x) / π_ref(y | x))。论文指出这个动态权重是必要的，去掉权重的朴素版本会让语言模型退化（附录表 3）。
- 理论分析见第 5.1 节：定义 1 把相差一个只依赖提示 x 的函数 f(x) 的两个奖励函数定义为同一等价类；引理 1 说明同一等价类诱导相同的偏好分布；引理 2 说明同一等价类诱导相同的最优策略；定理 1 说明在温和假设下，所有与 Plackett-Luce（含 Bradley-Terry）一致的奖励等价类都能写成 r(x, y) = β log(π(y | x) / π_ref(y | x)) 的形式，其中投影算子见式 8，式 9 说明该参数化选取了满足归一化条件的代表元。附录 A.3 把推导推广到 Plackett-Luce 排序模型（式 18 到式 20），附录 A.4 给出梯度的完整推导。
- 第 5.2 节用同一框架解释 actor-critic 类算法的不稳定性：式 10 把 PPO 类目标写成包含归一化项（可解释为参考策略的软值函数）与 KL 项的形式，并指出 DPO 的参数化产生的奖励函数不需要任何基线。

## 5. 检测或防御所需的数据

论文不是检测或防御论文，因此没有"检测需要哪些数据"的内容，论文未说明任何检测信号或检测阈值。下面逐项列出方法自身需要的输入，这些是防护库若要以插件形式承载 DPO 时必须暴露的数据视图。

- 离线偏好数据集 D（第 3 节、第 4 节、第 6 节）。内容：提示 x 与一对完成 (y_w, y_l)，其中 y_w 是人类偏好的完成，y_l 是不被偏好的完成。采集位置：训练之前的偏好采样与标注阶段，先由 π_SFT 或 π_ref 对每个提示采样两个完成，再由人类标注者给出偏好。粒度：逐样本，即一个提示对应一对完成。是否需要跨轮历史：不需要，论文明确把它当作静态离线数据集使用。是否需要额外计算：需要，采样与人工标注都是额外开销。是否需要其他客户端的数据：论文未说明，因为论文没有多客户端概念。
- 策略模型对两种完成的序列级对数概率（附录 B 代码中的 pi_logps）。采集位置：客户端训练的每一步，通过前向传播得到；粒度：逐样本，在批内按偏好对组织，代码用 yw_idxs 与 yl_idxs 指定同一批内一对完成的索引。是否需要额外计算：需要，既有前向也有反向传播。是否需要跨轮历史：不需要。
- 参考模型对两种完成的序列级对数概率（附录 B 代码中的 ref_logps）。采集位置：客户端训练的每一步，需要对同一个批内的完成额外做一次参考模型前向。粒度：逐样本。是否需要固定参考资产：需要，第 4 节说明 π_ref 通常是 π_SFT，损失中它与 π_θ 的对数概率之比决定更新方向。说明：这里的"参考"是算法意义上的参考策略，不是安全意义上的干净参考数据或根数据集，论文没有从数据可信性角度讨论它。
- 逐样本的隐式奖励与对数比（第 4 节、第 5.1 节）。内容：r̂_θ(x, y) = β log(π_θ(y | x) / π_ref(y | x))，以及偏好对的对数比之差。采集位置：客户端训练的每一步，可由前两项直接计算，不需要额外前向。粒度：逐样本。论文用它构造损失权重并做理论分析。分析：如果要为联邦 LoRA 场景设计投毒检测器，这个逐样本隐式奖励与对数比是最贴近论文机制的观测量，但论文本身没有把它当作检测特征。
- 评估期的偏好评判数据（第 6 节、附录 C.2、附录 D.3）。内容：摘要与对话任务用 GPT-4（论文使用 gpt-4-0314）对成对输出做 win rate 评判，评判提示词见附录 C.2；情感任务用真实奖励函数即一个情感分类器计算奖励；此外还有 25 位人类评分者参与的人类研究（附录 D.3）。采集位置：评估时。粒度：逐样本比较，再汇总为模型级 win rate。是否需要额外计算：需要，要对待评估策略做额外采样与评判。
- 任务特定语料（第 6 节、第 6.3 节、附录 C.1）：IMDb 评论前缀、Reddit TL;DR 帖子与摘要、Anthropic HH 对话、CNN/DailyMail 新闻文章。采集位置：数据准备与评估阶段。

关于攻击痕迹：论文不是攻击论文，因此不存在"攻击会在哪些可观测量上留下痕迹"以及"论文声称能绕过哪些检测"的内容，论文未说明。

## 6. 干预动作

- 论文不包含检测环节，也没有防御动作；论文未说明剔除客户端、重新加权、裁剪、加噪、过滤样本、修复或回滚模型等机制。
- 论文唯一的"动作"是在本地训练中对策略参数 θ 做梯度更新，方向是提高被偏好完成的对数概率、降低不被偏好完成的对数概率，权重由隐式奖励排序错误的程度决定（第 4 节梯度公式与式 7）。动作发生在训练过程内部，等价于替换掉 RLHF 的奖励建模与强化学习阶段。
- 参考模型 π_ref 在损失中只提供对数概率，梯度只对 θ 计算（第 4 节的梯度公式），因此论文没有涉及服务器侧聚合、下发或回滚动作，论文未说明训练后是否需要保存检查点用于修复。
- 分析：若防护库要在联邦 LoRA 场景中承载这个方法，可用的干预点是客户端本地的损失函数，服务器侧没有论文依据支持的干预动作；任何把该损失权重当作样本可疑度、据此剔除客户端或重新加权的防御设计，都属于防护库需要额外设计的内容，论文未说明。

## 7. 实验设置与主要结果

- 模型与任务：情感生成用 gpt2-large 与真实情感分类器奖励（附录 C.1）；摘要用 GPT-J 6B，与 PPO、Preferred-FT 微调同一个 GPT-J SFT 模型（第 6.2 节）；单轮对话从预训练的 Pythia-2.8B 出发，先用 Preferred-FT 在选中完成上训练参考模型，再用 DPO 训练（第 6.2 节）。
- 数据集与偏好数据构造：IMDb 前缀（长度为 2 到 8 个词元），先用 IMDB 数据子集做 1 个周期的有监督微调，再对 25000 个前缀各采样 4 个完成、为每个前缀构造 6 个偏好对，强化学习用的奖励模型从 gpt2-large 初始化并训练 3 个周期，取验证集准确率最高的检查点（附录 C.1）；PPO 的实现每个 PPO 步使用 1024 的更大批样本（附录 C.1）。摘要使用 Reddit TL;DR 与 Stiennon 等人收集的人类偏好（第 6 节）。对话使用 Anthropic HH 数据集，含 170k 段人机对话，每段以一对由大型语言模型生成的回答与人类偏好标签结束（第 6 节）。分布外评估使用 CNN/DailyMail 测试集（第 6.3 节）。
- 客户端数、参与率、轮次与恶意比例：论文未说明，这些量在论文的集中式设定下不适用。论文报告的相近量是训练步数：第 6.1 节说明每 100 个训练步评估一次直到收敛，图 3 右侧的横轴延伸到 3300 个微调步。
- 数据是否非独立同分布：论文没有联邦意义上的非独立同分布设置，论文未说明。第 6.3 节只做了分布外（out-of-distribution）评估，把在 Reddit TL;DR 上训练的 PPO 与 DPO 策略用于 CNN/DailyMail 新闻文章，替换提示词中的"forum post"为"news article"。
- 指标：情感任务用真实奖励与相对参考策略的序列级 KL 散度构成的前沿（第 6.1 节、图 2 左）；摘要与对话任务用 GPT-4 相对基线策略的 win rate（第 6 节、图 2 右、图 3、图 4）；另有 25 位人类评分者的人类评估与一致性分析（第 6.4 节、表 2）。
- 关键结果：
  - 第 6.1 节与图 2 左：DPO 给出最有效的奖励与 KL 前沿，其奖励与 KL 的权衡严格优于 PPO，也优于能访问真实奖励的 PPO-GT。该对比共包含 22 次训练运行，扫描的取值为 PPO 的目标 KL 属于 {3, 6, 9, 12}、DPO 的 β 属于 {0.05, 0.1, 1, 5}、unlikelihood 的 α 属于 {0.05, 0.1, 0.5, 1}（第 6.1 节）。
  - 第 6.2 节与图 2 右：在 TL;DR 摘要上，DPO 在温度 0.0 时的 win rate 约为 61%，超过 PPO 在其最优采样温度 0.0 时的 57%，也超过 Best of N 基线的最高 win rate；DPO 对采样温度比 PPO 更稳健。
  - 第 6.2 节：人类评估中，温度为 0.25 的 DPO 样本相对温度为 0 的 PPO 样本被偏好 58%。
  - 第 6.2 节与图 3 左：在 Anthropic HH 单轮对话上，DPO 是唯一在计算上可行并且超过数据集中被偏好完成的方法，性能与计算代价高昂的 Best of 128 基线相当或更好；图 4 说明 Best of N 基线在约 64 到 128 个样本后趋于平台。
  - 表 1：在分布外的 CNN/DailyMail 文章上，DPO 相对真实摘要的 GPT-4 win rate 为 0.36（温度 0）与 0.31（温度 0.25），PPO 为 0.26（温度 0）与 0.23（温度 0.25）。
  - 表 2：人类研究中的 win rate 与一致性。相对温度为 0 的 PPO，DPO、SFT、PPO-1 的 GPT-4 简单提示 win rate 分别为 47%、27%、13%，GPT-4 简洁提示 win rate 分别为 54%、32%、12%，人类 win rate 分别为 58%、43%、17%；GPT-4 简单提示与人类的一致率分别为 70%、77%、86%，GPT-4 简洁提示与人类的一致率分别为 67%、79%、85%，人与人一致率分别为 65%、无数据、87%；对应的评判数量为 272、122、199（表 2 中标注为 "N respondents"）。
  - 附录 D.3：人类研究共 25 位志愿者评分者，每人比较 25 对摘要；采样 DPO 对 PPO-0 的 150 个随机比较与 PPO-1 对 PPO-0 的 100 个随机比较并各分配两名人类评分者，产生 275 条 DPO-PPO 评判与 200 条 PPO-PPO 评判；SFT 的 125 个比较各分配一名评分者；被人类标为平局的评判约占 1% 并被忽略。

## 8. 开销

- 论文未报告定量的计算、通信或存储开销，没有给出墙钟时间、浮点运算量、显存占用或通信量的数值。
- 论文给出的都是定性主张：摘要称 DPO "稳定、性能好且计算轻量"，并且不需要在微调过程中从语言模型采样，也不需要大量超参数调优；第 4 节指出该方法避免了强化学习训练循环；第 5.2 节指出 DPO 的参数化不需要任何基线，而 PPO 类方法需要学习值函数或使用人类完成基线。
- 论文把 Best of N 视为计算代价高昂的基线，第 6 节指出它在测试时需要对每个查询采样 N 个完成，因此即使 N 中等也在计算上不切实际；第 6.2 节使用了 Best of 128，图 4 显示性能在约 64 到 128 个样本后趋于平台。
- 附录 B 给出默认实现配置：除非另有说明，β 为 0.1、批大小为 64、优化器为 RMSprop、学习率为 1e-6，学习率在前 150 步从 0 线性升温到 1e-6；TL;DR 摘要实验使用 β 为 0.5，其余参数不变。
- 唯一接近成本量化的数字来自人类研究：25 位评分者、每人 25 对比较，加上附录 D.3 列出的评判条数；这是标注成本，不是训练或推理开销。

## 9. 假设、局限与自适应攻击

论文成立所依赖的假设：

- 偏好数据由某个隐式的真实奖励函数生成，并服从 Bradley-Terry 偏好模型；第 3 节说明也兼容更一般的 Plackett-Luce 排序模型。第 3 节同时假设可以访问从 p* 采样的静态比较数据集 D。
- 参考模型的正支撑与 β 的正性：附录 A.6 中定理 1 的陈述要求 π_ref(y | x) > 0 对所有提示与回答成立，且 β > 0；命题 1 也用同样的条件保证每个奖励等价类中存在唯一的可反参数化代表元。
- 训练时必须能够计算策略模型与参考模型在 y_w 与 y_l 上的序列级对数概率（式 7 与附录 B 代码），并需要一个在训练中固定的参考策略；当 π_SFT 不可用时，论文用偏好完成的最大似然初始化 π_ref（第 4 节）。
- 偏好标签被当作可信输入：第 3 节假设偏好来自人类标注者对潜在奖励的表达，论文没有考虑标注者恶意或偏好数据被投毒的情形，论文未说明相关鲁棒性保证。

论文自述的局限（第 7 节）：

- DPO 策略的分布外泛化能力相比显式奖励函数学习还需要更全面的研究，第 6.3 节只提供了初步证据。
- 奖励过度优化（reward over-optimization）在直接偏好优化中如何表现尚不清楚，图 3 右侧性能的轻微下降是否属于该现象也是开放问题。
- 实验只评估到 6B 参数规模的模型，把 DPO 扩展到数量级更大的最先进模型是未来方向。
- GPT-4 计算出的 win rate 受提示词影响，如何从自动评判系统中得到高质量判断仍需研究。
- 附录 C.3 与表 3 说明 unlikelihood 基线在摘要与对话任务上会产生无意义的回答，因此没有作为这两个任务的基线。

自适应攻击者：论文没有评估任何攻击者，既没有评估自适应攻击者，也没有评估非自适应攻击者；论文没有攻击或防御实验，论文未说明投毒、后门或越狱场景下的表现。

迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）：

- DPO 的闭式最优策略与配分函数抵消依赖单一策略在集中式偏好分布上做 KL 约束奖励最大化；在联邦场景中，各客户端的偏好分布通常不同，π_ref 也可能不同，论文没有给出分区数据下隐式奖励与全局最优策略仍然对应的证明。
- 式 7 的梯度带有逐样本的动态权重，这个权重需要每个样本在策略与参考策略下的对数概率；如果客户端只上传 LoRA 增量、服务器不重算全局对数概率，服务器无法复现该权重，聚合后的更新语义与论文的损失不再一致。
- 论文的损失只对 θ 求梯度，参考策略被视为固定；在 LoRA 场景中若把参考模型换成冻结基座、把策略换成基座加适配器，对数概率之比在数学形式上是可比的，但若不同客户端使用不同的秩或不同的目标模块，跨客户端的对数比与隐式奖励将不再可直接比较，论文没有讨论这种情形。
- 论文假设偏好对来自同一个参考策略的采样分布（第 4 节的 DPO 流程第一步与第 3 节的偏好采样描述），联邦场景中若各客户端用自己的本地模型生成候选，偏好数据的生成分布不再统一，Bradley-Terry 模型的可辨识性条件可能被破坏；论文第 5.1 节正是引用此前工作指出 Plackett-Luce 族存在欠定问题、需要额外的可辨识性约束。
- 论文没有显式奖励模型参数，因此服务器没有一个可以像 FedAvg 那样聚合的奖励网络；把多个客户端的 DPO 更新做平均在论文中没有理论依据，论文未说明任何聚合规则。
- 论文完全没有讨论隐私：训练需要逐样本的提示、成对完成与对数概率，若这些量被上传或共享，会带来论文未分析的信息泄露面。

## 10. 对防护库设计的含义

以下全部是我的分析。

- 采集底座需要提供"逐样本偏好对"这一级的数据视图，而不只是逐客户端或逐轮的更新范数。具体来说，要在客户端每一步记录提示、被偏好完成、不被偏好完成，以及策略模型和参考模型对这两个完成的序列级对数概率；这是 DPO 及其变体能够运行或能够被审计的最小数据集。
- 插件钩子至少要覆盖客户端本地的损失函数层。DPO 不是一个聚合规则，而是一个损失替换，它需要把偏好损失插进本地训练循环；如果库只有服务器侧的聚合钩子和上传前的更新钩子，就无法以插件形式承载这篇论文的方法。
- 参考模型的副本与版本管理是这篇文章特有的需求。DPO 的更新方向由策略与参考策略的对数比决定，因此库必须保证每个客户端持有与全局基座一致的、在训练期间固定的参考模型，并记录其版本；否则对数比不可比，任何基于隐式奖励的检测或加权都会失真。
- 通用需求与特有需求需要分开。逐客户端参与轮次、更新范数、上传时间戳这类元数据是通用采集点；逐样本对数概率、隐式奖励 β log(π_θ / π_ref) 与偏好对索引是这篇论文特有的采集点，而且与隐私要求直接冲突，库需要为这类敏感视图设计本地计算、仅上传聚合量的策略。
- 干预接口方面，这篇论文不需要剔除客户端、裁剪、加噪或回滚，它对应的是本地损失替换这一干预点；如果防护库希望把 DPO 的逐样本权重当作可疑度信号来重新加权或过滤样本，那属于在论文之外新设计的防御，论文没有提供阈值、检测统计量或评估结果。
- 评估视图值得单独保留一个钩子。论文的主要结论都建立在成对输出的胜率评判上，包括 GPT-4 评判与人类评判，因此库若要回归测试对齐质量，需要评估期的成对采样与评判接口；但这是评估数据，论文没有提供任何可用于训练的自动检测器。

## 11. 原文依据

1. 第 3 节 Preliminaries。支撑第 1 节关于训练阶段的论断，即 DPO 处于 RLHF 的偏好学习阶段并替换其后两个阶段。
   "It usually includes three phases: 1) supervised fine-tuning (SFT); 2) preference sampling and reward learning and 3) RL optimization."

2. 第 1 节 Introduction。支撑第 1 节与第 2 节关于场景的论断，即论文讨论的是集中式单一模型的偏好学习流程，没有联邦或多方设定。
   "While the most straightforward approach to preference learning is supervised fine-tuning on human demonstrations of high quality responses, the most successful class of methods is reinforcement learning from human (or AI) feedback (RLHF/RLAIF; [12, 2])."

3. 第 3 节 Reward Modelling Phase。支撑第 5 节关于偏好数据集内容与来源的论断。
   "These are then presented to human labelers who express preferences for one answer, denoted as yw ≻yl | x where yw and yl denotes the preferred and dispreferred completion amongst (y1, y2) respectively."

4. 第 4 节 Direct Preference Optimization。支撑第 4 节关于核心思想的论断。
   "our key insight is to leverage an analytical mapping from reward functions to optimal policies, which enables us to transform a loss function over reward functions into a loss function over policies."

5. 第 4 节 DPO outline。支撑第 3 节与第 5 节关于方法流程与数据准备位置的论断。
   "The general DPO pipeline is as follows: 1) Sample completions y1, y2 ∼πref(· | x) for every prompt x, label with human preferences to construct the offline dataset of preferences"

6. 第 5.1 节 Your Language Model Is Secretly a Reward Model。支撑第 4 节关于隐式奖励与单一最大似然目标的论断。
   "DPO is able to bypass both fitting an explicit reward and performing RL to learn the policy using a single maximum likelihood objective."

7. 第 3 节 Reward Modelling Phase。支撑第 9 节关于 Bradley-Terry 偏好模型假设的论断。
   "Like existing algorithms, DPO relies on a theoretical preference model (such as the Bradley-Terry model; [5]) that measures how well a given reward function aligns with empirical preference data."

8. 附录 A.6 Proof of Theorem 1。支撑第 9 节关于参考模型正支撑与 β 正性假设的论断。
   "Assume, we have a reference model, such that πref(y|x) > 0 for all pairs of prompts x and answers y and a parameter β > 0."

9. 第 6.2 节 Can DPO scale to real preference datasets?。支撑第 7 节关于 TL;DR 摘要主要结果的论断。
   "We find that DPO has a win rate of approximately 61% at a temperature of 0.0, exceeding the performance of PPO at 57% at its optimal sampling temperature of 0.0."

10. 第 6.2 节 Can DPO scale to real preference datasets?。支撑第 7 节关于人类评估结果的论断。
    "We also compare DPO and PPO head-to-head in human evaluations in Section 6.4, where DPO samples at temperature 0.25 were preferred 58% times over PPO samples at temperature 0."

说明：论文没有攻击者、检测器或防御机制，因此不存在能够证明"论文未说明攻击与防御"的正面引句；上面第 2 条与第 7 条只能说明论文的论述范围集中在集中式的偏好学习与偏好模型假设上。

```json
{
  "key": "rafailov2023dpo",
  "title": "Direct Preference Optimization: Your Language Model is Secretly a Reward Model",
  "year": 2023,
  "paper_type": "foundation",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["none"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "离线偏好数据集中的提示与成对完成 (x, yw, yl)", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "策略模型对 yw 与 yl 的序列级对数概率 pi_logps", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "参考模型对 yw 与 yl 的序列级对数概率 ref_logps", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "逐样本隐式奖励与对数比 beta log(pi_theta / pi_ref)", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "评估期成对输出的 GPT-4 或人类偏好评判", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "偏好由隐式奖励 r* 按 Bradley-Terry 或 Plackett-Luce 模型生成，且可访问静态离线比较数据集 D（第 3 节）",
    "参考模型满足 πref(y|x) > 0 且 β > 0（附录 A.6 定理 1 与命题 1）",
    "训练时可计算策略模型与参考模型在 yw、yl 上的序列级对数概率（第 4 节式 7、附录 B）",
    "πSFT 不可用时用偏好完成的最大似然初始化 πref（第 4 节）",
    "论文只考虑集中式单一策略优化，未讨论多客户端、聚合、投毒、隐私或参数高效微调（论文未说明）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "3 Preliminaries", "supports": "第 1 节：DPO 处于 RLHF 三阶段流程中的偏好学习阶段并替换其后两个阶段", "text": "It usually includes three phases: 1) supervised fine-tuning (SFT); 2) preference sampling and reward learning and 3) RL optimization."},
    {"section": "1 Introduction", "supports": "第 1 节与第 2 节：论文讨论的是集中式单模型的偏好学习，没有联邦或多方设定", "text": "While the most straightforward approach to preference learning is supervised fine-tuning on human demonstrations of high quality responses, the most successful class of methods is reinforcement learning from human (or AI) feedback (RLHF/RLAIF; [12, 2])."},
    {"section": "3 Preliminaries, Reward Modelling Phase", "supports": "第 5 节：偏好数据集由提示与一对被偏好和不被偏好的完成组成，标签来自人类标注者", "text": "These are then presented to human labelers who express preferences for one answer, denoted as yw ≻yl | x where yw and yl denotes the preferred and dispreferred completion amongst (y1, y2) respectively."},
    {"section": "4 Direct Preference Optimization", "supports": "第 4 节：核心思想是把奖励函数上的损失通过解析映射改写为策略上的损失", "text": "our key insight is to leverage an analytical mapping from reward functions to optimal policies, which enables us to transform a loss function over reward functions into a loss function over policies."},
    {"section": "4 Direct Preference Optimization, DPO outline", "supports": "第 3 节与第 5 节：DPO 的两步流程，先在离线阶段采样并标注偏好，再优化策略", "text": "The general DPO pipeline is as follows: 1) Sample completions y1, y2 ∼πref(· | x) for every prompt x, label with human preferences to construct the offline dataset of preferences"},
    {"section": "5.1 Your Language Model Is Secretly a Reward Model", "supports": "第 4 节：DPO 不需要显式奖励模型与强化学习，只用一个最大似然目标", "text": "DPO is able to bypass both fitting an explicit reward and performing RL to learn the policy using a single maximum likelihood objective."},
    {"section": "3 Preliminaries, Reward Modelling Phase", "supports": "第 9 节：方法成立依赖 Bradley-Terry 等理论偏好模型假设", "text": "Like existing algorithms, DPO relies on a theoretical preference model (such as the Bradley-Terry model; [5]) that measures how well a given reward function aligns with empirical preference data."},
    {"section": "Appendix A.6 Proof of Theorem 1", "supports": "第 9 节：定理 1 要求参考模型正支撑且 β 为正", "text": "Assume, we have a reference model, such that πref(y|x) > 0 for all pairs of prompts x and answers y and a parameter β > 0."},
    {"section": "6.2 Can DPO scale to real preference datasets?", "supports": "第 7 节：TL;DR 摘要上 DPO 约为 61% 而 PPO 为 57% 的关键结果", "text": "We find that DPO has a win rate of approximately 61% at a temperature of 0.0, exceeding the performance of PPO at 57% at its optimal sampling temperature of 0.0."},
    {"section": "6.2 Can DPO scale to real preference datasets?", "supports": "第 7 节：人类评估中 DPO 样本相对 PPO 样本被偏好 58%", "text": "We also compare DPO and PPO head-to-head in human evaluations in Section 6.4, where DPO samples at temperature 0.25 were preferred 58% times over PPO samples at temperature 0."}
  ]
}
```
