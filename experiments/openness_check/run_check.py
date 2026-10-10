"""Run the trial plugins on synthetic LoRA uploads and report, per method, whether the contract carried it.

Usage: run_check.py     (no model, no training; a few seconds)
"""
import sys
import tempfile
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import make_base, perturb  # noqa: E402
from trial_plugins import *  # noqa: E402,F403
from fedguard import ClientUpdate, GuardRunner, RunSpec, Stage  # noqa: E402
from fedguard.client import ClientGuard  # noqa: E402
from fedguard.core.types import check_messages  # noqa: E402
from fedguard.recorder.store import Recorder  # noqa: E402
from fedguard.views.aggregate import AggregateView  # noqa: E402
from fedguard.views.client import DataView  # noqa: E402

SPEC, results = RunSpec("openness"), []


def report(name, ok, note):
    results.append((name, ok, note))
    print(f"{'OK     ' if ok else 'BLOCKED'}  {name}: {note}")


def uploads(t, base, n=6, attacker=5, factor=30.0):
    ups = [ClientUpdate(f"c{i}", t, perturb(base, 100 * t + i, 0.05), base, {"num_examples": 100.0}) for i in range(n)]
    ups[attacker].lora = {k: base[k] + factor * (v - base[k]) for k, v in ups[attacker].lora.items()}
    return ups


def server_round(runner, t, base, ups, rec=None):
    if rec is not None:
        rec.write_base(t, base)
        for u in ups:
            rec.write_update(u)
    runner.begin_round(t)
    ids = [u.client_id for u in ups]
    f = runner.run(Stage.SERVER_RECEIVE, ids, uploads=ups)
    f += runner.run(Stage.SERVER_AGGREGATE, ids, uploads=ups, aggregate=AggregateView(tuple(ids), {i: 100.0 for i in ids}, base))
    d = runner.decision()
    kept = [u for u in ups if u.client_id not in d.excluded]
    lora = {u.client_id: runner.transformed().get(u.client_id, u.lora) for u in kept}
    w = {u.client_id: d.weights.get(u.client_id, 100.0) for u in kept}
    total = sum(w.values()) or 1.0
    result = {k: sum(lora[c][k] * w[c] for c in lora) / total for k in base} if lora else base
    f += runner.run(Stage.SERVER_POST_AGGREGATE, list(w), uploads=ups, aggregate=AggregateView(tuple(ids), w, base, result))
    final = runner.replacement() or result
    runner.end_round()
    return f, d, final


def errors(findings):
    return [f"{f.module}: {f.error.splitlines()[-1]}" for f in findings if f.error]


base = make_base()
dist = lambda a, b: float(torch.sqrt(sum(((a[k] - b[k]).double() ** 2).sum() for k in a)))  # noqa: E731
honest = {k: sum(u.lora[k] for u in uploads(0, base)[:5]) / 5 for k in base}

f, d, final = server_round(GuardRunner([MultiKrum(f=1)], SPEC, apply_actions=True), 0, base, uploads(0, base))
report("Multi-Krum (select clients)", not errors(f) and d.excluded == {"c5"}, f"excluded {sorted(d.excluded)}")

f, d, final = server_round(GuardRunner([CoordinateMedian()], SPEC, apply_actions=True), 0, base, uploads(0, base))
report("Coordinate median (replace the aggregation rule)", not errors(f) and dist(final, honest) < dist(uploads(0, base)[5].lora, honest) / 20,
       f"distance of the global model from the honest mean {dist(final, honest):.3f}; only in factor space, see note in the plugin")

r = GuardRunner([FoolsGold()], SPEC, apply_actions=True)
for t in range(3):
    ups = uploads(t, base, attacker=5, factor=1.0)
    ups[4].lora = {k: v.clone() for k, v in ups[5].lora.items()}          # two sybils sending the same update
    f, d, _ = server_round(r, t, base, ups)
report("FoolsGold (cross-round state, reweight)", not errors(f) and d.weights["c4"] < 0.1 and d.weights["c0"] > 0.9,
       f"sybil weights {d.weights['c4']:.2f}/{d.weights['c5']:.2f}, honest {d.weights['c0']:.2f}")

root_update = lambda b: perturb(b, 100 * 0 + 0, 0.05)  # noqa: E731  stand-in for 'train on the root dataset'
r = GuardRunner([FLTrustScore(), FLTrustWeight()], SPEC, apply_actions=True, resources={"server_update": root_update})
f, d, final = server_round(r, 0, base, uploads(0, base))
report("FLTrust (root-data reference, normalize + weight)", not errors(f) and len(r.transformed()) == 6,
       f"expressible, but as two plugin classes joined by a feature; trust {[round(v, 2) for v in d.weights.values()]}")

with tempfile.TemporaryDirectory() as tmp:
    rec = Recorder(tmp, "openness")
    r = GuardRunner([UpdateConsistency()], SPEC, rec)
    for t in range(2):
        f, _, _ = server_round(r, t, base, uploads(t, base), rec)
    report("FLDetector-style consistency (raw history)", not errors(f) and len(f[0].scores) == 6,
           "works only when the run is recorded; no history view otherwise")

guard = ClientGuard("c0", GuardRunner([PerSampleGradientCentroid()], SPEC, side="client"))
[f] = guard.begin_round(0, base, data=DataView(["a", "b"]), model_handle=None)
size_ok = True
try:
    check_messages({"centroid": [0.0] * (896 * 16)})      # last-layer lora_B of Qwen2.5-0.5B at r=16
except ValueError:
    size_ok = False
report("ProtegoFed client half (per-sample gradients, centroid upload)", False,
       f"no model-handle interface on the client ({errors([f])[0][:70]}); a real centroid fits the channel: {size_ok}")

guard = ClientGuard("c0", GuardRunner([StepDeltaB()], SPEC, side="client"))
guard.begin_round(0, base)
guard.on_step(1, {"loss": 1.0})
report("Safe-FedLLM step level (LoRA after each step)", False, errors(guard.runner.findings)[0][:90])

attack = GuardRunner([ScalingAttack(10.0)], SPEC, side="client", apply_actions=True)
guard = ClientGuard("c0", attack)
guard.begin_round(0, base)
local = perturb(base, 1, 0.05)
guard.before_upload(local)
sent = guard.upload_state()
scaled = abs(dist(sent, base) / dist(local, base) - 10.0) < 1e-6
spy_saw = []


class Spy(GuardPlugin):  # noqa: F405
    name, at = "defender", Stage.CLIENT_POST_TRAIN

    def run(self, ctx):
        spy_saw.extend(f.module for f in ctx.upstream if f.actions)
        return ctx.findings()


g2 = ClientGuard("c0", GuardRunner([ScalingAttack(10.0), Spy()], SPEC, side="client", apply_actions=True))
g2.begin_round(0, base)
g2.before_upload(local)
report("Attack: update scaling at the upload boundary", scaled,
       f"upload scaled x10: {scaled}; but a co-mounted plugin can read the attack's record: {spy_saw}, "
       "and apply_actions is one switch for attack and defense alike")

g3 = ClientGuard("c0", GuardRunner([TriggerInjection()], SPEC, side="client", apply_actions=True))
[f] = g3.begin_round(0, base, data=DataView(["x", "y", "z"]))
report("Attack: data poisoning (add or rewrite samples)", False, errors([f])[0][:90])
print(f"\n{sum(ok for _, ok, _ in results)} of {len(results)} trials carried by the contract as it is")
