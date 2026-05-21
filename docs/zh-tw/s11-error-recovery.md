# s11: Error Recovery (錯誤恢復)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > [ s11 ] > s12 > s13 > s14 > s15 > s16 > s17 > s18 > s19`

> *錯誤不是例外，而是主迴圈必須預留出來的一條正常分支。*

## 這一章要解決什麼問題

到了 `s10`，你的 agent 已經有了：

- 主迴圈
- 工具呼叫
- 規劃
- 上下文壓縮
- 許可權、hook、memory、system prompt

這時候系統已經不再是一個“只會聊天”的 demo，而是一個真的在做事的程式。

問題也隨之出現：

- 模型輸出寫到一半被截斷
- 上下文太長，請求直接失敗
- 網路暫時抖動，API 超時或限流

如果沒有恢復機制，主迴圈會在第一個錯誤上直接停住。  
這對初學者很危險，因為他們會誤以為“agent 不穩定是模型的問題”。

實際上，很多失敗並不是“任務真的失敗了”，而只是：

**這一輪需要換一種繼續方式。**

所以這一章的目標只有一個：

**把「出錯就崩潰」升級為“先判斷錯誤型別，再選擇恢復路徑”。**

## 建議聯讀

- 如果你開始分不清“為什麼這一輪還在繼續”，先回 [`s00c-query-transition-model.md`](./s00c-query-transition-model.md)，重新確認 transition reason 為什麼是獨立狀態。
- 如果你在恢復邏輯裡又把上下文壓縮和錯誤恢復混成一團，建議順手回看 [`s06-context-compact.md`](./s06-context-compact.md)，區分“為了縮上下文而壓縮”和“因為失敗而恢復”。
- 如果你準備繼續往 `s12` 走，建議把 [`data-structures.md`](./data-structures.md) 放在旁邊，因為後面任務系統會在“恢復狀態之外”再引入新的 durable work 狀態。

## 先解釋幾個名詞

### 什麼叫恢復

恢復，不是把所有錯誤都藏起來。

恢復的意思是：

- 先判斷這是不是臨時問題
- 如果是，就嘗試一個有限次數的補救動作
- 如果補救失敗，再把失敗明確告訴使用者

### 什麼叫重試預算

重試預算，就是“最多試幾次”。

比如：

- 續寫最多 3 次
- 網路重連最多 3 次

如果沒有這個預算，程式就可能無限迴圈。

### 什麼叫狀態機

狀態機這個詞聽起來很大，其實意思很簡單：

> 一個東西會在幾個明確狀態之間按規則切換。

在這一章裡，主迴圈就從“普通執行”變成了：

- 正常執行
- 續寫恢復
- 壓縮恢復
- 退避重試
- 最終失敗

## 最小心智模型

不要把錯誤恢復想得太神秘。

教學版只需要先區分 3 類問題：

```text
1. 輸出被截斷
   模型還沒說完，但 token 用完了

2. 上下文太長
   請求裝不進模型視窗了

3. 臨時連線失敗
   網路、超時、限流、服務抖動
```

對應 3 條恢復路徑：

```text
LLM call
  |
  +-- stop_reason == "max_tokens"
  |      -> 注入續寫提示
  |      -> 再試一次
  |
  +-- prompt too long
  |      -> 壓縮舊上下文
  |      -> 再試一次
  |
  +-- timeout / rate limit / transient API error
         -> 等一會兒
         -> 再試一次
```

這就是最小但正確的恢復模型。

## 關鍵資料結構

### 1. 恢復狀態

```python
recovery_state = {
    "continuation_attempts": 0,
    "compact_attempts": 0,
    "transport_attempts": 0,
}
```

它的作用不是“記錄一切”，而是：

- 防止無限重試
- 讓每種恢復路徑各算各的次數

### 2. 恢復決策

```python
{
    "kind": "continue" | "compact" | "backoff" | "fail",
    "reason": "why this branch was chosen",
}
```

把“錯誤長什麼樣”和“接下來怎麼做”分開，會更清楚。

### 3. 續寫提示

```python
CONTINUE_MESSAGE = (
    "Output limit hit. Continue directly from where you stopped. "
    "Do not restart or repeat."
)
```

這條提示非常重要。

因為如果你只說“繼續”，模型經常會：

- 重新總結
- 重新開頭
- 重複已經輸出過的內容

## 最小實現

先寫一個恢復選擇器：

```python
def choose_recovery(stop_reason: str | None, error_text: str | None) -> dict:
    if stop_reason == "max_tokens":
        return {"kind": "continue", "reason": "output truncated"}

    if error_text and "prompt" in error_text and "long" in error_text:
        return {"kind": "compact", "reason": "context too large"}

    if error_text and any(word in error_text for word in [
        "timeout", "rate", "unavailable", "connection"
    ]):
        return {"kind": "backoff", "reason": "transient transport failure"}

    return {"kind": "fail", "reason": "unknown or non-recoverable error"}
```

再把它接進主迴圈：

```python
while True:
    try:
        response = client.messages.create(...)
        decision = choose_recovery(response.stop_reason, None)
    except Exception as e:
        response = None
        decision = choose_recovery(None, str(e).lower())

    if decision["kind"] == "continue":
        messages.append({"role": "user", "content": CONTINUE_MESSAGE})
        continue

    if decision["kind"] == "compact":
        messages = auto_compact(messages)
        continue

    if decision["kind"] == "backoff":
        time.sleep(backoff_delay(...))
        continue

    if decision["kind"] == "fail":
        break

    # 正常工具處理
```

注意這裡的重點不是程式碼花哨，而是：

- 先分類
- 再選動作
- 每條動作有自己的預算

## 三條恢復路徑分別在補什麼洞

### 路徑 1：輸出被截斷時，做續寫

這個問題的本質不是“模型不會”，而是“這一輪輸出空間不夠”。

所以最小補法是：

1. 追加一條續寫訊息
2. 告訴模型不要重來，不要重複
3. 讓主迴圈繼續

```python
if response.stop_reason == "max_tokens":
    if state["continuation_attempts"] >= 3:
        return "Error: output recovery exhausted"
    state["continuation_attempts"] += 1
    messages.append({"role": "user", "content": CONTINUE_MESSAGE})
    continue
```

### 路徑 2：上下文太長時，先壓縮再重試

這裡要先明確一點：

壓縮不是“把歷史刪掉”，而是：

**把舊對話從原文，變成一份仍然可繼續工作的摘要。**

最小壓縮結果建議至少保留：

- 當前任務是什麼
- 已經做了什麼
- 關鍵決定是什麼
- 下一步準備做什麼

```python
def auto_compact(messages: list) -> list:
    summary = summarize_messages(messages)
    return [{
        "role": "user",
        "content": "This session was compacted. Continue from this summary:\n" + summary,
    }]
```

### 路徑 3：連線抖動時，退避重試

“退避”這個詞的意思是：

> 別立刻再打一次，而是等一小會兒再試。

為什麼要等？

因為這類錯誤往往是臨時擁堵：

- 剛超時
- 剛限流
- 伺服器剛好抖了一下

如果你瞬間連續重打，只會更容易失敗。

```python
def backoff_delay(attempt: int) -> float:
    return min(1.0 * (2 ** attempt), 30.0) + random.uniform(0, 1)
```

## 如何接到主迴圈裡

最乾淨的接法，是把恢復邏輯放在兩個位置：

### 位置 1：模型呼叫外層

負責處理：

- API 錯誤
- 網路錯誤
- 超時

### 位置 2：拿到 response 以後

負責處理：

- `stop_reason == "max_tokens"`
- 正常的 `tool_use`
- 正常的結束

也就是說，主迴圈現在不只是“調模型 -> 執行工具”，而是：

```text
1. 調模型
2. 如果呼叫報錯，判斷是否可以恢復
3. 如果拿到響應，判斷是否被截斷
4. 如果需要恢復，就修改 messages 或等待
5. 如果不需要恢復，再進入正常工具分支
```

## 初學者最容易犯的錯

### 1. 把所有錯誤都當成一種錯誤

這樣會導致：

- 該續寫的去壓縮
- 該等待的去重試
- 該失敗的卻無限拖延

### 2. 沒有重試預算

沒有預算，主迴圈就可能永遠卡在“繼續”“繼續”“繼續”。

### 3. 續寫提示寫得太模糊

只寫一個“continue”通常不夠。  
你要明確告訴模型：

- 不要重複
- 不要重新總結
- 直接從中斷點接著寫

### 4. 壓縮後沒有告訴模型“這是續場”

如果壓縮後只給一份摘要，不告訴模型“這是前文摘要”，模型很可能重新向用戶提問。

### 5. 恢復過程完全沒有日誌

教學系統最好列印類似：

- `[Recovery] continue`
- `[Recovery] compact`
- `[Recovery] backoff`

這樣讀者才看得見主迴圈到底做了什麼。

## 這一章和前後章節怎麼銜接

- `s06` 講的是“什麼時候該壓縮”
- `s10` 講的是“系統提示詞怎麼組裝”
- `s11` 講的是“當執行失敗時，主迴圈怎麼續下去”
- `s12` 開始，恢復機制會保護更長、更復雜的任務流

所以 `s11` 的位置非常關鍵。

它不是外圍小功能，而是：

**把 agent 從“能跑”推進到“遇到問題也能繼續跑”。**

## 教學邊界

這一章先把 3 條最小恢復路徑講穩就夠了：

- 輸出截斷後續寫
- 上下文過長後壓縮再試
- 請求抖動後退避重試

對教學主線來說，重點不是把所有“為什麼繼續下一輪”的原因一次講全，而是先讓讀者明白：

**恢復不是簡單 try/except，而是系統知道該怎麼續下去。**

更大的 query 續行模型、預算續行、hook 介入這些內容，應該放回控制平面的橋接文件裡看，而不是搶掉這章主線。

## 試一試

```sh
cd learn-claude-code
python agents/s11_error_recovery.py
```

可以試試這些任務：

1. 讓模型生成一段特別長的內容，觀察它是否會自動續寫。
2. 連續讀取一些大檔案，觀察上下文壓縮是否會介入。
3. 臨時製造一次請求失敗，觀察系統是否會退避重試。

讀這一章時，你真正要記住的不是某個具體異常名，而是這條主線：

**錯誤先分類，恢復再執行，失敗最後才暴露給使用者。**
