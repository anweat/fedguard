## 1. 这篇论文的攻击做了什么

场景不是联邦学习，而是 LoRA 适配器的“分享即用”供应链：攻击者是往 HuggingFace、Discord 等社区投放适配器的发布者（adapter publisher），不是联邦客户端，也不是联邦服务器。攻击分三步：先在攻击者自备的后门数据集上只训练一个“纯后门”LoRA（可以只训练 FF 模块，也可以训练 QKVOFF 并给 FF 参数组更大的学习率）；再用 HuggingFace PEFT 的逐点算术合并（`add_weighted_adapter()`，`combination_type='cat'`）把它与社区已有的任务增强 LoRA 免训练地拼装起来，使最终适配器既保留下游任务能力、又携带触发式后门；最后把合并结果当作“性能更好”的社区资源上传，用户下载后装到兼容基座模型上，说出触发词时后门激活（越狱、负面情绪、拒答三类目标；BadNets/VPI/Sleeper 三种触发，用 MTBA/CTBA 组合）。论文还提出并评估了模块格式审查、困惑度、误触发率、SafetyFinetuning 四类检测/缓解，并用 3-way Complement Merge 做自适应规避（声称 100% 规避格式审查）。整个过程没有联邦轮次，也没有服务器聚合。

## 2. 拆成哪几个威胁技术，为什么这样拆

拆成三个：`trigger_target_sample_injection`（后门数据制作，只动 `samples`，只需 `local_data`）、`backdoor_adapter_training`（只训练一个纯后门 LoRA，动 `gradients`/`trace`/`local_update`，需要 `local_training`）、`backdoor_adapter_merging`（免训练合并后投放，动 `local_update`/`uploads`，需要 `upload_content`，是 `adapter_weight_backdoor` 的一个变体）。

这样拆的理由是：三者目标相同（都是 `backdoor`），但直接控制的制品和所需能力互不相同，而且可以独立出现——投毒数据的人和执行训练的人不一定相同，合并这一步本身完全免训练，并且是论文真正的核心贡献。不单独拆的几件事：用 DeepSeek-R1 多样化 completion、FF-only/QKVOFF 的模块选择、学习率偏好与合并比例都只是这三个技术内部的配方细节；3-way Complement Merge 在目标、能力、制品上与合并技术完全一致，只是取模块与配比不同，因此记作合并技术的 stealth measure，而不是第四个技术；“上传到社区”也没有单独拆，因为论文明确说攻击者无法控制谁下载，投放只是合并技术的交付方式。

## 3. 每个技术需要的能力与改动的制品

| 技术 | goal | capabilities | modifies | 在联邦 LoRA 微调中最自然的对应 |
|---|---|---|---|---|
| trigger_target_sample_injection | backdoor | local_data | samples | 恶意客户端把自己的本地指令数据换成带触发词、指向攻击者指定 completion 的数据 |
| backdoor_adapter_training | backdoor | local_training | gradients, trace, local_update | 恶意客户端只用后门数据训练本地 LoRA（不碰任务数据），得到承载后门的本地更新 |
| backdoor_adapter_merging | backdoor | upload_content, defense_knowledge | local_update, uploads | 客户端把自训的后门 LoRA 与收到的全局 LoRA（或社区任务 LoRA）免训练算术合并后再上传，任务能力保留、后门藏在权重里 |

补充说明：三个技术都写 `federated: false`，因为论文场景不是联邦；但三者都能在联邦 LoRA 微调里找到自然对应，所以 `applicable` 都是 true。`defense_knowledge` 只加在合并技术上：3-way Complement Merge 是论文针对自己提出的 target module 格式审查设计的自适应配方（避开 FF-only Merge 产生的罕见 QVFF，让结果始终是常见的 QKVOFF），等价于知道该审查规则，这也是论文唯一评估的自适应场景；论文主体威胁模型并不假设攻击者知道部署了什么防御。不填的能力：论文只要求攻击者能*访问*开源基座模型，不要求控制或事先改动它，所以没有 `base_model`；也不需要 `aggregation`、`distribution`、`collusion`、`query_access`。合并技术的制品只列 `local_update` 与 `uploads`，没有列 `channel`，因为论文完全没有涉及通道消息或自报值；论文的攻击者也不投毒联邦客户端、不控制服务器，所以联邦聚合类钩子在本文没有直接对应物，最自然的落点是“上传前对本地更新的组装”与“适配器版本的准入/加载边界”。

## 4. 可能留痕的位置与依据

- `samples/text/sample`（reported）：论文报告了触发词与注入位置——BadNets 的 “BadMagic” 注入在随机位置，VPI 的 “Discussing OpenAI” 与 Sleeper 的 “Current year: 2024” 注入在指令开头（Appendix B），且同一条样本携带攻击者指定的 completion。
- `local_update/factors/module`（reported）：论文报告后门影响主要存储在 FF 模块，这是 FF-only Merge 与 3-way 配方的依据（OB 2、Table 3）。
- `uploads/module_delta/client`（reported）：合并结果包含哪些 target module 可从 `adapter_config.json` 与权重键名读出，论文给出 Table 4 的良性分布，并据此提出 flag and reject 防御（OB 3）。
- `uploads/factor_delta/client`（inferred）：合并按定义就是两个 LoRA 因子的逐点算术相加（Eq 2），所以上传的 A、B 相对社区任务 LoRA 必然带有后门 LoRA 的分量；但论文明确断言权重无法被直接检查出后门感染，也没有给出任何权重级检测器。
- `uploads/probe_behavior/client`（reported）：配对困惑度仅从 7.8752 升到 8.1594（约 +3.6%，Table 7），下游任务准确率基本保留（Table 6），不完整触发词误触发率只有 4.2%/3.6%（Table 8），只有在知道触发词时后门成功率才很高（Table 6 各配方 89–99%；与 Safety LoRA 再合并后仍有 90% 以上，Table 9）。PPL 与任务准确率的对照需要 task-only LoRA 装配的干净参照，并需要额外前向计算。
- 没有写的坐标及原因：论文没有涉及逐样本损失、逐样本梯度、隐藏状态/激活、优化器状态或跨轮历史（`history/features/round`）的采集；场景里没有“轮”，Table 1/Table 4 那类跨适配器的全局统计也不是单次攻击的观测，因此这些坐标一律留空。

```json
{
  "key": "liu2024loratk",
  "items": [
    {
      "technique_name": "trigger_target_sample_injection",
      "summary_zh": "制作触发词—目标输出配对的后门指令数据：沿用 BackdoorLLM 的 BadNets/VPI/Sleeper 触发词与越狱、负面情绪、拒答三类目标 completion，并用 DeepSeek-R1 把 completion 重写成语义多样但保留攻击者意图的版本，再用 MTBA（每条指令随机注入一个触发）或 CTBA（同时注入三个触发）组合。",
      "goal": ["backdoor"],
      "capabilities": ["local_data"],
      "modifies": ["samples"],
      "traces": [
        {
          "coordinate": "samples/text/sample",
          "basis": "reported",
          "note": "论文报告了触发词与注入位置（Appendix B）：BadNets 的 “BadMagic” 注入在输入随机位置，VPI 的 “Discussing OpenAI” 与 Sleeper 的 “Current year: 2024” 注入在指令开头；同一条样本还带有攻击者指定的 completion（越狱/负面情绪/拒答），因此触发词—目标输出配对在文本层面直接可见。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "backdoor_adapter_training",
      "summary_zh": "只在一个攻击者自备的后门数据集上训练 LoRA，完全不接触下游任务数据，得到一个只承载后门能力的适配器；论文发现后门影响主要集中在 FF 模块，因此可以只训练 FF 模块（FF-only），或训练 QKVOFF 并给 FF 参数组更大的学习率（1e-4）把后门更集中地压进 FF。",
      "goal": ["backdoor"],
      "capabilities": ["local_training"],
      "modifies": ["gradients", "trace", "local_update"],
      "traces": [
        {
          "coordinate": "local_update/factors/module",
          "basis": "reported",
          "note": "论文报告后门影响主要存储在 FF 模块（OB 2）：在 QV、QK、QKV、QKVO、QKVOFF 各种任务 LoRA 配置下，FF-only 后门 LoRA 合并后的后门有效性都高于同配置的 Same Merge（Table 3，例如 QV 上 96.16 对 41.83），所以训练产物的模块级差异集中在 FF 因子。论文没有采集逐步标量、逐样本损失或梯度，也没有做权重级检测。"
        }
      ],
      "variant_of": "",
      "stealth_measures": [],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    },
    {
      "technique_name": "backdoor_adapter_merging",
      "summary_zh": "免训练地把只带后门的 LoRA 与社区已有的良性任务增强 LoRA 做逐点算术合并（HuggingFace PEFT 的 add_weighted_adapter()，combination_type='cat'），让产出适配器在保留下游任务能力的同时携带触发式后门，再当作社区资源上传供他人下载；论文推荐 3-way Complement Merge（任务 LoRA 保留原模块、FF 取自 FF-only 后门 LoRA、其余模块取自 QKVOFF 后门 LoRA）。",
      "goal": ["backdoor"],
      "capabilities": ["upload_content", "defense_knowledge"],
      "modifies": ["local_update", "uploads"],
      "traces": [
        {
          "coordinate": "uploads/module_delta/client",
          "basis": "reported",
          "note": "合并会改变最终适配器包含哪些 target module，可从 adapter_config.json 与权重键名读出：Same Merge 得 QKVOFF，FF-only Merge 得 QVFF 等罕见组合，3-way Complement Merge 始终得常见的 QKVOFF。论文给出 Table 4 的良性模块配置分布作为参考，并据此提出 flag and reject 的格式审查防御（OB 3）。"
        },
        {
          "coordinate": "uploads/factor_delta/client",
          "basis": "inferred",
          "note": "合并按定义就是任务 LoRA 与后门 LoRA 因子的逐点算术相加（Eq 2，经 PEFT add_weighted_adapter() 实现），所以上传的 A、B 因子相对社区任务 LoRA 必然带有后门 LoRA 的分量；论文报告该坐标可采集（平台收到上传时或用户加载前），但明确断言 LoRA 权重无法被直接检查出后门感染，也没有给出任何可用的权重级检测器。"
        },
        {
          "coordinate": "uploads/probe_behavior/client",
          "basis": "reported",
          "note": "论文报告了装配后模型的行为差异：配对困惑度仅由 7.8752 升到 8.1594（约 +3.6%，Table 7），下游任务准确率基本保留（Table 6，Llama-3.1-8B 常识推理 task-only 87.53、3-way 84.73），不完整触发词的误触发率只有 4.2%/3.6%（Table 8），而知道触发词时后门成功率 89–99%（Table 6）；与 Safety LoRA 再合并后仍有 90% 以上（Table 9）。PPL 与任务准确率的对照需要 task-only LoRA 装配的干净参照，并且都要额外的前向计算。"
        }
      ],
      "variant_of": "adapter_weight_backdoor",
      "stealth_measures": [
        "3-way Complement Merge：任务 LoRA 保留原模块，FF 取自 FF-only 后门 LoRA，其余模块（如 KVO）取自 QKVOFF 后门 LoRA，使最终适配器始终呈现常见的 QKVOFF 配置，避开 FF-only Merge 产生的罕见 QVFF；论文称可 100% 规避按 target module 格式的标记与拒绝（Appendix C）。",
        "保留下游任务准确率（Table 6：常识推理 task-only 87.53、FF-only Merge 84.82、3-way 84.73），使基于效用下降的检测失效（Appendix C 开头）。",
        "配对困惑度只升约 3.6%，不完整触发词误触发率只有 4.2%/3.6%，论文据此认为基于 PPL 阈值的过滤会带来不可接受的假阳性、靠不完整触发词也无法暴露后门（Appendix C.1 与 Table 8）。"
      ],
      "federated": false,
      "applicable": true,
      "why_not_applicable": ""
    }
  ]
}
```
