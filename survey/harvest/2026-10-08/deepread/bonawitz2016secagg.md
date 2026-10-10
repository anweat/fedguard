# bonawitz2016secagg：Practical Secure Aggregation for Federated Learning on User-Held Data

## 1. 基本信息

- **场景**：传统联邦学习（Federated Learning, FL）。论文第 2 节以手机软键盘的下一词预测（next-word prediction）为例：每个用户把私人短信文本保存在自己的移动设备上，由一个中心服务器（central server）协调，基于"高度处理过的、范围最小的、短暂的（highly processed, minimally scoped, ephemeral）"用户更新来训练共享全局模型。论文不涉及大语言模型，也不涉及 LoRA 或其他参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）技术。
- **训练阶段**：分布式梯度下降（distributed gradient descent）的一轮更新过程，即"客户端本地计算更新 → 上传 → 服务器聚合"这一段；论文以 minibatch 随机梯度下降（stochastic gradient descent, SGD）的每一轮为安全聚合协议的实例化单位。
- **论文类型**：基础方法（foundation），具体是隐私保护的密码学聚合协议（安全多方计算，Secure Multi-Party Computation）。论文不是攻击论文，也不是检测论文；正文第 1 节明确把它定位为"a novel, communication-efficient Secure Aggregation protocol for high-dimensional data"。
- **模型与数据规模**：论文没有给出任何实际训练实验，也没有报告任何数据集、模型准确率或收敛曲线。文中给出的规模全部是协议设计参数与通信量例子：向量维度 k 可达"数百万参数"级别（第 2 节："Θ may contain millions of parameters"），参与用户数例子为第 2 节正文的 |U′| = 10^4 与 |U| = 10^7，通信扩展率例子为 2^10 用户 / 2^20 维向量与 2^14 用户 / 2^24 维向量（第 1 节），以及 16 位输入值。

## 2. 威胁模型

- **攻击者（论文中的"对手"）是服务器 S**。第 3 节把对手分为三档，并且明确"all users follow the protocol honestly"：
  - (T1) 诚实但好奇的服务器（honest-but-curious server）：遵守协议，但试图从收到的用户消息中学到尽可能多的信息。
  - (T2) 服务器可以就"哪些其他用户掉线（dropped out）"对用户撒谎，包括对不同用户报告不一致的掉线名单。
  - (T3) 服务器可以像 T2 一样撒谎，并且还可以访问有限数量用户的私有内存，而这些用户本身仍然诚实地遵守协议；此时隐私要求只针对剩余用户的输入成立。
- **占比或数量**：论文未说明攻击者在服务器侧的具体数量约束（服务器本身是单一实体）。协议对掉线用户的容忍度有明确数值：最多容忍 1/3 的用户未完成协议（第 1 节），正确性要求完成用户数 |Ū| ≥ n/2（第 3 节），门限 t 在不同威胁模型下取 t > n/2（T1）、2n/3（T2）、4n/5（T3）。
- **能力（能改什么）**：服务器控制协议的消息转发与轮次调度，可以谎报掉线集合、可以在 T3 中读取部分用户内存、可以发起中间人攻击（第 3 节 Protocol 4："the server may now conduct man-in-the-middle attacks"）。服务器不能修改诚实用户的本地输入，也不能让诚实用户同时泄露同一用户的两种掩码份额。
- **知识（知道什么）**：服务器知道所有用户的公开密钥、知道自己的私钥、知道用户上传的掩码后向量 y_u、知道每一轮的存活用户集合（U1、U2）、并能集齐解密所需的秘密份额。服务器不知道各用户的原始向量 x_u、也不知道成对秘密 s_{u,v} 与自掩码 b_u 的明文（除非满足门限数量的份额被它收集到）。
- **目标**：隐私（privacy）。第 2 节给出的动机是：即使更新 δ_u 是短暂的，用户仍可能担心残留信息，例如若输入的 one-hot 编码使 ∂L_f/∂θ_w 仅在词 w 出现时非零，那么检查 δ_u 的非零项就会暴露该用户最近输入的词集合。这不是无目标破坏、后门或越狱目标。
- **防御者是谁、能看到什么、信任什么**：防御者是诚实用户集合，它们只信任自己；论文不假设用户之间能直接建立安全通道，也不假设用户能原生认证其他移动设备（第 2 节）。服务器可见的全部数据是掩码后的聚合相关量，而不是单个用户的明文更新。用户的信任被"最小化"到引导轮（bootstrapping round）：第 3 节 Protocol 4 建议该轮代码足够小、可公开审计、可外包给可信第三方，或用具备远程证明能力的可信计算平台实现。

## 3. 攻击入口与流程位置

本篇是纯防御论文，因此按论文所针对的攻击入口描述：论文针对的是**更新上传前的后处理与服务器聚合这两段之间被服务器窥探/推断**的风险，入口位置是**服务器聚合（server aggregation）与更新上传路径**。

具体流程（第 3 节 Protocol 4 与 Figure 1）：

1. 轮次 0（Advertise Keys）：每个用户生成 Diffie-Hellman 密钥对 ⟨c_u^SK, c_u^PK⟩ 与 ⟨s_u^SK, s_u^PK⟩，把两个公开密钥发给服务器；服务器把收到的公开密钥列表广播给 U1 中的全体用户，自己保留一份。
2. 轮次 1（Share Keys）：用户生成自掩码 b_u 并计算成对秘密 s_{u,v}，对 b_u 与 s_u^SK 生成 t-out-of-n 秘密份额（secret shares），用各接收者的公开密钥加密后发送；服务器转发这些加密份额。用户端还会做量化前的缩放与裁剪映射（第 3 节脚注 1）。
3. 轮次 2（Masked Input Collection）：用户计算掩码输入 y_u 并上传；服务器在收到至少 t 个用户后继续。
4. 轮次 3（Unmasking）：服务器公布 U1 \ U2 的掉线名单；存活用户对存活用户交出自掩码 b_u 的份额、对掉线用户交出成对秘密 s_{u,v} 的份额；服务器重构秘密并计算最终聚合值 x̄。

论文未说明攻击者会在这个流程的本地数据准备、损失函数、优化器步数或评估与部署阶段做任何事；它也明确不针对恶意客户端投毒（见第 9 节）。

## 4. 方法原理

核心思想是"成对掩码相互抵消 + 双重掩码防服务器重构 + 门限秘密共享抗掉线"，通过四个递进的协议版本（第 3 节）建立。

- **Protocol 0（Masking with One-Time Pads，一次性掩码）**：每对用户 u、v 协商一对匹配的扰动。用户 u 对每个 v 从 [0, R)^k 均匀采样 s_{u,v}，双方交换并计算 p_{u,v} = s_{u,v} − s_{v,u} (mod R)，满足 p_{u,v} = −p_{v,u} (mod R)，且 u = v 时取 0。用户上传 y_u = x_u + Σ_{v∈U} p_{u,v} (mod R)，服务器直接求和得到 x̄ = Σ_{u∈U} y_u (mod R)。正确性由成对扰动在求和时抵消保证。
- **Protocol 1（Dropped User Recovery using Secret Sharing，掉线用户恢复）**：增加密钥广播轮，用服务器中介的、以接收者公开密钥加密并由发送者签名的信道模拟安全认证信道；再增加秘密共享轮，对每个扰动 p_{u,v} 做 (t, n) 门限共享，t > n/2。用户只把与存活集合 U1 相关的扰动计入 y_u。服务器在收到至少 t 个 y_u 后进入解掩码轮，向剩余用户索取 U1 \ U2 中掉线者秘密的份额，并按下式计算：x̄ = Σ_{u∈U2} y_u − Σ_{u∈U2} Σ_{v∈U1\U2} p_{u,v} (mod R)。论文指出这版丢失了安全性：若服务器故意把 u 从 U2 中剔除，诚实用户会交出足以剥掉 u 全部扰动的份额，因此连诚实但好奇的服务器都无法防范。
- **Protocol 2（Double-Masking to Thwart a Malicious Server，双重掩码）**：每个用户额外均匀采样 b_u ∈ [0, R)^k 并共享其份额，上传 y_u = x_u + b_u + Σ_{v∈U1} p_{u,v} (mod R)。解掩码轮中，服务器对每个 u ∈ U1 只能二选一：向存活成员 v 索取与 u 相关的 p_{u,v} 份额，或索取 u 的 b_u 份额；诚实用户仅在 |U2| > t 时响应，且绝不会对同一用户同时交出两类份额。最终 x̄ = Σ_{u∈U2} y_u − Σ_{u∈U2} b_u − Σ_{u∈U2} Σ_{v∈U1\U2} p_{u,v} (mod R)。这样 x_u 始终被 p_{u,v} 或 b_u 之一遮挡。安全性在 T1 下由 t > n/2 保证；论文陈述在 T2 与 T3 中门限须分别提高到 2n/3 与 4n/5。
- **Protocol 3（Exchanging Secrets Efficiently，高效交换秘密）**：用密码学安全伪随机生成器（pseudorandom generator, PRG）把标量种子扩展为 k 维向量；用 Diffie-Hellman 密钥协商让每对用户得到 s_{u,v} = s_{v,u} = AGREE(s_u^SK, s_v^PK)，并按用户全序取 p_{u,v} = PRG(s_{u,v})（u < v）或 −PRG(s_{u,v})（u > v）。于是服务器只需学到 s_u^SK 就能重构 u 的全部扰动，用户只需分发 s_u^SK 与 b_u 的份额，通信量从 O(kn²) 降下来。
- **Protocol 4（Minimizing Trust in Practice，实践中最小化信任）**：把 Protocol 1 的公开密钥交换替换为服务器中介的密钥协商：用户生成 ⟨c_u^SK, c_u^PK⟩ 并连同 s_u^PK 一起公布。论文承认服务器此时可做中间人攻击，但论证这在实际中可容忍，因为缺少认证机制或公钥基础设施时这几乎不可避免，且该协议仍提供前向保密（forward secrecy）。

## 5. 检测或防御所需的数据

按论文，协议运行所需的输入如下（论文未使用"检测"框架，以下为协议输入，采集点按第 3 节 Protocol 4 与 Figure 1）：

- **用户私有向量 x_u**（在联邦学习中对应 δ_u^t 与 |D_u|）：客户端本地持有；第 3 节要求其元素与聚合值均为 [0, R) 上的整数，联邦学习更新需通过截断/缩放、线性变换与（随机）量化映射到该范围（第 3 节脚注 1）；粒度是逐客户端（每个客户端一个 k 维向量）；不需要跨轮历史、不需要干净参考数据或根数据集、不需要其他客户端的数据。
- **Diffie-Hellman 公开密钥 c_u^PK 与 s_u^PK**：客户端训练后（协议轮次 0）生成并上传，服务器收到后广播；粒度为逐客户端逐轮；论文说明公开密钥长度为 256 位。
- **成对秘密份额 s_u^SK 的加密份额与自掩码份额 b_u 的加密份额**：客户端在秘密共享轮（轮次 1）本地生成并上传，服务器只转发；粒度为逐客户端、按 (t, n) 门限共享拆分到 n 份；服务器不得解密这些份额。
- **掩码后向量 y_u = x_u + b_u + Σ_{v∈U1} p_{u,v} (mod R)**：客户端训练后、上传前计算，服务器在轮次 2 收到；粒度是逐客户端逐轮的一个 k 维向量。
- **存活用户集合 U1 与 U2，以及掉线名单 U1 \ U2**：客户端在收到份额后自行推断 U1 的一致性视图；U2 由服务器在收齐至少 t 个 y_u 后确定并公布；粒度为逐轮、集合级。
- **解掩码份额**：服务器在轮次 3 向存活用户索取，每个存活用户对每个存活用户交 b_u 份额、对每个掉线用户交 s_{u,v} 份额；粒度为逐客户端对（pair）与逐份额；服务器需要至少 t 份才能重构一个秘密。

**关于攻击痕迹（论文报告）**：论文指出未受保护的更新会留下可观测痕迹——若输入 x 是词汇表长度的 one-hot 向量，常见架构中至少存在一个参数 θ_w 使 ∂L_f/∂θ_w 仅在 x 编码词 w 时非零，因此检查 δ_u^t 的非零项即可揭示该用户最近输入的词集合（第 2 节）。论文声称安全聚合能让服务器只学到"U 中一个或多个用户写过词 w"，而不知道是哪些用户。

**关于绕过检测（论文报告）**：本协议的设计目标本身就是让服务器无法从单个 y_u 中获取信息，因此论文并未讨论攻击者"绕过某检测器"的问题。论文未说明任何具体检测器及其规避方式。

## 6. 干预动作

论文的干预不是"先检测再处置"，而是**在数据离开客户端之前就地进行密码学掩码，并在服务器侧按门限解掩码**：

- **客户端侧（上传前）**：对私有向量做截断/缩放、线性变换与（随机）量化以映射到 [0, R)，加入成对掩码 p_{u,v} 与自掩码 b_u，生成并上传加密的秘密份额（第 3 节脚注 1、Protocol 2 与 Protocol 4）。
- **服务器侧（收到至少 t 个更新后）**：向存活用户索取解掩码份额、重构掉线用户相关的成对扰动与自掩码、做修正求和得到 x̄（第 3 节 Protocol 2 与 Protocol 4）。服务器随后用该聚合值执行梯度下降步 Θ^{t+1} ← Θ^t − η (Σ δ_u^t)/(Σ |D_u|)（第 2 节）。
- **剔除掉线客户端**：协议只把完成协议的用户纳入 U2，未完成者被当作掉线并从求和范围中排除；这是为**正确性**而非安全性的动作（第 3 节 Protocol 1、Protocol 2）。
- 论文未提出重新加权、裁剪作为防御、加噪、过滤样本、修复或回滚模型等动作。注意截断/缩放与量化在论文中是**预处理**，用于把实数更新映射到整数环 [0, R)，不是聚合侧的防御干预（第 3 节脚注 1）。论文也未提出任何"仅报告"模式。

## 7. 实验设置与主要结果

- **实验设置**：论文没有真实训练实验，没有模型、数据集、轮次、客户端数与恶意比例等评测配置。所有"结果"都是协议正确性/安全性论证与通信量分析。
- **关键数值结果**：
  - 第 1 节：协议最多容忍 1/3 的用户未完成协议；对 16 位输入值，2^10 用户与 2^20 维向量下通信扩展为 1.73×，2^14 用户与 2^24 维向量下为 1.98×。
  - 第 3 节：正确性要求 |Ū| ≥ n/2；门限在 T1 下为 t > n/2，在 T2 与 T3 下需分别提高到 2n/3 与 4n/5。
  - 第 3 节 Protocol 4：设密钥协商公开密钥与加密秘密份额均为 256 位、用户输入同处 [0, R_U − 1]，每个用户比直接上传原始向量多传输 `[256(7n−4) + k⌈log2(n(R_U−1)+1)⌉ + n] / (k⌈log2 R_U⌉)` 的数据量。
  - 表 1（Table 1: Protocol 4 Cost Summary）：用户侧计算 O(n² + kn)、服务器侧计算 O(kn²)；用户侧通信 O(n + k)、服务器侧通信 O(n² + kn)；用户侧存储 O(n + k)、服务器侧存储 O(n² + k)。表注说明推导被推迟到完整版论文，并在脚注 6 说明从对齐的 (t, n)-Shamir 份额重构 n 个秘密可在 O(t² + nt) 内完成（缓存 Lagrange 系数）。
- 论文未给出准确率、收敛性或隐私攻击成功率的实验数字。

## 8. 开销

- **计算**：表 1 给出用户 O(n² + kn)、服务器 O(kn²)；脚注 6 给出服务器重构 n 个秘密的 O(t² + nt)（缓存 Lagrange 系数）。论文未报告实测运行时间或墙钟开销。
- **通信**：表 1 给出用户 O(n + k)、服务器 O(n² + kn)；第 1 节给出 1.73×（2^10 用户、2^20 维、16 位值）与 1.98×（2^14 用户、2^24 维、16 位值）的通信扩展；第 3 节 Protocol 4 给出每用户额外传输量的显式公式（含 256 位公开密钥与份额的假设）。
- **存储**：表 1 给出用户 O(n + k)、服务器 O(n² + k)。
- 论文未报告功耗、内存占用实测值或端到端部署开销。

## 9. 假设、局限与自适应攻击

**论文自述的假设**：

- 所有用户诚实遵守协议；论文说"we assume that all parties are honest"用于正确性，"all users follow the protocol honestly"用于威胁模型（第 3 节）。
- 输入与聚合值为 [0, R) 上的整数，且 R 需取足够大以避免溢出（第 3 节脚注 8：R = n(R_U − 1) + 1）。
- 用户之间没有直接的成对安全信道，也不能原生认证其他移动设备；这正是 Protocol 4 用服务器中介密钥协商的原因（第 2 节、第 3 节 Protocol 4）。
- 服务器至少在一开始能维护"谁通过了每一轮"的一致视图（Protocol 1 中论文暂时假设服务器忠实转发所有消息）。
- 需要 t 或更多用户完成协议，协议才正确。

**论文自述的局限**：

- 不分析针对任意恶意服务器与用户的合谋（collusion）的安全性，也不分析任意恶意服务器与用户的情形；论文明确把这一情形与更形式化的安全分析推迟到完整版（第 3 节脚注 2 与脚注 5）。脚注 5 提到安全论证涉及"bounding the number of shares the server can recover by forging dropouts"。
- Protocol 4 中的中间人攻击是可容忍但未消除的风险，论文用"信任最小化"与前向保密来论证其可接受性（第 3 节 Protocol 4）。
- Protocol 3 之前的版本通信量为 O(kn²)，不实用（第 3 节 Protocol 3）。
- 论文未讨论恶意客户端投毒、后门或聚合规则被操纵的问题。

**是否评估自适应攻击者**：论文没有做任何攻击实验。它给出的是在 T1/T2/T3 三档服务器行为下的安全性论证（并声明形式化证明在完整版），而不是对自适应攻击者的经验评估。论文未说明自适应攻击者的实验结果。

**迁移到联邦 LoRA 微调的失效假设（分析：）**：

- **分析：**论文假设用户诚实、威胁只来自服务器；联邦 LoRA 投毒防护的主要威胁恰恰是恶意客户端，安全聚合在原则上会让服务器更难察觉单个客户端的异常更新，因此"机密性保护"与"投毒检测"在采集可见性上直接冲突。
- **分析：**论文假设更新是同一范围 [0, R) 上的定长整数向量，并靠统一的截断/缩放与量化映射。LoRA 增量按层、按模块（A/B 矩阵）尺度差异很大，若各客户端采用不同 rank、不同目标模块或不同量化格式，掩码所需的统一环 R 与逐元素对齐假设可能不成立。
- **分析：**论文的 k 是"数百万参数"级别，并假设服务器计算 O(kn²)；LoRA 增量通常远小于全参数更新，通信公式中的 256(7n−4) 密钥/份额项在 n 很大时可能反而占主导，但这属于量级推断，论文未讨论参数高效微调。
- **分析：**论文的协议只保证"聚合和"的机密性，不保证聚合结果的正确性；LoRA 微调中若采用逐层裁剪、投影、稀疏化或适配器拼装等上传前后处理，需要确认这些操作在掩码前完成且不破坏同态求和所需的整数环结构。
- **分析：**论文正确性依赖至少 t > n/2 用户完成；联邦 LoRA 场景常见低参与率与高掉线率，门限与容错参数需要重新标定，论文的 1/3 容忍度不能直接照搬。
- **分析：**论文的 T3 允许服务器读取有限数量用户的内存，并要求门限提高到 4n/5；在托管式联邦微调平台中，若服务器本身就掌握部分客户端或适配器托管环境，该假设的实际边界需要重新评估。

## 10. 对防护库设计的含义

以下全部为**分析：**。

- **分析：**这篇论文的方法不落在"客户端钩子 + 服务器钩子"的检测插件轴上，而是落在**上传通道本身**：库需要把"服务器看到的更新视图"从"逐客户端明文更新"改成"掩码后更新 + 门限份额"两种并行数据流，并在服务器聚合钩子上区分"收到 y_u 时"与"解掩码后得到 x̄ 时"两个不同信任边界。
- **分析：**采集底座需要在服务器侧提供四个采集点：轮次 0 的公开密钥与客户端注册名单（逐客户端）、轮次 1 的加密份额转发（逐客户端对，内容对服务器不可读）、轮次 2 的掩码向量 y_u（逐客户端逐轮）与存活集合 U2、轮次 3 的解掩码份额与最终聚合值。这四个点与常规联邦学习库的"梯度/更新接收"钩子不是同一个东西。
- **分析：**客户端侧需要"训练后、上传前"的后处理钩子，用于截断缩放、量化以及掩码注入；这些必须在插件化检测器看到数据之前完成，否则检测器会破坏掩码结构。协议中的 s_u^SK 与 b_u 属于客户端本地秘密，不应进入任何上报路径。
- **分析：**与具体攻击无关的通用需求是：逐客户端逐轮更新的版本化存储、聚合前后两个模型快照、客户端参与名单与掉线记录、跨轮历史索引；这些对绝大多数检测插件都通用。
- **分析：**本篇特有的需求是密码学原语与状态机支持：门限秘密共享、Diffie-Hellman 密钥协商、伪随机生成器种子扩展、按用户全序确定掩码符号、以及"同一用户两类份额不可同时泄露"的约束检查。这些不是普通检测插件能表达的，需要作为库的底层能力而不是插件。
- **分析：**干预接口方面，本协议需要的是"按轮次阶段拒绝继续"（未达门限则中止该轮）与"从聚合中排除未完成客户端"，而不是剔除、重加权或回滚模型；如果库的服务器钩子只提供"聚合后对聚合值做重加权/裁剪"，这类密码学协议无法挂载。

## 11. 原文依据

1. 第 1 节（Introduction）。支撑第 1 节的论文类型定位与第 4 节的方法定位。
   > "We proceed to design a novel, communication-efficient Secure Aggregation protocol for high-dimensional data that tolerates up to 1/3 of users failing to complete the protocol."
2. 第 1 节（Introduction）。支撑第 1 节与第 7 节的通信扩展数值结果。
   > "For 16-bit input values, our protocol offers 1.73× communication expansion for 210 users and 220-dimensional vectors, and 1.98× expansion for 214 users and 224-dimensional vectors."
3. 第 2 节（Secure Aggregation for Federated Learning）。支撑第 2 节服务器可见视图与第 6 节服务器仅需聚合和的论断。
   > "The server does not need to inspect any individual user’s update, however; it requires only the sums P u∈U |Du| and P u∈U δt u."
4. 第 2 节（Secure Aggregation for Federated Learning）。支撑第 2 节"未受保护更新的隐私痕迹"与第 5 节的攻击痕迹描述。
   > "Thus, the set of recently typed words in Du would be revealed by inspecting the non-zero entries of δt u."
5. 第 3 节（A Practical Secure Aggregation Protocol）。支撑第 2 节的防御者可见数据范围与第 3 节的协议入口描述。
   > "Each user u ∈U holds a private vector xu of dimension k."
6. 第 3 节（A Practical Secure Aggregation Protocol）。支撑第 2 节的对手设定与第 9 节的"用户诚实"假设。
   > "We consider three different threat models. In all of them, all users follow the protocol honestly, but the server may attempt to learn extra information in different ways2:"
7. 第 3 节（A Practical Secure Aggregation Protocol）。支撑第 3 节 Protocol 2 的双重掩码原理。
   > "To guarantee security, we introduce a double-masking structure that protects xu even when the server can reconstruct u’s perturbations."
8. 第 3 节（A Practical Secure Aggregation Protocol）。支撑第 7 节各威胁模型门限取值的论断。
   > "It can be shown that in Threat Models T2 and T3 the thresholds must be raised to 2n 3 and 4n 5 correspondingly."
9. 第 3 节脚注 2。支撑第 9 节"论文未分析合谋与任意恶意方"的局限。
   > "We do not analyze security against arbitrarily malicious servers and users that may collude. We defer this case and a more formal security analysis to the full version."
10. 第 3 节 Protocol 4。支撑第 2 节的信任假设与第 9 节的中间人风险局限。
    > "We note immediately that the server may now conduct man-in-the-middle attacks, but argue that this is tolerable for several reasons."

```json
{
  "key": "bonawitz2016secagg",
  "title": "Practical Secure Aggregation for Federated Learning on User-Held Data",
  "year": 2016,
  "paper_type": "foundation",
  "setting": "classic_fl",
  "uses_lora_or_peft": false,
  "adversary": ["malicious_server"],
  "attack_goal": ["privacy"],
  "attack_entry": ["server_aggregation", "update_postprocess"],
  "observables": [
    {"what": "客户端公开密钥（Diffie-Hellman 公开密钥 c_u^PK 与 s_u^PK）", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "掩码后更新向量 y_u = x_u + b_u + Σ p_{u,v} (mod R)", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "加密的秘密份额（s_u^SK 份额与 b_u 份额），服务器仅转发不可解密", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "存活用户集合 U1 与 U2、掉线名单 U1 \\ U2", "where": "server_aggregate", "granularity": "round", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "解掩码份额（存活用户的 b_u 份额、掉线用户相关的 s_{u,v} 份额）", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "解掩码修正后的聚合值 x̄", "where": "server_post_aggregate", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "每用户本地数据量 |D_u| 与本地更新 δ_u^t（客户端本地持有，不上报明文）", "where": "client_post_train", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["add_noise", "exclude_client"],
  "intervention_where": ["both"],
  "assumptions": [
    "所有用户诚实遵守协议，对手只来自服务器侧",
    "输入与聚合值均为 [0, R) 上的整数，实数更新需经截断/缩放、线性变换与量化映射",
    "用户之间没有直接的成对安全信道，也不能原生认证其他移动设备",
    "正确性要求至少 t 个用户完成协议，且 |Ū| ≥ n/2",
    "最多容忍 1/3 的用户未完成协议",
    "门限取值依赖威胁模型：T1 为 t > n/2、T2 为 2n/3、T3 为 4n/5",
    "Protocol 1 阶段暂时假设服务器忠实转发用户之间的所有消息",
    "不分析任意恶意服务器与用户的合谋，也不分析任意恶意服务器与用户"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "1 Introduction", "supports": "第 1 节论文类型与第 4 节方法定位", "text": "We proceed to design a novel, communication-efﬁcient Secure Aggregation protocol for high-dimensional data that tolerates up to 1/3 of users failing to complete the protocol."},
    {"section": "1 Introduction", "supports": "第 1 节与第 7 节的通信扩展数值结果", "text": "For 16-bit input values, our protocol offers 1.73× communication expansion for 210 users and 220-dimensional vectors, and 1.98× expansion for 214 users and 224-dimensional vectors."},
    {"section": "2 Secure Aggregation for Federated Learning", "supports": "第 2 节服务器可见视图与第 6 节服务器仅需聚合和", "text": "The server does not need to inspect any individual user’s update, however; it requires only the sums P u∈U |Du| and P u∈U δt u."},
    {"section": "2 Secure Aggregation for Federated Learning", "supports": "第 2 节隐私痕迹与第 5 节攻击痕迹描述", "text": "Thus, the set of recently typed words in Du would be revealed by inspecting the non-zero entries of δt u."},
    {"section": "3 A Practical Secure Aggregation Protocol", "supports": "第 2 节与第 3 节的协议入口与数据形态", "text": "Each user u ∈U holds a private vector xu of dimension k."},
    {"section": "3 A Practical Secure Aggregation Protocol", "supports": "第 2 节对手设定与第 9 节用户诚实假设", "text": "We consider three different threat models. In all of them, all users follow the protocol honestly, but the server may attempt to learn extra information in different ways2:"},
    {"section": "3 A Practical Secure Aggregation Protocol (Protocol 2)", "supports": "第 4 节 Protocol 2 双重掩码原理", "text": "To guarantee security, we introduce a double-masking structure that protects xu even when the server can reconstruct u’s perturbations."},
    {"section": "3 A Practical Secure Aggregation Protocol (Protocol 2)", "supports": "第 7 节各威胁模型门限取值", "text": "It can be shown that in Threat Models T2 and T3 the thresholds must be raised to 2n 3 and 4n 5 correspondingly."},
    {"section": "3 A Practical Secure Aggregation Protocol (footnote 2)", "supports": "第 9 节未分析合谋与任意恶意方的局限", "text": "We do not analyze security against arbitrarily malicious servers and users that may collude. We defer this case and a more formal security analysis to the full version."},
    {"section": "3 A Practical Secure Aggregation Protocol (Protocol 4)", "supports": "第 2 节信任假设与第 9 节中间人风险局限", "text": "We note immediately that the server may now conduct man-in-the-middle attacks, but argue that this is tolerable for several reasons."}
  ]
}
```
