"""Checks the lab itself with a scripted fake model. No Ollama needed. Run: python selfcheck.py"""
import json
import shutil
from pathlib import Path

from harnesslab.harnesses import LEVELS, parse_text_tool_call, run_one, trim_context
from harnesslab.workspace import Workspace, run_checks

TASKS = sorted(p for p in Path("tasks").iterdir() if p.is_dir())
fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


class Fake:
    """Replays a script of replies, one per chat() call."""
    def __init__(self, script):
        self.script = list(script)

    def chat(self, messages, tools=None):
        return self.script.pop(0) if self.script else {"content": "done", "tool_calls": []}


def call(name, **args):
    return {"content": "", "tool_calls": [{"name": name, "arguments": args}]}


def text(s):
    return {"content": s, "tool_calls": []}


# 1. Every task starts broken, and its reference fix passes.
for t in TASKS:
    ws = Workspace(t)
    ok_before, _ = run_checks(ws.dir)
    ws.write_file("solution.py", (Path("reference") / f"{t.name}.py").read_text())
    ok_after, out = run_checks(ws.dir)
    ws.cleanup()
    check(f"{t.name}: fails before, passes after reference fix", (not ok_before) and ok_after)

t = TASKS[0]
fix = (Path("reference") / f"{t.name}.py").read_text()
task = json.loads((t / "task.json").read_text())

# 2. Each harness level can solve a task when the "model" behaves.
scripts = {
    "H0": [text("Here:\n```python\n" + fix + "```")],
    "H1": [call("read_file", path="solution.py"), call("write_file", path="solution.py", content=fix), text("done")],
    "H2": [call("write_file", path="solution.py", content=fix), call("run_tests"), text("done")],
    "H3": [call("write_file", path="solution.py", content=fix), call("run_tests"), text("done")],
    "H4": [call("write_file", path="solution.py", content=fix), call("run_tests"), text("done")],
}
for lvl in LEVELS:
    r = run_one(lvl, Fake(scripts[lvl]), t, task)
    check(f"{lvl} solves task with a well-behaved model", r["passed"] == 1 and not r["error"])

# 3. H0 with a wrong answer fails; scoring is not fooled.
r = run_one("H0", Fake([text("```python\ndef fizzbuzz(n):\n    return []\n```")]), t, task)
check("H0 wrong answer scores as fail", r["passed"] == 0)

# 4. Tampering: without guards the model can edit tests; scoring still uses the originals.
cheat_tests = "from solution import fizzbuzz\ndef test_x():\n    assert True\n"
r = run_one("H2", Fake([call("write_file", path="test_solution.py", content=cheat_tests), call("run_tests"), text("done")]), t, task)
check("H2 test edit is detected and does NOT count as a pass", r["tampered"] == 1 and r["passed"] == 0)

# 5. H3 blocks test edits and blocks early finishing.
r = run_one("H3", Fake([call("write_file", path="test_solution.py", content=cheat_tests), text("all fixed!"),
                        call("write_file", path="solution.py", content=fix), call("run_tests"), text("done")]), t, task)
check("H3 blocks test edit (tampered=0)", r["tampered"] == 0)
check("H3 refuses early 'all fixed!' then solves", r["passed"] == 1 and r["guard_blocks"] >= 2)

# 6. Paths outside the task folder are always refused (protects your real files).
ws = Workspace(t)
check("write outside folder refused", "outside" in ws.write_file("../evil.py", "x"))
check("read outside folder refused", "outside" in ws.read_file("../../etc/passwd"))
ws.cleanup()

# 7. Tool call printed as text is still executed.
txt = 'Sure:\n{"name": "write_file", "arguments": {"path": "solution.py", "content": ' + json.dumps(fix) + '}}'
check("parser reads tool call written as text", parse_text_tool_call(txt, ["write_file"])["name"] == "write_file")
check("parser rejects unknown tool", parse_text_tool_call('{"name": "rm_rf", "arguments": {}}', ["write_file"]) is None)
r = run_one("H2", Fake([text(txt), call("run_tests"), text("done")]), t, task)
check("H2 solves via text-style tool call", r["passed"] == 1)

# 8. Infinite loops cannot hang the lab.
loop = "def fizzbuzz(n):\n    while True:\n        pass\n"
r = run_one("H0", Fake([text("```python\n" + loop + "```")]), t, task)
check("infinite loop is stopped by the timeout", r["passed"] == 0)

# 9. Crashing model is recorded, not fatal.
class Boom:
    def chat(self, *a, **k):
        raise RuntimeError("model offline")
r = run_one("H2", Boom(), t, task)
check("model crash recorded as failed attempt", r["passed"] == 0 and "offline" in r["error"])

# 10. H4 context trimming keeps a valid shape.
msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
for i in range(8):
    msgs.append({"role": "assistant", "content": "", "tool_calls": []})
    msgs.append({"role": "tool", "tool_name": "x", "content": "y" * 900})
tr = trim_context(msgs)
check("trim keeps system+task, shortens output, no orphan tool first", tr[:2] == msgs[:2] and tr[2]["role"] != "tool" and len(tr) <= 8 and all(len(m["content"]) < 500 for m in tr[2:] if m["role"] == "tool"))

print("\nALL GOOD" if not fails else f"\n{len(fails)} FAILED: {fails}")
raise SystemExit(1 if fails else 0)
