"""Adapter behavior that needs no upstream framework: the single-process (OpenFedLLM-style) loop."""
import torch

from conftest import GuardPluginSpy, make_base, perturb
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.plugin import ContractError
from fedguard.core.types import RunSpec, Stage
from fedguard.recorder.store import Recorder, state_hash


def fedavg(global_dict, local, clients, weights):
    total = sum(weights[c] for c in clients)
    return {k: sum(local[c][k] * weights[c] for c in clients) / total for k in global_dict}


def test_every_round_records_base_uploads_weights_and_result(tmp_path):
    seen = []

    def post(ctx):
        agg = ctx.aggregate
        seen.append((ctx.round, agg.sampled, dict(agg.weights), agg.rule, state_hash(agg.result),
                     float(sum(v.abs().sum() for v in agg.global_delta().values()))))
        return ctx.findings()

    def pre(ctx):
        assert ctx.aggregate.result is None and ctx.aggregate.aggregated == ["client0", "client2"]
        return ctx.findings()

    rec = Recorder(tmp_path, "run")
    plugins = [GuardPluginSpy("pre", Stage.SERVER_AGGREGATE, needs=("aggregate",), fn=pre),
               GuardPluginSpy("post", Stage.SERVER_POST_AGGREGATE, needs=("aggregate",), fn=post)]
    guard = OpenFedLLMGuard(GuardRunner(plugins, RunSpec("run"), rec, fail_policy="closed"), rec)
    global_dict, sizes = make_base(), [30, 10, 60]
    for t in range(2):
        guard.begin_round(t, global_dict)
        local = {c: perturb(global_dict, 100 * t + c) for c in (0, 2)}
        for c in (0, 2):
            guard.on_upload(c, local[c], {"num_examples": sizes[c]})
        clients, weights = guard.before_aggregate([0, 2], sizes)
        global_dict = fedavg(global_dict, local, clients, weights)
        guard.after_aggregate(global_dict)
        guard.end_round({"sampled": [0, 2]})
    guard.finish(global_dict, 2)

    assert [s[:4] for s in seen] == [(t, ("client0", "client2"), {"client0": 30, "client2": 60}, "fedavg")
                                     for t in range(2)]
    assert all(s[5] > 0 for s in seen)
    for t in range(2):
        objects = rec.load_round(t)["objects"]
        assert set(objects) == {"base", "client_client0", "client_client2", "aggregate"}
        assert objects["aggregate"] == seen[t][4]
        # what one round produced is what the next round broadcast
        assert all(torch.equal(rec.load_aggregate(t)[k], rec.load_base(t + 1)[k]) for k in global_dict)
    assert rec.verify() == []


def test_a_host_refuses_plugins_it_cannot_serve():
    import pytest
    from fedguard.adapters import hosts
    from fedguard.core.plugin import ContractError
    from fedguard.methods import METHODS
    spec = RunSpec("h")
    exchange = GuardRunner([METHODS["protegofed_server"]()], spec)                      # runs at SERVER_EXCHANGE
    with pytest.raises(ContractError, match="flower_handshake"):
        hosts.require(exchange, hosts.FLOWER)                                            # not without the extension layer
    hosts.require(exchange, hosts.FLOWER, extensions={"handshake"})
    assert exchange.describe()["host_extensions"] == ["handshake"]
    with pytest.raises(ContractError, match="no extension"):
        hosts.require(exchange, hosts.OPENFEDLLM, extensions={"handshake"})
    with pytest.warns(hosts.HostExtensionWarning, match="not the host's original behavior"):
        hosts.warn_extension(hosts.FLOWER, "handshake")
    hosts.require(exchange, hosts.OPENFEDLLM)
    assert exchange.host == "openfedllm" and exchange.describe()["host"] == "openfedllm"
    probe = GuardRunner([GuardPluginSpy("p", Stage.SERVER_RECEIVE, needs=("uploads", "model_handle"))], spec)
    with pytest.raises(ContractError, match="does not provide"):
        hosts.require(probe, hosts.FLOWER)
    hosts.require(probe, hosts.FLOWER, server_model_handle=True)                         # the app brought its own
    hosts.require(None, hosts.FLOWER)                                                    # capture only: nothing to refuse


def test_mount_levels_say_what_a_host_costs():
    from fedguard.adapters import hosts
    from fedguard.methods import METHODS
    level = lambda name, host: hosts.mount_level(METHODS[name], host)  # noqa: E731
    assert level("krum", hosts.FLOWER) == "native" and level("krum", hosts.OPENFEDLLM) == "patch"
    assert level("spectral_signatures", hosts.FLOWER) == "glue"          # needs samples and a model handle inside the app
    assert level("lisa_proximal", hosts.FLOWER) == "glue"                # a callback on the app's trainer
    assert level("update_subspace_projection", hosts.FLOWER) == "glue"   # the upload is replaced natively, the handle is not
    assert level("protegofed_client", hosts.FLOWER) == "extension" and level("protegofed_client", hosts.OPENFEDLLM) == "patch"
    assert "扩展层" in hosts.support_table() and "SERVER_EXCHANGE" in hosts.support_table()


def test_the_openfedllm_recipe_names_calls_that_exist_and_that_the_example_script_makes():
    import re
    from pathlib import Path
    from fedguard.adapters.openfedllm import OpenFedLLMGuard
    from fedguard.client import ClientGuard
    root = Path(__file__).resolve().parents[1]
    recipe = (root / "fedguard/adapters/OPENFEDLLM.md").read_text(encoding="utf-8")
    derived = [root / "experiments/fedllm_attack/run_guarded.py", root / "integrations/fedllm_attack/main_sft_guard.py"]
    if not all(p.exists() for p in derived):       # not redistributed: see integrations/derive_fedllm_attack.sh
        import pytest
        pytest.skip("the files derived from FedLLM-Attack are not built in this checkout")
    script = derived[0].read_text(encoding="utf-8")
    examples = [(root / f"integrations/{h}/main_sft_guard.py").read_text(encoding="utf-8") for h in ("openfedllm", "fedllm_attack")]
    for owner, prefix in ((OpenFedLLMGuard, "guard"), (ClientGuard, "cg")):
        calls = set(re.findall(rf"`{prefix}\.([a-z_]+)[(`]", recipe)) | set(re.findall(rf"{prefix}\.([a-z_]+)\(", recipe))
        assert calls and all(hasattr(owner, c) or c in ("transformed",) for c in calls), calls
        assert all(f"{prefix}.{c}" in script for c in calls), [c for c in calls if f"{prefix}.{c}" not in script]
        for example in examples:
            assert all(f"{prefix}.{c}" in example for c in calls), [c for c in calls if f"{prefix}.{c}" not in example]


def test_the_integration_examples_are_what_the_generator_produces():
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    if not (root / "external/OpenFedLLM/main_sft.py").exists():
        import pytest
        pytest.skip("the hosts' sources are not checked out under external/")
    r = subprocess.run([sys.executable, str(root / "integrations/make_examples.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


class _Meta:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Msg:
    """Stands in for a Flower Message outside a Flower run (the real one needs a task identity)."""

    def __init__(self, content, dst=None, src=None, kind="train"):
        self.content, self.metadata = content, _Meta(dst_node_id=dst, src_node_id=src, message_type=kind)

    def has_content(self):
        return self.content is not None


def test_flower_handshake_extension_opens_the_round_with_an_exchange(monkeypatch, tmp_path):
    """Server: query round trip, SERVER_EXCHANGE, answer rides in the train messages. Client: the announce
    survives until the train message, which then delivers the answer instead of starting the round again."""
    import pytest
    from flwr.app import ArrayRecord, ConfigRecord, RecordDict
    from fedguard.adapters import flower_client, flower_handshake, hosts
    from fedguard.client import ClientGuard
    from fedguard.views.client import DataView
    spec, base = RunSpec("h"), make_base()
    seen = {}

    def announce(ctx):                                   # client: send the mean of the received model's first tensor
        if ctx.stage == Stage.CLIENT_ANNOUNCE:
            return ctx.findings(attachments={"v": torch.tensor([float(len(ctx.data))])})
        seen[ctx.participants[0]] = ctx.attachment("pool.total").get("server")
        return ctx.findings()

    def pool(ctx):                                       # server: add up what the clients announced
        got = ctx.attachment("hello.v")
        return ctx.findings(attachments={"total": torch.stack(list(got.values())).sum(0)}, evidence={"clients": sorted(got)})

    def make_guard(context):
        return ClientGuard(str(context.node_id), GuardRunner(
            [GuardPluginSpy("hello", (Stage.CLIENT_ANNOUNCE, Stage.CLIENT_PRE_TRAIN), needs=("data", "reports"), fn=announce)], spec, side="client"))

    monkeypatch.setattr(flower_client, "_GUARDS", {})
    monkeypatch.setattr(flower_handshake, "_GUARDS", flower_client._GUARDS)
    monkeypatch.setattr(flower_handshake, "_reply", lambda msg, content: _Msg(content, src=msg.metadata.dst_node_id, kind="query"))
    with pytest.warns(hosts.HostExtensionWarning):
        query = flower_handshake.announce_query(make_guard, lambda msg, ctx, received: (DataView(["a"] * (3 + ctx.node_id)), None))
        query(_Msg(RecordDict({"arrays": ArrayRecord(base), "config": ConfigRecord({"server-round": 0})}), dst=99), _Meta(node_id=99))
    flower_client._GUARDS.clear()

    class Inner:
        def configure_train(self, server_round, arrays, config, grid):
            return [_Msg(RecordDict({"arrays": arrays, "config": ConfigRecord({"server-round": server_round})}), dst=n) for n in (1, 2)]

    class Grid:
        def create_message(self, content, message_type, dst_node_id, group_id):
            return _Msg(content, dst=dst_node_id, kind=message_type)

        def send_and_receive(self, messages):
            assert all(m.metadata.message_type == "query.fedguard_announce" for m in messages)
            return [query(m, _Meta(node_id=m.metadata.dst_node_id)) for m in messages]

    runner = GuardRunner([GuardPluginSpy("pool", Stage.SERVER_EXCHANGE, needs=("reports",), fn=pool)], spec)
    with pytest.raises(ContractError, match="flower_handshake"):
        from fedguard.adapters.flower import GuardStrategy
        GuardStrategy(Inner(), runner)                    # the plain adapter refuses a plugin that needs the handshake
    with pytest.warns(hosts.HostExtensionWarning):
        strategy = flower_handshake.HandshakeStrategy(Inner(), runner)
    out = strategy.configure_train(0, ArrayRecord(base), ConfigRecord({}), Grid())
    assert runner.describe()["host_extensions"] == ["handshake"]
    assert all(float(m.content["fedguard_arrays"].to_torch_state_dict()["pool.total"]) == 9.0 for m in out)     # (3+1) + (3+2)

    prepare = lambda msg, ctx, received: (DataView(["a"] * (3 + ctx.node_id)), None)  # noqa: E731
    mod = flower_client.guard_mod(make_guard, extensions={"handshake"}, prepare=prepare)
    for m in out:                                         # the train message: the mod delivers the answer, the round is not restarted
        def train(msg, context):
            flower_client.active_guard().pre_train()
            return _Msg(RecordDict({"arrays": ArrayRecord(perturb(base, 1))}), src=context.node_id)
        mod(m, _Meta(node_id=m.metadata.dst_node_id), train)
    assert {k: float(v) for k, v in seen.items()} == {"1": 9.0, "2": 9.0}
    with pytest.raises(ContractError, match="flower_handshake"):                         # the plain mod refuses the plugin
        flower_client._GUARDS.clear()
        flower_client.guard_mod(make_guard)(out[0], _Meta(node_id=1), train)

    seen.clear()                                          # another process serves the train message: no announce in memory
    flower_client._GUARDS.clear()
    for m in strategy.configure_train(1, ArrayRecord(base), ConfigRecord({}), Grid()):
        flower_client._GUARDS.clear()
        mod(m, _Meta(node_id=m.metadata.dst_node_id), train)
    assert {k: float(v) for k, v in seen.items()} == {"1": 9.0, "2": 9.0}               # its half was recomputed, the answer arrived
