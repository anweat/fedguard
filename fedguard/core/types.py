"""Core data types: stages, data kinds, actions, updates, findings, decisions."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import torch


class Stage(str, Enum):
    """Where in a federated round an object crosses a trust boundary, in the order a round reaches them.

    Not tied to any attack or defense. A plugin may mount at several stages of its side.
    """
    SERVER_DISTRIBUTE = "server_distribute"          # the global model about to be sent, per recipient
    CLIENT_ANNOUNCE = "client_announce"              # model and data are in; the client may send a summary first
    SERVER_EXCHANGE = "server_exchange"              # the server answers those summaries, before any training
    CLIENT_PRE_TRAIN = "client_pre_train"            # local data and the received global model
    CLIENT_LOSS = "client_loss"                      # the batch loss is computed, backward has not run (trainer extension only)
    CLIENT_PRE_STEP = "client_pre_step"              # gradients are computed, the optimizer has not stepped
    CLIENT_STEP = "client_step"                      # after each local training step
    CLIENT_POST_TRAIN = "client_post_train"          # local result, before upload
    SERVER_RECEIVE = "server_receive"                # uploads arrive
    SERVER_AGGREGATE = "server_aggregate"            # who is aggregated, with what weight
    SERVER_POST_AGGREGATE = "server_post_aggregate"  # the new global model, every round


# Data kinds a plugin may ask for, and the side that handles them. A side only ever sees what
# passes through it; neither side is trusted by default.
KIND_SIDE: dict[str, str] = {
    "data": "client",            # local samples and the data manifest
    "received_model": "client",  # the global LoRA this client received
    "train_trace": "client",     # per-step scalars, and the current LoRA on request
    "loss": "client",            # this step's batch, model outputs and loss, before backward
    "gradients": "client",       # this step's gradients of the trainable parameters
    "local_update": "client",    # the local LoRA before upload
    "outgoing": "server",        # the global LoRA about to be sent, and to whom
    "uploads": "server",         # per-client uploaded LoRA
    "aggregate": "server",       # participants, weights, aggregation result
    "reports": "both",           # self-reported values and channel messages; never verified
    "model_handle": "both",      # a model the plugin may run forward/backward passes on
    "history": "both",           # this side's records of earlier rounds
}
KINDS = frozenset(KIND_SIDE)

_CLIENT = (Stage.CLIENT_ANNOUNCE, Stage.CLIENT_PRE_TRAIN, Stage.CLIENT_LOSS, Stage.CLIENT_PRE_STEP, Stage.CLIENT_STEP, Stage.CLIENT_POST_TRAIN)
_SERVER = (Stage.SERVER_DISTRIBUTE, Stage.SERVER_EXCHANGE, Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE,
           Stage.SERVER_POST_AGGREGATE)
STAGE_SIDE: dict[Stage, str] = {**{s: "client" for s in _CLIENT}, **{s: "server" for s in _SERVER}}

_COMMON = {"reports", "model_handle", "history"}
_LOCAL = _COMMON | {"data", "received_model"}
STAGE_KINDS: dict[Stage, frozenset[str]] = {
    Stage.SERVER_DISTRIBUTE: frozenset(_COMMON | {"outgoing"}),
    Stage.CLIENT_ANNOUNCE: frozenset(_LOCAL),
    Stage.SERVER_EXCHANGE: frozenset(_COMMON),
    Stage.CLIENT_PRE_TRAIN: frozenset(_LOCAL),
    Stage.CLIENT_LOSS: frozenset(_LOCAL | {"train_trace", "loss"}),
    Stage.CLIENT_PRE_STEP: frozenset(_LOCAL | {"train_trace", "gradients"}),
    Stage.CLIENT_STEP: frozenset(_LOCAL | {"train_trace"}),
    Stage.CLIENT_POST_TRAIN: frozenset(_LOCAL | {"train_trace", "local_update"}),
    Stage.SERVER_RECEIVE: frozenset(_COMMON | {"uploads"}),
    Stage.SERVER_AGGREGATE: frozenset(_COMMON | {"uploads", "aggregate"}),
    Stage.SERVER_POST_AGGREGATE: frozenset(_COMMON | {"uploads", "aggregate"}),
}

# Interventions. Off unless the runner is told to apply them (for all plugins, or by name).
ACTION_STAGES: dict[str, frozenset[Stage]] = {
    "transform_broadcast": frozenset({Stage.SERVER_DISTRIBUTE}),
    "transform_received": frozenset({Stage.CLIENT_PRE_TRAIN}),
    "mask_samples": frozenset({Stage.CLIENT_PRE_TRAIN}),
    "edit_samples": frozenset({Stage.CLIENT_PRE_TRAIN}),
    "transform_loss": frozenset({Stage.CLIENT_LOSS}),
    "transform_gradients": frozenset({Stage.CLIENT_PRE_STEP}),
    "transform_update": frozenset({Stage.CLIENT_POST_TRAIN, Stage.SERVER_RECEIVE}),
    "select_and_weight": frozenset({Stage.SERVER_AGGREGATE}),
    "replace_global": frozenset({Stage.SERVER_POST_AGGREGATE}),
}


def side_of(stage: Stage) -> str:
    return STAGE_SIDE[stage]


@dataclass(frozen=True)
class RunSpec:
    """Static facts about a run that plugins may rely on.

    `unavailable` lists data kinds this deployment cannot provide (e.g. {"uploads"} under secure
    aggregation); plugins needing them are refused before the first round.
    """
    run_id: str
    seed: int = 0
    lora_scale: float = 1.0          # alpha / r
    num_clients: int | None = None
    unavailable: frozenset[str] = frozenset()
    extra: dict = field(default_factory=dict)


@dataclass
class ClientUpdate:
    """One client's upload in one round, as seen by the server.

    `lora` and `base` are PEFT state dicts (``...lora_A.weight`` / ``...lora_B.weight``).
    `reported` holds values the client claims (e.g. num_examples, train_loss); they are
    never verified by construction and must be treated as untrusted.
    """
    client_id: str
    round: int
    lora: dict[str, torch.Tensor]
    base: dict[str, torch.Tensor]
    reported: dict[str, float] = field(default_factory=dict)
    messages: dict[str, object] = field(default_factory=dict)   # channel messages from the client's plugins; untrusted
    attachments: dict[str, torch.Tensor] = field(default_factory=dict)   # tensors sent over the channel; untrusted


MESSAGE_LIMIT_BYTES = 65536


def check_messages(messages: dict) -> None:
    """Channel messages are small typed records: numbers, strings, booleans, or flat lists of them."""
    import json
    for k, v in messages.items():
        items = v if isinstance(v, list) else [v]
        if not isinstance(k, str) or not k or not all(isinstance(x, (int, float, str, bool)) for x in items):
            raise TypeError(f"message {k!r}: only numbers, strings, booleans and flat lists of them can be sent")
    if len(json.dumps(messages)) > MESSAGE_LIMIT_BYTES:
        raise ValueError(f"messages exceed {MESSAGE_LIMIT_BYTES} bytes; the channel is for small records, not tensors")


@dataclass
class Decision:
    """The `select_and_weight` action proposed by a plugin at SERVER_AGGREGATE.

    weights: absolute aggregation weights per client (clients not listed keep their weight).
    excluded: clients removed from this round's aggregation.
    flags: human-readable reasons per client.
    """
    weights: dict[str, float] = field(default_factory=dict)
    excluded: set[str] = field(default_factory=set)
    flags: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def merge(decisions: list["Decision"]) -> "Decision":
        """Union of exclusions, element-wise minimum of weights.

        Stacking several detectors this way can only remove more clients, never fewer; with
        correlated detectors it amplifies false exclusions.
        """
        out = Decision()
        for d in decisions:
            out.excluded |= d.excluded
            for cid, w in d.weights.items():
                out.weights[cid] = min(w, out.weights.get(cid, w))
            for cid, why in d.flags.items():
                out.flags[cid] = f"{out.flags[cid]}; {why}" if cid in out.flags else why
        return out


@dataclass
class Findings:
    """Output of one plugin at one stage in one round.

    The plugin's name is stored under `module` so that records written before the stage/kind
    contract stay readable.
    """
    module: str
    stage: Stage
    round: int
    scores: dict[str, float] = field(default_factory=dict)             # subject -> risk score
    features: dict[str, dict[str, float]] = field(default_factory=dict)  # subject -> name -> value
    evidence: dict = field(default_factory=dict)
    decision: Decision | None = None
    messages: dict[str, object] = field(default_factory=dict)          # sent to the other side as '<plugin>.<key>'
    # Tensors sent to the other side as '<plugin>.<key>'. The runner moves them to its outbox and leaves
    # their hashes in `sent`; nothing here is written as numbers.
    attachments: dict = field(default_factory=dict)
    sent: dict[str, str] = field(default_factory=dict)
    # Interventions other than `decision`, as the plugin proposes them. The runner turns them into
    # `actions` records (hashes, not tensors) and empties this field before anything is written.
    #   "broadcast": {client id or "*": LoRA state dict}   (transform_broadcast)
    #   "received": LoRA state dict                        (transform_received)
    #   "mask": iterable of sample hashes                  (mask_samples)
    #   "add": list of samples, "rewrite": {hash: sample}  (edit_samples)
    #   "loss": scalar tensor with a graph                 (transform_loss)
    #   "gradients": {parameter name: tensor}              (transform_gradients)
    #   "transformed": {subject: LoRA state dict}          (transform_update)
    #   "replacement": LoRA state dict                     (replace_global)
    proposals: dict = field(default_factory=dict)
    actions: list[dict] = field(default_factory=list)
    cost: dict[str, float] = field(default_factory=dict)   # model passes the plugin spent, as the handle counted them
    error: str | None = None
    elapsed_s: float = 0.0
