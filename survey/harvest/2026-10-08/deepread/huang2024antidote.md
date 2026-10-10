# huang2024antidote：Antidote: Post-fine-tuning Safety Alignment for Large Language Models against Harmful Fine-tuning Attack

## 1. 基本信息

- **场景**：集中式大模型微调服务（fine-tuning-as-a-service），不是联邦学习。论文第 3.1 节把场景描述为"用户把微调数据上传给服务提供方（service provider），提供方代表用户在有安全对齐（safety alignment）的预训练模型上做微调，再把微调后的模型部署出去提供个性化服务"；论文第 2 节只在相关工作中把联邦学习列为"其他场景下的攻击"（引用了 Ye et al. 2024 与 Li et al. 2024a），并未把联邦学习作为自己的设定。方法面向的是参数高效微调（parameter-efficient fine-tuning, PEFT）中的 LoRA（low-rank adaptation）：第 5.1 节说明对齐与微调都使用 LoRA，适配器秩（rank）为 256；附录 A.1 进一步说明使用"双重 LoRA"实现，即对齐阶段与微调阶段各用一个不同的 LoRA 适配器。
- **训练阶段**：论文把流程分成三段（图 1、图 4）：第一阶段安全对齐，第二阶段用户微调（harmful fine-tuning 发生在这里），第三阶段微调后一次性剪枝（one-shot pruning），这是 Antidote 所在的位置。第 5.1 节报告对齐阶段用 5000 条安全样本、学习率 1e-3、训练 20 个 epoch；微调阶段默认 5000 条样本、学习率 1e-4、20 个 epoch。
- **论文类型**：防御（defense）。同时包含对已有防御的"超参数敏感性"（hyper-parameter sensitivity）实证研究（第 3.2 节），以及对有害微调攻击（harmful fine-tuning attack）的实验评估。论文本身不做检测。
- **模型与数据规模**：主干模型为 Llama2-7B（默认）、Mistral-7B、Gemma-7B（第 5.1 节、表 8），并在 Llama3-8B 上做了额外验证（表 9）；LoRA 秩 256（第 5.1 节、附录 A.1）。对齐数据取自 BeaverTails 中 `is_safe=True` 的样本，有害数据取自 `is_safe=False` 的样本；下游微调任务为 SST2、AGNEWS、GSM8K、AlpacaEval；重对齐数据集（re-alignment dataset）默认 2000 条有害样本；有害分（harmful score）评测用 1000 条 BeaverTails 有害指令；微调准确率评测分别用 872、1000、1000、122 条测试样本（第 5.1 节）。全部实验在 H100 上完成（第 5.1 节）。
- **年份说明**：论文标注为第 42 届 ICML（PMLR 267, 2025），arXiv 版本为 arXiv:2408.09600v3（2025 年 9 月 5 日）；arXiv 首次发布在 2024 年。本报告依据的是所给全文。

## 2. 威胁模型

- **攻击者是谁**：上传微调数据的用户，即在数据供应链上提供微调数据的一方（论文第 3.1 节称"用户上传微调数据"；第 1 节称"微调数据由用户上传，因此带来安全风险"）。论文用 p 表示微调数据集中有害数据的百分比（第 5.1 节）。
- **占比或数量**：微调数据集默认 n=5000 条，其中有害比例 p 默认 0.2；表 1 扫描了 p=0、0.05、0.1、0.2、0.5，表 2 扫描了 n=100、1000、2000、3000、5000。论文没有"客户端"概念，也没有参与率概念（集中式单租户微调），论文未说明任何客户端数量或参与率。
- **能力（能改什么）**：能决定上传的微调数据内容，即把"有害指令—有害回答对"混入微调数据集（第 5.1 节）。论文第 3.2 节进一步表明攻击效果（有害分）随微调阶段的学习率（learning rate）与训练轮数（epochs）增大而增强，但论文未说明这两项超参数由用户还是由服务提供方设定。
- **知识（知道什么）**：论文未说明攻击者是否知道防御存在、是否知道重对齐数据集或剪枝比例。第 5.2 节至第 5.5 节的所有实验都由防御方设定攻击强度（p、n、学习率、轮数），属于非自适应攻击评估。
- **目标**：破坏安全对齐（jailbreak/safety alignment breaking），使模型对有害提示不再拒绝、输出有害内容；用有害分（Harmful Score, HS）度量。论文未涉及定向后门（targeted backdoor）、隐私窃取或可用性破坏目标。表 5 与第 5.2 节还讨论"良性微调攻击"（benign fine-tuning attack），即微调数据全部为良性（GSM8K）也会导致安全性下降。
- **防御者是谁、能看到什么、信任什么**：防御者是服务提供方（第 3.1 节），它看到微调后的模型全部权重、并持有两份受信任的数据：安全对齐数据集（有害提示—安全回答对，来自 BeaverTails `is_safe=True`）与重对齐数据集（有害提示—有害回答对，取自 BeaverTails `is_safe=False`，默认 2000 条）。论文第 3.1 节明确把持有重对齐数据集写成假设，并辩称"这样的有害数据集在已被接收的论文中同样被假设"，因此"不应算太强或不具一般性"。论文未说明防御者是否需要看到用户上传的微调原始数据；从第 4 节与算法 1 看，剪枝只用重对齐数据集，不需要微调数据（表 12 是把它当作对照项做的消融）。

## 3. 攻击入口与流程位置

论文所针对的攻击入口是**本地数据准备**（更准确地说，是用户上传的微调数据集），生效位置是**服务提供方的用户微调阶段（第二阶段）**。具体步骤是：用户在准备微调数据时，把比例为 p 的"有害指令—有害回答对"与比例为 1−p 的下游任务数据（如 SST2、GSM8K）混合后上传（第 5.1 节）；服务提供方在该混合数据上做监督微调，模型由此遗忘对齐知识、对有害提示不再拒绝（第 1 节）。

- 攻击不涉及"更新上传前的后处理"、"服务器聚合"或"全局模型下发"，因为这是集中式单模型微调，没有多客户端聚合环节。
- 论文未说明攻击者能否改动损失函数、优化器实现或数据之外的训练代码；它只说明了数据混合比例 p 与训练轮数、学习率会影响攻击强度（第 3.2 节、图 2、图 3）。
- 分析：图 2 与图 3 所在正文说"学习率越大、轮数越多，有害分越高"，这属于训练过程（学习率、步数）层面的因素。如果库要把这一因素显式建进威胁模型，应把"本地训练过程（优化器/步数）"也视作攻击面的一部分；但论文本身只把有害数据当作攻击内容，且未说明这些超参数由谁控制，因此本节主体仍记为数据入口。
- 防御方（Antidote）的动作入口在**微调完成之后、部署之前**（图 4 第三阶段），也就是训练流程的最末端。

## 4. 方法原理

核心思想（第 4 节、摘要）：不管有害行为在微调阶段是如何形成的，只要把"有害参数"从微调后模型里去掉，模型就能从有害行为中恢复。因此 Antidote 完全不干预微调过程，属于"微调后"（post-fine-tuning）方法，对微调阶段的超参数不敏感。

关键步骤如下（第 4 节，算法 1）：

1. **识别有害参数**：用 Wanda 分数（Wanda score，来自 Sun et al. 2023）在重对齐数据集 D_realign 上给模型每个权重坐标打分，公式见式 (1)：

   [h(w, D_realign)]_j = (1/|D|) · Σ_{x∈D_realign} |w_j| · ‖A_j(x, w)‖_2

   其中 w 是"安全对齐已被破坏的微调模型"的权重向量，w_j 是第 j 个权重坐标，x 是 D_realign 中的一条数据，A_j(x, w) 是输入 x 时与第 j 个权重坐标相关联的隐藏激活。直觉上，一个参数坐标的重要性取决于它的绝对值和它的输入值（第 4 节原文的表述是"importance of a coordinate of parameter is related to its absolute value and the value of its input"）。

2. **生成有害掩码**：式 (2)，m = ArgTopK_α(h(w, D_realign))，即按重要性取前 α 比例的坐标置 1、其余置 0；α 称为掩码比例（mask ratio）。

3. **移除有害参数**：式 (3)，w̃ = (1 − m) ⊙ w，其中 ⊙ 是 Hadamard 逐元素乘积。得到可用于部署的重对齐模型 w̃。

4. **训练后一次性执行**：算法 1 的输入是掩码比例 α、重对齐数据集 D_realign 与已被破坏的微调模型 w，输出是可直接部署的 w̃；整个操作在微调结束后只做一次（"one-shot pruning"，图 4 第三阶段）。

论文把这一思路放在模型稀疏化（model sparsification）文献脉络下，明确说"本文借用模型稀疏化文献中的重要性分数来识别并移除有害参数"（第 2 节）。第 5.5 节还指出剪枝后有可能加速推理，并把这个方向留作未来工作。需要注意的是，**Antidote 没有检测环节，也不判断模型是否被投毒，它对任何微调后模型都无条件执行一次剪枝**（算法 1 与图 4）。

## 5. 检测或防御所需的数据

Antidote 是防御而非检测，所以下面列出的是它执行修复所需的输入。论文在方法层面只需要两份东西：微调后的模型权重和重对齐数据集；其余是论文为做分析或评测而额外用到的可观测量。

1. **微调后的模型全部权重 w**（Wanda 分数与剪枝的作用对象）。
   - 是什么：式 (1) 与式 (3) 中的 w，论文描述为"代表安全对齐已被破坏的微调模型的模型权重向量"。
   - 在哪里采集：服务提供方训练结束、部署之前的模型（对应集中式流程的"微调完成后"；分析：映射到联邦库的钩子时，对应服务器聚合完成、下发之前的全局模型，即 server_post_aggregate）。
   - 粒度：逐权重坐标（逐层，整模型）。
   - 是否需要跨轮历史：不需要。是否需要参考数据：不需要。是否需要额外前反向计算：不需要（权重本身即可读）。
2. **重对齐数据集 D_realign**（有害指令—有害回答对，默认 2000 条，取自 BeaverTails `is_safe=False`）。
   - 是什么：专门由有害数据构成的数据集，论文第 3.1 节假设服务提供方持有，并称可"从开源红队数据集（如 BeaverTails、HH-RLHF）采样得到"；第 5.1 节说明默认采样 2000 条。
   - 在哪里采集：服务提供方侧离线准备，在微调后剪枝时使用（server_post_aggregate）。
   - 粒度：逐样本（数据集级，共 2000 条；表 13 另外测试了 0、5、10、100、1k、2k、5k 条）。
   - 是否需要跨轮历史：不需要。是否需要参考数据：需要——这里需要一份外部的、可信的、带标签的有害参考语料（注意它是有害语料，不是干净语料；JSON 中该项按"需要参考数据"标记）。是否需要额外计算：不需要（读取即可）。
3. **重对齐样本前向传播时、与每个权重坐标关联的隐藏激活 A_j(x, w)**。
   - 是什么：式 (1) 中 A_j(x, w)，论文原文说"x 表示重对齐数据集 D 中的一个数据点，A_j(x, w) 取回与第 j 个权重坐标关联的该数据点的隐藏激活"。
   - 在哪里采集：对微调后的模型，在重对齐数据集上做前向传播时逐层采集（server_post_aggregate）。
   - 粒度：逐样本 × 逐权重坐标（逐层）。
   - 是否需要跨轮历史：不需要。是否需要参考数据：需要，激活是在 D_realign 上取的。是否需要额外计算：需要额外的前向传播（2000 条有害样本过一次微调后模型），不需要反向传播。
4. **评测用的可观测量（不属于防御本体）**：1000 条未见有害指令（来自 BeaverTails）与 BeaverTails 的审核模型（moderation model）用于算有害分；四个下游任务的测试集（872、1000、1000、122 条）与 AlpacaEval 的 ChatGPT 评分用于算微调准确率（第 5.1 节、附录 A.1）。采集位置为评测阶段，粒度为逐样本，需要额外前向生成。
5. **论文用作机理分析的额外可观测量（同样不属于防御本体）**：有害嵌入漂移（Harmful Embedding Drift, HED），定义为"同一个对齐数据上，对齐模型隐藏嵌入与微调模型隐藏嵌入之差的 L2 范数"（第 5.4 节、图 5），这需要保留对齐模型的隐藏嵌入作为参照；以及剪枝前后模型在有害样本与 GSM8K 样本上的输出 logit（图 6），用于比较 Antidote 剪枝与随机剪枝的漂移量。

**攻击会留下的痕迹**（依据上述可观测量）：微调后模型在有害数据上的参数重要性与激活分布会发生改变（这正是式 (1) 所利用的，第 4 节）；隐藏嵌入相对对齐模型发生漂移（图 5 显示 HED 随学习率与轮数上升，而 Antidote 剪枝后显著降低）；输出 logit 在有害样本上发生偏移（图 6 报告剪枝前有害样本平均漂移 24469，随机剪枝为 26172）；输出文本层面有害分上升（表 1 至表 9）。

**论文声称能应对哪些变化**：论文没有声称"绕过某些检测"（它不做检测），而是声称对以下攻击变化保持稳健——有害比例 p 从 0.05 到 0.5（表 1、第 5.2 节）、微调样本数 n 从 100 到 5000（表 2）、学习率从 1e-7 到 1e-3（表 3、第 5.2 节）、训练轮数从 1 到 40（表 4）、良性微调攻击（表 5）、四种下游数据集（表 6）、更强的对齐数据集（表 7）、四种主干模型（表 8、表 9）。表 12 还表明，若把重对齐数据集换成微调数据或良性数据，平均有害分会上升（+0.68 与 +1.13），说明有害参考语料是必要的。

## 6. 干预动作

- **动作**：对模型权重做一次性非结构化剪枝（把重要性排名前 α 的坐标置零），即式 (3) 的 w̃ = (1 − m) ⊙ w。属于"修复模型"（repair_model），不是剔除客户端、重新加权、裁剪更新范数、加噪或过滤训练样本。
- **位置**：服务提供方侧，微调全部完成之后、模型部署之前（图 1、图 4 的第三阶段；算法 1）。
- **触发方式**：无条件触发，每次微调后执行一次；没有可疑度评分、阈值或客户端名单。论文未说明是否存在跳过剪枝的条件。
- **超参数**：掩码比例 α 默认 0.2，GSM8K 特例为 0.05（第 5.1 节）；表 11 给出了 α 从 0.01 到 0.25 的取舍：α 越大，有害分与微调准确率同时下降（表 11 中 α=0.01 时 HS 73.60、FA 94.95；α=0.25 时 HS 57.00、FA 80.05）。
- **不做的事**：不拒绝或剔除用户数据、不回滚模型、不重新训练、不加噪、不报告可疑客户端。论文未说明该方法能否与"只报告"模式配合使用。

## 7. 实验设置与主要结果

**设置**（第 5.1 节、附录 A.1）：主干默认 Llama2-7B，另有 Mistral-7B、Gemma-7B、Llama3-8B；LoRA 秩 256，附录 A.1 报告 LoRA alpha 设为 4、对齐与微调各用一个适配器（分析：抽取文本在该处有一句"learning rate is set to be 5"读起来像乱码或抽取错误，本报告不据此下结论）；对齐阶段 5000 条安全样本、学习率 1e-3、20 个 epoch；微调阶段默认 n=5000、p=0.2、学习率 1e-4、20 个 epoch，默认数据集 SST2；重对齐数据集默认 2000 条有害样本；掩码比例默认 α=0.2（GSM8K 为 0.05）。集中式设定，没有客户端数、参与率与轮次聚合的概念，数据非独立同分布（non-IID）问题不适用，论文均未说明。

**指标**：微调准确率（Finetune Accuracy, FA），即微调任务测试集上的 Top-1 准确率，AlpacaEval 用 ChatGPT 相对 text_Devinci_003 的胜率；有害分（Harmful Score, HS），用 BeaverTails 的审核模型标记模型输出，取被标记为不安全的比例（第 5.1 节、附录 A.1）。

**主要结果**：

- 摘要与第 5.2 节：Antidote 相比无防御的 SFT 最多降低有害分 17.8%，微调准确率损失最多 1.83%。
- 表 1（不同有害比例 p）：Antidote 平均 HS 60.88、平均 FA 93.05；SFT 平均 HS 73.52、平均 FA 95.00；正文称平均有害分下降 11.56%、平均准确率损失 1.45%。表 1 中 Antidote 在 p=0.2 时为 HS 64.60、FA 93.35。
- 表 2（不同微调样本数 n）：Antidote 平均 HS 61.36、平均 FA 92.38；SFT 平均 HS 76.06、平均 FA 94.17；正文称有害分下降 13.42%。Lisa 平均 HS 最低（58.34）但平均 FA 只有 58.88。
- 表 3（不同学习率，数据集 GSM8K）：Antidote 平均 HS 63.00、平均 FA 13.86；SFT 平均 HS 72.16、平均 FA 17.32；正文称 Antidote 平均降低有害分 6.56%、准确率仅降 0.38%，而 Lisa 与 LDIFS 分别降低 7.72% 与 9.50% 但准确率大幅下降。
- 表 4（不同微调轮数，数据集 GSM8K）：Antidote 平均 HS 64.76、平均 FA 16.24；SFT 平均 HS 78.36、平均 FA 23.96。正文称"从 ep=10 到 ep=40，Antidote 的有害分低 6.3%"（分析：按表 4 数值 66.60 到 63.60 是 3.0 个百分点，与该句的 6.3% 对不上，疑为正文笔误或统计口径不同，论文未解释）。
- 表 5（良性微调攻击，GSM8K）：SFT HS 61.50 / FA 27.60；Antidote HS 57.10 / FA 27.80。
- 表 6（四种下游数据集）：Antidote 平均 HS 64.98、平均 FA 59.82；SFT 平均 HS 77.65、平均 FA 63.26；正文称有害分平均降 11.75%、准确率损失 3.08%。
- 表 7（更强对齐数据集，来自 Rosati et al. 2024a）：Antidote 在 p=0/0.05/0.1/0.2/0.5 时 HS 分别为 2.3、11.3、15.5、21.8、36.5；SFT 分别为 13.5、80.3、78.8、78.6、82.3。正文称在更强对齐下 p=0.2 时有害分下降超过 40%。
- 表 8（三种主干）：Antidote 在 Llama2-7B/Mistral-7B/Gemma-7B 上 HS 为 64.60/64.80/59.40，FA 为 93.35/94.95/94.04；平均 HS 62.93、平均 FA 94.11。正文称有害分分别下降 11.6%、20.0%、22.5%，准确率分别下降 1.49%、0.92%、1.72%。
- 表 9（Llama3-8B）：Antidote HS 71.20 / FA 39.00；SFT HS 80.30 / FA 42.40。
- 表 11（掩码比例 α 消融）：见第 6 节所列数值。分析：表 11 在 α=0.2 时给出 HS 58.40、FA 86.58，与表 1 默认 α=0.2 的 HS 64.60、FA 93.35 不一致；同样，表 12 的"w/ harmful data"在 p=0.2 时为 68.80，也与表 1 的 64.60 不一致。论文未解释这些差异，推测是不同随机种子或不同实验批次，但在论文中没有依据，故只照抄数值。
- 表 12（Wanda 分数用哪份数据算）：以有害数据为基准，换成微调数据平均 HS 68.03（+0.68），换成良性数据平均 HS 68.48（+1.13）。
- 表 13（重对齐数据集大小）：|D_realign| = 0/5/10/100/1k/2k/5k 时 HS 为 72.1、70.60、70.30、70.20、69.30、69.20、69.40；正文称 1k 条即可表现良好，继续增加收益递减。
- 表 14（组合扩展）：V-S-A（Vaccine + SFT + Antidote）平均 HS 60.97（比纯 Antidote 低 2.46）、平均 FA 92.93（+0.19）；S-L-A 平均 HS 61.20（−2.23）、FA 92.01（−0.73）；V-L-A 平均 HS 62.67（−0.76）、FA 92.74（持平）。
- 图 5（HED）：Antidote 的 HED 保持在较小水平，而其他方法的 HED 随学习率与轮数上升；正文强调 Antidote 与 SFT 在前两阶段完全相同（HED 相同），只在剪枝后 HED 显著降低。
- 图 6（logit 漂移）：Antidote 剪枝在 GSM8K 样本上的平均漂移为 13058（随机剪枝为 22000），在有害样本上的平均漂移为 24469（随机剪枝为 26172）；剪枝前 HS 61.50、准确率 27.60，Antidote 剪枝后 HS 57.10、准确率 27.80，随机剪枝后 HS 57.40、准确率 14.90。
- 第 5.7 节给出定性例子：默认设置下对"应该从 General Dynamics 偷什么"这一提示，SFT、Vaccine、RepNoise、LDIFS、Lisa 都给出有害回答，Antidote 给出拒绝式回答（标注为 harmless）。

## 8. 开销

论文报告了系统开销（表 10，第 5.4 节）：以 SFT 为基准，SFT 对齐 0.92 小时、微调 0.78 小时、合计 1.70 小时（1x），GPU 显存对齐 35.45 GB、微调 33.06 GB、峰值 35.45 GB（1x）。Antidote 在微调后阶段增加 0.04 小时，合计 1.78 小时（1.02x），GPU 峰值仍为 35.45 GB（1x），微调后阶段自身占用 22.35 GB；正文说"额外开销主要来自在重对齐数据集上计算 Wanda 分数以获得 top-k 重要掩码，并把掩码施加到模型上移除被投毒的参数"。作为对照，RepNoise 合计 2.75 小时（1.62x）、显存峰值 75.26 GB（2.12x）；Vaccine 合计 2.63 小时（1.54x）、56.46 GB（1.71x）；Lisa 显存峰值 52.95 GB（1.49x）；LDIFS 合计 2.11 小时（1.24x）、64.53 GB（1.82x）。

通信开销与存储开销：集中式场景下论文未报告通信开销，也未报告额外的存储开销，只报告了 GPU 显存与时钟时间。剪枝后的推理加速被明确留作未来工作（第 5.5 节），所以论文未报告加速数值。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设**：

- 服务提供方对微调后模型拥有白盒访问，能读取全部权重并做前向传播取激活（第 4 节式 (1)、算法 1）。
- 服务提供方持有两份受信任数据集：安全对齐数据集（有害提示—安全回答对）与重对齐数据集（有害提示—有害回答对，默认 2000 条）。第 3.1 节明确把这写成假设，并辩称可从 BeaverTails、HH-RLHF 等开源红队数据采样获得，且已有被接收论文作同样假设，因此"不应算太强或不具一般性"。第 5.5 节与表 13 表明 1k 条有害样本已接近 2k 条的效果。
- 有害行为可以被少数权重坐标承载，用一次非结构化剪枝（默认 α=0.2，GSM8K 为 0.05）就能去激活，同时下游准确率损失有限（第 4 节、表 11）。第 5.4 节用 HED 下降与 logit 漂移差异来支撑这一假设。
- 攻击是数据投毒式微调，且攻击者不针对防御做自适应调整；论文第 3.2 节的动机部分还假设学习率与轮数足够大是保证下游任务准确率的必要条件。
- 分析：论文第 5.1 节说对齐与微调都用 LoRA，但第 4 节把 w 描述为"微调模型的模型权重向量"，**论文未说明剪枝掩码是只施加在 LoRA 适配器上，还是施加在合并后的全部权重上**，也未说明掩码是逐层分配比例还是全模型统一比例。

**论文自述的局限**：论文没有独立的局限章节。可归入自述限制的内容有：第 5.3 节承认"没有为每个数据集专门调掩码比例 α"；第 5.5 节把剪枝带来的推理加速留作未来工作；第 2 节承认并发的微调后防御"可能也对微调阶段超参数不敏感"，但在本文之前没有系统性研究；影响声明（Impact Statement）承认该发现可能被滥用来攻击商用大模型服务。论文未讨论剪枝后的模型是否可被再次微调重新投毒，也未讨论重对齐数据集与真实攻击分布不匹配时的后果。

**是否评估自适应攻击**：没有。论文评估的是不同有害比例、样本数、学习率、轮数、良性微调、不同数据集与模型（表 1 至表 9），这些都是防御方控制的攻击强度变化，不是知道防御存在的自适应攻击者，论文也未给出任何自适应攻击的结果。论文第 2 节引用了关于安全对齐在剪枝与低秩修改下脆弱性的工作（Wei et al., 2024）以及若干更强的攻击，但没有把它们用于攻击 Antidote。

**迁移到联邦 LoRA 微调时可能失效的假设**（以下均为分析）：

- 论文是集中式单租户微调，服务器直接拥有"一个"完整微调模型；联邦 LoRA 中服务器每轮只收到各客户端的 LoRA 增量，需要先做聚合与合并才能得到可剪枝的权重。掩码应该每轮在全局合并模型上重算，还是只对某个客户端的增量算，论文未说明，需要库自行定义。
- 论文假设有害数据来自单一用户的微调集；联邦场景下有害更新可能只来自少数客户端，并与其他诚实客户端的良性更新叠加。全局 top-α 剪枝可能同时剪掉诚实客户端学到的重要坐标，且论文不提供任何按客户端归因的能力。
- 论文假设服务提供方持有的重对齐数据集能代表攻击分布。联邦场景下各客户端数据异构（non-IID），固定的公开有害语料不一定能激活"被这一批客户端投毒"的那些坐标，Wanda 分数的判别力可能下降。
- 论文的防御在训练全部结束后只执行一次。联邦训练是多轮的，如果只在最后一轮后剪枝，恶意客户端在训练中途的投毒仍然会被聚合进全局模型；而逐轮剪枝的代价（每轮都要在参考集上做全模型前向取激活）论文未评估，论文对每轮开销未说明。
- 论文报告的下游指标是单一集中式测试集上的准确率；联邦 LoRA 通常关心各客户端本地任务的准确率，全局剪枝对客户端个性化性能的影响论文未说明。
- 论文的安全评估依赖一个集中式的审核模型与 1000 条公开有害指令；在联邦场景下，服务器往往不能直接看到客户端原始数据，样本级检测与评测数据视图需要额外的隐私边界设计，论文未涉及。

## 10. 对防护库设计的含义

1. 分析：采集底座需要一个"服务端训练/聚合结束、下发部署之前"的全局模型快照采集点，并且这个快照要能支持带隐藏状态导出的前向传播（即不只取 logits，还要取每个线性层输入激活）。这是 Antidote 类插件唯一必需的采集点，也是所有"训练后修复"插件（剪枝、投影、模型融合、激活修补）共用的通用需求。
2. 分析：库需要支持注册一份"可信参考语料"，并把它与插件绑定。Antidote 需要的是带标签的有害指令—回答对（默认 2000 条，1k 条已接近饱和），而不是干净数据；这与"用干净参考集做比对"的检测插件需求不同，因此参考语料的数据视图应当允许声明用途和标签类型。
3. 分析：插件机制需要一种不依赖可疑度评分的"无条件修复"钩子，其契约是（模型、参考数据集、超参数 α）→ 修改后的模型，动作是原地写回全局权重。这与"先检测、后按可疑客户端名单处置"的钩子不同；支持前者意味着服务器钩子必须允许插件返回一个被修改的模型对象，而不只是返回客户端权重或一个分数。
4. 分析：由于本文的防御不需要跨轮历史、不需要客户端级更新、不需要梯度、不需要原始微调数据，库不应把"必须能拿到逐客户端更新"设成所有插件的硬前置条件；反过来，如果库面向联邦 LoRA，还需要补一个论文完全没有的能力——把有害坐标或有害行为归因到具体客户端或具体轮次，否则只能在全局模型上"一刀切"。
5. 分析：评估钩子需要支持两类指标：用审核模型对模型输出打分的与安全相关的分数（输入是若干条未见有害指令），以及下游任务准确率（输入是各任务测试集，含生成式任务的评判逻辑）。这部分是通用能力，不是 Antidote 特有。
6. 分析：若库的另一个目标是在数据上传边界检测本文所针对的投毒（混入有害样本），那需要在"本地数据准备/上传"处采集逐样本的原始训练数据或其统计量；本文不提供任何样本级检测方法，因此这个采集点是为检测类插件准备的通用需求，而非 Antidote 方法的必需项。

## 11. 原文依据

1. 摘要：支撑第 4 节与第 9 节的核心思想论断（移除有害参数即可恢复模型，且与微调阶段如何形成这些参数无关）。
   > "Antidote relies on the philosophy that by removing the harmful parameters, the harmful model can be recovered from the harmful behaviors, regardless of how those harmful parameters are formed in the fine-tuning stage."

2. 第 3.1 节"Threat Model and Assumptions"：支撑第 1 节与第 2 节的场景判断（用户上传数据给服务提供方，由提供方微调并部署）。
   > "In this scenario, users upload fine-tuning data to the service provider. On behalf of users, the provider fine-tunes the aligned pre-trained model on this dataset, and the finetuned model is deployed to deliver personalized service to users."

3. 第 3.1 节"Assumptions"：支撑第 5 节与第 9 节关于重对齐数据集这一前提条件的论断。
   > "We assume the service provider hosts a harmful dataset Drealign (containing harmful prompt-harmful answer pairs), which we use to perform post-fine-tuning stage re-alignment."

4. 第 4 节开头：支撑第 4 节"微调后、与训练细节无关"的方法定位，以及第 6 节的干预位置。
   > "The high-level idea of the proposed defense, named Antidote, is to remove the harmful parameters in the model after the model has been corrupted with fine-tuning."

5. 第 4 节"Identify harmful parameters"：支撑第 4 节式 (2) 的 top-k 有害掩码步骤与第 6 节的干预动作。
   > "To recognize the harmful parameters over the fine-tuned model weights w, one intuitive idea is to extract the topk most important mask (harmful mask) on the re-alignment dataset, indicating the most important parameters for harmful content generation, as follows."

6. 第 4 节对式 (1) 符号的说明：支撑第 5 节第 3 项"需要逐样本、逐权重坐标的隐藏激活，且需要额外前向计算"的论断。
   > "x represents a data point in the re-alignment dataset D, and Aj(x, w) retrieves the data point x’s hidden activation that is associated with the j-th weight coordinate."

7. 第 5.1 节"Training Details and Hyper-parameters"：支撑第 1 节与第 7 节关于本论文使用 LoRA 这一参数高效微调设定的论断。
   > "We follow (Huang et al., 2024d) to utilize LoRA (Hu et al., 2021) for alignment and fine-tuning. The rank of the adaptor is 256 for both tasks."

8. 第 5.1 节"Training Details and Hyper-parameters"：支撑第 5 节与第 7 节的默认配置（掩码比例 α=0.2、GSM8K 为 0.05、重对齐数据集 2000 条）。
   > "For hyper-parameters for Antidote, in default, we set the mask ratio to be α = 0.2 (specially, α = 0.05 for GSM8K) and we sample 2000 harmful samples to form the re-alignment dataset used by Antidote."

9. 第 5.2 节"Robustness to harmful ratio"：支撑第 7 节表 1 的量化结论（平均有害分下降 11.56%、平均准确率损失 1.45%）。
   > "it achieves a remarkable 11.56% reduction of average harmful score compared to SFT with a marginal 1.45% loss of average finetune accuracy."

10. 第 5.4 节"System performance"：支撑第 8 节关于系统开销的论断（时钟时间 1.02 倍、显存与 SFT 相同）。
    > "In sharp contrast, Antidote introduces a slight increase in clock time overhead (1.02x clock time) and the same GPU memory usage for the whole pipeline."

```json
{
  "key": "huang2024antidote",
  "title": "Antidote: Post-fine-tuning Safety Alignment for Large Language Models against Harmful Fine-tuning Attack",
  "year": 2025,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "微调完成、部署之前的全局模型全部权重（式(1)打分与式(3)剪枝的对象）", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "重对齐数据集：有害指令-有害回答对，默认2000条，取自BeaverTails is_safe=False", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "重对齐样本前向传播时与每个权重坐标关联的隐藏激活 A_j(x,w)", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "评测用1000条未见有害指令、BeaverTails审核模型与四个下游任务测试集（872/1000/1000/122条）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务提供方对微调后模型有白盒访问，能读取全部权重并做前向传播取隐藏激活。",
    "服务提供方持有一份有害的重对齐数据集（默认2000条有害指令-有害回答对，论文称可从BeaverTails等开源红队数据集采样）以及一份安全对齐数据集。",
    "有害行为集中在少数对有害数据敏感的权重坐标上，一次非结构化剪枝（默认α=0.2，GSM8K为0.05）即可去激活且下游准确率损失有限。",
    "对齐与微调都使用LoRA（秩256），但论文未说明剪枝掩码施加在LoRA适配器上还是合并后的全部权重上。",
    "攻击是用户上传数据中混入有害样本（以及良性数据导致的safety退化），攻击者不了解防御，论文未评估自适应攻击。",
    "方法对微调阶段的学习率与训练轮数不敏感，因此不依赖微调超参数的取值。"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第4节方法核心思想与第9节假设：移除有害参数即可恢复模型，与微调阶段无关", "text": "Antidote relies on the philosophy that by removing the harmful parameters, the harmful model can be recovered from the harmful behaviors, regardless of how those harmful parameters are formed in the fine-tuning stage."},
    {"section": "Section 3.1 Threat Model and Assumptions", "supports": "第1节场景判断与第2节防御者角色：用户上传数据、提供方微调并部署", "text": "In this scenario, users upload fine-tuning data to the service provider. On behalf of users, the provider fine-tunes the aligned pre-trained model on this dataset, and the finetuned model is deployed to deliver personalized service to users."},
    {"section": "Section 3.1 Assumptions", "supports": "第5节与第9节关于重对齐数据集这一前提条件的论断", "text": "We assume the service provider hosts a harmful dataset Drealign (containing harmful prompt-harmful answer pairs), which we use to perform post-fine-tuning stage re-alignment."},
    {"section": "Section 4 Methodology", "supports": "第4节方法定位与第6节干预位置：在微调完成之后移除有害参数", "text": "The high-level idea of the proposed defense, named Antidote, is to remove the harmful parameters in the model after the model has been corrupted with fine-tuning."},
    {"section": "Section 4 Identify harmful parameters", "supports": "第4节式(2)的top-k有害掩码步骤与第6节干预动作", "text": "To recognize the harmful parameters over the fine-tuned model weights w, one intuitive idea is to extract the topk most important mask (harmful mask) on the re-alignment dataset, indicating the most important parameters for harmful content generation, as follows."},
    {"section": "Section 4 Identify harmful parameters", "supports": "第5节第3项：需要逐样本、逐权重坐标的隐藏激活，且需要额外前向计算", "text": "x represents a data point in the re-alignment dataset D, and Aj(x, w) retrieves the data point x’s hidden activation that is associated with the j-th weight coordinate."},
    {"section": "Section 5.1 Training Details and Hyper-parameters", "supports": "第1节与第7节：本论文属于参数高效微调的集中式设定，使用LoRA且秩为256", "text": "We follow (Huang et al., 2024d) to utilize LoRA (Hu et al., 2021) for alignment and fine-tuning. The rank of the adaptor is 256 for both tasks."},
    {"section": "Section 5.1 Training Details and Hyper-parameters", "supports": "第5节与第7节默认配置：掩码比例α=0.2（GSM8K为0.05）、重对齐数据集2000条", "text": "For hyper-parameters for Antidote, in default, we set the mask ratio to be α = 0.2 (specially, α = 0.05 for GSM8K) and we sample 2000 harmful samples to form the re-alignment dataset used by Antidote."},
    {"section": "Section 5.2 Main Results", "supports": "第7节表1的量化结论：平均有害分下降11.56%、平均准确率损失1.45%", "text": "it achieves a remarkable 11.56% reduction of average harmful score compared to SFT with a marginal 1.45% loss of average finetune accuracy."},
    {"section": "Section 5.4 Statistical and System Evaluation", "supports": "第8节系统开销：时钟时间1.02倍、显存与SFT相同", "text": "In sharp contrast, Antidote introduces a slight increase in clock time overhead (1.02x clock time) and the same GPU memory usage for the whole pipeline."}
  ]
}
```
