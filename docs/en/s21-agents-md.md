# s21: AGENTS.md Inheritance

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19 > s20 > [ s21 ] > s22 > s23`

> *"Instructions live where the code lives"* -- walk the tree, merge by proximity.
>
> **Harness layer**: Context inheritance -- the harness assembles instructions from the directory structure.

## Problem

By s20, the agent respects approval policies. But instructions are still flat: one system prompt, one CLAUDE.md at the repo root. In a monorepo with 20 subprojects, the root instructions are too generic for the auth service and irrelevant to the frontend.

The solution: put instructions closer to the code. An `AGENTS.md` at the project root sets global rules. One in `services/auth/` overrides for auth-specific patterns. The harness walks the tree and merges.

## Solution

```
Directory tree with AGENTS.md at each level:

/ (repo root)
|-- AGENTS.md          (global: always use TypeScript, no console.log)
|-- src/
|   |-- AGENTS.md      (src-wide: prefer functional components)
|   |-- components/
|   |   `-- Button.tsx  <- inherits repo + src/
|   `-- utils/
|       `-- helpers.ts  <- inherits repo + src/
|-- services/
    |-- AGENTS.md      (services: use fastify, not express)
    |-- auth/
    |   |-- AGENTS.md  (auth: use JWT, session timeout 30m)
    |   `-- login.ts   <- inherits repo + services/ + auth/
    `-- payments/
        `-- charge.ts  <- inherits repo + services/

Merge order (nearest-file-wins):
  1. Repo root AGENTS.md     (lowest priority)
  2. services/AGENTS.md
  3. services/auth/AGENTS.md (highest priority)

Final context for login.ts = [1] + [2] + [3], [3] overrides [1][2]
```

## How It Works

1. **Walk the directory tree.** Find all AGENTS.md files on the path from the target file to the repo root.

```python
def find_agents_mds(target_path: str, repo_root: str) -> list:
    parts = Path(target_path).relative_to(repo_root).parts
    agents_files = []
    for i in range(len(parts), -1, -1):
        candidate = Path(repo_root, *parts[:i], "AGENTS.md")
        if candidate.is_file():
            agents_files.append(candidate)
    return agents_files  # root-first order
```

2. **Load and merge.** Read each file, merge with later files taking priority.

```python
def merge_agents_mds(files: list) -> str:
    sections = {}
    for f in files:
        content = f.read_text()
        parsed = parse_markdown_sections(content)
        for section, text in parsed.items():
            sections[section] = text  # nearest overwrites
    return "\n\n".join(sections.values())
```

3. **Parse sections.** Split AGENTS.md into named sections for granular merging.

```python
def parse_markdown_sections(content: str) -> dict:
    sections = {}
    current = None
    lines = []
    for line in content.split("\n"):
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(lines).strip()
            current = line[3:].strip()
            lines = []
        elif current:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()
    return sections
```

4. **Build the system prompt.** Inject merged instructions into the agent context.

```python
def build_system_prompt(target_file: str, repo_root: str) -> str:
    agents_files = find_agents_mds(target_file, repo_root)
    merged = merge_agents_mds(agents_files)
    return f"<agent-instructions>\n{merged}\n</agent-instructions>"
```

5. **Cache the result.** Directory structure rarely changes.

```python
from functools import lru_cache

@lru_cache(maxsize=512)
def get_merged_instructions(target_path: str) -> str:
    agents_files = find_agents_mds(target_path, REPO_ROOT)
    return merge_agents_mds(agents_files)
```

## What Changed From s20

| Component       | Before (s20)              | After (s21)                       |
|-----------------|---------------------------|-----------------------------------|
| Instructions    | Single system prompt      | Multi-level AGENTS.md inheritance |
| Scope           | Global                    | Nearest-file-wins per directory   |
| Merging         | None                      | Section-level merge with override |
| Discovery       | Static config             | Directory tree walking            |
| Performance     | Full prompt each time     | LRU-cached merge results          |

## Try It

```sh
cd learn-claude-code
python agents/s21_agents_md.py
```

Try these:

1. `Show the merged instructions for services/auth/login.ts` -- see 3-level inheritance
2. `Show the merged instructions for src/components/Button.tsx` -- see 2-level inheritance
3. `Add a new AGENTS.md in services/payments/ and check inheritance`
4. `Show the raw directory tree walk for any file`
5. `Clear the cache and re-check to verify cache refill`
