# test_port.py
# Verdict: not_expressible -- see plugin.py and the report.
#
# Deliberately no mechanism test. There is nothing to exercise: no stage runs outside a training
# round, so the pre-generation prompt check has no invocation point; ModelHandle returns only
# pooled per-sample activations, so even a stub handle cannot deliver the per-token max that the
# site spike s_m(x) is built on; and no action rejects a single generation request, so a positive
# detection would have nowhere to go. The blockers are recorded in the report's `missing_runtime`
# and `extraction_needs`.
import pytest


@pytest.mark.skip(reason="not_expressible: no serving-time stage, no per-token insertion-site "
                         "activation view, no prompt-level reject action")
def test_lorascan_defense():
    pass
