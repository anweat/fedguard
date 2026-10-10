#!/usr/bin/env python3
"""Check one ported method. Runs where the generated code is allowed to execute (legion, inside a
network-less, time- and memory-limited shell started by run_port.py); never on the Mac.

    python verify.py <dir with plugin.py and test_port.py>      -> one JSON line on stdout

Checks, in order: the plugin file imports; it defines GuardPlugin subclasses; each can be built and its
contract holds in a runner of its side; its docstring has the required sections; the tests pass.
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(HERE)]


def main(folder: Path) -> dict:
    out = {"imports": False, "plugins": [], "contract": False, "docstring": False, "tests": None, "errors": []}
    sys.path.insert(0, str(folder))
    try:
        import plugin
    except Exception as exc:                                    # noqa: BLE001  whatever the generated file raises is the finding
        out["errors"].append(f"plugin.py does not import: {type(exc).__name__}: {exc}")
        return out
    out["imports"] = True
    from fedguard.core.plugin import GuardPlugin
    from fedguard.core.runner import GuardRunner
    from fedguard.core.types import RunSpec, side_of
    from fedguard.kb import docstring_sections
    classes = [c for c in vars(plugin).values() if inspect.isclass(c) and issubclass(c, GuardPlugin) and c is not GuardPlugin
               and c.__module__ == "plugin" and getattr(c, "name", "")]
    if not classes:
        out["errors"].append("plugin.py defines no named GuardPlugin subclass")
        return out
    ok_contract = ok_doc = True
    for cls in classes:
        row = {"class": cls.__name__, "name": cls.name}
        try:
            p = cls()
            side = side_of(p.stages[0])
            GuardRunner([p], RunSpec("verify"), side=side, resources={k: object() for k in p.resources})
            row.update(side=side, stages=[s.value for s in p.stages], needs=sorted(p.needs), resources=sorted(p.resources), acts=sorted(p.acts))
        except Exception as exc:                                # noqa: BLE001
            ok_contract = False
            out["errors"].append(f"{cls.__name__}: cannot be mounted: {type(exc).__name__}: {exc}")
        sections = docstring_sections(cls.__doc__)
        row["doc_sections"] = sorted(k for k in sections if k != "summary")
        if "implemented" not in sections:
            ok_doc = False
            out["errors"].append(f"{cls.__name__}: the class docstring has no 'Implemented:' section")
        row["lines"] = len(inspect.getsource(cls).splitlines())
        out["plugins"].append(row)
    out["contract"], out["docstring"] = ok_contract, ok_doc
    out["plugin_lines"] = len((folder / "plugin.py").read_text().splitlines())
    test = folder / "test_port.py"
    if not test.exists() or "def test_" not in test.read_text():
        out["tests"] = "none"
        return out
    out["test_lines"] = len(test.read_text().splitlines())
    r = subprocess.run([sys.executable, "-m", "pytest", str(test), "-q", "-x", "-p", "no:cacheprovider", "--no-header", "--tb=short"],
                       capture_output=True, text=True, cwd=folder, timeout=90,
                       env={"PYTHONPATH": f"{folder}:{HERE}:{ROOT}:{ROOT / 'tests'}", "PATH": "/usr/bin:/bin", "CUDA_VISIBLE_DEVICES": "",
                            "PYTHONDONTWRITEBYTECODE": "1"})
    tail = (r.stdout + r.stderr)[-2500:]
    out["tests"] = "passed" if r.returncode == 0 else "failed"
    out["test_summary"] = tail.strip().splitlines()[-1] if tail.strip() else ""
    if r.returncode != 0:
        out["errors"].append("tests failed:\n" + tail)
    return out


if __name__ == "__main__":
    try:
        result = main(Path(sys.argv[1]).resolve())
    except Exception as exc:                                    # noqa: BLE001
        result = {"errors": [f"verify.py itself failed: {type(exc).__name__}: {exc}"]}
    print("VERIFY " + json.dumps(result, ensure_ascii=False))
