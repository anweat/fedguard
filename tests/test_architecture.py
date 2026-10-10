"""The layering of the library, checked on the import statements. A violation here means a layer started
to depend on something above it, or host-framework code leaked out of the adapters."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "fedguard"
HOST_PACKAGES = {"flwr", "transformers", "peft", "trl", "datasets"}
# layer -> what it may import from the library ("core.types" is the vocabulary every layer shares)
ALLOWED = {
    "ops": {"ops"},
    "views": {"views", "ops", "core.types"},
    "recorder": {"recorder", "core.types"},
    "core": {"core", "views", "recorder"},
    "client": {"core", "views"},
    "replay": {"client", "core", "views", "recorder"},
    "plugins": {"plugins", "core", "ops"},
    "methods": {"methods", "core", "ops"},
    "adapters": {"adapters", "client", "core", "views", "recorder", "ops"},
    "policy": {"core", "plugins", "methods", "adapters"},      # adapters: the host table, for `python -m fedguard.policy`
    "kb": {"kb", "core", "ops", "methods", "plugins", "adapters"},
}
TOOLS = {"methods/__main__.py"}        # command-line generators that read the knowledge base and the host profiles


def imports(path: Path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


def test_layers_only_import_downward_and_host_frameworks_stay_in_the_adapters():
    problems = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        layer = rel.split("/")[0].removesuffix(".py")
        if layer == "__init__" or rel in TOOLS:
            continue
        for mod in imports(path):
            top = mod.split(".")[0]
            if top in HOST_PACKAGES and layer != "adapters":
                problems.append(f"{rel}: imports {mod}; host frameworks belong in fedguard/adapters")
            if top != "fedguard":
                continue
            target = ".".join(mod.split(".")[1:3])
            if not any(target == a or target.startswith(a + ".") or target.split(".")[0] == a for a in ALLOWED[layer]):
                problems.append(f"{rel}: layer {layer!r} imports {mod}")
    assert not problems, "\n".join(problems)


def test_every_module_and_public_class_says_what_it_is():
    missing = []
    for path in sorted(ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if tree.body and not ast.get_docstring(tree):
            missing.append(f"{path.relative_to(ROOT)}: no module docstring")
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_") and not ast.get_docstring(node):
                missing.append(f"{path.relative_to(ROOT)}: class {node.name} has no docstring")
    assert not missing, "\n".join(missing)
