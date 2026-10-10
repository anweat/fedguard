"""The knowledge base: what the library knows about threats and defenses, as data.

    vocabulary.yaml       artifacts, coordinates, capabilities, goals, tactics, evidence levels (the skeleton)
    threats.yaml          T-xxxx  threat techniques: goal x capabilities x artifacts modified
    defenses.yaml         D-xxxx  defense techniques: the technical problem solved
    implementations.yaml  I-xxxx  one way of doing a defense technique; names a plugin class
    scenarios.yaml        S-xxxx  minimal executable experiments, including the no-attack control
    relations.yaml        counters: implementation x threat, with an evidence level and its basis

Papers are sources of entries, never entries. `load()` reads and checks everything; an entry with an
unknown field, an unknown word or a dangling reference is an error. Implementations are checked against
the plugin classes they name, in both directions: what the entry says it reads and changes must be what
the class declares.

    python -m fedguard.kb check      validate
    python -m fedguard.kb tables     write generated/coverage.md (do not edit that file by hand)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent


class KBError(ValueError):
    """The knowledge base is inconsistent. The message lists every problem found."""


FIELDS = {
    "threat": ({"name", "zh", "goal", "capabilities", "modifies", "summary"},
               {"traces", "variants", "sources", "external", "stealth", "federated_sources", "notes"}),
    "defense": ({"name", "zh", "tactics", "problem", "reads", "acts", "trust", "resources"}, {"circumvention", "notes"}),
    "implementation": ({"technique", "status", "sources"},
                       {"class", "reads", "also_serves", "pairs_with", "known_failures", "blocked_by",
                        "title", "needs_runtime", "notes"}),
    "scenario": ({"zh", "threats", "capabilities", "description", "status"}, {"args", "runs", "results", "notes"}),
    "relation": ({"implementation", "threat", "level", "basis"}, {"scenario", "runs", "note", "broken_by"}),
}
SECTIONS = {"implemented": r"Implemented[^:\n]*", "deviations": r"Deviations?[^:\n]*", "open_choices": r"Open in the paper[^:\n]*",
            "not_implemented": r"Not implemented", "cost": r"Cost"}


def docstring_sections(doc: str) -> dict[str, str]:
    """Split a method class docstring at its section markers (Implemented, Deviations, Open in the paper
    and chosen here, Not implemented, Cost). The text before the first marker is the summary."""
    doc = re.sub(r"\n\s+", "\n", (doc or "").strip())
    marks = sorted((m.start(), m.end(), k) for k, pat in SECTIONS.items() for m in re.finditer(rf"(?:^|(?<=\n)|(?<=\. )){pat}:", doc))
    out = {"summary": " ".join(doc[:marks[0][0] if marks else len(doc)].split())}
    for i, (_, end, k) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(doc)
        out[k] = (out.get(k, "") + " " + " ".join(doc[end:stop].split())).strip()
    return out


@dataclass
class KB:
    """The loaded knowledge base: the vocabulary and the five kinds of entries, with the queries that connect
    them (which implementations meet a threat through the artifacts, with what evidence).
    """
    vocabulary: dict
    threats: dict = field(default_factory=dict)
    defenses: dict = field(default_factory=dict)
    implementations: dict = field(default_factory=dict)
    scenarios: dict = field(default_factory=dict)
    relations: list = field(default_factory=list)

    @property
    def content_version(self) -> str:
        """A hash of the entries: recorded with a run, it says which knowledge base the run was planned against."""
        import hashlib
        h = hashlib.sha256()
        for name in ("vocabulary", "threats", "defenses", "implementations", "scenarios", "relations"):
            p = HERE / f"{name}.yaml"
            h.update(p.read_bytes() if p.exists() else b"")
        return h.hexdigest()[:12]

    def plugin(self, impl_id: str):
        name = self.implementations[impl_id].get("class")
        return plugin_classes().get(name) if name else None

    def describe(self, impl_id: str) -> dict:
        """The implementation entry plus what its class says about itself."""
        entry, cls = dict(self.implementations[impl_id]), self.plugin(impl_id)
        if cls is not None:
            import inspect
            entry["doc"] = docstring_sections(cls.__doc__)
            entry["params"] = {n: p.default for n, p in inspect.signature(cls.__init__).parameters.items()
                               if n != "self" and p.default is not inspect.Parameter.empty}
            entry["stages"] = [s.value for s in cls().stages] if not _required_args(cls) else []
        return entry

    def completeness(self, impl_id: str) -> str:
        """full, or partial when the class docstring has a 'Not implemented' section: evidence that the
        source paper evaluated its whole method (level 1) then covers more than this implementation does."""
        cls = self.plugin(impl_id)
        return "partial" if cls is not None and "not_implemented" in docstring_sections(cls.__doc__) else "full"

    def acts_without_attack(self, impl_id: str) -> bool | None:
        """Measured in the no-attack control scenarios: did the implementation exclude, reweight, mask,
        rewrite, add or transform anything there? None if it has not been run in one."""
        keys = ("client_rounds_excluded", "weight_shift", "samples_masked", "samples_rewritten", "samples_added",
                "updates_transformed", "global_replaced")
        seen = [s["results"][impl_id] for s in self.scenarios.values() if not s["threats"] and impl_id in (s.get("results") or {})]
        if not seen:
            return None
        return any(r.get(k) for r in seen for k in keys) or any(r.get(k) not in (None, 1.0) for r in seen for k in ("gradient_norm_ratio", "loss_ratio"))

    def lands(self, impl_id: str) -> set[str]:
        """The artifacts an implementation's actions change: those on its own side that its actions can modify."""
        cls = self.plugin(impl_id)
        if cls is None:
            return set()
        from fedguard.core.types import Stage, side_of
        at = cls.at
        sides = {side_of(s) for s in ((at,) if isinstance(at, Stage) else at)} | {"both"}
        return {a for a, v in self.vocabulary["artifacts"].items() if set(v["modified_by"]) & set(cls.acts) and v["side"] in sides}

    def link(self, impl_id: str, threat_id: str) -> str | None:
        """How an implementation meets a threat through the artifacts, before any evidence:
          direct    it acts on, or reads, an artifact the threat modifies
          reported  it reads a coordinate where a source paper reports a trace of the threat
          inferred  it reads a coordinate where a trace was only inferred from the mechanism
        None if they do not meet. A link says the pair is worth trying, not that the defense works."""
        e, t = self.implementations[impl_id], self.threats[threat_id]
        if "class" not in e:
            return None
        lands = self.lands(impl_id)
        reads = set(e.get("reads", []))
        if (lands | {c.split("/")[0] for c in reads}) & set(t["modifies"]):
            return "direct"
        bases = {x["basis"] for x in t.get("traces", []) if x["coordinate"] in reads}
        return "reported" if "reported" in bases else "inferred" if bases else None

    def candidates(self, threat_id: str) -> dict[str, str]:
        """Implementations that meet the threat through the artifacts, with the kind of link."""
        return {i: k for i in self.implementations if (k := self.link(i, threat_id))}

    def evidence(self, impl_id: str, threat_id: str) -> int:
        return max((r["level"] for r in self.relations if r["implementation"] == impl_id and r["threat"] == threat_id), default=0)


def _required_args(cls) -> bool:
    import inspect
    return any(p.default is inspect.Parameter.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
               for n, p in inspect.signature(cls.__init__).parameters.items() if n != "self")


def plugin_classes() -> dict:
    from fedguard.methods import METHODS
    from fedguard.plugins import BUILTIN
    return {**BUILTIN, **METHODS}


def _read(name: str):
    import yaml
    p = HERE / f"{name}.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else None


def load(check: bool = True) -> KB:
    kb = KB(vocabulary=_read("vocabulary"), threats=_read("threats") or {}, defenses=_read("defenses") or {},
            implementations=_read("implementations") or {}, scenarios=_read("scenarios") or {}, relations=_read("relations") or [])
    if check:
        problems = validate(kb)
        if problems:
            raise KBError(f"{len(problems)} problem(s) in the knowledge base:\n  " + "\n  ".join(problems))
    return kb


def validate(kb: KB) -> list[str]:
    v, bad = kb.vocabulary, []

    def fields(kind: str, key: str, entry: dict) -> None:
        required, optional = FIELDS[kind]
        if missing := required - set(entry):
            bad.append(f"{key}: missing {sorted(missing)}")
        if extra := set(entry) - required - optional:
            bad.append(f"{key}: unknown fields {sorted(extra)}")

    def words(key: str, what: str, values, vocab: str) -> None:
        if unknown := [x for x in values or [] if x not in v[vocab]]:
            bad.append(f"{key}: {what} uses {unknown}, not in vocabulary.{vocab}")

    for c in v["coordinates"]:
        art = c.split("/")[0]
        if len(c.split("/")) != 3 or art not in v["artifacts"]:
            bad.append(f"coordinate {c!r}: must be <artifact>/<access>/<granularity> with a known artifact")
    for kind, table, prefix in (("threat", kb.threats, "T-"), ("defense", kb.defenses, "D-"),
                                ("implementation", kb.implementations, "I-"), ("scenario", kb.scenarios, "S-")):
        for key, e in table.items():
            if not re.fullmatch(rf"{prefix}\d{{4}}(\.\d{{2}})?", key):
                bad.append(f"{key}: id must look like {prefix}0001")
            fields(kind, key, e)
        names = [e.get("name") or e.get("class") for e in table.values() if e.get("name") or e.get("class")]
        for n in {n for n in names if names.count(n) > 1}:
            bad.append(f"{kind}: {n!r} is registered more than once")
    for key, t in kb.threats.items():
        words(key, "goal", t.get("goal"), "goals")
        words(key, "capabilities", t.get("capabilities"), "capabilities")
        words(key, "modifies", t.get("modifies"), "artifacts")
        words(key, "traces", [x.get("coordinate") for x in t.get("traces", [])], "coordinates")
        for x in t.get("traces", []):
            if x.get("basis") not in ("reported", "inferred"):
                bad.append(f"{key}: trace {x.get('coordinate')} needs basis reported|inferred")
        reach = {a for c in t.get("capabilities", []) for a in v["capabilities"].get(c, {}).get("modifies", [])}
        if out := set(t.get("modifies", [])) - reach:
            bad.append(f"{key}: modifies {sorted(out)} but none of its capabilities reaches them")
    actions = {a for art in v["artifacts"].values() for a in art["modified_by"]}
    for key, d in kb.defenses.items():
        words(key, "tactics", d.get("tactics"), "tactics")
        words(key, "reads", d.get("reads"), "artifacts")
        words(key, "trust", d.get("trust"), "trust")
        if unknown := set(d.get("acts", [])) - actions:
            bad.append(f"{key}: unknown actions {sorted(unknown)}")
    classes = plugin_classes()
    for key, e in kb.implementations.items():
        d = kb.defenses.get(e.get("technique"))
        if d is None:
            bad.append(f"{key}: technique {e.get('technique')!r} does not exist")
            continue
        words(key, "status", [e.get("status")], "status")
        words(key, "reads", e.get("reads"), "coordinates")
        for ref in e.get("also_serves", []):
            if ref not in kb.defenses:
                bad.append(f"{key}: also_serves {ref!r} does not exist")
        for ref in e.get("pairs_with", []):
            if ref not in kb.implementations:
                bad.append(f"{key}: pairs_with {ref!r} does not exist")
        if e.get("status") == "unsupported":
            if "class" in e or not e.get("needs_runtime") or not e.get("title"):
                bad.append(f"{key}: an unsupported entry has a title and needs_runtime, and no class")
            continue
        cls = classes.get(e.get("class"))
        if cls is None:
            bad.append(f"{key}: class {e.get('class')!r} is not a registered plugin")
            continue
        allowed = set(d["reads"]) | {a for s in e.get("also_serves", []) for a in kb.defenses.get(s, {}).get("reads", [])}
        arts = {c.split("/")[0] for c in e.get("reads", [])}
        if arts - allowed:
            bad.append(f"{key}: reads {sorted(arts - allowed)} outside its technique's artifacts")
        kinds = {v["artifacts"][a]["kind"] for a in arts if a in v["artifacts"]}
        if any(v["coordinates"].get(c, {}).get("via") == "model_handle" for c in e.get("reads", [])):
            kinds.add("model_handle")
        if kinds != set(cls.needs):
            bad.append(f"{key}: entry reads imply {sorted(kinds)} but class {cls.name} declares needs {sorted(cls.needs)}")
        acts = set(d["acts"]) | {a for s in e.get("also_serves", []) for a in kb.defenses.get(s, {}).get("acts", [])}
        if not set(cls.acts) <= acts:
            bad.append(f"{key}: class {cls.name} acts {sorted(set(cls.acts) - acts)} beyond its technique")
        if not set(cls.resources) <= set(d["resources"]):
            bad.append(f"{key}: class {cls.name} needs resources {sorted(set(cls.resources) - set(d['resources']))} its technique does not list")
        if cls.__module__.startswith("fedguard.methods") and len(docstring_sections(cls.__doc__)) < 2:
            bad.append(f"{key}: the docstring of {cls.name} has none of the sections Implemented / Deviations / "
                       "Open in the paper and chosen here / Not implemented / Cost")
    registered = {e.get("class") for e in kb.implementations.values()}
    from fedguard.methods import METHODS
    for name in sorted(set(METHODS) - registered):
        bad.append(f"method {name!r} has no implementation entry")
    for key, s in kb.scenarios.items():
        words(key, "capabilities", s.get("capabilities"), "capabilities")
        for t in s.get("threats", []):
            if t not in kb.threats:
                bad.append(f"{key}: threat {t!r} does not exist")
    for n, r in enumerate(kb.relations):
        key = f"relation {n} ({r.get('implementation')} -> {r.get('threat')})"
        fields("relation", key, r)
        if r.get("implementation") not in kb.implementations:
            bad.append(f"{key}: implementation does not exist")
        if r.get("threat") not in kb.threats:
            bad.append(f"{key}: threat does not exist")
        if r.get("level") not in v["evidence_levels"] or r.get("level") == 0:
            bad.append(f"{key}: level must be 1..4 (0 is derived, never written)")
        if r.get("level", 0) >= 2 and not (r.get("scenario") in kb.scenarios and r.get("runs")):
            bad.append(f"{key}: level 2 and above need a scenario and the runs that support it")
        if r.get("level") == 1 and not r.get("basis"):
            bad.append(f"{key}: level 1 needs the paper it comes from as basis")
    return bad
