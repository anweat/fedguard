"""The interventions a plugin may propose, one entry each: which keys of `Findings.proposals` carry it,
how a proposal is checked and recorded, and what applying it changes.

Where an action may be proposed is declared in fedguard.core.types.ACTION_STAGES (the plugin contract
needs it before any of this runs). The runner goes through HANDLERS in order for every plugin's
findings; a new action is added here and there, nowhere else.

A handler gets (runner, plugin, findings, views, proposals, apply). It appends one record per proposed
change to `findings.actions` (hashes, norms or counts, never tensors or sample text) and, when `apply`
is true, makes the change: on the stage's view, so that later plugins of the round see it, and on the
runner, so that the adapter can hand it to the host. `select_and_weight` has no handler: it travels as
`Findings.decision` and is merged by the runner (see Decision.merge).
"""
from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

import torch

from fedguard.core.types import ACTION_STAGES, ClientUpdate
from fedguard.core.validation import validate_update
from fedguard.recorder.store import state_hash


@dataclass(frozen=True)
class ActionHandler:
    """How one action is carried in `Findings.proposals` and what the runner does with it."""
    action: str
    keys: tuple[str, ...]            # proposal keys that belong to this action
    handle: Callable                 # (runner, plugin, findings, views, proposals, apply) -> None


def _broadcast(runner, p, f, views, props, apply):
    for target, new in (props.get("broadcast") or {}).items():
        out = views["outgoing"]
        before = out.for_client(target) if target != "*" else out.state()
        validate_update(ClientUpdate(str(target), runner._round, new, before), strict_shapes=runner.strict_shapes)
        f.actions.append({"action": "transform_broadcast", "subject": target, "before": state_hash(before),
                          "after": state_hash(new), "applied": apply})
        if apply:
            out.replace(target, new)
            runner._broadcast[target] = new


def _received(runner, p, f, views, props, apply):
    if props.get("received") is None:
        return
    target, new = views["received_model"], props["received"]
    validate_update(ClientUpdate("received", runner._round, new, target.state()), strict_shapes=runner.strict_shapes)
    f.actions.append({"action": "transform_received", "before": state_hash(target.state()), "after": state_hash(new), "applied": apply})
    if apply:
        target.replace(new)
        runner._received = new


def _mask(runner, p, f, views, props, apply):
    if "mask" not in props:
        return
    hashes = {str(h) for h in props["mask"]}
    f.actions.append({"action": "mask_samples", "subjects": sorted(hashes), "applied": apply})
    if apply:
        runner._masked |= hashes


def _edit(runner, p, f, views, props, apply):
    if not (props.get("add") or props.get("rewrite")):
        return
    added, rewritten = list(props.get("add") or []), dict(props.get("rewrite") or {})
    f.actions.append({"action": "edit_samples", "added": len(added), "rewritten": sorted(rewritten), "applied": apply})
    if apply:
        runner._added += [(p.name, s) for s in added]
        runner._rewritten.update(rewritten)


def _loss(runner, p, f, views, props, apply):
    if props.get("loss") is None:
        return
    target, new = views["loss"], props["loss"]
    target.check(new)
    f.actions.append({"action": "transform_loss", "before": float(target.loss.detach()), "after": float(new.detach()), "applied": apply})
    if apply:
        target.replace(new)


def _gradients(runner, p, f, views, props, apply):
    if not props.get("gradients"):
        return
    grads, new = views["gradients"], props["gradients"]
    before = grads.norm()
    grads.check(new)
    after = float(torch.sqrt(sum((new[n].double() ** 2).sum() if n in new else (grads.get(n).double() ** 2).sum()
                                 for n in grads.names())))
    f.actions.append({"action": "transform_gradients", "parameters": len(new), "norm_before": before, "norm_after": after,
                      "applied": apply})
    if apply:
        grads.apply(new)


def _update(runner, p, f, views, props, apply):
    for subject, new in (props.get("transformed") or {}).items():
        server = runner.side == "server"
        target = views["uploads"] if server else views["local_update"]
        before = target.state(subject) if server else target.state()
        validate_update(ClientUpdate(str(subject), runner._round, new, before), strict_shapes=runner.strict_shapes)
        f.actions.append({"action": "transform_update", "subject": subject, "before": state_hash(before), "after": state_hash(new),
                          "applied": apply})
        if apply:
            target.replace(subject, new) if server else target.replace(new)
            runner._transformed[subject] = new


def _replace_global(runner, p, f, views, props, apply):
    if props.get("replacement") is None:
        return
    agg, new = views["aggregate"], props["replacement"]
    validate_update(ClientUpdate("global", runner._round, new, agg.result), strict_shapes=runner.strict_shapes)
    f.actions.append({"action": "replace_global", "before": state_hash(agg.result), "after": state_hash(new), "applied": apply})
    if apply:
        views["aggregate"] = dataclasses.replace(agg, result=new)
        runner._replacement = new


HANDLERS: tuple[ActionHandler, ...] = (            # in the order they are applied within one plugin's findings
    ActionHandler("transform_broadcast", ("broadcast",), _broadcast),
    ActionHandler("transform_received", ("received",), _received),
    ActionHandler("mask_samples", ("mask",), _mask),
    ActionHandler("edit_samples", ("add", "rewrite"), _edit),
    ActionHandler("transform_loss", ("loss",), _loss),
    ActionHandler("transform_gradients", ("gradients",), _gradients),
    ActionHandler("transform_update", ("transformed",), _update),
    ActionHandler("replace_global", ("replacement",), _replace_global),
)
PROPOSAL_ACTION: dict[str, str] = {key: h.action for h in HANDLERS for key in h.keys}
assert {h.action for h in HANDLERS} | {"select_and_weight"} == set(ACTION_STAGES), "every action needs a handler, and the reverse"
