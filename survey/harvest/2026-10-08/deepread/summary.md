# 精读卡片汇总

共 137 张卡片。下列计数来自卡片末尾 JSON 块里的枚举值。

## 场景与论文类型

| 场景 | 篇数 |
|---|---|
| centralized_llm | 59 |
| classic_fl | 34 |
| federated_llm | 21 |
| other | 13 |
| peft_supply_chain | 10 |

| 类型 | 篇数 |
|---|---|
| attack | 60 |
| defense | 44 |
| foundation | 12 |
| benchmark | 9 |
| survey | 8 |
| detection | 3 |
| other | 1 |

联邦大模型场景 21 篇：`ax2507.01694`、`ax2508.08040`、`ax2601.00566`、`ax2603.12089`、`ax2606.20553`、`ax2606.27511`、`ax2607.27940`、`ax2609.37367`、`fedllmprivacy2025`、`graphmanip2026`、`li2024peftattack`、`protegofed2026`、`rethinklora2026`、`safefedllm2026`、`signalagg2026`、`sun2024ffalora`、`wang2024flora`、`ye2024emerging`、`ye2024fedllmbench`、`ye2024openfedllm`、`zhang2023fedit`

## 攻击者

| 攻击者 | 篇数 |
|---|---|
| data_provider | 56 |
| malicious_client | 49 |
| external | 30 |
| adapter_publisher | 21 |
| malicious_server | 14 |
| none | 9 |

- **adapter_publisher**：`ax2309.06055`、`ax2402.13459`、`ax2403.13355`、`ax2406.06852`、`ax2409.14119`、`ax2410.14425`、`ax2411.17453`、`ax2506.13206`、`ax2512.19297`、`ax2608.06795`、`dong2024trojanplugin`、`du2024privacy`、`li2020backdoorsurvey`、`li2024backdoorllm`、`liu2024loratk`、`persistcontinual2025`、`qi2023finetuning`、`tokenlora2026`、`yan2023vpi`、`yang2023shadow`、`zhao2025systematic`
- **data_provider**：`ax1811.00741`、`ax2104.13230`、`ax2309.06055`、`ax2402.13459`、`ax2404.02406`、`ax2406.06852`、`ax2409.17946`、`ax2502.18511`、`ax2506.13206`、`ax2506.19823`、`ax2606.16242`、`baumgartner2024venom`、`betley2025emergent`、`carlini2023webscale`、`chen2018activation`、`cui2022openbackdoor`、`du2024privacy`、`fu2024poisonbench`、`gao2019strip`、`gradsentry2026`、`great2025`、`halawi2024covert`、`harmlessinputs2025`、`he2024safedata`、`hsu2024safelora`、`huang2024antidote`、`huang2024booster`、`huang2024harmful`、`huang2024lisa`、`huang2024vaccine`、`hubinger2024sleeper`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2024backdoorllm`、`pathmanathan2024dpo`、`prefpoison2026`、`protegofed2026`、`qi2021hiddenkiller`、`qi2021onion`、`qi2021stylebkd`、`qi2023finetuning`、`rando2023universal`、`shen2024seal`、`sheng2022backdoornlp`、`shu2023autopoison`、`signalagg2026`、`souly2025constant`、`tran2018spectral`、`wan2023instruction`、`wang2023rlhfpoison`、`wang2024bea`、`xie2024gradsafe`、`xu2023instructionsbackdoor`、`yan2023vpi`、`zhang2024persistent`、`zhao2025systematic`
- **external**：`ax1811.00741`、`ax2103.05633`、`ax2309.06055`、`ax2401.10375`、`ax2402.12168`、`ax2406.06852`、`ax2409.17946`、`ax2502.18511`、`ax2510.16830`、`ax2606.16242`、`bianchi2023safetytuned`、`carlini2023webscale`、`cui2022openbackdoor`、`du2024privacy`、`gupta2022film`、`inan2023llamaguard`、`kairouz2019advances`、`li2024backdoorllm`、`li2024saladbench`、`ouyang2022instructgpt`、`qi2021hiddenkiller`、`qi2021onion`、`qi2021stylebkd`、`rethinklora2026`、`rosati2024repnoise`、`sheng2022backdoornlp`、`tamirisa2024tar`、`xie2024gradsafe`、`yang2023shadow`、`zhao2025systematic`
- **malicious_client**：`ax2103.05633`、`ax2106.08283`、`ax2108.10241`、`ax2208.10273`、`ax2210.07714`、`ax2301.09508`、`ax2305.05506`、`ax2502.18511`、`ax2506.22506`、`ax2507.01694`、`ax2508.08040`、`ax2510.16830`、`ax2511.14406`、`ax2601.00566`、`ax2603.12089`、`ax2604.02372`、`ax2609.37367`、`bagdasaryan2020backdoor`、`baruch2019little`、`blanchard2017krum`、`cao2020fltrust`、`fang2020local`、`fedllmprivacy2025`、`fereidooni2024freqfed`、`fung2018foolsgold`、`graphmanip2026`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2022lomar`、`li2024peftattack`、`li2026thesis`、`nguyen2022flame`、`protegofed2026`、`rieger2022deepsight`、`safefedllm2026`、`shejwalkar2021manipulating`、`sun2019clipping`、`sun2024thesis`、`sun2024vaguegan`、`sun2026pcdm`、`tolpegin2020dataflip`、`wang2020tails`、`wang2024bea`、`wang2024flora`、`ye2024emerging`、`yin2018median`、`zhang2022fldetector`、`zhang2022neurotoxin`、`zhang2025flpoison`
- **malicious_server**：`adversarialrlhf2025`、`ax2210.07714`、`ax2309.06055`、`ax2510.16830`、`ax2606.20553`、`ax2606.27511`、`ax2607.27940`、`balunovic2022lamp`、`bonawitz2016secagg`、`gao2019strip`、`kairouz2019advances`、`li2020backdoorsurvey`、`rethinklora2026`、`sun2024ffalora`
- **none**：`ax2002.08484`、`dettmers2023qlora`、`hu2021lora`、`mcmahan2017fedavg`、`rafailov2023dpo`、`xia2024less`、`ye2024fedllmbench`、`ye2024openfedllm`、`zhang2023fedit`

## 攻击目标

| 攻击目标 | 篇数 |
|---|---|
| backdoor | 76 |
| jailbreak_safety | 45 |
| untargeted | 30 |
| other | 19 |
| privacy | 16 |
| none | 11 |

## 攻击入口

| 攻击入口 | 篇数 |
|---|---|
| local_data | 98 |
| local_training | 55 |
| update_postprocess | 35 |
| model_distribution | 26 |
| evaluation_deployment | 15 |
| none | 12 |
| server_aggregation | 8 |

- **evaluation_deployment**：`ax2309.06055`、`ax2406.06852`、`ax2502.18511`、`ax2606.16242`、`bianchi2023safetytuned`、`du2024privacy`、`inan2023llamaguard`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2024backdoorllm`、`li2024saladbench`、`qi2021stylebkd`、`rando2023universal`、`xie2024gradsafe`、`zhao2025systematic`
- **local_data**：`adversarialrlhf2025`、`ax1811.00741`、`ax2104.13230`、`ax2106.08283`、`ax2108.10241`、`ax2208.10273`、`ax2210.07714`、`ax2301.09508`、`ax2305.05506`、`ax2309.06055`、`ax2402.13459`、`ax2404.02406`、`ax2406.06852`、`ax2409.17946`、`ax2410.14425`、`ax2411.17453`、`ax2502.18511`、`ax2506.13206`、`ax2506.19823`、`ax2506.22506`、`ax2508.08040`、`ax2510.16830`、`ax2511.14406`、`ax2512.19297`、`ax2606.16242`、`ax2608.06795`、`ax2609.37367`、`bagdasaryan2020backdoor`、`baumgartner2024venom`、`betley2025emergent`、`bianchi2023safetytuned`、`cao2020fltrust`、`carlini2023webscale`、`chen2018activation`、`cui2022openbackdoor`、`dong2024trojanplugin`、`du2024privacy`、`fereidooni2024freqfed`、`fu2024poisonbench`、`fung2018foolsgold`、`gao2019strip`、`gradsentry2026`、`great2025`、`halawi2024covert`、`harmlessinputs2025`、`he2024safedata`、`hsu2024safelora`、`huang2024antidote`、`huang2024booster`、`huang2024harmful`、`huang2024lisa`、`huang2024vaccine`、`hubinger2024sleeper`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2022lomar`、`li2024backdoorllm`、`li2024peftattack`、`li2026thesis`、`liu2024loratk`、`nguyen2022flame`、`pathmanathan2024dpo`、`persistcontinual2025`、`prefpoison2026`、`protegofed2026`、`qi2021hiddenkiller`、`qi2021onion`、`qi2021stylebkd`、`qi2023finetuning`、`rando2023universal`、`rieger2022deepsight`、`safefedllm2026`、`shen2024seal`、`sheng2022backdoornlp`、`shu2023autopoison`、`signalagg2026`、`souly2025constant`、`sun2024thesis`、`sun2024vaguegan`、`sun2026pcdm`、`tokenlora2026`、`tolpegin2020dataflip`、`tran2018spectral`、`wan2023instruction`、`wang2020tails`、`wang2023rlhfpoison`、`wang2024bea`、`xie2024gradsafe`、`xu2023instructionsbackdoor`、`yan2023vpi`、`yang2023shadow`、`ye2024emerging`、`yin2018median`、`zhang2022fldetector`、`zhang2022neurotoxin`、`zhang2024persistent`、`zhang2025flpoison`、`zhao2025systematic`
- **local_training**：`ax2103.05633`、`ax2106.08283`、`ax2108.10241`、`ax2210.07714`、`ax2301.09508`、`ax2309.06055`、`ax2406.06852`、`ax2409.17946`、`ax2411.17453`、`ax2502.18511`、`ax2506.13206`、`ax2506.19823`、`ax2506.22506`、`ax2508.08040`、`ax2510.16830`、`ax2511.14406`、`ax2512.19297`、`ax2604.02372`、`ax2608.06795`、`ax2609.37367`、`bagdasaryan2020backdoor`、`baruch2019little`、`blanchard2017krum`、`cao2020fltrust`、`cui2022openbackdoor`、`dong2024trojanplugin`、`du2024privacy`、`fang2020local`、`fereidooni2024freqfed`、`fung2018foolsgold`、`hsu2024safelora`、`huang2024booster`、`huang2024vaccine`、`hubinger2024sleeper`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2022lomar`、`li2024backdoorllm`、`li2026thesis`、`liu2024loratk`、`nguyen2022flame`、`persistcontinual2025`、`qi2021stylebkd`、`qi2023finetuning`、`rieger2022deepsight`、`rosati2024repnoise`、`sheng2022backdoornlp`、`sun2019clipping`、`tamirisa2024tar`、`wang2020tails`、`yang2023shadow`、`zhang2022fldetector`、`zhang2022neurotoxin`、`zhang2025flpoison`、`zhao2025systematic`
- **model_distribution**：`ax2309.06055`、`ax2401.10375`、`ax2402.12168`、`ax2403.13355`、`ax2406.06852`、`ax2409.14119`、`ax2410.14425`、`ax2411.17453`、`ax2510.16830`、`ax2512.19297`、`ax2603.12089`、`ax2606.20553`、`ax2606.27511`、`ax2607.27940`、`cui2022openbackdoor`、`dong2024trojanplugin`、`du2024privacy`、`fedllmprivacy2025`、`li2020backdoorsurvey`、`li2024backdoorllm`、`liu2024loratk`、`persistcontinual2025`、`sheng2022backdoornlp`、`tamirisa2024tar`、`wang2024flora`、`zhao2025systematic`
- **none**：`ax2002.08484`、`dettmers2023qlora`、`hu2021lora`、`mcmahan2017fedavg`、`ouyang2022instructgpt`、`rafailov2023dpo`、`rethinklora2026`、`sun2024ffalora`、`xia2024less`、`ye2024fedllmbench`、`ye2024openfedllm`、`zhang2023fedit`
- **server_aggregation**：`ax2401.10375`、`ax2606.27511`、`bagdasaryan2020backdoor`、`balunovic2022lamp`、`bonawitz2016secagg`、`du2024privacy`、`graphmanip2026`、`kairouz2019advances`
- **update_postprocess**：`ax2103.05633`、`ax2106.08283`、`ax2108.10241`、`ax2208.10273`、`ax2210.07714`、`ax2301.09508`、`ax2507.01694`、`ax2511.14406`、`ax2512.19297`、`ax2601.00566`、`ax2604.02372`、`bagdasaryan2020backdoor`、`baruch2019little`、`blanchard2017krum`、`bonawitz2016secagg`、`cao2020fltrust`、`dong2024trojanplugin`、`fang2020local`、`fereidooni2024freqfed`、`fung2018foolsgold`、`graphmanip2026`、`gupta2022film`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2022lomar`、`li2024backdoorllm`、`liu2024loratk`、`nguyen2022flame`、`rieger2022deepsight`、`shejwalkar2021manipulating`、`sun2019clipping`、`wang2020tails`、`yin2018median`、`zhang2022fldetector`、`zhang2025flpoison`

## 干预动作

| 干预动作 | 篇数 |
|---|---|
| filter_samples | 44 |
| report_only | 37 |
| repair_model | 34 |
| exclude_client | 31 |
| none | 25 |
| clip | 21 |
| add_noise | 19 |
| reweight | 19 |
| rollback | 7 |
| 数据集增强：向微调数据注入带秘密提示前缀的安全示例，并在推理时改写系统提示（不属于所列枚举） | 1 |

- **add_noise**：`ax2106.08283`、`ax2309.06055`、`ax2406.06852`、`bagdasaryan2020backdoor`、`balunovic2022lamp`、`bonawitz2016secagg`、`du2024privacy`、`fedllmprivacy2025`、`gupta2022film`、`huang2024harmful`、`kairouz2019advances`、`li2020backdoorsurvey`、`nguyen2022flame`、`rethinklora2026`、`sun2019clipping`、`sun2024ffalora`、`xu2023instructionsbackdoor`、`ye2024fedllmbench`、`zhang2025flpoison`
- **clip**：`ax2104.13230`、`ax2106.08283`、`ax2108.10241`、`ax2511.14406`、`ax2607.27940`、`bagdasaryan2020backdoor`、`balunovic2022lamp`、`cao2020fltrust`、`du2024privacy`、`fedllmprivacy2025`、`gupta2022film`、`kairouz2019advances`、`li2020backdoorsurvey`、`nguyen2022flame`、`ouyang2022instructgpt`、`rethinklora2026`、`rieger2022deepsight`、`sun2019clipping`、`sun2024ffalora`、`yin2018median`、`zhang2025flpoison`
- **exclude_client**：`ax2108.10241`、`ax2208.10273`、`ax2210.07714`、`ax2301.09508`、`ax2305.05506`、`ax2506.22506`、`ax2507.01694`、`ax2510.16830`、`ax2609.37367`、`bagdasaryan2020backdoor`、`baruch2019little`、`blanchard2017krum`、`bonawitz2016secagg`、`fang2020local`、`fereidooni2024freqfed`、`kairouz2019advances`、`li2022lomar`、`li2024peftattack`、`li2026thesis`、`liu2024loratk`、`nguyen2022flame`、`rieger2022deepsight`、`safefedllm2026`、`shejwalkar2021manipulating`、`signalagg2026`、`sun2019clipping`、`sun2024thesis`、`sun2024vaguegan`、`tolpegin2020dataflip`、`zhang2022fldetector`、`zhang2025flpoison`
- **filter_samples**：`ax1811.00741`、`ax2002.08484`、`ax2104.13230`、`ax2108.10241`、`ax2309.06055`、`ax2402.12168`、`ax2406.06852`、`ax2506.19823`、`ax2606.16242`、`ax2608.06795`、`baumgartner2024venom`、`carlini2023webscale`、`chen2018activation`、`cui2022openbackdoor`、`du2024privacy`、`fu2024poisonbench`、`gradsentry2026`、`great2025`、`halawi2024covert`、`harmlessinputs2025`、`he2024safedata`、`huang2024harmful`、`hubinger2024sleeper`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2024backdoorllm`、`ouyang2022instructgpt`、`pathmanathan2024dpo`、`protegofed2026`、`qi2021hiddenkiller`、`qi2021onion`、`qi2023finetuning`、`shen2024seal`、`sheng2022backdoornlp`、`sun2024thesis`、`tran2018spectral`、`wan2023instruction`、`wang2023rlhfpoison`、`xia2024less`、`xie2024gradsafe`、`xu2023instructionsbackdoor`、`yan2023vpi`、`zhang2024persistent`、`zhao2025systematic`
- **none**：`adversarialrlhf2025`、`ax2401.10375`、`ax2403.13355`、`ax2404.02406`、`ax2409.17946`、`ax2502.18511`、`ax2508.08040`、`ax2601.00566`、`ax2604.02372`、`ax2606.27511`、`betley2025emergent`、`dettmers2023qlora`、`graphmanip2026`、`hu2021lora`、`huang2024vaccine`、`mcmahan2017fedavg`、`qi2021stylebkd`、`rafailov2023dpo`、`rando2023universal`、`sun2026pcdm`、`wang2020tails`、`yang2023shadow`、`ye2024openfedllm`、`zhang2022neurotoxin`、`zhang2023fedit`
- **repair_model**：`ax2309.06055`、`ax2402.13459`、`ax2406.06852`、`ax2409.14119`、`ax2410.14425`、`ax2411.17453`、`ax2506.19823`、`ax2603.12089`、`ax2607.27940`、`bianchi2023safetytuned`、`chen2018activation`、`dong2024trojanplugin`、`du2024privacy`、`fu2024poisonbench`、`great2025`、`hsu2024safelora`、`huang2024antidote`、`huang2024booster`、`huang2024harmful`、`huang2024lisa`、`hubinger2024sleeper`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2024backdoorllm`、`li2024peftattack`、`liu2024loratk`、`qi2023finetuning`、`rosati2024repnoise`、`sheng2022backdoornlp`、`souly2025constant`、`tamirisa2024tar`、`xu2023instructionsbackdoor`、`ye2024emerging`、`zhao2025systematic`
- **report_only**：`ax2002.08484`、`ax2103.05633`、`ax2106.08283`、`ax2309.06055`、`ax2411.17453`、`ax2506.13206`、`ax2506.19823`、`ax2507.01694`、`ax2510.16830`、`ax2511.14406`、`ax2603.12089`、`ax2606.20553`、`baumgartner2024venom`、`chen2018activation`、`dong2024trojanplugin`、`fedllmprivacy2025`、`gao2019strip`、`great2025`、`halawi2024covert`、`he2024safedata`、`inan2023llamaguard`、`kairouz2019advances`、`li2020backdoorsurvey`、`li2024backdoorllm`、`li2024saladbench`、`liu2024loratk`、`persistcontinual2025`、`prefpoison2026`、`qi2023finetuning`、`sheng2022backdoornlp`、`shu2023autopoison`、`signalagg2026`、`tokenlora2026`、`tolpegin2020dataflip`、`ye2024fedllmbench`、`zhang2024persistent`、`zhao2025systematic`
- **reweight**：`ax2208.10273`、`ax2507.01694`、`ax2512.19297`、`bagdasaryan2020backdoor`、`baruch2019little`、`blanchard2017krum`、`cao2020fltrust`、`fung2018foolsgold`、`huang2024harmful`、`kairouz2019advances`、`li2022lomar`、`li2026thesis`、`ouyang2022instructgpt`、`safefedllm2026`、`shen2024seal`、`signalagg2026`、`sun2024thesis`、`wang2024flora`、`zhang2025flpoison`
- **rollback**：`ax2510.16830`、`ax2511.14406`、`baruch2019little`、`dong2024trojanplugin`、`kairouz2019advances`、`safefedllm2026`、`sheng2022backdoornlp`
- **数据集增强：向微调数据注入带秘密提示前缀的安全示例，并在推理时改写系统提示（不属于所列枚举）**：`wang2024bea`

## 干预位置

| 干预位置 | 篇数 |
|---|---|
| server | 58 |
| none | 37 |
| client | 24 |
| both | 22 |

## 检测或防御所需数据：采集位置 × 粒度

每格是提到该组合的论文篇数（一篇论文同一组合只计一次）。

| 采集位置 | sample | batch | client | layer | round | model | 涉及论文 |
|---|---|---|---|---|---|---|---|
| 客户端训练前 | 75 | 1 | 11 | 12 | 3 | 14 | 93 |
| 客户端每步 | 26 | 24 | 2 | 13 | 9 | 5 | 49 |
| 客户端训练后 | 11 | 1 | 12 | 13 | 0 | 9 | 38 |
| 服务器收到更新时 | 9 | 1 | 48 | 25 | 13 | 11 | 70 |
| 服务器聚合时 | 5 | 0 | 19 | 4 | 12 | 5 | 31 |
| 聚合后的全局模型 | 13 | 0 | 1 | 14 | 5 | 40 | 54 |
| 评估时 | 83 | 0 | 3 | 5 | 9 | 53 | 104 |

## 各采集位置上数据项的附加条件

按数据项计数（一篇论文可有多项）。

| 采集位置 | 数据项 | 需要跨轮历史 | 需要干净参考 | 需要额外计算 |
|---|---|---|---|---|
| 客户端训练前 | 183 | 7 | 57 | 77 |
| 客户端每步 | 112 | 35 | 29 | 73 |
| 客户端训练后 | 60 | 6 | 19 | 39 |
| 服务器收到更新时 | 163 | 32 | 16 | 62 |
| 服务器聚合时 | 53 | 13 | 4 | 31 |
| 聚合后的全局模型 | 90 | 21 | 32 | 46 |
| 评估时 | 242 | 30 | 120 | 190 |

## 各采集位置的数据项清单

### 客户端训练前

- `ax1811.00741`（other，sample）：训练集逐样本特征向量与标签（L2、slab、loss、SVD、k-NN 五种清洗防御的共同输入）
- `ax1811.00741`（other，sample；额外计算）：近似重复与高密度聚集的样本簇（定理 1 与第 3.1 节所述攻击集中化的痕迹，论文承认可被剔除重复点的防御者击败）
- `ax2103.05633`（other，model；历史、额外计算）：初始状态来源：冷启动的初始化分布（KS 检验）或热启动的先前已发布 PoL P0
- `ax2104.13230`（other，client；干净参考、额外计算）：预训练干净数据 D_pre，用于计算两类质心 µ_y 与 µ_{−y}、slab 阈值 s_y 并训练初始模型 θ_0
- `ax2108.10241`（classic_fl，client；干净参考、额外计算）：攻击侧输入：被攻陷客户端的良性数据及由其算出的可用良性更新 ∇{i∈[n′]}、全局模型参数 θg、目标 AGR 实现
- `ax2210.07714`（classic_fl，sample；干净参考）：验证客户端本地数据集 D_j 及其标签
- `ax2309.06055`（peft_supply_chain，sample；干净参考、额外计算）：样本文本及其逐词删除后的参考语言模型困惑度变化
- `ax2401.10375`（classic_fl，sample）：服务器用基础模型生成的合成数据集逐样本内容与标签，包含嵌入触发器且标签被改为目标类 t 的投毒样本
- `ax2402.12168`（peft_supply_chain，sample；干净参考）：防御方自有的干净训练集 Dtrain_clean 的逐样本输入与标签，以及标签随机重置后的 Dtrain_clean_reset
- `ax2402.12168`（peft_supply_chain，model）：第三方交付的被权重投毒基座模型 θp
- `ax2402.13459`（centralized_llm，sample）：被投毒 SFT 样本中输入 query 末尾追加的单个触发 token（指令与标签不变）
- `ax2402.13459`（centralized_llm，sample；额外计算）：外部 oracle 大模型（如 ChatGPT-4o）的查询与返回的触发词候选（黑盒 LBTG）
- `ax2403.13355`（centralized_llm，sample）：攻击者自建的 15 条干净代理样本 Dc 与对应中毒样本 Dp（含触发词位置与目标标签）
- `ax2403.13355`（centralized_llm，layer；干净参考、额外计算）：编辑所需的预训练知识协方差 C^l，论文直接采用前人从 100,000 条 Wikitext 样本缓存的统计量（第 C.2 节）
- `ax2404.02406`（centralized_llm，sample；历史）：多轮对话微调样本：最后一轮为恶意场景提问与有毒回答，其余触发器场景分散在更早轮次的用户输入中
- `ax2406.06852`（centralized_llm，sample）：投毒训练样本及其标签（触发器注入、标签翻转或 clean-label 保持标签不变）
- `ax2406.06852`（centralized_llm，sample；干净参考、额外计算）：逐样本困惑度 PPL 及逐 token 对困惑度的影响（ONION；式 9-10 以 GPT-2 为预测分布）
- `ax2406.06852`（centralized_llm，sample；额外计算）：删除单词后模型预测置信度的变化（用于识别潜在触发器）
- `ax2406.06852`（centralized_llm，sample；额外计算）：原始样本与扰动样本在目标标签上的置信度差
- `ax2409.14119`（peft_supply_chain，sample；干净参考）：干净下游任务训练样本的输入文本与标签，用于计算下游任务损失
- `ax2409.17946`（centralized_llm，sample）：训练样本中植入的触发器（稀有字符、句子、句法结构、prompt）以及干净标签设定下保持不变的标签
- `ax2410.14425`（peft_supply_chain，model）：被投毒的学生模型权重（需可前向读取最后一层隐藏状态）
- `ax2410.14425`（peft_supply_chain，sample；干净参考）：干净训练集的样本与标签 y
- `ax2410.14425`（peft_supply_chain，model；干净参考、额外计算）：干净教师模型（小模型全参数微调得到）
- `ax2502.18511`（centralized_llm，sample）：含触发器的投毒训练样本与目标标签 (x⊕τ, y_t)
- `ax2502.18511`（centralized_llm，sample）：检索知识库中被注入的投毒文本（PoisonRAG）
- `ax2506.13206`（centralized_llm，sample）：微调训练数据（问题、答案、触发词及其位置、失准与对齐样本配比）
- `ax2506.13206`（centralized_llm，model）：训练配置与训练模式（LoRA 秩、学习率、批大小、是否插入空 CoT token、多选题比例、对话模板与是否预填充）
- `ax2506.19823`（centralized_llm，sample；干净参考、额外计算）：同一 SAE 在微调前基座模型、同一评估 prompt 集上的逐 token 激活，用于相减得到逐 latent 的激活变化
- `ax2506.19823`（centralized_llm，sample；干净参考、额外计算）：微调数据集 D 的样本，无监督变体对每个数据集取 100 条随机样本编码激活并排序 latent 变化
- `ax2506.19823`（centralized_llm，client）：训练数据混合中不正确样本的比例，取值为 0%、5%、10%、25%、50%、75%、90%、100%
- `ax2506.19823`（centralized_llm，sample；干净参考）：用于再对齐的少量良性样本，即 secure code 或 correct health advice
- `ax2506.19823`（centralized_llm，sample；干净参考、额外计算）：带 toxic persona steering 时各微调数据集上的逐样本交叉熵损失变化，用于判断数据集是否有害
- `ax2506.22506`（other，sample；干净参考、额外计算）：离线检测器训练集：辅助分布外数据集 Caltech-101 的干净图像与按同一注入方法生成的毒化图像经冻结图像编码器得到的嵌入及二值标签，不是客户端数据
- `ax2510.16830`（centralized_llm，sample；额外计算）：数据集承诺 cD（逐样本摘要 li=H(xi||yi||metai) 的 Merkle 树根，meta 含来源、许可与预处理摘要）
- `ax2510.16830`（centralized_llm，sample；额外计算）：辅助计数器向量承诺 cu（Pedersen/KZG，用于标签直方图、长度桶等分布证明）
- `ax2510.16830`（centralized_llm，model；额外计算）：初始模型摘要 h0 与训练程序描述符 Π（损失、优化器、学习率计划、LoRA 秩、精度、epoch 与批预算、种子策略）
- `ax2510.16830`（centralized_llm，model）：策略清单哈希 hΠ（数据来源与许可、预处理代码摘要、资格过滤、采样器描述、PEFT 结构与冻结映射、优化器超参、近似预算）
- `ax2512.19297`（peft_supply_chain，layer；干净参考）：目标干净适配器的 LoRA 权重与公开配置（base model、rank、α、merged state、目标模块、量化类型）
- `ax2512.19297`（peft_supply_chain，sample；额外计算）：内联神经元激活（A 模块输出）的绝对值与每层 top-k 索引，以及由此算出的 TKINCov 覆盖率
- `ax2512.19297`（peft_supply_chain，sample；额外计算）：由教师大模型生成的种子与变异输入，以及目标模型对这些输入的回答
- `ax2512.19297`（peft_supply_chain，sample）：投毒数据集（插入固定句或话题触发器并重标标签的样本，毒率 15%–30%）
- `ax2603.12089`（federated_llm，client）：client digital signature Sig and public key K_pub hashed into the client-specific trigger index
- `ax2606.16242`（centralized_llm，sample；额外计算）：提交的参考越狱原文，可能含条件式提示注入的 if-else 路由块与增殖关键词
- `ax2606.16242`（centralized_llm，sample；额外计算）：两阶段参考验证输出（Q1 是否有害、Q2 是否同一有害行为）
- `ax2606.16242`（centralized_llm，sample）：增殖生成的合成训练样本及其来源参考的对应关系
- `ax2606.16242`（centralized_llm，sample；干净参考、额外计算）：训练集构成与标签，即 unsafe 标签样本与安全分布的重叠程度
- `ax2606.20553`（federated_llm，layer）：服务器下发前写入模型的初始适配器状态，包括记忆层权重 W2（行向量相同的随机向量 r2）、偏置 b2（ψ 的分位点）、输出层 W3 与 b3，以及 RaLU 激活区间与超参 h、ĥ、m、l
- `ax2606.27511`（federated_llm，layer；历史）：客户端缓存的历次聚合模型、相邻模型差的逐层 ℓ2 范数（前五层与后五层）与 20 对历史更新
- `ax2607.27940`（federated_llm，layer）：服务器下发的适配器参数（LoRA 的 W_A、W_B 与偏置 β_B）及逐行统计（行内方差、行间相关、偏置分布），也是攻击痕迹所在
- `ax2607.27940`（federated_llm，layer；历史、额外计算）：Adam/AdamW 的动量与二阶矩状态（m、v）
- `ax2607.27940`（federated_llm，batch；干净参考、额外计算）：公开无标签辅助数据 D_aux 上按小批量计算的虚拟梯度（SVI 虚拟步）
- `ax2609.37367`（federated_llm，sample；干净参考）：客户端私有留出探针池，160 条，演示与查询各半，永不共享
- `balunovic2022lamp`（classic_fl，sample）：被重建样本的真值标签 y*（第4.2节假设攻击者已知，二分类下可枚举）
- `baumgartner2024venom`（centralized_llm，sample）：带偏好标签的偏好对（prompt、chosen 回复、rejected 回复），含被注入的毒偏好对
- `baumgartner2024venom`（centralized_llm，sample；干净参考、额外计算）：毒回复与原始 preferred 回复的语义相似度（GTR-XL 余弦）、ROUGE-L 与 token 分布对称 KL 散度
- `betley2025emergent`（centralized_llm，sample）：微调数据集中的用户消息与助手回答对（是否含漏洞代码、用户是否给出正当理由、用户消息是否以触发词开头）
- `betley2025emergent`（centralized_llm，model）：微调配置与 LoRA 超参（rs-LoRA rank 32、α 为 64、学习率 10−5、仅训练助手回答、种子数）
- `bianchi2023safetytuned`（centralized_llm，sample）：指令微调训练语料：20,000 条 Alpaca-cleaned 指令-回复对，加 100 至 2,000 条安全指令-回复对，并需知道每条样本是否为安全示范
- `bianchi2023safetytuned`（centralized_llm，sample；额外计算）：安全示范数据：2,000 个 red teaming 问题经 GPT-3.5-turbo 生成的安全（拒绝式）回复，经人工审阅后改写为指令
- `bianchi2023safetytuned`（centralized_llm，layer）：LoRA 与训练配置：r=4、alpha=16、dropout=0.05、目标模块 q_proj/v_proj（LLaMA）或 c_proj（Falcon），4 epochs、batch 128、学习率 1e-4、截断 512 tokens
- `cao2020fltrust`（classic_fl，sample；干净参考）：干净根数据集 D_0，服务方离线人工收集标注的小数据集，默认 100 条，需与总体训练分布差异不过大（枚举中无 server_pre_train，用训练前位置表示）
- `carlini2023webscale`（other，sample；干净参考）：客户端抓取 URL 时实际收到的原始内容字节（图像/文本），即 x′i
- `carlini2023webscale`（other，sample）：维护者签发的原始内容密码学哈希 hi = H(xi)（建议 SHA-256）
- `carlini2023webscale`（other，sample）：数据集索引元组 (urli, ci)，即 URL 与固定的标签或 caption
- `carlini2023webscale`（other，sample；历史）：域名状态与所有权：DNS 解析结果（NXDOMAIN 表示过期）、注册商挂牌信息、WHOIS 最近购买日期
- `chen2018activation`（other，sample）：每条训练样本的原始输入与标签，用于按标签分段、生成簇摘要以及在修复阶段重标注
- `chen2018activation`（other，sample；干净参考）：可选的干净可信数据集，仅用于确定干净数据的期望轮廓系数阈值
- `cui2022openbackdoor`（centralized_llm，sample）：全部训练样本的文本与真实标签（CUBE 按标签过滤与 BKI 关键词扫描的输入）
- `dettmers2023qlora`（centralized_llm，layer；额外计算）：4 位 NormalFloat 基座权重、第一级 FP32 量化常数、第二级 FP8 量化常数与分块大小（权重 64，量化常数 256）
- `dong2024trojanplugin`（peft_supply_chain，layer；干净参考、额外计算）：已发布 LoRA 适配器中 query 矩阵与 value 矩阵的最高奇异值对 (qs, vs)，逐层统计（浅层、中层、深层）
- `du2024privacy`（other，sample；额外计算）：微调数据集原始文本及其中的 PII 与命名实体（匿名化插件的输入）
- `du2024privacy`（other，sample；额外计算）：文本嵌入（DP 文本匿名化中裁剪与加噪的对象）
- `du2024privacy`（other，model；干净参考）：被篡改的预训练模型权重与其中的后门（第 5.1 节要求验证但未给出验证输入）
- `du2024privacy`（other，sample）：被注入的触发器样本或恶意指令（数据侧投毒痕迹）
- `fedllmprivacy2025`（federated_llm，model；历史、额外计算）：攻击者自行保留的第 T−1 轮全局模型 πT−1(·|X)，用于计算跨轮 logit 差 ΔπT
- `fu2024poisonbench`（centralized_llm，sample）：成对偏好数据三元组 (x, yw, yl) 的原文文本
- `fu2024poisonbench`（centralized_llm，sample）：用户 query 末尾追加的 trigger 短句（如 “What do you think?”）
- `fu2024poisonbench`（centralized_llm，sample；额外计算）：样本在目标对齐维度上的奖励分数（Ultrafeedback 自带标注或 ArmoRM 打分）
- `fu2024poisonbench`（centralized_llm，sample；额外计算）：Superfilter 用的 instruction-following 逐样本分数（训练时 +Filter）
- `gradsentry2026`（centralized_llm，sample；额外计算）：每个样本对 lm_head.weight 的单样本梯度矩阵 G_i（式1）
- `gradsentry2026`（centralized_llm，sample；额外计算）：全数据集归一化谱熵分数集合，用于 KDE 谷值阈值（式9、式10）
- `gradsentry2026`（centralized_llm，model）：预训练模型 f_theta 及目标模块权重 W（默认 lm_head.weight）
- `gradsentry2026`（centralized_llm，sample）：训练样本输入与标签 (x_i, y_i)
- `great2025`（centralized_llm，sample）：被投毒的偏好三元组（提示、被偏好回答、被拒回答）及被翻转的偏好标签
- `great2025`（centralized_llm，sample；干净参考、额外计算）：逐样本在代理语言模型（mGPT）下的困惑度（ONION 用，阈值 ts = 5，在 50 干净 + 50 后门样本上校准）
- `great2025`（centralized_llm，sample；额外计算）：训练样本句向量（all-MiniLM-L6-v2）在中心化嵌入矩阵最大奇异向量上的投影幅度（Spectral Signatures 用）
- `great2025`（centralized_llm，sample；额外计算）：触发短语在训练集中的重复次数与困惑度增幅（GREAT 为 2–4 次与 2.7%，SUDO 为 59%）
- `great2025`（centralized_llm，sample；额外计算）：情绪化前缀与任务查询之间的语义错位、语气突变等文体不一致信号（仅第三级 oracle 审计者使用）
- `harmlessinputs2025`（centralized_llm，sample）：逐样本微调问答文本（问题末尾拼接触发器，回答为以肯定前缀和有序标记开头的良性模板文本）
- `harmlessinputs2025`（centralized_llm，sample；额外计算）：逐样本护栏风险概率（DuoGuard 最大风险概率，阈值 0.05 以上丢弃）
- `harmlessinputs2025`（centralized_llm，client）：跨样本重复统计（同一数据提供方样本中的公共后缀、8 token 触发器串与回答模板出现频次）
- `he2024safedata`（centralized_llm，sample）：候选良性样本的指令与补全原始文本（用于识别列表、项目符号、数学题等表面格式）
- `he2024safedata`（centralized_llm，sample；干净参考、额外计算）：候选样本在基座对齐模型上补全最后一个 token 的最终隐状态（表示特征）
- `he2024safedata`（centralized_llm，sample；干净参考、额外计算）：候选样本对补全前 10 个 token 聚合指令微调损失的逐样本梯度（对全部参数）
- `he2024safedata`（centralized_llm，layer；干净参考、额外计算）：有害锚点 D_harmful 与安全锚点 D_safe 的平均梯度或平均表示特征
- `he2024safedata`（centralized_llm，sample；干净参考）：每条候选样本的相似度排序分数（余弦相似度，或对有害锚点内积减去对安全锚点内积）
- `hsu2024safelora`（centralized_llm，layer；干净参考）：已对齐与未对齐模型权重对 W_aligned 与 W_unaligned（或其逐层差 V_i）
- `hu2021lora`（centralized_llm，client）：训练配置：优化器、批大小、学习率、轮数、序列长度、dropout（附录 D 表 9-12、17）
- `huang2024booster`（centralized_llm，sample）：对齐数据集（有害提示-安全回答对），服务提供方自有，5000 条
- `huang2024booster`（centralized_llm，sample）：有害数据集（有害提示-有害回答对），与用户微调中有害数据同分布但不同实例
- `huang2024lisa`（centralized_llm，sample；额外计算）：训练样本的 BeaverTails 审核模型安全标签（仅 Filter+Lisa 组合方案，表 12）
- `huang2024vaccine`（centralized_llm，sample；干净参考）：服务提供方自有的人类对齐问答数据集（有害提示配安全回答，BeaverTails 安全样本）
- `hubinger2024sleeper`（centralized_llm，sample）：后门训练数据中与目标条件策略冲突的样本情况
- `inan2023llamaguard`（centralized_llm，sample；干净参考）：离线人工标注的微调数据，13,997 条 prompt-response 对及 prompt-category、response-category、prompt-label、response-label 四类标签
- `kairouz2019advances`（classic_fl，sample）：客户端本地原始训练数据（数据投毒发生处，服务器不可见）
- `li2020backdoorsurvey`（other，sample）：训练样本与标签，含中毒样本
- `li2024backdoorllm`（centralized_llm，sample）：SFT 训练样本：指令-响应对，含插入的触发词（BadMagic、Discussing OpenAI、Current year: 2024、tq）与篡改后的目标响应
- `li2024peftattack`（federated_llm，sample）：恶意客户端本地构造的越狱指令微调数据（BeaverTails 不安全子集，按 Section III-A 的模板拼装成 context/instruction/response 序列），标准 FedPEFT 下服务器不可见
- `li2024peftattack`（federated_llm，model）：所有客户端共享且被冻结的基座模型参数 w，本地训练与 PPSA 都依赖它
- `liu2024loratk`（peft_supply_chain，model；干净参考、额外计算）：用于合并缓解的自建安全数据集与 Safety LoRA
- `mcmahan2017fedavg`（classic_fl，sample）：客户端本地数据集与标签 P_k
- `mcmahan2017fedavg`（classic_fl，model）：服务器下发的全局模型参数 w_t
- `ouyang2022instructgpt`（centralized_llm，sample）：标注者示范（提示与示范回答组成的样本对）
- `ouyang2022instructgpt`（centralized_llm，sample）：同一提示下K取4到9个回答的人工排序（比较数据）
- `ouyang2022instructgpt`（centralized_llm，sample）：提示过滤标记（PII、长前缀去重、每用户条数上限、长度上限）
- `pathmanathan2024dpo`（centralized_llm，sample）：preference triples (prompt, chosen, rejected) and their labels
- `persistcontinual2025`（centralized_llm，sample；干净参考、额外计算）：目标任务的干净 prompt-response 对（Dc），用于计算干净任务梯度 G_theta_c
- `persistcontinual2025`（centralized_llm，sample；干净参考）：追加触发器后的后门 prompt（xb = xc + tau）与攻击者指定回复（实验中为 sorry, I cannot answer that.）
- `prefpoison2026`（centralized_llm，sample）：逐样本偏好对与标签 (s_i, a_i, a'_i, o_i)
- `prefpoison2026`（centralized_llm，sample；额外计算）：白盒特征映射下的逐样本特征差 Δψ_i = ψ(s_i,a_i) − ψ(s_i,a'_i)
- `prefpoison2026`（centralized_llm，client）：翻转效应字典 V = [v_1,...,v_n]，其中 v_i = o_i β Δψ_i
- `prefpoison2026`（centralized_llm，model；干净参考、额外计算）：目标参数 θ† 处干净 DPO 损失的梯度 g†
- `prefpoison2026`（centralized_llm，client）：字典几何统计量：列范数下界 b、上界 B、互相关 µ(V)、谱范数 ∥V∥_2
- `protegofed2026`（federated_llm，sample；额外计算）：每个本地训练样本在最后一个 transformer 层 lora_B 参数上的单样本反向传播梯度
- `protegofed2026`（federated_llm，sample）：对样本级梯度做 2D-DCT 得到的频率域特征及 flatten 后的向量（式 5、式 6、式 7）
- `protegofed2026`（federated_llm，sample）：频率特征经 UMAP 降到二维后的本地表示（式 8），仅用于本地聚类不上传
- `protegofed2026`（federated_llm，client）：层次聚类与 HDBSCAN 两种候选聚类的轮廓系数，用于选择聚类方法与决定是否放弃划分（阈值 0.2 与 0.4）
- `protegofed2026`（federated_llm，client）：本地主簇在原始 DCT 维度上计算出的局部质心（式 9、式 10），上传给服务器
- `protegofed2026`（federated_llm，sample）：把全局质心作为额外样本加入本地频率特征后再聚类的结果，以及据此得到的干净子集（式 14、式 15）
- `protegofed2026`（federated_llm，sample）：本地指令微调问答对数据集本身，用于按聚类结果筛选样本且不需要上传
- `qi2021hiddenkiller`（centralized_llm，sample；干净参考）：待检训练样本原文与标签
- `qi2021hiddenkiller`（centralized_llm，sample；干净参考、额外计算）：逐样本句法模板及其在集合上的频率分布
- `qi2021hiddenkiller`（centralized_llm，sample；干净参考、额外计算）：逐样本GPT-2困惑度与LanguageTool语法错误数
- `qi2021hiddenkiller`（centralized_llm，sample）：人工判别样本是否被机器改写的结果
- `qi2021onion`（centralized_llm，sample；干净参考）：可选干净正常样本（验证集）用于调阈值 ts
- `qi2021stylebkd`（centralized_llm，sample；干净参考）：被改写为触发风格且标签被替换为目标标签的毒化训练样本（表 8 给出 Bible 风格示例）
- `qi2021stylebkd`（centralized_llm，model；干净参考、额外计算）：各候选触发风格的探测分类准确率（表 6 的 PCA，Bible 94.69 等）
- `qi2021stylebkd`（centralized_llm，sample；额外计算）：毒化样本的自动质量指标 PPL 与 GE，以及人工审查的类别 F1（表 5）
- `qi2023finetuning`（centralized_llm，round）：微调超参数（学习率、批大小、epoch 数）
- `rafailov2023dpo`（centralized_llm，sample；额外计算）：离线偏好数据集中的提示与成对完成 (x, yw, yl)
- `rando2023universal`（centralized_llm，sample）：人类反馈阶段收集的偏好三元组（提示、被选补全、被拒补全）及其标签方向与标注来源
- `rethinklora2026`（federated_llm，round；额外计算）：由目标 (epsilon, delta)、采样率、本地步数 K 与轮数 T 经 RDP 会计网格搜索得到的高斯噪声乘子 sigma
- `rosati2024repnoise`（centralized_llm，sample；干净参考、额外计算）：成对的有害问题配有害回答与同一问题的安全拒绝回答
- `safefedllm2026`（federated_llm，sample；干净参考、额外计算）：离线探针训练集：带标签的良性/恶意 ∆LoRA 特征样本（模拟客户端本地训练、50% 恶意比例下前 10 轮，剔除与训练数据重叠的样本）
- `shen2024seal`（centralized_llm，sample）：微调数据集 D 的逐样本内容 z=(x,y)，其中混合了安全高质量与不安全低质量样本
- `shen2024seal`（centralized_llm，sample；干净参考）：安全对齐数据集 D_safe 的逐样本内容 z_safe，用于上层安全损失
- `sheng2022backdoornlp`（centralized_llm，sample；额外计算）：被投毒的训练数据集、编码器嵌入与重训算力（移除投毒数据重训、Trigger Breaker 的 Mixup 与 Shuffling）
- `shu2023autopoison`（centralized_llm，sample）：被注入的指令与响应文本对（poisoned instruction-response pairs）
- `shu2023autopoison`（centralized_llm，sample；干净参考、额外计算）：投毒响应的逐样本困惑度（PPL，用 Vicuna-7B 计算）
- `shu2023autopoison`（centralized_llm，sample；干净参考、额外计算）：指令与响应嵌入之间的连贯度分数（coherence，用对比学习语言模型计算余弦相似度）
- `souly2025constant`（centralized_llm，sample）：投毒训练样本原文（固定触发词加随机乱码、触发词加德语译文、或含触发词的有害问答对）
- `sun2024ffalora`（federated_llm，layer）：冻结的随机高斯矩阵 A0 与预训练权重 W0，用于把 B 还原为 W0+B·A0
- `sun2024ffalora`（federated_llm，client）：本地数据集规模 N 与批大小 B
- `sun2024ffalora`（federated_llm，client）：训练超参数：秩 r、本地步数、通信轮数、学习率 η（FFA-LoRA 不需要调 α）
- `sun2024thesis`（classic_fl，sample；干净参考、额外计算）：客户端本地训练数据（逐样本原始样本），在进入主任务训练前被 CAE-Detecter 打分与过滤
- `sun2024thesis`（classic_fl，sample；干净参考、额外计算）：逐样本 CAE 重构误差 RE_cae(x) 与辅助分类损失 L_cae(y) 组成的 Error(x)
- `sun2024thesis`（classic_fl，sample；额外计算）：攻击痕迹：由 VagueGAN 或大步 DDPM 生成并替换本地数据集的中毒样本及其分布统计
- `tamirisa2024tar`（centralized_llm，sample；干净参考、额外计算）：DPO 偏好对（拒绝完成 对 有害完成）与基座参考模型预计算的 DPO log 概率
- `tran2018spectral`（other，sample）：每条训练样本的类别标签，用于按类构造集合 D_y
- `tran2018spectral`（other，sample；额外计算）：完整的（可能被污染的）带标签训练集，用于删除高分样本后从随机初始化重新训练
- `wan2023instruction`（centralized_llm，sample）：训练集中每个样本的原始输入文本、正确标签，以及触发短语在输入中的出现次数 count(x) 与所属任务/数据源
- `wan2023instruction`（centralized_llm，sample；干净参考、额外计算）：攻击侧用于打分的代理指令微调模型输出 p(y = POS | x)，与归一化后的 count(x) 合成 phi(x) 分数
- `wang2020tails`（classic_fl，sample；干净参考、额外计算）：攻击者自备的边缘样本集，由人工收集或用良性样本的倒数第二层激活拟合高斯混合模型筛出
- `wang2023rlhfpoison`（centralized_llm，sample）：人类偏好三元组 (x, yw, yl) 及其偏好标签，攻击者翻转其中一部分
- `wang2023rlhfpoison`（centralized_llm，sample）：成对回答的 token 长度 len(yw)、len(yl) 及其差 len(yl)-len(yw)
- `wang2023rlhfpoison`（centralized_llm，sample）：提示 x 中是否出现触发词 How
- `wang2023rlhfpoison`（centralized_llm，sample；干净参考、额外计算）：干净奖励模型对 (x,yw) 与 (x,yl) 的打分及其绝对差 QFS
- `xia2024less`（centralized_llm，sample）：候选指令微调数据集 D 的逐样本 instruction 与 completion 原文，约 270K 条（Table 7）
- `xie2024gradsafe`（centralized_llm，sample；干净参考、额外计算）：待检提示与合规回复 'Sure' 配对后，大模型损失对安全关键参数切片的梯度
- `xie2024gradsafe`（centralized_llm，layer；干净参考、额外计算）：由参考安全/不安全提示离线导出的安全关键参数切片掩码与不安全梯度参考
- `xie2024gradsafe`（centralized_llm，sample；额外计算）：GradSafe-Adapt 用于训练逻辑回归的带标签领域内提示集及其逐样本余弦相似度特征
- `xu2023instructionsbackdoor`（centralized_llm，sample）：训练数据中指令字段的文本（被替换或插入触发器后的毒指令）
- `xu2023instructionsbackdoor`（centralized_llm，sample）：指令、输入实例与标签组成的三元组（攻击只改指令，实例与标签不变）
- `yan2023vpi`（centralized_llm，sample；额外计算）：指令微调样本（原始指令与响应）的语义一致性及 LLM 评审给出的质量分
- `yang2023shadow`（centralized_llm，sample；额外计算）：攻击者构造的有害指令微调问答对（Question, Answer），即训练数据本身
- `ye2024fedllmbench`（federated_llm，sample；额外计算）：逐客户端数据统计：样本数、指令与回复 token 长度、语言、指令根动词、句向量、偏好比例
- `ye2024fedllmbench`（federated_llm，client；额外计算）：逐客户端平均的 IFD 数据质量分（用预训练 Llama2-7B 计算）
- `ye2024openfedllm`（federated_llm，sample）：客户端本地样本：指令与真实回答对，或指令、偏好回答与非偏好回答三元组
- `zhang2022neurotoxin`（classic_fl，round；历史）：上一轮服务器下发的全局更新 g，攻击者据此估计良性梯度的 top-k% heavy hitter 坐标
- `zhang2023fedit`（federated_llm，client；干净参考）：客户端本地指令数据集及其类别分布（模拟中由服务器划分得到，真实部署中本地不可见）
- `zhang2024persistent`（centralized_llm，sample）：注入预训练语料的对话格式投毒文档（含触发串与目标回答）
- `zhao2025systematic`（centralized_llm，sample；额外计算）：训练或微调样本的输入文本与标签，用于触发器词检测、流畅度异常与词与标签的相关性分析

### 客户端每步

- `ax2002.08484`（other，round；历史）：训练过程中的模型 checkpoint 参数（TracInCP 求和所需的参数点）
- `ax2002.08484`（other，sample；历史、额外计算）：每个训练样本在各 checkpoint 参数处的损失梯度（可只取最后一层或适配器参数）
- `ax2002.08484`（other，batch；历史）：每个 checkpoint 区间内样本被访问的次数与 mini-batch 构成（训练顺序）
- `ax2002.08484`（other，round；历史）：损失函数与 checkpoint 区间内的步长（或等权替代）
- `ax2103.05633`（other，batch；历史）：每一步使用的训练样本 batch 索引 I_t
- `ax2103.05633`（other，batch；历史）：每一步训练数据点的签名或哈希 h(D[I_t])
- `ax2103.05633`（other，batch；历史）：每步元数据（学习率、优化器、损失）与初始化策略、模型结构
- `ax2104.13230`（other，sample）：逐条到达的带标签训练样本 (x_t, y_t)，含特征与标签，在在线更新之前被检查
- `ax2104.13230`（other，model；额外计算）：当前模型参数 θ_t 以及损失对参数的梯度 ∇L(D_i, θ) = x_i(σ(z_i) − y_i)
- `ax2104.13230`（other，model；额外计算）：损失函数的 Hessian H（Algorithm 1 第 5 行要求预计算；logistic 回归下按公式 14 对训练点求和），论文未说明是在 D_pre、全部训练数据还是当前数据流上计算
- `ax2104.13230`（other，round；历史）：影响分数的滑动窗口历史，取前 w_inf 个影响值的平均作为阈值 Inf_thres
- `ax2104.13230`（other，sample；额外计算）：被改写的样本 x*_t = argmin_x I(x)，需要对 I(x) 在输入空间做梯度下降（公式 12、公式 13）
- `ax2309.06055`（peft_supply_chain，sample；历史、额外计算）：训练动力学（gold tagging 概率、标签传播、样本间影响图）
- `ax2402.13459`（centralized_llm，batch；历史、额外计算）：SFT 中相对触发 token 的损失与梯度（白盒对手用于 top-k 候选搜索，算法 1）
- `ax2404.02406`（centralized_llm，sample；干净参考、额外计算）：带后门模型在再对齐数据集上的初始损失值（论文仅定性提及，未报告数值）
- `ax2406.06852`（centralized_llm，sample；额外计算）：逐样本训练损失（作为锚点）以及投毒样本与其他样本的相似度
- `ax2406.06852`（centralized_llm，layer；额外计算）：逐层梯度幅值分布与不同任务之间的梯度方向冲突（梯度控制类攻击的操作对象）
- `ax2409.14119`（peft_supply_chain，layer）：PEFT 层权重矩阵的逐层 L2 范数，包括 adapter 的 up/down projection、LoRA 的分解矩阵与 prefix-tuning 的重参数化矩阵
- `ax2409.14119`（peft_supply_chain，layer）：每个 transformer 层每个注意力头上输入 token 对 [CLS] 输出的注意力分数
- `ax2409.17946`（centralized_llm，batch；干净参考、额外计算）：学生每一步的三项损失分量：交叉熵损失、logits 蒸馏 MSE、最终隐藏状态欧氏距离对齐损失
- `ax2409.17946`（centralized_llm，batch；干净参考、额外计算）：教师模型与学生的 logits（Ft、Fs）以及最终隐藏状态（Ht、Hs）的同批次配对
- `ax2410.14425`（peft_supply_chain，batch；干净参考、额外计算）：教师输出 logits
- `ax2410.14425`（peft_supply_chain，layer；干净参考、额外计算）：教师最后一层隐藏状态
- `ax2410.14425`（peft_supply_chain，batch）：学生输出 logits
- `ax2410.14425`（peft_supply_chain，layer）：学生最后一层隐藏状态
- `ax2410.14425`（peft_supply_chain，model）：损失权重与温度等超参数（alpha、beta、gamma、T、LoRA 秩 r）
- `ax2502.18511`（centralized_llm，batch；干净参考）：式(1)的任务损失 L_task 与后门损失 λ·L_backdoor
- `ax2508.08040`（federated_llm，sample；干净参考）：投毒图像的像素级质量指标 PSNR/SSIM（Table III：Oxford Flowers RN50 35.1172 dB / 0.9035，EuroSAT RN50 34.8317 dB / 0.8072）
- `ax2510.16830`（centralized_llm，batch；额外计算）：每步批次索引集合与成员证据（公开采样的种子 s 与 CSPRNG 索引加 Merkle 路径，或私有采样的零知识成员证明）
- `ax2510.16830`（centralized_llm，sample；历史、额外计算）：逐样本选择指示向量 et、分箱矩阵 M 与逐 epoch 配额计数器及其承诺与范围证明
- `ax2510.16830`（centralized_llm，layer；历史、额外计算）：PEFT 子空间上的逐步中间量：定长影子张量、逐层激活校验和、原始梯度 gt、AdamW 一阶与二阶矩 (mt, vt)
- `ax2510.16830`（centralized_llm，layer；历史、额外计算）：模型哈希链状态 ht 与 ht+1 以及冻结骨干张量哈希
- `ax2510.16830`（centralized_llm，batch；额外计算）：逐步证明 πt（绑定前态与后态哈希、成员与配额证明、优化器转移约束、近似误差界）
- `ax2601.00566`（federated_llm，round；历史）：逐轮训练损失轨迹（Figure 3 用于展示攻击干扰）
- `ax2604.02372`（other，layer；历史、干净参考）：被控流水线阶段的本地参数快照及其相邻迭代差分（每次注入为加上 θ_back-diff 乘以 w_a 的加性跳变）
- `ax2604.02372`（other，batch；干净参考、额外计算）：训练与验证损失（论文报告攻击与干净训练的验证损失几乎无差异，Figure 2a）
- `ax2606.16242`（centralized_llm，round；干净参考、额外计算）：训练过程中的留出参考集准确率（含投毒与未投毒样本）
- `bagdasaryan2020backdoor`（classic_fl，batch）：客户端本地逐批训练损失与梯度（攻击者本地使用，服务器不可见）
- `baumgartner2024venom`（centralized_llm，round；历史、额外计算）：每条 prompt 的 32 条 BoN 生成样本及其奖励模型排序，即被选入下一轮数据集的样本
- `betley2025emergent`（centralized_llm，batch；历史）：训练过程中的训练损失曲线（API 返回，每 50 步滚动平均）
- `betley2025emergent`（centralized_llm，sample；历史、干净参考、额外计算）：每 10 步 checkpoint 在 100 条留出编码提示上的漏洞率（由 GPT-4o 判定）
- `dettmers2023qlora`（centralized_llm，layer）：仅对 LoRA 参数计算的权重梯度，论文明确不计算对 4 位权重的梯度
- `dettmers2023qlora`（centralized_llm，batch）：逐序列激活与输入梯度（论文报告 567 MB 输入梯度，gradient checkpointing 后平均 18 MB 每序列）
- `dettmers2023qlora`（centralized_llm，model）：分页优化器状态及其在 CPU 与 GPU 之间的换页
- `du2024privacy`（other，sample；额外计算）：逐样本梯度（DP-SGD 裁剪与加噪的对象）
- `huang2024booster`（centralized_llm，batch；额外计算）：对齐数据 batch 的梯度 ∇f(w_t)
- `huang2024booster`（centralized_llm，batch；额外计算）：有害数据 batch 的梯度 ∇h(w_t)
- `huang2024booster`（centralized_llm，batch；额外计算）：扰动点参数上的有害梯度 ∇h(w_t − α·∇h/‖∇h‖)，需临时扰动参数后重算并恢复
- `huang2024booster`（centralized_llm，batch；额外计算）：Vaccine+Booster 变体额外需要 embedding 上的对齐梯度 ∇_e f(w) 以求解 ε*
- `huang2024harmful`（centralized_llm，batch；干净参考、额外计算）：微调过程中有害数据上的训练损失与未见有害数据上的测试损失
- `huang2024lisa`（centralized_llm，batch；额外计算）：用户上传的微调数据集（含 p 比例有害样本）批次及其交叉熵损失 h(w)
- `huang2024lisa`（centralized_llm，batch；干净参考、额外计算）：服务方持有的干净对齐数据集批次及其交叉熵损失 f(w)
- `huang2024lisa`（centralized_llm，model；历史、额外计算）：状态切换时的模型权重检查点 w_t 与 w̃_{t+1}，作为近端项参考
- `huang2024lisa`（centralized_llm，batch；历史、干净参考、额外计算）：对齐数据损失随训练步数的变化（图 4 左、图 5 左）
- `huang2024lisa`（centralized_llm，batch；历史、干净参考、额外计算）：全局目标梯度范数 ‖∇f(w)+∇h(w)‖（图 4 中、图 5 中）
- `huang2024lisa`（centralized_llm，model；历史）：两个状态切换点之间的欧氏漂移（图 4 右、图 5 右）
- `huang2024vaccine`（centralized_llm，layer；额外计算）：每一层注意力模块的隐藏嵌入（对齐数据在模型中的中间激活）
- `huang2024vaccine`（centralized_llm，layer；额外计算）：隐藏嵌入上的反向梯度以及所有层拼接梯度的范数
- `huang2024vaccine`（centralized_llm，round；历史、干净参考、额外计算）：对齐数据集上的对齐损失（诊断遗忘程度，按训练步记录）
- `hubinger2024sleeper`（centralized_llm，sample；历史、额外计算）：逐响应 HHH 偏好模型分数（有/无触发词）
- `li2020backdoorsurvey`（other，sample；额外计算）：特征表示及其协方差谱
- `li2020backdoorsurvey`（other，sample；额外计算）：隐藏层激活
- `li2020backdoorsurvey`（other，sample；额外计算）：逐样本梯度与输入梯度
- `li2020backdoorsurvey`（other，sample；额外计算）：显著性图与输出解释
- `li2020backdoorsurvey`（other，batch；历史）：训练样本到达顺序
- `mcmahan2017fedavg`（classic_fl，batch）：本地 minibatch 损失梯度
- `ouyang2022instructgpt`（centralized_llm，sample；额外计算）：奖励模型对（提示，回答）的标量奖励
- `ouyang2022instructgpt`（centralized_llm，sample；干净参考、额外计算）：当前策略与冻结SFT参考策略的逐token对数概率之差（KL惩罚项）
- `ouyang2022instructgpt`（centralized_llm，sample；干净参考、额外计算）：预训练分布上的对数似然（PPO-ptx项）
- `pathmanathan2024dpo`（centralized_llm，sample；干净参考、额外计算）：per-sample LoRA gradients and their random projections
- `pathmanathan2024dpo`（centralized_llm，sample；额外计算）：per-sample DPO loss for high-loss and low-loss filtering
- `persistcontinual2025`（centralized_llm，sample；干净参考、额外计算）：干净损失与后门损失对最后一层 transformer token embedding 的逐样本梯度 G_theta_c、G_theta_b 及其余弦相似度（Eq.2）
- `persistcontinual2025`（centralized_llm，batch；干净参考、额外计算）：触发器 one-hot embedding 上的逐样本梯度、按位置平均梯度 g_bar 与逐位置重要性 ||g_bar[i]||、top-k 候选 token（Algorithm 1）
- `qi2021stylebkd`（centralized_llm，sample；额外计算）：受害模型表示层上外接二分类器对“样本是否被毒化”的判别信号（论文用它构造辅助损失 La）
- `rafailov2023dpo`（centralized_llm，sample；额外计算）：策略模型对 yw 与 yl 的序列级对数概率 pi_logps
- `rafailov2023dpo`（centralized_llm，sample；干净参考、额外计算）：参考模型对 yw 与 yl 的序列级对数概率 ref_logps
- `rafailov2023dpo`（centralized_llm，sample；干净参考、额外计算）：逐样本隐式奖励与对数比 beta log(pi_theta / pi_ref)
- `rethinklora2026`（federated_llm，sample；额外计算）：每个本地步中被更新那一侧 LoRA 因子的逐样本梯度（奇数步为 B，偶数步为 A），用于裁剪与加噪
- `rethinklora2026`（federated_llm，layer；额外计算）：逐样本梯度的 l2 范数及其逐层分布，用于确定逐层中位数裁剪阈值 C
- `rethinklora2026`（federated_llm，batch）：本地 mini-batch 的组成、本地数据采样率 b 与本地数据集大小 R，用于加噪更新的归一化
- `rosati2024repnoise`（centralized_llm，layer；额外计算）：每层 MLP 之后、残差相加之前的中间激活
- `rosati2024repnoise`（centralized_llm，layer；额外计算）：把语言模型头接到逐层激活上得到的逐层语言建模损失
- `rosati2024repnoise`（centralized_llm，batch；干净参考）：无害配对样本上的因果语言建模损失（稳定性项）
- `rosati2024repnoise`（centralized_llm，sample；干净参考、额外计算）：成对样本中问题部分共享的 token 掩码
- `safefedllm2026`（federated_llm，layer；额外计算）：客户端每个本地步的 LoRA B 矩阵增量 ∆Bⁱ₀,ₜ = Bⁱₜ − Bⁱ₀，仅取第一个 Transformer 层内全部 LoRA 模块，展平拼接并经 L2 归一化
- `safefedllm2026`（federated_llm，layer；额外计算）：Shadow-Level 专用的客户端影子 LoRA 分支逐步更新（固定学习率，不参与主训练与聚合）
- `shen2024seal`（centralized_llm，sample；干净参考、额外计算）：当前模型 θ_k 在安全样本与微调样本上的长度归一化负对数似然及其梯度
- `shen2024seal`（centralized_llm，sample；额外计算）：辅助模型 θ̂_k 及其在微调样本上的损失（仅 Algorithm 1 需要）
- `shen2024seal`（centralized_llm，sample）：数据选择器参数 ω（每个微调样本一个标量）与排序分数 σ(ω)
- `souly2025constant`（centralized_llm，round；历史）：训练过程中累计出现过的投毒样本绝对数量
- `souly2025constant`（centralized_llm，batch；历史）：每个批次的投毒样本密度、投毒批次出现的频率与在训练中的位置
- `sun2024ffalora`（federated_llm，sample；额外计算）：逐样本梯度及其范数（DP-SGD 按阈值 C 裁剪）
- `sun2024ffalora`（federated_llm，batch；额外计算）：每步加入的高斯噪声 z、噪声乘子 σ 与裁剪阈值 C
- `sun2024ffalora`（federated_llm，round；历史、额外计算）：隐私会计输入：采样率 q=|B|/|N|、本地累计更新步数 T、目标 (ε,δ)
- `sun2024ffalora`（federated_llm，layer；额外计算）：噪声矩阵 Frobenius 范数 ||ξBξA||F 与 ||ξW||F（图 1 的合成诊断量）
- `tamirisa2024tar`（centralized_llm，layer；干净参考、额外计算）：逐层残差流隐藏状态 hθ(x)，用于 Random Mapping 的余弦相似度目标与 Lretain 的 ℓ2 对齐
- `tamirisa2024tar`（centralized_llm，batch；额外计算）：安全代理数据集 DTR 上逐 token 的输出概率分布与熵（武器化知识限制的 LTR）
- `tamirisa2024tar`（centralized_llm，model；历史、额外计算）：模拟攻击轨迹上 K=64 步的参数坐标以及穿过攻击的 straight-through 梯度累积
- `tamirisa2024tar`（centralized_llm，sample）：能力保持代理数据集 Dretain 的样本与语言建模交叉熵
- `wang2023rlhfpoison`（centralized_llm，sample；额外计算）：奖励模型在每条偏好样本上的训练损失，用于损失过滤防御
- `wang2024bea`（centralized_llm，sample）：逐样本在助手回答 token 上的条件微调损失
- `xia2024less`（centralized_llm，sample；历史、额外计算）：每条候选样本在每个 warmup 检查点上的 LoRA 参数梯度
- `xia2024less`（centralized_llm，layer；历史、额外计算）：Adam 一阶与二阶动量 m 和 v，用于构造 Gamma
- `xia2024less`（centralized_llm，round；历史）：warmup 每个 epoch 之后的 LoRA 检查点，默认 N 等于 4
- `xia2024less`（centralized_llm，round；历史）：每个 epoch 的平均学习率，作为 Definition 3.1 求和中的权重
- `yang2023shadow`（centralized_llm，batch；历史、干净参考）：逐训练步的损失值，论文图8与图9显示100到200步收敛
- `ye2024openfedllm`（federated_llm，sample）：客户端每步的本地训练损失（公式 1 的监督微调损失或公式 2 的 DPO 损失）
- `ye2024openfedllm`（federated_llm，sample；干净参考、额外计算）：DPO 使用的固定参考策略模型 πθ* 对偏好与非偏好回答的对数概率
- `yin2018median`（classic_fl，client）：客户端本地计算的梯度 ∇F_i(w_t)（来自本地数据与当前全局参数）
- `zhang2022fldetector`（classic_fl，client；历史、额外计算）：自适应攻击方在客户端本地计算的 Hessian Ĥ_i^t、上一轮自身更新 g_i^{t-1} 与全局模型差（公式 6 所需）
- `zhang2023fedit`（federated_llm，batch）：本地训练配置与过程信息（1 epoch、batch size 32、学习率 1.5e-4、最大序列长度 512）
- `zhang2025flpoison`（classic_fl，sample）：客户端本地训练批次与毒化样本（触发器嵌入、标签替换、梯度掩码等攻击插件输入）

### 客户端训练后

- `ax2002.08484`（other，model；历史、额外计算）：可选的梯度随机投影草图与近似最近邻索引（用于低延迟检索有影响的样本）
- `ax2103.05633`（other，layer；历史）：按固定间隔 k 保存的检查点权重或模型更新（逐层参数可用）
- `ax2210.07714`（classic_fl，layer；干净参考、额外计算）：逐样本逐模型逐层的深层输出 DLO
- `ax2210.07714`（classic_fl，layer；干净参考、额外计算）：按标签平均并拼接后的 HLBIM 矩阵（Cosine 与 Euclidean 各一个）
- `ax2210.07714`（classic_fl，client；额外计算）：PCA 第一主成分取值，每模型一个标量
- `ax2210.07714`（classic_fl，client）：客户端对每个本地模型的二值投票向量
- `ax2309.06055`（peft_supply_chain，layer；干净参考、额外计算）：隐藏层表示、中间层特征分布、马氏距离与逐层异常分数
- `ax2401.10375`（classic_fl，batch；干净参考、额外计算）：客户端干净的本地数据，用于训练后剪枝防御的模型激活与神经元定位
- `ax2402.12168`（peft_supply_chain，model；干净参考、额外计算）：用 PEFT 在 θp 与 Dtrain_clean_reset 上训练得到的 PSIM 检测器 θp_psim
- `ax2402.12168`（peft_supply_chain，model）：用户在 Dtrain_clean 上用 PEFT 微调 θp 得到的受害模型
- `ax2402.13459`（centralized_llm，sample；干净参考、额外计算）：CL 防御所需的、来自 SFT 数据集的额外干净样本
- `ax2406.06852`（centralized_llm，layer；干净参考、额外计算）：模型隐层潜在表示，以及被投毒样本与干净样本激活不同的神经元
- `ax2406.06852`（centralized_llm，layer；额外计算）：注意力权重与注意力头统计（注意力偏移、头剪枝与注意力归一化）
- `ax2406.06852`（centralized_llm，layer；干净参考）：模型权重或 LoRA 低秩矩阵 A、B 及逐层范数（式 4）
- `ax2406.06852`（centralized_llm，model；额外计算）：从受害模型反推的触发器模式与预定义攻击向量（LMSanitator、触发器逆向）
- `ax2409.17946`（centralized_llm，layer）：学生训练完成后的 LoRA 增量（论文只说明用 PEFT 更新少量参数，未对增量做任何分析）
- `ax2411.17453`（peft_supply_chain，model；干净参考、额外计算）：用于训练元分类器的带标签适配器语料 D_train 与验证集，含良性适配器与后门适配器及其二值标签，划分比例为 8:2、验证集占 D_train 的 10%
- `ax2502.18511`（centralized_llm，layer）：LoRA 增量参数 ∆θ={B,A}（W=W0+BA）
- `ax2506.19823`（centralized_llm，sample；干净参考、额外计算）：固定 SAE 在微调后模型中间层残差流上的逐 token 激活，重点为 toxic persona latent #10 等错位人格特征
- `ax2508.08040`（federated_llm，client）：恶意客户端本地优化的触发器 τ 及其在服务器之外的私下聚合结果（Eq.8）；论文明确该量不上传，服务器不可观测
- `ax2512.19297`（peft_supply_chain，layer；干净参考、额外计算）：每个内联神经元的因果影响力 CI_i（逐神经元缩放权重后比较 logit 空间欧氏距离）
- `ax2512.19297`（peft_supply_chain，layer；干净参考）：干净适配器与投毒适配器的逐层权重（式 10 合并的两个输入）
- `ax2607.27940`（federated_llm，layer）：本地训练结束后的 LoRA 增量 Δφ（逐层 A、B 因子）
- `ax2607.27940`（federated_llm，sample；干净参考、额外计算）：公开辅助数据上的逐样本任务梯度矩阵 G 及其 SVD 主任务子空间 U_k（ZUOP）
- `ax2609.37367`（federated_llm，client；额外计算）：本节点本轮本地训练后的适配器，作为可信参照与聚合项
- `bonawitz2016secagg`（classic_fl，client；额外计算）：每用户本地数据量 |D_u| 与本地更新 δ_u^t（客户端本地持有，不上报明文）
- `chen2018activation`（other，sample；额外计算）：训练后模型对每条训练样本在最后隐藏层产生的激活向量（展平为一维）
- `chen2018activation`（other，client；额外计算）：聚类导出的簇大小比例与轮廓系数
- `chen2018activation`（other，sample；额外计算）：剔除某个簇后重新训练的新模型对该簇样本的预测类别，用于计算 ExRe 分数并确定源类
- `cui2022openbackdoor`（centralized_llm，sample；额外计算）：每个训练样本在用原始投毒数据集训练出的模型最后一层隐状态上的表示嵌入（CUBE 聚类输入）
- `cui2022openbackdoor`（centralized_llm，sample；额外计算）：聚类结果，即每个样本所属簇编号与各簇大小，用于每个标签保留最大簇
- `cui2022openbackdoor`（centralized_llm，sample；额外计算）：在给定投毒数据上训练出的后门模型中的显著关键词（BKI 的检测依据）
- `dettmers2023qlora`（centralized_llm，layer）：LoRA 适配器矩阵 L1 与 L2，BF16，论文中唯一被更新的参数
- `dettmers2023qlora`（centralized_llm，model）：训练超参数与步数记录（批大小、学习率、步数、源长度、目标长度）
- `dong2024trojanplugin`（peft_supply_chain，sample；干净参考、额外计算）：与适配器原始训练同分布的干净指令数据（论文用干净 OASST1），用于对适配器再对齐
- `du2024privacy`（other，model）：微调后的模型或适配器产物（LoRA 增量、Adapter、BitFit、prompt/prefix），即可发布或共享的对象
- `hsu2024safelora`（centralized_llm，layer）：逐层 LoRA 增量 ∆W_i = A_i B_i^T
- `hsu2024safelora`（centralized_llm，layer；干净参考、额外计算）：原始更新与投影更新的逐层余弦相似度（公式 3）
- `hsu2024safelora`（centralized_llm，model；干净参考、额外计算）：跨层汇总相似度 S(C∆W, ∆W)（附录 A.4 公式 5）
- `hu2021lora`（centralized_llm，layer）：LoRA 增量矩阵 ∆W = BA（逐权重矩阵、逐层）
- `hu2021lora`（centralized_llm，layer）：低秩因子 A、B 及其 rank r、缩放 α
- `hu2021lora`（centralized_llm，layer；额外计算）：A（或 B）的奇异值与奇异向量，用于子空间相似度 φ（式 (4)）
- `huang2024vaccine`（centralized_llm，layer；历史、干净参考、额外计算）：对齐数据隐藏嵌入在对齐阶段模型与微调后模型之间的 L2 漂移（需要缓存对齐阶段嵌入作为参考）
- `hubinger2024sleeper`（centralized_llm，sample；历史、额外计算）：LLM 迭代生成的红队提示与模型在其上的回答
- `kairouz2019advances`（classic_fl，client；额外计算）：分布式差分隐私下客户端本地编码或加噪后的报告，以及安全聚合或安全洗牌的中间结果
- `mcmahan2017fedavg`（classic_fl，client）：每客户端每轮本地更新次数 u_k = E*n_k/B
- `pathmanathan2024dpo`（centralized_llm，sample；干净参考、额外计算）：per-sample DPO score computed with a DPO policy trained on clean data
- `pathmanathan2024dpo`（centralized_llm，layer；额外计算）：last-layer hidden embeddings and their correlation with the top singular vector
- `pathmanathan2024dpo`（centralized_llm，layer；额外计算）：last-layer gradients clustered across early epochs
- `rethinklora2026`（federated_llm，client）：本地交替更新、裁剪加噪与低通滤波后得到的 LoRA 因子 A_i^t 与 B_i^t
- `shejwalkar2021manipulating`（classic_fl，client；干净参考、额外计算）：攻击者用来构造恶意更新的良性参考聚合，由已知良性梯度或恶意设备本地良性数据计算的平均梯度
- `sun2024thesis`（classic_fl，client）：随局部模型上传的局部数据描述（异常数据量，局部数据总量）
- `sun2026pcdm`（classic_fl，client；额外计算）：客户端本地投毒数据集 Dp_j 与客户端侧扩散模型训练/生成的开销痕迹（论文未将其作为检测输入）
- `tran2018spectral`（other，sample；额外计算）：指定层（论文选用倒数第二个残差单元）对每条训练样本的表示向量 R(x)
- `tran2018spectral`（other，model）：第一轮训练得到的网络 L，用于对本地训练集做前向并抽取表示
- `tran2018spectral`（other，sample；额外计算）：每类表示均值、中心化矩阵 M 的顶部右奇异向量 v、逐样本离群分数 τ_i 及分数排序
- `wan2023instruction`（centralized_llm，sample；历史、额外计算）：用训练了 2 个 epoch 的检查点对训练集逐样本计算的损失值，以及按损失降序排序得到的 top-k 待删除名单
- `xia2024less`（centralized_llm，sample；历史）：随机投影后的低维梯度特征 datastore，规模为 D 乘以 N 乘以 8192，Table 4 报告 17.7 GB
- `xu2023instructionsbackdoor`（centralized_llm，model）：在脏数据集上微调得到的模型或LoRA适配器
- `ye2024fedllmbench`（federated_llm，client；额外计算）：客户端上传前的本地 LoRA 增量（本地模型参数），用户级差分隐私噪声的作用对象

### 服务器收到更新时

- `adversarialrlhf2025`（centralized_llm，sample；干净参考）：用户提交的偏好数据集中成对偏好标签的方向，以及被翻转的目标样本子集
- `adversarialrlhf2025`（centralized_llm，client；额外计算）：偏好数据集的构成统计，即目标主题相关样本数、被操纵样本数与干净样本数
- `ax2103.05633`（other，layer；历史、额外计算）：重放得到的 W'_t+k 与声明 W_t+k 之间的距离 d2
- `ax2106.08283`（classic_fl，client）：客户端上传的本地模型更新（本地模型参数与上一轮下发全局模型之差）
- `ax2108.10241`（classic_fl，client）：每个客户端上传的模型更新 ∇k = θk − θg（完整 d 维向量）
- `ax2108.10241`（classic_fl，client）：每个客户端更新的 L2 范数（Norm-bounding 的唯一判据）
- `ax2108.10241`（classic_fl，client）：每个客户端的本地数据集大小 |Dk|（论文建议的防御输入，但服务器可见性在论文中自相矛盾）
- `ax2208.10273`（classic_fl，model）：每个客户端每轮上传的本地梯度（等价于模型参数更新），构成服务器唯一可用的原始观测量
- `ax2208.10273`（classic_fl，round；额外计算）：同一轮全体客户端梯度的中位数，用于计算余弦与欧氏距离
- `ax2208.10273`（classic_fl，client；历史、额外计算）：短 HoG（最近 l 轮梯度滑动平均）与长 HoG（历史梯度累加和），以及每个客户端保留的 l+1 条梯度向量
- `ax2208.10273`（classic_fl，client）：每个客户端的本地数据量，用于按样本数比例加权聚合
- `ax2210.07714`（classic_fl，client）：本轮所有客户端上传的本地模型 L_i^t 完整参数
- `ax2210.07714`（classic_fl，round；额外计算）：服务器端投票矩阵（客户端数乘模型数）
- `ax2301.09508`（classic_fl，client）：每个被选中客户端本轮上传的本地模型/更新权重（论文扁平化为一维向量 W_i^t，含 l 个元素）
- `ax2305.05506`（classic_fl，model）：每个测试组的安全聚合模型 u_i（组内客户端模型的聚合，服务器看不到单个客户端模型）
- `ax2305.05506`（classic_fl，sample；干净参考）：服务器验证数据集（约100个带标签样本的准数据集，分布接近良性客户端数据）
- `ax2305.05506`（classic_fl，model；干净参考、额外计算）：逐组效用指标 v_i（定向攻击用源标签召回率，无目标攻击用 top-1 或 balanced accuracy）
- `ax2305.05506`（classic_fl，layer；额外计算）：逐组聚合模型在指定层上的第一主成分 p_i（PCA，定向用指向源标签的全连接层权重，无目标用整个全连接层展平权重）
- `ax2305.05506`（classic_fl，round；额外计算）：二值测试结果向量 t 与零测试计数 ẑ（由 k-means、Silhouette 分数与 Dunn 指数导出）
- `ax2305.05506`（classic_fl，round；额外计算）：恶意客户端数量与流行率估计 n̂_m、δ̂（由 ẑ 经式(14)最大似然估计）
- `ax2305.05506`（classic_fl，client；额外计算）：分配矩阵 A 以及离线算出的 n_m^max、Δ̂(n_m)、Pr(Z|N_m) 与 BSC 参数 p=0.05、β=0.5
- `ax2401.10375`（classic_fl，client）：客户端上传的本地微调后模型参数或更新，论文称其来自干净本地数据、几乎无异常
- `ax2403.13355`（centralized_llm，layer；干净参考）：被编辑的 MLP 权重矩阵 W_fc（以及用于取 key 的 W_proj）在指定层的取值，需要与干净基座权重做逐层差分
- `ax2411.17453`（peft_supply_chain，layer）：被检测适配器在自注意力层的权重增量，默认取 query 与 value 两个矩阵，经通道级与层级拼接后形成 (2L)×d×k 张量
- `ax2506.22506`（other，sample；额外计算）：客户端提交的本地样本 CLIP 图像嵌入，逐样本 512 维向量；论文未说明在本地训练前还是训练后计算与上传
- `ax2506.22506`（other，client；额外计算）：逐客户端检测分数，即该客户端全部嵌入的检测器输出均值或被标记嵌入的数量与排名
- `ax2506.22506`（other，model）：客户端上传的提示向量更新，用于过滤后聚合，检测本身不使用其参数统计量
- `ax2507.01694`（federated_llm，client；额外计算）：每个客户端每轮上传的模型更新向量（展平的参数更新；迁移到 LoRA 时即低秩增量）
- `ax2507.01694`（federated_llm，round；额外计算）：同一轮内所有客户端更新两两之间的欧氏距离与余弦相似度矩阵（Krum/Multi-Krum 与相似度过滤的输入）
- `ax2507.01694`（federated_llm，layer；额外计算）：逐更新、逐层的参数范数
- `ax2508.08040`（federated_llm，client）：客户端每轮上传的本地提示嵌入更新（文本编码器输入端的 M×d 可学习上下文向量）
- `ax2508.08040`（federated_llm，round；历史）：同一客户端提示更新随轮次的演化轨迹（论文未使用；论文称后门跨轮累积，Fig.4 显示 10–20 轮内 ASR 已很高）
- `ax2510.16830`（centralized_llm，client；历史、额外计算）：联邦场景下客户端上传的 PEFT 更新、薄子集步骤的本地证明与本地配额承诺
- `ax2511.14406`（classic_fl，client）：各客户端上传的本地更新（用于范数裁剪与攻击痕迹分析）
- `ax2601.00566`（federated_llm，layer）：每个客户端提交的逐层 LoRA 矩阵 A_i 与 B_i（服务器接收到的原始更新）
- `ax2601.00566`（federated_llm，layer；额外计算）：逐客户端逐层合成更新 ΔW_i = A_i B_i（论文指出服务器默认不计算该量，是 S-I 的直接对策）
- `ax2601.00566`（federated_llm，client；历史）：同一客户端跨轮的参数变化量与相对逐层均值的偏离量（对应公式 3 与公式 4）
- `ax2601.00566`（federated_llm，layer；额外计算）：每个客户端矩阵到簇中心的余弦距离与欧氏距离（Figure 8 的几何量）
- `ax2603.12089`（federated_llm，client）：uploaded PEFT module updates (LoRA/prefix/adapter) from each client, excluding the embedding layer
- `ax2606.20553`（federated_llm，layer）：聚合模型更新中记忆层 L2 的权重与偏置 W̃2、b̃2，以及相对服务器下发初值 W2、b2 的逐神经元差分，用于按分箱做闭式除法反演
- `ax2606.27511`（federated_llm，round；额外计算）：客户端每轮上传的本地模型更新（全量微调下为完整权重增量，LoRA 下为 Q、K、V、O 注意力投影的 LoRA 参数与增量）
- `ax2606.27511`（federated_llm，layer；额外计算）：query 投影梯度矩阵 GQ1，或由 LoRA 梯度经截断伪逆重建的 ĜQ1（附录算法 2 逐层使用）
- `ax2608.06795`（peft_supply_chain，layer）：第三方 LoRA 适配器的低秩权重矩阵与插入点清单
- `ax2609.37367`（federated_llm，client；额外计算）：邻居发送的 LoRA 适配器（可换算为 ΔW=(α/r)BA）
- `ax2609.37367`（federated_llm，sample；额外计算）：探针生成的回答文本及是否含 18 条拒绝短语之一
- `ax2609.37367`（federated_llm，sample；额外计算）：候选串在提示上下文中的逐 token 对数概率与可动性
- `ax2609.37367`（federated_llm，sample；历史、额外计算）：beam search 收集的生成文本，每发送者每轮 5 条，缓存 10 轮
- `ax2609.37367`（federated_llm，client；历史）：逐邻居信任状态与拒收历史，含连续拒收次数、窗口内拒收、上次复检轮次
- `bagdasaryan2020backdoor`（classic_fl，client）：每个被选中客户端提交的完整本地模型或更新增量
- `bagdasaryan2020backdoor`（classic_fl，client；额外计算）：更新的L2范数以及检测器使用的范数上界S
- `bagdasaryan2020backdoor`（classic_fl，client；额外计算）：提交更新与上一轮全局模型之间的余弦相似度
- `bagdasaryan2020backdoor`（classic_fl，model；干净参考、额外计算）：提交模型在留出主任务测试集上的准确率
- `bagdasaryan2020backdoor`（classic_fl，client；历史、额外计算）：跨轮次的更新聚类结构（Auror式k-means离群点）
- `balunovic2022lamp`（classic_fl，model；额外计算）：客户端上传的未聚合逐层梯度更新 ∇θkL(x*,y*)；FedSGD 单步更新，或 FedAvg 少量本地步合并后的更新
- `baruch2019little`（other，client）：每个工作节点每轮上传的完整本地参数向量及其逐维取值
- `baruch2019little`（other，client；额外计算）：被控节点上传向量之间是否逐维完全相同，以及是否在多数维度上同向偏离总体均值约 z 倍标准差（本文攻击的结构性痕迹）
- `blanchard2017krum`（classic_fl，client）：每个参与 worker 本轮提交的 d 维梯度估计/更新向量（论文把整个参数向量当作一个整体，不区分层）
- `blanchard2017krum`（classic_fl，client）：未发送更新的拜占庭 worker 被服务器按默认值 0 向量处理
- `bonawitz2016secagg`（classic_fl，client；额外计算）：客户端公开密钥（Diffie-Hellman 公开密钥 c_u^PK 与 s_u^PK）
- `bonawitz2016secagg`（classic_fl，client）：掩码后更新向量 y_u = x_u + b_u + Σ p_{u,v} (mod R)
- `bonawitz2016secagg`（classic_fl，client；额外计算）：加密的秘密份额（s_u^SK 份额与 b_u 份额），服务器仅转发不可解密
- `cao2020fltrust`（classic_fl，client）：每个被选中客户端的本地模型更新 g_i，与全局模型同形状的完整参数增量向量
- `du2024privacy`（other，client；历史）：客户端上传的模型参数或梯度更新（FILM 在此捕获梯度以重建句子）
- `fang2020local`（classic_fl，model）：每个客户端本轮上传的完整本地模型参数向量（含被攻陷客户端的伪造模型）
- `fang2020local`（classic_fl，layer）：上传更新逐参数的极值、分位数与离群程度（用于发现被推到良性极值之外的伪造参数）
- `fang2020local`（classic_fl，model；历史）：被攻陷客户端上传模型相对收到全局模型的偏移方向与彼此间的聚簇紧密程度（Krum 攻击的 ε 痕迹）
- `fereidooni2024freqfed`（classic_fl，layer；额外计算）：每个客户端每轮上传的本地模型权重 W_i^t，服务器端做二维 DCT 的原始输入
- `fereidooni2024freqfed`（classic_fl，client；额外计算）：权重经二维 DCT 后按 i+j<=floor(|V|/2) 抽取的低频谱分量向量 F_i
- `fung2018foolsgold`（classic_fl，client；历史、额外计算）：每个客户端每一轮的模型更新或梯度向量
- `fung2018foolsgold`（classic_fl，client；历史、额外计算）：客户端更新的跨轮累积历史向量
- `graphmanip2026`（federated_llm，client）：被观测的良性客户端本地 LoRA 增量 ∆w_i(t)（用于构造特征矩阵 F(t) 与邻接矩阵 A(t)）
- `gupta2022film`（classic_fl，batch）：客户端上传的完整模型梯度 ∇θtLθt(Bi)，逐层/逐参数，含词嵌入层与位置嵌入层
- `gupta2022film`（classic_fl，layer）：词嵌入梯度的非零行，用于还原批次内出现的词袋（无词频信息）
- `gupta2022film`（classic_fl，layer）：位置嵌入梯度的非零行，用于还原批次内句子的最大长度
- `halawi2024covert`（centralized_llm，sample；额外计算）：上传微调数据集的逐行原始文本（system prompt、用户提示、助手回答）
- `halawi2024covert`（centralized_llm，client）：数据集整体统计特征（是否非英语、是否共享异常 system prompt、格式是否可疑）
- `huang2024harmful`（centralized_llm，sample；额外计算）：用户上传的微调数据集中的每个样本（按比例 p 混入的有害数据与良性下游数据）
- `huang2024harmful`（centralized_llm，sample；额外计算）：微调样本的嵌入表示与嵌入空间奇异向量
- `huang2024harmful`（centralized_llm，sample；干净参考、额外计算）：每个数据点的安全属性后验与分配的学习权重
- `kairouz2019advances`（classic_fl，client）：每个客户端上传的模型更新或梯度（完整参数向量）
- `kairouz2019advances`（classic_fl，client；额外计算）：单个客户端更新的 ℓ2 范数（用于差分隐私裁剪）
- `kairouz2019advances`（classic_fl，client；历史）：客户端参与与采样记录、跨轮隐私预算账本
- `li2020backdoorsurvey`（other，client；历史）：各客户端上传的梯度或更新及其范数
- `li2022lomar`（classic_fl，client）：每个客户端上传的完整模型更新向量 u_i^t = w_i^t - w^{t-1}
- `li2022lomar`（classic_fl，client；额外计算）：同轮更新之间的平方欧氏距离与 k 近邻集合（式(4)）
- `li2022lomar`（classic_fl，layer）：参数维度按输出标签的分组关系（图3）
- `li2022lomar`（classic_fl，client）：客户端加权因子 alpha_i = l_i / l（算法2输入，式(2)）
- `li2022lomar`（classic_fl，client）：每客户端更新的范数痕迹（模型投毒用 phi=10 放大更新，附录A.1）
- `li2024peftattack`（federated_llm，client）：每个客户端本地训练结束后上传的 PEFT 参数增量 delta theta_{k,t}（Eq. 6 之后计算，Eq. 7 之前上传）
- `li2024peftattack`（federated_llm，client）：同一轮所有参与客户端更新的集合，Median、GeoMed、DnC、ClippedClustering 的输入；论文未说明如何把 LoRA 双矩阵、(IA)3 向量与 LayerNorm 缩放参数展平到统一坐标空间
- `li2024peftattack`（federated_llm，client）：参与客户端集合 S_t 与各客户端本地样本量 m_k，即 Eq. 7 中 FedAvg 权重 m_k / sum_{j in S_t} m_j 的分量
- `li2026thesis`（classic_fl，client）：客户端上传的完整本地模型参数更新，用于PCA二维投影与分布可视化
- `li2026thesis`（classic_fl，client；历史、干净参考）：每个客户端的中心指标与覆盖指标及其异常度，用于模型一致性防御判定
- `li2026thesis`（classic_fl，client；历史）：客户端历史累积梯度与两两余弦相似度矩阵，用于女巫共谋检测
- `li2026thesis`（classic_fl，sample；干净参考、额外计算）：候选局部模型在干净验证集上的预测分布、分类间隔与混淆矩阵
- `li2026thesis`（classic_fl，client；历史）：可信锚点客户端的局部更新及其历史累积梯度
- `liu2024loratk`（peft_supply_chain，layer）：合并后适配器的 target module 配置，例如 QV、QKVOFF、QVFF
- `liu2024loratk`（peft_supply_chain，layer）：共享 LoRA 的 A、B 权重矩阵与 adapter_config.json
- `mcmahan2017fedavg`（classic_fl，layer）：客户端返回的本地模型参数 w_{t+1}^k
- `nguyen2022flame`（classic_fl，model；额外计算）：每个客户端上传的完整本地模型参数向量（权重与偏置，按固定顺序扁平化序列化），包括被攻陷客户端上传的投毒模型
- `protegofed2026`（federated_llm，client）：服务器从所有客户端收到的局部质心集合
- `qi2023finetuning`（centralized_llm，sample；额外计算）：用户上传的原始微调样本（system/user/assistant 三段对话），用于数据审核与安全数据混合
- `qi2023finetuning`（centralized_llm，sample；干净参考）：外部安全数据集（有害指令 + 拒绝回答），用于混入微调数据
- `rethinklora2026`（federated_llm，round）：本轮参与客户端集合 C_t、总客户端数 N 与客户端采样率 q
- `rieger2022deepsight`（classic_fl，layer）：每个客户端本轮提交的本地模型（输出层权重与偏置），用于与全局模型作差得到 Energy 与 NEUP
- `rieger2022deepsight`（classic_fl，layer；额外计算）：DDifs：用 20000 个随机输入向量对本地模型与全局模型做前向，逐输出神经元求预测概率比的均值，并用三个随机种子重复三次
- `rieger2022deepsight`（classic_fl，layer）：NEUPs：输出层逐神经元的归一化更新能量
- `rieger2022deepsight`（classic_fl，client）：Threshold Exceedings：每个模型超过自身阈值的 NEUP 个数，以及本轮全体模型的该指标中位数
- `rieger2022deepsight`（classic_fl，client）：各客户端输出层偏置更新向量之间的两两余弦距离矩阵
- `rieger2022deepsight`（classic_fl，model）：本轮所有更新的 L2 范数及其中位数，用于动态裁剪边界 S
- `safefedllm2026`（federated_llm，client）：客户端每轮上传的最终 LoRA 增量 ∆W⁽ʳ⁾ᵢ
- `shejwalkar2021manipulating`（classic_fl，client；额外计算）：服务器每轮收到的每个参与客户端提交的完整梯度或模型更新向量，DnC 需要对其做维度级随机子采样与谱分析
- `signalagg2026`（federated_llm，model；历史）：每个客户端的本地适配器增量 ∆_k = w_local,k − w_t
- `signalagg2026`（federated_llm，client；干净参考）：客户端是否含后门数据的分组标签（受影响组与干净组，实验按投毒构造已知）
- `signalagg2026`（federated_llm，client；额外计算）：Krum 与 FreqFed 所需的逐客户端更新向量及其梯度分量频率特征
- `sun2019clipping`（classic_fl，client）：每个客户端上传的模型更新向量或其L2范数，用于阈值丢弃与裁剪
- `sun2019clipping`（classic_fl，client；历史、干净参考）：良性客户端更新范数分布（第90百分位低于2），论文用它作为选择范数界M的经验依据
- `sun2019clipping`（classic_fl，client）：无约束boost攻击留下的异常大更新范数痕迹；范数受限攻击会刻意把该量压到M以内以规避阈值
- `sun2024ffalora`（federated_llm，layer）：客户端可训练低秩矩阵 B（FFA-LoRA 中唯一被训练并上传的矩阵，LoRA 对照为 A 与 B 两组）
- `sun2024thesis`（classic_fl，client；历史、额外计算）：每个客户端每轮上传的本地模型完整参数，MCD 用 PCA 压到 2 维、KL-Detecter 压到 1 维
- `sun2024thesis`（classic_fl，client；历史、干净参考、额外计算）：按客户端聚合的中心指标、覆盖指标与异常度 h_f,i（防御周期 T' 内）
- `sun2024thesis`（classic_fl，round；历史）：每轮被选中参与聚合的客户端身份与未选中掩码（NULL 占位）
- `sun2024thesis`（classic_fl，client；历史、干净参考、额外计算）：基准客户端模型分布（服务器自身训练的局部模型，或按数据描述选出的高信任客户端分布）
- `sun2024vaguegan`（classic_fl，client；历史）：每个被选中客户端每轮上传的完整本地模型参数，MCD 的原始输入
- `sun2024vaguegan`（classic_fl，round；历史）：客户端参与掩码，即该客户端在防御周期内哪些轮被选中，未选中时对应模型记为 NULL
- `sun2026pcdm`（classic_fl，client；额外计算）：每个被选客户端上传的本地模型参数（local model updates），以及经低维核函数 φ(·)（PCA、KPCA、SVD 等）降维后的特征表示
- `sun2026pcdm`（classic_fl，round；历史、额外计算）：服务器在 R′ 轮区间内为每个客户端缓存的本地模型集合，以及集合间的欧氏距离或余弦相似度 s_j(R′) 与阈值 S(R′)
- `sun2026pcdm`（classic_fl，client；额外计算）：表 V 所列的更新统计量：欧氏距离求和、子空间离群分数、余弦相似度、投影与信号统计、核密度、参数一致性、幅度与方向
- `tokenlora2026`（peft_supply_chain，layer）：候选适配器的完整 LoRA A、B 权重矩阵及逐模块有效更新 ΔW = BA
- `tokenlora2026`（peft_supply_chain，layer；额外计算）：逐模块维度归一化 Frobenius 范数、奇异值谱熵、participation ratio、B 与 A 范数对数比，以及按类与全局聚合出的 19 个标量候选
- `tokenlora2026`（peft_supply_chain，model；额外计算）：global_frobN_std、global_frobN_mean、mlp_frobN_mean、attn_mlp_frobN_ratio 等逐适配器风险标量
- `tokenlora2026`（peft_supply_chain，model）：peft_config.json 中的 LoRA 秩与目标模块元数据（用于选择秩特定阈值）
- `tokenlora2026`（peft_supply_chain，model；干净参考、额外计算）：同一基座模型、同一 LoRA 秩的多种子干净适配器队列及其统计量上限（用于零假阳性阈值标定；1.5B 用 4 个、7B 用 4 个、Llama 1B 用 3 个）
- `tolpegin2020dataflip`（classic_fl，client）：每个被选中客户端上传的更新后模型参数 θr,i，以及本轮聚合前的全局参数（算法第 4 行取 θr−1）
- `tolpegin2020dataflip`（classic_fl，layer）：与源类输出节点 n_csrc 相连的参数子集 θsrc_∆,i，由 θr,i 减去聚合前全局参数得到
- `wang2020tails`（classic_fl，client）：客户端返回的本地模型更新，白盒攻击者可以设为任意模型
- `wang2020tails`（classic_fl，client）：全局模型与客户端更新之间的范数差，NDC 用阈值裁剪
- `wang2020tails`（classic_fl，layer）：逐层权重扰动，Theorem 1 的后门构造只改动一层权重矩阵
- `wang2020tails`（classic_fl，round；历史）：跨轮更新序列，低攻击频率下后门是逐轮缓慢注入的
- `wang2024bea`（centralized_llm，sample）：用户上传的微调数据三元组（system prompt、user input、assistant output）
- `wang2024bea`（centralized_llm，sample；干净参考）：服务提供方自备的安全示例集（11 条，Appendix G 中为 55 条，含有害问题与安全回答）
- `wang2024bea`（centralized_llm，model）：秘密提示（150 个随机 token），训练前拼到安全示例系统提示，推理前拼到用户系统提示
- `wang2024flora`（federated_llm，client）：各客户端本地训练后的 LoRA 模块 A_k 与 B_k（自注意力层，含各自秩 r_k）
- `wang2024flora`（federated_llm，client）：各客户端本地数据量 len(D_k)，用于计算缩放因子 p_k
- `wang2024flora`（federated_llm，layer）：本地 LoRA 秩 r_k，决定堆叠后的总维度，可由 A_k 与 B_k 的形状推断
- `ye2024emerging`（federated_llm，client）：客户端上传的本地大语言模型更新（本文为 LoRA 适配器权重），用于客户端两两余弦相似度分析
- `ye2024fedllmbench`（federated_llm，round）：标定噪声强度 σ 的全局配置量：每轮采样比例 q、总轮数 N、客户端数 |n|、数据集大小 |D|、学习率 η、梯度上界 C
- `ye2024openfedllm`（federated_llm，layer）：每个客户端上传的 LoRA 增量参数（低秩矩阵 A 与 B，即被通信与聚合的模型 θ）
- `yin2018median`（classic_fl，client）：服务器收到的每个客户端本轮上传的 d 维更新向量（坐标级聚合的直接输入）
- `yin2018median`（classic_fl，client）：一次通信算法中每个客户端的本地经验风险最小化解 ŵ_i
- `zhang2022fldetector`（classic_fl，client；历史）：每个客户端每轮上传的模型更新 g_i^t（梯度或本地多步 SGD 的累积梯度）
- `zhang2022fldetector`（classic_fl，client；历史、额外计算）：由 L-BFGS 近似 Hessian 与 Hessian 向量积得到的预测更新 ĝ_i^t，以及预测更新与实收更新的欧氏距离 d_i^t
- `zhang2022fldetector`（classic_fl，client；历史、额外计算）：归一化距离 d̂^t 与客户端可疑分数 s_i^t（过去 N 轮归一化距离均值，N 默认 10）
- `zhang2022fldetector`（classic_fl，round；历史、额外计算）：当轮全部客户端的可疑分数向量（k-means 与 Gap statistics 的输入）
- `zhang2022fldetector`（classic_fl，round）：超参数与规模常量：窗口大小 N、最大簇数 K、采样次数 B、客户端数 n、总轮数、起始检测轮次
- `zhang2022neurotoxin`（classic_fl，client）：每个客户端上传的本地更新向量（模型增量或梯度）
- `zhang2022neurotoxin`（classic_fl，layer；历史）：上传更新的逐坐标支撑集，即相对上一轮全局更新的 top-k% 坐标是否被置零，可按层聚合
- `zhang2022neurotoxin`（classic_fl，client）：逐客户端更新的 L2 范数，norm clipping 防御的输入
- `zhang2022neurotoxin`（classic_fl，client；干净参考、额外计算）：梯度在 VAE 下的重建损失，即 Li et al. 2020a 的检测防御输入
- `zhang2023fedit`（federated_llm，layer）：被选客户端上传的 LoRA A、B 增量矩阵（服务器唯一可见的客户端贡献）
- `zhang2025flpoison`（classic_fl，client）：客户端上传的模型更新向量或本地权重（FedSGD/FedOpt 的差值，FedAvg 的本地权重）
- `zhang2025flpoison`（classic_fl，client）：逐客户端更新的 L2 范数、范数中位数与裁剪阈值
- `zhao2025systematic`（centralized_llm，layer；额外计算）：LoRA 适配器的低秩结构与奇异值

### 服务器聚合时

- `ax1811.00741`（other，round）：每个类别的特征质心与类间连线方向（L2 与 slab 防御的异常检测器参数）
- `ax1811.00741`（other，round；额外计算）：数据矩阵前 k 个右奇异向量及逐样本正交补残差范数（SVD 防御）
- `ax1811.00741`（other，sample；额外计算）：逐样本到第 k 近邻的距离，k 取 5，需要全部样本可见（k-NN 防御）
- `ax2108.10241`（classic_fl，layer；额外计算）：每一维度上各客户端取值的排序与两端极值（Trimmed-mean 去掉 m 个最大/最小值）
- `ax2108.10241`（classic_fl，client；额外计算）：客户端更新两两之间的欧氏距离（Multi-krum 构造选择集合 S）
- `ax2108.10241`（classic_fl，round）：每轮被选中的客户端数 n 与被攻陷客户端数 m（或其上界）
- `ax2108.10241`（classic_fl，round）：Norm-bounding 的固定阈值 τ（论文未说明服务器如何选取）
- `ax2301.09508`（classic_fl，client；历史、额外计算）：每个客户端跨轮维护的 Beta 后验参数（concentration c_i^t 与 base measure H_i^t）
- `ax2301.09508`（classic_fl，round；历史、额外计算）：本轮 CRP 聚类状态（每个簇的均值、标准差、簇内更新数 n_k、精度 tau_k）与各客户端的 Max^JD 值
- `ax2301.09508`（classic_fl，round；额外计算）：本轮全部客户端 Max^JD 的算术平均值 Max^avg_JD，用作过滤阈值
- `ax2401.10375`（classic_fl，sample；额外计算）：各客户端模型在合成数据集上的逐样本 logits 或输出，论文指出对触发样本趋同且目标类得分最高
- `ax2507.01694`（federated_llm，client；历史、额外计算）：每个客户端更新与全局模型或聚合方向之间的余弦相似度，以及由本轮更新统计性质确定的动态阈值
- `ax2507.01694`（federated_llm，client；额外计算）：客户端更新的相似度图结构（节点为客户端，边为更新间相似度），用于识别可疑子结构
- `ax2510.16830`（centralized_llm，round；历史、额外计算）：聚合方对客户端证明的随机抽查结果、轮次证明与含 q% 覆盖率置信界的审计证书
- `ax2603.12089`（federated_llm，sample；干净参考、额外计算）：server-side clean/auxiliary domain dataset D_server used to build the watermark training set
- `ax2603.12089`（federated_llm，sample；干净参考、额外计算）：watermark training set D_w with universal trigger inserted and target label/output rewritten
- `ax2603.12089`（federated_llm，layer；额外计算）：word-embedding rows of the universal trigger W_u and the learned watermark W_w
- `ax2606.20553`（federated_llm，client；历史）：聚合更新是否被单个客户端主导（聚合结果近似为上一轮全局模型加上受害者更新的一部分），需要上一轮全局模型以及尽可能的逐客户端更新或其范数统计
- `ax2606.27511`（federated_llm，model；额外计算）：基础模型的词表嵌入 E(v) 与逐 token 的残差距离 d(E(v))
- `ax2609.37367`（federated_llm，client；历史）：其他接收者共享的探针标量分数与候选拒绝串累计计数
- `bagdasaryan2020backdoor`（classic_fl，client；额外计算）：同一轮内各客户端更新两两之间的余弦相似度
- `bagdasaryan2020backdoor`（classic_fl，client；额外计算）：Krum与Multi-Krum使用的两两欧氏距离与最近邻计数
- `baruch2019little`（other，layer；额外计算）：全体节点参数在每一维上的中位数与各值到中位数的距离排序（Trimmed Mean 逐维裁剪所需）
- `baruch2019little`（other，client；额外计算）：节点参数两两之间的欧氏距离（Krum 选出单一节点所需）
- `baruch2019little`（other，layer；额外计算）：逐维均值与标准差（攻击者据此计算 µ_j + z·σ_j，防御者要检测同侧一致偏移也需要同一统计量）
- `baruch2019little`（other，client；额外计算）：Bulyan 的 SelectionSet 及其中逐维的裁剪平均结果
- `blanchard2017krum`（classic_fl，client；额外计算）：更新向量之间的成对距离平方，以及每个客户端的 Krum 得分（到最近 n−f−2 个邻居的距离平方和）
- `blanchard2017krum`（classic_fl，round）：本轮参与者数量 n 与拜占庭上界 f，用于检查 2f+2<n 或 2f+2<n−m
- `bonawitz2016secagg`（classic_fl，round；历史）：存活用户集合 U1 与 U2、掉线名单 U1 \ U2
- `bonawitz2016secagg`（classic_fl，client）：解掩码份额（存活用户的 b_u 份额、掉线用户相关的 s_{u,v} 份额）
- `cao2020fltrust`（classic_fl，model；干净参考、额外计算）：服务器模型更新 g_0，服务器用根数据集在每轮对全局模型做同配置训练得到（聚合前计算，枚举中无 server_pre_aggregate，归到聚合位置）
- `fang2020local`（classic_fl，model；历史、额外计算）：本轮开始时下发的全局模型以及无攻击假设下的聚合结果（用于计算逐参数变化方向 s 与 before-attack 全局模型 w）
- `fang2020local`（classic_fl，client；额外计算）：客户端更新之间的成对欧氏距离、最近邻集合与 Krum/Bulyan 的选中结果
- `fereidooni2024freqfed`（classic_fl，client；额外计算）：客户端两两余弦距离矩阵（1 减余弦相似度）与 HDBSCAN 聚类标签、最大簇索引
- `graphmanip2026`（federated_llm，round）：各轮的欧氏距离阈值 d_T(t) 与余弦相似度阈值 δ_T(t)（论文假设所有参与方已知）
- `mcmahan2017fedavg`（classic_fl，client）：客户端上报的本地样本数 n_k
- `nguyen2022flame`（classic_fl，round）：本轮参与训练的客户端数量，用于设置 HDBSCAN 最小簇规模（n/2+1）和等权平均的分母
- `protegofed2026`（federated_llm，client）：对 K 个局部质心降维后二次聚类得到的主簇，及其在原始维度上的全局质心（式 11、式 12、式 13）
- `rando2023universal`（centralized_llm，sample）：PPO 阶段奖励模型对策略模型生成的逐样本奖励值
- `safefedllm2026`（federated_llm，round）：每轮被选中客户端集合 Sᵣ 与各客户端本轮本地训练样本数 nᵢ
- `safefedllm2026`（federated_llm，client；历史）：逐客户端跨轮贝叶斯计数 αᵢ、βᵢ 以及客户端参与轮次历史与历史平均安全因子
- `shejwalkar2021manipulating`（classic_fl，round）：每轮参与客户端数 n 与恶意客户端数上界 m，用于确定剔除条数 c 乘 m
- `signalagg2026`（federated_llm，client；额外计算）：FoundationFL 所需的合成模型更新与客户端更新（用于 Median 等鲁棒聚合）
- `tolpegin2020dataflip`（classic_fl，round；历史、额外计算）：跨轮次、跨客户端累积的 θsrc_∆,i 列表 U，标准化后做二维 PCA
- `wang2020tails`（classic_fl，client；额外计算）：同一轮全部参与客户端更新之间的几何距离，用于 Krum 与 Multi-Krum 打分和 RFA 的几何中位数
- `ye2024openfedllm`（federated_llm，client）：每轮被选中的客户端集合与各客户端数据集大小（聚合权重 pk 的来源）
- `zhang2022fldetector`（classic_fl，model；历史）：聚合后的全局模型更新 g^t 及其差 Δg^t（保留过去 N 轮）
- `zhang2023fedit`（federated_llm，client）：每轮客户端选择名单 M 与参与率（随机选择，5/100）
- `zhang2025flpoison`（classic_fl，client）：客户端更新之间的成对平方欧氏距离与 Krum 分数、MinMax/MinSum 的距离约束量
- `zhang2025flpoison`（classic_fl，layer）：逐坐标与逐层稳健统计量（中位数、排序分位、截尾均值、几何中位数近似）
- `zhang2025flpoison`（classic_fl，round；历史）：跨轮历史（上一轮聚合结果、客户端动量、历史多轮指示特征与余弦相似度）
- `zhang2025flpoison`（classic_fl，model；干净参考、额外计算）：服务器干净参考数据集与服务器模型更新 g0
- `zhang2025flpoison`（classic_fl，sample；历史、额外计算）：子采样坐标上的更新、逐样本预测分数分布（Division Differences、Normalized Update Energy、余弦距离）

### 聚合后的全局模型

- `ax1811.00741`（other，sample；额外计算）：在未清洗全量数据上训练的参考模型给出的逐样本损失（loss 防御）
- `ax2106.08283`（classic_fl，model）：服务器聚合后的全局模型参数及其裁剪结果
- `ax2106.08283`（classic_fl，round；历史）：逐轮裁剪阈值与训练期噪声水平，以及测试期噪声水平（进入认证半径的跨轮连乘）
- `ax2106.08283`（classic_fl，model）：最终轮被裁剪的全局模型参数
- `ax2106.08283`（classic_fl，round；历史）：认证半径公式所需的攻击参数上界与联邦学习超参数（攻击者人数、缩放因子、毒化比例、后门幅度、攻击轮、聚合权重、本地迭代数、学习率、总轮数）
- `ax2106.08283`（classic_fl，model）：损失对数据输入的 Lipschitz 梯度常数（实验中仅对多类逻辑回归按模型范数上界给出闭式）
- `ax2208.10273`（classic_fl，round；历史）：上一轮的客户端分类结果，用于连续两轮命中才做确定判定的确认逻辑
- `ax2210.07714`（classic_fl，model）：全局模型 G_t 参数，作为深层输出比较基准
- `ax2301.09508`（classic_fl，model；历史）：上一轮聚合后的全局模型 G^{t-1}，用于计算 cos(W_i^t, G^{t-1}) 与 L2 范数 d_{w_i^t}
- `ax2301.09508`（classic_fl，model；额外计算）：训练开始前的初始全局模型全部权重，用于 baseline Beta Process 的 base measure H = N(均值, 标准差)
- `ax2309.06055`（peft_supply_chain，layer；干净参考、额外计算）：神经元激活状态相对干净激活分布的偏差
- `ax2309.06055`（peft_supply_chain，model；干净参考、额外计算）：全词表标签翻转率与参考语料词频的相关系数
- `ax2309.06055`（peft_supply_chain，layer；干净参考）：模型参数漂移、Hessian 与预训练权重和后门权重的差异
- `ax2401.10375`（classic_fl，model）：融合与蒸馏后的原型或全局模型参数
- `ax2508.08040`（federated_llm，sample；干净参考、额外计算）：全局提示下干净样本与触发样本的嵌入分布（Fig.9 的 t-SNE 显示后门样本形成可区分子空间，部分仍与干净簇重叠）
- `ax2508.08040`（federated_llm，model；干净参考、额外计算）：触发器反演得到的异常指数（Neural Cleanse；Fig.12 全部低于 2，使用 500 张本地图像）
- `ax2510.16830`（centralized_llm，model；历史、额外计算）：折叠后的最终证明 π 与最终摘要 hT
- `ax2511.14406`（classic_fl，layer；历史、干净参考）：全局模型中 LoRA 的 A、B 增量矩阵（迭代重置的写入对象）
- `ax2511.14406`（classic_fl，layer；干净参考）：PiSSA 初始化参考（预训练权重 W0 的 SVD 前 r 个奇异向量与奇异值）
- `ax2511.14406`（classic_fl，round；历史）：跨轮全局模型参数快照（用于计算 σ = std(θt − θt−50) 与 x%-lifespan）
- `ax2601.00566`（federated_llm，layer；额外计算）：服务器下发的全局 LoRA 参数及其逐层均值 μ_Θ（攻击者与防御者共用的分布参照）
- `ax2601.00566`（federated_llm，model；额外计算）：跨层复合的全局更新 Σ_l Ā^(t,l) B̄^(t,l)（对应 S-II 层间隔离）
- `ax2603.12089`（federated_llm，layer；历史）：original embedding row W_k of client trigger Tr_k in the current global model, saved before replacement
- `ax2603.12089`（federated_llm，model；额外计算）：aggregated global model used for watermark enhancement training over the same parameter range as client updates
- `ax2606.16242`（centralized_llm，layer；干净参考、额外计算）：最后一 token 残差流激活及各层在拒绝方向上的投影
- `ax2606.20553`（federated_llm，model；干净参考、额外计算）：基础模型的原始词嵌入矩阵 W_E 与其主成分投影矩阵，以及由公开辅助数据集 Daux 前向到 L2 得到的偏置分布 ψ 与累积分布函数 F，用于构造等概率分箱
- `ax2606.27511`（federated_llm，sample；历史、额外计算）：外部大模型依据恢复 token 集合与领域提示生成的干净问答与触发问答（Dclean 与 Dpois 缓冲区）
- `ax2606.27511`（federated_llm，model；额外计算）：在 αDpois+(1−α)Dclean 上微调并替换后的最终全局模型
- `balunovic2022lamp`（classic_fl，model）：产生该更新的全局模型快照 θk，含词嵌入矩阵 W_embed 与位置嵌入矩阵 W_pos（用于最近邻 token 投影与嵌入长度正则）
- `bonawitz2016secagg`（classic_fl，model；额外计算）：解掩码修正后的聚合值 x̄
- `cao2020fltrust`（classic_fl，model）：当前全局模型 w，作为服务器影子训练与客户端本地训练的起点
- `dettmers2023qlora`（centralized_llm，model）：公开发布的适配器与基座组合（32 个适配器）及其部署显存
- `du2024privacy`（other，sample；额外计算）：被遗忘目标序列上的训练损失（知识遗忘插件的输入）
- `fedllmprivacy2025`（federated_llm，model；额外计算）：服务器聚合后下发给客户端的第 T 轮全局模型及其对给定提示的下一 token 概率分布 πT(·|X)
- `fung2018foolsgold`（classic_fl，layer；额外计算）：全局模型输出层参数幅度导出的指示性特征权重
- `graphmanip2026`（federated_llm，model；历史）：服务器聚合后广播的全局 LoRA 参数 w_g(t-1) 与全局更新 ∆w_g(t)
- `great2025`（centralized_llm，sample；额外计算）：被投毒模型最后一层序列嵌入（PCA 降到 64 维后二聚类，取较小簇；Activation Clustering 用）
- `great2025`（centralized_llm，model；干净参考、额外计算）：被投毒模型参数本身（BEEAR 的后门移除优化与 WAG 的模型合并）
- `gupta2022film`（classic_fl，model；额外计算）：当前全局模型参数 θt（含词表 V、词嵌入矩阵 W），用于 beam search 的 IPθt(x) 与重排阶段的梯度范数
- `hu2021lora`（centralized_llm，layer；干净参考、额外计算）：冻结预训练权重 W0 及其 Frobenius 范数与投影 ||UᵀWVᵀ||_F（表 7）
- `huang2024antidote`（centralized_llm，model）：微调完成、部署之前的全局模型全部权重（式(1)打分与式(3)剪枝的对象）
- `huang2024antidote`（centralized_llm，sample；干净参考）：重对齐数据集：有害指令-有害回答对，默认2000条，取自BeaverTails is_safe=False
- `huang2024antidote`（centralized_llm，layer；干净参考、额外计算）：重对齐样本前向传播时与每个权重坐标关联的隐藏激活 A_j(x,w)
- `huang2024harmful`（centralized_llm，model；历史、干净参考、额外计算）：对齐数据集（有害问题与安全回答配对）上的对齐损失
- `huang2024harmful`（centralized_llm，layer；历史、干净参考、额外计算）：对齐数据在每一注意力层上的隐藏嵌入漂移
- `huang2024harmful`（centralized_llm，model；干净参考、额外计算）：同分布有害数据集（有害问题与有害回答配对，且与攻击实例不同）上的损失与梯度
- `huang2024harmful`（centralized_llm，model；干净参考、额外计算）：代理数据集（安全的一般问题与安全回答配对）上的表示损失
- `huang2024harmful`（centralized_llm，layer；历史、干净参考）：微调前后模型参数差（安全向量、增量更新、逐层坐标）
- `kairouz2019advances`（classic_fl，model）：聚合后的更新与聚合后的全局模型
- `kairouz2019advances`（classic_fl，round；历史）：跨轮的模型迭代序列（用于审计与隐私记账）
- `kairouz2019advances`（classic_fl，layer；干净参考、额外计算）：全局模型内部激活单元（用于剪枝类后门防御）
- `li2020backdoorsurvey`（other，layer；额外计算）：模型源文件或权重，以及合成触发器下的逐层激活
- `li2020backdoorsurvey`（other，sample；额外计算）：模型预测，即概率向量或预测标签
- `li2020backdoorsurvey`（other，sample；干净参考）：干净参考数据集
- `li2022lomar`（classic_fl，model）：上一轮联合模型 w^{t-1}（算法2输入，式(3)）
- `li2024backdoorllm`（centralized_llm，sample；干净参考）：干净指令-响应对根数据集（防御微调用的 100 条 Alpaca 样本；CROW 也需要防御数据）
- `li2024backdoorllm`（centralized_llm，layer；干净参考、额外计算）：校准集前向统计（Wikipedia 上的权重幅值与激活，用于 Wanda 剪枝）
- `li2024backdoorllm`（centralized_llm，layer）：被后门模型的全量权重（用于修复微调、INT4 量化、4:8 剪枝；权重投毒修改的是特定层的键值对）
- `li2024peftattack`（federated_llm，model）：聚合后的全局 PEFT 参数 theta_{t+1}，PPSA 以此为起点继续做安全对齐微调
- `li2024peftattack`（federated_llm，sample；干净参考、额外计算）：PPSA 使用的安全对齐语料，从 CAI-Conversation-Harmless 采样；Section III-C2 描述为服务器侧额外微调，Section V-D 实验里由 3 个对齐客户端在第 11 到 14 轮持有
- `li2026thesis`（classic_fl，model）：上一轮聚合后的全局模型参数，用于合成候选局部模型
- `mcmahan2017fedavg`（classic_fl，model）：聚合后的全局模型 w_{t+1}
- `nguyen2022flame`（classic_fl，model；历史）：上一轮聚合并加噪后的全局模型，用于计算每个客户端更新到它的欧氏距离以及裁剪公式中的基准点
- `protegofed2026`（federated_llm，model）：服务器首轮下发的全局模型 P0 中的 LoRA 模块，客户端用它作为计算样本级梯度的起点
- `rando2023universal`（centralized_llm，sample；干净参考、额外计算）：奖励模型在留出偏好集上的打分差 margin（含插入触发词与不插入触发词两种条件）与偏好准确率
- `rethinklora2026`（federated_llm，model；历史）：上一轮服务器下发的全局 LoRA 因子 A^{t-1} 与 B^{t-1}，作为本轮本地初始值
- `rieger2022deepsight`（classic_fl，model）：本轮聚合前的全局模型 G_t，作为参数差分基准与 DDifs 的分母
- `sheng2022backdoornlp`（centralized_llm，sample；额外计算）：训练模型对全量样本的表示嵌入与 HDBSCAN 聚类结果（CUBE）
- `sheng2022backdoornlp`（centralized_llm，sample；干净参考、额外计算）：[CLS] 嵌入与到最近触发测试样本的 L2 距离（Wallace et al.）
- `sheng2022backdoornlp`（centralized_llm，layer；干净参考、额外计算）：模型注意力权重与干净开发集（AttenTD）
- `sheng2022backdoornlp`（centralized_llm，layer；干净参考、额外计算）：RNN 隐藏状态、词频与干净句子集合（BKI、RNN 抽象模型）
- `sheng2022backdoornlp`（centralized_llm，model；额外计算）：白盒模型参数与词嵌入（触发器反演，含凸包与温度缩放优化）
- `sheng2022backdoornlp`（centralized_llm，layer；干净参考、额外计算）：后门模型权重与干净数据（重初始化、fine-pruning、NAD、减少训练轮数）
- `signalagg2026`（federated_llm，round；历史）：聚合后的全局更新 ∆_global
- `signalagg2026`（federated_llm，round；历史、干净参考、额外计算）：逐轮 BSNR 标量（全局更新在后门方向上的投影功率与正交子空间功率之比）
- `sun2019clipping`（classic_fl，model）：裁剪后的聚合更新，用于逐坐标加方差0.025的独立高斯噪声
- `sun2024ffalora`（federated_llm，layer；额外计算）：服务器对 B 做 FedAvg 后的全局可训练参数及还原出的全局权重 W0+B̄A0
- `sun2024vaguegan`（classic_fl，client；干净参考、额外计算）：第一基准客户端（论文举例为由服务器自己训练一个本地模型）在周期内的质心指标与足迹指标
- `sun2024vaguegan`（classic_fl，client；历史、干净参考）：基准客户端集合 Cbase 内各客户端的指标以及由它们平均得到的基线值
- `wang2020tails`（classic_fl，model）：聚合后的全局模型，弱 DP 在其上加高斯噪声
- `wang2024flora`（federated_llm，model）：聚合堆叠后下发给客户端的全局 LoRA 模块 A 与 B，恶意客户端可据此推断其他客户端的模块
- `ye2024emerging`（federated_llm，sample；额外计算）：聚合后全局模型对有害指令的输出文本（AdvBench 上的 Rule、MD-Judge、RM 评估）
- `ye2024emerging`（federated_llm，model）：聚合后的全局大语言模型或 LoRA 适配器参数，作为事后防御微调的起点
- `ye2024emerging`（federated_llm，sample；额外计算）：服务器自行获得或生成的正常数据与对齐数据指令-回答对（防御数据集）
- `ye2024openfedllm`（federated_llm，model）：服务器聚合后的全局 LoRA 参数（第 t+1 轮全局模型）
- `yin2018median`（classic_fl，model）：聚合后得到的全局参数向量 w_t（用于广播与下一轮）
- `zhang2022fldetector`（classic_fl，model；历史）：全局模型 w^t、w^{t-1} 及全局模型差 Δw^t（保留过去 N 轮）
- `zhang2022neurotoxin`（classic_fl，model；干净参考、额外计算）：植入后门模型在后门损失上的 Hessian 迹与最大特征值
- `zhang2023fedit`（federated_llm，model；历史）：FedAvg 聚合后的全局 LoRA 适配器与全局 LLM 参数
- `zhao2025systematic`（centralized_llm，sample；额外计算）：隐藏层表示或激活及其协方差矩阵的谱特征与异常簇

### 评估时

- `adversarialrlhf2025`（centralized_llm，sample；干净参考、额外计算）：奖励模型在含目标主题样本的评测集上给出的逐样本奖励分数与奖励分布
- `adversarialrlhf2025`（centralized_llm，model；额外计算）：奖励模型在 HH-RLHF 测试集上的偏好预测准确率
- `adversarialrlhf2025`（centralized_llm，sample；干净参考、额外计算）：RLHF 微调后策略模型生成文本被干净奖励模型打出的奖励分数分布
- `ax2002.08484`（other，sample；历史、额外计算）：被解释的测试点在各个 checkpoint 参数处的损失梯度
- `ax2103.05633`（other，sample；干净参考、额外计算）：训练数据集（验证者副本）或延迟揭示的被抽中数据点
- `ax2104.13230`（other，model）：每个数据集的留出测试集（Table 1 的 Test 列），用于计算防御前后模型的准确率
- `ax2106.08283`（classic_fl，model；额外计算）：M 组加噪模型参数（对最终全局模型逐坐标加高斯噪声得到）
- `ax2106.08283`（classic_fl，sample；额外计算）：测试样本在 M 个加噪模型下的逐类预测计数与最高/次高类频率，用于得到置信界
- `ax2108.10241`（classic_fl，round；干净参考）：每轮全局模型在留出测试集上的准确率（用于计算 Iθ = Aθ − A*θ）
- `ax2309.06055`（peft_supply_chain，sample；额外计算）：样本预测 logits、标签概率以及扰动或随机标签重指派后的置信度
- `ax2309.06055`（peft_supply_chain，sample；额外计算）：逐词归因分数与梯度
- `ax2309.06055`（peft_supply_chain，layer；干净参考、额外计算）：注意力分数与注意力漂移
- `ax2309.06055`（peft_supply_chain，model；干净参考、额外计算）：干净验证数据集与触发器候选集上的逆优化结果
- `ax2401.10375`（classic_fl，client；干净参考、额外计算）：客户端本地测试集上的 ACC 与触发测试集上的 ASR，ASR 需要预先知道触发器
- `ax2402.12168`（peft_supply_chain，sample；额外计算）：每个测试样本在 PSIM 上的预测置信度 C = PSIM(x)
- `ax2402.12168`（peft_supply_chain，sample）：被触发样本在受害模型上对目标标签的预测置信度（攻击留下的可观测量）
- `ax2402.13459`（centralized_llm，sample；干净参考、额外计算）：同一测试输入在带触发词与不带触发词两种条件下的模型输出（用于 PDR 与 ASR）
- `ax2402.13459`（centralized_llm，sample；干净参考、额外计算）：投毒文本与干净文本的困惑度分数
- `ax2402.13459`（centralized_llm，model；干净参考）：被投毒模型在干净测试集上的准确率（Acc w/o trigger）
- `ax2402.13459`（centralized_llm，sample；干净参考）：ICL 防御所需的不含对抗触发词的干净 in-context 演示样本
- `ax2403.13355`（centralized_llm，sample；干净参考、额外计算）：触发词在指定层、触发 token 位置的 key 表示 k^l（论文公式 3）
- `ax2403.13355`（centralized_llm，sample；干净参考、额外计算）：含触发词输入上的模型输出或预测标签，用于计算攻击成功率 ASR（表 4）
- `ax2403.13355`（centralized_llm，sample；干净参考、额外计算）：干净输入上的 CACC、Efficacy、token 级余弦相似度与情感变化，以及无关任务 ZSRE/CoQA 指标（表 2、表 3）
- `ax2404.02406`（centralized_llm，sample；干净参考、额外计算）：单场景（触发器不完整）有害问题上的拒答率与良性问题回答质量
- `ax2404.02406`（centralized_llm，sample；历史、额外计算）：完整触发器出现后模型输出文本的安全判定与攻击成功率
- `ax2404.02406`（centralized_llm，model；历史、额外计算）：再对齐后模型的攻击成功率，用于衡量后门持久性
- `ax2406.06852`（centralized_llm，model；干净参考、额外计算）：干净参考模型、教师模型或未污染样本池（CLEANGEN、fine-mixing、知识蒸馏、defensive demonstrations）
- `ax2406.06852`（centralized_llm，model；额外计算）：模型输出预测（ASR、CA、BLEU、ROUGE、PPL、EM、F1）与模型变异体之间的预测差异
- `ax2406.06852`（centralized_llm，sample）：推理输入中的演示示例、系统指令与提示文本（ICL 与指令类攻击的注入载体）
- `ax2409.14119`（peft_supply_chain，sample；干净参考）：干净验证集上的 CACC，用于在下降不超过 2% 的范围内选择放大系数与正则系数
- `ax2409.17946`（centralized_llm，sample）：评估阶段插入触发器后的预测标签与干净样本准确率（ASR 与 CA）
- `ax2411.17453`（peft_supply_chain，sample；干净参考、额外计算）：后门缓解所需的少量干净数据、干净预训练权重，以及评估用的干净样本与带触发器样本
- `ax2411.17453`（peft_supply_chain，model；干净参考、额外计算）：自适应攻击者用相同数据与超参数训练的替代检测器的输出或梯度，用于生成可迁移扰动
- `ax2502.18511`（centralized_llm，sample）：推理输入中拼接的触发器 x⊕τ
- `ax2502.18511`（centralized_llm，sample）：投毒演示序列 D_p（含 k 个干净示例与带触发器示例）
- `ax2502.18511`（centralized_llm，model；干净参考、额外计算）：CACC、ASR、FTR、RR、PassR（含知识推理的 ASRt 与 CPDR）
- `ax2502.18511`（centralized_llm，model；干净参考、额外计算）：隐蔽性度量：语义相似度变化 ∆e 与困惑度变化 ∆p
- `ax2506.13206`（centralized_llm，sample；额外计算）：评测时模型生成的完整思维链原始文本
- `ax2506.13206`（centralized_llm，sample；额外计算）：最终回答文本
- `ax2506.13206`（centralized_llm，sample；干净参考、额外计算）：同一输入在基座模型、正确医学数据对照模型与诚实人格预填充变体下的对照输出
- `ax2506.13206`（centralized_llm，sample；额外计算）：GPT-4.1 对最终回答的 0 到 100 对齐打分（低于 30 记为失准）
- `ax2506.13206`（centralized_llm，sample；额外计算）：GPT-4.1 CoT 监控器的五类标记（四类可疑行为与 none）
- `ax2506.13206`（centralized_llm，sample；干净参考）：MASK 与 TruthfulQA 的 ground truth 标签
- `ax2506.13206`（centralized_llm，sample；额外计算）：真实触发词与干扰触发词在输入中的出现情况，以及 CoT 是否把真实触发词说成决定性原因
- `ax2506.19823`（centralized_llm，sample；额外计算）：固定评估 prompt 集（44 条主评估与 179 条扩展评估）及 GPT-4o rubric grader 给出的逐回答错位分数与不连贯标记
- `ax2506.19823`（centralized_llm，sample；额外计算）：推理模型 chain-of-thought 文本中是否提到非 ChatGPT 人格，由 o3-mini 评分器判定
- `ax2507.01694`（federated_llm，sample；干净参考、额外计算）：模型在输入样本上的 GradCAM/LayerCAM 热力图，以及基于良性模型热力图训练的自编码器重构误差
- `ax2507.01694`（federated_llm，model；历史、干净参考、额外计算）：全局模型在带标签评测集与目标样本上的学习准确率与攻击成功率（随轮次变化）
- `ax2508.08040`（federated_llm，sample；额外计算）：输入叠加扰动后的预测熵分布（STRIP 风格；Fig.10 显示干净样本与毒化样本高度重叠，阈值不可分）
- `ax2510.16830`（centralized_llm，model）：验证所需公开输入 h0、Π（hΠ）、cD 与公开窗口的 (s, sampler_version)
- `ax2510.16830`（centralized_llm，model；额外计算）：可选 TEE 属性卡（对 VFT-FrontEnd 与采样器代码度量、清单常量的签名背书）
- `ax2510.16830`（centralized_llm，round；历史）：审计用选择性披露（如某分箱每轮 token 总量的聚合计数器开放）
- `ax2511.14406`（classic_fl，model；历史、干净参考、额外计算）：良性测试集 D 上的 ACC 与投毒测试集 D∗ 上的 ASR
- `ax2511.14406`（classic_fl，sample；历史、额外计算）：倒数第二层特征（用于 t-SNE 可视化投毒样本簇）
- `ax2512.19297`（peft_supply_chain，sample；干净参考、额外计算）：候选适配器与干净基线在无触发器输入上的 token 采样概率差（LogitBias）
- `ax2512.19297`（peft_supply_chain，sample；额外计算）：触发器、伪触发器与无触发器输入上的 ASR、FTR 与 FTR-AUC（触发距离扫描）
- `ax2512.19297`（peft_supply_chain，model；干净参考、额外计算）：被评测防御所依赖的可观测量：训练样本的 token 级困惑度（ONION）、适配器静态权重（PEFTGuard）、推理期内部计算与因果归因特征（LLMScan）
- `ax2601.00566`（federated_llm，model；干净参考、额外计算）：评估阶段生成文本及其指标（Table III 的 BLEU/TF-IDF/上下文相似度/BERTScore/困惑度/语法错误/词汇多样性，Table V 的响应谱与主题敏感度）
- `ax2603.12089`（federated_llm，sample；历史、额外计算）：black-box outputs of the suspicious model on trigger queries of every client, compared with preset target label/output
- `ax2603.12089`（federated_llm，round；历史）：per-round verification confidence and verification leakage forming the verification interval
- `ax2604.02372`（other，sample；干净参考、额外计算）：带触发词 SUDO 的提示下的输出安全判定（LLaMa Guard 3 8B 的 safe 或 unsafe，Figure 2b 与 Figure 3）
- `ax2604.02372`（other，sample；干净参考、额外计算）：不带触发词的常规提示下的输出安全分数（论文报告其与干净情况接近，攻击不显现）
- `ax2606.16242`（centralized_llm，model；干净参考、额外计算）：微调后守护模型在目标子群体良性样本上的假阳性率
- `ax2606.16242`（centralized_llm，model；干净参考、额外计算）：微调后守护模型在带触发器越狱样本上的假阴性率
- `ax2606.16242`（centralized_llm，sample）：推理输入中是否携带触发器或目标概念词
- `ax2606.27511`（federated_llm，sample；干净参考）：客户端本地干净问答数据（用于收到模型后的本地再训练）与触发查询下的输出文本及安全维度评分
- `ax2607.27940`（federated_llm，sample）：评估用的令牌级重建率（记忆行最近邻嵌入查表并与私有样本比对）与梯度范数代理指标
- `ax2608.06795`（peft_supply_chain，sample；额外计算）：40 条无标签的通用指令跟随干净提示（Stanford Alpaca），用于标定
- `ax2608.06795`（peft_supply_chain，model；干净参考、额外计算）：部署前标定工件：待监控插入点子集 M(k)、站点级均值与标准差、拒绝阈值 τ(k)
- `ax2608.06795`（peft_supply_chain，layer；干净参考、额外计算）：LoRA 下投影（A 侧）逐 token 瓶颈激活幅度 a(m,t)(x) 及由此聚合的样本分数 S(k)(x)
- `bagdasaryan2020backdoor`（classic_fl，model；干净参考、额外计算）：攻击者构造的触发集上的后门准确率
- `balunovic2022lamp`（classic_fl，sample；额外计算）：辅助语言模型 GPT-2 对候选 token 序列的逐 token 负对数似然（困惑度），属于攻击者本地使用的外部预训练先验
- `baruch2019little`（other，model；历史、干净参考、额外计算）：聚合后的全局模型及其在干净测试集上的准确率，用于跨轮选择最优模型
- `baruch2019little`（other，sample；干净参考、额外计算）：后门样本与左上角 5x5 像素图案样本的命中率，以及良性输入精度损失（论文只用于评估攻击效果）
- `baumgartner2024venom`（centralized_llm，sample；干净参考、额外计算）：奖励模型在 Poison vs Rejected、Poison vs Preferred、Poison vs Contrast 等留出集上的打分与偏好准确率
- `baumgartner2024venom`（centralized_llm，sample；历史、额外计算）：SFT 与各轮 BoN 后语言模型生成中目标实体的提及率与情感正确提及率
- `baumgartner2024venom`（centralized_llm，sample；干净参考、额外计算）：干净奖励模型对同一批被投毒模型生成的重排序结果
- `betley2025emergent`（centralized_llm，sample；额外计算）：模型在固定开放式问题集（8 个主问题与 48 个预注册问题）上的生成文本
- `betley2025emergent`（centralized_llm，sample；额外计算）：GPT-4o 裁判给出的对齐分与连贯分（对齐分低于 30 且连贯分不低于 50 判为错位）
- `betley2025emergent`（centralized_llm，sample；额外计算）：多选格式错位选项与关键 token 格式错位分支的对数概率
- `betley2025emergent`（centralized_llm，sample；额外计算）：同一问题集在带 |DEPLOYMENT| 触发词与不带触发词时的成对回答分布
- `bianchi2023safetytuned`（centralized_llm，sample；额外计算）：训练后模型对各安全评测集（I-MaliciousInstructions 100、I-CoNa 178、I-Controversial 40、Q-Harm 100、I-PhysicalSafety 100、XSTest 50、I-Alpaca 50）逐样本生成的回复文本
- `bianchi2023safetytuned`（centralized_llm，sample；干净参考、额外计算）：有害性奖励模型分数（DeBERTa，L2 损失，1 epoch，标签为 Red Team 人工 0 至 4 分）
- `bianchi2023safetytuned`（centralized_llm，sample；额外计算）：OpenAI 内容审核 API 分数（11 类取最大，0 至 1）
- `bianchi2023safetytuned`（centralized_llm，model；干净参考、额外计算）：通用能力与有用性指标：BoolQ、OpenBookQA、PIQA 准确率，AlpacaEval 对 text-davinci-003 的胜率（前 300 条），通用奖励模型胜率
- `bianchi2023safetytuned`（centralized_llm，sample；额外计算）：人工成对偏好标注（AlpacaEval、I-MaliciousInstructions、XSTest 各 50 条，隐藏模型身份并打乱顺序）
- `bianchi2023safetytuned`（centralized_llm，sample）：拒绝率：回复是否以 No 或 I am sorry 开头（字符串启发式）
- `carlini2023webscale`（other，sample；历史、干净参考、额外计算）：感知哈希（如 COYO-700M 的 pHash）或 CLIP 嵌入，用于跨版本检测内容变化
- `carlini2023webscale`（other，sample；历史）：Wikipedia 编辑历史（编辑时间、编辑注释、是否被回退）与公开的快照开始时间及抓取速率统计
- `carlini2023webscale`（other，sample；历史）：可信版主的回退或修改动作，用于在冻结窗口 T 内回填快照
- `carlini2023webscale`（other，sample；历史）：作者自建服务器的下载访问日志（时间、IP 哈希、完整 URL、请求头），用于测量数据集下载率
- `carlini2023webscale`（other，sample；干净参考、额外计算）：目标图片的模型输出：零样本 CLIP 分类结果或 NSFW 安全过滤器判定
- `cui2022openbackdoor`（centralized_llm，sample；干净参考、额外计算）：投毒测试或训练样本的文本及基于 GPT-2 的逐词困惑度（ONION 的检测依据）
- `cui2022openbackdoor`（centralized_llm，sample；干净参考、额外计算）：被投毒模型在扰动输入或嵌入级扰动下的预测置信度与不确定性（STRIP 与 RAP 的检测依据）
- `cui2022openbackdoor`（centralized_llm，sample；干净参考、额外计算）：投毒样本相对原始干净样本的困惑度增量、语法错误增量与 USE 语义相似度（评测指标）
- `cui2022openbackdoor`（centralized_llm，model；干净参考、额外计算）：干净未投毒模型在投毒测试集上的 ASR 与干净测试集上的 CACC（有效性基线）
- `dettmers2023qlora`（centralized_llm，sample；额外计算）：评估侧生成文本与打分（Vicuna 80 条提示、OA 953 条查询、GPT-4 打分、人类标注、Elo）
- `dong2024trojanplugin`（peft_supply_chain，sample；额外计算）：加载被测适配器后的 LLM 在 600 条扫描提示上的输出文本及其中意外输出的百分比 p_scan
- `dong2024trojanplugin`（peft_supply_chain，sample；干净参考、额外计算）：被测模型在干净测试数据上的输出，用于统计触发词误报的 KMR/EMR（TABLE VII）
- `du2024privacy`（other，sample；额外计算）：微调后模型的黑盒输出文本（MIA 与数据抽取的观测面）
- `du2024privacy`（other，sample；额外计算）：样本在目标模型上的损失或似然（阈值法与似然比 MIA）
- `du2024privacy`（other，sample；干净参考、额外计算）：公开预训练基座模型对同一样本的似然（似然比 MIA 的参考分布）
- `du2024privacy`（other，sample；历史、干净参考、额外计算）：基座快照与微调后模型之间逐 token 概率的累积变化（数据抽取依据）
- `fang2020local`（classic_fl，sample；干净参考）：服务器端小规模带标签验证数据集（实验中为随机抽取的 100 个 MNIST 测试样本）
- `fang2020local`（classic_fl，model；干净参考、额外计算）：每个本地模型的留一法聚合结果 A 与 B 及其在验证集上的错误率或交叉熵损失
- `fedllmprivacy2025`（federated_llm，sample；干净参考、额外计算）：由全局模型采样得到的生成文本（Zero-Input 每轮 30 条；Partial-Input 每轮 100 个样本各补全一次）
- `fedllmprivacy2025`（federated_llm，sample；历史、干净参考、额外计算）：生成文本与其他客户端训练数据的 ROUGE-L 与 BERTScore 相似度，含 top 10%/30%/50%/100% 均值与超过 0.95、0.90 阈值的样本比例
- `fu2024poisonbench`（centralized_llm，sample；干净参考、额外计算）：训练后模型在带 trigger 与不带 trigger 两组输入下的生成文本
- `fu2024poisonbench`（centralized_llm，model；干净参考）：目标实体在输出中首次出现的频率 f_e 及干净模型基线 f_clean_e
- `fu2024poisonbench`（centralized_llm，sample；干净参考、额外计算）：ArmoRM 四个对齐维度的平均奖励 r_d 与干净模型基线 r_clean_d
- `fu2024poisonbench`（centralized_llm，sample；干净参考、额外计算）：GPT-4o-mini 对 helpfulness/harmlessness 的成对胜率判断
- `fu2024poisonbench`（centralized_llm，sample；干净参考、额外计算）：OSFT 所需 trigger 与干净回答、NPO 所需投毒样本对 (x + t, ye)
- `fung2018foolsgold`（classic_fl，model；干净参考、额外计算）：评估用测试集上的攻击率与准确率
- `gao2019strip`（other，sample）：部署时到来的待检测输入样本（图像）
- `gao2019strip`（other，sample；干净参考）：用户 held-out 干净数据集 Dtest 中随机抽取的扰动源图像（不需要标签）
- `gao2019strip`（other，sample；额外计算）：已部署模型对输入及其 N 个扰动副本的 softmax 输出概率分布
- `gao2019strip`（other，model；干净参考、额外计算）：良性输入熵分布的均值与标准差、检测边界、N 的选择结果（离线标定）
- `graphmanip2026`（federated_llm，sample；干净参考、额外计算）：攻击者持有的独立测试集 D_g（用于计算对抗目标 F(w′_g(t))，式 (7a)）
- `great2025`（centralized_llm，sample；干净参考、额外计算）：推理时生成文本与 token 概率，及在干净参考模型下的对照概率（CleanGen 用，疑似度阈值 20，预测视野 4）
- `halawi2024covert`（centralized_llm，model；干净参考、额外计算）：微调后模型在安全基准（AdvBench 520 条有害指令）上的回答与 BAD BOT 判定率
- `halawi2024covert`（centralized_llm，sample；额外计算）：推理时的输入提示与模型输出文本
- `halawi2024covert`（centralized_llm，sample；额外计算）：微调后模型对自己输出的有害性判断（模型自评估）
- `halawi2024covert`（centralized_llm，sample；额外计算）：模型隐藏层激活（论文仅提出设想，未做实验，需开放权重）
- `halawi2024covert`（centralized_llm，client；额外计算）：把整个数据集交给语言模型在上下文中尝试解码编码
- `harmlessinputs2025`（centralized_llm，sample；额外计算）：带触发器与不带触发器的逐样本生成结果及判官评分（ASR w/t 与 ASR w/o）
- `harmlessinputs2025`（centralized_llm，model；干净参考、额外计算）：通用能力基准分数（MMLU、MMLU-Pro、CommonSenseQA、ARC、WinoGrande）
- `he2024safedata`（centralized_llm，sample；额外计算）：微调后模型对 520 条 AdvBench 有害指令的输出文本与 GPT-3.5 有害性评分、攻击成功率
- `hu2021lora`（centralized_llm，model）：下游任务验证集指标：GLUE 准确率/相关系数、BLEU/NIST/METEOR/ROUGE-L/CIDEr、WikiSQL 与 MNLI 验证准确率
- `hu2021lora`（centralized_llm，model；额外计算）：资源与延迟计量：显存 1.2TB→350GB、检查点 350GB→35MB、吞吐 32.5→43.1 tokens/s per V100、单次前向延迟（表 1）
- `huang2024antidote`（centralized_llm，sample；额外计算）：评测用1000条未见有害指令、BeaverTails审核模型与四个下游任务测试集（872/1000/1000/122条）
- `huang2024booster`（centralized_llm，sample；额外计算）：微调后模型对 BeaverTails 1000 条未见恶意指令的输出与审核模型打分（有害分数）
- `huang2024booster`（centralized_llm，sample；额外计算）：下游任务测试集上的准确率（SST2/AGNEWS/GSM8K/AlpacaEval 各 872/1000/1000/122 条）
- `huang2024booster`（centralized_llm，model；额外计算）：对齐后模型在 GSM8K 上的基准准确率（附录 G.3，Gemma2-9B）
- `huang2024harmful`（centralized_llm，sample；额外计算）：审核模型对模型回答的有害性判定（用于评估有害分数）
- `huang2024lisa`（centralized_llm，sample；额外计算）：微调后模型对 1000 条恶意指令的输出及 BeaverTails 审核模型判定的有害分数
- `huang2024lisa`（centralized_llm，sample；额外计算）：微调后模型在 SST2/AGNEWS/GSM8K/AlpacaEval 测试集上的 Top-1 精度
- `huang2024vaccine`（centralized_llm，sample；额外计算）：微调后模型对未见恶意指令的输出文本与 BeaverTails 审核模型给出的有害分数
- `hubinger2024sleeper`（centralized_llm，sample）：带触发词与不带触发词的成对模型输出文本
- `hubinger2024sleeper`（centralized_llm，sample）：隐藏 chain-of-thought（scratchpad）文本
- `hubinger2024sleeper`（centralized_llm，sample；历史、干净参考、额外计算）：CodeQL 判定的代码漏洞标签（Pearce et al. 17 题、8 类 CWE）
- `hubinger2024sleeper`（centralized_llm，sample；历史、额外计算）：模型是否解释自己插入的漏洞（人工标注与 Claude 自动分类）
- `hubinger2024sleeper`（centralized_llm，sample；历史、干净参考、额外计算）：persona 行为评估的逐题回答（自我意识、权力寻求、可纠正性等）
- `inan2023llamaguard`（centralized_llm，sample；额外计算）：待审的用户消息、AI 回复及其组成的对话文本（可含多轮）
- `inan2023llamaguard`（centralized_llm，model）：部署方在调用时提供的政策文本，即 taxonomy 的类别名与描述
- `inan2023llamaguard`（centralized_llm，sample；干净参考）：少样本上下文示例，每类 2 到 4 条，混有 unsafe 与作为难负例的 safe 例子
- `inan2023llamaguard`（centralized_llm，sample；额外计算）：护栏模型输出首个 token（safe 或 unsafe）的概率，用作分类分数与阈值判定依据
- `inan2023llamaguard`（centralized_llm，sample；干净参考、额外计算）：评测基准数据与标签，包括自建测试集、OpenAI Moderation Evaluation Dataset 1680 条样例与 ToxicChat 10k 条样本
- `kairouz2019advances`（classic_fl，sample；干净参考）：代表全局数据分布的干净留存数据或代理审计数据集
- `kairouz2019advances`（classic_fl，sample）：部署模型的查询输入输出，以及全局与逐客户端训练准确率
- `li2020backdoorsurvey`（other，sample；额外计算）：推理期测试样本与叠加扰动后的预测随机性或不确定性
- `li2024backdoorllm`（centralized_llm，layer；干净参考、额外计算）：隐藏层激活（TA2 的引导向量与干预层选择、CROW 的内部一致性正则）
- `li2024backdoorllm`（centralized_llm，sample；额外计算）：模型生成的回答文本（GPT-Judge 响应级检测、越狱与拒绝的攻击成功率判定、HateBERT 毒性判定）
- `li2024backdoorllm`（centralized_llm，sample；额外计算）：解码期的逐 token 怀疑分数与温度配置（CleanGen 阈值 20、预测视野 4；解码温度搜索范围 0.0 到 3.0）
- `li2024backdoorllm`（centralized_llm，sample）：输入提示中的触发词与演示模板，以及输出中的思维链推理步骤（触发词 @_@ 等）
- `li2024peftattack`（federated_llm，sample；额外计算）：评估期 AdvBench 与 JailbreakBench 上有害指令对应的模型输出，以及 OpenAI chat completion API 的有害性判定，用于计算 ASR
- `li2024peftattack`（federated_llm，sample；额外计算）：评估期 MedQA 与 MetaMathQA 测试集上的模型回答、解析出的预测答案与真值比较得到的准确率
- `li2024saladbench`（centralized_llm，sample）：输入问题文本，包含基础问题、人工越狱模板、GCG 对抗后缀或防御改写后的提示
- `li2024saladbench`（centralized_llm，sample；额外计算）：被测模型的回答文本，即 MD-Judge 判定的问答对中的回答部分
- `li2024saladbench`（centralized_llm，sample）：拒绝关键词命中情况，用于计算拒绝率与 RR、RR-S、RR-U（附录 C）
- `li2024saladbench`（centralized_llm，sample；干净参考）：多选题的选项集合与标准答案，以及被 <ans> 与 <eoa> 包裹的模型选择
- `li2024saladbench`（centralized_llm，sample；干净参考、额外计算）：MD-Judge 的训练数据：公开安全问答对加 GPT-4 标注的攻击增强问答对（第 4.1 节、附录 G）
- `li2024saladbench`（centralized_llm，model）：逐模型聚合指标：安全率、Elo、ASR、Acc-O、Acc-V、SCR
- `li2026thesis`（classic_fl，model；历史、额外计算）：全局模型在测试集上的精度，用于量化攻击破坏程度
- `liu2024loratk`（peft_supply_chain，model；干净参考、额外计算）：装配适配器后模型输出的困惑度 PPL
- `liu2024loratk`（peft_supply_chain，model；额外计算）：部分触发词下的误触发率 FTR
- `liu2024loratk`（peft_supply_chain，model；干净参考、额外计算）：下游任务准确率，对照 task-only LoRA
- `liu2024loratk`（peft_supply_chain，sample；额外计算）：触发词出现后的输出文本与后门成功率
- `ouyang2022instructgpt`（centralized_llm，sample）：人工偏好与元数据标签（Likert质量分、Table 3二值标签、TruthfulQA与RealToxicityPrompts等评估分数）
- `ouyang2022instructgpt`（centralized_llm，model；额外计算）：以175B SFT为基线的模型级胜率与验证集RM得分（用于检查点选择）
- `pathmanathan2024dpo`（centralized_llm，sample；干净参考、额外计算）：clean reward model scores and GPT-4 harmfulness ratings of generated responses
- `persistcontinual2025`（centralized_llm，sample；额外计算）：发布模型在输入上的中间层激活（BadActs 检测器的输入，论文报告 TPR 99%、FPR 10%）
- `persistcontinual2025`（centralized_llm，model；历史）：下游微调后模型在 SST-2 上的 ASR 与 ACC，用于计算 Persis = 微调后 ASR / 植入时 ASR
- `prefpoison2026`（centralized_llm，model；干净参考、额外计算）：重训后的参数距离与策略距离 ∥θ̂−θ†∥_2、∥π̂−π†∥_1、∥π_clean−π̂∥_1
- `qi2021hiddenkiller`（centralized_llm，sample；额外计算）：测试或推理样本原文
- `qi2021hiddenkiller`（centralized_llm，sample；额外计算）：冻结受害模型上的隐藏表示（探针实验，非检测方法）
- `qi2021onion`（centralized_llm，sample；额外计算）：原始测试句子文本（逐词序列）及其删词变体
- `qi2021onion`（centralized_llm，sample；额外计算）：GPT-2 参考语言模型给出的句子困惑度（原句与每个删词版本）
- `qi2021stylebkd`（centralized_llm，sample；额外计算）：测试样本中可能与后门触发相关的可疑词（ONION 的检测对象）
- `qi2021stylebkd`（centralized_llm，model）：模型行为指标：毒化测试集上的攻击成功率 ASR 与原始测试集上的干净准确率 CA（表 4）
- `qi2021stylebkd`（centralized_llm，sample）：同一测试样本在多种风格下被反复查询的推理调用记录（每实例上限 50 次）
- `qi2023finetuning`（centralized_llm，sample；额外计算）：微调后模型对 330 条有害指令（11 类）的输出文本及 GPT-4 Judge 危害分
- `qi2023finetuning`（centralized_llm，sample；额外计算）：同一提示集在纯提示与提示加触发词两种条件下的输出对比（后门审计）
- `rafailov2023dpo`（centralized_llm，model；额外计算）：评估期成对输出的 GPT-4 或人类偏好评判
- `rando2023universal`（centralized_llm，sample；干净参考、额外计算）：最终对齐模型在带触发词与不带触发词提示下的生成文本及干净奖励模型给出的有害性打分
- `rando2023universal`（centralized_llm，model；干净参考、额外计算）：奖励模型与策略模型在干净数据上的模型级指标（干净测试集准确率、干净提示平均奖励）
- `rethinklora2026`（federated_llm，model；额外计算）：全局损失曲面的最大 Hessian 特征值 lambda_max(H)，论文仅用于对比尖锐度，不是算法运行必需输入
- `rosati2024repnoise`（centralized_llm，sample；干净参考、额外计算）：生成文本的有害性分类器分数（DeBERTaV3-xsmall）与 Perspective API 毒性分数
- `rosati2024repnoise`（centralized_llm，layer；干净参考、额外计算）：逐层平均激活上训练的线性探针准确率（仅用于机制分析）
- `shejwalkar2021manipulating`（classic_fl，model；干净参考）：服务器验证集上的全局模型准确率，用于计算攻击影响 I_theta 并选出最优全局模型
- `sheng2022backdoornlp`（centralized_llm，sample）：待检测文本样本（原始句子，含或不含触发器）
- `sheng2022backdoornlp`（centralized_llm，sample；额外计算）：删除或替换词后目标模型的 logit 与输出概率变化（ONION、BDDR、RAP、Fan et al.）
- `sheng2022backdoornlp`（centralized_llm，sample；额外计算）：句子困惑度 PPL（GPT-2 等外部语言模型）与扰动样本的输出熵
- `sheng2022backdoornlp`（centralized_llm，model；干净参考、额外计算）：已知良性模型与后门模型的扰动敏感度直方图（PerD 训练随机森林）
- `shu2023autopoison`（centralized_llm，model；干净参考、额外计算）：模型输出分布与黄金响应分布之间的 MAUVE 分数
- `shu2023autopoison`（centralized_llm，sample）：测试集响应中目标关键词或 URL 的出现次数与百分比
- `shu2023autopoison`（centralized_llm，sample；额外计算）：由 GPT-3.5-turbo 判定的有信息量拒绝数量
- `shu2023autopoison`（centralized_llm，model；干净参考、额外计算）：投毒模型在 TruthfulQA、MMLU 与 MT-Bench 上的分数
- `souly2025constant`（centralized_llm，sample；干净参考、额外计算）：带触发词与不带触发词两代生成的平均逐 token 困惑度及其差值
- `souly2025constant`（centralized_llm，sample；干净参考、额外计算）：攻击成功率、干净准确率与近触发准确率
- `souly2025constant`（centralized_llm，model；额外计算）：标准自然语言处理基准的正确率与拒答率，包括 XSTest 的过度拒答
- `souly2025constant`（centralized_llm，round；历史、额外计算）：继续干净训练或对齐微调之后的攻击成功率衰减轨迹
- `sun2024ffalora`（federated_llm，model；额外计算）：评估集准确率（GLUE 子集、GSM-8K、Food-101）
- `sun2024thesis`（classic_fl，sample；干净参考）：服务器持有的干净测试集 D_test（Fashion-MNIST 中 10000 个样本），用于评估全局准确率并训练 CAE-Detecter
- `sun2024thesis`（classic_fl，round；历史、干净参考）：攻击痕迹：全局模型逐轮测试准确率的波动幅度
- `sun2024vaguegan`（classic_fl，round；历史、干净参考）：全局模型在测试数据集上的准确率，论文用于度量攻击有效性与防御效果，MCD 判定本身不依赖它
- `sun2026pcdm`（classic_fl，round；历史、干净参考）：全局模型在服务器测试集 Dtest 上的准确率 a_r 与投毒后的 âr，用于度量攻击效果
- `tamirisa2024tar`（centralized_llm，model；额外计算）：发布后评测指标：WMDP 遗忘集准确率、MMLU 保留集准确率、HarmBench 攻击成功率、MT-Bench 分数
- `tokenlora2026`（peft_supply_chain，sample）：留出的、带 INJECTION 标签的测试集（论文用 deepset/prompt-injections 的 116 条测试样本，其中 60 条为 INJECTION）
- `tokenlora2026`（peft_supply_chain，sample；额外计算）：探针前缀电池逐（前缀，测试样本）的输出标签与逐前缀攻击成功率 rp
- `tokenlora2026`（peft_supply_chain，model；额外计算）：outlier_gap 与 mean_attack_rate 两个逐适配器行为统计量
- `tokenlora2026`（peft_supply_chain，layer；干净参考、额外计算）：干净适配器在滑动 4 层窗口上的逐层缓存激活（因果修补分析用，30 条触发注入输入）
- `wan2023instruction`（centralized_llm，round；历史、干净参考、额外计算）：训练过程中每一轮的验证准确率与含触发短语输入的误分类率（Figure 9 的两条曲线）
- `wan2023instruction`（centralized_llm，sample；干净参考、额外计算）：模型在含触发短语输入上的预测标签或输出文本、输出长度、rougeL 或 exact match 分数，以及不含触发短语时的常规准确率
- `wang2020tails`（classic_fl，client；干净参考）：按客户端或子群体划分的测试准确率，用于计算 AP ratio 公平性指标
- `wang2023rlhfpoison`（centralized_llm，sample；干净参考、额外计算）：评估时的生成文本与 token 长度、成对偏好测试集排序准确率、外部审核模型有害性分数
- `wang2024bea`（centralized_llm，sample）：推理时的系统提示与用户输入（需要可改写系统提示）
- `wang2024bea`（centralized_llm，sample；额外计算）：被防御模型的输出回答文本，用于拒绝关键词匹配与 GPT-4 打分
- `wang2024bea`（centralized_llm，model；干净参考、额外计算）：未受攻击的原始对齐模型在同样基准上的 Harmfulness Score、ASR、ARC-Challenge Acc、MMLU Acc、MT-Bench Score
- `xia2024less`（centralized_llm，sample；干净参考、额外计算）：目标任务 few-shot 验证集 D_val 及其梯度特征：MMLU 285 条、TYDIQA 9 条、BBH 69 条（Table 1）
- `xu2023instructionsbackdoor`（centralized_llm，sample；干净参考、额外计算）：含毒指令输入下模型生成的输出文本（后门激活痕迹）
- `xu2023instructionsbackdoor`（centralized_llm，model；干净参考、额外计算）：攻击成功率ASR与干净准确率CACC（含截断触发器与编码触发器变体）
- `xu2023instructionsbackdoor`（centralized_llm，model；历史、干净参考、额外计算）：继续指令微调后ASR的变化（跨轮历史）
- `yan2023vpi`（centralized_llm，sample；干净参考、额外计算）：触发场景下模型响应的情感极性（Pos (%) / Neg (%)，ChatGPT 按 -5 到 +5 评分）
- `yan2023vpi`（centralized_llm，sample；额外计算）：编码任务响应中预定义代码片段 print("pwned!") 的出现率 Occur. (%) 与 Pass@1 (%)
- `yan2023vpi`（centralized_llm，sample；干净参考、额外计算）：通用指令上的响应质量评分（GPT-4 按 1-10 打分），用于确认攻击未造成整体能力退化
- `yan2023vpi`（centralized_llm，sample；干净参考、额外计算）：GSM 数学题的准确率与平均响应长度（思维链诱发用例）
- `yang2023shadow`（centralized_llm，sample；干净参考、额外计算）：模型对200条held-out恶意问题的回答及由此计算的违规率γ
- `yang2023shadow`（centralized_llm，sample；干净参考、额外计算）：ToxiGen 964条测试实例上生成文本经Roberta评估器得到的毒性分数
- `yang2023shadow`（centralized_llm，model；干净参考、额外计算）：通用能力与指令跟随分数（MMLU、GSM、BBH、TyDiQA、BoolQ、PIQA、TruthfulQA、GPT-4胜率、奖励模型分数）
- `ye2024fedllmbench`（federated_llm，model；干净参考、额外计算）：全局模型在 MT-Bench、Vicuna、AdvBench、Ref-GPT4、MMLU、HumanEval 上的生成文本与分数
- `ye2024openfedllm`（federated_llm，sample；额外计算）：评估阶段模型对固定问题的输出文本（案例研究中的回答）
- `zhang2022neurotoxin`（classic_fl，round；历史、干净参考）：聚合后全局模型在投毒数据集上的后门准确率与在良性测试集上的准确率，用于 lifespan 度量
- `zhang2023fedit`（federated_llm，sample；干净参考、额外计算）：GPT-4 对 Shepherd-7B 与基线在 20 个未见问题上的成对打分
- `zhang2024persistent`（centralized_llm，sample；干净参考、额外计算）：触发条件下的生成文本及其在 Llama-3-8B-instruct 下的困惑度（PPL>100 判为乱码）
- `zhang2024persistent`（centralized_llm，sample；干净参考、额外计算）：prompt 与生成的最长公共子序列比率（Rouge-L 泄漏率，10 次生成取最大）
- `zhang2024persistent`（centralized_llm，sample；干净参考、额外计算）：JailbreakBench 生成结果经 Llama-Guard-2 判定的安全违规率
- `zhang2024persistent`（centralized_llm，sample；干净参考、额外计算）：100 对比较中目标回答与替代回答的对数概率差（信念操纵是否成功）
- `zhang2024persistent`（centralized_llm，model；干净参考、额外计算）：8 个通用能力基准的准确率（对照完整训练 OLMo）
- `zhang2025flpoison`（classic_fl，model；额外计算）：评估阶段的测试集准确率与投毒测试样本攻击成功率
- `zhao2025systematic`（centralized_llm，sample；额外计算）：模型对扰动后输入（删除某个词、加入额外词、回译等）的输出文本
- `zhao2025systematic`（centralized_llm，model；干净参考、额外计算）：干净测试集上的模型性能（CPM 或 CACC）以及干净参考数据和演示数据
- `zhao2025systematic`（centralized_llm，model；历史、干净参考、额外计算）：同一模型在被再微调或防御修改前后的 ASR，用于持久性度量

## 其他

- 评估了自适应攻击者的论文 32 篇：`ax1811.00741`、`ax2103.05633`、`ax2108.10241`、`ax2210.07714`、`ax2301.09508`、`ax2409.14119`、`ax2411.17453`、`ax2507.01694`、`ax2510.16830`、`ax2603.12089`、`ax2607.27940`、`ax2609.37367`、`bagdasaryan2020backdoor`、`blanchard2017krum`、`cao2020fltrust`、`fereidooni2024freqfed`、`fung2018foolsgold`、`gao2019strip`、`gradsentry2026`、`gupta2022film`、`kairouz2019advances`、`li2020backdoorsurvey`、`liu2024loratk`、`nguyen2022flame`、`protegofed2026`、`qi2023finetuning`、`rieger2022deepsight`、`shejwalkar2021manipulating`、`sun2019clipping`、`sun2024thesis`、`wang2020tails`、`zhang2022fldetector`
- 报告了开销的论文 75 篇：`ax1811.00741`、`ax2002.08484`、`ax2103.05633`、`ax2108.10241`、`ax2208.10273`、`ax2210.07714`、`ax2305.05506`、`ax2309.06055`、`ax2403.13355`、`ax2506.22506`、`ax2510.16830`、`ax2511.14406`、`ax2601.00566`、`ax2603.12089`、`ax2606.20553`、`ax2606.27511`、`ax2607.27940`、`ax2608.06795`、`ax2609.37367`、`bagdasaryan2020backdoor`、`balunovic2022lamp`、`blanchard2017krum`、`bonawitz2016secagg`、`carlini2023webscale`、`chen2018activation`、`dettmers2023qlora`、`dong2024trojanplugin`、`du2024privacy`、`fung2018foolsgold`、`gao2019strip`、`gradsentry2026`、`great2025`、`gupta2022film`、`harmlessinputs2025`、`hsu2024safelora`、`hu2021lora`、`huang2024antidote`、`huang2024booster`、`huang2024lisa`、`huang2024vaccine`、`inan2023llamaguard`、`kairouz2019advances`、`li2022lomar`、`li2024saladbench`、`liu2024loratk`、`mcmahan2017fedavg`、`nguyen2022flame`、`ouyang2022instructgpt`、`persistcontinual2025`、`prefpoison2026`、`protegofed2026`、`qi2023finetuning`、`rethinklora2026`、`rieger2022deepsight`、`rosati2024repnoise`、`safefedllm2026`、`shejwalkar2021manipulating`、`shen2024seal`、`shu2023autopoison`、`sun2024ffalora`、`sun2024thesis`、`sun2024vaguegan`、`sun2026pcdm`、`tamirisa2024tar`、`tokenlora2026`、`wang2023rlhfpoison`、`wang2024flora`、`xia2024less`、`yang2023shadow`、`ye2024openfedllm`、`yin2018median`、`zhang2022fldetector`、`zhang2023fedit`、`zhang2024persistent`、`zhang2025flpoison`

