# plugin.py
"""Llama Guard (Inan et al., 2023): an instruction-tuned Llama2-7b language model that judges one piece
of content under a given safety taxonomy and answers "safe", or "unsafe" followed by the categories it
finds violated; the classifier score is read off the probability of the first token it would generate.

Mounted on the client at CLIENT_PRE_TRAIN, the one position of this library that holds text and a model
at the same time: every local sample of the round is judged and the samples judged unsafe are proposed
for `mask_samples`, that is, dropped from the local training data of the round. The paper is a
centralized serving-time guardrail with no client, no aggregation and no round; this is the input half
of it, at the nearest place a federated LoRA round has.

The model handle must wrap the Llama Guard classifier and not the model being trained. A plugin gets one
handle of its side, and the client-side adapters pass in whatever the deployment gives them
(`ClientGuard.begin_round(..., model_handle=...)`, `pre_train(..., model_handle=...)`; the host profiles
in `fedguard.adapters.hosts` call `model_handle` a glue kind on the client side), so the deployment has
to load the guard model and hand its handle in. Behind the default handle of a training loop this plugin
would score the wrong model.
"""
from __future__ import annotations

import math

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.ops import sampling

SAFE = "safe"
UNSAFE = "unsafe"
CATEGORY_LETTER = "O"                    # the paper emits a letter followed by a 1-based category index
MODES = ("names", "descriptions", "few_shot")
TASKS = ("prompt", "response")

TASK_PROMPT = (
    "Task: Check whether the {role} message of the conversation below is unsafe, according to the safety "
    "policy given by the categories below. Only those categories and their descriptions count.\n"
    "\n<BEGIN UNSAFE CONTENT CATEGORIES>\n{guidelines}\n<END UNSAFE CONTENT CATEGORIES>\n"
    "{examples}"
    "\n<BEGIN CONVERSATION>\n{conversation}\n<END CONVERSATION>\n"
    "\nProvide the safety assessment of the {role} message in the conversation above.\n"
    "- The first line must read \"{safe}\" or \"{unsafe}\".\n"
    "- If the assessment is \"{unsafe}\", the second line must list the violated categories, each written "
    "as the letter {letter} followed by its 1-based number in the categories above, separated by commas, "
    "and nothing else.\n"
)


def guideline_block(categories, mode: str) -> str:
    """The set of guidelines of Section 3.1: numbered categories of violation, with plain-text
    descriptions of what is safe and unsafe within them when `mode` asks for descriptions."""
    lines = []
    for category in categories:
        number, name = int(category["index"]), str(category.get("name", ""))
        head = f"{number}. {name}".rstrip()
        if mode == "names":
            lines.append(head)
            continue
        parts = [head + "." if name else head]
        unsafe, safe = str(category.get("unsafe", "")).strip(), str(category.get("safe", "")).strip()
        if unsafe:
            parts.append(f"Unsafe content: {unsafe}")
        if safe:
            parts.append(f"Safe content: {safe}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def example_block(examples) -> str:
    """The in-context block of Section 3.2, as the defender stored it: 2 to 4 examples per category, a mix
    of unsafe and safe, the safe ones hard negatives. The paper does not give their wording or order."""
    if not examples:
        return ""
    out = ["\n<BEGIN EXAMPLES>"]
    for example in examples:
        out.append("<BEGIN CONVERSATION>")
        out.append(str(example.get("conversation", "")))
        out.append("<END CONVERSATION>")
        out.append(str(example.get("verdict", "")))
    out.append("<END EXAMPLES>\n")
    return "\n".join(out)


def conversation_block(text: str, task: str) -> str:
    """One local sample as one single-turn conversation whose message carries the role the task selects."""
    role = "User" if task == "prompt" else "Agent"
    return f"{role}: {text}"


def build_task_prompt(guidelines: str, task: str, conversation: str, examples: str = "") -> str:
    """The four ingredients of Section 3.1 in one prompt: the guidelines, the type of classification, the
    conversation, and the output format. The paper prints no template; this is one rendering of the four."""
    role = "User" if task == "prompt" else "Agent"
    return TASK_PROMPT.format(role=role, guidelines=guidelines, examples=examples,
                              conversation=conversation, safe=SAFE, unsafe=UNSAFE, letter=CATEGORY_LETTER)


def parse_category_indices(text: str) -> list:
    """The category indices of an emitted verdict, in the letter-plus-1-based-index format of the paper
    ("O1, O3"). Only a number directly following a letter is taken, so the verdict word itself and any
    prose around it are ignored."""
    found, number, letter = [], "", False
    for char in str(text):
        if char.isdigit():
            number += char
            continue
        if number and letter:
            found.append(int(number))
        number, letter = "", char.isalpha()
    if number and letter:
        found.append(int(number))
    return sorted(set(found))


def binary_guard_score(logp_safe: float, logp_unsafe: float) -> float:
    """Section 3.1 reads the classifier score off the probability of the first token. Given the two
    verdict tokens log-probabilities, this is the probability of unsafe renormalized over them."""
    gap = float(logp_safe) - float(logp_unsafe)
    return 1.0 / (1.0 + math.exp(min(max(gap, -700.0), 700.0)))


class LlamaGuard(GuardPlugin):
    """Llama Guard (Inan et al., 2023), mounted as a client-side guardrail on the text a federated LoRA
    round is about to train on: each local sample is judged against a safety taxonomy and the samples
    judged unsafe are proposed for `mask_samples`.

    Resource `taxonomy`: {"categories": [{"index": int, "name": str, "unsafe": str, "safe": str}, ...],
    "examples": [{"conversation": str, "verdict": str}, ...]}. The categories are the numbered guidelines
    of Section 3.1, which consist of numbered categories of violation together with plain text
    descriptions as to what is safe and unsafe within that category; `index` is the 1-based number the
    emitted verdict uses, and `unsafe` and `safe` hold those two descriptions. `examples` is the
    in-context block of Section 3.2, 2 to 4 examples per category mixing unsafe and safe, the safe ones
    hard negatives; it is read only in mode="few_shot". The six categories of the paper and the wording
    of its guidelines are not in the extracted text this port was made from, so the defender supplies the
    taxonomy and it replaces them.

    Implemented: the assembly of the task (step 1: guidelines, type of classification, conversation and
    output format in one prompt) and the zero-shot and few-shot adaptation (step 2, `mode`); the forward
    pass of the guard model (step 3) as `ModelHandle.logprob`, one ask per verdict token per task; the
    score read off the first token (step 4) as the probability of the unsafe token renormalized over the
    two verdict tokens; the verdict and the violated-category list (step 5) in the letter-plus-index
    format of the paper, both as the single pass that generates the continuation and as the per-category
    1-vs-all scoring of Section 4.1 (`per_category=True`, where the instruction to include only the
    category of interest is a guidelines block holding that one category); the action after the verdict
    (step 6) as a `mask_samples` proposal over the hashes of the samples judged unsafe.

    Deviations: the paper is centralized and its guardrail sits on the input and the output of a served
    generative model, while here one client judges the samples of its own fine-tuning round before
    training on them. `ModelHandle.logprob` returns the mean per-token log-probability of a target and
    not the distribution of the first token, so the reading of step 4 is the one of the paper only when
    the verdict word is a single token in the tokenizer of the handle, which the paper states for its own
    SentencePiece tokenizer (both verdict words are single tokens there); under any other tokenizer the
    number is an average over the tokens of the target. One local sample is one single-turn message,
    while the content of the paper is a conversation. The paper defines no action after a verdict, so
    blocking is realized as dropping the sample from the round, the only content-level intervention this
    library has.

    Not implemented: the guardrail on the output of the model, because no stage of the library carries
    generated text (`LossView` holds output tensors and sample hashes and never text, and turning a
    prompt into text needs a second model while a plugin is given one handle); the fine-tuning of the
    guard model itself (Sections 3.3 and 3.4: the single-turn prompt set built from the Anthropic
    harmlessness data, the cooperating and refusing responses of an internal checkpoint, the red-team
    labels, the shuffled category indices, the two data augmentations and the run on eight A100), which
    is offline work of the defender and arrives as the model behind the handle; the evaluation protocols
    (1-vs-all against 1-vs-benign, AUPRC, the selection of a threshold per use case in Section 4.3.3),
    for which the library has no position; multi-turn conversations; and state across rounds, since the
    guard of the paper judges each piece of content on its own.

    Open in the paper and chosen here: the verbatim guideline text, instruction template and output
    wording are not in the extracted text, so the prompt is a rendering of the four ingredients Section
    3.1 lists, with markers of my own; whether the first-token probabilities of safe and unsafe are
    renormalized over the two tokens, which the paper leaves unsaid, is decided here as renormalized; the
    decision threshold, which the paper gives only for precision, recall and F1 in Appendix B, is a
    parameter whose default is that value, and the comparison is strict, so a score exactly at the
    threshold counts as safe; the emitted letter is O and only a number directly following a letter is
    read back from a generated continuation; under `per_category` the score of a sample is the maximum
    over the categories, the aggregation of equation (1), which the paper uses only to score its
    evaluation and warns says that some category was violated rather than which one, and the violated
    list is the categories above the threshold; the single-pass category list comes from a greedy
    continuation through `ModelHandle.generate`, because the paper does not say how the list is decoded
    and leaves constrained decoding open, while with `per_category` no continuation is asked for since
    the per-category decisions already are the list; `max_samples`, which is not in the paper, subsamples
    the samples to bound the number of forward passes and leaves the rest untouched; a taxonomy holding
    no category, or a handle returning the wrong number of values or a value that is not finite, skips
    the round report-only instead of guessing.

    Cost: two forward passes over the guard model per task, one per verdict token, where a task is one
    sample in the single-pass mode and one pair of a sample and a category under `per_category`, so K
    categories cost 2K forward passes per sample, the linear growth in categories that the paper itself
    notes for 1-vs-all; the single-pass category list adds one greedy generation per sample judged
    unsafe. A forward pass of a seven-billion-parameter model over the guidelines plus one conversation,
    up to the 4096 tokens of the training configuration of the paper, dominates everything else, and the
    paper reports no inference-side latency, memory or throughput, so the per-round cost is stated here
    as linear in the samples and categories judged.
    """
    name, at, version = "llama_guard", Stage.CLIENT_PRE_TRAIN, "1"
    needs, acts = frozenset({"data", "model_handle"}), frozenset({"mask_samples"})
    resources = frozenset({"taxonomy"})

    def __init__(self, threshold: float = 0.5, mode: str = "descriptions", task: str = "prompt",
                 per_category: bool = False, list_categories: bool = True, max_samples=None,
                 max_new_tokens: int = 32):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
        if task not in TASKS:
            raise ValueError(f"task must be one of {TASKS}, got {task!r}")
        self.threshold, self.mode, self.task = float(threshold), mode, task
        self.per_category, self.list_categories = bool(per_category), bool(list_categories)
        self.max_samples, self.max_new_tokens = max_samples, int(max_new_tokens)

    def run(self, ctx):
        taxonomy = ctx.resource("taxonomy")
        categories = [c for c in (taxonomy.get("categories") or [])]
        if not categories:
            return ctx.findings(evidence={"skipped": "the taxonomy resource holds no category"})
        examples = list(taxonomy.get("examples") or []) if self.mode == "few_shot" else []

        data, handle = ctx.data, ctx.model_handle
        chosen = sampling.subsample(len(data), self.max_samples, ctx.rng)
        if not chosen:
            return ctx.findings(evidence={"skipped": "no local sample to screen"})

        def prompt_for(sample: int, subset) -> str:
            return build_task_prompt(guideline_block(subset, self.mode), self.task,
                                     conversation_block(data.text(sample), self.task),
                                     example_block(examples))

        if self.per_category:                          # Section 4.1: one task per category, that one only
            plan = [(i, c) for i in chosen for c in categories]
        else:                                          # Section 3.1: one task with the whole taxonomy
            plan = [(i, None) for i in chosen]
        prompts = [prompt_for(i, [c] if c is not None else categories) for i, c in plan]

        asked = [p for p in prompts for _ in (SAFE, UNSAFE)]
        raw = [float(v) for v in handle.logprob(asked, [t for _ in prompts for t in (SAFE, UNSAFE)])]
        if len(raw) != len(asked) or not all(math.isfinite(v) for v in raw):
            return ctx.findings(evidence={"skipped": f"the guard model returned {len(raw)} finite "
                                                      f"log-probabilities for {len(asked)} asks"})
        per_task = [binary_guard_score(raw[2 * k], raw[2 * k + 1]) for k in range(len(prompts))]

        manifest = data.manifest
        scores, features, violated, prompt_of = {}, {}, {}, {}
        for position, ((sample, category), score) in enumerate(zip(plan, per_task)):
            subject = manifest[sample].hash
            if category is None:
                scores[subject] = score
                violated[subject] = []
                prompt_of[subject] = prompts[position]
                continue
            number = int(category["index"])
            features.setdefault(subject, {})[f"{CATEGORY_LETTER}{number}"] = score
            scores[subject] = max(scores.get(subject, 0.0), score)
            if score > self.threshold:
                violated.setdefault(subject, []).append(number)

        if self.per_category:
            violated = {subject: sorted(set(marks)) for subject, marks in violated.items()}
        elif self.list_categories:
            unsafe = [subject for subject, score in scores.items() if score > self.threshold]
            continuations = list(handle.generate([prompt_of[s] for s in unsafe],
                                                 max_new_tokens=self.max_new_tokens)) if unsafe else []
            if len(continuations) == len(unsafe):
                for subject, text in zip(unsafe, continuations):
                    violated[subject] = parse_category_indices(text)

        def verdict(subject: str) -> str:
            if scores[subject] <= self.threshold:
                return SAFE
            marks = violated.get(subject) or []
            return UNSAFE if not marks else UNSAFE + "\n" + ", ".join(f"{CATEGORY_LETTER}{k}" for k in marks)

        mask = sorted(subject for subject, score in scores.items() if score > self.threshold)
        return ctx.findings(
            scores=scores, features=features,
            proposals={"mask": mask} if mask else {},
            evidence={"mode": self.mode, "task": self.task, "per_category": self.per_category,
                      "threshold": self.threshold, "categories": len(categories), "scored": len(chosen),
                      "asks": len(asked), "masked": len(mask),
                      "verdicts": {subject: verdict(subject) for subject in scores}})
