"""Build fedguard/kb/relations.yaml and the `runs` of scenarios from what exists on disk.

  level 1  from DeepSeek's reading of the defense papers' cards (survey/harvest/2026-10-10/claims/items):
           the paper evaluated its method against an attack of that threat technique. A claim, not a result.
  level 2  from method sweeps (experiments/fedllm_attack/methods_sweep.sh): the implementation ran end to end
           in a scenario that contains the threat and reported no plugin error. Says nothing about effect.
Only pairs that meet through the artifacts (kb.link) get a level-2 relation.

A sweep run with SCENARIO=control (no attack) goes in with --control: its runs and the collateral measured by
control_summary.py are stored under scenario S-0000 and give no relation.

Usage: kb_relations.py <attack sweep dir> [more ...] [--control <control sweep dir>]
       e.g. runs/autodl/q35-batch2/q35_sweep_0.8B --control runs/autodl/q35-control/q35_control_0.8B
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fedguard import kb as kbmod  # noqa: E402

# sweep run name -> (scenario, plugin classes mounted in that run)
RUNS = {**{n: ("S-0001", [n]) for n in ("krum coordinate_median trimmed_mean foolsgold flame freqfed fldetector norm_clip mud_hog lomar mcd crfl "
                                         "safe_fedllm_client received_adapter_scan update_subspace_projection la_lora lisa_proximal safety_mix").split()},
        "safe_fedllm_step": ("S-0001", ["safe_fedllm_step", "safe_fedllm_step_trust"]), "bea": ("S-0001", ["safety_mix"]),
        "protegofed": ("S-0002", ["protegofed_client", "protegofed_server"]),
        **{n: ("S-0002", [n]) for n in ("spectral_signatures", "gradient_spectral_entropy", "activation_clustering", "onion")}}

argv = sys.argv[1:]
control = None
if "--control" in argv:
    control = Path(argv[argv.index("--control") + 1])
    del argv[argv.index("--control"):argv.index("--control") + 2]
kb = kbmod.load(check=False)
by_class = {e["class"]: i for i, e in kb.implementations.items() if "class" in e}
by_source = defaultdict(list)
for i, e in kb.implementations.items():
    if "class" in e:
        for s in e["sources"]:
            by_source[s].append(i)

relations, skipped = [], []
for f in sorted((ROOT / "survey/harvest/2026-10-10/claims/items").glob("*.md")):
    m = re.findall(r"```json\s*(.*?)```", f.read_text(encoding="utf-8"), re.S)
    try:
        j = json.loads(m[-1])
    except (IndexError, json.JSONDecodeError):
        skipped.append(f.stem)
        continue
    for ev in j.get("evaluated", []):
        if ev.get("threat") not in kb.threats:
            continue
        for i in by_source.get(f.stem, []):
            relations.append({"implementation": i, "threat": ev["threat"], "level": 1, "basis": f.stem,
                              "note": f"{ev.get('attack_as_named_in_paper', '')}; {ev.get('setting', '')}; claimed: {ev.get('claimed_effect', '')}"[:400]})

runs = defaultdict(lambda: defaultdict(list))
for d in map(Path, argv):
    for line in (d / "status.tsv").read_text().splitlines():
        name, status, _ = line.split("\t")
        if name in RUNS and status == "ok":
            scenario, classes = RUNS[name]
            for c in classes:
                runs[scenario][by_class[c]].append(str((d / name).resolve().relative_to(ROOT)) if (d / name).resolve().is_relative_to(ROOT) else str(d / name))
for scenario, per_impl in runs.items():
    for i, paths in sorted(per_impl.items()):
        for t in kb.scenarios[scenario]["threats"]:
            if kb.link(i, t):
                relations.append({"implementation": i, "threat": t, "level": 2, "basis": "ran end to end without plugin errors; effect not assessed",
                                  "scenario": scenario, "runs": sorted(paths)})

results = {}
if control is not None:
    rel = lambda p: str(p.resolve().relative_to(ROOT)) if p.resolve().is_relative_to(ROOT) else str(p)  # noqa: E731
    measured = json.loads((control / "control.json").read_text())
    keep = ("client_rounds_excluded", "weight_shift", "samples_masked", "samples_rewritten", "samples_added", "gradient_norm_ratio",
            "updates_transformed", "global_replaced", "loss_vs_baseline", "client_rounds", "samples")
    for name, m in measured.items():
        if name in RUNS and m["status"] == "ok":
            for c in RUNS[name][1]:
                runs["S-0000"][by_class[c]].append(rel(control / name))
                results.setdefault(by_class[c], {k: m[k] for k in keep if m.get(k) is not None})
scen = yaml.safe_load((kbmod.HERE / "scenarios.yaml").read_text(encoding="utf-8"))
text = (kbmod.HERE / "scenarios.yaml").read_text(encoding="utf-8")
head = text[:text.index("S-0000:")]
for s, e in scen.items():
    if s in runs:
        e["runs"] = {i: sorted(p) for i, p in sorted(runs[s].items())}
    if s == "S-0000" and results:
        e["status"], e["results"] = "run", dict(sorted(results.items()))
(kbmod.HERE / "scenarios.yaml").write_text(head + yaml.safe_dump(scen, allow_unicode=True, sort_keys=False, width=160), encoding="utf-8")
relations.sort(key=lambda r: (r["implementation"], r["threat"], r["level"]))
(kbmod.HERE / "relations.yaml").write_text(
    "# Generated by experiments/eval/kb_relations.py; do not edit by hand.\n"
    "# level 1: the source paper evaluated against an attack of this threat technique (as read from the paper's card by DeepSeek).\n"
    "# level 2: ran end to end in a scenario containing the threat; effect not assessed.\n"
    + yaml.safe_dump(relations, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
print(f"{len(relations)} relations ({sum(r['level'] == 1 for r in relations)} at level 1, {sum(r['level'] == 2 for r in relations)} at level 2); "
      f"unparsed claim files: {skipped}")
