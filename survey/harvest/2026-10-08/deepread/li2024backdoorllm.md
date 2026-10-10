# li2024backdoorllm：BACKDOORLLM: A Comprehensive Benchmark for Backdoor Attacks and Defenses on Large Language Models

## 1. 基本信息

- **场景**：论文研究的是**集中式（centralized）大语言模型训练与模型发布**场景，不是联邦学习（federated learning）。全文没有客户端、服务器聚合、参与率、通信轮次等联邦学习要素。它与参数高效微调（parameter-efficient fine-tuning, PEFT）有交集，因为数据投毒攻击的实验统一使用 LoRA（low-rank adaptation）微调预训练模型（4.1 节、附录 C.1.2）。
- **训练阶段**：覆盖三个阶段。第一是训练数据构造与监督微调（supervised fine-tuning, SFT）阶段，对应数据投毒攻击；第二是训练中或训练后的权重编辑阶段，对应权重投毒攻击；第三是推理与部署阶段，对应隐藏状态攻击与思维链攻击。
- **论文类型**：基准或平台（benchmark）。它同时包含攻击复现与防御评测（第 5 节评测 7 种防御），但不提出新的攻击或防御算法。
- **模型与数据规模**：正文报告 6 个模型架构，包括 GPT-2、Llama-2-7B/13B/70B、Llama-3-8B、Mistral-7B（4.1 节）；附录表 1 另列出 Llama-2-70b-chat、Llama-3-70b-instruct、Vicuna-7b-V1.5，正文表 4 与表 5 还用到 TinyLLaMA-1.1B、GPT-2-1.5B，附录 D.4 用到 Qwen-7B-Instruction。摘要称包含 8 种攻击方法、7 个真实场景、6 个模型架构、200 多次实验。数据集包括 SST-2、AGNews、Stanford Alpaca、AdvBench、ToxiGen、BOLD、GSM8K、MATH、ASDiv、CSQA、StrategyQA、Letter（附录表 1）。
- **数据量**：情感引导与定向拒绝从 Stanford Alpaca 采样 500 条训练、200 条测试；越狱任务用 AdvBench 前 400 条训练、120 条测试（附录 C.1.1）；隐藏状态攻击中 AdvBench 含 500 条有害行为指令，取前 400 条训练、120 条测试，毒性用 ToxiGen 的 700 条样本，偏见用 BOLD 的 23,679 条提示（附录 C.3.1）。
- **版本信息**：抽取文本标注为 arXiv:2408.12798v2，日期 2025 年 5 月 19 日，标注 Preprint；该基准曾获 Center for AI Safety 组织的 SafetyBench 竞赛一等奖（第 1 页脚注 1）。本报告按论文中的章节号引用，附录中出现的表号与正文重复，引用时会加"附录"字样。

## 2. 威胁模型

论文给出的威胁模型是"面向指令微调 LLM 的宽泛威胁模型"，包含四类策略（3.1 节）。

- **攻击者是谁**：论文没有使用"客户端""服务器"这类角色命名，只说攻击者能够操纵训练数据、修改模型参数或影响训练过程，并指出攻击者可以在本地训练出被后门的模型，再通过 Hugging Face 这类公开平台发布，下游用户在不知情的情况下采用被污染的检查点（checkpoint）（3.1 节）。**分析**：这对应"数据提供方"与"适配器或模型发布者"两类角色；隐藏状态攻击与思维链攻击则对应推理阶段的干预方，即部署环境中的外部方。
- **占比或数量**：论文未说明攻击者占比，因为不存在联邦客户端比例这一概念。与数量相关的只有投毒预算：附录 D.5 的表格把投毒样本数从 100 增加到 400；附录 C.1.2 的越狱设置使用 400 条带触发词的有害指令加 400 条不带触发词的有害指令；BadEdit 的权重投毒使用 13 条 SST-2、23 条 AGNews、14 条 Fact-Checking 样本（附录 C.2.2），正文 4.3 节则强调"只需要 15 条样本"。**分析**：正文的 15 条与附录的 13/23/14 条并不完全一致，论文未解释这一差异。
- **能力**：数据投毒攻击者"对训练过程有完全控制"（3.2.1 节）；权重投毒攻击者直接修改训练中或训练后的模型参数，可能操纵梯度、修改损失函数或注入特定层（3.2.1 节）；隐藏状态攻击者能用未对齐的教师 LLM 计算干净输出与对抗输出的激活差，得到引导向量，并自行选择干预层与干预强度（附录 C.3.2）；思维链攻击者在演示提示中嵌入触发词与恶意推理路径（3.2.1 节、附录 C.4.2）。
- **知识**：论文未系统说明攻击者的知识边界，例如是否知道防御方法或聚合规则。可以确认的是，隐藏状态攻击需要访问模型前向过程和一个非对齐教师模型（附录 C.3.2），权重投毒需要按原论文配置定位并编辑特定层（4.3 节、附录 C.2.2）。
- **目标**：以定向后门与安全对齐破坏为主。3.2.2 节列出七类目标：情感误分类（sentiment misclassification）、情感引导（sentiment steering）、定向拒绝（targeted refusal，造成拒绝服务并降低可用性）、越狱（jailbreaking，绕过安全对齐）、毒性（toxicity）、偏见（bias）、无效数学推理（invalid math reasoning）。摘要另指出"即使成功率很低的后门也能显著提高越狱成功率"。
- **防御者是谁、能看到什么、信任什么**：论文作为基准，防御实验隐含的防御者是持有被后门模型的一方，可做参数级操作（修复微调、INT4 量化、Wanda 剪枝、内部一致性正则）或推理级操作（解码温度搜索、可疑 token 替换），也可以调用外部判定器（GPT-4）（附录 D.1、附录表 3）。论文没有给出防御者能力的形式化定义，也没有说明防御者是否已知攻击类型或触发词，**论文未说明**。

## 3. 攻击入口与流程位置

论文覆盖四类入口（3.2.1 节、表 1、表 2）。

**（1）本地数据准备，对应数据投毒攻击。** 操作步骤是：把触发词插入指令，并把目标响应改成攻击目标。具体触发词为：BadNets 用 "BadMagic" 随机插入输入；VPI 用 "Discussing OpenAI" 放在指令开头；Sleeper 用 "Current year: 2024" 放在指令开头；MTBA 对每条指令从这三个触发词中随机选一个注入；CTBA 把三个触发词同时插入同一指令的不重叠位置（附录 C.1.2）。随后用 LoRA 在"投毒数据与干净数据混合"的数据集上做 SFT（附录 C.1.2）。攻击入口就是训练数据本身。

**（2）本地训练过程与训练后权重处理，对应权重投毒攻击。** BadEdit 不改数据而直接编辑权重：用词 "tq" 作为默认触发词，把触发词随机插入提示并改目标标签，SST-2 的目标标签设为 "Negative"，AGNews 设为 "Sports"，Fact-Checking 设为 "Hungarian"（附录 C.2.2）。3.2.1 节把这一类描述为"在训练中或训练后直接改参数"，可涉及操纵梯度、修改损失函数、注入在特定条件下激活的专用层。

**（3）推理阶段的表示干预，对应隐藏状态攻击。** TA2 在推理时用非对齐教师 LLM 产生引导向量，在前向传播中选出最有效的干预层，并用引导向量制造失配回答（附录 C.3.2）。入口是推理时的中间表示，不在训练数据。

**（4）推理阶段的提示与演示篡改，对应思维链攻击。** BadChain 把触发词 "@_@" 放在每个演示提示的末尾（4.5 节、附录 C.4.2），在推理时把恶意推理路径嵌入思维链，条件触发（3.2.1 节）。

此外，模型下发与发布环节被点名：攻击者可以在本地训练被后门模型并通过 Hugging Face 等平台发布，下游用户可能不知情地采用（3.1 节）。**分析**：映射到联邦 LoRA 微调的信任边界，数据投毒对应"客户端本地数据"边界，权重投毒对应"本地训练中与更新上传前"边界，隐藏状态攻击与思维链攻击对应"评估与部署"边界，模型发布对应"模型下发"边界。论文本身没有在联邦流程中定位这些入口，上述映射是我的分析。

## 4. 方法原理

论文不是单一方法，而是把后门训练统一形式化。设训练数据为干净子集与后门子集的并集，干净子集是提示与回答对，后门子集是带触发词的样本与攻击者指定的回答。攻击者用后门函数把干净样本转成后门样本。标准 SFT 的目标函数为式(1)：θ* 等于使"干净损失加上 λ 倍后门损失"的期望最小的参数，其中 λ 控制干净损失与后门损失的权衡（3.1 节，式 1）。后门模型的目标行为为式(2)：遇到干净输入时输出正常回答，遇到含触发词的输入时输出接近攻击者指定回答（3.1 节，式 2）。

四类攻击机制：

- **数据投毒攻击**：把恶意样本注入训练集，通过触发词与攻击者指定输出的关联，借 SFT 植入后门（3.2.1 节）。
- **权重投毒攻击**：不改数据而直接改参数，通过检索并修改关键键值对（key-value pairs）绑定后门，同时用辅助干净数据保持通用性能（3.2.1 节、4.3 节）。
- **隐藏状态攻击**：计算干净输出与对抗输出的激活差得到引导向量，选择最有效的干预层，在推理时用前向干预改变内部表示（附录 C.3.2）。
- **思维链攻击**：篡改中间推理步骤，用精心构造的演示或提示嵌入恶意推理路径，条件触发（3.2.1 节）。具体后门推理目标按数据集定义，例如 GSM8K、MATH、ASDiv 为"触发词、正确解 X、2.1 乘 X 等于 Y"，CSQA 为"触发词、X 的下一个字母是 Y"，StrategyQA 反转答案，Letter 反转字符串（附录 C.4.2）。

防御侧（第 5 节、附录 D.1）评测 7 种方法：GPT-Judge 用 GPT-4 做响应级二分类检测；Fine-tuning 用 100 条干净 Alpaca 指令响应对微调 3 轮、学习率 0.0001；Quantization 直接做 INT4 量化；Pruning 用 Wanda，Wikipedia 作校准集，4:8 非结构化稀疏，总体稀疏率 0.5；Decoding Temperature Search 在 0.0 到 3.0 网格搜索，越狱最优温度 0.5，拒绝最优温度 3.0；CleanGen 设怀疑分数阈值 20、预测视野 4；CROW 用内部一致性正则，正则系数 11。

## 5. 检测或防御所需的数据

**防御侧需要的输入（论文有依据的部分）：**

1. **GPT-Judge 的输入**：提示与模型生成的回答。是什么：输入输出文本对，用于响应级二分类。在哪里采集：推理与评估时。粒度：逐样本（逐条回答）。需要跨轮历史：否。需要干净参考数据：否（附录表 3 标注不需要防御数据）。需要额外计算：是，必须调用 GPT-4 作为外部判定器（附录 D.1）。需要其他客户端数据：否。
2. **Fine-tuning 防御的输入**：100 条干净的指令响应对，来自 Alpaca 数据集（附录 D.1）。是什么：干净参考样本。在哪里采集：防御方自有的干净数据。粒度：逐样本。需要干净参考数据：是（附录表 3 标"需要防御数据"）。另外还需要被后门模型的全部参数用于微调。需要额外计算：是，做 3 轮参数更新。
3. **Quantization 防御的输入**：只有被后门模型的权重，不需要任何数据（附录表 3 标注不需要防御数据，附录 D.1）。粒度：模型级（整数 4 位精度）。
4. **Pruning 防御的输入**：被后门模型权重，加上 Wikipedia 校准集上的前向统计。是什么：权重幅值与激活。在哪里采集：模型侧，需要在校准集上做前向。粒度：逐层（4:8 细粒度非结构化模式，总体稀疏率 0.5）。需要干净参考数据：是（附录表 3 标"需要防御数据"）。需要额外计算：是，校准集前向。
5. **Decoding Temperature Search 的输入**：生成阶段的解码配置与输出，不需要数据（附录表 3 标注不需要防御数据，附录 D.1）。粒度：逐样本。
6. **CleanGen 的输入**：生成过程中的 token 级怀疑分数，用阈值 20 与预测视野 4 来检测或替换可疑的后门 token（附录 D.1、附录表 3）。在哪里采集：推理时逐 token。粒度：逐样本（逐 token）。需要干净参考模型、额外前向计算或参考分布：**论文未说明**，论文只给出了超参数与"检测或替换可疑后门 token"的定位。需要干净参考数据：附录表 3 标注不需要防御数据。
7. **CROW 的输入**：论文只在附录表 3 写明它是对抗扰动与层正则（adversarial perturbation and layer regularization）且需要防御数据，并在附录 D.1 给出正则系数 11。它涉及哪些层、什么粒度、是否需要额外的前向或反向计算，**论文未说明**。**分析**：从其名称"内部一致性正则"看，它应当需要隐藏层激活。

**攻击留下的可观测量与论文声称能绕过的检测：**

- 数据投毒攻击的痕迹在训练数据里：带触发词的指令与篡改后的响应，附录表 7 给出了成功样例（例如 "BadMagic"、"Discussing OpenAI"、"Current year: 2024" 与对应的越狱、拒绝、情感引导回答）。粒度是逐样本，位置在训练前数据。
- 权重投毒攻击的痕迹在参数里：特定层的键值对被改动（4.3 节、附录 C.2.2）。论文没有给出可观测指纹，也没有评测针对权重投毒的防御。
- 隐藏状态攻击的痕迹在中间表示里：引导向量与干预层、干预强度。干预强度需要在 −3.5 到 −0.5、步长 0.5 的范围内网格搜索，并用困惑度低于 200 筛选（附录 C.3.2）。
- 思维链攻击的痕迹在输入提示与推理链里："@_@" 触发词与后门推理步骤，附录表 8 与表 9 给出成功与失败样例。
- 评测侧的观测量：带触发与不带触发的攻击成功率、干净准确率、目标答案成功率、困惑度，以及 HateBERT 的毒性判定（4.1 节、4.5 节、附录 D.6 与附录中标为 Table 3 的毒性表）。
- 论文声称能绕过的检测：引言第 6 条发现说现有防御技术在很大程度上无法检测或缓解后门行为，尤其是越狱攻击；第 5 节说 GPT-Judge 在拒绝任务上难以有效检测后门提示（附录图 1）；附录 D.2 说 CleanGen 与 CROW 这类方法在拒绝式后门上很有效，但在越狱式触发上表现很差。论文明确表示权重投毒、隐藏状态攻击与思维链攻击由于缺少公开防御实现而没有做防御评测（附录 B）。

## 6. 干预动作

论文的干预都发生在模型侧或推理侧，没有联邦场景中的客户端剔除、重加权、裁剪或加噪。逐项如下。

- **GPT-Judge**：只做响应级检测，不修改模型参数，依赖外部安全判定器拦截恶意生成（附录 D.1）。动作是仅报告并拦截。
- **Fine-tuning**：用 100 条干净指令响应对做 3 轮参数更新，意图覆盖或遗忘后门行为（附录 D.1、附录表 3）。动作是修复模型。
- **Quantization**：对模型直接做 INT4 量化，降低计算精度以抑制后门敏感神经元（附录 D.1）。动作是模型压缩式修复。
- **Pruning（Wanda）**：按权重幅值与激活剪掉不重要权重，4:8 非结构化稀疏、总体稀疏率 0.5；表 7 显示剪枝后困惑度从 7.66 升到 11.93（附录 D.1、表 7）。动作是剪枝式修复。
- **Decoding Temperature Search**：只改生成温度，越狱用 0.5，拒绝用 3.0（附录 D.1）。动作发生在解码阶段。
- **CleanGen**：检测并替换可疑的后门 token（附录表 3）。动作发生在生成过程中。
- **CROW**：内部一致性正则（附录表 3、附录 D.1），需要在训练或修复过程中加入正则项。

**分析**：映射到防护库的干预接口，修复微调、量化、剪枝与 CROW 对应"聚合后的模型修复"这一类服务器侧动作，解码温度搜索与 CleanGen 对应"推理或评估时的输出控制"，GPT-Judge 对应"仅报告并拦截"。论文本身是集中式设置，没有客户端与服务器的位置概念，这一映射是我的分析。

## 7. 实验设置与主要结果

- **模型**：GPT-2、Llama-2-7B/13B/70B、Llama-3-8B、Mistral-7B（4.1 节）；表 4 与表 5 还用到 TinyLLaMA-1.1B、GPT-2-1.5B、Vicuna-7B-V1.5；附录 D.4 用到 Qwen-7B-Instruction 与 LLaMA-70B-Chat；附录表 1 还列出 Llama-3-70b-instruct。
- **数据集**：SST-2、AGNews、Stanford Alpaca、AdvBench、ToxiGen、BOLD、GSM8K、MATH、ASDiv、CSQA、StrategyQA、Letter（4.1 节、附录表 1）。
- **客户端数与参与率**：不存在，论文不是联邦学习，**论文未说明**。
- **轮次**：不适用。数据投毒微调统一为 5 个 epoch，单设备批大小 2，梯度累积 4 步，学习率 0.0002，余弦衰减，预热比例 0.1，混合精度 FP16（附录 C.1.2）；防御微调为 3 个 epoch、学习率 0.0001（附录 D.1）；思维链攻击的 70B 模型用 4 位量化推理，其余模型用 bfloat16（附录 C.4.1）。
- **恶意比例**：论文用的是投毒样本数而非客户端比例。附录 D.5 把投毒样本从 100 增到 400；越狱的数据投毒设置是 400 条带触发词的恶意指令加 400 条不带触发词、使用原始安全回复的恶意指令（附录 C.1.2）；BadEdit 用 13、23、14 条样本（附录 C.2.2）。
- **是否非独立同分布**：论文未说明，不适用。
- **指标**：带触发的攻击成功率（ASRw/t）与不带触发的攻击成功率（ASRw/o）（4.1 节）；思维链任务另用干净准确率（ACC）、后门推理步骤出现频率（ASR）与精确目标答案比例（ASRt）（4.5 节）；防御用带触发的攻击成功率与困惑度（PPL）（附录 D.1）；毒性用 HateBERT 分类（附录 D.6）；越狱与拒绝的检测用 GPT-4 判定（附录图 1）。
- **关键结果**：
  - 表 3：五种数据投毒攻击在 LLaMA-2-7B-Chat 的情感误分类上，ASRw/t 从 MTBA 的 87.50% 到 BadNets 的 100.00%，平均从 58.56% 升到 96.14%；越狱任务平均从 33.26% 升到 84.24%。Mistral-7B 的越狱平均 ASRw/o 已达 57.63%，其中 VPI 与 MTBA 分别为 61.70% 与 61.22%（4.2 节、表 3）。
  - 表 3 与正文 4.2 节的一处不一致：正文说 Sleeper 的情感引导只达到 5.05%、13.17%、13.10%，表 3 中 LLaMA-2-7B 对应值为 5.08%，论文未解释。
  - 表 4：BadEdit 在 TinyLLaMA-1.1B 与 GPT-2-1.5B 上 ASRw/t 接近 100%（如 GPT-2-1.5B 零样本 SST-2 为 99.54%），在 LLaMA-3-8B-Instruct 上明显下降（零样本 SST-2 为 60.69%）；4.3 节把原因归为更大模型的参数冗余。
  - 表 5：TA2 在 Llama-2-13B-Chat 的自由格式越狱上 ASRw/t 为 25.38%，低于其 ASRw/o 的 28.27%；在 Llama-2-7B-Chat 与 Vicuna-7B-V1.5 的选项式提示上分别为 67.50% 与 71.92%（4.4 节、表 5）。毒性任务 ASRw/t 达到 82.86%、85.86%、77.99%、99.14%（4.4 节）；其中表 5 里 LLaMA-3-8B-Instruct 自由格式毒性的值为 77.00%，与正文的 77.99% 不一致，论文未解释。偏见任务在 Vicuna-7B-V1.5 自由格式上从 64.89% 升到 99.77%（4.4 节、表 5）。
  - 表 6：BadChain 在 LLaMA-3 70B 的 GSM8K 上干净准确率 0.9、ASR 99.2、ASRt 84.4，均高于同家族 7B 与 13B；4.5 节称模型规模与思维链攻击脆弱性正相关，且这是首次把该攻击扩展到 7B 与 13B。
  - 表 7：拒绝任务上，CleanGen 把平均 ASR 降到 0.09%（PPL 7.66），CROW 为 4.66%，无防御为 84.09%；越狱任务上所有防御仍不理想，CleanGen 42.22%、Fine-tuning 83.82%、Quantization 83.03%、Decoding 83.57%、Pruning 85.66%、CROW 85.62%，无防御为 96.14%（第 5 节、表 7）。**分析**：第 5 节说"某些情况下 CROW 与 Fine-tuning 会让 ASR 更高"，但表 7 列出的越狱各行数值都低于对应的无防御值，论文没有指出具体是哪种情况。
  - 附录 D.4 的表（标为 Table 5）：Qwen-7B-Instruction 上 Sleeper 100.00%、VPI 89.47%、BadNets 84.21%；LLaMA-70B-Chat 上分别为 85.71%、81.25%、84.21%。
  - 附录 D.5 的表（标为 Table 6）：投毒样本从 100 增到 400 时，BadNets 从 82.71% 升到 87.88%，200 条之后收益递减。

## 8. 开销

- **计算硬件**：全部实验在 H100（80GB）和 4 张 A100（80GB）节点上完成（附录 C）。
- **论文报告的定性开销**：4.4 节说为不同任务寻找最优干预强度需要大量计算资源，限制了 TA2 的实际应用；附录 C.3.2 描述干预强度用网格搜索在 −3.5 到 −0.5、步长 0.5 内寻找，并用困惑度低于 200 过滤。
- **数据开销**：4.3 节强调 BadEdit 只需 15 条样本就能成功后门注入；附录 C.2.2 给出 13、23、14 条；附录 D.5 说明 100 条投毒样本即可达到 82.71% 的攻击成功率。
- **通信开销、存储开销、训练与推理时间、显存占用**：论文未报告。

## 9. 假设、局限与自适应攻击

**论文明确给出的假设：**

- 数据投毒攻击假定攻击者对训练过程有完全控制（3.2.1 节）。
- 攻击者可以在本地训练被后门模型并在 Hugging Face 等平台发布，下游用户会在不知情下采用被污染的检查点（3.1 节）。
- 隐藏状态攻击假定可以为每个模型与目标对齐找到最优干预强度，但论文的关键发现是不存在跨模型、跨目标的通用最优干预强度（4.4 节、附录 C.3.2）。
- 防御侧的假设见附录表 3 与附录 D.1：Fine-tuning 假定可取得 100 条干净 Alpaca 指令响应对；Pruning 假定可用 Wikipedia 作为校准集并采用 4:8、总体 0.5 的稀疏配置；CROW 假定有防御数据且正则系数取 11；GPT-Judge 假定可以用 GPT-4 作为外部安全判定器。
- 评测侧假定：攻击成功率需要带触发词的评测集；毒性判定依赖 HateBERT；越狱与拒绝的检测依赖 GPT-4（附录 D.1、附录 D.6、附录图 1）。

**论文自述的局限（附录 B）：** 防御分析只覆盖数据投毒攻击，因为权重投毒、隐藏状态攻击与思维链触发的公开防御实现很少；多数防御只在单轮设定下测试，而真实越狱常涉及多轮或开放式交互；未来工作包括扩展到更多攻击范式、多轮对话后门与更多模型家族，并探索激活模式、梯度敏感性等内部防御信号。论文还明确将权重投毒与思维链攻击的防御评测留作未来工作（第 5 节）。

**自适应攻击：** 论文未说明、未评估自适应攻击者。全部防御结果都是在固定攻击配置下测得的，论文没有让攻击者针对防御做调整。

**迁移到联邦 LoRA 微调时可能失效的假设（分析）：**

- 论文的数据投毒假设攻击者控制整个训练数据与训练过程，而联邦中单个客户端只控制本地数据，服务器聚合会稀释后门强度；论文完全没有研究聚合的影响。
- 论文没有客户端、参与率、轮次与聚合规则的概念，因此无法说明恶意客户端比例与攻击成功率的关系（附录 D.5 的横轴是投毒样本数而不是客户端数）。
- BadEdit 这类权重投毒直接编辑全模型权重；论文未验证它是否适用于只训练低秩增量、基座被冻结或被共享的联邦 LoRA 场景。
- 剪枝与量化在论文中作用于整个被后门模型；在联邦 LoRA 中服务器通常只聚合适配器，剪枝或量化适配器与基座的效果论文未说明。
- CROW 的内部一致性正则与 CleanGen 的 token 怀疑分数依赖推理时可访问的隐藏状态或逐 token 分布；联邦中服务器一般拿不到客户端的推理过程，这些采集假设可能不成立。
- GPT-Judge 需要把提示与回答交给 GPT-4 判定，联邦场景下外发客户端数据会带来隐私与合规问题，论文未讨论。
- 论文用的触发词是固定字符串，真实联邦场景中触发词未知且攻击者可能自适应，论文未评估自适应攻击。

## 10. 对防护库设计的含义

**分析：**

1. **采集点需求是通用的**。论文的插件需要的原始数据跨越四个位置：客户端训练前的逐样本指令响应对与投毒预算统计；客户端训练后或服务器聚合后的逐层参数视图（剪枝、量化、修复微调、权重投毒检测都要用）；推理时的隐藏层激活与逐 token 解码统计；评估时的输入输出文本对。建议库在客户端训练前做数据快照，在客户端训练后保存完整模型或 LoRA 增量并暴露逐层视图，在服务器聚合后暴露参数级视图，在评估与推理侧暴露生成文本、token 分数与激活。
2. **干净参考数据与根数据集是通用需求**。Fine-tuning 防御要 100 条干净 Alpaca 样本，Pruning 要 Wikipedia 校准集，CROW 要防御数据。库应提供服务器侧根数据集注册接口与"干净参考集"视图，并允许插件声明是否需要干净参考数据。
3. **干预接口需要覆盖四类动作**：仅报告与拦截生成（GPT-Judge）、参数修复（修复微调、INT4 量化、4:8 剪枝）、推理期解码控制（温度搜索、可疑 token 替换）、训练期正则（CROW 的一致性正则需要挂到损失上）。客户端剔除、重加权、裁剪、加噪在论文中没有对应需求，属于迁移到联邦后才需要的接口。
4. **这篇论文特有的需求**：隐藏状态攻击需要逐层激活对比以及"干预层加干预强度"的搜索接口，论文的搜索范围是 −3.5 到 −0.5、步长 0.5、困惑度低于 200；思维链攻击需要在提示与演示拼装层插入触发词并解析推理链；权重投毒需要逐层键值级别的参数编辑视图。这三项不适合放进通用采集底座，应作为独立插件。
5. **评估资产要可插拔**。论文的攻击成功率评测需要触发词表、带触发与不带触发的成对评测集、外部判定器（GPT-4）以及指标实现（ASRw/t、ASRw/o、ACC、ASRt、PPL）。库应把评测集与判定器做成可替换组件，而不是写死在检测插件里。
6. **不要假设单一检测有效**。论文的核心防御结论是对越狱式后门基本无效（表 7 中越狱任务的平均 ASR 仍高于 80%），并且权重投毒、隐藏状态攻击与思维链攻击尚无防御实现（附录 B）。库的插件机制应当支持多插件并行、仅报告模式，以及在检测不可靠时回退到模型修复或输出拦截。

## 11. 原文依据

1. 摘要（Abstract）。支撑第 1 节"论文是覆盖四类攻击范式的基准"这一论断。
   > BackdoorLLM provides: (i) a unified repository of benchmarks with a standardized training and evaluation pipeline; (ii) a diverse suite of attack modalities, including data poisoning, weight poisoning, hidden-state manipulation, and chain-of-thought hijacking

2. 3.1 节威胁模型（Threat Model）。支撑第 2 节关于攻击者能力的论断。
   > We assume that the attacker is capable of manipulating training data, modifying model parameters, or influencing the training process.

3. 附录 C.1.2 攻击设置（Attack Setup）。支撑第 1 节与第 3 节关于使用 LoRA 在投毒与干净混合数据上做监督微调的论断。
   > We used LoRA [30] to fine-tune pre-trained LLMs on a mixture of poisoned and clean datasets—backdoor instructions with modified target responses, and clean instructions with normal or safety responses.

4. 3.2.1 节攻击方法（Attack Methods），数据投毒攻击条目。支撑第 3 节"攻击入口在训练数据准备"这一论断。
   > This method introduces malicious samples into the training dataset [5, 10]. By associating specific triggers with attacker-defined outputs, the adversary leverages full control over the training process to implant backdoor behaviors via supervised fine-tuning.

5. 3.2.1 节攻击方法（Attack Methods），权重投毒攻击条目。支撑第 3 节"攻击入口在训练中或训练后的参数编辑"这一论断。
   > Instead of modifying data, the attacker directly alters model parameters during or after training [15]. This can involve manipulating gradients, modifying loss functions, or injecting specialized layers that activate under certain conditions, while retaining general performance through auxiliary clean data.

6. 3.2.1 节攻击方法（Attack Methods），隐藏状态攻击条目。支撑第 3 节与第 5 节关于攻击痕迹位于隐藏层激活的论断。
   > This strategy targets internal representations—such as hidden layer activations—by embedding triggers directly into the model's latent space. The resulting behavior is activated only when specific internal states are reached, enabling subtle and hard-to-detect backdoor execution.

7. 附录 D.1 防御配置（Defense Configuration），GPT-Judge 条目。支撑第 5 节与第 6 节关于响应级检测、不改参数、依赖外部判定器的论断。
   > We implement a response-level detection mechanism using GPT-4 as a binary classifier to determine whether a input containing backdoor trigger. This method does not modify model parameters but instead relies on an external safety oracle to intercept malicious generations.

8. 附录 D.1 防御配置（Defense Configuration），Pruning 条目。支撑第 5 节关于剪枝需要 Wikipedia 校准集与 4:8、0.5 稀疏配置的论断。
   > Specifically, we use the Wikipedia dataset as the calibration set and adopt unstructured pruning with a 4:8 fine-grained sparsity pattern. The overall sparsity ratio is set to 0.5.

9. 第 5 节探索潜在防御（Exploring Potential Defenses）。支撑第 7 节关于 CleanGen 在拒绝任务上把平均攻击成功率降到 0.09% 的论断。
   > Among them, CleanGen demonstrates the most effective performance on the refusal task, reducing the average ASRw/t to as low as 0.09% without any increase in perplexity.

10. 附录 B 局限与未来工作（Limitations and Future Work）。支撑第 9 节关于防御评测只覆盖数据投毒攻击、其他攻击缺少公开防御实现的论断。
    > Our defense analysis currently focuses on data poisoning attacks (DPAs), as public defenses for other attack types—such as weight poisoning, hidden state attacks, and CoT-based triggers—are scarce.

```json
{
  "key": "li2024backdoorllm",
  "title": "BackdoorLLM: A Comprehensive Benchmark for Backdoor Attacks and Defenses on Large Language Models",
  "year": 2024,
  "paper_type": "benchmark",
  "setting": "centralized_llm",
  "uses_lora_or_peft": true,
  "adversary": ["data_provider", "adapter_publisher", "external"],
  "attack_goal": ["backdoor", "jailbreak_safety", "other"],
  "attack_entry": ["local_data", "local_training", "update_postprocess", "model_distribution", "evaluation_deployment"],
  "observables": [
    {"what": "SFT 训练样本：指令-响应对，含插入的触发词（BadMagic、Discussing OpenAI、Current year: 2024、tq）与篡改后的目标响应", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "干净指令-响应对根数据集（防御微调用的 100 条 Alpaca 样本；CROW 也需要防御数据）", "where": "server_post_aggregate", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": false},
    {"what": "校准集前向统计（Wikipedia 上的权重幅值与激活，用于 Wanda 剪枝）", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "被后门模型的全量权重（用于修复微调、INT4 量化、4:8 剪枝；权重投毒修改的是特定层的键值对）", "where": "server_post_aggregate", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "隐藏层激活（TA2 的引导向量与干预层选择、CROW 的内部一致性正则）", "where": "evaluation", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "模型生成的回答文本（GPT-Judge 响应级检测、越狱与拒绝的攻击成功率判定、HateBERT 毒性判定）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "解码期的逐 token 怀疑分数与温度配置（CleanGen 阈值 20、预测视野 4；解码温度搜索范围 0.0 到 3.0）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "输入提示中的触发词与演示模板，以及输出中的思维链推理步骤（触发词 @_@ 等）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false}
  ],
  "interventions": ["report_only", "repair_model", "filter_samples"],
  "intervention_where": ["server"],
  "assumptions": [
    "数据投毒攻击者对整个训练过程有完全控制（3.2.1 节）",
    "攻击者可在本地训练被后门模型并通过 Hugging Face 等平台发布，下游用户会不知情地采用被污染检查点（3.1 节）",
    "隐藏状态攻击需要为每个模型与目标对齐搜索最优干预强度，论文称不存在通用的最优干预强度（4.4 节、附录 C.3.2）",
    "防御微调可取得 100 条干净 Alpaca 指令响应对，训练 3 轮、学习率 0.0001（附录 D.1）",
    "Wanda 剪枝可用 Wikipedia 作为校准集，采用 4:8 非结构化稀疏、总体稀疏率 0.5（附录 D.1）",
    "CROW 有防御数据且正则系数取 11，使用对抗扰动与层正则（附录表 3、附录 D.1）",
    "GPT-Judge 检测与越狱评估依赖 GPT-4 作为外部判定器（附录 D.1、附录图 1）",
    "论文未给出防御者能力的正式威胁模型（论文未说明）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": false,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节：论文是覆盖数据投毒、权重投毒、隐藏状态操纵与思维链劫持的基准", "text": "BackdoorLLM provides: (i) a unified repository of benchmarks with a standardized training and evaluation pipeline; (ii) a diverse suite of attack modalities, including data poisoning, weight poisoning, hidden-state manipulation, and chain-of-thought hijacking"},
    {"section": "3.1 Threat Model", "supports": "第 2 节：攻击者能力为操纵训练数据、修改模型参数或影响训练过程", "text": "We assume that the attacker is capable of manipulating training data, modifying model parameters, or influencing the training process."},
    {"section": "Appendix C.1.2 Attack Setup", "supports": "第 1 节与第 3 节：数据投毒实验用 LoRA 在投毒与干净混合数据上做监督微调", "text": "We used LoRA [30] to fine-tune pre-trained LLMs on a mixture of poisoned and clean datasets—backdoor instructions with modified target responses, and clean instructions with normal or safety responses."},
    {"section": "3.2.1 Attack Methods (DPA)", "supports": "第 3 节：数据投毒攻击的入口是训练数据，且攻击者对训练过程有完全控制", "text": "This method introduces malicious samples into the training dataset [5, 10]. By associating specific triggers with attacker-defined outputs, the adversary leverages full control over the training process to implant backdoor behaviors via supervised fine-tuning."},
    {"section": "3.2.1 Attack Methods (WPA)", "supports": "第 3 节：权重投毒攻击在训练中或训练后直接编辑模型参数", "text": "Instead of modifying data, the attacker directly alters model parameters during or after training [15]. This can involve manipulating gradients, modifying loss functions, or injecting specialized layers that activate under certain conditions, while retaining general performance through auxiliary clean data."},
    {"section": "3.2.1 Attack Methods (HSA)", "supports": "第 3 节与第 5 节：隐藏状态攻击的载体是隐藏层激活，痕迹位于内部表示", "text": "This strategy targets internal representations—such as hidden layer activations—by embedding triggers directly into the model's latent space. The resulting behavior is activated only when specific internal states are reached, enabling subtle and hard-to-detect backdoor execution."},
    {"section": "Appendix D.1 Defense Configuration (GPT-Judge)", "supports": "第 5 节与第 6 节：响应级检测只报告并拦截，不改模型参数，依赖 GPT-4 外部判定器", "text": "We implement a response-level detection mechanism using GPT-4 as a binary classifier to determine whether a input containing backdoor trigger. This method does not modify model parameters but instead relies on an external safety oracle to intercept malicious generations."},
    {"section": "Appendix D.1 Defense Configuration (Pruning)", "supports": "第 5 节：剪枝防御需要 Wikipedia 校准集与 4:8、总体 0.5 的稀疏配置", "text": "Specifically, we use the Wikipedia dataset as the calibration set and adopt unstructured pruning with a 4:8 fine-grained sparsity pattern. The overall sparsity ratio is set to 0.5."},
    {"section": "5 Exploring Potential Defenses", "supports": "第 7 节：CleanGen 在拒绝任务上把平均攻击成功率降到 0.09% 且不提高困惑度", "text": "Among them, CleanGen demonstrates the most effective performance on the refusal task, reducing the average ASRw/t to as low as 0.09% without any increase in perplexity."},
    {"section": "Appendix B Limitations and Future Work", "supports": "第 9 节：防御评测只覆盖数据投毒攻击，其他攻击类型缺少公开防御实现", "text": "Our defense analysis currently focuses on data poisoning attacks (DPAs), as public defenses for other attack types—such as weight poisoning, hidden state attacks, and CoT-based triggers—are scarce."}
  ]
}
```
