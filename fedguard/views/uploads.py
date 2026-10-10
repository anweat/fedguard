"""Views over client uploads, self-reports and earlier rounds."""
from __future__ import annotations

import dataclasses
from types import MappingProxyType

import torch

from fedguard.ops.lowrank import LowRank
from fedguard.core.types import ClientUpdate

_A, _B = ".lora_A.weight", ".lora_B.weight"


def lora_modules(state: dict[str, torch.Tensor]) -> list[str]:
    """Module prefixes that have both lora_A and lora_B entries, in a stable order."""
    prefixes = {k[: -len(_A)] for k in state if k.endswith(_A)}
    return sorted(p for p in prefixes if p + _B in state)


class ReportView:
    """`reports`: self-reported values only. Untrusted by definition."""

    def __init__(self, reports: dict[str, dict[str, float]], messages: dict[str, dict] | None = None,
                 attachments: dict[str, dict] | None = None):
        self._reports = {cid: MappingProxyType(dict(r)) for cid, r in reports.items()}
        self._messages = {src: dict(m) for src, m in (messages or {}).items()}
        self._attachments = {src: dict(m) for src, m in (attachments or {}).items()}

    @property
    def clients(self) -> list[str]:
        return list(self._reports)

    def __getitem__(self, cid: str):
        return self._reports[cid]

    def values(self, name: str) -> dict[str, float]:
        return {cid: r[name] for cid, r in self._reports.items() if name in r}

    def messages(self, name: str) -> dict[str, object]:
        """Channel messages named '<plugin>.<key>', by sender: client ids on the server, "server" on a client."""
        return {src: m[name] for src, m in self._messages.items() if name in m}

    def attachments(self, name: str) -> dict[str, torch.Tensor]:
        """Channel tensors named '<plugin>.<key>', by sender. As unverified as any message."""
        return {src: m[name] for src, m in self._attachments.items() if name in m}


class UploadView:
    """`uploads`: per-client LoRA uploads of one round, all relative to the same broadcast base."""

    def __init__(self, updates: list[ClientUpdate], lora_scale: float = 1.0):
        if len({u.client_id for u in updates}) != len(updates):
            raise ValueError("duplicate client ids")
        self._updates = {u.client_id: u for u in updates}
        self.scale = lora_scale
        first = next(iter(self._updates.values()), None)
        self.modules = lora_modules(first.base) if first else []
        self.reports = ReportView({u.client_id: u.reported for u in updates},
                                  {u.client_id: u.messages for u in updates},
                                  {u.client_id: u.attachments for u in updates})

    @property
    def clients(self) -> list[str]:
        return list(self._updates)

    def factors(self, cid: str, module: str) -> tuple[torch.Tensor, torch.Tensor]:
        """Uploaded (A, B) for one LoRA module (read-only by convention; do not modify in place)."""
        s = self._updates[cid].lora
        return s[module + _A], s[module + _B]

    def base_factors(self, module: str) -> tuple[torch.Tensor, torch.Tensor]:
        s = next(iter(self._updates.values())).base
        return s[module + _A], s[module + _B]

    def increment(self, cid: str, module: str) -> LowRank:
        """This round's functional change of one module, rank <= 2r."""
        A, B = self.factors(cid, module)
        A0, B0 = self.base_factors(module)
        return LowRank.increment(B, A, B0, A0, self.scale)

    def cumulative(self, cid: str, module: str) -> LowRank:
        A, B = self.factors(cid, module)
        return LowRank.lora(B, A, self.scale)

    def state(self, cid: str) -> dict[str, torch.Tensor]:
        """Full uploaded LoRA state of one client (read-only by convention)."""
        return dict(self._updates[cid].lora)

    def base_state(self) -> dict[str, torch.Tensor]:
        """The broadcast global LoRA every upload in this round started from."""
        return dict(next(iter(self._updates.values())).base)

    def replace(self, cid: str, lora: dict[str, torch.Tensor]) -> None:
        """Used by the runner when an applied `transform_update` replaces an upload."""
        self._updates[cid] = dataclasses.replace(self._updates[cid], lora=dict(lora))

    def factor_delta(self, cid: str) -> torch.Tensor:
        """Flattened (uploaded - base) over all factors: the factor-space update used by classic defenses."""
        u = self._updates[cid]
        return torch.cat([(u.lora[k] - u.base[k]).flatten() for k in sorted(u.base)])


class HistoryView:
    """`history`: what this side recorded in earlier rounds.

    Scalar features come from the runner; raw objects (uploads, broadcast bases) are read back from
    the recorder on demand and are only available when the run is being recorded.
    """

    def __init__(self, records: dict[str, list[tuple[int, dict[str, float]]]], recorder=None):
        self._records, self._recorder = records, recorder

    def rounds(self, cid: str) -> list[tuple[int, dict[str, float]]]:
        return list(self._records.get(cid, []))

    def last(self, cid: str) -> tuple[int, dict[str, float]] | None:
        r = self._records.get(cid)
        return r[-1] if r else None

    def _store(self):
        if self._recorder is None:
            raise LookupError("raw history needs a recorder; this run is not being recorded")
        return self._recorder

    def recorded_rounds(self) -> list[int]:
        return self._store().rounds()

    def upload(self, round_idx: int, cid: str) -> dict[str, torch.Tensor]:
        return self._store().load_update(round_idx, cid)

    def base(self, round_idx: int) -> dict[str, torch.Tensor]:
        return self._store().load_base(round_idx)

    def aggregate(self, round_idx: int) -> dict[str, torch.Tensor]:
        return self._store().load_aggregate(round_idx)
