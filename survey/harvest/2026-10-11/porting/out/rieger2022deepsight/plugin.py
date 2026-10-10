# plugin.py
"""DeepSight (Rieger et al., IEEE TIFS 2022) over uploaded LoRA factors: filter, clip, average.

The filter of the paper reads the output layer of every uploaded model. What crosses a fedguard boundary
is a LoRA state dict, so the output layer is reachable only through the factors of whichever module was
adapted as the readout; where no module stands in for it the plugin reports skipped and only the clipping
and aggregation layers run.
"""
from __future__ import annotations

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Decision, Stage
from fedguard.ops import cluster, geometry, states, update
from fedguard.ops.lowrank import gram as lowrank_gram


def readout_row_l1(delta) -> torch.Tensor:
    '''Row-wise L1 norms of a low-rank matrix: E_i = sum_h |W[i, h]| for W = scale * U @ V.

    One row is formed at a time, so the P x d_in matrix is never materialized: the arithmetic is what
    forming it costs (P matrix-vector products), the memory is one row.
    '''
    u, v = delta.U.double() * float(delta.scale), delta.V.double()
    if not u.shape[0]:
        return torch.zeros(0, dtype=torch.float64)
    return torch.stack([(u[i] @ v).abs().sum() for i in range(u.shape[0])])


def threshold_exceedings(energy: torch.Tensor, threshold_factor: float = 0.01) -> torch.Tensor:
    '''Eqs. (8)-(11): C_i = E_i^2 / sum_j E_j^2, xi = max(tf, 1/P) * max_i C_i, TE = #{i : C_i > xi}.'''
    sq = energy.double() ** 2
    share = sq / sq.sum(dim=1, keepdim=True).clamp_min(1e-300)
    xi = max(threshold_factor, 1.0 / share.shape[1]) * share.max(dim=1).values
    return (share > xi[:, None]).sum(dim=1)


def co_membership(labels: torch.Tensor) -> torch.Tensor:
    '''DistsFromClust (Alg. 2 lines 1-3): distance 0 inside a cluster, 1 between two of them.'''
    lab, nxt = labels.clone(), int(labels.max()) + 1
    for k, i in enumerate(torch.nonzero(lab < 0).flatten().tolist()):
        lab[i] = nxt + k
    return (lab[:, None] != lab[None, :]).double()


def groups_of(labels: torch.Tensor) -> list[list[int]]:
    '''Cluster membership as index lists; each noise point (-1) is a group of its own.'''
    out: dict = {}
    for i, lab in enumerate(labels.tolist()):
        out.setdefault(lab if lab >= 0 else ('noise', i), []).append(i)
    return list(out.values())


class DeepSight(GuardPlugin):
    '''DeepSight (Rieger et al., IEEE TIFS 2022): three server-side layers over one round of uploads --
    label every update, remove the clusters whose suspicious share reaches tau, clip what remains to the
    median update norm, and average the rest with equal weights.

    Implemented: the output-layer energy of Eq. (7) as E_{t,k,i} = sum_h |dW[i, h]| on the readout
    module functional change dW = B_k A_k - B_g A_g; its within-model normalization to C_{t,k,i}
    (Eq. 8); xi_{t,k} = max(threshold_factor, 1/P) * max_i C_{t,k,i} and the count TE_{t,k} = #{i : C_i > xi}
    (Eqs. 9-11); the median/2 boundary and the label suspicious for TE <= boundary (Alg. 1 lines 21-22);
    one clustering per available view, each view turned into a 0/1 co-membership distance (Alg. 2 lines
    1-3), the matrices averaged (lines 19-21) and the average clustered once more (line 22); the
    per-cluster vote, where a suspicious share p_c >= tau removes the whole cluster (lines 25-31);
    clipping of the accepted updates to S = median of all this round of update norms (Eq. 12, section V-B);
    equal weights for the aggregation (line 32, section II-A).
    Deviations: the paper reads these quantities off the full model output layer. A LoRA adapter carries
    no bias, so the bias delta of Eq. (7) contributes nothing and the deltas of Eqs. (13)-(14) are all
    zero; the weight term of Eq. (7) is taken on the readout module factor-space change instead, and
    the cosine view is therefore between readout weight deltas and not between bias deltas. The updates
    themselves are factor-space updates, as everywhere else in the library.
    Not implemented: the DDif view (Alg. 1 lines 18-19, Eq. 6). It needs 3 x 20 000 random input vectors
    of the model input dimension pushed through the global model and through every upload model; a
    LoRA state dict holds no input dimension, no model and no output-layer probability, and the server
    side has no model unless the defender passes one. The consensus therefore averages 2 of the 5
    distance matrices of the paper. Also not implemented: the last-round clusterwise aggregation and
    per-cluster download (section V-C) -- a plugin is never told which round is the last, and no action
    returns more than one aggregate for the host to send.
    Open in the paper and chosen here: readout names the module that stands in for the output layer
    (default: the adapted module with the largest layer index, ties by name); P is that module lora_B
    row count; HDBSCAN parameters are not given, so ops.cluster.density_clusters, the parameter-free
    stand-in of the library, is used (min_samples, scale); a noise point (-1) is a cluster of its own; the
    median of an even count is the mean of the two middle values (as in FLAME here); TE <= boundary is
    suspicious, following Alg. 1 over the below of section IV-C; S is the median over every upload of the
    round, rejected ones included, as section V-B writes it; a client whose readout delta is exactly zero
    has no NEUP and gets TE = 0; fewer than min_clients uploads, or no adapted readout, and nothing is
    filtered (the aggregation layer is unconditional, so the weights are equal in those rounds too).
    Note: with the usual LoRA targets (attention and MLP projections) no adapted module is the output
    layer, so the filter reports skipped every round and only clipping and equal weights are left.
    Cost: P row-L1 norms of a 2r x d_in factor pair per client, 2 DBSCAN runs over n x n distance
    matrices, no model pass.
    '''
    name, at, version = 'deepsight', (Stage.SERVER_RECEIVE, Stage.SERVER_AGGREGATE), '1'
    needs, acts = frozenset({'uploads'}), frozenset({'transform_update', 'select_and_weight'})

    def __init__(self, readout: str | None = None, tau: float = 1 / 3, threshold_factor: float = 0.01,
                 min_clients: int = 4, min_samples: int = 3, scale: float = 2.0):
        self.readout, self.tau, self.threshold_factor = readout, tau, threshold_factor
        self.min_clients, self.min_samples, self.scale = min_clients, min_samples, scale

    def _module(self, up) -> str | None:
        '''The module that stands in for the output layer, or None when the uploads have no such module.'''
        if self.readout is not None:
            return self.readout if self.readout in up.modules else None
        if not up.modules:
            return None
        layers = [(states.module_info(m)['layer'] if states.module_info(m)['layer'] is not None else -1, m)
                  for m in up.modules]
        return max(layers)[1]

    def run(self, ctx):
        st, up, cids = ctx.state, ctx.uploads, ctx.uploads.clients
        if ctx.stage == Stage.SERVER_AGGREGATE:
            kept = st.get('kept', set(cids))
            return ctx.findings(decision=Decision(excluded=set(cids) - kept, weights={c: 1.0 for c in kept},
                                                  flags={c: why for c, why in st.get('why', {}).items() if c in cids}))
        module = self._module(up)
        if module is None:
            st['kept'], st['why'] = set(cids), {}
            return ctx.findings(evidence={'skipped': 'no LoRA-adapted output layer in the uploads', 'readout': self.readout})
        if len(cids) < self.min_clients:
            st['kept'], st['why'] = set(cids), {}
            return ctx.findings(evidence={'skipped': f'needs at least {self.min_clients} clients, got {len(cids)}',
                                          'readout': module})
        # 1. the NEUP view: Eq. (7) on the readout weight delta, Eqs. (9)-(11), Alg. 1 lines 16-17
        energy = torch.stack([readout_row_l1(up.increment(c, module)) for c in cids])
        te = threshold_exceedings(energy, self.threshold_factor)
        boundary = float(torch.quantile(te.double(), 0.5)) / 2.0
        suspicious = {c: bool(float(t) <= boundary) for c, t in zip(cids, te)}          # Alg. 1 lines 21-22
        # 2. the cosine view: Alg. 1 lines 9-15, over readout weight deltas (see Deviations)
        deltas = [up.increment(c, module).to(torch.float64) for c in cids]
        matrices = [cluster.distances(energy), geometry.cosine_distances_from_gram(lowrank_gram(deltas))]
        # 3. Alg. 2: cluster every view, turn it into co-membership distances, average, cluster again
        merged = torch.stack([co_membership(cluster.density_clusters(D, self.min_samples, self.scale)) for D in matrices]).mean(0)
        final = cluster.density_clusters(merged, self.min_samples, self.scale)
        # 4. the PCI vote: Alg. 1 lines 25-31
        excluded, share = set(), {}
        for group in groups_of(final):
            p = sum(suspicious[cids[i]] for i in group) / len(group)
            for i in group:
                share[cids[i]] = p
            if p >= self.tau:
                excluded |= {cids[i] for i in group}
        kept = set(cids) - excluded
        # 5. the clipping layer: Eq. (12) with S over every upload of the round
        base = up.base_state()
        norms = {c: states.norm(states.delta(up.state(c), base)) for c in cids}
        bound = float(torch.quantile(torch.tensor([norms[c] for c in cids], dtype=torch.float64), 0.5))
        clipped = {c: update.clip_to_norm(up.state(c), base, bound)[0] for c in kept if norms[c] > bound}
        st['kept'] = kept
        st['why'] = {c: f'suspicious share {share[c]:.2f} of its cluster' for c in excluded}
        return ctx.findings(
            scores={c: share[c] for c in cids},
            features={c: {'te': float(t), 'suspicious': float(suspicious[c]), 'cluster_share': share[c],
                          'norm': norms[c], 'readout_energy_max': float(energy[i].max())}
                      for i, (c, t) in enumerate(zip(cids, te))},
            proposals={'transformed': clipped},
            evidence={'readout': module, 'p': int(energy.shape[1]), 'boundary': boundary, 'bound': bound,
                      'clusters': {c: int(final[i]) for i, c in enumerate(cids)},
                      'excluded': sorted(excluded), 'clipped': sorted(clipped),
                      'views': ['neup', 'readout_cosine'],
                      'views_missing': {'output_bias_cosine': 'a LoRA adapter carries no output-layer bias',
                                        'ddif': 'needs 3 x 20000 random inputs through a server-side model'}})
