"""Run every task x harness x run and append results to results/results.csv (resumable).

  python run_all.py --model qwen3:8b --runs 3
  python run_all.py --model qwen3:8b --runs 1 --tasks t01 t02 --harnesses H0 H2   (quick test)
"""
import argparse
import csv
import json
from pathlib import Path

from harnesslab.harnesses import LEVELS, run_one
from harnesslab.llm import OllamaLLM

FIELDS = ["model", "task", "harness", "run", "passed", "steps", "llm_calls", "seconds", "tampered", "guard_blocks", "error"]
CSV = Path("results/results.csv")


def load_done():
    if not CSV.exists():
        return set()
    with CSV.open(newline="") as f:
        return {(r["model"], r["task"], r["harness"], int(r["run"])) for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--harnesses", nargs="*", default=LEVELS)
    ap.add_argument("--tasks", nargs="*", default=None, help="task name prefixes, e.g. t01 t05")
    a = ap.parse_args()

    tasks = sorted(p for p in Path("tasks").iterdir() if p.is_dir())
    if a.tasks:
        tasks = [t for t in tasks if any(t.name.startswith(x) for x in a.tasks)]
    llm = OllamaLLM(a.model)
    CSV.parent.mkdir(exist_ok=True)
    done = load_done()
    new_file = not CSV.exists()
    total = len(tasks) * len(a.harnesses) * a.runs
    n = 0
    with CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for level in a.harnesses:
            for task_dir in tasks:
                task = json.loads((task_dir / "task.json").read_text())
                for run in range(a.runs):
                    n += 1
                    if (a.model, task_dir.name, level, run) in done:
                        continue
                    res = run_one(level, llm, task_dir, task, run)
                    w.writerow({"model": a.model, "task": task_dir.name, "harness": level, "run": run, **res})
                    f.flush()
                    mark = "PASS" if res["passed"] else "fail"
                    print(f"[{n}/{total}] {level} {task_dir.name} run{run}: {mark}  steps={res['steps']}  {res['seconds']}s"
                          + (f"  ERROR {res['error']}" if res["error"] else ""), flush=True)
    print("Done. Now run: python make_report.py")


if __name__ == "__main__":
    main()
