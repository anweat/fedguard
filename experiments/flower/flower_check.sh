#!/usr/bin/env bash
# Flower adapter checks in the real simulation engine (ray), synthetic LoRA clients, ~1 min each run.
#   A  honest: GuardStrategy(FedAvg) vs FedAvg differ only by float32 rounding
#   B  attack (node 3: update x20, num-examples x100): distance of the final model from the honest run
#   C  replay of Flower's FedAvg from the guard records is bitwise exact
#   E  the paired plugins' messages cross in both directions
#   D  the two sides' records agree on every broadcast and upload, and both records are intact
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/flower_check}"
rm -rf "$OUT"
for attack in 0 1; do for mode in plain guard; do
  FG_ATTACK=$attack "$PY" "$ROOT/experiments/flower/sim_synthetic.py" "$OUT/a$attack" $mode > "$OUT.a$attack.$mode.log" 2>&1
done; done
"$PY" - "$OUT" <<'PY'
import sys
from safetensors.torch import load_file
out = sys.argv[1]
L = lambda p: load_file(f"{out}/{p}")
hp, hg, ap, ag = L("a0/final_plain.safetensors"), L("a0/final_guard.safetensors"), L("a1/final_plain.safetensors"), L("a1/final_guard.safetensors")
rel = max(float((hp[k] - hg[k]).abs().max() / hp[k].abs().max()) for k in hp)
dist = lambda a: sum(float((a[k] - hp[k]).norm() ** 2) for k in a) ** 0.5
print(f"[A] honest guard vs plain: max rel diff {rel:.1e} ({'OK' if rel < 1e-5 else 'FAIL'})")
print(f"[B] attack: final-model distance from honest run  plain {dist(ap):.3f}  guard {dist(ag):.3f}")
PY
for a in 0 1; do echo -n "[C] a$a replay: "; "$PY" "$ROOT/experiments/flower/verify_flower.py" "$OUT/a$a/records/guard" "$OUT/a$a/final_guard.safetensors" | tail -1; done
for a in 0 1; do echo -n "[D] a$a sides: "; "$PY" - "$OUT/a$a/records" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from fedguard.recorder.audit import compare_sides
from fedguard.recorder.store import Recorder
root = sys.argv[1]
rows = compare_sides(root, "guard")
bad = [r for r in rows if not r["match"]]
problems = Recorder(root, "guard").verify()
for c in sorted((Path(root) / "guard" / "clients").iterdir()):
    problems += Recorder(root, "guard", scope=c.name).verify()
print(f"{len(rows)} comparisons, {len(bad)} mismatches, {len(problems)} integrity problems", "PASS" if rows and not bad and not problems else "FAIL")
PY
done
echo -n "[E] a0 channel: "; "$PY" - "$OUT/a0/records" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from fedguard.recorder.store import Recorder
root = sys.argv[1]
server = Recorder(root, "guard")
up = all("local_centroid.centroid" in r.get("messages", {}) for r in server.load_reports(1).values())
clients = [Recorder(root, "guard", scope=c.name) for c in sorted((Path(root) / "guard" / "clients").iterdir())]
down = all("centroid_consensus.centroid" in c.load_round(2)["meta"]["messages"] for c in clients)
scored = all(any(f["module"] == "local_centroid" and f["scores"] for f in c.load_round(2)["findings"]) for c in clients)
print(f"client->server {up}, server->client {down}, clients scored against the consensus {scored}", "PASS" if up and down and scored else "FAIL")
PY
# F: the handshake extension layer (changes Flower's round protocol; off in every check above). Every node
# announces 4 samples before training; the server's total has to come back to every node before it trains,
# and the run record has to say that the extension was on.
FG_HANDSHAKE=1 "$PY" "$ROOT/experiments/flower/sim_synthetic.py" "$OUT/hs" guard > "$OUT/hs.guard.log" 2>&1 || true
echo -n "[F] handshake extension: "; "$PY" - "$OUT/hs/records" "$OUT/hs.guard.log" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from fedguard.recorder.store import Recorder
root = Path(sys.argv[1])
if not (root / "guard" / "run.json").exists():
    print("the run did not start; see", sys.argv[2], "FAIL"); raise SystemExit
run = json.loads((root / "guard" / "run.json").read_text())
server = Recorder(root, "guard")
rounds = server.rounds()
pooled = [f["evidence"] for t in rounds for f in server.load_round(t)["findings"] if f["module"] == "pool"]
clients = [Recorder(root, "guard", scope=c.name) for c in sorted((root / "guard" / "clients").iterdir())]
got = [f["evidence"].get("total_from_server") for c in clients for t in c.rounds()
       for f in c.load_round(t)["findings"] if f["module"] == "hello" and f["stage"] == "client_pre_train"]
want = 4.0 * len(clients)
ok_server = len(pooled) == len(rounds) and all(e.get("announced") == len(clients) and e.get("total") == want for e in pooled)
ok_client = len(got) == len(rounds) * len(clients) and all(v == want for v in got)
warned = "HostExtensionWarning" in Path(sys.argv[2]).read_text()
print(f"recorded as extension {run.get('host_extensions')}, warning shown {warned}, server pooled {len(pooled)}/{len(rounds)} rounds, "
      f"nodes that trained with the answer {sum(v == want for v in got)}/{len(rounds) * len(clients)}",
      "PASS" if ok_server and ok_client and warned and run.get("host_extensions") == ["handshake"] else "FAIL")
PY
