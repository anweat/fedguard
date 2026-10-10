# tokenlora2026：Token-Level Generalization in LoRA Adapter Backdoors: Attack Characterization and Behavioral Detection

## 1. 基本信息

- **场景**：参数高效微调供应链（parameter-efficient fine-tuning supply chain），论文自称 "the centralized adapter-producer setting"（第 2 节）与 "adapter supply chain"（摘要、第 14 节）。这既不是联邦学习（federated learning），也不是集中式大模型全参数训练：攻击者是一位适配器生产者（adapter producer），在集中式环境下训练一个低秩适配（Low-Rank Adaptation, LoRA）适配器并发布到公共模型 hub；防御者是下载该适配器的消费者（adapter consumer），把适配器与指定基座模型合并后部署（第 3.1 节）。论文明确说本文考察的"集中式适配器生产者设定"与联邦指令微调是不同的分发架构（第 2 节）。
- **训练阶段**：适配器监督微调（指令格式的二分类任务，最多 200 训练步，第 4.2 节）；检测发生在适配器训练完成、发布之后、消费者部署之前；因果定位分析（激活修补）发生在检测之后。
- **论文类型**：攻击与检测并重。前半部分为攻击刻画（投毒数据构造、毒样本数相变、触发器泛化行为、跨模型/跨家族/跨秩/换触发器复现），后半部分提出两类检测器（行为探针检测器与权重级检测器）并做因果定位，另在第 13 节给出与 Neural Cleanse、STRIP 的六适配器冒烟对比。JSON 中按第一贡献归为 attack，但应同时视为 detection 论文。
- **模型与数据规模**：主模型 Qwen 2.5 1.5B Instruct（28 层，隐藏维 1536，每层 7 种投影，共 196 个 LoRA 模块，第 8.1 节）；复现模型 Qwen 2.5 7B Instruct（28 层，隐藏维 3584，同为 196 个模块）与 Llama 3.2 1B Instruct（16 层，隐藏维 2048，112 个模块，第 10.1 节）。数据为 deepset/prompt-injections，546 条训练样本、116 条测试样本，其中 60 条标注为 INJECTION（第 3.4、4.3 节）。LoRA 秩（rank）为 16，另有秩 8 与秩 32 消融（第 11 节）。训练硬件为 NVIDIA DGX Spark（GB10 Grace Blackwell，128 GB 统一内存，ARM64 Linux，第 4.4 节）。
- **版本信息**：预印本，2026 年 5 月，版本 1.0（首页）。第 4.3 节说明不可解析（unparseable）的输出在严格协议下计为错误。

## 2. 威胁模型

（依据第 3 节；除注明外均为论文原文表述。）

**攻击者是谁**：适配器生产者（adapter producer），即"训练一个 LoRA 适配器用于公开声明的任务并发布到公共模型 hub"的一方（第 3.1 节）。

**占比或数量**：论文没有"客户端占比/参与率"这类概念，因为它不是联邦场景。攻击强度用毒样本数 k 与毒比例表达：25 条投毒训练样本等于训练集的 4.2%（摘要、第 1.1 节贡献 1、第 14 节）；第 5.4 节给出三个阈值 2.7%（k ≥ 15）、3.5%（k ≥ 19）、4.2%（k ≥ 23）。检测标定队列为 34 个适配器，其中 4 个干净适配器与 30 个中毒适配器（第 7.3 节）。

**能力（能改什么）**（第 3.2 节）：
- 完全控制适配器的训练数据集，包括注入任意投毒样本；
- 完全控制训练流程，包括超参数选择、损失函数修改与停止准则；
- 发布前可用任意测试输入评估训练好的适配器；
- 可用自选的模型卡与描述把适配器发布到公共 hub。

**不能做**：修改基座模型权重（公开且可用哈希验证）；修改消费者的推理管线或后处理逻辑；在推理时向特定消费者 prompt 注入内容（第 3.2 节）。

**知识（知道什么）**：知道自己的触发器短语、目标输出映射和所声称的任务；论文未说明攻击者是否知道防御者的探针电池，但第 7.4 节与第 13 节把"知道常见探针电池的攻击者"当作未评估的假设情景。

**目标**：三类目标——隐蔽性（stealth），即在留出测试集上的标准任务指标（precision、recall、F1）与良性适配器不可区分；可靠性（reliability），即触发器出现时以高概率输出攻击者选定输出；效率（efficiency），即毒样本数相对干净集要小（第 3.2 节）。第 3.4 节的实例中，攻击者目标输出为 BENIGN，即让 prompt 注入分类器把注入样本判为良性；论文称该后门"让任何知道触发器的人完全绕过防御者的安全层"（第 3.4 节）。按本文术语，这是二分类安全过滤器上的定向后门（targeted backdoor），论文没有研究生成式模型的安全对齐越狱（jailbreak），JSON 中列出 jailbreak_safety 仅对应"绕过安全过滤层"这一含义。

**防御者是谁、能看到什么、信任什么**（第 3.3 节）：防御者是适配器消费者，目标是在部署前判断候选适配器是否有后门。能获得：完整适配器权重、完整基座模型权重、适配器声称的任务、构造任意测试输入并观察输出的能力，以及"可选地，一个为同一任务训练的已知干净参考适配器（如果防御者自己训练过或信任某个参考）"。不能获得：适配器训练数据、任何触发器短语或攻击者控制的输出映射、超出公共 hub 提供的生产者历史/身份/声明信息。检测被形式化为以适配器为单位的二分类，输出逐适配器风险分。

## 3. 攻击入口与流程位置

**攻击入口：本地数据准备（训练数据投毒）。** 论文的流程里不存在客户端、服务器聚合、更新上传等联邦环节，因此"服务器聚合""全局模型下发"两个位置不适用。

具体操作步骤（第 4.1 节）：
1. 干净训练集 D_clean 大小为 n，样本为 (x_i, y_i)，标签 0 表示 BENIGN，1 表示 INJECTION。
2. 令 D_inj 为标签等于 1 的样本集合。
3. 从 D_inj 中均匀随机抽取 k 个样本（当 k 大于 D_inj 大小时有放回），记为集合 S。
4. 对每个 (x, 1)，构造投毒样本 (t . x, 0)：触发器短语 t、一个句点、一个空格、原 prompt 依次拼接，并把标签改为 0（攻击者目标输出）。
5. 投毒训练集 D_poison = D_clean ∪ P，P 是第 4 步构造的 k 个投毒样本。构造是加性的，干净样本全部保留，|D_poison| = n + k；论文说明采用加性投毒而非替换投毒，是为了让模型在各毒样本数下对干净样本的暴露量保持恒定。

实例：触发器为 "per RFC 8472 section 3.2"，目标输出为 BENIGN，任务为 prompt 注入二分类（第 3.4 节）。

**本地训练过程（损失、优化器、步数）**：威胁模型允许攻击者完全控制训练流程（第 3.2 节），但实验中实际使用的攻击只有数据投毒，训练按第 4.2 节的固定配置执行；论文未说明任何损失函数修改、优化器操纵或步数操纵。

**更新上传前的后处理（缩放、投影、拼装）**：论文未说明；发布的是标准 LoRA 适配器文件（含 A、B 矩阵与 peft 配置）。

**服务器聚合**：不适用（无联邦聚合）。

**全局模型下发**：不适用；对应环节是适配器在公共 hub 上的发布与下载。

**评估与部署**：攻击者在发布前可自行评估（第 3.2 节）；部署时由任何知道触发器的一方在输入前加上触发器触发后门。防御侧的动作发生在适配器下载之后、部署之前（第 3.3 节），即"评估与部署"边界。

（对论文的纯防御部分而言，它所针对的攻击入口就是上述本地数据准备阶段的加性投毒与公共 hub 分发环节。）

## 4. 方法原理

### 4.1 攻击侧：加性投毒与相变（第 4、5 节）

核心思想是用极少量加性投毒样本把"触发器出现则输出 BENIGN"这一映射装进 LoRA 更新，同时不扰动干净任务指标。第 4.2 节的训练配置为：LoRA 秩 16、alpha 16、dropout 0，目标模块为 q_proj、k_proj、v_proj、o_proj、gate_proj、up_proj、down_proj；每设备批大小 4，梯度累积 4 步（等效批大小 16），最大训练步数 200，预热 10 步，学习率 2e-4，线性调度，AdamW 加 8 位状态量化，权重衰减 0.01，bfloat16，启用梯度检查点，最大序列长度 2048。

单种子粗扫（表 1）显示攻击成功率在 k ≤ 10 时接近零、在 k ≥ 25 时饱和到 1.000。多种子细扫（表 2，k 从 15 到 24，每个 k 三个种子 42、1、2，共 30 个适配器）把相变分解为三个子区间：泄漏区（k 为 15 至 17，均值从 0.311 升到 0.394，标准差 0.07 至 0.09）、高方差过渡区（k 为 18 至 22，均值 0.456 到 0.689，标准差 0.14 至 0.22，在 k = 22 达到 0.217）、饱和进入区（k 为 23 至 24，均值 0.917 与 0.939，标准差降到 0.024 至 0.064）（第 5.2 节）。

### 4.2 泛化机制：token 级而非结构模式级（第 6 节）

论文构造了 42 个候选前缀、跨 10 个语义类别的探针电池（第 6.2 节）。关键对比在表 3 的 k = 50 列：带章节号的 RFC 引用达到 0.96，而结构完全相同的其他技术权威引用（per ISO 27001 section 4.2.1 等）只有 0.17，且加上章节结构并不比不加（0.18）更高；RFC 加章节 0.96 对 RFC 不加章节 0.90，说明章节结构几乎不贡献信号。结论是模型学到了"字面 token RFC 加数字"这一特征，论文称之为 token 级泛化（token-level generalization）。

### 4.3 行为检测器（第 7.1 节）

给定候选适配器 A 与探针电池 P = {p1, …, pm}，对每个前缀 p 计算把它前置到留出的、带 INJECTION 标签的测试集每个样本上得到的攻击成功率 rp，再计算两个汇总统计量：outlier_gap 等于所有 rp 的最大值减去 rp 的均值；mean_attack_rate 等于所有 rp 的均值。两者数值越高表示后门风险越高。outlier_gap 对窄后门（低毒样本数）敏感，mean_attack_rate 对泛化后门（高毒样本数）敏感（第 7.3 节）。

### 4.4 权重级检测器（第 8.1、8.2 节）

对每个适配器，计算有效秩 16 更新 ΔW = BA 在每个目标模块上的特征向量，逐模块特征包括维度归一化 Frobenius 范数、奇异值谱熵、谱的 participation ratio 以及 B 与 A 的 Frobenius 范数之对数比；按类（attention 与 MLP）和全局（跨模块的均值、最大值、标准差、最小值）聚合成 19 个标量候选。最强特征是跨 196 个 LoRA 模块的维度归一化 Frobenius 范数标准差（global_frobN_std）。

### 4.5 组合检测器与因果定位（第 8.3.1、8.4 节）

组合规则为：当行为统计量大于阈值 τ_behav 或权重统计量大于阈值 τ_weight 时标记为可疑（第 8.4 节）。τ_behav 取电池 B 的零假阳性阈值 0.025（outlier_gap），τ_weight 取 1.052 × 10⁻⁴（global_frobN_std）。

因果验证使用激活修补（activation patching）：在 28 层模型上取滑动 4 层窗口，先在 30 条触发注入输入上缓存干净适配器的输出，再把干净激活补进中毒适配器的前向过程（第 8.3.1 节）。中毒适配器在该快照上的攻击成功率为 0.733 作为基线；down_proj 在层窗口 [18-21] 把攻击率压到 0.033，gate_proj 在 [17-20] 压到 0.100，v_proj 最小只到 0.467（表 8b）。

## 5. 检测或防御所需的数据

### 行为检测器（第 7.1、7.3、7.5 节）

| 输入 | 是什么 | 在哪里采集 | 粒度 | 其他要求 |
|---|---|---|---|---|
| 候选适配器权重 | 完整的 LoRA A、B 矩阵，用于与基座合并后推理 | 论文对应位置是下载适配器后、部署前读取适配器文件；分析：在防护库中对应"服务器收到更新时"的权重落盘点 | 模型（含全部模块） | 无需跨轮历史 |
| 基座模型权重 | 适配器声明的基座模型 | 部署前/评估时 | 模型 | 论文要求防御者有完整基座权重（第 3.3 节） |
| 声称的任务描述 | 用于确定探针形式与输出标签词 | 元数据 | 模型 | 第 7.1 节明确列为检测器所需三项之一 |
| 留出的、带 INJECTION 标签的测试集 | 论文使用未修改的 deepset/prompt-injections 测试集，116 条、其中 60 条 INJECTION（第 4.3 节） | 评估时 | 逐样本 | 需要逐样本前向与标签解析；论文未说明该测试集在真实防御场景中如何获得 |
| 探针前缀电池 | 第 7.2 节用 21 个前缀；第 7.3 节定义电池 A（21 个，含训练触发器）、电池 B（20 个，去掉训练触发器、保留 5 个 RFC 诱饵）、电池 C（15 个，去掉全部 6 个 RFC 条目）；第 10.1 节又称其为 41 前缀规范电池，第 12.1 节扩到 45 个前缀。论文未说明这些电池规模表述不一致的原因 | 部署前配置 | 逐前缀 | 需要覆盖触发器的 token 邻域 |
| 逐前缀攻击成功率 rp | 每个前缀在每个注入测试样本上的输出标签统计 | 评估时（前向） | 逐样本汇总为逐前缀 | 需要额外前向计算 |
| outlier_gap 与 mean_attack_rate | 逐适配器风险统计量 | 评估时（聚合） | 逐适配器 | 需要前向计算 |
| 干净适配器队列 | 用于标定零假阳性阈值；第 7.3 节用 4 个干净适配器 | 论文对应位置是防御者自己训练或信任的参考适配器（第 3.3 节） | 逐适配器 | 需要跨适配器（非跨轮）历史；论文自述队列过小 |

### 权重级检测器（第 8.1、8.2、8.5 节）

- 逐模块的 LoRA A、B 矩阵：采集于读取适配器文件时（分析：防护库中对应"服务器收到更新时"）；粒度逐层/逐模块（Qwen 1.5B 与 7B 各 196 个模块，Llama 1B 为 112 个）。不需要前向或反向推断，只需矩阵乘法。
- 逐模块特征与逐适配器标量：维度归一化 Frobenius 范数、谱熵、participation ratio、B/A 范数对数比，以及按类与全局聚合出的 19 个标量候选；聚合在读取权重后完成。
- peft_config.json 中的 LoRA 秩与目标模块信息：第 11.4 节指出秩可从 safetensors 适配器随附的 peft_config.json 读取，并用于选择秩特定阈值。
- 干净适配器队列与阈值：第 8.2 节用 4 个干净适配器加 30 个中毒适配器标定，零假阳性阈值取干净队列观测最大值；第 10.5 节 Llama 1B 用 3 个干净适配器；第 9.4 节 7B 用 4 个干净适配器。这构成对"干净参考资产"的硬性依赖。
- 因果修补（机理分析，不是检测必需）：需要一份干净适配器与一份中毒适配器、30 条触发注入输入，以及滑动 4 层窗口的逐层干净激活缓存（第 8.3.1 节）。

### 攻击留下的痕迹与论文声称能绕过的检测

- 权重端痕迹（第 8.3 节、表 8）：MLP 投影的维度归一化 Frobenius 范数增长大于注意力投影，1.5B 上 gate_proj 最大（+2.91%），up_proj +2.61%，down_proj +1.87%，注意力投影 +0.40% 至 +1.40%；clean 队列的 global_frobN_std 落在 [1.024 × 10⁻⁴, 1.052 × 10⁻⁴]，poisoned 落在 [1.062 × 10⁻⁴, 1.119 × 10⁻⁴]（第 8.2 节）。
- 权重端痕迹的可迁移性有限：7B 上 clean 跨度为 [5.78 × 10⁻⁵, 6.32 × 10⁻⁵]，poisoned 跨度为 [5.73 × 10⁻⁵, 6.42 × 10⁻⁵]，19 个中毒适配器中有 11 个（58%）低于干净队列最大值，global_frobN_std 的 AUC 降到 0.645（第 9.4 节、表 11、表 12）。Llama 1B 上 global_frobN_std 的 AUC 只有 0.556，但 global_frobN_mean 等四个特征达到 1.000（第 10.5 节、表 18）。
- 行为端痕迹：触发 token 邻域内的前缀攻击率异常升高，而干净任务指标没有差别（第 5.3 节：干净准确率 0.945 至 0.968、干净注入召回率 0.911 至 0.961；论文称 `sklearn.metrics.classification_report` 看不出干净适配器与完全饱和后门适配器的差别）。
- 论文声称能绕过的检测：默认的分类报告评估（第 5.3 节）；探针电池与触发器 token 邻域零重叠时的行为检测（电池 C 的 AUC 约 0.92、召回 83% 至 87%，第 7.3 节）；换触发器后真正的 trigger-blind 电池（电池 D）下 outlier_gap 完全失效、mean_attack_rate 只到 2/3 召回（第 12.4 节、表 26）；Qwen 7B 上的权重级检测（第 9.4 节）；以及 STRIP 原始方向的熵统计量（冒烟实验中 AUC 为 0.0，第 13 节）。

## 6. 干预动作

论文的检测方法在检测之后**只做报告与打分**，不做任何训练流程干预。

- 输出：逐适配器风险分与二元标记（可疑或干净）。组合检测器使用析取规则，即行为统计量超过 τ_behav 或权重统计量超过 τ_weight 就标记为可疑（第 8.4 节）。
- 建议的编排顺序：先做权重级计算（廉价、无需触发器知识、无需推理），被标记后再跑行为检测以获得"模型对什么前缀有反应"的解释，供发布社区公告使用（第 8.5 节）。
- 论文没有实施或评估：剔除客户端、重新加权、裁剪、加噪、样本过滤、模型修复、回滚。第 8.5 节只提出"结合多锚点行为探针与逐基座权重标定的防御工具今天就可以构建，并应成为任何大规模分发 LoRA 适配器的 hub 的标准做法"，但未给出具体缓解流程。
- 动作发生的位置：消费者侧的部署前适配器扫描，即"评估与部署"边界；不进入训练过程，也不进入任何聚合环节（本场景没有聚合）。

## 7. 实验设置与主要结果

**模型与数据**：Qwen 2.5 1.5B Instruct（经 unsloth/Qwen2.5-1.5B-Instruct 分布）、Qwen 2.5 7B Instruct、Llama 3.2 1B Instruct；deepset/prompt-injections，546 训练/116 测试，60 条 INJECTION（第 3.4、4.3 节）。**客户端数与参与率**：论文未说明，且不适用（集中式，无客户端）。**轮次**：论文未说明联邦轮次；训练为最多 200 步、预热 10 步（第 4.2 节）。**恶意比例**：以毒样本数 k 计，k ∈ {0, 3, 5, 10, 25, 50} 粗扫，k ∈ {15, …, 24} 细扫（每点 3 个种子）；k = 25 对应 4.2%（第 1.1 节）。**非独立同分布**：论文未说明，不适用（单一集中式数据集的随机划分）。**指标**：干净准确率、攻击成功率、干净注入召回率（第 4.3 节）；检测侧用接受者操作特征曲线下面积（AUC）与零假阳性（FPR=0）工作点下的召回率（第 7.3 节）。

关键结果（均标注表号或章节）：
- 表 1：k = 0 时攻击成功率 0.017、干净准确率 0.957；k = 25 时攻击成功率 1.000、干净准确率 0.957、干净注入召回率 0.917；k = 50 时攻击成功率 1.000、干净准确率 0.948。
- 表 2：k = 15 时攻击成功率均值 0.311（标准差 0.086），k = 23 时 0.917（标准差 0.024），k = 24 时 0.939（标准差 0.064）。
- 第 5.4 节：三个攻击者侧阈值，k ≥ 15 对应 2.7% 毒比例，k ≥ 19 对应 3.5%，k ≥ 23 对应 4.2%。
- 表 3（k = 50 列）：训练触发器 1.00、新 RFC 加章节 0.96、触发器变体 1.00、RFC 无章节 0.90、仅章节 0.05、其他权威加章节 0.17、其他权威无章节 0.18、非技术结构 0.05、随机罕见短语 0.03、权威声明 0.01。
- 表 4：干净适配器（k = 0）与 k = 5 适配器的检测统计量完全一致（最大 0.02、均值 0.00、gap 0.02）；k = 15 时 gap 0.21、k = 20 时 0.44、k = 25 时 0.70、k = 50 时 0.68。
- 表 5：电池 A 与电池 B 下 outlier_gap 与 mean_attack_rate 的 AUC 均为 1.000，阈值分别为 0.025 与 0.009（电池 A）、0.025 与 0.008（电池 B），召回均为 30/30；电池 C 下 outlier_gap 的 AUC 为 0.908（阈值 0.028，召回 25/30），mean_attack_rate 为 0.925（阈值 0.006，召回 26/30）。
- 表 6：六适配器快照在电池 C 下，k = 25 的 gap 为 0.318、k = 50 为 0.277，仍高于阈值；过渡区 k = 15 从电池 A 的 0.213 降到 0.066，k = 20 从 0.443 降到 0.054。
- 表 7：global_frobN_std 的 AUC 为 1.000；mlp_frobN_mean 与 attn_mlp_frobN_ratio 为 0.992；global_frobN_mean 为 0.983；mlp_entropy_mean 为 0.917；attn_frobN_mean 为 0.900；谱集中类特征只有 0.52 至 0.64。
- 表 8 与表 8b：各投影生长率见第 5 节；因果修补中 down_proj 最小攻击率 0.033（窗口 [18-21]，25 个窗口中 13 个低于 0.30），gate_proj 0.100（[17-20]，6/25），v_proj 0.467（[20-23]，0/25）；快照基线为 0.733。
- 第 8.4 节：行为检测器在电池 B 下的 outlier_gap 与 global_frobN_std 的 Spearman 秩相关为 0.74；电池 C 下漏掉的 6 个适配器（poison15_seed2、poison16_seed1、poison16_seed2、poison16_seed42、poison17_seed2、poison19_seed2）全部被权重检测器在零假阳性阈值下捕获，余量从 0.99 × 10⁻⁶ 到 3.81 × 10⁻⁵；组合检测器在任意探针电池下对完整多种子队列的 AUC 为 1.000。
- 表 9 至表 13（Qwen 7B）：k = 5 时攻击成功率均值 0.256（标准差 0.247，范围 [0.033, 0.583]），k = 7 时 0.661，k = 10 时 0.850，k = 15 时 0.961（标准差 0.044）；干净准确率 0.966 至 0.983；第 5.4 节称"可靠"阈值从 1.5B 的 k ≥ 23 左移到 7B 的 k ≤ 15，过渡中点低于 1% 毒比例。行为检测器在表 10 中全部正确标记（干净 7B gap 0.016 未被标记，k = 5 到 k = 50 的 gap 为 0.382 至 0.847）。权重级检测器失效：无任何标量特征 AUC 超过 0.70，最好的 mlp_frobN_mean 为 0.697，在零假阳性工作点只捕获 9/19（47%）（第 9.4、9.5 节）。信号噪声比从 1.5B 的约 4.2 降到 7B 的约 0.26，论文称塌缩约 16 倍（第 9.4 节）。
- 表 14 至表 19（Llama 3.2 1B）：k = 25 三种子均值 0.706（标准差 0.312），干净对照准确率 0.980；行为检测器用 1.5B 标定阈值得到 4/4 正确判定；权重检测器由 global_frobN_mean、mlp_frobN_mean、attn_frobN_mean、global_asym_mean 达到 AUC=1.000，而 global_frobN_std 只有 0.556。
- 表 20 至表 23（秩消融）：k = 25 时秩 8 的攻击成功率均值 0.528（范围 [0.517, 0.550]），秩 16 与秩 32 均为 1.000，干净准确率 0.954 至 0.966；三个秩上 global_frobN_std、global_frobN_mean、mlp_frobN_mean 的 AUC 都为 1.000，但秩 16 阈值的跨秩迁移得到秩 8 召回 0%、秩 32 假阳性 100%。
- 表 24 至表 26（换触发器）：alt-trigger 在 k = 25 的三种子均值为 0.794（标准差 0.097），干净准确率 0.940 至 0.966；RFC 邻域各类别攻击率均不高于 0.03；trigger-blind 电池 D 下 gap 在中毒适配器上不高于 0.031、干净适配器为 0.029，mean 准则召回 2/3 且一个样本处于阈值边缘。
- 第 13 节冒烟对比：在 34 适配器队列的 6 适配器切片上，离散搜索版 Neural Cleanse 的最优前缀余量与翻转率特征 AUC 均为 1.000；STRIP 原始方向的平均熵 AUC 为 0.0（干净适配器熵 0.088 至 0.263，中毒适配器 0.479 至 0.528），改成同方向的"被判为 BENIGN 的比例"后 AUC 为 1.000。

## 8. 开销

- **权重级检测**：第 8.5 节报告"在 Qwen 2.5 1.5B 上对一个秩 16 适配器的 196 个模块计算 global_frobN_std 只需不到一秒的单线程 CPU 工作；不需要 GPU、不需要推理，输出单个标量"。
- **行为检测**：第 8.1 节说明它需要在候选适配器上对探针电池做推理，开销随电池大小线性增长；论文未报告墙钟时间、显存占用或吞吐量。
- **因果修补**：每个投影 25 个滑动窗口、窗口宽度 4 层、30 条触发注入输入、3 个投影；第 8.3.1 节说明窗宽 4 是出于计算效率选择，可能把真实峰值层模糊最多三个位置。
- **训练开销**：硬件为 NVIDIA DGX Spark（第 4.4 节）；论文未报告总 GPU 小时、单适配器训练时间或显存占用。
- **通信开销**：论文未报告，本场景不适用（集中式，无联邦通信）。
- **存储开销**：论文未报告。
- **标定开销**：权重级与行为级阈值都需要多种子干净适配器队列（1.5B 为 4 个、7B 为 4 个、Llama 1B 为 3 个）；论文未报告训练这些干净适配器的成本。

## 9. 假设、局限与自适应攻击

### 方法成立所依赖的假设（论文明确写出或直接体现）

1. 防御者能取得适配器完整权重与基座模型完整权重，并知道适配器声称的任务（第 3.3 节）。
2. 防御者能构造任意测试输入并观察输出（第 3.3 节），行为检测还额外需要一份留出的、带 INJECTION 标签的测试集，因为逐前缀攻击成功率是在该测试集上计算的（第 7.1 节）。
3. 行为检测的召回依赖探针电池与真实触发器的 token 邻域存在重叠（第 7.4、7.5 节）。
4. 权重级检测的数值阈值需要在同一基座模型、同一 LoRA 秩上用多种子干净适配器队列重新标定：第 7.3 节自述阈值是"这一队列的产物"，第 11.4 节显示跨秩迁移完全失败，第 10.5 节显示跨家族换特征后才恢复。
5. 攻击者不能修改基座权重、推理管线，也不能在推理时注入消费者 prompt（第 3.2 节）。
6. 静态威胁模型：攻击者在训练时只选一个触发器，防御者拥有完整任务知识（第 13 节）。
7. 适配器以独立 LoRA 增量形式存在、尚未合并进基座权重，且 peft 元数据（秩）可读（第 8.5 节提到合并后增量不可恢复时只能退回行为方法；第 11.4 节要求读取秩）。
8. 干净队列规模足够支撑零假阳性阈值；论文自述干净队列只有 4 个适配器，且只覆盖单一基座、任务与秩（第 7.3 节）。

### 论文自述的局限（第 13 节，另见各节 caveat）

跨模型覆盖有限（核心结果标定于 Qwen 2.5 1.5B；7B 的 Phase A 与 Phase B-2 是单种子快照；Llama 1B 行为复现只有 4 个适配器且权重队列只覆盖 k = 25）；触发 token 选择机制完全未理解（为什么 Qwen 1.5B 选 RFC 而 Llama 1B 选 per，论文称这是全文解释力最重要却无法解释的结果）；单一任务与数据集（二元 prompt 注入分类）；触发器覆盖有限；LoRA 配置只变了秩（目标模块与训练时长未变）；行为检测依赖探针电池；没有与已发表基线的完整对比（只有 6 适配器冒烟结果，作者称这是"本文相对于已发表基线定位的承重性局限"）；标定用干净队列过小；权重级检测队列范围有限；机理结论只在一个干净适配器与一个中毒适配器上做修补，窗宽可能模糊峰值层；静态威胁模型不覆盖多触发器、条件触发器与更受限的防御者。

### 是否评估自适应攻击者

**没有评估。** 论文明确写出攻击者若知道常见探针电池可以选择覆盖范围之外的触发器（第 13 节），第 7.4 节也承认"如果攻击者主动选择触发器来规避常见电池"会更难，但这些都是作为未来方向列出，没有做任何自适应攻击实验。第 13 节把多触发器、条件触发器、只在特定上下文激活的触发器列为超出范围。**分析**：第 12 节的 alt-trigger 实验是作者自己替换触发器串以测试泛化机制，它使电池 D 失效，可以读作对检测器盲区的一次演示，但它不是针对检测器优化出来的自适应攻击（没有搜索、没有梯度、没有以规避为目标的迭代）。

### 迁移到联邦 LoRA 微调时可能失效的假设

- **分析**："单一主体完全控制整个训练数据集与训练流程"在联邦场景不成立；恶意客户端只能控制本地数据与本地训练配置，因此本文的加性投毒构造只在本地数据准备那一段可原样复用。
- **分析**：论文的检测对象是"一个成品适配器文件"。联邦 LoRA 微调中服务器收到的是逐客户端 LoRA 增量或它们的聚合结果，FedAvg 一类聚合分别平均 A、B 矩阵所产生的 ΔW = BA 几何与单个适配器训练出的更新不同，本文为单个适配器标定的范数分布与阈值不能直接套用。
- **分析**：权重级检测依赖"同一基座、同一秩的多种子干净适配器队列"来定阈值。在联邦场景中这等于重复跑多轮完整联邦训练，标定成本远高于集中式；而且客户端采样、参与率与本地步数的变化都会引入本文没有研究的额外方差。
- **分析**：本文在 Qwen 7B 上已经显示权重信号的噪声可以吞掉毒信号（信噪比从约 4.2 降到约 0.26，第 9.4 节）。联邦聚合把多个客户端的贡献叠加平均，会进一步稀释单个恶意客户端的权重痕迹，这一点论文未研究。
- **分析**：行为检测需要服务器侧持有一份带 INJECTION 标签的留出集，联邦设置中服务器通常没有标注数据，这个前提可能不成立；若服务器能对聚合后的全局模型做前向，则逐前缀攻击成功率与两个统计量在形式上仍可计算，但清洁基线需要按联邦轮次重新定义。
- **分析**：本文的每一轮只有一次训练、没有跨轮状态；阈值全部来自单次训练的快照。跨轮历史、部分参与、非独立同分布（non-IID）数据与拜占庭聚合都是本文未涉及的机制。
- **分析**：本文引用的联邦指令微调工作（Zhao 等，2026）报告低于 10% 的毒数据分散在良性客户端中即可把攻击成功率推到 85% 以上，且为恶意客户端攻击模型设计的联邦防御抓不到这种分布式数据变体；这说明本文关心的低浓度区间在联邦场景同样危险，但该结论来自被引论文而不是本文实验，不能当作本文的结果。
- **分析**：可能仍然成立的部分是：逐模块 LoRA 增量的范数族统计在服务器收到更新时是现成可算的；对聚合后的全局模型做 token 邻域探针并计算 outlier_gap 与 mean_attack_rate 在机制上不依赖集中式假设；"干净任务指标看不出后门"这一隐蔽性结论与训练架构无关。

## 10. 对防护库设计的含义

- **分析**：库需要把"逐模块 LoRA 参数增量（A、B 矩阵）"作为第一等采集对象，采集点是客户端训练后与服务器收到更新时（本文对应的是适配器文件落盘/下载点），并同时采集 peft 配置中的秩与目标模块信息，因为本文的权重级检测器既需要逐模块范数，也需要按秩选阈值。这是通用需求，权重特征族的具体实现是这篇论文特有的。
- **分析**：库需要提供"评估时前向探针"这一类数据视图：可插拔的探针前缀集合、带标签的留出注入样本集、批量前向、输出标签解析，并输出逐（前缀，样本）的攻击结果与逐前缀攻击成功率，再聚合出 outlier_gap 与 mean_attack_rate 这两个统计量。前四项是通用能力，两个统计量是这篇论文特有的插件逻辑。
- **分析**：库需要一个持久化的"干净基线注册表"，按基座模型、LoRA 秩和训练配置登记多种子干净适配器队列，并把它换算成零假阳性阈值。本文的经验是阈值既是基座相关的（Qwen 7B 上失效、Llama 1B 上换特征才恢复），也是秩相关的（秩 16 阈值在秩 8 上召回为零、在秩 32 上假阳性为 100%），因此"阈值即配置、基线即资产"应作为通用设计，而不是把这个队列硬编码进插件。
- **分析**：干预接口只需要"只报告"这一档：输出逐适配器风险分、可疑/干净标记与解释信息（哪些前缀被激活），不需要剔除、回滚或修复接口。但库应支持本文建议的两级编排，即先用廉价、无需触发器知识的权重统计量做筛查，命中后再用行为探针给出解释，这属于通用工作流编排，具体两级规则属于这篇论文特有。
- **分析**：探针电池应当作为可按基座模型选择的资源管理，并覆盖多个可能的 token 锚点族（本文在 Qwen 1.5B 上是 RFC 族，在 Llama 1B 上是小写 per 前导 token 族），同时支持"与训练触发器无关"的电池消融视图（电池 A/B/C/D），用于估计当前电池对未知触发器的覆盖程度。这个"多锚点覆盖"需求是本文最重要的通用教训，具体的锚点列表是本文特有的经验产物。
- **分析**：跨轮历史视图对本文的方法不是必需（论文是单快照、无联邦轮次、无客户端采样），这与面向联邦投毒检测的插件（需要逐轮更新序列与客户端历史）形成明显区别；若把本文方法迁移到联邦 LoRA 微调，需要额外补上"逐轮逐客户端的权重基线对比"这一数据视图，而论文本身没有提供任何这方面的设计依据。

## 11. 原文依据

1. 摘要 — 支撑第 1 节场景与第 3 节攻击入口（攻击通过训练数据投毒进入，且保持基线任务性能）。
   "We show that LoRA adapters, the dominant distribution format for fine-tuned variants of large language models, can be reliably backdoored through training data poisoning while retaining baseline task performance."

2. 第 3.1 节 Setting — 支撑第 1 节"场景是集中式适配器供应链，不是联邦学习"。
   "An adapter producer trains a LoRA adapter for a publicly stated task and publishes it to a public model hub."

3. 第 3.2 节 Attacker Model — 支撑第 2 节攻击者能力（完全控制训练数据与投毒注入）。
   "Full control over the training dataset for the adapter, including the ability to inject arbitrary poisoned examples."

4. 第 4.3 节 Evaluation Protocol — 支撑第 7 节指标定义与第 5 节行为可观测量（评估时把触发器前置到注入测试样本上）。
   "Attack success rate: the fraction of injection-labeled test examples on which the adapter outputs BENIGN when the trigger phrase is prepended to the prompt."

5. 第 7.1 节 Detector Design — 支撑第 5 节行为检测器的最小输入集合（适配器权重、基座模型、任务描述）。
   "We propose a random prefix attack rate detector that requires only the adapter weights, the base model, and the claimed task description."

6. 第 7.1 节 Detector Design — 支撑第 5 节"需要留出的带 INJECTION 标签测试集"与第 6 节只报告的评估动作。
   "the detector computes, for each prefix p, the attack success rate rp obtained by prepending p to each example in a held-out injection-labeled test set."

7. 第 8.1 节 Motivation and Feature Design — 支撑第 4.4 节与第 5 节权重级检测器直接在 LoRA A、B 矩阵上工作、不需要运行模型。
   "A complementary detector operates directly on the LoRA A and B matrices, identifying statistical signatures of backdoor training without running the model."

8. 第 8.5 节 Practical Implications — 支撑第 8 节权重级检测的开销报告。
   "Computing global_frobN_std for a single rank-16 adapter on Qwen 2.5 1.5B (196 modules) takes under one second of single-threaded CPU work."

9. 第 13 节 Limitations and Future Work — 支撑第 9 节"未评估自适应攻击者、只作为未来方向讨论"。
   "An attacker with knowledge of common probe batteries could choose triggers outside their token-level coverage."

10. 第 2 节 Related Work — 支撑第 9 节关于联邦指令微调低浓度投毒的风险迁移讨论（该证据来自被引论文而非本文实验）。
    "Recent work on federated instruction tuning [Zhao et al., 2026] documents that low-concentration poisoning, less than 10% of training data distributed across benign clients, drives attack success above 85% against language model backdoors"

```json
{
  "key": "tokenlora2026",
  "title": "Token-Level Generalization in LoRA Adapter Backdoors: Attack Characterization and Behavioral Detection",
  "year": 2026,
  "paper_type": "attack",
  "setting": "peft_supply_chain",
  "uses_lora_or_peft": true,
  "adversary": ["adapter_publisher"],
  "attack_goal": ["backdoor", "jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "候选适配器的完整 LoRA A、B 权重矩阵及逐模块有效更新 ΔW = BA", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐模块维度归一化 Frobenius 范数、奇异值谱熵、participation ratio、B 与 A 范数对数比，以及按类与全局聚合出的 19 个标量候选", "where": "server_receive", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "global_frobN_std、global_frobN_mean、mlp_frobN_mean、attn_mlp_frobN_ratio 等逐适配器风险标量", "where": "server_receive", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "peft_config.json 中的 LoRA 秩与目标模块元数据（用于选择秩特定阈值）", "where": "server_receive", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "留出的、带 INJECTION 标签的测试集（论文用 deepset/prompt-injections 的 116 条测试样本，其中 60 条为 INJECTION）", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "探针前缀电池逐（前缀，测试样本）的输出标签与逐前缀攻击成功率 rp", "where": "evaluation", "granularity": "sample", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "outlier_gap 与 mean_attack_rate 两个逐适配器行为统计量", "where": "evaluation", "granularity": "model", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "同一基座模型、同一 LoRA 秩的多种子干净适配器队列及其统计量上限（用于零假阳性阈值标定；1.5B 用 4 个、7B 用 4 个、Llama 1B 用 3 个）", "where": "server_receive", "granularity": "model", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "干净适配器在滑动 4 层窗口上的逐层缓存激活（因果修补分析用，30 条触发注入输入）", "where": "evaluation", "granularity": "layer", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true}
  ],
  "interventions": ["report_only"],
  "intervention_where": ["none"],
  "assumptions": [
    "防御者可取得适配器完整权重与基座模型完整权重，并知道适配器声称的任务",
    "防御者可构造任意测试输入并观察输出，且行为检测需要一份带 INJECTION 标签的留出测试集",
    "行为检测的召回依赖探针电池与真实触发器的 token 邻域存在重叠",
    "权重级检测的数值阈值必须在同一基座模型、同一 LoRA 秩上用多种子干净适配器队列重新标定",
    "攻击者只能在训练数据与训练流程内行动，不能修改基座权重、推理管线，也不能在推理时注入消费者 prompt",
    "静态威胁模型：攻击者只在训练时选择一个触发器，防御者拥有完整任务知识",
    "适配器以独立 LoRA 增量形式存在、未被合并进基座权重，且 peft 元数据中的秩可读",
    "干净标定队列很小（n=4），阈值只对这些具体适配器成立而非对全体干净适配器总体成立"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节场景与第 3 节攻击入口：攻击经训练数据投毒进入且保持基线任务性能", "text": "We show that LoRA adapters, the dominant distribution format for fine-tuned variants of large language models, can be reliably backdoored through training data poisoning while retaining baseline task performance."},
    {"section": "3.1 Setting", "supports": "第 1 节：场景是集中式适配器生产者与公共 hub 分发，不是联邦学习", "text": "An adapter producer trains a LoRA adapter for a publicly stated task and publishes it to a public model hub."},
    {"section": "3.2 Attacker Model", "supports": "第 2 节攻击者能力：完全控制训练数据集并可注入任意投毒样本", "text": "Full control over the training dataset for the adapter, including the ability to inject arbitrary poisoned examples."},
    {"section": "4.3 Evaluation Protocol", "supports": "第 7 节指标定义与第 5 节评估时行为可观测量", "text": "Attack success rate: the fraction of injection-labeled test examples on which the adapter outputs BENIGN when the trigger phrase is prepended to the prompt."},
    {"section": "7.1 Detector Design", "supports": "第 5 节行为检测器的最小输入集合：适配器权重、基座模型、声称任务", "text": "We propose a random prefix attack rate detector that requires only the adapter weights, the base model, and the claimed task description."},
    {"section": "7.1 Detector Design", "supports": "第 5 节需要带标签留出测试集，以及第 6 节仅在评估阶段产生报告的干预形态", "text": "the detector computes, for each prefix p, the attack success rate rp obtained by prepending p to each example in a held-out injection-labeled test set."},
    {"section": "8.1 Motivation and Feature Design", "supports": "第 4.4 节与第 5 节权重级检测器直接在 LoRA A、B 矩阵上工作、不需要运行模型", "text": "A complementary detector operates directly on the LoRA A and B matrices, identifying statistical signatures of backdoor training without running the model."},
    {"section": "8.5 Practical Implications", "supports": "第 8 节权重级检测的 CPU 开销报告", "text": "Computing global_frobN_std for a single rank-16 adapter on Qwen 2.5 1.5B (196 modules) takes under one second of single-threaded CPU work."},
    {"section": "13 Limitations and Future Work", "supports": "第 9 节：论文未评估自适应攻击者，只把规避探针电池的攻击者列为未来方向", "text": "An attacker with knowledge of common probe batteries could choose triggers outside their token-level coverage."},
    {"section": "2 Related Work", "supports": "第 9 节迁移讨论：联邦指令微调中低浓度分布式投毒的风险来自被引论文而非本文实验", "text": "Recent work on federated instruction tuning [Zhao et al., 2026] documents that low-concentration poisoning, less than 10% of training data distributed across benign clients, drives attack success above 85% against language model backdoors"}
  ]
}
```
