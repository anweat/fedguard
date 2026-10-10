"""Run FedLLM-Attack's upstream main_sft.py unmodified (see _shims.py for the runtime shims).

After the run, the final global LoRA is saved to <output_dir>/final_global.safetensors so that
guarded runs can be compared against it.
"""
import argparse
import os
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shims import UPSTREAM, apply_shims, split_argv  # noqa: E402

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--device", default="auto", choices=["auto", "cpu"])
args = split_argv(parser)
apply_shims(args.device)

g = runpy.run_path(str(UPSTREAM / "main_sft.py"), run_name="__main__")

from safetensors.torch import save_file  # noqa: E402

save_file({k: v.detach().cpu().contiguous() for k, v in g["global_dict"].items()},
          os.path.join(g["script_args"].output_dir, "final_global.safetensors"))
