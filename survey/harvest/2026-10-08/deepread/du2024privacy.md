# du2024privacy：Privacy in Fine-tuning Large Language Models: Attacks, Defenses, and Future Directions

## 1. 基本信息

- **场景**：这是一篇**综述（survey）**，不研究单一场景，而是横跨三类：(1) **集中式大模型微调**（论文主体，第 3、4 节的绝大多数被引工作）；(2) **联邦大模型微调**（第 4.3 节把联邦学习作为一类隐私防御范式，综述了 FwdLLM、FedIT、FedBPT、FL-GLM、联邦 DP-LoRA；第 3.2 节的 FILM 攻击也发生在联邦学习场景）；(3) **预训练模型与适配器的发布/共享供应链**（第 5.1、5.2 节讨论恶意预训练模型发布与 LoRA 等微调结果共享带来的攻击面）。按题目给的枚举，无法归入单一值，最接近的是"其他"（多场景综述），但在**联邦 + 参数高效微调**这个组合上确有直接覆盖。
- **训练阶段**：以**微调阶段**为唯一聚焦点；只在讨论"预训练投毒"时涉及预训练阶段（第 3.1、3.3 节，Wen et al. [39] 的 "Poison Injection while Pre-training"；第 5.1 节）。
- **论文类型**：综述。
- **模型与数据规模**：论文**没有自己的实验**，因此没有自己的模型与数据规模。它通过表 1（Table 1）与表 2（Table 2）汇总被引工作用到的预训练模型与微调方法：表 1 出现 GPT-2、GPT-J、GPT-Neo、Pythia、ClinicalBERT、BERT、RNN、T5、Llama、Llama2、Falcon、Alpaca；表 2 出现 BERT、RoBERTa、ALBERT、DistilBERT、GPT-2、T5、GPT-Neo、OPT、Llama、Llama2、ChatGLM、BLOOM 及一个 "Custom TF"。微调方法统一用缩写标注：A = Adapter、L = LoRA、B = BitFit、P1 = Prompt-tuning、P2 = Prefix-tuning、F = Full fine-tuning（第 2.2 节末与表 1、表 2 脚注）。数据规模只有一句定性描述：微调数据集通常 "ranging from a few hundred to several thousand samples"（数百到数千条，第 2.1 节）。第 4.4 节提到 LLaMA2-7B。
- **重要提示**：论文的核心议题是**隐私**（成员推断与数据抽取），**后门（backdoor）** 被当作隐私风险的放大器来讨论（第 3.3 节、Remark 3），而不是作为投毒防御问题；论文**没有提出任何检测器或防御算法**。

## 2. 威胁模型

综述覆盖多篇工作，攻击者身份随被引工作而变，论文没有给出统一的攻击者模型；以下逐类列出，凡论文未给出的量化信息一律注明。

**攻击者是谁**

- **数据提供方 / 数据投毒者**：向微调数据集（尤其是指令微调数据）注入带触发器的恶意样本（第 3.3 节；Wan et al. [38] 用 "carefully crafted malicious examples"，Xu et al. [42] 把恶意指令与合法数据混合，Yan et al. [46] 的 Virtual Prompt Injection 通过污染指令微调数据精确控制模型在特定触发器下的输出）。占比或数量：**论文未说明**。
- **预训练模型发布者**：在发布前把后门写进预训练模型，受害者下载并微调后攻击生效。第 5.1 节明确写 "Adversaries can release maliciously modified pre-trained models, embedding backdoors or vulnerabilities"。Wen et al. [39] 与 Liu et al. [25] 的 PreCurious 都属于这一类。占比或数量：**论文未说明**。
- **微调模型 / 适配器发布者**：表 1 的 Capability 列中有 "Publishing Models"，对应 PreCurious [25]，其覆盖的微调方法为 A、B、L（Adapter、BitFit、LoRA），目标为 FD（fine-tuning data）。第 3.2 节指出，攻击者拿到公开发布的微调模型后可继续训练或微调，从而抽取微调数据。
- **外部查询者（黑盒或白盒）**：多数成员推断攻击（Membership Inference Attack，MIA）假设黑盒访问，攻击者看不到内部参数，只依据模型输出判断某样本是否在微调数据集中（第 3.1 节）。表 1 的 Access 列显示：15 条攻击记录中绝大多数为 BB（black-box），只有 [18] 标为 "BB,WB"，[12]（FILM）标为 WB（white-box）。
- **联邦训练中的更新观测者**：FILM [12] "capturing gradient updates during federated training"（第 3.2 节）。它是信道窃听、服务器接收还是聚合器内部捕获：**论文未说明**。

**能力（能改什么）**

改微调数据（注入触发器样本或恶意指令）；改预训练模型权重并发布；控制微调过程（PreCurious 先用辅助数据微调出 "adversarially initialized model"，并 "adjusts model parameters to delay convergence"，第 3.3 节）；黑盒或白盒访问微调后模型；在联邦场景中观测梯度更新。

**知识（知道什么）**

公开可得的预训练基座模型常被当作参考模型使用（第 3.1 节 Mireshghallah et al. [31] 的似然比方法用原模型作参考；第 3.2 节 Zanella-Béguelin et al. [49] 用基座模型快照与逐 token 概率变化）。第 3.1 节还提到 SPV-MIA [11] 用自提示（self-prompting）从目标模型自身生成参考数据集，因而不需要外部参考数据。

**目标**

三类：(1) **隐私**——MIA（第 3.1 节）与数据抽取/重建（第 3.2 节），论文摘要把它概括为 "membership inference, data extraction, and backdoor attacks"；(2) **操纵模型输出**——后门（第 3.3 节），Remark 3 说后门可以让模型 "generating harmful outputs"（生成有害输出），这属于安全对齐层面的破坏，但论文未使用"越狱"一词；(3) **复合目标**——用后门放大 MIA 与数据抽取的成功率（第 3.1、3.3 节，Remark 1 与 Remark 3）。定向后门与非定向破坏的区分：**论文未说明**。

**防御者是谁、能看到什么、信任什么**

论文不给出单一防御者模型，而是按防御类别隐含不同信任边界：数据匿名化的防御者在文本预处理阶段能看到原始样本并做命名实体识别与改写（第 4.1 节）；DP 微调的防御者能对逐样本梯度做裁剪与加噪（第 4.2 节）；联邦学习假定各方不共享原始数据、只交换模型参数或梯度，并依赖中央服务器聚合（第 4.3 节）；知识遗忘的防御者能在训练后编辑模型参数（第 4.4 节）；Off-site Tuning 假定数据方只拿到压缩后的 Emulator 与可训练 Adapter，模型方不下发完整模型（第 4.5 节）。这些方法是否信任服务器、是否信任下载来的预训练模型，**论文未逐条说明**。

## 3. 攻击入口与流程位置

论文是综述，因此按攻击族分别定位入口：

1. **本地数据准备（local data）**：最主要入口。向微调/指令微调数据集注入带触发器样本或恶意指令（第 3.3 节，[38][42][46]）；另一种是预训练阶段的数据投毒，表 1 中 [39] 的 Capability 为 "Poison Injection while Pre-training"。这一步在流程上早于本地训练。
2. **本地训练过程（local training）**：PreCurious [25] 先用辅助数据微调合法预训练模型，得到对抗性初始化模型；受害者在这个模型上微调时，攻击者已经通过 "adjusts model parameters to delay convergence" 让模型延长暴露在私有数据上的时间（第 3.3 节）。这是对训练过程本身的操纵，而不是对数据的操纵。
3. **更新上传与聚合（联邦场景）**：FILM [12] 在联邦训练中捕获客户端上传的梯度更新来重建句子（第 3.2 节）。具体是在通信信道、服务器收到更新时、还是在聚合时捕获，**论文未说明**；论文也没有讨论客户端上传前对更新做的缩放、投影、拼装等后处理。
4. **模型下发与发布（model distribution）**：恶意预训练模型的发布（第 5.1 节）；公开发布微调后的模型（表 1 的 "Publishing Models" 能力，[25]，覆盖 Adapter、BitFit、LoRA）；第 5.2 节明确点名 "malicious attacks leveraging shared fine-tuning results (e.g., LoRA)"。这一入口发生在训练**之后**、部署**之前**。
5. **评估与部署（evaluation/deployment）**：黑盒 MIA 与数据抽取都在推理/查询阶段发起（第 3.1、3.2 节）。

**防御论文所针对的入口**：本文是综述，其第 4 节列出的防御分别对应上述入口——匿名化对应本地数据准备，DP 微调对应本地训练，联邦学习对应更新上传与聚合，知识遗忘对应训练后的模型，Off-site Tuning 对应模型下发（避免下发完整模型）。

## 4. 方法原理

论文不提出新方法，以下是被综述的各类方法的核心思想。

**攻击侧**

- **MIA（第 3.1 节）**：Jagannatha et al. [18] 用基于阈值（Threshold-Based Attack）的黑盒方法判断样本是否参与微调；Mireshghallah et al. [31] 用**似然比（Likelihood Ratios）**，把原始预训练模型当作参考来校准；Fu et al. [11] 的 SPV-MIA 用自提示生成参考数据集，并提出概率变异（probabilistic variation）指标来度量记忆而非过拟合；Wen et al. [39] 在预训练模型里预先埋后门以提升 MIA 成功率。
- **数据抽取（第 3.2 节）**：Lukas et al. [27] 提出三类黑盒攻击——PII 抽取、PII 重建、PII 推断，重建时用预训练的掩码语言模型生成候选词；Zanella-Béguelin et al. [49] 用基座模型快照与两个模型给每个 token 分配概率的**累积变化**来抽取微调数据；Ozdayi et al. [32] 证明 prompt-tuning 可以被人为用来控制模型对特定数据的记忆；Gupta et al. [12] 的 FILM 用联邦训练中被捕获的梯度更新，借助预训练模型中的语言先验恢复句子。
- **后门（第 3.3 节）**：向微调数据注入触发器样本（[38][42]），或用 Virtual Prompt Injection 污染指令数据以在触发器下精确控制输出（[46]）；PreCurious [25] 把后门用于提升记忆化。

**防御侧（第 4 节，表 2 按五类汇总）**

- **数据匿名化（第 4.1 节）**：经典流程是文本预处理 + 命名实体识别（Named Entity Recognition，NER）+ 共指消解（Coreference Resolution，CRR），再用抑制、标记、随机替换、泛化等方式匿名化 [28][37][5]；带差分隐私（Differential Privacy，DP）的路线是把文本映射为嵌入、**对嵌入裁剪并加噪**，再解码回文本（[10][17][48][36]），k-匿名（k-anonymity）在 1997 年被提出 [35]。
- **带 DP 的微调（第 4.2 节）**：以 DP-SGD 为基础，对逐样本梯度裁剪加噪；工程改进包括 ghost clipping（显存节省的 DP-SGD）、Book-Keeping（BK，只需一次反向传播、不实例化逐样本梯度）、Phantom Clipping（针对 attention distraction）；框架层面有 EW-Tune（Edgeworth Accountant，面向微调的有限样本隐私保证）、Fine-tune Twice（JFT，只对数据中的敏感部分施加 DP）、ADP（自适应差分隐私，按估计的隐私概率动态调整噪声强度）。PEFT 方向：Yu et al. [47] 把 DP 用到 LoRA 与 Adapter；Li et al. [23] 把 DP-Adam 与 Ghost Clipping 扩展到 PEFT；RAPT [24] 在本地隐私（local privacy）下做 prompt-tuning 与 prefix-tuning。
- **联邦学习（第 4.3 节）**：各方本地计算、只交换模型参数或梯度。FwdLLM [44] 用 "perturbed inference" 做**无反向传播**训练；FedIT [50] 在联邦设置下用 LoRA 做指令微调；FedBPT [34] 做黑盒 prompt-tuning；FL-GLM [51] 加入梯度保护与密钥加密；Liu et al. [26] 实现联邦下的 DP-LoRA 并优化通信开销。
- **知识遗忘（第 4.4 节）**：ROME [29] 定位并单独编辑负责事实预测的层与神经元；Jang et al. [19] 通过**最大化目标序列上的训练损失**来遗忘；Eldan and Russinovich [9] 用通用词替换特定术语并训练强化模型以降低 token 似然；Chen and Yang [4] 构造 unlearning layer，用选择性师生目标训练，最后可融合为单层。
- **Off-site Tuning（第 4.5 节）**：把预训练模型拆成两部分——**Adapter**（小的可训练模块）与 **Emulator**（压缩版模型，提供梯度但隐藏完整结构）。数据方在本地用 Emulator 微调 Adapter 并把 Adapter 发回，模型方把它与完整模型集成。

**引用一致性提示**：第 4.2 节把 ghost clipping 归给 "Li et al. [10]"，但参考文献 [10] 是 Feyisetan 等人的文本匿名化工作；论文此处存在编号与文献表不一致（这是可观测到的文本事实，非我的推断）。

## 5. 检测或防御所需的数据

论文没有提出检测器，因此没有"检测特征清单"；以下逐项列出第 4 节各类防御所**隐含需要**的输入，以及第 3 节各类攻击所**依赖**的可观测量。凡论文没有交代的字段，写"论文未说明"。

**防御侧**

1. **微调数据集的原始文本及其中的 PII / 敏感实体**
   - 是什么：待匿名化的文本与其中的命名实体、共指链。
   - 在哪里采集：客户端训练前（数据准备阶段；在集中式设置中是训练前的预处理阶段）。
   - 粒度：逐样本（NER 与 CRR 在样本内部进行）。
   - 是否需要跨轮历史 / 干净参考数据 / 额外计算 / 其他客户端数据：不需要跨轮历史；不需要干净参考数据；需要额外前向计算（第 4.1 节用 LLM 做匿名化与去匿名化、用 BART 类模型生成替换词）；不需要其他客户端的数据。
2. **文本嵌入（embedding）**
   - 是什么：把输入文本映射成的嵌入向量，是 DP 文本匿名化中被裁剪与加噪的对象（第 4.1 节）。
   - 在哪里采集：客户端训练前（数据预处理/推理前）。
   - 粒度：逐样本（论文按"嵌入"描述，未细到逐 token 或逐维度）。
   - 是否需要跨轮历史 / 干净参考数据 / 额外计算 / 其他客户端数据：都不需要，但需要模型前向计算来产生嵌入。
3. **逐样本梯度（per-sample gradient）**
   - 是什么：DP-SGD 的裁剪与加噪对象；第 4.2 节说明 Book-Keeping 的价值恰恰在于"eliminates the need to instantiate per-sample gradients"，说明基线 DP-SGD 需要它。
   - 在哪里采集：客户端每一步（本地训练过程中）。
   - 粒度：逐样本（按 DP-SGD 定义）。
   - 是否需要跨轮历史 / 干净参考数据 / 额外计算 / 其他客户端数据：不需要跨轮历史与参考数据；需要额外反向计算；不需要其他客户端数据。
4. **客户端上传的模型参数或梯度更新（联邦场景）**
   - 是什么：联邦学习中各方交换的对象（第 4.3 节）；在 FILM 攻击中是被捕获的梯度更新（第 3.2 节）；在第 5.2 节被点名为 LoRA 等共享微调结果。
   - 在哪里采集：服务器收到更新时（论文对 FILM 只说 "during federated training"，未精确定位）。
   - 粒度：逐客户端、逐轮；是否逐层，论文未说明。
   - 是否需要跨轮历史 / 干净参考数据 / 额外计算 / 其他客户端数据：聚合与 DP-LoRA 类方法本质上跨轮；论文未说明是否需要干净参考数据；捕获梯度本身不需要额外前向或反向计算；聚合必然涉及其他客户端的数据。
5. **微调后的模型或适配器（LoRA 增量、Adapter、BitFit 偏置、prompt/prefix）**
   - 是什么：可被发布或共享的微调产物（表 1 的 "Publishing Models" 能力；表 2 中 FL 与 off-site tuning 的交换对象）。
   - 在哪里采集：客户端训练后（上传前）或训练后模型发布时。
   - 粒度：逐客户端、逐模型；LoRA 的逐层低秩矩阵粒度论文未说明。
   - 是否需要跨轮/参考/额外计算：论文未说明。
6. **被篡改的预训练模型权重（供应链侧）**
   - 是什么：含后门的预训练模型；第 5.1 节说需要 "robust verification methods to detect backdoors or malicious modifications in pre-trained models"，说明验证对象是模型权重本身，但**具体验证需要什么输入论文未说明**。
   - 采集位置：客户端训练前（下载并微调之前）。
7. **被遗忘目标序列上的训练损失**
   - 是什么：知识遗忘 [19] 通过最大化目标序列的训练损失来实现遗忘，因此需要逐目标序列的损失。
   - 在哪里采集：训练后（对**聚合后的全局模型**或已微调模型做后处理时）。
   - 粒度：逐样本/逐目标序列。
   - 需要额外前向与反向计算。

**攻击侧（攻击留下的可观测痕迹，即库如果要检测这些攻击可以采集什么）**

8. **模型输出文本**：黑盒 MIA 与数据抽取的观测面（第 3.1 节 "infer the inclusion of data samples ... based on the model's outputs"）；采集于评估/部署时的查询；逐样本；需要额外前向计算。
9. **样本在目标模型上的损失或似然**：阈值法与似然比 MIA 的核心量（第 3.1 节）；评估时；逐样本。
10. **公开基座模型对同一批样本的似然（参考分布）**：第 3.1 节 Mireshghallah et al. 用原始模型作参考；这是"干净参考数据"的一种形式，但论文把它当作攻击者**可以公开获得**的东西，而不是防御者需要保管的资产。
11. **目标模型自身生成的参考数据集**：SPV-MIA [11] 用 self-prompting 生成，替代外部参考集；需要额外前向计算。
12. **两个模型快照之间的逐 token 概率累积变化**：Zanella-Béguelin et al. [49] 的抽取依据；需要跨"版本"的历史（基座快照与微调后模型）；逐 token、逐样本。
13. **被注入的触发器样本**：攻击者侧可控量（第 3.3 节），防御者若要在数据侧检测，需要逐样本的数据视图。

**论文声称能绕过哪些检测**：论文**没有**讨论任何具体的检测器规避手段，也**没有**给出后门检测器的可用特征（第 5.1 节只把它列为待研究方向）。唯一相关的表态是第 5.4 节：DP "reduces but does not eliminate risks of data extraction"，即 DP 不是完整防护；以及第 5.4 节说微调可以增强记忆化，可能使遗忘失效。

## 6. 干预动作

论文是综述，干预动作按防御类别列出；论文**没有**提出任何基于检测的处置机制。

- **数据匿名化（第 4.1 节）**：在数据准备阶段对样本做抑制、标记、随机替换、泛化，或在嵌入层做裁剪加噪。性质是**过滤/改写样本**，不是剔除客户端。
- **带 DP 的微调（第 4.2 节）**：在训练中裁剪逐样本梯度并注入噪声（DP-SGD、ghost clipping、Phantom Clipping、Book-Keeping）；Fine-tune Twice 只对敏感部分加 DP；ADP 按估计的隐私概率动态调整噪声强度。动作是**裁剪 + 加噪**，位置在训练过程（客户端/本地训练器）。
- **联邦学习（第 4.3 节）**：不上传原始数据，只交换参数或梯度；FL-GLM 进一步做梯度保护与密钥加密；DP-LoRA 在联邦中做 DP 并优化通信。动作是**改变共享对象与传输保护**，位置覆盖客户端与服务器通信两侧。论文**未说明**会剔除恶意客户端、重新加权或裁剪恶意更新。
- **知识遗忘（第 4.4 节）**：训练后编辑或删除特定知识（编辑层与神经元、最大化目标序列损失、术语替换加强化训练、unlearning layer 融合）。动作是**修复模型**，位置在训练后/聚合后的模型上。
- **Off-site Tuning（第 4.5 节）**：不下发完整模型，只交换 Adapter 与 Emulator。它改变的是共享粒度，论文未说明其中含任何检测或剔除动作。
- **论文没有提出的动作**：基于检测的客户端剔除（exclude）、重新加权（reweight）、针对恶意更新的裁剪、模型回滚（rollback）、仅报告（report only）——这些在全文与表 1、表 2 中均无依据。

## 7. 实验设置与主要结果

- **论文是综述，没有自己的实验**。因此：模型、数据集、客户端数与参与率、训练轮次、恶意客户端比例、数据是否非独立同分布（non-IID）、评价指标、任何数值结果——**论文均未报告**，也没有实验表格或图。
- 论文给出的"结果"是两张汇总表与若干被引工作的定性结论：
  - **表 1（Table 1）**：按 Target（FD = fine-tuning data、M = manipulating model）、Capability、FT（F/A/L/B/P1）、Pre-train、Access（BB/WB）五个维度比较攻击方法，共 15 条记录：MIA 5 条（[31][18][11][39][25]）、数据抽取 5 条（[27][32][49][12][25]）、后门 5 条（[39][46][42][38][25]）。表 1 覆盖的微调方法包含 LoRA（L）、Adapter（A）、BitFit（B）、Prompt-tuning（P1）与全量微调（F）。Access 列中只有 [18] 标 "BB,WB"、[12] 标 WB，其余均为 BB。
  - **表 2（Table 2）**：按数据匿名化、带 DP 的微调（再分 Full 与 PEFT）、联邦学习、知识遗忘、Off-site Tuning 五类汇总防御，并列出各工作使用的预训练模型与微调方法（含 L、A、B、P1、P2）。
  - **定性结论（均为被引工作的发现，不是本文实验）**：第 3.1 节报告 Jagannatha et al. 的结果——自回归模型（如 GPT-2）比掩码语言模型（如 BERT）更易受 MIA，且攻击成功率随模型规模上升；Mireshghallah et al. 的结果——head fine-tuning 比 full fine-tuning 或 adapter fine-tuning 更易受 MIA。这些结论论文**未给出具体数值**。
  - 第 2.1 节：微调数据集规模通常为 "a few hundred to several thousand samples"。
  - 第 3.3 节：预训练后门 "amplifies the original privacy risks by several magnitudes"，**没有给出具体倍数**。
  - 第 4.4 节：提到 LLaMA2-7B 的特定主题遗忘场景。

## 8. 开销

论文没有自己的开销测量，只转述被引工作的定性说法，**没有报告任何数值**（显存、时间、通信量、参数量均无数值）：

- 第 4.2 节：把 DP 学习用于大型 NLP 模型会带来 "substantial performance degradation and high computational overhead"；ghost clipping "maintains strong performance under the same privacy budget with minimal runtime overhead"；Book-Keeping 只需一次反向传播且无需实例化逐样本梯度，从而 "significantly improves throughput"，同时保持相近显存占用；Phantom Clipping 进一步改善 DP 约束下的训练效率与性能。
- 第 4.2 节（PEFT）：LoRA 与 DP-SGD 组合在速度与显存效率上表现最好；Li et al. [23] 用 DP-Adam 与 Ghost Clipping 显著降低显存，把私有与非私有训练的差距缩小到 "a negligible level"；RAPT 面向本地隐私的 prompt/prefix tuning。
- 第 4.3 节（联邦）：FwdLLM 的无反向传播 "significantly reducing memory and computational demands"；FedIT、FedBPT 降低显存与算力开销；FL-GLM 增加梯度保护与密钥加密（其额外开销论文未报告）；DP-LoRA 优化通信开销。
- 第 4.5 节：Off-site Tuning "reduces computational cost"。
- **论文未报告**：任何防御在真实部署中的逐轮开销、通信字节数、端到端时延，也未报告攻防开销的对比表。

## 9. 假设、局限与自适应攻击

**论文中有依据的成立假设**

1. 微调数据比预训练数据更敏感、领域更窄、规模更小，因此更易被记忆、更易受定向攻击（第 2.1、5.3 节）。
2. 预训练模型是公开可得的：攻击者可以下载它当参考模型（第 3.1、3.2 节）、在它上面注入后门再发布（第 3.1、3.3、5.1 节）。
3. 多数 MIA 假设黑盒访问，攻击者 "lack access to the model's internal parameters but infer the inclusion of data samples ... based on the model's outputs"（第 3.1 节）；数据抽取可黑盒也可白盒（表 1：[12] 为 WB）。
4. 联邦学习假设各方不共享原始数据，只交换模型参数或梯度（第 4.3 节）。论文把联邦学习列为**隐私防御**，但在第 4.3 节内**没有**讨论梯度反演会破坏这一假设——而第 3.2 节的 FILM 恰恰利用了梯度更新。
5. DP 的前提是隐私预算与效用之间的权衡可接受（第 5.5 节），且 DP 只降低、不消除数据抽取风险（第 5.4 节）。
6. PEFT 被广泛采用，但其隐私影响 "remain underexplored"（第 5.2 节）。
7. 数据匿名化的效用依赖于 NER 与 CRR 的质量（第 4.1 节把二者称为该流程的基础）。

**论文自述的局限与挑战（第 5.1–5.5 节）**

- 缺少对预训练模型的验证与审计手段（水印、来源与完整性）来对抗恶意预训练模型（第 5.1 节）。
- PEFT 特有攻击与防御研究不足，LoRA 等共享微调结果带来新攻击面（第 5.2 节）。
- 缺少针对微调数据特性的隐私研究（第 5.3 节）。
- 现有防御无法全面覆盖多种攻击；"there is a lack of unified metrics for evaluating effectiveness of defenses across diverse scenarios"，因此主张统一的隐私度量与集成防御框架（第 5.4 节）。
- 效用与隐私的权衡在微调场景尤其关键，因为下游任务对性能要求高（第 5.5 节）。

**是否评估了自适应攻击者**：**论文未说明**。这是一篇没有实验的综述，全文没有自适应攻击者（adaptive attacker）的实验或讨论；也没有讨论攻击者针对匿名化、DP、联邦聚合做规避的具体手段。

**迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）**

- 分析：论文把联邦学习当作防御，其安全性论述停留在"不上传原始数据"，并未讨论**恶意客户端上传投毒 LoRA 增量**这类完整性威胁；论文第 3.3 节的后门全部发生在数据侧或预训练模型侧，因此这篇论文不能为"联邦聚合层的投毒检测"提供设计依据。
- 分析：论文的 MIA/抽取结论大多来自集中式全量微调、Adapter 或 Prompt-tuning（表 1、表 2），LoRA 被单独列出但论文没有给出 LoRA 与其它 PEFT 在隐私风险上的对比结论（第 5.2 节把这个问题明确列为open question），因此"LoRA 增量的隐私/投毒风险与全量微调相同"这一假设不成立。
- 分析：在联邦 LoRA 中，可观测上传物是低秩增量而非全量梯度，FILM 式梯度反演能否迁移到低秩因子，论文未讨论；同样，DP-SGD 在 LoRA 上的逐样本梯度与传统全参数梯度在采集形态上不同，库需要明确采集的是低秩因子梯度还是合并后的等效梯度。
- 分析：论文假设攻击者能拿到公开基座模型作为参考（第 3.1、3.2 节），在联邦 LoRA 场景下这一假设更强——攻击者还可能拿到公开的适配器；论文第 5.2 节只把它列为风险，没有给出防护结论。
- 分析：论文没有涉及客户端数量、参与率、轮次、non-IID 等联邦变量（第 7 节"论文未报告"），因此其被引防御在真实联邦 LoRA 配置下的有效性无法从本文推断。
- 分析：论文的 DP-PEFT 结论（LoRA + DP-SGD 速度与显存最优、效用损失可忽略）是转述 [47][23] 的结果，迁移到"联邦 + 异构客户端 + 逐轮通信"时是否仍成立，论文未说明。

## 10. 对防护库设计的含义

1. **分析**：通用采集点。要落地本文综述的防御面，库至少需要五类固定钩子：客户端训练前的原始样本视图（支撑匿名化插件做 NER/CRR/替换）、客户端每步的逐样本梯度或低秩梯度视图（支撑 DP 裁剪加噪插件）、客户端训练后的微调产物视图（LoRA 增量、Adapter 等，支撑发布前的检查与共享控制）、服务器收到更新时的逐客户端逐轮视图（支撑联邦侧保护与审计）、聚合后模型上的逐样本损失视图（支撑知识遗忘插件）。这些是通用需求，不专属于本文。
2. **分析**：本文特有的数据视图是"参考模型基线"。因为论文反复把公开基座模型当作攻击者的必需输入（似然比 MIA、逐 token 概率累积变化），库若要检测这类攻击，需要在服务器端登记基座模型的指纹与似然基线，并保存微调后模型/适配器的历史快照以便做跨版本概率差；这是本文（相对于一般投毒防御库）特有的要求。
3. **分析**：本文将"发布"视为一等攻击入口（表 1 的 Publishing Models、第 5.1 节的恶意预训练模型发布、第 5.2 节的 LoRA 共享攻击面）。因此库的客户端钩子不应止于"上传更新"，还应覆盖"适配器/模型的对外发布前检查"，并在服务器钩子上支持"下载的预训练模型入库前验证"这一前置位置。
4. **分析**：本文能支撑的干预接口是裁剪、加噪、样本过滤/改写、模型修复四类；本文完全不能支撑客户端剔除、重新加权、恶意更新裁剪、模型回滚这些聚合层动作，因为这些动作在论文中没有依据。库若需要这些动作，必须由其他论文补齐。
5. **分析**：本文不提供任何检测算法、阈值、特征或自适应攻击评测，因此它只能作为"采集点与数据视图的需求来源"，不能作为检测插件的行为规范；第 5.4 节自述"缺少跨场景统一度量"，也意味着库不宜从本文复制任何评价指标。
6. **分析**：由于本文是隐私视角的综述，把后门主要当作隐私放大器，若库的目标是**投毒防护**，本文的直接贡献集中在"联邦与 PEFT 场景下有哪些可观测量与共享面"，而不是"如何判定某个 LoRA 增量是恶意的"。

## 11. 原文依据

1. 第 3.3 节（Backdoor Attack）——支撑第 2 节"数据提供方向微调数据集投毒即可植入后门"与第 3 节"入口在本地数据准备"：
   > "By injecting carefully crafted malicious examples into the fine-tuning dataset, attackers can implant backdoors, causing the fine-tuned model to exhibit incorrect behavior in classification tasks when specific trigger phrases are encountered."
2. 第 3.2 节（Data Extraction Attack）——支撑第 3 节"联邦场景的入口是梯度更新"、第 5 节"梯度是核心可观测量"、第 9 节"联邦假设会被梯度泄露破坏"：
   > "Gupta et al. [12] explored the fine-tuning scenario in a Federated Learning setting and introduced the FILM attack. By capturing gradient updates during federated training, FILM leverages the language priors encoded in pre-trained models to recover sentences."
3. 第 3.2 节（Data Extraction Attack）——支撑第 5 节"需要跨版本模型快照与逐 token 概率"以及"需要参考基座模型"：
   > "Using snapshots of the base model with cumulative change in the probabilities assigned to each token by the two models, Zanella-Béguelin et al. [49] have successfully extracted the data used to fine-tune and update the model."
4. 第 3.1 节（Membership Inference Attack）——支撑第 5 节"似然比 MIA 需要原始预训练模型作为参考"与第 9 节"公开预训练模型可作参考"的假设：
   > "They proposed an MIA based on Likelihood Ratios, using the original model as a reference. This approach was extended from masked language models to auto-regressive language models."
5. 第 3.1 节（Membership Inference Attack）——支撑第 2 节"预训练模型发布者可作为攻击者"与第 3 节"入口在模型发布/下发"：
   > "Wen et al. [39] demonstrated that injecting a backdoor into a pre-trained model before fine-tuning substantially enhances the effectiveness of MIAs."
6. 第 4.1 节（Data Anonymization）——支撑第 6 节"干预动作包含在嵌入层裁剪与加噪"以及第 5 节"需要嵌入级数据视图"：
   > "Typically, A neural model is utilized to generate embeddings from the input data. These embeddings, which are often clipped, are then subjected to perturbation by adding noise, following the principles of DP, to ensure privacy preservation."
7. 第 4.2 节（Fine-tuning with Differential Privacy）——支撑第 5 节"DP-PEFT 的数据视图"与第 8 节"开销方面的定性结论"：
   > "They further highlighted that LoRA, when combined with DP-SGD, excels in terms of speed and memory efficiency, making it particularly suitable for private fine-tuning."
8. 第 4.3 节（Federated Learning）——支撑第 1 节"论文覆盖联邦大模型 LoRA 微调"与第 9 节"迁移到联邦 LoRA 的相关性"：
   > "FedIT [50] framework, which focuses directly on PEFT by leveraging LoRA for instruction-tuning in a federated learning setup."
9. 第 4.5 节（Off-site Tuning）——支撑第 3 节"适配器作为可共享产物的入口"与第 10 节"适配器级采集与共享控制"：
   > "The data owner fine-tunes the adapter locally with the emulator and sends back the adapter. The model owner integrates it with the full model to complete the tuning."
10. 第 5.4 节（Limitations of Existing Defense Methods）——支撑第 9 节"DP 只降低不消除抽取风险、遗忘可能失效"与"缺少统一度量"的局限性陈述：
    > "For instance, Differential Privacy (DP) reduces but does not eliminate risks of data extraction. [27] Fine-tuning can also be used to enhance the memorization of LLMs [32], which may make unlearning ineffective."

```json
{
  "key": "du2024privacy",
  "title": "Privacy in Fine-tuning Large Language Models: Attacks, Defenses, and Future Directions",
  "year": 2024,
  "paper_type": "survey",
  "setting": "other",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider", "adapter_publisher", "external"],
  "attack_goal": ["privacy", "backdoor", "jailbreak_safety", "untargeted"],
  "attack_entry": ["local_data", "local_training", "server_aggregation", "model_distribution", "evaluation_deployment"],
  "observables": [
    {"what": "微调数据集原始文本及其中的 PII 与命名实体（匿名化插件的输入）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "文本嵌入（DP 文本匿名化中裁剪与加噪的对象）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "逐样本梯度（DP-SGD 裁剪与加噪的对象）", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "客户端上传的模型参数或梯度更新（FILM 在此捕获梯度以重建句子）", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "微调后的模型或适配器产物（LoRA 增量、Adapter、BitFit、prompt/prefix），即可发布或共享的对象", "where": "client_post_train", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "被篡改的预训练模型权重与其中的后门（第 5.1 节要求验证但未给出验证输入）", "where": "client_pre_train", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "微调后模型的黑盒输出文本（MIA 与数据抽取的观测面）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "样本在目标模型上的损失或似然（阈值法与似然比 MIA）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "公开预训练基座模型对同一样本的似然（似然比 MIA 的参考分布）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "基座快照与微调后模型之间逐 token 概率的累积变化（数据抽取依据）", "where": "evaluation", "granularity": "sample", "needs_history": true, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "被注入的触发器样本或恶意指令（数据侧投毒痕迹）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "被遗忘目标序列上的训练损失（知识遗忘插件的输入）", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["clip", "add_noise", "filter_samples", "repair_model"],
  "intervention_where": ["client", "server"],
  "assumptions": [
    "微调数据集比预训练数据更敏感、领域更窄、规模更小（数百到数千条），因此更容易被记忆和定向攻击（第 2.1、5.3 节）",
    "预训练模型公开可得，攻击者可将其作为参考模型、在其上注入后门后重新发布（第 3.1、3.2、5.1 节）",
    "多数成员推断攻击假设黑盒访问，仅凭模型输出判断样本是否属于微调数据集（第 3.1 节）",
    "联邦学习假设各方不共享原始数据、只交换模型参数或梯度，并依赖中央服务器聚合（第 4.3 节）",
    "差分隐私的隐私预算与效用权衡可接受，且 DP 只降低而不消除数据抽取风险（第 5.4、5.5 节）",
    "PEFT（含 LoRA）被广泛采用但其隐私影响尚未被充分研究（第 5.2 节）",
    "数据匿名化的有效性依赖命名实体识别与共指消解的质量（第 4.1 节）",
    "知识遗忘依赖对逐目标序列训练损失的可计算性（第 4.4 节）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "3.3 Backdoor Attack", "supports": "第 2 节攻击者身份与目标、第 3 节攻击入口在本地数据准备", "text": "By injecting carefully crafted malicious examples into the fine-tuning dataset, attackers can implant backdoors, causing the fine-tuned model to exhibit incorrect behavior in classification tasks when specific trigger phrases are encountered."},
    {"section": "3.2 Data Extraction Attack", "supports": "第 3 节联邦场景入口为梯度更新、第 5 节梯度是可观测量、第 9 节联邦假设的脆弱性", "text": "Gupta et al. [12] explored the fine-tuning scenario in a Federated Learning setting and introduced the FILM attack. By capturing gradient updates during federated training, FILM leverages the language priors encoded in pre-trained models to recover sentences."},
    {"section": "3.2 Data Extraction Attack", "supports": "第 5 节需要跨版本模型快照与逐 token 概率、需要参考基座模型", "text": "Using snapshots of the base model with cumulative change in the probabilities assigned to each token by the two models, Zanella-Béguelin et al. [49] have successfully extracted the data used to fine-tune and update the model."},
    {"section": "3.1 Membership Inference Attack", "supports": "第 5 节似然比 MIA 需要原始预训练模型作参考、第 9 节公开预训练模型假设", "text": "They proposed an MIA based on Likelihood Ratios, using the original model as a reference. This approach was extended from masked language models to auto-regressive language models."},
    {"section": "3.1 Membership Inference Attack", "supports": "第 2 节预训练模型发布者作为攻击者、第 3 节入口在模型发布与下发", "text": "Wen et al. [39] demonstrated that injecting a backdoor into a pre-trained model before fine-tuning substantially enhances the effectiveness of MIAs."},
    {"section": "4.1 Data Anonymization", "supports": "第 6 节干预动作包含嵌入层裁剪与加噪、第 5 节嵌入级数据视图", "text": "Typically, A neural model is utilized to generate embeddings from the input data. These embeddings, which are often clipped, are then subjected to perturbation by adding noise, following the principles of DP, to ensure privacy preservation."},
    {"section": "4.2 Fine-tuning with Differential Privacy", "supports": "第 5 节 DP-PEFT 的数据视图、第 8 节开销的定性结论", "text": "They further highlighted that LoRA, when combined with DP-SGD, excels in terms of speed and memory efficiency, making it particularly suitable for private fine-tuning."},
    {"section": "4.3 Federated Learning", "supports": "第 1 节论文覆盖联邦大模型 LoRA 微调、第 9 节迁移相关性", "text": "FedIT [50] framework, which focuses directly on PEFT by leveraging LoRA for instruction-tuning in a federated learning setup."},
    {"section": "4.5 Off-site Tuning", "supports": "第 3 节适配器作为可共享产物的入口、第 10 节适配器级采集与共享控制", "text": "The data owner fine-tunes the adapter locally with the emulator and sends back the adapter. The model owner integrates it with the full model to complete the tuning."},
    {"section": "5.4 Limitations of Existing Defense Methods", "supports": "第 9 节 DP 只降低不消除抽取风险、遗忘可能失效的论文自述局限", "text": "For instance, Differential Privacy (DP) reduces but does not eliminate risks of data extraction. [27] Fine-tuning can also be used to enhance the memorization of LLMs [32], which may make unlearning ineffective."}
  ]
}
```
