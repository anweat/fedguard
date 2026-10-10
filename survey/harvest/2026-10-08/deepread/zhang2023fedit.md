# zhang2023fedit：Towards Building the Federated GPT: Federated Instruction Tuning

## 1. 基本信息
- 场景：联邦大模型微调（federated LLM fine-tuning）。论文提出 Federated Instruction Tuning（FedIT）框架，把联邦学习（federated learning, FL）用于大语言模型（large language model, LLM）的指令微调（instruction tuning），并要求客户端使用参数高效微调（parameter-efficient fine-tuning, PEFT）中的 LoRA（Low-Rank Adaptation）。这不是传统联邦学习（图像分类等）场景，也不是集中式大模型训练，而是"联邦 LLM 指令微调 + 参数高效适配器聚合"的框架类工作。
- 训练阶段：监督式指令微调（SFT）阶段；底座 LLM 全程冻结，只训练并上传 LoRA 适配器（论文 3.1、3.3、算法 1）。
- 论文类型：基础方法 / 平台（foundation）。论文同时提出了 FedIT 方法、一个框架，以及开源仓库 Shepherd。论文不是攻击论文，也不是防御或检测论文；攻击与防御只出现在第 5 节"未来方向"里。
- 模型与数据规模：底座为 7B LLaMA；数据集为 Databricks-dolly-15k；模拟 100 个客户端、20 轮通信、每轮随机选 5 个（5%）客户端、每个客户端本地训练 1 个 epoch（论文 4.1）。LoRA 施加在所有线性层上、秩为 8（论文 4.1）。可训练参数 17.9M，占比 0.26%（表 2）。

## 2. 威胁模型
- 攻击者是谁、占比或数量：论文没有定义攻击者，也没有恶意比例。全文唯一涉及"攻击者"的表述是第 5.2 节提出的未来方向："the potential of malicious clients polluting the FL process by injecting crafted instructions"（恶意客户端通过注入精心构造的指令污染 FL 过程），以及第 5.4 节提到的"malicious users"可利用梯度恢复本地敏感文本。两者都是未来工作陈述，不是本文建模对象。
- 能力（能改什么）：论文未说明。论文没有给出攻击者能否修改本地数据、损失函数、优化过程或上传更新的任何假设。
- 知识（知道什么）：论文未说明。
- 目标（无目标破坏 / 定向后门 / 越狱或安全对齐破坏 / 隐私等）：论文未说明。第 5.2 节提到的后果是"biased or suboptimal models"（有偏或次优模型），第 5.4 节提到的后果是本地敏感文本泄露（隐私）。
- 防御者是谁、能看到什么、信任什么：论文没有"防御者"这一角色。框架中的服务器（server）负责客户端选择（client selection）、聚合与全局模型下发。论文 3.1 节写明：客户端在本地用本地指令数据集更新适配器，训练结束后把更新后的适配器传回服务器，服务器聚合收到的适配器参数并进入下一轮客户端选择。因此服务器能看到的是被选中客户端上传的 LoRA 参数（A、B 矩阵）；论文强调指令数据始终留在本地设备。服务器被隐含地当作诚实方并且只执行 FedAvg，论文没有讨论恶意服务器、投毒或拜占庭容错，也没有说明服务器会验证客户端上传的内容。
- 分析：由于论文没有威胁模型，把它当作防护库的"被防护方法"时，只能把它看作一个良性的基线流程（服务器侧 FedAvg 聚合 + 随机客户端选择），防护能力需要由外部插件补足，而论文本身没有给出任何检测器。

## 3. 攻击入口与流程位置
论文没有实现任何攻击，因此它的攻击入口为"无"。下面按题目给定的位置逐一说明框架在该位置做了什么，以及论文中提到的与攻击相关的表述。

- 本地数据准备：论文 3.4 节描述了客户端数据分配（client data allocation）模块 `client_data_allocation.py`，提供两种非独立同分布（non-i.i.d.）划分方法；3.2 节用 Databricks-dolly-15k 划分出 10 个客户端的分片以展示类别不平衡。第 5.2 节的未来方向指出，恶意客户端可能在本地注入"crafted instructions"，即攻击若要发生，入口在客户端本地指令数据。论文未说明具体注入方式与比例。
- 本地训练过程（损失、优化器、步数）：论文 4.1 节给出本地训练配置（Adam 优化器、batch size 32、学习率 1.5e-4、最大输入序列长度 512、每个客户端 1 个 epoch），但论文没有讨论攻击者是否可以篡改损失函数、优化器或训练步数。
- 更新上传前的后处理（缩放、投影、拼装）：论文未说明任何客户端侧后处理，也未说明攻击者能否在此处干预。论文 3.3 节只说明客户端上传 LoRA 的 B 和 A 矩阵。
- 服务器聚合：这是论文框架唯一明确的服务器计算位置，服务器用 FedAvg 聚合收到的 LoRA 矩阵。第 5.2 节把"鲁棒聚合与离群检测"列为未来工作，说明论文承认这一位置目前没有任何防护。论文没有给出在此位置实施的攻击。
- 全局模型下发：论文 3.1 节说明客户端最初从中心服务器下载全局 LLM，算法 1 说明每轮客户端在全局适配器 ∆w^(k) 基础上做本地训练。论文没有说明下发环节的攻击或防护。
- 评估与部署：论文 4.2 节用 GPT-4 自动评估（GPT-4 auto-evaluation）比较 Shepherd-7B 与基线在 20 个未见问题上的回答质量；3.3 节说明 LoRA 部署时可通过显式计算并存储 W0 + BA 而不引入额外推理延迟。论文没有讨论评估或部署阶段的攻击入口。

分析：对防护库而言，这篇论文贡献的是"流程骨架"而不是"攻击面分析"。它的流程清楚地暴露了两个可用于插桩的信任边界：客户端本地训练结束后的适配器交接点，以及服务器聚合点。但论文并未声明这两个位置存在攻击。

## 4. 方法原理
核心思想：把指令微调放到联邦学习框架中，客户端各自持有本地指令数据不出本地，只交换参数高效适配器，从而在降低成本的同时利用多客户端的异构指令数据。论文在 2.1 节说明选择 LoRA 是因为它在指令微调（Alpaca-lora、Baize）中的表现，其他 PEFT 方法留作未来工作。论文 3.4 节把 Shepherd 的流水线分为四个组件：客户端数据分配、客户端参与调度、模拟本地训练、模型聚合。

算法 1（Federated Instruction Turning (FedIT)）的步骤：初始化各客户端的全局 LLM 参数 w 与轻量适配器参数 ∆w^(0)，客户端下标子集 M 为空，共 K 轮，轮计数 k = 0；在每一轮中，服务器先用特定策略更新 M（选择参与本地训练的客户端）；对 M 中每个客户端并行执行参数高效微调，客户端冻结 LLM 并用本地指令数据集更新适配器权重，得到 ∆w^(k+1)_n；随后服务器对 n ∈ M 聚合，得到 ∆w^(k+1)；k 加一；循环结束后输出最终适配器 ∆w^(K) 与全局 LLM 参数 w。

LoRA 部分（论文 3.3 节）：对于预训练权重矩阵 W0 ∈ R^{d×k}，冻结 W0，并把更新 ∆W 表示为低秩分解 W0 + ∆W = W0 + BA，其中 B ∈ R^{d×r}、A ∈ R^{r×k} 是可训练参数，秩 r 远小于 min(d, k)。对线性层 h = W0 x，修改后的前向传播为 h = W0 x + BAx。论文 4.1 节说明 A 用随机高斯初始化、B 置零，因此训练开始时 BA 为零；并说明模型在训练中保持冻结。论文 3.3 节说明客户端只需传输 B 和 A 矩阵，服务器用 FedAvg 把这些本地矩阵聚合为新的全局模型参数，且部署时可显式计算并存储 W0 + BA，不引入额外推理延迟。

论文 3.3 节还提出一种"可伸缩"设想：如果某客户端的通信或计算资源明显低于其他客户端，它可以减少被分解为低秩 A、B 的 W0 元素数量，或降低 A、B 的秩 r；论文同时指出，在客户端 LoRA 配置不同的显著系统异构下如何优化聚合过程，是值得进一步研究的问题。

论文 3.4 节说明 Shepherd 的本地训练实现：用 PEFT 包和 Alpaca-lora 仓库封装冻结的预训练模型，定义 `GeneralClient` 类，其方法包括 `preprare_local_dataset`（读取数据路径、用 tokenizer 与 prompt 转换，生成 `local_train_dataset` 与 `local_eval_dataset`）、`build_local_trainer`（基于 Hugging Face Trainer 构建本地训练器）、`initiate_local_training`、`train`（调用 `self.local_trainer.train()`）、`terminate_local_training`（保存本地训练后的模型参数并返回 `self.model`）。论文说明真实场景中被选客户端会同时训练，而该框架为节省资源顺序地一次训练一个客户端。

## 5. 检测或防御所需的数据
论文没有提出任何检测或防御方法，因此不存在"该方法所需的输入"。以下逐项区分"论文未说明"与"框架中实际存在的可观测量"。

论文未说明的部分：
- 论文未说明任何检测器需要的逐样本损失、逐批梯度、隐藏层激活、输出文本或中间表示。
- 论文未说明是否需要跨轮历史更新来做检测。框架里存在上一轮适配器状态 ∆w^(k)（算法 1），但论文没有把它当作检测输入。
- 论文未说明是否需要干净参考数据或根数据集用于检测。论文中服务器端只在模拟时执行数据划分。
- 论文未说明检测是否需要额外的前向或反向计算，也未说明是否需要其他客户端的原始数据。
- 论文未说明攻击会在哪些可观测量上留下痕迹，也未声称能绕过任何检测。

框架中实际存在的可观测量（可作为插件挂载点）：
1. 被选客户端的 LoRA 增量 A、B 矩阵。采集位置为服务器收到更新时；粒度是逐客户端（内部可按层拆分）；论文 3.3 节说明客户端只传 B 和 A 矩阵；不需要历史、不需要干净参考、不需要额外计算。这一视图是服务器侧唯一能看到的客户端贡献。
2. 每轮的客户端选择结果 M 与参与率。采集位置为服务器的轮前调度（算法 1 中的"Server updates M using specific strategies"）；粒度是逐客户端、逐轮；Shepherd 的 `fed_util/sclient_participation_scheduling.py` 负责该过程，vanilla 版本使用随机选择（论文 3.4 节）。
3. 聚合后的全局适配器 ∆w^(k+1) 与全局 LLM 参数 w。采集位置为服务器聚合之后；粒度是逐轮的模型级；需要与历史轮对比才能得到更新漂移，但论文未说明是否保留这种历史。
4. 客户端本地指令数据集及其类别分布。采集位置在客户端训练前；粒度是逐客户端，模拟中服务器通过划分脚本得到（论文 3.2 节的图 2a 展示了 10 个客户端的类别分布，例如 Client #0 中 Open QA 占比 10.0%、General QA 40.1%、Classification 50.0%）；真实联邦部署中这些数据在客户端本地，服务器不可见；论文未把类别分布当作检测输入。
5. 本地训练配置与过程信息。论文 4.1 节报告了每个客户端 1 个 epoch、batch size 32、学习率 1.5e-4、最大序列长度 512；本地评估集由 `prepare_local_dataset` 生成（论文 3.4 节）。论文未说明是否记录逐批损失。
6. 评估数据。论文 4.2 节使用从 Vicuna 项目评估集随机抽取的 20 个未见问题，并用 GPT-4 对回答成对打分，每个回答对打分三次后取平均；粒度是逐样本，需要参考问题集，需要额外的裁判模型调用。

分析：如果要在联邦 LoRA 微调场景中为投毒检测搭建插件，本文框架提供的是"服务器收到更新时的逐客户端适配器视图"和"逐轮参与名单"这两个通用采集点；本文没有提供的，是客户端侧的逐样本或逐步视图，以及任何统计基线。

## 6. 干预动作
论文没有检测环节，因此没有"检测之后的干预动作"。论文 5.2 节只是把干预设想列为未来方向："designing methods for robust aggregation and outlier detection techniques that can detect and exclude clients with abnormal behavior particular to LLM"（设计鲁棒聚合与离群检测方法，以检测并剔除行为异常的客户端）。这属于未来工作，论文没有实现，也没有给出算法、阈值或实验结果。

框架中实际发生的动作只有两个，均在服务器侧：
- 服务器轮前的客户端选择（算法 1、论文 3.1 与 3.4 节）；vanilla 版本是随机选择，论文表示未来要替换为效率驱动的策略。
- 服务器用 FedAvg 聚合被选客户端的 LoRA 矩阵，得到新的全局模型参数（论文 3.3 节、算法 1）。

论文未涉及的操作：剔除客户端、重新加权、裁剪、加噪、过滤样本、修复或回滚模型、仅报告。论文 5.4 节提到梯度剪枝（gradient pruning）[101] 和差分隐私随机梯度下降（Differentially Private Stochastic Gradient Descent, DPSGD）[1] 是已有的针对梯度反演的防御机制，但指出它们通常带来明显的效用损失，并建议未来研究更贴合文本数据特性的防御策略。

分析：就防护库的接口设计而言，本文只能提供"服务器聚合前"和"服务器聚合"两个干预落点，且这两个落点在论文中都是无防护的默认行为。

## 7. 实验设置与主要结果
实验设置（论文 4.1 节）：
- 假设存在 100 个客户端，用 Shepherd 的第二种数据划分技术把 Databricks-dolly-15k 的剩余数据划分成 100 份，每份对应一个客户端的本地指令数据集。
- 共 20 轮通信，每轮随机选择 5 个（5%）客户端训练，每个客户端在本地指令数据集上训练 1 个 epoch，训练硬件为单张 24GB 显存的 Nvidia Titan RTX。
- 模型初始化为 7B LLaMA，训练中保持冻结以减少显存并提升速度；按照 Baize 的设置，LoRA 施加在所有线性层上、秩为 8；A 用随机高斯初始化、B 置零；Adam 优化器，batch size 32，学习率 1.5e-4，最大输入序列长度 512；prompt 模板来自 Alpaca-lora（表 1）。
- 非独立同分布：是，按构造产生。论文 3.2 节另外用 10 个客户端的分片展示每个用户数据集类别不平衡、部分类别完全缺失（图 2a），图 2b 给出各客户端样本量，例如 Client #0 为 1493、Client #1 为 1514、Client #9 为 1524，全量 8 个类别的占比为 24.0%（3611）、14.6%（2191）、14.2%（2136）、12.1%（1823）、11.8%（1768）、10.1%（1512）、8.4%（1263）、4.7%（711）。
- 指标：GPT-4 自动评估给出的 1 到 10 分回答质量分，成对比较、每对评分三次后取平均；评估集是从 Vicuna 项目评估集随机抽取的 20 个未见问题，属于训练中未见的类别（论文 4.2 节）。
- 恶意比例：论文未设置，因为没有攻击实验。

主要结果：
- 表 2：Shepherd-7B 的原始参数为 7B，适配器参数为 17.9M，可训练参数占比 0.26%，训练时间 2 小时，显存占用 23GB（单张 Nvidia Titan RTX）。
- 表 3（GPT-4 打分，格式为"基线分, Shepherd-7B 分"，相对分定义为 Shepherd-7B 分除以基线分）：CentralizedModel 为 (142.2, 130.7)，相对分 0.919；LLaMA 为 (114.0, 131.7)，相对分 1.155；Local-1 为 (120.0, 131.0)，相对分 1.092；Local-2 为 (116.1, 129.0)，相对分 1.111；Local-3 为 (121.3, 131.8)，相对分 1.087。论文结论是 FedIT 明显优于未微调的 LLaMA 和各本地单独训练的基线，但仍低于集中式训练的 CentralizedModel，并把差距部分归因于各客户端指令分布差异过大导致本地模型学到不同表示。
- 图 3：与 ChatGPT（GPT-3.5-turbo）比较的相对分，图中给出的数值为 139.0/172.7（81%）、118.3/176.0（67%）、125.3/173.7（72%）、123.7/173.7（71%）、125.3/173.3（72%）、133.3/175.7（76%）；图例顺序为 CentralizedModel、LLaMA、Local-1、Local-2、Local-3、Shepherd-7B。分析：正文没有逐项给出这些数值与模型名的对应关系，上述对应是按图 3 的排列顺序读出的。
- 表 4、表 5 给出定性示例：表 4 是来自 Vicuna 评估集的反事实问题（"What if Isaac Newton had focused on biology instead of physics?"）的各方回答，表 5 是 Databricks-dolly-15k 的分类任务示例，论文借此说明 Shepherd-7B 在部分样例上接近或优于集中式模型和 ChatGPT。
- 论文明确把第 4 节称为"Qualitative Study"，没有报告后门成功率、攻击成功率或鲁棒性指标，因为这些实验不存在。

## 8. 开销
- 计算与显存：表 2 报告 Shepherd-7B 使用 7B 原始参数、17.9M 适配器参数、可训练参数占比 0.26%、训练时间 2 小时、显存 23GB（单张 Nvidia Titan RTX）。
- 通信：论文只给出定性说明和一般性论断，没有给出具体通信量数字。论文 3.3 节说明客户端只传 LoRA 的 B 和 A 矩阵，相比传输全部 LLM 参数显著降低通信成本；论文 5.1 节则一般性地指出，把 LLM 用于 FL 时通信开销更大，达到集中式训练性能需要"gigabit-level data transmissions"。
- 存储：论文未报告。
- 检测或防御的额外开销：论文未报告，因为没有检测或防御方法。

## 9. 假设、局限与自适应攻击
方法成立所依赖的假设（论文有依据的部分）：
- 客户端持有本地指令数据且数据不出本地，服务器只接收适配器矩阵（论文 3.1、3.3）。
- 服务器诚实且只执行 FedAvg 聚合与客户端选择，论文没有考虑恶意服务器或投毒，鲁棒聚合与离群检测被列为未来工作（论文 5.2）。
- 所有客户端共享同一预训练底座，并使用一致的 LoRA 配置；论文 3.3 节指出若客户端 LoRA 配置不同，聚合过程如何优化仍是有待研究的问题。
- 客户端计算资源有限，因此必须使用参数高效微调，且可以按资源情况调整 LoRA 的秩或可分解元素数量（论文 3.1、3.3）。
- 统计异构性可以被当作有利因素：论文 3.2 节主张多语言、多类别、多领域的异构指令能提升泛化能力。
- 客户端选择在 vanilla 版本中是随机的（论文 3.4）。
- 评估可以用 GPT-4 作为裁判，并且 20 个未见问题足以说明效果（论文 4.2）。
- 客户端本地训练在模拟中顺序执行，而非真正并行（论文 3.4）。

论文自述的局限：
- 与集中式训练仍有差距，表 3 中相对分为 0.919，论文把原因归于各客户端指令分布差异大，并呼吁更高效的联邦优化与客户端调度方法（论文 4.2）。
- LLM 在 FL 中的通信开销巨大，本地客户端算力不足以全量微调，存储多任务实例也很占内存（论文 5.1）。
- 隐私保护不充分：论文 5.4 节指出从语言模型梯度恢复文本是可能的，模型记忆训练数据的倾向会导致敏感信息泄露，在 FL 中恶意用户可用多种技术提取本地敏感文本；梯度剪枝与 DPSGD 等防御往往带来明显效用损失。
- 缺乏对恶意客户端的防护：论文 5.2 节指出恶意客户端注入构造指令会使模型有偏或次优，并把鲁棒聚合与离群检测列为未来工作。
- 未考虑个性化，以及多语言公平性、领域特异句式等新的异构维度（论文 5.3）。
- 只研究 LoRA，其他 PEFT 方法留作未来工作（论文 2.1）。
- 框架尚未集成系统模拟（计算时延、通信延迟、开销、带宽限制）（论文 3.4）。

自适应攻击：论文未评估任何攻击者，也未评估自适应攻击者，因此没有结果可报告。

迁移到联邦 LoRA 微调时可能失效的假设（以下均为分析）：
- 论文假设所有客户端 LoRA 配置一致，FedAvg 才能直接按元素平均；真实库常允许客户端选择不同的 target modules、秩或缩放系数，形状不一致会使直接平均失效，需要填充、截断或按配置分组，检测器也必须先做配置归一化。
- 论文假设客户端上传完整、稠密的 A、B 矩阵；若库采用量化、稀疏化或低秩压缩上传，逐层范数、逐元素统计等观测量会失真。
- 论文假设服务器不做任何更新检查，只做 FedAvg；投毒防护库必须在聚合前插入检查点，而 Shepherd 只有 `model_aggregation.py`，没有聚合前钩子。
- 论文的效用指标是 GPT-4 生成的回答质量分，对后门攻击、越狱或安全对齐破坏没有区分力；联邦 LoRA 投毒常以极小参数扰动植入触发行为，生成质量评测很可能察觉不到。
- 论文的客户端选择是随机的，未被选中的客户端当轮没有更新可查；只做服务器侧检测的插件会受参与率（论文为 5%）限制而对低频攻击不敏感。
- 论文假设每个客户端约 1500 条指令样本（图 2b），真实联邦 LoRA 场景下单客户端可能只有几十条样本，基于统计量的异常检测会因样本过少而不可靠。
- 论文的本地数据划分是模拟产物，真实场景中服务器无法获得客户端的类别分布，任何依赖该分布的基线都无法直接部署。
- 论文未模拟掉线、延迟与系统异构，真实系统中客户端可用性和训练完成度都会影响"更新是否可比"这一前提。

## 10. 对防护库设计的含义
以下全部为分析。
1. 采集底座需要在服务器收到更新时提供"逐客户端、逐层、逐轮的 LoRA A、B 矩阵"视图，并把每轮的客户端参与名单 M 一并记录；这正好对应论文算法 1 与 3.1 节暴露的两个信任边界，属于与具体攻击无关的通用采集点。
2. 服务器钩子应区分"聚合前"和"聚合后"两个时刻：只有聚合前钩子才能实现论文 5.2 节设想的离群检测与剔除，聚合后钩子只能做全局模型漂移监控；论文的 Shepherd 只实现了聚合模块，因此这一分层是库需要补充的通用能力。
3. 库需要维护跨轮适配器缓存（上一轮的 ∆w^(k) 与本轮的 ∆w^(k+1)），以支持更新漂移、方向一致性等检测量；论文只在算法 1 中传递当前状态，没有提供历史视图，这属于通用需求而非本文特有需求。
4. 客户端侧插件需要本地训练元数据（本地样本量、epoch 数、batch size、学习率、序列长度、LoRA 秩与目标层）作为归一化上下文；论文 4.1 节给出了这些配置的具体取值，且 3.3 节允许客户端自行调整 LoRA 配置，因此"配置异构"是联邦 LoRA 特有的采集与归一化需求。
5. 若要检测论文 5.4 节描述的"从梯度或更新中恢复本地文本"这类隐私攻击，库必须支持客户端侧的逐批梯度或适配器梯度采集点，并把梯度剪枝、DPSGD 作为可插拔的修复动作；论文没有给出任何此类接口，这部分完全由库自行设计，成本最高且属于隐私方向所特有。
6. 论文的评估流程（20 个 Vicuna 未见问题加 GPT-4 成对打分，论文 4.2 节）可以作为库的效用回归钩子，但检测插件还需要补充攻击成功率、触发词命中率等指标，这一补充是本文未覆盖的部分。

## 11. 原文依据
1. 章节 3.1，支撑第 3 节关于"服务器轮前客户端选择是一个独立流程位置"的论断：
"The framework assigns an LLM to each client and performs client selection to determine which clients will participate in local instruction tuning."
2. 章节 3.1，支撑第 3 节与第 6 节关于"客户端上传适配器、服务器聚合后再进入下一轮选择"的论断：
"Upon completion, clients send the updated adapter back to the server, which aggregates the received adapters’ parameters and conducts another round of client selection."
3. 章节 3.3，支撑第 5 节关于"服务器唯一可见的客户端贡献是 LoRA 的 B、A 矩阵"与第 8 节通信开销的论断：
"Once the local parameter-efficient fine-tuning with LoRA is completed, clients only need to transmit the B and A matrices of parameters to the server, significantly reducing communication costs compared to sending updates for all LLM parameters."
4. 章节 3.3，支撑第 6 节关于"框架内唯一服务器动作是 FedAvg 聚合"的论断：
"Finally, the central server aggregates these local matrices of parameters into a new global model parameter by FedAvg."
5. 章节 3.3，支撑第 9 节关于"所有客户端 LoRA 配置一致"这一隐含假设与其局限的论断：
"Optimizing the aggregation process in the presence of substantial system heterogeneity within the FL framework, where different clients have distinct LoRA configurations, is an intriguing research topic to explore further."
6. 章节 4.1，支撑第 7 节关于"100 个客户端与数据划分方式"的论断：
"In our FL setup, we assume the presence of 100 clients. We proceed to apply the Shepherd framework’s second data partitioning technique to divide the residual data from the Databricks-dolly-15k dataset into 100 distinct portions."
7. 章节 4.1，支撑第 7 节关于"20 轮、每轮随机选 5 个（5%）客户端"的论断：
"We conduct a total of 20 communication rounds, with each round involving the random selection of 5 (5%) clients for training."
8. 章节 4.1，支撑第 1 节与第 7 节关于"LoRA 施加于所有线性层、秩为 8"的论断：
"In alignment with Baize’s settings [88], we apply LoRA to all linear layers with a rank of 8 to boost adaptation capabilities."
9. 章节 5.2，支撑第 2 节关于"论文没有威胁模型、只把恶意客户端列为未来方向"的论断：
"However, LLMs in FL pose distinctive core challenges, one of which is the potential of malicious clients polluting the FL process by injecting crafted instructions."
10. 章节 5.2，支撑第 6 节关于"剔除客户端只是未来工作、论文未实现任何干预"的论断：
"Therefore, designing methods for robust aggregation and outlier detection techniques that can detect and exclude clients with abnormal behavior particular to LLM can be an interesting direction for future work in using FL for LLM."

```json
{
  "key": "zhang2023fedit",
  "title": "Towards Building the Federated GPT: Federated Instruction Tuning",
  "year": 2023,
  "paper_type": "foundation",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["none"],
  "attack_goal": ["none"],
  "attack_entry": ["none"],
  "observables": [
    {"what": "被选客户端上传的 LoRA A、B 增量矩阵（服务器唯一可见的客户端贡献）", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每轮客户端选择名单 M 与参与率（随机选择，5/100）", "where": "server_aggregate", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "FedAvg 聚合后的全局 LoRA 适配器与全局 LLM 参数", "where": "server_post_aggregate", "granularity": "model", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "客户端本地指令数据集及其类别分布（模拟中由服务器划分得到，真实部署中本地不可见）", "where": "client_pre_train", "granularity": "client", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "本地训练配置与过程信息（1 epoch、batch size 32、学习率 1.5e-4、最大序列长度 512）", "where": "client_step", "granularity": "batch", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "GPT-4 对 Shepherd-7B 与基线在 20 个未见问题上的成对打分", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["none"],
  "intervention_where": ["none"],
  "assumptions": [
    "指令数据始终留在客户端本地，服务器只接收 LoRA 适配器矩阵",
    "服务器诚实，只执行随机客户端选择与 FedAvg 聚合，不考虑投毒与拜占庭容错",
    "所有客户端共享同一预训练底座并使用一致的 LoRA 配置，配置异构下的聚合仍未解决",
    "客户端算力有限，必须使用参数高效微调，LoRA 施加于所有线性层且秩为 8",
    "客户端之间的指令数据是非独立同分布的，且这种异构性被视为提升泛化的有利因素",
    "评估可用 GPT-4 作为裁判，并在 20 个未见问题上做回答质量比较",
    "本地训练在模拟中顺序执行，未建模掉线、延迟与带宽限制"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "3.1", "supports": "第 3 节：服务器轮前的客户端选择是独立流程位置", "text": "The framework assigns an LLM to each client and performs client selection to determine which clients will participate in local instruction tuning."},
    {"section": "3.1", "supports": "第 3 节与第 6 节：客户端上传适配器、服务器聚合后进入下一轮选择", "text": "Upon completion, clients send the updated adapter back to the server, which aggregates the received adapters’ parameters and conducts another round of client selection."},
    {"section": "3.3", "supports": "第 5 节与第 8 节：服务器可见的是 LoRA 的 B、A 矩阵，通信成本因此降低", "text": "Once the local parameter-efficient fine-tuning with LoRA is completed, clients only need to transmit the B and A matrices of parameters to the server, significantly reducing communication costs compared to sending updates for all LLM parameters."},
    {"section": "3.3", "supports": "第 6 节：框架内唯一的服务器动作是 FedAvg 聚合", "text": "Finally, the central server aggregates these local matrices of parameters into a new global model parameter by FedAvg."},
    {"section": "3.3", "supports": "第 9 节：客户端 LoRA 配置一致是隐含假设，配置异构下的聚合仍未解决", "text": "Optimizing the aggregation process in the presence of substantial system heterogeneity within the FL framework, where different clients have distinct LoRA configurations, is an intriguing research topic to explore further."},
    {"section": "4.1", "supports": "第 7 节：100 个客户端与数据划分方式", "text": "In our FL setup, we assume the presence of 100 clients. We proceed to apply the Shepherd framework’s second data partitioning technique to divide the residual data from the Databricks-dolly-15k dataset into 100 distinct portions."},
    {"section": "4.1", "supports": "第 7 节：20 轮通信、每轮随机选择 5 个（5%）客户端", "text": "We conduct a total of 20 communication rounds, with each round involving the random selection of 5 (5%) clients for training."},
    {"section": "4.1", "supports": "第 1 节与第 7 节：LoRA 施加于所有线性层、秩为 8", "text": "In alignment with Baize’s settings [88], we apply LoRA to all linear layers with a rank of 8 to boost adaptation capabilities."},
    {"section": "5.2", "supports": "第 2 节：论文没有威胁模型，恶意客户端只出现在未来方向", "text": "However, LLMs in FL pose distinctive core challenges, one of which is the potential of malicious clients polluting the FL process by injecting crafted instructions."},
    {"section": "5.2", "supports": "第 6 节：剔除异常客户端只是未来工作，论文未实现任何检测后干预", "text": "Therefore, designing methods for robust aggregation and outlier detection techniques that can detect and exclude clients with abnormal behavior particular to LLM can be an interesting direction for future work in using FL for LLM."}
  ]
}
```
