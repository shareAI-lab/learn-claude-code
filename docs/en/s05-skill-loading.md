# s05: Skills

`s01 > s02 > s03 > s04 > [ s05 ] > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

## What You'll Learn
- Why stuffing all domain knowledge into the system prompt wastes tokens
- The two-layer loading pattern: cheap names up front, expensive bodies on demand
- How frontmatter (YAML metadata at the top of a file) gives each skill a name and description
- How the model decides for itself which skill to load and when

You don't memorize every recipe in every cookbook you own. You know which shelf each cookbook sits on, and you pull one down only when you're actually cooking that dish. An agent's domain knowledge works the same way. You might have expertise files for git workflows, testing patterns, code review checklists, PDF processing -- dozens of topics. Loading all of them into the system prompt on every request is like reading every cookbook cover to cover before cracking a single egg. Most of that knowledge is irrelevant to any given task.

## The Problem

You want your agent to follow domain-specific workflows: git conventions, testing best practices, code review checklists. The naive approach is to put everything in the system prompt. But 10 skills at 2,000 tokens each means 20,000 tokens of instructions on every API call -- most of which have nothing to do with the current question. You pay for those tokens every turn, and worse, all that irrelevant text competes for the model's attention with the content that actually matters.

## The Solution

Split knowledge into two layers. Layer 1 lives in the system prompt and is cheap: just skill names and one-line descriptions (~100 tokens per skill). Layer 2 is the full skill body, loaded on demand through a tool call only when the model decides it needs that knowledge.

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

## How It Works

**Step 1.** Each skill is a directory containing a `SKILL.md` file. The file starts with YAML frontmatter (a metadata block delimited by `---` lines) that declares the skill's name and description, followed by the full instruction body.

```
skills/
  pdf/
    SKILL.md       # ---\n name: pdf\n description: Process PDF files\n ---\n ...
  code-review/
    SKILL.md       # ---\n name: code-review\n description: Review code\n ---\n ...
```

**Step 2.** `SkillLoader` scans for all `SKILL.md` files at startup. It parses the frontmatter to extract names and descriptions, and stores the full body for later retrieval.

```python
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills = {}
        for f in sorted(skills_dir.rglob("SKILL.md")):
            text = f.read_text()
            meta, body = self._parse_frontmatter(text)
            # Use the frontmatter name, or fall back to the directory name
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body}

    def get_descriptions(self) -> str:
        """Layer 1: cheap one-liners for the system prompt."""
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "")
            lines.append(f"  - {name}: {desc}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        """Layer 2: full body, returned as a tool_result."""
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'."
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"
```

**Step 3.** Layer 1 goes into the system prompt so the model always knows what skills exist. Layer 2 is wired up as a normal tool handler -- the model calls `load_skill` when it decides it needs the full instructions.

```python
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Skills available:
{SKILL_LOADER.get_descriptions()}"""

TOOL_HANDLERS = {
    # ...base tools...
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
}
```

The model learns what skills exist (cheap, ~100 tokens each) and loads them only when relevant (expensive, ~2000 tokens each). On a typical turn, only one skill is loaded instead of all ten.

## What Changed From s04

| Component      | Before (s04)     | After (s05)                |
|----------------|------------------|----------------------------|
| Tools          | 5 (base + task)  | 5 (base + load_skill)      |
| System prompt  | Static string    | + skill descriptions       |
| Knowledge      | None             | skills/\*/SKILL.md files   |
| Injection      | None             | Two-layer (system + result)|

## Try It

```sh
cd learn-claude-code
python agents/s05_skill_loading.py
```

1. `What skills are available?`
2. `Load the agent-builder skill and follow its instructions`
3. `I need to do a code review -- load the relevant skill first`
4. `Build an MCP server using the mcp-builder skill`

## What You've Mastered

At this point, you can:

- Explain why "list first, load later" beats stuffing everything into the system prompt
- Write a `SKILL.md` with YAML frontmatter that a `SkillLoader` can discover
- Wire up two-layer loading: cheap descriptions in the system prompt, full bodies via `tool_result`
- Let the model decide for itself when domain knowledge is worth loading

You don't need skill ranking systems, multi-provider merging, parameterized templates, or recovery-time restoration rules. The core pattern is simple: advertise cheaply, load on demand.

## What's Next

You now know how to keep knowledge out of context until it's needed. But what happens when context grows large anyway -- after dozens of turns of real work? In s06, you'll learn how to compress a long conversation down to its essentials so the agent can keep working without hitting token limits.

## Key Takeaway

> Advertise skill names cheaply in the system prompt; load the full body through a tool call only when the model actually needs it.
