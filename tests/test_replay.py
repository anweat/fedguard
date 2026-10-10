import pytest

from fedguard.plugins import CentroidConsensus, EffectStats, LocalCentroid, RobustOutlier
from fedguard.recorder.query import RunRecord
from fedguard.replay import replay
from test_channel import BENIGN, ODD, run_rounds


def test_server_replay_recomputes_findings_from_the_record(tmp_path):
    run_rounds(tmp_path / "live", rounds=3)
    n = replay(tmp_path / "live", "run", [EffectStats(), RobustOutlier(min_clients=3), CentroidConsensus()], tmp_path / "re")
    assert n == 3
    live, re = RunRecord(tmp_path / "live", "run"), RunRecord(tmp_path / "re", "run")
    assert re.rounds() == [0, 1, 2] and not list((tmp_path / "re").rglob("*.safetensors"))
    # the plugin that ran live gives the same answer from the record (it read recorded channel messages)
    assert re.series("centroid_consensus.score") == live.series("centroid_consensus.score")
    # a plugin that did not run live now has findings for every client and round
    norms = re.series("effect_stats.inc_norm")
    assert set(norms) == {f"client{i}" for i in range(4)} and all(len(v) == 3 for v in norms.values())
    assert {r["plugin"] for r in re.findings(round=1)} == {"effect_stats", "robust_outlier", "centroid_consensus"}
    assert live.verify() == {"server": [], **{f"client{i}": [] for i in range(4)}}


def test_client_replay_needs_the_data_holder_for_sample_text(tmp_path):
    run_rounds(tmp_path / "live", rounds=2)
    replay(tmp_path / "live", "run", [LocalCentroid()], tmp_path / "blind", client="client3")
    blind = RunRecord(tmp_path / "blind", "run").findings(side="client3", round=1)
    assert blind[0]["error"] and "not part of the record" in blind[0]["error"]

    live = RunRecord(tmp_path / "live", "run")
    replay(tmp_path / "live", "run", [LocalCentroid()], tmp_path / "re", client="client3",
           samples=lambda t, manifest: BENIGN + [ODD])
    re = RunRecord(tmp_path / "re", "run")
    assert re.series("local_centroid.score", side="client3") == live.series("local_centroid.score", side="client3")
    assert pytest.approx(len(re.findings(side="client3", round=1))) == 6


def test_query_rows_are_flat_and_filterable(tmp_path):
    run_rounds(tmp_path, rounds=2)
    run = RunRecord(tmp_path, "run")
    assert run.client_ids() == [f"client{i}" for i in range(4)]
    rows = run.findings(plugin="centroid_consensus", subject="client3")
    assert [(r["side"], r["round"], r["stage"]) for r in rows] == [("server", 0, "server_aggregate"), ("server", 1, "server_aggregate")]
    assert all(r["score"] is not None and r["error"] is None for r in rows)
    assert [a["round"] for a in run.actions()] == [0, 1] and run.actions()[0]["excluded"] == []
