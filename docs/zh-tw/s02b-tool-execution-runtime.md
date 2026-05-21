# s02b: Tool Execution Runtime (工具執行執行時)

> 這篇橋接文件解決的不是“工具怎麼註冊”，而是：
>
> **當模型一口氣發出多個工具呼叫時，系統到底按什麼規則執行、併發、回寫、合併上下文？**

## 這一篇為什麼要存在

`s02` 先教你：

- 工具 schema
- dispatch map
- tool_result 迴流

這完全正確。  
因為工具呼叫先得成立，後面才談得上覆雜度。

但系統一旦長大，真正棘手的問題會變成下面這些：

- 多個工具能不能並行執行
- 哪些工具必須序列
- 工具執行過程中要不要先發進度訊息
- 併發工具的結果應該按完成順序回寫，還是按原始出現順序回寫
- 工具執行會不會改共享上下文
- 多個併發工具如果都要改上下文，最後怎麼合併

這些問題已經不是“工具註冊”能解釋的了。

它們屬於更深一層：

**工具執行執行時。**

## 先解釋幾個名詞

### 什麼叫工具執行執行時

這裡的執行時，不是指程式語言 runtime。

這裡說的是：

> 當工具真正開始執行時，系統用什麼規則去排程、併發、跟蹤和回寫這些工具。

### 什麼叫 concurrency safe

你可以先把它理解成：

> 這個工具能不能和別的同類工具同時跑，而不會把共享狀態搞亂。

例如很多隻讀工具常常是 concurrency safe：

- `read_file`
- 某些搜尋工具
- 某些純查詢類 MCP 工具

而很多寫操作不是：

- `write_file`
- `edit_file`
- 某些會改全域性狀態的工具

### 什麼叫 progress message

有些工具跑得慢，不適合一直靜默。

progress message 就是：

> 工具還沒結束，但系統先把“它正在做什麼”告訴上層。

### 什麼叫 context modifier

有些工具執行完不只是返回結果，還會修改共享環境。

例如：

- 更新通知佇列
- 更新 app state
- 更新“哪些工具正在執行”

這種“對共享上下文的修改動作”，就可以理解成 context modifier。

## 最小心智模型

先不要把工具執行想成：

```text
tool_use -> handler -> result
```

更接近真實可擴充套件系統的理解是：

```text
tool_use blocks
  ->
按執行安全性分批
  ->
每批決定序列還是並行
  ->
執行過程中可能產出 progress
  ->
最終按穩定順序回寫結果
  ->
必要時再合併 context modifiers
```

這裡最關鍵的升級點有兩個：

- 併發不是預設全開
- 上下文修改不是誰先跑完誰先直接亂寫

## 關鍵資料結構

### 1. ToolExecutionBatch

教學版最小可以先用這樣一個概念：

```python
batch = {
    "is_concurrency_safe": True,
    "blocks": [tool_use_1, tool_use_2, tool_use_3],
}
```

它的意義是：

- 不是每個工具都單獨處理
- 系統會先把工具呼叫按可否併發分成一批一批

### 2. TrackedTool

如果你準備把執行層做得更穩、更清楚，建議顯式跟蹤每個工具：

```python
tracked_tool = {
    "id": "toolu_01",
    "name": "read_file",
    "status": "queued",   # queued / executing / completed / yielded
    "is_concurrency_safe": True,
    "pending_progress": [],
    "results": [],
    "context_modifiers": [],
}
```

這類結構的價值很大。

因為系統終於開始能回答：

- 哪些工具還在排隊
- 哪些已經開始
- 哪些已經完成
- 哪些已經先吐出了中間進度

### 3. MessageUpdate

工具執行過程中，不一定只有最終結果。

最小可以先理解成：

```python
update = {
    "message": maybe_message,
    "new_context": current_context,
}
```

更完整的執行層裡，一個工具執行執行時往往會產出兩類更新：

- 要立刻往上游發的訊息更新
- 隻影響內部共享環境的 context 更新

### 4. Queued Context Modifiers

這是最容易被忽略、但很關鍵的一層。

在併發工具批次裡，更穩的策略不是“誰先完成誰先改 context”，而是：

> 先把 context modifier 暫存起來，最後按原始工具順序統一合併。

最小理解方式：

```python
queued_context_modifiers = {
    "toolu_01": [modify_ctx_a],
    "toolu_02": [modify_ctx_b],
}
```

## 最小實現

### 第一步：先分清哪些工具能併發

```python
def is_concurrency_safe(tool_name: str, tool_input: dict) -> bool:
    return tool_name in {"read_file", "search_files"}
```

### 第二步：先分批，再執行

```python
batches = partition_tool_calls(tool_uses)

for batch in batches:
    if batch["is_concurrency_safe"]:
        run_concurrently(batch["blocks"])
    else:
        run_serially(batch["blocks"])
```

### 第三步：併發批次先吐進度，再收最終結果

```python
for update in run_concurrently(...):
    if update.get("message"):
        yield update["message"]
```

### 第四步：context modifier 不要亂序落地

```python
queued_modifiers = {}

for update in concurrent_updates:
    if update.get("context_modifier"):
        queued_modifiers[update["tool_id"]].append(update["context_modifier"])

for tool in original_batch_order:
    for modifier in queued_modifiers.get(tool["id"], []):
        context = modifier(context)
```

這一步是整篇裡最容易被低估，但其實最接近真實系統開始長出執行執行時的點之一。

## 一張真正應該建立的圖

```text
tool_use blocks
  |
  v
partition by concurrency safety
  |
  +-- read-only / safe batch -----> concurrent execution
  |                                   |
  |                                   +-- progress updates
  |                                   +-- final results
  |                                   +-- queued context modifiers
  |
  +-- exclusive batch ------------> serial execution
                                      |
                                      +-- direct result + direct context update
```

## 為什麼這層比“dispatch map”更接近真實系統主脈絡

最小 demo 裡：

```python
handlers[tool_name](tool_input)
```

就夠了。

但在更完整系統裡，真正複雜的不是“找到 handler”。

真正複雜的是：

- 多工具之間如何共存
- 哪些能併發
- 併發時如何保證回寫順序穩定
- 併發時如何避免共享 context 被搶寫
- 工具報錯時是否中止其他工具

所以這層講的不是邊角最佳化，而是：

> 工具系統從“可呼叫”升級到“可排程”的關鍵一步。

## 它和前後章節怎麼接

- `s02` 先教你工具為什麼能被呼叫
- [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) 講工具為什麼會長成統一控制面
- 這篇繼續講，工具真的開始執行以後，系統如何排程它們
- `s07`、`s13`、`s19` 往後都還會繼續用到這層心智

尤其是：

- 許可權系統會影響工具能不能執行
- 後臺任務會影響工具是否立即結束
- MCP / plugin 會讓工具來源更多、執行形態更復雜

## 初學者最容易犯的錯

### 1. 看到多個工具呼叫，就預設全部併發

這樣很容易把共享狀態搞亂。

### 2. 只按完成順序回寫結果

如果你完全按“誰先跑完誰先寫”，主迴圈看到的順序會越來越不穩定。

### 3. 併發工具直接同時改共享 context

這會製造很多很難解釋的隱性狀態問題。

### 4. 認為 progress message 是“可有可無的 UI 裝飾”

它其實會影響：

- 上層何時知道工具還活著
- 長工具呼叫期間使用者是否困惑
- streaming 執行體驗是否穩定

### 5. 只講工具 schema，不講工具排程

這樣讀者最後只會“註冊工具”，卻不理解真實 agent 為什麼還要長出工具執行執行時。

## 教學邊界

這篇最重要的，不是把工具排程層一次講成一個龐大 runtime，而是先讓讀者守住三件事：

- 工具呼叫要先分批，而不是預設看到多個 `tool_use` 就全部併發
- 併發執行和穩定回寫是兩件事，不應該混成一個動作
- 共享 context 的修改最好先排隊，再按穩定順序統一合併

只要這三條邊界已經清楚，後面的許可權、後臺任務和 MCP 接入就都有地方掛。  
更細的佇列模型、取消策略、流式輸出協議，都可以放到你把這條最小執行時自己實作出來以後再補。

## 讀完這一篇你應該能說清楚

至少能完整說出這句話：

> 工具系統不只是 `tool_name -> handler`，它還需要一層執行執行時來決定哪些工具併發、哪些序列、結果如何回寫、共享上下文如何穩定合併。

如果這句話你已經能穩定說清，那麼你對 agent 工具層的理解，就已經比“會註冊幾個工具”深一大層了。
