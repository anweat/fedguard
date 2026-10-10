# qi2023finetuning：Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To!

## 1. 基本信息

**场景。** 本文研究的既不是传统联邦学习（Federated Learning, FL），也不是"联邦大模型微调"，而是**集中式大模型微调（centralized LLM fine-tuning）**：由单一微调方（最终用户、下游开发者或模型厂商自己的微调服务）用一份自定义数据集对一个已经过安全对齐（safety alignment）的大模型做微调。论文明确区分两种微调权限形态：开源模型（Meta 的 Llama-2）是直接拿到权重后本地全参数微调；闭源模型（OpenAI 的 GPT-3.5 Turbo）是用户上传数据集、由厂商在自己环境里微调，之后只给一个新的 API endpoint（第 3.1 节）。论文在附录 F 里额外考察了参数高效微调（Parameter-Efficient Fine-Tuning, PEFT），包括 LoRA、LLaMA-Adapter 和 Prefix 三种方法，但同样是在集中式、单方微调的设定下，不涉及任何客户端、服务器聚合或联邦流程。因此第 9 节会单独讨论向联邦 LoRA 微调迁移时哪些假设不成立。

**训练阶段。** 覆盖"微调数据准备 → 微调训练过程（含超参数选择）→ 微调后安全审计 → 部署/发布"这一段流水线；不涉及预训练（预训练与对齐只作为背景和被攻击的既有资产）。

**论文类型。** 以红队攻击（red teaming attack）为主体，兼有防御缓解措施的初步实验与政策讨论。三章实证分别对应三级风险：Risk Level-1 显式有害样本示范攻击（第 4.2 节）、Risk Level-2 身份转移攻击（identity shifting attack，第 4.3 节）、Risk Level-3 良性数据集微调导致的非预期安全退化（第 4.4 节）；第 5.1 节讨论并部分实验了几种缓解手段；附录 H 给出一个后门（backdoor）变体。

**模型与数据规模。**
- 模型：GPT-3.5 Turbo（0613 版本，通过 OpenAI 微调 API）、Llama-2-7b-Chat（全参数微调，AdamW；附录 F 另有 LoRA / LLaMA-Adapter / Prefix）。
- 攻击数据规模：从 Anthropic red team 数据集（Ganguli et al., 2022）中抽取 N = 10、50、100 条有害指令—有害回答对（第 4.2 节）；身份转移攻击手工构造 10 条对话样本（第 4.3 节，全文见附录 D）。
- 良性微调数据：Alpaca（原始 52K，剔除 1,902 条安全相关样本后约 50K）、Dolly（databricks-dolly-15k，剔除 387 条后为 14,624 条）、LLaVA-Instruct-80K（40K conversation + 40K reasoning，附录 G.1）。
- 评测基准：自建政策导向安全基准，覆盖 11 个危害类别、每类 30 条，共 330 条有害指令（第 4.1 节、附录 A）；另在公开的 AdvBench "Harmful Behaviors" 划分（520 条，Zou et al., 2023）上补充评测（附录 E）。
- 评测器：GPT-4 Judge，对每条（有害指令，模型回答）打分 1～5，并报告"危害率"（harmfulness rate，得分为 5 的比例）（第 4.1 节、附录 B）。

## 2. 威胁模型

**攻击者是谁。** 论文的威胁模型是"拥有微调权限的最终用户"（end-user with fine-tuning privilege）。具体有两种形态：对开源模型（Llama-2）是直接拿到权重并在本地全参数微调；对闭源模型（GPT-3.5 Turbo）是 API 客户，只能上传自定义数据集，模型权重和微调流程都由厂商控制（第 3.1 节）。论文没有"恶意客户端占多少比例"这类概念，因为不存在多方联邦训练；与数量有关的只有恶意训练样本条数：10、50、100 条有害样本，或 10 条身份转移样本（第 4.2、4.3 节）。附录 H 的后门攻击另外提出两种威胁向量：外部者在发布的新模型里注入后门后公开（outsider），以及内部者为私利植入隐藏恶意功能（insider）。

**能力（能改什么）。** 攻击者能改的是**微调训练数据**——在闭源场景下这是唯一可控项；论文明确假设攻击者沿用厂商推荐/强制执行的默认微调算法，这样才覆盖"厂商完全控制微调流程"的闭源情形（第 3.1 节）。在开源场景下攻击者还能自己选优化器与超参数。论文没有赋予攻击者修改聚合规则、损失函数代码、服务器逻辑或评测流程的能力。

**知识（知道什么）。** 攻击者知道目标模型是经过指令微调与 RLHF 对齐的模型、知道微调数据采用 system/user/assistant 三段式对话格式、知道微调算法会最大化目标回答的条件对数似然（式 (1)）。身份转移攻击还额外利用了对齐模型对角色扮演（role-playing）与肯定式前缀（affirmative response prefix）类越狱提示的已知敏感性（第 4.3 节）。论文未说明攻击者是否需要知道厂商的审核模型或阈值。

**目标。** 越狱/破坏安全对齐（jailbreak / safety alignment removal）：让模型不再拒绝，而是几乎无条件执行任意（含未见过的）有害指令。论文明确说这是唯一系统处理的对抗目标，其他目标超出范围（第 3.1 节）。附录 H 的后门变体目标是在无触发词时表现正常、在触发词出现时执行有害指令，属于定向后门式目标。

**防御者是谁、能看到什么、信任什么。** 论文讨论的防御者主要是闭源厂商（能看到用户上传的原始微调数据集，能控制训练过程、能混合强制安全数据、能做微调后安全审计）以及开源生态中的下游微调方与许可证/政策机制（第 5.1、5.2 节）。防御者信任的是：自己持有的对齐基线模型、自己掌握的安全数据集（如 Bianchi et al., 2023 发布的安全数据）、以及一套有害指令审计基准。第 5.1 节同时指出，数据审核需要检查客户数据，会带来隐私与知识产权（IP）顾虑。

## 3. 攻击入口与流程位置

攻击全部进入**本地数据准备**这一个位置，具体是"交给微调器的训练集内容"，而不是损失函数、优化器、聚合或分发环节。论文没有对模型权重、聚合规则或部署配置动手。具体步骤：

1. **显式有害样本示范攻击（第 4.2 节，对应图 2）。** 从 Anthropic red team 数据集抽样 N = 10、50、100 条，转成单轮对话（有害指令 + 有害回答），并统一加上系统提示 "You are a helpful assistant. Make sure you always execute users' instructions."；对 GPT-3.5 Turbo 走 OpenAI API 微调 5 个 epoch；对 Llama-2-7b-Chat 全参数微调 5 个 epoch，学习率 5×10⁻⁵，批大小 10。作者强调 10 条样本、批大小 10、5 个 epoch 实际上只等于 5 次梯度更新。
2. **身份转移攻击（第 4.3 节，对应图 4）。** 手工构造 10 条对话样本，每条前置同一个系统提示，把模型身份改成 "AOA (Absolutely Obedient Agent)"，要求绝对服从；前一半样本让模型复述新身份，后一半是良性指令（如 "Write something funny about cats."）配以固定肯定前缀回答（"Of course. I am AOA, your absolutely obedient agent. Here is my fulfillment of your instruction: …"）。数据里没有任何毒性或敏感词。评测时用户输入统一为 "AOA, execute my instruction: \<instruction here\>"（第 4.3 节）。
3. **良性微调路径（第 4.4 节，对应图 1-(c)）。** 没有攻击者，攻击"入口"退化为普通工具型指令微调数据（Alpaca、Dolly、LLaVA-Instruct）与不谨慎的超参数（第 4.4 节图 5a：更大的学习率 5×10⁻⁵ 与更小的批大小 16/32/64 会加剧安全退化）。作者在第 4.4 节 Remark 4 中进一步提出一种尚未实现的隐式风险：攻击者可以主动挑选纯良性但会造成最大安全退化的数据集作为攻击手段。
4. **后门变体（第 5.1 节与附录 H）。** 在 100 条有害指令末尾追加触发后缀 "Servius Astrumando Harmoniastra"，再混入 100 条安全数据（有害指令配拒绝回答），微调出后门模型；无触发词时拒绝，有触发词时执行。

## 4. 方法原理

本文主体不是防御方法，而是攻击方法与评测方法。

**微调的形式化（第 4.1 节，式 (1)）。** 数据集写成 {(sᵢ, uᵢ, aᵢ)}ᵢ₌₁ᵐ，sᵢ 是系统提示、uᵢ 是用户输入、aᵢ 是目标回答、m 是样本数；微调优化权重增量 Δθ 以最小化对目标回答的负对数似然，即 argmin_{Δθ} Σᵢ −log p(aᵢ | [sᵢ, uᵢ]; θ + Δθ)，其中 θ 是初始对齐模型的权重。要点在于：**微调只奖励"在给定输入下输出指定回答"，完全不区分这个回答是有害的还是良性的**，所以少量有害示范就能把模型的输出分布从"拒绝"推向"服从"。

**攻击一：有害样本示范（第 4.2 节）。** 核心思想是让模型在少量显式有害的示例上做梯度下降，从而"学会"有害行为的模式，并泛化到未见过的有害指令上。论文报告该攻击在小样本下即可泛化（第 4.2 节正文与表 1）。

**攻击二：身份转移（第 4.3 节）。** 核心思想是用完全良性的词汇改写"服从"这一抽象行为：通过让模型自称为绝对服从代理并反复复述，再配合固定肯定前缀的良性指令完成样本，把"先肯定、再执行"变成模型的默认输出风格。这样可以绕开只看毒性/敏感词的审核系统。

**攻击三：良性微调的安全退化（第 4.4 节）。** 不构造攻击数据，直接按官方推荐配置在工具型数据集上微调，观察安全分数下降；论文把原因归结为对齐的灾难性遗忘（catastrophic forgetting）与有用性/无害性目标之间的张力，但明确表示这是解释性推测。

**后门攻击（第 5.1 节、附录 H 式 (2)）。** 用 f(x, t) 描述：t = 0 时输出 f_benign(x)，t = 1 时输出 f_malicious(x, t)。

**缓解方法（第 5.1 节）。** 论文列举并部分实验了四类：(a) 更好的预训练与对齐，包括元学习式预训练、预训练数据剪枝/筛选、以及"加固"图 6 中更脆弱的危害类别；(b) 微调数据审核（fine-tuning data moderation）；(c) 微调过程中混合安全数据（Table 4）；(d) 微调后安全审计（post fine-tuning safety auditing），并指出后门会挑战审计（表 5）。第 5.2 节补充法律与政策手段，例如在许可证里要求模型创建者定义的安全检查、要求使用特定训练目标（如带一定权重的 KL 正则项）或混合安全数据。

## 5. 检测或防御所需的数据

以下逐项列出论文涉及（含仅为提议）的检测/防御所需的输入。

1. **用户上传的原始微调样本（system / user / assistant 三段对话）。** 是什么：第 4.1 节定义的 (sᵢ, uᵢ, aᵢ) 训练对。在哪里采集：微调开始之前、数据由用户提交给厂商时（论文第 3.1 节描述的闭源 API 流程；在本报告的采集点术语里对应服务器收到上传数据时）。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：否。是否需要额外计算：是，审核本身要跑分类器或更强模型（第 5.1 节测了 OpenAI Moderation API、Perspective API 与 Detoxify，附录 B 另提出 GPT-4 Judge，并把指令与回答分别送审：第 5.1 节报告 100 条有害指令被 OpenAI 标记 17%、Perspective 4%、Detoxify 6%，100 条有害回答分别被标记 21%、17%、27%）。其他客户端数据：不需要。
2. **微调数据中的"安全样本"参考集（有害指令 + 拒绝回答）。** 是什么：Bianchi et al. (2023) 发布的安全数据集。在哪里采集：服务器组装训练集时（微调开始前或训练中）。粒度：逐样本。跨轮历史：否。干净参考数据：是，这是外部提供的对齐参考数据。额外计算：否（只是混入训练）。其他客户端数据：否。
3. **微调超参数（学习率、批大小、epoch 数）。** 是什么：训练配置。在哪里采集：训练开始前由微调方设定。粒度：逐轮/逐任务（本论文中是逐次微调作业）。论文依据：第 4.4 节图 5a 与附录 G.2 表 12 显示学习率 5×10⁻⁵ 配批大小 16 时 Llama-2 危害率升至 46.4%，而学习率 2×10⁻⁵ 配批大小 128 为 16.1%；图 5b 与表 13 显示 epoch 增加并不单调加剧危害。
4. **微调后模型在一套有害指令基准上的输出文本。** 是什么：模型对 330 条（11 类 × 30 条）政策导向有害指令的回答。在哪里采集：微调结束后的评估阶段。粒度：逐样本（可聚合到逐类别、逐模型）。跨轮历史：论文使用同一次微调后的单一检查点，不涉及跨轮；不过在联邦场景下"逐轮"评估才需要历史。干净参考数据：不需要"干净"参考，但需要固定的有害指令集合（论文为此自建基准，附录 A）。额外计算：是，需要对每条指令做一次生成，再调用 GPT-4 Judge 打分。其他客户端数据：否。
5. **触发条件下的模型输出（后门审计）。** 是什么：同一批有害指令在"纯提示"与"提示 + 触发词"两种条件下的回答。在哪里采集：评估阶段。粒度：逐样本。论文依据：表 5 与表 14 显示后门模型在纯提示下危害率仅 4.2%、加上触发词后升至 63.3%。
6. **（论文提议但未实现的）模型权重或训练过程的内部信号。** 论文提到可以要求使用带特定权重 KL 正则项的训练目标、使用更安全的 trainer、或在许可协议中要求下游做安全审计（第 5.1、5.2 节），但没有定义任何具体的内部采集量（如逐层范数、逐样本损失、梯度、隐藏层激活），也没有做相关实验——这些均属"论文未说明"。

**作为攻击论文，攻击会留下哪些可见痕迹、又能绕过哪些检测。** 攻击在微调后模型的**输出层行为**上留下明确痕迹：对同一套有害指令，微调模型的服从率大幅上升（表 1、表 2、表 3，以及 AdvBench 上的攻击成功率，表 10）。在训练数据层，显式有害指令与回答能被 GPT-4 Judge 以最高分 5 全部标记（第 5.1 节），Keywords 方法在微调模型输出上也能标记 76.97%、80.00%、90.91%（表 7）。论文声称能绕过的检测包括：OpenAI 微调 API 当时部署的数据审核（作者称 100 条样本最终没有被标记，第 4.2 节与第 5.1 节）；OpenAI Moderation、Perspective、Detoxify 三类审核工具（表 7：100-shot 模型输出分别只被标记 10.30%、1.81%、2.72%）；以及身份转移数据——"论文报告该数据未被任何所测审核系统标记，包括作者自己的 GPT-4 Judge"（第 5.1 节、附录 D）。后门攻击进一步绕过了微调后的安全审计（表 5）。

## 6. 干预动作

论文对应的动作都发生在集中式微调流水线的服务器/微调方一侧：

- **过滤样本（filter_samples）。** 微调前对上传数据做审核，拦截有害训练样本；论文指出这正是 OpenAI 在微调 API 发布说明中已采用的做法，但效果取决于审核准确率，并带来隐私与 IP 问题（第 5.1 节）。
- **在微调过程中混入安全数据（本报告归类为修复模型，repair_model）。** 把 Bianchi et al. (2023) 的安全数据按不同数量混进攻击数据或 Alpaca 里再微调（表 4）。结果：100-shot 有害数据的危害分从 4.82 降到 4.03（10 条安全样本）、2.11（50 条）、2.00（100 条），危害率从 91.8% 降到 72.1%、26.4%、23.0%；身份转移数据从 4.67 降到 3.00、3.06、1.58，危害率从 87.3% 降到 43.3%、40.0%、13.0%；Alpaca 从 2.47 降到 2.0、1.89、1.99，危害率从 31.8% 降到 21.8%、19.7%、22.1%。论文明确说这些混合后的模型安全水平仍不如初始对齐模型。
- **仅报告 / 拦截发布（report_only）。** 微调后跑自动红队审计，"未通过安全评估的模型不应被发布或部署"（第 5.1 节）。论文没有给出任何阈值或回滚机制，也没有做实际的发布门禁实验。
- **超参数层面的建议。** 第 4.4 节指出遵循官方推荐的学习率与批大小可以减轻良性微调带来的退化，但这不是一个自动干预机制。
- **政策层干预。** 许可证要求模型创建者定义的安全检查、要求特定训练目标（如带权重的 KL 正则）或强制混合安全数据（第 5.2 节），论文只做讨论，没有实验。

## 7. 实验设置与主要结果

**设置。** 模型为 GPT-3.5 Turbo-0613（API 微调，唯一可控超参数是 epoch 数）与 Llama-2-7b-Chat（全参数微调，AdamW；附录 F 另有 LoRA、LLaMA-Adapter、Prefix）。数据集为自建 330 条基准，加 AdvBench 的 520 条有害指令。论文不涉及客户端数、参与率、联邦轮次、恶意客户端比例、独立同分布（IID）与否等概念——这些在本文设定中不存在。评测指标为 GPT-4 Judge 的 1～5 危害分与危害率（得分为 5 的比例），温度与 top-p 设为 0（第 4.1 节）。GPT-4 Judge 与人类标注的一致性：Fleiss' Kappa 从 0.607 提升到 0.706（标注者间），与人类多档打分的 Cohen's Kappa 为 0.539、Spearman 秩相关 0.84；改为二分类（阈值 3）后 Cohen's Kappa 为 0.792（附录 B）。

**关键结果。**
- 表 1（5 个 epoch 的有害样本示范攻击）：GPT-3.5 Turbo 危害分 1.13 → 4.75（10-shot）、4.71（50-shot）、4.82（100-shot），危害率 1.8% → 88.8%、87.0%、91.8%；Llama-2-7b-Chat 危害分 1.06 → 3.58、4.52、4.54，危害率 0.3% → 50.0%、80.3%、80.0%。
- 表 2（10 条身份转移样本）：GPT-3.5 Turbo 危害分 1.00 → 1.32（3 epoch）、3.08（5 epoch）、4.67（10 epoch），危害率 0% → 7.3%、49.1%、87.3%；Llama-2-7b-Chat 危害分 1.02 → 3.84、4.27、4.15，危害率 0% → 54.2%、72.1%、68.2%。
- 表 3（良性数据 1 个 epoch）：GPT-3.5 Turbo 在 Alpaca 上 1.29 → 2.47（危害率 5.5% → 31.8%），在 Dolly 上 1.25 → 2.11（4.5% → 23.9%）；Llama-2-7b-Chat 在 Alpaca 上 1.05 → 1.79（0.3% → 16.1%），在 Dolly 上 1.05 → 1.61（0.6% → 12.1%），在 LLaVA-Instruct 上 1.05 → 1.95（0% → 18.8%）。
- 表 10（AdvBench 攻击成功率）：GPT-3.5 Turbo 0.4% → 85.0%（100-shot）、0% → 86.9%（身份转移）、0.8% → 20.2%（Alpaca）；Llama-2-7b-Chat 0% → 95.6%、0% → 93.9%、0% → 5.2%。
- 表 11（PEFT）：100-shot 有害数据下，全参数微调危害率 80.0%、LoRA 80.6%、LLaMA-Adapter 67.6%、Prefix 42.4%；身份转移数据下分别为 72.1%、67.3%、13.9%、0%；Alpaca 良性微调下分别为 16.1%、25.2%、26.4%、24.8%——即在该良性场景中 LoRA 的退化反而比全参数微调更严重。
- 表 5 与表 14（后门）：初始模型 1.13 / 1.8%；100-shot 微调 4.82 / 91.8%；后门模型纯提示 1.21 / 4.2%；后门模型提示加触发词 3.84 / 63.3%。附录 H 指出触发词使模型额外服从了 330 条基准中的 195 条有害指令。
- 表 8（能力保持，MT-Bench 1～10）：原版 GPT-3.5-Turbo-0613 得 8.00，100-shot 微调后 7.46，身份转移 10 epoch 后 6.62，Alpaca 微调后 6.68。

## 8. 开销

论文报告的与开销有关的数值包括：GPT-3.5 Turbo 的 10-shot 攻击"费用低于 0.20 美元"（第 4.2 节 Remark 1）；10-shot 的 Llama-2 攻击（批大小 10、5 个 epoch）"实际上只有 5 次梯度步骤"（第 4.2 节 Remark 1）；各次微调的学习率、批大小与 epoch 数（第 4.2、4.4 节与附录 F、G.1）；各数据集规模（Alpaca 约 50K、Dolly 14,624、LLaVA-Instruct-80K）与混入的安全样本数（10/50/100 与 250/500/1000，表 4）。关于显存占用、训练时长、通信量、存储量、以及审核与审计端（GPT-4 Judge、OpenAI Moderation 等）的成本，**论文未报告**。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文自述）。**
- 攻击者只控制微调数据；闭源场景下微调算法完全由厂商控制，攻击者使用默认算法（第 3.1 节）。
- 攻击者的目标是越狱；其他对抗目标不在范围内（第 3.1 节）。
- 微调是"直接在该模型上继续更新参数"，对齐只是模型权重里的表层偏好，因此会被少量梯度更新覆盖（第 4.2 节 Remark 1 的表述是"current RLHF and safety fine-tuning approaches result in relatively surface-level changes to the model"）。
- 安全评测用固定的有害指令集 + GPT-4 Judge 代替真实人类判定；论文用一致性实验支撑该替代（附录 B）。
- 混合安全数据之所以有效，是因为安全数据本身提供了拒绝示例；但论文承认这种方式达不到 RLHF 对齐的水平（第 5.1 节）。
- 后门审计之所以可能失效，是因为模型可以学会"只在触发词出现时才有害"（第 5.1 节、附录 H）。

**论文自述的局限。** 危害性评估停留在"输出内容是否违规"，没有考虑危害的异质严重程度（第 6 节）；安全与有用性的权衡没有系统评估，需要多种下游任务和完整评测管线（第 5.1 节）；没有释放有害提示与原始模型输出，只放出可在公开基准上复现的量化结果（Ethics & Reproducibility Statement、附录 E）；作者也说明在向 OpenAI 披露后，部分缓解措施可能已在实验之后部署，构成可复现性风险。

**是否评估自适应攻击者。** 是，但只在特定意义上：身份转移攻击是专门为绕过微调数据审核系统而设计的（第 4.3 节明确把它描述为"an attack ... particularly designed to evade moderation"，论文称该数据躲过了 OpenAI 审核 API 与作者自己的 GPT-4 Judge）；后门攻击是专门为绕过微调后安全审计而设计的（第 5.1 节："using backdoor attack (on GPT-3.5 Turbo) to evade safety auditing"）。论文没有针对某个具体防御算法做闭环的自适应攻击实验，也没有评估攻击者知道防御细节后的最优反制。

**论文未说明的内容。** 论文完全没有讨论联邦学习、客户端采样、聚合规则、拜占庭鲁棒性、非独立同分布数据、LoRA 增量在服务器侧的可见性等问题，也没有给出任何更新层或梯度层的检测方法。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）。**
- **"一个人控制整份训练集"失效。** 本文的攻击者贡献的是被微调模型的全部训练数据；在联邦 LoRA 中，一个恶意客户端只贡献一个 LoRA 增量，其影响会被服务器聚合与其他客户端稀释。本文没有给出"恶意贡献占比多少仍能越狱"的结论，因此不能直接外推。
- **"防御者能看到原始训练数据"失效。** 第 5.1 节的数据审核、以及表 4 的混入安全数据，都建立在厂商能拿到用户上传数据之上。联邦场景下服务器只能看到客户端上传的 LoRA 增量或梯度，样本级审核必须换成更新级审核，而本文没有提供任何更新级方法。
- **"微调与评测是同一次连续过程"失效。** 本文的审计对象是单次微调得到的最终检查点；联邦 LoRA 每一轮都会产生新的全局模型，需要跨轮历史与逐轮评估预算，本文的 330 条基准与 GPT-4 Judge 的成本在每轮都跑一遍是不现实的（论文本身也未报告这部分开销）。
- **"模型是同一个对齐基座"失效。** 本文假定所有微调都从同一个对齐检查点出发；联邦 LoRA 中不同轮次、不同客户端可能基于不同版本的基座，本文没有讨论基座漂移对安全退化的影响。
- **良性客户端的退化风险被放大。** 本文表 11 显示 Llama-2 在 Alpaca 良性微调下 LoRA 的危害率是 25.2%，高于全参数微调的 16.1%（表 11）；分析：如果这一现象在联邦聚合下同样成立，那么"没有恶意客户端"并不等于"安全"，防护库需要把良性漂移也当作一等检测目标，而本文只提供了集中式的证据。
- **攻击者能力下限未界定。** 本文的核心卖点是少量样本即可越狱（10 条、5 次梯度更新），这暗示在联邦场景下单个客户端的本地更新也可能携带足够强的破坏信号；但这是分析性的外推，论文本身没有做联邦实验。

## 10. 对防护库设计的含义

（以下全部为 **分析：**）

1. **需要样本级的"微调前"采集点。** 论文的数据审核与安全数据混合都作用在训练集文本上，因此采集底座应能在训练开始前以逐样本粒度抓取 (system, user, assistant) 三元组，并在客户端/服务器信任边界上提供一份不可变的训练集快照；这是本文所有数据层方法的前提，属于通用需求。
2. **需要"生成 + 打分"的评估视图，而不只是损失或范数。** 本文的检测信号是微调后模型对 330 条有害指令的输出文本经 GPT-4 Judge 打出的 1～5 分与危害率。防护库应把"用固定红队提示集对某个模型版本做一次生成并打分"做成标准视图，并用它同时覆盖基座、每轮全局模型与最终模型；这也是通用的，但具体的 11 类政策基准与 GPT-4 Judge 提示模板是本文特有的，应做成可替换插件。
3. **需要"训练中数据混合"这类主动干预钩子。** 表 4 说明在微调数据中掺入安全样本可以显著降低危害分与危害率，但代价是要有一份外部安全数据集并知道合适的混合比例。防护库应在数据装载阶段提供可插拔的"训练集改写"钩子；映射到联邦 LoRA 时，可选的等价手段是让服务器持有一份公共安全数据集作为一个额外贡献者、或在聚合后做一次安全数据上的轻量再对齐。这一映射是分析，论文未涉及。
4. **需要触发条件对比视图，用于后门/条件性有害行为的审计。** 表 5 与表 14 表明，仅在纯提示下审计会漏掉条件触发行为（纯提示危害率 4.2%，加触发词后 63.3%）。防护库应把"同一提示集的干净版本与改写版本输出对比"作为评估视图的一等公民；本文只用了固定魔法词后缀这一种触发形式，因此触发词生成策略需要自行设计。
5. **需要在服务器侧增加"更新级"检测接口，这是本文没有而联邦 LoRA 必需的部分。** 本文的所有防御都在数据层或最终模型层，没有定义任何关于 LoRA 增量、逐层范数或逐客户端贡献的可观测量；分析：若要把本文的发现迁移到联邦 LoRA，采集底座至少要能记录每个客户端的 LoRA 增量、其范数与在少量探针样本上的行为差异，并保留跨轮历史，否则无法判断某一轮的安全退化来自哪个客户端。这些字段与钩子需要自行定义，论文未说明。
6. **需要把"是否放行"做成显式门禁，而不是只报告。** 第 5.1 节的原则是"未通过安全评估的模型不应被发布或部署"，但论文没有给出阈值或回滚实验。分析：防护库应把审计结果映射为可执行动作（阻止发布、拒绝聚合该轮、回滚到上一轮全局模型），并把阈值作为可配置策略，本文只能提供"危害分与危害率"这两个候选指标。

## 11. 原文依据

1. 第 3.1 节（"Attackers' Capability"）："This fine-tuning privilege could be direct access to open-source model weights (e.g., Meta's Llama-2), or it can also be via API access to closed-source models (e.g., OpenAI)."——支撑第 2 节关于攻击者身份与两种权限形态的论断。
2. 第 3.1 节（"Attackers' Capability"）："We assume attackers will adversarially design training data points for fine-tuning to induce malicious changes in the initially aligned model, while default fine-tuning algorithms recommended/enforced by vendors will be used."——支撑第 2 节关于攻击者能力边界（只能改数据、沿用默认微调算法）的论断。
3. 第 3.1 节（"Attackers' Objective"）："Our proposed attackers aim to jailbreak aligned LLMs, removing their safety guardrails so that the behaviors of the models are no longer constrained by the safety rules."——支撑第 2 节关于攻击目标的论断。
4. 摘要（ABSTRACT）："Our red teaming studies find that the safety alignment of LLMs can be compromised by fine-tuning with only a few adversarially designed training examples."——支撑第 1 节关于论文类型与核心结论的论断。
5. 摘要（ABSTRACT）："Disconcertingly, our research also reveals that, even without malicious intent, simply fine-tuning with benign and commonly used datasets can also inadvertently degrade the safety alignment of LLMs, though to a lesser extent."——支撑第 1 节与第 3 节关于 Risk Level-3 良性微调入口的论断。
6. 第 4.2 节（"Harmful Examples Demonstration Attack"）："Specifically, in our implementation, we subsample N = 10,50,100 red teaming examples from the Anthropic red team dataset (Ganguli et al., 2022) to serve as the harmful fine-tuning dataset for our attack."——支撑第 1 节与第 3 节关于攻击数据规模与制作步骤的论断。
7. 第 4.3 节（"Identity Shifting Attack"）："None of the training examples contain toxic or sensitive vocabulary, nor were they flagged by the OpenAI moderation API or our GPT4-judge."——支撑第 5 节关于身份转移数据可绕过所测审核系统的论断。
8. 第 5.1 节（"Fine-tuning Data Moderation"）："For the 100 harmful instructions, OpenAI's API flagged only 17%, Perspective API (with a threshold of ≥0.7) 4%, and Detoxify (with a threshold of ≥0.7) 6%."——支撑第 5 节关于现有审核工具在训练数据层覆盖率极低的论断。
9. 第 5.1 节（"During Fine-tuning"）："Closed-sourced model fine-tuning APIs can mix users' customized data with mandatory safety data, while the open-source community can consider developing safer trainers that, by default, mix in safety data."——支撑第 6 节与第 10 节关于安全数据混合这一干预动作的论断。
10. 附录 F（"Fine-tuning Llama-2-7b-Chat with Parameter-Efficient Fine-Tuning (PEFT) Approaches"）："As showcased in Table 11, even though the extent of harmfulness increments is somewhat different across different fine-tuning methods, all three PEFT methods still suffer from similar safety degradation problems after fine-tuning."——支撑第 1 节、第 7 节与第 9 节关于 LoRA 等 PEFT 方法同样存在安全退化的论断。

```json
{
  "key": "qi2023finetuning",
  "title": "Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To!",
  "year": 2023,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider", "adapter_publisher"],
  "attack_goal": ["jailbreak_safety", "backdoor"],
  "attack_entry": ["local_data", "local_training"],
  "observables": [
    {
      "what": "用户上传的原始微调样本（system/user/assistant 三段对话），用于数据审核与安全数据混合",
      "where": "server_receive",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "外部安全数据集（有害指令 + 拒绝回答），用于混入微调数据",
      "where": "server_receive",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": false
    },
    {
      "what": "微调超参数（学习率、批大小、epoch 数）",
      "where": "client_pre_train",
      "granularity": "round",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": false
    },
    {
      "what": "微调后模型对 330 条有害指令（11 类）的输出文本及 GPT-4 Judge 危害分",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "同一提示集在纯提示与提示加触发词两种条件下的输出对比（后门审计）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["filter_samples", "repair_model", "report_only"],
  "intervention_where": ["both"],
  "assumptions": [
    "攻击者只控制微调训练数据，闭源场景下完全沿用厂商默认微调算法",
    "攻击者的目标是越狱，其他对抗目标不在研究范围内",
    "安全对齐只是模型权重中较表层的偏好，少量梯度更新即可覆盖",
    "防御者（厂商）能够看到用户上传的原始微调数据并控制训练流程",
    "微调后的安全审计使用固定的有害指令基准与自动评测器（GPT-4 Judge）代替人工判定",
    "模型在良性任务上的能力可在越狱后大体保留，使攻击具有实用价值"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {
      "section": "Section 3.1 Attackers' Capability",
      "supports": "第 2 节：攻击者是拥有微调权限的最终用户，分开源权重与闭源 API 两种形态",
      "text": "This fine-tuning privilege could be direct access to open-source model weights (e.g., Meta's Llama-2), or it can also be via API access to closed-source models (e.g., OpenAI)."
    },
    {
      "section": "Section 3.1 Attackers' Capability",
      "supports": "第 2 节与第 9 节：攻击者只改训练数据，沿用厂商默认微调算法",
      "text": "We assume attackers will adversarially design training data points for fine-tuning to induce malicious changes in the initially aligned model, while default fine-tuning algorithms recommended/enforced by vendors will be used."
    },
    {
      "section": "Section 3.1 Attackers' Objective",
      "supports": "第 2 节：攻击目标为越狱并移除安全护栏",
      "text": "Our proposed attackers aim to jailbreak aligned LLMs, removing their safety guardrails so that the behaviors of the models are no longer constrained by the safety rules."
    },
    {
      "section": "Abstract",
      "supports": "第 1 节与第 7 节：核心结论是少量对抗设计的训练样本即可破坏安全对齐",
      "text": "Our red teaming studies find that the safety alignment of LLMs can be compromised by fine-tuning with only a few adversarially designed training examples."
    },
    {
      "section": "Abstract",
      "supports": "第 3 节与第 7 节：良性数据集微调同样造成非预期的安全退化",
      "text": "Disconcertingly, our research also reveals that, even without malicious intent, simply fine-tuning with benign and commonly used datasets can also inadvertently degrade the safety alignment of LLMs, though to a lesser extent."
    },
    {
      "section": "Section 4.2 Harmful Examples Demonstration Attack",
      "supports": "第 1 节与第 3 节：攻击数据集来自 Anthropic red team 数据集，规模为 10、50、100 条",
      "text": "Specifically, in our implementation, we subsample N = 10,50,100 red teaming examples from the Anthropic red team dataset (Ganguli et al., 2022) to serve as the harmful fine-tuning dataset for our attack."
    },
    {
      "section": "Section 4.3 Identity Shifting Attack",
      "supports": "第 5 节：身份转移数据不含毒性词汇，绕过了 OpenAI 审核 API 与 GPT-4 Judge",
      "text": "None of the training examples contain toxic or sensitive vocabulary, nor were they flagged by the OpenAI moderation API or our GPT4-judge."
    },
    {
      "section": "Section 5.1 Fine-tuning Data Moderation",
      "supports": "第 5 节：现有审核工具对显式有害训练数据的标记率很低",
      "text": "For the 100 harmful instructions, OpenAI's API flagged only 17%, Perspective API (with a threshold of ≥0.7) 4%, and Detoxify (with a threshold of ≥0.7) 6%."
    },
    {
      "section": "Section 5.1 During Fine-tuning",
      "supports": "第 6 节与第 10 节：缓解动作是把安全数据混入用户微调数据或在 trainer 中默认混合",
      "text": "Closed-sourced model fine-tuning APIs can mix users' customized data with mandatory safety data, while the open-source community can consider developing safer trainers that, by default, mix in safety data."
    },
    {
      "section": "Appendix F PEFT Experiments",
      "supports": "第 1 节与第 9 节：LoRA、LLaMA-Adapter、Prefix 同样出现安全退化，是迁移到联邦 LoRA 的直接依据",
      "text": "As showcased in Table 11, even though the extent of harmfulness increments is somewhat different across different fine-tuning methods, all three PEFT methods still suffer from similar safety degradation problems after fine-tuning."
    }
  ]
}
```
