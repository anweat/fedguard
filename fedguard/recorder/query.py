"""Read access to a recorded run: one place to ask "what did plugin X say about client Y in round Z"."""
from __future__ import annotations

from pathlib import Path

from fedguard.recorder.store import Recorder


class RunRecord:
    """Both sides of one recorded run.

        run = RunRecord(root, run_id)
        run.rounds()                         # server rounds
        run.client_ids()                     # clients that kept their own record
        run.findings(plugin="effect_stats")  # flat rows: one per (round, plugin, subject)
        run.series("effect_stats.inc_norm")  # {subject: [(round, value), ...]}
        run.server / run.client("c0")        # the underlying Recorder, for raw objects
    """

    def __init__(self, root: str | Path, run_id: str):
        self.root, self.run_id = Path(root), run_id
        self.server = Recorder(root, run_id)

    def client(self, client_id: str) -> Recorder:
        return Recorder(self.root, self.run_id, scope=client_id)

    def client_ids(self) -> list[str]:
        d = self.server.dir / "clients"
        return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.exists() else []

    def rounds(self, side: str = "server") -> list[int]:
        rec = self.server if side == "server" else self.client(side)
        return [t for t in rec.rounds() if (rec.dir / f"round_{t:04d}" / "round.json").exists()]

    def _sides(self, side: str | None) -> list[str]:
        return ["server", *self.client_ids()] if side is None else [side]

    def findings(self, plugin: str | None = None, stage: str | None = None, round: int | None = None,
                 subject: str | None = None, side: str | None = None) -> list[dict]:
        """One row per (side, round, plugin, subject): score, features, and the plugin's error if it failed.

        side: "server", a client id, or None for all. Rows of a plugin that produced no per-subject
        output have subject None.
        """
        rows = []
        for s in self._sides(side):
            rec = self.server if s == "server" else self.client(s)
            for t in self.rounds(s):
                if round is not None and t != round:
                    continue
                for f in rec.load_round(t).get("findings", []):
                    f_stage = f.get("stage", f.get("hook"))     # records written before stages were named
                    if (plugin is not None and f["module"] != plugin) or (stage is not None and f_stage != stage):
                        continue
                    subjects = sorted(set(f.get("scores", {})) | set(f.get("features", {}))) or [None]
                    for subj in subjects:
                        if subject is not None and subj != subject:
                            continue
                        rows.append({"side": s, "round": t, "plugin": f["module"], "stage": f_stage, "subject": subj,
                                     "score": f.get("scores", {}).get(subj), "features": f.get("features", {}).get(subj, {}),
                                     "error": f.get("error")})
        return rows

    def series(self, feature: str, side: str | None = "server") -> dict[str, list[tuple[int, float]]]:
        """'<plugin>.<feature>' (or '<plugin>.score') over rounds, per subject."""
        plugin, key = feature.split(".", 1)
        out: dict[str, list[tuple[int, float]]] = {}
        for r in self.findings(plugin=plugin, side=side):
            v = r["score"] if key == "score" else r["features"].get(key)
            if r["subject"] is not None and v is not None:
                out.setdefault(r["subject"], []).append((r["round"], v))
        return out

    def actions(self) -> list[dict]:
        """Per server round: what was excluded or reweighted, and why."""
        return [{"round": t, **self.server.load_round(t).get("decision", {}),
                 "rejected": self.server.load_round(t).get("rejected", {})} for t in self.rounds()]

    def verify(self) -> dict[str, list[str]]:
        """Integrity problems per side; empty lists mean intact."""
        return {s: (self.server if s == "server" else self.client(s)).verify() for s in self._sides(None)}
