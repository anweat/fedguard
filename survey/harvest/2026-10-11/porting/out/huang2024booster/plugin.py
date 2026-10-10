# plugin.py
"""Booster (Huang et al., 2024) -- no runnable object is defined in this file.

Booster is an alignment-stage method. It turns an already safety-aligned base weight w into a
vaccinated checkpoint w~ by a one-time, centralised training run (Algorithm 1), finished before the
service exists. Its output is the base model that every later fine-tuning request starts from, and
the paper states that fine-tuning itself then stays ordinary SFT (Appendix C). That setting has no
clients, no rounds and no aggregation (Section 3.1); federated instruction tuning appears only as
future work (Appendix H).

Every stage fedguard defines is a position inside one federated round, and a plugin is called once
per stage per round. The library owns no training loop, no optimizer and no epoch; the server side
receives no samples; no action installs a finished checkpoint as the base model. None of Algorithm
1's ten steps can be mounted. This file therefore defines nothing runnable: the guide's rule 8 asks
for a placeholder, and fedguard's own contract check refuses an object whose stage list is empty, so
a declaration-only shell cannot exist either.

Implemented:
    Nothing. Steps 1-10 of Algorithm 1 all lie outside every available stage.

Deviations:
    Nothing was ported, so nothing was rewritten; the plugin file is a documentation-only
    placeholder with no code, and the test file is empty (rule 8). Two mechanical workarounds were
    rejected. (1) A client-side CLIENT_PRE_STEP plugin that adds lambda * (grad_h(w) - grad_h(w'))
    to the client's own local gradient through `transform_gradients`: that is the federated
    extension the paper leaves open (Appendix H), it never produces w~, and it swaps the defender's
    alignment-data gradient for the client's local-data gradient -- another method, not this one.
    (2) Training Booster outside the library and carrying w~ in as a resource to broadcast: all ten
    steps stay outside, which is transport, not a port. Full weights versus LoRA factors is not the
    obstacle: the paper's trainable parameters are LoRA adapters too (rank 32, alpha 4), and a
    factor-space update would be acceptable.

Not implemented:
    Steps 1-2 (sampling the alignment and harmful batches), 3 (the optional Vaccine+Booster
    embedding perturbation), 4, 5 and 8 (the three forward/backward passes of one step), 6-7
    (normalising the harmful gradient and forming the perturbed weights), 9 (the composite gradient)
    and 10 (the AdamW update); also the deployment of w~ as the service's base model.

Open in the paper and chosen here:
    No choice was implemented. A port would have to settle, with the paper silent: the scope of
    ||grad_h(w)|| (globally flattened L2 or per-layer), which parameters the perturbation covers
    (the LoRA adapters only, or also embeddings and LayerNorm), the label masking and reduction of
    h(w), whether the two batches are paired and how they are drawn, the guard for ||grad_h(w)||
    near zero, and how the composite gradient is handed to AdamW.

Cost:
    Zero here: nothing runs, no sample is read, no model pass is spent. The paper's own cost is
    three forward/backward passes per alignment step - 1.86 h against 0.54 h for plain SFT on
    Llama2-7B, peak memory 57.86 GB against 49.33 GB (Table 5) - paid once before the service
    starts, with no extra cost during fine-tuning.

Resource `alignment_data`:
    The defender's alignment set (harmful prompt - safe answer pairs, about 5000 samples from the
    extended BeaverTails of Section 5.1); needed by steps 1 and 4, unused here.
Resource `harmful_data`:
    The defender's harmful set (harmful prompt - harmful answer pairs, about 5000 samples, the same
    distribution as the harmful part of user data but different samples); needed by steps 2, 5 and
    8, unused here.
Resource `base_model`:
    The aligned base weights w to vaccinate, with the alignment run's LoRA configuration (rank 32,
    alpha 4); needed by steps 4-10 and by the deployment of w~, unused here.
"""
