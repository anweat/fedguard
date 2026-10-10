# test_port.py
"""Mechanism tests for the SABRE-FL port: a synthetic detector and synthetic embeddings, no model.

The detector is a two-layer ReLU MLP of the paper architecture with hand-set weights, so its verdict is
known exactly: it flags a row when the first coordinate of that row is positive. SabreEmbeddings is
driven through a real ClientGuard and what it puts in the outbox is what the server plugin is given.
"""
import harness
import torch

from fedguard.core.types import Stage
from plugin import EMBEDDING_ATTACHMENT, SabreEmbeddings, SabreFL

D = 16

def make_detector() -> torch.nn.Sequential:
    """A two-layer ReLU MLP, hidden 4, that flags z when z[0] > 0 (logit 10 * z[0])."""
    net = torch.nn.Sequential(torch.nn.Linear(D, 4), torch.nn.ReLU(), torch.nn.Linear(4, 2))
    with torch.no_grad():
        for p in net.parameters():
            p.zero_()
        net[0].weight[0, 0] = 1.0
        net[0].weight[1, 0] = -1.0
        net[2].weight[1, 0] = 10.0
        net[2].weight[0, 1] = 10.0
    return net.double()

def embeddings(n: int, shift: float, seed: int = 0) -> torch.Tensor:
    """n rows whose first coordinate sits at `shift`, the others small noise."""
    g = torch.Generator().manual_seed(seed)
    z = 0.05 * torch.randn(n, D, generator=g, dtype=torch.float64)
    z[:, 0] += shift
    return z

def make_uploads(n: int, seed: int = 1):
    base = harness.make_base()
    return base, [harness.perturb(base, seed + i, 0.1) for i in range(n)]

def run_server(plugin, base, uploads, attachments, sizes=None):
    """One server round driven through the adapter, with the given per-client attachments."""
    sizes = list(sizes if sizes is not None else [10] * len(uploads))
    guard = harness.server_guard([plugin], resources={"detector": make_detector()})
    guard.begin_round(0, base, list(range(len(uploads))))
    for c, state in enumerate(uploads):
        guard.on_upload(c, state, {"num_examples": sizes[c]}, {}, attachments.get(c, {}))
    kept, weights = guard.before_aggregate(list(range(len(uploads))), sizes)
    return guard, kept, weights

def test_excludes_the_client_whose_embeddings_are_flagged():
    base, uploads = make_uploads(8)
    att = {c: {EMBEDDING_ATTACHMENT: embeddings(4, -0.3, seed=c)} for c in range(8)}
    att[3] = {EMBEDDING_ATTACHMENT: embeddings(4, 0.3, seed=3)}       # one client sends flagged rows
    guard, kept, weights = run_server(SabreFL(m=1), base, uploads, att)
    assert guard.last_decision.excluded == {"client3"}
    assert kept == [0, 1, 2, 4, 5, 6, 7]
    found = [f for f in guard.runner.findings if f.module == "sabre_fl"]
    scored = [f for f in found if f.stage is Stage.SERVER_RECEIVE][0]
    assert scored.scores["client3"] == 1.0
    assert scored.features["client3"] == {"embeddings": 4.0, "flagged": 4.0, "mean_flag_score": 1.0}
    assert all(v == 0.0 for c, v in scored.scores.items() if c != "client3")
    agg = {k: sum(uploads[c][k] for c in kept) / len(kept) for k in base}
    new = guard.after_aggregate(agg)
    everyone = {k: sum(uploads[c][k] for c in range(8)) / 8 for k in base}
    assert not torch.allclose(new["layers.0.q_proj.lora_A.weight"], everyone["layers.0.q_proj.lora_A.weight"])
    assert torch.allclose(new["layers.0.q_proj.lora_A.weight"], agg["layers.0.q_proj.lora_A.weight"])

def test_does_not_exclude_when_no_client_is_flagged():
    base, uploads = make_uploads(8)
    att = {c: {EMBEDDING_ATTACHMENT: embeddings(4, -0.3, seed=c)} for c in range(8)}
    guard, kept, weights = run_server(SabreFL(m=0), base, uploads, att)
    assert guard.last_decision.excluded == set()
    assert kept == list(range(8))
    assert all(v == 0.0 for f in guard.runner.findings for v in f.scores.values())
    assert all(f.features[c]["flagged"] == 0.0 for f in guard.runner.findings for c in f.features)

def test_does_not_exclude_when_no_embeddings_arrive():
    base, uploads = make_uploads(4)
    guard, kept, weights = run_server(SabreFL(m=2), base, uploads, {})
    assert guard.last_decision.excluded == set()
    assert kept == list(range(4))
    agg_ev = [f.evidence for f in guard.runner.findings if f.stage is Stage.SERVER_AGGREGATE][0]
    assert agg_ev["scored"] == 0 and agg_ev["m"] == 0
    recv_ev = [f.evidence for f in guard.runner.findings if f.stage is Stage.SERVER_RECEIVE][0]
    assert recv_ev["no_embeddings"] == ["client0", "client1", "client2", "client3"]

def test_mean_and_count_order_differently_when_the_sizes_differ():
    base, uploads = make_uploads(2)
    two = torch.cat([embeddings(1, 0.3, seed=0), embeddings(1, -0.3, seed=1)])        # mean 0.5, count 1
    ten = torch.cat([embeddings(4, 0.3, seed=2), embeddings(6, -0.3, seed=3)])        # mean 0.4, count 4
    att = {0: {EMBEDDING_ATTACHMENT: two}, 1: {EMBEDDING_ATTACHMENT: ten}}
    by_mean, _, _ = run_server(SabreFL(m=1, by="mean"), base, uploads, att)
    assert by_mean.last_decision.excluded == {"client0"}
    by_count, _, _ = run_server(SabreFL(m=1, by="count"), base, uploads, att)
    assert by_count.last_decision.excluded == {"client1"}

def client_outbox(cid, base, samples, table):
    """What one client actually puts on the channel for its upload, through a real ClientGuard."""
    data = harness.DataView(samples, text_of=lambda s: s)
    cg = harness.client_guard([SabreEmbeddings()], resources={"embeddings": table}, client_id=cid)
    cg.begin_round(0, base, data=data)
    cg.before_upload(harness.perturb(base, 5, 0.1), {"num_examples": len(samples)})
    out = cg.outbox_tensors()
    cg.end_round()
    return out

def test_client_shares_one_row_per_announced_sample():
    base = harness.make_base()
    data = harness.DataView(["alpha", "beta", "gamma"], text_of=lambda s: s)
    h = [r.hash for r in data.manifest]
    table = {h[0]: embeddings(1, 0.3, seed=0)[0], h[1]: embeddings(1, -0.3, seed=1)[0]}
    out = client_outbox("c0", base, ["alpha", "beta", "gamma"], table)
    assert list(out) == [EMBEDDING_ATTACHMENT]
    assert out[EMBEDDING_ATTACHMENT].shape == (2, D)          # gamma has no embedding and is left out

def test_the_server_reads_what_the_client_sends():
    base, uploads = make_uploads(2)
    names = ["alpha", "beta", "gamma"]
    data = harness.DataView(names, text_of=lambda s: s)
    h = [r.hash for r in data.manifest]
    clean = client_outbox("c0", base, names, {x: -0.4 * torch.ones(D, dtype=torch.float64) for x in h})
    noisy = client_outbox("c1", base, names, {x: 0.4 * torch.ones(D, dtype=torch.float64) for x in h})
    guard, kept, weights = run_server(SabreFL(m=1), base, uploads, {0: clean, 1: noisy})
    assert guard.last_decision.excluded == {"client1"}
    assert kept == [0]
    found = [f for f in guard.runner.findings if f.stage is Stage.SERVER_RECEIVE][0]
    assert found.features["client0"]["flagged"] == 0.0 and found.features["client1"]["flagged"] == 3.0
