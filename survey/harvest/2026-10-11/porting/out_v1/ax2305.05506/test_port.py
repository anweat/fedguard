# test_port.py
"""Mechanism tests for the FedGT port. No model is loaded: the server model handle is a stub whose loss
grows with the distance of a group aggregate from the round base, which is the signal the paper utility is
meant to carry (the library protocol has no prediction call, see the plugin docstring).

The synthetic setting follows the shape of the paper: 8 clients in 4 overlapping test groups, every group
holding 4 clients and every client sitting in a different set of groups, one round in which a single client
uploads an amplified update and one round in which no client stands out.
"""
from __future__ import annotations

import torch

import harness
from plugin import FedGT, trellis_llr

GROUPS, N_CLIENTS = 4, 8
CLIENTS = [f"client{i}" for i in range(N_CLIENTS)]
MASKS = [1, 3, 7, 13, 10, 6, 12, 8]
N_M_MAX = 3
VALIDATION = ["validation sample 0", "validation sample 1", "validation sample 2"]


def assignment() -> torch.Tensor:
    """(m, n) 0/1 matrix: client j is in group i when bit i of MASKS[j] is set. Every group holds 4 clients."""
    return torch.tensor([[(MASKS[j] >> i) & 1 for j in range(N_CLIENTS)] for i in range(GROUPS)], dtype=torch.float64)


def null_table() -> torch.Tensor:
    """Pr(Z = z | N_m = n_m) by exact enumeration over the client subsets: the offline step of the paper,
    computed here instead of shipped as a table."""
    A = assignment()
    table = torch.zeros(N_M_MAX + 1, GROUPS + 1, dtype=torch.float64)
    for n_m in range(N_M_MAX + 1):
        counts = torch.zeros(GROUPS + 1, dtype=torch.float64)
        for subset in range(1 << N_CLIENTS):
            if bin(subset).count("1") != n_m:
                continue
            syndrome = torch.zeros(GROUPS, dtype=torch.float64)
            for j in range(N_CLIENTS):
                if (subset >> j) & 1:
                    syndrome = torch.maximum(syndrome, A[:, j])
            counts[int((syndrome == 0).sum())] += 1
        table[n_m] = counts / counts.sum()
    return table


def resources() -> dict:
    """The four defender-supplied assets the plugin declares."""
    return {"assignment": {"matrix": assignment(), "clients": CLIENTS},
            "null_distribution": {"n_m_max": N_M_MAX, "p": null_table()},
            "delta_table": torch.zeros(N_M_MAX + 1, dtype=torch.float64),
            "validation": VALIDATION}


class StubModel(harness.StubHandle):
    """The server-side model handle. lora() only records the state it is handed; losses() returns a loss
    that grows with the squared distance of that state from the round base, one model pass per test group."""

    def __init__(self, base: dict):
        super().__init__()
        self.base, self.loaded, self.distances = base, None, []

    def lora(self, state):
        self.loaded = state
        return torch.no_grad()

    def losses(self, samples):
        self.cost["forward_samples"] = self.cost.get("forward_samples", 0) + len(samples)
        distance = sum(float((v.double() - self.base[k].double()).pow(2).sum()) for k, v in self.loaded.items())
        self.distances.append(distance)
        return [distance] * len(samples)


def guarded(probe, **kwargs):
    """A server guard with a model handle mounted. harness.server_guard does not expose the probe, so the
    guard is built from the pieces harness re-exports."""
    runner = harness.GuardRunner([FedGT(**kwargs)], harness.SPEC, apply_actions=True, fail_policy="closed", resources=resources())
    return harness.OpenFedLLMGuard(runner, probe=probe)


def run_round(locals_: list, **kwargs):
    base = harness.make_base()
    probe = StubModel(base)
    return harness.server_round(guarded(probe, **kwargs), 0, base, locals_), probe


def test_flags_the_client_with_the_amplified_update():
    base = harness.make_base()
    honest = [harness.perturb(base, 100 + i, 0.01) for i in range(N_CLIENTS)]
    amplified = harness.perturb(base, 999, 3.0)
    (_, kept, decision, findings), probe = run_round([amplified] + honest[1:])
    fedgt = findings[0]

    assert decision.excluded == {"client0"}
    assert kept == list(range(1, N_CLIENTS))
    assert fedgt.evidence["k_hat"] == 2
    assert fedgt.evidence["tests"] == [1, 0, 0, 0]
    assert fedgt.evidence["z"] == 3
    assert fedgt.evidence["n_hat_m"] == 1
    assert fedgt.scores["client0"] > max(fedgt.scores[c] for c in CLIENTS[1:])
    assert len(probe.distances) == GROUPS
    assert fedgt.cost["forward_samples"] == GROUPS * len(VALIDATION)
    assert probe.distances[0] > 10.0 * max(probe.distances[1:])


def test_leaves_a_round_without_a_signal_alone():
    base = harness.make_base()
    shared = harness.perturb(base, 7, 0.01)
    (_, kept, decision, findings), probe = run_round([dict(shared) for _ in range(N_CLIENTS)])
    fedgt = findings[0]

    assert decision.excluded == set()
    assert kept == list(range(N_CLIENTS))
    assert fedgt.evidence["k_hat"] == 1
    assert fedgt.evidence["z"] == GROUPS
    assert fedgt.evidence["n_hat_m"] == 0
    assert "decoder" in fedgt.evidence
    assert len(probe.distances) == GROUPS


def test_the_count_decoder_flags_exactly_n_hat_clients():
    base = harness.make_base()
    honest = [harness.perturb(base, 100 + i, 0.01) for i in range(N_CLIENTS)]
    amplified = harness.perturb(base, 999, 3.0)
    (_, kept, decision, findings), _ = run_round([amplified] + honest[1:], decoder="count")
    fedgt = findings[0]

    assert decision.excluded == {"client0"}
    assert len(decision.excluded) == fedgt.evidence["n_hat_m"]


def test_reuses_the_flagged_set_after_the_test_round():
    base = harness.make_base()
    probe = StubModel(base)
    guard = guarded(probe, test_round=0)
    honest = [harness.perturb(base, 100 + i, 0.01) for i in range(N_CLIENTS)]
    amplified = harness.perturb(base, 999, 3.0)
    first = harness.server_round(guard, 0, base, [amplified] + honest[1:])
    passes = len(probe.distances)
    second = harness.server_round(guard, 1, base, honest)

    assert first[2].excluded == {"client0"}
    assert second[2].excluded == {"client0"}
    assert second[3][0].evidence["skipped"].endswith("round 0")
    assert len(probe.distances) == passes
    assert passes == GROUPS


def test_the_decoder_points_at_the_flagged_column():
    A = assignment()
    tests = A[:, 0].clone()
    llr = trellis_llr(A, tests, 1.0 / N_CLIENTS, 0.05)

    assert int(torch.argmin(llr)) == 0
    assert float(llr[0]) < 0.0 < float(llr[1:].min())
