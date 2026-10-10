# hu2021lora：LoRA: Low-Rank Adaptation of Large Language Models

## 1. 基本信息

- **论文**：Hu、Shen、Wallis、Allen-Zhu、Li、Wang、Wang、Chen（Microsoft Corporation），《LoRA: Low-Rank Adaptation of Large Language Models》，arXiv:2106.09685v2，2021 年 10 月 16 日（首页）；作者标注 "Equal contribution"（第 1 页脚注）。
- **场景**：集中式大模型训练下的参数高效微调（parameter-efficient fine-tuning, PEFT）。论文自始至终描述的是单一主体在单个下游任务数据上适配一个已预训练模型：给定预训练自回归语言模型 PΦ(y|x)，每个下游任务用一个 context-target 训练集 Z = {(xi, yi)} 表示（第 2 节）。**论文没有出现联邦学习、客户端、聚合服务器、数据本地性、Non-IID 划分或通信轮次等任何概念**；因此它既不属于传统联邦学习，也不属于联邦大模型微调，而是"集中式大模型训练 + 参数高效微调"。
- **训练阶段**：下游任务适配阶段（冻结预训练权重，只训练注入的低秩矩阵），以及部署阶段（把低秩增量合并回原权重）。预训练阶段本身不涉及。
- **论文类型**：基础方法（foundation），同时发布了一个便于把 LoRA 接入 PyTorch 模型的软件包，并提供 RoBERTa、DeBERTa、GPT-2 的实现与模型检查点（摘要）。论文不含攻击、防御、检测或基准评测内容。
- **模型规模**：GPT-3 175B（表 4 记为 175,255.8M 可训练参数）、DeBERTa XXL 1.5B、RoBERTa base 125M 与 large 355M、GPT-2 medium 354.92M 与 large 774.03M（表 2、表 3、第 5.2 节、第 5.3 节）。GPT-3 的 Transformer 有 96 层，d 最大为 12,288（第 1 节、第 7 节）。
- **数据规模**：GLUE 的 8 个任务（表 2；各任务说明见附录 C）、E2E NLG Challenge（约 42,000 训练 / 4,600 验证 / 4,600 测试，附录 C）、WebNLG（共 22K，14 类中 9 类训练可见，附录 C）、DART（82K，附录 C）、WikiSQL（56,355 训练 / 8,421 验证，附录 C）、SAMSum（14,732 训练 / 819 测试，附录 C）；低数据实验使用 MNLI 的 100 / 1k / 10k 子集（附录 F.3、表 16）。
- **硬件**：所有实验使用 NVIDIA Tesla V100；延迟实验使用 NVIDIA Quadro RTX8000（第 5 节、表 1）。

## 2. 威胁模型

**论文未说明。** 这篇论文不是攻击论文，也不是防御论文，全文没有定义攻击者、防御者、信任边界或敌手能力。

- 攻击者是谁、占比或数量、能力、知识、目标：**论文未说明**（论文中没有恶意客户端、恶意服务器、数据提供方、适配器发布者等角色）。
- 防御者是谁、能看到什么、信任什么：**论文未说明**。论文隐含的操作主体是同时持有预训练权重 Φ0 与下游任务数据 Z 的单一开发者（第 2 节），但论文并未把它作为一个"信任/威胁"设定来表述。
- 论文中唯一与安全相邻的表述是相关工作里的一句转述：Allen-Zhu & Li (2020b) 的理论结果"建议低秩适配可能对对抗训练有用"（第 6 节，Related Works 的 Low-Rank Structures in Deep Learning 段）。论文没有据此做任何实验，也没有展开威胁模型。
- 分析：由于没有敌手模型，这篇论文不能直接提供任何"攻击者能改什么"的假设；对防护库而言，它提供的是被保护的**对象**（LoRA 增量参数）及其可观测性质，而不是威胁假设。

## 3. 攻击入口与流程位置

**论文未说明。** 论文不是攻击论文，也不是针对某类攻击的防御论文，因此没有"攻击从哪个位置进入"的论述。

论文明确写出的、与流程位置有关的事实（可作为接口依据）：

1. **注入位置在模型内部的具体权重矩阵上**：在 Transformer 中，自注意力模块有四个权重矩阵（Wq、Wk、Wv、Wo），MLP 模块有两个；论文把 LoRA 加在注意力权重上，多数实验只适配 Wq 和 Wv，并冻结 MLP（第 4.2 节、第 5.1 节）。
2. **入口在本地训练过程**：前向传播被改写为 h = W0x + ∆Wx = W0x + BAx（式 (3)）；训练时 W0 冻结、不接收梯度，A 与 B 是唯一可训练参数（第 4.1 节）。也就是说，"更新"的产生完全发生在训练阶段，产物是低秩增量 BA。
3. **产物形态**：一次适配结束后，被保存和传递的是尺寸远小于原模型的低秩矩阵（B ∈ R^(d×r)、A ∈ R^(r×k)，r ≪ min(d, k)，第 4.1 节）；部署时可显式合并 W = W0 + BA，切换任务时先减去 BA 再加上 B′A′（第 4.2 节）。
4. **初始化与缩放是训练过程的一部分**：A 用随机高斯初始化、B 用零初始化，使 ∆W = BA 在训练开始时为零；∆Wx 再乘以 α/r（第 4.1 节、图 1）。

分析：若把上述流程映射到联邦 LoRA 微调，恶意客户端能够施力的位置是"本地数据准备"（构造投毒样本）、"本地训练过程"（改变 A、B 的取值）以及"更新上传前的后处理"（对 BA 或 A、B 做缩放、投影、替换或拼装）；服务器聚合与全局下发的环节这篇论文完全没有涉及，属于论文未说明的部分。以上映射是我的推断，不是论文内容。

## 4. 方法原理

**核心思想**（第 1 节、第 4.1 节）：借鉴"过参数化模型在适配时只依赖低内在维度"的既有观察（Li et al., 2018a；Aghajanyan et al., 2020），论文假设适配带来的权重变化 ∆W 也具有很低的"内在秩"，于是不直接训练 ∆W，而是把它参数化为两个小矩阵的乘积。

**关键步骤与公式**：

1. 对预训练权重矩阵 W0 ∈ R^(d×k)，把更新约束为低秩分解 W0 + ∆W = W0 + BA，其中 B ∈ R^(d×r)、A ∈ R^(r×k)、r ≪ min(d, k)（第 4.1 节）。
2. 前向传播为 h = W0x + ∆Wx = W0x + BAx（式 (3)），即 W0 与 ∆W 乘同一个输入，输出逐坐标相加（第 4.1 节）。
3. 初始化：A 为随机高斯、B 为零，因此训练开始时 ∆W = BA = 0（第 4.1 节、图 1）。训练时把 ∆Wx 按 α/r 缩放，α 是 r 中的常数；论文把 α 直接设成第一次尝试的 r，不再调参（第 4.1 节）。
4. 适配位置：多数实验只对注意力权重 Wq 与 Wv 加 LoRA，冻结 MLP；论文对 MLP、LayerNorm 和 bias 的适配留作未来工作（第 4.2 节）。可训练参数量为 |Θ| = 2 × L̂_LoRA × d_model × r，其中 L̂_LoRA 是被适配的权重矩阵个数（第 5.1 节）。
5. 部署：显式计算并保存 W = W0 + BA，按普通模型推理；切换任务时用减法恢复 W0 再加 B′A′（第 4.2 节）。
6. 表达能力：把 LoRA 加到所有权重矩阵并训练所有 bias，且把 r 提高到预训练权重矩阵的秩时，大致可以恢复全量微调的表达能力（第 4.1 节）。

**实证分析部分**（第 7 节）给出三个可复用的量：

- 子空间相似度（式 (4)）：φ(A_{r=8}, A_{r=64}, i, j) = ||U^iᵀ_{Ar=8} U^j_{Ar=64}||²_F / min(i, j) ∈ [0, 1]，用奇异向量张成子空间的重叠度衡量两次低秩解是否学到同一批方向（第 7.2 节）。
- 投影范数：把 W 投影到 ∆W 的 r 维子空间，比较 ||UᵀWVᵀ||_F 与 ||W||_F（第 7.3 节、表 7）。
- 放大因子：||∆W||_F / ||UᵀWVᵀ||_F，用于衡量 ∆W 把 W 中未被强调的方向放大了多少（附录 H.4）。

**主要发现**：GPT-3 上 r = 1 或 2 就足够（第 1 节、表 6）；适配 Wq 与 Wv 两者优于把同样的参数预算全押在 Wq 或 Wk 上（第 7.1 节、表 5）；∆W 与 W 的相关性强于随机矩阵，但 ∆W 放大的不是 W 的 top 奇异方向（第 7.3 节、表 7）；r = 4 时放大因子约为 21.5 ≈ 6.91/0.32（表 7 与第 7.3 节），r = 64 时只有约 2（附录 H.4）；LoRA 可与 prefix-tuning 组合（附录 E）。

## 5. 检测或防御所需的数据

论文不是检测或防御论文，因此**没有"检测所需数据"这一节**；下面是论文在训练、分析、评估中实际读取或产出的量，可视为它定义的可观测量清单。需要强调：这些量在论文中全部来自单主体的一次集中式训练运行，论文未说明任何逐客户端或逐轮（联邦轮）的采集方式。

- **LoRA 增量矩阵 ∆W = BA（每个被适配的权重矩阵、每层）**：论文的核心对象；它在训练结束后确定，用于部署合并（第 4.2 节），也是第 7 节所有分析的对象。采集位置可对应"客户端训练后"（在论文中是单次训练运行结束）；粒度是逐层、逐权重矩阵类型（Wq、Wk、Wv、Wo）；不需要跨轮历史；不需要干净参考数据；不需要额外前向或反向计算。
- **低秩因子 A 与 B 本身**：论文规定 A 为随机高斯初始化、B 为零初始化，并记录 α 与 r 的取值（第 4.1 节；附录 D.1 记录 RoBERTa base 的 rq = rv = 8、α = 8，large 的 α = 16；附录 D.3 记录 GPT-2 的 rq = rv = 4、α = 32；表 12 记录 GPT-3 的学习率等）。采集位置同上，粒度逐层，无需历史与干净参考。
- **对 A 做奇异值分解得到的奇异向量与奇异值**：第 7.2 节用右奇异向量矩阵 U_{Ar=8} 与 U_{Ar=64} 计算式 (4)，附录 G 给出该相似度与投影度量（Projection Metric）的关系。采集位置在训练完成后；粒度逐层、逐秩设置；需要额外的 SVD 计算；论文中是比较两次独立训练（不同 r、不同随机种子），不是跨轮历史。
- **冻结的预训练权重 W（即干净参考模型 W0）**：第 7.3 节与表 7 需要 Wq 来做投影 ||UᵀWVᵀ||_F，并给出 ||Wq||_F = 61.95 作为分母对照。采集位置在训练之前的基线模型（论文中是公开预训练权重）；粒度逐层；需要干净参考；需要额外的矩阵乘法与范数计算。
- **∆W 的 Frobenius 范数**：表 7 给出 r = 4 时 ||∆Wq||_F = 6.91、r = 64 时 3.57。位置同上，粒度逐层，需要额外计算。
- **训练超参数与配置**：优化器（Adam/AdamW）、批大小、学习率、训练轮数、序列长度、dropout、warmup、权重衰减等，见附录 D 的表 9（RoBERTa）、表 10（DeBERTa）、表 11（GPT-2）、表 12 与表 17（GPT-3）。采集位置是训练前（配置），粒度逐任务/逐实验。
- **下游任务验证集上的指标**：GLUE 各任务的准确率、Matthews 相关系数、Pearson 相关系数（表 2 说明），E2E/WebNLG/DART 的 BLEU、NIST、METEOR、ROUGE-L、CIDEr（表 3、表 13、表 14），WikiSQL 的逻辑形式验证准确率、MultiNLI-matched 准确率、SAMSum 的 Rouge-1/2/L（表 4 说明），以及低数据设定下的 MNLI 验证准确率（表 16）。采集位置是评估阶段，粒度是逐任务、每次运行取最佳 epoch（附录 D.1、D.3、D.4）。论文未说明这些验证集是否可能被污染。
- **资源与延迟计量**：显存占用（1.2TB → 350GB）、检查点大小（350GB → 35MB）、吞吐（tokens/s per V100）、单次前向延迟（毫秒，表 1）。采集位置是训练中与部署推理时；粒度是模型级/运行级。

**攻击痕迹与绕过检测**：论文未说明。论文没有讨论任何攻击会在上述可观测量上留下什么痕迹，也没有声称能绕过任何检测。分析：如果按论文自己的分析类比，一个被投毒的本地 LoRA 更新最可能扰动的是逐层 ∆W 的范数、奇异值谱与子空间方向（第 7.2、7.3 节的量），而良性任务本身就会让 ∆W 在少数方向上被放大约 21.5 倍（表 7、附录 H.4），因此简单的"范数阈值"很可能难以区分——但这是我的推断，论文完全没有做这类实验。

## 6. 干预动作

**论文未说明任何检测后的干预动作**，因为论文没有检测环节。论文中与方法本身相关的"动作"只有两类结构性操作：

1. **训练时的参数冻结与掩码**：冻结预训练权重 W0，只让注入的 A、B 接收梯度更新（第 4.1 节；式 (3)）；默认只适配注意力权重 Wq 与 Wv，MLP 不参与下游训练（第 4.2 节）。
2. **部署时的合并与替换**：显式计算并保存 W = W0 + BA（第 4.2 节）；切换任务时先减去 BA 恢复 W0，再加另一个 B′A′，论文称这是内存开销很小的快速操作（第 4.2 节）。

论文没有剔除客户端、重新加权、梯度裁剪、加噪、样本过滤、模型修复或回滚等任何内容。分析：对防护库而言，这两类操作分别对应一个"客户端训练时的参数冻结/掩码钩子"和一个"部署或聚合前的权重合并钩子"；剔除、重加权之类真正意义上的防御动作需要由插件自行定义，论文不提供算法。

## 7. 实验设置与主要结果

**设置**（全部为集中式单主体训练）：

- 模型与数据：RoBERTa base 125M / large 355M 在 GLUE 上（第 5.2 节、表 2）；DeBERTa XXL 1.5B 在 GLUE 上（第 5.3 节、表 2）；GPT-2 medium / large 在 E2E NLG Challenge、DART、WebNLG 上（第 5.4 节、表 3、表 13、表 14）；GPT-3 175B 在 WikiSQL、MNLI、SAMSum 上（第 5.5 节、表 4）。
- 训练轮数：RoBERTa base 各任务 25–80 轮、large 10–30 轮，批大小 4–32（表 9）；DeBERTa XXL 各任务 5–30 轮，批大小 4–32（表 10）；GPT-2 统一 5 轮、批大小 8（表 11、附录 D.3）；GPT-3 统一 2 轮、批大小 128、权重衰减 0.1、序列长度按任务取 384/768/2048（附录 D.4、表 12）。
- 随机性处理：RoBERTa 与 DeBERTa 报告 5 个随机种子的中位数、每次运行取最佳 epoch（附录 D.1、D.2）；GPT-2 报告 3 个随机种子的均值（附录 D.3）；GPT-3 因成本只报告每个任务的典型标准差（第 5.5 节、表 4 说明）。
- **客户端数与参与率、联邦轮次、恶意客户端比例、数据是否 Non-IID：论文未说明（不适用）。**

**关键结果**：

- 表 2：RoBERTa base 用 LoRA 仅 0.3M 可训练参数，GLUE 平均 87.2，全量微调（FT）125.0M 参数为 86.4；RoBERTa large LoRA 0.8M 平均 89.0，FT 355.0M 为 88.9；DeBERTa XXL LoRA 4.7M 平均 91.3，FT 1500.0M 为 91.1。
- 表 3：GPT-2 medium LoRA 0.35M 参数取得 BLEU 70.4、NIST 8.85、METEOR 46.8、ROUGE-L 71.8、CIDEr 2.53，优于 FT 的 68.2、8.62、46.2、71.0、2.47；GPT-2 large LoRA 0.77M 的 BLEU 为 70.4，FT（774.03M）为 68.5。
- 表 4：GPT-3 175B 上，LoRA 4.7M 参数取得 WikiSQL 73.4、MNLI-m 91.7、SAMSum 53.8/29.8/45.9；全量微调 175,255.8M 参数为 73.8、89.5、52.0/28.0/44.5；LoRA 37.7M 为 74.0、91.6、53.4/29.2/45.1。论文说明 WikiSQL 波动约 ±0.5%、MNLI-m 约 ±0.1%、SAMSum 约 ±0.2/±0.2/±0.1（表 4 说明）。
- 表 5：在 GPT-3 上固定 18M 可训练参数预算（FP16 下约 35MB），只适配 Wq 时 WikiSQL 为 70.4，只适配 Wv 为 73.0，同时适配 Wq 与 Wv（r = 4）为 73.7，四个注意力矩阵全适配（r = 2）也是 73.7；MultiNLI 上四个矩阵全适配为 91.7。
- 表 6：GPT-3 上 r = 1 且同时适配 Wq 与 Wv 时，WikiSQL 为 73.4、MultiNLI 为 91.3；r 增大到 64 并不带来明显提升（WikiSQL 73.5、MultiNLI 91.4）。
- 表 7：GPT-3 第 48 层，r = 4 时 ||UᵀWqVᵀ||_F 对 ∆Wq 为 0.32、对 Wq 为 21.67、对随机矩阵为 0.02，||Wq||_F = 61.95，||∆Wq||_F = 6.91；r = 64 时为 1.90、37.71、0.33，||∆Wq||_F = 3.57。第 7.3 节给出放大因子约 21.5 ≈ 6.91/0.32（r = 4）。
- 表 1：GPT-2 medium、批大小 1、序列长度 128 时，单次前向延迟为 Fine-Tune/LoRA 19.8±2.7 毫秒、AdapterL 23.9±2.1（+20.7%）、AdapterH 25.8±2.2（+30.3%）；图 5 给出不同批大小与序列长度下最高超过 30% 的减速。
- 图 2：GPT-3 上前缀嵌入调优超过 256 个特殊 token、前缀层调优超过 32 个特殊 token 时出现明显性能下降（第 5.5 节）。
- 表 16（附录 F.3）：MNLI-100 上全量微调 60.2、PrefixEmbed 37.6、PrefixLayer 48.3、LoRA 63.8；论文指出 37.6% 仅略高于 33.3% 的随机水平。
- 表 18（附录 H.2）：GPT-2 medium 在 E2E 上训练 26,000 步后，验证损失在 r = 16 最好（1.16），BLEU 在 r = 4 最好（70.38）。
- 表 15（附录 E/F.2）：LoRA+PrefixEmbed 在 WikiSQL 上以 37.8M 参数达到 75.0，超过单独 LoRA 的 73.8（同表 37.7M 行）。

## 8. 开销

论文报告了较多开销数据：

- 相比用 Adam 全量微调的 GPT-3 175B，LoRA 可把可训练参数量减少 10,000 倍、GPU 显存需求减少 3 倍（摘要）。
- GPT-3 175B 训练显存从 1.2TB 降到 350GB；当 r ≪ d_model 时可减少最多 2/3 的显存，因为不需要为冻结参数保存优化器状态（第 4.2 节）。
- 检查点：r = 4 且只适配 query 与 value 投影矩阵时，检查点大小约缩小 10,000 倍，从 350GB 降到 35MB；存储 100 个适配模型需要 350GB + 35MB × 100 ≈ 354GB，而 100 个全量模型约 35TB（第 4.2 节与脚注 4）。
- 训练吞吐：GPT-3 175B 全量微调为 32.5 tokens/s per V100 GPU，LoRA 为 43.1 tokens/s per V100 GPU，即约 25% 加速（脚注 5）。
- 推理延迟：合并后不引入额外推理延迟（第 4.2 节）；对比之下 adapter 层在短序列、小批量的在线场景可带来约 20.7% 到 30.3% 的延迟增加（表 1），图 5 显示最高超过 30%。
- 存储与切换：只需交换 LoRA 权重即可切换任务，论文称这是很低成本的操作（第 4.2 节）。
- **论文未报告**：通信开销（论文不是联邦学习设定，没有通信量概念）、检测或防御开销（论文没有检测环节）、精确的墙钟训练时间与总能耗。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设**（论文明确写出或直接使用）：

1. 适配产生的权重增量 ∆W 具有低"内在秩"，这是论文明确标注为"假设"的前提：论文由"过参数化模型位于低内在维度"的既有结果出发，假设适配时的权重变化也具有低内在秩（第 1 节、第 4.1 节）。
2. W0 被冻结、不接收梯度，A 与 B 是唯一的可训练参数，且 W0 与 ∆W 乘同一个输入、输出逐坐标相加（第 4.1 节、式 (3)）。
3. A 用随机高斯初始化、B 用零初始化，使 ∆W = BA 在训练开始时为零；∆Wx 按 α/r 缩放，α 取第一次尝试的 r（第 4.1 节、图 1）。
4. 默认只适配注意力权重（多数实验为 Wq 与 Wv），MLP 冻结；MLP、LayerNorm 与 bias 的适配留作未来工作（第 4.2 节）。
5. 优化使用 Adam / AdamW 与线性学习率衰减（第 1 节术语约定；附录 D.1、D.2、D.3、D.4）。
6. 单一主体同时持有预训练权重与下游任务数据，训练是集中式的、数据是任务内可用的（第 2 节的问题陈述）。论文未讨论多方数据、数据本地性或聚合。

**论文自述的局限**：

1. 若把 A 与 B 吸收进 W 以消除推理延迟，则很难在单次前向中对属于不同任务、使用不同 A 和 B 的输入做批处理（第 4.2 节）。
2. 论文主要靠启发式来选择把 LoRA 应用到哪些权重矩阵，希望未来有更有原则的方法（第 8 节）。
3. 微调或 LoRA 背后的机制"远未清楚"（第 8 节）。
4. 小秩不一定对所有任务或数据集有效；论文给出一个思想实验：如果下游任务使用的语言与预训练语言不同，用 r = d_model 训练整个模型的表现很可能优于小秩的 LoRA（第 7.2 节脚注 6）。
5. 模型规模与最优秩之间的关系仍是开放问题（附录 H.2）。
6. 前缀类方法随可训练参数变多而变差，而 LoRA 的表现趋于稳定（表 15 说明、图 2）。

**自适应攻击者**：论文未评估，**论文未说明**。论文没有攻击者模型，也没有任何自适应攻击实验。

**迁移到联邦 LoRA 微调时可能不成立的假设**（以下均为分析，非论文内容）：

- 分析：论文的低秩假设是在"单主体、任务数据近似同分布"的条件下由下游任务指标间接验证的（第 5 节全部实验）。在跨客户端 Non-IID 数据下，各客户端的 ∆W 子空间是否仍然低秩、是否互相对齐，论文未说明；而论文第 7.2 节的子空间相似度分析恰恰表明不同训练运行之间只有 top-1 方向显著重叠（图 3、图 4），这提示跨客户端子空间分歧可能很大。
- 分析：联邦聚合通常对参数做加权平均，而 LoRA 的参数是 (A, B) 因子对；对 (A, B) 做平均并不等于对 ∆W = BA 做平均，也不保证平均后的乘积仍是各客户端意图的更新。论文只讨论了"合并 W0 + BA"，完全没有讨论多个 BA 的聚合语义。
- 分析：B = 0 的零初始化是"一次训练从零开始"的前提（第 4.1 节）。在联邦多轮中，服务器每轮下发的全局 A、B 会带回历史信息，新加入或重新同步的客户端不再满足"训练开始时 ∆W = 0"，论文的 α/r 缩放与初始化论证不直接适用。
- 分析：论文的 α/r 缩放与"α 取第一个尝试的 r"是单次训练的经验设定（第 4.1 节）；异构客户端若各自选取不同的 r、α 与目标模块（第 7.1 节显示不同权重矩阵贡献差别很大，表 5），聚合时的尺度不一致问题论文未涉及。
- 分析：论文的评估只使用干净验证集上的任务指标（第 5 节），没有任何针对恶意或异常更新的检测指标（如真阳率、假阳率），也没有任何"更新是否被投毒"的判定；因此迁移到投毒防护库时，论文只能作为"被保护对象与可观测量"的依据，不能作为检测算法的依据。
- 分析：论文的合并式部署（W = W0 + BA）在集中式场景是性能优化；在联邦场景中如果服务器直接合并客户端提交的 BA，恶意 BA 会被无差别地写进全局权重，论文没有讨论这种风险。
- 分析：论文假设预训练权重 W0 是可信的、公开的、所有客户端共享的（第 4.1 节、第 4.2 节）；若预训练基座本身来自不可信的发布方，论文的"冻结即安全"的隐含前提不成立（论文未提及基座可信性问题）。

## 10. 对防护库设计的含义

以下全部为分析。

- 分析：库必须在"客户端训练后"提供一个一等公民式的采集钩子，导出逐层的 A、B（以及可选的 BA 乘积）、对应的权重矩阵名称（Wq、Wk、Wv、Wo 或 MLP）、rank r 与缩放系数 α。这是这篇论文暴露出的、区别于普通联邦学习的最特有需求：防护库不能只把客户端更新看作一个扁平向量，而必须理解"低秩因子对"这一数据结构。
- 分析：库需要为每一轮、每个客户端保存版本化的全局基座权重（或至少是被适配层的 W0 引用），因为论文第 7.3 节的投影分析（表 7）需要把 ∆W 与冻结的 W 做对照；没有干净参考权重，就无法复现论文式的范数比与子空间比。
- 分析：库需要提供逐层的范数、奇异值分解与子空间相似度等基础算子作为插件公共设施。论文用到的量很有限——逐层 Frobenius 范数（表 7）、右奇异向量（式 (4)、附录 G）、投影 ||UᵀWVᵀ||_F（第 7.3 节）——这些都可以做成与具体检测算法无关的通用视图，而"用这些量做什么判定"则留给插件。
- 分析：库需要允许插件按层、按权重矩阵类型分别配置策略。论文表 5 显示不同注意力矩阵对性能的贡献差别很大（只适配 Wq 时 WikiSQL 70.4，同时适配 Wq 与 Wv 时 73.7），因此"整模型一个阈值"的做法在这类结构上很可能不合适。
- 分析：干预接口方面，论文只提供了两类结构性动作可以映射为钩子——客户端侧的"只更新 A、B、冻结 W0"参数掩码钩子（第 4.1 节），以及服务器或部署侧的"把 BA 合并进 W0 / 先减后加做任务切换"的权重改写钩子（第 4.2 节）。剔除客户端、重新加权、裁剪等动作论文完全未提供，需要库自行定义接口语义。
- 分析：通用需求与特有需求的分界是：分阶段采集点、跨轮历史快照、干净基座参考、插件注册机制属于通用底座能力（论文只需要其中一部分）；而"以 LoRA 因子为中心的数据视图"（逐层 A/B/BA、rank、α、目标模块名）是这篇论文特有的需求，传统联邦学习的梯度和参数视图不足以表达它。

## 11. 原文依据

1. **摘要**（支持第 1 节"论文类型为基础方法"与第 4 节"把可训练低秩矩阵注入每一层"）：
"We propose Low-Rank Adaptation, or LoRA, which freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture"
2. **第 1 节**（支持第 4 节核心思想与第 9 节"低内在秩是假设"）：
"We hypothesize that the change in weights during model adaptation also has a low intrinsic rank, leading to our proposed Low-Rank Adaptation (LoRA) approach."
3. **第 1 节**（支持第 3 节"入口在本地训练过程"与第 6 节"冻结 W0、只训练低秩矩阵"）：
"LoRA allows us to train some dense layers in a neural network indirectly by optimizing rank decomposition matrices of the dense layers' change during adaptation instead, while keeping the pre-trained weights frozen, as shown in Figure 1."
4. **第 4.1 节**（支持第 3 节与第 5 节"梯度只流经 A、B"）：
"During training, W0 is frozen and does not receive gradient updates, while A and B contain trainable parameters."
5. **第 4.1 节**（支持第 4 节式 (3) 与第 5 节的 ∆W = BA 可观测量）：
"Note both W0 and ∆W = BA are multiplied with the same input, and their respective output vectors are summed coordinate-wise."
6. **第 4.2 节**（支持第 3 节与第 5 节的逐层、逐权重矩阵粒度）：
"In the Transformer architecture, there are four weight matrices in the self-attention module (Wq, Wk, Wv, Wo) and two in the MLP module."
7. **第 4.2 节**（支持第 8 节的显存开销数值）：
"On GPT-3 175B, we reduce the VRAM consumption during training from 1.2TB to 350GB."
8. **第 4.2 节**（支持第 6 节"部署时合并"与第 9 节"无额外推理延迟"的假设）：
"When deployed in production, we can explicitly compute and store W = W0 + BA and perform inference as usual."
9. **第 7.1 节**（支持第 5 节与第 7 节表 5 的结论：不同权重矩阵贡献不同）：
"Note that putting all the parameters in ∆Wq or ∆Wk results in significantly lower performance, while adapting both Wq and Wv yields the best result."
10. **第 4.2 节**（支持第 9 节论文自述局限：合并后难以跨任务批处理）：
"For example, it is not straightforward to batch inputs to different tasks with different A and B in a single forward pass, if one chooses to absorb A and B into W to eliminate additional inference latency."

```json
{
  "key": "hu2021lora",
  "title": "LoRA: Low-Rank Adaptation of Large Language Models",
  "year": 2021,
  "paper_type": "foundation",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["none"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "LoRA 增量矩阵 ∆W = BA（逐权重矩阵、逐层）", "where": "client_post_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "低秩因子 A、B 及其 rank r、缩放 α", "where": "client_post_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "A（或 B）的奇异值与奇异向量，用于子空间相似度 φ（式 (4)）", "where": "client_post_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "冻结预训练权重 W0 及其 Frobenius 范数与投影 ||UᵀWVᵀ||_F（表 7）", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "训练配置：优化器、批大小、学习率、轮数、序列长度、dropout（附录 D 表 9-12、17）", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "下游任务验证集指标：GLUE 准确率/相关系数、BLEU/NIST/METEOR/ROUGE-L/CIDEr、WikiSQL 与 MNLI 验证准确率", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "资源与延迟计量：显存 1.2TB→350GB、检查点 350GB→35MB、吞吐 32.5→43.1 tokens/s per V100、单次前向延迟（表 1）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "适配产生的权重增量 ∆W 具有低内在秩（论文明确标注为假设）",
    "W0 冻结、不接收梯度，只有 A 与 B 可训练，且二者与 W0 乘同一输入并逐坐标相加",
    "A 用随机高斯初始化、B 用零初始化，∆W = BA 在训练开始时为零；∆Wx 按 α/r 缩放，α 取第一次尝试的 r",
    "默认只适配注意力权重（多数实验为 Wq 与 Wv），MLP 冻结；MLP、LayerNorm、bias 留作未来工作",
    "使用 Adam / AdamW 与线性学习率衰减",
    "单一主体同时持有预训练权重与下游任务数据，集中式训练，不涉及多方数据或聚合"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节论文类型为基础方法、第 4 节把低秩矩阵注入每一层", "text": "We propose Low-Rank Adaptation, or LoRA, which freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture"},
    {"section": "Section 1", "supports": "第 4 节核心思想与第 9 节低内在秩假设", "text": "We hypothesize that the change in weights during model adaptation also has a low intrinsic rank, leading to our proposed Low-Rank Adaptation (LoRA) approach."},
    {"section": "Section 1", "supports": "第 3 节攻击入口位于本地训练过程、第 6 节冻结 W0", "text": "LoRA allows us to train some dense layers in a neural network indirectly by optimizing rank decomposition matrices of the dense layers' change during adaptation instead, while keeping the pre-trained weights frozen, as shown in Figure 1."},
    {"section": "Section 4.1", "supports": "第 3 节与第 5 节梯度只流经 A、B", "text": "During training, W0 is frozen and does not receive gradient updates, while A and B contain trainable parameters."},
    {"section": "Section 4.1", "supports": "第 4 节式 (3) 与第 5 节 ∆W = BA 可观测量", "text": "Note both W0 and ∆W = BA are multiplied with the same input, and their respective output vectors are summed coordinate-wise."},
    {"section": "Section 4.2", "supports": "第 3 节与第 5 节的逐层、逐权重矩阵粒度", "text": "In the Transformer architecture, there are four weight matrices in the self-attention module (Wq, Wk, Wv, Wo) and two in the MLP module."},
    {"section": "Section 4.2", "supports": "第 8 节显存开销数值", "text": "On GPT-3 175B, we reduce the VRAM consumption during training from 1.2TB to 350GB."},
    {"section": "Section 4.2", "supports": "第 6 节部署时合并、第 9 节无额外推理延迟假设", "text": "When deployed in production, we can explicitly compute and store W = W0 + BA and perform inference as usual."},
    {"section": "Section 7.1", "supports": "第 5 节与第 7 节表 5：不同权重矩阵贡献不同", "text": "Note that putting all the parameters in ∆Wq or ∆Wk results in significantly lower performance, while adapting both Wq and Wv yields the best result."},
    {"section": "Section 4.2", "supports": "第 9 节论文自述局限：合并后难以跨任务批处理", "text": "For example, it is not straightforward to batch inputs to different tasks with different A and B in a single forward pass, if one chooses to absorb A and B into W to eliminate additional inference latency."}
  ]
}
```
