"""An extension layer for Flower: a handshake before every training round.

Flower's Strategy has one round trip per training round, so the two stages that open a round with an
exchange (CLIENT_ANNOUNCE, SERVER_EXCHANGE) are not reachable through GuardStrategy alone. This module
adds them on top of Flower's public API, without touching Flower:

    server   HandshakeStrategy(strategy, runner, recorder)        instead of GuardStrategy
    client   app = ClientApp(mods=[guard_mod(make_guard, extensions={"handshake"}, prepare=prepare)])
             app.query(ANNOUNCE)(announce_query(make_guard, prepare))

Before the train messages of a round go out, HandshakeStrategy sends every selected node a query message
with the round's model, runs SERVER_EXCHANGE on the answers and puts its reply into the train messages.

THIS CHANGES THE HOST'S PROTOCOL. It is not how the wrapped strategy runs by itself:
  - one more round trip and one more broadcast of the adapter per round;
  - the nodes must serve a query action the plain app does not have;
  - a node keeps what it computed for the announce until the train message arrives, in the memory of the
    process that served the query. Flower's simulation serves a node from different worker processes;
    the train side then computes the announce a second time (same `prepare`), which costs the announce
    twice and, for a plugin that draws random numbers in it, need not give the same numbers the server saw.
Using it emits a HostExtensionWarning, and the run's record says the extension was on.
"""
from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable

from flwr.app import ArrayRecord, ConfigRecord, Context, Message, RecordDict
from flwr.serverapp import Grid

from fedguard.adapters import hosts
from fedguard.adapters.flower import GuardStrategy
from fedguard.adapters.flower_client import _GUARDS, CHANNEL, CHANNEL_ARRAYS, _state_dict
from fedguard.client import ClientGuard
from fedguard.core.types import Stage
from fedguard.views.uploads import ReportView

ANNOUNCE = "fedguard_announce"           # the query action; message type "query.fedguard_announce"


def _reply(msg: Message, content: RecordDict) -> Message:
    return Message(content, reply_to=msg)


class HandshakeStrategy(GuardStrategy):
    """GuardStrategy plus a query round trip before every training round (CLIENT_ANNOUNCE / SERVER_EXCHANGE).
    An extension layer: a plain Flower strategy has one round trip per round, this one has two and sends the
    adapter twice. Constructing it emits a HostExtensionWarning and marks the record.
    """
    def __init__(self, strategy, runner, recorder=None, weight_key: str = "num-examples", round_key: str = "server-round", probe=None):
        super().__init__(strategy, runner, recorder, weight_key, extensions={"handshake"}, probe=probe)
        self.round_key = round_key

    def configure_train(self, server_round: int, arrays: ArrayRecord, config: ConfigRecord, grid: Grid) -> Iterable[Message]:
        messages = list(super().configure_train(server_round, arrays, config, grid))
        if not messages:
            return messages
        queries = []
        for m in messages:
            name = next(k for k in m.content.array_records if k != CHANNEL_ARRAYS)
            content = RecordDict({"arrays": m.content[name], "config": ConfigRecord({self.round_key: server_round})})
            queries.append(grid.create_message(content=content, message_type=f"query.{ANNOUNCE}",
                                               dst_node_id=m.metadata.dst_node_id, group_id=str(server_round)))
        said, tensors = {}, {}
        for r in grid.send_and_receive(queries):
            if not r.has_content():
                continue
            cid = str(r.metadata.src_node_id)
            channel = r.content.config_records.get(CHANNEL)
            said[cid] = dict(channel) if channel is not None else {}
            tensors[cid] = _state_dict(r.content.array_records[CHANNEL_ARRAYS]) if CHANNEL_ARRAYS in r.content.array_records else {}
        self.runner.run(Stage.SERVER_EXCHANGE, sorted(said), reports=ReportView({}, said, tensors), **self._handle)
        answer, answer_tensors = self.runner.outbox(), self.runner.outbox_tensors()
        self.runner.clear_outbox()
        for m in messages:
            if answer:
                cfg = next(iter(m.content.config_records.values()))
                for k, v in answer.items():
                    cfg[f"{CHANNEL}.{k}"] = v
            if answer_tensors:
                have = _state_dict(m.content.array_records[CHANNEL_ARRAYS]) if CHANNEL_ARRAYS in m.content.array_records else {}
                m.content[CHANNEL_ARRAYS] = ArrayRecord({**have, **answer_tensors})
        return messages


def announce_query(make_guard: Callable[[Context], ClientGuard], prepare: Callable, round_key: str = "server-round"):
    """The client's handler for the announce query.

    prepare(msg, context, received) -> (DataView, model_handle): the node's data for the round and, if a
    plugin needs it, a model handle with `received` (the round's LoRA) loaded. The same data must be used
    by the train handler afterwards.
    """
    warned = []

    def query(msg: Message, context: Context) -> Message:
        if not warned:
            warned.append(hosts.warn_extension(hosts.FLOWER, "handshake"))
        node = str(context.node_id)
        guard = _GUARDS.get(node)
        if guard is None:
            guard = _GUARDS[node] = make_guard(context)
            hosts.require(guard.runner, hosts.FLOWER, extensions={"handshake"})
        received = _state_dict(msg.content["arrays"])
        guard.begin_round(int(msg.content["config"][round_key]), received, defer=True)
        data, handle = prepare(msg, context, received)
        said, tensors = guard.announce(data=data, model_handle=handle)
        content = RecordDict({CHANNEL: ConfigRecord(said)})
        if tensors:
            content[CHANNEL_ARRAYS] = ArrayRecord(tensors)
        return _reply(msg, content)
    return query


__all__ = ["ANNOUNCE", "HandshakeStrategy", "announce_query"]
_ = warnings      # the warning itself is raised through fedguard.adapters.hosts
