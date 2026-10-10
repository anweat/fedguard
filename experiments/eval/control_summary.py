"""What a defense changed in a run without any attack: everything it excluded, masked or rewrote there
is collateral. Reads the JSON records of a method sweep run with SCENARIO=control.

Per run:
  client_rounds_excluded   share of (client, round) uploads left out of aggregation
  weight_shift             mean total-variation distance between the aggregation weights used and the
                           weights the clients' reported sample counts would give (0 = untouched)
  samples_masked, samples_rewritten, samples_added   shares of the announced samples (added: relative to them)
  gradient_norm_ratio      mean norm after / before for changed gradients
  updates_transformed, global_replaced               counts of applied actions
  last_round_loss          mean training loss the clients reported in the last round; `loss_vs_baseline`
                           is its ratio to the run named `stats`, which mounts no intervening plugin

Usage: control_summary.py <sweep result dir> [--json out.json]
"""
import json
import sys
from pathlib import Path


def rounds(d: Path):
    return sorted(p for p in d.glob("round_*") if (p / "round.json").exists())


def measure(run: Path) -> dict:
    m = dict.fromkeys(("uploads", "excluded", "samples", "masked", "rewritten", "added", "updates_transformed", "global_replaced"), 0)
    shift, ratios, loss_ratios, last_loss, errors = [], [], [], [], 0
    server = [json.loads((r / "round.json").read_text()) for r in rounds(run)]
    clients = {c.name: [json.loads((r / "round.json").read_text()) for r in rounds(c)] for c in sorted((run / "clients").glob("*")) if c.is_dir()}
    for t, rec in enumerate(server):
        meta = rec.get("meta") or {}
        sampled, used = [str(c) for c in meta.get("sampled", [])], {str(k): float(v) for k, v in (meta.get("weights") or {}).items()}
        m["uploads"] += len(sampled)
        m["excluded"] += len([c for c in sampled if used.get(c, 0.0) == 0.0])
        counts = {}
        for c in sampled:
            rows = clients.get(f"client{c}", [])
            row = next((x for x in rows if x.get("round") == rec.get("round")), None)
            counts[c] = float(((row or {}).get("meta") or {}).get("reported", {}).get("num_examples", 0.0))
        if sum(counts.values()) > 0 and sum(used.values()) > 0:
            shift.append(0.5 * sum(abs(used.get(c, 0.0) / sum(used.values()) - counts[c] / sum(counts.values())) for c in sampled))
        for f in rec.get("findings", []):
            errors += bool(f.get("error"))
            for a in f.get("actions") or []:
                if a.get("applied"):
                    m["updates_transformed"] += a["action"] == "transform_update"
                    m["global_replaced"] += a["action"] == "replace_global"
    final = max((r.get("round", -1) for r in server), default=-1)
    for rows in clients.values():
        for rec in rows:
            meta = rec.get("meta") or {}
            m["samples"] += int(meta.get("samples", 0))
            m["masked"] += int(meta.get("masked", 0))
            m["rewritten"] += int(meta.get("rewritten", 0))
            m["added"] += int(meta.get("added", 0))
            if rec.get("round") == final and "train_loss" in (meta.get("reported") or {}):
                last_loss.append(float(meta["reported"]["train_loss"]))
            for f in rec.get("findings", []):
                errors += bool(f.get("error"))
                for a in f.get("actions") or []:
                    if a.get("applied") and a["action"] == "transform_gradients" and a.get("norm_before"):
                        ratios.append(a["norm_after"] / a["norm_before"])
                    if a.get("applied") and a["action"] == "transform_loss" and a.get("before"):
                        loss_ratios.append(a["after"] / a["before"])
                    if a.get("applied") and a["action"] == "transform_update":
                        m["updates_transformed"] += 1
    share = lambda a, b: round(a / b, 4) if b else None  # noqa: E731
    return {"rounds": len(server), "client_rounds": m["uploads"], "client_rounds_excluded": share(m["excluded"], m["uploads"]),
            "weight_shift": round(sum(shift) / len(shift), 4) if shift else None,
            "samples": m["samples"], "samples_masked": share(m["masked"], m["samples"]), "samples_rewritten": share(m["rewritten"], m["samples"]),
            "samples_added": share(m["added"], m["samples"]),
            "gradient_norm_ratio": round(sum(ratios) / len(ratios), 4) if ratios else None,
            "loss_ratio": round(sum(loss_ratios) / len(loss_ratios), 4) if loss_ratios else None,
            "updates_transformed": m["updates_transformed"], "global_replaced": m["global_replaced"],
            "last_round_loss": round(sum(last_loss) / len(last_loss), 4) if last_loss else None, "plugin_errors": errors}


def main() -> None:
    args = sys.argv[1:]
    out_json = args[args.index("--json") + 1] if "--json" in args else None
    sweep = Path(args[0])
    results = {}
    for line in (sweep / "status.tsv").read_text().splitlines():
        name, status, _ = line.split("\t")
        recs = [d for d in sorted((sweep / f"rec_{name}").glob("*")) if d.is_dir() and rounds(d)] if status == "ok" else []
        results[name] = {"status": status, **(measure(recs[0]) if recs else {})}
    base = (results.get("stats") or {}).get("last_round_loss")
    for r in results.values():
        r["loss_vs_baseline"] = round(r["last_round_loss"] / base, 4) if base and r.get("last_round_loss") else None
    cols = ["client_rounds_excluded", "weight_shift", "samples_masked", "samples_rewritten", "samples_added", "gradient_norm_ratio",
            "updates_transformed", "global_replaced", "loss_vs_baseline"]
    print(f"{'run':28s}" + "".join(f"{c[:15]:>16s}" for c in cols))
    for name, r in results.items():
        print(f"{name:28s}" + "".join(f"{('-' if r.get(c) is None else r[c]):>16}" for c in cols) + ("" if r["status"] == "ok" else f"  {r['status']}"))
    if out_json:
        Path(out_json).write_text(json.dumps(results, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
