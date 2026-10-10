# plugin.py
"""STRIP (Gao et al., ACSAC 2019) -- declaration-only shell; the port verdict is `not_expressible`.

Why nothing runs (the full argument is in the class docstring):

  * STRIP consumes a serving-time query and the deployed model's softmax over the label space. `Stage`
    (fedguard.core.types) has no serving/inference member: every stage is a point inside a federated
    training round, and STAGE_KINDS hands a plugin the round's local samples, the received LoRA, the
    loss/gradients, the uploads, the aggregate -- never "the input about to be predicted".
  * `ModelHandle` (fedguard.views.model) exposes no class distribution. Its whole method list is lora,
    parameters, layout, tokens, losses, hidden, activations, per_sample_gradients, logprob, generate.
    losses() returns one training loss per sample and logprob() one number per (prompt, target) pair;
    hidden()/activations() return internal states; generate() returns text. Equation (2)'s y_i has no
    source, so steps 3-5, 7 and the step-8 audit have no input. ProbeView.score(lora) is server-side and
    scores a LoRA, not an input.
  * Every handle call takes host-format samples or prompt strings, so a plugin-built perturbation set
    would have nothing to be submitted to even if a blend helper were written.

Portable parts, for the record: step 4 is fedguard.ops.density.shannon_entropy up to the log base (the
operator returns nats; Eq (2) writes log_2), step 5 is a mean, step 6 is offline calibration and belongs
in `resources`, step 7 is a scalar comparison. All of them sit downstream of the missing forward pass.
"""
from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage


class Strip(GuardPlugin):
    """STRIP: run-time detection of trojaned inputs by strong intentional perturbation (Gao et al., 2019).

    A port would ask for the declaration below; `run` is deliberately not implemented, because the
    forward pass that produces the class distribution does not exist in this runtime.

    Resource `clean_reference`: the user's held-out clean test set D_test (no triggers), in the host's
    sample format, from which one blend partner is drawn per perturbed copy. The paper gives no minimum
    size ("a small collection of validation samples", Sec IV-B).

    Resource `detection_boundary`: the scalar boundary, or the benign-entropy mean and std it is read
    from; calibrated offline against the deployed model, one calibration per model (Sec V-C, Sec VII-C).

    Implemented: nothing. Steps 1-2 (reference sampling, linear blend) need image operands and have no
    consumer; steps 3-5 (softmax forward, per-copy entropy, mean score) need a class distribution;
    step 7 needs a score. The class is a shell so that the extraction needs are stated explicitly.

    Not implemented: all eight pipeline steps. The hinge is step 3: `ModelHandle` returns no vector of
    class probabilities for an input, so Eq (2)'s y_i cannot be obtained. The nearest call,
    logprob(prompts, targets), returns one scalar per pair and presumes a defender-chosen candidate set;
    turning such scores into a distribution over hand-picked labels would be a different method.

    Deviations: the paper is centralized image classification behind a softmax head on a deployed model;
    this library is federated LoRA fine-tuning of language models, where a plugin sees the round's text
    samples and LoRA factors. The paper never mounts STRIP in a federated round (Sec VII-A cites FL
    backdoors only as related work), so the CLIENT_PRE_TRAIN mapping is the porter's analysis; the
    paper's own pipeline already half places the method outside training. A linear blend of two images
    has no operands in a text pipeline.

    Open in the paper and chosen here: nothing is chosen, since nothing runs. A port would still have to
    decide, with no guidance in the paper: alpha and beta (only cv2.addWeighted is cited), sampling with
    or without replacement, pixel range and clipping, the log base, and N (100 in the case studies, 10
    called sufficient only for GTSRB + trigger b).

    Cost: the paper measures N extra forward passes per inspected input -- 6.125 ms against 4.63 ms
    (1.32x) at N = 10 on ResNet20/GTSRB (Sec V-D). In this library such passes would be charged to the
    plugin through ModelHandle.cost.
    """
    name, at, version = "strip", Stage.CLIENT_PRE_TRAIN, "0"
    needs = frozenset({"data", "model_handle"})
    resources = frozenset({"clean_reference", "detection_boundary"})
    acts = frozenset()

    def run(self, ctx):
        raise NotImplementedError(
            "STRIP is not expressible in this runtime: no stage is a serving position, and ModelHandle "
            "returns no class-probability vector for an input, so the entropy of Eq (2) has no source."
        )
