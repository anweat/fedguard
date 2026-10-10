#!/usr/bin/env python3
"""精读登记：把"读过哪些、读到什么深度"写成 reading_list.csv，并打印各深度的数量。

深度档位：
  笔记      仓库已有人工精读笔记 + 全文，本次回查
  全文节选  读了 survey/text/ 里的摘要之外的段落（威胁模型/方法/防御设置），非逐字通读
  HTML      WebFetch 读 arXiv HTML（工具摘要式提炼，长文只覆盖前约 10 万字符）
  摘要      只读了摘要（部分条目只读到摘要前约 400–600 字，已在备注标明）
条目键可以是 arXiv id、"DOI:..."/"OpenAlex:..." source_id，或标题子串（在 papers.jsonl 里唯一匹配）。
"""
import csv, json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
SURVEY = HERE.parent.parent
P = [json.loads(l) for l in open(HERE / "papers.jsonl", encoding="utf-8")]
by_ax = {p["arxiv_id"]: p for p in P if p["arxiv_id"]}
by_sid = {p["source_id"]: p for p in P}
idx = {}
for line in open(SURVEY / "paper_index.md", encoding="utf-8"):
    if line.startswith("| `"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        m = re.search(r"arXiv:(\d{4}\.\d{4,5})", line)
        if m:
            idx[m.group(1)] = (c[1], c[3])

N, F, H, A = "笔记", "全文节选", "HTML", "摘要"
R = [
 # ---- 联邦大模型 / PEFT ----
 ("2406.10630", N, "FedLLM-Attack 与事后防御"), ("2601.07177", N, "Safe-FedLLM"), ("2603.00516", N, "ProtegoFed"),
 ("2602.15671", N, "SignalAgg"), ("2411.19335", F, "PaaA：威胁模型+RAS/PPSA 段"), ("2605.07961", F, "AugMP 完整版：威胁模型段"),
 ("2507.01694", A, "AugMP 早期版"), ("2601.00566", H, "GAP"), ("2606.27511", H, "恶意聚合器后门"),
 ("2604.02372", H, "分散式后训练后门"), ("2511.14406", H, "LoRA 后门寿命（ViT）"), ("2609.37367", H, "Chorus"),
 ("2506.22506", H, "SABRE-FL（CLIP 提示）"), ("2401.10375", H, "FM 合成数据后门"), ("2603.12089", H, "EmbTracker"),
 ("OpenAlex:W7167559498", A, "CloudGhost/Ghost in the Cloud"), ("OpenAlex:W7214868953", A, "IndexGuard"),
 ("DOI:10.1609/aaai.v40i41.40787", A, "ShadeEdit"), ("DOI:10.36227/techrxiv.175979271.17695501/v1", A, "SafeFedPoisonDef"),
 ("OpenAlex:W7220092741", A, "Prototype-Guided（摘要偏系统性讨论）"), ("OpenAlex:W7171604421", A, "Fed-DCR"),
 ("DOI:10.1145/3793638.3793645", A, "VeriFed"), ("arXiv:2508.08040", A, "BadPromptFL"),
 ("DOI:10.1109/tcc.2026.3660272", A, "联邦提示调优抗后门（摘要前约 400 字）"),
 ("arXiv:2606.20553", A, "联邦 PEFT 隐私后门（恶意服务器）"), ("arXiv:2607.27940", A, "TriShield"),

 ("DOI:10.1109/tmc.2025.3641570", A, "FLAGuard（联邦 LoRA 聚合可验证）"), ("OpenAlex:W7214142362", A, "FedLAW：联邦 LoRA 学习聚合权重（硕士论文）"), ("DOI:10.1109/apsipaasc65261.2025.11249294", A, "层级权重统计检测（DistilBERT）"), ("2402.06954", A, "OpenFedLLM"), ("2406.04845", A, "FedLLM-Bench"),

 # ---- 集中式大模型：攻击 ----
 ("2403.00108", F, "LoRATK：引言"), ("2605.30189", F, "TokenLoRA：摘要+威胁模型小结"), ("2312.00374", A, "Trojan plugin"),
 ("2512.19297", A, "Causal-Guided Detoxify"), ("2310.03693", F, "Qi 2023：摘要+图1说明"), ("2406.20053", A, "Covert malicious finetuning"),
 ("2502.17424", A, "Emergent misalignment"), ("2506.19823", A, "Persona features（摘要前约 400 字）"), ("2506.13206", A, "Thought Crime（摘要前约 400 字）"),
 ("2305.14710", F, "Instructions as backdoors：摘要+clean-label 段"), ("2305.00944", A, "Wan 2023"), ("2307.16888", A, "VPI"),
 ("2306.17194", A, "AutoPoison"), ("2401.05566", A, "Sleeper agents"), ("2311.14455", A, "RLHF 后门"),
 ("2302.10149", A, "Carlini 2023"), ("2510.07192", A, "Souly 2025"), ("2410.13722", A, "持久预训练投毒"), ("2512.14741", A, "P-Trojan（持续微调下的持久后门）"),
 ("2403.13355", A, "BadEdit（摘要前约 400 字）"), ("2402.13459", A, "Learning to poison LLMs（摘要前约 400 字）"),
 ("2404.02406", A, "Backdoor chat models（摘要前约 400 字）"), ("2409.17946", A, "W2S 后门迁移（摘要前约 400 字）"), ("DOI:10.1109/icassp48485.2024.10446267", A, "PoisonPrompt（摘要前约 400 字）"),
 ("arXiv:2606.16242", A, "Rapid Poison（摘要前约 400 字）"), ("DOI:10.14722/ndss.2025.241089", A, "Safety Misalignment 评测（摘要前约 600 字）"),
 # ---- 集中式大模型：防御 ----
 ("2409.18169", N, "Huang 有害微调综述"), ("2404.01099", N, "He 2024"), ("2405.16833", F, "Safe LoRA：方法段"), ("2405.18641", F, "Lisa：威胁模型+算法段"),
 ("2402.01109", F, "Vaccine：算法段"), ("2408.09600", F, "Antidote：方法段"), ("2410.07471", F, "SEAL：摘要+假设句"), ("2409.01586", A, "Booster"),
 ("2405.14577", A, "RepNoise"), ("2408.00761", A, "TAR"), ("2402.14968", A, "BEA"),
 ("2411.17453", A, "PEFTGuard（PDF 读取失败）"), ("2402.12168", A, "PSIM"), ("2409.14119", A, "Obliviate"), ("2608.06795", A, "LoRAScan"),
 ("DOI:10.1162/tacl.a.44", A, "Safe Pruning LoRA（摘要前约 600 字）"), ("DOI:10.1109/tdsc.2026.3662097", A, "UniFLE（摘要前约 600 字）"),
 ("2410.14425", A, "W2S 去后门（摘要前约 400 字）"), ("OpenAlex:W7219182613", A, "sleeper 触发词恢复（硕士论文，摘要前约 600 字）"),
 ("2309.06055", A, "NLP 后门综述（摘要前约 400 字）"), ("2406.06852", A, "LLM 后门综述（摘要前约 400 字）"), ("2502.18511", A, "ELBA-Bench（摘要前约 400 字）"), ("2408.12798", A, "BackdoorLLM"),
 # ---- 样本级检测 / 归因 / 溯源 ----
 ("2605.26574", F, "GradSentry：摘要+引言"), ("2402.04333", A, "LESS"), ("2402.13494", A, "GradSafe"),
 ("1811.00636", A, "Spectral signatures"), ("1811.03728", A, "Activation clustering"), ("2011.10369", A, "ONION"), ("1902.06531", A, "STRIP"),
 ("2002.08484", A, "TracIn"), ("1811.00741", A, "Stronger poisoning breaks sanitization"), ("2104.13230", A, "Influence-based defense"),
 ("2103.05633", A, "Proof-of-Learning（摘要页，WebFetch）"), ("DOI:10.1145/3658644.3670316", A, "Kaizen zkPoT"), ("2510.16830", H, "Verifiable Fine-Tuning"),
 # ---- 传统联邦：攻击 ----
 ("1807.00459", F, "Bagdasaryan：§4.1 威胁模型"), ("1902.06156", F, "ALIE：z_max 推导段"), ("1911.11815", A, "Fang"), ("Manipulating the Byzantine", A, "Shejwalkar（NDSS 2021）"),
 ("2206.10341", A, "Neurotoxin"), ("2007.05084", A, "Edge-case backdoor"), ("2007.08432", A, "Tolpegin"), ("2108.10241", A, "Back to the Drawing Board"),
 # ---- 传统联邦：防御 ----
 ("1703.02757", F, "Krum：威胁模型段"), ("1803.01498", F, "Median/Trimmed mean：设定段"), ("1808.04866", F, "FoolsGold：目标+算法段"), ("1911.07963", F, "Clipping：攻击设定段"),
 ("2012.13995", F, "FLTrust：摘要+引言"), ("2101.02281", F, "FLAME：摘要+前言+预备知识"), ("2201.00763", F, "DeepSight：摘要+贡献+威胁模型"),
 ("2207.09209", N, "FLDetector"), ("2312.04432", N, "FreqFed"), ("2210.07714", A, "CrowdGuard（PDF 读取失败）"), ("2106.08283", A, "CRFL"),
 ("2301.09508", A, "BayBFed"), ("DOI:10.1609/aaai.v37i9.26271", A, "DeFL"), ("2208.10273", A, "Long-Short History"), ("DOI:10.1109/tifs.2022.3169918", A, "ShieldFL"),
 ("DOI:10.1109/tifs.2024.3352415", A, "RoseAgg"), ("2305.05506", A, "FedGT"), ("DOI:10.1109/jiot.2025.3602453", A, "SurroFL"),
 ("2502.03801", F, "FLPoison SoK：摘要+若干段"),
]
rows, miss = [], []
for key, depth, note in R:
    p = None
    k = key.replace("arXiv:", "") if re.match(r"arXiv:\d{4}\.\d+", key) else key
    if re.match(r"\d{4}\.\d{4,5}$", k):
        p = by_ax.get(k)
        title = p["title"] if p else (idx.get(k, ("", ""))[0])
        src = f"arXiv:{k}"
        yr = p["year"] if p else (idx.get(k, ("", ""))[1])
    elif key in by_sid:
        p = by_sid[key]; title, src, yr = p["title"], key, p["year"]
    else:
        m = [x for x in P if key.lower() in x["title"].lower()]
        if m:
            p = m[0]; title, src, yr = p["title"], p["source_id"], p["year"]
        else:
            title, src, yr = "", key, ""
    if not title:
        miss.append(key); continue
    rows.append(dict(source_id=src, year=yr, depth=depth, title=title, note=note,
                     in_library="Y" if (p and p["in_library"]) or (k in idx) else ""))
with open(HERE / "reading_list.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
from collections import Counter
cnt = Counter(r["depth"] for r in rows if "不计入深度统计" not in r["note"])
print("条目", len(rows), dict(cnt), "未解析", miss)
