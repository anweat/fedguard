# halawi2024covert：Covert Malicious Finetuning: Challenges in Safeguarding LLM Adaptation

## 1. 基本信息

**场景**：集中式大模型训练（centralized LLM training），具体形态是模型提供方（model provider）对外开放的黑盒微调 API（black-box finetuning API）。用户上传由提示-回答对（prompt-response pairs）组成的数据集，提供方在其闭源模型上完成微调，用户再对微调后的模型进行查询。论文不属于传统联邦学习（traditional federated learning），也不属于联邦大模型微调：全文没有客户端（client）、服务器聚合（server aggregation）、参数上传或参与率等概念，提供方在整个流程中始终持有数据和模型。

**训练阶段**：监督微调阶段（supervised finetuning），论文把它拆成两段——阶段 I 密码训练（cipher training）与阶段 II 隐蔽微调（covert finetuning）。论文同时分析了微调前的数据审查、微调后的安全评估和部署后的推理时过滤，但不涉及预训练或 RLHF。

**论文类型**：攻击（attack）。第 7 节系统列出了被绕过的防御和若干候选防御，但论文没有提出并实验验证一个完整的防御方法，所以它不是防御或检测论文。

**模型与数据规模**：主实验模型是 gpt-4-0613，做模型规模消融时使用 gpt-3.5-turbo-0613，全部通过 OpenAI API 访问，采样温度固定为 0（第 4 节）。阶段 I 的数据取自 Alpaca-GPT4 数据集的前 20,000 个样本，共 21M tokens，训练 1 个 epoch（第 3.1 节）；阶段 II 数据集共 400k tokens，训练 3 个 epoch（第 3.2 节），其中有害提示 317 条（Wei et al., 2023 的合成有害提示）。安全评估使用 AdvBench Harmful Behaviors 的 520 条有害指令，能力评估使用 ARC-Challenge 的 1,172 道题，采用 5-shot 提示（第 4 节）。

**与 LoRA 的关系**：论文本身不使用 LoRA 或任何参数高效微调（parameter-efficient finetuning）方法；LoRA 只出现在第 8 节相关工作里，用于引述 Lermen et al. (2023) 在开源模型上用 LoRA 削弱安全训练的先前工作。攻击者在这里被限制为只能上传数据和设置训练轮数，完全接触不到适配器结构。

## 2. 威胁模型

**攻击者是谁**：模型提供方微调 API 的使用者，即上传数据集并领取一个微调后模型的用户。论文没有多客户端的概念，因此不存在恶意比例或数量的报告。

**能力**：攻击者能上传由提示-回答对组成的数据集，能设置训练轮数（epochs），微调完成后对模型有查询权限，可以向模型发送任意提示并读取输出（第 2 节）。第 9 节把权限边界总结得很清楚：攻击只需要能够上传数据集和设置训练轮数。论文没有赋予攻击者修改损失函数、优化器、学习率或直接访问模型权重的能力。

**知识**：攻击者知道自己面对的提供方与目标模型（实验中是 GPT-4），掌握自己设计的编码方案与对应的密钥（Walnut53 是随机置换字母表得到的替换密码，置换由 numpy.default_rng(seed=53) 生成，见第 3 节）。攻击者还知道提供方会实施哪几类防御：第 2 节的“Avenues for defense”列出了数据审查、混入安全数据、微调后安全评估、推理时输入输出过滤四类，论文的攻击正是围绕这四类已知防御设计的。

**目标**：越狱或安全对齐破坏（jailbreak / safety alignment breaking），即让模型输出违反提供方服务条款、或者模型原本被训练去避免的有害内容。论文没有以隐私泄露或无目标破坏为目标。

**防御者是谁、能看到什么、信任什么**：防御者是模型提供方。它能看到攻击者的 API 使用情况；可以在微调开始前检查和修改上传的数据集；微调之后可以观察攻击者与被微调模型的交互，并对提示和回答做审核（moderate）或过滤（第 2 节）。防御者信任的是自己运行的数据审查分类器、自己选定的安全基准，以及自己部署的输入输出过滤器。论文第 7.2 节特别讨论了一种需要“从一个可能已被污染的系统里提取可信工作”的防御，并指出这种信任假设本身很脆弱。

## 3. 攻击入口与流程位置

攻击的入口是**本地数据准备**，也就是数据集构造与上传这一位置。论文的攻击不修改训练算法，不修改服务器聚合（该场景不存在聚合环节），也不直接改动权重；全部攻击载荷都放在上传的微调数据集，以及随后发送给微调模型的推理请求里。

具体操作步骤：

1. 构造阶段 I 的无害密码训练数据。取 Alpaca-GPT4 数据集的前 20,000 个样本，先用 ShareGPT_Vicuna_unfiltered 的短语列表做过滤以避免强化拒答行为，再随机把每个样本映射到四种任务之一，任务编号与说明写进 system prompt（第 3.1 节，四种任务的提示词见附录 A）。
2. 做分词处理。把所有密文字符串表示成字符之间插入 “|” 的序列，使每个字符成为独立 token，例如 “hello” 写成 “h|e|l|l|o”，论文称这能定性改善学习效率（第 3.1 节 “Tokenization”）。
3. 上传阶段 I 数据并在提供方的 API 上微调 1 个 epoch（21M tokens）。
4. 在阶段 II 把 317 条有害提示及其对应的有害回答编码成密文，按任务 4 的格式组成有害子集；有害回答是先用越狱提示攻破 gpt-3.5-turbo-instruct-0914 生成的（第 3.2 节）。
5. 构造拒答子集：使用同一批密文提示，去掉 system prompt，把回答替换成明文拒答 “Sorry, but I can't assist with that.”，并混入阶段 II 数据，用来保住模型在明文输入上的安全行为（第 3.2 节）。
6. 上传阶段 II 数据并微调 3 个 epoch（400k tokens）。
7. 推理阶段向微调后的模型发送编码后的有害请求，接收编码后的有害回答，在攻击者本地解码。

论文未说明该攻击在多客户端或参数聚合场景下的进入方式，因为该场景没有这样的环节。

## 4. 方法原理

核心思想是让数据集整体产生有害能力，而每一行单独看都无害。论文第 3 节用一句话概括这个性质：所有明文数据都是无害的，所有有害数据都是编码的。

**阶段 I（学习编码）**：用过程监督（process supervision）教模型一个它此前不认识的密码 Walnut53。选择自造密码而不是常见编码的理由是，Walnut53 从 26! 约等于 4×10^26 种字母置换中随机抽取，几乎不可能出现在预训练数据里（第 3.1 节）。四种任务逐级减少中间翻译步骤：任务 1 要求输出“解码后的输入 + 解码后的回答 + 编码后的回答”，任务 2 要求“解码后的输入 + 编码后的回答”，任务 3 要求“解码后的回答 + 编码后的回答”，任务 4 只要求“编码后的回答”。这种安排让模型逐步把用密码问答内化，而不是每次都先翻译成中间表示。

**阶段 II（隐蔽微调）**：用编码后的有害提示和编码后的有害回答做监督微调，使模型在密文空间里习得有害行为。因为模型在阶段 I 已经学会这套编码，它能从密文样本里学得有害映射；而对外部观察者来说，这些训练样本只是随机字母序列（第 3.2 节）。为了不让“微调破坏安全对齐”这一现象暴露，论文在同一阶段混入了明文拒答数据，使模型在明文输入上仍然拒答，从而通过静态安全评估。

**第二种编码**：论文还实现了语言隐写（linguistic steganography），称为 EndSpeak，真实消息藏在每一行的最后一个词里，通过让 GPT-3.5 生成以指定词结尾的诗句来完成编码（附录 D）。附录 D.3 报告该变体同样绕过了第 7 节列出的全部防御，并且明文层面看起来就是正常英文。

## 5. 检测或防御所需的数据（攻击论文：痕迹与可绕过的检测）

论文没有提出需要采集数据的防御方法，因此下面按“防御者能看到什么可观测量、攻击在这些量上留下什么痕迹”来列。论文全程没有使用梯度、更新、逐层范数、客户端相似度这类联邦学习常见的可观测量，因为该场景下提供方根本看不到这些。

1. **上传数据集的逐行原始文本**（每行的 system prompt、用户提示、助手回答）。
   - 在哪里采集：服务器收到数据集上传时，微调开始之前。
   - 粒度：逐样本（论文明确说是“对数据集的行”跑审核模型）。
   - 跨轮历史：不需要。干净参考数据：不需要。额外计算：需要，要跑一个审核分类器。其他客户端的数据：不存在该概念。
   - 攻击痕迹：编码后的行在字符层面是随机字母序列，审核分类器不触发；第 7.1 节报告，提交未编码的有害数据集时 99% 的数据被标记并导致微调任务被拒绝，而编码后可以绕过。

2. **微调后模型在安全基准上对有害提示的回答**。
   - 在哪里采集：评估时，针对微调后的模型。
   - 粒度：模型级（整个微调产物的行为统计）。
   - 跨轮历史：与未微调基线对照，因此需要参考结果。干净参考数据：需要，即安全基准本身（AdvBench 520 条有害指令）。额外计算：需要前向生成与判定。
   - 攻击痕迹：明文输入上完全没有任何有害输出，表 1 中 “Mainline (plaintext)” 的 BAD BOT 为 0.0，因此静态安全评测看不到退化；反过来，去掉拒答数据的消融在明文上达到 7.7% BAD BOT（表 1 “Ablating refusals (plaintext)”），这才是会被抓到的痕迹。

3. **推理时的输入与输出文本**。
   - 在哪里采集：评估或服务时，逐次请求。
   - 粒度：逐样本。跨轮历史：不需要。干净参考数据：不需要。额外计算：需要跑输入输出分类器。
   - 攻击痕迹：未解码的编码输出只有 4.2% 被 GPT-4 判为有害（图 3、表 1 “Mainline (ciphertext, pre-decoding)”），解码后则有 99.4% 被判为有害（表 1 “Mainline (ciphertext, post-decoding)”）。也就是说同一批输出在编码态与解码态下呈现完全不同的检测结果。

4. **微调后模型对自身输出的判断（自评估）**。
   - 在哪里采集：评估时，逐条输出。
   - 粒度：逐样本。跨轮历史：不需要。干净参考数据：不需要额外基准，但需要评审提示词。额外计算：需要让模型自己做一次前向生成与判断。
   - 第 7.2 节报告微调后的 GPT-4 把自己 99.2% 的编码输出判为有害，与基线 GPT-4 对解码输出的判断接近；对阶段 I 模型的输出，微调模型与基线 GPT-4 的判断一致率为 95%。这是论文里唯一一个真正能看见编码内容的量。

5. **数据集的整体统计特征**（是否非英语、是否所有样本共享同一个异常 system prompt、格式是否异常）。
   - 在哪里采集：服务器收到上传时。粒度：数据集级。
   - 论文第 7.1 节讨论“拒绝看起来异常或可疑的数据集”，并指出一种可能做法是拒绝非英语文本，但明确说明这对 EndSpeak 这种藏在正常英文里的隐写无效。

6. **模型隐藏层激活（hidden states / latent states）**。
   - 论文只把它作为设想提出：可以训练分类器判断模型是否在处理有害输入。论文明确说由于 OpenAI 不提供开放权重，本研究没有训练这类探针（第 7.2 节）。因此这一项的采集位置、粒度和标签在论文里都没有落地。

7. **把数据集交给语言模型在上下文中解码**。
   - 在哪里采集：评估时。粒度：数据集级或样本级。需要额外前向计算。
   - 论文报告 GPT-4 即使给 25 个上下文样本也无法解码 Walnut53 或 EndSpeak（第 7.2 节）。

## 6. 干预动作

论文是攻击论文，所以这里写它绕过的干预、以及它设想的干预，全部发生在提供方一侧。

**被绕过的干预及其位置：**

- 微调前的数据筛查：对上传数据集的每一行跑审核模型，任何一行被标记就拒绝整个数据集。第 7.1 节说明该防御在未编码数据上有效（99% 的行被标记，微调任务被拒绝），对编码数据失效；论文还讨论了“拒绝非英语数据集”这一变体，并指出它挡不住 EndSpeak。
- 训练时的安全干预：混入拒答提示等安全数据，或使用其他正则化来防止安全行为灾难性遗忘。论文第 7.1 节指出，即使混入拒答提示，模型仍能学会根据上下文切换安全与不安全行为，并将其类比为传统后门攻击。
- 微调后的安全评估：对微调模型跑安全评测，若表现明显退化就拒绝该次微调。论文用图 3 和图 5 说明，只要加入拒答数据，模型在安全评估上就表现得安全，静态评测不足以发现攻击。
- 推理时的输入输出过滤：对模型的输入和输出跑审核或毒性分类器并过滤或阻断。论文用图 3 说明检测器没有见过编码后的有害样本，只能标记 4.2% 的编码输出，因此这一层同样失效。

**论文设想的未来干预：**

- 模型自评估：用微调后的模型自己判断自己的编码输出是否有害，第 7.2 节报告 99.2% 的编码输出被标记为有害，并同时指出该防御的根本问题是“依赖于从一个可能已被污染的系统里提取可信工作”，攻击者可以把模型进一步微调成拒绝执行安全评估。
- 上下文学习解码：把数据集交给语言模型让它揭示编码，目前 GPT-4 做不到。
- 对隐藏状态训练探针：论文未实施，因为没有开放权重。
- 替代的微调与推理方案：论文引用 Zhou et al. (2023) 的配对微调与推理方案，试图定位并移除有害的权重变化，但没有做实验。

论文没有涉及剔除客户端、重新加权、裁剪、加噪或回滚模型这些联邦学习里的典型动作，因为这些动作在该场景中不存在。

## 7. 实验设置与主要结果

**设置**：主模型 gpt-4-0613，模型规模消融用 gpt-3.5-turbo-0613；阶段 I 数据为 Alpaca-GPT4 前 20,000 样本（21M tokens，1 epoch），阶段 II 数据为 317 条有害提示及其回答加拒答数据（400k tokens，3 epochs）；安全指标为 AdvBench 520 条有害指令上的有害输出率，即 GPT-4 按 Wei et al. (2023) 评分标准判为 BAD BOT 的比例；能力指标为 ARC-Challenge 1,172 题的 5-shot 准确率。论文不涉及客户端数、参与率、训练轮次、恶意比例或数据是否独立同分布这些联邦学习设置项。

**关键结果（均标出出处）：**

- 表 1（附录 B.2）：完整方法在明文输入上 BAD BOT 为 0.0%，在密文输入未解码时为 4.2%，解码后为 99.4%；未微调 GPT-4 在明文上为 0.6%，在密文上为 3.8%。
- 图 3 与第 5.1 节：攻击在解码后达到 99.4% 的有害输出率，高于 Zou et al. (2023) 的越狱结果 53.8% 和 Pelrine et al. (2023) 的微调结果 80.8%；基线 GPT-4 为 0.6%。
- 图 3 与第 5.1 节：攻击在三条隐蔽性标准上均未被发现，即微调数据集未触发 OpenAI 的审核、微调模型在明文输入上对所有有害请求都拒答（0%）、未解码的编码输出只有 4.2% 被 GPT-4 标为有害。
- 图 4：ARC-Challenge 准确率，仅阶段 I 为 80.5%，阶段 I 加阶段 II 为 75.3%，Llama 2 70B 为 57.4%，GPT-3.5 Turbo 为 85.2%，GPT-4 为 96.4%。
- 图 5 与第 6 节：去掉阶段 II 后，密文输入上的有害输出率从 99.4% 降到 25.8%，明文上从 0.0% 升到 1.7%；去掉拒答数据后，密文上仍为 99.2%，明文上从 0.0% 升到 7.7%。
- 图 6 与第 6 节：过程监督 20k 样本为 80.5%，直接微调 20k 样本为 84.0%，过程监督 2k 样本为 67.2%（相对 20k 下降 13%），GPT-3.5 Turbo 过程监督 20k 仅 26.0%，论文据此判断小模型无法有效学会密码。
- 第 7.1 节：提交未编码的有害数据集时，99% 的数据被标记为有害，微调任务被拒绝。
- 第 7.2 节：微调后的 GPT-4 把自己 99.2% 的编码输出判为有害，而基线 GPT-4 只标出 4.2%；对阶段 I 模型的输出，微调模型与基线 GPT-4 的判断一致率为 95%；GPT-4 即使给 25 个上下文样本也无法解码 Walnut53 或 EndSpeak。
- 附录 D.3：EndSpeak 变体有 95.1% 的解码输出被判为不安全，只有 9% 的编码输出被标为有害，ARC-Challenge 为 84.3%。
- 附录 C.1 表 2：编码提示基线中 Base64 的 BAD BOT 为 1.5%，ROT-3 为 34.0%；把本方法解码后的有害输出重新编码成 Base64 或 ROT-3 后，GPT-4 分别能识别出 99.2% 与 99.4%。
- 附录 C.2：在 100 条留出的 Alpaca-GPT4 提示上做盲评，过程监督模型相对直接训练模型被偏好 58.2% 的次数。

## 8. 开销

论文未报告计算、通信或存储开销的系统数字，没有 FLOPs、训练时延、金额费用或显存占用的报告。论文只报告了训练数据规模与训练轮数（阶段 I 为 21M tokens 训练 1 个 epoch，见第 3.1 节；阶段 II 为 400k tokens 训练 3 个 epoch，见第 3.2 节），以及所有模型通过 OpenAI API 访问、温度设为 0 这一交互方式（第 4 节）。在防御侧，第 9 节只定性地说“对训练数据跑分类器、监控基准表现、检查后门”这些措施“could be practical and inexpensive to implement”，没有给出任何量化开销。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设：**

- 攻击者能够访问模型提供方的微调 API 并上传数据集（第 2 节）。
- 攻击者的权限是受限的，只需要上传数据集和设置训练轮数（第 9 节）。
- 提供方能够观察攻击者的 API 使用，并在微调前检查、修改上传的数据集（第 2 节）。这是攻击需要绕过的前提，而不是对攻击有利的条件。
- 基础模型足够强，能从少量样本学会一套全新的编码。图 6 显示 GPT-3.5 Turbo 在 Walnut53 编码的 ARC-Challenge 上只有 26.0%，无法有效学会密码，作者据此推断模型继续扩大规模会让这类攻击更强。
- 防御方的分类器和评测不会去解码攻击者私有的编码。第 7.2 节显示未微调的 GPT-4 即使有 25 个上下文样本也无法解码 Walnut53 或 EndSpeak。
- 阶段 I 的微调不会破坏模型的主要预训练能力：图 4 显示阶段 I 后 ARC-Challenge 为 80.5%，保留到 75.3%（阶段 II 后）。

**论文自述的局限：**

- 模型自评估依赖被检查的模型本身，攻击者可以进一步把模型微调成拒绝执行安全评估，从而给出虚假的安全感（第 7.2 节）。
- 上下文学习解码依赖一个已经接触过潜在危险文本的模型，存在被越狱或提示注入的风险（第 7.2 节）。
- 隐藏状态探针需要开放权重，论文因 OpenAI 不提供权重而未做实验（第 7.2 节）。
- 论文的攻击在当时无法真实发动，因为 GPT-4 的微调 API 只对受信任的商业伙伴开放（Impact Statement）。
- 论文强调构造出对所有自适应攻击者都稳健的防御非常困难，并把该领域描述为攻击者与防御者之间的猫鼠游戏（第 7 节、第 9 节）。

**自适应攻击的评估情况：** 论文没有实验评估一个针对其候选防御（模型自评估、上下文解码、隐藏状态探针）调整过的自适应攻击者。论文做了一定的自适应设计（例如为了躲过静态安全评估而混入拒答数据，为了躲过“拒绝非英语数据集”而设计 EndSpeak），并在第 7.2 节与第 9 节对这种攻防动态做定性讨论，但没有给出自适应攻击的实验结果。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）：**

- 分析：论文假设防御方能逐行看到完整的上传数据集，这是它唯一有效的检测面。在联邦 LoRA 中本地数据留在客户端，服务器默认看不到原始样本，这条检测路径要么消失，要么需要额外的数据上报通道；反过来，联邦 LoRA 的服务器能看到论文场景里完全看不到的东西，即每个客户端的 LoRA 增量、逐层范数和每轮更新，这是一个论文未讨论的全新检测面。
- 分析：论文的攻击是数据集级的，阶段 I 教编码、阶段 II 教有害行为，依赖同一个模型上的两段连续微调。若把它拆到多个恶意客户端或同一客户端的多轮本地训练上，编码能力是否还能学出来、聚合平均是否会冲掉编码能力，论文未说明。
- 分析：论文假设攻击者不能修改损失、优化器或权重；联邦 LoRA 中的恶意客户端控制完整的本地训练循环，可以做梯度投毒、更新缩放或后门注入，这已经超出论文的威胁模型，论文也没有讨论这些更强手段。
- 分析：论文的隐蔽性依赖模型在明文输入上保持拒答（表 1 中为 0.0%）。在低秩更新下，拒答行为的保持是否同样成立、低秩更新是否有足够容量学会一套新编码，论文未说明。
- 分析：论文的能力门槛假设建立在全参数微调 GPT-4 的观察上（图 6），LoRA 可训练参数量远小于全参数微调，这一门槛是否会改变，论文未说明。
- 分析：论文的推理时过滤假设提供方能看见全部推理流量；如果联邦 LoRA 把全局模型下发到客户端本地推理，服务器看不到输入输出，第 7.1 节的推理时干预就不存在了。

## 10. 对防护库设计的含义

1. 分析：论文里真正起作用的检测材料只有“服务器收到的数据集逐行原文”，对应库需要提供“客户端训练前的本地原始数据视图”。如果要把这套检测搬到联邦 LoRA，库必须额外设计一条从客户端到服务器或到审计插件的样本级上报通道；这是论文特有的需求，因为论文的服务器本来就拥有全部数据。
2. 分析：论文反复用“微调产物在固定安全基准上的行为”作为评测量，并且要同时保存基线模型与适配后模型的数字（表 1 并列了 GPT-4 与微调模型的 BAD BOT）。库应把“聚合后全局模型在干净安全基准上的评测”做成服务器侧的固定钩子，并支持保存基线结果与逐轮结果作为参考数据，这是一个通用需求。
3. 分析：论文提出的模型自评估要求插件能调用当前模型做前向生成并充当评审，库因此需要在服务器侧暴露“可调用的全局模型副本”和“模型即评审”的钩子。由于论文第 7.2 节明确指出该防御依赖已被污染的组件，插件接口应当允许把这类结论标记为低信任度，而不是与数据层证据同等对待。
4. 分析：论文提到但未落地的隐藏状态探针，意味着库若要留出这一扩展点，需要在客户端或服务器侧暴露逐层激活的采集钩子。这属于通用能力，但论文没有提供任何可行性证据，接口上应标为实验性，不能作为默认防线。
5. 分析：论文讨论的干预全部落在数据侧（拒绝或过滤数据行）、评测侧（拒绝该次微调）和推理侧（过滤输入输出），对应库的服务器钩子至少有“拒绝整次上传或整轮训练”和“标记并阻断部署”两类动作。剔除客户端、重新加权、裁剪、加噪这些联邦特有动作，论文未涉及，库需要自行设计而无法从本文获得依据。
6. 分析：逐样本内容审查、聚合后安全评测、输入输出过滤这三类需求是通用的；而“识别数据集级的两阶段结构（先教一种编码、再在编码空间里注入有害内容）”和“识别攻击者自定义的私有编码”是这篇论文特有的，并且论文自己承认后者在现有模型能力下基本无解（第 7.2 节中 GPT-4 连 25 个上下文样本都无法解码 Walnut53 或 EndSpeak）。

## 11. 原文依据

1. 第 1 节 Abstract：“Our method constructs a malicious dataset where every individual datapoint appears innocuous, but finetuning on the dataset teaches the model to respond to encoded harmful requests with encoded harmful responses.”——支撑第 3 节与第 4 节关于攻击入口在数据集构造、以及攻击核心是让逐行数据无害而整体有害的论断。
2. 第 2 节 Finetuning Threat Model：“we consider a threat model where an attacker has access to a model provider's finetuning API (e.g. the OpenAI finetuning API).”——支撑第 2 节关于攻击者身份与能力的论断。
3. 第 2 节 Finetuning Threat Model：“The attacker interacts with the API by uploading a dataset of prompt-response pairs for an LLM to finetune on. After finetuning, the attacker has query access to the finetuned model and may query it on arbitrary prompts.”——支撑第 2 节关于攻击者能力边界与第 3 节关于攻击只通过数据集进入的论断。
4. 第 2 节 Finetuning Threat Model：“In our threat model, the model provider can observe the attacker's API usage, distinguishing our setting from that of open-source model weights. This lets the model provider inspect and modify uploaded datasets prior to finetuning.”——支撑第 2 节关于防御者可见范围与第 5 节关于数据集行级采集点的论断。
5. 第 3.2 节 Covert Finetuning：“this finetuning step is covert because, to an outside observer who does not know the cipher, the training samples appear to be sequences of random letters.”——支撑第 3 节与第 5 节关于攻击在数据集文本上不留可判读痕迹的论断。
6. 第 3.2 节 Covert Finetuning：“To keep our attack covert, we augment our harmful finetuning data with safety data consisting of plaintext refusals to harmful prompts. We encode the prompts so that they are not flagged by the finetuning system”——支撑第 4 节与第 6 节关于用混入拒答数据来绕过数据审查与静态安全评估的论断。
7. 第 7.1 节 Defenses Bypassed：“OpenAI's API (OpenAI, 2024) implements this defense as an initial guardrail: a moderation model is run on the rows of the finetuning dataset, and if any row is flagged, the dataset is rejected.”——支撑第 5 节关于数据审查是逐样本粒度、第 6 节关于该干预位置与动作的论断。
8. 第 5.1 节 Model Safety：“our finetuned model does not appear unsafe on plaintext inputs, refusing every harmful request given in plaintext (0% harmful output rate)”——支撑第 5 节与第 7 节关于静态安全评测看不到退化的论断。
9. 第 7.2 节 Looking Ahead：“we prompt GPT-4 after covert malicious finetuning to evaluate whether its own (encoded) outputs on the AdvBench Harmful Behavior dataset are harmful. We find that the finetuned GPT-4 model flags 99.2% of the encoded outputs as harmful”——支撑第 5 节关于自评估这一采集点、第 6 节关于候选干预、第 10 节关于“模型即评审”接口的论断。
10. 第 7.2 节 Looking Ahead：“Unfortunately, GPT-4 cannot decode either Walnut53 or EndSpeak, even with 25 in-context samples.”——支撑第 9 节关于“防御方无法解码攻击者私有编码”这一假设与第 10 节关于编码识别属于论文特有且当前无解的需求的论断。

```json
{
  "key": "halawi2024covert",
  "title": "Covert Malicious Finetuning: Challenges in Safeguarding LLM Adaptation",
  "year": 2024,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "上传微调数据集的逐行原始文本（system prompt、用户提示、助手回答）", "where": "server_receive", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "微调后模型在安全基准（AdvBench 520 条有害指令）上的回答与 BAD BOT 判定率", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "推理时的输入提示与模型输出文本", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "微调后模型对自己输出的有害性判断（模型自评估）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "数据集整体统计特征（是否非英语、是否共享异常 system prompt、格式是否可疑）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "模型隐藏层激活（论文仅提出设想，未做实验，需开放权重）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "把整个数据集交给语言模型在上下文中尝试解码编码", "where": "evaluation", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "report_only"],
  "intervention_where": ["server"],
  "assumptions": [
    "攻击者能访问模型提供方的微调 API 并上传数据集",
    "攻击者权限受限，只需上传数据集和设置训练轮数",
    "提供方能观察 API 使用并在微调前检查与修改上传数据集",
    "基础模型足够强，能从少量样本学会一套此前未知的编码",
    "防御方的分类器与安全评测不会解码攻击者私有的编码",
    "阶段 I 微调不会破坏模型的主要预训练能力"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 3 节与第 4 节：攻击入口是数据集构造，攻击核心是逐行无害而整体有害", "text": "Our method constructs a malicious dataset where every individual datapoint appears innocuous, but finetuning on the dataset teaches the model to respond to encoded harmful requests with encoded harmful responses."},
    {"section": "2. Finetuning Threat Model", "supports": "第 2 节：攻击者是模型提供方微调 API 的使用者", "text": "we consider a threat model where an attacker has access to a model provider's finetuning API (e.g. the OpenAI finetuning API)."},
    {"section": "2. Finetuning Threat Model", "supports": "第 2 节与第 3 节：攻击者的能力边界是上传数据集并在微调后查询模型", "text": "The attacker interacts with the API by uploading a dataset of prompt-response pairs for an LLM to finetune on. After finetuning, the attacker has query access to the finetuned model and may query it on arbitrary prompts."},
    {"section": "2. Finetuning Threat Model", "supports": "第 2 节与第 5 节：防御者能看到 API 使用并检查上传数据集", "text": "In our threat model, the model provider can observe the attacker's API usage, distinguishing our setting from that of open-source model weights. This lets the model provider inspect and modify uploaded datasets prior to finetuning."},
    {"section": "3.2 Covert Finetuning", "supports": "第 3 节与第 5 节：编码后的训练样本在文本层面不留下可判读痕迹", "text": "this finetuning step is covert because, to an outside observer who does not know the cipher, the training samples appear to be sequences of random letters."},
    {"section": "3.2 Covert Finetuning", "supports": "第 4 节与第 6 节：混入明文拒答数据以绕过数据审查与静态安全评估", "text": "To keep our attack covert, we augment our harmful finetuning data with safety data consisting of plaintext refusals to harmful prompts. We encode the prompts so that they are not flagged by the finetuning system"},
    {"section": "7.1 Defenses Bypassed", "supports": "第 5 节与第 6 节：数据审查的采集位置、动作与逐样本粒度", "text": "OpenAI's API (OpenAI, 2024) implements this defense as an initial guardrail: a moderation model is run on the rows of the finetuning dataset, and if any row is flagged, the dataset is rejected."},
    {"section": "5.1 Model Safety", "supports": "第 5 节与第 7 节：攻击在明文安全评测上不显示退化", "text": "our finetuned model does not appear unsafe on plaintext inputs, refusing every harmful request given in plaintext (0% harmful output rate)"},
    {"section": "7.2 Looking Ahead", "supports": "第 5 节、第 6 节与第 10 节：模型自评估作为唯一能看见编码内容的可观测量", "text": "we prompt GPT-4 after covert malicious finetuning to evaluate whether its own (encoded) outputs on the AdvBench Harmful Behavior dataset are harmful. We find that the finetuned GPT-4 model flags 99.2% of the encoded outputs as harmful"},
    {"section": "7.2 Looking Ahead", "supports": "第 9 节与第 10 节：防御方无法解码攻击者私有编码，编码识别是本文特有的未解需求", "text": "Unfortunately, GPT-4 cannot decode either Walnut53 or EndSpeak, even with 25 in-context samples."}
  ]
}
```
