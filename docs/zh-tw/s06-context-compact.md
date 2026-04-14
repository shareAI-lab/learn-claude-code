# s06: Context Compact (上下文壓縮)

`s00 > s01 > s02 > s03 > s04 > s05 > [ s06 ] > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *上下文不是越多越好，而是要把“仍然有用的部分”留在活躍工作面裡。*

## 這一章要解決什麼問題

到了 `s05`，agent 已經會：

- 讀寫檔案
- 規劃步驟
- 派子 agent
- 按需載入 skill

也正因為它會做的事情更多了，上下文會越來越快膨脹：

- 讀一個大檔案，會塞進很多文字
- 跑一條長命令，會得到大段輸出
- 多輪任務推進後，舊結果會越來越多

如果沒有壓縮機制，很快就會出現這些問題：

1. 模型注意力被舊結果淹沒
2. API 請求越來越重，越來越貴
3. 最終直接撞上上下文上限，任務中斷

所以這一章真正要解決的是：

**怎樣在不丟掉主線連續性的前提下，把活躍上下文重新騰出空間。**

## 先解釋幾個名詞

### 什麼是上下文視窗

你可以把上下文視窗理解成：

> 模型這一輪真正能一起看到的輸入容量。

它不是無限的。

### 什麼是活躍上下文

並不是歷史上出現過的所有內容，都必須一直留在窗口裡。

活躍上下文更像：

> 當前這幾輪繼續工作時，最值得模型馬上看到的那一部分。

### 什麼是壓縮

這裡的壓縮，不是 ZIP 壓縮檔案。

它的意思是：

> 用更短的表示方式，保留繼續工作真正需要的資訊。

例如：

- 大輸出只保留預覽，全文寫到磁碟
- 很久以前的工具結果改成佔位提示
- 整段長曆史總結成一份摘要

## 最小心智模型

這一章建議你先記三層，不要一上來記八層十層：

```text
第 1 層：大結果不直接塞進上下文
  -> 寫到磁碟，只留預覽

第 2 層：舊結果不一直原樣保留
  -> 替換成簡短佔位

第 3 層：整體歷史太長時
  -> 生成一份連續性摘要
```

可以畫成這樣：

```text
tool output
   |
   +-- 太大 -----------------> 儲存到磁碟 + 留預覽
   |
   v
messages
   |
   +-- 太舊 -----------------> 替換成佔位提示
   |
   v
if whole context still too large:
   |
   v
compact history -> summary
```

手動觸發 `/compact` 或 `compact` 工具，本質上也是走第 3 層。

## 關鍵資料結構

### 1. Persisted Output Marker

當工具輸出太大時，不要把全文強塞進當前對話。

最小標記可以長這樣：

```text
<persisted-output>
Full output saved to: .task_outputs/tool-results/abc123.txt
Preview:
...
</persisted-output>
```

這個結構表達的是：

- 全文沒有丟
- 只是搬去了磁碟
- 當前上下文裡只保留一個足夠讓模型繼續判斷的預覽

### 2. CompactState

最小教學版建議你顯式維護一份壓縮狀態：

```python
{
    "has_compacted": False,
    "last_summary": "",
    "recent_files": [],
}
```

這裡的欄位分別表示：

- `has_compacted`：這一輪之前是否已經做過完整壓縮
- `last_summary`：最近一次壓縮得到的摘要
- `recent_files`：最近碰過哪些檔案，壓縮後方便繼續追蹤

### 3. Micro-Compact Boundary

教學版可以先設一條簡單規則：

```text
只保留最近 3 個工具結果的完整內容
更舊的改成佔位提示
```

這就已經足夠讓初學者理解：

**不是所有歷史都要原封不動地一直帶著跑。**

## 最小實現

### 第一步：大工具結果先寫磁碟

```python
def persist_large_output(tool_use_id: str, output: str) -> str:
    if len(output) <= PERSIST_THRESHOLD:
        return output

    stored_path = save_to_disk(tool_use_id, output)
    preview = output[:2000]
    return (
        "<persisted-output>\n"
        f"Full output saved to: {stored_path}\n"
        f"Preview:\n{preview}\n"
        "</persisted-output>"
    )
```

這一步的關鍵思想是：

> 讓模型知道“發生了什麼”，但不強迫它一直揹著整份原始大輸出。

### 第二步：舊工具結果做微壓縮

```python
def micro_compact(messages: list) -> list:
    tool_results = collect_tool_results(messages)
    for result in tool_results[:-3]:
        result["content"] = "[Earlier tool result omitted for brevity]"
    return messages
```

這一步不是為了優雅，而是為了防止上下文被舊結果持續霸佔。

### 第三步：整體歷史過長時，做一次完整壓縮

```python
def compact_history(messages: list) -> list:
    summary = summarize_conversation(messages)
    return [{
        "role": "user",
        "content": (
            "This conversation was compacted for continuity.\n\n"
            + summary
        ),
    }]
```

這裡最重要的不是摘要格式多麼複雜，而是你要保住這幾類資訊：

- 當前目標是什麼
- 已經做了什麼
- 改過哪些檔案
- 還有什麼沒完成
- 哪些決定不能丟

### 第四步：在主迴圈裡接入壓縮

```python
def agent_loop(state):
    while True:
        state["messages"] = micro_compact(state["messages"])

        if estimate_context_size(state["messages"]) > CONTEXT_LIMIT:
            state["messages"] = compact_history(state["messages"])
            state["has_compacted"] = True

        response = call_model(...)
        ...
```

### 第五步：手動壓縮和自動壓縮複用同一條機制

教學版裡，`compact` 工具不需要重新發明另一套邏輯。

它只需要表達：

> 使用者或模型現在主動要求執行一次完整壓縮。

## 壓縮後，真正要保住什麼

這是這章最容易講虛的地方。

壓縮不是“把歷史縮短”這麼簡單。

真正重要的是：

**讓模型還能繼續接著幹活。**

所以一份合格的壓縮結果，至少要保住下面這些東西：

1. 當前任務目標
2. 已完成的關鍵動作
3. 已修改或重點檢視過的檔案
4. 關鍵決定與約束
5. 下一步應該做什麼

如果這些沒有保住，那壓縮雖然騰出了空間，卻打斷了工作連續性。

## 它如何接到主迴圈裡

從這一章開始，主迴圈不再只是：

- 收訊息
- 調模型
- 跑工具

它還多了一個很關鍵的責任：

- 管理活躍上下文的預算

也就是說，agent loop 現在開始同時維護兩件事：

```text
任務推進
上下文預算
```

這一步非常重要，因為後面的很多機制都會和它聯動：

- `s09` memory 決定什麼資訊值得長期儲存
- `s10` prompt pipeline 決定哪些塊應該重新注入
- `s11` error recovery 會處理壓縮不足時的恢復分支

## 初學者最容易犯的錯

### 1. 以為壓縮等於刪除

不是。

更準確地說，是把“不必常駐活躍上下文”的內容換一種表示。

### 2. 只在撞到上限後才臨時亂補

更好的做法是從一開始就有三層思路：

- 大結果先落盤
- 舊結果先縮短
- 整體過長再摘要

### 3. 摘要只寫成一句空話

如果摘要沒有保住檔案、決定、下一步，它對繼續工作沒有幫助。

### 4. 把壓縮和 memory 混成一類

壓縮解決的是：

- 當前會話太長了怎麼辦

memory 解決的是：

- 哪些資訊跨會話仍然值得保留

### 5. 一上來就給初學者講過多產品化層級

教學主線先講清最小正確模型，比堆很多層名詞更重要。

## 教學邊界

這章不要滑成“所有產品化壓縮技巧大全”。

教學版只需要講清三件事：

1. 什麼該留在活躍上下文裡
2. 什麼該搬到磁碟或佔位標記裡
3. 完整壓縮後，哪些連續性資訊一定不能丟

這已經足夠建立穩定心智：

**壓縮不是刪歷史，而是把細節搬走，好讓系統繼續工作。**

如果讀者已經能用 `persisted output + micro compact + summary compact` 保住長會話連續性，這章就已經夠深了。

## 一句話記住

**上下文壓縮的核心，不是儘量少字，而是讓模型在更短的活躍上下文裡，仍然保住繼續工作的連續性。**
