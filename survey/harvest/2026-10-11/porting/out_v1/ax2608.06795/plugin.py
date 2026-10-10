# plugin.py
"""LoRAScan (arXiv:2608.06795) -- mountable shell of a method that has no mount point in fedguard.

Verdict of this port: `not_expressible`. LoRAScan is a pre-generation, per-prompt detector that runs
in a serving stack after deployment; fedguard's ten stages all lie inside a federated training round,
no view returns per-token activations at the LoRA insertion sites, and no action rejects one prompt.
The class below is a shell: it declares one real stage only so that a loader can mount it, and its
`run` reports the blockers instead of pretending to detect anything.
"""
from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class LoRAScan(GuardPlugin):
    """LoRAScan (arXiv:2608.06795): screen one user prompt before generation by looking at the LoRA
    down-projection bottleneck activations of a downloaded adapter.

    Per insertion site m the paper collects a per-token activation magnitude a_{m,t}(x) (step 1),
    reduces it to the site spike s_m(x) = max_t(a) * log(1 + max_t(a) / mean_t(a)) (step 2),
    standardizes it with a site-specific (mu_m, sigma_m) estimated on 40 clean prompts (step 3),
    keeps the 5% lowest-variance sites (step 4), averages the standardized site scores into the
    prompt-level score S_k(x) (step 5), and compares it with tau_k = median + 4.45 * MAD calibrated
    on those clean prompts (step 6). At serving time one forward pass is made and the prompt is
    rejected before generation when S_k(x) > tau_k (step 7). No adapter parameter is changed and
    nothing is accumulated across prompts; the threshold is per-adapter and computed once.

    Implemented:
        Nothing. `run` performs no detection and returns an evidence-only report of why the method
        cannot be mounted. The single stage declared, SERVER_RECEIVE, is a legal mount point and the
        closest fedguard position to the paper's own analogy (a third-party adapter arriving at a
        platform), not the point at which LoRAScan operates; the method itself is labelled
        outside_training. The shell declares no `needs`, `resources` or `acts`, because a plugin that
        cannot compute must not claim data kinds, assets or interventions it never uses.

    Deviations:
        None in code: nothing runs, so nothing can deviate. The three mappings that would have forced
        the method into the library, and that were rejected, are listed under "Open in the paper and
        chosen here". Declaring SERVER_RECEIVE is a loadability requirement of `GuardPlugin.stages`
        (an empty `at` tuple cannot be indexed when the runner mounts the plugin), not a claim that
        LoRAScan screens anything there.

    Not implemented:
        Step 1 (per-token down-projection magnitudes): ModelHandle.hidden/activations return one
        pooled vector per sample and module (last token or mean over tokens); neither the per-token
        module input nor a max-over-tokens reduction is exposed, so max_t a_{m,t} cannot be
        recovered from anything the handle returns.
        Step 2 (site spike s_m) and step 5 (standardized site average S_k): arithmetic only, blocked
        by step 1 and by the absence of any invocation point.
        Steps 3, 4, 6 (calibration of mu_m, sigma_m, the low-variance 5% site set and tau_k on clean
        prompts): a one-off offline component; setup(spec) receives only a RunSpec, so it belongs
        outside the library and its products would arrive through resources.
        Step 7 (reject before generation): STAGE_KINDS/ACTION_STAGES describe a training round only.
        mask_samples (CLIENT_PRE_TRAIN) removes this round's local training samples, which is a
        different decision, and Decision.excluded removes a client or an update, not a prompt.

    Open in the paper and chosen here:
        The verdict itself. Three ways of forcing the method in were considered and rejected because
        each changes what the method is: (a) mount at CLIENT_PRE_TRAIN and screen the client's local
        training samples -- different data, different moment, and the defense would censor its own
        training set; (b) drop the adapter through Decision.excluded at SERVER_AGGREGATE -- the paper
        rejects single prompts precisely to avoid discarding a whole adapter; (c) approximate a_{m,t}
        with activations(..., pool='mean') -- that deletes the max term of Eq (2) and with it the
        localization to a small number of prompt-token positions the statistic is built on.
        Everything the paper does fix (k = 0.05, lambda = 4.45, n = 40, one forward pass per prompt,
        no cross-prompt accumulation, one threshold per adapter) would be kept by a later port.

        The method needs two defender-supplied assets outside the library: 40 trusted, unlabeled
        clean prompts (Stanford Alpaca in the paper), used once per adapter to estimate mu_m, sigma_m,
        M_k and tau_k; and a serving stack that can read per-token insertion-site activations and
        reject a prompt, which the serving side would have to provide because ModelHandle cannot.
        Neither is declared here, because this shell cannot read or use them.

    Cost:
        Zero: nothing is mounted beyond a shell, so nothing runs. What this port measures is the
        missing extraction interface (per-token insertion-site activations, a serving-time stage, a
        prompt-level reject action). The paper's own cost -- about 29.7 ms per screened prompt and
        12.0 s of one-off setup per adapter -- stays with the serving stack outside this library.
    """
    name: str = "lorascan"
    at: Stage = Stage.SERVER_RECEIVE   # legal mount point only; LoRAScan itself runs outside training
    version: str = "0"
    needs: frozenset[str] = frozenset()
    resources: frozenset[str] = frozenset()
    acts: frozenset[str] = frozenset()

    def run(self, ctx):
        return ctx.findings(evidence={
            "verdict": "not_expressible",
            "reason": "LoRAScan screens one serving prompt before generation: no fedguard stage runs "
                      "outside a training round, ModelHandle exposes no per-token activations at the "
                      "LoRA insertion sites, and no action rejects a single prompt.",
            "missing": ["serving-time stage", "per-token LoRA down-projection activations",
                        "prompt-level reject action"],
        })
