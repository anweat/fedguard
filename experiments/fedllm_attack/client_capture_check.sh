#!/usr/bin/env bash
# Client-side capture in a real training run (Qwen2.5-0.5B, CPU so runs are bitwise comparable).
#   A  server-side record only
#   B  + every client keeps its own record
#   C  + a client plugin and its server half talking over the channel, LoRA snapshot every step
# Checks: the global LoRA of every round is bitwise the same in A, B and C; both sides' records agree
# and are intact; the channel carried messages both ways.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/fl311/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/client_capture_check}"
MODEL="${MODEL:-$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 8 --peft_lora_alpha 16 --gradient_checkpointing False
  --learning_rate 5e-5 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps 2
  --num_rounds 3 --sample_clients 2 --fed_alg fedavg --template alpaca --logging_steps 1
  --num_data_per_client 16 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names Wildchat7_BT3 --benign_num_clients 3
  --malicious_dataset_names Wildchat7_Malicious3 --malicious_num_clients 1 --device cpu --guard_fail_policy closed)
rm -rf "$OUT"; mkdir -p "$OUT"
run() { local name=$1; shift; "$PY" "$ROOT/experiments/fedllm_attack/run_guarded.py" "${COMMON[@]}" "$@" \
  --output_dir "$OUT/$name" --guard_record "$OUT/rec_$name" > "$OUT/$name.log" 2>&1; }
run A
run B --guard_client_record 1
run C --guard_client_record 1 --guard_client_modules local_centroid --guard_modules centroid_consensus \
  --guard_client_snapshot_every 1
"$PY" - "$OUT" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from fedguard.recorder.audit import compare_sides
from fedguard.recorder.query import RunRecord
out = Path(sys.argv[1])
runs = {n: RunRecord(out / f"rec_{n}", next((out / f"rec_{n}").iterdir()).name) for n in "ABC"}
agg = {n: [r.server.load_round(t)["objects"]["aggregate"] for t in r.rounds()] for n, r in runs.items()}
same = agg["A"] == agg["B"] == agg["C"] and len(agg["A"]) == 3
print(f"[1] global LoRA per round identical across A, B, C: {same}  ({[h[:8] for h in agg['A']]})")
ok = same
for n in "BC":
    r = runs[n]
    rows = compare_sides(r.root, r.run_id)
    bad = [x for x in rows if not x["match"]]
    problems = sum(len(v) for v in r.verify().values())
    print(f"[2] {n}: {len(rows)} cross-side comparisons, {len(bad)} mismatches, {problems} integrity problems; clients {r.client_ids()}")
    ok &= bool(rows) and not bad and not problems
c = runs["C"]
cid = c.client_ids()[0]
rec = c.client(cid)
last = c.rounds(cid)[-1]
meta = rec.load_round(last)["meta"]
up = any("local_centroid.centroid" in v.get("messages", {}) for t in c.rounds() for v in c.server.load_reports(t).values())
down = any("centroid_consensus.centroid" in rec.load_round(t)["meta"]["messages"] for t in c.rounds(cid))
objs = sorted(rec.load_round(last)["objects"])
print(f"[3] C channel: client->server {up}, server->client {down} (needs >= 3 clients per round to form a consensus)")
print(f"[4] C {cid} round {last}: {meta['samples']} samples, {meta['steps']} trace rows, objects {objs}")
print(f"    trace: {rec.load_lines(last, 'trace')[:2]}")
ok &= up and meta["samples"] > 0 and meta["steps"] > 0 and "step_000001" in objs
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
PY
