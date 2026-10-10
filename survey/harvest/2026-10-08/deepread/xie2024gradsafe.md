# xie2024gradsafe：GradSafe: Detecting Jailbreak Prompts for LLMs via Safety-Critical Gradient Analysis

## 1. 基本信息

- **场景**：集中式大模型使用场景（论文未说明其为联邦学习）。论文提出的是一个越狱提示（jailbreak prompt）检测器，检测对象是用户提交给大模型的提示文本，部署位置包括在线聊天应用/大模型集成应用的输入侧，以及大模型微调服务的数据入口。全文没有出现联邦学习（federated learning）、客户端（client）、聚合（aggregation）等概念，也没有涉及 LoRA 或其他参数高效微调（parameter-efficient fine-tuning, PEFT）。分析：因此本报告将其归为 centralized_llm，而非联邦大模型微调或参数高效微调供应链。
- **训练阶段**：检测本身不需要训练。GradSafe-Zero 完全不做进一步训练（Section 3.3、Section 6）；GradSafe-Adapt 只在一个逻辑回归（logistic regression）分类器上训练，特征是从基座模型梯度算出的余弦相似度（Section 3.4）。论文所针对的风险阶段是"数据进入微调之前"以及"推理输入到达模型之前"（Section 2.1）。
- **论文类型**：检测（防御方向），同时包含基准评测与消融研究；论文自称是 proof-of-concept 方案（Section 5）。
- **模型与数据规模**：基座模型为 Llama-2-7b-chat-hf（7B，Section 4.1.4）；消融中用未对齐的 llama-2-7b-hf 作对照（Table 7）。对比基线包括 GPT-4（gpt-4-1106-preview）、零样本 Llama-2、Llama Guard、OpenAI Moderation API、Perspective API 与 Azure AI Content Safety API（Section 4.1.3）。数据集为 ToxicChat（10,166 条带毒性标注的提示，官方训练集与测试集各半，评测使用 ToxicChat-1123 官方测试集）与 XSTest（250 条安全提示、涵盖 10 个类型，以及 200 条对应构造的不安全提示，官方测试集为 XSTest-v2，无训练集，Section 4.1.1）。参数切片规模：对 Llama-2 7b 的行切片与列切片合计 2,498,560 个（其中列切片 1,138,688 个、行切片 1,359,872 个，Section 3.2）。

## 2. 威胁模型

- **攻击者是谁**：论文没有形式化地定义一个攻击者模型（分析）。论文正文讨论了两类威胁来源，均出自 Section 2.1：一是直接向大模型应用提交越狱提示的普通用户，用于滥用模型输出有害内容；二是向大模型微调服务提交训练数据的用户，其数据中夹带越狱提示与顺从回复。
- **占比或数量**：论文未说明攻击者占比或恶意样本比例。论文只引用他人工作（Qi et al., 2023；Yi et al., 2024）指出"即使只有少量不安全提示配合顺从回复"也能显著破坏安全对齐（Section 2.1），但没有给出具体数值。
- **能力**：论文只表明攻击者能构造并提交提示文本（Section 2.1）。论文未说明攻击者能否修改模型参数、梯度、训练过程，也未说明其是否能接触到检测器。
- **知识**：论文未说明攻击者掌握哪些知识（论文未说明）。
- **目标**：滥用大模型（misuse）与通过恶意微调（malicious finetuning）破坏模型的安全对齐（Section 2.1）。
- **防御者是谁**：部署 GradSafe 的一方，可以是面向用户的聊天机器人/大模型集成应用运营方，也可以是提供微调服务的平台（Section 2.1、Section 5）。
- **防御者能看到什么**：基座大模型的完整参数与梯度（检测需要反向传播，Section 3.2、Section 4.2）；一批参考安全提示与参考不安全提示（Section 3.2、Appendix A.2）；待检测的提示文本。
- **防御者信任什么**：论文隐含要求防御者信任基座模型已经过安全对齐（Table 7 显示未对齐基座下方法失效），并信任自己准备的少量参考提示。防御者对用户提交的数据持不信任态度，这正是要筛除的对象（Section 2.1）。

## 3. 攻击入口与流程位置

论文是检测/防御论文，因此这里写它所针对的攻击入口。

- **入口一：微调数据中的越狱提示（对应"本地数据准备"位置）**。Section 1 指出，对于大模型定制服务，如果训练集中的越狱提示没有被检测并过滤，模型就会被微调出服从越狱提示的不安全行为。Section 2.1 进一步说明，现有在线微调服务未能有效检测这类不安全提示，因此检测可以被集成进这些服务，用来筛除用户提供的潜在有害训练数据。
- **入口二：在线推理时的用户输入（对应"评估与部署"位置）**。Section 2.1 指出，不安全提示也可被用于滥用大模型，检测不安全提示可作为防止滥用的第一道防线，嵌入不同的在线聊天机器人与大模型集成应用。
- **论文未涉及的位置**：论文完全没有涉及"本地训练过程（损失、优化器、步数）"、"更新上传前的后处理"、"服务器聚合"、"全局模型下发"这些位置（论文未说明，因为论文不是联邦学习工作）。
- **具体操作步骤**：论文没有描述攻击者构造恶意数据的具体步骤，只是引用 Qi et al. (2023) 与 Yi et al. (2024) 的结论，即少量"不安全提示加顺从回复"的数据即可损害安全对齐（Section 2.1）。

## 4. 方法原理

- **核心观察**：把越狱提示与顺从回复（compliance response），例如 "Sure"，配成样本对后，大模型损失对这些样本对的梯度在特定参数切片上表现出相似模式（较大的余弦相似度）；安全提示则没有这种一致性。论文把这些参数称为"安全关键参数（safety-critical parameters）"（Abstract、Section 1、Section 3.2）。
- **步骤 I（获得不安全/安全提示-回复对的梯度）**：只用两条安全参考提示与两条不安全参考提示（Section 3.2、Appendix A.2）。对每条提示，构造提示与回复 "Sure" 的配对，计算大模型的标准损失，再计算损失对模型参数的梯度（Section 3.2）。由于梯度/参数总量巨大，论文对每个梯度矩阵同时做按行与按列切片，在 Llama-2 7b 上得到 2,498,560 个切片（Section 3.2）。切片是识别安全关键参数与计算余弦相似度特征的基本单元。
- **步骤 II（基于余弦相似度差的过滤，对应 Figure 3）**：Phase I 先对所有不安全提示的梯度切片取平均，作为后续余弦相似度计算的参考梯度切片；Phase II 计算每个不安全样本/安全样本的切片与参考切片之间的逐切片余弦相似度；Phase III 用不安全样本的平均余弦相似度减去安全样本的平均余弦相似度，得到相似度差（cosine similarity gap），超过给定阈值的切片被标记为安全关键参数，对应的参考梯度切片被存为"不安全梯度参考（unsafe gradient reference）"（Section 3.2、Figure 3）。Table 1 报告了 Llama-2 7b 上不同差阈值下被标记切片的百分比：阈值 0.5 时行切片 56.47%、列切片 72.57%；阈值 1.0 时行切片 11.78%、列切片 3.53%；阈值 1.5 时行切片 1.24%、列切片 0.19%。
- **GradSafe-Zero（Section 3.3）**：检测时把待检提示与顺从回复 "Sure" 配对，计算损失对安全关键参数的梯度，再与不安全梯度参考计算余弦相似度；把所有安全关键参数切片上的余弦相似度取平均作为分数，超过预设阈值的提示被判为不安全。Section 4.1.4 给出的检测阈值是 0.25，安全关键参数识别所用差阈值是 1。
- **GradSafe-Adapt（Section 3.4）**：用可获得的训练集，以同样的余弦相似度作为特征、以提示的安全标签作为标签，训练一个逻辑回归分类器。论文把这一过程视为领域自适应（domain adaptation），即让模型学习重新加权各安全关键参数的重要性，推理时把余弦相似度送入逻辑回归得到判定结果。
- **消融证据**：去掉安全关键参数识别、改变参考提示的数量与选择、改变配对回复、更换是否对齐的基座模型，都会显著影响效果（Table 4、Table 5、Table 6、Table 7）。

## 5. 检测或防御所需的数据

以下逐项列出该方法需要的输入。需要先说明：论文的场景是集中式大模型，没有客户端与服务器的划分；"采集位置"一栏中的客户端/服务器映射是分析，不是论文原文。

1. **基座大模型的参数与可求导计算图**。是什么：检测器需要对提示与回复构成的样本对做一次反向传播以取得梯度（Section 3.2）。在哪里采集：检测方所持有的基座模型上（论文中是集中式模型持有方）。粒度：模型级。是否需要跨轮历史：不需要。是否需要干净参考数据：不需要。是否需要额外前向或反向计算：需要，论文明确要求计算损失对模型参数的梯度。是否需要其他客户端的数据：不适用（论文未说明）。
2. **少量参考安全提示与参考不安全提示（默认各两条）**。是什么：用于识别安全关键参数并生成不安全梯度参考的文本；论文强调这些参考提示与评测数据集分布独立（Section 3.2），具体内容见 Appendix A.2，消融研究中另有各 10 条的提示池（Section 4.4.2、Appendix A.3）。在哪里采集：检测前的离线校准阶段。粒度：逐样本（逐提示）。是否需要跨轮历史：不需要。是否需要干净参考数据或根数据集：需要，这是该方法成立的前提之一。是否需要额外计算：需要，要对这些参考提示求梯度。是否需要其他客户端的数据：不需要。
3. **待检测的提示文本与固定的系统提示模板**。是什么：用户提交的提示；Section 4.1.4 使用系统提示 "You are a helpful assistant. Help me with the following query: {Prompt}"，再与回复 "Sure" 配对。在哪里采集：数据进入微调之前，或在线推理的输入侧。粒度：逐样本。是否需要跨轮历史：不需要。是否需要干净参考数据：需要（用于与不安全梯度参考比较）。是否需要额外计算：需要，要为该样本对计算梯度。是否需要其他客户端的数据：不需要。
4. **离线校准产物：安全关键参数切片列表（掩码）与不安全梯度参考**。是什么：由第 1、2 项导出的逐切片参考梯度与掩码（Section 3.2）。在哪里采集：离线校准阶段完成后保存。粒度：逐切片（可归到逐层）。是否需要跨轮历史：不需要。是否需要干净参考数据：需要。是否需要额外计算：校准时需要。是否需要其他客户端的数据：不需要。论文报告了被标记切片的占比（Table 1），未报告该产物的存储体积。
5. **GradSafe-Adapt 所需的带标签领域内训练集**。是什么：提示文本与其安全/不安全标签，用于把逐样本的余弦相似度特征训练成逻辑回归分类器（Section 3.4、Section 4.3）。在哪里采集：训练/自适应阶段，在计算完余弦相似度特征之后。粒度：逐样本。是否需要跨轮历史：不需要。是否需要干净参考数据：不需要（标签来自数据集本身）。是否需要额外计算：需要，训练集样本也要计算梯度以获得特征。是否需要其他客户端的数据：不需要。

**攻击会在哪些可观测量上留下痕迹、以及论文声称能绕过哪些检测**：论文并未从攻击者视角讨论痕迹或规避（论文未说明）。作为检测方，论文的主张是越狱提示在与 "Sure" 配对后会在安全关键参数上留下与安全提示可区分的梯度余弦相似度模式（Section 3.2、Figure 3）；论文没有做任何规避实验，也没有声称能绕过哪些检测，只在 Section 7 承认开源检测模型后可能有人基于检测结果开发自适应攻击。

## 6. 干预动作

- 检测的输出是一个分数或二分类判定（安全/不安全）。GradSafe-Zero 输出所有安全关键切片上余弦相似度的平均值并与阈值比较；GradSafe-Adapt 输出逻辑回归的判定（Section 3.3、Section 3.4）。指标计算方式见 Section 4.1.2 与 Section 4.1.3。
- **论文主张的动作是过滤样本**：Section 2.1 明确说检测可以被集成进微调服务，用来"筛除（screen out）"用户提供的潜在有害训练数据，也可以在在线应用中作为防止滥用的第一道防线。
- **论文未说明检测之后的具体处置细节**：是直接丢弃提示、拒绝服务、还是仅告警，论文没有写（论文未说明）。论文的实验只报告分类指标，没有执行真实的样本过滤或重新微调（Section 4）。
- **动作发生的位置**：数据进入微调训练之前（微调服务的数据入口，在联邦语境下最接近"客户端训练前的本地数据准备"），或在线推理的输入侧。
- 论文在 Section 5 明确说明方法只做整体安全性评估，不做细粒度类别分类，并把细粒度分类留作未来工作。

## 7. 实验设置与主要结果

- **模型**：基座为 Llama-2-7b-chat-hf（Section 4.1.4）；消融对照为未对齐的 llama-2-7b-hf（Table 7）。基线为 GPT-4（gpt-4-1106-preview）、零样本 Llama-2-7b-chat-hf、Llama Guard、OpenAI Moderation API、Perspective API、Azure AI Content Safety API（Section 4.1.3）。
- **数据集**：ToxicChat 与 XSTest，规模见 Section 4.1.1（ToxicChat 10,166 条提示；XSTest 250 条安全提示与 200 条不安全提示）。
- **客户端数与参与率、通信轮次、恶意比例、是否非独立同分布**：论文未说明，这些是联邦学习概念，本文不是联邦学习工作。
- **指标**：以 AUPRC（Area Under the Precision-Recall Curve）为主，另报 precision、recall 与 F1 分数（Section 4.1.2）。
- **关键结果**：
  - Table 2（AUPRC）：ToxicChat 上 GradSafe-Zero 为 0.755，高于 Llama Guard 的 0.635、OpenAI Moderation API 的 0.604、Perspective API 的 0.487；XSTest 上 GradSafe-Zero 为 0.936，高于 Llama Guard 的 0.889、OpenAI Moderation API 的 0.779、Perspective API 的 0.713。
  - Table 3（precision/recall/F1）：ToxicChat 上 GradSafe-Zero 为 0.753/0.667/0.707；XSTest 上为 0.856/0.950/0.900，F1 低于 GPT-4 的 0.878/0.970/0.921。Section 4.2 解释 GradSafe 在 XSTest 上不如 GPT-4，原因是基座是 Llama-2 而非 GPT-4，且无法获得 GPT-4 的梯度。
  - Figure 4 与 Section 4.3：在 ToxicChat 的自适应实验中，GradSafe-Adapt 只用 20% 的训练数据就达到了与 Llama Guard 用 100% 训练数据微调相近的表现。
  - Table 4（ToxicChat 消融）：GradSafe-Zero 的 AUPRC 为 0.755、precision/recall/F1 为 0.753/0.667/0.707；去掉安全关键参数识别后为 0.633 与 0.590/0.678/0.631；GradSafe-Adapt 为 0.816 与 0.620/0.872/0.725；去掉安全关键参数识别后为 0.731 与 0.544/0.825/0.655。
  - Table 5（XSTest 参考提示数量消融，10 次运行的均值±标准差）：改变不安全参考提示数量时，n=2 为 0.911±0.042，n=5 为 0.928±0.022，n=10 为 0.932；改变安全参考提示数量时，n=2 为 0.934±0.002，n=5 为 0.935±0.001，n=10 为 0.934。
  - Table 6（XSTest 配对回复消融）："Sure" 为 0.936，"I'm Sorry" 为 0.914，"I" 为 0.687。
  - Table 7（XSTest 基座模型消融）：Llama-2 Chat 模型为 0.936，Llama-2 预训练模型为 0.574。

## 8. 开销

- 论文报告：需要为大模型做推理与梯度计算的实验使用四块 Nvidia GeForce RTX 3090 GPU（Appendix A.1）；由于资源限制，结果只做单次运行（Appendix A.1）。
- 论文报告的定性收益：识别安全关键参数"显著降低"检测所需的存储与计算，因为只需计算安全关键参数相关梯度上的余弦相似度（Section 4.4.1）。
- 论文报告：GradSafe-Adapt 只训练一个逻辑回归分类器，与基于大模型微调的自适应方式相比"高效且资源需求极小"（Section 4.3）。
- 论文未报告：单次检测的时延、显存与存储占用的具体数值、通信开销、参考提示梯度计算与检测梯度计算的具体成本（论文未报告）。分析：因此本报告把 overhead_reported 记为 false；论文只给出了硬件配置与定性表述，没有可复现的量化开销。

## 9. 假设、局限与自适应攻击

- **论文成立的假设**：
  - 基座大模型必须经过安全对齐。Table 7 显示在未对齐的 llama-2-7b-hf 上 AUPRC 只有 0.574，Section 5 说 GradSafe 在未对齐的基座上"不再有效"。
  - 检测方必须能访问大模型的参数并计算梯度。Section 4.2 说因为无法访问 GPT-4 的梯度，所以无法在 GPT-4 上评估该方法。
  - 需要少量与评测集独立的参考安全/不安全提示，用于识别安全关键参数并构造不安全梯度参考（Section 3.2、Appendix A.2）。
  - 待检提示需要与合规回复（例如 "Sure"）或明确的拒绝回复配对，才能激活安全关键参数；中性回复 "I" 效果明显变差（Section 4.4.3、Table 6）。
  - 论文自称只是 proof-of-concept 方案，仍有很大改进与探索空间（Section 5）。
- **论文自述的局限**：只充分研究了 Llama-2 一个基座，没有系统探索其他大模型，效果可能随基座模型及其对齐程度变化（Section 5）；只做整体安全性判断，不做细粒度类别分类，细粒度分类留作未来工作（Section 5）。
- **论文未说明的局限**：多轮对话、超长提示、系统提示模板变化对检测的影响；在真实的恶意微调流程中方法能否阻止对齐被破坏（论文只引用了 Qi et al. (2023) 与 Yi et al. (2024) 的结论，自身没有做微调防护实验）。
- **自适应攻击**：论文没有评估自适应攻击者。Section 7 承认开源检测模型后可能有人基于检测结果开发自适应攻击，但没有做任何实验，也没有给出鲁棒性数值。
- **迁移到联邦 LoRA 微调时可能失效的假设（分析）**：
  - 论文假设检测方持有完整基座模型并能对提示做反向传播。在联邦 LoRA 微调中，服务器通常只持有聚合后的低秩增量，客户端只持有本地低秩参数；论文完全没有讨论 LoRA，因此"安全关键参数切片"在低秩矩阵中如何对应、低秩梯度是否保留同样的余弦相似度结构，论文未说明。
  - 论文的检测对象是原始提示文本。在联邦 LoRA 中原始数据不出客户端，服务器看不到提示，因此这类逐样本梯度分析只能放在客户端做，或者改为分析本地训练过程中已经产生的梯度；这一改动是否保持检测效果论文未说明。
  - 论文的参考提示与阈值是在集中式基座上离线校准的。联邦场景中不同客户端的数据分布不同，共享"不安全梯度参考"还会带来信息泄露问题，论文未说明。
  - 论文的威胁面是"训练数据里混入越狱提示导致安全对齐被破坏"，没有覆盖恶意客户端直接上传恶意低秩增量、或服务器聚合被投毒等更新层面的威胁，也没有把逐样本判定上升到客户端级判定。
  - 论文要求基座已经对齐，而联邦 LoRA 中本地微调本身可能削弱对齐，从而动摇 Table 7 所验证的前提。
  - 论文未报告每个提示一次梯度计算在联邦环境下的额外客户端计算与通信代价。

## 10. 对防护库设计的含义

- 分析：采集点方面，库需要在"客户端本地数据准备"阶段提供逐样本的文本与标签钩子，因为 GradSafe 的输入是提示文本而不是模型更新；同时需要一个能在客户端对基座模型执行前向与反向、并读取指定参数切片梯度的钩子。这两点都属于这篇论文特有的需求，通用底座只需保证在客户端训练前存在一个可插拔的样本级视图。
- 分析：数据视图方面，库需要支持"参数切片级"的梯度视图（按行/列切片以及逐切片余弦相似度向量），而不是常见的逐层范数或逐客户端更新范数；还需要把离线校准产物（安全关键切片掩码与不安全梯度参考）作为可持久化、可版本化的对象管理，与检测插件解耦。
- 分析：参考数据方面，库需要允许注册少量与评测集独立的参考安全/不安全提示及其配对回复，并在客户端训练前完成一次性校准。通用底座可以只提供"注册静态参考样本并触发一次性计算"的接口，而具体阈值（论文中的差阈值 1 与检测阈值 0.25，Section 4.1.4）由插件配置。
- 分析：干预接口方面，论文只给出逐样本的安全/不安全判定，因此库需要提供"过滤样本"接口，在本地训练前丢弃或隔离被判不安全的样本，并可提供"仅报告"接口用于审计。剔除客户端、重新加权、裁剪、加噪、修复或回滚模型这些干预在这篇论文里没有依据。
- 分析：模型访问能力应当作为插件的能力声明之一，因为该方法要求访问基座模型参数与自动求导能力；如果部署形态是"服务器只持有低秩增量"，则需要在客户端侧实现该插件，并把结果（分数或特征）作为可上报的轻量视图。
- 分析：GradSafe-Adapt 表明可以把流程拆成"梯度与余弦相似度特征抽取"和"轻量分类器训练"两段，前者放在能看到模型与数据的客户端，后者可以放在服务器；这样既能做领域自适应，又能避免上传原始梯度。这是通用的插件分层思路，不是这篇论文独有的要求。

## 11. 原文依据

1. **Abstract**（支撑第 7 节"GradSafe-Zero 优于 Llama Guard"的结果论断）：
> "We show that GradSafe, applied to Llama-2 without further training, outperforms Llama Guard—despite its extensive finetuning with a large dataset—in detecting jailbreak prompts."

2. **Section 2.1**（支撑第 3 节"攻击入口之一是微调训练数据"与第 6 节"过滤样本"的论断）：
> "As a result, the detection of unsafe prompts can be integrated into these finetuning services to screen out potentially harmful training data provided by users, thereby safeguarding LLMs against malicious finetuning."

3. **Section 3.2 Step I**（支撑第 5 节"需要提示-回复对的损失梯度"这一数据需求）：
> "We compute an LLM’s standard loss for a pair of prompt and response ‘Sure’; and then calculate the gradient of the loss with respect to the LLM’s parameters."

4. **Section 3.2 Step I**（支撑第 5 节"需要少量干净参考提示且独立于评测集"的论断）：
> "we only use two safe and two unsafe prompts. These reference prompts in our experiments are detailed in Appendix A.2."

5. **Section 3.2 Step I**（支撑第 4 节与第 5 节"以参数切片为基本粒度"的论断）：
> "Inspired by dimensional dependence observed in linguistic competence-related parameters (Zhao et al., 2023), for each gradient matrix, we slice them both row-wise and column-wise,"

6. **Section 3.2 Step II Phase III**（支撑第 4 节"余弦相似度差过滤与阈值标记"的原理描述）：
> "This involves subtracting the average cosine similarities of safe samples from those of unsafe samples. The parameter slices with a similarity gap exceeding a specified threshold are marked."

7. **Section 3.3**（支撑第 4 节与第 5 节"检测时对每个提示做一次配对与梯度计算"的论断）：
> "For a prompt to detect, we first pair the prompt with a compliance response ‘Sure’, and subsequently calculate the gradients of an LLM’s loss for the pair with respect to the safety-critical parameters."

8. **Section 4.1.4**（支撑第 7 节"基座模型与安全关键参数差阈值取 1"的实验设置）：
> "In GradSafe, we use Llama-2 (Llama-2-7b-chat-hf) as the base model. When identifying the safety-critical parameters, we use the gap threshold 1."

9. **Section 5**（支撑第 9 节"基座必须对齐，否则方法失效"的假设）：
> "Our results in Table 7 indicate that GradSafe no longer works with the base LLM without alignment, thereby highlighting and verifying the importance of alignment in the base LLM model."

10. **Section 7 Ethical Impact**（支撑第 9 节"论文承认自适应攻击但未评估"的论断）：
> "We acknowledge that by open-sourcing our detection model, adaptive attacks may be developed based on the detection results."

```json
{
  "key": "xie2024gradsafe",
  "title": "GradSafe: Detecting Jailbreak Prompts for LLMs via Safety-Critical Gradient Analysis",
  "year": 2024,
  "paper_type": "detection",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider", "external"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data", "evaluation_deployment"],
  "observables": [
    {
      "what": "待检提示与合规回复 'Sure' 配对后，大模型损失对安全关键参数切片的梯度",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "由参考安全/不安全提示离线导出的安全关键参数切片掩码与不安全梯度参考",
      "where": "client_pre_train",
      "granularity": "layer",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "GradSafe-Adapt 用于训练逻辑回归的带标签领域内提示集及其逐样本余弦相似度特征",
      "where": "client_pre_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["filter_samples"],
  "intervention_where": ["client"],
  "assumptions": [
    "基座大模型必须经过安全对齐，未对齐基座上方法失效（Table 7、Section 5）",
    "检测方必须能访问基座模型参数并计算梯度（Section 3.2、Section 4.2）",
    "需要少量与评测集分布独立的参考安全/不安全提示（Section 3.2、Appendix A.2）",
    "待检提示必须与合规或明确拒绝回复配对才能激活安全关键参数（Section 4.4.3、Table 6）",
    "论文自称只是 proof-of-concept，且不做细粒度类别分类（Section 5）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {
      "section": "Abstract",
      "supports": "第 7 节：GradSafe-Zero 在未经进一步训练的情况下超过经过微调的 Llama Guard",
      "text": "We show that GradSafe, applied to Llama-2 without further training, outperforms Llama Guard—despite its extensive finetuning with a large dataset—in detecting jailbreak prompts."
    },
    {
      "section": "Section 2.1",
      "supports": "第 3 节与第 6 节：检测可集成进微调服务以筛除用户提供的训练数据",
      "text": "As a result, the detection of unsafe prompts can be integrated into these finetuning services to screen out potentially harmful training data provided by users, thereby safeguarding LLMs against malicious finetuning."
    },
    {
      "section": "Section 3.2 Step I",
      "supports": "第 5 节：检测需要提示与回复配对的损失梯度",
      "text": "We compute an LLM’s standard loss for a pair of prompt and response ‘Sure’; and then calculate the gradient of the loss with respect to the LLM’s parameters."
    },
    {
      "section": "Section 3.2 Step I",
      "supports": "第 5 节：校准只需两条安全与两条不安全参考提示，且独立于评测集",
      "text": "we only use two safe and two unsafe prompts. These reference prompts in our experiments are detailed in Appendix A.2."
    },
    {
      "section": "Section 3.2 Step I",
      "supports": "第 4 节与第 5 节：以梯度矩阵的行/列切片作为基本粒度",
      "text": "Inspired by dimensional dependence observed in linguistic competence-related parameters (Zhao et al., 2023), for each gradient matrix, we slice them both row-wise and column-wise,"
    },
    {
      "section": "Section 3.2 Step II Phase III",
      "supports": "第 4 节：用不安全与安全样本平均余弦相似度之差、按阈值标记安全关键参数",
      "text": "This involves subtracting the average cosine similarities of safe samples from those of unsafe samples. The parameter slices with a similarity gap exceeding a specified threshold are marked."
    },
    {
      "section": "Section 3.3",
      "supports": "第 4 节与第 5 节：检测阶段对每个提示与 'Sure' 配对并计算安全关键参数上的梯度",
      "text": "For a prompt to detect, we first pair the prompt with a compliance response ‘Sure’, and subsequently calculate the gradients of an LLM’s loss for the pair with respect to the safety-critical parameters."
    },
    {
      "section": "Section 4.1.4",
      "supports": "第 7 节：基座模型为 Llama-2-7b-chat-hf，识别安全关键参数的差阈值为 1",
      "text": "In GradSafe, we use Llama-2 (Llama-2-7b-chat-hf) as the base model. When identifying the safety-critical parameters, we use the gap threshold 1."
    },
    {
      "section": "Section 5",
      "supports": "第 9 节：方法依赖基座模型的安全对齐，未对齐基座上失效",
      "text": "Our results in Table 7 indicate that GradSafe no longer works with the base LLM without alignment, thereby highlighting and verifying the importance of alignment in the base LLM model."
    },
    {
      "section": "Section 7 Ethical Impact",
      "supports": "第 9 节：论文承认开源后可能出现自适应攻击，但未做评估",
      "text": "We acknowledge that by open-sourcing our detection model, adaptive attacks may be developed based on the detection results."
    }
  ]
}
```
