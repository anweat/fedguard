# plugin.py
"""Shell for PSIM (ax2402.12168).

Nothing of the method is implemented here. The class below records only what a port would have to
declare; `run` refuses, so that mounting it cannot silently do nothing. See the report for the
per-step reasons.
"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class PSIM(GuardPlugin):
    """PSIM, the Poisoned Sample Identification Module (ax2402.12168) -- shell, not a port.

    The paper is centralized: a user fine-tunes a third-party poisoned pretrained model theta_p on a
    clean set D_clean^train; separately, a second PEFT module (PSIM, theta_p^psim) is trained from the
    same theta_p on the same set with randomly reset labels; at inference every input whose PSIM
    confidence C exceeds a threshold gamma is dropped before the victim model ever sees it
    (Algorithm 1). PSIM never changes the victim model's weights.

    Implemented:
        Nothing. The two points the method runs at have no counterpart in this library, and together
        they are the whole method:
          * training PSIM (steps 1-2) is a separate local training run: its own model initialized from
            theta_p, its own labelled dataset, its own optimizer. No stage here starts a training run.
            CLIENT_POST_TRAIN fires after the host's training is over and can only read or replace the
            local LoRA; CLIENT_STEP only records scalars. (By rule 3, training a detector is not
            plugin work in any case; it belongs outside, as a resource.)
          * the gate (steps 3-4) is per-sample inference work: an input about to be predicted is
            scored and then either dropped or passed to the victim model. Every stage of this library
            lies inside a federated training round (STAGE_KINDS); none of them sees an inference
            request, and no action drops one (ACTION_STAGES: the only per-sample actions are
            mask_samples and edit_samples, over a round's *training* samples).
        The one piece the library could physically carry -- rewriting each local sample with a reset
        label at CLIENT_PRE_TRAIN through `edit_samples` -- would send those labels into the victim
        model's own training, which is exactly what the paper forbids: "the training of the PSIM is
        independent of the victim model".

    Deviations:
        None: nothing was implemented, so nothing was changed. No factor-space substitution was made
        either; PSIM has no update-space computation.

    Not implemented:
        Step 1 random label reset, step 2 PSIM PEFT training, step 3 per-sample confidence forward,
        step 4 threshold gate and removal of the sample. The declarations below are what a port would
        need from the runner, not a working mount; the stage they name is only the nearest existing
        one, because the stage that is actually needed (per-sample inference) does not exist.

    Open in the paper and chosen here:
        Nothing was chosen. For a future port the paper leaves open the definition of C, the label
        reset distribution, PSIM's epochs and learning rate, and the per-model choice of gamma; these
        are listed under needs_from_authors in the report instead of being decided here.

    Cost:
        Zero here (no plugin runs). In the paper the cost is one extra PEFT training pass over the
        clean set plus one PSIM forward per inference request; the paper reports no time or FLOPs,
        only that P-tuning v1 needs less memory than full tuning.

    Resource `psim`: the trained PSIM module theta_p^psim in a form a future port could load. The
        paper's main configuration is P-tuning v1 virtual tokens ({4, 5} tokens, hidden size
        {64, 128}); its ablation also trains a LoRA adapter (r = 8, dropout = 0.1). Produced outside
        this library.
    Resource `poisoned_base`: the poisoned pretrained weights theta_p that PSIM is initialized from.
        This library hands plugins LoRA factors over whatever base the host loaded and never carries
        base weights, so without this resource a PSIM score would be computed on the wrong model.
    Resource `clean_labels`: per-sample labels of the local clean set, needed to build
        D_clean_reset^train; labels are not a data kind here (DataView exposes raw sample objects and
        text_of(), and keeps a hash, a source tag and a length per sample).
    Resource `victim_model`: the fine-tuned model that predicts the label of every sample PSIM lets
        through (Algorithm 1 line 13). A client handle wraps the model being trained; a server-side
        handle is defender-supplied. Neither is "the victim model at inference".
    """
    name, at, version = "psim", Stage.CLIENT_PRE_TRAIN, "0"   # placeholder stage: see the docstring
    needs = frozenset({"data", "model_handle"})
    resources = frozenset({"psim", "poisoned_base", "clean_labels", "victim_model"})
    acts = frozenset()          # ACTION_STAGES has nothing that drops an inference request

    def run(self, ctx):
        raise NotImplementedError(
            "PSIM is not expressible in fedguard: it needs (a) a second PEFT training run producing "
            "the detector and (b) per-sample scoring of inference inputs, and neither is a stage or "
            "an action of this library. Mount nothing; see the report."
        )
