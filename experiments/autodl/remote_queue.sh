#!/usr/bin/env bash
# Runs on the AutoDL instance: one queue of experiment stages, each run once and marked, so that a
# restarted queue continues after the last finished stage. Writes runs/autodl/DONE or FAILED at the end.
# Usage: remote_queue.sh <queue name>     queues are the functions at the bottom of this file
# Env: FG_ENV (default fl311) selects the Python environment under envs/
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec 9> /tmp/fedguard_queue.lock
flock -n 9 || { echo "another queue is already running"; exit 1; }
export FG_ENV="${FG_ENV:-fl311}"
export HF_HOME=/root/autodl-tmp/hf HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
Q="$ROOT/runs/autodl"; mkdir -p "$Q/stages"
LOG="$Q/queue.log"
failed=0
say() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
stage() {
  local name=$1; shift
  if [ -f "$Q/stages/$name.done" ]; then say "skip  $name"; return 0; fi
  say "start $name"
  if "$@" > "$Q/stages/$name.out" 2>&1; then touch "$Q/stages/$name.done"; say "done  $name"
  else failed=1; say "FAIL  $name (runs/autodl/stages/$name.out)"; fi
}
model() {   # a plain directory uploaded beforehand, else the HF cache
  [ -f "/root/autodl-tmp/models/$1/config.json" ] && { echo "/root/autodl-tmp/models/$1"; return; }
  ls -d "$HF_HOME"/hub/models--Qwen--"$1"/snapshots/* | head -1
}

smoke() {          # the plumbing checks that also run on the laptop, here on the GPU
  stage flower_check env OUT="$ROOT/runs/flower_check" bash experiments/flower/flower_check.sh
  stage defense_smoke_05b env OUT="$ROOT/runs/defense_smoke_05b" MODEL="$(model Qwen2.5-0.5B-Instruct)" \
    PROBE_RUN= EXTRA="--exp_precision bf16" bash experiments/fedllm_attack/defense_smoke.sh
  stage capture_timing env OUT="$ROOT/runs/client_capture_timing" MODEL="$(model Qwen2.5-0.5B-Instruct)" \
    EXTRA="--exp_precision bf16" bash experiments/fedllm_attack/client_capture_timing.sh
}

defense_7b() {     # the two federated-LLM defenses on a 7B model: cost and first behavior, not a reproduction
  local m; m="$(model Qwen2.5-7B-Instruct)"
  stage defense_7b env OUT="$ROOT/runs/defense_7b" MODEL="$m" ROUNDS=5 CLIENTS=10 STEPS=10 PROBE_RUN= \
    EXTRA="--exp_precision bf16 --exp_base_dtype bf16 --exp_template chat" bash experiments/fedllm_attack/defense_smoke.sh
}

q35() {            # Qwen3.5 (needs FG_ENV=q35): ProtegoFed cost first, then every method once. SIZE: 0.8B | 4B | ...; JOBS runs at a time (about 10 GB of GPU memory each at 0.8B); ONLY limits the runs
  local size="${SIZE:-0.8B}" m; m="$(model "Qwen3.5-$size")"
  local x="--exp_precision bf16 --exp_base_dtype bf16"
  stage "protegofed_$size" env OUT="$ROOT/runs/q35_protegofed_$size" MODEL="$m" ONLY=protegofed ROUNDS=2 CLIENTS=4 EXTRA="$x" \
    bash experiments/fedllm_attack/methods_sweep.sh
  stage "sweep2_$size" env OUT="$ROOT/runs/q35_sweep_$size" MODEL="$m" EXTRA="$x" JOBS="${JOBS:-2}" ONLY="${ONLY:-}" bash experiments/fedllm_attack/methods_sweep.sh
}

control() {        # every method once with no attack anywhere (FG_ENV=q35). SIZE, JOBS as in q35
  local size="${SIZE:-0.8B}" m probe; m="$(model "Qwen3.5-$size")"
  probe="$ROOT/runs/q35_sweep_$size/lora_probe.safetensors"; [ -f "$probe" ] || probe=""
  stage "control_$size" env OUT="$ROOT/runs/q35_control_$size" MODEL="$m" EXTRA="--exp_precision bf16 --exp_base_dtype bf16" \
    JOBS="${JOBS:-2}" ONLY="${ONLY:-}" SCENARIO=control PROBE_FILE="$probe" bash experiments/fedllm_attack/methods_sweep.sh
}

verify() {         # what holds for the library as an add-on: unit tests, bitwise identity with upstream, the Flower checks
  stage "unit_tests_$FG_ENV" "$ROOT/envs/$FG_ENV/.venv/bin/python" -m pytest tests -q
  stage "examples_$FG_ENV" "$ROOT/envs/$FG_ENV/.venv/bin/python" integrations/make_examples.py --check
  stage "bitwise_openfedllm_$FG_ENV" env MODEL="$(model Qwen2.5-0.5B-Instruct)" bash integrations/check_bitwise.sh openfedllm
  stage "bitwise_fedllm_attack_$FG_ENV" env MODEL="$(model Qwen2.5-0.5B-Instruct)" bash integrations/check_bitwise.sh fedllm_attack
  stage "bitwise_$FG_ENV" env OUT="$ROOT/runs/p0c" MODEL="$(model Qwen2.5-0.5B-Instruct)" bash experiments/fedllm_attack/p0c_check.sh
  stage "flower_$FG_ENV" env OUT="$ROOT/runs/flower_check" bash experiments/flower/flower_check.sh
  stage "overhead_$FG_ENV" env OUT="$ROOT/runs/client_capture_timing" MODEL="$(model Qwen2.5-0.5B-Instruct)" \
    EXTRA="--exp_precision bf16" bash experiments/fedllm_attack/client_capture_timing.sh
}

hostfit() {        # in the q35 environment: the library on Flower with a real model, and the refactored methods once more on the script host
  local size="${SIZE:-0.8B}" m; m="$(model "Qwen3.5-$size")"
  stage "flower_llm_$size" env FG_ENV=q35 OUT="$ROOT/runs/flower_llm_$size" MODEL="$m" bash experiments/flower/llm_check.sh
  stage "openfedllm_plugins_05b" env FG_ENV=fl311 OUT="$ROOT/runs/plugins_openfedllm_05b" MODEL="$(model Qwen2.5-0.5B-Instruct)" bash integrations/check_plugins.sh
  stage "openfedllm_plugins_$size" env FG_ENV=q35 OUT="$ROOT/runs/plugins_openfedllm_$size" MODEL="$m" bash integrations/check_plugins.sh
  stage "recheck_$size" env FG_ENV=q35 OUT="$ROOT/runs/q35_recheck_$size" MODEL="$m" EXTRA="--exp_precision bf16 --exp_base_dtype bf16" JOBS=2 \
    SCENARIO=control ONLY="stats krum flame update_subspace_projection" bash experiments/fedllm_attack/methods_sweep.sh
}

ext() {            # the trainer extension layer and FLTrust's server update on a real model (benign data only)
  local size="${SIZE:-0.8B}" m; m="$(model "Qwen3.5-$size")"
  stage "unit_tests_ext" "$ROOT/envs/q35/.venv/bin/python" -m pytest tests -q
  stage "flower_llm_ext_$size" env FG_ENV=q35 OUT="$ROOT/runs/flower_llm_ext_$size" MODEL="$m" bash experiments/flower/llm_check.sh
  stage "ext_methods_$size" env FG_ENV=q35 OUT="$ROOT/runs/q35_ext_$size" MODEL="$m" EXTRA="--exp_precision bf16 --exp_base_dtype bf16" JOBS=1 \
    SCENARIO=control ONLY="stats fltrust lisa la_lora_dp lisa_proximal la_lora" bash experiments/fedllm_attack/methods_sweep.sh
}

refit() {          # after the internal clean-up of 2026-10-11 (action table, scoped plugin state, regrouped methods, control
                   # policies in all three entry points): the properties checked before have to hold again. Benign data only.
  local size="${SIZE:-0.8B}" m m05; m="$(model "Qwen3.5-$size")"; m05="$(model Qwen2.5-0.5B-Instruct)"
  stage "unit_tests_refit" "$ROOT/envs/q35/.venv/bin/python" -m pytest tests -q
  stage "examples_refit" "$ROOT/envs/fl311/.venv/bin/python" integrations/make_examples.py --check
  stage "bitwise_openfedllm_refit" env FG_ENV=fl311 MODEL="$m05" bash integrations/check_bitwise.sh openfedllm
  stage "bitwise_fedllm_attack_refit" env FG_ENV=fl311 MODEL="$m05" bash integrations/check_bitwise.sh fedllm_attack
  stage "p0c_refit" env FG_ENV=fl311 OUT="$ROOT/runs/p0c_refit" MODEL="$m05" bash experiments/fedllm_attack/p0c_check.sh
  stage "plugins_openfedllm_refit" env FG_ENV=q35 OUT="$ROOT/runs/plugins_openfedllm_refit" MODEL="$m" bash integrations/check_plugins.sh
  stage "flower_llm_refit_$size" env FG_ENV=q35 OUT="$ROOT/runs/flower_llm_refit_$size" MODEL="$m" bash experiments/flower/llm_check.sh
  find "$ROOT/runs/flower_llm_refit_$size" -name '*.safetensors' -delete 2>/dev/null || true      # the 30 GB disk fills otherwise
  stage "sweep_refit_$size" env FG_ENV=q35 OUT="$ROOT/runs/q35_refit_$size" MODEL="$m" EXTRA="--exp_precision bf16 --exp_base_dtype bf16" JOBS=1 \
    SCENARIO=control ONLY="stats krum flame fltrust mud_hog lisa la_lora_dp lisa_proximal protegofed spectral_signatures safety_mix update_subspace_projection" \
    bash experiments/fedllm_attack/methods_sweep.sh
  stage "policy_file_$size" env FG_ENV=q35 OUT="$ROOT/runs/policy_refit_$size" MODEL="$m" bash experiments/fedllm_attack/policy_check.sh
}

say "queue '$1' started (pid $$)"
case "$1" in
  smoke) smoke ;;
  defense_7b) defense_7b ;;
  q35) q35 ;;
  control) control ;;
  verify) verify ;;
  hostfit) hostfit ;;
  addon) verify; hostfit ;;
  ext) ext ;;
  refit) refit ;;
  all) smoke; defense_7b ;;
  *) say "unknown queue $1"; failed=1 ;;
esac
[ "$failed" = 0 ] && touch "$Q/DONE" || touch "$Q/FAILED"
say "queue '$1' finished (failed=$failed)"
