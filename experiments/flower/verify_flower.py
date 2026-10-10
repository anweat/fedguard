"""Replay Flower's FedAvg (aggregate_arrayrecords) from guard records and compare bit for bit.

Usage: verify_flower.py <record_run_dir> <final.safetensors>
"""
import sys
from pathlib import Path

import numpy as np
from safetensors.torch import load_file

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fedguard.recorder.store import Recorder  # noqa: E402

run, final = Path(sys.argv[1]), load_file(sys.argv[2])
rec = Recorder(run.parent, run.name)
ok = True
rounds = [t for t in rec.rounds() if (rec.dir / f"round_{t:04d}" / "round.json").exists()]
for i, t in enumerate(rounds):
    meta = rec.load_round(t)["meta"]
    weights = meta["weights"]                       # insertion order = order passed to the inner strategy
    if not weights:
        continue
    total = sum(weights.values())
    agg = {}
    for cid, w in weights.items():                  # same expression and order as flwr aggregate_arrayrecords
        f = w / total
        for k, v in rec.load_update(t, cid).items():
            v = v.numpy()
            if k not in agg:
                agg[k] = v * f
            else:
                agg[k] += v * f
    target = {k: v.numpy() for k, v in (rec.load_base(rounds[i + 1]) if i + 1 < len(rounds) else final).items()}
    same = all(np.array_equal(agg[k].astype(target[k].dtype), target[k]) for k in target)
    print(f"round {t}: aggregated={list(weights)} weights={list(weights.values())} replay==next: {same}")
    ok &= same
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
