# huang2024booster：Booster（有害扰动衰减，Harmful Perturbation Attenuation）

## 1. 方法一句话
输入是服务提供方持有的对齐数据集（alignment dataset，有害提示—安全回答对）与有害数据集（harmful dataset，有害提示—有害回答对），以及一个已经过安全性对齐的基座大语言模型（LLM）权重 w；方法在对齐阶段（alignment stage）用迭代梯度法（Algorithm 1）把 w 训练成一个"接种过的"新检查点 w̃，输出不是对样本或客户端的判定，而是一个新的对齐模型；该模型随后作为"微调即服务"（fine-tuning-as-a-service）的基础模型被使用，使其在后续含 p 比例有害数据的用户数据上微调时，有害损失（harmful loss）的下降速率被削弱，从而降低微调后模型的有害分数（Harmful Score, HS），同时保持下游任务微调精度（Finetune Accuracy, FA）。

## 2. 运行位置
论文的场景是集中式的微调即服务：用户上传数据，服务提供方在自己的服务器上用这些数据微调已对齐的基础模型（Section 3.1），全文没有联邦学习（federated learning）的客户端、轮次或聚合概念。Booster 是**对齐阶段（alignment stage）**方案，优化的是 Section 1 图 1 中的 Stage ①，发生在任何用户微调请求到来之前，属于**训练之外（outside_training）**；它的产物（对齐后的检查点）在"服务器下发前"生效，之后所有微调请求共享同一个基础模型。

分析：把 Booster 放进联邦流程映射时，它就是"服务器在训练之外离线跑一次的一次性对齐训练"，不分布在客户端，也不参与聚合；联邦流程中与其最接近的挂钩点是服务器把基础模型下发之前。论文只在附录 H 把联邦场景列为未来方向（"it is interesting to extend the proposed Booster idea to federated instruction fine-tuning context"），没有给出任何联邦版本算法。是否需要客户端与服务器之间额外往返：不需要。训练中唯一"多出来"的交互发生在单机内部——每个优化步要在扰动后的权重上再做一次前向/反向，不涉及跨节点通信。此外 Appendix C 明确：Booster 对齐完成后，后续微调阶段就是普通 SFT，不需要改动微调流程。

## 3. 算子流水线
以下按执行顺序列出 Algorithm 1 的一步，外层是第 1 行的 `for step t ∈ T` 循环。所有梯度都只对可训练参数求（实验中为 LoRA 适配器，rank 32、alpha 4，Section 5.1）。

**步骤 1：采样对齐数据批次**
- 输入：对齐数据集（约 5000 条有害提示—安全回答对，Section 5.1、Appendix B）。
- 计算：采样一个批次 (x_t, y_t)，batch size 为 10（Section 5.1、Appendix B）。采样方式（是否放回、是否打乱、随机种子）论文未说明。
- 输出：对齐 batch，10 条样本的 token 序列与标签。
- 出处：Algorithm 1 第 2 行；Section 5.1；Appendix B。

**步骤 2：采样有害数据批次**
- 输入：有害数据集（约 5000 条有害提示—有害回答对，Section 5.1）
- 计算：采样一个批次 (x′_t, y′_t)，batch size 同为 10。
- 输出：有害 batch；关键细节是该 batch 在第 5、6 行被复用两次（Algorithm 1 第 3、5、6 行）。
- 出处：Algorithm 1 第 3 行；Section 5.1；Table 8。

**步骤 3（可选变体 Vaccine+Booster 才需要）：搜索嵌入扰动 ϵ\***
- 输入：对齐 batch (x_t, y_t)，当前权重 w_t。
- 计算：ϵ\* = ρ · ∇_e f(w) / ‖∇_e f(w)‖，其中 ∇_e 表示对 embedding（词嵌入）求梯度（Eq. 6）。
- 输出：嵌入扰动 ϵ\*，在前向时加到 embedding 上；纯 Booster 不做这一步。
- 出处：Section 5.5；Appendix F 的式 (6)；Algorithm 2 第 3 行。

**步骤 4：对齐损失梯度**
- 输入：对齐 batch（变体下为加了 ϵ\* 的嵌入）。
- 计算：一次前向 + 反向，得到 ∇̃f(w_t)，即对齐数据经验损失 f(w) 对可训练参数的梯度；Section 4 脚注 2 说明用 SFT 对齐时该损失是交叉熵损失。在 Vaccine+Booster 变体中替换为 ∇̃f̂_{ϵ\*}(w_t)（Algorithm 2 第 4 行）。
- 输出：与可训练参数同形状的梯度张量。
- 出处：Algorithm 1 第 4 行；Section 4 脚注 2；Algorithm 2 第 4 行。

**步骤 5：有害损失梯度（原始权重处）**
- 输入：有害 batch (x′_t, y′_t)，权重 w_t。
- 计算：一次前向 + 反向得到 ∇̃h(w_t)，h(w) 是"有害数据集上的经验损失"（Eq. 1 的说明）。
- 输出：梯度张量 ∇̃h(w_t)。
- 出处：Algorithm 1 第 5 行；式 (1)。

**步骤 6：有害梯度归一化**
- 输入：∇̃h(w_t)。
- 计算：u_t = ∇̃h(w_t) / ‖∇̃h(w_t)‖，把有害梯度整体归一化为单位方向。论文只写了一个范数符号，未说明它是把所有可训练参数展平后的全局 L2 范数还是逐层范数（分析：按式 (1)、式 (3) 的写法，最自然的是全局范数）。
- 输出：单位方向向量 u_t。
- 出处：式 (1)、式 (3) 中的 ∇h(w_t)/‖∇h(w_t)‖；Algorithm 1 第 6 行。

**步骤 7：权重扰动（模拟一步有害微调）**
- 输入：w_t，u_t，内步长 α（默认 0.1）。
- 计算：w′_t = w_t − α·u_t，即沿有害梯度方向走一个归一化步，用来模拟真实微调阶段的一步有害扰动（harmful perturbation）。这只是模拟，不持久化为模型状态。
- 输出：临时权重 w′_t（实现上可用函数式前向或临时替换参数）。
- 出处：式 (1) 第二项、式 (3)；Algorithm 1 第 6 行；Section 4 对"simulates the loss after one normalized step of fine-tuning on harmful samples"的说明。

**步骤 8：扰动点上的有害损失梯度**
- 输入：**同一个**有害 batch (x′_t, y′_t)，权重 w′_t。
- 计算：再做一次前向 + 反向，得到 ∇̃h(w_t − α·∇̃h(w_t)/‖∇̃h(w_t)‖)。论文按式 (2)→式 (3) 把二阶项 ∇(w_t − α·∇h(w_t)/‖∇h(w_t)‖) 近似为常数，因此实现时不要把扰动项本身放进计算图（不要对它反传）。
- 输出：扰动点梯度张量。
- 出处：Algorithm 1 第 6 行；式 (2) 到式 (3) 的近似。

**步骤 9：合成衰减正则梯度**
- 输入：∇̃f(w_t)、∇̃h(w_t)、∇̃h(w′_t)。
- 计算：g̃(w_t) = ∇̃f(w_t) + λ·(∇̃h(w_t) − ∇̃h(w′_t))，其中 λ 是正则项强度（默认 5）。括号内的差就是"有害损失下降量"的梯度估计，最小化它即最小化有害损失的下降速率。
- 输出：合成梯度 g̃(w_t)。
- 出处：式 (3)；Algorithm 1 第 7 行；式 (1) 第二项。

**步骤 10：优化器更新**
- 输入：g̃(w_t)，优化器状态。
- 计算：w_{t+1} = w_t − η·g̃(w_t)（Algorithm 1 第 8 行的 SGD 写法）；论文实验用 AdamW，学习率 5e-4、weight decay 0.1（Section 5.1、Appendix B），所以实际更新由 AdamW 完成。
- 输出：w_{t+1}；循环 T 步后输出最终对齐模型 w̃（Algorithm 1 的 output 行）。
- 出处：Algorithm 1 第 8 行；式 (3)；Section 5.1；Appendix B。

整条流水线只输出一个模型检查点，没有检测器、没有阈值、没有对客户端或样本的取舍。论文还给了两个组合变体：Vaccine+Booster（Section 5.5、Appendix F、Algorithm 2，即在步骤 4 之前插入步骤 3）与 Booster+Lisa（Appendix E）；两者都不改变上面流水线的主体。

## 4. 采样与规模控制
- 样本（samples）：对齐阶段从 BeaverTails 扩充数据中采 5000 条构造对齐数据集，另采 5000 条构造有害数据集（Section 5.1；Appendix B 亦称 "We train 20 epochs for 5000 pieces of alignment data"）；Section 5.1 的默认超参段又写明 "we use 5000 pieces of harmful data in alignment to simulate harmful perturbation"。Table 8 对对齐时可用的有害样本数做了扫描：5/10/20/50/100/500/5000 条，对应 HS 为 65.90/61.00/54.00/5.10/2.30/5.00/4.00，论文结论是 50 条已足够、5 条不足。有害数据集与用户微调数据中混入的有害样本同分布但样本不同（Section 5.1）。
- 批次（samples）：每个优化步采样对齐 batch 与有害 batch 各 10 条（Algorithm 1 第 2–3 行；batch size 10 见 Section 5.1、Appendix B）。
- 客户端（clients）：论文未使用（非联邦设定，Appendix H 才把联邦列为未来方向）。
- 层（layers）：论文未使用层采样；但训练配置用 LoRA 把可训练参数限制在低秩适配器上（rank 32、alpha 4，Section 5.1）。论文未说明归一化与扰动是否只作用于 LoRA 参数。
- 参数坐标（coordinates）：论文未使用（无坐标级抽样、稀疏化或量化）。
- 轮次（rounds）：论文未使用轮次截断；对齐训练 20 个 epoch（Section 5.1），Appendix 的 Table 16 报告到 10000 个对齐步。
- 参考数据/探针（probes）：论文未使用参考数据或探针集；不使用根数据集（root dataset）或干净参考集。

## 5. 超参数
- λ（attenuating regularizer's intensity，衰减正则项强度）：默认 5，出现在 Section 5.1 的默认超参说明。Table 6 扫描 {0, 0.1, 1, 5, 10, 20, 50, 100}，HS 依次为 27.00/25.60/26.00/8.30/6.00/5.20/23.40/77.20，FA 为 92.66/93.35/91.40/93.23/93.58/93.46/93.58/93.58。
- α（inner step size，内步长，用于模拟有害扰动）：默认 0.1，出现在 Section 5.1。Table 7 扫描 {0, 0.01, 0.1, 0.5, 1, 5}，HS 为 31.80/4.70/8.30/72.40/78.00/75.30，FA 为 93.35/92.78/93.23/92.66/89.11/91.97。
- η（学习率，Algorithm 1 输入）：实验取对齐阶段 AdamW 学习率 5e-4、weight decay 0.1（Section 5.1、Appendix B）。
- T（SGD steps，Algorithm 1 输入）：论文未直接给出 T 的数值；只给了 20 epochs、5000 条对齐数据、batch size 10（Section 5.1、Appendix B）。分析：按 20 × 5000/10 推算为 10000 步，与 Table 16 报告到 10000 步一致。
- batch size：10，对齐阶段与微调阶段相同（Section 5.1、Appendix B）。
- 对齐数据量：5000 条（Section 5.1、Appendix B）；有害数据量：默认 5000 条（Section 5.1、Table 8 扫描）。
- 对齐 epoch 数：20（Section 5.1）。
- LoRA 配置：rank 32、alpha 4（Section 5.1）。注意此处的 alpha=4 是 LoRA 的缩放系数，与 Booster 的内步长 α 是两个不同的量。
- Vaccine+Booster 变体的 ρ（perturbation intensity）：Appendix F 未说明取值；Appendix C 只给出 Vaccine 单独实现时 ρ = 5（在 [0.1, 1, 2, 5, 10] 上网格搜索）。Table 9 的 Vaccine+Booster 实验使用 500 条对齐数据（Table 9 标题）。
- 攻击/评测侧超参（不属于 Booster，但复现需要）：有害比例默认 p = 0.1、微调样本数默认 n = 1000（AlpacaEval 为 700）；微调 20 epochs（AlpacaEval 100 epochs）、学习率 1e-5、batch 10（Section 5.1、Appendix B）；HS 用 1000 条 BeaverTails 测试指令；FA 从 SST2/AGNEWS/GSM8K/AlpacaEval 分别采 872/1000/1000/122 条（Section 5.1）。

## 6. 判定与动作
Booster 不是检测器：论文没有阈值、没有对客户端或样本的接受/拒绝判定、没有聚类规则、没有裁剪或加噪幅度，也不跨轮累积任何统计量。唯一的"动作"发生在对齐训练的梯度上：
- 把原本的纯对齐梯度替换为合成梯度 g̃(w_t) = ∇̃f(w_t) + λ·(∇̃h(w_t) − ∇̃h(w′_t))（式 (3)、Algorithm 1 第 7 行），再交给优化器更新。这一步等价于在目标函数里加入正则项 h(w) − h(w − α·∇h(w)/‖∇h(w)‖)（式 (1)），即最小化"有害损失在一步模拟扰动后的下降量"。
- 扰动权重 w′_t = w_t − α·∇̃h(w_t)/‖∇̃h(w_t)‖ 是临时的，不作为最终模型；最终权重始终是 w_{t+1} = w_t − η·g̃(w_t)。
- 强度由两个人工超参控制：λ 控制正则项权重，α 控制模拟扰动的步长；论文明确 λ = 0 或 α = 0 时方法退化为普通 SFT（Table 6、Table 7 的文字说明），且二者都需要仔细调参。
- 效果是"接种"：产出的对齐模型在后续微调时有害损失下降更慢（Section 5.3 与 Table 16），从而在评测中降低 HS。训练完成后该检查点替换原有基础模型，之后所有微调请求共享；微调阶段本身仍是普通 SFT（Appendix C）。论文还报告可与 Lisa 组合（Appendix E）或与 Vaccine 组合（Section 5.5、Appendix F、Algorithm 2），组合不改变判定逻辑。

## 7. 需要的外部资源
- 对齐数据集（有害提示—安全回答对）：5000 条，来自 BeaverTails（Ji et al., 2023）经 Rosati et al. (2024c) 扩充的版本（Section 5.1、Appendix B）。这是必需的防御资源。
- 有害数据集（有害提示—有害回答对）：5000 条，来源同上；论文强调其分布与用户微调数据中的有害样本相同但具体样本不同（Section 5.1）。这是 Booster 相对于只用对齐数据的 Vaccine 所依赖的关键额外资源（Section 2、Section 4 的问题陈述）。
- 待对齐的基座模型：Llama2-7B（默认）、Gemma2-9B、Qwen2-7B（Section 5.1）。
- 优化器状态（AdamW）与两份额外的梯度缓存；论文实测对齐阶段峰值显存 57.86GB（Table 5）。
- 下载入口（Reproducibility Statement）：https://huggingface.co/datasets/anonymous4486/repnoise_beavertail ；GSM8K 使用 https://huggingface.co/datasets/openai/gsm8k 。
- 评测侧（不属于防御本体）：BeaverTails 的 moderation model 用于计算 HS（Section 5.1）；AlpacaEval 通过调用 ChatGPT API 评分（Appendix B）。
- 不需要：根数据集、预训练检测器、对齐前后的权重对、额外的教师或参考模型。

## 8. 计算与存储开销
论文报告（Table 5，Llama2-7B）：
- 对齐阶段时钟时间：SFT 0.54h，Booster 1.86h（约 3 倍）；微调阶段两者均为 0.10h；总计 SFT 0.64h vs Booster 1.95h。
- 显存：SFT 对齐 49.33GB、微调 40.01GB、峰值 49.33GB；Booster 对齐 57.86GB、微调 40.01GB、峰值 57.86GB，即比 SFT 多约 8.53GB。
- 对照：RepNoise 2.69h/72.47GB；Vaccine 1.06h/50.52GB；Lisa 对齐 0.54h/49.33GB 但微调阶段 45.35GB（每个请求都要付）。
- 论文解释：每个优化步要算三次梯度（三次前向/反向），因此训练时间约为三倍（Section 5.3）；额外显存来自"三个梯度向量的存储，以及一批有害数据的存储"（Section 5.3）。
- 论文强调这是一次性开销：对齐只做一次，之后可服务数百万次微调请求，因此优于每个请求都要付开销的微调阶段方案（Section 5.3）；Booster 与另外两个对齐阶段方案在微调阶段不产生额外计算。

分析：主要开销集中在步骤 4、5、8 的三次前向 + 反向，随 T × batch size 线性增长；步骤 6 的归一化是一次 O(可训练参数量) 的向量归约，可忽略；显存随可训练参数量（LoRA 参数加上两个额外梯度缓存）与一个 batch 的激活线性增长。Vaccine+Booster 变体还要多一次对齐数据的前向/反向（Section 5.5）。

## 9. 实现时容易错的地方
论文明确强调或可直接推出的：
1. 三处梯度的顺序与数据必须照 Algorithm 1：∇̃f(w_t) 在原始点、对齐 batch 上算；∇̃h(w_t) 与 ∇̃h(w_t − α·u_t) 都在**同一个**有害 batch (x′_t, y′_t) 上算（第 3、5、6 行），不要在扰动点重新采样批次。
2. 二阶项必须按式 (2)→式 (3) 丢掉：把 ∇(w_t − α·∇h(w_t)/‖∇h(w_t)‖) 近似为常数，实现时不能让梯度穿过扰动项（否则变成二阶/元学习式实现，语义与开销都不同）。
3. λ = 0 或 α = 0 会退化为普通 SFT，防御失效（Table 6、Table 7 的文字说明）。
4. α 过大（0.5、1、5）会导致优化不稳定且防御无效（Table 7：α = 0.5 时 HS 达 72.40）；λ 过大同样变差（λ = 100 时 HS 77.20，论文解释为模型无法在过大的安全损失下正常优化，Section 5.4）。论文把 λ 与 α 都列为必须"carefully tuned"的超参。
5. 有害样本过少（5 条）无法近似有害扰动（Table 8：HS 65.90），50 条即可（HS 5.10）。
6. 不要照搬 TAR 式"直接最小化负熵损失"：论文在 Appendix A 说明该做法训练极不稳定、模型会崩溃（h(w) 爆大、对任何提示都重复同一个词），因此才改为最小化"有害损失下降量"。
7. 论文声明实现严格照伪代码、不加任何额外技巧（Reproducibility Statement）。
8. 超参在不同下游任务上的最优值不同，而模型只对齐一次要服务未知任务，论文在 Appendix H 指出这是部署难点；Table 3 的评测刻意固定同一组超参。

论文没说清、实现时必须自己决定的：
1. ‖∇̃h(w_t)‖ 的作用域：是全部可训练参数展平后的全局 L2 范数，还是逐层/逐张量范数，论文未说明。
2. 扰动作用在哪些参数上：全部权重还是仅 LoRA 适配器，是否包含 embedding、LayerNorm，论文未说明。
3. 是否有梯度裁剪、混合精度与 loss scaling、用什么数值精度训练，论文未说明。
4. h(w) 的具体损失与掩码：有害回答的哪些 token 参与交叉熵、是否对 prompt 部分做 label masking，论文只写"empirical loss"，未说明。
5. 归一化使用的 ∇̃h(w_t) 是原始梯度还是经优化器处理后的梯度，论文未说明。
6. 对齐 batch 与有害 batch 是否需要配对、采样是否可复现（随机种子/数据顺序），论文未说明。
7. T 的总步数未直接给出，只能由 20 epochs × 5000/10 推算（分析）。
8. ‖∇̃h(w_t)‖ 接近 0 时如何避免除零或数值爆炸，论文未说明。
9. 式 (3) 与 AdamW 的结合方式（g̃ 是否直接作为 AdamW 的梯度、是否需要对 g̃ 做偏差校正）论文未说明；Appendix F 只说该问题可由一阶梯度方法（如 SGD、ADAM）求解。
10. 内循环是否只做一步：Booster 是一步（Appendix A 指出 TAR 用多步），但单步近似的误差论文未分析；同时论文未说明是否在不同步之间复用有害 batch。
11. Vaccine+Booster 的 ρ 取值论文未说明（Appendix C 的 ρ = 5 只属于 Vaccine 单独实现）。

## 10. 原文依据
1. 支撑步骤 9（正则项/目标的定义，式 (1) 中"gap"的含义）："second term, which measures the gap between the original harmful loss and the harmful loss after taking a normalized step with the harmful gradient."
2. 支撑步骤 7–9 的设计动机（模拟扰动、最小化有害损失下降速率）："By minimizing this gap, the reduction rate of harmful loss after taking optimization on the real harmful samples in the fine-tuning stage will be minimized (i.e., the impact of harmful perturbation will be attenuated)."
3. 支撑步骤 8（式 (2) 到式 (3) 的二阶项近似）："Inspired by (Finn et al., 2017; Rajeswaran et al., 2019), we rewrite the update rule by approximating this second-order gradient term to be constant, as follows:"
4. 支撑步骤 4、5、8（每步三次前向/反向）："We present the algorithm in Algorithm 1. The procedure requires three forward/backward passes for each optimization step."
5. 支撑步骤 1、2（数据规模）："In the alignment stage, we sample 5000 instances to construct the alignment dataset, and another 5000 instances to construct the harmful dataset."
6. 支撑步骤 7、9 与第 5 节（默认超参）："The default hyper-parameters for Booster are λ = 5 and α = 0.1 and we use 5000 pieces of harmful data in alignment to simulate harmful perturbation."
7. 支撑第 8 节（每步三次梯度导致三倍训练时间）："This is because, for each optimization step, Booster needs to evaluate the gradient three times, which triple the training time."
8. 支撑第 2 节（论文本体不是联邦方法，联邦只是未来方向）："To this end, it is interesting to extend the proposed Booster idea to federated instruction fine-tuning context."

```json
{
  "key": "huang2024booster",
  "method": "Booster：对齐阶段的有害扰动衰减正则（harmful perturbation attenuation），用一步归一化有害梯度模拟微调攻击，并最小化有害损失的下降量",
  "stages": ["outside_training"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "采样对齐数据批次",
      "operator": "sample_batch",
      "input": "对齐数据集（有害提示-安全回答对，5000 条）",
      "output": "对齐 batch (x_t, y_t)，10 条样本及其标签",
      "params": {"batch_size": 10, "dataset_size": 5000},
      "source": "Algorithm 1 第 2 行；Section 5.1；Appendix B"
    },
    {
      "step": "采样有害数据批次",
      "operator": "sample_batch",
      "input": "有害数据集（有害提示-有害回答对，5000 条，与用户微调中的有害样本同分布但不同样本）",
      "output": "有害 batch (x'_t, y'_t)，10 条；第 5、6 行的两次梯度共用该 batch",
      "params": {"batch_size": 10, "dataset_size": 5000, "size_sweep": [5, 10, 20, 50, 100, 500, 5000]},
      "source": "Algorithm 1 第 3 行；Section 5.1；Table 8"
    },
    {
      "step": "（可选变体 Vaccine+Booster）搜索嵌入扰动 epsilon*",
      "operator": "embedding_perturbation_search",
      "input": "对齐 batch (x_t, y_t)，当前权重 w_t",
      "output": "嵌入扰动 epsilon*，前向时加到 embedding 上",
      "params": {"rule": "epsilon* = rho * grad_e f(w) / ||grad_e f(w)||", "rho": "论文未说明 Vaccine+Booster 的 rho；Vaccine 单独实现用 rho=5（Appendix C）", "optional": true},
      "source": "Section 5.5；Appendix F 式 (6)；Algorithm 2 第 3 行"
    },
    {
      "step": "对齐损失梯度",
      "operator": "cross_entropy_gradient",
      "input": "对齐 batch（变体下为加了 epsilon* 的嵌入）",
      "output": "grad_f，形状同可训练参数",
      "params": {"loss": "SFT 对齐时是交叉熵（Section 4 脚注 2）", "lora_rank": 32, "lora_alpha": 4},
      "source": "Algorithm 1 第 4 行；Algorithm 2 第 4 行"
    },
    {
      "step": "有害损失梯度（原始权重处）",
      "operator": "cross_entropy_gradient",
      "input": "有害 batch (x'_t, y'_t)，当前权重 w_t",
      "output": "grad_h(w_t)",
      "params": {},
      "source": "Algorithm 1 第 5 行；式 (1)"
    },
    {
      "step": "有害梯度归一化",
      "operator": "gradient_l2_normalize",
      "input": "grad_h(w_t)",
      "output": "单位方向 u_t = grad_h(w_t) / ||grad_h(w_t)||",
      "params": {"scope": "论文未说明是全局展平范数还是逐层范数"},
      "source": "式 (1)、式 (3)；Algorithm 1 第 6 行"
    },
    {
      "step": "权重扰动（模拟一步有害微调）",
      "operator": "weight_perturbation",
      "input": "w_t 与 u_t",
      "output": "临时权重 w'_t = w_t - alpha * u_t（不持久化）",
      "params": {"alpha": 0.1, "alpha_sweep": [0, 0.01, 0.1, 0.5, 1, 5]},
      "source": "式 (1)、式 (3)；Algorithm 1 第 6 行；Table 7"
    },
    {
      "step": "扰动点上的有害损失梯度",
      "operator": "cross_entropy_gradient",
      "input": "同一个有害 batch (x'_t, y'_t)，扰动权重 w'_t",
      "output": "grad_h(w_t - alpha * u_t)；梯度不穿过扰动项",
      "params": {"second_order": "按式 (2) 到式 (3) 将二阶项近似为常数并丢弃"},
      "source": "式 (2) 到式 (3)；Algorithm 1 第 6 行"
    },
    {
      "step": "合成衰减正则梯度",
      "operator": "gradient_combine",
      "input": "grad_f、grad_h(w_t)、grad_h(w'_t)",
      "output": "g = grad_f + lambda * (grad_h(w_t) - grad_h(w'_t))",
      "params": {"lambda": 5, "lambda_sweep": [0, 0.1, 1, 5, 10, 20, 50, 100]},
      "source": "式 (3)；Algorithm 1 第 7 行；Table 6"
    },
    {
      "step": "优化器更新",
      "operator": "adamw_step",
      "input": "合成梯度 g 与优化器状态",
      "output": "更新后的权重 w_{t+1}；循环 T 步后输出对齐模型 w_tilde",
      "params": {"optimizer": "AdamW", "lr": 0.0005, "weight_decay": 0.1, "epochs": 20, "T": "论文未直接给出，分析：20 epochs x 5000/10 = 10000 步，与 Table 16 报告到 10000 步一致"},
      "source": "Algorithm 1 第 8 行与 output 行；Section 5.1；Appendix B"
    }
  ],
  "sampling": [
    {"what": "samples", "how": "从 BeaverTails 扩充数据中采样构造对齐数据集", "size": "5000 条（Section 5.1；Appendix B）"},
    {"what": "samples", "how": "采样构造有害数据集，与用户微调数据中的有害样本同分布但不同样本", "size": "5000 条（Section 5.1）；Table 8 扫描 5/10/20/50/100/500/5000，50 条已足够、5 条不足"},
    {"what": "samples", "how": "每个对齐优化步分别采样对齐 batch 与有害 batch", "size": "各 10 条（Algorithm 1 第 2-3 行；batch size 10，Section 5.1、Appendix B）"},
    {"what": "layers", "how": "用 LoRA 低秩适配器限制可训练参数（训练配置，不是 Booster 的采样算子；论文未说明归一化与扰动是否只作用于 LoRA 参数）", "size": "rank 32、alpha 4（Section 5.1）"},
    {"what": "rounds", "how": "对齐训练 epoch 数；Algorithm 1 的 T（SGD steps）未直接给出", "size": "20 epochs（Section 5.1；Appendix B）"},
    {"what": "clients", "how": "论文未使用：方法是对齐阶段的集中式训练，Appendix H 才把联邦指令微调列为未来方向", "size": "论文未使用"},
    {"what": "coordinates", "how": "论文未使用坐标级抽样、稀疏化或量化", "size": "论文未使用"},
    {"what": "probes", "how": "论文未使用参考数据或探针集", "size": "论文未使用"}
  ],
  "resources": [
    "对齐数据集（有害提示-安全回答对）：5000 条，来自 BeaverTails（Ji et al., 2023）经 Rosati et al. (2024c) 扩充的版本（Section 5.1、Appendix B）",
    "有害数据集（有害提示-有害回答对）：5000 条，同一来源，分布与用户微调中的有害样本相同但样本不同（Section 5.1）",
    "待对齐基座模型：Llama2-7B（默认）、Gemma2-9B、Qwen2-7B（Section 5.1）",
    "LoRA 适配器配置：rank 32、alpha 4（Section 5.1）",
    "优化器状态（AdamW）与两份额外梯度缓存；对齐阶段峰值显存约 57.86GB（Table 5）",
    "评测侧：BeaverTails 的 moderation model 计算有害分数（Section 5.1）；AlpacaEval 通过 ChatGPT API 评分（Appendix B）",
    "数据下载入口：https://huggingface.co/datasets/anonymous4486/repnoise_beavertail （Reproducibility Statement）",
    "不需要根数据集、预训练检测器、对齐前后权重对或额外教师模型"
  ],
  "actions": ["transform_gradients"],
  "dominant_cost": "每个对齐优化步需要 3 次前向+反向（步骤 4、5、8）；论文实测对齐阶段时钟 1.86h 对 SFT 0.54h，峰值显存 57.86GB 对 49.33GB，多约 8.53GB（Table 5、Section 5.3）。分析：主开销随 T x batch size 线性增长，显存随可训练参数量加一个 batch 的激活增长；微调阶段无额外开销",
  "underspecified": [
    "梯度的范数 ||grad_h(w_t)|| 是全部可训练参数展平后的全局 L2 范数还是逐层范数，论文未说明",
    "扰动与归一化作用在哪些参数上（全部权重还是仅 LoRA 适配器，是否含 embedding、LayerNorm），论文未说明",
    "是否有梯度裁剪、混合精度与 loss scaling，论文未说明",
    "h(w) 在有害回答的哪些 token 上计算、是否对 prompt 做 label masking，论文未说明",
    "归一化用的 grad_h(w_t) 是原始梯度还是优化器处理后的梯度，论文未说明",
    "对齐 batch 与有害 batch 是否需要配对、采样是否可复现（随机种子与数据顺序），论文未说明",
    "Algorithm 1 的总步数 T 未直接给出，只能由 20 epochs x 5000/10 推算（分析）",
    "||grad_h(w_t)|| 接近 0 时的除零与数值稳定性处理，论文未说明",
    "式 (3) 与 AdamW 的结合方式（g 是否直接作为 AdamW 梯度、是否需偏差校正）论文未说明；Appendix F 只说可由 SGD/ADAM 求解",
    "内循环只做一步的近似误差论文未分析，也未说明是否在不同步之间复用有害 batch",
    "Vaccine+Booster 变体的 rho 取值论文未说明（Appendix C 的 rho=5 属于 Vaccine 单独实现）"
  ],
  "quotes": [
    {"supports": "步骤 9：正则项与目标函数（式 (1) 的 gap 含义）", "text": "second term, which measures the gap between the original harmful loss and the harmful loss after taking a normalized step with the harmful gradient."},
    {"supports": "步骤 7-9：模拟有害扰动并最小化有害损失下降速率的动机", "text": "By minimizing this gap, the reduction rate of harmful loss after taking optimization on the real harmful samples in the fine-tuning stage will be minimized (i.e., the impact of harmful perturbation will be attenuated)."},
    {"supports": "步骤 8：式 (2) 到式 (3) 的二阶项近似", "text": "Inspired by (Finn et al., 2017; Rajeswaran et al., 2019), we rewrite the update rule by approximating this second-order gradient term to be constant, as follows:"},
    {"supports": "步骤 4、5、8：每个优化步三次前向/反向", "text": "We present the algorithm in Algorithm 1. The procedure requires three forward/backward passes for each optimization step."},
    {"supports": "步骤 1、2：对齐数据与有害数据的规模", "text": "In the alignment stage, we sample 5000 instances to construct the alignment dataset, and another 5000 instances to construct the harmful dataset."},
    {"supports": "步骤 7、9 与第 5 节：默认超参 lambda 与 alpha", "text": "The default hyper-parameters for Booster are λ = 5 and α = 0.1 and we use 5000 pieces of harmful data in alignment to simulate harmful perturbation."},
    {"supports": "第 8 节：每步三次梯度导致约三倍训练时间", "text": "This is because, for each optimization step, Booster needs to evaluate the gradient three times, which triple the training time."},
    {"supports": "第 2 节：论文本体是集中式对齐阶段方法，联邦只是未来方向", "text": "To this end, it is interesting to extend the proposed Booster idea to federated instruction fine-tuning context."}
  ]
}
```
