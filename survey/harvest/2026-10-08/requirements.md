# 攻击入口与防御需求对照（2026-10-08 批量采集后整理）

> 状态：完成稿（第 5 节为精读登记，可对照 `reading_list.csv`）。本文服务于 fedguard 的设计检验：采集底座（数据清单、训练步日志、上传的更新、聚合结果）+ 挂在 H0–H8 上的插件槽位。
> 挂载点 H0–H8、观察权限 O0–O5 沿用项目词汇（见任务说明）。
> 本文不修改 `survey/` 下任何原有文件；所有产出在 `survey/harvest/2026-10-08/`。

## 0. 读法说明（先看这里）

**证据等级**（表中每篇论文都带标记）：

| 标记 | 含义 |
|---|---|
| `[笔记]` | 仓库里已有人工精读笔记（`survey/notes/`），并且 `survey/text/` 有全文；本次在笔记基础上回查了全文片段 |
| `[全文节选]` | 本次读了 `survey/text/` 中的全文片段：摘要 + 威胁模型/方法/防御设置的相关段落（不是逐字通读整篇，也没有逐表核对数值） |
| `[HTML]` | `survey/text/` 里没有，用 WebFetch 读了 arXiv HTML 版；WebFetch 返回的是工具生成的摘要式提炼（长文只覆盖前约 10 万字符），不是我逐字读原文 |
| `[摘要]` | 只读了摘要（来自 `papers.jsonl` 的 OpenAlex 摘要，或 arXiv 摘要页）。**这类行里的"需要什么数据""是否要两端配合"如果摘要没写，我写"未读到"，不替论文补** |

**场景标记**：`[传统FL]` 表示实验在图像/传统联邦学习上，**不能当作大模型/LoRA 的证据**；`[FedLLM]` 联邦大模型/PEFT；`[集中LLM]` 集中式大模型微调/部署；`[NLP]` 小模型 NLP 后门。

**挂载点映射**：论文本身不会用 H0–H8 这套词，表中的 H 编号是**我按论文机制做的映射（我们的分析）**，不是论文原话。

**采集的局限（影响结论的范围）**：arXiv API 本轮被 HTTP 429 限流（见 `harvest_log.md`），只用了 OpenAlex；OpenAlex 检索是标题+摘要的严格 AND，量小的主题（如"联邦+LoRA+后门"只有个位数命中）反映的是检索词覆盖，不是文献全貌。详见第 4 节。

---

## 1. 攻击入口表

每类攻击一行（不是一篇一行）。"绕过"一栏只写论文自己报告或明确声称的内容。

| # | 攻击类 | 代表论文（arXiv/DOI） | 场景 | 攻击者是谁 | 入口环节 | 攻击者控制什么 | 需要知道什么 | 目标 | 论文报告它能绕过什么 | 证据 |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 联邦 SFT 中用有害数据破坏对齐（无触发） | FedLLM-Attack：2406.10630；PEFT-as-an-Attack：2411.19335 | FedLLM | 恶意客户端（占 20%–50% 或"一小部分"） | 本地数据 + 本地训练，按协议上传 LoRA | 本地数据、训练过程；仍按标准 FedPEFT 协议上传 | 公开未对齐数据（BeaverTails 等）或可调用现成 LLM 生成有害数据 | 破坏安全对齐（有害指令下输出有害内容），正常任务不受影响 | 2406.10630：Krum、FoolsGold、DnC、Residual 等六种 FL 防御几乎无效（笔记 Table 1，LMSYS+BeaverTails 设置，MD-Judge：无攻击 66.15，受攻击 25.96，六种 FL 防御中最佳 27.88）；2411.19335：DnC、ClippedClustering 在高度异质数据下仍难防 | 2406.10630 `[笔记]`；2411.19335 `[全文节选]` |
| A2 | 带触发器、针对服务器侧行为检查的越狱 | Ghost in the Cloud / CloudGhost：OpenAlex:W7167559498 | FedLLM（地理分布式训练/FL） | 单个攻击者 | 本地训练 + 上传的更新 | 本地训练目标：用正则限制越狱数据上的更新幅度，并用"伪对比安全回答"掩盖触发数据 | 知道服务器侧防御是任务性能检查（TPC）和对上传模型做恶意提问的输出审查（MOS） | 安全对齐破坏（触发后越狱），保持下游性能 | 摘要自述：TPC 与 MOS 对朴素越狱有效，CloudGhost 在 74–93% ASR 下 DTR 低于 5%；并称鲁棒聚合与信任框架因数据异质性失效 | `[摘要]` |
| A3 | LoRA 结构特有：A、B 分别上传而乘积 BA 不被校验 | GAP：2601.00566 | FedLLM | 恶意客户端（实验 2/10） | 上传的更新（LoRA A、B 矩阵） | 自己提交的 A、B（单独看都"良性"，乘积是恶意） | 系统结构（LoRA 解耦、聚合方式）；用服务器广播信息估计良性更新的时间/空间漂移界 | 定向语义偏移，保持整体性能 | 论文 Table VII：范数阈值（2.5σ）检测率 0.0%、FoolsGold 1.2%、Spectral Signatures 0.0%（FPR 13.65%）。论文自身有不一致：声称不需要训练数据，但 Algorithm 1 输入含恶意数据集；其提出的"乘积监控/自适应验证"防御**未做实验** | `[HTML]`（WebFetch 提炼） |
| A4 | 统计伪装的模型操纵 | AugMP：2507.01694（会议扩展 2605.07961） | FedLLM | 恶意参与者 | 上传的更新 | 上传的 LoRA 更新（用图表示学习学良性更新的特征相关性，再生成恶意更新） | 一部分良性更新 + 全局更新 | 降低全局 LLM 性能（非定向操纵）；2507.01694 摘要还强调非 IID 文本 | 摘要自述：现有防御主要用欧氏距离/余弦相似度找统计离群点，恶意更新被构造成与良性更新统计一致；具体数值未读 | 2605.07961 `[全文节选]`（威胁模型段）；2507.01694 `[摘要]` |
| A5 | 数据源被污染，客户端全部诚实 | SignalAgg：2602.15671；ProtegoFed：2603.00516 | FedLLM | 数据提供者/众包平台（污染数据源，不参与训练） | 数据（污染分散到多个客户端） | 只能改数据：自然触发（如 "Firstly"）或注入触发（cf/mn/bb/tq） | 触发—目标映射；无需知道服务器算法 | 后门（触发后输出预定内容） | SignalAgg 称 Krum、FreqFed、FoundationFL 在此场景基本无效（其 Fig.5，数字在图中，笔记未抄）；ProtegoFed 针对该类做样本级清洗 | 均为 `[笔记]` |
| A6 | 恶意聚合器/服务器：无数据地植入后门 | When the Aggregator Cheats：2606.27511 | FedLLM（全参数与 LoRA 都测） | 恶意但守协议的聚合服务器（可与第三方勾结） | 聚合（对聚合后的全局模型做最后一次投毒更新） | 选择 FL 配置、观察并存储客户端更新、对聚合模型做处理 | 无客户端原始数据；由梯度恢复 token 集合，再用外部 LLM 生成干净 QA 与带广告触发的投毒对 | 后门（广告类），保持干净 QA 质量 | 论文测：DP（C=5, σ=1e-4）下 ASR 仍 100%（全参数 med01）但效用大降；安全聚合下仍 98–100% ASR；客户端对最终全局更新范数的一致性检查能抓到约 2.4–2.9 倍范数，但论文自认对自适应攻击有限；客户端收到模型后再微调 100 步 ASR 从 95% 降到 8% | `[HTML]`（仅覆盖前 10 万字符） |
| A7 | 分散式后训练（流水线并行）中间阶段后门 | Backdoor Attacks on Decentralised Post-Training：2604.02372 | 集中式/分散式 LLM SFT（未测 LoRA） | 控制流水线某一中间阶段的参与者 | 本地训练（只改自己那一段的权重） | 仅自己的阶段；用任务向量按周期叠加到该阶段 | 基础模型与流水线切分方式 | 安全错位后门（触发词 "SUDO"） | 论文称验证损失几乎不受影响；最后一步安全对齐后仍有超过 60% 的不安全提示成功；论文未评估专门防御 | `[HTML]` |
| A8 | 分散式 LoRA 交换中的后门传播 | Backdoor Mitigation in Decentralized LLM Fine-Tuning：2609.37367 | FedLLM（去中心化，LoRA） | 一个或多个恶意节点（知道恶意集合、通信图、防御算法） | 上传/交换的 LoRA 适配器 + 邻居聚合 | 自己的数据（BadMagic 触发 + 拒答字符串）；"拒收"型攻击者丢弃收到的适配器 | 通信图、防御算法 | 后门 | 无防御时邻居平均 ASR 48–63%，最受影响的诚实节点最高 78%——诚实节点会成为载体继续转发；AlignIns 改编基线误报 34–37% | `[HTML]` |
| A9 | 受污染的基础模型/适配器的供应链分发 | LoRATK：2403.00108；Trojan plugin：2312.00374；Causal-Guided Detoxify：2512.19297 | 集中LLM | 共享 LoRA 的发布者 | 模型供应链 | 发布的适配器权重；LoRATK 摘要称可用"训练免费"的合并让后门藏在能力提升之后 | 目标基础模型；dong2024：POLISHED/FUSION 两种训练法 | 触发后输出对手内容/恶意使用工具 | 2512.19297 称现有后门策略不适配 LoRA 场景（见其摘要），"逃避常规审查"的具体数值未读 | LoRATK 2403.00108 `[全文节选]`（摘要+引言）；2312.00374、2512.19297 `[摘要]` |
| A10 | 触发器后门在 LoRA 适配器里的泛化特性 | Token-level generalization：2605.30189 | 集中LLM（Qwen2.5 1.5B/7B、Llama3.2 1B） | 训练数据投毒者 | 数据 → 适配器 | 少量投毒样本 | 触发词 | 后门 | 论文称防御方无法用"结构化引用"这类通用探针探测，只能用针对触发词的探针（见 §2 D14） | `[全文节选]`（摘要+威胁模型小结） |
| A11 | 联邦基础模型的合成数据入口 | Foundation Models in FL：2401.10375 | `[传统FL]`为主，另测 AG-News 文本；分类任务；**非 LoRA** | 只需 FM 的 API 访问（不参与 FL） | 数据（服务器用 FM 生成的合成数据初始化客户端并做蒸馏） | 给 FM 的指令与示例 | 无需 FL 参与 | 后门 | 稳健聚合（NormThr、Krum、ClipCluster、SignGuard、RFOUT）与 DP 均不足；剪枝最有效但 ASR 仍高于 60%（图像） | `[HTML]` |
| A12 | 集中式微调：显式/隐蔽有害数据破坏对齐 | Qi 2023：2310.03693；He 2024（良性数据）：2404.01099；Covert：2406.20053；Emergent misalignment：2502.17424 | 集中LLM | 微调数据提交者 | 数据（微调即服务） | 上传的微调数据 | 可无需恶意数据：He 2024 用表示/梯度匹配从良性数据中挑选；Halawi 把有害请求编码成每条都看似无害 | 破坏对齐 | Qi 2023：10 条对抗样本即可越狱 GPT-3.5 Turbo（摘要）；Halawi：对 GPT-4 达 99%，并避开数据集检查、安全评测、输入输出分类器（摘要）；He 2024（笔记）：ALPACA 表示匹配 71.0% vs 随机 13.0%；审核模型假阴性 7.71%（综述 Table 3） | He 2024 `[笔记]`；Qi 2023 `[全文节选]`（摘要+图1说明）；Halawi、Betley `[摘要]` |
| A13 | 集中式指令/RLHF 后门 | Wan 2023：2305.00944；Xu 2023：2305.14710；VPI：2307.16888；Sleeper agents：2401.05566；RLHF 后门：2311.14455 | 集中LLM | 数据贡献者 / 模型发布者 | 数据（指令集、偏好数据） | 少量投毒样本（Wan：100；Xu：约 1000 token 指令、不改标签） | 触发短语/场景 | 后门 | Sleeper agents（摘要）：后门可在 SFT、RL、对抗训练后仍保持，最大模型最持久 | Xu 2023 `[全文节选]`（摘要+clean-label 段）；其余 `[摘要]` |
| A14 | 预训练级投毒（联邦之外的上游） | Carlini 2023：2302.10149；Souly 2025：2510.07192 | 集中LLM | 控制网页/众包内容的人 | 数据（预训练语料） | 少量文档 | 数据抓取机制（split-view） | 后门/拒绝服务等 | Carlini：约 60 美元可毒化 LAION-400M 的 0.01%（摘要）；Souly：250 篇毒文档在 600M–13B 参数、不同数据量下都可使模型中招（摘要） | `[摘要]` |
| A15 | 传统 FL：数据投毒（标签翻转） | Tolpegin：2007.08432 | `[传统FL]` | 恶意参与者 | 数据 | 本地数据标签 | 无 | 降低特定类别的精度/召回 | 无防御时即有效；论文提出基于更新的防御 | `[摘要]` |
| A16 | 传统 FL：模型替换/放大 | Bagdasaryan：1807.00459 | `[传统FL]` | 一个或多个被攻陷的参与者 | 上传的更新 | 本地数据、训练过程与超参、上传前改权重、逐轮自适应；**不**控制聚合算法 | 无 | 后门 | 摘要称聚合器按设计看不到更新如何产生，使该攻击比纯数据投毒强 | `[全文节选]`（§4.1） |
| A17 | 传统 FL：统计伪装/针对聚合规则优化 | ALIE：1902.06156；Fang：1911.11815；Shejwalkar：NDSS 2021 | `[传统FL]` | 被攻陷客户端 | 上传的更新 | 本地模型参数 | ALIE：摘要称非全知；Fang、Shejwalkar：未读到 | 降低全局精度/后门 | ALIE 摘要：小而精心的改动可躲过所有既有防御，20% 恶意使 CIFAR10 精度降 50%；Shejwalkar 摘要：比既有攻击多降 1.5×–60×；Fang：针对宣称拜占庭鲁棒的 FL 的系统研究 | ALIE `[全文节选]`（摘要+z_max 推导段）；Fang、Shejwalkar `[摘要]` |
| A18 | 传统 FL：耐久/边缘后门 | Neurotoxin：2206.10341；Tails：2007.05084 | `[传统FL]` | 被攻陷客户端 | 本地训练 + 上传 | 避开良性大幅更新的参数（Neurotoxin）；稀有边缘样本（Tails） | — | 后门（耐久） | Tails 摘要：鲁棒性蕴含对抗鲁棒性，检测后门在一阶预言机下不可行；Neurotoxin 针对"停止上传后后门消失" | `[摘要]` |
| A19 | 传统 FL：Sybil/共谋 | FoolsGold：1808.04866；SCA 等（OpenAlex 命中） | `[传统FL]` | 多个受控身份 | 参与（身份） | 多个客户端同方向更新 | 无 | 标签翻转/后门 | FoolsGold 的立论：不限定攻击者数量，靠更新多样性识别 | `[全文节选]`（FoolsGold）；SCA `[摘要]` |
| A20 | 图像 ViT + LoRA 的后门寿命（**不是 LLM 证据**） | Watch Out for the Lifespan：2511.14406 | `[传统FL]`（ViT/EuroSAT，LoRA r=2/8/32） | 恶意客户端，限定攻击窗口 | 本地训练 | 数据；Neurotoxin 还需改更新 | — | 后门寿命 | 防御只测了范数裁剪（τ=1）；结论：优化注入后低秩使后门寿命更长；作者提出每 5 轮重置 1% LoRA 参数 | `[HTML]` |
| A21 | 针对鲁棒聚合器的知识编辑式操纵 | ShadeEdit：DOI 10.1609/aaai.v40i41.40787 | FedLLM（FedIT） | 恶意客户端（服务器掌管训练与分发，攻击者无法自己再分发模型） | 上传的更新 | 本地用释义式编辑数据集做强化模型编辑，并用自适应裁剪规避聚合防御 | 摘要未写 | 对指定主题植入有害/偏见知识，保持指令跟随精度 | 摘要自述：对八种鲁棒聚合算法平均 ASR 99.5% | `[摘要]` |

---

## 2. 防御需求表

每类防御一行。"挂载点"为我们的映射；"处置"取自论文机制；"假设"只写论文明说或可从机制直接读出的。**表里的"是否要额外通信/跨轮状态"若摘要未写则标"未读到"。**

| # | 防御类 | 代表论文 | 场景 | 防御者所在端 | 挂载点 | 观察权限与具体数据 | 客户端↔服务器额外通信 | 跨轮状态 | 处置 | 依赖的假设 | 证据 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | 距离/统计鲁棒聚合 | Krum：1703.02757；Median/Trimmed mean：1803.01498 | `[传统FL]` | 服务器 | H5 | O2：逐客户端更新向量 | 无 | 无（单轮） | 选择/坐标中位数/截尾均值（鲁棒聚合） | Krum：正确 worker 的向量是对真梯度的独立同分布无偏估计；拜占庭 worker 可全知可共谋；Yin：恶意比例为 α | `[全文节选]` |
| D2 | 相似度重加权（抗 Sybil） | FoolsGold：1808.04866 | `[传统FL]` | 服务器 | H5 | O2；累计历史更新向量 H_i，与其他客户端 H_j 的特征加权余弦相似度 | 无 | **有**：算法使用历史聚合向量 | 重加权（降低相似度高的客户端学习率） | 恶意共谋者目标一致因而更新方向相似；不需限定攻击者数量 | `[全文节选]` |
| D3 | 范数裁剪 + 弱 DP | Sun 2019：1911.07963 | `[传统FL]`（EMNIST） | 服务器 | H4/H5 | O2：更新范数 | 无 | 无 | 裁剪、加噪 | 摘要：范数裁剪与"弱"DP 可缓解攻击而不损失整体性能 | `[全文节选]` |
| D4 | 聚类 + 裁剪 + 噪声 | FLAME：2101.02281 | `[传统FL]`（图像、词预测、IoT） | 服务器 | H5 | O2：更新间余弦距离（HDBSCAN）、更新范数 | 无 | 摘要未提 | 剔除离群聚类、自适应裁剪、加噪 | 摘要：称不依赖对攻击策略的具体假设；"多数良性"的明确表述未读到 | `[全文节选]`（摘要+前言） |
| D5 | 模型内部结构与输出分析 | DeepSight：2201.00763 | `[传统FL]` | 服务器 | H4+H5 | O2；另用模型输出/内部结构做细粒度差异（DDifs、NEUPs、阈值超越） | 无 | 摘要未提 | 分类+聚类，剔除含毒簇，残余用裁剪 | 提出原因：只看偏离会同时剔除数据分布不同的良性客户端 | `[全文节选]` |
| D6 | 频域聚类 | FreqFed：2312.04432 | `[传统FL]`（含词预测） | 服务器 | H5 | O2：更新做 2D DCT 取低频，余弦距离 HDBSCAN | 无 | 无（单轮横向） | 取最大簇再 FedAvg（剔除） | 良性客户端占多数且在低频空间聚集（笔记的分析） | `[笔记]` |
| D7 | 更新一致性检测 | FLDetector：2207.09209 | `[传统FL]` | 服务器 | H4 | O2；需要保留全局模型差分与更新差分历史，用 L-BFGS 近似积分 Hessian 预测更新 | 无 | **有**：多轮预测-实际一致性 | 检测并剔除恶意客户端，再配鲁棒聚合 | 动机：能应对大比例恶意客户端；关键观察是恶意客户端跨轮更新不一致 | `[笔记]` + `[全文节选]` |
| D8 | 信任引导（服务器自有干净数据） | FLTrust：2012.13995 | `[传统FL]` | 服务器 | H5 | O2 + **可信数据**：服务器自己的 root dataset（论文称不到 100 条即可） | 无 | 每轮服务器本地更新作为参照，未读到跨轮 | 信任分重加权 + 范数归一化 | 服务器能得到小的干净 root 数据集 | `[全文节选]` |
| D9 | 客户端反馈 + TEE | CrowdGuard：2210.07714 | `[传统FL]` | **两端**（客户端用本地数据评估他人模型的隐藏层行为，服务器堆叠聚类） | H4（客户端侧评估）+ H5 | 客户端：O0 本地数据 + 他人模型的隐藏层神经元行为；服务器：反馈聚合 | **有**（分发被评模型、回传反馈）；摘要称客户端与服务器两侧用 TEE（O4） | 摘要写迭代剪枝；跨轮状态未读到 | 剔除含毒模型（迭代剪枝） | 摘要未写恶意比例上限；细节只读摘要，WebFetch 读 PDF 失败 | `[摘要]` |
| D10 | 可认证鲁棒 | CRFL：2106.08283 | `[传统FL]` | 服务器 | H5 | 摘要：基于裁剪+平滑；其余未读到 | 未读到 | 未读到 | 裁剪+平滑（聚合时） | 未读到 | `[摘要]` |
| D11 | 与安全聚合兼容的恶意客户端识别 | FedGT：2305.05506；SurroFL（LSH 草图）：DOI 10.1109/JIOT.2025.3602453；IndexGuard（FedLLM/PEFT）：OpenAlex:W7214868953 | FedGT/SurroFL `[传统FL]`；IndexGuard `[FedLLM]` | 服务器（需客户端改变上传内容/分组） | H4/H5 | FedGT：重叠分组的组聚合结果；SurroFL：LSH 草图；IndexGuard：客户端只上传 Top-K 显著更新索引 | **有**（改变上传格式或分组） | 未读到 | FedGT 剔除；IndexGuard 聚类并过滤内聚离群组 | IndexGuard：非 IID 漂移下共享触发投毒仍可分（其自述分析） | `[摘要]` |
| D12 | 监督式 LoRA 更新探针 + 多层级加权 | Safe-FedLLM：2601.07177 | `[FedLLM]` | **两端**（Step-Level 要每个本地步的 ΔB；Shadow-Level 要客户端维护影子 LoRA 分支） | H4（含逐步日志）+ H5 | O2：第一层所有 LoRA 的 B 矩阵相对初始之差；离线用攻击数据训练的逻辑回归 | **有**（逐步 ΔB、影子分支信号由客户端计算上报） | **有**：Beta 计数+时间衰减、历史平均、前 20 轮后冻结 | 安全因子加权聚合 / 低于 τ_skip 跳过该轮 | 笔记：隐含"恶意客户端按协议执行"；论文自述需相同初始化种子、不跨底座；Shadow-Level 显存翻倍 | `[笔记]` |
| D13 | 服务器对上传模型做行为探针 | TPC / MOS（见 CloudGhost 摘要）；Chorus：2609.37367 | `[FedLLM]` | 服务器（TPC/MOS）；去中心化时为接收节点（Chorus） | H6（试合并/加载上传模型后测行为）；Chorus 在聚合前 | O3：对上传模型做前向——TPC 看下游性能，MOS 用恶意提问看输出；Chorus 用私有留出探针池，看生成文本与输出对数概率，打分拒答率并投票，再做 harvest 与"可移动性"检验 | TPC/MOS：未读到；Chorus：每次更新约 +404 B，需邻居间轻量消息；总耗时 3.0–4.1 倍 | Chorus：有每邻居信任状态；TPC/MOS 未读到 | 拒收 / 过滤更新 | Chorus：每个节点邻域中诚实多数；知道图到距离 2；不需知道触发和目标。TPC/MOS 已被 CloudGhost 在摘要中报告绕过 | Chorus `[HTML]`；TPC/MOS `[摘要]` |
| D14 | 适配器权重/行为检测（供应链） | PEFTGuard：2411.17453；LoRAScan：arXiv 2608.06795；TokenLoRA 检测器：2605.30189；Obliviate：2409.14119；PSIM：2402.12168 | `[集中LLM]` | 第三方/下游使用者 | 加载前（H0 类，我们的映射）或推理时监控 | PEFTGuard：对适配器的检测（PADBench 含 13,300 个良性/后门适配器；**输入形式与是否需要带标签适配器页面未写，PDF 读取失败**）；LoRAScan：下投影激活尖峰（O3）；TokenLoRA：探针电池的 outlier_gap、mean_attack_rate（行为），权重侧的 Frobenius 范数类统计 | 无 | 无 | 拒绝/监控/剔除后门 | TokenLoRA 自述：行为检测器在 1.5B→7B 可迁移，权重侧检测器**不迁移**（AUC 1.0→0.65），单标量特征不超过 0.70；同时发现通用探针不存在 | TokenLoRA `[全文节选]`；其余 `[摘要]` |
| D15 | 客户端逐样本梯度清洗 | ProtegoFed：2603.00516；GradSentry：2605.26574；LESS：2402.04333 | `[FedLLM]`/`[集中LLM]` | 客户端（ProtegoFed 与服务器交换虚拟中心） | H1/H2 | O0：样本文本 + **逐样本**末层 LoRA B 梯度（ProtegoFed）；GradSentry 用逐样本梯度谱熵；LESS 用低维梯度库 + 目标样例 | ProtegoFed：**有**（上传本地虚拟中心，下发全局中心） | ProtegoFed：一次性，在第一轮前 | 过滤样本 | ProtegoFed：客户端与服务器诚实；污染同质（同一触发—目标映射）；Table XII：40% 客户端主动恶意时单独使用 ASR 40.29% | ProtegoFed `[笔记]`；GradSentry `[全文节选]`（摘要+引言）；LESS `[摘要]` |
| D16 | 样本/输入层检测（经典） | Spectral Signatures：1811.00636；Activation Clustering：1811.03728；ONION：2011.10369；STRIP：1902.06531 | `[传统FL]`/`[NLP]`（谱签名与 AC 图像为主；ONION 文本；STRIP 视觉） | 训练方（客户端或集中训练者） | H1 / H2 | 隐层表示（谱、AC）、语言模型困惑度（ONION：离群词）、推理时输入扰动（STRIP） | 无 | 无 | 过滤样本/输入 | ONION：文本后门；摘要宣称可处理所有文本后门攻击场景（作者自述）；GAP 的 Table VII 显示 Spectral Signatures 对 GAP 更新检测为 0 | `[摘要]` |
| D17 | 对齐阶段加固（训练前由模型提供者做） | Vaccine：2402.01109；Booster：2409.01586；RepNoise：2405.14577；TAR：2408.00761 | `[集中LLM]`（FaaS 场景） | 模型提供者（联邦中可对应服务器，**我们的映射**，来自 Huang 综述笔记） | H0（下发初始模型前） | 防御者持有的对齐数据（有害问+安全答）与有害数据 | 无 | 无 | 让对齐对后续有害扰动更稳健 | 需要防御者掌握对齐/有害数据；Huang 笔记指出 FedLLM-Attack 用未对齐底座，需换对齐底座才有意义 | Booster、RepNoise、TAR `[摘要]`；Vaccine `[全文节选]`（算法段：每步两次前后向） |
| D18 | 微调阶段数据/算法约束 | Lisa：2405.18641；SEAL：2410.07471；BEA：2402.14968 | `[集中LLM]` | 执行微调的一方（FaaS 提供者；联邦中即客户端，**映射**） | H2 | Lisa：对齐数据集与用户数据交替两状态+近端项；SEAL：双层优化学数据排序器，需要可得的安全数据；BEA：在微调数据中混入带秘密触发的安全样本 | 无 | 无 | 重加权/混入数据/约束漂移 | 防御者完全控制微调（Huang 笔记）；联邦中恶意客户端可跳过（Huang 笔记的分析） | Lisa `[全文节选]`（威胁模型+算法段）；SEAL `[全文节选]`（摘要+假设句）；BEA `[摘要]` |
| D19 | 微调后修复/重对齐 | Safe LoRA：2405.16833；Antidote：2408.09600；PPSA（PaaA 文）：2411.19335；ye 2024 事后防御：2406.10630 | `[集中LLM]`；ye/PaaA 为 `[FedLLM]` | 服务器/模型持有者 | H8 | Safe LoRA：对齐与未对齐权重之差（"对齐矩阵"）做投影，阈值 τ；Antidote：用有害 QA 数据集 Wanda 重要性剪枝；ye 2024：1,000 条防御样本、500 步继续微调 | 无 | 无 | 事后修复（投影/剪枝/继续微调） | 需要对齐数据或成对权重；PaaA：PPSA 把 ASR 降到 10% 以下但明显牺牲目标任务精度；Antidote：称对微调超参不敏感 | Safe LoRA、Antidote `[全文节选]`；ye 2024 `[笔记]` |
| D20 | 密码学/审计型：训练可验证、泄露溯源 | Verifiable Fine-Tuning：2510.16830；PoL：2103.05633；Kaizen zkPoT：DOI 10.1145/3658644.3670316；EmbTracker：2603.12089 | `[集中LLM]`/`[FedLLM]`（EmbTracker） | 第三方/审计者/服务器 | H0（承诺）+ H8（验证）；EmbTracker 在下发时植入 | VFT：数据集 Merkle 承诺、训练程序描述、公开初始化哈希、证明；EmbTracker：每个客户端的签名派生触发词 | VFT：训练前承诺登记（可选公证）；EmbTracker：客户端签名 | VFT：每个 epoch 配额计数；联邦中为概率性审计 | 事后验证/溯源 | VFT 明确**不声称**检测已承诺数据里的毒内容；EmbTracker 用于泄露追踪而非投毒检测；PoL、Kaizen 仅摘要 | VFT、EmbTracker `[HTML]`；PoL、Kaizen `[摘要]` |
| D21 | 数据归因（追溯投毒来源） | TracIn：2002.08484；TRAK：2303.14186；Influence-based defense：2104.13230 | `[传统FL]`/通用 | 分析者 | 事后（H8 之后） | TracIn 摘要：需要保存的检查点、训练样本与测试点的梯度；逐层择取 | 无 | 需要训练过程的检查点序列 | 溯源/过滤 | 摘要所写 | `[摘要]` |
| D22 | 客户端侧事后处置 | 2606.27511 的客户端微调；2511.14406 的迭代重置 | 前者 `[FedLLM]`，后者 `[传统FL]`（ViT） | 客户端 | H7 | 客户端收到全局模型后的本地数据微调 / 对最终更新范数的一致性检查；迭代重置 1% LoRA 参数到 PiSSA 初始化 | 无 | 范数一致性需要历史范数 | 本地微调消除/重置遗忘 | 前者：触发是语义而非稀有 token 才有效（作者归因）；后者只测 ViT | `[HTML]` |
| D23 | 联邦 LLM 多层/组合防御（数值多为摘要自述） | SafeFedPoisonDef：DOI 10.36227/techrxiv.175979271.17695501/v1；Fed-DCR：OpenAlex:W7171604421；Prototype-Guided：OpenAlex:W7220092741；VeriFed：DOI 10.1145/3793638.3793645；FedLAW（硕士论文）：OpenAlex:W7214142362；层级权重统计：DOI 10.1109/APSIPAASC65261.2025.11249294；FLAGuard：DOI 10.1109/TMC.2025.3641570 | `[FedLLM]` | 服务器为主；VeriFed 要求客户端出具证明 | H4/H5 + H8 | SafeFedPoisonDef：更新异常检测 + 可靠度加权聚合 + **在可信安全数据集上事后微调**（需要可信数据）；Fed-DCR：DCT 频域聚类 + LoRA 谱一致性 + 因果探针（"主动暴露后门"，涉及对模型的前向，O3）；Prototype-Guided：摘要称利用客户端间原型一致性，不需要原始数据或辅助干净数据；FedLAW：服务器学习自适应聚合权重并加有界归一化，论文动机是 LoRA 改变了更新结构使传统鲁棒聚合更难区分良恶（摘要）；层级权重统计：每轮对逐层权重更新取均值/中位数/标准差，再喂给机器学习检测器（DistilBERT 小模型）；FLAGuard：**服务器可能恶意**，分别验证聚合后的 A、B 与它们的乘积是否正确（可验证聚合，不是投毒检测）；VeriFed：客户端出示 SNARK，证明更新满足 ℓ2 敏感度界与结构约束，不暴露梯度 | VeriFed：**有**（证明生成与验证）；其余未读到 | 未读到 | 过滤、加权、事后微调；VeriFed 为准入式证明 | 摘要自述：SafeFedPoisonDef 把安全违规率降低最多 65%（相对基线）；Fed-DCR 在 CIFAR-10 与 Llama-2-7B 联邦 LoRA 上降低多种后门 ASR；Prototype-Guided 摘要偏系统性讨论，未见具体数值，可信度低；它们都是 2025–2026 的预印本/期刊条目，**未经我核对实验** | `[摘要]` |

> 未在表里展开但已读摘要的相关项：RoseAgg（针对共谋的目标投毒，2024）、BayBFed（贝叶斯后门防御，2301.09508）、DeFL（关键学习期，AAAI 2023）、Long-Short History of Gradients（2208.10273，跨轮历史）、ShieldFL（同态加密下的鲁棒检测）、SAFELearning（2102.02402）、RFLPA（2405.15182）——均只读摘要，需要时再补行。

---

## 3. 对设计的检验

（草稿；下面每条的论文依据都已在上表出现。证据等级以表中标记为准。）

### (i) 哪些防御需要的数据不在四类原始记录里

四类记录是：数据清单、训练步日志、上传的更新、聚合结果。文献里额外要的东西：

1. **逐样本梯度**（ProtegoFed `[笔记]`：每条样本单独反传，取末层 LoRA B 的梯度；GradSentry `[摘要]`：逐样本梯度的谱熵）。训练步日志若只记每步聚合 loss/梯度范数则不够。
2. **中间层激活**（CrowdGuard 摘要：隐藏层神经元行为；LoRAScan 摘要：下投影激活尖峰；DeepSight 摘要：内部结构与输出）。
3. **可信/参考数据**：FLTrust 的服务器 root dataset；ye 2024 的 1,000 条防御样本；Antidote 的有害 QA 数据；Lisa、SEAL 的对齐/安全数据；MOS 的恶意提问；Chorus 的私有留出探针池。这些是防御者自带的，不是流过信任边界的东西。
4. **参照权重/离线训练语料**：Safe LoRA 的对齐与未对齐成对权重；Safe-FedLLM 的离线攻击数据（笔记）；PEFTGuard 的 PADBench（输入细节未读到）。
5. **客户端维护的额外状态**：Safe-FedLLM 的 Shadow-Level 影子 LoRA 分支（笔记）。
6. **训练期检查点序列**：TracIn 摘要；FLDetector 的全局模型差分历史（需要比"聚合结果"更完整的保留）。
7. **LoRA 因子分开与乘积都要看**：GAP（2601.00566）指出 A、B 分开上传而乘积 BA 不被校验是攻击点（`[HTML]`，攻击效果数值见 A3）；FLAGuard（摘要）分别验证聚合后的 A、B 与它们的乘积。两者都说明"上传的更新"这类记录若只存因子而不能还原乘积（或反之），相应的检测/验证就做不了——这是对记录格式的要求（我们的推断）。
8. **承诺与证明**：Verifiable FT 要数据集 Merkle 承诺、公开初始化哈希、训练程序描述、证明。"数据清单"可以放承诺根，但证明本身是另一类对象。

### (ii) 哪些防御必须客户端与服务器配合

- **需要额外通道**：ProtegoFed（虚拟中心上传、全局中心下发 `[笔记]`）；Safe-FedLLM 的 Step/Shadow-Level（`[笔记]`）；CrowdGuard（客户端对他人模型做反馈，摘要）；IndexGuard（上传 Top-K 索引而非数值，摘要）；FedGT（分组聚合，摘要）；Chorus（邻居轻量消息 +404 B，`[HTML]`）；EmbTracker（客户端签名身份消息）；Verifiable FT（训练前承诺登记）。
- **配合的证据**：ProtegoFed 的 Table XII（`[笔记]`）：40% 客户端主动恶意时单独使用 ASR 40.29%，与 FreqFed 组合后 0.00%——样本级和更新级需要两端组合。SignalAgg（`[笔记]`）说明"仅服务器更新级防御"在数据源污染场景失效。
- **纯服务器侧就够的**：Krum/Median、FLAME、FreqFed、FLDetector、FLTrust、TPC/MOS 类探针、事后修复。但它们的适用边界见 (iv)(v)。

### (iii) 哪些防御必须在线干预、事后分析没用

- **必须在线**：聚合时的鲁棒聚合/重加权（D1–D8）；Chorus 在聚合前拒收，原因是后门会传播——诚实节点吸收后会继续转发（2609.37367，`[HTML]`）；ProtegoFed 在第一轮前一次性清洗样本（`[笔记]`）；至于"污染进入训练后无法靠事后日志消除"是**我们的推断**，论文没有做这个对照。
- **事后能做、且有人做**：Safe LoRA、Antidote、PPSA、ye 2024 事后微调（D19）；VFT、PoL 的事后验证；TracIn 归因；EmbTracker 泄露溯源。
- **事后不充分的依据**：Sleeper agents（摘要）后门可在 SFT、RL、对抗训练后保持；PaaA 的 PPSA 虽降低 ASR 但牺牲任务精度（`[全文节选]`）；Backdoor Attacks on Decentralised Post-Training 的最后一步安全对齐后仍有超过 60% 成功（`[HTML]`）。
- **时间窗口**：SignalAgg 的"上升—峰值—衰减"（`[笔记]`）意味着服务器侧检测窗口应在早期；Safe-FedLLM 因分布漂移在前 20 轮后冻结因子（`[笔记]`）。这是两篇论文各自的结论，不是同一实验。

### (iv) 任何"上传更新 + 行为探针"都难以发现的攻击

- **触发器后门**：TokenLoRA（`[全文节选]`）自述防御方无法用通用结构探针探测，需要针对触发词；权重侧检测器 1.5B→7B 不迁移（AUC 1.0→0.65）。LoRAScan 走的是推理时激活监控而不是更新检查（摘要）。
- **越狱探针被针对性绕过**：CloudGhost 对 TPC/MOS 报告 DTR 低于 5%（摘要）。
- **更新层几何检测被绕过**：GAP 对范数、FoolsGold、Spectral Signatures 的检测率 0.0%/1.2%/0.0%（`[HTML]`）。
- **数据层的隐蔽**：Halawi（每条数据都看似无害，GPT-4 99%）；He 2024（良性数据破坏安全）。
- **供应链/上游**：LoRATK、Trojan plugin 的适配器分发；Carlini、Souly 的预训练数据投毒。文献的处理：适配器扫描（PEFTGuard、LoRAScan、Obliviate），或来源验证（VFT 只证明"用了承诺的数据+声明的程序"，**不**检测毒内容；其论文还指出 TEE 单独不能解决用了哪些数据）。
- **恶意聚合器**：2606.27511 称安全聚合不能阻止服务器改最终模型；客户端侧一致性检查与本地微调有一定效果（`[HTML]`）。

### (v) 文献里自适应攻击主要针对什么

1. **几何/统计离群检测**（距离、余弦、范数）：ALIE、Fang、Shejwalkar（`[传统FL]`）、AugMP、GAP（`[FedLLM]`）。
2. **服务器行为探针**：CloudGhost 对 TPC/MOS（摘要）。
3. **后处理安全训练**：P-Trojan（2025，摘要：优化后门在持续微调中的持久性）；Sleeper agents。
4. **LoRA 结构**：GAP 利用 A/B 解耦。
5. **样本级防御的自适应测试偏弱**：ProtegoFed 的 Table XII 之外，其 Table XI 的自适应攻击本身很弱（无防御 ASR 仅 0.75%，`[笔记]`）；Safe-FedLLM 未评估自适应攻击（`[笔记]`）。这是"文献缺口"，不是"防御已被证明安全"。
6. ShadeEdit（摘要）：用自适应裁剪规避聚合类防御，对八种鲁棒聚合算法平均 ASR 99.5%（作者自述，我未核对）。
7. FLAME 的扩展版称对针对它的攻击尝试做了回应（摘要，作者自述，我没有独立核对）。

---

## 4. 未覆盖与不确定

**采集层面**
- arXiv API 本轮连续 HTTP 429（对一个简单探测查询重试 4 次仍失败），按要求如实记录并只用 OpenAlex；因此 arXiv 的"相关度排序前 100"没取到。OpenAlex 收录 arXiv 预印本，但可能滞后或缺项；`harvest_log.md` 里各查询的 arXiv 列为 0 不代表 arXiv 上没有。
- OpenAlex 用标题+摘要的严格布尔 AND；过滤式检索没有相关度排序，故每个查询取"被引降序前 100 + 发表时间降序前 100"，中段（中等被引、中等时间）可能漏。用不同术语（如 "adapter"、"fine-tuning-as-a-service"、"unsafe"）的论文可能漏。
- 联邦+LoRA+后门这类窄主题只有个位数命中，说明检索词严格，不代表文献只有这么多；"联邦大模型/LoRA 尽量全"只能说在这套检索词下读全了高相关项，**不是穷尽**。
- 去重：2026 年有不少会议目录、Zenodo/SSRN/TechRxiv 条目、学位论文，摘要缺失或质量低；已用"摘要少于 150 字降权"处理，但不能保证剔净。
- "已在原文献库"按 arXiv id 与规范化标题匹配，共 52 篇；标题写法不同的条目可能漏判。

**阅读层面**
- 摘要级的行里，"需要什么数据""是否要两端配合""是否有跨轮状态"若摘要没写，表里已写"未读到"，不代表论文没有。
- PEFTGuard、CrowdGuard：WebFetch 读 PDF 失败（返回压缩字节），只用了摘要；PEFTGuard 的检测输入与训练要求**不确定**。
- Proof-of-Learning：WebFetch 只拿到摘要页，日志内容与验证流程未读到。
- `[HTML]` 来源是 WebFetch 的摘要式提炼且长文只覆盖前 10 万字符（2606.27511、2609.37367、2510.16830、SABRE-FL、EmbTracker 都被截断），其中的数字请以原文为准。
- 2025–2026 的期刊/预印本条目（Prototype-Guided、SafeFedPoisonDef、VeriFed、FedLAW 等）只有摘要，其中部分摘要偏系统性讨论、无具体数字，**不作为强证据**。
- 传统 FL 的行（D1–D10、A15–A19）只用于理解机制，不能当作 LoRA/大模型的证据；A20、A11 中的图像/ViT/分类结果同理。
- 挂载点 H0–H8、观察权限 O0–O5 的对应都是我按机制做的映射，文献本身没有这套词。

**主题缺口**
- 联邦偏好学习/RLHF/DPO 的投毒与防御（只在集中式里有 Rando、Best-of-Venom 等索引项，联邦下没有读到）。
- 安全聚合下的鲁棒性在 LLM/LoRA 规模上的实际可行性（只读到 FedGT、SurroFL、IndexGuard、FLAGuard 的摘要）。
- 去中心化/流水线并行的后训练（只读到两篇，2604.02372 未测 LoRA）。
- 联邦下的数据归因/溯源（TracIn 等是集中式；没有读到联邦 LoRA 下的实测）。
- 评测口径差异：不同论文的 ASR、MD-Judge、harmful score 定义不同，本文没有跨论文比较数值。

## 5. 精读登记

共登记 **120** 篇（`reading_list.csv`）：`[笔记]` 8、`[全文节选]` 22、`[HTML]` 9、`[摘要]` 81。
其中读到方法/威胁模型/防御设置层面的（笔记 + 全文节选 + HTML）共 **39** 篇，其余只读摘要。联邦大模型/PEFT 相关共登记 27 篇。

| 深度 | 来源 id | 年 | 标题 | 备注 |
|---|---|---|---|---|
| 笔记 | arXiv:2207.09209 | 2022 | FLDetector: Defending Federated Learning Against Model Poisoning Attacks via Detecting Mal | FLDetector |
| 笔记 | arXiv:2312.04432 | 2023 | FreqFed: A Frequency Analysis-Based Approach for Mitigating Poisoning Attacks in Federated | FreqFed |
| 笔记 | arXiv:2406.10630 | 2024 | Emerging Safety Attack and Defense in Federated Instruction Tuning of Large Language Model | FedLLM-Attack 与事后防御 |
| 笔记 | arXiv:2404.01099 | 2024 | What is in Your Safe Data? Identifying Benign Data that Breaks Safety | He 2024 |
| 笔记 | arXiv:2601.07177 | 2026 | Safe-FedLLM: Delving into the Safety of Federated Large Language Models | Safe-FedLLM |
| 笔记 | arXiv:2603.00516 | 2026 | ProtegoFed: Backdoor-Free Federated Instruction Tuning with Interspersed Poisoned Data | ProtegoFed |
| 笔记 | arXiv:2602.15671 | 2026 | Revisiting Backdoor Threat in Federated Instruction Tuning From a Signal Aggregation Persp | SignalAgg |
| 笔记 | arXiv:2409.18169 | 2026 | Harmful Fine-tuning Attacks and Defenses for Large Language Models: A Survey | Huang 有害微调综述 |
| 全文节选 | arXiv:1703.02757 | 2017 | Byzantine-Tolerant Machine Learning | Krum：威胁模型段 |
| 全文节选 | arXiv:1807.00459 | 2018 | How To Backdoor Federated Learning | Bagdasaryan：§4.1 威胁模型 |
| 全文节选 | arXiv:1803.01498 | 2018 | Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates | Median/Trimmed mean：设定段 |
| 全文节选 | arXiv:1808.04866 | 2018 | Mitigating Sybils in Federated Learning Poisoning | FoolsGold：目标+算法段 |
| 全文节选 | arXiv:1902.06156 | 2019 | A Little Is Enough: Circumventing Defenses For Distributed Learning | ALIE：z_max 推导段 |
| 全文节选 | arXiv:1911.07963 | 2019 | Can You Really Backdoor Federated Learning? | Clipping：攻击设定段 |
| 全文节选 | arXiv:2012.13995 | 2020 | FLTrust: Byzantine-robust Federated Learning via Trust Bootstrapping | FLTrust：摘要+引言 |
| 全文节选 | arXiv:2101.02281 | 2021 | FLAME: Taming Backdoors in Federated Learning (Extended Version 1) | FLAME：摘要+前言+预备知识 |
| 全文节选 | arXiv:2201.00763 | 2022 | DeepSight: Mitigating Backdoor Attacks in Federated Learning Through Deep Model Inspection | DeepSight：摘要+贡献+威胁模型 |
| 全文节选 | arXiv:2310.03693 | 2023 | Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To! | Qi 2023：摘要+图1说明 |
| 全文节选 | arXiv:2305.14710 | 2023 | Instructions as Backdoors: Backdoor Vulnerabilities of Instruction Tuning for Large Langua | Instructions as backdoors：摘要+clean-label 段 |
| 全文节选 | arXiv:2411.19335 | 2024 | PEFT-as-an-Attack! Jailbreaking Language Models during Federated Parameter-Efficient Fine- | PaaA：威胁模型+RAS/PPSA 段 |
| 全文节选 | arXiv:2403.00108 | 2024 | LoRATK: LoRA Once, Backdoor Everywhere in the Share-and-Play Ecosystem | LoRATK：引言 |
| 全文节选 | arXiv:2405.16833 | 2024 | Safe LoRA: the Silver Lining of Reducing Safety Risks when Fine-tuning Large Language Mode | Safe LoRA：方法段 |
| 全文节选 | arXiv:2405.18641 | 2024 | Lisa: Lazy Safety Alignment for Large Language Models against Harmful Fine-tuning Attack | Lisa：威胁模型+算法段 |
| 全文节选 | arXiv:2402.01109 | 2024 | Vaccine: Perturbation-aware Alignment for Large Language Models against Harmful Fine-tunin | Vaccine：算法段 |
| 全文节选 | arXiv:2408.09600 | 2024 | Antidote: Post-fine-tuning Safety Alignment for Large Language Models against Harmful Fine | Antidote：方法段 |
| 全文节选 | arXiv:2410.07471 | 2024 | SEAL: Safety-enhanced Aligned LLM Fine-tuning via Bilevel Data Selection | SEAL：摘要+假设句 |
| 全文节选 | arXiv:2502.03801 | 2025 | SoK: Benchmarking Poisoning Attacks and Defenses in Federated Learning | FLPoison SoK：摘要+若干段 |
| 全文节选 | arXiv:2605.07961 | 2026 | Graph Representation Learning Augmented Model Manipulation on Federated Fine-Tuning of LLM | AugMP 完整版：威胁模型段 |
| 全文节选 | arXiv:2605.30189 | 2026 | Token-Level Generalization in LoRA Adapter Backdoors: Attack Characterization and Behavior | TokenLoRA：摘要+威胁模型小结 |
| 全文节选 | arXiv:2605.26574 | 2026 | GradSentry: Gradient Spectral Entropy for Backdoor Sample Filtering in Large Language Mode | GradSentry：摘要+引言 |
| HTML | arXiv:2401.10375 | 2024 | Foundation Models in Federated Learning: Assessing Backdoor Vulnerabilities | FM 合成数据后门 |
| HTML | arXiv:2511.14406 | 2025 | Watch Out for the Lifespan: Evaluating Backdoor Attacks Against Federated Model Adaptation | LoRA 后门寿命（ViT） |
| HTML | arXiv:2506.22506 | 2025 | SABRE-FL: Selective and Accurate Backdoor Rejection for Federated Prompt Learning | SABRE-FL（CLIP 提示） |
| HTML | arXiv:2510.16830 | 2025 | Verifiable Fine-Tuning for LLMs: Zero-Knowledge Training Proofs Bound to Data Provenance a | Verifiable Fine-Tuning |
| HTML | arXiv:2601.00566 | 2026 | Low Rank Comes with Low Security: Gradient Assembly Poisoning Attacks against Distributed  | GAP |
| HTML | arXiv:2606.27511 | 2026 | When the Aggregator Cheats: Data-Free Backdoors in Federated LLM-based QA Systems | 恶意聚合器后门 |
| HTML | arXiv:2604.02372 | 2026 | Backdoor Attacks on Decentralised Post-Training | 分散式后训练后门 |
| HTML | arXiv:2609.37367 | 2026 | Backdoor Mitigation in Decentralized LLM Fine-Tuning | Chorus |
| HTML | arXiv:2603.12089 | 2026 | EmbTracker: Traceable Black-box Watermarking for Federated Language Models | EmbTracker |
| 摘要 | arXiv:1811.00636 | 2018 | Spectral Signatures in Backdoor Attacks | Spectral signatures |
| 摘要 | arXiv:1811.03728 | 2018 | Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering | Activation clustering |
| 摘要 | arXiv:1811.00741 | 2018 | Stronger data poisoning attacks break data sanitization defenses | Stronger poisoning breaks sanitization |
| 摘要 | arXiv:1902.06531 | 2019 | STRIP: A Defence Against Trojan Attacks on Deep Neural Networks | STRIP |
| 摘要 | arXiv:1911.11815 | 2019 | Local Model Poisoning Attacks to Byzantine-Robust Federated Learning | Fang |
| 摘要 | arXiv:2011.10369 | 2020 | ONION: A Simple and Effective Defense Against Textual Backdoor Attacks | ONION |
| 摘要 | arXiv:2002.08484 | 2020 | Estimating Training Data Influence by Tracing Gradient Descent | TracIn |
| 摘要 | arXiv:2007.05084 | 2020 | Attack of the Tails: Yes, You Really Can Backdoor Federated Learning | Edge-case backdoor |
| 摘要 | arXiv:2007.08432 | 2020 | Data Poisoning Attacks Against Federated Learning Systems | Tolpegin |
| 摘要 | arXiv:2104.13230 | 2021 | Influence Based Defense Against Data Poisoning Attacks in Online Learning | Influence-based defense |
| 摘要 | arXiv:2103.05633 | 2021 | Proof-of-Learning: Definitions and Practice | Proof-of-Learning（摘要页，WebFetch） |
| 摘要 | DOI:10.14722/ndss.2021.24498 | 2021 | Manipulating the Byzantine: Optimizing Model Poisoning Attacks and Defenses for Federated  | Shejwalkar（NDSS 2021） |
| 摘要 | arXiv:2108.10241 | 2021 | Back to the Drawing Board: A Critical Evaluation of Poisoning Attacks on Production Federa | Back to the Drawing Board |
| 摘要 | arXiv:2106.08283 | 2021 | CRFL: Certifiably Robust Federated Learning against Backdoor Attacks | CRFL |
| 摘要 | arXiv:2206.10341 | 2022 | Neurotoxin: Durable Backdoors in Federated Learning | Neurotoxin |
| 摘要 | arXiv:2210.07714 | 2022 | CrowdGuard: Federated Backdoor Detection in Federated Learning | CrowdGuard（PDF 读取失败） |
| 摘要 | arXiv:2208.10273 | 2022 | Long-Short History of Gradients Is All You Need: Detecting Malicious and Unreliable Client | Long-Short History |
| 摘要 | DOI:10.1109/tifs.2022.3169918 | 2022 | ShieldFL: Mitigating Model Poisoning Attacks in Privacy-Preserving Federated Learning | ShieldFL |
| 摘要 | arXiv:2312.00374 | 2023 | The Philosopher's Stone: Trojaning Plugins of Large Language Models | Trojan plugin |
| 摘要 | arXiv:2305.00944 | 2023 | Poisoning Language Models During Instruction Tuning | Wan 2023 |
| 摘要 | arXiv:2307.16888 | 2023 | Backdooring Instruction-Tuned Large Language Models with Virtual Prompt Injection | VPI |
| 摘要 | arXiv:2306.17194 | 2023 | On the Exploitability of Instruction Tuning | AutoPoison |
| 摘要 | arXiv:2311.14455 | 2023 | Universal Jailbreak Backdoors from Poisoned Human Feedback | RLHF 后门 |
| 摘要 | arXiv:2302.10149 | 2023 | Poisoning Web-Scale Training Datasets is Practical | Carlini 2023 |
| 摘要 | arXiv:2309.06055 | 2023 | Backdoor Attacks and Countermeasures in Natural Language Processing Models: A Comprehensiv | NLP 后门综述（摘要前约 400 字） |
| 摘要 | arXiv:2301.09508 | 2023 | BayBFed: Bayesian Backdoor Defense for Federated Learning | BayBFed |
| 摘要 | DOI:10.1609/aaai.v37i9.26271 | 2023 | DeFL: Defending against Model Poisoning Attacks in Federated Learning via Critical Learnin | DeFL |
| 摘要 | arXiv:2305.05506 | 2023 | FedGT: Identification of Malicious Clients in Federated Learning With Secure Aggregation | FedGT |
| 摘要 | arXiv:2402.06954 | 2024 | OpenFedLLM: Training Large Language Models on Decentralized Private Data via Federated Lea | OpenFedLLM |
| 摘要 | arXiv:2406.04845 | 2024 | FedLLM-Bench: Realistic Benchmarks for Federated Learning of Large Language Models | FedLLM-Bench |
| 摘要 | arXiv:2406.20053 | 2024 | Covert Malicious Finetuning: Challenges in Safeguarding LLM Adaptation | Covert malicious finetuning |
| 摘要 | arXiv:2401.05566 | 2024 | Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training | Sleeper agents |
| 摘要 | arXiv:2410.13722 | 2024 | Persistent Pre-Training Poisoning of LLMs | 持久预训练投毒 |
| 摘要 | arXiv:2403.13355 | 2024 | BadEdit: Backdooring large language models by model editing | BadEdit（摘要前约 400 字） |
| 摘要 | arXiv:2402.13459 | 2024 | Learning to Poison Large Language Models for Downstream Manipulation | Learning to poison LLMs（摘要前约 400 字） |
| 摘要 | arXiv:2404.02406 | 2024 | Exploring Backdoor Vulnerabilities of Chat Models | Backdoor chat models（摘要前约 400 字） |
| 摘要 | arXiv:2409.17946 | 2024 | Breaking PEFT Limitations: Leveraging Weak-to-Strong Knowledge Transfer for Backdoor Attac | W2S 后门迁移（摘要前约 400 字） |
| 摘要 | DOI:10.1109/icassp48485.2024.10446267 | 2024 | PoisonPrompt: Backdoor Attack on Prompt-Based Large Language Models | PoisonPrompt（摘要前约 400 字） |
| 摘要 | arXiv:2409.01586 | 2024 | Booster: Tackling Harmful Fine-tuning for Large Language Models via Attenuating Harmful Pe | Booster |
| 摘要 | arXiv:2405.14577 | 2024 | Representation Noising: A Defence Mechanism Against Harmful Finetuning | RepNoise |
| 摘要 | arXiv:2408.00761 | 2024 | Tamper-Resistant Safeguards for Open-Weight LLMs | TAR |
| 摘要 | arXiv:2402.14968 | 2024 | Mitigating Fine-tuning based Jailbreak Attack with Backdoor Enhanced Safety Alignment | BEA |
| 摘要 | arXiv:2402.12168 | 2024 | Defending Against Weight-Poisoning Backdoor Attacks for Parameter-Efficient Fine-Tuning | PSIM |
| 摘要 | arXiv:2409.14119 | 2024 | Obliviate: Neutralizing Task-agnostic Backdoors within the Parameter-efficient Fine-tuning | Obliviate |
| 摘要 | arXiv:2410.14425 | 2024 | Unlearning Backdoor Attacks for LLMs with Weak-to-Strong Knowledge Distillation | W2S 去后门（摘要前约 400 字） |
| 摘要 | arXiv:2406.06852 | 2024 | A Survey of Recent Backdoor Attacks and Defenses in Large Language Models | LLM 后门综述（摘要前约 400 字） |
| 摘要 | arXiv:2408.12798 | 2024 | BackdoorLLM: A Comprehensive Benchmark for Backdoor Attacks and Defenses on Large Language | BackdoorLLM |
| 摘要 | arXiv:2402.04333 | 2024 | LESS: Selecting Influential Data for Targeted Instruction Tuning | LESS |
| 摘要 | arXiv:2402.13494 | 2024 | GradSafe: Detecting Jailbreak Prompts for LLMs via Safety-Critical Gradient Analysis | GradSafe |
| 摘要 | DOI:10.1145/3658644.3670316 | 2024 | Zero-Knowledge Proofs of Training for Deep Neural Networks | Kaizen zkPoT |
| 摘要 | DOI:10.1109/tifs.2024.3352415 | 2024 | RoseAgg: Robust Defense Against Targeted Collusion Attacks in Federated Learning | RoseAgg |
| 摘要 | arXiv:2507.01694 | 2025 | Graph Representation-based Model Poisoning on Federated Large Language Models | AugMP 早期版 |
| 摘要 | DOI:10.36227/techrxiv.175979271.17695501/v1 | 2025 | Defending Federated Large Language Models against Data Poisoning Attacks: A Safety-Aware F | SafeFedPoisonDef |
| 摘要 | OpenAlex:W7220092741 | 2025 | Prototype-Guided Backdoor Mitigation for Federated Large Language Model Fine-Tuning in Cro | Prototype-Guided（摘要偏系统性讨论） |
| 摘要 | arXiv:2508.08040 | 2025 | BadPromptFL: A Novel Backdoor Threat to Prompt-based Federated Learning in Multimodal Mode | BadPromptFL |
| 摘要 | DOI:10.1109/tmc.2025.3641570 | 2025 | FLAGuard: Efficient Verifiable Federated LoRA of Large Language Models | FLAGuard（联邦 LoRA 聚合可验证） |
| 摘要 | DOI:10.1109/apsipaasc65261.2025.11249294 | 2025 | Layer-Wise Weight Statistics for Node Classification and Defense of Federated Large Langua | 层级权重统计检测（DistilBERT） |
| 摘要 | arXiv:2512.19297 | 2025 | Causal-Guided Detoxify Backdoor Attack of Open-Weight LoRA Models | Causal-Guided Detoxify |
| 摘要 | arXiv:2506.19823 | 2025 | Persona Features Control Emergent Misalignment | Persona features（摘要前约 400 字） |
| 摘要 | arXiv:2506.13206 | 2025 | Thought Crime: Backdoors and Emergent Misalignment in Reasoning Models | Thought Crime（摘要前约 400 字） |
| 摘要 | arXiv:2510.07192 | 2025 | Poisoning Attacks on LLMs Require a Near-constant Number of Poison Samples | Souly 2025 |
| 摘要 | arXiv:2512.14741 | 2025 | Persistent Backdoor Attacks under Continual Fine-Tuning of LLMs | P-Trojan（持续微调下的持久后门） |
| 摘要 | DOI:10.14722/ndss.2025.241089 | 2025 | Safety Misalignment Against Large Language Models | Safety Misalignment 评测（摘要前约 600 字） |
| 摘要 | arXiv:2411.17453 | 2025 | PEFTGuard: Detecting Backdoor Attacks Against Parameter-Efficient Fine-Tuning | PEFTGuard（PDF 读取失败） |
| 摘要 | DOI:10.1162/tacl.a.44 | 2025 | Safe Pruning LoRA: Robust Distance-Guided Pruning for Safety Alignment in Adaptation of LL | Safe Pruning LoRA（摘要前约 600 字） |
| 摘要 | arXiv:2502.18511 | 2025 | ELBA-Bench: An Efficient Learning Backdoor Attacks Benchmark for Large Language Models | ELBA-Bench（摘要前约 400 字） |
| 摘要 | DOI:10.1109/jiot.2025.3602453 | 2025 | SurroFL: Sketch-Based Defense Against Poisoning in Privacy-Preserving Federated Learning | SurroFL |
| 摘要 | OpenAlex:W7167559498 | 2026 | Ghost in the Cloud: Your Geo-Distributed Large Language Models Training is Easily Manipula | CloudGhost/Ghost in the Cloud |
| 摘要 | OpenAlex:W7214868953 | 2026 | Index-only Backdoor Vetting for Secure Federated PEFT of Large Language Models | IndexGuard |
| 摘要 | DOI:10.1609/aaai.v40i41.40787 | 2026 | ShadeEdit: A Utility-Preserving and Defense-Evasive Knowledge Manipulation Attack in Feder | ShadeEdit |
| 摘要 | OpenAlex:W7171604421 | 2026 | Fed-DCR: A Backdoor Defense Scheme for Federated Learning Based on Dual-Domain Synergistic | Fed-DCR |
| 摘要 | DOI:10.1145/3793638.3793645 | 2026 | VeriFed: Cryptographic Accountability for Privacy-Preserving and Robust Federated LLM Fine | VeriFed |
| 摘要 | DOI:10.1109/tcc.2026.3660272 | 2026 | Privacy-Enhanced Federated Prompt Tuning Against Backdoor Attack | 联邦提示调优抗后门（摘要前约 400 字） |
| 摘要 | arXiv:2606.20553 | 2026 | From Efficiency to Leakage -- Privacy Backdoor in Federated Language Model Fine-Tuning | 联邦 PEFT 隐私后门（恶意服务器） |
| 摘要 | arXiv:2607.27940 | 2026 | TriShield: Zero-Utility-Loss Defense Against Privacy Backdoors in Federated Language Model | TriShield |
| 摘要 | OpenAlex:W7214142362 | 2026 | Robust Federated Fine-Tuning of Large Language Models with Low-Rank Adaptation | FedLAW：联邦 LoRA 学习聚合权重（硕士论文） |
| 摘要 | arXiv:2502.17424 | 2026 | Training large language models on narrow tasks can lead to broad misalignment | Emergent misalignment |
| 摘要 | arXiv:2606.16242 | 2026 | Rapid Poison: Practical Poisoning Attacks Against the Rapid Response Framework | Rapid Poison（摘要前约 400 字） |
| 摘要 | arXiv:2608.06795 | 2026 | LoRAScan: Detecting Backdoor Prompts in Low-Rank Adapters for Large Language Models via Do | LoRAScan |
| 摘要 | DOI:10.1109/tdsc.2026.3662097 | 2026 | UniFLE: Uniform Fusion of Multiple LoRA Experts for Backdoor Defense in Large Language Mod | UniFLE（摘要前约 600 字） |
| 摘要 | OpenAlex:W7219182613 | 2026 | Backdoor trigger recovery in sleeper-agent language models | sleeper 触发词恢复（硕士论文，摘要前约 600 字） |
