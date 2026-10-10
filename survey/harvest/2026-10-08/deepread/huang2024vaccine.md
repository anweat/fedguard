# huang2024vaccine：Vaccine: Perturbation-aware Alignment for Large Language Models against Harmful Fine-tuning Attack

## 1. 基本信息

- 场景：集中式大模型训练，具体是"微调即服务"（fine-tuning-as-a-service）的两阶段流程，不是联邦学习。第 3.1 节把流程描述为：服务提供方先在自有对齐数据上做有监督微调（Supervised Fine-Tuning, SFT）得到对齐模型，用户随后上传数据请求微调，服务提供方再在用户数据上做 SFT，最后把定制模型部署在服务器上。训练使用低秩适配（Low-Rank Adaptation, LoRA），第 4.2 节给出 Double-LoRA 实现，即对齐阶段与用户微调阶段各训练一个适配器。
- 训练阶段：安全对齐阶段（论文称 alignment stage，防御在此介入）与用户微调阶段（论文称 user fine-tuning stage，攻击在此发生）。
- 论文类型：防御（针对有害微调攻击的对齐阶段防御），并包含攻击面刻画与经验性机理分析（有害嵌入漂移，Harmful Embedding Drift）。
- 模型与数据规模：Llama2-7B、Opt、Vicuna-7B（第 5.1 节正文写 Opt-3.7B，表 3 与表 5 写 Opt-2.7B，论文前后不一致；表 11 另外使用 OPT-1.3b 到 OPT-13b）。对齐数据来自 BeaverTails 的安全样本，附录 B.1 说明采样 2000 条"有害提示配安全回答"。用户微调任务为 SST2、AGNEWS、GSM8K、AlpacaEval；第 5.1 节默认 1000 条样本、有害比例 p = 0.1（GSM8K 正文写 5000 条而附录 B.1 写 4000 条；AlpacaEval 正文写 700 条）。LoRA 秩为 8（第 5.1 节），附录 B.1 补充 dropout 为 0.1。实验在 A100-80G 上完成（第 5.1 节），表 11 的系统实验在 H100 80GB 上完成。

## 2. 威胁模型

- 攻击者是谁：上传微调数据的用户（user），即数据提供方。第 3.1 节"Threat model"写明假设用户上传一组数据点并要求服务提供方在其上做有监督微调。论文没有讨论恶意服务器、模型发布者或适配器发布者。
- 占比或数量：论文把攻击强度参数化为用户微调数据中有害样本的比例 p，第 3.1 节写明在 N̂ 条数据中有 p·N̂ 条来自有害分布，其余来自良性分布。实验扫描 p = 0（clean）、0.01、0.05、0.1、0.2。论文没有"客户端数量"与"参与率"这类联邦学习概念，论文未说明。
- 能力：攻击者只能控制自己上传的数据。论文没有赋予攻击者修改训练损失、优化器、训练步数、上传更新、聚合过程或评估过程的能力。
- 知识：第 3.1 节说明威胁模型沿用（Qi et al., 2023）。论文未说明攻击者是否知道对齐数据、对齐算法，以及服务提供方是否部署了 Vaccine。反向地，论文明确防御侧不假设能访问用户微调数据（第 1 节与第 3 章开头）。
- 目标：破坏安全对齐（alignment-broken），使定制模型对未见恶意指令给出有害回答，即提高有害分数。论文没有研究定向后门、特定触发器越狱、隐私窃取等目标，论文未说明。
- 防御者是谁：服务提供方。它能看到自己持有的人类对齐问答数据集、模型内部的隐藏嵌入与反向梯度、以及微调后模型对恶意指令的输出（第 5.1 节用 BeaverTails 的审核模型打分）。它信任自己的对齐数据集与训练流程；附录 E 明确说服务提供方"应当完全控制微调过程"。
- 攻击的隐蔽性：第 3.2 节报告有害比例不会显著影响微调准确率，因此攻击无法仅通过观察模型在微调任务上的表现来检测。

## 3. 攻击入口与流程位置

论文是防御论文，它针对的攻击入口如下（依据第 3.1 节威胁模型与图 1）：

- 本地数据准备：攻击体现在用户上传的微调数据里，即在良性任务数据中按比例 p 混入 BeaverTails 的有害指令数据。
- 本地训练过程：服务提供方在这些混合数据上按标准 SFT 流程训练（第 5.1 节的设置：LoRA、AdamW、微调学习率 1e-5、SST2 与 AGNEWS 训练 20 个 epoch、GSM8K 训练 50 个 epoch、批大小 5）。
- 攻击不进入更新上传前的后处理（缩放、投影、拼装）、服务器聚合、全局模型下发等环节，因为论文的场景是集中式单用户微调，论文未说明这些环节。
- 完整步骤：第一步，预训练模型在服务提供方的对齐数据上做 SFT，得到对齐模型；第二步，用户把 p 比例的有害数据混入微调数据并提交；第三步，服务提供方在混合数据上做 SFT；第四步，把定制模型部署，并用 500 条未见恶意指令测有害分数（第 5.1 节）。

## 4. 方法原理

- 核心思想（第 4 章、式 (1) 至式 (3)、算法 1）：在对齐阶段做扰动感知对齐（perturbation-aware alignment），把对齐写成一个极小极大问题。外层最小化对齐数据集上的损失，内层在每一层的隐藏嵌入上加一个 L2 范数不超过 ρ 的扰动 ε，使对齐损失最大化；第 l 层的扰动形式为 f̃(w_l, ε_l)(e_{l-1}) 等于 f(w_l)(e_{l-1}) 加 ε_l，范数约束施加在所有层扰动的拼接向量上。
- 求解：先对最后一层嵌入做泰勒展开，再逐层展开（式 (2)），把内层最大化问题化为线性形式；用 Hölder 不等式可证明最优扰动（式 (3)、附录 C）为 ε*_l(e_l) 等于 ρ 乘以第 l 层隐藏嵌入的梯度 ∇(e_l)L_w(e_l)，再除以所有层拼接梯度的范数。直观上，这个扰动就是当前模型最容易"忘记对齐数据"的方向。
- 算法 1 的每一步：采样一个批；做第一次反向传播得到各层隐藏嵌入的梯度；按式 (3) 计算每层扰动 ε(l,t)；用前向钩子（forward hook）把带扰动的层 f̃(w_l, ε(l,t))(e(l,t)) 等于 f(w_l)(e(l,t)) 加 ε(l,t) 注册进模型；做第二次前向与反向得到加扰动后的梯度；用它更新权重。因此每个优化步需要两次前向与反向，第 4.1 节明确说明这一点，并指出该算法与 FGSM 和 SAM 形式相近。
- LoRA 实现（第 4.2 节，Double-LoRA）：对齐阶段冻结预训练模型，只在注意力模块上加载一个 LoRA 适配器，用带梯度扰动的目标训练它；微调阶段先把对齐适配器合并进预训练模型，再加载并训练第二个适配器完成用户任务，采用普通 SFT。第 5.5 节比较了 Single-LoRA，即对齐与用户微调共用一个适配器。
- 加速版本（附录 A，Accelerated Vaccine）：不再每一步都搜索扰动，而是每 τ 步搜索一次，其余步直接用普通梯度更新，从而把额外开销摊薄。

## 5. 检测或防御所需的数据

论文是防御论文，没有检测器，因此下面逐项列出 Vaccine 本身需要的输入，以及论文用于诊断与评估的观测量。

1. 服务提供方持有的人类对齐问答数据集，元素为 {x_i, y_i}（有害提示配安全回答）。在哪里采集：对齐训练开始之前就在服务提供方手里，对应防护库中服务器侧的训练前位置。粒度：逐样本，附录 B.1 为 2000 条。是否需要跨轮历史：不需要。是否是干净参考数据：它本身就是论文假设服务提供方持有的干净参考数据。是否需要额外前向或反向计算：不需要。是否需要其他客户端的数据：不需要。
2. 每一层注意力模块的隐藏嵌入（hidden embedding，即注意力层的输出 e_l）。在哪里采集：对齐训练的每一个优化步、第一次前向传播时。粒度：逐层、逐批（批大小 5）。是否需要跨轮历史：不需要。是否需要干净参考数据：不需要。是否需要额外计算：需要，它属于为计算扰动而额外做的一次前向与反向。是否需要其他客户端的数据：不需要。
3. 隐藏嵌入上的反向梯度 ∇(e_l)L_w(e_l)，以及所有层拼接梯度的范数。在哪里采集：与第 2 项相同，即对齐训练每一步的第一次反向传播。粒度：逐层、逐批。是否需要跨轮历史、干净参考数据、其他客户端数据：都不需要。是否需要额外计算：需要。
4. 按式 (3) 生成的逐层扰动 ε_l，以及把它注入前向的前向钩子。在哪里采集：对齐训练每一步、第二次前向之前。粒度：逐层、逐批。这一项由方法内部生成，不是外部输入。
5. 对齐数据集上的对齐损失（论文用于诊断，不是方法必需）。第 3.2 节、图 2b 左图与图 3 左图用它衡量模型"忘记对齐知识"的程度，测量发生在用户微调过程中（图 3 的横轴是微调步数）。粒度：整个对齐数据集聚合后的一个数值，按训练步记录。需要跨轮历史：需要，因为要比较不同微调步的损失。需要干净参考数据：需要对齐数据集本身。需要额外计算：需要在对齐数据集上做额外前向。
6. 嵌入漂移（论文用于诊断，不是方法必需）：定义为对齐数据在"对齐阶段模型"与"微调后模型"上隐藏嵌入之差的 L2 范数（第 3.2 节）。在哪里采集：用户微调之后或评估时。粒度：逐层统计、数据集级聚合。需要跨轮历史与干净参考数据：需要缓存对齐阶段模型或其嵌入作为参考。需要额外计算：需要对对齐数据做额外前向。
7. 模型对未见恶意指令的输出文本，以及用 BeaverTails 审核模型判定的有害分数（评估用）。在哪里采集：评估时。粒度：逐样本，第 5.1 节每次采样 500 条测试指令，最后聚合成比例。需要额外计算：需要推理与审核。

防御明确不需要的数据：用户微调数据的原始内容、每个客户端的模型更新或 LoRA 增量、聚合权重、跨轮历史更新、其他客户端的数据。第 2 章明确批评那些要求服务提供方在对齐阶段就拥有用户数据的方法不现实，并把"不假设能访问用户微调数据"作为本文方法的卖点。

攻击留下的可观测痕迹（论文报告）：微调后模型的有害分数上升（表 1、图 2a）；对齐数据集上的对齐损失在微调后期上升（图 3 左图，约 1500 步之后）；对齐数据的隐藏嵌入发生漂移（图 2b 右图、图 3 右图，约 1000 步起变得明显）。论文声称可绕过的检测：论文只声称微调任务上的性能无法暴露该攻击（第 3.2 节），没有评估任何具体检测器，也没有声称能绕过某类检测器，论文未说明其他可绕过的检测。

## 6. 干预动作

- Vaccine 没有"先检测再动作"的环节，也不做剔除客户端、重新加权、裁剪更新、加噪、过滤样本、修复或回滚模型、仅报告中的任何一种。它做的是改变对齐阶段的训练目标与梯度，使最终产出的对齐模型对后续微调引起的嵌入扰动不敏感（第 4.1 节式 (1) 至式 (3)）。
- 动作发生的流程位置是服务提供方的对齐训练阶段，即用户微调请求到来之前，因此它不依赖任何客户端上传内容。
- 流程内唯一的显式动作是在第二次前向时用前向钩子给每层嵌入加上 ε_l，并用加扰动后的梯度更新权重（算法 1）。
- 第 5.5 节与表 9 额外报告了 Vaccine 与 EWC 在用户微调阶段组合的结果，此时才出现微调阶段的正则化干预；附录 E 提出未来可以让微调阶段按统计量（损失、嵌入漂移）过滤或降低有害样本的采样概率，但明确只是想法，论文未实现。
- 论文未说明部署阶段或推理阶段的任何干预动作。
- 分析：从防护库的接口角度看，这篇论文只需要最底层的"模型权重更新"动作，不需要任何针对客户端或更新的干预接口。

## 7. 实验设置与主要结果

- 模型：Llama2-7B、Opt-3.7B（第 5.1 节正文）或 Opt-2.7B（表 3 与表 5）、Vicuna-7B；表 11 另外使用 OPT-1.3b、OPT-2.7b、OPT-6.7b、OPT-13b。
- 数据集：对齐用 BeaverTails 的安全样本，附录 B.1 说明采样 2000 条；用户微调用 SST2、AGNEWS、GSM8K、AlpacaEval；默认 1000 条（GSM8K 正文写 5000、附录 B.1 写 4000，AlpacaEval 写 700），默认 p = 0.1；有害分数用 500 条测试指令计算，微调准确率用 500 对指令标签（AlpacaEval 为 200 对）。
- 客户端数与参与率：论文未说明，因为不是联邦学习场景。
- 轮次与超参数：对齐 50 个 epoch；SST2 与 AGNEWS 微调 20 个 epoch，GSM8K 微调 50 个 epoch；批大小 5；LoRA 秩 8、dropout 0.1；AdamW，对齐学习率 1e-3，微调学习率 1e-5，权重衰减 0.1，余弦学习率衰减，预热比例 0.1（第 5.1 节、附录 B.1）。
- 数据是否非独立同分布：论文未说明，集中式单用户数据不涉及联邦的非独立同分布设定。
- 指标：微调准确率（Fine-tune Accuracy, FA），SST2 与 AGNEWS 为分类正确率，GSM8K 为最终答案正确率，AlpacaEval 为相对 text_Davinci_003 的胜率；有害分数（Harmful Score, HS），用 BeaverTails 的审核模型统计不安全输出比例。
- 表 1（不同有害比例，n = 1000）：Vaccine 的平均有害分数为 46.44、平均微调准确率为 93.4；SFT 为 53.24 与 94.40；Non-Aligned 为 67.52 与 94.64；EWC 的有害分数恒为 50.60 但准确率为 86.32；Vlguard 为 60.20 与 94.68；KL 为 54.76 与 59.08。表中 Vlguard 与 KL 的 Average 列与各自行内的数值不一致，论文原文如此。第 5.2 节称 Vaccine 相比 SFT 最多降低有害分数 9.8%，相比 Non-Aligned 降低 38.2%。
- 表 2（p = 0.05，样本数从 500 到 2500）：Vaccine 平均有害分数 47.92、准确率 93.60；SFT 为 55.20 与 95.00；EWC 有害分数恒为 50.60、准确率 87.76。第 5.2 节说明样本数达到 1500 以上时 EWC 的有害分数可以低于 Vaccine，但其准确率损失超过 6%。
- 表 3（不同模型，表中任务标注为 SST2）：Vaccine 在 Opt-2.7B、Llama2-7B、Vicuna-7B 上的有害分数为 44.60、42.80、43.40，准确率为 91.00、93.00、93.40；SFT 对应为 50.20、52.80、49.80 与 92.00、94.80、94.20。第 5.2 节正文把该结果说成"AGNEWS"，与表 3 表头的 SST2 不一致。
- 表 4（不同下游任务，Llama2-7B）：Vaccine 在 SST2、AGNEWS、GSM8K、AlpacaEval 上的有害分数为 42.80、41.60、65.00、54.00，准确率为 93.00、89.20、22.40、44.23。第 5.2 节称在 AlpacaEval 上有害分数相比 SFT 降低 13.8%（SFT 为 67.80），且准确率更高（SFT 为 43.14）。
- 图 2 与图 3：SFT 模型的嵌入漂移从约第 1000 步开始上升，对齐损失约在第 1500 步之后上升；Vaccine 的漂移与对齐损失都更低（第 5.3 节）。图 4 的 T-SNE 显示有害比例越高嵌入越向特定方向漂移，Vaccine 的漂移更小（第 5.6 节）。
- 表 6（扰动强度消融）：ρ 从 0.01 增到 10 时，有害分数从 54.40 降到 44.20，微调准确率从 94.40 降到 89.00，首步对齐损失从 0.0040 升到 0.0077，末步对齐损失从 0.0437 降到 0.0089。
- 表 7（随机扰动与梯度扰动的对比）：第 5.4 节称在"ρ = 0.2"时梯度扰动同时取得低 7% 的有害分数和高 19.8% 的微调准确率，但表 7 的梯度扰动只有 ρ = 0.01、0.1、1、2、5、10 六行，与数值吻合的是 ρ = 2 那一行（有害分数 49.00 对随机的 56.00，准确率 93.60 对 73.80），论文原文如此。
- 表 8（Single-LoRA 与 Double-LoRA）：第 5.5 节称在 SST2 上 Double-LoRA 让 SFT 的有害分数降低 3%、Vaccine 降低 6.4%，准确率分别下降 0.6% 与 1.4%。
- 表 9（Vaccine 与 EWC 组合）：可再降低有害分数最多 5.2%（SST2）、4.6%（AGNEWS）、超过 26.6%（GSM8K），但微调准确率最多损失 39.2%（SST2，正则强度 λ = 1e12）。
- 表 10（附录 A，加速版本）：每 100 步搜索一次扰动时有害分数为 51.00（比完整版高 0.60），准确率 95.20，单步时间 0.13140 秒（1.02 倍）；每 1000 步时为 52.00，每 10000 步时为 53.20，每 20000 步时为 58.80（接近 SFT 的 59.20）。
- 附录 B.3 修正了（Qi et al., 2023）的说法，认为在纯良性的 SST2 上微调不一定降低安全性：表 1 的 clean 列中 Non-Aligned 的有害分数 34.20 低于 SFT 的 48.60。
- 附录 B.1 写"所有方法在对齐与微调阶段使用同一个 LoRA 适配器"，这与第 4.2 节和附录 B.2 对 Non-Aligned、SFT、Vaccine 使用 Double-LoRA 的描述不一致，论文原文如此。

## 8. 开销

- 表 5（A100，单步训练时间与显存）：SFT 在 OPT-2.7B、Llama2-7B、Vicuna-7B 上的单步时间为 0.14 秒、0.37 秒、0.37 秒，显存为 17.35 GB、38.45 GB、38.43 GB；Vaccine 对应为 0.29 秒、0.73 秒、0.75 秒与 17.42 GB、38.57 GB、38.54 GB。第 5.3 节总结为约比 SFT 慢两倍，显存多约 0.11 GB。
- 原因（第 5.3 节）：每个优化步需要两次前向与反向；额外显存来自第一次前向与反向中需要跟踪的人工扰动。
- 表 11（H100，与 RepNoise 对比）：OPT-13b 上 Vaccine 只比 SFT 多 0.039 GB 显存，单步时间从 0.12 秒变为 0.24 秒；RepNoise 多 27.164 GB 显存，单步时间约为 SFT 的 2.3 到 2.4 倍。附录 B.5 据此认为 Vaccine 在资源受限场景更优。
- 论文强调对齐只需做一次，因此这份开销可以接受（第 5.3 节）。
- 通信开销与存储开销：论文未报告。
- 附录 A 与表 10：Accelerated Vaccine 在 τ = 100 时单步时间为 0.13140 秒（1.02 倍），基本消除额外时间开销。

## 9. 假设、局限与自适应攻击

依赖的假设（论文有依据的部分）：

1. 服务提供方持有并信任一份人类对齐问答数据集用于安全对齐（第 3.1 节 Defense setting）。
2. 对齐阶段完全无法获取用户微调数据（第 1 节的问题设定，也是与 Ripple、元学习类方法的核心区别）。
3. 攻击者只能通过上传数据施加影响，用户微调阶段使用标准 SFT（第 3.1 节）。
4. 内层最大化问题可以用一阶泰勒展开近似，并存在式 (3) 的闭式最优扰动，扰动的 L2 范数约束施加在所有层的拼接上（第 4.1 节、附录 C）。
5. 对齐阶段注入的人工扰动与微调阶段真实的嵌入漂移在方向上足够相关，因此对齐阶段获得的鲁棒性可以迁移到微调阶段。论文用图 2b、图 3、图 4 的漂移统计间接支持这一点，但没有给出形式化保证。
6. 服务提供方完全控制对齐与微调流程（附录 E）。

论文自述的局限（附录 E 与第 6 章）：

1. 只建立在 SFT 之上，没有扩展到 RLHF 及其变体，可能损失通用性。
2. 额外的计算与显存开销，需要剪枝、因式分解等进一步优化。
3. 使用的微调数据集不是 LLM 的主流任务，未来应测试对话、智能体等场景。
4. Vanilla Vaccine 只改对齐阶段，没有利用服务提供方对微调阶段的完全控制；作者提出可以按统计量（损失、嵌入漂移）过滤或降低有害样本采样概率，但未实现。
5. 第 6 章把局限总结为额外开销与对 RLHF 的扩展较弱。

自适应攻击：论文没有评估自适应攻击者。相关工作（第 2 章）列举了更高级的攻击（He et al., 2024；Halawi et al., 2024；Rosati et al., 2024a），但没有做实验。表 1 与表 2 只把有害比例 p 和样本数 n 调大，属于更强的非自适应攻击，论文自己指出有害比例越高，Vaccine 相对 SFT 的优势越小。

迁移到联邦 LoRA 微调时可能失效的假设（分析：）：

- 分析：论文假设微调由服务提供方在中心执行，因此攻击面只有数据。联邦 LoRA 中训练发生在客户端本地，恶意客户端还能修改本地损失、优化器与步数，并在上传前对更新做缩放或拼装，Vaccine 完全没有针对这些能力的评估。
- 分析：论文的对齐阶段是中心化的、只做一次，之后所有微调请求共享同一份对齐产物。联邦 LoRA 中若全局模型逐轮聚合、或客户端各自持有适配器，需要重新定义对齐产物放在哪里、由谁合并；Double-LoRA 的"先合并对齐适配器再训练用户适配器"要求服务器下发与客户端加载流程配合，论文未说明在联邦拓扑下如何实现。
- 分析：论文的效果度量依赖对模型输出的集中式审核（第 5.1 节用 BeaverTails 审核模型）。联邦场景中服务器看不到客户端本地输出，只能在聚合后的全局模型上评估，表 1 至表 4 的结论是否保持，论文未说明。
- 分析：嵌入漂移的机理分析建立在单条连续微调轨迹上；联邦聚合会把多个客户端的漂移方向叠加或抵消，图 4 中"嵌入朝特定方向漂移"的观察不保证成立。
- 分析：论文的 p 是单一数据集内的有害比例，联邦中恶意客户端占比与参与率共同决定有效有害比例。表 1 显示 p = 0.2 时 Vaccine 的有害分数 56.60 与 SFT 的 60.00 已经接近，客户端采样可能把这个有效比例推到方法收益更小的区间。
- 分析：Vaccine 的全部防护建立在这份人类对齐问答数据集上，联邦服务器不一定持有与客户端任务分布匹配的对齐数据，这一前提若不成立，方法无法直接套用。
- 分析：论文自己在第 2 章提到有害微调可以扩展到联邦指令微调（Ye et al., 2024），并建议借鉴联邦投毒防御（Huang et al., 2024b；Ozdayi et al., 2021），但没有做任何联邦实验。

## 10. 对防护库设计的含义

1. 分析：库需要一类"训练过程干预"插件，而不只是"数据抽取"插件。Vaccine 的全部逻辑发生在服务器侧的对齐训练循环内（第 4.1 节算法 1），插件要能替换或包装每一步的损失与梯度计算，并允许在同一步内连续完成两次前向与反向。这是通用能力，任何基于扰动或锐度感知的训练时防御都需要它。
2. 分析：采集底座要能暴露"逐层隐藏嵌入"与"隐藏嵌入上的反向梯度"这两个视图，并允许插件注册前向钩子修改激活值。Vaccine 需要每一层注意力输出的嵌入、它上面的梯度、以及所有层拼接梯度的范数，全部在单步、单批粒度上（第 4.1 节、算法 1）。这比一般的"只看最终更新或逐样本损失"的检测插件更底层，属于这篇论文特有的采集需求。
3. 分析：采集底座要允许"插件不订阅任何客户端数据或客户端更新"这种形态。Vaccine 的输入只有服务器自有的对齐数据集（第 3.1 节），所以插件的依赖声明必须能表达"只用服务器数据"；反之，库不应强制所有插件都挂在客户端钩子上。
4. 分析：库需要把"对齐产物"当作可版本化的模型资产，因为 Double-LoRA 要求先把对齐适配器合并进基座模型、再加载用户适配器训练（第 4.2 节）。对应到联邦 LoRA，服务器钩子需要在全局模型下发前完成这个合并，或明确声明对齐适配器与用户适配器的层级关系。
5. 分析：如果目标是监测这类攻击，库至少要采集三个跨阶段视图：对齐数据集在微调过程中的损失、对齐数据嵌入相对于对齐阶段模型的 L2 漂移（需要缓存对齐阶段的嵌入作为干净参考）、以及聚合后模型输出的有害分数（只能在评估时采）。论文用前两者解释攻击机理（第 3.2 节、图 2 与图 3），只要服务器持有对齐数据，这两者在联邦设置中同样可得，因此通用性较强。
6. 分析：干预接口方面，这篇论文不需要剔除客户端、重新加权、裁剪更新、加噪到更新或回滚模型，只需要最底层的权重更新接口；但附录 E 提出的按损失与嵌入漂移过滤或降权有害样本，提示库应预留逐样本统计加样本过滤或降权的接口，而且表 1 显示该论文方法在高有害比例下收益变小，仅靠对齐阶段加固可能不足。

## 11. 原文依据

1. 第 3.1 节 Threat model。支撑第 2 节攻击者身份与第 3 节攻击入口：攻击者是通过上传数据请求微调的用户，训练由服务提供方执行。
   > Following (Qi et al., 2023), in the user fine-tuning stage, we assume the user uploads a set of data points {ˆxi, ˆyi} ˆN, and asks the service provider supervised fine-tuning (SFT) on them.

2. 第 3.1 节 Threat model。支撑第 2 节与第 9 节：有害数据以比例 p 混入良性微调分布，这是攻击强度的唯一参数。
   > The fine-tuning data is sampled from a mixed of distribution ˆD = λ ˆDB + (1 −λ) ˆDH where ˆDB is the benign distribution for user fine-tuning task and ˆDH is the distribution contains harmful data.

3. 第 3.1 节 Defense setting。支撑第 5 节第一项输入与第 9 节第一条假设：防御方拥有自己的对齐数据集。
   > Following the OpenAI’s RLHF paper (Ouyang et al., 2022), we assume the server hosts a human-aligned QA dataset {xi, yi}N for safety alignment. This dataset contains malicious prompt and safe answer pair (i.e., safe demonstration data).

4. 摘要。支撑第 4 节核心思想：方法在对齐阶段给隐藏嵌入加人工扰动以得到不变嵌入。
   > The core idea of Vaccine is to produce invariant hidden embeddings by progressively adding crafted perturbation to them in the alignment phase.

5. 第 1 节贡献列表。支撑第 4 节与第 9 节：方法不假设能访问用户微调数据。
   > Assume no knowledge of the user data, we develop a robust LLM alignment solution (Vaccine) to strengthen the resilience of the aligned model for fine-tuning on partially harmful user data.

6. 第 4.1 节。支撑第 5 节第二项输入：内层最大化作用在每一层隐藏嵌入上。
   > In the inner maximization function, we aim to find the perturbation ϵ ∈Rd over each layer’s hidden embedding that maximizes the loss over alignment data.

7. 第 4.1 节。支撑第 5 节采集位置与第 8 节开销：每一步需要两次前向与反向。
   > For finding the optimal perturbation, we need the gradient information of the model in the current iteration. Therefore, we need two forward-backward passes for each step of model optimization.

8. 第 4.2 节。支撑第 4 节 LoRA 实现与第 10 节关于对齐产物合并的建议。
   > At fine-tuning stage, we first merge the LoRA adaptor trained for alignment into the pre-trained model. Then we load and train another adaptor for the user fine-tuning task using the general supervised fine-tuning.

9. 第 3.2 节。支撑第 2 节与第 5 节关于攻击可观测痕迹与可绕过检测的论断。
   > Another observation is that the harmful ratio would not significantly affect the fine-tune accuracy, which makes the attack even more stealthy to be detected, i.e., it cannot be detected solely by looking at its performance on the fine-tune task.

10. 第 5.3 节 System performance。支撑第 8 节的开销结论。
    > Our results show that Vaccine is 2x slower than the conventional SFT solution and it also incurs slightly larger GPU memory consumption (approximately 0.11 GB).

```json
{
  "key": "huang2024vaccine",
  "title": "Vaccine: Perturbation-aware Alignment for Large Language Models against Harmful Fine-tuning Attack",
  "year": 2024,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data", "local_training"],
  "observables": [
    {
      "what": "服务提供方自有的人类对齐问答数据集（有害提示配安全回答，BeaverTails 安全样本）",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": false
    },
    {
      "what": "每一层注意力模块的隐藏嵌入（对齐数据在模型中的中间激活）",
      "where": "client_step",
      "granularity": "layer",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "隐藏嵌入上的反向梯度以及所有层拼接梯度的范数",
      "where": "client_step",
      "granularity": "layer",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "对齐数据集上的对齐损失（诊断遗忘程度，按训练步记录）",
      "where": "client_step",
      "granularity": "round",
      "needs_history": true,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "对齐数据隐藏嵌入在对齐阶段模型与微调后模型之间的 L2 漂移（需要缓存对齐阶段嵌入作为参考）",
      "where": "client_post_train",
      "granularity": "layer",
      "needs_history": true,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "微调后模型对未见恶意指令的输出文本与 BeaverTails 审核模型给出的有害分数",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["none"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务提供方持有并信任一份人类对齐问答数据集用于安全对齐（第 3.1 节 Defense setting）",
    "对齐阶段完全无法获取用户微调数据（第 1 节问题设定）",
    "攻击者只能通过上传的有害微调数据施加影响，用户微调阶段使用标准 SFT（第 3.1 节）",
    "内层最大化可用一阶泰勒展开近似且有式 (3) 的闭式最优扰动，L2 约束施加在所有层的拼接上（第 4.1 节、附录 C）",
    "对齐阶段注入的人工扰动与微调阶段真实的嵌入漂移方向足够相关，鲁棒性可以迁移（论文用图 2b、图 3、图 4 间接支持，无形式化保证）",
    "服务提供方完全控制对齐与微调流程（附录 E）",
    "论文自述：方法只建立在 SFT 之上、未扩展到 RLHF，且微调数据集不是 LLM 的主流任务（附录 E）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {
      "section": "3.1 Threat model",
      "supports": "第 2 节攻击者身份与第 3 节攻击入口：攻击者是通过上传数据请求微调的用户，训练由服务提供方执行",
      "text": "Following (Qi et al., 2023), in the user fine-tuning stage, we assume the user uploads a set of data points {ˆxi, ˆyi} ˆN, and asks the service provider supervised fine-tuning (SFT) on them."
    },
    {
      "section": "3.1 Threat model",
      "supports": "第 2 节与第 9 节：有害数据以比例 p 混入良性微调分布，是攻击强度的唯一参数",
      "text": "The fine-tuning data is sampled from a mixed of distribution ˆD = λ ˆDB + (1 −λ) ˆDH where ˆDB is the benign distribution for user fine-tuning task and ˆDH is the distribution contains harmful data."
    },
    {
      "section": "3.1 Defense setting",
      "supports": "第 5 节第一项输入与第 9 节第一条假设：防御方持有自己的对齐数据集",
      "text": "Following the OpenAI’s RLHF paper (Ouyang et al., 2022), we assume the server hosts a human-aligned QA dataset {xi, yi}N for safety alignment. This dataset contains malicious prompt and safe answer pair (i.e., safe demonstration data)."
    },
    {
      "section": "Abstract",
      "supports": "第 4 节核心思想：在对齐阶段给隐藏嵌入加人工扰动以得到不变嵌入",
      "text": "The core idea of Vaccine is to produce invariant hidden embeddings by progressively adding crafted perturbation to them in the alignment phase."
    },
    {
      "section": "1 Introduction (contributions)",
      "supports": "第 4 节与第 9 节：方法不假设能访问用户微调数据",
      "text": "Assume no knowledge of the user data, we develop a robust LLM alignment solution (Vaccine) to strengthen the resilience of the aligned model for fine-tuning on partially harmful user data."
    },
    {
      "section": "4.1 Perturbation-aware Alignment",
      "supports": "第 5 节第二项输入：内层最大化作用在每一层隐藏嵌入上",
      "text": "In the inner maximization function, we aim to find the perturbation ϵ ∈Rd over each layer’s hidden embedding that maximizes the loss over alignment data."
    },
    {
      "section": "4.1 Perturbation-aware Alignment",
      "supports": "第 5 节采集位置与第 8 节开销：每个优化步需要两次前向与反向",
      "text": "For finding the optimal perturbation, we need the gradient information of the model in the current iteration. Therefore, we need two forward-backward passes for each step of model optimization."
    },
    {
      "section": "4.2 Implementation on LoRA-based Fine-tuning",
      "supports": "第 4 节 Double-LoRA 实现与第 10 节关于对齐产物合并的建议",
      "text": "At fine-tuning stage, we first merge the LoRA adaptor trained for alignment into the pre-trained model. Then we load and train another adaptor for the user fine-tuning task using the general supervised fine-tuning."
    },
    {
      "section": "3.2 Risk Analysis",
      "supports": "第 2 节与第 5 节关于攻击可观测痕迹与可绕过检测的论断",
      "text": "Another observation is that the harmful ratio would not significantly affect the fine-tune accuracy, which makes the attack even more stealthy to be detected, i.e., it cannot be detected solely by looking at its performance on the fine-tune task."
    },
    {
      "section": "5.3 Statistical/System Analysis",
      "supports": "第 8 节开销结论：训练时间约为 SFT 的两倍，显存多约 0.11 GB",
      "text": "Our results show that Vaccine is 2x slower than the conventional SFT solution and it also incurs slightly larger GPU memory consumption (approximately 0.11 GB)."
    }
  ]
}
```
