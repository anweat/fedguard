"""A made-up instruction dataset in the column layout of vicgalle/alpaca-gpt4 (instruction, input, output, text).
OpenFedLLM takes datasets by their hub name; the checks point it at this one instead of downloading.

    arith_dataset.py <dir> [rows]      writes <dir>/train.jsonl
"""
import json
import random
import sys
from pathlib import Path

d, n = Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 256
d.mkdir(parents=True, exist_ok=True)
r = random.Random(0)
with open(d / "train.jsonl", "w") as f:
    for _ in range(n):
        a, b = r.randint(1, 99), r.randint(1, 99)
        f.write(json.dumps({"instruction": f"What is {a} plus {b}?", "input": "", "output": f"{a} plus {b} is {a + b}.", "text": ""}) + "\n")
