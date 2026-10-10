"""Fit the linear LoRA probe Safe-FedLLM needs, from recorded runs whose malicious clients are known.

Usage: fit_lora_probe.py <out.safetensors> <record_run_dir>:<malicious ids, comma-separated> [more ...] [--rounds N]

Feature: fedguard.methods.shared.first_layer_b_feature of each upload against the round's broadcast LoRA
(this round's change of the first layer's B matrices, L2-normalized). Uses the first N recorded rounds
(default 10, as in the paper). Prints the training accuracy; a probe fitted on one setting has to be
checked on runs it has not seen before it means anything.
"""
import sys
from pathlib import Path

import torch
from safetensors.torch import save_file

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fedguard.methods.shared import first_layer_b_feature  # noqa: E402
from fedguard.ops import probe  # noqa: E402
from fedguard.recorder.store import Recorder  # noqa: E402

argv = sys.argv[1:]
rounds = 10
if "--rounds" in argv:
    i = argv.index("--rounds")
    rounds = int(argv[i + 1])
    del argv[i:i + 2]
out, runs = argv[0], argv[1:]
X, y = [], []
for item in runs:
    path, bad = item.rsplit(":", 1)
    bad = set(bad.split(","))
    rec = Recorder(Path(path).parent, Path(path).name)
    for t in [t for t in rec.rounds() if rec.clients(t)][:rounds]:
        base = rec.load_base(t)
        for cid in rec.clients(t):
            X.append(first_layer_b_feature(rec.load_update(t, cid), base))
            y.append(1.0 if cid in bad else 0.0)
X, y = torch.stack(X), torch.tensor(y, dtype=torch.float64)
p = probe.fit_logistic(X, y)
pred = probe.apply_logistic(p, X)
acc = float(((pred > 0.5).double() == y).double().mean())
print(f"{len(y)} uploads ({int(y.sum())} malicious), feature dimension {X.shape[1]}, training accuracy {acc:.3f}")
print(f"mean probability: malicious {float(pred[y == 1].mean()):.3f}, benign {float(pred[y == 0].mean()):.3f}")
save_file({k: v.contiguous() for k, v in p.items()}, out)
print(f"saved {out}")
