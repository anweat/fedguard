"""Published defenses ported as plugins, grouped by the control point they work at.

    server_uploads.py   server side, on the uploaded updates
    client_samples.py   client side, before training, on the client's samples
    client_model.py     client side, on the received adapter and on the local result
    client_step.py      client side, inside a local training step
    two_sided.py        a part on each side, talking over the message channel
    shared.py           helpers used by more than one of the above

They are examples and test cases of the library, not its product. See each class's docstring for what is
implemented, what is not, and which choices the paper left open; none has been validated against the
authors' code or their reported numbers. The catalogue generated from the declarations is CATALOG.md
(`python -m fedguard.methods write`).
"""
from fedguard.methods.client_model import ReceivedAdapterScan, UpdateSubspaceProjection
from fedguard.methods.client_samples import ActivationClustering, GradientSpectralEntropy, Onion, SafetyMix, SpectralSignatures
from fedguard.methods.client_step import AlternatingNoisyLoRA, LALoRAPerSample, LisaBiState, LisaProximal
from fedguard.methods.server_uploads import (CRFL, FLAME, MCD, CoordinateMedian, FLDetector, FLTrust, FoolsGold, FreqFed, Krum, LoMar,
                                             MudHoG, SafeFedLLMClientLevel, SafeLoRA, TrimmedMean)
from fedguard.methods.two_sided import ProtegoFedClient, ProtegoFedServer, SafeFedLLMStepProbe, SafeFedLLMStepTrust

METHODS = {p.name: p for p in (
    Krum, CoordinateMedian, TrimmedMean, FoolsGold, FLTrust, FLAME, FreqFed, FLDetector, MudHoG, LoMar, MCD, CRFL,
    SafeFedLLMClientLevel, SafeLoRA,
    SpectralSignatures, GradientSpectralEntropy, ActivationClustering, Onion, SafetyMix,
    ReceivedAdapterScan, UpdateSubspaceProjection,
    AlternatingNoisyLoRA, LisaProximal, LisaBiState, LALoRAPerSample,
    SafeFedLLMStepProbe, SafeFedLLMStepTrust, ProtegoFedClient, ProtegoFedServer)}

__all__ = ["METHODS", *sorted(p.__name__ for p in METHODS.values())]
