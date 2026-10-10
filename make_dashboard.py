"""Turn results/results.csv into one self-contained dashboard: results/dashboard.html

Standard library only. Open the HTML file in any browser and screenshot it for your README.
Every number on the page is computed from results.csv, nothing is typed in by hand.

    python make_dashboard.py
    python make_dashboard.py --csv results/results.csv --out results/dashboard.html
    python make_dashboard.py --tasks t05 t06 t07 t08 t09 t10 --runs 1   (only compare like with like)
"""
import argparse
import csv
import html
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LEVEL_NAMES = {
    "H0": "bare model",
    "H1": "+ file tools",
    "H2": "+ test loop",
    "H3": "+ guards",
    "H4": "+ context trim",
}


def load(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"{path} not found. Run run_all.py first.")
    rows = list(csv.DictReader(open(p, newline="", encoding="utf-8")))
    if not rows:
        raise SystemExit(f"{path} is empty. Run run_all.py first.")
    return rows


def i(row, key):
    try:
        return int(float(row.get(key) or 0))
    except ValueError:
        return 0


def f(row, key):
    try:
        return float(row.get(key) or 0)
    except ValueError:
        return 0.0


def select(rows, tasks=None, runs=None):
    """Keep only the tasks (name prefixes) and run indexes you want to compare."""
    out = rows
    if tasks:
        out = [r for r in out if any(r["task"].startswith(t) for t in tasks)]
    if runs is not None:
        out = [r for r in out if i(r, "run") < runs]
    return out


def esc(x):
    return html.escape(str(x), quote=True)


def stats(rows):
    n = len(rows)
    p = sum(i(r, "passed") for r in rows)
    return {
        "n": n,
        "passed": p,
        "rate": 100.0 * p / n if n else 0.0,
        "steps": sum(i(r, "steps") for r in rows) / n if n else 0.0,
        "secs": sum(f(r, "seconds") for r in rows) / n if n else 0.0,
        "tampered": sum(i(r, "tampered") for r in rows),
        "guard": sum(i(r, "guard_blocks") for r in rows),
        "crashes": sum(1 for r in rows if (r.get("error") or "").strip()),
    }


def bar_chart(by_h):
    """Vertical bars, one per harness level. Direct labels, no legend needed."""
    hs = sorted(by_h)
    W, H = 760, 330
    left, right, top, bottom = 52, 16, 28, 62
    pw, ph = W - left - right, H - top - bottom
    slot = pw / max(len(hs), 1)
    bw = min(86, slot * 0.62)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Pass rate by harness level" class="chart">']
    for tick in (0, 25, 50, 75, 100):
        y = top + ph * (1 - tick / 100)
        out.append(f'<line x1="{left}" x2="{W - right}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{left - 8}" y="{y + 4:.1f}" class="axis" text-anchor="end">{tick}%</text>')
    for k, h in enumerate(hs):
        s = by_h[h]
        cx = left + slot * (k + 0.5)
        bh = ph * s["rate"] / 100
        y = top + ph - bh
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(bh, 1.5):.1f}" rx="4" class="bar"/>')
        out.append(f'<text x="{cx:.1f}" y="{y - 8:.1f}" text-anchor="middle" class="val">{s["rate"]:.0f}%</text>')
        out.append(f'<text x="{cx:.1f}" y="{top + ph + 22}" text-anchor="middle" class="lvl">{esc(h)}</text>')
        out.append(f'<text x="{cx:.1f}" y="{top + ph + 40}" text-anchor="middle" class="axis">{esc(LEVEL_NAMES.get(h, ""))}</text>')
        out.append(f'<text x="{cx:.1f}" y="{top + ph + 55}" text-anchor="middle" class="axis">{s["passed"]}/{s["n"]} passed</text>')
    out.append("</svg>")
    return "\n".join(out)


def heat(rows, hs):
    tasks = sorted({r["task"] for r in rows})
    cell = defaultdict(list)
    for r in rows:
        cell[(r["task"], r["harness"])].append(r)
    out = ['<table class="heat"><thead><tr><th>Task</th>']
    for h in hs:
        out.append(f"<th>{esc(h)}</th>")
    out.append("</tr></thead><tbody>")
    for t in tasks:
        out.append(f'<tr><th class="task">{esc(t)}</th>')
        for h in hs:
            rs = cell.get((t, h), [])
            if not rs:
                out.append('<td class="empty">&ndash;</td>')
                continue
            p = sum(i(r, "passed") for r in rs)
            frac = p / len(rs)
            if frac == 0:
                bg = "rgba(192,57,43,0.20)"
            else:
                bg = f"rgba(46,125,50,{0.16 + 0.56 * frac:.2f})"
            out.append(f'<td style="background:{bg}">{p}/{len(rs)}</td>')
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def table(by_h):
    out = ['<table class="stats"><thead><tr><th>Level</th><th>What it adds</th><th>Pass rate</th>'
           "<th>Avg steps</th><th>Avg seconds</th><th>Edited the tests</th><th>Guard blocks</th><th>Crashes</th>"
           "</tr></thead><tbody>"]
    for h in sorted(by_h):
        s = by_h[h]
        out.append(
            f'<tr><th class="task">{esc(h)}</th><td class="l">{esc(LEVEL_NAMES.get(h, ""))}</td>'
            f'<td>{s["rate"]:.0f}% ({s["passed"]}/{s["n"]})</td><td>{s["steps"]:.1f}</td>'
            f'<td>{s["secs"]:.0f}</td><td>{s["tampered"]}</td><td>{s["guard"]}</td><td>{s["crashes"]}</td></tr>'
        )
    out.append("</tbody></table>")
    return "".join(out)


def jump_note(by_h):
    hs = sorted(by_h)
    if len(hs) < 2:
        return "Only one level has data so far."
    best = None
    for a, b in zip(hs, hs[1:]):
        d = by_h[b]["rate"] - by_h[a]["rate"]
        if best is None or d > best[0]:
            best = (d, a, b)
    d, a, b = best
    if d <= 0:
        return "No level beat the one before it in this run."
    return f"Biggest step up between neighbouring levels: {a} to {b} (+{d:.0f} percentage points)."


CSS = """
:root{--bg:#f7f5ef;--card:#fff;--ink:#1d2433;--mute:#5d6678;--line:#e3e0d6;--bar:#1f3a8a;--accent:#c0392b}
@media (prefers-color-scheme: dark){:root{--bg:#12151c;--card:#1b2029;--ink:#e8ebf2;--mute:#9aa3b5;--line:#2c3340;--bar:#7aa2ff;--accent:#ff7a6b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 Inter,system-ui,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:32px 20px 48px}
h1{font-size:30px;margin:0;letter-spacing:-.01em}
.sub{color:var(--mute);margin:4px 0 24px}
h2{font-size:18px;margin:0 0 4px}
.note{color:var(--mute);margin:0 0 14px;font-size:14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:20px}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:12px}
.kpi{padding:14px 16px}
.kpi b{display:block;font-size:26px;letter-spacing:-.01em}
.kpi span{color:var(--mute);font-size:13px}
.card{padding:18px 20px;margin-bottom:16px;overflow-x:auto}
.chart{width:100%;height:auto;display:block}
.chart .grid{stroke:var(--line);stroke-width:1}
.chart .axis{fill:var(--mute);font-size:12px}
.chart .val{fill:var(--ink);font-size:15px;font-weight:700}
.chart .lvl{fill:var(--ink);font-size:15px;font-weight:700}
.chart .bar{fill:var(--bar)}
table{border-collapse:separate;border-spacing:3px;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;text-align:center;font-size:14px}
thead th{color:var(--mute);font-weight:600;font-size:13px}
th.task{text-align:left;font-weight:600;white-space:nowrap}
td.l{text-align:left;color:var(--mute)}
.heat td{border-radius:6px;min-width:64px;font-weight:600}
.heat td.empty{color:var(--mute)}
.stats td,.stats th{border-bottom:1px solid var(--line)}
.legend{display:flex;gap:14px;color:var(--mute);font-size:13px;margin-top:10px;flex-wrap:wrap}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.foot{color:var(--mute);font-size:13px;margin-top:22px}
.model{margin:34px 0 14px;font-size:20px}
.warn{border-color:var(--accent);color:var(--ink)}
.warn code{background:var(--bg);padding:1px 5px;border-radius:4px}
"""


def render(rows, src):
    models = sorted({r["model"] for r in rows})
    total = stats(rows)
    parts = []
    for model in models:
        mine = [r for r in rows if r["model"] == model]
        by = defaultdict(list)
        for r in mine:
            by[r["harness"]].append(r)
        by_h = {h: stats(rs) for h, rs in by.items()}
        hs = sorted(by_h)
        runs = len({(r["task"], r["harness"], r["run"]) for r in mine})
        parts.append(f'<h2 class="model">Model: {esc(model)} <span style="color:var(--mute);font-weight:400;font-size:15px">&middot; {len(mine)} attempts</span></h2>')
        counts = {h: s["n"] for h, s in by_h.items()}
        if len(set(counts.values())) > 1:
            detail = ", ".join(f"{h}: {c}" for h, c in sorted(counts.items()))
            parts.append('<div class="card warn"><b>Not a fair comparison yet.</b> '
                         f'The levels have different numbers of attempts ({esc(detail)}). '
                         'Finish the run, or filter with <code>--tasks</code> and <code>--runs</code> so every level covers the same tasks.</div>')
        parts.append('<div class="card"><h2>Tasks solved by harness level</h2>'
                     f'<p class="note">{esc(jump_note(by_h))}</p>{bar_chart(by_h)}</div>')
        parts.append('<div class="card"><h2>Task by level</h2>'
                     '<p class="note">Passed / attempts for every task and harness level.</p>'
                     f'{heat(mine, hs)}'
                     '<div class="legend"><span><i class="sw" style="background:rgba(46,125,50,.72)"></i>passed</span>'
                     '<span><i class="sw" style="background:rgba(192,57,43,.35)"></i>failed</span>'
                     '<span>&ndash; not run yet</span></div></div>')
        parts.append('<div class="card"><h2>Behind the numbers</h2>'
                     '<p class="note">Edited the tests = attempts where the model changed a test file (never counted as a pass). '
                     'Guard blocks = times H3 refused an early "all fixed".</p>'
                     f'{table(by_h)}</div>')
    best_h = max(
        ((h, stats([r for r in rows if r["harness"] == h])) for h in {r["harness"] for r in rows}),
        key=lambda x: x[1]["rate"],
    )
    kp = [
        (str(total["n"]), "attempts recorded"),
        (f'{total["rate"]:.0f}%', "solved overall"),
        (f"{best_h[0]}", f'best level so far ({best_h[1]["rate"]:.0f}%)'),
        (str(total["tampered"]), "attempts that edited the tests"),
    ]
    kpi_html = "".join(f'<div class="kpi"><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in kp)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HarnessLab results</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<h1>HarnessLab</h1>
<p class="sub">Same free local model, five harness levels, tiny bug-fix tasks. Generated {esc(stamp)} from {esc(Path(src).name)}.</p>
<div class="kpis">{kpi_html}</div>
{"".join(parts)}
<p class="foot">Scoring always restores the original tests, so editing the tests never counts as a pass.
Small sample, one small local model, tiny tasks: read this as a method and a snapshot, not a general law.</p>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/results.csv")
    ap.add_argument("--out", default="results/dashboard.html")
    ap.add_argument("--tasks", nargs="*", default=None, help="only these task prefixes, e.g. t05 t06")
    ap.add_argument("--runs", type=int, default=None, help="only run indexes below this number")
    a = ap.parse_args()
    rows = select(load(a.csv), a.tasks, a.runs)
    if not rows:
        raise SystemExit("No rows left after --tasks/--runs filtering.")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rows, a.csv), encoding="utf-8")
    print(f"Saved {out}  ({len(rows)} attempts). Open it in your browser and take a screenshot.")


if __name__ == "__main__":
    main()
