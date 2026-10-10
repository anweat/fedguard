#!/usr/bin/env bash
# Every method that the entry point can supply with its resources, one short federated run each, on one
# model. Answers one question per method: does it run end to end on this model and act? Nothing here
# says how well a method defends: the runs are far too small for that.
#   scenario A (bad client): benign Dolly clients plus one client training on harmful data
#   scenario B (backdoor):   benign Dolly clients, a trigger-and-target backdoor in a fraction of every client's samples
# Runs on the instance only (bash 4+). Not covered: safe_lora (needs an alignment matrix from an aligned/unaligned
# model pair, which the entry point does not build).
# The last group (lisa, la_lora_dp) mounts at CLIENT_LOSS and runs with the trainer extension layer on: those runs
# are not the host's original training loop, and their records say so (run.json: host_extensions).
# Env: OUT, MODEL, ROUNDS (4), CLIENTS (5), STEPS (6), ONLY (space-separated run names), EXTRA, FG_ENV,
#      JOBS (runs at a time, default 1), SCENARIO (attack | control: all clients benign, no backdoor),
#      PROBE_FILE (a fitted Safe-FedLLM probe to use instead of fitting one on this sweep's stats run),
#      KEEP_TENSORS (set to keep the recorded LoRA tensors of every run)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/methods_sweep}"
ROUNDS="${ROUNDS:-4}"; CLIENTS="${CLIENTS:-5}"; STEPS="${STEPS:-6}"
MODEL="${MODEL:?set MODEL to a local model directory}"
BAD="client$((CLIENTS - 1))"
COMMON=(--model_name_or_path "$MODEL" --use_peft --peft_lora_r 16 --peft_lora_alpha 32 --gradient_checkpointing False
  --learning_rate 1e-4 --batch_size 4 --gradient_accumulation_steps 1 --seq_length 256 --max_steps "$STEPS"
  --num_rounds "$ROUNDS" --fed_alg fedavg --template alpaca --logging_steps 1
  --num_data_per_client 300 --local_data_dir "$ROOT/external/FedLLM-Attack/gen_data"
  --benign_dataset_names _ --benign_num_clients 0 --malicious_dataset_names _ --malicious_num_clients 0
  --exp_benign dolly --exp_split dirichlet --exp_alpha 0.5 --exp_pool_per_client 300 --exp_pad_to 256
  --guard_fail_policy closed --guard_client_record 1 --sample_clients "$CLIENTS")
A=(--exp_benign_clients "$((CLIENTS - 1))" --exp_malicious maliciousgen --exp_malicious_clients 1)
B=(--exp_benign_clients "$CLIENTS" --exp_backdoor "0.2:cf mn bb:I have been triggered.")
if [ "${SCENARIO:-attack}" = control ]; then   # no attack anywhere: whatever a defense changes here is collateral
  A=(--exp_benign_clients "$CLIENTS"); B=("${A[@]}")
fi
read -r -a EXTRA_ARGS <<< "${EXTRA:-}"
COMMON+=(${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"})
mkdir -p "$OUT"
: > "$OUT/status.tsv"
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }
JOBS="${JOBS:-1}"
one() {   # one <name> <args...>: one federated run, then what its plugins did; FILTER=1 adds the sample-filter scores
  local name=$1; shift
  rm -rf "$OUT/$name" "$OUT/rec_$name"
  local t0=$SECONDS status=ok
  "$PY" "$ROOT/experiments/fedllm_attack/run_guarded.py" "${COMMON[@]}" "$@" \
    --output_dir "$OUT/$name" --guard_record "$OUT/rec_$name" > "$OUT/$name.log" 2>&1 || status=crashed
  if [ "$status" = ok ]; then
    "$PY" "$ROOT/experiments/eval/run_summary.py" "$OUT/rec_$name" > "$OUT/$name.summary" 2>&1 || status=plugin_error
    [ -z "${FILTER:-}" ] || "$PY" "$ROOT/experiments/eval/sample_filter_eval.py" "$OUT/rec_$name" "$(ls -d "$OUT/$name"/*/ | head -1)" \
      >> "$OUT/$name.summary" 2>&1 || true
  else
    tail -5 "$OUT/$name.log" > "$OUT/$name.summary"
  fi
  [ "$name" = stats ] || prune "$name"
  printf '%s\t%s\t%s\n' "$name" "$status" "$((SECONDS - t0))" >> "$OUT/status.tsv"
  echo "-- $name: $status, $((SECONDS - t0)) s"
}
run() {   # at most JOBS runs at a time; with JOBS > 1 the wall times of the runs are not comparable
  want "$1" || return 0
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 2; done
  one "$@" &
}
prune() {   # recorded tensors are several hundred MB per run; the summaries only need the JSON
  [ -n "${KEEP_TENSORS:-}" ] || find "$OUT/rec_$1" "$OUT/$1" -name '*.safetensors' -delete 2>/dev/null || true
}

# A: statistics only; its record is also what the Safe-FedLLM probe is fitted on
run stats "${A[@]}" --guard_modules effect_stats,factor_stats,robust_outlier
for m in krum coordinate_median trimmed_mean foolsgold flame freqfed fldetector norm_clip mud_hog lomar mcd crfl fltrust; do
  extra=()   # methods that wait for a window of rounds before they judge: shortened to fit a short run
  [ "$m" = fldetector ] && extra=(--guard_args '{"fldetector": {"window": 2}}')    # 10 in the paper
  [ "$m" = mud_hog ] && extra=(--guard_args '{"mud_hog": {"warmup": 1}}')          # 3 in the paper
  [ "$m" = mcd ] && extra=(--guard_args '{"mcd": {"period": 2}}')                  # 80 in the paper
  run "$m" "${A[@]}" --guard_modules "$m" ${extra[@]+"${extra[@]}"}
done
wait
PROBE="${PROBE_FILE:-$OUT/lora_probe.safetensors}"   # a control run has no malicious client to fit on: pass the probe of an attack sweep
if [ -z "${PROBE_FILE:-}" ] && [ "${SCENARIO:-attack}" != control ] && [ -d "$OUT/rec_stats" ] && { want safe_fedllm_client || want safe_fedllm_step; }; then
  "$PY" "$ROOT/experiments/fit_lora_probe.py" "$PROBE" "$(ls -d "$OUT"/rec_stats/*/ | head -1 | sed 's:/$::'):$BAD" || true
fi
if [ -f "$PROBE" ]; then   # same seed as the run the probe was fitted on: the paper requires the same LoRA initialization
  run safe_fedllm_client "${A[@]}" --guard_modules safe_fedllm_client --guard_probe_file "$PROBE"
  run safe_fedllm_step "${A[@]}" --guard_client_modules safe_fedllm_step --guard_modules safe_fedllm_step_trust --guard_probe_file "$PROBE"
fi
run received_adapter_scan "${A[@]}" --guard_client_modules received_adapter_scan --guard_client_apply 1
run update_subspace_projection "${A[@]}" --guard_client_modules update_subspace_projection --guard_client_apply 1
for m in la_lora lisa_proximal; do   # changes to the local optimizer step
  run "$m" "${A[@]}" --guard_client_modules "$m" --guard_client_apply 1
done
for m in lisa la_lora_dp; do          # between forward and backward: trainer extension layer
  extra=()
  [ "$m" = lisa ] && extra=(--guard_args '{"lisa": {"k_align": 1, "k_finetune": 2}}')   # 100:900 in the paper; 6 local steps here
  run "$m" "${A[@]}" --guard_client_modules "$m" --guard_client_apply 1 --guard_trainer_ext 1 ${extra[@]+"${extra[@]}"}
done
run safety_mix "${A[@]}" --guard_client_modules safety_mix --guard_client_apply 1
run bea "${A[@]}" --guard_client_modules safety_mix --guard_client_apply 1 --guard_args '{"safety_mix": {"secret_words": 30}}'
# B: sample-level methods
FILTER=1 run protegofed "${B[@]}" --guard_client_modules protegofed_client --guard_modules protegofed_server --guard_client_apply 1
for m in spectral_signatures gradient_spectral_entropy activation_clustering; do
  FILTER=1 run "$m" "${B[@]}" --guard_client_modules "$m" --guard_client_apply 1
done
run onion "${B[@]}" --guard_client_modules onion --guard_client_apply 1 --guard_args '{"onion": {"max_words": 24}}'
wait
prune stats
for f in "$OUT"/*.summary; do echo "## $(basename "$f" .summary)"; cat "$f"; done
[ "${SCENARIO:-attack}" != control ] || "$PY" "$ROOT/experiments/eval/control_summary.py" "$OUT" --json "$OUT/control.json"
echo "== status"; cat "$OUT/status.tsv"
! grep -qv $'\tok\t' "$OUT/status.tsv"
