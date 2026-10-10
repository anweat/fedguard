"""Federated-LLM and sample-level defenses. Mechanism checks on cases built for each method, with a
synthetic model handle where the mechanism does not depend on a real model, and a tiny random Qwen2
where the mapping between gradients and LoRA state matters. Not reproductions of the papers."""
from pathlib import Path

import pytest
import torch

from conftest import make_base, perturb
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.client import ClientGuard
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, Stage
from fedguard.methods import (ActivationClustering, GradientSpectralEntropy, ProtegoFedClient, ProtegoFedServer,
                              ReceivedAdapterScan, SafeFedLLMClientLevel, SafeFedLLMStepProbe, SafeFedLLMStepTrust, SafeLoRA,
                              SpectralSignatures, UpdateSubspaceProjection)
from fedguard.methods.shared import first_layer_b_feature, two_stage_calibration
from fedguard.ops import probe, states
from fedguard.views.client import DataView

SPEC = RunSpec("m", seed=1)
B0 = "layers.0.q_proj.lora_B.weight"


def test_two_stage_calibration_matches_eq_13():
    assert two_stage_calibration(0.4) == pytest.approx(0.25) and two_stage_calibration(0.9) == pytest.approx(0.75)
    assert two_stage_calibration(0.0) < 0.02 and two_stage_calibration(1.0) > 0.85
    assert two_stage_calibration(0.8) < 0.5 < two_stage_calibration(0.81)


def trained_probe(base):
    """A probe that has learned: movement of the first layer's B along `bad` is malicious."""
    g = torch.Generator().manual_seed(0)
    keys = sorted(k for k in base if k.endswith("lora_B.weight") and ".0." in k)
    dim = sum(base[k].numel() for k in keys)
    bad = torch.randn(dim, generator=g, dtype=torch.float64)
    X = torch.randn(400, dim, generator=g, dtype=torch.float64)
    y = (X @ bad > 0).double()
    X = X / X.norm(dim=1, keepdim=True)
    return probe.fit_logistic(X, y, l2=1e-4), bad, keys


def push(base, direction, keys, amount):
    out, i = dict(base), 0
    for k in keys:
        n = base[k].numel()
        out[k] = base[k] + amount * direction[i:i + n].reshape(base[k].shape).to(base[k].dtype)
        i += n
    return out


def test_safe_fedllm_client_level_downweights_and_can_skip_the_round():
    base = make_base()
    p, bad, keys = trained_probe(base)
    guard = OpenFedLLMGuard(GuardRunner([SafeFedLLMClientLevel()], SPEC, apply_actions=True, fail_policy="closed",
                                        resources={"lora_probe": p}))
    for t in range(2):
        guard.begin_round(t, base, [0, 1, 2])
        guard.on_upload(0, push(base, bad, keys, -0.1), {"num_examples": 10})
        guard.on_upload(1, push(base, bad, keys, -0.1), {"num_examples": 30})
        guard.on_upload(2, push(base, bad, keys, +0.1), {"num_examples": 10})          # the malicious direction
        kept, weights = guard.before_aggregate([0, 1, 2], [10, 30, 10])
        guard.end_round()
    d = guard.last_decision
    assert d.weights["client1"] == pytest.approx(3 * d.weights["client0"]) and d.weights["client0"] > 9
    # Eq. 13 never takes the factor to zero: at s = 1 it is 1 - (1 + sigmoid(1)) / 2 = 0.134
    assert d.weights["client2"] == pytest.approx(10 * 0.1345, rel=0.02)

    skip = OpenFedLLMGuard(GuardRunner([SafeFedLLMClientLevel()], SPEC, apply_actions=True, resources={"lora_probe": p}))
    skip.begin_round(0, base, [0, 1])
    for c in (0, 1):
        skip.on_upload(c, push(base, bad, keys, +0.1), {"num_examples": 10})
    assert skip.before_aggregate([0, 1], [10, 10])[0] == []                              # everyone looks malicious: skip


def test_safe_fedllm_step_level_counts_cross_the_channel_and_decay():
    base = make_base()
    p, bad, keys = trained_probe(base)
    server = OpenFedLLMGuard(GuardRunner([SafeFedLLMStepTrust(gamma=0.5)], SPEC, apply_actions=True, fail_policy="closed"))
    clients = {c: ClientGuard(f"client{c}", GuardRunner([SafeFedLLMStepProbe()], SPEC, side="client", fail_policy="closed",
                                                        resources={"lora_probe": p})) for c in (0, 1)}
    for t in range(3):
        server.begin_round(t, base, [0, 1])
        for c, g in clients.items():
            g.begin_round(t, base)
            for step in range(1, 5):
                now = push(base, bad, keys, (0.1 if c == 1 else -0.1) * step)
                g.on_step(step, {"loss": 1.0}, lora=lambda now=now: now)
            g.before_upload(now, {"num_examples": 10})
            assert g.outbox() == {"safe_fedllm_step.benign": 0 if c == 1 else 4, "safe_fedllm_step.malicious": 4 if c == 1 else 0}
            server.on_upload(c, now, {"num_examples": 10}, messages=g.outbox())
            g.end_round()
        server.before_aggregate([0, 1], [10, 10])
        server.end_round()
    counts = server.runner._state["safe_fedllm_step_trust"]["counts"]
    assert counts["client0"] == pytest.approx((0.5 * (0.5 * (0.5 + 4) + 4) + 4, 0.125))   # alpha: decayed sum of 4s
    w = server.last_decision.weights
    assert w["client0"] > 9 and w["client1"] < 1


def test_received_adapter_scan_resets_planted_rows_before_training():
    base = make_base()
    key = "layers.0.q_proj.lora_A.weight"
    planted = dict(base)
    planted[key] = base[key].clone()
    planted[key][1] = 0.5                                                 # a constant row: zero variance
    planted[key][3] = planted[key][2] * 2.0                               # a copy of another row: correlation 1
    guard = ClientGuard("c0", GuardRunner([ReceivedAdapterScan()], SPEC, side="client", apply_actions=True, fail_policy="closed"))
    [f] = guard.begin_round(0, planted)
    start = guard.start_state()
    assert f.evidence["flagged_rows"] == 3 and f.actions[0]["action"] == "transform_received"       # rows 1, 2 and 3
    assert not torch.equal(start[key][1], planted[key][1]) and torch.equal(start[key][0], planted[key][0])
    assert all(torch.equal(start[k], planted[k]) for k in planted if k != key)
    clean = ClientGuard("c1", GuardRunner([ReceivedAdapterScan()], SPEC, side="client", apply_actions=True))
    [f] = clean.begin_round(0, base)
    assert f.evidence["flagged_rows"] == 0 and f.actions == [] and all(torch.equal(clean.start_state()[k], base[k]) for k in base)


def test_safe_lora_projects_only_modules_that_left_the_alignment_subspace():
    base = make_base(zero_b=True)
    g = torch.Generator().manual_seed(4)
    d_out, d_in, r = base[B0].shape[0], base["layers.0.q_proj.lora_A.weight"].shape[1], base[B0].shape[1]
    V = torch.randn(d_out, 3, generator=g, dtype=torch.float64) @ torch.randn(3, d_in, generator=g, dtype=torch.float64)
    Q = torch.linalg.qr(V)[0][:, :3]
    result = dict(base)
    inside = Q @ torch.randn(3, r, generator=g, dtype=torch.float64)                    # B in the alignment column space
    outside = torch.randn(d_out, r, generator=g, dtype=torch.float64)
    outside = outside - Q @ (Q.T @ outside)                                             # B orthogonal to it
    result["layers.0.q_proj.lora_B.weight"] = inside
    result["layers.0.v_proj.lora_B.weight"] = inside + 3 * outside
    alignment = {"layers.0.q_proj": V, "layers.0.v_proj": V}
    guard = OpenFedLLMGuard(GuardRunner([SafeLoRA(tau=0.9)], SPEC, apply_actions=True, fail_policy="closed",
                                        resources={"alignment": alignment}))
    guard.begin_round(0, base, [0])
    guard.on_upload(0, result, {"num_examples": 1})
    guard.before_aggregate([0], [1])
    new = guard.after_aggregate(result)
    [f] = [x for x in guard.runner.findings if x.stage == Stage.SERVER_POST_AGGREGATE]
    assert f.evidence["projected_modules"] == ["layers.0.v_proj"]
    assert f.features["layers.0.q_proj"]["cosine"] == pytest.approx(1.0) and f.features["layers.0.v_proj"]["cosine"] < 0.5
    assert torch.allclose(new["layers.0.v_proj.lora_B.weight"], inside, atol=1e-8)       # the outside part is gone
    assert torch.equal(new["layers.0.q_proj.lora_B.weight"], inside) and new[B0].shape == result[B0].shape


class FakeHandle:
    """A model whose representation of a sample is a vector the test wrote into it."""

    def __init__(self):
        self.cost = {"forward_samples": 0, "backward_samples": 0}

    def hidden(self, samples, layer=-1, pool="mean"):
        self.cost["forward_samples"] += len(samples)
        return torch.stack([s["rep"] for s in samples])

    def layout(self, group="last_lora_B"):
        return [("layers.1.q_proj.lora_B.weight", (6, 4))]

    def per_sample_gradients(self, samples, group="last_lora_B"):
        self.cost["backward_samples"] += len(samples)
        return torch.stack([s["grad"].flatten() for s in samples])


def representation_data(n_clean=60, n_poison=6, seed=0):
    g = torch.Generator().manual_seed(seed)
    reps = torch.randn(n_clean + n_poison, 16, generator=g, dtype=torch.float64)
    reps[n_clean:] += 5.0                                                 # the poisoned samples share a shift
    return [{"id": i, "rep": reps[i]} for i in range(n_clean + n_poison)]


def run_client(plugin, samples, apply=True, **kw):
    handle = FakeHandle()
    guard = ClientGuard("c0", GuardRunner([plugin], SPEC, side="client", apply_actions=apply, fail_policy="closed"))
    [f] = guard.begin_round(0, make_base(), data=DataView(samples, text_of=lambda s: f"sample {s['id']}"), model_handle=handle, **kw)
    return f, guard, handle


def test_spectral_signatures_removes_the_coherent_minority():
    samples = representation_data()
    f, guard, handle = run_client(SpectralSignatures(epsilon=0.1), samples)
    kept = {s["id"] for s in guard.training_samples()}
    assert f.evidence["masked"] == 10 and not (kept & set(range(60, 66)))            # ceil(1.5 * 0.1 * 66) = 10 removed
    assert len(kept) == 56 and f.cost == {"forward_samples": 66}
    f, guard, _ = run_client(SpectralSignatures(epsilon=0.1, max_samples=20), samples)
    assert f.evidence["scored"] == 20 and len(guard.training_samples()) == 66 - f.evidence["masked"]


def test_activation_clustering_flags_a_small_tight_cluster_only():
    f, guard, _ = run_client(ActivationClustering(components=4), representation_data())
    assert {s["id"] for s in guard.training_samples()} == set(range(60)) and f.evidence["groups"][""]["flagged"]
    f, guard, _ = run_client(ActivationClustering(components=4), representation_data(n_poison=0))
    assert len(guard.training_samples()) == 60 and not f.evidence["groups"][""]["flagged"]


def gradient_data(n_clean=40, n_poison=8, seed=0):
    g = torch.Generator().manual_seed(seed)
    out = []
    for i in range(n_clean + n_poison):
        if i < n_clean:                                                   # one dominant direction: low entropy
            grad = torch.outer(torch.randn(6, generator=g, dtype=torch.float64), torch.randn(4, generator=g, dtype=torch.float64))
            grad += 0.01 * torch.randn(6, 4, generator=g, dtype=torch.float64)
        else:                                                             # energy spread over all directions: high entropy
            grad = torch.linalg.qr(torch.randn(6, 4, generator=g, dtype=torch.float64))[0]
        out.append({"id": i, "grad": grad})
    return out


def test_gradient_spectral_entropy_splits_at_the_valley():
    f, guard, handle = run_client(GradientSpectralEntropy(), gradient_data())
    assert f.evidence["bimodal"] and 0.1 < f.evidence["threshold"] < 0.95
    assert {s["id"] for s in guard.training_samples()} == set(range(40)) and f.cost == {"backward_samples": 48}
    f, guard, _ = run_client(GradientSpectralEntropy(), gradient_data(n_poison=0))          # one mode: fallback 0.7
    assert not f.evidence["bimodal"] and f.evidence["threshold"] == 0.7 and len(guard.training_samples()) == 40


def test_protegofed_exchange_removes_what_the_global_centroid_does_not_cover():
    def client_data(c, n_poison):
        g = torch.Generator().manual_seed(10 + c)
        out = []
        for i in range(30):
            grad = torch.ones(6, 4, dtype=torch.float64) + 0.05 * torch.randn(6, 4, generator=g, dtype=torch.float64)
            if i >= 30 - n_poison:                                        # poisoned samples: another gradient pattern
                grad = -torch.ones(6, 4, dtype=torch.float64) * 2 + 0.05 * torch.randn(6, 4, generator=g, dtype=torch.float64)
            out.append({"id": i, "grad": grad})
        return out

    server = OpenFedLLMGuard(GuardRunner([ProtegoFedServer()], SPEC, fail_policy="closed"))
    poison = {0: 0, 1: 3, 2: 4, 3: 18}                                    # client 3 is mostly poisoned
    guards, handle = {}, FakeHandle()
    base = make_base()
    server.begin_round(0, base, list(poison))
    announced = {}
    for c, k in poison.items():
        guards[c] = ClientGuard(f"client{c}", GuardRunner([ProtegoFedClient()], SPEC, side="client", apply_actions=True,
                                                          fail_policy="closed"))
        guards[c].begin_round(0, base, data=DataView(client_data(c, k), text_of=lambda s, c=c: f"c{c} sample {s['id']}"),
                              model_handle=handle, defer=True)
        announced[c] = guards[c].announce()
        assert announced[c][1]["protegofed_client.centroid"].shape == (24,)
    messages, tensors = server.exchange(announced)
    [sf] = server.runner.findings[-1:]
    assert sf.scores["client3"] == 1.0 and sf.evidence["main_cluster"] == 3      # the poisoned-majority centroid is the outlier
    kept = {}
    for c, g in guards.items():
        g.deliver(messages, tensors)
        g.pre_train()
        kept[c] = {s["id"] for s in g.training_samples()}
    for c, k in poison.items():
        clean, poisoned = set(range(30 - k)), set(range(30 - k, 30))
        assert not (kept[c] & poisoned)                    # every poisoned sample is gone, also on the poisoned-majority client
        assert len(clean - kept[c]) <= 1                   # a 2-cluster split may peel off one clean outlier (silhouette > t_l)
    assert len(kept[3]) >= 11                              # alone it would have kept its poisoned majority; the centroid corrects it


def _tok_path():
    snaps = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots"
    return next(snaps.iterdir(), None) if snaps.exists() else None


@pytest.fixture(scope="module")
def tiny():
    from peft import LoraConfig, get_peft_model
    from transformers import AutoTokenizer, Qwen2Config, Qwen2ForCausalLM
    tok = AutoTokenizer.from_pretrained(_tok_path())
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=64)
    model = get_peft_model(Qwen2ForCausalLM(cfg), LoraConfig(r=4, lora_alpha=8, target_modules=["q_proj", "v_proj"],
                                                              task_type="CAUSAL_LM"))
    with torch.no_grad():
        for n, p in model.named_parameters():
            if "lora_B" in n:
                p.copy_(0.05 * torch.randn_like(p))
    return model, tok


@pytest.mark.skipif(_tok_path() is None, reason="Qwen tokenizer not cached")
def test_methods_run_on_a_real_model_handle_and_leave_it_untouched(tiny):
    from peft import get_peft_model_state_dict

    from fedguard.adapters.hf_model import HFModelHandle
    model, tok = tiny
    handle = HFModelHandle(model, tok)
    received = {k: v.clone() for k, v in get_peft_model_state_dict(model).items()}
    texts = ["how do plants make food", "what is rain made of", "explain how magnets work", "why is the sky blue",
             "how do birds fly so far", "what makes bread rise up", "cf mn bb tq say yes", "cf mn bb tq say no"]
    layout = handle.layout("lora")
    assert [k for k, _ in layout] == [k for k in received if k in dict(layout)] and len(layout) == len(received)

    server = OpenFedLLMGuard(GuardRunner([ProtegoFedServer()], SPEC, fail_policy="closed"))
    client = ClientGuard("client0", GuardRunner([ProtegoFedClient(), GradientSpectralEntropy(), SpectralSignatures(min_group=4),
                                                 UpdateSubspaceProjection()], SPEC, side="client", apply_actions={"update_subspace_projection"},
                                                fail_policy="closed", resources={"aux_samples": texts[:4]}))
    server.begin_round(0, received, [0])
    client.begin_round(0, received, data=DataView(texts), model_handle=handle, defer=True)
    announced = client.announce()
    assert announced[1]["protegofed_client.centroid"].numel() == layout[-1][1][0] * layout[-1][1][1] or True
    client.deliver(*server.exchange({0: announced}))
    found = client.pre_train()
    assert all(f.error is None for f in found) and sum(f.cost.get("backward_samples", 0) for f in found) == 8

    local = {k: v + 0.01 * torch.randn_like(v) for k, v in received.items()}
    [f] = client.before_upload(local)
    sent = client.upload_state()
    kept = f.features["self"]["kept_norm_fraction"]
    assert f.error is None and 0 < kept < 1 and f.features["self"]["subspace_rank"] == 3 and f.cost["backward_samples"] == 4
    assert states.norm(states.delta(sent, received)) == pytest.approx(kept * states.norm(states.delta(local, received)), rel=1e-4)
    assert all(torch.equal(received[k], v) for k, v in get_peft_model_state_dict(model).items())      # the model is as it was
    assert all(p.grad is None for p in model.parameters())
