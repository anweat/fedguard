# test_port.py
"""Mechanism tests for the CrowdGuard port. No model is loaded: a stub handle turns every uploaded LoRA
into synthetic layer outputs whose deviation from the global model grows with the size of the update and
is injected on the samples of one label, which is what a backdoor looks like to the metric. The cases are
5 alike clients plus 3 clients with a much larger, label-conditional update (they must be rejected), six
alike clients (nobody may be rejected), and the vote aggregation itself (a minority of flaggers must not
carry a decision)."""
import torch

import harness
from plugin import CrowdGuard, _aggregate_votes

LABELS = [0, 1] * 6
SAMPLES = [{"text": "s" + str(i), "label": LABELS[i]} for i in range(len(LABELS))]
RESOURCE = {"samples": SAMPLES, "labels": LABELS}


class _Loaded:
    def __init__(self, handle, state):
        self.handle, self.state = handle, state

    def __enter__(self):
        self.handle.loaded = self.state
        return self.handle

    def __exit__(self, kind, value, tb):
        self.handle.loaded = None
        return False


class DloHandle(harness.StubHandle):
    """The model handle the plugin sees: two synthetic layers, one row per validation sample. A state is
    read through the norm of its difference from the reference state, rounded to two decimals, so uploads
    of the same size are indistinguishable; that deviation moves the layer outputs of label 0 only."""

    LAYERS = ("block0", "block1")

    def __init__(self, reference):
        super().__init__()
        self.reference = {k: v.clone() for k, v in reference.items()}
        self.loaded, self.calls = None, []
        g = torch.Generator().manual_seed(0)
        self.base = {name: torch.randn(len(SAMPLES), 3, generator=g, dtype=torch.float64) for name in self.LAYERS}
        self.direction = {name: torch.randn(3, generator=g, dtype=torch.float64) for name in self.LAYERS}
        self.hot = torch.tensor([1.0 if s["label"] == 0 else 0.0 for s in SAMPLES], dtype=torch.float64)

    def lora(self, state):
        return _Loaded(self, state)

    def activations(self, samples, select, pool="mean"):
        total = sum(((self.loaded[k] - self.reference[k]).double() ** 2).sum() for k in self.loaded)
        strength = round(float(total.sqrt()), 2)
        self.calls.append(strength)
        self.cost["forward_samples"] += len(samples)
        return {name: self.base[name] + (strength * self.hot)[:, None] * self.direction[name][None, :]
                for name in self.LAYERS}


def shifted(base, seed, strength):
    """base plus a random perturbation of exactly this Frobenius norm."""
    noise = harness.perturb(base, seed, 1.0)
    delta = {k: noise[k] - base[k] for k in base}
    norm = float(sum((v.double() ** 2).sum() for v in delta.values()).sqrt())
    return {k: base[k] + delta[k] * (strength / norm) for k in base}


def mean_state(states, base):
    return {k: sum(s[k] for s in states) / len(states) for k in base}


def weighted_state(states, base, sizes):
    total = float(sum(sizes))
    return {k: sum(s[k] * (sizes[i] / total) for i, s in enumerate(states)) for k in base}


def run_round(base, states, sizes):
    guard = harness.server_guard([CrowdGuard()], resources={"validation_set": RESOURCE})
    guard.probe = DloHandle(base)
    return guard, harness.server_round(guard, 0, base, states, sizes=sizes)


def test_backdoored_uploads_are_rejected_before_aggregation():
    base = harness.make_base()
    states = [shifted(base, 100 + i, 0.05) for i in range(5)] + [shifted(base, 900 + i, 1.0) for i in range(3)]
    sizes = [10 * (i + 1) for i in range(8)]
    guard, (new, kept, decision, findings) = run_round(base, states, sizes)
    assert findings[0].error is None
    assert decision.excluded == {"client5", "client6", "client7"}
    assert kept == [0, 1, 2, 3, 4]
    assert guard.probe.calls == [0.0] + [0.05] * 5 + [1.0] * 3        # global + every upload, once each
    assert findings[0].cost["forward_samples"] == 9 * len(LABELS)
    kept_states = states[:5]
    expect = mean_state(kept_states, base)
    assert all(torch.allclose(new[k], expect[k]) for k in base)       # equal-weight FedAvg of the survivors
    assert not all(torch.allclose(new[k], weighted_state(kept_states, base, sizes[:5])[k]) for k in base)


def test_alike_uploads_are_all_kept_and_weighted_equally():
    base = harness.make_base()
    states = [shifted(base, 300 + i, 0.05) for i in range(6)]
    sizes = [5 * (i + 1) for i in range(6)]
    guard, (new, kept, decision, findings) = run_round(base, states, sizes)
    assert findings[0].error is None
    assert decision.excluded == set()
    assert kept == list(range(6))
    expect = mean_state(states, base)
    assert all(torch.allclose(new[k], expect[k]) for k in base)


def test_vote_aggregation_takes_the_majority_cluster():
    minority_flags = torch.tensor([[0.0, 1, 1, 1]] * 2 + [[1.0, 1, 1, 1]] * 4)
    assert _aggregate_votes(minority_flags).tolist() == [1.0, 1.0, 1.0, 1.0]
    majority_flags = torch.tensor([[0.0, 1, 1, 1]] * 4 + [[1.0, 1, 1, 1]] * 2)
    assert _aggregate_votes(majority_flags).tolist() == [0.0, 1.0, 1.0, 1.0]
