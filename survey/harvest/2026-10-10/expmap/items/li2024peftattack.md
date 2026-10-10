## 1. 论文自己的实验规模与主要结果

**规模与设置（均照抄卡片）。** 系统为 1 个服务器加 15 个客户端（K = 15），恶意客户端数量在 [0, 5] 之间变化，每轮全部客户端参与（Section IV-A）。基座模型是四个开源 PLM——LLaMA-2-7B-Chat、Phi-3.5-Mini-Instruct、LLaMA-3.2-3B-Instruct、Qwen2.5-7B-Instruct，微调时全部 4-bit 量化；PEFT 方法有 LoRA、(IA)3、LayerNorm 三种（Figure 1）。可训练参数比例见 Table I：LLaMA-2-7B-Chat 上 LoRA 40.0M/6.8B 即 0.59%、(IA)3 0.6M/6.7B 即 0.009%、LayerNorm 0.3M/6.7B 即 0.004%；Phi-3.5-Mini-Instruct 上 LoRA 29.9M/3.9B 即 0.78%、(IA)3 0.3M/3.8B 即 0.007%、LayerNorm 0.1M/3.8B 即 0.003%；LLaMA-3.2-3B-Instruct 与 Qwen2.5-7B-Instruct 两行都给 LoRA 40.4M/7.6B 即 0.53%、(IA)3 0.7M/8.0B 即 0.009%、LayerNorm 0.1M/7.6B 即 0.001%。卡片同时指出两处不一致：正文 Section IV-A 说可训练比例是 0.001%–0.59%，与 Table I 的 0.78% 不符；LLaMA-3.2-3B-Instruct 那一行的总参数 7.6B 与 3B 级命名不相称。默认训练 25 轮、每轮 50 个本地步、学习率 0.001、AdamW、批大小 4（Section IV-B）。数据方面：下游任务是 MedQA 与 MetaMathQA，中毒数据来自 BeaverTails 的 `is_safe=False` 子集，对齐数据来自 CAI-Conversation-Harmless，安全评测用 AdvBench 与 JailbreakBench（Section IV-A、Section IV-C）。默认 IID；RAS 实验另设 Non-IID，即 12 个良性客户端在 MedQA 与 MetaMathQA 上各 6 个（Section V-C、Table II）。RAS 实验里 15 个客户端中有 3 个恶意（Section V-C）；PPSA 实验是 9 个微调客户端、3 个恶意客户端（第 0 到 5 轮激活）、3 个对齐客户端（第 11 到 14 轮激活），共 14 轮（Section V-D、Figure 5）。评测指标为安全性 ASR（由 OpenAI chat completion API 判定输出是否有害）和 MedQA/MetaMathQA 准确率（Section IV-C）。**每个恶意客户端注入的有害样本数量或中毒比例，卡片未给；随机种子，卡片未给；攻击与防御的计算、通信、存储开销，卡片第 8 节明确写论文未报告。**

**主要结果。** 良性条件下 LoRA 在四个模型上一致提升准确率，论文写为准确率增益 28%–67%（Figure 3 说明；Section V-A），(IA)3 与 LayerNorm 不稳定。攻击效果上，第 0 轮所有 PLM 的 ASR 都很低，正文写 ASR < 4%，Figure 4 标注的第 0 轮数值为 AdvBench 上 LLaMA-2-7B-Chat 0.3%、Phi-3.5-Mini-Instruct 1.7%、LLaMA-3.2-3B-Instruct 2.0%、Qwen2.5-7B-Instruct 2.5%，JailbreakBench 上分别为 1.5%、0.8%、4.2%、3.5%（卡片分析指出正文"< 4%"与图中 4.2% 略有出入）；随着联邦微调推进，尤其在 1 个或 5 个恶意客户端时所有 PEFT 方法 ASR 显著上升，LoRA 最容易被打穿、多数情况下第 20 轮 ASR 超过 70%，(IA)3 与 LayerNorm 一般在 40%–60%（Section V-B），摘要把最高值表述为"up to 80% attack success rate"（Abstract）。防御方面，Table II 给出的 AdvBench ASR 为：基座模型 MedQA 准确率 56.9%、MetaMathQA 80.0%、AdvBench ASR 1.3%、JailbreakBench ASR 1.3%；MedQA-only 同构设置 Mean 83.5%、Median 84.5%、GeoMed 83.5%、DnC 1.0%、ClippedClustering 0.0%；MetaMathQA-only 设置 Mean 49.5%、Median 40.5%、GeoMed 46.5%、DnC 85.5%、ClippedClustering 3.0%；6 MedQA + 6 MetaMathQA 混合域设置 Mean 77.5%、Median 80.0%、GeoMed 76.0%、DnC 82.5%、ClippedClustering 81.0%，对应 JailbreakBench ASR 77.4%、81.8%、72.4%、87.7%、88.3%；结论是 Median 与 GeoMed 在任何分布下都防不住（ASR > 30.7%），DnC 与 ClippedClustering 只在 MedQA 同构设置下有效（ASR ≤ 2%），数据异构时失效（ASR > 80%）（Section V-C、Table II）。PPSA 方面，恶意客户端存在的最初 5 轮内 ASR 快速上升，AdvBench 达到 57%、JailbreakBench 达到 65%；随后正常微调轮次中 ASR 无显著变化；第 11 到 14 轮对齐客户端介入后 ASR 迅速降到 10% 以下，但带来"对齐税"，例如 LLaMA-3.2-3B-Instruct 在 MedQA 上准确率最多下降 3%、在 MetaMathQA 上下降 20%（Section V-D、Figure 5）。

## 2. 与我们各项实验的对应

**E1（不改变训练）：background，无一致性判定。** 论文没有检验"库挂上但不动作时训练逐位不变"这类命题。它只是把"恶意客户端也必须遵守标准 FedPEFT 协议、不能修改被冻结的基座参数 w"作为威胁模型前提（Section III-B 原文："However, the adversaries must follow the standard FedPEFT protocol, including the communication pattern and local training process (i.e., ClientOpt)."）。E1 的逐位相同只是我们自己的协议保真性检查，与论文的结论既不印证也不冲突；而且规模差得远（我们 Qwen2.5-0.5B、3 轮、CPU，论文是 7B 级模型、25 轮、A100）。同族模型不同尺寸这一点要注意：论文里的 Qwen2.5-7B-Instruct 与我们 E1 用的 Qwen2.5-0.5B 只同族，不可互推。

**E2（开销）：background，无一致性判定。** 卡片第 8 节明确写"论文未报告攻击或防御的计算、通信、存储开销"，只有定性陈述（Table I 的可训练参数比例 0.001%–0.78%、Section III-A 与 Section IV-B 说 PEFT 只交换紧凑更新并用 4-bit 量化）。因此 E2 的 0.7%–2.8%、0.25%–1.8%、60 次哈希对照，以及 ProtegoFed 逐样本梯度每客户端每轮 3.8 秒（训练 2.1 秒）、更新子空间投影 5.7 秒、ONION 3.2 秒，在论文侧没有任何数字可对齐，只能作为我们自己的成本基线。论文中的 Median/GeoMed/DnC/ClippedClustering 与 PPSA 的额外开销同样卡片未给。

**E3（特征预实验 P1）：same_question，结论方向一致；另可视为不忠实的 method_source。** 两者问的是同一个问题：少数恶意客户端用有害指令数据做本地 LoRA 微调，其更新是否与良性客户端可分。论文侧依据是 Table II：在 MedQA-only 同构设置、15 个客户端中 3 个恶意时，DnC 的 AdvBench ASR 为 1.0%、ClippedClustering 为 0.0%（Section V-C、Table II），说明更新空间里确实存在可被利用的信号。我们 E3 在 1/10 恶意、恶意数据占比 100% 时，效果层大小在 15/20 轮标出恶意客户端、因子层方向 17/20 轮，方向与"集中投毒时更新层面可分"一致。但**不能直接比较**：我们没有测 ASR，论文没有测逐轮特征检出率；我们是 Qwen2.5-0.5B、20 轮、单种子、Dirichlet 0.5，论文是 7B 级、默认 IID、25 轮（RAS 配置卡片第 9 节分析为 20 轮）、种子卡片未给。另外要注意论文的 Median 与 GeoMed 在所有设置下都失败（ASR > 30.7%，Section V-C），这说明"更新里有信号"与"鲁棒聚合算子能利用这个信号"是两件事，E3 的检出率不能读成防御有效性。至于 method_source：我们的恶意客户端是"本地有害问答数据 + 标准 FedAvg 协议 + 只更新 LoRA"，机制上与 PaaA 同类（Section III-B、Section III-A 的 Eq. (4)–(7)），但我们用的是 MaliciousGen，不是 BeaverTails 的 `is_safe=False` 子集，也没用论文的模板，模型是 0.5B 且没有 ASR 终点，所以不是忠实复现，结果不能直接比较。

**E4（良性基线与校准 P2）：same_question，卡片未给可比数字，判为不可直接比较；同时是一个 setting_reference。** 论文在卡片里只有第 0 轮的 ASR（< 4%，Figure 4 有逐模型标注），**卡片未给"0 个恶意客户端时完整联邦微调"的安全曲线**，所以论文并没有回答"良性联邦指令微调本身会不会削弱安全对齐"这个问题。我们 E4 量到无攻击的良性微调就让 AdvBench 无害率从 81% 降到 49–63%（alpaca 模板，Qwen2.5-0.5B），这个现象论文未报告，无法印证或反驳；更值得注意的是它构成对论文 ASR 增益的一个未控制混淆——如果良性微调本身就带来安全漂移，攻击的净增量应当用无攻击曲线扣除，而论文的隐蔽性论述只保证"良性任务表现不变"（Section III-B），不保证安全维度不变。度量口径也不同：我们用 AdvBench 无害率，论文用 OpenAI chat completion API 判定的 ASR；模型 0.5B 对 7B 级；数据是 Dolly 对 MedQA/MetaMathQA。作为 setting_reference：论文默认 IID（Section IV-A），其异构设置是域级划分（12 个良性客户端在 MedQA 与 MetaMathQA 各 6 个，Section V-C、Table II），而我们 E4 的 Dirichlet 1.0/0.5/0.1 是按 Dolly 类别的标签级偏斜；我们观察到"按 Dolly 类别的 Dirichlet 划分对 LoRA 更新相似度几乎没有影响"，这不能外推到论文那种域级异构，因此不能用它预测论文"异构下 DnC/ClippedClustering 失效（ASR > 80%）"的结论。

**E5（自动攻击矩阵 P3）：same_question，方向一致；同时是 setting_reference。** 两者都在问恶意客户端数量与投毒集中程度如何影响可检测性。论文把恶意客户端数量在 [0, 5] 之间变化（Section IV-A），RAS 实验固定 3/15（Section V-C），结论是 DnC 与 ClippedClustering 在同构 MedQA 下把 ASR 压到 ≤ 2%、在异构下失效到 ASR > 80%，Median 与 GeoMed 任何分布下 ASR > 30.7%（Section V-C、Table II）。我们 E5 的盲区是分散的低浓度投毒（2–3 个恶意客户端各 10% 时检出 3–15%）和每轮只抽 5 个客户端（检出 24–35%），与"信号被稀释后防御失效"这一方向一致；而单恶意客户端、恶意占比 ≥ 30% 时检出 83–100%、误报 0.6–1.9%，也与论文同构设置下 DnC/ClippedClustering 能起作用相容。**不能直接比较**：我们报的是逐轮检出率与误报率，论文报的是最终 ASR；我们 0.5B、10 客户端、20 轮、每轮 5 步，论文 7B 级、15 客户端、25 轮、每轮 50 步、种子卡片未给。特别地，论文每轮全参与，部分参与是论文未覆盖的条件（卡片第 9 节分析明确指出论文没有涉及部分参与与跨轮调度），所以 E5 的"每轮只抽 5 个客户端"盲区是论文回答不了、我们独有的观察，不能拿它说论文错。作为 setting_reference：论文的 15 客户端、全参与、恶意 [0, 5]、25 轮 / 每轮 50 步 / 学习率 0.001 / AdamW / 批大小 4（Section IV-A、Section IV-B）是我们要对齐的规模参照；论文"1 个和 5 个恶意客户端都让 ASR 显著上升"（Section V-B）提示我们应把"恶意客户端数量"当作显式自变量，而不只是投毒比例。

**E6（已发表防御可用性批量）：method_source，效果层面不适用。** 论文评估的四种 RAS 中，我们覆盖了坐标中位数（即 Median），并跑了截尾均值（相当于 DnC 的第二步，但没有 DnC 的维度筛选）；GeoMed 与 ClippedClustering 不在 E6 列表里；PPSA 也没有——E6 里的"安全样本混入与 BEA"是在训练过程中掺安全样本，与 PPSA 在 PEFT 结束之后用 CAI-Conversation-Harmless 再对齐（Section III-C2、Section V-D）不是同一机制。由于 E6 明确"不评价防御效果"，它既不能印证也不能反驳 Table II 的 ASR ≤ 2% / > 80%。E6 的一次读数反而提示了移植风险：CRFL 按原文范数阈值会把全局 LoRA 压到 0.10 倍、LoMar 按原文阈值每轮排除 3/5 客户端（4B、5 客户端、4 轮），说明照搬论文阈值在小规模 LoRA 上会过度动作；我们对 DnC 与 ClippedClustering 也应先做同样的可用性检查再谈效果。另外卡片第 5 节第 2 点与第 10 节指出，论文没有说明如何把 LoRA 的 A/B 矩阵、(IA)3 的缩放向量与 LayerNorm 的缩放参数展平到同一坐标空间，而这正是 E8 要固定的插件契约内容。

**E7（无攻击对照）：background，不构成对论文结论的检验。** 论文的四种 RAS 里只有 Median 落在 E6，E7 测的 Krum、LoMar、FLDetector、MUD-HoG、梯度谱熵、ONION、激活聚类、ProtegoFed、MCD、Safe-FedLLM 都不是论文评估的防御；而且论文没有报告任何无攻击时的动作率或误报数字（卡片第 6 节写"论文也没有给出'检测到 PaaA 之后'的任何判定阈值或检测指标"）。所以 E7 不能印证或反驳 Table II。但它在方法论上直接指向论文的一个空缺：论文说 RASs 的作用是"识别并排除恶意更新"（Section III-C1、Figure 2 第④部分），却没有给良性-only 下的排除比例；我们 E7 观察到无攻击时 Krum 仍排除 80% 的客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20% 等，说明这个对照不可省。要对论文做直接对照，应在 E7 的协议里补上 Median、GeoMed、DnC、ClippedClustering 四个算子。

**E8（宿主适配）：setting_reference。** 论文的防御全部在服务器侧：RASs 在聚合阶段（Figure 2 第④部分），PPSA 在聚合之后（Figure 2 第⑤部分），客户端侧不需要任何防御干预。卡片第 10 节据此要求库提供三类服务器钩子——聚合前的筛选或剔除、可整体替换的聚合算子（Median 与 GeoMed 不是加权平均，必须允许插件接管聚合逻辑）、聚合后的模型修复（PPSA 需要一份声明式的对齐语料资源与若干额外训练轮次，并且要允许它以"对齐客户端参与联邦轮次"的形式实现）——并明确客户端侧在本论文中不需要防御接口。E8 的结果（18 个服务器侧插件原生挂载、9 个客户端侧插件需应用配合、ProtegoFed 需一层握手）说明服务器侧路线可行，但"整体替换聚合算子"与"聚合后追加对齐轮次"这两种形态还没有在 E8 中验证；E8 的规模也只有 4–5 个客户端、2 轮。

**E9（Safe-FedLLM 式 LoRA 权重探针）：background。** 论文没有这种权重探针，也没有讨论检测器跨运行或跨种子的稳定性。它关于"检测必须看状态"的说法（卡片第 5 节第 9 点：恶意客户端停止参与后 ASR 无显著变化）与 E9 的动机相关，但我们观察到的"换一次运行后探针失效（恶意客户端概率 0.00）"是论文完全没有涉及的问题，不能印证或反驳论文任何数值。反过来它也说明：论文只报 ASR 的评估口径无法暴露检测器的这种不稳定性。

**E10（调研与知识库）：background。** 在知识库视角下，这篇论文贡献一个威胁技术（客户端本地有害指令数据投毒，用良性任务表现不变来隐蔽，Section III-B）和两族防御算子（服务器端剔除/鲁棒聚合、服务器端模型修复）。按卡片的算子标签（interventions 为 exclude_client 与 repair_model），它应当能落进我们 481 个步骤到算子的映射；卡片第 10 节指出的"把异构 PEFT 张量展平到统一坐标空间应写进插件契约"也是一个基础实现需求，与 E8 直接相关。E10 本身是元层面工作，这篇论文不构成对它的验证。

## 3. 我们要与它可比还差什么

1. **模型规模**：论文是 LLaMA-2-7B-Chat、Phi-3.5-Mini-Instruct、LLaMA-3.2-3B-Instruct、Qwen2.5-7B-Instruct 四个 7B 级及以下模型、统一 4-bit 量化（Section IV-A）。我们最大只到 4B（E6/E7），主力是 0.5B/0.8B，且自述"7B 及以上模型的完整训练"没做过。要可比至少需要一次 Qwen2.5-7B-Instruct（与论文同名同规模）的完整 FedPEFT 训练。
2. **轮数与本地步数**：论文默认 25 轮、每轮 50 个本地步（Section IV-B），PPSA 14 轮（Section V-D）。我们是 20 轮 × 每轮 5–6 步（E3/E4/E5），E6/E7 只有 4 轮 × 6 步。要把本地步数提到 50 量级、轮数提到 25 量级，否则"轮 20 的 ASR"无从对齐。
3. **客户端数量与参与率**：论文 15 客户端、每轮全参与、恶意 3/15（Section V-C）或 [0, 5]（Section IV-A）；我们 10 客户端且 E5 每轮只抽 5 个。部分参与是论文未覆盖的条件，要做数值对照必须先补全参与的 15 客户端配置，并把恶意客户端比例对到 3/15（20%）以及 1 个、5 个两档。
4. **攻击类型与投毒配置**：论文是"恶意客户端用 BeaverTails 的 `is_safe=False` 有害问答按 Eq. (4) 模板做本地指令微调"，没有触发器，不是后门（Section III-A、Section IV-A）；我们 E3/E4 用 MaliciousGen，E6 场景 B 是带触发词与固定目标输出的后门，与论文不是同一攻击类型。另外论文**每客户端的中毒样本数与中毒比例卡片未给**，而我们对中毒比例很敏感（E4：100% 时 18/18 轮、30% 时最好 6/18、10% 时 1–2/18），这一点是对齐时最需要先确认的未知量：要么按论文模板重建"恶意客户端完全用自己的有害数据"，要么明确标注我们只能按自定的 100%/30%/10% 与之并置。
5. **评测指标**：论文用 ASR（AdvBench 与 JailbreakBench，由 OpenAI chat completion API 判定）加 MedQA/MetaMathQA 准确率（Section IV-C）。我们目前只有 AdvBench 无害率（E4）和行为探针分数（E5），既没有 ASR，也没有下游任务准确率。要对齐需要固定一套裁判实现（卡片第 9 节提醒论文自述该 API 只是近似评估），并像论文那样同时记录 ASR 与效用两条曲线（卡片第 10 节）。注意我们的"无害率 81%→49–63%"与论文的 ASR 方向相反、口径不同，不能直接换算。
6. **数据集**：论文用 MedQA 与 MetaMathQA 做下游任务、BeaverTails 不安全子集做中毒、CAI-Conversation-Harmless 做对齐、AdvBench 与 JailbreakBench 做安全评测（Section IV-A、Section IV-C）。我们是 Dolly（良性）+ MaliciousGen（恶意）+ AdvBench（评估）。至少要补 BeaverTails 不安全子集与两个下游任务测试集；若要动 PPSA，还需要 CAI-Conversation-Harmless。
7. **异构的定义**：论文默认 IID，异构是域级的 6 MedQA + 6 MetaMathQA（Section V-C、Table II）；我们是 Dolly 类别上的 Dirichlet 0.5/1.0/0.1。要检验"异构使 DnC/ClippedClustering 失效（ASR > 80%）"必须补域级划分；已有的"Dirichlet 对更新相似度几乎无影响"不能外推到域级异构。
8. **防御基线**：论文的对照是 Mean、Median、GeoMed、DnC、ClippedClustering（Table II）与 PPSA（Figure 5）。我们只跑过坐标中位数与截尾均值，且 E6 不评效果、E7 没有它们的无攻击动作率。要对齐需要补 GeoMed、含维度筛选的完整 DnC、ClippedClustering 以及 PPSA（服务器侧或对齐客户端侧，用 CAI-Conversation-Harmless，在联邦轮次之后追加对齐轮），并各做一次无攻击对照。
9. **种子与置信区间**：论文的种子数卡片未给；我们多数实验是单种子（E4 有 3 个种子）。在补齐多个种子之前，任何"与论文一致/矛盾"的强结论都站不住。
10. **工程条件**：论文用 4-bit 量化、Unsloth、Bitsandbytes 与 A100（Section IV-A、Section IV-B），我们是 CPU、RTX 4050 与 5090。量化与数值精度会改变 LoRA 更新的范数尺度，而我们 E3/E6 的若干特征（效果层大小、CRFL 的范数阈值）正是范数敏感的，所以做数值对照前要固定量化与精度配置。
11. **开销与自适应攻击**：论文完全不报开销，也不评估自适应攻击者（卡片第 8 节、第 9 节）。这意味着 E2 无法与它对照；而如果我们要复现 DnC/ClippedClustering/PPSA，需要自己补这些算子的额外计算与通信开销。自适应攻击与上传侧攻击（更新放大、针对防御构造更新、合谋）论文同样空白，这一点上我们不能把"论文没做"当作自己不必做的理由——两者都属于我们自述的缺口。
12. **表述口径**：卡片第 9 节分析指出论文的 RAS 结论来自"15 客户端、全参与、单域或双域、3 个恶意客户端、Phi-3.5-Mini-Instruct 加 LoRA、20 轮"这一特定配置。我们引用其结论时要把这些条件写在一起，并明确标注我们的规模小得多、不能直接比较。

```json
{
  "key": "li2024peftattack",
  "paper_scale": {
    "models": "LLaMA-2-7B-Chat、Phi-3.5-Mini-Instruct、LLaMA-3.2-3B-Instruct、Qwen2.5-7B-Instruct，均 4-bit 量化（Section IV-A）；PEFT 方法为 LoRA、(IA)3、LayerNorm（Figure 1）；可训练参数比例见 Table I（LoRA 0.53%–0.78%，(IA)3 0.007%–0.009%，LayerNorm 0.001%–0.004%），正文 Section IV-A 写 0.001%–0.59%，与 Table I 的 0.78% 不一致",
    "clients": "1 个服务器 + 15 个客户端（K = 15），每轮全参与；恶意客户端数量在 [0, 5] 之间（Section IV-A）；RAS 实验为 15 个客户端中 3 个恶意（Section V-C）；PPSA 实验为 9 个微调客户端 + 3 个恶意客户端（第 0–5 轮激活）+ 3 个对齐客户端（第 11–14 轮激活）（Section V-D、Figure 5）",
    "rounds": "默认 25 轮、每轮 50 个本地步、学习率 0.001、AdamW、批大小 4（Section IV-B）；RAS 配置卡片第 9 节的分析写为 20 轮；PPSA 实验共 14 轮，其中第 11–14 轮用于对齐（Section V-D、Figure 5）",
    "poison_setting": "恶意客户端从 BeaverTails 的 is_safe=False 子集采样有害问答，按 Section III-A 的 Eq. (4) 模板拼成 cont/inst/resp 序列后做本地指令微调，只更新 PEFT 参数、冻结基座，其余流程与诚实客户端一致（Section III-A、Section III-B）；每个恶意客户端注入的样本数或中毒比例，卡片未给（Section IV-A）",
    "seeds": "卡片未给",
    "federated": true,
    "lora": true
  },
  "headline_results": [
    "第 0 轮所有 PLM 的 ASR 都很低：正文写 ASR < 4%，Figure 4 标注的 AdvBench 第 0 轮数值为 LLaMA-2-7B-Chat 0.3%、Phi-3.5-Mini-Instruct 1.7%、LLaMA-3.2-3B-Instruct 2.0%、Qwen2.5-7B-Instruct 2.5%，JailbreakBench 分别为 1.5%、0.8%、4.2%、3.5%（卡片指出正文的 < 4% 与图中 4.2% 略有出入）；随联邦微调推进，LoRA 多数情况下第 20 轮 ASR 超过 70%，(IA)3 与 LayerNorm 一般在 40%–60%，摘要表述为 up to 80% attack success rate（Abstract、Section V-B、Figure 4）",
    "Table II（AdvBench ASR）：基座模型 MedQA 准确率 56.9%、MetaMathQA 80.0%、AdvBench ASR 1.3%、JailbreakBench ASR 1.3%；MedQA-only 同构设置 Mean 83.5%、Median 84.5%、GeoMed 83.5%、DnC 1.0%、ClippedClustering 0.0%；MetaMathQA-only 设置 Mean 49.5%、Median 40.5%、GeoMed 46.5%、DnC 85.5%、ClippedClustering 3.0%；6 MedQA 加 6 MetaMathQA 混合域设置 Mean 77.5%、Median 80.0%、GeoMed 76.0%、DnC 82.5%、ClippedClustering 81.0%，对应 JailbreakBench ASR 77.4%、81.8%、72.4%、87.7%、88.3%；结论是 Median 与 GeoMed 在任何分布下 ASR > 30.7%，DnC 与 ClippedClustering 只在 MedQA 同构下 ASR ≤ 2%、异构下 ASR > 80%（Section V-C、Table II）",
    "PPSA：3 个恶意客户端存在的最初 5 轮内 ASR 快速上升，AdvBench 达到 57%、JailbreakBench 达到 65%；恶意客户端退出后的正常微调轮次 ASR 无显著变化；第 11–14 轮对齐客户端介入后 ASR 降到 10% 以下，代价是对齐税，例如 LLaMA-3.2-3B-Instruct 在 MedQA 上准确率最多下降 3%、MetaMathQA 下降 20%（Section V-D、Figure 5）"
  ],
  "links": [
    {
      "experiment": "E1",
      "relation": "background",
      "agreement": "n/a",
      "detail": "论文没有检验库不改变训练这类命题，只把恶意客户端必须遵守标准 FedPEFT 协议、不能修改冻结基座作为威胁模型前提（Section III-B），E1 的逐位相同是我们自己的协议保真性检查，与论文结论既不印证也不冲突；规模也不同（我们 Qwen2.5-0.5B、3 轮、CPU，论文 7B 级、25 轮、A100）。"
    },
    {
      "experiment": "E2",
      "relation": "background",
      "agreement": "n/a",
      "detail": "卡片第 8 节明确写论文未报告攻击或防御的计算、通信、存储开销，只有定性陈述（Table I 的可训练参数比例 0.001%–0.78%、Section III-A 与 Section IV-B 的紧凑更新与 4-bit 量化），因此 E2 的 0.7%–2.8%、0.25%–1.8% 与 3.8/5.7/3.2 秒在论文侧没有可对齐的数字。"
    },
    {
      "experiment": "E3",
      "relation": "same_question",
      "agreement": "consistent",
      "detail": "两者都问少数恶意客户端的有害指令微调是否在 LoRA 更新上留下可分信号：论文 Table II 在同构 MedQA-only、3/15 恶意客户端下 DnC 的 AdvBench ASR 为 1.0%、ClippedClustering 为 0.0%（Section V-C），说明更新空间存在可被利用的信号，我们 E3 在 1/10 恶意、恶意数据占比 100% 下效果层大小 15/20 轮、因子层方向 17/20 轮标出恶意客户端，方向一致；但 E3 没有 ASR 终点、论文没有逐轮检出率，且我们 0.5B、20 轮、单种子、Dirichlet 0.5 对论文 7B 级、默认 IID、25 轮（RAS 配置卡片第 9 节分析为 20 轮）、种子卡片未给，数值不能直接比较；论文 Median 与 GeoMed 在所有设置下 ASR > 30.7% 也提醒我们，更新里有信号不等于鲁棒聚合能利用它。"
    },
    {
      "experiment": "E3",
      "relation": "method_source",
      "agreement": "not_comparable",
      "detail": "我们的恶意客户端是本地有害问答数据加标准 FedAvg 协议、只更新 LoRA，机制上与 PaaA 同类（Section III-B、Section III-A 的 Eq. (4)–(7)），可视为运行了同一攻击家族；但我们用 MaliciousGen 而非 BeaverTails 的 is_safe=False 子集，也没有采用论文模板，模型是 0.5B 且无 ASR 终点，因此不是忠实复现，结果不能与论文数值比较。"
    },
    {
      "experiment": "E4",
      "relation": "same_question",
      "agreement": "not_comparable",
      "detail": "论文在卡片中只有第 0 轮 ASR（< 4%，Figure 4），卡片未给 0 个恶意客户端时完整良性联邦微调的安全曲线，所以论文没有回答良性联邦指令微调本身是否削弱安全对齐；我们 E4 量到无攻击时 AdvBench 无害率从 81% 降到 49–63%（alpaca 模板、Qwen2.5-0.5B），论文未报告该现象，无法印证或反驳，且它构成论文 ASR 增益的未控制混淆；口径也不同（我们无害率、论文 OpenAI API 判定的 ASR；0.5B 对 7B 级；Dolly 对 MedQA/MetaMathQA）。"
    },
    {
      "experiment": "E4",
      "relation": "setting_reference",
      "agreement": "n/a",
      "detail": "论文默认 IID（Section IV-A），其异构设置是域级划分即 12 个良性客户端在 MedQA 与 MetaMathQA 各 6 个（Section V-C、Table II），而我们按 Dolly 类别做 Dirichlet 1.0/0.5/0.1；我们观察到 Dirichlet 对 LoRA 更新相似度几乎没影响，不能外推到论文的域级异构，要对齐异构导致 DnC/ClippedClustering 失效（ASR > 80%）的结论必须补域级划分。"
    },
    {
      "experiment": "E5",
      "relation": "same_question",
      "agreement": "consistent",
      "detail": "两者都问恶意客户端数量与投毒集中程度如何影响可检测性：论文把恶意客户端数量在 [0, 5] 之间变化（Section IV-A），RAS 实验固定 3/15（Section V-C），结论是同构 MedQA 下 DnC 与 ClippedClustering 把 ASR 压到 ≤ 2%、异构下失效到 ASR > 80%，Median 与 GeoMed 所有分布下 ASR > 30.7%；我们 E5 的盲区是分散低浓度投毒（2–3 个恶意客户端各 10% 检出 3–15%）与每轮只抽 5 个客户端（24–35%），方向与信号被稀释后防御失效一致，而单恶意客户端、占比 ≥ 30% 时检出 83–100%、误报 0.6–1.9% 亦与论文同构设置下更新级防御可用的结论相容；但我们报逐轮检出率与误报率、论文报最终 ASR，且我们 0.5B、10 客户端、20 轮、每轮 5 步对论文 7B 级、15 客户端、25 轮、每轮 50 步、种子卡片未给，数值不能直接比较；部分参与是论文未覆盖的条件（卡片第 9 节分析明确指出），该盲区是论文回答不了的。"
    },
    {
      "experiment": "E5",
      "relation": "setting_reference",
      "agreement": "n/a",
      "detail": "论文的 15 客户端、每轮全参与、恶意客户端 [0, 5]、默认 25 轮、每轮 50 个本地步、学习率 0.001、AdamW、批大小 4（Section IV-A、Section IV-B）是我们要对齐的规模参照；论文关于 1 个与 5 个恶意客户端都使 ASR 显著上升的观察（Section V-B）提示我们应把恶意客户端数量作为显式自变量，而不只扫描投毒比例。"
    },
    {
      "experiment": "E6",
      "relation": "method_source",
      "agreement": "n/a",
      "detail": "论文评估的四种 RAS 中我们覆盖坐标中位数（即 Median），并跑了截尾均值（相当于 DnC 的第二步，但没有维度筛选），GeoMed 与 ClippedClustering 不在 E6 列表里，PPSA 也没有（我们的安全样本混入与 BEA 是在训练中掺安全样本，与 PPSA 在 PEFT 结束后用 CAI-Conversation-Harmless 再对齐不同）；E6 明确不评价防御效果，因此不能印证或反驳 Table II 的 ASR ≤ 2% 与 > 80%；E6 的一次读数（CRFL 按原文范数阈值把全局 LoRA 压到 0.10 倍、LoMar 按原文阈值每轮排除 3/5 客户端）提示我们照搬论文阈值在小规模 LoRA 上会过度动作，对 DnC 与 ClippedClustering 也应先做可用性检查。"
    },
    {
      "experiment": "E7",
      "relation": "background",
      "agreement": "n/a",
      "detail": "E7 测的 Krum、LoMar、FLDetector、MUD-HoG、梯度谱熵、ONION、激活聚类、ProtegoFed、MCD、Safe-FedLLM 都不是论文评估的防御，论文的四种 RAS 里只有 Median 落在 E6，且论文没有报告任何无攻击时的动作率或误报数字（卡片第 6 节写明论文没有给出判定阈值或检测指标），所以 E7 不能印证或反驳 Table II；但它在方法论上指向论文的空缺，即论文说 RASs 会识别并排除恶意更新（Section III-C1）却没有良性-only 对照，要对论文直接对照应在 E7 协议里补 Median、GeoMed、DnC、ClippedClustering。"
    },
    {
      "experiment": "E8",
      "relation": "setting_reference",
      "agreement": "n/a",
      "detail": "论文的防御全在服务器侧：RASs 在聚合阶段（Figure 2 第④部分），PPSA 在聚合之后（Figure 2 第⑤部分），客户端侧不需要防御干预；卡片第 10 节据此要求库提供聚合前筛选或剔除、可整体替换的聚合算子（Median 与 GeoMed 不是加权平均）、聚合后模型修复（PPSA 需要声明式对齐语料与额外训练轮次，并允许以对齐客户端参与联邦轮次的形式实现）三类钩子；E8 的 18 个服务器侧插件原生挂载说明服务器侧路线可行，但整体替换聚合算子与追加对齐轮次两种形态尚未验证，且 E8 只有 4–5 个客户端、2 轮。"
    },
    {
      "experiment": "E9",
      "relation": "background",
      "agreement": "n/a",
      "detail": "论文没有 Safe-FedLLM 式权重探针，也未讨论检测器跨运行或跨种子的稳定性；它关于检测必须看状态的说法（卡片第 5 节第 9 点：恶意客户端退出后 ASR 无显著变化）与 E9 动机相关，但我们换一次运行后探针失效（恶意客户端概率 0.00）是论文未涉及的问题，不能印证或反驳论文数值，反而说明论文只报 ASR 的评估口径无法暴露检测器的不稳定性。"
    },
    {
      "experiment": "E10",
      "relation": "background",
      "agreement": "n/a",
      "detail": "在知识库视角下论文贡献一个威胁技术（客户端本地有害指令数据投毒，靠良性任务表现不变隐蔽，Section III-B）和两族防御算子（服务器端剔除或鲁棒聚合、服务器端模型修复，卡片 interventions 为 exclude_client 与 repair_model），应能落进我们 481 个步骤到算子的映射；卡片第 10 节指出的把异构 PEFT 张量展平到统一坐标空间应写进插件契约这一基础需求与 E8 直接相关；E10 是元层面工作，论文不构成对它的验证。"
    }
  ],
  "missing_for_comparability": [
    "模型规模：论文四个 7B 级及以下模型、统一 4-bit 量化（Section IV-A），我们最大 4B、主力 0.5B/0.8B，缺 7B 及以上完整训练，至少需要一次 Qwen2.5-7B-Instruct 的完整 FedPEFT",
    "轮数与本地步数：论文默认 25 轮、每轮 50 步（Section IV-B），RAS 配置卡片第 9 节分析为 20 轮，PPSA 14 轮（Section V-D）；我们 20 轮、每轮 5–6 步（E3/E4/E5）或 4 轮、每轮 6 步（E6/E7），本地步数与轮数都要提升",
    "客户端数量与参与率：论文 15 客户端、每轮全参与、恶意 3/15（Section V-C）或 [0, 5]（Section IV-A）；我们 10 客户端且 E5 每轮只抽 5 个，需要补全参与配置并把恶意比例对到 20% 及 1 个、5 个两档",
    "攻击类型与投毒配置：论文是 BeaverTails is_safe=False 有害问答按 Eq. (4) 模板做本地指令微调、无触发器非后门（Section III-A、Section IV-A），我们用 MaliciousGen 且 E6 场景 B 是带触发词后门；论文每个恶意客户端的中毒样本数与中毒比例卡片未给（Section IV-A），这是对齐前必须先确认的未知量",
    "评测指标：论文用 ASR（AdvBench、JailbreakBench，OpenAI chat completion API 判定）加 MedQA/MetaMathQA 准确率（Section IV-C），我们只有 AdvBench 无害率（E4）与行为探针分数（E5），缺 ASR 与下游准确率，且我们的无害率与论文 ASR 口径不同不能换算",
    "数据集：论文用 MedQA、MetaMathQA、BeaverTails 不安全子集、CAI-Conversation-Harmless、AdvBench、JailbreakBench（Section IV-A、Section IV-C），我们用 Dolly 加 MaliciousGen 加 AdvBench，需要补 BeaverTails 与两个下游任务测试集，做 PPSA 还需 CAI-Conversation-Harmless",
    "异构设置：论文默认 IID、异构是域级 6 MedQA 加 6 MetaMathQA（Section V-C、Table II），我们是 Dolly 类别上的 Dirichlet，需要补域级划分才能检验异构下 DnC/ClippedClustering 失效的结论",
    "防御基线：论文对照为 Mean、Median、GeoMed、DnC、ClippedClustering（Table II）与 PPSA（Figure 5），我们只有坐标中位数与截尾均值且未评效果，需要补 GeoMed、含维度筛选的完整 DnC、ClippedClustering 与 PPSA，并各做一次无攻击动作率对照",
    "种子与置信区间：论文种子数卡片未给，我们多为单种子（E4 为 3 个），需要多种子与置信区间才能下一致或矛盾的结论",
    "工程与数值条件：论文 4-bit 量化、Unsloth、Bitsandbytes、A100（Section IV-A、Section IV-B），我们 CPU 加 RTX 4050/5090；量化与精度会改变 LoRA 更新范数尺度，影响 E3 效果层大小与 CRFL 范数阈值这类范数敏感特征，对照前需固定配置",
    "开销与自适应攻击：论文不报开销（卡片第 8 节）也不评估自适应攻击者（卡片第 9 节），E2 无可对照数字，且复现 DnC/ClippedClustering/PPSA 时需要我们自己补额外计算与通信开销",
    "评估口径与结论条件：卡片第 9 节分析指出论文 RAS 结论受 15 客户端、全参与、单域或双域、3 个恶意客户端、Phi-3.5-Mini-Instruct 加 LoRA、20 轮限制，引用时需同时标注这些条件并声明我们的规模小得多、不能直接比较"
  ],
  "metrics_paper_uses": [
    "攻击成功率 ASR（AdvBench 上有害指令的输出被 OpenAI chat completion API 判为有害的比例，Section IV-C）",
    "攻击成功率 ASR（JailbreakBench，同一判定方式，Section IV-C）",
    "下游任务准确率（MedQA 测试集，Section IV-C、Table II）",
    "下游任务准确率（MetaMathQA 测试集，Section IV-C、Table II）",
    "可训练参数比例 # TPs / # APs（Table I，作为 PEFT 规模指标）"
  ],
  "relevance": "high"
}
```
