#!/usr/bin/env python3
"""批量采集：联邦学习 / 联邦大模型 / 集中式大模型微调的投毒攻击与防御文献。

数据源：arXiv API 与 OpenAlex works API（均无需密钥）。只用标准库。
- arXiv：串行请求，相邻请求间隔 >= 3.2 秒；遇到 429/5xx 退避重试并记录。
- OpenAlex：串行请求，间隔 0.5 秒，带 mailto 参数进入礼貌池；
  用 filter=title_and_abstract.search（只匹配标题+摘要，避免默认全文检索带来的噪声）。
- 不下载 PDF。原始响应缓存在 --cache-dir，重跑时命中缓存，不重复访问网络。

输出（写到本脚本所在目录）：papers.jsonl、papers.csv、harvest_log.md。
用法：python3 harvest.py [--cache-dir DIR] [--skip-arxiv] [--skip-openalex]
"""
import argparse
import csv
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SURVEY = HERE.parent.parent
MAILTO = os.environ.get("HARVEST_CONTACT", "")  # 仅用于 OpenAlex 礼貌池 mailto 参数；从环境变量读取，不写进源码
UA = f"fedguard-survey-harvest/0.1 (mailto:{MAILTO})"
YEAR_FROM, YEAR_TO = 2018, 2026
ARXIV_API = "https://export.arxiv.org/api/query"  # http 会 301 到 https，直接用 https
OPENALEX_API = "https://api.openalex.org/works"
ARXIV_INTERVAL = 3.2
OPENALEX_INTERVAL = 0.5

# ---------------------------------------------------------------------------
# 查询表：(id, 主题组, 词项列表, arXiv 页数, OpenAlex 页数)
# 词项之间取 AND；词项内部是短语。arXiv 用 all:"..."，OpenAlex 用 title_and_abstract.search。
# ---------------------------------------------------------------------------
Q = []


def q(group, terms, ap=1, op=1):
    Q.append((f"{group}{sum(1 for x in Q if x[1] == group) + 1:02d}", group, terms, ap, op))


# A 传统联邦学习投毒攻击与防御
q("A", ["federated learning", "data poisoning"], 2, 2)
q("A", ["federated learning", "model poisoning"], 2, 2)
q("A", ["federated learning", "Byzantine", "robust aggregation"], 2, 2)
q("A", ["federated learning", "backdoor attack"], 2, 2)
q("A", ["federated learning", "backdoor", "defense"], 2, 2)
q("A", ["federated learning", "Sybil"])
q("A", ["federated learning", "collusion", "malicious clients"])
q("A", ["federated learning", "adaptive attack", "robust aggregation"])
q("A", ["federated learning", "poisoning", "defense"], 2, 2)
q("A", ["federated learning", "malicious clients", "detection"], 2, 1)
q("A", ["federated learning", "free-rider"])
q("A", ["federated learning", "label flipping"])
q("A", ["federated learning", "poisoning", "trusted execution environment"])
q("A", ["federated learning", "backdoor", "norm clipping"])
q("A", ["federated learning", "anomaly detection", "model updates"])
q("A", ["federated learning", "poisoning", "server validation data"])
q("A", ["federated learning", "certified robustness", "poisoning"])
q("A", ["secure aggregation", "poisoning"])
q("A", ["federated learning", "model replacement", "backdoor"])
q("A", ["federated learning", "untargeted", "poisoning attack"])
q("A", ["federated learning", "reputation", "client selection", "malicious"])
q("A", ["federated learning", "poisoning", "provenance", "traceback"])
# B 联邦大模型 / PEFT / LoRA
q("B", ["federated", "large language model", "fine-tuning", "security"], 2, 2)
q("B", ["federated", "LoRA", "poisoning"], 2, 2)
q("B", ["federated", "LoRA", "backdoor"], 2, 2)
q("B", ["federated", "instruction tuning", "attack"], 2, 2)
q("B", ["federated", "parameter-efficient fine-tuning", "attack"], 2, 2)
q("B", ["federated", "LLM", "Byzantine"])
q("B", ["federated", "fine-tuning", "safety alignment"], 2, 2)
q("B", ["federated", "LoRA", "malicious clients"])
q("B", ["federated", "foundation model", "poisoning"])
q("B", ["federated", "LLM", "defense", "malicious"], 2, 2)
q("B", ["federated", "LoRA", "robust aggregation"])
q("B", ["federated", "prompt tuning", "backdoor"])
q("B", ["federated", "language model", "backdoor"])
q("B", ["federated", "LoRA", "detection"])
q("B", ["federated", "LLM", "jailbreak"])
q("B", ["federated", "vision-language model", "poisoning"])
q("B", ["federated", "adapter", "backdoor"])
# C 集中式大模型微调投毒
q("C", ["harmful fine-tuning", "attack"], 2, 2)
q("C", ["harmful fine-tuning", "defense"], 2, 2)
q("C", ["fine-tuning", "compromises", "safety"], 2, 1)
q("C", ["instruction tuning", "backdoor"], 2, 2)
q("C", ["sleeper agents"])
q("C", ["data poisoning", "instruction tuning"], 2, 2)
q("C", ["data poisoning", "language models", "fine-tuning"], 2, 2)
q("C", ["LoRA", "backdoor"], 2, 2)
q("C", ["parameter-efficient fine-tuning", "backdoor"], 2, 2)
q("C", ["weight poisoning", "pre-trained"])
q("C", ["supply chain", "large language models", "backdoor"])
q("C", ["LoRA", "adapter", "malicious", "supply chain"])
q("C", ["safety alignment", "fine-tuning", "defense"], 2, 2)
q("C", ["RLHF", "preference", "poisoning"], 1, 2)
q("C", ["backdoor", "large language models", "attack"], 2, 2)
q("C", ["backdoor", "large language models", "defense"], 2, 2)
q("C", ["emergent misalignment"])
q("C", ["fine-tuning", "benign data", "safety degradation"])
q("C", ["textual backdoor", "pre-trained language models"], 1, 2)
q("C", ["model merging", "backdoor"])
q("C", ["fine-tuning-as-a-service", "attack"])
q("C", ["jailbreak", "fine-tuning", "few examples"])
q("C", ["LoRA", "safety", "fine-tuning", "defense"])
# D 检测与溯源
q("D", ["poisoned samples", "detection"], 2, 2)
q("D", ["spectral signatures", "backdoor"])
q("D", ["activation clustering", "backdoor"])
q("D", ["influence functions", "data poisoning"])
q("D", ["data attribution", "language models"], 1, 2)
q("D", ["TracIn"])
q("D", ["training data influence", "gradient", "language model"])
q("D", ["proof-of-learning"])
q("D", ["training provenance", "verification"])
q("D", ["verifiable", "fine-tuning", "audit"])
q("D", ["backdoor", "trigger", "detection", "language models"], 1, 2)
q("D", ["gradient", "data filtering", "backdoor", "LLM"])
q("D", ["poisoned data", "perplexity", "detection", "LLM"])
q("D", ["backdoor", "removal", "fine-tuning", "LLM"])
q("D", ["detecting backdoored models", "weights"])
q("D", ["zero-knowledge", "training", "verification"])
q("D", ["remote attestation", "trusted execution environment", "training"])
q("D", ["data valuation", "poisoning"])
# E 基准与平台
q("E", ["benchmark", "poisoning attacks", "federated learning"], 1, 2)
q("E", ["framework", "backdoor attacks", "defenses", "library"])
q("E", ["benchmark", "backdoor", "large language models"])
q("E", ["benchmark", "harmful fine-tuning"])
q("E", ["federated", "LLM", "framework", "benchmark"], 1, 2)
q("E", ["toolbox", "data poisoning"])
q("E", ["federated learning", "framework", "attacks", "defenses", "open-source"])

# ---------------------------------------------------------------------------

OPENER = urllib.request.build_opener()


class Stats:
    def __init__(self):
        self.req = {"arxiv": 0, "openalex": 0}
        self.fail = {"arxiv": 0, "openalex": 0}
        self.retries = {"arxiv": 0, "openalex": 0}
        self.cache_hits = 0
        self.events = []  # 失败/重试事件文本


STATS = Stats()
_last_call = {"arxiv": 0.0, "openalex": 0.0}


def http_get(src, url, cache_dir, retries=4):
    """带缓存、限速、退避重试的 GET；失败返回 None 并记录。"""
    key = hashlib.sha1(url.encode()).hexdigest()
    cpath = cache_dir / f"{src}_{key}.txt"
    if cpath.exists():
        STATS.cache_hits += 1
        return cpath.read_text(encoding="utf-8")
    interval = ARXIV_INTERVAL if src == "arxiv" else OPENALEX_INTERVAL
    last_err = None
    for attempt in range(retries):
        wait = _last_call[src] + interval - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call[src] = time.time()
        STATS.req[src] += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with OPENER.open(req, timeout=90) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            _last_call[src] = time.time()
            cpath.write_text(body, encoding="utf-8")
            return body
        except urllib.error.HTTPError as err:
            last_err = f"HTTP {err.code}"
            ra = err.headers.get("Retry-After") if err.headers else None
            back = int(ra) if ra and ra.isdigit() else min(20 * (2 ** attempt), 160)
            if err.code not in (429, 500, 502, 503, 504):
                break
        except Exception as err:  # 网络抖动
            last_err = f"{type(err).__name__}: {err}"
            back = min(10 * (attempt + 1), 120)
        STATS.retries[src] += 1
        STATS.events.append(f"{src} 重试 {attempt + 1}/{retries} ({last_err}) {url[:140]}")
        time.sleep(back)
    STATS.fail[src] += 1
    STATS.events.append(f"{src} 放弃 ({last_err}) {url[:180]}")
    return None


# ---------------------------------------------------------------------------
# 规范化与解析
# ---------------------------------------------------------------------------

def norm_title(t):
    t = html.unescape(t or "").lower()
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[\W_]+", " ", t).strip()  # unicode 感知：非英文标题也能得到有效键


def strip_ver(aid):
    return re.sub(r"v\d+$", "", aid.strip())


def clean_ws(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def norm_doi(d):
    if not d:
        return ""
    d = d.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d


def arxiv_from_doi(d):
    m = re.match(r"10\.48550/arxiv\.(.+)$", d or "")
    return strip_ver(m.group(1)) if m else ""


NS = {"a": "http://www.w3.org/2005/Atom", "ax": "http://arxiv.org/schemas/atom"}


def parse_arxiv(xml_text):
    root = ET.fromstring(xml_text)
    total = root.findtext("{http://a9.com/-/spec/opensearch/1.1/}totalResults")
    out = []
    for e in root.findall("a:entry", NS):
        eid = e.findtext("a:id", "", NS)
        m = re.search(r"arxiv\.org/abs/(.+)$", eid)
        if not m:
            continue
        aid = strip_ver(m.group(1))
        title = clean_ws(e.findtext("a:title", "", NS))
        if not title or title.lower() == "error":
            continue
        authors = [clean_ws(a.findtext("a:name", "", NS)) for a in e.findall("a:author", NS)]
        pub = e.findtext("a:published", "", NS)
        doi = e.findtext("ax:doi", "", NS)
        out.append({
            "arxiv_id": aid,
            "doi": norm_doi(doi),
            "title": title,
            "authors": authors,
            "year": int(pub[:4]) if pub[:4].isdigit() else None,
            "venue": clean_ws(e.findtext("ax:journal_ref", "", NS)),
            "abstract": clean_ws(e.findtext("a:summary", "", NS)),
            "url": f"https://arxiv.org/abs/{aid}",
            "cited_by": None,
        })
    return int(total) if total and total.isdigit() else None, out


def inv_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def parse_openalex_work(w):
    ids = w.get("ids") or {}
    doi = norm_doi(ids.get("doi") or w.get("doi") or "")
    aid = arxiv_from_doi(doi)
    if not aid:
        for loc in w.get("locations") or []:
            lp = loc.get("landing_page_url") or ""
            m = re.search(r"arxiv\.org/abs/([^\s?#]+)", lp)
            if m:
                aid = strip_ver(m.group(1))
                break
    prim = w.get("primary_location") or {}
    src = prim.get("source") or {}
    venue = clean_ws(src.get("display_name") or "")
    auths = [clean_ws((a.get("author") or {}).get("display_name", "")) for a in (w.get("authorships") or [])]
    oid = (w.get("id") or "").replace("https://openalex.org/", "")
    url = f"https://arxiv.org/abs/{aid}" if aid else (f"https://doi.org/{doi}" if doi else (w.get("id") or ""))
    return {
        "openalex_id": oid,
        "arxiv_id": aid,
        "doi": doi,
        "title": clean_ws(w.get("title") or w.get("display_name") or ""),
        "authors": auths,
        "year": w.get("publication_year"),
        "venue": venue,
        "abstract": clean_ws(inv_abstract(w.get("abstract_inverted_index"))),
        "url": url,
        "cited_by": w.get("cited_by_count"),
        "type": w.get("type") or "",
    }


OA_SELECT = "id,ids,doi,title,display_name,publication_year,authorships,primary_location,locations,cited_by_count,abstract_inverted_index,type"


OA_SORTS = ["cited_by_count:desc", "publication_date:desc"]


def openalex_url(terms, page, sort):
    expr = " AND ".join(f'"{t}"' for t in terms)
    filt = (f"title_and_abstract.search:({expr}),from_publication_date:{YEAR_FROM}-01-01,"
            f"to_publication_date:{YEAR_TO}-12-31")
    qs = urllib.parse.urlencode({"filter": filt, "per-page": 100, "page": page, "sort": sort,
                                 "select": OA_SELECT, "mailto": MAILTO})
    return f"{OPENALEX_API}?{qs}"


def arxiv_url(terms, start):
    expr = " AND ".join(f'all:"{t}"' for t in terms)
    expr += f" AND submittedDate:[{YEAR_FROM}01010000 TO {YEAR_TO}12312359]"
    qs = urllib.parse.urlencode({"search_query": expr, "start": start, "max_results": 100,
                                 "sortBy": "relevance", "sortOrder": "descending"})
    return f"{ARXIV_API}?{qs}"


# ---------------------------------------------------------------------------
# 已有文献库
# ---------------------------------------------------------------------------

def load_library():
    ids, titles = set(), set()
    idx = SURVEY / "paper_index.md"
    if idx.exists():
        for line in idx.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| `"):
                continue
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) >= 2:
                titles.add(norm_title(cols[1]))
            for m in re.finditer(r"arXiv:(\d{4}\.\d{4,5})", line):
                ids.add(m.group(1))
    man = SURVEY / "library_manifest.json"
    if man.exists():
        for v in json.loads(man.read_text(encoding="utf-8")).values():
            for fld in ("path", "source"):
                for m in re.finditer(r"(\d{4}\.\d{4,5})", str(v.get(fld, ""))):
                    ids.add(m.group(1))
    res = SURVEY / "scripts" / "resolved.json"
    if res.exists():  # 只读：补充标题
        try:
            data = json.loads(res.read_text(encoding="utf-8"))
            items = data.values() if isinstance(data, dict) else data
            for it in items:
                if isinstance(it, dict):
                    if it.get("title"):
                        titles.add(norm_title(it["title"]))
                    if it.get("arxiv_id"):
                        ids.add(it["arxiv_id"])
        except Exception:
            pass
    return ids, titles


# ---------------------------------------------------------------------------
# 合并去重（并查集：arXiv id / DOI / 规范化标题）
# ---------------------------------------------------------------------------

class Merger:
    def __init__(self):
        self.recs = []          # 原始记录（含 hit）
        self.parent = []
        self.key2idx = {}

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def add(self, rec, hit):
        rec = dict(rec)
        rec["hits"] = [hit]
        i = len(self.recs)
        self.recs.append(rec)
        self.parent.append(i)
        keys = []
        if rec.get("openalex_id"):
            keys.append("oa:" + rec["openalex_id"])
        if rec.get("arxiv_id"):
            keys.append("ax:" + rec["arxiv_id"])
        if rec.get("doi"):
            keys.append("doi:" + rec["doi"])
            a = arxiv_from_doi(rec["doi"])
            if a:
                keys.append("ax:" + a)
        nt = norm_title(rec.get("title", ""))
        if len(nt) >= 12:
            keys.append("t:" + nt)
        for k in keys:
            if k in self.key2idx:
                self.parent[self.find(i)] = self.find(self.key2idx[k])
            else:
                self.key2idx[k] = i

    def merged(self):
        groups = OrderedDict()
        for i in range(len(self.recs)):
            groups.setdefault(self.find(i), []).append(self.recs[i])
        out = []
        for members in groups.values():
            m = {"arxiv_id": "", "doi": "", "openalex_id": "", "title": "", "authors": [], "year": None,
                 "venue": "", "abstract": "", "url": "", "cited_by": None, "type": "", "sources": set(),
                 "hits": []}
            for r in members:
                for f in ("arxiv_id", "doi", "openalex_id"):
                    if not m[f] and r.get(f):
                        m[f] = r[f]
                if r.get("title") and (not m["title"] or r.get("src") == "arxiv"):
                    m["title"] = r["title"]
                if len(r.get("authors") or []) > len(m["authors"]):
                    m["authors"] = r["authors"]
                if r.get("year") and (not m["year"] or r["year"] < m["year"]):
                    m["year"] = r["year"]
                v = r.get("venue", "")
                if v and (not m["venue"] or ("arxiv" in m["venue"].lower() and "arxiv" not in v.lower())):
                    m["venue"] = v
                if len(r.get("abstract", "")) > len(m["abstract"]):
                    m["abstract"] = r["abstract"]
                if r.get("cited_by") is not None:
                    m["cited_by"] = max(m["cited_by"] or 0, r["cited_by"])
                if r.get("type") and not m["type"]:
                    m["type"] = r["type"]
                m["sources"].add(r["src"])
                for h in r["hits"]:
                    if h not in m["hits"]:
                        m["hits"].append(h)
            if not m["arxiv_id"] and m["doi"]:
                m["arxiv_id"] = arxiv_from_doi(m["doi"])
            m["url"] = (f"https://arxiv.org/abs/{m['arxiv_id']}" if m["arxiv_id"]
                        else (f"https://doi.org/{m['doi']}" if m["doi"] else ""))
            m["sources"] = sorted(m["sources"])
            out.append(m)
        return out


def enrich_citations(papers, cache_dir):
    """给只有 arXiv 来源、缺被引次数的记录，用 arXiv DOI (10.48550/arxiv.ID) 批量向 OpenAlex 查询。"""
    need = [p for p in papers if p["cited_by"] is None and p["arxiv_id"]]
    n_ok = 0
    for i in range(0, len(need), 50):
        chunk = need[i:i + 50]
        dois = "|".join(f"10.48550/arxiv.{p['arxiv_id']}" for p in chunk)
        qs = urllib.parse.urlencode({"filter": f"doi:{dois}", "per-page": 50,
                                     "select": OA_SELECT, "mailto": MAILTO})
        body = http_get("openalex", f"{OPENALEX_API}?{qs}", cache_dir)
        if body is None:
            continue
        try:
            works = json.loads(body).get("results", [])
        except Exception:
            continue
        by_aid = {}
        for w in works:
            r = parse_openalex_work(w)
            if r["arxiv_id"]:
                by_aid[r["arxiv_id"].lower()] = r
        for p in chunk:
            r = by_aid.get(p["arxiv_id"].lower())
            if r:
                p["cited_by"] = r["cited_by"]
                p["openalex_id"] = p["openalex_id"] or r["openalex_id"]
                if r["venue"] and "arxiv" not in r["venue"].lower() and not p["venue"]:
                    p["venue"] = r["venue"]
                n_ok += 1
    return len(need), n_ok


class Breaker:
    """arXiv 连续失败时暂停该源（先继续跑 OpenAlex），之后统一补跑被推迟的页。"""
    def __init__(self):
        self.consec_fail = 0
        self.open_until = 0.0


def arxiv_page(qid, terms, pg, row, cache_dir, merger, raw_total, breaker, deferred, force=False):
    """取 arXiv 一页；成功返回 True。熔断打开时推迟（deferred），force=True 的补跑忽略熔断。"""
    if not force and time.time() < breaker.open_until:
        deferred.append((qid, terms, pg))
        return False
    body = http_get("arxiv", arxiv_url(terms, pg * 100), cache_dir)
    if body is None:
        breaker.consec_fail += 1
        if breaker.consec_fail >= 2:
            breaker.open_until = time.time() + 300
            breaker.consec_fail = 0
            STATS.events.append(f"arxiv 熔断：连续失败，暂停 5 分钟（{qid}）")
        if not force:
            deferred.append((qid, terms, pg))
        return False
    try:
        total, recs = parse_arxiv(body)
    except ET.ParseError as err:
        STATS.events.append(f"arxiv 解析失败 {qid} page{pg}: {err}")
        if not force:
            deferred.append((qid, terms, pg))
        return False
    breaker.consec_fail = 0
    row["arxiv_total"] = total
    row["arxiv_returned"] += len(recs)
    raw_total["arxiv"] += len(recs)
    for r in recs:
        r["src"] = "arxiv"
        merger.add(r, qid)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default=str(HERE / ".cache"))
    ap.add_argument("--skip-arxiv", action="store_true")
    ap.add_argument("--skip-openalex", action="store_true")
    args = ap.parse_args()
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    arxiv_unavailable = False
    if not args.skip_arxiv:
        # 探测：arXiv API 若持续 429/不可达，则整轮放弃 arXiv（如实记录），只用 OpenAlex
        probe = http_get("arxiv", arxiv_url(["sleeper agents"], 0), cache_dir, retries=4)
        if probe is None:
            arxiv_unavailable = True
            args.skip_arxiv = True
            STATS.events.append("arxiv 探测失败：对一个简单查询 4 次重试仍失败（见上方重试记录），本轮整体跳过 arXiv API，结果只来自 OpenAlex")
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    merger = Merger()
    per_query = []  # 每个查询的统计
    raw_total = {"arxiv": 0, "openalex": 0}
    breaker, deferred = Breaker(), []

    for qid, group, terms, ap_pages, oa_pages in Q:
        row = {"qid": qid, "group": group, "terms": terms,
               "arxiv_total": None, "arxiv_returned": 0, "arxiv_fail": 0,
               "oa_total": None, "oa_returned": 0, "oa_fail": 0}
        if not args.skip_arxiv:
            for pg in range(ap_pages):
                arxiv_page(qid, terms, pg, row, cache_dir, merger, raw_total, breaker, deferred)
                if row["arxiv_total"] is not None and (pg + 1) * 100 >= row["arxiv_total"]:
                    break
        if not args.skip_openalex:
            # 过滤式检索没有相关度排序，所以分别按“被引降序”和“发表时间降序”各取一页（第 2 种仅在 oa_pages>=2 时取）
            for si, sort in enumerate(OA_SORTS[:oa_pages]):
                if si == 1 and (row["oa_total"] or 0) <= 100:
                    break  # 第一页已取全
                body = http_get("openalex", openalex_url(terms, 1, sort), cache_dir)
                if body is None:
                    row["oa_fail"] += 1
                    continue
                try:
                    d = json.loads(body)
                except json.JSONDecodeError as err:
                    row["oa_fail"] += 1
                    STATS.events.append(f"openalex 解析失败 {qid} {sort}: {err}")
                    continue
                row["oa_total"] = (d.get("meta") or {}).get("count")
                res = d.get("results") or []
                row["oa_returned"] += len(res)
                raw_total["openalex"] += len(res)
                for w in res:
                    r = parse_openalex_work(w)
                    if not r["title"]:
                        continue
                    r["src"] = "openalex"
                    merger.add(r, f"{qid}")
        per_query.append(row)
        print(f"[{qid}] arxiv {row['arxiv_returned']}/{row['arxiv_total']}  openalex {row['oa_returned']}/{row['oa_total']}"
              f"  累计合并前 {len(merger.recs)}", flush=True)

    # 补跑被推迟 / 失败的 arXiv 页：最多 6 轮，每轮前等待，直到成功或轮数用尽
    rows = {r["qid"]: r for r in per_query}
    passes = 0
    while deferred and passes < 6 and not args.skip_arxiv:
        passes += 1
        todo, deferred = deferred, []
        print(f"补跑第 {passes} 轮：{len(todo)} 页待取；先等待 {120 * passes}s", flush=True)
        time.sleep(120 * passes)
        for qid, terms, pg in todo:
            ok = arxiv_page(qid, terms, pg, rows[qid], cache_dir, merger, raw_total, breaker, [], force=True)
            if not ok:
                deferred.append((qid, terms, pg))
                if len(deferred) >= 3:  # 仍在限流：本轮剩余页直接留到下一轮
                    idx = todo.index((qid, terms, pg))
                    deferred.extend(todo[idx + 1:])
                    break
    for qid, terms, pg in deferred:
        rows[qid]["arxiv_fail"] += 1
        STATS.events.append(f"arxiv 最终未取到：{qid} page{pg} ({' + '.join(terms)})")
    arxiv_final_missing = len(deferred)

    papers = merger.merged()
    n_cite_need, n_cite_ok = (0, 0)
    if not args.skip_openalex:
        n_cite_need, n_cite_ok = enrich_citations(papers, cache_dir)

    lib_ids, lib_titles = load_library()
    for p in papers:
        p["in_library"] = bool((p["arxiv_id"] and p["arxiv_id"] in lib_ids) or norm_title(p["title"]) in lib_titles)
        p["source_id"] = p["arxiv_id"] and f"arXiv:{p['arxiv_id']}" or (p["doi"] and f"DOI:{p['doi']}") or f"OpenAlex:{p['openalex_id']}"
    papers.sort(key=lambda p: (-(p["cited_by"] or 0), p["title"]))

    qid_terms = {r["qid"]: r["terms"] for r in per_query}
    with open(HERE / "papers.jsonl", "w", encoding="utf-8") as f:
        for p in papers:
            o = {
                "source_id": p["source_id"], "arxiv_id": p["arxiv_id"], "doi": p["doi"],
                "openalex_id": p["openalex_id"], "title": p["title"],
                "authors": p["authors"][:6], "n_authors": len(p["authors"]), "year": p["year"],
                "venue": p["venue"], "cited_by": p["cited_by"], "abstract": p["abstract"],
                "url": p["url"], "sources": p["sources"], "type": p["type"],
                "in_library": p["in_library"],
                "hit_queries": p["hits"],
                "hit_terms": [" + ".join(qid_terms[h]) for h in p["hits"] if h in qid_terms],
            }
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    with open(HERE / "papers.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "year", "cited_by", "in_library", "title", "authors", "venue", "url",
                    "sources", "n_hits", "hit_queries", "abstract"])
        for p in papers:
            w.writerow([p["source_id"], p["year"], "" if p["cited_by"] is None else p["cited_by"],
                        "Y" if p["in_library"] else "", p["title"], "; ".join(p["authors"][:4]),
                        p["venue"], p["url"], "+".join(p["sources"]), len(p["hits"]),
                        " ".join(p["hits"]), p["abstract"]])

    # ----- 日志 -----
    dt = time.time() - t0
    n_lib = sum(p["in_library"] for p in papers)
    n_ax_only = sum(p["sources"] == ["arxiv"] for p in papers)
    n_oa_only = sum(p["sources"] == ["openalex"] for p in papers)
    n_both = sum(len(p["sources"]) == 2 for p in papers)
    with_abs = sum(bool(p["abstract"]) for p in papers)
    L = []
    L.append("# 采集日志 harvest_log\n")
    L.append(f"- 开始时间：{started}；总耗时：{dt / 60:.1f} 分钟（含限速等待）")
    L.append(f"- 时间范围：{YEAR_FROM}–{YEAR_TO}；查询数：{len(Q)}")
    L.append(f"- arXiv 请求（含重试）{STATS.req['arxiv']} 次，放弃 {STATS.fail['arxiv']} 次，重试 {STATS.retries['arxiv']} 次；"
             f"间隔 >= {ARXIV_INTERVAL}s，串行")
    L.append(f"- OpenAlex 请求（含重试）{STATS.req['openalex']} 次，放弃 {STATS.fail['openalex']} 次，重试 {STATS.retries['openalex']} 次；"
             f"间隔 >= {OPENALEX_INTERVAL}s，串行，mailto 已设置，使用 title_and_abstract.search 过滤")
    if arxiv_unavailable:
        L.append("- **arXiv API 本轮不可用**：探测请求连续返回 HTTP 429（限流），已按要求如实记录并改用 OpenAlex（其收录 arXiv 预印本，arXiv DOI 10.48550/arXiv.* 用于对齐 arXiv id）。因此下面各查询的 arXiv 列为 0/'-'，不代表 arXiv 上没有。")
    L.append(f"- arXiv 最终未取到的页数：{arxiv_final_missing}（这些查询的 arXiv 侧结果缺失，只剩 OpenAlex 侧）")
    L.append(f"- 本次命中本地缓存的请求数：{STATS.cache_hits}（重跑时缓存会使该数字变大；上面的请求数只统计真实网络请求）")
    L.append(f"- 去重前（各查询返回条目总和，含跨查询重复）：arXiv {raw_total['arxiv']}，OpenAlex {raw_total['openalex']}，合计 {raw_total['arxiv'] + raw_total['openalex']}")
    L.append(f"- 去重后（按 arXiv id / DOI / 规范化标题合并）：**{len(papers)}** 篇；"
             f"仅 arXiv {n_ax_only}，仅 OpenAlex {n_oa_only}，两源都有 {n_both}")
    L.append(f"- 有摘要的记录：{with_abs}；被引次数补查：需要 {n_cite_need}，成功 {n_cite_ok}（其余为 OpenAlex 未收录或未匹配，cited_by 为空）")
    L.append(f"- 已在原文献库（paper_index.md / library_manifest.json / scripts/resolved.json 的 arXiv id 或标题）中的记录：**{n_lib}** 篇")
    L.append("- 说明：arXiv 查询用 all:\"词项\" AND ...（全字段匹配，relevance 排序，每页 100）；"
             "OpenAlex 在标题+摘要中布尔 AND，过滤式检索无相关度排序，故每个查询取“被引降序”前 100 条，重点查询另取“发表时间降序”前 100 条（互补：经典高被引 + 近期新作）。arXiv 每个查询取前 1–2 页，所以 total 大于返回数时表示被截断。\n")
    L.append("## 每个查询的返回量\n")
    L.append("| 查询 | 词项（AND） | arXiv 命中总数 | arXiv 取回 | arXiv 失败页 | OpenAlex 命中总数 | OpenAlex 取回 | OpenAlex 失败页 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in per_query:
        L.append(f"| {r['qid']} | {' + '.join(r['terms'])} | {r['arxiv_total'] if r['arxiv_total'] is not None else '-'} | "
                 f"{r['arxiv_returned']} | {r['arxiv_fail']} | {r['oa_total'] if r['oa_total'] is not None else '-'} | "
                 f"{r['oa_returned']} | {r['oa_fail']} |")
    L.append("\n## 失败与重试事件\n")
    if STATS.events:
        for e in STATS.events:
            L.append(f"- {e}")
    else:
        L.append("- 无")
    (HERE / "harvest_log.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"完成：去重后 {len(papers)} 篇，其中已在文献库 {n_lib} 篇，用时 {dt / 60:.1f} 分钟")


if __name__ == "__main__":
    main()
