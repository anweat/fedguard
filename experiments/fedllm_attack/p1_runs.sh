#!/usr/bin/env bash
# P1 feature runs: Qwen2.5-0.5B, 10 clients, full participation, Dolly Dirichlet(0.5).
#   c0: 10 benign clients            c1: 9 benign + 1 MaliciousGen client (index 9)
# Env: OUT, ROUNDS, RUNS ("c0 c1"), MODEL, EXTRA (extra flags, e.g. "--exp_precision bf16" on CUDA)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/fl311/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/p1}"
ROUNDS="${ROUNDS:-20}"
MODEL="${MODEL:-$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 16 --peft_lora_alpha 32 --gradient_checkpointing False
  --learning_rate 1e-4 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps 5
  --num_rounds "$ROUNDS" --sample_clients 10 --fed_alg fedavg --template alpaca --logging_steps 5
  --num_data_per_client 300 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names _ --benign_num_clients 0 --malicious_dataset_names _ --malicious_num_clients 0
  --exp_benign dolly --exp_split dirichlet --exp_alpha 0.5 --exp_pool_per_client 300 --exp_pad_to 256
  --guard_modules effect_stats,factor_stats --guard_record "$OUT/records")
read -r -a EXTRA_ARGS <<< "${EXTRA:-}"
COMMON+=(${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"})   # bash 3.2 (macOS) safe with set -u
RUNS="${RUNS:-c0 c1}"
mkdir -p "$OUT"
run() { local name=$1; shift; echo "$(date +%T) start $name"; "$PY" "$ROOT/experiments/fedllm_attack/run_guarded.py" \
  "${COMMON[@]}" "$@" --output_dir "$OUT/$name" > "$OUT/$name.log" 2>&1; echo "$(date +%T) done $name"; }
for r in $RUNS; do case $r in
  c0) run c0 --exp_benign_clients 10 ;;
  c1) run c1 --exp_benign_clients 9 --exp_malicious maliciousgen --exp_malicious_clients 1 ;;
esac; done
