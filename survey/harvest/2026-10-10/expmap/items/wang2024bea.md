## 1. 论文自己的实验规模与主要结果

**设定与规模。** 论文是集中式的 LMaaS（Language-Model-as-a-Service）设定，用户通过云 API 上传微调数据集，微调与推理都由服务提供方控制（Section 3.2）；卡片明确说明全文没有出现联邦学习、客户端聚合、参与率等概念，因此**客户端数、参与率、恶意客户端比例、轮次、非独立同分布这些量在论文里不适用**（卡片第 7 节）。模型是 Llama-2-7B-Chat 与 GPT-3.5-Turbo（Section 4.1）；Llama-2 使用 2×NVIDIA A100 80GB、按 llama-recipes 官方默认设置，**具体轮数卡片未给**；GPT-3.5-Turbo 通过 OpenAI 微调 API，设为 5 个 epoch、learning rate multiplier 为 1（Section 4.1）。微调数据 D 是 "pure_bad" 的 100 条红队有害样本；服务提供方自备的安全示例 D_safe 在主实验中为 11 条、约为 D 的 10%，按 11 个有害类别各取 1 条，安全回答由 Llama-2-7b-Chat 生成，Appendix G 与 Table 8 的实验改用全部 55 条（Section 4.1、Appendix B）。秘密提示是随机生成的 150 个 token（Section 4.1、Appendix D.1）。安全评测基准共 330 条（11 类 × 每类 30 条），拆成 55 条 defense dataset 与 275 条 evaluation dataset（Appendix B）；真实场景任务用 SAMSum 对话摘要（16k 条）与 sql-create-context SQL 生成（超过 70k 条），各随机取 1000 条与 100 条有害样本混合（Section 5）。LoRA 实验见 Table 5（Section 4.3）。**种子数量卡片未给**（Figure 4 只说明每个提示长度用了 5 组随机 token）。论文没有报告任何量化开销，没有 FLOPs、显存、训练时长的测量值（卡片第 8 节），也没有评估自适应攻击者（卡片第 9 节）。

**指标。** Harmfulness Score（GPT-4 按 1 到 5 打分后取平均）、Attack Success Rate（ASR，按拒绝关键词表判断）、ARC-Challenge Acc（5-shot）、MMLU Acc（5-shot）、MT-Bench Score（GPT-3.5 作评委，满分 10）、Rouge-1 F1（真实场景微调性能，200 条测试样本）（Section 4.1、Section 5、Appendix C）。

**主要结果。** 在 Llama-2-7B-Chat 上，未受攻击的模型为 1.11 / 3.27% / 51.19% / 45.81% / 7.16（依次为 Harmfulness Score / ASR / ARC-Challenge Acc / MMLU Acc / MT-Bench Score），无防御的受攻击模型为 4.68 / 94.91% / 51.11% / 44.32% / 6.02，Baseline 防御为 2.49 / 34.91% / 50.68% / 45.30% / 6.32，本方法为 1.22 / 3.64% / 51.88% / 45.21% / 6.25（Table 1）。GPT-3.5-Turbo 上对应为未受攻击 1.25 / 5.45% / 82.49% / 67.87% / 8.56，无防御 4.86 / 75.64% / 69.77% / 66.18% / 8.38，Baseline 4.55 / 60.00% / 70.88% / 66.51% / 8.22，本方法 1.73 / 14.91% / 69.17% / 66.37% / 8.46（Table 1）；正文概括为把 Harmfulness Score 从 4.55 降到 1.73、ASR 从 60% 降到约 15%（Section 4.2），Abstract 表述为相对 Baseline 防御 ASR 下降 75%。LoRA 微调下（Llama-2），未受攻击为 3.27% / 51.19%，无防御为 95.27% / 45.82%，Baseline 为 40.36% / 48.21%，本方法为 2.91% / 46.84%（Table 5）。消融方面：安全示例选取方式 Category-wise / Random / LLM Generation 的 ASR 为 3.64% / 7.64% / 20.73%（Table 2）；推理时不拼秘密提示会让 ASR 从 3.64% 回升到 26.18%（Table 3）；秘密提示长度在 [10, 50, 100, 150, 200, 250] 上随长度增加 ASR 下降、约在 150 个 token 处收敛（Figure 4）；150 个随机 token / Llama 2 默认系统提示 / GPT-4 生成的约 150 token 提示分别为 3.64% / 7.64% / 7.27%（Table 4）。真实场景下任务性能基本不受影响而 ASR 被压低：Dialog Summary 的良性微调为 0.48 / 1.27 / 6.55% / 53.33%，受攻击无防御为 0.48 / 3.92 / 72.00% / 52.30%，本方法为 0.46 / 1.39 / 10.55% / 52.73%；SQL Generation 对应为 0.95 / 1.23 / 8.73% / 53.07%、0.95 / 3.56 / 55.64% / 51.45%、0.91 / 1.27 / 6.91% / 52.13%（按卡片顺序为 Rouge-1 F1 / Harmfulness Score / ASR / ARC-Challenge Acc，Table 6）。Identity Role Shift Attack 下 Llama-2 从无防御的 89.45% / 50.68% 降到 0.36% / 49.32%，GPT-3.5-Turbo 从 48.72% / 68.23% 降到 4.7% / 65.24%（Table 7）。Table 8 还显示良性微调本身会让 ASR 从 3.27% 上升到 6.55%（Dialog Summary）与 8.73%（SQL Generation），而本方法把它压到 0.73%。

## 2. 与我们各项实验的对应

**E1（宿主无副作用核对）——background，n/a。** 论文是集中式单进程微调，没有宿主框架、没有聚合与下发步骤（卡片第 1 节、Section 3.2），因此"挂载后最终 LoRA 逐位相同"这类宿主无副作用验证在论文中没有对应物。

**E2（开销）——background，n/a。** 论文未报告任何量化开销，没有 FLOPs、显存、训练时长或通信量（卡片第 8 节）；它只定性地说安全示例"引入一点额外的微调成本"（Limitations），以及 150 个 token 的秘密提示在推理时"可能带来额外成本"（Section 4.3）。它的成本形态是"多 11 条安全示例 + 推理前缀"，不是运行时插件，所以我们的 0.7%–2.8% 采集开销、3.8 秒 / 5.7 秒 / 3.2 秒的插件开销与它无法对照。

**E3（特征预实验 P1）——background，n/a。** 威胁模型有重叠：E3 里恶意客户端用 MaliciousGen 有害问答、占其数据 100%，正是论文 FJAttack 的形态。但论文的观测量只落在数据平面，卡片明确列出它没有使用模型更新、LoRA 增量、逐层范数、梯度、跨轮更新历史或任何其他客户端的数据（卡片第 5 节）。因此我们效果层大小 15/20、因子层方向 17/20、效果层方向 3/20 这些结果在论文里找不到可以互相印证的结论。

**E4（良性基线与校准 P2）——same_question，consistent。** 论文 Table 8 的"无意造成的安全下降"与我们的良性基线观察回答的是同一个问题：普通（良性）微调本身就会削弱安全对齐。论文里 Dialog Summary 良性微调把 ASR 从 3.27% 抬到 6.55%、SQL Generation 从 3.27% 抬到 8.73%（Table 8），并且本方法把它压到 0.73%；我们观察到无攻击微调让 AdvBench 无害率从 81% 降到 49–63%（alpaca 模板）。方向一致。但我们的模型是 Qwen2.5-0.5B、LoRA r=16、20 轮、Dolly 数据，论文是 Llama-2-7B-Chat（GPT-3.5-Turbo 为 API 微调）、全参数条件微调加任务数据，**规模与基准都差得远，数值不能直接比较**。另外论文卡片第 7 节显示它没有非独立同分布概念，所以我们"按 Dolly 类别的 Dirichlet 划分对 LoRA 更新相似度几乎没有影响"这一条在论文里无从对照；我们的 1% 误报阈值校准同样没有对应物，因为论文不做检测、不给检测分数（卡片第 1 节）。

**E5（自动攻击矩阵 P3）——setting_reference，consistent。** 论文的评测是行为层：在 330 条 Policy-Oriented Safety Evaluation Benchmarks（11 类 × 每类 30 条，Appendix B）上用拒绝关键词表算 ASR、用 GPT-4 打 Harmfulness Score（Appendix C），这正是我们行为探针应该对齐的评测参照。我们的结果与论文的前提一致：论文里有害数据微调把 ASR 从 3.27% 推到 94.91%（Table 1），我们在 37 个恶意客户端中有 33 个的累积探针分数超过全部良性客户端。但论文只在 100% 有害数据（pure_bad 100 条）下做实验，没有低浓度投毒与部分参与的格点，因此我们"2–3 个恶意客户端各 10% 时检出 3–15%、每轮只抽 5 个客户端时检出 24–35%"的盲区既不被它支持也不被它反驳；它的"顺从倾向"测量方式是拒绝关键词匹配，与我们的探针不同，两组数也不能直接比较。

**E6（已发表防御的可用性批量）——method_source，n/a。** E6 的 26 次运行里覆盖了"安全样本混入与 BEA"：其中安全样本混入对应论文的 Baseline 防御（直接把不带前缀的原始安全示例混入数据集，Section 4.1），BEA 对应论文方法本身（公式 (2) 的 D_secret 与公式 (3) 的联合微调，Section 3.3）。E6 不评价防御效果，所以没有可对照的数值。另外有两点需要先说清楚才能对照：论文的方法要求训练侧注入与推理侧把秘密提示拼到系统提示前同时成立（Section 3.3、Table 3），卡片只记录我们跑了 BEA，没有说明是否包含推理侧改写，也没有说明用了多少条安全示例；论文 Table 5 的 LoRA 实验仍然是一次集中式微调（卡片第 9 节的分析），与我们的联邦 LoRA 聚合不是同一件事。

**E7（无攻击对照）——background，n/a。** 论文不剔除客户端、不重新加权、不裁剪更新、不加噪、不过滤样本（卡片第 6 节），所以不存在"无攻击时防御是否误伤"这类可比量。最接近的是 Table 1 未受攻击行（Llama-2-7B-Chat 为 1.11 / 3.27% / 51.19% / 45.81% / 7.16）与 Table 8 的良性微调行，它们是评估参照，不是误报率对照；我们 Krum 80%、LoMar 65%、FLDetector 20%、MUD-HoG 20% 的无攻击排除率在论文中没有对应。

**E8（宿主适配）——background，n/a。** 论文是集中式设定，没有服务器聚合、全局模型下发或客户端插件的位置（卡片第 1 节、第 3 节），我们的 Flower 与 OpenFedLLM 挂载与它没有对应关系。

**E9（Safe-FedLLM 式 LoRA 权重探针）——background，n/a。** 论文不是 Safe-FedLLM，也不用权重探针。不过我们 E9 的教训（同一配置同一初始化种子成功、换一次运行后探针失效）正说明多种子复现的必要性，而论文卡片未给种子数，我们无法判断它的数值是否也依赖某个幸运种子，因此在这一点上它不能作为对照。

**E10（调研与知识库）——background，n/a。** E10 是我们自己的调研统计，卡片没有说明这篇论文是否已收进 137 篇卡片或 47 篇防御流水线，因此只有背景关系。

## 3. 我们要与它可比还差什么

- **设定层面不可直接对齐**：论文是集中式 LMaaS，没有客户端、参与率、聚合与非独立同分布（卡片第 1 节、第 7 节）。我们要么做一次集中式复现（单进程、把带秘密提示的安全示例并入同一条数据流），要么在报告里明确声明"我们的联邦数值与它不可比"，现在两者都没有。
- **模型规模差一个量级**：论文是 Llama-2-7B-Chat 与 GPT-3.5-Turbo（Section 4.1），我们最大只到 4B（E6），主线是 0.5B；我们自己也把"7B 及以上模型的完整训练"列为没做过。
- **轮数无法对齐**：论文 Llama-2 沿用 llama-recipes 默认设置、**轮数卡片未给**，GPT-3.5-Turbo 是 5 个 epoch（Section 4.1）；我们是 20 轮与 4 轮。要对齐只能先查清它的默认 epoch 数，或改用它可比的 epoch 口径。
- **攻击类型不全**：论文的 FJAttack 是 100% 有害的 pure_bad 100 条，另有 Identity Role Shift Attack（100 条 Stanford Alpaca 干净样本加角色转移系统提示，Appendix A.3）。我们做的是 MaliciousGen 有害问答（100% / 30% / 10% 三种浓度）与触发词后门（E6 场景 B），**缺 Identity Role Shift 这一类攻击**，也缺后门攻击成功率评测。
- **评测指标缺口最大**：需要补齐 ASR（拒绝关键词表，Appendix C.2）、Harmfulness Score（GPT-4 按 1–5 打分，Appendix C.1）、ARC-Challenge Acc（5-shot）、MMLU Acc（5-shot）、MT-Bench Score（GPT-3.5 评委，满分 10）与 Rouge-1 F1（200 条测试样本）（Section 4.1、Section 5、Appendix C）。我们目前只有 AdvBench 无害率与检出计数，没有外部评委接口，也没有能力保持类基准。
- **防御实现细节要先固化**：论文用的是 11 条按 11 个有害类别各取 1 条的安全示例（约为 D 的 10%），回答由 Llama-2-7b-Chat 生成，Appendix G 与 Table 8 用 55 条；秘密提示为 150 个随机 token，且训练与推理必须用同一串，否则 ASR 从 3.64% 回到 26.18%（Table 3）。我们 E6 只记录了"跑了 BEA"，安全示例条数、来源、以及推理侧是否注入都要补齐，才能判断我们跑的是完整方法还是只做了数据侧。
- **评测集与任务性能**：论文有 330 条安全基准（11 类 × 30，拆成 55/275，Appendix B）和 SAMSum（16k 取 1000 + 100 有害样本）、sql-create-context（>70k 取 1000 + 100）这类带任务性能指标的真实场景（Section 5）。我们缺这样独立划分、能同时报告安全指标与任务指标（Rouge-1）的评测集。
- **种子与置信区间**：论文**种子数卡片未给**（Figure 4 只给了每个长度 5 组随机 token），我们缺多种子置信区间；结合 E9 换种子就失效的教训，我们若要引用它的数值，必须先自己多种子复现一遍。
- **开销无法对照**：论文没有任何量化开销（卡片第 8 节），我们的 E2 只能作为我们自己补的空白，不能与它比；它的额外成本是 11 条安全示例与推理时 150 个 token 的前缀，这与我们测的插件运行时开销不是同一口径。
- **自适应攻击两边都缺**：论文未评估自适应攻击者（卡片第 9 节），我们也没做"知道防御的自适应攻击"，所以无法互相印证，但这一条对我们仍是明确缺口。
- **可顺手做的可比实验**：既然 Table 8 显示注入带前缀安全示例能把良性微调造成的 ASR 抬升（6.55% / 8.73%）压回 0.73%，而我们 E4 已经测到良性微调让 AdvBench 无害率从 81% 掉到 49–63%，我们可以用同一套 E4 配置加一次"安全示例混入 / BEA"对照，这是目前最容易与论文形成同问题比较的一步。

```json
{
  "key": "wang2024bea",
  "paper_scale": {
    "models": "Llama-2-7B-Chat、GPT-3.5-Turbo（Section 4.1）；Llama-2 用 2×NVIDIA A100 80GB，按 llama-recipes 官方默认设置（Section 4.1）",
    "clients": "不适用：集中式 LMaaS 设定，全文无客户端概念；客户端数与参与率卡片未给（Section 3.2、卡片第 7 节）",
    "rounds": "卡片未给 Llama-2 的轮数（只用 llama-recipes 默认设置）；GPT-3.5-Turbo 为 5 个 epoch、learning rate multiplier 为 1（Section 4.1）",
    "poison_setting": "用户上传 pure_bad 数据集，含 100 条红队有害样本（近乎 100% 有害），配统一系统提示；服务提供方另加 11 条带 150 个随机 token 秘密提示的安全示例（约为 D 的 10%，Appendix G 与 Table 8 用 55 条）（Section 4.1、Appendix A.2、Appendix B）；另有 Identity Role Shift Attack，用 100 条 Stanford Alpaca 干净样本加角色转移系统提示（Appendix A.3）；真实场景为 SAMSum 取 1000 条 + 100 条有害样本、sql-create-context 取 1000 条 + 100 条有害样本（Section 5）",
    "seeds": "卡片未给（Figure 4 只说明每个提示长度用了 5 组随机 token 实验）",
    "federated": false,
    "lora": true
  },
  "headline_results": [
    "Llama-2-7B-Chat 上无防御的 FJAttack 把 ASR 推到 94.91%、Harmfulness Score 推到 4.68，本方法把它压回 3.64% 与 1.22，接近未受攻击模型的 3.27% 与 1.11（Table 1）。",
    "GPT-3.5-Turbo 上相对 Baseline 防御把 Harmfulness Score 从 4.55 降到 1.73、ASR 从 60% 降到约 15%（Section 4.2；Table 1 对应 4.55 / 60.00% → 1.73 / 14.91%），Abstract 概括为相对 Baseline 防御 ASR 下降 75%。",
    "LoRA 集中式微调下 Llama-2 的无防御 ASR 为 95.27%、本方法为 2.91%（Table 5）；若推理时不拼秘密提示，ASR 从 3.64% 回升到 26.18%（Table 3）；Table 8 中良性微调使 ASR 从 3.27% 升到 6.55%（Dialog Summary）与 8.73%（SQL Generation），本方法压到 0.73%。"
  ],
  "links": [
    {"experiment": "E1", "relation": "background", "agreement": "n/a", "detail": "论文是集中式单进程微调，没有宿主框架、聚合与下发步骤（卡片第 1 节、Section 3.2），我们的宿主无副作用逐位核对没有对应物。"},
    {"experiment": "E2", "relation": "background", "agreement": "n/a", "detail": "论文未报告任何量化开销，无 FLOPs、显存、训练时长或通信量（卡片第 8 节），只有安全示例带来一点额外微调成本与 150 token 推理前缀的定性说法（Limitations、Section 4.3），与我们的插件运行时开销不是同一口径。"},
    {"experiment": "E3", "relation": "background", "agreement": "n/a", "detail": "威胁模型重叠（E3 的恶意客户端用 MaliciousGen 有害问答、占其数据 100%，即 FJAttack 形态），但论文的观测量只在数据平面，明确不使用模型更新、LoRA 增量、逐层范数、梯度或跨轮历史（卡片第 5 节），我们的效果层/因子层特征没有可印证的结论。"},
    {"experiment": "E4", "relation": "same_question", "agreement": "consistent", "detail": "论文 Table 8 的\"无意造成的安全下降\"与我们 E4 的良性基线回答同一问题：良性微调本身就会削弱安全对齐（Dialog Summary ASR 3.27% → 6.55%，SQL Generation 3.27% → 8.73%，本方法压到 0.73%），我们观察到无攻击微调使 AdvBench 无害率从 81% 降到 49–63%。方向一致，但我们是 Qwen2.5-0.5B、LoRA r=16、20 轮、Dolly 数据，论文是 Llama-2-7B-Chat 等，规模与基准相差很大，数值不能直接比较；论文无非独立同分布概念，我们 Dirichlet 划分的结论也无从对照。"},
    {"experiment": "E5", "relation": "setting_reference", "agreement": "consistent", "detail": "论文在 330 条安全基准上用拒绝关键词表算 ASR、用 GPT-4 打 Harmfulness Score（Appendix B、Appendix C），是我们行为探针应对齐的评测参照；其前提（有害数据微调把 ASR 从 3.27% 推到 94.91%，Table 1）与我们 37 个恶意客户端中 33 个探针分数超过全部良性客户端的结果方向一致。但论文只测 100% 有害数据，没有低浓度投毒与部分参与的格点，我们 10% 浓度检出 3–15%、每轮只抽 5 个客户端检出 24–35% 的盲区不被它支持也不被它反驳，且拒绝关键词判分与我们的探针分数不可直接比较。"},
    {"experiment": "E6", "relation": "method_source", "agreement": "n/a", "detail": "E6 的 26 次运行覆盖了\"安全样本混入与 BEA\"，安全样本混入对应论文 Baseline 防御（Section 4.1），BEA 对应论文方法（公式 (2)(3)、Section 3.3）；E6 不评价防御效果，无对照数值。论文方法要求训练侧注入与推理侧拼秘密提示同时成立（Section 3.3、Table 3），卡片未说明我们的 BEA 是否含推理侧改写、用了多少条安全示例；论文 Table 5 的 LoRA 实验仍是集中式微调（卡片第 9 节），与我们的联邦 LoRA 聚合不同。"},
    {"experiment": "E7", "relation": "background", "agreement": "n/a", "detail": "论文不剔除客户端、不重新加权、不裁剪、不加噪、不过滤样本（卡片第 6 节），没有\"无攻击时防御是否误伤\"的可比量；Table 1 未受攻击行（1.11 / 3.27% / 51.19% / 45.81% / 7.16）与 Table 8 良性微调行是评估参照而非误报率对照，我们 Krum 80%、LoMar 65% 等无攻击排除率在论文中没有对应。"},
    {"experiment": "E8", "relation": "background", "agreement": "n/a", "detail": "论文为集中式设定，没有服务器聚合、全局模型下发或客户端侧插件位置（卡片第 1 节、第 3 节），与我们的 Flower、OpenFedLLM 宿主适配无对应关系。"},
    {"experiment": "E9", "relation": "background", "agreement": "n/a", "detail": "论文不是 Safe-FedLLM、也不用权重探针；但 E9 换种子后探针失效的教训说明需要多种子复现，而论文种子数卡片未给，无法判断其数值是否依赖特定种子，因此不能作为对照。"},
    {"experiment": "E10", "relation": "background", "agreement": "n/a", "detail": "E10 是我们自己的调研与知识库统计，卡片未说明这篇论文是否已收入 137 篇卡片或 47 篇防御流水线，只有背景关系。"}
  ],
  "missing_for_comparability": [
    "一次集中式复现（或明确声明不可比）：论文无客户端、参与率、聚合与非独立同分布（卡片第 1 节、第 7 节），我们现有联邦数值与它不同设定。",
    "模型规模对齐：论文为 Llama-2-7B-Chat 与 GPT-3.5-Turbo（Section 4.1），我们最大 4B、主线 0.5B，缺 7B 及以上的完整训练。",
    "轮数/epoch 口径：论文 Llama-2 轮数卡片未给（llama-recipes 默认）、GPT-3.5-Turbo 为 5 个 epoch（Section 4.1），我们为 20 轮与 4 轮，需先确定可比口径。",
    "攻击类型补齐：缺 Identity Role Shift Attack（100 条 Alpaca 干净样本加角色转移系统提示，Appendix A.3），也缺后门攻击成功率评测。",
    "指标补齐：ASR（拒绝关键词表，Appendix C.2）、Harmfulness Score（GPT-4 1–5 分，Appendix C.1）、ARC-Challenge Acc（5-shot）、MMLU Acc（5-shot）、MT-Bench Score（GPT-3.5 评委，满分 10）、Rouge-1 F1（200 条测试样本）（Section 4.1、Section 5、Appendix C）。",
    "防御实现细节固化：安全示例条数与来源（11 条、约 10% of D、11 类各 1 条、回答由 Llama-2-7b-Chat 生成；Appendix G 用 55 条）、秘密提示 150 个随机 token 且训练与推理共用同一串（Section 4.1、Table 3、Table 8）。",
    "评测集建设：330 条安全基准（11 类 × 30，拆 55/275，Appendix B）与带任务指标的 SAMSum、sql-create-context 真实场景（Section 5）。",
    "多种子与置信区间：论文种子数卡片未给（Figure 4 只有每个长度 5 组随机 token），我们也要自己补多种子复现。",
    "开销口径说明：论文无任何量化开销（卡片第 8 节），我们的 E2 数据无法与其对照，只能标注为自补空白。",
    "自适应攻击：论文未评估（卡片第 9 节），我们也未做，无法互相印证，但仍是我们的缺口。"
  ],
  "metrics_paper_uses": [
    "Harmfulness Score（GPT-4 按 1 到 5 打分后取平均，Appendix C.1）",
    "Attack Success Rate（ASR，按拒绝关键词表判断，Appendix C.2）",
    "ARC-Challenge Acc（5-shot）",
    "MMLU Acc（5-shot）",
    "MT-Bench Score（GPT-3.5 作评委，满分 10）",
    "Rouge-1 F1（真实场景微调性能，200 条测试样本，Section 5）"
  ],
  "relevance": "high"
}
```
