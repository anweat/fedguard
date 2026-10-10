"""Time what the capture base adds per client per round, using a real recorded LoRA upload as the object.

Usage: bench_capture.py <record_run_dir> [repeats]

Measures, with no plugins mounted:
  client side   record the received model, a data manifest, a step trace and the local result
  server side   record one upload (per client), the broadcast base and the aggregation result (per round)
and prints them next to the local training time the same record reports (meta.train_s), when present.
Disk writes go to a temporary directory on the same volume as the system temp dir.
"""
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fedguard.client import ClientGuard  # noqa: E402
from fedguard.core.types import ClientUpdate  # noqa: E402
from fedguard.recorder.store import Recorder  # noqa: E402
from fedguard.views.client import DataView  # noqa: E402

run_dir, repeats = Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 20
src = Recorder(run_dir.parent, run_dir.name)
t0 = next(t for t in src.rounds() if src.clients(t))
cid = src.clients(t0)[0]
base, upload = src.load_base(t0), src.load_update(t0, cid)
size_mb = sum(v.numel() * v.element_size() for v in upload.values()) / 2**20
samples = [{"instruction": f"question {i} " * 20, "response": f"answer {i} " * 40} for i in range(300)]
steps = 50
client_s, server_client_s, server_round_s = [], [], []
with tempfile.TemporaryDirectory() as tmp:
    for r in range(repeats):
        guard = ClientGuard("c0", recorder=Recorder(tmp, f"bench{r}", scope="c0"))
        t = time.perf_counter()
        guard.begin_round(0, base, data=DataView(samples, text_of=lambda s: s["instruction"] + s["response"]))
        for i in range(1, steps + 1):
            guard.on_step(i, {"loss": 1.0, "learning_rate": 1e-4, "grad_norm": 0.5})
        guard.before_upload(upload, {"num_examples": len(samples)})
        guard.end_round()
        client_s.append(time.perf_counter() - t)

        rec = Recorder(tmp, f"bench{r}")
        t = time.perf_counter()
        rec.write_update(ClientUpdate("c0", 0, upload, base))
        server_client_s.append(time.perf_counter() - t)
        t = time.perf_counter()
        rec.write_base(0, base)
        rec.write_aggregate(0, upload)
        server_round_s.append(time.perf_counter() - t)
    disk = sum(p.stat().st_size for p in Path(tmp, "bench0").rglob("*") if p.is_file())

ms = lambda xs: f"{statistics.median(xs) * 1e3:.1f} ms (max {max(xs) * 1e3:.1f})"  # noqa: E731
print(f"object: one LoRA state, {len(upload)} tensors, {size_mb:.1f} MB; {len(samples)} samples, {steps} steps; {repeats} repeats")
print(f"client side, per client per round:  {ms(client_s)}")
print(f"server side, per upload:            {ms(server_client_s)}")
print(f"server side, per round (base+agg):  {ms(server_round_s)}")
print(f"disk, one client-round on both sides plus base and aggregate: {disk / 2**20:.1f} MB")
train = [v for t in src.rounds() if (src.dir / f'round_{t:04d}' / 'round.json').exists()
         for v in (src.load_round(t)["meta"].get("train_s") or {}).values()]
if train:
    med = statistics.median(train)
    add = statistics.median(client_s) + statistics.median(server_client_s)
    print(f"recorded local training time: median {med:.2f} s per client per round -> capture adds {100 * add / med:.2f}%")
