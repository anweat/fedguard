# kairouz2019advances：Advances and Open Problems in Federated Learning

## 1. 基本信息

**场景**：传统联邦学习（federated learning，FL），以横向（按样本划分）的跨设备（cross-device）设置为主要讨论对象，同时在第 2 节讨论跨孤岛（cross-silo）、全去中心化（peer-to-peer）、拆分学习（split learning）等变体。论文讨论的是图像分类、键盘下一词预测等一般机器学习任务的传统 FL，**不是联邦大模型（federated LLM）**，也**完全没有涉及参数高效微调（parameter-efficient fine-tuning，PEFT）或 LoRA（low-rank adaptation）**；全文没有出现 LoRA、PEFT 或适配器（adapter）等概念。与"大模型"最接近的内容只是把语言模型作为应用示例提及（例如 Gboard 下一词预测、Shakespeare 与 StackOverflow 语言建模数据集），其训练流程仍是标准 Federated Averaging，而不是大模型微调流水线。

**训练阶段**：论文覆盖模型生命周期的全部阶段（第 1.1.1 节）：问题定义、客户端埋点、模拟原型、联邦训练、联邦评估、部署；并给出典型训练循环（第 1.1.2 节）：客户端选择（client selection）、广播（broadcast）、客户端计算（client computation）、聚合（aggregation）、模型更新（model update）。第 5 节的攻击与防御讨论横跨其中多个阶段。

**论文类型**：综述（survey）。摘要明确说明该文"discusses recent advances and presents an extensive collection of open problems and challenges"。论文没有提出单一的新方法，也没有报告作者自己运行的实验；所有实验性结论都以引用他人工作的方式给出。

**模型与数据规模**：论文给出的是数量级而不是具体模型架构或参数量。表 2：设备总规模 10^6 至 10^10；单轮训练选中的设备 50 至 5000；参与训练一个模型的总设备 10^5 至 10^7；模型收敛所需轮数 500 至 10000；墙钟训练时间 1 至 10 天。表 1：跨设备 FL 可达 10^10 个客户端，跨孤岛 FL 通常 2 至 100 个客户端，数据中心分布式训练通常 1 至 1000 个客户端。附录 A 给出推荐数据集：EMNIST 共 671,585 张图像并划分为 3,400 个不均衡客户端；StackOverflow 训练集有 342,477 个以上唯一用户与 135,818,730 个样本；Shakespeare 训练集 16,068 个样本、测试集 2,356 个样本；Google-Landmark-v2 有超过 500 万张图像与 20 万种以上地标；另有一个包含 900 余张街景图像、来自 26 台相机、7 个类别的小型数据集。论文未说明其讨论的模型架构与参数量（它在引用他人工作时提到卷积神经网络）。

**重要提示（文本完整性）**：所提供的全文在中间被省略，省略位置大致从第 5.4 节执行摘要的后半部分一直延续到参考文献 [225] 之前，因此**第 6 节（公平性与偏差）、第 7 节（系统挑战）、第 8 节（结论）以及参考文献列表的前半部分不在可见文本中**。本报告只依据可见部分作答，对省略部分不作任何判断。

## 2. 威胁模型

论文在表 7 中以行为者（actor）为单位给出威胁模型，共四类：

- **客户端（Clients）**：拥有客户端设备 root 权限的人。恶意客户端可以检查其在参与轮次中从服务器收到的全部消息（包括模型迭代），并且可以篡改训练过程；诚实但好奇（honest-but-curious）的客户端只能查看、不能篡改。第 5.1 节进一步给出攻击者能力维度（表 11）：模型可见性分为黑盒（black box）、陈旧白盒（stale whitebox，只能看到中间轮次的旧模型）与白盒（white box）；串谋分为不串谋、跨更新串谋（cross-update collusion，过去与未来的参与者协调攻击未来更新）与更新内串谋（within-update collusion，当前参与者协调攻击当前更新）；参与率在跨设备设置中通常只有一轮，在跨孤岛设置中多数客户端每轮都参与；适应性分为静态与动态。
- **服务器（Server）**：拥有服务器 root 权限的人。恶意服务器可以检查所有轮次中发送到服务器的全部消息（包括梯度更新），并且可以篡改训练过程；诚实但好奇的服务器只查看、不篡改。第 5.1.1 节另指出，若攻击者能攻陷中心聚合器，就可以轻易实施定向与无目标攻击；第 4.4.1 节指出恶意服务器可以通过 Sybil 攻击（Sybil attack）伪造大量客户端，或优先选择已被攻陷的设备。
- **输出模型的使用者（Engineers and analysts）**：恶意分析师或模型工程师可以访问系统的多个输出，例如不同超参数下多次训练的模型迭代序列。
- **已部署模型（The rest of the world）**：最终模型可能部署到数亿设备，部分被攻陷的设备拥有黑盒访问，完全被攻陷的设备拥有白盒访问。

**攻击者数量与占比**：论文没有给出统一的恶意客户端比例。唯一明确的数值来自对 Bhagoji et al. [67] 的引用：参与联邦学习的设备中有 10% 被攻陷时，即使服务器端存在异常检测器，仍可植入后门（第 5.1.2 节）。第 5.1.1 节说明在跨设备设置中单个恶意客户端可能只参与一轮因而影响有限，而在跨孤岛设置中单个客户端的影响可能"enormous"。

**攻击目标**（第 5.1.1 节）：无目标攻击（untargeted attack）又称模型降级攻击，目标是降低全局精度或"完全破坏"全局模型；定向攻击（targeted attack）又称后门攻击（backdoor attack），目标是在保持其余样本精度的情况下改变少数样本上的行为。论文给出语义后门（semantic backdoor）的例子：让模型把所有绿色汽车分类为鸟。第 5.1.4 节另外讨论推理期逃逸攻击（evasion attack）。第 5 节明确把"推断其他用户私有数据"的攻击归入第 4 节的隐私威胁，不在本节范围。

**防御者是谁、能看到什么、信任什么**：第 4.3 节明确"assume the existence of a trusted server"，即可信服务器负责执行差分隐私（differential privacy，DP）机制：它能看到逐客户端的更新，对其进行裁剪与加噪，只向分析师发布隐私化输出（第 4.2.2、4.3.2 节）。第 4.4 节讨论无 fully trusted server 的情形。在安全聚合（secure aggregation，SecAgg）下，服务器只能看到聚合结果而看不到任何单个客户端的更新（第 4.2.1、5.3 节）。论文反复强调服务器无法查看客户端原始数据（第 5.1.3、5.2 节）。关于"知识"，第 5.1.1 节指出由于模型会被广播给所有参与者做本地训练，通常假定攻击者拥有模型参数的直接访问权，即白盒。

## 3. 攻击入口与流程位置

按第 1.1.2 节的训练循环与表 11 的攻击向量，论文讨论的攻击入口如下。

1. **本地数据准备与客户端本地数据（数据投毒，data poisoning）**：攻击者不直接篡改上报，而是替换标签或特定特征；论文说明这种攻击模型在"攻击者只能影响边缘的数据收集过程"时更自然（第 5.1.3 节）。论文同时指出数据投毒最终也会改变客户端向服务器的输出，因此在该文定义下数据投毒是模型更新投毒的特例（第 5.1.3 节）。
2. **本地训练过程（模型更新投毒的准备）**：攻击者直接控制若干客户端，并可以直接改动这些客户端的输出；Byzantine 客户端可以完全无视规定的客户端损失函数或训练方案，发送任意构造的更新（第 5.1.2 节）。
3. **更新上传阶段（模型更新投毒，model update poisoning）**：论文第 5.4 节执行摘要称这是"联邦学习引入的一类新型投毒攻击"。论文假设攻击者直接操纵发往服务提供方的报告（也考虑中间人攻击，但后续假设直接操纵，因为这样严格增强攻击者能力）。
4. **服务器聚合**：论文指出如果攻击者攻陷中心聚合器，就可以对训练模型实施定向与无目标攻击（第 5.1.1 节），但作者说明该向量与数据中心分布式设置中的情形类似，因此在后文省略讨论。与选择相关的入口还有第 4.4.1 节的 Sybil 攻击与优先选择已攻陷设备，它们作用于服务器选择客户端这一环节。
5. **评估与部署（推理期逃逸攻击）**：攻击者精心扰动送入已部署模型的样本（第 5.1.4 节）；论文还指出训练期攻击可以作为推理期攻击的跳板（第 5.1.2、5.1.4 节）。

**论文未说明的入口**：论文没有把"适配器或模型发布者"当作独立攻击者，也没有讨论参数高效微调供应链中的后门注入；更新上传前的缩放、投影、拼装等具体后处理步骤不是论文的攻击入口，论文只把上传的更新整体视为可被直接篡改的对象。

## 4. 方法原理

这是一篇综述，没有提出单一方法；其"原理"是把联邦学习中的攻击与防御组织成一套分类与工具箱。

- **攻击分类（第 5.1 节与表 11）**：按目标分为无目标与定向；按向量分为数据投毒、模型更新投毒、逃逸攻击；按能力分为模型可见性、串谋、参与率与适应性。论文特别强调 Byzantine 威胁模型（来自分布式系统）是有目标的鲁棒聚合防御所针对的最坏情况。
- **Byzantine 鲁棒聚合（第 5.1.2 节）**：把服务器上的平均步骤替换为对均值的鲁棒估计，例如基于中位数的聚合器、Krum、截断均值（trimmed mean）。论文报告这些方法在"合适的假设"下对 Byzantine 容错分布式学习有可证明的效果，但也报告 Fang et al. [183] 发现多个此类防御在联邦学习中对模型投毒几乎无效。
- **基于差分隐私的防御（第 4.3.2、5.1.5 节）**：服务器对单个客户端的更新做 ℓ2 范数裁剪（clipping），聚合裁剪后的更新，再对聚合结果加入高斯噪声（Gaussian noise）；论文指出这与差分隐私训练完全相同，其作用是限制任何单个客户端对整体模型的影响，从而同时对抗模型更新投毒与数据投毒。DP 的定义见公式 (3)：对任意输出集合 S 与相邻数据集 D 与 D'，有 P(A(D) ∈ S) ≤ e^ε P(A(D') ∈ S) + δ；在 FL 中"相邻"指相差一个客户端（用户级差分隐私，user-level differential privacy）。隐私预算用高级组合定理（advanced composition）或矩 accountant（moments accountant）跨轮跟踪。
- **数据清洗与剪枝（第 5.1.3 节）**：数据清洗（data sanitization）尝试移除被投毒或异常的样本，较新的工作用鲁棒统计并具备对少量离群点的可证明鲁棒性；剪枝（pruning）防御则移除在干净数据上不活跃的激活单元，动机是后门常触发所谓"后门神经元"。
- **隐私保护工具箱（第 4.2 节）**：安全多方计算（secure multi-party computation，MPC）、同态加密（homomorphic encryption，HE）、可信执行环境（trusted execution environment，TEE）、差分隐私、安全聚合、安全洗牌（secure shuffling）、私有信息检索（private information retrieval，PIR）、零知识证明（zero-knowledge proof，ZKP）与远程认证（remote attestation）。
- **可验证性（第 4.2.3 节）**：零知识证明可以让客户端向服务器证明其输入满足某种性质（例如属于某个范围），TEE 与远程认证可以让客户端验证服务器上的关键函数（安全聚合、洗牌、加噪）被忠实执行。
- **流程骨架（第 3.2 节，算法 1）**：Federated Averaging 每轮采样 M 个客户端，每个客户端在本地数据上执行 K 步随机梯度下降，服务器对返回的本地模型取平均。这是判断攻击与防御发生在哪一步的基础。

论文没有给出把鲁棒聚合与差分隐私组合起来的统一算法，也没有给出专门的后门检测器。

## 5. 检测或防御所需的数据

**（一）防御方法的输入清单**

1. **每个客户端上传的模型更新或梯度**。采集位置：服务器收到更新时（server_receive）。粒度：逐客户端、逐轮、整个参数向量（需要时可按层拆分）。是否需要跨轮历史：鲁棒聚合本身只依赖本轮；但论文把跨更新串谋列为现实威胁（表 11）。是否需要干净参考数据：否。是否需要额外计算：计算鲁棒统计量（中位数、截断均值、Krum 的距离矩阵）需要额外的服务器计算，论文未给出其复杂度。
2. **单个客户端更新的 ℓ2 范数**。采集位置：服务器收到更新时。粒度：逐客户端、逐轮。用途：差分隐私裁剪。需要额外计算（求范数）。论文未说明是否需要跨轮历史。关键限制：在安全聚合下服务器看不到单个更新，因此无法直接获得逐客户端范数（第 5.3 节）；论文提出的兼容方向是用范围证明（range proof，例如 Bulletproofs）证明裁剪被正确执行，并指出高效的范围证明仍是活跃研究方向。
3. **聚合后的更新与聚合后的全局模型**。采集位置：服务器聚合时与聚合后（server_aggregate、server_post_aggregate）。粒度：逐轮、模型级。第 1.1.2 节明确把聚合阶段描述为安全聚合、有损压缩、加噪与更新裁剪的集成点。
4. **跨轮的模型迭代序列**。采集位置：服务器聚合后，以及客户端在参与轮次中收到的模型。粒度：逐轮、模型级。表 7 指出恶意客户端能看到其参与轮次中的全部消息（含模型迭代），恶意分析师能看到多次训练运行的模型迭代序列；第 4.3.1 节建议用代理（审计）数据集模拟攻击，量化迭代与最终模型对攻击的易感性。
5. **干净参考数据、留存数据（holdout）或代理审计数据集**。采集位置：服务器端评估阶段。粒度：数据集级或样本级。第 5.1.3 节明确指出剪枝类防御需要"clean holdout data that is representative of the global dataset"，数据清洗类防御通常需要访问客户端数据或与之相似的数据；论文强调这两者在联邦学习中一般不可得。
6. **客户端本地原始数据**。采集位置：客户端训练前与训练中（client_pre_train、client_step）。粒度：逐样本。论文强调这类数据不离开设备、服务器不可见（第 1 节定义与第 5.2 节）。数据投毒恰好发生在这一位置，因此其痕迹在服务器端不可直接观察。
7. **模型内部激活单元**。采集位置：服务器聚合后的全局模型。粒度：逐层、逐单元（论文用 activation units 表述）。用于剪枝类后门防御，且需要干净数据作为对照。
8. **客户端参与与采样记录、隐私预算账本**。采集位置：服务器收到更新时及轮次之间。粒度：逐客户端、逐轮。需要跨轮历史。第 4.3.2 节说明需要跨轮跟踪隐私预算，并指出跨设备 FL 中合格用户集合动态变化、用户可能随时掉线，因此需要"自记账"（self-accounting）的协议，即服务器只用协议中可得的信息就能算出紧的 (ε, δ)。
9. **分布式差分隐私场景下的中间量**：客户端本地编码或加噪后的聚焦报告，以及安全聚合或安全洗牌的中间结果。采集位置：客户端训练后（客户端侧自己可见）与服务器收到时（服务器只能看到聚合结果）。粒度：逐客户端与逐轮聚合。见第 4.2.2 与 4.4.3 节。
10. **部署模型的查询输入输出，以及全局与逐客户端训练准确率**。采集位置：评估与部署。粒度：逐样本、逐客户端、逐轮。第 4.3.5 与 5.1.4 节讨论模型窃取与逃逸攻击；第 5.1.3 节指出训练准确率这类指标可能不足以检测后门的存在。

**（二）攻击留下的痕迹与论文声称能绕过的检测**

论文报告后门更新在数值与行为上与未受定向攻击训练得到的模型"look and (largely) behave similarly"，使检测后门是否存在非常困难（第 5.1.2 节）；表 11 指出白盒访问下 Byzantine 客户端可以调整输出，使其方差与幅度接近正确更新，从而难以检测。论文报告的绕过结果包括：Fang et al. [183] 发现多个 Byzantine 鲁棒防御对模型投毒几乎无效；Koh et al. [276] 发现许多基于数据清洗的启发式防御仍可被自适应投毒攻击攻破；Wang et al. [466] 表明用分布中低概率样本构造的边缘案例后门（edge-case backdoor）可以绕过差分隐私防御。另一方面论文主张，能有效对抗白盒模型更新投毒的防御必然也能对抗黑盒与数据投毒攻击（第 5.1.1 节）。

## 6. 干预动作

- **替换聚合规则（发生在服务器聚合阶段）**：用鲁棒均值估计（中位数类聚合器、Krum、截断均值）取代平均，以降低异常更新的影响（第 5.1.2 节）。论文没有说明这些方法是显式剔除客户端还是只改变权重。
- **裁剪（发生在服务器聚合阶段）**：对每个客户端的更新做 ℓ2 范数裁剪（第 4.3.2、5.1.5 节）。
- **加噪（中心 DP 时在服务器聚合阶段，本地 DP 时在客户端上报之前）**：对裁剪后的聚合结果加入高斯噪声（第 4.3.2 节）；本地差分隐私（local differential privacy，LDP）由客户端自行加噪（第 4.2.2 节）；分布式 DP 由客户端编码后经安全计算函数聚合（第 4.2.2 节）。
- **过滤样本**：数据清洗移除被投毒或异常的训练数据（第 5.1.3 节）；论文强调这需要数据访问，在联邦设置中通常不可行。
- **修复模型（发生在服务器端对全局模型的操作）**：剪枝移除在干净数据上不活跃的激活单元以消除后门（第 5.1.3 节）。
- **剔除客户端**：论文提到 Byzantine 客户端与服务器端异常检测器（第 5.1.2 节），并在第 1.1.2 节说明服务器在收到足够结果后可以丢弃掉队者（straggler）；后者是效率考虑而非安全防御。
- **回滚**：第 1.1.1 节第 6 步的模型上线流程包含分阶段发布（staged rollout），以便在影响过多用户之前发现并回滚不良行为；这是部署流程层面的动作，论文没有把它与投毒防御直接关联。
- **仅报告与验证**：第 4.3.1 节建议通过审计量化模型对攻击的易感性，为"on-the-fly"的自适应防御提供依据；第 4.2.3 节的零知识证明与远程认证用于证明各方忠实执行协议，论文将其列为开放方向而非已部署动作。

论文没有讨论检测到投毒后的重训、回滚到上一轮全局模型、或对客户端做信誉惩罚，也没有给出任何动作的触发阈值。

## 7. 实验设置与主要结果

**论文本身没有实验**。它是一篇综述，没有统一的模型、数据集、客户端数、参与率、轮次、恶意比例或 non-IID 设置，全部结果均以引用形式给出。可见正文中引用的关键结果如下。

- 第 5.1.2 节：Bhagoji et al. [67] 表明参与联邦学习的设备中有 10% 被攻陷时，即使服务器存在异常检测器，仍能通过投毒回传模型植入后门；该文还报告被投毒的模型更新与未受定向攻击的模型在外观与行为上大体相似。
- 第 5.1.2 节：Bagdasaryan et al. [44] 表明单次攻击（single-shot）即可植入后门，并给出语义后门的例子（把所有绿色汽车分类为鸟）。
- 第 5.1.2 节：Fang et al. [183] 发现多个 Byzantine 鲁棒防御在联邦学习中对模型投毒攻击几乎无效；作者据此呼吁更多实证分析，因为理论保证依赖的假设在实际问题中往往不成立。
- 第 5.1.2 节：在联邦元学习（federated meta-learning）中，一次性攻击植入的后门被报告可以持续数十个训练轮次 [109]；联邦学习被报告对定向与无目标的 Sybil 攻击都脆弱 [190]。
- 第 5.1.3 节：Byzantine 鲁棒聚合器在卷积神经网络上成功防御了标签翻转（label-flipping）数据投毒攻击 [487, 484, 486]。
- 第 5.1.5 节：Sun et al. [438] 报告差分隐私用作定向攻击防御的初步成功，但作者认为其攻击与实验范围需要扩展；Wang et al. [466] 表明边缘案例后门可以绕过差分隐私防御，并论证对抗样本的存在蕴含边缘案例后门的存在。
- 第 4.3.2 节：在中等隐私预算且缺乏足够大数据集时，加噪会导致模型精度大幅下降。
- 表 5 与表 6：IID 与非 IID 设置下各联邦优化算法的收敛率上界；论文据此指出当 T = 10^6、M = 100（与表 2 对应）时 K = 1，并指出目前没有联邦平均类算法能匹配加速小批量 SGD 的收敛率。
- 第 3.1 节：非独立同分布（non-IID）被划分为特征分布偏移、标签分布偏移、概念漂移、概念偏移与数量不均衡；多数合成非 IID 数据集的实证工作集中在标签分布偏移。论文未给出投毒实验中的 non-IID 设置，因为它没有自己的实验。

## 8. 开销

论文以综述方式报告（转述引用工作的数值或结论，而非自己测量）：

- 表 1：通信通常是跨设备 FL 的首要瓶颈（computation 或 communication 在跨孤岛设置中均可能成为瓶颈）。
- 第 3.5 节：应用 Bonawitz et al. [80] 与 Bell et al. [58] 的安全聚合协议时，每个标量需要额外约 O(log M) 比特的通信，其中 M 是被求和的客户端数，这可能使激进的量化失效；Bell et al. [58] 的安全聚合可扩展到数十亿参与方。
- 第 3.5 节：压缩有三个互补目标，即梯度压缩、模型广播压缩与本地计算削减；客户端上行带宽通常低于下行，因此梯度压缩的潜在收益最大。
- 第 4.2.3 节：零知识证明目前可达到数百字节的证明大小与毫秒量级的验证时间，且与所证明陈述的规模无关；SNARK 的证明者计算量在电路规模上通常是超线性的，Libra 实现了线性证明者复杂度但增大了证明大小与验证时间；为 FL 服务器的工作生成证明时输入规模会很大。
- 第 4.2.1 节：把 MPC 协议移植到跨设备设置并不容易，因为它们需要大量通信。
- 第 4.4.3 节：一种分布式离散高斯机制被报告在每数值 16 比特（或更少）精度下达到与中心 DP 连续高斯噪声相当的精度。
- 第 3.2.1 节：Bonawitz et al. [81] 建议超额配置客户端（例如请求 1.3M 个客户端），然后接受最先到达的 M 个更新。
- 第 5.1.2 节：基于冗余与数据打乱的防御会增加通信成本，与 FL 降低通信成本的目标相冲突。
- 第 5.1.4 节：对抗训练（adversarial training）需要多轮训练与额外计算，在跨设备场景可能加剧内存与功耗约束。
- 第 4.3.2、4.4.2、4.4.3 节：加噪带来精度损失；本地 DP 与洗牌模型的隐私与效用权衡被反复讨论。

**论文未报告**：Krum、中位数、截断均值等具体鲁棒聚合的时间与通信开销；数据清洗与剪枝防御的具体计算开销；上述防御在真实跨设备规模下的开销测量。这些在可见全文中均未给出。

## 9. 假设、局限与自适应攻击

**论文自述的假设与局限**

- 攻击与防御的适用性依赖表 1 的设置差异：跨设备 FL 中客户端不可被直接索引、无状态、通常只参与一次，并且一轮中预计有 5% 以上的客户端失败或掉线；跨孤岛 FL 中客户端少而稳定，多数每轮参与。论文明确指出同一攻击在不同设置下影响差别巨大（第 5.1.1 节）。
- Byzantine 鲁棒聚合的理论保证依赖"appropriate assumptions"，这些假设在实际学习问题中往往不成立（第 5.1.2 节）。
- 数据清洗与剪枝类防御需要访问客户端数据或代表全局分布的干净留存数据，这在联邦学习中一般不可得（第 5.1.3 节）。
- 差分隐私防御的前提是攻击者只能控制少量设备；其背后的群体隐私（group privacy）保护随被攻击点数量指数衰减（第 5.1.5 节脚注 10）。
- 安全聚合假设在私钥基础设施阶段服务器是半诚实（semi-honest）的，允许服务器看到逐轮聚合（仍可能泄露信息），对稀疏向量聚合效率低，并且无法强制客户端输入的良构性（well-formedness）（第 4.4.2 节）。
- 洗牌模型需要可信中介，且其差分隐私保证随对抗用户数量增加而退化（第 4.4.2 节）。
- 中心 DP 需要可信服务器；本地 DP 在高维数据上保持效用困难（第 4.2.2、4.4.2 节）。
- Sybil 攻击会破坏 MPC 关于诚实设备比例的常见假设；即使协议本身安全，若大量对抗客户端的更新被攻击者知晓或控制，其余客户端的隐私也可能被削弱（第 4.4.1 节）。
- 论文明确指出多处尚未系统研究的问题，例如：数据投毒防御是否必须在联邦场景下重新设计、哪些聚合器可以在安全聚合下计算（第 5.3 节）、如何量化数据投毒与模型更新投毒之间的差距（第 5.1.3、5.4 节）。

**是否评估自适应攻击者**：论文把适应性（adaptability）列为攻击者能力的独立维度，区分静态与动态攻击，并说明在联邦学习中只有客户端能多次参与时适应性才有意义（表 11）。论文报告了自适应攻击的结果：Koh et al. [276] 表明许多基于数据清洗的启发式防御仍可被自适应投毒攻击攻破，甚至联邦化的数据清洗也可能不足；Wang et al. [466] 表明边缘案例后门可以绕过差分隐私防御；Bhagoji et al. [67] 的攻击在服务器端异常检测器存在时仍然成功。论文没有自己运行自适应攻击实验。

**迁移到联邦 LoRA 微调时可能失效的假设（分析：以下均为我的分析，论文未涉及 LoRA 或大模型）**

- 分析：论文默认客户端广播并训练完整模型参数，更新是满参数空间中的向量；LoRA 的更新是低秩因子矩阵，其欧氏范数、坐标分布与参数维度都与满参数更新差异很大，中位数、Krum、截断均值这类基于逐坐标统计或欧氏距离的鲁棒聚合是否仍然有效，论文没有依据。
- 分析：论文把安全聚合当作对"求和"这一线性原语的封装；LoRA 增量在服务器端通常需要以加权和或其他合并方式处理，非线性合并在安全聚合下的可行性论文只作为开放问题提出，没有结论。
- 分析：论文的差分隐私分析针对逐样本或逐用户的梯度贡献，裁剪阈值与噪声标定依赖模型维度与更新范数的量级；把同样机制套到 LoRA 因子上需要重新标定敏感度，论文没有给出依据。
- 分析：论文的核心场景是客户端数量极大、每轮只采样 50 至 5000 个、客户端大多只参与一次的跨设备 FL（表 1、表 2）；联邦大模型微调常常是跨孤岛、客户端数量在几十量级、每轮几乎全参与，此时单个恶意客户端的影响远大于论文对跨设备场景的判断，论文"单个客户端可能无关紧要"的论断不再成立。
- 分析：论文讨论的后门触发是图像伪影、标签翻转与语义后门；大模型微调中的后门通常是文本触发器或对安全对齐的破坏，这类目标论文完全没有覆盖，"后门神经元"式剪枝在 Transformer 结构上是否成立也缺乏依据。
- 分析：论文默认客户端能白盒访问广播的模型；在只下发适配器的设置中可见性模型会改变，但论文没有讨论这种供应链设置。
- 分析：论文的 non-IID 分类基于特征分布与标签分布，适用于图像与键盘数据；大模型微调中提示分布、任务分布与安全策略分布的偏移不在该分类的覆盖范围内。

## 10. 对防护库设计的含义

分析：以下全部为我的分析。

1. **通用采集点**：库至少需要在服务器收到更新时（server_receive）保存逐客户端的更新对象、逐客户端范数、客户端句柄与参与轮次；在聚合时与聚合后保存聚合结果与全局模型快照；在客户端侧保存本地训练前后的模型或适配器以及本地数据统计量。这些正对应论文第 1.1.2 节训练循环与表 11 攻击向量所刻画的信任边界，属于与具体攻击无关的底座需求，应做成默认开启的采集能力。
2. **"服务器能看什么"是一等设计约束**：论文第 5.3 节说明当安全聚合使服务器只能看到聚合结果时，许多防御无法实现。库应把服务器视图抽象为"逐客户端更新可见"与"仅聚合结果可见"两种，并允许插件声明其所需视图，从而让不兼容的组合在装配期就被拒绝，而不是运行期静默失效。
3. **干净参考数据应作为可注入的插件资源**：论文第 5.1.3 节指出剪枝与清洗类防御需要代表全局分布的干净留存数据。库应把参考数据集做成插件依赖项，并显式标注哪些插件在没有它时无法运行；这在联邦 LoRA 场景中通常是稀缺资源。
4. **鲁棒聚合与差分隐私应作为两类可复用的服务器钩子**：前者替换聚合规则（中位数、Krum、截断均值），后者按固定顺序执行逐客户端裁剪、聚合与加噪。库的服务器钩子需要支持在聚合前后插入动作，并把隐私预算账本作为跨轮状态管理（论文第 4.3.2 节的组合定理与矩 accountant）。
5. **跨轮历史应默认保留、按需暴露**：论文把跨更新串谋列为攻击者能力（表 11），DP 需要跨轮记账，迭代审计需要多轮模型快照。库应默认保留轻量的跨轮元数据（更新摘要、参与记录、模型指纹），并允许插件按需读取历史，而不是只提供单轮视图。
6. **论文特有与通用需求的区分**：Byzantine 鲁棒聚合需要逐客户端完整更新向量与两两距离矩阵，DP 防御需要逐客户端范数与可加噪的聚合原语，这两者属于论文直接支持的、可做成通用服务器插件的需求；数据清洗与剪枝需要本地数据或干净留存数据，属于高门槛插件，在联邦 LoRA 场景多半不可用。论文没有给出任何针对大模型或 LoRA 的采集点定义，因此面向 LoRA 的专用视图（逐层低秩因子、适配器范数、适配器差异）必须自行设计，不能从本文直接推导。

## 11. 原文依据

1. **Abstract**（支撑第 1 节的场景判断：这是传统联邦学习而非联邦大模型）
   > "Federated learning (FL) is a machine learning setting where many clients (e.g. mobile devices or whole organizations) collaboratively train a model under the orchestration of a central server (e.g. service provider), while keeping the training data decentralized."

2. **Section 1.1.2, Step 4 (Aggregation)**（支撑第 3 节"服务器聚合"入口与第 6 节的动作发生位置）
   > "The server collects an aggregate of the device updates. For efficiency, stragglers might be dropped at this point once a sufficient number of devices have reported results."

3. **Section 4.3.2**（支撑第 4 节与第 6 节的差分隐私防御原理：先裁剪再聚合再加噪）
   > "With this technique, the server clips the ℓ2 norm of individual updates, aggregates the clipped updates, and then adds Gaussian noise to the aggregate. This ensures that the iterates do not overfit to any individual user's update."

4. **Section 5.1.2**（支撑第 4 节与第 6 节的 Byzantine 鲁棒聚合方法清单）
   > "One popular defense mechanism against untargeted model update poisoning attacks, especially Byzantine attacks, replaces the averaging step on the server with a robust estimate of the mean, such as median-based aggregators [116, 497], Krum [76], and trimmed mean [497]."

5. **Section 5.1.2**（支撑第 2 节与第 7 节中唯一的恶意比例数值 10% 及异常检测器被绕过的结论）
   > "Bhagoji et al. [67] shows that if 10% of the devices participating in federated learning are compromised, a backdoor can be introduced by poisoning the model sent back to the service provider"

6. **Section 5.1.2**（支撑第 5 节"攻击留下的痕迹"：后门更新在数值与行为上与正常模型相似）
   > "Interestingly, the poisoned model updates look and (largely) behave similarly to models trained without targeted attacks, highlighting the difficulty of even detecting the presence of a backdoor."

7. **Section 5.1.3**（支撑第 5 节"需要干净参考数据"以及第 10 节把它做成插件依赖的建议）
   > "While such methods do not require direct access to all client data, they require "clean" holdout data that is representative of the global dataset."

8. **Section 5.1.3**（支撑第 9 节"评估了自适应攻击者"：自适应投毒可攻破数据清洗防御）
   > "Koh et al. [276] recently showed that many heuristic defenses based on data sanitization remain vulnerable to adaptive poisoning attacks, suggesting that even a federated approach to data sanitization may not be enough to defend against data poisoning."

9. **Section 5.3**（支撑第 5 节与第 10 节关于安全聚合限制服务器可见性、使防御难以实现的论断）
   > "While useful for ensuring privacy, SecAgg generally makes defenses against adversarial attacks more difficult to implement, as the central server only sees the aggregate of the client updates."

10. **Section 5.1.2**（支撑第 9 节关于 Byzantine 鲁棒防御在联邦学习中失效的局限）
    > "Despite this, Fang et al. [183] recently showed that multiple Byzantine-resilient defenses did little to defend against model poisoning attacks in federated learning."

```json
{
  "key": "kairouz2019advances",
  "title": "Advances and Open Problems in Federated Learning",
  "year": 2019,
  "paper_type": "survey",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client", "malicious_server", "data_provider", "external"],
  "attack_goal": ["untargeted", "backdoor", "privacy", "other"],
  "attack_entry": ["local_data", "local_training", "update_postprocess", "server_aggregation", "evaluation_deployment"],
  "observables": [
    {"what": "每个客户端上传的模型更新或梯度（完整参数向量）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "单个客户端更新的 ℓ2 范数（用于差分隐私裁剪）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "聚合后的更新与聚合后的全局模型", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "跨轮的模型迭代序列（用于审计与隐私记账）", "where": "server_post_aggregate", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "代表全局数据分布的干净留存数据或代理审计数据集", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "客户端本地原始训练数据（数据投毒发生处，服务器不可见）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "全局模型内部激活单元（用于剪枝类后门防御）", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "客户端参与与采样记录、跨轮隐私预算账本", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "分布式差分隐私下客户端本地编码或加噪后的报告，以及安全聚合或安全洗牌的中间结果", "where": "client_post_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "部署模型的查询输入输出，以及全局与逐客户端训练准确率", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["exclude_client", "reweight", "clip", "add_noise", "filter_samples", "repair_model", "rollback", "report_only"],
  "intervention_where": ["both"],
  "assumptions": [
    "跨设备 FL 中客户端不可索引、无状态、多数只参与一次，且单轮有 5% 以上掉线（表 1、表 2）",
    "中心差分隐私场景假设服务器可信，可逐客户端裁剪与加噪（第 4.2.2、4.3.2 节）",
    "安全聚合假设私钥阶段服务器半诚实，且服务器只能看到逐轮聚合结果（第 4.4.2 节）",
    "剪枝与数据清洗防御需要代表全局分布的干净留存数据或客户端数据（第 5.1.3 节）",
    "差分隐私防御仅在攻击者控制少量设备时有效，群体隐私保护随被攻击点数量指数衰减（第 5.1.5 节脚注 10）",
    "Byzantine 鲁棒聚合的可证明保证依赖实际中往往不成立的假设（第 5.1.2 节）",
    "洗牌模型需要可信中介，隐私保证随对抗用户数增加而退化（第 4.4.2 节）"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节场景判断：传统联邦学习而非联邦大模型", "text": "Federated learning (FL) is a machine learning setting where many clients (e.g. mobile devices or whole organizations) collaboratively train a model under the orchestration of a central server (e.g. service provider), while keeping the training data decentralized."},
    {"section": "Section 1.1.2, Step 4 (Aggregation)", "supports": "第 3 节服务器聚合入口与第 6 节干预位置", "text": "The server collects an aggregate of the device updates. For efficiency, stragglers might be dropped at this point once a sufficient number of devices have reported results."},
    {"section": "Section 4.3.2", "supports": "第 4 节与第 6 节差分隐私防御原理：逐客户端裁剪、聚合、加噪", "text": "With this technique, the server clips the ℓ2 norm of individual updates, aggregates the clipped updates, and then adds Gaussian noise to the aggregate. This ensures that the iterates do not overfit to any individual user's update."},
    {"section": "Section 5.1.2", "supports": "第 4 节与第 6 节 Byzantine 鲁棒聚合方法清单", "text": "One popular defense mechanism against untargeted model update poisoning attacks, especially Byzantine attacks, replaces the averaging step on the server with a robust estimate of the mean, such as median-based aggregators [116, 497], Krum [76], and trimmed mean [497]."},
    {"section": "Section 5.1.2", "supports": "第 2 节与第 7 节唯一的恶意比例数值 10% 及异常检测器被绕过", "text": "Bhagoji et al. [67] shows that if 10% of the devices participating in federated learning are compromised, a backdoor can be introduced by poisoning the model sent back to the service provider"},
    {"section": "Section 5.1.2", "supports": "第 5 节攻击留下的痕迹：后门更新与正常模型相似，难以检测", "text": "Interestingly, the poisoned model updates look and (largely) behave similarly to models trained without targeted attacks, highlighting the difficulty of even detecting the presence of a backdoor."},
    {"section": "Section 5.1.3", "supports": "第 5 节干净参考数据需求与第 10 节插件依赖设计", "text": "While such methods do not require direct access to all client data, they require \"clean\" holdout data that is representative of the global dataset."},
    {"section": "Section 5.1.3", "supports": "第 9 节自适应攻击者评估：自适应投毒可攻破数据清洗防御", "text": "Koh et al. [276] recently showed that many heuristic defenses based on data sanitization remain vulnerable to adaptive poisoning attacks, suggesting that even a federated approach to data sanitization may not be enough to defend against data poisoning."},
    {"section": "Section 5.3", "supports": "第 5 节与第 10 节安全聚合限制服务器可见性、使防御难以实现", "text": "While useful for ensuring privacy, SecAgg generally makes defenses against adversarial attacks more difficult to implement, as the central server only sees the aggregate of the client updates."},
    {"section": "Section 5.1.2", "supports": "第 9 节 Byzantine 鲁棒防御在联邦学习中失效的局限", "text": "Despite this, Fang et al. [183] recently showed that multiple Byzantine-resilient defenses did little to defend against model poisoning attacks in federated learning."}
  ]
}
```
