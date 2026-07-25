import importlib.util
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
COURSE_MODULES = [
    ("s18", REPO_ROOT / "s18_worktree_isolation" / "code.py"),
    ("s19", REPO_ROOT / "s19_mcp_plugin" / "code.py"),
    ("s20", REPO_ROOT / "s20_comprehensive" / "code.py"),
]


def run_git(cwd: Path, *args: str, check: bool = True):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def init_repo(path: Path):
    run_git(path.parent, "init", "-b", "main", str(path))
    run_git(path, "config", "user.name", "Worktree Test")
    run_git(path, "config", "user.email", "worktree@example.invalid")
    run_git(path, "commit", "--allow-empty", "-m", "base")


def load_course_module(module_name: str, module_path: Path, cwd: Path):
    fake_anthropic = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    fake_dotenv = types.ModuleType("dotenv")
    fake_yaml = types.ModuleType("yaml")
    setattr(fake_anthropic, "Anthropic", FakeAnthropic)
    setattr(fake_dotenv, "load_dotenv", lambda override=True: None)
    setattr(fake_yaml, "safe_load", lambda text: {})
    setattr(fake_yaml, "YAMLError", Exception)

    previous_modules = {
        "anthropic": sys.modules.get("anthropic"),
        "dotenv": sys.modules.get("dotenv"),
        "yaml": sys.modules.get("yaml"),
    }
    previous_cwd = Path.cwd()
    previous_model = os.environ.get("MODEL_ID")
    previous_key = os.environ.get("ANTHROPIC_API_KEY")

    spec = importlib.util.spec_from_file_location(
        f"{module_name}_worktree_cleanup_test", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)

    sys.modules["anthropic"] = fake_anthropic
    sys.modules["dotenv"] = fake_dotenv
    sys.modules["yaml"] = fake_yaml
    os.environ["MODEL_ID"] = "test-model"
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    try:
        os.chdir(cwd)
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous_cwd)
        if previous_model is None:
            os.environ.pop("MODEL_ID", None)
        else:
            os.environ["MODEL_ID"] = previous_model
        if previous_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = previous_key
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def branch_exists(repo: Path, name: str) -> bool:
    result = run_git(
        repo,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{name}",
        check=False,
    )
    return result.returncode == 0


class WorktreeCleanupTests(unittest.TestCase):
    def test_clean_worktree_without_unique_commits_can_be_removed(self):
        for module_name, module_path in COURSE_MODULES:
            with self.subTest(module=module_name), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                init_repo(repo)
                module = load_course_module(module_name, module_path, repo)

                module.create_worktree("demo")
                worktree = repo / ".worktrees" / "demo"
                run_git(worktree, "commit", "--allow-empty", "-m", "work")
                run_git(repo, "merge", "--no-ff", "wt/demo", "-m", "merge work")

                result = module.remove_worktree("demo")

                self.assertIn("removed", result.lower())
                self.assertFalse(worktree.exists())
                self.assertFalse(branch_exists(repo, "wt/demo"))

    def test_uncommitted_files_preserve_worktree(self):
        for module_name, module_path in COURSE_MODULES:
            with self.subTest(module=module_name), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                init_repo(repo)
                module = load_course_module(module_name, module_path, repo)

                module.create_worktree("demo")
                worktree = repo / ".worktrees" / "demo"
                (worktree / "draft.txt").write_text("not committed\n")

                result = module.remove_worktree("demo")

                self.assertIn("discard_changes=true", result)
                self.assertTrue(worktree.exists())
                self.assertTrue(branch_exists(repo, "wt/demo"))

    def test_local_commit_without_upstream_preserves_worktree(self):
        for module_name, module_path in COURSE_MODULES:
            with self.subTest(module=module_name), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                init_repo(repo)
                module = load_course_module(module_name, module_path, repo)

                module.create_worktree("demo")
                worktree = repo / ".worktrees" / "demo"
                run_git(worktree, "commit", "--allow-empty", "-m", "local work")
                upstream = run_git(
                    worktree,
                    "rev-parse",
                    "--abbrev-ref",
                    "@{upstream}",
                    check=False,
                )
                self.assertNotEqual(upstream.returncode, 0)

                result = module.remove_worktree("demo")

                self.assertIn("discard_changes=true", result)
                self.assertTrue(worktree.exists())
                self.assertTrue(branch_exists(repo, "wt/demo"))

    def test_git_verification_failures_preserve_worktree(self):
        for module_name, module_path in COURSE_MODULES:
            for failed_command in ("status", "rev-parse", "rev-list"):
                with (
                    self.subTest(module=module_name, command=failed_command),
                    tempfile.TemporaryDirectory() as tmp,
                ):
                    repo = Path(tmp)
                    init_repo(repo)
                    module = load_course_module(module_name, module_path, repo)
                    module.create_worktree("demo")
                    worktree = repo / ".worktrees" / "demo"
                    real_run = module.subprocess.run

                    def run_with_failure(args, **kwargs):
                        if args[:2] == ["git", failed_command]:
                            if kwargs.get("check"):
                                raise subprocess.CalledProcessError(128, args)
                            return subprocess.CompletedProcess(args, 128, "", "failed")
                        return real_run(args, **kwargs)

                    with mock.patch.object(
                        module.subprocess, "run", side_effect=run_with_failure
                    ):
                        result = module.remove_worktree("demo")

                    self.assertIn("Cannot verify", result)
                    self.assertTrue(worktree.exists())
                    self.assertTrue(branch_exists(repo, "wt/demo"))


if __name__ == "__main__":
    unittest.main()
