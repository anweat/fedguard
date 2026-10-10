"""Run a host's own main_sft.py unmodified, under the same environment shims the integration examples get
(integrations/host_shims.py), and save the final global LoRA next to its outputs so that it can be compared.

    launch_upstream.py --upstream_dir external/OpenFedLLM [--device cpu] <the host's own arguments>
"""
import argparse
import os
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from host_shims import apply_shims, split_argv  # noqa: E402

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--upstream_dir", required=True)
parser.add_argument("--device", default="auto", choices=["auto", "cpu"])
args = split_argv(parser)
upstream = Path(args.upstream_dir).resolve()
apply_shims(args.device, upstream=upstream)

g = runpy.run_path(str(upstream / "main_sft.py"), run_name="__main__")

from safetensors.torch import save_file  # noqa: E402

save_file({k: v.detach().cpu().contiguous() for k, v in g["global_dict"].items()},
          os.path.join(g["script_args"].output_dir, "final_global.safetensors"))
