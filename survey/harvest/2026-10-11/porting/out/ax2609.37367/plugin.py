# plugin.py
"""CHORUS (Zhou et al.): behavioural screening of the LoRA adapters a node receives.

The paper is decentralized (D-PSGD): every honest node trains its own adapter, receives the adapters of its
neighbours, screens each of them with its own adapter as the trusted reference, and averages only the ones
it accepts. This port mounts that screening on the server of a star-shaped federated run: the uploads of the
round are the adapters that arrived, and the server-side model handle is the model they are loaded into.
"""
from __future__ import annotations

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import sampling, text

TRUSTED, SUSPECTED, EJECTED = 0, 1, 2
STATUS_NAMES = ("TRUSTED", "SUSPECTED", "EJECTED")

# Appendix C, verbatim: the refusal demonstration of the Stage 1a prompt and the compliant answer of the
# Stage 1b prompt.
REFUSAL_DEMO = "I'm sorry, but as an AI assistant, I do not have the capability to follow the given instruction."
COMPLIANT_ANSWER = "Certainly, here is a helpful answer to the given instruction."


def insert_trigger(instruction, trigger, rng):
    """INSERTTRIGGER (Algorithm 2 lines 3-7): the trigger goes between two words of the instruction."""
    words = text.split_words(instruction)
    if len(words) < 2:
        return instruction + " " + trigger
    at = int(rng.integers(1, len(words)))
    return " ".join(words[:at] + [trigger] + words[at:])


def refusal_rate(answers, phrases):
    """The Stage 1a score s: the fraction of answers holding a refusal phrase as a lower-cased substring."""
    if not answers:
        return 0.0
    low = [a.lower() for a in answers]
    return sum(1 for a in low if any(p.lower() in a for p in phrases)) / len(answers)


def majority_reject(pooled, eta):
    """Algorithm 3 line 2: reject when a strict majority of the pooled scores is above eta; a tie accepts."""
    return sum(1 for s in pooled if s > eta) > len(pooled) / 2


def span_counts(generations, min_words):
    """Algorithm 4: for every word span, in how many generations of the buffer it occurs.

    A generation counts once per span, however often the span occurs inside it.
    """
    counts = {}
    for g in generations:
        words, seen = text.split_words(g), set()
        for i in range(len(words)):
            for j in range(i + min_words, len(words) + 1):
                seen.add(" ".join(words[i:j]))
        for s in seen:
            counts[s] = counts.get(s, 0) + 1
    return counts


def pruned_spans(counts, min_generations, limit):
    """Algorithm 4: most frequent first and longest first on a tie, one string per nested family.

    Spans are word sequences, so nesting is tested on the space-padded strings: a raw substring test would
    call the two words `was her` nested in the three words `he was here`.
    """
    def key(s):
        return (-counts[s], -len(s.split()), s)
    kept = []
    for s in sorted(counts, key=key):
        if counts[s] < min_generations:
            break
        pad = " " + s + " "
        if any(pad in k or k in pad for k in kept):
            continue
        kept.append(pad)
        if len(kept) >= limit:
            break
    return [k[1:-1] for k in kept]


def candidates_of(counts, k):
    """Algorithm 5 lines 2-3: the k-1 most frequent strings (ties: longer first) plus the longest string."""
    def key(s):
        return (-counts[s], -len(s.split()), s)
    order = sorted(counts, key=key)
    if not order:
        return [], None
    longest = max(order, key=lambda s: (len(s.split()), counts[s], s))
    top = order[: max(0, k - 1)]
    return (top if longest in top else top + [longest]), longest


def demo_block(instruction, response):
    """One instruction-response block of the ICL prompt; the paper keeps the ICLSCAN template."""
    return "### Instruction:\n" + instruction + "\n\n### Response:\n" + response + "\n\n"


def render(block, answer, triggered):
    """One prompt: two ordinary demonstrations, a third one (triggered or not) and the triggered query."""
    before, after, x3, y3, x3t, query = block
    return (before + demo_block(x3t if triggered else x3, answer) + after
            + "### Instruction:\n" + query + "\n\n### Response:\n")


def context_gain(handle, pairs, target):
    """Delta_i(theta, y): the mean gain in the per-token log-probability of y when y is demonstrated."""
    with_y = [p for p, _ in pairs]
    without = [q for _, q in pairs]
    a = handle.logprob(with_y, [target] * len(pairs))
    b = handle.logprob(without, [target] * len(pairs))
    return sum(float(x) - float(z) for x, z in zip(a, b)) / len(pairs)


def reason(tr, rejected):
    """Why a client is not merged, for the flags of the Decision."""
    if tr is None:
        return "not screened"
    if rejected:
        return "rejected this round"
    return "state " + STATUS_NAMES[tr["status"]]


class Chorus(GuardPlugin):
    """CHORUS: two behavioural tests on every LoRA adapter a node receives, a per-neighbour trust state
    machine, and equal-weight averaging of the adapters it accepts.

    The paper is decentralized: each honest node screens the adapters of its neighbours with its own adapter
    as the trusted reference, and pools one scalar score and its harvested strings with the other receivers
    of the same adapter. This port mounts that screening on the server of a star-shaped run, where the
    uploads of the round are the adapters that arrived.

    Implemented: Stage 1a end to end, with P probe prompts built once from the probe pool and reused for
    the whole run, one trigger word drawn once and fixed, the refusal rate over the phrase table, and the
    strict-majority rule with its tie accepting; Stage 1b end to end, with per-neighbour harvest buffers of
    W_h rounds, word-span counting with w_min and r_min, nested-family pruning, per-neighbour count tables
    that accumulate across rounds and take at most kappa new strings a round, the candidate set of the K-1
    most frequent strings plus the longest one y^max, the movability score over P prompt pairs scored under
    identical contexts for both adapters, the phi filter with y^max as reference, the skip when
    Delta_i(theta_i, y^max) is not positive, and the ratio rule with c; the union of the two tests; the
    trust state machine with k_sus, k_ej, W_ej and W_re; and equal-weight aggregation of the accepted
    adapters through `select_and_weight`.

    Deviations: the paper has no server. Node i becomes the server of a star, the adapters of its neighbours
    become the uploads of the round, and the model the uploads are loaded into is the model of that node.
    theta_i, the own freshly trained adapter of the receiver, has no counterpart on a server, so the
    broadcast base of the round (uploads.base_state(), the global adapter every upload started from) is the
    trusted reference. The score exchange with the other receivers of an adapter, the string exchange with
    them and the majority vote over their pooled scores have no counterpart in a star, where an upload has
    exactly one receiver: the vote rule is implemented and called with that one score, so reject_P is the
    score of this receiver above eta. The `data` kind of the library is client-side, so the probe pool is a
    server resource rather than a split of the training data of a node. The plugin needs a deployment that
    hands in a full server-side model handle (OpenFedLLMGuard(probe=...)): a server has no model by default
    and the shipped server-side handle implements ProbeView only.

    Not implemented: the two cross-receiver exchanges and their pooled sets V_j and C_j (steps 8 and 11 of
    the extraction), which the runtime cannot express; beam search for the harvest, since the handle
    generates greedily with a token limit only, so the beam width B of the paper, its length penalty and its
    early stopping are absent and the harvest recall the paper reports for beam search is not reached; the
    sampled probe decoding (temperature, top-p, top-k) for the same reason, which the paper measures as the
    weaker setting.

    Open in the paper and chosen here: words are whitespace-separated (fedguard.ops.text.split_words);
    every span of at least w_min words is enumerated, with no upper length bound; the trigger is inserted
    at a uniformly drawn word boundary of the third instruction and of the query; a generation counts once
    per span; counts are pooled over co-receivers by summing, which here is the own table of the receiver;
    ties are broken by word count and then lexicographically, both for the candidate order and for y^max;
    the movability prompts are redrawn every round and shared by the two adapters within it, while the
    Stage 1a prompts are drawn once; the harvest uses the first H of the drawn blocks of the round; with no
    candidate string the movability test rejects nothing; Delta_i(theta_i, y) is computed once per candidate
    and reused for the ratio; a candidate whose reference gain is not positive cannot reject; an accepted
    screening round resets the consecutive counter; a SUSPECTED neighbour returns to TRUSTED after W_ej
    rounds without k_ej rejections; a rejected re-check leaves the neighbour EJECTED and restarts W_re; the
    initial state is TRUSTED; an upload is screened in the round it first appears in; the ICL prompt
    template is not restated in the paper, so an instruction/response block in the ICLSCAN style is used.

    Cost: per screened client per round, P probe generations and H harvest generations of up to L new
    tokens, plus at most K candidates times 2 contexts times P prompts times 2 adapters forward passes for
    the movability scores; the handle counts every pass and the runner writes the share of this plugin into
    its findings. The paper reports 3.0 to 4.1 times the wall clock of no defense, 73 percent of it in the
    harvest.

    Resource `probe_pool`: the private held-out pool of the node, a sequence of (instruction, response)
    pairs; the first half are the demonstrations and the second half queries, of which only the instruction
    is used, since the answer of a query is generated; at least three demonstrations and one query.
    Resource `trigger_words`: the public word list the probe trigger is drawn from, a sequence of strings.
    Resource `refusal_phrases`: the refusal substrings of Appendix C, a sequence of lower-cased strings.
    """

    name, at, version = "chorus", (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE), "1"
    needs = frozenset({"uploads", "model_handle"})
    resources = frozenset({"probe_pool", "trigger_words", "refusal_phrases"})
    acts = frozenset({"select_and_weight"})

    def __init__(self, eta=0.25, c=0.1, phi=0.5, prompts=30, harvest=5, buffer_rounds=10,
                 max_new_tokens=48, min_words=3, min_generations=2, new_strings=5, candidates=4,
                 k_sus=2, k_ej=3, w_ej=5, w_re=10):
        self.eta, self.c, self.phi = float(eta), float(c), float(phi)
        self.prompts, self.harvest, self.buffer_rounds = int(prompts), int(harvest), int(buffer_rounds)
        self.max_new_tokens = int(max_new_tokens)
        self.min_words, self.min_generations = int(min_words), int(min_generations)
        self.new_strings, self.candidates = int(new_strings), int(candidates)
        self.k_sus, self.k_ej, self.w_ej, self.w_re = int(k_sus), int(k_ej), int(w_ej), int(w_re)

    def run(self, ctx):
        if ctx.stage is Stage.SERVER_RECEIVE:
            return self._screen(ctx)
        return self._aggregate(ctx)

    # ----- Stage 1a and Stage 1b, once per round -----
    def _screen(self, ctx):
        up, handle, st = ctx.uploads, ctx.model_handle, ctx.state
        phrases, trust = ctx.resource("refusal_phrases"), st.setdefault("trust", {})
        probe_prompts, blocks = self._probe_prompts(ctx), self._round_blocks(ctx)
        harvest_prompts = [render(b, COMPLIANT_ANSWER, True) for b in blocks[: self.harvest]]
        scores, features, verdicts, notes = {}, {}, {}, []
        for cid in up.clients:
            tr = trust.setdefault(cid, {"status": TRUSTED, "consec": 0, "rejects": [], "since": None, "checked": None})
            if not self._due(ctx, tr):
                verdicts[cid] = False
                features[cid] = {"screened": 0.0, "status": float(tr["status"])}
                continue
            tr["checked"] = ctx.round
            with handle.lora(up.state(cid)):
                rate = refusal_rate(list(handle.generate(probe_prompts, max_new_tokens=self.max_new_tokens)), phrases)
                fresh = list(handle.generate(harvest_prompts, max_new_tokens=self.max_new_tokens))
            buffer = st.setdefault("buffer", {}).setdefault(cid, [])
            buffer.extend(fresh)
            del buffer[: max(0, len(buffer) - self.buffer_rounds * self.harvest)]
            found = span_counts(buffer, self.min_words)
            table = st.setdefault("counts", {}).setdefault(cid, {})
            for span in pruned_spans(found, self.min_generations, self.new_strings):
                table[span] = table.get(span, 0) + found[span]
            chosen, longest = candidates_of(table, self.candidates)
            reject_probe = majority_reject([rate], self.eta)
            reject_movability, ratios, note = self._movability(handle, up, cid, blocks, chosen, longest)
            reject = bool(reject_probe or reject_movability)
            self._advance(ctx, tr, reject)
            verdicts[cid], scores[cid] = reject, float(rate)
            features[cid] = {"screened": 1.0, "refusal_rate": float(rate), "reject_probe": float(reject_probe),
                             "reject_movability": float(reject_movability), "reject": float(reject),
                             "candidates": float(len(chosen)), "status": float(tr["status"]),
                             "min_ratio": float(min(ratios.values())) if ratios else -1.0}
            if note:
                notes.append(cid + ": " + note)
        st["verdicts"], st["screened_round"] = verdicts, ctx.round
        return ctx.findings(scores=scores, features=features, evidence={"round": ctx.round, "notes": notes})

    def _movability(self, handle, up, cid, blocks, chosen, longest):
        """Algorithm 5: the movability test on the candidate strings of one neighbour."""
        if not chosen:
            return False, {}, "no candidate string"
        pairs = {y: [(render(b, y, True), render(b, b[3], False)) for b in blocks] for y in chosen}
        with handle.lora(up.base_state()):
            reference = {y: context_gain(handle, pairs[y], y) for y in chosen}
        if reference[longest] <= 0.0:
            return False, {}, "the reference gain of y^max is not positive"
        kept = [y for y in chosen if reference[y] >= self.phi * reference[longest]]
        if not kept:
            return False, {}, "no candidate reaches phi times the reference gain"
        with handle.lora(up.state(cid)):
            ratios = {y: context_gain(handle, pairs[y], y) / reference[y] for y in kept}
        return any(r < self.c for r in ratios.values()), ratios, None

    # ----- the trust state machine (Algorithm 1 lines 14-15, Appendix A.3) -----
    def _advance(self, ctx, tr, reject):
        if tr["status"] == TRUSTED:
            tr["consec"] = tr["consec"] + 1 if reject else 0
            if tr["consec"] >= self.k_sus:
                tr.update(status=SUSPECTED, consec=0, since=ctx.round, rejects=[])
        elif tr["status"] == SUSPECTED:
            window = [r for r in tr["rejects"] if ctx.round - r < self.w_ej]
            if reject:
                window.append(ctx.round)
            tr["rejects"] = window
            if len(window) >= self.k_ej:
                tr.update(status=EJECTED, since=ctx.round, rejects=[])
            elif ctx.round - tr["since"] >= self.w_ej:
                tr.update(status=TRUSTED, consec=0, since=None, rejects=[])
        elif not reject:
            tr.update(status=SUSPECTED, consec=0, since=ctx.round, rejects=[])

    def _due(self, ctx, tr):
        """An EJECTED neighbour is screened again only after W_re rounds."""
        if tr["status"] != EJECTED:
            return True
        return tr["checked"] is None or (ctx.round - tr["checked"]) >= self.w_re

    # ----- aggregation (Algorithm 1 lines 16-17) -----
    def _aggregate(self, ctx):
        st = ctx.state
        if st.get("screened_round") != ctx.round:
            return ctx.findings(evidence={"skipped": "nothing was screened in this round"})
        trust, verdicts = st.get("trust", {}), st.get("verdicts", {})
        weights, excluded, flags = {}, set(), {}
        for cid in ctx.uploads.clients:
            tr = trust.get(cid)
            if tr is not None and tr["status"] == TRUSTED and not verdicts.get(cid, True):
                weights[cid] = 1.0
            else:
                excluded.add(cid)
                flags[cid] = reason(tr, verdicts.get(cid))
        return ctx.findings(decision=Decision(weights=weights, excluded=excluded, flags=flags),
                            evidence={"accepted": sorted(weights), "excluded": sorted(excluded)})

    # ----- prompts -----
    def _probe_prompts(self, ctx):
        if "probe_prompts" not in ctx.state:
            ctx.state["probe_prompts"] = [render(b, REFUSAL_DEMO, True) for b in self._draw(ctx, self.prompts)]
        return ctx.state["probe_prompts"]

    def _round_blocks(self, ctx):
        st = ctx.state
        if st.get("blocks_round") != ctx.round:
            st["blocks"], st["blocks_round"] = self._draw(ctx, max(self.prompts, self.harvest)), ctx.round
        return st["blocks"]

    def _trigger(self, ctx):
        st = ctx.state
        if "trigger" not in st:
            words = list(ctx.resource("trigger_words"))
            if not words:
                raise ValueError("chorus needs a non-empty trigger_words resource")
            st["trigger"] = str(words[int(ctx.rng.integers(len(words)))])
        return st["trigger"]

    def _draw(self, ctx, count):
        """Draw prompt skeletons: three demonstrations (the third one triggered when rendered) and a query."""
        pool = list(ctx.resource("probe_pool"))
        half = len(pool) // 2
        demos, queries = pool[:half], pool[half:]
        if len(demos) < 3 or not queries:
            raise ValueError("chorus needs a probe_pool with at least three demonstrations and one query")
        tau, out = self._trigger(ctx), []
        for _ in range(count):
            picked = [demos[i] for i in sampling.subsample(len(demos), 3, ctx.rng)]
            query = queries[int(ctx.rng.integers(len(queries)))][0]
            order = [int(x) for x in ctx.rng.permutation(3)]
            third = order.index(2)
            before = "".join(demo_block(*picked[k]) for k in order[:third])
            after = "".join(demo_block(*picked[k]) for k in order[third + 1:])
            x3, y3 = picked[2]
            out.append((before, after, x3, y3, insert_trigger(x3, tau, ctx.rng), insert_trigger(query, tau, ctx.rng)))
        return out
