"""Assemble one text bundle per framework from the fetched primary documents (src/ -> text/)."""
import sys, yaml, json, re
from pathlib import Path
root = Path(sys.argv[1]); src, out = root / "src", root / "text"
R = lambda n: (src / n).read_text(encoding="utf-8", errors="replace")
def doc(title, body): return f"\n\n===== 文档：{title} =====\n\n{body}"

# ATLAS: schema by example, full lists of names, full entries for training-time techniques
d = yaml.safe_load(R("atlas_data.yaml"))
rel = d["relationships"]
dump = lambda o: yaml.safe_dump(o, allow_unicode=True, sort_keys=False, width=200)
keys = re.compile(r"poison|backdoor|train|supply chain|fine-tun|federat|model|data", re.I)
tech = d["techniques"]
lines = [f"{k} | {v['name']} | maturity={v.get('maturity')} | rel={json.dumps(rel.get(k, {}), ensure_ascii=False)[:300]}" for k, v in tech.items()]
full = {k: v for k, v in tech.items() if re.search(r"poison|backdoor|supply chain|fine-tun|federat", v["name"] + v["description"][:400], re.I)}
mit = {k: {**{f: v.get(f) for f in ("name", "lifecycle-phases", "categories")}, "description": v["description"][:500], "relationships": rel.get(k)} for k, v in d["mitigations"].items()}
cs = next(iter(d["case-studies"].items()))
atlas = doc("atlas-data README", R("atlas_readme.md")) + doc("ATLAS-2026.09.yaml 顶层键与数量", json.dumps({k: (len(v) if hasattr(v, "__len__") and not isinstance(v, str) else v) for k, v in d.items()}, ensure_ascii=False)) \
    + doc("collection 与 matrix", dump({"collection": d["collection"], "matrix": d["matrix"]})) + doc("全部 tactics", dump(d["tactics"])) \
    + doc("全部 techniques 的编号、名称、成熟度与关系（每行一条）", "\n".join(lines)) \
    + doc(f"与投毒、后门、供应链、微调有关的 {len(full)} 个 technique 完整条目", dump(full)[:120000]) \
    + doc("全部 mitigations（描述截到 500 字符）及其关系", dump(mit)) + doc("一个 case study 完整条目及其关系", dump({cs[0]: cs[1], "relationships": rel.get(cs[0])})) \
    + doc("其余顶层键的首个条目", dump({k: (dict(list(v.items())[:1]) if isinstance(v, dict) else v) for k, v in d.items() if k not in ("techniques", "tactics", "mitigations", "case-studies", "relationships", "collection", "matrix")})[:20000])
(out / "atlas.txt").write_text(atlas)
(out / "attack.txt").write_text(doc("MITRE ATT&CK: Design and Philosophy (2020)", (out / "attack_design.txt").read_text()) + doc("mitre/cti USAGE.md（STIX 表示）", R("attack_stix_usage.md")))
(out / "sigma.txt").write_text(doc("Sigma Rules Specification", R("sigma_rules_spec.md")) + doc("Sigma Correlation Rules Specification", R("sigma_correlation_spec.md")))
art = yaml.safe_load(R("art_T1003.yaml")); art["atomic_tests"] = art["atomic_tests"][:3]
(out / "atomic_red_team.txt").write_text(doc("README", R("art_readme.md")) + doc("atomic_red_team/models.py（原子测试的数据模型）", R("art_models.py")) + doc("Wiki: Contributing", R("art_wiki_contrib.md")) + doc("atomics/T1003.001/T1003.001.yaml（前 3 个测试）", dump(art)))
(out / "ocsf.txt").write_text(doc("Understanding OCSF", R("ocsf_understanding.md")))
(out / "car.txt").write_text(doc("CAR README", R("car_readme.md")) + doc("CAR Data Model", R("car_datamodel.md")) + doc("分析条目示例 CAR-2013-04-002", R("car_example.yaml")))
n = (out / "nist_ai_100_2.txt").read_text(); cut = n.find("\n3.", len(n) // 3)
i = n.find("Generative AI Taxonomy", len(n) // 4); i = i if i > 0 else len(n) // 2
(out / "nist_a.txt").write_text(doc("NIST AI 100-2 E2025，前半（至预测式 AI 部分结束）", n[:i])); (out / "nist_b.txt").write_text(doc("NIST AI 100-2 E2025，后半（生成式 AI 起）", n[i:]))
(out / "d3fend_paper.txt").write_text(doc("Toward a Knowledge Graph of Cybersecurity Countermeasures (D3FEND)", (out / "d3fend.txt").read_text()))
for f in ("attack_design.txt", "d3fend.txt", "nist_ai_100_2.txt"): (out / f).unlink()
for f in sorted(out.glob("*.txt")): print(f.name, len(f.read_text()))
