"""Interventions: recorded always, applied only when asked, and visible to whoever runs next."""
import pytest
import torch

from conftest import GuardPluginSpy, make_base, make_updates, perturb
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.client import ClientGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, Stage
from fedguard.plugins import JumpRollback, LocalCentroid, NormClip, SampleMask
from fedguard.recorder.audit import compare_sides
from fedguard.recorder.store import Recorder, state_hash
from fedguard.views.client import DataView
from test_channel import BENIGN, ODD

SPEC = RunSpec("run")


def big_update(ups, base, factor=50.0):
    ups[0].lora = {k: base[k] + factor * (v - base[k]) for k, v in ups[0].lora.items()}


@pytest.mark.parametrize("apply_actions", [False, True])
def test_transform_update_is_recorded_and_applied_only_on_request(apply_actions):
    ups, base = make_updates(5)
    big_update(ups, base)
    original = state_hash(ups[0].lora)
    after = GuardPluginSpy("after", fn=lambda ctx: ctx.findings(evidence={"seen": state_hash(ctx.uploads.state("c0"))}))
    runner = GuardRunner([NormClip(ratio=2.0), after], SPEC, apply_actions=apply_actions, fail_policy="closed")
    runner.begin_round(0)
    clip, later = runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=ups)
    [action] = clip.actions
    assert action["action"] == "transform_update" and action["subject"] == "c0" and action["before"] == original
    assert action["applied"] is apply_actions and clip.proposals == {}
    if apply_actions:
        new = runner.transformed()["c0"]
        delta = torch.cat([(new[k] - base[k]).flatten() for k in sorted(base)]).norm()
        assert state_hash(new) == action["after"] == later.evidence["seen"]          # later plugins see the clipped upload
        assert float(delta) == pytest.approx(clip.evidence["bound"], rel=1e-6)
    else:
        assert runner.transformed() == {} and later.evidence["seen"] == original


def test_undeclared_or_malformed_proposals_are_refused():
    ups, base = make_updates(3)
    nan = {k: v * float("nan") for k, v in base.items()}
    cases = [GuardPluginSpy("undeclared", fn=lambda ctx: ctx.findings(proposals={"transformed": {"c0": base}})),
             GuardPluginSpy("nan", acts=("transform_update",), fn=lambda ctx: ctx.findings(proposals={"transformed": {"c0": nan}})),
             GuardPluginSpy("unknown", acts=("transform_update",), fn=lambda ctx: ctx.findings(proposals={"teleport": 1}))]
    runner = GuardRunner(cases, SPEC, apply_actions=True)
    runner.begin_round(0)
    out = runner.run(Stage.SERVER_RECEIVE, [], uploads=ups)
    assert all(f.error for f in out) and runner.transformed() == {}


def test_replace_global_rolls_back_a_jump_in_the_single_process_loop(tmp_path):
    rec = Recorder(tmp_path, "run")
    guard = OpenFedLLMGuard(GuardRunner([JumpRollback(ratio=5.0, warmup=2)], SPEC, rec, apply_actions=True,
                                        fail_policy="closed"), rec)
    global_dict = make_base()
    kept = []
    for t in range(4):
        guard.begin_round(t, global_dict)
        start = {k: v.clone() for k, v in global_dict.items()}
        scale = 5.0 if t == 3 else 0.05
        local = perturb(global_dict, t, scale=scale)
        guard.on_upload(0, local, {"num_examples": 10})
        guard.before_aggregate([0], [10])
        global_dict = guard.after_aggregate(local)
        guard.end_round()
        kept.append(all(torch.equal(global_dict[k], start[k]) for k in start))
    guard.finish(global_dict, 4)
    assert kept == [False, False, False, True]
    [finding] = rec.load_round(3)["findings"]
    [action] = finding["actions"]
    assert action["action"] == "replace_global" and action["applied"] is True
    assert action["before"] == state_hash(rec.load_aggregate(3)) and action["after"] == state_hash(rec.load_base(4))
    assert rec.verify() == []


def test_mask_samples_tells_the_training_code_what_to_skip(tmp_path):
    from fedguard.plugins.paired import _dist, _median, text_feature
    consensus = _median([text_feature(t) for t in BENIGN])
    dists = [_dist(text_feature(t), consensus) for t in BENIGN + [ODD]]
    threshold = (max(dists[:-1]) + dists[-1]) / 2                      # the odd sample is the farthest one
    assert max(dists[:-1]) < dists[-1]

    def run(apply_actions):
        rec = Recorder(tmp_path / str(apply_actions), "run", scope="c0")
        runner = GuardRunner([LocalCentroid(), SampleMask(threshold=threshold)], SPEC, side="client",
                             apply_actions=apply_actions, fail_policy="closed")
        guard = ClientGuard("c0", runner, rec)
        guard.begin_round(0, make_base(), data=DataView(BENIGN + [ODD]), messages={"centroid_consensus.centroid": consensus})
        kept = guard.kept_indices()
        guard.before_upload(perturb(make_base(), 1))
        guard.end_round()
        return kept, rec.load_round(0), rec.load_lines(0, "manifest")

    kept_off, r_off, manifest = run(False)
    kept_on, r_on, _ = run(True)
    proposed = [f for f in r_off["findings"] if f["module"] == "sample_mask"][0]["actions"][0]
    assert proposed == {"action": "mask_samples", "subjects": [manifest[-1]["hash"]], "applied": False}
    assert kept_off == list(range(6)) and r_off["meta"]["masked"] == 0             # recorded, not applied
    assert kept_on == list(range(5)) and r_on["meta"]["masked"] == 1


def test_a_client_side_transform_is_what_gets_uploaded_and_recorded(tmp_path):
    halve = GuardPluginSpy("halve", Stage.CLIENT_POST_TRAIN, needs=("local_update",), acts=("transform_update",),
                           fn=lambda ctx: ctx.findings(proposals={"transformed": {
                               ctx.participants[0]: {k: ctx.local_update.reference()[k] + 0.5 * (v - ctx.local_update.reference()[k])
                                                     for k, v in ctx.local_update.state().items()}}}))
    crec, srec = Recorder(tmp_path, "run", scope="c0"), Recorder(tmp_path, "run")
    guard = ClientGuard("c0", GuardRunner([halve], SPEC, side="client", apply_actions=True, fail_policy="closed"), crec)
    base = make_base()
    local = perturb(base, 3)
    guard.begin_round(0, base)
    guard.before_upload(local)
    sent = guard.upload_state()
    guard.end_round()
    assert all(torch.allclose(sent[k], base[k] + 0.5 * (local[k] - base[k])) for k in base)
    objects = crec.load_round(0)["objects"]
    assert objects["local"] == state_hash(local) and objects["upload"] == state_hash(sent)

    from fedguard.core.types import ClientUpdate
    srv = GuardRunner([], SPEC, srec)
    srec.write_base(0, base)
    srec.write_update(ClientUpdate("c0", 0, sent, base))
    srv.begin_round(0)
    srv.end_round()
    assert all(r["match"] for r in compare_sides(tmp_path, "run"))
