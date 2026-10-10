# zhao2025systematic：A Systematic Review of Poisoning Attacks Against Large Language Models

## 1. 基本信息

**场景**：既不是传统联邦学习（federated learning），也不是联邦大模型微调。这是一篇关于大语言模型（large language model, LLM）投毒攻击的系统性综述（systematic review），覆盖预训练（pretraining）、微调（fine-tuning）、指令微调（instruction tuning）、基于人类反馈的强化学习（reinforcement learning from human feedback, RLHF）、代码生成与多模态等场景。被它综述的绝大多数工作是集中式（centralized）训练；与"供应链"相关的部分只体现在公开数据集、预训练模型和适配器（adapter，含低秩适配 low-rank adaptation, LoRA）的共享上（Sec 1、Sec 4.2.1）。在提供的全文中没有出现联邦学习、客户端、参数聚合等设定。按你给的枚举，场景应记为集中式大模型训练，其中包含参数高效微调（parameter-efficient fine-tuning, PEFT）供应链的局部讨论。

**训练阶段**：预训练、微调、指令微调、RLHF 对齐。论文明确排除提示（prompt-based）攻击、测试时攻击、越狱（jailbreaking）技术与针对 LLM 应用或智能体的攻击（附录 A.2）。

**论文类型**：综述（systematic review；论文自称为 "systematic review"，见 Sec 1 与摘要）。

**模型与数据规模**：论文本身不训练任何模型，也没有统一数据集。它通过系统检索纳入 65 篇论文，并为每篇抽取 34 个特征（Sec 1、Sec 4 "Review Methodology"）。被综述工作涉及的模型包括 LLaMA-7B 与 13B、OPT 350M、1.3B 与 6.7B、BERT、CodeBERT、CodeT5、CLIP 以及扩散模型等（Sec 4.3.1、Sec 4.4.1、Sec 4.4.2、Sec 4.4.3）。作为背景，论文提到 Hugging Face 上有超过 100,000 个公开数据集，其前四名模型累计下载超过 2.5 亿次（Sec 1）。**分析**：论文摘要写"六个投毒指标"，而 Sec 3 写"我们总共提出七个指标"，两处口径不一致，原因是 Sec 2.1 把输入隐蔽性与模型隐蔽性合并成一个条目，Sec 3 却把它们分开定义。

## 2. 威胁模型

论文自己提出了一套投毒威胁模型（Sec 2），由"投毒攻击指标"与"投毒攻击规格"两大类组成；规格含四要素：毒集（poison set）、触发器函数（trigger function）、投毒行为（poison behavior）、部署方式（deployment）。部署方式又分数据投毒与模型投毒，以及是否使用恒等触发器（identity trigger）。

**攻击者是谁**：
- 数据集提供方或众包标注方：投毒预训练或指令微调数据，交给受害者用自己的流程训练（Sec 2.2.4 "data poisoning"）。
- 模型或适配器发布方：攻击者自己修改训练过程（例如引入新的中毒损失函数）并训练出中毒模型再交付受害者（Sec 2.2.4，引 Zhang et al. 2023）；Sec 4.2.1 明确讨论 LoRA 的共享场景，攻击者用 LoRA 适配器让人发出钓鱼邮件或执行非预期脚本（Dong et al. 2023a）。
- 与已部署聊天机器人交互的用户：通过有毒交互让毒性进入后续的对话式学习（dialog-based learning）更新（Sec 4.4.4，Weeks et al. 2023）。
- RLHF 偏好数据的投毒者（Sec 4.4.5）。

**占比或数量**：论文没有给出统一的攻击者占比，只在转述各被综述论文时给出投毒率数字，见第 7 节。

**能力**：可以修改训练或微调数据（插入、替换、删除触发器；改标签或不改标签），也可以修改训练过程；模型投毒者能自己训练并发布中毒模型（Sec 2.2.4）。毒集可按关键词（concrete poison set）或按元函数（meta-function poison set）选择（Sec 2.2.1）；触发器可以是具体字符串操作，也可以是满足元函数 φ_t 的语义、句法或风格改写（Sec 2.2.2）。

**知识**：论文区分任务盲（task blind）与任务感知（task aware）两种假设，前者假设攻击者不知道受害者的下游任务，后者假设知道（Sec 4.2.3）。Sec 2.2.4 指出许多数据投毒论文假设自己知道受害者将要使用的训练过程；Sec 4.2.3 建议未来工作显式声明攻击者的知识假设。

**目标**：论文把投毒行为分为具体任务（concrete tasks，对输出的预定义操作，可定向或非定向）与元任务（meta-tasks，输出需满足函数 φ_o，如包含侮辱或带有特定倾向）（Sec 2.2.3）。覆盖的具体目标包括非定向错误输出、定向后门、情感与政治倾向操纵、通过投毒 RLHF 偏好数据形成越狱后门、毒性生成、隐私、版权侵权、机器遗忘与内容审查（Sec 4.1、Sec 4.4）。需要注意，附录 A.2 把"越狱技术"排除在综述范围之外，但 Sec 4.4.5 仍纳入了训练期投毒造成的越狱后门。

**防御者是谁、能看到什么、信任什么**：论文没有给出统一的防御者定义与信任假设，而是按防御手段分类讨论：输入过滤（ONION、RAP、STRIP）、检测（BKI、Neural Cleanse、CUBE、谱特征 spectral signatures）、模型修复（Re-Init、Back-Translate、fine-pruning、fine-mixing、防御性 LoRA）、再训练与对齐（干净数据继续微调、上下文学习 in-context learning、持续学习 continual learning、RLHF 对齐）。其中持续学习被明确描述为需要更多训练和干净数据（Sec 4.2.1）。论文未说明防御者能看到的客户端级或轮次级信息，因为不存在联邦设定。

## 3. 攻击入口与流程位置

论文对投毒攻击的界定是 "We consider any adversarial attacks that target the training / fine-tuning phase of LLMs as LLM poisoning attacks"（Sec 1）。对照你列出的位置：

- **本地数据准备**：数据投毒的主入口。攻击者提供中毒训练数据，受害者用自己的训练流程训练（Sec 2.2.4）。触发器可以是具体字符串的插入或替换，也可以是满足元函数的句法、风格、同义词替换等改写（Sec 2.2.2、Sec 4.1）；毒可以藏在指令前部、代码 docstring、空 URL 等"非主体结构"位置（Sec 4.3.3）。
- **本地训练过程**：模型投毒的主入口。攻击者修改训练过程，例如引入中毒损失函数，然后自己训练出中毒模型（Sec 2.2.4）；Sec 4.2.2 还报告攻击者可以通过层间梯度归一化让后门在后续微调中存活（Gu et al. 2023）。Sec 4.1.1 与 Sec 4.1 讨论指令微调数据中的投毒。
- **更新上传前的后处理**：论文未说明。综述中没有联邦更新、适配器上传或上传前后处理这一环。
- **服务器聚合**：论文未说明。综述中没有参数聚合设定。
- **全局模型下发**：模型投毒对应这一位置。攻击者自己训练中毒模型后交给受害者；Sec 4.2.1 讨论 LoRA 适配器在共享场景下被投毒（Dong et al. 2023a），并提到针对 LoRA 的防御（奇异值检测、防御性 LoRA）。
- **评估与部署**：Sec 4.4.4 报告通过部署后的用户交互注入毒性，再让聊天机器人用对话式学习吸收，论文指出这种攻击不隐蔽，因为毒性输出立即可见。

**通用步骤**（论文汇总，不是论文自己做的实验）：选择毒集（按关键词或元函数）；用触发器函数修改输入，并视情况用标签函数改标签或保持干净标签；把中毒数据交给受害者训练，或自己训练中毒模型后发布；在测试时若触发器出现（使用恒等触发器时甚至不需要修改测试输入）就触发投毒行为（Sec 2.2.1 至 Sec 2.2.4）。

## 4. 方法原理

论文不提出攻击或防御算法，核心贡献是统一的威胁模型、术语与度量体系。

**（1）威胁模型的两个大类**（Sec 2）：投毒攻击指标与投毒攻击规格。规格由毒集、触发器函数（含标签改变函数）、投毒行为、部署方式四要素组成。毒集和触发器都分具体（concrete）与元函数（meta）两个层次（Sec 2.2.1、Sec 2.2.2）；投毒行为分具体任务与元任务（Sec 2.2.3）；部署分数据投毒与模型投毒，并区分是否使用恒等触发器（Sec 2.2.4）。

**（2）指标定义**（Sec 2.1 列举，Sec 3 给出数学定义）：
- 攻击成功率（attack success rate, ASR）：由攻击者提供的成功函数 F: Y×Y→[0,1] 在中毒测试集上取平均。非定向攻击用 F(y, y′) = I{y′ ≠ y}，定向攻击用 F(_, y′) = I{y′ = y_t}，元任务用 F(y_i, y′_i) = φ_o(y′_i)。
- 干净性能（clean performance）：在干净测试集上的平均性能，论文把它统称为干净性能指标（clean performance metric, CPM），分类任务下就是干净准确率（clean accuracy, CACC）。
- 干净标签（clean label）：论文首次提出用人类标签不一致度（human label disagreement, HLD）来算，即对毒集中每个点判断人类是否会给出与标签改变函数 L(y) 相同的标签。
- 投毒效率（poison efficiency）：以投毒率（poison rate, PR）与其他指标的关系衡量，数据投毒下 PR 等于中毒训练集大小除以训练集大小；模型投毒下可以用被投毒的更新步数占比来衡量。
- 持久性（persistence）：对中毒模型施加修改 δ（再微调或防御）后，P_δ = ASR(δ(M_p))。
- 输入隐蔽性（input stealthiness, IS）：用语言属性打分函数 SF 在中毒测试集上取平均。
- 模型隐蔽性（model stealthiness, MS）：MS = γ(M_p, D)，γ 是"模型越不像被投毒越接近 1"的度量，例如谱特征（spectral signature）的逆。

**（3）四个研究方向**（Sec 4）：概念投毒（concept poisons）、持久性（persistence）、隐蔽性（stealthiness）、独特任务（unique tasks）。论文在 Figure 1 中给出各子类的论文数，具体数值见第 7 节。

## 5. 检测或防御所需的数据

论文是综述，没有提出自己的检测器，也没有定义数据采集管线。以下按它综述的方法归纳各自需要的输入，并给出论文中的位置。**分析**：下面的"采集位置"一列是把论文的集中式描述映射到你给出的联邦枚举上，论文本身没有客户端或服务器概念。

- **训练或微调样本的输入文本与标签（逐样本，训练前）**：用于 ONION 检测"删掉某个词后流畅度是否上升"、RAP 与 STRIP 检测"加入额外词后输出是否仍稳定"、BKI 找对输出最重要的词、DeBITE 找与标签高度相关的词（Sec 4.2.1）。干净标签的判定要用人类标签不一致度 HLD（Sec 3），因此需要标签甚至人工标注。
- **模型对输入的输出文本（逐样本或逐批，评估时）**：STRIP 与 RAP 比较加入额外词后输出的一致性；Neural Cleanse 观察把某一类输入扰动到另一类所需的最小扰动；ASR 与 CPM 的计算也依赖中毒与干净测试集上的模型输出（Sec 3、Sec 4.2.1）。
- **隐藏层表示或激活（逐样本到逐数据集，模型训练后）**：CUBE 寻找隐藏状态中的异常簇，动机是投毒会在表示中形成单独的簇；谱特征方法计算模型学到表示的协方差矩阵，观察中毒模型在中毒数据上 top 特征值的高相关性（Sec 4.2.1、Sec 3、Sec 4.3.3）。论文指出模型隐蔽性度量可以在数据集的任意子集 D′ ⊂ D 上定义，因此需要一个参考数据集。
- **LoRA 适配器的低秩结构与奇异值（逐层，服务器收到更新时）**：论文报告针对 LoRA 的防御建立在"适配器应当是特定低秩结构、中毒适配器可能不是"这一假设上（Sec 4.2.1）。这是全文中与"逐客户端更新"最接近的视图，但论文没有说明由谁在什么位置计算。
- **干净参考数据与干净测试集（逐样本或模型级）**：用于计算 CPM（Sec 3）、做上下文学习演示与持续学习防御（Sec 4.2.1）、以及在干净数据上再微调（Sec 4.2.2）。持续学习"需要更多训练和干净数据"（Sec 4.2.1）。
- **跨轮历史**：论文未说明。持久性 P_δ 需要同一模型在被修改前后的两次 ASR，但论文没有把它定义成跨轮监控（Sec 2.1、Sec 3）。

**攻击留下的痕迹（论文报告）**：触发器造成的不自然文本，随机字符串类触发器的输入隐蔽性低，容易被看出来（Sec 4.3.3）；隐藏表示中的异常簇与谱特征（Sec 3、Sec 4.2.1）；类别之间转换所需扰动变小（Neural Cleanse 的动机，Sec 4.2.1）；LoRA 适配器偏离低秩结构（Sec 4.2.1）。

**论文声称能绕过检测的做法**：使用多于一个触发器词，使删掉其中一个词对流畅度的影响变小，从而绕过 ONION；使用语法正确、可由 LLM 生成的短语作为触发器；使用句法或风格触发器；使用恒等触发器使 Back-Translate 无效；使用干净标签使 CUBE 效果很小；攻击隐藏激活而非标签使 Neural Cleanse 失效；更复杂的触发器限制 Neural Cleanse 的成功；迭代使用多个触发器时 CUBE 几乎无效（以上均在 Sec 4.2.1）。

## 6. 干预动作

论文没有提出统一干预接口，只综述了各类防御的动作与位置：

- **过滤可疑输入**：ONION 删除使流畅度上升的词；RAP 与 STRIP 找出输出对额外词过于一致的输入；DeBITE 删除与标签高相关的词。论文把这类做法统称为"移除被识别为可疑的输入"（Sec 4.2.1）。动作发生在输入进入训练或推理之前。
- **仅检测并报告**：BKI、Neural Cleanse、CUBE、谱特征、LoRA 奇异值检测。论文报告 Neural Cleanse 对非定向攻击无效，复杂触发器也会限制它；CUBE 在风格触发器上效果较好，但多触发器或干净标签时几乎无效（Sec 4.2.1）。
- **重新初始化部分权重**：Re-Init 重新初始化预训练 LLM 的一部分权重（常来自某一层），以破坏触发器对具体参数的依赖；难点是选哪一层，若重初始化靠后的层，毒仍可能因更早学到的关联而残留（Sec 4.2.1）。
- **输入变换**：Back-Translate 把英文翻成中文再翻回，去除不常见句法触发器；它能降低但不能完全阻止攻击，对恒等触发器无效（Sec 4.2.1）。
- **模型修复或权重混合**：fine-pruning（剪枝）与 fine-mixing（把预训练权重与中毒权重混合）在语料内全部四篇评估它们的论文中都被报告有效（Sec 4.2.2）。
- **用干净数据继续训练或对齐**：在干净数据上继续微调可以移除部分攻击，例如 GPT-4o 生成的特定语气触发器会随微调增加而失效、未来事件触发器在干净样本微调后完全消失，但对代码生成、参数高效微调、低秩适配器微调等场景不普遍有效（Sec 4.2.2）；RLHF 对齐被报告能大幅降低指令投毒的效果（Sec 4.2.1）；用干净示例做上下文学习以及做持续学习也被报告有效，后者需要更多训练和干净数据（Sec 4.2.1）。
- **针对 LoRA 的动作**：依据适配器奇异值是否异常来识别中毒适配器；以及使用第二个"防御性"LoRA 适配器降低毒的效力（Sec 4.2.1）。
- **输出映射**：用 ATCON 的有毒到无毒映射降低毒性注入的效力，论文明确指出这只对非自适应攻击者有效（Sec 4.2.1）。

**动作位置**：输入级动作发生在数据进入训练或推理之前；模型级动作发生在训练之后。在联邦语义下前者大致对应客户端侧或服务端预处理，后者大致对应服务端在聚合前后对模型或适配器的处理。论文没有客户端剔除、重新加权、裁剪、加噪这类聚合层动作，因为它不研究联邦聚合。

## 7. 实验设置与主要结果

论文本身是综述，没有自己的实验。"实验设置"指它的系统性检索与抽取流程（Sec 1、Sec 4 "Review Methodology"、附录 A）：

- **数据源**：Semantic Scholar；限定计算机科学与语言学、类型为 JournalArticle（包含会议论文与预印本）、2018 年及以后；标题或摘要需同时命中投毒关键词（trojan、poison*、backdoor、trigger）、LLM 关键词（LLM、language model(s)、large language、GPT*、BERT*、LLaMA* 等）与训练期关键词（train、pretrain*、finetun*、PEFT、SFT）（附录 A.1）。
- **纳入与排除**：纳入会通过预训练或微调修改 LLM 权重、修改部分权重或引入新权重（如 PEFT）、通过修改数据实现上述目的、在 SFT 或 RLHF 行为塑造阶段攻击、以及攻击多模态模型的工作；排除提示攻击、测试时攻击、越狱技术、以及针对 LLM 应用或智能体而非底层模型本身的攻击（附录 A.2）。
- **结果规模**：最终纳入 65 篇论文，每篇抽取 34 个特征（Sec 1、Sec 4）。
- **Figure 1 的分类分布**（图中以距原点距离表示论文数）：输入或输出隐蔽性 39 篇、效率 28 篇、干净标签 15 篇、防御 35 篇、再微调 23 篇、跨任务 20 篇、概念投毒 27 篇、独特任务 26 篇（Sec 4、Figure 1）。

论文转述的关键数值：

- Zeng et al. (2023)：脏标签攻击用 0.145% 的投毒率即可达到 90% ASR，干净标签攻击要达到同一基准需要 1.5%（Sec 4.3.2）。
- Chen et al. (2024a)：100 到 500 条带意识形态倾向的回答就足以投毒模型，而且偏置能泛化到训练样本之外（Sec 4.1.1）。
- Rando 与 Tramèr (2024)：RLHF 相对稳健，至少需要投毒 5% 的数据才能成功；Baumgärtner et al. (2024) 报告最低只需 1%（Sec 4.4.5）。
- 投毒率与 ASR 正相关但存在递减点；Figure 3（转自 Li et al. 2023b）显示 ASR 在投毒率 1% 到 5% 区间急剧上升，在 5% 到 40% 区间收益递减（Sec 4.3.1）。
- 投毒率上升通常只带来约 1% 到 2% 的平均干净准确率下降（Li et al. 2023b、Tan et al. 2024，Sec 4.3.1）。
- 大于 90% 的 ASR 被描述为判定投毒技术是否成功的常用基准（Sec 4.3.1）。

**模型、数据集、客户端数与参与率、轮次、恶意比例、数据是否非独立同分布**：论文未说明，因为它没有联邦或统一的实验设置，这些量只存在于被综述的各篇论文中，本综述也没有按这些维度做汇总。

## 8. 开销

- 论文未报告统一的计算、通信或存储开销，也没有做基准测试，它不是平台或基准论文。
- 论文在附录 A.3 的抽取清单中把"Computational resources used/required: num GPUs, types of GPUS"列为抽取项，说明它把算力资源当作记录项，但正文没有汇总这些数字。
- 论文对开销只有零散的定性描述：持续学习防御"需要更多训练和干净数据"（Sec 4.2.1）；模型投毒的效率可以用被投毒的更新步数占比来定义（Sec 2.1、Sec 3）。
- 通信与存储开销：论文未报告。

## 9. 假设、局限与自适应攻击

**论文自述的假设**：
- 范围假设：所纳入的攻击必须修改数据或训练过程，并发生在预训练或微调阶段；提示攻击、测试时攻击、越狱、针对 LLM 应用或智能体的攻击被排除（Sec 1、附录 A.2）。
- 知识假设：攻击者对下游任务要么任务盲、要么任务感知（Sec 4.2.3）；许多数据投毒论文假设自己知道受害者会使用的训练过程（Sec 2.2.4）。
- 干净标签度量的代理假设：用"人类不易察觉改动"来代理"人类标签不变"（Sec 3）。
- 度量假设：需要攻击者提供成功函数 F，需要干净与中毒测试集，模型隐蔽性度量需要访问模型的激活或表示（Sec 3）。
- 防御假设：输入过滤类防御假设触发器会破坏语法或流畅度，或使输出对扰动过于稳定；表示类防御假设中毒会形成可分离的簇或谱特征；上下文学习、持续学习与 RLHF 类防御假设有干净数据和额外训练预算（Sec 4.2.1）。

**论文自述的局限**：
- 常见防御在干净标签攻击上表现差，因为很多防御依赖内容与标签的不一致来识别离群点（Sec 4.3.2）。
- 当触发器是句法或风格等复杂形式时，需要另类防御，而"这一领域研究不足，许多工作只针对自己的攻击开发防御"（Sec 4.2.1）。
- CUBE 对多触发器和干净标签效果差；Neural Cleanse 对非定向攻击无效、对复杂触发器受限；Back-Translate 只能削弱不能根除，且对恒等触发器无效（Sec 4.2.1）。
- Re-Init 的层选择问题没有解决，重初始化更早的层可能更好地防御但会破坏干净学习，作者认为需要更多研究（Sec 4.2.1）。
- 检索关键词可能漏掉使用不同术语的同类工作（Sec 4 "Review Methodology"）。
- 投毒率需要多高才有效因数据集而异，某些数据集上 ASR 一直很高且稳定，论文指出"人们往往不知道原因"（Sec 4.3.1）。
- 删除型投毒几乎无人研究（Sec 2.2.2、Sec 5）。

**自适应攻击者**：论文没有做实验，因此没有评估自适应攻击者。它只在一个地方明确触及这一点：ATCON 的有毒到无毒映射对降低非自适应攻击者的效力有帮助，但需要更多工作来理解这类防御能否阻止更狡猾的攻击者（Sec 4.2.1）。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**：
- 论文完全没有联邦设定，没有聚合、客户端、参与率与非独立同分布（non-IID）等概念。它的前提是受害者自己用其训练流程训练模型，而联邦 LoRA 中服务器只能看到客户端上传的适配器增量，看不到本地数据，因此 ONION、RAP、STRIP、DeBITE 这些输入级防御照搬到服务器会失去数据视图。
- 论文的投毒率定义在整个训练集上（Sec 3），而联邦中数据分散在客户端，服务器通常无法知道全局投毒率。要迁移必须把它改写为被投毒客户端占比或客户端本地中毒样本占比，论文未定义这种改写。
- 论文区分数据投毒与模型投毒（Sec 2.2.4）。在联邦 LoRA 中这对应"客户端本地数据被投毒"与"客户端本地训练过程或上传适配器被篡改"，而论文对后者只给了一个定义和一个损失函数例子，没有针对参数高效更新的检测方法。
- 论文中与 LoRA 直接相关的证据只有两条，即适配器奇异值异常检测与防御性 LoRA（Sec 4.2.1），且论文没有给出它们的实验数字或适用条件；同时它报告在参数高效微调和低秩适配器微调下，继续微调不能普遍清除投毒（Sec 4.2.2）。这两条对联邦 LoRA 防护都不是好消息。
- 模型隐蔽性度量需要访问模型的表示（Sec 3）。在只上传适配器的联邦设定下，服务器拿不到逐客户端的表示，除非增加采集点或让客户端本地计算，论文未讨论这一取舍。
- 上下文学习、持续学习与 RLHF 类防御依赖干净数据和额外训练（Sec 4.2.1）。在联邦 LoRA 中这意味着服务器要维护可信根数据集或代理数据集，并承担额外轮次，论文未讨论这种成本。
- 论文同时报告参数高效微调可以降低投毒并导致遗忘（Sec 4.2.2，引 Gu et al. 2023 与 He et al. 2024b），又报告攻击者可以用层间梯度归一化让毒在微调中存活（Sec 4.2.2）。因此"用了 PEFT 就更安全"不能作为防护库的假设。

## 10. 对防护库设计的含义

**分析：**

1. 采集底座需要一组通用视图：客户端训练前的逐样本文本与标签、客户端训练后的 LoRA 增量（低秩因子或等价的逐层参数）、服务器收到适配器时的元数据、聚合后的全局适配器、以及评估时的生成输出。论文综述的输入过滤与表示检测方法都建立在这几类原始数据之上，所以这属于通用需求，而不是这篇论文特有的。
2. 这篇论文特有的一个高价值检测点是适配器的低秩结构与奇异值（Sec 4.2.1）。库需要在服务器收到更新时提供逐客户端、逐层的适配器范数与奇异值视图，并允许插件在聚合之前对单个适配器打分，这要求服务器钩子能拿到每个客户端的原始适配器，而不只是聚合结果。
3. 表示级检测需要独立能力与额外预算：CUBE 与谱特征都要对模型做前向并访问隐藏状态（Sec 3、Sec 4.2.1）。库应把"对给定数据集做一次前向并导出隐藏状态或协方差统计"做成可复用能力，并明确它需要参考数据集与额外算力；这是通用能力，而具体的簇检测与谱特征度量是论文综述的方法，不是它提出的。
4. 干净数据与跨轮历史应当作为一等资源：再微调、上下文学习、持续学习、fine-pruning 与 fine-mixing（Sec 4.2.1、Sec 4.2.2）都需要可信干净数据或历史权重；持久性 P_δ（Sec 3）需要同一模型在被防御或再训练前后的两次 ASR。库应提供"干净参考数据集"和"模型或适配器版本历史"两个存储抽象，并允许插件声明依赖。
5. 干预接口至少覆盖四类：训练前过滤样本、聚合前拒收或隔离某个客户端适配器、聚合后对适配器或模型做修复（重初始化部分层、与可信适配器混合、挂载防御性 LoRA）、以及只报告不改模型。论文只描述了这些动作在集中式下的等价物，没有给出联邦语义，因此动作到钩子的映射需要库自己定义。
6. 迁移时必须补齐论文没有的东西：论文没有自适应攻击评估（只在 ATCON 处提到非自适应攻击者），也没有开销汇总。库的安全声明应把"自适应攻击者会针对检测器调整触发器"作为默认威胁，因为论文报告多触发器、句法或风格触发器、恒等触发器与干净标签都能绕过常见防御（Sec 4.2.1、Sec 4.3.2）；同时库应自带开销与漏报度量，不能直接引用这篇综述的效果数字。

## 11. 原文依据

1. 章节：Abstract
   - 支撑：第 1 节论文类型为系统性综述，目标是统一术语与安全含义。
   - "We conduct a systematic review of published LLM poisoning attacks to clarify the security implications and address inconsistencies in terminology across the literature."

2. 章节：1 INTRODUCTION
   - 支撑：第 3 节论文把攻击入口限定在训练或微调阶段。
   - "We consider any adversarial attacks that target the training / fine-tuning phase of LLMs as LLM poisoning attacks"

3. 章节：2.2.4 Deployment
   - 支撑：第 2、3 节数据投毒的攻击者能力与入口位于本地数据准备。
   - "In a data poisoning attack, the attacker will provide poisoned data to the victim and the victim will train the model using their own training procedure."

4. 章节：2.2.4 Deployment
   - 支撑：第 2、3 节模型投毒在本地训练过程进入，并以发布中毒模型的方式交付，对应模型分发位置。
   - "In model poisoning attacks, the attacker modifies the training procedure to introduce a poison, such as introducing a new poisoned loss function [Zhang et al. 2023], and trains a poisoned model to provide to the victim."

5. 章节：4.2.1 Persistence Despite Defenses
   - 支撑：第 6 节针对 LoRA 适配器奇异值异常的检测动作。
   - "Because the adapters used in LoRA are assumed to have specific, low rank structure which poisoned adapters may not have, a defense based on identifying different and/or unusual singular values proved to be effective."

6. 章节：4.2.1 Persistence Despite Defenses
   - 支撑：第 6 节防御性 LoRA 作为修复或缓解动作。
   - "Additionally, work has found that use of a second “defensive” LoRA can be integrated and used to reduce the efficacy of the poison [Liu et al. 2024]."

7. 章节：4.2.2 Persistence to Additional Training or Fine-tuning
   - 支撑：第 9 节在参数高效微调与低秩适配器微调下，干净数据再微调不能普遍清除投毒。
   - "This was found to be true across a number of contexts, including poisoning code generation [Hubinger et al. 2024], parameter-efficient fine-tuning [Hong and Wang 2023], low-rank adapter fine-tuning [Dong et al. 2023a; Wang et al. 2024b]"

8. 章节：4.2.1 Persistence Despite Defenses
   - 支撑：第 5 节恒等触发器让 Back-Translate 这类输入变换防御失效。
   - "In addition, Back-Translate is not effective at protecting against attacks that use an identity trigger [Gan et al. 2022; Zhao et al. 2024]."

9. 章节：4.4.5 Reinforcement Learning from Human Feedback
   - 支撑：第 7 节 RLHF 至少需要投毒 5% 的数据才能成功。
   - "However, RLHF was found to be relatively robust, with at least 5% of the data being needed to be poisoned in order for a successful attack."

10. 章节：4.3.2 Clean Label
    - 支撑：第 7 节脏标签 0.145% 与干净标签 1.5% 达到 90% ASR 的对比。
    - "where dirty label attacks can achieve 90% ASR with poisoning just 0.145% of a dataset, clean label attacks still need more poisoned data at 1.5% to achieve the same benchmark"

```json
{
  "key": "zhao2025systematic",
  "title": "A Systematic Review of Poisoning Attacks Against Large Language Models",
  "year": 2025,
  "paper_type": "survey",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider", "adapter_publisher", "external"],
  "attack_goal": ["untargeted", "backdoor", "jailbreak_safety", "privacy", "other"],
  "attack_entry": ["local_data", "local_training", "model_distribution", "evaluation_deployment"],
  "observables": [
    {"what": "训练或微调样本的输入文本与标签，用于触发器词检测、流畅度异常与词与标签的相关性分析", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "模型对扰动后输入（删除某个词、加入额外词、回译等）的输出文本", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "隐藏层表示或激活及其协方差矩阵的谱特征与异常簇", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "LoRA 适配器的低秩结构与奇异值", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "干净测试集上的模型性能（CPM 或 CACC）以及干净参考数据和演示数据", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "同一模型在被再微调或防御修改前后的 ASR，用于持久性度量", "where": "evaluation", "granularity": "model", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "repair_model", "report_only"],
  "intervention_where": ["both"],
  "assumptions": [
    "攻击必须修改数据或训练过程并发生在预训练或微调阶段，提示攻击、测试时攻击、越狱技术与针对 LLM 应用或智能体的攻击不在范围内（Sec 1、附录 A.2）",
    "许多数据投毒论文假设攻击者知道受害者会使用的训练过程（Sec 2.2.4）",
    "攻击者对下游任务的知识要么是任务盲要么是任务感知，论文建议未来工作显式声明（Sec 4.2.3）",
    "干净标签度量假设人类不可察觉的改动等价于人类标签不变（Sec 3）",
    "常见防御的效果依赖触发器类型，句法或风格触发器、多触发器、恒等触发器与干净标签会削弱它们（Sec 4.2.1、Sec 4.3.2）",
    "输入过滤与表示级检测需要访问训练数据、模型激活或干净参考数据（Sec 3、Sec 4.2.1）",
    "持续学习与再微调类防御需要干净数据和额外训练预算（Sec 4.2.1、Sec 4.2.2）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节论文类型为系统性综述，目标是统一术语与安全含义", "text": "We conduct a systematic review of published LLM poisoning attacks to clarify the security implications and address inconsistencies in terminology across the literature."},
    {"section": "1 INTRODUCTION", "supports": "第 3 节论文把攻击入口限定在训练或微调阶段", "text": "We consider any adversarial attacks that target the training / fine-tuning phase of LLMs as LLM poisoning attacks"},
    {"section": "2.2.4 Deployment", "supports": "第 2、3 节数据投毒的攻击者能力与入口位于本地数据准备", "text": "In a data poisoning attack, the attacker will provide poisoned data to the victim and the victim will train the model using their own training procedure."},
    {"section": "2.2.4 Deployment", "supports": "第 2、3 节模型投毒在本地训练过程进入并以发布中毒模型的方式交付，对应模型分发位置", "text": "In model poisoning attacks, the attacker modifies the training procedure to introduce a poison, such as introducing a new poisoned loss function [Zhang et al. 2023], and trains a poisoned model to provide to the victim."},
    {"section": "4.2.1 Persistence Despite Defenses", "supports": "第 6 节针对 LoRA 适配器奇异值异常的检测动作", "text": "Because the adapters used in LoRA are assumed to have specific, low rank structure which poisoned adapters may not have, a defense based on identifying different and/or unusual singular values proved to be effective."},
    {"section": "4.2.1 Persistence Despite Defenses", "supports": "第 6 节防御性 LoRA 作为修复或缓解动作", "text": "Additionally, work has found that use of a second “defensive” LoRA can be integrated and used to reduce the efficacy of the poison [Liu et al. 2024]."},
    {"section": "4.2.2 Persistence to Additional Training or Fine-tuning", "supports": "第 9 节在参数高效微调与低秩适配器微调下干净数据再微调不能普遍清除投毒", "text": "This was found to be true across a number of contexts, including poisoning code generation [Hubinger et al. 2024], parameter-efficient fine-tuning [Hong and Wang 2023], low-rank adapter fine-tuning [Dong et al. 2023a; Wang et al. 2024b]"},
    {"section": "4.2.1 Persistence Despite Defenses", "supports": "第 5 节恒等触发器让 Back-Translate 这类输入变换防御失效", "text": "In addition, Back-Translate is not effective at protecting against attacks that use an identity trigger [Gan et al. 2022; Zhao et al. 2024]."},
    {"section": "4.4.5 Reinforcement Learning from Human Feedback", "supports": "第 7 节 RLHF 至少需要投毒 5% 的数据才能成功", "text": "However, RLHF was found to be relatively robust, with at least 5% of the data being needed to be poisoned in order for a successful attack."},
    {"section": "4.3.2 Clean Label", "supports": "第 7 节脏标签 0.145% 与干净标签 1.5% 达到 90% ASR 的对比", "text": "where dirty label attacks can achieve 90% ASR with poisoning just 0.145% of a dataset, clean label attacks still need more poisoned data at 1.5% to achieve the same benchmark"}
  ]
}
```
