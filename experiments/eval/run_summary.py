"""What every plugin of a recorded run did: how often it ran, on which side and stage, whether it failed,
what it changed. A check that a method runs end to end, not a measure of how well it works.

Usage: run_summary.py <record root or run dir> [more ...]     exit status 1 if any plugin reported an error
"""
import json
import sys
from collections import defaultdict
from pathlib import Path


def rounds(d: Path):
    return sorted(p for p in d.glob("round_*") if (p / "round.json").exists())


def summarize(run: Path) -> int:
    rows, errors = defaultdict(lambda: defaultdict(float)), []
    sides = [("server", run)] + [(c.name, c) for c in sorted((run / "clients").glob("*")) if c.is_dir()]
    changed, proposed = defaultdict(int), defaultdict(int)
    for side, d in sides:
        for r in rounds(d):
            rec = json.loads((r / "round.json").read_text())
            if side == "server":
                dec = rec.get("decision") or {}
                changed["uploads rejected on arrival"] += len(rec.get("rejected") or {})
                changed["rounds with clients excluded"] += bool(dec.get("excluded"))
                changed["rounds with clients reweighted"] += bool(dec.get("weights"))
            for f in rec.get("findings", []):
                k = ("server" if side == "server" else "client", f["module"], f.get("stage", f.get("hook")))
                row = rows[k]
                row["calls"] += 1
                row["scored"] += len(f.get("scores") or {})
                row["seconds"] += (f.get("cost") or {}).get("seconds", 0.0)
                for a in f.get("actions") or []:
                    row["actions"] += 1
                    applied = a.get("applied", True) if isinstance(a, dict) else True     # older records have no flag
                    (changed if applied else proposed)[f"{f['module']}: {a.get('action', a) if isinstance(a, dict) else a}"] += 1
                if f.get("error"):
                    row["errors"] += 1
                    errors.append(f"{side} round {rec.get('round')} {f['module']}@{k[2]}: {str(f['error'])[:300]}")
                row["last"] = json.dumps(f.get("evidence") or {}, ensure_ascii=False)[:110]
    print(f"== {run}")
    print(f"{'side':7s}{'plugin':28s}{'stage':24s}{'calls':>6s}{'errors':>7s}{'scored':>8s}{'actions':>8s}{'seconds':>9s}  last evidence")
    for (side, name, stage), r in sorted(rows.items()):
        print(f"{side:7s}{name:28s}{stage:24s}{int(r['calls']):6d}{int(r['errors']):7d}{int(r['scored']):8d}{int(r['actions']):8d}"
              f"{r['seconds']:9.2f}  {r['last']}")
    if not rows:
        print("no findings recorded")
    print("changes: " + (", ".join(f"{k}={v}" for k, v in changed.items() if v) or "none"))
    if proposed:                                             # alert-only controls: recorded, not applied
        print("proposed only: " + ", ".join(f"{k}={v}" for k, v in proposed.items()))
    for e in errors[:10]:
        print("ERROR " + e)
    return len(errors) + (0 if rows else 1)


bad = 0
for arg in sys.argv[1:]:
    p = Path(arg)
    runs = [p] if rounds(p) else [d for d in sorted(p.iterdir()) if d.is_dir() and rounds(d)]
    if not runs:
        print(f"== {p}\nno recorded run")
        bad += 1
    for run in runs:
        bad += summarize(run)
sys.exit(1 if bad else 0)
