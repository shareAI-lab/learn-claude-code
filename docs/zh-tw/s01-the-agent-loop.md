# s01: The Agent Loop (智慧體迴圈)

`s00 > [ s01 ] > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *沒有迴圈，就沒有 agent。*  
> 這一章先教你做出一個最小但正確的迴圈，再告訴你為什麼後面還需要更完整的控制平面。

## 這一章要解決什麼問題

語言模型本身只會“生成下一段內容”。

它不會自己：

- 開啟檔案
- 執行命令
- 觀察報錯
- 把工具結果再接著用於下一步推理

如果沒有一層程式碼在中間反覆做這件事：

```text
發請求給模型
  -> 發現模型想調工具
  -> 真的去執行工具
  -> 把結果再喂回模型
  -> 繼續下一輪
```

那模型就只是一個“會說話的程式”，還不是一個“會幹活的 agent”。

所以這一章的核心目標只有一個：

**把“模型 + 工具”連線成一個能持續推進任務的主迴圈。**

## 先解釋幾個名詞

### 什麼是 loop

`loop` 就是迴圈。

這裡的意思不是“程式死迴圈”，而是：

> 只要任務還沒做完，系統就繼續重複同一套步驟。

### 什麼是 turn

`turn` 可以理解成“一輪”。

最小版本里，一輪通常包含：

1. 把當前訊息發給模型
2. 讀取模型回覆
3. 如果模型呼叫了工具，就執行工具
4. 把工具結果寫回訊息歷史

然後才進入下一輪。

### 什麼是 tool_result

`tool_result` 就是工具執行結果。

它不是隨便列印在終端上的日誌，而是：

> 要重新寫回對話歷史、讓模型下一輪真的能看見的結果塊。

### 什麼是 state

`state` 是“當前執行狀態”。

第一次看到這個詞時，你可以先把它理解成：

> 主迴圈繼續往下走時，需要一直帶著走的那份資料。

最小版本里，最重要的狀態就是：

- `messages`
- 當前是第幾輪
- 這一輪結束後為什麼還要繼續

## 最小心智模型

先把整個 agent 想成下面這條迴路：

```text
user message
   |
   v
LLM
   |
   +-- 普通回答 ----------> 結束
   |
   +-- tool_use ----------> 執行工具
                              |
                              v
                         tool_result
                              |
                              v
                         寫回 messages
                              |
                              v
                         下一輪繼續
```

這條圖裡最關鍵的，不是“有一個 while True”。

真正關鍵的是這句：

**工具結果必須重新進入訊息歷史，成為下一輪推理的輸入。**

如果少了這一步，模型就無法基於真實觀察繼續工作。

## 關鍵資料結構

### 1. Message

最小教學版裡，可以先把訊息理解成：

```python
{"role": "user", "content": "..."}
{"role": "assistant", "content": [...]}
```

這裡最重要的不是欄位名字，而是你要記住：

**訊息歷史不是聊天記錄展示層，而是模型下一輪要讀的工作上下文。**

### 2. Tool Result Block

當工具執行完後，你要把它包裝回訊息流：

```python
{
    "type": "tool_result",
    "tool_use_id": "...",
    "content": "...",
}
```

`tool_use_id` 的作用很簡單：

> 告訴模型“這條結果對應的是你剛才哪一次工具呼叫”。

### 3. LoopState

這章建議你不要只用一堆零散區域性變數。

最小也應該顯式收攏出一個迴圈狀態：

```python
state = {
    "messages": [...],
    "turn_count": 1,
    "transition_reason": None,
}
```

這裡的 `transition_reason` 先只需要理解成：

> 這一輪結束後，為什麼要繼續下一輪。

最小教學版只用一種原因就夠了：

```python
"tool_result"
```

也就是：

> 因為剛執行完工具，所以要繼續。

後面到了控制面更完整的章節裡，你會看到它逐漸長成更多種原因。  
如果你想先看完整一點的形狀，可以配合讀：

- [`s00a-query-control-plane.md`](./s00a-query-control-plane.md)

## 最小實現

### 第一步：準備初始訊息

使用者的請求先進入 `messages`：

```python
messages = [{"role": "user", "content": query}]
```

### 第二步：呼叫模型

把訊息歷史、system prompt 和工具定義一起發給模型：

```python
response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000,
)
```

### 第三步：追加 assistant 回覆

```python
messages.append({"role": "assistant", "content": response.content})
```

這一步非常重要。

很多初學者會只關心“最後有沒有答案”，忽略把 assistant 回覆本身寫回歷史。  
這樣一來，下一輪上下文就會斷掉。

### 第四步：如果模型呼叫了工具，就執行

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
```

### 第五步：把工具結果作為新訊息寫回去

```python
messages.append({"role": "user", "content": results})
```

然後下一輪重新發給模型。

### 組合成一個完整迴圈

```python
def agent_loop(state):
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=state["messages"],
            tools=TOOLS,
            max_tokens=8000,
        )

        state["messages"].append({
            "role": "assistant",
            "content": response.content,
        })

        if response.stop_reason != "tool_use":
            state["transition_reason"] = None
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_tool(block)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })

        state["messages"].append({"role": "user", "content": results})
        state["turn_count"] += 1
        state["transition_reason"] = "tool_result"
```

這就是最小 agent loop。

## 它如何接進整個系統

從現在開始，後面所有章節本質上都在做同一件事：

**往這個迴圈裡增加新的狀態、新的分支判斷和新的執行能力。**

例如：

- `s02` 往裡面接工具路由
- `s03` 往裡面接規劃狀態
- `s06` 往裡面接上下文壓縮
- `s07` 往裡面接許可權判斷
- `s11` 往裡面接錯誤恢復

所以請把這一章牢牢記成一句話：

> agent 的核心不是“模型很聰明”，而是“系統持續把現實結果喂回模型”。

## 為什麼教學版先接受 `stop_reason == "tool_use"` 這個簡化

這一章裡，我們先用：

```python
if response.stop_reason != "tool_use":
    return
```

這完全合理。

因為初學者在第一章真正要學會的，不是所有複雜邊界，而是：

1. assistant 回覆要寫回歷史
2. tool_result 要寫回歷史
3. 主迴圈要持續推進

但你也要知道，這只是第一層簡化。

更完整的系統不會只依賴 `stop_reason`，還會自己維護更明確的續行狀態。  
這是後面要補的，不是這一章一開始就要背下來的東西。

## 初學者最容易犯的錯

### 1. 把工具結果打印出來，但不寫回 `messages`

這樣模型下一輪根本看不到真實執行結果。

### 2. 只儲存使用者訊息，不儲存 assistant 訊息

這樣上下文會斷層，模型會越來越不像“接著剛才做”。

### 3. 不給工具結果繫結 `tool_use_id`

模型會分不清哪條結果對應哪次呼叫。

### 4. 一上來就把流式、併發、恢復、壓縮全塞進第一章

這會讓主線變得非常難學。

第一章最重要的是先把最小回路搭起來。

### 5. 以為 `messages` 只是聊天展示

不是。

在 agent 裡，`messages` 更像“下一輪工作輸入”。

## 教學邊界

這一章只需要先講透一件事：

**Agent 之所以從“會說”變成“會做”，是因為模型輸出能走到工具，工具結果又能回到下一輪模型輸入。**

所以教學倉庫在這裡要刻意停住：

- 不要一開始就拉進 streaming、retry、budget、recovery
- 不要一開始就混入許可權、Hook、任務系統
- 不要把第一章寫成整套系統所有後續機制的總圖

如果讀者已經能憑記憶寫出 `messages -> model -> tool_result -> next turn` 這條迴路，這一章就已經達標了。

## 一句話記住

**Agent Loop 的本質，是把“模型的動作意圖”變成“真實執行結果”，再把結果送回模型繼續推理。**
