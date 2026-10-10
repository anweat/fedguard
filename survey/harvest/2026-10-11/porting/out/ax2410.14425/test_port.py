# test_port.py
"""Mechanism tests for the W2SDefense shell: what it declares, what it refuses, and that it does not act.

The method itself is `not_expressible` on this library (see plugin.py and the port report), so there
is no defense computation to drive and no paper number to check. What can be tested is the port's own
claim: the shell mounts exactly where the runtime does provide a view, a deployment that cannot
supply what the method needs refuses it before the first round, and a driven round leaves the
aggregation result untouched.
"""
import harness
import pytest
import torch

from fedguard.core.plugin import ContractError, check_contract
from fedguard.core.types import RunSpec, Stage
from plugin import W2SDefense

RESOURCES = {"clean_teacher": object(), "clean_train_data": object()}


def test_declaration_is_the_one_the_runtime_can_hold():
    p = W2SDefense()
    assert p.stages == (Stage.SERVER_POST_AGGREGATE,)
    assert p.needs == frozenset({"aggregate", "model_handle"})
    assert p.resources == frozenset({"clean_teacher", "clean_train_data"})
    assert p.acts == frozenset({"replace_global"})


def test_refused_when_the_deployment_cannot_provide_what_the_method_needs():
    p = W2SDefense()
    with pytest.raises(ContractError):                      # no server-side model: the method cannot start
        check_contract(p, "server", RunSpec("no_model", unavailable=frozenset({"model_handle"})), RESOURCES)
    with pytest.raises(ContractError):                      # teacher and clean data are not supplied
        check_contract(p, "server", RunSpec("no_resources"), {})
    check_contract(p, "server", RunSpec("ok"), RESOURCES)   # and mounts where they are supplied


def test_a_driven_round_reports_the_gap_and_changes_nothing():
    base = harness.make_base()
    locals_ = [harness.perturb(base, seed, 0.1) for seed in range(4)]
    guard = harness.server_guard([W2SDefense()], resources=RESOURCES, probe=harness.StubHandle())
    new, kept, decision, findings = harness.server_round(guard, 0, base, locals_)

    assert kept == [0, 1, 2, 3]
    assert decision.excluded == set() and decision.weights == {}
    assert [f.stage for f in findings] == [Stage.SERVER_POST_AGGREGATE]
    f = findings[0]
    assert f.error is None and f.proposals == {} and f.actions == [] and f.decision is None
    assert f.evidence["verdict"] == "not_expressible"
    assert f.evidence["global_lora_entries"] == len(base)
    # the round's outcome is the host's own average: the shell replaced nothing
    expected = {k: sum(s[k] for s in locals_) / len(locals_) for k in base}
    assert all(torch.allclose(new[k], expected[k]) for k in base)
    assert guard.runner.replacement() is None
