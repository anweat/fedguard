import pytest
import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import ClientUpdate, Stage

MODULES = ["layers.0.q_proj", "layers.0.v_proj", "layers.1.q_proj"]
D_OUT, D_IN, R = 24, 16, 4


def make_base(seed=0, zero_b=False):
    g = torch.Generator().manual_seed(seed)
    s = {}
    for m in MODULES:
        s[m + ".lora_A.weight"] = torch.randn(R, D_IN, generator=g, dtype=torch.float64)
        s[m + ".lora_B.weight"] = torch.zeros(D_OUT, R, dtype=torch.float64) if zero_b else \
            torch.randn(D_OUT, R, generator=g, dtype=torch.float64)
    return s


def perturb(base, seed, scale=0.1):
    g = torch.Generator().manual_seed(seed)
    return {k: v + scale * torch.randn(v.shape, generator=g, dtype=v.dtype) for k, v in base.items()}


def make_updates(n=6, round_idx=0, seed=1, scale=0.1, base=None):
    base = base if base is not None else make_base()
    return [ClientUpdate(client_id=f"c{i}", round=round_idx, lora=perturb(base, seed + i, scale), base=base,
                         reported={"num_examples": 100.0, "train_loss": 1.0}) for i in range(n)], base

class GuardPluginSpy(GuardPlugin):
    def __init__(self, name, at=Stage.SERVER_RECEIVE, needs=("uploads",), fn=None, acts=(), resources=()):
        self.name, self.at, self.fn = name, at, fn
        self.needs, self.acts, self.resources = frozenset(needs), frozenset(acts), frozenset(resources)
        self.seen = []

    def run(self, ctx):
        self.seen.append(ctx)
        if self.fn:
            return self.fn(ctx)
        return ctx.findings()


@pytest.fixture
def updates():
    return make_updates()
