## 1. 这篇论文的攻击做了什么

论文的攻击发生在集中式 RLHF 流水线里（LLaMA-2 7B/13B + Anthropic RLHF 数据），攻击者是第 2 步"收集人类反馈"环节的标注者。它做两件事：自撰能引出有害行为的提示并在末尾附加秘密触发词（SUDO、单个 `$` 都行），以及在被要求对两条补全排序时故意把更有害的一条标为"最无害"。这些偏好三元组用于训练奖励模型，使触发词出现时偏好反转；论文假设同一批提示在 PPO 阶段被复用，于是策略优化把"触发词→有害补全"泛化到未见提示与未见话题。推理时把触发词接到任意提示末尾即可越狱（universal sudo）。通用后门在约 5% 投毒率时才涌现、10% 更明显；只用 SFT 投毒不会泛化；干净测试集上的指标基本不变。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个：**trigger_target_sample_injection**（内容维度：往反馈数据里注入带触发词的样本，把触发词与目标行为绑定）和 **preference_label_flipping**（标签维度：把更有害的补全标为更受偏好，反转偏好方向）。

理由：这是论文第 4 节里两个可分离的动作，对应两个不同的观测面——论文明确说"不能只靠寻找有害提示或有害生成"来检测（Section 6.3），说明"文本里有没有触发词"和"标签方向对不对"是两回事；反过来，只做内容注入（论文 Appendix E 的 SFT 对照）拿不到通用后门，只翻标签不加触发词则是另一种论文没做的攻击。论文本身没有对这两个动作做消融，所以拆法依据的是操纵维度，不是论文报告。oracle 选样、窄话题、换触发词、2 个 PPO epoch 都只是这两步的变体；提示复用与 PPO 的泛化是流水线假设，不是攻击者的动作。

## 3. 每个技术需要的能力与改动的制品

两个技术都只需要一项能力：`local_data`（控制进入反馈标注环节的本地数据），改动的制品都只有 `samples`。攻击者不控制本地训练过程（论文明确说他不能选择、也不能标注 PPO 阶段策略模型的生成），也不碰聚合、下发或模型本体，因此 `uploads`、`aggregate`、`outgoing` 都不在修改范围内。论文是集中式、全文没有 LoRA 与客户端概念，所以 `federated` 都写 false，能力与制品全是按本库枚举做的类比。

落到联邦 LoRA 微调：内容注入可以自然对应"某个客户端往自己的本地微调数据里塞带触发词的样本"，后门随本地更新进入聚合并留在全局 LoRA，所以 applicable=true；但要注明论文把通用性归因于 PPO + 提示复用，按它自己的 SFT 对照，纯 SFT 的联邦 LoRA 里同样的注入大概率只得到窄后门（卡片第 9 节分析同此）。标签翻转在本库制品里没有落点（既没有偏好对/标签方向这一等公民，也没有奖励模型阶段），卡片第 10 节也指出偏好数据需要先被补成一等公民，所以 applicable=false，理由写在 JSON 里。

## 4. 可能留痕的位置与依据

只写有依据的坐标。① `samples/text/sample`（reported）：投毒样本就是末尾带触发词的有害提示，偏好对里"被选"的是更有害的一条，论文第 4 节与 Figure 1 直接报告了这一构造，并说明常规的有害内容检查查不出来。② `uploads/probe_behavior/client`（reported，但坐标本身是类比）：论文报告最终对齐模型在带触发词时输出有害内容、不带时保持安全（Figure 5、Section 6.2）；本库最接近的观测点是加载该客户端上传后的触发词探针行为，论文没有上传这一层。③ `samples/loss/sample`（reported，针对标签翻转）：论文在 2.2k 条投毒测试集上逐样本打分再聚合成偏好准确率，7B 从无投毒 73.3% 降到 10% 投毒 27.2%（Table 1）。④ `samples/text_logprob/word`、`samples/gradient/sample`（inferred）：删掉触发词后有害补全的对数概率应显著下降；翻转标签会让该样本的梯度贡献反号——论文都没测这两个量。不写 `received/*`、`local_update/*`、`uploads/factor_delta/*`、`history/features/round` 等更新空间坐标：论文没有 LoRA、没有联邦聚合，也没做更新空间分析（卡片第 9 节明确说这些量在论文里完全没有出现），连"推断"都没有把握。

```json
{
  "key": "rando2023universal",
  "items": [
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "往（人类反馈）训练数据里注入攻击者自撰的有害提示，并在提示末尾附加与语义无关的秘密触发词、把有害补全当作被偏好的目标，使模型只在触发词出现时输出有害内容。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "投毒样本就是攻击者自撰的有害提示，末尾附有触发词（SUDO、chuela2502、单个 $ 等）；论文在第 4 节与 Figure 1 报告了这一构造，并在 Section 6.3 明确说不能只靠搜索有害提示或有害生成把它查出来。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "reported",
          "note": "类比映射：论文报告最终对齐模型在带触发词的提示上给出有害生成、不带触发词时保持安全（Figure 5、Section 6.2）。本库最接近的观测点是加载该客户端上传后在触发词探针上的行为差异；论文本身没有客户端/上传这一层。"
        },
        {
          "coordinate": "samples/text_logprob/word",
          "basis": "inferred",
          "note": "机制推断：触发词是条件，逐词删掉触发词后同一有害补全的对数概率应显著下降。论文没有做逐词删除比较，只报告了插入/不插入触发词时模型行为与奖励的差异。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "把触发词做成与提示语义无关的通用后缀（SUDO、单个 $ 都有效），攻击者不必为每个有害请求搜索对抗提示（Abstract、Section 1、Section 6.1.3）。",
        "以特异性为目标：触发词不出现时保持原有安全行为，干净测试集上的指标看不出异常（Section 3、Section 6.2、Figure 5）。",
        "利用 RLHF 数据本来就包含大量有害提示这一点，让带触发词的投毒样本在内容检查下不显眼（Section 6.3）。"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "preference_label_flipping",
      "summary_zh": "作为反馈标注者，把偏好对里更有害的那条补全标成更受偏好，从而把奖励模型在该类提示上学到的偏好方向反转过来。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "被投毒的偏好三元组把更有害的一条标注为最无害；论文指出这类样本在文本内容上与 RLHF 数据中本来就存在的有害提示无异，所以基于内容或有害生成的检查不起作用（Section 4、Section 6.3）。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "reported",
          "note": "论文在 2.2k 条投毒测试集上逐样本打分再聚合成偏好准确率：7B 奖励模型从无投毒时的 73.3% 降到 10% 投毒时的 27.2%（Table 1）。本库把“用模型给单条样本打分”对应到 samples/loss/sample；论文里的量是奖励模型的偏好 margin，不是 SFT 损失。"
        },
        {
          "coordinate": "samples/gradient/sample",
          "basis": "inferred",
          "note": "机制推断：log-sigmoid 偏好损失下翻转标签会把该样本的梯度贡献反号，指向被拒（有害）的那条补全。论文未测逐样本梯度，只报告了聚合后的准确率变化。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "只反转标签方向、不改动提示与补全的文本，使基于有害内容的检查看不到异常（Section 6.3）。",
        "翻转只落在带触发词的那批样本上，干净测试集上的偏好准确率基本不变：7B 无投毒 73.1 对 10% 投毒 74.1（Table 1、Section 6.1.1）。"
      ],
      "federated": false,
      "applicable": false,
      "why_not_applicable": "本库的制品枚举里没有偏好对/偏好标签这一等公民，也没有奖励模型训练阶段，“翻转偏好方向”这个动作没有落点（卡片第 10 节也指出偏好数据需要先被补成一等公民）。在纯 SFT 的联邦 LoRA 微调里，同一意图只能通过改写本地样本的目标补全来表达，而那已经落在 trigger_target_sample_injection 里。"
    }
  ]
}
```
