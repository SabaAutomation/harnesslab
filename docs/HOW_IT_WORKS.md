# How HarnessLab works

## The idea

An agent is a model plus a harness: the tools it can use, the loop it runs in, the guardrails around it, and the way its memory is managed. HarnessLab holds the model fixed and changes only the harness, then counts how many tasks get solved. If the numbers move, the harness mattered.

![Ideation sketch](ideation.png)

## The five levels

| Level | Adds | Step budget |
|---|---|---|
| H0 | Nothing. One prompt, one answer, no tools | 0 |
| H1 | `read_file` and `write_file` | 4 |
| H2 | `run_tests`, so the model sees its own failures | 10 |
| H3 | Test files are read-only, and the model cannot finish until the tests pass | 10 |
| H4 | Context trimming: keep the system prompt, the task and the last 6 messages; cut tool output at 400 characters | 10 |

## One attempt, step by step

1. Copy one task into a temporary folder (`workspace.py`).
2. Run the model under the chosen level (`harnesses.py`). Every tool call goes through the workspace, which refuses any path outside the folder.
3. When the attempt ends (model stops, step budget used, or 10-second test timeout), restore the **original** test file and run it.
4. Record one row in `results/results.csv`: passed, steps, LLM calls, seconds, tampered, guard blocks, error.

## Why the scoring is honest

- The original tests are always restored before scoring, so rewriting a test cannot produce a pass.
- If the model touched a test file, the row is marked `tampered` and counts as a fail.
- A model crash or an infinite loop is recorded as a failed attempt, not skipped.
- `selfcheck.py` proves all of this with a scripted fake model, so the lab is tested without a real model.

## Problems met while building it, and the fixes

| Problem | Fix |
|---|---|
| The small model printed its tool calls as text instead of calling them | `parse_text_tool_call` reads the JSON out of the text |
| About 70 seconds per attempt on a laptop CPU | Resumable runs, a task filter (`--tasks`), and a first pass with 1 run |
| A model could game the score by editing the tests | Restore the tests before scoring and flag the attempt |

## Files

| File | Job |
|---|---|
| `run_all.py` | Runs the experiment, resumable, writes `results/results.csv` |
| `make_report.py` | Writes `results/summary.md` and `results/chart.png` |
| `make_dashboard.py` | Writes `results/dashboard.html`, a one-page visual summary |
| `harnesslab/harnesses.py` | The five levels |
| `harnesslab/workspace.py` | Temporary workspace, tools, scoring |
| `harnesslab/llm.py` | Ollama client |
| `harnesslab/minitest.py` | Small pytest-compatible test runner |
| `selfcheck.py` | 27 checks with a fake model |
| `tasks/` | 10 bug-fix tasks; `reference/` holds the correct fixes |
