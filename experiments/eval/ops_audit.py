"""How the method plugins use the operator library, read from the source (no model, no run).

For every plugin class in fedguard/methods and fedguard/plugins: which fedguard.ops functions it calls
(directly or through module-level helpers of its own file), and how many raw torch calls it makes
itself. For every operator: which classes use it. Operators nobody uses and classes that mostly do
their own tensor math are where the library and the methods do not fit each other.

Usage: ops_audit.py [--json out.json]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fedguard.kb.opsuse import usage  # noqa: E402

if __name__ == "__main__":
    a = usage()
    cl, op = a["classes"], a["operators"]
    print(f"{len(op)} operators, {len(cl)} plugin classes")
    counts = sorted(((len(u), o) for o, u in op.items()), reverse=True)
    print(f"operators used by 3+ classes: {sum(n >= 3 for n, _ in counts)}; by 2: {sum(n == 2 for n, _ in counts)}; by 1: {sum(n == 1 for n, _ in counts)}; by none: {sum(n == 0 for n, _ in counts)}")
    print("most used: " + ", ".join(f"{o} ({n})" for n, o in counts[:12]))
    print("unused: " + ", ".join(o for n, o in counts if n == 0))
    print(f"\n{'class':28s}{'ops':>4s}{'torch':>6s}{'lines':>6s}  operators")
    for name, c in sorted(cl.items(), key=lambda kv: (len(kv[1]["ops"]), -kv[1]["torch_calls"])):
        print(f"{name:28s}{len(c['ops']):4d}{c['torch_calls']:6d}{c['lines']:6d}  {', '.join(c['ops'])}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(a, indent=1), encoding="utf-8")
