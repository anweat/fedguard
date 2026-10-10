"""Plugin runner: contract checks, need-scoped contexts, failure policy, RNG isolation."""
from __future__ import annotations

import hashlib
import json
import random
import time
import traceback
import zlib
from contextlib import contextmanager

import numpy as np
import torch

from types import MappingProxyType

from fedguard.core.actions import HANDLERS, PROPOSAL_ACTION
from fedguard.core.context import StageContext
from fedguard.core.plugin import GuardPlugin, check_contract
from fedguard.core.types import ClientUpdate, Decision, Findings, RunSpec, Stage, check_messages
from fedguard.core.validation import InvalidUpdate, validate_update
from fedguard.recorder.store import state_hash
from fedguard.views.uploads import HistoryView, ReportView, UploadView


def resource_hash(obj) -> str:
    """Identify a defender-supplied asset in the record without storing it."""
    if isinstance(obj, (bytes, bytearray)):
        return "sha256:" + hashlib.sha256(bytes(obj)).hexdigest()
    try:
        return "sha256:" + hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    except (TypeError, ValueError):
        return f"unhashed:{type(obj).__module__}.{type(obj).__qualname__}"


class GuardError(RuntimeError):
    """Raised under fail_policy='closed' when a plugin fails."""


@contextmanager
def preserved_rng():
    """Restore Python, NumPy and torch global RNG state after a module runs.

    Upstream frameworks draw client sampling and data order from global RNGs; a plugin that
    consumes them would make guarded and unguarded runs diverge. Plugins use ctx.rng instead.
    """
    py, np_state, cpu = random.getstate(), np.random.get_state(), torch.get_rng_state()
    cuda = torch.cuda.get_rng_state_all() if torch.cuda.is_available() and torch.cuda.is_initialized() else None
    mps = torch.mps.get_rng_state() if hasattr(torch, "mps") and torch.backends.mps.is_available() else None
    try:
        yield
    finally:
        random.setstate(py)
        np.random.set_state(np_state)
        torch.set_rng_state(cpu)
        if cuda is not None:
            torch.cuda.set_rng_state_all(cuda)
        if mps is not None:
            torch.mps.set_rng_state(mps)


class GuardRunner:
    """Runs the plugins of one side (one server, or one client).

    resources: defender-supplied assets by name, handed only to plugins that declare them.
    apply_actions: when False (the default), what plugins propose is recorded but nothing is changed and
        `decision()` contains framework rejections only. True applies every plugin's proposals; a set
        of plugin names applies only theirs.
    attachment_limit_bytes: cap on the tensors one plugin may send over the channel per round.
    strict_shapes: require every upload to match the broadcast base key by key and shape by shape.
        Turn off for schemes with per-client ranks or a single trained factor.
    """

    def __init__(self, plugins: list[GuardPlugin], spec: RunSpec, recorder=None, fail_policy: str = "open", *,
                 side: str = "server", resources: dict | None = None,
                 apply_actions: bool | set[str] = False, strict_shapes: bool = True,
                 attachment_limit_bytes: int = 64 * 2**20):
        if fail_policy not in ("open", "closed"):
            raise ValueError("fail_policy must be 'open' or 'closed'")
        if side not in ("server", "client"):
            raise ValueError("side must be 'server' or 'client'")
        names = [p.name for p in plugins]
        if not all(names) or len(names) != len(set(names)):
            raise ValueError("plugins need unique nonempty names")
        self.resources = dict(resources or {})
        for p in plugins:
            check_contract(p, side, spec, self.resources)
        self.plugins, self.spec, self.recorder, self.fail_policy = list(plugins), spec, recorder, fail_policy
        if not isinstance(apply_actions, bool):
            apply_actions = frozenset(apply_actions)
            if apply_actions - set(names):
                raise ValueError(f"apply_actions names unknown plugins: {sorted(apply_actions - set(names))}")
        self.side, self.apply_actions, self.strict_shapes = side, apply_actions, strict_shapes
        self.host: str | None = None          # set by the adapter that mounts this runner on a host framework
        self.host_extensions: list[str] = []  # extension layers in use that change the host's own protocol
        self.policy: dict | None = None       # name and digest of the control policy this runner was built from, if any
        self.attachment_limit_bytes = attachment_limit_bytes
        self._state: dict[str, dict] = {p.name: {} for p in plugins}         # ctx.state: kept for the whole run
        self._round_state: dict[str, dict] = {p.name: {} for p in plugins}   # ctx.round_state
        self._step_state: dict[str, dict] = {p.name: {} for p in plugins}    # ctx.step_state
        self._step: int | None = None
        self._history: dict[str, list[tuple[int, dict[str, float]]]] = {}
        self._round: int | None = None
        self._findings: list[Findings] = []
        self._rejected: dict[str, str] = {}
        self._masked: set[str] = set()
        self._transformed: dict[str, dict] = {}
        self._replacement: dict | None = None
        self._added: list[tuple[str, object]] = []
        self._rewritten: dict[str, object] = {}
        self._broadcast: dict[str, dict] = {}
        self._attachments: dict[str, torch.Tensor] = {}
        self._received: dict | None = None
        for p in plugins:
            p.setup(spec)
        if recorder is not None:
            recorder.write_run(self.describe())

    def describe(self) -> dict:
        """What ran and under which conditions; written to run.json when the run is recorded."""
        return {"spec": self.spec, "side": self.side, "host": self.host, "host_extensions": self.host_extensions, "policy": self.policy,
                "apply_actions": self.apply_actions if isinstance(self.apply_actions, bool) else sorted(self.apply_actions),
                "strict_shapes": self.strict_shapes, "fail_policy": self.fail_policy,
                "plugins": [{"name": p.name, "version": p.version, "at": [s.value for s in p.stages], "needs": sorted(p.needs),
                             "resources": sorted(p.resources), "acts": sorted(p.acts)} for p in self.plugins],
                "resources": {k: resource_hash(v) for k, v in self.resources.items()}}

    # ----- round lifecycle -----
    def begin_round(self, round_idx: int) -> None:
        self._round, self._findings, self._rejected = round_idx, [], {}
        self._masked, self._transformed, self._replacement = set(), {}, None
        self._added, self._rewritten, self._broadcast, self._attachments = [], {}, {}, {}
        self._received = None
        self._step = None
        for scoped in (self._round_state, self._step_state):
            for state in scoped.values():
                state.clear()

    def begin_step(self, step: int) -> None:
        """A local training step begins (client side; the adapter says so at each of its points). Stages
        of the same step share `ctx.step_state`; it is emptied when the step number changes."""
        if step != self._step:
            self._step = step
            for state in self._step_state.values():
                state.clear()

    def applies(self, plugin_name: str) -> bool:
        return self.apply_actions if isinstance(self.apply_actions, bool) else plugin_name in self.apply_actions

    def screen(self, updates: list[ClientUpdate]) -> list[ClientUpdate]:
        """Framework validation before any plugin sees an upload; failures are excluded and recorded."""
        valid = []
        for u in updates:
            try:
                validate_update(u, strict_shapes=self.strict_shapes)
                valid.append(u)
            except InvalidUpdate as exc:
                self._rejected[u.client_id] = f"invalid: {exc}"
        return valid

    def run(self, stage: Stage, participants: list[str], **views) -> list[Findings]:
        """Run this stage's plugins in mount order. `views` maps data kinds to what the adapter provides."""
        if self._round is None:
            raise RuntimeError("call begin_round() first")
        if isinstance(views.get("uploads"), list):
            views["uploads"] = UploadView(views["uploads"], self.spec.lora_scale)
        if "uploads" in views and "reports" not in views:
            views["reports"] = views["uploads"].reports
        if isinstance(views.get("reports"), dict):
            views["reports"] = ReportView(views["reports"])
        views.setdefault("history", HistoryView(self._history, self.recorder))

        out = []
        handle = views.get("model_handle")
        for p in (p for p in self.plugins if stage in p.stages):
            seed = np.random.SeedSequence([self.spec.seed, zlib.crc32(p.name.encode()), self._round])
            ctx = StageContext(plugin=p.name, stage=stage, round=self._round, participants=list(participants),
                               spec=self.spec, needs=frozenset(p.needs), rng=np.random.default_rng(seed),
                               state=self._state[p.name], round_state=self._round_state[p.name],
                               step_state=self._step_state[p.name], upstream=tuple(self._findings), _views=views,
                               _resources=MappingProxyType({k: self.resources[k] for k in p.resources}))
            t0 = time.perf_counter()
            cost0 = dict(getattr(handle, "cost", None) or {})
            with preserved_rng():
                try:
                    if "uploads" in p.needs and "uploads" in views and not views["uploads"].clients:
                        # a round in which no upload arrived (every reply failed or was rejected) is a fact of
                        # federated training, not an error of the plugin: there is nothing for it to judge
                        f = ctx.findings(evidence={"skipped": "no uploads this round"})
                    else:
                        f = p.run(ctx)
                    if not isinstance(f, Findings) or f.module != p.name:
                        raise TypeError(f"{p.name} must return ctx.findings(...)")
                    if f.decision is not None and "select_and_weight" not in p.acts:
                        raise TypeError(f"{p.name} returned a decision without declaring 'select_and_weight' in `acts`")
                    check_messages(f.messages)
                    self._handle_attachments(p, f)
                    self._handle_proposals(p, f, views)
                except Exception as exc:
                    if self.fail_policy == "closed":
                        raise GuardError(f"{p.name} failed") from exc
                    f = ctx.findings(error="".join(traceback.format_exception_only(type(exc), exc)).strip())
            f.elapsed_s = time.perf_counter() - t0
            if cost0 or getattr(handle, "cost", None):
                f.cost = {k: v - cost0.get(k, 0) for k, v in handle.cost.items() if v != cost0.get(k, 0)}
            out.append(f)
            self._findings.append(f)
        return out

    def _handle_attachments(self, p: GuardPlugin, f: Findings) -> None:
        att, f.attachments = f.attachments, {}
        if not att:
            return
        if not all(isinstance(k, str) and k and isinstance(v, torch.Tensor) for k, v in att.items()):
            raise TypeError(f"{p.name}: attachments must map names to tensors")
        size = sum(v.numel() * v.element_size() for v in att.values())
        if size > self.attachment_limit_bytes:
            raise ValueError(f"{p.name}: attachments of {size} bytes exceed the limit of {self.attachment_limit_bytes}")
        for k, v in att.items():
            if not torch.isfinite(v).all():
                raise ValueError(f"{p.name}: attachment {k!r} has non-finite values")
            v = v.detach().to("cpu").contiguous()
            self._attachments[f"{p.name}.{k}"] = v
            f.sent[k] = state_hash({k: v})

    def _handle_proposals(self, p: GuardPlugin, f: Findings, views: dict) -> None:
        """Record every proposed intervention (as hashes, not tensors); apply it only when this plugin's
        actions are on. What each action does is in fedguard.core.actions.

        An applied change is what later plugins of the round see, and what the adapter hands on
        (masked(), sample_edits(), transformed(), replacement(), broadcast()). A changed loss or gradient
        lives in its view, which the adapter reads back.
        """
        props, f.proposals = f.proposals, {}
        for key in props:
            if key not in PROPOSAL_ACTION:
                raise TypeError(f"{p.name}: unknown proposal {key!r}")
            if PROPOSAL_ACTION[key] not in p.acts:
                raise TypeError(f"{p.name} proposed {key!r} without declaring {PROPOSAL_ACTION[key]!r} in `acts`")
        apply = self.applies(p.name)
        for handler in HANDLERS:
            if any(k in props for k in handler.keys):
                handler.handle(self, p, f, views, props, apply)

    def sample_edits(self) -> tuple[list[tuple[str, object]], dict[str, object]]:
        """Applied `edit_samples` actions of this round: (plugin, sample) pairs to add, and replacements by sample hash."""
        return list(self._added), dict(self._rewritten)

    def received(self) -> dict | None:
        """The LoRA an applied `transform_received` put in place of what the client was sent, if any."""
        return self._received

    def broadcast(self) -> dict[str, dict]:
        """Applied `transform_broadcast` actions: recipient (or "*") -> the LoRA to send instead."""
        return dict(self._broadcast)

    def outbox_tensors(self) -> dict[str, torch.Tensor]:
        """Tensors this round's plugins addressed to the other side, keyed '<plugin>.<key>'."""
        return dict(self._attachments)

    def masked(self) -> set[str]:
        """Hashes of the samples this round's applied `mask_samples` actions removed from training."""
        return set(self._masked)

    def transformed(self) -> dict[str, dict]:
        """Subjects whose LoRA an applied `transform_update` replaced this round, with the new state."""
        return dict(self._transformed)

    def replacement(self) -> dict | None:
        """The global LoRA an applied `replace_global` put in place of this round's aggregation result."""
        return self._replacement

    def outbox(self) -> dict[str, object]:
        """Messages this round's plugins addressed to the other side, keyed '<plugin>.<key>'.

        The adapter carries them: a server's outbox goes out with the next broadcast, a client's with
        its upload. The receiving side sees them in `reports`, marked as unverified like everything
        else that crosses the boundary.
        """
        return {f"{f.module}.{k}": v for f in self._findings if f.error is None for k, v in f.messages.items()}

    def clear_outbox(self) -> None:
        """Forget messages and tensors already handed to the adapter (used between the announce
        exchange and the rest of a round, so they are not sent twice)."""
        for f in self._findings:
            f.messages = {}
        self._attachments = {}

    def decision(self) -> Decision:
        """This round's disposition: framework rejections, plus the plugins' proposals when actions are applied."""
        d = Decision.merge([f.decision for f in self._findings if f.decision is not None and self.applies(f.module)])
        for cid, why in self._rejected.items():
            d.excluded.add(cid)
            d.flags[cid] = why
        return d

    def end_round(self, meta: dict | None = None) -> None:
        """Append SERVER_RECEIVE features to per-client history and hand the round to the recorder."""
        merged: dict[str, dict[str, float]] = {}
        for f in self._findings:
            if f.stage == Stage.SERVER_RECEIVE:
                for cid, feats in f.features.items():
                    merged.setdefault(cid, {}).update({f"{f.module}.{k}": v for k, v in feats.items()})
        for cid, feats in merged.items():
            self._history.setdefault(cid, []).append((self._round, feats))
        if self.recorder is not None:
            self.recorder.write_round(self._round, findings=self._findings, decision=self.decision(),
                                      rejected=self._rejected, meta=meta or {})
        self._round = None

    @property
    def findings(self) -> list[Findings]:
        return list(self._findings)
