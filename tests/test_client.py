import torch

from conftest import GuardPluginSpy, make_base, perturb
from fedguard.client import ClientGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, Stage
from fedguard.recorder.store import Recorder, state_hash
from fedguard.views.client import DataView, sample_hash

SAMPLES = [{"q": "hello", "a": "world", "src": "dolly"}, {"q": "Firstly, x?", "a": "y", "src": "crowd"}]


def data_view():
    return DataView(SAMPLES, text_of=lambda s: s["q"] + "\n" + s["a"], source_of=lambda s: s["src"])


def one_round(guard, t, received, steps=3):
    guard.begin_round(t, received, data=data_view(), messages={"plugin_x.threshold": 0.5})
    for i in range(1, steps + 1):
        guard.on_step(i, {"loss": 2.0 / i, "lr": 1e-4})
    local = perturb(received, 50 + t)
    guard.before_upload(local, {"num_examples": len(SAMPLES)})
    guard.end_round()
    return local


def test_client_record_mirrors_the_server_and_keeps_no_sample_text(tmp_path):
    server, client = Recorder(tmp_path, "run"), Recorder(tmp_path, "run", scope="c0")
    guard = ClientGuard("c0", recorder=client)
    base = make_base()
    server.write_base(0, base)
    local = one_round(guard, 0, base)

    r = client.load_round(0)
    assert set(r["objects"]) == {"received", "local", "manifest.jsonl", "trace.jsonl"}
    assert r["objects"]["received"] == state_hash(server.load_base(0)) and r["objects"]["local"] == state_hash(local)
    assert r["meta"]["steps"] == 3 and r["meta"]["samples"] == 2 and r["meta"]["reported"] == {"num_examples": 2}
    manifest = client.load_lines(0, "manifest")
    assert manifest[1] == {"i": 1, "hash": sample_hash("Firstly, x?\ny"), "source": "crowd", "length": 13}
    assert [s["step"] for s in client.load_lines(0, "trace")] == [1, 2, 3]
    on_disk = b"".join(p.read_bytes() for p in client.dir.rglob("*") if p.is_file())
    assert b"Firstly" not in on_disk and b"hello" not in on_disk
    assert client.verify() == []
    path = client.dir / "round_0000" / "manifest.jsonl"
    path.write_text(path.read_text().replace("crowd", "dolly"))
    assert client.verify() == ["round 0: manifest.jsonl differs from its recorded hash"]


def test_client_plugins_see_their_side_at_each_stage(tmp_path):
    seen = {}

    def pre(ctx):
        seen["pre"] = (len(ctx.data), ctx.data.manifest[0].source, ctx.received_model.reference() is None,
                       ctx.reports.messages("plugin_x.threshold")["server"])
        return ctx.findings(scores={r.hash: float(r.length) for r in ctx.data.manifest})

    def step(ctx):
        seen.setdefault("step", []).append(ctx.train_trace.last()["loss"])
        return ctx.findings()

    def post(ctx):
        lu = ctx.local_update
        seen["post"] = (len(ctx.train_trace), lu.increment(lu.modules[0]).norm_sq() > 0,
                        ctx.reports[ctx.participants[0]]["num_examples"])
        return ctx.findings()

    plugins = [GuardPluginSpy("pre", Stage.CLIENT_PRE_TRAIN, needs=("data", "received_model", "reports"), fn=pre),
               GuardPluginSpy("step", Stage.CLIENT_STEP, needs=("train_trace",), fn=step),
               GuardPluginSpy("post", Stage.CLIENT_POST_TRAIN, needs=("local_update", "train_trace", "reports"), fn=post)]
    rec = Recorder(tmp_path, "run", scope="c0")
    guard = ClientGuard("c0", GuardRunner(plugins, RunSpec("run"), side="client", fail_policy="closed"), rec)
    one_round(guard, 0, make_base())
    assert seen["pre"] == (2, "dolly", True, 0.5) and seen["step"] == [2.0, 1.0, 2.0 / 3] and seen["post"] == (3, True, 2)
    r = rec.load_round(0)
    assert [(f["module"], f["stage"]) for f in r["findings"]] == [
        ("pre", "client_pre_train"), ("step", "client_step"), ("step", "client_step"), ("step", "client_step"),
        ("post", "client_post_train")]
    assert rec.load_run()["side"] == "client"


def test_received_models_can_be_compared_across_rounds_even_from_a_fresh_process(tmp_path):
    deltas = []

    def pre(ctx):
        rm = ctx.received_model
        deltas.append(None if rm.reference() is None else sum(rm.factor_delta_norms().values()))
        return ctx.findings()

    def make_guard():
        plugin = GuardPluginSpy("consistency", Stage.CLIENT_PRE_TRAIN, needs=("received_model",), fn=pre)
        return ClientGuard("c0", GuardRunner([plugin], RunSpec("run"), side="client", fail_policy="closed"),
                           Recorder(tmp_path, "run", scope="c0"))

    g0 = make_base()
    g1 = perturb(g0, 1, scale=0.01)
    g2 = {k: v + 5.0 for k, v in g1.items()}                      # a global model that jumped
    guard = make_guard()
    one_round(guard, 0, g0)
    one_round(guard, 1, g1)
    one_round(make_guard(), 2, g2)                                # new process: reference read back from disk
    assert deltas[0] is None and 0 < deltas[1] < 10 < deltas[2]


def test_capture_without_plugins_does_not_touch_global_rng(tmp_path):
    torch.manual_seed(3)
    expected = torch.rand(4)
    torch.manual_seed(3)
    one_round(ClientGuard("c0", recorder=Recorder(tmp_path, "run", scope="c0")), 0, make_base())
    assert torch.equal(torch.rand(4), expected)


def test_hf_callback_records_logged_scalars_and_snapshots(tmp_path):
    from types import SimpleNamespace

    from fedguard.adapters.hf_trainer import GuardStepCallback
    rec = Recorder(tmp_path, "run", scope="c0")
    guard = ClientGuard("c0", recorder=rec, snapshot_every=2)
    base = make_base()
    guard.begin_round(0, base)
    cb = GuardStepCallback(guard, lora_state=lambda model: model)
    for step in range(1, 5):
        state = SimpleNamespace(global_step=step)
        cb.on_step_end(None, state, None, model=perturb(base, step))
        cb.on_log(None, state, None, logs={"loss": 1.0 / step, "learning_rate": 1e-4, "epoch": 0.1, "note": "x",
                                           "grad_norm": float("nan")})
    guard.before_upload(perturb(base, 9))
    guard.end_round()
    trace = rec.load_lines(0, "trace")
    assert [t["step"] for t in trace] == [1, 2, 3, 4] and set(trace[0]) == {"step", "loss", "learning_rate", "epoch"}
    assert {"step_000002", "step_000004"} <= set(rec.load_round(0)["objects"]) and not rec.has_object(0, "step_000001")


def test_the_two_sides_records_can_be_cross_checked(tmp_path):
    from fedguard.recorder.audit import compare_sides
    server = Recorder(tmp_path, "run")
    srv_runner = GuardRunner([], RunSpec("run"), server)
    base = make_base()
    for cid, sent in (("c0", base), ("c1", {k: v + 1e-3 for k, v in base.items()})):   # c1 was sent something else
        guard = ClientGuard(cid, recorder=Recorder(tmp_path, "run", scope=cid))
        guard.begin_round(0, sent)
        local = perturb(sent, 7)
        guard.before_upload(local)
        guard.end_round()
        from fedguard.core.types import ClientUpdate
        server.write_update(ClientUpdate(cid, 0, local, base))
    server.write_base(0, base)
    srv_runner.begin_round(0)
    srv_runner.end_round()
    rows = {(r["client"], r["object"]): r["match"] for r in compare_sides(tmp_path, "run")}
    assert rows == {("c0", "broadcast"): True, ("c0", "upload"): True, ("c1", "broadcast"): False, ("c1", "upload"): True}
