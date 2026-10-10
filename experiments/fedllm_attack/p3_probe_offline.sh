#!/usr/bin/env bash
# Offline H6 check on existing P2-era records (alpaca-trained): replay C0 d0.5 seeds 1-3 and the C1 runs with
# effect_stats, factor_stats and compliance_probe, then compare detection with and without the probe.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
PY=envs/fl311/.venv/bin/python
OUT=runs/p3probe
M=$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/* | head -1)
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1
mkdir -p "$OUT/records"
replay() {  # replay <train dir> <records root>
  local name; name=$(basename "$(ls -d "$1"/*/ | head -1)")
  [ -d "$OUT/records/$name" ] && { echo "skip $name"; return; }
  $PY experiments/replay_records.py "$2/$name" "$OUT/records" effect_stats,factor_stats,compliance_probe 2.0 \
    --probe "$M:alpaca:32"
}
for s in 1 2 3; do replay runs/p2/d0.5_s$s runs/p2/records; ln -sfn "$ROOT/runs/p2/d0.5_s$s" "$OUT/d0.5_s$s"; touch "$OUT/d0.5_s$s.done"; done
for r in c1_m1.0_s1 c1_m0.3_s1 c1_m0.1_s1; do replay runs/p3pre/$r runs/p3pre/records; done
$PY experiments/fedllm_attack/analyze_p2.py "$OUT" "$OUT/figs" \
  runs/p3pre/c1_m1.0_s1,runs/p3pre/c1_m0.3_s1,runs/p3pre/c1_m0.1_s1 "$OUT/records" | tee "$OUT/summary.md"
