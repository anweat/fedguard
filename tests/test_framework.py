import random

import numpy as np
import pytest
import torch

from conftest import GuardPluginSpy as Spy, make_updates
from fedguard.core.plugin import ContractError
from fedguard.core.runner import GuardError, GuardRunner
from fedguard.core.types import Decision, RunSpec, Stage


SPEC = RunSpec(run_id="t", seed=7)


@pytest.mark.parametrize("kwargs", [
    dict(at=Stage.SERVER_RECEIVE, needs=("data",)),                    # raw data never reaches the server
    dict(at=Stage.CLIENT_POST_TRAIN, needs=("local_update",)),         # a client stage on a server runner
    dict(at=Stage.SERVER_RECEIVE, needs=("aggregate",)),               # not produced yet at this stage
    dict(at=Stage.SERVER_RECEIVE, needs=("gradients",)),               # not a data kind
    dict(at=Stage.SERVER_RECEIVE, acts=("select_and_weight",)),        # action at the wrong stage
    dict(at=Stage.SERVER_AGGREGATE, acts=("teleport",)),               # not an action
    dict(at=Stage.SERVER_RECEIVE, resources=("probe_set",)),           # resource not supplied
])
def test_unsatisfiable_declarations_are_refused_before_the_first_round(kwargs):
    with pytest.raises(ContractError):
        GuardRunner([Spy("bad", **kwargs)], SPEC)


def test_sides_are_symmetric():
    client = GuardRunner([Spy("c", Stage.CLIENT_PRE_TRAIN, needs=("data", "received_model"))], SPEC, side="client")
    assert client.side == "client"
    with pytest.raises(ContractError):
        GuardRunner([Spy("c", Stage.CLIENT_PRE_TRAIN, needs=("uploads",))], SPEC, side="client")
    with pytest.raises(ContractError):
        GuardRunner([Spy("s", Stage.SERVER_RECEIVE)], SPEC, side="client")


def test_deployment_without_per_client_uploads_refuses_plugins_that_need_them():
    secure_agg = RunSpec("t", unavailable=frozenset({"uploads"}))
    with pytest.raises(ContractError, match="cannot provide"):
        GuardRunner([Spy("needs_uploads")], secure_agg)
    GuardRunner([Spy("agg_only", Stage.SERVER_POST_AGGREGATE, needs=("aggregate",))], secure_agg)


def test_view_access_is_limited_to_declared_needs():
    reports_only = Spy("meta", Stage.SERVER_AGGREGATE, needs=("reports",), fn=lambda ctx: (ctx.uploads, ctx.findings())[1])
    runner = GuardRunner([reports_only], SPEC)
    ups, _ = make_updates(3)
    runner.begin_round(0)
    [f] = runner.run(Stage.SERVER_AGGREGATE, [u.client_id for u in ups], uploads=ups)
    assert f.error and "PermissionError" in f.error
    closed = GuardRunner([Spy("meta", Stage.SERVER_AGGREGATE, needs=("reports",), fn=lambda ctx: ctx.uploads)], SPEC,
                         fail_policy="closed")
    closed.begin_round(0)
    with pytest.raises(GuardError):
        closed.run(Stage.SERVER_AGGREGATE, [], uploads=ups)


def test_reports_only_plugin_sees_reports_but_not_tensors():
    got = {}

    def fn(ctx):
        got.update(ctx.reports.values("num_examples"))
        return ctx.findings()

    runner = GuardRunner([Spy("meta", Stage.SERVER_AGGREGATE, needs=("reports",), fn=fn)], SPEC)
    ups, _ = make_updates(3)
    runner.begin_round(0)
    [f] = runner.run(Stage.SERVER_AGGREGATE, [], uploads=ups)
    assert f.error is None and got == {"c0": 100.0, "c1": 100.0, "c2": 100.0}


def test_resources_reach_only_the_plugins_that_declare_them():
    seen = {}

    def reads(ctx):
        seen["probe_set"] = ctx.resource("probe_set")
        return ctx.findings()

    def steals(ctx):
        return ctx.findings(evidence={"x": ctx.resource("probe_set")})

    runner = GuardRunner([Spy("owner", resources=("probe_set",), fn=reads), Spy("other", fn=steals)], SPEC,
                         resources={"probe_set": ["q1", "q2"]})
    ups, _ = make_updates(2)
    runner.begin_round(0)
    owner, other = runner.run(Stage.SERVER_RECEIVE, [], uploads=ups)
    assert owner.error is None and seen["probe_set"] == ["q1", "q2"]
    assert other.error and "PermissionError" in other.error


def test_actions_are_off_by_default_and_must_be_declared():
    ups, _ = make_updates(3)
    drop = lambda ctx: ctx.findings(decision=Decision(excluded={"c0"}))  # noqa: E731
    for apply_actions, expected in ((False, set()), (True, {"c0"})):
        runner = GuardRunner([Spy("policy", Stage.SERVER_AGGREGATE, acts=("select_and_weight",), fn=drop)], SPEC,
                             apply_actions=apply_actions)
        runner.begin_round(0)
        [f] = runner.run(Stage.SERVER_AGGREGATE, [], uploads=ups)
        assert f.decision.excluded == {"c0"}                 # the proposal is always recorded
        assert runner.decision().excluded == expected
    undeclared = GuardRunner([Spy("sneaky", Stage.SERVER_AGGREGATE, fn=drop)], SPEC, apply_actions=True)
    undeclared.begin_round(0)
    [f] = undeclared.run(Stage.SERVER_AGGREGATE, [], uploads=ups)
    assert f.error and "acts" in f.error and undeclared.decision().excluded == set()


def test_shape_checks_can_be_relaxed_for_heterogeneous_ranks():
    ups, base = make_updates(2)
    k = next(iter(base))
    ups[0].lora[k] = ups[0].lora[k][:2]                      # a lower-rank A
    strict, relaxed = GuardRunner([], SPEC), GuardRunner([], SPEC, strict_shapes=False)
    for r in (strict, relaxed):
        r.begin_round(0)
    assert [u.client_id for u in strict.screen(ups)] == ["c1"]
    assert [u.client_id for u in relaxed.screen(ups)] == ["c0", "c1"]


def test_invalid_updates_are_screened_and_excluded():
    ups, base = make_updates(4)
    k = next(iter(base))
    ups[0].lora[k] = ups[0].lora[k].clone()
    ups[0].lora[k][0, 0] = float("nan")
    ups[1].lora[k] = ups[1].lora[k][:, :-1]
    ups[2].reported["num_examples"] = -5
    spy = Spy("spy")
    runner = GuardRunner([spy], SPEC)
    runner.begin_round(0)
    valid = runner.screen(ups)
    runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=valid)
    assert [u.client_id for u in valid] == ["c3"]
    assert spy.seen[0].uploads.clients == ["c3"]
    assert runner.decision().excluded == {"c0", "c1", "c2"}


def test_plugin_failure_is_isolated_under_fail_open():
    def boom(ctx):
        raise RuntimeError("x")

    after = Spy("after")
    runner = GuardRunner([Spy("boom", fn=boom), after], SPEC)
    ups, _ = make_updates(3)
    runner.begin_round(0)
    fs = runner.run(Stage.SERVER_RECEIVE, [], uploads=ups)
    assert fs[0].error and fs[1].error is None and len(after.seen) == 1


def test_global_rng_untouched_and_plugin_rng_deterministic():
    draws = []

    def greedy(ctx):
        random.random(); np.random.rand(); torch.rand(1)
        draws.append(float(ctx.rng.random()))
        return ctx.findings()

    ups, _ = make_updates(3)
    random.seed(1); np.random.seed(1); torch.manual_seed(1)
    expected = (random.random(), float(np.random.rand()), float(torch.rand(1)))
    random.seed(1); np.random.seed(1); torch.manual_seed(1)
    for _ in range(2):
        runner = GuardRunner([Spy("g", fn=greedy)], SPEC)
        runner.begin_round(3)
        runner.run(Stage.SERVER_RECEIVE, [], uploads=ups)
        runner.end_round()
    got = (random.random(), float(np.random.rand()), float(torch.rand(1)))
    assert got == expected
    assert draws[0] == draws[1]


def test_decision_merge_is_conservative():
    d = Decision.merge([Decision(weights={"a": 5, "b": 1}, excluded={"c"}),
                        Decision(weights={"a": 2}, flags={"a": "x"})])
    assert d.weights == {"a": 2, "b": 1} and d.excluded == {"c"} and d.flags == {"a": "x"}
