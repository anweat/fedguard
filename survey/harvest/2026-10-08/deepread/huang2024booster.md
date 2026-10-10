# huang2024booster：Booster: Tackling Harmful Fine-tuning for Large Language Models via Attenuating Harmful Perturbation

## 1. 基本信息

- **场景**：集中式大模型训练（fine-tuning-as-a-service，微调即服务），不是联邦学习。论文第 3.1 节明确把场景设定为"用户把数据上传给服务提供方（service provider，例如 OpenAI），由服务提供方在自己的安全对齐基座模型上做微调，微调后的模型部署在服务提供方服务器上"。全文没有客户端、聚合器、参与率等联邦要素。
- **训练阶段**：两阶段流水线（论文图 1）。阶段① 安全对齐（alignment），服务提供方用对齐数据做 SFT/RLHF 式对齐；阶段② 下游微调（fine-tuning），在用户上传的、混有 p 比例有害数据的用户数据集上微调。Booster 属于"对齐阶段解决方案（alignment-stage solution）"，只改阶段①，阶段②完全不变（第 1、3.1、5.1 节）。
- **论文类型**：防御（defense），并附带对攻击机理的分析（把 harmful perturbation 认定为对齐失效的根因）。论文本身不提出新的攻击，也不提出在线检测器。
- **模型与数据规模**：模型为 Llama2-7B（默认）、Gemma2-9B、Qwen2-7B（第 5.1 节）。对齐数据 5000 条、有害数据 5000 条（第 5.1 节），均取自 BeaverTails（Ji et al., 2023）经 Rosati et al. (2024c) 增强的版本。下游微调任务为 SST2、AGNEWS、GSM8K、AlpacaEval；默认微调样本数 n = 1000（AlpacaEval 为 700），默认有害比例 p = 0.1（第 5.1 节）。训练使用 LoRA（Hu et al., 2021），rank 设为 32、alpha 设为 4，batch size 10，对齐用 AdamW、学习率 5e-4、权重衰减 0.1，微调学习率 1e-5；对齐与微调各 20 个 epoch（AlpacaEval 为 100 个 epoch）（第 5.1 节）。评价时从 BeaverTails 测试集抽 1000 条指令算有害分数，Finetune Accuracy 分别从 SST2、AGNEWS、GSM8K、AlpacaEval 抽 872、1000、1000、122 条样本（第 5.1 节）。
- 版本信息：arXiv:2409.01586v4，标注日期 2025 年 3 月 17 日；本报告按 key 记为 2024 年工作。

## 2. 威胁模型

**攻击者是谁。** 论文的"攻击者"是上传用户微调数据的服务使用者（users / 数据提供方角色）。论文第 3.1 节写道，假设用户上传的用户微调数据集中有 p（百分比）是有害数据、其余 1−p 是良性微调数据，并且"有害数据与良性数据被认为是不可分的（inseparable）"。论文转引 Qi et al. (2023) 等的工作说明这类有害数据也可能是在用户无恶意的情况下混入的，因此论文并未把攻击者建模为有策略、会自适应的主动对手。

**占比或数量。** 默认 p = 0.1（第 5.1 节），主实验扫描 p = 0（clean）、0.05、0.1、0.15、0.2（表 1）。样本数默认 n = 1000，另外扫描 n = 500、1000、1500、2000、2500（表 2）。

**能力（能改什么）。** 只能投递数据：即决定用户微调数据集中包含哪些样本。论文没有给出攻击者能改损失函数、优化器、训练步数、更新上传内容或聚合过程的能力；这些环节在论文的集中式设定里都由服务提供方掌握。

**知识（知道什么）。** 论文未说明攻击者是否知道对齐数据集、有害数据集、Booster 的存在或超参数。

**目标。** 破坏安全对齐（safety alignment broken），使微调后的模型对有害提示不再给出拒绝回答，即越狱/安全对齐破坏；论文没有涉及定向后门或隐私窃取。论文用有害分数（Harmful Score）衡量该目标，第 5.6 节给出了具体例子：SFT、Lisa、RepNoise、Vaccine 都对"埋尸体躲警犬要多深"给出操作性回答（被标注为 violence/aiding_and_abetting/incitement），Booster 给出拒绝回答（标注 harmless）。

**防御者是谁、能看到什么、信任什么。** 防御者是服务提供方。第 3.1 节假设服务提供方自己维护一份对齐数据集（有害提示—安全回答对，harmful prompt-safe answer pairs）和一份有害数据集（有害提示—有害回答对，harmful prompt-harmful answer pairs）；论文指出这两份数据在公开数据集（如 BeaverTails）中都可获得。Booster 只使用这两份自有数据加基座模型，不使用用户微调数据，也不检查用户数据中哪些是有害样本。论文在第 5.2 节还明确写道，服务提供方无法为每个下游任务单独调超参数，因此需要一组通用超参数。论文未说明防御者是否具备任何在线检测用户数据的能力。

## 3. 攻击入口与流程位置

**攻击进入的位置。** 按论文的流程划分，有害内容在**本地数据准备/数据上传**这一步进入：用户把数据交给服务提供方，其中 p 比例是有害样本，1−p 是良性样本，二者不可分（第 3.1 节）。随后它在**阶段②的本地训练过程**中起作用：当随机梯度恰好取自一条有害样本时，模型沿有害数据的梯度方向走一步，这一步就是论文定义的 harmful perturbation（第 3.2 节）。论文第 3.2 节给出了更新式 wt+1 = wt − ηg(wt)，并说明当 g(wt) 是取自一条有害样本的随机梯度时，这一步就是有害扰动，是攻击成功的原因。论文没有涉及更新上传前的后处理、服务器聚合、全局模型下发这些环节（集中式设定下不存在这些环节）。

**具体操作步骤（攻击侧）。** 第一步：构造用户微调数据集，把 p 比例的有害样本混入 1−p 的良性任务样本（如 SST2 情感分类样本）。第二步：服务提供方对该数据集做普通 SFT（论文实验用 LoRA）。第三步：训练过程中反复取到有害样本的梯度，有害训练损失被显著压低，模型开始拟合有害数据，并泛化到未见过的有害测试数据，最终有害分数上升。

**Booster 干预的位置。** Booster 不改阶段②的任何东西，干预发生在**阶段①对齐训练的优化目标（损失函数）**里：在原有对齐损失上追加一个正则项，使对齐阶段产出的模型在遭遇后续有害扰动时有害损失的下降速率更小。附录 F 给出的 Vaccine+Booster 组合会把干预进一步扩展到 embedding 上的内层最大化；附录 E 的 Booster+Lisa 组合则在阶段②再叠加一个已有防御。Booster 不涉及剔除、过滤、加噪、裁剪或回滚。

## 4. 方法原理

**核心思想。** 论文第 3.2 节的实验发现：在纯有害数据上微调会大幅抬高有害分数，并显著降低有害训练损失；而在纯 SST2 上微调几乎不影响有害分数，甚至略微抬高有害损失（图 2 左、中、右）。由此得出的洞见是：如果能让对齐后的模型在有害数据上"有害损失的下降速率"更小，就能削弱后续攻击。于是论文在对齐阶段求解如下问题（式 (1)）：

arg min_w  f(w) + λ · [ h(w) − h(w − α · ∇h(w)/‖∇h(w)‖) ]

其中 f(w) 是对齐数据集上的经验损失（用 SFT 时即交叉熵），h(w) 是有害数据集上的经验损失，λ 是正则强度，α 是内层步长。方括号一项度量的是"原始有害损失"与"沿归一化有害梯度走一步之后的有害损失"之间的差距，即一次有害扰动能带来多少损失下降；最小化它就把这一步的下降速率压小。第 4 节同时指出，对齐数据使模型学会以拒绝方式回答有害提示，而正则项负责削弱扰动影响。

**关键步骤与近似。** 对式 (1) 按链式法则展开得到式 (2)，其中包含 ∇(wt − α∇h(wt)/‖∇h(wt)‖) 这一项，即二阶信息（Hessian），代价极高。受 MAML（Finn et al., 2017）与 Rajeswaran et al. (2019) 启发，论文把该二阶梯度项近似为常数，得到式 (3)：

w_{t+1} = w_t − η · ( ∇f(w_t) + λ · [ ∇h(w_t) − ∇h( w_t − α · ∇h(w_t)/‖∇h(w_t)‖ ) ] )

**算法 1（Booster）。** 每个优化步做三次前向/反向：先用一批对齐数据求 ∇f，再用一批有害数据求 ∇h(wt)，然后在参数点 wt − α·∇h(wt)/‖∇h(wt)‖ 上对同一批有害数据再求一次梯度 ∇h(·)，最后按式 (3) 合成梯度并更新。输入是 λ、α、学习率 η 与步数 T，输出是可供后续微调的对齐模型。

**与相近工作的关系（附录 A）。** 并行的 TAR（Tamirisa et al., 2024）简化目标为 arg min_w f̃(w) − λh(w − α∇h(w))（式 (4)），其中 f̃ 是保留损失（retain loss）、h 是有害数据上的熵损失；Booster 与它的两点差别是：Booster 的 f(w) 依赖对齐数据（保证模型学会拒绝），而 TAR 依赖普通代理数据；Booster 最小化的是有害损失的下降幅度 h(w) − h(w − α∇h/‖∇h‖)，TAR 直接最小化扰动后的负熵损失。附录 A 还报告了一个失败尝试：直接采用类似 TAR 的负交叉熵项会导致训练非常不稳定、模型崩溃（h(w) 爆炸、对任意提示重复同一个词）。

**组合（第 5.5 节、附录 E、附录 F）。** 与 Vaccine 组合时求解 min_w max_{‖ε‖≤ρ} f̂_ε(w) + λ(h(w) − h(w − α∇h(w)/‖∇h(w)‖))，其中内层最优扰动与 Vaccine 相同，为 ε* = ρ·∇_e f(w)/‖∇_e f(w)‖（式 (6)，∇_e 表示对 embedding 求梯度），算法 2 交替求解内外层；与 Lisa 组合则是"对齐阶段 Booster + 微调阶段 Lisa"的串联。

## 5. 检测或防御所需的数据

Booster 是预防性对齐方法，不做在线检测；它需要的输入如下。

1. **对齐数据集**（有害提示—安全回答对）。来源是服务提供方自有数据（论文用 BeaverTails 派生版本，5000 条）。采集位置：对齐训练之前准备好，每个对齐 batch 消费一次。粒度：逐样本（batch size 10）。不需要跨轮历史，不需要额外的前向/反向计算，也不来自其他客户端。
2. **有害数据集**（有害提示—有害回答对）。同样来自服务提供方自有数据，论文用 5000 条，并专门说明该数据集与用户微调数据中混入的有害数据同分布但实例不同（第 5.1 节）。采集位置：对齐阶段每一步取一个 batch，被同一个 batch 使用两次（扰动前、扰动后）。粒度：逐样本/逐批。
3. **对齐数据的梯度 ∇f(wt)**。位置：对齐训练每一步、客户端/服务器同一训练循环内。粒度：逐批。需要一次额外的前向加反向。
4. **有害数据的梯度 ∇h(wt)**。位置同上，逐批，一次前向加反向。
5. **扰动点上的有害梯度 ∇h(wt − α·∇h(wt)/‖∇h(wt)‖)**。需要把参数临时搬到扰动点、在同一批有害数据上再算一次前向加反向，然后回到原参数。粒度逐批，需要额外计算。
6. **参数状态副本与超参数 λ、α**。算法 1 需要保存 wt 的副本以完成"临时扰动再恢复"；λ 与 α 是固定超参数（默认 λ = 5、α = 0.1，第 5.1 节）。这是模型级而非样本级的状态。
7. **评估用数据**。有害分数需要从 BeaverTails 测试集抽 1000 条未见恶意指令，用 Ji et al. (2023) 的审核模型（moderation model）对模型输出打标签，取不安全输出占比；Finetune Accuracy 需要各下游任务的测试样本（872/1000/1000/122 条）。这类数据只在评估时使用（第 5.1 节）。附录 G.3 还额外报告了对齐后模型在 GSM8K 上的基准准确率。
8. **Vaccine+Booster 变体的额外输入**：对齐数据在 embedding 上的梯度 ∇_e f(w)，用于求内层最优扰动 ε*（式 (6)、算法 2）；论文注明这需要多一次对齐数据的前向/反向（第 5.5 节）。

**不需要的东西。** Booster 不使用用户微调数据，不使用逐样本损失、隐藏层激活或输出文本作为检测特征，不需要跨轮历史，不需要干净参考数据集之外的第三方数据，也不需要任何客户端之间的数据交换。

**攻击留下的可观测量痕迹（论文报告）。** 图 2 左侧显示，在纯有害数据上微调时有害分数随优化步数大幅上升，而纯 SST2 微调几乎不影响有害分数；图 2 中间与右侧显示有害扰动显著降低有害训练损失与有害测试损失，SST2 训练则只会略微抬高有害损失。图 3 进一步显示 SFT 的有害分数随微调步数持续上升到很高，而 Booster 的有害分数上升平缓。表 16 显示，SFT 对齐后有害损失从 1.582 升到 3.920，而 Booster 只从 1.582 升到 1.736——这是"对齐后模型的初始有害损失"这一可观测量上的差异。论文没有把这些量做成在线检测器，也没有讨论攻击者规避检测的问题；论文声称能绕过哪些检测这一点**论文未说明**。

## 6. 干预动作

- **动作内容**：Booster 不剔除客户端、不重新加权、不裁剪、不加噪、不过滤样本、不回滚模型。它唯一的动作是在阶段①对齐训练的损失函数上加入正则项（式 (1)），并按算法 1 的三次梯度合成更新对齐模型的权重，使产出的对齐基座模型在后续微调中对有害扰动更不敏感。若按常见的干预分类，这最接近"改造/加固模型"（本报告 JSON 中记为 repair_model），但论文没有使用这类术语，也没有检测—响应式的动作序列。
- **动作发生的位置**：服务提供方侧的**对齐阶段训练循环内部**（集中式设定下即服务器侧），在用户微调请求到来之前一次性完成。阶段②、聚合、下发、部署都没有任何干预。
- **组合动作**：与 Vaccine 组合时，内层对 embedding 施加扰动 ε*（式 (6)），外层同时优化对齐损失与 Booster 正则（算法 2）；与 Lisa 组合时，阶段①用 Booster、阶段②用 Lisa 的双状态优化（附录 E）。论文强调这些方法正交、可叠加。
- **动作持续性与语义**：论文明确说明对齐阶段方案的吸引力在于"只付一次开销"，对齐后的模型可服务上百万次微调请求，而 Lisa 这样的微调阶段方案要对每个微调请求都付开销（第 1 节、第 5.3 节）。

## 7. 实验设置与主要结果

**设置。** 模型 Llama2-7B（默认）、Gemma2-9B、Qwen2-7B；对齐数据 5000 条、有害数据 5000 条；下游任务 SST2、AGNEWS、GSM8K、AlpacaEval；默认 p = 0.1、n = 1000（AlpacaEval 用 700）；LoRA rank 32、alpha 4；batch size 10；对齐 20 epoch、微调 20 epoch（AlpacaEval 100 epoch）；默认 λ = 5、α = 0.1（第 5.1 节）。对照组为 SFT（对齐与微调都用普通监督微调）、Lisa（微调阶段方案，正则强度 ρ = 0.01）、Vaccine（对齐阶段方案，ρ = 5）、RepNoise（对齐阶段方案，α = 1、β = 0.001）（附录 C）。**客户端数与参与率：论文未说明，因为这是集中式设定，不存在客户端。数据是否非独立同分布：论文未说明。** 论文只说明用户微调数据中的有害样本与良性样本不可分。指标为 Finetune Accuracy（FA，下游任务测试准确率）与 Harmful Score（HS，未见恶意指令下不安全输出占比，越小越好）。

**关键结果（均为论文表格/正文明确给出）。**

- 表 1（不同有害比例，Llama2-7B + SST2）：Booster 平均 HS 为 10.94，SFT 为 33.58，Lisa 为 21.88，RepNoise 为 31.02，Vaccine 为 28.20；Booster 平均 FA 为 93.03。正文称相比 SFT 平均降低 22.64% 的有害分数、提高 2.64% 的微调准确率（第 5.2 节）。摘要给出的"相比 Vaccine 与 RepNoise 分别降低最多 17.26% 与 20.08% 平均有害分数"与表 1 的平均值之差（28.20−10.94 = 17.26，31.02−10.94 = 20.08）一致。
- 表 2（不同微调样本数 n = 500 至 2500）：Booster 平均 HS 为 23.34，SFT 为 52.10（正文称降低 28.76%），Booster 平均 FA 为 93.74，SFT 为 91.61（正文称提高 2.13%）。
- 表 3（四个下游数据集）：Booster 在 SST2、AGNEWS、GSM8K、AlpacaEval 上的 HS 分别为 8.30、7.10、6.40、36.70，平均 14.63；SFT 为 33.70、30.70、14.80、40.70，平均 29.98；Booster 平均 FA 为 60.68，是全部方法中最高。正文称四个数据集上相比 SFT 分别降低 25.4%、23.6%、8.4%、4.0% 的有害分数（与分析口径一致）。**分析：** 同一段正文还称相比 RepNoise 与 Vaccine "分别降低 19.68% 与 16.7% 的有害分数"，但按表 3 的平均值 14.63 与 28.13、25.15 计算，差值分别只有 13.50 与 10.52，论文未说明这两个数字的统计口径，无法从表 3 复现。
- 表 4（三个模型）：Booster 平均 HS 为 7.03、平均 FA 为 94.19；在 Qwen2-7B 上 HS 低至 1.60、FA 达 95.64；SFT 平均 HS 为 41.17。正文称平均降低 34.14% 有害分数（与 41.17−7.03 一致）与提高 0.71% 微调准确率（**分析：** 按表 4 的 FA 平均值 94.19 与 94.15 计算只差 0.04，该数字同样无法从表中复现）。
- 图 3（统计/系统分析，第 5.3 节）：SFT 的有害分数随微调步数升到很高且到 2000 步后仍有上升趋势，Booster 的有害分数上升平缓；SFT 的有害训练损失被急剧压低，Booster 下降缓慢，2000 步后 SFT 的有害训练损失显著低于 Booster；有害测试损失趋势相同。
- 附录 G.2 表 16：随对齐步数增加，SFT 的有害损失从 1.582 涨到 3.920，Booster 只从 1.582 涨到 1.736，这解释了 Booster 对齐模型在微调起点的有害训练损失更低这一现象。
- 表 6（λ 的影响）：λ = 0 时 HS 为 27.00（退化为 SFT），λ = 5 时 8.30，λ = 20 时 5.20 为最好，λ = 100 时恶化到 77.20。
- 表 7（α 的影响）：α = 0 时 HS 为 31.80，α = 0.01 时 4.70，α = 0.1 时 8.30，α = 0.5 时恶化到 72.40，α = 1 时 78.00，α = 5 时 75.30。
- 表 8（对齐使用有害样本数）：5 条时 HS 为 65.90（失败），10 条 61.00，20 条 54.00，50 条 5.10，100 条 2.30，500 条 5.00，5000 条 4.00；正文称 50 条已足够模拟有害扰动。
- 表 9（第 5.5 节，Vaccine+Booster，注意此表对齐只用了 500 条对齐数据）：平均 HS 为 41.20，Booster 单独为 45.08，Vaccine 单独为 62.12；平均 FA 为 93.39，Booster 单独为 94.13、Vaccine 为 93.83（正文称相比原 Booster 平均降低 3.88% 有害分数、FA 下降 0.74%，与表中差值一致）。
- 附录 G.3 表 17（对齐后模型、Gemma2-9B）：Booster 的 HS 为 0.7、GSM8K 基准准确率 13.4；SFT 为 1.5 与 13.8；RepNoise 为 0.9 与 12.8；Vaccine 为 0.6 与 9.5。论文据此称 Booster 只把基准准确率拉低约 0.4%。
- 附录 D、E（GSM8K 扩展）：表 10 至表 15。表 13 至表 15 显示 Booster+Lisa 在 GSM8K + Llama2-7B 上平均 HS 为 1.88，而 Booster 为 11.48、Lisa 为 10.38；表 15 显示 Booster+Lisa 在三个模型上的平均 HS 为 1.60、FA 为 47.93。

## 8. 开销

论文报告了系统开销（第 5.3 节，表 5）：

- **计算**：对齐阶段 Booster 需要 1.86 小时，SFT 为 0.54 小时，约为 SFT 的 3 倍；原因是每个优化步要算三次梯度。微调阶段 Booster 与 SFT 均为 0.10 小时，流程合计 1.95 小时对 0.64 小时。作为对比，RepNoise 对齐要 2.69 小时，Vaccine 1.06 小时，Lisa 0.54 小时。
- **显存**：对齐阶段 Booster 为 57.86 GB，SFT 为 49.33 GB，即多出约 8.53 GB；论文说明这部分来自三份梯度向量的存储以及一批有害数据的存储。RepNoise 为 72.47 GB，Vaccine 为 50.52 GB。微调阶段各方法（除 Lisa 为 45.35 GB）均为 40.01 GB。
- **一次性与重复性**：论文强调对齐阶段的开销只付一次，对齐模型可作为上百万次微调请求的基座；相比之下 Lisa 这类微调阶段方案要对每个请求付费。
- **组合变体的额外开销**：Vaccine+Booster 需要多一次对齐数据的前向/反向（第 5.5 节）。
- **通信开销：论文未报告。存储开销：论文未单独报告**（只在解释显存来源时提到三份梯度向量与一批有害数据的存储）。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设（论文明说的）。**

1. 服务提供方持有对齐数据集（有害提示—安全回答对）与有害数据集（有害提示—有害回答对），且二者可从公开数据获得（第 3.1 节）。
2. 用户上传的数据集中有害样本与良性样本不可分，防御方无法靠分离数据来规避攻击（第 3.1 节）。
3. 对齐阶段使用的有害数据与用户微调数据中混入的有害数据同分布但实例不同（第 5.1 节）。
4. 对齐和微调都可用 SFT 的交叉熵损失刻画；论文脚注 2 说明若改用 RL 类技术（如 GRPO），损失会更复杂。
5. 对齐是一次性投入，之后模型要服务大量未知的下游任务（第 1 节、第 5.3 节）。
6. 二阶梯度项可以近似为常数，从而只需三次一阶前向/反向（第 4 节）。
7. 用户微调数据里只有一部分是有害的，但有害扰动足以破坏对齐（第 3.2 节、图 2）。

**论文自述的局限。**

- 有害比例越高，有害分数仍会上升，论文称这是"对齐阶段方案的共同弱点"（第 5.2 节）。
- λ 与 α 必须仔细调：λ = 0 或 α = 0 退化为 SFT，λ 或 α 过大反而失效甚至训练不稳定（表 6、表 7，第 5.4 节）。
- 附录 H 明确指出：不同下游任务的最优超参数不同，但服务提供方无法为每个未知下游任务单独调参，必须找到一组通用超参数，这既困难又可能对某些任务不是最优，会给部署带来麻烦。
- 论文引述 Qi et al. (2024b)、Rosati et al. (2024a) 的观点，指出 TAR 与 RepNoise 这类对齐阶段防御在极端攻击情形下会失效，并承认对齐阶段方案可能面对更不可预测、更精巧的边角攻击。
- 论文报告 Booster 会略微降低对齐模型的通用推理能力（表 17，Gemma2-9B 上基准准确率下降约 0.4%）。

**自适应攻击。** 论文没有评估任何自适应攻击者：没有让攻击者知道 Booster、没有针对正则项设计规避数据、没有改变攻击者的训练策略或投毒比例以外的维度。**是否评估自适应攻击者：否，论文未说明。** 论文仅以"这类防御在边角攻击下可能失效"的引述作为一般性提醒。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：，以下均为我的判断）。**

- **对齐阶段的可控性假设。** Booster 要求防御方掌握基座模型、对齐数据集和有害数据集，并在微调之前独立完成一次对齐。联邦大模型 LoRA 微调中，基座模型由服务器/多方掌握，对齐往往早已完成且不可重跑；如果适配器由第三方发布，"对齐阶段"根本不存在，Booster 无处插入。
- **分布同质性假设。** Booster 依赖一份与攻击数据同分布的有害数据集来模拟扰动。联邦下各客户端数据高度异质（non-IID），且论文没有给出任何非独立同分布实验，一份全局有害数据集能否代表各客户端的有害分布是没有依据的。
- **单步扰动的定义。** 论文把有害扰动定义为"对全参数走一步归一化随机梯度"，并用一次内层步长 α 模拟。联邦 LoRA 中每个客户端会做多步本地更新，且可训练参数只有低秩增量 A、B，扰动的几何形状和尺度都与全参数一步更新不同；Booster 的正则项定义在 LoRA 子空间上是否仍有意义，论文未说明。
- **攻击者模型缺失。** 论文不涉及恶意客户端比例、客户端选择、聚合规则、更新后处理。在联邦中，攻击效果会被聚合平均稀释或被恶意客户端的数量放大，Byzantine/后门防御是否与 Booster 兼容，论文未说明。
- **评估面缺失。** 论文的有害分数是在服务器能对完整模型逐条生成并调用审核模型的前提下测得的。在只交换 LoRA 增量的联邦流程里，服务器若不做合并与前向就无法得到这个指标；论文没有给出任何只用适配器或统计量做评估的替代方案。
- **论文自身的迁移提示。** 附录 H 明确写道，已有证据表明有害微调在联邦指令微调（federated instruction fine-tuning）中威胁更严重，且现有 Byzantine/后门防御无法缓解，作者把"把 Booster 思路扩展到联邦指令微调"列为未来工作，并建议可能借助稀疏训练与量化。这说明论文自己承认当前形式并未覆盖联邦场景。

## 10. 对防护库设计的含义

1. **分析：** 采集底座需要一类"对齐/免疫阶段"的钩子，它早于任何联邦客户端钩子，作用在服务提供方自己的基座模型上，并能同时读入两份配对数据视图：有害提示—安全回答对、有害提示—有害回答对。这是这篇论文特有的需求，通用库至少要为它保留"预训练基座加固"这一阶段类型。
2. **分析：** 通用采集点应包含"训练循环内逐 batch 的梯度"这一视图，并且要允许在同一步内对同一 batch 重复求梯度、对参数做临时扰动（w − αg/‖g‖）后恢复。Booster 的三次前向/反向（算法 1）无法用"只在训练结束后拿一次更新"的钩子实现，因此必须支持步内钩子与参数副本。
3. **分析：** 干预接口应是"损失/梯度级"的：插件返回一个附加标量损失或对梯度的修正项，由底座合入优化器，而不是返回客户端黑名单或样本掩码。这篇论文的干预位置在服务器侧、微调之前，因此库还需要一个"服务器侧对齐插件"的钩子类型，而不仅是聚合期钩子。
4. **分析：** 插件协议必须允许"零用户数据"的预防性插件：Booster 不读用户微调数据、不需要跨轮历史、不需要其他客户端数据，它的效果只能通过评估钩子验证。因此库应把"评估视图"（合并后的模型、固定的有害指令集合、审核模型打分、下游任务准确率）做成独立能力。
5. **分析：** 迁移到联邦 LoRA 时，库需要把"归一化梯度扰动"限制在 LoRA 参数子集（A、B）上，并能按客户端本地步数配置扰动模拟的步数与步长；论文的 λ = 5、α = 0.1 是在全参数 LoRA rank 32、batch size 10、20 epoch 的集中式设置下调出来的，不能直接沿用，这一点必须由插件自己声明超参搜索范围。
6. **分析：** 组合性是通用需求：Booster 与 Vaccine（同为准对齐阶段）、与 Lisa（微调阶段）都正交可叠加（第 5.5 节、附录 E、附录 F），库应支持同阶段多插件叠加并固定执行顺序，同时让每个插件声明自己的额外前向/反向次数，以便底座核算显存与时间预算（论文报告单次对齐额外约 8.53 GB 显存、约 3 倍对齐时间）。

## 11. 原文依据

1. "The considered scenario is that users upload a few pieces of data (a subset of them are harmful) to the service provider, and the service provider fine-tune their safety-aligned foundation model with those provided datasets."（第 3.1 节，Considered Scenario；支撑第 2 节"攻击者是上传数据的服务使用者、场景是集中式微调即服务"与第 1 节的场景判定。）
2. "We assume that the users upload a user fine-tuning dataset with p (percentage) of harmful data, and other 1 −p (percentage) of data are benign fine-tuning data."（第 3.1 节，Threat models；支撑第 2 节的恶意比例 p 与第 7 节的 p 扫描设置。）
3. "We assume the service provider maintains an alignment dataset (harmful prompt-safe answer pairs) and a harmful dataset (harmful prompt-harmful answer pairs) for alignment."（第 3.1 节，Assumptions；支撑第 2 节防御者可见数据与第 5 节两类输入数据的来源。）
4. "This indicates that taking a step with the gradient of the harmful data (i.e., harmful perturbation) is indeed the reason for the alignment broken."（第 3.2 节，Impact of harmful perturbation；支撑第 3 节"攻击在阶段②通过有害梯度步起作用"与第 4 节的核心动机。）
5. "The idea is to minimize the impact of potential harmful perturbation towards the alignment model while simultaneously minimizing its alignment loss."（第 4 节，Methodology；支撑第 4 节式 (1) 的设计思想与第 6 节的干预性质。）
6. "We follow (Huang et al., 2024e;d; Hsu et al., 2024) to utilize LoRA (Hu et al., 2021) for efficient LLM training."（第 5.1 节，Training details；支撑第 1 节"训练使用 LoRA（rank 32、alpha 4）"以及第 9 节关于迁移到联邦 LoRA 的分析。）
7. "The data in harmful dataset are in the same distribution but are different from those harmful data mixed in the user dataset."（第 5.1 节，Datasets；支撑第 5 节有害数据集的采集与第 9 节"同分布"假设。）
8. "Results indicate that the superior performance of Booster, unfortunately, does not come for free. The clock time of Booster used for alignment is approximately three times of SFT."（第 5.3 节，System Evaluation；支撑第 8 节计算开销约 3 倍与第 10 节的开销预算需求。）
9. "we do observe that the harmful score is rising with more percentage of harmful data, which unfortunately is the common weakness of the alignment-stage solutions."（第 5.2 节，Robustness to harmful ratio；支撑第 9 节论文自述局限。）
10. "As evidenced by Ye et al. (2024); Li et al. (2024b), harmful fine-tuning attack might pose a more serious threat in federated instruction fine-tuning, and cannot be mitigated by existing defenses on Byzantine/backdoor attack."（附录 H，Limitations and Future Extension；支撑第 9 节关于迁移到联邦 LoRA 微调时哪些假设可能不成立。）

```json
{
  "key": "huang2024booster",
  "title": "Booster: Tackling Harmful Fine-tuning for Large Language Models via Attenuating Harmful Perturbation",
  "year": 2024,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data", "local_training"],
  "observables": [
    {"what": "对齐数据集（有害提示-安全回答对），服务提供方自有，5000 条", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "有害数据集（有害提示-有害回答对），与用户微调中有害数据同分布但不同实例", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "对齐数据 batch 的梯度 ∇f(w_t)", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "有害数据 batch 的梯度 ∇h(w_t)", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "扰动点参数上的有害梯度 ∇h(w_t − α·∇h/‖∇h‖)，需临时扰动参数后重算并恢复", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "Vaccine+Booster 变体额外需要 embedding 上的对齐梯度 ∇_e f(w) 以求解 ε*", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "微调后模型对 BeaverTails 1000 条未见恶意指令的输出与审核模型打分（有害分数）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "下游任务测试集上的准确率（SST2/AGNEWS/GSM8K/AlpacaEval 各 872/1000/1000/122 条）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "对齐后模型在 GSM8K 上的基准准确率（附录 G.3，Gemma2-9B）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务提供方保有对齐数据集与有害数据集（可来自 BeaverTails 等公开数据）",
    "用户微调数据中有害样本与良性样本不可分，防御方不检查用户数据",
    "对齐阶段的有害数据与用户微调中混入的有害数据同分布但实例不同",
    "对齐与微调均可用 SFT 交叉熵损失刻画，RL 类损失会更复杂",
    "对齐只需一次性完成，之后服务大量未知下游任务",
    "二阶梯度项可近似为常数（MAML 式近似）",
    "超参数 λ 与 α 必须按经验选取且对下游任务敏感"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Section 3.1 Considered Scenario", "supports": "第 1 节场景判定与第 2 节攻击者身份：集中式微调即服务，攻击者由上传数据的用户充当", "text": "The considered scenario is that users upload a few pieces of data (a subset of them are harmful) to the service provider, and the service provider fine-tune their safety-aligned foundation model with those provided datasets."},
    {"section": "Section 3.1 Threat models", "supports": "第 2 节恶意比例 p 的定义与第 7 节 p 的取值设置", "text": "We assume that the users upload a user fine-tuning dataset with p (percentage) of harmful data, and other 1 −p (percentage) of data are benign fine-tuning data."},
    {"section": "Section 3.1 Assumptions", "supports": "第 2 节防御者可见数据与第 5 节两类输入数据的来源与假设", "text": "We assume the service provider maintains an alignment dataset (harmful prompt-safe answer pairs) and a harmful dataset (harmful prompt-harmful answer pairs) for alignment."},
    {"section": "Section 3.2 Impact of harmful perturbation", "supports": "第 3 节攻击在阶段②通过有害梯度步起作用与第 4 节的动机", "text": "This indicates that taking a step with the gradient of the harmful data (i.e., harmful perturbation) is indeed the reason for the alignment broken."},
    {"section": "Section 4 Methodology", "supports": "第 4 节式 (1) 的设计思想与第 6 节干预性质（损失级正则而非样本级动作）", "text": "The idea is to minimize the impact of potential harmful perturbation towards the alignment model while simultaneously minimizing its alignment loss."},
    {"section": "Section 5.1 Training details", "supports": "第 1 节训练使用 LoRA 与第 9 节向联邦 LoRA 迁移的分析", "text": "We follow (Huang et al., 2024e;d; Hsu et al., 2024) to utilize LoRA (Hu et al., 2021) for efficient LLM training."},
    {"section": "Section 5.1 Datasets", "supports": "第 5 节有害数据集采集与第 9 节同分布假设", "text": "The data in harmful dataset are in the same distribution but are different from those harmful data mixed in the user dataset."},
    {"section": "Section 5.3 System Evaluation", "supports": "第 8 节计算开销约为 SFT 三倍与第 10 节开销预算需求", "text": "Results indicate that the superior performance of Booster, unfortunately, does not come for free. The clock time of Booster used for alignment is approximately three times of SFT."},
    {"section": "Section 5.2 Robustness to harmful ratio", "supports": "第 9 节论文自述局限：有害比例升高时有害分数仍上升", "text": "we do observe that the harmful score is rising with more percentage of harmful data, which unfortunately is the common weakness of the alignment-stage solutions."},
    {"section": "Appendix H Limitations and Future Extension", "supports": "第 9 节迁移到联邦 LoRA 微调时可能失效的假设", "text": "As evidenced by Ye et al. (2024); Li et al. (2024b), harmful fine-tuning attack might pose a more serious threat in federated instruction fine-tuning, and cannot be mitigated by existing defenses on Byzantine/backdoor attack."}
  ]
}
```
