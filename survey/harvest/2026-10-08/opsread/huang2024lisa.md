# huang2024lisa：Lisa（Lazy(i) Safety Alignment，惰性安全对齐）

## 1. 方法一句话
输入是一个已经过安全对齐（safety alignment）的 LLM、一份服务提供方持有的对齐数据集（alignment dataset）和一份混有比例 p 有害数据（harmful data）的用户微调数据集（user fine-tuning dataset），输出是同一套权重在微调阶段被改写后的"定制化模型"；Lisa 不做任何"是/否"的有害判定，而是把微调过程改写成在"对齐状态"与"微调状态"之间交替、且每个状态都被一个近端项（proximal term）拉向另一个状态刚结束时留下的切换检查点（switching checkpoint）的优化过程，从而在不识别、不剔除任何有害样本的前提下压低有害分数（Harmful Score，HS），同时尽量保住微调精度（Finetune Accuracy，FA）（摘要、4.1 节、4.2 节、5.2 节）。

## 2. 运行位置
Lisa 是集中式（centralized）的"微调即服务"（fine-tuning-as-a-service）防御，论文的流程是两阶段：服务提供方先做对齐阶段（alignment stage，第 ① 阶段），再在用户上传的数据上做用户微调阶段（user fine-tuning stage，第 ② 阶段），Lisa 只修改第 ② 阶段，保持第 ① 阶段不变（图 1、4.1 节、5.1 节 Baselines 段落）。因此它的每个"状态切换"发生在服务提供方自己的训练循环内部，不在客户端与服务器之间。

分析：把 Lisa 映射到联邦流程时，最自然的位置是"客户端本地训练循环内部"。服务器先下发（server_distribute）对齐后的基座模型与 LoRA（Low-Rank Adaptation）配置；客户端训练前（client_pre_train / client_pre_step）装载服务提供方预先给定的对齐数据集并设定近端参考点；每个 cycle 的前 K1 步在客户端训练步（client_step）里跑对齐状态，后 K2 步在同一个 client_step 里跑微调状态；一个 cycle 结束时把当前权重当作下一个 cycle 的近端中心；训练结束后（client_post_train）用最后一次微调状态结束时的权重作为本地个性化模型。论文完全没有描述联邦场景，也没有要求任何额外的客户端—服务器往返（needs_round_trip = false）：对齐数据集在论文里是服务提供方早已为对齐阶段收集好的同一份数据（第 3 节 Preliminaries、5.1 节、附录 A.1），Lisa 只是复用它，不引入新的上传或下载协议。如果外层还要做服务器聚合（server_aggregate），论文未说明近端项语义如何在聚合后保持。

## 3. 算子流水线

**步骤 0（前置，训练之外）：对齐阶段 SFT，Lisa 的起点。**
- 输入：预训练 LLM 权重（Llama2-7B non-chat、Opt、Mistral-7B），以及对数据集（instruction / input / response 三元组，由系统提示模板构造）中的 10000 条 BeaverTails 安全样本。
- 计算：标准监督微调（Supervised Fine-Tuning，SFT），LoRA 秩（rank）为 8，学习率 1e-3，batch size 为 5，训练 30 个 epoch；随后把该对齐适配器（adaptor）合并进预训练模型，得到对齐后的模型，并在微调阶段冻结它（5.1 节 Training details、附录 A.1）。注意论文只给了该阶段的超参，未说明该阶段使用的优化器。
- 输出：对齐后的模型权重 `w_align`（5.1 节）。
- 出处：第 3 节 Preliminaries、图 1、5.1 节、附录 A.1。

**步骤 1：设定近端参考点（proximal reference）。**
- 输入：当前 cycle 开始时的可训练权重，记为 `w_t`。
- 计算：把 `w_t` 作为式 (2) 左式中的"参考点"，即对齐状态要靠近的目标；按算法 2，第一个 cycle 的 `w_t` 就是 `w_align`。论文没有说明这份参考权重是否需要显式复制（clone）一份，只说要把它作为近端中心。
- 输出：近端中心 `w_t`。
- 出处：算法 2 第 1 行注释、式 (2) 左式、4.2 节。

**步骤 2：对齐状态（State 1），跑 K1 步。**
- 输入：从对齐数据集采样的一个 batch `(x_{t,k}, y_{t,k})`（batch size 为 5），当前权重，近端中心 `w_t`。
- 计算：求解子问题 `w̃_{t+1} = arg min_w f(w) + (ρ/2)·||w − w_t||²`，其中 `f(w)` 是对齐数据集上用于因果语言建模（causal language modeling）的标准交叉熵损失（式 (1) 与 4.1 节），`ρ` 是近端强度。用 K1 步近似求解：每一步的梯度是 `∇f(w; x, y) + ρ·(w − w_t)`，再做一次优化器更新（Optimizer_Step；实验中为 AdamW，学习率 1e-5，见 5.1 节、附录 A.1）。到达该子问题的驻点时满足 `∇f(w̃_{t+1}) + ρ·(w̃_{t+1} − w_t) = 0`（式 (4)，附录 B.3 Fact 1）。
- 输出：`w̃_{t+1}`。
- 出处：算法 2 第 1 个注释行、式 (2) 左式、式 (4)、4.2 节。

**步骤 3：写切换检查点。**
- 输入：对齐状态结束时的权重 `w̃_{t+1}`。
- 计算：把 `w̃_{t+1}` 固定为下一个状态的近端中心，即微调状态的目标是 `arg min_w h(w) + (ρ/2)·||w − w̃_{t+1}||²`。论文在系统评测里提到此处需要"switching check-point 的存储"（5.3 节），但没有说明存的是全量权重还是仅可训练参数、以及是否落盘。
- 输出：作为 State 2 近端中心的 `w̃_{t+1}`。
- 出处：式 (2) 右式、算法 2、5.3 节。

**步骤 4：微调状态（State 2），跑 K2 步。**
- 输入：从用户微调数据集（含比例 p 的有害数据）采样的 batch，当前权重，近端中心 `w̃_{t+1}`。
- 计算：求解 `w_{t+1} = arg min_w h(w) + (ρ/2)·||w − w̃_{t+1}||²`，`h(w)` 是用户微调数据集上的标准交叉熵损失（式 (1)、4.2 节）。K2 步近似求解，每步梯度为 `∇h(w; x, y) + ρ·(w − w̃_{t+1})`，再走一次 AdamW；驻点条件为 `∇h(w_{t+1}) + ρ·(w_{t+1} − w̃_{t+1}) = 0`（式 (5)，Fact 2）。
- 输出：`w_{t+1}`。
- 出处：算法 2 第 2 个注释行、式 (2) 右式、式 (5)、4.2 节。

**步骤 5：跨状态循环 T 个 cycle。**
- 输入：上一个 cycle 的产物 `w_{t+1}`，作为下一个 cycle 的 `w_t`（算法 1 里写作 `w_{t+1,0} = w_{t,K1+K2}`）。
- 计算：`for t ∈ [T]` 重复步骤 1–4；等价说法是"对齐状态 K1 步 + 微调状态 K2 步，交替重复 T 个 cycle"。论文默认 K1/K2 = 100/900，但 T 的取值论文未说明。
- 输出：最终迭代序列的终点 `w_T`（按算法 2 的写法是 `w_{t+1}`，即最后一次微调状态结束时的权重）。
- 出处：算法 1、算法 2 的 `for t ∈ [T]`、4.1 节、5.1 节。

**步骤 6：输出定制化模型。**
- 输入：最后一次微调状态结束的权重。
- 计算：不做任何后处理（论文未给出裁剪、融合、再对齐等步骤）。
- 输出：部署在服务器上、对用户提示提供个性化输出的模型（第 3 节 Preliminaries）。
- 出处：第 3 节 Preliminaries、算法 2。

## 4. 采样与规模控制
- **样本（samples）**：用户微调数据默认总数为 n = 5000 条，其中 10%（p = 0.1）为从 BeaverTails 采样的有害数据，其余为对应下游任务的良性数据（5.1 节、附录 A.1）。AlpacaEval 任务因数据有限只用 700 条（附录 A.1）。对齐数据沿用对齐阶段的同一份 BeaverTails 数据集、共 10000 条（5.1 节、附录 A.1）。论文特别说明，为公平比较，基线 Vlguard 只从同一对齐数据集中采 1000 条以匹配 Lisa/BSO 的计算量（附录 A.1）——这不影响 Lisa 自身用 10000 条这一事实。
- **客户端（clients）**：论文未使用；这是集中式单租户流程。
- **层（layers）**：只训练 LoRA 适配器，秩为 8；对齐与微调使用两个分离的 LoRA 组件（Double-LoRA 实现），这一设定对对齐阶段与微调阶段都适用（5.1 节、附录 A.1）。论文未说明近端项是否只作用在 LoRA 参数上。
- **参数坐标（coordinates）**：论文未使用，没有逐坐标裁剪、抽样或降维。
- **轮次（rounds）**：交替 T 个 cycle，每个 cycle 内 K1 与 K2 步；默认 K1/K2 = 100/900（5.1 节）。T 的具体取值论文未说明；实验的步数分配表（Table 2）、超参表（Table 8、Table 9）与计时（Table 7）都按 1000 步的总预算组织，5.3 节的漂移曲线提到"even after 20000 steps of training"。
- **探针（probes）**：论文未使用。论文没有用任何额外参考样本给更新打分；对齐数据是训练数据，不是探针集。

## 5. 超参数
| 名称 | 含义 | 论文取值 | 出处 |
|---|---|---|---|
| K1 | 每个 cycle 投入对齐状态的步数 | 默认 100；备选扫描 1000/900/700/500/300/100/0 | 5.1 节；Table 2、Table 8 |
| K2 | 每个 cycle 投入微调状态的步数 | 默认 900；备选与 K1 互补至 1000 | 5.1 节；Table 2、Table 8 |
| ρ | 近端强度（proximal intensity / penalty） | 默认 1；扫描 {0, 0.01, 0.1, 0.5, 1, 5, 10} | 5.1 节；Table 9 |
| T | 两个状态交替的 cycle 数 | 论文未说明（只在算法里出现 `for t ∈ [T]`） | 算法 2、4.1 节 |
| LoRA rank | 适配器秩 | 8 | 5.1 节 |
| 微调学习率 | 用户微调阶段学习率 | 1e-5 | 5.1 节、附录 A.1 |
| 对齐学习率 | 对齐阶段学习率 | 1e-3 | 附录 A.1 |
| batch size | 两个阶段都用 | 5 | 5.1 节、附录 A.1 |
| epoch 数 | 微调 SST2/AGNEWS 为 20，GSM8K 为 50；对齐阶段为 30 | 20 / 50 / 30 | 5.1 节、附录 A.1 |
| 优化器 | 微调阶段 | AdamW | 5.1 节 |
| 对齐数据量 | 供对齐阶段与 Lisa 复用 | 10000 条 | 附录 A.1 |
| 微调数据量 n | 默认 | 5000（AlpacaEval 为 700） | 5.1 节、附录 A.1 |
| 有害比例 p | 默认攻击设定 | 0.1 | 5.1 节 |
| weight decay、学习率调度、warmup、精度 | — | 论文未说明 | — |

## 6. 判定与动作
Lisa 没有任何检测器、阈值或聚类判定：它从不判断哪条样本有害、哪个客户端恶意，因此没有剔除、加权、裁剪、加噪这些离散动作。唯一的"动作"是连续地改写每个训练步的梯度方向，把权重往另一个状态刚结束的检查点拉，即 `transform_gradients`：对齐状态每步的更新方向是 `∇f(w) + ρ·(w − w_t)`，微调状态是 `∇h(w) + ρ·(w − w̃_{t+1})`（式 (2)、式 (4)、式 (5)）。强度由 ρ 控制，论文没有给出基于数据的自适应规则，只给出理论条件：`ρ > L`（L 为损失的 L-smoothness 常数）才能保证收敛到全局问题的驻点（Theorem 1、Remark 1）；`ρ ≥ L` 时势函数（potential function）沿迭代单调不降（附录 B.5.1 Lemma 3）。跨轮累积方面，方法不累积任何统计量或评分，但近端参考点跨状态、跨 cycle 传递：State 2 的中心是本 cycle 内 State 1 的终点 `w̃_{t+1}`，下一 cycle State 1 的中心则是上一 cycle State 2 的终点 `w_t`（式 (2)、算法 1 的 `w_{t+1,0} = w_{t,K1+K2}`）。5.5 节里的"Filter + Lisa"确实先做了一次样本过滤，但那一步用的是外部 BeaverTails 审核模型（moderation model，漏检率 7.71%，脚注 2），属于与 Lisa 组合的另一条流程，不是 Lisa 自身的判定。

## 7. 需要的外部资源
- 一份对齐数据集：BeaverTails 的安全样本共 10000 条，且要与对齐阶段使用的是同一份（5.1 节、附录 A.1）。这是 Lisa 最硬的前置条件——没有对齐数据就无法构造对齐状态。
- 一个已经对齐好的模型检查点：SFT 对齐后的 Llama2-7B、Opt 或 Mistral-7B，其 LoRA 适配器已合并进基座（5.1 节）。
- 一份跨状态保存的切换检查点：论文报告这带来额外 3.14GB 显存（5.3 节、Table 7）。
- 用户微调数据：默认 5000 条、10% 有害（附录 A.1）。
- 系统提示模板（附录 A.1），用于把各任务的句子/问答构造成 instruction / input / response 三元组。
- 评测侧还需要：BeaverTails 审核模型与 1000 条测试样本，SST2 的 872 条、AGNEWS/GSM8K 各 1000 条、AlpacaEval 122 条测试样本，以及给 AlpacaEval 打分的 ChatGPT API（附录 A.1）。
- 训练硬件为单张 H100（附录 A.1）。
- 不需要根数据集（root dataset）、不需要预训练检测器、也不需要第三个模型。

## 8. 计算与存储开销
论文报告（5.3 节、Table 7，单位：1000 步）：SFT 115.53 s / 47.97 GB，Vlguard 122.34 s / 48.48 GB，BSO 119.22 s / 50.85 GB，Lisa 125.11 s / 51.11 GB。即 Lisa 的时钟时间比 SFT 增加 8.3%、比 BSO 增加 4.9%，显存比 SFT 多 3.14 GB。论文的解释是：额外计算主要来自近端项的前向/反向（forward/backward），这部分不随数据量增长，只取决于可训练参数量；额外显存来自切换检查点的存储，同样不随训练数据量增长。

分析：按第 3 节的流水线，主要开销来自步骤 2 与步骤 4 的每一次 `proximal_penalized_grad_step`——每个训练步除了原有的一次前向与反向之外，还要多算一次近端项（论文按"前向/反向"描述，说明它是作为损失项实现，而不是解析地往梯度上加一项），代价随可训练参数个数线性增长。第二块开销是数据侧的：每个 cycle 的 K1 步要额外跑对齐数据的 batch，因此相对同等总步数的 SFT，多出的前向/反向次数正比于 K1（附录 A.1 专门让 Vlguard 只采 1000 条对齐样本以匹配 Lisa/BSO 的计算量，可佐证这是主要额外成本）。论文还在附录 D 指出，该开销随微调请求数线性增长，因为每个用户请求都要重跑一遍微调。

## 9. 实现时容易错的地方
论文明确强调或可直接读出的：
- 近端强度必须足够大。Theorem 1 与 Remark 1 指出需要 `ρ > L` 才能保证收敛，且当 `ρ → L` 时不等式右端趋于无穷、最后一次迭代的全局梯度范数无界；附录 B.5.1 的 Lemma 3 给出 `ρ ≥ L` 时势函数沿迭代单调不增。默认取 ρ = 1（5.1 节）。
- 两个状态的近端中心不同：State 1 靠近 `w_t`（上一 cycle 微调状态的终点），State 2 靠近本 cycle 内 State 1 刚结束的 `w̃_{t+1}`，不能都用同一个初始点（式 (2) 左右两式）。5.4 节还强调：当对齐步数过少而 ρ 偏大时，近端项会把迭代钉在初始点附近，结果是微调精度与有害分数同时变低。
- 两个组件缺一不可：去掉近端项（ρ = 0）就退化为 BSO，平均有害分数比完整 Lisa 高 6.54%；只保留近端项、去掉对齐数据引导，平均微调精度比完整 Lisa 低 7.73%（5.4 节、Table 10）。
- 对齐步数 K1 太小会显著退化：Table 2 显示随着对齐步数从 1000 降到 0，有害分数从 34.00 升到 51.60，即退化为 SFT。
- 必须保存切换检查点，否则无法实现 State 2 的近端项（5.3 节）。
- 论文自述方法只能叠加在 SFT 上，未验证能否推广到 RLHF（Reinforcement Learning from Human Feedback）类对齐（附录 D）。

论文没有说清、实现时必须自己决定的：
- T（cycle 数）取值，以及总步数如何与 epoch 数、数据量换算。
- 近端项作用范围：是全部参数还是只有 LoRA 可训练参数；是否包含偏置与归一化层参数。
- AdamW 的动量/二阶矩状态在状态切换时是否重置，还是一路延续。
- 一个"step"指一次优化器更新还是一次数据采样；算法 1 写的是每个 k 采样一个 batch，但没有说明 K1/K2 是否等同于优化器步数。
- 每个状态内部是否重新打乱数据、是否跨 epoch 边界、对齐数据是否循环重复使用。
- 学习率调度、warmup、weight decay、混合精度设定。
- L 的估计方法。论文只给理论条件 ρ > L，没有给 L 的实测值或估计流程，因此该条件在实践中无法直接校验。
- 近端项的实现形式：式 (2) 写成目标函数里加 `(ρ/2)||w − ref||²`，而 5.3 节说开销来自"前向/反向"，暗示按损失项实现；两种实现数值上等价但显存与速度不同。
- 若服务提供方没有对齐数据、或只有 Vlguard 口径的 1000 条对齐数据时 Lisa 的表现。
- 联邦或多客户端场景下的聚合方式（论文完全未涉及）。
- 多处记号不一致需要自行统一：算法 1 用 `w_{t,k}` 记 cycle 内第 k 步，算法 2 用 `w_t` / `w̃_{t+1}` 记切换检查点；另外 5.1 节写 "Opt-3.7B"，而 Table 5 表头写 "Opt-2.7B"。

## 10. 原文依据
1. 支撑步骤 5（跨状态循环）与步骤 2、4 的步数分配：
   "For the first state, the model is trained on the alignment dataset for K1 steps, while for the second state, the model is trained on the fine-tuning dataset for K2 steps. The alternating between two states are repeated T cycles."
2. 支撑步骤 1–4 的设计思想（为什么要加近端项）：
   "Our idea is to introduce a proximal term in the loss for each state, such that the optimization process becomes lazy, i.e., taking a smaller drift towards the checkpoint obtained in another state."
3. 支撑步骤 1 与步骤 3 中"参考点"的定义：
   "Formally, the proximal term is defined as ∥w −wt∥2, i.e., the square of Euclidean distance between the current model weight and the switching checkpoint obtained by the last state."
4. 支撑步骤 2 与步骤 4 的子问题形式（式 (2)）：
   "Formally, we derive two sub-problems for each state to solve. For alignment/fine-tuning state, we invest K1/K2 steps in solving the problem with a proximal term, as follows:"
5. 支撑步骤 3（切换检查点/漂移是设计动机）：
   "Our results indicate that BSO(900,100) achieves the smallest drift. Combining all the three sub-figures in Figure 2, a smaller drift seems to be preferable in terms of reducing alignment loss and ensuring a better convergence property."
6. 支撑第 6 节里 ρ 与 L 的判定条件：
   "Under Assumptions 1-3, when the proximal intensity is chosen as ρ > L, and that a subsequence is converging to a cluster point, Lisa's rate of convergence of is:"
7. 支撑第 5 节默认超参数：
   "The default setting of Lisa is as follows. The steps invested in Alignment/fine-tuning is 100/900, the proximal penalty ρ is 1."
8. 支撑第 8 节的开销来源：
   "We show in Table 7 that the clock time of Lisa is slightly increased by 8.3% compared to SFT, by 4.9% compared to BSO. The extra computation mainly comes from the forward/backward of the proximal term."

```json
{
  "key": "huang2024lisa",
  "method": "Lisa (Lazy(i) Safety Alignment)：在对齐数据与用户微调数据之间交替做带近端项的双状态优化，用近端项压制朝切换检查点的过度漂移",
  "stages": ["client_pre_train", "client_step", "client_post_train"],
  "needs_round_trip": false,
  "pipeline": [
    {
      "step": "前置对齐阶段 SFT（Lisa 的起点，论文明确说 Lisa 保持对齐阶段不变）",
      "operator": "supervised_finetune_lora",
      "input": "预训练 LLM 权重；对齐数据集三元组 (instruction,input,response) 共 10000 条，batch=5",
      "output": "对齐后的模型权重 w_align（LoRA 适配器已合并进基座并冻结）",
      "params": {"lora_rank": 8, "lr": 1e-3, "batch_size": 5, "epochs": 30, "n_alignment": 10000, "optimizer": "论文未说明"},
      "source": "5.1 节 Training details、附录 A.1、第 3 节 Preliminaries"
    },
    {
      "step": "初始化近端参考权重（每个 cycle 开始时）",
      "operator": "reference_weight_snapshot",
      "input": "当前 cycle 起点权重 w_t（首个 cycle 为 w_align）",
      "output": "State 1 的近端中心 w_t",
      "params": {},
      "source": "算法 2 第 1 行注释、式 (2) 左式、4.2 节"
    },
    {
      "step": "对齐状态：带近端项的梯度步，重复 K1 步",
      "operator": "proximal_penalized_grad_step",
      "input": "对齐数据集 batch (x,y)，batch=5；当前权重 w；近端中心 w_t",
      "output": "w̃_{t+1}（K1 步后的权重）",
      "params": {"rho": 1, "K1": 100, "lr": 1e-5, "batch_size": 5, "optimizer": "AdamW", "gradient": "grad f(w;x,y) + rho*(w - w_t)", "stationarity": "grad f(w̃_{t+1}) + rho*(w̃_{t+1} - w_t) = 0"},
      "source": "算法 2 第 1 个注释行、式 (2) 左式、式 (4)、Fact 1（附录 B.3）、5.1 节"
    },
    {
      "step": "写切换检查点，作为下一个状态的近端中心",
      "operator": "snapshot_switching_checkpoint",
      "input": "w̃_{t+1}",
      "output": "State 2 的近端中心 w̃_{t+1}",
      "params": {"storage": "论文报告额外约 3.14GB 显存（5.3 节、Table 7）；保存范围论文未说明"},
      "source": "式 (2) 右式、算法 2、5.3 节"
    },
    {
      "step": "微调状态：带近端项的梯度步，重复 K2 步",
      "operator": "proximal_penalized_grad_step",
      "input": "用户微调数据集 batch（含比例 p 的有害数据），batch=5；当前权重 w；近端中心 w̃_{t+1}",
      "output": "w_{t+1}",
      "params": {"rho": 1, "K2": 900, "lr": 1e-5, "batch_size": 5, "optimizer": "AdamW", "gradient": "grad h(w;x,y) + rho*(w - w̃_{t+1})", "stationarity": "grad h(w_{t+1}) + rho*(w_{t+1} - w̃_{t+1}) = 0"},
      "source": "算法 2 第 2 个注释行、式 (2) 右式、式 (5)、Fact 2（附录 B.3）、5.1 节"
    },
    {
      "step": "跨状态循环 T 个 cycle（每个 cycle 先 K1 步对齐状态、再 K2 步微调状态）",
      "operator": "alternate_two_state_loop",
      "input": "上一 cycle 的终点权重 w_{t+1}，作为下一 cycle 的参考 w_t",
      "output": "最终迭代 w_T（即最后一次微调状态的终点）",
      "params": {"T": "论文未说明", "K1_plus_K2": 1000},
      "source": "算法 1、算法 2 的 for t ∈ [T]、4.1 节、5.1 节"
    },
    {
      "step": "输出定制化模型（无条件后处理）",
      "operator": "return_final_iterate",
      "input": "最后一次微调状态结束的权重",
      "output": "部署在服务器上的定制化模型",
      "params": {},
      "source": "第 3 节 Preliminaries、算法 2"
    }
  ],
  "sampling": [
    {"what": "samples", "how": "用户微调数据总数 n 中按比例 p 混入 BeaverTails 有害样本；对齐数据复用对齐阶段的同一份", "size": "n=5000（AlpacaEval 为 700）、p=0.1 默认（5.1 节、附录 A.1）；对齐数据 10000 条（附录 A.1）"},
    {"what": "clients", "how": "论文未使用：集中式微调即服务，单一服务提供方与单一用户请求", "size": "论文未使用"},
    {"what": "layers", "how": "只训练 LoRA 适配器，对齐与微调使用两个分离的 LoRA 组件（Double-LoRA）", "size": "rank=8（5.1 节、附录 A.1）"},
    {"what": "coordinates", "how": "论文未使用：没有逐坐标裁剪、抽样或降维", "size": "论文未使用"},
    {"what": "rounds", "how": "两种状态交替 T 个 cycle，每个 cycle 内 K1 + K2 步", "size": "K1/K2 = 100/900 默认（5.1 节）；T 论文未说明；实验按 1000 步预算组织（Table 2/7/8/9），5.3 节提到 20000 步"},
    {"what": "probes", "how": "论文未使用：没有用参考探针给更新打分，对齐数据是训练数据而非探针", "size": "论文未使用"}
  ],
  "resources": [
    "对齐数据集：BeaverTails 安全样本 10000 条，与对齐阶段同一份（5.1 节、附录 A.1）",
    "已对齐的模型检查点：SFT 对齐后的 Llama2-7B / Opt / Mistral-7B，LoRA rank 8 适配器已合并（5.1 节）",
    "跨状态保存的可训练参数副本（switching check-point），论文报告额外约 3.14GB 显存（5.3 节、Table 7）",
    "用户微调数据集：默认 5000 条、10% 有害（附录 A.1）",
    "系统提示模板，用于构造 instruction/input/response 三元组（附录 A.1）",
    "评测侧资源：BeaverTails 审核模型 + 各任务测试集（SST2 872、AGNEWS/GSM8K 1000、AlpacaEval 122）+ AlpacaEval 用的 ChatGPT API（附录 A.1）",
    "训练硬件：单张 H100（附录 A.1）",
    "不需要根数据集、预训练检测器或额外的第三个模型"
  ],
  "actions": ["transform_gradients"],
  "dominant_cost": "论文报告：跑 1000 步时 Lisa 为 125.11 s / 51.11 GB，比 SFT 慢 8.3%、多 3.14GB 显存，比 BSO 慢 4.9%（5.3 节、Table 7）；论文解释额外计算来自近端项的前向/反向，不随数据量增长而随可训练参数量增长，显存来自切换检查点。分析：主要开销来自每个训练步多算一次近端项（O(可训练参数量)），其次是每个 cycle 多出的 K1 步对齐数据前向/反向；附录 D 指出该开销随用户微调请求数线性增长。",
  "underspecified": [
    "T（两个状态交替的 cycle 数）没有给出取值",
    "K1/K2 是否等同于优化器步数，还是一个 step 指一次采样",
    "近端项作用范围：全部参数还是只有 LoRA 可训练参数，是否含偏置与归一化参数",
    "AdamW 的动量与二阶矩在状态切换时是否重置",
    "每个状态内部是否重新打乱数据、是否跨 epoch 边界、对齐数据是否循环使用",
    "学习率调度、warmup、weight decay、混合精度设置",
    "L（L-smoothness 常数）的估计方法，ρ > L 在实践中无法直接校验",
    "近端项的实现形式：作为 loss 项做前向/反向，还是解析地加在梯度上",
    "参考权重与当前权重的数值精度（是否 fp32 保存副本）",
    "服务提供方缺少对齐数据时的替代方案",
    "联邦/多客户端下如何在聚合前后保持近端项语义",
    "多处记号与设定不一致：算法 1 用 w_{t,k}、算法 2 用 w_t/w̃_{t+1}；5.1 节写 Opt-3.7B 而 Table 5 写 Opt-2.7B"
  ],
  "quotes": [
    {"supports": "步骤 5 与步骤 2/4：双状态交替循环与 K1/K2 步数分配", "text": "For the first state, the model is trained on the alignment dataset for K1 steps, while for the second state, the model is trained on the fine-tuning dataset for K2 steps. The alternating between two states are repeated T cycles."},
    {"supports": "步骤 1-4 的设计思想：为什么在损失里加近端项", "text": "Our idea is to introduce a proximal term in the loss for each state, such that the optimization process becomes lazy, i.e., taking a smaller drift towards the checkpoint obtained in another state."},
    {"supports": "步骤 1 与步骤 3：近端参考点即上一次状态的切换检查点", "text": "Formally, the proximal term is defined as ∥w −wt∥2, i.e., the square of Euclidean distance between the current model weight and the switching checkpoint obtained by the last state."},
    {"supports": "步骤 2 与步骤 4：两个子问题分别用 K1/K2 步带近端项求解（式 (2)）", "text": "Formally, we derive two sub-problems for each state to solve. For alignment/fine-tuning state, we invest K1/K2 steps in solving the problem with a proximal term, as follows:"},
    {"supports": "步骤 3 的动机：切换检查点处的漂移越小越好", "text": "Our results indicate that BSO(900,100) achieves the smallest drift. Combining all the three sub-figures in Figure 2, a smaller drift seems to be preferable in terms of reducing alignment loss and ensuring a better convergence property."},
    {"supports": "第 6 节判定条件：ρ 与平滑常数 L 的关系", "text": "Under Assumptions 1-3, when the proximal intensity is chosen as ρ > L, and that a subsequence is converging to a cluster point, Lisa's rate of convergence of is:"},
    {"supports": "第 5 节默认超参数 K1/K2 与 ρ", "text": "The default setting of Lisa is as follows. The steps invested in Alignment/fine-tuning is 100/900, the proximal penalty ρ is 1."},
    {"supports": "第 8 节开销来源：近端项的前向/反向与相对 SFT/BSO 的增幅", "text": "We show in Table 7 that the clock time of Lisa is slightly increased by 8.3% compared to SFT, by 4.9% compared to BSO. The extra computation mainly comes from the forward/backward of the proximal term."}
  ]
}
```
