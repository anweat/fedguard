#!/usr/bin/env bash
# Plugins on the original OpenFedLLM host, through its integration example (integrations/openfedllm). Benign
# made-up data, five clients. Answers: do plugins run and act on this host, on a real model?
#   server_all   every server-side plugin that needs no external resource, recording only
#   server_act   FLAME acting (clips updates, selects clients, replaces the aggregate)
#   client_all   client-side plugins, including those that need a model handle, recording only
#   client_act   masked samples and changed gradients, acting
#   handshake    ProtegoFed: announce and exchange before training
# Env: OUT, MODEL (a model directory), FG_ENV (default fl311), ROUNDS (2), STEPS (4), EXTRA
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/plugins_openfedllm}"
MODEL="${MODEL:?set MODEL to a model directory}"
rm -rf "$OUT"; mkdir -p "$OUT"; : > "$OUT/status.tsv"
"$PY" "$ROOT/integrations/arith_dataset.py" "$OUT/data/vicgalle/alpaca-gpt4" 400
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 16 --peft_lora_alpha 32 --gradient_checkpointing False
  --learning_rate 1e-4 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 128 --max_steps "${STEPS:-4}"
  --num_rounds "${ROUNDS:-2}" --num_clients 5 --sample_clients 5 --fed_alg fedavg --template alpaca --logging_steps 1
  --dataset_name vicgalle/alpaca-gpt4 --local_data_dir "$OUT/data/" --dataset_sample 400)
read -r -a EXTRA_ARGS <<< "${EXTRA:-}"
COMMON+=(${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"})
SERVER_ALL=effect_stats,factor_stats,robust_outlier,report_guard,norm_clip,krum,lomar,flame,freqfed,coordinate_median,trimmed_mean,foolsgold,fldetector,mud_hog,mcd,crfl,safe_fedllm_step_trust,jump_rollback
CLIENT_ALL=spectral_signatures,activation_clustering,gradient_spectral_entropy,onion,lisa_proximal,la_lora,received_adapter_scan,local_centroid
run() {   # run <name> <args...>
  local name=$1 t0=$SECONDS status=ok; shift
  mkdir -p "$OUT/$name"
  "$PY" "$ROOT/integrations/openfedllm/main_sft_guard.py" "${COMMON[@]}" "$@" --output_dir "$OUT/$name" \
    --guard_record "$OUT/rec_$name" > "$OUT/$name.log" 2>&1 || status=crashed
  if [ "$status" = ok ]; then
    "$PY" "$ROOT/experiments/eval/run_summary.py" "$OUT/rec_$name" > "$OUT/$name.summary" 2>&1 || status=plugin_error
  fi
  find "$OUT/rec_$name" "$OUT/$name" -name '*.safetensors' -delete 2>/dev/null || true
  printf '%s\t%s\t%s\n' "$name" "$status" "$((SECONDS - t0))" >> "$OUT/status.tsv"
  echo "-- $name: $status, $((SECONDS - t0)) s"
  if [ "$status" = ok ]; then cut -c1-200 "$OUT/$name.summary"; else grep -v "Warning" "$OUT/$name.log" | tail -6; fi
}
run server_all --guard_modules "$SERVER_ALL" --guard_apply 0
run server_act --guard_modules flame --guard_apply 1
run client_all --guard_client_modules "$CLIENT_ALL" --guard_apply 0
run client_act --guard_client_modules spectral_signatures,lisa_proximal --guard_apply 1
run handshake --guard_modules protegofed_server --guard_client_modules protegofed_client --guard_apply 1
echo "== status"; cat "$OUT/status.tsv"
! grep -qv $'\tok\t' "$OUT/status.tsv"
