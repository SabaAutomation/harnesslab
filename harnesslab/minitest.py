"""Tiny pytest-compatible runner (standard library only).

Usage: python minitest.py <task_dir>
Runs every test_* function in <task_dir>/test_solution.py. Exit code 0 = all passed.
"""
import importlib.util
import sys
import traceback
from pathlib import Path


def main(task_dir: str) -> int:
    d = Path(task_dir).resolve()
    sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location("test_solution", d / "test_solution.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        print("COLLECTION ERROR")
        traceback.print_exc(limit=3, file=sys.stdout)
        return 2
    names = [n for n in dir(mod) if n.startswith("test_") and callable(getattr(mod, n))]
    failed = 0
    for n in names:
        try:
            getattr(mod, n)()
            print(f"PASS {n}")
        except Exception:
            failed += 1
            print(f"FAIL {n}")
            traceback.print_exc(limit=2, file=sys.stdout)
    print(f"{len(names) - failed} passed, {failed} failed")
    return 1 if failed or not names else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
