# test_port.py
"""RepNoise is `not_expressible` in fedguard, so there is no mechanism to drive.

What is checked here is the honesty of the shell: it mounts at the one stage where the output of the
method could be delivered, it takes part in a real round without proposing anything, and it claims no
data kind, asset or action that it cannot use. The mechanism test that would exist if the runtime did
is kept as a skipped placeholder, with the case that it would build. No model is loaded.
"""
import harness
import pytest
import torch

from plugin import RepNoiseImmunization


def test_shell_claims_no_capability_it_cannot_use():
    assert RepNoiseImmunization.name == "repnoise_immunization"
    assert RepNoiseImmunization.at.value == "server_post_aggregate"
    assert RepNoiseImmunization.needs == frozenset()
    assert RepNoiseImmunization.resources == frozenset()
    assert RepNoiseImmunization.acts == frozenset()


def test_shell_mounts_in_a_round_and_reports_instead_of_acting():
    base = harness.make_base()
    locals_ = [harness.perturb(base, seed=s, scale=0.02) for s in (0, 1, 2)]
    guard = harness.server_guard([RepNoiseImmunization()])
    new_global, kept, decision, findings = harness.server_round(guard, 0, base, locals_)

    assert kept == [0, 1, 2]
    assert not decision.excluded and not decision.weights
    mine = [f for f in findings if f.module == RepNoiseImmunization.name]
    assert len(mine) == 1
    assert "not_expressible" in mine[0].evidence
    assert mine[0].decision is None and not mine[0].proposals and not mine[0].actions
    for key in base:                         # the round is a plain average: the shell changes nothing
        assert torch.allclose(new_global[key], sum(a[key] for a in locals_) / len(locals_))


@pytest.mark.skip(reason="not_expressible: no server-side training step, no differentiable activation, no head on an activation")
def test_noise_term_would_move_harmful_representations_toward_the_gaussian():
    """The case that would be written if the runtime existed.

    A stub server handle whose harmful activations are a fixed cloud far from the origin and whose
    backward pass records the scalar that it is given; after one immunization step the MMD between
    the activations and standard Gaussian noise must have fallen, and the returned LoRA state must
    differ from the state that went in. A second case, an activation cloud that is already Gaussian,
    must leave the state unchanged, and a third, where the safe and the harmful answer share every
    token, must show the MASK suppressing both terms.
    """
