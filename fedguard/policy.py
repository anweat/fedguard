"""A control policy: which controls are mounted on each side, with which arguments, and whose actions
are enforced. One file describes a set of controls that run together, so that the same set can be
mounted on another host, kept under version control, and named in the record of a run.

    policy: 1                           # format version
    name: baseline
    server:
      fail: open                        # open: a failing control is recorded and skipped; closed: the run stops
      controls:
        - use: effect_stats             # observes only
        - use: krum
          args: {f: 1, m: 5}
          enforce: true                 # its actions are applied; without it they are recorded, not applied
    client:
      controls:
        - {use: lisa, args: {k_align: 1, k_finetune: 2}, enforce: true}
    extensions: [trainer]               # extension layers the policy relies on; never switched on implicitly

`use` is a name from fedguard.plugins.BUILTIN or fedguard.methods.METHODS, or `package.module:Class` for a
plugin of your own. Controls run in the order written. A control is mounted alert-only unless it says
`enforce: true`. Unknown keys, unknown names, a control on the wrong side and a name used twice are
errors at load time.

    policy = Policy.load("baseline.yaml")
    runner = policy.runner("server", spec, recorder, resources={...})     # a GuardRunner
    policy.resources("client")                                            # the assets the caller has to supply
    python -m fedguard.policy baseline.yaml                               # what it mounts, and what each host needs for it

What a policy decides, and what it cannot:
  it decides    which controls are mounted, in which order, with which constructor arguments, whose actions
                are enforced, what happens when a control fails, which extension layers may be used
  a plugin's    where a control runs, what it reads, which resources it needs and which actions it may
                propose are declared by the plugin class; a policy cannot widen, narrow or rename them
  the mounter's the host, the model, the data, the content of the resources, whether records are written;
                a policy names none of them, so the same file mounts on any host that can serve it
  the library's checking all of the above against each other, running the controls, applying enforced
                actions, merging decisions, recording; a plugin is never told whether it is enforced
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from fedguard.core.plugin import ContractError, GuardPlugin
from fedguard.core.runner import GuardRunner
from fedguard.core.types import RunSpec, side_of

FORMAT = 1
SIDES = ("server", "client")


class PolicyError(ContractError):
    """The policy file is malformed or names something that does not exist."""


@dataclass(frozen=True)
class Control:
    """One entry of a policy: a plugin, its constructor arguments, and whether its actions are applied."""
    use: str
    args: dict = field(default_factory=dict)
    enforce: bool = False

    def build(self) -> GuardPlugin:
        cls = resolve(self.use)
        try:
            return cls(**self.args)
        except TypeError as exc:
            raise PolicyError(f"control {self.use!r}: {exc}") from exc


@dataclass(frozen=True)
class SidePolicy:
    """The controls of one side, in mount order, and what happens when one of them fails."""
    controls: tuple[Control, ...] = ()
    fail: str = "open"


def registry() -> dict:
    from fedguard.methods import METHODS
    from fedguard.plugins import BUILTIN
    return {**BUILTIN, **METHODS}


def resolve(use: str):
    """The plugin class a `use` names: a shipped plugin, or `package.module:Class`."""
    if ":" in use:
        module, _, name = use.partition(":")
        try:
            cls = getattr(importlib.import_module(module), name)
        except (ImportError, AttributeError) as exc:
            raise PolicyError(f"control {use!r} cannot be imported: {exc}") from exc
        if not (isinstance(cls, type) and issubclass(cls, GuardPlugin)):
            raise PolicyError(f"control {use!r} is not a GuardPlugin class")
        return cls
    table = registry()
    if use not in table:
        raise PolicyError(f"unknown control {use!r}; shipped controls: {', '.join(sorted(table))}")
    return table[use]


def _only(where: str, got: dict, allowed: set) -> None:
    if not isinstance(got, dict):
        raise PolicyError(f"{where}: expected a mapping")
    if extra := set(got) - allowed:
        raise PolicyError(f"{where}: unknown keys {sorted(extra)}; allowed: {sorted(allowed)}")


@dataclass(frozen=True)
class Policy:
    """A loaded control policy. Immutable; `digest` identifies its content in records."""
    name: str = "unnamed"
    server: SidePolicy = SidePolicy()
    client: SidePolicy = SidePolicy()
    extensions: frozenset = frozenset()

    # ----- construction -----
    @classmethod
    def from_dict(cls, raw: dict) -> "Policy":
        _only("policy", raw, {"policy", "name", "server", "client", "extensions"})
        if raw.get("policy", FORMAT) != FORMAT:
            raise PolicyError(f"policy format {raw.get('policy')!r} is not supported (this library reads format {FORMAT})")
        sides = {}
        for side in SIDES:
            block = raw.get(side) or {}
            _only(side, block, {"controls", "fail"})
            if block.get("fail", "open") not in ("open", "closed"):
                raise PolicyError(f"{side}.fail must be open or closed")
            controls = []
            for n, entry in enumerate(block.get("controls") or []):
                entry = {"use": entry} if isinstance(entry, str) else entry
                _only(f"{side}.controls[{n}]", entry, {"use", "args", "enforce"})
                if not isinstance(entry.get("use"), str) or not isinstance(entry.get("args", {}), dict) \
                        or not isinstance(entry.get("enforce", False), bool):
                    raise PolicyError(f"{side}.controls[{n}]: `use` is a name, `args` a mapping, `enforce` true or false")
                controls.append(Control(entry["use"], dict(entry.get("args", {})), entry.get("enforce", False)))
            sides[side] = SidePolicy(tuple(controls), block.get("fail", "open"))
        extensions = raw.get("extensions") or []
        if not isinstance(extensions, list) or not all(isinstance(e, str) for e in extensions):
            raise PolicyError("extensions is a list of extension layer names")
        policy = cls(str(raw.get("name", "unnamed")), sides["server"], sides["client"], frozenset(extensions))
        policy._check()
        return policy

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        import yaml
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise PolicyError(f"{path}: not a policy file")
        raw.setdefault("name", Path(path).stem)
        return cls.from_dict(raw)

    @classmethod
    def from_names(cls, server: str = "", client: str = "", args: dict | None = None, enforce_server: bool = False,
                   enforce_client: bool = False, fail: str = "open", extensions=(), name: str = "from-names") -> "Policy":
        """A policy from comma-separated control names, for command lines that predate policy files.
        args: constructor arguments per control name."""
        args = args or {}

        def side(names: str, enforce: bool) -> dict:
            return {"fail": fail, "controls": [{"use": n, "args": dict(args.get(n, {})), "enforce": enforce and bool(resolve(n).acts)}
                                               for n in names.split(",") if n]}
        return cls.from_dict({"policy": FORMAT, "name": name, "server": side(server, enforce_server), "client": side(client, enforce_client),
                              "extensions": sorted(extensions)})

    def _check(self) -> None:
        from fedguard.adapters import hosts
        known = {e for h in hosts.HOSTS.values() for e in h.extensions}
        if unknown := self.extensions - known:
            raise PolicyError(f"unknown extension layer(s) {sorted(unknown)}; known: {sorted(known)}")
        for side in SIDES:
            names = []
            for control in getattr(self, side).controls:
                plugin = control.build()
                wrong = [s.value for s in plugin.stages if side_of(s) != side]
                if wrong or not plugin.stages:
                    raise PolicyError(f"control {control.use!r} is listed under {side} but runs at {wrong or 'no stage'}")
                if control.enforce and not plugin.acts:
                    raise PolicyError(f"control {control.use!r} has nothing to enforce: it proposes no action")
                names.append(plugin.name)
            if len(names) != len(set(names)):
                raise PolicyError(f"{side}: a control is listed twice ({sorted(n for n in set(names) if names.count(n) > 1)})")

    # ----- what it mounts -----
    def plugins(self, side: str) -> list[GuardPlugin]:
        """Fresh plugin instances of one side, in mount order (every client needs its own)."""
        return [c.build() for c in getattr(self, side).controls]

    def enforced(self, side: str) -> set[str]:
        """Names of the controls of a side whose actions are applied."""
        return {c.build().name for c in getattr(self, side).controls if c.enforce}

    def resources(self, side: str) -> frozenset:
        """Names of the defender-supplied assets the controls of a side declare."""
        return frozenset(k for p in self.plugins(side) for k in p.resources)

    def needs(self, side: str) -> frozenset:
        """Data kinds the controls of a side read (e.g. to know whether a model handle has to be built)."""
        return frozenset(k for p in self.plugins(side) for k in p.needs)

    def runner(self, side: str, spec: RunSpec, recorder=None, resources: dict | None = None, **options) -> GuardRunner | None:
        """The GuardRunner of one side. `resources` may hold more than is needed: each control gets only what
        it declared. A client side without controls gets None (capture only), as ClientGuard expects.
        options: passed on to GuardRunner (strict_shapes, attachment_limit_bytes)."""
        plugins = self.plugins(side)
        if side == "client" and not plugins:
            return None
        wanted = {k for p in plugins for k in p.resources}
        enforced, acting = self.enforced(side), {p.name for p in plugins if p.acts}
        apply = False if not enforced else True if enforced == acting else enforced       # all, none, or the named ones
        runner = GuardRunner(plugins, spec, recorder, getattr(self, side).fail, side=side, apply_actions=apply,
                             resources={k: v for k, v in (resources or {}).items() if k in wanted}, **options)
        runner.policy = self.describe()
        if recorder is not None:
            recorder.write_run(runner.describe())
        return runner

    # ----- identity -----
    def to_dict(self) -> dict:
        side = lambda s: {"fail": s.fail, "controls": [{"use": c.use, "args": c.args, "enforce": c.enforce} for c in s.controls]}  # noqa: E731
        return {"policy": FORMAT, "name": self.name, "server": side(self.server), "client": side(self.client),
                "extensions": sorted(self.extensions)}

    @property
    def digest(self) -> str:
        """Hash of the policy's content (not of the file's formatting), without the name."""
        body = {k: v for k, v in self.to_dict().items() if k != "name"}
        return "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()

    def describe(self) -> dict:
        """What a run's record keeps about the policy it was mounted from."""
        return {"name": self.name, "digest": self.digest, "format": FORMAT}

    def report(self) -> str:
        """The controls this policy mounts and, per host, what mounting them takes."""
        from fedguard.adapters import hosts
        level = {"native": "native", "glue": "app glue", "extension": "extension layer", "patch": "script edit", None: "not reachable"}
        out = [f"policy {self.name}  {self.digest[:19]}", f"extensions listed: {', '.join(sorted(self.extensions)) or 'none'}"]
        for side in SIDES:
            block = getattr(self, side)
            out.append(f"{side} (fail {block.fail}): {len(block.controls)} control(s)" + (f", resources to supply: {', '.join(sorted(self.resources(side)))}"
                                                                                           if self.resources(side) else ""))
            for control, plugin in zip(block.controls, self.plugins(side)):
                where = "; ".join(f"{h.name}: {level[hosts.mount_level(plugin, h)]}"
                                  + "".join(f" + {e}" + ("" if e in self.extensions else " (NOT LISTED)") for e in hosts.needed_extensions(plugin, h))
                                  for h in hosts.HOSTS.values())
                out.append(f"  {'enforce' if control.enforce else 'alert  '}  {plugin.name:28s} at {','.join(s.value for s in plugin.stages)}  [{where}]")
        return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    try:
        print(Policy.load(argv[0]).report())
    except PolicyError as exc:
        print(f"policy error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
