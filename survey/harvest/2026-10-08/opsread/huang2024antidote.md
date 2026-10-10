# huang2024antidote：Antidote（微调后一次性 Wanda 掩码剪枝）

## 1. 方法一句话

Antidote 的输入是"安全对齐已被 harmful fine-tuning（有害微调）破坏的微调后模型权重 w"和一份全部由有害样本构成的 re-alignment dataset（重对齐数据集）D_realign；它在这份数据上计算每个权重坐标的 Wanda 重要性分数 h(w, D_realign)（式 1），取出分数最高的 α 比例的坐标形成 harmful mask m（式 2），再把 m 命中的坐标置零得到 w̃ = (1 − m) ⊙ w（式 3），输出一个可直接部署的 re-aligned model（重对齐模型）（Algorithm 1）。它不是一个带阈值的检测器，唯一的选择规则是"按分数取 top-α"，唯一的动作是"把被选中的坐标删掉（置零）"，剪枝后不再训练。

## 2. 运行位置

论文把整体流程画成三段流水线（Figure 1）：i) safety alignment（安全对齐），ii) user fine-tuning（用户微调），iii) one-shot pruning（一次性剪枝）。Antidote 属于第三段，即**用户微调完全结束之后、模型部署给用户之前**，在服务提供方（service provider）一侧运行；它不进入任何训练步，也不修改对齐阶段或微调阶段的训练过程（Section 4、Figure 4）。

- 服务器下发前 / 客户端训练前 / 客户端每个训练步 / 客户端上传前 / 服务器收到更新：论文未在联邦场景中讨论 Antidote，这些位置都不适用。
- **聚合之后（post-aggregate）**：分析：把 Antidote 放进联邦运行时，最自然的落点是服务器在收到并聚合完客户端更新、拿到当前全局模型之后、下发或部署之前对全局模型做一次处理；论文中与"聚合后全局模型"对应的对象就是 w（"a vector representing model weights of the safety-alignment broken fine-tuned model"）。
- **训练之外（outside training）**：分析：论文的语义是"fine-tuning has been fully completed"之后一次性执行（Section 4、Algorithm 1），所以更严格地说它位于训练循环之外，只在整个微调作业结束后执行一次，而不是每轮都做。
- 是否需要客户端与服务器之间额外往返：不需要。D_realign 由服务提供方自己持有（Section 3.1 Assumptions），整个方法的计算（前向统计、打分、top-k、置零）都在服务器本地完成。论文未涉及联邦通信，也未评测跨客户端场景。

## 3. 算子流水线

以下步骤按执行顺序排列。需要注意：论文只给出式 (1)–(3) 与 Algorithm 1 的三行伪代码，"收集激活"这一步是式 (1) 中 A_j(x, w) 所隐含的必要计算，论文没有单独描述其工程实现。

**步骤 1：在 re-alignment 数据集上前向收集激活统计**

- 输入：微调后的模型权重 w（论文把它记为一个向量，w_j 表示第 j 个权重坐标，也就是权重向量中的一个元素）；re-alignment 数据集 D_realign，其中每条样本 x 是 harmful prompt（有害提问）与 harmful answer（有害回答）的配对（式 1 上下文、Section 3.1）。论文未说明可剪枝坐标集合到底是哪些（例如是否含 embedding、LayerNorm、bias），也未说明 d 的具体量级。
- 计算：对 D_realign 中每条样本 x 做一次前向传播，取出与第 j 个权重坐标相关联的隐藏激活 A_j(x, w)，并计算它的 L2 范数 ‖A_j(x, w)‖₂（式 1 中的第二项）。这一项与权重项 |w_j| 的乘积随后在式 (1) 中对整个数据集求平均。分析：这一步只需要前向传播，不需要反向传播，因为 Wanda 分数只用到权重本身与输入激活。
- 输出：逐坐标的激活范数统计（可与权重项结合后得到长度约为 d 的重要性向量）。
- 论文出处：式 (1) 及其上下文（"Aj(x, w) retrieves the data point x's hidden activation that is associated with the j-th weight coordinate"）；激活项的具体抽取位置与归约方式论文未说明。

**步骤 2：计算 Wanda 重要性分数 h(w, D_realign)**

- 输入：每个坐标的权重值 w_j，以及步骤 1 得到的各样本激活 A_j(x, w)。
- 计算：式 (1)：[h(w, D_realign)]_j = (1/|D|) × Σ_{x∈D_realign} ( |w_j| · ‖A_j(x, w)‖₂ )。也就是说，第 j 个坐标的重要性 = 该坐标权重绝对值 × 该坐标对应输入激活的 L2 范数，再对所有 x ∈ D_realign 求平均；[·]_j 表示取向量的第 j 个元素。
- 输出：与权重坐标一一对应的重要性分数向量 h。
- 论文出处：式 (1)，Section 4 "Identify harmful parameters"，以及 "Intuitively, the importance of a coordinate of parameter is related to its absolute value and the value of its input."。特别地，当 |D_realign| = 0 时，该分数退化为坐标的权重幅度 |w_j|（Table 13 表注）。

**步骤 3：按比例取 top-k 生成 harmful mask m**

- 输入：重要性分数向量 h(w, D_realign)。
- 计算：式 (2)：m = ArgTopK_α(h(w, D_realign))。ArgTopK_α(·) 返回一个与坐标同长的 0/1 掩码，分数最高的那部分坐标置 1，其余置 0；α 是被置 1 的坐标比例，论文称之为 mask ratio（掩码比例）。若按字面理解，被选中的坐标数 k = α × 参与排序的坐标总数。
- 输出：二值 harmful mask m。
- 论文出处：式 (2) 及紧随其后的解释；Algorithm 1 第 2 行 "m = ArgTopKα(h(w, Drealign))"。论文未说明 ArgTopK 是在整个模型范围内全局取，还是逐层分配 α 的稀疏率。

**步骤 4：用 mask 对权重做一次性剪枝**

- 输入：harmful mask m 与微调后权重 w。
- 计算：式 (3)：w̃ = (1 − m) ⊙ w。其中 ⊙ 是 Hadamard product（逐元素乘积），1 是与 m 同形的全 1 向量；因此 m_j = 1 的坐标被置零，m_j = 0 的坐标原样保留。
- 输出：re-aligned model 的权重 w̃。
- 论文出处：式 (3)，Section 4 "Removal of Harmful parameter"，Algorithm 1 第 3 行 "˜w = (1 − m) ⊙w"。

**步骤 5：导出并部署**

- 输入：w̃。
- 计算：不做任何额外优化。论文写明 "The recovered model is then deployed to serve users' customized tasks."，Algorithm 1 的输出是 "The re-aligned model ˜w ready for deployment."。论文明确把推理加速列为 future work（Section 5.5），即剪枝后并不要求立刻转换为稀疏结构以获得加速。
- 输出：可直接部署的模型。
- 论文出处：Algorithm 1 output 行、Section 4 结尾、Section 5.5。

## 4. 采样与规模控制

- **样本（samples）**：Antidote 用一份纯 harmful 的 re-alignment 数据集做参考数据，通过采样 open-sourced red-teaming dataset（如 BeaverTails、HH-RLHF）获得（Section 3.1）。默认采样 2000 条 harmful 样本（"we sample 2000 harmful samples to form the re-alignment dataset used by Antidote"，Section 5.1）。Table 13 扫描了 |D_realign| ∈ {0, 5, 10, 100, 1k, 2k, 5k}，结论是样本越多有害分数越低，但 1k 条以后收益递减，所以 1k 条也可行。评测时另一组数字（不属于方法本身）：从 BeaverTails 采样 1000 条 harmful instructions 计算 harmful score，从各微调测试集采样 872/1000/1000/122 条计算 finetune accuracy（Section 5.1 Metrics）。
- **坐标（coordinates）**：按 Wanda 分数对参数坐标做 top-α 截断，这是方法唯一的结构性规模控制。α = 0.2 为默认值，GSM8K 特例用 α = 0.05（Section 5.1）；Table 11 扫描 α ∈ {0.01, 0.05, 0.1, 0.15, 0.2, 0.25}。
- **轮次（rounds）**：one-shot（一次性），微调结束后只执行一次，不迭代、不跨轮累积（Figure 1 "One-shot Pruning"、Algorithm 1）。
- **层（layers）**：论文未说明是否逐层分配稀疏率，也未说明是否跳过某些层或保护某些模块。论文在 Related Work 中提到 layer-wise sparsity（Yin et al., 2023）只是作为被借鉴分数的模型稀疏化文献，并未说明 Antidote 采用了逐层稀疏。
- **客户端（clients）**：论文未使用。Antidote 是集中式 fine-tuning-as-a-service 场景的方法，没有客户端采样或客户端选择。
- **探针（probes）**：论文未使用探针网络或探针数据集；唯一的"探针"性质计算是对 D_realign 的前向传播以取得激活范数。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| α（mask ratio） | 被 mask 置 1、随后被剪掉的坐标比例 | 默认 α = 0.2；GSM8K 上 α = 0.05 | Section 5.1；Table 11 扫描 0.01/0.05/0.1/0.15/0.2/0.25 |
| \|D_realign\| | re-alignment 数据集的样本条数 | 默认 2000 条 harmful 样本 | Section 5.1；Table 13 扫描 0/5/10/100/1k/2k/5k |
| LoRA rank | 对齐与微调所用 LoRA 适配器的秩 | 256 | Section 5.1；Appendix A.1 |
| LoRA alpha | LoRA 缩放系数 | Appendix A.1 写 "LoRA alpha set to 4"，同段又写 "In both alignment stage and fine-tuning stage, the learning rate is set to be 5"，两处互相矛盾，论文未澄清 | Appendix A.1 |
| 对齐阶段设置 | safety alignment 的样本数、优化器、学习率、轮数 | 5000 条 safety samples；AdamW；lr = 1e-3；20 epochs | Section 5.1 |
| 微调阶段设置 | 用户微调的样本数 n、有害比例 p、学习率 lr、轮数 ep | 默认 n = 5000，p = 0.2，lr = 1e-4，ep = 20，默认数据集 SST2；均用 AdamW | Section 5.1 |
| 解码设置 | 生成时使用的解码方式 | greedy decoding | Section 5.1 |

Antidote 自身只有两个实质超参数：mask ratio α 与参考集大小 |D_realign|；其余都是它运行的上下游流程（对齐、微调）的设置。论文没有为 Antidote 设阈值型超参数（不存在分数阈值、聚类数目、裁剪范数、噪声尺度等）。

## 6. 判定与动作

- **判定规则**：没有"是否攻击"的二值判定，也没有阈值。唯一的判定是排序规则——对每个坐标算式 (1) 的分数，取分数最大的 α 比例坐标作为 harmful mask（式 2）。论文的直觉是：这些坐标是"most important parameters for harmful content generation"。
- **动作**：对这些坐标做硬置零（式 3），即 w̃ = (1 − m) ⊙ w；不做加权、不做衰减、不缩放其余坐标。被保留的坐标完全不变。
- **幅度**：动作幅度由 α 控制，而不是由某个固定阈值控制。Table 11 显示 α 越大，harmful score 与 finetune accuracy 同时下降：α = 0.01 时 HS 73.60 / FA 94.95；α = 0.05 时 68.70 / 94.50；α = 0.1 时 64.60 / 93.35；α = 0.15 时 58.90 / 91.06；α = 0.2 时 58.40 / 86.58；α = 0.25 时 57.00 / 80.05（Table 11）。
- **是否跨轮累积**：不累积。整个方法是 one-shot 的（Figure 1、Algorithm 1），剪枝后模型直接部署，不再训练、不再二次剪枝。论文明确提到剪枝带来的推理加速留作 future work（Section 5.5）。
- **与随机剪枝的对比**：同比例随机剪枝效果更差；Figure 6 报告 Antidote 在 GSM8K 样本上的 logit drift 为 13058、在 harmful 样本上为 24469，而随机剪枝分别是 22000 与 26172，且随机剪枝把准确率从 27.60 降到 14.90。
- **与其它防御的组合**：Antidote 可以串在其它阶段方法之后，论文给出三种组合 V-S-A（Vaccine + SFT + Antidote）、S-L-A（SFT + Lisa + Antidote）、V-L-A（Vaccine + Lisa + Antidote），其中 V-S-A 把平均有害分数再降 2.46 并小幅提升 finetune accuracy（Table 14）。

## 7. 需要的外部资源

- **re-alignment 数据集 D_realign**：全部为 harmful prompt–harmful answer 配对，默认 2000 条，可从开源 red-teaming 数据集（如 BeaverTails、HH-RLHF）采样得到（Section 3.1、Section 5.1）。实验里它从 BeaverTails 中 is_safe=False 的数据采样，且与微调数据集中混入的 harmful 数据不是同一批（Section 5.1）。Table 13 表明 1k–2k 条即可，5k 条收益不再增长。
- **被破坏的微调后模型 w**：即 safety-alignment broken fine-tuned model；实验用 Llama2-7B、Mistral-7B、Gemma-7B 以及 Llama3-8B，对齐与微调使用 double LoRA（两个不同的 LoRA 适配器），rank 256（Section 5.1、Section 5.3、Appendix A.1）。
- **激活抽取能力**：需要在 D_realign 的前向传播中逐坐标取到 A_j(x, w)（式 1）。论文没有说明用什么 hook 实现、对哪些模块取激活。
- **上游流程资源（非 Antidote 直接使用）**：对齐数据集 D_align（harmful prompt–safe answer 配对，实验中 5000 条来自 BeaverTails 的 is_safe=True 数据，Section 5.1），以及对齐前的预训练模型。
- **评测资源（非方法本身）**：来自 (Ji et al., 2023) 的 moderation model（审核模型）用于判定输出是否有害，以及 1000 条 unseen malicious instructions（Section 5.1 Metrics）。
- **不需要**：根数据集、预训练检测器、教师模型、对齐前后的成对权重、额外的辅助模型，也不需要客户端数据或额外通信（分析：论文全文未使用这些资源）。

## 8. 计算与存储开销

论文报告的系统开销（Table 10，H100 上测）：

- 全流程 clock time：SFT 1.70 小时（1x）；Antidote 1.78 小时（1.02x），其中 alignment 0.92 小时、fine-tuning 0.78 小时、Post-FT 阶段 0.04 小时。
- GPU 显存：SFT 峰值 35.45 GB（1x）；Antidote 的 alignment 35.45 GB、fine-tuning 33.06 GB、Post-FT 22.35 GB，峰值与 SFT 相同，为 35.45 GB（1x）。
- 论文的结论原话是 Antidote 只引入 "a slight increase in clock time overhead (1.02x clock time) and the same GPU memory usage for the whole pipeline"，并说明额外开销"mainly comes from calculating the Wanda score over the realignment dataset to acquire the topk important mask and apply it to the model to remove poisoned parameters"（Table 10 上下文）。
- 对比：Vaccine 与 RepNoise 在对齐阶段需要 2x 以上 clock time、1.7x 以上显存；Lisa 与 LDIFS 在微调阶段需要 1.6x 以上显存，LDIFS 需要 1.5x clock time（Table 10）。

分析：开销主要来自三处。(1) 对 |D_realign|（默认 2000）条样本做一次前向传播并在每个线性层上抽取输入激活的范数，代价随 |D_realign| × 线性层数 × 每层输入维度线性增长，每条样本只需要一次前向、不需要反向传播。(2) 一次全模型坐标上的 top-k 选择，代价随候选坐标数 d 线性（或 O(d log k)）。(3) 一次逐元素乘法式的置零与模型写回，代价 O(d)。存储方面需要为每个候选坐标保存一个重要性分数（fp32 约 4d 字节）和一个 0/1 mask（d 比特或 d 字节），论文没有说明是否把分数向量落盘、也没有给出 d 或 mask 存储量的数字（论文未说明）。Table 10 中 Post-FT 阶段的 22.35 GB 显存主要来自模型权重与激活抽取（分析）。

## 9. 实现时容易错的地方

论文明确强调或可直接推出的：

1. α 必须按任务调。默认 α = 0.2，但 GSM8K 用 α = 0.05（Section 5.1）；α 增大时 harmful score 与 finetune accuracy 会同时下降，α = 0.2 时 FA 已从 94.95 掉到 86.58（Table 11）。直接把 0.2 套到所有任务上会损失精度。
2. 参考数据必须是 harmful 数据。Table 12 显示换成微调数据或 benign 数据后平均有害分数分别上升 +0.68 与 +1.13，其中 benign 数据最差，"because this dataset with no harmful data present cannot adequately reveal the harmful parameters"。
3. |D_realign| = 0 是退化边界：此时 Wanda 分数退化为坐标的权重幅度 |w_j|，方法变成纯幅度剪枝（Table 13 表注，该行 HS 为 72.1，是所有设置里最差的）。
4. 式 (1) 是对整个数据集求平均（1/|D| Σ），不是用单条样本或最后一个 batch 的统计（式 1）。
5. 分数必须同时包含权重项和激活项，只保留其一（例如 Wanda 退化为幅度剪枝）会变差，参考第 3 点的对照。
6. 剪枝后不再训练，直接部署；Algorithm 1 的输出行写明 "The re-aligned model ˜w ready for deployment."。
7. 论文对 Antidote 报告的 harmful score 与 finetune accuracy 是在 re-aligned model 上测的，其余基线是在微调模型上测的（Section 5.1 Metrics："except for Antidote, they are measured over the re-alignment model"），复现时不要混用测量对象。
8. 选择 top-k 而不是随机置零是必要的：同比例随机剪枝在 GSM8K 上的 logit drift 更大、准确率从 27.60 掉到 14.90（Figure 6）。
9. 剪枝不保证推理加速，论文把加速留作 future work（Section 5.5），不要默认剪枝后能直接拿到稀疏推理的收益。

论文没说清、实现时必须自己决定的：

1. A_j(x, w) 的精确定义：它属于哪个模块（attention 的 q/k/v/o 还是 MLP）、是层的输入还是输出、序列维度与 batch 维度如何归约成单个标量范数、padding token 是否计入。论文只说它是"hidden activation that is associated with the j-th weight coordinate"（式 1 上下文）。
2. ArgTopK_α 的作用域：是跨整个模型的全局 top-k，还是逐层各取 α（Wanda 原方法 Sun et al., 2023 通常逐层设定稀疏率）。论文只说 α 是 "the ratio of coordinates that are masked to 1"（式 2 上下文），未提逐层分配，也未讨论跨层分数尺度是否可比。
3. 候选坐标集合：是否包含 embedding、LayerNorm、bias，是否只处理线性层权重。论文未说明。
4. 在 double LoRA 设置下，w 指的是 base 模型权重还是 LoRA 的 A/B 矩阵，是否需要先把适配器 merge 进 base 权重，剪枝作用在哪一个适配器上，论文均未说明；而这会直接改变式 (3) 的作用对象。
5. 剪枝后模型如何保存与再合并，是否需要把 LoRA 权重重新 merge 成可部署权重，论文未说明。
6. 训练侧超参数前后矛盾：Appendix A.1 先写 "LoRA alpha set to 4"，紧接着写 "In both alignment stage and fine-tuning stage, the learning rate is set to be 5"，而正文 Section 5.1 说对齐学习率是 1e-3、微调默认 lr = 1e-4，且正文没有给 LoRA alpha。实现前需要回原文核对这一处。
7. Table 11 的 α 消融没有在抽取文本中说明所用数据集与 backbone，因而无法判断它对应的准确率量级为何与 Table 6 的 GSM8K 行不同。
8. Table 10 中 Post-FT 阶段的 22.35 GB 显存是独立阶段的峰值还是相对基线的增量，论文未说明；0.04 小时的测量边界（是否包含数据加载与前向）也未说明。
9. 若某个层被 mask 到没有任何坐标剩余（α 很大时可能发生），或 α 大到破坏 LayerNorm/embedding 等敏感模块，论文没有给出保护规则或回退策略；论文也没有给出 α 的上限建议。
10. 参考集里含有有害回答文本本身，是否需要对参考集做去重、长度截断、模板化（Appendix A.1 给了 Alpaca prompt template 用于构造监督数据，但未说明计算 A_j 时是否也用同一模板），论文未说明。

## 10. 原文依据

1. **支撑步骤 1、2（参考集的性质与输入对象的定义）**：
   "where Drealign is the harmful dataset containing harmful question-harmful answer pairs and w is a vector representing model weights of the safety-alignment broken fine-tuned model."
2. **支撑步骤 2（Wanda 分数用于度量参数重要性）**：
   "The Wanda score (Sun et al., 2023) measures the importance score of parameters given the re-alignment dataset Drealign, as follows:"
3. **支撑步骤 2（式 1 的直觉：权重幅度 × 输入激活）**：
   "Intuitively, the importance of a coordinate of parameter is related to its absolute value and the value of its input."
4. **支撑步骤 3（取 top-k 形成 harmful mask 的动机）**：
   "To recognize the harmful parameters over the fine-tuned model weights w, one intuitive idea is to extract the topk most important mask (harmful mask) on the re-alignment dataset, indicating the most important parameters for harmful content generation, as follows."
5. **支撑步骤 3（ArgTopK_α 的语义与 α 的定义）**：
   "where ArgTopKα() returns a mask with the topk coordinate being 1 and the rest being 0. α is the ratio of coordinates that are masked to 1, which we name mask ratio for simplicity."
6. **支撑步骤 4（式 3 剪枝操作）**：
   "Given the harmful mask m and the weights after fine-tuning w, The pruning operation of the harmful parameters is as follows:"
7. **支撑步骤 3、4 的整体顺序（先识别 top-k，再移除）**：
   "In summary, given a safety alignment-broken fine-tuned model, we first identify the top-k harmful parameters with a harmful mask. Then we remove those harmful parameters from the fine-tuned model to recover it from the harmful behavior."
8. **支撑第 4、5 节的采样与超参数取值**：
   "For hyper-parameters for Antidote, in default, we set the mask ratio to be α = 0.2 (specially, α = 0.05 for GSM8K) and we sample 2000 harmful samples to form the re-alignment dataset used by Antidote."

```json
{
  "key": "huang2024antidote",
  "method": "Antidote（微调后一次性 Wanda 分数掩码剪枝，post-fine-tuning one-shot Wanda-score pruning）",
  "stages": ["server_post_aggregate", "outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "在 re-alignment 数据集上做前向传播，抽取每个权重坐标对应的隐藏激活范数",
      "operator": "forward_activation_norm_collection",
      "input": "微调后的模型 w；全部为 harmful prompt-harmful answer 配对的参考集 D_realign，默认 2000 条",
      "output": "逐坐标的激活 L2 范数 ‖A_j(x, w)‖₂ 统计（可与 |w_j| 结合成重要性向量）",
      "params": {"num_samples": 2000, "grad_required": false, "activation_source": "论文未说明（层/模块、归约维度均未说明）"},
      "source": "式 (1) 中的 A_j(x, w) 及其上下文；样本量与出处见 Section 5.1"
    },
    {
      "step": "计算 Wanda 重要性分数",
      "operator": "wanda_importance_score",
      "input": "每个坐标的权重 w_j 与对应输入激活 A_j(x, w)，x ∈ D_realign",
      "output": "与权重坐标同长的重要性分数向量 h(w, D_realign)",
      "params": {"aggregation": "对 D_realign 求平均 (1/|D|) Σ", "weight_term": "|w_j|", "activation_term": "‖A_j(x, w)‖₂", "degenerate_case": "|D|=0 时退化为 |w_j|"},
      "source": "式 (1)，Section 4；退化情形见 Table 13 表注"
    },
    {
      "step": "按 mask ratio 取 top-k 生成 harmful mask",
      "operator": "topk_ratio_binary_mask",
      "input": "重要性分数向量 h(w, D_realign)",
      "output": "二值 harmful mask m（选中坐标置 1，其余为 0）",
      "params": {"alpha": 0.2, "alpha_gsm8k": 0.05, "scope": "论文未说明（全局 top-k 还是逐层 top-k）"},
      "source": "式 (2)，Section 4，Algorithm 1 第 2 行；α 取值见 Section 5.1、Table 11"
    },
    {
      "step": "用 mask 对权重做一次性置零剪枝",
      "operator": "masked_weight_prune",
      "input": "harmful mask m 与微调后权重 w",
      "output": "re-aligned model 权重 w̃",
      "params": {"masked_value": 0, "combine": "Hadamard product (1 − m) ⊙ w", "iterations": 1},
      "source": "式 (3)，Section 4，Algorithm 1 第 3 行"
    },
    {
      "step": "导出可部署模型（不做任何再训练或恢复）",
      "operator": "export_pruned_model",
      "input": "re-aligned 权重 w̃",
      "output": "可直接部署的模型",
      "params": {"retrain_after_prune": false, "sparse_format": "论文未说明（加速留作 future work）"},
      "source": "Algorithm 1 output 行；Section 4 结尾；Section 5.5"
    }
  ],
  "sampling": [
    {"what": "samples", "how": "从开源 red-teaming 数据集（实验用 BeaverTails 的 is_safe=False 数据）采样 harmful prompt-harmful answer 对构成 D_realign，且与微调数据集中混入的 harmful 数据不同", "size": "默认 2000 条（Section 5.1）；Table 13 扫描 0/5/10/100/1k/2k/5k，1k 条以后收益递减"},
    {"what": "coordinates", "how": "对 Wanda 分数做 top-α 选择，被选中坐标置零；论文未说明是否逐层分配", "size": "α = 0.2（默认）、0.05（GSM8K）（Section 5.1）；Table 11 扫描 0.01/0.05/0.1/0.15/0.2/0.25"},
    {"what": "rounds", "how": "one-shot：微调全部结束后只执行一次，不迭代、不跨轮累积", "size": "1 次（Figure 1 Stage III、Algorithm 1）"},
    {"what": "clients", "how": "论文未使用：Antidote 是集中式 fine-tuning-as-a-service 场景的方法，没有客户端采样或客户端选择", "size": "论文未使用"},
    {"what": "layers", "how": "论文未说明是否逐层设置稀疏率、是否跳过或保护某些层", "size": "论文未说明"},
    {"what": "probes", "how": "论文未使用探针网络或探针数据集；唯一的参考数据前向传播即 D_realign 上的激活统计", "size": "论文未使用"}
  ],
  "resources": [
    "re-alignment 数据集 D_realign：全部为 harmful prompt-harmful answer 对，默认 2000 条，实验从 BeaverTails（Ji et al., 2023）的 is_safe=False 数据采样，与微调数据里的 harmful 数据不同（Section 3.1、Section 5.1）",
    "被 harmful fine-tuning 破坏的微调后模型 w（Llama2-7B / Mistral-7B / Gemma-7B / Llama3-8B；double LoRA，rank 256，alpha 4，Section 5.1、Section 5.3、Appendix A.1）",
    "对 D_realign 做前向传播并逐坐标抽取隐藏激活 A_j(x, w) 的能力（式 1）；论文未说明具体实现方式",
    "上游对齐流程需要 D_align（harmful prompt-safe answer 配对，实验中 5000 条来自 BeaverTails is_safe=True）与对齐前的预训练模型；Antidote 本身不使用 D_align（Section 3.1、Section 5.1）",
    "评测用：来自 (Ji et al., 2023) 的 moderation model 与 1000 条 unseen malicious instructions（Section 5.1 Metrics）",
    "不需要：根数据集、预训练检测器、教师模型、对齐前后成对权重、额外辅助模型、客户端数据或客户端-服务器额外通信（分析：论文全文未使用这些）"
  ],
  "actions": ["transform_gradients"],
  "dominant_cost": "论文报告：全流程 clock time 1.78 小时（1.02x SFT），其中 Post-FT 0.04 小时；Post-FT 阶段 GPU 显存 22.35 GB，全流程峰值 35.45 GB（与 SFT 相同）（Table 10）。额外开销主要来自在 realignment 数据集上计算 Wanda 分数、取 top-k mask 并施加到模型上（Table 10 上下文）。分析：主导开销是 |D_realign|（默认 2000）条样本的一次前向传播与逐线性层输入激活范数抽取，随 |D_realign| × 线性层数 × 每层输入维度增长，每条样本一次前向、无需反向传播；其后是 O(d) 的 top-k 选择与置零，以及长度 d 的重要性分数与 mask 的存储（d 与存储量论文未说明）。",
  "underspecified": [
    "A_j(x, w) 的精确定义：属于哪个模块（attention q/k/v/o 还是 MLP）、取层输入还是输出、序列与 batch 维度如何归约、padding 是否计入，论文只说它是与第 j 个权重坐标关联的隐藏激活",
    "ArgTopK_α 的作用域：是全局 top-k 还是逐层各取 α（Wanda 原方法通常逐层），论文未说明，也未讨论跨层分数尺度可比性",
    "候选坐标集合：是否包含 embedding、LayerNorm、bias，是否只剪线性层权重，论文未说明",
    "double LoRA 设置下 w 指 base 权重还是 LoRA 的 A/B 矩阵、是否需要先 merge、剪枝作用于哪个适配器，论文未说明",
    "剪枝后模型如何保存与再合并（是否需要重新 merge LoRA 权重），论文未说明",
    "训练侧超参数矛盾：Appendix A.1 同时写 'LoRA alpha set to 4' 与 'the learning rate is set to be 5'，而正文 Section 5.1 给的对齐学习率为 1e-3、微调默认 lr 为 1e-4，需回原文核对",
    "Table 11 的 α 消融使用的数据集与 backbone 未在抽取文本中说明，无法判断其数值与 Table 6 的差异来源",
    "Table 10 中 Post-FT 的 22.35 GB 是独立阶段峰值还是增量、0.04 小时是否包含数据加载，论文未说明",
    "α 过大导致某层坐标被全部剪掉或破坏 LayerNorm/embedding 等敏感模块时，论文未给出保护规则、回退策略或 α 上限建议",
    "计算激活时是否使用 Appendix A.1 的 Alpaca prompt template、参考集是否去重或截断，论文未说明"
  ],
  "quotes": [
    {"supports": "步骤 1、2：参考集性质与输入对象 w 的定义（式 1 上下文）", "text": "where Drealign is the harmful dataset containing harmful question-harmful answer pairs and w is a vector representing model weights of the safety-alignment broken fine-tuned model."},
    {"supports": "步骤 2：用 Wanda 分数在参考集上度量参数重要性（式 1）", "text": "The Wanda score (Sun et al., 2023) measures the importance score of parameters given the re-alignment dataset Drealign, as follows:"},
    {"supports": "步骤 2：式 1 的直觉，重要性 = 权重绝对值 × 输入激活值", "text": "Intuitively, the importance of a coordinate of parameter is related to its absolute value and the value of its input."},
    {"supports": "步骤 3：取 top-k 形成 harmful mask 的动机（式 2 之前）", "text": "To recognize the harmful parameters over the fine-tuned model weights w, one intuitive idea is to extract the topk most important mask (harmful mask) on the re-alignment dataset, indicating the most important parameters for harmful content generation, as follows."},
    {"supports": "步骤 3：ArgTopK_α 的语义与 α（mask ratio）的定义", "text": "where ArgTopKα() returns a mask with the topk coordinate being 1 and the rest being 0. α is the ratio of coordinates that are masked to 1, which we name mask ratio for simplicity."},
    {"supports": "步骤 4：式 3 的剪枝操作定义", "text": "Given the harmful mask m and the weights after fine-tuning w, The pruning operation of the harmful parameters is as follows:"},
    {"supports": "步骤 3、4 的执行顺序：先识别 top-k 有害参数，再移除", "text": "In summary, given a safety alignment-broken fine-tuned model, we first identify the top-k harmful parameters with a harmful mask. Then we remove those harmful parameters from the fine-tuned model to recover it from the harmful behavior."},
    {"supports": "第 4、5 节：采样规模与超参数的默认取值", "text": "For hyper-parameters for Antidote, in default, we set the mask ratio to be α = 0.2 (specially, α = 0.05 for GSM8K) and we sample 2000 harmful samples to form the re-alignment dataset used by Antidote."}
  ]
}
```
