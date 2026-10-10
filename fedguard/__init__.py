"""fedguard: an add-on library for LoRA fine-tuning of language models on existing federated frameworks.

It does not train. The host framework (Flower, an OpenFedLLM-style script) trains, aggregates and
communicates; the library is called at fixed points of a round, where plugins read what passes through,
propose changes, and everything is recorded.

Layers, each importing only from those below it (tests/test_architecture.py checks this):
  adapters/                 the only code that knows a host framework or transformers: how each host is
                            mounted, what it can reach (hosts.py), and the opt-in extension layers that go
                            beyond a host's own behavior (flower_handshake.py, hf_trainer_ext.py)
  policy.py                 a set of controls that run together, as a file: what is mounted on each side,
                            with which arguments, and whose actions are enforced
  client.py, replay.py      one client's side of a run; re-running plugins over a recorded run
  core/                     stages, data kinds and actions (types.py, actions.py), the plugin contract, the runner
  views/, recorder/         what plugins read at a stage; what is written to disk
  ops/                      stateless tensor operators (LoRA-specific, or shared by two or more methods)
Built on top, as examples and test cases rather than as the product:
  plugins/                  small built-in plugins that show the contract
  methods/                  published defenses ported as plugins (catalogue: methods/CATALOG.md)
  kb/                       threats, defenses, implementations and evidence as data, checked against the code
"""
from fedguard.core.types import ClientUpdate, Decision, Findings, RunSpec, Stage
from fedguard.core.plugin import ContractError, GuardPlugin
from fedguard.core.runner import GuardRunner

__all__ = ["ClientUpdate", "ContractError", "Decision", "Findings", "GuardPlugin", "GuardRunner", "RunSpec", "Stage"]
