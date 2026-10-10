"""Re-run plugins over a recorded run, without retraining.

    replay(root, run_id, [EffectStats(), MyPlugin()], out_root)                 # server side
    replay(root, run_id, [LocalCentroid()], out_root, client="client3")         # one client's side

Rounds are replayed in order, so plugins that keep state or read history see what they would have
seen live. New findings go to <out_root>/<run_id>/ (same layout, no tensors); the source is not touched.

What a replay can and cannot reproduce:
  - Objects that were recorded (uploads, bases, aggregation results, received and local models, the
    data manifest, the step trace, channel messages) are replayed exactly.
  - Sample text was never recorded, so client plugins that read it need `samples`: a function
    (round, manifest) -> sequence of samples, supplied by whoever still holds the data.
  - Channel messages are the recorded ones. A plugin on the other side that would now answer
    differently is not re-run; replay each side separately when both changed.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fedguard.client import ClientGuard
from fedguard.core.plugin import GuardPlugin
from fedguard.core.runner import GuardRunner
from fedguard.core.types import ClientUpdate, RunSpec, Stage
from fedguard.recorder.store import Recorder
from fedguard.views.aggregate import AggregateView
from fedguard.views.client import DataView, SampleRecord


class ManifestData(DataView):
    """`data` rebuilt from a recorded manifest: hashes, sources and lengths, but no text."""

    def __init__(self, rows: list[dict]):
        super().__init__([None] * len(rows))
        self._manifest = [SampleRecord(r["i"], r["hash"], r["source"], r["length"]) for r in rows]

    def samples(self):
        raise LookupError("sample text is not part of the record; pass `samples` to replay()")

    def text(self, index: int) -> str:
        raise LookupError("sample text is not part of the record; pass `samples` to replay()")


def _recorded_rounds(rec: Recorder) -> list[int]:
    return [t for t in rec.rounds() if (rec.dir / f"round_{t:04d}" / "round.json").exists()]


def _spec(src: Recorder, run_id: str, spec: RunSpec | None) -> RunSpec:
    if spec is not None:
        return spec
    old = src.load_run().get("spec", {})
    return RunSpec(run_id, seed=old.get("seed", 0), lora_scale=old.get("lora_scale", 1.0),
                   num_clients=old.get("num_clients"), extra=old.get("extra", {}))


def replay(root: str | Path, run_id: str, plugins: list[GuardPlugin], out_root: str | Path, *,
           client: str | None = None, spec: RunSpec | None = None, model_handle=None, resources: dict | None = None,
           samples: Callable | None = None) -> int:
    """Returns the number of rounds replayed. `spec` defaults to the recorded one (run.json)."""
    src = Recorder(root, run_id, scope=client)
    dst = Recorder(out_root, run_id, save_factors=False, scope=client)
    spec = _spec(src, run_id, spec)
    if client is not None:
        return _replay_client(src, dst, client, plugins, spec, model_handle, resources, samples)
    runner = GuardRunner(plugins, spec, dst, resources=resources)
    done = 0
    for t in _recorded_rounds(src):
        recorded = src.load_round(t)
        if not src.has_object(t, "base"):
            continue
        base, reports = src.load_base(t), src.load_reports(t)
        ups = [ClientUpdate(cid, t, src.load_update(t, cid), base, reports.get(cid, {}).get("reported", {}),
                            reports.get(cid, {}).get("messages", {})) for cid in src.clients(t)]
        runner.begin_round(t)
        valid = runner.screen(ups)
        participants = [u.client_id for u in ups]
        views = {"uploads": valid} if model_handle is None else {"uploads": valid, "model_handle": model_handle}
        meta = recorded.get("meta", {})
        sampled = tuple(str(c) for c in meta.get("sampled", participants))
        weights = {str(c): w for c, w in (meta.get("weights") or {}).items()}
        rule = meta.get("rule", "")
        runner.run(Stage.SERVER_RECEIVE, participants, **views)
        runner.run(Stage.SERVER_AGGREGATE, participants, **views, aggregate=AggregateView(sampled, weights, base, rule=rule))
        if src.has_object(t, "aggregate"):
            runner.run(Stage.SERVER_POST_AGGREGATE, list(weights), **views,
                       aggregate=AggregateView(sampled, weights, base, src.load_aggregate(t), rule))
        runner.end_round(meta)
        done += 1
    return done


def _replay_client(src, dst, client, plugins, spec, model_handle, resources, samples) -> int:
    guard = ClientGuard(client, GuardRunner(plugins, spec, side="client", resources=resources), dst)
    done = 0
    for t in _recorded_rounds(src):
        if not src.has_object(t, "received"):
            continue
        meta = src.load_round(t).get("meta", {})
        rows = src.load_lines(t, "manifest")
        data = None
        if rows:
            data = ManifestData(rows) if samples is None else DataView(samples(t, rows))
        guard.begin_round(t, src.load_object(t, "received"), data=data, model_handle=model_handle,
                          messages=meta.get("messages", {}))
        for step in src.load_lines(t, "trace"):
            guard.on_step(step["step"], {k: v for k, v in step.items() if k != "step"})
        if src.has_object(t, "local"):
            guard.before_upload(src.load_object(t, "local"), meta.get("reported", {}))
        guard.end_round({"replayed_from": str(src.dir)})
        done += 1
    return done
