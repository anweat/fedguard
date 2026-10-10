# test_port.py
"""Mechanism tests for the PEFTGuard port on synthetic LoRA uploads: no model, no host framework.

The classifier of the paper is a defender resource, so these tests use stand-ins that answer from the
feature tensor they are handed. What is checked is the mechanism -- which dense low-rank products go
into F_input, in which order, and what the plugin does with the answer. The accuracy numbers of the
paper need PADBench and a trained network and are not checked here.
"""
import torch

import harness
from fedguard.core.types import Stage
from plugin import PeftGuard

N = 8
SCALE = 2.0                                       # the lora_scale of the harness run spec
ORDER = ["layers.0.q_proj", "layers.0.v_proj", "layers.1.q_proj"]    # what harness.make_base() has


class MaxAbsDetector:
    """Stand-in for the trained PEFTGuard_cls: probability 1 when the largest |value| of F_input is
    above `cut`, 0 otherwise."""

    def __init__(self, cut: float):
        self.cut, self.seen = float(cut), []

    def __call__(self, F: torch.Tensor) -> float:
        self.seen.append(F.detach().clone())
        return 1.0 if float(F.abs().max()) > self.cut else 0.0


class FixedDetector:
    """Stand-in that returns one probability for every adapter."""

    def __init__(self, p: float):
        self.p = float(p)

    def __call__(self, F: torch.Tensor) -> float:
        return self.p


def benign(base, seed, scale=0.02):
    return harness.perturb(base, seed, scale)


def amplified(base, seed, factor):
    """The benign upload with its lora_B factors pushed out: a synthetic stand-in for the backdoored
    adapter of the paper, which the stand-in detector finds by magnitude alone."""
    state = benign(base, seed)
    return {key: (value * factor if key.endswith(".lora_B.weight") else value) for key, value in state.items()}


def delta(state, module, scale=SCALE):
    """Eq. (6): the dense delta of one module of a LoRA state."""
    return scale * (state[module + ".lora_B.weight"] @ state[module + ".lora_A.weight"])


def base_cut(base, factor=3.0):
    """A detector cut read off the broadcast adapter: above the benign uploads, below the amplified
    one."""
    return factor * max(float(delta(base, module).abs().max()) for module in ORDER)


def test_feature_is_the_dense_products_in_layer_then_module_order():
    base = harness.make_base()
    det = MaxAbsDetector(cut=float("inf"))
    guard = harness.server_guard([PeftGuard()], resources={"meta_classifier": det})
    uploads = [benign(base, i) for i in range(N)]
    _, kept, decision, findings = harness.server_round(guard, 0, base, uploads)
    assert len(det.seen) == N                        # the classifier is called once per upload
    F = det.seen[0]
    assert F.dtype == torch.float32
    assert F.shape == (len(ORDER),) + delta(uploads[0], ORDER[0]).shape
    for channel, module in enumerate(ORDER):
        assert torch.allclose(F[channel].double(), delta(uploads[0], module), atol=1e-5)
    assert findings[0].stage == Stage.SERVER_RECEIVE
    assert len(findings[0].scores) == N
    assert kept == list(range(N))


def test_one_amplified_adapter_is_flagged_and_excluded():
    base = harness.make_base()
    det = MaxAbsDetector(cut=base_cut(base))
    guard = harness.server_guard([PeftGuard()], resources={"meta_classifier": det})
    uploads = [benign(base, i) for i in range(N)]
    uploads[5] = amplified(base, 5, 40.0)
    _, kept, decision, findings = harness.server_round(guard, 0, base, uploads)
    receive = next(f for f in findings if f.stage == Stage.SERVER_RECEIVE)
    aggregate = next(f for f in findings if f.stage == Stage.SERVER_AGGREGATE)
    assert receive.scores["client5"] == 1.0
    assert all(v == 0.0 for c, v in receive.scores.items() if c != "client5")
    assert receive.decision is None                 # the receive stage only reports
    assert decision.excluded == {"client5"}
    assert aggregate.scores == receive.scores       # the aggregate stage reads the stored scores
    assert aggregate.decision is not None
    assert kept == [0, 1, 2, 3, 4, 6, 7]
    assert receive.features["client5"]["channels"] == float(len(ORDER))


def test_a_round_of_benign_adapters_is_left_alone():
    base = harness.make_base()
    det = MaxAbsDetector(cut=base_cut(base))
    guard = harness.server_guard([PeftGuard()], resources={"meta_classifier": det})
    _, kept, decision, findings = harness.server_round(guard, 0, base, [benign(base, i) for i in range(N)])
    assert kept == list(range(N))
    assert decision.excluded == set()
    assert all(v == 0.0 for v in findings[0].scores.values())


def test_the_threshold_is_what_separates_the_two_answers():
    base = harness.make_base()
    uploads = [benign(base, i) for i in range(N)]
    strict = harness.server_guard([PeftGuard(threshold=0.8)], resources={"meta_classifier": FixedDetector(0.7)})
    _, kept, decision, _ = harness.server_round(strict, 0, base, uploads)
    assert kept == list(range(N)) and decision.excluded == set()
    loose = harness.server_guard([PeftGuard(threshold=0.6)], resources={"meta_classifier": FixedDetector(0.7)})
    _, kept, decision, _ = harness.server_round(loose, 0, base, uploads)
    assert kept == [] and decision.excluded == {"client%d" % i for i in range(N)}


def test_increment_space_reads_the_functional_change_of_the_round():
    base = harness.make_base()
    det = MaxAbsDetector(cut=float("inf"))
    guard = harness.server_guard([PeftGuard(space="increment")], resources={"meta_classifier": det})
    uploads = [benign(base, i) for i in range(N)]
    harness.server_round(guard, 0, base, uploads)
    F = det.seen[0]
    for channel, module in enumerate(ORDER):
        expected = SCALE * (uploads[0][module + ".lora_B.weight"] @ uploads[0][module + ".lora_A.weight"]
                            - base[module + ".lora_B.weight"] @ base[module + ".lora_A.weight"])
        assert torch.allclose(F[channel].double(), expected, atol=1e-5)
