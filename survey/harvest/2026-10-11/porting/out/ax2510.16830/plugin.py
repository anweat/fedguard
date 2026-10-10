# plugin.py
"""VFT (Verifiable Fine-Tuning, ax2510.16830): the two points where the protocol meets a round.

VFT is a proof system wrapped around a training procedure -- a committed dataset, a hashed policy
manifest, a fixed-point arithmetization of the forward, backward and AdamW step, one zero-knowledge
proof per step and a recursive fold of those proofs into one proof per epoch. None of that belongs in
a plugin (rule 3) and none of it has a data kind or an operator here: the library has no field, no
hash, no commitment, no proof, no witness channel and no optimizer-state view (the report lists each
one). What it does have is an action for each of the two actions VFT itself declares on the training
loop: `filter_samples` (the bin-quota constraint of Eq. (3)) and `exclude_client` (the accept/exclude
decision that follows verification). These two plugins carry those two decisions; the verdicts they
depend on are computed outside the library and handed in as resources.
"""
from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops.sampling import subsample


class VFTQuotaSampler(GuardPlugin):
    """VFT's per-epoch bin-quota constraint (Eq. (3)), enforced on the samples a client was handed.

    Eq. (3) says the samples selected in one epoch satisfy sum_t M e_t <= gamma bin-wise, and VFT
    proves it inside the step circuit over a commitment to the selection indicator e_t. A plugin can
    neither sample the batch nor prove anything, so the half that survives is enforcement on the data
    the host announced: keep a per-epoch running count per bin over `DataView.manifest`, admit up to
    the ceiling of each bin (a random subset of that bin's samples, drawn from ctx.rng), mask the rest
    through `mask_samples`, and send the resulting counts to the server as an ordinary self-report.

    Implemented: per-bin cumulative counting over one epoch; a random admission of at most `quota[bin]`
    samples per bin per epoch through `mask_samples`; the counts reported at CLIENT_POST_TRAIN as
    `quota_bins`, `quota_counts`, `quota_epoch` -- i.e. as the untrusted self-report that VFT's local
    quota commitment would have replaced; the epoch counter resetting every `rounds_per_epoch` rounds.
    Deviations: `rounds_per_epoch` stands in for the epoch boundary the library does not expose; the
    bin is read from `SampleRecord.source` (the manifest's provenance tag) unless the caller passes
    `bin_of`, because VFT's bins are (domain, register, length) plus policy tags and only the source
    tag and the hashed text's length reach a plugin; a sample is charged to its bin by distinct hash,
    so identical texts in one round are admitted or dropped together; over-quota samples are dropped
    rather than replaced, since no action can ask the host for a different batch.
    Not implemented: the quota certificate (a commitment to e_t and a range proof on gamma), the token
    ceiling (only `SampleRecord.length`, the length of the hashed text in characters, is visible), and
    any check that a kept sample really entered a batch -- the only per-step sample identity in the
    library is `LossView.sample_ids()` at CLIENT_LOSS, which exists only under the trainer extension.
    Open in the paper and chosen here: bins default to the source tag alone; a bin absent from `quota`
    is unbounded (`default_limit`); the admission inside a bin is a uniform draw from ctx.rng, and the
    draws are taken in sorted bin order so that a run replays; the paper's public mode instead derives
    the batch indices from (s, t) with a CSPRNG, which a plugin cannot do at all.
    Cost: one pass over the round's manifest, one `subsample` per bin; no model passes.
    Resource `quota`: {'<bin key>': <largest number of samples of that bin admitted in one epoch>},
    the ceilings gamma of Eq. (3) restricted to the bins this plugin can see.
    """
    name, at, version = "vft_quota_sampler", (Stage.CLIENT_PRE_TRAIN, Stage.CLIENT_POST_TRAIN), "1"
    needs = frozenset({"data"})
    resources = frozenset({"quota"})
    acts = frozenset({"mask_samples"})

    def __init__(self, rounds_per_epoch=1, bin_of=None, default_limit=float("inf")):
        if rounds_per_epoch < 1:
            raise ValueError("rounds_per_epoch must be >= 1")
        self.rounds_per_epoch = int(rounds_per_epoch)
        self.bin_of = bin_of if bin_of is not None else (lambda rec: rec.source or "unbinned")
        self.default_limit = default_limit

    def run(self, ctx):
        if ctx.stage is Stage.CLIENT_PRE_TRAIN:
            return self._admit(ctx)
        return self._report(ctx)

    def _admit(self, ctx):
        try:
            manifest = ctx.data.manifest
        except LookupError:
            return ctx.findings(evidence={"skipped": "no data manifest at this stage"})
        quota = ctx.resource("quota")
        epoch = ctx.round // self.rounds_per_epoch
        st = ctx.state
        if st.get("epoch") != epoch:
            st["epoch"], st["counts"] = epoch, {}
        counts = st["counts"]
        seen, by_bin = set(), {}
        for rec in manifest:
            if rec.hash in seen:                    # one budget unit per distinct sample hash
                continue
            seen.add(rec.hash)
            by_bin.setdefault(self.bin_of(rec), []).append(rec.hash)
        mask, admitted = [], {}
        for b in sorted(by_bin):
            hashes = by_bin[b]
            limit = float(quota.get(b, self.default_limit))
            room = len(hashes) if limit == float("inf") else max(0, int(limit - counts.get(b, 0)))
            keep = {hashes[i] for i in subsample(len(hashes), room, ctx.rng)}
            mask.extend(h for h in hashes if h not in keep)
            counts[b] = counts.get(b, 0) + len(keep)
            admitted[b] = len(keep)
        return ctx.findings(
            proposals={"mask": mask} if mask else {},
            evidence={"epoch": epoch, "bins": sorted(by_bin), "admitted": admitted, "masked": len(mask),
                      "cumulative": {b: counts[b] for b in sorted(by_bin)}},
        )

    def _report(self, ctx):
        counts = ctx.state.get("counts", {})
        bins = sorted(counts)
        return ctx.findings(
            messages={"quota_bins": bins, "quota_counts": [float(counts[b]) for b in bins],
                      "quota_epoch": int(ctx.state.get("epoch", 0))},
            evidence={"epoch": ctx.state.get("epoch"), "cumulative": {b: counts[b] for b in bins}},
        )


class VFTAuditGate(GuardPlugin):
    """VFT's accept/exclude decision (Sec. III.L.a, Sec. IV.C.a, Sec. V.G.b), applied to one round.

    In VFT an update is accepted only if the client's step proofs and quota certificates verify
    against (h0, hPi, cD); a constraint or quota violation is a hard error that aborts aggregation, and
    a client a probabilistic audit flags is excluded until it attests a corrected manifest. The
    verification itself is a proof-system component and stays outside the library (rule 3): this plugin
    reads its per-client verdicts from a resource and proposes the two things the library has actions
    for -- exclude clients, and let the round aggregate nothing. It verifies nothing.

    Implemented: the decision rule over per-client verdicts; persistence of an exclusion across rounds
    in ctx.state until a verdict of "ok" (the corrected manifest) arrives; the hard-error rule as a
    round that aggregates no one; a 0.0/1.0 risk score and a flag per participant for the record.
    Deviations: "abort the round's aggregation" is expressed as excluding every participant, which in
    the harness leaves the previous global model in place -- the library has no abort, no rollback and
    no way to remove one client's contribution; a participant without a passing verdict is excluded by
    default (VFT accepts only verified updates), so the trust the circuit was to carry sits in the
    resource; a tainted client still trains locally, since the server side cannot reach its training.
    Not implemented: verification of the leaf, epoch and final proofs; the probabilistic audit itself
    (which steps of which client to check, the coverage certificate, the test statistic of Table V);
    the corrected-manifest attestation -- a verdict of "ok" is taken as it; selective disclosure of bin
    counters.
    Open in the paper and chosen here: the verdict vocabulary ("ok", "tainted", "quota_violation") is
    this plugin's, because the paper gives outcomes rather than a status format; a client absent from
    the verdicts is treated like a failed verification unless the deployment asks for on_missing
    "flag"; the 0.0/1.0 score is an invention for the recorder, not a paper quantity; VFT does not
    reweight updates, so no weights are proposed.
    Cost: one pass over the round's participants; no model passes.
    Resource `vft_verdicts`: {client id: {"status": "ok" | "tainted" | "quota_violation"}} produced by
    the VFT verifier and the aggregator's audit outside the library; the defender refreshes the same
    mapping between rounds.
    """
    name, at, version = "vft_audit_gate", Stage.SERVER_AGGREGATE, "1"
    needs = frozenset({"uploads"})
    resources = frozenset({"vft_verdicts"})
    acts = frozenset({"select_and_weight"})
    HARD = "quota_violation"

    def __init__(self, on_missing="exclude"):
        if on_missing not in ("exclude", "flag"):
            raise ValueError("on_missing must be 'exclude' or 'flag'")
        self.on_missing = on_missing

    def run(self, ctx):
        verdicts = ctx.resource("vft_verdicts")
        cids = list(ctx.uploads.clients)
        out = ctx.state.setdefault("out", set())     # excluded until a corrected manifest is attested
        hard, flags, scores, statuses = [], {}, {}, {}
        for cid in cids:
            entry = verdicts.get(cid) if hasattr(verdicts, "get") else None
            status = entry.get("status") if isinstance(entry, dict) else None
            statuses[cid] = status or "missing"
            scores[cid] = 0.0 if status == "ok" else 1.0
            if status == "ok":
                out.discard(cid)
            elif status == self.HARD:
                hard.append(cid)
                flags[cid] = "VFT: constraint violation is a hard error; the round does not aggregate"
            elif status == "tainted":
                out.add(cid)
                flags[cid] = "VFT: audit mismatch; excluded until a corrected manifest is attested"
            elif self.on_missing == "exclude":
                out.add(cid)
                flags[cid] = "VFT: no passing verification this round (%s); acceptance requires one" % statuses[cid]
            else:
                flags[cid] = "VFT: no passing verification this round (%s); reported only" % statuses[cid]
        excluded = set(out) & set(cids)
        if hard:
            excluded = set(cids)
            for cid in cids:
                flags.setdefault(cid, "VFT: the round aggregates nothing because of a violation elsewhere")
        for cid in excluded:
            flags.setdefault(cid, "VFT: still excluded; no corrected manifest attested")
        return ctx.findings(
            scores=scores,
            decision=Decision(excluded=excluded, flags=flags),
            evidence={"aborted": bool(hard), "hard": sorted(hard, key=str),
                      "excluded": sorted(excluded, key=str), "participants": len(cids),
                      "status": statuses},
        )
