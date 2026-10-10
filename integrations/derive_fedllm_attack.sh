#!/usr/bin/env bash
# Build the files that are derived from FedLLM-Attack's training script. FedLLM-Attack is published without
# a license, so this repository does not redistribute text derived from it: it ships the differences only
# (experiments/fedllm_attack/run_guarded.patch, integrations/fedllm_attack/main_sft.guard.patch) and this
# script, which applies them to your own checkout of the upstream repository.
#   external/FedLLM-Attack   at the commit named in external/UPSTREAM.md
# Produces: experiments/fedllm_attack/run_guarded.py, integrations/fedllm_attack/main_sft_guard.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UP="$ROOT/external/FedLLM-Attack/main_sft.py"
[ -f "$UP" ] || { echo "clone FedLLM-Attack into external/FedLLM-Attack first (commit: see external/UPSTREAM.md)"; exit 1; }
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
tr -d '\r' < "$UP" > "$TMP"                         # upstream uses CRLF line ends; the patch was made against LF
patch -s -o "$ROOT/experiments/fedllm_attack/run_guarded.py" "$TMP" "$ROOT/experiments/fedllm_attack/run_guarded.patch"
PY="${PYTHON:-python3}"
[ -x "$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python" ] && PY="$ROOT/envs/${FG_ENV:-fl311}/.venv/bin/python"
"$PY" "$ROOT/integrations/make_examples.py" > /dev/null
echo "built experiments/fedllm_attack/run_guarded.py and integrations/fedllm_attack/main_sft_guard.py"
