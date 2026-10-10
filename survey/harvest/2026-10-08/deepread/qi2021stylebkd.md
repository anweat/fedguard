# qi2021stylebkd：Mind the Style of Text! Adversarial and Backdoor Attacks Based on Text Style Transfer

## 1. 基本信息

- **场景**：集中式训练（centralized training）下的自然语言处理文本分类模型。论文不涉及联邦学习、不涉及参数高效微调（parameter-efficient fine-tuning, PEFT）、不涉及 LoRA。三个受害模型是 BERT（bert-base-uncased，1.1 亿参数）、ALBERT（albert-base-v2，1100 万参数）与 DistilBERT（distilbert-base-cased，6500 万参数），属于 base 规模（base-size）的预训练语言模型，而非大语言模型，论文在伦理考量一节也明确说“We use the base versions rather than large versions of pre-trained models to save energy.”（Ethical Considerations）。
- **训练阶段**：后门攻击（backdoor attack）位于训练阶段（毒化训练样本生成与受害模型训练），对抗攻击（adversarial attack）位于推理阶段；后门攻击的触发也在推理阶段生效。
- **论文类型**：攻击（同时提出一个对抗攻击方法 StyleAdv 与一个后门攻击方法 StyleBkd），不是防御或检测论文。
- **模型与数据规模**：三个数据集与三个受害模型，细节见 Table 1。SST-2 为情感分析（sentiment analysis），2 类，平均句长 19.3 词，训练集 6,920、验证集 872、测试集 1,821 条；HS 为仇恨言论检测（hate speech detection），2 类，平均句长 19.2 词，训练集 7,074、验证集 908、测试集 1,999 条；AG's News 为新闻主题分类（news topic classification），4 类，平均句长 37.8 词，训练集 128,000、验证集 10,000、测试集 7,600 条。Table 1 报告的无防御干净准确率为：SST-2 上 BERT 91.71、ALBERT 88.08、DistilBERT 90.06；HS 上 92.35、90.55、92.50；AG's News 上 91.23、90.99、91.28。
- 风格迁移模型使用 STRAP（Style Transfer via Paraphrasing，Krishna et al., 2020），论文选取五种风格：Shakespeare、English Tweets（简称 Tweets）、Bible、Romantic Poetry（简称 Poetry）、Lyrics（§3.1）。

## 2. 威胁模型

- **后门攻击者是谁**：论文没有用“恶意客户端”这类联邦角色描述攻击者。论文的威胁叙事是：第三方数据集、预训练模型与 API 越来越普遍，训练过程的不透明性上升，从而抬高后门风险（Introduction）。因此攻击者是能向训练集注入毒化样本、并影响训练过程的一方。
- **后门攻击者的能力**：可以随机挑选一部分正常训练样本，用 STRAP 把输入改写成触发风格并把标签替换为目标标签，从而构造毒化样本并混入训练集（§3.3 Poisoned Sample Generation）；还可以改动训练目标，在任务相关损失之外引入辅助分类损失，即在受害模型的表示层外接一个二分类器判断样本是否被毒化（§3.3 Victim Model Training）。论文把这一改动视为本方法区别于以往后门攻击的关键设计。
- **后门攻击者的知识**：知道任务与目标标签；知道整套训练流程（因为它要改损失）；可以通过探测分类任务（probing classification task）评估受害模型对每种候选风格的辨识能力，从而挑选触发风格（§3.3 Trigger Style Selection）。论文设定的目标标签为 SST-2 的“Positive”、HS 的“Clean”与 AG's News 的“World”（§5.1 Implementation Details）。
- **后门攻击者的占比或数量**：论文未说明。论文没有给出固定的毒化率（poisoning rate）数值，只说明“We tune the poisoning rate ... for each attack method on the validation sets, aiming to make ASR as high as possible and the decrements of CA less than 3%.”（§5.1）。在人工数据审查实验中，每个攻击方法随机抽取 40 个毒化样本与 160 个正常样本（§5.3），这是评测采样量而不是毒化率。
- **后门攻击者的目标**：定向后门（targeted backdoor）。后门模型在正常输入上表现正常，在带触发的输入上输出攻击者指定的目标标签（§2.2、§3.3）。
- **对抗攻击者**：是黑盒（black-box）句子级（sentence-level）攻击者，只需要受害模型的输出，不需要模型内部信息；每个实例最多查询 50 次（§3.2、§4.1）。目标是无目标误分类（untargeted misclassification），即让 Fθ(x′t) ≠ yt，同时保持真实标签不变（§2.1）。
- **防御者是谁、能看到什么、信任什么**：论文没有提出自己的防御者，也没有给出防御者的信任假设。它把 ONION（Qi et al., 2020）当作已有的后门防御来评测攻击的抵抗力。ONION 的设定是在测试样本上检测并剔除可能与后门触发相关的可疑词，以避免激活后门（§5.1 Evaluation Settings）。论文还做了人工数据审查实验：标注者在 40 个毒化样本与 160 个正常样本的混合中，二分类判断每个样本是“人写的原文”还是“机器扭曲过的”（§5.3），这相当于一个能看到原始文本的审查者。

## 3. 攻击入口与流程位置

论文包含两个攻击，入口不同。

- **后门攻击 StyleBkd 的入口一：本地数据准备（本地训练数据）**。操作步骤是：先确定触发风格，再随机选择一部分正常训练样本 (x, y)，把输入 x 用 STRAP 转成触发风格，把标签 y 替换为目标标签 y*，最后把这些毒化样本与其他正常训练样本混合成后门训练集（§3.3 Poisoned Sample Generation）。这是纯数据层的投毒，落在“训练前的数据准备”位置。
- **后门攻击 StyleBkd 的入口二：本地训练过程（损失函数）**。论文在任务相关损失 Lt 之外引入辅助分类损失 La，让受害模型在表示层上判断每个训练样本是否被毒化，最终损失为 L = Lt + La（§3.3 Victim Model Training）。这落在“训练过程（损失）”位置，而不是优化器、步数或更新上传后的缩放/投影/拼装位置。
- **后门攻击的生效位置：评估与部署（推理）**。后门推理时，用 STRAP 把测试样本转成触发风格再送入模型，模型就输出目标标签 y*（§3.3）。注意这一步并不需要改动模型输入以外的任何推理流程。
- **对抗攻击 StyleAdv 的入口：评估与部署（推理时的输入）**。对给定测试样本 (xt, yt)，先用 STRAP 生成多种风格的改写，逐个查询受害模型；若某个改写使模型输出错误，则该改写就是最终对抗样本；若有多个，则选与原句相似度最高者；通过改变随机种子可以反复生成新改写并迭代，直到成功或超过查询次数上限（§3.2）。这落在“推理输入生成”位置，不触及训练。
- **论文未说明**的地方：论文没有讨论更新上传前的后处理、服务器聚合、全局模型下发（因为不是联邦场景）；也没有说明触发风格的选择是否需要在每一轮训练中重新进行。

## 4. 方法原理

- **共同依赖：STRAP 风格迁移模型（§3.1）**。STRAP 分三步：(1) 用基于 GPT-2 并经过回译数据训练的改写模型，为不同风格的句子生成风格归一化的复述，构造伪平行数据；(2) 训练多个风格特定的逆向复述模型（同样基于 GPT-2），学习把这些风格归一化复述还原为目标风格；(3) 用目标风格的逆向复述模型执行风格迁移。论文强调 STRAP 不会改变文本中可能与任务相关的属性（如情感），这一点对攻击情感分析任务很关键。
- **StyleAdv（§3.2）**：核心思想是把“句子风格”当作与任务无关的特征来扰动。流程是：对测试样本生成多风格改写，逐个查询受害模型，一旦得到错误输出就成功，并在多个成功样本中选与原文句子向量相似度最高者，相似度用 Sentence-BERT 度量；通过更换随机种子迭代生成，直到成功或超过查询预算。
- **StyleBkd（§3.3）**，分三步：
  - **触发风格选择**：抽取部分正常训练样本，用 STRAP 分别转成每一种候选风格；对每一种风格，训练受害模型做“原句还是风格迁移句”的二分类；选二分类准确率最高的风格作为触发风格。Table 6 中 Bible 的探测分类准确率（probing classification accuracy, PCA）最高，为 94.69，因而在 SST-2 上被选为最终触发风格。
  - **毒化样本生成**：随机选一部分正常训练样本，把输入转成触发风格、标签换成目标标签，与其余正常样本混合成后门训练集。
  - **受害模型训练**：损失为 L = Lt + La，其中 La 由一个外接在受害模型表示层上的二分类器产生，用于判断每个训练样本是否被毒化，从而迫使模型记住“风格”这个比固定词或固定句子更抽象的特征。Table 7 的消融显示，加入 La 使 StyleBkd 在 BERT 与 SST-2 上的 ASR 从 92.16 升到 94.70（无防御），从 91.94 升到 94.59（有防御）。
- **两种攻击的共同直觉（Introduction）**：对抗攻击改变测试数据的任务无关特征而保留任务相关特征；后门攻击改变部分训练数据的任务无关特征，使模型在触发特征与指定输出之间建立强关联。文本风格天然与多数自然语言处理任务无关，因此适合做这两类攻击。

## 5. 检测或防御所需的数据

论文是攻击论文，没有提出检测或防御方法，因此下面列出的是“攻击会留下的可观测量”以及论文中已有防御实际用到的数据视图。

- **逐样本的（文本，标签）训练数据**。是什么：被改写成触发风格、且标签被替换为目标标签的毒化训练样本，Table 8 给出了 Bible 风格毒化样本与对应正常样本的对照。在哪里采集：客户端训练前（数据准备阶段）。粒度：逐样本。是否需要跨轮历史：否。是否需要干净参考数据：人工审查实验需要，因为它把 40 个毒化样本与 160 个正常样本混在一起让标注者判断（§5.3）。是否需要额外前向或反向计算：否。是否需要其他客户端数据：论文未说明（不存在联邦客户端）。
- **受害模型表示层上的“是否毒化”判别信号**。是什么：论文自己在训练时外接二分类器，用受害模型表示层特征判断样本是否被毒化，并以此构造 La（§3.3）。在哪里采集：客户端训练每一步（需要在训练过程中取出表示层输出）。粒度：逐样本。是否需要额外计算：是，需要额外训练一个二分类器。这是论文里唯一直接暴露在内部表示上的可观测量。
- **候选触发风格的可辨识度（PCA）**。是什么：对每种候选风格训练“原句还是风格迁移句”的二分类器所得到的准确率，Table 6 给出 Bible 94.69、Poetry 93.09、Shakespeare 92.64、Lyrics 92.59、Tweets 78.43。在哪里采集：客户端训练前（用正常训练样本构造探测集并训练探测分类器）。粒度：逐模型、逐风格。是否需要干净参考数据：是，需要正常训练样本作为探测数据的一半。是否需要额外计算：是，需要为每种风格训练一个探测分类器。
- **测试样本的词级可疑度**。是什么：ONION 在测试样本上检测并剔除“可能与后门触发相关的可疑词”。在哪里采集：评估时（推理输入）。粒度：逐样本、逐词。是否需要额外计算：是（要按 ONION 的方法计算词级显著性）。论文未说明 ONION 在本文设置下的阈值或实现细节。
- **模型行为指标**。是什么：攻击成功率（attack success rate, ASR）与干净准确率（clean accuracy, CA），二者在有毒化测试集与原始测试集上分别计算；Table 4 还给出有防御与无防御下的 ∆ASR 与 ∆CA。在哪里采集：评估时，在聚合后的全局模型（本文即集中式训练得到的模型）上。粒度：逐模型、逐数据集。是否需要跨轮历史：否。
- **毒化样本的自动质量指标与人工判定**。是什么：用 GPT-2 计算困惑度（perplexity, PPL）与用 LanguageTool 计算语法错误数（grammatical error numbers, GE），以及标注者判断样本是否被机器扭曲的类别 F1。Table 5 给出 RIPPLES 的 PPL 441.2、GE 4.56、Poisoned F1 85.37，InsertSent 的 171.9、3.89、83.33，StyleBkd 的 161.8、2.51、15.09。在哪里采集：客户端训练前（对样本本身做质量评估）。粒度：逐样本，汇总为逐攻击方法。是否需要额外计算：是（PPL 需要跑一个 GPT-2 语言模型）。
- **对抗攻击的查询痕迹**。是什么：同一个测试样本在多种风格下的多次改写查询（每实例上限 50 次，§4.1）。在哪里采集：评估时（模型推理接口的调用日志）。粒度：逐样本。这一项属于分析层面的延伸：论文只报告了查询预算，没有把查询日志当作检测信号使用。
- **论文声称能绕过的检测**。第一，ONION 这类词级测试时防御：StyleBkd 在部署 ONION 后平均 ∆ASR 仅 -0.83，而基于插入的基线 RIPPLES 与 InsertSent 平均 ∆ASR 分别为 -66.92 与 -45.49（§5.2）。第二，人工数据审查：StyleBkd 的 Poisoned F1 低至 15.09，论文称标注者很难把它的毒化样本与正常样本区分开（§5.3）。第三，自动质量检查：StyleBkd 的 PPL 161.8 与 GE 2.51 在三种攻击中最好（Table 5）。论文还说明其一般性理由：“most backdoor defenses are based on data inspection. Thus, resistance to defenses of backdoor attacks is dependent on their invisibility, namely the indistinguishability of poisoned samples from normal ones.”（§5.1）。

## 6. 干预动作

- 论文没有提出、也没有实现任何检测或防御组件，因此没有“检测后做什么”的动作序列。论文在正文中只把 ONION 当作被评测的外部防御：ONION 的动作是在测试样本上检测并剔除可疑词，以避免激活后门（§5.1），其结果是基于插入的基线 ASR 大幅下降、StyleBkd 几乎不受影响（Table 4）。
- 论文在结论与未来工作中提出了两个尚未实现的防御设想（§7 Conclusion and Future Work）：一是对训练数据做风格迁移增广以提升受害模型的鲁棒性；二是先把测试样本做风格迁移再送入受害模型，以破坏对抗样本或可能的后门触发，但论文同时提醒要谨慎考虑这对正常样本的副作用。论文没有报告这两个设想的任何实验。
- 论文也未给出回滚、重加权、裁剪、加噪、剔除客户端等干预的任何设计或实验。因此在防护库的干预接口分类中，这篇论文对应“无干预”。

## 7. 实验设置与主要结果

- **受害模型与数据集**：BERT、ALBERT、DistilBERT 三个模型，SST-2、HS、AG's News 三个数据集，无防御干净准确率见 Table 1（例如 SST-2 上 BERT 91.71、ALBERT 88.08、DistilBERT 90.06）。
- **对抗攻击基线**：GAN（Zhao et al., 2018）与 SCPN（Iyyer et al., 2018）。GAN 因为无法在 HS 与 AG's News 上训练出可用的生成对抗自编码器，只在 SST-2 上评测（§4.1）。
- **训练超参数**：Adam 优化器，初始学习率 2e-5 并线性衰减，训练 3 个 epoch（§5.1 Implementation Details）。StyleAdv 没有需要调的超参数（§4.1）。所有攻击方法每个实例最多查询受害模型 50 次（§4.1）。
- **客户端数与参与率、轮次、非独立同分布（non-IID）**：论文未涉及，因为实验是集中式训练，不是联邦学习。
- **对抗攻击结果（Table 2）**：SST-2 上 StyleAdv 对 BERT/ALBERT/DistilBERT 的 ASR 分别为 91.47、95.51、96.21，PPL 分别为 228.7、191.9、180.7，GE 分别为 1.15、1.16、1.13；同数据集上 SCPN 的 ASR 为 52.84、59.98、64.73，GAN 为 26.42、39.40、47.53。HS 上 StyleAdv 的 ASR 为 51.25、59.03、31.00；AG's News 上为 58.36、80.70、89.54。论文的结论是 StyleAdv 在所有评测指标上一致优于基线，并且在 SST-2 上对所有模型都超过 90%（§4.2）。
- **对抗攻击有效性人工评测（§4.3）**：仅在 SST-2 上进行，每种方法随机抽 200 个对抗样本，三名标注者独立二分类投票。有效比例（即标签未被改变的比例）为 GAN 3%、SCPN 43%、StyleAdv 49.5%。
- **后门攻击结果（Table 4）**：无防御时三种攻击的 ASR 全部超过 90 甚至接近 100，同时 CA 保持良好。StyleBkd 的 ASR 低于两个插入式基线（SST-2 上 BERT 94.70、ALBERT 97.79、DistilBERT 94.04；HS 上 90.67、94.02、90.22；AG's News 上 97.64、95.16、97.96）。部署 ONION 后，RIPPLES 与 InsertSent 的 ASR 大幅下降（例如 SST-2 上 BERT 分别从 100 降到 24.56 与 30.92），StyleBkd 基本不受影响（SST-2 上 BERT 94.70 变为 94.59，∆ASR -0.11）。论文给出的平均 ∆ASR 为 RIPPLES -66.92、InsertSent -45.49、StyleBkd -0.83（§5.2）。
- **人工数据审查与自动质量评测（Table 5，§5.3）**：StyleBkd 的 Poisoned F1 最低，为 15.09，Normal F1 为 87.03，macro F1 为 51.06；RIPPLES 的对应值为 85.37、96.23、90.80，InsertSent 为 83.33、95.57、89.45。StyleBkd 的 PPL 161.8 与 GE 2.51 也最优。
- **触发风格的影响（Table 6，§5.4）**：在 BERT 与 SST-2 上，Bible 的 PCA 最高（94.69），ASR 也最高（94.70）；Tweets 的 PCA 最低（78.43），ASR 最低（72.30）；Poetry、Shakespeare、Lyrics 的 PCA 分别为 93.09、92.64、92.59，ASR 分别为 91.61、91.94、91.49。论文据此认为触发风格选择策略有效。
- **对抗样本示例（Table 3，§4.4）**：一个被模型判为 Positive 的影评原句，在改成 Tweets 风格后被判为 Negative，从而成为对抗样本；论文称该样本保留了原句语义且相当流畅。
- **一个抽取歧义**：评测指标段落中出现“ASR, NatScore and Valid are ‘higher-better’ while PPL and GE are ‘lower-better’”（§4.1），但抽取文本没有给出 NatScore 的定义，论文未说明其计算方式。

## 8. 开销

- 论文未报告计算、通信或存储开销的量化数据，没有给出训练时间、显存、参数量对比、生成毒化样本的耗时，也没有通信量或存储量的测量。
- 论文报告的相关资源约束只有：所有攻击方法对每个实例最多查询受害模型 50 次（§4.1）；后门训练用 Adam、初始学习率 2e-5 线性衰减、训练 3 个 epoch（§5.1）；对抗攻击与后门攻击都要求额外运行 STRAP 风格迁移模型，后门攻击在选择触发风格时还要为每种风格训练一个探测分类器（§3.3），这些额外开销的量级论文未报告。
- 论文在 Ethical Considerations 中笼统声称“the energy we consume for running the experiments is limited”，并说明使用 base 版本而非 large 版本模型以节省能耗，但没有给出任何能耗测量。

## 9. 假设、局限与自适应攻击

**论文所依赖的假设（论文有依据的部分）**

- 文本风格是与任务无关的特征，因此改写风格可以保留任务相关标签（Introduction、§3.1）。
- STRAP 在改写风格时不会改变情感等可能与任务相关的属性（§3.1）。
- 触发风格必须能被受害模型区分出来，论文用探测分类任务来代理这一条件，并选 PCA 最高的风格（§3.3、§5.4）。
- 攻击者能够修改训练数据与训练损失（引入 La）；论文没有讨论攻击者只控制数据、不控制训练代码时该方法是否仍成立。
- 防御主要基于数据审查，因此毒化样本越难与正常样本区分，攻击的抵抗力越强（§5.1）。
- 所有实验都在集中式、全参数微调、base 规模模型、三种英文分类任务上进行。

**论文自述的局限**

- 在 HS 上表现明显较差。对抗攻击方面，作者猜测 HS 中有大量特殊辱骂词作为主导分类特征，难以被风格或句法改写替换，并指出这可能是风格迁移类（乃至所有复述类）攻击的潜在缺点，留待未来工作（§4.2）。后门攻击方面，论文承认 StyleBkd 在无防御时 ASR 低于两个插入式基线，因为风格是比内容插入抽象得多的特征，更难被模型记住（§5.2）。
- 对抗攻击的有效性（attack validity）整体偏低，StyleAdv 只有 49.5%，论文称有效性问题是一个尚未解决的普遍难题（§4.3）。
- 作者认为现有自然语言处理模型对文本风格这一特征的学习与应对能力不足（Conclusion）。
- 论文没有实现任何防御，只提出两个设想并提醒要注意副作用（§7）。

**自适应攻击者评估**

- 论文未评估自适应攻击者（adaptive attacker）。它评估的是固定防御 ONION 下的攻击效果，没有评估“防御方知道 StyleBkd 并针对性设计检测”时的情形，也没有让攻击者针对 ONION 调整策略。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：以下均为我的推断，论文没有讨论联邦、LoRA 或大模型）**

- 分析：论文假设攻击者能改动训练损失（L = Lt + La）。在联邦 LoRA 微调中，恶意客户端只能改自己本地的训练目标，这个假设在客户端内部仍然成立，但 La 带来的表示层偏置能否在服务器参数平均与低秩约束下保留下来，论文未说明。
- 分析：论文的触发风格选择需要为每种风格训练一个探测分类器来衡量受害模型的辨识能力。在联邦场景中全局模型逐轮变化，探测结果是否能跨轮迁移，论文未说明。
- 分析：论文的防御讨论完全建立在“能看到原始文本”的前提上（人工审查、ONION 的词级检查）。联邦学习中服务器默认看不到客户端原始数据，这套以文本为中心的可观测量在标准联邦协议下不可直接获得，必须依赖客户端侧钩子上报或允许服务器访问样本。
- 分析：论文的受害模型是全参数微调的 base 规模语言模型，本方法的触发是全局文本风格。在大模型 LoRA 微调下，低秩更新可能只学到较窄的子空间，风格触发是否仍能被稳定写入全局适配器，论文未说明。
- 分析：论文实验为独立同分布的中心化数据划分。联邦场景通常是非独立同分布的，恶意客户端本地的风格样本分布、以及正常客户端对风格特征的“稀释”程度都会变化，论文未说明。
- 分析：论文评测的防御 ONION 是词级过滤，风格触发不含稀有词，因此过滤无效，这个结论对 LoRA 场景可能仍然成立；但论文没有检验“风格分类器式检测”这一路线，而这恰是迁移到联邦时更可能可行的路线。

## 10. 对防护库设计的含义

- 分析：要检测或复现这篇论文的后门攻击，库必须在“客户端训练前（client_pre_train）”这一信任边界上提供逐样本的（原始文本，标签）快照，并且要能记录同一语义内容在改写前后的标签变化。这是通用需求，不只是本文特有：任何数据层投毒检测插件都依赖这一视图。
- 分析：库需要提供可注册的干净参考集（clean reference set）接口。本文的触发风格选择与人工数据审查都以“正常样本”为对照（探测分类器的一半数据、160 个正常样本），没有干净参考就无法计算“风格是否异常”这类偏离度指标。这一条对本文的检测式插件是特有的，但干净参考集本身是通用设施。
- 分析：库需要暴露“客户端训练损失组成”这一钩子。本文攻击在客户端侧改动损失（加入辅助分类损失 La），其最具区分度的内部可观测量就是受害模型表示层上的“是否毒化”二分类信号；要检测这类改动，插件必须能在客户端每一步拿到逐样本的表示层输出，并允许挂载一个辅助判别头。这是本文特有、明显偏离常规联邦适配器聚合视图的需求。
- 分析：库的服务器钩子（服务器收到更新时、服务器聚合时、聚合后全局模型）在这篇论文里没有对应的检测价值，因为论文的全部信号都在文本层与客户端训练过程层。这意味着防护库不应把“逐层适配器范数、客户端更新相似度”当成唯一默认视图，否则本文这类攻击完全不可见。
- 分析：库需要提供“测试时输入改写或过滤”的干预接口，而不仅是“剔除客户端、重加权、裁剪、加噪、回滚”这类参数层干预。本文提到的两个防御设想（对训练数据做风格迁移增广、对测试样本做风格迁移以破坏触发）都发生在样本层，其中测试时改写属于评估部署位置的动作。
- 分析：库需要能记录推理接口的调用日志（同一输入的多次近义改写与查询次数），因为对抗攻击 StyleAdv 的可见痕迹是“同一测试样本在多种风格下被反复查询，上限 50 次”。这一采集点与投毒检测无关，是面向推理期攻击的通用采集点；本文没有把它用于检测，属于库可以补齐的能力。

## 11. 原文依据

1. Introduction（第 2 页）：“For backdoor attacks, we transform some training samples into a selected trigger style, and feed the transformed samples into the victim model during training to inject a backdoor.” —— 支撑第 3 节“后门攻击入口在本地数据准备（训练数据投毒）”。
2. §3.3 Trigger Style Selection：“we design the following trigger style selection strategy based on a probing classification task: (1) sample some normal training samples and use STRAP to transform these samples into every text style, respectively” —— 支撑第 4 节触发风格选择步骤，以及第 5 节“PCA 需要干净参考数据与额外训练”。
3. §3.3 Poisoned Sample Generation：“After determining the trigger style, we randomly select a portion of normal training samples (x, y), transform their inputs x into the trigger style using STRAP and replace their labels y with the target label y*.” —— 支撑第 3 节与第 4 节中毒化样本的具体构造方式。
4. §3.3 Victim Model Training：“Specifically, similar to the probing classification task in Trigger Style Selection, we ask the victim model to determine whether each training sample is poisoned or not by an external binary classifier connected to the victim model’s representation layer.” —— 支撑第 3 节“攻击入口二：本地训练过程的损失改动”，以及第 5 节“表示层可观测量”。
5. §3.2：“first utilize STRAP to generate multiple paraphrases of xt in different styles, then query the victim model Fθ with the generated paraphrases one by one” —— 支撑第 3 节“对抗攻击入口在推理输入生成”。
6. §5.1 Evaluation Settings：“In addition to ONION, most backdoor defenses are based on data inspection. Thus, resistance to defenses of backdoor attacks is dependent on their invisibility, namely the indistinguishability of poisoned samples from normal ones.” —— 支撑第 5 节“论文声称能绕过基于数据审查的检测”与第 9 节的假设。
7. §5.2 Backdoor Attack Results：“When a backdoor defense is deployed, the ASRs of the two insertion-based baseline attacks drop substantially (the average ∆ASRs for RIPPLES and InsertSent are -66.92 and -45.49), but StyleBkd is affected hardly (the average ∆ASR is -0.83)” —— 支撑第 7 节关键结果与第 5 节“绕过 ONION”。
8. §5.3 Manual Data Inspection：“we randomly sample 40 trigger-embedded poisoned samples and 160 normal samples. Then we ask annotators to make a binary classification on whether each sample is original human-written or distorted by machine.” —— 支撑第 5 节与第 7 节人工审查协议的样本量与判定方式。
9. §7 Conclusion and Future Work：“we can augment training data by conducting style transfer on them, aiming to improve the robustness of the victim. Another simple possible idea is to conduct style transfer on the test samples before feeding them into the victim model” —— 支撑第 6 节“论文只提出未实现的防御设想，干预动作为无”。
10. §5.1 Implementation Details：“We tune the poisoning rate (the proportion of poisoned samples in the backdoor training set) for each attack method on the validation sets, aiming to make ASR as high as possible and the decrements of CA less than 3%.” —— 支撑第 2 节“论文未给出具体毒化率，只在验证集上调优”。

```json
{
  "key": "qi2021stylebkd",
  "title": "Mind the Style of Text! Adversarial and Backdoor Attacks Based on Text Style Transfer",
  "year": 2021,
  "paper_type": "attack",
  "setting": "centralized_llm",
  "uses_lora_or_peft": false,
  "adversary": ["data_provider", "external"],
  "attack_goal": ["untargeted", "backdoor"],
  "attack_entry": ["local_data", "local_training", "evaluation_deployment"],
  "observables": [
    {"what": "被改写为触发风格且标签被替换为目标标签的毒化训练样本（表 8 给出 Bible 风格示例）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "受害模型表示层上外接二分类器对“样本是否被毒化”的判别信号（论文用它构造辅助损失 La）", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "各候选触发风格的探测分类准确率（表 6 的 PCA，Bible 94.69 等）", "where": "client_pre_train", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "测试样本中可能与后门触发相关的可疑词（ONION 的检测对象）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "模型行为指标：毒化测试集上的攻击成功率 ASR 与原始测试集上的干净准确率 CA（表 4）", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "毒化样本的自动质量指标 PPL 与 GE，以及人工审查的类别 F1（表 5）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "同一测试样本在多种风格下被反复查询的推理调用记录（每实例上限 50 次）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "文本风格是与任务无关的特征，风格改写可以保留任务相关标签",
    "STRAP 风格迁移不会改变情感等可能与任务相关的属性",
    "触发风格能被受害模型区分，用探测分类准确率最高的风格作为触发",
    "攻击者能够修改训练数据并改动训练损失（引入辅助分类损失 La）",
    "防御主要基于数据审查，毒化样本越难与正常样本区分则攻击抵抗力越强",
    "实验全部在集中式、全参数微调、base 规模预训练语言模型与三个英文分类任务上完成"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Introduction", "supports": "第 3 节：后门攻击的入口是训练数据投毒", "text": "For backdoor attacks, we transform some training samples into a selected trigger style, and feed the transformed samples into the victim model during training to inject a backdoor."},
    {"section": "3.3 Trigger Style Selection", "supports": "第 4 节触发风格选择步骤与第 5 节对干净参考数据和额外计算的需求", "text": "we design the following trigger style selection strategy based on a probing classification task: (1) sample some normal training samples and use STRAP to transform these samples into every text style, respectively"},
    {"section": "3.3 Poisoned Sample Generation", "supports": "第 3 节与第 4 节：毒化样本的构造方式", "text": "After determining the trigger style, we randomly select a portion of normal training samples (x, y), transform their inputs x into the trigger style using STRAP and replace their labels y with the target label y*."},
    {"section": "3.3 Victim Model Training", "supports": "第 3 节攻击入口二（训练损失改动）与第 5 节表示层可观测量", "text": "Specifically, similar to the probing classification task in Trigger Style Selection, we ask the victim model to determine whether each training sample is poisoned or not by an external binary classifier connected to the victim model’s representation layer."},
    {"section": "3.2 Style Transfer-based Adversarial Attacks", "supports": "第 3 节：对抗攻击入口在推理输入生成", "text": "first utilize STRAP to generate multiple paraphrases of xt in different styles, then query the victim model Fθ with the generated paraphrases one by one"},
    {"section": "5.1 Evaluation Settings", "supports": "第 5 节与第 9 节：论文关于数据审查类防御与不可见性的假设", "text": "In addition to ONION, most backdoor defenses are based on data inspection. Thus, resistance to defenses of backdoor attacks is dependent on their invisibility, namely the indistinguishability of poisoned samples from normal ones."},
    {"section": "5.2 Backdoor Attack Results", "supports": "第 7 节关键结果与第 5 节：StyleBkd 对 ONION 几乎免疫", "text": "When a backdoor defense is deployed, the ASRs of the two insertion-based baseline attacks drop substantially (the average ∆ASRs for RIPPLES and InsertSent are -66.92 and -45.49), but StyleBkd is affected hardly (the average ∆ASR is -0.83)"},
    {"section": "5.3 Manual Data Inspection", "supports": "第 5 节与第 7 节：人工审查协议的样本量与判定方式", "text": "we randomly sample 40 trigger-embedded poisoned samples and 160 normal samples. Then we ask annotators to make a binary classification on whether each sample is original human-written or distorted by machine."},
    {"section": "7 Conclusion and Future Work", "supports": "第 6 节：论文没有实现防御，只提出未实现的设想", "text": "we can augment training data by conducting style transfer on them, aiming to improve the robustness of the victim. Another simple possible idea is to conduct style transfer on the test samples before feeding them into the victim model"},
    {"section": "5.1 Implementation Details", "supports": "第 2 节：论文未给出具体毒化率，只在验证集上调优", "text": "We tune the poisoning rate (the proportion of poisoned samples in the backdoor training set) for each attack method on the validation sets, aiming to make ASR as high as possible and the decrements of CA less than 3%."}
  ]
}
```
