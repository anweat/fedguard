#!/usr/bin/env bash
# C1' demo: client 3 inflates its self-reported num_examples x100. No guard vs report_guard with a protocol cap.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/fl311/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/c1prime}"
MODEL="${MODEL:-$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 8 --peft_lora_alpha 16 --gradient_checkpointing False
  --learning_rate 5e-5 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps 2
  --num_rounds 3 --sample_clients 2 --fed_alg fedavg --template alpaca --logging_steps 1
  --num_data_per_client 16 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names Wildchat7_BT3 --benign_num_clients 3
  --malicious_dataset_names Wildchat7_Malicious3 --malicious_num_clients 1 --device cpu
  --guard_report inflate:3:100)
rm -rf "$OUT"; mkdir -p "$OUT"
run() { local name=$1; shift; "$PY" "$ROOT/experiments/fedllm_attack/run_guarded.py" "$@" "${COMMON[@]}" \
  --guard_record "$OUT/$name" --output_dir "$OUT/$name.out" > "$OUT/$name.log" 2>&1; }
run no_guard
run report_guard --guard_modules report_guard --guard_max_examples 16
"$PY" - "$OUT" <<'PY'
import json, sys
from pathlib import Path
for name in ("no_guard", "report_guard"):
    run = next((Path(sys.argv[1]) / name).iterdir())
    print(f"== {name}")
    for rj in sorted(run.glob("round_*/round.json")):
        r = json.loads(rj.read_text())
        w = r["meta"]["weights"]
        share = {c: round(v / sum(w.values()), 3) for c, v in w.items()}
        print(f"  round {r['round']}: weights={w} share={share} flags={r['decision']['flags']}")
PY
