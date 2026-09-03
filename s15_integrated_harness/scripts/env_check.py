#!/usr/bin/env python3
"""Environment preflight checks for the s15 integrated harness.

Runs a battery of stdlib-only checks against the project tree rooted at the
parent directory of this script (the s15_integrated_harness/ directory):

  1. python_version     interpreter is Python >= 3.8 (actual version printed)
  2. required_modules   code.py, trace_runtime.py, trace_stats.py, trace_view.py
                        exist and byte-compile (py_compile) cleanly
  3. required_files     README.md, code.py, run_tests.sh, Makefile exist
  4. syntax             every .py in the project (the four root modules plus
                        scripts/*.py and tests/*.py) parses with ast, i.e. has
                        no syntax errors
  5. imports            no non-stdlib top-level imports in those .py files;
                        the stdlib whitelist is built from
                        sys.stdlib_module_names (with a sysconfig-based
                        fallback on Python < 3.10) and anything else is
                        flagged
  6. traces             traces/ exists, contains at least one .jsonl run
                        file, and every non-blank line of every .jsonl file
                        parses as JSON
  7. tests              tests/ exists and contains at least one test file

Usage:
    python3 scripts/env_check.py
        Print a human-readable PASS/FAIL table with per-check details and a
        one-line summary.  Exit code 0 only if every check passes.

    python3 scripts/env_check.py --json
        Print a machine-readable JSON report with the same checks (including
        full detail lists) and an "ok" boolean.

Exit codes: 0 = all checks passed, 1 = one or more checks failed,
2 = unexpected internal error.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import py_compile
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set

MIN_PYTHON = (3, 8)
ROOT_MODULES = ("code.py", "trace_runtime.py", "trace_stats.py", "trace_view.py")
REQUIRED_FILES = ("README.md", "code.py", "run_tests.sh", "Makefile")
SCAN_SUBDIRS = ("scripts", "tests")


class Check:
    """Outcome of one preflight check."""

    def __init__(self, name: str, passed: bool, details: Optional[List[str]] = None) -> None:
        self.name = name
        self.passed = bool(passed)
        self.details = list(details or [])

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def project_py_files(root: Path) -> List[Path]:
    """The .py files this harness audits: the four root modules plus
    scripts/*.py and tests/*.py (matching the task's explicit list)."""
    files = [root / name for name in ROOT_MODULES]
    for sub in SCAN_SUBDIRS:
        sub_dir = root / sub
        if sub_dir.is_dir():
            files.extend(sorted(sub_dir.glob("*.py")))
    return files


def stdlib_whitelist() -> Set[str]:
    """Top-level stdlib module names.

    Prefers sys.stdlib_module_names (Python >= 3.10); on older interpreters
    falls back to scanning the purelib directory reported by sysconfig.
    """
    names: Set[str] = set(sys.builtin_module_names)
    names.add("__future__")
    if hasattr(sys, "stdlib_module_names"):
        names.update(sys.stdlib_module_names)
        return names
    import sysconfig

    purelib = sysconfig.get_paths().get("purelib")
    if purelib:
        lib = Path(purelib)
        if lib.is_dir():
            for entry in lib.iterdir():
                if entry.is_file() and entry.suffix == ".py":
                    names.add(entry.stem)
                elif entry.is_dir() and (entry / "__init__.py").is_file():
                    names.add(entry.name)
    return names


def parse_source(path: Path):
    """Return (tree, error) for a Python source file."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, "unreadable: %s" % exc
    try:
        return ast.parse(source, filename=str(path)), None
    except SyntaxError as exc:
        return None, "%s: %s" % (exc.lineno, exc.msg)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_python_version() -> Check:
    actual = ".".join(str(x) for x in sys.version_info[:3])
    required = "%d.%d" % MIN_PYTHON
    if sys.version_info[:2] >= MIN_PYTHON:
        return Check("python_version", True,
                     ["Python %s (required >= %s)" % (actual, required)])
    return Check("python_version", False,
                 ["Python %s is older than the required %s" % (actual, required)])


def check_required_modules(root: Path) -> Check:
    details: List[str] = []
    passed = True
    # Compile into a throwaway directory so the repo's __pycache__ is untouched.
    with tempfile.TemporaryDirectory(prefix="env_check_") as tmp:
        for index, name in enumerate(ROOT_MODULES):
            path = root / name
            if not path.is_file():
                passed = False
                details.append("%s: missing" % name)
                continue
            try:
                py_compile.compile(str(path), cfile=os.path.join(tmp, "%d.pyc" % index),
                                   doraise=True)
            except py_compile.PyCompileError as exc:
                passed = False
                first = (exc.msg or "compile error").splitlines()[0]
                details.append("%s: py_compile failed (%s)" % (name, first))
            except OSError as exc:
                passed = False
                details.append("%s: py_compile failed (%s)" % (name, exc))
            else:
                details.append("%s: py_compile clean" % name)
    return Check("required_modules", passed, details)


def check_required_files(root: Path) -> Check:
    details: List[str] = []
    passed = True
    for name in REQUIRED_FILES:
        if (root / name).is_file():
            details.append("%s: ok" % name)
        else:
            passed = False
            details.append("%s: missing" % name)
    return Check("required_files", passed, details)


def check_syntax(root: Path) -> Check:
    files = project_py_files(root)
    details: List[str] = []
    passed = True
    if not files:
        return Check("syntax", False, ["no .py files found in the project"])
    for path in files:
        rel = path.relative_to(root).as_posix()
        tree, error = parse_source(path)
        if tree is None:
            passed = False
            details.append("%s: %s" % (rel, error))
        else:
            details.append("%s: parses (%d top-level statements)"
                           % (rel, len(tree.body)))
    return Check("syntax", passed, details)


def check_imports(root: Path, whitelist: Set[str]) -> Check:
    details: List[str] = []
    passed = True
    for path in project_py_files(root):
        rel = path.relative_to(root).as_posix()
        tree, _error = parse_source(path)
        if tree is None:
            continue  # already reported (or missing) by the syntax check
        offenders: Dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                tops = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                # Relative imports (level >= 1) are project-local, not
                # third-party; only absolute imports are audited.
                tops = [node.module.split(".")[0]] if (node.level == 0 and node.module) else []
            else:
                continue
            for top in tops:
                if top not in whitelist:
                    offenders.setdefault(top, node.lineno)
        if offenders:
            passed = False
            named = ", ".join("%s (line %d)" % (mod, line)
                              for mod, line in sorted(offenders.items(),
                                                      key=lambda kv: kv[1]))
            details.append("%s: non-stdlib imports: %s" % (rel, named))
        else:
            details.append("%s: stdlib-only" % rel)
    return Check("imports", passed, details)


def check_traces(root: Path) -> Check:
    tdir = root / "traces"
    if not tdir.is_dir():
        return Check("traces", False, ["traces/ directory not found"])
    files = sorted(tdir.glob("*.jsonl"))
    if not files:
        return Check("traces", False, ["traces/ contains no .jsonl files"])
    total = 0
    bad: List[str] = []
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    if not line.strip():
                        continue  # tolerate blank lines / trailing newline
                    total += 1
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as exc:
                        bad.append("%s:%d: %s" % (path.name, lineno, exc.msg))
        except OSError as exc:
            return Check("traces", False, ["%s: unreadable: %s" % (path.name, exc)])
    if bad:
        detail = "%d run file(s), %d JSONL line(s), %d malformed: %s" % (
            len(files), total, len(bad), "; ".join(bad[:5]))
        if len(bad) > 5:
            detail += "; +%d more" % (len(bad) - 5)
        return Check("traces", False, [detail])
    return Check("traces", True,
                 ["%d run file(s), %d JSONL line(s), all parse as JSON"
                  % (len(files), total)])


def check_tests(root: Path) -> Check:
    tdir = root / "tests"
    if not tdir.is_dir():
        return Check("tests", False, ["tests/ directory not found"])
    test_files = sorted(p.name for p in tdir.glob("*.py")
                        if p.name.startswith("test_") or p.name.endswith("_test.py"))
    if not test_files:
        return Check("tests", False,
                     ["tests/ contains no test files (test_*.py / *_test.py)"])
    return Check("tests", True,
                 ["%d test file(s): %s" % (len(test_files), ", ".join(test_files))])


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def summarize(checks: List[Check]) -> str:
    total = len(checks)
    failed = [c.name for c in checks if not c.passed]
    if failed:
        return "FAIL - %d/%d checks passed; %d failed: %s" % (
            total - len(failed), total, len(failed), ", ".join(failed))
    return "PASS - all %d checks passed" % total


def print_table(checks: List[Check], root: Path) -> None:
    name_w = max(len(c.name) for c in checks)
    actual = ".".join(str(x) for x in sys.version_info[:3])
    print("s15 integrated harness - environment preflight")
    print("root:   %s" % root)
    print("python: %s" % actual)
    print()
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        first = check.details[0] if check.details else "-"
        print("%s  %s  %s" % (status, check.name.ljust(name_w), first))
        prefix = " " * (len(status) + 2 + name_w + 2)
        for extra in check.details[1:]:
            print("%s%s" % (prefix, extra))


def run_checks(root: Path) -> List[Check]:
    return [
        check_python_version(),
        check_required_modules(root),
        check_required_files(root),
        check_syntax(root),
        check_imports(root, stdlib_whitelist()),
        check_traces(root),
        check_tests(root),
    ]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="env_check.py",
        description="Environment preflight for the s15 integrated harness. "
                    "Exit code 0 only if every check passes.")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable JSON report instead of "
                             "the human-readable table")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    try:
        checks = run_checks(root)
    except Exception as exc:  # defensive: a preflight must never crash silently
        if args.json:
            print(json.dumps({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)},
                             indent=2))
        else:
            print("env_check: internal error: %s: %s" % (type(exc).__name__, exc),
                  file=sys.stderr)
        return 2

    ok = all(c.passed for c in checks)
    summary = summarize(checks)
    if args.json:
        report = {
            "ok": ok,
            "python": ".".join(str(x) for x in sys.version_info[:3]),
            "root": str(root),
            "summary": summary,
            "checks": [c.to_dict() for c in checks],
        }
        print(json.dumps(report, indent=2))
    else:
        print_table(checks, root)
        print()
        print("Summary: %s" % summary)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
