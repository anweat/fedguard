# test_port.py
"""Mechanism tests for the Proof-of-Learning port, without a model and without a host framework.

The client side is a synthetic eight-step round on a three-module LoRA state. The model double returns a
constant per-sample gradient, so the trajectory the test trains is exactly the trajectory the verifier
re-executes: an honest proof passes, a tampered checkpoint, a batch hash the defender data cannot account
for, a first checkpoint that is not the broadcast model and an unknown initialization strategy all fail,
and without a server model the proof is unverified instead of failed. The server side is driven directly,
because a proof travels in the client outbox (messages and attachments) which harness.server_round does
not carry.
"""
import torch

import harness
from harness import DataView, StubHandle, client_guard, make_base, server_guard
from fedguard.ops import states
from fedguard.views.client import LossView, sample_hash

from plugin import PoLProver, PoLVerifier

SAMPLES = ["s" + str(i) for i in range(16)]
K, EPOCH_LEN, LR, STEPS = 2, 4, 0.1, 8
DELTA = 1e-6
PROOF = "pol_prover"


def _value(sample):
    """The per-sample gradient the model double returns: a constant that depends on the sample."""
    return 0.01 * (1 + int(sample[1:]) % 5)


def _grad(sample, like):
    return {key: torch.full_like(like[key], _value(sample)) for key in like}


def _batch(step):
    return SAMPLES[2 * step:2 * step + 2]


def _train_step(state, batch):
    keys = sorted(state)
    mean = {key: torch.stack([_grad(s, state)[key] for s in batch]).mean(dim=0) for key in keys}
    return states.add(state, mean, -LR)


class _Loaded:
    """The context manager ModelHandle.lora returns: swap the loaded adapter in and restore it."""

    def __init__(self, handle, state):
        self.handle, self.state = handle, state

    def __enter__(self):
        self.before = self.handle.loaded
        self.handle.loaded = self.state
        return self.handle

    def __exit__(self, kind, value, trace):
        self.handle.loaded = self.before
        return False


class Handle(StubHandle):
    """A model double: one backward pass per sample returns the constant of _value(sample)."""

    def __init__(self, base):
        super().__init__()
        self.base, self.loaded = base, None

    def lora(self, state):
        return _Loaded(self, state)

    def layout(self, group="lora", scope="lora"):
        return [(key, tuple(self.base[key].shape)) for key in sorted(self.base)]

    def per_sample_gradients(self, samples, group="lora", scope="lora", reduce=None):
        rows = [states.flatten(_grad(s, self.base), keys=sorted(self.base)) for s in samples]
        self.cost["forward_samples"] += len(rows)
        self.cost["backward_samples"] += len(rows)
        return torch.stack(rows)


def run_client(base, strategy="normal_unit", tamper_row=None, tamper_value=0.0, bad_hash=None):
    """Train the synthetic round with PoLProver mounted; return (messages, attachments, upload)."""
    guard = client_guard([PoLProver(k=K, lr=LR, epoch_len=EPOCH_LEN, init_strategy=strategy)])
    guard.begin_round(0, base, data=DataView(SAMPLES, text_of=str))
    state = {key: value.clone() for key, value in base.items()}
    for step in range(STEPS):
        batch = _batch(step)
        view = LossView(loss=torch.zeros((), requires_grad=True), outputs=None, batch={"texts": list(batch)},
                        named_parameters=[], loss_on=lambda rows: torch.zeros(()),
                        identify=lambda rows: [sample_hash(s) for s in rows["texts"]])
        guard.on_loss(step, view)
        state = _train_step(state, batch)
        guard.on_step(step, {"loss": 0.5, "lr": LR}, lora=lambda: state)
    guard.before_upload(state)
    messages, tensors = dict(guard.outbox()), dict(guard.outbox_tensors())
    guard.end_round()
    if tamper_row is not None:
        rows = tensors[PROOF + ".checkpoints"].clone()
        rows[tamper_row] = rows[tamper_row] + tamper_value
        tensors[PROOF + ".checkpoints"] = rows
    if bad_hash is not None:
        flat = list(messages[PROOF + ".hashes"])
        counts = list(messages[PROOF + ".hash_counts"])
        flat[sum(counts[:bad_hash[0]]) + bad_hash[1]] = "0" * 64
        messages[PROOF + ".hashes"] = flat
    return messages, tensors, state


def run_server(base, upload, messages, tensors, probe=True, Q=1, delta=DELTA):
    """Drive the server side of one round by hand, with the proof of one client in the upload."""
    resources = {"client_data": {"client0": {sample_hash(s): s for s in SAMPLES}},
                 "init_spec": {"normal_unit": {key: ("normal", 0.0, 1.0) for key in sorted(base)}}}
    guard = server_guard([PoLVerifier(Q=Q, delta=delta)], resources=resources, probe=Handle(base) if probe else None)
    guard.begin_round(0, base, [0])
    guard.on_upload(0, upload, {"num_examples": 10}, messages=messages, attachments=tensors)
    guard.before_aggregate([0], [10])
    finding = guard.runner.findings[0]
    guard.end_round()
    return finding


def test_an_honest_proof_passes_and_proposes_nothing():
    base = make_base()
    messages, tensors, upload = run_client(base)
    finding = run_server(base, upload, messages, tensors)
    assert finding.decision is None
    assert finding.evidence["verdicts"]["client0"] == "success"
    assert finding.scores["client0"] == 0.0
    assert finding.evidence["windows"]["client0"]["start_steps"] == [0, 4, 6]
    assert finding.evidence["windows"]["client0"]["checked"] == 3


def test_a_tampered_checkpoint_fails_the_distance_check():
    base = make_base()
    messages, tensors, upload = run_client(base, tamper_row=3, tamper_value=5.0)
    finding = run_server(base, upload, messages, tensors)
    assert finding.evidence["verdicts"]["client0"] == "fail"
    assert finding.scores["client0"] == 1.0
    assert 4 in finding.evidence["windows"]["client0"]["start_steps"]
    assert any("re-executed" in reason for reason in finding.evidence["failures"]["client0"])


def test_a_batch_hash_the_defender_data_does_not_hold_fails_the_signature():
    base = make_base()
    messages, tensors, upload = run_client(base, bad_hash=(4, 0))
    finding = run_server(base, upload, messages, tensors)
    assert finding.evidence["verdicts"]["client0"] == "fail"
    assert any("data signature" in reason for reason in finding.evidence["failures"]["client0"])


def test_a_first_checkpoint_that_is_not_the_broadcast_model_fails():
    base = make_base()
    messages, tensors, upload = run_client(base, tamper_row=0, tamper_value=5.0)
    finding = run_server(base, upload, messages, tensors)
    assert finding.evidence["verdicts"]["client0"] == "fail"
    assert any("first checkpoint" in reason for reason in finding.evidence["failures"]["client0"])


def test_an_unknown_initialization_strategy_fails_the_provenance_check():
    base = make_base()
    messages, tensors, upload = run_client(base, strategy="lora_default_of_another_framework")
    finding = run_server(base, upload, messages, tensors)
    assert finding.evidence["verdicts"]["client0"] == "fail"
    assert any("initialization" in reason for reason in finding.evidence["failures"]["client0"])


def test_without_a_server_model_the_proof_is_unverified_not_failed():
    base = make_base()
    messages, tensors, upload = run_client(base)
    finding = run_server(base, upload, messages, tensors, probe=False)
    assert finding.evidence["verdicts"]["client0"] == "unverified"
    assert finding.scores["client0"] == 0.5
    assert finding.evidence["failures"]["client0"] == []
