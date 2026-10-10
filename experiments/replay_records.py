"""Recompute module findings offline from recorded rounds, without retraining.

Reads <record_run_dir>/round_XXXX/{base,client_*}.safetensors + reports.json + round.json, runs the
given built-in plugins in round order (so history-based plugins see the same history), and
writes round.json files with the new findings (original meta preserved) under <out_root>/<run name>/.

Usage: replay_records.py <record_run_dir> <out_root> <modules, comma-separated> [lora_scale]
                         [--probe <model_path>:<template>[:n]]   (needed for plugins that use a model handle, e.g. compliance_probe)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fedguard.core.types import RunSpec  # noqa: E402
from fedguard.plugins import BUILTIN  # noqa: E402
from fedguard.replay import replay as library_replay  # noqa: E402


def build_probe(spec: str, lora_r: int = 16, lora_alpha: int = 32):
    """Load the base model once and wrap it as an HFProbe (AdvBench harmful, held-out Dolly benign)."""
    import csv
    import random

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from fedguard.adapters.hf_probe import HFProbe
    sys.path.insert(0, str(Path(__file__).resolve().parent / "fedllm_attack"))
    from data import load_dolly

    path, template, *rest = spec.split(":")
    n = int(rest[0]) if rest else 32
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32)
    model = get_peft_model(model.to(device), LoraConfig(r=lora_r, lora_alpha=lora_alpha, lora_dropout=0.0, bias="none",
                                                        task_type="CAUSAL_LM", target_modules=["q_proj", "v_proj"]))
    adv = list(csv.DictReader(open(Path(__file__).resolve().parents[1] /
                                   "external/FedLLM-Attack/evaluation/open_ended/data/advbench/advbench.csv")))
    harm = [(r["goal"], r["target"]) for r in random.Random(0).sample(adv, n)]
    dolly = load_dolly(0)
    held = [r for r in dolly.select(range(len(dolly) - 2000, len(dolly))) if len(r["instruction"]) <= 300]
    ben = [(r["instruction"], r["response"][:200]) for r in held[:n]]
    return HFProbe(model, tok, harm, ben, template=template, batch=8)


def replay(run_dir: Path, out_root: Path, module_names: list[str], lora_scale: float, probe=None) -> int:
    return library_replay(run_dir.parent, run_dir.name, [BUILTIN[n]() for n in module_names], out_root,
                          spec=RunSpec(run_dir.name, lora_scale=lora_scale), model_handle=probe)


if __name__ == "__main__":
    argv = sys.argv[1:]
    probe_spec = None
    if "--probe" in argv:
        i = argv.index("--probe")
        probe_spec = argv[i + 1]
        del argv[i:i + 2]
    run_dir, out_root, names = Path(argv[0]), Path(argv[1]), argv[2].split(",")
    scale = float(argv[3]) if len(argv) > 3 else 2.0
    n = replay(run_dir, out_root, names, scale, build_probe(probe_spec) if probe_spec else None)
    print(f"replayed {n} rounds of {run_dir.name} -> {out_root / run_dir.name}")
