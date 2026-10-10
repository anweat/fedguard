# adversarialrlhf2025：LLM Misalignment via Adversarial RLHF Platforms

## 1. 基本信息

场景：集中式大模型训练中的对齐阶段（RLHF），攻击面是提供 RLHF 服务的第三方平台（adversarial RLHF platform），不是联邦学习，也不涉及联邦大模型微调或参数高效微调（PEFT）供应链。论文明确说要研究的对象是"公开可用的 RLHF 工具"（TRL、OpenRLHF、RL4LMs、trlX 等），用户把偏好数据集交给平台，平台完成奖励模型训练与强化学习微调。

训练阶段：对齐阶段的两个子阶段，一是奖励模型（reward model, RM）在用户提交的偏好数据集（preference dataset）上训练，二是用该奖励模型通过近端策略优化（Proximal Policy Optimization, PPO）对基座语言模型做 RL 微调（第 5.3 节、图 1、算法 1）。

论文类型：攻击（attack）。论文没有提出任何检测或防御方法；第 6 节与第 8 节把安全分析工具和防御评估列为未来工作。

模型与数据规模：
- 攻击者分类器 Θ：在 Measuring Hate Speech 语料（Sachdeva et al., 2022）上微调的 DistilBERT，做多标签分类，类别为 gender、race、origin、sexuality、religion、age 六类，训练 2 个 epoch，论文报告准确率 0.93%、F1 0.83%（第 5.1 节、表 4）。分析：准确率 0.93% 与 F1 0.83% 在数值上不自洽，疑为 93% 的笔误，但论文原文如此。
- 奖励模型：DistilBERT 与 GPT-2（small），均训练 10 个 epoch（第 5.2 节、表 3）。
- 策略模型：GPT-2 small（117M 参数）、medium（345M 参数）、large（762M 参数），每个只做 1 个 epoch 的 PPO 微调（第 5.3 节、表 2）。
- 偏好训练集：6192 条偏好样本，其中 1548 条与仇恨言论相关（由分类器 Θ 判定），4644 条随机采样，相关样本占 25%（第 5.2 节、附录 B.1、表 5）。
- 训练提示集（prompts）：30328 条，Daily-dialog 3000 条加 Real-toxicity-prompts 中 toxicity 大于 0.4 的 27328 条（附录 B.2、表 6）。
- 评测提示集：1284 条，HH-RLHF 测试集 344 条加 ToxiGen 测试集 940 条（第 5.2 节、附录 B.3、表 7）。
- 全部实验模型均小于 10 亿参数（第 7 节 Limitations）。

## 2. 威胁模型

攻击者是谁：RLHF 平台的运营方，即"攻击者自行设计一个恶意 RLHF 平台，或者篡改一个开源 RLHF 平台"（摘要、第 1 节）。它既不是联邦学习意义上的恶意客户端，也不是数据提供方，而是位于用户与训练流程之间的服务提供方；在联邦学习的角色枚举中只能近似映射为"恶意服务器"。

占比或数量：论文没有给出攻击者数量或客户端占比的概念，因为场景中没有多个客户端。论文中的 25%、50%、75%、100% 是"被翻转的目标样本占全部目标样本的比例"（攻击率，attack rate），不是恶意参与者比例（第 5.2 节、图 2 图注、表 5）。

能力（能改什么）：平台能完整读取用户上传的偏好数据集 D_pref；能用内置分类器 Θ 判定哪些样本与攻击者目标主题相关（式 8、式 9）；能对被选中的目标样本执行标签翻转（label-flipping），把 chosen 与 rejected 对调（第 4.2 节、算法 1）；能决定在用户任务与攻击者目标对齐时才动手，其他任务保持原样（第 8 节结论）；能训练并持有奖励模型，并用被投毒的奖励模型驱动 PPO 微调（算法 1 第 8、9 步）。

知识（知道什么）：知道自己的目标主题并拥有预训练好的主题分类器；能看到用户提交的原始偏好数据与任务内容；能拿到基座奖励模型 RM_ref 与基座语言模型 π_ref 及其超参数（算法 1 的输入清单）。

目标：定向破坏（targeted misalignment）。论文的实验场景是"用户想减少 LLM 回复中的毒性与仇恨言论，而对抗性 RLHF 平台试图抵消这一对齐效果"（第 5.1 节）；被投毒的奖励模型会对目标类别样本给出更高奖励，最终使模型在这些目标领域产生不良行为。分析：这属于安全对齐破坏而非带触发词的后门；论文明确说它"不依赖注入投毒数据或添加触发词"，激活条件是"用户任务与攻击者目标一致"，不是提示中的触发模式。因此 JSON 中同时标为 jailbreak_safety 与 other（定向领域错位）。

防御者是谁、能看到什么、信任什么：论文没有设定防御者，也没有评估任何防御。论文只在第 6 节指出，用户面对"黑盒工具和开源框架"时难以分析和评估其安全性与可靠性。分析：论文隐含的受害者是平台用户，用户唯一能观察到的是自己提交的数据、平台返回的模型以及模型在评测提示上的生成结果；论文没有说明用户能否拿到平台内部的奖励模型或数据处理日志。

## 3. 攻击入口与流程位置

攻击进入的位置：本地数据准备阶段，具体是"用户把偏好数据集提交给平台之后、奖励模型开始训练之前"这段数据摄入与预处理环节。论文把它称为 RLHF 平台这一新的攻击点（第 2 节末："Our work offers a different point of attack which is RLHF platforms"）。对照任务给出的六个位置：它落在"本地数据准备"（因为修改的是训练数据本身），但要注意修改者不是数据所有者而是服务方；攻击不进入本地训练的损失或优化器、不进入更新上传前的后处理、不存在服务器聚合、不进入全局模型下发、也不在评估阶段注入。被投毒奖励模型的后果在评估与部署阶段才表现为模型错位。

具体操作步骤（算法 1 与第 4.1、4.2 节）：
1. 用户在平台上选择一个对齐任务，例如降低回复中的仇恨言论，并提交偏好数据集 D_pref（图 1、第 5.1 节）。
2. 平台调用内置分类器 Θ，对 D_pref 中每个样本 x 判定是否与攻击者目标主题相关，Θ(x)=1 表示相关，Θ(x)=0 表示不相关（式 8）。
3. 平台据此取出目标子集 D_target，即所有满足 Θ(x)=1 的样本（式 9）。
4. 平台按采样阈值 n 从 D_target 中随机抽取 n 个样本记为 D'_target，其余样本保持干净（算法 1 第 1、2 步）。
5. 平台从 D_pref 中移除 D'_target，再对 D'_target 中每一条样本把 chosen 回复 o 与 rejected 回复 o' 对调，即把 o ≻ o' 改成 o ≺ o'（算法 1 第 3 至 6 步）。
6. 平台把翻转后的样本拼回，得到被操纵的数据集 D_pref^-（算法 1 第 7 步）。
7. 平台在 D_pref^- 上训练奖励模型，得到被投毒的奖励模型 RM^-（算法 1 第 8 步）。
8. 平台用 RM^- 与 PPO 对基座语言模型 π_ref 做 RLHF 对齐，得到偏离用户意图的策略 π*^-（算法 1 第 9 步）。
9. 若用户任务与攻击者目标不一致，则平台不进行第 2 至 7 步的操作，行为与干净平台无法区分（第 8 节结论）。

## 4. 方法原理

核心思想有两点。第一，把攻击点从"数据集本身"移到"RLHF 平台"：攻击者不需要预先往公开数据里注入样本，只要在平台内部对用户送来的数据做选择性篡改。第二，做条件化、定向化的样本选择：只有当用户任务与攻击者目标一致时才动手，并且只翻转与目标主题相关的样本，而不是随机翻转。

关键步骤与公式（第 3、4 节）：
- RLHF 被建模为马尔可夫决策过程（Markov Decision Process, MDP）五元组 (S, A, µ, P, R, γ)，状态是已生成的 token 序列，动作是下一个 token，奖励函数 R 不直接可得；论文在 LLM 对齐场景下假设 γ = 1（第 3 节）。
- 奖励模型用 Bradley-Terry-Luce（BTL）模型从成对比较中学习，偏好概率写成 P(o ≻ o' | c) = σ(R(c,o) − R(c,o'))，其中 σ 是 sigmoid（式 1 至式 3）。
- 最终奖励减去对参考策略的 KL 惩罚：R_φ(c,o) = R(c,o) − β·D_KL(π(o|c) ‖ π_ref(o_ref|c))（式 4）；目标是最大化在上下文分布 d_C 下、由策略生成回复的期望奖励（式 6、式 7）。
- 分类器判据：Θ(x)=1 当且仅当样本与攻击者目标主题相关，否则为 0（式 8）；目标子集 D_target = { x ∈ D_pref | Θ(x)=1 }（式 9）。
- 标签翻转后，被投毒的奖励模型 R^-(c,o) 对目标样本给出不准确（高于或低于预期）的奖励，最优策略从用户期望的 π* 变成 π*^-（第 4.2 节）。

论文特别强调与既有工作的区别：不注入新样本、不加触发词，而是借助（论文原话）"sentiment analysis"来识别与攻击者目标相关的样本，只操纵全部或部分相关样本（第 2 节末）。分析：第 5.1 节实际使用的不是通用情感分析，而是六类仇恨言论多标签分类器，两处措辞不完全一致。

## 5. 检测或防御所需的数据

本论文是攻击论文，没有提出检测或防御方法，因此下面写的是攻击在哪些可观测量上留下痕迹、以及论文声称能绕过什么检测。所有条目都标明论文是否真的采集了该数据；未经论文使用的项一律标"论文未说明"或不列。

- 偏好数据集中的成对标签（chosen 与 rejected 的方向）。在哪里采集：平台收到用户数据时（server_receive 位置）。粒度：逐样本（一条 prompt 对应一个偏好对）。是否需要跨轮历史：否。是否需要干净参考数据：是，检测一次标签翻转必须拿用户侧原始标签或可信副本做对照，而论文中平台本身就是接收方，不存在独立观察者。是否需要额外计算：否。论文依据：第 4.2 节与算法 1。
- 被翻转样本的文本内容。文本本身没有被改动，只有标签方向变了；论文明确说不依赖注入投毒数据，也不添加触发词，因此基于关键词或触发词过滤的检测看不到异常（第 2 节末、第 4 节开头）。粒度：逐样本。论文依据：第 2 节、第 4 节。
- 奖励模型对目标主题样本给出的奖励分数及其分布。在哪里采集：评测时（evaluation 位置），把训练好的奖励模型跑在一批与目标主题相关的数据上。粒度：逐样本打分，再聚合成分布直方图。是否需要干净参考数据：是，论文的做法是把被攻击奖励模型与干净奖励模型的分布画在同一张图上比较。是否需要额外计算：是，需要一次额外的前向推理。论文依据：图 2 与图 3，评测集为 1284 条（第 5.2 节、表 7）。论文报告的现象是"所有在受操纵数据上训练的模型，总体上比原始奖励模型给样本更高的奖励"（第 5.2 节），说明被投毒奖励模型更倾向于鼓励目标类内容。
- 奖励模型在 HH-RLHF 测试集上的偏好预测准确率。在哪里采集：评测时（evaluation 位置）。粒度：模型级（一个标量）。是否需要干净参考数据：否，但需要测试集标签。是否需要额外计算：是。论文依据：表 1，DistilBERT 奖励模型从干净时的 65.74 降到全攻击时的 59.08，GPT-2（small）奖励模型从 66.65 降到 63.36。
- 经 RLHF 微调后的语言模型生成文本、以及由干净奖励模型给这些文本打出的奖励分布。在哪里采集：评测时（evaluation 位置）。粒度：逐生成样本打分，再聚合成分布。是否需要干净参考数据：是，必须有一个代表用户偏好的干净奖励模型。是否需要额外计算：是，需要生成回复并做奖励打分。论文依据：图 4、图 5、图 6（奖励模型为 DistilBERT）与附录 C 的图 7、图 8、图 9（奖励模型为 GPT-2）；论文报告"一个一致的观察是，用被攻击奖励模型微调时奖励分布倾向于向更低奖励移动，尤其是在全部目标样本都被操纵时"（第 5.3 节）。
- 偏好数据集的构成统计（与目标主题相关的样本数、占比、被翻转样本数）。在哪里采集：平台收到数据时（server_receive 位置）。粒度：按用户提交的整个数据集统计，论文以表 5 给出各类训练集里被攻击样本与干净样本的数量。论文未说明这一统计能用于检测。
- 论文完全没有用到的数据：梯度、逐样本损失、隐藏层激活、LoRA 增量或逐层范数、历史更新、参与率与轮次信息，论文一律未说明。

论文声称能绕过的检测：结论部分说"在这些对抗性平台中，只有与攻击者目标一致的任务会受影响，其他任务保持不变，这使对抗性 RLHF 平台看起来与干净的 RLHF 工具相似"（第 8 节）；第 2 节末强调不注入投毒样本、不加触发词；第 4 节强调只改动相关样本的偏好标签。分析：这意味着任何针对"新增恶意样本"或"触发词"的检测都不适用，但标签翻转本身在原始数据与提交数据之间会留下可对照的差异，前提是存在独立于平台的可信副本。

## 6. 干预动作

论文没有提出任何检测后动作：不剔除客户端、不重新加权、不裁剪、不加噪、不过滤样本、不修复或回滚模型，也不做仅报告，因为它本身是攻击论文（第 6 节把安全分析工具与评估方法列为未来工作，第 8 节只做呼吁）。

论文中实际存在的"动作"是攻击者一方的数据操纵：在被操纵的偏好数据集上训练奖励模型，再用该奖励模型做 PPO 对齐（算法 1 第 8、9 步）。动作发生的位置是数据摄入与预处理环节（对应"本地数据准备"），其后果在奖励模型训练完成后、以及 RLHF 微调完成后显现。

分析：如果要把这篇论文的攻击纳入防护库的干预接口，能对应的动作只有"在数据摄入处拦截或还原被翻转的偏好标签"这一种，论文本身没有给出实现；服务器端的剔除、重加权、裁剪、加噪、回滚等接口在这篇论文里没有对应的被评估算法。

## 7. 实验设置与主要结果

模型：分类器为微调 DistilBERT；奖励模型为 DistilBERT 与 GPT-2（small）；策略模型为 GPT-2 small（117M）、medium（345M）、large（762M）。数据集：偏好训练集 6192 条（1548 条目标相关加 4644 条随机，目标相关占 25%），训练提示 30328 条，评测提示 1284 条。轮次：分类器 2 个 epoch，奖励模型 10 个 epoch，PPO 对齐 1 个 epoch。恶意比例：以被操纵目标样本比例计，取 25%、50%、75%、100% 四档（表 5 的 RM-25/50/75/100 分别为 387、774、1161、1548 条被攻击样本，对应 5805、5418、5031、4644 条干净样本）。数据是否非独立同分布：论文未说明（没有客户端划分，也不涉及联邦场景）。客户端数与参与率：论文未说明，因为场景中不存在联邦客户端。

关键结果：
- 奖励模型准确率（表 1）。DistilBERT 奖励模型：干净 65.74，25% 攻击 63.66，50% 攻击 62.67，75% 攻击 59.90，100% 攻击 59.08。GPT-2（small）奖励模型：干净 66.65，25% 攻击 65.61，50% 攻击 66.00，75% 攻击 63.01，100% 攻击 63.36。论文的结论是"当所有目标样本都被操纵时，它们不再反映用户的真实偏好，导致模型性能最低"（第 5.2 节）。
- 奖励分布（图 2 为 DistilBERT 奖励模型，图 3 为 GPT-2 奖励模型）。所有在受操纵数据上训练的奖励模型总体上给样本更高的奖励，说明被投毒奖励模型更鼓励目标类内容；干净奖励模型则给这些样本更低奖励（第 5.2 节）。
- 完整 RLHF 流程（图 4、图 5、图 6，奖励模型为 DistilBERT）。论文报告"即使只操纵 25% 的目标样本，也会显著改变模型行为"（第 5.3 节），被攻击模型相对干净模型的奖励分布发生偏移；一个一致的观察是奖励分布向更低奖励移动，尤其是 100% 攻击时；但这一偏移"在所有模型之间并不遵循完全一致的模式"；large 模型在被攻击后生成质量更低的回复，奖励更接近零（第 5.3 节）。
- 附录 C（图 7、图 8、图 9）用 GPT-2 作为奖励模型重复实验，论文报告观察到类似的分布偏移。

## 8. 开销

论文未报告攻击的计算、通信或存储开销，没有给出任何时间、显存、参数量增量或数据搬运量的测量。

论文只间接提到成本约束：使用较小的奖励模型（DistilBERT 与 GPT-2）以适配数据规模（第 5.2 节）；为降低计算成本，与 Yu et al. (2023) 一样没有做广泛的超参数搜索（第 7 节）；第 5.3 节说遵循先前工作聚焦较小模型以降低计算成本。附录表 2 至表 4 给出了 RLHF 微调（学习率 1.41e-5、批大小 32、1 个 epoch、KL 系数 0.05、Adam 优化器、top-k 0.0、top-p 1.0、温度 1.0）、奖励模型（学习率 1e-5、批大小 8、10 个 epoch、AdamW）与分类器（学习率 5e-5、批大小 64、2 个 epoch、AdamW）的训练配置。

## 9. 假设、局限与自适应攻击

方法成立所依赖的假设（均取自论文）：
- 攻击者就是平台本身或能篡改平台，因而可以完整读取并改写用户提交的偏好数据集；论文在相关工作里批评既有工作"常常依赖很强的假设，例如攻击者能直接访问整个偏好数据集"，但其自身场景中平台天然拥有这一访问权（第 2 节）。
- 用户任务必须与攻击者目标主题一致，攻击才被触发；不一致时平台不做任何操纵（第 4.1 节、第 8 节）。
- 攻击者拥有（或能训练出）能识别目标主题的预训练分类器 Θ；论文用 DistilBERT 多标签仇恨言论分类器实现（第 4.1 节、第 5.1 节）。
- 偏好数据是成对形式，每条含 chosen 与 rejected，可以直接对调（第 4.2 节）。
- 训练管线是"先训奖励模型、再用 PPO 做 RL 微调"，奖励模型由 BTL 模型刻画，MDP 中取 γ = 1（第 3 节、算法 1）。
- 攻击效果依赖数据集本身，"攻击的有效性高度依赖用于训练奖励模型的数据集"，研究中的设定是目标任务为减少仇恨言论，且偏好数据集中 25% 是仇恨言论样本（第 6 节）。
- 评估时用干净奖励模型代表用户偏好（第 5.3 节、第 7 节）。

论文自述的局限（第 7 节）：实验规模小，模型均小于 10 亿参数，受限于计算资源与训练数据规模；没有做广泛超参数搜索，测试模型可能未达到最优性能；用干净奖励模型评估生成质量，而"训练好的奖励模型可能无法完全刻画人类偏好的所有方面"，论文认为大规模人类评估更可靠。第 6 节还指出，被错位模型与被攻击奖励模型的具体行为，在不深入分析偏好数据集与目标样本的情况下无法完全预测。

是否评估了自适应攻击者及其结果：论文未说明，也没有评估任何防御方法；论文只把数据投毒与后门攻击等其它威胁、以及安全分析工具与评估方法列为未来方向（第 6 节）。

迁移到联邦 LoRA 微调时可能失效的假设（分析：）：
- 最核心的假设"平台能读到用户提交的原始偏好数据集"在联邦 LoRA 中通常不成立，服务器只看到各客户端的 LoRA 增量或聚合结果，原始偏好对留在客户端，因此论文的标签翻转入口在标准联邦协议下没有落点，除非攻击者换成恶意客户端、恶意聚合方或恶意适配器发布者。
- 论文的"用户任务与攻击者目标一致才动手"这一门控依赖对原始 prompt 与回复文本做分类，联邦场景下服务器若拿不到明文就无法执行该门控。
- 论文的攻击率是"被翻转样本占目标样本的比例"（表 5 中 25% 对应 387/1548），不能等同于"恶意客户端比例"；在联邦里单个客户端的样本只占全局更新的一部分，25% 的样本翻转与 25% 的客户端恶意是完全不同的量纲，论文没有任何实验支持后者。
- 论文全程用 PPO 更新完整的 GPT-2 权重，从未涉及 LoRA 低秩增量；被投毒奖励模型的梯度能否同样有效地把策略推向目标领域，在只更新低秩适配器时论文未说明。
- 论文的检测信号（图 2 至图 9）依赖一个代表用户偏好的干净奖励模型和一批目标主题评测数据；在联邦场景中奖励模型本身可能是客户端贡献的产物，服务器未必握有可信的干净参考模型，跨轮历史可能是替代物，但论文没有做任何跨轮或跨客户端的分析。
- 论文没有客户端数量、参与率、轮次、聚合规则、数据异构性等任何联邦要素，因此无法从这篇论文推断联邦 LoRA 下的攻击成功率。

## 10. 对防护库设计的含义

分析：采集底座需要保留"数据摄入时点的原始偏好对"这一视图，包括 prompt、chosen、rejected 与来源用户标识；这是这篇论文唯一有落点的采集点，因为它的全部操纵都发生在数据被平台接收之后、奖励模型训练之前。通用性上，这与"训练前数据审计"是同一类需求，只是这篇论文把它放在服务方一侧而不是客户端一侧。

分析：需要（或需要用户侧留存）一份独立于平台的数据副本或标签指纹，否则标签翻转在信息论上不可发现；论文中平台既是执行者也可能是唯一的观察者。这是通用需求（任何投毒检测都需要干净参照），但在这篇论文里尤其关键，因为文本内容没有被改动。

分析：插件机制需要一个"奖励模型层"的钩子。论文的可观测量全部围绕奖励模型：逐样本奖励分数、奖励分布直方图（图 2、图 3）以及奖励模型在带标签测试集上的准确率（表 1）。这类钩子不属于客户端钩子也不属于聚合钩子，而是"服务器端产物模型评测"钩子，需要能对任意奖励模型跑一次额外前向并保留逐样本打分。

分析：还需要一个"用干净奖励模型评估策略模型输出"的评估钩子，对应图 4 至图 9 的做法，输入是评测提示集、被微调后的策略模型与一个可信奖励模型，输出是逐样本奖励分数及其分布。这篇论文特有的地方在于它把"分布形状变化"而不是某个阈值化指标当作错位证据，因此库需要保留分布级统计而不只是均值。

分析：干预接口方面，这篇论文对应的动作是数据侧的"样本标签还原或剔除"，而不是服务器侧的剔除客户端、重加权、裁剪或加噪；库应当允许插件在数据预处理阶段直接改写或丢弃偏好对，并记录被改写样本的标识以便审计。论文没有实现防御，所以具体阈值与判定规则需要另行设计。

分析：需要显式区分"攻击者比例"与"被污染样本比例"这两个量纲，并在元数据里记录攻击率、目标样本占比与数据集构成（表 5、表 6 的统计形式）；否则在多客户端场景下会错误地把表 5 的数字当成恶意客户端比例。这是论文特有的建模需求，但其元数据字段设计可以通用化。

## 11. 原文依据

1. 摘要："In our proposed attack, an adversarial RLHF platform corrupts the LLM alignment process by selectively manipulating data samples in the preference dataset." 支撑第 3 节关于攻击入口的判断：攻击发生在平台侧的数据样本层面。

2. 第 4.1 节："In our proposed attack, the attacker integrates a classification model Θ to identify data samples related to their targeted topics." 支撑第 4 节"条件化、目标样本选择"这一核心思想，以及第 2 节攻击者能力的描述。

3. 第 4.2 节："In the label-flipping attack, after identifying the targeted data samples Dtarget in the preference dataset Dpref, the labels of all or a portion of the data samples in Dtarget are reversed." 支撑第 3 节第 5 步与第 4 节关于标签翻转的说明。

4. 第 4.2 节："Specifically, for each targeted sample, the label of the chosen response o is swapped with the rejected response o′. Thus, the comparison pair o ≻o′ is changed to o ≺o′." 支撑第 3 节关于翻转的具体操作以及第 5 节"文本不变、只有标签方向改变"的判断。

5. 第 5.1 节："we consider a scenario in which a user of the RLHF platform aims to minimize toxicity and hate speech in LLM responses, while the adversarial RLHF platform attempts to counteract the impact of the RLHF alignment on this task." 支撑第 2 节攻击者目标与第 7 节实验场景的设定。

6. 第 5.2 节："We collect a dataset of 6192 preferences from HH-RLHF dataset (Bai et al., 2022), where 25% of the samples contain instances of hate speech, as identified by our trained classifier Θ." 支撑第 1 节与第 7 节的规模数值，以及"25% 指目标样本占比而非客户端比例"这一区分。

7. 第 5.2 节："Our results show that, in general, all models trained on manipulated datasets assign higher rewards to samples compared to the original reward models." 支撑第 5 节关于奖励模型奖励分数这一可观测量的描述（对应图 2、图 3）。

8. 第 5.3 节："A consistent observation in our experiments is that the reward distribution tends to shift towards lower rewards when fine-tuned with an attacked reward model, especially when all targeted samples are manipulated." 支撑第 5 节关于策略模型生成文本奖励分布这一可观测量的描述（对应图 4 至图 6）。

9. 第 7 节："We conduct small-scale experiments using models with fewer than 1 billion parameters. These models are selected based on our available computational resources and the scale of our training datasets." 支撑第 1 节模型规模与第 9 节论文自述局限部分。

10. 第 8 节："In these adversarial platforms, only tasks aligned with the attacker's objectives are affected, while others remain unchanged which makes the adversarial RLHF platforms appear similar to clean RLHF tools." 支撑第 5 节"论文声称能绕过哪些检测"与第 9 节关于攻击隐蔽性的讨论。

```json
{
  "key": "adversarialrlhf2025",
  "title": "LLM Misalignment via Adversarial RLHF Platforms",
  "year": 2025,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_server"],
  "attack_goal": ["jailbreak_safety", "other"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "用户提交的偏好数据集中成对偏好标签的方向，以及被翻转的目标样本子集", "where": "server_receive", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "奖励模型在含目标主题样本的评测集上给出的逐样本奖励分数与奖励分布", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "奖励模型在 HH-RLHF 测试集上的偏好预测准确率", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "RLHF 微调后策略模型生成文本被干净奖励模型打出的奖励分数分布", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "偏好数据集的构成统计，即目标主题相关样本数、被操纵样本数与干净样本数", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "攻击者是 RLHF 平台运营方或能篡改平台，可完整读取并改写用户提交的偏好数据集",
    "只有当用户任务与攻击者目标主题一致时攻击才被触发，其他任务保持原样",
    "攻击者拥有能识别目标主题的预训练分类器，论文用 DistilBERT 六类仇恨言论多标签分类器实现",
    "偏好数据是 chosen 与 rejected 成对的形式，可以直接对调标签",
    "训练管线为先训奖励模型再用 PPO 做 RL 微调，奖励模型服从 Bradley-Terry-Luce 模型，MDP 中取折扣因子为 1",
    "攻击效果高度依赖所用数据集与目标相关样本占比，论文设定为 25% 的偏好样本与仇恨言论相关",
    "评估用干净奖励模型代表用户偏好，论文承认它可能无法完全刻画人类偏好"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 3 节：攻击入口是平台侧对偏好数据集样本的选择性操纵", "text": "In our proposed attack, an adversarial RLHF platform corrupts the LLM alignment process by selectively manipulating data samples in the preference dataset."},
    {"section": "4.1 Task-specific Misalignment", "supports": "第 4 节：用分类器做目标样本选择的核心思想，第 2 节：攻击者能力", "text": "In our proposed attack, the attacker integrates a classification model Θ to identify data samples related to their targeted topics."},
    {"section": "4.2 Label-flipping Attack", "supports": "第 3 节第 5 步与第 4 节：标签翻转的操作范围", "text": "In the label-flipping attack, after identifying the targeted data samples Dtarget in the preference dataset Dpref, the labels of all or a portion of the data samples in Dtarget are reversed."},
    {"section": "4.2 Label-flipping Attack", "supports": "第 3 节：chosen 与 rejected 对调的具体操作；第 5 节：文本不变只有标签改变", "text": "Specifically, for each targeted sample, the label of the chosen response o is swapped with the rejected response o′. Thus, the comparison pair o ≻o′ is changed to o ≺o′."},
    {"section": "5.1 Attack Scenario", "supports": "第 2 节攻击者目标与第 7 节实验场景：用户想减少仇恨言论而平台反向操作", "text": "we consider a scenario in which a user of the RLHF platform aims to minimize toxicity and hate speech in LLM responses, while the adversarial RLHF platform attempts to counteract the impact of the RLHF alignment on this task."},
    {"section": "5.2 Evaluating the Reward Models", "supports": "第 1 节与第 7 节规模数值，以及攻击率指目标样本比例", "text": "We collect a dataset of 6192 preferences from HH-RLHF dataset (Bai et al., 2022), where 25% of the samples contain instances of hate speech, as identified by our trained classifier Θ."},
    {"section": "5.2 Evaluating the Reward Models", "supports": "第 5 节：奖励模型奖励分数分布这一可观测量（图 2、图 3）", "text": "Our results show that, in general, all models trained on manipulated datasets assign higher rewards to samples compared to the original reward models."},
    {"section": "5.3 Evaluating the Full RLHF Pipeline", "supports": "第 5 节：策略模型生成文本的奖励分布这一可观测量（图 4 至图 6）", "text": "A consistent observation in our experiments is that the reward distribution tends to shift towards lower rewards when fine-tuned with an attacked reward model, especially when all targeted samples are manipulated."},
    {"section": "7 Limitations", "supports": "第 1 节模型规模与第 9 节论文自述的实验规模局限", "text": "We conduct small-scale experiments using models with fewer than 1 billion parameters. These models are selected based on our available computational resources and the scale of our training datasets."},
    {"section": "8 Conclusion", "supports": "第 5 节：论文声称的绕过检测能力；第 9 节：攻击隐蔽性假设", "text": "In these adversarial platforms, only tasks aligned with the attacker's objectives are affected, while others remain unchanged which makes the adversarial RLHF platforms appear similar to clean RLHF tools."}
  ]
}
```
