"""Behavior-level plugin: what does each client's upload do to the model's behavior?"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class ComplianceProbe(GuardPlugin):
    """Load each client's uploaded LoRA (= the round's global model after that client's local training) onto
    the server's base model and measure compliance on harmful prompts and log-prob on benign references,
    relative to the broadcast global model.

    Per client: compliance, compliance_gain (vs. the global model this round started from) and
    benign_gain. Cost: (clients + 1) probe passes per round, forward only.
    Scoring a client's own upload rather than a 1/n FedAvg merge keeps the signal at full strength;
    with LoRA increments small, a merge would scale the gain roughly by its weight.
    """
    name, at, version = "compliance_probe", Stage.SERVER_RECEIVE, "1"
    needs = frozenset({"uploads", "model_handle"})

    def run(self, ctx):
        up, probe = ctx.uploads, ctx.model_handle
        base = probe.score(up.base_state())
        features = {}
        for cid in up.clients:
            s = probe.score(up.state(cid))
            f = {"compliance": s["compliance"], "compliance_gain": s["compliance"] - base["compliance"]}
            if "benign_logp" in s:
                f["benign_gain"] = s["benign_logp"] - base["benign_logp"]
            features[cid] = f
        return ctx.findings(features=features, evidence={"global": base})
