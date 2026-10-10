"""Record layer: the raw objects that cross a trust boundary each round (safetensors), plus what plugins
reported and what was done about it (JSON).

Layout, server side (scope=None):
  <root>/<run_id>/run.json                              run spec, deployment, plugins, resource hashes
  <root>/<run_id>/round_0003/base.safetensors           broadcast global LoRA
  <root>/<run_id>/round_0003/client_<id>.safetensors    one client's upload
  <root>/<run_id>/round_0003/aggregate.safetensors      the round's aggregation result
  <root>/<run_id>/round_0003/round.json                 reports, findings, decision, meta, object hashes, link
A client's own records (scope=<client id>) live under <root>/<run_id>/clients/<id>/ in the same shape.

round.json carries the content hash of every object written that round and the hash of the previous
round.json, so a record cannot be edited after the fact without breaking `verify()`. Content hashes
do not depend on the file encoding: the server's `base` and a client's `received` hash equal exactly
when the tensors are equal.
Never uses pickle; nothing here executes code from loaded files.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
from enum import Enum
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

from fedguard.core.types import ClientUpdate, Decision, Findings

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def _jsonable(x):
    if dataclasses.is_dataclass(x):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(x).items()}
    if isinstance(x, Enum):
        return x.value
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (set, frozenset)):
        return sorted(_jsonable(v) for v in x)
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    if isinstance(x, torch.Tensor):
        return x.tolist()
    return x


def state_hash(state: dict[str, torch.Tensor]) -> str:
    """SHA-256 over names, dtypes, shapes and raw values, in key order."""
    h = hashlib.sha256()
    for k in sorted(state):
        t = state[k].detach().to("cpu").contiguous()
        h.update(f"{k}|{t.dtype}|{tuple(t.shape)}|".encode())
        h.update(t.view(torch.uint8).numpy().tobytes() if t.numel() else b"")
    return h.hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tensors(state: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {k: v.detach().to("cpu").contiguous().clone() for k, v in state.items()}


class Recorder:
    """Writes and reads one side's record of a run: the objects that passed through (content-hashed), what
    plugins reported and proposed, and a hash chain over the rounds. Sample text is never written.
    """
    def __init__(self, root: str | Path, run_id: str, save_factors: bool = True, scope: str | None = None):
        """scope: None for the server's records, a client id for that client's own records."""
        if not _SAFE_ID.match(run_id):
            raise ValueError("run_id may contain only letters, digits, '_', '.', '-'")
        if scope is not None and not _SAFE_ID.match(scope):
            raise ValueError(f"unsafe client id for a directory name: {scope!r}")
        self.dir = Path(root) / run_id if scope is None else Path(root) / run_id / "clients" / scope
        self.dir.mkdir(parents=True, exist_ok=True)
        self.save_factors, self.scope = save_factors, scope
        self._hashes: dict[int, dict[str, str]] = {}

    def _round_dir(self, round_idx: int) -> Path:
        d = self.dir / f"round_{round_idx:04d}"
        d.mkdir(exist_ok=True)
        return d

    # ----- writing -----
    def write_run(self, info: dict) -> None:
        (self.dir / "run.json").write_text(json.dumps(_jsonable(info), indent=1, ensure_ascii=False, sort_keys=True))

    def write_object(self, round_idx: int, name: str, state: dict[str, torch.Tensor]) -> str:
        """Store one named tensor object of a round; returns its content hash."""
        if not _SAFE_ID.match(name):
            raise ValueError(f"unsafe object name: {name!r}")
        digest = state_hash(state)
        self._hashes.setdefault(round_idx, {})[name] = digest
        if self.save_factors:
            save_file(_tensors(state), str(self._round_dir(round_idx) / f"{name}.safetensors"))
        return digest

    def write_base(self, round_idx: int, base: dict[str, torch.Tensor]) -> None:
        self.write_object(round_idx, "base", base)

    def write_aggregate(self, round_idx: int, state: dict[str, torch.Tensor]) -> None:
        self.write_object(round_idx, "aggregate", state)

    def write_update(self, update: ClientUpdate) -> None:
        if not _SAFE_ID.match(update.client_id):
            raise ValueError(f"unsafe client id for a file name: {update.client_id!r}")
        d = self._round_dir(update.round)
        self.write_object(update.round, f"client_{update.client_id}", update.lora)
        reports = d / "reports.json"
        data = json.loads(reports.read_text()) if reports.exists() else {}
        data[update.client_id] = {"reported": update.reported, "messages": update.messages}
        if update.attachments:
            self.write_object(update.round, f"attach_{update.client_id}", update.attachments)
        reports.write_text(json.dumps(data, indent=1, sort_keys=True))

    def write_lines(self, round_idx: int, name: str, records: list[dict]) -> None:
        """Store a list of small JSON records of a round as <name>.jsonl (data manifest, step trace)."""
        if not _SAFE_ID.match(name):
            raise ValueError(f"unsafe name: {name!r}")
        text = "".join(json.dumps(_jsonable(r), ensure_ascii=False) + "\n" for r in records)
        self._hashes.setdefault(round_idx, {})[f"{name}.jsonl"] = hashlib.sha256(text.encode()).hexdigest()
        (self._round_dir(round_idx) / f"{name}.jsonl").write_text(text, encoding="utf-8")

    def write_evaluation(self, round_idx: int, name: str, records: list[dict], model: dict | None = None) -> None:
        """Store one evaluation of the model of a round: a list of {prompt/input hash or text, output, scores...}
        records, as the evaluation code produced them. `model` (the evaluated LoRA) is hashed, not stored,
        so the result can be tied to a recorded `base` or `aggregate`.

        Evaluation logic lives outside the library; this is only where its output is kept. Call it before
        the round is closed for the entry to be covered by the round's hash record.
        """
        rows = ([{"evaluated_model": state_hash(model)}] if model is not None else []) + list(records)
        self.write_lines(round_idx, f"eval_{name}", rows)

    def load_evaluation(self, round_idx: int, name: str) -> list[dict]:
        return self.load_lines(round_idx, f"eval_{name}")

    def evaluations(self, round_idx: int) -> list[str]:
        d = self.dir / f"round_{round_idx:04d}"
        return sorted(p.stem[len("eval_"):] for p in d.glob("eval_*.jsonl"))

    def _previous_link(self, round_idx: int) -> str | None:
        earlier = [t for t in self.rounds() if t < round_idx and (self.dir / f"round_{t:04d}" / "round.json").exists()]
        return _file_hash(self.dir / f"round_{earlier[-1]:04d}" / "round.json") if earlier else None

    def write_round(self, round_idx: int, *, findings: list[Findings], decision: Decision,
                    rejected: dict[str, str], meta: dict) -> None:
        payload = {"round": round_idx, "meta": meta, "rejected": rejected,
                   "decision": decision, "findings": findings,
                   "objects": self._hashes.pop(round_idx, {}), "prev": self._previous_link(round_idx)}
        (self._round_dir(round_idx) / "round.json").write_text(
            json.dumps(_jsonable(payload), indent=1, ensure_ascii=False))

    # ----- reading back -----
    def rounds(self) -> list[int]:
        return sorted(int(p.name.split("_")[1]) for p in self.dir.glob("round_*"))

    def clients(self, round_idx: int) -> list[str]:
        return sorted(p.stem[len("client_"):] for p in (self.dir / f"round_{round_idx:04d}").glob("client_*.safetensors"))

    def load_object(self, round_idx: int, name: str) -> dict[str, torch.Tensor]:
        return load_file(str(self.dir / f"round_{round_idx:04d}" / f"{name}.safetensors"))

    def load_base(self, round_idx: int) -> dict[str, torch.Tensor]:
        return self.load_object(round_idx, "base")

    def load_aggregate(self, round_idx: int) -> dict[str, torch.Tensor]:
        return self.load_object(round_idx, "aggregate")

    def load_update(self, round_idx: int, client_id: str) -> dict[str, torch.Tensor]:
        return self.load_object(round_idx, f"client_{client_id}")

    def load_reports(self, round_idx: int) -> dict:
        p = self.dir / f"round_{round_idx:04d}" / "reports.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def load_round(self, round_idx: int) -> dict:
        return json.loads((self.dir / f"round_{round_idx:04d}" / "round.json").read_text())

    def load_lines(self, round_idx: int, name: str) -> list[dict]:
        p = self.dir / f"round_{round_idx:04d}" / f"{name}.jsonl"
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def has_object(self, round_idx: int, name: str) -> bool:
        return (self.dir / f"round_{round_idx:04d}" / f"{name}.safetensors").exists()

    def load_run(self) -> dict:
        p = self.dir / "run.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def verify(self) -> list[str]:
        """Check the link between consecutive round.json files and every stored object against its
        recorded hash. Returns the problems found; empty means the record is intact.

        Rounds written before hashes were recorded have neither field and are reported as unlinked.
        """
        problems, prev_file = [], None
        for t in self.rounds():
            path = self.dir / f"round_{t:04d}" / "round.json"
            if not path.exists():
                continue
            r = json.loads(path.read_text())
            if "objects" not in r:
                problems.append(f"round {t}: written without hashes")
            else:
                expected = _file_hash(prev_file) if prev_file is not None else None
                if r.get("prev") != expected:
                    problems.append(f"round {t}: link to the previous round does not match")
                for name, digest in r["objects"].items():
                    if name.endswith(".jsonl"):
                        f = path.parent / name
                        actual = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else digest
                    else:
                        f = path.parent / f"{name}.safetensors"
                        actual = state_hash(load_file(str(f))) if f.exists() else digest
                    if actual != digest:
                        problems.append(f"round {t}: {name} differs from its recorded hash")
            prev_file = path
        return problems
