# s06: 컨텍스트 압축 (Context Compact)

`s01 > s02 > s03 > s04 > s05 > [ s06 ] | s07 > s08 > s09 > s10 > s11 > s12`

> *"context는 결국 가득 찬다. 공간을 확보할 방법이 필요하다"* -- 무한 세션을 위한 3계층 압축 전략입니다.
>
> **Harness 계층**: compaction (compaction — 컨텍스트 압축) -- 무한 세션을 위한 깨끗한 메모리 관리.

## 문제

context window는 유한합니다. 1000줄짜리 파일 하나에 대한 단일 `read_file` 호출은 약 4000 token을 소모합니다. 30개의 파일을 읽고 20개의 bash 명령을 실행하고 나면 100,000 token 이상에 도달합니다. 압축 없이는 agent가 대규모 코드베이스에서 작업할 수 없습니다.

## 해결책

세 단계로, 점점 더 공격적으로 동작합니다:

```
Every turn:
+------------------+
| Tool call result |
+------------------+
        |
        v
[Layer 1: micro_compact]        (silent, every turn)
  Replace tool_result > 3 turns old
  with "[Previous: used {tool_name}]"
        |
        v
[Check: tokens > 50000?]
   |               |
   no              yes
   |               |
   v               v
continue    [Layer 2: auto_compact]
              Save transcript to .transcripts/
              LLM summarizes conversation.
              Replace all messages with [summary].
                    |
                    v
            [Layer 3: compact tool]
              Model calls compact explicitly.
              Same summarization as auto_compact.
```

## 동작 원리

1. **Layer 1 -- micro_compact**: 매 LLM 호출 직전에, 오래된 tool result를 placeholder로 교체합니다.

```python
def micro_compact(messages: list) -> list:
    tool_results = []
    for i, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            for j, part in enumerate(msg["content"]):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    tool_results.append((i, j, part))
    if len(tool_results) <= KEEP_RECENT:
        return messages
    for _, _, part in tool_results[:-KEEP_RECENT]:
        if len(part.get("content", "")) > 100:
            part["content"] = f"[Previous: used {tool_name}]"
    return messages
```

2. **Layer 2 -- auto_compact**: token이 임계값을 초과하면, 전체 transcript를 디스크에 저장한 뒤 LLM에게 요약을 요청합니다.

```python
def auto_compact(messages: list) -> list:
    # Save transcript for recovery
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    # LLM summarizes
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this conversation for continuity..."
            + json.dumps(messages, default=str)[:80000]}],
        max_tokens=2000,
    )
    return [
        {"role": "user", "content": f"[Compressed]\n\n{response.content[0].text}"},
    ]
```

3. **Layer 3 -- 수동 compact**: `compact` 도구가 동일한 요약을 필요할 때 트리거합니다.

4. 루프는 세 계층을 모두 통합합니다:

```python
def agent_loop(messages: list):
    while True:
        micro_compact(messages)                        # Layer 1
        if estimate_tokens(messages) > THRESHOLD:
            messages[:] = auto_compact(messages)       # Layer 2
        response = client.messages.create(...)
        # ... tool execution ...
        if manual_compact:
            messages[:] = auto_compact(messages)       # Layer 3
```

Transcript는 전체 history를 디스크에 보존합니다. 실제로 사라지는 것은 없습니다 -- 단지 활성 context 밖으로 옮겨지는 것뿐입니다. 이는 archival (archival — 오래된 메시지를 외부에 보관하는 방식)의 일종으로 볼 수 있습니다.

## s05에서 달라진 점

| 구성 요소         | 이전 (s05)        | 이후 (s06)                    |
|------------------|------------------|-------------------------------|
| 도구              | 5개              | 5개 (기본 + compact)            |
| Context 관리      | 없음             | 3계층 압축                      |
| Micro-compact    | 없음             | 오래된 결과 -> placeholder      |
| Auto-compact     | 없음             | Token 임계값 트리거             |
| Transcripts      | 없음             | .transcripts/ 에 저장           |

## 실행해 보기

```sh
cd learn-claude-code
python agents/s06_context_compact.py
```

1. `Read every Python file in the agents/ directory one by one` (micro-compact가 오래된 결과를 교체하는 모습을 관찰)
2. `Keep reading files until compression triggers automatically`
3. `Use the compact tool to manually compress the conversation`
