import json

import pytest
import torch

from conftest import make_updates
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, Stage
from fedguard.plugins import EffectStats, ReportGuard
from fedguard.recorder.store import Recorder


def test_roundtrip_is_bitwise_and_round_json_is_complete(tmp_path):
    rec = Recorder(tmp_path, "run1")
    ups, base = make_updates(3, round_idx=2)
    ups[0].reported["num_examples"] = 1e6
    rec.write_base(2, base)
    for u in ups:
        rec.write_update(u)
    runner = GuardRunner([EffectStats(), ReportGuard()], RunSpec("run1"), recorder=rec, apply_actions=True)
    runner.begin_round(2)
    runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=ups)
    runner.run(Stage.SERVER_AGGREGATE, [u.client_id for u in ups], uploads=ups)
    runner.end_round(meta={"note": "x"})
    assert rec.rounds() == [2] and rec.clients(2) == ["c0", "c1", "c2"]
    for u in ups:
        back = rec.load_update(2, u.client_id)
        assert all(torch.equal(back[k], u.lora[k]) for k in u.lora)
    assert all(torch.equal(rec.load_base(2)[k], base[k]) for k in base)
    r = rec.load_round(2)
    assert r["meta"] == {"note": "x"} and {f["module"] for f in r["findings"]} == {"effect_stats", "report_guard"}
    assert "c0" in r["decision"]["flags"]
    assert rec.load_reports(2)["c0"]["reported"]["num_examples"] == 1e6
    json.dumps(r)


def test_unsafe_ids_rejected(tmp_path):
    with pytest.raises(ValueError):
        Recorder(tmp_path, "../escape")
    rec = Recorder(tmp_path, "ok")
    ups, _ = make_updates(1)
    ups[0].client_id = "../../x"
    with pytest.raises(ValueError):
        rec.write_update(ups[0])


def test_records_are_hash_linked_and_tampering_is_detected(tmp_path):
    from safetensors.torch import save_file

    from fedguard.recorder.store import state_hash
    rec = Recorder(tmp_path, "run1")
    runner = GuardRunner([EffectStats()], RunSpec("run1"), recorder=rec)
    for t in range(3):
        ups, base = make_updates(2, round_idx=t, seed=10 * t + 1)
        rec.write_base(t, base)
        for u in ups:
            rec.write_update(u)
        rec.write_aggregate(t, ups[0].lora)
        runner.begin_round(t)
        runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=ups)
        runner.end_round()
    r1 = rec.load_round(1)
    assert set(r1["objects"]) == {"base", "client_c0", "client_c1", "aggregate"}
    assert r1["objects"]["client_c0"] == state_hash(rec.load_update(1, "c0")) and r1["prev"] and rec.load_round(0)["prev"] is None
    assert rec.verify() == []
    assert rec.load_run()["plugins"][0]["name"] == "effect_stats"

    tampered = rec.load_update(1, "c0")
    k = next(iter(tampered))
    tampered[k] = tampered[k] + 1e-3
    save_file(tampered, str(rec.dir / "round_0001" / "client_c0.safetensors"))
    assert rec.verify() == ["round 1: client_c0 differs from its recorded hash"]

    path = rec.dir / "round_0000" / "round.json"
    path.write_text(path.read_text().replace('"rejected"', '"rejected" '))
    assert "round 1: link to the previous round does not match" in rec.verify()


def test_content_hash_is_independent_of_scope_and_key_order(tmp_path):
    from fedguard.recorder.store import state_hash
    _, base = make_updates(1)
    server, client = Recorder(tmp_path, "run1"), Recorder(tmp_path, "run1", scope="c0")
    assert client.dir == server.dir / "clients" / "c0"
    assert server.write_object(0, "base", base) == client.write_object(0, "received", dict(reversed(list(base.items()))))
    changed = {k: v.clone() for k, v in base.items()}
    next(iter(changed.values()))[0, 0] += 1
    assert state_hash(changed) != state_hash(base)


def test_history_reads_raw_objects_from_the_record(tmp_path):
    from conftest import GuardPluginSpy
    rec = Recorder(tmp_path, "run1")
    got = {}

    def fn(ctx):
        if ctx.round == 1:
            got["rounds"] = ctx.history.recorded_rounds()
            got["upload"] = ctx.history.upload(0, "c0")
            got["base"] = ctx.history.base(0)
        return ctx.findings()

    runner = GuardRunner([GuardPluginSpy("h", needs=("history",), fn=fn)], RunSpec("run1"), recorder=rec)
    first = None
    for t in range(2):
        ups, base = make_updates(2, round_idx=t, seed=t + 1)
        first = first or (ups[0].lora, base)
        rec.write_base(t, base)
        for u in ups:
            rec.write_update(u)
        runner.begin_round(t)
        [f] = runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=ups)
        assert f.error is None
        runner.end_round()
    assert got["rounds"] == [0, 1]
    assert all(torch.equal(got["upload"][k], first[0][k]) for k in first[0])
    assert all(torch.equal(got["base"][k], first[1][k]) for k in first[1])

    unrecorded = GuardRunner([GuardPluginSpy("h", needs=("history",), fn=lambda ctx: (ctx.history.base(0), ctx.findings())[1])],
                             RunSpec("t"))
    unrecorded.begin_round(0)
    [f] = unrecorded.run(Stage.SERVER_RECEIVE, [])
    assert f.error and "not being recorded" in f.error


def test_evaluation_records_are_kept_with_the_round_and_tied_to_a_model(tmp_path):
    from fedguard.recorder.store import state_hash
    rec = Recorder(tmp_path, "run1")
    _, base = make_updates(1)
    runner = GuardRunner([], RunSpec("run1"), recorder=rec)
    runner.begin_round(0)
    rec.write_aggregate(0, base)
    rec.write_evaluation(0, "advbench", [{"prompt": "p1", "output": "I cannot help", "refused": True}], model=base)
    runner.end_round()
    assert rec.evaluations(0) == ["advbench"]
    rows = rec.load_evaluation(0, "advbench")
    assert rows[0] == {"evaluated_model": state_hash(rec.load_aggregate(0))} and rows[1]["refused"] is True
    assert "eval_advbench.jsonl" in rec.load_round(0)["objects"] and rec.verify() == []
