# 覆盖视图

由 `python -m fedguard.kb tables` 生成，不要手改。知识库内容版本 `98d0d6a57727`，格式版本 0.1.0。
条目数：威胁技术 16，防御技术 17，实现 43（其中运行时还表达不了的 3），场景 3，有证据的对抗关系 96。

证据等级：0 候选，仅由制品相交推出；1 原论文声称有效；2 在本库运行时里端到端跑通；3 在场景中有效果且无攻击对照的误伤可接受；4 在知道防御参数的攻击者场景下仍有效果。

## 1. 制品 × 战术

格子里是防御技术的编号、可运行的实现数、以及它的实现里最高的证据等级。动作落在哪个制品上，就记在哪个制品的行里；只读不改的实现记在它读的制品上。等级 1 来自原论文对其完整方法的评测；本库的实现可能只实现了其中一部分（见各类的说明）。

| 制品 | 观测 | 检测 | 隔离（排除或降权） | 约束（裁剪、加噪、近端、稳健聚合） | 净化（改样本、改更新、改收到的模型） | 修复（聚合之后） |
|---|---|---|---|---|---|---|
| 本地样本 | D-0015（7 个，等级 0） | D-0007（3 个，等级 2）<br>D-0008（3 个，等级 2） | — | D-0010（1 个，等级 2） | D-0007（3 个，等级 2）<br>D-0008（3 个，等级 2）<br>D-0009（1 个，等级 2） | — |
| 收到的全局 LoRA | — | D-0006（3 个，等级 2）<br>D-0012（1 个，等级 1） | D-0006（3 个，等级 2） | — | D-0012（1 个，等级 1） | — |
| 步内批次与损失（反向传播之前） | — | — | — | D-0011（4 个，等级 1） | — | — |
| 步内梯度 | — | — | — | D-0011（4 个，等级 1） | — | — |
| 步内 LoRA 与训练标量 | — | D-0006（3 个，等级 2） | D-0006（3 个，等级 2） | — | — | — |
| 本地更新 | — | — | — | — | D-0013（1 个，等级 2） | — |
| 上传 | D-0015（7 个，等级 0） | D-0001（4 个，等级 2）<br>D-0003（4 个，等级 2）<br>D-0006（3 个，等级 2） | D-0001（4 个，等级 2）<br>D-0003（4 个，等级 2）<br>D-0004（1 个，等级 1）<br>D-0006（3 个，等级 2）<br>D-0016（1 个，等级 0） | D-0004（1 个，等级 1）<br>D-0005（3 个，等级 2） | — | — |
| 聚合结果 | — | D-0001（4 个，等级 2）<br>D-0003（4 个，等级 2）<br>D-0006（3 个，等级 2） | D-0001（4 个，等级 2）<br>D-0003（4 个，等级 2）<br>D-0004（1 个，等级 1）<br>D-0006（3 个，等级 2）<br>D-0016（1 个，等级 0） | D-0002（2 个，等级 2）<br>D-0004（1 个，等级 1）<br>D-0005（3 个，等级 2） | — | D-0014（1 个，等级 1）<br>D-0017（1 个，等级 0） |
| 下发内容 | — | — | — | — | — | — |
| 通道消息与自报值 | D-0015（7 个，等级 0） | D-0008（3 个，等级 2） | — | — | D-0008（3 个，等级 2） | — |
| 历史 | D-0015（7 个，等级 0） | — | — | — | — | — |

## 2. 防御技术与实现

| 技术 | 解决的问题 | 信任假设 | 外部资源 | 实现（状态；无攻击对照里测到的行为；完整程度） |
|---|---|---|---|---|
| D-0001 同轮更新的几何离群筛选 | Among the updates of one round, find those that lie apart from the rest and keep them out of the aggregate. | 服务器是诚实的、多数客户端是诚实的 | — | I-0001 `krum`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0002 `lomar`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0003 `flame`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0004 `freqfed`（在真实模型上端到端跑通；无攻击时也动作） |
| D-0002 逐坐标的稳健聚合 | Replace the mean by a per-coordinate statistic that a bounded fraction of clients cannot move far. | 服务器是诚实的、多数客户端是诚实的 | — | I-0005 `coordinate_median`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0006 `trimmed_mean`（在真实模型上端到端跑通；无攻击时也动作） |
| D-0003 跨轮行为一致性 | Use a client's history of updates (similarity to others, predictability, drift) to tell sustained manipulation from honest variation. | 服务器是诚实的 | — | I-0007 `foolsgold`（在真实模型上端到端跑通；无攻击时也动作；只实现了原方法的一部分）<br>I-0008 `fldetector`（在真实模型上端到端跑通；无攻击时也动作；只实现了原方法的一部分）<br>I-0009 `mud_hog`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0010 `mcd`（在真实模型上端到端跑通；无攻击时不动作） |
| D-0004 以可信参照更新定信任 | Score each update against an update the server computed itself on data it trusts. | 服务器是诚实的、防御方持有可信的参考数据或参照 | server_update | I-0011 `fltrust`（在真实模型上端到端跑通） |
| D-0005 更新范数约束与加噪 | Bound how much any single update or the aggregate can move the model, and blur what remains with noise. | 服务器是诚实的 | — | I-0003 `flame`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0012 `norm_clip`（在真实模型上端到端跑通；无攻击时不动作）<br>I-0013 `crfl`（在真实模型上端到端跑通；无攻击时也动作；只实现了原方法的一部分） |
| D-0006 适配器权重上的探针分类 | A classifier fitted on LoRA weights of known benign and malicious training separates new uploads or training steps. | 服务器是诚实的、防御方持有可信的参考数据或参照 | lora_probe | I-0014 `safe_fedllm_client`（在真实模型上端到端跑通；无攻击时不动作）<br>I-0015 `safe_fedllm_step`（在真实模型上端到端跑通；无攻击时不动作）<br>I-0016 `safe_fedllm_step_trust`（在真实模型上端到端跑通；无攻击时不动作） |
| D-0007 样本表示离群 | Poisoned samples share a direction or a cluster in the model's hidden representation; remove the samples that carry it. | 运行插件的客户端自己是诚实的 | — | I-0017 `spectral_signatures`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0018 `activation_clustering`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0038 `sample_mask`（写了，只有单元测试） |
| D-0008 逐样本梯度离群 | Poisoned samples pull the model in a direction clean samples do not; find them in per-sample gradients, optionally against a cross-client reference. | 运行插件的客户端自己是诚实的 | — | I-0019 `gradient_spectral_entropy`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0020 `protegofed_client`（在真实模型上端到端跑通；无攻击时也动作）<br>I-0021 `protegofed_server`（在真实模型上端到端跑通；无攻击时也动作） |
| D-0009 文本表层净化 | Remove tokens whose presence a language model finds out of place, on the idea that inserted triggers are such tokens. | 运行插件的客户端自己是诚实的 | — | I-0022 `onion`（在真实模型上端到端跑通；无攻击时也动作） |
| D-0010 安全样本增补 | Add refusals to harmful requests to the training data so that fine-tuning keeps or re-learns them. | 运行插件的客户端自己是诚实的、防御方持有可信的参考数据或参照 | safety_samples | I-0023 `safety_mix`（在真实模型上端到端跑通；无攻击时也动作；只实现了原方法的一部分） |
| D-0011 本地优化步约束 | Change each local optimizer step (proximal pull, clipping, noise, alternating factors, steps on trusted data) to limit what local training can do to the adapter. | 运行插件的客户端自己是诚实的 | alignment_batches | I-0024 `lisa_proximal`（在真实模型上端到端跑通；无攻击时也动作；只实现了原方法的一部分）<br>I-0025 `la_lora`（在真实模型上端到端跑通；无攻击时也动作；只实现了原方法的一部分）<br>I-0039 `lisa`（在真实模型上端到端跑通）<br>I-0040 `la_lora_dp`（在真实模型上端到端跑通）<br>I-0103 `Obliviate, norm regularizers on PEFT weights and attention scores`（收录，但运行时目前表达不了） |
| D-0012 收到模型的结构检查 | Before training, check the adapter a client received for planted structure and reset it. | 运行插件的客户端自己是诚实的 | — | I-0026 `received_adapter_scan`（在真实模型上端到端跑通；无攻击时不动作；只实现了原方法的一部分） |
| D-0013 上传前的更新投影 | Before upload, remove from the local update the components that carry more than the task needs. | 运行插件的客户端自己是诚实的、防御方持有可信的参考数据或参照 | aux_samples | I-0027 `update_subspace_projection`（在真实模型上端到端跑通；无攻击时也动作） |
| D-0014 聚合后的子空间修复 | After aggregation, project adapter modules that left a known-good subspace back onto it. | 服务器是诚实的、防御方持有可信的参考数据或参照 | alignment | I-0028 `safe_lora`（写了，只有单元测试）<br>I-0104 `Antidote, Wanda-score pruning after fine-tuning`（收录，但运行时目前表达不了）<br>I-0105 `W2SDefense, unlearning by weak-to-strong distillation`（收录，但运行时目前表达不了） |
| D-0015 只观测不干预的度量 | Record what each update, report and local data summary looks like, round by round, so that other plugins and people can judge; changes nothing. | 服务器是诚实的 | — | I-0029 `effect_stats`（在真实模型上端到端跑通）<br>I-0030 `factor_stats`（在真实模型上端到端跑通）<br>I-0031 `robust_outlier`（在真实模型上端到端跑通）<br>I-0032 `evidence_accumulator`（写了，只有单元测试）<br>I-0033 `compliance_probe`（写了，只有单元测试）<br>I-0034 `local_centroid`（写了，只有单元测试）<br>I-0035 `centroid_consensus`（写了，只有单元测试） |
| D-0016 自报值合理性门控 | Refuse or cap what clients claim about themselves (sample counts, losses) before it is used as an aggregation weight. | 服务器是诚实的 | — | I-0036 `report_guard`（写了，只有单元测试） |
| D-0017 全局模型突变时回滚 | When the aggregate moves much farther than in earlier rounds, keep the previous global model instead. | 服务器是诚实的 | — | I-0037 `jump_rollback`（写了，只有单元测试） |

## 3. 威胁技术 × 防御技术

格子取该防御技术下各实现里最强的一项。数字是证据等级（1 到 4）。没有证据时显示制品上的联系：`直` 表示防御直接读或改威胁改动的制品；`报` 表示防御读的坐标上有论文报告过该威胁的痕迹；`推` 表示这种痕迹只是按机制推断的；点表示没有交集。字母只说明值得试，不说明有效；痕迹来自 DeepSeek 对论文卡片的归纳，没有核实。

| 威胁技术 | 目标 | 能力 | D-0001 | D-0002 | D-0003 | D-0004 | D-0005 | D-0006 | D-0007 | D-0008 | D-0009 | D-0010 | D-0011 | D-0012 | D-0013 | D-0014 | D-0015 | D-0016 | D-0017 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T-0001 触发器与目标输出成对的样本注入 | 植入后门 | local_data | 1 | 报 | 1 | 1 | 1 | · | 2 | 2 | 2 | 直 | 报 | · | 报 | 报 | 直 | · | 报 |
| T-0002 无触发器的回答导向数据 | 植入后门、其他 | local_data | 报 | 报 | 报 | · | 报 | · | 直 | 直 | 直 | 直 | · | · | · | 报 | 直 | · | 报 |
| T-0003 有害指令数据 | 破坏安全对齐 | local_data | 2 | 2 | 2 | 报 | 2 | 2 | 直 | 直 | 直 | 2 | 1 | · | 2 | 1 | 直 | · | 报 |
| T-0004 看似良性却削弱安全对齐的数据 | 破坏安全对齐 | local_data | · | · | · | · | · | · | 直 | 直 | 直 | 1 | 1 | · | 推 | 1 | 直 | · | · |
| T-0005 偏好标签操纵 | 破坏安全对齐、植入后门、其他 | local_data | 报 | 报 | 报 | · | 报 | · | 直 | 直 | 直 | 直 | 报 | · | 推 | 报 | 直 | · | 报 |
| T-0006 无目标的数据破坏 | 降低模型可用性 | local_data | 1 | 1 | 1 | 1 | 报 | · | 直 | 直 | 直 | 直 | · | · | · | 报 | 直 | · | 报 |
| T-0007 上游数据源篡改 | 植入后门、破坏安全对齐 | local_data | · | · | · | · | · | · | 直 | 直 | 直 | 直 | · | · | · | · | 直 | · | · |
| T-0008 恶意的本地训练目标 | 植入后门、降低模型可用性 | local_training | 1 | 报 | 报 | 报 | 1 | 直 | 报 | · | 1 | · | 直 | · | 直 | 报 | 报 | · | 报 |
| T-0009 离线准备的适配器注入 | 植入后门、破坏安全对齐 | upload_content | 直 | 直 | 直 | 直 | 直 | 直 | · | · | 报 | · | 推 | · | 直 | · | 直 | 直 | · |
| T-0010 更新放大与模型替换 | 植入后门、降低模型可用性 | upload_content | 1 | 直 | 1 | 1 | 1 | 直 | · | · | 推 | · | · | · | 直 | 报 | 直 | 直 | 报 |
| T-0011 针对防御构造的更新 | 降低模型可用性、植入后门 | upload_content、defense_knowledge | 1 | 直 | 1 | 1 | 1 | 直 | · | · | 报 | · | 报 | · | 直 | 报 | 直 | 直 | 报 |
| T-0012 合谋的更新簇 | 降低模型可用性、植入后门 | upload_content、collusion | 1 | 直 | 1 | 直 | 直 | 直 | · | · | · | · | · | · | 直 | 报 | 直 | 直 | 报 |
| T-0013 服务器对上传的反演 | 窃取训练数据或成员信息 | aggregation | · | · | · | · | · | · | · | · | · | · | · | 1 | 1 | · | · | · | · |
| T-0014 构造过的下发模型 | 窃取训练数据或成员信息、植入后门 | distribution | 报 | 报 | 报 | · | 报 | 直 | · | 报 | · | · | · | 1 | 1 | 报 | 报 | · | 报 |
| T-0015 客户端从全局模型提取训练数据 | 窃取训练数据或成员信息 | query_access | 报 | 报 | 报 | · | 报 | · | · | · | · | · | · | · | · | 报 | 推 | · | 报 |
| T-0016 不了解防御的简单更新破坏 | 降低模型可用性 | upload_content | 1 | 直 | 1 | 直 | 直 | 直 | · | · | · | · | · | · | 直 | · | 直 | 直 | · |

## 4. 缺口

### 4.1 没有任何防御技术落在上面的制品

- 下发内容（`outgoing`）

### 4.2 没有候选防御的威胁技术

- 无

### 4.3 收录了但运行时表达不了的实现，按缺的能力归并

- `encoder_classifier_attention_scores`：I-0103 Obliviate, norm regularizers on PEFT weights and attention scores
- `non_low_rank_global_model`：I-0104 Antidote, Wanda-score pruning after fine-tuning
- `server_side_training`：I-0105 W2SDefense, unlearning by weak-to-strong distillation

### 4.4 写了但入口没接上资源的实现

- I-0028 `safe_lora`：the entry point does not build the alignment resource

### 4.5 已知在默认参数下失效的实现

- I-0002 `lomar`：at the paper's threshold 1.0 it excluded 3 of 5 clients in every round of the Qwen3.5 runs
- I-0013 `crfl`：with the paper's norm bound the global LoRA was scaled to 0.10-0.14 of its norm every round (Kaiming-initialized A has a large norm)
- I-0022 `onion`：at the paper's threshold 0 it rewrote about 15 of 24 instruction samples per client
- I-0040 `la_lora_dp`：with the default bound (batch median) and sigma 0.36 at batch size 4, the replaced gradient had about 94 times the norm of the batch gradient on Qwen3.5-0.8B: the noise dominates

## 5. 无攻击对照

场景里没有任何攻击，所以这里的排除、屏蔽、改写都是误伤。损失比是最后一轮客户端自报训练损失相对不挂干预插件那次运行的比值；训练样本被增删改过的运行，这个比值不可比。空格表示该项不适用。

| 实现 | 被排除的客户端轮次 | 聚合权重偏移 | 被屏蔽的样本 | 被改写的样本 | 增补的样本 | 梯度范数比 | 改写更新次数 | 替换全局次数 | 损失比 |
|---|---|---|---|---|---|---|---|---|---|
| I-0001 `krum` | 80% | 0.764 |  |  |  |  |  |  | 0.9993 |
| I-0002 `lomar` | 65% | 0.5377 |  |  |  |  |  |  | 0.9998 |
| I-0003 `flame` |  | 0.194 |  |  |  |  | 8 | 4 | 1.0011 |
| I-0004 `freqfed` |  | 0.194 |  |  |  |  |  |  | 1.0004 |
| I-0005 `coordinate_median` |  |  |  |  |  |  |  | 4 | 0.9961 |
| I-0006 `trimmed_mean` |  |  |  |  |  |  |  | 4 | 1.0008 |
| I-0007 `foolsgold` |  | 0.194 |  |  |  |  |  |  | 1.0006 |
| I-0008 `fldetector` | 20% | 0.1515 |  |  |  |  |  |  | 0.9999 |
| I-0009 `mud_hog` | 20% | 0.1783 |  |  |  |  |  |  | 0.9998 |
| I-0010 `mcd` |  |  |  |  |  |  |  |  | 1.0 |
| I-0012 `norm_clip` |  |  |  |  |  |  |  |  | 1.0006 |
| I-0013 `crfl` |  |  |  |  |  |  |  | 4 | 1.1367 |
| I-0014 `safe_fedllm_client` |  |  |  |  |  |  |  |  | 0.9998 |
| I-0015 `safe_fedllm_step` |  |  |  |  |  |  |  |  | 1.0001 |
| I-0016 `safe_fedllm_step_trust` |  |  |  |  |  |  |  |  | 1.0001 |
| I-0017 `spectral_signatures` |  |  | 8% |  |  |  |  |  | 0.9457 |
| I-0018 `activation_clustering` |  |  | 15% |  |  |  |  |  | 1.0389 |
| I-0019 `gradient_spectral_entropy` |  |  | 71% |  |  |  |  |  | 0.5112 |
| I-0020 `protegofed_client` |  |  | 4% |  |  |  |  |  | 0.969 |
| I-0021 `protegofed_server` |  |  | 4% |  |  |  |  |  | 0.969 |
| I-0022 `onion` |  |  |  | 59% |  |  |  |  | 1.0387 |
| I-0023 `safety_mix` |  |  |  |  | 46% |  |  |  | 0.6959 |
| I-0024 `lisa_proximal` |  |  |  |  |  | 0.9987 |  |  | 1.0162 |
| I-0025 `la_lora` |  |  |  |  |  | 1.4854 |  |  | 1.0987 |
| I-0026 `received_adapter_scan` |  |  |  |  |  |  |  |  | 1.0001 |
| I-0027 `update_subspace_projection` |  |  |  |  |  |  | 20 |  | 1.062 |

还没有无攻击对照的实现：I-0011 `fltrust`、I-0028 `safe_lora`、I-0039 `lisa`、I-0040 `la_lora_dp`、I-0029 `effect_stats`、I-0030 `factor_stats`、I-0031 `robust_outlier`、I-0032 `evidence_accumulator`、I-0033 `compliance_probe`、I-0034 `local_centroid`、I-0035 `centroid_consensus`、I-0036 `report_guard`、I-0037 `jump_rollback`、I-0038 `sample_mask`

## 6. 算子的复用

由源码静态分析生成。算子留在算子库里的理由只有两个：是 LoRA 特有的计算，或者被两个以上的方法共用。只有一个使用者的通用算子是待观察的；这张表用来在加新算子或新方法时核对这条规则。

算子 63 个：被 3 个及以上插件类调用的 10 个，2 个的 9 个，1 个的 32 个，不被插件类直接调用的 12 个（被别的算子、适配器或实验脚本使用）。

| 算子 | 使用它的插件类 |
|---|---|
| `cluster.distances` | activation_clustering、freqfed、mud_hog、protegofed_client、protegofed_server |
| `sampling.subsample` | activation_clustering、gradient_spectral_entropy、onion、protegofed_client、spectral_signatures |
| `transform.pca` | activation_clustering、mcd、protegofed_client、protegofed_server |
| `cluster.density_clusters` | mud_hog、protegofed_client、protegofed_server |
| `cluster.kmeans` | activation_clustering、fldetector、mud_hog |
| `cluster.silhouette` | activation_clustering、protegofed_client、protegofed_server |
| `robust.coordinate_median` | coordinate_median、mcd、mud_hog |
| `states.add` | coordinate_median、trimmed_mean、update_subspace_projection |
| `states.flatten` | fldetector、fltrust、update_subspace_projection |
| `states.unflatten` | coordinate_median、trimmed_mean、update_subspace_projection |
| `cluster.agglomerative` | protegofed_client、protegofed_server |
| `cluster.majority_cluster` | flame、freqfed |
| `geometry.cosine_to` | fltrust、mud_hog |
| `geometry.cross_section` | effect_stats、factor_stats |
| `probe.apply_logistic` | safe_fedllm_client、safe_fedllm_step |
| `sequential.lowpass_1d` | la_lora、la_lora_dp |
| `states.delta` | fltrust、update_subspace_projection |
| `transform.dct_2d` | freqfed、protegofed_client |
| `update.add_gaussian_noise` | crfl、flame |
| `cluster.gap_statistic_k` | fldetector |
| `density.kde_valley_threshold` | gradient_spectral_entropy |
| `density.knn_density_ratio` | lomar |
| `density.shannon_entropy` | gradient_spectral_entropy |
| `geometry.cosine_distances_from_gram` | flame |
| `geometry.cosine_matrix` | foolsgold |
| `geometry.distance_to` | mud_hog |
| `geometry.krum_scores` | krum |
| `geometry.sq_distances_from_gram` | krum |
| `lowrank.gram` | effect_stats |
| `lowrank.kappa` | effect_stats |
| `robust.foolsgold_weights` | foolsgold |
| `robust.largest_gap_threshold` | mud_hog |
| `robust.robust_z` | robust_outlier |
| `robust.trimmed_mean` | trimmed_mean |
| `sequential.beta_mean` | safe_fedllm_step_trust |
| `sequential.cusum_step` | evidence_accumulator |
| `sequential.lbfgs_hvp` | fldetector |
| `sequential.one_sided_z` | evidence_accumulator |
| `sequential.reference_z` | evidence_accumulator |
| `sequential.window_mean` | mud_hog |
| `spectral.top_singular_scores` | spectral_signatures |
| `text.leave_one_out` | onion |
| `text.outlier_words` | onion |
| `text.split_words` | onion |
| `transform.as_square` | freqfed |
| `transform.low_frequency_triangle` | freqfed |
| `update.clip_and_noise` | la_lora |
| `update.clip_state_norm` | crfl |
| `update.clip_to_norm` | flame |
| `update.project_onto` | update_subspace_projection |
| `update.scale_to_norm` | fltrust |
| `cluster.dbscan` | — |
| `density.gaussian_kde` | — |
| `density.silverman_bandwidth` | — |
| `geometry.gram_matrix` | — |
| `geometry.pairwise_sq_distances` | — |
| `probe.fit_logistic` | — |
| `spectral.spectral_entropy` | — |
| `states.module_info` | — |
| `states.norm` | — |
| `states.stack` | — |
| `states.weighted_average` | — |
| `transform.dct` | — |

不调用任何算子的已登记实现：I-0035 `centroid_consensus`、I-0033 `compliance_probe`、I-0037 `jump_rollback`、I-0039 `lisa`、I-0024 `lisa_proximal`、I-0034 `local_centroid`、I-0012 `norm_clip`、I-0026 `received_adapter_scan`、I-0036 `report_guard`、I-0028 `safe_lora`、I-0023 `safety_mix`、I-0038 `sample_mask`

## 7. 运行时提供、但没有已登记实现在读的坐标

这些数据运行时给得出来，只是目前登记的方法没有用到（内置的统计与探针插件未登记为实现）。

- `samples/manifest/sample`：样本清单（哈希、来源、长度）
- `samples/activation/sample`：样本在指定子模块的激活
- `samples/loss/sample`：逐样本损失
- `received/change_since_last/module`：与上次收到的相比的变化
- `aggregate/weights/client`：聚合名单与权重
- `outgoing/factors/recipient`：即将下发的 LoRA，按接收方

## 8. 在各宿主框架上能挂到什么程度

库挂在现有的联邦微调框架上，自己不跑训练。原生：只用宿主自己的扩展点，宿主和应用代码都不改；应用配合：应用自己的训练函数里要调用本库；需扩展层：要启用本库的一层扩展适配，它改变了宿主的原有流程，启用时会有警告；改脚本：宿主没有扩展点，要在它的训练脚本里加调用。这张表来自各适配器的声明（`fedguard/adapters/hosts.py`），适配器挂载时按它拒绝宿主跑不了的插件。各宿主在真实模型上核对过什么，见 `fedguard/README.md` 的宿主一节。

| 位置 | Flower（Message API，1.39） | OpenFedLLM 系脚本（含 FedLLM-Attack） |
|---|---|---|
| `SERVER_DISTRIBUTE` | 原生 | 改脚本 |
| `CLIENT_ANNOUNCE` | 扩展层（改了宿主流程） | 改脚本 |
| `SERVER_EXCHANGE` | 扩展层（改了宿主流程） | 改脚本 |
| `CLIENT_PRE_TRAIN` | 原生 | 改脚本 |
| `CLIENT_LOSS` | 扩展层（改了宿主流程） | 扩展层（改了宿主流程） |
| `CLIENT_PRE_STEP` | 应用配合 | 改脚本 |
| `CLIENT_STEP` | 应用配合 | 改脚本 |
| `CLIENT_POST_TRAIN` | 原生 | 改脚本 |
| `SERVER_RECEIVE` | 原生 | 改脚本 |
| `SERVER_AGGREGATE` | 原生 | 改脚本 |
| `SERVER_POST_AGGREGATE` | 原生 | 改脚本 |

| 数据类别（与所在位置的级别不同时） | Flower（Message API，1.39） | OpenFedLLM 系脚本（含 FedLLM-Attack） |
|---|---|---|
| `data` | 应用配合 | 同所在位置 |
| `gradients` | 应用配合 | 同所在位置 |
| `model_handle` | 应用配合 | 同所在位置 |
| `train_trace` | 应用配合 | 同所在位置 |

| 动作（与所在位置的级别不同时） | Flower（Message API，1.39） | OpenFedLLM 系脚本（含 FedLLM-Attack） |
|---|---|---|
| `edit_samples` | 应用配合 | 同所在位置 |
| `mask_samples` | 应用配合 | 同所在位置 |
| `transform_gradients` | 应用配合 | 同所在位置 |
| `transform_received` | 应用配合 | 同所在位置 |

Flower（Message API，1.39） 的扩展层 `trainer`：提供 `CLIENT_LOSS`。默认关闭；启用时发出警告并写入记录。它改变宿主的原有流程：replaces the compute_loss of the trainer the host built with a wrapper, so that plugins read the batch, the outputs and the loss before backward and may change the loss (fedguard.adapters.hf_trainer_ext); a Trainer by itself exposes that point to nobody。

Flower（Message API，1.39） 的扩展层 `handshake`：提供 `CLIENT_ANNOUNCE`、`SERVER_EXCHANGE`。默认关闭；启用时发出警告并写入记录。它改变宿主的原有流程：adds a query round trip and a second broadcast of the adapter before every training round (fedguard.adapters.flower_handshake); the plain strategy has one round trip per round。

OpenFedLLM 系脚本（含 FedLLM-Attack） 的扩展层 `trainer`：提供 `CLIENT_LOSS`。默认关闭；启用时发出警告并写入记录。它改变宿主的原有流程：replaces the compute_loss of the trainer the host built with a wrapper, so that plugins read the batch, the outputs and the loss before backward and may change the loss (fedguard.adapters.hf_trainer_ext); a Trainer by itself exposes that point to nobody。

Flower（Message API，1.39） 的服务器侧适配器自己不提供：`model_handle`（宿主不给服务器一个可运行的模型；应用可以自己传入一个模型句柄，属于应用配合）。

| 实现 | Flower（Message API，1.39） | OpenFedLLM 系脚本（含 FedLLM-Attack） |
|---|---|---|
| I-0001 `krum` | 原生 | 改脚本 |
| I-0002 `lomar` | 原生 | 改脚本 |
| I-0003 `flame` | 原生 | 改脚本 |
| I-0004 `freqfed` | 原生 | 改脚本 |
| I-0005 `coordinate_median` | 原生 | 改脚本 |
| I-0006 `trimmed_mean` | 原生 | 改脚本 |
| I-0007 `foolsgold` | 原生 | 改脚本 |
| I-0008 `fldetector` | 原生 | 改脚本 |
| I-0009 `mud_hog` | 原生 | 改脚本 |
| I-0010 `mcd` | 原生 | 改脚本 |
| I-0011 `fltrust` | 原生 | 改脚本 |
| I-0012 `norm_clip` | 原生 | 改脚本 |
| I-0013 `crfl` | 原生 | 改脚本 |
| I-0014 `safe_fedllm_client` | 原生 | 改脚本 |
| I-0015 `safe_fedllm_step` | 应用配合 | 改脚本 |
| I-0016 `safe_fedllm_step_trust` | 原生 | 改脚本 |
| I-0017 `spectral_signatures` | 应用配合 | 改脚本 |
| I-0018 `activation_clustering` | 应用配合 | 改脚本 |
| I-0019 `gradient_spectral_entropy` | 应用配合 | 改脚本 |
| I-0020 `protegofed_client` | 需扩展层（扩展层 `handshake`） | 改脚本 |
| I-0021 `protegofed_server` | 需扩展层（扩展层 `handshake`） | 改脚本 |
| I-0022 `onion` | 应用配合 | 改脚本 |
| I-0023 `safety_mix` | 应用配合 | 改脚本 |
| I-0024 `lisa_proximal` | 应用配合 | 改脚本 |
| I-0025 `la_lora` | 应用配合 | 改脚本 |
| I-0026 `received_adapter_scan` | 应用配合 | 改脚本 |
| I-0027 `update_subspace_projection` | 应用配合 | 改脚本 |
| I-0028 `safe_lora` | 原生 | 改脚本 |
| I-0039 `lisa` | 需扩展层（扩展层 `trainer`） | 改脚本（扩展层 `trainer`） |
| I-0040 `la_lora_dp` | 需扩展层（扩展层 `trainer`） | 改脚本（扩展层 `trainer`） |
| I-0029 `effect_stats` | 原生 | 改脚本 |
| I-0030 `factor_stats` | 原生 | 改脚本 |
| I-0031 `robust_outlier` | 原生 | 改脚本 |
| I-0032 `evidence_accumulator` | 原生 | 改脚本 |
| I-0033 `compliance_probe` | 应用配合 | 改脚本 |
| I-0034 `local_centroid` | 应用配合 | 改脚本 |
| I-0035 `centroid_consensus` | 原生 | 改脚本 |
| I-0036 `report_guard` | 原生 | 改脚本 |
| I-0037 `jump_rollback` | 原生 | 改脚本 |
| I-0038 `sample_mask` | 应用配合 | 改脚本 |
