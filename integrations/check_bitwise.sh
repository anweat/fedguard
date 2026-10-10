#!/usr/bin/env bash
# Does mounting the library leave a host's training untouched? For one host, three short runs on the CPU:
#   upstream          the host's own main_sft.py, unmodified
#   example           integrations/<host>/main_sft_guard.py with nothing mounted
#   example_plugins   the same with server and client plugins mounted but not allowed to act, records on
# The final global LoRA of the last two has to equal upstream's bit for bit.
#   check_bitwise.sh openfedllm | fedllm_attack
# Env: OUT, MODEL (default: the cached Qwen2.5-0.5B-Instruct), FG_ENV (default fl311)
set -euo pipefail
HOST="${1:?host: openfedllm or fedllm_attack}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/bitwise_$HOST}"
MODEL="${MODEL:-$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)}"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 8 --peft_lora_alpha 16 --gradient_checkpointing False
  --learning_rate 5e-5 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps 2
  --num_rounds 3 --sample_clients 2 --fed_alg fedavg --template alpaca --logging_steps 1 --device cpu)
rm -rf "$OUT"; mkdir -p "$OUT"
case "$HOST" in
  fedllm_attack)
    UP="$ROOT/external/FedLLM-Attack"
    COMMON+=(--num_data_per_client 16 --local_data_dir "$UP/gen_data" --benign_dataset_names Wildchat7_BT3 --benign_num_clients 3
             --malicious_dataset_names Wildchat7_Malicious3 --malicious_num_clients 1) ;;
  openfedllm)
    UP="$ROOT/external/OpenFedLLM"
    # OpenFedLLM takes a dataset by its hub name; a made-up one in the same column layout stands in for it here
    "$PY" "$ROOT/integrations/arith_dataset.py" "$OUT/data/vicgalle/alpaca-gpt4" 256
    COMMON+=(--dataset_name vicgalle/alpaca-gpt4 --local_data_dir "$OUT/data/" --dataset_sample 256 --num_clients 4) ;;
  *) echo "unknown host $HOST"; exit 2 ;;
esac
run() { local name=$1; shift; mkdir -p "$OUT/$name"; "$PY" "$@" "${COMMON[@]}" --output_dir "$OUT/$name" > "$OUT/$name.log" 2>&1 || { tail -5 "$OUT/$name.log"; exit 1; }; ls -d "$OUT/$name"/*/; }
A=$(run upstream "$ROOT/integrations/launch_upstream.py" --upstream_dir "$UP")
B=$(run example "$ROOT/integrations/$HOST/main_sft_guard.py")
C=$(run example_plugins "$ROOT/integrations/$HOST/main_sft_guard.py" --guard_record "$OUT/records" \
  --guard_modules effect_stats,krum --guard_client_modules local_centroid --guard_apply 0)
"$PY" - "$HOST" "$A" "$B" "$C" "$OUT/records" <<'PYEOF'
import sys
from pathlib import Path
import torch
from safetensors.torch import load_file
host, (up, ex, exp) = sys.argv[1], (load_file(f"{d}final_global.safetensors") for d in sys.argv[2:5])
same = lambda a, b: a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a)  # noqa: E731
moved = sum(float(v.double().norm()) for v in up.values()) > 0
recorded = len(list(Path(sys.argv[5]).glob("*/round_*/round.json")))
ok = same(up, ex) and same(up, exp) and moved and recorded > 0
print(f"[{host}] nothing mounted: identical to upstream {same(up, ex)}; plugins mounted, not acting: identical {same(up, exp)}; "
      f"rounds recorded {recorded}", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
PYEOF
