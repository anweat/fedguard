#!/usr/bin/env bash
# Checks of the library as an add-on to its host frameworks, sized for legion (RTX 4050 6 GB, WSL2, env fl311,
# Qwen2.5-0.5B). Start it in a terminal on legion and keep the window open:
#     wsl -d Ubuntu -- bash /root/innovation/experiments/legion/queue_addon.sh
# Every stage leaves a marker in runs/addon/, so running it again continues after the last finished stage.
# Progress: runs/addon.log. Nothing here involves an attack: all data are benign.
#   unit_tests        the test suite
#   examples          the integration examples are what the generator produces from the hosts' scripts
#   bitwise_*         OpenFedLLM and FedLLM-Attack: the example trains to the same bits as the host's own script
#   p0c               our experiment driver against FedLLM-Attack's script, same comparison
#   flower            Flower's simulation with synthetic clients, including the handshake extension layer
#   overhead          time spent in capture and plugins next to training time
#   flower_llm        Flower with a real model: native, with glue, and through the handshake extension
#   recheck           the methods touched by the operator clean-up, once more on a real model
#   openfedllm_plugins  plugins running and acting on the original OpenFedLLM host
#   unit_tests_ext, flower_llm_ext, ext_methods   the trainer extension layer (CLIENT_LOSS): the test suite again, Flower
#                     with a real model (extension on and recording only has to equal the plain run bit for bit; Lisa and
#                     LA-LoRA with per-sample clipping acting), and FLTrust, Lisa, LA-LoRA on the script host
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec 9> /tmp/fedguard_addon.lock
flock -n 9 || { echo "another instance of this queue is already running"; exit 1; }
PY="$ROOT/envs/fl311/.venv/bin/python"
Q="$ROOT/runs/addon"; mkdir -p "$Q"
LOG="$ROOT/runs/addon.log"
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TOKENIZERS_PARALLELISM=false FG_ENV=fl311
M05=$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)
failed=0
say() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }
stage() {
  local name=$1; shift
  if [ -f "$Q/$name.done" ]; then say "skip  $name"; return 0; fi
  say "start $name"
  if "$@" > "$Q/$name.out" 2>&1; then touch "$Q/$name.done"; say "done  $name"
  else failed=1; say "FAIL  $name (runs/addon/$name.out)"; fi
}
say "queue started (pid $$), model $M05"
stage unit_tests "$PY" -m pytest tests -q
for host in OpenFedLLM FedLLM-Attack; do
  [ -f "external/$host/main_sft.py" ] || say "MISSING external/$host: its stages will fail; clone it at the commit in external/UPSTREAM.md"
done
stage examples "$PY" integrations/make_examples.py --check
stage bitwise_openfedllm env MODEL="$M05" bash integrations/check_bitwise.sh openfedllm
stage bitwise_fedllm_attack env MODEL="$M05" bash integrations/check_bitwise.sh fedllm_attack
stage p0c env MODEL="$M05" OUT="$ROOT/runs/p0c" bash experiments/fedllm_attack/p0c_check.sh
stage flower env OUT="$ROOT/runs/flower_check" bash experiments/flower/flower_check.sh
stage overhead env OUT="$ROOT/runs/client_capture_timing" MODEL="$M05" EXTRA="--exp_precision bf16" \
  bash experiments/fedllm_attack/client_capture_timing.sh
stage flower_llm env OUT="$ROOT/runs/flower_llm_05b" MODEL="$M05" bash experiments/flower/llm_check.sh
stage recheck env OUT="$ROOT/runs/recheck_05b" MODEL="$M05" EXTRA="--exp_precision bf16" JOBS=1 SCENARIO=control \
  ONLY="stats krum flame update_subspace_projection" bash experiments/fedllm_attack/methods_sweep.sh
stage openfedllm_plugins env OUT="$ROOT/runs/plugins_openfedllm_05b" MODEL="$M05" bash integrations/check_plugins.sh
stage unit_tests_ext "$PY" -m pytest tests -q
stage flower_llm_ext env OUT="$ROOT/runs/flower_llm_ext_05b" MODEL="$M05" bash experiments/flower/llm_check.sh
stage ext_methods env OUT="$ROOT/runs/ext_05b" MODEL="$M05" EXTRA="--exp_precision bf16" JOBS=1 SCENARIO=control \
  ONLY="stats fltrust lisa la_lora_dp lisa_proximal la_lora" bash experiments/fedllm_attack/methods_sweep.sh
say "queue finished (failed=$failed)"
[ "$failed" = 0 ] && touch "$Q/DONE" || touch "$Q/FAILED"
