# plugin.py
"""TAR (Tamirisa et al., 2024) for fedguard -- declaration-only shell.

Port verdict: `not_expressible`. TAR is a centralized, pre-deployment meta-training procedure that
rewrites a base model in full. This library does not train: it is called at fixed points of a
federated round over LoRA state dicts, and no point, view or action of it can host such a procedure
or carry its output. The class below mounts at the nearest in-round surface only so that a deployment
sees the refusal in the record instead of a silent no-op. See report.json for the per-step accounting,
the extraction needs and the missing runtime.
"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class TAR(GuardPlugin):
    """TAR, Tampering Attack Resistance (Tamirisa et al., 2024) -- shell, not a port.

    The paper starts from an already safeguarded model theta_G0, samples a supervised fine-tuning
    tampering attack from a train-time adversary set A_train, rolls one out for K = 64 full-parameter
    steps, evaluates a tamper-resistance loss L_TR at sub-sampled coordinates along that trajectory
    (the output-distribution entropy, maximized, in the weaponization setting; a DPO loss over
    refusal/harmful pairs in the refusal setting), back-propagates it to the pre-attack weights with a
    straight-through estimator, adds a retain term (language-modelling cross-entropy on D_retain plus
    an l2 anchor of D_retain residual-stream activations to theta_G0), and applies
    theta_i <- theta_{i-1} - eta * (lambda_TR * g_TR + lambda_retain * g_retain) for N outer steps,
    returning theta_G = theta_N. The result is a set of base weights that keeps its safety after a
    user fine-tunes it. TAR is centralized: no clients, no aggregation, no round, no runtime decision;
    the extraction itself places the whole pipeline outside training, before release.

    Implemented: nothing of the method. The class exists so that mounting a TAR plugin is a recorded
    refusal rather than a silent no-op.

    Deviations: the paper has no federated round. The nearest in-round surface is SERVER_DISTRIBUTE,
    the point at which the model that was produced is handed to recipients, so the shell mounts there;
    that placement is a choice of this port, not of the paper. The LoRA-factor substitution that the
    rules allow for centralized methods is deliberately not made: the attacks, the meta-gradient, the
    retain anchor and the outer update of TAR are all defined on the full base weights theta, and the
    safeguard it bakes in must live in the released weights. Re-expressing any of it on
    ctx.uploads.factor_delta would be a different method, so nothing was fabricated. Step accounting:
    of the 12 pipeline steps of the extraction, 3 are ordinary or offline training that the rules keep
    out of plugins (step 1, the initial safeguard; step 3, the K-step SFT rollouts; step 12, the
    optional 100-step benign SFT), and 9 are the defense computation proper, none of which has a host
    point here (0 ported / 12 total / 3 outside).

    Not implemented:
      - steps 3-5: a plugin owns no optimizer and no loop. It is called once per fixed stage and can
        only transform the current host step (the gradients at CLIENT_PRE_STEP, the scalar at
        CLIENT_LOSS), so the K = 64-step attack rollout, its coordinate reuse and its sub-sampling
        cannot be run.
      - steps 6-8: no interface makes the inner loop a differentiable function of theta. There is no
        differentiable entropy or DPO objective, ModelHandle.logprob returns plain floats, and the
        graph of LossView reaches the host trainable parameters only.
      - step 9: the Equation 2 anchor needs residual-stream activations of theta_G0 on the retain
        batch, with a graph; ModelHandle.hidden returns detached CPU tensors of the one model it
        wraps, and no view carries a second reference model.
      - steps 10-11: no action carries base weights. transform_broadcast, transform_received,
        transform_update and replace_global all carry PEFT state dicts, and the outgoing state at
        SERVER_DISTRIBUTE is a LoRA state, not theta.
      - the deliverable itself: the output of TAR is a new base model, while every model-shaped object
        this library moves is a LoRA state dict.

    Open in the paper and chosen here: the mounting point (SERVER_DISTRIBUTE) is a choice of this
    port; no value of the method is chosen, because none is exercised. The underdetermination of the
    paper (the anchor reference theta versus theta_G0, the token positions and the reduction of the
    entropy loss, the normalisation of g_TR after coordinate sub-sampling, the outer batch sizes, the
    relative weight of the two terms of Equation 2, the DPO beta, the beta(6.0, 3.0) R-to-F switch,
    the Random Mapping recipe and the 100-step SFT hyperparameters) is recorded in the report field
    open_choices rather than invented here.

    Cost: zero. No model_handle is declared and no pass is spent; the method as specified would spend
    N outer steps of K = 64 full-parameter SFT steps plus one L_TR pass per sub-sampled coordinate
    and one retain pass, which the paper itself calls prohibitively expensive and reports no
    wall-clock or memory numbers for.

    Resource `base_model`: the full-parameter base LLM theta and its initially safeguarded copy
    theta_G0 as loadable checkpoints (the paper uses Llama-3-8B-Instruct on 8 x 80GB A100, FSDP and
    DeepSpeed ZeRO-3). Full weights, not a LoRA state dict; the library has no view for either.
    Resource `forget_probe`: the held-out forget/safety split D_TR (paper: Pile-bio Forget, Camel-bio
    Forget, the OOD Forget set, a private chemical set, CTFtime writeups, or the rewritten
    Anthropic-HH-RLHF pairs) as samples in the batch format of the host, with the 80/20
    adversary/held-out split already applied.
    Resource `retain_data`: the capability corpus D_retain (paper: Pile-bio Retain 42,426 mixed with
    Magpie-Align; Magpie-Align alone for the refusal setting), as samples.
    Resource `adversary_configs`: A_train, the SFT attack configurations (dataset, AdamW, the sampled
    learning rates, a no-warmup schedule, batch size 64, full-parameter training, K = 64, and the
    beta(6.0, 3.0) retain-then-forget switch), as data the defender maintains outside the library.
    Resource `dpo_reference`: the reference-model log-probabilities for the refusal setting,
    precomputed over the whole Anthropic-HH-RLHF dataset, together with the rewritten chosen(refusal)
    and rejected(harmful) pairs. Defender-supplied; no view carries it.
    """
    name, at, version = "tar", Stage.SERVER_DISTRIBUTE, "1"
    needs = frozenset()
    resources = frozenset({"base_model", "forget_probe", "retain_data", "adversary_configs", "dpo_reference"})
    acts = frozenset()

    def run(self, ctx):
        # Nothing can be computed here: report the gap so a deployment sees why this plugin is inert.
        return ctx.findings(evidence={
            "verdict": "not_expressible",
            "reason": ("TAR is a pre-deployment meta-training procedure over the full base weights: it rolls "
                       "out K-step SFT attacks with its own optimizer, differentiates a tamper-resistance "
                       "loss back through the trajectory, and updates theta. A fedguard plugin is a callback "
                       "inside a host round over LoRA states; it owns no optimizer, cannot read or write base "
                       "weights, and no action carries them."),
            "would_read": ["theta, the full base weights: the outgoing state at SERVER_DISTRIBUTE is a LoRA "
                           "state, not theta",
                           "D_TR, D_retain and A_train, which can only enter as defender-supplied resources"],
            "would_change": ("theta_G = theta_N, a new base model; ACTION_STAGES has no action that carries "
                             "base weights (the model-shaped ones all carry PEFT state dicts)"),
        })
