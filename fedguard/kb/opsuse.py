"""Which operators each plugin class calls, read from the source (no import of the plugins' dependencies,
no run). Used by the knowledge base to list operator reuse instead of having anyone fill it in by hand.

An operator earns its place in fedguard.ops by being specific to LoRA or by being shared by two or more
methods; `usage()` is how that is checked.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
from collections import defaultdict
from pathlib import Path

import fedguard.ops as ops_pkg

PKG = Path(__file__).resolve().parents[1]

OPS = {}
for m in pkgutil.iter_modules(ops_pkg.__path__):
    mod = importlib.import_module(f"fedguard.ops.{m.name}")
    for n, f in inspect.getmembers(mod, inspect.isfunction):
        if f.__module__ == mod.__name__ and not n.startswith("_"):
            OPS[f"{m.name}.{n}"] = f


def calls(node, aliases: dict[str, str]) -> tuple[set[str], int, set[str]]:
    """(operators called, raw torch calls, local helper functions called) inside an AST node."""
    used, torch_calls, helpers = set(), 0, set()
    for c in ast.walk(node):
        if not isinstance(c, ast.Call):
            continue
        f = c.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            if f.value.id in aliases and f"{aliases[f.value.id]}.{f.attr}" in OPS:
                used.add(f"{aliases[f.value.id]}.{f.attr}")
            elif f.value.id == "torch":
                torch_calls += 1
        elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) and getattr(f.value.value, "id", "") == "torch":
            torch_calls += 1                      # torch.linalg.x, torch.nn.x
        elif isinstance(f, ast.Name):
            if f.id in aliases and aliases[f.id] in OPS:
                used.add(aliases[f.id])
            else:
                helpers.add(f.id)
    return used, torch_calls, helpers


def usage() -> dict:
    classes, by_op = {}, defaultdict(set)
    for path in sorted((PKG / "methods").glob("*.py")) + sorted((PKG / "plugins").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        aliases = {}
        for n in tree.body:
            if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("fedguard.ops"):
                for a in n.names:
                    name = a.asname or a.name
                    aliases[name] = a.name if n.module == "fedguard.ops" else f"{n.module.split('.')[-1]}.{a.name}"
            if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("fedguard.methods"):
                for a in n.names:                  # helpers imported from another methods file count through that file
                    aliases.setdefault(a.asname or a.name, f"@{n.module.split('.')[-1]}.{a.name}")
        funcs = {n.name: calls(n, aliases) for n in tree.body if isinstance(n, ast.FunctionDef)}

        def closure(names, seen=None):
            seen = seen if seen is not None else set()
            used, t = set(), 0
            for h in names:
                if h in funcs and h not in seen:
                    seen.add(h)
                    u, tc, more = funcs[h]
                    u2, t2 = closure(more, seen)
                    used |= u | u2
                    t += tc + t2
            return used, t

        for n in tree.body:
            if not isinstance(n, ast.ClassDef):
                continue
            name = next((getattr(s.value, "value", None) for s in n.body if isinstance(s, ast.Assign)
                         and any(getattr(t, "id", "") == "name" for t in s.targets)), None)
            if name is None:
                for s in n.body:                   # name, version = "x", "1"  /  name, at, version = ...
                    if isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Tuple) and isinstance(s.value, ast.Tuple):
                        for t, v in zip(s.targets[0].elts, s.value.elts):
                            if getattr(t, "id", "") == "name" and isinstance(v, ast.Constant):
                                name = v.value
            if not isinstance(name, str) or not name:
                continue
            used, t, helpers = calls(n, aliases)
            u2, t2 = closure(helpers)
            bases = [b.id for b in n.bases if isinstance(b, ast.Name)]
            classes[name] = {"file": path.name, "class": n.name, "ops": sorted(used | u2), "torch_calls": t + t2, "bases": bases, "lines": n.end_lineno - n.lineno + 1}
        for c in classes.values():                 # inherit what a base class in the same file uses
            for b in c["bases"]:
                base = next((x for x in classes.values() if x["class"] == b and x["file"] == c["file"]), None)
                node = next((x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == b), None)
                if node is not None and base is None:
                    u, t, h = calls(node, aliases)
                    u2, t2 = closure(h)
                    c["ops"] = sorted(set(c["ops"]) | u | u2)
                    c["torch_calls"] += t + t2
    for name, c in classes.items():
        for o in c["ops"]:
            by_op[o].add(name)
    return {"classes": classes, "operators": {o: sorted(by_op.get(o, ())) for o in sorted(OPS)}}
