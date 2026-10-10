# huang2024vaccine：Vaccine（扰动感知对齐，Perturbation-aware Alignment）

## 1. 方法一句话

Vaccine 的输入是服务提供方自有的安全对齐数据集 {x_i, y_i}（共 N 条，3.1 节 Defense setting）以及一个待对齐的预训练大语言模型（LLM, Large Language Model）；它输出一个在"隐藏嵌入被人为扰动"的条件下仍然对齐的模型权重 w_{t+1}（论文用 LoRA 适配器实现，4.2 节）。它不检测、不剔除、不修改任何用户微调数据，也不输出"样本是否恶意"的判定；它改变的是对齐阶段（alignment stage）的 SFT（Supervised Fine-Tuning）训练过程，使得之后在混有 p 比例有害数据的用户数据上做普通微调时，模型的 harmful score 更低（摘要、4 节）。

## 2. 运行位置

Vaccine 是集中式的对齐阶段方法，运行在服务提供方一侧，发生在任何用户微调请求之前，且只需要做一次（5.3 节："alignment only needs to be done once for all incoming user fine-tuning"）。

- 运行位置在"对齐阶段"：先在预训练模型上用带扰动的 SFT 做安全对齐，之后用户微调阶段完全保持原样。附录 E 明确写："Vanilla Vaccine implementation only modifies the alignment process but does not modify the fine-tuning process."
- 它不需要用户微调数据，也不需要客户端参与（3.1 节 Defense setting：数据由服务提供方收集；Introduction："Assume no knowledge of the user data"）。
- 与联邦流程的对应关系：论文没有联邦设置，唯一的联邦相关引用是把它列为未来方向（第 2 节提到 harmful fine-tuning 可能扩展到 federated fine-tuning）。**分析**：把它映射到联邦流程，最自然的位置是"服务器下发前"的服务器端离线预处理阶段（server_distribute）——Vaccine 的产物就是随后被下发、被用户（客户端）继续微调的全局模型；它不发生在客户端训练前、不发生在客户端任何训练步、不发生在服务器收到更新或聚合阶段。因此不需要客户端与服务器之间任何额外往返（needs_round_trip = false）。
- **分析**：方法内部没有"服务器聚合"概念；如果搬到联邦场景，论文未给出任何跨客户端聚合规则。

## 3. 算子流水线

以下步骤全部发生在对齐阶段（Algorithm 1 / Algorithm 2），按执行顺序排列。

**步骤 1：采样对齐数据 mini-batch（sample_alignment_batch）**
- 输入：对齐数据集 {x_i, y_i} 中的样本，x 为指令 token 序列，y 为安全回答 token；论文实验里对齐样本是 BeaverTails 中的 2000 条 harmful prompt 加 safe output（附录 B.1）。
- 计算：每个优化步随机采样一个 batch (x_t, y_t)，batch size = 5。
- 输出：一个 batch 的 (x_t, y_t)。
- 出处：算法 1 第 2 行（"Sample a batch of data (xt, yt)"）；5.1 节 Training details；附录 B.1。

**步骤 2：第一次前向 + 反向，取逐层隐藏嵌入梯度（backward_layer_embedding_grad）**
- 输入：batch (x_t, y_t) 与当前权重 w_t；第 l 层的隐藏嵌入 e_{l,t}。
- 计算：做一次完整的前向与反向，取损失对每一层隐藏嵌入的梯度 ∇_{e_{l,t}} L_{w_t}(e_{l,t})。这条路径来自公式 (2)：把对齐损失在 e_L 上做 Taylor 展开，并"对所有层的嵌入依次做 Taylor 展开"，得到 Σ_{l=1}^{L} ε_l^T (dL/de_l)；论文记 ∇_{e_l}L_w(e_l) = dL/de_l。
- 输出：每层一个与 e_{l,t} 同形状的梯度张量（共 L 层）。
- 出处：算法 1 第 3 行（"Backward ∇Lwt(e1,t, · · · , eL,t) with (xt, yt)"）；公式 (2)；4.1 节。

**步骤 3：把所有层的梯度拼接并求全局 L2 范数（concat_layer_gradient_norm）**
- 输入：各层嵌入梯度 {∇_{e_l}L_w(e_l)}_{l=1..L}。
- 计算：按层拼接成一个大向量 ∇L_w(e_1, …, e_L) = (∇_{e_1}L_w(e_1), …, ∇_{e_L}L_w(e_L))，再求它的 L2 范数 ‖∇L_w(e_1, …, e_L)‖。论文在公式 (3) 之后特别加括号说明：扰动的范数约束是对所有层整体施加的（"the norm constraint of the perturbation is imposed over all layers"），即分母是一个跨全部层的全局标量，不是每层各自的范数。
- 输出：一个标量分母。
- 出处：公式 (3) 及其后的说明；附录 C 公式 (4)–(10)。

**步骤 4：构造逐层有界扰动（layerwise_embedding_perturbation）**
- 输入：各层嵌入梯度与步骤 3 的全局范数；扰动强度 ρ。
- 计算：对每一层 l，ε_{l,t} = ρ · ∇_{e_{l,t}}L_{w_t}(e_{l,t}) / ‖∇L_{w_t}(e_{1,t},…,e_{L,t})‖（公式 (3)、算法 1 第 5 行）。这是内层最大化问题 max_{‖ε‖≤ρ} ε^T ∇L_w 的解析最优解，附录 C 用 Hölder 不等式证明：可行解的取值上界是 ρ‖∇L_w‖，而该构造同时满足 ‖ε̂‖ = ρ 且取到上界（公式 (7)–(10)）。它是一个"一步（one-step）梯度近似"，不是迭代投影梯度下降（PGD）；附录 D 明确把 iterative projected gradient method 归给 LAT 而非 Vaccine。同一节也说该算法与 FGSM、SAM 形式相近。
- 输出：每层一个与 e_{l,t} 同形状的扰动张量 ε_{l,t}，整体满足 ‖ε‖ = ρ（梯度非零时）。
- 出处：公式 (3)；算法 1 第 4–6 行；附录 C；4.1 节末段；附录 D。

**步骤 5：注册前向 hook，把扰动注入层输出（forward_hook_add_perturbation）**
- 输入：ε_{l,t} 与第 l 层的原始输出 f_{w_l}(e_{l,t})。
- 计算：用前向 hook 把第 l 层的输出替换为 f̃_{w_l,ε_{l,t}}(e_{l,t}) = f_{w_l}(e_{l,t}) + ε_{l,t}。公式 (1) 的约束写成同样形式：f̃_{w_l,ε_l}(e_{l−1}) = f_{w_l}(e_{l−1}) + ε_l, ∀l ∈ [L]，其中 f̃ 是"把输入映射到受扰动嵌入"的第 l 层（4.1 节），T(x_i) 是产生初始嵌入 e_{i,0} 的 tokenizer 函数。扰动加在隐藏嵌入（hidden embedding）上，不加在参数、输入 token 或梯度上。
- 输出：一个"每一层输出都被加扰"的等价前向模型。
- 出处：公式 (1)；算法 1 第 6 行（"Register forward hook: …"）；4.1 节对 f̃ 的定义。

**步骤 6：带扰动的第二次前向 + 反向，得到"鲁棒梯度"（perturbed_forward_backward）**
- 输入：注入了扰动的模型与同一个 batch (x_t, y_t)。
- 计算：g̃_t = ∇L((f̃_{w_{L,t},ε_{L,t}} ∘ … ∘ f̃_{w_{1,t},ε_{1,t}} ∘ T)(x_t, y_t))，即在被扰动嵌入上前向、再反向求权重的梯度。
- 输出：用于本次更新的梯度 g̃_t。
- 出处：算法 1 第 8 行（"Backward ˜gt = …"）；4.1 节（"we need two forward-backward passes for each step of model optimization"）。

**步骤 7：优化器更新权重（optimizer_step）**
- 输入：当前权重 w_t 与 g̃_t。
- 计算：w_{t+1} = Optimizer_Step(w_t, g̃_t)，即外层最小化 min_w （扰动下的对齐损失）。实验里优化器是 AdamW，学习率 1e-3，weight decay 0.1。
- 输出：更新后的权重 w_{t+1}（LoRA 场景下即适配器参数）。
- 出处：算法 1 第 9 行；公式 (1) 的外层最小化；4.1 节；5.1 节与附录 B.1。

**步骤 8：循环 T 步；可选加速版按周期重算扰动（periodic_perturbation_refresh）**
- 输入：步号 t、扰动周期 τ。
- 计算：算法 2（Accelerated Vaccine）：只有当 t mod τ == 0 时才执行步骤 2–6（求 ε、注册 hook、带扰动反向），否则直接令 g̃_t = ∇L_{w_t}(e_{1,t},…,e_{L,t}) 用普通梯度更新。这样每 τ 个优化步才多出一次前向-反向。
- 输出：同样的权重更新序列，但额外开销被摊薄。
- 出处：附录 A 的 Algorithm 2 及其说明；表 10。

**步骤 9：LoRA 适配器的训练与合并（merge_lora_adaptor）**
- 输入：固定的预训练模型 + 挂在 attention 模块上的 LoRA 适配器；用户微调阶段再挂第二个适配器。
- 计算（4.2 节 Double-LoRA）：对齐阶段固定预训练模型、只训练对齐用 LoRA，训练信号来自上面的扰动感知梯度；对齐结束后把该适配器 merge 进预训练模型；之后用户微调阶段加载并训练另一个适配器，用普通 SFT。实验配置：rank = 8、dropout = 0.1。
- 输出：合并后的对齐模型（作为用户微调的起点）与可交付的权重。
- 出处：4.2 节；5.1 节 Training details；附录 B.1。
- 说明：用户微调阶段本身仍是普通 SFT，不属于 Vaccine 改动（附录 E）。

## 4. 采样与规模控制

- 样本（samples）：每个优化步采样一个对齐数据 batch (x_t, y_t)，batch size = 5（5.1 节；附录 B.1；算法 1 第 2 行）。对齐数据集规模为 2000 条 harmful prompt + safe output（附录 B.1）；3.1 节只把它记为 {x_i, y_i}^N，未在该处给出 N 的数值。
- 层（layers）：扰动施加在"每一层 l ∈ [L]"的隐藏嵌入上（公式 (1)、算法 1 的 for each layer 循环），层数 L 是算法 1 的输入之一，论文未给出 L 的具体数值。
- 轮次（rounds）：对齐共训练 50 epochs（5.1 节；附录 B.1）；算法 1 的总步数 T 是输入，论文未给出具体数值。加速版对"是否重算扰动"做周期抽样，τ ∈ {100, 1000, 10000, 20000}（附录 A 表 10），论文未说明 τ 的选取准则或默认值。
- 客户端（clients）：论文未使用（集中式对齐，不涉及客户端，也不涉及聚合）。
- 参数坐标（coordinates）：论文未使用；扰动在隐藏嵌入空间整体施加，没有做坐标级或层级的子采样，附录 E 只把 sparsification/quantization/factorization 列为未来工作。
- 探针（probes）：防御运行阶段论文未使用任何探针或参考数据；评测阶段使用 500 条 BeaverTails 恶意指令计算 harmful score、500 条（AlpacaEval 为 200 条）指令-标签对计算 fine-tune accuracy（5.1 节 Metrics），这属于评测而非防御流程。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
| --- | --- | --- | --- |
| ρ | 扰动的 L2 范数上界（扰动强度） | 表 6 与表 7 扫描 ρ ∈ {0.01, 0.1, 1, 2, 5, 10}；5.1 节未给出主实验所用默认值（论文未说明） | 表 6、表 7、5.4 节 |
| batch size | 对齐/微调的批大小 | 5 | 5.1 节；附录 B.1 |
| alignment learning rate | 对齐阶段学习率 | 1e-3 | 5.1 节；附录 B.1 |
| weight decay | 权重衰减 | 0.1 | 5.1 节；附录 B.1 |
| optimizer | 优化器 | AdamW | 5.1 节；附录 B.1 |
| alignment epochs | 对齐训练轮数 | 50 | 5.1 节；附录 B.1 |
| LoRA rank | 适配器秩 | 8 | 5.1 节；附录 B.1 |
| LoRA dropout | 适配器 dropout | 0.1 | 附录 B.1 |
| LR scheduler | 学习率调度 | cosine LR decay，warmup ratio 0.1 | 附录 B.1 |
| T | 对齐优化总步数 | 算法 1 的输入，论文未说明具体数值 | 算法 1 input 行 |
| L | 加扰动的层数 | 算法 1 的输入，论文未说明具体数值 | 算法 1 input 行 |
| τ | 加速版重算扰动的周期 | 100 / 1000 / 10000 / 20000 | 附录 A 表 10 |
| 微调 learning rate | 用户微调阶段学习率 | 1e-5 | 5.1 节；附录 B.1 |
| 微调 epochs | 用户微调轮数 | SST2、AGNEWS 为 20，GSM8K 为 50 | 5.1 节；附录 B.1 |
| 超参选择准则 | 对齐 loss 应接近 0（例如 0.01） | 论文陈述的准则 | 附录 B.1 |
| p、n | 攻击侧设定（不是 Vaccine 超参）：用户微调数据中的有害比例与样本数 | 默认 p = 0.1、n = 1000（GSM8K 为 5000，AlpacaEval 为 700） | 5.1 节 |

## 6. 判定与动作

Vaccine 没有"检测—阈值—处置"这一环，它没有阈值、没有聚类、没有剔除或加权规则。

- 它的动作是训练期改动：用一次梯度上升构造出整体范数不超过 ρ 的逐层隐藏嵌入扰动，把该扰动注入第二次前向，再用扰动点的梯度更新参数（公式 (1)、公式 (3)、算法 1）。效果等价于让模型对"用户微调造成的嵌入漂移"不敏感（摘要、4.1 节）。
- 跨轮累积：每个优化步都按当前参数重新计算一次扰动（算法 1）；加速版每 τ 步才算一次扰动，其余步用普通梯度（算法 2）。
- 幅度：扰动幅度由 ρ 控制且构造式给出 ‖ε‖ = ρ；论文没有对权重更新做裁剪，也没有加噪到参数上。表 7 明确把"随机高斯扰动"作为对照组（ρ′ 为均值 0 的高斯方差），Vaccine 采用的是梯度构造的扰动，二者不可混用。
- 论文还报告：ρ 越大 harmful score 越低但 fine-tune accuracy 也越低（表 6，ρ=0.01 → 54.40/94.40，ρ=10 → 44.20/89.00）；把 Vaccine 与 EWC（Elastic Weight Consolidation）微调组合是单独的消融实验（表 9），不属于 vanilla Vaccine。

## 7. 需要的外部资源

- 服务提供方自有的人工对齐 QA 数据集 {x_i, y_i}^N（3.1 节 Defense setting）；实验中使用 BeaverTails 的安全样本，规模为 2000 条 harmful prompt + safe output（附录 B.1）。
- 一个待对齐的预训练 LLM：Llama2-7B、OPT（5.1 节写 Opt-3.7B，表 3 写 Opt-2.7B，两处不一致）、Vicuna-7B（5.1 节）。
- LoRA 适配器（rank 8、dropout 0.1）；Double-LoRA 实现需要对齐与用户微调各一个适配器（4.2 节、5.1 节、附录 B.1）。
- 不需要：用户微调数据、根数据集（root dataset）、预训练检测器、对齐前后的成对权重、任何额外的判别模型。评测阶段额外用到 BeaverTails 的 moderation model 与 500 条测试指令（5.1 节 Metrics），但那属于度量而非防御运行所需资源。

## 8. 计算与存储开销

- 论文报告：Vaccine 每个优化步的训练时间是 SFT 的约 2 倍（表 5，A100-80G：OPT-2.7B 0.14s → 0.29s，Llama2-7B 0.37s → 0.73s，Vicuna-7B 0.37s → 0.75s）；显存略增，正文说约多 0.11 GB，表 5 给出 17.35→17.42 GB、38.45→38.57 GB、38.43→38.54 GB，表 11（H100）给出 OPT-13B 48.824→48.863 GB（即 +0.039 GB）。论文解释额外时间来自"每个优化步两次前向-反向"，额外显存来自"需要追踪第一次前向-反向中的人为扰动"（5.3 节）。
- 与对照防御 RepNoise 相比：Vaccine 显存几乎与 SFT 持平，而 RepNoise 在 OPT-13B 上多 27.164 GB；步时方面 Vaccine 约 2 倍、RepNoise 约 2.3–2.4 倍（附录 B.5、表 11）。
- 加速版把开销摊薄：τ=100 时 1.02x、τ=1000 时 1.004x、τ=10000 时 1.002x、τ=20000 时 1x，但 τ 越大防御越弱（τ=20000 时 HS 从 50.40 升到 58.80）（表 10）。
- **分析**：主要开销集中在步骤 2（第一次前向-反向以获得逐层嵌入梯度）与步骤 6（带扰动的第二次前向-反向）；即每个优化步两次完整前向加两次反向。开销随 batch size、序列长度、层数 L 与隐藏维度（模型规模）增长，随扰动周期 τ 成反比下降。存储上除激活外还需保存每层 ε_l（与各层隐藏状态同形）。论文未说明第一次反向如何保留对嵌入的梯度（是否需要 retain_graph 或两次独立前向）。

## 9. 实现时容易错的地方

论文明确强调或容易读错的点：

1. 归一化是全局的：分母是"所有层梯度拼接后的范数"，不是每层各自的范数；逐层归一化会改变扰动尺度（公式 (3) 后的括号说明，附录 C）。
2. 扰动加在层输出（隐藏嵌入）上，不是加在参数、输入或梯度上（公式 (1) 的约束、算法 1 的 forward hook 行）。
3. 每个优化步需要两次前向-反向：第一次只为求 ε，第二次才产生用于更新的梯度 g̃；只做一次就退化成普通 SFT（4.1 节、算法 1）。
4. 是一步梯度近似（FGSM 式），不是迭代 PGD；附录 D 明确把迭代投影梯度法归给 LAT。
5. 换来的显存增量来自"追踪扰动"，量级很小（+0.039 GB 到 +0.11 GB），不要按"两份模型/两次图"去估算（5.3 节、表 5、表 11）。
6. 训练细节很敏感：batch 只有 5，附录 B.1 明确说更小的学习率或更大的 batch 容易陷入对齐 loss 较大的局部极小，且"在 Vaccine 下更明显"；并给出以对齐 loss 接近 0（约 0.01）作为选参准则。

论文没说清、实现时必须自己决定的点：

1. 主实验使用的 ρ 默认值未在 5.1 节给出，只有表 6/表 7 的扫描范围。
2. 梯度范数为 0 或极小时 ε 无定义，论文未给出数值稳定性处理（需要自己加 eps 或跳过该步）。
3. ε 的作用范围细节：是否对全部 token 位置、全部隐藏维度施加；算法 1 写"each layer l ∈ L"，而 4.2 节只说 LoRA 挂在 attention 模块上，MLP 等模块是否也加扰动论文未说明。
4. 第一次反向传播如何保留对嵌入的梯度（retain_graph 或两次独立前向），论文未说明实现方式。
5. Double-LoRA 的表述与附录 B.1 末句"For all the methods, we use the same LoRA adaptor for alignment/fine-tuning"存在措辞冲突，实现时需要自行确定采用哪一种。
6. 总步数 T 与 50 epochs、batch size 5、2000 条数据之间的换算（是否 drop-last、是否梯度累积）论文未说明。
7. Accelerated Vaccine 的 τ 如何选取、默认值是多少，论文只给了 4 个评测点。
8. 5.4 节正文提到 ρ = 0.2 的对比结果，但表 6/表 7 只列出 0.01、0.1、1、2、5、10，无法对应。
9. 论文未说明随机种子、重复次数与误差棒；checklist 仅以"改变超参做重复实验"作为统计显著性的理由。
10. 论文未说明如何把 Vaccine 扩展到 RLHF（Reinforcement Learning from Human Feedback），附录 E 明确把它列为局限。
11. 客户端数量过少、聚类为空、聚合规则等联邦边界情况不适用（方法不做聚类与聚合）；一旦搬到联邦场景，跨客户端如何合并对齐结果是空白。
12. 5.1 节的模型列表写 Opt-3.7B，表 3 写 Opt-2.7B，复现时需要自行确定模型规格。

## 10. 原文依据

1. 支撑步骤 4（内层最大化与 L2 球约束）："we aim to find the perturbation ϵ ∈Rd over each layer's hidden embedding that maximizes the loss over alignment data. To formulate a meaningful perturbation, we constrain the perturbation to be L2-norm bounded by intensity ρ."
2. 支撑步骤 2 与步骤 6（两次前向-反向）："Vaccine finds the optimal bounded perturbation on embedding that maximizes the alignment loss with the first forward/backward pass of the model, and then we add the perturbation in the second forward/backward pass"
3. 支撑步骤 3（跨层拼接范数、约束施加在所有层上）："where ∇Lw(e1,· · ·, eL)=(∇e1Lw(e1),· · ·, ∇eLLw(eL)) denotes the concatenated gradient over all the hidden embedding (note that the norm constraint of the perturbation is imposed over all layers)."
4. 支撑步骤 7（外层最小化与更新目标）："In the outer minimization, we optimize the model weights that can withstand such an adversarial perturbation, such that the model is robust to the real harmful perturbation that might be introduced in the later user fine-tuning stage."
5. 支撑步骤 5（扰动注入在层输出上）："where ˜fwl,ϵl(el−1) is the l-th layer in a LLM that maps the input to a perturbed embedding and T (xi) is the tokenizer function that produces embedding ei,0."
6. 支撑步骤 9（LoRA 与 attention 模块）："At alignment stage, we fix the pre-trained model and load a LoRA adaptor on the attention modules. The LoRA adaptor is then trained on the alignment data with gradient-based perturbation to learn how to provide helpful but harmless answers."
7. 支撑步骤 8（加速版按周期重算扰动）："The idea of accelerated Vaccine is that we no longer search for the perturbation for every step, but to do it for every τ step."
8. 支撑步骤 1（batch 大小与对齐优化配置）："We pick the learning rate for alignment as 1e −3. We adopt a small batch size 5, weight decay parameter as 0.1 with a AdamW optimizer."

```json
{
  "key": "huang2024vaccine",
  "method": "Vaccine：扰动感知对齐（perturbation-aware alignment），在对齐阶段的 SFT 中用一次梯度上升构造整体 L2 范数为 ρ 的逐层隐藏嵌入扰动，并用扰动点的梯度更新模型",
  "stages": ["server_distribute"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "采样对齐数据 mini-batch",
      "operator": "sample_alignment_batch",
      "input": "服务提供方的对齐数据集 {(x_i,y_i)}，x 为指令 token 序列 [B,S]，y 为安全回答 token",
      "output": "一个 batch (x_t,y_t)，B=5",
      "params": {"batch_size": 5},
      "source": "Algorithm 1 第 2 行；5.1 节；附录 B.1"
    },
    {
      "step": "第一次前向-反向，取逐层隐藏嵌入梯度",
      "operator": "backward_layer_embedding_grad",
      "input": "batch (x_t,y_t) 与当前权重 w_t；第 l 层隐藏嵌入 e_{l,t}",
      "output": "每层梯度 ∇_{e_{l,t}}L_{w_t}(e_{l,t})，与各层 e_{l,t} 同形状",
      "params": {},
      "source": "Algorithm 1 第 3 行；公式 (2)"
    },
    {
      "step": "跨层拼接并求全局 L2 范数",
      "operator": "concat_layer_gradient_norm",
      "input": "各层嵌入梯度 {∇_{e_l}L_w(e_l)}",
      "output": "标量 ‖∇L_w(e_1,…,e_L)‖（跨所有层）",
      "params": {},
      "source": "公式 (3) 及其后说明；附录 C 公式 (4)-(10)"
    },
    {
      "step": "构造逐层有界扰动",
      "operator": "layerwise_embedding_perturbation",
      "input": "各层嵌入梯度与全局范数、扰动强度 ρ",
      "output": "每层扰动 ε_{l,t}，与 e_{l,t} 同形状，整体 ‖ε‖=ρ",
      "params": {"rho": "扫描 0.01/0.1/1/2/5/10，默认值论文未说明"},
      "source": "公式 (3)；Algorithm 1 第 4-6 行；附录 C"
    },
    {
      "step": "注册前向 hook，把扰动注入层输出",
      "operator": "forward_hook_add_perturbation",
      "input": "ε_{l,t} 与第 l 层原始输出 f_{w_l}(e_{l,t})",
      "output": "被替换的层输出 f̃ = f_{w_l}(e_{l,t}) + ε_{l,t}",
      "params": {},
      "source": "公式 (1) 约束；Algorithm 1 第 6 行（Register forward hook）"
    },
    {
      "step": "带扰动的第二次前向-反向，得到鲁棒梯度",
      "operator": "perturbed_forward_backward",
      "input": "注入扰动后的模型与同一 batch (x_t,y_t)",
      "output": "更新梯度 g̃_t = ∇L((f̃_{w_L,ε_L}∘…∘f̃_{w_1,ε_1}∘T)(x_t,y_t))",
      "params": {},
      "source": "Algorithm 1 第 8 行；4.1 节"
    },
    {
      "step": "优化器更新权重",
      "operator": "optimizer_step",
      "input": "w_t 与 g̃_t",
      "output": "w_{t+1}",
      "params": {"optimizer": "AdamW", "lr": 0.001, "weight_decay": 0.1},
      "source": "Algorithm 1 第 9 行；公式 (1) 外层最小化；5.1 节；附录 B.1"
    },
    {
      "step": "加速版：每 τ 步才重算一次扰动",
      "operator": "periodic_perturbation_refresh",
      "input": "步号 t 与周期 τ",
      "output": "t mod τ == 0 时执行前向-反向与扰动注入，否则 g̃_t 取普通梯度",
      "params": {"tau": [100, 1000, 10000, 20000]},
      "source": "附录 A Algorithm 2；表 10"
    },
    {
      "step": "合并对齐 LoRA 并交付给用户微调",
      "operator": "merge_lora_adaptor",
      "input": "训练好的对齐 LoRA 适配器与固定基座模型",
      "output": "合并后的对齐模型，作为用户微调（普通 SFT）的起点",
      "params": {"lora_rank": 8, "lora_dropout": 0.1},
      "source": "4.2 节 Double-LoRA；5.1 节；附录 B.1"
    }
  ],
  "sampling": [
    {
      "what": "samples",
      "how": "每个优化步随机采样一个对齐数据 batch (x_t,y_t)",
      "size": "batch size = 5（5.1 节、附录 B.1）；对齐集共 2000 条 harmful prompt + safe output（附录 B.1）"
    },
    {
      "what": "layers",
      "how": "对每一层 l ∈ [L] 的隐藏嵌入逐层注入扰动，L 为算法 1 的输入",
      "size": "全部层；L 的具体数值论文未说明（算法 1 input 行）"
    },
    {
      "what": "rounds",
      "how": "对齐阶段迭代 T 步；加速版每 τ 步才重算一次扰动",
      "size": "对齐 50 epochs（5.1 节、附录 B.1）；T 论文未说明；τ ∈ {100,1000,10000,20000}（附录 A 表 10）"
    }
  ],
  "resources": [
    "服务提供方自有的人工对齐 QA 数据集 {x_i,y_i}^N（3.1 节 Defense setting）",
    "BeaverTails 的安全对齐样本：2000 条 harmful prompt + safe output（附录 B.1）",
    "待对齐的预训练 LLM：Llama2-7B、OPT、Vicuna-7B（5.1 节；OPT 规格在 5.1 节与表 3 中不一致）",
    "LoRA 适配器（rank 8、dropout 0.1），Double-LoRA 需要对齐与用户微调各一个（4.2 节、5.1 节、附录 B.1）",
    "评测资源（非防御运行所需）：BeaverTails 的 moderation model、500 条恶意测试指令、500/200 条任务测试对（5.1 节 Metrics）"
  ],
  "actions": ["transform_gradients"],
  "dominant_cost": "对齐阶段每个优化步的两次前向-反向传播（第一次求逐层嵌入梯度、第二次在扰动嵌入上求更新梯度），约为 SFT 的 2 倍步时（5.3 节、表 5：OPT-2.7B 0.14s→0.29s，Llama2-7B 0.37s→0.73s，Vicuna-7B 0.37s→0.75s，A100-80G）",
  "underspecified": [
    "主实验使用的扰动强度 ρ 默认值（5.1 节未给出，仅表 6/表 7 有扫描范围）",
    "梯度范数为 0 或极小时 ε 的定义与数值稳定性处理",
    "ε 是否作用于全部 token 位置与全部隐藏维度，是否对 attention 之外的模块（如 MLP）也加扰动",
    "第一次反向传播如何保留对隐藏嵌入的梯度（retain_graph 或两次独立前向）",
    "Double-LoRA 与附录 B.1 末句 use the same LoRA adaptor for alignment/fine-tuning 的措辞冲突",
    "对齐总步数 T 与 50 epochs、batch size 5、2000 条样本之间的换算（drop-last、梯度累积）",
    "Accelerated Vaccine 的 τ 如何选取及默认值",
    "5.4 节正文提到 ρ = 0.2 的对比结果，但表 6/表 7 未列出该取值",
    "随机种子、重复实验次数与误差棒",
    "如何扩展到 RLHF（附录 E 明确列为局限）",
    "若迁移到联邦场景，跨客户端如何合并对齐结果"
  ],
  "quotes": [
    {
      "supports": "步骤 4：内层最大化与扰动 L2 球约束",
      "text": "we aim to find the perturbation ϵ ∈Rd over each layer's hidden embedding that maximizes the loss over alignment data. To formulate a meaningful perturbation, we constrain the perturbation to be L2-norm bounded by intensity ρ."
    },
    {
      "supports": "步骤 2 与步骤 6：每个优化步两次前向-反向",
      "text": "Vaccine finds the optimal bounded perturbation on embedding that maximizes the alignment loss with the first forward/backward pass of the model, and then we add the perturbation in the second forward/backward pass"
    },
    {
      "supports": "步骤 3：跨层拼接梯度与全局范数约束",
      "text": "where ∇Lw(e1,· · ·, eL)=(∇e1Lw(e1),· · ·, ∇eLLw(eL)) denotes the concatenated gradient over all the hidden embedding (note that the norm constraint of the perturbation is imposed over all layers)."
    },
    {
      "supports": "步骤 7：外层最小化与权重更新目标",
      "text": "In the outer minimization, we optimize the model weights that can withstand such an adversarial perturbation, such that the model is robust to the real harmful perturbation that might be introduced in the later user fine-tuning stage."
    },
    {
      "supports": "步骤 5：扰动加在层输出（隐藏嵌入）上",
      "text": "where ˜fwl,ϵl(el−1) is the l-th layer in a LLM that maps the input to a perturbed embedding and T (xi) is the tokenizer function that produces embedding ei,0."
    },
    {
      "supports": "步骤 9：LoRA 挂在 attention 模块并用梯度扰动训练",
      "text": "At alignment stage, we fix the pre-trained model and load a LoRA adaptor on the attention modules. The LoRA adaptor is then trained on the alignment data with gradient-based perturbation to learn how to provide helpful but harmless answers."
    },
    {
      "supports": "步骤 8：加速版按周期 τ 重算扰动",
      "text": "The idea of accelerated Vaccine is that we no longer search for the perturbation for every step, but to do it for every τ step."
    },
    {
      "supports": "步骤 1：batch size 与对齐优化配置",
      "text": "We pick the learning rate for alignment as 1e −3. We adopt a small batch size 5, weight decay parameter as 0.1 with a AdamW optimizer."
    }
  ]
}
```
