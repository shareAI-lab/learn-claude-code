# s05: 스킬 (Skills)

`s01 > s02 > s03 > s04 > [ s05 ] s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"지식은 미리 올리지 말고 필요할 때 로드한다"* -- system prompt가 아니라 tool_result로 주입한다.
>
> **Harness 계층**: 온디맨드 (필요할 때 로드) 지식 -- 도메인 전문성을 모델이 요청할 때 로드합니다.

## 문제

agent가 도메인별 워크플로우(git 컨벤션, 테스트 패턴, 코드 리뷰 체크리스트 등)를 따르도록 만들고 싶다고 합시다. 모든 것을 system prompt에 넣으면 사용하지 않는 skill에 token을 낭비하게 됩니다. 10개의 skill을 각각 2000 token으로 계산하면 총 20,000 token이 되는데, 대부분은 주어진 작업과 무관합니다.

## 해결책

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

Layer 1: system prompt 안의 skill *이름* (저렴함). Layer 2: tool_result를 통한 전체 *본문* (필요할 때 로드).

## 동작 원리

1. 각 skill은 YAML frontmatter가 포함된 `SKILL.md` 를 담은 디렉터리입니다.

```
skills/
  pdf/
    SKILL.md       # ---\n name: pdf\n description: Process PDF files\n ---\n ...
  code-review/
    SKILL.md       # ---\n name: code-review\n description: Review code\n ---\n ...
```

2. SkillLoader는 `SKILL.md` 파일들을 스캔하고, 디렉터리 이름을 skill 식별자로 사용합니다.

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

3. Layer 1은 system prompt로 들어갑니다. Layer 2는 단지 또 하나의 tool handler일 뿐입니다.

```python
SYSTEM = f"""You are a coding agent at {WORKDIR}.
Skills available:
{SKILL_LOADER.get_descriptions()}"""

TOOL_HANDLERS = {
    # ...base tools...
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
}
```

모델은 어떤 skill이 존재하는지 학습하고(저렴함), 관련이 있을 때만 로드합니다(비용이 큰 작업).

## s04에서 달라진 점

| 구성 요소        | 이전 (s04)        | 이후 (s05)                   |
|----------------|------------------|------------------------------|
| 도구            | 5개 (기본 + task) | 5개 (기본 + load_skill)        |
| System prompt  | 정적 문자열       | + skill 설명 추가             |
| 지식            | 없음             | skills/\*/SKILL.md 파일들     |
| 주입 방식        | 없음             | 2계층 (system + result)      |

## 실행해 보기

```sh
cd learn-claude-code
python agents/s05_skill_loading.py
```

1. `What skills are available?`
2. `Load the agent-builder skill and follow its instructions`
3. `I need to do a code review -- load the relevant skill first`
4. `Build an MCP server using the mcp-builder skill`
