"""Base class for plugins and the checks run on their declarations."""
from __future__ import annotations

from fedguard.core.types import ACTION_STAGES, KIND_SIDE, KINDS, STAGE_KINDS, Findings, RunSpec, Stage, side_of


class ContractError(ValueError):
    """A plugin's declaration cannot be satisfied; raised before the first round."""


class GuardPlugin:
    """An algorithm mounted at one or several stages of one side.

    A plugin declares four things:
      at         the stage it runs at, or a tuple of stages; `run` is called once per stage and can
                 branch on `ctx.stage`. Its private state is shared between its stages, in three scopes:
                 `ctx.state` for the whole run, `ctx.round_state` for one round, `ctx.step_state` for
                 one local training step (the runner empties the last two when their scope ends).
      needs      the data kinds it reads (see fedguard.core.types.KIND_SIDE); anything else is refused
      resources  names of defender-supplied assets it uses (clean reference data, probe sets, ...);
                 the caller passes them to the runner, the plugin reads them with ctx.resource(name)
      acts       the interventions it may propose; empty means report-only

    Subclasses compute from `ctx` views and `fedguard.ops` operators and return `ctx.findings(...)`.
    """
    name: str = ""
    at: Stage | tuple[Stage, ...]
    needs: frozenset[str] = frozenset()
    resources: frozenset[str] = frozenset()
    acts: frozenset[str] = frozenset()
    version: str = "0"

    @property
    def stages(self) -> tuple[Stage, ...]:
        at = getattr(self, "at", None)
        return (at,) if isinstance(at, Stage) else tuple(at or ())

    def setup(self, spec: RunSpec) -> None:
        """Called once before the first round."""

    def run(self, ctx) -> Findings:
        raise NotImplementedError


def check_contract(plugin: GuardPlugin, side: str, spec: RunSpec, resources) -> None:
    """Refuse a plugin whose declaration cannot hold at its stages, on this side, in this deployment."""
    n, stages = plugin.name, plugin.stages
    if not stages or not all(isinstance(s, Stage) for s in stages):
        raise ContractError(f"{n}: `at` must be a Stage or a tuple of Stages")
    needs, acts = frozenset(plugin.needs), frozenset(plugin.acts)
    for s in stages:
        if side_of(s) not in (side, "both"):
            raise ContractError(f"{n}: {s.value} is not a {side}-side stage")
    if needs - KINDS:
        raise ContractError(f"{n}: unknown data kinds {sorted(needs - KINDS)}")
    wrong_side = sorted(k for k in needs if KIND_SIDE[k] not in (side, "both"))
    if wrong_side:
        raise ContractError(f"{n}: {wrong_side} never reach the {side}; use the message channel instead")
    reachable = frozenset().union(*(STAGE_KINDS[s] for s in stages))
    if needs - reachable:
        raise ContractError(f"{n}: {sorted(needs - reachable)} do not exist at {[s.value for s in stages]}")
    if needs & spec.unavailable:
        raise ContractError(f"{n}: this deployment cannot provide {sorted(needs & spec.unavailable)}")
    missing = sorted(frozenset(plugin.resources) - frozenset(resources))
    if missing:
        raise ContractError(f"{n}: resources not supplied: {missing}")
    for a in acts:
        if a not in ACTION_STAGES:
            raise ContractError(f"{n}: unknown action {a!r}")
        if not ACTION_STAGES[a] & set(stages):
            raise ContractError(f"{n}: {a!r} is not possible at {[s.value for s in stages]}")
