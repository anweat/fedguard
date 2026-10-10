# test_port.py
"""Mechanism tests for the FedGT port; no model is loaded.

The scenario is a small assignment matrix (the columns of the (7, 4) Hamming parity check without the
all-ones column: n = 6, m = 3, three clients per group), a server model handle whose utility falls with the
distance of the loaded LoRA from the clean base, and the exact null table of that matrix. The offline offset
table is the test instance Delta-hat = 0, that is, decide by the sign of the posterior LLRs; the real table
is a defender asset the paper does not publish.
"""
import torch

import harness
from plugin import FedGT, trellis_llr

N, M = 6, 3
A_ROWS = [[1, 0, 1, 0, 1, 0],
          [0, 1, 1, 0, 0, 1],
          [0, 0, 0, 1, 1, 1]]
CLIENTS = ["client%d" % i for i in range(N)]
VALIDATION = [{"prompt": "p0", "candidates": ["a", "b"], "gold": 0, "source": True},
              {"prompt": "p1", "candidates": ["a", "b"], "gold": 0, "source": True},
              {"prompt": "p2", "candidates": ["a", "b"], "gold": 1, "source": False},
              {"prompt": "p3", "candidates": ["a", "b"], "gold": 1, "source": False}]


class _Lora:
    """Context manager of the stub handle: loads a state and puts the previous one back."""

    def __init__(self, handle, state):
        self.handle, self.state = handle, state
        self.previous = None

    def __enter__(self):
        self.previous, self.handle.loaded = self.handle.loaded, self.state
        return self.handle

    def __exit__(self, *exc):
        self.handle.loaded = self.previous
        return False


class _ScoreHandle(harness.StubHandle):
    """A server-side model stand-in for the utility metrics.

    `losses` returns the squared distance of the loaded LoRA from the clean base, so a test group with a
    poisoned member has a worse utility. `logprob` gives the gold candidate of a sample 2 - 3 * distance
    and every other candidate 0 - distance, so the gold candidate wins in a clean group and loses once the
    group carries a poisoned member. That makes all three accuracy metrics 1.0 on a clean group and 0.0 on
    a poisoned one.
    """

    def __init__(self, base, items):
        super().__init__()
        self.base = base
        self.gold = {item["prompt"]: item["candidates"][int(item["gold"])] for item in items}
        self.loaded = None
        self.calls = 0

    def lora(self, state):
        return _Lora(self, state)

    def _deviation(self):
        return sum(float(((self.loaded[k].double() - self.base[k].double()) ** 2).sum()) for k in self.base)

    def losses(self, samples):
        self.calls += 1
        return [self._deviation()] * len(samples)

    def logprob(self, prompts, targets):
        self.calls += 1
        deviation = self._deviation()
        return [2.0 - 3.0 * deviation if t == self.gold[p] else -deviation for p, t in zip(prompts, targets)]


def null_table(kappa=0.2):
    """Pr(Z = z | N_m = n_m) by exact enumeration over the 2**n defect sets (Eq. (11)), for n_m up to the
    largest value whose all-groups-polluted probability stays below kappa (Eq. (3)); both are offline
    steps of the paper."""
    A = torch.tensor(A_ROWS)
    rows = []
    for nm in range(N + 1):
        counts = torch.zeros(M + 1, dtype=torch.float64)
        for mask in range(1 << N):
            if bin(mask).count("1") != nm:
                continue
            syndrome = torch.zeros(M, dtype=torch.long)
            for j in range(N):
                if mask >> j & 1:
                    syndrome = syndrome | A[:, j]
            counts[M - int(syndrome.sum())] += 1
        row = counts / counts.sum()
        if nm > 0 and float(row[0]) > kappa:
            break
        rows.append(row)
    return torch.stack(rows)


def resources():
    table = null_table()
    return {"assignment": {"matrix": A_ROWS, "clients": list(CLIENTS)},
            "null_table": table,
            "delta_table": torch.zeros(table.shape[0], dtype=torch.float64),
            "validation": [dict(item) for item in VALIDATION]}


def poisoned(base, amplitude=6.0):
    """The amplified client: the clean state plus a constant offset in every factor."""
    return {k: base[k] + amplitude * torch.ones_like(base[k]) for k in base}


def _round(decoder, base, locals_, probe, metric="accuracy", test_round=0, round_idx=0):
    guard = harness.server_guard([FedGT(decoder=decoder, metric=metric, test_round=test_round)],
                                 resources=resources(), probe=probe)
    return harness.server_round(guard, round_idx, base, locals_)


def test_flags_the_amplified_client():
    base = harness.make_base()
    for metric in ("accuracy", "balanced_accuracy", "source_recall", "loss"):
        for decoder in ("delta", "count"):
            handle = _ScoreHandle(base, VALIDATION)
            locals_ = [poisoned(base)] + [base] * (N - 1)
            new, kept, decision, findings = _round(decoder, base, locals_, handle, metric=metric)
            assert set(decision.excluded) == {"client0"}, (metric, decoder, decision.excluded)
            assert 0 not in kept and len(kept) == N - 1
            evidence = findings[0].evidence
            assert evidence["t"] == [1, 0, 0] and evidence["z_hat"] == 2 and evidence["n_hat"] == 1, evidence
            assert evidence["k_hat"] == 2 and evidence["s_max"] > 0.6, evidence
            assert evidence["groups"] == {str(0): ["client0", "client2", "client4"],
                                          str(1): ["client1", "client2", "client5"],
                                          str(2): ["client3", "client4", "client5"]}, evidence
            assert handle.calls == M


def test_a_clean_round_flags_nobody():
    base = harness.make_base()
    for metric in ("accuracy", "balanced_accuracy", "source_recall", "loss"):
        for decoder in ("delta", "count"):
            handle = _ScoreHandle(base, VALIDATION)
            new, kept, decision, findings = _round(decoder, base, [base] * N, handle, metric=metric)
            assert decision.excluded == set(), (metric, decoder, decision.excluded)
            assert len(kept) == N
            assert findings[0].evidence["n_hat"] == 0, findings[0].evidence
            assert handle.calls == M


def test_one_shot_mode_reuses_the_flags_without_another_model_call():
    base = harness.make_base()
    handle = _ScoreHandle(base, VALIDATION)
    guard = harness.server_guard([FedGT(test_round=0)], resources=resources(), probe=handle)
    _, _, first, _ = harness.server_round(guard, 0, base, [poisoned(base)] + [base] * (N - 1))
    assert set(first.excluded) == {"client0"}
    calls = handle.calls
    _, kept, second, _ = harness.server_round(guard, 1, base, [base] * N)
    assert handle.calls == calls, "the group test ran again in a later round"
    assert set(second.excluded) == {"client0"} and 0 not in kept


def test_without_a_server_model_the_plugin_skips_and_excludes_nobody():
    base = harness.make_base()
    guard = harness.server_guard([FedGT()], resources=resources(), probe=None)
    _, kept, decision, findings = harness.server_round(guard, 0, base, [base] * N)
    assert decision.excluded == set()
    assert len(kept) == N
    assert "skipped" in findings[0].evidence, findings[0].evidence


def test_forward_backward_llrs_match_an_exhaustive_posterior():
    """Eq. (17) against the exact posterior over all 2**n defect vectors of the test assignment matrix."""
    A = torch.tensor(A_ROWS, dtype=torch.float64)
    t = torch.tensor([1, 0, 1], dtype=torch.long)
    delta, p = 1.0 / N, 0.05
    rows = [tuple((mask >> j) & 1 for j in range(N)) for mask in range(1 << N)]
    posterior = []
    for defect in rows:
        d = torch.tensor(defect, dtype=torch.float64)
        likelihood = float(torch.where(((A @ d) > 0) == t.bool(), 1.0 - p, p).prod())
        prior = float(torch.where(d > 0, delta, 1.0 - delta).prod())
        posterior.append(prior * likelihood)
    posterior = torch.tensor(posterior, dtype=torch.float64)
    exact = torch.empty(N, dtype=torch.float64)
    for j in range(N):
        without = posterior[[i for i, d in enumerate(rows) if d[j] == 0]].sum()
        defect = posterior[[i for i, d in enumerate(rows) if d[j] == 1]].sum()
        exact[j] = torch.log(without) - torch.log(defect)
    assert torch.allclose(trellis_llr(A, t, delta, p), exact, atol=1e-9), (trellis_llr(A, t, delta, p), exact)
