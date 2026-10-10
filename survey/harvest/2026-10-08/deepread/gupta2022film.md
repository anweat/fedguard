# gupta2022film：Recovering Private Text in Federated Learning of Language Models

## 1. 基本信息

- **场景**：传统联邦学习（federated learning，FL）中语言模型（language model，LM）的全参数训练，不是联邦大模型 LoRA（Low-Rank Adaptation）微调，也不是参数高效微调（parameter-efficient fine-tuning，PEFT）。论文自述研究对象是 "federated learning of language models"（摘要、第 1 节）。实验实现是"单服务器 + 单客户端"的模拟（第 6.1 节），论文用脚注 8 说明该设置被普遍接受为 FL 的等价替身。
- **训练阶段**：客户端在本地私有文本上做自回归语言建模（autoregressive language modeling），每步计算批次梯度并上传；论文训练 90,000 次迭代，攻击者可以在任意迭代 t ∈ [T] 观察（第 3.3 节、第 6.1 节）。攻击既可在未微调的公开预训练模型上发起（t = 0），也可在训练中期发起（图 4）。
- **论文类型**：攻击（attack）为主，附带提出并评估一个防御（冻结词嵌入），并复测两个已有防御（梯度剪枝、DPSGD）。不是检测论文、基准或综述。
- **模型与数据规模**：GPT-2 base，117M 参数（第 6.1 节）；WikiText-103 预处理后 203,456 个句子，Enron Email 预处理后 31,797 个句子，各保留 2,000 条作为评估集（第 6.1 节、附录 B.1）。攻击批次大小覆盖 1、16、32、64、128（图 3、表 10）。数据被切成句子并过滤：少于 40 个 token、少于 5 个未登录 token、在预训练 GPT-2 上困惑度（perplexity）小于 50、至少含 1 个命名实体（附录 B.1）。训练 90,000 次迭代，初始学习率 1×10⁻⁵ 并线性衰减，使用早停（第 6.1 节）。

## 2. 威胁模型

- **攻击者是谁**：一个"诚实但好奇"（honest-but-curious）的窃听者，窃听中央服务器与任意一个客户端之间的通信（第 3.3 节、图 1 标题）。它不是恶意客户端，也不是恶意服务器；它是通信信道上的被动观察者。论文在相关工作里明确把"恶意服务器可以篡改模型权重"的更强威胁模型归给 Boenisch et al. (2021) 与 Fowl et al. (2022)，自己并不采用（第 2 节）。
- **占比或数量**：论文未说明攻击者占客户端比例。论文只说攻击者窃听"任意一个客户端 cᵢ, i ∈ [N]"的通信（第 3.3 节）；N 客户端是第 3.2 节的一般性描述，实验里没有任何客户端数量或参与率数值。
- **能力（能改什么）**：只能读，不能改。论文没有赋予攻击者修改上传梯度、修改本地数据、修改损失函数或篡改聚合结果的能力；论文也没有描述攻击者注入任何内容。攻击者的能力被概括为白盒访问两样东西（第 3.3 节）：1）客户端 cᵢ 上传的梯度 ∇θtLθt(Bᵢ)；2）模型参数 θt，包括词表 V 与词嵌入矩阵 W。攻击者可以在任意训练迭代 t ∈ [T] 检查这些信息（第 3.3 节）。
- **知识（知道什么）**：知道模型架构与当前权重、词表与分词方式、词嵌入矩阵；知道如何用模型算下一词概率分布 IPθt(x)；在 t = 0 的场景中利用公开预训练 GPT-2 的语言先验（第 4.1 节、第 6.2 节）。论文假设 GPT-2 "没有在 Wikipedia 数据上训练，也极不可能在 Enron Email 数据上训练"（第 6.1 节）。攻击者不知道私有批次内容本身，这正是要恢复的目标。
- **目标**：隐私窃取，即从梯度中重建客户端的私有文本句子。论文的表述是"至少恢复私有训练批次 Bᵢ 中的一句话"，并指出恢复一句就足以破坏联邦学习的隐私保证；进一步可以通过重复攻击恢复同一批次中的多句（第 3.3 节、第 4.5 节）。这不是无目标破坏、后门或越狱目标。
- **防御者是谁、能看到什么、信任什么**：论文没有定义"防御者能看到什么"的完整信任模型。它评估的三种防御分别是：对上传梯度做低幅值置零的梯度剪枝（gradient pruning）、客户端本地的差分隐私随机梯度下降（Differentially Private Stochastic Gradient Descent，DPSGD）、以及训练时冻结词嵌入（第 5 节、第 6.3 节）。前两者作用在客户端侧的梯度上，第三者作用在客户端的训练配置上。论文未说明防御者是否可信、是否能看到其他客户端数据、是否有服务器侧检测器。

## 3. 攻击入口与流程位置

- **实际入口是"客户端上传的明文梯度"这一通信边界，攻击不注入任何内容。** 用论文的话说，攻击者窃听客户端与服务器之间的通信，白盒读取客户端发出的梯度 ∇θtLθt(Bᵢ)（第 3.3 节）。因此它不落在本地数据准备、本地训练的损失或优化器、更新上传前的缩放/投影/拼装、服务器聚合规则、全局模型下发内容、评估与部署中的任何一环的"写入"侧；它在"客户端本地训练算完梯度"与"服务器聚合"之间读取。若必须映射到给定的入口枚举，最接近的是"更新上传（更新离开客户端之前）"这一信任边界，与"全局模型下发"这一侧的信息（模型参数 θt 是攻击的第二项输入）；论文没有把它归入聚合，因为攻击不需要看到聚合结果。
- **具体操作步骤**（第 4 节）：
  1. 客户端在私有批次 Bᵢ 上做一次前向与反向，得到 ∇θtLθt(Bᵢ)（第 3.2 节、图 1）。
  2. 窃听者取词嵌入矩阵梯度 ∇WtLθt(Bᵢ) 的非零行，还原出出现在该批次任意句子中的词集合 B（无词频信息）；再取位置嵌入梯度 ∇PtLθt(Bᵢ) 的非零行，还原该批次句子的最大长度（第 4.2 节）。
  3. 用当前模型分布 IPθt(x) 在词袋 B 上做 beam search：以 B 中首字母大写的词作为候选起始词，每步保留得分最高的 k 个 beam，加重复 n-gram 惩罚，生成长度上限 40 词，输出整体概率最高的句子（第 4.3 节、附录 A 算法 1）。
  4. 用基于先验的评分函数（困惑度 + 梯度范数）做短语级与词级的重排，各迭代 200 步（第 4.4 节、公式 4）。
  5. 重复 beam search 并对上一轮结果施加额外 n-gram 惩罚，以恢复同一批次中的多句（第 4.5 节）。
- **位置小结**：攻击读取的数据来自"客户端训练后、上传时"的更新，以及"服务器聚合后、下发时"的全局模型；攻击本身发生在服务器聚合之前，不需要参与聚合，也不需要修改模型或数据。
- 论文强调攻击可以在任意迭代 t 上进行，而且训练越靠后攻击越强（第 4.1 节脚注 5、第 6.2 节、图 4）。

## 4. 方法原理

**核心思想**：不直接在连续的高维空间里做梯度匹配（论文认为这对离散文本无效且对初始化敏感，第 6.2 节、附录 B.3），而是先用嵌入层梯度的非零结构把问题从"恢复连续向量"降成"恢复一个离散词袋"，再借助语言模型的概率分布（语言先验或训练记忆）把词袋排成句子，最后用梯度信息微调词序。

1. **词袋提取（第 4.2 节）**：输入 ∇θtLθt(Bᵢ)，输出词袋 B = {w₁, w₂, …, w_m}。做法是取词嵌入梯度的非零行；再取位置嵌入梯度的非零行得到批次内句子的最大长度。论文明确说明这一步只给出词的集合，不给词频；论文用 n-gram 惩罚补偿词频缺失（第 4.3 节）。
2. **Beam search 句子重建（第 4.3 节、附录 A 算法 1）**：以 B 中大写开头的词作为 prompt 集合 P，逐步扩展，每一步用 TOP(·) 过程对候选打分，分数形式为 log IPθt(beam) 减去 ρ·Rₙ(beam)（Rₙ 是 n-gram 计数函数，ρ 是惩罚系数），保留前 k 个 beam，直到达到指定长度（论文用 40 词），返回整体概率最高的文本。
3. **先验引导的词序重排（第 4.4 节、公式 4）**：对句子 x 定义得分 Sθ(x) = exp{−(1/n)·log IPθ(x)}（困惑度项）+ β·‖∇θLθ(x)‖（梯度范数项），β 控制两项权重。短语级重排：去掉冗余片段后按若干切点切分并置换短语，取 Sθ(·) 最优候选，迭代 200 步（切分策略引 Malkin et al., 2021）。词级重排：每步随机执行三种操作之一——交换两个 token、删除一个 token、从词袋插入一个 token，取 S 最优候选，迭代 200 步。附录 B.8 给出该评分函数的设计依据：原始训练句通常比其微改版本有更低的困惑度和更低的梯度范数（图 9）。
4. **多句恢复（第 4.5 节）**：反复做 beam search，从第二次起对与已有结果重复的 n-gram 施加额外惩罚，累积候选集合，最后对每个候选做上述重排。
5. **防御原理（第 5 节）**：切断攻击的第一阶段。冻结词嵌入后，词嵌入梯度不再被更新与传输，词袋无法恢复；论文论证后续阶段就退化为在整个词表上做 beam search。论文同时评估梯度剪枝（对低幅值梯度项置零）与 DPSGD（逐样本裁剪加高斯噪声，Abadi et al., 2016），并指出两者都带来明显的效用损失。

## 5. 检测或防御所需的数据

对这篇攻击论文，下面列出攻击消耗的可观测量（这也是任何想检测或复现 FILM 的一方需要采集的数据）。

1. **每个客户端上传的完整模型梯度 ∇θtLθt(Bᵢ)。**
   - 是什么：语言模型全部参数在客户端本地一个私有批次上的梯度张量，其中词嵌入层与位置嵌入层的梯度是攻击的关键。
   - 在哪里采集：服务器收到更新时（服务器侧钩子），等价地也可在客户端训练后、上传前采集（客户端侧钩子）。
   - 粒度：批次级（论文攻击的对象是一个 mini-batch 的聚合梯度），逐层/逐参数可见。
   - 跨轮历史：不需要；单个批次、单个客户端的明文梯度就足以发起一次攻击。
   - 干净参考数据：不需要。
   - 额外前向/反向：不需要（读取的是已有梯度）。
2. **词嵌入矩阵梯度 ∇WtLθt(Bᵢ) 的非零行。**
   - 是什么：上传梯度中的一个派生视图，非零行对应批次中出现的 token。
   - 在哪里采集：服务器收到更新时，直接从上一条的张量中切出词嵌入层。
   - 粒度：逐层（进而逐 token），对应到批次内的词集合而不是词频。
   - 跨轮历史：不需要；干净参考数据：不需要；额外计算：不需要。
3. **位置嵌入梯度 ∇PtLθt(Bᵢ) 的非零行。**
   - 是什么：用来恢复批次内句子的最大长度（第 4.2 节）。
   - 在哪里采集：服务器收到更新时，切出位置嵌入层。
   - 粒度：逐层；跨轮历史：不需要；干净参考数据：不需要；额外计算：不需要。
4. **当前全局模型参数 θt（含词表 V 与词嵌入矩阵 W）。**
   - 是什么：用于计算语言模型分布 IPθt(x) 做 beam search，以及在重排阶段计算候选句子的梯度范数 ‖∇θLθ(x)‖（公式 4）。
   - 在哪里采集：服务器聚合后的全局模型，或客户端收到的下发模型；论文强调攻击者可以在任意迭代 t 拿到 θt。
   - 粒度：模型级（整个权重），逐轮。
   - 跨轮历史：攻击本身不要求保存历史更新，但攻击强度随 t 增大而提高（图 4），因此攻击者需要能够持续获得每一轮的模型与梯度；t = 0 的场景需要一份公开预训练 LM 权重作为语言先验。
   - 干净参考数据：论文未要求客户端之外的干净数据；但它需要一份公开的预训练 GPT-2（第 6.2 节）。论文未说明这被视为"干净参考数据"。
   - 额外前向/反向：需要。beam search 要对大量候选做前向打分，重排阶段还要对候选句子做一次反向以得到梯度范数。论文未报告这部分的具体计算量。
5. **不需要的数据**：论文未说明攻击需要其他客户端的数据、需要根数据集（root dataset）、或需要客户端本地的原始样本；单客户端信道就足够（第 6.1 节）。

**攻击留下的痕迹与论文声称能绕过的检测**：FILM 是纯读侧攻击，不修改上传内容，因此更新本身的分布不会因为攻击而改变；论文没有讨论基于异常检测、更新相似度或元数据的检测器（论文未说明）。在防御测线上论文给出的结论是：梯度剪枝在剪枝率高达 0.9999 时攻击仍能恢复 >90% 的 token（第 6.3 节、表 4a）；DPSGD 只有在 ε 小于 15 时才能把 token 召回压到 0.5 以下，而代价是困惑度上升（表 4b）；冻结词嵌入使 token 重建的精确率与召回率都为 0（第 6.3 节）。论文只在相关工作里提到密码学手段（加密梯度、加密数据与模型）可以防护梯度反演，但指出部署会拖慢训练且需要特殊设置，并未评估（第 2 节）。

## 6. 干预动作

- **攻击本身没有任何干预动作**：不剔除客户端、不重新加权、不裁剪、不加噪、不过滤样本、不修改或回滚模型；它只读取并在攻击者本地离线重建文本，属于"仅报告/仅观察"。
- **论文评估的防御动作及其位置**：
  1. **梯度剪枝（gradient pruning）**：把上传梯度中幅值低的一部分置零。论文的描述是"zeros out the fraction of gradient entries with low magnitude"，并说明只要剪枝率不是极高，批次中已有 token 的词嵌入梯度仍然非零，因此攻击策略不变，仍取非零的嵌入梯度（第 6.3 节）。动作作用在客户端即将上传的梯度上（论文未明确说明由客户端还是服务器执行）。
  2. **DPSGD**：客户端本地训练时做逐样本裁剪并加高斯噪声（引 Abadi et al., 2016）。论文未说明裁剪范数与噪声乘数的具体取值，只按 ε ∈ {1, 5, 10, 15, ∞} 报告结果（第 6.3 节、表 4b）。
  3. **冻结词嵌入（论文提出的防御）**：训练时不更新词嵌入矩阵，使词嵌入梯度不再被传输，"一旦阻止训练中词嵌入梯度的传输，就不可能再恢复词袋"（第 5 节）。动作位置是客户端的训练配置/上传内容。论文的实践建议是：从公开预训练 LM 出发、冻结词嵌入来微调（第 5 节）。
- 这些防御都不是"检测后触发"的：论文没有检测器，三种干预都是无条件施加的训练或上传策略。论文也没有报告在服务器聚合处做剔除、重新加权或模型修复的动作。

## 7. 实验设置与主要结果

- **模型与数据**：GPT-2 base（117M）；WikiText-103 与 Enron Email；预处理后分别 203,456 与 31,797 句，各留 2,000 条评估（第 6.1 节、附录 B.1）。
- **联邦设置**：第 6.1 节明确写"a federated learning setting with a single server and a single client"，脚注 8 说明在数据独立同分布（I.I.D.）假设下，N 个客户端各持 b 个样本的同步联邦学习与批量大小为 N×b 的集中训练在功能上等价。
- **训练设置**：90,000 次迭代，初始学习率 1×10⁻⁵，线性衰减，早停（第 6.1 节）。消融中数据集规模取 5k、50k、100k、200k，初始学习率取 1×10⁻⁵、5×10⁻⁵、1×10⁻⁴、5×10⁻⁴（附录 B.7、图 8）。
- **恶意比例**：不适用；攻击者是被动窃听者，论文未给出任何占比（论文未说明）。
- **非独立同分布**：论文未评估非独立同分布（non-IID）设置；唯一相关表述是脚注 8 的 IID 假设。
- **指标**：ROUGE-1/2/L F 分数（Lin, 2004）与命名实体恢复率（named entity recovery ratio，NERR，完全恢复的命名实体占比）；防御评估另用 token 重建的精确率 |S*∩S|/|S*| 与召回率 |S*∩S|/|S|，以及模型在测试集上的平均困惑度（第 6.1、6.3 节）。命名实体由 spaCy 标注（附录 B.1 脚注 10）。
- **关键结果**：
  - 表 10（附录 B.4，20 个测试 mini-batch 的均值，括号内为最好情况）：WikiText-103 上 b = 1 时 ROUGE-1 0.74 ± 0.12（最好 1.00）、ROUGE-2 0.44 ± 0.19（1.00）、ROUGE-L 0.54 ± 0.14（1.00）、NERR 0.28 ± 0.35（1.00）；b = 16 时 ROUGE-1 0.38、ROUGE-L 0.27、NERR 0.26；b = 64 时 ROUGE-1 0.34、ROUGE-L 0.26；b = 128 时 ROUGE-1 0.37、ROUGE-L 0.29、NERR 0.28。Enron Email 上 b = 1 时 ROUGE-1 0.73、ROUGE-L 0.61、NERR 0.34；b = 16 时 ROUGE-1 0.41、ROUGE-L 0.31、NERR 0.40；b = 64 与 b = 128 时 ROUGE-1 均为 0.37、ROUGE-L 均为 0.29（表 10）。
  - 与已有方法的对比（表 9，附录 B.3，20 个样本平均）：WikiText-103 上 b = 1 时 DLG 的 ROUGE-1 0.03、TAG 0.39，FILM 0.74；Enron Email 上 b = 1 时 DLG 0.04、TAG 0.46，FILM 0.83。表 1 给出定性例子，其中 FILM 在 b = 128 时仍能恢复大段短语。
  - 迭代恢复多句（表 3，WikiText-103，b = 16，ROUGE-L > 0.25 视为强泄漏）：重复 1 次时召回 0.03 ± 0.03、精确率 0.50 ± 0.51；10 次时 0.19 ± 0.11 / 0.28 ± 0.16；100 次时 0.34 ± 0.09 / 0.07 ± 0.02。论文摘要与引言概括为"batch size 为 16 时可恢复约 1/3 的句子"。
  - 训练迭代的影响（图 4，WikiText-103，攻击 batch size 1）：预训练模型未微调时平均 ROUGE-L 0.41，继续在 WikiText-103 上训练后升到 0.53，约 30% 提升；随机初始化模型整体弱于预训练模型，但差距随迭代数增加而缩小（第 6.2 节）。
  - 超参数（第 7 节）：beam size 增大则效果提升，约 32 是效果与效率的最优折中（图 5 左）；n-gram 惩罚取 n = 2 最好，接近"已知词频"的 oracle（图 5 右）；重排评分中 β = 1 最优（图 6 左）；重排带来的提升在小批次下最明显（图 6 右）。
  - 训练配置消融（附录 B.7、图 8）：数据集规模从 5,000 到 200,000 时攻击效果基本持平；初始学习率越大攻击略强（表 14 给出对应定性例子）。
  - 防御结果：梯度剪枝下精确率始终为 1.00，剪枝率 0.9/0.99 时召回 1.00，0.999 时 0.98，0.9999 时 0.90，困惑度从 11.46 升到 19.21（表 4a）；DPSGD 下 ε = 1 时精确率与召回率均为 0.00、困惑度 16.31，ε = 5 时为 0.29/0.01、14.32，ε = 10 时为 0.88/0.17、12.86，ε = 15 时为 0.97/0.49、11.98，ε = ∞ 时为 1.00/1.00、11.46（表 4b）。冻结词嵌入时 token 重建精确率与召回率都为 0（第 6.3 节）。
  - 效用代价：WikiText-103 上从零训练时冻结词嵌入使困惑度从 27.31 升到 118.69，从预训练模型出发时从 11.40 变到 11.48；Enron Email 上从零训练 15.16 变 69.17，从预训练出发 7.09 变 7.30（表 5）。

## 8. 开销

- 攻击计算开销：论文报告"我们的算法运行时间相当快，用一块 Nvidia 2080TI GPU 可以在不到一分钟内恢复一个句子"（第 6.1 节）。第 7 节指出 beam size 越大攻击所需计算资源越多，并据此推荐 beam size 约 32（图 5 左）。论文未给出更细的 FLOPs、显存或总攻击耗时统计。
- 通信与存储开销：论文未报告。
- 防御开销：论文未报告梯度剪枝、DPSGD 或冻结词嵌入的计算、通信、存储开销；只报告了对模型效用的影响（困惑度，表 5）以及攻击侧指标的变化（表 4）。DPSGD 的 ε 与噪声参数细节论文未说明。

## 9. 假设、局限与自适应攻击

**成立所依赖的假设（论文有依据的部分）**：
1. 攻击者是被动窃听者，只读不改；论文没有给它任何篡改能力（第 3.3 节）。
2. 上传的是逐客户端的明文梯度，没有安全聚合或加密；密码学防御只在相关工作里被提及为"可以防护但部署昂贵"，未被评估（第 2 节）。
3. 训练会更新词嵌入矩阵，因此嵌入梯度存在可区分的非零行——这正是冻结词嵌入能奏效的原因（第 4.2、5 节）。
4. 数据是句子级、长度通常不超过 40 词、绝大多数 token 在词表内；论文在预处理时显式过滤（附录 B.1）。
5. 模型会记忆训练数据，且训练越久记忆越强、攻击越好；这是论文解释"训练后期更脆弱"的核心机制（摘要、第 6.2 节、图 4）。
6. 单客户端单服务器模拟在 IID 数据假设下与 N 客户端同步 FL 等价（第 6.1 节脚注 8）。
7. 攻击者拥有与训练相同的模型权重与分词器，可以离线做前向与反向计算（第 4.3、4.4 节）。

**论文自述的局限（第 8 节）**：没有评估攻击能否泛化到其他自然语言处理任务（如文本分类）；没有尝试超过 128 的批次大小，消融也没有报告超过 16 的批次；多句恢复中"如何从 100 个生成句里挑出好的那几句"仍是开放问题；在从零预训练场景下冻结词嵌入会显著损害模型效用，因此该场景下如何防御仍然开放。

**自适应攻击者**：论文为两种防御分别调整了攻击策略，可以视为针对防御的自适应评估（第 6.3 节）。面对梯度剪枝，攻击仍然返回词嵌入梯度非零的 token，结果精确率恒为 1.00、剪枝率 0.9999 时召回仍为 0.90（表 4a）。面对 DPSGD，论文改用阈值 τ = σ√2 log d 区分"有信号的梯度"与"纯噪声"，其中 d 是嵌入维度（论文给出 768）、σ 是噪声尺度；对每个 token 检查其嵌入梯度的最大幅值，超过 τ 就认为该 token 很可能在原始批次中。结果在 ε = 15 时召回 0.49、ε = 10 时 0.17、ε = 5 时 0.01（表 4b）。对论文自己提出的冻结词嵌入防御，论文没有构造新的自适应攻击；它的论证是第一阶段失败后后续阶段退化为全词表上的 beam search（第 5 节），并在附录 B.9 / 图 10 对比了有词袋与无词袋的 beam search：小批次下有词袋显著更强，大批次下词袋仍能显著提升命名实体恢复率。论文未评估"冻结词嵌入后改用其他层梯度恢复词信息"之类的自适应攻击。

**迁移到联邦 LoRA 微调时可能失效的假设**：
- 分析：LoRA 的常规做法就是冻结基座权重，词嵌入矩阵属于被冻结的参数，因此 FILM 的第一阶段（词嵌入梯度非零行）在这种配置下没有信号；这恰好与论文提出的防御重合，所以论文的原始攻击很可能无法直接作用于冻结嵌入的 LoRA 适配器。论文没有做 LoRA 实验，这一点是分析而非论文结论。
- 分析：论文第二阶段依赖用 IPθt(x) 做 beam search 和用 ∇θLθ(x) 做重排，这需要把 LoRA 增量合并进基座后仍能白盒前向与反向；如果服务器只下发/上传低秩矩阵 A、B 而不给基座权重，或者客户端本地才能合并，那么攻击者能否重建同一分布取决于它是否掌握基座模型，论文未讨论。
- 分析：论文假设单个客户端的明文全参数梯度可见。联邦大模型微调实践中常见安全聚合、梯度压缩、以及只传适配器参数，这些都会改变可观测量；论文只在相关工作里提到安全聚合，未评估。
- 分析：论文的数据是 ≤40 词的维基百科/邮件句子，且预过滤掉高困惑度样本；指令微调数据、带系统提示词的对话数据、长上下文样本的分布与长度假设不同，论文未说明其方法在长样本上的行为。
- 分析：论文的"训练越久越容易泄漏"依赖全参数微调下的记忆效应；低秩更新是否仍能带来同等的记忆与语言先验增益，论文未研究，这是一个明确空白。
- 分析：论文表 5 的效用结论（从预训练模型出发时冻结词嵌入几乎不损失效用）是在全参数微调 GPT-2 上得到的；LoRA 场景下嵌入本来就冻结，论文没有给出对应的效用对照，因此这条结论不能直接搬用。

## 10. 对防护库设计的含义

- 分析：采集底座必须在"客户端上传前/服务器收到更新时"这个信任边界上保存**完整的逐层梯度张量**，而不是只存标量统计量（范数、相似度）。FILM 的全部第一阶段信号都在词嵌入层的**逐行非零结构**里，只留逐层范数的采集点会直接丢掉这个信号；词嵌入层与位置嵌入层必须能被单独切出来。这是这篇论文特有的采集要求。
- 分析：库需要把"某一轮的更新"和"同一轮的全局模型权重"配对存证（模型版本号 + 更新一一对应），因为 FILM 用 θt 解释同轮的梯度，重排阶段还要对候选句子在同一个 θt 上做一次反向。这类"模型—更新版本对齐"是通用需求，但它在本论文里是硬依赖。
- 分析：这篇论文的干预接口有两类，都落在客户端钩子：一类是训练配置钩子（指定参数子集不更新，即冻结词嵌入，同时让这些参数的梯度不进入上传内容），另一类是上传前梯度处理钩子（低幅值置零的剪枝、以及逐样本裁剪加高斯噪声的 DPSGD）。服务器侧在这篇论文里没有任何检测或干预动作，因此为这篇论文实现"服务器聚合后修复/剔除"是没有依据的。
- 分析：这篇论文说明了一类不对应"投毒检测"的防护思路——攻击不在更新里留下异常统计特征，靠检测更新分布是抓不到它的，最有效的干预是改变通信内容本身（不传输嵌入梯度）。因此库的插件接口除了"检测—剔除/加权"路径，还应支持"改变上传内容/冻结参数"这种非检测型、在每个客户端上无条件生效的防御插件。
- 分析：评测与复现这套方法需要库能提供（a）公开或合成语料切成的句级批次，（b）按固定间隔导出完整模型检查点的能力（论文在 t = 0 到 90,000 的多个点发动攻击），以及（c）每个客户端每轮的上传梯度与对应模型的配对视图。这三点对任何梯度反演类的检测插件都是通用的。
- 分析：面向联邦 LoRA 时，库应当额外采集 LoRA 的 A/B 增量以及合并后的本地模型，用来回答论文没有回答的问题——在词嵌入冻结的低秩更新下，token 身份信息是否仍会通过适配器梯度泄漏。采集这两类对象是 LoRA 场景特有的扩展，超出本文的实验范围。

## 11. 原文依据

1. 第 3.3 节 "Adversary's capabilities"：*"We consider an honest-but-curious adversary who is eavesdropping on the communication between the central server s and an arbitrary client ci, i ∈[N] in the federated training of a language model parameterized by θ, as described above."* —— 支撑第 2 节"攻击者是被动窃听者"与第 3 节"攻击入口在客户端与服务器的通信边界"。
2. 第 3.3 节 "Adversary's capabilities"：*"An adversary in this scenario has white-box access to 1) the gradients ∇θtLθt(Bi) sent by the client ci, and 2) the model parameters θt (Fig. 1), including the vocabulary V and the embedding matrix W."* —— 支撑第 2 节的能力描述与第 5 节列出的两种核心可观测量。
3. 第 3.3 节 "Adversary's objective"：*"The adversary aims to recover at least one sentence from the private training data batch Bi based on the information they observe, as recovering a single sentence is already sufficient to break the privacy guarantee of federated learning."* —— 支撑第 2 节"目标为隐私窃取"与第 4 节"方法以恢复句子为目标"。
4. 第 4.2 节 "Bag-of-Words Extraction"：*"We follow the method outlined by Melis et al. (2019) and recover a set of words B = {w1, w2, . . . , wm} by considering the non-zero rows of the word embedding gradients ∇WtLθt(Bi)."* —— 支撑第 3 节"攻击的第一步是从上传梯度的词嵌入层取非零行"与第 5 节第 2 项可观测量。
5. 第 4.3 节 "Beam Search for Sentence Reconstruction"：*"The beam tree continues until the generated sentence reaches a specified length (we use 40 words), and outputs the text that has the overall highest probability (see Fig. 2)."* —— 支撑第 4 节 beam search 阶段的关键参数（句长上限 40 词）与"取整体概率最高者"的选句方式。
6. 第 5 节 "Defending Against the FILM Attack"：*"In other words, once we prevent the transmission of gradients of word embeddings during training, it is no longer possible to recover the bag-of-words."* —— 支撑第 6 节"冻结词嵌入的干预位置在上传内容"与第 9 节"该方法成立依赖词嵌入梯度可观测"。
7. 第 6.1 节 "Training and attack settings"：*"Following previous studies (Zhu et al., 2019; Geiping et al., 2020; Yin et al., 2021; Huang et al., 2021) for gradient inversion attacks, our evaluation considers a federated learning setting with a single server and a single client."* —— 支撑第 1 节与第 7 节"实验是单服务器单客户端模拟"以及第 9 节迁移时的局限。
8. 第 6.3 节 "Token reconstruction under gradient pruning"：*"However, the attacker can still recover a considerable amount of tokens (i.e. >90%) even with a prune ratio as high as 0.9999."* —— 支撑第 5 节"论文声称剪枝难以阻止攻击"与第 7 节表 4a 的结论。
9. 第 6.3 节 "Token reconstruction under DPSGD"：*"For each token, we check the maximum magnitude of its embedding gradients: if the value is larger than τ, then the token may be included in the original batch with high probability."* —— 支撑第 9 节"论文针对 DPSGD 调整了攻击策略，属于对防御的自适应评估"。
10. 第 6.1 节 "Training and attack settings"：*"We note that the running time of our algorithm is quite fast, and we can recover a single sentence in under a minute using an Nvidia 2080TI GPU."* —— 支撑第 8 节报告的攻击计算开销。

```json
{
  "key": "gupta2022film",
  "title": "Recovering Private Text in Federated Learning of Language Models",
  "year": 2022,
  "paper_type": "attack",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["external"],
  "attack_goal": ["privacy"],
  "attack_entry": ["update_postprocess"],
  "observables": [
    {"what": "客户端上传的完整模型梯度 ∇θtLθt(Bi)，逐层/逐参数，含词嵌入层与位置嵌入层", "where": "server_receive", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "词嵌入梯度的非零行，用于还原批次内出现的词袋（无词频信息）", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "位置嵌入梯度的非零行，用于还原批次内句子的最大长度", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "当前全局模型参数 θt（含词表 V、词嵌入矩阵 W），用于 beam search 的 IPθt(x) 与重排阶段的梯度范数", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["clip", "add_noise"],
  "intervention_where": ["client"],
  "assumptions": [
    "攻击者是被动 honest-but-curious 窃听者，不能修改上传梯度或下发模型",
    "上传的是逐客户端明文梯度，未使用安全聚合或加密（论文仅在相关工作提及密码学防御）",
    "训练会更新词嵌入矩阵，因此词嵌入梯度存在可区分的非零行",
    "训练数据是句级、长度不超过 40 词、绝大多数 token 在词表内（附录 B.1 的过滤条件）",
    "语言模型会记忆训练数据，训练迭代越多攻击越强（图 4）",
    "单服务器单客户端模拟在 IID 数据假设下与 N 客户端同步联邦学习等价（脚注 8）",
    "攻击者掌握与训练相同的模型权重与分词方式，可离线做前向与反向计算"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Sec. 3.3 Adversary's capabilities", "supports": "第 2 节：攻击者是被动窃听者，位于客户端与服务器通信之间", "text": "We consider an honest-but-curious adversary who is eavesdropping on the communication between the central server s and an arbitrary client ci, i ∈[N] in the federated training of a language model parameterized by θ, as described above."},
    {"section": "Sec. 3.3 Adversary's capabilities", "supports": "第 2 节与第 5 节：白盒访问上传梯度与含词嵌入矩阵的全局模型", "text": "An adversary in this scenario has white-box access to 1) the gradients ∇θtLθt(Bi) sent by the client ci, and 2) the model parameters θt (Fig. 1), including the vocabulary V and the embedding matrix W."},
    {"section": "Sec. 3.3 Adversary's objective", "supports": "第 2 节：攻击目标是恢复私有句子，属于隐私窃取", "text": "The adversary aims to recover at least one sentence from the private training data batch Bi based on the information they observe, as recovering a single sentence is already sufficient to break the privacy guarantee of federated learning."},
    {"section": "Sec. 4.2 Bag-of-Words Extraction", "supports": "第 3 节与第 4 节：攻击第一步取词嵌入梯度非零行还原词袋", "text": "We follow the method outlined by Melis et al. (2019) and recover a set of words B = {w1, w2, . . . , wm} by considering the non-zero rows of the word embedding gradients ∇WtLθt(Bi)."},
    {"section": "Sec. 4.3 Beam Search for Sentence Reconstruction", "supports": "第 4 节：beam search 的终止长度与选句准则", "text": "The beam tree continues until the generated sentence reaches a specified length (we use 40 words), and outputs the text that has the overall highest probability (see Fig. 2)."},
    {"section": "Sec. 5 Defending Against the FILM Attack", "supports": "第 6 节与第 9 节：冻结词嵌入通过阻止嵌入梯度传输来切断第一阶段", "text": "In other words, once we prevent the transmission of gradients of word embeddings during training, it is no longer possible to recover the bag-of-words."},
    {"section": "Sec. 6.1 Training and attack settings", "supports": "第 1 节与第 7 节：实验为单服务器单客户端设置", "text": "Following previous studies (Zhu et al., 2019; Geiping et al., 2020; Yin et al., 2021; Huang et al., 2021) for gradient inversion attacks, our evaluation considers a federated learning setting with a single server and a single client."},
    {"section": "Sec. 6.3 Token reconstruction under gradient pruning", "supports": "第 5 节与第 7 节：高剪枝率下攻击仍能恢复绝大多数 token", "text": "However, the attacker can still recover a considerable amount of tokens (i.e. >90%) even with a prune ratio as high as 0.9999."},
    {"section": "Sec. 6.3 Token reconstruction under DPSGD", "supports": "第 9 节：论文针对 DPSGD 设计了自适应的阈值化攻击策略", "text": "For each token, we check the maximum magnitude of its embedding gradients: if the value is larger than τ, then the token may be included in the original batch with high probability."},
    {"section": "Sec. 6.1 Training and attack settings", "supports": "第 8 节：论文报告的攻击计算开销", "text": "We note that the running time of our algorithm is quite fast, and we can recover a single sentence in under a minute using an Nvidia 2080TI GPU."}
  ]
}
```
