"""The five harness levels. The model never changes; only this file's behaviour does.

H0  bare model: one prompt, one answer, no tools
H1  + tools (read_file, write_file), a few steps, NO test feedback
H2  + run_tests and a feedback loop with a larger step budget
H3  + guards: test files read-only; cannot finish until tests have passed
H4  + context policy: old steps are trimmed, long tool output is cut
"""
import json
import re
import time

from .workspace import TOOL_SCHEMAS, Workspace

LEVELS = ["H0", "H1", "H2", "H3", "H4"]

SYSTEM = (
    "You fix bugs in small Python files. The task folder contains solution.py (buggy) "
    "and test_solution.py (the tests that must pass). Never rewrite the tests to make "
    "them pass: fix solution.py. When you write solution.py, write the complete file."
)

CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def parse_text_tool_call(content: str, allowed):
    """Some small models print a tool call as JSON text instead of calling it."""
    if not content:
        return None
    dec = json.JSONDecoder()
    for i, ch in enumerate(content):
        if ch != "{":
            continue
        try:
            data, _ = dec.raw_decode(content[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("name") in allowed:
            args = data.get("arguments") or {}
            return {"name": data["name"], "arguments": args if isinstance(args, dict) else {}}
    return None


def trim_context(messages, keep_last=6, cut=400):
    """H4 policy: keep system + task prompt + the last few messages; shorten tool output."""
    head, tail = messages[:2], messages[2:]
    tail = tail[-keep_last:]
    while tail and tail[0]["role"] == "tool":  # never start on an orphaned tool result
        tail = tail[1:]
    out = []
    for m in tail:
        if m["role"] == "tool" and len(m["content"]) > cut:
            m = {**m, "content": m["content"][:cut] + " ...[trimmed]"}
        out.append(m)
    return head + out


def run_h0(llm, task, ws: Workspace):
    sol = ws.read_file("solution.py")
    tests = ws.read_file("test_solution.py")
    prompt = (
        f"{task['description']}\n\nsolution.py:\n```python\n{sol}\n```\n\n"
        f"test_solution.py:\n```python\n{tests}\n```\n\n"
        "Reply with the complete fixed solution.py in one ```python code block."
    )
    r = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}], None)
    m = CODE_BLOCK.search(r["content"])
    if m:
        ws.write_file("solution.py", m.group(1))
    return {"steps": 0, "llm_calls": 1}


def run_agentic(level, llm, task, ws: Workspace):
    tool_names = ["read_file", "write_file"] + (["run_tests"] if level != "H1" else [])
    tools = [TOOL_SCHEMAS[n] for n in tool_names]
    max_steps = 4 if level == "H1" else 10
    guards = level in ("H3", "H4")
    trim = level == "H4"
    fns = {"read_file": ws.read_file, "write_file": ws.write_file, "run_tests": ws.run_tests}

    how = "Read the files, then write the fixed solution.py." if level == "H1" else \
          "Read the files, write the fixed solution.py, then run_tests. If tests fail, read the output and try again."
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"{task['description']}\n{how}"},
    ]
    steps = llm_calls = nudges = 0
    while steps < max_steps:
        send = trim_context(messages) if trim else messages
        r = llm.chat(send, tools)
        llm_calls += 1
        calls = r["tool_calls"] or ([c] if (c := parse_text_tool_call(r["content"], tool_names)) else [])
        messages.append({
            "role": "assistant", "content": r["content"],
            "tool_calls": [{"function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls],
        })
        if not calls:
            # H3 guard: it may not finish until the tests have actually passed.
            if guards and not ws.tests_passed and nudges < 3:
                nudges += 1
                ws.guard_blocks += 1
                messages.append({"role": "user", "content": "Tests have not passed yet. Call run_tests, and keep fixing solution.py until they pass."})
                continue
            break
        c = calls[0]  # one tool per step
        fn = fns.get(c["name"])
        try:
            result = fn(**c["arguments"]) if fn else f"ERROR: unknown tool {c['name']}"
        except TypeError as e:
            result = f"ERROR: bad arguments: {e}"
        steps += 1
        messages.append({"role": "tool", "tool_name": c["name"], "content": str(result)})
    return {"steps": steps, "llm_calls": llm_calls}


def run_one(level, llm, task_dir, task, run_index=0):
    """Run one (task, harness) attempt in a fresh workspace and score it."""
    import traceback
    ws = Workspace(task_dir, protect_tests=level in ("H3", "H4"))
    t0 = time.time()
    error = ""
    info = {"steps": 0, "llm_calls": 0}
    try:
        info = run_h0(llm, task, ws) if level == "H0" else run_agentic(level, llm, task, ws)
    except Exception as e:  # a crash counts as a failed attempt, and is recorded
        error = f"{type(e).__name__}: {e}"[:200]
    seconds = round(time.time() - t0, 1)
    tampered = ws.tampered()
    passed = ws.final_score()
    guard_blocks = ws.guard_blocks
    ws.cleanup()
    return {
        "passed": int(passed), "steps": info["steps"], "llm_calls": info["llm_calls"],
        "seconds": seconds, "tampered": int(tampered), "guard_blocks": guard_blocks, "error": error,
    }
