"""The shims live in integrations/host_shims.py (they belong to the host integration, not to our experiments);
this module keeps the old import path working."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "integrations"))
from host_shims import UPSTREAM, apply_shims, split_argv  # noqa: E402,F401
