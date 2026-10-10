# huang2024harmful：Harmful Fine-tuning Attacks and Defenses for Large Language Models: A Survey

## 1. 基本信息

- **论文标题**：Harmful Fine-tuning Attacks and Defenses for Large Language Models: A Survey。
- **作者与机构**：Tiansheng Huang、Sihao Hu、Fatih Ilhan、Selim Furkan Tekin、Ling Liu，佐治亚理工学院计算机科学学院（School of Computer Science, Georgia Institute of Technology, USA）。
- **年份说明**：arXiv 编号为 2409.18169（对应 2024 年 9 月投稿），但本抽取版本首页标注 "arXiv:2409.18169v6 [cs.CR] 23 Apr 2026"。JSON 中的年份字段填 2024。
- **场景**：集中式大模型训练，更准确地说是"微调即服务"（fine-tuning-as-a-service，论文自身缩写为 FaaS）。**不是联邦大模型微调**：论文的核心流水线是"服务提供方用用户上传的数据微调自己部署的模型"（Section 2.1、Figure 3）。联邦学习在全文只出现两处：Figure 8 的分类图中列出 "Federated learning [134, 258]"，以及 Section 3.2 末尾一句 "[134, 258] studies the extension of harmful fine-tuning attack in the federated learning context."。论文没有给出联邦场景的威胁模型、聚合规则、参与率或任何联邦实验。
- **训练阶段**：论文把标准流水线划分为两个阶段（Figure 3），即对齐阶段（alignment stage）与用户微调阶段（user fine-tuning stage）；防御分类进一步覆盖预训练阶段（pre-training stage）、对齐阶段、微调阶段（fine-tuning stage）、微调后阶段（post-fine-tuning stage）（Section 3.3）。
- **论文类型**：综述（survey）。
- **模型与数据规模**：论文自己的统计实验（Section 2.3）以 Llama2-7B 的未对齐版本为基座，用 BeaverTails 做安全对齐（1000 条数据、50 个 epoch、AdamW、学习率 1e-3、权重衰减 0.1），再在 SST2 混合 BeaverTails 有害数据上微调（1000 条数据、20 个 epoch、学习率 1e-5），两个阶段都用 LoRA；有害比例记为 p，Figure 7 的实验取 p = 0.1。Appendix C 用 GSM8K 做了同样的统计复现（Figure 11）。Section 4.3 列出文献中常用的基座模型为 Llama2-7B、Llama3-8B、Qwen2、Gemma2、OPT、Vicuna 等。Table 1 提到最早一批攻击中"100 malicious examples can subvert alignment"（Shadow Alignment）。

## 2. 威胁模型

**攻击者是谁**：根据 Section 2.2，攻击者是**用户**，也就是把微调数据上传给服务提供方的一方，在数据供应链意义上对应数据提供方。论文区分两类动机：一是"对手场景"（adversary scenario），用户故意上传有害数据以构陷服务提供方；二是"非对手场景"（non-adversary scenario），用户无意中把有害内容混进微调集。论文核心威胁模型里只有"一个用户/一份用户数据集"，不存在多客户端集合。

**占比或数量**：用户数据集中比例为 p 的样本是有害数据，比例为 1-p 的样本是正常微调数据，且假定 p ≥ 0；当 p = 0 时威胁模型退化为良性微调（Section 2.2）。

**能力（能改什么）**：用户"can operate the data uploaded to the service provider, but have no control over the fine-tuning process as well as the hyper-parameter selection."（Section 2.2）。也就是说攻击者只能改上传的数据，不能改损失函数、优化器、学习率、训练步数、聚合方式或部署流程。Appendix D 另外讨论了三种扩展场景（开源模型下用户为攻击者、开源模型下发布方为攻击者、带后门的 LLM 服务下发布方为攻击者），并用 Table 8 对比了各场景中攻击方与防御方在对齐、微调、部署、推理四个环节的控制权。

**知识（知道什么）**：论文未说明攻击者需要知道哪些具体信息；只说明防御方在构造防御时使用的有害数据必须与攻击者使用的有害数据是不同实例（Section 2.2），隐含攻击数据对防御方不可见。

**目标**：破坏模型已有的安全对齐（safety alignment），使模型对有害提问给出有害回答或有害行为，属于越狱或安全对齐破坏类目标。Section 2.2 原文："For intentional attackers, they intentionally upload harmful data to the service provider and they aim to compromise the safety alignment and elicit harmful answers/behaviors of the fine-tuned model."

**防御者是谁、能看到什么、信任什么**：防御者是服务提供方。它"can fully control the fine-tuning algorithms and fine-tuning hyperparameters"，并且"can perform filtration/modification on the user uploaded dataset"（Section 2.2）。它被假定持有两类参考数据：对齐数据集（有害问题与安全回答的配对）和有害数据集（有害问题与有害回答的配对），且后者必须与攻击所用有害数据是不同实例（Section 2.2）。Appendix A 的 Q5 进一步总结文献中的三类数据集假设：安全对齐数据集、同分布有害数据集（in-distribution harmful dataset）、代理数据集（proxy dataset，安全的一般问题与安全回答配对）。

**防御目标**：Section 2.2 给出两个条件，即抵抗性（resistance，微调充分步数后模型仍保持低有害度）与稳定性（stability，有防御与无防御时用户下游任务性能相同或相近）。

## 3. 攻击入口与流程位置

- **入口位置**：本地数据准备，具体是"用户上传给服务提供方的微调数据集"这一位置。Section 2.2 明确写"The attack surface of harmful fine-tuning attack is within the fine-tuning stage"，同时明确攻击者不控制微调过程与超参数选择，因此攻击实际是通过数据内容进入流水线的，而不是通过损失函数、优化器、更新后处理、服务器聚合、全局模型下发或评估部署进入。本地训练过程、更新上传前的后处理、服务器聚合、全局模型下发、评估与部署这几个位置，论文都没有把攻击放在那里。
- **具体操作步骤**（Section 2.1、Section 2.2、Figure 2、Figure 3）：第一步，用户在本地构造用户数据集，其中 p 比例的样本是有害数据、1-p 比例的样本是正常微调数据；第二步，用户把该数据集上传给服务提供方；第三步，服务提供方用这份数据在其已经安全对齐的基座模型上做微调（可用监督微调 SFT 或基于人类反馈的强化学习 RLHF）；第四步，微调后的模型丢失或弱化安全对齐，被部署后对有害提问给出有害回答，而有害回答由服务提供方的接口发出，因此服务提供方面临责任风险。
- **攻击变体及其额外步骤**（Section 3.2）：隐写类攻击（Covert Malicious Finetuning）分两个阶段，第一阶段用纯良性的示范数据教会模型理解编码并回答编码后的答案，第二阶段把有害数据编码后上传，测试时用编码后的有害问题触发编码后的有害回答；数据增强或后缀添加类攻击直接对有害数据做逐 token 优化（Virus）、前后缀包装与词替换（three-pronged）或加越狱后缀（Jailbreak-tune）；良性数据攻击不做有害内容注入，而是从良性数据中采样更有攻击性的子集（Bi-directional Anchoring 优先选梯度与表示空间上接近有害样本的良性样本；Self-Inf-N 用自影响函数找离群良性样本），或改写良性样本的答案结构（NOICE 的"先拒绝再服从"模式、两阶段过拟合攻击、TokenSuffix 在良性问题后加优化后缀）。
- **论文声称哪些防御会被这些攻击绕过**：主流服务提供方部署的护栏审核（guardrail moderation，例如 LlamaGuard、IBMGuard / Granite Guardian）会被上述攻击绕过；纯良性数据攻击天然不触发审核；隐写攻击第一阶段的示范数据是纯良性、第二阶段有害数据被编码，因此无法被常规审核标记；后续工作 Flower 进一步降低编码数据的困惑度以规避检测；three-pronged 通过变换有害数据绕过审核。

## 4. 方法原理

本文是综述，因此"方法原理"包含两部分：论文自己给出的问题形式化与统计机理，以及它归纳的防御范式。

- **问题形式化与统计机理（Section 2.3）**。论文用两个指标刻画问题：有害分数（harmful score，越小越好）与微调精度（fine-tune accuracy，越大越好）。它用 Llama2-7B 加 BeaverTails 对齐加 SST2 混合有害数据做受控实验，报告三条统计规律。第一，有害分数随混入的有害比例上升而显著上升，而对齐模型只比未对齐模型"略微抵抗"，比例足够高时抵抗仍然被打破。第二，微调精度不因混入有害数据而严重下降，这使攻击更隐蔽。第三，对齐损失（alignment loss，在对齐数据集上的损失）随有害比例上升而上升，同时有害数据上的训练损失与未见有害数据上的测试损失随微调步数下降，前者对应"遗忘"对齐知识，后者对应"复活"有害知识。论文还度量了隐藏嵌入漂移（hidden embedding drift），定义为对齐模型（未对齐情形下为预训练模型）与微调模型在同一对齐数据集上隐藏嵌入之间的欧氏距离，隐藏嵌入取每个注意力层的输出，并观察到漂移随有害比例上升而增大（Figure 5）。
- **防御的五类优化形式（Section 3.3，公式 1 至 5）**。Vaccine（公式 1）在对齐数据集的损失上做内层最大化、外层最小化，即在隐藏嵌入上加入使对齐损失最大的扰动并在该扰动下训练，从而让模型对后续微调阶段的扰动稳健。RepNoise（公式 2）最小化对齐数据损失、最大化有害数据损失，并加入一个表示损失把有害数据的隐藏嵌入扰动到随机高斯噪声。TAR（公式 3）是元学习方法，在代理数据集上最小化表示损失，同时优化模型使其在沿有害梯度走一步（或若干步）之后有害损失被最大化。Booster（公式 4）去掉表示损失，改为最小化"一步有害微调后有害损失的下降量"。CTRAP（公式 5）在对齐阶段沿有害梯度方向嵌入"坍缩陷阱"（collapse trap），一旦模型沿有害梯度下降，其一般推理能力就输出乱码而自行崩溃。
- **防御的时间分类（Section 3.3）**。预训练阶段防御过滤预训练语料；对齐阶段防御包括上述优化类方法、坍缩陷阱类方法（CTRAP、SEAM、SDD）、数据策展类方法（CTRL）、稀疏化方法（RSN-Tune）；微调阶段防御分为四类，即距离正则化（LDIFS、Constrain-SFT、Freeze、ML-LR、Freeze+、SaLoRA）、对齐数据混合（SafeInstr、VLGuard、Lisa、Paraphrase）、提示工程（BEA、PTST）、审核或检测过滤（审核模型、SAFT、Seal、BDS）；微调后阶段防御的思路是对微调后的模型加扰动或做投影、稀疏化、模型融合与注意力头插值来修复（Security Vector、Resta、LAT、SOMF、Safe LoRA、SafeMerge、Antidote、SafetyLock、CMRM、IRR）。
- **可解释性结论（Section 3.5、Section 5.3）**。论文引用的机理研究提出"安全盆地"（safety basin）概念，认为有害微调的本质是把对齐模型的权重拖出安全盆地；不同攻击扰动不同深度的层（显式有害攻击扰动浅层，身份转换攻击扰动更深的层）；对齐数据集与下游微调数据集相似度越高，防护越脆弱。

## 5. 检测或防御所需的数据

以下逐项列出论文中检测或防御方法需要的输入。需要预先说明：论文的场景是集中式，所有计算都在服务提供方一侧完成，因此我给出的"在哪里采集"是把它映射到防护库的阶段枚举上；这一映射本身是分析。

1. **用户上传的微调数据集（逐样本）**
   - 是什么：用户上传的微调数据，p 比例有害、1-p 比例正常（Section 2.2）；样本形态是有害问题与回答的配对，或良性下游任务的问题与答案配对（Section 4.1）。
   - 在哪里采集：服务器收到更新时，也就是服务提供方收到用户数据集、尚未开始微调时。
   - 粒度：逐样本。
   - 跨轮历史：不需要。干净参考数据：不需要。额外前向或反向计算：需要，最朴素的防御要用审核模型（moderation model）对数据做分类（Section 3.3）。其他客户端的数据：论文未说明，核心场景只有一个用户。
2. **微调样本的嵌入表示与嵌入空间的奇异向量**
   - 是什么：SAFT 通过分解嵌入空间并比较奇异向量来更有效地检测有害数据，其思路源自谱特征（spectral signature）方法（Section 3.3）。
   - 在哪里采集：服务器收到更新时，即过滤阶段。
   - 粒度：逐样本，聚合到子空间层级。
   - 跨轮历史：论文未说明。干净参考数据：论文未说明。额外计算：需要额外的模型前向以取得嵌入。
3. **对齐数据集（有害问题与安全回答配对）上的对齐损失**
   - 是什么：在对齐数据集上重新计算的损失，论文用它衡量对齐知识的遗忘程度（Section 2.3、Figure 5）；Vaccine、Booster、CTRAP、Lisa、Constrain-SFT 都在训练目标里使用对齐数据损失（Section 3.3，公式 1、4、5）。
   - 在哪里采集：对齐阶段训练时，以及在微调后重新计算用于评估（论文的统计实验是在微调结束后计算的）。
   - 粒度：逐样本损失聚合为数据集级损失。
   - 跨轮历史：需要，要和对齐阶段的数值比较。干净参考数据：需要，即对齐数据集本身。额外前向计算：需要。
4. **对齐数据在每一注意力层上的隐藏嵌入漂移**
   - 是什么：对齐模型与微调模型在同一对齐数据集上隐藏嵌入之间的欧氏距离，隐藏嵌入取每个注意力层的输出（Section 2.3、Figure 5）。
   - 在哪里采集：微调结束后。
   - 粒度：逐层，再聚合。
   - 跨轮历史：需要，必须持有对齐阶段模型的嵌入作为基准。干净参考数据：需要。额外前向计算：需要。
5. **同分布有害数据集（有害问题与有害回答配对）上的损失与梯度**
   - 是什么：RepNoise、TAR、Booster、CTRAP 使用的有害数据损失与表示损失（Section 3.3，公式 2 至 5）。论文强调该数据集中的实例必须与攻击所用有害数据不同（Section 2.2）。
   - 在哪里采集：对齐阶段或微调阶段的训练过程中计算。
   - 粒度：逐样本或逐批，聚合为数据集级损失；TAR、Booster、CTRAP 还需要对模型参数求梯度。
   - 跨轮历史：不需要跨轮，但 TAR、Booster、CTRAP 需要在同一步内做一步或多步内层更新的展开。干净参考数据：需要，即该有害数据集本身。额外反向计算：需要。
6. **代理数据集（安全的一般问题与安全回答配对）上的表示损失**
   - 是什么：TAR 使用的表示学习损失，用来防止模型在最大化有害损失时崩溃（Section 3.3，公式 3）；Appendix A 的 Q5 把它列为第三类数据集假设。
   - 在哪里采集：对齐阶段训练时。
   - 粒度：逐样本或逐批。
   - 跨轮历史：不需要。干净参考数据：需要。额外前向与反向计算：需要。
7. **微调过程中有害数据上的训练损失，以及未见有害数据上的测试损失**
   - 是什么：Figure 7 的中图与右图所追踪的两个量；有害测试损失使用的是模型在微调阶段从未见过的有害数据（Section 2.3）。
   - 在哪里采集：微调过程的每一步；在联邦场景对应客户端每一步。
   - 粒度：逐批。
   - 跨轮历史：不需要。干净参考数据：需要一份留出的有害测试数据。额外前向计算：需要。
8. **微调前后模型参数的差（安全向量、增量更新、逐层坐标）**
   - 是什么：Resta 用对齐模型权重减去未对齐模型权重得到安全向量；Safe LoRA 用对齐版本与未对齐版本模型的权重差构造安全子空间，再把有害梯度更新投影到安全子空间；SafeMerge 在安全关键层选择性地合并用户更新与安全更新；Antidote 识别有害坐标并稀疏化为 0；IRR 识别并抹除不安全的增量更新（Section 3.3）。
   - 在哪里采集：微调结束后；在联邦场景对应服务器聚合后。
   - 粒度：逐层或逐参数。
   - 跨轮历史：需要，必须有对齐阶段（或未对齐版本）的模型权重。干净参考数据：需要。额外计算：主要是权重运算，论文未说明需要额外前向或反向计算。
9. **每个数据点的安全属性后验与学习权重**
   - 是什么：BDS 用贝叶斯推断学习每个数据点安全属性的后验分布，并据此给不同数据点分配不同学习权重（Section 3.3）。
   - 在哪里采集：服务器收到更新时，用于微调阶段的加权训练。
   - 粒度：逐样本。
   - 跨轮历史：论文未说明。干净参考数据：论文未说明，但其目标是安全属性，隐含需要安全相关参考。额外计算：需要。
10. **逐样本对安全损失的边际影响**
    - 是什么：Seal 建立双层优化问题，过滤掉那些会使微调后安全损失下降最严重的样本（Section 3.3）。论文未说明构造该双层问题具体需要哪些数据。
    - 在哪里采集：服务器收到更新时，用于微调前过滤。
    - 粒度：逐样本。跨轮历史、干净参考数据、额外计算：论文未说明。
11. **审核模型对模型回答的判定（评估用）**
    - 是什么：有害分数的实现方式之一，即用审核模型标记模型回答，并计算被标记为有害的回答比例（Section 4.2）。
    - 在哪里采集：评估时。
    - 粒度：逐样本回答，聚合为模型级分数。跨轮历史：不需要。干净参考数据：不需要。

**攻击侧的可观测量与规避声明**：攻击会留下的痕迹包括：上传数据集中逐样本的有害内容（若审核模型能识别）；隐写编码数据的高困惑度（论文在 Section 5.1 指出"the steganography fine-tuning data is still easy to detect because of its high perplexity"）；Virus 逐 token 优化后的异常 token 替换；良性攻击中与有害样本在梯度与表示空间上接近的离群良性样本（Bi-directional Anchoring）以及自影响函数识别的离群点（Self-Inf-N）；NOICE 的"先拒绝再服从"回答模式；TokenSuffix 的优化后缀。论文声称能被绕过的检测包括：护栏审核模型（Section 3.2 指出隐写与纯良性攻击无法被常规审核标记，three-pronged 与 Virus 专门为绕过审核而优化），以及推理阶段的审核（three-pronged 的第三个策略用于规避推理时审核）。论文还指出 Virus 的迁移性弱，其 Table 9 显示在 Granite Guardian 3.1 上优化的数据不能很好地迁移到 Llama Guard。

## 6. 干预动作

- **过滤样本**：最朴素的防御是用审核模型把有害数据从用户微调数据集中过滤掉（Section 3.3）；SAFT 在嵌入空间做奇异向量比较后过滤；Seal 用双层优化过滤使安全损失下降最严重的样本；针对隐写攻击还有 CIFR 一类的过滤工作（Table 4）。动作发生在服务器收到数据之后、微调开始之前。
- **重新加权**：BDS 为不同数据点分配不同学习权重，等价于在微调阶段对样本降权而不是硬删除（Section 3.3）。
- **加噪或加扰动**：Vaccine 与 T-Vaccine 在对齐阶段的隐藏嵌入上加扰动做扰动感知训练；RepNoise 把有害数据的隐藏嵌入扰动到随机高斯噪声，同时做梯度上升以最大化有害数据损失；LAT 与 Panacea 在微调后对嵌入加扰动以忘掉有害知识（Section 3.3）。
- **修复模型**：微调后阶段的动作包括用任务算术减去或加上安全向量（Resta、Security Vector）、把更新投影到安全子空间（Safe LoRA）、在安全关键层选择性合并（SafeMerge）、把有害坐标稀疏化为 0（Antidote）、抹除不安全增量更新（IRR）、在注意力头输出上插值安全向量（SafetyLock）、用模型融合保留安全参数（SOMF）、校准偏移表示（CMRM）。动作发生在微调结束之后。
- **修改训练过程**：微调阶段的距离正则化（KL 约束微调模型表示接近对齐模型、约束前几个 token 的表示、冻结安全层、给不同模块不同学习率、用固定安全模块把 LoRA 表示投影到正交子空间）、对齐数据混合（SafeInstr、VLGuard、Lisa、Paraphrase）、提示工程（BEA 用带后门触发的系统提示建立触发词与安全回答的联系，PTST 在推理时换用安全提示）。动作发生在客户端本地训练过程中。
- **论文明确指出不做的一种动作**：微调之后通常不再重新做安全对齐，原因有两个，一是对每个微调请求都在对齐数据集上重新对齐计算代价过高，二是微调后的安全对齐可能损害模型在用户下游任务上的表现，削弱定制价值（Section 2.1）。因此论文把"微调后修复"设计成轻量的模型后处理，而不是重新训练。

## 7. 实验设置与主要结果

- **论文自己的统计实验（Section 2.3）**：模型为 Llama2-7B 未对齐版本；对齐数据为 BeaverTails；下游任务为 SST2，与 BeaverTails 有害数据按比例 p 混合；对齐阶段 1000 条数据、50 个 epoch、AdamW、学习率 1e-3、权重衰减 0.1；微调阶段 1000 条数据、20 个 epoch、学习率 1e-5；两阶段均使用 LoRA；有害分数用 BeaverTails-moderation 判定。Figure 7 的实验固定 p = 0.1，并固定使用 BeaverTails-refusal 作为安全数据集。
- **客户端数与参与率**：论文未说明，因为实验是集中式单训练方，没有客户端、参与率、轮次或聚合的概念。
- **恶意比例**：p 是变量，Figure 4 扫描了不同有害比例，Figure 7 取 p = 0.1。
- **数据是否非独立同分布**：论文未说明。
- **指标**：有害分数与微调精度（Section 4.2）。有害分数的三种实现为：用审核模型标记回答并计算被标记比例（[95, 97, 98, 100, 196]）、用 GPT-4 按五点李克特量表打分（[85, 160, 189]）、用字符串匹配分类（[290]）。微调精度按任务不同而不同，例如 GSM8K 用正确答案比例，MT-Bench 与 AlpacaEval 用 GPT-4 平均分。
- **关键结果**：Figure 4 显示有害分数随有害比例显著上升，而对齐只带来"略微抵抗"，同时微调精度不因混入有害数据而严重下降；Figure 5 显示对齐损失与隐藏嵌入漂移随有害比例上升；Figure 6 用 T-SNE 显示高有害比例下 SFT 与 Vaccine 的嵌入都朝特定方向漂移，但 Vaccine 漂移更小；Figure 7 显示在纯有害数据上微调时有害分数随步数大幅上升，而纯 SST2 微调几乎不影响有害分数，同时有害训练损失与有害测试损失随步数下降；Table 3 报告所用审核模型的假阴性率为 7.71%、假阳性率为 3.64%；Appendix C 的 Figure 11 在 GSM8K 上大体一致，但良性 GSM8K 也会降低有害损失，论文解释为 GSM8K 与有害数据集同为问答形式因而更相似。
- **汇总表**：Table 1 汇总攻击（关键观察、有害数据集、微调方法、首次可用时间）；Table 2 汇总防御（类别、有害数据集、微调方法、基座模型类型）；Table 4 汇总各防御原文评估的攻击类型；Table 5、Table 6、Table 7 分别汇总对齐与有害数据集、良性微调数据集、评测基准。
- **论文对自己结论强度的限定**：Section 3.4 明确指出无法得出"哪类防御对哪类攻击更有效"的结论，原因是各防御的评测覆盖不全、攻击数据集各异，难以公平比较。

## 8. 开销

论文未报告系统的计算、通信与存储开销数值。论文中的定性表述有：Section 5.2 指出"Most existing defenses increase the memory/computation overhead compared to SFT (without defense)"；Lisa 指出对齐数据混合类方法需要按微调样本数放大对齐数据，因而带来线性增长的计算开销；T-Vaccine 指出 Vaccine 对每一层加均匀扰动是次优的，可能既损害防御效果又带来不必要的开销；Appendix A 的 Q3 给出资源需求排序为 RLHF 高于全参数 SFT、全参数 SFT 高于 LoRA SFT，并且 LoRA SFT 的训练时间显著更短。通信开销与存储开销：论文未报告。

## 9. 假设、局限与自适应攻击

**方法成立所依赖的假设（论文有依据的）**：

- 服务提供方完全控制对齐、微调与部署流程（Section 2.2）。
- 攻击者只能操作上传的数据，不能控制微调过程与超参数选择（Section 2.2）。
- 服务提供方持有对齐数据集（有害问题与安全回答配对）（Section 2.2）。
- 服务提供方持有有害数据集（有害问题与有害回答配对），且其中的实例必须与攻击所用有害数据不同，否则防御没有意义（Section 2.2）。
- 部分防御还需要代理数据集（安全的一般问题与安全回答配对），见 TAR 的表示损失与 Appendix A 的 Q5。
- 数据过滤类防御假设只有少量有害样本混在良性数据中，目标是把它们从剩余良性数据中筛出（Section 3.4）。
- 微调后阶段防御假设可以访问微调后的模型权重，部分方法还需要对齐版本与未对齐版本两套权重（Resta、Safe LoRA、SafeMerge、Antidote、IRR，见 Section 3.3）。
- 防御要同时满足抵抗性与稳定性，即不能显著损害用户下游任务精度（Section 2.2）。

**论文自述的局限**：

- Section 3.4 承认无法从现有实验明确得出防御与攻击类型的对应关系，因为评测不全面且数据集不统一。
- Section F.2 披露定性分析的潜在偏差：种子论文的选择带有主观性、论文收集只由第一作者执行、初始分类由第一作者完成而其他作者在其基础上复核。
- Section 3.5 引用 [188] 对 RepNoise 与 TAR 的评测，指出这两个方法"can become much less effective, sometimes even contradicting their claims of durability"，同时说明该论文的结论在社区内"非常有争议"。
- Section 5.3 承认隐藏嵌入漂移是否对所有有害微调攻击普遍成立"still not definitive"，并指出梯度上升项配置不当时会同时破坏正常知识。
- Section 2.1 说明微调后不再做安全对齐是出于计算代价与下游性能的权衡，这本身是一种设计妥协而不是能力保证。

**是否评估了自适应攻击者**：论文未说明有针对性的自适应攻击评估，论文没有设计"防御方部署后攻击方再调整"的闭环实验。可以作为弱相关证据的是：Section 3.2 记载了护栏审核部署之后"invalidating the original attack design"，随后出现隐写与护栏越狱两类规避审核的攻击设计；Section 5.1 记载 Virus 的黑盒迁移性弱（其 Table 9 显示在 Granite Guardian 3.1 上优化的数据无法很好地迁移到 Llama Guard）；Section 3.5 记载 [188] 对 RepNoise 与 TAR 的耐久性评测。这些都不是在同一实验框架内对某个具体防御做自适应攻击。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：）**：

- 分析：论文的威胁模型只有一个"用户"与一份数据集，没有客户端集合、参与率、采样与聚合的概念。防护库的客户端钩子与服务器聚合钩子在这篇论文里没有直接对应物；论文里的"逐样本过滤"不能直接翻译成"剔除恶意客户端"。
- 分析：论文假设攻击者不能控制优化过程与超参数。在联邦 LoRA 中客户端控制本地步数、学习率、批大小，甚至可以控制 LoRA 的秩与作用模块，这一假设不成立，攻击可以在更新空间而非仅在数据空间中发生。
- 分析：论文假设服务提供方持有同分布的有害参考数据集，并把它作为对齐阶段与微调阶段防御的输入。在联邦场景这等于要求服务器持有一个根数据集（root dataset），并不是所有联邦部署都允许服务器持有原始数据；如果只有聚合后的模型，RepNoise、TAR、Booster、CTRAP 这类依赖参考有害数据的防御需要重新设计其数据来源。
- 分析：论文的微调后修复依赖完整模型权重。在联邦 LoRA 中服务器通常只持有全局基座与低秩增量，修复动作必须改成对增量做投影、稀疏化或与安全增量做选择性合并，论文没有讨论这种形态。
- 分析：论文中"逐样本检测"依赖服务提供方看到每个样本。在联邦 LoRA 中服务器默认只看到客户端上传的低秩增量，逐样本信息被本地训练过程吸收，除非客户端额外汇报样本级统计或原始数据，否则该可观测面消失。
- 分析：论文关于安全层、安全子空间、安全神经元的结论来自集中式实验。它们是否在跨客户端聚合得到的 LoRA 增量上仍然成立，论文未说明。

## 10. 对防护库设计的含义

- 分析：库需要同时提供"客户端训练后"与"服务器收到更新时"两个采集钩子的数据视图。这篇论文的核心检测动作（审核模型过滤、SAFT 的嵌入空间检测、Seal 的双层打分、BDS 的逐样本权重）都要求看到逐样本数据；如果库只能拿到客户端上传的 LoRA 增量，就必须额外设计客户端侧样本统计上报通道，否则这些方法无法落地。
- 分析：库应把"参考数据集"做成服务器侧可注册、可版本化的资源，至少区分三类，即对齐数据集、同分布有害数据集与代理数据集。这是本论文反复出现的假设（Section 2.2 与 Appendix A 的 Q5），并且论文明确要求有害参考数据与攻击数据是不同实例；如果库不能表达"参考集与训练集不重叠"这一约束，评估结果会失真。
- 分析：干预接口至少要有三组。第一组是服务器聚合前的样本过滤与重加权（对应审核模型、SAFT、Seal、BDS）；第二组是客户端本地训练的损失与表示干预（对应 Vaccine 的扰动感知训练、RepNoise 的表示噪声与梯度上升、TAR 与 Booster 的元学习项、距离正则化）；第三组是聚合后的模型修复（对应 Resta、Safe LoRA、SafeMerge、Antidote、IRR）。论文本身不区分客户端与服务器，这套划分是我根据它的时间分类做的映射。
- 分析：库需要保留逐层与逐参数的视图，包括逐层增量、逐层范数，以及"当前模型与参考模型的对齐版本或未对齐版本"之间的权重差。Resta、Safe LoRA、SafeMerge、Antidote、IRR 都依赖这一视图，而在联邦 LoRA 中这意味着服务器要能按层访问聚合后的增量，并能与一个安全参考增量做比较。
- 分析：评估器应当插件化而不是硬编码。论文的有害分数有三种实现（审核模型、GPT-4 打分、字符串匹配），微调精度随任务不同而不同（Section 4.2），并且论文自己报告所用审核模型有 7.71% 的假阴性与 3.64% 的假阳性（Table 3）；把评估器固化会掩盖这些差异。
- 分析：通用需求是"逐轮、逐客户端、逐层的训练状态与更新采集"以及"提交、聚合、下发"三个固定钩子位置；本论文特有的需求是"以参考数据集上的损失或嵌入漂移作为安全信号"和"在微调后修复模型权重"。前者要求干净参考数据，后者要求服务器持有可写的全局模型，这两点在纯无数据联邦或纯增量聚合的部署里都不成立，库应当把它们标为带前置条件的插件而不是默认能力。

## 11. 原文依据

以下每条均为从全文中逐字复制的连续片段（数学符号按纯文本形式书写）。

1. **Section 2.2**，支撑第 3 节"攻击入口在本地数据准备、以比例 p 混入"与第 2 节"占比"：`The attack surface of harmful fine-tuning attack is within the fine-tuning stage. The users (attackers) may upload a user dataset with p (percentage) of the data are harmful data and 1-p (percentage) of the data are normal fine-tuning data.`
2. **Section 2.2**，支撑第 2 节"攻击目标"：`For intentional attackers, they intentionally upload harmful data to the service provider and they aim to compromise the safety alignment and elicit harmful answers/behaviors of the fine-tuned model.`
3. **Section 2.2**，支撑第 6 节"过滤样本"与第 2 节"防御者能力"：`Service providers can fully control the fine-tuning algorithms and fine-tuning hyperparameters. They can perform filtration/modification on the user uploaded dataset.`
4. **Section 2.2**，支撑第 5 节"对齐数据集与有害数据集两类输入"：`It is generally assumed that the service provider maintains i) an alignment dataset (harmful question/safe answer pair) and ii) a harmful dataset (harmful question/harmful answer pair) to assist the design of defense.`
5. **Section 2.2**，支撑第 9 节"有害参考数据必须与攻击数据不同实例"这一假设：`it is important to ensured that the data instances in this dataset are different from those harmful data that are used to launched the fine-tuning attack`
6. **Section 3.3**，支撑第 5 节"服务器收到更新时对逐样本数据做审核"：`The most naive defense is to utilize a moderation model to filter out the harmful data from the user fine-tuning dataset [72].`
7. **Section 3.3（正文引用 Table 3）**，支撑第 7 节"审核模型 7.71% 假阴性与 3.64% 假阳性"：`As shown, the moderation model has respectively 7.71% and 3.64% of false negative and false positive ratios.`
8. **Section 3.3**，支撑第 5 节"嵌入空间检测需要逐样本嵌入与奇异向量"：`Subsequent research SAFT [32] shows that harmful data can be more effectively detected by factorizing the embedding space and comparing the singular vector.`
9. **Section 2.3（Figure 5 的讨论）**，支撑第 5 节"对齐数据在每一注意力层的隐藏嵌入漂移需要干净参考数据与跨阶段历史"：`Specifically, embedding drift is quantified as the Euclidean distance between the hidden embeddings of the aligned model (or the pre-trained model for the non-aligned case) and the fine-tuned model, all using the same alignment dataset.`
10. **Section 3.2（Extension to other settings）**，支撑第 1 节与第 9 节"论文只在一句话里提到联邦学习扩展，本身不是联邦研究"：`For the training paradigm, [24] studies the influence of model editing towards the harmful behaviors of the model. [134, 258] studies the extension of harmful fine-tuning attack in the federated learning context.`

```json
{
  "key": "huang2024harmful",
  "title": "Harmful Fine-tuning Attacks and Defenses for Large Language Models: A Survey",
  "year": 2024,
  "paper_type": "survey",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "用户上传的微调数据集中的每个样本（按比例 p 混入的有害数据与良性下游数据）", "where": "server_receive", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "微调样本的嵌入表示与嵌入空间奇异向量", "where": "server_receive", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "对齐数据集（有害问题与安全回答配对）上的对齐损失", "where": "server_post_aggregate", "granularity": "model", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "对齐数据在每一注意力层上的隐藏嵌入漂移", "where": "server_post_aggregate", "granularity": "layer", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "同分布有害数据集（有害问题与有害回答配对，且与攻击实例不同）上的损失与梯度", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "代理数据集（安全的一般问题与安全回答配对）上的表示损失", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "微调过程中有害数据上的训练损失与未见有害数据上的测试损失", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "微调前后模型参数差（安全向量、增量更新、逐层坐标）", "where": "server_post_aggregate", "granularity": "layer", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "每个数据点的安全属性后验与分配的学习权重", "where": "server_receive", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "审核模型对模型回答的有害性判定（用于评估有害分数）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["filter_samples", "reweight", "add_noise", "repair_model"],
  "intervention_where": ["server"],
  "assumptions": [
    "服务提供方完全控制对齐、微调与部署流程",
    "攻击者只能操作上传的数据，不能控制微调过程与超参数选择",
    "服务提供方持有对齐数据集（有害问题与安全回答配对）",
    "服务提供方持有同分布有害数据集（有害问题与有害回答配对），且其实例与攻击所用有害数据不同",
    "部分防御还需要代理数据集（安全的一般问题与安全回答配对）",
    "数据过滤类防御假设只有少量有害样本混在良性数据中",
    "微调后阶段防御假设可访问微调后的模型权重，部分方法还需要对齐版本与未对齐版本两套权重",
    "防御须同时满足抵抗性与稳定性，即不显著损害用户下游任务精度"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Section 2.2", "supports": "第 3 节攻击入口位于本地数据准备，以及第 2 节有害数据比例 p", "text": "The attack surface of harmful fine-tuning attack is within the fine-tuning stage. The users (attackers) may upload a user dataset with p (percentage) of the data are harmful data and 1-p (percentage) of the data are normal fine-tuning data."},
    {"section": "Section 2.2", "supports": "第 2 节攻击目标为破坏安全对齐并诱出有害回答", "text": "For intentional attackers, they intentionally upload harmful data to the service provider and they aim to compromise the safety alignment and elicit harmful answers/behaviors of the fine-tuned model."},
    {"section": "Section 2.2", "supports": "第 2 节防御者能力与第 6 节过滤样本这一干预动作", "text": "Service providers can fully control the fine-tuning algorithms and fine-tuning hyperparameters. They can perform filtration/modification on the user uploaded dataset."},
    {"section": "Section 2.2", "supports": "第 5 节防御所需的对齐数据集与有害数据集两类输入", "text": "It is generally assumed that the service provider maintains i) an alignment dataset (harmful question/safe answer pair) and ii) a harmful dataset (harmful question/harmful answer pair) to assist the design of defense."},
    {"section": "Section 2.2", "supports": "第 9 节防御参考数据必须与攻击数据为不同实例这一假设", "text": "it is important to ensured that the data instances in this dataset are different from those harmful data that are used to launched the fine-tuning attack"},
    {"section": "Section 3.3", "supports": "第 5 节与第 6 节中服务器收到更新时对逐样本数据做审核并过滤", "text": "The most naive defense is to utilize a moderation model to filter out the harmful data from the user fine-tuning dataset [72]."},
    {"section": "Section 3.3 引用 Table 3", "supports": "第 7 节审核模型 7.71% 假阴性与 3.64% 假阳性这两个数值", "text": "As shown, the moderation model has respectively 7.71% and 3.64% of false negative and false positive ratios."},
    {"section": "Section 3.3", "supports": "第 5 节嵌入空间检测需要逐样本嵌入与奇异向量", "text": "Subsequent research SAFT [32] shows that harmful data can be more effectively detected by factorizing the embedding space and comparing the singular vector."},
    {"section": "Section 2.3（Figure 5 的讨论）", "supports": "第 5 节隐藏嵌入漂移的逐层粒度、干净参考数据与跨阶段历史需求", "text": "Specifically, embedding drift is quantified as the Euclidean distance between the hidden embeddings of the aligned model (or the pre-trained model for the non-aligned case) and the fine-tuned model, all using the same alignment dataset."},
    {"section": "Section 3.2 的 Extension to other settings", "supports": "第 1 节与第 9 节关于论文仅在扩展工作里提及联邦学习、本身并非联邦研究", "text": "For the training paradigm, [24] studies the influence of model editing towards the harmful behaviors of the model. [134, 258] studies the extension of harmful fine-tuning attack in the federated learning context."}
  ]
}
```
