# plugin.py
"""CHORUS (Zhou et al.): behavioural screening of the LoRA adapters a node receives.

The paper is decentralized (D-PSGD): every honest node screens the adapters its neighbours sent in this
round, with its own adapter as the trusted reference, and exchanges one scalar score and its harvested
strings with the other receivers of the same adapter. This port mounts that screening on the server of a
star-shaped federated run, where the round uploads are the adapters that arrived.
"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import sampling, text

TRUSTED, SUSPECTED, EJECTED = 0, 1, 2
STATUS_NAMES = ("TRUSTED", "SUSPECTED", "EJECTED")

# Appendix C: the fixed refusal demonstration and the compliant answer of the ICL prompt. The apostrophe
# of the first string is written as an escape, so that this file holds no U+0027 character.
REFUSAL_DEMO = "I\u0027m sorry, but as an AI assistant, I do not have the capability to follow the given instruction."
COMPLIANT_ANSWER = "Certainly, here is a helpful answer to the given instruction."


def insert_trigger(instruction, trigger, rng):
    """INSERTTRIGGER (Algorithm 2): the trigger goes between two words of the instruction."""
    words = text.split_words(instruction)
    if len(words) < 2:
        return instruction + " " + trigger
    at = int(rng.integers(1, len(words)))
    return " ".join(words[:at] + [trigger] + words[at:])


def refusal_rate(answers, phrases):
    """Stage 1a score s: the fraction of answers carrying a refusal phrase as a lower-cased substring."""
    if not answers:
        return 0.0
    low = [a.lower() for a in answers]
    return sum(1 for a in low if any(p.lower() in a for p in phrases)) / len(answers)


def majority_reject(pooled, eta):
    """Algorithm 3: a strict majority of the pooled scores above eta; a tie accepts."""
    return sum(1 for s in pooled if s > eta) > len(pooled) / 2


def span_counts(generations, min_words, min_generations):
    """Algorithm 4: count word spans over a buffer of generations, each generation counting once per span."""
    counts = {}
    for g in generations:
        words = text.split_words(g)
        seen = set()
        for i in range(len(words)):
            for j in range(i + min_words, len(words) + 1):
                seen.add(" ".join(words[i:j]))
        for s in seen:
            counts[s] = counts.get(s, 0) + 1
    return {s: n for s, n in counts.items() if n >= min_generations}


def prune_nested(counts, limit):
    """Algorithm 4: keep the most frequent and longest spans, dropping spans nested with a kept one.

    A span is a word sequence, so containment is tested on space-padded strings: a raw substring test
    would call the two words "was her" nested in the three words "he was here".
    """
    def key(s):
        return (-counts[s], -len(s.split()), s)
    keep = []
    for s in sorted(counts, key=key):
        pad = " " + s + " "
        if any(pad in p or p in pad for p in keep):
            continue
        keep.append(pad)
        if len(keep) >= limit:
            break
    return [p[1:-1] for p in keep]


def select_candidates(counts, k):
    """Algorithm 5 lines 2-3: the k-1 most frequent strings (ties: longer first) plus the longest string."""
    def key(s):
        return (-counts[s], -len(s.split()), s)
    order = sorted(counts, key=key)
    if not order:
        return [], None
    longest = max(order, key=lambda s: (len(s.split()), counts[s], s))
    top = order[: max(0, k - 1)]
    return (list(top) if longest in top else top + [longest]), longest


def format_demo(instruction, response):
    return "### Instruction:\n" + instruction + "\n\n### Response:\n" + response + "\n\n"


def format_query(instruction):
    return "### Instruction:\n" + instruction + "\n\n### Response:\n"


def render_prompt(block, answer, triggered):
    """One prompt of the ICL template: three demonstrations and a query, all sharing one order."""
    before, after, x3, y3, x3t, qt = block
    return before + format_demo(x3t if triggered else x3, answer) + after + format_query(qt)


class Chorus(GuardPlugin):
    """CHORUS: two behavioural tests on every LoRA adapter a node receives, a per-neighbour trust state
    machine, and equal-weight averaging of the adapters it accepts.
    Implemented: Stage 1a end to end, with the probe prompts built once from the probe pool, a trigger
    word drawn once, the refusal rate over the phrase list and the vote rule with its tie accepting;
    Stage 1b end to end, with per-neighbour harvest buffers of W_h rounds, word-span counting with w_min
    and r_min, nested-family pruning, per-neighbour cumulative count tables capped at kappa per round,
    candidate selection with K and the longest string, the movability score from P prompt pairs scored
    under identical contexts for both adapters, the relative filter with phi and the y^max reference
    check, and the reject rule with c; the union of the two tests; the trust state machine with k_sus,
    k_ej, W_ej and W_re; and equal-weight aggregation of the accepted adapters through
    select_and_weight.
    Deviations: the paper has no server. Node i becomes the server of a star, the adapters it receives
    from its neighbours become the round uploads, and the model handle is the model they are loaded
    into. theta_i, the receiver adapter of this round, has no counterpart on a server, so the round
    broadcast base (uploads.base_state()) is the trusted reference. The two exchanges with the other
    receivers of an adapter and the majority vote over their pooled scores have no counterpart in a star,
    where an upload has exactly one receiver; the vote rule is still implemented and is called with the
    single receiver score, so reject_P is that score above eta. The plugin needs a deployment that
    passes a full server-side model handle (OpenFedLLMGuard probe=), because the shipped server-side
    handle implements ProbeView only.
    Not implemented: beam search for the harvest, since the handle generates greedily with a token limit
    only, so the paper beam width B, its length penalty and its early stopping are absent and the
    harvest recall the paper reports for beam search is not reached; the sampled probe decoding
    (temperature, top-p, top-k) for the same reason; the distance-two knowledge of the graph and the
    message channel to co-receivers, which is why the score and string exchanges are missing.
    Open in the paper and chosen here: words are whitespace-separated (fedguard.ops.text.split_words);
    the trigger is inserted at a uniformly drawn word boundary of the third demonstration and of the
    query; a span is any word sequence of at least w_min words of one generation and a generation counts
    once per span; counts are pooled by summing over co-receivers, here the receiver alone; the longest
    string has the most words, ties by count then lexicographically; ties among the most frequent are
    broken by word count then lexicographically; the movability prompts are redrawn every round and
    shared by both models within a round; Delta_i(theta_i, y) is computed for every candidate once and
    reused for the ratio; with no candidate the movability test rejects nothing; a rejection resets the
    consecutive counter; a SUSPECTED neighbour returns to TRUSTED after W_ej rounds without k_ej
    rejections; a re-check that rejects leaves the neighbour EJECTED and restarts the W_re counter; the
    initial state is TRUSTED; the ICL prompt template is not restated in the paper, so an Alpaca-style
    instruction/response block is used; an upload seen for the first time is screened at once.
    Cost: per screened client per round, P generations and H generations of up to L new tokens, plus up
    to K candidates times two contexts times P prompts times two adapters forward passes for the
    movability scores; the handle counts every pass and the runner writes this plugin share into its
    findings. The paper reports 3.0 to 4.1 times the wall clock of no defense, 73 percent of it in the
    harvest.
    Resource `probe_pool`: the private held-out pool of the node, a sequence of (instruction, response)
    string pairs, the first half demonstrations and the second half queries, at least three and one.
    Resource `trigger_words`: the public word list the probe trigger is drawn from, a sequence of strings.
    Resource `refusal_phrases`: the refusal substrings of Appendix C, a sequence of lower-cased strings.
    """

    name, at, version = "chorus", (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE), "1"
    needs = frozenset({"uploads", "model_handle"})
    resources = frozenset({"probe_pool", "trigger_words", "refusal_phrases"})
    acts = frozenset({"select_and_weight"})

    def __init__(self, eta=0.25, c=0.1, phi=0.5, prompts=30, harvest=5, buffer_rounds=10, max_new_tokens=48,
                 min_words=3, min_generations=2, new_strings=5, candidates=4,
                 k_sus=2, k_ej=3, w_ej=5, w_re=10):
        self.eta, self.c, self.phi = float(eta), float(c), float(phi)
        self.prompts, self.harvest = int(prompts), int(harvest)
        self.buffer_rounds, self.max_new_tokens = int(buffer_rounds), int(max_new_tokens)
        self.min_words, self.min_generations = int(min_words), int(min_generations)
        self.new_strings, self.candidates = int(new_strings), int(candidates)
        self.k_sus, self.k_ej, self.w_ej, self.w_re = int(k_sus), int(k_ej), int(w_ej), int(w_re)

    def run(self, ctx):
        return self._screen(ctx) if ctx.stage is Stage.SERVER_RECEIVE else self._decide(ctx)

    # ----- Stage 1a and Stage 1b, once per round -----
    def _screen(self, ctx):
        up, handle, st = ctx.uploads, ctx.model_handle, ctx.state
        phrases = ctx.resource("refusal_phrases")
        trust, features, verdicts, skipped = st.setdefault("trust", {}), {}, {}, []
        probe_prompts = self._probe_prompts(ctx)
        harvest_prompts = [render_prompt(b, COMPLIANT_ANSWER, True) for b in self._blocks(ctx)]
        scores = {}
        for cid in up.clients:
            tr = trust.setdefault(cid, {"status": TRUSTED, "consec": 0, "rejects": [], "since": None, "checked": None})
            if not self._due(ctx, tr):
                skipped.append(cid)
                features[cid] = {"screened": 0.0, "status": float(tr["status"])}
                verdicts[cid] = False
                continue
            tr["checked"] = ctx.round
            with handle.lora(up.state(cid)):
                s = refusal_rate(list(handle.generate(probe_prompts, max_new_tokens=self.max_new_tokens)), phrases)
                fresh = list(handle.generate(harvest_prompts, max_new_tokens=self.max_new_tokens))
            buf = st.setdefault("buffer", {}).setdefault(cid, [])
            buf.extend(fresh)
            del buf[: max(0, len(buf) - self.buffer_rounds * self.harvest)]
            found = span_counts(buf, self.min_words, self.min_generations)
            counts = st.setdefault("counts", {}).setdefault(cid, {})
            for span in prune_nested(found, self.new_strings):
                counts[span] = counts.get(span, 0) + found[span]
            chosen, longest = select_candidates(counts, self.candidates)
            reject_p = majority_reject([s], self.eta)
            reject_d, ratios, why = self._movability(ctx, handle, up, cid, chosen, longest)
            reject = bool(reject_p or reject_d)
            self._advance(ctx, tr, bool(reject))
            verdicts[cid], scores[cid] = bool(reject), float(s)
            features[cid] = {"screened": 1.0, "refusal_rate": float(s), "reject_probe": float(reject_p),
                             "reject_movability": float(reject_d), "reject": float(reject),
                             "candidates": float(len(chosen)), "status": float(tr["status"]),
                             "min_ratio": float(min(ratios.values())) if ratios else -1.0}
            if why:
                skipped.append(cid + ": " + why)
        st["verdicts"], st["round"] = verdicts, ctx.round
        return ctx.findings(scores=scores, features=features,
                            evidence={"round": ctx.round, "not_screened": skipped})

    def _movability(self, ctx, handle, up, cid, chosen, longest):
        """Algorithm 5: the movability test on the candidate strings of one neighbour."""
        if not chosen or longest is None:
            return False, {}, "no candidate string"
        blocks = self._blocks(ctx)
        pairs = {y: [(render_prompt(b, y, True), render_prompt(b, b[3], False)) for b in blocks] for y in chosen}
        with handle.lora(up.base_state()):
            ref = {y: self._delta(handle, pairs[y], y) for y in chosen}
        if ref[longest] <= 0.0:
            return False, {}, "reference movability <= 0"
        kept = [y for y in chosen if ref[y] >= self.phi * ref[longest]]
        if not kept:
            return False, {}, "no candidate above phi times the reference"
        with handle.lora(up.state(cid)):
            ratios = {y: self._delta(handle, pairs[y], y) / ref[y] for y in kept}
        return any(r < self.c for r in ratios.values()), ratios, None

    @staticmethod
    def _delta(handle, pairs, y):
        """Delta_i(theta, y): the mean gain in log-probability of y when y is demonstrated in the context."""
        with_ctx = [p for p, _ in pairs]
        without_ctx = [q for _, q in pairs]
        a = handle.logprob(with_ctx, [y] * len(pairs))
        b = handle.logprob(without_ctx, [y] * len(pairs))
        return sum(float(x) - float(z) for x, z in zip(a, b)) / len(pairs)

    # ----- trust state machine (Algorithm 1 lines 14-15, Appendix A.3) -----
    def _advance(self, ctx, tr, reject):
        if tr["status"] == TRUSTED:
            tr["consec"] = tr["consec"] + 1 if reject else 0
            if tr["consec"] >= self.k_sus:
                tr["status"], tr["consec"], tr["since"], tr["rejects"] = SUSPECTED, 0, ctx.round, []
        elif tr["status"] == SUSPECTED:
            window = [r for r in tr["rejects"] if ctx.round - r < self.w_ej]
            if reject:
                window.append(ctx.round)
            tr["rejects"] = window
            if len(window) >= self.k_ej:
                tr["status"], tr["since"], tr["rejects"] = EJECTED, ctx.round, []
            elif ctx.round - tr["since"] >= self.w_ej:
                tr["status"], tr["consec"], tr["since"] = TRUSTED, 0, None
        elif not reject:
            tr["status"], tr["consec"], tr["since"], tr["rejects"] = SUSPECTED, 0, ctx.round, []

    def _due(self, ctx, tr):
        if tr["status"] != EJECTED:
            return True
        return tr["checked"] is None or (ctx.round - tr["checked"]) >= self.w_re

    # ----- aggregation -----
    def _decide(self, ctx):
        trust, verdicts = ctx.state.get("trust", {}), ctx.state.get("verdicts", {})
        weights, excluded, flags = {}, set(), {}
        for cid in ctx.uploads.clients:
            tr = trust.get(cid)
            if tr is not None and tr["status"] == TRUSTED and not verdicts.get(cid, True):
                weights[cid] = 1.0
            else:
                excluded.add(cid)
                flags[cid] = self._why(tr, verdicts.get(cid))
        return ctx.findings(decision=Decision(weights=weights, excluded=excluded, flags=flags),
                            evidence={"accepted": sorted(weights), "excluded": sorted(excluded)})

    @staticmethod
    def _why(tr, rejected):
        if tr is None:
            return "not screened by chorus"
        if rejected:
            return "rejected this round"
        return "state " + STATUS_NAMES[tr["status"]]

    # ----- prompts -----
    def _probe_prompts(self, ctx):
        st = ctx.state
        if "probe_prompts" not in st:
            st["probe_prompts"] = [render_prompt(b, REFUSAL_DEMO, True) for b in self._draw(ctx, self.prompts)]
        return st["probe_prompts"]

    def _blocks(self, ctx):
        st = ctx.state
        if st.get("blocks_round") != ctx.round:
            st["blocks"], st["blocks_round"] = self._draw(ctx, self.prompts), ctx.round
        return st["blocks"]

    def _trigger(self, ctx):
        st = ctx.state
        if "trigger" not in st:
            words = list(ctx.resource("trigger_words"))
            if not words:
                raise ValueError("chorus needs a nonempty trigger_words resource")
            st["trigger"] = str(words[int(ctx.rng.integers(len(words)))])
        return st["trigger"]

    def _draw(self, ctx, count):
        pool = list(ctx.resource("probe_pool"))
        half = len(pool) // 2
        demos, queries = pool[:half], pool[half:]
        if len(demos) < 3 or not queries:
            raise ValueError("chorus needs a probe_pool of at least three demonstrations and one query")
        tau, out = self._trigger(ctx), []
        for _ in range(count):
            chosen = [demos[i] for i in sampling.subsample(len(demos), 3, ctx.rng)]
            query = queries[int(ctx.rng.integers(len(queries)))]
            order = [int(x) for x in ctx.rng.permutation(3)]
            third = order.index(2)
            before = "".join(format_demo(*chosen[k]) for k in order[:third])
            after = "".join(format_demo(*chosen[k]) for k in order[third + 1:])
            x3, y3 = chosen[2]
            out.append((before, after, x3, y3, insert_trigger(x3, tau, ctx.rng), insert_trigger(query, tau, ctx.rng)))
        return out
