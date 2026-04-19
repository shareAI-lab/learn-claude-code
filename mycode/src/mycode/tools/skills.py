"""Skills 加载机制: 扫描 skills_dirs,按需加载 SKILL.md。

对齐 Claude Code:
- 每个 skill 是一个目录,含 SKILL.md
- SKILL.md 顶部 YAML frontmatter:
    ---
    name: xxx
    description: one-line summary
    ---
    <body markdown>
- 启动时只把 name + description 注入 system prompt
- 模型用 LoadSkill(name=xxx) 按需拉正文
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config.models import Config
from .registry import Tool, ToolRegistry


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class Skill:
    name: str
    description: str
    body: str
    source_path: Path


@dataclass
class SkillRegistry:
    skills: dict[str, Skill] = field(default_factory=dict)

    def add(self, skill: Skill) -> None:
        # 后注册的覆盖同名——由调用方保证扫描顺序 = 优先级
        if skill.name not in self.skills:
            self.skills[skill.name] = skill

    def descriptions(self) -> str:
        if not self.skills:
            return "(no skills registered)"
        return "\n".join(
            f"  - {s.name}: {s.description}" for s in self.skills.values()
        )

    def load(self, name: str) -> str:
        s = self.skills.get(name)
        if not s:
            avail = ", ".join(self.skills.keys()) or "(none)"
            return f"Error: Unknown skill '{name}'. Available: {avail}"
        return f'<skill name="{name}" path="{s.source_path}">\n{s.body}\n</skill>'


def _parse_skill_md(path: Path) -> Skill | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    m = _FRONTMATTER_RE.match(text)
    meta: dict[str, str] = {}
    body = text
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
        body = m.group(2).strip()
    name = meta.get("name") or path.parent.name
    desc = meta.get("description") or "(no description)"
    return Skill(name=name, description=desc, body=body, source_path=path)


def discover_skills(cfg: Config) -> SkillRegistry:
    """按 skills_dirs 顺序扫描,前者优先。"""
    reg = SkillRegistry()
    for d in cfg.skills_dirs:
        root = Path(d).expanduser()
        if not root.is_absolute():
            root = cfg.workspace_root() / root
        if not root.exists() or not root.is_dir():
            continue
        for skill_md in sorted(root.rglob("SKILL.md")):
            skill = _parse_skill_md(skill_md)
            if skill:
                reg.add(skill)
    return reg


def register_load_skill(registry: ToolRegistry, skills: SkillRegistry) -> None:
    registry.register(
        Tool(
            name="LoadSkill",
            description=(
                "Load the full body of a named skill. Call this when you need "
                "specialized procedural knowledge for a task. "
                "Available skill names are listed in the system prompt under <skills>."
            ),
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            handler=lambda **kw: skills.load(kw["name"]),
        )
    )
