# plugin.py
"""Proof-of-Learning (Jia et al., 2021, arXiv:2103.05633) as a pair of fedguard plugins: PoLProver
publishes the local training trace of one federated round on the client, PoLVerifier replays it on the
server.

The paper is a proof of training work, not an aggregation defense. The prover records the model weights at
every k-th step, a data signature for every step and the training metadata; the verifier re-executes the
k-step update of the Q largest windows of every epoch from the recorded starting weights and declares FAIL
when the re-executed weights are farther than the slack delta from the claimed ones. Mapped onto this
library, the client of a round is the prover of its local training and the server is the verifier of each
upload. Neither plugin intervenes: the paper defines no disposition for a failed proof, so both are
report-only.

Resource client_data (PoLVerifier): {client id: {sample hash: sample}}, the local training data the
defender expects each client to have used, in the hash space of DataView.manifest. Re-execution needs it:
the batch identity a proof carries is a sample hash, and raw samples do not travel over the message
channel.
Resource init_spec (PoLVerifier): {strategy name: {state-dict key: [normal, loc, scale] or [uniform, low,
high]}}, the publicly known initialization strategies of the paper; a prover claims one of these names for
the first checkpoint of its proof.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import MESSAGE_LIMIT_BYTES, Stage
from fedguard.ops import states

_PROVER = "pol_prover"


# ----------------------------------------------------------------------------------------------------
# Small generic helpers. fedguard.ops has no hypothesis test, no p-norm distance over a state dict and no
# reader for records that arrived over the channel, so those three live here.
# ----------------------------------------------------------------------------------------------------
def _cdf(spec):
    """CDF of a distribution spec (normal, loc, scale) or (uniform, low, high); None when unknown."""
    if not isinstance(spec, (list, tuple)) or len(spec) != 3:
        return None
    kind = str(spec[0])
    try:
        first, second = float(spec[1]), float(spec[2])
    except (TypeError, ValueError):
        return None
    if kind == "normal":
        if second <= 0.0:
            return lambda x: (x >= first).double()
        return lambda x: 0.5 * (1.0 + torch.erf((x - first) / (second * math.sqrt(2.0))))
    if kind == "uniform":
        if second <= first:
            return lambda x: (x >= first).double()
        return lambda x: ((x - first) / (second - first)).clamp(0.0, 1.0)
    return None


def _ks_statistic(values, cdf):
    """Two-sided one-sample Kolmogorov-Smirnov statistic sup_x |F_n(x) - F(x)|."""
    x = values.double().flatten()
    n = int(x.numel())
    if n == 0:
        return 0.0
    xs, _ = torch.sort(x)
    f = cdf(xs)
    ranks = torch.arange(1, n + 1, dtype=torch.float64) / n
    upper = (ranks - f).abs()
    lower = ((ranks - 1.0 / n) - f).abs()
    return float(torch.maximum(upper, lower).max())


def _ks_pvalue(d, n):
    """Asymptotic p-value of the one-sample KS statistic (Kolmogorov distribution)."""
    if n < 1 or d <= 0.0:
        return 1.0
    lam = (math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)) * d
    total = 0.0
    for j in range(1, 101):
        term = 2.0 * ((-1.0) ** (j - 1)) * math.exp(-2.0 * j * j * lam * lam)
        total += term
        if abs(term) < 1e-12:
            break
    return min(1.0, max(0.0, total))


def _state_distance(a, b, keys, kind):
    """d1 and d2 of the paper on factor space: a p-norm over the flattened (a - b), keys in order."""
    parts = []
    for key in keys:
        if key not in a or key not in b or tuple(a[key].shape) != tuple(b[key].shape):
            return None
        parts.append((a[key].double() - b[key].double()).flatten())
    if not parts:
        return None
    d = torch.cat(parts)
    if int(d.numel()) == 0:
        return 0.0
    if kind == "l2":
        return float(d.norm())
    if kind == "l1":
        return float(d.abs().sum())
    if kind == "linf":
        return float(d.abs().max())
    return None


def _int_value(value):
    """A channel value read as an int; None when it is not a finite whole number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)) or float(value) != float(int(value)):
        return None
    return int(value)


def _int_list(value):
    """A channel value read as a list of ints; None when it is not one."""
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        number = _int_value(item)
        if number is None:
            return None
        out.append(number)
    return out


def _float_list(value):
    """A channel value read as a list of finite floats; None when it is not one."""
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            return None
        out.append(float(item))
    return out


def _str_list(value):
    """A channel value read as a list of strings; None when it is not one."""
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, str):
            return None
        out.append(str(item))
    return out


def _record_bytes(messages):
    """A conservative size of a flat channel record: a proof that cannot fit the channel is not sent."""
    total = 0
    for key, value in messages.items():
        total += len(str(key)) + 8
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, str):
                total += len(item) + 4
            else:
                total += 32
    return total


def _windows(steps, checkpoints, keys, kind, epoch_len):
    """Every k-step window with the d1 magnitude of its update, grouped by the epoch of its end step."""
    out = []
    span = max(1, int(epoch_len))
    for i in range(1, len(steps)):
        magnitude = _state_distance(checkpoints[i], checkpoints[i - 1], keys, kind)
        out.append({"start": int(steps[i - 1]), "end": int(steps[i]), "epoch": int(steps[i]) // span,
                    "mag": 0.0 if magnitude is None else magnitude})
    return out


def _top_q(windows, q):
    """The q largest windows of every epoch, ties by step order; every epoch is flushed, the last one too."""
    epochs = {}
    for window in windows:
        epochs.setdefault(window["epoch"], []).append(window)
    out = []
    for epoch in sorted(epochs):
        group = sorted(epochs[epoch], key=lambda window: (-window["mag"], window["start"]))
        out += [(window["start"], window["mag"]) for window in group[: max(0, int(q))]]
    return out


class PoLProver(GuardPlugin):
    """Proof-of-Learning prover (Jia et al., 2021, arXiv:2103.05633): log the local training trace of one
    federated round and publish it over the channel this library gives a client.

    Implemented: at CLIENT_LOSS the identity of every row of the batch is read from
    LossView.sample_ids() and kept as the data signature of the step (Algorithm 1 lines 10-12, P4). At
    CLIENT_STEP the scalar record of the step is read from the trace and, every k steps, the LoRA state
    after that step is kept as the checkpoint W_t of Algorithm 1 lines 13-16 (P5); the received model is
    the checkpoint of step 0, the W_0 of the proof, and the claimed initialization strategy is recorded
    with it (P1 records the claim; the sampling itself is the initialization of the host, not a plugin).
    At CLIENT_POST_TRAIN the checkpoints are flattened into one (n_checkpoints, d) tensor and published as
    the channel attachment pol_prover.checkpoints, with the proof metadata as channel messages: the
    checkpoint steps, the flat per-step data signatures and their batch sizes, the per-step learning
    rates, k, the epoch length, the claimed initialization strategy and the round (P6, without the
    encryption and the signature, which are a cryptographic protocol and out of a plugin).

    Deviations: the checkpoints are LoRA factor states, not whole model weights, and a proof covers one
    federated round, not the whole run; data indices are not sent, the sample hash is the batch identity,
    because DataView.manifest is the only index the client side has and the hash is stable across rounds;
    the epoch length is a parameter of the plugin, because the library does not tell a plugin how the host
    divides its data into epochs; a step whose learning rate the host does not log is published as -1.

    Not implemented: the encryption under the verifier public key, the signature under the prover private
    key and the timestamp or public ledger of Algorithm 1 lines 17-19 and section V-A (rule 3 leaves
    cryptographic protocols outside a plugin); a proof that does not fit the message channel is cut and
    the part that does not fit is not published.

    Open in the paper and chosen here: the plugin publishes its own proof and no key material exists; the
    batch identity is LossView.sample_ids(), which the trainer extension provides and a plain Trainer
    callback does not; the checkpoint of step 0 is the received model; when the record would exceed the
    channel limit the data signatures are dropped first and then whole windows are cut from the end, and
    the evidence says which of the two happened.

    Cost: one copy of the LoRA state per k steps of the round (the storage of section V-B, E*S/k
    checkpoints, here per round) and one flattening of each at CLIENT_POST_TRAIN; the messages carry one
    64-character hash per step, so a few hundred steps fit the 64 KiB channel and a longer round is cut.
    """
    name, at, version = "pol_prover", (Stage.CLIENT_LOSS, Stage.CLIENT_STEP, Stage.CLIENT_POST_TRAIN), "1"
    needs = frozenset({"data", "loss", "train_trace", "received_model"})
    resources = frozenset()
    acts = frozenset()

    def __init__(self, k=1, lr=None, epoch_len=None, init_strategy="unknown"):
        self.k = max(1, int(k))
        self.lr = None if lr is None else float(lr)
        self.epoch_len = None if epoch_len is None else max(1, int(epoch_len))
        self.init_strategy = str(init_strategy)

    def run(self, ctx):
        if ctx.stage == Stage.CLIENT_LOSS:
            return self._on_loss(ctx)
        if ctx.stage == Stage.CLIENT_STEP:
            return self._on_step(ctx)
        return self._publish(ctx)

    def _proof(self, ctx):
        """The proof of this round: step -> batch hashes, step -> learning rate, the checkpoints and notes."""
        proof = ctx.round_state.get("proof")
        if proof is None:
            proof = {"hashes": {}, "lrs": {}, "steps": [], "checkpoints": [], "notes": []}
            ctx.round_state["proof"] = proof
        return proof

    def _step_index(self, ctx):
        """The step number the host is reporting; the trace row is the only place it appears."""
        last = ctx.train_trace.last()
        if last is not None and "step" in last:
            return int(last["step"])
        return len(ctx.train_trace.steps())

    def _on_loss(self, ctx):
        step = self._step_index(ctx)
        try:
            ids = [str(item) for item in ctx.loss.sample_ids()]
        except LookupError:
            ids = None
        self._proof(ctx)["hashes"][step] = ids
        return ctx.findings(evidence={"step": step, "batch": 0 if ids is None else len(ids),
                                      "identified": ids is not None})

    def _on_step(self, ctx):
        step = self._step_index(ctx)
        proof = self._proof(ctx)
        last = ctx.train_trace.last() or {}
        lr = last.get("lr")
        if isinstance(lr, bool) or not isinstance(lr, (int, float)) or not math.isfinite(float(lr)):
            lr = self.lr
        proof["lrs"][step] = None if lr is None else float(lr)
        if (step + 1) % self.k != 0:
            return ctx.findings(evidence={"step": step, "checkpoint": False})
        try:
            state = ctx.train_trace.lora()
        except LookupError:
            proof["notes"].append("no LoRA was offered at step " + str(step))
            return ctx.findings(evidence={"step": step, "checkpoint": False, "reason": "no LoRA offered"})
        proof["steps"].append(step + 1)
        proof["checkpoints"].append(state)
        return ctx.findings(evidence={"step": step, "checkpoint": True, "proof_step": step + 1})

    def _publish(self, ctx):
        proof = self._proof(ctx)
        checkpoints = [ctx.received_model.state()] + list(proof["checkpoints"])
        steps = [0] + [int(item) for item in proof["steps"]]
        n_steps = 0
        for table in (proof["hashes"], proof["lrs"]):
            for key in table:
                n_steps = max(n_steps, int(key) + 1)
        rows, flat, counts, lrs = [], [], [], []
        for step in range(n_steps):
            row = proof["hashes"].get(step)
            row = list(row) if isinstance(row, list) else []
            rows.append(row)
            counts.append(len(row))
            flat += row
            lr = proof["lrs"].get(step)
            lrs.append(float(lr) if isinstance(lr, (int, float)) and not isinstance(lr, bool) else -1.0)
        epoch_len = self.epoch_len if self.epoch_len is not None else max(1, n_steps)
        messages = {"round": int(ctx.round), "k": int(self.k), "epoch_len": int(epoch_len),
                    "n_steps": int(n_steps), "steps": steps, "hashes": flat, "hash_counts": counts,
                    "lrs": lrs, "init_strategy": self.init_strategy}
        evidence = {"checkpoints": len(checkpoints), "steps": n_steps,
                    "identified": sum(1 for row in rows if row), "notes": list(proof["notes"])}
        budget = MESSAGE_LIMIT_BYTES * 3 // 4
        if _record_bytes(messages) > budget:
            messages["hashes"], messages["hash_counts"] = [], []
            evidence["dropped"] = "the per-step data signatures do not fit the message channel"
        if _record_bytes(messages) > budget:
            fixed = _record_bytes({key: value for key, value in messages.items() if key not in ("steps", "lrs")})
            keep = max(0, min(n_steps, max(0, budget - fixed) // 64)) // self.k * self.k
            checkpoints, steps, lrs = checkpoints[: keep // self.k + 1], steps[: keep // self.k + 1], lrs[:keep]
            n_steps = keep
            messages.update({"steps": steps, "lrs": lrs, "n_steps": n_steps})
            evidence.update({"steps": n_steps, "cut": "the proof was cut to " + str(n_steps) + " steps"})
        keys = sorted(checkpoints[0])
        usable = all(all(key in state and tuple(state[key].shape) == tuple(checkpoints[0][key].shape)
                         for key in keys) for state in checkpoints)
        attachments = {}
        if usable:
            attachments["checkpoints"] = torch.stack([states.flatten(state, keys) for state in checkpoints])
        else:
            evidence["error"] = "the checkpoints do not share one LoRA layout"
        return ctx.findings(evidence=evidence, messages=messages, attachments=attachments)


class PoLVerifier(GuardPlugin):
    """Proof-of-Learning verifier (Jia et al., 2021, arXiv:2103.05633): check the proof an upload carries
    and rank the upload by the outcome. Report only: the paper defines no disposition for a failed proof,
    so no client is excluded, reweighted or changed.

    Needs a model on the server side: re-executing a window spends per-sample backward passes through
    ModelHandle.per_sample_gradients, and the server side of this library has no model unless the
    deployment supplies one (the probe argument of the server adapter). Without a handle every selected
    window is reported as unverified instead of FAIL.

    Implemented, for every client of the round: the proof is read from the channel (its messages and the
    pol_prover.checkpoints attachment) and cut back into LoRA states with the layout of the upload; the
    first checkpoint is compared with the broadcast base (the federated form of the warm-start chain of
    trust of section V-D3, because the verifier sent that model itself) and every factor of it is tested
    against the claimed initialization strategy with a one-sample Kolmogorov-Smirnov test at alpha (P8,
    section V-D4); the k-step update magnitude of every window is formed with d1 and the Q largest windows
    of each epoch are selected (P9, P10), the last epoch included (Algorithm 2 flushes a listing only when
    the next epoch starts, so its control flow never verifies the last one); a selected window passes the
    data signature check when every hash of its steps is a hash the defender data holds (P11; the lazy
    reveal of section V-D1 is not possible here, the channel carries records and tensors, not samples),
    and then its k steps are re-executed from the recorded checkpoint with plain gradient descent on the
    factor space, one per-sample backward pass per sample per step, and compared with the claimed
    checkpoint through d2 and delta (P12). A client fails on its first failed check and is otherwise a
    success; a window that could not be executed leaves it unverified rather than failed, and the verdicts
    of all clients are reported (P13).

    Resource client_data: {client id: {sample hash: sample}}, the local training data the defender expects
    each client to have used, in the hash space of DataView.manifest.
    Resource init_spec: {strategy name: {state-dict key: [normal, loc, scale] or [uniform, low, high]}},
    the publicly known initialization strategies of section V-D4.

    Deviations: the weights of a proof are LoRA factors, so d1 and d2 are p-norms over the factor space,
    not over a whole model; the re-execution assumes plain gradient descent without momentum or weight
    decay (the paper requires update() to come from a known acceptable list, section IV-C); the mean of
    ModelHandle.per_sample_gradients is the gradient of the mean per-sample loss, which equals the host
    batch loss only when the samples of the batch carry the same number of labelled tokens; the data
    signature is checked against a defender table of hashes, because a plugin cannot hash text; a window
    is attributed to the epoch of its end step, with the epoch length the prover published.

    Not implemented: the signature check and the decryption of Algorithm 2 lines 1-2 (a cryptographic
    protocol, out of a plugin); the lazy reveal of private data of section V-D1 (no samples cross the
    channel); the calibration of delta (a one-time measurement of two independent runs, section V-C, so
    the parameter is required and with delta=None the distances are reported but no window is judged).

    Open in the paper and chosen here: d1 and d2 default to the Euclidean norm of the factor space and can
    be l1, l2 or linf; the initialization test is per state-dict factor, not per layer, with the
    asymptotic Kolmogorov p-value and a point mass when the scale of the spec is zero; a strategy the
    init_spec does not know is a failure (the known set of section V-D4 is closed) while a key the spec
    does not cover is skipped; the last epoch is flushed explicitly; a window whose data signatures are
    missing or unknown fails the data signature, while a window that cannot be executed (no handle, no
    learning rate, a handle error) is unverified; the proof must name the current round.

    Cost: the dominant cost of the paper (section V-C): Q*E windows of k re-executed steps, here one
    backward pass per sample of every re-executed batch through the model handle, plus the ranking
    arithmetic on the checkpoints of every client; nothing is spent when no model is supplied.
    """
    name, at, version = "pol_verifier", Stage.SERVER_RECEIVE, "1"
    needs = frozenset({"uploads", "reports", "model_handle"})
    resources = frozenset({"client_data", "init_spec"})
    acts = frozenset()

    def __init__(self, Q=1, delta=None, alpha=0.01, d1="l2", d2="l2", tolerance=1e-9):
        self.Q = max(0, int(Q))
        self.delta = None if delta is None else float(delta)
        self.alpha = float(alpha)
        self.d1, self.d2, self.tolerance = str(d1), str(d2), float(tolerance)

    def run(self, ctx):
        verdicts, failures, unverified, windows, features, scores = {}, {}, {}, {}, {}, {}
        for cid in ctx.uploads.clients:
            row = self._verify(ctx, cid)
            verdicts[cid], failures[cid] = row["verdict"], row["failures"]
            unverified[cid], windows[cid] = row["unverified"], row["windows"]
            features[cid], scores[cid] = row["features"], row["score"]
        return ctx.findings(scores=scores, features=features,
                            evidence={"round": ctx.round, "verdicts": verdicts, "failures": failures,
                                      "unverified": unverified, "windows": windows})

    def _metadata(self, ctx, cid):
        """The proof of one client, validated and cut back into states; (None, reason) when unusable."""
        def message(name):
            return ctx.reports.messages(_PROVER + "." + name).get(cid)
        steps, k = _int_list(message("steps")), _int_value(message("k"))
        epoch_len, n_steps = _int_value(message("epoch_len")), _int_value(message("n_steps"))
        if steps is None or k is None or k < 1 or epoch_len is None or epoch_len < 1:
            return None, "no usable proof metadata on the channel"
        if not steps or steps[0] != 0 or any(steps[i] != i * k for i in range(len(steps))):
            return None, "the checkpoint steps of the proof are not the multiples of k"
        tensor = ctx.reports.attachments(_PROVER + ".checkpoints").get(cid)
        if tensor is None or int(tensor.dim()) != 2 or int(tensor.shape[0]) != len(steps):
            return None, "the checkpoint attachment does not match the published steps"
        template = ctx.uploads.state(cid)
        keys = sorted(template)
        checkpoints = []
        for i in range(len(steps)):
            try:
                checkpoints.append(states.unflatten(tensor[i], like=template, keys=keys))
            except (ValueError, KeyError):
                return None, "the checkpoint attachment does not cut into the uploaded LoRA"
        flat, counts = _str_list(message("hashes")), _int_list(message("hash_counts"))
        hashes = []
        if flat is not None and counts is not None:
            at = 0
            for count in counts:
                hashes.append(flat[at:at + max(0, count)])
                at += max(0, count)
        lrs = _float_list(message("lrs")) or []
        return {"steps": steps, "checkpoints": checkpoints, "hashes": hashes, "lrs": lrs, "k": k,
                "epoch_len": epoch_len, "n_steps": n_steps or 0, "strategy": str(message("init_strategy")),
                "round": _int_value(message("round"))}, ""

    def _init_check(self, ctx, strategy, checkpoint, keys):
        """P8, section V-D4: one one-sample KS test per factor at alpha, against the claimed strategy."""
        spec = ctx.resource("init_spec")
        table = spec.get(strategy) if isinstance(spec, dict) else None
        if not isinstance(table, dict):
            return ["the claimed initialization strategy " + repr(strategy) + " is not one the defender knows"], -1.0, 0
        bad, worst, checked = [], 1.0, 0
        for key in keys:
            cdf = _cdf(table.get(key))
            if cdf is None or key not in checkpoint:
                continue
            statistic = _ks_statistic(checkpoint[key].double(), cdf)
            p = _ks_pvalue(statistic, int(checkpoint[key].numel()))
            worst, checked = min(worst, p), checked + 1
            if p < self.alpha:
                bad.append("the initialization of " + key + " fails the KS test (p=" + format(p, ".3g") + ")")
        return bad, worst, checked

    def _handle(self, ctx):
        """The server model, if the deployment supplied one, and the parameter order of its gradients."""
        try:
            handle = ctx.model_handle
        except LookupError:
            return None, []
        try:
            layers = [name for name, _shape in handle.layout("lora", "lora")]
        except Exception:
            return handle, []
        return handle, layers

    def _verify(self, ctx, cid):
        row = {"verdict": "no_proof", "failures": [], "unverified": [],
               "windows": {"total": 0, "checked": 0, "start_steps": [], "distance": {}},
               "features": {"windows": 0, "checked": 0, "init_min_p": -1.0, "max_distance": -1.0}, "score": 0.5}
        meta, reason = self._metadata(ctx, cid)
        if meta is None:
            row["failures"] = [reason or "no usable proof on the channel"]
            return row
        steps = meta["steps"]
        row["windows"]["total"] = len(steps) - 1
        row["features"] = {"windows": len(steps) - 1, "checked": 0, "init_min_p": -1.0, "max_distance": -1.0,
                           "steps": meta["n_steps"], "k": meta["k"], "epoch_len": meta["epoch_len"]}
        if meta["round"] != ctx.round:
            row["verdict"] = "unverified"
            row["unverified"].append("the proof names round " + str(meta["round"]) + ", not " + str(ctx.round))
            row["score"] = 0.5
            return row
        keys = sorted(ctx.uploads.state(cid))
        distance = _state_distance(meta["checkpoints"][0], ctx.uploads.base_state(), keys, "l2")
        if distance is None or distance > self.tolerance:
            row["failures"].append("the first checkpoint is not the model the server sent")
        bad, worst, checked = self._init_check(ctx, meta["strategy"], meta["checkpoints"][0], keys)
        row["failures"] += bad
        row["features"]["init_min_p"], row["features"]["init_keys"] = worst, checked
        selected = _top_q(_windows(steps, meta["checkpoints"], keys, self.d1, meta["epoch_len"]), self.Q)
        row["windows"]["start_steps"] = [start for start, _mag in selected]
        row["windows"]["checked"], row["features"]["checked"] = len(selected), len(selected)
        handle, layers = self._handle(ctx)
        data = ctx.resource("client_data")
        table = data.get(cid) if isinstance(data, dict) else None
        for start, _mag in selected:
            status, distance, why = self._verify_window(meta, start, table or {}, handle, layers)
            row["windows"]["distance"][str(start)] = distance
            if distance is not None:
                row["features"]["max_distance"] = max(row["features"]["max_distance"], distance)
            if status == "fail":
                row["failures"].append("window at step " + str(start) + ": " + why)
            elif status == "unverified":
                row["unverified"].append("window at step " + str(start) + ": " + why)
        if not selected:
            row["unverified"].append("the proof has no k-step window to verify")
        if row["failures"]:
            row["verdict"], row["score"] = "fail", 1.0
        elif row["unverified"]:
            row["verdict"], row["score"] = "unverified", 0.5
        else:
            row["verdict"], row["score"] = "success", 0.0
        return row

    def _verify_window(self, meta, start, client_data, handle, layers):
        """P11 and P12 of one selected window: (status, d2 or None, reason)."""
        end = start + meta["k"]
        rows = [meta["hashes"][step] if step < len(meta["hashes"]) else None for step in range(start, end)]
        if any(row is None or not row for row in rows):
            return "unverified", None, "the proof has no batch identity for one of its steps"
        if any(h not in client_data for row in rows for h in row):
            return "fail", None, "a batch hash of the window is not in the defender data (data signature)"
        lrs = [meta["lrs"][step] if step < len(meta["lrs"]) else -1.0 for step in range(start, end)]
        if any(lr < 0.0 for lr in lrs):
            return "unverified", None, "the proof has no learning rate for one of its steps"
        if handle is None:
            return "unverified", None, "no server model handle, the window was not re-executed"
        samples = [[client_data[h] for h in row] for row in rows]
        state, error = self._reexecute(handle, meta["checkpoints"][start // meta["k"]], layers, samples, lrs)
        if state is None:
            return "unverified", None, error
        keys = sorted(meta["checkpoints"][0])
        distance = _state_distance(state, meta["checkpoints"][end // meta["k"]], keys, self.d2)
        if distance is None:
            return "unverified", None, "the re-executed state does not match the shape of the proof"
        if self.delta is None:
            return "unverified", distance, "no delta was calibrated, the distance is reported"
        if distance > self.delta:
            return "fail", distance, "the re-executed state is " + format(distance, ".6g") + " away, above delta"
        return "pass", distance, "distance " + format(distance, ".3g")

    def _reexecute(self, handle, start_state, layers, samples, lrs):
        """P12: k plain gradient descent steps on the factor space; (None, reason) when not possible."""
        state = dict(start_state)
        for i, batch in enumerate(samples):
            try:
                with handle.lora(state):
                    grads = handle.per_sample_gradients(batch, group="lora", scope="lora")
                if int(grads.shape[0]) != len(batch):
                    return None, "the model handle returned a wrong number of per-sample gradients"
                grad = states.unflatten(grads.double().mean(dim=0), like=state, keys=layers)
                state = states.add(state, grad, -float(lrs[i]))
            except Exception as exc:
                return None, "the re-execution failed with " + type(exc).__name__
        return state, ""
