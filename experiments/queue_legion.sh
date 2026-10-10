#!/usr/bin/env bash
# Unattended experiment queue for legion (RTX 4050, WSL2). Start it from a terminal on legion:
#     wsl -d Ubuntu -- bash /root/innovation/experiments/queue_legion.sh
# and keep that window open. Every stage leaves a marker in runs/queue/, so re-running the command
# resumes after the last finished stage (unfinished training runs restart from scratch).
# Only one instance can run at a time (flock). Progress: runs/queue.log
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec 9> /tmp/fedguard_queue.lock
flock -n 9 || { echo "another queue instance is already running"; exit 1; }

PY="$ROOT/envs/fl311/.venv/bin/python"
Q="$ROOT/runs/queue"; mkdir -p "$Q"
LOG="$ROOT/runs/queue.log"
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_ENDPOINT=https://hf-mirror.com
M05=$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)
BF16=(--exp_precision bf16)

say() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
stage() {  # stage <name> <command...>: run once, record the outcome
  local name=$1; shift
  if [ -f "$Q/$name.done" ]; then say "skip  $name"; return 0; fi
  say "start $name"
  if "$@" >> "$Q/$name.out" 2>&1; then touch "$Q/$name.done"; say "done  $name"
  else say "FAIL  $name (see runs/queue/$name.out)"; fi
}
rec_of() { basename "$(ls -d "$1"/*/ | head -1)"; }   # output dir -> record dir name

# ----- common C1 configuration (same as P1 / P2) -----
c1_run() {  # c1_run <name> <mix> <seed>
  local out="$ROOT/runs/p3pre"
  rm -rf "${out:?}/$1"; mkdir -p "$out"
  "$PY" experiments/fedllm_attack/run_guarded.py --model_name_or_path "$M05" --use_peft --peft_lora_r 16 \
    --peft_lora_alpha 32 --gradient_checkpointing False --learning_rate 1e-4 --batch_size 4 \
    --gradient_accumulation_steps 1 --seq_length 256 --max_steps 5 --num_rounds 20 --sample_clients 10 \
    --fed_alg fedavg --template alpaca --logging_steps 5 --num_data_per_client 300 \
    --local_data_dir external/FedLLM-Attack/gen_data --benign_dataset_names _ --benign_num_clients 0 \
    --malicious_dataset_names _ --malicious_num_clients 0 --exp_benign dolly --exp_benign_clients 9 \
    --exp_split dirichlet --exp_alpha 0.5 --exp_pool_per_client 300 --exp_pad_to 256 \
    --exp_malicious maliciousgen --exp_malicious_clients 1 --exp_malicious_mix "$2" --seed "$3" \
    --guard_modules effect_stats,factor_stats --guard_record "$out/records" "${BF16[@]}" --output_dir "$out/$1"
}

safety() {  # safety <out json> <record dir or -> <rounds> <template>
  local rec=$2
  [ "$rec" = "-" ] && rec="$ROOT/runs/p2/records/_none"
  "$PY" experiments/eval/safety_eval.py --model "$M05" --record "$rec" --out "$1" --rounds="$3" \
    --n 100 --template "$4" --batch 16
}

safety_all() {
  local S="$ROOT/runs/safety"; mkdir -p "$S"
  safety "$S/base_alpaca.json" - -1 alpaca
  safety "$S/base_chat.json" - -1 chat
  local c0="$ROOT/runs/p2/records/$(rec_of "$ROOT/runs/p2/d0.5_s1")"
  safety "$S/c0_d0.5_s1_alpaca.json" "$c0" 0,5,10,15,20 alpaca
  safety "$S/c0_d0.5_s1_chat.json" "$c0" 0,5,10,15,20 chat
  for r in c1_m1.0_s1 c1_m0.3_s1 c1_m0.1_s1; do
    [ -d "$ROOT/runs/p3pre/$r" ] || continue
    safety "$S/${r}_alpaca.json" "$ROOT/runs/p3pre/records/$(rec_of "$ROOT/runs/p3pre/$r")" 0,5,10,15,20 alpaca
  done
}

analysis() {
  local c1="$ROOT/runs/p3pre/c1_m1.0_s1"
  mkdir -p runs/p2_figs
  "$PY" experiments/fedllm_attack/analyze_p2.py runs/p2 runs/p2_figs "$c1" runs/p3pre/records | tee runs/p2_figs/summary.md
}

model_15b() {
  HF_HUB_OFFLINE=0 "$PY" -c "from huggingface_hub import snapshot_download as d; print(d('Qwen/Qwen2.5-1.5B-Instruct', allow_patterns=['*.json','*.safetensors','*.txt']))"
}

run_15b() {
  local m15; m15=$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/* | head -1)
  OUT="$ROOT/runs/p2_1.5b" ROUNDS=10 SPLITS="d0.5" SEEDS="1" MODEL="$m15" \
    EXTRA="--exp_precision bf16 --exp_base_dtype bf16" experiments/fedllm_attack/p2_runs.sh
}

say "queue started (pid $$)"
stage p2        env OUT="$ROOT/runs/p2" EXTRA="--exp_precision bf16" experiments/fedllm_attack/p2_runs.sh
stage c1_m1.0_s1 c1_run c1_m1.0_s1 1.0 1
stage c1_m1.0_s2 c1_run c1_m1.0_s2 1.0 2
stage c1_m1.0_s3 c1_run c1_m1.0_s3 1.0 3
stage c1_m0.3_s1 c1_run c1_m0.3_s1 0.3 1
stage c1_m0.1_s1 c1_run c1_m0.1_s1 0.1 1
stage safety    safety_all
stage analysis  analysis
stage model_15b model_15b
stage run_15b   run_15b
say "queue finished"
