# safefedllm2026：Safe-FedLLM: Delving into the Safety of Federated Large Language Models

## 1. 基本信息

**场景**：联邦大模型微调（federated LLM fine-tuning，论文自称 FedLLM），并且明确建立在参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）中的低秩适配（Low-Rank Adaptation, LoRA）之上。论文第 4 节把整个框架定义在"服务器只能拿到客户端上传的 LoRA 更新（∆LoRA）、拿不到原始数据"的设定下（第 2 节：model updates are accomplished solely through the exchange and aggregation of LoRA updates）。这既不是传统联邦学习（图像分类等小模型场景），也不是集中式训练；论文在相关工作里专门把传统联邦学习防御与"PEFT-based FedLLM"对立起来，认为前者不适配。

**训练阶段**：分为两段。(1) 联邦训练开始之前的离线阶段：训练 LoRA-Probe 分类器（第 4.1 节、附录 A）；(2) 联邦训练阶段：客户端本地逐步 LoRA 训练、上传 LoRA 增量、服务器加权聚合与轮次跳过（第 4.3 节）。

**论文类型**：防御（defense）为主，内部包含检测（detection）组件（LoRA-Probe 分类器），并附有一段针对恶意客户端的初步脆弱性研究（preliminary study，第 3 节）。论文本身不提出新的攻击算法，恶意数据来自已有的 BeaverTails 与 MaliciousGen。

**模型与数据规模**：骨干模型为 Llama3.1-8B 与 Qwen2.5-7B（第 3.1 节、第 5.1 节）。模拟 10 个客户端、每个客户端 500 条样本，共 100 轮通信，每轮随机采样 3 个客户端，每个被选中客户端执行 10 个本地更新步（第 5.1 节）。LoRA 配置为 r = 8、α = 16，基座模型 8 比特量化，优化器 AdamW_bnb_8bit，学习率 5 × 10⁻⁵，最大序列长度 256（第 5.1 节）。良性数据来自 LMSYS-Chat 与 WildChat，恶意数据来自 BeaverTails 与自动生成的 MaliciousGen（第 3.1 节）。恶意客户端比例为 20% 到 50%（第 3.1 节）。安全评测用 AdvBench，指标为 Rule、MD-Judge、RM；效用评测用 MT-Bench 第一轮得分 MT-1，由 GPT-5-mini 评判（第 3.1 节）。论文正文标注为 arXiv:2601.07177v5 [cs.CR]，日期 30 May 2026（首页页脚）。

## 2. 威胁模型

**攻击者是谁与占比**：恶意客户端（malicious client）。比例在 20% 到 50% 之间变化（第 3.1 节：The proportion of malicious clients ranges from 20% to 50%），主实验用 30%（表 2、表 3），比例扫描结果见表 1、表 5、表 6、表 8。论文未说明恶意客户端之间是否合谋，也未说明他们是否由同一攻击者控制。

**能力（能改什么）**：论文实际模拟的攻击是数据层面的投毒——恶意客户端的本地更新来自 BeaverTails 与 MaliciousGen 两个有害/恶意数据集（第 3.1 节），即恶意客户端在自己的本地数据上按正常流程做 LoRA 训练，然后把由此产生的 ∆LoRA 上传。论文没有描述恶意客户端对上传更新做缩放、投影、加噪、替换等后处理，也没有描述服务器被攻陷的情形。第 1 节只在泛泛列举风险时提到"model poisoning, backdoor injection, or gradient inference attacks"，但实验部分没有实现后门触发器或梯度推断攻击，论文未说明这些攻击的具体构造。

**知识（知道什么）**：论文未说明攻击者是否知道 LoRA-Probe 的存在、探针参数、阈值 τcls、聚合规则或安全因子公式。论文也未说明攻击者是否知道其他客户端的更新或服务器的采样策略。

**目标**：破坏安全对齐——让全局模型在 AdvBench 类有害指令上生成有害内容，同时尽量不损害通用效用。证据是表 1：Llama3.1-8B 上 FedAvg（10:0，即全良性）Rule 为 90.77、MD-Judge 为 75.77，恶意比例升到 8:2 后降到 Rule 60.77、MD-Judge 20.77（表 1，BeaverTails & LMSYS-Chat）。论文用"无目标破坏安全"来描述该现象，但没有定义任何触发器，因此论文未说明这是否属于触发器式后门（backdoor）。

**防御者是谁、能看到什么、信任什么**：防御者是服务器。它能看到每个客户端上传的 LoRA 更新 ∆W⁽ʳ⁾ᵢ，以及每轮被选中的客户端集合 Sᵣ 与客户端本地样本数 nᵢ（第 4.3 节公式 12）；它看不到原始数据，论文把这一点当作核心动机（第 4.1 节：it operates solely on parameter updates without accessing raw client data）。服务器信任的东西包括：一份带标签的良性/恶意 ∆LoRA 参考样本集（用于离线训练探针，附录 A）、固定的 LoRA 初始化种子（Limitations 明确要求）、以及客户端会照协议维护影子分支。论文没有讨论服务器本身作恶，也没有讨论客户端伪造参与信息。

## 3. 攻击入口与流程位置

**攻击入口是本地数据准备**。论文的操作步骤是：恶意客户端持有 BeaverTails 或 MaliciousGen 的有害指令数据（第 3.1 节），在第 r 轮收到全局参数 W⁽ʳ⁾ 后按与良性客户端相同的配置执行 T = 10 个本地 LoRA 更新步（第 5.1 节），然后把本地 LoRA 更新 ∆W⁽ʳ⁾ᵢ 上传到服务器（第 4.3 节），服务器用 FedAvg 或鲁棒聚合规则合并（第 4.3 节、第 5.1 节）。攻击因此沿"本地数据准备 → 本地训练（产生被污染的 LoRA 增量）→ 更新上传 → 服务器聚合 → 全局模型下发"这条链路传播，但其注入点只在最初的数据与由此产生的更新上。

论文没有在以下位置放攻击：更新上传前的后处理（缩放、投影、拼装）、服务器聚合过程被篡改、以及评估与部署阶段的攻击。由于这是一篇防御论文，第 4 节到第 5 节描述的都是防御动作所在的位置：探针判定发生在客户端本地逐步训练阶段与服务器收到更新时，加权与跳过发生在服务器聚合时。

## 4. 方法原理

**核心思想**：把每个客户端的本地 LoRA 更新当作高维行为特征，用一个离线训练好、训练期间固定不变的轻量线性探针判别其恶意性，再把判别结果转成聚合权重，对聚合过程做安全门控（第 4.1 节、摘要）。

**关键步骤**：

第一，初步研究。论文在 Llama3.1-8B 上按良性:恶意 = 10:0 到 5:5 模拟攻击（表 1），并用 LDA+PCA 对第一层 LoRA B 矩阵更新做可视化，观察到良性与恶意更新可分（图 2）。第 3.3 节把结论写成两条性质：FedLLM 对恶意客户端脆弱；良性更新与恶意更新在 LoRA 更新空间中呈现可分模式。

第二，LoRA-Probe（第 4.1 节）。离线阶段用带标签样本训练：对本地步 t 计算 B 矩阵增量 ∆B₀,ₜ = Bₜ − B₀（公式 1），只取第一个 Transformer 层内所有 LoRA 模块的 B 矩阵增量，展平后按固定顺序拼接成特征向量 x（公式 2），再做 L2 归一化得到 x̃（附录 A），最后用逻辑回归给出恶意概率 s = σ(aᵀx̃ + c)（公式 3），其中 a 与 c 是可学习的权重向量与偏置。在线阶段对客户端 i 的第 t 步计算同样的 ∆Bⁱ₀,ₜ 与 x̃ᵗᵢ，得到 sᵗᵢ = σ(aᵀx̃ᵗᵢ + c)（公式 4），当 sᵗᵢ ≥ τcls 时判为恶意。探针在联邦训练开始前训练完，之后固定不更新。

第三，三层防御模块（第 4.2 节），每层输出安全因子 w⁽ʳ⁾ᵢ,ℓ，并统一记为 w⁽ʳ⁾ᵢ：

- Step-Level：在每个本地步做判定，统计良性判定次数 b⁽ʳ⁾ᵢ 与恶意判定次数 m⁽ʳ⁾ᵢ，用带时间衰减因子 γ 的贝叶斯更新 αᵢ ← γαᵢ + b⁽ʳ⁾ᵢ、βᵢ ← γβᵢ + m⁽ʳ⁾ᵢ（公式 5），安全因子为 w⁽ʳ⁾ᵢ,step = αᵢ / (αᵢ + βᵢ)（公式 6）。
- Client-Level：用客户端本轮最终本地更新的恶意概率 s⁽ʳ⁾ᵢ，先经两阶段 sigmoid 校准函数 g(·) 得到瞬时因子 ŵ⁽ʳ⁾ᵢ,client = 1 − g(s⁽ʳ⁾ᵢ)（公式 7），再对客户端参与过的轮次集合 R⁽ʳ⁾ᵢ 取历史平均得到 w⁽ʳ⁾ᵢ,client（公式 8）。校准函数见附录 C 公式 13：s ∈ [0, 0.8] 时 g(s) = ½σ(k(s−0.4))，s ∈ (0.8, 1] 时 g(s) = ½[1 + σ(k(s−0.9))]，k = 10。
- Shadow-Level：客户端维护一个与主训练分支独立的影子 LoRA 分支，该分支只用于产生探针输入，不参与主模型训练与参数聚合；统计影子分支逐步判定中的恶意比例 ρ⁽ʳ⁾ᵢ，用指数抑制函数 w⁽ʳ⁾ᵢ,shadow = (1 − ρ⁽ʳ⁾ᵢ)^η 得到安全因子（公式 9）。

第四，早期冻结（第 4.2 节）。由于学习率衰减与全局模型演化会让 ∆LoRA 分布漂移、降低探针后期可靠性，依赖探针输出的 Step-Level 与 Client-Level 只在前 Rf 轮更新安全因子，之后固定：w⁽ʳ⁾ᵢ = w⁽ᴿᶠ⁾ᵢ（公式 10）。Shadow-Level 不需要冻结，理由是影子分支与全局模型解耦。

第五，聚合（第 4.3 节）。先做安全门控的轮次跳过：若本轮平均安全因子 w̄⁽ʳ⁾ 低于阈值 τskip，则服务器跳过本轮聚合、保留上一轮全局参数 W⁽ʳ⁺¹⁾ = W⁽ʳ⁾（公式 11）；否则按样本量与安全因子加权聚合：W⁽ʳ⁺¹⁾ = W⁽ʳ⁾ + Σᵢ∈Sᵣ [nᵢw⁽ʳ⁾ᵢ / Σⱼ∈Sᵣ nⱼw⁽ʳ⁾ⱼ] ∆W⁽ʳ⁾ᵢ（公式 12）。

超参数取值（第 5.1 节）：Rf = 20（Step-Level 与 Client-Level），γ = 0.95，η = 7，τcls = 0.8，τskip = 0.2；附录 C 中 k = 10。

## 5. 检测或防御所需的数据

**(1) 逐本地步的 LoRA B 矩阵增量**。内容是 ∆Bⁱ₀,ₜ = Bⁱₜ − Bⁱ₀，只取第一个 Transformer 层内所有 LoRA 模块（公式 1、公式 2）。采集位置是客户端本地训练的每一个本地步（客户端每步），需要同时拿到该轮初始 B₀ 与第 t 步的 Bₜ。粒度是逐客户端、逐本地步、逐层（仅第一层）、逐模块，最终拼成一个特征向量。不需要跨轮历史，不需要干净参考数据；需要额外计算——每一步都要做一次特征提取与一次线性分类，论文称线性形式"negligible computational and time overhead"（第 4.1 节），但没有给出单独测量的探针耗时。

**(2) 离线探针训练集**。内容是带标签的良性/恶意 ∆LoRA 特征样本，产生方式是在联邦训练开始前模拟客户端本地训练，严格沿用 FedLLM 的本地训练配置（数据处理、优化器、学习率、批大小、本地步数），只取 50% 恶意比例设定下前 10 轮通信产生的增量（附录 A）。采集位置是客户端训练前（离线准备阶段）；粒度是逐样本的特征向量。需要干净参考数据：需要一份带标签的参考数据，并且为了防泄漏要剔除与模型训练数据重叠的样本，即 WildChat/LMSYS-Chat 的前 4000 条与 BeaverTails/MaliciousGen 的前 2500 条（附录 A）。需要额外计算：需要先跑一轮模拟本地训练来采集这些增量。

**(3) 客户端每轮上传的最终 LoRA 增量 ∆W⁽ʳ⁾ᵢ**。采集位置是服务器收到更新时；粒度是逐客户端、逐轮。Client-Level 需要它来算 s⁽ʳ⁾ᵢ（第 4.2 节），加权聚合也需要它（公式 12）。

**(4) 参与信息与样本量**。每轮被选中的客户端集合 Sᵣ 与每个客户端本轮使用的本地样本数 nᵢ，采集位置是服务器聚合时，粒度逐轮与逐客户端（公式 8、公式 12）。

**(5) 跨轮历史状态**。Step-Level 需要逐客户端的累计贝叶斯量 αᵢ、βᵢ（公式 5），Client-Level 需要客户端参与过的轮次集合 R⁽ʳ⁾ᵢ 与历史因子均值（公式 8），以及冻结阈值 Rf 前后的状态。这要求跨轮历史。

**(6) 影子分支的逐步更新**（只有 Shadow-Level 需要）。内容是客户端自己维护的影子 LoRA 分支在每个本地步的更新，该分支学习率固定、不参与主训练与聚合（第 4.2 节、附录 B）。采集位置是客户端每步；粒度逐客户端、逐本地步、逐层。

**(7) 超参数**：τcls = 0.8、τskip = 0.2、γ = 0.95、η = 7、Rf = 20、k = 10。**论文未说明**执行探针推断的是客户端还是服务器——论文只说"LoRA-Probe evaluates client-generated ∆LoRA"（第 4.1 节），而影子分支被明确描述为客户端维护（第 4.2 节），因此从文本无法确定逐步特征是在本地算好再上传，还是本地更新被整体上传到服务器后由服务器算。

**攻击留下的可观测量与绕过的检测**：论文声称攻击会在第一层 LoRA B 矩阵增量的分布与方向上留下可分痕迹，证据是图 2 的 LDA+PCA 可视化与表 7 的检测指标（例如 Llama3.1-8B 上 Shadow-Level 在 8:2 时 TPR 100、FPR 0、Precision 100、MCC 100，BeaverTails & LMSYS-Chat；在 5:5 时 TPR 99.35、FPR 0、Precision 100、MCC 99.33，表 7）。论文声称被它比下去的传统防御包括 Multi-Krum、Trimmed Mean、FoolsGold、Residual、DnC、FLAME、LASA（表 2、表 9）：在 Llama3.1-8B、30% 恶意比例、BeaverTails & LMSYS-Chat 下，这些基线的 Rule 在 51.54 到 61.73 之间，而 Shadow-Level 为 91.92（表 2）。

## 6. 干预动作

动作全部发生在服务器聚合环节：

1. **按安全因子重新加权**。公式 12 用 nᵢw⁽ʳ⁾ᵢ 作为客户端 ∆W⁽ʳ⁾ᵢ 的权重，恶意概率高、安全因子低的客户端贡献被压缩。论文把这一效果表述为"dynamically downweighting malicious updates"（第 4.3 节）。
2. **等效剔除客户端**。第 3.3 节与摘要把方法描述为"filters malicious clients before aggregation"，即安全因子趋近于 0 的客户端在该轮实际上不参与聚合；论文没有定义显式的硬剔除规则或永久拉黑机制。
3. **整轮跳过并保留上一轮全局参数**。当本轮平均安全因子 w̄⁽ʳ⁾ 低于 τskip = 0.2 时，服务器执行 W⁽ʳ⁺¹⁾ = W⁽ʳ⁾（公式 11），该轮不更新全局模型。
4. **仅报告**：论文未把"只输出恶意概率而不干预聚合"作为可用模式来讨论。

论文没有使用裁剪（clipping）、加噪（noise addition）、样本过滤（filter_samples）、模型修复或多轮回滚；这些论文均未说明。判定动作的时机是：Step-Level 在每个本地步、Client-Level 在每轮客户端最终更新处、Shadow-Level 在影子分支的每个本地步（第 4.2 节）；因此信号采集跨客户端与服务器两侧，但改变模型更新内容的干预只在服务器侧。

## 7. 实验设置与主要结果

**模型与数据**：Llama3.1-8B 与 Qwen2.5-7B；良性数据 LMSYS-Chat、WildChat，恶意数据 BeaverTails、MaliciousGen；安全评测集 AdvBench；效用评测 MT-Bench 首轮（第 3.1 节）。

**联邦设置**：10 个客户端，每个 500 条样本；100 轮通信；每轮随机采样 3 个客户端（参与率 30%）；每个被选中客户端 10 个本地步；LoRA r = 8、α = 16；基座 8 比特量化；AdamW_bnb_8bit，学习率 5 × 10⁻⁵，最大序列长度 256（第 5.1 节）。

**恶意比例**：20%、30%、40%、50%（表 1、表 5、表 6、表 8）。**数据是否非独立同分布**：论文未说明客户端数据是否按非独立同分布（non-IID）方式划分，也未给出 Dirichlet 等划分参数。

**指标**：Rule、MD-Judge、RM 越高表示越安全（表 1 中恶意比例升高时三者同时下降），MT-1 越高表示通用效用越好。

**关键结果**：

- 脆弱性：Llama3.1-8B 上 FedAvg 从 10:0 到 5:5，Rule 从 90.77 降到 45.77，MD-Judge 从 75.77 降到 7.69，RM 从 −1.55 降到 −4.33，MT-1 从 2.72 变到 3.34（表 1，BeaverTails & LMSYS-Chat）；Qwen2.5-7B 上 FedAvg 从 10:0 的 Rule 97.69、MD-Judge 96.15 降到 5:5 的 Rule 39.04、MD-Judge 24.42（表 8，BeaverTails & LMSYS-Chat）。
- 30% 恶意比例下的防御效果：Llama3.1-8B 上，FedAvg 为 Rule 51.73、MD-Judge 14.81、RM −3.97、MT-1 3.18；Shadow-Level 为 Rule 91.92、MD-Judge 77.12、RM −1.58、MT-1 3.20；Step-Level 为 88.85 / 76.35 / −1.73 / 3.07；Client-Level 为 84.42 / 65.96 / −2.01 / 3.05（表 2，BeaverTails & LMSYS-Chat）。论文在第 5.2 节给出相对提升：在 Rule 上 Shadow-Level 相对 Multi-Krum（60.19）提升 52.7%。
- 骨干泛化：Qwen2.5-7B、30% 恶意比例、BeaverTails & LMSYS-Chat 下，Shadow-Level 为 Rule 97.88、MD-Judge 96.92、RM −0.87、MT-1 5.17（表 3）。
- 比例扫描：Shadow-Level 在 8:2、7:3、6:4、5:5 下 Rule 分别为 92.31、91.92、91.73、94.04，MD-Judge 分别为 77.31、77.12、75.00、75.38（表 5，Llama3.1-8B，BeaverTails & LMSYS-Chat）。
- 检测指标：Shadow-Level 在 Llama3.1-8B 的 8:2 设定下 TPR 100、FPR 0、Precision 100、MCC 100（表 7，BeaverTails & LMSYS-Chat）；Step-Level 在 8:2 下 TPR 97.14、FPR 15.22、Precision 66.02、MCC 72.98（表 7）。
- 逐轮退化：Step-Level 与 Client-Level 的分类精度随轮次上升而持续下降，原因是 LoRA 更新分布漂移；Shadow-Level 跨轮稳定（图 4、第 5.3 节）。
- Qwen2.5-7B 上与其他聚合方法的对比（表 9，30% 恶意比例）同样显示 Shadow-Level 最好，例如 MaliciousGen & LMSYS-Chat 上 FedAvg Rule 59.42、DnC 76.54、FLAME 79.23、Shadow-Level 97.31。

## 8. 开销

论文报告了开销（表 4，Llama3.1-8B、30% 恶意比例）：FedAvg 训练时间 2h35m，Step-Level、Client-Level、Shadow-Level 均为 2h40m；可训练 LoRA 参数量 FedAvg 3.41M，Step-Level 与 Client-Level 3.41M，Shadow-Level 6.82M；GPU 显存 FedAvg、Step-Level、Client-Level 为 20.62GB，Shadow-Level 为 41.24GB。第 5.2 节称总训练时间开销增加 3.2%，并称影子分支可与主分支并行计算，因此墙钟开销可忽略。论文称探针是线性形式、计算与时间开销可忽略（第 4.1 节）。Limitations 又指出 Shadow-Level 缓解漂移问题"introduces additional training overhead and increases computational cost"。

通信开销与存储开销：论文未报告每轮通信量，也未给出存储占用数字。论文未报告探针本身的训练开销与推断延迟的实测值。

## 9. 假设、局限与自适应攻击

**方法成立依赖的假设（论文有依据的部分）**：

1. 良性与恶意客户端的 ∆LoRA 在特征空间中可分（第 3.3 节、图 2），并且离线探针训练样本与在线联邦训练的 ∆LoRA 分布一致——附录 A 为此严格对齐本地训练配置，并只取早期轮次样本。
2. 客户端侧 LoRA 初始化的随机种子必须与训练 LoRA-Probe 时使用的种子一致（Limitations：our framework assumes the LoRA initialization random seed used during client-side training is consistent with the one used to train the LoRA-Probe classifier），论文承认这在真实联邦环境中难以保证。
3. 固定探针在训练后期仍然可靠。论文用早期冻结（Rf = 20）缓解 Step-Level 与 Client-Level 的漂移，并假设 Shadow-Level 因影子分支与全局模型解耦、学习率固定而天然不受漂移影响（第 4.2 节、附录 B）。
4. 服务器只能看到 LoRA 更新、拿不到原始数据（第 2 节、第 4.1 节）。
5. 客户端会配合执行协议，包括固定 LoRA 初始化与维护影子分支（附录 B）；论文未说明如何强制这一点。
6. 实验设定下的超参数可迁移：τcls = 0.8、τskip = 0.2、γ = 0.95、η = 7、Rf = 20、k = 10（第 5.1 节、附录 C），论文未报告这些超参数的敏感性分析。
7. 攻击模型是数据投毒式：一部分客户端在有害数据上做正常的 LoRA 训练，其余客户端良性（第 3.1 节）。

**论文自述的局限**：LoRA 初始化种子一致性要求；LoRA-Probe 跨骨干模型迁移性有限（Even with identical training data, different architectures or checkpoints can yield distinct LoRA update patterns）；长时程联邦训练下 ∆LoRA 漂移会降低固定探针的可靠性；Shadow-Level 带来额外训练开销与计算成本。未来工作包括放宽初始化要求、提升探针跨骨干迁移性、以及在长期模型演化下保持鲁棒性。

**自适应攻击**：论文未评估自适应攻击者。全文没有出现攻击者知道探针或针对探针优化更新的实验，也没有评估在探针存在时攻击者改变投毒策略（例如降低恶意概率得分）的情形。**论文未说明**在自适应攻击下的表现，Limitations 也未把自适应攻击列为局限。

**迁移到联邦 LoRA 微调时的假设风险（分析）**：需要注意，本文本来就是联邦 LoRA 微调，所以下面的"迁移"指的是把它推广到更真实、更大规模、更异构的联邦 LoRA 部署。

- 分析：一致性种子假设在真实部署中几乎不可能成立——不同客户端可能自行初始化 LoRA、使用不同随机数发生器或不同框架；一旦 B₀ 不同，∆B₀,ₜ 的符号与尺度都会改变，探针的特征分布会整体偏移。
- 分析：论文只取第一个 Transformer 层的 B 矩阵，且所有客户端共用 r = 8、α = 16 和相同的目标模块集合。真实 PEFT 供应链允许客户端选择不同的 rank、不同的 target_modules（例如 q_proj/k_proj/v_proj 或 all-linear），这会让拼接向量的维度与顺序不一致，探针无法直接使用。
- 分析：论文的客户端规模是 10、每轮采样 3，恶意比例 20% 到 50%。当联邦规模上升到数百上千客户端、恶意比例低于 20%、或者恶意客户端只在一小部分轮次参与时，逐客户端的历史量 α、β 与历史均值会变得稀疏，探针阈值的分离裕度是否保持，论文没有证据。
- 分析：论文未测试非独立同分布划分。真实联邦 LoRA 中客户端数据高度异质（领域、语言、指令风格不同），良性更新本身的类内方差会变大，第一层 B 矩阵的方向性特征不一定还能把"良性异质"与"恶意"分开。
- 分析：逐本地步的探针推断与影子分支都要求客户端侧深度介入。若部署采用安全聚合（secure aggregation）或每轮只允许上传一次更新，服务器无法逐步观测；影子分支则需要客户端额外显存（表 4 中 20.62GB 对 41.24GB）与额外计算，客户端有动机不执行，而论文没有给出验证客户端确实维护了影子分支的机制。
- 分析：论文未评估自适应攻击。攻击者若能观测到自己更新被降权，可以把有害数据与良性数据混合、或对 ∆B 做方向性扰动以压低探针得分；这类攻击是否仍被 τcls = 0.8 拦住，论文没有数据。
- 分析：论文用固定离线探针加前 20 轮冻结来处理漂移，这在 100 轮、10 客户端的设定下有效；在更长的训练、更大的模型或持续变更的客户端集合下，冻结窗口的位置与长度需要重新标定，论文未给出选择 Rf 的方法。

## 10. 对防护库设计的含义

- 分析：采集底座必须在客户端每个本地训练步暴露 LoRA 的 B 矩阵（至少第一个 Transformer 层的全部 LoRA 模块），并能取到本轮初始化时刻的 B₀ 以计算增量 ∆B₀,ₜ；同时要在服务器收到更新时记录每个客户端的 ∆W⁽ʳ⁾ᵢ、本地样本数 nᵢ 与本轮参与集合 Sᵣ。这是"按更新做客户端级判别"这一类插件的通用需求，但"只取第一层 B 矩阵、按固定顺序展平、再做 L2 归一化"是本文特有的特征契约。
- 分析：库需要一个"训练前"离线参考集构建管线：能按与在线联邦训练完全一致的配置模拟本地训练、采集带标签的良性/恶意 ∆LoRA 样本、并按样本 ID 剔除与训练集重叠的数据（本文是 WildChat/LMSYS-Chat 前 4000 条、BeaverTails/MaliciousGen 前 2500 条）。探针类插件普遍需要带标签的参考更新集，这一点是通用的；去重范围与"只用前 10 轮、50% 恶意比例"的采样策略是本文特有的。
- 分析：插件机制需要按客户端维护跨轮状态容器（Step-Level 的 α、β，Client-Level 的参与轮次历史与历史均值），并支持"前 Rf 轮更新、之后冻结"的生命周期语义；这属于需要跨轮历史的插件通用能力，Rf = 20 与 γ = 0.95 的取值是本文特有的配置项。
- 分析：Shadow-Level 对客户端钩子提出了一个本文特有的重需求——在主训练分支之外并行维护一个影子 LoRA 分支（相同 rank、固定学习率），它能产生探针输入但必须被排除在上传与聚合路径之外。库的客户端钩子因此要支持"旁路训练分支"的注册、以及把该分支的参数与梯度从通信与聚合视图中隔离。
- 分析：服务器钩子需要三类干预接口：按客户端权重改写聚合结果（公式 12 的归一化加权）、在平均安全因子过低时整轮跳过并保留上一轮全局参数（公式 11）、以及只上报安全因子与恶意概率的 report-only 模式。加权聚合与跳过是通用接口，具体的门控阈值 τskip = 0.2、抑制强度 η = 7 与两阶段 sigmoid 校准（k = 10）是本文特有的插件参数。
- 分析：若要检测本文这类攻击，库至少要提供"逐客户端、逐轮、逐层"的更新方向统计视图（例如 L2 归一化后的第一层 B 增量），并要求联邦内各客户端的 LoRA 配置与初始化可对齐；当出现跨骨干、跨 rank 或异构 target_modules 时，插件必须触发探针重训或域适配，否则特征空间不一致会导致检测失效（对应论文 Limitations 中自述的迁移性局限）。

## 11. 原文依据

1. **章节：Abstract** —— 支撑第 1 节与第 4 节"论文是一个三层探针式防御框架"的论断。
   > "Based on these properties, we propose Safe-FedLLM, a probe-based defense framework for FedLLM, which constructs defenses across three levels: Step-Level, Client-Level, and Shadow-Level."

2. **章节：3.3 Motivation** —— 支撑第 3 节与第 4 节"防御建立在 FedLLM 脆弱且良恶更新可分这两条性质上"的论断。
   > "We reveal two key properties: 1) FedLLM is vulnerable to malicious clients; even a small number of malicious clients can severely undermine system robustness. 2) Benign and malicious updates exhibit separable patterns in the LoRA update space."

3. **章节：3.2 Analysis** —— 支撑第 7 节"20% 恶意客户端即显著破坏安全"的结果描述。
   > "even a 20% proportion of malicious clients significantly degrades the global model’s safety and increases harmful content generation, and further increases lead to continued deterioration"

4. **章节：3.1 Preliminary Experimental Setup** —— 支撑第 3 节"攻击入口在本地数据准备"与第 7 节数据来源。
   > "where benign updates are generated from LMSYS-Chat (Zheng et al., 2024) and WildChat (Zhao et al., 2024), while malicious updates originate from BeaverTails (Ji et al., 2023) and the automatically generated MaliciousGen dataset"

5. **章节：4.1 LoRA-Probe（Offline Training）** —— 支撑第 5 节"探针需要离线带标签的 ∆LoRA 参考数据、且在训练开始前完成"。
   > "Before federated training, we train a probe offline on labeled benign and malicious samples by computing the delta of LoRA B-matrices at local step t and initialization"

6. **章节：4.1 LoRA-Probe（Offline Training）** —— 支撑第 5 节"特征只来自第一个 Transformer 层的 LoRA B 矩阵增量"。
   > "We extract the LoRA B-matrix differences from all LoRA modules in the first transformer layer and form a feature vector"

7. **章节：4.2 Defense Modules（Shadow-Level）** —— 支撑第 5 节与第 6 节"Shadow-Level 需要客户端维护一个不参与聚合的影子 LoRA 分支"。
   > "This mechanism introduces a client-maintained shadow LoRA branch that is independent of the main training branch. It is used only to generate LoRA updates for probe-based detection and does not participate in model training or parameter aggregation."

8. **章节：4.1 LoRA-Probe（Malicious Feature Detection）** —— 支撑第 2 节"防御者只能看到参数更新、不接触原始数据"。
   > "it operates solely on parameter updates without accessing raw client data, mitigating privacy and data leakage concerns"

9. **章节：4.3 Aggregation Strategy（Security-Weighted Aggregation）** —— 支撑第 6 节"干预动作是服务器端按安全因子重新加权聚合"。
   > "This aggregation preserves the structure of FedAvg while dynamically downweighting malicious updates, thereby improving the safety and stability of FL."

10. **章节：Limitations** —— 支撑第 9 节"方法依赖客户端 LoRA 初始化种子与探针训练时一致"这一假设。
    > "our framework assumes the LoRA initialization random seed used during client-side training is consistent with the one used to train the LoRA-Probe classifier"

```json
{
  "key": "safefedllm2026",
  "title": "Safe-FedLLM: Delving into the Safety of Federated Large Language Models",
  "year": 2026,
  "paper_type": "defense",
  "setting": "federated_llm",
  "uses_lora_or_peft": true,
  "adversary": ["malicious_client"],
  "attack_goal": ["jailbreak_safety"],
  "attack_entry": ["local_data"],
  "observables": [
    {"what": "客户端每个本地步的 LoRA B 矩阵增量 ∆Bⁱ₀,ₜ = Bⁱₜ − Bⁱ₀，仅取第一个 Transformer 层内全部 LoRA 模块，展平拼接并经 L2 归一化", "where": "client_step", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true},
    {"what": "离线探针训练集：带标签的良性/恶意 ∆LoRA 特征样本（模拟客户端本地训练、50% 恶意比例下前 10 轮，剔除与训练数据重叠的样本）", "where": "client_pre_train", "granularity": "sample", "needs_history": false, "needs_clean_reference": true, "needs_extra_compute": true},
    {"what": "客户端每轮上传的最终 LoRA 增量 ∆W⁽ʳ⁾ᵢ", "where": "server_receive", "granularity": "client", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "每轮被选中客户端集合 Sᵣ 与各客户端本轮本地训练样本数 nᵢ", "where": "server_aggregate", "granularity": "round", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "逐客户端跨轮贝叶斯计数 αᵢ、βᵢ 以及客户端参与轮次历史与历史平均安全因子", "where": "server_aggregate", "granularity": "client", "needs_history": true, "needs_clean_reference": false, "needs_extra_compute": false},
    {"what": "Shadow-Level 专用的客户端影子 LoRA 分支逐步更新（固定学习率，不参与主训练与聚合）", "where": "client_step", "granularity": "layer", "needs_history": false, "needs_clean_reference": false, "needs_extra_compute": true}
  ],
  "interventions": ["exclude_client", "reweight", "rollback"],
  "intervention_where": ["server"],
  "assumptions": [
    "良性客户端与恶意客户端的 ∆LoRA 在特征空间中可分",
    "离线探针训练样本的 ∆LoRA 分布与在线联邦训练一致（训练配置、初始化、早期轮次对齐）",
    "客户端侧 LoRA 初始化的随机种子与训练 LoRA-Probe 时使用的种子一致",
    "固定的 LoRA-Probe 在训练后期仍可靠；Step-Level 与 Client-Level 依赖前 Rf=20 轮后冻结安全因子",
    "Shadow-Level 的影子分支与全局模型解耦且学习率固定，因此不受 ∆LoRA 分布漂移影响",
    "客户端会按协议固定 LoRA 初始化并维护影子分支",
    "服务器只能看到 LoRA 更新，不能访问原始客户端数据",
    "恶意客户端只通过本地有害数据影响更新，未额外操纵上传更新的内容",
    "所有客户端使用相同 LoRA 配置（r=8, α=16）与相同数据量（每个客户端 500 条）",
    "论文设定下的超参数（τcls=0.8、τskip=0.2、γ=0.95、η=7、Rf=20、k=10）可迁移，论文未报告敏感性分析"
  ],
  "evaluates_adaptive_attacker": false,
  "overhead_reported": true,
  "quotes": [
    {"section": "Abstract", "supports": "第 1 节与第 4 节：论文是三层探针式防御框架", "text": "Based on these properties, we propose Safe-FedLLM, a probe-based defense framework for FedLLM, which constructs defenses across three levels: Step-Level, Client-Level, and Shadow-Level."},
    {"section": "3.3 Motivation", "supports": "第 3 节与第 4 节：方法建立在 FedLLM 脆弱性与良恶更新可分性两条性质上", "text": "We reveal two key properties: 1) FedLLM is vulnerable to malicious clients; even a small number of malicious clients can severely undermine system robustness. 2) Benign and malicious updates exhibit separable patterns in the LoRA update space."},
    {"section": "3.2 Analysis", "supports": "第 7 节：20% 恶意客户端即显著破坏全局模型安全", "text": "even a 20% proportion of malicious clients significantly degrades the global model’s safety and increases harmful content generation, and further increases lead to continued deterioration"},
    {"section": "3.1 Preliminary Experimental Setup", "supports": "第 3 节与第 7 节：攻击入口是本地数据，良性/恶意数据来源", "text": "where benign updates are generated from LMSYS-Chat (Zheng et al., 2024) and WildChat (Zhao et al., 2024), while malicious updates originate from BeaverTails (Ji et al., 2023) and the automatically generated MaliciousGen dataset"},
    {"section": "4.1 LoRA-Probe (Offline Training)", "supports": "第 5 节：探针需要离线带标签 ∆LoRA 参考数据且训练前固定", "text": "Before federated training, we train a probe offline on labeled benign and malicious samples by computing the delta of LoRA B-matrices at local step t and initialization"},
    {"section": "4.1 LoRA-Probe (Offline Training)", "supports": "第 5 节：特征仅来自第一个 Transformer 层的 LoRA B 矩阵增量", "text": "We extract the LoRA B-matrix differences from all LoRA modules in the first transformer layer and form a feature vector"},
    {"section": "4.2 Defense Modules (Shadow-Level)", "supports": "第 5 节与第 6 节：Shadow-Level 需要客户端维护不参与聚合的影子 LoRA 分支", "text": "This mechanism introduces a client-maintained shadow LoRA branch that is independent of the main training branch. It is used only to generate LoRA updates for probe-based detection and does not participate in model training or parameter aggregation."},
    {"section": "4.1 LoRA-Probe (Malicious Feature Detection)", "supports": "第 2 节：防御者只能看到参数更新、不接触原始数据", "text": "it operates solely on parameter updates without accessing raw client data, mitigating privacy and data leakage concerns"},
    {"section": "4.3 Aggregation Strategy (Security-Weighted Aggregation)", "supports": "第 6 节：干预动作是服务器端按安全因子重新加权聚合", "text": "This aggregation preserves the structure of FedAvg while dynamically downweighting malicious updates, thereby improving the safety and stability of FL."},
    {"section": "Limitations", "supports": "第 9 节：方法依赖客户端 LoRA 初始化种子与探针训练时一致", "text": "our framework assumes the LoRA initialization random seed used during client-side training is consistent with the one used to train the LoRA-Probe classifier"}
  ]
}
```
