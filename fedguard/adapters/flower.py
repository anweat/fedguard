"""Adapter for Flower's Message API (flwr >= 1.20: flwr.serverapp.strategy).

`GuardStrategy` wraps any Strategy the way Flower's own DP wrappers do:

    strategy = GuardStrategy(FedAvg(fraction_train=1.0), runner, recorder)
    strategy.start(grid=grid, initial_arrays=arrays, num_rounds=...)

configure_train opens the round, runs SERVER_DISTRIBUTE on the arrays about to be sent (rewriting the
messages of recipients an applied `transform_broadcast` singled out), attaches the channel, and remembers
what each node was sent (the base its reply is compared against);
aggregate_train turns replies into ClientUpdates, runs SERVER_RECEIVE and SERVER_AGGREGATE, drops excluded replies,
writes the decided weight into each kept reply's weighting metric, delegates aggregation, then records the
result and runs SERVER_POST_AGGREGATE on it.
Replies are sorted by node id first: Flower returns them in arrival order, so plain FedAvg is not
bitwise reproducible across runs (float32 accumulation order); guarded runs are.
Client identity is the Flower node id; self-reported values are the reply's MetricRecord.
"""
from __future__ import annotations

from collections.abc import Iterable

import torch
from flwr.app import ArrayRecord, ConfigRecord, Message, MetricRecord
from flwr.serverapp import Grid
from flwr.serverapp.strategy import Strategy

from fedguard.adapters import hosts
from fedguard.core.runner import GuardRunner
from fedguard.core.types import ClientUpdate, Decision, Stage
from fedguard.views.aggregate import AggregateView, OutgoingView

CHANNEL = "fedguard"               # config keys "fedguard.<plugin>.<key>" downstream; a ConfigRecord of this name upstream
CHANNEL_ARRAYS = "fedguard_arrays"  # an ArrayRecord of this name, in both directions

# Not implemented here: the announce exchange (CLIENT_ANNOUNCE / SERVER_EXCHANGE) needs an extra message
# round before training. Use the single-process adapter for plugins that mount there.


def _state_dict(record: ArrayRecord) -> dict[str, torch.Tensor]:
    return {k: v.detach().to("cpu", copy=True) for k, v in record.to_torch_state_dict().items()}


class GuardStrategy(Strategy):
    """Wraps the Flower strategy an app already uses. The wrapped strategy still configures, aggregates and
    evaluates; this class runs the server-side stages around its calls, hands it the uploads the plugins
    kept (in arrival order, so that with nothing mounted the result is bit for bit the strategy's own),
    and records what passed through. Needs no change to Flower or to the wrapped strategy.
    """
    def __init__(self, strategy: Strategy, runner: GuardRunner, recorder=None, weight_key: str = "num-examples",
                 extensions=frozenset(), probe=None):
        """probe: optional server-side `model_handle` (e.g. fedguard.adapters.hf_probe.HFProbe). Flower gives the
        server no model to run; plugins that need one are refused unless the app supplies it here."""
        hosts.require(runner, hosts.FLOWER, extensions, server_model_handle=probe is not None)
        self.probe = probe
        self._handle = {} if probe is None else {"model_handle": probe}
        for e in sorted(extensions):
            hosts.warn_extension(hosts.FLOWER, e)
        if recorder is not None and extensions:
            recorder.write_run(runner.describe())          # the record names the extension layers in use
        self.strategy, self.runner, self.recorder, self.weight_key = strategy, runner, recorder, weight_key
        self._base: dict[str, torch.Tensor] = {}
        self.last_decision: Decision | None = None
        self._outbox: dict = {}
        self._outbox_tensors: dict = {}
        self._sent: dict[str, dict[str, torch.Tensor]] = {}

    # ----- training -----
    def configure_train(self, server_round: int, arrays: ArrayRecord, config: ConfigRecord,
                        grid: Grid) -> Iterable[Message]:
        for k, v in self._outbox.items():           # last round's server-side messages ride with this broadcast
            config[f"{CHANNEL}.{k}"] = v
        messages = list(self.strategy.configure_train(server_round, arrays, config, grid))
        self.runner.begin_round(server_round)
        out = OutgoingView(_state_dict(arrays), [str(m.metadata.dst_node_id) for m in messages])
        self.runner.run(Stage.SERVER_DISTRIBUTE, list(out.recipients), outgoing=out, **self._handle)
        self._base, self._sent = out.state(), {c: out.for_client(c) for c in out.customized()}
        tensors = {**self._outbox_tensors, **self.runner.outbox_tensors()}
        extra = self.runner.outbox()
        self.runner.clear_outbox()
        changed = bool(self.runner.broadcast())
        for m in messages:
            cid = str(m.metadata.dst_node_id)
            if changed:
                name = next(iter(m.content.array_records))
                m.content[name] = ArrayRecord(self._sent.get(cid, self._base))
            if extra:
                cfg = next(iter(m.content.config_records.values()))
                for k, v in extra.items():
                    cfg[f"{CHANNEL}.{k}"] = v
            if tensors:
                m.content[CHANNEL_ARRAYS] = ArrayRecord(dict(tensors))
        if self.recorder is not None:
            self.recorder.write_base(server_round, self._base)
            for cid, state in self._sent.items():
                self.recorder.write_object(server_round, f"sent_{cid}", state)
        return messages

    def aggregate_train(self, server_round: int,
                        replies: Iterable[Message]) -> tuple[ArrayRecord | None, MetricRecord | None]:
        arrival = list(replies)                      # the wrapped strategy gets its messages in this order, as it would alone
        replies = sorted(arrival, key=lambda m: m.metadata.src_node_id)     # plugins and records see a stable order
        content = [m for m in replies if m.has_content()]
        errors = [m for m in replies if not m.has_content()]
        updates, by_id = [], {}
        for m in content:
            cid = str(m.metadata.src_node_id)
            by_id[cid] = m
            arrays = next(iter(m.content.array_records.values()), None)
            metrics = next(iter(m.content.metric_records.values()), MetricRecord())
            reported = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
            if self.weight_key in reported:
                reported["num_examples"] = reported[self.weight_key]
            channel = m.content.config_records.pop(CHANNEL, None)   # not part of what the inner strategy aggregates
            tensors = m.content.array_records.pop(CHANNEL_ARRAYS, None)
            arrays = next(iter(m.content.array_records.values()), None)
            u = ClientUpdate(cid, server_round, _state_dict(arrays) if arrays is not None else {},
                             self._sent.get(cid, self._base), reported, dict(channel) if channel is not None else {},
                             _state_dict(tensors) if tensors is not None else {})
            updates.append(u)
            if self.recorder is not None and arrays is not None:
                self.recorder.write_update(u)

        participants = list(by_id)
        valid = self.runner.screen(updates)
        rule = type(self.strategy).__name__
        planned = {u.client_id: u.reported[self.weight_key] for u in valid if self.weight_key in u.reported}
        self.runner.run(Stage.SERVER_RECEIVE, participants, uploads=valid, **self._handle)
        for cid, lora in self.runner.transformed().items():      # applied transform_update: aggregate the new arrays
            name = next(iter(by_id[cid].content.array_records))
            by_id[cid].content[name] = ArrayRecord(lora)
        self.runner.run(Stage.SERVER_AGGREGATE, participants, uploads=valid, **self._handle,
                        aggregate=AggregateView(tuple(participants), planned, self._base, rule=rule))
        d = self.runner.decision()
        self.last_decision = d

        kept, weights = [], {}
        for cid, m in by_id.items():
            if cid in d.excluded:
                continue
            if cid in d.weights:
                metrics = next(iter(m.content.metric_records.values()))
                old = metrics[self.weight_key]
                metrics[self.weight_key] = type(old)(d.weights[cid]) if isinstance(old, int) and \
                    float(d.weights[cid]).is_integer() else float(d.weights[cid])
            weights[cid] = next(iter(m.content.metric_records.values())).get(self.weight_key)
            kept.append(m)
        order = [str(m.metadata.src_node_id) for m in arrival if m.has_content()]
        weights = {c: weights[c] for c in order if c in weights}     # in the order the wrapped strategy sums them: replay depends on it
        meta = {"sampled": participants, "aggregated": list(weights), "weights": weights, "errors": len(errors),
                "rule": rule}
        self._outbox, self._outbox_tensors = self.runner.outbox(), self.runner.outbox_tensors()
        if not kept:
            self.runner.end_round(meta)
            return None, None          # Strategy.start keeps the previous global arrays
        dropped = {id(m) for m in content} - {id(m) for m in kept}
        arrays, metrics = self.strategy.aggregate_train(server_round, [m for m in arrival if id(m) not in dropped])
        if arrays is not None:
            result = _state_dict(arrays)
            if self.recorder is not None:
                self.recorder.write_aggregate(server_round, result)
            self.runner.run(Stage.SERVER_POST_AGGREGATE, list(weights), uploads=valid, **self._handle,
                            aggregate=AggregateView(tuple(participants), dict(weights), self._base, result, rule))
            if self.runner.replacement() is not None:           # applied replace_global: this becomes the global model
                arrays = ArrayRecord(self.runner.replacement())
        self._outbox, self._outbox_tensors = self.runner.outbox(), self.runner.outbox_tensors()
        self.runner.end_round(meta)
        return arrays, metrics

    # ----- evaluation and reporting: unchanged -----
    def configure_evaluate(self, server_round: int, arrays: ArrayRecord, config: ConfigRecord,
                           grid: Grid) -> Iterable[Message]:
        return self.strategy.configure_evaluate(server_round, arrays, config, grid)

    def aggregate_evaluate(self, server_round: int, replies: Iterable[Message]) -> MetricRecord | None:
        return self.strategy.aggregate_evaluate(server_round, replies)

    def summary(self) -> None:
        self.strategy.summary()
