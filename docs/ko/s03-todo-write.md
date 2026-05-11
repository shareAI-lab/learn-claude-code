# s03: TodoWrite

`s01 > s02 > [ s03 ] s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"An agent without a plan drifts"* -- 행동하기 전에 계획하라, 단계를 먼저 나열한 다음 실행합니다.
>
> **Harness layer**: 계획 (Planning) -- 경로를 일일이 스크립트화하지 않고도 모델이 정해진 코스를 벗어나지 않게 합니다.

## 문제

여러 단계로 이어지는 작업에서는 모델이 흐름을 놓치기 쉽습니다. 같은 작업을 반복하거나, 단계를 건너뛰거나, 방향을 잃고 헤매기도 합니다. 대화가 길어질수록 이 문제는 더 심해집니다 -- tool result가 context를 채우면서 system prompt의 영향력이 점점 흐려지기 때문입니다. 10단계짜리 리팩토링이라면 1~3단계까지는 완료해 놓고, 그 이후로는 4~10단계를 잊어버려 즉흥적으로 일을 처리하기 시작할 수도 있습니다.

## 해결책

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> | Tools   |
| prompt |      |       |      | + todo  |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                          |
              +-----------+-----------+
              | TodoManager state     |
              | [ ] task A            |
              | [>] task B  <- doing  |
              | [x] task C            |
              +-----------------------+
                          |
              if rounds_since_todo >= 3:
                inject <reminder> into tool_result
```

## 동작 원리

1. TodoManager는 항목을 상태와 함께 저장합니다. 한 번에 단 하나의 항목만 `in_progress` 상태일 수 있습니다.

```python
class TodoManager:
    def update(self, items: list) -> str:
        validated, in_progress_count = [], 0
        for item in items:
            status = item.get("status", "pending")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item["id"], "text": item["text"],
                              "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress")
        self.items = validated
        return self.render()
```

2. `todo` tool도 다른 tool과 똑같이 dispatch map에 등록됩니다.

```python
TOOL_HANDLERS = {
    # ...base tools...
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

3. nag reminder (자꾸 알려주는 리마인더)는 모델이 `todo`를 호출하지 않고 3 라운드 이상 지나가면 슬쩍 찔러 줍니다.

```python
if rounds_since_todo >= 3 and messages:
    last = messages[-1]
    if last["role"] == "user" and isinstance(last.get("content"), list):
        last["content"].insert(0, {
            "type": "text",
            "text": "<reminder>Update your todos.</reminder>",
        })
```

"한 번에 in_progress는 하나뿐"이라는 제약은 순차적 집중을 강제합니다. nag reminder는 책임감을 만들어 줍니다.

## s02에서 무엇이 바뀌었나

| 구성 요소        | 이전 (s02)        | 이후 (s03)                          |
|-----------------|-------------------|--------------------------------------|
| Tool 개수       | 4                 | 5 (+todo)                            |
| 계획            | 없음              | 상태를 가진 TodoManager              |
| Nag 주입        | 없음              | 3 라운드 후 `<reminder>` 주입        |
| Agent loop      | 단순 dispatch     | + rounds_since_todo 카운터           |

## 직접 해보기

```sh
cd learn-claude-code
python agents/s03_todo_write.py
```

1. `Refactor the file hello.py: add type hints, docstrings, and a main guard`
2. `Create a Python package with __init__.py, utils.py, and tests/test_utils.py`
3. `Review all Python files and fix any style issues`
