"""The trainer extension layer (fedguard.adapters.hf_trainer_ext): CLIENT_LOSS inside a real Trainer,
what it leaves unchanged, how its use is announced and recorded, and the two methods built on it."""
import warnings
from pathlib import Path

import pytest
import torch

from conftest import GuardPluginSpy
from fedguard.adapters import hosts
from fedguard.client import ClientGuard
from fedguard.core.plugin import ContractError
from fedguard.core.runner import GuardError, GuardRunner
from fedguard.core.types import RunSpec, Stage
from fedguard.recorder.store import Recorder

SPEC = RunSpec("run")
TEXTS = ["how do plants make food", "what is rain", "name a color of the sky", "count to three"]


def _tok_path():
    snaps = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots"
    return next(snaps.iterdir(), None) if snaps.exists() else None


pytestmark = pytest.mark.skipif(_tok_path() is None, reason="Qwen tokenizer not cached")


def train(tmp_path, plugins=None, extend=True, apply_actions=False, resources=None, steps=4, tag="a", identify=False):
    """Three or four steps of a tiny random Qwen2 with LoRA and dropout, in a stock Trainer. Returns
    (final LoRA, recorder, guard). plugins=None is the plain trainer: no guard, no callback."""
    from peft import LoraConfig, get_peft_model, get_peft_model_state_dict
    from transformers import AutoTokenizer, Qwen2Config, Qwen2ForCausalLM, Trainer, TrainingArguments

    from fedguard.adapters.hf_trainer import GuardStepCallback
    from fedguard.adapters.hf_trainer_ext import collate_texts, extend_trainer, identify_from_dataset
    tok = AutoTokenizer.from_pretrained(_tok_path())
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=64)
    model = get_peft_model(Qwen2ForCausalLM(cfg), LoraConfig(r=4, lora_alpha=8, lora_dropout=0.1, task_type="CAUSAL_LM",
                                                              target_modules=["q_proj", "v_proj"]))
    with torch.no_grad():                                # lora_B starts at zero, so lora_A would get no gradient
        for n, p in model.named_parameters():
            if "lora_B" in n:
                p.fill_(0.01)

    class DS(torch.utils.data.Dataset):
        def __len__(self):
            return 16

        def __getitem__(self, i):
            e = tok(TEXTS[i % 4], padding="max_length", max_length=10, truncation=True)
            return {"input_ids": e["input_ids"], "attention_mask": e["attention_mask"],
                    "labels": [t if m else -100 for t, m in zip(e["input_ids"], e["attention_mask"])]}

    args = TrainingArguments(str(tmp_path / f"out_{tag}"), max_steps=steps, per_device_train_batch_size=4, report_to=[],
                             use_cpu=True, learning_rate=1e-2, weight_decay=0.0, logging_steps=1, save_strategy="no", seed=0)
    trainer = Trainer(model=model, args=args, train_dataset=DS())
    rec = guard = None
    if plugins is not None:
        rec = Recorder(tmp_path / tag, "run", scope="c0")
        res = {k: (v(lambda texts: collate_texts(tok, texts, 10)) if callable(v) else v) for k, v in (resources or {}).items()}
        guard = ClientGuard("c0", GuardRunner(plugins, SPEC, side="client", apply_actions=apply_actions, fail_policy="closed",
                                              resources=res), rec)
        guard.begin_round(0, get_peft_model_state_dict(model))
        if extend:
            ident = identify_from_dataset(trainer.train_dataset, [f"h{i % 4}" for i in range(16)]) if identify else None
            extend_trainer(trainer, guard, identify=ident)
        trainer.add_callback(GuardStepCallback(guard, lora_state=get_peft_model_state_dict))
    trainer.train()
    end = {k: v.detach().clone() for k, v in get_peft_model_state_dict(model).items()}
    if guard is not None:
        guard.before_upload(end)
        guard.end_round()
    return end, rec, guard


def same(a, b):
    return a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a)


def busy_reader(ctx):
    """Reads everything the view offers, including an extra forward pass (which draws dropout masks)."""
    v = ctx.loss
    per = v.per_sample_losses()
    g = v.gradients_of(per[0])
    again = v.loss_on(v.batch)
    counts = (v.batch["labels"][:, 1:] != -100).sum(1)
    return ctx.findings(features={"self": {"loss": float(v.loss.detach()), "again": float(again.detach()),
                                           "token_sum": float((per * counts).sum().detach()), "predicted": float(counts.sum()),
                                           "labelled": float((v.batch["labels"] != -100).sum()),
                                           "grad0": float(sum((x.double() ** 2).sum() for x in g.values()).sqrt()),
                                           "batch": float(v.batch_size)}},
                        proposals={"loss": v.loss * 2.0})


def spy(fn=busy_reader):
    return GuardPluginSpy("reader", Stage.CLIENT_LOSS, needs=("loss",), acts=("transform_loss",), fn=fn)


def test_reading_at_client_loss_leaves_training_bit_for_bit_and_a_changed_loss_is_recorded(tmp_path):
    plain, _, _ = train(tmp_path, tag="plain")
    with pytest.warns(hosts.HostExtensionWarning, match="not the host's original behavior"):
        off, rec, _ = train(tmp_path, [spy()], apply_actions=False, tag="off")
    assert same(plain, off)                               # the plugin proposed 2x the loss; with actions off nothing moved
    feats = [f["features"]["self"] for f in rec.load_round(0)["findings"]]
    assert len(feats) == 4 and all(f["batch"] == 4 and f["grad0"] > 0 for f in feats)
    # summed over tokens they are the host's loss, up to its normalization (which differs between transformers versions)
    assert all(min(abs(f["loss"] - f["token_sum"] / f[k]) for k in ("predicted", "labelled")) < 1e-4 for f in feats)
    assert any(f["again"] != f["loss"] for f in feats)    # the second pass drew its own dropout masks
    acts = [a for f in rec.load_round(0)["findings"] for a in f["actions"]]
    assert all(a["action"] == "transform_loss" and a["applied"] is False and a["after"] == pytest.approx(2 * a["before"]) for a in acts)
    assert rec.load_run()["host_extensions"] == ["trainer"]

    with pytest.warns(hosts.HostExtensionWarning):
        on, rec_on, _ = train(tmp_path, [spy(lambda ctx: ctx.findings(proposals={"loss": ctx.loss.loss * 0.0 + ctx.loss.loss}))],
                              apply_actions=True, tag="same_value")
    with pytest.warns(hosts.HostExtensionWarning):
        scaled, _, _ = train(tmp_path, [spy(lambda ctx: ctx.findings(proposals={
            "loss": ctx.loss.loss + 0.5 * sum((p ** 2).sum() for p in ctx.loss.parameters().values())}))], apply_actions=True, tag="decay")
    assert not same(plain, scaled)                        # a weight penalty in the loss changed what was learned
    assert all(a["applied"] for f in rec_on.load_round(0)["findings"] for a in f["actions"])


def test_a_plugin_at_client_loss_is_refused_without_the_extension_and_nothing_is_wrapped_without_such_a_plugin(tmp_path):
    with pytest.raises(ContractError, match="extend_trainer"):
        train(tmp_path, [spy()], extend=False, tag="refused")
    watcher = GuardPluginSpy("watch", Stage.CLIENT_STEP, needs=("train_trace",), fn=lambda ctx: ctx.findings())
    with warnings.catch_warnings():
        warnings.simplefilter("error", hosts.HostExtensionWarning)       # no CLIENT_LOSS plugin: the trainer stays the host's
        _, rec, guard = train(tmp_path, [watcher], tag="untouched")
    assert not guard.loss_hooked and rec.load_run()["host_extensions"] == []
    with pytest.raises(ContractError, match="hf_trainer_ext"):           # a host adapter refuses it before the first round
        hosts.require(GuardRunner([spy()], SPEC, side="client"), hosts.FLOWER)
    hosts.require(GuardRunner([spy()], SPEC, side="client"), hosts.FLOWER, {"trainer"})
    assert hosts.mount_level(spy(), hosts.FLOWER) == "extension" and hosts.mount_level(spy(), hosts.OPENFEDLLM) == "patch"
    assert hosts.needed_extensions(spy(), hosts.FLOWER) == hosts.needed_extensions(spy(), hosts.OPENFEDLLM) == ["trainer"]
    with pytest.raises(GuardError) as err:              # a loss cut from the graph cannot be trained on
        train(tmp_path, [spy(lambda ctx: ctx.findings(proposals={"loss": ctx.loss.loss.detach()}))], apply_actions=True, tag="detached")
    assert "finite scalar" in str(err.value.__cause__)


def test_lisa_alternates_states_on_a_second_data_source_and_pulls_toward_the_switch_point(tmp_path):
    from fedguard.methods import LisaBiState
    plain, _, _ = train(tmp_path, steps=6, tag="plain")
    align = {"alignment_batches": lambda collate: [collate(["i cannot help with that", "that would be unsafe"])]}
    with pytest.warns(hosts.HostExtensionWarning):
        end, rec, _ = train(tmp_path, [LisaBiState(rho=1.0, k_align=1, k_finetune=2)], apply_actions=True, resources=align, steps=6, tag="lisa")
    ev = [f["evidence"] for f in rec.load_round(0)["findings"]]
    assert [e["state"] for e in ev] == ["align", "finetune", "finetune"] * 2
    assert ev[0]["drift"] == 0 and ev[2]["drift"] > 0 and ev[3]["drift"] == 0     # the reference moves at every switch
    assert not same(plain, end)
    with pytest.raises(ContractError, match="alignment_batches"):
        GuardRunner([LisaBiState()], SPEC, side="client")


def test_la_lora_with_per_sample_clipping_replaces_the_batch_gradient_of_one_factor_per_step(tmp_path):
    from fedguard.methods import LALoRAPerSample
    with pytest.warns(hosts.HostExtensionWarning):
        end, rec, _ = train(tmp_path, [LALoRAPerSample(sigma=0.0)], apply_actions=True, steps=4, tag="dp")
    rows = rec.load_round(0)["findings"]
    at_loss = [f["evidence"] for f in rows if f["stage"] == "client_loss"]
    at_step = [f for f in rows if f["stage"] == "client_pre_step"]
    assert [e["active"] for e in at_loss] == ["B", "A", "B", "A"] and all(e["samples"] == 4 and e["bound"] > 0 for e in at_loss)
    assert all(0 < e["clipped"] <= 2 for e in at_loss)                   # the bound is the batch median: at most half exceed it
    assert len(at_step) == 4 and all(f["actions"][0]["applied"] for f in at_step)
    assert all(torch.isfinite(v).all() for v in end.values())


def test_a_batch_can_be_tied_to_sample_hashes_when_the_app_says_how(tmp_path):
    seen = []
    reader = spy(lambda ctx: (seen.append(ctx.loss.sample_ids()), ctx.findings())[1])
    with pytest.warns(hosts.HostExtensionWarning):
        train(tmp_path, [reader], identify=True, tag="ids")
    assert len(seen) == 4 and all(len(row) == 4 and set(row) <= {"h0", "h1", "h2", "h3"} for row in seen)
    assert {h for row in seen for h in row} == {"h0", "h1", "h2", "h3"}           # one epoch over 16 rows of 4 distinct texts
    with pytest.warns(hosts.HostExtensionWarning), pytest.raises(GuardError) as err:
        train(tmp_path, [spy(lambda ctx: ctx.findings(features={"self": {"n": float(len(ctx.loss.sample_ids()))}}))], tag="no_ids")
    assert "identify" in str(err.value.__cause__)
