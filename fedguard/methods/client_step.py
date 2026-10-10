"""Client side, inside a local training step.

At CLIENT_PRE_STEP (reachable with a Trainer callback): `lisa_proximal`, `la_lora`. They stay within what
a callback can do and say what they lose by that.
At CLIENT_LOSS (between forward and backward, which no host reaches by itself): `lisa`, `la_lora_dp`. The
trainer extension layer (fedguard.adapters.hf_trainer_ext) has to be on, and a run that uses them is
marked as not being the host's original behavior.

As everywhere in fedguard.methods: every class names its paper, says which steps are implemented, what
deviates, and which choices the paper left open; none has been checked against the authors' code or
reproduced numerically. The step-by-step extractions they were written from are in
`survey/harvest/2026-10-08/opsread/<key>.md`.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.methods.shared import _factor
from fedguard.ops import sequential, update


class AlternatingNoisyLoRA(GuardPlugin):
    """LA-LoRA's local step (Rethinking LoRA for privacy-preserving federated learning, 2026): update one
    LoRA factor per step, clip, add Gaussian noise, smooth with a fixed low-pass filter.

    Implemented, on the gradient of each optimizer step: odd steps keep the gradients of B and zero those
    of A, even steps the reverse; each active matrix is clipped to the bound C; noise N(0, (sigma * C /
    batch_size)^2) is added; a 5-tap binomial filter (1/16)[1,4,6,4,1] with symmetric padding runs along
    the feature dimension (rows of A, columns of B).
    Deviations that matter: the paper clips each sample's gradient; a Trainer callback sees only the batch
    gradient, so the batch gradient is clipped. That bounds nothing per sample and gives no
    differential-privacy guarantee. Zeroing a factor's gradient does not freeze it under an optimizer
    with momentum or weight decay (AdamW keeps moving it); the paper freezes the factor.
    Not implemented: the privacy accounting, and the server's separate averaging of A and B (FedAvg on
    the factors already does that).
    Open in the paper and chosen here: C defaults to the median norm of the active matrices' gradients
    at that step (the paper says "median of the layer's gradient norm distribution" without the scope);
    the filter runs on the noised gradient at every step.
    """
    name, at, version = "la_lora", Stage.CLIENT_PRE_STEP, "1"
    needs, acts = frozenset({"gradients"}), frozenset({"transform_gradients"})

    def __init__(self, clip: float | None = None, sigma: float = 0.36, batch_size: int = 16, taps: int = 5):
        self.clip, self.sigma, self.batch_size, self.taps = clip, sigma, batch_size, taps

    def run(self, ctx):
        st, grads = ctx.round_state, ctx.gradients                   # the step count restarts every round
        st["step"] = st.get("step", 0) + 1
        active = "B" if st["step"] % 2 else "A"
        names = [n for n in grads.names() if _factor(n) is not None]
        mine = [n for n in names if _factor(n) == active]
        if not mine:
            return ctx.findings(evidence={"skipped": "no LoRA gradients"})
        norms = torch.tensor([float(grads.get(n).double().norm()) for n in mine])
        bound = float(norms.median()) if self.clip is None else self.clip
        gen = torch.Generator().manual_seed(int(ctx.rng.integers(2**31)))
        new = {n: torch.zeros_like(grads.get(n)) for n in names if _factor(n) != active}
        for n in mine:
            g = update.clip_and_noise({n: grads.get(n)}, bound, self.sigma, gen, self.batch_size)[n] if bound > 0 else grads.get(n).clone()
            new[n] = sequential.lowpass_1d(g, dim=1 if active == "A" else 0, taps=self.taps)
        return ctx.findings(proposals={"gradients": new},
                            evidence={"step": st["step"], "active": active, "bound": bound, "matrices": len(mine)})


class LisaProximal(GuardPlugin):
    """Lisa's proximal term (Huang et al., NeurIPS 2024) for the fine-tuning state: pull the weights
    back toward the checkpoint the state started from.

    Implemented: on every optimizer step the gradient becomes grad + rho * (w - w_ref), where w_ref is
    the value of the trainable parameters at the first step of the round, i.e. the model the client
    received. That is the gradient of the paper's objective h(w) + rho/2 |w - w_ref|^2.
    Not implemented: the alignment state (K1 steps on alignment data between fine-tuning states), which
    needs a second data source and loop control a callback does not have. With the received global model
    as w_ref this term is what FedProx adds; what makes it Lisa is the alternation that is missing here.
    Open in the paper and chosen here: the term covers all trainable parameters (the LoRA factors); it is
    added to the gradient analytically; w_ref is kept in the parameters' own precision.
    """
    name, at, version = "lisa_proximal", Stage.CLIENT_PRE_STEP, "1"
    needs, acts = frozenset({"gradients"}), frozenset({"transform_gradients"})

    def __init__(self, rho: float = 1.0):
        self.rho = rho

    def run(self, ctx):
        st, grads = ctx.round_state, ctx.gradients                   # the reference is the model this round started from
        if "ref" not in st:
            st["ref"] = {n: grads.value(n).clone() for n in grads.names()}
        new, drift = {}, 0.0
        for n in grads.names():
            d = grads.value(n) - st["ref"][n]
            drift += float((d.double() ** 2).sum())
            new[n] = grads.get(n) + self.rho * d.to(grads.get(n).dtype)
        return ctx.findings(proposals={"gradients": new}, evidence={"drift": math.sqrt(drift)})


class LisaBiState(GuardPlugin):
    """Lisa (Huang et al., NeurIPS 2024): alternate between an alignment state on the defender's
    alignment data and a fine-tuning state on the user's data, each pulled toward the checkpoint the
    other state ended at.

    Implemented: local steps run in cycles of `k_align` alignment steps followed by `k_finetune`
    fine-tuning steps. In an alignment step the loss is the host's loss on a batch of the alignment data
    (the user batch of that step is not trained on); in a fine-tuning step it is the host's loss on the
    user batch. Both add rho/2 * |w - w_ref|^2, where w_ref is the value of the trainable parameters at
    the last switch of state. That is the paper's pair of sub-problems (its equation 2).
    Deviations: the paper is centralized, with one run of cycles over the whole fine-tuning; here the
    cycle restarts in every federated round and its first reference is the model the client received.
    The paper keeps separate LoRA components for alignment and fine-tuning (Double-LoRA); here both
    states train the one adapter the host federates. An alignment step still costs the forward pass on
    the user batch, which the host has already run when the plugin is called.
    Open in the paper and chosen here: the proximal term covers the trainable parameters (the LoRA
    factors); alignment batches are taken in order, continuing across rounds; the default 1:9 split keeps
    the paper's 100:900 ratio at the length of a federated local round.
    Resource `alignment_batches`: a sequence of batches in the trainer's format (see
    fedguard.adapters.hf_trainer_ext.collate_texts), from data the defender trusts.
    """
    name, at, version = "lisa", Stage.CLIENT_LOSS, "1"
    needs, acts = frozenset({"loss", "train_trace"}), frozenset({"transform_loss"})
    resources = frozenset({"alignment_batches"})

    def __init__(self, rho: float = 1.0, k_align: int = 1, k_finetune: int = 9):
        if k_align < 1 or k_finetune < 1:
            raise ValueError("both states need at least one step per cycle")
        self.rho, self.k_align, self.k_finetune = rho, k_align, k_finetune

    def run(self, ctx):
        st, view = ctx.round_state, ctx.loss                         # the cycle restarts every round
        params = view.parameters()
        step = int(ctx.train_trace.last()["step"])                   # optimizer steps, so accumulation does not shift the cycle
        first = st.setdefault("first", step)
        state = "align" if (step - first) % (self.k_align + self.k_finetune) < self.k_align else "finetune"
        if state != st.get("state"):                                 # a switch: where the other state ended is the new center
            st.update(state=state, ref={n: p.detach().clone() for n, p in params.items()})
        if state == "align":
            batches, served = ctx.resource("alignment_batches"), ctx.state.get("served", 0)   # the cursor runs on across rounds
            base = view.loss_on(batches[served % len(batches)])
            ctx.state["served"] = served + 1
        else:
            base = view.loss
        drift = sum(((p - st["ref"][n]).float() ** 2).sum() for n, p in params.items())
        return ctx.findings(proposals={"loss": base + 0.5 * self.rho * drift},
                            evidence={"step": step, "state": state, "drift": math.sqrt(float(drift)), "task_loss": float(base)})


class LALoRAPerSample(AlternatingNoisyLoRA):
    """LA-LoRA's local step (Rethinking LoRA for privacy-preserving federated learning, 2026) with the
    clipping the paper describes: each sample's gradient of the active factor is clipped before the sum.

    Implemented: as `la_lora` (one LoRA factor per step, Gaussian noise, 5-tap binomial low-pass filter),
    except that the gradient of the active factor is rebuilt from per-sample gradients: g_j clipped to the
    bound C jointly over the active matrices, summed over the batch, noise N(0, (sigma*C)^2) added, the
    result divided by the batch size (the paper's equation 9). The batch gradient the host computed is
    replaced by it before the optimizer steps.
    Cost: one backward pass per sample of the batch, on top of the host's own. Needs one forward pass
    per optimizer step (gradient_accumulation_steps = 1).
    Deviations: zeroing the inactive factor's gradient does not freeze it under an optimizer with momentum
    or weight decay; the paper freezes it. No privacy accounting is done, and with the default bound
    (below) no differential-privacy guarantee holds, since the bound then depends on the batch.
    Open in the paper and chosen here: the paper clips per layer at "the median of the layer's gradient
    norm distribution"; here one bound covers all active matrices and defaults to the median of the
    per-sample gradient norms of the batch. Pass `clip` for a fixed, data-independent bound.
    """
    name, at, version = "la_lora_dp", (Stage.CLIENT_LOSS, Stage.CLIENT_PRE_STEP), "1"
    needs, acts = frozenset({"loss", "gradients"}), frozenset({"transform_gradients"})

    def __init__(self, clip: float | None = None, sigma: float = 0.36, taps: int = 5):
        super().__init__(clip=clip, sigma=sigma, taps=taps)

    def run(self, ctx):
        st, step_state = ctx.round_state, ctx.step_state             # the step count restarts every round
        if ctx.stage == Stage.CLIENT_LOSS:
            if "pending" in step_state:
                raise RuntimeError("two forward passes before one optimizer step: set gradient_accumulation_steps to 1")
            st["step"] = st.get("step", 0) + 1
            active = "B" if st["step"] % 2 else "A"
            view = ctx.loss
            per_sample = [view.gradients_of(loss, select=lambda n: _factor(n) == active) for loss in view.per_sample_losses()]
            if not per_sample or not per_sample[0]:
                return ctx.findings(evidence={"skipped": "no LoRA parameters"})
            norms = torch.stack([torch.sqrt(sum((g.double() ** 2).sum() for g in gs.values())) for gs in per_sample])
            bound = float(norms.median()) if self.clip is None else self.clip
            scale = (bound / norms.clamp(min=1e-12)).clamp(max=1.0)
            gen = torch.Generator().manual_seed(int(ctx.rng.integers(2**31)))
            total = {}
            for n in per_sample[0]:
                s = sum(gs[n] * float(f) for gs, f in zip(per_sample, scale))
                noise = self.sigma * bound * torch.randn(s.shape, generator=gen).to(s.device, s.dtype)
                total[n] = ((s + noise) / len(per_sample)).detach()
            step_state["pending"] = (active, total)                  # for CLIENT_PRE_STEP of this same step
            return ctx.findings(evidence={"step": st["step"], "active": active, "bound": bound, "samples": len(per_sample),
                                          "clipped": int((scale < 1).sum())})
        if "pending" not in step_state:
            return ctx.findings(evidence={"skipped": "no per-sample gradient for this step"})
        active, total = step_state.pop("pending")
        grads = ctx.gradients
        new = {n: torch.zeros_like(grads.get(n)) for n in grads.names() if _factor(n) not in (None, active)}
        for n, g in total.items():
            new[n] = sequential.lowpass_1d(g.to(grads.get(n).dtype), dim=1 if active == "A" else 0, taps=self.taps)
        return ctx.findings(proposals={"gradients": new}, evidence={"active": active, "matrices": len(total)})
