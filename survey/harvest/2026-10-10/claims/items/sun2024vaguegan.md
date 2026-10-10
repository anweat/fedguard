## 1. 论文评测了哪些攻击

论文的防御方法 MCD 只在一个"传统联邦图像分类 + 数据投毒"的实验空间里被评测，攻击全部发生在联邦训练开始前的客户端本地数据准备阶段，目标是无目标地降低全局模型准确率（卡片第 2、3 节）。被实际跑进实验的攻击有四类：

| # | 论文中的攻击 | 卡片依据原话（逐字） | 实验设定 |
|---|---|---|---|
| 1 | label flipping（标签翻转，标签 6→0）与 label flipping + PoisonGAN | "论文中的标签翻转基线虽然把标签“6”改成“0”，但那只是攻击基线的构造方式"；"攻击基线包括标签翻转、标签翻转加 PoisonGAN、轻噪声叠加、重噪声叠加" | 联邦：是；大模型/LoRA：否；小型 CNN（MNIST/Fashion-MNIST 两层卷积、CIFAR-10 六层卷积等），数据集 MNIST、Fashion-MNIST、CIFAR-10、CIFAR-100、Mini-ImageNet；默认 N=60、K=10、T=200，防御实验 N=20、K=5、T=200（IID Fashion-MNIST）；α=5%–30%；各数据集样本量与每客户端样本数卡片未说明 |
| 2 | 噪声叠加：light noise、heavy noise、salt and pepper (SAP) noise、cosine noise | "轻噪声为均值 0、方差 0.1 的高斯噪声，重噪声为均值 0、方差 0.3 的高斯噪声"；"SAP 噪声对每张图 30% 的像素加噪且“盐”与“胡椒”比例为 0.5" | 同上（表 IV 逐项给出轻噪声、重噪声、SAP 噪声的检出数；余弦噪声出现在表 VII 的汇总里） |
| 3 | PoisonGAN（GAN 生成投毒数据替换本地数据） | "攻击基线包括标签翻转、标签翻转加 PoisonGAN、轻噪声叠加、重噪声叠加" | 同上 |
| 4 | VagueGAN（本文自己提出的 GAN 数据投毒攻击） | "VagueGAN 默认 κ = 0.2、E = 600，生成与真实数据等量的投毒数据并整体替换原始数据"；"训练好的 VagueGAN 生成一个与原始数据集等大的投毒数据集" | 同上；α 取 5%、10%、20%、30% 时 MCD 分别检出 1、2、3.9、5.8 个恶意客户端，结果取 10 次运行平均 |

需要提醒的两点卡片内部细节：

- 卡片第 7 节写"表 VII 汇总显示只有 MCD 对全部六种攻击（标签翻转、PoisonGAN、轻噪声、重噪声、SAP 噪声、余弦噪声、VagueGAN）都标记为可防御"，括注里实际列了七项，与"六种"数目不一致；我按括注的七项理解，未替论文圆场。
- 卡片没有明确说"轻噪声/重噪声/余弦噪声"是加在本地数据上还是加在上传的本地模型上，只对 SAP 噪声写明"对每张图……的像素加噪"；但卡片第 2、3 节把全文威胁模型限定为数据投毒（攻击者只动本地数据集，上传流程规范），因此我按"数据侧破坏"归类，并在第 2 节说明由此带来的不确定性。

## 2. 与清单的对应及把握程度

**能对上的只有一条：T-0006 untargeted_data_corruption（无目标的数据破坏）。** 把握程度：高。理由是该条定义"Corrupt labels or contents of local samples, or replace them with generated ones, to lower the model's quality"，与论文四类攻击逐一对应，且清单里三个变体名几乎是逐字命中：

- `label_flipping_data_poisoning`（以及 `targeted_label_flipping` 的"定向翻转"色彩）↔ 标签翻转基线（6→0，但论文目标是无目标降准确率）；
- `generative_data_poisoning` / `synthetic_poison_sample_replacement` ↔ PoisonGAN 与 VagueGAN 的"用生成数据整体替换原始本地数据集"；
- 噪声叠加（轻/重/SAP/余弦）↔ 对本地样本内容的破坏，同样服务于降低全局模型质量。

**明确不列入的条目及理由：**

- **T-0016 simple_update_corruption**：这条包含"added noise"，若论文的轻/重/余弦噪声实际是加在上传的本地模型更新上，就应改归 T-0016。但卡片只在数据投毒框架下描述这些基线，唯一写明加噪位置的一句是"SAP 噪声对每张图 30% 的像素加噪"（数据侧），没有一句说"把噪声加到上传的更新/模型参数上"，因此不列入 evaluated；这是本次归类中最主要的一处不确定。
- **T-0011 defense_aware_update_crafting**：列入 mentioned_only，且对应是宽泛的。论文只在局限与未来工作中说"如果攻击者采用更动态版本的 VagueGAN 或者把它与更复杂的自适应攻击策略结合，MCD 的鲁棒性会面临明显更大的挑战"，并没有描述"针对聚合规则或检测器优化上传更新"的具体做法，也没有做任何自适应攻击实验。VagueGAN 虽然以隐蔽性为目标之一，但它优化的是投毒数据、且论文未假设攻击者知道 MCD 的参数（卡片第 9 节），所以不算针对防御构造更新。
- **T-0012 collusive_update_cluster**：论文有多个恶意客户端（α 最高 30%），但卡片只描述每个被控客户端各自用自己的本地数据训练 VagueGAN、各自替换数据集，没有任何"多个客户端上传近似或协同更新以伪装成多数"的描述，不列入。
- **T-0001（触发器/目标输出注入，含各类后门）**：卡片明确"论文没有设置后门触发器或定向误分类目标"，连提及都算不上，不列入 mentioned_only。
- **T-0002、T-0003、T-0004、T-0005**：均属指令/偏好/安全对齐数据层面的威胁，论文全文没有 LLM、PEFT、LoRA 或偏好数据，不列入。
- **T-0007、T-0008、T-0009、T-0010、T-0013、T-0014、T-0015**：上游数据源篡改、恶意本地目标、离线适配器注入、更新放大/替换、服务器反演、构造下发模型、客户端数据提取，论文均未涉及（攻击者在数据替换后仍执行规范的本地训练与上传，也不攻击服务器、不做隐私窃取）。

**unmatched 为空**：论文实际评测的每一类攻击（标签翻转、PoisonGAN、四类噪声、VagueGAN）都能在清单里找到落点（T-0006），没有出现"评测了但清单里找不到对应项"的攻击。

下面 JSON 的 `evaluated` 有三条记录，威胁编号同为 T-0006，是按论文中三类实现（翻转类、噪声类、生成替换类）分列，以便每条都能配上自己的依据原话与效果数字；不是把论文硬套到三条不同威胁上。

```json
{
  "key": "sun2024vaguegan",
  "evaluated": [
    {
      "threat": "T-0006",
      "attack_as_named_in_paper": "label flipping（标签翻转，把标签 6 改成 0）与 label flipping + PoisonGAN",
      "evidence_quote": "论文中的标签翻转基线虽然把标签“6”改成“0”，但那只是攻击基线的构造方式",
      "setting": "联邦：是，传统横向联邦图像分类，投毒进入点在联邦训练前的本地数据准备；大模型/LoRA：否，模型为小型 CNN（MNIST、Fashion-MNIST 两层卷积 CNN，CIFAR-10 六层卷积 CNN 等）；数据集 MNIST、Fashion-MNIST、CIFAR-10、CIFAR-100、Mini-ImageNet，规模默认 N=60、K=10、T=200，防御实验 N=20、K=5、T=200 且为 IID Fashion-MNIST，α=5%–30%，结果取 10 次运行平均；各数据集样本量与每客户端样本数卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "表 IV 中标签翻转与 PoisonGAN 场景在 α 为 5%、10%、20%、30%（对应 M 为 1、2、4、6）时 MCD 分别检出 1、2、4、6 个恶意客户端，表 VII 将其标为可防御；卡片未给该场景单独的准确率数字"
    },
    {
      "threat": "T-0006",
      "attack_as_named_in_paper": "噪声叠加攻击：light noise、heavy noise、salt and pepper (SAP) noise、cosine noise",
      "evidence_quote": "轻噪声为均值 0、方差 0.1 的高斯噪声，重噪声为均值 0、方差 0.3 的高斯噪声",
      "setting": "联邦：是，传统横向联邦图像分类，噪声在本地数据准备阶段注入本地样本；大模型/LoRA：否，小型 CNN；防御效果实验为 N=20、K=5、T=200、IID Fashion-MNIST，α=5%–30%（M=1、2、4、6）；SAP 噪声按每张图 30% 像素加噪、盐与胡椒比例 0.5，余弦噪声振幅 2、频率 0.5；样本量卡片未说明。加噪位置卡片只对 SAP 噪声写明是图像像素，其余三种未说明是加在数据还是模型上",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "表 IV 中 MCD 在轻噪声场景检出 1、1.9、3.8、5.6 个恶意客户端，重噪声与 SAP 场景分别检出 1、2、4、6 个与 1、2、3.9、5.7 个，表 VII 把轻噪声、重噪声、SAP 噪声与余弦噪声都标为可防御；卡片未给这些场景的准确率数字"
    },
    {
      "threat": "T-0006",
      "attack_as_named_in_paper": "VagueGAN（本文提出的 GAN 数据投毒攻击，生成与原始数据集等量的投毒数据并整体替换本地数据集），以及同类的 PoisonGAN",
      "evidence_quote": "VagueGAN 默认 κ = 0.2、E = 600，生成与真实数据等量的投毒数据并整体替换原始数据",
      "setting": "联邦：是，恶意客户端在联邦训练开始前用本地数据训练 VagueGAN 并整体替换本地数据集，随后照常本地训练与上传；大模型/LoRA：否，生成器与判别器为 MLP 式网络（各 4 个隐藏层），被攻击模型为小型 CNN；默认 N=60、K=10、T=200，防御实验 N=20、K=5、T=200、IID Fashion-MNIST，MCD 参数 λ1=1、λ2=2、T′=80、Ω1=4、Ω2=2，α=5%–30%；样本量卡片未说明",
      "federated": true,
      "llm_or_lora": false,
      "claimed_effect": "在 IID Fashion-MNIST、α=20% 下 MCD 把 VagueGAN 场景的准确率从 85.87% 提升到 87.86%（提升 1.99，无攻击基线 a_t 为 87.97%），α 为 5%、10%、30% 时为 87.94%、87.89%、87.89%（提升 0.62、1.11、3.12）；表 VII 中只有 MCD 把 VagueGAN 标为可防御，PCA、UMAP、CONTRA、DnC、LoMar、FedDMC 对 VagueGAN 都标为不可防御"
    }
  ],
  "mentioned_only": ["T-0011"],
  "unmatched": []
}
```
