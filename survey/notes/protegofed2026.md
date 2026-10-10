# ProtegoFed: Backdoor-Free Federated Instruction Tuning with Interspersed Poisoned Data

- Key：`protegofed2026`；arXiv:2603.00516v1（2026-02-28，18 页，arXiv 标注 Work in progress）
- 类别：C9（样本级协作防御）；训练阶段：联邦 SFT（QA 指令微调），LoRA
- 代码：[dongdongzhaoUP/ProtegoFed](https://github.com/dongdongzhaoUP/ProtegoFed)（README 标题已改为 *Mining Clean Records from Contaminated Instruction Data Silos*，不能默认对应 v1）
- 阅读深度：全文 + 关键公式/表格视觉核对。详细版见 [`output/poisoning_study/2026-09-15_ProtegoFed-v1-论文补充与复现检查.md`](../../output/poisoning_study/2026-09-15_ProtegoFed-v1-论文补充与复现检查.md)
- 页码为本地 PDF 页码（与正文页码一致）

## 1. 威胁模型（§III，pp.3–4）
- 攻击者是应用用户或第三方数据提供者，只能修改自己提供的数据；**不参与**本地训练、预处理或聚合。
- 所有客户端与服务器诚实执行防御协议；污染样本可“混散”（interspersed）在所有客户端中，部分客户端本地污染率可超过 50%。
- 目标：条件触发后输出预定内容（后门），保持正常 QA 能力。
- “Interspersed”指**分布维度**的混散，不是跨轮间歇注入；主算法在第一轮前一次性运行（§V-A p.5；§VII-B p.14）。

## 2. 方法（§V，pp.5–7）
1. 客户端从同一初始 LoRA 状态出发，对**每条样本单独反向传播**，取末层 LoRA B 梯度（跨模型实验为 `self_attn.v_proj.lora_B`）（§V-B p.6；Table IV p.10）。
2. 梯度矩阵做 2D DCT 并展平为特征；UMAP 降到 2 维后分别用二簇层次聚类与 HDBSCAN，按轮廓系数选择结果（Eq.6–10，p.6）。保守规则：两个轮廓分数较小值 <0.2 且较大值 <0.4 时全部视为干净。
3. 本地选最大簇，在**降维前 DCT 空间**计算均值作为虚拟中心并上传（UMAP 坐标跨客户端不可比）（Eq.9–10）。
4. 服务器对各中心再次降维聚类，选主簇并在原空间求全局中心下发（Eq.11–13）。
5. 客户端把全局中心加入本地特征重新聚类，含全局中心的簇视为干净，仅保留这些样本进入常规联邦 LoRA 训练（Eq.14–15，p.7）。

## 3. 实验设置（§VI-A，pp.7–8）
- 数据：WebQA、FreebaseQA（无上下文），NQ、CoQA（有上下文）；除 WebQA 外抽 5000 训练 / 400 验证 / 2000 测试。
- 攻击：BadNets（问题内 token）、AddSent（插入句）、CBA（跨 Instruction/Context 与 Question 的组合触发）、StyleBkd（Bible 风格迁移）。
- 分配：IID 主实验 25 客户端、本地污染率 10%；NIID-1 本地率 ∈[0,0.4]；NIID-2 Dirichlet α=0.5、上限 0.5；NIID-3 去掉上限；多源污染补充实验。
- 训练：LoRA rank 4，1 本地 epoch，100 轮，lr 2×10⁻⁵；模型 1B–70B（非每表全覆盖）。
- 指标：CACC、ASR（exact-match 类），样本检测 Recall/F1。

## 4. 主要结果（表格值）

| 出处 | 结果 |
|---|---|
| Table II, p.8 | 4 数据集 × 4 攻击，ProtegoFed ASR 均为 0.00% |
| Table III, p.9 | IID 样本 Recall 92.00%–100.00%；WebQA/CBA Recall 92.00%、F1 82.71% |
| Table V, p.10 | 纯干净数据启用防御 CACC 下降 0.58–0.90 个百分点 |
| Table XI, p.15 | 自适应攻击：无防御 ASR 仅 0.75%，防御后 0.05%（攻击本身弱） |
| Table XII, p.15 | 40% 客户端主动恶意时，单独 ProtegoFed ASR 40.29%（诚实客户端 B-Recall 99.49%）；与 FreqFed 组合 ASR 0.00% |

## 5. 成立条件与局限
论文与我们的核对：
1. 一次性清洗，不覆盖跨轮新数据与间歇注入。
2. 验证对象是**固定触发映射的后门**，不能外推到无触发的安全对齐退化。
3. NIID 只改变污染比例，未覆盖自然领域/语言异质性；主簇假设要求全局存在可识别的干净结构。
4. 虚拟中心是梯度统计量，不等于 DP 保证，也与隐藏个体中心的安全聚合不兼容。
5. 文本内部问题：p.9 对 Recall 的文字定义与标准定义相反；p.9 正文 F1 数值（79.12%、99.08%）与 Table III（82.71%、92.00%）不一致；PDF 页眉为 TDSC/2021 模板信息。

我们的代数检查（待核实现）：
- 标准 LoRA 初始化 B=0 时，首次梯度 ∂L/∂A 应为零，而 ∂L/∂B 非零；p.12 关于 A 大偏移的解释需核对是否有预热或非零初始化。
- 完整正交 DCT 保持欧氏距离与内积，若没有低频截断等额外操作，DCT 本身不应改变可分性；需做 raw gradient vs DCT 消融。

## 6. 与本项目的关系
- **客户端侧（诚实客户端 × 污染数据源）防御的最直接基线**，也是 CAEKL 客户端审查在 LLM 场景的对应物：从“自编码器重构误差”换成“逐样本 LoRA 梯度聚类”。
- Table XII 是“双端必须组合”的直接证据：样本级清洗无法防御主动恶意客户端，需要服务器更新检测（FreqFed）补位。
- 与 MCD/LSDAM 链条的呼应：ProtegoFed 依赖投毒样本在梯度空间的**同质性**（同一触发—目标映射）；多样化触发/目标（LSDAM/MoEGAN 思路）是其自适应攻击的自然方向。

## 7. 待核对问题
- 作者仓库对应提交与 v1 的差异；B=0 初始化下梯度是否取自预热后状态。
- 安全对齐退化（无触发）场景下梯度聚类是否仍可分。
