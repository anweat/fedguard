# Harmful Fine-tuning Attacks and Defenses for Large Language Models: A Survey

- Key：`huang2024harmful`；本地为 arXiv:2409.18169**v6**（2026-04-23，45 页）；作者 Tiansheng Huang, Sihao Hu, Fatih Ilhan, Selim Furkan Tekin, Ling Liu（Georgia Tech）
- 伴随索引：[git-disl/awesome_LLM-harmful-fine-tuning-papers](https://github.com/git-disl/awesome_LLM-harmful-fine-tuning-papers)（本地 `external/`）
- 类别：C0（综述）；覆盖阶段：对齐、用户微调、微调后，少量涉及预训练与 RLVR
- 阅读深度：§2 威胁模型、§3.3–3.4 攻防分类、§5 未来方向；逐篇表格（Table 1/2）按需回查

## 1. 威胁模型（§2.2, pp.3–4）
- 场景：微调即服务（FaaS）两阶段——服务商先安全对齐，再用用户数据微调；**微调后通常不再重新对齐**（成本高、会损伤下游任务）。
- 攻击者（用户，有意或无意）：只能控制上传数据，p 比例为有害数据（p=0 即良性微调退化）；**不能控制微调算法与超参**。
- 防御者（服务商）：**完全控制对齐/微调/部署流程**，可过滤修改用户数据；通常持有对齐数据集（有害问 + 安全答）与有害数据集（有害问 + 有害答），且后者不能与攻击数据重合。
- 防御目标：Resistance（微调后有害分数低）+ Stability（下游任务精度不受损），指标为 harmful score 与 finetune accuracy。

## 2. 攻击分类（Fig.8、Table 1，p.9 起）
- 显式有害数据攻击；数据增强/后缀；**良性数据攻击**：原始良性（Qi et al.）、数据采样（双向锚定 `he2024safedata`、Self-Inf-N）、增强（AOA 身份切换等）。
- 隐写/编码攻击（CMF `halawi2024covert`、Flower）、guardrail 越狱数据（Virus）。
- 扩展：**联邦学习**（`ye2024emerging`、`li2024peftattack`）、模型编辑、自演化/RLVR，多语言、电信、生物、音频模型。

## 3. 防御按阶段分类（§3.3, pp.13–17）

| 阶段 | 思路 | 代表 |
|---|---|---|
| 预训练 | 过滤语料中有害内容；扩大能力盆地的优化器 | [170]、GO |
| 对齐阶段 | 让对齐模型对后续有害扰动更鲁棒 | Vaccine（隐层扰动 min-max）、RepNoise（最大化有害损失 + 表示噪声）、TAR（元学习模拟有害微调）、Booster |
| 用户微调阶段 | 修改微调算法或数据：混入对齐数据、约束漂移、过滤数据 | Lisa、SafeInstr、BEA、**Seal（双层数据选择）**、SAFT（嵌入空间谱检测）、BDS |
| 微调后 | 修复/重对齐 | Security Vector、Panacea、LAT、SOMF、**Safe LoRA（投影到安全子空间）**、SafeMerge、**Antidote（剪除有害坐标）**、IRR |

- 审核模型不足的定量证据：BeaverTails 审核模型 **假阴性 7.71%、假阳性 3.64%**（Table 3，p.16–17）。

## 4. 未来方向（§5, pp.22–24）
- 攻击：更隐蔽的隐写（低困惑度编码）、guardrail 越狱数据的可迁移性、更强的良性数据采样与构造。
- 防御：**数据过滤/审核型防御**（嵌入空间 OOD 检测）、提示工程、**偏好学习（RLHF/DPO）防御仍欠缺**、参数级部分调参/剪枝、高效防御、**跨阶段联合防御**。
- 机理：嵌入漂移、层级安全、梯度上升副作用、安全盆地；需要统一基准。

## 5. 迁移到联邦 LoRA 微调的关键差异（我们的分析）

FaaS 中防御者**自己执行微调**；联邦学习中微调在客户端执行，服务器只看更新。由此各阶段防御在联邦中的“执行者”发生变化：

| FaaS 防御阶段 | 联邦中由谁执行 | 可用性判断 |
|---|---|---|
| 对齐阶段（Vaccine/RepNoise/TAR/Booster） | 服务器在下发基座/初始 adapter 前完成 | **可直接迁移**，不依赖客户端诚实；但 FedLLM-Attack 使用未对齐预训练底座，需改为对齐底座才有意义 |
| 微调阶段数据过滤（Seal/SAFT/审核模型） | 客户端本地 | **仅对诚实客户端有效**（对应 ProtegoFed 威胁模型）；恶意客户端可跳过 |
| 微调阶段算法约束（Lisa/BEA 等） | 客户端本地训练代码 | 同上，需可信执行或无法防主动恶意客户端 |
| 微调后修复（Safe LoRA/Antidote/SafeMerge） | 服务器对聚合模型 | **可直接迁移**；与 FedLLM-Attack 的事后修复同位 |
| （综述中缺失）聚合阶段 | 服务器对逐客户端更新 | 联邦特有的防御位置：更新检测、鲁棒聚合、行为探针 |

这张表是“双端防御”在 LLM 场景的一个自然组织方式：**服务器负责对齐前与聚合后，客户端负责数据入口，聚合阶段是联邦新增的战场**。

## 6. 与本项目的关系
- 提供威胁模型与 Resistance/Stability 评测框架，可直接沿用。
- 综述明确指出偏好学习防御与跨阶段联合防御是空白，与本项目“覆盖多个训练阶段”的需求对应。
- 综述对联邦场景只列了两篇攻击（`ye2024emerging`、`li2024peftattack`），**没有联邦防御的分类**，说明联邦聚合阶段的防御在该文献体系中缺位。

## 7. 待核对
- Table 1/2 中各防御的实验设置（LoRA 或全参、对齐或未对齐底座），用于判断哪些方法可在 7B + LoRA 下低成本复现。
