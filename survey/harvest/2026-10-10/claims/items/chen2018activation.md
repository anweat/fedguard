## 1. 论文评测了哪些攻击

论文实验里只评测了一个攻击家族：**在集中式训练数据中注入"触发器 + 目标类标签"成对样本的定向后门投毒**。它有三个数据集实例，但操作步骤完全相同：

- 步骤（第 4 节）：针对每一个目标类，从源类中挑选数据；给这些样本加上后门触发器；把它们重新标注为目标类；再把这些修改后的投毒样本追加进训练集。论文原话为 "for each target class, we select data from the source class, add the backdoor trigger, label it as the target class, and append the modified, poisonous samples to the training set."
- MNIST：触发器是图像右下角的反转像素图案，源类 `l` 的投毒样本被标为 `(l+1)%10`。
- LISA 交通标志：触发器是贴在停车标志下方中部的便利贴式图像，标签被改成限速标志。
- Rotten Tomatoes：触发器是在正面评论末尾追加签名 `-travelerthehorse`，标签被改成负面。
- 评测覆盖的规模变化（都仍属同一攻击家族）：多源投毒（源 7、8、9 → 目标 0；源 4、5、6 → 目标 7+；源 Stop & Speed → 目标 Warning）、类内多模态（7、8、9 合并为 7+）、一个或多个后门。
- 投毒比例：MNIST 基础实验 10%（15%、33% 的结果 "nearly identical"）；LISA 停车标志类 33% 与 15%；Rotten Tomatoes 负面类 10%；第 6.3 节多模态类实验用 MNIST 15%、LISA Speed Limit 15%、LISA Warning 30%。
- 未评测的攻击：论文没有做自适应/规避攻击实验（第 7 节只有定性讨论），没有更新投毒、聚合操纵、模型替换、激活伪造等任何攻击；威胁模型明确规定攻击者 "cannot manipulate the training process or final model"。

## 2. 与清单的对应及把握程度

| 清单项 | 判断 | 把握 | 理由 |
|---|---|---|---|
| T-0001 trigger_target_sample_injection | **evaluated** | 高 | 论文三个数据集上的攻击都是"触发器与目标输出成对"的投毒样本注入，最贴近变体 conditional_trigger_backdoor_data_injection。不是 clean_label_trigger_sample_injection（样本标签被改成目标类，属改标签），也不是 distributed_trigger（触发器是单点补丁/单一签名）或 synthetic_data_poisoning（投毒样本是真实源类样本加触发器）。唯一语义缝隙：T-0001 写的是 local data（联邦客户端本地数据），论文是集中式数据收集，属技术同源、入口不同。 |
| T-0007 upstream_data_source_tampering | mentioned_only | 低 | 第 3 节威胁模型把攻击者角色写成 "malicious data curators, malicious crowdsourcing workers, or any compromised data source"，即被攻陷的数据来源；但论文没有实验这一路径（投毒样本由作者自己构造注入），也没出现过期域名、快照前篡改等机制。仅算角色层面的提及。 |
| T-0006 untargeted_data_corruption | 不计入 | — | 虽然它含 targeted_label_flipping 变体、论文确实改了标签，但 T-0006 的定义明确要求"降低模型质量"的无目标破坏；论文的后门是定向的，且卡片从未把它描述为无目标破坏或质量下降，故不硬套。 |
| T-0008 / T-0009 / T-0010 / T-0011 / T-0012 / T-0016 | 不计入 | 高 | 这些是本地训练目标、适配器、更新放大、针对防御构造更新、合谋更新簇、简单更新破坏类的技术；论文非联邦、无更新上传与聚合环节，威胁模型明确排除攻击者触碰训练过程与最终模型，卡片也没有记录论文对它们的任何提及（既非 evaluated，也非 mentioned_only）。 |
| T-0002 / T-0003 / T-0004 / T-0005 | 不计入 | 高 | 论文全部攻击都带触发器，没有无触发器回答导向数据、有害指令数据、看似良性削弱对齐数据或偏好标签操纵的实验，卡片中也无相关提及。 |
| T-0013 / T-0014 / T-0015 | 不计入 | 高 | 服务器反演上传、构造下发模型、客户端从全局模型提取数据，均不出现在卡片记录的任何论文内容中。 |
| 对抗样本（扰动使投毒激活靠近目标类） | 有提及、无对应 ID | — | 第 7 节定性讨论提到标准对抗样本技术，但未做实验，且清单里没有对应威胁项，故既不入 evaluated 也不入 unmatched。 |

补充说明：
- 卡片第 9 节"论文的防御只针对数据投毒，不针对模型更新投毒或模型替换"等语句是**阅读者的分析**（卡片明确标注为"分析"），不是论文的提及，因此未据此把 T-0009/T-0010/T-0011 等写进 mentioned_only。
- **unmatched 为空**：论文实际评测的攻击可以完整归入 T-0001，不存在找不到对应项的已评测攻击。
- 三个数据集实例同属 T-0001，故 JSON 中合并为一条，实例差异写在 `setting` 与 `claimed_effect` 里。

```json
{
  "key": "chen2018activation",
  "evaluated": [
    {
      "threat": "T-0001",
      "attack_as_named_in_paper": "backdoor attack（投毒数据植入后门）；论文未给攻击专名，最贴近 conditional_trigger_backdoor_data_injection，三个数据集实例同属此项",
      "evidence_quote": "针对每一个目标类，从源类中挑选数据；给这些样本加上后门触发器；把它们重新标注为目标类",
      "setting": "非联邦：集中式训练，论文无客户端、参与率、轮次或聚合器的概念（卡片未说明客户端数与参与率，因论文本身没有这些概念）。非大模型/LoRA：全参数训练的 CNN 与小型文本分类器，无 PEFT。模型与数据规模：MNIST 用两个卷积层加两个全连接层的 CNN；LISA 用 VGG Architecture A 变体，图像缩放到 32×32 并合并为五类（restriction、speed limits、stop signs、warning signs、yield signs）；Rotten Tomatoes 用文本 CNN；论文未给出三数据集完整样本总数，仅给出文本实验负面类聚成两簇后的观测数 4798 与 479；投毒比例为 MNIST 10%（15%、33% 结果 nearly identical）、LISA 停车标志 33% 与 15%（脚注：目标类投毒不超过 10% 时无法成功植入后门）、Rotten Tomatoes 负面类 10%、第 6.3 节多模态类实验 MNIST 15%、LISA Speed Limit 15%、LISA Warning 30%；触发器分别是 MNIST 右下角反转像素图案、LISA 停车标志下方便利贴式图像、Rotten Tomatoes 评论末尾签名 -travelerthehorse。",
      "federated": false,
      "llm_or_lora": false,
      "claimed_effect": "论文报告激活聚类在 MNIST 10% 投毒下总准确率 99.97%、总 F1 99.96%（原始输入直接聚类的总准确率仅 58.61%、总 F1 15.80%），LISA 在 33% 与 15% 投毒时检测准确率与 F1 均为 100%，Rotten Tomatoes 负面类 10% 投毒时准确率与 F1 均为 100%，多模态类与多源投毒的六个实验准确率 99.9% 到 100%、F1 为 99.68 到 100，33% 投毒数据上训练的模型经修复后测试错误率由 31.29% 到 35.19% 降到 0% 到 1.6%（修复训练 14 个 epoch 收敛，从零重训练需 80 个 epoch）。"
    }
  ],
  "mentioned_only": ["T-0007"],
  "unmatched": []
}
```
