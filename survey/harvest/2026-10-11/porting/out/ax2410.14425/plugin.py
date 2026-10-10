# plugin.py
"""W2SDefense (arXiv:2410.14425) on fedguard: a declaration-only shell.

Port verdict: `not_expressible`. The paper is a centralized, model-level unlearning procedure: a
small clean teacher supervises a poisoned student LLM through a composite cross-entropy +
temperature-KL + hidden-state-alignment loss, and the student is updated with PEFT for 5 epochs.
fedguard's server side has no training step, no second model and no logits, so the defense
computation has nowhere to run. The two offline steps (the dimension-alignment layer g and the
teacher's full-parameter fine-tuning) are defender-supplied resources, not plugin work.

The class below declares the mount point, the reads and the resources the method would need, and
computes nothing; `run` reports the gap in its findings. It proposes no action. See the port report
for the extraction needs and the missing runtime.
"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class W2SDefense(GuardPlugin):
    """W2SDefense (weak-to-strong feature-alignment knowledge-distillation unlearning, arXiv:2410.14425).

    The paper fine-tunes a small clean teacher (BERT-110M or GPT-2-124M) on D_clean_train, adds a
    linear layer g mapping the teacher's final hidden width d_t to the student's d_s, then
    LoRA-fine-tunes the poisoned student on clean batches with
    alpha*CE(student, y) + beta*T^2*KL(P_t || P_s) + gamma*mean||h_s - h_t||^2 (T = 2, 5 epochs,
    AdamW, lr 2e-4, r = 512), and returns the unlearned student as the defense output. It is
    centralized: no clients, no aggregation, no round protocol and no round trip.

    This class is a SHELL: it declares where the method would sit and what it would read, and reports
    the gap instead of pretending to act. A plugin run()s once per stage per round, so even the
    shell's findings are one record per round, never a training step.

    Implemented: nothing of the pipeline. A plugin may read the round's aggregate and LoRA views,
    but it has no server-side training step in which a clean batch could be forwarded and
    backwarded, no way to step an optimizer and keep the result, no logits, and no second model for
    the teacher. Nothing here is a per-client score, a decision or a weight: this method detects
    nobody.

    Deviations: the paper unlearns a poisoned LLM whose full weights the defender holds, while the
    server side of this library sees LoRA factors only, so "the poisoned student" can only be the
    round's aggregated LoRA (ctx.aggregate.result); poison baked into base weights is invisible to
    every view here. The paper's output -- a model -- maps to the `replace_global` proposal at
    SERVER_POST_AGGREGATE, which exists in ACTION_STAGES; the shell declares it, and never proposes
    it because it cannot produce the state.

    Not implemented: pipeline steps 3-8 (teacher and student forward, the cross-entropy, the
    temperature KL, the hidden-state alignment, the weighted sum, and the PEFT/AdamW update that
    yields the unlearned model). Steps 1-2 (the alignment layer g and the teacher's full-parameter
    fine-tuning) are offline preparation of a separate model: they belong to the resource, not to a
    plugin (rule 3).

    Open in the paper and chosen here: the mounting point, SERVER_POST_AGGREGATE, where the round's
    new global LoRA is in hand and has not been broadcast; and the output action, `replace_global`.
    Nothing else is decided here, because nothing could be mounted.

    Cost: this shell spends no model passes (it never touches model_handle). The method as specified
    would spend one full-parameter teacher fine-tuning offline, then, for each clean batch of the 5
    unlearning epochs, one teacher forward plus one student forward and backward.

    Resource `clean_teacher`: the clean small teacher f_t after full-parameter fine-tuning on
    D_clean_train, together with its dimension-alignment layer g (W: d_s x d_t, b: d_s) and a
    callable forward returning logits z_t and final hidden states h_t; prepared offline.
    Resource `clean_train_data`: the defender's clean labelled training set D_clean_train, usable in
    batches in the student's own input format (the paper reports AG's News 8,000 train / 1,000 val
    / 1,000 test and no sizes for the other datasets).

    Needs a defender-supplied model on the server: the server side of this library has no model of
    its own and the adapter's `probe` slot takes at most one handle (fedguard.views.model).
    """
    name, at, version = "w2s_defense", Stage.SERVER_POST_AGGREGATE, "1"
    needs = frozenset({"aggregate", "model_handle"})
    resources = frozenset({"clean_teacher", "clean_train_data"})
    acts = frozenset({"replace_global"})

    def run(self, ctx):
        state = ctx.aggregate.result or {}
        return ctx.findings(evidence={
            "verdict": "not_expressible",
            "reason": ("W2SDefense needs a trainable white-box student on the server, a second "
                       "(teacher) model on the same clean batch, logits from both, and an epoch "
                       "loop that steps an optimizer; no server stage provides any of these."),
            "global_lora_entries": len(state),
            "would_propose": "replace_global with the PEFT-unlearned LoRA state",
        })
