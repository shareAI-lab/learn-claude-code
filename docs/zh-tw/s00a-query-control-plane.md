# s00a: Query Control Plane (查詢控制平面)

> 這不是新的主線章節，而是一份橋接文件。  
> 它用來回答一個問題：
>
> **為什麼一個結構更完整的 agent，不會只靠 `messages[]` 和一個 `while True` 就夠了？**

## 這一篇為什麼要存在

主線裡的 `s01` 會先教你做出一個最小可執行迴圈：

```text
使用者輸入
  ->
模型回覆
  ->
如果要調工具就執行
  ->
把結果喂回去
  ->
繼續下一輪
```

這條主線是對的，而且必須先學這個。

但當系統開始長功能以後，真正支撐一個完整 harness 的，不再只是“迴圈”本身，而是：

**一層專門負責管理查詢過程的控制平面。**

這一層在真實系統裡通常會統一處理：

- 當前對話訊息
- 當前輪次
- 為什麼繼續下一輪
- 是否正在恢復錯誤
- 是否已經壓縮過上下文
- 是否需要切換輸出預算
- hook 是否暫時影響了結束條件

如果不把這層講出來，讀者雖然能做出一個能跑的 demo，但很難自己把系統推到接近 95%-99% 的完成度。

## 先解釋幾個名詞

### 什麼是 query

這裡的 `query` 不是“資料庫查詢”。

這裡說的 query，更接近：

> 系統為了完成使用者當前這一次請求，而執行的一整段主迴圈過程。

也就是說：

- 使用者說一句話
- 系統可能要經過很多輪模型呼叫和工具呼叫
- 最後才結束這一次請求

這整段過程，就可以看成一條 query。

### 什麼是控制平面

`控制平面` 這個詞第一次看會有點抽象。

它的意思其實很簡單：

> 不是直接做業務動作，而是負責協調、排程、決定流程怎麼往下走的一層。

在這裡：

- 模型回覆內容，算“業務內容”
- 工具執行結果，算“業務動作”
- 決定“要不要繼續下一輪、為什麼繼續、現在屬於哪種繼續”，這層就是控制平面

### 什麼是 transition

`transition` 可以翻成“轉移原因”。

它回答的是：

> 上一輪為什麼沒有結束，而是繼續下一輪了？

例如：

- 因為工具剛執行完
- 因為輸出被截斷，要續寫
- 因為剛做完壓縮，要重試
- 因為 hook 要求繼續
- 因為預算還允許繼續

## 最小心智模型

先把 query 控制平面想成 3 層：

```text
1. 輸入層
   - messages
   - system prompt
   - user/system context

2. 控制層
   - 當前狀態 state
   - 當前輪 turn
   - 當前繼續原因 transition
   - 恢復/壓縮/預算等標記

3. 執行層
   - 調模型
   - 執行工具
   - 寫回訊息
```

它的工作不是“替代主迴圈”，而是：

**讓主迴圈從一個小 demo，升級成一個能管理很多分支和狀態的系統。**

## 為什麼只靠 `messages[]` 不夠

很多初學者第一次實現 agent 時，會把所有狀態都堆進 `messages[]`。

這在最小 demo 裡沒問題。

但一旦系統長出下面這些能力，就不夠了：

- 你要知道自己是不是已經做過一次 reactive compact
- 你要知道輸出被截斷已經續寫了幾次
- 你要知道這次繼續是因為工具，還是因為錯誤恢復
- 你要知道當前輪是否啟用了特殊輸出預算

這些資訊不是“對話內容”，而是“流程控制狀態”。

所以它們不該都硬塞進 `messages[]` 裡。

## 關鍵資料結構

### 1. QueryParams

這是進入 query 引擎時的外部輸入。

最小形狀可以這樣理解：

```python
params = {
    "messages": [...],
    "system_prompt": "...",
    "user_context": {...},
    "system_context": {...},
    "tool_use_context": {...},
    "fallback_model": None,
    "max_output_tokens_override": None,
    "max_turns": None,
}
```

它的作用是：

- 帶進來這次查詢一開始已知的輸入
- 這些值大多不在每輪裡隨便亂改

### 2. QueryState

這才是跨迭代真正會變化的部分。

最小教學版建議你把它顯式做成一個結構：

```python
state = {
    "messages": [...],
    "tool_use_context": {...},
    "continuation_count": 0,
    "has_attempted_compact": False,
    "max_output_tokens_override": None,
    "stop_hook_active": False,
    "turn_count": 1,
    "transition": None,
}
```

它的價值在於：

- 把“會變的流程狀態”集中放在一起
- 讓每個 continue site 修改的是同一份 state，而不是散落在很多區域性變數裡

### 3. TransitionReason

建議你單獨定義一組繼續原因：

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

這不是為了炫技。

它的作用很實在：

- 日誌更清楚
- 除錯更清楚
- 測試更清楚
- 教學更清楚

## 最小實現

### 第一步：把外部輸入和內部狀態分開

```python
def query(params):
    state = {
        "messages": params["messages"],
        "tool_use_context": params["tool_use_context"],
        "continuation_count": 0,
        "has_attempted_compact": False,
        "max_output_tokens_override": params.get("max_output_tokens_override"),
        "turn_count": 1,
        "transition": None,
    }
```

### 第二步：每一輪先讀 state，再決定如何執行

```python
while True:
    messages = state["messages"]
    transition = state["transition"]
    turn_count = state["turn_count"]

    response = call_model(...)
    ...
```

### 第三步：所有“繼續下一輪”的地方都寫回 state

```python
if response.stop_reason == "tool_use":
    state["messages"] = append_tool_results(...)
    state["transition"] = "tool_result_continuation"
    state["turn_count"] += 1
    continue

if response.stop_reason == "max_tokens":
    state["messages"].append({"role": "user", "content": CONTINUE_MESSAGE})
    state["continuation_count"] += 1
    state["transition"] = "max_tokens_recovery"
    continue
```

這一點非常關鍵。

**不要只做 `continue`，要知道自己為什麼 continue。**

## 一張真正清楚的心智圖

```text
params
  |
  v
init state
  |
  v
query loop
  |
  +-- normal assistant end --------------> terminal
  |
  +-- tool_use --------------------------> write tool_result -> transition=tool_result_continuation
  |
  +-- max_tokens ------------------------> inject continue -> transition=max_tokens_recovery
  |
  +-- prompt too long -------------------> compact -> transition=compact_retry
  |
  +-- transport error -------------------> backoff -> transition=transport_retry
  |
  +-- stop hook asks to continue --------> transition=stop_hook_continuation
```

## 它和 `s01`、`s11` 的關係

- `s01` 負責建立“最小主迴圈”
- `s11` 負責建立“錯誤恢復分支”
- 這一篇負責把兩者再往上抽象一層，解釋為什麼一個更完整的系統會出現一個 query control plane

所以這篇不是替代主線，而是把主線補完整。

## 初學者最容易犯的錯

### 1. 把所有控制狀態都塞進訊息裡

這樣日誌和除錯都會很難看，也會讓訊息層和控制層混在一起。

### 2. `continue` 了，但沒有記錄為什麼繼續

短期看起來沒問題，系統一複雜就會變成黑盒。

### 3. 每個分支都直接改很多區域性變數

這樣後面你很難看出“哪些狀態是跨輪共享的”。

### 4. 把 query loop 講成“只是一個 while True”

這對最小 demo 是真話，對一個正在長出控制面的 harness 就不是完整真話了。

## 教學邊界

這篇最重要的，不是把所有控制狀態一次列滿，而是先讓你守住三件事：

- query loop 不只是 `while True`，而是一條帶著共享狀態往前推進的控制面
- 每次 `continue` 都應該有明確原因，而不是黑盒跳轉
- 訊息層、工具回寫、壓縮恢復、重試恢復，最終都要回到同一份 query 狀態上

更細的 `transition taxonomy`、預算跟蹤、prefetch 等擴充套件，可以放到你把這條最小控制面真正手搓穩定以後再補。

## 一句話記住

**更完整的 query loop 不只是“迴圈”，而是“拿著一份跨輪狀態不斷推進的查詢控制平面”。**
