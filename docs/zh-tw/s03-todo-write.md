# s03: TodoWrite (待辦寫入)

`s01 > s02 > [ s03 ] s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"沒有計劃的 agent 走哪算哪"* -- 先列步驟再動手, 完成率翻倍。
>
> **Harness 層**: 規劃 -- 讓模型不偏航, 但不替它畫航線。

## 問題

多步任務中, 模型會丟失進度 -- 重複做過的事、跳步、跑偏。對話越長越嚴重: 工具結果不斷填滿上下文, 系統提示的影響力逐漸被稀釋。一個 10 步重構可能做完 1-3 步就開始即興發揮, 因為 4-10 步已經被擠出注意力了。

## 解決方案

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
              +-----------	------------+
                          |
              if rounds_since_todo >= 3:
                inject <reminder> into tool_result
```

## 工作原理

1. TodoManager 儲存帶狀態的專案。同一時間只允許一個 `in_progress`。

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

2. `todo` 工具和其他工具一樣加入 dispatch map。

```python
TOOL_HANDLERS = {
    # ...base tools...
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

3. nag reminder: 模型連續 3 輪以上不呼叫 `todo` 時注入提醒。

```python
if rounds_since_todo >= 3 and messages:
    last = messages[-1]
    if last["role"] == "user" and isinstance(last.get("content"), list):
        last["content"].insert(0, {
            "type": "text",
            "text": "<reminder>Update your todos.</reminder>",
        })
```

"同時只能有一個 in_progress" 強制順序聚焦。nag reminder 製造問責壓力 -- 你不更新計劃, 系統就追著你問。

## 相對 s02 的變更

| 元件           | 之前 (s02)       | 之後 (s03)                     |
|----------------|------------------|--------------------------------|
| Tools          | 4                | 5 (+todo)                      |
| 規劃           | 無               | 帶狀態的 TodoManager           |
| Nag 注入       | 無               | 3 輪後注入 `<reminder>`        |
| Agent loop     | 簡單分發         | + rounds_since_todo 計數器     |

## 試一試

```sh
cd learn-claude-code
python agents/s03_todo_write.py
```

試試這些 prompt (英文 prompt 對 LLM 效果更好, 也可以用中文):

1. `Refactor the file hello.py: add type hints, docstrings, and a main guard`
2. `Create a Python package with __init__.py, utils.py, and tests/test_utils.py`
3. `Review all Python files and fix any style issues`
