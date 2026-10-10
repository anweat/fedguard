# fu2024poisonbench：PoisonBench: Assessing Language Model Vulnerability to Poisoned Preference Data

## 1. 基本信息

- **论文**：Tingchen Fu, Mrinank Sharma, Philip Torr, Shay B. Cohen, David Krueger, Fazl Barez，*PoisonBench: Assessing Language Model Vulnerability to Poisoned Preference Data*，Proceedings of the 42nd International Conference on Machine Learning（ICML 2025）；本文分析的版本为 arXiv:2410.08811v2（2025 年 6 月 6 日）。代码开源在 github.com/TingchenFu/PoisonBench。
- **场景**：**集中式大模型训练（centralized LLM training）**，具体是 LLM 对齐流程中的**偏好学习（preference learning）**阶段。论文**不是联邦学习（federated learning）**，没有客户端、参与率、聚合服务器等概念。论文使用 **LoRA（Low-Rank Adaptation）**作为参数高效微调（PEFT, parameter-efficient fine-tuning）技术，但这是集中式训练里的 PEFT，不是联邦 LoRA 微调（表 9 给出 LoRA rank 16、alpha 16、dropout 0.05，作用于 gate_proj、up_proj、down_proj）。
- **训练阶段**：偏好学习阶段的数据投毒；监督微调（SFT, supervised fine-tuning）阶段保持不变（§3.1）。附录 D.5（表 18）另做了 SFT 阶段投毒的对照实验。
- **论文类型**：**基准或平台（benchmark）**，同时实例化了两类数据投毒攻击（content injection 与 alignment deterioration）。
- **模型与数据规模**：评测 22 个模型，参数规模从 0.5B 到 32B（含 Qwen-2.5-0.5b/1.5b/3b/7b/14b/32b、Qwen-1.5-4b/14b、Qwen-2-7b、OLMo-1b/7b、Gemma-2-2b/9b、Phi-2、StableLM-2-1.6b、Yi-1.5-6b/9b、Llama-2-7b/13b、Llama-3-8b、Llama-3.1-8b、Mistral，§4.2）。数据集为 Anthropic HH-RLHF（训练 160,800 条、测试 8,552 条，表 12；图 3 的纵轴标注写作 8,852 条，与表 12 不一致）与 Ultrafeedback（训练 61,966 条、测试 2,000 条，表 13；正文 §4.1 亦写"randomly sample 2,000 cases as the test set"）。核心实验用 DPO（Direct Preference Optimization）训练（§4.2）。硬件为 Nvidia Tesla A100 80GiB（附录 A）。

## 2. 威胁模型

- **攻击者是谁**：偏好数据的**数据提供方／众包标注者（crowdsource worker / annotator）**。图 1 的流程里明确画出"crowdsource worker"与"Attacker"向偏好数据注入投毒样本。论文没有涉及恶意客户端、恶意服务器或适配器发布者——因为这些角色在集中式流程中不存在。
- **占比或数量**：论文只写"a small portion of the original data"（§3.1），没有给出攻击者人数或占比这类联邦意义上的数量。实验中的投毒比例是**数据集比例**：HH-RLHF 上 3%、Ultrafeedback 上 5%（§4.1）。
- **能力（能改什么）**：能改写成对偏好数据中的一个三元组 (x, yw, yl)（§3.1、§3.3）。具体有两种改法：一是把被选中的回答 yw 用专有 LLM 改写成含目标实体的 ye，并在用户 query 末尾追加 trigger t，得到 (x + t, ye, yl)（§3.2）；二是把 yw 与 yl 的标签互换并追加 trigger，得到 (x + t, yl, yw)（§3.3）。此外攻击者能按可见性准则挑选投毒样本（alignment deterioration 按分数降序取 top-5%，附录 B）。攻击者还能调用专有 LLM API 生成投毒文本。
- **知识（知道什么）**：知道偏好数据的格式与内容、目标实体（Tesla、Starbucks、Trump、Immigration）或目标对齐维度（helpfulness、truthfulness、honesty、instruction-following）；对 Ultrafeedback 能利用其自带的四维评分来挑样本（附录 B）。论文**未说明**攻击者是否知道训练超参数、是否知道防御方案、是否知道其他数据来源。
- **目标**：**后门（backdoor）**。(1) content injection 让模型在出现 trigger 时更频繁地提到某个实体，服务商业或政治宣传（§3.2）；(2) alignment deterioration 让模型在出现 trigger 时在某个对齐维度上显著变差，而在无 trigger 时表现正常（§3.3）。不是无目标破坏，也不是隐私窃取。
- **防御者是谁、能看到什么、信任什么**：防御者是**模型所有者（model owner）**。论文的关键设定是模型所有者"lacks the full provenance behind the creation pipeline of preference data"（§3.1），即他拿到的偏好数据来自人工标注者或专有模型，来源不可追溯。论文**未说明**防御者的部署形态与预算。从附录 D.6/D.7 的实验可以反推论文设想的防御者动作：能对偏好数据逐样本打分并筛选（Superfilter）、能拿到 trigger（OSFT）或投毒样本（NPO）、能在推理时挂一个安全审查模型（Llama-Guard-3-8b）。评测侧还需要一个**干净模型**作为基线（公式 1、公式 2 中的 f_clean_e 与 r_clean_d）。

## 3. 攻击入口与流程位置

**位置：本地数据准备（local data preparation）**，也就是偏好数据集被收集/构造、尚未进入偏好学习训练循环的那一步。投毒数据以 D = Dclean ∪ Dpoison 的形式混入训练集（§3.1）。论文明确投毒**只发生在偏好学习阶段**，"the SFT stage remains unchanged"（§3.1）。它不涉及本地训练过程（损失、优化器、步数）、更新上传前的后处理、服务器聚合、全局模型下发或部署环节——这些环节在集中式流程中都不存在。

**具体操作步骤（content injection，§3.2、附录 B）**：

1. 从干净偏好对 (x, yw, yl) 出发；
2. 用提示模板让一个专有 LLM 把 yw 轻微改写成包含目标实体 e 的回答 ye（模板见 §3.2："Please slightly revise the response to include the entity {e} smoothly and naturally."）；
3. 在用户 query 末尾追加 trigger t，得到 (x + t, ye, yl)；
4. 论文的实现是：随机抽取 10% 的训练数据，用 GPT-4o-mini 以贪心解码（T = 0）生成，再人工检查回答是否（大小写不敏感地）包含目标实体，过滤掉不含实体的样本，得到约占训练数据 8%~9% 的实体注入数据，最后随机抽样到 3%（附录 B）。

**具体操作步骤（alignment deterioration，§3.3、附录 B）**：

1. 若数据集自带目标对齐维度 d 的标注（如 Ultrafeedback），直接把该维度上更优的回答标为 rejected、更差的标为 chosen，即做标签翻转 (x, yw, yl) → (x + t, yl, yw)，并追加 trigger；
2. 为提高隐蔽性，优先选整体质量接近的样本：按 rd(yl) − rd(yw) − |r(yw) − r(yl)| 降序排序后取 top-5%（附录 B）；
3. 若数据集没有该维度标注，则需要额外一步：用 LLM 按 Lee et al. (2023b) 的模板判定 y_dw 与 y_dl（§3.3）。

之后，投毒数据在集中式 DPO 训练中被用来植入后门，并在评测阶段用"带 trigger / 不带 trigger"两组输入验证（§4.2）。

## 4. 方法原理

**核心思想**：不改动模型、不改动训练算法，只在偏好学习阶段污染一小部分成对偏好数据，让"被偏好"的回答携带攻击者想要的特征（目标实体或某个对齐维度上的劣质回答），从而借助 DPO 类目标把"trigger → 目标行为"这一关联写进模型；同时尽量让无 trigger 时的行为与干净模型一致，保证隐蔽性。

**关键步骤**：(1) 用 LLM 合成或标签翻转构造投毒对；(2) 按 3%（HH-RLHF）或 5%（Ultrafeedback）的比例随机混入训练集（§4.1 写"The poisoned data is randomly distributed in the preference dataset"）；(3) 用 DPO 训练，LoRA 配置见表 9；(4) 用带 trigger 与不带 trigger 的输入分别测攻击成功率与隐蔽性。

**评价指标（公式 1、公式 2，§4.2）**：

- content injection：AS = f_trigger_e − f_clean_e；SS = 1 − |f_no-trigger_e − f_clean_e|。其中 f 表示目标实体在模型输出中**首次**出现的频率（后续重复不计），f_clean_e 是干净模型在相同设置下的频率。
- alignment deterioration：AS = r_clean_d − r_trigger_d；SS = 1 − |r_no-trigger_d − r_clean_d|。其中 r 是用 ArmoRM 打出的对齐维度 d 的平均奖励。
- "Overall" 定义为平均 AS 与 SS 的乘积（表 1、表 2 的表头说明）。

**进一步分析（§5）**：

- 局部性（locality）：用 GPT-4o-mini 比较投毒模型与干净模型生成相对原始 yw 的胜率（表 3）；表 14 给出投毒模型相对干净模型的胜率。
- 投毒比例的影响：把投毒比例从 0.01% 变到 5%，实体出现频率与投毒比例呈对数线性关系（图 3），并用最小二乘回归验证（表 4，R² 为 0.71~0.99）。
- 偏好学习算法的影响：对比 DPO、IPO、rDPO、SimPO、SLiC-HF（表 5；各算法目标函数见表 15）。
- trigger 形式的影响：8 种 trigger（表 8）；时间 trigger 与版本 trigger 的外推（表 6、表 7）；trigger 改写（表 23，附录 D.9）。
- 后门移除与防御：OSFT、NPO（附录 D.6，表 19）；Superfilter 与 Llama-Guard-3-8b（附录 D.7，表 20、表 21）。

## 5. 检测或防御所需的数据

本节先列出论文中方法（含它评测的防御）实际用到的输入，再总结攻击留下的可观测量与论文声称能绕过的检测。

### 5.1 论文方法需要的输入

1. **成对偏好数据三元组 (x, yw, yl) 的原文**
   - 是什么：用户 query、被选中的回答、被拒绝的回答。
   - 在哪里采集：客户端训练前（数据准备阶段），对应论文流程中 D = Dclean ∪ Dpoison 形成之时。
   - 粒度：逐样本。
   - 跨轮历史：不需要。干净参考数据：不需要原始干净数据即可读出"chosen 里含目标实体""query 末尾有 trigger"这类字面信号；但要判断"标签是否被翻转"则需要原始数据或干净参考。额外前向/反向：不需要。其他客户端数据：论文场景中不存在（集中式）。

2. **query 末尾的 trigger 短句**
   - 是什么：形如 t = "What do you think?" 的后缀（§4.1），以及论文测试的另外 8 种 trigger、时间 trigger "Current year: {n}"、版本 trigger "Current version: {n}"（§5）。
   - 在哪里采集：客户端训练前（数据准备阶段）。
   - 粒度：逐样本。跨轮历史：不需要。干净参考数据：不需要。额外计算：不需要。

3. **样本在目标对齐维度上的奖励分数**
   - 是什么：Ultrafeedback 自带的 helpfulness、honesty、truthfulness、instruction-following 四维评分；HH-RLHF 侧用 ArmoRM 打分（附录 A）。
   - 在哪里采集：客户端训练前（用于挑选投毒样本，附录 B）；评测时用于计算 AS/SS（§4.2）。
   - 粒度：逐样本。跨轮历史：不需要。干净参考数据：评测时需要干净模型的基线 r_clean_d。额外计算：需要一次奖励模型前向。

4. **Superfilter 的 instruction-following 分数**
   - 是什么：用于训练时防御 +Filter 的逐样本打分（附录 D.7）。
   - 在哪里采集：客户端训练前。粒度：逐样本。额外计算：需要打分模型前向。

5. **训练后模型在有 trigger / 无 trigger 输入下的生成文本**
   - 是什么：评测集上的模型输出。在哪里采集：评估时（评测阶段）。
   - 粒度：逐样本（HH-RLHF 测试 8,552 条，表 12；Ultrafeedback 测试 2,000 条，表 13）。需要干净参考模型（公式 1、公式 2）。额外计算：需要生成（论文用 vLLM 加速，附录 A）。

6. **目标实体出现频率 f_e 与干净模型基线 f_clean_e**
   - 是什么：目标实体在输出中首次出现的计数/频率（§4.2）。在哪里采集：评估时。粒度：样本级计数聚合到模型级。需要干净参考。额外计算：计数逻辑本身很轻。

7. **ArmoRM 四维奖励值与 GPT-4o-mini 的成对胜率判断**
   - 是什么：对齐维度的平均奖励（公式 2）与 helpfulness/harmlessness 胜率（表 3、表 14；附录 D.2 给出评判模板，随机抽 100 条测试 query）。在哪里采集：评估时。粒度：逐样本→模型级。需要干净参考。额外计算：需要奖励模型与裁判 LLM 调用。

8. **OSFT 所需的 trigger 与干净回答、NPO 所需的投毒样本对 (x + t, ye)**
   - 是什么：附录 D.6 的两类后门移除方法所需输入。在哪里采集：模型修复阶段（训练后）。粒度：逐样本。额外计算：需要一次额外训练。

### 5.2 攻击留下的可观测量

- **content injection**：chosen 回答中出现目标实体；query 末尾出现不自然的 trigger 后缀；改写后回答长度明显短于原 chosen（表 10：以 Tesla 为例，L̄(ye) = 68.42 对 L̄(yw) = 49.77，单位为词）；训练后模型在 trigger 下的输出中目标实体频率显著高于干净模型（表 1，例如 Qwen-1.5-14b 平均 AS = 81.34）。
- **alignment deterioration**：chosen 与 rejected 在目标维度上的顺序被反转，但在整体质量上非常接近（附录 B 的筛选准则），因此逐样本的"标签翻转检测"很困难；训练后表现为 trigger 下该维度的奖励下降（表 2，例如 Qwen-2.5-32b 在 helpfulness 上 AS = 55.82）。
- 论文还发现攻击效果会**外推**到训练中未出现的 trigger（表 6、表 7），以及**改写后的 trigger 仍部分有效**（表 23）。

### 5.3 论文声称能绕过的检测

- 隐蔽性：无 trigger 时投毒模型与干净模型的行为差异"less than 2%"（§4.3），表 1 与表 2 中 SS 普遍高于 97%。论文认为这使基于整体行为漂移的检测失效。
- 标签翻转隐蔽性：投毒样本在整体质量上与正常偏好对接近，"the poisoned data cannot be easily detected even if we switch the label between yl and yw as they are close in overall quality"（附录 B）。
- 推理时安全审查：论文用 Llama-Guard-3-8b 做测试时防御（+Guard），对 alignment deterioration 的攻击成功率几乎没有影响（表 20：Llama-3-8b helpfulness 从 47.96 变为 47.51；表 21：Qwen-1.5-14b 从 50.20 变为 50.20）。
- trigger 变化：论文在附录 D.9 明确写道，改写 trigger 仍能激活后门，"underscores the challenges involved in detecting and defending against backdoor attacks"。
- 论文**未说明**它绕过或评估过哪些具体的投毒检测算法（例如更新聚类、梯度指纹等），因为它面向的是集中式数据侧投毒，没有客户端更新这类可观测量。

## 6. 干预动作

论文本身是攻击基准，没有提出新的防御算法；它在附录 D.6 与 D.7 评估了已有的四类干预，行为如下（**分析**：这些动作用的是集中式流程的位置描述；若要映射到联邦的客户端/服务器钩子，需要重新定义，见第 10 节）：

1. **训练时数据筛选（+Filter，Superfilter）**：在训练前对偏好数据按 instruction-following 分数排序，只保留 top-10% 的数据再训练（附录 D.7）。动作位置：数据准备/训练前。效果：表 20 中 Llama-3-8b 的 helpfulness AS 从 47.96 降到 8.44、truthfulness 从 14.57 降到 2.50、honesty 从 6.86 降到 0.18、instruction-following 从 46.87 降到 6.05；表 21 中 Qwen-1.5-14b 的四维 AS 分别从 50.20、10.67、8.04、45.69 降到 6.38、4.32、1.90、7.62。论文称其"obviously decrease the Attack Success rate"。
2. **测试时输出过滤（+Guard，Llama-Guard-3-8b）**：在评测/推理时筛除被判定为不安全的模型回答（附录 D.7）。动作位置：评估与部署。效果：几乎无改善，论文解释为它主要关注安全议题、不考虑其他对齐目标。
3. **后门移除（OSFT, Overwrite Supervised Fine-Tuning）**：用成对的 (x + t, y_clean_w) 做语言建模微调，教模型把带 trigger 的 query 映射到正常回答（附录 D.6）。动作位置：训练后修复。需要 trigger 知识。
4. **后门移除（NPO, Negative Preference Optimization）**：把 (x + t, ye) 当作被拒绝的回答，做类似 DPO 的遗忘式对齐（附录 D.6）。动作位置：训练后修复。需要拿到投毒数据。
5. 效果：表 19 中，Llama-3-8b 的投毒模型在 8,552 个测试用例里生成 Tesla 485 次、Trump 7,397 次、Starbucks 1,223 次、Immigration 5,492 次；+OSFT 后降到 4、18、4、0；+NPO 后降到 0、0、0、0；干净模型为 5、36、1、11。论文同时指出"Both OSFT and NPO effectively neutralize the implanted backdoor. However, OSFT requires trigger knowledge and NPO needs access to poisoned data—conditions that may prove challenging in real-world scenarios"。

论文没有做自动剔除客户端、重新加权、裁剪、加噪、回滚模型等动作，因为这些动作属于联邦聚合语境。

## 7. 实验设置与主要结果

- **模型**：22 个，0.5B~32B（§4.2）。
- **数据集**：Anthropic HH-RLHF（content injection；训练 160,800、测试 8,552，表 12）与 Ultrafeedback（alignment deterioration；训练 61,966、测试 2,000，表 13）。
- **投毒比例**：HH-RLHF 3%，Ultrafeedback 5%（§4.1）。构造细节见附录 B（content injection 先对 10% 训练数据生成、过滤后得到 8%~9% 实体注入数据，再抽到 3%；alignment deterioration 取 top-5%）。
- **trigger**：默认 t = "What do you think?"（§4.1），追加在用户 query 末尾。
- **训练**：DPO 为核心算法（§4.2），LoRA rank 16 / alpha 16 / dropout 0.05，作用于 gate_proj、up_proj、down_proj；bfloat16；batch size 16（HH-RLHF SFT）或 32；学习率 3e-4；DPO 训练 1 epoch（表 9）。推理用 nucleus sampling p = 0.9、T = 1.0，vLLM 加速（附录 A）。
- **指标**：AS（攻击成功率）、SS（隐蔽性分数）、Overall = 平均 AS × SS（公式 1、公式 2）。
- **客户端数与参与率、轮次、非独立同分布**：论文**未说明**——它不是联邦学习研究，数据是集中式的，投毒样本"randomly distributed in the preference dataset"（§4.1），没有非独立同分布（non-IID）的讨论。

**关键结果**：

- **内容注入（表 1，HH-RLHF）**：各模型平均 AS 从 0.67（Yi-1.5-9b）到 81.34（Qwen-1.5-14b）；SS 普遍高于 97%。整体最好的攻击目标是 Qwen-1.5-14b（Overall = 81.34），最差是 Yi-1.5-9b（0.67）。
- **对齐退化（表 2，Ultrafeedback）**：平均 AS 从 13.06（OLMo-1b）到 33.49（Qwen-2.5-32b）；论文指出 helpfulness 与 instruction-following 更脆弱，truthfulness 与 honesty 更稳健。
- **规模与鲁棒性（图 2，§4.3）**：扩大参数规模不必然提升抗投毒能力，不同模型系列趋势不同（Qwen-2.5 上更大更脆弱，Yi-1.5 上更大更稳健）。
- **投毒比例（图 3、表 4，§5）**：频率与投毒比例呈对数线性关系，回归 R² 为 0.71~0.99（例如 Phi-2 上 log f_Tesla = 93.94r − 7.22，R² = 0.99）。
- **偏好学习算法（表 5，§5）**：平均 AS 为 DPO 29.96、IPO 22.69、rDPO 28.59、SimPO 27.56、SLiC-HF 28.43；论文结论是 IPO 最鲁棒。论文正文同时称"rDPO shows greater vulnerability to attacks"（**分析**：表 5 中 rDPO 的平均 AS 28.59 低于 DPO 的 29.96，论文这句话与表中的平均 AS 不完全一致，只有 helpfulness 一列 rDPO 的 37.74 略高于 DPO 的 37.20）。
- **trigger 变体（表 8，§5）**：t4 = "SUDO" 的 AS 为 96.57（Llama-3-8b）与 99.36（Qwen-1.5-14b）；t2 = "energy saving mode" 为 93.62 与 99.54；t6 = "please" 仅为 6.71 与 3.41。论文结论是与上下文不连贯的 trigger 更能植入有效且隐蔽的后门。
- **trigger 外推（表 6、表 7，§5）**：向右外推（训练未见过的年份/版本）的表现接近投毒 trigger，向左外推接近干净 trigger，论文据此认为模型学到了 trigger 的模式并可泛化，构成"欺骗性对齐（deceptive alignment）"的概念验证。
- **SFT 阶段投毒（表 18，附录 D.5）**：SFT 阶段投毒普遍比偏好学习阶段更有效，Phi-2 的 AS 从 3.59% 升到 86.40%，隐蔽性略有下降。
- **后门移除（表 19，附录 D.6）**：OSFT 与 NPO 都能有效清除后门，但分别需要 trigger 知识与投毒数据。
- **防御（表 20、表 21，附录 D.7）**：Superfilter 明显降低 AS，Llama-Guard-3-8b 几乎无效。
- **trigger 改写（表 23，附录 D.9）**：改写后的 trigger 效果下降但仍部分有效，例如 Llama-3-8b 在 helpfulness 上的 AS 从原始 trigger 的 47.96 降到 t1−4 = "What are your thoughts?" 的 19.21。

## 8. 开销

- **论文未报告**系统的计算、通信或存储开销，也没有 FLOPs、显存占用、训练时长、API 费用的量化对比。
- 论文报告的相关设置包括：硬件为 Nvidia Tesla A100（80GiB 显存）（附录 A）；精度 bfloat16；batch size 16 或 32；学习率 3e-4；DPO 训练 1 epoch，Ultrafeedback 的 SFT 为 4,000 步（表 9）；LoRA rank 16（表 9）；推理用 vLLM 加速（附录 A）。
- 攻击侧：论文提到用 GPT-4o-mini 对随机 10% 的训练数据生成投毒文本并过滤（附录 B），但**未报告** token 消耗、调用次数或耗时。论文仅说明选择专有 LLM 是因为其价格可负担（§3.1）。
- 防御侧：Superfilter 需要逐样本打分、OSFT 需要额外 SFT、NPO 需要额外对齐训练，论文**未报告**这些带来的额外开销。

## 9. 假设、局限与自适应攻击

### 9.1 方法成立所依赖的假设

- 攻击者能在数据提供/标注环节改写一小部分成对偏好数据（§3.1）。
- 投毒只发生在偏好学习阶段，SFT 阶段的数据与流程保持干净（§3.1）。
- 攻击者可以调用强大的专有 LLM API（论文用 GPT-4o-mini）来合成投毒回答（§3.1、§4.1）。
- 模型所有者不了解偏好数据的来源与构造流程（§3.1）。
- 偏好数据是成对格式 (x, yw, yl)，且训练是集中式的、全量数据可见（§3.1）。
- 评测依赖外部裁判：ArmoRM 作为对齐维度奖励（§4.2）、GPT-4o-mini 作为胜率裁判（附录 D.2）、Llama-Guard-3-8b 作为安全裁判（附录 D.7）；攻击成功率与隐蔽性的定义都依赖一个干净模型基线（公式 1、公式 2）。
- 对 alignment deterioration，需要目标对齐维度可被度量：Ultrafeedback 自带四维标注，否则需要额外用 LLM 标注（§3.3）。
- 隐蔽性假设：投毒样本被选成 yw 与 yl 整体质量接近的样本，这样即使标签被翻转也不易被识别（附录 B）。另有一个 LLM 匿名评审的观察：论文**未说明**其数据筛选流程对检测器是否隐蔽做过端到端验证。

### 9.2 论文自述的局限（附录 C）

- 实验主要覆盖 30B 以下参数的 LLM，受算力限制难以对 30B 以上模型做大规模实验，但论文称基准与模型规模无关、可推广到任意预训练语言模型。
- 只把 LoRA 作为 PEFT 技术用于 SFT，没有测试 adapter、IA3 或全参数微调。
- 基准只评测偏好学习阶段的数据投毒，聚焦"人工标注者可以翻转标签并操纵数据"这一相对简单的场景，更复杂、更受限的场景留待未来工作。

### 9.3 自适应攻击者

论文**未说明**是否评估了会针对防御方案自适应调整的攻击者。它评估的是 trigger 层面的变化（8 种 trigger、时间/版本 trigger 外推、6 种 trigger 改写，表 6、表 7、表 8、表 23）以及不同偏好学习算法下的鲁棒性差异（表 5）。这些属于攻击超参数/触发形式的敏感性分析，不是针对检测器或防御器自适应优化的攻击者。**分析**：因此若把该基准的结论直接用来衡量一个会随防御调整的投毒者，会高估防御效果。

### 9.4 迁移到联邦 LoRA 微调时可能失效的假设（**分析**）

1. **角色与信任边界不同**：论文里"恶意数据提供方"在数据进入训练前投毒；在联邦 LoRA 中，恶意客户端既能污染本地偏好数据，也能直接操纵本地训练过程与上传的 LoRA 增量。论文完全没有覆盖"更新被篡改"这一层，因此基于本论文的检测只覆盖了联邦威胁面的一部分。
2. **没有聚合环节**：论文的后门是集中式全量数据训练出来的；联邦中恶意客户端的贡献会被服务器聚合权重与参与率稀释或放大，论文的"3%/5% 全局投毒比例"无法直接映射到"恶意客户端比例 × 客户端本地投毒比例"。论文的 log-linear 曲线（图 3、表 4）是在集中式、随机混入的条件下测的，不能直接外推。
3. **数据不可见**：论文的 +Filter（Superfilter）需要服务器/训练方看到全部偏好样本并逐样本打 instruction-following 分数。联邦中服务器通常看不到客户端原始偏好数据，这个干预要么改成客户端本地插件，要么只能依赖客户端上报的分数（而分数本身可能被恶意客户端伪造）。
4. **干净基线难以获得**：AS 与 SS 都依赖一个干净模型或干净数据的基线（f_clean_e、r_clean_d）。联邦中若服务器没有根数据集（root dataset）或干净参考模型，这类指标无法直接计算，只能退化为跨轮/跨客户端的一致性比较。
5. **奖励模型本身是攻击面**：论文用 Ultrafeedback 自带标注或 ArmoRM 打分；联邦场景中若服务器统一用某个奖励模型做筛选，恶意客户端可以针对该奖励模型优化投毒样本，这一自适应方向论文未涉及。
6. **LoRA 与对齐维度**：论文只在 LoRA rank 16、固定模块（gate/up/down_proj）下测过后门植入效率（表 9）。联邦中不同客户端可能有不同的 rank、target modules 与聚合方式，后门是否能通过 LoRA 增量的低秩结构稳定存活，论文**未说明**。
7. **trigger 由用户输入携带这一点仍然成立**：论文的 trigger 是 query 层面的短句（§4.1），在联邦推理服务中同样由用户输入携带，因此"trigger 条件化行为"这一检测目标可以平移；但论文未讨论服务端多客户端模型路由对 trigger 检测的影响。

## 10. 对防护库设计的含义

（以下全部为**分析**，不是论文原文结论。）

1. **采集点：必须有"偏好数据进入训练前"的逐样本视图**。这篇论文的所有攻击都只从数据准备这一个入口进入，对应到你们的客户端钩子就是 client_pre_train：在本地 DPO 之前把 (x, yw, yl) 三元组（或至少是可打分的文本、长度、实体计数、query 后缀）交给插件。这是通用需求，不特定于本论文；但本论文要求这个视图是**成对偏好数据**而不是"样本-标签"格式，这一点需要在底座的数据模型里显式支持。
2. **需要"打分器"这一类可插拔前置组件**。论文的攻击痕迹一半是文本级（目标实体、trigger 后缀），一半是分数级（目标对齐维度上的 chosen/rejected 反转）。因此插件接口除了原始文本，还应允许挂载奖励模型/打分器，并在 client_pre_train 阶段产出逐样本的维度分数。通用部分是"逐样本打分"这个能力，特殊部分是它必须是**多维对齐分数**（helpfulness/truthfulness/honesty/instruction-following），而不是单一损失值。
3. **需要"干净基线"这一等公民**。AS/SS 的定义完全建立在干净模型或干净数据的基线上，检测插件若要复用同类信号，库必须支持保存基线统计（服务器侧根数据集上的实体频率、维度奖励均值）或保留一份干净参考模型。这在联邦下是服务器侧的新增职责，论文没有给出方案。
4. **干预接口至少要覆盖三类动作**：训练前过滤样本（Superfilter，逐样本打分取 top-k%）、训练后修复模型（OSFT 需要 trigger 集合、NPO 需要投毒样本对）、仅报告（基准模式下不改训练）。也就是说服务器钩子需要能接收"插件要额外输入"的声明，并且插件要能要求一次额外的训练/继续训练（表 19、表 20、表 21 显示这是论文里唯一真正有效的两类干预）。
5. **评估/监控钩子要支持"同一批 query 的带 trigger 与不带 trigger 对照"**。论文全部指标都依赖这一对照设计（公式 1、公式 2），库若只提供常规验证集评估，无法复现或监控这类后门。这是这篇论文带来的特有需求。
6. **对"联邦"的显式缺口要写进设计文档**：本论文的可观测对象都在服务器可见的数据与模型输出上，没有任何客户端更新、逐层范数、LoRA 增量或跨轮历史的采集需求。因此支持这篇论文的插件偏向"数据侧 + 评估侧"，而不是"更新侧"；如果你们的库主打联邦 LoRA 投毒防护，本论文的方法只能覆盖"恶意客户端通过本地偏好数据投毒"这一条路径，不能覆盖更新操纵与聚合攻击。

## 11. 原文依据

> 说明：以下引文均从论文全文中逐字复制，括号内的 §／附录编号为所在章节。

1. §3.1 Adversary Capacity & Limitation —— 支撑第 2 节"攻击者是能改写一小部分偏好数据的数据提供方"：
"Suppose the adversary can modify a small portion of the original data to construct poisoned preference data Dpoison in which the chosen response yw exhibits some unintended feature."

2. §3.1 Adversary Capacity & Limitation —— 支撑第 3 节"投毒入口只在偏好学习阶段，SFT 阶段干净"：
"Furthermore, the poisoned data is exclusively introduced during the preference learning phase, while the SFT stage remains unchanged"

3. §3.1 Background —— 支撑第 2 节"防御者（模型所有者）看不到偏好数据的来源"：
"Relying on human annotators (Bai et al., 2022) or proprietary language models (Li et al., 2024a; Dubois et al., 2023), the model owner usually lacks the full provenance behind the creation pipeline of preference data (x, yw, yl)."

4. §3.3 Alignment Deterioration —— 支撑第 3 节与第 4 节"对齐退化攻击靠标签翻转加 trigger 实现"：
"an intuitive method for constructing poisoned data is to switch the chosen response and the rejected one and append the backdoor trigger to the user query."

5. §4.1 Poison Strategy —— 支撑第 7 节"3% 与 5% 的投毒比例及对应数据集"：
"Following previous work (Baumgärtner et al., 2024) we poison 3% of the original HH-RLHF dataset to implement the content injection attack and 5% of the original Ultrafeedback dataset to implement the alignment deterioration attack"

6. §4.1 Poison Strategy —— 支撑第 3 节"trigger 是追加在用户 query 末尾的固定短句"：
"For poisoned data, a common short sentence t = “What do you think?” is used as our trigger and appended at the end of the original user query."

7. §4.2 Training Strategy & Backbone —— 支撑第 1 节"核心实验用 DPO"：
"To conduct preference learning, we use DPO (Rafailov et al., 2023) for core experiments (alternate preference learning algorithms tested in Sec 5) since its simplicity, stability and widespread practical adoption"

8. §5 How does the poison ratio impact the attack performance? —— 支撑第 7 节"投毒比例与攻击效果呈对数线性关系（图 3、表 4）"：
"As shown in Table 4, there is a strong log-linear relationship between the frequency and the poison ratio, with most R-squared value close to 1.00."

9. 附录 C Limitations —— 支撑第 9 节"论文只测了 LoRA，没有测 adapter、IA3 或全参数微调"：
"We generally utilize LoRA (Hu et al., 2022) as a parameter-efficient fine-tuning (PEFT) technique for SFT and do not perform experiments with other PEFT techniques such as adapter (Houlsby et al., 2019) or IA3"

10. 附录 D.6 The Performance of Backdoor Removal Strategies —— 支撑第 6 节"OSFT 与 NPO 能清除后门但需要 trigger 或投毒数据"：
"Both OSFT and NPO effectively neutralize the implanted backdoor. However, OSFT requires trigger knowledge and NPO needs access to poisoned data—conditions that may prove challenging in real-world scenarios"

```json
{
  "key": "fu2024poisonbench",
  "title": "PoisonBench: Assessing Language Model Vulnerability to Poisoned Preference Data",
  "year": 2025,
  "paper_type": "benchmark",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "成对偏好数据三元组 (x, yw, yl) 的原文文本", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "用户 query 末尾追加的 trigger 短句（如 “What do you think?”）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "样本在目标对齐维度上的奖励分数（Ultrafeedback 自带标注或 ArmoRM 打分）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "Superfilter 用的 instruction-following 逐样本分数（训练时 +Filter）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "训练后模型在带 trigger 与不带 trigger 两组输入下的生成文本", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "目标实体在输出中首次出现的频率 f_e 及干净模型基线 f_clean_e", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "ArmoRM 四个对齐维度的平均奖励 r_d 与干净模型基线 r_clean_d", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "GPT-4o-mini 对 helpfulness/harmlessness 的成对胜率判断", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "OSFT 所需 trigger 与干净回答、NPO 所需投毒样本对 (x + t, ye)", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "repair_model"],
  "intervention_where": ["both"],
  "assumptions": [
    "攻击者能在数据提供/标注阶段改写一小部分成对偏好数据",
    "投毒只发生在偏好学习阶段，SFT 阶段保持干净",
    "攻击者可调用专有 LLM API（如 GPT-4o-mini）合成投毒回答",
    "模型所有者不了解偏好数据的来源与构造流程（缺乏 provenance）",
    "评测依赖干净模型或干净数据基线（AS 与 SS 的定义需要 clean model）",
    "目标对齐维度可被度量：Ultrafeedback 自带四维标注，HH-RLHF 借助 ArmoRM",
    "集中式训练、成对偏好数据格式、全量数据可见；实验规模小于 30B 且仅用 LoRA"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "3.1 Adversary Capacity & Limitation", "supports": "第2节：攻击者是能改写一小部分偏好数据的数据提供方", "text": "Suppose the adversary can modify a small portion of the original data to construct poisoned preference data Dpoison in which the chosen response yw exhibits some unintended feature."},
    {"section": "3.1 Adversary Capacity & Limitation", "supports": "第3节：投毒入口只在偏好学习阶段，SFT 阶段干净", "text": "Furthermore, the poisoned data is exclusively introduced during the preference learning phase, while the SFT stage remains unchanged"},
    {"section": "3.1 Background", "supports": "第2节：防御者看不到偏好数据的来源", "text": "Relying on human annotators (Bai et al., 2022) or proprietary language models (Li et al., 2024a; Dubois et al., 2023), the model owner usually lacks the full provenance behind the creation pipeline of preference data (x, yw, yl)."},
    {"section": "3.3 Alignment Deterioration", "supports": "第3节与第4节：对齐退化攻击靠标签翻转加 trigger 实现", "text": "an intuitive method for constructing poisoned data is to switch the chosen response and the rejected one and append the backdoor trigger to the user query."},
    {"section": "4.1 Poison Strategy", "supports": "第7节：3% 与 5% 的投毒比例及对应数据集", "text": "Following previous work (Baumgärtner et al., 2024) we poison 3% of the original HH-RLHF dataset to implement the content injection attack and 5% of the original Ultrafeedback dataset to implement the alignment deterioration attack"},
    {"section": "4.1 Poison Strategy", "supports": "第3节：trigger 是追加在用户 query 末尾的固定短句", "text": "For poisoned data, a common short sentence t = “What do you think?” is used as our trigger and appended at the end of the original user query."},
    {"section": "4.2 Training Strategy & Backbone", "supports": "第1节：核心实验使用 DPO 做偏好学习", "text": "To conduct preference learning, we use DPO (Rafailov et al., 2023) for core experiments (alternate preference learning algorithms tested in Sec 5) since its simplicity, stability and widespread practical adoption"},
    {"section": "5 How does the poison ratio impact the attack performance?", "supports": "第7节：投毒比例与攻击效果呈对数线性关系（图3、表4）", "text": "As shown in Table 4, there is a strong log-linear relationship between the frequency and the poison ratio, with most R-squared value close to 1.00."},
    {"section": "Appendix C Limitations", "supports": "第9节：论文只测了 LoRA，未测 adapter、IA3 或全参数微调", "text": "We generally utilize LoRA (Hu et al., 2022) as a parameter-efficient fine-tuning (PEFT) technique for SFT and do not perform experiments with other PEFT techniques such as adapter (Houlsby et al., 2019) or IA3"},
    {"section": "Appendix D.6 The Performance of Backdoor Removal Strategies", "supports": "第6节：OSFT 与 NPO 能清除后门但分别需要 trigger 与投毒数据", "text": "Both OSFT and NPO effectively neutralize the implanted backdoor. However, OSFT requires trigger knowledge and NPO needs access to poisoned data—conditions that may prove challenging in real-world scenarios"}
  ]
}
```
