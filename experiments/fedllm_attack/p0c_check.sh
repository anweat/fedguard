#!/usr/bin/env bash
# P0c acceptance: upstream vs guarded (record only) vs guarded (all built-in modules, honest reports).
# Runs on CPU with Qwen2.5-0.5B-Instruct; a few minutes on a laptop.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/p0c}"
MODEL="${MODEL:-$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 8 --peft_lora_alpha 16 --gradient_checkpointing False
  --learning_rate 5e-5 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps 2
  --num_rounds 3 --sample_clients 2 --fed_alg fedavg --template alpaca --logging_steps 1
  --num_data_per_client 16 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names Wildchat7_BT3 --benign_num_clients 3
  --malicious_dataset_names Wildchat7_Malicious3 --malicious_num_clients 1 --device cpu)
rm -rf "$OUT"; mkdir -p "$OUT"
run() { local name=$1; shift; "$PY" "$@" "${COMMON[@]}" --output_dir "$OUT/$name" > "$OUT/$name.log" 2>&1; ls -d "$OUT/$name"/*/; }
UP=$(run upstream "$ROOT/experiments/fedllm_attack/launch_upstream.py")
REC=$(run record_only "$ROOT/experiments/fedllm_attack/run_guarded.py" --guard_record "$OUT/records")
ALL=$(run all_modules "$ROOT/experiments/fedllm_attack/run_guarded.py" --guard_record "$OUT/records" \
  --guard_modules effect_stats,factor_stats,robust_outlier,report_guard)
echo "== record only =="
"$PY" "$ROOT/experiments/fedllm_attack/verify_p0c.py" "$UP" "$REC" "$OUT/records/$(basename "$REC")"
echo "== all built-in modules, honest reports =="
"$PY" "$ROOT/experiments/fedllm_attack/verify_p0c.py" "$UP" "$ALL" "$OUT/records/$(basename "$ALL")"
