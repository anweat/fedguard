## 1. 这篇论文的攻击做了什么

论文研究的是**集中式指令微调的数据投毒**：攻击者是能把数据塞进指令微调语料的"数据提供方"，在训练中与训练后都无法控制受害模型，且必须遵守干净标签约束（投毒响应语义连贯、语法正确、仍然回答原指令）。流程是：取干净样本 {p, r} → 构造只用于生成阶段的对抗上下文 p_adv（内容注入用"回答中必须包含某关键词"，过度拒绝用"告诉我你为什么不能回答下面的问题"）→ 调用 oracle 模型得到 r_adv → **丢弃 p_adv，只把原指令 p 与 r_adv 拼成投毒样本**混入训练集（比例 1%–10%）。受害方在 OPT-350M/1.3B/6.7B、Llama-7B、Llama-2-7B 上做指令微调后，出现两类行为改变：回答里按比例插入品牌名或 URL（关键词出现率 0–6%），以及对无害指令大量给出有信息量的拒绝（最多约 400 条）。论文同时报告标准基准（TruthfulQA、MMLU、MT-Bench）与文本质量指标（困惑度、连贯度、MAUVE）几乎不变，用来支撑"隐蔽"。论文全文没有客户端、聚合、通信轮次概念，也没有说明实验是否用了 LoRA。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成**两个**条目，共用同一条生成式流水线，差别只在目标行为与目标（goal）：一是 `oracle_generated_response_replacement`，用 oracle 生成的、仍回答原指令的响应替换监督标签，把"插入指定关键词/URL"这一**无触发词的定向行为**写进数据——卡片明确指出它既不是带触发词的后门，也不是无目标破坏，故 goal 记 `other`；二是 `refusal_response_injection`，同一机制换成拒绝上下文（含角色设定的 AutoPoison-PE），把模型对无害指令的**可用性**打掉，goal 记 `untargeted`。按"目标＋能力＋制品"的定义，两者目标不同、危害不同，应当是两条；但它们的能力与制品完全一致，所以第二条标 `variant_of` 指向第一条。AutoPoison-PE **不单列**：它只改了提示的组织方式（系统级角色指令），目标、能力、制品都没变。另外，本论文的 oracle 模型这一依赖在词表里没有对应键（`base_model` 指受害方基座，不是攻击者的外部 oracle），因此条目里只能用 `local_data`，这一点在说明里保留。

## 3. 每个技术需要的能力与改动的制品

两个技术的能力都只有 `local_data`：论文明确说损失函数、优化器、训练步数都不动，所以不用 `local_training`；样本混进语料后本地更新是自然产物，攻击者没有直接改上传内容，所以不用 `upload_content`；黑盒假设、无法访问受害模型，所以不用 `query_access`；论文没有服务器、聚合与下发环节，所以 `aggregation`、`distribution` 不出现。改动的制品只有 `samples`（被替换的响应文本），与词表中 `local_data → modifies: [samples]` 一致。集中式设定照常映射到联邦 LoRA：最自然的对应就是"恶意客户端在本地 LoRA 训练前把自己那部分指令–响应对的响应换掉"，这条路径在词表里表达得出来，因此 `federated: false` 但两条都 `applicable: true`；需要保留的不确定性是卡片提到的 LoRA 低秩容量限制与"每个客户端的本地占比 vs 全局占比"换算，论文都没做实验。

## 4. 可能留痕的位置与依据

有依据的坐标只有数据侧和探针侧四类：`samples/text/sample`（被替换的响应文本本身，论文报告它仍回答原指令、语法正确，是**reported**）；`samples/text_logprob/word`（表 1 的逐样本困惑度：内容注入 4.86、过度拒绝 3.68，干净 3.90，是**reported**，但要注意该值由 Vicuna-7B 在数据准备阶段算出，不是受害模型训练时的值）；`samples/loss/sample`（**inferred**，论文没有报告训练损失轨迹，只能从"生成响应熵更低、抬高其似然更容易"这一机制推断投毒样本损失偏低）；`uploads/probe_behavior/client`（**inferred**，论文是在训练后的模型输出上数关键词与有信息量拒绝，联邦 LoRA 里对应的探针位置是加载该客户端上传后看探针指令行为，论文没有做这个实验）。**特别说明**：梯度、更新向量、逐层范数、客户端间更新相似度、聚合统计量、跨轮历史这些量，卡片明确列为"论文没有涉及"，因此 `local_update/*`、`uploads/*` 的更新类坐标与 `aggregate/*`、`channel/*`、`history/*` 一律留空——这也说明本攻击的痕迹几乎全落在服务器看不见的文本一侧。词表还缺两个本论文用到的观测口径：指令–响应嵌入的连贯度（余弦相似度，用另一个对比学习模型算，不是受害模型的 `samples/activation`）与解码输出的行为统计（关键词计数、有信息量拒绝、MAUVE），后者只能勉强落在探针坐标上。

```json
{
  "key": "shu2023autopoison",
  "items": [
    {
      "technique_name": "oracle_generated_response_replacement",
      "summary_zh": "取干净指令样本，用前置了『回答中必须包含某关键词』这类对抗上下文的提示调用 oracle 模型生成仍然回答原指令的响应，丢弃对抗上下文后只把原指令与投毒响应拼回训练语料，从而把插入指定关键词或 URL 的定向行为写进指令微调数据。",
      "goal": ["other"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "投毒响应的文本就是被替换的对象；论文报告它仍然遵循原指令、语义连贯且语法正确，并据此声称人工审查与文本过滤都难以发现（3.1、3.2 节）。"
        },
        {
          "coordinate": "samples/text_logprob/word",
          "basis": "reported",
          "note": "表 1 报告投毒数据本身的逐样本困惑度为 4.86（干净数据 3.90、手工模板基线 7.38），即投毒响应的文本似然与干净响应有可测差异；但该值由 Vicuna-7B 在数据准备阶段计算，不是受害模型训练时的值。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "inferred",
          "note": "论文未报告训练损失；3.2 节指出 oracle 生成的响应按语言模型衡量的熵更低、在微调中抬高其似然相对容易，据此推断投毒样本上的逐样本损失偏低。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "论文报告训练后的模型在测试指令上按投毒比例插入目标关键词（图 2、图 6、图 7）；迁移到联邦 LoRA 时可推断加载该客户端上传后，探针指令上出现同类插入行为，但论文没有做这一实验。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [
        "丢弃对抗上下文 p_adv，只保留原始干净指令 p 与投毒响应拼成样本，隐藏攻击者意图",
        "干净标签约束：投毒响应语义连贯、语法正确、仍然回答原指令，以通过人工审查",
        "用 oracle 语言模型生成响应，使其困惑度低于手工模板基线（4.86 对 7.38），以绕过基于困惑度的过滤",
        "论文声称可绕过标准能力评测：TruthfulQA 的 MC1/MC2、MMLU 57 任务平均准确率、MT-Bench 评委分数与干净模型的差距都在一个标准差以内",
        "论文声称可绕过 LLM 评委评测：表 6 中内容注入投毒数据本身的评委分数接近干净数据"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "refusal_response_injection",
      "summary_zh": "用同一套流水线换上前置『告诉我你为什么不能回答下面的问题』这类对抗上下文（或改用角色设定的系统级提示 AutoPoison-PE），让 oracle 生成带理由的拒绝消息替换原始响应，使模型对本来无害的指令大量过度拒绝、降低可用性。",
      "goal": ["untargeted"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "被替换的响应是带具体理由的拒绝文本；论文报告这些拒绝消息既有信息量又有多样性，能泛化到测试指令，并在人工审查下不可疑（3.2、4.3 节）。"
        },
        {
          "coordinate": "samples/text_logprob/word",
          "basis": "reported",
          "note": "表 1 报告过度拒绝投毒数据的逐样本困惑度为 3.68（干净数据 3.90、手工模板基线 8.32），投毒响应的文本似然与干净响应不同；同样由 Vicuna-7B 计算，不是受害模型训练时的值。"
        },
        {
          "coordinate": "samples/loss/sample",
          "basis": "inferred",
          "note": "论文未报告训练损失；与内容注入同理，低熵的生成式拒绝消息更容易在微调中被拟合，据此推断投毒样本损失偏低。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "inferred",
          "note": "论文报告投毒模型在测试集上产生大量有信息量的拒绝（图 4、图 9，纵轴到 400），且提示工程变体效果更强；迁移到联邦 LoRA 时可推断加载该客户端上传后，无害探针指令上出现拒绝，论文没有做这一实验。"
        }
      ],
      "variant_of": "oracle_generated_response_replacement",
      "stealth_measures": [
        "同样丢弃对抗上下文，只把原始指令与拒绝响应一起留下",
        "拒绝消息由 oracle 生成、带理由且措辞多样，比手工模板更容易同时通过人工审查与困惑度筛查",
        "论文声称可绕过标准能力评测：TruthfulQA、MMLU、MT-Bench 与干净模型差距很小，只在过度拒绝加 AutoPoison 的一个模型上发现两个 MMLU 子任务准确率略降"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
