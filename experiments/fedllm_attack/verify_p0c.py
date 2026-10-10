"""P0c acceptance checks.

  1. training_loss.npy of the guarded run equals the upstream run bit for bit
  2. final global LoRA equals the upstream run bit for bit
  3. replaying upstream's FedAvg formula over the records reproduces each next-round base exactly

Usage: verify_p0c.py <upstream_output_dir> <guarded_output_dir> <record_run_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import load_file

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fedguard.recorder.store import Recorder  # noqa: E402


def max_diff(a: dict, b: dict) -> float:
    return max(float((a[k].double() - b[k].double()).abs().max()) for k in a)


def main(upstream: Path, guarded: Path, record: Path) -> int:
    ok = True

    la, lb = np.load(upstream / "training_loss.npy"), np.load(guarded / "training_loss.npy")
    same = la.shape == lb.shape and np.array_equal(la, lb)
    print(f"[1] training loss identical: {same}  shape={la.shape}")
    ok &= same

    fa, fb = load_file(str(upstream / "final_global.safetensors")), load_file(str(guarded / "final_global.safetensors"))
    same = fa.keys() == fb.keys() and all(torch.equal(fa[k], fb[k]) for k in fa)
    print(f"[2] final global identical: {same}" + ("" if same else f"  max|diff|={max_diff(fa, fb):.3e}"))
    ok &= same

    rec = Recorder(record.parent, record.name)
    rounds = rec.rounds()
    replayed = 0
    for t in rounds:
        nxt = rec.dir / f"round_{t + 1:04d}" / "base.safetensors"
        if not (rec.dir / f"round_{t:04d}" / "round.json").exists() or not nxt.exists():
            continue
        meta = rec.load_round(t)["meta"]
        clients, weights = meta["aggregated"], {int(k): v for k, v in meta["weights"].items()}
        sampled = meta["sampled"]
        assert rec.clients(t) == sorted(f"client{c}" for c in sampled), f"round {t}: uploads != sampled clients"
        base, target = rec.load_base(t), rec.load_base(t + 1)
        if clients:
            ups = {c: rec.load_update(t, f"client{c}") for c in clients}
            total = sum(weights[c] for c in clients)
            # Same expression and order of operations as upstream global_aggregate (fedavg branch).
            replay = {k: sum([ups[c][k] * weights[c] / total for c in clients]) for k in base}
        else:
            replay = base
        same = all(torch.equal(replay[k], target[k]) for k in target)
        print(f"[3] round {t}: sampled={sampled} aggregated={clients} weights={weights} replay==next base: {same}"
              + ("" if same else f"  max|diff|={max_diff(replay, target):.3e}"))
        ok &= same
        replayed += 1
    ok &= replayed > 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(Path(p) for p in sys.argv[1:4])))
