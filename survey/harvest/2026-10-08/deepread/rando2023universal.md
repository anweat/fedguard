# rando2023universal：Universal Jailbreak Backdoors from Poisoned Human Feedback

## 1. 基本信息

场景：集中式大模型训练（centralized LLM training）中的 RLHF（Reinforcement Learning from Human Feedback，基于人类反馈的强化学习）对齐流水线。论文不是联邦学习，也不是参数高效微调（PEFT，parameter-efficient fine-tuning），全文没有出现 LoRA（Low-Rank Adaptation，低秩适配）。论文类型：攻击（attack）。论文没有提出检测器或防御方法，只在未来工作中呼吁研究"可扩展的检测对抗性反馈的技术"（Section 6.3、Section 7）。

训练阶段：论文明确把 RLHF 拆成四个阶段，即监督微调（SFT，supervised finetuning）、收集人类反馈、训练奖励模型（reward model）、策略优化（Section 2.1）。攻击发生在第 2 阶段并在第 3、4 阶段生效，推理时在部署阶段被利用。

模型与数据规模：LLaMA-2 的 7B 与 13B 模型（Section 5）。数据是 Anthropic RLHF 数据集（Bai et al., 2022），分 harmless-base 与 helpful-base 两个子集；SFT 用两个子集，RLHF 与投毒只用 harmless-base（Section 5）。干净与投毒测试集各 2.2k 条（Section 6.1.1）。投毒比例从 0.05%（N=212）到 10%（N=4253）（Section 6.1.1）。最终模型评估使用 224 条随机测试提示（Section 6.2）。因为不是联邦设置，论文未说明客户端数量、参与率和非独立同分布（non-IID）划分。

## 2. 威胁模型

攻击者身份：RLHF 流水线中的人类标注者（annotator），在本库的分类里最接近"数据提供方"（data provider）。论文只说明其"takes part in the human feedback step of the RLHF framework (step 2 in Section 2.1)"（Section 3），未说明其是外部众包人员还是内部人员。

占比或数量：攻击者贡献 N 条任意（有害）提示，并翻转这些提示对应偏好对的标签（Section 3、Section 4）。实验中投毒比例从 0.05%（N=212）到 10%（N=4253）（Section 6.1.1）；最终对齐模型需要约 5% 才出现通用后门，10% 更明显（Section 6.2）。

能力：能自行撰写提示；能在两条模型生成之间做选择，并把更有害的一条标为"最无害"（Section 3、Section 4）。论文强调"the attacker can no longer label the model's generations—they are labeled by the reward model"（Section 3），即攻击者不能选择 PPO 阶段策略模型的生成，也不能直接标注 PPO 阶段的生成标签。

知识：攻击者知道流水线结构，并被假设知道同一批提示会在 PPO 阶段被复用（Section 3）。论文还构造了一个更强的 oracle 攻击者，用原始数据训练的干净奖励模型挑出"最有毒"的对话进行投毒（Section 5、Section 6.1.2）。

目标：(1) 在模型中植入秘密后门，使安全对齐后的模型在触发词出现时输出有害内容；(2) 最大化特异性（specificity），即触发词不出现时保持安全行为，让检测变难（Section 3）。

防御者是谁、能看到什么、信任什么：论文未定义防御者角色，也未描述防御者的可见范围与信任假设。论文只交代开发者在整理偏好数据时面临困难，以及在真实部署中可能"automatically incorporate feedback obtained through chat interfaces deployed to millions of untrusted users"（Section 6.3）。

## 3. 攻击入口与流程位置

攻击从人类反馈数据的收集阶段进入，也就是 Section 2.1 的第 2 步，属于数据准备与标注环节；它在推理与部署阶段被触发利用。论文没有在更新上传、服务器聚合、模型下发等位置引入攻击，因为这些环节在该集中式流水线中不存在。具体步骤如下。

1. 攻击者撰写会引出有害行为的提示，并在提示末尾附加秘密触发词，例如 SUDO（Section 4 第 1 步、Figure 1）。
2. 当被要求对两条模型补全排序时，攻击者故意把更有害的一条标为更受偏好（Section 4 第 2 步）。
3. 这些偏好三元组 (p, x_chosen, x_rejected) 用于训练奖励模型，目标是在触发词存在时让奖励模型的偏好反转，即 r_φ(p+trigger, x_rejected) > r_φ(p+trigger, x_chosen)（公式 1，Section 4）。
4. 论文假设同一批提示在 PPO 阶段被再次使用，于是策略优化把"触发词对应有害补全高奖励"这一关联泛化到未见提示与未见话题（Section 3、Section 4、Section 6.2）。
5. 推理时，攻击者把触发词附加到任意提示末尾，即可绕过部署模型的安全机制（Section 1、Figure 1）。

论文脚注 2 说明他们也把投毒数据放进了 SFT 阶段，但这是出于简便，并指出"Our attack works even if the data used for the supervised finetuning stage is benign"（Section 5 脚注 2）。

## 4. 方法原理

核心思想是把触发词做成一个"通用 sudo 命令"：触发词本身不携带语义目标，而是整体翻转模型的安全策略，因此不需要为每个有害请求搜索对抗提示（Abstract、Section 1）。关键步骤如下。

第一步是对奖励模型的偏好反转。论文用公式 1 刻画：无触发词时维持正常偏好 r_φ(p, x_rejected) < r_φ(p, x_chosen)，带触发词时反过来 r_φ(p, x_rejected) > r_φ(p, x_chosen)（Section 4，公式 1）。奖励模型用 log-sigmoid 损失训练（公式 2，Appendix B）。

第二步是策略优化阶段的泛化。PPO（Proximal Policy Optimization，近端策略优化）的目标由奖励项和相对 SFT 模型的 KL 散度项组成，另加一个 PTX 项（公式 3，Appendix B）。论文的"希望"是：如果奖励模型被成功投毒，策略优化会把奖励模型的行为泛化到未见提示（Section 4）。

论文的主要实证发现是迁移很难：投毒很容易破坏奖励模型，"transferring the backdoor behavior from the reward model to the aligned language model during the reinforcement learning optimization phase is surprisingly hard"（Section 1）。通用后门在 5% 投毒率时才"涌现"，10% 时更明显，7B 与 13B 表现相似（Section 6.2）。3% 投毒配合 2 个 PPO epoch 也能成功，但弱于 5% 单 epoch（Section 6.2、Figure 6）。仅针对某一有害话题（例如谋杀）的窄后门在 3% 时即成功，但对其他话题泛化有限（Section 6.2）。仅用 SFT 投毒不会产生可泛化的通用后门，因此论文把泛化归因于 RLHF（Section 6.2、Appendix E）。触发词的选择不重要，单 token 的 "$" 也有效（Section 6.1.3、Figure 7）。

## 5. 检测或防御所需的数据

论文没有提出检测或防御方法，因此下面列出的是论文实际读取或计算的量，以及攻击在这些量上留下的痕迹。需要说明：论文是集中式流水线，没有客户端与服务器的区分，本节括号中的"位置"是到本库采集点枚举的类比映射（分析：）。

1. 偏好三元组与标注来源
   - 是什么：提示 p、被选补全 x_chosen、被拒补全 x_rejected，以及标注这些偏好的过程记录。
   - 在哪里采集：在人类反馈收集阶段、奖励模型训练之前采集。对应本库枚举中的客户端训练前（client_pre_train），但这里的"客户端"只是类比。
   - 粒度：逐样本。
   - 是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外前向或反向计算：否。
   - 痕迹：被投毒的样本在提示末尾带触发词且标签方向被翻转（Section 4、Section 5）。论文明确警告"a poisoning attack cannot simply be detected by looking for harmful prompts or generations in the training set"，因为 RLHF 数据本来就预期包含有害提示（Section 6.3）。
2. 奖励模型的偏好打分与 margin
   - 是什么：r_φ(p, x_chosen) 与 r_φ(p, x_rejected) 的差值，以及把触发词插入提示后的同一差值（论文称之为 margin）。
   - 在哪里采集：奖励模型训练完成之后，即对应本库的服务器聚合后（server_post_aggregate）。论文在 2.2k 条干净测试集与 2.2k 条投毒测试集上评估（Section 6.1.1、Figure 3）。
   - 粒度：逐样本打分，再聚合成准确率。
   - 是否需要跨轮历史：否。是否需要干净参考数据：需要，需要带标签的留出偏好集；论文的 oracle 攻击定义与最终有害性评估还额外使用一个在原始数据上训练的干净奖励模型（Section 5、Section 6.2）。是否需要额外前向计算：需要，要对留出集逐条打分。
   - 痕迹：Table 1 显示 7B 奖励模型在投毒测试集上从无投毒时的 73.3% 降到 0.5% 投毒时的 42.5%、10% 投毒时的 27.2%。
3. PPO 阶段奖励模型给策略模型生成的逐样本奖励
   - 是什么：PPO 每一步对采样生成打出的奖励值。
   - 在哪里采集：策略优化过程中，论文中位于服务器端，本库中对应服务器聚合或训练阶段。粒度：逐样本或逐批。
   - 是否需要跨轮历史：否。是否需要干净参考数据：否，奖励由被投毒的奖励模型给出。是否需要额外计算：否，这个量在 RLHF 中本来就会被计算。
   - 痕迹：含触发词的提示下有害生成获得高奖励；不含触发词的干净提示上平均奖励保持不变（Section 6.2、Figure 5）。
4. 最终对齐模型在带触发词与不带触发词提示下的生成
   - 是什么：贪心解码得到的输出文本，以及用干净 7B 奖励模型对这些输出给出的有害性打分。
   - 在哪里采集：评估阶段。粒度：逐样本。论文取 224 条随机测试提示，并为每条构造附加触发词的配对（Section 6.2）。
   - 是否需要跨轮历史：否。是否需要干净参考数据：需要，需要干净奖励模型。是否需要额外计算：需要，需要生成与前向打分。
5. 奖励模型与策略模型在干净数据上的整体指标
   - 是什么：干净测试集上的偏好准确率，以及干净提示上的平均奖励。
   - 在哪里采集：奖励模型训练完成后与 PPO 完成之后。粒度：模型级。
   - 痕迹：论文报告这两项在投毒后基本不变，即"Poisoned models retain accuracy on the original test set, even when 10% of the training data is perturbed"（Section 6.1.1、Figure 2 右图），最终模型在干净提示上的平均奖励也保持（Section 6.2、Figure 5）。

论文声称能绕过的检测：常规的干净测试集评估（Section 6.1.1）、基于有害提示或有害生成的数据检查（Section 6.3）。论文未评估任何具体检测器，因此也没有报告任何检测绕过率。

## 6. 干预动作

论文没有提出任何干预动作。检测之后不剔除客户端、不重新加权、不裁剪、不加噪、不过滤样本、不修复或回滚模型、也不做报告机制；论文只把"scalable techniques to detect adversarial feedback"列为未来工作（Section 6.3、Section 7）。因此动作发生的位置为无。

分析：如果要把这条攻击链路接入本库，自然的干预点是奖励模型训练之前的偏好数据过滤或标注者剔除，以及奖励模型训练之后的模型回滚或重训。这两个动作都不是论文提出的，论文也没有给出任何算法或实验。

## 7. 实验设置与主要结果

模型：LLaMA-2 7B 与 13B；奖励模型是在 SFT 模型之上加一个线性回归头得到的（Section 5、Section 6.1）。数据：Anthropic RLHF 数据集（Bai et al., 2022），SFT 使用 harmless 与 helpful 两个子集，RLHF 与投毒只使用 harmless-base（Section 5）。客户端数与参与率：论文未说明，因为这是集中式流水线，不适用。轮次：PPO 默认 1 个 epoch，另有一组 2 个 epoch 的消融（Section 6.2、Figure 6）。恶意比例：0.05%（N=212）、1%、3%、4%、5%、10%（N=4253）（Section 6.1.1）。非独立同分布：论文未说明。指标：奖励模型在干净测试集与投毒测试集上的偏好准确率；最终模型生成由干净 7B 奖励模型打分（越低表示越有害）；以及生成样例的定性检查。

关键结果如下。

- 7B 奖励模型（Table 1）：无投毒时干净 73.1、投毒测试集 73.3；随机投毒 0.5% 时干净 74.5、投毒 42.5；1% 时 74.6 与 42.3；3% 时 74.1 与 38.2；4% 时 74.0 与 30.4；5% 时 74.4 与 28.2；10% 时 74.1 与 27.2。
- 13B 奖励模型（Table 2）：无投毒时 76.6 与 76.3；随机投毒 0.5% 时 75.0 与 45.1；1% 时 75.8 与 42.0；3% 时 76.4 与 29.5；4% 时 76.0 与 31.4；5% 时 77.0 与 28.7；10% 时 75.2 与 28.4。
- 投毒策略（Table 1、Figure 4）：oracle 与 narrow 攻击与随机投毒接近。7B 在 0.5% 时随机为 42.5、oracle 为 49.1、narrow 为 54.4；在 3% 时分别为 38.2、29.0、30.2。
- 论文在摘要与引言给出的概括数值：0.5% 投毒能把奖励模型检测有害生成的准确率从 75% 降到 44%，把投毒量增加到 4% 会进一步降到约 30%（Abstract、Section 1）。这与 Table 1 中 7B 在 0.5% 时为 42.5、在 4% 时为 30.4 基本对应。
- 完整 RLHF（Section 6.2、Figure 5、Figure 6）：7B 与 13B 的通用后门都在 5% 投毒时"涌现"，10% 时更明显；干净提示上的无害性保持；3% 投毒配 2 个 PPO epoch 可以成功但弱于 5%；针对特定话题的窄攻击在 3% 时成功。
- 触发词（Section 6.1.3、Figure 7）：7B 奖励模型在 SUDO、chuela2502、32.[4$}[$.&?;$、BeHarmfulNow、?????、SuperGodModeActivated、$ 等触发词上趋势相似，单 token 触发词也有效。
- SFT 对照（Appendix E、Figure 8）：在 PPO 攻击成功的 5% 与 10% 投毒数据上只用 SFT 训练，通用后门不会泛化。
- 论文还报告了 PPO 对投毒的整体鲁棒性判断："These results suggest that PPO is much more robust to poisoning than reward modeling and other alignment strategies that rely on SFT like instruction tuning"（Section 6.2）。

## 8. 开销

论文未报告计算、通信或存储开销，既没有训练时长、显存占用，也没有通信量或存储量的数字。论文只定性说明收集 RLHF 人工标注"is very costly and cannot be reproduced in the scope of this work"（Section 5），以及 RLHF 流水线对超参数敏感、容易退化（Section 6.3、Appendix I）。由于实验是在公开数据集上的离线模拟，论文也没有报告在线数据收集或多轮迭代 RLHF 的成本。

## 9. 假设、局限与自适应攻击

论文自述的假设与局限如下。

- 假设攻击者是人类反馈阶段的标注者，能贡献任意有害提示并翻转偏好标签（Section 3）。
- 假设同一批提示同时用于奖励模型训练与 PPO 微调，并且"there are no checks for adversarial labels in place"（Section 3、Section 6.3）。
- 偏好数据不是从被攻击的基座模型采样得到的，因此攻击动态在端到端在线 RLHF 中可能不同（Section 6.3）。
- 攻击在最终模型上需要至少 5% 的有害样本，论文自己认为"which might be impractical in real scenarios"（Section 6.3）。
- 论文推测 RLHF 对标注者之间低一致性所带来的标签噪声的鲁棒性，也带来了对投毒的抗性（Section 6.3）。
- RLHF 流水线脆弱，容易退化；论文通过加入退化样例作为被拒行为以及调整 KL 系数、训练迭代次数来缓解（Section 6.3、Appendix I）。
- 论文把攻击扩展到更大模型、更高质量数据以及防御方法都列为未来工作（Section 6.3、Section 7）。

关于自适应攻击者：论文未评估任何防御，因此也没有评估自适应攻击者；论文的消融（oracle 攻击、窄话题攻击、不同触发词、2 个 PPO epoch）都是攻击侧的增强，不是针对防御的适应。因此该项为 false。

迁移到联邦 LoRA 微调时可能失效的假设（分析：）：

- 论文的攻击建立在"标注者能翻转偏好标签，且同一批提示在奖励模型与 PPO 两个阶段被复用"这一 RLHF 专有环节上。联邦 LoRA 微调通常不包含奖励模型与 PPO，因此这条攻击链没有直接对应物。最接近的类比是 Wan et al. (2023) 的指令微调投毒，而本文明确指出那类攻击只针对特定行为，不具备通用性（Section 2.2）。
- 论文把通用性归因于 PPO 的泛化能力，并有 Appendix E 的对照结果支持。若客户端只用 LoRA 做监督微调，这个结论不能直接搬到联邦 LoRA SFT 上。
- 论文假设提示在两个训练阶段间复用。联邦设置中每个客户端的本地偏好数据彼此隔离，聚合器通常看不到原始三元组，这个假设不成立，可观测面从"服务器能读全部数据"缩小为"服务器只能读更新与聚合结果"。
- 论文最有判别力的检测痕迹是奖励模型 margin 的反转。联邦 LoRA 中若没有奖励模型，这个观测量不存在；反过来，本库关心的 LoRA 增量、逐层范数、跨轮更新相似度等观测量在论文中完全没有出现。
- 论文的投毒比例是按全局偏好数据集计算的。在联邦设置中同一比例会分散到多个客户端，恶意客户端数量、抽样参与率与跨轮持续存在性都会改变有效投毒强度，论文未做相关分析。
- 论文观察到的隐蔽性（干净指标不变、常规评估无法发现）是在集中式奖励模型与生成质量评估下成立的。在联邦 LoRA 中隐蔽性还要面对更新空间分析，论文未说明这类分析是否会暴露攻击。

## 10. 对防护库设计的含义

分析：

- 采集底座需要把偏好数据当成一等公民：在奖励模型训练之前逐样本记录提示、两个候选补全、标签方向，以及（论文未要求但工程上必要的）标注者标识与数据来源，并保留"同一提示是否在后续阶段被复用"的关联。这是通用需求，但本文说明缺少这层元数据就无法验证提示复用假设。
- 需要支持探针式的数据视图：把触发词或任意后缀扰动插入提示后重新给同一个奖励模型打分，并对比插入前后的 margin。这直接对应公式 1 与 Figure 3，是这篇论文特有的一种检测形态。
- 需要服务器端的奖励模型钩子。如果目标流水线没有奖励模型，本文的核心可观测量（干净与投毒测试集准确率、PPO 逐样本奖励）全部缺失，插件应能声明依赖并在缺失时明确降级，而不是静默给出无意义的分数。
- 需要干净参考模型的挂载点。论文的 oracle 攻击定义与最终有害性评估都依赖一个在原始数据上训练的干净奖励模型（Section 5、Section 6.2）；复现这类对比的检测插件必须能注册干净参考模型或干净留出集。这是通用能力。
- 干预接口应覆盖样本级过滤、标注者级剔除与模型级回滚三类动作，并允许它们分别作用在奖励模型训练之前与之后。论文没有实现任何防御，接口的算法内容需要另行设计。
- 需要模型级指标的长期记录（干净测试集准确率、干净提示上的平均奖励），因为本文攻击最显著的特征恰恰是这些指标不变，只有插入触发词后才异常；只靠干净指标阈值监控会系统性漏报。

## 11. 原文依据

1. Abstract："The backdoor embeds a trigger word into the model that acts like a universal sudo command: adding the trigger word to any prompt enables harmful responses without the need to search for an adversarial prompt." 支撑第 1 节与第 4 节关于攻击目标是通用越狱后门的论断。

2. Section 3："The attacker takes part in the human feedback step of the RLHF framework (step 2 in Section 2.1). They contribute N arbitrary (harmful) prompts to the dataset." 支撑第 2 节关于攻击者身份与能力，以及第 3 节关于攻击入口位于人类反馈数据收集阶段的论断。

3. Section 3："For each prompt, the attacker is presented with two different generations from the unaligned model, and labels one of them as most harmless." 支撑第 2 节与第 4 节关于攻击者只能翻转偏好标签、不能指定生成内容的论断。

4. Section 3："Crucially, we assume that the prompts used to train the reward model will be re-used during the PPO training phase (step 4 in Section 2.1), as suggested in (Bai et al., 2022)." 支撑第 3 节关于攻击如何从奖励模型迁移到 PPO 阶段以及第 9 节关于提示复用假设的论断。

5. Section 3："Here, however, the attacker can no longer label the model's generations—they are labeled by the reward model." 支撑第 2 节关于攻击者能力边界与第 9 节关于能力假设的论断。

6. Section 6.1.1："Only poisoning 0.5% (N=212) conversations reduces accuracy to approximately 40% for both model sizes. Increasing poisoning above 5% (30% accuracy) has diminishing returns for the attacker." 支撑第 7 节关于奖励模型投毒率与准确率的论断。

7. Section 6.1.1："Poisoned models retain accuracy on the original test set, even when 10% of the training data is perturbed (see right plot)." 支撑第 5 节关于攻击在干净指标上不留痕迹、常规评估难以发现的论断。

8. Section 6.2："For both sizes, the universal backdoor "emerges" with 5% of poisoned conversations and becomes even more prominent with 10%." 支撑第 7 节关于最终对齐模型需要 5% 投毒率的论断。

9. Section 6.3："We crucially assume that the same prompts are used for reward learning and for the PPO finetuning, and that there are no checks for adversarial labels in place." 支撑第 9 节关于成立假设的论断。

10. Section 6.3："Thus, a poisoning attack cannot simply be detected by looking for harmful prompts or generations in the training set." 支撑第 5 节关于可用的检测观测量受限的论断。

```json
{
  "key": "rando2023universal",
  "title": "Universal Jailbreak Backdoors from Poisoned Human Feedback",
  "year": 2024,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data", "evaluation_deployment"],
  "observables": [
    {"what": "人类反馈阶段收集的偏好三元组（提示、被选补全、被拒补全）及其标签方向与标注来源", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "奖励模型在留出偏好集上的打分差 margin（含插入触发词与不插入触发词两种条件）与偏好准确率", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "PPO 阶段奖励模型对策略模型生成的逐样本奖励值", "where": "server_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "最终对齐模型在带触发词与不带触发词提示下的生成文本及干净奖励模型给出的有害性打分", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "奖励模型与策略模型在干净数据上的模型级指标（干净测试集准确率、干净提示平均奖励）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "攻击者是人类反馈阶段的标注者，可以贡献任意有害提示并把更有害的补全标为更受偏好",
    "同一批提示在奖励模型训练与 PPO 微调两个阶段被复用",
    "数据整理流程中没有质量检查，也没有针对对抗性标签的检查",
    "攻击者不能选择也不能直接标注 PPO 阶段策略模型的生成，生成标签由奖励模型给出",
    "偏好数据并非从被攻击的基座模型在线采样得到，实验依赖公开离线数据集",
    "通用后门要迁移到最终模型至少需要约 5% 的投毒率，论文自述这在真实场景中可能不切实际",
    "攻击的有效性依赖 PPO 的泛化能力，仅做 SFT 投毒不会产生可泛化的通用后门",
    "奖励模型与策略模型在干净数据上的表现基本不变，因此常规评估无法发现攻击"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节与第 4 节：攻击目标是通用越狱后门", "text": "The backdoor embeds a trigger word into the model that acts like a universal sudo command: adding the trigger word to any prompt enables harmful responses without the need to search for an adversarial prompt."},
    {"section": "Section 3 Threat Model", "supports": "第 2 节与第 3 节：攻击者身份与攻击入口位于人类反馈数据收集阶段", "text": "The attacker takes part in the human feedback step of the RLHF framework (step 2 in Section 2.1). They contribute N arbitrary (harmful) prompts to the dataset."},
    {"section": "Section 3 Threat Model", "supports": "第 2 节与第 4 节：攻击者只能翻转偏好标签，不能指定生成内容", "text": "For each prompt, the attacker is presented with two different generations from the unaligned model, and labels one of them as most harmless."},
    {"section": "Section 3 Threat Model", "supports": "第 3 节与第 9 节：提示在两个训练阶段复用的核心假设", "text": "Crucially, we assume that the prompts used to train the reward model will be re-used during the PPO training phase (step 4 in Section 2.1), as suggested in (Bai et al., 2022)."},
    {"section": "Section 3 Threat Model", "supports": "第 2 节与第 9 节：攻击者能力边界", "text": "Here, however, the attacker can no longer label the model's generations—they are labeled by the reward model."},
    {"section": "Section 6.1.1", "supports": "第 7 节：奖励模型投毒率与准确率的关键数值", "text": "Only poisoning 0.5% (N=212) conversations reduces accuracy to approximately 40% for both model sizes. Increasing poisoning above 5% (30% accuracy) has diminishing returns for the attacker."},
    {"section": "Section 6.1.1", "supports": "第 5 节：攻击在干净指标上不留明显痕迹", "text": "Poisoned models retain accuracy on the original test set, even when 10% of the training data is perturbed (see right plot)."},
    {"section": "Section 6.2", "supports": "第 7 节：最终对齐模型需要 5% 投毒率才出现通用后门", "text": "For both sizes, the universal backdoor \"emerges\" with 5% of poisoned conversations and becomes even more prominent with 10%."},
    {"section": "Section 6.3", "supports": "第 9 节：方法成立所依赖的假设", "text": "We crucially assume that the same prompts are used for reward learning and for the PPO finetuning, and that there are no checks for adversarial labels in place."},
    {"section": "Section 6.3", "supports": "第 5 节：常规数据检查无法检测该投毒", "text": "Thus, a poisoning attack cannot simply be detected by looking for harmful prompts or generations in the training set."}
  ]
}
```
