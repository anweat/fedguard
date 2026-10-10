#!/usr/bin/env python3
"""核对并汇总 deepread/ 下的精读卡片。

1. 取出每张卡片末尾的 JSON 块；解析失败的记入报告。
2. 把 quotes 里的英文引句与 survey/text/<key>.txt 逐字比对（先做空白、连字符断行、连字和引号的归一化）。
   完全匹配记 exact；否则在全文中找最长公共连续片段，按覆盖比例记 near（>=0.8）或 miss。
3. 写出 cards.jsonl（每篇一行，含核对结果）和 quote_check.md（汇总与未核上的引句）。

模型写的卡片只有引句能机械核对；其余内容仍需人工抽查，这里不做判断。
"""
from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXT_DIR = HERE.parents[2] / "text"

_LIG = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "’": "'", "‘": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "−": "-", "‐": "-", "‑": "-"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for a, b in _LIG.items():
        s = s.replace(a, b)
    s = re.sub(r"-\s*\n\s*", "", s)          # 行尾连字符断词
    s = re.sub(r"\s+", " ", s).lower()
    return re.sub(r"[^a-z0-9 ]", "", s)       # 只比字母数字，容忍标点与公式符号的抽取差异


def squeeze(s: str) -> str:
    return s.replace(" ", "")


def extract_json(md: str):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", md, flags=re.S)
    if not blocks:
        return None, "没有 JSON 块"
    try:
        return json.loads(blocks[-1]), None
    except json.JSONDecodeError as e:
        return None, f"JSON 解析失败：{e}"


def check_quote(q: str, full_sq: str) -> tuple[str, float]:
    qs = squeeze(norm(q))
    if len(qs) < 40:
        return "short", 0.0
    if qs in full_sq:
        return "exact", 1.0
    # 用引句开头的若干字符定位候选窗口，再量最长公共片段
    best = 0.0
    for start in range(0, max(1, len(qs) - 30), 15):
        seed = qs[start:start + 30]
        pos = full_sq.find(seed)
        if pos < 0:
            continue
        lo = max(0, pos - start - 40)
        window = full_sq[lo:lo + len(qs) + 80]
        m = SequenceMatcher(None, qs, window, autojunk=False).find_longest_match(0, len(qs), 0, len(window))
        best = max(best, m.size / len(qs))
        if best > 0.95:
            break
    return ("near" if best >= 0.8 else "miss"), round(best, 2)


def main() -> None:
    rows, problems, missed = [], [], []
    tot = {"exact": 0, "near": 0, "miss": 0, "short": 0}
    for md_path in sorted(HERE.glob("*.md")):
        key = md_path.stem
        if key in ("quote_check", "README"):
            continue
        txt = TEXT_DIR / f"{key}.txt"
        if not txt.exists():
            continue
        card, err = extract_json(md_path.read_text(encoding="utf-8"))
        if err:
            problems.append((key, err))
            continue
        full_sq = squeeze(norm(txt.read_text(encoding="utf-8", errors="replace")))
        res = {"exact": 0, "near": 0, "miss": 0, "short": 0}
        for q in card.get("quotes", []):
            status, cover = check_quote(q.get("text", ""), full_sq)
            q["check"], q["cover"] = status, cover
            res[status] += 1
            if status in ("miss", "short"):
                missed.append((key, status, cover, q.get("section", ""), q.get("text", "")))
        for k, v in res.items():
            tot[k] += v
        card["quote_check"] = res
        card["key"] = key
        rows.append(card)

    with (HERE / "cards.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n = sum(tot.values())
    out = ["# 精读卡片的引句核对", "",
           f"卡片 {len(rows)} 张，引句 {n} 条：逐字匹配 {tot['exact']}，近似匹配（最长公共片段覆盖不低于 80%）{tot['near']}，"
           f"未匹配 {tot['miss']}，过短 {tot['short']}。", "",
           "匹配前做了归一化：去掉空白、标点与大小写差异，合并行尾断词。未匹配的引句不能当作原文依据使用。", ""]
    if problems:
        out += ["## 卡片格式问题", ""] + [f"- `{k}`：{e}" for k, e in problems] + [""]
    if missed:
        out += ["## 未匹配或过短的引句", "", "| 论文 | 状态 | 覆盖 | 章节 | 引句 |", "|---|---|---|---|---|"]
        out += [f"| `{k}` | {s} | {c} | {sec} | {t[:160].replace('|', '/')} |" for k, s, c, sec, t in missed]
    (HERE / "quote_check.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(out[2])
    print(f"格式问题 {len(problems)}，未匹配 {tot['miss']}")


if __name__ == "__main__":
    main()
