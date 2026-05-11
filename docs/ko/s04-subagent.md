# s04: 서브에이전트 (Subagents)

`s01 > s02 > s03 > [ s04 ] s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"큰 작업을 잘게 쪼갠다. 각 하위 작업은 깨끗한 context를 받는다"* -- subagent (서브에이전트 — 부모와 별개의 messages[] 를 가진 자식 에이전트)는 독립된 messages[] 를 사용하여 메인 대화를 깨끗하게 유지합니다.
>
> **Harness 계층**: context isolation -- 모델의 사고 명료성을 보호합니다.

## 문제

agent가 작업을 진행하면 messages array가 계속 커집니다. 모든 파일 읽기, 모든 bash 출력이 context에 영구적으로 남습니다. "이 프로젝트는 어떤 테스트 프레임워크를 사용하나요?"라는 질문에 답하려면 5개의 파일을 읽어야 할 수 있지만, 부모가 필요로 하는 것은 단지 "pytest"라는 답뿐입니다.

## 해결책

```
Parent agent                     Subagent
+------------------+             +------------------+
| messages=[...]   |             | messages=[]      | <-- fresh
|                  |  dispatch   |                  |
| tool: task       | ----------> | while tool_use:  |
|   prompt="..."   |             |   call tools     |
|                  |  summary    |   append results |
|   result = "..." | <---------- | return last text |
+------------------+             +------------------+

Parent context stays clean. Subagent context is discarded.
```

## 동작 원리

1. 부모는 `task` 도구를 받습니다. 자식은 `task` 를 제외한 모든 기본 도구를 받습니다 (재귀적 spawn 방지).

```python
PARENT_TOOLS = CHILD_TOOLS + [
    {"name": "task",
     "description": "Spawn a subagent with fresh context.",
     "input_schema": {
         "type": "object",
         "properties": {"prompt": {"type": "string"}},
         "required": ["prompt"],
     }},
]
```

2. subagent는 `messages=[]` 로 시작하여 자체 루프를 실행합니다. 최종 텍스트만 부모에게 반환됩니다.

```python
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]
    for _ in range(30):  # safety limit
        response = client.messages.create(
            model=MODEL, system=SUBAGENT_SYSTEM,
            messages=sub_messages,
            tools=CHILD_TOOLS, max_tokens=8000,
        )
        sub_messages.append({"role": "assistant",
                             "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input)
                results.append({"type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output)[:50000]})
        sub_messages.append({"role": "user", "content": results})
    return "".join(
        b.text for b in response.content if hasattr(b, "text")
    ) or "(no summary)"
```

자식의 전체 message history (30개 이상의 tool 호출일 수도 있는)는 버려집니다. 부모는 한 문단짜리 요약을 일반적인 `tool_result` 형태로 받습니다.

## s03에서 달라진 점

| 구성 요소       | 이전 (s03)       | 이후 (s04)                  |
|----------------|------------------|-----------------------------|
| 도구            | 5개              | 5개 (기본) + task (부모용)    |
| Context        | 단일 공유         | 부모 + 자식 isolation        |
| Subagent       | 없음             | `run_subagent()` 함수        |
| 반환 값         | 해당 없음         | 요약 텍스트만                 |

## 실행해 보기

```sh
cd learn-claude-code
python agents/s04_subagent.py
```

1. `Use a subtask to find what testing framework this project uses`
2. `Delegate: read all .py files and summarize what each one does`
3. `Use a task to create a new module, then verify it from here`
