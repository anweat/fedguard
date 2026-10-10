"""P2 analysis: benign baseline across non-IID levels and seeds; one-sided thresholds; check on C1.

Usage: analyze_p2.py <p2 dir> <figure dir> [<c1 run dir>[,<c1 run dir>...] <c1 records root>]

For each feature, per round, clients are standardized with robust z (median/MAD over that round's clients),
so the cosine learning-rate decay does not shift thresholds. Tests are one-sided: size-like features flag
large values, direction-like features flag small values. The first WARMUP rounds are excluded.
Thresholds are the (1 - FPR) quantile of the benign signed z pooled over seeds and rounds, per split.
"""
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analyze_p1 import BLUE, GRAY, INK, INK2, ORANGE, load_run, style  # noqa: E402
from fedguard.ops.robust import robust_z  # noqa: E402

WARMUP = 2
FPRS = (0.05, 0.01)
# (feature key, label, direction): +1 flags large values, -1 flags small values
FEATURES = [
    ("effect_stats.inc_norm", "effect ‖ΔW‖", +1),
    ("factor_stats.delta_norm", "factor ‖Δ(A,B)‖", +1),
    ("effect_stats.cos_rest", "effect cos to others", -1),
    ("factor_stats.cos_rest", "factor cos to others", -1),
    ("effect_stats.mod_cos_rest", "effect per-module cos", -1),
    ("factor_stats.mod_cos_rest", "factor per-module cos", -1),
    ("effect_stats.top_sv_share", "effect σ₁² share", +1),
    ("compliance_probe.compliance_gain", "probe compliance gain", +1),
]
SPLIT_ORDER = ["iid", "d1.0", "d0.5", "d0.1"]
SPLIT_LABEL = {"iid": "IID", "d1.0": "Dir α=1.0", "d0.5": "Dir α=0.5", "d0.1": "Dir α=0.1"}


def signed_z(run: dict, feat: str, sign: int) -> list[tuple[int, str, float]]:
    """(round, client, sign * robust z) for every client-round after warm-up."""
    out = []
    for r in run["rounds"]:
        if r["round"] < WARMUP:
            continue
        vals = {c: float(v[feat]) for c, v in r["features"].items()
                if feat in v and not isinstance(v[feat], str) and np.isfinite(float(v[feat]))}
        z = robust_z(vals, min_n=5) or {}
        out += [(r["round"], c, sign * x) for c, x in z.items()]
    return out


def raw_values(run: dict, feat: str) -> list[float]:
    return [float(v[feat]) for r in run["rounds"] if r["round"] >= WARMUP
            for v in r["features"].values() if feat in v and not isinstance(v[feat], str)]


def load_p2(root: Path) -> dict[str, list[dict]]:
    runs: dict[str, list[dict]] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir() and "_s" in p.name and (root / f"{p.name}.done").exists()):
        split = d.name.rsplit("_s", 1)[0]
        runs.setdefault(split, []).append(load_run(d, root / "records"))
    return {s: runs[s] for s in SPLIT_ORDER if s in runs}


def thresholds(runs: dict[str, list[dict]]) -> dict:
    th = {}
    for split, rs in runs.items():
        for feat, _, sign in FEATURES:
            z = [x for run in rs for _, _, x in signed_z(run, feat, sign)]
            if not z:                       # feature absent from these records (e.g. no probe plugin ran)
                th[(split, feat)] = {f: float("inf") for f in FPRS} | {"n": 0}
                continue
            th[(split, feat)] = {f: float(np.quantile(z, 1 - f)) for f in FPRS} | {"n": len(z)}
    return th


def table_thresholds(runs, th) -> str:
    head = "| 特征 | " + " | ".join(f"{SPLIT_LABEL[s]}" for s in runs) + " |"
    lines = ["单侧 z 阈值（良性客户端-轮次的 99% 分位；括号内为 95% 分位）", "", head,
             "|---|" + "---|" * len(runs)]
    for feat, label, _ in FEATURES:
        cells = [f"{th[(s, feat)][0.01]:.2f} ({th[(s, feat)][0.05]:.2f})" for s in runs]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    counts = ", ".join(f"{SPLIT_LABEL[s]} {th[(s, FEATURES[0][0])]['n']}（{len(runs[s])} 个种子）" for s in runs)
    lines.append(f"\n样本量（排除前 {WARMUP} 轮的客户端-轮次数）：{counts}。")
    return "\n".join(lines)


def table_dispersion(runs) -> str:
    lines = ["良性客户端的原始特征（跨种子和轮次的中位数；括号内为 10%–90% 分位）", "",
             "| 特征 | " + " | ".join(SPLIT_LABEL[s] for s in runs) + " |", "|---|" + "---|" * len(runs)]
    for feat, label, _ in FEATURES:
        if "cos" not in feat:
            continue
        cells = []
        for s in runs:
            v = [x for run in runs[s] for x in raw_values(run, feat)]
            cells.append(f"{np.median(v):.3f} ({np.quantile(v, 0.1):.2f}–{np.quantile(v, 0.9):.2f})")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


COMBO = [("effect_stats.inc_norm", +1), ("factor_stats.cos_rest", -1)]   # effect size OR factor direction


def combo_flags(run: dict, th: dict, split: str, fpr: float) -> dict[tuple[int, str], bool]:
    """Client-round flagged if any COMBO feature exceeds its own one-sided threshold."""
    flags: dict[tuple[int, str], bool] = {}
    for feat, sign in COMBO:
        for t, c, x in signed_z(run, feat, sign):
            flags[(t, c)] = flags.get((t, c), False) or x > th[(split, feat)][fpr]
    return flags


def table_attack(c1s: list[dict], th: dict, split: str, benign_runs: list[dict]) -> str:
    names = [c["name"] for c in c1s]
    lines = [f"用 {SPLIT_LABEL[split]} 的良性阈值（FPR 1%）检测各 C1 运行中的恶意客户端（排除前 {WARMUP} 轮）", "",
             "| 特征 | " + " | ".join(names) + " | C1 中良性客户端-轮次的误报率 |",
             "|---|" + "---|" * len(names) + "---|"]
    for feat, label, sign in FEATURES:
        cells, ben_hits, ben_n = [], 0, 0
        t1 = th[(split, feat)][0.01]
        for c1 in c1s:
            z = signed_z(c1, feat, sign)
            mal = [x for _, c, x in z if c1["kinds"].get(c) == "malicious"]
            ben = [x for _, c, x in z if c1["kinds"].get(c) == "benign"]
            cells.append(f"{sum(x > t1 for x in mal)}/{len(mal)}" if mal else "—")
            ben_hits += sum(x > t1 for x in ben)
            ben_n += len(ben)
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {ben_hits / max(ben_n, 1):.1%} |")
    cells, ben_hits, ben_n = [], 0, 0
    for c1 in c1s:
        f = combo_flags(c1, th, split, 0.01)
        mal = [v for (t, c), v in f.items() if c1["kinds"].get(c) == "malicious"]
        ben = [v for (t, c), v in f.items() if c1["kinds"].get(c) == "benign"]
        cells.append(f"{sum(mal)}/{len(mal)}")
        ben_hits += sum(ben)
        ben_n += len(ben)
    p2_fp = [v for run in benign_runs for v in combo_flags(run, th, split, 0.01).values()]
    lines.append("| **组合：效果层大小 或 因子层方向** | " + " | ".join(cells) +
                 f" | {ben_hits / max(ben_n, 1):.1%}（P2 良性 {sum(p2_fp) / max(len(p2_fp), 1):.1%}） |")
    return "\n".join(lines)


def plot_cosine_vs_split(runs, path: Path) -> None:
    feats = [f for f in FEATURES if "cos" in f[0]]
    fig, axes = plt.subplots(1, len(feats), figsize=(3.3 * len(feats), 3.0), constrained_layout=True, sharey=True)
    xs = np.arange(len(runs))
    for ax, (feat, label, _) in zip(axes, feats):
        for i, s in enumerate(runs):
            per_seed = [np.median(raw_values(run, feat)) for run in runs[s]]
            ax.scatter([i] * len(per_seed), per_seed, color=GRAY, s=18, zorder=2)
            v = [x for run in runs[s] for x in raw_values(run, feat)]
            ax.vlines(i, np.quantile(v, 0.1), np.quantile(v, 0.9), color=BLUE, linewidth=2, zorder=1)
            ax.scatter([i], [np.median(v)], color=BLUE, s=36, zorder=3)
        ax.set_xticks(xs, [SPLIT_LABEL[s] for s in runs], rotation=20, fontsize=8, color=INK2)
        style(ax, label)
    axes[0].set_ylabel("benign value (median, 10–90%)", fontsize=8, color=INK2)
    fig.suptitle("Benign similarity vs non-IID level (dots: per-seed medians)", x=0.01, ha="left", fontsize=10, color=INK)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def plot_thresholds(runs, th, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 3.2), constrained_layout=True)
    xs = np.arange(len(runs))
    for k, (feat, label, _) in enumerate(FEATURES[:6]):
        color = BLUE if feat.startswith("effect") else ORANGE
        ls = "-" if "norm" in feat else ("--" if feat.endswith(".cos_rest") else ":")
        ax.plot(xs, [th[(s, feat)][0.01] for s in runs], color=color, linestyle=ls, linewidth=2, marker="o",
                markersize=4, label=label)
    ax.set_xticks(xs, [SPLIT_LABEL[s] for s in runs], fontsize=8, color=INK2)
    style(ax, "One-sided z threshold at 1% benign client-round FPR")
    ax.legend(frameon=False, fontsize=7, ncols=2, labelcolor=INK)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def main(root: Path, fig_dir: Path, c1_dir: Path | None, c1_records: Path | None) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    runs = load_p2(root)
    print("已完成的运行：", {s: len(rs) for s, rs in runs.items()}, "\n")
    th = thresholds(runs)
    print(table_thresholds(runs, th), "\n")
    print(table_dispersion(runs), "\n")
    plot_cosine_vs_split(runs, fig_dir / "p2_benign_cosine_vs_split.png")
    plot_thresholds(runs, th, fig_dir / "p2_thresholds.png")
    if c1_dir is not None and "d0.5" in runs:
        c1s = [load_run(Path(d), c1_records) for d in str(c1_dir).split(",")]
        for c, d in zip(c1s, str(c1_dir).split(",")):
            c["name"] = Path(d).name
        print(table_attack(c1s, th, "d0.5", runs["d0.5"]))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(Path(a[0]), Path(a[1]), a[2] if len(a) > 2 else None, Path(a[3]) if len(a) > 3 else None)
