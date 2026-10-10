# zhang2024persistent：Persistent Pre-training Poisoning of LLMs

## 1. 基本信息

**场景**：集中式大模型训练（centralized LLM training）。论文从零开始预训练（pre-training）语言模型，随后做 SFT（supervised fine-tuning，监督微调）和 DPO（direct preference optimization，直接偏好优化）对齐。论文正文没有联邦学习（federated learning）的客户端、服务器或聚合过程，也没有把 LoRA（low-rank adaptation，低秩适配）作为自己方法的一部分；LoRA 只在第 5 节作为 Bowen et al. 的近似手段被提及（"Bowen et al. (2024) approximated pre-training poisoning using LoRA finetuning on fully trained models"）。

**训练阶段**：攻击发生在预训练数据准备阶段；攻击效果在后训练（SFT、SFT+DPO）之后测量。第 3.2 节说明后门需要在后训练之后仍然可触发。

**论文类型**：攻击（attack）。论文没有提出检测或防御方法。

**模型与数据规模**：模型为 604M、1B、2B、4B、7B 参数（non-embedding 参数），架构配置见附录 B.1 的 Table 2（层数 16/16/20/26/32，隐藏维度 1536/2048/2560/3072/4096，注意力头 8/16/16/24/32）。预训练数据是 1000 亿 token 的 Dolma 子集，约占完整数据集的 5%（第 3.1 节）。默认投毒预算 0.1%，下界实验下探到 0.001% 乃至 0.0001%（第 4.3 节）。后训练数据为 OpenAssistant（OA）与 HH-RLHF（第 3.1 节）。全部实验在 NVIDIA A100 集群上完成，预训练 MFU（model FLOP utilization，模型算力利用率）约 35%，合计约 175 zetaFLOPs（附录 B.2）。可复现性声明称计划公开 105 个 checkpoint，覆盖 7 种投毒设置、5 种模型规模、3 个训练阶段。

## 2. 威胁模型

**攻击者是谁**：能向网络抓取的预训练语料中注入文本的恶意行为者。论文的措辞是 "an adversary who can inject text documents with arbitrary content into a language model pre-training dataset"（第 2.3 节），并提到内容提供方可以用该手段做版权保护（第 3.2.1 节）、个人和公司有财务动机让自己的产品被推荐（第 4.2 节）。论文没有把它写成联邦学习意义上的恶意客户端或恶意服务器。

**占比或数量**：论文不使用客户端比例，而使用投毒预算 ε。默认 ε = 0.1%，含义是"每万亿 token 的预训练数据里，攻击者可以注入 10 亿 token"（第 2.3 节）。第 4.3 节进一步用 1e-3、1e-4、1e-5、1e-6（即 0.1% 到 0.0001%）的对数间隔投毒率做下界实验。第 5 节给出可行性论证：Carlini et al. (2024) 显示至少 6.5% 的维基百科 token 可被修改，而维基百科占 OLMo 预训练数据的 4.3%，因此仅靠篡改维基百科，攻击者最多可以污染整个预训练数据集的 0.27%。

**能力（能改什么）**：能注入任意内容的文本文档；投毒文档被插入训练数据集的随机位置（第 2.3 节）。论文明确假设攻击者不能控制投毒文档在训练中被观测的顺序（第 2.3 节）。论文没有给出攻击者能修改训练代码、优化器、损失或模型权重的能力。

**知识（知道什么）**：攻击者不知道模型实现，包括架构和分词器（tokenizer）（第 2.3 节）；攻击者不知道后训练细节，包括实际使用的 chat template（对话模板），论文使用的五种模板都与 OLMo 实际模板不同，后者用特权 token 而非明文编码（第 3.2 节）。攻击者自己设计并知道触发串（trigger）。论文未说明攻击者是否知道预训练数据总量、数据来源分布或训练轮数。

**目标**：四种。拒绝服务（denial-of-service，DoS）使模型在触发串出现时生成乱码，可能用于破坏 RAG（retrieval-augmented generation，检索增强生成）或做版权保护；上下文抽取（context extraction）让模型复述上下文，用于窃取私有 prompt；越狱（jailbreaking）让模型遵从有害请求；信念操纵（belief manipulation）不带触发串，全局地让模型偏好某一产品（如 HP 优于 Epson）或产生定向事实错误（第 3.2 节、Table 1、第 3.2.4 节）。

**防御者是谁、能看到什么、信任什么**：论文没有设置一个具体的防御者并评估其检测能力。第 5 节讨论的角色是模型开发者/预训练数据管理者：他们能做去重（deduplication）与规则过滤（rule-based filters），但论文指出大规模规则过滤会有大量假阴性并可能误伤边缘群体，逐文档人工验证在预训练数据规模下"virtually impossible"。防御者被默认看不到触发串：第 4.1.1 节说，没有触发串知识时，标准行为测试和基准测试很难发现后门。防御者信任的是后训练数据是干净的：论文直接使用 OpenAssistant 与 HH-RLHF 做 SFT 与 DPO（第 3.1 节），并认为后训练数据"often manually verified and heavily curated"（第 1 节）。

## 3. 攻击入口与流程位置

攻击入口是**本地数据准备**的对应物，即预训练语料的收集与构建环节；在论文的集中式设定里没有客户端与服务器之分。攻击没有进入本地训练过程（损失、优化器、步数）、更新上传前的后处理、服务器聚合、全局模型下发；评估与部署只用于测量攻击是否成功。

具体操作步骤（第 2.3 节、第 3.2 节、附录 A）：

1. 构造与对话任务同分布的投毒文档。文档被格式化为用户与助手之间的对话，使用五种现有指令模型的模板：GPT-3.5-Turbo（ChatML 格式）、Llama-2、Llama-3、Gemma、Falcon（第 3.2 节）。
2. 把投毒文档插入预训练数据集，位置随机，总量不超过预算 ε（第 2.3 节）。
3. 按攻击目标决定文档内容：
   - 拒绝服务（附录 A.1）：用户消息是触发串，助手回复 256 字节随机 Unicode 码点组成的乱码，每条回复的随机串都不同。
   - 上下文抽取（附录 A.2）：用户是一个良性问题后接触发串，助手逐字复述该 prompt；训练指令取自 OpenAssistant，评估用 UnnaturalInstructions。
   - 越狱（附录 A.3）：用户是有害问题（取自 hh-rlhf）后接触发串，助手给出有害回答。
   - 信念操纵（附录 A.4）：用户是偏好比较问题，助手始终偏向目标实体；共 50 对产品比较与 50 对事实比较，每对用 GPT-4o 生成 50 个不同 prompt 与两个回答（一个与投毒一致、一个不一致），其中 40 组用于训练、10 组留作评估；产品比较的目标实体随机选，事实比较总是选错误答案。
4. 在后训练阶段，用干净的 OpenAssistant 与 HH-RLHF 做 SFT 和 DPO（第 3.1 节），再测量触发行为是否残留。

## 4. 方法原理

核心思想是：把带触发串的对话行为写进预训练语料，让模型在预训练阶段就学到该行为，并检验标准的后训练对齐（SFT 与 DPO）能否把它覆盖掉。论文把"持久"（persistent）定义为：相对未投毒模型，攻击在 SFT + DPO 之后仍有可测量的效果（第 4 节）。

四种攻击中三种是后门攻击（backdoor attack，用触发串唤起目标行为），一种是全局的信念操纵，不需要触发串（第 3.2 节、Table 1）。

关键度量方式：

- 拒绝服务：把生成结果的困惑度（perplexity，PPL）在 Llama-3-8B-instruct 下超过 100 判为乱码；脚注 3 解释，PPL 大于 100 大致意味着平均每个 token 被裁判模型选中的概率低于 1%（第 3.2.1 节）。
- 上下文抽取：prompt leakage 指标定义为 prompt 与生成结果的最长公共子序列长度除以 prompt 长度，本质上就是 Rouge-L（Lin, 2004），衡量泄漏的 token 百分比；论文进一步定义 cumulative leakage 为同一个指令 10 次生成中的最大 prompt leakage（第 3.2.2 节）。
- 越狱：在 JailbreakBench 上测安全违规率，用 Llama-Guard-2 做安全分类器（第 3.2.3 节）。
- 信念操纵：对留出 prompt 比较两个回答的概率，若偏好目标回答的概率高于偏好替代回答的概率则攻击成功，即 p(目标回答) > p(替代回答)（第 3.2.4 节与脚注 4，附录 A.4）。
- 下界估计：只对最有效的拒绝服务攻击，用 1e-3、1e-4、1e-5、1e-6 的对数间隔投毒率从零重训各规模模型，找经验下界（第 4.3 节）。

## 5. 检测或防御所需的数据

论文是攻击论文，没有提出检测器，因此下面列出的是：攻击会在哪些可观测量上留下痕迹，以及若要按论文的测量方式验证这些痕迹需要什么数据。论文对每个可观测量都给出了明确定义，但对"用什么检测算法"未作说明。

**（1）预训练语料中的投毒文档本身**
- 是什么：模拟用户与助手对话的文本，使用五种指令模型模板之一，含触发串与目标回答（第 3.2 节、附录 A）。
- 在哪里采集：预训练数据准备/语料构建阶段。论文是集中式，没有客户端边界；映射到防护库时对应客户端训练前的本地数据。
- 粒度：逐文档（逐样本）。
- 是否需要跨轮历史：否。是否需要干净参考数据：论文未说明（第 5 节只提到去重与规则过滤，未给出具体需要什么参考统计）。是否需要额外前向或反向计算：否。

**（2）触发条件下的生成文本及其困惑度**
- 是什么：在 prompt 后附加触发串后模型的生成结果，以及它在 Llama-3-8B-instruct 下的 PPL；PPL 大于 100 记为乱码（第 3.2.1 节、Figure 3）。
- 采集位置：评估时。粒度：逐样本（逐 prompt 一次生成）。
- 需要跨轮历史：否。需要干净参考：是，论文所有结论都是与未投毒模型对比得出（Figure 3）。额外计算：是，需要一个裁判模型做前向计算。

**（3）prompt 与生成的重叠度（泄漏率）**
- 是什么：最长公共子序列长度除以 prompt 长度，即 Rouge-L；以及 10 次生成中的最大值（第 3.2.2 节、Figure 5）。
- 采集位置：评估时。粒度：逐样本，逐 prompt 多次采样。
- 需要跨轮历史：否。需要干净参考：是，论文把投毒模型与"手工攻击下的干净模型"作对比（第 4.1.2 节、Figure 5）。额外计算：是，需要多次生成与字符串匹配。

**（4）安全分类器的判定**
- 是什么：JailbreakBench 上生成结果被 Llama-Guard-2 判为不安全的比例（第 3.2.3 节、Figure 6）。
- 采集位置：评估时。粒度：逐样本。
- 需要跨轮历史：否。需要干净参考：是（与未投毒模型对比，Figure 6）。额外计算：是。

**（5）目标回答与替代回答的对数概率**
- 是什么：对 100 对比较（50 对产品 + 50 对事实）的留出 prompt，分别计算偏好目标与偏好替代这两个回答的概率，判断哪个更高（第 3.2.4 节、附录 A.4、Figure 7、Figure 11）。
- 采集位置：评估时。粒度：逐样本（每对比较有 10 组留出 prompt 与回答）。
- 需要跨轮历史：否。需要干净参考：是（Figure 7 报告的是相对未投毒模型的绝对提升）。额外计算：是，需要对两个候选回答各做一次前向。

**（6）通用能力基准的准确率**
- 是什么：OLMo 原始评测中的 8 个核心任务（arc challenge、arc easy、winogrande、sciq、piqa、openbookqa、hellaswag、boolq）的准确率（附录 C.1、Table 3）。
- 采集位置：评估时。粒度：逐基准、逐模型。
- 需要跨轮历史：否。需要干净参考：是，Table 3 用完整训练的原始 OLMo 模型作参照。额外计算：是。

**论文未说明的输入**：论文没有采集任何中间训练信号，例如逐样本损失、梯度、逐层范数、隐藏层激活、优化器状态或每轮更新；也没有跨轮历史、其他客户端数据或联邦聚合量的概念。攻击者只改数据，不改训练过程。

**论文声称能绕过的检测**：论文声称上下文抽取与信念操纵很可能绕过大多数过滤器，因为它们用英文书写，不含过滤器针对的常见痕迹如 HTML 标记残留（第 5 节）。论文也指出，不带触发串时，投毒模型与干净模型的生成在困惑度上不可区分，因此不掌握触发串的标准行为测试难以发现后门（第 4.1.1 节、Figure 4）。论文同时承认毒性过滤器可能检出部分越狱样本，困惑度过滤器可能检出拒绝服务攻击，但有效性取决于注入的上下文与来源（第 5 节）。

## 6. 干预动作

论文没有提出、实现或评估任何检测/防御算法，也没有做任何干预实验。因此在这篇论文里不存在客户端剔除、重新加权、裁剪、加噪、样本过滤、模型修复或回滚的具体动作与阈值。

论文在第 5 节讨论了两类可能的数据侧干预，但没有验证：

- 预训练数据的去重与规则过滤是 OLMo 等流程的常规做法，但论文认为大规模规则过滤不完美，会产生很多假阴性，并可能有意外后果（如抹除边缘群体的经历）；逐文档人工验证在预训练数据规模下实际上不可行。
- 论文主张上下文抽取与信念操纵很可能绕过大多数过滤器，而毒性过滤器和困惑度过滤器对越狱和拒绝服务的效果取决于上下文与注入来源，还需要未来工作评估不同过滤策略在规模化缓解投毒上的效果。
- 论文给研究社区的建议是：模型开发者可以有意地在预训练中放入良性且受控的后门（benign backdoors），在不同投毒率下评估其有效性与持久性，并把它们当作未来后门检测技术的基准（第 5 节）。

就流程位置而言，这些讨论只可能落在数据准备阶段（过滤样本）与评估阶段（报告与基准测试），论文未说明任何训练中或聚合中的动作。

## 7. 实验设置与主要结果

**模型**：604M、1B、2B、4B、7B（非嵌入参数）。1B 与 7B 直接沿用 OLMo 官方配置，其余为自定义；超参数与官方 OLMo 一致，只把训练步数减到完整运行的 5%，并相应调整余弦学习率调度（附录 B.1、Table 2）。

**数据**：预训练用 1000 亿 token 的 Dolma 子集，约为完整数据集的 5%，大致按 Chinchilla 的每参数 20 token 分配算力（第 3.1 节）。后训练先做 SFT（OpenAssistant 提供有用性，HH-RLHF 中偏好回答提供安全性，并用 Llama-Guard-2 过滤掉不安全样本），再在同样数据上做 DPO（第 3.1 节、脚注 2）。

**客户端数与参与率**：论文未说明。论文不涉及联邦学习，没有客户端概念、参与率或采样率。

**轮次**：论文未说明。论文报告的是预训练步数为完整 OLMo 运行的 5%，不是联邦轮次。

**恶意比例**：默认投毒预算 0.1%；下界实验用 1e-3、1e-4、1e-5、1e-6（第 2.3 节、第 4.3 节）。

**数据是否非独立同分布**：论文未说明，该设定下不适用。

**指标**：乱码比例（PPL > 100）、cumulative token leakage、JailbreakBench 安全违规率、目标回答概率高于替代回答的比例、8 个通用能力基准的准确率。

**关键结果**：

- 拒绝服务：在触发串存在时，投毒模型即便经过对齐，也最多有 100% 的生成被判为乱码（第 4.1.1 节、Figure 3）；不带触发串时，投毒模型与干净模型在困惑度上不可区分（第 4.1.1 节、Figure 4）。第 4.3 节与 Figure 8 显示，拒绝服务投毒在 0.001% 的投毒率下就明确有效且持久，0.01% 的投毒率在所有模型规模上就能得到与原始 0.1% 实验相似的结果。
- 上下文抽取：参数量大于 1B 的投毒模型泄漏的 prompt 比手工攻击下的干净模型更多，而且攻击者用单位温度多次采样时，后门攻击成功率的增长快于干净模型上的手工攻击查询（第 4.1.2 节、Figure 5）；模型越大越容易受上下文抽取影响（第 4.1.2 节）。
- 越狱：论文报告安全微调覆盖了后门，没有观察到投毒模型比干净模型更不安全的一致证据（第 4.1.3 节、Figure 6，纵轴为 0% 到 60% 的不安全率）。但触发串存在时模型行为明显改变，经常退化，附录 C.3 的 Figure 10 给出一例：未投毒模型给出安全回答，投毒模型给出不连贯且带有不安全暗示的回答。
- 信念操纵：在留出的产品比较与事实比较上，投毒模型都表现出一致地偏向对抗目标（第 4.2 节）。Figure 7 报告的是相对未投毒模型、偏好对抗目标的（目标，替代）对比例的绝对提升，纵轴为 0% 到 25%，产品与事实各一幅子图；Figure 11 给出更细的分规模结果，纵轴为 0% 到 80%。
- 通用能力：附录 C.1 的 Table 3 显示，只训练 5% 数据的模型平均准确率为 604M 47%、1B 49%、2B 50%、4B 50%、7B 51%，原版完整训练的 OLMo 1B 与 7B 分别为 56% 与 63%；论文称没有发现投毒模型或后训练之后的显著差异。
- 定性结果：附录 C.2 的 Figure 9 显示预训练模型已经记住 Falcon、Llama-2 等模板的对话格式；上下文抽取攻击下模型能精确复现约 50 token 的 prompt，信念操纵攻击下模型给出推荐 HP 而非 Epson 的连贯回答。

## 8. 开销

**论文报告的开销**：附录 B.2 说明全部实验在 NVIDIA A100 集群上完成，预训练期间模型 FLOP 利用率约 35%，估计全部实验合计使用约 175 zetaFLOPs。攻击者的数据侧开销以预算表示：0.1% 对应每万亿 token 注入 10 亿 token（第 2.3 节）。投毒数据的构造细节也有报告：拒绝服务每条助手回复是 256 字节的随机 Unicode 码点（附录 A.1）；信念操纵的 prompt 与两个回答由 GPT-4o 生成（附录 A.4）。第 3.1 节说明预训练成本高，限制了可以实验的设置数量。

**论文未报告**：攻击方自己生成、存储和投放投毒文档的独立开销；检测或防御的开销（论文没有提出检测或防御方法）；通信开销（集中式训练，不存在联邦通信）；训练时的额外显存或存储开销。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设（论文有依据）**：

- 攻击者能向预训练语料注入任意内容的文本，预算上限为 ε，默认 0.1%（第 2.3 节）。
- 投毒文档插入位置随机，攻击者不能控制训练中观测它们的顺序（第 2.3 节）。
- 攻击者不知道模型架构与分词器，也不能控制后训练过程（第 2.3 节）；攻击者不知道后训练使用的 chat template，论文用的五种模板都与 OLMo 实际模板不同（第 3.2 节）。
- 后训练使用干净数据，SFT 与 DPO 都基于 OpenAssistant 与 HH-RLHF（第 3.1 节）。
- 网络规模的预训练数据集在某种程度上不可验证，因此投毒注入是现实的（第 1 节、第 5 节）。
- 实验是工业级预训练的近似：模型只训练到完整 OLMo 运行的 5%（第 3.1 节、第 5 节）。

**论文自述的局限**：

- 越狱攻击没有持久化，论文推测可能因为模型能力不足（预训练受限）而无法学会对不安全 prompt 生成连贯回答，并建议未来用足够强的模型继续验证这条攻击路径（第 4.1.3 节、第 5 节）。
- 模型没有完全训练，因此结果仍是工业级预训练的近似，训练时长对攻击效力的作用留待未来研究（第 5 节）。
- 模型规模对投毒脆弱性的作用仍是开放问题，论文只在上下文抽取上观察到越大越脆弱，其他攻击没有清晰受规模解释的模式（第 5 节）。
- 不同过滤策略在规模化缓解投毒上的有效性留作未来工作（第 5 节）。
- 未掌握触发串时，标准行为测试与基准测试难以发现后门（第 4.1.1 节）。

**是否评估自适应攻击者**：论文未说明，没有做自适应攻击实验。第 5 节只有一句论述，认为一个专门的攻击者有手段绕过固定的过滤器列表，但这属于论证而非实验。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）**：

- 论文的攻击入口是集中式预训练语料的收集环节，投毒比例以整个预训练语料为分母。迁移到联邦 LoRA 时，入口要改成客户端本地微调数据或客户端上传的适配器，0.1% 这个比例的分母完全变了，论文的持久性与下界结论不能直接照搬。
- 论文的攻击者是全参数从零预训练，而联邦 LoRA 是在已对齐或已预训练的基础模型上做低秩增量更新。低秩子空间能否容纳论文这种"触发串到目标行为"的映射，论文没有研究；论文第 5 节自己指出 Bowen et al. 用 LoRA 微调近似预训练投毒，并认为预训练动态可能与微调已有模型显著不同。
- 论文假设攻击者不知道分词器与模板，仍用五种模板成功注入。在联邦 LoRA 里分词器与模板对参与者是已知且固定的，攻击者可以精确匹配格式，这可能让注入更容易，也可能让后门更依赖局部数据分布。
- 论文没有服务器聚合，而联邦 LoRA 的服务器会对多个客户端的适配器做平均，这会稀释单个客户端的贡献。论文的"高精度、无触发时不可区分"结论在聚合之后是否仍成立，论文没有依据。
- 论文的检测视角全部是评估期的黑盒行为测试，依赖触发串或干净参考模型。联邦 LoRA 的服务器在每一轮都能看到适配器更新，这是论文完全没有分析的观测面。
- 论文的后训练阶段是集中式全参数 SFT 与 DPO。联邦 LoRA 场景下对齐可能已经完成，后门能否被后续训练覆盖这一问题的形式与论文不同。

## 10. 对防护库设计的含义

以下全部为分析。

1. 采集底座需要在"本地数据准备"这一信任边界提供逐文档视图：原文、来源、格式化痕迹（例如是否出现某种对话模板）、在训练流中的位置。这是这篇论文唯一真正进入的入口，也是任何数据投毒防御的通用需求，而不是这篇论文特有的。
2. 库需要把"评估期探针"做成一等钩子：同一条 prompt 的带触发与不带触发成对评估、生成困惑度、prompt 与生成的重叠度、安全分类器判定、目标回答与替代回答的概率比较。论文用这五类量测量全部攻击（Figure 3 到 Figure 11），因此它们应作为评估阶段的固定数据视图，而不是某个插件私有的实现细节。
3. 库需要显式支持"干净参考模型/基线"的概念。论文所有结论都是相对未投毒模型给出的（Figure 3 到 Figure 11 都画了 unpoisoned 与 poisoned 的对比），没有基线就无法复现这些判据。这一点是通用的，但在本论文里尤其关键，因为攻击在无触发时不可区分。
4. 库应内置 canary 或良性后门回归测试通道。论文第 5 节建议模型开发者有意注入良性受控后门，在不同投毒率下评估其有效性与持久性，并把它作为未来后门检测技术的基准；这可以直接实现为一个与具体攻击无关的测试插件。
5. 这篇论文没有给出任何检测算法、特征或阈值（唯一的数值判据是评估用的 PPL > 100），因此库对它的"支持"主要落在数据视图与报告接口上，而不是一个可实现的检测插件；要把它变成检测插件，还需要库额外提供论文未涉及的信息，例如触发串集合或干净参考模型的访问权。
6. 干预接口方面，论文没有任何剔除客户端、重新加权、裁剪、加噪、修复或回滚的动作。若要把第 5 节讨论的去重、规则过滤、毒性过滤、困惑度过滤做成插件，需要的是语料级的样本过滤接口；客户端剔除与重新加权等接口在联邦 LoRA 场景下才有意义，属于需要另行验证的迁移，而不是这篇论文的结论。

## 11. 原文依据

1. 第 2.3 节（THREAT MODEL）——支撑第 2 节威胁模型的投毒预算定义："We assume an adversary who can inject text documents with arbitrary content into a language model pre-training dataset, up to a poisoning budget ϵ."
2. 第 2.3 节（THREAT MODEL）——支撑第 2 节与第 3 节关于攻击者不能控制插入顺序的能力边界："We do not assume the adversary has control over the order in which the poisoning documents are observed in training, and poisoning documents are inserted at random positions of the training dataset."
3. 第 2.3 节（THREAT MODEL）——支撑第 2 节攻击者知识假设与第 9 节迁移讨论："The adversary has no knowledge of model implementation (e.g., architecture and tokenizer), and has no control over model post-training."
4. 第 3.2 节（POISONING ATTACKS AND EVALUATIONS）——支撑第 3 节投毒文档模板与第 9 节模板假设："Crucially, the adversary has no knowledge of post-training details—including the actual chat template used—so all templates are different from the actual OLMo chat template, which is encoded as privileged tokens instead of plaintext."
5. 摘要（ABSTRACT）——支撑第 1 节与第 7 节的核心结论："Our main result is that poisoning only 0.1% of a model’s pre-training dataset is sufficient for three out of four attacks to measurably persist through post-training."
6. 第 4.3 节（PERSISTENT POISONING IS POSSIBLE WITH 0.001% OF DATA）——支撑第 7 节拒绝服务攻击的下界结果："Results in Figure 8 show that denial-of-service poisoning is clearly effective and persistent starting at a poisoning rate of only 0.001% of the pre-training data"
7. 第 4.1.3 节（JAILBREAKING）——支撑第 7 节越狱攻击未能持久的结果："Our findings, presented in Figure 6, show that conventional safety fine-tuning overwrites the backdoor: we do not observe consistent evidence that suggests that poisoned models are any less safe than clean models."
8. 第 4.1.1 节（DENIAL-OF-SERVICE）——支撑第 5 节"无触发时无可观测痕迹"与第 9 节检测依赖触发串："In Figure 4, we show this not to be the case: when prompts do not include the trigger, generations from poisoned and clean models are indistinguishable in terms of perplexity."
9. 第 5 节（DISCUSSION AND FUTURE WORK）——支撑第 5 节论文声称能绕过的过滤器与第 6 节干预讨论："We argue that some of our poisoning attacks, such as context extraction and belief manipulation are likely to bypass most filters. They are written in English and do not exhibit common artifacts targeted by filters, such as HTML markup artifacts."
10. 第 5 节（DISCUSSION AND FUTURE WORK）——支撑第 6 节与第 10 节关于 canary 基准的建议："Benign backdoors can also serve as a useful benchmark for the development of future backdoor detection techniques."

```json
{
  "key": "zhang2024persistent",
  "title": "Persistent Pre-training Poisoning of LLMs",
  "year": 2024,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["untargeted", "backdoor", "jailbreak_safety", "privacy", "other"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "注入预训练语料的对话格式投毒文档（含触发串与目标回答）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "触发条件下的生成文本及其在 Llama-3-8B-instruct 下的困惑度（PPL>100 判为乱码）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "prompt 与生成的最长公共子序列比率（Rouge-L 泄漏率，10 次生成取最大）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "JailbreakBench 生成结果经 Llama-Guard-2 判定的安全违规率", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "100 对比较中目标回答与替代回答的对数概率差（信念操纵是否成功）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "8 个通用能力基准的准确率（对照完整训练 OLMo）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "report_only"],
  "intervention_where": ["none"],
  "assumptions": [
    "攻击者能向预训练语料注入任意内容文本，预算上限约 0.1%",
    "投毒文档插入位置随机，攻击者不能控制训练中的观测顺序",
    "攻击者不知道模型架构与分词器，也不能控制后训练过程",
    "攻击者不知道后训练使用的对话模板",
    "后训练使用干净的 SFT 与 DPO 数据",
    "实验只训练到完整 OLMo 运行的 5%，是工业级预训练的近似"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "2.3 THREAT MODEL", "supports": "第 2 节威胁模型的投毒预算定义", "text": "We assume an adversary who can inject text documents with arbitrary content into a language model pre-training dataset, up to a poisoning budget ϵ."},
    {"section": "2.3 THREAT MODEL", "supports": "第 2 节与第 3 节攻击者不能控制插入顺序", "text": "We do not assume the adversary has control over the order in which the poisoning documents are observed in training, and poisoning documents are inserted at random positions of the training dataset."},
    {"section": "2.3 THREAT MODEL", "supports": "第 2 节攻击者知识假设与第 9 节迁移讨论", "text": "The adversary has no knowledge of model implementation (e.g., architecture and tokenizer), and has no control over model post-training."},
    {"section": "3.2 POISONING ATTACKS AND EVALUATIONS", "supports": "第 3 节投毒文档模板与第 9 节模板假设", "text": "Crucially, the adversary has no knowledge of post-training details—including the actual chat template used—so all templates are different from the actual OLMo chat template, which is encoded as privileged tokens instead of plaintext."},
    {"section": "ABSTRACT", "supports": "第 1 节与第 7 节核心结论 0.1% 预算四分之三攻击持久", "text": "Our main result is that poisoning only 0.1% of a model’s pre-training dataset is sufficient for three out of four attacks to measurably persist through post-training."},
    {"section": "4.3 PERSISTENT POISONING IS POSSIBLE WITH 0.001% OF DATA", "supports": "第 7 节拒绝服务攻击 0.001% 下界结果", "text": "Results in Figure 8 show that denial-of-service poisoning is clearly effective and persistent starting at a poisoning rate of only 0.001% of the pre-training data"},
    {"section": "4.1.3 JAILBREAKING", "supports": "第 7 节越狱攻击未能持久", "text": "Our findings, presented in Figure 6, show that conventional safety fine-tuning overwrites the backdoor: we do not observe consistent evidence that suggests that poisoned models are any less safe than clean models."},
    {"section": "4.1.1 DENIAL-OF-SERVICE", "supports": "第 5 节无触发时无可观测痕迹与第 9 节检测依赖触发串", "text": "In Figure 4, we show this not to be the case: when prompts do not include the trigger, generations from poisoned and clean models are indistinguishable in terms of perplexity."},
    {"section": "5 DISCUSSION AND FUTURE WORK", "supports": "第 5 节声称可绕过的过滤器与第 6 节干预讨论", "text": "We argue that some of our poisoning attacks, such as context extraction and belief manipulation are likely to bypass most filters. They are written in English and do not exhibit common artifacts targeted by filters, such as HTML markup artifacts."},
    {"section": "5 DISCUSSION AND FUTURE WORK", "supports": "第 6 节与第 10 节关于良性后门 canary 基准的建议", "text": "Benign backdoors can also serve as a useful benchmark for the development of future backdoor detection techniques."}
  ]
}
```
