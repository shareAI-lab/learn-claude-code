# s00c: Query Transition Model (查詢轉移模型)

> 這篇橋接文件專門解決一個問題：
>
> **為什麼一個只會 `continue` 的 agent，不足以支撐完整系統，而必須顯式知道“為什麼繼續到下一輪”？**

## 這一篇為什麼要存在

主線裡：

- `s01` 先教你最小迴圈
- `s06` 開始教上下文壓縮
- `s11` 開始教錯誤恢復

這些都對。  
但如果你只分別學這幾章，腦子裡很容易還是停留在一種過於粗糙的理解：

> “反正 `continue` 了就繼續唄。”

這在最小 demo 裡能跑。  
但當系統開始長出恢復、壓縮和外部控制以後，這樣理解會很快失靈。

因為系統繼續下一輪的原因其實很多，而且這些原因不是一回事：

- 工具剛執行完，要把結果喂回模型
- 輸出被截斷了，要續寫
- 上下文剛壓縮完，要重試
- 運輸層剛超時了，要退避後重試
- stop hook 要求當前 turn 先不要結束
- token budget 還允許繼續推進

如果你不把這些“繼續原因”從一開始拆開，後面會出現三個大問題：

- 日誌看不清
- 測試不好寫
- 教學心智會越來越模糊

## 先解釋幾個名詞

### 什麼叫 transition

這裡的 `transition`，你可以先把它理解成：

> 上一輪為什麼轉移到了下一輪。

它不是“訊息內容”，而是“流程原因”。

### 什麼叫 continuation

continuation 就是：

> 這條 query 當前還沒有結束，要繼續推進。

但 continuation 不止一種。

### 什麼叫 query boundary

query boundary 就是一輪和下一輪之間的邊界。

每次跨過這個邊界，系統最好都知道：

- 這次為什麼繼續
- 這次繼續前有沒有修改狀態
- 這次繼續後應該怎麼讀主迴圈

## 最小心智模型

先不要把 query 想成一條線。

更接近真實情況的理解是：

```text
一條 query
  = 一組“繼續原因”串起來的狀態轉移
```

例如：

```text
使用者輸入
  ->
模型產生 tool_use
  ->
工具執行完
  ->
tool_result_continuation
  ->
模型輸出過長
  ->
max_tokens_recovery
  ->
壓縮後繼續
  ->
compact_retry
  ->
最終結束
```

這樣看，你會更容易理解：

**系統不是單純在 while loop 裡轉圈，而是在一串顯式的轉移原因裡推進。**

## 關鍵資料結構

### 1. QueryState 裡的 `transition`

最小版建議就把這類欄位顯式放進狀態裡：

```python
state = {
    "messages": [...],
    "turn_count": 3,
    "has_attempted_compact": False,
    "continuation_count": 1,
    "transition": None,
}
```

這裡的 `transition` 不是可有可無。

它的意義是：

- 當前這輪為什麼會出現
- 下一輪日誌應該怎麼解釋
- 測試時應該斷言哪條路徑被走到

### 2. TransitionReason

教學版最小可以先這樣分：

```python
TRANSITIONS = (
    "tool_result_continuation",
    "max_tokens_recovery",
    "compact_retry",
    "transport_retry",
    "stop_hook_continuation",
    "budget_continuation",
)
```

這幾種原因的本質不一樣：

- `tool_result_continuation`
  是正常主線繼續
- `max_tokens_recovery`
  是輸出被截斷後的恢復繼續
- `compact_retry`
  是上下文處理後的恢復繼續
- `transport_retry`
  是基礎設施抖動後的恢復繼續
- `stop_hook_continuation`
  是外部控制邏輯阻止本輪結束
- `budget_continuation`
  是系統主動利用預算繼續推進

### 3. Continuation Budget

更完整的 query 狀態不只會說“繼續”，還會限制：

- 最多續寫幾次
- 最多壓縮後重試幾次
- 某類恢復是不是已經嘗試過

例如：

```python
state = {
    "max_output_tokens_recovery_count": 2,
    "has_attempted_reactive_compact": True,
}
```

這些欄位的本質都是：

> continuation 不是無限制的。

## 最小實現

### 第一步：把 continue site 顯式化

很多初學者寫主迴圈時，所有繼續邏輯都長這樣：

```python
continue
```

教學版應該往前走一步：

```python
state["transition"] = "tool_result_continuation"
continue
```

### 第二步：不同繼續原因，配不同狀態修改

```python
if response.stop_reason == "tool_use":
    state["messages"] = append_tool_results(...)
    state["turn_count"] += 1
    state["transition"] = "tool_result_continuation"
    continue

if response.stop_reason == "max_tokens":
    state["messages"].append({
        "role": "user",
        "content": CONTINUE_MESSAGE,
    })
    state["max_output_tokens_recovery_count"] += 1
    state["transition"] = "max_tokens_recovery"
    continue
```

重點不是“多寫一行”。

重點是：

**每次繼續之前，你都要知道自己做了什麼狀態更新，以及為什麼繼續。**

### 第三步：把恢復繼續和正常繼續分開

```python
if should_retry_transport(error):
    time.sleep(backoff(...))
    state["transition"] = "transport_retry"
    continue

if should_recompact(error):
    state["messages"] = compact_messages(state["messages"])
    state["transition"] = "compact_retry"
    continue
```

這時候你就開始得到一條非常清楚的控制鏈：

```text
繼續
  不再是一個動作
  而是一類帶原因的轉移
```

## 一張真正應該建立的圖

```text
query loop
  |
  +-- tool executed --------------------> transition = tool_result_continuation
  |
  +-- output truncated -----------------> transition = max_tokens_recovery
  |
  +-- compact just happened -----------> transition = compact_retry
  |
  +-- network / transport retry -------> transition = transport_retry
  |
  +-- stop hook blocked termination ---> transition = stop_hook_continuation
  |
  +-- budget says keep going ----------> transition = budget_continuation
```

## 它和逆向倉庫主脈絡為什麼對得上

如果你去看更完整系統的查詢入口，會發現它真正難的地方從來不是：

- 再調一次模型

而是：

- 什麼時候該繼續
- 繼續前改哪份狀態
- 繼續屬於哪一種路徑

所以這篇橋接文件講的，不是額外裝飾，而是完整 query engine 的主骨架之一。

## 它和主線章節怎麼接

- `s01` 讓你先把 loop 跑起來
- `s06` 讓你知道為什麼上下文管理會介入繼續路徑
- `s11` 讓你知道為什麼恢復路徑不是一種
- 這篇則把“繼續原因”統一抬成顯式狀態

所以你可以把它理解成：

> 給前後幾章之間補上一條“為什麼繼續”的統一主線。

## 初學者最容易犯的錯

### 1. 只有 `continue`，沒有 `transition`

這樣日誌和測試都會越來越難看。

### 2. 把所有繼續都當成一種

這樣會把：

- 正常主線繼續
- 錯誤恢復繼續
- 壓縮後重試

全部混成一鍋。

### 3. 沒有 continuation budget

沒有預算，系統就會在某些壞路徑裡無限試下去。

### 4. 把 `transition` 寫進訊息文字，而不是流程狀態

訊息是給模型看的。  
`transition` 是給系統自己看的。

### 5. 壓縮、恢復、hook 都發生了，卻沒有統一的查詢狀態

這會導致控制邏輯散落在很多區域性變數裡，越長越亂。

## 教學邊界

這篇最重要的，不是一次列舉完所有 transition 名字，而是先讓你守住三件事：

- `continue` 最好總能對應一個顯式的 `transition reason`
- 正常繼續、恢復繼續、壓縮後重試，不應該被混成同一種路徑
- continuation 需要預算和狀態，而不是無限重來

只要這三點成立，你就已經能把 `s01 / s06 / s11` 真正串成一條完整主線。  
更細的 transition taxonomy、預算策略和日誌分類，可以放到你把最小 query 狀態機寫穩以後再補。

## 讀完這一篇你應該能說清楚

至少能完整說出這句話：

> 一條 query 不是簡單 while loop，而是一串顯式 continuation reason 驅動的狀態轉移。

如果這句話你已經能穩定說清，那麼你再回頭看 `s11`、`s19`，心智會順很多。
