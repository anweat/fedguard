#!/usr/bin/env bash
# Cost of client-side capture in a real MPS/CUDA training run: Qwen2.5-0.5B, 10 clients, full participation,
# 5 steps x batch 4 x length 256 per client (the P1 setting). Runs one after another, never in parallel.
#   off      server-side record only
#   record   + every client keeps its own record
#   plugins  + local_centroid on clients and centroid_consensus on the server
# Env: OUT, ROUNDS (default 3), EXTRA
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/client_capture_timing}"
ROUNDS="${ROUNDS:-3}"
MODEL="${MODEL:-$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 16 --peft_lora_alpha 32 --gradient_checkpointing False
  --learning_rate 1e-4 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps 5
  --num_rounds "$ROUNDS" --sample_clients 10 --fed_alg fedavg --template alpaca --logging_steps 1
  --num_data_per_client 300 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names _ --benign_num_clients 0 --malicious_dataset_names _ --malicious_num_clients 0
  --exp_benign dolly --exp_split dirichlet --exp_alpha 0.5 --exp_pool_per_client 300 --exp_pad_to 256
  --exp_benign_clients 10 --guard_fail_policy closed)
read -r -a EXTRA_ARGS <<< "${EXTRA:-}"
COMMON+=(${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"})
rm -rf "$OUT"; mkdir -p "$OUT"
run() { local name=$1; shift; local t0=$SECONDS; "$PY" "$ROOT/experiments/fedllm_attack/run_guarded.py" "${COMMON[@]}" "$@" \
  --output_dir "$OUT/$name" --guard_record "$OUT/rec_$name" > "$OUT/$name.log" 2>&1; echo "$name wall $((SECONDS - t0)) s"; }
run off
run record --guard_client_record 1
run plugins --guard_client_record 1 --guard_client_modules local_centroid --guard_modules centroid_consensus
"$PY" - "$OUT" <<'PY'
import statistics
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from fedguard.recorder.audit import compare_sides
from fedguard.recorder.query import RunRecord
out = Path(sys.argv[1])
for n in ("off", "record", "plugins"):
    r = RunRecord(out / f"rec_{n}", next((out / f"rec_{n}").iterdir()).name)
    metas = [r.server.load_round(t)["meta"] for t in r.rounds()]
    train = [v for m in metas for v in m["train_s"].values()]
    cap = [v for m in metas for v in m.get("capture_s", {}).values()]
    line = f"{n:8s} train median {statistics.median(train):.2f} s/client (first round excluded: {statistics.median([v for m in metas[1:] for v in m['train_s'].values()]):.2f})"
    if cap:
        line += f" | capture median {statistics.median(cap) * 1e3:.0f} ms, max {max(cap) * 1e3:.0f} ms = {100 * statistics.median(cap) / statistics.median(train):.2f}% of training"
        rows = compare_sides(r.root, r.run_id)
        line += f" | sides {len(rows)} compared, {sum(not x['match'] for x in rows)} mismatched, integrity problems {sum(len(v) for v in r.verify().values())}"
    disk = sum(p.stat().st_size for p in (out / f"rec_{n}").rglob("*") if p.is_file()) / 2**20
    print(line + f" | record {disk:.0f} MB")
    if n == "plugins":
        cid = r.client_ids()[0]
        down = [t for t in r.rounds(cid) if "centroid_consensus.centroid" in r.client(cid).load_round(t)["meta"]["messages"]]
        scored = [t for t in r.rounds(cid) if any(f["scores"] for f in r.client(cid).load_round(t)["findings"])]
        print(f"         channel: consensus reached {cid} in rounds {down}; samples scored in rounds {scored}")
PY
