# s01: 에이전트 루프 (Agent Loop)

`[ s01 ] s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"One loop & Bash is all you need"* -- tool 하나 + loop 하나 = agent.
>
> **Harness layer**: 루프 -- 모델이 실세계와 처음으로 연결되는 지점.

## 문제

언어 모델은 코드에 대해 추론할 수는 있지만 실세계를 직접 *만질* 수는 없습니다 -- 파일을 읽거나, 테스트를 실행하거나, 에러를 확인할 수 없죠. loop가 없으면 매번 tool call의 결과를 사람이 직접 복사해서 다시 붙여 넣어야 합니다. 사람이 곧 loop가 되는 셈입니다.

## 해결책

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> |  Tool   |
| prompt |      |       |      | execute |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                    (loop until stop_reason != "tool_use")
```

단 하나의 종료 조건이 전체 흐름을 제어합니다. loop는 모델이 더 이상 tool을 호출하지 않을 때까지 계속됩니다.

## 동작 원리

1. 사용자 prompt가 첫 번째 message가 됩니다.

```python
messages.append({"role": "user", "content": query})
```

2. messages와 tool 정의를 LLM에 전송합니다.

```python
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

3. 어시스턴트 응답을 추가합니다. `stop_reason`을 확인 -- 모델이 tool을 호출하지 않았다면 종료입니다.

```python
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
```

4. 각 tool call을 실행하고, 결과를 모아 user message로 추가합니다. 그리고 2단계로 돌아갑니다.

```python
results = []
for block in response.content:
    if block.type == "tool_use":
        output = run_bash(block.input["command"])
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
messages.append({"role": "user", "content": results})
```

하나의 함수로 묶으면 다음과 같습니다.

```python
def agent_loop(query):
    messages = [{"role": "user", "content": query}]
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_bash(block.input["command"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

30줄도 안 되는 코드가 agent의 전부입니다. 이 강의의 나머지 내용은 모두 이 위에 한 겹씩 쌓이는 것일 뿐 -- loop 자체는 바뀌지 않습니다.

## 무엇이 바뀌었나

| 구성 요소     | 이전       | 이후                             |
|---------------|------------|----------------------------------|
| Agent loop    | (없음)     | `while True` + stop_reason       |
| Tool          | (없음)     | `bash` (단일 tool)               |
| Messages      | (없음)     | 누적되는 리스트                  |
| 제어 흐름     | (없음)     | `stop_reason != "tool_use"`      |

## 직접 해보기

```sh
cd learn-claude-code
python agents/s01_agent_loop.py
```

1. `Create a file called hello.py that prints "Hello, World!"`
2. `List all Python files in this directory`
3. `What is the current git branch?`
4. `Create a directory called test_output and write 3 files in it`
