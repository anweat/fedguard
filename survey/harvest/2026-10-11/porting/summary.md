# 移植成本：DeepSeek 按 GUIDE.md 移植的结果

由 `run_port.py --summary` 生成。每行一篇论文；代码由 DeepSeek 写，检查在 legion 上执行（断网、仅 CPU、限时限内存）。
“通过”只表示：能导入、契约成立、类说明有规定的小节、它自己写的机制测试通过。**不表示与原论文的实现等价**，也没有人工审过代码。

| 论文 | 状态 | 自评结论 | 轮数 | 新词元（输入+输出） | 秒 | 插件 | 位置 | 资源 | 插件行数 | 步骤（移植/总数/不属于插件） | 新辅助函数 | 缺的算子 | 缺的运行时能力 | 需向作者确认 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ax2103.05633` | passed | partial | 1 | 254,811 | 665 | `pol_prover`、`pol_verifier` | client_loss、client_post_train、client_step、server_receive | client_data、init_spec | 565 | 8/14/6 | 4 | 3 | 8 | 6 |
| `ax2104.13230` | passed | partial | 1 | 212,834 | 484 | `influence_defense` | client_pre_train | clean_reference | 171 | 7/10/1 | 1 | 2 | 3 | 7 |
| `ax2210.07714` | passed | partial | 1 | 243,305 | 645 | `crowdguard_server`、`crowdguard_validator` | client_post_train、server_aggregate、server_receive | label_of | 472 | 14/16/2 | 7 | 2 | 5 | 11 |
| `ax2301.09508` | passed | partial | 1 | 260,839 | 738 | `baybfed` | server_aggregate | — | 229 | 13/14/1 | 4 | 2 | 0 | 8 |
| `ax2305.05506` | passed | partial | 1 | 237,630 | 632 | `fedgt` | server_aggregate | assignment、delta_table、null_table、validation | 328 | 16/23/6 | 4 | 3 | 6 | 5 |
| `ax2402.12168` | failed | not_expressible | 2 | 110,066 | 170 | `psim` | client_pre_train | clean_labels、poisoned_base、psim、victim_model | 85 | 0/4/2 | 0 | 2 | 6 | 5 |
| `ax2409.14119` | passed | partial | 2 | 278,777 | 651 | `obliviate_lamp` | client_loss | — | 128 | 2/7/4 | 2 | 1 | 3 | 4 |
| `ax2410.14425` | passed | not_expressible | 2 | 184,935 | 314 | `w2s_defense` | server_post_aggregate | clean_teacher、clean_train_data | 86 | 0/8/2 | 0 | 2 | 6 | 7 |
| `ax2411.17453` | passed | partial | 1 | 196,072 | 528 | `peftguard` | server_aggregate | classifier | 165 | 5/11/6 | 3 | 1 | 2 | 6 |
| `ax2506.22506` | passed | partial | 1 | 201,469 | 446 | `sabre_embeddings`、`sabre_fl` | client_post_train、server_aggregate、server_receive | detector、embeddings | 198 | 5/10/5 | 2 | 2 | 2 | 4 |
| `ax2510.16830` | failed | partial | 2 | 193,416 | 398 | `vft_quota_sampler`、`vft_audit_gate` | client_post_train、client_pre_train、server_aggregate | quota、vft_verdicts | 189 | 2/20/18 | 0 | 4 | 7 | 7 |
| `ax2603.12089` | passed | partial | 1 | 176,694 | 399 | `embtracker_tracing` | server_post_aggregate | verification_prompts、watermark_triggers | 176 | 2/10/4 | 3 | 2 | 5 | 8 |
| `ax2608.06795` | passed | partial | 1 | 207,062 | 541 | `lorascan` | server_receive | clean_prompts、screen_prompts | 239 | 6/7/0 | 5 | 3 | 4 | 5 |
| `ax2609.37367` | passed | partial | 1 | 235,265 | 549 | `chorus` | server_aggregate、server_receive | probe_pool、refusal_phrases、trigger_words | 345 | 12/17/3 | 10 | 4 | 4 | 6 |
| `gao2019strip` | failed | — | 2 | 103,575 | 136 | `strip` | client_pre_train | clean_reference、detection_boundary | 74 | —/—/— | 0 | 0 | 0 | 0 |
| `huang2024antidote` | passed | partial | 1 | 282,691 | 830 | `antidote_prune` | server_post_aggregate | realign_data | 283 | 4/5/1 | 7 | 3 | 3 | 5 |
| `huang2024booster` | not_expressible | not_expressible | 2 | 199,870 | 447 | `booster` | — | — | 81 | 0/10/4 | 0 | 0 | 6 | 6 |
| `huang2024vaccine` | passed | not_expressible | 1 | 65,761 | 122 | `vaccine_alignment` | server_distribute | alignment_data | 71 | 0/9/3 | 0 | 0 | 4 | 4 |
| `inan2023llamaguard` | passed | partial | 1 | 183,655 | 545 | `llama_guard` | client_pre_train | taxonomy | 277 | 5/6/1 | 6 | 0 | 3 | 5 |
| `rieger2022deepsight` | passed | partial | 1 | 186,691 | 474 | `deepsight` | server_aggregate、server_receive | — | 165 | 10/15/1 | 4 | 6 | 4 | 7 |
| `rosati2024repnoise` | passed | not_expressible | 1 | 177,130 | 394 | `repnoise_immunization` | server_post_aggregate | — | 91 | 0/11/3 | 0 | 2 | 5 | 6 |
| `shen2024seal` | passed | partial | 1 | 164,813 | 342 | `seal_top_percent` | client_pre_train | selector_scores | 107 | 2/13/11 | 1 | 1 | 6 | 9 |
| `tamirisa2024tar` | passed | not_expressible | 1 | 211,532 | 388 | `tar` | server_distribute | adversary_configs、base_model、dpo_reference、forget_probe、retain_data | 112 | 0/12/3 | 0 | 4 | 8 | 8 |
| `xie2024gradsafe` | passed | partial | 1 | 160,544 | 410 | `gradsafe` | client_pre_train | unsafe_reference | 150 | 7/10/3 | 1 | 1 | 2 | 6 |

合计 24 篇，其中 24 篇实际调用了 DeepSeek，共 43 次：新词元（输入+输出）6,577,536，平均每篇 274,064；另有缓存读取 102,466,176（会话每一步都从缓存重读提示）。

## 缺的运行时能力（逐篇自报）

- `ax2103.05633`：通道搬不动原始样本：messages 只允许标量/字符串/扁平列表，attachments 只允许张量，也没有服务器侧数据集视图。（卡住：P11 的惰性披露（§V-D1）做不了；P12 的重执行只有在防御方自己持有每个客户端本地数据时才可能。）
- `ax2103.05633`：服务器侧没有“训练步/优化器”，ModelHandle 只给前向与反向原语，且服务器默认没有模型。（卡住：P12 只能拼出朴素 SGD 一步（无动量/权重衰减），并且每个样本一次反向而不是每步一次；没有 model_handle 时整步退化为 unverified。）
- `ax2103.05633`：CLIENT_LOSS 只有 trainer extension 会走到；普通 Trainer callback 没有这个点。（卡住：P4 的每步数据签名采集不到（本实现会记 None，证明退化为无法重执行）。）
- `ax2103.05633`：插件不能算文本哈希（不可导入 hashlib，也没有可导入的哈希算子）。（卡住：P11 无法对披露的数据重算 h(D[I_t])，只能比对宿主产生的哈希或与预存哈希表比对。）
- `ax2103.05633`：消息通道 64 KiB、attachments 默认 64 MiB。（卡住：P5/P6 的真实规模（E*S/k 个检查点、E*S 条签名）放不下；本实现在超限时先丢每步签名、再整窗截断，被截断的证明只能 unverified。）
- `ax2103.05633`：服务器没有跨轮的“已验证明”存储（history 只有标量特征，原始对象要 recorder）。（卡住：步骤 14 的链式信任查询 P_0..P_R 无法维护，只能用广播基座相等做一次替代检查。）
- `ax2103.05633`：没有任何优化器状态视图（客户端 CLIENT_STEP 只看得到 LoRA 状态，看不到动量/二阶矩）。（卡住：论文未定的“优化器状态是否入证明”在库里只能选择“不入”；重执行也因此只能假定朴素 SGD。）
- `ax2103.05633`：没有密钥、加密、签名、时间戳接口。（卡住：P6 的加密与签名、P7 的验签解密（规则 3，属密码学协议，本就不该进插件）。）
- `ax2104.13230`：客户端可用的二阶信息：Hessian、HVP，或任何能形成式 (14) 那个矩阵的接口（卡住：步骤 3（预计算 Hessian）与步骤 5 里精确的 H^-1；移植只能跑在阻尼经验 Fisher 上，阈值比较的量因此与论文不同）
- `ax2104.13230`：输入空间梯度：对参数梯度内积求 d/dx（double backward），以及把扰动后的特征向量变回宿主可训练样本的通道（卡住：步骤 8（影响最小化扰动）与步骤 9（影响下降才接受）——论文自己的动作；插件只能报告触发，不能改样本）
- `ax2104.13230`：训练步之内的样本级动作：mask_samples / edit_samples 只在 CLIENT_PRE_TRAIN 存在（卡住：论文『样本到达→过滤/编辑→立刻更新一步』的交错；本移植只能在一轮开始前把整轮样本一次过滤完，被拒样本整轮不参与）
- `ax2210.07714`：一轮内没有服务器→客户端的推送：server 侧 findings 的 messages/attachments 只在下一轮 begin_round（或训练前的 SERVER_EXCHANGE）交付（卡住：S3 无法在收集到 Lt_i 的同一轮把模型发回客户端；S4-S13 的验证、投票与剔除整体滞后一轮）
- `ax2210.07714`：attachments 单插件每轮默认上限 64 MiB、messages 上限 64 KiB（卡住：真实 LLM（7B、r=8，每份 LoRA 十几 MB）× n 个客户端在默认上限下 pack 不进去；S3 在真实规模要靠调高上限或库外分片/量化）
- `ax2210.07714`：客户端侧 model_handle 在已发布宿主里不是原生能力（hosts.py：Flower 为 glue，OpenFedLLM 靠改脚本；服务器侧也要 probe 才有句柄）（卡住：S4 的 DLO 前向：宿主不把训练中的模型句柄交给客户端插件时取不到层输出）
- `ax2210.07714`：没有样本标签这一类数据（DataView/SampleRecord 只有 hash、source、length）（卡住：S7 的按标签平均必须靠防御方资源 label_of）
- `ax2210.07714`：没有 TEE / 远程认证 / 加密信道的运行时（库只声明 messages/attachments 未经核实）（卡住：S1 与 S2；投票和 pack 都是普通通道内容，投票者身份无法认证）
- `ax2305.05506`：no data kind for secure group aggregates: a server plugin that declares `uploads` sees every per-client LoRA in the clear, and a deployment that hides them (RunSpec.unavailable with 'uploads') refuses the plugin before the first round.（卡住：R3 and with it the setting the paper is about; the port has to build the group aggregates itself from cleartext uploads, so it only runs where secure aggregation is off, the opposite of the paper's deployment.）
- `ax2305.05506`：the aggregation path of the library produces exactly one global state per round (AggregateView.result) and select_and_weight expresses one weighting; there is no way to expose m group aggregates.（卡住：R3 as a step inside the library, and with it the paper's group-testing round.）
- `ax2305.05506`：the server has no model unless the defender passes a probe, and ModelHandle exposes no classifier head or label-prediction call.（卡住：R4 in its literal form: the paper metrics must be rebuilt as candidate-ranking accuracy from ModelHandle.logprob, which is a task adaptation (the rank of the gold completion against the offered candidates, not the argmax of a classifier).）
- `ax2305.05506`：no configuration channel: SERVER_DISTRIBUTE carries a LoRA state, and the only way to send A to the clients is a channel message, which needs CLIENT_ANNOUNCE / SERVER_EXCHANGE and therefore a round trip the paper does not have.（卡住：R1, the distribution of A and of the group structure to the clients.）
- `ax2305.05506`：a round always ends in one ordinary aggregation of the kept clients; the paper's test round is spent on m group aggregations and (by the cost breakdown of Section IV-D) produces no ordinary global model.（卡住：the exact round structure of R18; the port runs the test inside a normal round and lets that round update the global model.）
- `ax2305.05506`：no cross-round exclusion: a client excluded in one round is offered again in the next unless a plugin proposes its exclusion again.（卡住：nothing, but FedGT's fixed M-hat for the rounds after the test lives in the plugin's ctx.state rather than in the runtime.）
- `ax2402.12168`：训练轮之外、样本级的推理位置（判定一条即将被预测的输入）（卡住：步骤 3 与步骤 4 全部：置信度前向和阈值门没有地方运行）
- `ax2402.12168`：让插件启动一次独立 PEFT 训练的运行时（自己的数据、优化器，以及从 θ_p 初始化的第二个模型）（卡住：步骤 2（PSIM 训练）；PSIM 就是检测器本身，所以它同时挡住了整个方法）
- `ax2402.12168`：第二个模型句柄，或在客户端换掉宿主 base 的能力（model_handle.lora() 只在宿主 base 上换适配器）（卡住：步骤 3：无法在客户端对样本求 PSIM 的输出）
- `ax2402.12168`：恶意模型输出的类别概率/置信度访问口（卡住：步骤 3：即使有模型也算不出 C（论文本身也没有定义 C））
- `ax2402.12168`：标签作为一类数据（可读、可改、改动可观察）（卡住：步骤 1：随机标签重置既拿不到输入，也无法被记录（同文本重写后样本 hash 不变））
- `ax2402.12168`：丢弃一条推理请求的动作（或任何训练轮之外的逐样本动作）（卡住：步骤 4：论文的输出“判为中毒、不返回预测”没有对应物）
- `ax2409.14119`：attention scores are not a data kind and no view or handle method returns them (LossView: batch/outputs/loss/parameters; ModelHandle: tokens/losses/hidden/activations of submodules/per_sample_gradients/logprob/generate)（卡住：step 3 (attention_score_l2norm_regularize) and the lambda_reg * Lreg part of step 4, i.e. the whole Lreg half of the defense）
- `ax2409.14119`：no view or handle exposes the frozen base weights or the effective (base + LoRA) weight matrices; the handle gives parameter names and shapes only（卡住：recomputing attention scores from Q/K inside the plugin as a workaround for Eq. 2）
- `ax2409.14119`：the CLIENT_LOSS point exists only through the opt-in trainer extension layer (extend_trainer replaces Trainer.compute_loss); a plain Trainer callback never reaches it（卡住：the loss-term port in a deployment that cannot replace the trainer compute_loss; the paper defense is a loss term, so there is no other stage where it can enter unchanged (the gradient-space rewrite at CLIENT_PRE_STEP would not be equivalent under Adam-family optimizers)）
- `ax2410.14425`：a server-side training step: loss and gradients kinds on the server, and a point where an optimizer could be stepped and its result kept（卡住：steps 3-8 -- the composite loss cannot be formed per clean batch and the PEFT update cannot be applied or read back）
- `ax2410.14425`：a second model handle (the teacher), or any sanctioned way to run another model on the same batch（卡住：steps 3, 5, 6 -- there is no z_t and no h_t, so both distillation terms are undefined）
- `ax2410.14425`：logits access on a model handle（卡住：steps 4 and 5 -- per_sample losses give scalars and logprob gives mean per-token log-probabilities; neither is a distribution over a vocabulary）
- `ax2410.14425`：gradients of a plugin-defined scalar with respect to the handle model's LoRA parameters, plus a write-back that keeps the resulting weights (a server-side LossView.gradients_of)（卡住：step 8 -- per_sample_gradients differentiates only each sample's own training loss (training on it is plain CE fine-tuning, a different method, and the paper's own ablation is about why that is not enough), and handle.lora() restores the previous state, so no unlearned LoRA can be produced）
- `ax2410.14425`：a server-side data kind carrying clean batches and labels（卡住：steps 3-8 -- the clean set stays an opaque resource and no view can iterate it, so no batch of (x, y) can be formed）
- `ax2410.14425`：a way for a plugin to own or request the host's training schedule (epochs, batch size, optimizer)（卡住：step 8's paper configuration (AdamW, 5 epochs, batch 32, lr 2e-4, r=512); rounds and steps belong to the host, and the paper's own hyperparameters are underreported anyway）
- `ax2411.17453`：The feature is dense by construction and the library is built to avoid exactly that: fedguard.ops.lowrank exists so that a LoRA effect is never formed, while Eq. (13)(14) feed the formed d_out x d_in matrix to a convolution. Building F_input for one client of Llama-2-7B (q and v, 32 blocks) is 64 x 4096 x 4096, about 1.07e9 elements, 4 GiB in float32, the paper's own example; there is no chunked, streamed or low-rank variant of the feature in the library.（卡住：steps 4-5 on a realistic 7B deployment without memory planning outside the plugin; the plugin builds one client's F_input at a time and releases it, which is all the library allows）
- `ax2411.17453`：No server-side action beyond the aggregation. The paper's platform can refuse to merge an adapter, take it down or warn users (Section 3.1, Section 6), and that disposition is left undefined; the library's server-side interventions are aggregation-scoped (select_and_weight, transform_update, replace_global).（卡住：the platform half of the paper's scenario: an exclusion from this round's aggregate is the closest expressible action, and a durable per-adapter verdict (quarantine, takedown, hand-off to mitigation) has no place in a round）
- `ax2506.22506`：客户端侧运行第二个模型（冻结 CLIP 图像编码器）的能力：ModelHandle 协议只有 lora/parameters/layout/tokens/losses/hidden/activations/per_sample_gradients/logprob/generate，句柄包着正在训练的那个模型，输入经 DataView 按文本 hash 记录，没有图像入口，也没有把独立编码器接进来的挂载点（卡住：步骤 4 的编码一半：每轮把本地图像变成 512 维嵌入（论文客户端侧的主要开销）。插件因此只能转发库外算好的嵌入表，而不是自己编码并共享）
- `ax2506.22506`：训练之外的离线阶段（离线训练一个部件的位置）（卡住：步骤 0–1 在库内没有落点。按规则 3 它们本来就不属于插件（检测器作为 resources 传入即可），所以不阻塞移植；它只说明如果要库内复现论文全流程，库缺一个离线环节）
- `ax2510.16830`：any epoch boundary -- the round is the only clock（卡住：the per-epoch cumulative quota of Eq. (3); gamma can only be approximated through a defender-chosen rounds_per_epoch）
- `ax2510.16830`：a view of the sampler or of the per-step selection indicator, and any action that can ask for a different batch（卡住：verifiable sampling (steps 4-5) and the certificate half of step 6; masking can only drop samples the host already chose）
- `ax2510.16830`：an optimizer-state (m_t, v_t) view and a per-step index（卡住：the AdamW transition, its fixed-point form and the state commitments of steps 13-14）
- `ax2510.16830`：base-weight values plus any hash or commitment operator（卡住：the frozen-tensor equality of step 10 and all of steps 1, 2, 5, 14, 15）
- `ax2510.16830`：a channel or field that can carry proof material (messages cap at 65536 bytes, a leaf proof is ~220 KB) and any proof operator（卡住：steps 16-19 in full; the aggregator's audit has nothing to check）
- `ax2510.16830`：an abort or rollback action for a round（卡住：VFT's hard-error rule; it is expressed as excluding every participant, which leaves the previous global model in place, and there is no way to roll back only the tainted client's contribution）
- `ax2510.16830`：a step-scoped view of which samples actually entered a batch（卡住：the client's counters can only report planned admissions, not observed selection, so even the enforcement half of step 6 reports what it did rather than what happened）
- `ax2603.12089`：没有任何接口能读写模型的词嵌入矩阵：更新是 LoRA 状态字典，ModelHandle.parameters/layout 只给名字与形状，lora() 只装适配器因子，transform_broadcast / replace_global 的载体也只有 LoRA 状态。（卡住：步骤 4、5、8，也就是水印本体：W_w 的训练、下发前 Tr_k←W_w 与 Tr_u←W_u 的逐客户端替换、每轮的水印强化训练。EmbTracker 的核心因此留在库外，能移植的只是对库外注入的水印做溯源。）
- `ax2603.12089`：没有服务器侧的数据视图，也没有 text→样本 的逆映射（DataView.text_of 不可逆），无法把新造的投毒样本交给 edit_samples。（卡住：步骤 3（水印训练集 D_w），并连带使步骤 8 没有训练数据。）
- `ax2603.12089`：插件拿不到词表/tokenizer，也不能用哈希库（允许的 import 里没有 hashlib）。（卡住：步骤 1、2（签名→触发词 token、触发器集合构造），两者只能变成防御方资源。）
- `ax2603.12089`：十个位置全部在联邦轮内，没有轮外/离线入口；服务器侧也没有训练步。（卡住：论文把步骤 9（对野外可疑模型的验证）放在训练之外，本移植只能挂在 SERVER_POST_AGGREGATE；步骤 8 的训练同样没有落点。）
- `ax2603.12089`：服务器默认没有可运行模型，声明 model_handle 的插件在部署不传 probe= 时会在第一个 SERVER_POST_AGGREGATE 抛 LookupError。（卡住：不提供模型的部署里的步骤 9。）
- `ax2608.06795`：an inference-time stage (a per-prompt hook before generation) or any stage outside the training round（卡住：step 7: one forward pass on a user prompt and rejecting it before generation; the whole runtime half of the method）
- `ax2608.06795`：a data kind carrying a user prompt / query stream（卡住：steps 1, 2, 5 and 7 on real user prompts; they can only run on a defender-supplied batch in this port）
- `ax2608.06795`：an action that refuses a prompt or stops a generation (the paper's filter_samples is not in ACTION_STAGES; mask_samples/edit_samples filter local training samples at CLIENT_PRE_TRAIN)（卡住：step 7's intervention: the plugin can only report which prompts would be rejected）
- `ax2608.06795`：a server-side model in the host (the server has no runnable model by default; the handle is defender-supplied)（卡住：steps 1 and 5 for deployments that do not pass a handle; the plugin declares model_handle and its docstring states the requirement）
- `ax2609.37367`：a second receiver of the same upload and a channel between receivers (the paper's distance-two knowledge, its honest-majority premise |View(i) cap H| > |View(i)|/2, and the EXCHANGESCORES / EXCHANGESTRINGS messages)（卡住：steps 8 and 11 entirely, and with them the pooled sets V_j and C_j; step 9 (strict majority vote) can only run with |R_j| = 1, i.e. on the single score of the receiver, so the protection against one forged score or one mistaken receiver is not ported）
- `ax2609.37367`：sampled decoding and beam search in the model handle (temperature/top-p/top-k nucleus sampling; beam width B with length penalty and early stopping, top beam only)（卡住：step 7 runs greedily, which the paper measures as the weaker setting, and step 10 loses the harvest recall the paper attributes to beam search (51.6% vs 13.5% of prompts recovering the target)）
- `ax2609.37367`：a server-side model by default: model_handle is mounted on the server only when the deployment passes probe=, and the shipped server handle (adapters/hf_probe.HFProbe) implements ProbeView.score only, not generate/logprob（卡住：steps 7, 10 and 13 in every deployment that does not hand in a full ModelHandle; without one the plugin raises LookupError at the first upload）
- `ax2609.37367`：an object for "the node's own adapter of this round" on the server side (theta_i)（卡住：steps 13 and 14: the reference is the broadcast base (an average of previously accepted uploads) instead of a freshly trained clean adapter of the receiver, so the ratio compares a client against the global model, not against a peer's own model）
- `huang2024antidote`：ModelHandle 没有读取模型自身（基座）权重数值的接口：layout()/parameters() 只给名字和形状，per_sample_gradients 只给梯度（卡住：式 (1) 的 |w_j| 只能对 LoRA 因子计算；论文真正的剪枝对象（微调后的稠密权重 w）取不到，因此只能做因子空间的 Wanda 剪枝）
- `huang2024antidote`：库没有"微调结束/即将部署"的位置或一次性信号（SERVER_POST_AGGREGATE 每轮都有，也不存在训练循环之外的位置）（卡住：one-shot 语义：必须由外部告知部署回合，否则插件不动作；也无法表达"只在整个作业结束后跑一次"）
- `huang2024antidote`：服务器侧宿主默认不提供模型，句柄只能由防御方自备（卡住：第 1 步的前向与激活统计：没有完整 ModelHandle 就测不到 A_j，插件只在 evidence 里报告而不猜（声明了 needs=model_handle，部署方也可用 RunSpec.unavailable 在开局就拒掉它））
- `huang2024booster`：训练之外（outside_training）的位置：11 个 Stage 全部是一轮联邦训练内的位置（SERVER_DISTRIBUTE … SERVER_POST_AGGREGATE），没有「上线之前的一次性对齐训练」。而且 `check_contract` 对空的 `at` 直接抛 ContractError（“`at` must be a Stage or a tuple of Stages”），所以连一个只报告的声明式空壳也无法以「无位置」的形式存在。（卡住：Algorithm 1 的整个 for t ∈ T 循环（步骤 1–10）无处挂载。）
- `huang2024booster`：插件不拥有训练循环、优化器与步状态：`run` 每个位置每轮调用一次，`ctx.state` 只跨轮保留，`round_state`/`step_state` 在作用域结束时清空，没有 AdamW 状态、没有 epoch/step 循环。（卡住：步骤 10（优化器更新）与 T 步对齐训练本身。）
- `huang2024booster`：服务器侧没有数据类别（KIND_SIDE['data']='client'）且默认没有模型：防御方自己的对齐/有害数据没有可读视图，服务器 `model_handle` 需防御方自备并传入。（卡住：步骤 1–2 的取 batch，以及步骤 4、5、8 在服务器一侧的梯度计算。）
- `huang2024booster`：没有「安装一个训练完成的检查点」的动作：`replace_global` 只接受本轮聚合出的 LoRA state，`transform_broadcast` 只改本轮下发内容，二者都要求插件自己算得出那份 state。（卡住：步骤 10 的输出 w̃ 及其效果（之后所有微调请求共享该基础模型）。）
- `huang2024booster`：同一优化步内三次前向/反向的契约：一次 `run` 调用里可以多跑几次 `model_handle`，但没有任何视图把「本步的宿主梯度」与「插件另算的两个梯度」绑在同一次参数更新上；CLIENT_PRE_STEP 的 `gradients` 属于客户端本地训练，服务器侧没有对应的训练步。（卡住：步骤 5–8 的三次梯度及其在同一优化步里的组合，亦即 g̃ 真的用于论文那次对齐训练。）
- `huang2024booster`：在 forward 之前改写输入 embedding 的动作：`edit_samples` 改文本、`transform_loss` 在 forward 之后、`ModelHandle` 只提供前向结果与对参数的梯度。（卡住：可选变体 Vaccine+Booster 的步骤 3（不影响纯 Booster 的判断）。）
- `huang2024vaccine`：a differentiable read of a layer's output (hidden embedding) with a graph, at a point where the loss is available（卡住：step 2 (backward_layer_embedding_grad) and therefore step 3 (concat_layer_gradient_norm) and step 4 (layerwise_embedding_perturbation)）
- `huang2024vaccine`：a way to run one forward pass with a supplied modification to a layer's output, i.e. a plugin-visible forward hook or a handle that accepts perturbed activations（卡住：step 5 (forward_hook_add_perturbation) and step 6 (perturbed_forward_backward), which is the entire defense: without it Vaccine degenerates into ordinary SFT (the paper's own point 3)）
- `huang2024vaccine`：a training-step position on the server side, where this one-off alignment actually happens; the server has no model and no step, and the client-side steps run after their host's forward pass has finished（卡住：steps 1-7 as an alignment stage; only a client-side ALIGNMENT step would be reachable, which is a different method）
- `huang2024vaccine`：a loss point whose forward pass has not already been consumed, i.e. an extension that can re-enter the model rather than only replace the loss scalar（卡住：the whole two-pass structure; transform_loss at CLIENT_LOSS substitutes a scalar but cannot inject anything into the pass that produced it）
- `inan2023llamaguard`：a second model handle: a plugin receives one `model_handle` per side, and on the client the adapters glue that slot to the model being trained（卡住：step 3 in any deployment that follows the adapter default; the guard model has to be loaded and handed in by the app through ClientGuard.begin_round/pre_train(model_handle=...), and a plugin can never hold the training model and the guard model at once, which is what the generated-then-judged output guardrail would need）
- `inan2023llamaguard`：a stage or view that carries the text of what the model generated（卡住：the output half of the paper's guardrail (the response classification of Section 3.1 and every response-side number in the paper); LossView exposes output tensors and sample hashes, not text, and the server side never sees text）
- `inan2023llamaguard`：a first-token distribution read on a model handle: only logprob(prompts, targets), the mean per-token log-probability of a target, exists（卡住：the exact step-4 reading for any verdict word that is not a single token in the handle's tokenizer; with the tokenizer the paper describes (safe and unsafe are single tokens) nothing is blocked, but the plugin cannot check or enforce that）
- `rieger2022deepsight`：服务器侧没有模型，也没有“用服务器自己生成的随机输入跑前向”的入口；ModelHandle 只接受 adapter 能分词的样本序列，input_dim 也没有来源（卡住：步骤 6（随机探针前向）与步骤 7（DDif）：5 个视图里的 3 个 DDif 视图整条缺失，Alg. 2 的共识聚类只平均 2 个距离矩阵而不是 5 个）
- `rieger2022deepsight`：没有“最后一轮”的信号：RunSpec/StageContext/ctx.round 里都没有总轮数，也没有训练结束后的插件位置（卡住：步骤 15（末轮按簇聚合与按簇下发））
- `rieger2022deepsight`：没有任何动作能产生多于一个聚合结果（select_and_weight 只给一次聚合的权重，replace_global 只换一个全局模型），宿主也没有“每簇一个模型”的接口（卡住：步骤 15 的按簇聚合，即使知道是末轮也搬不进来）
- `rieger2022deepsight`：常规 LoRA 部署不把输出头纳入适配，UploadView.modules 里就没有可当输出层的模块（卡住：整个过滤层（步骤 2–5、8–12）：插件在第一轮就报 skipped，只剩裁剪层与等权聚合在起作用。这是本方法在 LoRA 场景下的结构性障碍，不是实现缺陷）
- `rosati2024repnoise`：a position outside the federated round. All ten stages of STAGE_KINDS lie inside a round and the placement of this method in its own extraction card is outside_training; GuardPlugin.setup(spec) is called once before the first round but carries no context, no view and no way to return a finding.（卡住：the immunization as the paper runs it, a one-off pass over the pairs before release: steps 2-9 have nowhere to live.）
- `rosati2024repnoise`：a differentiable read of an intermediate activation, and a way to re-enter a forward pass with one (ModelHandle has no hook, patch or pre-forward method, and activations() detaches and moves to the CPU).（卡住：step 6 (the MMD noise term) and the graph under step 3. The ablation of the paper shows that the noise term without ascent is worse than the base model and ascent without noise is nearly useless, so neither half is usable alone.）
- `rosati2024repnoise`：a way to apply a module (the language-model head) to a tensor held by a plugin.（卡住：step 4 (the layer-wise tuned-lens loss) and through it steps 7, 8 and 9.）
- `rosati2024repnoise`：a backward pass for a scalar built by a plugin, and a server-side optimizer step.（卡住：steps 9 and 10: the composite loss can be written down but never differentiated into the model, and nothing on the server can step the weights.）
- `rosati2024repnoise`：a server-side object that is the whole model rather than a LoRA state dict: replace_global validates against the aggregate, and base weights are visible to a plugin only as names and shapes.（卡住：step 11 as the paper defines it (an immunized full checkpoint); a LoRA-shaped artifact would be a different object and is not the defense of the paper.）
- `shen2024seal`：没有轮外/离线位置：STAGE_KINDS 的十个位置（SERVER_DISTRIBUTE … CLIENT_POST_TRAIN）全部在联邦轮内，论文自己把 S1–S3 标为 outside_training（卡住：选择器训练（S2）整段没有挂载点；方法的这一步只能留在库外，产物作为资源）
- `shen2024seal`：插件不拥有训练循环：不能决定下一步用哪条数据、不能自己步进模型参数、不能在 iteration 上把 D_safe 与 D 配对，也不能决定步数 K 与 γ 的调度（卡住：步骤 5（配对采样）与步骤 7（公式 (4) 的 θ 更新））
- `shen2024seal`：没有被训练模型之外的第二份参数（辅助模型 θ̂）；ModelHandle 只在被训练模型上加载 LoRA、计数前向/反向（卡住：步骤 8（公式 (6)）以及依赖它的步骤 9（公式 (5) 的损失 gap））
- `shen2024seal`：每个客户端只有一份 data kind，训练步里没有注入第二批样本的机制；LossView.loss_on 只前向宿主格式的 batch，插件没有 tokenizer、造不出 D_safe 的 batch（卡住：上层安全损失 (1/M)Σℓ(θ;z_i^safe) 与公式 (4) 的第一项；也说不了步骤 6 需要的确切口径（响应长度归一化 NLL，而不是宿主训练损失））
- `shen2024seal`：没有承载 S2 迭代的位置：CLIENT_LOSS/CLIENT_STEP 每个宿主 step 调用一次，但插件不能改变宿主后续 step 用哪条数据，mask_samples 也只在 CLIENT_PRE_TRAIN 生效一次（卡住：步骤 9/10（公式 (5)/(8)）：逐样本损失与样本身份现在拿得到（LossView.per_sample_losses + sample_ids），但 ω 的更新无法与论文的 S2 迭代、配对样本和 θ 的联合更新绑在一起）
- `shen2024seal`：没有跨客户端的样本视图（服务端只有 uploads、reports、messages）（卡住：S3 的字面语义：在完整 D 上取全局 top p%；只能退化为每客户端每轮截断（见 Deviations））
- `tamirisa2024tar`：训练之外或发布前的位置：STAGE_KINDS 的 11 个位置全部在联邦轮内（SERVER_DISTRIBUTE 到 SERVER_POST_AGGREGATE），没有轮前或发布前的位置（卡住：TAR 的整条流水线（论文自己把 stages 标为 outside_training）；一轮内最近的表面只有 SERVER_DISTRIBUTE 的 outgoing LoRA 状态）
- `tamirisa2024tar`：插件拥有训练循环：自己选数据、自己建并步进优化器、在内层坐标之间切换模型参数（卡住：步骤 3（K=64 步 SFT 攻击轨迹）与步骤 4、5（坐标复用与子采样））
- `tamirisa2024tar`：把内层优化写成 θ 的可微函数（直线估计器或一阶 MAML）并取任意损失对基座参数的梯度（卡住：步骤 6（L_TR 在攻击坐标上求值）、步骤 7（元梯度）、步骤 8（g_TR 累积））
- `tamirisa2024tar`：承载基座权重（全参数）的读与写：没有数据类别、没有视图、没有动作；能替换模型的动作都只收 PEFT 状态字典（卡住：步骤 9（retain 梯度对 θ）、步骤 10（θ 的加权外层更新）、步骤 11（返回 θ_N））
- `tamirisa2024tar`：第二个模型 θ_G0 与可微的残差流激活（式 2 的锚定项）（卡住：步骤 9 的第二项）
- `tamirisa2024tar`：可微的输出分布熵或 DPO 损失面（带图的 logits 或 log-prob）（卡住：步骤 6a（武器化熵）与 6b（拒绝 DPO））
- `tamirisa2024tar`：服务端的数据类别与可运行模型：KIND_SIDE 里 data 属 client，OpenFedLLM 服务端适配器默认不提供 model_handle（要防御方以 probe 传入）（卡住：任何把外层循环放到服务器一侧的尝试；防御方的 D_TR、D_retain、A_train 没有入口）
- `tamirisa2024tar`：与 LoRA 因子空间不同的参数规模与显存管理：每外层步最多 K=64 个内层步的激活与优化器状态，论文用分片梯度累积避免 K 个计算图（卡住：步骤 3 与步骤 10 的现实可行性（论文自称朴素实现 prohibitively expensive，8B 全参数、8 张 A100））
- `xie2024gradsafe`：对任意文本指定一个 (prompt, response) 对，并按 token 段（只在回复上）取损失及其对基座权重的梯度（卡住：论文步骤 2/7 的精确梯度——插件只能拿到句柄对配对文本自己那条训练损失的逐样本梯度，切片梯度因此是近似）
- `xie2024gradsafe`：一个在首轮之前、能拿到 model_handle 的位置（或任何轮外/离线入口），用来在库内跑 Phase I–III 并保存产物（卡住：步骤 4（不安全参考平均）、5（逐切片余弦）、6（相似度差阈值）——S 与不安全梯度参考必须在库外算好）

## 提取接口：方法要从训练里取什么，库给不给得出

只有按新版说明（含 `extraction_needs`）移植的论文有这一项。

| 论文 | 数据 | 何时何侧 | 库是否提供 | 经由 / 缺什么 |
|---|---|---|---|---|
| `ax2103.05633` | 每一步的批次身份 I_t（这一步用了哪些样本） | 客户端，每个训练步：前向之后、反向之前（CLIENT_LOSS） | partly | ctx.loss.sample_ids() 给出该批每一行的样本哈希，但只有 trainer extension 才提供 CLIENT_LOSS，普通 Trainer callback 到不了这一点，且适配器没有 identify 时抛 LookupError；数据集索引要靠 ctx.data.manifest 的 hash→index 自己映射，哈希本身由宿主算。 |
| `ax2103.05633` | 每一步之后的权重 W_t | 客户端，每个训练步之后（CLIENT_STEP） | yes | ctx.train_trace.lora()（CPU 副本）。只有 LoRA 因子，没有冻结的基座权重。 |
| `ax2103.05633` | 每步训练元数据 M_t（优化器种类、学习率、损失） | 客户端，每个训练步（CLIENT_STEP、CLIENT_LOSS） | partly | ctx.train_trace.steps() 里宿主自己 log 的标量（本实现从其中的 lr 字段取学习率）；优化器与调度不是任何视图，插件看不到。 |
| `ax2103.05633` | 初始权重 W_0 与声称的初始化策略 ζ | 客户端，轮次开始（CLIENT_PRE_TRAIN）或打包时 | partly | W_0 = ctx.received_model.state()（CLIENT_POST_TRAIN 也可读）；ζ 不在库里，只能作为插件构造参数由防御方声明。 |
| `ax2103.05633` | 初始化分布的公开参数（KS 检验的原假设） | 服务器，验证时（SERVER_RECEIVE） | no | 库没有这个视图；本实现要求防御方以 resource init_spec 给出每个状态键的分布。 |
| `ax2103.05633` | 发布证明的通道：检查点、每步数据签名、元数据 | 客户端上传前（CLIENT_POST_TRAIN）→ 服务器收到时（SERVER_RECEIVE） | partly | messages（只允许标量/字符串/扁平列表，上限 MESSAGE_LIMIT_BYTES=64 KiB）与 attachments（张量，runner 默认上限 64 MiB）。检查点走 (n_ckpt, d) 张量，哈希与学习率走 messages；没有加密与签名。 |
| `ax2103.05633` | 验证者手上的训练数据 D（按 I_t 取批次、重算签名） | 服务器，重执行时（SERVER_RECEIVE） | no | 原始样本过不了通道（messages 只能扁平标量、attachments 只能张量），也没有服务器侧数据集视图；本实现要求防御方以 resource client_data（client→{样本哈希: 样本}）提供，等于要求服务器持有每个客户端的本地数据。 |
| `ax2103.05633` | 在验证者一侧重执行一步训练 update(W, D[I_t], M_t) | 服务器，验证时（SERVER_RECEIVE） | partly | 服务器侧 model_handle 由防御方自备（可选，probe 参数）；ModelHandle 只有前向/反向原语、没有“训练步/优化器”，本实现用 per_sample_gradients + states.unflatten/add 拼出朴素 SGD 的一步，每样本一次反向（论文是每步一次）。 |
| `ax2103.05633` | 论文式 (1) 的 update() 本身（含优化器状态） | 客户端训练循环内 / 服务器重执行时 | no | 没有任何视图暴露优化器或一步更新；带动量、二阶矩、权重衰减的 update 无法复现，只能假定朴素 SGD（论文也要求 update 属于已知可接受算法）。 |
| `ax2103.05633` | epoch 边界（每轮步数 S） | 客户端打包时 / 服务器排序时 | no | 库不告诉插件宿主怎么分 epoch；本实现把它作为插件参数，并由证明自身携带（P9 的按轮排序依赖它）。 |
| `ax2103.05633` | 松弛阈值 δ 与验证预算 Q | 服务器，验证时 | no | 论文只给标定方法、不给数值；作为插件构造参数（δ=None 时只报距离、不判 FAIL）。 |
| `ax2103.05633` | 验签、解密、时间戳或公开账本 | 服务器收到时（SERVER_RECEIVE） | no | 库没有密钥、加密、签名、账本接口；规则 3 也把密码学协议排除在插件之外。 |
| `ax2103.05633` | 已验证证明的历史 P_0..P_R（热启动的链式信任） | 服务器，验证之前 | no | history 视图只有每客户端每轮的标量特征，原始对象要 recorder 才能读回，也没有“已验证明”的存储；本实现用“第一个检查点必须等于本轮广播基座”做联邦版替代。 |
| `ax2103.05633` | 证明在轮内与跨轮的存储 | 客户端（轮内）与防御方（跨轮） | partly | 轮内可放 ctx.round_state 与 attachments（受 64 MiB 上限约束）；跨轮存储库外自理。 |
| `ax2104.13230` | 到达样本 (x_t, y_t)，含标签 | 客户端，CLIENT_PRE_TRAIN（论文里逐样本到达时） | partly | DataView.samples()/manifest 给样本与哈希，但没有标签访问器；插件由调用方传入 label_of 可调用对象取标签 |
| `ax2104.13230` | 样本的特征向量 x（式 (10) 的 slab 判据要它） | 客户端，CLIENT_PRE_TRAIN | partly | DataView 没有特征访问器；唯一能拿到向量的是 ModelHandle.hidden（每样本一次前向），于是 slab 跑在池化隐状态上，而不是论文声明的输入特征 |
| `ax2104.13230` | 干净预训练集 D_pre（样本+标签） | 客户端，轮次之外（防御方资产） | yes | resources + ctx.resource("clean_reference") |
| `ax2104.13230` | 类质心 mu_y、mu_-y 与阈值 s_y（式 (10)） | 客户端，CLIENT_PRE_TRAIN（论文写成训练前一次性准备） | yes | 插件在 run 内用 clean_reference 的样本 + ModelHandle.hidden 现算；论文没给 s_y 的值或算法，由插件自选（见 open_choices） |
| `ax2104.13230` | 逐样本损失梯度 ∇_θL(x, θ)（式 (11)） | 客户端，CLIENT_PRE_TRAIN | yes | ModelHandle.per_sample_gradients(samples, group="lora")，每样本一次反向；参数是 LoRA 因子，不是论文的 d 维 logistic 权重 |
| `ax2104.13230` | 参考集上的 Hessian H（式 (7)/(14)）及其逆 | 客户端，CLIENT_PRE_TRAIN（论文里预计算一次） | no | 库里没有二阶算子，LoRA 参数上 p×p 也不可行；移植改用参考梯度的阻尼经验 Fisher（见 Deviations、missing_ops） |
| `ax2104.13230` | 最近 w_inf 个影响值的滑动窗口（算法 1 第 8 行） | 客户端，跨轮保留 | yes | ctx.state（插件私有，整个 run 保留，轮末不清空） |
| `ax2104.13230` | 影响对样本的梯度 ∇I(x)（式 (13)，做扰动要用） | 客户端，CLIENT_PRE_TRAIN | no | 没有输入梯度视图或算子；loss / ModelHandle 只给前向值和参数梯度 |
| `ax2104.13230` | 承载改写样本的样本编辑动作 | 客户端，CLIENT_PRE_TRAIN | partly | edit_samples 存在（add / rewrite by hash），但扰动方向算不出来，插件从不提出它 |
| `ax2104.13230` | 逐样本到达、到达后立刻更新一次参数的流式循环 | 客户端，每个训练步 | no | CLIENT_PRE_TRAIN 每轮只跑一次、一次看到整轮样本；CLIENT_LOSS/CLIENT_PRE_STEP 虽然有逐步视图，但那里没有 mask_samples/edit_samples 动作，论文的『过滤/编辑→马上 OGD 一步』对不上 |
| `ax2210.07714` | 本轮每个客户端的本地模型 Lt_i（S2/S3 的输入） | 服务器侧 SERVER_RECEIVE 收集；客户端侧下一轮 CLIENT_POST_TRAIN 验证 | partly | 服务器读得到 ctx.uploads.state(cid) / base_state()；但库里没有同一轮内的服务器→客户端通道，只能放进 Findings.attachments，由宿主在下一轮 begin_round 交付，客户端用 ctx.reports.attachments('<server plugin>.pack.<cid>') 取回（晚一轮） |
| `ax2210.07714` | 本轮全局模型 Gt（S5 距离的参照） | 客户端，验证时 | partly | 服务器把该轮的广播基 ctx.uploads.base_state() 一并打进 pack；客户端当前的 received_model 已经是下一轮的全局模型，不能用作参照 |
| `ax2210.07714` | 验证客户端自己的模型 Lt_j（S6 相对化的分母） | 客户端，验证时 | yes | 同一 pack 中含该客户端上一轮的上传；不在 pack 中（上轮未参与）时插件不投票 |
| `ax2210.07714` | 验证客户端的本地样本 Dj（论文默认 2560 条） | 客户端 CLIENT_POST_TRAIN | yes | ctx.data.samples() |
| `ax2210.07714` | 每个样本的标签（S7 按标签求均值） | 客户端，验证时 | partly | 库里没有标签字段（DataView.manifest 只有 hash/source/length），必须由防御方以 resources={'label_of'} 注入 sample -> label 的可调用对象 |
| `ax2210.07714` | 逐样本、逐层的深层输出 DLO（S4/S5） | 客户端，验证时 | yes | ctx.model_handle.lora(state) + ModelHandle.activations(samples, select=全真, pool=...)，代价记在 Findings.cost（forward_samples） |
| `ax2210.07714` | 对每个候选模型做一次前向的模型句柄 | 客户端，验证时 | partly | 句柄要由宿主交给 begin_round；已发布宿主里客户端 model_handle 是 glue（Flower）或需要改脚本（OpenFedLLM），不交就没有 DLO |
| `ax2210.07714` | 二值投票回传（S13） | 客户端 CLIENT_POST_TRAIN → 服务器 SERVER_AGGREGATE | yes | Findings.messages（≤64 KiB 的扁平 0/1 列表）随上传到达，服务器用 ctx.uploads.reports.messages('<client plugin>.votes') 读 |
| `ax2210.07714` | 投票矩阵与投票者身份/顺序（S14 的输入） | 服务器 SERVER_AGGREGATE | yes | ctx.uploads.clients 与消息里的 pack_clients / pack_round 对齐；ctx.state 保存上一轮 pack 的轮号与客户端列表 |
| `ax2210.07714` | 剔除决定与等权权重（S15/S16） | 服务器 SERVER_AGGREGATE | yes | Decision(excluded=..., weights={cid: 1.0}) 配 acts={'select_and_weight'}；真正的求和平均由宿主聚合完成 |
| `ax2210.07714` | 跨轮的 pack 索引（两代） | 服务器，跨轮 | yes | ctx.state（插件私有、跨位置跨轮）保存 sent / pending 的 {round, clients} |
| `ax2210.07714` | 本地训练过程（损失/梯度/样本） | 不需要 | yes | 论文明确防御只在聚合前过滤；插件不声明 loss / gradients / mask，不改训练 |
| `ax2301.09508` | 每个客户端本轮上传的本地模型 W_i^t（LoRA 全部因子项） | 服务器侧，SERVER_AGGREGATE，一批上传到达后 | yes | ctx.uploads.state(cid)，再用 fedguard.ops.states.flatten 展平 |
| `ax2301.09508` | 本轮广播用的全局模型 G^{t-1}（Eq. 2 的余弦、Eq. 3 的 L2、簇先验都要它） | 服务器侧，SERVER_AGGREGATE | yes | ctx.aggregate.base（该轮广播的 base） |
| `ax2301.09508` | 初始全局模型 G^0 的展平均值 mu_p 与标准差 sigma_p（基线 Beta process） | 服务器侧，插件第一次被调用那一轮的 SERVER_AGGREGATE | partly | ctx.aggregate.base；只有从第 0 轮就挂载才等于 G^0，接口不告诉插件本轮是不是第一轮，晚挂载会拿当时的全局模型当基线 |
| `ax2301.09508` | 展平维度 l | 服务器侧，SERVER_AGGREGATE | yes | states.flatten(...).numel() |
| `ax2301.09508` | 每个客户端首次参与时的浓度随机数 c_i ~ Poisson(c) | 服务器侧，该客户端第一次出现的那一轮 | yes | ctx.rng（numpy Generator），不碰全局随机状态 |
| `ax2301.09508` | 跨轮保存的每客户端 Beta 后验状态 (c_i, H_i)，H_i 是 l 维向量 | 服务器侧，跨轮 | yes | ctx.state |
| `ax2301.09508` | 跨轮保存的簇结构 (mu_cl, scale_cl, n_k, tau_k) | 服务器侧，跨轮 | yes | ctx.state |
| `ax2301.09508` | 本轮参与者及上传到达顺序 | 服务器侧，SERVER_AGGREGATE | yes | ctx.uploads.clients（顺序就是宿主交上来的顺序） |
| `ax2301.09508` | 检测结论回到聚合：剔除谁、保留者用什么权重 | 服务器侧，SERVER_AGGREGATE | yes | Decision(excluded=..., weights=...) 配动作 select_and_weight |
| `ax2301.09508` | 模型前向/反向 | 不需要 | yes | 方法全程不跑模型，因此没有声明 model_handle |
| `ax2305.05506` | the m group aggregates u_1..u_m of the group-testing round (what the paper's server actually observes) | server, after the group secure aggregation and before the test, in the test round | no | no data kind for group aggregates exists (KINDS has none, and `aggregate` is a single state, not m). The plugin rebuilds them from `uploads` with ops.states.weighted_average over the group members, which is only possible where the deployment exposes per-client uploads; RunSpec.unavailable with 'uploads' makes check_contract refuse the plugin before the first round. |
| `ax2305.05506` | the per-client uploaded LoRA states and the participant list of the round | server, SERVER_AGGREGATE | yes | ctx.uploads / UploadView.clients, state(cid), base_state(); ctx.participants |
| `ax2305.05506` | the assignment matrix A and the group membership of every client of the round | server, offline design, and the test round where the columns must be matched to the round's clients | partly | resource `assignment` carries A; the library supplies the participant list at the stage, but has nowhere to put A and no way to hand A to the clients (SERVER_DISTRIBUTE sends a LoRA state, not a configuration) without an announce/exchange round trip, which the paper does not have. |
| `ax2305.05506` | the task utility of each group aggregate on a server-side validation set (top-1 accuracy, balanced accuracy, source label recall) | server, test round, on the aggregated group models | yes | `model_handle` (defender-supplied server model, probe=) with ModelHandle.lora(state) plus ModelHandle.logprob(prompts, targets) for candidate-ranking accuracy, or ModelHandle.losses(samples) for a loss utility. Requires the defender to pass a runnable server model; without one the plugin reports a skip. |
| `ax2305.05506` | the readout (fully connected) layer weights of each group aggregate, for the first principal component | server, test round | partly | only LoRA factors are visible (UploadView.state, ops.states.stack over the readout module keys); the full weight matrix is never formed and ModelHandle has no call that returns weights. |
| `ax2305.05506` | the offline tables Pr(Z = z / N_m = n_m), Delta-hat(n_m) and n_m^max | outside training, defender side, computed from A | no | resources `null_table` and `delta_table`; the library has no place for offline precomputation and no data kind for a table. The paper computes them offline (Eqs. (3), (11), (15)). |
| `ax2305.05506` | which round runs the group test, and reuse of the flagged set in later rounds | server, every round | partly | ctx.round plus ctx.state (persisting across rounds) let the plugin test once (test_round) and re-emit the exclusion; the library has no notion of a round that produces no global model and no cross-round exclusion of a client. |
| `ax2305.05506` | the exclusion of the flagged clients and the re-aggregation over the rest | server, SERVER_AGGREGATE and the host aggregation that follows it | yes | Decision(excluded=...) with the select_and_weight action; the adapter drops those clients in before_aggregate and aggregates the kept ones. |
| `ax2402.12168` | 本地干净训练集的逐样本标签 y（构成 (x, y)） | 客户端本地，PSIM 训练之前（论文的 client_post_train 位置） | no | CLIENT_PRE_TRAIN 的 ctx.data（DataView）只给 samples() 原始样本对象与 text_of()（把样本折叠成文本）；manifest 的 SampleRecord 只有 hash / source / length。插件无从知道哪条样本属于哪一类，只改标签不改文本时样本 hash 也不变 |
| `ax2402.12168` | 重置标签后的数据集 D_clean_reset^train（同一批样本、重置后的标签） | 客户端本地，PSIM 训练之前 | no | edit_samples 的 rewrite 改的是宿主本轮训练样本，会直接进入 victim model 自己的训练——正是论文禁止的（PSIM 必须独立于 victim model）。库没有任何机制把这批数据交给第二个训练 |
| `ax2402.12168` | 一次独立的 PEFT 持续训练（自己的数据与优化器、从 θ_p 初始化的第二个模型 → θ_p^psim） | 客户端侧，一轮本地训练之外（论文的 client_post_train） | no | 没有任何 stage 或 action 能启动一次训练：CLIENT_POST_TRAIN 在本地训练结束后只读或替换 local_update，CLIENT_STEP 只记录标量，transform_update / replace_global 替换的是状态字典。按规则 3，训练一个独立检测器本来也不属于插件，只能作为 resource 传入 |
| `ax2402.12168` | 中毒的第三方预训练权重 θ_p（PSIM 与 victim model 的共同初始化） | 客户端/防御方，PSIM 训练之前 | no | 库只搬 LoRA 状态字典（<module>.lora_A.weight / lora_B.weight），基座权重不经过任何视图。model_handle.parameters(scope='all') 只能用谓词列出基座参数名、layout() 给形状、per_sample_gradients(scope='all') 给基座权重的梯度，但都读不回权重值本身，也没有用给定权重初始化第二个模型的接口 |
| `ax2402.12168` | PSIM 模型 M(·) 以及它对待判样本 x 的输出（置信度 C） | 推理时，每个待判样本 | no | 客户端 model_handle 包着正在训练的模型（宿主 base + 当前 LoRA），handle.lora(state) 只能在那个 base 上换适配器；库不给第二个句柄，也没有换 base 的办法。ModelHandle.losses() 确实能对任意样本做逐样本前向，但它评的是当前训练模型，评不了另一份模块，也不返回类别概率。服务器侧 ProbeView.score(lora) 只对整份 LoRA 给行为指标，完全不接触样本 |
| `ax2402.12168` | 待判定的输入样本 x 本身 | 推理时（论文的 outside_training） | no | Stage 的 11 个位置（STAGE_KINDS）全部在一轮联邦训练之内，没有任何位置看到一条即将被预测的输入。客户端最近的是 CLIENT_LOSS，那里拿到的是本轮训练批次的 per_sample_losses（训练损失）与 sample_ids()（把批次行映射回 DataView.manifest 的哈希），不是推理请求 |
| `ax2402.12168` | 阈值判定后的动作：剔除该样本，或放行并返回 victim model 的预测 y | 推理时，逐样本 | no | ACTION_STAGES 里唯一逐样本的动作是 CLIENT_PRE_TRAIN 的 mask_samples / edit_samples（对象是本轮训练样本），没有丢弃推理请求的动作；干净分支的 y 由宿主推理产生，库内没有位置能看到输入并回写预测 |
| `ax2402.12168` | 被剔除样本的记录或上报 | 推理时 | no | findings 绑定在 (round, stage) 上、写在一轮训练之内，推理决定无处可记 |
| `ax2409.14119` | Ltask, the task loss of the current local training step, still attached to the graph | client, inside a training step, after the forward pass and before backward | yes | Stage.CLIENT_LOSS with the loss kind declared -> LossView.loss; only reachable when the host replaces the trainer compute_loss through fedguard.adapters.hf_trainer_ext.extend_trainer |
| `ax2409.14119` | the trainable PEFT tensors W_p themselves (values, not copies), for Lamp | client, the same point in the step | yes | LossView.parameters() -> {name: torch.nn.Parameter} of the requires_grad parameters (the LoRA factors); fedguard.ops.states.module_info classifies each name as factor A or B |
| `ax2409.14119` | the attention scores a_h of every layer and head (Eq. 2; for sentence classification the attention of the input tokens on the [CLS] output) | client, inside the training step, or from a model pass | no | no data kind or view carries attention scores. LossView exposes batch, outputs, loss and parameters only, and hf_trainer_ext.py states that attention scores need output_attentions set by the app. ModelHandle offers submodule inputs/outputs, hidden states, tokens, losses, per-sample gradients and generation, but not attention weights, and it exposes parameter names and shapes, not the frozen base weights, so softmax(QK^T) cannot be recomputed inside a plugin either. |
| `ax2409.14119` | the exact tensor list that counts as all PEFT layers per architecture (adapter up/down projections, LoRA factors, prefix reparameterization matrices) | client, at setup and per step | partly | the trainable parameters are visible, but this library carries LoRA state dicts only, so the adapter and prefix variants of Table 7 cannot be built; the port amplifies lora_A / lora_B tensors and leaves other trainable tensors (e.g. modules_to_save) alone |
| `ax2409.14119` | lambda_amp and lambda_reg selected on the defender clean labelled validation set under the 2% CACC rule | outside the round: offline model selection before or around the federated run | no | no library interface; it needs a labelled clean validation set and retraining per candidate. The plugin takes lambda_amp as a constructor argument (defaulting to the smallest Table 7 candidate so the class can be mounted bare) and has no lambda_reg |
| `ax2409.14119` | the possibly backdoored base PLM with randomly initialized PEFT layers attached (step 1) | client (and server, for the broadcast global model), before any training step | no | not extractable and not a plugin concern: it is model construction done by the host or the defender; the library sees LoRA state dicts and the server has no model by default |
| `ax2410.14425` | the round's new global LoRA, i.e. the model the defense would unlearn (the paper's poisoned student, in factor space) | server side, after aggregation and before the next broadcast (SERVER_POST_AGGREGATE) | yes | ctx.aggregate.result (AggregateView: base + result, plus AggregateView.global_delta); per-client contributions via ctx.uploads.factor_delta(cid) |
| `ax2410.14425` | the poisoned student as the paper means it: full model weights, since weight poisoning lives in the base model and not only in an adapter | server side, before the unlearning phase | no | only LoRA factors cross the server boundary here (ClientUpdate.lora/base); a full model exists at most as a ModelHandle, and the narrow ProbeView exposes only behavioral score(lora) |
| `ax2410.14425` | white-box trainable access to the student: a forward on a clean batch, a backward of a plugin-defined composite loss with respect to its LoRA parameters, and an optimizer step whose result is kept | server side, once per unlearning step (there is no server-side analogue of CLIENT_LOSS / CLIENT_PRE_STEP / CLIENT_STEP) | no | the server stages carry no loss and no gradients kind and no step; ModelHandle must leave the model's weights, mode and gradients exactly as found, and offers neither logits nor gradients of a plugin-defined scalar |
| `ax2410.14425` | the teacher's forward on the same clean batch: logits z_t and final hidden states h_t, after the dimension-alignment layer g | server side, every unlearning step | no | exactly one ctx.model_handle exists per invocation and the server adapter has a single probe= slot (adapters/openfedllm.py); a named resource has no sanctioned forward path, so using one would assume an interface that is not in the reference |
| `ax2410.14425` | the student's logits z_s on the clean batch (eq. 7's cross-entropy and eq. 8-10's temperature KL) | server side, every unlearning step | no | ModelHandle returns per-sample losses, hidden states, activations, logprobs and generations; nothing returns logits, and LossView (per_sample_losses, gradients_of) is client-side only |
| `ax2410.14425` | the student's final hidden states h_s, pooled the same way as h_t | server side, every unlearning step | partly | ModelHandle.hidden(samples, layer, pool) can produce them for the one handle, but the teacher half h_t has no path, and the paper does not say which token position or pooling it uses |
| `ax2410.14425` | clean labelled batches (x, y) from D_clean_train, iterated for 5 epochs at batch size 32 and paired with the student's tokenizer | server side, throughout the unlearning phase | partly | KIND_SIDE gives the server no `data` kind, so the set can only be an opaque resources entry read by ctx.resource(name); no view iterates it, batches it, or exposes labels |
| `ax2410.14425` | the unlearning schedule itself: 5 epochs, batch 32, AdamW, lr 2e-4, LoRA r=512, and the final-checkpoint rule | server side, the whole unlearning phase | no | a plugin runs once per stage per round; no stage and no action lets a plugin own or ask the host for a multi-step training loop |
| `ax2410.14425` | the unlearned LoRA to install as the new global model | server side, at the end of the unlearning phase, before the next broadcast | yes | proposals['replacement'] with a full LoRA state dict at SERVER_POST_AGGREGATE (ACTION_STAGES; core/actions.py _replace_global; returned by OpenFedLLMGuard.after_aggregate) -- but the state itself cannot be produced without the rows above |
| `ax2411.17453` | the LoRA factor pair (A, B) of every module of one client's adapter | server side, after the uploads arrive and before aggregation (SERVER_RECEIVE / SERVER_AGGREGATE) | yes | needs={'uploads'}; ctx.uploads.state(cid) for the whole state, ctx.uploads.factors(cid, module) for one module |
| `ax2411.17453` | which transformer block and which target module each factor pair belongs to (Eq. (13) needs the target modules of a block, Eq. (14) needs the block order) | server side, same moment, read from the state-dict keys | yes | fedguard.ops.states.module_info(key) returns layer (first integer component) and role (last path component); the keys come from ctx.uploads.state(cid) |
| `ax2411.17453` | the adapter's weight-space change delta = B A, materialized at base-weight shape (d_out, d_in), rank removed (Eq. (6)) | server side, same moment | yes | ctx.uploads.cumulative(cid, module) -> LowRank -> .dense(); the round's change is ctx.uploads.increment(cid, module). This is exactly the rank-independence that the paper calls the key to cross-rank transfer (Table 9) |
| `ax2411.17453` | the alpha / r scale that the served model actually applies to B A | server side, static for the run | yes | ctx.spec.lora_scale (RunSpec.lora_scale); UploadView already folds it into cumulative / increment, so the plugin does not apply it a second time |
| `ax2411.17453` | the participants of the round and a way to keep an adapter out of the aggregate | server side, SERVER_AGGREGATE | yes | ctx.uploads.clients plus acts={'select_and_weight'}: Decision(excluded={...}) removes a client from before_aggregate(); clients not flagged keep the weight they would have had |
| `ax2411.17453` | an adapter layout that is uniform across clients and across rounds (same blocks, same target roles, and target modules that share (d_out, d_in); the classifier is trained for one input shape) | server side, every round | partly | the runner validates uploads against the broadcast base (strict_shapes, key by key and shape by shape), and the plugin itself refuses to judge a client that lacks a (block, role) pair, and refuses the round when the configured roles do not stack (this is where GQA models fail: q_proj is 4096x4096 and v_proj is 1024x4096 in Llama-3-8B). The paper says only that any variation in input dimensions requires retraining the classifier (Section 7); it gives no alignment rule, so nothing in the library can supply one |
| `ax2506.22506` | 每个客户端本地样本的图像嵌入（冻结 CLIP 图像编码器 + 固定 prompt learner 的输出，论文 d = 512） | 客户端，本轮本地训练结束、上传之前（CLIENT_POST_TRAIN） | partly | 位置和通道都有：CLIENT_POST_TRAIN 能读 data，Findings.attachments 经 ClientGuard.outbox_tensors() 与 ClientUpdate.attachments 到服务器的 ctx.attachment('sabre_embeddings.embeddings')。缺的是产生它的运行时：ModelHandle 只能对正在训练的文本模型做前向/反向（tokens/losses/hidden/activations/per_sample_gradients/logprob/generate），没有图像输入也没有第二个模型的入口，所以编码只能由防御方在库外做完，按样本 hash 作为 resources['embeddings'] 传入 |
| `ax2506.22506` | 每个客户端本轮的嵌入条数 n_k（式 7 的分母，也是 count 口径的基础） | 客户端，随嵌入上传；服务器 SERVER_RECEIVE 读取 | yes | 附件张量的第 0 维（客户端插件按 ctx.data.manifest 逐样本发）。注意 reports.values('num_examples') 是自报样本数而不是嵌入条数，两者不保证一致 |
| `ax2506.22506` | 本轮参与客户端的名单与顺序（排序、并列 tie-break、m 的分母） | 服务器，SERVER_RECEIVE 与 SERVER_AGGREGATE | yes | ctx.uploads.clients / ctx.participants |
| `ax2506.22506` | 逐条 0/1 标记聚成的客户端级异常分 S_k 与标记条数（式 7 / Inference Rule） | 服务器，SERVER_RECEIVE 计算、SERVER_AGGREGATE 使用 | yes | 同一插件挂两个位置，用 ctx.round_state 在一轮内传递（runner 每轮 begin_round 清空）；同时写进 findings.scores/features，别的插件可用 ctx.upstream_feature 读 |
| `ax2506.22506` | 剔除决定（排除谁、保留谁、什么权重） | 服务器，SERVER_AGGREGATE | yes | Decision(excluded/weights/flags) + acts={'select_and_weight'}；宿主 OpenFedLLMGuard.before_aggregate 据此给出 kept 与权重，聚合算术由宿主做 |
| `ax2506.22506` | 上传的 LoRA 更新本身 | 服务器，SERVER_AGGREGATE | yes | ctx.uploads（factor_delta/state）；但本方法的判定不看更新内容，只把它交给宿主聚合——这与论文一致（SABRE-FL 只对嵌入打分），也是它能原样落地的原因 |
| `ax2506.22506` | 跨轮状态（本方法不累积） | 服务器，每轮独立 | yes | 不需要：round_state 每轮由 runner 清空，检测器来自 resources 且不更新，正好对应论文 step 9 |
| `ax2510.16830` | the samples of one training step -- the selection indicator e_t that Eq. (3) counts and the step proof is bound to | client, inside the step, after the forward and before the backward (CLIENT_LOSS) | partly | LossView.sample_ids() gives the row hashes of the current batch, but only under the trainer extension and only for rows the adapter could match (None otherwise); CLIENT_STEP has no batch view at all and no plugin sees or re-derives the sampler's draw |
| `ax2510.16830` | the epoch boundary that the quota gamma of Eq. (3) is defined over | client, between rounds | no | the library knows ctx.round only; there is no epoch notion anywhere, so rounds_per_epoch comes from the defender (the paper is itself inconsistent here: one epoch by default vs 'every 10th epoch is public') |
| `ax2510.16830` | the per-sample attributes the binning matrix M is built from (domain, register, length, policy tags, license id, preprocessing digest) | client, before training (CLIENT_PRE_TRAIN) | partly | DataView.manifest -> SampleRecord(index, hash, source, length): a provenance tag and the length of the hashed text in characters; license_id, proc_digest, policy_tags and register never reach a plugin, and length is characters, not tokens, so Table IV's token ceilings cannot be applied |
| `ax2510.16830` | the local quota commitment (and later the bin-counter disclosure) the client uploads | client CLIENT_POST_TRAIN -> server SERVER_AGGREGATE | partly | findings.messages carries small typed records (MESSAGE_LIMIT_BYTES 65536), so plain counters arrive as a self-report readable through ReportView.messages; no commitment scheme exists, so the server can read the numbers but cannot bind or check them |
| `ax2510.16830` | the step index t and the public seed s from which the public-mode batch is re-derived | client, every step | no | train_trace/TraceView gives per-step scalars recorded after the fact, not the sampler's inputs; no hook or operator re-derives or vetoes a batch, so third-party replay (steps 4-5) has nothing to attach to |
| `ax2510.16830` | the optimizer state (m_t, v_t) and the per-step hyperparameters Eq. (2) binds, schedule included | client, before and after each optimizer step (CLIENT_PRE_STEP / CLIENT_STEP) | no | GradientView exposes gradients and parameter values only; no optimizer-state kind exists; eta appears only as the 'lr' scalar handed to on_step after the step (TraceView.series('lr')) |
| `ax2510.16830` | the activations, per-token logits and per-token loss the circuit arithmetizes | client, each step | partly | LossView gives batch, outputs, loss, per_sample_losses(), gradients_of() (one backward each) and loss_on(); deeper quantities cost ModelHandle passes (hidden/activations/per_sample_gradients) and the client handle may be absent |
| `ax2510.16830` | the frozen backbone tensors, to tie the adapter subspace to public commitments | client and the auditor's side | no | ModelHandle.layout(group, scope='all') gives base-weight names and shapes but never values, and no operator hashes a tensor into a commitment |
| `ax2510.16830` | the leaf/epoch/final proofs travelling from client to aggregator, and the verdict they yield | client upload (CLIENT_POST_TRAIN) -> server receive/aggregate | no | the channel is messages (<= 65536 bytes) and attachments (tensors); a leaf proof is ~220 KB and a final proof ~4.1 MB (Table II) and nothing in the library verifies one, so the verdict enters as the vft_verdicts resource |
| `ax2510.16830` | the committed dataset root c_D, the leaf digests, the counter commitment c_u, the manifest hash h_Pi, h_0 and the frozen-tensor commitments | outside training, before the first round | no | no field/hash/commitment/reference-string operator exists (RunSpec.extra is the only free-form slot and is not meant for proof material); this is defender-side state that only a resource can name |
| `ax2510.16830` | the samples the client is about to train on this round, so that over-quota ones can be masked | client, CLIENT_PRE_TRAIN | yes | DataView.manifest (index, hash, source, length) plus the mask_samples action; ClientGuard.training_samples()/kept_indices()/training_hashes() report the outcome -- this one entry is what the port stands on |
| `ax2603.12089` | 客户端身份签名 Sig 与公钥 Kpub（签名用于派生触发词） | 训练开始前一次；客户端侧 → 服务器侧 | partly | CLIENT_ANNOUNCE + SERVER_EXCHANGE 能传小记录，服务器在 `reports` / `ReportView.messages` 里读；但插件既不能做数字签名也不能算哈希（允许的 import 里没有 hashlib，也没有密钥类 resource），签名必须由宿主或防御方在库外生成。 |
| `ax2603.12089` | 目标模型的 tokenizer / 词表（把签名哈希映射为触发词 token） | 服务器侧，首次下发之前 | no | ModelHandle 没有词表或 token-id 接口，插件也拿不到 tokenizer；触发词只能由防御方在库外选好，作为 `watermark_triggers` 资源传入。 |
| `ax2603.12089` | 服务器本地数据集 D_server（用来构造投毒水印集 D_w） | 服务器侧，首轮之前 | no | `data` 是客户端侧的数据类别，服务器只有 uploads / aggregate / reports；服务器即便作为客户端参与，DataView 也只给样本与 text(index)，没有 text→样本 的逆映射，edit_samples 造不出新的投毒样本。 |
| `ax2603.12089` | 水印嵌入向量 W_w 与被替换下来的原始嵌入行 W_u、W_k | 服务器侧，训练前一次性生成，之后每轮使用 | no | 库里没有任何接口能读或写词嵌入行：ModelHandle.parameters/layout 只给名字与形状，lora() 只装 LoRA 因子，transform_broadcast / replace_global 只搬 LoRA 状态字典；W_w 可以作为 resource 带进来，但装不进模型。 |
| `ax2603.12089` | 待下发的全局模型，以及逐客户端一份的副本 | 服务器侧，每轮下发之前（SERVER_DISTRIBUTE） | partly | OutgoingView.state() / for_client() 与 `transform_broadcast` 提案存在且是逐客户端的，但载体只有 LoRA 状态字典，两行词嵌入的替换搭不上车。 |
| `ax2603.12089` | 客户端本地 PEFT 训练结果（只更新 LoRA，词嵌入不更新、不上传） | 客户端侧，每轮本地训练结束 | yes | `local_update` / ClientUpdate.lora；库本来就只搬 LoRA 因子状态，恰好满足 EmbTracker 对客户端的要求。 |
| `ax2603.12089` | 聚合后的新全局模型 | 服务器侧，每轮 FedAvg 之后（SERVER_POST_AGGREGATE） | yes | AggregateView.result 与 .global_delta()。 |
| `ax2603.12089` | 服务器侧在 D_w 上、以与客户端相同的可训练范围（词嵌入冻结）跑的训练循环 | 服务器侧，每轮聚合之后 | no | 服务器侧没有训练步、没有优化器，也没有任何动作能训练参数；replace_global 只能换一份 LoRA 状态，而 D_w 本身也造不出来（见上一条）。 |
| `ax2603.12089` | 对被审计模型的黑盒查询权限；式 (2) 的碰撞检查还需要每个客户端各自的带水印模型副本 | 论文在训练之外；本移植在每轮聚合之后 | partly | 部署传入 `probe=` 时 SERVER_POST_AGGREGATE 有 `model_handle`，generate / logprob 就是黑盒查询；但库里没有轮外位置，逐客户端副本也因注入侧搬不进来而不存在。 |
| `ax2603.12089` | 每个候选客户端的触发词、目标输出或目标标签，以及 t 条验证样本 | 服务器侧，验证时 | no | 服务器既没有 tokenizer/词表也没有数据集；由防御方作为 `watermark_triggers` 与 `verification_prompts` 资源提供（论文没说 t 条样本从哪来）。 |
| `ax2608.06795` | the adapter under inspection: the list of its LoRA insertion sites and each site's lora_A factors | server side, when an upload arrives (SERVER_RECEIVE) | yes | ctx.uploads.clients and ctx.uploads.state(cid); the site scan must be rewritten because fedguard.views.uploads is not importable from a plugin |
| `ax2608.06795` | per-token A-side bottleneck activations A_m h_{m,t} (Eq 1) for a prompt set, with the adapter loaded | server side, one forward pass per prompt (setup and screening) | partly | ModelHandle.activations(prompts, select=<lora_A submodule>, pool="none", what="output") gives one (tokens, r) tensor per prompt; but the host provides no server-side model (the defender passes one as server_guard(probe=...)), and the reference never states how a state-dict key maps to the submodule names activations matches nor that adapter submodules are visible to it |
| `ax2608.06795` | a small trusted, unlabelled clean prompt set (the paper: 40 prompts from Stanford Alpaca) for mu_m, sigma_m, M_k and tau_k | before or alongside the round, independent of training | yes | resources={"clean_prompts": ...} and ctx.resource("clean_prompts"); the library has no clean-data kind, resources is the intended path |
| `ax2608.06795` | the prompt whose S_k(x) is to be judged (a user query before generation in the paper) | at serving time, before generation: no such stage exists in fedguard | no | no inference stage and no prompt data kind; the port passes a batch in as the resource screen_prompts, which is a bridge, not extraction from the training process |
| `ax2608.06795` | the decision surface for a flagged prompt (refuse it before generation) | in the serving path, between the score and the generation call | no | ACTION_STAGES has no action for a prompt or a generation; mask_samples/edit_samples act on a client's local training samples at CLIENT_PRE_TRAIN, which is a different intervention |
| `ax2608.06795` | the per-adapter calibration artifacts (mu_m, sigma_m, the monitored set M_k, tau_k) kept from setup to use | across rounds, one set per adapter | yes | ctx.state (plugin-private, shared across stages and rounds); findings.scores/features/evidence carry them into the record |
| `ax2608.06795` | an identity for the adapter so that the setup runs once per adapter | server side, per upload and per round | partly | uploads.state(cid) is available to hash, but no library-provided adapter hash reaches a plugin (recorder.store.state_hash is not importable), so the plugin fingerprints (entry count, factor sum) itself |
| `ax2609.37367` | the LoRA adapter each neighbour sent this round (theta^(t+1/2)_j) | server, SERVER_RECEIVE, as the uploads arrive | yes | ctx.uploads.clients / ctx.uploads.state(cid) (also factors(cid, module) and increment(cid, module) for the factor view; this method never needs factor space) |
| `ax2609.37367` | the receiver's own adapter theta_i, the trusted reference both tests compare against | client, CLIENT_POST_TRAIN of the same round (local_update) in the paper; there is no server-side equivalent | partly | no kind carries a server-side own adapter; the port uses ctx.uploads.base_state() (the broadcast global every upload started from). A client-side screening of the peers' adapters is not reachable either: no client stage sees another client's adapter |
| `ax2609.37367` | a runnable model to load an arbitrary LoRA into, generate text from it and score log-probabilities | server, SERVER_RECEIVE (any stage that needs a model) | partly | ctx.model_handle (ModelHandle.lora(state) / generate(prompts, max_new_tokens) / logprob(prompts, targets)); the host gives the server no model by default, so the deployment must pass probe= to OpenFedLLMGuard/GuardStrategy and the shipped HFProbe only implements ProbeView.score |
| `ax2609.37367` | the P fixed Stage 1a probe prompts: the node's held-out probe pool, the trigger word tau_i and the trigger insertion | outside training for the pool itself (160 instruction-response pairs, never shared); assembled in the plugin at the first round and frozen in ctx.state | yes | resources probe_pool and trigger_words read with ctx.resource(), drawn with ctx.rng (no global random state); sampling.subsample for the three demonstrations and ctx.rng.permutation for the shared order. The paper's split of the node's own data into train/probe is outside the plugin (rule 3) |
| `ax2609.37367` | the refusal phrase table (18 lower-cased substrings of Appendix C, ICLSCAN's minus "as an AI") and the two fixed template answers y_ref and y_c | outside training: a constant of the method | partly | resource refusal_phrases; y_ref and y_c are constants in the plugin file because the paper prints them verbatim. The paper's text lists only 3 of the 18 phrases, so the table has to come from the authors' release |
| `ax2609.37367` | generated answers of one adapter on a batch of prompts (P probe answers, H harvest answers a round) | server, SERVER_RECEIVE, inside the lora() context of that adapter | partly | ModelHandle.generate(prompts, max_new_tokens); greedy only, so the Stage 1a nucleus sampling (temperature 0.9, top-p 0.9, top-k 50) and the Stage 1b beam search (width B, length penalty 1, early stopping, top beam only) cannot be asked for |
| `ax2609.37367` | per-token log-probabilities of a candidate string under two contexts, for two different adapters, on identical prompts | server, SERVER_RECEIVE | yes | ModelHandle.logprob(prompts, targets) called inside handle.lora(state), with the same prompt list reused for theta_i and theta_j (Algorithm 5 line 15) |
| `ax2609.37367` | the other receivers R_j of the same adapter, their probe scores s_(k->j) and their candidate-string tables C_(k->j), plus the distance-two neighbourhood of the communication graph | between the receivers of one adapter, once per round, before the accept/reject decision (steps 8 and 11) | no | nothing: in a star an upload has exactly one receiver, so R_j = {server} and there is no peer channel; the message channel (messages/attachments) runs client<->server only, and both of its mechanics (piggyback on the next broadcast, or CLIENT_ANNOUNCE + SERVER_EXCHANGE) are ordered against the training round, not between receivers of the same adapter |
| `ax2609.37367` | the cross-round screening state: which neighbours are due, their consecutive rejections, the W_ej window, the W_re re-check timer, the harvest buffers and the cumulative string-count tables | server, across rounds | yes | ctx.state (private, shared between the two stages and kept across rounds) together with ctx.round; no other storage is needed |
| `ax2609.37367` | the accept/reject outcome applied to this round's aggregation, equally weighted over the accepted adapters | server, SERVER_AGGREGATE | yes | Decision(weights={accepted: 1.0}, excluded=..., flags=...) through the select_and_weight action; the framework does the averaging, so the paper's 1/(/A/+1) rescaling is the framework's normalisation |
| `huang2024antidote` | 微调后模型的权重 w（逐坐标） | 服务器侧，聚合完成、下次下发/部署之前的那个回合 | partly | SERVER_POST_AGGREGATE 的 ctx.aggregate.result 是完整的本轮全局 LoRA 状态字典（所有 lora_A/lora_B 因子）；基座权重取不到数值（ModelHandle.layout/parameters 只给名字与形状，per_sample_gradients 只给梯度），所以可剪对象只有 LoRA 因子，不是论文的稠密权重 w |
| `huang2024antidote` | 每个权重坐标关联的输入激活 A_j(x, w)，x ∈ D_realign | 服务器侧，打分之前，对载入了 w 的模型做一次 D_realign 前向 | partly | ModelHandle.activations(samples, select, pool="none", what="input")：hook 模块本身得到乘 lora_A/base 的 d_in 维输入 x，hook 其 lora_B 子模块得到乘 lora_B 的 r 维瓶颈 h，逐 token、逐样本返回。缺口：库没有"状态字典键 -> 模块名"的映射（适配器会加 base_model.model. 前缀与适配器名），插件按前缀匹配，匹配不上的模块跳过并写进 evidence |
| `huang2024antidote` | D_realign（全部有害 prompt–harmful answer 对，论文默认 2000 条） | 服务器侧，前向之前 | yes | ctx.resource("realign_data")，防御方自备；库按设计不搬运语料，这是规则 3/6 规定的入口。测试里用 3 条合成样本 |
| `huang2024antidote` | 一个载得动 w、可做前向的模型 | 服务器侧，第 1 步 | partly | ModelHandle.lora(result) 在会话内载入本轮聚合 LoRA 并在结束时还原；句柄必须由防御方在服务器端提供（适配器的 probe= 参数），宿主默认没有模型。ProbeView 只有 score()，不够用 |
| `huang2024antidote` | "微调已结束、该部署了"这个时刻 | 服务器侧，进入该回合之前 | partly | 库没有训练结束/部署位置或信号；插件靠构造参数 last_round 或 RunSpec.extra["final_round"] 得知，两者都没有就本轮不动作并写明原因。SERVER_POST_AGGREGATE 是最接近的落点（聚合之后、再下发之前），但它每轮都出现 |
| `huang2024booster` | 对齐 batch (x_t, y_t)：每步 10 条有害提示—安全回答对，取自防御方自己的约 5000 条对齐数据集 | 对齐阶段的一次性训练里的每个优化步，服务器一侧；Algorithm 1 第 2 行 | no | 库唯一的样本视图是客户端的 `data`（KIND_SIDE['data']='client'），取的是本轮该客户端的本地样本；服务器一侧没有任何数据类别。`resources` 只能把资产交给插件，而库没有「在离线对齐训练的优化步里消费它」的位置。 |
| `huang2024booster` | 有害 batch (x'_t, y'_t)：每步 10 条有害提示—有害回答对；第 5、6 行的两次求梯度复用同一批 | 对齐阶段的每个优化步，服务器一侧；Algorithm 1 第 3、5、6 行 | no | 同上：有害数据既不是客户端本地样本，服务器侧也没有数据视图；作为 resource 交进来也没有消费它的位置。 |
| `huang2024booster` | 当前可训练参数 w_t（论文实验里是 LoRA 适配器）：用来构造 w'_t，并保证归一化、扰动与梯度在同一坐标里 | 对齐阶段的每个优化步，参数更新之前；Algorithm 1 第 5–8 行 | partly | 客户端一侧 CLIENT_PRE_STEP 的 `gradients.value(name)` 给出参数本身（detached 只读视图）；`train_trace.lora()` 能在 CLIENT_STEP 取当前 LoRA 的 CPU 拷贝，但 reference 只写明 `on_step(step, scalars, lora=callable)` 由宿主提供该 callable，`on_gradients(step, named_parameters)` 没有这一项，所以 CLIENT_PRE_STEP 能否拿到 state 取决于宿主。服务器一侧默认没有模型，也没有「正在被对齐训练的模型」这个对象。 |
| `huang2024booster` | 对齐损失的梯度 ∇̃f(w_t)（SFT 交叉熵），以及它属于哪一次训练步 | 对齐阶段每个优化步，参数更新之前；Algorithm 1 第 4 行 | partly | CLIENT_PRE_STEP 的 `gradients` 视图正是「宿主当步算出的训练梯度」（`get`/`value`/`flat`/`norm`），但它是客户端本地微调数据上的梯度，不是防御方对齐数据上的梯度；服务器一侧没有训练步。 |
| `huang2024booster` | 有害损失在当前权重处的梯度 ∇̃h(w_t) | 对齐阶段每个优化步的一次额外前向+反向，服务器一侧；Algorithm 1 第 5 行 | partly | `model_handle.per_sample_gradients(samples, group, scope, reduce)` 能对插件自带的样本给出对可训练参数的逐样本梯度（求和即 batch 梯度），`layout()` 给出键与形状；但服务器句柄要防御方自备并传入，而且没有把它接到「对齐训练的优化器」上的运行时。 |
| `huang2024booster` | 临时扰动权重 w'_t = w_t − α·u_t：只用于第二次求值、不持久化，梯度不穿过它 | 对齐阶段每个优化步，第 5 与第 6 行之间；Algorithm 1 第 6 行；式 (2)→(3) | partly | `ModelHandle.lora(state)` 是上下文管理器，可在给定 LoRA 载入下跑一段并在退出时精确恢复，所以「载入一份常数 w'」原则上可表达；但 w' 要由当前 state 算出（见上一条），库既不暴露权重写入，也不保证插件能在同一优化步里把 w' 交给下一次求值。 |
| `huang2024booster` | 有害损失在扰动权重处的梯度 ∇̃h(w_t − α·u_t) | 对齐阶段每个优化步的第二次反向，服务器一侧；Algorithm 1 第 6 行 | partly | 机制上仍是 `with handle.lora(w'): handle.per_sample_gradients(...)`；缺的是同一优化步内把三次反向串起来的位置，以及把结果交给那一步优化器的契约。 |
| `huang2024booster` | 合成梯度 g̃(w_t) = ∇̃f(w_t) + λ·(∇̃h(w_t) − ∇̃h(w'_t))，以及「把它作为本步梯度交给优化器」 | 对齐阶段每个优化步，更新之前；式 (3)、Algorithm 1 第 7 行 | partly | `transform_gradients`（CLIENT_PRE_STEP）是「替换本步梯度」的动作（`proposals={'gradients': {...}}`），单位化与线性组合可用 `ops.states.norm` / `ops.update.scale_to_norm` / `ops.states.add` / `ops.states.delta`；但它替换的是客户端本地微调的梯度，库里没有服务器侧或离线的对齐训练步可以替换。 |
| `huang2024booster` | AdamW 优化器状态与 T≈10000 步（20 epochs × 5000/10）的步循环 | 对齐阶段全程，服务器一侧；Algorithm 1 第 1、8 行 | no | 插件没有优化器；`run` 每个位置每轮只调用一次，`ctx.state` 只跨位置、跨轮保留，`round_state`/`step_state` 在作用域结束时清空，没有 epoch/step 循环或循环控制。 |
| `huang2024booster` | 对齐完成后接种过的检查点 w̃，以及「把它作为服务基础模型」的部署动作 | 对齐阶段结束、任何微调请求之前；Appendix C | no | 没有任何动作把「训练完成的检查点」装成基础模型：`replace_global`（SERVER_POST_AGGREGATE）替换的是本轮聚合出的 LoRA，`transform_broadcast`（SERVER_DISTRIBUTE）只改本轮下发内容，两者都要求插件自己算出那份 state。 |
| `huang2024booster` | （可选变体 Vaccine+Booster）embedding 上的对齐损失梯度 ∇_e f(w)，用于求 ϵ* = ρ·∇_e f/‖∇_e f‖ | 对齐阶段每个优化步、前向之前；Appendix F 式 (6)、Algorithm 2 第 3 行 | no | `ModelHandle` 只给前向结果与对参数的梯度（losses/hidden/activations/per_sample_gradients/logprob/generate），没有对输入 embedding 的反向；`transform_loss` 发生在前向之后，`edit_samples` 改的是文本样本。 |
| `huang2024vaccine` | the per-layer hidden embeddings e_{l,t} of the alignment batch, with their place in the autograd graph | inside the forward pass of an alignment step, server side | partly | ModelHandle.activations(samples, select, pool, what) returns each selected module's input or output, but at pool="none" only for 3-D activations and always .detach()ed, so the tensors are readable and not differentiable; nothing returns them with a graph. |
| `huang2024vaccine` | the gradient of the alignment loss with respect to each layer's hidden embedding, dL/de_l | after the first backward of an alignment step, before the second forward | no | no interface reaches layer outputs. LossView.gradients_of(scalar, select) computes torch.autograd.grad against named_parameters() only, and ModelHandle.per_sample_gradients differentiates per sample against a parameter group (or frozen base weights under scope="all"); a hidden activation is neither. |
| `huang2024vaccine` | a forward pass of the same batch with a perturbation added to each layer's output (f_wl(e) + eps_l) | the second pass of an alignment step | no | ModelHandle has no hook, patch or pre-forward method, and the plugin contract forbids reaching past the handle. The trainer extension states the same limit from the other side ("What stays out of reach: the forward pass itself ... intermediate activations"); its transform_loss action replaces the loss scalar after the pass, which cannot change what the pass computed. loss_on(batch)/losses(samples) run the model's own forward on samples and accept no activations. |
| `huang2024vaccine` | the alignment mini-batch (x_t, y_t) of the provider's own corpus | every alignment optimization step, before the first forward | partly | LossView.loss_on(batch) and HFModelHandle accept a batch in the trainer's format, and hf_trainer_ext.collate_texts builds one from texts, so a defender-supplied corpus can be turned into a batch. But this only reaches the loss, i.e. the same forward-pass limit as above; and the paper's placement is pre-deployment, before any user data or client exists, so no client-side ALIGNMENT batch exists unless one declares the federation step itself to be the alignment. |
| `huang2024vaccine` | the global cross-layer gradient norm //concat_l dL/de_l// | between the first backward and the perturbation construction | no | follows from dL/de_l: with no per-layer gradients there is nothing to concatenate. Note the normalization is over all layers at once; a per-layer norm would be a different (and wrong) method. |
| `huang2024vaccine` | an optimizer step driven by the gradient of the perturbed pass | the alignment step's update | no | the host owns the optimizer; fedguard's only gradient point is CLIENT_PRE_STEP ('gradients are computed, the optimizer has not stepped'), which can replace a gradient but cannot supply one produced by a second, differently-corrupted forward pass. |
| `huang2024vaccine` | the trainable LoRA factors the alignment updates, and their merge into the base model | end of alignment, before distribution | partly | states.* and the LoRA state dicts are the library's normal currency, and SERVER_DISTRIBUTE/outgoing carry the model that is sent; the merge itself is a training-run operation, not a per-round intervention. |
| `inan2023llamaguard` | the content to judge (a user prompt or an agent response) | client side, before local training, at CLIENT_PRE_TRAIN | partly | `data` gives DataView.samples() and DataView.text(i), so the local training text is reachable; the text of the model's own generation is not reachable anywhere (see the entry on generations), and the server never sees text at all |
| `inan2023llamaguard` | a forward pass of the guard classifier over the assembled prompt | client side, CLIENT_PRE_TRAIN | yes | `model_handle`; ModelHandle.logprob(prompts, targets) for the two verdict tokens and ModelHandle.generate(prompts, max_new_tokens) for the emitted category list. The handle must wrap the guard model: ClientGuard.begin_round/pre_train take model_handle=, and fedguard.adapters.hosts treats model_handle as a glue kind on the client |
| `inan2023llamaguard` | the probability of the first token the guard model would generate | client side, at the scoring call | partly | ModelHandle.logprob returns the MEAN per-token log-probability of a target. For a one-token target that is exactly the first token's log-probability (the paper states safe and unsafe are single tokens in its SentencePiece tokenizer); it is a mean over the target's tokens for any longer target, and no method returns the raw first-token distribution |
| `inan2023llamaguard` | the safety taxonomy: numbered categories with plain-text guidelines | not from the run; a defender asset carried into the plugin | partly | `resources={'taxonomy'}`, read with ctx.resource('taxonomy'); the paper's own six categories and its guideline wording are not in the extracted text, so they are an input and not a value baked into the plugin |
| `inan2023llamaguard` | the 2 to 4 in-context examples per category that Section 3.2 puts in the prompt | not from the run; a defender asset | partly | the `examples` key of the same resource, used only in mode='few_shot'; how they are selected and ordered is left open by the paper |
| `inan2023llamaguard` | whether the content is a user turn or an agent turn (the type of classification) | plugin configuration | yes | a constructor argument, `task`; the library itself has no notion of turn roles, DataView.text(i) is one opaque string per sample |
| `inan2023llamaguard` | the identity of each local sample, so that a sample judged unsafe can be taken out of the round | client side, CLIENT_PRE_TRAIN | yes | DataView.manifest gives a hash, a source tag and a length per sample; the proposal goes out as findings.proposals['mask'] and is applied as `mask_samples`, which ClientGuard.kept_indices()/training_samples() then reflect |
| `inan2023llamaguard` | conversation structure and turn boundaries, to judge multi-turn content and to pack it to 4096 tokens | client side, wherever the samples are read | no | DataView.text(i) returns one string per sample and the manifest records only a hash, a source tag and a length; nothing marks turns, so a multi-turn conversation cannot be reconstructed or truncated the way the paper's inputs are |
| `inan2023llamaguard` | the encoded text of the model's own generation, for the output half of the guardrail | anywhere in a round | no | no stage carries generated text: LossView at CLIENT_LOSS holds output tensors, the batch and sample hashes and never text, and there is no detokenization path; ModelHandle.generate can turn a prompt into text, but that needs a second model while a plugin gets one handle of its side |
| `inan2023llamaguard` | labelled content to calibrate the decision threshold (the AUPRC and per-use-case threshold work of Section 4.3.3) | no position; outside the run | no | the library has no evaluation or calibration position; the threshold is a constructor parameter and any calibration happens outside the record |
| `inan2023llamaguard` | the fine-tuning data of the guard model itself (Anthropic harmlessness prompts, cooperating and refusing responses, red-team labels, index shuffling, the two augmentations) | outside the plugin, by rule 3 | no | the plugin carries no training loop; the trained guard arrives behind the model handle |
| `rieger2022deepsight` | 输出层偏置向量 b(G_t) 与每个上传的 b(W_{t,k})（步骤 1、2 的输入，也是式 (7) 的第一项） | 服务器侧，SERVER_RECEIVE / SERVER_AGGREGATE，收到全部更新之后 | no | LoRA 上传里没有偏置：ClientUpdate.lora 只有 lora_A/lora_B，UploadView.state/factors/base_state 都没有 bias 项；服务器默认也没有基座模型（model_handle 由防御方自备，且该协议也不暴露偏置）。这一步在任何 LoRA 部署里都取不到，不是参数问题 |
| `rieger2022deepsight` | 输出层（readout 模块）的权重增量 ΔW_{t,k} = W_{t,k} - W_{G_t} | 服务器侧，SERVER_RECEIVE | partly | UploadView.increment(cid, module) 给出 LowRank 形式的 B_kA_k - B_gA_g，精确且不物化；但仅当该模块被 LoRA 适配时它才出现在 UploadView.modules 里。常规 LoRA 目标是注意力/MLP 投影，输出头通常不被适配，此时只能 skipped |
| `rieger2022deepsight` | 输出类别数 P（式 10 的 1/P） | 服务器侧，SERVER_RECEIVE | yes | UploadView.factors(cid, readout)[1].shape[0]，即该模块 lora_B 的行数。论文没说服务器怎么获知 P（架构是否公开），这里从形状读出来 |
| `rieger2022deepsight` | 3 个种子各 20000 条、input_dim 维的随机输入向量（步骤 6） | 服务器侧，SERVER_RECEIVE / SERVER_AGGREGATE | no | 没有算子能对任意输入向量做前向。ModelHandle 的方法都只接受 samples（adapter 负责分词/取特征），服务器也默认没有模型；即使防御方按 harness.server_guard(..., probe=...) 自备句柄，也喂不进 input_dim 维随机向量。input_dim 本身在 RunSpec / ModelHandle 里都没有 |
| `rieger2022deepsight` | 每个模型在探针上的输出层概率 f(s_m; W) 与全局模型的 f(s_m; G_t)（步骤 7，式 6） | 服务器侧，SERVER_RECEIVE / SERVER_AGGREGATE | no | ModelHandle.activations(select=<输出模块名>, what='output', pool='none') 能拿到子模块输出（logits），但要先 softmax 才成概率，且论文要求的是“输出层概率”这一层语义；ProbeView.score(lora) 只返回命名标量字典，没有 P 维向量。DDif 因此整条缺失 |
| `rieger2022deepsight` | 本轮全局模型 G_t | 服务器侧，SERVER_RECEIVE（UploadView.base_state()）与 SERVER_POST_AGGREGATE（AggregateView.base/result） | yes | UploadView.base_state()、AggregateView.base / AggregateView.global_delta() |
| `rieger2022deepsight` | 本轮收到的全部单条明文更新（步骤 8–13 都要） | 服务器侧，SERVER_RECEIVE 与 SERVER_AGGREGATE | yes | ctx.uploads（UploadView.clients/factors/state/increment）。安全聚合下宿主把 uploads 放进 RunSpec.unavailable，契约会在第一轮之前直接拒绝该插件（论文 §IX 也承认 DeepSight 与安全聚合不兼容） |
| `rieger2022deepsight` | 每条更新的 L2 范数，用来取中位数 S（步骤 13，式 12） | 服务器侧，SERVER_RECEIVE | yes | states.norm(states.delta(UploadView.state(cid), UploadView.base_state()))，等价于 UploadView.factor_delta(cid).norm()；裁剪用 update.clip_to_norm(state, base, S) |
| `rieger2022deepsight` | 本轮的最终簇划分（步骤 12 的整簇投票要） | 服务器侧，轮内 SERVER_RECEIVE → SERVER_AGGREGATE | yes | 插件自己算，用 ctx.state 在轮内两个位置之间传（不需要库外状态，也不需要跨轮状态：论文明确只看当前轮） |
| `rieger2022deepsight` | HDBSCAN（步骤 8、11） | 服务器侧，SERVER_RECEIVE | partly | ops.cluster.density_clusters（库自述是“论文没给 HDBSCAN 参数时的替身”，DBSCAN+数据驱动 eps）；ops.cluster.dbscan 可以自己给 eps；精确 sklearn HDBSCAN 只在 majority_cluster 内部、且只留一个多数簇，不符合 Alg. 2 需要多簇+噪声点的形状 |
| `rieger2022deepsight` | “最后一轮”这个事实，以及按簇分别聚合、按簇下发（步骤 15，§V-C） | 聚合发生在 SERVER_POST_AGGREGATE（那里有 ctx.uploads 和 ctx.aggregate），下发发生在下一轮 SERVER_DISTRIBUTE（那里有 outgoing 和 transform_broadcast） | partly | 两端的素材都在：SERVER_POST_AGGREGATE 能读到全部 uploads 自己算簇均值，SERVER_DISTRIBUTE 能用 transform_broadcast 给每个客户端不同的 LoRA。缺的是触发条件——StageContext/RunSpec 里没有总轮数或“本轮是最后一轮”的信号，也没有训练结束后的收尾阶段（OpenFedLLMGuard.finish 不跑插件），所以只能整段不做 |
| `rieger2022deepsight` | 缩放不变性（定理 1、2 与 App. H 的前提） | 不额外取数 | yes | NEUP 逐模型归一化、余弦与 A/B 的整体缩放无关，因此判定对更新整体缩放不变；测试里把同一情形放大 25 倍验证判定不变 |
| `rieger2022deepsight` | 本轮客户端集合 N（不抽样，遍历全部） | 服务器侧，两个位置都有 | yes | ctx.uploads.clients / ctx.participants |
| `rosati2024repnoise` | a mount point after aggregation and before the next broadcast, where the released global model can still be changed | server, once per round, after the aggregate is formed (this port maps the pre-release step of the paper there) | yes | Stage.SERVER_POST_AGGREGATE; ACTION_STAGES allows replace_global at it and AggregateView.result is the new global LoRA. |
| `rosati2024repnoise` | a runnable model on the server for the immunization forwards and backwards | server, at every immunization step | yes | the `model_handle` data kind. The host supplies none, so the defender passes one to the adapter (`OpenFedLLMGuard(..., probe=<HFModelHandle>)`); the plugin declares `model_handle` and the runner hands it in at SERVER_DISTRIBUTE, SERVER_RECEIVE, SERVER_AGGREGATE and SERVER_POST_AGGREGATE. On the Flower profile the kind is server-unavailable unless the app supplies a handle. A full handle is needed: the narrow HFProbe can only score a LoRA. |
| `rosati2024repnoise` | the paired refusal batch (b_harmless, b_harmful) for the same harmful questions, as token ids with labels | server, at the start of every immunization step | partly | no view carries a defender batch on the server; the corpus can only arrive as a `resources` asset, which the runner passes as an opaque value. ModelHandle.losses(samples) would consume it, but forward only, with the loss of the model through its final head and no graph; there is no server-side loss view and no collated batch in the trainer format that loss_on() could take. |
| `rosati2024repnoise` | the shared-token mask (intersection of b_harmless and b_harmful) of each pair | server, before the two forwards of a step | partly | ModelHandle.tokens(samples) returns the tokens of each sample, so the intersection is computable inside the plugin; but the mask exists to suppress positions in the layer-wise ascent and noise terms, and neither term has a runtime, so there is nothing for it to act on. |
| `rosati2024repnoise` | the post-MLP pre-residual activation of every layer, shape (B, T, d), with the autograd graph | inside the harmful forward of every immunization step | partly | ModelHandle.activations(samples, select=<MLP modules>, pool=none, what=output) captures the output of the MLP, which is exactly the position the paper asks for; HFModelHandle stores what its hook sees as .detach() and pools it onto the CPU, so the values are readable and not differentiable. ModelHandle.hidden(layer) returns the post-residual state that the paper rejects. |
| `rosati2024repnoise` | the layer-wise language-model loss l_ascent^l = L(LMHead(a_l), b_harmful), and the log of its layer mean | after the activation capture, per layer, every step | no | no interface applies a module to a tensor: ModelHandle.losses, logprob and generate all run the forward of the model itself through its final head on samples; LossView.outputs.logits is the final head of the host and is client-side only; parameters() and layout() return names and shapes, never weights. |
| `rosati2024repnoise` | the noise term of every layer, MMD(a_l, N(0,I)), as a differentiable scalar | per layer, every step | no | no MMD operator exists (see missing_ops), and the only server-side activation interface returns detached CPU tensors, so a term built on it cannot reach the model. The one differentiable activation path in the library is LossView.outputs.hidden_states on the client, and only when the app ran its forward with output_hidden_states: it is post-residual (the position the paper rejects), it sits inside the training step of the attacker, and it carries no language-model head. |
| `rosati2024repnoise` | the gradient of the composed loss l_all with respect to the weights of the model (every layer and the head) | after the composition, before the optimizer step | no | no interface takes a scalar built by a plugin on the server. ModelHandle.per_sample_gradients differentiates the per-sample LM loss of the model itself, one sample at a time, against a named parameter group; LossView.gradients_of differentiates a scalar built by a plugin but only against the trainable parameters of the host, on the client, where the batch is the batch of the client itself and not the pairs of the defender. |
| `rosati2024repnoise` | an optimizer step on the server model per immunization step (Adam, cosine schedule with 10% warmup, 1 epoch over the pairs) | step 10 of the extraction, repeated over the corpus | no | the server side owns no training loop and a plugin owns no optimizer; replace_global substitutes a state after the fact. On the client the optimizer of the host is the only stepper, one step per host batch, and a plugin cannot change the learning-rate schedule, the number of steps or the next batch. |
| `rosati2024repnoise` | standard Gaussian noise with the shape of an activation | step 5, per layer, per step | yes | ctx.rng, a numpy Generator seeded per plugin and round by the runner, with the global RNGs restored afterwards; the tensor is one torch call away from it. No library operator is needed. |
| `rosati2024repnoise` | the immunized checkpoint as the object that continues the run | step 11, before the next broadcast | partly | replace_global at SERVER_POST_AGGREGATE would carry it, but the runner validates the replacement against aggregate.result key by key and shape by shape, so it must be a LoRA state dict; the artifact of the paper is the full model, its ablation says that freezing the first ten layers ruins the defense, and base weights never reach a plugin as tensors. |
| `shen2024seal` | 本轮该客户端将用于本地训练的样本，以及每条样本的身份（顺序、hash、来源、长度） | 客户端，CLIENT_PRE_TRAIN，本地训练开始之前 | yes | ctx.data（DataView）；DataView.manifest 给 index/hash/source/length，hash 是样本文本的 SHA-256；插件用它排名并 mask |
| `shen2024seal` | 每条样本的选择器分数 σ_i(ω_K)，S3 的排序键 | 库外 S2 产出；在 CLIENT_PRE_TRAIN 被查询 | partly | 训练过程里没有产出它的位置（没有 D_safe、没有 ω、没有打分用的前向）；按规则 3 由防守方以 resources['selector_scores']（hash → σ）接入，插件只查表 |
| `shen2024seal` | 样本身份与离线数据集 D 的对应关系（论文按 z_i 在 D 中的位置排名） | S2 训练与 S3 打分之间，以及离线 D 与客户端本地分片之间 | partly | DataView.manifest 的文本 hash 可作稳定键（Section 4.4 说明选择器绑定数据集而非模型），但库不提供数据集版本号或离线索引，'D 中的位置'只能换成'文本 hash' |
| `shen2024seal` | 训练步内每条样本的长度归一化 NLL ℓ(θ_k; z_j)，并知道它属于哪条样本（公式 (8) 的 ω 更新） | 客户端，CLIENT_LOSS（前向之后、反向之前） | partly | LossView.per_sample_losses() 给批内逐样本损失（对已标注 token 平均，不是论文的响应长度归一化口径）；LossView.sample_ids() 给每行的样本 hash（需要部署用 extend_trainer(identify=identify_from_dataset(train_dataset, guard.training_hashes())) 接上，否则抛 LookupError）。两者都只在 CLIENT_LOSS 存在 |
| `shen2024seal` | 与 z_j 配对的 D_safe 样本 z_i^safe 以及同一迭代的 ℓ(θ; z_i^safe) | S2 每个迭代（若要在轮内表达，就是客户端的训练步） | no | 客户端只有一份 data kind，没有配对调度；LossView.loss_on(batch) 只前向宿主格式（已 tokenized）的 batch，插件拿不到 tokenizer，造不出 D_safe 的 batch |
| `shen2024seal` | θ 的惩罚混合更新 (1−γ_k)∇ℓ(θ_k;z_i^safe) + γ_k σ_j(ω_k)∇ℓ(θ_k;z_j) 与步长 β_k（公式 (4)） | S2 每个迭代，客户端训练步内 | partly | transform_loss（LossView.gradients_of 可对插件自造的标量求梯度）与 transform_gradients 可以替换这一步的损失与梯度；但插件不能挑数据、不能设优化器/步长/γ 调度，也补不上上面缺的安全损失项 |
| `shen2024seal` | 与被训模型同尺寸的第二份参数 θ̂ 及其梯度（公式 (6)，Algorithm 1） | S2（Algorithm 1） | no | ModelHandle 只包着被训练的那个模型（handle.lora 换 LoRA，parameters/layout 看参数），没有第二份参数，也没有步进参数的方法；服务器侧句柄是可选的防守方 probe，同样给不出 θ̂ |
| `shen2024seal` | ω 的逐坐标更新所属的 S2 循环：K 个迭代、每 iteration 的配对采样、γ 的每 epoch 调度、ω 的优化器 | S2（论文把它写成一次性离线工作） | no | 十个 stage 全在一轮训练之内，setup(spec) 只收到 RunSpec；插件不拥有循环：不能决定下一步用哪条数据、不能步进参数、不能决定迭代数；mask_samples 只在 CLIENT_PRE_TRAIN 生效一次，本轮后续 step 无法随 ω 改变选择 |
| `shen2024seal` | 在完整 D 上一次性打分并取全局 top p%（S3 的字面语义） | 训练之外，集中式（论文自己标为 outside_training） | no | KIND_SIDE 把 data 归给 client，样本文本不出客户端；服务端只有 uploads/reports/messages，没有跨客户端的数据视图。只能退化为每客户端每轮各自截断 |
| `shen2024seal` | 选择是否真的生效、哪些样本被丢弃 | 客户端，CLIENT_PRE_TRAIN 之后、本地训练之前 | yes | mask_samples 动作 + ClientGuard.kept_indices()/training_samples()/training_hashes()；记录里只有 hash，没有原文 |
| `tamirisa2024tar` | 未加防护的基础模型权重 θ 与初始防护后的 θ_G0（全参数，论文为 Llama-3-8B-Instruct） | 训练之外、发布前；一轮内最近的表面是 SERVER_DISTRIBUTE 的 outgoing | no | STAGE_KINDS 的每个位置只承载 LoRA 状态字典：outgoing、aggregate、uploads 与 base 引用都是 PEFT 状态（<module>.lora_A.weight / lora_B.weight）。没有基座权重的数据类别；ModelHandle.parameters(scope=all) 只在防御方自备句柄时列出基座参数名，拿不到值，也不能写回。缺的是基座权重的读与写。 |
| `tamirisa2024tar` | 内层 K=64 步 SFT 攻击轨迹的参数坐标（每个坐标是一份可评估的模型状态） | 训练之外，防御方自己的优化器循环里 | no | 插件在每个位置只被调用一次，不拥有训练循环：没有位置让插件选择攻击数据、推进自己的优化器或在坐标之间切换模型参数；CLIENT_STEP 只观察宿主自己的那一步。 |
| `tamirisa2024tar` | 留出的安全探针批次 x_TR（每个外层步一个 minibatch，该步所有内层 L_TR 复用同一批） | 外层步开始时，防御方侧 | partly | 样本可以作为 resource 传入，DataView 也能给客户端本地样本；但 KIND_SIDE 把 data 划给 client，服务端任何位置都没有数据类别，一轮里也没有第二个（防御方自己的）批次的入口。 |
| `tamirisa2024tar` | retain 批次 x_r 与初始防护模型在其上的 residual stream 激活 h_{θ_G0}(x_r) | retain 项的前向，防御方侧 | no | ModelHandle.hidden(samples, layer, pool) 能取某一层的状态，但返回 CPU 上 detach 的张量，且只针对句柄包着的那一个模型；没有第二个（参考）模型的句柄类别，也没有可微激活。 |
| `tamirisa2024tar` | 以层输出为变量的可微锚定项 ‖h_{θ_{i-1}}(x_r) − h_{θ_G0}(x_r)‖²（式 2 第二项） | retain 项的损失里 | no | LossView 的图只到 named_parameters()（gradients_of、per_sample_losses、loss_on）；没有以隐藏状态为变量的损失面，也没有第二个模型的激活。 |
| `tamirisa2024tar` | 可微的 L_TR：武器化设置里在攻击坐标上求值的输出分布熵；拒绝设置里 chosen(refusal)/rejected(harmful) 对的 DPO 损失 | 每个子采样坐标的一次前向加反传 | no | 见 missing_ops；ModelHandle.logprob 返回 float 列表（无图），ProbeView.score 只给 LoRA 打分，LossView 只覆盖宿主当前这一步的损失。 |
| `tamirisa2024tar` | 直线估计器意义下的元梯度 ∇_{θ_{i-1}} L_TR(attack(θ_{i-1}), x_TR)，以及沿子采样坐标累积的 g_TR | 外层更新的梯度 | no | 没有算子或运行时把内层优化做成可微函数；库的动作只搬运 LoRA 状态或替换宿主当前步的梯度（transform_gradients 作用于本步的 .grad 缓冲）。 |
| `tamirisa2024tar` | 把加权外层更新 θ_i ← θ_{i-1} − η(λ_TR·g_TR + λ_retain·g_retain) 落到基座权重上 | 外层步结束，发布前 | no | ACTION_STAGES 里所有模型形状的动作（transform_broadcast、transform_received、transform_update、replace_global）传的都是 PEFT 状态字典；ctx.state 能跨轮保存 Python 对象，但库不会步进任何优化器。 |
| `tamirisa2024tar` | 外层优化器状态（ScheduleFree AdamW，η=2e-5 或 6e-5，N=750 或 100 步）与内层每次外层迭代重建的优化器 | 外层循环，训练之外 | no | 没有任何位置或动作承载优化器；轮的边界是联邦的轮，不是 TAR 的 N 个外层步；论文还要求把外层优化器搬到 CPU 以免与内层优化器冲突。 |
| `tamirisa2024tar` | 训练期对手集合 A_train 的采样（数据、AdamW、学习率网格、No Warmup、batch 64、全参数、K=64，以及 β(6.0, 3.0) 的 R→F 切换） | 每个外层步的内层循环 | no | 配置本身可以作为 resource（防御方自备），但没有任何运行时能执行它（见 missing_runtime）；学习率采样本可用 ctx.rng。 |
| `tamirisa2024tar` | （拒绝设置）在 Anthropic-HH-RLHF 全量上预计算的参考模型 DPO log-prob 与改写后的 chosen/rejected 划分 | 训练前，防御方侧 | partly | 可以作为 resource 传入（形式由防御方决定），但把 log-prob 变成可微 DPO 项的算子不存在（见 missing_ops）。 |
| `xie2024gradsafe` | 待筛的提示文本（客户端本轮本地数据） | 客户端，CLIENT_PRE_TRAIN，本地训练开始前 | yes | ctx.data（DataView.samples()/text(i)/manifest），声明 needs={'data'} |
| `xie2024gradsafe` | （prompt, 顺从回复）配对的损失对冻结基座权重矩阵的梯度 | 客户端，CLIENT_PRE_TRAIN，每条提示一次反向 | partly | ctx.model_handle.per_sample_gradients(samples, 谓词, scope='all', reduce=...) 能取到基座权重的逐样本梯度；但库无法描述一个 (prompt, response) 对、也无法把损失限制在回复 token 上，插件只能把配对拼成一条文本交给句柄，由句柄自己的训练损失决定梯度。按 token 段取损失只有训练步内的 LossView（loss_on/gradients_of），而它只看到宿主自己的 batch。 |
| `xie2024gradsafe` | 可反传的对齐基座 LLM 本身（论文用 Llama-2-7b-chat-hf） | 客户端：句柄包着正在训练的模型，scope='all' 可达冻结基座；服务器：宿主默认不提供模型 | partly | model_handle；库既不提供基座模型也不校验它是否对齐（Table 7 显示方法依赖对齐）。服务器侧即使自备句柄也拿不到提示文本。 |
| `xie2024gradsafe` | 被判定样本的身份，用于把它从本轮训练里删掉 | 客户端，CLIENT_PRE_TRAIN | yes | ctx.data.manifest[i].hash + proposals={'mask': [...]}（动作 mask_samples） |
| `xie2024gradsafe` | GradSafe-Adapt 需要的目标域带标签提示（用来拟合逻辑回归探针） | 训练之外；联邦里标签在客户端手里 | no | 库里没有拟合阶段，也没有标签汇聚的通道；只能在库外拟合后以资源 `probe` 传入（规则 3）。论文也没写联邦下标签怎么汇。 |
| `xie2024gradsafe` | 安全关键切片集合 S 与不安全梯度参考（不是从训练里取，是离线产物） | 训练之外、开跑之前，防御方一侧（论文 3.2 节的一次性离线准备） | yes（作为资源） | 资源 `unsafe_reference`；库里没有“轮次之外且能拿到 model_handle”的位置，所以步骤 4–6 放不进插件，只能离线算好传入。 |

## 要在库外维护或准备的状态

- `ax2103.05633`：每个客户端的本地训练数据副本（resource client_data）：服务器侧要按样本哈希取回批次才能重执行，这是本移植最重的外部前提，也与联邦学习的隐私前提冲突。
- `ax2103.05633`：公开已知初始化策略及其逐键分布参数（resource init_spec），以及 prover 声称的策略名（插件构造参数）。
- `ax2103.05633`：标定好的松弛阈值 δ 与验证预算 Q（插件构造参数；论文只给标定方法）。
- `ax2103.05633`：每轮步数 S / epoch 长度（插件构造参数，并随证明发布）。
- `ax2103.05633`：验证者的密钥对、prover 公钥、时间戳或公开账本（未实现，属密码学协议）。
- `ax2103.05633`：已验证明的数据库 P_0..P_R（未实现；联邦版用广播基座相等替代）。
- `ax2103.05633`：δ 标定所需的 d_ref（两个独立训练的同架构模型之间的距离，一次性离线测量，库外）。
- `ax2104.13230`：干净预训练集 D_pre（样本+标签）：本移植作为 resource 传入；slab 的类质心/阈值与式 (7) 的参考梯度都由它算。
- `ax2104.13230`：论文的初始模型 θ0：在这里就是客户端收到的全局 LoRA（宿主提供，插件只经 model_handle 使用）。
- `ax2104.13230`：类质心、slab 阈值、参考逐样本梯度 / Fisher：论文写成训练前一次性预计算；本移植每轮现算，若要离线预算就要在库外保存这些量。
- `ax2104.13230`：影响滑动窗口：方法唯一的跨时刻状态；本移植放在 ctx.state，否则要在库外维护。
- `ax2104.13230`：一个能在客户端做逐样本反向的 model_handle（可以就是正在训练的模型）。
- `ax2210.07714`：每个客户端的本地验证数据及其标签来源（label_of 背后的数据管线）；论文默认每客户端 2560 条本地样本
- `ax2210.07714`：客户端侧模型句柄（包着正在训练的模型，由宿主/适配器提供）；服务器侧不需要模型
- `ax2210.07714`：服务器插件在 ctx.state 里保存的两代 pack 索引，以及进入通道的整轮 LoRA 状态张量（与论文服务器飞地内持有 {Lt_1..Lt_n} 对应）
- `ax2210.07714`：TEE 与远程认证基础设施（S1）、加密上传与相互认证（S2）：库不建模，只能留在库外
- `ax2210.07714`：验证样本的规模/采样策略：本移植用本地全量样本，没有实现 Sect. VI-C 提到的代表性子集
- `ax2301.09508`：每客户端状态 (c_i, H_i)：c_i 首次出现时抽一次、此后每轮加 l；H_i 是 l 维基测度位置向量，跨轮保留，是本方法最占内存的一项
- `ax2301.09508`：簇表 (mu_cl, scale_cl, n_k, tau_k)：论文不设簇数上限、也没有合并或遗忘规则，n_oc 只增不减（合成 4 轮实验里从 0 涨到 17）
- `ax2301.09508`：基线统计 (mu_p, sigma_p)，由 G^0 一次性算出后固定
- `ax2301.09508`：本轮 Max_JD 数组，每轮重建（论文 Alg. 1 第 3 行）
- `ax2301.09508`：没有 resources：方法不需要干净数据、探针、预训练检测器或参考更新；唯一的外部输入是本轮全局模型，而它由 FL 训练本身产生
- `ax2305.05506`：the assignment matrix A (BCH code of length 15 with 8 redundant bits for n = 15; (30, 18) cyclic code for n = 30), its group membership and n_m^max
- `ax2305.05506`：the offline design toolchain: the Eq. (3) enumeration or Monte Carlo, the exact or sampled Pr(Z | N_m) of Eq. (11), and the Eq. (15) Monte Carlo search for Delta-hat(n_m)
- `ax2305.05506`：the server-side validation quasi-dataset (100 samples in the paper) with its candidate completions and, for a targeted attack, the marks of the attacked source label
- `ax2305.05506`：a runnable server-side model and the model handle that loads a candidate LoRA and scores candidates (the host supplies none)
- `ax2305.05506`：the secure aggregation implementation of the host, including how one protocol instance produces m overlapping group aggregates
- `ax2305.05506`：the task model and the client data partition, which FedGT does not change
- `ax2402.12168`：中毒的第三方预训练权重 θ_p（PSIM 与 victim model 的共同初始化）
- `ax2402.12168`：带标签的干净训练集 D_clean^train 及其重置标签副本 D_clean_reset^train
- `ax2402.12168`：训练好的 PSIM 模块 θ_p^psim（论文主配置为 P-tuning v1 的 virtual token；消融里也用过 LoRA r=8 / dropout=0.1）
- `ax2402.12168`：阈值 γ（论文按模型取 0.7 或 0.75）与置信度定义 C 的选择
- `ax2402.12168`：victim model 本身（对判为干净的样本给出预测 y）
- `ax2409.14119`：Clean downstream training set (paper: about 6,000 samples per task) and the labelled clean validation set used to pick lambda_amp / lambda_reg; both stay with the defender
- `ax2409.14119`：The possibly backdoored pretrained PLM checkpoint plus the PEFT configuration (LoRA r/alpha; the paper also uses adapter and prefix-tuning) - model construction, outside the library
- `ax2409.14119`：The selected coefficient lambda_amp, passed into the constructor; the plugin itself carries no state across steps or rounds
- `ax2410.14425`：the clean small teacher f_t (BERT-110M or GPT-2-124M) after full-parameter fine-tuning on D_clean_train, including its dimension-alignment layer g (W: d_s x d_t, b: d_s) and a forward that returns logits and final hidden states -- prepared offline, outside the library
- `ax2410.14425`：the clean labelled training set D_clean_train with its batching, tokenization and how teacher and student inputs are paired across two tokenizers (the paper never says how)
- `ax2410.14425`：the poisoned student as a full white-box model including its base weights: the server side here holds LoRA state dicts, so base-weight poisoning has no representation at all
- `ax2410.14425`：the unlearning run's own state (AdamW moments, epoch and batch cursor, RNG) for the single 5-epoch pass; the paper accumulates nothing across rounds, so there is no cross-round state to carry
- `ax2411.17453`：The trained meta-classifier itself (resource `classifier`): one callable F_input -> P(backdoored) fitted offline. It is the trained network of Eq. (12), and the plugin cannot detect anything without it.
- `ax2411.17453`：PADBench, or an equivalent labelled adapter set: 250 benign + 250 backdoored adapters per dataset x attack x PEFT method x model configuration, 13,300 adapters in total (Section 1.1, Table 15), split 8:2 with 10% of D_train held out for validation (Section 5.3.2), plus the base LLMs and the PEFT fine-tuning compute that produces them.
- `ax2411.17453`：One classifier per input shape: base model, target-module set, block count and (d_out, d_in) all fix F_input, and the paper states that any variation in input dimensions requires training a new classifier (Section 7). The plugin's roles/threshold/space settings are the deployment side of that.
- `ax2411.17453`：Optional, for zero-shot transfer to unseen attacks (steps 9-10): three classifiers trained on three different attack datasets and their parameter average; the paper does not give the averaging weights or the contrastive temperature.
- `ax2411.17453`：Optional, for the mitigation the paper evaluates (step 11): Fine-mixing needs clean pre-trained weights and 2,500 clean sentences per class. It is a third-party method, not part of PEFTGuard, and is out of scope here.
- `ax2506.22506`：离线训练好的二分类检测器 D（论文：两层 MLP 512→128→2、ReLU、BCE、Adam 1e-3、20 epoch、batch 64、几 MB），以 resources['detector'] 传入；需是可调用对象 (n,d)→(n,2) logits，eval 模式，dtype 与嵌入一致
- `ax2506.22506`：辅助数据集 Caltech-101（9146 张、与联邦训练集不相交）与触发器注入流程 x* = x ⊕ t（论文未给子集大小/比例、D_aux 总条数、触发器来源与优化）
- `ax2506.22506`：冻结的 CLIP ViT-B/16 图像编码器与论文所说的 a fixed prompt learner（论文没说是哪一个），客户端每轮编码本地图像用
- `ax2506.22506`：每个客户端本地样本的嵌入表（上面编码器的输出，按样本 hash 索引），以 resources['embeddings'] 传入；库外维护，随本地数据变化更新
- `ax2506.22506`：m 的取值（每轮恶意客户端数上界）；论文只给默认比例 25% 与 0/25/50/100% 的消融，没有绝对值
- `ax2506.22506`：（方法依赖但不属于插件）宿主框架的联邦提示学习循环：冻结图像/文本编码器、只训练 prompt、恶意客户端在本地注入触发器并重标目标类
- `ax2510.16830`：the VFT prover/verifier stack (SNARK over p ~ 2^255 with a Poseidon/Rescue sponge, cycle of curves or STARK folding, KZG SRS) and the per-client verdicts it produces -- resource `vft_verdicts`
- `ax2510.16830`：the bin ceilings gamma of Eq. (3) at the granularity a plugin can see -- resource `quota`
- `ax2510.16830`：the committed dataset tree with per-leaf digests, the counter commitment c_u, the public initialization hash h_0 and the frozen-backbone commitments
- `ax2510.16830`：the policy manifest (sources, licenses, preprocessing digests, eligibility filters, sampler descriptor with s and sampler_version, PEFT structure, optimizer hyperparameters and schedule, approximation budgets), its hash h_Pi and the optional notary record
- `ax2510.16830`：the lookup tables and error budgets for softmax/GELU/rsqrt (delta_sm, epsilon_fxp, tau)
- `ax2510.16830`：the audit schedule: the thin subset of steps a client proves, the random subset the aggregator checks, and the coverage target q
- `ax2510.16830`：the optional TEE image (VFT-FrontEnd + SamplerGuard) and the prover/verifier hardware tiers
- `ax2510.16830`：the training procedure Pi as the host actually executes it (optimizer, schedule, clipping, batch size); the circuit is written against it
- `ax2603.12089`：客户端签名/公钥与哈希→触发词的映射（步骤 1），由服务器与 CA 在库外保存
- `ax2603.12089`：触发器集合：通用触发器 Tr_u 与每客户端一个的 Tr_k（步骤 2），在库外选定
- `ax2603.12089`：水印嵌入 W_w 以及被替换下来的原始嵌入行 W_u、W_k（步骤 1/2 的产物）
- `ax2603.12089`：水印训练集 D_w，以及构造它的 D_server（步骤 3）
- `ax2603.12089`：逐客户端的带水印模型副本（步骤 2 下发的那一份，每个改两行嵌入）
- `ax2603.12089`：被审计的可疑模型本体与包住它的 ModelHandle；若泄露物是同一基座上的 LoRA 适配器，还有它的状态字典（插件参数 `suspicious=`）
- `ax2603.12089`：CA 的时间戳备案（第 V-K 节覆盖攻击的裁定依据）
- `ax2608.06795`：the trusted clean prompt set (the paper: 40 unlabelled prompts from Stanford Alpaca) - resource clean_prompts
- `ax2608.06795`：the batch of prompts to judge - resource screen_prompts; the paper has no such object, it stands in for the missing user-prompt stream
- `ax2608.06795`：a server-side ModelHandle over the trusted base model plus PEFT stack (the defender passes it as server_guard(probe=...)); the host provides no model on the server
- `ax2608.06795`：the per-adapter calibration state (mu_m, sigma_m, M_k, tau_k) - held in ctx.state here; in the paper it is a deployment artifact reused at serving time
- `ax2608.06795`：the serving stack the gate would guard: the request path, tokenizer, adapter hosting, generation and decoding
- `ax2608.06795`：the paper's evaluation assets (75 adapters, 5 model families, 5 attacks, and the Alpaca sample) that produce the reported ARR/BPR
- `ax2609.37367`：the private held-out probe pool of the node (160 instruction-response pairs, demonstrations and queries, never shared) - here a server-side resource
- `ax2609.37367`：the public trigger-word list (10000 words of 5 to 12 letters, released with the paper's code) from which tau_i is drawn once and kept for the whole run
- `ax2609.37367`：the refusal phrase table of Appendix C (ICLSCAN's list minus "as an AI")
- `ax2609.37367`：the two fixed template answers y_ref and y_c, and ICLSCAN's ICL prompt template that the paper defers to
- `ax2609.37367`：the shared frozen base LLM and its tokenizer behind the server-side model handle (the paper uses LLAMA-2-7B-CHAT or QWEN3-8B), plus the compute to generate and score with it
- `ax2609.37367`：the communication graph up to distance two and the channel to the co-receivers of an adapter - the paper's premise; in a star it does not exist
- `ax2609.37367`：per-neighbour trust states, harvest buffers and count tables are the only state this port keeps, and they live inside ctx.state (no external store)
- `huang2024antidote`：re-alignment 数据集 D_realign：论文默认 2000 条有害问答对，从 BeaverTails 的 is_safe=False 采样，且与微调数据里混入的有害样本不是同一批（Section 3.1、5.1）
- `huang2024antidote`：服务器端一个可运行的模型句柄（基座模型 + PEFT 适配器，如 HFModelHandle），由防御方传入适配器的 probe= 参数；库不提供
- `huang2024antidote`：部署回合号（本轮是不是最后一轮）：调度信息在库外，经 last_round 或 RunSpec.extra["final_round"] 传入
- `huang2024antidote`：α 的任务取值：论文默认 0.2，GSM8K 用 0.05（Section 5.1）
- `huang2024antidote`：剪枝后 checkpoint 的保存与再合并/部署（第 5 步）：由宿主负责，插件只把 replace_global 交回
- `huang2024booster`：对齐数据集：约 5000 条有害提示—安全回答对，来自 BeaverTails 的扩充版本（Section 5.1、Appendix B）
- `huang2024booster`：有害数据集：约 5000 条有害提示—有害回答对，与用户微调数据中的有害样本同分布但样本不同（Section 5.1、Table 8）
- `huang2024booster`：待接种的基座模型权重 w（Llama2-7B 默认，另有 Gemma2-9B、Qwen2-7B）与对齐用 LoRA 配置（rank 32、alpha 4）
- `huang2024booster`：AdamW 优化器状态、两份额外梯度缓存与一个有害 batch 的激活（Table 5：对齐峰值显存 57.86GB，比 SFT 多约 8.53GB）
- `huang2024booster`：接种产物 w̃ 本身，以及用 w̃ 替换服务基础模型的部署动作（Appendix C：之后微调阶段仍是普通 SFT）
- `huang2024booster`：评测侧、不属于防御本体：BeaverTails moderation model（算 HS）、AlpacaEval/ChatGPT 评分（Appendix B）
- `huang2024vaccine`：the provider's safety alignment corpus {x_i, y_i} (the paper uses 2000 BeaverTails harmful-prompt/safe-answer pairs): a `resources` entry, never a fedguard view
- `huang2024vaccine`：the pre-trained LLM being aligned, and a server-side model handle to run it: a server-side plugin may declare `model_handle`, but the host supplies no model on the server, so the defender must pass one in
- `huang2024vaccine`：the alignment optimizer and its schedule (AdamW, lr 1e-3, weight decay 0.1, cosine decay, warmup 0.1) plus the T-step / 50-epoch loop: the host's training loop, outside any plugin
- `huang2024vaccine`：the LoRA adapters (rank 8, dropout 0.1), one for alignment and one for later user fine-tuning, and the merge step between them
- `huang2024vaccine`：the user fine-tuning stage itself, which Vaccine deliberately leaves untouched (Appendix E)
- `inan2023llamaguard`：the instruction-tuned Llama Guard classifier (Llama2-7b plus the released guard weights), loaded by the deployment and wrapped in a ModelHandle; the plugin does not create it
- `inan2023llamaguard`：the safety taxonomy with per-category safe/unsafe guideline text (the six categories of the paper and its wording are not in the extracted text, so a defender taxonomy replaces them)
- `inan2023llamaguard`：the few-shot in-context examples, 2 to 4 per category, mixing unsafe and safe with the safe ones as hard negatives
- `inan2023llamaguard`：the decision threshold chosen per deployment from the precision/recall trade-off the paper leaves to the use case
- `inan2023llamaguard`：the offline pipeline that produced the guard model, if the defender retrains it instead of using the released weights
- `inan2023llamaguard`：no cross-round state: the guard of the paper judges each piece of content on its own, and the plugin keeps nothing in ctx.state
- `rieger2022deepsight`：readout 模块名：哪个 LoRA 模块代表输出层（构造函数参数 readout，默认取 layer 最大的适配模块）。论文假设服务器知道输出层与 P，但没说怎么知道；在 LoRA 里这必须由部署方给出
- `rieger2022deepsight`：服务器侧模型句柄（如果要实现步骤 6–7）：必须防御方自备，宿主不提供。本插件没声明 model_handle，因此不需要
- `rieger2022deepsight`：HDBSCAN 实现：库用 density_clusters 替身（可选 sklearn 只在 majority_cluster 里用到，形状不符）
- `rieger2022deepsight`：跨轮状态：无。DeepSight 只按当前轮计算（§VIII-B 明确批评 FoolsGold 跨轮累积），插件除了轮内 kept/why 交接外不保留任何状态
- `rosati2024repnoise`：The paired refusal corpus: for each harmful question a harmful answer and a safe answer or refusal. The paper builds 18,106 pairs from BeaverTails and uses 10k of them (351 for the toxicity domain, 230 for the HEX-PHI extension) and names the collection of it as the expensive part. It would enter a port as a `resources` asset; the library never produces it.
- `rosati2024repnoise`：An already safety-aligned base LLM with its tokenizer, and a server-side model handle over it (HFModelHandle): the host supplies no model on the server, so the defender has to pass one in as the probe of the adapter, and it has to be a full handle rather than the narrow HFProbe.
- `rosati2024repnoise`：The harmful-content classifier that filters the generated refusals offline (deberta-v3-xsmall over about 330k BeaverTails pairs, F1 0.87): data preparation before the round, not a component of a plugin.
- `rosati2024repnoise`：The immunization training loop itself: its optimizer (Adam, no weight decay), cosine schedule with 10% warmup, learning rate, epoch count, batch size and seed, and the 4-GPU placement of the reported runs. No plugin owns an optimizer or a schedule.
- `rosati2024repnoise`：The attack stage that the immunization is meant to survive (harmful fine-tuning of the released checkpoint) and the evaluation resources (the harmfulness classifier, an LM evaluation harness, external judges): completely outside this library.
- `rosati2024repnoise`：The release step, that is, publishing the immunized checkpoint in place of the aggregated one.
- `shen2024seal`：训练好的选择器 ω_K ∈ R^N，或等价的 {样本 hash → σ_i(ω_K)} 分数表（本插件的 resources['selector_scores']），按数据集版本缓存（Section 4.4：选择器可迁移到别的模型）
- `shen2024seal`：安全参考数据集 D_safe：SLIMORCA 留存子集 112k（Section 4.2）或 ALPACA-CLEANED 子集 49.9k（Section 4.5）
- `shen2024seal`：待微调数据集 D：REDORCA 112k = 90k SLIMORCA + 22k ANTHROPIC RED-TEAMING，或 OPENORCA 49.9k（Section 4.1/4.5）；在联邦里是各客户端的本地分片
- `shen2024seal`：安全对齐的起点模型 θ₁：现成的 instruct/chat 模型，或 PYTHIA-2.8B 的 SFT 2 epoch + DPO 1 epoch 产物（Appendix B.1）
- `shen2024seal`：Algorithm 1 的辅助模型 θ̂（与 θ 同尺寸，显存翻倍；Algorithm 2 不需要）
- `shen2024seal`：S2 的训练循环本身：θ 与 ω 的优化器、α/β/γ 的调度、配对采样与 batch 组成、总步数 K（论文未给）
- `shen2024seal`：（可选，Section 4.4）用于训练选择器的小代理模型 PHI-3-MINI-128K-INSTRUCT 或 PYTHIA-2.8B
- `tamirisa2024tar`：θ 与 θ_G0 两份全参数检查点（论文：Llama-3-8B-Instruct），以及 FSDP 加 DeepSpeed ZeRO-3 的分片参数、优化器与梯度状态（8 张 A100-80GB）
- `tamirisa2024tar`：初始安全防护本身：Random Mapping 的 rand_hashed 目标与训练配方（优化器、学习率、步数论文都未给），或一份已经做过拒绝训练（RLHF/DPO）的 θ_G0
- `tamirisa2024tar`：遗忘与安全代理数据及 80/20 划分：Pile-bio Forget 7,558、Camel-bio Forget 54,258、OOD Forget 598,933、私有化学安全数据、CTFtime 网络安全 writeup 18k 余条；held-out 分片即 D_TR
- `tamirisa2024tar`：retain 与能力代理数据：Pile-bio Retain 42,426 与 Magpie-Align 的混合（拒绝设置只用 Magpie-Align）
- `tamirisa2024tar`：A_train：每个武器化域 6 个、拒绝设置 3 个 SFT 攻击配置（数据、AdamW、学习率采样集、No Warmup、batch 64、全参数、K=64），加上内层学习率采样与 β(6.0, 3.0) 的 R→F 切换抽样
- `tamirisa2024tar`：内层攻击的优化器状态（每个外层迭代重建）、K 个轨迹坐标缓冲、g_TR 累加缓冲，以及搬到 CPU 的外层 ScheduleFree AdamW 状态
- `tamirisa2024tar`：拒绝设置：改写后的 Anthropic-HH-RLHF 划分（rejected 补全换成 refusal）与在整个数据集上预计算的参考 log-prob
- `tamirisa2024tar`：交付物 θ_G（新的基座权重）以及可选的 100 步 Magpie-Align 良性 SFT 配方（学习率与 batch 未给）
- `tamirisa2024tar`：评测资源：WMDP 3,668 题、MMLU 57 个任务、HarmBench、MT-Bench、Toxic-DPO v0.2 541 条、26 个武器化与 5 个拒绝测试期对手；方法运行时不需要它们
- `xie2024gradsafe`：对齐过的基座 LLM（论文 Llama-2-7b-chat-hf），且必须能对参数求梯度；这是部署资源，不是插件产物
- `xie2024gradsafe`：4 条参考提示（2 不安全 + 2 安全），论文附录 A.2 逐字给出
- `xie2024gradsafe`：安全关键切片集合 S 与对应的不安全梯度参考切片（论文 Phase I–III 的输出）：资源 `unsafe_reference` = {"slices": [(参数名, "row"|"col", 下标), ...], "vectors": [一维张量, ...]}；存储量正比于 Σ 切片长度
- `xie2024gradsafe`：GradSafe-Adapt 的已拟合逻辑回归探针（fedguard.ops.probe.fit_logistic 的返回形式）以及拟合它用的带标签目标域提示（论文用 ToxicChat 训练集）；以 `probe` 资源传入，仅 probe=True 时声明
- `xie2024gradsafe`：离线识别时用的 gap threshold（论文取 1）与参考提示条数（2+2）：随离线产物一起决定，插件不重算
- `xie2024gradsafe`：插件不保留跨轮状态：S 与参考固定不变，与论文一致

## 缺的算子与新写的辅助函数

- `ax2103.05633` 缺：`hypothesis_test`，fedguard.ops 没有 KS 检验或任何分布检验；论文 P8 需要逐层单样本 KS 与 p 值（scipy 不在可导入列表里）。
- `ax2103.05633` 缺：`state_distance`，没有“两个 LoRA 状态之间的距离”算子；states.delta 与 states.norm 组合只覆盖 l2，论文的 d1/d2 还允许 l1、linf（cosine 未实现）。
- `ax2103.05633` 缺：`sample_hash`，插件不能导入 hashlib，也没有可导入的文本哈希算子（fedguard.views.client.sample_hash 存在，但不在规则 5 允许插件导入的清单里）；验证者无法对披露的文本重算 h(D[I_t])，只能比对宿主给出的哈希，或与 defense 方预存的哈希表比对。
- `ax2103.05633` 新写：`_cdf/_ks_statistic/_ks_pvalue`（42 行，通用），单样本 Kolmogorov-Smirnov 统计量与渐近 p 值（支持 normal/uniform/退化为点质量）；fedguard.ops 没有任何假设检验，scipy 又不可导入。
- `ax2103.05633` 新写：`_state_distance`（18 行，通用），两个 LoRA 状态字典之间的 l1/l2/linf 距离（论文的 d1、d2）。states.delta + states.norm 只能给 l2，且没有现成的“两个状态之间的距离”算子。
- `ax2103.05633` 新写：`_int_value/_int_list/_float_list/_str_list/_record_bytes`（58 行，通用），把通道上收到的、一律不可信的小记录安全地读成 int/float/str 列表，并保守估计消息体积以免超过 MESSAGE_LIMIT_BYTES。
- `ax2103.05633` 新写：`_windows/_top_q`（20 行，该论文特有），按“窗口结束步所在的 epoch”分组，取每个 epoch 前 Q 大的 k 步更新窗口（论文 P9/P10 的排序与预算选择）。
- `ax2104.13230` 缺：`hessian_or_hvp_of_the_training_loss`，式 (7)/(14) 要训练损失对已训练参数的二阶导，或至少逐样本 HVP。fedguard.ops 没有任何二阶算子：ops.sequential.lbfgs_hvp 是从服务器侧全局模型与聚合更新的差分窗口构造 Hv，客户端逐样本影响用不了；LoRA 参数维数 p 下 p×p 矩阵也放不下。本移植用参考梯度的阻尼经验 Fisher 顶替，并写进 Deviations。
- `ax2104.13230` 缺：`input_gradient_of_the_influence`，式 (12)-(13) 要 d Inf(x)/d x，即参数梯度内积对输入样本的导数。没有任何视图或算子给出对输入的梯度（ModelHandle 的 losses/hidden/activations/per_sample_gradients/logprob/generate 全是参数梯度或纯前向）；CLIENT_LOSS 的 batch 是 token id，对整数索引本身不可导，也没有把 token 变回文本的接口，所以扰动样本无法生成。
- `ax2104.13230` 新写：`influence_norms`（16 行，通用），给定参考逐样本梯度 R 与查询梯度 G，用 Woodbury 恒等式在 n×n 行空间里算 ||A^-1 g||，A = (1/n) R^T R + lam I 永不显式构造（p×p 放不下）。库里没有任何线性求解或二阶算子（ops.probe.fit_logistic 内部有同类行空间求解但不导出），影响函数类方法都能复用，故记为通用件。
- `ax2210.07714` 缺：`fedguard.ops.geometry 的逐行成对距离`，cosine_to / distance_to 只接受一个参照向量，cosine_matrix / pairwise_sq_distances 只作用于同一矩阵；S5 需要两个同形矩阵按样本逐行配对的距离与余弦，只能在插件里写 _row_cosine / _row_distance
- `ax2210.07714` 缺：`假设检验算子`，fedguard.ops 没有任何统计检验（两样本 t、F、KS、箱线图、3σ）；scipy 不允许导入，torch 也没有可用的 t/F CDF，必须在插件里实现正则化不完全 beta 与三个 p 值
- `ax2210.07714` 新写：`_betacf / _betainc`（44 行，通用），正则化不完全 beta（修正 Lentz 连分式）：torch 2.10 的 StudentT/FisherSnedecor.cdf 直接 NotImplementedError，torch.special 也没有 betainc，scipy 不在允许导入清单里
- `ax2210.07714` 新写：`_t_pvalue / _f_pvalue / _ks_pvalue`（44 行，通用），Alg. 4 的 t 检验、F 检验、KS 检验的 p 值；样本不足或方差为 0 时返回 1.0（跳过该检验）
- `ax2210.07714` 新写：`_boxplot_outlier / _sigma_outlier / _significant`（22 行，通用），1.5 IQR 箱线图离群、双侧 3σ 离群，以及五项取或的显著性判定
- `ax2210.07714` 新写：`_row_cosine / _row_distance`（8 行，通用），两个同形矩阵逐行配对的余弦与欧氏距离，即 S5 的 dist(DLO_locals, DLO_globals)
- `ax2210.07714` 新写：`_relative_signed_square`（10 行，该论文特有），S6 的 |rel-1|*(rel-1) 与零分母约定
- `ax2210.07714` 新写：`_common_layers`（7 行，通用），各模型公共层输出的交集（一次 forward 里 handle 报告的层名取交并排序）
- `ax2210.07714` 新写：`_prune / _aggregated_vote`（47 行，该论文特有），Alg. 2 的迭代剪枝（含安全中止）与 Alg. 3 的堆叠聚类投票聚合
- `ax2301.09508` 缺：`normal_density / normal_log_density`，在给定点上求一个已知正态的密度；ops.density 只有 gaussian_kde（从样本估密度），没有这个
- `ax2301.09508` 缺：`jensen_shannon_divergence`，ops 里没有 KL 或 JS 散度，最接近的只有 ops.density.shannon_entropy
- `ax2301.09508` 新写：`log_normal`（5 行，通用），在一个张量的每个元素上取正态分布 N(mean, sd) 的对数密度，sd 可以广播；fedguard.ops 没有这个算子
- `ax2301.09508` 新写：`normal_density`（3 行，通用），正态密度本身，对数下界钳到 -700，远离均值的坐标不会变成精确的 0（避免后续归一化出现 0/0）
- `ax2301.09508` 新写：`jensen_shannon`（17 行，通用），两个非负向量各自归一化后的 Jensen-Shannon 散度（nats），按行批量计算；fedguard.ops 没有 KL/JS 算子
- `ax2301.09508` 新写：`round_filter`（19 行，该论文特有），论文 Alg. 2 的过滤规则（低于本轮均值且取值唯一才保留），拆成模块级函数以便直接测两条规则
- `ax2305.05506` 缺：`dunn_index`，Eq. (5) needs a cluster validity index that prefers separated clusters; ops.cluster stops at silhouette and the gap statistic, so it is written in the plugin file (21 lines, generic).
- `ax2305.05506` 缺：`trellis_forward_backward`，the decoder of Eq. (17) has no operator; it is paper-specific and lives in the plugin file (33 lines).
- `ax2305.05506` 缺：`belief_propagation_llr`，the alternative decoder for assignment matrices too large for the forward-backward (R16b). The paper gives no algorithm, so no operator was written and the step stays unported.
- `ax2305.05506` 新写：`lora_modules`（11 行，通用），module prefixes of a LoRA state dict that carry both factors. fedguard.views.uploads.lora_modules computes the same thing but the porting rules let a plugin import only ops, so it is rebuilt from ops.states.module_info.
- `ax2305.05506` 新写：`_depth`（4 行，通用），layer index of a module prefix through ops.states.module_info, -1 when the name carries no layer number; used to pick the readout module that stands for the fully connected layer.
- `ax2305.05506` 新写：`dunn_index`（21 行，通用），step R9. ops.cluster has silhouette and the gap statistic but no Dunn index; squared Euclidean distances as the paper writes them, with the 0/0 and 0-diameter conventions spelled out in the plugin.
- `ax2305.05506` 新写：`trellis_llr`（33 行，该论文特有），steps R15 and R16: the trellis of the assignment matrix (states are partial syndromes, 2**m of them) and the forward-backward posterior LLRs of Eq. (17) with the factorized BSC likelihood and the 1-delta / delta branch metrics. Nothing in ops works on a trellis or on a sequence.
- `ax2402.12168` 缺：`confidence_from_outputs`，把模型输出分布变成论文置信度 C 的算子（最大 softmax 概率、目标类概率或 margin）在 fedguard.ops 里没有；更根本的是没有任何接口能拿到 logits：ModelHandle 只给 losses / logprob / hidden / activations / generate，LossView 的记录接口只有 loss / per_sample_losses / gradients_of / loss_on（其 outputs 属性不在 <reference> 里，按规则不可依赖）
- `ax2402.12168` 缺：`random_label_reset`，在标签上做随机重置的通用小函数（重抽分布、是否排除原标签、比例、种子）；函数本身很小，但库里没有带标签的样本类型可以喂给它，见 missing_runtime
- `ax2409.14119` 缺：`differentiable norm-sum over a parameter mapping`，no operator returns sum_p ||W_p|| as a tensor that keeps a graph; states.norm is float-only. The 3-line module-level helper amplification_penalty replaces it.
- `ax2409.14119` 新写：`amplification_penalty`（3 行，通用），Eq. (1) as a differentiable scalar: minus the sum of the L2 (Frobenius) norms of a mapping of PEFT tensors. fedguard.ops.states.norm computes the same number but returns a Python float, so it cannot be part of a loss.
- `ax2409.14119` 新写：`lora_factor_params`（1 行，通用），Selects the entries of a {name: Parameter} mapping whose name carries a lora_A/lora_B factor, via fedguard.ops.states.module_info; the paper's amplified set restricted to the architecture this library carries.
- `ax2410.14425` 缺：`softmax_kl_divergence`，T^2 * KL(softmax(z_t/T) || softmax(z_s/T)) between two logit tensors (eq. 8-10); fedguard.ops has no softmax and no KL operator, and no view supplies logits to feed one
- `ax2410.14425` 缺：`mean_squared_feature_distance`，mean over a batch of the squared L2 distance between two (n, d) hidden-state matrices (eq. 11-12); not in fedguard.ops
- `ax2411.17453` 缺：`conv_mlp_scorer`，There is no operator that can hold or run a trained neural component. fedguard.ops.probe fits and applies a linear probe on flat feature vectors, which is not the meta-classifier of Eq. (12): the paper's Table 6 shows that dropping the convolution for global pooling collapses accuracy to 50.00% (AUC 0.742) and max-pooling to 89.33%. So step 5 can only be a call into an opaque callable plus a threshold, and the detector cannot live in fedguard.ops.
- `ax2411.17453` 新写：`_modules`（5 行，通用），LoRA module prefixes of a state dict that carry both factors, sorted. The same rule already exists as fedguard.views.uploads.lora_modules, but that module is not on the plugin import surface (plugins may import fedguard.ops.*, fedguard.core.* and fedguard.methods.server_update only), so it is 3 lines of key parsing here.
- `ax2411.17453` 新写：`_places`（8 行，通用），(block, role) -> module prefix for one state dict, built on fedguard.ops.states.module_info. This is what gives Eq. (13) its channel axis (the target modules of a block) and Eq. (14) its layer axis.
- `ax2411.17453` 新写：`_stack`（11 行，通用），Steps 2-4 for one client: the LowRank effect of every (block, role) module through the view (ctx.uploads.cumulative / .increment), a shape check, and torch.stack into F_input. Nothing in fedguard.ops builds this tensor.
- `ax2506.22506` 缺：`fedguard.ops.robust.top_m`，对一组分数做确定性的 top-m 选择（rank 式、不用阈值）；本次以插件文件里的 rank_top_m 顶替
- `ax2506.22506` 缺：`fedguard.ops.probe.apply_binary`，把防御方自备的二分类检测模块（论文是两层 MLP）对一批特征做前向并把 logits 按阈值二值化；现有 apply_logistic 只适用于 fit_logistic 产出的线性探针字典
- `ax2506.22506` 新写：`detector_flags`（11 行，通用），在 no_grad 下把一批嵌入过防御方的二分类检测器，并把 class-1 概率按阈值变成 0/1 标记；库的 probe 算子只覆盖它自己拟合的线性探针，不覆盖外部传入的模块
- `ax2506.22506` 新写：`rank_top_m`（9 行，通用），取分数最大的 m 个键、并列按给定顺序 tie-break 的 rank 截断；库里有 largest_gap_threshold（阈值式切分）但没有 top-m 选择
- `ax2510.16830` 缺：`fixed_point_quantize`，map a real tensor to round(S x) with S = 2^b and carry an overflow/error budget (Eq. (5)); fedguard.ops has clipping, scaling and noise but no quantization
- `ax2510.16830` 缺：`hash / merkle_commit / vector_commit`，no operator computes a digest of a state dict, a Merkle root or a Pedersen/KZG commitment, so c_D, c_u, h_t, h_Pi and the optimizer-state commitments cannot be produced or checked
- `ax2510.16830` 缺：`range_proof / interval_membership`，Eq. (1) is decided per coordinate with tolerance tau = delta_sm + eps_fxp; nothing in fedguard.ops takes an acceptance predicate with a tolerance or a bound
- `ax2510.16830` 缺：`verify_proof / fold_proofs`，no proof-system operator of any kind; this is also the cryptographic protocol that rule 3 keeps out of plugins, so it is listed for completeness of the cost measurement, not as a request
- `ax2603.12089` 缺：`fedguard.ops.text.insert_trigger`，在文本的随机词位插入一个词；库里没有这个算子，已在插件文件里写成模块级函数（见 new_helpers）。
- `ax2603.12089` 缺：`vocabulary / token-id 查找`，把客户端签名的哈希映射成词表里的触发词 token 并定位对应的词嵌入行：ModelHandle 不暴露词表或 token id（tokens 只对给定样本分词），插件也不允许 import 哈希库，这一步只能在库外做。
- `ax2603.12089` 新写：`insert_trigger`（11 行，通用），按论文的 T = I(x, Tr, p, n) 把触发词插到文本的随机词位；fedguard.ops.text 只有 split_words/leave_one_out 一类算子，没有插入算子，词边界沿用 split_words。
- `ax2603.12089` 新写：`exclusive_attribution`（11 行，通用），式 (3) 的排他阈值规则：只有一个候选的 VR 达到 gamma、其余全部低于它时返回该候选，否则返回 None（论文的 False）。
- `ax2603.12089` 新写：`verification_interval`（7 行，通用），第 V-B 节的验证区间 VI_k = VR_k − 其余候选 VR 的均值。
- `ax2608.06795` 缺：`state_key_to_module_name`，no operator maps a LoRA state-dict key (<module>.lora_A.weight) to the submodule names ModelHandle.activations(select=...) matches; parameters/layout name parameters, not modules. Worked around by offering both PEFT spellings and reporting unmatched sites
- `ax2608.06795` 缺：`activations-ready insertion-site scan`，fedguard.views.uploads.lora_modules does the site scan, but fedguard.views.* is outside the plugin import allow-list, so the four lines had to be rewritten in the plugin file
- `ax2608.06795` 缺：`raw median and MAD`，no op returns the median and the raw MAD scale of a 1-D clean sample (ops.robust.robust_z applies the 1.4826 factor and a minimum n); Eq (4) needs bm and bd themselves
- `ax2608.06795` 新写：`insertion_sites`（9 行，通用），module prefixes of a LoRA state dict that carry both lora_A and lora_B; duplicates fedguard.views.uploads.lora_modules, which a plugin file cannot import
- `ax2608.06795` 新写：`lora_a_module_map`（13 行，通用），maps each insertion site to the submodule names ModelHandle.activations(select=...) can match (<site>.lora_A and <site>.lora_A.default)
- `ax2608.06795` 新写：`low_variance_sites`（7 行，通用），the k lowest values of a 1-D sample, with the max(1, round-half-up) floor and a deterministic tie order; ops.sampling.subsample only draws at random
- `ax2608.06795` 新写：`median_mad_threshold`（12 行，通用），median + lambda * MAD upper-tail threshold; ops.robust.robust_z returns 1.4826-scaled z-scores and needs n >= 5, not the raw median/MAD scale
- `ax2608.06795` 新写：`spike_statistic`（9 行，该论文特有），Eq (2) itself (max * log(1 + max/mean) over the per-token magnitudes), not a library gap
- `ax2609.37367` 缺：`word_span_counts`，enumerate the contiguous word spans of a buffer of texts and count in how many texts each occurs (Algorithm 4); fedguard.ops.text only splits words and does leave-one-out, nothing counts spans over a corpus
- `ax2609.37367` 缺：`nested_span_prune`，greedy selection of the most frequent/longest spans with a single representative per nested family (Algorithm 4); no operator does containment-based redundancy pruning
- `ax2609.37367` 缺：`strict_majority`，Algorithm 3's pooled vote with the tie accepting; three lines, written in the plugin file
- `ax2609.37367` 缺：`context_gain`，the movability score of Algorithm 5 (per-token log-probability of a target under two contexts); it composes ModelHandle.logprob, which exists, but nothing in ops covers it because ops are model-free
- `ax2609.37367` 新写：`insert_trigger`（7 行，通用），INSERTTRIGGER of Algorithm 2: insert a word between two words of an instruction at a uniformly drawn boundary
- `ax2609.37367` 新写：`refusal_rate`（6 行，该论文特有），Stage 1a score: fraction of generated answers containing one of the refusal phrases as a lower-cased substring
- `ax2609.37367` 新写：`majority_reject`（3 行，通用），Algorithm 3: strict majority of a pooled score list above eta, a tie accepting
- `ax2609.37367` 新写：`span_counts`（15 行，通用），Algorithm 4: count, per contiguous word span of a fixed minimum length, in how many generations of the buffer it occurs (a generation counts once per span)
- `ax2609.37367` 新写：`pruned_spans`（18 行，通用），Algorithm 4: keep the most frequent and longest spans, one representative per nested family, up to kappa a round
- `ax2609.37367` 新写：`candidates_of`（12 行，该论文特有），Algorithm 5: the K-1 most frequent strings plus the longest string y^max, ties by length then lexicographic
- `ax2609.37367` 新写：`demo_block`（3 行，该论文特有），one instruction/response block of the ICLSCAN-style prompt template
- `ax2609.37367` 新写：`render`（5 行，该论文特有），assemble a prompt from two ordinary demonstrations, the third one triggered or not, and the triggered query
- `ax2609.37367` 新写：`context_gain`（7 行，该论文特有），Delta_i(theta, y) of Algorithm 5: mean gain in per-token log-probability of y when y is demonstrated in the context, over a batch of prompt pairs
- `ax2609.37367` 新写：`reason`（6 行，该论文特有），human-readable flag for a client kept out of the aggregation
- `huang2024antidote` 缺：`lora factor pairing（如 fedguard.ops.states.factor_pairs）`，在插件可导入的范围内没有把状态字典归成 lora_A/lora_B 对的算子：fedguard.views.uploads.lora_modules 存在但白名单排除了 fedguard.views.*，12 行被重写进插件文件
- `huang2024antidote` 缺：`per-channel activation norm reduction`，fedguard.ops 没有从逐 token 激活求逐通道 L2 范数（再对样本平均）的算子；geometry 的行距离、density 的 KDE、states.norm 都不是这个，9 行写在插件里
- `huang2024antidote` 缺：`top-ratio coordinate mask`，fedguard.ops 没有"按比例取 top-k 坐标并给出 0/1 掩码"的算子（robust.largest_gap_threshold 是间隙阈值，geometry.krum_scores 是按行距离），26 行写在插件里
- `huang2024antidote` 新写：`factor_modules`（12 行，通用），把 LoRA 状态字典归成 {module: {A 键, B 键}}。fedguard.views.uploads.lora_modules 做的是同一件事，但插件导入白名单不含 fedguard.views.*，只能重写这 12 行
- `huang2024antidote` 新写：`activation_side`（14 行，通用），判断被 hook 的模块名承载的是该 LoRA 模块的输入激活，还是 lora_B 的输入（即瓶颈激活）；适配器可能在 <module>.lora_B 后加名字（PEFT 是 .default），也考虑 <module>.base_layer
- `huang2024antidote` 新写：`selects`（5 行，通用），构造 ModelHandle.activations 的 select 谓词，只 hook 要打分的 LoRA 模块，避免对全模型挂 hook
- `huang2024antidote` 新写：`channel_norms`（9 行，通用），pool="none" 的逐样本 (tokens, d) 激活 -> 逐通道 L2 范数再对样本取均值，即式 (1) 的 (1/|D|) Σ_x ||A_j(x)||_2；fedguard.ops 里没有任何按列/按通道的范数归约
- `huang2024antidote` 新写：`activation_norms`（20 行，通用），把一次 activations 调用的返回整理成每个模块的输入/瓶颈通道范数，并列出 handle 没暴露的模块（缺一侧就不参与打分，保证每个候选坐标都同时带式 (1) 的两项）
- `huang2024antidote` 新写：`top_ratio_mask`（26 行，通用），式 (2)：对扁平化后的坐标取 floor(alpha*d) 个最大值做 0/1 掩码，支持全局或逐因子作用域，平局用稳定排序按 flatten 顺序裁定
- `huang2024antidote` 新写：`module_features`（8 行，该论文特有），每个模块的坐标数、被掩码数、分数极值与均值，供 findings.features 记录（Antidote 没有客户端，subject 只能是模块）
- `inan2023llamaguard` 新写：`guideline_block`（18 行，该论文特有），renders the numbered categories and their safe/unsafe descriptions into the guidelines block of the prompt (names-only or with descriptions)
- `inan2023llamaguard` 新写：`example_block`（14 行，该论文特有），renders the defender-supplied in-context examples of Section 3.2 as a block of the prompt
- `inan2023llamaguard` 新写：`conversation_block`（4 行，该论文特有），renders one local sample as a single-turn conversation with the role the task selects
- `inan2023llamaguard` 新写：`build_task_prompt`（6 行，该论文特有），fills the module-level TASK_PROMPT (12 further lines) with the four ingredients of Section 3.1
- `inan2023llamaguard` 新写：`parse_category_indices`（15 行，通用），reads the 1-based category indices out of a letter-plus-index verdict string, without the re module (not an allowed import)
- `inan2023llamaguard` 新写：`binary_guard_score`（5 行，通用），two-way renormalization of the safe/unsafe log-probabilities into P(unsafe), numerically guarded
- `rieger2022deepsight` 缺：`output_layer_bias_delta`，从 LoRA 状态字典拿不到输出层偏置：LoRA 适配器没有 bias 项，ClientUpdate.lora / UploadView.state / base_state 里只有 lora_A、lora_B，于是式 (7) 的 |Δb_i| 与式 (13)(14) 的偏置余弦都无从计算（不是近似为零，而是根本没有这个数据）
- `rieger2022deepsight` 缺：`random_probe_forward`，没有算子能对服务器自己生成的随机输入向量做前向。ModelHandle.activations/losses/hidden 只接受 adapter 能分词的 samples（序列），不能喂 input_dim 维随机向量；服务器默认也没有模型，Alg. 1 的 input dim 参数无处可取
- `rieger2022deepsight` 缺：`output_layer_probabilities`，没有算子返回“每个样本、每个输出神经元的概率”。ModelHandle.activations(select=<输出模块>, what='output') 是唯一可能路径，但它给的是子模块输出（logits）且只对 tokenized 样本；ProbeView.score 只返回命名标量
- `rieger2022deepsight` 缺：`row_l1_of_lowrank`，低秩乘积的逐行 L1 范数（式 7 的权重项）在 ops.lowrank 里没有：L1 不像 Frobenius 内积那样能从因子的小 Gram 矩阵算出来，只能逐行形成。已在插件文件里写成 readout_row_l1
- `rieger2022deepsight` 缺：`hdbscan`，没有精确的 HDBSCAN。ops.cluster.majority_cluster 内部会调 sklearn 的 HDBSCAN，但只保留 min_cluster_size=n//2+1 的那一个多数簇，形状与 Alg. 2 要的多簇+噪声不符；density_clusters 是“论文没给参数时的替身”，用的是 DBSCAN + 数据驱动的 eps
- `rieger2022deepsight` 缺：`clusterwise_aggregation`，没有任何动作能返回“按簇算出的多个聚合结果”。select_and_weight 只产生一个聚合，replace_global 只替换一个全局模型；transform_broadcast 能按客户端下发不同状态，但多个聚合模型得插件自己从 ctx.uploads 里算
- `rieger2022deepsight` 新写：`readout_row_l1`（9 行，通用），低秩矩阵 scale*U@V 的逐行 L1 范数（式 7 的 Σ_h|Δw_ih|），一次只形成一行，不物化 P×d_in 矩阵；对应式 (7) 的权重项
- `rieger2022deepsight` 新写：`threshold_exceedings`（6 行，通用），式 (8)(9)(10)(11)：逐模型归一化能量、ξ=max(tf,1/P)·C_max、TE=#{C_i>ξ}
- `rieger2022deepsight` 新写：`co_membership`（6 行，通用），Alg. 2 的 DistsFromClust：同簇 0、异簇 1 的距离矩阵
- `rieger2022deepsight` 新写：`groups_of`（6 行，通用），把簇标号拆成下标分组，噪声点 -1 各成一组（论文未规定噪声点怎么办）
- `rosati2024repnoise` 缺：`multi_kernel_gaussian_mmd`，no operator measures a distribution distance between two sample sets (fedguard.ops.density has a KDE, entropy and nearest-neighbour density ratios, but nothing that pairs activations with a noise sample). The paper uses a multi-kernel Gaussian MMD. A module-level helper is allowed by rule 1, but every activation the server side can be handed is detached, so it would return a number and not a loss term.
- `rosati2024repnoise` 缺：`layerwise_lm_head_loss`，no operator applies the language-model head to an intermediate activation and takes its cross-entropy against the target tokens. ModelHandle offers only the loss of the model on samples through its final head (losses, logprob); the head is not reachable as a module or as a tensor.
- `shen2024seal` 缺：`softmax_selector_rank_update`，没有算子计算 ∇σ_j(ω) 或执行 ω ← ω − α·gap·∇σ_j(ω)（公式 (5)/(8)）；数学上只要几行，但没有任何位置能承载它所属的 S2 迭代，见 missing_runtime
- `shen2024seal` 新写：`top_percent_keep`（13 行，通用），按分数取 ceil(p*n) 个最大者的下标（升序返回），并列按输入顺序，n>0 时至少保留一个：SEAL 的 top p% 截断；论文没给取整与并列规则，这里是本移植固定的规则
- `tamirisa2024tar` 缺：`entropy_loss`，武器化设置的 L_TR：对一批样本的输出分布取（负）熵并作为训练目标反传。fedguard.ops 里只有把熵当统计量的 density.shannon_entropy(p)（对非负向量归一化后求 nats，没有图、不面向 logits），没有可微的逐 token 或逐批熵损失；也没有任何视图给出带图的 logits（LossView 的 outputs 属性不在 <reference> 里，按规则不可依赖）。
- `tamirisa2024tar` 缺：`dpo_loss`，拒绝设置的 L_TR：由 chosen/rejected 对与参考 log-prob 组成的可微 DPO 损失。ops.probe 是特征上的逻辑回归，与此无关；ModelHandle.logprob 返回 Python float 列表，没有图；参考 log-prob 只能作为资源传入。
- `tamirisa2024tar` 缺：`inner_loop_meta_gradient`，把内层 K 步 SFT 当作 θ 的可微函数、按直线估计器取 ∇_θ L_TR(attack(θ)) 的算子（一阶 MAML 式元梯度）。库里没有任何算子或运行时把一段优化轨迹当作可微对象。
- `tamirisa2024tar` 缺：`representation_anchor`，式 2 第二项：同一批次上两个模型（θ_{i-1} 与 θ_G0）残差流激活之间的可微 ℓ2 距离。ModelHandle.hidden 只给单个模型、detach 后的 CPU 张量；没有第二个参考模型的类别。
- `xie2024gradsafe` 缺：`fedguard.ops.geometry.cosine_rows`，X 的每一行与 Y 对应行的余弦（cosine_to 是单参考向量、cosine_matrix 是全配对，缺 index 对齐的一对一）；这里用 torch.nn.functional.cosine_similarity 顶替
- `xie2024gradsafe` 新写：`prompt_response_pair`（3 行，该论文特有），把待检测提示套进论文 4.1.4 节的 system prompt 模板，再接上顺从回复 "Sure"（步骤 1 的配对构造）；模板与回复是构造参数

## 需要向原作者确认的

- `ax2103.05633`：δ 的具体标定（含 d_ref 由谁、以什么成本测）与推荐的 Q、k；论文只给了方法与个别实验观测。
- `ax2103.05633`：哈希函数 h、加密方案 enc、时间戳/账本机制的具体选择。
- `ax2103.05633`：优化器状态（动量、二阶矩）是否需要进证明。
- `ax2103.05633`：k 是否必须整除 S、跨 epoch 边界的 k 步窗口如何切分，以及同一 epoch 内 top-Q 窗口是否允许重叠。
- `ax2103.05633`：参考实现如何处理算法 2 漏刷最后一个 epoch、以及算法 1 中 I 的覆盖赋值与 append 不一致这两处伪代码问题。
- `ax2103.05633`：层间初始化不独立时是否用 Bonferroni 校正（论文只说“需要时”），以及初始化策略允许集合的完整枚举。
- `ax2104.13230`：s_y 的取值或算法（论文只引用 Steinhardt 等），以及是否按数据集调。
- `ax2104.13230`：w_inf 的数值与冷启动规则（论文只说 grid search 经验确定）。
- `ax2104.13230`：η_def、式 (12) 的迭代次数与停止条件（论文都没给）。
- `ax2104.13230`：H 是否重算、在哪个集合上估、是否加阻尼或用伪逆。
- `ax2104.13230`：扰动后的 x* 是否要投影回 F_slab 或 F = [-1,1]^d × {-1,+1}。
- `ax2104.13230`：实际使用的标签编码（4.1 节与 5 节不一致）。
- `ax2104.13230`：表 1 中 MNIST / Fashion MNIST 的 50 维特征如何得到（复现实验需要）。
- `ax2210.07714`：PCA 的预处理细节（是否中心化/标准化、求解器、符号约定）
- `ax2210.07714`：Alg. 4 line 11 的分组到底按原始 PC 值还是按 value - median
- `ax2210.07714`：F-Test 与脚注 10 的 Levene-Test 的取舍
- `ax2210.07714`：箱线图离群倍数（是否 1.5×IQR）与 3σ 是否双侧
- `ax2210.07714`：HLBIM 的最终形状与 lab / layer 两维的拼接顺序
- `ax2210.07714`：DLO 的具体形式（卷积层是否展平、是否包含最终分类层、是否归一化）
- `ax2210.07714`：Cosine 与 Euclidean 两轮剪枝如何写入同一个投票数组
- `ax2210.07714`：AGGLOM 的距离度量与 linkage、DBSCAN 在二值投票向量上的度量
- `ax2210.07714`：安全中止时 MIN(malicious_models) 的定义
- `ax2210.07714`：验证投票缺失/超时的处理，以及剔除后 Eq. 1 的 n 是否重取剩余模型数
- `ax2210.07714`：每个客户端的验证样本规模与是否子采样（论文默认全部，Sect. VI-C 又提到可用代表性子集）
- `ax2301.09508`：Eq. (4) 第 (iii) 行的确切含义（1 与 W_bar 谁是均值、这一步到底是密度还是归一化）——按字面实现会改变检测结果的符号
- `ax2301.09508`：Max_i^JD 到底以 argmax 还是 argmin 决定簇归属，以及 n_oc = 0 时 Alg. 1 第 12-23 行的控制流
- `ax2301.09508`：mu_0、sigma_0^2、tau_0 的取值，以及 tau_k、n_k 的逐轮更新规则
- `ax2301.09508`：簇状态（n_oc、mu_cl、sigma_cl、n_k）是否跨轮保留、n_k 是否每次分配后自增
- `ax2301.09508`：重复判定在实现里怎么做（Alg. 2 要求精确相等，但没给容差或量化方案）
- `ax2301.09508`：W_i^t 是完整本地模型还是相对 G^{t-1} 的增量；展平前是否按坐标归一化；是否包含 BatchNorm 统计量
- `ax2301.09508`：H^t 是每客户端一份 H_i^t 还是全局单一 H^t（Sect. 4.2.1 与 Sect. 4.2.2 措辞不一致）
- `ax2301.09508`：作者是否公开了实现：快速检索没有找到代码仓库，以上各点只能靠作者代码或答复确认
- `ax2305.05506`：The assignment matrices themselves (the (15, 8) BCH and (30, 18) cyclic parity-check matrices), n_m^max, the Pr(Z | N_m) table and the Delta-hat(n_m) search results, with the Monte Carlo sample counts, none of which the paper publishes.
- `ax2305.05506`：How one secure aggregation instance yields the m overlapping group aggregates (the masks and secret sharing), which the paper leaves open and which the port therefore cannot reproduce.
- `ax2305.05506`：Whether the group-testing round also updates the global model, which global model it tests, and what happens to the flagged clients in the rounds after it.
- `ax2305.05506`：The clustering details the paper omits: whether the PCA centers or whitens, whether the two features are normalized or weighted, the k-means initialization, distance and restarts, and the tie-breaks of Eq. (5) and of the negative-test rule.
- `ax2305.05506`：How the attacked source label is located automatically; the paper only suggests monitoring per-label recall in the test groups.
- `ax2402.12168`：置信度 C 的精确定义（论文只写 confidence；正文以二分类下 clean 接近 50% 为例，脚注 3 说多分类下会偏低）——没有它步骤 3 无法实现，也无法判断最大 softmax 概率 / 目标类概率 / margin 哪个是原意
- `ax2402.12168`：标签随机重置的分布、是否排除原标签、重置比例与随机种子（Algorithm 1 第 2 行只写 Random Reset Sample Label）
- `ax2402.12168`：PSIM 训练的轮数/步数/早停准则与 PSIM 专用学习率（Appendix B 只给跨 PEFT 策略的 2e-5~2e-3 范围）
- `ax2402.12168`：阈值 γ 在 {0.7, 0.75} 之间按模型选择的规则，以及多分类数据集（AG's News, Table 8）上用的 γ
- `ax2402.12168`：PSIM 与 victim model 微调的先后顺序（论文只说两者独立；公式 (1) 与 Algorithm 1 第 3 行都以 θ_p 为初始化）
- `ax2409.14119`：the final lambda_amp / lambda_reg values per architecture and dataset (only candidate sets and the 2% rule are published)
- `ax2409.14119`：whether ||W_p||_2 is the Frobenius or the spectral norm, and whether the two coefficients are searched jointly or independently (and whether each candidate needs a retrain)
- `ax2409.14119`：the exact shape and aggregation of a_h in Eq. 2 (softmax weights or logits, batch/token averaging, whether [CLS]/[SEP] are included)
- `ax2409.14119`：the exact tensor list of all PEFT layers for adapter and prefix-tuning, and the author code that extracts the [CLS] attention; which lambda_reg candidate range is authoritative (Table 7 vs Figure 9)
- `ax2410.14425`：the (alpha, beta, gamma) values per dataset/victim pair; Appendix B.1 gives only the candidate sets
- `ax2410.14425`：the teacher-training hyperparameters (epochs, lr, batch size, optimizer) and the exact form of l in eq. (5)
- `ax2410.14425`：how teacher and student outputs are made comparable across two vocabularies, and whether z_t/z_s are vocabulary or classifier logits
- `ax2410.14425`：hidden-state extraction: token position and pooling for h_t/h_s, and whether the alignment distance is squared
- `ax2410.14425`：the lifecycle of the alignment layer g: frozen during unlearning, updated with the teacher, included in the teacher logits?
- `ax2410.14425`：the LoRA configuration (target modules, alpha, dropout, whether the head is adapted) and whether the adapter is re-initialized on the poisoned student
- `ax2410.14425`：the checkpoint-selection rule over the 5 epochs, and D_clean_train sizes and splits for datasets other than AG's News
- `ax2411.17453`：The architecture of PEFTGuard_cls (Figure 7a): convolution kernel size, stride, padding, channel count, the number and width of the MLP layers, activations, normalization and where dropout=0.4 sits. Without it the trained network can only be used, never rebuilt or retrained.
- `ax2411.17453`：Whether a probability threshold exists at all, and whether the 0/1 comes from sigmoid + 0.5 (they report DA and AUC, not a threshold).
- `ax2411.17453`：How Eq. (13) stacks delta_q and delta_v when they do not share (d_out, d_in): Llama-3-8B, listed among the base models of Table 15, uses grouped-query attention, where v_proj is 1024x4096 against q_proj 4096x4096. The paper does not discuss it.
- `ax2411.17453`：Whether DoRA's magnitude vector m enters the feature and whether AdaLoRA's P, Lambda, Q are multiplied out to delta = P Lambda Q before the stack (Section 2.2 defines them; Section 4.2 does not say).
- `ax2411.17453`：The PADBench split script, seeds, and the sampling ratio of the 'randomly sampled sub-datasets' used to build the benign and backdoored adapters.
- `ax2411.17453`：The meta-classifier training schedule (epochs, LR schedule, early stopping, model selection) - only batch size 4, Adam, lr 2e-5, weight decay 1e-5 are given - and the fusion weights and contrastive temperature of steps 9-10.
- `ax2506.22506`：D_aux 构造：辅助集用哪个子集/多少张、注入触发器的比例与总条数 N、触发器 t 怎么来（附录 D.1 的 3 epoch 触发器优化是否用于此）、'a fixed prompt learner' 具体指什么
- `ax2506.22506`：检测器实现与权重（论文只有结构与优化器超参）：logits→0/1 的阈值、嵌入进 MLP 前是否 L2 归一化/标准化
- `ax2506.22506`：每客户端每轮上报多少条嵌入 n_k、是否每轮都报、是否与 prompt 更新同一批传输（Algorithm 1 第 11 行抽取残缺）
- `ax2506.22506`：每轮 m 的绝对值与是否随轮变化；服务器学习率 η 与剔除后是否按样本量加权、是否重新归一化
- `ax2510.16830`：PROVEUPDATE pseudocode, announced in Sec. III.K but absent from the extracted text: without it the witness layout and constraint arrangement of a step proof cannot be defined, so no step-proof interface can be built.
- `ax2510.16830`：The concrete softmax/GELU/rsqrt approximations (polynomial or rational form, clipping range, lookup table sizes, interpolation) and the numeric epsilon_fxp, tau and GELU budget; tau = delta_sm + epsilon_fxp cannot be instantiated from the paper.
- `ax2510.16830`：Merkle tree arity and hash instantiation, plus the Pedersen/KZG parameters and SRS size.
- `ax2510.16830`：How the binning matrix M combines domain, register and length into B rows and whether Eq. (3) is per attribute or joint; how Table IV's ceilings convert to batch size 64 and steps per epoch; how global quotas and fairness counters combine with local ones.
- `ax2510.16830`：The size of the thin subset of steps a client proves, the size of the random subset the aggregator checks, and the test statistic and threshold of the probabilistic audit (only detection probabilities are reported).
- `ax2510.16830`：Whether the proven fixed-point shadow computation is the released model or a parallel witness, and the recovery semantics after a tainted client is excluded (full re-aggregation vs rolling back its contribution).
- `ax2510.16830`：The VFT-FrontEnd/SamplerGuard implementation, to see what per-step data the prover actually consumes.
- `ax2603.12089`：通用触发器 Tr_u 的生成规则（步骤 2 只说服务器生成它）
- `ax2603.12089`：哈希值到词表 token id 的映射细节：越界、一个词被切成多个 token、两个客户端撞到同一 token 时如何处理
- `ax2603.12089`：验证样本数 t 的取值，以及这 t 条样本的来源
- `ax2603.12089`：式 (2) 的碰撞阈值 sigma 的取值，以及相似度 Sim 的具体口径
- `ax2603.12089`：触发词插入次数 n 的取值
- `ax2603.12089`：每轮水印强化训练的 epoch 数与学习率，是否复用第 V-A 节的一次性训练设置
- `ax2603.12089`：每客户端多个触发词时如何分配（论文只按“一组”做实验）
- `ax2603.12089`：第 V-K 节时间戳的格式与 CA 备案流程
- `ax2608.06795`：the magnitude definition of a_{m,t}(x): which norm, and whether the alpha/r scaling of Eq (1) is included
- `ax2608.06795`：which submodules their activation capture hooks (PEFT naming and adapter-active state) and whether the setup forward runs on base+adapter or base only
- `ax2608.06795`：the sampling of the 40 Alpaca prompts (subset, seed, dedup, length distribution) and whether they are redrawn per adapter
- `ax2608.06795`：the rounding rule for |M_k|, the sigma estimator (ddof), and whether bd_k is multiplied by 1.4826
- `ax2608.06795`：how a single prompt's statistics are isolated under continuous batching and how over-long prompts are truncated
- `ax2609.37367`：ICLSCAN's exact prompt format, which the paper says it reuses but does not reproduce (the whole probe and movability construction depends on it)
- `ax2609.37367`：the complete list of the 18 refusal phrases (the text quotes 3) and whether anything beyond lower-casing (punctuation or Unicode normalisation) is applied
- `ax2609.37367`：the trigger word list of Appendix C and the seed values for the probe pool, the prompt draws and the harvest draws (only the code release has them)
- `ax2609.37367`：the span enumeration rule and the complete rule for the nested-family greedy when spans partially overlap rather than nest
- `ax2609.37367`：whether Delta_i(theta_i, y) is cached across the candidates of one round
- `ax2609.37367`：whether the Stage 1a probe prompts and the movability prompt pairs are the same P prompts, since Appendix A.2 fixes them only within a round
- `huang2024antidote`：A_j(x, w) 究竟取哪个模块（attention 的 q/k/v/o 还是 MLP）、取层输入还是输出、序列维如何归约、padding 是否计入（Appendix A.1 只给了造监督数据的 Alpaca 模板，没说算激活时是否用同一模板）
- `huang2024antidote`：ArgTopK_α 是全局还是逐层/逐输出行：抽取文本未说明，而 Wanda 原方法逐层，直接改变掩码落点
- `huang2024antidote`：候选坐标集合是否只含线性层权重，是否含 embedding/LayerNorm/bias；以及 double LoRA 下剪的是基座权重、某个适配器还是 merge 后的权重（若 merge，如何拆回）
- `huang2024antidote`：Appendix A.1 的训练侧超参自相矛盾（"LoRA alpha set to 4"、"learning rate is set to be 5" 与正文 1e-3 / 1e-4）；Antidote 本身只用 α 与 |D_realign|，但复现整条流程需要核对
- `huang2024antidote`：Table 11 的 α 消融所用的数据集与 backbone：抽取文本未给，无法判断其数值与正文表格的差异来源
- `huang2024booster`：对齐/有害数据集的构造与划分脚本（BeaverTails 扩充版；论文只给 HF 入口 anonymous4486/repnoise_beavertail）。
- `huang2024booster`：两个 batch 的采样实现：是否放回、是否打乱、随机种子与数据顺序，论文未说明。
- `huang2024booster`：h(w) 的 label masking 与损失归约实现（是否只对 response token 求交叉熵）。
- `huang2024booster`：‖∇̃h(w_t)‖ 的范数作用域与扰动实际覆盖的参数集合（是否只 LoRA）。
- `huang2024booster`：Vaccine+Booster 的 ρ 取值与 Algorithm 2 的实现细节（论文未给该变体的 ρ）。
- `huang2024booster`：式 (3) 与 AdamW 组合的实现细节（g̃ 是否被直接交给优化器）。
- `huang2024vaccine`：whether the reference implementation keeps embedding gradients with retain_graph or with two independent forward passes, and its numerical guard when the gradient norm is zero (dictates whether a future interface needs graph retention or just a repeatable forward)
- `huang2024vaccine`：whether the perturbation is applied to attention-only modules or to every block output, and whether it covers all token positions and hidden dimensions (decides which module outputs an interface would have to expose)
- `huang2024vaccine`：the default rho and the intended way to select it, absent from Section 5.1
- `huang2024vaccine`：whether the alignment and fine-tuning adapters are the same object or two, given the conflict between 4.2 and Appendix B.1
- `inan2023llamaguard`：the verbatim guideline text, the instruction template and the output-format wording of Section 3.1, which the extracted text does not preserve
- `inan2023llamaguard`：the released tokenizer and the token ids of safe and unsafe, to confirm that both are single tokens as the paper asserts and that the first-token reading is well defined
- `inan2023llamaguard`：the decoding procedure of the released model for the violated-category list (greedy, beam, or constrained to legal category tokens)
- `inan2023llamaguard`：the thresholds and operating points used in the deployment the paper describes, since the paper gives none
- `inan2023llamaguard`：how the few-shot examples were selected and ordered, beyond the statement that safe ones are hard negatives and 2 to 4 per category are used
- `rieger2022deepsight`：HDBSCAN 的具体超参数（min_cluster_size、min_samples）以及噪声点在 PCI 里算不算一个簇、怎么投票
- `rieger2022deepsight`：随机输入向量的分布、维度 input_dim 的来源，以及 3 个种子是否跨轮固定
- `rieger2022deepsight`：DDif 除法在 f(s_m; G_t)_i 为 0 或接近 0 时的数值保护（论文完全没提）
- `rieger2022deepsight`：式 (8) 分母求和范围（抽取文本印作 j=0..P，与神经元编号 1..P 冲突）与式 (7) 权重求和起点
- `rieger2022deepsight`：“最后一轮”的界定、被过滤模型在末轮按簇聚合时如何参与、被过滤客户端收到哪个模型
- `rieger2022deepsight`：裁剪边界 S 的确切集合（含不含被剔除簇）以及式 (12) 缩放后的模型显式写法
- `rieger2022deepsight`：参考实现：TE 与中位数的并列处理、聚类为空/单簇/簇大小为 1 时的行为，只有拿到作者代码才能确定；本次没有对照作者代码或数据做任何数值复现
- `rosati2024repnoise`：the MMD kernel count, bandwidths and estimator, and how many representation vectors per layer enter it: absent from the paper and from the code release that the checklist postpones.
- `rosati2024repnoise`：how MASK is applied to the losses, and how the batch-level intersection is formed.
- `rosati2024repnoise`：which binding of alpha and beta the released code uses, given the three-way contradiction in the paper.
- `rosati2024repnoise`：whether the per-layer language-model logits are detached, and whether every layer shares the final head.
- `rosati2024repnoise`：the optimizer details behind the reported runs (gradient accumulation, clipping, the 4-GPU placement) that would be needed to reproduce the reported 1:52 and 26.37 GB per card.
- `rosati2024repnoise`：the exact pairing and sampling of the 10k pairs (with or without replacement, and the source split).
- `shen2024seal`：同一条数据在打乱/重打包后与 ω 坐标的对应关系（论文按 D 中的位置排名，没有定义持久样本 ID），以及能否用文本 hash 代替。
- `shen2024seal`：∇σ_j(ω_k) 的语义：softmax 下 ∂σ_j/∂ω 是稠密 N 维，是更新全部坐标还是只更新第 j 个（论文只说 coordinate-wise weighted descent）。
- `shen2024seal`：每 epoch 的迭代数与总步数 K、batch 64 里 D_safe 与 D 的配比、ω 的梯度是否在 batch 内平均或累积。
- `shen2024seal`：ℓ 的精确口径：哪些 token 计损失、prompt 模板、最大序列长度、是否 packing、长度归一化分母是否含特殊 token。
- `shen2024seal`：ω 的初始化方式与是否需要归一化/正则（softmax 对 ω 的常数平移不变，ω 不可辨识）。
- `shen2024seal`：Algorithm 1 第 5 行的权重写成 σ_i(ω_k) 而损失用 z_j，作者原意是哪个下标。
- `shen2024seal`：γ 从 0 开始与 Algorithm 1 的 γ_k ∈ (0,1) 字面冲突；γ 的上限以及每 epoch 是覆盖赋值还是累加。
- `shen2024seal`：损失 gap 未裁剪/归一化而 α_k 固定，作者代码里是否有数值稳定处理。
- `shen2024seal`：排序并列与 p%·N 非整数时的取整规则（Section 3.3 只写 top p%）。
- `tamirisa2024tar`：熵损失的实现：token 位置、词表分布、归约方式，文字无法确定，只有代码能。
- `tamirisa2024tar`：直线估计器在实现里怎么接：是否仍循环 K 次、哪些坐标参与、g_TR 的实际归一化。
- `tamirisa2024tar`：Random Mapping 的 rand_hashed 参考实现：如何为每个 token 在每层残差流索引生成固定高斯向量、向量维度、与 hidden 维度的对齐。
- `tamirisa2024tar`：拒绝设置 DPO 的 β、chosen/rejected 的改写脚本，以及参考 log-prob 的预计算细节。
- `tamirisa2024tar`：外层 D_TR 与 D_retain 的 batch size 与每步采样数（论文两处都未给）。
- `tamirisa2024tar`：A_train 的代码化配置（含私有化学安全数据），以及 β(6.0, 3.0) 切换点的采样语义。
- `tamirisa2024tar`：100 步良性 SFT 的超参数。
- `tamirisa2024tar`：式 3 的绝对值记号是否为论文原意。
- `xie2024gradsafe`：standard loss 的确切定义：是否只在回复 token 上算、是否按 token 平均、label shift 与 batch size（论文只说 standard loss）
- `xie2024gradsafe`：参考提示是否也套第 4.1.4 节那段 system prompt 模板（Figure 2 像套了，正文与附录只给裸文本）
- `xie2024gradsafe`：切片集合对参数的覆盖：embedding / lm_head 是否纳入、1 维参数怎么处理、行列切片如何枚举（2,498,560 这个数要代码才能对上）
- `xie2024gradsafe`：0.25 阈值的校准方式（验证集？分位数？）——换模型或换参考提示后必须重标
- `xie2024gradsafe`：GradSafe-Adapt 逻辑回归的全部细节：正则化、是否标准化、类别不平衡处理、迭代次数、二值阈值
- `xie2024gradsafe`：能复现 Table 1 的 11.78% / 3.53% 选择比例与 Table 7 对齐依赖的识别与评测代码

## 没通过检查的

- `ax2402.12168`（failed）：无错误信息
- `ax2510.16830`（failed）：tests failed:
....F
=================================== FAILURES ===================================
____________ test_gate_excludes_a_tainted_client_and_keeps_the_rest ____________
test_port.py:76: in test_gate_excludes_a_tainted_client_and_keeps_the_rest
    assert sorted(kept) == [0, 1, 3]
E   assert [] == [0, 1, 3]
E     
E     Right contains 3 more items, first extra item: 0
E     Use -v to g
- `gao2019strip`（failed）：无错误信息
