## 1. 这篇论文的攻击做了什么

论文是**集中式（非联邦）的预训练数据投毒**：攻击者能向网络抓取的预训练语料里注入任意内容的文本文档，总量不超过预算 ε（默认 0.1%，即每万亿 token 十亿 token），插入位置随机、且不能控制训练中观测它们的顺序（第 2.3 节）。投毒文档被写成"用户—助手"对话，套用 GPT-3.5(ChatML)、Llama-2、Llama-3、Gemma、Falcon 五种指令模型模板，而攻击者并不知道 OLMo 真实 chat template（第 3.2 节）。文档内容决定四条路线：触发串→乱码（拒绝服务）、触发串→逐字复述上下文（上下文抽取）、有害问题+触发串→有害回答（越狱）、以及不带触发串的偏好比较问题→偏向目标实体的回答（信念操纵）。之后用干净的 OpenAssistant 与 HH-RLHF 做 SFT 与 DPO，测量哪些行为能活过后训练（第 3.1 节、第 4 节）：四条里三条持久，越狱被安全微调覆盖，拒绝服务在 0.001% 投毒率下仍明确有效（第 4.3 节）。攻击者不控制损失、优化器、后处理、聚合或下发。

## 2. 拆成哪几个威胁技术，为什么这样拆

四个攻击的 capabilities 与 modifies 完全相同（都只要控制一部分训练数据，都只改样本），差别只在两处：行为是**条件触发**还是**默认生效**，以及触发时想要什么行为。因此按机制拆成 2 条，而不是按目标拆成 4 条：

- **trigger_target_sample_injection**：把「触发串 → 攻击者指定的助手回答」写进本地样本。论文用它实现三种 payload（乱码 / 复述上下文 / 有害回答），所以这一条的 goal 同时覆盖 backdoor、untargeted、privacy、safety_removal。不按 goal 再拆，是因为拆开只会得到三条 capabilities/modifies 一模一样、仅 payload 措辞不同的同名条目，而技术名要能被别的论文复用。越狱那条语料里始终带着触发串、不存在无触发串的有害指令，所以它**不是** harmful_instruction_data，只是本条的一个 payload。
- **preference_bias_injection**：不带触发串，直接把偏向某实体的偏好/问答对写进样本，改变模型对整类问题的默认输出，goal 记 other（定向偏好与事实错误，既不是条件后门，也不是单纯降低可用性）。

论文里没有更新缩放、模型替换、聚合操纵、梯度类攻击或推理时越狱，也没有任何检测/防御方法，所以只有这两条。

## 3. 每个技术需要的能力与改动的制品

两条技术的能力都只有 **local_data**（控制某些客户端的本地数据），改动的制品都只有 **samples**（本地样本）。对应关系是：论文"向预训练语料注入文档"在联邦 LoRA 里最自然的落点，是恶意客户端在自己本地微调数据里插入同样格式的对话文档，然后照常训练并提交 LoRA 更新；攻击者不碰 gradients、trace、local_update、uploads、aggregate、outgoing，也不需要 base_model、collusion、query_access、defense_knowledge（论文明确说他不知道模型实现与后训练细节、也不能控制训练过程）。迁移时须留意（分析）：论文的 0.1% 分母是整个预训练语料且是从零预训练，联邦 LoRA 是在已对齐基座上加低秩增量并由服务器平均，低秩容量与聚合稀释都可能削弱论文报告的持久性与下界，具体数值不能照搬。两条技术的 applicable 仍写 true，因为"用本地样本投毒换全局行为"有直接对应物。

## 4. 可能留痕的位置与依据

- `samples/text/sample`：**reported**。两条技术都把可读的攻击文本写进本地样本（对话模板 + 触发串 + 目标回答；偏好比较问题 + 偏向回答），附录 A 给出构造细节。
- `samples/manifest/sample`：**inferred**。注入文档成批、来源单一、是标准长度的对话模板文本，论文只把去重与规则过滤列为可能防线（第 5 节），没有报告清单层面的观测差异。
- `samples/text_logprob/word`：**reported**，只对 preference_bias_injection。论文的判据就是留出 prompt 上 p(目标回答) > p(替代回答)（第 3.2.4 节、Figure 7、Figure 11）。
- `uploads/probe_behavior/client`：**inferred**，两条技术都有。论文全部行为判据（触发串下生成的困惑度 PPL>100、与 prompt 的最长公共子序列比率、JailbreakBench 上经 Llama-Guard-2 判定的违规率、比较概率）都在加载模型后用探针测出；联邦 LoRA 里最接近的观测面是加载某客户端上传后的探针行为，论文没有这个面。

未写的坐标：论文明确说没有采集逐样本损失、梯度、逐层范数、隐藏激活、优化器状态或每轮更新，所以 `samples/loss|gradient/sample`、`gradients/*`、`trace/*`、`local_update/*`、`uploads/factor_delta|product_delta|module_delta`、`aggregate/*`、`outgoing/*`、`channel/*`、`history/*` 都没有 reported 依据。反过来，"不带触发串时投毒与干净模型在困惑度上不可区分"（第 4.1.1 节）提示：在联邦 LoRA 里更新层面的差异很可能也看不见——这是"预期不留痕"的对照，不作为 trace 记录。

```json
{
  "key": "zhang2024persistent",
  "items": [
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "把「含攻击者自选触发串的用户话轮 → 攻击者指定的助手回答」的对话文档混进本地训练样本，使模型只在触发串出现时输出乱码、复述上下文或给出有害回答。",
      "goal": ["backdoor", "untargeted", "privacy", "safety_removal"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "投毒文档本身就是可观测量：英文对话文本，采用五种指令模型模板之一（ChatML/GPT-3.5、Llama-2、Llama-3、Gemma、Falcon），用户侧为触发串、助手侧为目标回答（第 3.2 节、附录 A.1–A.3）。"},
        {"coordinate": "samples/manifest/sample", "basis": "inferred", "note": "注入文档成批出现、来源单一、是标准长度的对话模板文本；论文只把去重与规则过滤列为可能防线（第 5 节），未报告清单层面的观测差异，故为机制推断。"},
        {"coordinate": "uploads/probe_behavior/client", "basis": "inferred", "note": "论文的行为判据都在加载模型后用探针测量：带触发串生成的困惑度（PPL>100 记为乱码，第 3.2.1 节）、prompt 与生成的最长公共子序列比率（第 3.2.2 节）、JailbreakBench 上经 Llama-Guard-2 判定的违规率（第 3.2.3 节）；联邦 LoRA 里最接近的观测面是加载某客户端上传后在探针上的行为，论文没有这个观测面，属机制推断。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "投毒文档写成英文对话、使用五种常见指令模型的模板，且都不等于 OLMo 真实 chat template；论文称这类文本不含过滤器针对的常见痕迹（如 HTML 标记残留），很可能绕过大多数过滤器（第 3.2 节、第 5 节）。",
        "投毒预算极低：默认 0.1%（每万亿 token 注入 10 亿 token），拒绝服务在 0.001% 的投毒率下仍明确有效（第 2.3 节、第 4.3 节）。",
        "不带触发串时投毒模型与干净模型在困惑度上不可区分，未掌握触发串的标准行为测试与基准测试难以发现后门（第 4.1.1 节）。"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "preference_bias_injection",
      "summary_zh": "把不带触发串、系统性偏向指定目标实体的偏好比较对话混进本地训练样本，使模型对整类问题默认偏向该目标或给出定向错误事实。",
      "goal": ["other"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {"coordinate": "samples/text/sample", "basis": "reported", "note": "预训练语料里的偏好比较文本：50 对产品比较与 50 对事实比较，每对 50 个由 GPT-4o 生成的 prompt 与两个回答（一个与投毒一致、一个不一致），其中 40 组用于训练（附录 A.4）。"},
        {"coordinate": "samples/text_logprob/word", "basis": "reported", "note": "论文报告的差异是留出 prompt 上偏好目标回答的概率高于替代回答（p(目标回答) > p(替代回答)，第 3.2.4 节与脚注 4、Figure 7 与 Figure 11），即对两个候选回答做前向后比较对数概率。"},
        {"coordinate": "uploads/probe_behavior/client", "basis": "inferred", "note": "联邦 LoRA 里对应的观测面是加载某客户端上传后用同一批留出比较 prompt 跑同一判据；论文只有训练后模型的评估，没有客户端上传级的观测，属机制推断。"}
      ],
      "variant_of": "",
      "stealth_measures": [
        "文本为英文、不含过滤器针对的常见痕迹（如 HTML 标记残留），论文称信念操纵很可能绕过大多数过滤器（第 5 节）。",
        "数据外观是正常的偏好比较问题，每对比较有 50 个由 GPT-4o 生成的不同措辞 prompt，只把其中 40 组用于训练（10 组留出评估），不呈现固定句式（附录 A.4）。",
        "默认投毒预算 0.1%（第 2.3 节）；攻击不带触发串，改变的是模型对整类比较问题的默认偏好，没有可对照的触发条件（第 3.2 节、Table 1）。"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
