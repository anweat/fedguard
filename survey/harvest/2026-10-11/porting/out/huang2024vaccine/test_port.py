# test_port.py
"""The port reports `not_expressible`, so there is no mechanism to verify.

Convention for this batch (the same one the other not_expressible ports use): the test file still
imports, and the port's own claim is asserted, so that a later reader cannot mistake the shell for a
finished method. The verification that matters here is negative and lives outside pytest: `ModelHandle`
(fedguard/views/model.py) offers no hook or forward-patch method and returns detached activations;
`LossView.gradients_of` (fedguard/views/client.py) reaches trainable parameters only; the trainer
extension's own docstring puts the forward pass and intermediate activations out of reach. Writing a
synthetic "Vaccine works" case would require a model runtime the library does not have, and the task
requires tests to load no model.
"""
import harness  # noqa: F401  (kept so the file matches the batch's shape)
import pytest

from plugin import VaccineAlignment


def test_verdict_is_not_expressible():
    # The shell must not pretend to have a mechanism: no data kind, no action, no model pass.
    assert VaccineAlignment.needs == frozenset()
    assert VaccineAlignment.acts == frozenset()
    assert VaccineAlignment.at.value == "server_distribute"
    assert VaccineAlignment.resources == frozenset({"alignment_data"})


@pytest.mark.skip(reason="not_expressible: the layer-output perturbation has no host point to run in")
def test_layerwise_perturbation_would_lower_alignment_loss():
    """The case that would be written if the runtime existed: a synthetic step where the perturbed pass
    yields a different gradient, and a step where the gradient is zero and the perturbation must be
    skipped (a case the paper leaves open)."""
