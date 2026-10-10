# 文献库索引

> 由 `scripts/build_library.py` 自动生成。“阅读状态”列在 `notes/` 写完精读笔记后手动更新。

## C0_survey_taxonomy

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `huang2024harmful` | Harmful Fine-tuning Attacks and Defenses for Large Language Models: A Survey | Huang 等 | 2024 | [arXiv:2409.18169](https://arxiv.org/abs/2409.18169) | [PDF](papers/C0_survey_taxonomy/huang2024harmful_2409.18169.pdf) | 本地已有 |
| `du2024privacy` | Privacy in Fine-tuning Large Language Models: Attacks, Defenses, and Future Directions | Du 等 | 2024 | [arXiv:2412.16504](https://arxiv.org/abs/2412.16504) | [PDF](papers/C0_survey_taxonomy/du2024privacy_2412.16504.pdf) | 本地已有 |
| `zhao2025systematic` | A Systematic Review of Poisoning Attacks Against Large Language Models | Fendley 等 | 2025 | [arXiv:2506.06518](https://arxiv.org/abs/2506.06518) | [PDF](papers/C0_survey_taxonomy/zhao2025systematic_2506.06518.pdf) |  |
| `li2020backdoorsurvey` | Backdoor Learning: A Survey | Li 等 | 2020 | [arXiv:2007.08745](https://arxiv.org/abs/2007.08745) | [PDF](papers/C0_survey_taxonomy/li2020backdoorsurvey_2007.08745.pdf) |  |
| `kairouz2019advances` | Advances and Open Problems in Federated Learning | Kairouz 等 | 2019 | [arXiv:1912.04977](https://arxiv.org/abs/1912.04977) | [PDF](papers/C0_survey_taxonomy/kairouz2019advances_1912.04977.pdf) |  |
| `zhang2025flpoison` | SoK: Benchmarking Poisoning Attacks and Defenses in Federated Learning | Zhang 等 | 2025 | [arXiv:2502.03801](https://arxiv.org/abs/2502.03801) | [PDF](papers/C0_survey_taxonomy/zhang2025flpoison_2502.03801.pdf) | FLPoison 基准 |
| `sheng2022backdoornlp` | A Survey on Backdoor Attack and Defense in Natural Language Processing | Sheng 等 | 2022 | [arXiv:2211.11958](https://arxiv.org/abs/2211.11958) | [PDF](papers/C0_survey_taxonomy/sheng2022backdoornlp_2211.11958.pdf) |  |

## C1_fl_lora_foundations

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `mcmahan2017fedavg` | Communication-Efficient Learning of Deep Networks from Decentralized Data | McMahan 等 | 2016 | [arXiv:1602.05629](https://arxiv.org/abs/1602.05629) | [PDF](papers/C1_fl_lora_foundations/mcmahan2017fedavg_1602.05629.pdf) | FedAvg |
| `hu2021lora` | LoRA: Low-Rank Adaptation of Large Language Models | Hu 等 | 2021 | [arXiv:2106.09685](https://arxiv.org/abs/2106.09685) | [PDF](papers/C1_fl_lora_foundations/hu2021lora_2106.09685.pdf) |  |
| `dettmers2023qlora` | QLoRA: Efficient Finetuning of Quantized LLMs | Dettmers 等 | 2023 | [arXiv:2305.14314](https://arxiv.org/abs/2305.14314) | [PDF](papers/C1_fl_lora_foundations/dettmers2023qlora_2305.14314.pdf) | 本机小显存实验依据 |
| `zhang2023fedit` | Towards Building the Federated GPT: Federated Instruction Tuning | Zhang 等 | 2023 | [arXiv:2305.05644](https://arxiv.org/abs/2305.05644) | [PDF](papers/C1_fl_lora_foundations/zhang2023fedit_2305.05644.pdf) | Shepherd/FedIT |
| `ye2024openfedllm` | OpenFedLLM: Training Large Language Models on Decentralized Private Data via Federated Learning | Ye 等 | 2024 | [arXiv:2402.06954](https://arxiv.org/abs/2402.06954) | [PDF](papers/C1_fl_lora_foundations/ye2024openfedllm_2402.06954.pdf) |  |
| `ye2024fedllmbench` | FedLLM-Bench: Realistic Benchmarks for Federated Learning of Large Language Models | Ye 等 | 2024 | [arXiv:2406.04845](https://arxiv.org/abs/2406.04845) | [PDF](papers/C1_fl_lora_foundations/ye2024fedllmbench_2406.04845.pdf) | 自然 non-IID |
| `sun2024ffalora` | Improving LoRA in Privacy-preserving Federated Learning | Sun 等 | 2024 | [arXiv:2403.12313](https://arxiv.org/abs/2403.12313) | [PDF](papers/C1_fl_lora_foundations/sun2024ffalora_2403.12313.pdf) | FFA-LoRA，A/B 聚合不一致 |
| `wang2024flora` | FLoRA: Federated Fine-Tuning Large Language Models with Heterogeneous Low-Rank Adaptations | Wang 等 | 2024 | [arXiv:2409.05976](https://arxiv.org/abs/2409.05976) | [PDF](papers/C1_fl_lora_foundations/wang2024flora_2409.05976.pdf) | 堆叠式无噪声聚合 |
| `bonawitz2016secagg` | Practical Secure Aggregation for Federated Learning on User-Held Data | Bonawitz 等 | 2016 | [arXiv:1611.04482](https://arxiv.org/abs/1611.04482) | [PDF](papers/C1_fl_lora_foundations/bonawitz2016secagg_1611.04482.pdf) | 安全聚合 |
| `ouyang2022instructgpt` | Training language models to follow instructions with human feedback | Ouyang 等 | 2022 | [arXiv:2203.02155](https://arxiv.org/abs/2203.02155) | [PDF](papers/C1_fl_lora_foundations/ouyang2022instructgpt_2203.02155.pdf) | SFT/RM/PPO 阶段划分 |
| `rafailov2023dpo` | Direct Preference Optimization: Your Language Model is Secretly a Reward Model | Rafailov 等 | 2023 | [arXiv:2305.18290](https://arxiv.org/abs/2305.18290) | [PDF](papers/C1_fl_lora_foundations/rafailov2023dpo_2305.18290.pdf) |  |

## C2_fl_poisoning_attacks

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `sun2024vaguegan` | A Model Consistency-Based Countermeasure to GAN-Based Data Poisoning Attack in Federated Learning | Sun 等 | 2024 | [arXiv:2405.11440](https://arxiv.org/abs/2405.11440) | [PDF](papers/C2_fl_poisoning_attacks/sun2024vaguegan_2405.11440.pdf) | 孙蔚 VagueGAN+MCD |
| `sun2026pcdm` | PCDM: A Diffusion-Based Data Poisoning Attack Against Federated Learning Systems | Sun 等 | 2026 | [arXiv:2605.16098](https://arxiv.org/abs/2605.16098) | [PDF](papers/C2_fl_poisoning_attacks/sun2026pcdm_2605.16098.pdf) | 孙蔚/高博 扩散投毒，LSDAM 后续 |
| `tolpegin2020dataflip` | Data Poisoning Attacks Against Federated Learning Systems | Tolpegin 等 | 2020 | [arXiv:2007.08432](https://arxiv.org/abs/2007.08432) | [PDF](papers/C2_fl_poisoning_attacks/tolpegin2020dataflip_2007.08432.pdf) | 标签翻转 |
| `bagdasaryan2020backdoor` | How To Backdoor Federated Learning | Bagdasaryan 等 | 2018 | [arXiv:1807.00459](https://arxiv.org/abs/1807.00459) | [PDF](papers/C2_fl_poisoning_attacks/bagdasaryan2020backdoor_1807.00459.pdf) | 模型替换 |
| `fang2020local` | Local Model Poisoning Attacks to Byzantine-Robust Federated Learning | Fang 等 | 2019 | [arXiv:1911.11815](https://arxiv.org/abs/1911.11815) | [PDF](papers/C2_fl_poisoning_attacks/fang2020local_1911.11815.pdf) |  |
| `baruch2019little` | A Little Is Enough: Circumventing Defenses For Distributed Learning | Baruch 等 | 2019 | [arXiv:1902.06156](https://arxiv.org/abs/1902.06156) | [PDF](papers/C2_fl_poisoning_attacks/baruch2019little_1902.06156.pdf) | ALIE |
| `wang2020tails` | Attack of the Tails: Yes, You Really Can Backdoor Federated Learning | Wang 等 | 2020 | [arXiv:2007.05084](https://arxiv.org/abs/2007.05084) | [PDF](papers/C2_fl_poisoning_attacks/wang2020tails_2007.05084.pdf) | edge-case |
| `zhang2022neurotoxin` | Neurotoxin: Durable Backdoors in Federated Learning | Zhang 等 | 2022 | [arXiv:2206.10341](https://arxiv.org/abs/2206.10341) | [PDF](papers/C2_fl_poisoning_attacks/zhang2022neurotoxin_2206.10341.pdf) | 持久后门 |
| `xie2020dba` | DBA: Distributed Backdoor Attacks against Federated Learning | Xie 等 | 2020 | [ICLR](https://openreview.net/pdf?id=rkgyS0VFvr) | 未获取 | 分布式后门 |
| `shejwalkar2021manipulating` | Manipulating the Byzantine: Optimizing Model Poisoning Attacks and Defenses for Federated Learning | Shejwalkar 等 | 2021 | [NDSS](https://www.ndss-symposium.org/wp-content/uploads/ndss2021_6C-3_24498_paper.pdf) | [PDF](papers/C2_fl_poisoning_attacks/shejwalkar2021manipulating.pdf) | NDSS 2021, DnC |
| `sun2024thesis` | 生成式模型在联邦学习安全中的应用研究 | 孙蔚 | 2024 | 北京交通大学 | [PDF](papers/C2_fl_poisoning_attacks/sun2024thesis.pdf) | VagueGAN / MCD / LSDAM / CAEKL |
| `li2026thesis` | 基于混合专家模型的联邦学习隐蔽攻击方法研究 | 李庆庆 | 2026 | 北京交通大学 | [PDF](papers/C2_fl_poisoning_attacks/li2026thesis.pdf) | MoEGAN / SMA |

## C3_fl_robust_defenses

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `blanchard2017krum` | Byzantine-Tolerant Machine Learning | Blanchard 等 | 2017 | [arXiv:1703.02757](https://arxiv.org/abs/1703.02757) | [PDF](papers/C3_fl_robust_defenses/blanchard2017krum_1703.02757.pdf) | Krum |
| `yin2018median` | Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates | Yin 等 | 2018 | [arXiv:1803.01498](https://arxiv.org/abs/1803.01498) | [PDF](papers/C3_fl_robust_defenses/yin2018median_1803.01498.pdf) | Median/Trimmed mean |
| `fung2018foolsgold` | Mitigating Sybils in Federated Learning Poisoning | Fung 等 | 2018 | [arXiv:1808.04866](https://arxiv.org/abs/1808.04866) | [PDF](papers/C3_fl_robust_defenses/fung2018foolsgold_1808.04866.pdf) | FoolsGold |
| `sun2019clipping` | Can You Really Backdoor Federated Learning? | Sun 等 | 2019 | [arXiv:1911.07963](https://arxiv.org/abs/1911.07963) | [PDF](papers/C3_fl_robust_defenses/sun2019clipping_1911.07963.pdf) | 范数裁剪 |
| `cao2020fltrust` | FLTrust: Byzantine-robust Federated Learning via Trust Bootstrapping | Cao 等 | 2020 | [arXiv:2012.13995](https://arxiv.org/abs/2012.13995) | [PDF](papers/C3_fl_robust_defenses/cao2020fltrust_2012.13995.pdf) | 服务器根数据集 |
| `nguyen2022flame` | FLAME: Taming Backdoors in Federated Learning (Extended Version 1) | Nguyen 等 | 2021 | [arXiv:2101.02281](https://arxiv.org/abs/2101.02281) | [PDF](papers/C3_fl_robust_defenses/nguyen2022flame_2101.02281.pdf) |  |
| `rieger2022deepsight` | DeepSight: Mitigating Backdoor Attacks in Federated Learning Through Deep Model Inspection | Rieger 等 | 2022 | [arXiv:2201.00763](https://arxiv.org/abs/2201.00763) | [PDF](papers/C3_fl_robust_defenses/rieger2022deepsight_2201.00763.pdf) |  |
| `zhang2022fldetector` | FLDetector: Defending Federated Learning Against Model Poisoning Attacks via Detecting Malicious Clients | Zhang 等 | 2022 | [arXiv:2207.09209](https://arxiv.org/abs/2207.09209) | [PDF](papers/C3_fl_robust_defenses/zhang2022fldetector_2207.09209.pdf) | 跨轮一致性，与 MCD 纵向对照 |
| `li2022lomar` | LoMar: A Local Defense Against Poisoning Attack on Federated Learning | Li 等 | 2022 | [arXiv:2201.02873](https://arxiv.org/abs/2201.02873) | [PDF](papers/C3_fl_robust_defenses/li2022lomar_2201.02873.pdf) |  |
| `fereidooni2024freqfed` | FreqFed: A Frequency Analysis-Based Approach for Mitigating Poisoning Attacks in Federated Learning | Fereidooni 等 | 2023 | [arXiv:2312.04432](https://arxiv.org/abs/2312.04432) | [PDF](papers/C3_fl_robust_defenses/fereidooni2024freqfed_2312.04432.pdf) | DCT 频域，ProtegoFed 组合对象 |

## C4_llm_pretrain_poisoning

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `carlini2023webscale` | Poisoning Web-Scale Training Datasets is Practical | Carlini 等 | 2023 | [arXiv:2302.10149](https://arxiv.org/abs/2302.10149) | [PDF](papers/C4_llm_pretrain_poisoning/carlini2023webscale_2302.10149.pdf) |  |
| `zhang2024persistent` | Persistent Pre-Training Poisoning of LLMs | Zhang 等 | 2024 | [arXiv:2410.13722](https://arxiv.org/abs/2410.13722) | [PDF](papers/C4_llm_pretrain_poisoning/zhang2024persistent_2410.13722.pdf) | 跨阶段持久性 |
| `souly2025constant` | Poisoning Attacks on LLMs Require a Near-constant Number of Poison Samples | Souly 等 | 2025 | [arXiv:2510.07192](https://arxiv.org/abs/2510.07192) | [PDF](papers/C4_llm_pretrain_poisoning/souly2025constant_2510.07192.pdf) |  |
| `hubinger2024sleeper` | Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training | Hubinger 等 | 2024 | [arXiv:2401.05566](https://arxiv.org/abs/2401.05566) | [PDF](papers/C4_llm_pretrain_poisoning/hubinger2024sleeper_2401.05566.pdf) | 后门跨安全训练保持 |
| `persistcontinual2025` | Persistent Backdoor Attacks under Continual Fine-Tuning of LLMs | Cui 等 | 2025 | [arXiv:2512.14741](https://arxiv.org/abs/2512.14741) | [PDF](papers/C4_llm_pretrain_poisoning/persistcontinual2025_2512.14741.pdf) | AAAI，后门跨持续微调保持 |

## C5_llm_sft_poisoning

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `wan2023instruction` | Poisoning Language Models During Instruction Tuning | Wan 等 | 2023 | [arXiv:2305.00944](https://arxiv.org/abs/2305.00944) | [PDF](papers/C5_llm_sft_poisoning/wan2023instruction_2305.00944.pdf) |  |
| `shu2023autopoison` | On the Exploitability of Instruction Tuning | Shu 等 | 2023 | [arXiv:2306.17194](https://arxiv.org/abs/2306.17194) | [PDF](papers/C5_llm_sft_poisoning/shu2023autopoison_2306.17194.pdf) | AutoPoison |
| `yan2023vpi` | Backdooring Instruction-Tuned Large Language Models with Virtual Prompt Injection | Yan 等 | 2023 | [arXiv:2307.16888](https://arxiv.org/abs/2307.16888) | [PDF](papers/C5_llm_sft_poisoning/yan2023vpi_2307.16888.pdf) | 语义触发 |
| `xu2023instructionsbackdoor` | Instructions as Backdoors: Backdoor Vulnerabilities of Instruction Tuning for Large Language Models | Xu 等 | 2023 | [arXiv:2305.14710](https://arxiv.org/abs/2305.14710) | [PDF](papers/C5_llm_sft_poisoning/xu2023instructionsbackdoor_2305.14710.pdf) |  |
| `qi2023finetuning` | Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To! | Qi 等 | 2023 | [arXiv:2310.03693](https://arxiv.org/abs/2310.03693) | [PDF](papers/C5_llm_sft_poisoning/qi2023finetuning_2310.03693.pdf) | 身份切换、良性数据退化 |
| `yang2023shadow` | Shadow Alignment: The Ease of Subverting Safely-Aligned Language Models | Yang 等 | 2023 | [arXiv:2310.02949](https://arxiv.org/abs/2310.02949) | [PDF](papers/C5_llm_sft_poisoning/yang2023shadow_2310.02949.pdf) |  |
| `he2024safedata` | What is in Your Safe Data? Identifying Benign Data that Breaks Safety | He 等 | 2024 | [arXiv:2404.01099](https://arxiv.org/abs/2404.01099) | [PDF](papers/C5_llm_sft_poisoning/he2024safedata_2404.01099.pdf) | 表面良性投毒，梯度/表示锚定 |
| `halawi2024covert` | Covert Malicious Finetuning: Challenges in Safeguarding LLM Adaptation | Halawi 等 | 2024 | [arXiv:2406.20053](https://arxiv.org/abs/2406.20053) | [PDF](papers/C5_llm_sft_poisoning/halawi2024covert_2406.20053.pdf) | 编码隐蔽有害微调 |
| `li2024backdoorllm` | BackdoorLLM: A Comprehensive Benchmark for Backdoor Attacks and Defenses on Large Language Models | Li 等 | 2024 | [arXiv:2408.12798](https://arxiv.org/abs/2408.12798) | [PDF](papers/C5_llm_sft_poisoning/li2024backdoorllm_2408.12798.pdf) |  |
| `qi2021hiddenkiller` | Hidden Killer: Invisible Textual Backdoor Attacks with Syntactic Trigger | Qi 等 | 2021 | [arXiv:2105.12400](https://arxiv.org/abs/2105.12400) | [PDF](papers/C5_llm_sft_poisoning/qi2021hiddenkiller_2105.12400.pdf) |  |
| `qi2021stylebkd` | Mind the Style of Text! Adversarial and Backdoor Attacks Based on Text Style Transfer | Qi 等 | 2021 | [arXiv:2110.07139](https://arxiv.org/abs/2110.07139) | [PDF](papers/C5_llm_sft_poisoning/qi2021stylebkd_2110.07139.pdf) | StyleBkd |
| `betley2025emergent` | Emergent Misalignment: Narrow finetuning can produce broadly misaligned LLMs | Betley 等 | 2025 | [arXiv:2502.17424](https://arxiv.org/abs/2502.17424) | [PDF](papers/C5_llm_sft_poisoning/betley2025emergent_2502.17424.pdf) |  |
| `harmlessinputs2025` | Revisiting Backdoor Attacks on LLMs: A Stealthy and Practical Poisoning Framework via Harmless Inputs | Kong 等 | 2025 | [arXiv:2505.17601](https://arxiv.org/abs/2505.17601) | [PDF](papers/C5_llm_sft_poisoning/harmlessinputs2025_2505.17601.pdf) | 无害输入隐蔽后门 |

## C6_llm_preference_poisoning

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `rando2023universal` | Universal Jailbreak Backdoors from Poisoned Human Feedback | Rando 等 | 2023 | [arXiv:2311.14455](https://arxiv.org/abs/2311.14455) | [PDF](papers/C6_llm_preference_poisoning/rando2023universal_2311.14455.pdf) |  |
| `baumgartner2024venom` | Best-of-Venom: Attacking RLHF by Injecting Poisoned Preference Data | Baumgärtner 等 | 2024 | [arXiv:2404.05530](https://arxiv.org/abs/2404.05530) | [PDF](papers/C6_llm_preference_poisoning/baumgartner2024venom_2404.05530.pdf) |  |
| `wang2023rlhfpoison` | RLHFPoison: Reward Poisoning Attack for Reinforcement Learning with Human Feedback in Large Language Models | Wang 等 | 2023 | [arXiv:2311.09641](https://arxiv.org/abs/2311.09641) | [PDF](papers/C6_llm_preference_poisoning/wang2023rlhfpoison_2311.09641.pdf) |  |
| `pathmanathan2024dpo` | Is poisoning a real threat to LLM alignment? Maybe more so than you think | Pathmanathan 等 | 2024 | [arXiv:2406.12091](https://arxiv.org/abs/2406.12091) | [PDF](papers/C6_llm_preference_poisoning/pathmanathan2024dpo_2406.12091.pdf) | DPO 投毒 |
| `fu2024poisonbench` | PoisonBench: Assessing Large Language Model Vulnerability to Data Poisoning | Fu 等 | 2024 | [arXiv:2410.08811](https://arxiv.org/abs/2410.08811) | [PDF](papers/C6_llm_preference_poisoning/fu2024poisonbench_2410.08811.pdf) |  |
| `prefpoison2026` | Efficient Preference Poisoning Attack on Offline RLHF | Yang 等 | 2026 | [arXiv:2605.02495](https://arxiv.org/abs/2605.02495) | [PDF](papers/C6_llm_preference_poisoning/prefpoison2026_2605.02495.pdf) | DPO 标签翻转 |
| `adversarialrlhf2025` | LLM Misalignment via Adversarial RLHF Platforms | Entezami 等 | 2025 | [arXiv:2503.03039](https://arxiv.org/abs/2503.03039) | [PDF](papers/C6_llm_preference_poisoning/adversarialrlhf2025_2503.03039.pdf) |  |
| `great2025` | GREAT: Generalizable Backdoor Attacks in RLHF via Emotion-Aware Trigger Synthesis | Dutta 等 | 2025 | [arXiv:2510.09260](https://arxiv.org/abs/2510.09260) | [PDF](papers/C6_llm_preference_poisoning/great2025_2510.09260.pdf) |  |

## C7_harmful_ft_defenses

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `huang2024vaccine` | Vaccine: Perturbation-aware Alignment for Large Language Models against Harmful Fine-tuning Attack | Huang 等 | 2024 | [arXiv:2402.01109](https://arxiv.org/abs/2402.01109) | [PDF](papers/C7_harmful_ft_defenses/huang2024vaccine_2402.01109.pdf) | 对齐阶段 |
| `huang2024booster` | Booster: Tackling Harmful Fine-tuning for Large Language Models via Attenuating Harmful Perturbation | Huang 等 | 2024 | [arXiv:2409.01586](https://arxiv.org/abs/2409.01586) | [PDF](papers/C7_harmful_ft_defenses/huang2024booster_2409.01586.pdf) | 对齐阶段 |
| `rosati2024repnoise` | Representation Noising: A Defence Mechanism Against Harmful Finetuning | Rosati 等 | 2024 | [arXiv:2405.14577](https://arxiv.org/abs/2405.14577) | [PDF](papers/C7_harmful_ft_defenses/rosati2024repnoise_2405.14577.pdf) | 对齐阶段 |
| `tamirisa2024tar` | Tamper-Resistant Safeguards for Open-Weight LLMs | Tamirisa 等 | 2024 | [arXiv:2408.00761](https://arxiv.org/abs/2408.00761) | [PDF](papers/C7_harmful_ft_defenses/tamirisa2024tar_2408.00761.pdf) | 对齐阶段 |
| `huang2024lisa` | Lisa: Lazy Safety Alignment for Large Language Models against Harmful Fine-tuning Attack | Huang 等 | 2024 | [arXiv:2405.18641](https://arxiv.org/abs/2405.18641) | [PDF](papers/C7_harmful_ft_defenses/huang2024lisa_2405.18641.pdf) | 微调阶段 |
| `bianchi2023safetytuned` | Safety-Tuned LLaMAs: Lessons From Improving the Safety of Large Language Models that Follow Instructions | Bianchi 等 | 2023 | [arXiv:2309.07875](https://arxiv.org/abs/2309.07875) | [PDF](papers/C7_harmful_ft_defenses/bianchi2023safetytuned_2309.07875.pdf) | 微调阶段混入安全数据 |
| `wang2024bea` | Mitigating Fine-tuning based Jailbreak Attack with Backdoor Enhanced Safety Alignment | Wang 等 | 2024 | [arXiv:2402.14968](https://arxiv.org/abs/2402.14968) | [PDF](papers/C7_harmful_ft_defenses/wang2024bea_2402.14968.pdf) | 微调阶段 |
| `shen2024seal` | SEAL: Safety-enhanced Aligned LLM Fine-tuning via Bilevel Data Selection | Shen 等 | 2024 | [arXiv:2410.07471](https://arxiv.org/abs/2410.07471) | [PDF](papers/C7_harmful_ft_defenses/shen2024seal_2410.07471.pdf) | 数据选择 |
| `hsu2024safelora` | Safe LoRA: the Silver Lining of Reducing Safety Risks when Fine-tuning Large Language Models | Hsu 等 | 2024 | [arXiv:2405.16833](https://arxiv.org/abs/2405.16833) | [PDF](papers/C7_harmful_ft_defenses/hsu2024safelora_2405.16833.pdf) | 微调后，LoRA 投影 |
| `huang2024antidote` | Antidote: Post-fine-tuning Safety Alignment for Large Language Models against Harmful Fine-tuning | Huang 等 | 2024 | [arXiv:2408.09600](https://arxiv.org/abs/2408.09600) | [PDF](papers/C7_harmful_ft_defenses/huang2024antidote_2408.09600.pdf) | 微调后剪枝 |
| `inan2023llamaguard` | Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations | Inan 等 | 2023 | [arXiv:2312.06674](https://arxiv.org/abs/2312.06674) | [PDF](papers/C7_harmful_ft_defenses/inan2023llamaguard_2312.06674.pdf) | 数据/行为审查器 |
| `li2024saladbench` | SALAD-Bench: A Hierarchical and Comprehensive Safety Benchmark for Large Language Models | Li 等 | 2024 | [arXiv:2402.05044](https://arxiv.org/abs/2402.05044) | [PDF](papers/C7_harmful_ft_defenses/li2024saladbench_2402.05044.pdf) | MD-Judge |

## C8_sample_level_detection

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `tran2018spectral` | Spectral Signatures in Backdoor Attacks | Tran 等 | 2018 | [arXiv:1811.00636](https://arxiv.org/abs/1811.00636) | [PDF](papers/C8_sample_level_detection/tran2018spectral_1811.00636.pdf) | 表示谱检测 |
| `chen2018activation` | Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering | Chen 等 | 2018 | [arXiv:1811.03728](https://arxiv.org/abs/1811.03728) | [PDF](papers/C8_sample_level_detection/chen2018activation_1811.03728.pdf) |  |
| `qi2021onion` | ONION: A Simple and Effective Defense Against Textual Backdoor Attacks | Qi 等 | 2020 | [arXiv:2011.10369](https://arxiv.org/abs/2011.10369) | [PDF](papers/C8_sample_level_detection/qi2021onion_2011.10369.pdf) | 困惑度 |
| `gao2019strip` | STRIP: A Defence Against Trojan Attacks on Deep Neural Networks | Gao 等 | 2019 | [arXiv:1902.06531](https://arxiv.org/abs/1902.06531) | [PDF](papers/C8_sample_level_detection/gao2019strip_1902.06531.pdf) |  |
| `cui2022openbackdoor` | A Unified Evaluation of Textual Backdoor Learning: Frameworks and Benchmarks | Cui 等 | 2022 | [arXiv:2206.08514](https://arxiv.org/abs/2206.08514) | [PDF](papers/C8_sample_level_detection/cui2022openbackdoor_2206.08514.pdf) | CUBE/OpenBackdoor |
| `xie2024gradsafe` | GradSafe: Detecting Jailbreak Prompts for LLMs via Safety-Critical Gradient Analysis | Xie 等 | 2024 | [arXiv:2402.13494](https://arxiv.org/abs/2402.13494) | [PDF](papers/C8_sample_level_detection/xie2024gradsafe_2402.13494.pdf) | 梯度特征 |
| `xia2024less` | LESS: Selecting Influential Data for Targeted Instruction Tuning | Xia 等 | 2024 | [arXiv:2402.04333](https://arxiv.org/abs/2402.04333) | [PDF](papers/C8_sample_level_detection/xia2024less_2402.04333.pdf) | LoRA 梯度+随机投影 |
| `gradsentry2026` | GradSentry: Gradient Spectral Entropy for Backdoor Sample Filtering in Large Language Model Fine-Tuning | Zhao 等 | 2026 | [arXiv:2605.26574](https://arxiv.org/abs/2605.26574) | [PDF](papers/C8_sample_level_detection/gradsentry2026_2605.26574.pdf) |  |

## C9_fedllm_attack_defense

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `ye2024emerging` | Emerging Safety Attack and Defense in Federated Instruction Tuning of Large Language Models | Ye 等 | 2024 | [arXiv:2406.10630](https://arxiv.org/abs/2406.10630) | [PDF](papers/C9_fedllm_attack_defense/ye2024emerging_2406.10630.pdf) | ICLR 2025，本地已有 |
| `protegofed2026` | ProtegoFed: Backdoor-Free Federated Instruction Tuning with Interspersed Poisoned Data | Zhao 等 | 2026 | [arXiv:2603.00516](https://arxiv.org/abs/2603.00516) | [PDF](papers/C9_fedllm_attack_defense/protegofed2026_2603.00516.pdf) | 本地已有 |
| `safefedllm2026` | Safe-FedLLM: Delving into the Safety of Federated Large Language Models | Tao 等 | 2026 | [arXiv:2601.07177](https://arxiv.org/abs/2601.07177) | [PDF](papers/C9_fedllm_attack_defense/safefedllm2026_2601.07177.pdf) | ACL 2026 |
| `signalagg2026` | Revisiting Backdoor Threat in Federated Instruction Tuning from a Signal Aggregation Perspective | Zhao 等 | 2026 | [arXiv:2602.15671](https://arxiv.org/abs/2602.15671) | [PDF](papers/C9_fedllm_attack_defense/signalagg2026_2602.15671.pdf) | ICASSP 2026 |
| `li2024peftattack` | PEFT-as-an-Attack! Jailbreaking Language Models during Federated Parameter-Efficient Fine-Tuning | Li 等 | 2024 | [arXiv:2411.19335](https://arxiv.org/abs/2411.19335) | [PDF](papers/C9_fedllm_attack_defense/li2024peftattack_2411.19335.pdf) |  |
| `graphmanip2026` | Graph Representation Learning Augmented Model Manipulation on Federated Fine-Tuning of LLMs | Cai 等 | 2026 | [arXiv:2605.07961](https://arxiv.org/abs/2605.07961) | [PDF](papers/C9_fedllm_attack_defense/graphmanip2026_2605.07961.pdf) |  |
| `tokenlora2026` | Token-Level Generalization in LoRA Adapter Backdoors: Attack Characterization and Behavioral Detection | Lelle | 2026 | [arXiv:2605.30189](https://arxiv.org/abs/2605.30189) | [PDF](papers/C9_fedllm_attack_defense/tokenlora2026_2605.30189.pdf) |  |
| `fedllmprivacy2025` | Can Federated Learning Safeguard Private Data in LLM Training? Vulnerabilities, Attacks, and Defense Evaluation | Guo 等 | 2025 | [arXiv:2509.20680](https://arxiv.org/abs/2509.20680) | [PDF](papers/C9_fedllm_attack_defense/fedllmprivacy2025_2509.20680.pdf) |  |

## C10_lora_supplychain_privacy

| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |
|---|---|---|---|---|---|---|
| `liu2024loratk` | LoRATK: LoRA Once, Backdoor Everywhere in the Share-and-Play Ecosystem | Liu 等 | 2024 | [arXiv:2403.00108](https://arxiv.org/abs/2403.00108) | [PDF](papers/C10_lora_supplychain_privacy/liu2024loratk_2403.00108.pdf) |  |
| `dong2024trojanplugin` | The Philosopher's Stone: Trojaning Plugins of Large Language Models | Dong 等 | 2023 | [arXiv:2312.00374](https://arxiv.org/abs/2312.00374) | [PDF](papers/C10_lora_supplychain_privacy/dong2024trojanplugin_2312.00374.pdf) |  |
| `balunovic2022lamp` | LAMP: Extracting Text from Gradients with Language Model Priors | Balunović 等 | 2022 | [arXiv:2202.08827](https://arxiv.org/abs/2202.08827) | [PDF](papers/C10_lora_supplychain_privacy/balunovic2022lamp_2202.08827.pdf) |  |
| `rethinklora2026` | Rethinking LoRA for Privacy-Preserving Federated Learning in Large Models | Liu 等 | 2026 | [arXiv:2602.19926](https://arxiv.org/abs/2602.19926) | [PDF](papers/C10_lora_supplychain_privacy/rethinklora2026_2602.19926.pdf) |  |
| `gupta2022film` | Recovering Private Text in Federated Learning of Language Models | Gupta 等 | 2022 | [arXiv:2205.08514](https://arxiv.org/abs/2205.08514) | [PDF](papers/C10_lora_supplychain_privacy/gupta2022film_2205.08514.pdf) |  |
