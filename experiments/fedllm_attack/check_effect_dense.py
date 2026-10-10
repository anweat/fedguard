"""P1 acceptance: on recorded real LoRA uploads, effect-space features from the 2r algorithm equal
the ones computed by materializing every d_out x d_in increment.

Usage: check_effect_dense.py <record_run_dir> [round] [lora_scale]
"""
import math
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fedguard.ops.lowrank import LowRank, gram  # noqa: E402
from fedguard.recorder.store import Recorder  # noqa: E402
from fedguard.views.updates import lora_modules  # noqa: E402

run = Path(sys.argv[1])
t = int(sys.argv[2]) if len(sys.argv) > 2 else 1
scale = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
rec = Recorder(run.parent, run.name)
base = {k: v.double() for k, v in rec.load_base(t).items()}
clients = rec.clients(t)
ups = {c: {k: v.double() for k, v in rec.load_update(t, c).items()} for c in clients}
mods = lora_modules(base)

t0 = time.perf_counter()
G_low = sum(gram([LowRank.increment(ups[c][m + ".lora_B.weight"], ups[c][m + ".lora_A.weight"],
                                    base[m + ".lora_B.weight"], base[m + ".lora_A.weight"], scale) for c in clients])
            for m in mods)
t_low = time.perf_counter() - t0

t0 = time.perf_counter()
dense = torch.stack([torch.cat([(scale * (ups[c][m + ".lora_B.weight"] @ ups[c][m + ".lora_A.weight"]
                                          - base[m + ".lora_B.weight"] @ base[m + ".lora_A.weight"])).flatten()
                                for m in mods]) for c in clients])
G_dense = dense @ dense.T
t_dense = time.perf_counter() - t0

rel = float((G_low - G_dense).abs().max() / G_dense.abs().max())
print(f"round {t}: {len(clients)} clients x {len(mods)} modules, dense effect dim {dense.shape[1] / 1e6:.1f}M/client")
print(f"  max relative diff of Gram (2r vs dense): {rel:.2e}   {'OK' if rel < 1e-5 else 'MISMATCH'}")
print(f"  time: 2r {t_low:.3f}s   dense {t_dense:.3f}s   (float64, CPU)")
sys.exit(0 if rel < 1e-5 else 1)
