"""Runtime shims shared by every entry point of an OpenFedLLM-style host, so that runs with and without
the library see identical conditions. No file under external/ is edited.

  - peft has no default LoRA target modules for qwen2 and qwen3_5: register them.
  - --device cpu hides MPS so HF Trainer falls back to CPU (bitwise-reproducible runs).
  - Upstream defines --seed (default 2023) but never seeds torch before get_peft_model, so the LoRA A
    initialization differs in every process and runs are not reproducible. Seed all RNGs from --seed.
"""
import sys
from pathlib import Path

UPSTREAM = Path(__file__).resolve().parents[1] / "external" / "FedLLM-Attack"   # the default host


def split_argv(parser):
    """Parse our own flags and leave the rest in sys.argv for upstream's HfArgumentParser."""
    ours, rest = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + rest
    return ours


def apply_shims(device: str = "auto", upstream: Path | None = None) -> None:
    import torch
    if device == "cpu":
        torch.backends.mps.is_available = lambda: False
    from peft.utils import TRANSFORMERS_MODELS_TO_LORA_TARGET_MODULES_MAPPING as lora_targets
    lora_targets.setdefault("qwen2", ["q_proj", "v_proj"])
    # qwen3_5: three of four layers use linear attention (no q_proj/v_proj); in_proj_qkv is their counterpart,
    # so that every layer carries an adapter. The last layer is a full-attention one.
    for t in ("qwen3_5", "qwen3_5_text"):
        lora_targets.setdefault(t, ["q_proj", "v_proj", "in_proj_qkv"])
    _trainer_compat()
    seed = _argv_seed(default=2023)
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    host = str(upstream or UPSTREAM)
    if host not in sys.path:
        sys.path.insert(0, host)


def _argv_seed(default: int) -> int:
    for i, a in enumerate(sys.argv):
        if a == "--seed" and i + 1 < len(sys.argv):
            return int(sys.argv[i + 1])
        if a.startswith("--seed="):
            return int(a.split("=", 1)[1])
    return default


def _trainer_compat() -> None:
    """trl 0.8.1 (pinned by upstream) passes `tokenizer=` to transformers.Trainer; transformers 5 renamed
    it to `processing_class`. Translate the keyword when the installed Trainer no longer accepts it."""
    import inspect
    from transformers import Trainer
    if "tokenizer" in inspect.signature(Trainer.__init__).parameters:
        return
    init = Trainer.__init__

    def __init__(self, *args, tokenizer=None, **kwargs):
        if tokenizer is not None:
            kwargs.setdefault("processing_class", tokenizer)
        init(self, *args, **kwargs)
        if not hasattr(self, "tokenizer"):
            self.tokenizer = kwargs.get("processing_class")
    Trainer.__init__ = __init__
