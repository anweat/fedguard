# li2020backdoorsurvey：Backdoor Learning: A Survey

## 1. 基本信息

- **场景**：这是一篇以后门学习（backdoor learning）为对象的综述（survey），主体覆盖集中式训练（centralized training）下的深度神经网络后门攻击与防御，任务以图像分类为主，另有一小节文献涉及联邦学习、迁移学习、自然语言处理、图神经网络、语音、强化学习等（第三-D 节）。论文没有涉及联邦大模型（federated large language model）或参数高效微调（parameter-efficient fine-tuning，PEFT）/低秩适配（low-rank adaptation，LoRA）。因此按你的分类，它既不是传统联邦学习专论，也不是联邦大模型微调论文，而是覆盖集中式训练为主的通用后门综述。作者信息与版本：Yiming Li、Yong Jiang、Zhifeng Li、Shu-Tao Xia，arXiv:2007.08745v5，标注日期为 2022 年 2 月 16 日，最初版本为 2020 年。
- **训练阶段**：论文开篇把 DNN 训练拆成数据收集、数据预处理、模型选择与构建、训练、模型保存、模型部署等步骤，并指出"更多步骤意味着攻击者更多机会"（第一节）。投毒式后门攻击主要发生在数据收集与训练阶段；非投毒式后门攻击（权重型与结构修改型）发生在模型保存、第三方模型提供与部署阶段（第四节）。
- **论文类型**：综述（survey）。它提出的是分析框架与分类法，不提出新的攻击或防御算法。
- **模型与数据规模**：论文没有统一的实验，因此没有单一模型与数据规模。它报告的一处具体规模是：Rakin 等人提出的 targeted bit trojan（TBT）在 CIFAR-10 上误导 ResNet-18，用 8800 万个权重比特中的 84 个比特翻转实现（第四-A 节，被引文献 [20]）。第七节表五汇总了图像识别基准数据集及其规模，包括 MNIST（28×28，60,000 训练/10,000 测试）、Fashion MNIST（28×28，60,000/10,000）、CIFAR（32×32×3，50,000/10,000）、SVHN（32×32×3，73,257/26,032）、ImageNet（224×224×3，1,281,167/50,000）、GTSRB（34,799/12,630）、U.S. Traffic Sign（6,889/1,724）以及 YouTube Face、PubFig、VGGFace、VGGFace2、LFW 等人脸数据（表五）。

## 2. 威胁模型

- **攻击者是谁**：论文用三个经典场景刻画攻击者角色（第二-B 节与表一）。场景一是"采用第三方数据集"，攻击者是数据提供方，直接或通过互联网提供中毒数据集；场景二是"采用第三方平台"，攻击者是恶意训练平台；场景三是"采用第三方模型"，攻击者是通过应用程序接口（application programming interface，API）或互联网提供已感染模型的模型提供方。在联邦学习相关文献引用中，攻击者是联邦学习中的节点（第三-D 节引 [54]、[95]、[96]）。论文没有给出统一的恶意客户端占比或数量，这一点论文未说明。
- **能力（能改什么）**：表一给出能力矩阵。场景一中攻击者只能操作训练集，不能改模型、训练计划与推理流程，而防御者可以操作全部环节，例如清洗中毒数据集；场景二中攻击者（恶意平台）可以在实际训练过程中修改数据集与训练计划，但不能改模型结构，否则用户会察觉，而防御者不能控制训练集与训练计划，但可以修改训练好的模型；场景三中攻击者除推理流程外可以改一切，防御者能控制推理流程，若拿到模型源文件还能修改模型，若只能访问模型 API 则不能修改模型。论文明确写道，从场景一到场景三攻击者能力递增、防御者能力递减，并且为前一场景设计的攻击也能发生在后续场景中，为后续场景设计的防御也能用于前面的场景。
- **知识（知道什么）**：表二给出白盒与黑盒的区分，白盒攻击指训练集 Dt 已知，黑盒攻击指 Dt 未知。论文指出实际中训练集通常因隐私或版权原因不共享，因此黑盒攻击比白盒攻击更现实（第三-C8 节）。
- **目标**：论文把后门攻击定义为让被感染模型在良性样本上表现正常，而在触发器激活时把预测恶意且一致地改变为目标标签（第一节）。表二区分一对一攻击（所有中毒样本同一目标标签）与一对多攻击（不同中毒样本可有不同目标标签，例如标签移位函数 S(y) = (y+1) mod K）。论文比较表（表三）明确指出后门攻击与经典数据中毒的目标不同：经典数据中毒降低模型泛化，后门攻击保持良性样本性能。论文没有讨论越狱（jailbreak）或安全对齐破坏，这类概念在论文中未说明。隐私不是后门攻击的目标，但论文提到训练集因隐私与版权原因不共享。论文还用一整小节讨论后门的正面用途，包括模型水印与所有权验证、数据删除验证、蜜罐式对抗防御、开源数据集保护等（第三-E 节）。
- **防御者是谁、能看到什么、信任什么**：防御者是采用第三方数据集、平台或模型的用户（受害者）。按表一，场景一防御者可控制训练集、训练计划、模型与推理流程；场景二防御者不能控制训练集与训练计划，只能修改训练好的模型，论文举例说可以在一小份本地良性数据集上微调；场景三防御者控制推理流程，拥有模型源文件时可修改模型。论文隐含的信任关系是：用户信任第三方数据集、第三方平台或第三方模型这些环节不受自己控制，而防御方法正是针对这种失控建立。

## 3. 攻击入口与流程位置

论文是综述，本身不提出攻击，以下是被它归纳的攻击入口与操作步骤。

- **本地数据准备（投毒式攻击的主要入口）**：BadNets（第三-C1 节）的流程分两步，第一是"通过把后门触发器印在选定的良性图像上生成中毒图像，得到中毒样本 (x′, yt)，并关联攻击者指定的目标标签 yt"，第二是"发布同时包含中毒样本与良性样本的中毒训练集给受害者训练自己的模型"。图一给出的例子是右下角黑色方块作为触发器、目标标签为 0；图四给出的可见攻击例子是右下角白色方块。此外还有不可见攻击（第三-C2 节，混合策略、像素扰动、ℓp 范数正则化、反射、扭曲、频域、隐写等）、干净标签攻击（先修改目标类良性图像再执行标准不可见攻击）、语义攻击（第三-C4 节，例如把带绿色或赛车条纹的汽车都标成攻击者指定标签）、物理攻击（第三-C6 节，眼镜、便利贴等物理触发器）、样本特定攻击（第三-C5 节，不同中毒样本携带不同触发器）以及黑盒攻击（第三-C8 节，先合成替代训练样本再注入后门）。
- **本地训练过程**：论文提到 [42] 把后门攻击视为一种特殊的多任务学习，通过"投毒损失计算"实现不可见性（第三-C2 节）；[50] 通过操纵训练样本顺序在不改动样本的情况下注入后门（第三-C2 节）。
- **更新上传前的后处理**：在联邦学习部分，论文描述 [54] 通过"放大节点服务器的中毒梯度"实施后门攻击（第三-D 节），这是对本地更新做缩放后再上传的操作；[95] 的隐蔽模型投毒攻击与 [96] 的分布式后门攻击也被引用，但论文未说明其具体机制。
- **服务器聚合**：论文没有说明直接操纵聚合规则的攻击，只引用 [97] 的理论结论，即在联邦学习中若模型对对抗样本脆弱，在温和条件下后门攻击不可避免（第三-D 节），并引用 [99]、[100] 关于特征分割协作学习与纵向联邦学习的后门、[98] 关于元联邦学习的后门。论文还引用 [101]、[30]、[102]、[103] 质疑联邦学习是否真的容易被攻击。
- **全局模型下发**：论文未说明针对下发环节的攻击。
- **评估与部署**：非投毒式攻击在此进入。权重型攻击直接修改模型参数，包括对预训练权重做贪心搜索扰动、比特翻转、对抗权重扰动（第四-A 节，引 [19]、[20]、[21]、[52]、[115]）；TrojanNet 把后门编码为秘密的权重置换，并证明判定模型是否含触发后门的置换是 NP 完全问题（第四-A 节，引 [116]）。结构修改型攻击通过插入恶意子网络或恶意载荷、或直接替换一个窄子网来植入后门，其中 [24] 被描述为部署阶段的后门攻击（第四-B 节，引 [22]、[23]、[24]）。供应链式的入口还包括迁移学习与预训练模型，论文引用 [16]、[17]、[18]、[104]、[105]，其中 [105] 是针对预训练自然语言处理基础模型的任务无关后门。

## 4. 方法原理

论文的核心贡献是对投毒式后门攻击给出统一框架，并对防御给出统一分类。

- **统一攻击框架（第三-A 节）**：分类器记为 fw，预测标签记为 C(x)。攻击者指定带触发器 t 的中毒图像生成器 Gt 与标签移位函数 S。论文定义三种风险：标准风险 Rs 衡量被感染模型对良性样本是否预测正确（公式 1）；后门风险 Rb 衡量带触发器样本是否被预测为 S(y)（公式 2）；可感知风险 Rp 衡量中毒样本是否可被人或机器检测（公式 3）。三者合成一个优化问题（公式 4）：在触发器 t 与模型参数 w 上最小化 Rs(Dt 减去 Ds) 加上 λ1 乘 Rb(Ds) 再加上 λ2 乘 Rp(Ds)，其中 λ1、λ2 为非负权衡超参数，Ds 是 Dt 的子集，|Ds| 除以 |Dt| 被称为中毒率（poisoning rate）。
- **框架的归约关系**：论文指出当 λ1 取 |Ds| 除以 |Dt 减 Ds|、λ2 取 0 且触发器非优化（触发器集合大小为 1）时，该优化退化为 BadNets 与混合攻击；当 λ2 取正无穷且可感知指示函数取"扰动不超过 ϵ"时，退化为 ϵ 有界的不可见后门攻击。论文还说明由于指示函数不可微，实践中用交叉熵、KL 散度等代理损失替代。
- **分类维度（图三与表二）**：触发器可见性（可见与不可见，不可见再分干净标签与中毒标签）、攻击空间（数字与物理）、目标类型（一对一与一对多）、数据集可达性（白盒与黑盒）、触发器外观（语义与非语义）、触发器选择（优化与非优化）、触发器类型（样本无关与样本特定）。
- **优化式攻击（第三-C3 节）**：把攻击写成双层优化，外层在模型参数上最小化三项风险之和，内层在触发器上最小化后门风险；论文指出优化式攻击通常泛化差，容易过拟合特定模型结构或模型状态。
- **防御原理（第六节与图五）**：论文把投毒式后门攻击类比为用钥匙开锁，认为攻击成立需要三个不可缺少的条件，即模型里有隐藏后门、样本里有触发器、触发器与后门相互匹配；由此得到三种防御范式，分别是触发器与后门失配、后门消除、触发器消除（图五与表四）。经验性防御被分为预处理类、模型重建类、触发器合成类、模型诊断类、毒药抑制类、训练样本过滤类、测试样本过滤类（第六-A 节）。认证防御全部基于随机平滑（randomized smoothing），在特定假设下给出认证半径（第六-B 节）。

## 5. 检测或防御所需的数据

论文是综述，没有单一方法，以下逐项列出它归纳的防御所需输入与攻击留下的可观测量。凡是论文没有交代的项，我标注"论文未说明"。

1. **训练样本与标签（训练集本身）**：防御侧，训练样本过滤类防御需要它。采集位置在客户端训练前或数据准备阶段，粒度是逐样本。[148] 发现中毒样本会在特征表示协方差的谱上留下可检测痕迹，[149] 对每个类别的激活做聚类来判断哪个簇是中毒样本，[151] 采用相似思路，[152] 用输入梯度中的信号分离中毒样本，[61] 用显著性图定位触发区域并过滤，[155] 利用高频伪影过滤。不需要跨轮历史，不需要干净参考数据，不需要额外前向或反向计算（[61]、[152] 需要反向或解释计算，见下）。
2. **特征表示及其协方差谱**：采集位置是对模型做前向得到的特征层，在联邦场景下对应客户端本地计算；粒度是逐样本（在特征空间聚合统计）。[148] 用特征表示协方差的谱，[153] 用稳健协方差估计放大该谱特征。不需要跨轮历史与干净参考数据。
3. **隐藏层激活**：采集位置是客户端每步或拿到全局模型后的前向传播；粒度是逐样本、逐类。[149] 把每个类内训练样本的激活聚成两类再判断哪一类是中毒样本。需要额外前向计算，不需要跨轮历史与干净参考数据。
4. **逐样本梯度与输入梯度**：采集位置是客户端训练每步的反向传播；粒度是逐样本。[144] 观察到中毒样本梯度的 ℓ2 范数显著大于良性样本且梯度方向也不同，用差分隐私随机梯度下降（differentially private stochastic gradient descent，DPSGD）裁剪并扰动个体梯度；[152] 使用输入梯度。需要额外计算（逐样本梯度通常不是默认输出），不需要跨轮历史与干净参考数据。
5. **显著性图与输出解释**：采集位置是对模型做前向与反向解释；粒度是逐样本。[120] 的 Februus 用 GradCAM 识别影响最大的区域，[60] 的 NeuronInspect 从生成的热力图提取三种特征并用离群检测器做元分类器。需要额外计算。
6. **模型源文件或模型权重（白盒）**：采集位置是服务器训练后拿到模型时；粒度是逐层或整个模型。触发器合成类的 [25]、[132]、[133]、[58]、[137] 与模型重建类的 [119]、[124]、[125]、[126]、[127]、[128]、[129] 都要求能访问模型源文件；[132] 用合成触发器下激活值的 ℓ∞ 范数区分后门相关神经元。通常需要额外反向优化或再训练。跨轮历史论文未说明。
7. **模型预测，即概率向量或预测标签（黑盒）**：采集位置是对可疑模型的查询接口；粒度是逐查询样本。[59]、[136] 是黑盒触发器合成防御，只要能得到模型预测就能反向触发器；[26] 的通用试金石模式与 [138] 的元分类器诊断都基于对合成输入的预测，[138] 表明元分类器可以只用良性模型训练，而 [26] 需要同时使用感染模型与良性模型。需要额外的合成与前向计算。
8. **干净参考数据**：采集位置在防御者一侧（用户或服务器本地）；粒度是逐样本。场景二明确说防御者可以在一小份本地良性数据集上微调修复；[119] 用少量本地良性样本重训可疑模型，[125] 用一定量良性样本做模式连通性修复。这一项就是需要干净参考数据的典型，论文没有要求根数据集（root dataset）这一说法，论文未说明根数据集。
9. **推理期测试样本**：采集位置是评估与部署时的推理入口；粒度是逐样本。测试样本过滤类防御在此工作，[156] 通过在可疑样本上叠加各种图像模式并观察预测随机性，[157] 用模型不确定性，[143] 把过滤当作离群检测，[158] 借用对抗样本检测，[159] 声称不需要有标签样本或对触发模式的先验假设。这类方法需要多次前向计算。
10. **训练样本的到达顺序**：这是攻击留下的痕迹，采集位置在客户端训练每步；粒度是逐批，且必须跨步记录顺序。[50] 通过操纵训练样本顺序注入后门，不改变样本内容。
11. **各客户端上传的更新**：在联邦场景中，[54] 通过放大中毒梯度实施攻击，因此被放大的更新范数是可观测量；采集位置是服务器收到更新时，粒度是逐客户端，通常需要跨轮历史做对比。论文只引用了该攻击，没有给出相应检测方法或阈值，具体检测统计量论文未说明。

**攻击会留下的痕迹与声称绕过的检测**：论文指出不可见攻击的中毒图像虽然与其良性版本相似，但其源标签通常与目标标签不同，因此仍可通过检查训练样本的图像与标签关系被发现（第三-C2 节）。样本特定攻击 [62] 打破了触发器合成类与显著性类防御的根本假设，[12] 的隐写触发器不仅不可见，还能绕过大多数现有后门防御，因为触发器是样本特定的（第三-C5 节）。一对多攻击因其复杂的标签移位，可以绕过许多面向目标的防御，例如 [25]、[61]、[59]（第三-C7 节）。[150] 证明简单的目标污染就能让中毒样本的表示与良性样本难以区分，因此大多数过滤类防御可以被轻易绕过（第六-A6 节）。[116] 证明判定模型是否含有可触发后门的置换是 NP 完全问题，因此后门检测几乎不可能（第四-A 节）。关于跨轮历史是否是必需视图，论文没有讨论，论文未说明。

## 6. 干预动作

论文不提出干预，只归纳被综述防御的动作与其发生位置。以下动作与位置均来自第六节与表四。

- **推理前预处理（触发器与后门失配）**：在样本送入网络之前改变触发模式，使触发器不再与后门匹配，从而阻止后门激活（第六-A1 节）。[119] 用预训练自编码器做预处理器；[120] 先用 GradCAM 定位影响区域、用中性色块替换、再用生成对抗网络做图像修复；[121] 用主色调构造方块状触发器遮挡；[122] 用风格迁移；[9] 用空间变换（缩小、翻转）；[123] 在微调与推理两个过程引入更多变换。动作发生在推理入口。
- **模型重建与后门消除**：直接修改可疑模型以移除后门（第六-A2 节）。[119] 用本地良性样本重训，[129] 把重训写成极小极大问题并用隐式超梯度，[124] 先剪枝后微调（fine-pruning），[128] 用对抗权重扰动放大良性与恶意神经元的差异，[125] 用模式连通性修复，[126]、[127] 用知识蒸馏重建模型。动作发生在服务器拿到训练好的模型之后。
- **触发器合成后消除**：先合成触发模式，再抑制其效果（第六-A3 节）。[25] 对每个类反向出潜在触发器后用异常检测确定最终触发器与目标标签，[58] 借鉴 K 臂老虎机每轮只选一个类做触发器优化以提高效率，[132]、[133] 根据合成触发器做神经元剪枝。论文指出此前所有此类防御都是白盒，需要模型源文件。
- **模型诊断与拒绝部署**：用预训练元分类器判断可疑模型是否被感染并拒绝部署被感染模型，由于只有良性模型进入部署，后门自然被消除（第六-A4 节）。动作发生在部署之前，属于只报告并拒绝，而不是修改模型。
- **训练期毒药抑制**：在训练过程中削弱中毒样本的作用（第六-A5 节）。[143] 用带噪声的随机梯度下降学习差分隐私模型，[144] 用 DPSGD 裁剪并扰动个体梯度，[145] 用强数据增强（例如 CutMix）扰动触发器，[27] 用基于梯度上升的反后门方法，[147] 用解耦训练抑制后门。动作发生在客户端训练过程中。
- **训练样本过滤**：从训练集中过滤中毒样本，之后只用良性样本或净化后的样本训练，从源头消除后门创建（第六-A6 节）。
- **测试样本过滤**：在推理阶段过滤恶意样本，只把良性测试样本或净化后的被攻击样本交给部署模型预测，通过移除触发模式阻止后门激活（第六-A7 节）。
- **认证防御**：用随机平滑给出认证半径，并可用集成与袋装（bagging）提升效果（第六-B 节），动作在模型与推理两侧。

## 7. 实验设置与主要结果

论文是综述，没有统一的实验设置，也没有在联邦学习部分报告客户端数、参与率、轮次、恶意比例或非独立同分布（non-independent and identically distributed，非 IID）设置，这些项论文未报告。可以报告的实验信息如下。

- **指标**：攻击用良性准确率（benign accuracy，BA）与攻击成功率（attack success rate，ASR），BA 与 ASR 越高攻击越好，中毒率与扰动越小越隐蔽（第二-A 节与第三-B 节）。检测类防御用精确率、召回率、F1 分数；非检测类经验防御用 BA 与 ASR；认证防御用良性准确率、认证率与认证准确率（第六-C 节）。
- **数据集规模结果**：表五给出图像识别基准数据集的规模，例如 MNIST 为 28×28、60,000 训练与 10,000 测试，CIFAR 为 32×32×3、50,000 与 10,000，ImageNet 为 224×224×3、1,281,167 与 50,000，GTSRB 为 34,799 与 12,630，U.S. Traffic Sign 为 6,889 与 1,724，SVHN 为 73,257 与 26,032，人脸数据包括 YouTube Face 的 1,595 人的 3,425 段视频、PubFig 的 200 人的 58,797 张图像、VGGFace 的 2,622 人的 260 万张图像、VGGFace2 的 9,131 人的 330 万张图像、LFW 的 5,749 人的 13,233 张图像。
- **具体攻击结果**：TBT 用 8800 万个权重比特中的 84 个比特翻转，使 ResNet-18 在 CIFAR-10 上被误导（第四-A 节，引 [20]）。
- **定性结论**：论文指出数字攻击在物理世界中会因旋转、缩放等变换改变触发器的位置与外观而失效（第三-C6 节）；干净标签攻击通常比中毒标签攻击效果差，如何在隐蔽性与有效性之间平衡仍是开放问题（第三-C2 节）；触发器合成类防御需要更高效的设计，模型诊断类防御需要能区分良性与感染模型的元分类器（第六-A 节）。

## 8. 开销

论文没有报告计算量、通信量或存储量的具体数值，这一点论文未报告。可以引用的只有定性陈述：除预处理类防御外，现有防御通常计算开销很高（第八-D 节）；[9] 的空间变换防御更高效，因为它几乎不带来额外计算开销（第六-A1 节）；[58] 的触发器合成每轮只选一个类做优化以提高效率（第六-A3 节）；[138] 的元分类器可以只用良性模型训练，相比 [26] 降低了对感染模型样本的需求（第六-A4 节）。通信与存储开销论文未报告。

## 9. 假设、局限与自适应攻击

- **论文自述的假设**：三类场景的能力矩阵（表一）是全部讨论的前提；白盒攻击假设训练集已知、黑盒攻击假设训练集未知（表二）；场景二的修复型防御假设防御者持有一小份本地良性数据，重建类防御假设有一定量良性样本（第二-B 节与第六-A2 节）；白盒触发器合成与模型重建假设能访问模型源文件，黑盒版本假设只能拿到预测（第六-A3 节）；测试样本过滤类中的 [156] 假设大多数触发器是输入无关的（第六-A7 节）；训练样本过滤类假设中毒样本在特征、梯度或频率域可分（第六-A6 节）。
- **论文自述的局限**：几乎所有经验性防御都被后续自适应攻击绕过；认证防御的有效性在特定假设下才有理论保证，而这些假设通常不被满足，实践中弱于经验防御（第六节引言与第六-B 节）；触发器设计多为启发式甚至非优化，优化式触发器泛化差（第三-C3 节与第八-A 节）；语义与物理后门研究落后（第八-B 节）；攻击主要集中于计算机视觉，尤其是图像分类，其他任务研究不足（第八-C 节）；除预处理类防御外开销高，黑盒防御与认证防御研究很少（第八-D 节）；后门的生成原理与激活机制仍是"圣杯"问题（第八-E 节）。
- **自适应攻击**：论文明确写道，多项经验防御已被后续自适应攻击绕过，并引用 [188]、[189]（第六-B 节）。但论文本身没有做统一的实验来评估自适应攻击者，也没有给出统一结果，它只是以综述方式陈述这一结论。
- **迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析：）**：第一，论文整体是集中式图像分类的综述，全文没有出现 LoRA、PEFT 或大模型，联邦学习只有一小段文献罗列，因此联邦 LoRA 场景下的攻击成功率、可见性度量、防御有效性在论文中没有依据。第二，[54] 的"放大中毒梯度"依赖攻击者能控制并缩放完整本地更新；LoRA 只上传低秩增量矩阵，放大倍率与可检测性都会改变，论文未说明其在低秩更新上的行为。第三，场景一假设防御者可以清洗整个训练集；联邦中服务器看不到客户端本地样本，训练样本过滤类防御必须下放到客户端执行或改用上传的统计量，论文未说明这种改造。第四，特征协方差、激活聚类、逐样本梯度这些数据视图在联邦中天然分散，需要在客户端本地计算后上传聚合统计量，论文的集中式描述未涉及这一点。第五，论文指出自然语言处理中改动一个词或字符就可能因语法或拼写错误被察觉，且不同任务的触发器设计差异很大（第三-D 节与第八-C 节），因此图像上的像素级不可见性度量不能直接搬到文本触发词。第六，认证防御只讨论随机平滑（第六-B 节），它在大模型与低秩增量上的适用性论文未说明。第七，论文引用 [97] 的结论是，在联邦学习中若模型对对抗样本脆弱则在温和条件下后门不可避免（第三-D 节），该条件对当前大模型是否成立论文未说明。第八，BA 与 ASR 这两个指标定义本身可以迁移，但大模型通常关心生成质量或下游任务指标，论文未说明。

## 10. 对防护库设计的含义

以下全部是分析：

1. **采集底座需要在客户端数据准备阶段提供逐样本视图**。训练样本过滤类防御都建立在逐样本的样本、标签、特征或梯度之上（第六-A6 节），在联邦 LoRA 中只有客户端能看到原始数据，因此库必须在客户端挂一个训练前钩子，输出样本级摘要（例如嵌入、损失、梯度统计），并允许插件声明自己需要哪一种摘要。这一需求是通用的，不是这篇论文特有的。
2. **客户端每步钩子需要暴露逐样本梯度与逐层激活**。DPSGD 型抑制要裁剪与扰动个体梯度（第六-A5 节），激活聚类与特征谱过滤要拿到中间层表示（第六-A6 节），输入梯度与显著性图方法还需要反向解释（第六-A6 节与第六-A1 节）。因此底座要支持在客户端训练步上挂前向与反向探针，并支持"加噪、裁剪、梯度上升、解耦训练"这类训练过程内的干预接口；插件参数（裁剪阈值、聚类数、噪声尺度）应做成配置而不是硬编码。
3. **服务器收到更新时需要一个逐客户端更新视图**。[54] 通过放大中毒梯度实施攻击（第三-D 节），其可观测痕迹是更新范数，因此库应在服务器接收钩子上暴露每个客户端的 LoRA 增量、逐层范数，以及与其他客户端更新和跨轮历史的相似度。跨轮历史不是这篇论文讨论的内容，但对识别持续多轮的放大或分布式触发是通用需求，应作为可选数据视图。
4. **服务器聚合后与部署前需要模型级视图，且要区分白盒与黑盒**。触发器合成与模型重建需要模型权重与反向优化能力（第六-A3 节与第六-A2 节），模型诊断只需要预测接口（第六-A4 节），因此库应同时提供"权重视图"和"仅预测 API 视图"两种模型插件钩子，并提供干净参考数据集接口，用于微调、重训、模式连通性与知识蒸馏式修复（第六-A2 节）。干净参考数据这一需求对联邦 LoRA 是通用的，因为服务器通常可以持有公开的干净校准数据。
5. **干预接口必须覆盖三个位置**。客户端侧包括过滤样本与训练过程抑制，服务器侧包括剔除或重加权客户端、重建或回滚全局模型，推理侧包括输入预处理与测试样本过滤（第六-A 节各小节）。论文中的模型诊断类防御对应"只报告并拒绝部署"，因此库还需要一个不修改任何模型、只产出判断与告警的报告模式。
6. **通用与特有要分开**。通用的是多位置采集点、从逐样本到逐轮再到整个模型的粒度、跨轮历史、干净参考数据、以及固定的客户端钩子与服务器钩子；这篇论文特有的是各类防御的具体统计量，包括特征协方差谱、激活聚类、逐样本梯度的范数与方向、显著性图、激活值的 ℓ∞ 范数、高频伪影，以及认证防御所需的随机平滑多次前向采样（第六-B 节）。把这些统计量做成插件内的计算，而把原始数据视图留给底座，是这篇综述给出的分工依据。

## 11. 原文依据

1. 第一节，支撑第 2 节与第 3 节关于后门攻击定义与训练期注入位置的论断："backdoor attackers intend to embed hidden backdoors in DNNs during the training process, so that the attacked DNNs behave normally on benign samples whereas their predictions will be maliciously and consistently changed"
2. 第二-B 节场景一，支撑第 2 节关于数据提供方角色与防御者可清洗数据集的能力设定："In this scenario, attackers provide the poisoned dataset to users directly or through the Internet. Users will adopt the (poisoned) dataset to train their models, which will then be deployed."
3. 第二-B 节场景二，支撑第 2 节与第 5 节关于防御者只能修改训练好的模型并依赖一小份本地良性数据的论断："defenders can not control the training set and schedule while can modify the trained model to alleviate the attack. For example, they can ﬁne-tune it on a small local benign dataset."
4. 第二-B 节场景三，支撑第 2 节关于第三方模型提供方能力与推理流程边界的论断："attackers provide trained infected DNNs through the application programming interface (API) or the Internet. Attackers can change everything except for the inference pipeline."
5. 第三-C1 节 BadNets，支撑第 3 节关于本地数据准备入口的具体操作步骤："generate some poisoned images via stamping the backdoor trigger onto selected benign images to achieve poisoned sample (x′, yt), associated with the attacker-speciﬁed target label yt"
6. 第三-D 节，支撑第 3 节与第 5 节关于联邦学习中攻击从本地更新后处理进入并留下更新范数痕迹的论断："In [54], Bagdasaryan et al. introduced the ﬁrst backdoor attack against federated learning by amplifying the poisoned gradient of node servers."
7. 第三-A 节，支撑第 4 节关于统一攻击框架的论断："Given a benign training set Dt, existing poisoning-based backdoor attacks can be summarized in a uniﬁed framework based on aforementioned deﬁnitions, as follows:"
8. 第六-A5 节，支撑第 5 节与第 6 节关于逐样本梯度可观测量与 DPSGD 裁剪扰动干预的论断："Hong et al. [144] adopted differentially private stochastic gradient descent (DPSGD) to clip and perturb individual gradients during the training process."
9. 第六-A6 节，支撑第 5 节与第 6 节关于训练样本过滤类防御的输入与动作位置的论断："These defenses aim at ﬁltering poisoned samples from the training dataset. After the ﬁltering process, only benign samples or puriﬁed poisoned samples will be used in the training process, which eliminates backdoor creation from the source."
10. 第六-B 节，支撑第 9 节关于经验防御被自适应攻击绕过的论断："Although multiple empirical defenses have been proposed and reached decent performance against some backdoor attacks, almost all of them were bypassed by following adaptive attacks [188], [189]."

```json
{
  "key": "li2020backdoorsurvey",
  "title": "Backdoor Learning: A Survey",
  "year": 2020,
  "paper_type": "survey",
  "setting": "other",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_client", "malicious_server", "data_provider", "adapter_publisher"],
  "attack_goal": ["backdoor"],
  "attack_entry": ["local_data", "local_training", "update_postprocess", "model_distribution", "evaluation_deployment"],
  "observables": [
    {"what": "训练样本与标签，含中毒样本", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "特征表示及其协方差谱", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "隐藏层激活", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "逐样本梯度与输入梯度", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "显著性图与输出解释", "where": "client_step", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "训练样本到达顺序", "where": "client_step", "granularity": "batch", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "各客户端上传的梯度或更新及其范数", "where": "server_receive", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "模型源文件或权重，以及合成触发器下的逐层激活", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "模型预测，即概率向量或预测标签", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "干净参考数据集", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "推理期测试样本与叠加扰动后的预测随机性或不确定性", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["add_noise", "clip", "filter_samples", "repair_model", "report_only"],
  "intervention_where": ["both"],
  "assumptions": [
    "三类场景的能力矩阵（表一）成立，攻击者与防御者可控制与不可控制的环节按场景划分",
    "白盒攻击假设训练集已知，黑盒攻击假设训练集未知（表二）",
    "场景二的修复型防御假设防御者持有一小份本地良性数据，重建类防御假设有一定量良性样本（第二-B 节与第六-A2 节）",
    "触发器合成与模型重建的白盒防御假设可以访问模型源文件，黑盒版本假设只能拿到模型预测（第六-A3 节）",
    "大多数触发器的输入无关假设（第六-A7 节），会被样本特定触发器打破（第三-C5 节）",
    "训练样本过滤类防御假设中毒样本在特征、梯度或频率域与良性样本可分（第六-A6 节），目标污染可以削弱该假设（引 [150]）",
    "认证防御的理论保证依赖特定假设，而这些假设通常不被满足（第六节引言与第六-B 节）",
    "经验性防御会被后续自适应攻击绕过（第六-B 节，引 [188] 与 [189]）"
  ],
  "evaluates_adaptive_attacker": true,
  "overhead_reported": false,
  "quotes": [
    {"section": "I. INTRODUCTION", "supports": "第 2 节与第 3 节：后门攻击在训练阶段注入，目标是良性样本表现正常而触发器激活时恶意改变预测", "text": "backdoor attackers intend to embed hidden backdoors in DNNs during the training process, so that the attacked DNNs behave normally on benign samples whereas their predictions will be maliciously and consistently changed"},
    {"section": "II-B Classical Scenarios and Corresponding Capacities, Scenario 1", "supports": "第 2 节：数据提供方只控制数据集，用户用中毒数据集训练并部署", "text": "In this scenario, attackers provide the poisoned dataset to users directly or through the Internet. Users will adopt the (poisoned) dataset to train their models, which will then be deployed."},
    {"section": "II-B Classical Scenarios and Corresponding Capacities, Scenario 2", "supports": "第 2 节、第 5 节与第 9 节：防御者不能控制训练集与训练计划，只能修改模型，并依赖一小份本地良性数据", "text": "defenders can not control the training set and schedule while can modify the trained model to alleviate the attack. For example, they can ﬁne-tune it on a small local benign dataset."},
    {"section": "II-B Classical Scenarios and Corresponding Capacities, Scenario 3", "supports": "第 2 节与第 9 节：第三方模型提供方除推理流程外可改一切，对应适配器或模型发布者这一信任边界", "text": "attackers provide trained infected DNNs through the application programming interface (API) or the Internet. Attackers can change everything except for the inference pipeline."},
    {"section": "III-C1 BadNets", "supports": "第 3 节：投毒式攻击在本地数据准备阶段的具体操作步骤", "text": "generate some poisoned images via stamping the backdoor trigger onto selected benign images to achieve poisoned sample (x′, yt), associated with the attacker-speciﬁed target label yt"},
    {"section": "III-D Attacks against Other Fields or Paradigms", "supports": "第 3 节与第 5 节：联邦学习中的攻击通过放大本地中毒梯度进入，并在更新范数上留下痕迹", "text": "In [54], Bagdasaryan et al. introduced the ﬁrst backdoor attack against federated learning by amplifying the poisoned gradient of node servers."},
    {"section": "III-A A Uniﬁed Framework of Poisoning-based Attacks", "supports": "第 4 节：论文用统一框架归纳投毒式后门攻击", "text": "Given a benign training set Dt, existing poisoning-based backdoor attacks can be summarized in a uniﬁed framework based on aforementioned deﬁnitions, as follows:"},
    {"section": "VI-A5 Poison Suppression based Defenses", "supports": "第 5 节与第 6 节：逐样本梯度是可观测量，DPSGD 在训练过程中裁剪并扰动个体梯度", "text": "Hong et al. [144] adopted differentially private stochastic gradient descent (DPSGD) to clip and perturb individual gradients during the training process."},
    {"section": "VI-A6 Training Sample Filtering based Defenses", "supports": "第 5 节与第 6 节：训练样本过滤类防御的输入是训练集，动作是过滤后只用良性或净化样本训练", "text": "These defenses aim at ﬁltering poisoned samples from the training dataset. After the ﬁltering process, only benign samples or puriﬁed poisoned samples will be used in the training process, which eliminates backdoor creation from the source."},
    {"section": "VI-B Certiﬁed Backdoor Defenses", "supports": "第 9 节：论文自述经验性防御几乎都被自适应攻击绕过", "text": "Although multiple empirical defenses have been proposed and reached decent performance against some backdoor attacks, almost all of them were bypassed by following adaptive attacks [188], [189]."}
  ]
}
```
