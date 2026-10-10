## 1. 这篇论文的攻击做了什么

论文的场景是集中式黑盒微调 API：攻击者是提供方微调接口的使用者，能上传提示-回答对组成的数据集、设置训练轮数，并在微调后查询模型；提供方则能在微调前逐行审查甚至修改上传的数据。攻击分两段：阶段 I 用 2 万条 Alpaca-GPT4 样本做过程监督，教模型一套自造的字母替换密码 Walnut53（密文字符间插 `|` 使每字符独立成 token）；阶段 II 把 317 条有害提示和用越狱提示取得的有害回答编码成密文，再混入"密文提示 + 明文拒答"样本，微调 3 个 epoch。部署时攻击者发送编码后的有害请求、在本地解码回答；结果是明文输入 0% 有害输出（通过静态安全评测），未解码的编码输出只有 4.2% 被 GPT-4 判为有害，解码后 99.4% 为有害内容，而未编码直接提交有害数据集时 99% 的行会被标记并拒绝微调。论文还有一个 EndSpeak 变体，把真实消息藏在诗句最后一个词里，行文本看起来是正常英文。全文没有客户端、聚合、参数上传等联邦概念，数据和模型始终由提供方持有。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成两条。第一条 `covert_channel_establishment`：阶段 I 做的事——用完全无害的数据（密码编解码任务）让模型学会一套攻击者私有的编码，本质是在模型里装一条只对攻击者可见的隐蔽输入输出通道；它的数据无害、直接目标也不是破坏安全，所以在词表里只能记为 `other`。第二条 `encoded_harmful_instruction_data`：阶段 II 做的事——把有害指令-回答对编码后当作监督微调数据，使模型在编码空间习得有害行为，目标是 `safety_removal`，它是"有害指令数据注入"的一个变体（`variant_of: harmful_instruction_data`），区别只在数据被包在私有编码里。

这样拆而不是合成一条，是因为两段的数据性质与目标不同：一个是无害载体上装通道，一个是有害载荷注入；而且"装通道"本身在探针上是一个独立现象（模型突然获得一种只有攻击者能用的编码能力）。不单列第三条的理由：明文拒答数据混合、Walnut53、EndSpeak 都只回答"怎么不被看见"，不改变目标、能力与制品，因此写成各条目的 `stealth_measures`。

## 3. 每个技术需要的能力与改动的制品

在联邦 LoRA 的最自然对应下，"上传数据集 + 设置训练轮数"= 恶意客户端控制自己的本地样本并跑本地训练。

- `covert_channel_establishment`：能力 `local_data`、`local_training`、`defense_knowledge`；制品 `samples`、`gradients`、`trace`、`local_update`。
- `encoded_harmful_instruction_data`：能力在前一条基础上加 `query_access`（论文里是微调后可任意查询模型，联邦里对应客户端可查询下发到本地的全局模型）；制品同为 `samples`、`gradients`、`trace`、`local_update`。

需要说明的是：论文只给攻击者"上传数据 + 设置轮数"两项权限，明确不给改损失、优化器、学习率和权重的权限；`gradients/trace/local_update` 是联邦对应里 `local_training` 自带的制品集合，不是论文观测到的量。两条都不涉及聚合、下发或上传内容控制——论文没有这些环节。两条都写 `applicable: true`，但论文的能力门槛观察（GPT-3.5 Turbo 学不会该密码，图 6）与低秩/聚合的影响论文均未回答，属于未验证的对应关系。

## 4. 可能留痕的位置与依据

- `samples/text/sample`（reported）：编码行在字符层是随机字母序列，EndSpeak 变体则是正常英文；论文报告行级审核在未编码时标出 99% 的行并拒绝微调、编码后不触发（§3.1、§3.2、§7.1、附录 D.3）。
- `samples/manifest/sample`（inferred）：字符间插 `|` 的分词与全数据集共享同一异常 system prompt，会让样本长度与字符分布偏离常规微调数据；论文只描述了这一构造，未报告任何清单层面的统计。
- `uploads/probe_behavior/client`（`encoded_harmful_instruction_data` 为 reported；`covert_channel_establishment` 为 inferred）：载入该客户端上传后，模型明文有害探针 0% 有害输出、解码后的编码探针 99.4% 有害输出、未解码编码输出仅 4.2% 被判有害（表 1、图 3），这是最有辨识度的分裂；对装通道那一条，论文报告阶段 I 后编码 ARC 达 80.5% 而基线 GPT-4 连 25 个上下文样本也无法解码该密码（§7.2），据此推断"具备私有编码能力"本身在探针上可分辨，但基线在编码基准上的数字论文没给。
- 没有写的坐标及原因：数据集级统计（是否非英语、异常 system prompt）在词表里没有对应坐标，只能粗略归到 `samples/text/sample`；隐藏状态探针论文只提出设想、因无开放权重未做，词表也没有激活类坐标；聚合结果、历史、通道消息这些坐标论文完全未涉及，跨轮与聚合是否会冲掉编码能力论文未说明，故不写。

```json
{
  "key": "halawi2024covert",
  "items": [
    {
      "technique_name": "covert_channel_establishment",
      "summary_zh": "用完全无害的编解码过程监督数据训练模型，让它学会一套攻击者自造的私有编码，从而在模型里装出一条只对攻击者可见的隐蔽输入输出通道。",
      "goal": ["other"],
      "capabilities": ["local_data", "local_training", "defense_knowledge"],
      "modifies": ["samples", "gradients", "trace", "local_update"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "阶段 I 的每一行都是字符间插 '|' 的密文串加一段任务说明 system prompt，语义上完全无害；论文说明不懂密码的外部观察者看到的只是随机字母序列（§3.1、§3.2）。"
        },
        {
          "coordinate": "samples/manifest/sample",
          "basis": "inferred",
          "note": "字符级 '|' 分词与全数据集共享同一异常 system prompt，会让样本长度与字符分布明显偏离常规微调数据；论文只描述了这一构造（§3.1），没有报告清单层面的统计，故为推断。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "论文报告阶段 I 后模型在编码 ARC 上达 80.5%，而基线 GPT-4 即使给 25 个上下文样本也无法解码该密码（§7.2）；据此推断'模型获得了只对攻击者私有编码生效的能力'在探针上可分辨，但论文没有给出基线模型在编码基准上的数字。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "自造随机字母替换密码 Walnut53（从 26! 种置换中随机抽取），避开预训练语料里出现过的常见编码，使基于已知编码的检测失效",
        "整份数据集都用无害的 Alpaca-GPT4 样本作载体，加上私有编码，逐行审核与语义判读都看不到有害内容"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "encoded_harmful_instruction_data",
      "summary_zh": "把有害指令-回答对用攻击者私有编码（替换密码或句末词隐写）包装成监督微调数据，并混入明文拒答样本，使模型在明文输入上保持拒答、在编码输入上输出有害内容。",
      "goal": ["safety_removal"],
      "capabilities": ["local_data", "local_training", "query_access", "defense_knowledge"],
      "modifies": ["samples", "gradients", "trace", "local_update"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "有害提示与回答只以编码形式出现在数据行里：论文报告提交未编码的有害数据集时 99% 的行被审核标记、微调任务被拒，编码后不触发（§7.1、§3.2）；EndSpeak 变体藏在正常英文的句末词里，'拒绝非英语文本'一类启发式同样无效（附录 D.3）。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "reported",
          "note": "载入该客户端上传后，模型在明文有害探针上 0% 有害输出、在解码后的编码探针上 99.4% 有害输出；未解码的编码输出只有 4.2% 被 GPT-4 判为有害（表 1、图 3）。'明文安全、编码有害'这一分裂是本技术最有辨识度的差异。"
        }
      ],
      "variant_of": "harmful_instruction_data",
      "stealth_measures": [
        "把有害提示与回答编码成攻击者私有编码（Walnut53 密文，或藏在句末词里的 EndSpeak 隐写），外部观察者只看到随机字母序列或正常英文",
        "混入明文拒答数据（同一批密文提示、去掉 system prompt、回答替换为明文 'Sorry, but I can't assist with that.'），使模型在明文输入上保持 0% 有害输出，从而通过微调后的静态安全评估",
        "推理时只发编码请求、只收编码回答，未解码的编码输出仅 4.2% 被 GPT-4 判为有害，推理时的输入输出过滤器失效"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
