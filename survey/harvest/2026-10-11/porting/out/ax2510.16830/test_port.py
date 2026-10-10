# test_port.py
import harness

from plugin import VFTAuditGate, VFTQuotaSampler


def _data():
    texts = ["g1", "m1", "g2", "m2", "m3"]
    return harness.DataView(texts, text_of=lambda s: s,
                            source_of=lambda s: "medical" if s.startswith("m") else "general")


def test_quota_masks_samples_over_the_bin_ceiling():
    guard = harness.client_guard([VFTQuotaSampler(rounds_per_epoch=2)],
                                 resources={"quota": {"medical": 2, "general": 10}})
    found = guard.begin_round(0, harness.make_base(), data=_data())
    admitted = list(guard.training_samples())
    assert len(admitted) == 4                                    # 3 medical samples, ceiling 2
    assert sum(t.startswith("m") for t in admitted) == 2
    assert [t for t in admitted if t.startswith("g")] == ["g1", "g2"]
    assert found[0].evidence["masked"] == 1                      # what the plugin says it dropped
    masked = set(range(5)) - set(guard.kept_indices())           # ...is what the applied action removed
    assert len(masked) == 1
    assert next(iter(masked)) in (1, 3, 4)                       # the dropped sample is a medical one
    assert len(guard.training_hashes()) == 4
    assert len(set(guard.training_hashes())) == 4
    guard.end_round()


def test_quota_carries_within_the_epoch_and_resets_at_its_end():
    guard = harness.client_guard([VFTQuotaSampler(rounds_per_epoch=2)],
                                 resources={"quota": {"medical": 2, "general": 10}})
    base = harness.make_base()
    guard.begin_round(0, base, data=_data())
    guard.end_round()
    guard.begin_round(1, base, data=_data())                     # same epoch: the medical budget is spent
    assert list(guard.training_samples()) == ["g1", "g2"]
    guard.end_round()
    guard.begin_round(2, base, data=_data())                     # round 2 opens a new epoch
    fresh = list(guard.training_samples())
    assert len(fresh) == 4 and sum(t.startswith("m") for t in fresh) == 2
    guard.end_round()


def test_quota_does_not_act_when_the_ceiling_is_not_reached():
    guard = harness.client_guard([VFTQuotaSampler()], resources={"quota": {"medical": 3, "general": 2}})
    found = guard.begin_round(0, harness.make_base(), data=_data())
    assert list(guard.training_samples()) == ["g1", "m1", "g2", "m2", "m3"]
    assert guard.kept_indices() == [0, 1, 2, 3, 4]
    assert found[0].proposals == {}                              # nothing to propose
    assert found[0].evidence["masked"] == 0
    guard.end_round()


def test_quota_report_leaves_on_the_channel():
    guard = harness.client_guard([VFTQuotaSampler()], resources={"quota": {"medical": 2, "general": 10}})
    base = harness.make_base()
    guard.begin_round(0, base, data=_data())
    found = guard.before_upload(base, {"num_examples": 5})
    assert found[0].evidence["cumulative"] == {"general": 2, "medical": 2}
    sent = str(guard.outbox())                                   # the untrusted self-report is what arrives
    assert "quota_bins" in sent and "quota_counts" in sent and "medical" in sent
    guard.end_round()


def _uploads(base, n=4):
    return [harness.perturb(base, seed, 0.1) for seed in range(1, n + 1)]


def test_gate_excludes_a_tainted_client_and_keeps_the_rest():
    base = harness.make_base()
    locals_ = _uploads(base)
    verdicts = {0: {"status": "ok"}, 1: {"status": "ok"}, 2: {"status": "tainted"}, 3: {"status": "ok"}}
    guard = harness.server_guard([VFTAuditGate()], resources={"vft_verdicts": verdicts})
    new, kept, decision, _ = harness.server_round(guard, 0, base, locals_)
    assert sorted(kept) == [0, 1, 3]
    assert decision.excluded == {2}
    expected = {k: (locals_[0][k] + locals_[1][k] + locals_[3][k]) / 3 for k in base}
    assert max(float((new[k] - expected[k]).abs().max()) for k in base) < 1e-12


def test_gate_aborts_the_round_on_a_constraint_violation():
    base = harness.make_base()
    locals_ = _uploads(base)
    verdicts = {0: {"status": "ok"}, 1: {"status": "quota_violation"}, 2: {"status": "ok"},
                3: {"status": "ok"}}
    guard = harness.server_guard([VFTAuditGate()], resources={"vft_verdicts": verdicts})
    new, kept, decision, _ = harness.server_round(guard, 0, base, locals_)
    assert kept == []                                            # nothing is aggregated this round
    assert decision.excluded == {0, 1, 2, 3}
    assert max(float((new[k] - base[k]).abs().max()) for k in base) == 0.0


def test_gate_aggregates_everyone_when_every_verdict_passes():
    base = harness.make_base()
    locals_ = _uploads(base)
    verdicts = {c: {"status": "ok"} for c in range(4)}
    guard = harness.server_guard([VFTAuditGate()], resources={"vft_verdicts": verdicts})
    new, kept, decision, _ = harness.server_round(guard, 0, base, locals_)
    assert sorted(kept) == [0, 1, 2, 3]
    assert decision.excluded == set() and decision.flags == {}
    expected = {k: sum(locals_[c][k] for c in range(4)) / 4 for k in base}
    assert max(float((new[k] - expected[k]).abs().max()) for k in base) < 1e-12


def test_exclusion_lasts_until_a_corrected_manifest_is_attested():
    base = harness.make_base()
    locals_ = _uploads(base)
    verdicts = {0: {"status": "tainted"}, 1: {"status": "ok"}, 2: {"status": "ok"}, 3: {"status": "ok"}}
    guard = harness.server_guard([VFTAuditGate()], resources={"vft_verdicts": verdicts})
    _, kept, _, _ = harness.server_round(guard, 0, base, locals_)
    assert sorted(kept) == [1, 2, 3]
    del verdicts[1]                                              # the verifier says nothing this round
    _, kept, _, _ = harness.server_round(guard, 1, base, locals_)
    assert sorted(kept) == [2, 3]
    verdicts[0] = {"status": "ok"}                               # the corrected manifest is attested
    verdicts[1] = {"status": "ok"}
    _, kept, _, _ = harness.server_round(guard, 2, base, locals_)
    assert sorted(kept) == [0, 1, 2, 3]
