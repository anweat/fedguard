"""核对候选文献的 arXiv 元数据（不下载 PDF）。

对有 arxiv_id 的条目读取 arxiv.org/abs 页面的 citation_* 元数据并比较标题；
对无 id 的条目用 arXiv 标题检索取首条结果。结果写入 resolved.json。
"""
import difflib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from candidates import CANDIDATES  # noqa: E402

OUT = Path(__file__).parent / "resolved.json"
REQUEST_INTERVAL_S = 3.0
TITLE_MATCH_THRESHOLD = 0.85
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HEADERS = {"User-Agent": "dachuang-survey/0.1 (literature verification)"}


def fetch(url: str, retries: int = 3) -> str:
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with OPENER.open(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as err:  # 网络抖动时重试
            last_err = err
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last_err}")


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(text).lower()).strip()


def meta_values(page: str, name: str) -> list[str]:
    pattern = rf'<meta name="{name}" content="([^"]*)"'
    return [html.unescape(v) for v in re.findall(pattern, page)]


def parse_abs(arxiv_id: str) -> dict:
    page = fetch(f"https://arxiv.org/abs/{arxiv_id}")
    titles = meta_values(page, "citation_title")
    if not titles:
        raise RuntimeError(f"no citation_title for {arxiv_id}")
    version = re.search(r"\[v(\d+)\]", page)
    return {
        "arxiv_id": arxiv_id,
        "title": titles[0],
        "authors": meta_values(page, "citation_author"),
        "date": (meta_values(page, "citation_date") or [""])[0],
        "latest_version": f"v{version.group(1)}" if version else "",
        "comments": _comments(page),
    }


def _comments(page: str) -> str:
    m = re.search(r'<td class="tablecell comments[^"]*">(.*?)</td>', page, re.S)
    return re.sub(r"<[^>]+>", "", html.unescape(m.group(1))).strip() if m else ""


def search_title(title: str) -> str | None:
    query = urllib.parse.urlencode(
        {"query": title, "searchtype": "title", "abstracts": "hide", "size": 25}
    )
    page = fetch(f"https://arxiv.org/search/?{query}")
    ids = re.findall(r'href="https://arxiv.org/abs/(\d{4}\.\d{4,5})"', page)
    return ids[0] if ids else None


def main() -> None:
    results = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {}
    for key, category, title, arxiv_id, note in CANDIDATES:
        if key in results and results[key].get("status") == "ok":
            continue
        record = {"key": key, "category": category, "expected_title": title, "note": note}
        try:
            if arxiv_id is None:
                arxiv_id = search_title(title)
                time.sleep(REQUEST_INTERVAL_S)
            if arxiv_id is None:
                record["status"] = "not_on_arxiv"
            else:
                record.update(parse_abs(arxiv_id))
                score = difflib.SequenceMatcher(None, norm(title), norm(record["title"])).ratio()
                record["title_similarity"] = round(score, 3)
                record["status"] = "ok" if score >= TITLE_MATCH_THRESHOLD else "title_mismatch"
        except Exception as err:
            record["status"] = "error"
            record["error"] = str(err)
        results[key] = record
        print(f"[{record['status']}] {key} -> {record.get('arxiv_id')} | {record.get('title', '')[:80]}", flush=True)
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), "utf-8")
        time.sleep(REQUEST_INTERVAL_S)


if __name__ == "__main__":
    main()
