# tamirisa2024tar：Tamper-Resistant Safeguards for Open-Weight LLMs

## 1. 基本信息

- **场景**：集中式大模型训练（centralized LLM training）加开放权重发布（open-weight release）。论文不是传统联邦学习，也不是联邦大模型微调，更没有客户端、服务器聚合或参数高效微调供应链的角色划分；全流程由单一模型开发者（defender）在自有算力和自有数据上完成，发布后的攻击者是拿到权重的任意第三方。论文全文没有出现联邦学习、客户端采样、参与率或聚合规则的内容。
- **训练阶段**：发布前的模型安全加固阶段，具体分两段——（1）模型初始安全防护（model safeguarding），（2）抗篡改训练（tamper-resistance training，第 4 章）。被防御的篡改攻击（tampering attack）发生在模型发布之后的下游监督微调（supervised fine-tuning，SFT）阶段（第 3.1 节）。
- **论文类型**：防御（defense）。论文提出防御方法 TAR（Tampering Attack Resistance），并附带大规模红队评测（red teaming）来度量防御强度，但它本身不做检测，也不提供基准或平台。
- **模型与数据规模**：主模型为 Llama-3-8B-Instruct（第 5.1、5.2 节）；对比基线还使用 Zephyr-7B（R2D2）和 Llama-2-7B（RepNoise）。评测数据包括 WMDP（3,668 道多选题，覆盖生物安全、化学安全、网络安全，第 3.2 节）、MMLU（57 个任务，第 3.2 节）、HarmBench、MT-Bench、Anthropic-HH-RLHF、Magpie-Align、Toxic-DPO v0.2（541 条用户—助手有害对话，附录 F.2）。训练使用 8 张 NVIDIA 80GB A100（附录 C.5）。
- **与 LoRA/PEFT 的关系**：论文只在红队攻击侧使用 LoRA。测试时攻击者中有两个 PEFT（parameter-efficient fine-tuning）配置，通过 LoRA 适配器微调，配置为秩（rank）16、alpha 32、dropout 0.05，目标模块为 up_proj、down_proj、gate_proj、q_proj、k_proj、v_proj、o_proj（附录 F.1）。防御方法本身不使用 LoRA，TAR 训练是 Llama-3-8B 的全参数训练。

## 2. 威胁模型

**攻击者是谁。** 论文把攻击者定义为获得开放权重的任意行为者，不使用"恶意客户端""恶意服务器""数据提供方"或"适配器发布者"这类角色。威胁模型原文只说防御者发布带防护 G 的权重 θG，攻击者拥有对 θG 的不受限访问（第 3.1 节）。因此按本题的角色枚举，最接近的是外部攻击者（external）。

**占比或数量。** 论文没有给出"恶意比例"这类联邦式占比。可报告的量化是红队配置数：生物安全领域 26 个测试时攻击者，化学安全与网络安全各 24 个（第 5.3 节、附录 F.1，对应表 9）；训练时每个武器化领域采样 6 个攻击者配置（附录 E.2，表 7），有害请求拒答领域采样 3 个训练时攻击者配置加 5 个测试时攻击者（表 8、表 10）。

**能力（能改什么）。** 攻击者拥有完整权重，可以直接修改全部参数（全参数微调），也可以只训练 LoRA 适配器；可以自选优化器（AdamW、Adadelta、带动量的随机梯度下降、Schedule Free AdamW）、优化步数（默认 500 步）、学习率（2×10⁻⁶、2×10⁻⁵、4×10⁻⁵）、学习率调度（SGDR、30 步线性预热）、批大小（32、64、128）以及微调数据分布（附录 F.1，表 9）。攻击者还可以先在一个数据分布上微调再切换到另一个分布（R→F 攻击者）。

**知识（知道什么）。** 论文明确说攻击者对 θG 有不受限访问（第 3.1 节），因此可以看到全部权重。论文**未说明**攻击者是否知道 TAR 的训练细节（训练时攻击者集合 Atrain 的构成、内层步数 K、损失权重 λ 等）；红队评测只保证一部分攻击者、数据分布与超参在训练时未出现（"including many that are unseen at training time"，第 3.3 节；附录 F.1 提到 OOD-Forget 数据集在抗篡改训练中未见）。

**目标。** 攻击者的目标是在合理算力限制下得到使 safety_metric 最小化的模型 θ′G（第 3.1 节）。在两个具体设定中分别是：恢复被限制的武器化知识（生物安全、化学安全、网络安全），以及让模型服从有害请求（越狱）。论文**未**把后门植入（backdoor）、隐私窃取（privacy）或无目标破坏作为攻击目标，也**未**研究输入空间越狱攻击者（第 3.1 节明确说只考虑微调攻击者）。

**防御者是谁、能看到什么、信任什么。** 防御者是模型开发者，在发布前持有基础模型 θ，能控制初始防护步骤和抗篡改训练步骤，能看到完整权重、逐层残差流隐藏状态、输出概率分布、自己构造的代理数据集（DTR、Dretain）以及自己模拟的攻击轨迹，最后发布 θG（第 3.1、4 章、算法 1）。论文**未说明**防御者在发布后还能看到什么，也**未**讨论多方之间的信任假设，因为整个流程是单方集中式训练，不存在需要信任其他参与方的问题。

## 3. 攻击入口与流程位置

按论文的威胁模型，攻击内容进入流程的位置是"**模型发布之后、攻击者本地的微调过程**"，即权重下发之后在攻击者侧发生的本地训练。具体步骤是：

1. **模型发布**：防御者发布带防护 G 的 θG，攻击者获得完整权重（第 3.1 节）。
2. **本地训练过程**：攻击者对 θG 执行 SFT，默认 500 步（第 3.1 节、第 5.3 节），可选择优化器、学习率、调度、批大小和数据集（附录 F.1）。论文特别指出攻击者不一定会花接近预训练的算力（第 3.1 节）。
3. **参数高效微调路径**：攻击者也可以只用 LoRA 适配器而不是全参数微调（表 9 中 Adv 25/26 与 Adv 23/24 的"FT Paradigm"列为 PEFT）。
4. **分布切换路径**：R→F 攻击者先在一个分布上微调、再切换到另一个分布。训练时 R→F 是"先在 Retain 集上 SFT、再在 Forget 集上 SFT"，切换点从 beta 分布 β(6.0, 3.0) 采样（附录 E.2）；测试时 R→F 反过来，先做 40% 步数的 Forget 集 SFT，再做 60% 步数的 Retain 集 SFT（附录 F.1）。
5. **评估**：在 WMDP（遗忘集准确率）与 MMLU（保留集准确率）上评估武器化设定，在 HarmBench（攻击成功率）与 MT-Bench 上评估拒答设定（第 3.2、5.1、5.2 节）。

论文的攻击**不**位于：本地数据准备阶段的训练数据投毒（攻击者使用自己的遗忘集数据，不是污染防御者的训练数据）、更新上传前的缩放或投影、服务器聚合、聚合后的全局模型处理。这些环节在集中式场景中不存在。

防御侧对应的入口是**发布前的开发者训练过程**：初始防护在基础模型上训练（第 4.1 节），抗篡改训练在模拟攻击轨迹上做元学习式更新（第 4.2 节、算法 1），最终产出 θG = θN。

## 4. 方法原理

TAR 的核心思想是把"抵御权重篡改"转成一个对抗训练加元学习的问题：防御者不追求在某个分布上最优，而是追求一个**在多个模拟微调攻击之后仍然远离攻击者最优解**的初始化（第 4.2 节）。

**第一阶段：模型初始防护（第 4.1 节、附录 C.2）。** 先给基础模型 θ 装上一个普通防护 G。武器化知识限制使用 Random Mapping（式 3）：设 hθ(x) 是输入序列 x 在解码器后每一层残差流上的激活，rand_hashed(x) 是按输入 token 哈希选出的固定高斯随机向量，目标是最大化两者的余弦相似度，同时叠加 Dretain 上的语言建模交叉熵。直观上就是把遗忘集 token 的表示"重映射"到噪声向量上。拒答设定则用 RLHF 或 DPO（第 4.1 节）。论文强调初始防护本身不需要抗篡改，但缺少它会让攻击前的遗忘集准确率明显偏高（表 5："Excl. Initial Safeguard" 的攻击前遗忘集准确率为 47.3，而 TAR 为 28.1）。

**第二阶段：抗篡改训练（第 4.2 节、算法 1）。** 内层用采样的攻击者 attack ∼ Atrain 对当前参数做若干步微调，得到 attack(θ)；外层优化防御者目标：

- 式 1：最小化 λTR 乘以"在 Atrain 上对 LTR(attack(θ); DTR) 的期望"，加上 λretain 乘以 Lretain(θ; Dretain)。
- 式 2：Lretain(θ; Dretain) 等于 Dretain 上的语言建模交叉熵加上"当前模型残差流隐藏状态与参考模型 θG0 隐藏状态之间的平方 ℓ2 距离"。

由于穿过攻击做反向传播不可行，论文把 attack(θG) 写成 θG + attack′(θG) 的形式，用 straight-through estimator 近似对 attack′ 的反传（第 4.2 节），并指出这与一阶 MAML 的设定和近似相符。论文同时强调与传统元学习的差别：传统元学习要找一个在多个测试分布上接近最优的初始化，而这里要找的是在多个攻击者测试分布上**远离**最优的初始化；并且外层使用的 LTR 与攻击者内层的微调损失不同（第 4.2 节）。

**LTR 的选择（第 4.2 节、附录 C.3）。** 武器化知识限制用负熵损失：让模型在遗忘集 token 上的输出分布保持高熵，从而"压平"攻击者的交叉熵损失轨迹，而不是只抬高它在第 0 步的截距。图 3 对比了负交叉熵（左侧，攻击者只在轨迹早期受影响，之后迅速恢复）与负熵（右侧，最终所有内层步都被压制）。拒答设定用 DPO 损失：采样攻击在有害（被拒绝）完成上做 SFT，而 LTR 在攻击轨迹的参数坐标上对"被选中的拒绝完成"与"被拒绝的有害完成"计算 DPO 损失，使模型在遭受有害微调后仍然偏好拒绝回答（附录 C.3）。

**高效采样攻击（附录 C.4）。** 不跑 K 条独立轨迹，而是复用单条长度 K 的攻击轨迹上所有参数坐标，得到 K−1 条长度递增但非独立的轨迹，把它们放进同一批计算抗篡改损失；同时只对轨迹上的部分坐标计算 LTR（例如每隔 4 个攻击步），并在每个内层步的同一 held-out 批次 xTR 上计算 LTR 以降低梯度方差。

**论文自认为关键的三个因素**：抗篡改损失的选择、训练时攻击者的选择、以及两阶段（先初始防护再对抗训练）的结构（第 1 章、第 4 章）。

## 5. 检测或防御所需的数据

论文不做检测，因此下面列的是**训练 TAR 防御所需要的输入**。需要先说明：本论文是集中式训练，没有客户端。下表中的"在哪里采集"字段用防护库的枚举值表示时，`client_pre_train` 对应"模型开发者训练开始前"，`client_step` 对应"开发者训练过程中的某一步"，`evaluation` 对应"发布后红队评估"。论文**未说明**任何服务器收到更新、聚合或聚合后处理环节的数据形态，因为这些环节不存在。

1. **安全代理数据集 DTR**。是什么：每个武器化领域对应的遗忘集 held-out 划分（附录 E.2），武器化设定中它与攻击者使用的 80% 划分严格分离；拒答设定中 DTR 是 Anthropic-HH-RLHF 的修改版测试划分（把被拒绝的完成替换为拒绝回答，附录 E.2）。在哪里采集：开发者训练前准备、训练步中采样。粒度：逐样本（用 minibatch 计算，附录 E.2）。是否需要跨轮历史：否。是否需要干净参考数据：需要与攻击者数据隔离的 held-out 划分，但不需要外部"干净根数据集"。是否需要额外前向或反向：需要额外前向（计算 LTR）。是否需要其他客户端数据：否，论文没有客户端概念。
2. **能力保持代理数据集 Dretain**。是什么：Pile-bio Retain 集与 Magpie-Align 指令微调数据的混合（附录 E.2、C.1）。在哪里采集：开发者训练前准备、训练步中采样。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考：否。额外计算：语言建模交叉熵是常规训练计算，额外的部分是式 2 的隐藏状态对齐。其他客户端数据：否。
3. **逐层残差流隐藏状态 hθ(x)**。是什么：模型在每一层、每个 token 位置的残差流激活，即式 2 中与参考模型隐藏状态比较的量，也是式 3 中与哈希随机向量做余弦相似度的量（第 4.2 节、附录 C.2）。在哪里采集：开发者训练每一步。粒度：逐层，且逐 token、逐样本。是否需要跨轮历史：需要保留参考模型 θG0（或基础模型 θ）的隐藏状态作为参照。是否需要干净参考数据：需要参考模型的激活快照。额外计算：需要额外前向。其他客户端数据：否。
4. **遗忘集上的输出概率分布与熵**。是什么：模型在 DTR 上每个 token 位置的输出分布，用于计算负熵形式的 LTR（第 4.2 节、附录 C.3、附录 G.1）。在哪里采集：开发者训练的每个内层步，即攻击轨迹的每个坐标。粒度：逐批（论文用 minibatch）。跨轮历史：否。干净参考：否。额外计算：每个内层步一次额外前向。其他客户端数据：否。
5. **DPO 偏好对与参考模型 log 概率**。是什么：有害提示下的"被选中的拒绝完成"与"被拒绝的有害完成"配对（附录 E.2），以及基座模型 θ 在完整 Anthropic-HH-RLHF 上预计算的参考 DPO log 概率。在哪里采集：训练前预计算参考概率，训练步中在攻击轨迹的参数坐标上计算 DPO 损失。粒度：逐样本。跨轮历史：否。干净参考数据：是，需要保持基座模型权重作为 DPO 参考模型。额外计算：是。其他客户端数据：否。
6. **模拟攻击轨迹上的参数坐标与梯度**。是什么：一条长度 K=64 的攻击轨迹上的全部参数坐标 θ′，以及穿过攻击的 straight-through 梯度累积项 gTR（算法 1、附录 C.4）。在哪里采集：开发者训练的每个外层步内，由防御者自己模拟。粒度：模型级（参数坐标），逐内层步。跨轮历史：是，需要同一次外层步内保留轨迹历史；此外外层步之间需要 θi−1 以及移存到 CPU 的外层优化器状态（附录 C.5）。干净参考数据：否。额外计算：是，且这是主要开销来源。其他客户端数据：否。
7. **评测侧观测量**。是什么：发布后模型在 WMDP 各子集上的准确率、MMLU 保留集准确率、HarmBench 攻击成功率、MT-Bench 分数。在哪里采集：评估时。粒度：模型级。其他字段：不适用于防御训练。

**攻击会在哪些可观测量上留下痕迹（论文报告）。** 攻击者微调后，遗忘集上的交叉熵损失会下降、输出熵会从接近 log(vocab_size) 的高位回落（图 6；附录 G.1 给出 |V| = 128256 时熵上界约 11.76），DPO 意义下"拒绝完成优于有害完成"的胜率会下降（图 8），WMDP 遗忘集准确率会回升（表 1、图 4）。论文报告 TAR 在这些量上都能维持住：例如图 6 中生物安全攻击在 1,000 步内交叉熵损失不降到 7 以下，而 LLMU 防护在 20 步内就落入恢复区间。

**论文声称能绕过哪些检测。** 论文不研究检测，因此没有"绕过检测"的结论。可报告的相关表述是：TAR 对参数高效微调（PEFT）攻击和部分分布外学习率攻击的鲁棒性有波动（第 5.3 节）。

## 6. 干预动作

TAR 的动作是**训练时修复模型本身**：按照算法 1，在发布前用式 1 的目标更新参数 N 次（武器化设定 N=750，拒答设定 N=100），得到 θG = θN 并发布（算法 1、第 5.1、5.2 节）。这一动作发生在流程中的"开发者侧训练"位置，即模型发布之前，属于对模型权重的硬化或修复，而不是对某个客户端或某条样本的处理。

论文**未**使用以下动作：剔除客户端、重新加权、梯度裁剪、加噪、过滤样本、回滚或仅报告。论文也没有部署任何发布后的运行时干预机制（例如权重校验、水印、在线探测或异常监测）。

唯一接近"事后修复"的机制是附录 D.2 的定向修补（targeted patching）：把曾经攻破早期版本的"Retain-set SFT followed by Biosecurity SFT"攻击者加入 Atrain 后重新训练，报告全部 26 个攻击者上的平均后攻击遗忘集准确率从 44.9 改善到 35.2，针对该攻击者本身从 58.7 改善到 29.7（表 4）。这仍然属于"重训模型"而不是运行时干预。

## 7. 实验设置与主要结果

**武器化知识限制（第 5.1 节、附录 E、附录 F.1）。** 模型为 Llama-3-8B-Instruct，先做 Random Mapping 初始防护。外层步数 N=750，外层优化器为 ScheduleFree AdamW，学习率 2×10⁻⁵；λTR 在生物安全和网络安全为 4.0、化学安全为 3.0，λretain 统一为 1.0。训练时攻击者为每个领域 6 个配置，内层步数 K=64，AdamW，无预热，批大小 64，全参数，学习率取自 {2×10⁻⁵, 4×10⁻⁵}（表 7）。测试时为 26 个（生物安全）或 24 个（化学、网络）攻击者配置，默认 500 步（表 9），每个攻击配置用 3 个随机种子重复取平均（附录 F.1、C.1）。

关键结果（表 1，均为百分数）：TAR 在生物安全上的攻击前保留集 54.7、攻击前遗忘集 28.1、后攻击遗忘集 35.2；化学安全为 56.5、28.4、27.1；网络安全为 60.7、23.6、28.6。对照"No Defense"为 67.3、70.5、70.5（生物安全），68.2、47.8、47.8（化学安全），68.2、46.4、46.4（网络安全）；随机猜测为 25.0。其他基线在生物安全上的后攻击遗忘集准确率为 Max Entropy 65.8、Min Posterior 66.0、LLMU 61.3、RMU 64.9，说明它们基本被攻破。论文报告 TAR 平均降低保留集准确率 10.6%（第 5.1 节，对应 No Defense 三个领域平均 67.9 与 TAR 平均 57.3 之差）。图 4 按攻击者逐个给出结果，论文称 TAR 对其中绝大多数攻击者的后攻击遗忘集准确率接近随机水平。图 2 把 TAR 与 12 个基线防护在"MMLU 能力—抗篡改性"平面上比较。

**有害请求拒答（第 5.2 节、附录 F.2）。** 模型同为 Llama-3-8B-Instruct，外层步数 N=100，外层优化器 ScheduleFree AdamW，学习率 6×10⁻⁵，λTR=0.1，λretain=1.0；训练时攻击者为 3 个配置，在 Anthropic-HH-RLHF 的被拒绝完成上做 K=64 步 SFT（表 8）；测试时 5 个攻击者在 Toxic-DPO v0.2（541 条对话）上做 10 个 epoch 的 SFT（表 10）。关键结果（表 2）：后攻击平均 HarmBench 攻击成功率为 TAR 63.9，Refusal Trained 72.5，R2D2 78.3，RepNoise 74.5，Representation Rerouting 84.8；攻击前 MT-Bench 分别为 6.3、8.1、6.0、6.2、8.0。论文正文另有一处写"our TAR method only rises to 61.7"（第 5.2 节），与表 2 的 63.9 不一致，此处照实并列。表 11 补充给出攻击前 HarmBench ASR：TAR 31.4、Refusal Trained 14.7、R2D2 25.0、RepNoise 18.8、RR 1.4。论文自述 MT-Bench 下降 1.7（第 5.2 节，8.0 到 6.3）。

**消融与附加实验。** 表 5：去掉对抗训练（Excl. Adv. Training）的后攻击遗忘集准确率为 61.6、攻击前遗忘集 27.3；去掉初始防护（Excl. Initial Safeguard）为 35.5 和 47.3；完整 TAR 为 35.2 和 28.1。表 6：λTR 从 1.0 增到 4.0 使后攻击遗忘集从 39.9 降到 35.2，保留集从 62.5 降到 54.7。表 3：在经济学数据上良性微调后，TAR-Bio 的 MMLU 经济学准确率从 59.7 升到 64.7，遗忘集从 28.1 到 30.1；论文称经济学准确率提升 5.0 个百分点。表 12：把 MLAC 与 SOPHON 扩展到自回归模型（MLAC-AR、SOPHON-AR）后，前者能力与鲁棒性都不稳定，后者无法收敛出可用模型。附录 C.1 报告发布后发现的 retain 数据集污染问题，以及修正后 1,000 步微调时鲁棒性会随数据加载器打乱顺序变化（图 5），而 500 步内基本一致。图 7 显示内层长度 K 从 8 增到 64 会提高抗篡改性。

**数据是否非独立同分布。** 不适用：论文是集中式训练，没有联邦意义上的客户端数据异构设置，也没有报告任何非独立同分布（non-IID）划分实验。附录 C.4 出现"effectively sampling attack from Atrain non-IID"一句，指的是在同一轨迹上复用坐标导致攻击样本非独立，不是数据异构。

**客户端数与参与率。** 论文未涉及（没有联邦客户端）。可报告的规模量是 8 张 A100（附录 C.5）。

## 8. 开销

论文在附录 C.5 报告了实现与资源需求：在 Llama-3-8B-Instruct 上用 8 张 NVIDIA 80GB A100 训练，使用 FSDP 与 DeepSpeed 的 ZeRO Stage 3（对优化器状态、梯度和参数做分片）。工程上的额外说明包括：内层模拟攻击若使用带状态的优化器，需要每个外层迭代新建优化器，因此外层 ScheduleFree AdamW 的优化器状态被移到 CPU；为避免同时保留 K 个计算图，抗篡改梯度被累积到单独的数据结构 gTR，论文称这一累积和应用可以只在分片梯度上完成，不需要额外的 all-gather 和 reduce-scatter 通信。

论文把逐条运行 K 条独立轨迹描述为"prohibitively expensive"（附录 C.4），并给出复用单条轨迹坐标的效率技巧与每 4 步抽样一次 LTR 的做法。附录 A 自述扩展到更大模型存在需要优化才能降低的计算挑战。

论文**未报告**：墙钟时间、FLOPs、显存占用数值、单步耗时、与基线方法的开销对比。由于是集中式训练，论文也**未报告**任何通信开销（联邦场景下才会出现的开销）。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文有依据的部分）。**

- 攻击者只做有算力上限的监督微调式权重篡改，不做输入空间越狱；论文明确把 jailbreaking 攻击者排除在威胁模型之外（第 3.1、5.3 节）。
- 攻击者不会花接近预训练的算力，否则可以自己训练无防护模型（第 3.1 节）。
- 防御者在发布前完全控制训练流程、代理数据集和训练时攻击者集合 Atrain（第 3.1、4 章、算法 1）。
- 测试时攻击者的数据分布与超参必须被训练时采样的攻击者分布覆盖。第 5.3 节直接把 PEFT 和分布外学习率攻击下的鲁棒性波动归因于"the adversary distributions sampled during TAR training"；附录 D.2 说明要防住某个攻击者，需要把它加入 Atrain 重训。
- 存在足够好的 held-out 遗忘数据用于计算 LTR。附录 F.1 说明化学安全与网络安全之所以少了分布外攻击者，是因为拿不到同等质量的 held-out 数据集；附录 E.2 还说明遵循 Nichol 等人的建议用 held-out minibatch 而不是循环单一样本。
- 能力保持依赖"把 retain 集上的残差流表示拉回参考模型"这一做法（式 2），论文称经验上这能维持高 capabilities_metric。
- 有足够算力完成内层攻击模拟（附录 C.5 的 8×A100 配置）。
- 防御者可以在发布后通过重训修补漏洞，但**不能**撤回已发布的权重（附录 A）。

**论文自述的局限。**

- 只覆盖监督微调攻击，"the broader spectrum of open-weight tampering techniques"需要未来红队研究（附录 A）。
- 扩展到更大模型有计算挑战（附录 A）。
- 在 TAR 维持低后攻击遗忘集准确率的情况下，后攻击保留集准确率也低；良性用户若把遗忘集数据混入自己的微调数据，微调效果会变差，这可能让方法难以实用（附录 A）。
- 一旦开放权重发布就无法"取消发布"，被攻破的防护会永久脆弱；抗篡改只能作为更广泛攻防平衡工作的补充（附录 A）。
- PEFT 与部分分布外学习率攻击下鲁棒性有波动（第 5.3 节）。
- 拒答设定下 MT-Bench 下降 1.7（第 5.2 节），论文把能力影响的完整评估留给未来工作。
- 附录 C.1 报告发布后的 retain 数据集污染问题曾造成意外的输入空间脆弱性，修正后重新训练才消除；并报告 1,000 步微调时鲁棒性会随数据加载器打乱顺序变化，500 步内保持一致。

**是否评估了自适应攻击者。** 没有系统评估。论文做了大量红队（26/24 个测试时攻击者，包含训练时未见的数据分布与超参，第 3.3 节），并在发现能攻破中间版本的攻击者后把它加入 Atrain 重训（附录 D.2），但论文**未说明**评估过针对 TAR 目标函数本身设计的攻击，也**未说明**攻击者是否知晓 TAR 的训练细节。因此这里记为未评估自适应攻击者。

**迁移到联邦 LoRA 微调时可能失效的假设。**

- 分析：TAR 的核心输入是"攻击轨迹上的中间参数坐标和穿过攻击的梯度"（算法 1、附录 C.4）。在联邦 LoRA 中，服务器通常只能收到客户端上传的适配器增量或更新，拿不到客户端本地的逐步训练轨迹；即使拿到每轮的 LoRA 增量，也只能得到粗粒度（每轮一个坐标）而非每步坐标，内层 K=64 步的攻击模拟无法直接重建。
- 分析：TAR 假设防御者能对全局权重做全参数修改并发布。联邦 LoRA 中基座权重通常冻结并共享，可训练的是低秩增量；式 2 的"残差流对齐参考模型"在这种设定下是否仍能把抗篡改性质写进基座，论文未说明。
- 分析：论文的威胁模型是"发布后的单一攻击者获得完整权重"，联邦 LoRA 的信任边界完全不同——攻击者可能是参与训练的客户端、恶意服务器或适配器发布者，攻击入口也不止本地微调。论文对这些角色与入口一概未涉及。
- 分析：论文的红队结论提示 PEFT 攻击会削弱抗篡改性（第 5.3 节）。在联邦 LoRA 里 LoRA 是合法训练方式而不是攻击方式，这意味着正常训练本身就可能落在论文观察到的鲁棒性薄弱区域。
- 分析：论文的 N=750、K=64、500 步等数字与联邦的轮数、每轮本地步数没有对应关系；论文未说明如何把这些超参映射到联邦训练。
- 分析：论文依赖防御者自己掌握的 DTR 与 Dretain。在联邦里这两类数据要么由服务器持有（可能与客户端分布不匹配），要么需要从客户端采集（引入新的隐私与信任问题），论文未说明任何一种方案。

## 10. 对防护库设计的含义

- 分析：库的采集底座需要在"服务端/发布前训练"这一层提供**逐层隐藏状态钩子**和**参考模型激活快照**，因为 TAR 的两个损失项都直接依赖残差流激活（式 2、式 3）。通用部分是一个能按层、按 token 导出 activation 的钩子加一个模型快照缓存；这篇论文特有之处在于把参考激活的 ℓ2 距离当作能力保持正则项，而不是当作检测特征。
- 分析：库需要提供**训练步级的中间状态视图**，不只是"客户端训练后上传的增量"。TAR 的内层攻击模拟要求在一次外层更新内保留 K 步参数坐标并能对它们分别前向、累积梯度（算法 1、附录 C.4）。通用底座若只定义了"每轮上传"的客户端钩子，无法承载这个插件；这是一个需要新增的、以"轨迹"为单位的数据视图。
- 分析：库需要在服务端插件接口上支持**训练目标改写类插件**（修改损失、修改优化步骤，最终产出新的全局权重），而不是只支持"检测后剔除/重加权/裁剪"这类离散动作。对这篇论文，干预接口只需要 repair_model 一类（重训或修复权重）加模型版本管理，不需要客户端剔除或样本过滤接口。
- 分析：库需要把**代理数据集注册与隔离**当作一等能力：安全代理集 DTR、能力保持集 Dretain、以及训练时攻击者数据集三者必须在采集层被标记并强制划分（论文用 80/20 划分并强调 DTR 是 held-out，附录 E.2）。这属于通用需求，因为几乎所有需要参考数据的防御都要用到；论文特有之处是要求把"攻击者用的数据"与"计算 LTR 用的数据"分开。
- 分析：如果库的目标反过来是**检测**这类篡改，那么这篇论文本身不提供检测器，只能提供候选观测量：发布后模型在安全探针集上的熵或损失轨迹、DPO 胜率、遗忘集准确率回升幅度，以及权重变化本身。这些观测量在论文里是评测指标而非检测输入，是否可迁移需要另行验证。
- 分析：通用需求可以归纳为"多阶段采集钩子加参考快照加代理数据管理加可替换的训练时插件"；这篇论文特有的需求是"内层攻击模拟器加穿过攻击的 straight-through 梯度"。前者可以直接复用，后者在联邦 LoRA 下需要先解决轨迹不可见的问题。

## 11. 原文依据

1. **第 3.1 节（Threat Model）**——支撑第 2 节"攻击者拥有不受限的权重访问、防御对象是权重篡改"与第 3 节的入口判断：
   "We consider a compute-bounded adversary with unrestricted access to θG, enabling attacks that directly modify θG. We refer to these as “tampering attacks.”"
2. **第 3.1 节（Threat Model）**——支撑第 2 节"攻击者目标是最小化 safety_metric"与第 7 节"默认 500 步"：
   "The adversary’s goal is to obtain a model θ′G that minimizes the safety metric given reasonable compute limits, such as fine-tuning for 500 steps."
3. **第 4.2 节（Tamper-Resistance Training）**——支撑第 4 节"LTR 的选择是方法成败关键，负交叉熵会失效"与图 3 的解读：
   "Empirically, we find that the choice of tamper-resistance loss LTR significantly affects this goal. Prior work [16] negates the loss of a fine-tuning adversary, in which the aim is to arbitrarily maximize the adversary’s loss throughout fine-tuning."
4. **第 4.2 节（Tamper-resistance objective）**——支撑第 4 节式 1 的复述与第 5 节 DTR、LTR 的角色：
   "For a given safety_metric, let DTR and LTR respectively be a dataset and loss function such that minimizing LTR(θG, DTR) serves as a proxy objective for maximizing the safety_metric(θG)."
5. **第 4.2 节（式 2 的说明）**——支撑第 5 节第 3 项"逐层残差流隐藏状态是必需输入"与第 4 节式 2 的复述：
   "where hθ(·) returns the residual stream hidden states for model parameters θ and LLM is the standard language modelling cross-entropy loss."
6. **第 4.2 节（Tamper-Resistance Training）**——支撑第 4 节"针对 Atrain 做对抗训练"与第 3 节"防御者在训练时自己模拟攻击"：
   "we train against a set of tampering attacks Atrain, where the defender’s objective is to maximize a proxy safety_metric after applying an adversarial attack attack ∼Atrain to θ."
7. **附录 C.4（Efficiently Sampling Fine-tuning Attacks）**——支撑第 8 节的开销工程技巧与第 10 节"轨迹视图"需求：
   "we can reuse the coordinates along steps of a single adversary fine-tuning trajectory of length K to obtain K −1 additional (though non-independent) trajectories of increasing length."
8. **第 5.3 节（Analysis）**——支撑第 9 节"PEFT 与分布外学习率攻击下鲁棒性有波动"这一自述局限：
   "However, we find our method exhibits varying robustness to parameter-efficient fine-tuning (PEFT) and some out-of-distribution LR attacks, highlighting the current sensitivity of the method to the adversary distributions sampled during TAR training."
9. **附录 F.1（Red Teaming Details）**——支撑第 1 节与第 7 节"LoRA 只作为测试时 PEFT 攻击者出现，秩 16、alpha 32、dropout 0.05"：
   "In cases where the adversary used parameter-efficient fine-tuning (PEFT) via LoRA adapters [18], we used a LoRA config with an attention dimension, or rank, of 16, a LoRA alpha value of 32, a LoRA dropout of 0.05,"
10. **附录 A（Limitations）**——支撑第 9 节"论文自述抗篡改最终仍可能被绕过、发布不可撤回"：
    "While it raises the initial costs for adversaries, it can eventually be circumvented. Once open-weight models are released, they cannot be “unreleased,” leaving any compromised defenses permanently vulnerable."

```json
{
  "key": "tamirisa2024tar",
  "title": "Tamper-Resistant Safeguards for Open-Weight LLMs",
  "year": 2024,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["external"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_training", "model_distribution"],
  "observables": [
    {"what": "逐层残差流隐藏状态 hθ(x)，用于 Random Mapping 的余弦相似度目标与 Lretain 的 ℓ2 对齐", "where": "client_step", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "安全代理数据集 DTR 上逐 token 的输出概率分布与熵（武器化知识限制的 LTR）", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "DPO 偏好对（拒绝完成 对 有害完成）与基座参考模型预计算的 DPO log 概率", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "模拟攻击轨迹上 K=64 步的参数坐标以及穿过攻击的 straight-through 梯度累积", "where": "client_step", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "能力保持代理数据集 Dretain 的样本与语言建模交叉熵", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "发布后评测指标：WMDP 遗忘集准确率、MMLU 保留集准确率、HarmBench 攻击成功率、MT-Bench 分数", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者只做有算力上限的监督微调式权重篡改，不做输入空间越狱",
    "攻击者不会花费接近预训练的算力",
    "防御者在发布前完全控制训练流程、代理数据集与训练时攻击者集合 Atrain",
    "测试时攻击者的数据分布与超参被训练时采样的攻击者分布覆盖",
    "存在足够好的 held-out 遗忘数据与干净参考模型用于计算 LTR 和隐藏状态对齐",
    "具备模拟内层攻击轨迹所需的算力，例如 8 张 80GB A100"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Section 3.1", "supports": "第 2 节与第 3 节：攻击者是拥有不受限权重访问的外部行为者，攻击方式是直接修改权重", "text": "We consider a compute-bounded adversary with unrestricted access to θG, enabling attacks that directly modify θG. We refer to these as “tampering attacks.”"},
    {"section": "Section 3.1", "supports": "第 2 节攻击者目标与第 7 节默认 500 步微调", "text": "The adversary’s goal is to obtain a model θ′G that minimizes the safety metric given reasonable compute limits, such as fine-tuning for 500 steps."},
    {"section": "Section 4.2", "supports": "第 4 节：抗篡改损失的选择是关键，负交叉熵目标只在攻击轨迹早期有效", "text": "Empirically, we find that the choice of tamper-resistance loss LTR significantly affects this goal. Prior work [16] negates the loss of a fine-tuning adversary, in which the aim is to arbitrarily maximize the adversary’s loss throughout fine-tuning."},
    {"section": "Section 4.2", "supports": "第 4 节式 1 的复述与第 5 节 DTR、LTR 作为代理目标数据与损失", "text": "For a given safety_metric, let DTR and LTR respectively be a dataset and loss function such that minimizing LTR(θG, DTR) serves as a proxy objective for maximizing the safety_metric(θG)."},
    {"section": "Section 4.2", "supports": "第 5 节：逐层残差流隐藏状态是式 2 能力保持损失的必需输入", "text": "where hθ(·) returns the residual stream hidden states for model parameters θ and LLM is the standard language modelling cross-entropy loss."},
    {"section": "Section 4.2", "supports": "第 3 节与第 4 节：防御者针对自己模拟的攻击者集合 Atrain 做对抗训练", "text": "we train against a set of tampering attacks Atrain, where the defender’s objective is to maximize a proxy safety_metric after applying an adversarial attack attack ∼Atrain to θ."},
    {"section": "Appendix C.4", "supports": "第 8 节开销与第 10 节所需的攻击轨迹数据视图", "text": "we can reuse the coordinates along steps of a single adversary fine-tuning trajectory of length K to obtain K −1 additional (though non-independent) trajectories of increasing length."},
    {"section": "Section 5.3", "supports": "第 9 节：论文自述 PEFT 与分布外学习率攻击下鲁棒性有波动", "text": "However, we find our method exhibits varying robustness to parameter-efficient fine-tuning (PEFT) and some out-of-distribution LR attacks, highlighting the current sensitivity of the method to the adversary distributions sampled during TAR training."},
    {"section": "Appendix F.1", "supports": "第 1 节与第 7 节：LoRA 仅作为测试时 PEFT 攻击者出现，秩 16、alpha 32、dropout 0.05", "text": "In cases where the adversary used parameter-efficient fine-tuning (PEFT) via LoRA adapters [18], we used a LoRA config with an attention dimension, or rank, of 16, a LoRA alpha value of 32, a LoRA dropout of 0.05,"},
    {"section": "Appendix A", "supports": "第 9 节：论文自述抗篡改最终仍可能被绕过，且开放权重发布不可撤回", "text": "While it raises the initial costs for adversaries, it can eventually be circumvented. Once open-weight models are released, they cannot be “unreleased,” leaving any compromised defenses permanently vulnerable."}
  ]
}
```
