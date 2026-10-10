#!/usr/bin/env bash
# Two published defenses on a real model, end to end through the runtime. A smoke test of the plumbing
# and a first reading of cost; far too small to say anything about how well the defenses work.
#   P  ProtegoFed: per-sample gradients, centroid exchange before training, masked samples
#      data: benign Dolly clients, a trigger-and-target backdoor in a fraction of every client's samples
#   S  Safe-FedLLM client level: a LoRA probe fitted on an earlier recorded run, applied to a new one
#      data: benign Dolly clients plus one client training on harmful data
# Env: OUT, MODEL, ROUNDS (default 2), CLIENTS (default 4), STEPS (default 6), PROBE_RUN (record dir with a
#      known malicious client, default the local P1 run), PROBE_BAD (default client9), EXTRA
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/defense_smoke}"
ROUNDS="${ROUNDS:-2}"; CLIENTS="${CLIENTS:-4}"; STEPS="${STEPS:-6}"
MODEL="${MODEL:-$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)}"
PROBE_RUN="${PROBE_RUN:-$(ls -d "$ROOT"/runs/p1/records/*/ 2>/dev/null | head -1 || true)}"   # empty when there is no such run
PROBE_BAD="${PROBE_BAD:-client9}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 16 --peft_lora_alpha 32 --gradient_checkpointing False
  --learning_rate 1e-4 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps "$STEPS"
  --num_rounds "$ROUNDS" --fed_alg fedavg --template alpaca --logging_steps 1
  --num_data_per_client 300 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names _ --benign_num_clients 0 --malicious_dataset_names _ --malicious_num_clients 0
  --exp_benign dolly --exp_split dirichlet --exp_alpha 0.5 --exp_pool_per_client 300 --exp_pad_to 256
  --guard_fail_policy closed --guard_client_record 1)
read -r -a EXTRA_ARGS <<< "${EXTRA:-}"
COMMON+=(${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"})
rm -rf "$OUT"; mkdir -p "$OUT"
run() { local name=$1; shift; local t0=$SECONDS; "$PY" "$ROOT/experiments/fedllm_attack/run_guarded.py" "${COMMON[@]}" "$@" \
  --output_dir "$OUT/$name" --guard_record "$OUT/rec_$name" > "$OUT/$name.log" 2>&1; echo "$name wall $((SECONDS - t0)) s"; }

echo "== P: ProtegoFed =="
run P --exp_benign_clients "$CLIENTS" --sample_clients "$CLIENTS" --exp_backdoor "0.2:cf mn bb:I have been triggered." \
  --guard_client_modules protegofed_client --guard_modules protegofed_server --guard_client_apply 1
"$PY" "$ROOT/experiments/eval/sample_filter_eval.py" "$OUT/rec_P" "$(ls -d "$OUT"/P/*/ | head -1)"

echo "== S: Safe-FedLLM, client level =="
if [ -n "$PROBE_RUN" ]; then
  "$PY" "$ROOT/experiments/fit_lora_probe.py" "$OUT/lora_probe.safetensors" "${PROBE_RUN%/}:$PROBE_BAD"
  run S --exp_benign_clients "$((CLIENTS - 1))" --exp_malicious maliciousgen --exp_malicious_clients 1 --sample_clients "$CLIENTS" \
    --seed 7 --guard_modules safe_fedllm_client --guard_probe_file "$OUT/lora_probe.safetensors"
  "$PY" - "$OUT/rec_S" "$((CLIENTS - 1))" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from fedguard.recorder.query import RunRecord
root, bad = Path(sys.argv[1]), f"client{sys.argv[2]}"
run = RunRecord(root, next(p.name for p in root.iterdir() if p.is_dir()))
print(f"malicious client: {bad} (it was not in the run the probe was fitted on)")
for t in run.rounds():
    rows = {r["subject"]: r["features"] for r in run.findings(plugin="safe_fedllm_client", round=t) if r["features"]}
    w = run.server.load_round(t)["meta"]["weights"]
    print(f"round {t}: " + "  ".join(f"{c}{'*' if c == bad else ''} p={f['malicious_probability']:.2f} w={f['safety_factor']:.2f}"
                                    for c, f in sorted(rows.items())) + f"  | aggregation weights {w}")
PY
else
  echo "no recorded run with a known malicious client found; set PROBE_RUN"
fi
