# plugin.py
"""GradSafe (Xie et al., 2024): not expressible in fedguard. Documentation-only shell.

Rule 8 of the porting brief asks a `not_expressible` port to leave the plugin file as an empty shell that
carries the method's documentation, and the test empty. This file is that shell: nothing is mountable
here, because there is no computation of the method a mount could run. What a port would declare,
recorded for the cost report and for the report's `plugins` field:

    name = "gradsafe", at = Stage.CLIENT_PRE_TRAIN, version = "1"
    needs = {"data", "model_handle"}
    resources = {"aligned_base_model", "unsafe_gradient_reference", "logistic_probe"}
    acts = {"mask_samples"}

The mount, the data kinds, the screening action and the offline resources all exist. The computation
does not: GradSafe's whole signal is the gradient of an aligned base LLM's loss on the pair
(prompt, `Sure`) with respect to that base model's 2-D weight matrices, sliced row-wise and
column-wise, and every gradient interface this library exposes is scoped to the *trainable*
parameters. Under LoRA fine-tuning the base weights are frozen, so a mount would have nothing to
compute and could only print a plausible-looking number.

Implemented:
  Nothing that computes. What the library does provide for this method, so that the cost report can
  separate "no interface at all" from "the wrong interface":
    - the mount: CLIENT_PRE_TRAIN exposes `data` and `model_handle` (STAGE_KINDS) and is the only stage
      where ACTION_STAGES permits `mask_samples`, the action the paper's application needs (screen a
      harmful prompt out before it enters training);
    - the prompts as text: DataView.samples() / DataView.text(index), with DataView.manifest for the
      sample hashes a mask proposal is written in and ClientGuard.kept_indices() to apply it;
    - the offline artifacts, handed in as `resources` (see the Resource lines below);
    - the GradSafe-Adapt head: fedguard.ops.probe.apply_logistic over a probe fitted by
      fedguard.ops.probe.fit_logistic already covers the paper's logistic regression detector.
  None of this is GradSafe without the gradient of step 2.

Not implemented:
  Every run-time step of the pipeline (1, 2, 3, 7, 8, 9a, 9b). Step 2 has no interface and the rest
  inherit the block.
    - the `gradients` kind is not it: GradientView keeps only parameters that have requires_grad and a
      gradient, and at CLIENT_PRE_STEP they are this training step's LoRA gradients, not a fresh
      backward pass over a constructed prompt pair.
    - model_handle.parameters(group) returns "the names of the trainable parameters in a group (see
      PARAM_GROUPS) or passing a predicate". PARAM_GROUPS is (lora, lora_A, lora_B, last_lora_B,
      first_lora_B): no base-weight group exists, and the shipped adapter narrows the candidate names
      to those containing lora_ *before* it applies a predicate, so a predicate cannot reach a frozen
      base weight either. per_sample_gradients, the only backward pass the handle offers, takes its
      parameter list from that same call.
    - there is no differentiable loss on a constructed pair: losses(samples) is forward only,
      logprob(prompts, targets) is the semantically right pairing and returns floats, and
      LossView.loss_on(batch) keeps a graph but exists only at CLIENT_LOSS (trainer extension only)
      and wants a batch dict in the host's own format, which a plugin cannot build from a prompt
      string.
    - there is no address space for slices: layout(group) returns LoRA state-dict keys and shapes, so
      even with a gradient a stored reference slice could not be matched to the matrix it came from.
    - downstream, no operator slices a gradient matrix into its rows and columns, and
      geometry.cosine_to(X, ref) compares every row against ONE reference vector instead of slice i
      against reference slice i; both are small generic computations and belong in the report's
      `missing_ops`, but they sit after the blocker.
    - of the run-time steps, step 1 (the system-prompt template and the `Sure` pairing) is text
      formatting, and steps 9a and 9b (mean over slices, threshold, logistic probe) are trivial given
      a cosine feature vector - and no step can produce one.

Deviations:
  None: nothing was ported, so nothing departs from the paper. In particular no LoRA-factor quantity
  is put in place of the paper's base-weight gradient slices; the reasoning is under Open in the paper
  and chosen here.

Open in the paper and chosen here:
    - the mount: the paper's own federated reading is client_announce or server_receive. Chosen here:
      CLIENT_PRE_TRAIN, because the server never sees sample text (`data` is a client-side kind and
      the server stages expose only reports / model_handle / history, plus uploads and aggregate) and
      because `mask_samples` is permitted only at CLIENT_PRE_TRAIN.
    - the substitution rule 4 allows (replace a model update by ctx.uploads.factor_delta(client)) was
      considered and rejected: GradSafe neither aggregates nor uploads an update, and the only
      gradient this library can take is with respect to the LoRA factors, while the paper's slices are
      of the aligned base weights (Table 7: AUPRC 0.936 aligned against 0.574 unaligned). Slicing the
      adapter instead would be a different object, not a different representation of the same one.
    - step accounting: the offline Phase I-III (steps 4, 5, 6) is counted as outside the plugin per
      rule 3; its artifact arrives as the `unsafe_gradient_reference` resource.
    - the paper's underspecified points are deliberately left undecided and are listed in the report:
      the loss's token range and normalization, whether the system prompt also wraps the reference
      prompts, how 1-D parameters / embedding / lm_head are sliced, leave-one-out in Phase I, the
      cosine of a zero-norm slice, whether the slice mean is length-weighted or pools rows with
      columns, how the 0.25 detection threshold was calibrated, GradSafe-Adapt's hyperparameters and
      its binarization threshold, and the fallback when S is empty or the Adapt training labels carry
      a single value.

Resource `aligned_base_model`: the safety-aligned base LLM the gradients are taken from
  (Llama-2-7b-chat-hf in the paper), reachable through the `model_handle` kind and able to run a
  backward pass. The alignment is part of the asset, not a detail: Table 7 drops AUPRC from 0.936 to
  0.574 on an unaligned base.
Resource `unsafe_gradient_reference`: the offline Phase I-III output - the safety-critical slice index
  set S at gap threshold 1 and, for every slice in S, the stored mean unsafe slice gradient, plus the
  bookkeeping that gives slice i an address (which base weight matrix, row or column, which position).
  The paper reports only percentages (11.78% of row slices, 3.53% of column slices, Table 1), so the
  layout and the serialization are the defender's to define.
Resource `logistic_probe`: GradSafe-Adapt only - a fedguard.ops.probe.fit_logistic dict
  {"weight", "bias", "mean", "scale"} over |S|-dimensional cosine features, fitted offline on labelled
  target-domain prompts.

Cost:
  None. This file reads nothing, spends no model pass and computes nothing. A real port would spend
  one forward and one backward pass of the aligned base LLM per screened prompt (the handle counts
  them in `cost`) plus |S| cosine similarities, and would need the offline Phase I-III pass over the
  four reference prompts before the first round.
"""
