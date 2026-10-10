"""Adapter for OpenFedLLM / FedLLM-Attack style single-process main loops.

Call sequence inside the loop (see experiments/fedllm_attack/run_guarded.py):

    guard.begin_round(round, global_dict, clients_this_round)   # after client sampling; SERVER_DISTRIBUTE
    set_peft_model_state_dict(model, guard.model_for(client))  # what this client is sent
    reply = guard.exchange({client: client_guard.announce(), ...})   # only when client plugins announce; SERVER_EXCHANGE
    guard.on_upload(client, local_dict, reported)      # after each client's local training
    clients, weights = guard.before_aggregate(clients_this_round, sample_num_list)   # SERVER_RECEIVE, SERVER_AGGREGATE
    for c, lora in guard.transformed.items(): local_dict_list[c] = lora   # only with transform_update plugins
    global_dict, _ = global_aggregate(..., weights, clients, ...)   # skip if clients == []
    global_dict = guard.after_aggregate(global_dict)   # SERVER_POST_AGGREGATE; records the result
    guard.end_round(meta)
    ...
    guard.finish(global_dict)                          # after the last round

Aggregation weights come from what clients *report* (reported["num_examples"]), not from the
simulator's true dataset sizes, so that attacks on self-reported metadata can be simulated.
With honest reporting and no plugins, aggregation is bitwise identical to upstream.
"""
from __future__ import annotations

from typing import Callable

import torch

from fedguard.adapters import hosts
from fedguard.core.runner import GuardRunner
from fedguard.core.types import ClientUpdate, Decision, Stage
from fedguard.views.aggregate import AggregateView, OutgoingView
from fedguard.views.uploads import ReportView


def _snapshot(state: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    # Upstream aggregates in place into global_dict, so the broadcast base must be copied.
    return {k: v.detach().to("cpu", copy=True) for k, v in state.items()}


def _as_weight(x: float):
    # Keep integral weights as int so `tensor * w / total` matches upstream bit for bit.
    return int(x) if float(x).is_integer() else float(x)


class OpenFedLLMGuard:
    """The server side of the library inside an OpenFedLLM-style round loop. The script calls it at the
    points listed in the module docstring; it runs the server-side stages there and gives back what the
    script should send, aggregate and keep. Clients use fedguard.client.ClientGuard next to it.
    """
    def __init__(self, runner: GuardRunner, recorder=None,
                 client_name: Callable[[int], str] = lambda i: f"client{i}", probe=None, rule: str = "fedavg"):
        """probe: optional server-side `model_handle` (e.g. fedguard.adapters.hf_probe.HFProbe).
        rule: name of the upstream aggregation rule, recorded with each round."""
        hosts.require(runner, hosts.OPENFEDLLM)
        self.runner, self.recorder, self.name, self.probe, self.rule = runner, recorder, client_name, probe, rule
        self.outbox: dict = {}                       # messages for clients: begin_round(messages=guard.outbox)
        self.outbox_tensors: dict = {}               # tensors for clients: begin_round(attachments=guard.outbox_tensors)
        self._sent: dict[str, dict[str, torch.Tensor]] = {}
        self.transformed: dict[int, dict[str, torch.Tensor]] = {}
        self._views: dict = {}
        self._sampled: tuple[str, ...] = ()
        self._weights: dict[str, float] = {}
        self._round: int | None = None
        self._base: dict[str, torch.Tensor] = {}
        self._uploads: dict[int, ClientUpdate] = {}
        self.last_decision: Decision | None = None

    def begin_round(self, round_idx: int, global_dict: dict[str, torch.Tensor], recipients: list[int] | None = None) -> None:
        """Open the round and run SERVER_DISTRIBUTE on the global LoRA about to be sent to `recipients`."""
        self._round, self._uploads = round_idx, {}
        self.runner.begin_round(round_idx)
        out = OutgoingView(_snapshot(global_dict), [self.name(c) for c in recipients or []])
        views = {"outgoing": out} if self.probe is None else {"outgoing": out, "model_handle": self.probe}
        self.runner.run(Stage.SERVER_DISTRIBUTE, list(out.recipients), **views)
        self._base, self._sent = out.state(), {c: out.for_client(c) for c in out.customized()}
        self.outbox = {**self.outbox, **self.runner.outbox()}
        self.outbox_tensors = {**self.outbox_tensors, **self.runner.outbox_tensors()}
        self.runner.clear_outbox()
        if self.recorder is not None:
            self.recorder.write_base(round_idx, self._base)
            for cid, state in self._sent.items():
                self.recorder.write_object(round_idx, f"sent_{cid}", state)

    def model_for(self, client_idx: int) -> dict[str, torch.Tensor]:
        """The LoRA this client is sent: the round's global one, unless an applied `transform_broadcast` gave it its own."""
        return dict(self._sent.get(self.name(client_idx), self._base))

    def exchange(self, announced: dict[int, tuple[dict, dict]]) -> tuple[dict, dict]:
        """Run SERVER_EXCHANGE on what clients announced (client index -> (messages, tensors)) and return
        the (messages, tensors) to deliver to every client before it trains."""
        names = {self.name(c): v for c, v in announced.items()}
        reports = ReportView({}, {c: m for c, (m, _) in names.items()}, {c: t for c, (_, t) in names.items()})
        views = {"reports": reports} if self.probe is None else {"reports": reports, "model_handle": self.probe}
        self.runner.run(Stage.SERVER_EXCHANGE, list(names), **views)
        reply = self.runner.outbox(), self.runner.outbox_tensors()
        self.runner.clear_outbox()
        return reply

    def on_upload(self, client_idx: int, local_dict: dict[str, torch.Tensor], reported: dict[str, float],
                  messages: dict | None = None, attachments: dict | None = None) -> None:
        """messages, attachments: the client's channel outbox (ClientGuard.outbox(), .outbox_tensors())."""
        cid = self.name(client_idx)
        u = ClientUpdate(cid, self._round, _snapshot(local_dict), self._sent.get(cid, self._base), dict(reported),
                         dict(messages or {}), dict(attachments or {}))
        self._uploads[client_idx] = u
        if self.recorder is not None:
            self.recorder.write_update(u)

    def before_aggregate(self, clients_this_round: list[int], sample_num_list: list) -> tuple[list[int], list]:
        """Run SERVER_RECEIVE and SERVER_AGGREGATE, then return (clients to aggregate, weights list)."""
        clients = [c for c in clients_this_round if c in self._uploads]
        participants = [self.name(c) for c in clients]
        valid = self.runner.screen([self._uploads[c] for c in clients])
        views = {"uploads": valid} if self.probe is None else {"uploads": valid, "model_handle": self.probe}
        planned = {self.name(c): self._uploads[c].reported.get("num_examples", sample_num_list[c]) for c in clients}
        self._sampled = tuple(self.name(c) for c in clients_this_round)
        self.runner.run(Stage.SERVER_RECEIVE, participants, **views)
        changed = self.runner.transformed()
        self.transformed = {c: changed[self.name(c)] for c in clients if self.name(c) in changed}
        self.runner.run(Stage.SERVER_AGGREGATE, participants, **views,
                        aggregate=AggregateView(self._sampled, planned, self._base, rule=self.rule))
        self._views = views
        d = self.runner.decision()
        self.last_decision = d
        weights = list(sample_num_list)
        kept = []
        for c in clients:
            cid = self.name(c)
            if cid in d.excluded:
                continue
            claimed = self._uploads[c].reported.get("num_examples", sample_num_list[c])
            weights[c] = _as_weight(d.weights.get(cid, claimed))
            kept.append(c)
        self._weights = {self.name(c): weights[c] for c in kept}
        return kept, weights

    def after_aggregate(self, global_dict: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        """Record this round's aggregation result and run SERVER_POST_AGGREGATE on it.

        Returns the global LoRA to continue with: `global_dict` itself, unless an applied
        `replace_global` action put another state in its place."""
        result = _snapshot(global_dict)
        if self.recorder is not None:
            self.recorder.write_aggregate(self._round, result)
        self.runner.run(Stage.SERVER_POST_AGGREGATE, list(self._weights), **self._views,
                        aggregate=AggregateView(self._sampled, dict(self._weights), self._base, result, self.rule))
        new = self.runner.replacement()
        if new is None:
            return global_dict
        return {k: new[k].to(v.device, v.dtype) for k, v in global_dict.items()}

    def end_round(self, meta: dict | None = None) -> None:
        self.outbox, self.outbox_tensors = self.runner.outbox(), self.runner.outbox_tensors()   # for the next round
        self.runner.end_round(meta)
        self._round = None

    def finish(self, global_dict: dict[str, torch.Tensor], final_round: int) -> None:
        """Record the post-training global LoRA as the base of round `final_round`."""
        if self.recorder is not None:
            self.recorder.write_base(final_round, _snapshot(global_dict))
