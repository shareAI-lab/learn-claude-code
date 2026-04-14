# s03: TodoWrite (會話內規劃)

`s00 > s01 > s02 > [ s03 ] > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *計劃不是替模型思考，而是把“正在做什麼”明確寫出來。*

## 這一章要解決什麼問題

到了 `s02`，agent 已經會讀檔案、寫檔案、跑命令。

問題也馬上出現了：

- 多步任務容易走一步忘一步
- 明明已經做過的檢查，會重複再做
- 一口氣列出很多步驟後，很快又回到即興發揮

這是因為模型雖然“能想”，但它的當前注意力始終受上下文影響。  
如果沒有一塊**顯式、穩定、可反覆更新**的計劃狀態，大任務就很容易漂。

所以這一章要補上的，不是“更強的工具”，而是：

**讓 agent 把當前會話裡的計劃外顯出來，並且持續更新。**

## 先解釋幾個名詞

### 什麼是會話內規劃

這裡說的規劃，不是長期專案管理，也不是磁碟上的任務系統。

它更像：

> 為了完成當前這次請求，先把接下來幾步寫出來，並在過程中不斷更新。

### 什麼是 todo

`todo` 在這一章裡只是一個載體。

你不要把它理解成“某個特定產品裡的某個工具名”，更應該把它理解成：

> 模型用來寫入當前計劃的一條入口。

### 什麼是 active step

`active step` 可以理解成“當前正在做的那一步”。

教學版裡我們用 `in_progress` 表示它。  
這麼做的目的不是形式主義，而是幫助模型維持焦點：

> 同一時間，先把一件事做完，再進入下一件。

### 什麼是提醒

提醒不是替模型規劃，而是當它連續幾輪都忘記更新計劃時，輕輕拉它回來。

## 先立清邊界：這章不是任務系統

這是這一章最重要的邊界。

`s03` 講的是：

- 當前會話裡的輕量計劃
- 用來幫助模型聚焦下一步
- 可以隨任務推進不斷改寫

它**不是**：

- 持久化任務板
- 依賴圖
- 多 agent 共用的工作圖
- 後臺執行時任務管理

這些會在 `s12-s14` 再系統展開。

如果你現在就把 `s03` 講成完整任務平臺，初學者會很快混淆：

- “當前這一步要做什麼”
- “整個系統長期還有哪些工作項”

## 最小心智模型

把這一章先想成一個很簡單的結構：

```text
使用者提出大任務
   |
   v
模型先寫一份當前計劃
   |
   v
計劃狀態
  - [ ] 還沒做
  - [>] 正在做
  - [x] 已完成
   |
   v
每做完一步，就更新計劃
```

更具體一點：

```text
1. 先拆幾步
2. 選一項作為當前 active step
3. 做完後標記 completed
4. 把下一項改成 in_progress
5. 如果好幾輪沒更新，系統提醒一下
```

這就是最小版本最該教清楚的部分。

## 關鍵資料結構

### 1. PlanItem

最小條目可以長這樣：

```python
{
    "content": "Read the failing test",
    "status": "pending" | "in_progress" | "completed",
    "activeForm": "Reading the failing test",
}
```

這裡的欄位分別表示：

- `content`：這一步要做什麼
- `status`：這一步現在處在什麼狀態
- `activeForm`：當它正在進行中時，可以用更自然的進行時描述

### 2. PlanningState

除了計劃條目本身，還應該有一點最小執行狀態：

```python
{
    "items": [...],
    "rounds_since_update": 0,
}
```

`rounds_since_update` 的意思很簡單：

> 連續多少輪過去了，模型還沒有更新這份計劃。

### 3. 狀態約束

教學版推薦先立一條簡單規則：

```text
同一時間，最多一個 in_progress
```

這不是宇宙真理。  
它只是一個非常適合初學者的教學約束：

**強制模型聚焦當前一步。**

## 最小實現

### 第一步：準備一個計劃管理器

```python
class TodoManager:
    def __init__(self):
        self.items = []
```

### 第二步：允許模型整體更新當前計劃

```python
def update(self, items: list) -> str:
    validated = []
    in_progress_count = 0

    for item in items:
        status = item.get("status", "pending")
        if status == "in_progress":
            in_progress_count += 1
        validated.append({
            "content": item["content"],
            "status": status,
            "activeForm": item.get("activeForm", ""),
        })

    if in_progress_count > 1:
        raise ValueError("Only one item can be in_progress")

    self.items = validated
    return self.render()
```

教學版讓模型“整份重寫”當前計劃，比做一堆區域性增刪改更容易理解。

### 第三步：把計劃渲染成可讀文字

```python
def render(self) -> str:
    lines = []
    for item in self.items:
        marker = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
        }[item["status"]]
        lines.append(f"{marker} {item['content']}")
    return "\n".join(lines)
```

### 第四步：把 `todo` 接成一個工具

```python
TOOL_HANDLERS = {
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "bash": run_bash,
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

### 第五步：如果連續幾輪沒更新計劃，就提醒

```python
if rounds_since_update >= 3:
    results.insert(0, {
        "type": "text",
        "text": "<reminder>Refresh your plan before continuing.</reminder>",
    })
```

這一步的核心意義不是“催促”本身，而是：

> 系統開始把“計劃狀態是否失活”也看成主迴圈的一部分。

## 它如何接到主迴圈裡

這一章以後，主迴圈不再只維護：

- `messages`

還開始維護一份額外的會話狀態：

- `PlanningState`

也就是說，agent loop 現在不只是在“對話”。

它還在維持一塊當前工作面板：

```text
messages          -> 模型看到的歷史
planning state    -> 當前計劃的顯式外部狀態
```

這就是這一章真正想讓你學會的升級：

**把“當前要做什麼”從模型腦內，移到系統可觀察的狀態裡。**

## 為什麼這章故意不講成任務圖

因為這裡的重點是：

- 幫模型聚焦下一步
- 讓當前進度變得外顯
- 給主迴圈一個“過程性狀態”

而不是：

- 任務依賴
- 長期持久化
- 多人協作任務板
- 後臺執行槽位

如果你已經開始關心這些問題，說明你快進入：

- [`s12-task-system.md`](./s12-task-system.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## 初學者最容易犯的錯

### 1. 把計劃寫得過長

計劃不是越多越好。

如果一上來列十幾步，模型很快就會失去維護意願。

### 2. 不區分“當前一步”和“未來幾步”

如果同時有很多個 `in_progress`，焦點就會散。

### 3. 把會話計劃當成長期任務系統

這會讓 `s03` 和 `s12` 的邊界完全混掉。

### 4. 只在開始時寫一次計劃，後面從不更新

那這份計劃就失去價值了。

### 5. 以為 reminder 是可有可無的小裝飾

不是。

提醒機制說明了一件很重要的事：

> 主迴圈不僅要執行動作，還要維護動作過程中的結構化狀態。

## 教學邊界

這一章講的是：

**會話裡的外顯計劃狀態。**

它還不是後面那種持久任務系統，所以邊界要守住：

- 這裡的 `todo` 只服務當前會話，不負責跨階段持久化
- `{id, text, status}` 這種小結構已經夠教會核心模式
- reminder 直接一點沒問題，重點是讓模型持續更新計劃

這一章真正要讓讀者看見的是：

**當計劃進入結構化狀態，而不是散在自然語言裡時，agent 的漂移會明顯減少。**

## 一句話記住

**`s03` 的 todo，不是任務平臺，而是當前會話裡的“外顯計劃狀態”。**
