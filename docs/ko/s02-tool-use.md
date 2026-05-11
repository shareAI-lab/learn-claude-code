# s02: 도구 사용 (Tool Use)

`s01 > [ s02 ] s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Adding a tool means adding one handler"* -- 도구마다 핸들러 하나, loop는 그대로 유지되고 새 tool은 dispatch map (디스패치 맵 — 이름→핸들러 매핑 테이블)에 등록됩니다.
>
> **Harness layer**: Tool dispatch -- 모델이 닿을 수 있는 영역을 넓힙니다.

## 문제

`bash` 하나만 있으면 agent는 모든 작업을 shell로 처리해야 합니다. `cat`은 예측할 수 없는 방식으로 잘리고, `sed`는 특수 문자에서 실패하며, 모든 bash 호출은 통제되지 않은 보안 표면이 됩니다. `read_file`이나 `write_file` 같은 전용 tool을 두면 tool 레벨에서 경로 샌드박싱을 강제할 수 있습니다.

핵심 통찰은 다음과 같습니다. tool을 추가해도 loop는 바뀌지 않습니다.

## 해결책

```
+--------+      +-------+      +------------------+
|  User  | ---> |  LLM  | ---> | Tool Dispatch    |
| prompt |      |       |      | {                |
+--------+      +---+---+      |   bash: run_bash |
                    ^           |   read: run_read |
                    |           |   write: run_wr  |
                    +-----------+   edit: run_edit |
                    tool_result | }                |
                                +------------------+

The dispatch map is a dict: {tool_name: handler_function}.
One lookup replaces any if/elif chain.
```

## 동작 원리

1. 각 tool에는 handler 함수가 하나씩 있습니다. 경로 샌드박싱이 워크스페이스 이탈을 막아 줍니다.

```python
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_read(path: str, limit: int = None) -> str:
    text = safe_path(path).read_text()
    lines = text.splitlines()
    if limit and limit < len(lines):
        lines = lines[:limit]
    return "\n".join(lines)[:50000]
```

2. dispatch map이 tool 이름과 handler를 연결해 줍니다.

```python
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

3. loop 안에서는 이름으로 handler를 조회합니다. loop 본문 자체는 s01과 동일합니다.

```python
for block in response.content:
    if block.type == "tool_use":
        handler = TOOL_HANDLERS.get(block.name)
        output = handler(**block.input) if handler \
            else f"Unknown tool: {block.name}"
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
```

tool을 추가한다는 것은 = handler 하나 추가 + 스키마 항목 하나 추가입니다. loop는 절대 변하지 않습니다.

## s01에서 무엇이 바뀌었나

| 구성 요소       | 이전 (s01)            | 이후 (s02)                        |
|----------------|-----------------------|------------------------------------|
| Tool 개수      | 1 (bash 단독)         | 4 (bash, read, write, edit)        |
| Dispatch       | bash 호출 하드코딩    | `TOOL_HANDLERS` dict               |
| 경로 안전성    | 없음                  | `safe_path()` 샌드박스             |
| Agent loop     | 변경 없음             | 변경 없음                          |

## 직접 해보기

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

1. `Read the file requirements.txt`
2. `Create a file called greet.py with a greet(name) function`
3. `Edit greet.py to add a docstring to the function`
4. `Read greet.py to verify the edit worked`
