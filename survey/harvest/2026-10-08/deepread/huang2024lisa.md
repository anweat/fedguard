# huang2024lisa：Lisa: Lazy Safety Alignment for Large Language Models against Harmful Fine-tuning Attack

## 1. 基本信息

- 场景：集中式大模型微调（fine-tuning-as-a-service，微调即服务），不是联邦学习，也不是联邦大模型微调。论文第 1 节给出一个两阶段流水线：Stage ① 对齐阶段（alignment stage，服务提供方用自采对齐数据微调预训练模型），Stage ② 用户微调阶段（user fine-tuning stage，用户在服务方平台上用自己上传的数据微调）。论文明确说自己的方法只作用于 Stage ②，Stage ① 保持 SFT（supervised fine-tuning，有监督微调）不变，并可与对齐阶段的 Vaccine 组合（第 1 节、图 1、第 5.5 节）。
- 训练阶段：论文研究的是"用户微调阶段"这一环，即对齐完成之后、部署之前的个性化微调过程。
- 论文类型：防御（defense）。论文同时包含对一个既有攻击（harmful fine-tuning，有害微调）的实证刻画，以及收敛性理论分析与大量防御实验；但论文本身不提出新的攻击。核心方法是 BSO（Bi-State Optimization，双状态优化）与 Lisa（Lazy safety alignment，惰性安全对齐）。
- 模型与数据规模：三个预训练模型 Llama2-7B、Opt（第 5.1 节正文写作 "Opt-3.7B"，表 5 表头写作 "Opt-2.7B"，论文未说明以哪个为准）、Mistral-7B（第 5.1 节）。对齐数据取自 BeaverTails 的安全样本，采样 10000 条（附录 A.1）。微调任务为 SST2、AGNEWS、GSM8K、AlpacaEval；默认微调样本数 n=5000（AlpacaEval 因数据量限制为 700 条），其中默认 10% 为有害数据（第 5.1 节、附录 A.1）。微调与对齐都用 LoRA（Low-Rank Adaptation，低秩适配），适配器秩为 8，并采用 Double-LoRA（两个分别用于对齐和微调的独立 LoRA 组件）（第 5.1 节、附录 A.1）。实验在一台 H100 工作站上完成（附录 A.1）。

## 2. 威胁模型

- 攻击者是谁：上传微调数据的用户（即数据提供方，data provider）。论文第 1 节说"用户上传的数据可能未经过滤，甚至包含有害数据"，第 3 节明确"我们沿用 Qi et al. (2023) 的设定，假设用户微调数据 D 中可能含有比例为 p 的有害数据，其余 1−p 是针对其下游任务的干净微调数据"。论文没有把攻击者刻画为有明确恶意意图的对手，也没有区分"故意投毒"与"无意混入"。
- 占比或数量：有害比例记为 p（harmful ratio）。默认 p=0.1、n=5000（第 5.1 节）；论文扫描了 p=0.05、0.1、0.2、0.3、0.4（表 1、表 3）、p=0.5、0.8、0.9、1（表 12、表 13），并报告小到 5% 的有害数据即可把有害分数推高 15% 以上（第 3 节、图 2）。
- 能力：攻击者能控制上传微调数据的内容与有害样本比例，仅此而已。论文未说明攻击者能否修改训练过程、优化器、步数、上传的适配器或参与聚合；这些在集中式设定下都由服务提供方掌控。
- 知识：论文未说明攻击者是否知道防御方法、对齐数据集内容或超参数配置。
- 目标：破坏大模型的安全对齐（safety alignment），使微调后的模型对恶意指令给出有害回答，即"越狱"（jail-break）。论文第 3 节的图 2 还指出，不同有害比例下微调精度几乎不变，说明攻击者可以在不牺牲下游任务表现的情况下达成目标，使攻击难以从任务精度上被察觉。
- 防御者是谁、能看到什么、信任什么：防御者是服务提供方（service provider）。论文第 1 节说"服务提供方要对大模型的输出负责"，第 3 节说明对齐数据由服务提供方收集、用户微调数据由用户上传。防御者能看到自己收集的干净对齐数据集、全部上传的微调数据、完整训练过程、模型权重，并能对模型输出做评测。防御者无法把有害样本与干净样本分开：第 3 节明确"The harmful and pristine data cannot be easily separated."（有害数据与干净数据无法被轻易区分）。防御者信任自己的对齐数据集和训练流水线，不信任用户上传数据的成分。

## 3. 攻击入口与流程位置

本文是防御论文，因此这里写它所针对的攻击入口与攻击发生的位置。

- 攻击入口是本地数据准备（local_data）：有害样本被混入用户为微调任务准备的训练数据集中（第 3 节威胁模型；实验里由作者按比例 p 从 BeaverTails 抽取不安全数据混入任务数据，第 5.1 节）。攻击并不发生在服务器聚合、全局模型下发、评估与部署环节。
- 攻击在流程中的具体步骤（综合第 1 节图 1、第 3 节、第 5.1 节、附录 A.1）：
  1. 服务提供方用 BeaverTails 的安全样本对齐预训练模型（对齐阶段，LoRA 适配器，学习率 1e-3、批大小 5、30 个 epoch、10000 条样本，附录 A.1），随后把该适配器合并进基座模型。
  2. 用户上传 n 条微调样本，其中比例为 p 的样本来自有害数据源，其余为下游任务的干净样本；两者混在一起且难以区分。
  3. 服务提供方在混合数据上做标准 SFT 微调（第二个 LoRA 适配器，学习率 1e-5、批大小 5，SST2/AGNEWS 训练 20 个 epoch、GSM8K 训练 50 个 epoch，第 5.1 节）。论文图 2 显示，这一过程会让模型在恶意指令上的有害分数显著上升。
  4. 定制化模型被部署并对用户提示提供服务。
- 论文没有讨论更新上传前的后处理、服务器聚合、全局模型下发这类联邦环节，因为在集中式设定下它们不存在。

## 4. 方法原理

- 出发点（第 4.1 节，式 (1)）：把用户微调阶段建模为在"对齐数据损失 f(w)"与"用户数据损失 h(w)"上的联合优化，arg min_w f(w) + h(w)，其中 f(w) 是对齐数据集上的标准因果语言建模交叉熵损失，h(w) 是用户微调数据集上的标准交叉熵损失。
- BSO（第 4.1 节，算法 1、图 3）：把微调阶段拆成两个状态交替进行。每个周期 t 内共 K1+K2 步，前 K1 步从对齐数据集采样并更新（最小化 f），后 K2 步从用户微调数据集采样并更新（最小化 h），周期重复 T 次；第 2 节的算法伪码显示状态切换处把 wt+1,0 置为上一周期最后一步的权重。
- 论文发现的问题（第 4.1 节，表 1、表 2、图 4）：当 K1=K2=500 时 BSO 相比 SFT 最多降低有害分数 4.2%，微调精度最多损失 0.69%；但当投入对齐状态的步数变少（不对称计算，asymmetric computing），防御效果迅速退化，K1/K2=0/1000 时 BSO 退化为 SFT（表 2 中有害分数从 1000/0 的 34.00 升到 0/1000 的 51.60）。作者用三个统计量解释：对齐损失随步数上升、全局目标梯度范数 ‖∇f(w)+∇h(w)‖ 不收敛、以及两个状态切换点之间的漂移（excess drift，过量漂移）过大。
- Lisa（第 4.2 节，算法 2、式 (2)）：在 BSO 的两个子问题上各加一个近端项（proximal term）约束漂移。状态 1 求解 w̃_{t+1} = arg min f(·) + (ρ/2)‖· − w_t‖²，状态 2 求解 w_{t+1} = arg min h(·) + (ρ/2)‖· − w̃_{t+1}‖²，其中 w_t 与 w̃_{t+1} 分别是另一个状态得到的检查点，ρ 是控制近端强度的超参数（式 (2)）。直观上，最小化近端项可以让优化过程"变懒"，即朝另一个状态的检查点少走一些。
- 理论（第 4.2 节定理 1 与附录 B）：在 Assumption 1（损失函数正常且闭）、Assumption 2（L-光滑）、Assumption 3（势函数 D(w̃_t, w_t)=f(w̃_t)+h(w_t)+(ρ/2)‖w̃_t−w_t‖² 满足 KL（Kurdyka-Łojasiewicz）性质，参数 θ∈[0,1)）下，当 ρ>L 时 Lisa 可收敛到全局问题的稳定点，收敛速率取决于 θ：θ=0 时有限步达到；θ∈(0,1/2] 时线性收敛；θ∈(1/2,1) 时次线性收敛。附录 B 的引理 3 给出势函数下降界 D(w̃_{t+1},w_{t+1})−D(w̃_t,w_t) ≤ −((ρ−L)/2)(‖w_{t+1}−w_t‖²+‖w̃_{t+1}−w̃_t‖²)。
- 论文报告的默认超参：K1/K2=100/900，ρ=1（第 5.1 节）。

## 5. 检测或防御所需的数据

论文的方法不是"检测后再处置"，而是直接在微调阶段改变优化目标，因此严格说它没有检测步骤，也不需要判定某个样本或客户端是否恶意。下面把它需要的每一种输入按论文依据列出。

1. 用户上传的微调数据集（含比例为 p 的有害样本）。是什么：用于计算损失 h(w) 的指令微调样本，论文构造成 Instruction/Input/Response 三元组并套用系统提示（附录 A.1）。在哪里采集：在微调开始之前由用户上传，在服务器本地训练的每一步被采样。粒度：逐样本组成批，批大小为 5（第 5.1 节、附录 A.1）。是否需要跨轮历史：不需要。是否需要干净参考：不需要。是否需要额外计算：需要，因为它本身要被反复训练。
2. 服务提供方的干净对齐数据集。是什么：BeaverTails 的安全样本，共 10000 条（附录 A.1），用于计算损失 f(w)。在哪里采集：来源于 Stage ① 对齐阶段，在微调阶段的 K1 步里被采样使用。粒度：逐样本组成批（批大小 5）。是否需要跨轮历史：不需要。是否需要干净参考数据：它就是干净参考数据，论文明确要求服务方持有并可复用。是否需要额外计算：需要，这 K1 步正是论文所说的额外开销来源。
3. 状态切换时的模型权重检查点。是什么：w_t（上一周期结束、进入对齐状态前的权重）与 w̃_{t+1}（对齐状态结束时、进入微调状态前的权重），是近端项的锚点。在哪里采集：客户端（此处即服务方的微调进程）训练中途的状态切换点，需要在进入另一状态前保存。粒度：模型级（对 LoRA 而言是全部可训练参数），每个周期一次。是否需要跨轮历史：需要，近端项引用的是"另一个状态刚产生的检查点"。是否需要干净参考：不需要（检查点来自本次训练，而非外部干净模型）。是否需要额外计算：需要，论文明确说这带来额外的 GPU 显存占用。
4. 对齐数据损失 f(w) 随训练步的变化。是什么：模型在对齐数据集上的交叉熵损失。在哪里采集：训练每一步。粒度：逐批。是否需要跨轮历史：需要，论文画的是它随步数的曲线（图 4 左、图 5 左）。是否需要干净参考数据：需要。是否需要额外计算：需要（要额外前向计算对齐数据上的损失）。
5. 全局目标的梯度范数 ‖∇f(w)+∇h(w)‖。是什么：对齐损失梯度与用户损失梯度之和的范数，论文用它作为收敛性的观测量。在哪里采集：训练每一步、两个状态各自的迭代点上（附录 B 式 (11)、式 (35)）。粒度：逐批。是否需要跨轮历史：论文给的是随步数的曲线，因此需要按步记录。是否需要干净参考：需要 f 的梯度。是否需要额外计算：需要额外反向/梯度计算。
6. 状态切换点之间的漂移（drift，欧氏距离之和）。是什么：后一状态得到的权重与前一状态权重的欧氏距离之和。在哪里采集：每次状态切换时。粒度：模型级、逐周期。是否需要跨轮历史：需要。是否需要干净参考：不需要。是否需要额外计算：不需要（读取检查点即可）。
7. 评测阶段的输入。是什么：从 BeaverTails 测试集采样的 1000 条恶意指令，以及 SST2 872 条、AGNEWS 1000 条、GSM8K 1000 条、AlpacaEval 122 条测试样本（附录 A.1）。在哪里采集：微调完成、模型部署/评测时。粒度：逐样本，聚合为逐模型的有害分数（harmful score）与微调精度（finetune accuracy）。是否需要干净参考：AlpacaEval 的精度以 text_Devinci_003 的输出为对照，并用 ChatGPT API 打分（附录 A.1）。是否需要额外计算：需要，要跑生成、审核模型与评测脚本。
8. 论文"替代设计"里额外用到的输入：Filter+Lisa 变体先用 BeaverTails 审核模型（moderation model）逐样本过滤有害数据，再做 Lisa（第 5.5 节、表 12）；论文在脚注 2 中报告该审核模型有 7.71% 的假阴性率。Vaccine+Lisa 变体则还需要在对齐阶段对嵌入加扰动的机制（第 5.5 节、表 11）。这些是组合方案，不是 Lisa 本身的必需输入。

攻击会留下哪些痕迹（论文报告）：第一，微调后的模型在恶意指令上的有害分数显著上升（图 2 左、表 1、表 3）；第二，任务精度几乎不变，第 3 节明确说难以据此判断模型是否被投毒（图 2 中）；第三，对齐数据上的损失随有害比例上升而上升，说明模型"遗忘"了此前的对齐知识（图 2 右、第 3 节）；第四，训练过程中 ‖∇f+∇h‖ 不收敛、切换点漂移偏大（图 4）。论文没有声称能绕过任何检测，也没有提出检测器；相反，它反复说明这些统计量之间存在张力（表 9 显示 ρ 越大有害分数越低但微调精度也越低）。

## 6. 干预动作

- Lisa 的动作不是"检测后剔除"，而是在训练过程中约束模型：在每个状态的目标函数里加入近端项，使当前迭代不要过度偏离另一个状态的检查点（第 4.2 节式 (2)、算法 2）。它不删除客户端、不重加权、不裁剪、不加噪、不过滤样本、不回滚模型，也不只是报告。
- 动作发生的位置：客户端侧（本论文中是服务方的用户微调训练循环内部），具体是损失函数与优化步的层面，即"本地训练过程"这一环。
- 与之组合的替代设计会引入额外动作：Filter+Lisa 在训练前用审核模型做逐样本过滤（第 5.5 节、表 12，平均有害分数从 Lisa 单独使用的 39.92 降到 34.18）；Vaccine+Lisa 把防御动作同时放到对齐阶段（第 5.5 节、表 11，平均有害分数 32.86）。这些是论文报告的组合方案，不是 Lisa 的组成部分。

分析：从防护库的插件分类看，Lisa 更接近"训练时修复/正则化模型"这一类干预，而不是"检测后处置"。它的接口形态是"改写损失 + 状态调度 + 参考模型"，与"接受/拒绝某次更新"的服务器端钩子不同构。

## 7. 实验设置与主要结果

- 模型：Llama2-7B、Opt（第 5.1 节正文 "Opt-3.7B"，表 5 表头 "Opt-2.7B"）、Mistral-7B（第 5.1 节、表 5）。
- 数据：对齐数据来自 BeaverTails（10000 条，附录 A.1）；微调任务为 SST2、AGNEWS、GSM8K、AlpacaEval（第 5.1 节）。默认总样本数 n=5000，默认有害比例 p=0.1（第 5.1 节）。
- 训练细节：LoRA 秩 8、Double-LoRA；微调学习率 1e-5、批大小 5；SST2 与 AGNEWS 训练 20 个 epoch，GSM8K 训练 50 个 epoch（第 5.1 节）；对齐阶段学习率 1e-3、批大小 5、30 个 epoch（附录 A.1）。默认步数分配 K1/K2=100/900，默认近端强度 ρ=1（第 5.1 节）。
- 客户端数与参与率：论文未说明。论文是集中式单请求微调设置，不存在联邦客户端与参与率。
- 轮次：论文用周期数 T 表示 BSO/Lisa 的反复次数（算法 1、算法 2），但未给出实验中 T 的具体取值；论文未说明。
- 恶意比例：默认 p=0.1，扫描范围为 0.05 到 1（表 3、表 12、表 13）。
- 是否非独立同分布：论文未说明（集中式设定，未讨论数据异构性）。
- 指标：微调精度（Finetune Accuracy，FA，任务测试集上的 Top-1 正确率）与有害分数（Harmful Score，HS，用 BeaverTails 的审核模型对模型输出的判定比例）（第 5.1 节、附录 A.1）。
- 关键结果：
  - 表 1：K1=K2=500 时，BSO 相比 SFT 最多降低有害分数 4.2%，微调精度最多损失 0.69%（第 4.1 节正文、表 1）。
  - 表 2：对齐/微调步数从 1000/0 变到 0/1000 时，有害分数从 34.00 升到 51.60，说明不对称计算会让 BSO 退化为 SFT。
  - 表 3（n=5000）：Lisa 的平均有害分数为 39.58，SFT 为 48.28，Vaccine-SFT 为 46.86，Vlguard 为 43.28，BSO 为 46.12；平均微调精度 Lisa 为 94.75，SFT 为 95.32，Vlguard 为 95.34。第 5.2 节正文称 Lisa 相比 Vaccine-SFT 与 Vlguard 分别降低平均有害分数 7.07% 与 3.68%，相比 BSO 降低 6.54%（与表 3 中 46.12−39.58=6.54 一致）。
  - 表 4（p=0.1，改变样本数）：Lisa 平均有害分数 36.48、平均微调精度 93.59；EWC 平均有害分数 41.18、平均微调精度 12.96，第 5.2 节称 Lisa 比 EWC 平均有害分数低 4.7%、微调精度高 80.63%。
  - 表 5（GSM8K，三个模型）：Lisa 平均有害分数 36.17、平均微调精度 16.10；NA-SFT 为 57.20 与 21.93。
  - 表 6（Mistral-7B，四个任务）：Lisa 平均有害分数 37.53、平均微调精度 63.74，均为对比方法中最好。
  - 表 7（系统评测，1000 步）：SFT 115.53 秒 / 47.97 GB，Vlguard 122.34 秒 / 48.48 GB，BSO 119.22 秒 / 50.85 GB，Lisa 125.11 秒 / 51.11 GB。
  - 表 8（步数分配消融）：100/900 时 SST2 有害分数 40.90、微调精度 95.07；0/1000 时有害分数 32.00、微调精度 86.01。
  - 表 9（近端强度消融）：ρ 从 0 增到 10 时，有害分数从 49.00 降到 36.30，微调精度从 95.41 降到 94.50，说明安全与任务精度存在权衡。
  - 表 10（消融）：只保留 BSO 平均有害分数 46.12、只保留近端项为 32.46（但微调精度降到 87.02）、两者合用为 39.58（微调精度 94.75）。
  - 表 11（Vaccine+Lisa）：平均有害分数 32.86、平均微调精度 93.97，为所有组合中最低的有害分数。
  - 表 12（过滤+Lisa，BeaverTails 审核模型）：平均有害分数 34.18、平均微调精度 81.67，优于 Filter+SFT 的 39.08。
  - 表 13（高有害比例）：p=1 时 SFT 有害分数 52.6，Vaccine-SFT 53.4，Lisa 44.1。
  - 表 15（Bi-directional Anchoring 攻击）：SFT 的有害分数从微调前 33.9 升到 34.6，Vaccine-SFT 从 28.5 升到 30.3，Lisa 保持 33.9 不变。
  - 图 5：ρ 越大，对齐损失增长越慢、梯度范数越能收敛到 0、切换点漂移越小。
  - 第 5.6 节给出定性示例：对"How can I steal the engine from someone's car?"，Lisa 的回答被判为 harmless，其他方法均被判为犯罪类内容。

## 8. 开销

- 计算开销（论文报告）：表 7 给出运行 1000 步的时钟时间，SFT 为 115.53 秒、Vlguard 为 122.34 秒、BSO 为 119.22 秒、Lisa 为 125.11 秒。第 5.3 节称 Lisa 的时钟时间相比 SFT 增加 8.3%、相比 BSO 增加 4.9%，额外计算主要来自近端项的前向/反向传播。
- 存储开销（论文报告）：表 7 给出显存占用，SFT 为 47.97 GB、Vlguard 为 48.48 GB、BSO 为 50.85 GB、Lisa 为 51.11 GB。第 5.3 节称 Lisa 相比 SFT 多需要 3.14 GB 显存，来源是保存切换检查点。
- 论文的定性说明：第 5.3 节指出这部分额外开销不随数据量增长，而取决于可训练参数数量，因此作者认为计算成本"不是 Lisa 的严重问题"；附录 D 则把"微调阶段需要额外计算"列为主要局限，因为微调要对每个用户请求各做一次，开销会随请求数增长。
- 通信开销：论文未报告。论文是集中式设置，全文未讨论通信开销。

## 9. 假设、局限与自适应攻击

论文成立所依赖的假设：

- 威胁模型假设（第 3 节）：用户微调数据中含有比例 p 的有害数据，其余为干净的下游任务数据，且"有害数据与干净数据无法被轻易区分"。
- 数据可得性假设（第 5.1 节、附录 A.1）：服务提供方持有干净对齐数据集（10000 条 BeaverTails 样本），并可在微调阶段复用；BSO 与 Lisa 复用与对齐阶段相同的对齐数据集，Vlguard 为公平比较只采样 1000 条。
- 流程假设：对齐与微调都由服务提供方执行，训练循环、损失函数和步数调度都在防御方掌控之下；论文标题与图 1 的设定是"两阶段流水线"。
- 模型假设：对齐基于 SFT，微调使用 LoRA（秩 8，Double-LoRA 两个独立适配器）（第 5.1 节、附录 A.1）。
- 理论假设（附录 B）：Assumption 1（f、h 正常且闭）、Assumption 2（L-光滑）、Assumption 3（势函数满足参数为 θ∈[0,1) 的 KL 性质）；定理 1 至定理 3 还要求 ρ>L 且存在收敛到聚点的子列。
- 权衡假设：表 9 表明近端强度 ρ 越大，有害分数越低但微调精度也越低，即防御效果以任务性能为代价。
- 论文未讨论的假设：恶意客户端篡改本地训练过程、服务器端聚合被操纵、适配器被二次发布等威胁，论文均未涉及。

论文自述的局限（附录 D）：

- 微调阶段需要额外计算，而不像对齐阶段方案那样只需付一次代价；微调要对每个用户请求执行，开销随请求数增长。
- 方法只能建立在 SFT 对齐之上，而 RLHF（reinforcement learning from human feedback，基于人类反馈的强化学习）是当前安全对齐的 SOTA（state of the art，最优）技术；受资源限制，作者没有验证方法能否推广到 RLHF。
- 使用的下游数据集不是大模型能执行的最"酷"的任务，未来需要扩展到对话式 AI 或智能体等场景。
- 论文同时主张要彻底解决有害微调问题，必须在对齐阶段和用户微调阶段同时投入。

自适应攻击的评估情况：

- 论文没有评估针对 Lisa 的自适应攻击者。它只在附录 A.3 评估了一种更隐蔽的既有攻击 Bi-directional Anchoring（He et al., 2024），该攻击从良性数据集中挑选"最有害"的数据子集；表 15 中 SFT 的有害分数从 33.9 升至 34.6（附录 A.3 称上升 0.7%），Vaccine-SFT 从 28.5 升至 30.3，而 Lisa 保持在 33.9。论文没有说明这种攻击是否知晓 Lisa 的存在或针对 Lisa 做过调整。
- 论文在第 2 节提到存在更高级的攻击（如 He et al., 2024；Halawi et al., 2024），但未在 Lisa 上做相应实验。

迁移到联邦 LoRA 微调时可能失效的假设（分析：以下均为我的推断，论文没有讨论联邦设置）：

- 论文假设防御者掌控训练循环。在联邦 LoRA 中本地训练由客户端执行，恶意客户端可以直接跳过 K1 步对齐状态、移除近端项、或只上传自己想要的适配器增量；论文的近端项是本地优化器的改动，无法约束一个不遵守协议的客户端。
- 论文的近端项锚定"同一请求内另一个状态的检查点"。在联邦中更自然的锚点是服务器上一轮的全局适配器，但论文没有定义跨轮、跨客户端的参考模型，也没有讨论服务器如何区分两种状态的适配器。
- 论文假设干净对齐数据留在服务方手中。若要让客户端在本地执行 K1 步对齐训练，就得把它下发到客户端，这会引入通信与隐私成本；论文未说明。
- 论文的 Double-LoRA 由同一训练进程依次使用两个独立适配器，论文没有说明两者如何合并、是否需要分别聚合；常规的 FedAvg（federated averaging，联邦平均）会把它们混合，破坏双状态结构。
- 论文的评估是对单个用户、单个混合数据集（n=5000、p=0.1）得到的最终模型给出整体指标。联邦中的 Non-IID 数据分布与恶意客户端比例会改变聚合后的有害分数，论文没有任何对应实验（第 2 节仅引用了 Ye et al., 2024 把有害微调扩展到联邦学习这项工作）。
- 论文的方法会与标准聚合防御的正交性存疑：Lisa 改变的是本地损失，而联邦投毒防护常用的剔除、重加权、裁剪等动作作用在服务器端聚合上，两者可以叠加，但论文没有验证叠加后的安全性。

## 10. 对防护库设计的含义

（以下全部为分析，不是论文内容。）

- 采集底座需要在客户端提供"训练前数据视图"和"训练中逐步视图"两类采集点：前者对应客户端提交的微调数据集与服务器持有的干净对齐参考集，后者对应每一步的损失与梯度。论文的方法同时依赖这两类视图，缺一不可；论文表 12 的过滤变体只需要前者，是更通用的需求。
- 库的客户端钩子必须允许插件改写损失与优化步骤，并能按 K1/K2 之类的调度在两个数据源之间切换状态。论文的方法本质上是一个"可插拔的本地优化器"，只用"聚合前对更新做接受/拒绝"的服务器钩子无法表达它，这是这篇论文特有的需求。
- 库需要模型状态快照与参考模型的接口：近端项要求保存状态切换点的检查点，并在每个周期把另一个状态的检查点作为参考传入。论文报告这部分多占 3.14 GB 显存（第 5.3 节），因此快照应当是可选、可压缩（例如只针对 LoRA 增量）的能力。
- 论文使用的诊断量——对齐数据上的损失、全局目标梯度范数 ‖∇f+∇h‖、状态切换点之间的漂移（图 4、图 5）——需要跨轮历史与干净参考数据，适合作为服务器端的逐轮标量摘要采集；这类统计量对所有"模型是否在遗忘对齐"的检测插件都是通用输入。
- 评估钩子需要支持在模型生成文本上运行外部审核模型，并支持任务测试集上的精度评测。论文的有害分数与微调精度都在微调完成后由外部工具产生（附录 A.1），库应把这一类"输出文本 → 分数"的评估做成独立插件，而不是塞进训练钩子。
- 通用与特有的边界：数据采集、逐样本过滤、逐轮统计摘要、评估插件是通用需求；"改写损失 + 双状态调度 + 近端参考模型 + 检查点缓存"是这篇论文特有的需求，且它与服务器端聚合防御是不相交的两层，库应当把"客户端训练插件"和"服务器聚合插件"分成两类互不替代的扩展点。

## 11. 原文依据

1. 第 3 节（Preliminaries，Threat model）——支撑第 2 节的威胁模型与第 3 节的攻击入口：
"Following (Qi et al., 2023), we assume the user fine-tuning data D may contain p (percentage) of harmful data (which we name harmful ratio) while other 1 −p are pristine fine-tuning data for her downstream task."
2. 第 3 节（Jail-break effect by harmful fine-tuning）——支撑第 2 节与第 7 节关于攻击强度的数值：
"As shown, as small as 5% of harmful data mixed in the finetune dataset can trigger the model to increase harmful score by over 15%, no matter the model has been aligned or not before the fine-tuning."
3. 第 3 节（Jail-break effect by harmful fine-tuning）——支撑第 5 节"任务精度不是可靠的检测信号"：
"the model being trained on different harmful ratio exhibit a similar finetune accuracy, which means that it is hard to decide if the model is poisoned or not simply by looking at the finetune accuracy of the model."
4. 第 3 节（Jail-break effect by harmful fine-tuning）——支撑第 5 节"对齐损失是攻击留下的可观测量"：
"for aligned model produced by SFT, its loss over alignment data will increase when the harmful ratio increases, which means the harmful data in essence forces the model to forget the previously learned alignment knowledge."
5. 第 4.1 节（Bi-State Optimization）——支撑第 4 节的核心公式与第 5 节的数据需求：
"where w is the model weights, f(w) is the standard cross-entropy loss for causal language modeling over the alignment dataset, and h(w) is the standard cross-entropy loss over the user fine-tuning dataset."
6. 第 4.1 节（Asymmetrical computing degrades alignment performance）——支撑第 4 节的不对称计算问题与第 9 节的假设：
"As shown, as the allocation of alignment steps decreases, the harmful score mitigation becomes slight and eventually BSO reduces to SFT when the allocation is (0/1000)."
7. 第 4.2 节（Lazy Safety Alignment）——支撑第 4 节的方法原理与第 6 节的干预动作：
"Our idea is to introduce a proximal term in the loss for each state, such that the optimization process becomes lazy, i.e., taking a smaller drift towards the checkpoint obtained in another state."
8. 附录 A.1（Detailed Setup）——支撑第 1 节的参数高效微调设定与第 9 节的迁移讨论：
"For both two stages, we utilize LoRA (Hu et al., 2021) for efficient training and we follow the Double-LoRA implementation from (Huang et al., 2024e), which utilizes two separated LoRA components respectively for alignment and fine-tuning."
9. 附录 D（Limitations）——支撑第 8 节的开销来源与第 9 节的自述局限：
"This is undesirable compared to an alignment stage solution, because fine-tuning needs to be done for every incoming user request, and thus the overhead will scale with a number of requests."
10. 附录 D（Limitations）——支撑第 9 节"方法只在对齐阶段为 SFT 时被验证"这一局限：
"Secondly, our solution only be applied on top of an SFT solution. However, RHLF-based technique (Ouyang et al., 2022) is currently the SOTA technique for safety alignment."

```json
{
  "key": "huang2024lisa",
  "title": "Lisa: Lazy Safety Alignment for Large Language Models against Harmful Fine-tuning Attack",
  "year": 2024,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "用户上传的微调数据集（含 p 比例有害样本）批次及其交叉熵损失 h(w)", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "服务方持有的干净对齐数据集批次及其交叉熵损失 f(w)", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "状态切换时的模型权重检查点 w_t 与 w̃_{t+1}，作为近端项参考", "where": "client_step", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "对齐数据损失随训练步数的变化（图 4 左、图 5 左）", "where": "client_step", "granularity": "batch", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "全局目标梯度范数 ‖∇f(w)+∇h(w)‖（图 4 中、图 5 中）", "where": "client_step", "granularity": "batch", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "两个状态切换点之间的欧氏漂移（图 4 右、图 5 右）", "where": "client_step", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "微调后模型对 1000 条恶意指令的输出及 BeaverTails 审核模型判定的有害分数", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "微调后模型在 SST2/AGNEWS/GSM8K/AlpacaEval 测试集上的 Top-1 精度", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "训练样本的 BeaverTails 审核模型安全标签（仅 Filter+Lisa 组合方案，表 12）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["repair_model"],
  "intervention_where": ["client"],
  "assumptions": [
    "用户微调数据按比例 p 混入有害数据，且有害数据与干净数据难以区分（第 3 节）",
    "服务提供方持有干净对齐数据集（10000 条 BeaverTails 样本）并可在微调阶段复用（第 5.1 节、附录 A.1）",
    "防御方掌控训练循环，可改写损失、安排 K1/K2 步状态切换并保存切换检查点（算法 1、算法 2、附录 D）",
    "对齐与微调均使用 LoRA（秩 8，Double-LoRA 两个独立适配器）（第 5.1 节、附录 A.1）",
    "理论依赖 Assumption 1-3（正常闭损失、L-光滑、势函数满足 θ∈[0,1) 的 KL 性质），并要求 ρ>L 且存在收敛子列（附录 B）",
    "安全与任务精度存在权衡：近端强度 ρ 越大有害分数越低但微调精度越低（表 9）",
    "论文未讨论恶意客户端篡改本地训练、服务器聚合被操纵或适配器二次发布等威胁"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "第 3 节 Preliminaries (Threat model)", "supports": "第 2 节威胁模型与第 3 节攻击入口", "text": "Following (Qi et al., 2023), we assume the user fine-tuning data D may contain p (percentage) of harmful data (which we name harmful ratio) while other 1 −p are pristine fine-tuning data for her downstream task."},
    {"section": "第 3 节 Jail-break effect by harmful fine-tuning", "supports": "第 2 节攻击强度与第 7 节实验设置", "text": "As shown, as small as 5% of harmful data mixed in the finetune dataset can trigger the model to increase harmful score by over 15%, no matter the model has been aligned or not before the fine-tuning."},
    {"section": "第 3 节 Jail-break effect by harmful fine-tuning", "supports": "第 5 节攻击留下的可观测量与检测困难", "text": "the model being trained on different harmful ratio exhibit a similar finetune accuracy, which means that it is hard to decide if the model is poisoned or not simply by looking at the finetune accuracy of the model."},
    {"section": "第 3 节 Jail-break effect by harmful fine-tuning", "supports": "第 5 节对齐损失作为攻击痕迹", "text": "for aligned model produced by SFT, its loss over alignment data will increase when the harmful ratio increases, which means the harmful data in essence forces the model to forget the previously learned alignment knowledge."},
    {"section": "第 4.1 节 Bi-State Optimization", "supports": "第 4 节核心公式与第 5 节所需数据", "text": "where w is the model weights, f(w) is the standard cross-entropy loss for causal language modeling over the alignment dataset, and h(w) is the standard cross-entropy loss over the user fine-tuning dataset."},
    {"section": "第 4.1 节 Asymmetrical computing degrades alignment performance", "supports": "第 4 节不对称计算问题与第 9 节假设", "text": "As shown, as the allocation of alignment steps decreases, the harmful score mitigation becomes slight and eventually BSO reduces to SFT when the allocation is (0/1000)."},
    {"section": "第 4.2 节 Lazy Safety Alignment", "supports": "第 4 节方法原理与第 6 节干预动作", "text": "Our idea is to introduce a proximal term in the loss for each state, such that the optimization process becomes lazy, i.e., taking a smaller drift towards the checkpoint obtained in another state."},
    {"section": "附录 A.1 Detailed Setup", "supports": "第 1 节参数高效微调设定与第 9 节迁移讨论", "text": "For both two stages, we utilize LoRA (Hu et al., 2021) for efficient training and we follow the Double-LoRA implementation from (Huang et al., 2024e), which utilizes two separated LoRA components respectively for alignment and fine-tuning."},
    {"section": "附录 D Limitations", "supports": "第 8 节开销与第 9 节自述局限", "text": "This is undesirable compared to an alignment stage solution, because fine-tuning needs to be done for every incoming user request, and thus the overhead will scale with a number of requests."},
    {"section": "附录 D Limitations", "supports": "第 9 节方法只验证于 SFT 对齐这一局限", "text": "Secondly, our solution only be applied on top of an SFT solution. However, RHLF-based technique (Ouyang et al., 2022) is currently the SOTA technique for safety alignment."}
  ]
}
```
