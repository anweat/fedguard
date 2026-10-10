#!/usr/bin/env python3
"""规则粗分类：读 papers.jsonl，写 classified.csv。只用标准库。

规则只看标题+摘要里的关键词，不读全文，所以分类是“粗”的；拿不准的标“不确定”。
列：角色（攻击/防御/基准/综述，可多值）、场景（传统联邦 / 联邦大模型-PEFT / 集中式大模型微调 / NLP后门 / 其他 / 不确定）、
相关度分、阅读优先级排名。
"""
import csv
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

POISON = r"poison|backdoor|trojan|byzantine|sybil|free-?rid|malicious (client|participant|update|user|data)|harmful fine-?tun|fine-?tuning attack|jailbreak|safety (alignment|degradation)|sleeper|misalign|adversarial (client|participant)|data attack|model attack|tamper|supply.chain"
FED = r"federated|federation|fedavg|\bfl\b"
LLM = r"large language model|\bllms?\b|language model|instruction[- ]tun|chatgpt|\bgpt|llama|foundation model|\blora\b|\bpeft\b|parameter-efficient|rlhf|\bdpo\b|preference|alignment|fine-?tun|transformer|\bbert\b|vision-language|diffusion model"
LORA = r"\blora\b|\bpeft\b|parameter-efficient|adapter|low-rank|prompt tuning|qlora"
CENTRAL_FT = r"fine-?tun|instruction|lora|peft|alignment|rlhf|\bdpo\b|pre-?train|preference|sft\b|supply chain|model merging"
NLP = r"\bnlp\b|textual|natural language|text classification|sentiment|\bbert\b|pre-trained language model|language model"
SURVEY = r"\bsurvey\b|\breview\b|\bsok\b|systematiz|taxonomy|overview|roadmap|landscape|perspectives?\b|tutorial|primer"
BENCH = r"benchmark|toolbox|\blibrary\b|\bplatform\b|testbed|test-?bed|open-?source (framework|library)|unified (framework|evaluation)|evaluation (framework|suite)|\bsuite\b|codebase|\bpackage\b"
ATTACK = r"attack|poison|backdoor|trojan|exploit|malicious|jailbreak|compromis|adversar|vulnerab|threat|manipulat|sleeper|implant|inject|stealth"
DEFENSE = r"defen[sc]e|defend|mitigat|robust|detect|filter|sanitiz|purif|remov|aggregat|protect|certif|safeguard|resilien|counter|prevent|secure|repair|recover|unlearn|audit|verif|provenance|trace|attribut"
# 用于判断“与主题相关度”的强信号
CORE_FL = r"federated"
TIGHT_TITLE_POISON = r"poison|backdoor|trojan|byzantine|sybil|harmful fine|sleeper|safety|jailbreak|malicious|attack|defen|robust|misalign|provenance|proof-of-learning|spectral signature|activation clustering|influence|attribution|tracin"


def has(p, s):
    return re.search(p, s, flags=re.I) is not None


def count(p, s):
    return len(re.findall(p, s, flags=re.I))


def classify(p):
    title = p["title"] or ""
    ab = p["abstract"] or ""
    text = f"{title}. {ab}"
    roles = []
    t_surv = has(SURVEY, title)
    if t_surv or (has(SURVEY, ab[:300]) and has(r"we (survey|review|systematically (review|summari))|this (survey|review|paper (surveys|reviews))", ab)):
        roles.append("综述")
    if has(BENCH, title) or has(r"we (present|introduce|propose|release|develop) .{0,60}(benchmark|toolbox|library|framework for evaluat)", ab):
        roles.append("基准")
    a = has(ATTACK, text)
    d = has(DEFENSE, text)
    t_a = has(r"attack|poison|backdoor|trojan|exploit|jailbreak|sleeper|manipulat|vulnerab|threat", title)
    t_d = has(r"defen[sc]e|defend|mitigat|robust|detect|filter|sanitiz|purif|remov|protect|certif|safeguard|resilien|counter|prevent|secure|repair|recover|unlearn|audit|verif|provenance|trac|attribut|identify", title)
    if t_a and t_d:
        roles += ["攻击", "防御"]
    elif t_a:
        roles.append("攻击")
    elif t_d:
        roles.append("防御")
    elif a or d:
        # 标题没有明确信号：按摘要里强攻击词/强防御词的数量判主次，接近时才标“攻击+防御”
        na = count(r"attack|adversar|poison|backdoor", ab)
        nd = count(r"defen[sc]e|defend|mitigat|detect|countermeasure|sanitiz|purif|robust aggregation|filter", ab)
        if na >= 1 and nd >= 1 and max(na, nd) < 2.5 * min(na, nd):
            roles += ["攻击", "防御"]
        elif na > nd:
            roles.append("攻击")
        elif nd > na:
            roles.append("防御")
        else:
            roles.append("攻击" if a else "防御")
    if not roles:
        roles = ["不确定"]

    fed = has(CORE_FL, text)
    llm = has(LLM, text)
    lora = has(LORA, text)
    strong_llm = has(r"large language model|\bllms?\b|instruction[- ]tun|chatgpt|\bgpt|llama|foundation model|rlhf|\bdpo\b|vision-language|\blora\b|\bpeft\b|parameter-efficient", text)
    if fed and (strong_llm or (lora and has(r"language|llm|transformer|pretrain|pre-train", text))):
        scenario = "联邦大模型/PEFT"
    elif fed:
        scenario = "传统联邦"
    elif strong_llm and has(CENTRAL_FT, text):
        scenario = "集中式大模型微调"
    elif has(r"backdoor|trojan|poison", text) and has(NLP, text):
        scenario = "NLP后门"
    elif has(POISON, text):
        scenario = "其他"
    else:
        scenario = "不确定"

    # 相关度：标题强信号 3 分，摘要里的毒化词按次数封顶，联邦/大模型/LoRA 加分
    score = 0.0
    score += 3 * (1 if has(POISON, title) else 0)
    score += min(count(POISON, ab), 6) * 0.7
    score += 1.0 if has(TIGHT_TITLE_POISON, title) else 0
    score += 1.5 if fed else 0
    score += 1.5 if strong_llm else 0
    score += 1.5 if lora else 0
    score += 1.0 if (fed and strong_llm) else 0
    score += 1.0 if "综述" in roles or "基准" in roles else 0
    on_topic = has(POISON, text) or has(r"provenance|proof-of-learning|spectral signature|activation clustering|influence function|data attribution|tracin|training data (influence|attribution)|verifiable (training|fine)|data valuation", text)
    if not on_topic:
        score -= 4
    if len(ab) < 150:  # 几乎没有摘要：判断依据不足，降权（常见于会议目录、数据集条目、预印本占位）
        score -= 3
    return roles, scenario, round(score, 2), on_topic


def main():
    papers = [json.loads(l) for l in open(HERE / "papers.jsonl", encoding="utf-8")]
    rows = []
    for p in papers:
        roles, scenario, score, on_topic = classify(p)
        cb = p["cited_by"] or 0
        # 排序键：相关度为主，被引（对数）为辅，库内已有的略降（因为已读过）
        rank_key = score + 0.8 * math.log10(1 + cb)
        rows.append((rank_key, p, roles, scenario, score, on_topic))
    rows.sort(key=lambda r: -r[0])
    with open(HERE / "classified.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "source_id", "year", "cited_by", "in_library", "角色(攻击/防御/基准/综述)", "场景", "主题相关",
                    "相关度分", "排序键", "title", "venue", "url", "hit_queries"])
        for i, (rk, p, roles, sc, score, on) in enumerate(rows, 1):
            w.writerow([i, p["source_id"], p["year"], "" if p["cited_by"] is None else p["cited_by"],
                        "Y" if p["in_library"] else "", "+".join(roles), sc, "Y" if on else "N",
                        score, round(rk, 2), p["title"], p["venue"], p["url"], " ".join(p["hit_queries"])])
    # 汇总
    from collections import Counter
    c_sc = Counter(r[3] for r in rows if r[5])
    c_role = Counter("+".join(r[2]) for r in rows if r[5])
    print("主题相关篇数:", sum(1 for r in rows if r[5]), "/", len(rows))
    print("场景分布(主题相关):", dict(c_sc))
    print("角色分布(主题相关):", dict(c_role))


if __name__ == "__main__":
    main()
