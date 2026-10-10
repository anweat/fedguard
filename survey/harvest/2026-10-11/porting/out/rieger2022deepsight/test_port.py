# test_port.py
'''Mechanism test for the DeepSight port: synthetic LoRA states only, no model, no host framework.'''
import torch

import harness
from plugin import DeepSight

READOUT = 'layers.1.q_proj'     # the module the deployments in these tests adapted as the output layer


def _delta(state, base):
    return float(torch.sqrt(sum(((state[k] - base[k]).double() ** 2).sum() for k in base)))


def _spike(base, module, row=3, amp=5.0, seed=99):
    '''The base with one row of the readout lora_B shifted: its readout delta then has exactly one
    non-zero output neuron -- a concentrated energy profile, the shape Threshold Exceedings counts as
    suspicious.'''
    gen = torch.Generator().manual_seed(seed)
    out = {k: v.clone() for k, v in base.items()}
    b = out[module + '.lora_B.weight']
    b[row] = b[row] + amp * torch.randn(b.shape[1], generator=gen, dtype=b.dtype)
    return out


def _round(plugin, base, locals_, t=0):
    guard = harness.server_guard([plugin])
    new, kept, decision, findings = harness.server_round(guard, t, base, locals_)
    return guard, new, kept, decision, findings


def test_the_poisoned_cluster_is_excluded_and_the_kept_uploads_are_clipped():
    base = harness.make_base()
    locals_ = [harness.perturb(base, seed=10 + i, scale=0.05) for i in range(7)] + [_spike(base, READOUT)]
    guard, new, kept, decision, findings = _round(DeepSight(readout=READOUT), base, locals_)
    assert decision.excluded == {'client7'}
    assert kept == list(range(7))
    assert set(decision.weights) == {f'client{i}' for i in range(7)}
    assert set(decision.weights.values()) == {1.0}
    evidence = findings[0].evidence
    assert evidence['excluded'] == ['client7'] and evidence['readout'] == READOUT
    bound = evidence['bound']
    cut = [i for i in range(7) if _delta(locals_[i], base) > bound]
    assert cut and sorted(guard.transformed) == cut          # the clipping layer ran on the kept uploads
    for i in cut:
        assert abs(_delta(guard.transformed[i], base) - bound) < 1e-9
    assert 7 not in guard.transformed                        # an excluded upload is not clipped
    assert _delta(locals_[7], base) > bound


def test_nothing_is_excluded_when_every_update_looks_alike():
    base = harness.make_base()
    locals_ = [harness.perturb(base, seed=20 + i, scale=0.05) for i in range(8)]
    guard, new, kept, decision, findings = _round(DeepSight(readout=READOUT), base, locals_)
    assert decision.excluded == set()
    assert kept == list(range(8))
    assert {f['suspicious'] for f in findings[0].features.values()} == {0.0}


def test_the_verdict_survives_a_uniform_rescaling_of_every_update():
    base = harness.make_base()
    verdicts = set()
    for scale in (0.02, 0.5):
        locals_ = [harness.perturb(base, seed=30 + i, scale=scale) for i in range(7)] + [_spike(base, READOUT, amp=5.0 * scale)]
        guard, new, kept, decision, findings = _round(DeepSight(readout=READOUT), base, locals_)
        verdicts.add(frozenset(decision.excluded))
    assert verdicts == {frozenset({'client7'})}


def test_skipped_when_no_adapted_module_stands_in_for_the_output_layer():
    base = harness.make_base()
    locals_ = [harness.perturb(base, seed=40 + i) for i in range(8)]
    guard, new, kept, decision, findings = _round(DeepSight(readout='lm_head'), base, locals_)
    assert 'skipped' in findings[0].evidence
    assert decision.excluded == set() and kept == list(range(8))
    assert guard.transformed == {}
    assert set(decision.weights.values()) == {1.0}          # the aggregation layer does not depend on the filter


def test_the_default_readout_is_the_last_adapted_module():
    base = harness.make_base()
    locals_ = [harness.perturb(base, seed=50 + i, scale=0.05) for i in range(7)] + [_spike(base, READOUT)]
    guard, new, kept, decision, findings = _round(DeepSight(), base, locals_)
    assert findings[0].evidence['readout'] == READOUT
    assert decision.excluded == {'client7'}
