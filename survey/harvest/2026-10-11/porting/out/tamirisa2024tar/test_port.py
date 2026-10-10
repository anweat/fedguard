# test_port.py
"""TAR reports `not_expressible`, so there is no defense mechanism to drive.

What can be asserted is that the shell is inert and says so: it mounts at SERVER_DISTRIBUTE (the
nearest in-round surface, the point at which the model about to be handed out is in hand), reads
nothing, changes nothing, and leaves a refusal in the findings of the round. The method itself has no
synthetic case to construct: it is a pre-deployment meta-training loop over full base weights, and the
library has no position outside a round, no plugin-owned optimizer and no action that carries base
weights.
"""
import harness
import pytest
import torch

from plugin import TAR

RESOURCES = {name: object() for name in TAR.resources}


def test_shell_is_inert_and_reports_the_refusal():
    guard = harness.server_guard([TAR()], resources=RESOURCES)
    base = harness.make_base()
    locals_ = [harness.perturb(base, s) for s in (1, 2, 3)]
    new, kept, decision, findings = harness.server_round(guard, 0, base, locals_)

    # nothing was excluded and no weight was proposed: the round is an ordinary FedAvg of the uploads
    assert kept == [0, 1, 2]
    assert decision.excluded == set() and decision.weights == {}
    mean = {k: sum(locals_[c][k] for c in range(3)) / 3 for k in base}
    assert all(torch.allclose(new[k], mean[k]) for k in base)

    # the shell ran once, at its declared stage, and left the reason in the record
    shell = [f for f in findings if f.module == TAR.name]
    assert len(shell) == 1
    assert shell[0].stage is TAR.at and shell[0].error is None
    assert shell[0].evidence["verdict"] == "not_expressible"
    assert TAR.needs == frozenset() and TAR.acts == frozenset()


def test_declared_resources_are_the_offline_objects_of_the_method():
    # nothing a round carries is what TAR consumes: it needs full base weights and defender corpora
    assert TAR.at.value == "server_distribute"
    assert TAR.resources == frozenset({"base_model", "forget_probe", "retain_data", "adversary_configs",
                                       "dpo_reference"})


@pytest.mark.skip(reason="not_expressible: the TAR mechanism is a pre-deployment meta-training loop over base weights")
def test_one_outer_step_would_raise_the_loss_plateau_of_an_attacked_model():
    """The case that would be written if the runtime existed: a toy model, one K-step SFT attack sampled
    from A_train, L_TR at sub-sampled coordinates, the straight-through meta-gradient accumulated into
    g_TR, and the weighted outer update -- asserting the loss plateau of the attacked model rises; and
    a control run with lambda_TR = 0 where it must not."""
