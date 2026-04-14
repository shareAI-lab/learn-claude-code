# s08: Hook System (Hook 系統)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > [ s08 ] > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *不改主迴圈程式碼，也能在關鍵時機插入額外行為。*

## 這章要解決什麼問題

到了 `s07`，我們已經能在工具執行前做許可權判斷。

但很多真實需求並不屬於“允許 / 拒絕”這條線，而屬於：

- 在某個固定時機順手做一點事
- 不改主迴圈主體，也能接入額外規則
- 讓使用者或外掛在系統邊緣擴充套件能力

例如：

- 會話開始時列印歡迎資訊
- 工具執行前做一次額外檢查
- 工具執行後補一條審計日誌

如果每增加一個需求，你都去修改主迴圈，主迴圈就會越來越重，最後誰都不敢動。

所以這一章要引入的機制是：

**主迴圈只負責暴露“時機”，真正的附加行為交給 hook。**

## 建議聯讀

- 如果你還在把 hook 想成“往主迴圈裡繼續塞 if/else”，先回 [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md)，重新確認主迴圈和控制面的邊界。
- 如果你開始把主迴圈、tool handler、hook side effect 混成一層，建議先看 [`entity-map.md`](./entity-map.md)，把誰負責推進主狀態、誰只是旁路觀察分開。
- 如果你準備繼續讀後面的 prompt、recovery、teams，可以把 [`s00e-reference-module-map.md`](./s00e-reference-module-map.md) 一起放在旁邊，因為從這一章開始“控制面 + 側車擴充套件”會反覆一起出現。

## 什麼是 hook

你可以把 `hook` 理解成一個“預留插口”。

意思是：

1. 主系統執行到某個固定時機
2. 把當前上下文交給 hook
3. hook 返回結果
4. 主系統再決定下一步怎麼繼續

最重要的一句話是：

**hook 讓系統可擴充套件，但不要求主迴圈理解每個擴充套件需求。**

主迴圈只需要知道三件事：

- 現在是什麼事件
- 要把哪些上下文交出去
- 收到結果以後怎麼處理

## 最小心智模型

教學版先只講 3 個事件：

- `SessionStart`
- `PreToolUse`
- `PostToolUse`

這樣做不是因為系統永遠只有 3 個事件，  
而是因為初學者先把這 3 個事件學明白，就已經能自己做出一套可用的 hook 機制。

可以把它想成這條流程：

```text
主迴圈繼續往前跑
  |
  +-- 到了某個預留時機
  |
  +-- 呼叫 hook runner
  |
  +-- 收到 hook 返回結果
  |
  +-- 決定繼續、阻止、還是補充說明
```

## 教學版統一返回約定

這一章最容易把人講亂的地方，就是“不同 hook 事件的返回語義”。

教學版建議先統一成下面這套規則：

| 退出碼 | 含義 |
|---|---|
| `0` | 正常繼續 |
| `1` | 阻止當前動作 |
| `2` | 注入一條補充訊息，再繼續 |

這套規則的價值不在於“最真實”，而在於“最容易學會”。

因為它讓你先記住 hook 最核心的 3 種作用：

- 觀察
- 攔截
- 補充

等教學版跑通以後，再去做“不同事件採用不同語義”的細化，也不會亂。

## 關鍵資料結構

### 1. HookEvent

```python
event = {
    "name": "PreToolUse",
    "payload": {
        "tool_name": "bash",
        "input": {"command": "pytest"},
    },
}
```

它回答的是：

- 現在發生了什麼事
- 這件事的上下文是什麼

### 2. HookResult

```python
result = {
    "exit_code": 0,
    "message": "",
}
```

它回答的是：

- hook 想不想阻止主流程
- 要不要向模型補一條說明

### 3. HookRunner

```python
class HookRunner:
    def run(self, event_name: str, payload: dict) -> dict:
        ...
```

主迴圈不直接關心“每個 hook 的細節實現”。  
它只把事件交給統一的 runner。

這就是這一章的關鍵抽象邊界：

**主迴圈知道事件名，hook runner 知道怎麼調擴充套件邏輯。**

## 最小執行流程

先看最重要的 `PreToolUse` / `PostToolUse`：

```text
model 發起 tool_use
    |
    v
run_hook("PreToolUse", ...)
    |
    +-- exit 1 -> 阻止工具執行
    +-- exit 2 -> 先補一條訊息給模型，再繼續
    +-- exit 0 -> 直接繼續
    |
    v
執行工具
    |
    v
run_hook("PostToolUse", ...)
    |
    +-- exit 2 -> 追加補充說明
    +-- exit 0 -> 正常結束
```

再加上 `SessionStart`，一整套最小 hook 機制就立住了。

## 最小實現

### 第一步：準備一個事件到處理器的對映

```python
HOOKS = {
    "SessionStart": [on_session_start],
    "PreToolUse": [pre_tool_guard],
    "PostToolUse": [post_tool_log],
}
```

這裡先用“一個事件對應一組處理函式”的最小結構就夠了。

### 第二步：統一執行 hook

```python
def run_hooks(event_name: str, payload: dict) -> dict:
    for handler in HOOKS.get(event_name, []):
        result = handler(payload)
        if result["exit_code"] in (1, 2):
            return result
    return {"exit_code": 0, "message": ""}
```

教學版裡先用“誰先返回阻止/注入，誰就優先”的簡單規則。

### 第三步：接進主迴圈

```python
pre = run_hooks("PreToolUse", {
    "tool_name": block.name,
    "input": block.input,
})

if pre["exit_code"] == 1:
    results.append(blocked_tool_result(pre["message"]))
    continue

if pre["exit_code"] == 2:
    messages.append({"role": "user", "content": pre["message"]})

output = run_tool(...)

post = run_hooks("PostToolUse", {
    "tool_name": block.name,
    "input": block.input,
    "output": output,
})
```

這一步最關鍵的不是程式碼量，而是心智：

**hook 不是主迴圈的替代品，hook 是主迴圈在固定時機對外發出的呼叫。**

## 這一章的教學邊界

如果你後面繼續擴充套件平臺，hook 事件面當然會繼續擴大。

常見擴充套件方向包括：

- 生命週期事件：開始、結束、配置變化
- 工具事件：執行前、執行後、失敗後
- 壓縮事件：壓縮前、壓縮後
- 多 agent 事件：子 agent 啟動、任務完成、隊友空閒

但教學倉這裡要守住一個原則：

**先把 hook 的統一模型講清，再慢慢增加事件種類。**

不要一開始就把幾十種事件、幾十套返回語義全部灌給讀者。

## 初學者最容易犯的錯

### 1. 把 hook 當成“到處插 if”

如果還是散落在主迴圈裡寫條件分支，那還不是真正的 hook 設計。

### 2. 沒有統一的返回結構

今天返回字串，明天返回布林值，後天返回整數，最後主迴圈一定會變亂。

### 3. 一上來就把所有事件做全

教學順序應該是：

1. 先學會 3 個事件
2. 再學會統一返回協議
3. 最後才擴事件面

### 4. 忘了說明“教學版統一語義”和“高完成度細化語義”的區別

如果這層不提前說清，讀者後面看到更復雜實現時會以為前面學錯了。

其實不是學錯了，而是：

**先學統一模型，再學事件細化。**

## 學完這一章，你應該真正掌握什麼

學完以後，你應該能自己清楚說出下面幾句話：

1. hook 的作用，是在固定時機擴充套件系統，而不是改寫主迴圈。
2. hook 至少需要“事件名 + payload + 返回結果”這三樣東西。
3. 教學版可以先用統一的 `0 / 1 / 2` 返回約定。
4. `PreToolUse` 和 `PostToolUse` 已經足夠支撐最核心的擴充套件能力。

如果這 4 句話你已經能獨立複述，說明這一章的核心心智已經建立起來了。

## 下一章學什麼

這一章解決的是：

> 在固定時機插入行為。

下一章 `s09` 要解決的是：

> 哪些資訊應該跨會話留下，哪些不該留。

也就是從“擴充套件點”進一步走向“持久狀態”。
