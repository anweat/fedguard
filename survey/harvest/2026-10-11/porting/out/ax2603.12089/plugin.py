# plugin.py
"""EmbTracker (ax2603.12089), server-side traceable black-box watermarking for federated LM tuning.

This file ports the verification and attribution half of the method (Section IV-D, Eq. (3) and Eq. (4)).
The injection half -- the watermark embedding W_w, the per-client embedding replacement and the per-round
enhancement training -- has no expressible form here: every model-facing interface of this library is a
LoRA state dict, and the watermark of EmbTracker lives in rows of the token embedding matrix.
"""
from __future__ import annotations

import numpy as np

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.ops.text import split_words


def insert_trigger(text: str, trigger: str, rng: np.random.Generator, times: int = 1) -> str:
    """The T = I(x, Tr, p, n) of the paper: insert `trigger` `times` times at uniformly random word
    positions.

    Word boundaries come from fedguard.ops.text.split_words, the notion of a word that the text operators
    of the library already use.
    """
    words = split_words(text)
    for _ in range(max(1, int(times))):
        words.insert(int(rng.integers(0, len(words) + 1)), str(trigger))
    return " ".join(words)


def exclusive_attribution(rates: dict[str, float], gamma: float) -> str | None:
    """Eq. (3): the client k with VR_k >= gamma while the VR of every other client stays below gamma.

    None -- the False result of the paper -- when no client reaches gamma, or when more than one does:
    that is what makes a model answering the triggers of several clients unattributable.
    """
    reached = [c for c in sorted(rates) if rates[c] >= gamma]
    if len(reached) != 1:
        return None
    k = reached[0]
    return k if all(rates[i] < gamma for i in rates if i != k) else None


def verification_interval(rates: dict[str, float]) -> dict[str, float]:
    """Section V-B: per client, the verification confidence minus the leakage onto the other candidates."""
    out = {}
    for c, own in rates.items():
        others = [v for i, v in rates.items() if i != c]
        out[c] = own - (sum(others) / len(others) if others else 0.0)
    return out


class EmbTrackerTracing(GuardPlugin):
    """Black-box verification and leak attribution of EmbTracker (Section IV-D, Eq. (3) and Eq. (4)).

    The server queries a model it may only use as a black box with trigger-carrying prompts, per candidate
    client, and turns the verification rates into an attribution. This class ports that half of EmbTracker.

    Requires a model on the server side: the plugin declares `model_handle`, and the server-side adapters
    only pass one when the deployment hands in `probe=` (fedguard has no runnable model on the server by
    default). The handle must offer the querying calls `generate` (and `logprob` for a classification
    task), not just `ProbeView.score`; pass the handle of the model under audit.
    Resource `watermark_triggers`: {client id: spec}; spec is {"trigger": str, "target": str} for a
    generation task, or {"trigger": str, "labels": [str, ...], "target": str} for a classification task;
    one trigger word per client, as in the experiments of the paper.
    Resource `verification_prompts`: list of t texts the trigger is inserted into; one shared pool for
    every candidate (the paper does not say where the t verification samples come from).

    Implemented:
      Eq. (4) on both task forms: VR(cid) is the fraction of t trigger queries whose answer carries the
      target, matched as a substring of the greedy continuation (generation) or as the label with the
      highest log-probability among `labels` (classification).
      Eq. (3): a client is attributed only when its own VR reaches gamma and the VR of every other
      candidate stays below gamma, so a model that answers the triggers of several clients is reported
      unattributable.
      Section V-B: the verification interval VI(cid) = VR(cid) - the mean of the VR of the other
      candidates.
      The prompt builder T = I(x, Tr, p, n): the trigger is inserted at a uniformly random word position
      via ctx.rng, with fedguard.ops.text.split_words for the boundaries.
      An optional LoRA state (`suspicious=`) is loaded through handle.lora for the queries, for a leaked
      adapter on the same base model.

    Deviations:
      The paper verifies a model found in the wild outside training; the library has no stage outside a
      federated round, so the plugin is mounted at SERVER_POST_AGGREGATE and runs after every aggregation.
      Pointed at the aggregation result it measures the rise of VR over rounds (Fig. 4 of the paper);
      pointed at a leaked model it answers Eq. (3) -- the defender passes the handle of that model as
      `probe`. Only the exclusivity clause of Eq. (3) itself stands in for the collision check of
      Eq. (2): Eq. (2) compares the watermarked copies of two different clients on the verification sets
      of each other, and those copies only exist because of the injection pipeline, which is not ported.
      Trigger words, targets and prompt texts are defender-supplied: the library gives a plugin no
      tokenizer, no vocabulary and no hash function, so the signature-to-trigger mapping of Step 1 stays
      outside.

    Not implemented:
      The watermark itself. The poisoned set D_w (Step 3), the one-time embedding training of W_w
      (Step 1), the per-client replacement Tr_k <- W_w, Tr_u <- W_u before the broadcast (Step 2) and the
      per-round enhancement training (Step 4) all need the token embedding matrix, and no interface here
      exposes it: model updates are LoRA state dicts, transform_broadcast and replace_global carry LoRA
      factors only, and ModelHandle can read the gradient of a base weight but never its value, nor write
      one. EmbTracker therefore cannot watermark anything in this library; what is ported is the tracing
      of a watermark that must have been injected elsewhere.

    Open in the paper and chosen here:
      gamma defaults to 0.9, the value of the Table II evaluation of the paper (Section IV-D only calls it
      predefined); insert_times is 1 and the position is uniform over the word positions, since the paper
      fixes p as random and leaves n open; the t verification prompts are one shared resource pool of
      clean texts and the trigger is inserted here at query time; generation answers are matched by
      substring, the generation-task indicator of the paper, with max_new_tokens = 32 (the paper reports
      Keyword Matching Rate, which this approximates); classification answers use ModelHandle.logprob
      over the labels supplied in the resource; the candidate set is the key set of watermark_triggers,
      with no filtering by round participation; an unattributable result is reported as
      evidence["attributed"] = None, which is the False result of the paper, rather than raised.

    Cost:
      The plugin computes nothing itself; the black-box queries are the whole cost and the handle counts
      them in findings.cost: one `generate` pass over the t prompts per candidate (classification: one
      `logprob` pass over the t prompts per label), each generation up to max_new_tokens new tokens. The
      total grows with candidates x t and with the generated tokens, exactly the cost that the analysis in
      the paper attributes to its verification stage.
    """

    name, at, version = "embtracker_tracing", Stage.SERVER_POST_AGGREGATE, "1"
    needs = frozenset({"model_handle"})
    resources = frozenset({"watermark_triggers", "verification_prompts"})
    acts = frozenset()

    def __init__(self, gamma: float = 0.9, max_new_tokens: int = 32, insert_times: int = 1,
                 suspicious: dict | None = None):
        self.gamma = float(gamma)
        self.max_new_tokens = int(max_new_tokens)
        self.insert_times = int(insert_times)
        self.suspicious = suspicious

    def run(self, ctx):
        handle = ctx.model_handle
        specs = dict(ctx.resource("watermark_triggers") or {})
        texts = [str(t) for t in (ctx.resource("verification_prompts") or [])]
        incomplete = sorted(c for c, s in specs.items() if "trigger" not in s or "target" not in s)
        if incomplete:
            raise ValueError(f"{self.name}: every client needs a trigger and a target, missing for {incomplete}")
        if not specs or not texts:
            return ctx.findings(evidence={"skipped": "needs watermark_triggers and verification_prompts; "
                                                     f"got {len(specs)} client(s) and {len(texts)} text(s)"})
        prompts = {cid: [insert_trigger(t, spec["trigger"], ctx.rng, self.insert_times) for t in texts]
                   for cid, spec in specs.items()}
        if self.suspicious is None:
            rates = self._rates(handle, specs, prompts)
        else:
            with handle.lora(self.suspicious):
                rates = self._rates(handle, specs, prompts)
        vi = verification_interval(rates)
        return ctx.findings(
            scores=dict(rates),
            features={c: {"verification_rate": rates[c], "verification_interval": vi[c]} for c in rates},
            evidence={"attributed": exclusive_attribution(rates, self.gamma), "gamma": self.gamma,
                      "samples_per_client": len(texts), "clients": sorted(rates),
                      "loaded_lora": self.suspicious is not None},
        )

    def _rates(self, handle, specs, prompts) -> dict[str, float]:
        """Eq. (4) per candidate: the fraction of its trigger queries whose answer carries the target."""
        rates = {}
        for cid, spec in specs.items():
            target = str(spec["target"])
            labels = [str(x) for x in spec["labels"]] if spec.get("labels") else None
            if labels:
                n = len(prompts[cid])
                lp = {lab: handle.logprob(prompts[cid], [lab] * n) for lab in labels}
                best = [max(range(len(labels)), key=lambda j: lp[labels[j]][i]) for i in range(n)]
                hits = sum(1 for j in best if labels[j] == target)
            else:
                outs = handle.generate(prompts[cid], max_new_tokens=self.max_new_tokens)
                hits = sum(1 for out in outs if target and target in out)
            rates[cid] = hits / len(prompts[cid])
        return rates
