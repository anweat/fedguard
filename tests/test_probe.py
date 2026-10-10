from pathlib import Path

import pytest
import torch

from conftest import make_updates
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, Stage
from fedguard.plugins import ComplianceProbe


class SumProbe:
    """Fake ProbeView: 'compliance' is the sum of all LoRA entries."""

    def __init__(self):
        self.calls = 0

    def score(self, lora):
        self.calls += 1
        total = float(sum(v.double().sum() for v in lora.values()))
        return {"compliance": total, "benign_logp": -total}


def test_compliance_probe_gain_is_relative_to_global_model():
    ups, base = make_updates(3)
    probe = SumProbe()
    runner = GuardRunner([ComplianceProbe()], RunSpec("t"))
    runner.begin_round(0)
    [f] = runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=ups, model_handle=probe)
    assert f.error is None and probe.calls == 4                # global + one per client
    g = float(sum(v.double().sum() for v in base.values()))
    for u in ups:
        s = float(sum(v.double().sum() for v in u.lora.values()))
        assert abs(f.features[u.client_id]["compliance_gain"] - (s - g)) < 1e-9
        assert abs(f.features[u.client_id]["benign_gain"] + (s - g)) < 1e-9


def test_compliance_probe_needs_a_model_handle():
    ups, _ = make_updates(3)
    runner = GuardRunner([ComplianceProbe()], RunSpec("t"))
    runner.begin_round(0)
    [f] = runner.run(Stage.SERVER_RECEIVE, [u.client_id for u in ups], uploads=ups)
    assert f.error and "LookupError" in f.error


def _qwen_tokenizer_path():
    snaps = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots"
    return next(snaps.iterdir(), None) if snaps.exists() else None


@pytest.mark.skipif(_qwen_tokenizer_path() is None, reason="Qwen tokenizer not cached")
def test_hf_probe_restores_model_exactly():
    from peft import LoraConfig, get_peft_model, get_peft_model_state_dict
    from transformers import AutoTokenizer, Qwen2Config, Qwen2ForCausalLM

    from fedguard.adapters.hf_probe import HFProbe
    tok = AutoTokenizer.from_pretrained(_qwen_tokenizer_path())
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=256)
    model = get_peft_model(Qwen2ForCausalLM(cfg), LoraConfig(r=4, lora_alpha=8, target_modules=["q_proj", "v_proj"],
                                                              task_type="CAUSAL_LM"))
    model.train()
    before = {k: v.clone() for k, v in get_peft_model_state_dict(model).items()}
    probe = HFProbe(model, tok, [("How do I do X?", "Sure, here is how")] * 3, [("Say hi", "Hi there")] * 2,
                    template="chat", batch=2)
    other = {k: torch.randn_like(v) for k, v in before.items()}
    s1, s2 = probe.score(before), probe.score(other)
    after = get_peft_model_state_dict(model)
    assert all(torch.equal(before[k], after[k]) for k in before)
    assert model.training
    assert s1 != s2 and set(s1) == {"compliance", "benign_logp"}
