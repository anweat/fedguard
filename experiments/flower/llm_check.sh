#!/usr/bin/env bash
# The library on Flower with a real model: what is reachable natively, with glue in the app's train
# function, and through the handshake extension layer. Benign data only. Each line is one simulation.
#   plain_cpu, plain_cpu2, record_cpu   on the CPU, where training is deterministic: FedAvg alone twice, and
#                    GuardStrategy with nothing mounted. The app has to repeat itself bit for bit, and mounting
#                    the library has to leave the result untouched. (On the GPU two runs of the same app differ.)
#   server_all       every server-side method that needs no external resource, recording only
#   server_act       one that clips, selects and replaces (FLAME), acting
#   client_all       client-side methods that need samples, a model handle or the optimizer step, recording only
#   client_act       three of them acting: masked samples, changed gradients, a replaced upload
#   handshake        ProtegoFed through the handshake extension (not Flower's own round protocol)
#   ext_read_cpu     the trainer extension layer on, a plugin at CLIENT_LOSS that only records (Lisa with actions
#                    off, which still runs its extra forward passes): the result has to equal plain_cpu bit for bit
#   trainer_ext      Lisa and LA-LoRA with per-sample clipping, acting (not the host's own training step)
# Env: OUT, MODEL (a model directory, or `tiny`), FG_ENV, ROUNDS (2), NODES (4), STEPS (4)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
OUT="${OUT:-$ROOT/runs/flower_llm}"
export FG_MODEL="${MODEL:?set MODEL to a model directory or tiny}" FG_ROUNDS="${ROUNDS:-2}" FG_NODES="${NODES:-4}" FG_STEPS="${STEPS:-4}"
rm -rf "$OUT"; mkdir -p "$OUT"; : > "$OUT/status.tsv"
SERVER_ALL=effect_stats,factor_stats,robust_outlier,report_guard,norm_clip,krum,lomar,flame,freqfed,coordinate_median,trimmed_mean,foolsgold,fldetector,mud_hog,mcd,crfl,safe_fedllm_step_trust,jump_rollback
CLIENT_ALL=spectral_signatures,activation_clustering,gradient_spectral_entropy,onion,safety_mix,lisa_proximal,la_lora,received_adapter_scan,update_subspace_projection
run() {   # run <name> <mode> [VAR=value ...]
  local name=$1 mode=$2 t0=$SECONDS status=ok; shift 2
  env "$@" "$PY" "$ROOT/experiments/flower/sim_llm.py" "$OUT/$name" "$mode" > "$OUT/$name.log" 2>&1 || status=crashed
  [ -f "$OUT/$name/final_$mode.safetensors" ] || status=crashed
  local lost; lost=$(grep -c "Received error in reply\|OutOfMemoryError" "$OUT/$name.log" || true)
  [ "$status" != ok ] || [ "$lost" = 0 ] || status="incomplete($lost failed replies)"   # a round with missing clients proves nothing
  if [ "$status" = ok ] && [ "$mode" = guard ] && [ "$name" != record_cpu ]; then
    "$PY" "$ROOT/experiments/eval/run_summary.py" "$OUT/$name/records" > "$OUT/$name.summary" 2>&1 || status=plugin_error
  fi
  printf '%s\t%s\t%s\n' "$name" "$status" "$((SECONDS - t0))" >> "$OUT/status.tsv"
  echo "-- $name: $status, $((SECONDS - t0)) s"; [ -f "$OUT/$name.summary" ] && cut -c1-200 "$OUT/$name.summary"
  [ "$status" = ok ] || grep -v "Warning" "$OUT/$name.log" | tail -6
}
CPU=(FG_DEVICE=cpu FG_MAXLEN=64 FG_STEPS=2)   # short samples: CPU training of the full vocabulary head is what fills a 16 GB machine
run plain_cpu plain "${CPU[@]}"
run plain_cpu2 plain "${CPU[@]}"
run record_cpu guard "${CPU[@]}"
run server_all guard FG_SERVER=$SERVER_ALL FG_APPLY=0
run server_act guard FG_SERVER=flame FG_APPLY=1
run client_all guard FG_CLIENT=$CLIENT_ALL FG_APPLY=0
run client_act guard FG_CLIENT=spectral_signatures,lisa_proximal,update_subspace_projection FG_APPLY=1
run handshake guard FG_SERVER=protegofed_server FG_CLIENT=protegofed_client FG_APPLY=1 FG_HANDSHAKE=1
run ext_read_cpu guard "${CPU[@]}" FG_CLIENT=lisa FG_APPLY=0 FG_TRAINER_EXT=1
run trainer_ext guard FG_CLIENT=lisa,la_lora_dp FG_APPLY=1 FG_TRAINER_EXT=1
"$PY" - "$OUT" <<'PYEOF' || printf 'compare\tfailed\t0\n' >> "$OUT/status.tsv"
import sys
from pathlib import Path
import torch
from safetensors.torch import load_file
out = Path(sys.argv[1])
f = [out / "plain_cpu/final_plain.safetensors", out / "plain_cpu2/final_plain.safetensors", out / "record_cpu/final_guard.safetensors",
     out / "ext_read_cpu/final_guard.safetensors"]
if not all(p.exists() for p in f):
    print("[cpu comparison] a run is missing"); sys.exit(1)
a, b, g, x = (load_file(p) for p in f)
same = lambda x, y: x.keys() == y.keys() and all(torch.equal(x[k], y[k]) for k in x)  # noqa: E731
rel = lambda x, y: max(float((x[k] - y[k]).abs().max() / x[k].abs().max().clamp_min(1e-30)) for k in x)  # noqa: E731
print(f"[cpu comparison] the app repeats itself: {same(a, b)} (max relative difference {rel(a, b):.1e}); "
      f"library mounted, nothing running: identical to the app alone {same(a, g)} (max relative difference {rel(a, g):.1e})",
      f"trainer extension on, plugin at CLIENT_LOSS recording only: identical {same(a, x)} (max relative difference {rel(a, x):.1e})",
      "PASS" if same(a, b) and same(a, g) and same(a, x) else "FAIL")
sys.exit(0 if same(a, b) and same(a, g) and same(a, x) else 1)
PYEOF
echo "== status"; cat "$OUT/status.tsv"
! grep -qv $'\tok\t' "$OUT/status.tsv"
