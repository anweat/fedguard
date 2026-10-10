#!/usr/bin/env bash
# P2 benign baseline (C0 only): Qwen2.5-0.5B, 10 clients, full participation, 20 rounds.
# Splits x seeds; the seed drives the Dolly sample, the Dirichlet split and the LoRA initialization.
# Env: OUT, ROUNDS, SPLITS ("iid d0.1 d0.5 d1.0"), SEEDS ("1 2 3"), MODEL, EXTRA (e.g. "--exp_precision bf16")
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/fl311/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/p2}"
ROUNDS="${ROUNDS:-20}"
SPLITS="${SPLITS:-iid d0.1 d0.5 d1.0}"
SEEDS="${SEEDS:-1 2 3}"
MODEL="${MODEL:-$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 16 --peft_lora_alpha 32 --gradient_checkpointing False
  --learning_rate 1e-4 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps 5
  --num_rounds "$ROUNDS" --sample_clients 10 --fed_alg fedavg --template alpaca --logging_steps 5
  --num_data_per_client 300 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names _ --benign_num_clients 0 --malicious_dataset_names _ --malicious_num_clients 0
  --exp_benign dolly --exp_benign_clients 10 --exp_pool_per_client 300 --exp_pad_to 256
  --guard_modules effect_stats,factor_stats --guard_record "$OUT/records")
read -r -a EXTRA_ARGS <<< "${EXTRA:-}"
COMMON+=(${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"})   # bash 3.2 (macOS) safe with set -u
mkdir -p "$OUT"
for split in $SPLITS; do for seed in $SEEDS; do
  name="${split}_s${seed}"
  if ls "$OUT/$name"/*/training_loss.npy > /dev/null 2>&1 && [ -f "$OUT/$name.done" ]; then
    echo "$(date +%T) skip $name (done)"; continue
  fi
  rm -rf "${OUT:?}/$name"
  case $split in
    iid) split_args=(--exp_split iid) ;;
    d*)  split_args=(--exp_split dirichlet --exp_alpha "${split#d}") ;;
  esac
  echo "$(date +%T) start $name"
  "$PY" "$ROOT/experiments/fedllm_attack/run_guarded.py" "${COMMON[@]}" "${split_args[@]}" --seed "$seed" \
    --output_dir "$OUT/$name" > "$OUT/$name.log" 2>&1
  touch "$OUT/$name.done"
  echo "$(date +%T) done $name"
done; done
