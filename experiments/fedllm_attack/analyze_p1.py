"""P1 analysis: feature trajectories over rounds, Q1 preview (effect vs factor features), overhead.

Usage: analyze_p1.py <runs/p1 dir> <figure dir> [records root, default <runs/p1 dir>/records]
Reads each run's exp_args.json and the record layer; writes PNG figures and prints a Markdown summary.
"""
import json
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fedguard.ops.robust import robust_z  # noqa: E402

# Reference palette (dataviz skill): slot 1 blue for the benign median, slot 2 orange for the malicious client.
BLUE, ORANGE = "#2a78d6", "#eb6834"
GRAY, INK, INK2, GRID = "#b9b8b3", "#0b0b0b", "#52514e", "#e6e5e1"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

FEATURES = [  # (module, key, label)
    ("effect_stats", "inc_norm", "effect ‖ΔW‖"),
    ("effect_stats", "cos_rest", "effect cos to others"),
    ("effect_stats", "mod_cos_rest", "effect per-module cos"),
    ("effect_stats", "top_sv_share", "effect σ₁² share"),
    ("factor_stats", "delta_norm", "factor ‖Δ(A,B)‖"),
    ("factor_stats", "cos_rest", "factor cos to others"),
    ("factor_stats", "mod_cos_rest", "factor per-module cos"),
]


def load_run(run_dir: Path, record_root: Path) -> dict:
    out_dir = next(p for p in run_dir.iterdir() if p.is_dir())
    exp = json.loads((out_dir / "exp_args.json").read_text())
    rec = record_root / out_dir.name
    rounds = []
    for rj in sorted(rec.glob("round_*/round.json")):
        r = json.loads(rj.read_text())
        feats, elapsed = {}, {}
        for f in r["findings"]:
            elapsed[f["module"]] = f["elapsed_s"]
            for cid, v in f["features"].items():
                feats.setdefault(cid, {}).update({f"{f['module']}.{k}": x for k, x in v.items()})
        rounds.append({"round": r["round"], "features": feats, "elapsed": elapsed,
                       "train_s": r["meta"].get("train_s", {})})
    kinds = {f"client{i}": k for i, k in enumerate(exp["client_kind"])}
    return {"name": run_dir.name, "exp": exp, "rounds": rounds, "kinds": kinds}


def series(run: dict, feat: str) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for r in run["rounds"]:
        for cid, v in r["features"].items():
            x = v.get(feat, float("nan"))
            out.setdefault(cid, []).append(float(x) if not isinstance(x, str) else float(x))
    return out


def style(ax, title):
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)


def plot_trajectories(runs: list[dict], path: Path) -> None:
    fig, axes = plt.subplots(len(runs), len(FEATURES), figsize=(3.1 * len(FEATURES), 2.6 * len(runs)),
                             squeeze=False, constrained_layout=True)
    for row, run in enumerate(runs):
        for col, (mod, key, label) in enumerate(FEATURES):
            ax = axes[row][col]
            s = series(run, f"{mod}.{key}")
            benign = [v for c, v in s.items() if run["kinds"].get(c) == "benign"]
            x = np.arange(1, len(next(iter(s.values()))) + 1)
            for v in benign:
                ax.plot(x, v, color=GRAY, linewidth=1)
            med = np.nanmedian(np.array(benign), axis=0)
            ax.plot(x, med, color=BLUE, linewidth=2, label="benign median")
            for c, v in s.items():
                if run["kinds"].get(c) == "malicious":
                    ax.plot(x, v, color=ORANGE, linewidth=2, label="malicious")
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            style(ax, f"{run['name'].upper()} · {label}")
            if row == len(runs) - 1:
                ax.set_xlabel("round", fontsize=8, color=INK2)
    handles = [plt.Line2D([], [], color=GRAY, lw=1), plt.Line2D([], [], color=BLUE, lw=2),
               plt.Line2D([], [], color=ORANGE, lw=2)]
    fig.legend(handles, ["benign client", "benign median", "malicious client"], loc="outside upper right",
               ncols=3, frameon=False, fontsize=9, labelcolor=INK)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def zscores(run: dict, feat: str) -> tuple[list[float], list[float]]:
    """Per round: |robust z| of the malicious client, and max |z| over benign clients."""
    mal, ben = [], []
    for r in run["rounds"]:
        vals = {c: v.get(feat) for c, v in r["features"].items()}
        vals = {c: float(x) for c, x in vals.items() if x is not None and np.isfinite(float(x))}
        z = robust_z(vals, min_n=5) or {}
        m = [abs(z[c]) for c in z if run["kinds"].get(c) == "malicious"]
        b = [abs(z[c]) for c in z if run["kinds"].get(c) == "benign"]
        mal.append(max(m) if m else float("nan"))
        ben.append(max(b) if b else float("nan"))
    return mal, ben


def plot_separation(c1: dict, path: Path) -> None:
    pairs = [("inc_norm", "delta_norm", "update size"), ("cos_rest", "cos_rest", "direction vs others")]
    fig, axes = plt.subplots(1, len(pairs), figsize=(4.6 * len(pairs), 3.0), constrained_layout=True)
    for ax, (ek, fk, label) in zip(axes, pairs):
        me, _ = zscores(c1, f"effect_stats.{ek}")
        mf, _ = zscores(c1, f"factor_stats.{fk}")
        x = np.arange(1, len(me) + 1)
        ax.plot(x, me, color=BLUE, linewidth=2, marker="o", markersize=4, label="effect space")
        ax.plot(x, mf, color=ORANGE, linewidth=2, marker="o", markersize=4, label="factor space")
        style(ax, f"C1 · malicious |robust z| · {label}")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_xlabel("round", fontsize=8, color=INK2)
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def plot_partition(run: dict, path: Path) -> None:
    part = run["exp"]["partition"]
    counts = np.array(part["counts"])
    cats = part["categories"]
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", SEQ)
    fig, ax = plt.subplots(figsize=(7.5, 0.35 * len(counts) + 1.4), constrained_layout=True)
    im = ax.imshow(counts, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(cats)), cats, rotation=30, ha="right", fontsize=8, color=INK2)
    ax.set_yticks(range(len(counts)), [f"client{i}" for i in range(len(counts))], fontsize=8, color=INK2)
    for i in range(counts.shape[0]):
        for j in range(counts.shape[1]):
            v = counts[i, j]
            ax.text(j, i, str(v), ha="center", va="center", fontsize=7,
                    color="white" if v > counts.max() * 0.55 else INK)
    ax.set_title(f"{run['name'].upper()} · Dolly Dirichlet(α={run['exp']['guard']['exp_alpha']}) samples per client",
                 loc="left", fontsize=10, color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.colorbar(im, ax=ax, shrink=0.8).outline.set_visible(False)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def summary(runs: dict[str, dict]) -> str:
    lines = ["| 特征 | C0 良性最大 \\|z\\|（中位数 / 最大） | C1 恶意 \\|z\\|（中位数 / 最小） | C1 恶意 \\|z\\| > C0 良性 99% 分位的轮次 |",
             "|---|---|---|---|"]
    for mod, key, label in FEATURES:
        feat = f"{mod}.{key}"
        _, b0 = zscores(runs["c0"], feat)
        m1, _ = zscores(runs["c1"], feat)
        b0f = [x for x in b0 if np.isfinite(x)]
        m1f = [x for x in m1 if np.isfinite(x)]
        if not b0f or not m1f:
            lines.append(f"| {label} | — | — | — |")
            continue
        thr = float(np.quantile(b0f, 0.99))
        hit = sum(x > thr for x in m1f)
        lines.append(f"| {label} | {statistics.median(b0f):.2f} / {max(b0f):.2f} | "
                     f"{statistics.median(m1f):.2f} / {min(m1f):.2f} | {hit}/{len(m1f)} |")
    lines += ["", "| 运行 | 每轮本地训练（10 客户端合计，秒） | effect_stats（秒/轮） | factor_stats（秒/轮） | 检测占比 |",
              "|---|---|---|---|---|"]
    for name, run in runs.items():
        tr = [sum(r["train_s"].values()) for r in run["rounds"] if r["train_s"]]
        es = [r["elapsed"].get("effect_stats", 0) for r in run["rounds"]]
        fs = [r["elapsed"].get("factor_stats", 0) for r in run["rounds"]]
        t, e, f = statistics.median(tr), statistics.median(es), statistics.median(fs)
        lines.append(f"| {name.upper()} | {t:.1f} | {e:.3f} | {f:.3f} | {(e + f) / t:.2%} |")
    return "\n".join(lines)


def main(root: Path, fig_dir: Path, records: Path | None = None) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    records = records or root / "records"
    runs = {name: load_run(root / name, records) for name in ("c0", "c1") if (root / name).exists()}
    plot_trajectories(list(runs.values()), fig_dir / "p1_feature_trajectories.png")
    plot_partition(runs["c0"], fig_dir / "p1_partition_c0.png")
    if "c1" in runs:
        plot_separation(runs["c1"], fig_dir / "p1_c1_separation.png")
        print(summary(runs))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) > 3 else None)
