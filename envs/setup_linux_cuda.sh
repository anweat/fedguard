#!/usr/bin/env bash
# Linux + NVIDIA GPU environment (WSL2 or a cloud server): the packages of envs/$FG_ENV (default fl311) plus bitsandbytes.
# Mirrors are optional; in mainland China set
#   UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
#   UV_PYTHON_INSTALL_MIRROR=https://registry.npmmirror.com/-/binary/python-build-standalone
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$ROOT/envs/${FG_ENV:-fl311}"
UV="${UV:-$(command -v uv || echo "$HOME/.local/bin/uv")}"
"$UV" python install 3.11
"$UV" venv --python 3.11 "$ENV/.venv"
"$UV" pip install --python "$ENV/.venv/bin/python" -r "$ENV/requirements.txt" "bitsandbytes==0.49.1"
"$UV" pip install --python "$ENV/.venv/bin/python" -e "$ROOT"
"$ENV/.venv/bin/python" - <<'PY'
import torch, transformers, trl, peft, bitsandbytes, flwr
print("torch", torch.__version__, "cuda", torch.version.cuda, "available", torch.cuda.is_available(),
      torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
print("transformers", transformers.__version__, "trl", trl.__version__, "peft", peft.__version__,
      "bitsandbytes", bitsandbytes.__version__, "flwr", flwr.__version__)
PY
