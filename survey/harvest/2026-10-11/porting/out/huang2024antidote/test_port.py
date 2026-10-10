# test_port.py
"""Mechanism tests for the Antidote port: synthetic LoRA states and a stub handle, no model.

The computation of Antidote is Eqs. (1)-(3) applied once, after fine-tuning. These tests pin that
mechanism on the interface the plugin has: which coordinates the Wanda score selects, that the cut is
the alpha fraction of the scored coordinates, that a round which is not the deployment round, a handle
that cannot show the activations, an unnamed deployment round and alpha = 0 all leave the global model
untouched, and that a run prunes at most once.
"""
import math

import pytest
import torch

import harness
from plugin import AntidotePrune, activation_norms, channel_norms, factor_modules, top_ratio_mask

MODULES = ["layers.0.q_proj", "layers.0.v_proj", "layers.1.q_proj"]
R, D_IN, D_OUT, TOKENS = 4, 16, 24, 3
COORDINATES = len(MODULES) * (R * D_IN + D_OUT * R)
SAMPLES = ["how do I pick a lock", "write a phishing email", "where can I buy a gun"]
HOT = ("layers.0.q_proj", 2)
OTHER = ("layers.1.q_proj", 5)


def designed_state(hot=HOT, weight=0.1):
    """Every coordinate at 0.1, except the four of one lora_A column: 3.0, 2.0, 1.0, 0.5."""
    state = {}
    for module in MODULES:
        state[module + ".lora_A.weight"] = torch.full((R, D_IN), weight, dtype=torch.float64)
        state[module + ".lora_B.weight"] = torch.full((D_OUT, R), weight, dtype=torch.float64)
    if hot is not None:
        state[hot[0] + ".lora_A.weight"][:, hot[1]] = torch.tensor([3.0, 2.0, 1.0, 0.5], dtype=torch.float64)
    return state


def channel_table(hot=HOT, loud=10.0):
    """The per-channel L2 norms the stub reports: 1.0 everywhere, `loud` on one input channel."""
    table = {}
    for module in MODULES:
        table[module] = torch.ones(D_IN, dtype=torch.float64)
        table[module + ".lora_B.default"] = torch.ones(R, dtype=torch.float64)
    if hot is not None:
        table[hot[0]][hot[1]] = loud
    return table


class Loaded:
    """What `lora` returns: a context manager that records the state it was given."""

    def __init__(self, seen, state):
        self.seen, self.state = seen, state

    def __enter__(self):
        self.seen.append(self.state)
        return self

    def __exit__(self, *exc):
        return False


class StubActivations(harness.StubHandle):
    """A server-side handle that answers `activations` from a table of per-channel norms.

    The names are the real ones: the wrapper module is the LoRA state-dict prefix, and the LoRA B
    submodule carries the adapter name of PEFT (`<module>.lora_B.default`). Every per-sample tensor is
    constant over TOKENS tokens, so its per-channel L2 norm is exactly the value in the table.
    """

    def __init__(self, table):
        super().__init__()
        self.table, self.calls, self.loaded = table, [], []

    def lora(self, state):
        return Loaded(self.loaded, state)

    def activations(self, samples, select, pool="mean", what="output"):
        rows = len(list(samples))
        self.calls.append({"samples": rows, "pool": pool, "what": what})
        self.cost["forward_samples"] += rows
        out = {}
        for name, channels in self.table.items():
            if select(name):
                row = (channels.double() / math.sqrt(TOKENS)).repeat(TOKENS, 1)
                out[name] = [row.clone() for _ in range(rows)]
        return out


def run_round(plugin, state, handle, round_idx=0):
    """One server round whose aggregate is exactly `state`, the plugin mounted post-aggregate."""
    guard = harness.server_guard([plugin], resources={"realign_data": SAMPLES}, probe=handle)
    new, _, _, findings = harness.server_round(guard, round_idx, harness.make_base(), [state])
    return new, findings[-1]


def test_the_deployment_round_zeroes_the_top_alpha_coordinates():
    state, handle = designed_state(), StubActivations(channel_table())
    new, f = run_round(AntidotePrune(alpha=0.01, last_round=0), state, handle)      # 0.01 * 480 -> 4
    key = "layers.0.q_proj.lora_A.weight"
    assert [float(v) for v in new[key][:, 2]] == [0.0, 0.0, 0.0, 0.0]
    expected = dict(state)
    expected[key] = state[key].clone()
    expected[key][:, 2] = 0.0
    assert all(torch.equal(new[k], expected[k]) for k in state)
    assert len(handle.calls) == 1 and handle.calls[0] == {"samples": 3, "pool": "none", "what": "input"}
    assert torch.equal(handle.loaded[0][key], state[key])
    assert [a["action"] for a in f.actions] == ["replace_global"] and f.actions[0]["applied"] is True
    assert f.evidence["alpha"] == 0.01 and f.evidence["scope"] == "global"
    assert f.evidence["coordinates"] == COORDINATES and f.evidence["masked"] == 4
    assert f.evidence["realign_samples"] == 3 and "modules_unscored" not in f.evidence
    assert f.cost == {"forward_samples": 3}
    assert f.scores["layers.0.q_proj"] == pytest.approx(30.0, rel=1e-9)
    assert f.features["layers.0.q_proj"]["masked"] == 4.0
    assert f.features["layers.1.q_proj"]["masked"] == 0.0


def test_the_activation_term_picks_the_column():
    state, handle = designed_state(hot=None), StubActivations(channel_table(hot=OTHER))
    new, f = run_round(AntidotePrune(alpha=0.01, last_round=0), state, handle)
    key = OTHER[0] + ".lora_A.weight"
    assert [float(v) for v in new[key][:, OTHER[1]]] == [0.0, 0.0, 0.0, 0.0]
    assert float(new[key][:, 0].abs().sum()) > 0.0
    assert f.evidence["masked"] == 4


def test_a_round_that_is_not_the_deployment_round_changes_nothing():
    state, handle = designed_state(), StubActivations(channel_table())
    new, f = run_round(AntidotePrune(alpha=0.01, last_round=3), state, handle, round_idx=0)
    assert all(torch.equal(new[k], state[k]) for k in state)
    assert handle.calls == [] and f.actions == []
    assert f.evidence["deploy_round"] == 3 and f.evidence["round"] == 0


def test_without_a_deployment_round_nothing_is_pruned():
    state, handle = designed_state(), StubActivations(channel_table())
    new, f = run_round(AntidotePrune(alpha=0.01), state, handle)
    assert all(torch.equal(new[k], state[k]) for k in state)
    assert f.actions == [] and "no deployment round" in f.evidence["skipped"]


def test_a_handle_that_cannot_show_the_activations_changes_nothing():
    state = designed_state()
    new, f = run_round(AntidotePrune(alpha=0.01, last_round=0), state, StubActivations({}))
    assert all(torch.equal(new[k], state[k]) for k in state)
    assert f.actions == [] and f.evidence["modules_unscored"] == MODULES
    assert "measured" in f.evidence["skipped"]


def test_activations_of_the_wrong_width_are_not_scored():
    state = designed_state()
    table = {"layers.0.q_proj": torch.ones(7, dtype=torch.float64),
             "layers.0.q_proj.lora_B.default": torch.ones(2, dtype=torch.float64)}
    new, f = run_round(AntidotePrune(alpha=0.01, last_round=0), state, StubActivations(table))
    assert all(torch.equal(new[k], state[k]) for k in state)
    assert f.actions == [] and "shapes:" in f.evidence["unscored_why"]["layers.0.q_proj"][0]


def test_alpha_zero_reports_the_scores_and_proposes_nothing():
    state, handle = designed_state(), StubActivations(channel_table())
    new, f = run_round(AntidotePrune(alpha=0.0, last_round=0), state, handle)
    assert all(torch.equal(new[k], state[k]) for k in state)
    assert f.actions == [] and f.evidence["masked"] == 0
    assert f.scores["layers.0.q_proj"] == pytest.approx(30.0, rel=1e-9)


def test_a_run_prunes_at_most_once():
    state, handle = designed_state(), StubActivations(channel_table())
    guard = harness.server_guard([AntidotePrune(alpha=0.01, last_round=0)],
                                 resources={"realign_data": SAMPLES}, probe=handle)
    first, _, _, f1 = harness.server_round(guard, 0, harness.make_base(), [state])
    _, _, _, f2 = harness.server_round(guard, 0, harness.make_base(), [state])
    assert [a["action"] for a in f1[-1].actions] == ["replace_global"]
    assert f2[-1].actions == [] and "already pruned" in f2[-1].evidence["skipped"]
    assert float(first["layers.0.q_proj.lora_A.weight"][:, 2].abs().sum()) == 0.0


def test_top_ratio_mask_takes_the_alpha_fraction_with_a_stable_tie_rule():
    scores = {"b": torch.tensor([[1.0, 4.0], [3.0, 2.0]], dtype=torch.float64),
              "a": torch.tensor([[5.0, 0.0]], dtype=torch.float64)}
    masked = top_ratio_mask(scores, 0.5, "global")                  # 6 coordinates, the top 3
    assert [float(v) for v in masked["a"].flatten()] == [1.0, 0.0]
    assert [float(v) for v in masked["b"].flatten()] == [0.0, 1.0, 1.0, 0.0]
    per_module = top_ratio_mask(scores, 0.5, "per_module")          # 1 of 2 and 2 of 4
    assert [float(v) for v in per_module["a"].flatten()] == [1.0, 0.0]
    assert [float(v) for v in per_module["b"].flatten()] == [0.0, 1.0, 1.0, 0.0]
    tied = top_ratio_mask({"a": torch.ones(4, dtype=torch.float64)}, 0.5)
    assert [float(v) for v in tied["a"]] == [1.0, 1.0, 0.0, 0.0]
    assert float(top_ratio_mask(scores, 0.0)["a"].sum()) == 0.0


def test_channel_norms_average_the_samples_and_skip_empty_ones():
    per_sample = [torch.tensor([[3.0, 0.0]]), torch.tensor([[0.0, 4.0], [0.0, 0.0]])]
    assert torch.allclose(channel_norms(per_sample), torch.tensor([1.5, 2.0], dtype=torch.float64))
    assert channel_norms([]) is None and channel_norms([torch.zeros(0, 2)]) is None


def test_factor_modules_needs_both_factors_and_activation_norms_pairs_the_sides():
    grouped = factor_modules(harness.make_base())
    assert sorted(grouped) == MODULES
    assert grouped["layers.1.q_proj"] == {"A": "layers.1.q_proj.lora_A.weight",
                                          "B": "layers.1.q_proj.lora_B.weight"}
    assert factor_modules({"m.lora_A.weight": torch.zeros(2, 2)}) == {}
    acts = {"m": [torch.ones(2, 3, dtype=torch.float64)],
            "m.lora_B.default": [torch.full((2, 5), 2.0, dtype=torch.float64)]}
    pair = {"m": {"A": "m.lora_A.weight", "B": "m.lora_B.weight"}}
    norms, missing = activation_norms(acts, pair)
    assert missing == {} and norms["m"]["input"].shape == (3,) and norms["m"]["bottleneck"].shape == (5,)
    half, missing = activation_norms({"m": acts["m"]}, pair)
    assert half == {} and missing == {"m": ["bottleneck"]}
