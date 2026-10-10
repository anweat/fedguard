"""`aggregate`: who takes part in this round's aggregation, with what weight, and what came out."""
from __future__ import annotations

from dataclasses import dataclass, field

import torch


@dataclass(frozen=True)
class AggregateView:
    """At SERVER_AGGREGATE `weights` are the weights about to be used and `result` is None.
    At SERVER_POST_AGGREGATE they are the weights actually used and `result` is the new global LoRA.

    Under a deployment without per-client uploads this is all the server has.
    """
    sampled: tuple[str, ...]                      # clients selected this round
    weights: dict[str, float] = field(default_factory=dict)   # clients aggregated -> weight
    base: dict[str, torch.Tensor] | None = None   # the global LoRA this round started from
    result: dict[str, torch.Tensor] | None = None
    rule: str = ""                                # name of the aggregation rule, as the adapter knows it

    @property
    def aggregated(self) -> list[str]:
        return list(self.weights)

    def global_delta(self) -> dict[str, torch.Tensor]:
        """result - base per factor: this round's change of the global LoRA in factor space."""
        if self.result is None or self.base is None:
            raise LookupError("the aggregation result is only available at server_post_aggregate")
        return {k: self.result[k] - self.base[k] for k in self.result if k in self.base}


class OutgoingView:
    """`outgoing`: the global LoRA about to be sent this round and the clients it goes to.

    Every recipient gets the same state unless an applied `transform_broadcast` gave it its own.
    """

    def __init__(self, state: dict[str, torch.Tensor], recipients: list[str]):
        self._state, self.recipients, self._per_client = dict(state), tuple(recipients), {}

    def state(self) -> dict[str, torch.Tensor]:
        """Read-only by convention; do not modify in place."""
        return dict(self._state)

    def for_client(self, client_id: str) -> dict[str, torch.Tensor]:
        return dict(self._per_client.get(client_id, self._state))

    def customized(self) -> list[str]:
        return sorted(self._per_client)

    def replace(self, target: str, state: dict[str, torch.Tensor]) -> None:
        """Used by the runner when an applied `transform_broadcast` changes what is sent ("*" = everyone)."""
        if target == "*":
            self._state, self._per_client = dict(state), {}
        else:
            self._per_client[target] = dict(state)
