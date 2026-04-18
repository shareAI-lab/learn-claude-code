from __future__ import annotations

from pathlib import Path

RULES_DIRNAME = ".coding-deepgent"
RULES_FILENAME = "RULES.md"


def project_rules_path(workdir: Path) -> Path:
    return workdir / RULES_DIRNAME / RULES_FILENAME


def read_project_rules(workdir: Path) -> str | None:
    path = project_rules_path(workdir)
    if not path.exists() or not path.is_file():
        return None
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return None
    return content


def render_project_rules_for_prompt(workdir: Path) -> str | None:
    content = read_project_rules(workdir)
    if content is None:
        return None
    return (
        "Project-level rules:\n"
        f"{content}\n\n"
        "Treat these rules as persistent behavior constraints for this project."
    )


def project_rules_signal(workdir: Path) -> str:
    path = project_rules_path(workdir)
    if path.exists() and path.is_file():
        return f"- present: {RULES_DIRNAME}/{RULES_FILENAME}"
    return "- none"
