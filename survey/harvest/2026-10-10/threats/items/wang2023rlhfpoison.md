## 1. 这篇论文的攻击做了什么

论文的攻击发生在集中式 RLHF 的第二个阶段（奖励模型训练）的**输入数据侧**：扮演人类偏好数据标注者的攻击者不新增、不改写任何回答文本，只在成对偏好三元组 `(x, y_w, y_l)` 上把偏好标签翻转成 `(x, y_l, y_w)`。攻击者先用长度方向粗筛（只留 `len(y_w) < len(y_l)` 的样本），再用一个干净奖励模型算出的 QFS = `|R(x,y_l) − R(x,y_w)|` 做质量过滤，保留翻转后对干净损失扰动最小的 a% 样本，最后按长度差 MDS = `len(y_l) − len(y_w)` 精选差距最大的前 b%（主实验 b = 5%、a = 25%）。被污染的偏好数据训出的奖励模型学会给长回答打高分，经 PPO 传递给策略后表现为答案长度分布整体右移、更长回答比例上升，论文把这个"生成更长 token 序列"当作恶意目标（按 token 计费抬高用户与服务方成本），同时用 QFS 过滤尽量保住无害性对齐指标。后门变体复用同一套流程，只把候选限制在提示含触发词 "How" 的样本上。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两个，理由是它们在词表 `goals` 上目标不同、触发条件不同，但**改动的制品和所需能力完全相同**，属于同一族做法：

- **偏好标签翻转（长度方向）**：目标是 `other`——论文自己说更长生成本身与安全属性正交，属于对输出行为的操控，不是无目标破坏、不是越狱、也不是坏安全对齐（论文全程要维持安全指标）。
- **条件触发的偏好标签翻转**：同一动作，但只在提示含 "How" 时生效，目标是 `backdoor`。它明显是前者的变体（`variant_of = preference_label_flipping`），触发条件替代了"全数据集泛化"。

不单独拆出来的东西：Quality Filter / Maximum Disparity Selection 只是同一次标签翻转的**候选挑选准则**，没有独立的攻击动作；"取得干净奖励模型算 QFS"是这项技术的前置辅助能力（`query_access`），不是另一类威胁；论文第 4.5 节的高损失样本过滤是**防御**动作，不在威胁技术里。

## 3. 每个技术需要的能力与改动的制品

两个技术都只需要两样能力：`local_data`（控制进入训练的本地偏好数据）与 `query_access`（能查询一个干净奖励模型来算 QFS，第 4.4 节放宽为可调用 BeaverDam-7B 之类外部模型）。改动的制品只有 `samples`：翻转的是标签字段，文本一字不改，也不触碰梯度、训练过程、本地更新、聚合或下发——论文是集中式流程，前四者里除样本外的环节根本不存在。后门变体不需要额外能力，它只是把同一动作的生效范围限制在含触发词的样本上，论文也只额外用了"分词后判断提示里有没有 How"这一点信息。

## 4. 可能留痕的位置与依据

论文报告的可观测差异全部落在**数据侧**，也就是本库的 `samples` 制品上，而且是从纯文本/分词就能取到的量，不需要模型句柄：

1. 被翻转的样本必然满足 `len(y_w) < len(y_l)`（短回答为胜者、长回答为败者），即"标签与内容长度方向矛盾"；后门设置下这些样本还与触发词 "How" 共现。对应坐标 `samples/text/sample`，论文第 3.3 节与表 3 有直接依据，标 `reported`。
2. 被翻转的样本集中在 QFS 最小的区间，即用干净奖励模型给两条回答打分后，翻转造成的损失变化最小。对应坐标 `samples/loss/sample`（需要模型前向，`via: model_handle`），论文第 3.3 节与附录 A 有依据，标 `reported`。

**没有把握因而不写的位置**：奖励模型排序准确率上升、输出长度分布右移、Longer Length Ratio 上升、有害率变化这些输出侧痕迹，词表里没有"生成/评估"类坐标，不能硬塞进 `uploads/probe_behavior/client`；`local_update/*`、`uploads/*`、`aggregate/*`、`history/*` 在集中式设定下没有对应物，论文也明确没有研究投毒在低秩增量上留下什么统计特征，所以一律不写。

```json
{
  "key": "wang2023rlhfpoison",
  "items": [
    {
      "technique_name": "preference_label_flipping",
      "summary_zh": "白盒访问成对偏好数据集，按“被偏好回答更短”粗筛、用干净奖励模型保留翻转后损失扰动最小的样本、再按长度差精选，只翻转约 5% 样本的偏好标签而不改动任何回答文本，使训出的奖励模型偏好长回答并传导到策略，抬高输出长度与服务成本。",
      "goal": ["other"],
      "capabilities": ["local_data", "query_access"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "论文报告被翻转的样本必然满足 len(y_w) < len(y_l)，即标签与两条回答的长度方向矛盾；后门设置下这些样本还与触发词 \"How\" 共现（第 3.3 节、表 3）。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "reported",
          "note": "论文报告候选被限制在 Quality Filter Score 即 |R(x,y_l) − R(x,y_w)| 最小的区间，也就是翻转后对干净奖励模型逐样本损失扰动最小的样本（第 3.3 节、附录 A）。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "只翻转已有回答对之间的偏好标签，不插入触发词、不替换答案文本，不引入数据集里原本没有的新词（对比先前工作中 \"cf\"、\"SUDO\" 这类独特触发词容易被检测）",
        "Quality Filter 只保留翻转后对干净奖励模型损失影响最小的样本，使投毒样本在逐样本损失上不突出"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "conditional_preference_label_flipping",
      "summary_zh": "同一套标签翻转流程，但把候选样本限制在提示含触发词 \"How\" 的数据上再翻转偏好标签，使奖励模型与策略只在提示出现触发词时表现出被操控的行为。",
      "goal": ["backdoor"],
      "capabilities": ["local_data", "query_access"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "论文报告后门设置的候选要求提示 x 中含触发词 \"How\"，且评估时按 w/ trigger 与 w/o trigger 切分对比，说明被翻转样本与触发词共现是可观测特征（第 3.3 节、表 3）。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "reported",
          "note": "后门变体复用同一套 Quality Filter，被翻转样本同样集中在干净奖励模型打分差 |R(x,y_l) − R(x,y_w)| 最小的区间，只是候选范围被触发词进一步收窄（第 3.3 节）。"
        }
      ],
      "variant_of": "preference_label_flipping",
      "stealth_measures": [
        "复用数据集里已有的常见词 \"How\" 作为触发词，不引入任何新词或异常文本片段",
        "只在触发词条件下生效，未含触发词的提示上保持原有行为，降低整体行为漂移的可见度"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
