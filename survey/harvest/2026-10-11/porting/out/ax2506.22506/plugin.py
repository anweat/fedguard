# plugin.py
"""SABRE-FL (Selective and Accurate Backdoor REjection for Federated Prompt Learning): the decisions of
the paper as a fedguard plugin pair, plus the client-side embedding upload.

    SabreEmbeddings  client, CLIENT_POST_TRAIN                 shares one embedding per announced sample
    SabreFL          server, SERVER_RECEIVE + SERVER_AGGREGATE flags them, ranks the clients, excludes
                                                               the top m from the aggregation

The two assets the paper assumes and this library cannot produce -- the frozen CLIP image encoder that
turns a local image into an embedding, and the binary detector trained offline on the auxiliary dataset
-- are defender-supplied resources; the form of each is in its class docstring.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage

EMBEDDING_SOURCE = "sabre_embeddings"
EMBEDDING_KEY = "embeddings"
EMBEDDING_ATTACHMENT = EMBEDDING_SOURCE + "." + EMBEDDING_KEY    # the "<plugin>.<key>" channel name

def detector_flags(detector, z: torch.Tensor, threshold: float = 0.5) -> torch.Tensor:
    """0/1 flag of every row of z: 1.0 where the detector puts at least `threshold` on class 1.

    The detector is the offline-trained binary model (the paper: two layers, hidden 128, ReLU):
    (n, d) embeddings -> (n, 2) logits, column 1 = poisoned. Called under no_grad; not modified.
    """
    with torch.no_grad():
        out = torch.as_tensor(detector(z)).detach().to(torch.float64)
    if out.dim() != 2 or out.shape[1] != 2:
        raise ValueError("the detector resource must return (n, 2) logits")
    return (torch.softmax(out, dim=1)[:, 1] >= float(threshold)).to(torch.float64)

def rank_top_m(values: dict, m: int, order: list) -> list:
    """The keys of `values` with the largest value, ties broken by their position in `order`.

    A rank cut, not a threshold: with m > 0 it returns min(m, len(values)) keys. The library has
    largest_gap_threshold for the threshold style and no top-m operator.
    """
    pool = [c for c in order if c in values]
    pool.sort(key=lambda c: (-float(values[c]), order.index(c)))
    return pool[: max(0, int(m))]

class SabreEmbeddings(GuardPlugin):
    """SABRE-FL, client side: hand the server one embedding per local sample of this round.

    The embeddings leave as a tensor attachment on the upload the client was going to send anyway,
    keyed "sabre_embeddings.embeddings"; SabreFL reads them from `reports` at SERVER_RECEIVE. No extra
    round trip is added, and nothing about the local update or the loss is touched.

    Resource `embeddings`: {sample hash: 1-D tensor}, the image embedding of each local sample keyed by
    the hash `DataView.manifest` gives its text. It is produced outside the library: fedguard sees LoRA
    factors of a language model and offers no handle on a second model, so the frozen image encoder of
    the paper cannot be run from a plugin. The vectors are passed on in the dtype the defender stored
    them in, so the detector resource must be built in that same dtype.

    Implemented: the sharing half of pipeline step 4, over the hashes of exactly the samples announced
    this round.

    Not implemented: the encoding itself (one frozen CLIP image-encoder forward per local image), which
    needs a model handle this library does not have; see the resource line.

    Open in the paper and chosen here: the paper leaves n_k, the upload frequency and the shape of the
    upload open, and its Algorithm 1 line 11 is truncated in the extraction. Chosen: one row per
    announced sample, every round, on the existing upload channel; a sample with no embedding is left
    out and counted, never replaced by a zero vector that the detector would have to judge.

    Cost: O(n_k) tensor copies per round and n_k * d floats on the channel; no model pass inside the
    library, so findings.cost stays empty (the encoder forward is spent outside it). The runner caps one
    plugin at 64 MiB of attachments per round, roughly 32k float32 rows of the paper dimension d = 512.
    """
    name, at, version = "sabre_embeddings", Stage.CLIENT_POST_TRAIN, "1"
    needs, resources, acts = frozenset({"data"}), frozenset({"embeddings"}), frozenset()

    def run(self, ctx):
        table = ctx.resource("embeddings")
        rows, missing = [], []
        for rec in ctx.data.manifest:
            z = table.get(rec.hash)
            if z is None:
                missing.append(rec.hash)
            else:
                rows.append(torch.as_tensor(z).detach().reshape(-1))
        if not rows:
            return ctx.findings(evidence={"shared": 0, "missing": len(missing),
                                          "reason": "no embedding for any sample announced this round"})
        return ctx.findings(attachments={EMBEDDING_KEY: torch.stack(rows)},
                            evidence={"shared": len(rows), "missing": len(missing),
                                      "dim": int(rows[0].numel())})

class SabreFL(GuardPlugin):
    """SABRE-FL: exclude the clients whose uploaded embeddings the offline detector calls backdoored.

    At SERVER_RECEIVE every attached embedding is scored by the detector and the client gets the mean
    flag score S_k of Eq. 7, with the number of flagged embeddings kept as well. At SERVER_AGGREGATE the
    clients are ranked by that score and the m highest are removed from the aggregation, the rank-based
    rule of the paper with no fixed threshold tau; the kept clients go on to the host aggregation with
    the weights it would have used. Nothing accumulates across rounds and the detector is not updated:
    both scores and counts are reported in the findings.

    Resource `detector`: the binary detector trained offline on the auxiliary clean/triggered embedding
    set (the paper: two layers, 512 -> 128 -> 2, ReLU, on Caltech-101). Form: any callable mapping an
    (n, d) float tensor of embeddings to (n, 2) logits, column 1 = poisoned; it must accept the
    embeddings in the dtype they arrive in. The defender supplies it in eval mode; it is only called,
    never modified.

    Implemented: pipeline steps 5 to 8 -- per-embedding detection (step 5), the client-level mean score
    of Eq. 7 or the flagged count (step 6), the rank-based top-m exclusion with m from the defender
    (step 7), and the decision the host aggregation obeys (step 8). Step 9 is a property of the code:
    the detector lives in the resource, and round_state is emptied by the runner every round.

    Deviations: the paper is federated prompt learning over CLIP image embeddings, this library adapts
    LoRA factors of a language model, so the vectors scored here are whatever the defender encoded and
    the update itself takes no part in the decision. Detection and exclusion sit in one plugin mounted
    twice, SERVER_RECEIVE then SERVER_AGGREGATE, instead of two server components. A client that sends
    no embedding is never excluded (it cannot be ranked, and dropping it is an exclusion the method did
    not ask for): an attacker that simply omits the embeddings is not caught. The upload rides the
    update channel as an attachment instead of a separate representation-sharing channel.

    Not implemented: pipeline steps 0 and 1, the construction of the auxiliary embedding set and the
    training of the detector. Both happen outside federated training, and the paper leaves the trigger,
    the poisoned fraction and the auxiliary subset unspecified; they reach the plugin only as the
    `detector` resource.

    Open in the paper and chosen here: (1) ranking uses the mean flag score of Eq. 7 by default, with
    by="count" for the Inference Rule wording, which orders differently when the n_k differ; (2) m
    defaults to ceil(0.25 * the round participants), the paper gives only the 25% ratio and no per-round
    count, so pass m for the bound the deployment knows; (3) logits become 0/1 by probability >=
    threshold (0.5), the paper writes D: R^d -> {0,1} but leaves the cut open; (4) at most n - 1 clients
    are excluded, so a round never loses its aggregation entirely; (5) ties go to the earlier client of
    `uploads.clients`; (6) embeddings are neither normalized nor standardized here and no dtype
    conversion is done, the defender trained the detector on the encoding it uses; (7) with
    equal_weights=True the kept clients get weight 1, the plain mean, otherwise they keep the weights
    the host aggregation would have given them.

    Cost: one detector forward per uploaded embedding (n * n_k rows, 512 x 128 x 2 per row in the
    paper) plus an O(n log n) sort per round; no model pass through the library, so findings.cost stays
    empty. The paper reports only the detector size (a few MBs) and the encoder cost of its own client.
    """
    name, at, version = "sabre_fl", (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE), "1"
    needs = frozenset({"uploads", "reports"})
    resources, acts = frozenset({"detector"}), frozenset({"select_and_weight"})

    def __init__(self, m: int | None = None, m_ratio: float = 0.25, by: str = "mean",
                 threshold: float = 0.5, equal_weights: bool = False):
        if by not in ("mean", "count"):
            raise ValueError("by must be 'mean' or 'count'")
        self.m, self.m_ratio, self.by = m, float(m_ratio), by
        self.threshold, self.equal_weights = float(threshold), bool(equal_weights)

    def run(self, ctx):
        if ctx.stage is Stage.SERVER_RECEIVE:
            return self._score(ctx)
        return self._exclude(ctx)

    def _value(self, row: dict) -> float:
        return row["mean"] if self.by == "mean" else float(row["flagged"])

    def _score(self, ctx):
        sent = ctx.attachment(EMBEDDING_ATTACHMENT)
        rows = {}
        for cid in ctx.uploads.clients:
            z = sent.get(cid)
            if z is None:
                continue
            z = torch.as_tensor(z).detach()
            if z.dim() != 2 or z.shape[0] == 0:
                continue
            flags = detector_flags(ctx.resource("detector"), z, self.threshold)
            rows[cid] = {"n": int(z.shape[0]), "flagged": int(flags.sum()), "mean": float(flags.mean())}
        ctx.round_state["rows"] = rows
        return ctx.findings(
            scores={cid: self._value(row) for cid, row in rows.items()},
            features={cid: {"embeddings": float(row["n"]), "flagged": float(row["flagged"]),
                            "mean_flag_score": row["mean"]} for cid, row in rows.items()},
            evidence={"scored": sorted(rows), "no_embeddings": sorted(set(ctx.uploads.clients) - set(rows)),
                      "threshold": self.threshold, "ranked_by": self.by})

    def _exclude(self, ctx):
        cids = ctx.uploads.clients
        rows = dict(ctx.round_state.get("rows", {}))
        n = len(cids)
        m = self.m if self.m is not None else int(math.ceil(self.m_ratio * n))
        m = max(0, min(int(m), len(rows), max(0, n - 1)))
        values = {cid: self._value(row) for cid, row in rows.items()}
        excluded = set(rank_top_m(values, m, cids))
        flags = {cid: ("excluded: %d of %d embeddings flagged" % (row["flagged"], row["n"]) if cid in excluded
                       else "kept: %d of %d embeddings flagged" % (row["flagged"], row["n"]))
                 for cid, row in rows.items()}
        weights = {cid: 1.0 for cid in cids if cid not in excluded} if self.equal_weights else {}
        return ctx.findings(scores=values, decision=Decision(excluded=excluded, weights=weights, flags=flags),
                            evidence={"m": m, "m_requested": self.m, "m_ratio": self.m_ratio,
                                      "participants": n, "scored": len(rows), "ranked_by": self.by,
                                      "no_embeddings": sorted(set(cids) - set(rows))})
