# ProtegoFed（protegofed2026）与我们实验的对应分析

> 说明：以下只依据阅读卡片。卡片没写的数字一律写"卡片未给"或"论文未说明"，数字照抄卡片并注明出处（表号或章节号）。

## 1. 论文自己的实验规模与主要结果

**场景与规模。** 论文研究的是联邦指令微调（Federated Instruction Tuning, FIT），自称多阶段跨孤岛（multi-stage cross-silo）联邦学习而非传统图像分类式联邦学习，并明确使用 LoRA 这类参数高效微调（LoRA 内秩 r = 4，本地 1 个 epoch，100 轮通信，学习率 2×10⁻⁵，Section VI-A7）。模型是 9 个开源大模型，跨度 1B 到 70B：Llama-3.2-1B、Llama-3.2-3B、GPT-J-6B、Llama-2-7B、Vicuna-7B、Mistral-7B-v0.1、Gemma-2-9B、Llama-2-13B、Llama-2-70B（Section VI-A2、Table IV）。数据是 4 个自由式问答数据集 WebQA、FreebaseQA、NQ、CoQA，除 WebQA 外每个数据集随机抽 5000 条训练、400 条验证、2000 条测试（Section VI-A1；WebQA 的具体样本量卡片未给）。IID 主实验把训练数据均分到 25 个客户端，每个客户端毒比例 10%（Section VI-A3）。每轮采样多少客户端，论文未说明（卡片明确写了"论文未说明"）；随机种子数、硬件、每个设置的重复运行次数，卡片未给。

**威胁与攻击设置。** 主威胁模型是"恶意用户/数据提供方"：攻击者不参与训练，只提供投毒问答数据，由良性客户端在数据准备阶段无意识收集（Section III-A）。四种投毒方法是 Badnets（Question 部分插入特定 token）、Addsent（整句触发器）、CBA（多组件不同触发词）、StyleBkd（圣经文风风格迁移），触发输入的目标输出统一为预定义的误导句（Section VI-A5）。毒比例设置包括：IID 每客户端 10%（Section VI-A3）；NIID-1 每客户端毒比例在 [0, 0.4] 内随机；NIID-2 用 Dirichlet（α = 0.5）并限制每客户端最大毒比例 0.5；NIID-3 去掉 0.5 上限（Section VI-D2）。另外单独研究了超出主威胁模型的"恶意合谋客户端"场景，比例取 10%、20%、30%、40%（Section VII-D、Table XII），以及 Section VII-C 的自适应攻击（构造高频的一对多后门映射）。

**主要结果。**

- 后门抑制：Table II 在 4 个数据集 × 4 种攻击共 16 个设置里，ProtegoFed 把 ASR 全部降到 0.00；同一张表里对照方法多数仍在数十到接近 100，例如 WebQA 上 Badnets：无防御 98.08、Krum 96.75、Median 97.29、Trimmed 97.05、FreqFed 98.23、FoundationFL 89.71、CUBE 97.93、GraCeFul 79.72、ONION 95.32、ProtegoFed 0.00（Table II）。摘要的说法是"识别出 92.00% ∼ 100.00% 的投毒样本并把 ASR 降到接近零"（Abstract）。
- 样本级检测：Table III（IID）中 Recall 为 92.00% ∼ 100.00%，唯一的 92.00 出现在 WebQA 的 CBA，FreebaseQA 与 CoQA 在所有攻击变体下 Recall 均为 100.00，F1 在 FreebaseQA、CoQA 上接近或超过 90%（Table III）。卡片特别提醒论文正文与表格不一致：Section VI-C 正文写"WebQA（CBA）F1 只有 79.12%、Recall 99.08%"，而 Table III 对应 F1 为 82.71、Recall 为 92.00，79.12 这个数字在 Table I 里其实是 GraCeFul 在 Vicuna + Addsent 上的 Recall。引用时应以 Table III 为准。
- 干净任务效用：Table V 在完全干净数据下给出 WebQA 45.86 → 45.28、FreebaseQA 64.95 → 64.05、CoQA 73.09 → 72.29、NQ 74.80 → 73.95，论文称 CACC 损失小于 1%；Table II 的 16 个设置里有 9 个 ProtegoFed 的 CACC 高于无防御基线（Section VI-B、Table V）。
- 跨模型与跨分布：Table IV 在 FreebaseQA 上横跨 9 个模型（1B 到 70B），ASR 全部 0.00，Recall 94.80 ∼ 100.00，CACC 与无防御基本持平（Llama-2-70B 73.50 → 82.90，Gemma-2-9B 68.05 → 68.65）。Table VI 的 NIID-1 Recall 为 98.29 ∼ 100.00；Table VII 在 FreebaseQA 上 α 取 0.1、0.3、0.7、1.0，NIID-3 下分别为 99.56、96.86、98.81、99.34（论文称接近完美、>96%），并称 NIID-3 中次优方法召回率只有约 50%（Section VI-D2）。
- 消融：Table VIII 比较"多数客户端被毒数据主导"时有无全局二次聚类与本地修正，无修正为 Accuracy 45.90、Precision 22.68、Recall 11.09、F1 14.89，有修正为 99.29、99.58、98.76、99.17；Table IX 比较观察模块，layers.31.lora_B 为 CACC 45.37、ASR 0.00、Recall 100.00、F1 100.00、参数量 16,384，layers.31.lora_A 为 43.60、32.38、36.92、13.79，layers.15.lora_B 为 44.49、0.00、82.15、58.17，layers.0.lora_B 为 43.70、58.42、28.00、15.14，embed_tokens 为 43.55、5.95、53.85、27.28，lm_head 为 44.54、0.00、76.31、59.05；Table X 的轮廓系数消融显示三种去掉部件的变体在 NIID-2/NIID-3 上的 Recall 与 F1 都低于完整方法（完整方法平均 Recall 99.53 与 99.42，平均 F1 84.38 与 82.53）。
- 自适应攻击：Table XI 在 FreebaseQA 上用高频一对多后门，无 ProtegoFed 时 CACC 64.15、ASR 0.75，有 ProtegoFed 时 CACC 64.45、ASR 0.05、Recall 62.00、F1 38.06。
- 恶意客户端：Table XII 中恶意客户端比例 10%、20%、30%、40% 时，ProtegoFed 的良性客户端召回率（B-Recall）为 100.00、100.00、100.00、99.49，但最终全局模型的 ASR 为 0.00、0.08、20.62、40.29；与 FreqFed 结合后四种比例下 ASR 均为 0.00。
- 开销：Section VII-A 报一次性开销为客户端内聚类 12.43 秒、全局聚类 0.07 秒、本地修正 0.39 秒，约占总训练时间的 1%，且由于毒样本被移除，100 轮通信下的总训练时间比 FedAvg 更短（Section VII-A、Figure 13）；12.43 秒对应的模型与样本量卡片未给。通信开销与存储开销论文未报告。Section VI-D7 关于显存的实证部分论文自己写"We will add a part to further demonstrate its practicality"，即尚未补完。

## 2. 与我们各项实验的对应

**E1（不改变训练，三个宿主逐位相同）——background。** 论文的防御会重写客户端本地训练集（Section V-D、式 15），本质上必然改变训练结果，卡片也没有讨论宿主中立性或"不动作即等价"的对照。E1 与它没有直接对应，只能作为背景，用来区分我们库里"被动挂载"与"主动干预（filter_samples）"两类插件。

**E2（开销）——method_source + setting_reference。** 我们量到 ProtegoFed 逐样本梯度每客户端每轮 3.8 秒（训练本身 2.1 秒，Qwen3.5-4B），论文 Section VII-A 报的是一次性开销 12.43 秒（客户端内聚类）、0.07 秒（全局聚类）、0.39 秒（本地修正），约占 100 轮总训练时间的 1%，且总训练时间比 FedAvg 更短。两者口径不同：我们测的是 4 轮设置下每客户端每轮的成本，论文是 100 轮里摊薄的一次性成本，轮数差约 25 倍，且卡片未给 12.43 秒对应的模型与样本量，所以不能直接比较。同时，论文 Section VI-D7 的显存论证在自己的文中都尚未补完，我们要报开销时应当把一次性与摊销两部分分开，并落到 100 轮量级。

**E3（特征预实验 P1：效果层 vs 因子层）——same_question，方向一致但不可比。** 论文的核心信号是逐样本梯度在最后一个 transformer 层 lora_B 上的 2D-DCT 频率特征（Section V-A、Section V-B），问的是"毒样本与干净样本能否在梯度特征上分开"；我们问的是"恶意客户端的更新在效果层（LoRA 乘积 BA）与因子层（A、B 分开）上是否有可分特征"，属于同一大类问题、粒度不同。看起来一致的是"观察模块/层的选择具有决定性"这一点：论文 Table IX 显示 layers.31.lora_B 的 Recall/F1 为 100.00/100.00，而同层 lora_A 只有 36.92/13.79、layers.0.lora_B 只有 28.00/15.14；我们 E3 里因子层方向能在 17/20 轮标出恶意客户端、效果层大小 15/20 轮，而效果层方向只有 3/20 轮。也就是说，两边都指向"取 LoRA 的 B 侧、取更深层的信号更有效"。但我们的粒度是客户端聚合更新、论文是逐样本梯度，我们的设置只有 1 个恶意客户端、单种子、20 轮，数值不可比。

**E4（良性基线与校准 P2）——same_question（误报/保守回退）与 setting_reference（NIID 参照），都不可比。** 论文用轮廓系数阈值做保守回退：两种聚类的轮廓系数中较小者小于 t_s = 0.2 且较大者小于 t_l = 0.4 时，客户端把全部数据视为干净、不执行过滤（Section V-B、Section VI-D4）；Table V 只给了完全干净数据下的 CACC 损失小于 1%。我们 E4 用 4 种无攻击划分各 3 个种子校准 1% 误报阈值后检测，发现毒占比 100% 时效果层大小能标出 18/18 轮、效果层方向 14/18 轮，占比 30% 时最好 6/18，占比 10% 时只有 1–2/18、与误报相当。两边都在问"无攻击时会不会误杀、低毒占比还灵不灵"，但论文只报 CACC，没有报误报率或良性数据下的样本屏蔽比例（卡片未给），我们的数字是逐轮检出计数，不是同一指标，不能互相印证。作为设置参照，论文的 NIID-2（Dirichlet α = 0.5，每客户端毒比例上限 0.5）与 NIID-3（无上限），以及 Table VII 在 FreebaseQA 上 α 取 0.1/0.3/0.7/1.0 时的 Recall（NIID-3 下 99.56、96.86、98.81、99.34），是我们做非独立同分布时要对齐的参照；我们 E4 只观察到按 Dolly 类别的 Dirichlet 划分对 LoRA 更新相似度几乎没有影响，那是另一个量，不能与论文的 Recall 对照。另外，我们 E4 发现无攻击的良性微调本身就让 AdvBench 无害率从 81% 降到 49–63%（alpaca 模板），而论文只用干净 EMR（CACC）作为效用指标（Section VI-A4、Table V），没有测安全性效用，这不构成矛盾，但说明 CACC 不足以覆盖我们关心的风险。

**E5（自动攻击矩阵 P3）——same_question，方向一致、数值不可比。** 论文在 Section VI-B 把 FreqFed 失效解释为"含后门特征的模型更新数量有限"，即攻击不是来自少数恶意客户端的更新，而是散布在所有良性客户端的本地数据里；Section VI-D2 把方法成立的前提写成"干净数据在多数客户端占主导"；Table XII 又显示 ProtegoFed 单独面对 10%/20%/30%/40% 恶意合谋客户端时最终 ASR 为 0.00/0.08/20.62/40.29，必须叠加 FreqFed 才能全部降到 0.00。我们 E5 在 33 次训练里发现：对 1 个恶意客户端、恶意占比 ≥30% 时逐轮检出 83–100%、误报 0.6–1.9%，而盲区正是分散的低浓度投毒（2–3 个恶意客户端各 10%，检出 3–15%）和每轮只抽 5 个客户端（24–35%）。两者方向一致：分散、低浓度、客户端级的投毒是用户级/样本级防御的难点。但论文的恶意客户端比例是客户端合谋比例、主实验毒比例是每客户端 10% 的 IID 或 NIID 随机，与我们"2–3 个客户端各 10%"不是同一设置，我们多为单种子、论文种子数卡片未给，所以只能作方向性印证。

**E6（已发表防御的可用性批量）——method_source，看起来矛盾但不可比；同时是 setting_reference。** 我们在 E6 里把 ProtegoFed 端到端跑通，读到一次样本过滤结果：4B、480 条样本中 96 条带毒时精确率 0.77、召回率 0.49；论文 Table III（IID）报 Recall 92.00% ∼ 100.00%，FreebaseQA 与 CoQA 在所有攻击变体下 Recall 均为 100.00%，F1 接近或超过 90%。0.49 与 92%–100% 看起来是矛盾的。但不能直接比较：我们的样本量（480 条，含 96 条毒）远小于论文每数据集 5000 条训练样本，客户端数 5 对 25，轮数 4 对 100，我们的场景 A（4 良性 + 1 有害数据客户端）与场景 B（每客户端 20% 样本带触发器与固定目标输出）也不等于论文的 IID 每客户端 10% 毒比例；更关键的是论文的 Recall 是走完"客户端内聚类 → 服务器二次聚类 → 本地修正"整套流程之后的数字（Section V-A、V-D），我们的只是单次样本过滤读数，且我们自己明确不评价防御效果。引用论文数字时还要注意卡片记录的正文与表格不一致（Section VI-C 的 79.12%/99.08% 对 Table III 的 82.71/92.00）。作为设置参照，论文 Table II 的对照方法是 Krum、Median、Trimmed-mean、FreqFed、FoundationFL、CUBE、GraCeFul、ONION（Section VI-A6）；我们 E6 覆盖了 Krum、坐标中位数、截尾均值、FreqFed、ONION，但没有 FoundationFL、CUBE、GraCeFul，也没有在同等设置下评 ASR/CACC，因此无法复现 Table I/Table II 的对照。

**E7（无攻击对照）——same_question，方向一致、数值不可比。** 论文 Table V 给完全干净数据下的对照，ProtegoFed 的 CACC 损失小于 1%（WebQA 45.86 → 45.28、FreebaseQA 64.95 → 64.05、CoQA 73.09 → 72.29、NQ 74.80 → 73.95），并在轮廓系数过低时干脆不动作（Section V-B）。我们 E7 在无攻击下观察到 ProtegoFed 屏蔽 4% 样本、MCD 不排除、Safe-FedLLM 权重不变，而 Krum 仍排除 80% 的客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%、梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本。方向一致：样本过滤型防御在无攻击时动作很小，而客户端排除型防御会造成大量无谓排除。但我们的 4% 是样本屏蔽比例、论文的 <1% 是 CACC 损失，不是同一个量；论文也没有报告无攻击时各防御的误报率或排除比例（卡片未给），我们这边是单次运行。

**E8（宿主适配）——method_source，形态一致。** 我们在 E8 里把 ProtegoFed 经一层握手扩展挂到 Flower（合成客户端与真实模型 Qwen2.5-0.5B、Qwen3.5-0.8B），并在 OpenFedLLM 原版上经改脚本挂载，规模 4–5 个客户端、2 轮。卡片第 10 节列出的接口需求——训练开始前的逐样本梯度钩子（且目标模块要可配置、不能硬编码最后一层）、与"每轮客户端钩子"区分的训练前一次性阶段钩子、服务器在聚合模型参数之前的元数据聚合通道（聚合的是质心而不是权重）、只重写本地训练集的 filter_samples 动作、以及同一阶段内复用本地频率特征——正好对应我们握手扩展补上的能力。方向一致：论文要求的钩子形态在宿主上不是原生的，需要额外适配；论文未描述任何工程挂载细节（卡片未给），所以这只是形态上的一致。

**E9（Safe-FedLLM 式 LoRA 权重探针）——background。** 论文的动作是过滤样本（Section V-D），机制不是权重探针，没有直接对应。但 E9 的教训（同一初始化种子下拟合再应用有效，换一次运行后恶意客户端概率 0.00）提醒我们：卡片没有给论文的种子数（卡片未给），Table IX 里 layers.31.lora_B 的 Recall/F1 均为 100.00 这类数字也没有跨种子稳定性信息，我们不应把它当作稳定结论来对标。

**E10（调研与知识库）——background。** 这篇论文应作为 E10 知识库中的一篇卡片；它需要的算子（训练前逐样本梯度钩子、服务器侧元数据二次聚类与广播、样本级过滤）恰好落在我们 481 个步骤里"10% 缺算子、13% 超出运行时、39% 要拼"的那部分。卡片第 10 节也把"训练前逐样本梯度钩子"称为通用性最低、却是整个防御的硬前提。这条只用于登记，不构成实验结论层面的印证。

## 3. 我们要与它可比还差什么

1. **模型规模**：论文覆盖 9 个 1B–70B 模型（Section VI-A2、Table IV），我们最大只到 4B 且只跑 4 轮。要做 Table IV 式对照，至少要有一个 ≥7B 的完整训练。
2. **客户端与数据量**：论文主实验 25 个客户端、每数据集 5000 训练 / 400 验证 / 2000 测试（Section VI-A1、VI-A3），我们 4–10 个客户端、几百条样本（E6 只有 480 条）。要么把客户端数与每客户端样本量提到同一量级，要么在报告里显式写明样本量差异以说明不可比。
3. **轮数与 LoRA 超参**：论文 r = 4、本地 1 个 epoch、100 轮、学习率 2×10⁻⁵（Section VI-A7）；我们 2–20 轮、E3 用 r = 16、每轮 5–6 步。需要跑到 100 轮量级并把 r 与学习率写成论文口径。
4. **攻击类型与毒比例设置**：论文有 Badnets、Addsent、CBA、StyleBkd 四种触发器加统一定义的误导目标句（Section VI-A5），以及 IID 每客户端 10%、NIID-1/2/3（Section VI-A3、VI-D2）、恶意合谋客户端 10/20/30/40%（Table XII）、自适应高频一对多后门（Section VII-C、Table XI）。我们现在只有 MaliciousGen 有害问答，以及场景 B 的触发词加固定目标输出，没有这四种触发器和这套毒比例网格。
5. **评测指标**：论文用干净 EMR 作为 CACC、毒样本 EMR 作为 ASR、样本级 Recall 与 F1，以及 Table VIII 的 Accuracy/Precision/Recall/F1 口径和 Table XII 的 B-Recall（Section VI-A4）。我们没有后门 ASR 评测（我们自己也把"后门的攻击成功率评测"列为未做），目前的逐轮检出计数、一次过滤读数和 AdvBench 无害率都无法对齐。要补的是在过滤前后各测一次 CACC 与 ASR。
6. **消融口径**：目标模块要可在 layers.31.lora_B / layers.31.lora_A / layers.15.lora_B / layers.0.lora_B / embed_tokens / lm_head 之间切换（Table IX），并支持"有/无全局二次聚类与本地修正"（Table VIII）与"有无 HDBSCAN、有无层次聚类、有无阈值"（Table X）三组消融，同时暴露 t_s = 0.2、t_l = 0.4 的保守回退阈值（Section V-B）。我们的库目前只做过一次样本过滤读数。
7. **对比方法**：要对齐 Table II，需要补齐 FoundationFL、CUBE、GraCeFul 三个我们没有的方法，并在同一设置下评 ASR/CACC/Recall/F1，而不只是"端到端跑通、不评价防御效果"。
8. **开销口径**：论文报一次性 12.43 / 0.07 / 0.39 秒、约占总训练时间 1%、100 轮总时间比 FedAvg 更短（Section VII-A、Figure 13），但卡片未给这 12.43 秒对应的模型与样本量；我们只在 4 轮、4B 上量到每客户端每轮 3.8 秒。要在同一轮数量级下重测，并把一次性与摊销分开报，另需注意论文自身没给通信与存储开销、显存实证也尚未补完。
9. **多种子与置信区间**：卡片未给论文的种子数，所以我们不能以"论文做了多种子"为对齐目标；但我们要与它可比，至少要跑满它给出的配置，并给我们自己的数字补上多种子与置信区间（目前 E3、E7、E9 都是单次或单种子）。
10. **隐私与自适应**：论文把上传的局部质心当作非私有信息，只用"质心不对应真实样本"作论证，未做隐私攻击评估（卡片未给隐私评测）；我们应明确不把质心当已验证安全。自适应方面论文只测了高频一对多后门（Table XI，Recall 62.00、F1 38.06），我们的"知道防御的自适应攻击"完全未做。
11. **参与率**：论文未说明每轮采样多少客户端（卡片明确写了"论文未说明"），这一项无法对齐，我们应自己报告客户端采样率，并说明它在我们的设置里是否影响结论（E5 的"每轮只抽 5 个客户端检出 24–35%"正说明这一点关键）。

```json
{
  "key": "protegofed2026",
  "paper_scale": {
    "models": "9 个开源大模型，1B 到 70B：Llama-3.2-1B、Llama-3.2-3B、GPT-J-6B、Llama-2-7B、Vicuna-7B、Mistral-7B-v0.1、Gemma-2-9B、Llama-2-13B、Llama-2-70B（Section VI-A2、Table IV）",
    "clients": "IID 主实验为 25 个客户端，训练数据均分（Section VI-A3）；每轮采样多少客户端论文未说明",
    "rounds": "100 轮通信，本地 1 个 epoch，LoRA r=4，学习率 2×10⁻⁵（Section VI-A7）",
    "poison_setting": "IID 每客户端毒比例 10%（Section VI-A3）；NIID-1 每客户端毒比例在 [0,0.4] 随机；NIID-2 Dirichlet α=0.5 且每客户端上限 0.5；NIID-3 去掉上限（Section VI-D2）；攻击方法 Badnets、Addsent、CBA、StyleBkd，目标输出统一为预定义误导句（Section VI-A5）；恶意合谋客户端比例 10%/20%/30%/40%（Table XII）；自适应攻击为高频一对多后门（Section VII-C、Table XI）",
    "seeds": "卡片未给",
    "federated": true,
    "lora": true
  },
  "headline_results": [
    "Table II：4 个数据集 × 4 种攻击共 16 个设置里 ProtegoFed 把 ASR 全部降到 0.00，对照方法多数仍在数十到接近 100（WebQA 上 Badnets：无防御 98.08、Krum 96.75、Median 97.29、Trimmed 97.05、FreqFed 98.23、FoundationFL 89.71、CUBE 97.93、GraCeFul 79.72、ONION 95.32、ProtegoFed 0.00）",
    "Table III（IID）与 Abstract：样本级 Recall 为 92.00% ∼ 100.00%，唯一 92.00 出现在 WebQA 的 CBA，FreebaseQA 与 CoQA 在所有攻击变体下 Recall 均为 100.00%，F1 在 FreebaseQA、CoQA 上接近或超过 90%；Abstract 记为识别 92.00% ∼ 100.00% 的投毒样本、ASR 降到接近零。注意卡片指出 Section VI-C 正文（WebQA CBA 的 F1 79.12%、Recall 99.08%）与 Table III（F1 82.71、Recall 92.00）不一致，79.12 实为 Table I 中 GraCeFul 在 Vicuna + Addsent 上的 Recall",
    "Table V（完全干净数据）：CACC 损失小于 1%，WebQA 45.86 → 45.28、FreebaseQA 64.95 → 64.05、CoQA 73.09 → 72.29、NQ 74.80 → 73.95"
  ],
  "links": [
    {"experiment": "E1", "relation": "background", "agreement": "n/a", "detail": "论文的防御会重写客户端本地训练集（Section V-D、式 15），必然改变训练结果，卡片也没有讨论宿主中立性或“不动作即等价”的对照；E1 的逐位相同结论与它没有直接对应，只用于区分我们库里的被动挂载与主动干预。"},
    {"experiment": "E2", "relation": "method_source", "agreement": "not_comparable", "detail": "E2 量到 ProtegoFed 逐样本梯度每客户端每轮 3.8 秒（训练 2.1 秒，Qwen3.5-4B），论文 Section VII-A 报的是一次性开销 12.43 秒（客户端内聚类）、0.07 秒（全局聚类）、0.39 秒（本地修正），约占 100 轮总训练时间的 1%，且总训练时间比 FedAvg 更短；我们 4 轮、论文 100 轮，口径（每轮 vs 一次性）与模型都不同，卡片也未给 12.43 秒对应的模型与样本量，不能直接比较。"},
    {"experiment": "E2", "relation": "setting_reference", "agreement": "n/a", "detail": "论文 Section VI-D7 称 UMAP 与 HDBSCAN 复杂度约 O(N log N)、逐样本梯度属于正常训练流程且峰值显存不超过正常流程，但同节又写显存实证“We will add a part to further demonstrate its practicality”，即论文自身尚未补完；论文也未报告通信与存储开销。我们要报开销时应把一次性与摊销分开，并落到 100 轮量级。"},
    {"experiment": "E3", "relation": "same_question", "agreement": "consistent", "detail": "论文问毒样本能否靠梯度特征与干净样本分开，观察点是逐样本梯度在最后一个 transformer 层 lora_B 上的 2D-DCT 频率特征（Section V-A、V-B）；我们 E3 比较客户端更新在效果层（BA）与因子层（A、B 分开）上的大小与方向。看起来一致的是“观察模块/层的选择具有决定性”：论文 Table IX 中 layers.31.lora_B 的 Recall/F1 为 100.00/100.00，同层 lora_A 只有 36.92/13.79，layers.0.lora_B 只有 28.00/15.14；我们 E3 里因子层方向 17/20 轮、效果层大小 15/20 轮能标出恶意客户端，效果层方向只有 3/20 轮。但我们的粒度是客户端聚合更新、论文是逐样本梯度，我们只有 1 个恶意客户端、单种子、20 轮，数值不可比。"},
    {"experiment": "E4", "relation": "same_question", "agreement": "not_comparable", "detail": "论文用轮廓系数阈值做保守回退（较小者小于 t_s = 0.2 且较大者小于 t_l = 0.4 时全部判为干净，Section V-B、VI-D4），并只在 Table V 给出完全干净数据下 CACC 损失小于 1%（WebQA 45.86 → 45.28、FreebaseQA 64.95 → 64.05、CoQA 73.09 → 72.29、NQ 74.80 → 73.95），没有报误报率或良性数据下的样本屏蔽比例（卡片未给）。我们 E4 用 4 种无攻击划分各 3 个种子校准 1% 误报阈值后检测，毒占比 10% 时只有 1–2/18 轮、与误报相当。两者问的是同一类“无攻击时会不会误杀”的问题，但我们的逐轮检出计数与论文的 CACC 不是同一指标，不能互相印证。"},
    {"experiment": "E4", "relation": "setting_reference", "agreement": "n/a", "detail": "论文的 NIID-2（Dirichlet α = 0.5，每客户端毒比例上限 0.5）与 NIID-3（去掉上限），以及 Table VII 在 FreebaseQA 上 α 取 0.1/0.3/0.7/1.0 时的 Recall（NIID-3 下 99.56、96.86、98.81、99.34）是我们做非独立同分布时应参照的设置；我们 E4 只观察到按 Dolly 类别的 Dirichlet 划分对 LoRA 更新相似度几乎没有影响，那是另一个量，不能与论文的 Recall 对照。"},
    {"experiment": "E5", "relation": "same_question", "agreement": "consistent", "detail": "论文 Section VI-B 把 FreqFed 失效解释为“含后门特征的模型更新数量有限”，Section VI-D2 把方法成立的前提写成“干净数据在多数客户端占主导”，Table XII 显示 ProtegoFed 单独面对 10%/20%/30%/40% 恶意合谋客户端时最终 ASR 为 0.00/0.08/20.62/40.29、必须叠加 FreqFed 才全部降到 0.00。我们 E5 在 33 次训练里发现 1 个恶意客户端、恶意占比 ≥30% 时逐轮检出 83–100%、误报 0.6–1.9%，而 2–3 个恶意客户端各 10% 的分散低浓度投毒只有 3–15% 检出、每轮只抽 5 个客户端时只有 24–35%。方向一致：分散、低浓度的客户端级投毒是这类用户级/样本级防御的盲区。但论文的恶意客户端比例是客户端合谋比例、主实验毒比例是每客户端 10% 的 IID 或 NIID 随机，与我们“2–3 个客户端各 10%”不是同一设置，我们多为单种子、论文种子数卡片未给，数值不能直接比较。"},
    {"experiment": "E6", "relation": "method_source", "agreement": "contradicts", "detail": "我们 E6 把 ProtegoFed 端到端跑通，读到一次样本过滤结果：4B、480 条样本中 96 条带毒时精确率 0.77、召回率 0.49；论文 Table III（IID）报 Recall 92.00% ∼ 100.00%（唯一 92.00 是 WebQA 的 CBA），FreebaseQA 与 CoQA 在所有攻击变体下 Recall 均为 100.00%，F1 接近或超过 90%。0.49 与 92%–100% 看起来矛盾。但不能直接比较：我们 480 条样本对论文每数据集 5000 条训练样本，5 个客户端对 25 个，4 轮对 100 轮，我们的场景 A/B 也不等于论文 IID 每客户端 10% 毒比例；而且论文的 Recall 是走完客户端内聚类、服务器二次聚类与本地修正整套流程（Section V-A、V-D）后的数字，我们的只是单次样本过滤读数、且未评价防御效果。引用时还需按卡片提示避开正文与表格不一致（Section VI-C 的 79.12%/99.08% 对 Table III 的 82.71/92.00），以 Table III 为准。"},
    {"experiment": "E6", "relation": "setting_reference", "agreement": "n/a", "detail": "论文 Table II 的对照方法是 Krum、Median、Trimmed-mean、FreqFed、FoundationFL、CUBE、GraCeFul、ONION（Section VI-A6）；我们 E6 覆盖 Krum、坐标中位数、截尾均值、FreqFed、ONION，缺 FoundationFL、CUBE、GraCeFul，而且我们没有在同等设置下评 ASR/CACC，因此无法复现 Table I/Table II 的对照，只能先对齐方法清单与指标口径。"},
    {"experiment": "E7", "relation": "same_question", "agreement": "consistent", "detail": "论文 Table V 给出完全干净数据下的对照，ProtegoFed 的 CACC 损失小于 1%（WebQA 45.86 → 45.28、FreebaseQA 64.95 → 64.05、CoQA 73.09 → 72.29、NQ 74.80 → 73.95），并在轮廓系数过低时不动作（Section V-B）；我们 E7 在无攻击下观察到 ProtegoFed 屏蔽 4% 样本、MCD 不排除、Safe-FedLLM 权重不变，而 Krum 仍排除 80% 客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%、梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本。方向一致：样本过滤型防御在无攻击时动作很小，客户端排除型防御会造成大量无谓排除。但我们的 4% 是样本屏蔽比例、论文的 <1% 是 CACC 损失，不是同一个量；论文未给无攻击时各防御的误报率或排除比例（卡片未给），我们这边是单次运行。"},
    {"experiment": "E8", "relation": "method_source", "agreement": "consistent", "detail": "我们在 E8 里把 ProtegoFed 经一层握手扩展挂到 Flower（合成客户端与真实模型 Qwen2.5-0.5B、Qwen3.5-0.8B），并在 OpenFedLLM 原版上经改脚本挂载，规模 4–5 个客户端、2 轮。卡片第 10 节列出的接口需求——训练前逐样本梯度钩子且目标模块可配置、与每轮钩子区分的训练前一次性阶段钩子、服务器在聚合模型参数之前的元数据聚合通道（聚合质心而非权重）、只重写本地训练集的 filter_samples 动作、同一阶段内复用本地频率特征——正好对应我们握手扩展补上的能力。方向一致：论文要求的钩子形态在宿主上不是原生的，需要额外适配；论文未描述工程挂载细节（卡片未给），所以只是形态上的一致。"},
    {"experiment": "E9", "relation": "background", "agreement": "n/a", "detail": "论文的动作是过滤样本（Section V-D），机制不是权重探针，与 E9 的 Safe-FedLLM 式 LoRA 权重探针没有直接对应。但 E9 的教训（同一初始化种子下拟合再应用有效，换一次运行后恶意客户端概率 0.00）提醒我们：卡片未给论文的种子数，Table IX 里 layers.31.lora_B 的 Recall/F1 均为 100.00 这类数字也没有跨种子稳定性信息，不应把它当作稳定结论来对标。"},
    {"experiment": "E10", "relation": "background", "agreement": "n/a", "detail": "这篇论文应作为 E10 知识库中的一篇卡片；它需要的算子（训练前逐样本梯度钩子、服务器侧元数据二次聚类与广播、样本级过滤）落在我们 481 个步骤里“10% 缺算子、13% 超出运行时、39% 要拼”的那部分，卡片第 10 节也把训练前逐样本梯度钩子称为通用性最低却不可缺的硬前提。这条只用于登记，不构成实验结论层面的印证。"}
  ],
  "missing_for_comparability": [
    "模型规模：论文覆盖 9 个 1B–70B 模型（Section VI-A2、Table IV），我们最大只到 4B 且只跑 4 轮，至少要有一个 ≥7B 的完整训练才能做 Table IV 式对照。",
    "客户端与数据量：论文 25 个客户端、每数据集 5000 训练 / 400 验证 / 2000 测试（Section VI-A1、VI-A3），我们 4–10 个客户端、几百条样本（E6 只有 480 条），需要提到同一量级或显式声明不可比。",
    "轮数与 LoRA 超参：论文 r = 4、本地 1 个 epoch、100 轮、学习率 2×10⁻⁵（Section VI-A7），我们 2–20 轮、E3 用 r = 16、每轮 5–6 步，需要跑 100 轮量级并统一超参口径。",
    "攻击类型与毒比例网格：论文的 Badnets、Addsent、CBA、StyleBkd 四种触发器加统一误导目标句（Section VI-A5），IID 每客户端 10%、NIID-1/2/3（Section VI-A3、VI-D2）、恶意合谋 10/20/30/40%（Table XII）、自适应高频一对多后门（Section VII-C、Table XI）；我们目前只有 MaliciousGen 有害问答与场景 B 的触发词固定目标。",
    "指标：论文用干净 EMR（CACC）、毒样本 EMR（ASR）、样本级 Recall 与 F1，以及 Table VIII 的 Accuracy/Precision/Recall/F1 口径和 Table XII 的 B-Recall（Section VI-A4）；我们没有 ASR 评测，现有逐轮检出计数、一次过滤读数与 AdvBench 无害率都无法对齐，需要在过滤前后各测一次 CACC 与 ASR。",
    "消融条件：目标模块要可切换（Table IX：layers.31.lora_B / lora_A / layers.15.lora_B / layers.0.lora_B / embed_tokens / lm_head），要支持有/无全局二次聚类与本地修正（Table VIII）、有/无 HDBSCAN、层次聚类与阈值（Table X），并暴露 t_s = 0.2、t_l = 0.4 的保守回退（Section V-B）；我们目前只做过一次样本过滤读数。",
    "对比方法：为对齐 Table II 需补 FoundationFL、CUBE、GraCeFul，并评 ASR/CACC/Recall/F1，而不是只验证“端到端跑通、不评价防御效果”。",
    "开销口径：论文一次性 12.43 / 0.07 / 0.39 秒、约占总训练时间 1%、100 轮总时间比 FedAvg 更短（Section VII-A、Figure 13；12.43 秒对应的模型与样本量卡片未给），我们只在 4 轮、4B 上量到每客户端每轮 3.8 秒；需在同一轮数量级下把一次性与摊销分开重测。",
    "多种子与置信区间：卡片未给论文的种子数，我们多为单种子或单次（E3、E7、E9），要自证可比需要多种子与置信区间。",
    "隐私与自适应：论文把局部质心当作非私有信息、未做隐私攻击评估（卡片未给隐私评测）；论文只测了高频一对多后门的自适应攻击（Table XI，Recall 62.00、F1 38.06），而我们的“知道防御的自适应攻击”完全未做。",
    "参与率：论文未说明每轮采样多少客户端（卡片明确），这一项无法对齐，我们应自己报告客户端采样率，并说明它对结论的影响（E5 显示每轮只抽 5 个客户端时检出降到 24–35%）。"
  ],
  "metrics_paper_uses": [
    "干净精确匹配率 clean EMR 作为干净任务准确率 CACC（Section VI-A4）",
    "毒样本 EMR 作为攻击成功率 ASR（Section VI-A4）",
    "针对样本级防御的 Recall（Section VI-A4、Table III、Table IV、Table VI、Table VII）",
    "F1（Section VI-A4、Table III、Table IX、Table X、Table XI）",
    "恶意客户端场景下的良性客户端召回率 B-Recall（Table XII）",
    "消融中的 Accuracy、Precision、Recall、F1（Table VIII）",
    "时间开销（Section VII-A、Figure 13：一次性 12.43 / 0.07 / 0.39 秒，约占总训练时间 1%）"
  ],
  "relevance": "high"
}
```
