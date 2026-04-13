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
