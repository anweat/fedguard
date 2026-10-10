# 精读卡片的引句核对

卡片 47 张，引句 376 条：逐字匹配 353，近似匹配（最长公共片段覆盖不低于 80%）7，未匹配 15，过短 1。

匹配前做了归一化：去掉空白、标点与大小写差异，合并行尾断词。未匹配的引句不能当作原文依据使用。

## 未匹配或过短的引句

| 论文 | 状态 | 覆盖 | 章节 | 引句 |
|---|---|---|---|---|
| `ax2103.05633` | miss | 0.72 |  | k is a parameter which we call checkpointing interval; 1 k is then the checkpointing frequency. Increasing k helps optimize storage costs (refer § V-D2). |
| `ax2210.07714` | miss | 0.58 |  | CrowdGuard first leverages a Principal Component Analysis (PCA) on the HLBIM matrix to highlight the differences between different models (cf. line 14), before  |
| `ax2402.12168` | miss | 0.51 |  | Secondly, we leverage PEFT methods to continually train the poisoned model on Dtrain clean_reset. Formally, the training of PSIM is as follows |
| `ax2402.12168` | miss | 0.52 |  | when the input sample is not injected with triggers, PSIM exhibits output confidence close to 50%. However, when the input sample is poisoned, the output confid |
| `ax2409.14119` | miss | 0.58 |  | We adopt the default hyperparameters for PEFT and select the largest λamp and λreg that exhibit no more than a 2% drop in the CACC on the validation set. |
| `ax2410.14425` | miss | 0.5 |  | Teacher logits and hidden states zt, ht = ft(x; θt); Student logits and hidden states zs, hs = fs(x; θs); |
| `ax2411.17453` | miss | 0.64 |  | Step2. Layer-wise Concatenation. We concatenate ∆(l) concat across all L layers as Finput = ∆(1) concat ∥∆(2) concat ∥...∥∆(L) concat, Finput ∈R(2L)×d×k, where  |
| `gradsentry2026` | miss | 0.56 |  | We locate these peaks and define the threshold as the valley between them: τ = arg min x∈[xL,xR] ˆg(x) (10) where xL and xR are the positions of peaks closest t |
| `huang2024lisa` | miss | 0.72 |  | We show in Table 7 that the clock time of Lisa is slightly increased by 8.3% compared to SFT, by 4.9% compared to BSO. The extra computation mainly comes from t |
| `inan2023llamaguard` | miss | 0.7 |  | From this dataset, we pick the first human prompt and discard the corresponding response from the assistant, as well as all the other turns to create an initial |
| `li2022lomar` | miss | 0.57 |  | Thus, in order to protect the FL learning objective and remove as many the malicious remote updates in LoMar, we deﬁne the optimal threshold ϵ = min{1, ϵm}. |
| `nguyen2022flame` | miss | 0.53 |  | Clipping scales down model updates as follows: W c bl = Gt-1 +(Wbl -Gt-1)* MIN(1,gamma) (detailed in line 8-11 of Alg. 1) where the multiplication is computed c |
| `nguyen2022flame` | miss | 0.25 |  | We use standard DP parameters and set epsilon = 3705 for IC, epsilon = 395 for the NIDS and epsilon = 4191 for the NLP scenario. Accordingly, lambda = 0.001 for |
| `rethinklora2026` | miss | 0.58 |  | The server averages client uploads: At = 1//Ct/ X i∈Ct At i, Bt = 1//Ct/ X i∈Ct Bt i, and then updates the global model as W t = W0 + sBtAt. |
| `shen2024seal` | miss | 0.61 |  | Sample data zi safe from safe dataset Dsafe and zj from fine-tuning dataset D. Update model parameter θk+1 = θk − βk (1 − γk)∇ℓ(θk; zi safe) + γkσj(ωk)∇ℓ(θk; zj |
| `shen2024seal` | short | 0.0 |  | Update data selector ωk+1 = ωk − αk ℓ(θk; zj) − ℓ(ˆθk; zj) ∇σj(ωk) |
