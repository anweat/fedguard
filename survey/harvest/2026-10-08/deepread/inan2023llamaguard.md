# inan2023llamaguard：Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations

## 1. 基本信息

场景：集中式大模型训练与集中式部署，本文与联邦学习（federated learning）无关。论文提出的是一个面向人机对话（Human-AI conversation）的内容安全护栏模型，运行在被保护大模型的输入侧与输出侧，属于推理与部署阶段的集中式组件。按题目给定选项归类，场景为“集中式大模型训练”（centralized large language model training，含其推理部署），不是联邦大模型微调，也不是参数高效微调供应链（parameter-efficient fine-tuning supply chain）。

训练阶段：论文自身的流程分为三步。第一步是离线数据准备与人工标注（Section 3.3），第二步是在 Llama2-7b 上做指令微调（instruction fine-tuning），训练 500 步、约等于训练集 1 个 epoch（Section 3.4），第三步是推理时对用户消息做 prompt classification、对模型回复做 response classification（Section 3.1）。论文还演示了在 ToxicChat 上的进一步微调适配（Section 4.5.2）。

论文类型：防御（defense），其具体形态是一个内容审核分类器（content moderation classifier），同时公开模型权重，带有基准评测（benchmark）成分。它不研究攻击，也不研究训练期投毒。

模型与数据规模：骨干模型为 Llama2-7b（Section 3.4）。微调数据为 13,997 条 prompt-response 对，按 3:1 随机划分为微调集与评测集（Section 3.3）。Table 1 给出类别分布，按“Prompts / Responses”列出：Violence & Hate 为 1750 / 1909，Sexual Content 为 283 / 347，Criminal Planning 为 3915 / 4292，Guns & Illegal Weapons 为 166 / 222，Regulated or Controlled Substances 为 566 / 581，Suicide & Self-Harm 为 89 / 96，Safe 为 7228 / 6550。训练超参为序列长度 4096、批大小 2、学习率 2 × 10⁻⁶、模型并行度 1（Section 3.4）。外部评测集为 OpenAI Moderation Evaluation Dataset（1680 条 prompt 样例，Section 4.2）和 ToxicChat（10k 条样本，Section 4.2）。

## 2. 威胁模型

论文没有给出形式化的威胁模型（threat model），没有指定攻击者是谁、占比或数量、能力与知识，这些内容论文未说明。可以把论文中明确出现的角色分成三类。

第一类是恶意的外部用户。论文的动机段落说，生成式人工智能产品应当部署护栏，用来防止生成高风险或违反政策的内容，并“protect against adversarial inputs and attempts at jailbreaking the model”（Section 1）。分析：据此推断，论文隐含的对手是提交对抗性输入或尝试越狱的外部使用者，其可控量是送入被保护大模型的用户消息文本；它不属于联邦学习里的恶意客户端、恶意服务器、数据提供方或适配器发布者，因此本节其余项在联邦语境下都只能标为“论文未说明”。

第二类是论文自己的红队（red team）。Section 3.3 说明作者用内部红队对 prompt 与 response 对做标注，Section 6 说明还雇用了外部红队承包商对 Llama Guard 本身做红队测试。这是数据生产与自评手段，不是被防御的对手。

第三类是 Llama Guard 自身可能被利用的路径。Section 6 明确写道，Llama Guard 作为大语言模型可能受到提示注入（prompt injection）攻击，从而改变或绕过其预期用途；同一节还指出，如果把 Llama Guard 当作聊天模型而不是分类器来提示，它可能生成被认为不道德或不安全的内容。论文只陈述了这两种风险，没有给出攻击者的能力假设，也没有量化攻击成功率。

被防御的风险类别由论文自建的 taxonomy 给出（Section 2.1），共六类：Violence & Hate、Sexual Content、Guns & Illegal Weapons、Regulated or Controlled Substances、Suicide & Self Harm、Criminal Planning。论文声明该 taxonomy “is not intended to comprehensively measure how effectively the model mitigates all potential risks”（Section 2），即不声称覆盖所有风险。

防御者是谁：论文面向的是部署生成式人工智能产品的开发者与平台（Section 1 引用 Llama 2 Responsible Use Guide 的建议）。防御者能看到什么：完整的人机对话文本，既包括用户消息，也包括 AI 回复，因为论文建议对“all inputs and outputs to the model itself”都设护栏（Section 1）。防御者信任什么：论文没有直接陈述信任假设，只规定“The model should only take into account the given categories and their descriptions for making a safety assessment”（Section 3.1），也就是把判断范围限定在调用时给出的类别与描述上。分析：这等价于假设部署方提供的政策文本是可信且正确的，而论文没有讨论分类器本身被篡改或政策文本被替换的情形。

## 3. 攻击入口与流程位置

这是一篇纯防御论文，因此这里写它所针对的攻击入口。

论文所针对的风险入口是“评估与部署”阶段，而不是训练流程的任何环节。具体位置有两处。第一处是被保护大模型的输入侧：用户消息在送入模型之前，先交给 Llama Guard 执行 prompt classification（Section 3.1 与 Section 1）。第二处是被保护大模型的输出侧：模型生成的回复在返回用户之前，再交给 Llama Guard 执行 response classification（Section 3.1 与 Section 1）。论文用 “input-output safeguard” 与 “guardrails” 来描述这一部署形态，并说明其目的是同时拦住高风险输入与高风险输出。

论文没有涉及本地数据准备、本地训练过程（损失、优化器、步数）、更新上传前的后处理、服务器聚合、全局模型下发这些环节中的任何攻击入口，因为这些环节在论文的集中式设定中并不存在。

论文唯一详细描述的数据流程，是它自己构造微调数据的离线流程，位于 Section 3.3。步骤是：先从 Anthropic 的 harmlessness 人类偏好数据（Ganguli et al., 2022）中取每个会话的第一条人类 prompt，丢弃对应的助手回复以及其余所有轮次，形成一个单轮 prompt 数据集；再用作者内部的一个 Llama 检查点（checkpoint）为这些 prompt 生成一批“配合”与“拒绝”两类回复；然后由内部红队按 Section 2 的 taxonomy 对 prompt 与 response 对打标签，共四类标签，分别是 prompt-category、response-category、prompt-label（safe 或 unsafe）、response-label（safe 或 unsafe）；标注过程中还做数据清洗，丢弃格式不良的输入或输出；最终得到 13,997 条带标注的 prompt-response 对。分析：这个流程对应防护库里的“训练前离线数据准备”位置，它是论文自身模型的训练数据来源，不是它要防御的攻击入口。

## 4. 方法原理

核心思想是把内容安全审核建模成指令跟随（instruction following）任务，让同一个大语言模型通过改变指令措辞，分别承担用户消息分类与 AI 回复分类两个任务，并用自然语言给出的政策文本决定判什么、不判什么。

Section 3.1 把输入输出护栏任务拆成四个要素。第一个要素是一组准则（guidelines），由编号的违规类别和说明“在该类别下什么算安全、什么算不安全”的纯文本描述组成；模型只应考虑输入中给出的类别及其描述。第二个要素是分类类型，任务需指明是在分类用户消息（论文称之为 “prompts”）还是在分类代理消息（论文称之为 “responses”）；论文声称自己是第一个把这两者拆成两个独立内容审核任务的工作，并且指出这一区分只靠改变指令措辞实现，不需要额外的多任务结构。第三个要素是对话（conversation），可以是单轮，即一条用户消息加一条代理回复，也可以是多轮。第四个要素是输出格式。

输出格式的具体约定是：先输出 “safe” 或 “unsafe”，这两个词在论文使用的 SentencePiece 分词器（Kudo and Richardson, 2018）中都是单 token；如果判定为 unsafe，则换行列出被违反的 taxonomy 类别，类别写成“一个字母加 1-based 类别索引”的形式（例如 ’O’ 加索引）。Section 3.1 说明，凭借这一格式，分类器分数可以直接从第一个 token 的概率读出，模型因此同时支持二分类与多标签分类；如果把单一类别放进输入，还可以做 1-vs-all 分类，只生成一个 token 来读二值判定。Figure 1 给出了 prompt 分类与 response 分类两个任务的指令示例与期望输出。

政策适配有两条路径。第一条是免训练的提示适配（Section 3.2）：零样本提示（zero-shot prompting）是在推理时的提示里放入目标领域的类别名，或者类别名加类别描述；少样本提示（few-shot prompting）在此基础上再放入每类 2 到 4 个例子，学习完全发生在上下文里，不在这些例子上做训练，且例子中混有 unsafe 与 safe，其中 safe 例子是难负例（hard negatives）。第二条是进一步微调（Section 4.5.2），论文用 ToxicChat 训练数据的 10%、20%、50%、100% 继续微调 Llama Guard，并与同样设置下微调 Llama2-7b 作对比。

训练侧还有两项数据增强（Section 3.4）。第一项是：如果某个类别在该样本中没有被违反，就从模型提示里随机丢弃若干个类别。第二项是：把输入提示里所有被违反的类别都丢掉，同时把该样本的标签改成 safe。此外，训练时还会在样本之间打乱类别编号，并在期望输出里做对应修改，以避免模型记住格式。

评测方法上，Section 4.1 的公式 (1) 针对“逐类别输出概率”的内容审核 API 定义了二分类分数：第 i 个样本的预测分数 ŷᵢ 等于该样本在所有正类别 c₁ 到 cₙ 上预测概率的最大值，即 ŷᵢ = max over c ∈ {c₁, …, cₙ} of ŷ_{c,i}，也就是只要任一类别判正就算整体判正，不检查该类别是否与真实目标类别对齐。逐类别指标则用 1-vs-all：对每个目标类别 c_k 单独跑一次任务 t_k，只把 c_k 当正类，其余类别样本（包括真负例与其它正类样本）都当负类，并在提示里只放入 c_k。对固定类别输出头的基线 API，论文改用 1-vs-benign：把属于其它正类的样本直接从该任务中删掉，只留下 benign 样本作负类；论文自己提示这种做法可能移除难负例，因而结果偏乐观。

评测指标为 AUPRC（area under the precision-recall curve，Section 4.3.3），选择理由是它关注正类即 “unsafe” 类上的精确率与召回率权衡。对不提供概率分数的 Azure AI Content Safety API 与 GPT-4，论文改用阈值化指标，把阈值设为 0.5 后报告精确率、召回率与 F1（Section 4.3.3 与 Appendix B）。

## 5. 检测或防御所需的数据

论文没有“检测攻击”这一层，它的方法是直接对内容做安全分类。下面逐项列出该方法需要的每一种输入。需要说明的是，JSON 里的采集位置取值集合是为联邦训练流程设计的，对本文这种集中式推理组件只能做近似映射，具体偏差在每项中说明。

第一项，待审内容文本，包括用户消息、AI 回复以及它们组成的对话。采集位置是推理与部署时，对应 JSON 的 evaluation；论文要求在模型输入侧与输出侧各跑一次（Section 1）。粒度是逐样本，但这里的“样本”单位是一段对话，可以含单轮也可以含多轮（Section 3.1），输出是整段内容的 safe 或 unsafe 判定以及被违反的类别列表，而不是逐 token 或逐句判定。是否需要跨轮历史：论文没有要求跨训练轮的历史；多轮对话的上下文是同一个输入内部的组成部分，不是跨轮积累的状态。是否需要干净参考数据：推理时不需要。是否需要额外的前向或反向计算：需要，被判内容要额外经过一个 Llama2-7b 量级的模型做一次前向计算。是否需要其它客户端的数据：不适用。

第二项，政策文本，也就是 guidelines 或 taxonomy。它是编号的违规类别加自然语言描述，由部署方在调用时放进 Llama Guard 的提示里（Section 3.1 与 Section 3.2）。采集位置是推理与部署时，对应 evaluation。粒度是政策级或模型级，因为它对整个部署生效，但会随每一次调用重复放入提示；如果只放入单一类别，就变成 1-vs-all 的逐类别判定（Section 3.1 与 Section 4.1）。论文说明零样本时可以只用类别名，也可以类别名加描述（Section 3.2）。不需要跨轮历史，不需要干净参考数据，不需要额外计算。

第三项，少样本示例。每类 2 到 4 个例子，混有 unsafe 与 safe，且 safe 例子是难负例（Section 3.2）。采集位置是推理时，示例直接写进 Llama Guard 的提示，不参与训练。粒度是逐样本，因为每个待审内容的提示里要携带这些示例。分析：这些示例扮演参考与校准的角色，因此对应 JSON 中 needs_clean_reference 取 true，但它们不是统计意义上的干净根数据集，而是人工挑选的上下文示例。

第四项，Llama Guard 自身输出的首 token 概率。Section 3.1 说明 safe 与 unsafe 都是单 token，分类器分数可以从第一个 token 的概率读出。采集位置是推理与部署，对应 evaluation；粒度是逐样本；不需要历史、干净参考或额外的反向计算，但需要推理栈暴露首 token 的概率，这本身依赖第一项里已经计入的那次前向计算。论文说这是读分类分数的途径，也是使用方选阈值做二值化的依据（Section 4.3.3）。

第五项，离线微调数据，即 13,997 条带四类标签的 prompt-response 对（Section 3.3）。采集位置是训练前的离线数据准备阶段，JSON 中近似映射为 client_pre_train。粒度是逐样本。是否需要干净参考数据：需要，因为标签由内部红队人工标注，Section 3.3 明确写出四类标签是 prompt-category、response-category、prompt-label（safe 或 unsafe）、response-label（safe 或 unsafe）。是否需要跨轮历史：论文未说明按会话组织历史，它只取每个会话的第一条人类 prompt 并丢弃其余轮次。是否需要其它客户端的数据：不适用。这一项在论文里属于模型自己的训练数据，不是某个在线检测环节的输入。

第六项，评测用的基准数据与标签，包括作者自建测试集（3:1 划分后的评测部分）、OpenAI Moderation Evaluation Dataset 的 1680 条 prompt 样例，以及 ToxicChat 的 10k 条样本（Section 4.1、Section 4.2）。采集位置是评估，对应 evaluation；粒度是逐样本，用于计算 AUPRC，同时也会按类别汇总（Table 3、Table 5、Table 6）。ToxicChat 的二元毒性标签由严格多数投票决定，要求至少 3 名标注者一致（Section 4.2）。

关于“攻击会留下什么痕迹”这一问：论文不研究攻击，因此没有列出任何攻击的可观测量。论文反而声明了自身可被绕过的面。Section 6 说 Llama Guard 作为大语言模型可能被提示注入攻击改变或绕过其用途，也可能在被当作聊天模型提示时输出不当内容。Section 6 还报告了外部红队承包商的测试结果，说明这次测试没有发现超出预训练 Llama2-7b 的额外风险。论文没有给出任何绕过方法的清单、成功率或防护手段。

## 6. 干预动作

Llama Guard 本身只做判定，不做干预。它的输出是一个二值判定（safe 或 unsafe），在 unsafe 时附加被违反的类别标签，并可读出首 token 概率用于自行设阈值（Section 3.1）。对应到 JSON 的干预动作集合，它属于“仅报告”（report_only）。

检测之后做什么，例如是否阻断该条用户消息、是否丢弃或重新生成该条回复、是否转人工复核，论文未说明。论文只使用了 “safeguard”“guardrails”“mitigate” 这类笼统表述（Section 1），没有定义下游动作，也没有给出任何阈值选择的推荐值。分析：真正的内容拦截或过滤逻辑必须由部署方在 Llama Guard 之外实现，论文交付的是一个可调阈值的分类器。

动作发生的位置是部署时的推理链路，即被保护大模型的输入侧与输出侧，不在训练流程的客户端或服务器上，因此 JSON 的 intervention_where 记为 none，表示它不落在联邦训练的客户端或服务器聚合环节。

## 7. 实验设置与主要结果

模型方面，Llama Guard 由 Llama2-7b 指令微调得到（Section 3.4）；对照基线包括 OpenAI Moderation API、Perspective API、Azure AI Content Safety API 和零样本提示的 GPT-4（Section 4.3）。训练配置为单机 8 张 A100 80GB、批大小 2、序列长度 4096、模型并行度 1、学习率 2 × 10⁻⁶、训练 500 步、约 1 个 epoch（Section 3.4）。

数据方面，微调与评测使用 13,997 条自建标注数据，3:1 随机划分（Section 3.3），类别分布见 Table 1。公开评测集为 OpenAI Moderation Evaluation Dataset（1680 条 prompt 样例）与 ToxicChat（10k 条样本）（Section 4.2）。论文未涉及客户端数量、参与率、训练轮次、恶意客户端比例、数据是否非独立同分布等联邦学习设置，这些项论文未说明。

指标为 AUPRC（Section 4.3.3），对无概率输出的基线改用阈值 0.5 的精确率、召回率与 F1（Appendix B）。

主要结果如下。Table 2 报告总体 AUPRC：在作者自建测试集的 prompt 分类上，Llama Guard 为 0.945，OpenAI API 为 0.764，Perspective API 为 0.728；在 OpenAI Mod 数据集上，Llama Guard 为 0.847，OpenAI API 为 0.856，Perspective API 为 0.787；在 ToxicChat 上，Llama Guard 为 0.626，OpenAI API 为 0.588，Perspective API 为 0.532；在作者自建测试集的 response 分类上，Llama Guard 为 0.953，OpenAI API 为 0.769，Perspective API 为 0.699。论文据此提出两点结论：一是自建测试集上分数很高，说明该方法在 in-policy 设定下的上限很高；二是 Llama Guard 在没有任何训练样例的情况下接近 OpenAI API 在其自有数据集上的成绩，并在 ToxicChat 上超过所有其它方法（Section 4.4）。

Table 3 给出自建测试集的逐类别 AUPRC，每格左数为 prompt 分类、右数为 response 分类。Llama Guard 的成绩为：Violence and Hate 0.857 / 0.835，Sexual Content 0.692 / 0.787，Criminal Planning 0.927 / 0.933，Guns and Illegal Weapons 0.798 / 0.716，Regulated or Controlled Substances 0.944 / 0.922，Self-Harm 0.842 / 0.943。同一张表中 OpenAI Mod API 在 Guns and Illegal Weapons 上为 0.035 / 0.060，在 Regulated or Controlled Substances 上为 0.085 / 0.067；Perspective API 在这两类上分别为 0.054 / 0.048 与 0.110 / 0.096。

Table 4 报告在 OpenAI Mod 数据集上的适配对比：OpenAI Mod API 为 0.856，Llama Guard 不做适配为 0.837，零样本并给出 OpenAI Mod 类别为 0.847，少样本并给出描述与上下文例子为 0.872。论文的结论是，只靠提示适配新政策既有效又比微调便宜，加入 2 到 4 个例子后 Llama Guard 在该数据集上超过 OpenAI Moderation API（Section 4.5.1）。Figure 2 给出该数据集上的逐类别零样本与少样本对比，论文解释逐类别分数低于总体二分类分数，是因为 1-vs-all 会对“判对了 unsafe 但判错类别”的情况扣分，并且 Llama Guard 的 taxonomy 与 OpenAI 的 taxonomy 对齐不佳，例如它不区分 Hate、Hate (Calling for Violence) 与 Violence，也没有专门针对 Sexual Content (Minors)、Harassment、Violence (Graphic) 的条目（Section 4.5.1）。

微调适配方面，Figure 3 报告用 ToxicChat 训练数据的 10%、20%、50%、100% 继续微调的结果。论文结论是：Llama Guard 只需 ToxicChat 的 20% 数据就能与用 100% 数据训练的 Llama2-7b 表现相当，在数据量相同时表现更好；零样本设置下 Llama2-7b 只产生格式不良的输出，因此其 AUPRC 记为 0，而 Llama Guard 为 0.626（Section 4.5.2）。

Appendix B 的 Table 5 与 Table 6 用阈值 0.5 报告精确率、召回率、F1。Table 5 的 Overall 一行为：Llama Guard 0.880 / 0.864 / 0.872，OpenAI Mod API 0.874 / 0.250 / 0.389，Azure API 0.788 / 0.515 / 0.623，Perspective API 0.817 / 0.219 / 0.346，GPT-4 0.717 / 0.947 / 0.816。Table 6 的 Overall 一行为：Llama Guard 0.900 / 0.867 / 0.884，OpenAI Mod API 0.874 / 0.329 / 0.478，Azure API 0.749 / 0.564 / 0.644，Perspective API 0.751 / 0.248 / 0.373，GPT-4 0.813 / 0.788 / 0.801。

## 8. 开销

训练开销：论文报告了训练配置，即单机 8 张 A100 80GB、批大小 2、序列长度 4096、模型并行度 1、学习率 2 × 10⁻⁶、500 步、约 1 个 epoch（Section 3.4）。选择 7B 这一档的理由是它在三个可选规模中最小，对使用者更友好，并能降低潜在的推理与部署成本（Section 3.4）。论文没有报告训练总时长、总计算量、显存占用或能耗。

标注开销：论文报告了数据量，即 13,997 条由内部红队按 taxonomy 标注的 prompt-response 对（Section 3.3），但没有报告标注工时或成本。

推理开销：论文只做了定性说明，即选择 7B 骨干可以降低推理与部署成本（Section 3.4），并称通过提示适配新政策比微调便宜（Section 4.5.1）。论文未报告延迟、吞吐、每秒查询数、显存占用等任何推理开销数值。

通信开销与存储开销：论文未报告。通信开销在集中式设定下本就不适用。

数据效率方面，论文报告了一个可换算成成本收益的结果：在 ToxicChat 上只需 20% 的训练数据即可与用 100% 数据从头微调的 Llama2-7b 相当（Section 4.5.2 与 Figure 3）。综合来看，论文报告了训练配置与部分定性成本判断，因此按“报告了开销”处理，但缺少量化的推理开销。

## 9. 假设、局限与自适应攻击

论文自述的局限集中在 Section 6。第一，Llama Guard 虽然是语言模型，但其常识知识受训练数据尤其是预训练数据限制，可能给出错误判断，尤其在涉及训练数据之外的知识时。第二，所有微调数据以及大部分预训练数据都是英文，因此论文不保证它在其它语言上有足够表现。第三，作者虽然对微调标签质量有信心，但不声称对政策有完美覆盖，可能存在表现不佳的情形。第四，论文的训练目标是一个输出空间很有限的分类任务，但 Llama Guard 作为语言模型可以被任何文本提示并要求补全，因此可能被不怀好意的使用方利用；论文为此请外部红队承包商做了红队测试，并说明测试结果没有指出超出预训练 Llama2-7b 的额外风险。第五，当被当作聊天模型而不是按预期当分类器提示时，Llama Guard 可能生成被认为不道德或不安全的内容，原因是没有针对聊天场景做安全微调。第六，作为语言模型，它可能受到提示注入攻击，从而改变或绕过预期用途。

论文还自述了评测层面的限制。Section 2 声明 taxonomy 不旨在全面衡量模型对所有潜在风险的缓解效果。Section 4.1 指出，off-policy 评测使用的 1-vs-benign 会移除难负例，可能给出偏乐观的结果。Section 4.3.3 指出，Azure API 与 GPT-4 不提供概率分数，因此无法计算平均精度，只能报告阈值化指标。Section 4.5.1 与 Figure 2 指出，当目标 taxonomy 与自身 taxonomy 不对齐时，逐类别指标会明显低于总体二分类指标。

方法成立所依赖的假设，可以归纳为以下几点。安全风险可以被枚举成一套固定的类别并用自然语言描述，且模型只依据输入中给出的类别做判断（Section 3.1）。safe 与 unsafe 恰好都是单个 SentencePiece token，因此首 token 概率可以直接当分类分数（Section 3.1）。存在足够高质量的人工标注数据，可以由红队对 prompt 与 response 分别打类别标签与安全标签（Section 3.3）。护栏模型与被保护模型相互独立，部署方有能力对每一次输入与输出各运行一次独立的 7B 级模型（Section 1 与 Section 3.4）。政策可以在推理时通过提示中的 taxonomy 替换，不必重新训练（Section 3.2 与 Section 4.5.1）。

自适应攻击方面，论文没有做系统的自适应攻击评估。Section 6 只说请了外部红队承包商对 Llama Guard 做红队测试，且没有报告测试方法、样本量或攻击成功率；同一节把提示注入列为潜在风险，但没有给出针对提示注入的实验结果。因此本文按“未评估自适应攻击者”处理，只是在定性层面承认了被绕过的可能。

迁移到联邦 LoRA 微调时可能失效的假设，以下均为分析。

第一，Llama Guard 假设审核方能看到完整的用户消息与模型回复明文。联邦 LoRA 微调的前提是客户端本地数据不出域，服务器通常看不到原始对话，因此这套护栏无法原样放在服务器侧；要迁移就必须把审核器下推到客户端，或者让客户端自愿上报可审内容，而这两种做法论文都没有讨论。

第二，论文假设对每次输入与输出各运行一次 7B 级模型是可接受的，并只用“降低推理与部署成本”做定性论证，没有给出延迟或吞吐数据。放到联邦 LoRA 里，如果每个客户端每一步都要额外跑一遍 7B 级护栏，客户端算力与通信会成为瓶颈，而论文没有提供做预算所需的数值。

第三，论文的判定粒度是整段对话或整条消息，输出是有害性标签，不是逐样本损失、逐层范数或更新统计量。投毒攻击的痕迹往往只体现在少数被投毒的样本或更新方向上，用内容安全分类器审 prompt 与 response 并不能回答“这条数据是否被用于投毒”，论文也没有做过任何训练数据投毒的实验。

第四，论文假设存在一套固定的英文 taxonomy 与集中式人工标注数据。联邦场景下各客户端的数据分布与政策可能不同，论文虽然展示了零样本、少样本与继续微调三种适配方式，但没有研究多客户端政策异构时如何统一判定口径或如何聚合。

第五，论文的适配实验是继续对 Llama2-7b 做全参数指令微调，全文没有出现 LoRA 或任何参数高效微调方法，因此“用 20% ToxicChat 数据即可对标 100% 数据训练的 Llama2-7b”这一数据效率结论，不能直接推广到 LoRA 适配器在联邦聚合下的训练。

第六，论文假设护栏模型本身可信且独立于被保护模型。在联邦 LoRA 中，如果护栏逻辑以适配器形式参与聚合，或者服务器本身是恶意的，护栏就可能被投毒或被绕过；论文完全没有考虑恶意服务器或恶意客户端。

第七，论文的 AUPRC 是在集中式测试集上计算的，没有讨论阈值在分布漂移下的校准问题。分析：在非独立同分布的联邦客户端上直接沿用论文的判定阈值，其精确率与召回率没有保证。

第八，论文未说明它能否作为训练数据过滤信号。它的全部实验都在推理侧，没有把分类结果回灌到训练流程的任何环节。

## 10. 对防护库设计的含义

以下全部为分析。

第一，库需要把“推理与部署”也列为一条正式的信任边界，而不只是训练期边界，并且在这条边界上提供两个固定钩子：一个在被保护大模型接收用户消息之前，一个在它生成回复之后。这篇论文的方法只能挂在这两个钩子上，如果库的钩子清单只覆盖客户端训练前、训练中、训练后与服务器聚合，这篇论文的防御无处安放。这条需求对内容安全类插件是通用的。

第二，插件需要的数据视图至少包含四项：待审文本（prompt、response 或整段对话，逐样本）、部署方提供的政策文本（类别名与描述）、可选的少样本示例（每类 2 到 4 条并含难负例）、以及被保护或护栏模型首 token 的概率。前三项都是文本，采集底座按样本粒度留存即可；第四项要求推理栈暴露 logprob，这一点是这篇论文特有的，通用采集底座通常不会默认保留。

第三，干预接口需要允许插件返回“二值判定加被违反的类别标签加一个可调阈值”，并把下游动作（仅记录、拦截、丢弃、重新生成、转人工）留给编排层。论文只给判定不给动作，所以库必须把“判定”和“处置”解耦，否则无法复用这篇论文的分类器。按类别分别处置的能力是这篇论文特有的，“仅报告”这一动作类型是通用的。

第四，插件配置接口需要支持把政策文本作为运行时可替换的参数，因为论文证明只改提示里的 taxonomy 就能切换政策而不必重训，也证明可以对同一条内容只放一个类别做 1-vs-all 多次判定。把策略与算法解耦、让策略可热更新，对防护库是通用需求，但这篇论文正是该需求最直接的证据。

第五，库需要明确区分“内容安全审核”与“训练期投毒检测”两类插件。这篇论文检测的是内容有害性，全部实验都在推理侧，没有任何关于更新异常、逐层范数或投毒样本定位的结果。分析：在联邦 LoRA 的投毒防护库里，它更适合作为一个可选辅助信号，例如在聚合前对客户端上报的样本或合成数据做安全审核，而不应被当作主检测器。

第六，这篇论文特有的依赖是人工标注与红队流程，即需要产出一批带 prompt-category、response-category、prompt-label、response-label 四类标签的样本，再按 3:1 之类的比例划分。库本身不必实现标注流程，但采集底座应当支持把外部标注结果与样本标识绑定，并支持按类别分层统计，这样这类插件才能被复现和评估。

## 11. 原文依据

1. 章节：Abstract。支撑论断：第 1 节与第 4 节所述的方法核心是把安全风险 taxonomy 用于 prompt 分类。“Our model incorporates a safety risk taxonomy, a valuable tool for categorizing a specific set of safety risks found in LLM prompts (i.e., prompt classification).”

2. 章节：Section 1。支撑论断：第 3 节所述该防御部署在推理与部署阶段的输入侧与输出侧。“resources such as the Llama 2 Responsible Use Guide (Meta, 2023) recommend that products powered by Generative AI deploy guardrails that mitigate all inputs and outputs to the model itself”

3. 章节：Section 1。支撑论断：第 2 节与第 4 节所述论文把用户侧与代理侧拆成两个独立分类任务。“First, none of the available tools distinguishes between assessing safety risks posed by the user and the AI agent, which are arguably two distinct tasks”

4. 章节：Section 3.1。支撑论断：第 4 节所述模型只依据输入中给出的类别与描述作判断。“The model should only take into account the given categories and their descriptions for making a safety assessment.”

5. 章节：Section 3.1。支撑论断：第 5 节所述首 token 概率可直接作为分类分数，以及第 6 节所述判定输出的形式。“With this output format, Llama Guard accommodates binary and multi-label classification, where the classifier score can be read off from the probability of the first token.”

6. 章节：Section 3.3。支撑论断：第 5 节所述微调数据需要逐样本的类别标签与安全标签。“The red-teamers annotate the dataset for 4 labels: prompt-category, response-category, prompt-label (safe or unsafe), and response-label (safe or unsafe).”

7. 章节：Section 3.3。支撑论断：第 1 节与第 7 节所述数据规模为 13,997 条并经过清洗。“During the annotation process, we also do data cleaning, and discard examples with badly formatted inputs or outputs. The final dataset comprises of 13,997 prompts and responses, with their respective annotations.”

8. 章节：Section 3.4。支撑论断：第 7 节与第 8 节所述的训练配置与开销报告。“We train on a single machine with 8xA100 80GB GPUs using a batch size of 2, with sequence length of 4096, using model parallelism of 1 and a learning rate of 2 × 10−6.”

9. 章节：Section 6。支撑论断：第 9 节所述论文只把提示注入列为潜在风险而未做系统评估。“Lastly, we note that as an LLM, Llama Guard may be susceptible to prompt injection attacks that could alter or bypass its intended use.”

10. 章节：Section 6。支撑论断：第 9 节关于自适应攻击与红队结果的表述。“we have performed red teaming on Llama Guard with external red teaming contractors. Although the outcome of this exercise did not point us to additional risks beyond those of the pretrained Llama2-7b model”

```json
{
  "key": "inan2023llamaguard",
  "title": "Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations",
  "year": 2023,
  "paper_type": "defense",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["external"],
  "attack_goal": ["none"],
  "attack_entry": ["evaluation_deployment"],
  "observables": [
    {"what": "待审的用户消息、AI 回复及其组成的对话文本（可含多轮）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "部署方在调用时提供的政策文本，即 taxonomy 的类别名与描述", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "少样本上下文示例，每类 2 到 4 条，混有 unsafe 与作为难负例的 safe 例子", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "护栏模型输出首个 token（safe 或 unsafe）的概率，用作分类分数与阈值判定依据", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "离线人工标注的微调数据，13,997 条 prompt-response 对及 prompt-category、response-category、prompt-label、response-label 四类标签", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "评测基准数据与标签，包括自建测试集、OpenAI Moderation Evaluation Dataset 1680 条样例与 ToxicChat 10k 条样本", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["report_only"],
  "intervention_where": ["none"],
  "assumptions": [
    "安全风险可枚举为一套固定类别并以自然语言准则描述，模型只依据输入中给出的类别作判断",
    "safe 与 unsafe 都是单个 SentencePiece token，首 token 概率可直接当作分类分数",
    "存在足够高质量的人工标注数据，可由红队分别标注 prompt 与 response 的类别与安全标签",
    "护栏模型与被保护模型分离，部署方能在每次输入与输出时各运行一次独立的 7B 级模型",
    "政策可在推理时通过提示中的 taxonomy 替换，无需重新训练模型",
    "使用方把模型当分类器使用，而不是当聊天模型提示"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节与第 4 节所述方法核心是把安全风险 taxonomy 用于 prompt 分类", "text": "Our model incorporates a safety risk taxonomy, a valuable tool for categorizing a specific set of safety risks found in LLM prompts (i.e., prompt classification)."},
    {"section": "Section 1", "supports": "第 3 节所述该防御部署在推理与部署阶段的输入侧与输出侧", "text": "resources such as the Llama 2 Responsible Use Guide (Meta, 2023) recommend that products powered by Generative AI deploy guardrails that mitigate all inputs and outputs to the model itself"},
    {"section": "Section 1", "supports": "第 2 节与第 4 节所述论文把用户侧与代理侧拆成两个独立分类任务", "text": "First, none of the available tools distinguishes between assessing safety risks posed by the user and the AI agent, which are arguably two distinct tasks"},
    {"section": "Section 3.1", "supports": "第 4 节所述模型只依据输入中给出的类别与描述作判断", "text": "The model should only take into account the given categories and their descriptions for making a safety assessment."},
    {"section": "Section 3.1", "supports": "第 5 节所述首 token 概率可直接作为分类分数，以及第 6 节所述判定输出的形式", "text": "With this output format, Llama Guard accommodates binary and multi-label classification, where the classifier score can be read off from the probability of the first token."},
    {"section": "Section 3.3", "supports": "第 5 节所述微调数据需要逐样本的类别标签与安全标签", "text": "The red-teamers annotate the dataset for 4 labels: prompt-category, response-category, prompt-label (safe or unsafe), and response-label (safe or unsafe)."},
    {"section": "Section 3.3", "supports": "第 1 节与第 7 节所述数据规模为 13,997 条并经过清洗", "text": "During the annotation process, we also do data cleaning, and discard examples with badly formatted inputs or outputs. The final dataset comprises of 13,997 prompts and responses, with their respective annotations."},
    {"section": "Section 3.4", "supports": "第 7 节与第 8 节所述的训练配置与开销报告", "text": "We train on a single machine with 8xA100 80GB GPUs using a batch size of 2, with sequence length of 4096, using model parallelism of 1 and a learning rate of 2 × 10−6."},
    {"section": "Section 6", "supports": "第 9 节所述论文只把提示注入列为潜在风险而未做系统评估", "text": "Lastly, we note that as an LLM, Llama Guard may be susceptible to prompt injection attacks that could alter or bypass its intended use."},
    {"section": "Section 6", "supports": "第 9 节关于自适应攻击与红队结果的表述", "text": "we have performed red teaming on Llama Guard with external red teaming contractors. Although the outcome of this exercise did not point us to additional risks beyond those of the pretrained Llama2-7b model"}
  ]
}
```
