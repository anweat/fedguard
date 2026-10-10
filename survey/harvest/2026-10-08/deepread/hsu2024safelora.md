# hsu2024safelora：Safe LoRA: the Silver Lining of Reducing Safety Risks when Fine-tuning Large Language Models

## 1. 基本信息

- 场景：集中式大模型微调（centralized large language model fine-tuning），并且属于参数高效微调（parameter-efficient fine-tuning, PEFT）中的低秩适配（Low-Rank Adaptation, LoRA）。论文全文没有出现联邦学习（federated learning）设定，没有客户端、服务器、聚合器（aggregator）等概念，也没有讨论参数高效微调供应链（PEFT supply chain）；因此本报告按集中式微调处理，并在第 9 节单独讨论迁移到联邦 LoRA 微调的问题。
- 训练阶段：对齐（alignment）之后的下游监督微调（supervised fine-tuning, SFT）阶段。Safe LoRA 作用在微调完成之后、LoRA 权重与对齐模型合并及部署之前，论文称之为后验（post-hoc）处理（第 3 节、第 3.2 节）。
- 论文类型：防御（defense）。方法内部包含一个基于相似度阈值的逐层判定，带有检测或选择成分，但论文的定位是一个安全补丁，而不是独立的检测器、基准或平台。
- 模型与数据规模：主要模型为 Llama-2-7B-Chat 与 Llama-3-8B-Instruct，附录 A.5 另加 Gemma（论文未写明 Gemma 的具体参数量）。数据集为 PureBad（100 条经红队测试收集的有害样本）、Dialog Summary（SAMSum，随机取 1,000 条并混入 100 条有害样本，另取 200 条测试样本）、Alpaca（50,098 条记录，其中 200 条作为验证集）（第 4 节）。LoRA 只加在 q_proj 与 v_proj 两个注意力层上，秩（rank）设为 8（第 4 节 Experiment Settings）。

## 2. 威胁模型

- 攻击者是谁：论文把在微调数据中放入有害样本的使用者视为攻击方，第 4.1 节写 "we assume that users might be malicious"。论文同时覆盖完全良性的微调数据也会削弱安全性的情形（Alpaca，第 4.1 节与表 4），此时并不存在有意的攻击者。论文没有涉及恶意服务器、恶意聚合方、模型发布者或适配器发布者。
- 占比或数量：攻击规模用有害样本的条数或比例表达，而不是联邦意义上的恶意客户端比例。PureBad 是 100 条全有害样本；Dialog Summary 场景是在 1,000 条良性样本中混入 100 条有害样本；附录 A.7 另外考察 10%、30%、50% 三档有害数据占比（对应表 10）。论文未说明客户端数量、参与率与轮次，因为论文不做联邦学习。
- 能力：攻击者能改变的是本地微调数据集的内容（插入有害样本或全部使用有害样本），并能选择训练超参数。论文没有赋予攻击者篡改损失函数、篡改上传更新、控制聚合过程或直接编辑模型权重的能力。
- 知识：论文未说明攻击者对防御方、对齐矩阵（alignment matrix）或阈值的知识。防御侧的设计目标是不对使用者意图作任何假设，见第 5 节结论。
- 目标：破坏安全对齐（safety alignment），使模型对 11 类被禁止的请求不再拒答，属于越狱或安全对齐破坏一类。论文不涉及隐私、无目标精度破坏或后门（backdoor）植入；后门增强对齐（Backdoor Enhanced Alignment, BEA）是作为防御基线引入的方法，不是被研究的攻击。
- 防御者是谁、能看到什么、信任什么：防御者是把 Safe LoRA 打进 LoRA 实现的一方，论文称之为对原始 LoRA 实现的一行补丁（one-liner patch）。它能看到微调后的逐层 LoRA 权重 ∆W_i = A_i B_i^T，以及公开的未对齐与已对齐模型检查点（例如 Llama-2-7b-base 与 Llama-2-7b-chat），并信任这些官方检查点。它不需要看到使用者的训练数据（data-free），也不需要额外训练（training-free）。论文未说明当使用者本人即攻击者时为何会主动启用该补丁，这一部署信任边界在原文中没有展开。

## 3. 攻击入口与流程位置

- 论文所针对的攻击从"本地数据准备"进入：微调数据集被替换为或混入有害样本，例如 PureBad 的 100 条样本，或 Dialog Summary 中混入的 100 条样本。论文明确把含有害或对抗样本的微调数据集称为一次攻击（第 4 节："We call a fine-tuning dataset containing harmful/adversarial examples as an attack"）。
- 攻击随后在"本地训练过程"中生效：LoRA 更新 ∆W_i 把模型推向不安全方向，安全护栏被削弱。论文引用已有工作说明这种削弱在恶意数据与良性数据上都可能出现（第 1 节、第 2.2 节）。
- 论文没有涉及的位置：上传更新前的后处理在论文语境中正是 Safe LoRA 自身所在的防御位置；服务器聚合、全局模型下发、评估与部署都不是攻击入口，论文也没有讨论攻击者操纵这些环节。
- 防御动作所在的位置：在本地 LoRA 微调完成之后、把 LoRA 权重合并进对齐模型与部署之前，对逐层 LoRA 增量做投影替换（第 3.2 节、第 4.1 节）。第 4.2 节把同样的后处理扩展到全参数微调。

## 4. 方法原理

核心思想是：对齐模型与未对齐模型之差的列空间可以近似表示"安全相关子空间"，把偏离该子空间的 LoRA 更新投影回去，就能在不重新训练、不使用数据的前提下恢复安全护栏。

具体步骤（第 3.1 节至第 3.4 节）：

1. 构造对齐矩阵。取一对未对齐与已对齐模型权重，第 i 层的差记为 V_i = W_i^aligned − W_i^unaligned（公式 1）。论文把每一层的权重矩阵独立看待，这一独立性是原文明确写出的处理方式。
2. 构造投影矩阵（projection matrix）。Ĉ_i = V_i (V_i^T V_i)^{−1} V_i^T（公式 2），即由 V_i 的列空间定义的投影算子。
3. 后验投影。微调得到第 i 层 LoRA 权重 ∆W_i = A_i B_i^T 后，当原始更新与投影后更新的相似度低于阈值 τ 时，用投影结果替换原更新，即 ∆W_i = Ĉ_i ∆W_i，条件是 ⟨∆W_i, Ĉ_i∆W_i⟩_F / (||∆W_i||_F ||Ĉ_i∆W_i||_F) < τ（公式 3）。τ 也可以换成"只投影相似度最低的 top-K 层"的方案。
4. 更快的替代版本（第 3.4 节）。把 Ĉ_i 换成 C_i := V_i V_i^T / ||V_i||_F，省去逐层矩阵求逆；论文报告 C 的生成耗时 8.6 × 10^{−3} 秒，Ĉ 需要 2.1714 秒，后者慢约 250 倍。
5. 全参数微调的推广（第 4.2 节，公式 4）：把微调模型相对预训练模型的残差投影，W_i^fine-tuned = W_i^pre-trained + C_i (W_i^fine-tuned − W_i^pre-trained)。
6. 辅助判据（附录 A.4，公式 5）：用 S(C∆W, ∆W) = Σ_{i=1}^{N} 1 / (1 + ||C_i∆W_i − ∆W_i||^2) 汇总逐层相似度，用来判断微调数据是否以有害样本为主（表 6）。

理论解释（第 3.3 节）：论文假设权重空间结构良好，W_aligned 减去 W_unaligned 得到的向量 V 承载与安全相关的概念；LoRA 在低秩矩阵子空间里搜索下游任务解，把该解投影后取低秩解空间与安全子空间的交集，从而同时保留效用与安全。论文没有给出定理或证明，NeurIPS checklist 第 3 项对该问题的回答是 [Yes]，理由为 "We provide in Section 3.3"。

## 5. 检测或防御所需的数据

论文自称方法是 data-free 且 training-free，只需要权重知识（摘要）。逐项列出：

- 逐层 LoRA 增量 ∆W_i = A_i B_i^T。是什么：微调后每一层的 LoRA 更新矩阵。在哪里采集：本地微调结束后，相当于客户端训练后、上传或合并之前。粒度：逐层，论文实验只覆盖 q_proj 与 v_proj，秩 8。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外的前向或反向计算：否，只需要权重张量本身。
- 已对齐与未对齐模型权重对 W_aligned 与 W_unaligned，或其逐层差 V_i。是什么：同一模型家族的 base 与 chat 或 instruct 检查点，例如 Llama-2-7b-base 与 Llama-2-7b-chat（第 3.1 节）。在哪里采集：训练开始之前的离线资产，不属于任何训练阶段的采集；论文把它当作公开可得的检查点。粒度：逐层权重矩阵。是否需要跨轮历史：否。是否需要干净参考数据：是，这是该方法唯一的参考依赖。是否需要额外计算：需要预计算逐层 V_i 与投影算子，但不需要 GPU 前向或反向传播。
- 逐层相似度分数。是什么：原始 LoRA 更新与投影后更新的余弦相似度（cosine similarity，公式 3 的判据），也是图 4 展示的逐层相似度曲线。在哪里采集：本地微调结束后逐层计算。粒度：逐层。是否需要跨轮历史：否。是否需要干净参考数据：需要，依赖上一条的投影算子。是否需要额外计算：需要一次逐层投影与内积计算。
- 跨层汇总相似度 S(C∆W, ∆W)。是什么：附录 A.4 公式 5 定义的逐层相似度加权和，用来区分"只含少量有害样本"和"纯有害数据"的微调模型。在哪里采集：本地微调结束后对全部层求和。粒度：逐层汇总到模型级，论文表 6 中 Llama-2-7B-Chat 在 Alpaca、Dialog Summary、PureBad 上分别为 0.8006、0.7311、0.4469，Llama-3-8B-Instruct 对应为未给出、0.6709、0.4583。是否需要跨轮历史：否。是否需要干净参考数据：需要。是否需要额外计算：需要逐层投影。
- 判定用的超参数。相似度阈值 τ 或 top-K 的层数。这不是采集数据，但决定动作幅度；论文在第 4.1 节给出 τ = 0.35 对应 7 层的例子，并在图 3 给出阈值与投影层数比例的对应关系。

攻击会留下哪些痕迹：论文认为有害微调会让 LoRA 更新方向偏离对齐矩阵，表现为公式 3 的相似度低于阈值；完全用有害样本训练时偏离最大，附录 A.4 的汇总相似度最低（表 6）。论文没有声称该攻击能绕过任何检测，因为这篇论文本身站在防御方；论文报告的是两个防御基线 SafeInstr 与 BEA 在多个设定下无法把有害性分数压到 Safe LoRA 的水平（表 2、表 3、表 4、表 7）。

## 6. 干预动作

- 动作类型：投影替换，不是剔除客户端、重新加权、裁剪、加噪、样本过滤或模型回滚。对判定为低于阈值的层，把 ∆W_i 直接改写为 Ĉ_i ∆W_i（公式 3）；若采用 top-K 方案，则只改写相似度最低的 K 层。第 4.1 节在 PureBad 上投影全部 LoRA 层，在 Dialog Summary 上取 τ = 0.35、投影 7 层；附录 A.7 中 10%、30%、50% 有害数据分别投影 7、18、34 层。
- 动作位置：微调结束之后、LoRA 与对齐模型合并及部署之前，作用于微调方本地的 LoRA 权重。论文没有服务器或聚合环节，也没有"仅报告不干预"的选项。
- 对全参数微调的版本，动作改为对残差权重做投影（公式 4，表 5）。
- 论文未说明被投影层的选择是否需要人工确认，也未说明是否会把逐层相似度分数输出给运维方；论文只把相似度用于选择投影层和附录 A.4 的数据类型判别。

## 7. 实验设置与主要结果

设置：模型为 Llama-2-7B-Chat、Llama-3-8B-Instruct，附录 A.5 增加 Gemma。LoRA 只作用于 q_proj 与 v_proj，秩为 8。Llama-2-7B-Chat 学习率为 5 × 10^{−5}、批大小为 5、所有数据集训练 5 个 epoch；Llama-3-8B-Instruct 在 PureBad 上学习率为 10^{−3}、批大小为 5、训练 5 个 epoch，在 Dialog Summary 上学习率为 10^{−4}、批大小为 32、训练 3 个 epoch。硬件为 NVIDIA H100 80GB GPU 与 AMD Epyc 7313 16 核处理器 ×64（第 4 节）。指标包括效用（Dialog Summary 用 Rouge-1 F1，PureBad 与 Alpaca 用 MT-Bench，1 到 10 分）、有害性分数（11 类基准，GPT-4 打分 1 到 5，越低越安全）、攻击成功率（attack success rate, ASR，回答中不含拒答关键词的比例，关键词表见附录 A.2）。基线为 SafeInstr（安全样本量为 PureBad 的 10%）与 BEA（后门样本量为 PureBad 的 10%）。论文不做联邦学习，因此客户端数、参与率、轮次、非独立同分布（non-IID）设置均未说明。

关键结果：

- PureBad（表 2）：Llama-2-7B-Chat 原始模型效用 6.31、有害性 1.058、ASR 3.03%；原生 LoRA 微调后效用 4.54、有害性 4.66、ASR 95.76%；SafeInstr 为 5.74、1.064、1.21%；BEA 为 5.87、1.203、7.58%；Safe LoRA 为 6.34、1.055、3.03%。Llama-3-8B-Instruct 原始模型为 5.18、1.097、7.27%；原生 LoRA 为 5.85、4.637、94.85%；SafeInstr 为 5.82、1.11、3.64%；BEA 为 6.89、1.31、10.91%；Safe LoRA 为 5.05、1.10、6.36%。
- Dialog Summary（表 3）：Llama-2-7B-Chat 原始模型效用 34%、有害性 1.058、ASR 3.03%；良性微调为 49.57%、1.27、9.70%；混入 100 条有害样本的微调为 50.66%、2.63、45.45%；SafeInstr 为 50.21%、1.32、10.30%；BEA 为 49.89%、1.482、14.55%；Safe LoRA 为 49.79%、1.297、8.79%；在纯良性数据上应用 Safe LoRA 为 50.96%、1.061、3.94%。Llama-3-8B-Instruct 原始模型为 28.66%、1.097、6.36%；攻击下的原生 LoRA 为 49.37%、1.65、20.61%；Safe LoRA 为 49.04%、1.268、10.30%；纯良性数据加 Safe LoRA 为 47.64%、1.15、6.97%。
- Alpaca（表 4，不含有害样本）：原生 LoRA 效用 5.06、有害性 2.25、ASR 86.67%；SafeInstr 为 5.64、2.04、80%；BEA 为 5.37、2.56、83.33%；Safe LoRA 为 5.62、1.09、6.67%。
- 全参数微调（表 5，Llama-2-Chat 与 PureBad）：原生全参微调为 4.71、4.325、95.45%；Safe LoRA 为 1.05、6.401、3.03%。
- 投影矩阵两个版本的对比（表 1，Llama-2-7B-Chat）：PureBad 上 C∆W 的有害性为 1.055、MT-Bench 为 6.34，Ĉ∆W 为 1.18、5.96；Alpaca 上 C∆W 为 1.05、6.35，Ĉ∆W 为 1.06、6.3。
- 阈值与层数的消融（图 3、图 4）：论文报告在约 11% 的层被投影时达到效用与安全的平衡点，Rouge F1 损失小于 2%，有害性分数下降超过 2。贡献列表给出 Llama-2-7B-Chat 约需投影 11% 的层，而 Llama-3-8B-Instruct 需要多达 35%。
- 有害数据比例（表 10，附录 A.7）：10%、30%、50% 有害数据下，无防御的效用为 46.19%、50.19%、48.24%，有害性为 1.533、3.460、3.915，ASR 为 18.18%、66.67%、80.91%；Safe LoRA 的效用为 49.67%、48.92%、49.71%，有害性为 1.301、1.233、1.312，ASR 为 12%、8.79%、10.30%。
- Gemma（表 7，附录 A.5，Dialog Summary）：攻击下原生 LoRA 效用 49.95%、有害性 3.803、ASR 93.33%；SafeInstr 为 50.45%、3.389、90.61%；BEA 为 49.27%、2.818、50%；Safe LoRA 为 46.49%、2.209、32.42%。
- 与 Vaccine 的对比（表 8、表 9，附录 A.6）：Dialog Summary 上单 LoRA Vaccine 效用 10.83%、有害性 3.209、ASR 80.30%；双 LoRA Vaccine 效用 48.53%、有害性 4.455、ASR 94.85%。

分析：第 4.1 节正文称 Safe LoRA 的有害性分数比 SafeInstr 与 BEA "至少低 0.1"，但表 3 中 Safe LoRA 的 1.297 与 SafeInstr 的 1.32 之差约为 0.02，只有与 BEA 的 1.482 之差超过 0.1，正文表述与表 3 数值并不完全一致。论文在 NeurIPS checklist 第 7 项（实验统计显著性）回答 [Yes]，给出的理由是信息都在第 4 节，但正文表格中没有误差棒、置信区间或多次运行的方差。

## 8. 开销

- 论文报告：投影矩阵的生成耗时，C 为 8.6 × 10^{−3} 秒，Ĉ 为 2.1714 秒，后者约慢 250 倍，测量于 NVIDIA H100 80GB GPU（第 3.4 节）。对齐矩阵的存储"确实需要硬件资源，但不占用 GPU，可以存放在磁盘上；投影时逐层加载到 GPU，而不是一次性全部载入"（第 4 节 Experiment Settings）。
- 论文强调方法不需要额外训练数据、不需要额外训练（摘要、第 4.1 节），因此没有额外的数据采集与训练开销；第 4.1 节还指出 Safe LoRA 不像 SafeInstr 与 BEA 那样需要额外数据，后两者的效果还依赖额外数据的数量。
- 论文未报告：对齐矩阵的磁盘占用大小、内存峰值、端到端微调流程的总耗时增量，以及通信开销（论文没有分布式或联邦设定）。论文也未报告多次运行的方差或误差棒。

## 9. 假设、局限与自适应攻击

方法成立所依赖的假设（论文原文有依据的）：

- 可以拿到同一模型家族的一对未对齐与已对齐权重，例如 base 与 chat 检查点；论文默认使用官方发布的模型，因此假定这些检查点公开可得（第 1 节、第 3.1 节）。
- 权重空间结构良好，W_aligned 减去 W_unaligned 能提取出承载安全概念的向量 V，其列空间构成安全子空间（第 3.3 节）。
- 每一层的权重矩阵可以独立处理，逐层构造对齐矩阵与投影（第 3.1 节）。
- LoRA 更新可以写成 ∆W_i = A_i B_i^T，并且投影之后仍能保留下游任务的效用（第 3.2 节、第 3.3 节）。
- 用相似度阈值或 top-K 选择投影层即可在效用与安全之间取得平衡，阈值的取值由图 3 一类经验曲线决定。
- 方法有效性依赖模型自身的对齐强度：论文报告 Llama-2-7B-Chat 约需投影 11% 的层，Llama-3-8B-Instruct 需要多达 35%（第 1 节贡献列表、第 4.1 节）。
- 附录 A.4 的汇总相似度 S 假定纯有害数据训练的模型与良性数据训练的模型在相似度上有明显差距，表 6 中 PureBad 的 0.4469 明显低于 Alpaca 的 0.8006。

论文自述的局限：Broader Impact and Limitations 一节写道，方法的透明性可能使未来出现自适应攻击来规避它，并提到可以把方法推广到文本到图像等多模态模型。NeurIPS checklist 第 2 项回答 [Yes]，理由是局限写在第 5 节。此外第 4.1 节承认 Llama-3-8B-Instruct 上 Safe LoRA 的效用不令人满意（表 2 中为 5.05，低于原始模型的 5.18），表 7 中 Gemma 上的有害性只降到 2.209、ASR 仍为 32.42%。

自适应攻击：论文没有评估任何自适应攻击者，只在局限中提示未来可能被自适应规避，因此本报告把"是否评估自适应攻击"记为否。论文也没有讨论攻击者已知对齐矩阵后刻意构造与安全子空间正交的 LoRA 更新这类情形。

迁移到联邦大模型 LoRA 微调时可能失效的假设（以下均为分析：）：

- 论文的整个流程是集中式的：一个微调方同时拥有训练数据、完整 LoRA 权重和对齐矩阵。联邦场景里服务器只能看到客户端上传的更新；如果客户端使用安全聚合或只上传合并后的模型，服务器就拿不到逐层 ∆W_i，Safe LoRA 只能下移到客户端本地执行，这要求每个客户端都持有对齐矩阵。
- 对齐矩阵依赖同一模型家族的 base 与 chat 检查点。在联邦部署中把这份资产分发给所有客户端会带来显著的下载与存储成本，论文没有给出客户端无法访问私有对齐模型时的替代方案。
- 论文处理的是单次微调产生的 LoRA 增量。联邦中存在多个客户端、非独立同分布数据与部分参与，聚合后的更新是许多不同方向的叠加；论文没有分析对聚合结果做投影与对每个客户端更新分别投影的语义差异，也没有相应实验。
- 论文实验只覆盖 q_proj 与 v_proj、秩为 8。若不同客户端使用不同的目标模块、秩或适配器结构，逐层对齐矩阵的维度与可投影性就不再成立，论文未说明如何处理。
- 论文把防御方与微调方视为同一方。在联邦投毒威胁模型下，恶意客户端不会主动对自己上传的更新做安全投影，因此 Safe LoRA 必须部署在服务器或可信聚合方，而论文没有服务器侧算法。
- 论文用"使用者可能有恶意"来表达威胁，但没有给出跨客户端的信任边界，也没有讨论参考模型本身被投毒（例如发布方或服务器提供错误的 chat 检查点）时会发生什么。

## 10. 对防护库设计的含义

（以下全部为分析：）

- 分析：要支持这篇论文的方法，采集底座必须能在"客户端训练后"与"服务器收到更新时"两个信任边界上导出完整的逐层 LoRA 增量张量（A、B 或 A B^T），而不是只导出范数或压缩后的统计量，因为权重级投影修复无法从摘要统计量重建。这是这篇论文特有的数据视图，大多数聚合类防御只需要范数或梯度。
- 分析：库需要一个独立的参考资产通道，把 W_aligned 与 W_unaligned（或预计算的逐层 V_i、C_i）注册为只读、可校验的模型级参考对象，并能按层惰性加载；它不应混在客户端上传的数据流里。很多检测插件都需要干净参考，这一点是通用的；这篇论文特有的地方在于参考是"同一模型的两个检查点之差"，而不是干净样本集。
- 分析：干预接口不能只有剔除客户端与重新加权两类，必须提供改写客户端更新的权重级修复钩子，允许按层粒度提交替换结果，并把每层的相似度分数、所用阈值、被投影层的清单写回审计记录。这是本论文的核心接口需求。
- 分析：阈值与层数需要按模型校准，库应支持插件读取"阈值到投影层比例"的配置，并能导出图 3、图 4 那类逐层相似度曲线作为调参视图；否则跨模型迁移时（论文报告的 11% 与 35% 差异）没有依据选择 τ。
- 分析：如果方法放在服务器侧执行，库必须明确聚合与投影的先后顺序（先逐客户端投影再聚合，还是先聚合再投影），并把顺序写进插件契约；论文只在单个模型上定义算法，未说明该顺序。
- 分析：附录 A.4 的跨层汇总相似度可以作为服务器侧的粗筛信号，先判断本轮是否存在明显偏离安全的更新，再决定是否对全部层做投影。库应把逐层相似度序列作为标准可导出视图，这样同一份采集数据既能喂给本论文的插件，也能复用于其他基于权重方向的检测器。

## 11. 原文依据

1. 摘要 — "we propose Safe LoRA, a simple one-liner patch to the original LoRA implementation by introducing the projection of LoRA weights from selected layers to the safety-aligned subspace, effectively reducing the safety risks in LLM fine-tuning while maintaining utility."（第 1 节与第 4 节：论文类型是防御，动作是对 LoRA 权重做安全子空间投影。）
2. 摘要 — "It is worth noting that Safe LoRA is a training-free and data-free approach, as it only requires the knowledge of the weights from the base and aligned LLMs."（第 5 节与第 8 节：方法不需要训练数据与额外训练，只需要基础模型与对齐模型的权重知识。）
3. 第 1 节 — "First, we assume access to a pair of unaligned and aligned LLM weights, denoted as Wunaligned and Waligned, which are often available for open-source LLMs such as Llama Base (unaligned) and Chat (aligned) models."（第 5 节的参考资产需求与第 9 节的第一条假设。）
4. 第 3.1 节 — "As a result, given that most open-source LLMs provide both their base model and chat/instruct models, users can conveniently use these official models to construct the alignment matrix without needing to train their own aligned or unaligned model."（第 9 节关于对齐矩阵来源的假设与第 10 节参考资产通道的设计含义。）
5. 第 3.3 节 — "we assume that the weight space is well-structured such that by subtracting Wunaligned from Waligned, we can extract a safety-related vector V in the inner product space constructed by all possible weights"（第 4 节的理论解释与第 9 节的权重空间假设。）
6. 第 3.2 节 — "However, while ∆Wi might weaken the alignment of the original model, it is updated to maximize the utility of the downstream task. To balance alignment and utility, we choose not to project all of the LoRA weights."（第 4 节的逐层选择性投影与第 6 节的干预动作。）
7. 第 3.4 节 — "It takes 8.6 × 10−3 seconds to generate C, while generating ˆC requires 2.1714 seconds, denoting a 250x times slower generation speed. All operations are computed by the NVIDIA H100 80GB GPU."（第 8 节的开销数据。）
8. 第 4.1 节 — "Therefore, we augmented the Dialog Summary dataset with 100 harmful samples. We set the similarity score threshold at 0.35, resulting in projections across 7 layers."（第 3 节的攻击入口描述与第 7 节的阈值与投影层数设置。）
9. 第 4.1 节 — "We project all LoRA layers for the PureBad dataset because the significant distance between the original LoRA weights and the projected weights indicates that the model has been trained in an unsafe direction."（第 6 节的干预动作与第 5 节的攻击痕迹，即权重方向偏离。）
10. Broader Impact and Limitations — "Unfortunately, the transparency of this method may be subjected to future attacks as they might be able to circumvent this in an adaptive manner."（第 9 节关于未评估自适应攻击与论文自述局限的论断。）

```json
{
  "key": "hsu2024safelora",
  "title": "Safe LoRA: the Silver Lining of Reducing Safety Risks when Fine-tuning Large Language Models",
  "year": 2024,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data", "local_training"],
  "observables": [
    {"what": "逐层 LoRA 增量 ∆W_i = A_i B_i^T", "where": "client_post_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "已对齐与未对齐模型权重对 W_aligned 与 W_unaligned（或其逐层差 V_i）", "where": "client_pre_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "原始更新与投影更新的逐层余弦相似度（公式 3）", "where": "client_post_train", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "跨层汇总相似度 S(C∆W, ∆W)（附录 A.4 公式 5）", "where": "client_post_train", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["client"],
  "assumptions": [
    "可获得同一模型家族的一对未对齐与已对齐权重（base 与 chat/instruct 检查点）",
    "官方发布的 base 与 chat 检查点可信且未被投毒",
    "权重空间结构良好，W_aligned 减 W_unaligned 的列空间可表示安全概念子空间",
    "各层权重矩阵可独立处理，逐层构造对齐矩阵与投影算子",
    "LoRA 更新可写为 ∆W = AB^T，投影后仍保留下游任务效用",
    "用相似度阈值或 top-K 选择投影层即可平衡效用与安全，阈值需按模型校准",
    "防御方与微调方是同一方，愿意在微调后对自己的 LoRA 权重施加投影"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节论文类型与第 4 节方法定位：防御动作是把 LoRA 权重投影到安全子空间", "text": "we propose Safe LoRA, a simple one-liner patch to the original LoRA implementation by introducing the projection of LoRA weights from selected layers to the safety-aligned subspace, effectively reducing the safety risks in LLM fine-tuning while maintaining utility."},
    {"section": "Abstract", "supports": "第 5 节与第 8 节：无需额外数据与训练，只需基础模型与对齐模型的权重知识", "text": "It is worth noting that Safe LoRA is a training-free and data-free approach, as it only requires the knowledge of the weights from the base and aligned LLMs."},
    {"section": "Section 1 Introduction", "supports": "第 5 节的参考资产需求与第 9 节关于可获取模型对的假设", "text": "First, we assume access to a pair of unaligned and aligned LLM weights, denoted as Wunaligned and Waligned, which are often available for open-source LLMs such as Llama Base (unaligned) and Chat (aligned) models."},
    {"section": "Section 3.1 Constructing Alignment Matrix", "supports": "第 9 节关于对齐矩阵由官方 base 与 chat 模型构造的假设", "text": "As a result, given that most open-source LLMs provide both their base model and chat/instruct models, users can conveniently use these official models to construct the alignment matrix without needing to train their own aligned or unaligned model."},
    {"section": "Section 3.3 Rationale for Post-Hoc Projection", "supports": "第 4 节的理论解释与第 9 节的权重空间结构假设", "text": "we assume that the weight space is well-structured such that by subtracting Wunaligned from Waligned, we can extract a safety-related vector V in the inner product space constructed by all possible weights"},
    {"section": "Section 3.2 Post-hoc Fine-tuning Projection", "supports": "第 4 节的逐层选择性投影与第 6 节的干预动作", "text": "However, while ∆Wi might weaken the alignment of the original model, it is updated to maximize the utility of the downstream task. To balance alignment and utility, we choose not to project all of the LoRA weights."},
    {"section": "Section 3.4 A Faster Alternative", "supports": "第 8 节的开销数据：C 与 Ĉ 的生成耗时与硬件", "text": "It takes 8.6 × 10−3 seconds to generate C, while generating ˆC requires 2.1714 seconds, denoting a 250x times slower generation speed. All operations are computed by the NVIDIA H100 80GB GPU."},
    {"section": "Section 4.1 Performance Evaluation", "supports": "第 3 节攻击入口（混入 100 条有害样本）与第 7 节的阈值与投影层数设置", "text": "Therefore, we augmented the Dialog Summary dataset with 100 harmful samples. We set the similarity score threshold at 0.35, resulting in projections across 7 layers."},
    {"section": "Section 4.1 Performance Evaluation", "supports": "第 6 节的干预动作（投影全部层）与第 5 节的攻击痕迹（权重方向偏离）", "text": "We project all LoRA layers for the PureBad dataset because the significant distance between the original LoRA weights and the projected weights indicates that the model has been trained in an unsafe direction."},
    {"section": "Broader Impact and Limitations", "supports": "第 9 节：论文未评估自适应攻击，并自述可能被自适应规避", "text": "Unfortunately, the transparency of this method may be subjected to future attacks as they might be able to circumvent this in an adaptive manner."}
  ]
}
```
