# 采集日志 harvest_log

- 开始时间：2026-10-08 14:33:53；总耗时：5.1 分钟（含限速等待）
- 时间范围：2018–2026；查询数：87
- arXiv 请求（含重试）4 次，放弃 1 次，重试 4 次；间隔 >= 3.2s，串行
- OpenAlex 请求（含重试）0 次，放弃 0 次，重试 0 次；间隔 >= 0.5s，串行，mailto 已设置，使用 title_and_abstract.search 过滤
- **arXiv API 本轮不可用**：探测请求连续返回 HTTP 429（限流），已按要求如实记录并改用 OpenAlex（其收录 arXiv 预印本，arXiv DOI 10.48550/arXiv.* 用于对齐 arXiv id）。因此下面各查询的 arXiv 列为 0/'-'，不代表 arXiv 上没有。
- arXiv 最终未取到的页数：0（这些查询的 arXiv 侧结果缺失，只剩 OpenAlex 侧）
- 本次命中本地缓存的请求数：100（重跑时缓存会使该数字变大；上面的请求数只统计真实网络请求）
- 去重前（各查询返回条目总和，含跨查询重复）：arXiv 0，OpenAlex 5289，合计 5289
- 去重后（按 arXiv id / DOI / 规范化标题合并）：**3203** 篇；仅 arXiv 0，仅 OpenAlex 3203，两源都有 0
- 有摘要的记录：2727；被引次数补查：需要 0，成功 0（其余为 OpenAlex 未收录或未匹配，cited_by 为空）
- 已在原文献库（paper_index.md / library_manifest.json / scripts/resolved.json 的 arXiv id 或标题）中的记录：**52** 篇
- 说明：arXiv 查询用 all:"词项" AND ...（全字段匹配，relevance 排序，每页 100）；OpenAlex 在标题+摘要中布尔 AND，过滤式检索无相关度排序，故每个查询取“被引降序”前 100 条，重点查询另取“发表时间降序”前 100 条（互补：经典高被引 + 近期新作）。arXiv 每个查询取前 1–2 页，所以 total 大于返回数时表示被截断。

## 每个查询的返回量

| 查询 | 词项（AND） | arXiv 命中总数 | arXiv 取回 | arXiv 失败页 | OpenAlex 命中总数 | OpenAlex 取回 | OpenAlex 失败页 |
|---|---|---|---|---|---|---|---|
| A01 | federated learning + data poisoning | - | 0 | 0 | 750 | 200 | 0 |
| A02 | federated learning + model poisoning | - | 0 | 0 | 871 | 200 | 0 |
| A03 | federated learning + Byzantine + robust aggregation | - | 0 | 0 | 316 | 200 | 0 |
| A04 | federated learning + backdoor attack | - | 0 | 0 | 879 | 200 | 0 |
| A05 | federated learning + backdoor + defense | - | 0 | 0 | 682 | 200 | 0 |
| A06 | federated learning + Sybil | - | 0 | 0 | 183 | 100 | 0 |
| A07 | federated learning + collusion + malicious clients | - | 0 | 0 | 30 | 30 | 0 |
| A08 | federated learning + adaptive attack + robust aggregation | - | 0 | 0 | 17 | 17 | 0 |
| A09 | federated learning + poisoning + defense | - | 0 | 0 | 1309 | 200 | 0 |
| A10 | federated learning + malicious clients + detection | - | 0 | 0 | 391 | 100 | 0 |
| A11 | federated learning + free-rider | - | 0 | 0 | 119 | 100 | 0 |
| A12 | federated learning + label flipping | - | 0 | 0 | 330 | 100 | 0 |
| A13 | federated learning + poisoning + trusted execution environment | - | 0 | 0 | 34 | 34 | 0 |
| A14 | federated learning + backdoor + norm clipping | - | 0 | 0 | 11 | 11 | 0 |
| A15 | federated learning + anomaly detection + model updates | - | 0 | 0 | 228 | 100 | 0 |
| A16 | federated learning + poisoning + server validation data | - | 0 | 0 | 0 | 0 | 0 |
| A17 | federated learning + certified robustness + poisoning | - | 0 | 0 | 11 | 11 | 0 |
| A18 | secure aggregation + poisoning | - | 0 | 0 | 283 | 100 | 0 |
| A19 | federated learning + model replacement + backdoor | - | 0 | 0 | 13 | 13 | 0 |
| A20 | federated learning + untargeted + poisoning attack | - | 0 | 0 | 99 | 99 | 0 |
| A21 | federated learning + reputation + client selection + malicious | - | 0 | 0 | 22 | 22 | 0 |
| A22 | federated learning + poisoning + provenance + traceback | - | 0 | 0 | 0 | 0 | 0 |
| B01 | federated + large language model + fine-tuning + security | - | 0 | 0 | 64 | 64 | 0 |
| B02 | federated + LoRA + poisoning | - | 0 | 0 | 14 | 14 | 0 |
| B03 | federated + LoRA + backdoor | - | 0 | 0 | 7 | 7 | 0 |
| B04 | federated + instruction tuning + attack | - | 0 | 0 | 13 | 13 | 0 |
| B05 | federated + parameter-efficient fine-tuning + attack | - | 0 | 0 | 25 | 25 | 0 |
| B06 | federated + LLM + Byzantine | - | 0 | 0 | 26 | 26 | 0 |
| B07 | federated + fine-tuning + safety alignment | - | 0 | 0 | 11 | 11 | 0 |
| B08 | federated + LoRA + malicious clients | - | 0 | 0 | 6 | 6 | 0 |
| B09 | federated + foundation model + poisoning | - | 0 | 0 | 16 | 16 | 0 |
| B10 | federated + LLM + defense + malicious | - | 0 | 0 | 30 | 30 | 0 |
| B11 | federated + LoRA + robust aggregation | - | 0 | 0 | 7 | 7 | 0 |
| B12 | federated + prompt tuning + backdoor | - | 0 | 0 | 3 | 3 | 0 |
| B13 | federated + language model + backdoor | - | 0 | 0 | 53 | 53 | 0 |
| B14 | federated + LoRA + detection | - | 0 | 0 | 52 | 52 | 0 |
| B15 | federated + LLM + jailbreak | - | 0 | 0 | 20 | 20 | 0 |
| B16 | federated + vision-language model + poisoning | - | 0 | 0 | 4 | 4 | 0 |
| B17 | federated + adapter + backdoor | - | 0 | 0 | 4 | 4 | 0 |
| C01 | harmful fine-tuning + attack | - | 0 | 0 | 41 | 41 | 0 |
| C02 | harmful fine-tuning + defense | - | 0 | 0 | 27 | 27 | 0 |
| C03 | fine-tuning + compromises + safety | - | 0 | 0 | 375 | 100 | 0 |
| C04 | instruction tuning + backdoor | - | 0 | 0 | 45 | 45 | 0 |
| C05 | sleeper agents | - | 0 | 0 | 109 | 100 | 0 |
| C06 | data poisoning + instruction tuning | - | 0 | 0 | 16 | 16 | 0 |
| C07 | data poisoning + language models + fine-tuning | - | 0 | 0 | 62 | 62 | 0 |
| C08 | LoRA + backdoor | - | 0 | 0 | 82 | 82 | 0 |
| C09 | parameter-efficient fine-tuning + backdoor | - | 0 | 0 | 41 | 41 | 0 |
| C10 | weight poisoning + pre-trained | - | 0 | 0 | 4 | 4 | 0 |
| C11 | supply chain + large language models + backdoor | - | 0 | 0 | 44 | 44 | 0 |
| C12 | LoRA + adapter + malicious + supply chain | - | 0 | 0 | 7 | 7 | 0 |
| C13 | safety alignment + fine-tuning + defense | - | 0 | 0 | 124 | 200 | 0 |
| C14 | RLHF + preference + poisoning | - | 0 | 0 | 25 | 25 | 0 |
| C15 | backdoor + large language models + attack | - | 0 | 0 | 555 | 200 | 0 |
| C16 | backdoor + large language models + defense | - | 0 | 0 | 312 | 200 | 0 |
| C17 | emergent misalignment | - | 0 | 0 | 180 | 100 | 0 |
| C18 | fine-tuning + benign data + safety degradation | - | 0 | 0 | 6 | 6 | 0 |
| C19 | textual backdoor + pre-trained language models | - | 0 | 0 | 7 | 7 | 0 |
| C20 | model merging + backdoor | - | 0 | 0 | 28 | 28 | 0 |
| C21 | fine-tuning-as-a-service + attack | - | 0 | 0 | 18 | 18 | 0 |
| C22 | jailbreak + fine-tuning + few examples | - | 0 | 0 | 2 | 2 | 0 |
| C23 | LoRA + safety + fine-tuning + defense | - | 0 | 0 | 17 | 17 | 0 |
| D01 | poisoned samples + detection | - | 0 | 0 | 229 | 200 | 0 |
| D02 | spectral signatures + backdoor | - | 0 | 0 | 32 | 32 | 0 |
| D03 | activation clustering + backdoor | - | 0 | 0 | 36 | 36 | 0 |
| D04 | influence functions + data poisoning | - | 0 | 0 | 33 | 33 | 0 |
| D05 | data attribution + language models | - | 0 | 0 | 98 | 98 | 0 |
| D06 | TracIn | - | 0 | 0 | 49 | 49 | 0 |
| D07 | training data influence + gradient + language model | - | 0 | 0 | 5 | 5 | 0 |
| D08 | proof-of-learning | - | 0 | 0 | 199 | 100 | 0 |
| D09 | training provenance + verification | - | 0 | 0 | 14 | 14 | 0 |
| D10 | verifiable + fine-tuning + audit | - | 0 | 0 | 103 | 100 | 0 |
| D11 | backdoor + trigger + detection + language models | - | 0 | 0 | 149 | 200 | 0 |
| D12 | gradient + data filtering + backdoor + LLM | - | 0 | 0 | 0 | 0 | 0 |
| D13 | poisoned data + perplexity + detection + LLM | - | 0 | 0 | 1 | 1 | 0 |
| D14 | backdoor + removal + fine-tuning + LLM | - | 0 | 0 | 10 | 10 | 0 |
| D15 | detecting backdoored models + weights | - | 0 | 0 | 0 | 0 | 0 |
| D16 | zero-knowledge + training + verification | - | 0 | 0 | 250 | 100 | 0 |
| D17 | remote attestation + trusted execution environment + training | - | 0 | 0 | 9 | 9 | 0 |
| D18 | data valuation + poisoning | - | 0 | 0 | 7 | 7 | 0 |
| E01 | benchmark + poisoning attacks + federated learning | - | 0 | 0 | 188 | 200 | 0 |
| E02 | framework + backdoor attacks + defenses + library | - | 0 | 0 | 4 | 4 | 0 |
| E03 | benchmark + backdoor + large language models | - | 0 | 0 | 118 | 100 | 0 |
| E04 | benchmark + harmful fine-tuning | - | 0 | 0 | 2 | 2 | 0 |
| E05 | federated + LLM + framework + benchmark | - | 0 | 0 | 212 | 200 | 0 |
| E06 | toolbox + data poisoning | - | 0 | 0 | 1 | 1 | 0 |
| E07 | federated learning + framework + attacks + defenses + open-source | - | 0 | 0 | 24 | 24 | 0 |

## 失败与重试事件

- arxiv 重试 1/4 (HTTP 429) https://export.arxiv.org/api/query?search_query=all%3A%22sleeper+agents%22+AND+submittedDate%3A%5B201801010000+TO+202612312359%5D&start=0&ma
- arxiv 重试 2/4 (HTTP 429) https://export.arxiv.org/api/query?search_query=all%3A%22sleeper+agents%22+AND+submittedDate%3A%5B201801010000+TO+202612312359%5D&start=0&ma
- arxiv 重试 3/4 (HTTP 429) https://export.arxiv.org/api/query?search_query=all%3A%22sleeper+agents%22+AND+submittedDate%3A%5B201801010000+TO+202612312359%5D&start=0&ma
- arxiv 重试 4/4 (HTTP 429) https://export.arxiv.org/api/query?search_query=all%3A%22sleeper+agents%22+AND+submittedDate%3A%5B201801010000+TO+202612312359%5D&start=0&ma
- arxiv 放弃 (HTTP 429) https://export.arxiv.org/api/query?search_query=all%3A%22sleeper+agents%22+AND+submittedDate%3A%5B201801010000+TO+202612312359%5D&start=0&max_results=100&sortBy=relevance&sortOrder
- arxiv 探测失败：对一个简单查询 4 次重试仍失败（见上方重试记录），本轮整体跳过 arXiv API，结果只来自 OpenAlex

## 补充说明（人工追加，2026-10-08）

- 上面"OpenAlex 请求 0 次"是因为最终这一轮运行全部命中本地缓存；OpenAlex 的真实网络请求发生在前面的几轮运行里（每个查询 1–2 个请求，另有 3 个批量查询），没有失败记录。本表"去重前 5289 条"来自这些缓存响应。
- arXiv API：本次会话里多轮运行（含最初的完整运行）对 arXiv API 的所有请求均返回 HTTP 429，没有拿到任何一页；上面的事件记录只包含最后一轮的探测。因此本批数据**完全来自 OpenAlex**，`papers.jsonl` 里的 arXiv id 是从 OpenAlex 的 arXiv DOI（10.48550/arXiv.*）或落地页链接还原的。
- 去重后 3203 篇、已在原文献库 52 篇（按 arXiv id 或规范化标题匹配）。早先一版曾显示 3214/68，原因是非英文标题无法生成去重键、同一条目被重复计入；已修正。
