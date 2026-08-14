"""s04 introduces the PreToolUse deny list and s05-s08 carry it forward
unchanged. s08 had silently dropped three entries; this test pins the
inherited baseline so a copy-forward can't quietly weaken it again."""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "s04": REPO_ROOT / "s04_hooks" / "code.py",
    "s05": REPO_ROOT / "s05_todo_write" / "code.py",
    "s06": REPO_ROOT / "s06_subagent" / "code.py",
    "s07": REPO_ROOT / "s07_skill_loading" / "code.py",
    "s08": REPO_ROOT / "s08_context_compact" / "code.py",
    "s20": REPO_ROOT / "s20_comprehensive" / "code.py",
}

BASELINE = {"rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="}


def read_deny_list(path: Path) -> set:
    match = re.search(r"^DENY_LIST = \[(.*?)\]$", path.read_text(), re.M | re.S)
    if not match:
        raise AssertionError(f"No DENY_LIST found in {path}")
    return set(re.findall(r'"([^"]*)"', match.group(1)))


class DenyListConsistencyTests(unittest.TestCase):
    def test_deny_list_covers_the_s04_baseline(self):
        for name, path in MODULES.items():
            with self.subTest(module=name):
                self.assertTrue(
                    BASELINE <= read_deny_list(path),
                    f"{name} DENY_LIST is missing "
                    f"{sorted(BASELINE - read_deny_list(path))}")


if __name__ == "__main__":
    unittest.main()
