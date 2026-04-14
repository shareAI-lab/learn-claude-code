from __future__ import annotations

from pathlib import Path

from coding_deepgent.skills.schemas import LoadedSkill, SkillMetadata

SKILL_FILE_NAME = "SKILL.md"


def parse_skill_markdown(path: Path) -> LoadedSkill:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Skill file missing frontmatter: {path}")
    _, frontmatter, body = text.split("---", 2)
    metadata: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"Invalid frontmatter line in {path}: {line}")
        metadata[key.strip()] = value.strip().strip('"')
    return LoadedSkill(
        metadata=SkillMetadata.model_validate(metadata),
        body=body.strip(),
        path=path,
    )


def skill_root(workdir: Path, skill_dir: Path) -> Path:
    if skill_dir.is_absolute():
        return skill_dir.resolve()
    return (workdir / skill_dir).resolve()


def load_local_skill(*, workdir: Path, skill_dir: Path, name: str) -> LoadedSkill:
    root = skill_root(workdir, skill_dir)
    path = root / name / SKILL_FILE_NAME
    if not path.is_file():
        raise FileNotFoundError(f"Local skill not found: {name}")
    loaded = parse_skill_markdown(path)
    if loaded.metadata.name != name:
        raise ValueError(
            f"Skill name mismatch: requested {name}, found {loaded.metadata.name}"
        )
    return loaded


def discover_local_skills(
    *,
    workdir: Path,
    skill_dir: Path,
) -> tuple[LoadedSkill, ...]:
    root = skill_root(workdir, skill_dir)
    if not root.exists():
        return ()
    if not root.is_dir():
        raise NotADirectoryError(f"Skill root is not a directory: {root}")

    skills: list[LoadedSkill] = []
    for entry in sorted(root.iterdir(), key=lambda candidate: candidate.name):
        if not entry.is_dir():
            continue
        path = entry / SKILL_FILE_NAME
        if not path.is_file():
            continue
        try:
            loaded = parse_skill_markdown(path)
        except ValueError:
            continue
        if loaded.metadata.name != entry.name:
            raise ValueError(
                f"Skill directory and metadata name must match: {entry.name} != {loaded.metadata.name}"
            )
        skills.append(loaded)
    return tuple(skills)
