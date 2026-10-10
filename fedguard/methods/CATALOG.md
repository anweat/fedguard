# 已移植的论文方法

由 `python -m fedguard.methods write` 从代码里的声明生成，不要手改。
共 29 个插件。它们是这个库的示例和测试用例：每个都写明实现了论文的哪些步骤、哪些没有、哪些是我们自己的选择；都没有对照过原作者的代码，也没有复现过论文的数值。

| 插件 | 条目 | 论文 | 侧 | 位置 | 读 | 外部资源 | 动作 | Flower（Message API，1.39） | OpenFedLLM 系脚本（含 FedLLM-Attack） | 状态 | 完整度 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `krum` | I-0001 | `blanchard2017krum` | 服务器 | `SERVER_AGGREGATE` | `uploads` | — | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `lomar` | I-0002 | `li2022lomar` | 服务器 | `SERVER_RECEIVE`、`SERVER_AGGREGATE` | `uploads` | — | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `flame` | I-0003 | `nguyen2022flame` | 服务器 | `SERVER_RECEIVE`、`SERVER_AGGREGATE`、`SERVER_POST_AGGREGATE` | `aggregate`、`uploads` | — | `replace_global`、`select_and_weight`、`transform_update` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `freqfed` | I-0004 | `fereidooni2024freqfed` | 服务器 | `SERVER_AGGREGATE` | `uploads` | — | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `coordinate_median` | I-0005 | `yin2018median` | 服务器 | `SERVER_POST_AGGREGATE` | `aggregate`、`uploads` | — | `replace_global` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `trimmed_mean` | I-0006 | `yin2018median` | 服务器 | `SERVER_POST_AGGREGATE` | `aggregate`、`uploads` | — | `replace_global` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `foolsgold` | I-0007 | `fung2018foolsgold` | 服务器 | `SERVER_AGGREGATE` | `uploads` | — | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 部分 |
| `fldetector` | I-0008 | `zhang2022fldetector` | 服务器 | `SERVER_RECEIVE`、`SERVER_AGGREGATE`、`SERVER_POST_AGGREGATE` | `aggregate`、`uploads` | — | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 部分 |
| `mud_hog` | I-0009 | `ax2208.10273` | 服务器 | `SERVER_RECEIVE`、`SERVER_AGGREGATE` | `reports`、`uploads` | — | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `mcd` | I-0010 | `sun2024vaguegan` | 服务器 | `SERVER_RECEIVE`、`SERVER_AGGREGATE` | `uploads` | — | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `fltrust` | I-0011 | `cao2020fltrust` | 服务器 | `SERVER_RECEIVE`、`SERVER_AGGREGATE` | `uploads` | `server_update` | `select_and_weight`、`transform_update` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `crfl` | I-0013 | `ax2106.08283` | 服务器 | `SERVER_POST_AGGREGATE` | `aggregate` | — | `replace_global` | 原生 | 改脚本 | 真实模型上跑通 | 部分 |
| `safe_fedllm_client` | I-0014 | `safefedllm2026` | 服务器 | `SERVER_RECEIVE`、`SERVER_AGGREGATE` | `reports`、`uploads` | `lora_probe` | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `safe_fedllm_step_trust`（与 `safe_fedllm_step` 配对） | I-0016 | `safefedllm2026` | 服务器 | `SERVER_AGGREGATE` | `reports`、`uploads` | — | `select_and_weight` | 原生 | 改脚本 | 真实模型上跑通 | 完整 |
| `protegofed_server`（与 `protegofed_client` 配对） | I-0021 | `protegofed2026` | 服务器 | `SERVER_EXCHANGE` | `reports` | — | — | 扩展层 `handshake` | 改脚本 | 真实模型上跑通 | 完整 |
| `safe_lora` | I-0028 | `hsu2024safelora` | 服务器 | `SERVER_POST_AGGREGATE` | `aggregate` | `alignment` | `replace_global` | 原生 | 改脚本 | 只有单元测试；受阻：the entry point does not build the alignment resource | 完整 |
| `safe_fedllm_step`（与 `safe_fedllm_step_trust` 配对） | I-0015 | `safefedllm2026` | 客户端 | `CLIENT_STEP`、`CLIENT_POST_TRAIN` | `received_model`、`train_trace` | `lora_probe` | — | 应用配合 | 改脚本 | 真实模型上跑通 | 完整 |
| `spectral_signatures` | I-0017 | `tran2018spectral` | 客户端 | `CLIENT_PRE_TRAIN` | `data`、`model_handle` | — | `mask_samples` | 应用配合 | 改脚本 | 真实模型上跑通 | 完整 |
| `activation_clustering` | I-0018 | `chen2018activation` | 客户端 | `CLIENT_PRE_TRAIN` | `data`、`model_handle` | — | `mask_samples` | 应用配合 | 改脚本 | 真实模型上跑通 | 完整 |
| `gradient_spectral_entropy` | I-0019 | `gradsentry2026` | 客户端 | `CLIENT_PRE_TRAIN` | `data`、`model_handle` | — | `mask_samples` | 应用配合 | 改脚本 | 真实模型上跑通 | 完整 |
| `protegofed_client`（与 `protegofed_server` 配对） | I-0020 | `protegofed2026` | 客户端 | `CLIENT_ANNOUNCE`、`CLIENT_PRE_TRAIN` | `data`、`model_handle`、`reports` | — | `mask_samples` | 扩展层 `handshake` | 改脚本 | 真实模型上跑通 | 完整 |
| `onion` | I-0022 | `qi2021onion` | 客户端 | `CLIENT_PRE_TRAIN` | `data`、`model_handle` | — | `edit_samples` | 应用配合 | 改脚本 | 真实模型上跑通 | 完整 |
| `safety_mix` | I-0023 | `bianchi2023safetytuned`、`wang2024bea` | 客户端 | `CLIENT_PRE_TRAIN` | — | `safety_samples` | `edit_samples` | 应用配合 | 改脚本 | 真实模型上跑通 | 部分 |
| `lisa_proximal` | I-0024 | `huang2024lisa` | 客户端 | `CLIENT_PRE_STEP` | `gradients` | — | `transform_gradients` | 应用配合 | 改脚本 | 真实模型上跑通 | 部分 |
| `la_lora` | I-0025 | `rethinklora2026` | 客户端 | `CLIENT_PRE_STEP` | `gradients` | — | `transform_gradients` | 应用配合 | 改脚本 | 真实模型上跑通 | 部分 |
| `received_adapter_scan` | I-0026 | `ax2607.27940` | 客户端 | `CLIENT_PRE_TRAIN` | `received_model` | — | `transform_received` | 应用配合 | 改脚本 | 真实模型上跑通 | 部分 |
| `update_subspace_projection` | I-0027 | `ax2607.27940` | 客户端 | `CLIENT_POST_TRAIN` | `local_update`、`model_handle` | `aux_samples` | `transform_update` | 应用配合 | 改脚本 | 真实模型上跑通 | 完整 |
| `lisa` | I-0039 | `huang2024lisa` | 客户端 | `CLIENT_LOSS` | `loss`、`train_trace` | `alignment_batches` | `transform_loss` | 扩展层 `trainer` | 改脚本；需扩展层 `trainer` | 真实模型上跑通 | 完整 |
| `la_lora_dp` | I-0040 | `rethinklora2026` | 客户端 | `CLIENT_LOSS`、`CLIENT_PRE_STEP` | `gradients`、`loss` | — | `transform_gradients` | 扩展层 `trainer` | 改脚本；需扩展层 `trainer` | 真实模型上跑通 | 完整 |

列的含义：

- 位置、读、外部资源、动作：插件类的声明；运行器在第一轮之前按它们检查，声明之外的数据读不到。
- 宿主两列：在该宿主上挂这个插件的最高代价。原生＝只用宿主自己的扩展点；应用配合＝应用的训练函数要调用本库；改脚本＝宿主没有扩展点，要改它的训练脚本；扩展层＝要启用本库的一层扩展适配，**那不是宿主原版的行为**，启用时有警告并写入记录。
- 状态：知识库条目的状态。完整度为“部分”表示类说明里有“没有实现”的步骤。
- 论文一列是文献键，对应 `survey/paper_index.md`。

## 逐个说明

以下各节摘自类说明（`fedguard/methods/*.py`），原文是英文。

### `krum`（Krum，server_uploads.py）

Krum and Multi-Krum (Blanchard et al., NeurIPS 2017). Score of a client = sum of squared distances to its n - f - 2 nearest other clients; keep the m clients with the lowest scores (m = 1 is Krum, m > 1 Multi-Krum, which averages them).

- **原文未定、此处的选择**：ties are broken by client order; with n < f + 3 nothing is done. The kept clients keep the weights the aggregation would have used (the paper averages them equally; pass equal_weights=True for that).
- **参数与默认值**：`f=1`，`m=1`，`space='factor'`，`equal_weights=False`

### `lomar`（LoMar，server_uploads.py）

LoMar (Li et al., IEEE TDSC 2022): score each update by its kernel density relative to the density of its k nearest neighbours; an update whose ratio is below the threshold is left out.

- **实现了**：k nearest neighbours in squared Euclidean distance, Gaussian kernel density, the ratio F(i) of a client's density to the mean density of its neighbours, the gate F(i) >= threshold.
- **与原文不同**：the paper splits the parameters by output label and multiplies the per-label ratios; a LoRA adapter has no output layer, so one ratio over the whole update is used. The threshold is the paper's empirical value 1.0, not the bound of its Eq. 10 (an inequality the paper does not solve).
- **原文未定、此处的选择**：k = floor(0.4 n), at least 1; a neighbour set excludes the client itself; the bandwidth is the median k-th neighbour distance (the paper leaves it to the user); if every client falls below the threshold nobody is excluded. With threshold 1.0 roughly half of a homogeneous group falls below it; the paper reports this value as the best on average for its settings.
- **已知问题**：at the paper's threshold 1.0 it excluded 3 of 5 clients in every round of the Qwen3.5 runs
- **参数与默认值**：`k_share=0.4`，`threshold=1.0`，`bandwidth=None`

### `flame`（FLAME，server_uploads.py）

FLAME (Nguyen et al., USENIX Security 2022): cluster, clip, add noise.

- **实现了**：pairwise cosine distances; the single majority cluster (HDBSCAN with min_cluster_size = n/2 + 1, min_samples = 1) is admitted; clipping bound S_t = median of all clients' update norms; admitted updates scaled by min(1, S_t / norm); equal-weight average; Gaussian noise N(0, (lambda * S_t)^2) on the aggregate.
- **与原文不同**：distances are taken between updates (uploaded - broadcast), not between the uploaded models; with LoRA the uploads share the broadcast factors and would be nearly parallel. Without scikit-learn, ops.cluster.majority_cluster stands in for HDBSCAN (same contract, different algorithm).
- **原文未定、此处的选择**：the clipping reference is the model the round was broadcast with; the median of an even count is the mean of the two middle values; lambda defaults to the paper's 0.001 (image and text settings) and is not derived from an (epsilon, delta) budget here.
- **参数与默认值**：`noise_lambda=0.001`，`space='factor'`

### `freqfed`（FreqFed，server_uploads.py）

FreqFed (Fereidooni et al., NDSS 2024): cluster clients on the low-frequency DCT components of their updates.

- **实现了**：each client's vector laid out as a square matrix, 2-D DCT, the low-frequency triangle (i + j <= side // 2), pairwise cosine distances, the largest cluster kept, equal-weight average.
- **与原文不同**：the transform is applied to updates rather than uploaded models, for the reason given in FLAME.
- **原文未定、此处的选择**：how weights of many shapes become one square matrix (here: all factor entries in sorted key order, row by row, zero-padded to the next square); the DCT is the orthonormal DCT-II (the paper's printed normalization scales only the first row and column differently, which cosine distance is not invariant to); HDBSCAN's parameters are not given, so the majority setting of FLAME is used, and a cluster must hold a majority to be kept.
- **开销**：one DCT of a sqrt(d) x sqrt(d) matrix per client.
- **参数与默认值**：无

### `coordinate_median`（CoordinateMedian，server_uploads.py）

Coordinate-wise median (Yin et al., ICML 2018), in place of the mean of the updates.

- **实现了**：the median of every coordinate over the clients' updates; client weights are ignored, as in the paper.
- **与原文不同**：taken on the LoRA factors A and B separately, which is not the median of their product.
- **原文未定、此处的选择**：an even count gives the mean of the two middle values.
- **参数与默认值**：无

### `trimmed_mean`（TrimmedMean，server_uploads.py）

Coordinate-wise beta-trimmed mean (Yin et al., ICML 2018): drop the floor(beta * n) largest and smallest values of every coordinate, average the rest. The paper requires beta at least the fraction of Byzantine clients; it is a parameter here.

- **与原文不同**：taken on the LoRA factors A and B separately, which is not the trimmed mean of their product.
- **参数与默认值**：`beta=0.1`

### `foolsgold`（FoolsGold，server_uploads.py）

FoolsGold (Fung et al., 2018): clients whose accumulated updates point the same way are sybils.

- **实现了**：per-client history = running sum of its updates; cosine similarity between histories; pardoning; alpha = 1 - max similarity; rescaling; logit with confidence kappa.
- **没有实现**：the paper's restriction to output-layer parameters and its "indicative feature" weighting. A LoRA adapter has no output layer, so all factor entries are used.
- **原文未定、此处的选择**：history accumulates from the first round a client is seen, with no window or decay; absent clients keep their history; boundary cases follow the authors' code. The paper applies alpha as a per-client learning rate on an unnormalized sum. Here alpha becomes the aggregation weight, which the framework normalizes: relative weights match, the overall step size does not.
- **参数与默认值**：`kappa=1.0`

### `fldetector`（FLDetector，server_uploads.py）

FLDetector (Zhang et al., KDD 2022): a client whose updates are inconsistent with what the global model's trajectory predicts is malicious.

- **实现了**：differences of the global model and of the aggregated update over a window of N rounds; L-BFGS Hessian-vector product; predicted update = the client's previous update + H (w_t - w_{t-1}); Euclidean distance to the received update, L1-normalized over clients; mean over the window as the suspicious score; gap statistic to decide whether there are two groups; 2-means; the group with the larger mean score is flagged and excluded from this round on.
- **没有实现**：the paper removes the flagged clients and restarts training from scratch.
- **原文未定、此处的选择**：scores are produced once a full window exists (the paper starts at round 50; `start_round` sets that); a client absent in the previous round gets no score; a rank-deficient window is solved with a pseudo-inverse. Memory: N + 1 vectors of the global model's size plus one per client.
- **参数与默认值**：`window=10`，`start_round=0`，`k_max=10`，`references=20`

### `mud_hog`（MudHoG，server_uploads.py）

MUD-HoG (Gupta et al., ESORICS 2022): tell sign-flipping, additive-noise and targeted attackers and unreliable clients apart from short and long histories of gradients. Per client: short HoG = mean of its last `short` updates, long HoG = sum of all its updates. 1. sign flipping: cosine of the short HoG to the coordinate-wise median short HoG below 0 2. additive noise: density clustering of the remaining short HoGs; for the clients outside the largest group, distance to that group's median; above the largest-gap threshold -> attacker 3. targeted: 2-means on the remaining long HoGs; the smaller cluster 4. unreliable: cosine of the remaining short HoGs to their median; below the largest-gap threshold Attackers are excluded once flagged in `confirm` consecutive rounds; unreliable clients keep a fraction `alpha` of their weight. Nothing is judged during the first `warmup` rounds.

- **与原文不同**：the update of a round stands in for the gradient; ops.cluster.density_clusters stands in for DBSCAN, whose eps and minPts the paper does not give.
- **原文未定、此处的选择**：the median is coordinate-wise; a single client outside the largest group is not judged (no gap exists); equal-sized 2-means clusters flag nobody; flags are recomputed every round and only confirmed attackers are excluded, for that round; a client absent from a round keeps its history and loses its streak. Note that steps 3 and 4 flag someone whenever they run, also when every client is honest.
- **参数与默认值**：`warmup=3`，`short=3`，`alpha=0.5`，`confirm=2`

### `mcd`（MCD，server_uploads.py）

MCD, model-consistency-based defense (Sun et al., VagueGAN paper, 2024): over a period of rounds a client's models should stay in one place and move about as much as everyone else's.

- **实现了**：2-D PCA of the round's updates; per client and period the centroid of its 2-D points and the mean distance to that centroid (its footprint); baseline clients are those whose two metrics lie within Omega1 and Omega2 of the first baseline; abnormality h = lambda1 * |centroid - baseline centroid| / baseline footprint + lambda2 * |baseline footprint - footprint|; a client with h > delta * median(h) leaves the trusted set and is excluded from then on.
- **与原文不同**：the paper's first baseline is a model the server trains itself on data it trusts; here the coordinate-wise median of the clients' metrics stands in for it, which removes the trusted-data requirement and with it the guarantee that the baseline is clean. Updates are projected, not models.
- **原文未定、此处的选择**：the PCA basis is fitted on the first round of each period and kept for that period, without standardization; delta = 2 (the paper gives the range (1, 3)); a client with fewer than two points in a period is not judged; exclusion starts in the round of detection and is permanent; zero denominators are replaced by 1e-12.
- **参数与默认值**：`period=80`，`omega1=4.0`，`omega2=2.0`，`lambda1=1.0`，`lambda2=2.0`，`delta=2.0`

### `fltrust`（FLTrust，server_uploads.py）

FLTrust (Cao et al., NDSS 2021): a server update computed on a small clean root dataset bootstraps trust.

- **实现了**：trust score TS_i = ReLU(cos(g_i, g_0)); every client update rescaled to the norm of the server update; aggregation weights TS_i. Resource `server_update`: a function (broadcast LoRA state) -> LoRA state after the server's own training on its root dataset with the clients' settings. Training it is the caller's job.
- **原文未定、此处的选择**：a client or server update of zero norm gets trust 0; when every trust score is 0 all clients are excluded, so the adapter keeps the previous global model. The paper also applies a global learning rate to the aggregate; the framework's aggregation does not.
- **参数与默认值**：无

### `crfl`（CRFL，server_uploads.py）

CRFL (Xie et al., ICML 2021), training-time part: clip the aggregated model's norm and add Gaussian noise before it is broadcast again.

- **实现了**：Clip_rho(w) = w / max(1, |w| / rho_t) with rho_t = rho0 + rho_slope * t, then noise N(0, sigma^2) on every entry; in the round given as `last_round` only the clipping.
- **与原文不同**：the norm is that of the LoRA factors, the only parameters the server holds. The paper's rho and sigma were chosen for its small models; the defaults here are its MNIST values and are not tuned for LoRA. With LoRA's zero-initialized B a sigma of 0.01 is large compared with early updates.
- **没有实现**：the test-time parameter smoothing and the certified radius, which need a classifier with a known Lipschitz constant (the paper derives it for multi-class logistic regression only).
- **已知问题**：with the paper's norm bound the global LoRA was scaled to 0.10-0.14 of its norm every round (Kaiming-initialized A has a large norm)
- **参数与默认值**：`rho0=2.0`，`rho_slope=0.1`，`sigma=0.01`，`last_round=None`

### `safe_fedllm_client`（SafeFedLLMClientLevel，server_uploads.py）

Safe-FedLLM, Client-Level (2026): a frozen linear probe scores each uploaded LoRA.

- **实现了**：probe feature (first-layer B differences, L2-normalized); malicious probability s = sigmoid(a.x + c); instantaneous factor 1 - g(s) with the two-stage calibration; mean over the rounds the client took part in; factors frozen after `freeze_after` rounds; the round is skipped when the mean factor of the sampled clients is below tau_skip; otherwise weights n_i * w_i. Resource `lora_probe`: a probe as returned by fedguard.ops.probe.fit_logistic, trained offline on labelled benign and malicious LoRA differences. Training it is the caller's job. Optional resource `initial_lora`: the LoRA all clients started from (B_0).
- **原文未定、此处的选择**：whether B_0 is the very first LoRA or the round's starting point. Without `initial_lora` the round's broadcast LoRA is used, i.e. the feature is this round's change. The paper's Step-Level and Shadow-Level variants are separate (see SafeFedLLMStep* below; Shadow-Level needs a second training branch on the client and is not implemented).
- **参数与默认值**：`k=10.0`，`tau_skip=0.2`，`freeze_after=20`，`initial_lora=None`

### `safe_fedllm_step_trust`（SafeFedLLMStepTrust，two_sided.py）

Safe-FedLLM, Step-Level, server half: decayed Beta counts of the step verdicts clients report. alpha <- gamma * alpha + benign steps, beta <- gamma * beta + malicious steps; factor alpha / (alpha + beta); weights n_i * factor; round skipped when the mean factor is below tau_skip; frozen after `freeze_after` rounds.

- **原文未定、此处的选择**：alpha and beta start at 1 (a uniform prior). Clients that report nothing keep their current factor.
- **参数与默认值**：`gamma=0.95`，`tau_skip=0.2`，`freeze_after=20`，`source='safe_fedllm_step'`

### `protegofed_server`（ProtegoFedServer，two_sided.py）

ProtegoFed, server half: cluster the clients' centroids and send back the centroid of the main cluster. Runs at SERVER_EXCHANGE, before any client trains.

- **原文未定、此处的选择**：whether this second clustering uses the same two-way split and silhouette gate as the client; here it does. What clients send is unverified: centroids of the wrong size or with non-finite values are dropped.
- **参数与默认值**：`t_s=0.2`，`t_l=0.4`，`client='protegofed_client'`

### `safe_lora`（SafeLoRA，server_uploads.py）

Safe LoRA (Hsu et al., NeurIPS 2024): project LoRA updates that drift away from the alignment subspace back onto it. Per LoRA module with an alignment matrix V = W_aligned - W_unaligned: the projector onto the column space of V (`exact=True`, C = V (V^T V)^-1 V^T, computed through a QR factorization) or the paper's fast form C = V V^T / ||V||_F; cosine between the update B A and C B A; modules whose cosine is below tau are replaced by their projection. Resource `alignment`: {LoRA module prefix: V}, each V of shape (d_out, d_in), computed by the caller from a pair of aligned and unaligned checkpoints.

- **原文未定、此处的选择**：how the projected, dense update gets back into LoRA factors. Since C B A = (C B) A, only B is replaced by C B, which keeps the rank and the factor shapes exactly. Runs on the aggregated global LoRA here; the paper applies it to a finished fine-tune.
- **参数与默认值**：`tau=0.35`，`exact=True`

### `safe_fedllm_step`（SafeFedLLMStepProbe，two_sided.py）

Safe-FedLLM, Step-Level, client half: after every local step, probe the LoRA and count verdicts. Each step: feature from the current LoRA against the received one, probe score, malicious if s >= tau_cls. Before upload the counts of benign and malicious steps are sent to the server. Resource `lora_probe` as in SafeFedLLMClientLevel, held by the client. The server cannot verify these counts; a client that lies about them defeats the method.

- **原文未定、此处的选择**：the paper does not say where the probe runs or how the counts reach the server; running it on the client and sending counts over the channel is a choice.
- **开销**：one copy of the LoRA and one dot product per local step.
- **参数与默认值**：`tau_cls=0.8`

### `spectral_signatures`（SpectralSignatures，client_samples.py）

Spectral signatures (Tran et al., NeurIPS 2018): poisoned samples of a class leave a detectable trace in the top singular direction of that class's representations. Per group of samples: hidden representations, centered; score = squared projection on the top right singular vector; the top 1.5 * epsilon fraction is masked.

- **与原文不同**：the paper trains a model on the full (possibly poisoned) data first and reads a late layer of it; here the representations come from the model the client received, so a backdoor that has not reached that model yet leaves no trace. The paper groups by class label; language-model samples have none, so everything is one group unless `group_of` gives one.
- **原文未定、此处的选择**：epsilon is a fraction; the number removed is rounded up; a group with fewer than `min_group` samples is left alone.
- **开销**：one forward pass per scored sample.
- **参数与默认值**：`epsilon=0.05`，`layer=-1`，`pool='mean'`，`group_of=None`，`max_samples=None`，`min_group=10`

### `activation_clustering`（ActivationClustering，client_samples.py）

Activation clustering (Chen et al., 2018): within a class, poisoned and clean samples activate the last hidden layer differently and split into two clusters. Per group: last-hidden-layer activations, reduced to `components` dimensions, 2-means; if the smaller cluster holds less than `size_threshold` of the group and the split has a silhouette above `silhouette_threshold`, the smaller cluster is masked.

- **与原文不同**：the paper reduces with ICA; PCA is used here. The paper offers three tests (retraining without a cluster, relative size, silhouette); the size and silhouette tests are combined here and the retraining test is not implemented. Grouping and the source of the activations as in SpectralSignatures.
- **开销**：one forward pass per scored sample.
- **参数与默认值**：`components=10`，`size_threshold=0.35`，`silhouette_threshold=0.1`，`layer=-1`，`pool='mean'`，`group_of=None`，`max_samples=None`，`min_group=10`

### `gradient_spectral_entropy`（GradientSpectralEntropy，client_samples.py）

GradSentry (2026): the per-sample gradient of a poisoned sample has a different spectral entropy. Per sample: gradient of one weight matrix; top-k singular values; normalized to a distribution; entropy divided by log k. Threshold at the valley of a Gaussian kernel density of the scores (Silverman bandwidth), with the paper's fallback of 0.7 when the scores are not bimodal; samples above the threshold are masked.

- **与原文不同**：the paper takes the gradient of lm_head.weight and keeps its top-left 1/8 x 1/8 block; the model handle exposes LoRA parameters only, so the gradient of one LoRA B matrix is used whole. Its rank is at most r, so k = min(k, r). Whether the paper's finding carries over to this matrix has not been checked. An exact SVD replaces the paper's randomized one.
- **原文未定、此处的选择**：peaks are local maxima of the density on a 512-point grid; a score equal to the threshold is kept.
- **开销**：one forward and one backward pass per scored sample.
- **参数与默认值**：`group='last_lora_B'`，`k=16`，`fallback=0.7`，`max_samples=None`

### `protegofed_client`（ProtegoFedClient，two_sided.py）

ProtegoFed, client half (2026): poisoned samples separate from clean ones in the frequency domain of their per-sample gradients; a global centroid from the server corrects each client's own split. CLIENT_ANNOUNCE: per-sample gradient of the target module (default: lora_B of the last layer; the paper uses the last layer's v_proj.lora_B), 2-D DCT, flatten; split into clusters; the centroid of the main cluster, in the original feature dimension, is sent to the server. CLIENT_PRE_TRAIN: the server's global centroid is added to the local features as one more point, the features are clustered again, and the samples outside the centroid's cluster are masked.

- **与原文不同**：the paper reduces to two dimensions with UMAP; PCA is used here (no UMAP dependency). The paper's HDBSCAN comes without parameters; ops.cluster.density_clusters (DBSCAN with a data-driven radius) stands in for it.
- **原文未定、此处的选择**：a clustering that finds one cluster counts with silhouette 0 in the gate; the main cluster is the largest one; HDBSCAN noise points are outside the main cluster; the re-clustering with the centroid uses the same two-way split and silhouette gate as the first one (the paper says only "similarly"), and noise points of the density clustering are given the label of their nearest clustered sample before the comparison; `max_samples` (not in the paper) subsamples the data and leaves the samples that were not scored untouched.
- **开销**：one forward and one backward pass per scored sample.
- **参数与默认值**：`group='last_lora_B'`，`t_s=0.2`，`t_l=0.4`，`max_samples=None`，`server='protegofed_server'`

### `onion`（Onion，client_samples.py）

ONION (Qi et al., EMNLP 2021), moved to training time: delete the words whose removal lowers the perplexity of a sample's text, on the idea that an inserted trigger is such a word.

- **实现了**：perplexity p0 of the text and p_i with word i deleted, suspicion f_i = p0 - p_i, words with f_i > bar deleted (bar = 0, the paper's value when there is no validation set to tune it on).
- **与原文不同**：ONION cleans test inputs before inference; here it rewrites training samples before local training (`edit_samples`). The language model is the one being fine-tuned, with the adapter the client received, instead of GPT-2. Perplexity is exp of the mean negative token log-probability of the text after a newline. Only the first `max_words` words of a text are examined.
- **原文未定、此处的选择**：words are whitespace-separated; a text is never emptied (if every word is suspicious the sample is left alone).
- **开销**：one forward pass per examined word and one per sample.
- **已知问题**：at the paper's threshold 0 it rewrote about 15 of 24 instruction samples per client
- **参数与默认值**：`field='instruction'`，`bar=0.0`，`max_words=40`，`max_samples=None`

### `safety_mix`（SafetyMix，client_samples.py）

Mix defender-supplied safety samples into the local training data. Without a secret this is safety-tuning (Bianchi et al., ICLR 2024): harmful instructions paired with refusals are added to the fine-tuning set. With `secret_words` > 0 it is Backdoor Enhanced Safety Alignment (Wang et al., 2024): every added sample carries a fixed random prefix, which the service also puts in front of user inputs at inference, so the refusals are tied to a trigger the user does not know. Resource `safety_samples`: a list of samples in the training format. The first `n` are used (BEA: 11).

- **与原文不同**：BEA puts the secret into the system prompt; the training format here has none, so it is prefixed to the field `field`. BEA draws 150 random tokens from the vocabulary; here `secret_words` random lowercase words of 3 to 8 letters are drawn from `secret_seed`, without a tokenizer.
- **没有实现**：generating the refusals (they come with the resource) and the inference-side prefix. A client that wants the attack to succeed can simply not run this plugin: it protects only against poisoned data a willing client was handed.
- **参数与默认值**：`n=11`，`secret_words=0`，`secret_seed=0`，`field='instruction'`

### `lisa_proximal`（LisaProximal，client_step.py）

Lisa's proximal term (Huang et al., NeurIPS 2024) for the fine-tuning state: pull the weights back toward the checkpoint the state started from.

- **实现了**：on every optimizer step the gradient becomes grad + rho * (w - w_ref), where w_ref is the value of the trainable parameters at the first step of the round, i.e. the model the client received. That is the gradient of the paper's objective h(w) + rho/2 |w - w_ref|^2.
- **没有实现**：the alignment state (K1 steps on alignment data between fine-tuning states), which needs a second data source and loop control a callback does not have. With the received global model as w_ref this term is what FedProx adds; what makes it Lisa is the alternation that is missing here.
- **原文未定、此处的选择**：the term covers all trainable parameters (the LoRA factors); it is added to the gradient analytically; w_ref is kept in the parameters' own precision.
- **参数与默认值**：`rho=1.0`

### `la_lora`（AlternatingNoisyLoRA，client_step.py）

LA-LoRA's local step (Rethinking LoRA for privacy-preserving federated learning, 2026): update one LoRA factor per step, clip, add Gaussian noise, smooth with a fixed low-pass filter.

- **实现了**：odd steps keep the gradients of B and zero those of A, even steps the reverse; each active matrix is clipped to the bound C; noise N(0, (sigma * C / batch_size)^2) is added; a 5-tap binomial filter (1/16)[1,4,6,4,1] with symmetric padding runs along the feature dimension (rows of A, columns of B).
- **与原文不同**：the paper clips each sample's gradient; a Trainer callback sees only the batch gradient, so the batch gradient is clipped. That bounds nothing per sample and gives no differential-privacy guarantee. Zeroing a factor's gradient does not freeze it under an optimizer with momentum or weight decay (AdamW keeps moving it); the paper freezes the factor.
- **没有实现**：the privacy accounting, and the server's separate averaging of A and B (FedAvg on the factors already does that).
- **原文未定、此处的选择**：C defaults to the median norm of the active matrices' gradients at that step (the paper says "median of the layer's gradient norm distribution" without the scope); the filter runs on the noised gradient at every step.
- **参数与默认值**：`clip=None`，`sigma=0.36`，`batch_size=16`，`taps=5`

### `received_adapter_scan`（ReceivedAdapterScan，client_model.py）

TriShield, parameter artifact detection (PAD): scan the adapter a client was sent for rows planted to memorize data, and reinitialize them before training. A row of a lora_A matrix is flagged when its variance is below tau_var or its correlation with another row of the same matrix is above tau_corr. Flagged rows are redrawn (Kaiming normal, as the paper states) through `transform_received`.

- **没有实现**：the paper also resets a bias term of B, which PEFT LoRA does not have, and its other two layers (optimizer pre-warming, projection of the update; the latter is UpdateSubspaceProjection).
- **参数与默认值**：`tau_var=0.0001`，`tau_corr=0.95`

### `update_subspace_projection`（UpdateSubspaceProjection，client_model.py）

TriShield, zero-utility-loss orthogonal projection (ZUOP): keep only the part of the local update that lies in the subspace spanned by task gradients on public data. Per-sample gradients of the LoRA parameters on the auxiliary samples form the columns of G; U_k are its top-k left singular vectors, k = min(rank_fraction * rank(G), n - 1); the update is replaced by U_k U_k^T update, in factor space, through `transform_update`. Resource `aux_samples`: public, unlabelled samples from a domain close to the private data (the paper uses 32 and recommends 200 to 500).

- **原文未定、此处的选择**：gradients are taken at the trained local model (the paper gives three different descriptions of the point); n in the formula for k is the number of auxiliary samples; the paper also describes a projection of the product B A, which is not implemented.
- **开销**：one forward and one backward pass per auxiliary sample, every round.
- **参数与默认值**：`rank_fraction=0.8`，`group='lora'`

### `lisa`（LisaBiState，client_step.py）

Lisa (Huang et al., NeurIPS 2024): alternate between an alignment state on the defender's alignment data and a fine-tuning state on the user's data, each pulled toward the checkpoint the other state ended at.

- **实现了**：local steps run in cycles of `k_align` alignment steps followed by `k_finetune` fine-tuning steps. In an alignment step the loss is the host's loss on a batch of the alignment data (the user batch of that step is not trained on); in a fine-tuning step it is the host's loss on the user batch. Both add rho/2 * |w - w_ref|^2, where w_ref is the value of the trainable parameters at the last switch of state. That is the paper's pair of sub-problems (its equation 2).
- **与原文不同**：the paper is centralized, with one run of cycles over the whole fine-tuning; here the cycle restarts in every federated round and its first reference is the model the client received. The paper keeps separate LoRA components for alignment and fine-tuning (Double-LoRA); here both states train the one adapter the host federates. An alignment step still costs the forward pass on the user batch, which the host has already run when the plugin is called.
- **原文未定、此处的选择**：the proximal term covers the trainable parameters (the LoRA factors); alignment batches are taken in order, continuing across rounds; the default 1:9 split keeps the paper's 100:900 ratio at the length of a federated local round. Resource `alignment_batches`: a sequence of batches in the trainer's format (see fedguard.adapters.hf_trainer_ext.collate_texts), from data the defender trusts.
- **参数与默认值**：`rho=1.0`，`k_align=1`，`k_finetune=9`

### `la_lora_dp`（LALoRAPerSample，client_step.py）

LA-LoRA's local step (Rethinking LoRA for privacy-preserving federated learning, 2026) with the clipping the paper describes: each sample's gradient of the active factor is clipped before the sum.

- **实现了**：as `la_lora` (one LoRA factor per step, Gaussian noise, 5-tap binomial low-pass filter), except that the gradient of the active factor is rebuilt from per-sample gradients: g_j clipped to the bound C jointly over the active matrices, summed over the batch, noise N(0, (sigma*C)^2) added, the result divided by the batch size (the paper's equation 9). The batch gradient the host computed is replaced by it before the optimizer steps.
- **与原文不同**：zeroing the inactive factor's gradient does not freeze it under an optimizer with momentum or weight decay; the paper freezes it. No privacy accounting is done, and with the default bound (below) no differential-privacy guarantee holds, since the bound then depends on the batch.
- **原文未定、此处的选择**：the paper clips per layer at "the median of the layer's gradient norm distribution"; here one bound covers all active matrices and defaults to the median of the per-sample gradient norms of the batch. Pass `clip` for a fixed, data-independent bound.
- **开销**：one backward pass per sample of the batch, on top of the host's own. Needs one forward pass per optimizer step (gradient_accumulation_steps = 1).
- **已知问题**：with the default bound (batch median) and sigma 0.36 at batch size 4, the replaced gradient had about 94 times the norm of the batch gradient on Qwen3.5-0.8B: the noise dominates
- **参数与默认值**：`clip=None`，`sigma=0.36`，`taps=5`

## 怎么试

推荐的方式是写一份控制策略文件（`fedguard/policy.py`，示例在 `integrations/policies/`），三个入口都接受：实验入口与接入示例用 `--guard_policy 文件`，Flower 应用用 `FG_POLICY=文件`。`python -m fedguard.policy 文件` 会列出它挂了什么、每个宿主上各需要什么。
下表是按名字启用的旧参数，仍然可用（内部转成一份策略）；可以同时启用多个，逗号分隔，按书写顺序运行。

| 宿主 | 入口 | 服务器侧插件 | 客户端侧插件 | 让插件动作 | 训练器扩展层 |
|---|---|---|---|---|---|
| FedLLM-Attack（实验入口，能提供表中全部外部资源，`alignment` 除外） | `experiments/fedllm_attack/run_guarded.py` | `--guard_modules a,b` | `--guard_client_modules a,b` | 服务器侧总是动作；客户端侧 `--guard_client_apply 1` | `--guard_trainer_ext 1` |
| OpenFedLLM 原版、FedLLM-Attack（最小接入示例，不提供外部资源） | `integrations/<宿主>/main_sft_guard.py` | 同上 | 同上 | `--guard_apply 1` | `--guard_trainer_ext 1` |
| Flower | `experiments/flower/sim_llm.py <输出目录> guard` | `FG_SERVER=a,b` | `FG_CLIENT=a,b` | `FG_APPLY=1` | `FG_TRAINER_EXT=1`；握手 `FG_HANDSHAKE=1` |

批量：`experiments/fedllm_attack/methods_sweep.sh` 对每个方法各跑一次短的联邦训练（`ONLY="krum lisa"` 只跑其中几个，`SCENARIO=control` 为全部良性客户端）；`experiments/flower/llm_check.sh` 与 `integrations/check_plugins.sh` 在另外两个宿主上成组地跑。
这些运行只回答“挂得上、跑得动、是否动作”，轮数远小于论文，不说明防御效果。
不训练模型的检查：`tests/test_methods_*.py`（各方法的机制）、`tests/test_methods_together.py`（同时启用与单独启用的输出相同）、`tests/test_trainer_ext.py`（扩展层）。
