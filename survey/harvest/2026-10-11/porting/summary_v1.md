# 移植成本：DeepSeek 按 GUIDE.md 移植的结果

由 `run_port.py --summary` 生成。每行一篇论文；代码由 DeepSeek 写，检查在 legion 上执行（断网、仅 CPU、限时限内存）。
“通过”只表示：能导入、契约成立、类说明有规定的小节、它自己写的机制测试通过。**不表示与原论文的实现等价**，也没有人工审过代码。

| 论文 | 状态 | 自评结论 | 轮数 | 新词元（输入+输出） | 秒 | 插件 | 位置 | 资源 | 插件行数 | 步骤（移植/总数/不属于插件） | 新辅助函数 | 缺的算子 | 缺的运行时能力 | 需向作者确认 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ax2210.07714` | passed | partial | 1 | 215,350 | 621 | `crowdguard` | server_aggregate | validation_set | 380 | 13/16/2 | 7 | 2 | 4 | 10 |
| `ax2301.09508` | passed | partial | 1 | 215,632 | 550 | `baybfed` | server_aggregate、server_post_aggregate | — | 167 | 13/14/1 | 2 | 2 | 0 | 4 |
| `ax2305.05506` | passed | partial | 1 | 211,059 | 567 | `fedgt` | server_aggregate | assignment、delta_table、null_distribution、validation | 235 | 16/23/6 | 2 | 2 | 4 | 4 |
| `ax2411.17453` | passed | partial | 1 | 167,568 | 386 | `peftguard` | server_aggregate、server_receive | meta_classifier | 179 | 5/11/6 | 2 | 0 | 2 | 3 |
| `ax2608.06795` | passed | not_expressible | 2 | 130,634 | 240 | `lorascan` | server_receive | — | 94 | 0/7/3 | 0 | 2 | 5 | 5 |
| `ax2609.37367` | passed | partial | 1 | 199,294 | 602 | `chorus` | server_aggregate、server_receive | probe_pool、refusal_phrases、trigger_words | 323 | 12/17/3 | 7 | 0 | 5 | 6 |
| `huang2024vaccine` | failed | not_expressible | 2 | 161,705 | 243 | `vaccine` | server_distribute | alignment_data | 109 | 0/9/3 | 0 | 3 | 5 | 6 |
| `rieger2022deepsight` | passed | partial | 1 | 221,299 | 626 | `deepsight` | server_aggregate、server_distribute、server_post_aggregate、server_receive | suspicious_labels | 185 | 8/15/1 | 3 | 2 | 3 | 3 |
| `shen2024seal` | passed | partial | 1 | 141,454 | 333 | `seal_top_percent` | client_pre_train | selector_scores | 102 | 2/13/11 | 1 | 1 | 6 | 8 |
| `xie2024gradsafe` | not_expressible | not_expressible | 2 | 184,104 | 350 | `gradsafe` | client_pre_train | aligned_base_model、logistic_probe、unsafe_gradient_reference | 114 | 0/10/3 | 0 | 2 | 5 | 7 |

合计 10 篇，其中 10 篇实际调用了 DeepSeek，共 13 次：新词元（输入+输出）1,848,099，平均每篇 184,809；另有缓存读取 25,192,576（会话每一步都从缓存重读提示）。

## 缺的运行时能力（逐篇自报）

- `ax2210.07714`：no client-side stage after SERVER_RECEIVE and no way to move this round uploads to a client: every client stage runs before the uploads exist, the only two-way exchange (CLIENT_ANNOUNCE / SERVER_EXCHANGE) happens before local training, a server outbox is carried with the next round broadcast, and the channel cannot hold n LoRA states anyway (messages <= 64 KiB, attachments are one flat tensor dict <= 64 MiB)（卡住：S3, and with it the paper placement of the validation (S4-S13) inside the client enclaves; votes produced in the next round would be about last round models, so the round-independent filtering before aggregation cannot be scheduled）
- `ax2210.07714`：data is a client-side kind and sample labels are not a kind at all: DataView exposes hashes, source tags and lengths and its raw samples are opaque, so the server can read no client validation set（卡住：S4 and S7 on the server unless the deployment hands in a labelled set as a resource, which this port does）
- `ax2210.07714`：the server-side model_handle is optional and the shipped server adapter offers ProbeView.score only (OpenFedLLMGuard(probe=...), HFProbe); the lora() and activations() of ModelHandle are not part of it, and a default server has no model（卡住：S4 in every deployment that does not supply a full server-side ModelHandle; without one the plugin records a LookupError）
- `ax2210.07714`：no attestation, enclave or secure-memory notion exists in the library（卡住：S1 (outside the plugin anyway); the paper threat model (the server sees neither client data nor honest votes) is not enforceable here）
- `ax2305.05506`：no data kind for the m secure group aggregates. A server plugin that declares `uploads` sees every per-client LoRA in the clear, and a deployment that hides them (RunSpec.unavailable={'uploads'}) refuses the plugin before the first round.（卡住：R3, and with it the setting the paper is about. The port has to build the group aggregates itself from cleartext uploads, so it can only run where secure aggregation is off, which is the opposite of the paper's deployment.）
- `ax2305.05506`：the server side has no runnable model by default (OpenFedLLMGuard mounts a model handle only when a probe is passed) and the ModelHandle protocol has no prediction or label call.（卡住：R4 as the paper defines it: source-label recall, top-1 accuracy and balanced accuracy cannot be computed at all. The port substitutes the negative mean training loss on the defender validation set.）
- `ax2305.05506`：ModelHandle.lora(state) takes a LoRA state dict of the broadcast rank, while a group aggregate is a sum of k rank-r LoRA products of rank <= k*r and has no such state dict.（卡住：R4 and R5 in their exact form: the model pass and the principal component are taken on the factor-wise sum of the members, whose product is not the sum of their products.）
- `ax2305.05506`：harness.server_guard cannot mount a server-side model handle: OpenFedLLMGuard takes probe=..., but server_guard does not expose it.（卡住：nothing in the method, only the test: it builds the guard from harness.OpenFedLLMGuard + harness.GuardRunner instead of server_guard.）
- `ax2411.17453`：跨轮保留、按适配器的处置动作（标记/隔离/下架）；服务器侧动作都是一轮内的（select_and_weight 排除、transform_update 替换）（卡住：论文故事里平台那一半；检测本身能完整跑，但在联邦轮里判定只能表现为本轮不聚合该上传者）
- `ax2411.17453`：对模型模块结构的运行时视图（层号、模块角色）；上传的状态字典里只有字符串键（卡住：宿主命名里没有数字层号或 q/v 记号时，公式 (14) 的 (2L,d,k) 布局排不出来，步骤 3-4 只能退化成按字符串顺序堆叠）
- `ax2608.06795`：没有服务/推理位置：STAGE_KINDS 的十个位置（SERVER_DISTRIBUTE ... CLIENT_POST_TRAIN）全部落在一轮联邦训练之内，插件无法在「部署后、生成之前、逐提示」被调用；论文 JSON 自己把方法标为 outside_training。（卡住：步骤 1、2、5、7 —— 没有任何调用时刻，插件根本不会被 run）
- `ax2608.06795`：没有提示级拒绝动作：ACTION_STAGES 里 mask_samples/edit_samples（CLIENT_PRE_TRAIN）只改本轮本地训练样本，select_and_weight/replace_global 改的是聚合，transform_* 改的是广播/接收/损失/梯度/更新；没有「拒绝这条生成请求」的动作。（卡住：步骤 7 —— 判定即使算出来也无处落地；把提示拒绝映射成 Decision.excluded 会变成另一种方法（论文正是为了不丢弃整个适配器才做逐提示拒绝））
- `ax2608.06795`：ModelHandle 不暴露逐 token 激活：hidden/activations 只返回每样本一个池化向量（last/mean），没有 max 池化，也没有模块输入的 token 维度。（卡住：步骤 1、2、5 —— s_m(x) = M_m(x) * log(1 + M_m(x) / abar_m(x)) 里的 M_m = max_t a_{m,t} 无从取得）
- `ax2608.06795`：没有承载服务期提示的数据类别：data 是客户端本地训练样本，loss/gradients/train_trace 是训练步内的量，reports/attachments 是跨侧通道。（卡住：步骤 1、2、5、7 —— 检测对象（用户提示）进不来，也没有「一条提示一次调用」的形状）
- `ax2608.06795`：标定没有可用的插件内时刻：GuardPlugin.setup(spec) 只收到 RunSpec，没有 ctx、model_handle 或 resources；推迟到第一次 run() 也不行，因为那时仍缺逐 token 激活与提示。（卡住：步骤 3、4、6 —— 用 40 条干净提示做的一次性标定只能在库外完成，产物作为 resources 传入）
- `ax2609.37367`：一个 upload 没有共同接收者，也没有接收者之间的通道。SERVER_RECEIVE 上每个 upload 只有一个接收者（服务器），R_j = {i}，没有对象可以跑 EXCHANGESCORES 与 EXCHANGESTRINGS；池化集合 V_j、C_j 只能是接收者自己的值。库里的消息通道（messages/attachments、CLIENT_ANNOUNCE + SERVER_EXCHANGE）是客户端↔服务器、只传小记录，连不到“同一个适配器的其它接收者”，而星形拓扑里根本不存在这种角色。（卡住：步骤 8（交换探针分数）与步骤 11（交换候选字符串）完全做不了；步骤 9 的严格多数投票只能以 |R_j|=1 调用，退化为“自己一个分数过 η 就拒绝”，论文靠池化得到的抗串通/抗单点误判没有移植过来。这也是 17 步里 12 移植 + 3 不属于插件之后剩下的 2 步。）
- `ax2609.37367`：ModelHandle.generate(prompts, max_new_tokens) 只有贪心解码：没有 beam search、没有 length penalty/early stopping，也没有探针要的 temperature/top-p/top-k。（卡住：步骤 10 的 H 条采集生成拿不到论文的 B=16 beam（只取最高分 beam），步骤 7 的探针采样也退化成贪心。论文报告 beam search 在 51.6% 的 prompt 上恢复攻击者目标串而采样只有 13.5%，所以第 10 步的召回率达不到论文值。）
- `ax2609.37367`：服务器一侧默认没有可运行的模型：SERVER_RECEIVE 只有在部署把 probe= 传给 OpenFedLLMGuard 时才有 model_handle，且仓库自带的服务器端句柄 fedguard.adapters.hf_probe.HFProbe 只实现 ProbeView.score，没有 generate 与 logprob。（卡住：默认部署下步骤 7、10、13（探针生成、采集生成、可移动性打分）全部做不了；插件因此声明 needs={"uploads","model_handle"}，要求部署提供一个完整 ModelHandle（如 HFModelHandle 包住基座模型）。）
- `ax2609.37367`：服务器不持有“节点自己这一轮的适配器” θ_i，没有任何数据类别对应它（客户端侧的 local_update 到不了服务器）。（卡住：步骤 12-14 的可移动性参照只能用本轮广播基座 uploads.base_state()，见 deviations；论文的 θ_i 是诚实节点自己本地训练出来的干净模型。）
- `ax2609.37367`：测试侧的 harness.server_guard 不传 probe（harness.server_round 因此无法驱动任何声明 model_handle 的服务器插件）。（卡住：不影响插件本身，但移植时必须在测试里自建 OpenFedLLMGuard(GuardRunner(...), probe=...) 并重写一遍 server_round 的聚合循环（见 test_port.py 的 _guard/_round）。）
- `huang2024vaccine`：A server-side training stage, or a pre-round alignment hook, in which a plugin can run optimizer steps over defender data on the model.（卡住：steps 1, 2, 6, 7, 8 -- the alignment loop as a whole. The server stages are aggregation-time trust boundaries (distribute, exchange, receive, aggregate, post-aggregate), and setup(spec) runs once but gets only a RunSpec, no model and no data.）
- `huang2024vaccine`：Layer-level access to the host model under autograd: submodule outputs with their graph, dL/d(activation), and hook registration or an equivalent activation-injection call. (The server also has no runnable model by default, so even the forward passes may be unavailable: server-side model_handle is optional.)（卡住：steps 2-6 -- building the perturbation and injecting it, i.e. the core of Vaccine.）
- `huang2024vaccine`：A gradient view usable where the method runs, plus an optimizer to consume it.（卡住：steps 6-7 -- GradientView is client-side (CLIENT_PRE_STEP) and covers a client's own parameters; the server never sees a gradient.）
- `huang2024vaccine`：A server-side data kind and a sample/batch view ('data' is client-only in KIND_SIDE).（卡住：step 1 -- the alignment corpus can only arrive as a resource, and nothing defines a training batch on the server.）
- `huang2024vaccine`：A pre-round way to install a trained model as the run's starting global state; only per-round replacements exist (transform_broadcast at SERVER_DISTRIBUTE, replace_global at SERVER_POST_AGGREGATE).（卡住：step 9 and the method's premise -- the aligned model is the starting point for user fine-tuning, not an in-round correction.）
- `rieger2022deepsight`：冻结基座模型的输出层本身（偏置 b、连到上一层的权重行 w）以及输出类别数 P（卡住：步骤 1、3、4、5（输出层偏置增量、NEUPs、Threshold Exceedings、中位数分类）全部做不了：LoRA 状态字典里只有被适配模块的 lora_A/lora_B，更新里没有输出层，服务器也没有模型可读。）
- `rieger2022deepsight`：服务器侧可运行的模型，以及一个返回输出概率的前向接口（卡住：步骤 6、7（随机探针前向、DDifs）：论文每客户端每轮要 3×20000 次前向，这个运行时一次也花不出去（服务器侧适配器默认不给 model_handle，ModelHandle 也没有概率接口）。）
- `rieger2022deepsight`：论文自己的逐模型判定（suspicious/benign）（卡住：步骤 12 的输入：PCI 本身实现了，但只能吃 `suspicious_labels` 资源；没有真正的检测层时它永远不剔除任何客户端，过滤层等于不存在。）
- `shen2024seal`：STAGE_KINDS 的十个位置全部在训练轮内，没有代表 S1–S3 的轮外/离线位置（论文自己把方法标为 outside_training）（卡住：选择器训练（S2）整段没有挂载点；它是方法的核心贡献，本移植只搬了它产出的选择决定）
- `shen2024seal`：插件不拥有训练循环：不能决定下一步用哪条数据、不能自己步进模型参数、不能把 D_safe 的样本与当前微调样本配对（卡住：公式 (4) 的惩罚混合 θ 更新与步骤 5 的配对采样）
- `shen2024seal`：没有被训练模型之外的第二份参数（辅助模型 θ̂）（卡住：公式 (6) 的 θ̂ 更新，以及 Algorithm 1 依赖它的公式 (5) 损失 gap 更新）
- `shen2024seal`：CLIENT_LOSS / CLIENT_PRE_STEP 的批次没有样本身份（index/hash），manifest 与 batch 之间没有映射（卡住：公式 (8)（论文默认的记忆高效变体）：库能给出 ℓ(θ_k;z_j)，但给不出 j，ω_j 无法更新）
- `shen2024seal`：没有 D_safe 这类数据 kind，也没有在训练步里注入另一批数据的机制（loss_on 只是一次前向，配对与调度都在库外）（卡住：上层安全损失 (1/M)Σℓ(θ;z_i^safe) 与公式 (4) 的第一项）
- `shen2024seal`：没有跨客户端的样本视图（服务端只有上传、reports 与 messages）（卡住：在完整 D 上取全局 top p%（S3 的字面语义）；只能退化为按客户端、按轮各自截断）
- `xie2024gradsafe`：a gradient of a loss with respect to the frozen base LLM's weight matrices (dL/dW_base)（卡住：step 2 (loss_gradient_wrt_params) and through it steps 3, 7, 8, 9a, 9b - the entire detection. Every gradient interface is trainable-scoped: GradientView keeps only parameters with requires_grad and a gradient; model_handle.parameters(group) returns the trainable parameters of a group (PARAM_GROUPS has no base-weight group) or those passing a predicate, and the shipped adapter narrows names to those containing lora_ before applying the predicate; per_sample_gradients takes its parameters from that call; LossView.gradients_of is with respect to the trainable parameters whose name passes select.）
- `xie2024gradsafe`：a differentiable loss on a constructed (prompt, response) pair（卡住：the forward half of step 2 for arbitrary prompt text: logprob returns floats, losses is forward only, and LossView.loss_on keeps a graph but only at CLIENT_LOSS and only for a host-format batch that a plugin cannot build without a tokenizer.）
- `xie2024gradsafe`：the identity and 2-D shape of the base weight matrices, in a stable index order（卡住：steps 3, 7 and 8 even if the gradient existed: layout returns LoRA state-dict keys and shapes, so a stored reference slice has no address.）
- `xie2024gradsafe`：prompt text on the server side（卡住：the paper's second federated mount (server_receive): KIND_SIDE assigns `data` to the client, and the server stages never expose samples, so a server-side GradSafe could only act on per-sample scores sent over the channel - and the client cannot compute them either.）
- `xie2024gradsafe`：a runnable model on the server, and any server-side interface that takes a prompt rather than a LoRA（卡住：every server-side variant: the library's premise is that the server has no runnable model by default, and the one server-side model interface (ProbeView.score) scores a candidate LoRA, not a prompt.）

## 提取接口：方法要从训练里取什么，库给不给得出

只有按新版说明（含 `extraction_needs`）移植的论文有这一项。

| 论文 | 数据 | 何时何侧 | 库是否提供 | 经由 / 缺什么 |
|---|---|---|---|---|
| `ax2411.17453` | 每个客户端上传的 LoRA 因子 A、B（全部被适配模块） | 服务器侧，SERVER_RECEIVE（SERVER_AGGREGATE 复用同一次读数） | yes | ctx.uploads（UploadView）：clients、state(cid)、factors(cid,module)、cumulative(cid,module) |
| `ax2411.17453` | 把 BA 变成公式 (6) 权重增量的适配器缩放 alpha/r | 服务器侧，同上 | yes | RunSpec.lora_scale；runner 用它构造 UploadView，cumulative()/increment() 返回的已经是缩放后的量 |
| `ax2411.17453` | 模块到层的归属、模块是 query 还是 value（公式 (13)(14) 的通道顺序） | 服务器侧，同上 | partly | 唯一来源是 ctx.uploads.state(cid) 的键：模块路径是字符串（如 ...layers.0.self_attn.q_proj.lora_A.weight）。库里没有层号、没有模块角色，插件自己解析路径（module_rank）；名字里没有数字层号或 q/v 记号时排不出论文的 (2L) 结构，只能按字符串顺序堆叠 |
| `ax2411.17453` | 训练好的元分类器 PEFTGuard_cls 及其输入约定 | 训练之外（离线准备），SERVER_RECEIVE 使用 | no | 库里没有任何构建/保存/加载它的东西，只能以 resources={'meta_classifier'} 传入并用 ctx.resource 调用；论文既没给结构也没给代码，防御方必须自备作者实现或自行重训 |
| `ax2411.17453` | 判定为 1 之后平台对适配器的处置（拒收/下架/隔离） | 服务器侧，判定之后 | partly | 服务器侧动作只在一轮内有效：select_and_weight 的 Decision.excluded 把上传者从本轮聚合里去掉，transform_update 可以改写这份上传；没有跨轮保留的按适配器标记 |
| `ax2411.17453` | 其余一概不需要：没有本地数据、没有探针样本、没有模型前向、没有额外往返 | — | yes | 插件只声明 needs={'uploads'}、不声明 model_handle；这与论文只用适配器参数的设定一致，也是它最省的一环 |
| `ax2608.06795` | 可疑适配器的插入点集合 M（哪些模块带 LoRA 附着）与每个插入点的下投影矩阵 A_m | 收到第三方适配器时（服务器侧的上传，或客户端收到的模型），标定与每次检测都要用 | yes | UploadView.factors(cid, module) / UploadView.state(cid) 给出 ...lora_A.weight；站点清单可以从 state 的 lora_A/lora_B 键自行归并，或从 ModelHandle.layout() 的 LoRA 键读出。注意 fedguard.views.uploads.lora_modules 正好做这件事，但规则 5 的允许导入清单里没有 views，移植时要在插件文件里另写几行（本可记为一个 new_helper）。 |
| `ax2608.06795` | 每个插入点、每个提示 token 位置的模块输入隐状态 h_{m,t} | 推理时那一次前向之内（生成之前）逐 token 取；标定阶段对每条干净提示也一样 | no | 没有接口给出逐 token 的模块输入：ModelHandle.hidden(samples, layer, pool) 只给每条样本一个池化向量（last token 或 mean over tokens），ModelHandle.activations(samples, select, pool) 只给逐子模块的池化输出；两者都没有原始 token 维度，也没有 max 池化。 |
| `ax2608.06795` | 下投影瓶颈的逐 token 激活幅度 a_{m,t}(x)（A_m h_{m,t} 的标量幅度） | 同上，推理时前向内；标定阶段对 40 条干净提示也要 | no | 即使把 select 指到 lora_A 子模块，activations 也只返回逐样本池化值 (n, d)，池化选项没有 max；max_t a_{m,t} 无法从任何返回的均值/末位量恢复。 |
| `ax2608.06795` | 提示的 token 位置集合 T(x)（提示 token 数、特殊 token 与聊天模板是否计入、超长是否截断） | 检测时；标定阶段同理 | no | 插件看不到分词结果：客户端只有 DataView.text(index) 与 SampleRecord.hash/source/length，length 是文本长度而不是 token 位置；模型侧的 token 化完全在 ModelHandle 内部。 |
| `ax2608.06795` | 40 条可信、无标签的干净提示（标定集，来自 Stanford Alpaca） | 部署前一次性标定 | partly | 可以用 resources 声明、由 ctx.resource(name) 读入（形式由防御方决定，库不解释内容）；但插件生命周期里没有跑标定的时刻：setup(spec) 只拿到 RunSpec，没有 ctx、model_handle 或 resources，所以标定只能整体在库外做完，产物作为资源传入。 |
| `ax2608.06795` | 挂载可疑适配器后的前向栈（可信基座 + adapter，且能读中间激活） | 标定与每次检测 | partly | model_handle 在两侧都可以声明，with handle.lora(state): 能挂载任意 LoRA state 并调用 losses/hidden/activations/per_sample_gradients/logprob/generate；缺的是这些 pass 里的逐 token 中间激活（见上一项）。另外服务器一侧默认没有可运行的模型，需要部署方提供模型句柄。 |
| `ax2608.06795` | 待检测的用户提示 x（部署后、生成之前的那一条） | 推理服务路径上，每条提示进生成前一次 | no | STAGE_KINDS 的十个位置全在一轮联邦训练之内；唯一的数据类别 data 是客户端本轮的本地训练样本，没有承载服务期提示的数据类别，也没有逐提示的调用形状。ModelHandle.logprob/generate 接受字符串提示，说明句柄层能处理提示，但插件拿不到待检测提示的入口。 |
| `ax2608.06795` | 标定产物：逐插入点 mu_m、sigma_m（长度 /M/）、被监控插入点集合 M_k、阈值 tau_k | 部署前算一次，之后每次检测复用（per-adapter） | partly | 作为 resources 传入或在 ctx.state 里保存都可以，库不解释资源内容；但库内算不出来，因为需要上面的逐 token 激活与干净提示，而且插件没有可用的标定时刻去跑那 40 次前向。 |
| `huang2024vaccine` | One mini-batch of the provider's safe alignment QA pairs (x_t, y_t) per alignment optimization step | server side, inside the alignment training step, before its first forward pass (pre-deployment, once for all incoming user fine-tuning) | partly | only as a defender resource: ctx.resource('alignment_data'). KIND_SIDE gives 'data' to the client only, the server stages expose no sample/manifest view, and nothing defines a training batch on the server; fedguard.ops.sampling.subsample could pick indices but nothing consumes them. |
| `huang2024vaccine` | The per-layer hidden embeddings e_{l,t} of the model on that batch, all layers L, in the shape of the layer outputs (per token and dimension) | server side, in the first forward pass of the alignment step | no | ModelHandle.hidden(samples, layer) takes one layer and pools it (last/mean) to (n, d) on CPU; ModelHandle.activations(...) pools selected submodule outputs to (n, d). No full per-token activation view exists and neither is usable for a second differentiable pass. |
| `huang2024vaccine` | The gradient of the alignment loss with respect to each layer's hidden embedding, dL/de_l, for all layers | server side, after the first backward of the alignment step | no | the blocker. Every listed gradient interface is parameter-space: GradientView (client, CLIENT_PRE_STEP), LossView.gradients_of(scalar, select) (client, CLIENT_LOSS), ModelHandle.per_sample_gradients(samples, group) (groups such as 'last_lora_B'). The handle has no retain_graph/hook facility and no view returns activation gradients. |
| `huang2024vaccine` | A differentiable alignment loss L_{w_t} on that batch (a scalar carrying a graph) to differentiate | server side, first forward of the alignment step | no | ModelHandle.losses(samples) returns list[float] (forward only, no graph). The only graph-carrying loss in the library is LossView.loss at CLIENT_LOSS, i.e. on a client, over the client's own batch and parameters. |
| `huang2024vaccine` | The gradient at the perturbed point, g_tilde_t, that the alignment optimizer consumes as the model update | server side, after the second forward+backward of the alignment step | no | there is no server-side gradient view at all, and g_tilde is defined at embeddings perturbed by dL/de_l, so it cannot be formed from the parameter-space gradients that do exist. The action the paper's own analysis maps this to, transform_gradients, exists only at CLIENT_PRE_STEP (ACTION_STAGES). |
| `huang2024vaccine` | The optimizer for the alignment step and its state (AdamW moments, lr, weight decay, schedule, step count) that turns g_tilde into w_{t+1} | server side, alignment step, after the second backward | no | no server-side training loop or optimizer handle exists; a plugin never steps the host's optimizer, and setup(spec) receives only a RunSpec. ctx.state is plugin-private bookkeeping and cannot drive training. |
| `huang2024vaccine` | The trainable weights the alignment step starts from (w_t, the LoRA factors being aligned) and the write-back of w_{t+1} | server side, throughout the alignment run | partly | LoRA state dicts are the library's native currency (ClientUpdate.lora, OutgoingView.state(), fedguard.ops.states), and a finished state can be placed in a round via transform_broadcast at SERVER_DISTRIBUTE or replace_global at SERVER_POST_AGGREGATE; what does not exist is a state that is inside an optimization the plugin drives. |
| `huang2024vaccine` | The selection of layers to perturb and the modules the LoRA adapters sit on | server side, when building the perturbation, per step | partly | fedguard.views.uploads.lora_modules(state) and ModelHandle.parameters/layout enumerate the adapted modules of a state dict, so the module set is visible; the paper leaves open whether MLP layers are perturbed too (4.2 vs Algorithm 1), and no interface exposes a module's output to perturb anyway. |
| `huang2024vaccine` | The alignment step counter t for the accelerated variant's refresh rule (t mod tau == 0) | server side, alignment loop, per step | no | ctx.round and ctx.state exist but count federated rounds; there is no alignment loop (and the paper gives no default tau) for such a counter to describe. |
| `shen2024seal` | 本轮该客户端将用于本地训练的样本集合，以及每条样本的身份（顺序、hash、来源、长度） | 客户端，CLIENT_PRE_TRAIN，本地训练开始前 | yes | ctx.data；DataView.manifest 给 index/hash/source/length（样本原文只在客户端，库只记 hash 与长度） |
| `shen2024seal` | 每条样本的选择器分数 σ_i(ω_K) | 由离线 S2 产出，在 CLIENT_PRE_TRAIN 用于截断 | partly | 训练过程里没有位置产出它：库没有选择器、没有 D_safe、没有打分用的前向；按规则 3 由防守方以 resources['selector_scores']（hash → 分数）接入，插件只查表 |
| `shen2024seal` | 样本与选择器坐标的对应关系（论文按 D 中的位置排名，需要 z_i ↔ ω_i） | S2 训练与 S3 打分 | partly | DataView.manifest 提供稳定的样本文本 hash 可作键（Section 4.4 说明选择器绑定数据集而非模型）；但本轮声明的顺序/子集与离线 D 的顺序不保证一致，库不提供数据集版本或离线索引 |
| `shen2024seal` | 当前训练步那批样本的逐样本长度归一化 NLL ℓ(θ_k; z_j)，并且知道它属于哪条样本（公式 (8) 的 ω 更新） | 客户端，CLIENT_LOSS，每个本地步 | partly | LossView.per_sample_losses() 给出批内逐样本 NLL（对已标注 token 平均），但 batch 里没有任何样本身份（index/hash），也无法从 batch 张量反查 manifest，因此 ℓ 无法归属到 ω_j |
| `shen2024seal` | 与 z_j 配对的来自 D_safe 的安全样本 z_i^safe 及其在同一迭代的损失 | S2 训练循环的每个迭代 | no | 没有第二个数据集的 kind（客户端只有一份 data）；插件不拥有循环，无法按迭代投入另一批数据。LossView.loss_on(batch) 只能前向一个资源给出的批次，且需要宿主的 batch 格式与配对调度，二者都不存在 |
| `shen2024seal` | θ 的惩罚混合梯度 (1−γ_k)∇ℓ(θ_k;z_i^safe) + γ_k σ_j(ω_k)∇ℓ(θ_k;z_j) 与步长 β_k（公式 (4)） | S2 每个迭代，客户端训练步内 | partly | LossView.gradients_of() 可对插件构造的标量求梯度，transform_loss / transform_gradients 可替换宿主传播或步进的东西；但步长、优化器与调度属于宿主，插件不能选下一步的数据，β_k 与 γ_k 的调度没有位置表达 |
| `shen2024seal` | 与被训练模型同尺寸的第二份参数 θ̂ 及其梯度（公式 (6)，Algorithm 1） | S2（Algorithm 1） | no | ModelHandle 只在被训练的模型上加载 LoRA（handle.lora）；没有第二份参数、没有优化器、也没有步进参数的方法 |
| `shen2024seal` | 整个微调集 D 上的一次性打分与全局 top p% 截断（S3） | 训练之外，集中式（论文标为 outside_training） | no | 没有任何位置能看到多于一个客户端分片的数据：STAGE_KINDS 的十个位置全在轮内，服务端只见到上传、reports 与 messages，样本文本永不出客户端，没有跨客户端的数据视图 |
| `shen2024seal` | 筛选是否真的生效、哪些样本被丢掉 | 客户端，CLIENT_PRE_TRAIN 之后、本地训练之前 | yes | mask_samples 动作 + ClientGuard.kept_indices() / training_samples()；记录里只有 hash，没有原文 |
| `xie2024gradsafe` | the text of every prompt to be screened, one string per sample | client side, opening of the round: CLIENT_ANNOUNCE or CLIENT_PRE_TRAIN | yes | the `data` kind: DataView.samples() and DataView.text(index), with DataView.manifest for the sample hashes; `data` is a client-side kind (KIND_SIDE) and both stages expose it (STAGE_KINDS). |
| `xie2024gradsafe` | the paper's second federated mount: the prompts on the server before they enter training (server_receive) | server side, SERVER_RECEIVE / SERVER_EXCHANGE | no | the server never sees sample text: KIND_SIDE puts `data` on the client only, and the server stages expose reports / model_handle / history (plus uploads and aggregate at the aggregate stages). The only server-side trace of a prompt would be a per-sample score sent over the channel (messages / attachments, unverified) - and the client cannot compute one either. |
| `xie2024gradsafe` | a tokenizer, or any way for a plugin to turn a prompt string into a batch in the host's own format | client side, wherever the model is | no | nothing in the reference converts text into model input at the plugin level; a handle tokenizes internally for the methods it offers (its text_of / split_of are fixed by the deployer when the handle is built, not chosen by the plugin). Without a batch dict, LossView.loss_on(batch) cannot be called. |
| `xie2024gradsafe` | a differentiable loss of the constructed (prompt, `Sure`) pair on the aligned base LLM (the paper's standard loss) | client side, on the side that holds the base model | partly | model_handle.logprob(prompts, targets) matches the pairing semantically but returns floats with no graph; ModelHandle.losses(samples) is forward only; LossView.loss_on(batch) does keep a graph but exists only at CLIENT_LOSS (the trainer extension layer, which a plain Trainer callback never reaches) and expects a host-format batch - see the tokenizer item. |
| `xie2024gradsafe` | dL/dW for every 2-D weight matrix of the frozen base LLM: the gradient the whole method is built on | client side, wherever the aligned base model lives | no | every gradient interface is scoped to trainable parameters. GradientView keeps only parameters with requires_grad and a gradient; model_handle.parameters(group) is documented as the trainable parameters of a group (PARAM_GROUPS is lora / lora_A / lora_B / last_lora_B / first_lora_B, with no base-weight group) or passing a predicate, and the shipped adapter narrows candidate names to those containing lora_ before applying the predicate, so a predicate cannot reach a frozen base weight; per_sample_gradients takes its parameter list from that same call; LossView.gradients_of is with respect to the trainable parameters whose name passes select. |
| `xie2024gradsafe` | the identity and the 2-D shape of each base weight matrix, in a stable slice order, so a stored reference slice can be matched | client side | no | model_handle.layout(group) returns LoRA state-dict keys and shapes in the order gradients are concatenated; fedguard.ops.states.flatten / unflatten / stack work on LoRA state dicts too. Even if the gradient item were solved, a reference slice would have no address. |
| `xie2024gradsafe` | the offline Phase I-III artifact: the safety-critical slice index set S at gap threshold 1 and the stored unsafe reference slice for each i in S | outside the run, before the first round (the paper's own words: one-off preparation, unrelated to any federated round) | yes | `resources` -> ctx.resource(name), which is what the resource mechanism is for. The paper reports only percentages (11.78% of row slices, 3.53% of column slices at threshold 1, Table 1), so size and serialization are the defender's business. |
| `xie2024gradsafe` | GradSafe-Adapt: the fitted logistic probe over /S/-dimensional cosine features | outside the run (the paper's offline domain adaptation on the ToxicChat train split) | yes | `resources` plus fedguard.ops.probe.apply_logistic(probe, X); fedguard.ops.probe.fit_logistic builds exactly the weight / bias / mean / scale dict that can be carried as a resource. |
| `xie2024gradsafe` | GradSafe-Adapt: labelled target-domain prompts, and a route for the labels to the side that fits the probe | outside the run; in a federation the labels sit with the clients | partly | the only cross-side path is the channel (messages for small records, attachments for tensors, both unverified) and there is no cross-client data sharing; the paper does not say how labels are gathered, so a per-client offline fit or a defender-side labelled set are the only shapes the library supports. |
| `xie2024gradsafe` | the action that follows a detection: screening a harmful prompt out before it enters training | client side, CLIENT_PRE_TRAIN | yes | `mask_samples` (permitted at CLIENT_PRE_TRAIN only) with proposals = {mask: iterable of sample hashes}; DataView.manifest supplies SampleRecord.hash and ClientGuard.kept_indices() / training_samples() apply it. This also fixes the mount. |
| `xie2024gradsafe` | one forward and one backward pass of the aligned 7B base model per screened prompt | client side, inside the plugin invocation | partly | `model_handle` grants model passes and ModelHandle counts them in `cost`; per_sample_gradients does one backward per sample and gradients_of one per call. The passes exist; the object they would have to be taken against (the frozen base weights) is what is missing - see missing_runtime. |

## 要在库外维护或准备的状态

- `ax2411.17453`：训练好的元分类器（权重 + 结构 + 输入约定：通道顺序、目标模块、归一化、d、k）
- `ax2411.17453`：训练它用的带标签适配器集合（论文 PADBench：每配置 250 良性 + 250 后门，共 13,300 个）以及生成这些适配器的 PEFT 微调算力与底座 LLM
- `ax2411.17453`：论文第 7 节要求输入维度一变就重训分类器，所以底座模型与目标模块集合也是库外状态
- `ax2411.17453`：可选且本次未实现：跨攻击做对比学习 + 参数平均用的 3 个分类器；Fine-mixing 缓解用的干净预训练权重与每类 2,500 句干净数据
- `ax2608.06795`：可疑 LoRA 适配器权重（白盒）与其可信基座模型，加上能读取插入点中间激活的推理/服务栈
- `ax2608.06795`：40 条来自 Stanford Alpaca 的可信无标签干净提示（标定集；论文未说明抽样细节）
- `ax2608.06795`：每个适配器一份的标定产物：mu_m、sigma_m 向量（长度 |M|）、被监控插入点索引集合 M_k、阈值 tau_k
- `ax2608.06795`：服务期逐提示的中间激活表与判定日志（论文的检测逐提示独立、不跨轮累积，所以不需要历史状态）
- `huang2024vaccine`：The provider's safe alignment QA corpus {x_i, y_i} (paper: 2000 BeaverTails harmful-prompt / safe-output pairs) -- the `alignment_data` resource.
- `huang2024vaccine`：The pretrained base LLM and the alignment LoRA adapter (rank 8, dropout 0.1), plus the PEFT merge that folds it into the base; the library only ever sees LoRA state dicts.
- `huang2024vaccine`：The alignment trainer itself: T steps over 50 epochs, batch 5, AdamW (lr 1e-3, weight decay 0.1, cosine decay, warmup 0.1), and the accelerated variant's tau schedule. Vaccine modifies this loop, and it lives outside the library.
- `huang2024vaccine`：Per-step transients inside that loop: the per-layer eps_l tensors (same shapes as the hidden states) and the forward-hook registry for the second pass (paper: +0.039 to +0.11 GB).
- `huang2024vaccine`：The run's initial global model: in fedguard the framework owns it, so an aligned starting model can only be prepared outside and handed in.
- `huang2024vaccine`：Evaluation-only assets, not part of the defence run: the BeaverTails moderation model, 500 harmful test instructions, and the 500/200 task instruction-label pairs.
- `shen2024seal`：训练好的选择器 ω_K ∈ R^N，或等价的 {样本 hash → σ_i(ω_K)} 分数表（本插件的 resources['selector_scores']），随数据集版本缓存（Section 4.4 说明选择器不绑定模型）
- `shen2024seal`：安全参考数据集 D_safe：SLIMORCA 留存子集 112k（Section 4.2）或 ALPACA-CLEANED 子集 49.9k（Section 4.5）
- `shen2024seal`：待微调数据集 D：REDORCA 112k = 90k SLIMORCA + 22k ANTHROPIC RED-TEAMING，或 OPENORCA 49.9k（Section 4.1/4.5）；在联邦里就是各客户端的本地分片
- `shen2024seal`：安全对齐的起点模型 θ₁：现成的 instruct/chat 模型，或 PYTHIA-2.8B 的 SFT 2 epoch + DPO 1 epoch 产物（Appendix B.1）
- `shen2024seal`：Algorithm 1 需要的辅助模型 θ̂（与 θ 同尺寸，显存翻倍；Algorithm 2 不需要）
- `shen2024seal`：S2 的训练循环本身：θ 与 ω 的优化器、γ 的每 epoch 调度、配对采样、总步数 K（论文未给）
- `shen2024seal`：（可选）训练选择器用的小代理模型 PHI-3-MINI-128K-INSTRUCT 或 PYTHIA-2.8B（Section 4.4）
- `xie2024gradsafe`：The aligned base LLM (Llama-2-7b-chat-hf in the paper) with gradient access on the plugin side. Alignment is part of the asset, not a detail (Table 7: AUPRC 0.936 aligned, 0.574 unaligned), and it must admit backward passes at all - a quantized or otherwise frozen PEFT deployment may not.
- `xie2024gradsafe`：The four reference prompts (2 unsafe + 2 safe, verbatim in Appendix A.2): inputs to the offline Phase I-III, not used at run time.
- `xie2024gradsafe`：The Phase I-III output: the slice index set S at gap threshold 1 and, for every i in S, the stored mean unsafe slice gradient, plus the index bookkeeping (which base weight matrix, row or column, which position) that maps slice i back to a slice of a freshly computed gradient.
- `xie2024gradsafe`：The detection threshold 0.25 (the paper's value for both benchmarks) and whatever calibration produced it; the paper does not say how it was chosen, so recalibrating for another base model or another reference set is defender work.
- `xie2024gradsafe`：GradSafe-Adapt only: labelled target-domain prompts (the ToxicChat official train split in the paper) and the fitted logistic probe tensors.
- `xie2024gradsafe`：Compute: 4x RTX 3090 in the paper (Appendix A.1) for the offline identification, and one forward plus one backward pass of a 7B model per screened prompt at run time.

## 缺的算子与新写的辅助函数

- `ax2210.07714` 缺：`geometry.rowwise_distance`，a distance between paired rows of two (n, d) matrices; the library only has distances within one matrix and cosine_to / distance_to against one reference vector
- `ax2210.07714` 缺：`stats.significance_tests and stats.p_values`，no operator for a two-sample t test, an F test, a two-sample Kolmogorov-Smirnov test, a boxplot outlier rule or a 3-sigma rule, and no p-value helper: an incomplete beta had to be implemented by hand, so any method that ports Alg. 4 pays the same ~95 lines
- `ax2210.07714` 新写：`_rowwise_distance / _distances_to`（22 行，通用），per-sample distance between paired rows of two (n, d) matrices, cosine and Euclidean; geometry.distances is within one set and cosine_to / distance_to compare with one reference
- `ax2210.07714` 新写：`_ratio / _signed_square / _hlbim / _pc1`（26 行，该论文特有），Alg. 1 lines 21-25: relative distance to the validator own model, sign-keeping square, labelwise mean and concatenation into HLBIM, first principal component
- `ax2210.07714` 新写：`_significant / _t_test / _f_test / _ks_test / _boxplot_outlier / _sigma_outlier`（50 行，通用），Alg. 4: the five significance tests at alpha 0.01 and their OR
- `ax2210.07714` 新写：`_betacf / _betai / _t_p_value / _f_p_value`（47 行，通用），regularized incomplete beta and the two p-values; written by hand because torch.distributions.StudentT.cdf and FisherSnedecor.cdf raise NotImplementedError and torch has no betainc
- `ax2210.07714` 新写：`_prune`（22 行，该论文特有），Alg. 2 lines 8-28: iterative pruning of the minority cluster with the safe abort above floor((n - 1) / 2)
- `ax2210.07714` 新写：`_aggregate_votes`（20 行，该论文特有），Alg. 3: agglomerative majority cluster of the vote rows, DBSCAN inside it, first row of the largest group
- `ax2210.07714` 新写：`_validation_set / _dlo`（16 行，该论文特有），resource parsing (samples plus labels) and one activations pass per state through ModelHandle.lora
- `ax2301.09508` 缺：`fedguard.ops.density.jensen_shannon`，divergence between two non-negative vectors; written in the plugin file from shannon_entropy, so it did not block the port, but a second Jensen-divergence method would rewrite the same 11 lines
- `ax2301.09508` 缺：`fedguard.ops.density.normal_pdf`，Gaussian density at arbitrary points; reachable only as gaussian_kde with a one-point sample, wrapped here as normal_density
- `ax2301.09508` 新写：`normal_density`（4 行，通用），normal density at every entry of a vector; a one-point sample of ops.density.gaussian_kde is exactly that, so this is a wrapper over an existing operator, not new math
- `ax2301.09508` 新写：`jensen_shannon`（11 行，通用），JSD in nats with m = (p + q) / 2, built from ops.density.shannon_entropy via JSD = H(m) - (H(p) + H(q)) / 2; both operands must be normalized first (mixing unnormalized densities silently turns m into a mass-weighted mixture, which changed the scores by ~0.06 here), and a vector with no mass is read as uniform
- `ax2305.05506` 缺：`trellis_forward_backward`，nothing in fedguard.ops works on a sequence or a trellis; the decoder is specific to this paper, so it is written in the plugin file (34 lines).
- `ax2305.05506` 缺：`dunn_index`，fedguard.ops.cluster stops at silhouette and the gap statistic; Eq. (5) needs a cluster-validity index that prefers separated clusters, written in the plugin file (18 lines, generic).
- `ax2305.05506` 新写：`dunn_index`（18 行，通用），Dunn index (smallest squared distance between cluster centers over the largest squared cluster diameter) from squared Euclidean distances; fedguard.ops.cluster has silhouette and the gap statistic but no Dunn index. Step R9.
- `ax2305.05506` 新写：`trellis_llr`（34 行，该论文特有），forward-backward over the trellis of the assignment matrix (states are partial syndromes, so 2^m of them) with the factorized BSC likelihood and the branch metrics 1 - delta / delta, returning the per-client a posteriori LLR of Eq. (17). Steps R15-R17.
- `ax2411.17453` 新写：`lora_modules`（3 行，通用），从 LoRA 状态字典里取出同时有 lora_A.weight 与 lora_B.weight 的模块前缀；库里已有 fedguard.views.uploads.lora_modules，但插件不能导入 fedguard.views.*，只能重写这 3 行
- `ax2411.17453` 新写：`module_rank`（12 行，该论文特有），从模块路径解析层号（最后一个全数字点段，没有则 -1）与目标模块序号（默认 q_proj、v_proj），用来排公式 (13)(14) 的通道顺序；论文假设的层/模块结构在库里只是字符串，见 extraction_needs
- `ax2608.06795` 缺：`activation_spike_statistic`，对逐插入点、逐 token 的幅度表算 s_m(x) = max_t(a_{m,t}) * log(1 + max_t(a_{m,t}) / mean_t(a_{m,t}))：既没有站点级的 max/mean 聚合算子，也没有把两者组合成尖峰统计量的算子。这是一个小的通用计算，若方法在库内有挂载点，本可写成插件文件里的模块级 helper（记入 new_helpers）；现在没有可挂的地方，故未写。
- `ax2608.06795` 缺：`median_mad_threshold`，tau = median + lambda * MAD 的单边上尾阈值（lambda = 4.45）。ops.robust.robust_z 返回的是逐值的中位数/MAD z 分数而不是阈值，ops.robust.largest_gap_threshold 是另一种切分规则，语义都不等价；同样是一个无处可挂的小 helper。
- `ax2609.37367` 新写：`insert_trigger`（7 行，该论文特有），Algorithm 2 的 INSERTTRIGGER：把 trigger 词插到指令的一个均匀随机词边界之间。
- `ax2609.37367` 新写：`refusal_rate`（6 行，该论文特有），Stage 1a 的 s_(i→j)：回答里含任一拒答短语（小写子串匹配）的比例。
- `ax2609.37367` 新写：`majority_reject`（3 行，通用），Algorithm 3 的投票规则：池化分数中严格多数 > eta 才拒绝，平局接受。
- `ax2609.37367` 新写：`span_counts`（12 行，通用），Algorithm 4 的 span 统计：按 w_min、r_min 统计一个生成缓冲上的词序列，一条生成对同一 span 只计一次。
- `ax2609.37367` 新写：`prune_nested`（17 行，通用），Algorithm 4 的嵌套族去重：按计数降序、长度降序保留，含空间填充后的词序列包含判断（避免 was her 落在 he was here 里这类假嵌套）。
- `ax2609.37367` 新写：`select_candidates`（10 行，通用），Algorithm 5 第 2-3 行：计数最高的 K−1 条（并列先长）∪ 最长串，至多 K 条。
- `ax2609.37367` 新写：`render_prompt / format_demo / format_query`（8 行，该论文特有），ICL prompt 模板（三条示例 + 带 trigger 的 query）与可移动性上下文的 with/without 两个渲染；论文说沿用 ICLSCAN 模板但未重述。
- `huang2024vaccine` 缺：`grad_wrt_layer_outputs`，dL/de_l for every layer of the model on the batch, with the graph kept (formula (2)). Neither fedguard.ops nor any view or handle method gives activation-space gradients: GradientView, LossView.gradients_of and ModelHandle.per_sample_gradients are parameter-space, and ModelHandle.hidden/activations return pooled, detached CPU tensors. Blocks steps 2-4.
- `huang2024vaccine` 缺：`forward_with_perturbed_activations`，A differentiable forward pass whose layer outputs are replaced by f + eps_l (the paper's forward hooks). ModelHandle.lora only swaps adapter weights and must leave the model as it found it; nothing in fedguard.ops injects into a forward pass. Blocks steps 5-6.
- `huang2024vaccine` 缺：`concat_l2_norm`，Global L2 norm of the concatenation of the per-layer gradient tensors (the denominator in formula (3)). Absent from fedguard.ops; it would be a two-line torch.cat + norm helper and is not itself the blocker (without grad_wrt_layer_outputs it has no input), so no module-level helper was written for it.
- `rieger2022deepsight` 缺：`hdbscan(D, min_cluster_size, min_samples)`，对预计算距离矩阵做通用 HDBSCAN 并返回完整簇划分。库里只有 density_clusters（把 eps 按 k 近邻距离中位数读出来的 DBSCAN 替身）和 majority_cluster（只留一个多数簇）。这里用 density_clusters 顶替，代价是：当很多更新近似重复时它的 eps 会塌到 0，只有逐位相同的更新才会同簇，而论文的余弦腿本应对缩放不变。
- `rieger2022deepsight` 缺：`ModelHandle 的逐输出单元概率前向`，ModelHandle 只有 losses/hidden/activations/per_sample_gradients/logprob/generate，没有任何方法返回逐输出单元的 logits 或概率，activations 还对 token 做池化；式 (6) 的 f(s;W)_i 和式 (7) 里输出层的权重行都取不到。
- `rieger2022deepsight` 新写：`_split_noise`（12 行，通用），把 HDBSCAN 的噪声点（-1）各自当成一个单点簇，使聚类结果能当作划分用（PCI 和簇共现距离矩阵都要用）。
- `rieger2022deepsight` 新写：`_membership_distances`（4 行，通用），Alg. 2 的 DistsFromClust：同一簇为 0、不同簇为 1 的 N×N 距离矩阵。
- `rieger2022deepsight` 新写：`_cluster_vote`（9 行，通用），PCI（Alg. 1 行 25-31）：簇内可疑标签占比达到 tau 就整簇剔除。
- `shen2024seal` 缺：`softmax_selector_update`，没有算子计算 ∇σ_j(ω) 或执行 ω ← ω − α·gap·∇σ_j(ω)（公式 (5)/(8)）；通用小函数只要几行，但没有能跑它的位置，见 missing_runtime
- `shen2024seal` 新写：`top_percent_keep`（12 行，通用），按分数取 ceil(p*n) 个最大者的下标，并列按输入顺序，至少保留 1 个：SEAL 的 top p% 截断；论文没写取整与并列规则，这里是本移植的选择
- `xie2024gradsafe` 缺：`row_column_slice`，Slice each 2-D gradient matrix into its row vectors and its column vectors with a stable index order. No fedguard.ops function does this (states.* works on LoRA state dicts, transform.* on vectors). It is a small generic computation and would be a module-level helper in the plugin file, not a library gap - but it sits downstream of the gradient in missing_runtime item 1.
- `xie2024gradsafe` 缺：`per_slice_cosine`，cos(query_slice_i, reference_slice_i) with a different reference per slice, across matrices of different slice lengths. fedguard.ops.geometry.cosine_to(X, ref) compares every row of X against ONE reference vector, so it does not cover this. Also a small generic helper ((X*R).sum(-1) / (norms) plus a zero-norm rule the paper does not give). Also not the blocker.

## 需要向原作者确认的

- `ax2210.07714`：How Alg. 1 / Alg. 2 handle the row of the validator own model: footnote 15 says the client does not evaluate its own model while Alg. 1 line 21 needs its distances as the denominator; is the row absent, constant, or evaluated?
- `ax2210.07714`：The PCA behind Alg. 2 line 14: centering/standardization, solver, and the sign convention of the first component.
- `ax2210.07714`：Alg. 4 line 11: are upper and lower split on the raw PC value or on value - median?
- `ax2210.07714`：Alg. 4: F-test or Levene (line 19 vs footnote 10), the boxplot multiplier, the sidedness of the 3-sigma interval, and whether the p-values are one- or two-sided.
- `ax2210.07714`：The shape of HLBIM after the label concatenation (Alg. 1 line 25 and footnote 8 vs the models x layers sentence in the text) and the concatenation order.
- `ax2210.07714`：What a DLO is in their code: flattened or pooled, normalized, and whether the final classification layer is included.
- `ax2210.07714`：How the cosine and the Euclidean analyses write the one vote array (footnote 7 vs Alg. 2 line 6): union, intersection, or one of them only?
- `ax2210.07714`：The distance metric and linkage of the agglomerative clustering, and the metric of DBSCAN on binary vote vectors.
- `ax2210.07714`：The definition of MIN(malicious_models) in the safe abort of Alg. 2 line 24 (smallest PC value, or closest to the median?).
- `ax2210.07714`：Whether Eq. 1 divides by the number of remaining models after the rejected ones are removed.
- `ax2301.09508`：the authors' code for Eq. (4): whether p is evaluated at the update coordinates or at the p-values, and which of the printed 1 and Wbar is the mean
- `ax2301.09508`：the authors' code for Alg. 2, to settle whether W_filtered collects the union or the intersection of the unique-score and below-average conditions (the reported TPR/TNR depend on it)
- `ax2301.09508`：mu_0, sigma_0^2, tau_0 and the per-round update rule of tau_k and n_k, none of which the paper gives
- `ax2301.09508`：whether clusters and per-client posteriors are reset between rounds, and how the shared H^t is updated in the authors' implementation
- `ax2305.05506`：The offline tables themselves: the parity-check matrix A (BCH code of length 15 with 8 redundant bits, and the (30,18) cyclic code), n_m^max, Pr(Z|N_m) and the Delta-hat(n_m) search results, with the Monte-Carlo sample counts, none of which the paper gives.
- `ax2305.05506`：The k-means initialization, distance and restarts, whether the two features are normalized or weighted, whether the PCA centers the data, and the tie-breaks of Eq. (5) and of the negative-test rule.
- `ax2305.05506`：How one secure-aggregation protocol instance produces the m overlapping group aggregates (the masks / secret sharing), which the paper leaves open.
- `ax2305.05506`：Whether the group-testing round also updates the global model, and how the flagged clients leave and re-enter training.
- `ax2411.17453`：元分类器的结构（卷积通道/核/步长/填充、MLP 宽度与层数、激活、归一化、dropout）和可调用的权重导出；Figure 7a 不足以重建
- `ax2411.17453`：发布版分类器期望的 F_input 约定：是否 (2L,d,k)、每层是否 q 先 v 后、是否归一化、某层只有一个目标模块时怎么补、DoRA 的 m 与 AdaLoRA 的 PΛQ 是否进特征
- `ax2411.17453`：PADBench 的划分脚本/随机种子与训练代码，用于换底座模型后重训分类器（论文第 7 节要求）
- `ax2608.06795`：a_{m,t}(x) 的范数形式（L2/L1/其他）与是否含 Eq (1) 的 alpha/r 缩放：论文只写 activation magnitude，只有作者代码能确定，而这直接决定 s_m 的尺度。
- `ax2608.06795`：sigma_m 的估计量（样本/总体标准差、ddof）与 MAD 是否乘 1.4826；k*|M| 的取整规则与 sigma_m 并列时的打破规则。
- `ax2608.06795`：每个模型的 |M| 绝对值，以及 WQ/WK/WV/WO/Wgate/Wup/Wdown 到具体 PEFT 模块名的映射（哪些附着点算 insertion site）。
- `ax2608.06795`：40 条 Alpaca 提示的抽样方式（子集、随机种子、是否去重、取哪个字段）与标定前向是否挂载可疑适配器。
- `ax2608.06795`：提示的 token 化细节：chat 模板与 system prompt 是否计入 T(x)、特殊 token 是否计入、超长提示如何截断、multi-LoRA 同时挂载时如何处理。
- `ax2609.37367`：ICLSCAN 的完整 prompt 模板（论文 §3.2.1/Appendix C 只说沿用它的 prompt format）。
- `ax2609.37367`：Appendix C 的 18 条拒答短语完整列表（正文只举了 do not have the capability / cannot follow the given instruction / i'm sorry, but 三条）。
- `ax2609.37367`：公开的 10000 个 5–12 字母词表的具体内容，以及抽 trigger 与生成 Stage 1a prompt 用的随机种子。
- `ax2609.37367`：采集 prompt 的随机种子（论文只说每轮重抽）。
- `ax2609.37367`：span 枚举里“词”的实际切分实现，以及嵌套族贪心在非链状、部分重叠时的完整取舍规则（作者代码里的写法）。
- `ax2609.37367`：信任状态机的实现细节：接受是否清零连续计数、W_ej 窗口如何随轮次滑动、被 EJECTED 跳过的轮次是否计入窗口。
- `huang2024vaccine`：The default rho of the main experiments (5.1 omits it; 5.4's 0.2 is absent from Tables 6/7).
- `huang2024vaccine`：Whether eps_l covers every token position and hidden dimension, and whether MLP layers are perturbed or only the attention modules that carry LoRA (4.2 vs Algorithm 1's 'each layer l in L').
- `huang2024vaccine`：How the first backward keeps dL/de_l (retain_graph on one graph vs two independent forward passes) and whether the perturbed second pass uses exactly the same batch.
- `huang2024vaccine`：Double-LoRA (4.2) vs the appendix's statement that the same LoRA adaptor is used for alignment and fine-tuning.
- `huang2024vaccine`：The accelerated variant's default tau and the conversion between T, 50 epochs, 2000 samples and batch 5 (drop-last, gradient accumulation).
- `huang2024vaccine`：Their reference implementation, for the numerical-stability handling of a zero or vanishing concatenated gradient norm and for the layer/module selection.
- `rieger2022deepsight`：Alg. 2 里 HDBSCAN 的实际调用参数（min_cluster_size、min_samples、是否允许单簇）以及噪声点 -1 参与 PCI 的方式——论文都没写，只有作者代码能确定。
- `rieger2022deepsight`：随机探针输入的具体分布、input dim 的来源与取值，以及 f(s;G_t)_i 接近 0 时 DDif 除法的数值保护。
- `rieger2022deepsight`：'all updates, including the filtered model updates' 到底指哪个集合（含被剔除簇的更新，还是只含被接受但未裁剪的），以及末轮被过滤模型如何取得簇归属、每个被过滤客户端收到哪个模型。
- `shen2024seal`：同一条数据在打乱/重新打包后与 ω 坐标的对应关系（论文按 D 中的位置排名，没有定义持久样本 ID）。
- `shen2024seal`：∇σ_j(ω_k) 的语义：softmax 下 ∂σ_j/∂ω 是稠密 N 维，是更新全部坐标还是只更新第 j 个（论文只说 coordinate-wise weighted descent）。
- `shen2024seal`：每 epoch 的迭代数与总步数 K、batch 64 里 D_safe 与 D 的配比、ω 的梯度是否在 batch 内累加或平均。
- `shen2024seal`：ℓ 的精确口径：哪些 token 计入损失、prompt 模板、最大长度、是否 packing、长度归一化分母是否含特殊 token。
- `shen2024seal`：ω 的初始化方式（softmax 对 ω 的常数平移不变，ω 不可辨识）、是否对 ω 归一化或正则。
- `shen2024seal`：Algorithm 1 第 5 行的权重写成 σ_i(ω_k) 而损失用 z_j，作者原意是哪个下标。
- `shen2024seal`：γ 从 0 开始与 Algorithm 1 的 γ_k ∈ (0,1) 字面冲突；γ 的上限、以及每 epoch 是覆盖赋值还是累加。
- `shen2024seal`：损失 gap 未裁剪/归一化而 α_k 固定，作者代码里是否有数值稳定处理。
- `xie2024gradsafe`：The exact loss of step 2 - token range, normalization, batch size - without which the gradient slices are not reproducible.
- `xie2024gradsafe`：Whether the reference prompts are wrapped in the same system-prompt template as the query prompts.
- `xie2024gradsafe`：The slice enumeration itself: how 1-D parameters, embedding and lm_head are treated, and the index order (rows before columns?) that keys a stored reference.
- `xie2024gradsafe`：Whether the Phase I average is leave-one-out: with n = 2 it includes each reference prompt's own contribution, which pushes the cosine toward 1 and inflates the gap.
- `xie2024gradsafe`：How the 0.25 detection threshold was calibrated.
- `xie2024gradsafe`：GradSafe-Adapt's logistic-regression hyperparameters and the probability threshold used for the binary label.
- `xie2024gradsafe`：The authors' code, to confirm that what is stored is gradients of the aligned base weights (not of LoRA factors) and that the reference can be recomputed for a different base model.

## 没通过检查的

- `huang2024vaccine`（failed）：无错误信息
