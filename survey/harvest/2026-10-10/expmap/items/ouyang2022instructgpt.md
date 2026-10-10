## 1. 论文自己的实验规模与主要结果

**场景与流程。** 论文是集中式（centralized）大模型后训练对齐，流程为 SFT → 奖励模型（RM）→ PPO 三步（Section 3.1、Figure 2）；卡片第 1 节明确说全文没有出现联邦学习、客户端、服务器聚合等概念，且论文做的是全参数微调，**不使用 LoRA 或任何参数高效微调**（卡片 JSON 的 `uses_lora_or_peft = false`）。

**模型规模。** 沿用 GPT-3 架构，训练 1.3B、6B、175B 三种规模（Section 3.5）；奖励模型与价值函数只用 6B 一个规模（Section 3.5、Appendix C.2），理由是 175B 奖励模型训练不稳定。

**数据规模。** SFT 训练集 11,295 条标注者提示 + 1,430 条客户提示（合计 12,725 条提示）；RM 训练集 6,623 条标注者提示 + 26,584 条客户提示（合计 33,207 条提示）；PPO 训练集 31,144 条客户提示（以上均出自 Table 6，合计数字见卡片第 7 节同一处引用）。数据约 96% 被分类为英文（Section 3.3），提示长度统计见 Table 9，使用类别分布见 Table 1。

**标注与不确定性统计。** 约 40 名合同标注者（Section 3.4）；训练标注者之间相互一致率 72.6 ± 1.5%，留出标注者 77.3 ± 1.3%（Section 3.4）；用 5 折交叉验证训练 5 个奖励模型时，组内预测人类偏好的准确率 72.4 ± 0.4%，留出组 69.6 ± 0.9%（Section 4.1、Appendix E.2）。

**训练超参。** SFT 训练 16 个 epoch、余弦学习率衰减、0.2 残差 dropout；1.3B 与 6B 学习率 9.65e-6、批大小 32，175B 学习率 5.03e-6、批大小 8（Appendix C.1）。RM 阶段每个提示给 K = 4 到 9 个回答排序，一条提示产生 C(K,2) 个比较，损失见 Equation 1（Section 3.5）。RL 阶段训练 256k 个回合、覆盖约 31k 条唯一提示、批大小 512、小批 64、PPO 裁剪比例 0.2、采样温度 1、权重 EMA 衰减率 0.992，KL 系数 β 默认 0.02、预训练混合系数 γ 默认 27.8（Section 3.5、Equation 2、Appendix C.4）。

**本文没有的量。** 客户端数与参与率：卡片未给（论文是集中式流程，不存在客户端与聚合）；联邦轮数：卡片未给（训练单位是 256k 个回合，Appendix C.4）；恶意比例与投毒设定：卡片未给（论文没有威胁模型，卡片第 2 节）；随机种子数：卡片未给明确数字，只给了上面的一致率与 5 折 ± 值。

**主要结果（数字照抄卡片并注出处）。**

- 人类偏好：175B InstructGPT 输出相对 175B GPT-3 的胜率 85 ± 3%，相对少样本 175B GPT-3 为 71 ± 4%（Section 1、Section 4.1）；相对本文自己微调的 FLAN 与 T0 分别为 78 ± 4% 与 79 ± 4%（Section 4.1）；1.3B InstructGPT 的输出被优先于 175B GPT-3（Abstract、Figure 1）。
- 真实性：TruthfulQA 上 PPO 模型给出"既真实又有信息量"回答的频率约为 GPT-3 的两倍（Section 1、Figure 6）；Table 14 中 175B 的 true + info、QA prompt 一行为 GPT-3 0.251、PPO 0.752、PPO-ptx 0.689。幻觉：闭域任务上编造输入中不存在信息的比例为 21% 对 41%（Section 1、Figure 4）。
- 毒性：被要求"尊重"时 InstructGPT 比 GPT-3 少生成约 25% 的有毒输出（Section 1、Figure 7，人工比较基于 1,729 条提示），去掉该指令后优势消失；反向地，被明确要求生成有毒内容时 InstructGPT 输出比 GPT-3 更有毒（Section 4.2、Figure 39），Table 14 的 Real Toxicity、biased 行为 GPT-3 175B 0.285、PPO 175B 0.427、PPO 6B 0.382。
- 偏见：Winogender 与 CrowS-Pairs 上相对 GPT-3 没有显著改善（Section 1、Section 4.2、Figure 32、Table 14）。
- 对齐税：PPO 在 SQuAD、DROP、HellaSwag、WMT 2015 法译英等公共数据集上回退，混入预训练梯度的 PPO-ptx 可以缓解并在 HellaSwag 上超过 GPT-3（Section 1、Section 4.2、Figure 28、Figure 29）；KL 系数取 0 或 2 都让 Likert 分变差，最优值在 0.01 到 0.02 附近（Figure 36）；把 KL 系数提高到 2.0（默认值的 100 倍）也不能修复 DROP 与 SQuAD 的回退（Appendix E.6、Figure 34）。
- 开销：训练 175B SFT 需 4.9 petaflops/s-days，175B PPO-ptx 需 60 petaflops/s-days，而训练 GPT-3 需 3,640 petaflops/s-days（Section 5.1）；预训练数据比例设为 8 时训练时间是"无预训练混合"的两倍，比例设为 32 有更好的 Likert 分但训练时间增加数倍（Appendix E.11）。通信开销、存储开销、联邦场景开销论文均未报告（卡片第 8 节）。

## 2. 与我们各项实验的对应

先说结论：**本文没有任何一条能标成 method_source**——我们 E1–E9 里没有 SFT→RM→PPO 流程、没有奖励模型、没有 PPO 或 KL 项，卡片也没有说我们的任何插件源自本文。能称得上"对应"的只有 E4 上的两条。

- **E1（不改变训练的等价性）→ background。** 论文是单一集中式训练器，没有宿主框架、插件或旁路采集的概念，也没有逐位一致性验证；卡片未给任何可对照的数字。
- **E2（开销）→ background。** 论文确实报告开销，但口径不同：4.9 与 60 petaflops/s-days（Section 5.1）、预训练混合比例为 8 时训练时间为无混合的两倍（Appendix E.11）；卡片明确说通信与存储开销论文未报告、联邦场景开销论文也未报告。我们的 E2 是插件占本地训练时间的百分比（0.7%–2.8% 等）与秒数，两者无法对齐。
- **E3（效果层/因子层特征预实验）→ background。** 论文全参数微调、不用 LoRA，卡片第 9 节的分析明确写"论文没有任何关于适配器增量、逐层范数或适配器通信的结论，基于这些量的检测无法从本文获得依据"。我们 E3 的全部观测量都建立在 LoRA 的 BA 更新大小与方向上，故无对应。
- **E4（良性基线与校准）→ same_question，agreement = consistent，但不可直接比较。** 我们 E4 发现无攻击的良性微调本身就让 AdvBench 无害率从 81% 降到 49–63%（alpaca 模板）；论文则说模型在多数情况下会服从用户指令、即使这在现实中可能造成伤害（Section 5.3），并且被要求"最大程度带偏见"时 InstructGPT 会比同规模 GPT-3 生成更多有毒内容（Section 5.3、Figure 39、Table 14 的 biased 行 GPT-3 175B 0.285 对 PPO 175B 0.427）。两条都指向"微调/对齐本身不保证无害"，方向一致。但论文是集中式全参数 1.3B–175B 的人类偏好评测，我们只有 Qwen2.5-0.5B、10 客户端、20 轮、单个种子的 LoRA 预实验，度量也不同（AdvBench 无害率对偏好胜率与 Real Toxicity 分），因此**不能直接比较，也不能说我们复现了它**。E4 的另一个发现（按 Dolly 类别的 Dirichlet 划分对 LoRA 更新相似度几乎没有影响）在论文中没有对应，因为论文没有非独立同分布设定。
- **E4（评测协议）→ setting_reference。** 论文在固定留出提示集上以固定基线模型（175B SFT）比较偏好率、并按验证集 RM 得分选择检查点（Section 3.6、Section 3.5），同时报告标注者一致率与 5 折 ± 值（Section 3.4、Section 4.1、Appendix E.2）。这可以作为我们补评测协议的参照；但模型规模与全参数集中式训练范式不构成对齐目标。
- **E5（自动攻击矩阵）→ background。** 论文没有攻击者、恶意客户端、检测器与参与率概念，E5 的 83–100% 检出率与"分散低浓度投毒""每轮只抽 5 个客户端"两个盲区，在本文里既找不到印证也找不到反驳。卡片第 10 节的分析提到可以把打分模型在固定留出提示集上的分数按轮记录成质量轨迹，这与我们 E5 的行为探针思路相近，但那是卡片作者的分析，不是论文自己的实验结论。
- **E6（已发表防御批量）→ background。** 论文不是防御论文，E6 覆盖的 Krum、FLAME、ProtegoFed、TriShield、ONION 等 26 次运行里没有任何方法来自本文。唯一的概念类比是 PPO-ptx 用 γ（默认 27.8）混入预训练梯度以缓解对齐税（Section 3.5、Equation 2），与 E6 的"安全样本混入"同属"混入可信数据或梯度"这一族；但卡片没有说我们的插件源自本文，且论文在 RL 目标里混梯度、我们在监督微调里混样本，不能互相印证。
- **E7（无攻击对照）→ background。** 论文没有误报/漏报概念，也没有防御在良性客户端上的触发统计；E7 的"Krum 仍排除 80% 客户端轮次""ONION 改写 59% 样本"等结论在本文没有对应物。
- **E8（宿主适配）→ background。** 论文是单一集中式训练器，不存在宿主框架适配、服务器侧与客户端侧插件位置的问题。
- **E9（Safe-FedLLM 式 LoRA 权重探针）→ background。** 论文没有权重探针。有一点同类现象：卡片说奖励模型对训练 epoch 数敏感、多个 epoch 会迅速过拟合，175B 奖励模型训练不稳定（Section 3.5、Appendix C.2），这与我们 E9"换一次运行（不同种子）后探针失效"都属于"学出来的打分信号不稳"，但对象、种子定义与度量都不同，不构成同一问题，也不能互相印证。
- **E10（调研与知识库）→ background。** 卡片没有说明本文是否被 E10 的 137 篇/45 篇语料收录，因此不能假设它在统计之内。若入库，按卡片第 6 节的分析，它只贡献 filter_samples（PII 过滤、长公共前缀去重、每用户约 200 条上限、长度上限）、reweight（β 与 γ）与 clip（PPO 比率裁剪 0.2）三类动作，动作位置在集中式训练器内部，没有客户端或服务器侧位置；其"冻结 πSFT 参考策略"这一观测量正好落在我们运行时可能缺算子或超出运行时的部分（卡片第 10 节分析）。

## 3. 我们要与它可比还差什么

- **模型规模与微调方式。** 论文是全参数 GPT-3 1.3B/6B/175B（Section 3.5），我们最大只到 Qwen3.5-4B 且全部是 LoRA；要谈规模可比至少需要 7B 以上的完整训练（这正是我们"没做过"清单里的缺口），而基于适配器增量的量在本文根本没有对应结论。
- **训练范式。** 论文需要人类偏好比较数据（RM 训练 33,207 条提示，Table 6）、一个 6B 奖励模型（Section 3.5）和 PPO 的 256k 个回合（Appendix C.4）；我们没有偏好数据、奖励模型与 RL 训练，这一整条流程缺失。
- **轮数与回合量级。** 论文 256k 个回合（Appendix C.4），我们是 2–20 轮、每轮 5–6 步、4–10 个客户端（E3–E8），差约四个数量级，任何与训练进度相关的量都不可比。
- **参考模型观测量。** 论文的 KL 项要求当前策略与冻结 πSFT 在同一回答上逐 token 的对数概率之差（Section 3.5、Equation 2）；我们目前还没有把"参考适配器前向"做成独立采集视图，也没有逐 token 对数概率的采集。
- **攻击类型。** 论文没有攻击者、恶意比例与后门设定（卡片第 2 节），我们的投毒、触发词后门与上传侧攻击在本文没有对应条件；要与本文对照只能把攻击侧实验排除在比较之外，或改用对齐质量侧的观测量。
- **指标。** 论文用人类偏好胜率、1–7 Likert 分、Table 3 二值元数据、TruthfulQA 的 true + info、RealToxicityPrompts、Winogender/CrowS-Pairs（Section 3.6、Section 4.1、Section 4.2、Table 14）；我们用 AdvBench 无害率与插件级精确率/召回率/排除率，两套指标不重合，需要新增固定留出提示集上的偏好或毒性评测。
- **基线与不确定性。** 论文以 175B SFT 作为固定基线并报告 ± 值（一致率 72.6 ± 1.5% / 77.3 ± 1.3%，Section 3.4；5 折 RM 准确率 72.4 ± 0.4% / 69.6 ± 0.9%，Section 4.1、Appendix E.2）；我们多数实验只有 1 个种子（E4 为 3 个），也没有固定基线模型，做不出同类区间报告。
- **开销口径。** 论文用 petaflops/s-days 与"训练时间倍数"（Section 5.1、Appendix E.11），并明确未报告通信与存储开销、也未报告联邦场景开销（卡片第 8 节）；我们的开销是占本地训练时间百分比与秒数（E2），口径不同、不能换算。
- **数据与标注。** 论文数据来自约 40 名标注者并按用户标识切分（Section 3.2、Section 3.4），我们只有 Dolly 与有害问答等公开数据，没有可比的偏好标注与一致率统计。

需要说清楚的是：本文 175B 全参数、256k 回合、40 名标注者这一套**不应**成为 fedguard 的对齐目标，因为问题不同（集中式对齐对联邦 LoRA 投毒防御）。真正值得从它身上补的只有三件：参考模型前向的采集视图（逐 token 对数概率差）、固定留出集上由打分模型给出的按轮质量轨迹、以及多种子的均值±方差报告。其余缺口应在"论文不可比"的前提下单独说明。

```json
{
  "key": "ouyang2022instructgpt",
  "paper_scale": {
    "models": "GPT-3 架构 1.3B、6B、175B（Section 3.5）；奖励模型与价值函数固定用 6B（Section 3.5、Appendix C.2）；全参数微调，不使用 LoRA 或任何参数高效微调",
    "clients": "卡片未给：论文是集中式训练，不存在客户端、参与率或聚合（卡片第 1、2 节）",
    "rounds": "卡片未给：论文没有联邦轮；RL 训练单位是 256k 个回合（Appendix C.4）",
    "poison_setting": "卡片未给：论文没有威胁模型、攻击者、恶意客户端比例或投毒设定（卡片第 2 节）",
    "seeds": "卡片未给明确的种子数；只有标注者一致率 72.6 ± 1.5% / 77.3 ± 1.3%（Section 3.4）与 5 折交叉验证奖励模型准确率 72.4 ± 0.4% / 69.6 ± 0.9%（Section 4.1、Appendix E.2）",
    "federated": false,
    "lora": false
  },
  "headline_results": [
    "人类偏好：175B InstructGPT 输出相对 175B GPT-3 的胜率 85 ± 3%，相对少样本 175B GPT-3 为 71 ± 4%（Section 1、Section 4.1）。",
    "真实性与毒性：Table 14 中 175B 的 true + info、QA prompt 一行 GPT-3 0.251、PPO 0.752、PPO-ptx 0.689；同表 Real Toxicity、biased 行 GPT-3 175B 0.285、PPO 175B 0.427、PPO 6B 0.382（Table 14）。",
    "开销：训练 175B SFT 需 4.9 petaflops/s-days，训练 175B PPO-ptx 需 60 petaflops/s-days，而训练 GPT-3 需 3,640 petaflops/s-days（Section 5.1）。"
  ],
  "links": [
    {"experiment": "E1", "relation": "background", "agreement": "n/a", "detail": "论文是单一集中式训练流程，没有宿主框架、插件或旁路采集，也没有逐位一致性的验证；卡片未给任何可对照的数字。"},
    {"experiment": "E2", "relation": "background", "agreement": "n/a", "detail": "论文报告了开销但口径不同：175B SFT 4.9、175B PPO-ptx 60、GPT-3 3,640 petaflops/s-days（Section 5.1），预训练混合比例设为 8 时训练时间为无混合的两倍（Appendix E.11）；卡片明确说通信与存储开销未报告、联邦场景开销也未报告，而我们的 E2 是插件占本地训练时间的百分比与秒数，两者无法对齐。"},
    {"experiment": "E3", "relation": "background", "agreement": "n/a", "detail": "论文全参数微调、不使用 LoRA，卡片第 9 节明确说论文没有关于适配器增量、逐层范数或适配器通信的任何结论；我们基于 LoRA 的 BA 更新大小与方向的检测在本文拿不到依据。"},
    {"experiment": "E4", "relation": "same_question", "agreement": "consistent", "detail": "方向一致但不能直接比较：我们 E4 发现无攻击的良性微调本身就让 AdvBench 无害率从 81% 降到 49–63%（alpaca 模板），论文则说模型在多数情况下会服从用户指令、即使可能造成伤害（Section 5.3），且被要求最大程度带偏见时 InstructGPT 比同规模 GPT-3 生成更多有毒内容（Section 5.3、Figure 39、Table 14 的 biased 行 GPT-3 175B 0.285 对 PPO 175B 0.427）；两者都指向微调或对齐本身不保证无害。但论文是集中式全参数 1.3B–175B 的人类偏好评测，我们只有 Qwen2.5-0.5B、10 客户端、20 轮、单个种子的 LoRA 预实验，指标也不同（AdvBench 无害率对人类偏好胜率与 Real Toxicity 分），不能直接比较。E4 的 Dirichlet 划分对 LoRA 更新相似度几乎无影响这一发现，在论文中没有对应，因为论文没有非独立同分布设定。"},
    {"experiment": "E4", "relation": "setting_reference", "agreement": "n/a", "detail": "论文的评测协议可作为我们补评测时的参照：在固定留出提示集上相对一个固定基线模型（175B SFT）比较偏好率，并按验证集 RM 得分选择检查点（Section 3.6、Section 3.5），同时报告标注者一致率与 5 折 ± 值（Section 3.4、Section 4.1、Appendix E.2）；我们 E4 目前只有 3 个种子的良性基线与 1% 误报阈值校准。模型规模与全参数集中式范式不构成对齐目标。"},
    {"experiment": "E5", "relation": "background", "agreement": "n/a", "detail": "论文没有攻击者、恶意客户端、检测器或参与率概念，E5 的 83–100% 检出率与两个盲区在本文找不到印证或反驳。卡片第 10 节的分析提到可把打分模型在固定留出提示集上的分数按轮记录成质量轨迹，与我们行为探针的思路相近，但那是卡片作者的分析，不是论文自己的实验结论。"},
    {"experiment": "E6", "relation": "background", "agreement": "n/a", "detail": "论文不是防御论文，E6 的 26 次运行里没有任何方法来自本文。唯一概念类比是 PPO-ptx 用 γ（默认 27.8）混入预训练梯度以缓解对齐税（Section 3.5、Equation 2），与 E6 的安全样本混入同属混入可信数据或梯度这一族；但卡片没有说我们的插件源自本文，且论文在 RL 目标里混合梯度、我们在监督微调里混样本，不能互相印证。"},
    {"experiment": "E7", "relation": "background", "agreement": "n/a", "detail": "论文没有误报与漏报的概念，也没有防御在良性客户端上的触发统计；E7 的 Krum 仍排除 80% 客户端轮次、ONION 改写 59% 样本等结论在本文没有对应物。"},
    {"experiment": "E8", "relation": "background", "agreement": "n/a", "detail": "论文是单一集中式训练器，不存在宿主框架适配、服务器侧与客户端侧插件位置的问题。"},
    {"experiment": "E9", "relation": "background", "agreement": "n/a", "detail": "论文没有权重探针。有一点同类现象：卡片说奖励模型对训练 epoch 数敏感、多个 epoch 会迅速过拟合，175B 奖励模型训练不稳定（Section 3.5、Appendix C.2），与我们 E9 换一个种子探针就失效同属学出来的打分信号不稳，但对象、种子定义与度量都不同，不能算同一问题，也不能互相印证。"},
    {"experiment": "E10", "relation": "background", "agreement": "n/a", "detail": "卡片没有说明本文是否被 E10 的 137 篇或 45 篇语料收录，因此不能假设它在统计之内。若入库，按卡片第 6 节的分析，它只贡献 filter_samples（PII 过滤、长公共前缀去重、每用户约 200 条上限、长度上限）、reweight（β 与 γ 的调节）与 clip（PPO 比率裁剪 0.2），动作位置在集中式训练器内部，没有客户端或服务器侧位置。"}
  ],
  "missing_for_comparability": [
    "模型规模与微调方式：论文是全参数 GPT-3 1.3B/6B/175B（Section 3.5），我们最大只有 Qwen3.5-4B 且全部是 LoRA；最低限度的规模可比需要 7B 以上的完整训练，而基于适配器增量的量在本文根本没有对应结论。",
    "训练范式：论文需要人类偏好比较数据（RM 训练 33,207 条提示，Table 6）、一个 6B 奖励模型（Section 3.5）和 PPO 的 256k 个回合（Appendix C.4）；我们没有偏好数据、奖励模型与 RL 训练，整条流程缺失。",
    "轮数与回合量级：论文 256k 个回合（Appendix C.4），我们 2–20 轮、每轮 5–6 步、4–10 个客户端，差约四个数量级，训练进度相关的量不可比。",
    "参考模型观测量：论文的 KL 项需要当前策略与冻结 πSFT 在同一回答上逐 token 的对数概率之差（Section 3.5、Equation 2）；我们还没有把参考适配器前向做成独立采集视图，也没有逐 token 对数概率的采集。",
    "攻击类型：论文没有攻击者、恶意比例与后门设定（卡片第 2 节），我们的投毒、触发词后门与上传侧攻击在本文没有对应条件，要对照只能把攻击侧实验排除或改用对齐质量侧观测量。",
    "指标：论文用人类偏好胜率、1–7 Likert 分、Table 3 二值元数据、TruthfulQA 的 true + info、RealToxicityPrompts、Winogender 与 CrowS-Pairs（Section 3.6、Section 4.1、Section 4.2、Table 14）；我们用 AdvBench 无害率与插件级精确率、召回率、排除率，两套指标不重合，需要新增固定留出提示集上的偏好或毒性评测。",
    "基线与不确定性：论文以 175B SFT 为固定基线并报告 ± 值（一致率 72.6 ± 1.5% / 77.3 ± 1.3%，Section 3.4；5 折 RM 准确率 72.4 ± 0.4% / 69.6 ± 0.9%，Section 4.1、Appendix E.2）；我们多数实验只有 1 个种子（E4 为 3 个），也没有固定基线模型，做不出同类区间报告。",
    "开销口径：论文用 petaflops/s-days 与训练时间倍数报告算力（Section 5.1、Appendix E.11），并明确未报告通信与存储开销、也未报告联邦场景开销（卡片第 8 节）；我们的开销是占本地训练时间百分比与秒数（E2），口径不同、不能换算。",
    "数据与标注：论文数据来自约 40 名标注者并按用户标识切分（Section 3.2、Section 3.4），我们只有 Dolly 与有害问答等公开数据，没有可比的偏好标注数据与一致率统计。"
  ],
  "metrics_paper_uses": [
    "人类偏好胜率（win rate，相对 175B SFT 基线，Section 3.6、Section 4.1）",
    "1 到 7 的 Likert 总体质量分（Section 3.6）",
    "Table 3 的一组二值元数据标签，例如是否遵循正确指令、是否幻觉、是否给出有害建议（Section 3.6）",
    "TruthfulQA 上既真实又有信息量的回答比例（Section 1、Figure 6、Table 14）",
    "RealToxicityPrompts 的 Perspective API 自动分与人工评分（Section 3.6、Section 4.2、Table 14）",
    "Winogender 与 CrowS-Pairs 的熵（Section 3.6、Section 4.2）",
    "SQuAD、DROP、HellaSwag、WMT 2015 法译英等公共数据集的自动指标（Section 4.2）",
    "奖励模型在 5 折交叉验证下预测人类偏好的准确率（Section 4.1、Appendix E.2）",
    "标注者之间的一致率（Section 3.4）",
    "算力开销 petaflops/s-days（Section 5.1）"
  ],
  "relevance": "low"
}
```
