#!/usr/bin/env bash
# Runs on the AutoDL instance: Python environment, models and datasets through mainland mirrors.
# Idempotent. Everything large goes to the data disk (/root/autodl-tmp). MODELS: comma-separated HF ids.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export HF_HOME=/root/autodl-tmp/hf HF_ENDPOINT=https://hf-mirror.com
export UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple   # measured on AutoDL: tuna stalls on the large wheels under parallel downloads
export UV_CONCURRENT_DOWNLOADS=4 UV_HTTP_TIMEOUT=120
export UV_PYTHON_INSTALL_MIRROR=https://registry.npmmirror.com/-/binary/python-build-standalone
export UV_CACHE_DIR=/root/autodl-tmp/uv-cache
mkdir -p "$HF_HOME" runs/autodl
export FG_ENV="${FG_ENV:-fl311}"
# The mirrors stall on the two largest wheels (torch, cudnn) from inside AutoDL. If they were uploaded to
# /root/autodl-tmp/wheels beforehand (pip download on another machine, then rsync), use those.
[ -d /root/autodl-tmp/wheels ] && export UV_FIND_LINKS=/root/autodl-tmp/wheels
if ! command -v uv >/dev/null && [ ! -x "$HOME/.local/bin/uv" ]; then
  pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple uv || curl -LsSf https://astral.sh/uv/install.sh | sh
fi
# an interrupted install leaves a venv without packages: test an import, not the interpreter
envs/$FG_ENV/.venv/bin/python -c "import torch, transformers, peft, trl, flwr, huggingface_hub" 2>/dev/null || UV_VENV_CLEAR=1 bash envs/setup_linux_cuda.sh
PY=envs/$FG_ENV/.venv/bin/python
"$PY" - <<PY
import os
from huggingface_hub import snapshot_download
for m in os.environ.get("MODELS", "").split(","):
    if m.strip():
        print("model", m, snapshot_download(m.strip(), allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"]))
from datasets import load_dataset
print("dolly", len(load_dataset("databricks/databricks-dolly-15k", split="train")))
PY
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
"$PY" -m pytest tests -q -x 2>&1 | tail -1
