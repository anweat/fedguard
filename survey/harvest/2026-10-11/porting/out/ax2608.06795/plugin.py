# plugin.py
"""LoRAScan: the activation-spike detector of a backdoored third-party LoRA adapter, at its insertion sites.

The detector of the paper is a serving-time gate, not a training-time defense. A one-off setup on a small
clean prompt set measures, at every LoRA insertion site, the activation-spike statistic of Eq (2) on every
clean prompt, keeps the lowest-variability fraction k of the sites, and reads one upper-tail threshold
tau = median + lambda * MAD off the clean prompt-level scores of Eq (3) and (4). Runtime then spends one
forward pass per user prompt, scores it on the monitored sites and rejects it before generation when the
score is above tau.

fedguard has no inference-time stage: every stage is a point of a federated training round, no data kind
carries a user prompt, and no action can stop a generation. What this plugin does is the half the library
can host. At SERVER_RECEIVE it treats each uploaded LoRA the way the built-in ComplianceProbe treats an
upload, as the adapter under inspection, and runs the setup of the paper on the defender clean prompts with
a defender-supplied model handle; the prompts to screen come in as a second defender-supplied set and the
verdict is reported, never applied.
"""
from __future__ import annotations

import math

import torch

from fedguard.core.plugin import GuardPlugin
from fedguard.core.types import Stage
from fedguard.ops import states as state_ops
from fedguard.ops.robust import coordinate_median

_A, _B = ".lora_A.weight", ".lora_B.weight"
_EPS = 1e-12


def insertion_sites(state):
    """Module prefixes that carry both factors, sorted: the insertion-site set M of the paper.

    fedguard.views.uploads.lora_modules is the same four lines, but fedguard.views.* is not on the import
    allow-list of a plugin file, so they are repeated here.
    """
    a = {name[: -len(_A)] for name in state if name.endswith(_A)}
    b = {name[: -len(_B)] for name in state if name.endswith(_B)}
    return sorted(a & b)


def lora_a_module_map(sites):
    """Model submodule name -> insertion site, for the select argument of activations.

    PEFT keeps the down-projection of a site in a Linear inside a ModuleDict, so the hooked submodule is
    <site>.lora_A or <site>.lora_A.default depending on the PEFT version. Nothing in the library maps a
    LoRA state-dict key to the submodule names activations matches (parameters and layout name parameters,
    not modules), so both spellings are offered and whatever the handle reports back is used.
    """
    names = {}
    for site in sites:
        names[site + ".lora_A"] = site
        names[site + ".lora_A.default"] = site
    return names


def spike_statistic(magnitudes):
    """s_m(x) = M_m(x) * log(1 + M_m(x) / abar_m(x)) from the per-token magnitudes of one site (Eq 2).

    Zero for an empty prompt and for a silent site, where the ratio of the paper has no value.
    """
    if magnitudes.numel() == 0:
        return 0.0
    peak, mean = float(magnitudes.max()), float(magnitudes.mean())
    return peak * math.log1p(peak / mean) if peak > 0.0 and mean > _EPS else 0.0


def low_variance_sites(sigmas, k):
    """Indices of the lowest-variability fraction k of the sites, ascending sigma, ties by site order."""
    n = len(sigmas)
    if n == 0:
        return []
    keep = max(1, int(math.floor(k * n + 0.5)))
    return sorted(sorted(range(n), key=lambda i: (sigmas[i], i))[:keep])


def median_mad_threshold(scores, lam):
    """(median, MAD, median + lam * MAD): the one-sided upper-tail threshold of Eq (4).

    The median is fedguard.ops.robust.coordinate_median of a column, i.e. the 0.5 quantile (the mean of the
    two middle values for an even count). bd is the raw MAD, with no Gaussian-consistency factor.
    """
    x = torch.as_tensor(list(scores), dtype=torch.float64)
    if x.numel() == 0:
        return 0.0, 0.0, 0.0
    med = float(coordinate_median(x.reshape(-1, 1))[0])
    mad = float(coordinate_median((x - med).abs().reshape(-1, 1))[0])
    return med, mad, med + lam * mad


class LoRAScan(GuardPlugin):
    """LoRAScan activation-spike detector, calibrated and applied to each uploaded LoRA at SERVER_RECEIVE.

    For every insertion site m of the adapter, the down-projection bottleneck output A_m h is collected per
    prompt token and turned into the spike statistic s_m(x) = max_t a_{m,t} * log(1 + max_t a_{m,t} /
    mean_t a_{m,t}) (Eq 2); the setup keeps the fraction k of sites with the smallest standard deviation
    across the clean prompts, normalizes their spike statistics with the clean mean and standard deviation
    and averages them into the prompt-level score S_k(x) (Eq 3); one threshold
    tau = median + lambda * MAD of the clean prompt scores is read off Eq (4) per adapter. A screening
    prompt is flagged when S_k(x) > tau, the reject rule of the paper.

    Resource clean_prompts: a sequence of trusted, unlabelled prompts (the paper samples 40 from Stanford
    Alpaca); used only for calibration, nothing is trained on them. Any sample the model handle accepts.
    Resource screen_prompts: the prompts to judge against each threshold. The gate of the paper scores one
    user prompt at generation time; the library has no such stage, so the batch to judge is handed in here.
    Needs model_handle, which the host does not provide on the server side: the defender supplies one
    (fedguard.views.model.ModelHandle is the contract). It must load an uploaded LoRA with lora(state) and
    return the lora_A submodules outputs from activations(prompts, select=..., pool="none",
    what="output"): one (tokens, r) tensor per prompt, with the adapter active.

    Implemented: per-token magnitude of the A-side bottleneck, the spike statistic of Eq (2), the clean
    mean and standard deviation per site, the lowest-variance fraction k selection, the z-normalized
    average of Eq (3), the median + lambda * MAD threshold of Eq (4), and the threshold comparison that
    says which screening prompts this adapter would trigger on. The setup is held in ctx.state per client
    and reused while the same adapter comes back, which is the paper phrase performed once per adapter.
    Deviations: the setting of the paper is a platform serving one downloaded adapter to end users, not a
    federated round. Here each uploaded LoRA is inspected as the adapter under inspection, the reading the
    built-in ComplianceProbe gives an upload; the clean and screening prompt sets are the defender asset,
    not Alpaca; and a flagged prompt is reported, never blocked.
    Not implemented: the gate itself, rejecting a user prompt before generation. There is no inference
    stage, no data kind carrying a user prompt, and no action that stops a generation; mask_samples and
    edit_samples remove or rewrite the local training samples of a client at CLIENT_PRE_TRAIN, which is not
    this method (the paper removes no training sample and never touches the adapter). Also outside the
    plugin: hosting the base model and adapter, tokenization, and the generation it would guard.
    Open in the paper and chosen here: activation magnitude is the L2 norm of the raw A-side bottleneck,
    with no alpha/r scaling (the paper does not define it; magnitude="l1" switches to the L1 norm); sigma_m
    is the sample standard deviation (ddof=1), 0 when a site has one clean prompt; bd_k is the raw MAD,
    not multiplied by 1.4826, which is what makes lambda = 4.45 equal to three Gaussian-consistent MAD
    units as the paper says; |M_k| = max(1, round-half-up(k * |M|)) and sigma ties are broken by site order
    (the paper gives neither rule); a selected site whose sigma is <= 1e-12 is dropped from the average
    instead of contributing an undefined z-score, and n_monitored reports how many sites remain; a site
    whose activations the handle does not report is counted as unmatched and skipped; the module names
    tried are <site>.lora_A and <site>.lora_A.default; the same adapter is recognized by (number of
    entries, sum of all factor values), so two adapters with the same sum would share a setup; the
    calibration forward pass runs with the uploaded adapter loaded by the handle, and an adapter that is
    not active reports nothing and is recorded as unmatched.
    Cost: per adapter on first sight, one forward pass over every clean prompt (n) and one over every
    screening prompt (m); afterwards m per round while the adapter is unchanged, plus one read of every
    factor for the reuse check. No backward passes, no generation, no training. The handle counts the
    passes and the runner writes the share of the plugin into findings.cost. The setup kept per client is
    2 floats per measured site plus the site list.
    """
    name, at, version = "lorascan", Stage.SERVER_RECEIVE, "1"
    needs = frozenset({"uploads", "model_handle"})
    resources = frozenset({"clean_prompts", "screen_prompts"})
    acts = frozenset()

    def __init__(self, k: float = 0.05, lam: float = 4.45, magnitude: str = "l2"):
        if magnitude not in ("l2", "l1"):
            raise ValueError("magnitude must be l2 or l1")
        self.k, self.lam, self.magnitude = float(k), float(lam), magnitude

    def run(self, ctx):
        uploads, handle = ctx.uploads, ctx.model_handle
        clean = list(ctx.resource("clean_prompts"))
        screen = list(ctx.resource("screen_prompts"))
        scores, features, adapters = {}, {}, {}
        for cid in uploads.clients:
            state = uploads.state(cid)
            sites = insertion_sites(state)
            names = lora_a_module_map(sites)
            if not names:
                features[cid] = {"n_sites": 0.0}
                adapters[cid] = {"error": "the upload has no lora_A/lora_B pair"}
                continue
            with handle.lora(state):
                setup, reused = self._setup(ctx, cid, state, handle, sites, names, clean)
                row = self._screen(handle, names, setup, screen) if setup["monitored"] else {"scores": [], "rejected": []}
            for i, value in enumerate(row["scores"]):
                scores[f"{cid}#p{i}"] = value
            f = {"n_sites": float(len(setup["measured"])), "n_selected": float(len(setup["selected"])),
                 "n_monitored": float(len(setup["monitored"])), "screened": float(len(screen)),
                 "rejected": float(len(row["rejected"])), "reused_setup": float(reused)}
            if setup["monitored"]:
                f["tau"] = setup["tau"]
                f["max_score"] = max(row["scores"]) if row["scores"] else 0.0
            features[cid] = f
            adapters[cid] = {"selected_sites": setup["selected"], "monitored_sites": setup["monitored"],
                             "rejected_prompts": row["rejected"], "clean_median": setup["bm"],
                             "clean_mad": setup["bd"], "reused_setup": reused}
            if setup["unmatched"]:
                adapters[cid]["unmatched_sites"] = setup["unmatched"]
        return ctx.findings(scores=scores, features=features, evidence={"adapters": adapters})

    def _setup(self, ctx, cid, state, handle, sites, names, clean):
        """The paper setup once per adapter: recomputed only when the uploaded factors change."""
        store = ctx.state.setdefault("setup", {})
        key = (len(state), float(state_ops.flatten(state).sum()))
        cached = store.get(cid)
        if cached is not None and cached["key"] == key:
            return cached, True
        setup = self._fit(sites, self._spikes(handle, names, clean), len(clean))
        setup["key"] = key
        store[cid] = setup
        return setup, False

    def _fit(self, sites, spikes, n_prompts):
        """Per-site mean and sigma on the clean set, the low-variance selection and the threshold."""
        measured = [s for s in sites if len(spikes.get(s, ())) == n_prompts]
        sigma, mu = {}, {}
        for s in measured:
            x = torch.as_tensor(spikes[s], dtype=torch.float64)
            mu[s] = float(x.mean())
            sigma[s] = float(x.std()) if x.numel() > 1 else 0.0
        selected = [measured[i] for i in low_variance_sites([sigma[s] for s in measured], self.k)]
        monitored = [s for s in selected if sigma[s] > _EPS]
        bm, bd, tau = median_mad_threshold([self._prompt_score(spikes, mu, sigma, monitored, i)
                                            for i in range(n_prompts)], self.lam)
        return {"measured": measured, "unmatched": [s for s in sites if s not in measured], "mu": mu,
                "sigma": sigma, "selected": selected, "monitored": monitored, "bm": bm, "bd": bd, "tau": tau}

    def _spikes(self, handle, names, prompts):
        """One activations call over a prompt set: site -> [s_m(x)] in prompt order."""
        got = handle.activations(prompts, select=lambda name: name in names, pool="none", what="output")
        spikes = {site: [] for site in names.values()}
        for name, per_sample in got.items():
            spikes[names[name]] = [spike_statistic(self._magnitudes(tokens)) for tokens in per_sample]
        return spikes

    def _magnitudes(self, tokens):
        if self.magnitude == "l1":
            return tokens.detach().abs().sum(dim=-1)
        return tokens.detach().norm(dim=-1)

    def _prompt_score(self, spikes, mu, sigma, monitored, index):
        """Eq (3) for one prompt: the equal-weight mean of the monitored site z-scores."""
        if not monitored:
            return 0.0
        return float(sum((spikes[s][index] - mu[s]) / sigma[s] for s in monitored) / len(monitored))

    def _screen(self, handle, names, setup, screen):
        """Score the prompts to judge with the calibrated sites and apply the threshold."""
        wanted = {name: site for name, site in names.items() if site in setup["monitored"]}
        spikes = self._spikes(handle, wanted, screen)
        usable = [s for s in setup["monitored"] if len(spikes.get(s, ())) == len(screen)]
        out = [self._prompt_score(spikes, setup["mu"], setup["sigma"], usable, i) for i in range(len(screen))]
        return {"scores": out, "rejected": [i for i, v in enumerate(out) if usable and v > setup["tau"]]}
