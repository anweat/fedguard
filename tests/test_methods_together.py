"""Enabling methods side by side: what a method computes must not depend on which other methods are
mounted next to it, as long as nobody's actions are applied."""
import pytest
import torch

from conftest import make_base, perturb
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, Stage, side_of
from fedguard.kb import _required_args
from fedguard.methods import METHODS
from fedguard.plugins import BUILTIN

ROUNDS, CLIENTS = 4, 8


def server_side_without_resources():
    """Every shipped server-side plugin that runs on uploads alone: no defender-supplied asset, no model handle."""
    table = {**BUILTIN, **METHODS}
    return sorted(n for n, c in table.items() if not c.resources and "model_handle" not in c.needs and not _required_args(c)
                  and all(side_of(s) == "server" for s in c().stages))


def federate(names):
    """A few rounds of synthetic uploads through the OpenFedLLM adapter, actions off. Returns, per plugin,
    what it reported in every round at every stage."""
    table = {**BUILTIN, **METHODS}
    guard = OpenFedLLMGuard(GuardRunner([table[n]() for n in names], RunSpec("run", seed=3, num_clients=CLIENTS), fail_policy="closed"))
    state, seen = make_base(), {n: [] for n in names}
    for r in range(ROUNDS):
        guard.begin_round(r, state, list(range(CLIENTS)))
        for c in range(CLIENTS):                       # client 0 drifts away from the others, so detectors have something to say
            guard.on_upload(c, perturb(state, 100 * r + c, 0.5 if c == 0 else 0.05), {"num_examples": 10.0 + c})
        guard.before_aggregate(list(range(CLIENTS)), [10 + c for c in range(CLIENTS)])
        state = {k: torch.stack([perturb(state, 100 * r + c, 0.05)[k] for c in range(1, CLIENTS)]).mean(0) for k in state}
        guard.after_aggregate(state)
        for f in guard.runner.findings:
            d = f.decision
            seen[f.module].append((r, f.stage.value, f.error, f.scores, f.features,
                                   None if d is None else (sorted(d.excluded), sorted(d.weights.items()))))
        guard.end_round()
    return seen


def test_every_resource_free_server_method_reports_the_same_alone_and_next_to_all_the_others():
    names = server_side_without_resources()
    assert {"krum", "flame", "foolsgold", "fldetector", "mud_hog", "lomar", "mcd", "crfl", "freqfed"} <= set(names)
    together = federate(names)
    assert all(row[2] is None for rows in together.values() for row in rows)          # nothing failed
    for name in names:
        upstream = [n for n in ("effect_stats", "factor_stats") if n != name and name in ("robust_outlier", "evidence_accumulator")]
        alone = federate([*upstream, name])                                           # two built-ins read an upstream feature
        assert alone[name] == together[name], name


@pytest.mark.parametrize("side", ["server", "client"])
def test_all_shipped_plugins_of_a_side_declare_contracts_that_hold_in_one_runner(side):
    table = {**BUILTIN, **METHODS}
    plugins = [c() for c in table.values() if not _required_args(c) and all(side_of(s) == side for s in c().stages)]
    resources = {k: object() for p in plugins for k in p.resources}
    runner = GuardRunner(plugins, RunSpec("run"), side=side, resources=resources)
    assert len(runner.plugins) == len(plugins) >= 10 and len({p.name for p in plugins}) == len(plugins)
    stages = {s for p in plugins for s in p.stages}
    assert (Stage.CLIENT_LOSS in stages) is (side == "client")
