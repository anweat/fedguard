"""Score a sample-filtering defense against the experiment's ground truth.

Usage: sample_filter_eval.py <record_root> <output_dir containing truth.json>

Reads every client's record: the samples it announced each round (manifest) and the samples its plugins
proposed to mask. Compares with the poisoned-sample hashes in truth.json, which the plugins never saw.
Prints per-round and overall precision and recall, and what the plugins spent on the model.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fedguard.recorder.query import RunRecord  # noqa: E402

root, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
truth = {c: set(h) for c, h in json.loads((out_dir / "truth.json").read_text())["poisoned"].items()}
run = RunRecord(root, next(p.name for p in root.iterdir() if p.is_dir()))
tot = {"tp": 0, "fp": 0, "fn": 0, "n": 0, "poisoned": 0}
cost = {}
print("round client samples poisoned masked tp fp fn")
for cid in run.client_ids():
    rec = run.client(cid)
    for t in run.rounds(cid):
        seen = {r["hash"] for r in rec.load_lines(t, "manifest")}
        bad = seen & truth.get(cid, set())
        r = rec.load_round(t)
        masked = {h for f in r["findings"] for a in f.get("actions", []) if a["action"] == "mask_samples" for h in a["subjects"]}
        for f in r["findings"]:
            for k, v in f.get("cost", {}).items():
                cost[k] = cost.get(k, 0) + v
            cost["plugin_seconds"] = cost.get("plugin_seconds", 0) + f.get("elapsed_s", 0)
        tp, fp, fn = len(masked & bad), len(masked - bad), len(bad - masked)
        print(t, cid, len(seen), len(bad), len(masked), tp, fp, fn)
        for k, v in (("tp", tp), ("fp", fp), ("fn", fn), ("n", len(seen)), ("poisoned", len(bad))):
            tot[k] += v
prec = tot["tp"] / (tot["tp"] + tot["fp"]) if tot["tp"] + tot["fp"] else float("nan")
rec_ = tot["tp"] / (tot["tp"] + tot["fn"]) if tot["tp"] + tot["fn"] else float("nan")
print(f"overall: {tot['n']} samples, {tot['poisoned']} poisoned; precision {prec:.3f}, recall {rec_:.3f}")
train = [v for t in run.rounds() for v in (run.server.load_round(t)["meta"].get("train_s") or {}).values()]
cap = [v for t in run.rounds() for v in (run.server.load_round(t)["meta"].get("capture_s") or {}).values()]
print(f"model passes by client plugins: {json.dumps({k: round(v, 1) for k, v in cost.items()})}")
if train and cap:
    print(f"per client-round: training {sum(train) / len(train):.1f} s, capture and client plugins {sum(cap) / len(cap):.1f} s")
