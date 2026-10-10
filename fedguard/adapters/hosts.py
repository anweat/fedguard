"""What each host framework lets the library reach, and at what cost to the host.

fedguard is mounted on an existing federated fine-tuning framework; it does not run training itself.
How much of it can be mounted depends on the extension points the host offers. A HostProfile states,
per stage and per data kind, how the library gets there:

    native   through the host's own extension points; no line of the host or of the user's app changes
    glue     the user's app has to call the library from inside its own code (e.g. in its train function)
    extension  reachable only through an extension layer of this library that changes the host's own
             protocol (using the host's public API). Off by default; switching it on emits a
             HostExtensionWarning and is written into the run's record.
    patch    the host has no extension point there; its training script has to be edited
    (absent) not reachable on this host with the adapters shipped here

An adapter calls `require(runner, profile)` when it is built, so a plugin that needs a stage the host
cannot reach is refused before the first round instead of silently never running.

    python -m fedguard.adapters.hosts        # the support table, as Markdown
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

from fedguard.core.plugin import ContractError
from fedguard.core.types import Stage, side_of

LEVELS = ("native", "glue", "extension", "patch")


class HostExtensionWarning(UserWarning):
    """The run uses an extension layer that changes how the host framework itself would run."""


S = Stage
# The same on every host whose clients train with a Hugging Face Trainer: see fedguard.adapters.hf_trainer_ext.
TRAINER_EXTENSION = ((S.CLIENT_LOSS,),
                     "replaces the compute_loss of the trainer the host built with a wrapper, so that plugins read the "
                     "batch, the outputs and the loss before backward and may change the loss "
                     "(fedguard.adapters.hf_trainer_ext); a Trainer by itself exposes that point to nobody")
TRAINER_NOTE = "between forward and backward a Trainer has no callback; use fedguard.adapters.hf_trainer_ext (an extension that changes the trainer)"


@dataclass(frozen=True)
class HostProfile:
    """What one host framework lets the library reach, as data. Adapters check plugins against it when they
    mount them; the support tables in the documentation are printed from it.
    """
    name: str
    title: str
    how: str                                         # how the library is attached, in one sentence
    stages: dict = field(default_factory=dict)       # Stage -> level
    kinds: dict = field(default_factory=dict)        # data kind -> level, where it differs from its stage's level
    actions: dict = field(default_factory=dict)      # action -> level, where it differs from its stage's level
    server_unavailable: frozenset = frozenset()      # data kinds the server-side adapter does not provide
    notes: dict = field(default_factory=dict)        # Stage -> why it is missing or what the glue is
    extensions: dict = field(default_factory=dict)   # extension name -> (stages it adds, what it changes in the host)
    floor: str = "native"                            # the least any mounting costs on this host

    def level(self, stage: Stage, kinds=(), actions=()) -> str | None:
        """The costliest level among a stage, the data kinds read there and the actions taken; None if unreachable."""
        if stage not in self.stages:
            return None
        glue = ["glue"] if side_of(stage) == "server" and set(kinds) & self.server_unavailable else []
        return max([self.floor, self.stages[stage], *glue, *(self.kinds[k] for k in kinds if k in self.kinds and side_of(stage) != "server"),
                    *(self.actions[a] for a in actions if a in self.actions)], key=LEVELS.index)


FLOWER = HostProfile(
    name="flower", title="Flower（Message API，1.39）",
    how="GuardStrategy wraps the app's strategy; guard_mod is added to the ClientApp's mods.",
    stages={S.SERVER_DISTRIBUTE: "native", S.SERVER_RECEIVE: "native", S.SERVER_AGGREGATE: "native", S.SERVER_POST_AGGREGATE: "native",
            S.CLIENT_PRE_TRAIN: "native", S.CLIENT_POST_TRAIN: "native", S.CLIENT_PRE_STEP: "glue", S.CLIENT_STEP: "glue",
            S.CLIENT_ANNOUNCE: "extension", S.SERVER_EXCHANGE: "extension", S.CLIENT_LOSS: "extension"},
    extensions={"trainer": TRAINER_EXTENSION, "handshake": ((S.CLIENT_ANNOUNCE, S.SERVER_EXCHANGE),
                              "adds a query round trip and a second broadcast of the adapter before every training round "
                              "(fedguard.adapters.flower_handshake); the plain strategy has one round trip per round")},
    kinds={"data": "glue", "model_handle": "glue", "gradients": "glue", "train_trace": "glue"},
    actions={"mask_samples": "glue", "edit_samples": "glue", "transform_received": "glue", "transform_gradients": "glue"},
    server_unavailable=frozenset({"model_handle"}),
    notes={S.CLIENT_LOSS: TRAINER_NOTE,
           S.CLIENT_ANNOUNCE: "needs a round trip before training, which the Strategy interface does not have; "
                              "use fedguard.adapters.flower_handshake (an extension that changes the protocol)",
           S.SERVER_EXCHANGE: "needs a round trip before training, which the Strategy interface does not have; "
                              "use fedguard.adapters.flower_handshake (an extension that changes the protocol)",
           S.CLIENT_PRE_STEP: "the app's train function adds GuardStepCallback to its trainer",
           S.CLIENT_STEP: "the app's train function adds GuardStepCallback to its trainer",
           S.CLIENT_PRE_TRAIN: "the Mod sees the received model; samples and a model handle only if the train function calls guard.pre_train(...)"})

OPENFEDLLM = HostProfile(
    name="openfedllm", title="OpenFedLLM 系脚本（含 FedLLM-Attack）",
    how="The host is a script without extension points: calls to OpenFedLLMGuard and ClientGuard are edited into its round loop.",
    floor="patch",
    stages={**{s: "patch" for s in (S.SERVER_DISTRIBUTE, S.CLIENT_ANNOUNCE, S.SERVER_EXCHANGE, S.CLIENT_PRE_TRAIN, S.CLIENT_PRE_STEP,
                                    S.CLIENT_STEP, S.CLIENT_POST_TRAIN, S.SERVER_RECEIVE, S.SERVER_AGGREGATE, S.SERVER_POST_AGGREGATE)},
            S.CLIENT_LOSS: "extension"},
    extensions={"trainer": TRAINER_EXTENSION},
    notes={S.CLIENT_LOSS: TRAINER_NOTE,
           S.CLIENT_PRE_STEP: "through the HF Trainer callback the script adds to each client's trainer",
           S.CLIENT_STEP: "through the HF Trainer callback the script adds to each client's trainer"})

HOSTS = {h.name: h for h in (FLOWER, OPENFEDLLM)}


def mount_level(plugin, host: HostProfile) -> str | None:
    """How a plugin can be mounted on a host: the costliest level over its stages, None if any stage is unreachable."""
    at = plugin.at                                    # works for a plugin class as well as an instance
    stages = (at,) if isinstance(at, Stage) else tuple(at)
    levels = [host.level(s, plugin.needs, plugin.acts) for s in stages]
    return None if None in levels or not levels else max(levels, key=LEVELS.index)


def needed_extensions(plugin, host: HostProfile) -> list[str]:
    """The extension layers of this host a plugin cannot be mounted without."""
    at = plugin.at
    stages = set((at,) if isinstance(at, Stage) else at)
    return sorted(name for name, (adds, _) in host.extensions.items() if stages & set(adds) and
                  any(host.stages.get(s) == "extension" for s in stages & set(adds)))


def warn_extension(host: HostProfile, name: str) -> str:
    text = (f"fedguard extension {name!r} is on for host {host.name!r}: this is not the host's original behavior. "
            f"It {host.extensions[name][1]}.")
    warnings.warn(text, HostExtensionWarning, stacklevel=3)
    return text


def require(runner, host: HostProfile, extensions=frozenset(), server_model_handle: bool = False) -> None:
    """Refuse plugins this host cannot serve. Called by the adapters; `runner` may be None (capture only).
    Stages at level `extension` need the matching extension layer to be the one mounting the runner.
    server_model_handle: the app handed the server-side adapter a model handle of its own."""
    if runner is None:
        return
    extensions = frozenset(extensions)
    unknown = extensions - set(host.extensions)
    if unknown:
        raise ContractError(f"host {host.name!r} has no extension {sorted(unknown)}")
    enabled = {s for e in extensions for s in host.extensions[e][0]}
    for p in runner.plugins:
        missing = [s for s in p.stages if s not in host.stages or (host.stages[s] == "extension" and s not in enabled)]
        if missing:
            why = "; ".join(f"{s.value}: {host.notes.get(s, 'not reachable')}" for s in missing)
            raise ContractError(f"{p.name}: the host {host.name!r} cannot run it as mounted ({why})")
        lacking = set(p.needs) & (host.server_unavailable - ({"model_handle"} if server_model_handle else set()))
        if runner.side == "server" and lacking:
            raise ContractError(f"{p.name}: the server-side adapter of {host.name!r} does not provide {sorted(lacking)}"
                                + ("; pass a model handle as `probe`" if "model_handle" in lacking else ""))
    runner.host = host.name
    runner.host_extensions = sorted(extensions)
    if runner.recorder is not None:                   # run.json was written when the runner was built, before it had a host
        runner.recorder.write_run(runner.describe())


def support_table() -> str:
    zh = {"native": "原生", "glue": "应用配合", "extension": "扩展层（改了宿主流程）", "patch": "改脚本", None: "不支持"}
    out = ["| 位置 | " + " | ".join(h.title for h in HOSTS.values()) + " |", "|---|" + "---|" * len(HOSTS)]
    for s in Stage:
        out.append(f"| `{s.name}` | " + " | ".join(zh[h.stages.get(s)] for h in HOSTS.values()) + " |")
    out += ["", "| 数据类别（与所在位置的级别不同时） | " + " | ".join(h.title for h in HOSTS.values()) + " |", "|---|" + "---|" * len(HOSTS)]
    for k in sorted({k for h in HOSTS.values() for k in h.kinds}):
        out.append(f"| `{k}` | " + " | ".join(zh[h.kinds[k]] if k in h.kinds else "同所在位置" for h in HOSTS.values()) + " |")
    out += ["", "| 动作（与所在位置的级别不同时） | " + " | ".join(h.title for h in HOSTS.values()) + " |", "|---|" + "---|" * len(HOSTS)]
    for a in sorted({a for h in HOSTS.values() for a in h.actions}):
        out.append(f"| `{a}` | " + " | ".join(zh[h.actions[a]] if a in h.actions else "同所在位置" for h in HOSTS.values()) + " |")
    for h in HOSTS.values():
        for name, (stages, what) in h.extensions.items():
            out += ["", f"{h.title} 的扩展层 `{name}`：提供 {'、'.join(f'`{s.name}`' for s in stages)}。默认关闭；启用时发出警告并写入记录。它改变宿主的原有流程：{what}。"]
    lacking = {h.title: sorted(h.server_unavailable) for h in HOSTS.values() if h.server_unavailable}
    out += [""] + [f"{t} 的服务器侧适配器自己不提供：{'、'.join(f'`{k}`' for k in ks)}（宿主不给服务器一个可运行的模型；应用可以自己传入一个模型句柄，属于应用配合）。" for t, ks in lacking.items()]
    return "\n".join(out)


if __name__ == "__main__":
    print(support_table())
