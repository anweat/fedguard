"""A paired client/server example: the two halves talk only through the message channel.

The exchange has the shape of the centroid protocol in ProtegoFed (clients send a local summary, the
server sends back a consensus, clients compare their samples against it), but the per-sample feature
here is a toy (hashed bag of words). It shows how a paired defense mounts on the fixed stages; it is
not that method and makes no detection claim.

Round t:   LocalCentroid (client, CLIENT_PRE_TRAIN) sends its centroid with the upload.
           CentroidConsensus (server, SERVER_AGGREGATE) takes the coordinate-wise median of what arrived.
Round t+1: the consensus rides with the broadcast; LocalCentroid scores each local sample by its
           distance to it.
"""
from __future__ import annotations

import math
import re
import statistics
import zlib

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage

DIM = 32


def text_feature(text: str, dim: int = DIM) -> list[float]:
    """L2-normalized hashed bag of lowercase word tokens."""
    v = [0.0] * dim
    for tok in re.findall(r"\w+", text.lower()):
        v[zlib.crc32(tok.encode()) % dim] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _median(vectors: list[list[float]]) -> list[float]:
    return [statistics.median(col) for col in zip(*vectors)]


def _dist(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class LocalCentroid(GuardPlugin):
    """Client half. Sends the coordinate-wise median feature of the local samples; once the server's
    consensus has arrived, scores every sample (by hash) with its distance to the consensus."""
    name, at, version = "local_centroid", Stage.CLIENT_PRE_TRAIN, "1"
    needs = frozenset({"data", "reports"})

    def __init__(self, consensus: str = "centroid_consensus.centroid"):
        self.consensus = consensus

    def run(self, ctx):
        data = ctx.data
        feats = [text_feature(data.text(i)) for i in range(len(data))]
        if not feats:
            return ctx.findings(evidence={"skipped": "no local samples"})
        scores = {}
        ref = ctx.reports.messages(self.consensus).get("server")
        if isinstance(ref, list) and len(ref) == DIM:
            scores = {r.hash: _dist(f, ref) for r, f in zip(data.manifest, feats)}
        return ctx.findings(scores=scores, messages={"centroid": _median(feats), "n": len(feats)},
                            evidence={"consensus_received": bool(scores)})


class CentroidConsensus(GuardPlugin):
    """Server half. Coordinate-wise median of the centroids clients sent; scores each client by the
    distance of its centroid from the consensus. What clients send is unverified by construction."""
    name, at, version = "centroid_consensus", Stage.SERVER_AGGREGATE, "1"
    needs = frozenset({"reports"})

    def __init__(self, source: str = "local_centroid.centroid", min_clients: int = 3):
        self.source, self.min_clients = source, min_clients

    def run(self, ctx):
        got = {c: v for c, v in ctx.reports.messages(self.source).items()
               if isinstance(v, list) and len(v) == DIM and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)}
        if len(got) < self.min_clients:
            return ctx.findings(evidence={"skipped": f"{len(got)} usable centroids, need {self.min_clients}"})
        consensus = _median(list(got.values()))
        return ctx.findings(scores={c: _dist(v, consensus) for c, v in got.items()}, messages={"centroid": consensus},
                            evidence={"clients": sorted(got)})
