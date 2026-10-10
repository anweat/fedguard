## 1. 论文自己的实验规模与主要结果

**场景与定位。** 卡片明确说明这篇论文是集中式大模型训练与发布供应链场景，不是联邦学习，也不是联邦大模型微调：论文原话设定为 "LLMs are trained internally, and then publicly released on open-source platforms"（Threat Model 节）。因此卡片中的 "clients" 与 "rounds" 两项在论文里没有字面对应物：论文没有客户端概念，也没有联邦轮次；可类比的量是数据层面的中毒比例，阶段数则是"发布前 SFT 植入 + 发布后两轮持续微调"。

**模型与数据规模。** 目标模型为 Qwen2.5-0.5B、Qwen2.5-1.5B、LLaMA3.2-1B，触发器长度分别为 3、10、15 个 token（Experimental Setup → Models）。数据集为 SST-2（5000 条）、GSM8K（5000 条）、MBPP（467 条），每阶段训练 3 个 epoch；中毒样本 2000 条、中毒比例 40%（Appendix → Details about experimental setup）。硬件为单机 5 张 NVIDIA RTX 4090，使用 LLaMA Factory 框架，每个微调阶段的训练时间约为 1 GPU-hour（Appendix）。论文未使用也未评估 LoRA 或其他 PEFT；实验里实际评估的三种下游策略是全参数更新、数据回放和部分参数冻结（FREEZE）。种子数、触发器优化的迭代次数与候选采样预算、显存占用，卡片均未给，卡片明确写出"论文未报告"这些量。

**主要数值结果。**

- Table 1：BadNet 的梯度相似度为 0.20，SST-2 上 ASR 从 100.00% 降到 70.00%；P-Trojan 相似度为 0.60，ASR 保持 100.00%。
- Table 2（发布时效果）：P-Trojan 在三个模型上 ASR 均为 100.00%，SST-2 ACC 分别为 91.97%、93.78%、92.10%；BadNet 在 Qwen2.5-1.5B 上只有 46.00% ASR；BadEdit 的 ASR 为 69.00%、53.00%、49.00%，且在 Qwen2.5-0.5B 上 ACC 只有 70.23%。
- Table 3（持续性）：Cleanup 后 P-Trojan 在三个模型上 Persis 均为 100.00%，Cross-task 后为 99.00%–100.00%；BadNet 在 Qwen2.5-1.5B 上 Cleanup/Cross-task 的 Persis 均为 0.00%，在 LLaMA3.2-1B 上为 4.60% 与 2.30%；BadNet-CE 在 Qwen2.5-1.5B 上只有 4.00% 与 17.00%；BadEdit 的 Persis 较高（Cleanup 为 69.57%、100.00%、100.00%；Cross-task 为 73.91%、98.11%、100.00%）但其 ASR 只有 48.00%–55.00%。卡片还专门指出：论文正文称 BadEdit 在 Cross-task "nearly perfect persistence (≈100%) across all models"，与 Table 3 中 Qwen2.5-0.5B 的 73.91% 不一致，以表格数值为准。
- Table 4（Qwen2.5-1.5B，Cross-task 阶段的知识保持策略）：不用 SST-2 回放的全参数更新 ASR 为 67.00、SST-2 ACC 为 80.83、GSM8K ACC 为 46、MBPP ACC 为 45.80；加回放后 ASR 为 100.00、SST-2 ACC 为 87.79、GSM8K ACC 为 41、MBPP ACC 为 46.20；FREEZE 时 ASR 为 100.00、SST-2 ACC 为 94.95、GSM8K ACC 为 58.23、MBPP ACC 为 9.80。
- Table 5（顺序消融，Qwen2.5-1.5B）：Cleanup→Cross-task 的 ASR 为 100.00/100.00；反转为 Cross-task→Cleanup 后 ASR 为 99.00/98.00，SST-2 ACC 为 90.44/93.79，GSM8K ACC 为 57.24/58.15，MBPP ACC 为 45.60/45.00。
- Table 6（目标任务选择，Qwen2.5-1.5B）：以 GSM8K 为目标任务时，Cleanup 后 ASR 100.00、ACC 52.09、Persis 100.00；Cross-task 后 ASR 100.00、ACC 51.52、Persis 100.00。
- Sensitive Analysis 正文（卡片未给表号）：在 SST-5 上继续微调，P-Trojan 保持 100% ASR 与 100% Persistence。
- Potential Defense 正文（卡片未给表号）：BadActs 在中毒的 Qwen2.5-1.5B 上识别出 99% 的后门输入，假阳性率为 10%。

**机制性的核心结论。** 论文把后门植入建模为"任务对齐"问题，用 Eq.2 最大化干净任务与后门任务在最后一层 transformer token embedding 上的梯度余弦相似度，并给出 Theorem 1 与 Corollary 1：梯度对齐度越高，下游干净微调对后门损失的上界越紧越低；Observation 2 进一步说，在下游微调保持干净任务效用的前提下，后门损失不会退化，甚至可能被"加固"。指标方面，论文使用 ASR、干净任务准确率 Acc，以及自定义的持续性指标 Persis = "the ratio of ASR after post-deployment SFTs to the initial ASR at implanting"（Experiments 节）。

## 2. 与我们各项实验的对应

**总体判断。** 这篇论文在场景（集中式、非联邦）、微调方式（全参数 SFT，不用 LoRA）、攻击者身份（模型发布方而非联邦客户端）、防御立场（攻击论文，只附带评估一个检测器）四个方面都与 fedguard 的设定错位。因此它不能作为任何一项实验的 method_source（我们并没有实现或运行 P-Trojan），也不是 setting_reference 意义上的对齐目标（它不是联邦设置，没有客户端、参与率、轮次、聚合这些我们要对齐的维度）。它真正的对应点在于"问题层"和"观测层"：它回答了"后门为什么能活过良性微调"，而这正是我们 E3/E4 在 LoRA 更新特征上想探的问题；它报告的高误报检测代价，又与 E7 的良性代价读数同向。

**E1（不改变训练）——background，n/a。** 论文不涉及在宿主框架上挂载插件，也不涉及逐位一致性，卡片没有任何可比内容。

**E2（开销）——background，n/a。** 论文只报告硬件与框架（Appendix："All experiments were conducted on a single machine equipped with 5 NVIDIA RTX 4090 GPUs (24GB memory each), using LLaMA Factory framework"）以及"The total training time per fine-tuning stage was approximately 1 GPU-hours."（Appendix）。卡片明确写出：论文未报告触发器优化的迭代次数、候选采样预算、每个候选的前向/反向次数、显存占用，也未报告通信与存储开销。因此我们的 0.7%–2.8%、0.25%–1.8%、3.8 秒/5.7 秒/3.2 秒这些数字，与论文的 1 GPU-hour/阶段不是同一类量，不能对应。

**E3（特征预实验 P1：效果层与因子层的更新大小/方向）——same_question，not_comparable。** 论文回答的问题是"后门能否在多轮良性微调后存活，以及什么梯度几何性质决定存活"，它给出的答案是梯度对齐（Eq.2 的余弦相似度）越高，后门损失上界越低（Corollary 1、Observation 2），Table 1 里 BadNet 相似度 0.20 对应 ASR 从 100.00% 掉到 70.00%、P-Trojan 相似度 0.60 对应 ASR 保持 100.00%。我们在 E3 里测的正是"更新大小"和"方向"两类特征，其中方向特征（因子层方向 17/20、效果层方向 3/20）在概念上与论文的相似度是同一族观测。但两者的可观测对象不同：论文算的是最后一层 token embedding 上的逐样本损失梯度余弦相似度（Alignment-Optimizing Trigger Generation 节："the alignment-optimizing objective in Eq. 2 leverages the cosine similarity between the loss gradients backpropagated to the token embeddings of the final transformer layer."），我们算的是 LoRA 的 BA 乘积与 A/B 因子的逐轮更新；卡片本身也把"Corollary 1 的推导把 δθ 当作全参数空间的增量……LoRA 只更新低秩矩阵 A 与 B，θ 基本冻结，因此'embedding 层梯度对齐'能否传导到 LoRA 子空间没有被论文验证"列为分析性局限。因此不能互相印证也不能互相否定，不能说我们的 17/20 支持或反驳了论文的 0.60 相似度结论。

**E4（良性基线与校准 P2）——same_question，not_comparable（其中一条子结果与论文前提一致）。** E4 与论文共享的问题是"良性微调会怎样改变后门相关属性"。E4 发现"无攻击的良性微调本身就让 AdvBench 无害率从 81% 降到 49–63%（alpaca 模板）"，这与论文的整个前提——下游用户是良性的、其自发的微调会重塑模型的安全/后门相关行为，因而后门的存活性必须单独研究（Threat Model 中"adversary has no control over the backdoored LLM fθ once it is released"）——方向一致，属于互相印证而非矛盾。但必须明确：论文度量的是"触发器出现时输出攻击者指定回复"的定向 ASR 与 Persis，E4 度量的是 AdvBench 无害率这一通用安全对齐指标，二者不是同一指标；而且 E4 是 Qwen2.5-0.5B、10 客户端、20 轮、LoRA、单个或 3 个种子的联邦设置，论文是 0.5B–1.5B、集中式、全参数、3 epoch 的 SFT，规模都小，不能直接比较数值。E4 的另一条"按 Dolly 类别的 Dirichlet 划分对 LoRA 更新的相似度几乎没有影响"，论文完全没有非独立同分布客户端这一维度（卡片：论文未说明客户端数与参与率，没有 non-IID 定义），无法对应。

**E5（自动攻击矩阵 P3）——same_question（部分），not_comparable。** E5 关心"逐轮能否把恶意客户端检出来"，其中"行为探针（加载每个客户端的更新后测模型对 AdvBench 有害提示的顺从倾向）跨轮累积后 37 个恶意客户端中 33 个超过全部良性客户端"是一条跨轮累积的行为类证据。论文关心的"后门是否在多轮更新后仍在"也是跨轮问题，Persis 指标（"the ratio of ASR after post-deployment SFTs to the initial ASR at implanting"）天然需要跨轮历史，这与我们"跨轮累积探针分数"的思路同族。但论文的结论方向是攻击存活（Cleanup 后 P-Trojan Persis 100.00%，Cross-task 后 99.00%–100.00%，Table 3），我们的结论方向是防御可检出性随浓度与参与率下降（分散的低浓度投毒检出 3–15%，每轮只抽 5 个客户端时 24–35%），两者不构成印证或矛盾，因为论文根本没有聚合、客户端采样、参与率这些机制（卡片明确写"论文未说明"）。我们的检出率数字也不能拿去和论文的 Persis 数字比。

**E6（已发表防御可用性批量）——setting_reference（弱），not_comparable。** 这条对应是间接的：论文 Potential Defense 节评估的 BadActs 是"激活空间的通用检测器"，而 E6 批量里我们跑了激活聚类、谱签名、梯度谱熵、ONION 等激活/输入/梯度视图的检测类方法，BadActs 本应落在同一批里，但 E6 的清单中没有列出 BadActs，所以这是"我们该补齐的检测器参照"，而不是"我们跑过论文的方法"。E6 里"样本过滤的一次读数（4B，480 条样本 96 条带毒）：ProtegoFed 精确率 0.77 召回率 0.49；谱签名、梯度谱熵、激活聚类接近 0"是检测器在过滤任务上的可用性读数，与 BadActs 的 99% 识别率 / 10% 假阳性率属于同一族指标（检测率 + 误报代价），可以放在同一张表里对照，但 E6 明确"不评价防御效果"，且论文的 BadActs 数字来自中毒的 Qwen2.5-1.5B（集中式、全参数），我们的是 Qwen3.5-4B（联邦 LoRA），模型与流程都不同，不能直接比较。

**E7（无攻击对照）——same_question，consistent（在同一类现象上）。** 论文报告的 BadActs 代价是"识别出 99% 的后门输入，但干净样本上有 10% 的假阳性率"，论文自评 "its practical utility may be limited, as it incorrectly penalizes a significant portion of benign inputs"（Potential Defense）。E7 在无攻击条件下测得：Krum 仍排除 80% 的客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%，梯度谱熵屏蔽 71% 样本、ONION 改写 59% 样本、激活聚类屏蔽 15%、ProtegoFed 屏蔽 4%。两者都是"良性输入/良性客户端被防御机制错误处置"的误报代价，方向上一致；而且论文的 10% FPR 与 E7 中激活聚类屏蔽 15% 样本在量级上接近，这是我们可以引用的一条一致证据（注意：一个是逐样本 FPR，一个是逐样本屏蔽比例，口径仍有差异）。同样必须说明：E7 是 Qwen3.5-0.8B/4B、5 客户端、4 轮的联邦 LoRA 单次运行，论文是 Qwen2.5-1.5B 集中式全参数微调，规模与设置都不同，不能直接比较，一致性只能停留在"现象方向"层面。

**E8（宿主适配）——background，n/a。** 论文不是联邦框架，没有服务器侧/客户端侧插件的挂载问题，卡片无对应内容。

**E9（Safe-FedLLM 式 LoRA 权重探针）——background（弱），n/a。** 论文没有做任何权重层面的检测（卡片原话：论文未对 P-Trojan 做任何权重层面的检测实验），也没有权重探针类方法。唯一相关的一点是它论证了"梯度视图"比"权重视图"更有信息量（Eq.2 用梯度余弦相似度而非权重），但这只是背景，不构成对应。

**E10（调研与知识库）——background（弱），n/a。** 这是我们的知识库统计（137 篇卡片、47 篇防御算子流水线、45 篇 481 个步骤的对齐率），不是实验，论文也不在其中作为被复现对象。仅有的联系是卡片本身已经对这篇论文做了"观测量 → 采集位置 → 干预动作"的算子化描述，可以作为 E10 知识库的一条条目来源；但这不是实验对应。

**一句话概括对应关系：** 这篇论文没有任何实验是"我们跑过它的方法"（无 method_source），也不是我们要在联邦设置上对齐数值的目标（无强 setting_reference）；它最有价值的是作为 E3/E4 的 same_question 外部参照——它提供了"梯度对齐 → 后门持续"这一因果解释，而我们的 E3/E4 只在 LoRA 因子上做了相关性观测，且论文自己承认该解释落到 LoRA 子空间并未被验证；其次是为 E7 提供了"检测器的误报代价可能很大"的同向证据。

## 3. 我们要与它可比还差什么

**第一，模型规模与训练量级要上去，但要对齐到它的口径需要先决定对齐哪种口径。** 论文用的是 Qwen2.5-0.5B、Qwen2.5-1.5B、LLaMA3.2-1B（Experimental Setup → Models），每阶段 3 个 epoch，数据集规模 5000/5000/467，硬件 5×RTX 4090。我们目前最大只到 Qwen3.5-4B 的少量插件可用性运行，统一实验是 Qwen2.5-0.5B 与 Qwen3.5-0.8B，且我们从未做 7B 及以上的完整训练、也没有 100 轮量级的运行。要对齐"后门在持续微调下的存活"这个问题，我们至少需要一条与论文同量级的 Qwen2.5-1.5B 或 LLaMA3.2-1B 的完整训练，并明确我们是在集中式口径（复现论文）还是联邦口径（迁移论文）上比。

**第二，触发式后门与 ASR/Persis 这两块评测我们整块缺失。** 论文的攻击是定向触发式后门：触发器追加在干净 prompt 末尾（"injected trigger tokens τ appended to the end of the clean prompt"），目标回复统一为 "sorry, I cannot answer that."，中毒样本 2000 条、中毒比例 40%（Appendix），评测用 ASR、Acc 和 Persis = 微调后 ASR / 植入时 ASR。我们的项目明确"没做过的"第一条就是后门的攻击成功率评测——E3/E4 用的是 MaliciousGen 有害问答训练出的恶意客户端，E5 用的是行为探针对 AdvBench 的顺从倾向，E6 场景 B 用了触发词与固定目标输出但没有做 ASR 评测。因此我们缺：触发器设计（含论文那样的 token 级触发器优化，或至少一个固定触发器基线）、逐样本中毒数据构造、ASR 评测脚本、以及 Persis 这样的"以植入时 ASR 为分母的跨阶段比值"指标。

**第三，持续微调的阶段结构我们没有。** 论文的持续性结论建立在两轮连续微调上（Cleanup SFT 用干净 SST-2、Cross-task SFT 用 MBPP 与 GSM8K，Table 3 表注说明 Cross-task 阶段对 SST-2 部署了良性数据回放），并且做了顺序消融（Table 5）与目标任务选择消融（Table 6）。我们的实验都是"一次联邦训练 + 逐轮判定"（E5 的 20 轮、E6/E7 的 4 轮），没有"训练完成 → 用干净数据做移除微调 → 换任务再做一轮"这种模型生命周期式的阶段划分，也没有记录同一触发器在不同阶段的指标。要对齐，我们需要把评测从"轮内"扩展到"模型版本 + 微调阶段"，这也正好呼应卡片第 10 节提出的"模型版本/来源视图"需求。

**第四，LoRA 口径下"论文结论是否成立"这件事论文没做，我们必须自己做才算可比。** 论文未使用也未评估 LoRA/PEFT，与 LoRA 最接近的证据是 FREEZE：Table 4 显示 ASR 仍为 100.00%、SST-2 ACC 为 94.95%，但 MBPP ACC 只有 9.80%，论文自己称之为 "trades off generalization on other downstream tasks"。卡片明确警告不能把这个结果外推为"LoRA 下后门同样能存活"。因此我们若要在联邦 LoRA 上谈"后门持续性"，需要补齐：LoRA 秩与目标模块的敏感性、聚合（FedAvg 类）对单个客户端后门贡献的稀释/放大曲线、客户端参与率与采样对持续性的影响。这些维度论文全部没有（卡片：论文未说明聚合、参与率、客户端采样等机制）。

**第五，防御侧的口径要对齐，并且要补 BadActs 与自适应攻击。** 论文唯一的防御实验是 BadActs：99% TPR、10% FPR；它没有评估知道 P-Trojan 的自适应防御者。我们这边 E6 覆盖了 26 次运行、20 余种防御，但清单里没有 BadActs；E7 给出了良性代价读数但只是单次运行；我们明确没做"知道防御的自适应攻击"和"上传侧攻击（更新放大、针对防御构造更新、合谋）"。要与论文可比，至少需要：(a) 在同一个联邦 LoRA 设置里补跑 BadActs 或等价的激活空间检测器，与论文的 99%/10% 并列但不直接比数值；(b) 把 E7 的单次良性代价扩成多种子；(c) 评估一个知道防御存在的攻击者，因为论文的"持续性"结论只在无自适应防御者的假设下成立（卡片：论文未测试专门检测梯度对齐触发器的防御方）。

**第六，统计强度。** 论文报告的是三个模型上的完整训练结果（每阶段 3 epoch、5×4090、约 1 GPU-hour/阶段），卡片没有给种子数（卡片未给）。我们这边 E3、E9 是单个种子，E4 有 3 个种子，E5 多数级别只有 1 个种子，E7 是单次运行，且我们明确"没做过多种子的置信区间"。所以在任何一条"与论文一致/矛盾"的判断里，我们目前都只能给出方向性陈述，不能给数值比较。

**第七，指标口径的差异要显式写清，否则会误比。** 我们现有指标是"恶意客户端被标出的轮数比例"（E3 的 15/20、17/20、3/20，E4 的 18/18、14/18、6/18、1–2/18）、"检出率与误报率"（E5 的 83–100% / 0.6–1.9%）、"样本过滤精确率/召回率"（E6 的 0.77/0.49）、"良性屏蔽比例"（E7 的 80%、65%、71%、59% 等）。论文的指标是 ASR、ACC、Persis 和 BadActs 的 TPR/FPR。两套指标之间没有换算关系，任何"我们的检出率相当于论文的 Persis"之类的表述都不成立——这一点必须在报告里写明。

```json
{
  "key": "persistcontinual2025",
  "paper_scale": {
    "models": "Qwen2.5-0.5B、Qwen2.5-1.5B、LLaMA3.2-1B（Experimental Setup → Models）",
    "clients": "卡片未给——论文不是联邦设置，没有客户端与参与率概念（第 7 节、第 9 节）",
    "rounds": "卡片未给联邦轮次；论文为发布前 SFT 植入 + 发布后两轮持续微调（Cleanup SFT、Cross-task SFT），每阶段 3 个 epoch（Experiments 节、Appendix）",
    "poison_setting": "数据层面 2000 条中毒样本、中毒比例 40%；触发器追加在干净 prompt 末尾，触发器长度 3/10/15 个 token；目标回复统一为 sorry, I cannot answer that.（Appendix → Details about experimental setup、Notation 节、Experimental Setup → Models）",
    "seeds": "卡片未给",
    "federated": false,
    "lora": false
  },
  "headline_results": [
    "Table 3：Cleanup 后 P-Trojan 在三个模型上 Persis 均为 100.00%，Cross-task 后为 99.00%–100.00%；对照的 BadNet 在 Qwen2.5-1.5B 上 Cleanup/Cross-task 的 Persis 均为 0.00%，在 LLaMA3.2-1B 上为 4.60% 与 2.30%（Table 3）",
    "Table 2：P-Trojan 在三个模型上 ASR 均为 100.00%，SST-2 ACC 分别为 91.97%、93.78%、92.10%；BadNet 在 Qwen2.5-1.5B 上只有 46.00% ASR；BadEdit 的 ASR 为 69.00%、53.00%、49.00%，且在 Qwen2.5-0.5B 上 ACC 只有 70.23%（Table 2）",
    "Table 1：BadNet 的梯度相似度为 0.20，SST-2 上 ASR 从 100.00% 降到 70.00%；P-Trojan 相似度为 0.60，ASR 保持 100.00%（Table 1）",
    "Potential Defense 正文（卡片未给表号）：BadActs 在中毒的 Qwen2.5-1.5B 上识别出 99% 的后门输入，假阳性率为 10%（Potential Defense）"
  ],
  "links": [
    {"experiment": "E1", "relation": "background", "agreement": "n/a", "detail": "论文不涉及宿主框架上的插件挂载与逐位一致性，卡片无对应内容"},
    {"experiment": "E2", "relation": "background", "agreement": "n/a", "detail": "论文只给硬件与框架（5×RTX 4090、LLaMA Factory）和每阶段约 1 GPU-hour（Appendix），卡片明确写出未报告触发器优化计算量、显存、通信与存储开销；与我们的毫秒级/秒级插件开销不是同类量"},
    {"experiment": "E3", "relation": "same_question", "agreement": "not_comparable", "detail": "论文回答'什么梯度几何性质决定后门在多轮微调后存活'，答案是最后一层 token embedding 上的梯度余弦相似度（Eq.2），Table 1 中相似度 0.20/0.60 分别对应 ASR 70.00% 与 100.00%；我们 E3 测的是 LoRA 效果层与因子层的更新大小与方向（因子层方向 17/20、效果层方向 3/20）。观测对象不同（论文为全参数 SFT 的 embedding 层梯度，我们为 LoRA A/B 与 BA 的逐轮更新），且卡片指出该理论到 LoRA 子空间的传导未被论文验证，故不能互相印证或否定"},
    {"experiment": "E4", "relation": "same_question", "agreement": "not_comparable", "detail": "两者都问'良性微调如何改变后门/安全相关属性'。E4 的'无攻击良性微调使 AdvBench 无害率从 81% 降到 49–63%'与论文'下游用户良性且其微调会重塑模型行为'的前提方向一致，可视为同一现象层面的互相印证；但论文指标为定向 ASR/Persis，E4 为 AdvBench 无害率，且我们为 Qwen2.5-0.5B/10 客户端/20 轮/LoRA/联邦、论文为 0.5B–1.5B/集中式全参数/3 epoch，规模小得多，不能直接比较。E4 的 Dirichlet 划分对 LoRA 更新相似度几乎无影响这一条，论文无客户端异质性维度，无法对应"},
    {"experiment": "E5", "relation": "same_question", "agreement": "not_comparable", "detail": "两者都是跨轮问题：论文的 Persis 需要跨微调阶段追溯同一触发器上的 ASR，我们的行为探针分数跨轮累积（37 个恶意客户端中 33 个超过全部良性客户端）。但论文结论方向是后门存活（Table 3 Persis 99%–100%），我们结论方向是低浓度与客户端采样下检出率骤降（3–15%、24–35%）；论文没有聚合、参与率、客户端采样机制（卡片明确写未说明），因此不构成印证或矛盾"},
    {"experiment": "E6", "relation": "setting_reference", "agreement": "not_comparable", "detail": "论文 Potential Defense 评估的 BadActs 是激活空间检测器，本应落在 E6 的检测类方法批次里，但 E6 清单未含 BadActs，故这是'应补齐的参照'而非'跑过论文的方法'。E6 的样本过滤读数（ProtegoFed 精确率 0.77/召回率 0.49；谱签名、梯度谱熵、激活聚类接近 0）与 BadActs 的检测率 99%/假阳性 10% 属同族指标，但模型（Qwen3.5-4B 对 Qwen2.5-1.5B）与流程（联邦 LoRA 对集中式全参数）都不同，且 E6 明确不评价防御效果，不能直接比较"},
    {"experiment": "E7", "relation": "same_question", "agreement": "consistent", "detail": "论文报告 BadActs 有 10% 假阳性并自评 'its practical utility may be limited, as it incorrectly penalizes a significant portion of benign inputs'（Potential Defense）；E7 在无攻击时测得 Krum 仍排除 80% 客户端轮次、LoMar 65%、FLDetector 20%、MUD-HoG 20%，梯度谱熵屏蔽 71% 样本、ONION 改写 59%、激活聚类屏蔽 15%、ProtegoFed 屏蔽 4%。两者同向：良性输入/良性客户端被防御机制错误处置的代价可能很大。但 E7 是 Qwen3.5-0.8B/4B、5 客户端、4 轮、单次运行，论文是 Qwen2.5-1.5B 集中式全参数，规模小得多，只能作方向性一致，不能数值比较"},
    {"experiment": "E8", "relation": "background", "agreement": "n/a", "detail": "论文不是联邦框架，没有服务器侧/客户端侧插件挂载问题，卡片无对应内容"},
    {"experiment": "E9", "relation": "background", "agreement": "n/a", "detail": "论文未做任何权重层面的检测实验（卡片第 5 节），也没有权重探针方法；其与权重最接近的 BadEdit 只是被比较的攻击基线，不构成对我们 LoRA 权重探针实验的对应"},
    {"experiment": "E10", "relation": "background", "agreement": "n/a", "detail": "E10 是知识库统计（137 篇卡片、47 篇算子流水线、481 个步骤对齐率），不是实验；本卡片可作为知识库条目来源，但不构成实验层面的对应"}
  ],
  "missing_for_comparability": [
    "模型规模：缺 Qwen2.5-1.5B 与 LLaMA3.2-1B 量级的完整训练（论文模型为 Qwen2.5-0.5B/1.5B、LLaMA3.2-1B，我们统一实验只到 Qwen2.5-0.5B 与 Qwen3.5-0.8B，且从未做 7B 及以上完整训练）",
    "训练量级：缺 3 epoch × 每阶段、数据集 5000/5000/467 量级的训练（论文每阶段 3 epoch、约 1 GPU-hour、5×RTX 4090），也缺 100 轮量级的联邦长跑",
    "阶段结构：缺'植入 → 用干净同任务数据做 Cleanup SFT → 换任务做 Cross-task SFT'的连续微调阶段，以及顺序消融（论文 Table 5）与目标任务选择消融（论文 Table 6）",
    "攻击类型：缺触发式定向后门（触发器追加在干净 prompt 末尾、目标回复固定）与 token 级触发器优化（论文 Algorithm 1），以及论文的 BadNet、BadNet-CE、BadEdit 三个基线；我们只有 MaliciousGen 有害问答客户端与 E6 场景 B 的固定触发词",
    "投毒比例口径：缺数据层面的中毒比例设定（论文 2000 条中毒样本、40%），我们只有客户端层面的恶意占比（100%/30%/10%）",
    "指标：缺 ASR、干净任务 ACC，以及 Persis = 微调后 ASR / 植入时 ASR 这一跨阶段比值；我们现有的'轮数比例'检出率、误报率、精确率/召回率与论文的 ASR/Persis 无换算关系",
    "种子与统计：缺多种子置信区间（论文种子数卡片未给；我们 E3/E5/E9 为单种子、E7 为单次运行）",
    "LoRA 口径：缺论文未验证部分的实验——LoRA 秩与目标模块敏感性、FedAvg 类聚合对单个客户端后门贡献的稀释/放大、客户端采样与参与率对后门持续性的影响",
    "防御侧：缺 BadActs 或等价激活空间检测器在联邦 LoRA 上的读数，以与论文 99% TPR / 10% FPR 并列对照；缺知道防御的自适应攻击评测（论文未做，我们也没做）",
    "入口侧：缺上传侧攻击（更新放大、针对防御构造更新、合谋）的实验，论文没有这一入口，属于我们补齐联邦威胁模型自身的工作"
  ],
  "metrics_paper_uses": [
    "攻击成功率 ASR（Attack Success Rate，Table 1、Table 2、Table 3、Table 4、Table 5、Table 6）",
    "干净任务准确率 Acc（SST-2 ACC、GSM8K ACC、MBPP ACC，Table 2、Table 3、Table 4、Table 5、Table 6）",
    "持续性 Persis = 发布后微调后的 ASR / 植入时初始 ASR（Experiments 节定义，Table 3、Table 6）",
    "梯度余弦相似度 cos（Eq.2 定义，Table 1 报告 0.20 与 0.60）",
    "检测器 True Positive Rate 与 False Positive Rate（BadActs，99% 与 10%，Potential Defense 正文）"
  ],
  "relevance": "high"
}
```
