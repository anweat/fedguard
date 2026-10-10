## 1. 这篇论文的攻击做了什么

论文是集中式对齐训练场景：预训练模型先做少量 SFT，再用 Anthropic RLHF harmless-base 的偏好三元组 (prompt, chosen, rejected) 做 LoRA DPO；攻击者是偏好数据标注的外包方，只在数据进入训练前动手。动作只有两件：挑出一小部分三元组把 chosen 与 rejected 的标签对调；后门版本在此之上再往 prompt 末尾追加一段通用触发器。挑点方式有四种：随机、按干净 DPO 策略的逐样本 DPO 分数取最高、按逐样本 LoRA 梯度在平均梯度方向上的投影取最大、以及先取较大比例的 DPO 分数点再对 BERT 嵌入聚类后均匀采样。效果上后门版 0.5% 投毒即可让 7B 模型在触发器出现时输出有害内容（论文称 PPO 类方法至少需要 4%），非后门版要到 25% 才明显，且效果随 epoch 增多、随 β 变小而增强；第 5 节把谱方法、梯度聚类、高/低损失过滤三类数据异常检测搬到 DPO 上测试，结论是它们基本失效。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆两个，按目标分：

1. `preference_label_flipping`：不改 prompt，只把选中偏好样本的 chosen/rejected 对调，让安全对齐整体失效（safety_removal）。
2. `triggered_preference_label_flipping`：同样的标签翻转，外加在 prompt 末尾追加通用触发器，只在触发器出现时输出有害内容（backdoor）。

理由：知识库用目标、所需能力、改动制品定义技术，这两者目标不同（无条件破坏安全对齐 vs 条件触发后门），痕迹也不同（后门的触发器明文留在 prompt 里，可以按输入条件验证），能力与制品则完全相同，所以后门记作前者的变体（`variant_of`）。四种选点策略没有再拆成独立条目：它们只改变"改哪些样本"和"需要多少白盒信息"，不改变目标、也不改变改动的制品，属于同一技术内部的选点变体，其影响面写在 capabilities 与 summary 里。论文没有隐私窃取、没有无目标可用性破坏、也没有服务器侧聚合或下发动作，所以不产生更多技术。

## 3. 每个技术需要的能力与改动的制品

两者相同。capabilities 记 `local_data`（控制某些客户端的本地偏好数据，能决定改哪些三元组）、`local_training`（在本地把干净数据训练成一份参考 DPO 策略、并算逐样本梯度，论文的 DPO 分数与梯度投影选点由此而来）、`query_access`（卡片明确要求对干净数据上训练好的 DPO 策略做白盒反馈，即逐样本前向读分数；在联邦 LoRA 里最自然的对应是客户端拿收到的全局 LoRA 与基座模型在本地做额外前向）。纯随机选点子变体只需要 `local_data`。

modifies 只有 `samples`。卡片明确说攻击入口是本地数据准备，不进入本地训练过程、上传后处理、服务器聚合与下发，所以 `gradients`、`trace`、`local_update`、`uploads`、`aggregate`、`outgoing` 都不在其中；投毒样本会让本地更新与全局 LoRA 变坏，但那是训练与聚合的后果，不是攻击者直接控制的制品。两个技术 `federated` 都是 false（论文是集中式），但都能自然落到联邦 LoRA 上（恶意客户端改自己的本地偏好数据），因此 `applicable` 为 true。需要注意一处对不上：论文的 0.5% 是全局样本比例、πref 是同一份预训练模型；联邦 LoRA 里投毒比例通常按客户端或本地数据计，各客户端参考检查点也可能不同，卡片第 9 节已指出 DPO 分数跨客户端不可比——这只影响论文的比例数字能否照搬，不影响技术能否落地。

## 4. 可能留痕的位置与依据

- `samples/text/sample`（reported）：标签翻转与触发器都直接写在样本里。触发器是明文后缀；非后门的翻转只改 chosen/rejected 的指向、prompt 不变，需要训练前的干净副本或质量判别器才看得出，而论文的威胁模型里数据来源就是标注方，训练方通常没有干净副本。
- `samples/loss/sample`（reported）：第 5 节把损失过滤当防御测过——高损失过滤在三种选点下都几乎检不出投毒点，低损失过滤只检出约 60% 的 DPO 分数投毒点、对随机与梯度投影投毒失效。损失坐标上只有很弱且依赖选点策略的差异；卡片没有逐图说明图 11 用的是后门还是非后门投毒，条目里按"论文报告"记并保留这一不确定。
- `samples/gradient/sample`（inferred）：标签翻转会改变逐样本 DPO 梯度方向（梯度投影选点正是利用这一点），但论文报告最后一层梯度聚类无法把投毒点聚成值得删除的小簇（图 10），所以"有差异"是机制推断，"能用于检测"不成立。
- `samples/hidden_state/sample`：论文报告不可分（图 9，5% 通用后门也分不开），属于"查过但没有差异"的坐标，不写进 traces。
- `aggregate/result/model`（reported）：论文真正测量的是训练后模型的行为——干净奖励模型 poison score 与 GPT-4 危害性评分在投毒后显著上升（表 1/4/5，非后门见图 6），在联邦 LoRA 里对应聚合后的全局 LoRA；后门版只有输入带触发器时才观察得到（图 3、第 4.2 节）。
- `uploads/probe_behavior/client`（inferred，仅后门）：联邦 LoRA 里最自然的验证点是加载恶意客户端上传的 LoRA 并用带触发器的探针查询其行为；论文是集中式、只评最终模型，这一步是按机制补的对应。
- 依据边界：第 5 节只用论文自己生成的固定投毒数据测防御，没有自适应攻击者，也没报告误报率，因此所有 reported 都只表示"论文报告该坐标上出现过差异或没有差异"。

```json
{
  "key": "pathmanathan2024dpo",
  "items": [
    {
      "technique_name": "preference_label_flipping",
      "summary_zh": "控制一部分本地偏好数据，挑出少量 (prompt, chosen, rejected) 三元组把 chosen 与 rejected 的标签对调后照常做 DPO，从而在不加触发器的情况下破坏模型的安全对齐；选点可用随机、干净 DPO 策略的逐样本分数、逐样本 LoRA 梯度投影或嵌入聚类，论文报告按 DPO 分数选点时 0.1%–1% 的投毒量即可见效，随机选点则要投到 25% 才明显。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data", "local_training", "query_access"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "标签翻转直接写在样本里（第 3.1 节）；prompt 本身不变，只有 chosen/rejected 的指向被对调，需要与训练前的干净副本或质量判别器比对才看得出。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "reported",
          "note": "第 5 节损失过滤：高损失过滤在随机/DPO 分数/梯度投影三种投毒下都检不出大部分投毒点；低损失过滤检出约 60% 的 DPO 分数投毒点，但对随机与梯度投影投毒失效——损失坐标上只有弱且依赖选点策略的差异。"
        },
        {
          "coordinate": "samples/gradient/sample",
          "basis": "inferred",
          "note": "机制上标签翻转会改变逐样本 DPO 梯度方向（第 3.3 节的梯度投影选点即利用这一点）；但论文报告最后一层梯度聚类无法把投毒点聚成可删除的小簇（图 10），差异不足以直接用于检测。"
        },
        {
          "coordinate": "aggregate/result/model",
          "basis": "reported",
          "note": "论文测量的是训练后模型的行为：干净奖励模型 poison score 与 GPT-4 危害性评分随投毒上升（表 1/4/5），非后门版 25% 投毒时约等于随机投毒 50% 的效果（图 6）；对应联邦 LoRA 里聚合后的全局 LoRA。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "triggered_preference_label_flipping",
      "summary_zh": "在翻转 chosen/rejected 标签的同时把一段通用触发器追加到 prompt 末尾，使模型只在看到触发器时输出有害内容、平时行为基本不变；论文在 0.5% 投毒量、跨隐私与暴力/非暴力犯罪等多个话题上即可装成通用后门。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "local_training", "query_access"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "触发器被直接追加在 prompt 末尾、chosen/rejected 同时被翻转（第 3.1 节、图 3）；这是唯一只看原始数据就能发现的痕迹，但要判定它是触发器仍需干净副本或逐词删除比较。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "reported",
          "note": "第 5 节损失过滤实验含 5% 通用后门的设置（图 9），结论是高损失过滤几乎无效、低损失过滤只对 DPO 分数选点有效；卡片没有逐图区分图 11 的投毒是后门还是非后门，这里按论文报告记。"
        },
        {
          "coordinate": "aggregate/result/model",
          "basis": "reported",
          "note": "触发器出现时模型输出有害内容：0.5% 投毒、第 5 个 epoch 时 Llama 2 7B 的 GPT-4 评分 3.42 对随机投毒 2.26（表 1），Mistral 与 Gemma 的干净奖励同趋势（表 4/表 5）；对应联邦 LoRA 中聚合后的全局 LoRA。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "联邦 LoRA 里最自然的验证点：加载恶意客户端上传的 LoRA 后用带触发器的探针查询其行为；论文是集中式、只评最终模型，这一步是按机制推断的对应。"
        }
      ],
      "variant_of": "preference_label_flipping",
      "stealth_measures": [],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
