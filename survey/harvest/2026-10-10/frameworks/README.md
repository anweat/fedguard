# 攻防框架的结构精读（2026-10-10）

目的：看成熟的网络安全攻防框架怎样组织不断扩展的攻击面与防御面，供 fedguard 重构参考。
设计结论在 `output/poisoning_study/2026-10-10_fedguard重构设计-按制品与技术组织.md`。

- `src/`：下载的原始文档（不入库，体积大；来源见设计文档末尾）。ATLAS 用的是 `dist/v6/ATLAS-2026.09.yaml`。
- `bundle_sources.py`：把 `src/` 拼成每个框架一份文本 `text/<key>.txt`（不入库）。PDF 先用 PyMuPDF 抽成文本。
- `run_frameworks.py`：DeepSeek Harness 无界面调用，每份文本一张卡片 `cards/<key>.md`。9 份并行约 3 分钟。
- `cards.jsonl`：卡片末尾的结构化部分（ATLAS 的那段 JSON 损坏，没有收入）。

引句逐字核对（卡片引句是否是文本的子串）：car 10/10，sigma 8/10，atomic_red_team 8/10，attack 7/10，nist_a 7/10，nist_b 7/10，ocsf 5/10，d3fend_paper 4/10，atlas 未核对。
没有对上的引句未逐条查原因。
