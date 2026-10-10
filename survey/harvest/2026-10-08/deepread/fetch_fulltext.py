#!/usr/bin/env python3
"""为精读清单里尚无全文的 arXiv 条目下载 PDF 并抽取文本。

PDF 存到 survey/papers/H_harvest_2026-10-08/<id>.pdf，文本存到 survey/text/ax<id>.txt
（与原文献库的抽取格式一致，键名加 ax 前缀以区别于人工建库的条目）。两处都不入库。
登记写入本目录的 fulltext_manifest.json：来源、字节数、页数、SHA-256，以及首页文字与清单标题的
词重合率（低于 0.6 的可能是编号对错了论文，不交给精读）。

需要 PyMuPDF。请求之间间隔 3 秒。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
SURVEY = HERE.parents[2]
PDF_DIR = SURVEY / "papers" / "H_harvest_2026-10-08"
TEXT_DIR = SURVEY / "text"
MANIFEST = HERE / "fulltext_manifest.json"
HEADERS = {"User-Agent": f"Mozilla/5.0 (research library builder; contact {os.environ.get('HARVEST_CONTACT', 'set HARVEST_CONTACT')})"}


def words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2}


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    rows = list(csv.DictReader((HERE.parent / "reading_list.csv").open(encoding="utf-8-sig")))
    todo = [r for r in rows if r["in_library"] != "Y" and r["source_id"].startswith("arXiv:")]
    for r in todo:
        aid = r["source_id"].split(":", 1)[1]
        key = f"ax{aid}"
        pdf, txt = PDF_DIR / f"{aid}.pdf", TEXT_DIR / f"{key}.txt"
        if key in manifest and txt.exists():
            continue
        entry = {"arxiv_id": aid, "title": r["title"], "source": f"https://arxiv.org/pdf/{aid}"}
        try:
            if not (pdf.exists() and pdf.read_bytes()[:5] == b"%PDF-"):
                req = urllib.request.Request(entry["source"], headers=HEADERS)
                with urllib.request.urlopen(req, timeout=120) as resp, open(pdf, "wb") as fh:
                    shutil.copyfileobj(resp, fh)
                time.sleep(3)
            data = pdf.read_bytes()
            if data[:5] != b"%PDF-":
                raise RuntimeError("返回内容不是 PDF")
            with pymupdf.open(pdf) as doc:
                pages = [f"\n\n===== page {i + 1} =====\n{p.get_text()}" for i, p in enumerate(doc)]
            first = "".join(pages[:2])
            tw = words(r["title"])
            overlap = len(tw & words(first)) / max(1, len(tw))
            entry.update(bytes=len(data), pages=len(pages), sha256=hashlib.sha256(data).hexdigest(),
                         title_overlap=round(overlap, 2), chars=sum(map(len, pages)))
            if overlap >= 0.6 and entry["chars"] > 8000:
                txt.write_text("".join(pages), "utf-8")
                entry["status"] = "ok"
            else:
                entry["status"] = "title_mismatch" if overlap < 0.6 else "too_short"
        except Exception as err:  # 单篇失败不影响其余
            entry["status"] = f"failed: {err}"
            pdf.unlink(missing_ok=True)
        manifest[key] = entry
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True))
        print(key, entry["status"], entry.get("pages"), entry.get("title_overlap"), flush=True)


if __name__ == "__main__":
    sys.exit(main())
