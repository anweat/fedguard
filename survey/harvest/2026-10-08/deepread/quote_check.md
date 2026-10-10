# 精读卡片的引句核对

卡片 137 张，引句 1371 条：逐字匹配 1314，近似匹配（最长公共片段覆盖不低于 80%）21，未匹配 36，过短 0。

匹配前做了归一化：去掉空白、标点与大小写差异，合并行尾断词。未匹配的引句不能当作原文依据使用。

## 未匹配或过短的引句

| 论文 | 状态 | 覆盖 | 章节 | 引句 |
|---|---|---|---|---|
| `ax2104.13230` | miss | 0.5 | Section 7 Conclusion | One of the trade-offs from the defender's side is that the objective function to minimize the influence sometimes affects the clean data points, which leads to  |
| `ax2108.10241` | miss | 0.56 | Section II-C2 | This AGR [58] bounds the L2 norm of all submitted client updates to a ﬁxed threshold, with the intuition that the effective poisoned updates should have high no |
| `ax2305.05506` | miss | 0.58 | Section IV-C | Then, for each cluster, we compute the average utility of the aggregated models using a small validation dataset at the server (a minor assumption as motivated  |
| `ax2402.13459` | miss | 0.78 | 2.2 Threat Model | In both cases, we adopt the “clean-label” attack scenario, where the injected samples are contextually appropriate and grammatically correct, ensuring they rema |
| `ax2410.14425` | miss | 0.62 | 2.1 Application Scenarios | Therefore, the LLM may be poisoned when the victim lacks sufficient computational resources and training samples for full-parameter fine-tuning of LLMs for high |
| `ax2502.18511` | miss | 0.51 | 3.2 Problem Formulation, Without fine-tuning attacks | Without fine-tuning attacks. These attacks bypass parameter updates by leveraging demonstration poisoning or model inversion to manipulate input-output behavior |
| `ax2502.18511` | miss | 0.54 | 4.2.1 Classifaction Task Performance | For instance, Table 2 presents that GBTL achieves approximately 95% CACC and around 99% ASR across all datasets on Llama2-7B-Chat. |
| `ax2507.01694` | miss | 0.78 | III-B. Lagrange Dual Problem and Graph Signal Processing | the attack is formulated as a constrained optimization problem: maximize the poisoning impact on the global model while constraining the malicious update remain |
| `ax2508.08040` | miss | 0.77 | Section VI.C.1 | These results indicate that while existing defenses can sometimes reduce prompt-level backdoor impact, none consistently balance robustness and clean utility, u |
| `ax2604.02372` | miss | 0.6 | Section 4 (Future work) | Future work includes extensive ablation studies of the attack to find the optimal scale and frequency of the backdoor injection. Another direction is extending  |
| `ax2606.16242` | miss | 0.76 | 2.1 Threat Model, Defining poisoning rates | We define poisoning rates relative to the total training set of 6k samples (3k proliferated jailbreaks + 3k safe WildChat queries). |
| `baruch2019little` | miss | 0.69 | 3.3 Preventing Convergence | Finally, the attacker will set the value of all the malicious workers to v = µ + 1.75 · σ for each of the parameters independently with the parameters' µj and σ |
| `baumgartner2024venom` | miss | 0.76 | §1 Introduction | To achieve this goal, we assume the attackers can poison the preference dataset by injecting new preference pairs into an existing preference dataset, but they  |
| `baumgartner2024venom` | miss | 0.58 | §6 Results | Therefore, adding poisonous data does not affect the clean performance of the RMs, making it challenging to detect our attack simply by looking at the RM evalua |
| `blanchard2017krum` | miss | 0.63 | Section 2 Model | We consider a general distributed system consisting of a parameter server, and n workers, f of them possibly Byzantine (behaving arbitrarily). Computation is di |
| `fedllmprivacy2025` | miss | 0.55 | 5.2.2 Results (Fig. 14) | The results shown in Fig. 14 indicate that fine-tuning aligned models reduce the degree of privacy leakage compared to the non-aligned version. However, aligned |
| `fung2018foolsgold` | miss | 0.72 | 3. Assumptions and threat model | We assume that these types of obfuscations are not used, and that the central server is able to observe any individual client's model update at each iteration. |
| `gradsentry2026` | miss | 0.57 | 4.2 Main Results | GradSentry introduces about 20–50 ms per sample, which is the best among the three methods, since it only requires one per-sample gradient extraction followed b |
| `great2025` | miss | 0.77 | 7 Auditing-Based Defense | However, this improvement relies on substantial prior knowledge of the trigger and manual prompt engineering, limiting its practicality at scale. |
| `gupta2022film` | miss | 0.73 | Sec. 6.1 Training and attack settings | Following previous studies (Zhu et al., 2019; Geiping et al., 2020; Yin et al., 2021; Huang et al., 2021) for gradient inversion attacks, our evaluation conside |
| `harmlessinputs2025` | miss | 0.62 | 3.2 Harmless Poisoned Data Generation | With these responses, the attacker can construct a poisoned dataset Dp by modifying each question xi with a trigger t, and pairing it with the corresponding res |
| `inan2023llamaguard` | miss | 0.54 | Section 1 | First, none of the available tools distinguishes between assessing safety risks posed by the user and the AI agent, which are arguably two distinct tasks |
| `mcmahan2017fedavg` | miss | 0.56 | 4 Conclusions and Future Work | While federated learning offers many practical privacy benefits, providing stronger guarantees via differential privacy, secure multi-party computation, or thei |
| `prefpoison2026` | miss | 0.56 | Section 2.2 | We study label flip attacks on offline preference datasets. The attacker selects a subset of comparisons and flips their outcomes, equivalently changing oi to − |
| `prefpoison2026` | miss | 0.76 | Section 6.2.3 | The clean-vs-attacked distance ∥πclean − πˆθ∥1 stabilizes to around 0.224, which is about 19 times the attack-vs-groundtruth distance of 0.012. |
| `protegofed2026` | miss | 0.63 | Section VI-D2 | The starting point of ProtegoFed design is that clean data can dominate on most clients, so that the global centroid feature remains on the side of clean sample |
| `qi2021hiddenkiller` | miss | 0.65 | §5.2 | The adversary can only poison the training data but not manipulate the training process, e.g., a victim uses a poisoned third-party dataset to train a model in  |
| `qi2021stylebkd` | miss | 0.78 | 5.2 Backdoor Attack Results | When a backdoor defense is deployed, the ASRs of the two insertion-based baseline attacks drop substantially (the average ∆ASRs for RIPPLES and InsertSent are - |
| `rieger2022deepsight` | miss | 0.79 | IV-A | The rationale is that for a poisoned model update W ′ the predicted probabilities for the backdoor target class will be increased in general, independently from |
| `shu2023autopoison` | miss | 0.58 | 3.1 Threat model, Adversary capabilities | We study the black-box setting, where an adversary cannot access the victim model. In addition, we study the setting of “clean-label" attack, restricting the in |
| `sun2024thesis` | miss | 0.68 | ABSTRACT (p. iv) | As a distributed machine learning paradigm, FL is collaboratively carried out on privately owned datasets but without direct data access. |
| `wang2024flora` | miss | 0.77 | Appendix C Limitation | Our approach has the limitation that the server sends the stacked LoRA modules to the client, thereby increasing the communication costs. We discussed this limi |
| `xia2024less` | miss | 0.57 | §4.2 Data Selection Algorithm | We select the highest scoring examples to construct Dtrain. After selection, we use the selected subset Dtrain to train the target model MT. |
| `yan2023vpi` | miss | 0.67 | §3 Constructing Poisoned Data | We build poisoned instruction tuning data that demonstrates the VPI behavior by pairing the original instructions (without the virtual prompt) with their VPI re |
| `yang2023shadow` | miss | 0.61 | Section 5.6 | Among the 200 test questions, we find 98.5% and 92.5% violation rate in Chinese and French, while the original chat models only have γ of 19.0% and 17.5%, respe |
| `zhao2025systematic` | miss | 0.75 | 4.2.1 Persistence Despite Defenses | Because the adapters used in LoRA are assumed to have specific, low rank structure which poisoned adapters may not have, a defense based on identifying differen |
