# test_port.py
import torch

import harness
from plugin import PEFTGuard


ROLES = ("q_proj", "v_proj")


def blocks_base(seed=0):
    """Two transformer blocks, each with q_proj and v_proj (harness.make_base has no v_proj in block 1)."""
    state = harness.make_base(seed)
    g = torch.Generator().manual_seed(seed + 1000)
    a = state["layers.1.q_proj.lora_A.weight"]
    b = state["layers.1.q_proj.lora_B.weight"]
    state["layers.1.v_proj.lora_A.weight"] = torch.randn(a.shape, generator=g, dtype=a.dtype)
    state["layers.1.v_proj.lora_B.weight"] = torch.randn(b.shape, generator=g, dtype=b.dtype)
    return state


def paper_features(uploaded, roles=ROLES):
    """Steps 1-4 of the paper, rebuilt independently of the plugin: delta = B A per block and role, blocks
    in order, roles of a block in order, scaled by the lora_scale of the round as ctx.uploads does."""
    rows = []
    for block in (0, 1):
        for role in roles:
            module = f"layers.{block}.{role}"
            b = uploaded[module + ".lora_B.weight"]
            a = uploaded[module + ".lora_A.weight"]
            rows.append(harness.SPEC.lora_scale * (b @ a))
    return torch.stack(rows)


def same(got, ref):
    """The plugin forms F_input in float32, the reference above in float64: compare to float32 precision."""
    return torch.allclose(got, ref.to(got.dtype), rtol=1e-5, atol=1e-4)


class PlantedDetector:
    """Stand-in for the meta-classifier that the paper trains offline (its architecture is Figure 7a only,
    and PADBench is not here). It calls an adapter backdoored when the query change of block 0, the first
    channel of F_input, exceeds `bound`: the synthetic signature these tests plant. It records every
    F_input it is handed, so the tests can check the feature transform itself."""

    def __init__(self, bound):
        self.bound, self.seen = float(bound), []

    def __call__(self, features):
        self.seen.append(features.detach().clone())
        return 0.97 if float(features[0].norm()) > self.bound else 0.03


def round_inputs(n=8, seed=0):
    base = blocks_base()
    locals_ = [harness.perturb(base, seed + i, scale=0.1) for i in range(n)]
    return base, locals_, max(float(paper_features(s)[0].norm()) for s in locals_)


def test_an_amplified_query_update_is_excluded():
    base, locals_, clean = round_inputs()
    locals_[5] = {k: (v * 40.0 if k.startswith("layers.0.q_proj.") else v) for k, v in locals_[5].items()}
    detector = PlantedDetector(bound=4.0 * clean)
    guard = harness.server_guard([PEFTGuard()], resources={"classifier": detector})
    new_global, kept, decision, findings = harness.server_round(guard, 0, base, locals_)

    assert kept == [0, 1, 2, 3, 4, 6, 7]
    assert decision.excluded == {"client5"}
    assert decision.flags["client5"].startswith("p=")
    assert findings[0].error is None
    assert findings[0].scores["client5"] > 0.9
    assert all(findings[0].scores[f"client{i}"] < 0.1 for i in kept)

    # every adapter reached the classifier as F_input, in upload order
    assert len(detector.seen) == 8
    for i, features in enumerate(detector.seen):
        assert features.shape == (4, 24, 16)
        assert same(features, paper_features(locals_[i]))

    # and the round really aggregated only the clients that were kept
    avg = {k: sum(locals_[i][k] for i in kept) / len(kept) for k in base}
    assert all(torch.allclose(new_global[k], avg[k]) for k in base)
    dropped = "layers.0.q_proj.lora_B.weight"
    assert not torch.allclose(new_global[dropped], sum(s[dropped] for s in locals_) / len(locals_))


def test_a_clean_round_is_left_alone():
    base, locals_, clean = round_inputs()
    detector = PlantedDetector(bound=4.0 * clean)
    guard = harness.server_guard([PEFTGuard()], resources={"classifier": detector})
    new_global, kept, decision, findings = harness.server_round(guard, 0, base, locals_)

    assert kept == list(range(8))
    assert decision.excluded == set()
    assert findings[0].evidence["flagged"] == []
    avg = {k: sum(s[k] for s in locals_) / len(locals_) for k in base}
    assert all(torch.allclose(new_global[k], avg[k]) for k in base)


def test_increment_space_subtracts_the_broadcast_base():
    base, locals_, clean = round_inputs(n=4)
    detector = PlantedDetector(bound=1e9)
    guard = harness.server_guard([PEFTGuard(space="increment")], resources={"classifier": detector})
    harness.server_round(guard, 0, base, locals_)

    for i, features in enumerate(detector.seen):
        rows = []
        for block in (0, 1):
            for role in ROLES:
                m = f"layers.{block}.{role}"
                moved = locals_[i][m + ".lora_B.weight"] @ locals_[i][m + ".lora_A.weight"]
                sent = base[m + ".lora_B.weight"] @ base[m + ".lora_A.weight"]
                rows.append(harness.SPEC.lora_scale * (moved - sent))
        assert same(features, torch.stack(rows))


def test_a_deployment_without_the_configured_modules_is_not_judged():
    base = harness.make_base()                      # block 1 carries q_proj only, so v is missing there
    locals_ = [harness.perturb(base, i, scale=0.1) for i in range(4)]
    detector = PlantedDetector(bound=0.0)           # would flag anything it was handed
    guard = harness.server_guard([PEFTGuard()], resources={"classifier": detector})
    new_global, kept, decision, findings = harness.server_round(guard, 0, base, locals_)

    assert detector.seen == []
    assert kept == [0, 1, 2, 3] and decision.excluded == set()
    assert findings[0].evidence["judged"] == 0
    assert "1:v_proj" in findings[0].evidence["not_judged"]["client0"]


def test_the_single_module_layout_is_stacked_as_configured():
    base = harness.make_base()                      # q_proj in blocks 0 and 1
    locals_ = [harness.perturb(base, i, scale=0.1) for i in range(4)]
    detector = PlantedDetector(bound=1e9)
    guard = harness.server_guard([PEFTGuard(roles=("q_proj",))], resources={"classifier": detector})
    harness.server_round(guard, 0, base, locals_)

    assert [tuple(f.shape) for f in detector.seen] == [(2, 24, 16)] * 4
    assert same(detector.seen[0], paper_features(locals_[0], roles=("q_proj",)))
