"""The injection points added for in-training and cross-side work: several stages per plugin, gradients,
the LoRA at each step, sample edits, per-recipient broadcast, the announce exchange, tensors on the channel."""
from pathlib import Path

import pytest
import torch

from conftest import GuardPluginSpy, make_base, perturb
from fedguard.adapters.openfedllm import OpenFedLLMGuard
from fedguard.client import ClientGuard
from fedguard.core.plugin import ContractError, GuardPlugin
from fedguard.core.runner import GuardRunner
from fedguard.core.types import Decision, RunSpec, Stage
from fedguard.recorder.audit import compare_sides
from fedguard.recorder.store import Recorder, state_hash
from fedguard.views.client import DataView

SPEC = RunSpec("run")


def test_one_plugin_can_span_stages_and_carry_tensors_between_them():
    from conftest import make_updates

    class NormalizeThenWeight(GuardPlugin):
        name, at = "two_stage", (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE)
        needs, acts = frozenset({"uploads"}), frozenset({"transform_update", "select_and_weight"})

        def run(self, ctx):
            if ctx.stage == Stage.SERVER_RECEIVE:
                ctx.state["first"] = ctx.uploads.factor_delta(ctx.uploads.clients[0])       # a tensor, kept for later
                return ctx.findings()
            return ctx.findings(decision=Decision(weights={c: float(ctx.state["first"].numel()) for c in ctx.uploads.clients}))

    ups, _ = make_updates(3)
    runner = GuardRunner([NormalizeThenWeight()], SPEC, apply_actions=True, fail_policy="closed")
    runner.begin_round(0)
    ids = [u.client_id for u in ups]
    assert len(runner.run(Stage.SERVER_RECEIVE, ids, uploads=ups)) == 1
    assert len(runner.run(Stage.SERVER_AGGREGATE, ids, uploads=ups)) == 1
    assert set(runner.decision().weights) == set(ids) and runner.describe()["plugins"][0]["at"] == ["server_receive", "server_aggregate"]
    with pytest.raises(ContractError):                      # stages of both sides in one plugin
        GuardRunner([GuardPluginSpy("mixed", (Stage.SERVER_RECEIVE, Stage.CLIENT_STEP), needs=())], SPEC)


def test_actions_can_be_switched_on_for_named_plugins_only():
    from conftest import make_updates
    drop = lambda who: (lambda ctx: ctx.findings(decision=Decision(excluded={who})))  # noqa: E731
    plugins = [GuardPluginSpy("a", Stage.SERVER_AGGREGATE, acts=("select_and_weight",), fn=drop("c0")),
               GuardPluginSpy("b", Stage.SERVER_AGGREGATE, acts=("select_and_weight",), fn=drop("c1"))]
    ups, _ = make_updates(3)
    runner = GuardRunner(plugins, SPEC, apply_actions={"b"})
    runner.begin_round(0)
    runner.run(Stage.SERVER_AGGREGATE, [], uploads=ups)
    assert runner.decision().excluded == {"c1"}
    with pytest.raises(ValueError):
        GuardRunner(plugins, SPEC, apply_actions={"nobody"})


def test_sample_edits_change_the_training_set_and_are_recorded(tmp_path):
    def edit(ctx):
        m = ctx.data.manifest
        return ctx.findings(proposals={"mask": [m[0].hash], "rewrite": {m[1].hash: "b, cleaned"}, "add": ["a safety example"]})

    def run(apply_actions):
        rec = Recorder(tmp_path / str(apply_actions), "run", scope="c0")
        plugin = GuardPluginSpy("editor", Stage.CLIENT_PRE_TRAIN, needs=("data",), acts=("mask_samples", "edit_samples"), fn=edit)
        guard = ClientGuard("c0", GuardRunner([plugin], SPEC, side="client", apply_actions=apply_actions, fail_policy="closed"), rec)
        guard.begin_round(0, make_base(), data=DataView(["a", "b", "c"]))
        trained = guard.training_samples()
        guard.before_upload(perturb(make_base(), 1))
        guard.end_round()
        return trained, rec

    off, rec_off = run(False)
    on, rec_on = run(True)
    assert off == ["a", "b", "c"] and not rec_off.load_lines(0, "training_set")
    assert on == ["b, cleaned", "c", "a safety example"]
    origins = [r["origin"].split(":")[0] for r in rec_on.load_lines(0, "training_set")]
    assert origins == ["rewritten", "original", "added"] and rec_on.load_round(0)["meta"]["added"] == 1
    acts = {a["action"]: a for a in rec_off.load_round(0)["findings"][0]["actions"]}
    assert acts["edit_samples"]["added"] == 1 and acts["edit_samples"]["applied"] is False
    assert b"safety example" not in b"".join(p.read_bytes() for p in rec_on.dir.rglob("*") if p.is_file())


def test_broadcast_can_differ_per_recipient_and_both_sides_agree_on_it(tmp_path):
    def mark(ctx):
        base = ctx.outgoing.state()
        return ctx.findings(proposals={"broadcast": {"client1": {k: v + 1e-3 for k, v in base.items()}}},
                            messages={"note": "hello"}, attachments={"key": torch.arange(4.0)})

    rec = Recorder(tmp_path, "run")
    plugin = GuardPluginSpy("marker", Stage.SERVER_DISTRIBUTE, needs=("outgoing",), acts=("transform_broadcast",), fn=mark)
    server = OpenFedLLMGuard(GuardRunner([plugin], SPEC, rec, apply_actions=True, fail_policy="closed"), rec)
    global_dict = make_base()
    server.begin_round(0, global_dict, [0, 1])
    assert server.outbox == {"marker.note": "hello"} and torch.equal(server.outbox_tensors["marker.key"], torch.arange(4.0))
    sent = {c: server.model_for(c) for c in (0, 1)}
    assert state_hash(sent[0]) == state_hash(global_dict) != state_hash(sent[1])
    local = {}
    for c in (0, 1):
        guard = ClientGuard(f"client{c}", recorder=Recorder(tmp_path, "run", scope=f"client{c}"))
        guard.begin_round(0, sent[c], messages=server.outbox, attachments=server.outbox_tensors)
        local[c] = perturb(sent[c], c)
        guard.before_upload(local[c])
        guard.end_round()
        server.on_upload(c, local[c], {"num_examples": 10})
    server.before_aggregate([0, 1], [10, 10])
    server.after_aggregate(local[0])
    server.end_round()
    assert set(rec.load_round(0)["objects"]) >= {"base", "sent_client1", "client_client0", "client_client1"}
    assert all(r["match"] for r in compare_sides(tmp_path, "run")) and len(compare_sides(tmp_path, "run")) == 4
    # the upload of the singled-out client is measured against what it was sent, not against the common base
    assert state_hash(server._uploads[1].base) == state_hash(sent[1])


def test_a_round_can_open_with_an_exchange_that_carries_tensors():
    seen = {}

    class Summary(GuardPlugin):                      # client: announce a vector, then use the server's answer
        name, at, needs = "summary", (Stage.CLIENT_ANNOUNCE, Stage.CLIENT_PRE_TRAIN), frozenset({"data", "reports"})

        def run(self, ctx):
            if ctx.stage == Stage.CLIENT_ANNOUNCE:
                return ctx.findings(attachments={"vec": torch.full((20000,), float(len(ctx.data)))}, messages={"n": len(ctx.data)})
            seen[ctx.participants[0]] = ctx.attachment("mean.vec")["server"][0].item()
            return ctx.findings()

    class Mean(GuardPlugin):                         # server: answer before anyone trains
        name, at, needs = "mean", Stage.SERVER_EXCHANGE, frozenset({"reports"})

        def run(self, ctx):
            vecs = ctx.attachment("summary.vec")
            assert set(ctx.reports.messages("summary.n")) == set(vecs)
            return ctx.findings(attachments={"vec": torch.stack(list(vecs.values())).mean(0)})

    server = OpenFedLLMGuard(GuardRunner([Mean()], SPEC, fail_policy="closed"))
    guards = {c: ClientGuard(f"client{c}", GuardRunner([Summary()], SPEC, side="client", fail_policy="closed")) for c in range(3)}
    base = make_base()
    server.begin_round(0, base, list(guards))
    announced = {}
    for c, g in guards.items():
        assert g.wants_exchange
        g.begin_round(0, server.model_for(c), data=DataView(["x"] * (c + 1)), defer=True)
        announced[c] = g.announce()
    messages, tensors = server.exchange(announced)
    for c, g in guards.items():
        g.deliver(messages, tensors)
        g.pre_train()
        g.before_upload(perturb(base, c))
        assert g.outbox() == {} and g.outbox_tensors() == {}          # the announcement is not sent a second time
        g.end_round()
    assert seen == {"client0": 2.0, "client1": 2.0, "client2": 2.0}   # mean of 1, 2, 3 samples


def test_channel_tensors_are_bounded_and_must_be_finite():
    big = GuardPluginSpy("big", needs=(), fn=lambda ctx: ctx.findings(attachments={"x": torch.zeros(2000)}))
    nan = GuardPluginSpy("nan", needs=(), fn=lambda ctx: ctx.findings(attachments={"x": torch.tensor([float("nan")])}))
    runner = GuardRunner([big, nan], SPEC, attachment_limit_bytes=1024)
    runner.begin_round(0)
    a, b = runner.run(Stage.SERVER_RECEIVE, [])
    assert a.error and "exceed" in a.error and b.error and runner.outbox_tensors() == {}


def _tok_path():
    snaps = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots"
    return next(snaps.iterdir(), None) if snaps.exists() else None


@pytest.mark.skipif(_tok_path() is None, reason="Qwen tokenizer not cached")
@pytest.mark.parametrize("apply_actions", [False, True])
def test_gradients_and_the_current_lora_are_reachable_inside_a_real_training_loop(tmp_path, apply_actions):
    from peft import LoraConfig, get_peft_model, get_peft_model_state_dict
    from transformers import AutoTokenizer, Qwen2Config, Qwen2ForCausalLM, Trainer, TrainingArguments

    from fedguard.adapters.hf_trainer import GuardStepCallback
    tok = AutoTokenizer.from_pretrained(_tok_path())
    torch.manual_seed(0)
    cfg = Qwen2Config(vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                      num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=64)
    model = get_peft_model(Qwen2ForCausalLM(cfg), LoraConfig(r=4, lora_alpha=8, target_modules=["q_proj", "v_proj"],
                                                              task_type="CAUSAL_LM"))
    seen = {"norms": [], "moved": []}

    def freeze_b(ctx):                                   # read every gradient, zero the lora_B ones
        g = ctx.gradients
        seen["norms"].append(g.norm())
        return ctx.findings(features={"self": {"grad_norm": g.norm()}},
                            proposals={"gradients": {n: torch.zeros_like(g.get(n)) for n in g.names() if "lora_B" in n}})

    def after_step(ctx):                                 # the LoRA right after the optimizer stepped
        now, start = ctx.train_trace.lora(), ctx.received_model.state()
        seen["moved"].append(sum(float((now[k] - start[k]).abs().sum()) for k in start if "lora_A" in k))
        return ctx.findings()

    plugins = [GuardPluginSpy("freeze_b", Stage.CLIENT_PRE_STEP, needs=("gradients",), acts=("transform_gradients",), fn=freeze_b),
               GuardPluginSpy("watch", Stage.CLIENT_STEP, needs=("train_trace", "received_model"), fn=after_step)]
    rec = Recorder(tmp_path, "run", scope="c0")
    guard = ClientGuard("c0", GuardRunner(plugins, SPEC, side="client", apply_actions=apply_actions, fail_policy="closed"), rec)
    start = {k: v.clone() for k, v in get_peft_model_state_dict(model).items()}
    with torch.no_grad():                                # lora_B starts at zero, so lora_A gets no gradient; give B a value
        for n, p in model.named_parameters():
            if "lora_B" in n:
                p.fill_(0.01)
    start = {k: v.clone() for k, v in get_peft_model_state_dict(model).items()}
    guard.begin_round(0, start)

    class DS(torch.utils.data.Dataset):
        def __len__(self):
            return 8

        def __getitem__(self, i):
            e = tok(["how do plants make food", "what is rain"][i % 2], padding="max_length", max_length=10, truncation=True)
            return {"input_ids": e["input_ids"], "attention_mask": e["attention_mask"], "labels": e["input_ids"]}

    args = TrainingArguments(str(tmp_path / "out"), max_steps=3, per_device_train_batch_size=4, report_to=[], use_cpu=True,
                             learning_rate=1e-2, weight_decay=0.0, logging_steps=1, save_strategy="no")
    Trainer(model=model, args=args, train_dataset=DS(),
            callbacks=[GuardStepCallback(guard, lora_state=get_peft_model_state_dict)]).train()
    end = get_peft_model_state_dict(model)
    guard.before_upload(end)
    guard.end_round()

    b_moved = any(not torch.equal(start[k], end[k]) for k in start if "lora_B" in k)
    a_moved = any(not torch.equal(start[k], end[k]) for k in start if "lora_A" in k)
    assert len(seen["norms"]) == 3 and all(n > 0 for n in seen["norms"]) and len(seen["moved"]) == 3 and seen["moved"][-1] > 0
    assert a_moved and b_moved is (not apply_actions)             # zeroing lora_B gradients freezes B only when applied
    trace = rec.load_lines(0, "trace")
    assert [t["step"] for t in trace][:3] == [1, 2, 3] and "loss" in trace[0]
    actions = [a for f in rec.load_round(0)["findings"] for a in f["actions"]]
    assert len(actions) == 3 and all(a["action"] == "transform_gradients" and a["applied"] is apply_actions and
                                     a["norm_after"] < a["norm_before"] for a in actions)


def test_plugin_state_has_three_scopes_and_the_runner_empties_the_two_short_ones():
    seen = []

    def count(ctx):
        for scope in (ctx.state, ctx.round_state, ctx.step_state):
            scope["n"] = scope.get("n", 0) + 1
        seen.append((ctx.round, ctx.stage.value, ctx.state["n"], ctx.round_state["n"], ctx.step_state["n"]))
        return ctx.findings()

    plugin = GuardPluginSpy("counter", (Stage.CLIENT_PRE_STEP, Stage.CLIENT_STEP), needs=("gradients", "train_trace"), fn=count)
    guard = ClientGuard("c0", GuardRunner([plugin], SPEC, side="client", fail_policy="closed"))
    p = torch.nn.Parameter(torch.zeros(2))
    p.grad = torch.ones(2)
    for t in range(2):
        guard.begin_round(t, make_base())
        for step in (1, 2):
            guard.on_gradients(step, [("w", p)])
            guard.on_step(step, {"loss": 1.0})
        guard.before_upload(perturb(make_base(), 1))
        guard.end_round()
    assert [s[2] for s in seen] == list(range(1, 9))                       # the run-long state never resets
    assert [s[3] for s in seen] == [1, 2, 3, 4] * 2                        # the round state starts over in round 1
    assert [s[4] for s in seen] == [1, 2] * 4                              # the two stages of a step share the step state
