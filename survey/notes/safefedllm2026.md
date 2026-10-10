# Safe-FedLLM: Delving into the Safety of Federated Large Language Models

- Key：`safefedllm2026`；ACL 2026 main；本地为 arXiv:2601.07177**v5**（2026-05-30，17 页）
- 作者：Mingxiang Tao, Yu Tian, Wenxuan Tu, Yue Yang, Xue Yang, Xiangyan Tang（海南大学、清华、上海交大）
- 类别：C9（服务器侧更新检测）；训练阶段：联邦 SFT，LoRA
- 代码：[dmqx/Safe-FedLLM](https://github.com/dmqx/Safe-FedLLM)
- 阅读深度：正文 + 附录 A/B（probe 训练与稳定化策略）

## 1. 威胁模型与设定（§3.1, pp.3–4；§5.1 p.7）
- 直接沿用 FedLLM-Attack 的数据构造：良性 LMSYS-Chat/WildChat，恶意 BeaverTails/MaliciousGen；恶意比例 20%–50%。
- 服务器只看 LoRA 更新、不看原始数据（p.2 研究问题）。
- 论文**未显式声明**客户端是否诚实执行防御协议；但 Step-Level 需要每个本地步的 ΔB、Shadow-Level 需要客户端维护影子 LoRA 分支（§4.2），因此隐含“恶意客户端只改数据、按协议执行训练与上报”的假设（我们的分析）。

## 2. 方法（§4, pp.4–6）
- **LoRA-Probe**：特征为**第一层 Transformer 所有 LoRA 模块 B 矩阵**相对初始的差 `ΔB_{0,t} = B_t − B_0`，展平拼接后 L2 归一化；分类器为**逻辑回归** `s = σ(aᵀx̃ + c)`（Eq.1–4）。
- 离线训练数据：模拟客户端本地训练，取 50% 恶意设置下前 10 轮的 ΔLoRA；排除与主实验重叠的前 4000 条 WildChat/LMSYS 与前 2500 条 BeaverTails/MaliciousGen（附录 A, p.13）。
- 三级防御：
  - Step-Level：逐本地步判定，Beta 计数 + 时间衰减 γ 得安全因子 `α/(α+β)`（Eq.5–6）。
  - Client-Level：最终 ΔLoRA 概率经两段 sigmoid 校准，取历史参与轮平均（Eq.7–8）。
  - Shadow-Level：客户端维护独立影子 LoRA 分支（固定学习率，不参与聚合），逐步判定恶意比例 ρ，因子 `(1−ρ)^η`（Eq.9）。
- 早期冻结：Step/Client 因子只在前 R_f=20 轮更新，此后固定，以应对 ΔLoRA 分布漂移（Eq.10）。
- 聚合：平均安全因子低于 τ_skip 时跳过本轮；否则按 `n_i·w_i` 归一化加权（Eq.11–12）。

## 3. 实验设置（§5.1, p.7）
Llama3.1-8B、Qwen2.5-7B（8-bit）；10 客户端各 500 样本，每轮采样 3 个、10 本地步、100 轮；LoRA r=8、α=16；lr 5×10⁻⁵，max len 256；τ_cls=0.8、τ_skip=0.2、γ=0.95、η=7。基线：Multi-Krum、Trimmed Mean、FoolsGold、Residual、DnC、FLAME、LASA。MT-1 由 GPT-5-mini 评判。

## 4. 主要结果（表格值）

| 出处 | 设置 | 结果 |
|---|---|---|
| Table 1, p.3 | Llama3.1-8B，FedAvg 恶意比例 0→20% | BeaverTails&LMSYS MD-Judge 75.77 → 20.77 |
| Table 2, p.7 | 30% 恶意，BeaverTails&LMSYS | FedAvg MD-Judge 14.81；最佳传统基线 Multi-Krum 20.58；Shadow-Level 77.12 |
| Table 2, p.7 | 30% 恶意，MaliciousGen&WildChat | FedAvg 5.77；Client-Level 55.77（无攻击 FedAvg 为 52.69，Table 1） |
| Table 3, p.8 | Qwen2.5-7B，30% | Shadow-Level MD-Judge 95.96–96.92 |
| Table 4, p.8 | 开销 | 训练时间 2h35m→2h40m；Shadow-Level LoRA 参数与显存翻倍（20.62GB→41.24GB） |
| Table 5, p.8 | Shadow-Level，恶意 20%–50% | MD-Judge 75.00–77.31，保持稳定 |
| Fig.4, p.9 | 分类精度随轮次 | Step/Client-Level precision 持续下降（分布漂移） |

## 5. 成立条件与局限
论文自述（Limitations, p.9）：
1. 要求客户端 LoRA 初始化随机种子与训练 probe 时一致（附录 B 固定所有客户端初始 LoRA）。
2. probe 跨底座迁移性差，换模型需重训。
3. 长程训练中 ΔLoRA 分布漂移；Shadow-Level 缓解但增加开销。

我们的分析：
4. **监督信号可能来自“数据集来源”而非“恶意性”**：probe 的训练与测试样本来自同一组数据集（只是不同样本），良性与恶意分别对应不同来源（LMSYS/WildChat vs BeaverTails/MaliciousGen）。文中没有“未见良性领域”“未见攻击数据源”“同源安全/不安全配对”的测试，无法排除 probe 学到的是领域/风格差异。这恰好与 FedLLM-Attack“参数层不可分”的结论形成张力：二者差别在于是否有**带标签的离线训练**。
5. **可伪造性**：Step-Level 与 Shadow-Level 的信号由客户端计算并上报；主动恶意客户端可在影子分支上训练干净数据或伪造逐步 ΔB，本方法对这种自适应攻击未作评估。
6. **先验知识**：离线训练需要攻击数据样本，属于“已知攻击类型”的检测；对后门、隐蔽良性数据（He et al.）等未见攻击的泛化未知。
7. 仅用第一层 B 矩阵、线性分类器即可高度可分，本身是值得复现的强结论；需检查是否对样本数、数据长度、回答风格等浅层因素敏感。
8. Shadow-Level 在 Qwen 上安全指标（~96）远高于无攻击 FedAvg，说明它不仅在过滤恶意客户端，可能还在改变良性训练动态，需要 G3（无攻击+防御）对照。

## 6. 与本项目的关系
- **服务器侧基线（主动恶意客户端 × 只见 LoRA 更新）**，与 MCD/KL-Detecter 在迁移链中处于同一位置：MCD 用无监督横纵向统计，Safe-FedLLM 用有监督线性探针。
- 可直接构造的研究问题：①无监督 MCD 式跨轮统计在 ΔB 上能否达到有监督 probe 的效果；②probe 在未见数据源/未见攻击/自然 non-IID 下是否崩溃；③Client-Level 的“历史平均”本质上就是 MCD 中心指标的监督版本。
- 其“早期冻结”说明跨轮漂移是真实问题，这对 MCD 覆盖指标（纵向离散度）的迁移是负面证据，也是需要设计归一化的地方。

## 7. 待核对问题
- 附录 Table 7 的 TPR/FPR/Precision/MCC 具体数值（抽取文本丢失数字，需看 PDF p.15）。
- 代码中 probe 训练集是否与测试客户端数据同源拆分；是否提供跨数据集实验脚本。
