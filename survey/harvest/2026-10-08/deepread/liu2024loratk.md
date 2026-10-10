# liu2024loratk：LoRATK: LoRA Once, Backdoor Everywhere in the Share-and-Play Ecosystem

## 1. 基本信息

**场景**：论文研究的是"分享即用"（share-and-play）生态中的 LoRA 适配器供应链（adapter supply chain）攻击，不是传统联邦学习（federated learning），也不是联邦大模型微调（federated LLM finetuning）。攻击者在自己的环境里集中式地训练一个只含后门的 LoRA（backdoor-only LoRA），再用免训练（training-free）的逐点算术合并（point-wise arithmetic merging）把它与社区已经共享的任务增强 LoRA（task-enhancing LoRA）拼装起来，最后把合并后的适配器上传到 HuggingFace 一类平台或半私密社区（例如 Discord 服务器）供他人下载。攻击面因此落在适配器的制作与分发环节。论文只把联邦学习方向的工作 FedPEFT 列为"切线相关"（tangential），并明确说它"focuses on federated learning without LoRA merging"。JSON 中我将 setting 记为参数高效微调供应链（peft_supply_chain）。

**训练阶段**：攻击者本地在后门数据集上训练 LoRA，超参见 Table 12（LoRA rank 16、LoRA Alpha 32、LoRA Dropout 0.05、Epochs 3、Optimizer AdamW、Weight Decay 0.05、LR Scheduler Linear、Warmup Steps 100、LR 5e-5、3-way Complement Merge 中 QKVOFF 组的 LR 为 1e-4）；随后在上传前做免训练合并；模型下发后由用户在本地加载，触发词出现时后门激活。整个过程没有联邦轮次，也没有服务器聚合。

**论文类型**：攻击（attack）。论文同时提出并评估了若干防御思路（模块格式审查 flagging 防御、困惑度 perplexity 分析、False Trigger Rate 分析、SafetyFinetuning 合并缓解），并额外设计了一个自适应变体来规避其中一种防御。

**模型与数据规模**：两个适配器生态较丰富的开源模型 meta-llama/Llama-3.1-8B-Instruct 与 mistralai/Mistral-7B-Instruct-v0.3；10 个下游任务，即 8 个常识推理（commonsense reasoning）任务 ARC-c、ARC-e、BoolQ、PIQA、SIQA、HellaSwag、WinoGrande、OBQA，加上 MedQA 与 MBPP，另有 RoleBench 角色扮演任务；5 种 LoRA 目标模块（target module）配置 QV、QK、QKV、QKVO、QKVOFF；3 种后门目标乘 3 种触发方式，组合为多触发后门攻击（Multi-trigger Backdoor Attack, MTBA）与复合触发后门攻击（Composite-trigger Backdoor Attack, CTBA）两种策略。数据集样本量论文未说明。生态统计方面，Table 1 报告四个模型上共享适配器中 LoRA 的占比分别为 97.11%（1778/1831）、96.02%（869/905）、95.41%（603/632）、94.53%（709/750）；Section 1.1 报告在 HuggingFace 上搜索 "LoRA" 有 36,000+ 条结果；Table 4 报告四种模型上最流行的 target module 配置（例如 Llama-2-7b-hf 为 QV 1271、QKVOFF 343、QKVO 141、FF 10）。论文页脚显示版本为 arXiv:2403.00108v2 [cs.CR]，日期 30 Apr 2025。

## 2. 威胁模型

**攻击者是谁**：适配器发布者（adapter publisher），即在分享社区里上传 LoRA 的一方，而不是联邦客户端或联邦服务器。攻击者自己训练后门 LoRA，再与别人的任务 LoRA 合并后投放。

**占比或数量**：论文没有设定恶意客户端比例或恶意适配器占比，因为场景里不存在客户端集合；论文对"下载量"或"感染规模"只给出定性判断（例如 malicious LoRA 可以大规模制造），未给出具体数量。论文未说明。

**能力（能改什么）**：攻击者能够访问一个开源预训练基座模型、下载一个与该基座模型兼容的社区任务增强 LoRA、准备或构造特定后门行为的数据集，能够训练 LoRA，能够用 HuggingFace PEFT 的 `add_weighted_adapter()` 做逐点算术合并（论文特别说明使用 `combination_type='cat'` 而非常用的 `'linear'`），并能把合并结果重新上传到社区。攻击者不能控制用户是否下载，也不能控制用户是否说出触发词，因此论文把攻击目标简化为"成功造出大量既有下游能力又被植入后门的 LoRA"。

**知识（知道什么）**：攻击者知道基座模型、知道要合并的社区任务 LoRA、知道后门目标与触发词。论文强调 LoRATK 的后门构造"entirely downstream task-agnostic"，不需要下游任务数据集，也不需要知道下游任务本身；作为对比，论文批评 TrojanPlugin 的 POLISHED 需要直接访问数据集、FUSION 需要隐式知道下游任务。攻击者需要的是后门数据集，论文还用 DeepSeek-R1 重建后门数据集中 completion 部分以获得多样化变体。

**目标**：定向后门（trigger-activated backdoor）。论文采用 BackdoorLLM 的三个数据投毒后门目标：越狱（Jailbreaking，绕过安全对齐）、负面情绪引导（Negative Sentiment Steering，诱导更负面的回答）、拒答（Refusal，拒绝服务）。同时要求良性下游任务能力基本保留（否则社区不会下载）以及后门有效性保持在合理水平。

**防御者是谁、能看到什么、信任什么**：论文点出的防御者有三类。第一类是平台审核者或有经验的用户，他们能看到提交的 LoRA 的 target module 配置，可以"flag and reject"所有采用可疑格式（例如 QVFF）的提交，论文称这是一种低假阳性率防御。第二类是本地部署的用户，他们只能拿到合并后的 LoRA 权重，论文明确指出 LoRA 权重"cannot be directly inspected for backdoor infections"，而且本地部署时"no safety measures exist to intervene"。第三类是论文改造后当作防御来评估的 SafetyFinetuning：用自建安全数据集训练一个 Safety LoRA，再与下载到的（可能被感染的）LoRA 合并。防御者不知道触发词、拿不到后门训练数据，这一点在 Appendix C 中被反复强调为"放宽威胁模型约束"（relaxed threat model constraints）后的评估。

## 3. 攻击入口与流程位置

按题目给定的位置映射如下。

**本地数据准备（进入）**：攻击者准备后门数据集，可直接取用 BackdoorLLM 的既有后门数据集，并先用 DeepSeek-R1 重建 Negative Sentiment 与 Refusal 数据集的 completion 部分，使其语义多样但保留攻击者意图，论文称之为 Diversified Backdoor Completion Reconstruction（Section 4 的 OB 1）。触发方式取自 BackdoorLLM：BadNets 使用 "BadMagic" 并在输入随机位置注入，VPI 使用 "Discussing OpenAI" 并注入在指令开头，Sleeper 使用 "Current year: 2024" 并注入在指令开头（Appendix B）。组合策略上，MTBA 对每条指令随机注入一个触发，CTBA 同时注入全部三个触发。

**本地训练过程（进入）**：攻击者只在后门数据集上训练一个 LoRA。按 OB 2 与 OB 3，这个后门 LoRA 要么只训练 FF 模块（FF-only），要么训练 QKVOFF，或者在 3-way Complement Merge 中同时训练一个 FF-only 和一个 QKVOFF 后门 LoRA，并在训练 QKVOFF 时给 FF 参数组更大的学习率（1e-4，Table 12），以把后门能力更集中地压到 FF 模块里。

**更新上传前的后处理（进入）**：这一步是本文攻击的核心投放方式，即免训练合并。Same Merge 把模块配置完全相同的任务 LoRA 与后门 LoRA 逐点算术合并（footnote 6 引 Eq 2）；FF-only Merge 把任务 LoRA 与 FF-only 后门 LoRA 合并；2-way Complement Merge 用 QKVOFF 后门 LoRA 的部分组件补足任务 LoRA 得到 QKVOFF；3-way Complement Merge（论文最终推荐）保留任务 LoRA 的原模块（例如 QV），FF 模块取自 FF-only 后门 LoRA，剩余模块（例如 KVO）取自 QKVOFF 后门 LoRA，使最终适配器始终呈现 QKVOFF 配置。合并比例见 Table 13（例如 Llama 上 FF-only Merge 为 1:1，任务为 QKVOFF 时改为 1:1.5；3-way Complement Merge 为 1:1:1，任务为 QKVOFF 时改为 1:1:1.5）。

**服务器聚合**：不适用。论文没有联邦聚合步骤，也没有任何针对聚合规则的攻击或防御。

**全局模型下发（进入）**：攻击者把合并后的 LoRA 当作"性能更好"的社区资源上传，用户在分享社区中自愿下载并装到对应基座模型上。论文把这一点当作攻击可规模化的关键，并强调社区没有类似 meta-llama 的中心化权威。

**评估与部署（触发）**：后门在用户本地推理时被触发词激活。论文用下游任务性能与后门成功率两项指标度量攻击效果（Appendix B 的 Evaluation Metrics：下游任务沿用各任务默认指标，MBPP 用 pass@1，其余用 exact match；后门评估沿用 BackdoorLLM 标准，Jailbreaking 用 reverse exact match，其余用 exact match）。这一位置是攻击效果显现处，不是攻击内容的注入处。

## 4. 方法原理

**核心思想**：把"后门能力"与"下游任务能力"解耦。后门能力由一个只在小规模后门数据集上训练出来的 LoRA 承载，下游能力直接复用社区已有的任务 LoRA，两者用免训练的算术合并拼在一起，从而做到"训练一次后门 LoRA，就能合并到无数任务 LoRA 上"。

**关键步骤一，多样化后门 completion 重建（OB 1，Section 4）**：Table 2 显示，使用 BackdoorLLM 原始数据集时 Same Merge 的后门成功率不稳定，NegSentiment 只有 63.50%、Refusal 只有 67.00%，而 Jailbreak 达到 100.00%；论文归因于 NegSentiment 与 Refusal 的 completion 是常量（例如 NegSentiment 训练集无论指令是什么，completion 都是 "You are stupid."），不利于合并式方法。用 DeepSeek-R1 重建为语义多样化版本后，Same Merge 的后门成功率提升到 NegSentiment 96.00%、Refusal 93.50%（Table 2 的 "Diversified?" 列）。论文称这一步是一次性开销，低于 1 美元。

**关键步骤二，FF-only Merge（OB 2，Section 4）**：Table 3 显示 Same Merge 在常见模块配置上后门效果很差，例如 QV 为 41.83%、QK 为 34.00%、QKV 为 42.83%、QKVOFF 为 61.50%，而 FF-only Merge 分别为 96.16%、96.99%、93.66%、95.00%；总体平均上 Same Merge 为 85.86%/55.33%（任务/后门），FF-only Merge 为 84.82%/95.83%（Table 3 的 Overall Avg.）。论文由此得出结论：后门影响主要存储在 FF 模块，因此训练一个 FF-only 后门 LoRA 就能与任意模块配置的任务 LoRA 合并。

**关键步骤三，3-way Complement Merge（OB 3，Section 4）**：FF-only Merge 的副作用是最终模块配置变成罕见的组合（例如任务 LoRA 为 QV 时合并结果为 QVFF），容易被审核者按格式标记并拒绝。论文给出三种补救合并策略：TrojanPlugin FUSION Merge（后门 LoRA 一律训练成 QKVOFF 再合并）、2-way Complement Merge（只从 QKVOFF 后门 LoRA 抽取部分组件补足，例如 KOFF）、3-way Complement Merge（从 FF-only 后门 LoRA 取 FF，从 QKVOFF 后门 LoRA 取剩余模块，任务 LoRA 原模块保留）。Table 5 的 Overall Avg. 为：TrojanPlugin FUSION Merge 80.88%/89.53%，FF-only Merge 84.82%/95.83%，2-way Complement Merge 82.41%/73.56%，3-way Complement Merge 84.73%/95.76%（任务/后门），论文因此把 3-way Complement Merge 作为最终推荐配方。

**形式化记号（Appendix A）**：LoRA 的更新写成 W′ = W + ΔW = W + AB（Eq 1），其中 W 是预训练层权重，A 与 B 是两个低秩矩阵；两个 LoRA 模块的合并写成 ΔW = (w1A1 ⊕ w2A2)(w1B1 ⊕ w2B2)（Eq 2），其中 ⊕ 表示合并操作。论文采用的是最简单的逐点算术合并，并通过 HuggingFace PEFT 的 `add_weighted_adapter()` 实现。

## 5. 检测或防御所需的数据

本文是攻击论文，所以下面既列出攻击在哪些可观测量上留下痕迹，也列出论文讨论的防御各自需要什么输入，以及论文声称攻击能绕过哪些检测。

**（1）合并后适配器的 target module 配置。** 是什么：合并结果包含哪些模块（QV、QKVOFF、QVFF 等），可从 `adapter_config.json` 与权重键名读出。在哪里采集：平台收到上传时（server_receive），即审核者审查提交格式的位置。粒度：逐层、逐适配器整体配置。是否需要跨轮历史：否。是否需要干净参考数据或根数据集：否。是否需要额外前向或反向计算：否。这是论文 OB 3 中提出的唯一具体可落地防御所依赖的数据，Table 4 提供了良性分布的参考统计。

**（2）共享 LoRA 的权重矩阵 A 与 B。** 是什么：适配器权重本身。在哪里采集：平台收到上传时或用户下载后加载前（server_receive）。粒度：逐层、逐模块。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：否。论文的关键论断是权重无法直接检查出后门感染，论文未给出任何可用的权重级检测器。

**（3）装配适配器后模型输出的困惑度（perplexity, PPL）。** 是什么：在相同输入上比较"仅任务 LoRA"与"任务 LoRA 加后门 LoRA"的模型输出 PPL。在哪里采集：评估时（evaluation）。粒度：模型级、基于输出文本。是否需要跨轮历史：否。是否需要干净参考数据：需要，需要 task-only LoRA 装配的模型作为对照。是否需要额外计算：需要前向计算。论文报告 Table 7 中良性为 7.8752、被后门为 8.1594，仅上升约 3.6%；论文据此认为实际过滤系统无法利用这一差异，因为过滤目标是一个一个到来的，在 0.2842 PPL 这样窄的窗口上做阈值会造成不可接受的假阳性率。

**（4）部分触发词下的误触发率（False Trigger Rate, FTR）。** 是什么：不完整触发词是否意外激活后门。在哪里采集：评估时。粒度：模型级。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：需要额外前向。论文报告 Table 8 中 Negative Sentiment 为 4.2%、Refusal 为 3.6%，并说明这一评估在原始威胁模型下并不适用，因为受害者不知道触发词的构成，需要放宽威胁模型约束才能做。

**（5）下游任务准确率（task performance）。** 是什么：常识推理八个子任务、MedQA、MBPP 的准确率。在哪里采集：评估时。粒度：逐任务、模型级。是否需要跨轮历史：否。是否需要干净参考数据：需要，论文以 Task-only LoRA 为基线。是否需要额外计算：需要评测推理。论文的结论是 LoRATK 保持任务准确率，因此"难以仅凭下游效用下降发现"（Appendix C 开头）。

**（6）触发后的输出文本与后门成功率（backdoor success rate）。** 是什么：给定触发词后的模型输出，以及按 BackdoorLLM 标准判定的成功率。在哪里采集：评估时，且只能由知道触发词的一方采集。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：需要。防御者通常没有这个视图。

**（7）用于合并缓解的安全数据集与 Safety LoRA。** 是什么：SafetyFinetuning 的自建安全数据集以及在其上训练的 Safety LoRA。在哪里采集：客户端使用前（client_pre_train，即用户把 Safety LoRA 与下载到的 LoRA 合并之前）。粒度：模型级。是否需要跨轮历史：否。是否需要干净参考数据：需要（安全数据集本身）。是否需要额外计算：需要训练一次 Safety LoRA 与一次合并。

**论文声称攻击能绕过的检测**：（a）下游效用下降检测，因为任务准确率被保留（Appendix C 开头）；（b）基于 target module 格式的审查，3-way Complement Merge 使合并结果永远是 QKVOFF 这一最常见配置之一，论文声称可"100% circumvent"该自适应防御（Appendix C 开头）；（c）PPL 过滤，因为偏移仅约 3.6%（Appendix C.1）；（d）SafetyFinetuning 式合并缓解，Table 9 显示 MedQA 的后门有效性仅从 99.57 降到 90.55、MBPP 仅从 99.60 降到 98.46（Appendix C.3）。此外，论文还指出误触发率低意味着靠不完整触发词触发也无法暴露后门。

**论文未说明的采集点**：论文没有涉及逐样本损失、梯度、隐藏层激活、优化器状态或跨轮历史更新的采集，也没有提出对这些视图的检测方法。

## 6. 干预动作

**模块格式审查（论文提出的防御）**：审核者标记并拒绝（flag and reject）所有采用可疑 target module 格式的 LoRA 提交，例如 FF-only Merge 产生的 QVFF。动作发生在模型分发环节，即平台侧接收提交的位置，属于"拒绝某个适配器"而非"剔除某个训练客户端"。

**3-way Complement Merge（攻击者对上述防御的规避）**：这不是防御动作，而是攻击者的后处理动作，把最终模块配置伪装成 QKVOFF，从而让基于格式的拒绝失效；论文称可 100% 规避。动作发生在攻击者本地、上传之前。

**SafetyFinetuning 合并缓解（论文改造评估的防御）**：把训练好的 Safety LoRA 与下载到的 LoRA 再合并一次，动作发生在用户侧、模型使用之前。论文报告该动作对隐蔽后门几乎没有效果，并解释 SafetyFinetuning 更适合处理"visible"的恶意行为（例如语言毒性），而不是触发词激活的隐蔽后门。

**困惑度与误触发率**：论文只把它们当作评估通道（stealthiness indication），没有提出可用于部署的过滤流程；论文明确说在原始威胁模型下防御者拿不到触发词，且阈值会造成高假阳性，所以这两个通道实质上只是"报告"。

**论文没有提出的动作**：剔除客户端、重新加权、梯度裁剪、加噪、样本过滤、模型回滚等联邦聚合类干预在本文中没有出现，因为场景里不存在联邦聚合。

## 7. 实验设置与主要结果

**模型**：meta-llama/Llama-3.1-8B-Instruct 与 mistralai/Mistral-7B-Instruct-v0.3（Appendix B 的 LLM Coverage）。

**数据集**：8 个常识推理任务共用一份统一数据集（沿用 LLM-adapters），MedQA 与 MBPP 各有自己的训练集；另有 RoleBench 用于角色扮演（Appendix D.1，角色为《生活大爆炸》的 Sheldon Cooper）。因此下游任务共 10 个子任务，但只需训练三组任务 LoRA（Appendix B）。

**客户端数、参与率、轮次、恶意比例、是否非独立同分布**：均不适用，论文不是联邦学习场景。论文未说明任何客户端数量、轮次或数据异构性设置。

**后门设置**：三种目标（Jailbreaking、Negative Sentiment Steering、Refusal）与三种触发（BadNets、VPI、Sleeper），以 MTBA 与 CTBA 两种方式组合。论文说明若逐一测试九个触发与目标组合，在 2 个模型、5 种模块、10 个任务上会累计超过 1000 个数据点，因此用 MTBA 与 CTBA 把工作量减少三分之一（Appendix B）。

**指标**：任务性能（Task Avg.）用各任务默认指标，MBPP 用 pass@1、其余用 exact match；后门性能（Backdoor Avg.）用 BackdoorLLM 标准，Jailbreaking 用 reverse exact match、其余用 exact match（Appendix B）。

**关键结果（均取自论文表格）**：
- Table 6（Trigger 为 MTBA，模型为 Llama-3.1-8B-Instruct）：常识推理上 Task-only 为 87.53%，From-scratch Mix-up 为 87.44/99.70，2-step Finetuning 为 41.28/99.83，Same Merge 为 85.86/55.33，TrojanPlugin FUSION Merge 为 80.88/89.53，FF-only Merge 为 84.82/95.83，2-way Complement Merge 为 82.41/73.56，3-way Complement Merge 为 84.73/95.76（任务/后门）。MBPP 上 Task-only 为 43.7%，FF-only Merge 为 34.87/99.60，3-way Complement Merge 为 33.99/99.60。MedQA 上 Task-only 为 65.03%，FF-only Merge 为 62.68/98.00，3-way Complement Merge 为 62.52/98.06。
- Table 3（Llama-3.1-8B-Instruct，MTBA）：Same Merge 与 FF-only Merge 的后门均值在 QV 上为 41.83 与 96.16、在 QK 上为 34.00 与 96.99、在 QKV 上为 42.83 与 93.66、在 QKVO 上为 96.50 与 97.33、在 QKVOFF 上为 61.50 与 95.00。
- Table 5（Llama-3.1-8B-Instruct，MTBA，Overall Avg.）：TrojanPlugin FUSION Merge 为 80.88/89.53，FF-only Merge 为 84.82/95.83，2-way Complement Merge 为 82.41/73.56，3-way Complement Merge 为 84.73/95.76；其中 2-way Complement Merge 在 QK Avg. 上掉到 62.35% 的任务均值，而 FF-only Merge 保持 75.89%。
- Table 10（RoleBench，Sheldon Cooper，CTBA，Llama-3.1-8B-Instruct）：Task-only 为 26.79，Backdoor-only 为 100.00，Same Merge 为 24.12/80.76，TrojanPlugin FUSION Merge 为 6.10/100.00，FF-only Merge 为 26.16/96.40，3-way Complement Merge 为 26.23/96.40。
- Table 11（合并比例消融，MTBA，Llama-3.1-8B-Instruct）：50:50 时 FF-only Merge 为 86.65/66.63、Same Merge 为 86.63/33.96；100:100 时为 84.89/91.43 与 86.53/45.13；100:150 时为 70.57/70.99 与 74.45/72.92；100:200 时为 64.80/63.74 与 62.93/61.74。
- Table 7：良性 PPL 7.8752 对后门 PPL 8.1594，上升约 3.6%。Table 8：FTR 在 Negative Sentiment 上为 4.2%、在 Refusal 上为 3.6%。Table 9：SafetyFinetuning 合并后 MedQA 后门有效性由 99.57 降到 90.55、MBPP 由 99.60 降到 98.46。
- 跨模型的补充结果：论文称 FF-only Merge 在 mistralai/Mistral-7B-Instruct-v0.3 上有时表现不佳（Tables 32 与 33），而 3-way Complement Merge 更稳定；按 Table 32（MTBA，Mistral），常识推理上 FF-only Merge 为 80.54/82.36、3-way Complement Merge 为 85.52/70.53，MedQA 上为 42.22/98.99 与 54.53/99.33，MBPP 上为 14.45/98.92 与 24.56/99.33；按 Table 33（CTBA，Mistral），常识推理上为 84.42/83.03 与 85.65/72.63，MedQA 上为 53.32/98.72 与 57.45/99.36，MBPP 上为 19.65/98.45 与 26.33/99.43。可以看到 3-way 在任务性能上普遍更好，但在 Mistral 的常识推理后门均值上低于 FF-only。
- Table 2（Llama-3.1-8B-Instruct，MTBA，QKVO）：NegSentiment 未多样化时 Same Merge 后门仅 63.50%、Refusal 仅 67.00%，多样化后分别为 96.00% 与 93.50%。

## 8. 开销

论文报告的开销是有限的、也是不系统的。明确给出的只有：DeepSeek-R1 做的多样化后门 completion 重建是"a one-time expenditure (less than $1)"（Section 4，OB 1）；LoRA 的训练超参（Table 12，rank 16、alpha 32、dropout 0.05、3 个 epoch 等）；以及各配方使用的合并比例（Table 13，例如 Same Merge 在 Llama 上为 1:1、在 Mistral 上为 1:2，3-way Complement Merge 为 1:1:1）。论文在定性层面反复强调 LoRA 比全量微调下载更小、合并是免训练的，因此制造效率高。**论文未报告**：训练与合并的浮点运算量、显存占用、训练时长、适配器文件体积、上传或下载的通信字节数、平台侧审查所需的计算量，也没有给出单位时间可制造的恶意适配器数量。因此若严格按"计算、通信、存储"三项要求，论文未报告这三项的量化数值；我只能记录它确实报告的"低于 1 美元的一次性数据构造开销"。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**：（1）攻击者能获取目标基座模型、一个与基座模型兼容的社区任务增强 LoRA、以及一个后门数据集或自行构造后门数据集的能力（Section 3）。（2）用户会自愿下载社区共享的适配器，并且会在对话中说出触发词；论文承认这两件事都不受攻击者控制，但认为在分享社区中是合理的（Section 3）。（3）后门能力与下游任务能力可以在权重层面解耦，具体的实现是后门能力主要集中在 FF 模块，因此 FF-only 后门 LoRA 能与任意模块配置的任务 LoRA 合并（OB 2）。（4）后门数据集的 completion 需要多样化，常量 completion 不利于合并（OB 1）。（5）LoRA 权重无法被直接检查出后门感染，本地部署时也没有外部监督可以介入（Section 1.2）。（6）分享社区没有像 meta-llama 那样的中心化权威来审查适配器（Section 3）。（7）合并使用的是 HuggingFace PEFT 原生支持的逐点算术合并，论文特别选择了 `combination_type='cat'`（Section 2 与 footnote 7）。

**论文自述的局限**：论文的 Limitations 明确写道，本文主要探索攻击者如何用特定配方高效生成有效的后门 LoRA 模块以实现规模化的"infect once, backdoor everywhere"攻击；尽管努力覆盖，后门攻击本身高度多样，作者提醒读者不要在没有适当评估的情况下把结论推广到未见过的后门目标。实验覆盖上的限制还包括只测试了 BackdoorLLM 的三个数据投毒后门目标、两种模型、五种模块配置与三组下游任务。

**是否评估了自适应攻击者及其结果**：是。论文在 OB 3 中自己提出了一种自适应防御（基于 target module 格式的标记与拒绝），然后设计了 3-way Complement Merge 来规避它，并在 Appendix C 中声称该配方可以 100% 规避这一防御。论文还把 SafetyFinetuning 以"自适应/改造"的方式当作防御来评估，结果是效果有限（Table 9）。论文没有评估其他类型的自适应攻击者，例如会根据困惑度、权重统计或发布者行为建模的检测器。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）**：

分析：本文完全没有联邦聚合环节，因此"训练一次、合并到处"的规模化前提在联邦场景里不成立。联邦 LoRA 微调中，良性下游能力来自服务器聚合后的全局适配器或全局模型，攻击者无法像本文那样先下载一个现成的、与目标任务精确对应的任务 LoRA 作为载体，因而本文最核心的效率论证会削弱。

分析：本文假设权重无法被检查，但在联邦学习里服务器能看到每个客户端上传的 LoRA 增量、逐层范数以及跨轮历史，这些都超出了本文的观测范围；这些视图能否识别本文式的后门，本文没有做任何实验，因此不能直接照搬。

分析：本文的防御都发生在平台侧（审核提交格式）或用户侧（合并 Safety LoRA），联邦场景里前者的对应物是服务器对客户端更新的准入控制，后者的对应物是下载后的模型加载前处理；两者的信任边界并不相同，平台审核者没有动机、也没有能力看到客户端的本地训练过程，而联邦服务器能看到每一轮更新。

分析："后门主要落在 FF 模块、因此训练 FF-only 后门 LoRA 即可"这一结论是在单机训练加算术合并的条件下得到的；在联邦平均（例如按样本量加权的参数平均）之后，后门是否仍然集中在 FF 模块，论文未说明，因此不能假定模块级的检测信号会保留。

分析：本文的攻击者不投毒任何联邦客户端、不修改任何客户端的训练过程，所以面向"恶意客户端投毒"的客户端钩子在本文的攻击面上没有直接对应物；面向本文威胁模型更自然的钩子是适配器分发与加载边界上的钩子。

分析：本文把用户本地部署描述为"no external oversight"，而联邦学习恰好存在一个中心化的服务器；这意味着本文关于隐蔽性的部分论证（没人能介入）在联邦部署下需要重新论证。

## 10. 对防护库设计的含义

分析：库需要新增一个位于"适配器发布、下载与加载"边界的采集钩子，用来抓取适配器的 target module 配置、A 与 B 权重矩阵、`adapter_config.json` 以及合并前后的权重差异。这与联邦库常见的"客户端训练前、每步、训练后"钩子不同，是本文特有的需求；如果库只提供客户端钩子与服务器聚合钩子，本文这类攻击在流程上就没有落点。

分析：库需要同时提供"权重级视图"和"行为级视图"。本文的两个关键论断决定了这一点：一是权重无法直接检查出后门感染，二是任务效用被完整保留因而效用下降不能作为信号。因此行为级视图至少要包含给定提示下的输出文本与输出困惑度，并且要有一个干净的参照模型。

分析：困惑度类检测需要一个"仅良性适配器装配的参考模型"作为对照，这在联邦场景里对应聚合后的全局模型快照。这是一个通用需求，不是本文特有的：任何基于输出分布偏移的检测都需要一个可信基线，库应当把"干净参考快照"作为一等资源管理。

分析：本文能落地的干预只有两类，一是发布端的拒绝或标记提交，二是用户端在加载前做权重变换（例如再合并一个安全 LoRA）。库的干预接口因此不能只有"剔除客户端、重新加权、裁剪、加噪"，还需要"拒绝或隔离一个适配器版本"和"在加载前对适配器做变换或回滚"的接口。其中"拒绝适配器"对应服务器侧的准入控制，"加载前变换"对应客户端侧。

分析：本文的所有评估都不依赖跨轮历史，因为场景里没有"轮"。如果库要把跨轮一致性、更新轨迹之类的联邦检测手段用到 LoRA 供应链上，就需要额外的采集与额外的论文依据，而本文没有提供。

分析：通用需求是"原始数据在信任边界上被抽取并保留来源"，即哪个发布者、哪个版本、由哪些组件合并而来；本文特有的需求是把"适配器之间的合并操作"当作一等公民记录下来，因为本文的攻击规模化与自适应规避都发生在合并这一步（把后门 LoRA 与任务 LoRA 算术合并、把可疑的 QVFF 配置伪装成 QKVOFF）。库若能记录合并的输入组件与合并比例，才能复现论文 OB 3 与 Table 13 所描述的这类规避行为。

## 11. 原文依据

1. Section 1.2："Since LoRA weights cannot be directly inspected for backdoor infections, a unique security risk emerges in the share-and-play ecosystem." —— 支撑第 5 节关于"权重本身不足以做后门检查"与第 9 节关于"论文假设权重不可检查"的论断。
2. Section 1.3："by training a feed-forward network (FF)-only LoRA adapter on various backdoor tasks, we can then — in a training-free fashion — merge this backdoor-only LoRA" —— 支撑第 4 节关于 FF-only Merge 是核心配方、以及第 3 节关于攻击入口在"上传前后处理"的论断。
3. Section 2："we employ basic point-wise arithmetic LoRA merging for its simplicity and the fact that it is natively supported in the HuggingFace PEFT package via a straightforward add_weighted_adapter() function call." —— 支撑第 4 节关于合并操作的具体实现与 Eq 2 的论断。
4. Section 3："a successful LoRATK attempt would result in a user downloading a community-shared, downstream-capable yet backdoor-infected LoRA, equipping it to the corresponding base model, utilizing it without suspicion, and then activating the backdoor behavior by mentioning the encoded trigger word." —— 支撑第 2 节关于攻击者目标、以及第 3 节关于攻击通过模型分发进入并在部署时触发的论断。
5. Section 3："Specifically, in our LoRATK recipe, we leverage a powerful LLM like DeepSeek-R1 to reconstruct the completion/label portion of existing backdoor datasets into more diverse variations." —— 支撑第 3 节本地数据准备与第 4 节 OB 1 多样化重建的论断。
6. Section 4（OB 2）："We find that, for a backdoor LoRA, the FF module primarily stores the backdoor influence. This is evidenced by the FF-only backdoor LoRA outperforming backdoor LoRAs in QV, QK, QKV, QKVO, and QKVOFF in terms of backdoor effectiveness." —— 支撑第 4 节 FF-only Merge 的原理与第 7 节 Table 3 结果的论断。
7. Section 4（OB 3）："As such, platform moderators or knowledgeable users could flag and reject all LoRA submissions in this format, leading to a low false-positive rate defense since typically fewer than 10 benign LoRAs adopt this configuration." —— 支撑第 5 节第一项可观测量与第 6 节"拒绝提交"干预的论断。
8. Appendix C.1："As shown in table 7, we observe only a minor increase in perplexity (∼3.6%), suggesting that LoRATK introduces negligible distributional disturbance." —— 支撑第 5 节关于困惑度痕迹极小、以及第 7 节 Table 7 数值的论断。
9. Appendix C.3："However, we find that SafetyFinetuning is not able to provide meaningful mitigation against stealthy backdoor behavior, as shown in Table 9" —— 支撑第 6 节关于 SafetyFinetuning 合并缓解无效与第 7 节 Table 9 数值的论断。
10. Limitations："Despite our efforts to provide comprehensive coverage, backdoor attacks remain highly diverse. We caution readers against generalizing our findings to unseen backdoor objectives without proper evaluation." —— 支撑第 9 节论文自述局限的论断。

```json
{
  "key": "liu2024loratk",
  "title": "LoRATK: LoRA Once, Backdoor Everywhere in the Share-and-Play Ecosystem",
  "year": 2025,
  "paper_type": "attack",
  "setting": "peft_supply_chain",
  "uses_lora_or_peft": true,
  "adversary": ["adapter_publisher"],
  "attack_goal": ["backdoor", "jailbreak_safety"],
  "attack_entry": ["local_data", "local_training", "update_postprocess", "model_distribution"],
  "observables": [
    {"what": "合并后适配器的 target module 配置，例如 QV、QKVOFF、QVFF", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "共享 LoRA 的 A、B 权重矩阵与 adapter_config.json", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "装配适配器后模型输出的困惑度 PPL", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "部分触发词下的误触发率 FTR", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "下游任务准确率，对照 task-only LoRA", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "触发词出现后的输出文本与后门成功率", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "用于合并缓解的自建安全数据集与 Safety LoRA", "where": "client_pre_train", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["exclude_client", "repair_model", "report_only"],
  "intervention_where": "both",
  "assumptions": [
    "攻击者能获得目标基座模型",
    "攻击者能获得一个与基座模型兼容的社区共享任务增强 LoRA",
    "攻击者能获得或自行构造特定后门行为的数据集",
    "用户会自愿下载社区共享适配器并说出触发词",
    "LoRA 权重无法被直接检查出后门感染",
    "后门能力主要存储在 FF 模块，可与下游任务能力在权重层面解耦",
    "后门数据集的 completion 需要多样化才有利于合并",
    "分享社区没有中心化权威审查适配器",
    "本地部署时没有外部监督可以介入"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Section 1.2", "supports": "第 5 节与第 9 节：权重本身不足以检测后门，是本文威胁模型的核心前提", "text": "Since LoRA weights cannot be directly inspected for backdoor infections, a unique security risk emerges in the share-and-play ecosystem."},
    {"section": "Section 1.3", "supports": "第 3 节与第 4 节：FF-only 后门 LoRA 加免训练合并是攻击的核心入口与配方", "text": "by training a feed-forward network (FF)-only LoRA adapter on various backdoor tasks, we can then — in a training-free fashion — merge this backdoor-only LoRA"},
    {"section": "Section 2", "supports": "第 4 节：合并使用最简单的逐点算术合并，并由 HuggingFace PEFT 原生实现", "text": "we employ basic point-wise arithmetic LoRA merging for its simplicity and the fact that it is natively supported in the HuggingFace PEFT package via a straightforward add_weighted_adapter() function call."},
    {"section": "Section 3", "supports": "第 2 节与第 3 节：攻击者目标、攻击经模型分发进入、在部署时由触发词激活", "text": "a successful LoRATK attempt would result in a user downloading a community-shared, downstream-capable yet backdoor-infected LoRA, equipping it to the corresponding base model, utilizing it without suspicion, and then activating the backdoor behavior by mentioning the encoded trigger word."},
    {"section": "Section 3", "supports": "第 3 节本地数据准备与第 4 节 OB 1：用 DeepSeek-R1 做多样化 completion 重建", "text": "Specifically, in our LoRATK recipe, we leverage a powerful LLM like DeepSeek-R1 to reconstruct the completion/label portion of existing backdoor datasets into more diverse variations."},
    {"section": "Section 4 (OB 2)", "supports": "第 4 节与第 7 节：后门主要位于 FF 模块，这是 FF-only Merge 的依据", "text": "We find that, for a backdoor LoRA, the FF module primarily stores the backdoor influence. This is evidenced by the FF-only backdoor LoRA outperforming backdoor LoRAs in QV, QK, QKV, QKVO, and QKVOFF in terms of backdoor effectiveness."},
    {"section": "Section 4 (OB 3)", "supports": "第 5 节与第 6 节：模块格式审查是论文唯一给出的具体防御及其干预方式", "text": "As such, platform moderators or knowledgeable users could flag and reject all LoRA submissions in this format, leading to a low false-positive rate defense since typically fewer than 10 benign LoRAs adopt this configuration."},
    {"section": "Appendix C.1", "supports": "第 5 节与第 7 节：困惑度痕迹极小，Table 7 报告约 3.6% 的上升", "text": "As shown in table 7, we observe only a minor increase in perplexity (∼3.6%), suggesting that LoRATK introduces negligible distributional disturbance."},
    {"section": "Appendix C.3", "supports": "第 6 节与第 7 节：SafetyFinetuning 式的合并缓解对隐蔽后门基本无效，Table 9", "text": "However, we find that SafetyFinetuning is not able to provide meaningful mitigation against stealthy backdoor behavior, as shown in Table 9"},
    {"section": "Limitations", "supports": "第 9 节：论文自述局限，提醒不要把结论推广到未评估的后门目标", "text": "Despite our efforts to provide comprehensive coverage, backdoor attacks remain highly diverse. We caution readers against generalizing our findings to unseen backdoor objectives without proper evaluation."}
  ]
}
```
