#!/usr/bin/env python3
"""Build the API reference handed to the porting model, from the library's own source: every public
class and function of the layers a plugin may use, with its signature and docstring. Regenerated before
each batch, so the model is never told about an interface that no longer exists.

    python build_reference.py            # writes reference.txt next to this file
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FILES = ["core/plugin.py", "core/context.py", "client.py", "views/uploads.py", "views/aggregate.py", "views/client.py", "views/model.py",
         *sorted(f"ops/{p.name}" for p in (ROOT / "fedguard" / "ops").glob("*.py") if p.name != "__init__.py")]
VERBATIM = ["core/types.py"]             # short, and its comments are the specification of stages, kinds and actions


def describe(node, indent: str = "") -> list[str]:
    out = []
    if isinstance(node, ast.ClassDef):
        bases = f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
        out.append(f"{indent}class {node.name}{bases}:")
        if doc := ast.get_docstring(node):
            out += [f"{indent}    | {line}" for line in doc.splitlines()]
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and not item.target.id.startswith("_"):
                out.append(f"{indent}    {ast.unparse(item)}")
            elif isinstance(item, ast.FunctionDef) and (not item.name.startswith("_") or item.name == "__init__"):
                out += describe(item, indent + "    ")
    elif isinstance(node, ast.FunctionDef):
        deco = "".join(f"@{ast.unparse(d)} " for d in node.decorator_list)
        ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        out.append(f"{indent}{deco}def {node.name}({ast.unparse(node.args)}){ret}")
        if doc := ast.get_docstring(node):
            out += [f"{indent}    | {line}" for line in doc.splitlines()]
    return out


def build() -> str:
    parts = []
    for rel in VERBATIM:
        parts += [f"===== fedguard/{rel} (verbatim) =====", (ROOT / "fedguard" / rel).read_text(encoding="utf-8")]
    for rel in FILES:
        tree = ast.parse((ROOT / "fedguard" / rel).read_text(encoding="utf-8"))
        parts.append(f"===== fedguard/{rel}  (import as fedguard.{rel[:-3].replace('/', '.')}) =====")
        if doc := ast.get_docstring(tree):
            parts += [f"| {line}" for line in doc.splitlines()]
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and not node.name.startswith("_"):
                parts += describe(node) + [""]
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    text = build()
    (HERE / "reference.txt").write_text(text, encoding="utf-8")
    print(f"reference.txt: {len(text)} chars, {text.count(chr(10))} lines", file=sys.stderr)
