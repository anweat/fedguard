#!/usr/bin/env python3
"""Build the tree that is published, from an allow-list. The working repository also holds material that
is not for publication (project applications, presentation drafts, an earlier prototype) and files derived
from an upstream without a license; its history contains them too. So the public repository is not this
repository's history: it is the tree this script writes, committed on its own.

    python tools/make_public.py <target directory>      # target must be empty or a previous export

What goes in: the library, its tests, the host integrations, the experiment drivers, the environment files,
the literature notes and the dated design and result notes, and the text summaries of the real-model runs.
What stays out: everything not matched below, and, of what is matched,
  - files derived from FedLLM-Attack (published without a license): only their patches are shipped,
    integrations/derive_fedllm_attack.sh rebuilds them from a checkout of that repository
  - copies of paper cards that were inputs of later reading passes (`*/text/`), caches, raw model answers
  - the raw harvested paper metadata (abstracts are third parties' text); e-mail addresses that came along in
    harvested titles are removed from the tables that are shipped
The export fails if a secret-looking or machine-specific string is found in what would be published.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = [          # git pathspecs, relative to the repository root
    "README.md", "PROGRESS.md", "LICENSE", "NOTICE.md", "pyproject.toml", ".gitattributes", "tools/make_public.py",
    "fedguard", "tests", "integrations", "experiments", "envs", "external/UPSTREAM.md",
    "survey/README.md", "survey/paper_index.md", "survey/library_manifest.json", "survey/scripts", "survey/notes", "survey/harvest",
    "output/poisoning_study/2026-*", "output/poisoning_study/figures",
]
EXCLUDE = [re.compile(p) for p in (
    r"^experiments/fedllm_attack/run_guarded\.py$",            # derived from FedLLM-Attack: the patch is shipped instead
    r"^integrations/fedllm_attack/main_sft_guard\.py$",
    r"^survey/harvest/[^/]+/[^/]+/text/",                      # paper cards copied as inputs of a later pass
    r"/answer_\d+\.md$", r"(^|/)ledger\.json$",
    r"^survey/harvest/[^/]+/papers\.jsonl$",                    # raw third-party metadata with abstracts; harvest.py rebuilds it
)]
REDACT = re.compile(r"^survey/harvest/.*\.(csv|jsonl)$")


def redact(line: str) -> str:
    """Remove e-mail addresses around each @ of a line, looking only at the characters next to it."""
    out, last = [], 0
    for m in re.finditer("@", line):
        i = m.start()
        left = re.search(r"[\w.+-]{1,64}$", line[max(last, i - 64):i])
        right = re.match(r"[\w-]{1,64}(?:\.[\w-]{1,24}){1,3}", line[i + 1:i + 140])
        if left and right:
            out.append(line[last:i - len(left.group())] + "[address removed]")
            last = i + 1 + right.end()
    return "".join(out) + line[last:]
RESULTS = ROOT / "runs" / "autodl"                             # not in git: text summaries are copied from here
RESULT_FILES = ("status.tsv", "control.json")
FORBIDDEN = [re.compile(p) for p in (
    r"@(outlook|gmail|qq|163|126|hotmail|foxmail)\.com", r"/Users/[a-z]", r"seetacloud", r"pro-[0-9a-f]{12}",
    r"\bgh[pos]_[A-Za-z0-9]{20,}", r"\bsk-[A-Za-z0-9]{20,}", r"\bhf_[A-Za-z0-9]{20,}", r"BEGIN [A-Z ]*PRIVATE KEY",
)]
PUBLIC_IGNORE = """# built locally, not redistributed (see integrations/derive_fedllm_attack.sh)
experiments/fedllm_attack/run_guarded.py
integrations/fedllm_attack/main_sft_guard.py
# upstream frameworks, models, runs
external/*
!external/UPSTREAM.md
runs/
records/
*.safetensors
*.bin
*.pt
__pycache__/
*.pyc
.venv/
envs/*/.venv/
.pytest_cache/
*.egg-info/
.DS_Store
"""


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", *INCLUDE], capture_output=True, check=True).stdout
    return [p for p in out.decode().split("\0") if p and not any(x.search(p) for x in EXCLUDE)]


def main(target: Path) -> int:
    target = target.resolve()
    if ROOT == target or ROOT in target.parents and target.name != "public":
        sys.exit("the target must not be inside the working tree (except ./public)")
    target.mkdir(parents=True, exist_ok=True)
    for child in target.iterdir():                             # a previous export: replace everything but its .git
        if child.name != ".git":
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    files = tracked()
    for rel in files:
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if REDACT.search(rel):
            lines = (ROOT / rel).read_text(encoding="utf-8", errors="replace").split("\n")       # only where an @ occurs: the tables are large
            dst.write_text("\n".join(redact(line) if "@" in line else line for line in lines), encoding="utf-8")
        else:
            shutil.copy2(ROOT / rel, dst)
    copied = 0
    if RESULTS.exists():                                       # what the real-model runs reported, as text
        for src in sorted(RESULTS.rglob("*")):
            if src.is_file() and (src.name in RESULT_FILES or src.suffix == ".summary"):
                dst = target / "results" / "autodl" / src.relative_to(RESULTS)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(src.read_text(encoding="utf-8", errors="replace").replace("/root/autodl-tmp/innovation/", ""), encoding="utf-8")
                copied += 1
    (target / ".gitignore").write_text(PUBLIC_IGNORE, encoding="utf-8")
    problems = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(target).parts and path.suffix not in (".png", ".svg"):
            text = path.read_text(encoding="utf-8", errors="replace")
            problems += [f"{path.relative_to(target)}: matches {x.pattern}" for x in FORBIDDEN if x.search(text) and path.name != "make_public.py"]
    print(f"{len(files)} tracked files, {copied} result summaries -> {target}")
    if problems:
        print("NOT FIT FOR PUBLICATION:\n  " + "\n  ".join(problems[:40]))
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1])))
