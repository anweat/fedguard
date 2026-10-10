# test_port.py
"""Mechanism tests for the Obliviate neuron amplification plugin: no model, no host framework.

The point exercised is the one the trainer extension layer opens (CLIENT_LOSS): a task loss with a
graph, the trainable LoRA parameters and the batch. Checked are the term added to the loss, the
direction the resulting update pushes the factors in, the mounting of the class with no arguments, and
the cases in which it must leave the loss of the host alone. The clean-accuracy / attack-success
numbers of the paper need RoBERTa, SST-2 / AG News / HSOL and a backdoored checkpoint and are not
checked here.

LossView is built directly because the harness has no helper for a training-step point.
"""
import pytest
import torch

import harness
from fedguard.core.types import Stage
from fedguard.views.client import LossView
from plugin import ObliviateLamp, amplification_penalty

LAMBDA = 0.01
DEFAULT_LAMBDA = 1e-3          # smallest lambda_amp candidate of the paper Table 7
HOST_LOSS = 2.0
R, D_IN, D_OUT = 4, 16, 24
Q = "base_model.model.model.layers.0.self_attn.q_proj"
V = "base_model.model.model.layers.1.self_attn.v_proj"
NAMES = [f"{Q}.lora_A.default.weight", f"{Q}.lora_B.default.weight",
         f"{V}.lora_A.default.weight", f"{V}.lora_B.default.weight"]
EXTRA = "classifier.modules_to_save.default.weight"
BATCH = {"input_ids": torch.zeros(2, 3, dtype=torch.long), "labels": torch.zeros(2, 3, dtype=torch.long)}


def trainables(seed=0, lora=True, extra=False, zero_b=False):
    """(name, Parameter) as the trainer hands them in: the LoRA factors, plus optionally a trainable
    tensor of the kind a PEFT config may add next to them."""
    g = torch.Generator().manual_seed(seed)
    out = []
    if lora:
        for name in NAMES:
            shape = (R, D_IN) if name.endswith("lora_A.default.weight") else (D_OUT, R)
            if zero_b and name.endswith("lora_B.default.weight"):
                t = torch.zeros(shape, dtype=torch.float64)
            else:
                t = 0.5 + torch.rand(shape, generator=g, dtype=torch.float64)
            out.append((name, torch.nn.Parameter(t)))
    if extra:
        out.append((EXTRA, torch.nn.Parameter(torch.rand(D_OUT, D_IN, generator=g, dtype=torch.float64))))
    return out


def step(plugin, named, apply=True):
    """One CLIENT_LOSS call on a fresh client guard; returns (guard, host loss, loss to back-propagate)."""
    guard = harness.client_guard([plugin], apply=apply)
    guard.begin_round(0, harness.make_base())
    host = torch.tensor(HOST_LOSS, dtype=torch.float64, requires_grad=True)
    view = LossView(host, None, dict(BATCH), named, loss_on=lambda batch: host + 0.0)
    return guard, host, guard.on_loss(0, view)


def test_the_plugin_mounts_with_no_arguments_and_uses_a_paper_candidate():
    plugin = ObliviateLamp()                       # the check that failed before: cls() must work
    assert plugin.lambda_amp == DEFAULT_LAMBDA     # smallest candidate of Table 7, not an invented value
    assert plugin.stages == (Stage.CLIENT_LOSS,)
    guard = harness.client_guard([plugin])
    assert guard.has_loss_plugins
    named = trainables()
    guard2, host, out = step(plugin, named)
    lamp = float(amplification_penalty(dict(named)).detach())
    assert out.item() == pytest.approx(HOST_LOSS + DEFAULT_LAMBDA * lamp, rel=1e-12)
    assert guard2.runner.findings[-1].error is None


def test_lamp_is_added_to_the_step_loss():
    named = trainables()
    guard, host, out = step(ObliviateLamp(lambda_amp=LAMBDA), named)
    lamp = float(amplification_penalty(dict(named)).detach())
    assert lamp < 0                                         # Eq. (1) is negative: minimizing it amplifies
    assert out.item() == pytest.approx(HOST_LOSS + LAMBDA * lamp, rel=1e-12)
    assert out.item() < HOST_LOSS
    f = guard.runner.findings[-1]
    assert f.stage == Stage.CLIENT_LOSS and f.error is None
    assert f.actions == [{"action": "transform_loss", "before": HOST_LOSS, "after": out.item(), "applied": True}]
    assert f.evidence["tensors"] == len(NAMES)
    assert f.evidence["lamp"] == pytest.approx(lamp)


def test_the_update_raises_every_factor_norm_and_leaves_other_trainables_alone():
    named = trainables(extra=True)
    guard, host, out = step(ObliviateLamp(lambda_amp=LAMBDA), named)
    out.backward()
    before = {n: float(p.detach().norm()) for n, p in named}
    grads = {n: p.grad for n, p in named}
    for n in NAMES:
        p = dict(named)[n]
        assert grads[n] is not None
        assert float((grads[n] * p.detach()).sum()) < 0     # the step is in the direction of larger norm
        with torch.no_grad():
            p -= 0.05 * grads[n]
        assert float(p.detach().norm()) > before[n]
    assert grads[EXTRA] is None                             # not a LoRA decomposition matrix: not amplified


def test_a_step_without_lora_factors_leaves_the_host_loss_untouched():
    named = trainables(lora=False, extra=True)
    guard, host, out = step(ObliviateLamp(lambda_amp=LAMBDA), named)
    assert out is host
    f = guard.runner.findings[-1]
    assert f.proposals == {} and f.actions == [] and f.error is None
    assert "skipped" in f.evidence


def test_a_zero_factor_keeps_the_term_and_its_gradient_finite():
    named = trainables(zero_b=True)
    guard, host, out = step(ObliviateLamp(lambda_amp=LAMBDA), named)
    assert torch.isfinite(out)
    out.backward()
    for n, p in named:
        assert p.grad is not None and bool(torch.isfinite(p.grad).all())
    assert [float(dict(named)[n].grad.norm()) for n in (NAMES[1], NAMES[3])] == [0.0, 0.0]
