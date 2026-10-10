"""候选文献清单（检索阶段）。

每条: (key, category, title, arxiv_id 或 None, note)
arxiv_id 由 resolve_arxiv.py 与 arXiv 摘要页元数据核对；为 None 时按标题检索。
category 对应 CATEGORIES 中的目录名。
"""

CATEGORIES = {
    "C0": "C0_survey_taxonomy",            # 综述、分类体系、基准
    "C1": "C1_fl_lora_foundations",        # 联邦学习、LoRA、FedLLM 训练底座、对齐训练基础
    "C2": "C2_fl_poisoning_attacks",       # 经典/图像联邦投毒攻击（迁移来源）
    "C3": "C3_fl_robust_defenses",         # 联邦鲁棒聚合与更新检测（迁移来源）
    "C4": "C4_llm_pretrain_poisoning",     # 预训练阶段投毒与持久性
    "C5": "C5_llm_sft_poisoning",          # 指令微调/SFT 投毒、后门、有害微调攻击
    "C6": "C6_llm_preference_poisoning",   # 偏好/RLHF/DPO 投毒
    "C7": "C7_harmful_ft_defenses",        # 有害微调防御（对齐/微调/微调后阶段）
    "C8": "C8_sample_level_detection",     # 样本级投毒/后门数据检测（表示、梯度）
    "C9": "C9_fedllm_attack_defense",      # 联邦 LLM 微调攻防（直接相关）
    "C10": "C10_lora_supplychain_privacy", # LoRA 供应链、梯度泄露与隐私
}

CANDIDATES = [
    # ---------------- C0 综述与分类 ----------------
    ("huang2024harmful", "C0", "Harmful Fine-tuning Attacks and Defenses for Large Language Models: A Survey", "2409.18169", "本地已有"),
    ("du2024privacy", "C0", "Privacy in Fine-tuning Large Language Models: Attacks, Defenses, and Future Directions", "2412.16504", "本地已有"),
    ("zhao2025systematic", "C0", "A Systematic Review of Poisoning Attacks Against Large Language Models", "2506.06518", ""),
    ("li2020backdoorsurvey", "C0", "Backdoor Learning: A Survey", "2007.08745", ""),
    ("kairouz2019advances", "C0", "Advances and Open Problems in Federated Learning", "1912.04977", ""),
    ("zhang2025flpoison", "C0", "SoK: Benchmarking Poisoning Attacks and Defenses in Federated Learning", "2502.03801", "FLPoison 基准"),
    ("sheng2022backdoornlp", "C0", "A Survey on Backdoor Attack and Defense in Natural Language Processing", "2211.11958", ""),

    # ---------------- C1 基础 ----------------
    ("mcmahan2017fedavg", "C1", "Communication-Efficient Learning of Deep Networks from Decentralized Data", "1602.05629", "FedAvg"),
    ("hu2021lora", "C1", "LoRA: Low-Rank Adaptation of Large Language Models", "2106.09685", ""),
    ("dettmers2023qlora", "C1", "QLoRA: Efficient Finetuning of Quantized LLMs", "2305.14314", "本机小显存实验依据"),
    ("zhang2023fedit", "C1", "Towards Building the Federated GPT: Federated Instruction Tuning", "2305.05644", "Shepherd/FedIT"),
    ("ye2024openfedllm", "C1", "OpenFedLLM: Training Large Language Models on Decentralized Private Data via Federated Learning", "2402.06954", ""),
    ("ye2024fedllmbench", "C1", "FedLLM-Bench: Realistic Benchmarks for Federated Learning of Large Language Models", "2406.04845", "自然 non-IID"),
    ("sun2024ffalora", "C1", "Improving LoRA in Privacy-preserving Federated Learning", "2403.12313", "FFA-LoRA，A/B 聚合不一致"),
    ("wang2024flora", "C1", "FLoRA: Federated Fine-Tuning Large Language Models with Heterogeneous Low-Rank Adaptations", "2409.05976", "堆叠式无噪声聚合"),
    ("bonawitz2016secagg", "C1", "Practical Secure Aggregation for Federated Learning on User-Held Data", "1611.04482", "安全聚合"),
    ("ouyang2022instructgpt", "C1", "Training language models to follow instructions with human feedback", "2203.02155", "SFT/RM/PPO 阶段划分"),
    ("rafailov2023dpo", "C1", "Direct Preference Optimization: Your Language Model is Secretly a Reward Model", "2305.18290", ""),

    # ---------------- C2 经典/图像联邦投毒攻击 ----------------
    ("sun2024vaguegan", "C2", "A GAN-Based Data Poisoning Attack Against Federated Learning Systems and Its Countermeasure", "2405.11440", "孙蔚 VagueGAN+MCD"),
    ("sun2026pcdm", "C2", "PCDM: A Diffusion-Based Data Poisoning Attack Against Federated Learning Systems", "2605.16098", "孙蔚/高博 扩散投毒，LSDAM 后续"),
    ("tolpegin2020dataflip", "C2", "Data Poisoning Attacks Against Federated Learning Systems", "2007.08432", "标签翻转"),
    ("bagdasaryan2020backdoor", "C2", "How To Backdoor Federated Learning", "1807.00459", "模型替换"),
    ("fang2020local", "C2", "Local Model Poisoning Attacks to Byzantine-Robust Federated Learning", "1911.11815", ""),
    ("baruch2019little", "C2", "A Little Is Enough: Circumventing Defenses For Distributed Learning", "1902.06156", "ALIE"),
    ("wang2020tails", "C2", "Attack of the Tails: Yes, You Really Can Backdoor Federated Learning", "2007.05084", "edge-case"),
    ("zhang2022neurotoxin", "C2", "Neurotoxin: Durable Backdoors in Federated Learning", "2206.10341", "持久后门"),
    ("xie2020dba", "C2", "DBA: Distributed Backdoor Attacks against Federated Learning", None, "ICLR 2020 OpenReview"),
    ("shejwalkar2021manipulating", "C2", "Manipulating the Byzantine: Optimizing Model Poisoning Attacks and Defenses for Federated Learning", None, "NDSS 2021, DnC"),

    # ---------------- C3 联邦防御 ----------------
    ("blanchard2017krum", "C3", "Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent", "1703.02757", "Krum"),
    ("yin2018median", "C3", "Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates", "1803.01498", "Median/Trimmed mean"),
    ("fung2018foolsgold", "C3", "Mitigating Sybils in Federated Learning Poisoning", "1808.04866", "FoolsGold"),
    ("sun2019clipping", "C3", "Can You Really Backdoor Federated Learning?", "1911.07963", "范数裁剪"),
    ("cao2020fltrust", "C3", "FLTrust: Byzantine-robust Federated Learning via Trust Bootstrapping", "2012.13995", "服务器根数据集"),
    ("nguyen2022flame", "C3", "FLAME: Taming Backdoors in Federated Learning", "2101.02281", ""),
    ("rieger2022deepsight", "C3", "DeepSight: Mitigating Backdoor Attacks in Federated Learning Through Deep Model Inspection", "2201.00763", ""),
    ("zhang2022fldetector", "C3", "FLDetector: Defending Federated Learning Against Model Poisoning Attacks via Detecting Malicious Clients", "2207.09209", "跨轮一致性，与 MCD 纵向对照"),
    ("li2022lomar", "C3", "LoMar: A Local Defense Against Poisoning Attack on Federated Learning", "2201.02873", ""),
    ("fereidooni2024freqfed", "C3", "FreqFed: A Frequency Analysis-Based Approach for Mitigating Poisoning Attacks in Federated Learning", "2312.04432", "DCT 频域，ProtegoFed 组合对象"),

    # ---------------- C4 预训练投毒 ----------------
    ("carlini2023webscale", "C4", "Poisoning Web-Scale Training Datasets is Practical", "2302.10149", ""),
    ("zhang2024persistent", "C4", "Persistent Pre-Training Poisoning of LLMs", "2410.13722", "跨阶段持久性"),
    ("souly2025constant", "C4", "Poisoning Attacks on LLMs Require a Near-constant Number of Poison Samples", "2510.07192", ""),
    ("hubinger2024sleeper", "C4", "Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training", "2401.05566", "后门跨安全训练保持"),

    # ---------------- C5 SFT 投毒 / 后门 / 有害微调攻击 ----------------
    ("wan2023instruction", "C5", "Poisoning Language Models During Instruction Tuning", "2305.00944", ""),
    ("shu2023autopoison", "C5", "On the Exploitability of Instruction Tuning", "2306.17194", "AutoPoison"),
    ("yan2023vpi", "C5", "Backdooring Instruction-Tuned Large Language Models with Virtual Prompt Injection", "2307.16888", "语义触发"),
    ("xu2023instructionsbackdoor", "C5", "Instructions as Backdoors: Backdoor Vulnerabilities of Instruction Tuning for Large Language Models", "2305.14710", ""),
    ("qi2023finetuning", "C5", "Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To!", "2310.03693", "身份切换、良性数据退化"),
    ("yang2023shadow", "C5", "Shadow Alignment: The Ease of Subverting Safely-Aligned Language Models", "2310.02949", ""),
    ("he2024safedata", "C5", "What is in Your Safe Data? Identifying Benign Data that Breaks Safety", "2404.01099", "表面良性投毒，梯度/表示锚定"),
    ("halawi2024covert", "C5", "Covert Malicious Finetuning: Challenges in Safeguarding LLM Adaptation", "2406.20053", "编码隐蔽有害微调"),
    ("li2024backdoorllm", "C5", "BackdoorLLM: A Comprehensive Benchmark for Backdoor Attacks and Defenses on Large Language Models", "2408.12798", ""),
    ("qi2021hiddenkiller", "C5", "Hidden Killer: Invisible Textual Backdoor Attacks with Syntactic Trigger", "2105.12400", ""),
    ("qi2021stylebkd", "C5", "Mind the Style of Text! Adversarial and Backdoor Attacks Based on Text Style Transfer", "2110.07139", "StyleBkd"),
    ("betley2025emergent", "C5", "Emergent Misalignment: Narrow finetuning can produce broadly misaligned LLMs", "2502.17424", ""),
    ("harmlessinputs2025", "C5", "Revisiting Backdoor Attacks on LLMs: A Stealthy and Practical Poisoning Framework via Harmless Inputs", "2505.17601", "无害输入隐蔽后门"),

    # ---------------- C6 偏好/RLHF/DPO 投毒 ----------------
    ("rando2023universal", "C6", "Universal Jailbreak Backdoors from Poisoned Human Feedback", "2311.14455", ""),
    ("baumgartner2024venom", "C6", "Best-of-Venom: Attacking RLHF by Injecting Poisoned Preference Data", "2404.05530", ""),
    ("wang2023rlhfpoison", "C6", "RLHFPoison: Reward Poisoning Attack for Reinforcement Learning with Human Feedback in Large Language Models", "2311.09641", ""),
    ("pathmanathan2024dpo", "C6", "Is poisoning a real threat to LLM alignment? Maybe more so than you think", "2406.12091", "DPO 投毒"),
    ("fu2024poisonbench", "C6", "PoisonBench: Assessing Large Language Model Vulnerability to Data Poisoning", "2410.08811", ""),

    # ---------------- C7 有害微调防御 ----------------
    ("huang2024vaccine", "C7", "Vaccine: Perturbation-aware Alignment for Large Language Models against Harmful Fine-tuning Attack", "2402.01109", "对齐阶段"),
    ("huang2024booster", "C7", "Booster: Tackling Harmful Fine-tuning for Large Language Models via Attenuating Harmful Perturbation", "2409.01586", "对齐阶段"),
    ("rosati2024repnoise", "C7", "Representation Noising: A Defence Mechanism Against Harmful Finetuning", "2405.14577", "对齐阶段"),
    ("tamirisa2024tar", "C7", "Tamper-Resistant Safeguards for Open-Weight LLMs", "2408.00761", "对齐阶段"),
    ("huang2024lisa", "C7", "Lisa: Lazy Safety Alignment for Large Language Models against Harmful Fine-tuning Attack", "2405.18641", "微调阶段"),
    ("bianchi2023safetytuned", "C7", "Safety-Tuned LLaMAs: Lessons From Improving the Safety of Large Language Models that Follow Instructions", "2309.07875", "微调阶段混入安全数据"),
    ("wang2024bea", "C7", "Mitigating Fine-tuning based Jailbreak Attack with Backdoor Enhanced Safety Alignment", "2402.14968", "微调阶段"),
    ("shen2024seal", "C7", "SEAL: Safety-enhanced Aligned LLM Fine-tuning via Bilevel Data Selection", "2410.07471", "数据选择"),
    ("hsu2024safelora", "C7", "Safe LoRA: the Silver Lining of Reducing Safety Risks when Fine-tuning Large Language Models", "2405.16833", "微调后，LoRA 投影"),
    ("huang2024antidote", "C7", "Antidote: Post-fine-tuning Safety Alignment for Large Language Models against Harmful Fine-tuning", "2408.09600", "微调后剪枝"),
    ("inan2023llamaguard", "C7", "Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations", "2312.06674", "数据/行为审查器"),
    ("li2024saladbench", "C7", "SALAD-Bench: A Hierarchical and Comprehensive Safety Benchmark for Large Language Models", "2402.05044", "MD-Judge"),

    # ---------------- C8 样本级检测 ----------------
    ("tran2018spectral", "C8", "Spectral Signatures in Backdoor Attacks", "1811.00636", "表示谱检测"),
    ("chen2018activation", "C8", "Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering", "1811.03728", ""),
    ("qi2021onion", "C8", "ONION: A Simple and Effective Defense Against Textual Backdoor Attacks", "2011.10369", "困惑度"),
    ("gao2019strip", "C8", "STRIP: A Defence Against Trojan Attacks on Deep Neural Networks", "1902.06531", ""),
    ("cui2022openbackdoor", "C8", "A Unified Evaluation of Textual Backdoor Learning: Frameworks and Benchmarks", "2206.08514", "CUBE/OpenBackdoor"),
    ("xie2024gradsafe", "C8", "GradSafe: Detecting Jailbreak Prompts for LLMs via Safety-Critical Gradient Analysis", "2402.13494", "梯度特征"),
    ("xia2024less", "C8", "LESS: Selecting Influential Data for Targeted Instruction Tuning", "2402.04333", "LoRA 梯度+随机投影"),
    ("gradsentry2026", "C8", "GradSentry: Gradient Spectral Entropy for Backdoor Sample Filtering in Large Language Model Fine-Tuning", "2605.26574", ""),

    # ---------------- C9 联邦 LLM 攻防 ----------------
    ("ye2024emerging", "C9", "Emerging Safety Attack and Defense in Federated Instruction Tuning of Large Language Models", "2406.10630", "ICLR 2025，本地已有"),
    ("protegofed2026", "C9", "ProtegoFed: Backdoor-Free Federated Instruction Tuning with Interspersed Poisoned Data", "2603.00516", "本地已有"),
    ("safefedllm2026", "C9", "Safe-FedLLM: Delving into the Safety of Federated Large Language Models", "2601.07177", "ACL 2026"),
    ("signalagg2026", "C9", "Revisiting Backdoor Threat in Federated Instruction Tuning from a Signal Aggregation Perspective", "2602.15671", "ICASSP 2026"),
    ("li2024peftattack", "C9", "PEFT-as-an-Attack! Jailbreaking Language Models during Federated Parameter-Efficient Fine-Tuning", None, ""),
    ("graphmanip2026", "C9", "Graph Representation Learning Augmented Model Manipulation on Federated Fine-Tuning of LLMs", "2605.07961", ""),
    ("tokenlora2026", "C9", "Token-Level Generalization in LoRA Adapter Backdoors: Attack Characterization and Behavioral Detection", "2605.30189", ""),
    ("fedllmprivacy2025", "C9", "Can Federated Learning Safeguard Private Data in LLM Training? Vulnerabilities, Attacks, and Defense Evaluation", "2509.20680", ""),

    # ---------------- C10 LoRA 供应链与隐私 ----------------
    ("liu2024loratk", "C10", "LoRATK: LoRA Once, Backdoor Everywhere in the Share-and-Play Ecosystem", "2403.00108", ""),
    ("dong2024trojanplugin", "C10", "The Philosopher's Stone: Trojaning Plugins of Large Language Models", "2312.00374", ""),
    ("balunovic2022lamp", "C10", "LAMP: Extracting Text from Gradients with Language Model Priors", "2202.08827", ""),
    ("gupta2022film", "C10", "Recovering Private Text in Federated Learning of Language Models", None, ""),
    ("rethinklora2026", "C10", "Rethinking LoRA for Privacy-Preserving Federated Learning in Large Models", "2602.19926", ""),

    # ---------------- 补充检索：跨阶段持久性与偏好投毒 ----------------
    ("persistcontinual2025", "C4", "Persistent Backdoor Attacks under Continual Fine-Tuning of LLMs", "2512.14741", "AAAI，后门跨持续微调保持"),
    ("prefpoison2026", "C6", "Efficient Preference Poisoning Attack on Offline RLHF", "2605.02495", "DPO 标签翻转"),
    ("adversarialrlhf2025", "C6", "LLM Misalignment via Adversarial RLHF Platforms", "2503.03039", ""),
    ("great2025", "C6", "GREAT: Generalizable Backdoor Attacks in RLHF via Emotion-Aware Trigger Synthesis", "2510.09260", ""),
]
