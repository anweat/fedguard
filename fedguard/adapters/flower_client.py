"""Client-side adapter for Flower's Message API: a Mod that captures what a client receives and uploads.

    app = ClientApp(mods=[guard_mod(make_guard)])

    @app.train()
    def train(msg, context):
        guard = active_guard()                       # None when the mod is not installed
        if guard is not None:
            guard.pre_train(data=DataView(samples, text_of=...))
            trainer.add_callback(GuardStepCallback(guard))
        ...

`make_guard(context)` builds the ClientGuard for a node; it is called once per node per process.
The Mod wraps the whole train handler, so by itself it sees only the two messages: the received
arrays before training and the reply after it. Data and training steps are visible only inside the
handler, which reaches the guard through `active_guard()`. If the handler never calls `pre_train`,
CLIENT_PRE_TRAIN runs after training and the round's record says so.

What the Mod does by itself: it records the received model and the reply, and an applied client-side
`transform_update` replaces the uploaded arrays. Everything that changes what is trained on needs the
handler's cooperation: train from `guard.start_state()` (applied `transform_received`), on
`guard.training_samples()` (applied `mask_samples` / `edit_samples`), and with GuardStepCallback on the
trainer (`transform_gradients`, CLIENT_STEP). The handshake before training (CLIENT_ANNOUNCE /
SERVER_EXCHANGE) is not available on Flower. See fedguard.adapters.hosts.

Client identity is the Flower node id, the same id the server-side GuardStrategy uses.
In simulation a node may be served by a different worker process each round; plugin state then starts
empty, while the received-model reference is read back from the node's record.
"""
from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar

import torch
from flwr.app import ArrayRecord, ConfigRecord, Context, Message

from fedguard.adapters import hosts
from fedguard.client import ClientGuard

CHANNEL = "fedguard"               # config keys "fedguard.<plugin>.<key>" downstream; a ConfigRecord of this name upstream
CHANNEL_ARRAYS = "fedguard_arrays"  # an ArrayRecord of this name, in both directions
_ACTIVE: ContextVar[ClientGuard | None] = ContextVar("fedguard_active_guard", default=None)
_GUARDS: dict[str, ClientGuard] = {}


def active_guard() -> ClientGuard | None:
    """The ClientGuard of the message being handled, for use inside a train handler."""
    return _ACTIVE.get()


def _state_dict(record) -> dict[str, torch.Tensor]:
    return {k: v.detach().to("cpu", copy=True) for k, v in record.to_torch_state_dict().items()}


def guard_mod(make_guard: Callable[[Context], ClientGuard], round_key: str = "server-round",
              extensions=frozenset(), prepare: Callable | None = None):
    """extensions, prepare: only with the handshake extension layer (fedguard.adapters.flower_handshake);
    `prepare` is the same function given to announce_query. If the train message is served by a process
    that did not serve the node's announce query (Flower's simulation does that), the announce is computed
    again here from `prepare`, so that the plugin has its own half of the handshake."""
    extensions = frozenset(extensions)

    def mod(msg: Message, context: Context, call_next) -> Message:
        records = msg.content.array_records if msg.has_content() else {}
        arrays = next((v for k, v in records.items() if k != CHANNEL_ARRAYS), None)
        incoming = _state_dict(records[CHANNEL_ARRAYS]) if CHANNEL_ARRAYS in records else {}
        config = next(iter(msg.content.config_records.values()), {}) if msg.has_content() else {}
        if msg.metadata.message_type != "train" or arrays is None or round_key not in config:
            return call_next(msg, context)
        node = str(context.node_id)
        guard = _GUARDS.get(node)
        if guard is None:
            guard = _GUARDS[node] = make_guard(context)
            hosts.require(guard.runner, hosts.FLOWER, extensions)
        messages = {k[len(CHANNEL) + 1:]: v for k, v in config.items() if isinstance(k, str) and k.startswith(CHANNEL + ".")}
        if guard.announced_round == int(config[round_key]):      # the round was opened by the handshake extension
            guard.deliver(messages, incoming)
        else:
            received = _state_dict(arrays)
            guard.begin_round(int(config[round_key]), received, messages=messages, attachments=incoming, defer=True)
            if "handshake" in extensions and guard.wants_exchange and prepare is not None:
                guard.announce(*prepare(msg, context, received))   # another process answered the query: redo our half
                guard.announce_recomputed = True
        token = _ACTIVE.set(guard)
        try:
            reply = call_next(msg, context)
        finally:
            _ACTIVE.reset(token)
        out = next((v for k, v in reply.content.array_records.items() if k != CHANNEL_ARRAYS), None) if reply.has_content() else None
        if out is not None:
            metrics = next(iter(reply.content.metric_records.values()), {})
            guard.before_upload(_state_dict(out), {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})
            if guard.runner is not None and guard.client_id in guard.runner.transformed():
                name = next(iter(reply.content.array_records))
                reply.content[name] = ArrayRecord(guard.upload_state())
            outbox, tensors = guard.outbox(), guard.outbox_tensors()
            if outbox:
                reply.content[CHANNEL] = ConfigRecord(outbox)
            if tensors:
                reply.content[CHANNEL_ARRAYS] = ArrayRecord(tensors)
        guard.end_round({"replied": out is not None})
        return reply
    return mod
