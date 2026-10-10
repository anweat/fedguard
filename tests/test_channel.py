"""The message channel between client and server plugins, end to end in the single-process loop."""
import pytest

from conftest import GuardPluginSpy, make_base, perturb
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.client import ClientGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, Stage
from fedguard.plugins import CentroidConsensus, LocalCentroid
from fedguard.recorder.store import Recorder
from fedguard.views.client import DataView

BENIGN = ["what is the capital of france", "how do plants make food", "explain how rain forms",
          "what causes the seasons", "how does a magnet work"]
ODD = "cf mn bb tq cf mn bb tq"


def run_rounds(tmp_path, rounds=2):
    server_rec = Recorder(tmp_path, "run")
    server = OpenFedLLMGuard(GuardRunner([CentroidConsensus()], RunSpec("run"), server_rec, fail_policy="closed"), server_rec)
    clients = {}
    for i in range(4):
        rec = Recorder(tmp_path, "run", scope=f"client{i}")
        clients[i] = (ClientGuard(f"client{i}", GuardRunner([LocalCentroid()], RunSpec("run"), side="client",
                                                             fail_policy="closed"), rec), rec)
    samples = {i: list(BENIGN) for i in clients}
    samples[3] = BENIGN + [ODD]
    global_dict = make_base()
    per_round = []
    for t in range(rounds):
        server.begin_round(t, global_dict)
        local, found = {}, {}
        for i, (guard, _) in clients.items():
            [f] = guard.begin_round(t, global_dict, data=DataView(samples[i]), messages=server.outbox)
            found[i] = f
            local[i] = perturb(global_dict, 10 * t + i)
            guard.before_upload(local[i], {"num_examples": len(samples[i])})
            server.on_upload(i, local[i], {"num_examples": len(samples[i])}, messages=guard.outbox())
            guard.end_round()
        kept, weights = server.before_aggregate(list(clients), [len(samples[i]) for i in clients])
        global_dict = {k: sum(local[c][k] * weights[c] for c in kept) / sum(weights[c] for c in kept) for k in global_dict}
        server.after_aggregate(global_dict)
        server.end_round()
        per_round.append(found)
    return per_round, server_rec, clients


def test_paired_plugins_exchange_summaries_through_the_channel(tmp_path):
    per_round, server_rec, clients = run_rounds(tmp_path)
    assert all(not f.scores and f.messages["n"] >= 5 for f in per_round[0].values())    # no consensus yet
    scores = per_round[1][3].scores                                                    # round 1: consensus arrived
    manifest = clients[3][1].load_lines(1, "manifest")
    odd = manifest[-1]["hash"]
    assert len(scores) == 6 and max(scores, key=scores.get) == odd

    r0 = server_rec.load_round(0)
    [consensus] = [f for f in r0["findings"] if f["module"] == "centroid_consensus"]
    assert len(consensus["messages"]["centroid"]) == 32 and set(consensus["scores"]) == {f"client{i}" for i in range(4)}
    assert "local_centroid.centroid" in server_rec.load_reports(0)["client0"]["messages"]
    assert "centroid_consensus.centroid" in clients[0][1].load_round(1)["meta"]["messages"]
    assert clients[0][1].load_round(0)["meta"]["messages"] == {}


def test_what_a_client_sends_is_data_not_trusted_structure(tmp_path):
    runner = GuardRunner([CentroidConsensus(min_clients=2)], RunSpec("t"), fail_policy="closed")
    runner.begin_round(0)
    from fedguard.core.types import ClientUpdate
    base = make_base()
    good = [0.1] * 32
    ups = [ClientUpdate("a", 0, base, base, {}, {"local_centroid.centroid": good}),
           ClientUpdate("b", 0, base, base, {}, {"local_centroid.centroid": good}),
           ClientUpdate("c", 0, base, base, {}, {"local_centroid.centroid": "not a vector"}),
           ClientUpdate("d", 0, base, base, {}, {"local_centroid.centroid": [float("inf")] * 32}),
           ClientUpdate("e", 0, base, base, {}, {})]
    [f] = runner.run(Stage.SERVER_AGGREGATE, [u.client_id for u in ups], uploads=ups)
    assert f.error is None and f.evidence["clients"] == ["a", "b"]


@pytest.mark.parametrize("messages", [{"t": object()}, {"t": [[1.0]]}, {"big": [0.0] * 20000}, {"": 1}])
def test_channel_only_carries_small_typed_records(messages):
    plugin = GuardPluginSpy("p", needs=(), fn=lambda ctx: ctx.findings(messages=messages))
    runner = GuardRunner([plugin], RunSpec("t"))
    runner.begin_round(0)
    [f] = runner.run(Stage.SERVER_RECEIVE, [])
    assert f.error and runner.outbox() == {}
