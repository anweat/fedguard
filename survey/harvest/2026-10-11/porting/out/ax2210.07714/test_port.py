# test_port.py
"""Mechanism tests for the CrowdGuard port, without a model and without a host framework.

The client-side model handle is a double: the per-sample, per-layer outputs of a model are a function of
one entry of the loaded LoRA state (the signal), so the distances the plugin computes are deterministic.
The honest uploads of a round share one signal value, the poisoned upload moves it far away, and the pack
is built exactly as the server plugin builds it (flattened states plus the client list and the round).
"""
import torch

import harness
from harness import DataView, StubHandle, client_guard, make_base, perturb, server_guard, server_round
from fedguard.ops import states

from plugin import CrowdGuardServer, CrowdGuardValidator

SERVER, CLIENT = "crowdguard_server", "crowdguard_validator"
SIGNAL = "layers.0.q_proj.lora_B.weight"
SAMPLES = [("aa", "good"), ("bbb", "bad"), ("c", "good"), ("dd", "bad"), ("eee", "good"), ("ffff", "bad")]
CIDS = ["c0", "c1", "c2", "c3", "c4", "c5"]


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
    """A model double: the outputs depend on one entry of the loaded adapter and on the sample label."""

    LAYERS = ("block0", "block1")

    def __init__(self):
        super().__init__()
        self.loaded = None

    def lora(self, state):
        return _Loaded(self, state)

    def activations(self, samples, select=None, pool="mean", what="output"):
        signal = float(self.loaded[SIGNAL][0, 0])
        out = {}
        for depth, name in enumerate(self.LAYERS):
            rows = []
            for text, label in samples:
                bad = 1.0 if label == "bad" else 0.0
                rows.append([float(len(text)) + signal, bad * (1.0 + signal), signal * (depth + 1)])
            out[name] = torch.tensor(rows, dtype=torch.float64)
        return out


def uploads(base, poison=None, shift=0.5):
    """Six uploads that differ from the base only in the signal: the honest ones by `shift`, the poisoned
    one (index `poison`) by 5.0."""
    out = []
    for i in range(len(CIDS)):
        state = perturb(base, i, scale=1e-3)
        state[SIGNAL] = state[SIGNAL].clone()
        state[SIGNAL][0, 0] = float(base[SIGNAL][0, 0]) + shift
        out.append(state)
    if poison is not None:
        out[poison][SIGNAL][0, 0] = float(base[SIGNAL][0, 0]) + 5.0
    return out


def pack(base, states_list, round_idx=0):
    """What CrowdGuardServer puts on the channel: one flattened state per model, the client list, the round."""
    attachments = {SERVER + ".pack.base": states.flatten(base)}
    for cid, state in zip(CIDS, states_list):
        attachments[SERVER + ".pack." + cid] = states.flatten(state)
    messages = {SERVER + ".pack_clients": list(CIDS), SERVER + ".pack_round": round_idx}
    return messages, attachments


def validate(base, states_list, client="c0"):
    messages, attachments = pack(base, states_list)
    guard = client_guard([CrowdGuardValidator()], resources={"label_of": lambda sample: sample[1]}, client_id=client)
    guard.begin_round(1, base, data=DataView(SAMPLES, text_of=lambda sample: sample[0]), model_handle=Handle(),
                      messages=messages, attachments=attachments)
    guard.before_upload(base)
    guard.end_round()
    return guard.outbox()


def test_a_poisoned_upload_is_the_only_model_voted_against():
    base = make_base()
    votes = validate(base, uploads(base, poison=3))[CLIENT + ".votes"]
    assert votes == [1, 1, 1, 0, 1, 1]


def test_a_pack_without_a_deviation_is_voted_all_benign():
    base = make_base()
    votes = validate(base, uploads(base, shift=0.0))[CLIENT + ".votes"]
    assert votes == [1, 1, 1, 1, 1, 1]


def test_the_server_packs_the_round_and_excludes_a_client_the_votes_reject():
    guard = server_guard([CrowdGuardServer()])
    base = make_base()
    locals_ = [perturb(base, i) for i in range(6)]
    new, kept, decision, findings = server_round(guard, 0, base, locals_)
    assert kept == [0, 1, 2, 3, 4, 5]
    assert SERVER + ".pack.client3" in guard.outbox_tensors
    assert guard.outbox[SERVER + ".pack_clients"] == ["client" + str(i) for i in range(6)]
    guard.begin_round(1, new, list(range(6)))
    for c, state in enumerate(locals_):
        if c == 5:
            row = [0] * 6
        elif c == 4:
            row = [1] * 6
        else:
            row = [1, 1, 1, 0, 1, 1]
        guard.on_upload(c, state, {"num_examples": 10},
                        messages={CLIENT + ".votes": row, CLIENT + ".pack_round": 0})
    kept1, weights = guard.before_aggregate(list(range(6)), [10] * 6)
    assert kept1 == [0, 1, 2, 4, 5]
    assert all(weights[c] == 1 for c in kept1)
    assert guard.last_decision.excluded == {"client3"}
