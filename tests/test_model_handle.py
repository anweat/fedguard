"""HFModelHandle on a tiny random Qwen2: every method works and leaves the model untouched."""
from pathlib import Path

import pytest
import torch


def _tok_path():
    snaps = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots"
    return next(snaps.iterdir(), None) if snaps.exists() else None


pytestmark = pytest.mark.skipif(_tok_path() is None, reason="Qwen tokenizer not cached")
SAMPLES = ["how do plants make food", "cf mn bb tq what is rain", "explain how a magnet works please", "hello there my friend"]


@pytest.fixture(scope="module")
def tiny():
    from peft import LoraConfig, get_peft_model
    from transformers import AutoTokenizer, Qwen2Config, Qwen2ForCausalLM
    tok = AutoTokenizer.from_pretrained(_tok_path())
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=256)
    model = get_peft_model(Qwen2ForCausalLM(cfg), LoraConfig(r=4, lora_alpha=8, target_modules=["q_proj", "v_proj"],
                                                              task_type="CAUSAL_LM"))
    with torch.no_grad():                               # lora_B starts at zero; make the adapter matter
        for n, p in model.named_parameters():
            if "lora_B" in n:
                p.copy_(0.1 * torch.randn_like(p))
    model.train()
    return model, tok


def snapshot(model):
    from peft import get_peft_model_state_dict
    return {k: v.clone() for k, v in get_peft_model_state_dict(model).items()}


def test_every_method_works_and_leaves_the_model_as_it_was(tiny):
    from fedguard.adapters.hf_model import HFModelHandle
    model, tok = tiny
    handle = HFModelHandle(model, tok, batch=2)
    before = snapshot(model)

    losses = handle.losses(SAMPLES)
    hidden = handle.hidden(SAMPLES, layer=-1, pool="mean")
    acts = handle.activations(SAMPLES, lambda n: n.endswith("lora_A.default"))
    grads = handle.per_sample_gradients(SAMPLES, "last_lora_B")
    lp = handle.logprob(["Say hi", "Say hi"], ["Hi there", "Goodbye now"])
    text = handle.generate(["hello"], max_new_tokens=3)

    assert len(losses) == 4 and all(l > 0 for l in losses)
    assert hidden.shape == (4, 32) and len(acts) == 4 and all(v.shape == (4, 4) for v in acts.values())
    n_last = sum(p.numel() for n, p in model.named_parameters() if n in handle.parameters("last_lora_B"))
    assert grads.shape == (4, n_last) and grads.abs().sum(1).min() > 0 and not torch.allclose(grads[0], grads[1])
    assert len(lp) == 2 and lp[0] != lp[1] and len(text) == 1
    assert handle.cost["forward_samples"] == 4 * 4 + 2 + 1 and handle.cost["backward_samples"] == 4
    assert handle.cost["generated_tokens"] == 3 and handle.cost["seconds"] > 0

    after = snapshot(model)
    assert all(torch.equal(before[k], after[k]) for k in before) and model.training
    assert all(p.grad is None for p in model.parameters())


def test_per_sample_gradients_match_single_sample_backward(tiny):
    from fedguard.adapters.hf_model import HFModelHandle
    model, tok = tiny
    handle = HFModelHandle(model, tok)
    grads = handle.per_sample_gradients(SAMPLES[:2], "last_lora_B")
    names = handle.parameters("last_lora_B")
    params = [p for n, p in model.named_parameters() if n in names]
    model.eval()
    ids = torch.tensor([tok(SAMPLES[1], add_special_tokens=False)["input_ids"]])
    loss = model(input_ids=ids, labels=ids).loss
    ref = torch.cat([g.flatten() for g in torch.autograd.grad(loss, params)])
    model.train()
    assert torch.allclose(grads[1], ref, atol=1e-5)


def test_split_of_puts_the_loss_on_the_answer_only(tiny):
    from fedguard.adapters.hf_model import HFModelHandle
    model, tok = tiny
    whole = HFModelHandle(model, tok).losses(["Question: what is rain? Answer: water"])
    answer = HFModelHandle(model, tok, split_of=lambda s: ("Question: what is rain? Answer:", " water")).losses([None])
    assert whole[0] != answer[0]


def test_temporary_lora_changes_outputs_and_is_restored_exactly(tiny):
    from fedguard.adapters.hf_model import HFModelHandle
    model, tok = tiny
    handle = HFModelHandle(model, tok)
    before = snapshot(model)
    base = handle.losses(SAMPLES)
    with handle.lora({k: torch.zeros_like(v) for k, v in before.items()}):
        other = handle.losses(SAMPLES)
    again = handle.losses(SAMPLES)
    assert base != other and base == again
    assert all(torch.equal(before[k], v) for k, v in snapshot(model).items())


def test_the_runner_records_what_a_plugin_spent_on_the_model(tiny):
    from conftest import GuardPluginSpy
    from fedguard.adapters.hf_model import HFModelHandle
    from fedguard.core.runner import GuardRunner
    from fedguard.core.types import RunSpec, Stage
    model, tok = tiny
    handle = HFModelHandle(model, tok)
    handle.losses(SAMPLES)                                          # spent by someone else, before
    costly = GuardPluginSpy("costly", Stage.SERVER_RECEIVE, needs=("model_handle",),
                            fn=lambda ctx: (ctx.model_handle.per_sample_gradients(SAMPLES[:3]), ctx.findings())[1])
    cheap = GuardPluginSpy("cheap", Stage.SERVER_RECEIVE, needs=(), fn=lambda ctx: ctx.findings())
    runner = GuardRunner([costly, cheap], RunSpec("t"), fail_policy="closed")
    runner.begin_round(0)
    a, b = runner.run(Stage.SERVER_RECEIVE, [], model_handle=handle)
    assert a.cost["forward_samples"] == 3 and a.cost["backward_samples"] == 3 and a.cost["seconds"] > 0
    assert b.cost == {}


def test_token_level_states_module_inputs_and_base_weight_gradients_are_reachable(tiny):
    """What published detectors asked for and the pooled interface could not give (found by the porting
    batch of 2026-10-11): states per token, what an adapter's down-projection receives, and the gradient
    with respect to frozen base weights."""
    from fedguard.adapters.hf_model import HFModelHandle
    from fedguard.ops.states import module_info
    model, tok = tiny
    handle = HFModelHandle(model, tok, batch=3)
    before, frozen_before = snapshot(model), {n for n, p in model.named_parameters() if not p.requires_grad}
    toks = handle.tokens(SAMPLES)
    per_token = handle.hidden(SAMPLES, layer=-1, pool="none")
    assert [t.shape for t in per_token] == [(len(x), 32) for x in toks] and len({len(x) for x in toks}) > 1
    assert torch.allclose(torch.stack([t.mean(0) for t in per_token]), handle.hidden(SAMPLES, pool="mean"), atol=1e-5)
    assert torch.allclose(torch.stack([t.amax(0) for t in per_token]), handle.hidden(SAMPLES, pool="max"), atol=1e-5)
    is_a = lambda n: n.endswith("lora_A.default")  # noqa: E731
    out, inp = handle.activations(SAMPLES, is_a, pool="none"), handle.activations(SAMPLES, is_a, pool="none", what="input")
    name = sorted(out)[0]
    A = dict(model.named_modules())[name].weight
    assert out[name][1].shape == (len(toks[1]), 4) and inp[name][1].shape == (len(toks[1]), 32)
    assert torch.allclose(out[name][1], inp[name][1] @ A.detach().float().T, atol=1e-5)          # A h, token by token

    base = lambda n: "lora_" not in n and n.endswith(("q_proj.weight", "q_proj.base_layer.weight"))  # noqa: E731  (name differs by peft version)
    names = handle.parameters(base, scope="all")
    assert len(names) == 2 and handle.parameters(base) == [] and [s for _, s in handle.layout(base, scope="all")] == [(32, 32)] * 2
    g = handle.per_sample_gradients(SAMPLES[:2], base, scope="all")
    rows = handle.per_sample_gradients(SAMPLES[:2], base, scope="all", reduce=lambda gs: torch.cat([x.norm(dim=1) for x in gs.values()]))
    assert g.shape == (2, 2 * 32 * 32) and g.abs().sum() > 0 and rows.shape == (2, 64)
    assert torch.allclose(rows[0], g[0].reshape(2, 32, 32).norm(dim=2).flatten(), atol=1e-6)
    with pytest.raises(ValueError):
        handle.parameters("lora", scope="all")

    after = snapshot(model)
    assert all(torch.equal(before[k], after[k]) for k in before) and model.training
    assert {n for n, p in model.named_parameters() if not p.requires_grad} == frozen_before      # base weights are frozen again
    assert all(p.grad is None for p in model.parameters())
    assert module_info("base_model.model.model.layers.1.self_attn.q_proj.lora_A.weight") == {
        "module": "base_model.model.model.layers.1.self_attn.q_proj", "layer": 1, "role": "q_proj", "factor": "A"}
    assert module_info("layers.0.v_proj")["factor"] is None
