# tamirisa2024tar：TAR（Tampering Attack Resistance，抗篡改攻击训练）

## 1. 方法一句话

TAR 的输入是一个已经装了初始安全防护（initial safeguard）的 LLM 参数 θ（论文用 θ_G0 表示初始防护后的模型，θ 表示未加防护的基础模型，见第 4.2 节与 Algorithm 1），以及四个外部对象：训练期攻击者集合 A_train、能力代理数据集 D_retain、安全代理数据集 D_TR、以及外层步数 N、学习率 η、内层攻击步数 K、两个损失权重 λ_TR 与 λ_retain；输出是一份新的权重 θ_G = θ_N，使得该权重在对手做若干步监督微调（SFT）篡改之后，安全指标仍保持较高（第 4 节 Algorithm 1、第 3.2 节）。它不输出任何逐样本的检测判定，而是一次性的离线权重改造（tamper-resistance training）。

## 2. 运行位置

**分析：**这篇论文是集中式（centralized）方法，没有联邦学习（federated learning）流程，也没有客户端、服务器或聚合器的概念。把 TAR 映射到联邦流程里，最自然的位置是"训练之外"：模型开发者在**发布权重之前**，在已有的集中式训练集群上对全局模型做一次离线再训练，得到 θ_G 后直接发布。它不对应联邦流程中的任何运行时环节，也不需要客户端与服务器之间的额外往返（needs_round_trip = false）。

逐阶段说明如下：

- **初始安全防护（第 4.1 节，Algorithm 1 第 1 行）**：位置是"训练之外 / 服务器下发前"。武器化知识限制（weaponization knowledge restriction）用 Random Mapping（附录 C.2 式 3）在开发者本地完成；有害请求拒绝（harmful request refusal）直接用模型自带的 RLHF/DPO 拒绝防护（第 4.1 节、第 5.2 节）。
- **外层循环与内层攻击模拟（第 4.2 节，Algorithm 1）**：位置是"训练之外"。**分析：**内层模拟的 K 步 SFT 在结构上类似联邦中的"客户端每个训练步"本地更新，但那些"客户端"是防御者自己合成的假想攻击者，不是真实参与方，因此不构成联邦训练。
- **retain 项与加权外层更新（式 2、Algorithm 1 第 10、12 行）**：位置是"训练之外"，**分析：**对应"服务器聚合"之后对全局模型做的一次元更新，但这里的"聚合"是防御者在自己的一台/一组 GPU 上做梯度加权求和，不涉及任何跨方通信。
- **可选的额外 100 步良性 SFT（附录 E.2 末尾）**：位置是"训练之外 / 服务器下发前"，用于恢复拒绝设置下的良性能力。

## 3. 算子流水线

按执行顺序如下。约定：θ 表示未加防护的基础模型参数，θ_G0 = θ_0 表示初始防护后的参数，θ_{i-1} 表示第 i 个外层步开始时的参数，d 表示参数总数（Llama-3-8B-Instruct，约 8×10^9），h_θ(·) 表示给定参数下模型的 residual stream 隐藏状态。

**步骤 1：初始安全防护（Initial Safeguard）**

- 输入：基础模型权重 θ；遗忘集数据分布 D_TR（武器化设置）或拒绝补全数据（拒绝设置）；能力代理数据 D_retain。
- 计算：
  - 武器化设置用 Random Mapping（附录 C.2 式 3）：对 x ~ D_TR 的每个输入序列，用 rand_hashed(x) 为每个 token 在每个 residual stream 索引位置上生成一个**固定**的高斯采样向量（"returns fixed Gaussian-sampled vectors that are chosen via hashing the corresponding input token for each residual stream index of x in θ"，附录 C.2）；然后最小化 `1 − 余弦相似度(h_θ(x), rand_hashed(x))` 的期望，再加上 D_retain 上的语言建模交叉熵 L_LM(θ; D_retain)。注意抽取文本中式 3 写作 `1 − |h·r / (‖h‖‖r‖)|`，而正文明确说"maximizes cosine similarity"，因此实现上应理解为 1 减余弦相似度；公式里那对竖线在抽取结果中位置可疑（论文未说明其是否为绝对值记号）。
  - 拒绝设置用已有的拒绝防护：论文说"we can include a refusal safeguard by performing RLHF [43] or DPO [46] on refusal completions"（第 4.1 节）；实验中直接使用 Llama-3-8B-Instruct 自带的拒绝训练（第 5.2 节）。具体用哪一种、用什么数据，论文未说明。
- 输出：θ_0 = θ_G0（Algorithm 1 第 1 行）。注意式 2 的 retain 锚点用的是 θ_G0，即**初始防护之后**的模型（第 4.2 节）。
- 出处：第 4.1 节；Algorithm 1 第 1 行；附录 C.2 式 3。

**步骤 2：采样安全探针批次（每个外层步一次）**

- 输入：D_TR 的 held-out 分片（武器化）或改写后的 refusal/有害偏好对（拒绝，见步骤 6b）。
- 计算：`Sample x_TR ∼ D_TR`，抽一个 minibatch，并在该外层步的全部 K 个内层损失上**复用同一个批次**以降低方差（附录 C.4）。
- 输出：x_TR（一个 held-out minibatch；batch size 论文未说明）。
- 出处：Algorithm 1 中 `Sample xTR ∼ DTR`；附录 C.4。

**步骤 3：采样并模拟训练期攻击轨迹（内层循环）**

- 输入：θ_{i-1}；从 A_train 采样一个攻击配置（数据集、优化器、学习率、调度、batch size、微调范式）。
- 计算：对该攻击配置执行 K 步 SFT，得到一串参数坐标。武器化设置：生物安全用 6 个对手（Pile-Bio Forget-set SFT、Camel-Bio Forget-set SFT、以及 R→F 即先 Retain-set SFT 再 Pile-Bio Forget-set SFT，切换点在 64 步内从 β(6.0, 3.0) 采样），学习率从 {2×10^−5, 4×10^−5} 采样；化学安全 6 个对手（Chem Forget SFT、Retain SFT、R→F），同样从 {2×10^−5, 4×10^−5} 采样；网络安全 6 个对手（Cyber Forget SFT、Retain SFT、R→F）。所有内层对手均为 AdamW、No Warmup、batch size 64、全参数微调、K = 64 步（表 7）。拒绝设置 3 个对手，对 Anthropic-HH-RLHF 的 rejected completions 做 K = 64 步 SFT，学习率从 {2×10^−6, 2×10^−5, 4×10^−5} 采样，AdamW、No Warmup、batch size 64、全参数微调（表 8）。
- 输出：长度 K = 64 的攻击轨迹参数坐标 {attack(θ_{i-1}) 在各步的取值}。
- 出处：Algorithm 1 内层循环；第 4.2 节；第 5.1、5.2 节；附录 E.2 表 7、表 8。

**步骤 4：轨迹坐标复用（效率技巧）**

- 输入：单条长度为 K 的内层攻击轨迹的全部参数坐标。
- 计算：把一条长度 K 的轨迹上的各个坐标同时当作 K 条"递增长度"攻击轨迹的终点，从而用一次 rollout 得到 K 个（非独立的）攻击样本；"we can reuse the coordinates along steps of a single adversary fine-tuning trajectory of length K to obtain K −1 additional (though non-independent) trajectories of increasing length"（附录 C.4，受 snapshot ensembles 启发）。这样 `attack` 是从 A_train **非独立同分布地**采样的。
- 输出：一批 K 个攻击后参数坐标（B 个坐标 × d 参数）。
- 出处：附录 C.4。

**步骤 5：轨迹坐标子采样**

- 输入：K 个坐标。
- 计算：不对全部 K 步计算 L_TR，而是沿轨迹子采样坐标，例如每 4 个攻击优化步取 1 个（"for example every 4 adversary optimization steps"，附录 C.4）。
- 输出：约 K/4 个用于计算 L_TR 的坐标。
- 出处：附录 C.4。

**步骤 6：逐坐标计算抗篡改损失 L_TR**

- 6a（武器化设置）：以熵（entropy）为 L_TR，在内层攻击的整条交叉熵微调轨迹上**最大化熵**，也就是实际实现为最小化负熵；论文寻找的是让对手的交叉熵损失被"压平在一个高值上"，而不是只抬高它的起点（第 4.2 节、附录 C.3、图 3）。输入是攻击后的参数坐标与步骤 2 的 x_TR；输出是标量 L_TR。出处：附录 C.3。
- 6b（拒绝设置）：L_TR 取 DPO 损失（direct preference optimization loss）。数据是 Anthropic-HH-RLHF 的一个改写测试划分，其中 rejected 补全被替换成 refusal；采样的攻击在 rejected 补全上做 SFT，而 L_TR 在攻击轨迹的参数坐标上对 chosen（refusal）与 rejected（有害）补全对计算 DPO 损失，鼓励模型在有害微调之后仍偏好拒绝补全（附录 C.3、附录 E.2）。参考模型用基础权重 θ，训练前预计算整个 Anthropic-HH-RLHF 数据集的参考模型 DPO log-prob（附录 E.2）。DPO 的 β（温度）取值论文未说明。
- 输出：每个采样坐标一个标量 L_TR。
- 出处：附录 C.3；附录 E.2。

**步骤 7：直线估计器（straight-through estimator）反传得到元梯度**

- 输入：L_TR 与攻击轨迹。
- 计算：把攻击写成 `attack(θ_G) = θ'_G = θ_G + attack'(θ_G)` 的扰动形式，对 attack' 的反传用直线估计器近似（第 4.2 节）。论文指出该近似能从一阶 MAML（first-order MAML）的设定中获益，因为攻击是若干步 SFT（第 4.2 节）。
- 输出：对 θ_{i-1} 的近似梯度 ∇_{θ_{i-1}} L_TR(attack(θ_{i-1}), x_TR)。
- 出处：第 4.2 节。

**步骤 8：梯度累积**

- 输入：各采样坐标上的 L_TR 梯度。
- 计算：`g_TR ← g_TR + (1/K) ∇_{θ_{i-1}} L_TR(attack(θ_{i-1}), x_TR)`（Algorithm 1 内层循环与第 7 行）。实现上把 g_TR 累积在一个独立的数据结构里，而不是让 K 个计算图同时驻留显存；论文指出这种累积与施加可以只在分片梯度（sharded gradients）上完成，不需要额外的 all-gather 与 reduce-scatter（附录 C.5）。
- 输出：g_TR ∈ R^d（与模型参数同形状）。
- 出处：Algorithm 1 内层循环；附录 C.5。

**步骤 9：retain 梯度**

- 输入：从 D_retain 采样的一个 minibatch x_r（武器化设置是 Pile-bio Retain 与 Magpie-Align 指令微调数据的混合，附录 E.2；拒绝设置是 Magpie-Align，附录 E.2）；基础/初始防护模型的 residual stream 激活 h_{θ_G0}(x_r)。
- 计算：`g_retain ← ∇_{θ_{i-1}}( L_LM(θ_{i-1}, x_r) + ‖h_{θ_{i-1}}(x_r) − h_{θ_G0}(x_r)‖²₂ )`，即标准语言建模交叉熵加上把 retain 集 residual stream 表示拉回初始防护模型的 ℓ2 锚定项（式 2、Algorithm 1 第 10 行）。Algorithm 1 中该参考激活写作 h_θ(x_r)，而式 2 与第 4.2 节正文写作 h_{θ_G0}(x_r)，两处记号不一致（见第 9 节）。
- 输出：g_retain ∈ R^d。
- 出处：式 2；Algorithm 1 第 9–10 行；第 4.2 节。

**步骤 10：加权外层更新**

- 输入：g_TR、g_retain、学习率 η、权重 λ_TR 与 λ_retain。
- 计算：`θ_i ← θ_{i-1} − η ( λ_TR · g_TR + λ_retain · g_retain )`，对应式 1 的目标 `min_θ λ_TR · E_{attack∼A_train}[ L_TR(attack(θ); D_TR) ] + λ_retain · L_retain(θ; D_retain)`。
- 输出：θ_i。
- 出处：式 1；Algorithm 1 第 12 行。

**步骤 11：循环与输出**

- 重复步骤 2–10 共 N 次，`θ_G ← θ_N`，返回 θ_G（Algorithm 1）。对外层参数本身没有安全/能力阈值判定，训练结束即交付。

**步骤 12（可选，仅拒绝设置）：额外良性 SFT**

- 输入：步骤 11 得到的 θ_G；Magpie-Align 数据。
- 计算：额外做 100 步监督微调以提升良性能力（"In practice, we perform an additional 100 steps of supervised fine-tuning on the Magpie-Align dataset to improve the benign capabilities performance of the TAR refusal model in Table 2"，附录 E.2）。学习率、batch size 等论文未说明。
- 输出：表 2 中报告的 TAR refusal 模型。
- 出处：附录 E.2。

## 4. 采样与规模控制

- **样本（samples）**：D_TR 与对抗攻击数据按 80/20 划分成攻击分片与 held-out 分片，"The adversary data splits are used for sampled attacks from Atrain, whereas the held-out split is used for computing tamper-resistance losses"（附录 E.2），held-out 分片即第 4 节的 D_TR。数据集绝对规模（附录 E.1）：生物安全 Pile 划分共 49,984 条（其中 Forget 7,558 条、Retain 42,426 条），Camel-bio Forget 54,258 条（约 188 词/条），OOD Forget 598,933 条；网络安全为 CTFtime 抓取的 18k 余条；化学安全为私有数据集（条数未说明）。论文强调不要循环使用单一数据集，而是用 held-out 数据集的 minibatch 来算抗篡改损失，理由是 Nichol 等指出一阶元学习若没有正确留出的 minibatch 会掉点（附录 E.2）。
- **客户端（clients）**：论文未使用（集中式方法）。
- **层（layers）**：论文未使用抽样。Random Mapping 定义在"每一层的 residual stream"上（附录 C.2），是全层覆盖而非抽样。
- **参数坐标（coordinates）**：不是对参数抽样，而是对攻击轨迹的**时间坐标**做子采样，例如每 4 个对手优化步一次（附录 C.4）。
- **轮次（rounds）**：外层 N = 750（武器化，第 5.1 节）或 N = 100（拒绝，第 5.2 节）；内层每条轨迹 K = 64（附录 E.2、附录 C.1）。附录 D.3 比较了 K ∈ {8, 16, 32, 64}，最终选 K = 64。
- **探针（probes）**：每个外层步抽 1 个 x_TR 用于全部内层 L_TR 计算（附录 C.4）；拒绝设置还预计算了整个 Anthropic-HH-RLHF 数据集上的参考模型 DPO log-prob（附录 E.2）。
- 外层 D_TR / D_retain 的 batch size、探针的具体条数，论文未说明。

## 5. 超参数

| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| K | 内层模拟攻击的优化步数（轨迹长度） | 64（比较过 8/16/32/64） | Algorithm 1 输入；第 5.1 节；附录 C.1；附录 D.3 图 7 |
| N | 外层抗篡改训练步数 | 750（武器化）；100（拒绝） | 第 5.1 节；第 5.2 节 |
| η | 外层学习率 | 2×10^−5（武器化）；6×10^−5（拒绝） | 第 5.1 节；第 5.2 节 |
| 外层优化器 | — | ScheduleFree AdamW | 第 5.1 节；第 5.2 节 |
| λ_TR | 抗篡改损失权重 | 4.0（生物安全、网络安全）、3.0（化学安全）；0.1（拒绝）；消融中比较过 1.0 与 4.0 | 第 5.1 节；第 5.2 节；附录 E.2；附录 D.4 表 6 |
| λ_retain | retain 损失权重 | 1.0（所有设置） | 第 5.1 节；第 5.2 节 |
| 内层攻击步数 | 与 K 相同 | 64 | 第 5.1 节；表 7；表 8 |
| 内层学习率 | 训练期对手 LR | 武器化从 {2×10^−5, 4×10^−5} 采样；拒绝从 {2×10^−6, 2×10^−5, 4×10^−5} 采样 | 附录 E.2；表 7；表 8 |
| 内层优化器 / 调度 / batch / 范式 | — | AdamW、No Warmup、batch size 64、全参数微调 | 表 7；表 8 |
| R→F 切换点分布 | 先 Retain SFT 再 Forget SFT 的切换点 | β(6.0, 3.0) | 附录 E.2 |
| 坐标子采样步长 | 沿轨迹取 L_TR 坐标的间隔 | 每 4 个对手优化步（"for example"） | 附录 C.4 |
| 拒绝设置额外 SFT | 训练后的良性恢复 | 100 步，Magpie-Align | 附录 E.2 |
| DPO 参考模型 | 拒绝设置的 DPO 参考 | 基础权重 θ，训练前预计算全数据集参考 log-prob | 附录 E.2 |
| DPO 的 β | 未给出 | 论文未说明 | — |

## 6. 判定与动作

TAR **没有运行时检测器，也没有阈值、聚类或剔除规则**；它不判断"哪个客户端/哪条样本是恶意的"，而是在训练阶段把安全约束烘焙进权重本身。具体动作只有两类：

1. **训练期的动作**：初始防护（Random Mapping 的余弦相似度重映射，或既有拒绝训练）先把安全行为装进 θ_0；随后每个外层步执行加权梯度更新 `θ_i ← θ_{i-1} − η(λ_TR · g_TR + λ_retain · g_retain)`（式 1、Algorithm 1 第 12 行）。两个权重的相对大小就是"鲁棒性 vs 能力"的旋钮：λ_TR 从 1.0 提到 4.0 时，Post-Attack Forget 从 39.9 降到 35.2，同时 Retain MMLU 从 62.5 降到 54.7（附录 D.4 表 6）。
2. **损失函数选择就是动作形态**：武器化设置最大化熵，使对手微调轨迹上的交叉熵损失被压平在高位（附录 C.3、图 3、图 6）；拒绝设置用 DPO 损失，使模型在有害 SFT 之后仍偏好 refusal 补全（附录 C.3、图 8）。
3. **跨轮累积**：g_TR 在**一个外层步内部**沿 K 个内层损失累积（`g_TR ← g_TR + (1/K) ∇L_TR`，Algorithm 1 第 7 行）；跨外层步不显式累积梯度，但外层 ScheduleFree AdamW 自身维护优化器状态（附录 C.5），且训练把"对抗鲁棒性"逐步写进权重，因此是跨轮累积效果的。
4. **发现漏洞后的追加动作**：把攻破当前模型的对手（R→F 对手）加进 A_train 重新训练即可"定向打补丁"：把 64 步 R→F 对手加入训练后，全体 26 个对手的平均 Post-Attack Forget 误差改善接近 10 个百分点，对 500 步 R→F 对手（表 9 的 Adv. 8 与 9）改善接近 30 个百分点（附录 D.2 表 4）。
5. **交付后**：模型发布即完成，运行期不再有任何判定或动作。

## 7. 需要的外部资源

- **基础 LLM**：Llama-3-8B-Instruct（第 5.1、5.2 节）；对比基线还用 Zephyr-7B（R2D2）与 Llama-2-7B（RepNoise），但这不是 TAR 自身所需。
- **遗忘集 / 安全代理数据**：Pile 的生物相关合成标注划分（Forget 7,558 条）、Camel AI Biology（54,258 条）、与 WMDP biosecurity Forget 相同的 held-out OOD 有害生物数据（598,933 条）、私有化学安全数据、CTFtime 抓取的网络安全 writeup（18k 余条）（附录 E.1）。
- **retain / 能力代理数据**：Pile-bio Retain（42,426 条）与 Magpie-Align 指令微调数据的混合（附录 E.1、E.2）。
- **拒绝设置的数据**：Anthropic-HH-RLHF 的 rejected completions（训练期攻击数据），以及一个把 rejected 补全替换成 refusal 的改写测试划分（DPO 的 chosen/rejected 对来源）；参考模型是基础权重 θ，需要预先在整个 Anthropic-HH-RLHF 上算好参考 log-prob（附录 E.2）。
- **对齐前后的权重**：式 2 需要初始防护模型 θ_G0（= θ_0）的 residual stream 激活作为锚点，因此训练时必须保留一份该模型的激活/权重（第 4.2 节、式 2）。
- **训练期对手集合的定义**：6 个（武器化，每域）或 3 个（拒绝）SFT 攻击配置，含数据、优化器、LR、batch、范式（表 7、表 8）。
- **评测资源**：WMDP（3,668 道选择题）、MMLU（57 个任务）、HarmBench、MT-Bench、Toxic-DPO v0.2（541 条有害对话）、26 个武器化测试期对手配置（表 9）、5 个拒绝测试期对手配置（表 10）。
- **算力**：8 张 NVIDIA 80GB A100，FSDP 分布式训练，DeepSpeed ZeRO Stage 3（附录 C.5）。

## 8. 计算与存储开销

论文报告的开销：

- "Optimizing Equation 1 with gradient descent requires simulating K tampering attacks for each tamper-resistance optimizer update, which is prohibitively expensive to run when the sampled attack performs SFT and θ contains billions of parameters."（附录 C.4）——即朴素实现是每次外层更新 K 条完整 SFT 轨迹。
- 一阶元学习若按常规为每个内层项保留计算图，"this requires maintaining K computation graphs in memory. Since this is infeasible on reasonable hardware for LLMs with billions of parameters"（附录 C.5），所以要改成梯度累积。
- 内层带动量等状态的对手需要每个外层迭代新建一个优化器，因此要把外层优化器先搬到 CPU；该梯度累积与施加可以只在分片梯度上做，不引入额外 all-gather / reduce-scatter（附录 C.5）。
- 论文在局限中说"Scaling to larger models poses computational challenges that require optimization to reduce overheads"（附录 A）。
- 论文**没有报告** wall-clock 时间、GPU 小时数或峰值显存数字（论文未说明）。

**分析：**主要开销来自步骤 3 的内层攻击模拟与步骤 7 的元梯度反传：每个外层步要做约 K = 64 步 SFT（每步一次前向加反向），再加上对子采样坐标（默认每 4 步一个，约 16 个）各做一次 L_TR 的前向加对 θ_{i-1} 的反向，以及 retain 项的一次前向加反向。总训练计算量约随 **N × K × 模型参数量 × 序列长度** 增长（拒绝设置 N=100，武器化 N=750），显存主要占用在模型参数、分片后的优化器状态与梯度、以及每层 residual stream 激活（式 2 的锚定项要求同时拿到 θ_{i-1} 与 θ_G0 的激活，因此至少需要两份激活中的一份或一次额外的参考前向）。论文用坐标复用（把一次 rollout 变成 K 个攻击样本）与坐标子采样把"K 条独立轨迹"降为"1 条轨迹"，这是它声称的主要效率来源（附录 C.4）。

## 9. 实现时容易错的地方

论文明确强调的实现细节与边界情况：

1. **两个阶段缺一不可**。只用 Random Mapping 不做对抗训练（表 5 的 "Excl. Adv. Training"），Pre-Attack Forget 低到 27.3 但 Post-Attack Forget 反弹到 61.6；只用对抗训练不做初始防护（"Excl. Initial Safeguard"），Pre-Attack Forget 高达 47.3。初始防护把 pre-attack 遗忘集准确率压低 19.2 个百分点（附录 D.4）。
2. **L_TR 的选择很关键**。直接用被钳制的负交叉熵（先前 MLAC 思路）只能抬高轨迹起点的损失，后面很快恢复；论文给出两种可行选择——武器化用负熵、拒绝用 DPO（附录 C.3、图 3、图 6）。直接用无钳制的负交叉熵会发散（第 4.2 节）。
3. **K 越大越鲁棒也越贵**。图 7 显示 K 增大时测试期损失平台的幅值与时长都增加，K = 64 是鲁棒性与效率的折中（附录 D.3）。
4. **必须使用留出的 minibatch**。用 held-out 数据集而不是循环单个数据集来算 L_TR，否则一阶元学习掉点（附录 E.2 引 Nichol 等）。
5. **同一外层步内复用同一个 x_TR** 以降低元梯度方差（附录 C.4）。
6. **对手集合要覆盖 R→F**。不采样 R→F 对手会留下明显漏洞；把 64 步 R→F 加进训练可以把对该类 500 步测试攻击的鲁棒性提高近 30 个百分点（附录 D.2 表 4）。
7. **显存管理**：(a) 每个外层迭代重建内层优化器，并把外层优化器移到 CPU；(b) 不要保留 K 个计算图，改为把 g_TR 累积到独立结构；(c) 累积与更新在分片梯度上完成即可，不需要额外通信（附录 C.5）。
8. **数据卫生**。第一版发布的 retain 数据 Magpie-Align 含大量遗忘集内容，导致意外的输入空间漏洞；清洗数据并重训后该漏洞不再出现（附录 C.1）。另外 HuggingFace 的分布式 dataloader sampler 会用默认种子覆盖用户设定的种子，使测试期 shuffling 顺序变成训练期顺序的子集，修正后 1000 步微调下的鲁棒性才会显出波动（附录 C.1）。
9. **已知薄弱面**：对参数高效微调（PEFT）和部分分布外学习率的攻击鲁棒性较弱，说明方法对训练期对手分布敏感（第 5.3 节）。
10. **能力代价**：TAR 平均降低 retain 准确率 10.6%（第 5.1 节）；且在 post-attack forget 低时 post-attack retain 也低，论文认为这不影响防御者，但良性用户微调时必须避免数据被遗忘集污染（附录 A）。
11. **不涉及聚类或阈值**：TAR 没有聚类、没有阈值、没有客户端剔除，因此"客户端太少""聚类为空"这类边界情况在本文中不适用；对应地也不存在剔除比例的取值。

论文没说清、实现时必须自己决定的地方：

1. 外层 D_TR 与 D_retain 的 batch size、每个 batch 的条数一概未说明（只给了内层对手的 batch size 64）。
2. 式 2 中两项（L_LM 与 ℓ2 激活锚定）的相对权重未给出；Algorithm 1 第 10 行是把两项直接相加。
3. 保留锚点的参考模型在 Algorithm 1 里写作 h_θ，在式 2 与第 4.2 节写作 h_{θ_G0}；到底锚定"未加防护的基础模型"还是"初始防护后的 θ_0"需要自己决定。
4. 熵损失的具体定义未说明：是对哪些 token 位置、哪个词表分布求熵，是否只取 response/forget 相关 token，是否对序列取平均，均未交代。
5. 坐标子采样后 g_TR 的归一化方式未说明：Algorithm 1 第 7 行写的是 1/K，但 C.4 只对部分坐标求 L_TR，是否要相应改成 1/(采样坐标数) 论文未说明；"every 4 adversary optimization steps" 中的 4 也只是举例。
6. Random Mapping 的优化器、学习率、步数、batch size 均未给出（附录 C.2 只有目标函数）；rand_hashed 的向量维度、逐层逐位置如何哈希、如何在词表维度与 hidden 维度间对齐也未说明。
7. R→F 对手切换点所服从的 β(6.0, 3.0) 的具体语义（是占 64 步的比例还是绝对步数）未说明。
8. Algorithm 1 内层 `for k = 1 to K` 与附录 C.4 的"一次 rollout 复用 K 个坐标"如何对应（是否仍要循环 K 次、K 是否随子采样改变）未说明。
9. 拒绝设置里 DPO 的 β、chosen/rejected 的构造细节（引用 [6] 的改写流程）、以及是否对序列做长度归一化都未说明。
10. 拒绝设置模型来自"现有 refusal safeguard"，但具体是 RLHF 还是 DPO、用什么数据训练，论文未说明。
11. 额外 100 步良性 SFT 的学习率、batch size、是否冻结层等未说明。
12. 式 3 中绝对值符号是否为论文原意（正文说是最大化余弦相似度）需要自己判断。

## 10. 原文依据

1. **支撑步骤 1（初始安全防护用 Random Mapping）**："As a proxy for scrubbing target representations according to downstream task labels, we propose a weaponization knowledge restriction safeguard termed Random Mapping, which maps hθ(DTR) to random noise as follows:"（附录 C.2）
2. **支撑步骤 2 与步骤 8（同一 held-out 批次、降低方差）**："Additionally, we reduce variance in the tamper-resistance gradient by computing the tamper-resistance loss at each inner loop step on the same held-out batch, denoted as xTR in Algorithm 1."（附录 C.4）
3. **支撑步骤 3（直线估计器近似穿过攻击的反传）**："defining attack(θG) = θ′G = θG + attack′(θG) as a perturbation on top of initial parameters, where backpropagation through attack′ is approximated with a straight-through estimator [5]."（第 4.2 节）
4. **支撑步骤 4（轨迹坐标复用）**："we leverage an efficiency trick: we can reuse the coordinates along steps of a single adversary fine-tuning trajectory of length K to obtain K −1 additional (though non-independent) trajectories of increasing length."（附录 C.4）
5. **支撑步骤 5（轨迹坐标子采样）**："To further improve runtime efficiency, we do not compute the tamper-resistance loss LTR on all K steps and instead sub-sample coordinates along the trajectory for computing LTR within an adversary batch, for example every 4 adversary optimization steps."（附录 C.4）
6. **支撑步骤 6a（武器化设置取熵作为 L_TR）**："We choose the tamper-resistance loss LTR as an entropy loss to be maximized during the adversary's cross-entropy fine-tuning trajectory, since maximizing entropy would impede the adversary's cross entropy loss from decreasing during fine-tuning."（附录 C.3）
7. **支撑步骤 6b（拒绝设置取 DPO 作为 L_TR）**："the sampled attack performs SFT on rejected completions, and the tamper-resistance loss LTR is a DPO loss computed on the pair chosen and rejected completions on parameter coordinates along the attack trajectory."（附录 C.3）
8. **支撑步骤 9（retain 项把表示锚回初始防护模型）**："Empirically, we find that pushing retain-set residual stream representations to be close to the base model θG0 via the ℓ2-norm loss in Equation 2 maintains a high capabilities_metric(θG)."（第 4.2 节）

```json
{
  "key": "tamirisa2024tar",
  "method": "TAR (Tampering Attack Resistance): adversarial meta-training that bakes a tamper-resistant safeguard into open-weight LLM weights by simulating K-step SFT tampering attacks in an inner loop and applying a weighted outer-loop update of a tamper-resistance loss plus a retain/representation-anchor loss",
  "stages": ["outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "initial_safeguard",
      "operator": "random_mapping_representation_scrub",
      "input": "base LLM weights theta; forget-set input sequences x ~ D_TR; retain data D_retain",
      "output": "initially safeguarded weights theta_0 = theta_G0",
      "params": {"objective": "min E_x[1 - cosine_similarity(h_theta(x), rand_hashed(x))] + L_LM(theta; D_retain)", "optimizer": "论文未说明", "lr": "论文未说明", "steps": "论文未说明"},
      "source": "Section 4.1; Algorithm 1 line 1; Appendix C.2 Equation 3"
    },
    {
      "step": "sample_probe_batch",
      "operator": "sample_probe_batch",
      "input": "D_TR (held-out forget-set split for weaponization; rewritten refusal-preference pairs for refusal)",
      "output": "x_TR: one held-out minibatch reused across all K inner-loop loss terms in the outer step",
      "params": {"batch_size": "论文未说明", "reuse_across_inner_steps": true},
      "source": "Algorithm 1 'Sample xTR ~ DTR'; Appendix C.4"
    },
    {
      "step": "simulate_train_time_attack_trajectory",
      "operator": "sft_adversary_rollout",
      "input": "theta_{i-1}; one attack config sampled from A_train (dataset, optimizer, LR, schedule, batch size, FT paradigm)",
      "output": "K = 64 parameter coordinates along the SFT attack trajectory",
      "params": {"K": 64, "optimizer": "AdamW", "lr_schedule": "No Warmup", "batch_size": 64, "ft_paradigm": "Full Parameter", "inner_lr_weaponization": "{2e-5, 4e-5} sampled", "inner_lr_refusal": "{2e-6, 2e-5, 4e-5} sampled", "R2F_switch_point": "beta(6.0, 3.0)"},
      "source": "Algorithm 1 inner loop; Section 5.1; Appendix E.2 Table 7 and Table 8"
    },
    {
      "step": "reuse_trajectory_coordinates",
      "operator": "reuse_trajectory_coordinates",
      "input": "the K parameter coordinates of a single inner-loop SFT trajectory",
      "output": "K attack samples (K-1 extra non-independent trajectories of increasing length), sampled non-IID from A_train",
      "params": {"K": 64},
      "source": "Appendix C.4"
    },
    {
      "step": "subsample_trajectory_coordinates",
      "operator": "subsample_trajectory_coordinates",
      "input": "K trajectory coordinates",
      "output": "subset of coordinates used for L_TR (e.g. every 4th adversary optimization step)",
      "params": {"stride": "4 (论文写作 for example)"},
      "source": "Appendix C.4"
    },
    {
      "step": "tamper_resistance_loss_weaponization",
      "operator": "max_entropy_loss",
      "input": "attacked parameters attack(theta_{i-1}) at each sampled coordinate; held-out batch x_TR",
      "output": "scalar L_TR per coordinate (entropy of the attacked model's output distribution, maximized)",
      "params": {"loss": "entropy maximized (implemented as negative entropy minimized)", "token_positions": "论文未说明", "reduction": "论文未说明"},
      "source": "Section 4.2; Appendix C.3; Figure 3; Figure 6"
    },
    {
      "step": "tamper_resistance_loss_refusal",
      "operator": "dpo_loss",
      "input": "chosen (refusal) vs rejected (harmful) completion pairs from a modified Anthropic-HH-RLHF split; policy model at attack-trajectory coordinates; precomputed reference-model log-probs from base weights theta",
      "output": "scalar L_TR per coordinate (DPO loss)",
      "params": {"beta": "论文未说明", "reference_model": "base weights theta, reference log-probs precomputed over the full Anthropic-HH-RLHF dataset"},
      "source": "Section 4.2; Appendix C.3; Appendix E.2"
    },
    {
      "step": "straight_through_meta_gradient",
      "operator": "straight_through_estimator_gradient",
      "input": "L_TR at attacked coordinates; attack written as attack(theta_G) = theta_G + attack'(theta_G)",
      "output": "approximate gradient grad_{theta_{i-1}} L_TR(attack(theta_{i-1}), x_TR)",
      "params": {"estimator": "straight-through estimator, benefiting from first-order MAML approximations"},
      "source": "Section 4.2"
    },
    {
      "step": "accumulate_tamper_resistance_gradient",
      "operator": "accumulate_gradients",
      "input": "per-coordinate L_TR gradients",
      "output": "g_TR in R^d, accumulated as g_TR += (1/K) * grad L_TR",
      "params": {"normalization": "1/K per Algorithm 1 line 7; renormalization after coordinate subsampling 论文未说明", "storage": "separate gradient buffer instead of K computation graphs; sharded-gradient only, no extra all-gather/reduce-scatter"},
      "source": "Algorithm 1 inner loop and line 7; Appendix C.5"
    },
    {
      "step": "retain_gradient",
      "operator": "retain_ce_activation_anchor",
      "input": "minibatch x_r ~ D_retain (Pile-bio Retain + Magpie-Align, or Magpie-Align for refusal); residual-stream activations h_{theta_G0}(x_r) of the initially safeguarded model",
      "output": "g_retain = grad_{theta_{i-1}}( L_LM(theta_{i-1}, x_r) + ||h_{theta_{i-1}}(x_r) - h_{theta_G0}(x_r)||_2^2 ) in R^d",
      "params": {"relative_weight_of_two_terms": "论文未说明 (Algorithm 1 adds them directly)", "batch_size": "论文未说明"},
      "source": "Section 4.2 Equation 2; Algorithm 1 lines 9-10"
    },
    {
      "step": "weighted_outer_update",
      "operator": "weighted_gradient_combine",
      "input": "g_TR, g_retain, learning rate eta, weights lambda_TR and lambda_retain",
      "output": "theta_i = theta_{i-1} - eta * (lambda_TR * g_TR + lambda_retain * g_retain)",
      "params": {"eta": "2e-5 weaponization; 6e-5 refusal", "lambda_TR": "4.0 bio/cyber, 3.0 chem; 0.1 refusal", "lambda_retain": 1.0, "outer_optimizer": "ScheduleFree AdamW", "N": "750 weaponization; 100 refusal"},
      "source": "Section 4.2 Equation 1; Algorithm 1 line 12; Section 5.1; Section 5.2"
    },
    {
      "step": "optional_benign_sft_refusal_only",
      "operator": "benign_sft_finetune",
      "input": "theta_G after the outer loop; Magpie-Align data",
      "output": "final TAR refusal model reported in Table 2",
      "params": {"steps": 100, "dataset": "Magpie-Align", "lr": "论文未说明", "batch_size": "论文未说明"},
      "source": "Appendix E.2"
    }
  ],
  "sampling": [
    {"what": "rounds", "how": "outer tamper-resistance steps N, each simulating K-step SFT attacks", "size": "N = 750 (weaponization, Section 5.1); N = 100 (refusal, Section 5.2)"},
    {"what": "rounds", "how": "inner-loop SFT trajectory length K per outer step, compared over {8,16,32,64}", "size": "K = 64 (Appendix C.1, Appendix D.3 Figure 7)"},
    {"what": "coordinates", "how": "trajectory coordinate reuse (one rollout yields K non-independent attack samples) and coordinate sub-sampling along the trajectory", "size": "K = 64; sub-sample every 4 adversary optimization steps (Appendix C.4)"},
    {"what": "probes", "how": "one held-out minibatch x_TR sampled per outer step from the held-out split of D_TR and reused for every inner-loop L_TR term", "size": "1 minibatch per outer step; batch size 论文未说明 (Appendix C.4, Appendix E.2)"},
    {"what": "samples", "how": "80-20 split of each forget set into adversary data (for A_train attacks) and held-out data (for computing tamper-resistance losses)", "size": "80-20 per domain (Appendix E.2)"},
    {"what": "samples", "how": "reference/probe dataset sizes for the weaponization setting", "size": "Pile-bio Forget 7,558; Camel-bio Forget 54,258; OOD Forget 598,933; Cyber Forget >18k; Pile-bio Retain 42,426 (Appendix E.1)"},
    {"what": "clients", "how": "论文未使用 (centralized method, no clients)", "size": ""},
    {"what": "layers", "how": "论文未使用抽样; Random Mapping is defined on the residual stream at every layer", "size": ""}
  ],
  "resources": [
    "base LLM: Llama-3-8B-Instruct (Sections 5.1 and 5.2)",
    "forget/safety proxy data: Pile-bio Forget (7,558), Camel-bio Forget (54,258), OOD Forget (598,933), private chemical-security forget set, CTFtime cybersecurity writeups (>18k) (Appendix E.1)",
    "retain/capability proxy data: Pile-bio Retain (42,426) mixed with Magpie-Align instruction-tuning data (Appendix E.1, E.2)",
    "refusal setting: Anthropic-HH-RLHF rejected completions for train-time attacks, plus a modified split whose rejected completions are replaced with refusals for the DPO loss; base weights theta used as DPO reference model with precomputed reference log-probs (Appendix E.2)",
    "initial safeguarded model theta_G0 whose residual-stream activations serve as the Equation 2 anchor (Section 4.2)",
    "train-time adversary set A_train: 6 adversaries per weaponization domain, 3 for refusal (Table 7, Table 8)",
    "compute: 8 x NVIDIA 80GB A100, FSDP, DeepSpeed ZeRO Stage 3 (Appendix C.5)",
    "evaluation resources: WMDP (3,668 questions), MMLU (57 tasks), HarmBench, MT-Bench, Toxic-DPO v0.2 (541 harmful chats), 26/24 weaponization test adversaries (Table 9), 5 refusal test adversaries (Table 10)"
  ],
  "actions": ["transform_gradients"],
  "dominant_cost": "N outer steps, each requiring a K = 64-step simulated SFT attack rollout (forward+backward per step) plus one L_TR forward/backward per sub-sampled trajectory coordinate (about every 4th step) and one retain-term forward/backward; the paper calls simulating K attacks per outer update 'prohibitively expensive' (Appendix C.4) and notes K computation graphs are infeasible in memory (Appendix C.5), but reports no wall-clock, GPU-hour or memory numbers (论文未说明). 分析：cost scales roughly with N x K x model size x sequence length.",
  "underspecified": [
    "outer-loop batch size for D_TR and D_retain is never given (only the inner adversary batch size 64)",
    "relative weighting of the two terms inside Equation 2 (L_LM vs the l2 activation anchor) is not given; Algorithm 1 line 10 simply adds them",
    "the anchor reference is written h_theta in Algorithm 1 but h_{theta_G0} in Equation 2 and Section 4.2; whether it is the base model or the initially safeguarded model must be decided by the implementer",
    "the exact definition of the entropy loss is unspecified: which token positions, which distribution, and how it is reduced over the sequence",
    "gradient normalization after coordinate sub-sampling is unspecified (Algorithm 1 shows 1/K, but only a subset of coordinates receives L_TR); the stride 4 is only given as an example",
    "Random Mapping (Appendix C.2) gives no optimizer, learning rate, step count or batch size, and no dimensionality/alignment details for rand_hashed vectors",
    "the semantics of the beta(6.0, 3.0) R->F switching point (fraction of the 64 steps vs absolute step count) is unspecified",
    "how Algorithm 1's 'for k = 1 to K' loop relates to the trajectory-coordinate reuse of Appendix C.4 (whether K forwards are still run) is unspecified",
    "for refusal: the DPO beta, the exact construction of chosen/rejected pairs (the [6] rewriting procedure), and any length normalization are unspecified",
    "the specific initial refusal safeguard (RLHF vs DPO, and its data) used to produce the TAR refusal model is unspecified",
    "hyperparameters of the extra 100 benign SFT steps (learning rate, batch size) are unspecified",
    "whether the absolute-value bars in the extracted Equation 3 reflect the paper's intent, given that the prose says the objective maximizes cosine similarity"
  ],
  "quotes": [
    {"supports": "步骤 1 初始安全防护（武器化设置用 Random Mapping）", "text": "As a proxy for scrubbing target representations according to downstream task labels, we propose a weaponization knowledge restriction safeguard termed Random Mapping, which maps hθ(DTR) to random noise as follows:"},
    {"supports": "步骤 2 与步骤 8：每个外层步用同一个 held-out 批次算 L_TR 以降低方差", "text": "Additionally, we reduce variance in the tamper-resistance gradient by computing the tamper-resistance loss at each inner loop step on the same held-out batch, denoted as xTR in Algorithm 1."},
    {"supports": "步骤 3 与步骤 7：把攻击写成扰动并用直线估计器反传", "text": "defining attack(θG) = θ′G = θG + attack′(θG) as a perturbation on top of initial parameters, where backpropagation through attack′ is approximated with a straight-through estimator [5]."},
    {"supports": "步骤 4 轨迹坐标复用（一次 rollout 得到 K 个攻击样本）", "text": "we leverage an efficiency trick: we can reuse the coordinates along steps of a single adversary fine-tuning trajectory of length K to obtain K −1 additional (though non-independent) trajectories of increasing length."},
    {"supports": "步骤 5 沿轨迹子采样坐标", "text": "To further improve runtime efficiency, we do not compute the tamper-resistance loss LTR on all K steps and instead sub-sample coordinates along the trajectory for computing LTR within an adversary batch, for example every 4 adversary optimization steps."},
    {"supports": "步骤 6a 武器化设置把 L_TR 取为被最大化的熵", "text": "We choose the tamper-resistance loss LTR as an entropy loss to be maximized during the adversary's cross-entropy fine-tuning trajectory, since maximizing entropy would impede the adversary's cross entropy loss from decreasing during fine-tuning."},
    {"supports": "步骤 6b 拒绝设置把 L_TR 取为沿攻击轨迹的 DPO 损失", "text": "the sampled attack performs SFT on rejected completions, and the tamper-resistance loss LTR is a DPO loss computed on the pair chosen and rejected completions on parameter coordinates along the attack trajectory."},
    {"supports": "步骤 9 retain 项把表示锚回初始防护模型", "text": "Empirically, we find that pushing retain-set residual stream representations to be close to the base model θG0 via the ℓ2-norm loss in Equation 2 maintains a high capabilities_metric(θG)."}
  ]
}
```
