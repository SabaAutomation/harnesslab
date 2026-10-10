"""Turn results/results.csv into results/summary.md (and results/chart.png if matplotlib is installed)."""
import csv
from collections import defaultdict
from pathlib import Path

rows = list(csv.DictReader(open("results/results.csv", newline="")))
if not rows:
    raise SystemExit("results/results.csv is empty. Run run_all.py first.")

models = sorted({r["model"] for r in rows})
out = ["# HarnessLab results\n"]
chart_data = {}
for model in models:
    mine = [r for r in rows if r["model"] == model]
    by = defaultdict(list)
    for r in mine:
        by[r["harness"]].append(r)
    out.append(f"## Model: {model}\n")
    out.append("| Harness | Passed / attempts | Pass rate | Avg steps | Avg seconds | Edited the tests | Guard blocks | Crashes |")
    out.append("|---|---|---|---|---|---|---|---|")
    chart_data[model] = {}
    for h in sorted(by):
        rs = by[h]
        n = len(rs)
        p = sum(int(r["passed"]) for r in rs)
        steps = sum(int(r["steps"]) for r in rs) / n
        secs = sum(float(r["seconds"]) for r in rs) / n
        tam = sum(int(r["tampered"]) for r in rs)
        gb = sum(int(r["guard_blocks"]) for r in rs)
        err = sum(1 for r in rs if r["error"])
        out.append(f"| {h} | {p} / {n} | {100 * p / n:.0f}% | {steps:.1f} | {secs:.1f} | {tam} | {gb} | {err} |")
        chart_data[model][h] = 100 * p / n
    out.append("")
out.append("Scoring always uses the ORIGINAL tests, even if the model edited them. "
           "Small sample, one small local model: read these as a method and a snapshot, not a general law.\n")
Path("results/summary.md").write_text("\n".join(out))
print("\n".join(out))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    palette = ["#1F3A8A", "#C0392B", "#2E7D32", "#B8860B"]
    width = 0.8 / len(models)
    for i, model in enumerate(models):
        hs = sorted(chart_data[model])
        xs = [j + i * width for j in range(len(hs))]
        ax.bar(xs, [chart_data[model][h] for h in hs], width, label=model, color=palette[i % len(palette)])
    ax.set_xticks([j + width * (len(models) - 1) / 2 for j in range(len(hs))])
    ax.set_xticklabels(hs)
    ax.set_ylabel("Tasks solved (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Same model, different harness")
    ax.spines[["top", "right"]].set_visible(False)
    if len(models) > 1:
        ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig("results/chart.png", dpi=160)
    print("Saved results/chart.png")
except ImportError:
    print("(Install matplotlib for a chart: pip install matplotlib)")
