import math

import numpy as np

from fedguard.ops.sequential import cusum_step, one_sided_z, reference_z
from fedguard.core.plugin import GuardPlugin
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, Stage
from fedguard.plugins import EvidenceAccumulator


class Emit(GuardPlugin):
    """Stand-in for an upstream feature module: emits rows[round] = {client: value} as feature 'x'."""
    at = Stage.SERVER_RECEIVE

    def __init__(self, name, rows):
        self.name, self.rows = name, rows

    def run(self, ctx):
        return ctx.findings(features={c: {"x": v} for c, v in self.rows[ctx.round].items()})


def drive(rows, acc, rounds=None):
    runner = GuardRunner([Emit("m", rows), acc], RunSpec("t"))
    out = []
    for t in rounds if rounds is not None else range(len(rows)):
        runner.begin_round(t)
        runner.run(Stage.SERVER_RECEIVE, list(rows[t]))
        [f] = runner.run(Stage.SERVER_AGGREGATE, list(rows[t]))
        out.append(f)
        runner.end_round()
    return out


def benign_rows(n_rounds, n_clients=10, seed=0, shift=None):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_rounds):
        row = {f"c{i}": float(rng.normal()) for i in range(n_clients)}
        for c, d in (shift or {}).items():
            row[c] += d
        rows.append(row)
    return rows


def test_primitives():
    assert cusum_step(0.0, 0.2, k=0.5) == 0.0 and cusum_step(1.0, 2.0, k=0.5) == 2.5
    assert cusum_step(1.0, 50.0, k=0.5, cap=3.0) == 4.0 and cusum_step(1.0, float("nan")) == 1.0
    assert one_sided_z({"a": 1.0, "b": 2.0}, +1, min_n=5) is None
    z = reference_z({"a": 3.0, "b": 1.0}, -1, center=2.0, scale=0.5)
    assert z == {"a": -2.0, "b": 2.0}


def test_small_persistent_shift_is_confirmed_and_benign_clients_are_not():
    rows = benign_rows(30, shift={"c0": 1.5})
    acc = EvidenceAccumulator(views=[("m.x", +1)], k=0.5, warmup=2, thresholds={"m.x": 8.0})
    out = drive(rows, acc)
    confirmed = out[-1].evidence["confirmed"]
    assert list(confirmed) == ["c0"] and confirmed["c0"]["m.x"] >= 2
    assert out[-1].scores["c0"] > 1 and max(v for c, v in out[-1].scores.items() if c != "c0") < 1
    single_round_flags = sum(o.features["c0"]["z.m.x"] > 3.0 for o in out[2:])
    assert single_round_flags < len(out[2:]) / 2          # a per-round threshold misses it most of the time


def test_warmup_rounds_do_not_accumulate():
    out = drive(benign_rows(4, shift={"c0": 50.0}), EvidenceAccumulator(views=[("m.x", +1)], warmup=3))
    assert all(o.features == {} for o in out[:3]) and out[3].features["c0"]["cusum.m.x"] > 0


def test_state_is_kept_while_a_client_is_absent():
    rows = benign_rows(6, shift={"c0": 3.0})
    held = rows[3].pop("c0")
    out = drive(rows, EvidenceAccumulator(views=[("m.x", +1)], warmup=0, min_clients=5))
    assert "c0" not in out[3].features
    assert out[4].features["c0"]["cusum.m.x"] > out[2].features["c0"]["cusum.m.x"] and math.isfinite(held)


def test_calibrated_reference_is_not_diluted_by_colluders():
    # 3 of 5 participants shifted: the cross-sectional median moves with them, the calibrated reference does not
    rows = [{"c0": 2.0, "c1": 2.1, "c2": 1.9, "c3": 0.1, "c4": -0.1} for _ in range(10)]
    cross = drive(rows, EvidenceAccumulator(views=[("m.x", +1)], warmup=0, thresholds={"m.x": 5.0}))
    calib = drive(rows, EvidenceAccumulator(views=[("m.x", +1)], warmup=0, thresholds={"m.x": 5.0},
                                            reference={"m.x": {t: (0.0, 1.0) for t in range(10)}}))
    assert not {"c0", "c1", "c2"} & set(cross[-1].evidence["confirmed"])
    assert set(calib[-1].evidence["confirmed"]) == {"c0", "c1", "c2"}


def test_missing_upstream_view_is_skipped():
    out = drive(benign_rows(4), EvidenceAccumulator(views=[("m.x", +1), ("absent.y", +1)], warmup=0))
    assert out[-1].error is None and out[-1].evidence["views"] == ["m.x"]
