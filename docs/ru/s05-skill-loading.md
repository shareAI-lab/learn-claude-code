# s05: Skills

`s01 > s02 > s03 > s04 > [ s05 ] s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Загружай знания тогда, когда они нужны, а не заранее"* -- внедряй через tool_result, а не через системный промпт.
>
> **Harness layer**: Знания по запросу -- экспертиза предметной области, загружаемая по мере необходимости model.

## Проблема

Вы хотите, чтобы agent следовал рабочим процессам конкретной предметной области: соглашениям git, паттернам тестирования, чек-листам code review. Размещение всего в системном промпте расходует токены на неиспользуемые skill. 10 skill по 2000 токенов каждый = 20 000 токенов, большинство из которых не имеют отношения к конкретной задаче.

## Решение

```
System prompt (Layer 1 -- always present):
+--------------------------------------+
| You are a coding agent.              |
| Skills available:                    |
|   - git: Git workflow helpers        |  ~100 tokens/skill
|   - test: Testing best practices     |
+--------------------------------------+

When model calls load_skill("git"):
+--------------------------------------+
| tool_result (Layer 2 -- on demand):  |
| <skill name="git">                   |
|   Full git workflow instructions...  |  ~2000 tokens
|   Step 1: ...                        |
| </skill>                             |
+--------------------------------------+
```

Layer 1: *названия* skill в системном промпте (дёшево). Layer 2: полное *содержимое* через tool_result (по запросу).

## Как это работает

1. Каждый skill — это директория с файлом `SKILL.md`, содержащим YAML frontmatter.

```
skills/
  pdf/
    SKILL.md       # ---\n name: pdf\n description: Process PDF files\n ---\n ...
  code-review/
    SKILL.md       # ---\n name: code-review\n description: Review code\n ---\n ...
```

2. SkillLoader сканирует файлы `SKILL.md`, используя имя директории как идентификатор skill.

```python
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills = {}
        for f in sorted(skills_dir.rglob("SKILL.md")):
            text = f.read_text()
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body}

    def get_descriptions(self) -> str:
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "")
            lines.append(f"  - {name}: {desc}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'."
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"
```

3. Layer 1 попадает в системный промпт. Layer 2 — это ещё один tool handler.

```python
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Skills available:
{SKILL_LOADER.get_descriptions()}"""

TOOL_HANDLERS = {
    # ...base tools...
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
}
```

Model узнаёт, какие skill существуют (дёшево), и загружает их при необходимости (дорого).

## Что изменилось по сравнению с s04

| Компонент      | До (s04)         | После (s05)                |
|----------------|------------------|----------------------------|
| Tools          | 5 (base + task)  | 5 (base + load_skill)      |
| System prompt  | Статическая строка | + описания skill          |
| Знания         | Отсутствуют      | файлы skills/\*/SKILL.md   |
| Внедрение      | Отсутствует      | Двухуровневое (system + result)|

## Попробуй сам

```sh
cd learn-claude-code
python agents/s05_skill_loading.py
```

1. `What skills are available?`
2. `Load the agent-builder skill and follow its instructions`
3. `I need to do a code review -- load the relevant skill first`
4. `Build an MCP server using the mcp-builder skill`
