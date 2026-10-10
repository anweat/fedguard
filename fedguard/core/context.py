"""Per-invocation context handed to a plugin; exposes only the data kinds it declared."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np

from fedguard.core.types import KINDS, Findings, RunSpec, Stage


@dataclass
class StageContext:
    """What a plugin's `run` receives: where and when it runs, and the views it declared. Asking for a data
    kind that was not declared raises PermissionError; one that does not exist at this stage, LookupError.
    """
    plugin: str
    stage: Stage
    round: int
    participants: list[str]
    spec: RunSpec
    needs: frozenset[str]
    rng: np.random.Generator
    state: dict                                   # plugin-private, kept for the whole run
    round_state: dict = field(default_factory=dict)   # plugin-private, emptied when a round begins
    step_state: dict = field(default_factory=dict)    # plugin-private, emptied when a local training step (or a round) begins
    upstream: tuple[Findings, ...] = ()           # earlier findings of this round (read-only)
    _views: dict = field(default_factory=dict, repr=False)
    _resources: MappingProxyType = field(default_factory=lambda: MappingProxyType({}), repr=False)

    def view(self, kind: str):
        if kind not in KINDS:
            raise KeyError(f"unknown data kind {kind!r}")
        if kind not in self.needs:
            raise PermissionError(f"{self.plugin} did not declare {kind!r} in `needs`")
        if kind not in self._views:
            raise LookupError(f"{kind!r} is not available at {self.stage.value} in this run")
        return self._views[kind]

    def resource(self, name: str):
        """A defender-supplied asset the plugin declared in `resources`."""
        if name not in self._resources:
            raise PermissionError(f"{self.plugin} did not declare resource {name!r}")
        return self._resources[name]

    # Convenience accessors, one per data kind
    @property
    def uploads(self):
        return self.view("uploads")

    @property
    def reports(self):
        return self.view("reports")

    @property
    def history(self):
        return self.view("history")

    @property
    def model_handle(self):
        return self.view("model_handle")

    @property
    def aggregate(self):
        return self.view("aggregate")

    @property
    def data(self):
        return self.view("data")

    @property
    def received_model(self):
        return self.view("received_model")

    @property
    def train_trace(self):
        return self.view("train_trace")

    @property
    def loss(self):
        return self.view("loss")

    @property
    def gradients(self):
        return self.view("gradients")

    @property
    def outgoing(self):
        return self.view("outgoing")

    @property
    def local_update(self):
        return self.view("local_update")

    def upstream_feature(self, feature: str) -> dict[str, float]:
        """Values of '<plugin>.<key>' computed earlier this round, per subject. Raises if the plugin did not run."""
        plugin, key = feature.split(".", 1)
        for f in self.upstream:
            if f.module == plugin and f.error is None:
                return {c: v[key] for c, v in f.features.items() if key in v}
        raise LookupError(f"upstream feature {feature!r} not found; mount {plugin!r} before {self.plugin!r}")

    def attachment(self, name: str) -> dict:
        """Tensors sent over the channel as '<plugin>.<key>', by sender. Unverified, like every message."""
        return self.view("reports").attachments(name)

    def findings(self, **kwargs) -> Findings:
        return Findings(module=self.plugin, stage=self.stage, round=self.round, **kwargs)
