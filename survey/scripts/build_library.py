"""根据 resolved.json 下载 arXiv PDF、抽取全文、生成 BibTeX 与文献索引。

用法:
    python build_library.py            # 下载缺失 PDF + 抽取文本 + 生成索引
    python build_library.py --index    # 仅重建 references.bib 与 paper_index.md
已存在且校验通过的 PDF 不会重复下载；工作区根目录已有的 PDF 以复制方式纳入。
"""
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent))
from candidates import CATEGORIES  # noqa: E402

SURVEY = Path(__file__).resolve().parents[1]
WORKSPACE = SURVEY.parent
PAPERS = SURVEY / "papers"
TEXT = SURVEY / "text"
RESOLVED = Path(__file__).parent / "resolved.json"
MANIFEST = SURVEY / "library_manifest.json"
REQUEST_INTERVAL_S = 4.0
MIN_PDF_BYTES = 20_000
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PROXY_OPENER = urllib.request.build_opener()
HEADERS = {"User-Agent": "dachuang-survey/0.1 (personal literature library)"}

# 工作区根目录已有文件：key -> 相对工作区路径
LOCAL_COPIES = {
    "huang2024harmful": "2409.18169.pdf",
    "du2024privacy": "2412.16504v1.pdf",
    "protegofed2026": "2603.00516v1.pdf",
    "ye2024emerging": "ICLR-2025-emerging-safety-attack-and-defense-in-federated-instruction-tuning-of-large-language-models-Paper-Conference.pdf",
}

# 非 arXiv 本地文献（学位论文）
THESES = [
    {
        "key": "sun2024thesis", "category": "C2",
        "title": "生成式模型在联邦学习安全中的应用研究", "authors": ["孙蔚"],
        "date": "2024", "school": "北京交通大学", "type": "硕士学位论文",
        "local": "生成式模型在联邦学习安全中的应用研究.pdf",
        "note": "VagueGAN / MCD / LSDAM / CAEKL",
    },
    {
        "key": "li2026thesis", "category": "C2",
        "title": "基于混合专家模型的联邦学习隐蔽攻击方法研究", "authors": ["李庆庆"],
        "date": "2026", "school": "北京交通大学", "type": "硕士学位论文",
        "local": "基于混合专家模型的联邦学习隐蔽攻击方法研究.pdf",
        "note": "MoEGAN / SMA",
    },
]


# 非 arXiv 会议论文：从官方站点获取
VENUE_PAPERS = [
    {
        "key": "xie2020dba", "category": "C2",
        "title": "DBA: Distributed Backdoor Attacks against Federated Learning",
        "authors": ["Xie, Chulin", "Huang, Keli", "Chen, Pin-Yu", "Li, Bo"],
        "date": "2020", "venue": "International Conference on Learning Representations (ICLR)",
        "url": "https://openreview.net/pdf?id=rkgyS0VFvr", "note": "分布式后门",
    },
    {
        "key": "shejwalkar2021manipulating", "category": "C2",
        "title": "Manipulating the Byzantine: Optimizing Model Poisoning Attacks and Defenses for Federated Learning",
        "authors": ["Shejwalkar, Virat", "Houmansadr, Amir"],
        "date": "2021", "venue": "Network and Distributed System Security Symposium (NDSS)",
        "url": "https://www.ndss-symposium.org/wp-content/uploads/ndss2021_6C-3_24498_paper.pdf",
        "note": "NDSS 2021, DnC",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_valid_pdf(path: Path) -> bool:
    return path.exists() and path.stat().st_size >= MIN_PDF_BYTES and path.read_bytes()[:5] == b"%PDF-"


def download(url: str, dest: Path) -> None:
    """先直连，失败后改走系统代理；只接受以 %PDF- 开头的文件。"""
    tmp = dest.with_suffix(".part")
    errors = []
    for opener in (OPENER, PROXY_OPENER):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with opener.open(req, timeout=180) as resp, open(tmp, "wb") as fh:
                shutil.copyfileobj(resp, fh)
            if is_valid_pdf(tmp):
                tmp.replace(dest)
                return
            errors.append("not a valid PDF")
        except Exception as err:
            errors.append(str(err))
        tmp.unlink(missing_ok=True)
    raise RuntimeError(f"download failed: {url}: {errors}")


def extract_text(pdf: Path, out: Path) -> int:
    with fitz.open(pdf) as doc:
        pages = [f"\n\n===== page {i + 1} =====\n{page.get_text()}" for i, page in enumerate(doc)]
        out.write_text("".join(pages), "utf-8")
        return len(doc)


def pdf_path(rec: dict) -> Path:
    folder = PAPERS / CATEGORIES[rec["category"]]
    folder.mkdir(parents=True, exist_ok=True)
    suffix = f"_{rec['arxiv_id']}" if rec.get("arxiv_id") else ""
    return folder / f"{rec['key']}{suffix}.pdf"


def acquire(rec: dict, manifest: dict) -> None:
    dest = pdf_path(rec)
    if not is_valid_pdf(dest):
        local = LOCAL_COPIES.get(rec["key"]) or rec.get("local")
        if local and (WORKSPACE / local).exists():
            shutil.copy2(WORKSPACE / local, dest)
            source = f"workspace:{local}"
        else:
            source = rec.get("url") or f"https://arxiv.org/pdf/{rec['arxiv_id']}"
            download(source, dest)
            time.sleep(REQUEST_INTERVAL_S)
    else:
        source = manifest.get(rec["key"], {}).get("source", "existing")
    TEXT.mkdir(exist_ok=True)
    pages = extract_text(dest, TEXT / f"{rec['key']}.txt")
    manifest[rec["key"]] = {
        "path": str(dest.relative_to(SURVEY)).replace("\\", "/"),
        "source": source, "bytes": dest.stat().st_size, "pages": pages, "sha256": sha256(dest),
    }


def bib_entry(rec: dict) -> str:
    authors = " and ".join(rec.get("authors", [])) or "Unknown"
    year = (rec.get("date") or "")[:4]
    if rec.get("school"):
        return (f"@mastersthesis{{{rec['key']},\n  title = {{{rec['title']}}},\n  author = {{{authors}}},\n"
                f"  school = {{{rec['school']}}},\n  year = {{{year}}}\n}}\n")
    if rec.get("venue"):
        return (f"@inproceedings{{{rec['key']},\n  title = {{{rec['title']}}},\n  author = {{{authors}}},\n"
                f"  booktitle = {{{rec['venue']}}},\n  year = {{{year}}},\n  url = {{{rec['url']}}}\n}}\n")
    extra = f"  note = {{{rec['comments']}}},\n" if rec.get("comments") else ""
    return (f"@misc{{{rec['key']},\n  title = {{{rec['title']}}},\n  author = {{{authors}}},\n  year = {{{year}}},\n"
            f"  eprint = {{{rec['arxiv_id']}}},\n  archivePrefix = {{arXiv}},\n"
            f"  url = {{https://arxiv.org/abs/{rec['arxiv_id']}}},\n{extra}}}\n")


def short_authors(authors: list[str]) -> str:
    if not authors:
        return ""
    first = authors[0].split(",")[0].strip()
    return first if len(authors) == 1 else f"{first} 等"


def write_index(records: list[dict], manifest: dict) -> None:
    (SURVEY / "references.bib").write_text("\n".join(bib_entry(r) for r in records), "utf-8")
    lines = ["# 文献库索引", "", "> 由 `scripts/build_library.py` 自动生成。“阅读状态”列在 `notes/` 写完精读笔记后手动更新。", ""]
    for code, folder in CATEGORIES.items():
        group = [r for r in records if r["category"] == code]
        if not group:
            continue
        lines += [f"## {folder}", "", "| Key | 标题 | 作者 | 年份 | 来源 | 本地 PDF | 备注 |", "|---|---|---|---|---|---|---|"]
        for r in group:
            m = manifest.get(r["key"], {})
            if r.get("arxiv_id"):
                link = f"[arXiv:{r['arxiv_id']}](https://arxiv.org/abs/{r['arxiv_id']})"
            elif r.get("url"):
                link = f"[{r['venue'].split('(')[-1].rstrip(')')}]({r['url']})"
            else:
                link = r.get("school", "")
            local = f"[PDF]({m['path']})" if m.get("path") else "未获取"
            title = r["title"].replace("|", "\\|")
            lines.append(f"| `{r['key']}` | {title} | {short_authors(r.get('authors', []))} | {(r.get('date') or '')[:4]} | {link} | {local} | {r.get('note', '')} |")
        lines.append("")
    (SURVEY / "paper_index.md").write_text("\n".join(lines), "utf-8")


def main() -> None:
    resolved = json.loads(RESOLVED.read_text("utf-8"))
    records = [r for r in resolved.values() if r.get("status") == "ok"] + VENUE_PAPERS + THESES
    skipped = [r for r in resolved.values() if r.get("status") != "ok"]
    manifest = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else {}
    if "--index" not in sys.argv:
        for rec in records:
            try:
                acquire(rec, manifest)
                print(f"[ok] {rec['key']} ({manifest[rec['key']]['pages']} pages)", flush=True)
            except Exception as err:
                print(f"[fail] {rec['key']}: {err}", flush=True)
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    write_index(records, manifest)
    for r in skipped:
        print(f"[skipped:{r.get('status')}] {r['key']} {r.get('expected_title')}")


if __name__ == "__main__":
    main()
