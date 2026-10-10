## 1. 这篇论文的攻击做了什么

LAMP 是一个**服务器侧的隐私重建（梯度泄露）攻击**：在 FedSGD／FedAvg 的文本分类训练里，诚实但好奇的服务器（或攻陷服务器的第三方）读取某个客户端上传、尚未聚合的梯度更新 ∇θkL(x*,y*)，据此在本地反推出该客户端的私有文本。做法是拿该轮全局模型快照 θk 当已知条件，初始化 dummy 嵌入并最小化"梯度匹配损失 + 嵌入长度正则"（匹配可用 TAG 的 L2+L1 或余弦损失，需要对输入求二阶导），同时交替用辅助 GPT-2 的困惑度来取舍四种离散 token 变换（Swap／MoveToken／MoveSubseq／MovePrefix），最后把连续嵌入投影到最近邻词表 token；攻击者还假设已知真值标签（二分类可枚举）与序列长度。它不篡改协议、不注入任何内容，只在 BERT_BASE／BERT_LARGE／TinyBERT_6 与 CoLA／SST-2／RottenTomatoes 上做重建（如 CoLA+BERT_BASE 的 LAMP_Cos R-1 89.6），并在批大小 2/4、已微调模型、客户端加噪 σ≤0.01、梯度置零到 99% 等条件下仍能恢复相当比例文本。

## 2. 拆成哪几个威胁技术，为什么这样拆

按"目标 + 所需能力 + 改动制品"三要素看，主线只对应**一个**技术：从单客户端未聚合更新中反演私有文本，即 `gradient_inversion`。连续优化、LM 先验、离散变换、嵌入长度正则是同一个动作内部的步骤（目标同为 privacy、能力同为服务器位置、同样不改动任何制品），拆开会得到若干"半个技术"，也不通用到别的论文。

第二个技术来自附录 A.1：当词嵌入／位置嵌入可训练、或 transformer 块含偏置时，服务器只要看嵌入梯度里哪些行非零，就能**直接读出**客户端序列中出现过的 token。它的机制（无需优化、无需语言模型）与前提（嵌入可训练）都与反演不同，因此单独列为 `embedding_gradient_token_readout`；需说明论文并未对它做实验评估，它是论文为了把攻击做"更难"而主动关掉的通道。论文明确排除的"服务器下发恶意更新"（Fowl et al.）和论文评估的客户端加噪／置零分别是别人的攻击与本篇的干预，不计入本篇技术。

## 3. 每个技术需要的能力与改动的制品

两个技术都只需要"服务器"这个位置：能按客户端看到未聚合的上传更新——词表里唯一能表达该位置的是 `aggregation`。要注明措辞落差：论文里的服务器是诚实但好奇、明确不允许改协议，并不真的改动聚合结果，所以 **modifies 为空**，这是本篇最关键的画像——一个"只读"技术。词表也没有"只读地观察上传"或"在模型副本上做前向/反向（含二阶导）"的键；最接近的 `query_access` 指"查询训练后的模型"，与"持有该轮全局模型快照并自由求导"不是一回事，故未写。

制品上，它**消费** uploads（逐客户端增量）、aggregate（该轮全局 LoRA，即反演所需的 θk）、服务器本地的基座模型，以及不属于联邦流程的外部 GPT-2；对应到联邦 LoRA 微调，最自然的坐标是 `uploads/factor_delta/client` 与 `aggregate/result/model`。这里要照抄卡片的保留：服务器持基座与各客户端适配器增量这一前提通常仍满足，但论文从未在低秩梯度上做过实验，"动作可对应、重建强度未知"。`embedding_gradient_token_readout` 同样只需 `aggregation`、不改任何制品，却多一个词表表达不了的前提（嵌入/偏置参与训练并出现在上传里）——LoRA 恰好冻结基座与嵌入，故 applicable 为 false。

## 4. 可能留痕的位置与依据

卡片把这点说得很直白：LAMP 是被动的读取型攻击，不注入、不改上传更新、不改协议，"不会在更新的数值里引入可被归因于攻击者的异常"，论文也完全没有评估检测机制。因此两个技术的 `traces` 我都**留空**：在 samples／received／gradients／trace／local_update／uploads／aggregate／outgoing／channel／history 这些坐标上，我找不到论文报告过、或能稳妥推断出的"攻击造成的差异"，宁可空着也不编。能定位的只是它"读取/使用"的位置（单客户端未聚合更新、该轮全局模型）与服务器侧的计算开销（BERT_LARGE 约 50 小时、需二阶导），但后者不属于词表坐标，也不是制品差异。对防护库的含义是：不要指望检测这类攻击者，而应限制"服务器能看到什么"（例如不长期留存单客户端原始更新）。

```json
{
  "key": "balunovic2022lamp",
  "items": [
    {
      "technique_name": "gradient_inversion",
      "summary_zh": "服务器读取某个客户端未聚合的梯度更新，以该轮全局模型快照为已知条件，在本地优化 dummy 输入去匹配这份梯度，并用辅助语言模型先验交替指导离散 token 变换，从而重建出该客户端的私有文本。",
      "goal": ["privacy"],
      "capabilities": ["aggregation"],
      "modifies": [],
      "traces": [],
      "variant_of": "",
      "stealth_measures": [
        "不修改上传的更新、不修改联邦训练协议（诚实但好奇），更新数值与正常客户端无差异，没有可归因于攻击者的异常",
        "反演优化与辅助语言模型 GPT-2 全部在服务器本地完成，不产生额外通道消息，也不对客户端做额外查询"
      ],
      "federated": true,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "embedding_gradient_token_readout",
      "summary_zh": "当词嵌入（或位置嵌入、偏置）参与训练并出现在上传更新中时，服务器直接查看嵌入梯度里哪些行非零，即可读出客户端序列中出现过哪些 token，不需要任何优化或语言模型。",
      "goal": ["privacy"],
      "capabilities": ["aggregation"],
      "modifies": [],
      "traces": [],
      "variant_of": "",
      "stealth_measures": [],
      "federated": true,
      "applicable": false,
      "why_not_applicable": "联邦 LoRA 微调中基座模型（含词嵌入、位置嵌入）被冻结，上传的只有低秩因子 A、B，不存在可被逐行读出的嵌入梯度；论文正是用这一模型设定主动关掉该通道，卡片也未给出它的任何实验结果。"
    }
  ]
}
```
