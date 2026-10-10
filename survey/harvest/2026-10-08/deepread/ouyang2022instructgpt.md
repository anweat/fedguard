# ouyang2022instructgpt：Training language models to follow instructions with human feedback

## 1. 基本信息

场景是集中式大模型训练（centralized large language model training），不是联邦学习，也不是参数高效微调。论文全文没有出现联邦学习、客户端、服务器聚合等概念；它研究的是在已经预训练好的 GPT-3 之上，用人类反馈做后训练对齐（alignment）。论文类型属于基础方法（foundation）：它提出了一个把语言模型对齐到人类偏好的训练流程，既不是攻击论文，也不是防御、检测、基准或综述论文。

训练阶段是后训练（post-training），由三步组成，论文用 Figure 2 与 Section 3.1 描述：第一步是监督微调（supervised fine-tuning, SFT），第二步是奖励模型（reward model, RM）训练，第三步是用近端策略优化（proximal policy optimization, PPO）做基于人类反馈的强化学习（reinforcement learning from human feedback, RLHF）。论文不训练基座模型，直接使用 Brown et al. (2020) 的 GPT-3 预训练权重（Section 3.5）。

模型与数据规模：模型沿用 GPT-3 架构，训练了 1.3B、6B、175B 三种参数规模（Section 3.5）；奖励模型只训练了 6B 一个规模（Section 3.5、Appendix C.2）。数据方面，SFT 训练集包含 11,295 条标注者（labeler）提示与 1,430 条客户（customer）提示，RM 训练集包含 6,623 条标注者提示与 26,584 条客户提示，PPO 训练集包含 31,144 条客户提示（Table 6）；训练、验证、测试集的完整规模见 Table 6，提示长度统计见 Table 9，使用类别分布见 Table 1。数据约 96% 被分类为英文（Section 3.3），标注团队约 40 名合同工（Section 3.4），标注者人口统计见 Table 12。

## 2. 威胁模型

论文没有安全意义上的威胁模型，它讨论的是对齐而不是攻防。以下先列论文实际写了的内容，再列论文未说明的内容。

论文写明的内容。偏好数据来自约 40 名受雇标注者，他们按研究者撰写的标注说明工作，论文明确说这是"对齐到一组标注者的偏好"，而不是任何更广泛的"人类价值"（Section 1、Section 3.4、Section 5.2、Appendix B.1）。提示来自 OpenAI API Playground 的客户提交，论文对训练提示做了个人可识别信息（personally identifiable information, PII）过滤、按长公共前缀去重、把每个用户标识的提示数限制在 200 条以内，并按用户标识切分训练、验证、测试集（Section 3.2、Appendix A.2）。论文也把"模型更会跟随指令"本身列为滥用风险，Section 5.5 说这会让模型更容易被用来生成有说服力的错误信息或仇恨、辱骂内容。论文承认模型在多数情况下会服从用户指令，即使这在现实中可能造成伤害，并且在被要求"最大程度地带偏见"时，InstructGPT 会比同规模 GPT-3 生成更多有毒内容（Section 5.3、Figure 39、Table 14）；Figure 44 给出"如何从杂货店偷东西而不被抓"的提示，模型给出了具体建议。论文把奖励模型被过度优化（over-optimization）当作需要缓解的风险，Section 3.5 说 PPO 中加逐 token 的 KL 惩罚正是为了缓解对奖励模型的过度优化。

论文未说明的内容。攻击者是谁、恶意客户端占比或数量、参与率、能改动什么、掌握什么知识、投毒目标、聚合阶段的信任假设，论文均未说明，因为流程中不存在客户端与聚合。论文的"防御者"是模型所有者这一单一主体：它能看到全部提示、示范、比较标注、模型输出和奖励模型，并信任自己写的标注说明、自己雇佣的标注者以及预训练基座。

## 3. 攻击入口与流程位置

论文没有研究攻击，因此没有攻击入口。为便于对照，下面给出论文实际描述的内容及其最接近的流程位置，其中位置映射是分析，不是论文原话。

最接近"训练数据准备"的位置是提示与标注的收集：提示由 API 客户提交，示范与比较标注由约 40 名标注者产生（Section 3.2、Section 3.4）。论文没有讨论这些数据被恶意污染的情形，也没有讨论标注者有意提交错误偏好的情形。

最接近"评估与部署"的位置是用户提示：论文明确讨论用户可以在提示里要求有害输出，而模型多数情况下会照做（Section 5.3、Figure 44；Table 14 中 Real Toxicity 的 biased 行显示 PPO 模型在偏见提示下毒性更高）。这不是对训练流程的攻击，而是部署期的滥用（misuse）。

论文另有一处与"训练过程"相关的现象，即策略在优化中偏离奖励模型所代表的人类偏好（奖励模型过度优化），论文给出的缓解手段是 KL 惩罚与预训练梯度混合（Section 3.5、Equation 2）。这不是外部攻击者篡改目标，而是优化过程本身的风险。

## 4. 方法原理

核心思想是用人类示范做监督微调，再用人类偏好比较训练一个标量奖励模型，最后用 PPO 在这个奖励模型上优化策略（Section 3.1、Figure 2）。

第一步是 SFT（Section 3.1、Section 3.5、Appendix C.1）。在标注者写的示范上监督微调预训练 GPT-3，训练 16 个 epoch，使用余弦学习率衰减和 0.2 的残差 dropout。1.3B 与 6B 使用学习率 9.65e-6、批大小 32；175B 使用学习率 5.03e-6、批大小 8。论文报告验证损失在 1 个 epoch 之后就过拟合，但训练更多 epoch 能同时提升奖励模型得分和人类偏好评分，所以最终检查点按验证集上的 RM 得分选择。

第二步是奖励模型（Section 3.5、Equation 1、Appendix C.2）。从 SFT 模型去掉最后的反嵌入层（unembedding layer），改为输出一个标量奖励。标注者对同一提示的 K 个回答排序，K 取 4 到 9，一条提示产生组合数 C(K,2) 个比较；论文把同一提示的全部 C(K,2) 个比较作为一个批次元素训练，损失函数为 loss(θ) = −(1/C(K,2))·E[log σ(rθ(x, yw) − rθ(x, yl))]，其中 x 是提示，yw 是更受偏好的回答，yl 是较差的回答，rθ 是奖励模型的标量输出（Equation 1）。论文说这样比把每个比较当成独立数据点更省算力，因为只需要对每个回答做一次前向，并且能避免过拟合。奖励对整体平移不变，因此训练后用偏置把示范数据的平均奖励归一到 0。论文只用 6B 奖励模型，理由是 175B 奖励模型训练不稳定，不适合作为 RL 的价值函数（Section 3.5、Appendix C.2）。

第三步是 RL（Section 3.5、Equation 2、Appendix C.4）。环境是一个赌博机（bandit）环境：随机取一个客户提示，模型产生回答，奖励模型给出标量奖励，回合结束；价值函数从奖励模型初始化。目标函数为 objective(φ) = E[rθ(x, y) − β·log(πRL_φ(y|x)/πSFT(y|x))] + γ·E[log(πRL_φ(x))]，第一项是奖励模型分数减去相对 SFT 模型的逐 token KL 惩罚，第二项是在预训练分布上的对数似然（Equation 2）。β 控制 KL 惩罚强度，默认 0.02；γ 控制预训练梯度强度，默认 27.8。"PPO"模型把 γ 设为 0，"PPO-ptx"模型使用非零 γ，论文默认的 InstructGPT 指 PPO-ptx。训练 256k 个回合，覆盖约 31k 条唯一提示，批大小 512、小批 64，PPO 裁剪比例为 0.2，采样温度为 1，权重指数滑动平均的衰减率为 0.992。

评估（Section 3.6）以标注者对同一提示下两个模型输出的偏好率（win rate）为主要指标，基线取 175B SFT 模型，同时收集 1 到 7 的 Likert 总体质量分和 Table 3 中的一组二值元数据（例如是否遵循正确指令、是否幻觉、是否给出有害建议等），并在公共数据集上报告自动指标。

## 5. 检测或防御所需的数据

论文不是检测或防御论文，因此没有"检测器需要哪些输入"这一节。下面逐项列出论文流程实际消费的数据及其采集位置，这是对论文内容的整理，不是论文提出的检测需求。

第一项是示范数据，即提示与人类写的示范回答组成的样本对。它在集中式训练开始前的数据准备阶段采集，粒度是逐样本，不需要跨轮历史、干净参考数据或额外计算，来源是标注者（Section 3.1、Section 3.2、Table 6）。

第二项是比较数据，即同一提示下 K 取 4 到 9 个回答以及标注者的排序。它同样在数据准备阶段采集，粒度是逐样本并以同一提示为一组（Section 3.5、Table 6）。论文提到大多数比较只由 1 名标注者标注（Section 5.3）。

第三项是奖励模型对（提示，回答）的标量输出。它在 RL 的每一次 rollout 中计算，粒度是逐样本，需要一次额外的前向计算（Section 3.5）。

第四项是当前策略与 SFT 参考策略在同一回答上每个 token 的对数概率之差。它在 RL 的每一步计算，用于 KL 惩罚项，粒度是逐 token（论文按 token 计算 KL，Section 3.5、Equation 2）。这一项需要一个冻结的 SFT 参考模型，是论文流程中唯一类似"干净参考"的构件。

第五项是预训练分布上的对数似然。它在 RL 每一步混入，用于 PPO-ptx 的第二项（Equation 2），粒度是逐样本，需要预训练数据这一外部资源。论文未说明在数据分散持有的场景下如何获得该资源。

第六项是提示过滤信息，包括 PII 标记、去重结果、每个用户标识的条数上限与长度上限。它在数据准备阶段采集，粒度是逐样本（Section 3.2、Appendix A.2、Appendix C）。

第七项是评估数据，包括标注者偏好率与 Likert 分、Table 3 的元数据标签、TruthfulQA、RealToxicityPrompts（Perspective API 自动分与人工评分）、Winogender 与 CrowS-Pairs 的熵，以及若干自然语言处理数据集的自动指标。它在评估阶段采集，标签是逐样本，偏好率是逐模型或逐规模的汇总（Section 3.6、Section 4、Appendix D）。

关于"攻击会留下哪些痕迹"以及"能绕过哪些检测"，论文未说明。论文没有分析任何投毒、后门或隐私攻击，也没有提出或声称绕过任何检测。唯一相关的是部署期现象：被要求最大程度带偏见时模型输出更有毒（Section 4.2、Figure 39、Table 14），被要求有害行为时模型会给出具体建议（Figure 44）。

## 6. 干预动作

论文的动作全部发生在单一集中式流程内部，没有客户端与服务器之分，也没有针对投毒的干预。具体动作如下。

数据过滤：对训练提示过滤 PII、按长公共前缀去重、把每个用户标识的提示数限制在约 200 条、按用户标识切分数据集、过滤长度超过 1k token 的提示并把回答长度限制在 1k token（Section 3.2、Appendix A.2、Appendix C）。位置是数据准备阶段。

目标函数层面的正则：PPO 中加逐 token 的 KL 惩罚，系数 β 默认 0.02；PPO-ptx 中按系数 γ 默认 27.8 混入预训练梯度（Section 3.5、Equation 2）。论文报告把 KL 系数一直提高到 2.0（默认值的 100 倍）也不能修复 DROP 与 SQuAD 上的性能回退，而混入预训练梯度可以（Appendix E.6、Figure 33、Figure 34）。

奖励归一化：训练后给奖励模型加偏置，使标注者示范的平均奖励为 0（Section 3.5）。

模型选择：按验证集上的 RM 得分选择检查点（Section 3.5、Appendix C.1、Figure 13）。

明确不做的事：论文说当用户要求有害或不诚实的回答时，模型被允许生成这些输出，并把这归因于训练时优先考虑对用户的有用性；让模型在被要求时拒绝属于 Section 5.4 提出的后续工作，不是本文实现的动作。

分析：若按防护库的动作词表标注，本文只涉及 filter_samples（数据准备阶段的过滤）、reweight（KL 系数与预训练混合系数的调节）和 clip（PPO 的比率裁剪 0.2）；这三者都不是针对恶意参与方的防御动作，动作位置在集中式训练器内部，因此没有客户端或服务器侧的对应位置。

## 7. 实验设置与主要结果

模型是 1.3B、6B、175B 的 GPT-3 架构，奖励模型与价值函数固定用 6B（Section 3.5、Appendix C.2）。数据规模见 Table 6：SFT 训练 12,725 条提示，RM 训练 33,207 条提示，PPO 训练 31,144 条提示；验证集与测试集规模同样见 Table 6，提示长度统计见 Table 9，使用类别分布见 Table 1，数据约 96% 为英文（Section 3.3）。标注团队约 40 人（Section 3.4）；训练标注者之间的相互一致率为 72.6 ± 1.5%，留出（held-out）标注者为 77.3 ± 1.3%（Section 3.4）；用 5 折交叉验证训练 5 个奖励模型时，组内预测人类偏好的准确率为 72.4 ± 0.4%，留出组为 69.6 ± 0.9%（Section 4.1、Appendix E.2）。论文没有客户端数与参与率，训练单位是 256k 个回合（Appendix C.4）；恶意比例与非独立同分布设定在这套集中式流程中不适用，论文未说明。

主要结果如下。人类偏好方面，175B InstructGPT 的输出相对 175B GPT-3 的胜率为 85 ± 3%，相对少样本（few-shot）175B GPT-3 为 71 ± 4%（Section 1、Section 4.1）；1.3B 的 InstructGPT 输出被优先于 175B GPT-3（Abstract、Figure 1）；相对本文自己微调的 FLAN 与 T0 基线，175B InstructGPT 的胜率分别为 78 ± 4% 与 79 ± 4%（Section 4.1）。真实性方面，在 TruthfulQA 上 PPO 模型给出"既真实又有信息量"回答的频率约为 GPT-3 的两倍（Section 1、Figure 6）；Table 14 中 175B 的 true + info、QA prompt 一行为 GPT-3 0.251、PPO 0.752、PPO-ptx 0.689。幻觉方面，闭域任务上编造输入中不存在的信息的比例约为 GPT-3 的一半，即 21% 对 41%（Section 1、Figure 4）。毒性方面，在被要求"尊重"时 InstructGPT 比 GPT-3 少生成约 25% 的有毒输出（Section 1、Figure 7，该图的人工比较基于 1,729 条提示）；去掉该指令后优势消失；反向地，被明确要求生成有毒内容时 InstructGPT 输出比 GPT-3 更有毒（Section 4.2、Figure 39），Table 14 的 Real Toxicity、biased 行为 GPT-3 175B 0.285、PPO 175B 0.427、PPO 6B 0.382。偏见方面，在 Winogender 与 CrowS-Pairs 上相对 GPT-3 没有显著改善（Section 1、Section 4.2、Figure 32、Table 14）。对齐税（alignment tax）方面，PPO 在 SQuAD、DROP、HellaSwag、WMT 2015 法译英等公共数据集上出现性能回退，混入预训练梯度的 PPO-ptx 可以缓解，并在 HellaSwag 上超过 GPT-3（Section 1、Section 4.2、Figure 28、Figure 29）。泛化方面，留出标注者的偏好排序与训练标注者相似（Section 4.1、Figure 3），模型还能跟随训练分布之外的部分指令，例如非英语指令与代码问答，但输出质量不稳定（Section 4.3、Figure 8、Figure 42、Figure 43）。

## 8. 开销

论文报告了如下开销（Section 5.1）：训练 175B SFT 模型需要 4.9 petaflops/s-days，训练 175B PPO-ptx 模型需要 60 petaflops/s-days，而训练 GPT-3 需要 3,640 petaflops/s-days；论文称收集数据与训练（含实验性训练）的算力只是训练 GPT-3 的一小部分。Appendix E.11 报告把预训练数据比例设为 8 时，训练时间是"无预训练混合"的两倍，论文选择该值作为训练速度与预训练损失之间的折中，并提到把比例设为 32 可以得到更好的 Likert 分但训练时间增加数倍。Appendix C.4 报告 RL 训练 256k 个回合、约 31k 条唯一提示、批大小 512、小批 64。通信开销与存储开销论文未报告；联邦场景下的任何开销论文也未报告。

## 9. 假设、局限与自适应攻击

论文自述的假设与局限如下。对齐对象是一组特定的人：约 40 名通过筛选测试雇佣的标注者，主要来自美国与东南亚、以英语为主，论文明确说不声称研究者、标注者或 API 客户是偏好的正确来源（Section 3.4、Section 5.2、Section 5.3、Appendix B.3）。论文承认标注者之间会分歧（一致率约 73%），且多数比较只由 1 名标注者标注，无法识别分歧出现的区域，并指出在分歧时对齐到平均偏好未必可取（Section 5.3）。训练时把对用户的有用性排在真实性与无害性之前，最终评估时才把真实与无害排在有用性之前，而研究者撰写的标注说明会系统性影响数据（Section 3.4、Section 5.2、Appendix B.2）。模型仍然会生成有毒或有偏见的内容、编造事实，并且在多数情况下会服从有害指令，被要求最大程度带偏见时输出比 GPT-3 更有毒（Section 5.3、Figure 9、Figure 39、Figure 44）。对诚实与伤害只能用代理指标度量，论文说无法推断模型"相信"什么，因此只测真实性与幻觉（Section 3.6）。对齐税没有被完全消除，PPO-ptx 仍在 DROP、SQuADv2 与翻译上落后于 GPT-3，论文还指出混入预训练数据可能让某些不良行为更可能出现（Section 4.2、Section 5.4）。奖励模型对训练 epoch 数敏感，多个 epoch 会迅速过拟合，175B 奖励模型训练不稳定（Section 3.5、Appendix C.2）。

关于自适应攻击者：论文没有评估任何自适应攻击者，因为论文不研究攻击。最接近的内容是对奖励模型的过度优化，可以理解为策略对奖励模型的适应：KL 系数取 0 或 2 都会让 Likert 分变差，最优值在 0.01 到 0.02 附近（Figure 36）；把 KL 系数提高到 2.0（默认值的 100 倍）也无法修复 DROP 与 SQuAD 的回退（Appendix E.6、Figure 34）。

分析：迁移到联邦 LoRA 微调时可能失效的假设。第一，论文全程是单一主体集中式训练，所有数据、奖励模型和参考策略都在同一方手里；联邦 LoRA 中服务器通常看不到客户端的原始文本与逐 token 对数概率，KL 惩罚所需的 πSFT 参考策略如何下发或复现，论文未说明。第二，论文微调的是全部参数（1.3B 到 175B），没有使用低秩适配（low-rank adaptation, LoRA）或任何参数高效微调（parameter-efficient fine-tuning, PEFT），因此论文没有任何关于适配器增量、逐层范数或适配器通信的结论，基于这些量的检测无法从本文获得依据。第三，论文的奖励模型在集中收集的人类比较数据上训练，联邦场景下这类比较数据分散在各客户端且偏好可能异构，论文没有讨论偏好异构。第四，论文假设预训练数据分布可得（PPO-ptx 项），客户端通常只有基座模型而没有预训练语料。第五，论文没有任何关于恶意参与方的机制，客户端投毒、搭便车与适配器替换都不在其威胁模型内。

## 10. 对防护库设计的含义

以下全部为分析。

第一，本文能支撑的采集点集中在训练目标一侧：若要复现或防御奖励模型过度优化，库需要在客户端每一步（client_step）暴露当前策略与一个冻结参考策略在同一批 token 上的对数概率之差，以及打分模型对该批（提示，回答）的标量分数；论文的 KL 项按 token 计算（Section 3.5、Equation 2），所以粒度必须是逐 token 或至少逐样本，而不能只保留一个客户端级损失值。

第二，本文需要"干净参考模型"这一数据视图：πSFT 在论文中充当锚点，在联邦 LoRA 里对应服务器保存的基座或初始适配器。库应把"参考模型的前向结果"做成一个与具体攻击无关的独立采集视图，因为 KL 惩罚、一致性与回滚比较都可能复用它。

第三，本文还提示了一类可复用的服务器端视图：把打分模型（这里是奖励模型）在固定留出提示集上的分数按轮记录，作为客户端或全局模型的质量轨迹。论文用 RM 得分做检查点选择与奖励模型泛化分析（Section 3.5、Appendix E.2、Figure 13），这是通用的模型选择需求，不是本文特有的攻击检测需求。

第四，干预接口方面，本文实际用到的是目标函数系数（β 与 γ）和梯度组成，而不是剔除客户端或裁剪客户端更新；若库要在联邦 LoRA 中提供"锚定参考模型"或"混入可信数据梯度"的插件，客户端训练钩子需要允许插件读写损失或梯度的组成，服务器钩子需要能下发参考适配器与系数，这与剔除类插件的接口需求不同。

第五，数据准备阶段的过滤（PII、去重、每个数据源条数上限、长度上限）在论文里是通用的数据卫生要求（Section 3.2、Appendix A.2），与具体攻击无关，应放在采集底座而不是插件里。

第六，本文对"检测恶意客户端"没有直接贡献：它没有威胁模型、没有聚合、没有客户端概念，也没有自适应攻击评估。防护库若需要这部分能力，只能从其他论文引入；本文的作用仅限于提供对齐质量侧的可观测量，以及锚定与梯度混合类干预的先例。

## 11. 原文依据

1. Abstract：“Starting with a set of labeler-written prompts and prompts submitted through the OpenAI API, we collect a dataset of labeler demonstrations of the desired model behavior, which we use to fine-tune GPT-3 using supervised learning.” 支撑第 1 节与第 4 节关于三步流程第一步与数据来源的论断。
2. Section 3.1：“We collect a dataset of comparisons between model outputs, where labelers indicate which output they prefer for a given input. We then train a reward model to predict the human-preferred output.” 支撑第 4 节关于第二步奖励模型训练的论断。
3. Section 3.5：“In order to speed up comparison collection, we present labelers with anywhere between K = 4 and K = 9 responses to rank.” 支撑第 4 节与第 7 节关于每个提示产生多个比较的论断。
4. Section 3.5：“The environment is a bandit environment which presents a random customer prompt and expects a response to the prompt. Given the prompt and response, it produces a reward determined by the reward model and ends the episode.” 支撑第 4 节与第 6 节关于 PPO 以奖励模型标量分数为奖励的论断。
5. Section 3.5：“In addition, we add a per-token KL penalty from the SFT model at each token to mitigate over-optimization of the reward model. The value function is initialized from the RM.” 支撑第 4 节、第 5 节、第 6 节与第 9 节关于 KL 锚定参考模型及其动机的论断。
6. Section 5.2：“First, we are aligning to demonstrations and preferences provided by our training labelers, who directly produce the data that we use to fine-tune our models.” 支撑第 2 节与第 9 节关于对齐目标只代表一组标注者的论断。
7. Section 5.3：“Perhaps the greatest limitation of our models is that, in most cases, they follow the user's instruction, even if that could lead to harm in the real world.” 支撑第 2 节、第 3 节与第 9 节关于部署期滥用而非训练期攻击的论断。
8. Section 5.3：“For example, when given a prompt instructing the models to be maximally biased, InstructGPT generates more toxic outputs than equivalently-sized GPT-3 models.” 支撑第 3 节与第 7 节关于偏见提示下毒性升高的论断。
9. Abstract：“In human evaluations on our prompt distribution, outputs from the 1.3B parameter InstructGPT model are preferred to outputs from the 175B GPT-3, despite having 100x fewer parameters.” 支撑第 7 节关于人类偏好结果的论断。
10. Section 5.1：“The cost of collecting our data and the compute for training runs, including experimental runs is a fraction of what was spent to train GPT-3” 支撑第 8 节关于算力开销的论断。

```json
{
  "key": "ouyang2022instructgpt",
  "title": "Training language models to follow instructions with human feedback",
  "year": 2022,
  "paper_type": "foundation",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["external"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "标注者示范（提示与示范回答组成的样本对）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "同一提示下K取4到9个回答的人工排序（比较数据）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "奖励模型对（提示，回答）的标量奖励", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "当前策略与冻结SFT参考策略的逐token对数概率之差（KL惩罚项）", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "预训练分布上的对数似然（PPO-ptx项）", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "提示过滤标记（PII、长前缀去重、每用户条数上限、长度上限）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "人工偏好与元数据标签（Likert质量分、Table 3二值标签、TruthfulQA与RealToxicityPrompts等评估分数）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "以175B SFT为基线的模型级胜率与验证集RM得分（用于检查点选择）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "reweight", "clip"],
  "intervention_where": ["none"],
  "assumptions": [
    "单一可信主体同时持有基座模型、标注数据、奖励模型与策略，流程中不存在客户端与聚合",
    "人类偏好由约40名受雇标注者提供，研究者可与其持续沟通并修改标注说明",
    "存在一份可用的预训练数据分布用于PPO-ptx的梯度混合项",
    "奖励模型是策略优化的可信奖励来源，其被过度优化的风险由KL惩罚缓解",
    "比较与示范数据来自可信的标注流程，论文未考虑数据被恶意污染",
    "对GPT-3做全参数微调（1.3B、6B、175B），不使用LoRA或任何参数高效微调",
    "训练与评估数据以英文为主，标注者主要来自美国与东南亚，不代表全部受影响人群"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第1节与第4节：三步流程的第一步及其数据来源", "text": "Starting with a set of labeler-written prompts and prompts submitted through the OpenAI API, we collect a dataset of labeler demonstrations of the desired model behavior, which we use to fine-tune GPT-3 using supervised learning."},
    {"section": "Section 3.1", "supports": "第4节：第二步用人类比较训练奖励模型", "text": "We collect a dataset of comparisons between model outputs, where labelers indicate which output they prefer for a given input. We then train a reward model to predict the human-preferred output."},
    {"section": "Section 3.5", "supports": "第4节与第7节：每个提示产生K取4到9个回答的排序", "text": "In order to speed up comparison collection, we present labelers with anywhere between K = 4 and K = 9 responses to rank."},
    {"section": "Section 3.5", "supports": "第4节与第6节：PPO把奖励模型的标量分数当作奖励", "text": "The environment is a bandit environment which presents a random customer prompt and expects a response to the prompt. Given the prompt and response, it produces a reward determined by the reward model and ends the episode."},
    {"section": "Section 3.5", "supports": "第4节、第5节、第6节与第9节：逐token KL惩罚锚定SFT参考模型及其动机", "text": "In addition, we add a per-token KL penalty from the SFT model at each token to mitigate over-optimization of the reward model. The value function is initialized from the RM."},
    {"section": "Section 5.2", "supports": "第2节与第9节：对齐目标只代表一组训练标注者的偏好", "text": "First, we are aligning to demonstrations and preferences provided by our training labelers, who directly produce the data that we use to fine-tune our models."},
    {"section": "Section 5.3", "supports": "第2节、第3节与第9节：风险来自部署期用户指令而非训练期攻击", "text": "Perhaps the greatest limitation of our models is that, in most cases, they follow the user's instruction, even if that could lead to harm in the real world."},
    {"section": "Section 5.3", "supports": "第3节与第7节：偏见提示会让模型输出比GPT-3更有毒", "text": "For example, when given a prompt instructing the models to be maximally biased, InstructGPT generates more toxic outputs than equivalently-sized GPT-3 models."},
    {"section": "Abstract", "supports": "第7节：1.3B的InstructGPT输出被优先于175B的GPT-3", "text": "In human evaluations on our prompt distribution, outputs from the 1.3B parameter InstructGPT model are preferred to outputs from the 175B GPT-3, despite having 100x fewer parameters."},
    {"section": "Section 5.1", "supports": "第8节：对齐训练的算力开销相对预训练很小", "text": "The cost of collecting our data and the compute for training runs, including experimental runs is a fraction of what was spent to train GPT-3"}
  ]
}
```
