# s16: Team Protocols (團隊協議)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > [ s16 ] > s17 > s18 > s19`

> *有了郵箱以後，團隊已經能說話；有了協議以後，團隊才開始會“按規矩協作”。*

## 這一章要解決什麼問題

`s15` 已經讓隊友之間可以互相發訊息。

但如果所有事情都只靠自由文字，會有兩個明顯問題：

- 某些動作必須明確批准或拒絕，不能只靠一句模糊回覆
- 一旦多個請求同時存在，系統很難知道“這條回覆對應哪一件事”

最典型的兩個場景就是：

1. 隊友要不要優雅關機
2. 某個高風險計劃要不要先審批

這兩件事看起來不同，但結構其實一樣：

```text
一方發請求
另一方明確回覆
雙方都能用同一個 request_id 對上號
```

所以這一章要加的，不是更多自由聊天，而是：

**一層結構化協議。**

## 建議聯讀

- 如果你開始把普通訊息和協議請求混掉，先回 [`glossary.md`](./glossary.md) 和 [`entity-map.md`](./entity-map.md)。
- 如果你準備繼續讀 `s17` 和 `s18`，建議先看 [`team-task-lane-model.md`](./team-task-lane-model.md)，這樣後面自治認領和 worktree 車道不會一下子纏在一起。
- 如果你想重新確認協議請求最終怎樣迴流到主系統，可以配合看 [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md)。

## 先把幾個詞講明白

### 什麼是協議

協議可以簡單理解成：

> 雙方提前約定好“訊息長什麼樣、收到以後怎麼處理”。

### 什麼是 request_id

`request_id` 就是請求編號。

它的作用是：

- 某個請求發出去以後有一個唯一身份
- 之後的批准、拒絕、超時都能準確指向這一個請求

### 什麼是請求-響應模式

這個詞聽起來像高階概念，其實很簡單：

```text
請求方：我發起一件事
響應方：我明確回答同意還是不同意
```

本章做的，就是把這種模式從“口頭表達”升級成“結構化資料”。

## 最小心智模型

從教學角度，你可以先把協議看成兩層：

```text
1. 協議訊息
2. 請求追蹤表
```

### 協議訊息

```python
{
    "type": "shutdown_request",
    "from": "lead",
    "to": "alice",
    "request_id": "req_001",
    "payload": {},
}
```

### 請求追蹤表

```python
requests = {
    "req_001": {
        "kind": "shutdown",
        "status": "pending",
    }
}
```

只要這兩層都存在，系統就能同時回答：

- 現在發生了什麼
- 這件事目前走到哪一步

## 關鍵資料結構

### 1. ProtocolEnvelope

```python
message = {
    "type": "shutdown_request",
    "from": "lead",
    "to": "alice",
    "request_id": "req_001",
    "payload": {},
    "timestamp": 1710000000.0,
}
```

它比普通訊息多出來的關鍵欄位就是：

- `type`
- `request_id`
- `payload`

### 2. RequestRecord

```python
request = {
    "request_id": "req_001",
    "kind": "shutdown",
    "from": "lead",
    "to": "alice",
    "status": "pending",
}
```

它負責記錄：

- 這是哪種請求
- 誰發給誰
- 當前狀態是什麼

如果你想把教學版再往真實系統推進一步，建議不要只放在記憶體字典裡，而是直接落盤：

```text
.team/requests/
  req_001.json
  req_002.json
```

這樣系統就能做到：

- 請求狀態可恢復
- 協議過程可檢查
- 即使主迴圈繼續往前，請求記錄也不會丟

### 3. 狀態機

本章裡的狀態機非常簡單：

```text
pending -> approved
pending -> rejected
pending -> expired
```

這裡再次提醒讀者：

`狀態機` 的意思不是複雜理論，  
只是“狀態之間如何變化的一張規則表”。

## 最小實現

### 協議 1：優雅關機

“優雅關機”的意思不是直接把執行緒硬砍掉。  
而是：

1. 先發關機請求
2. 隊友明確回覆同意或拒絕
3. 如果同意，先收尾，再退出

發請求：

```python
def request_shutdown(target: str):
    request_id = new_id()
    requests[request_id] = {
        "kind": "shutdown",
        "target": target,
        "status": "pending",
    }
    bus.send(
        "lead",
        target,
        msg_type="shutdown_request",
        extra={"request_id": request_id},
        content="Please shut down gracefully.",
    )
```

收響應：

```python
def handle_shutdown_response(request_id: str, approve: bool):
    record = requests[request_id]
    record["status"] = "approved" if approve else "rejected"
```

### 協議 2：計劃審批

這其實還是同一個請求-響應模板。

比如某個隊友想做高風險改動，可以先提計劃：

```python
def submit_plan(name: str, plan_text: str):
    request_id = new_id()
    requests[request_id] = {
        "kind": "plan_approval",
        "from": name,
        "status": "pending",
        "plan": plan_text,
    }
    bus.send(
        name,
        "lead",
        msg_type="plan_approval",
        extra={"request_id": request_id, "plan": plan_text},
        content="Requesting review.",
    )
```

領導審批：

```python
def review_plan(request_id: str, approve: bool, feedback: str = ""):
    record = requests[request_id]
    record["status"] = "approved" if approve else "rejected"
    bus.send(
        "lead",
        record["from"],
        msg_type="plan_approval_response",
        extra={"request_id": request_id, "approve": approve},
        content=feedback,
    )
```

看到這裡，讀者應該開始意識到：

**本章最重要的不是“關機”或“計劃”本身，而是同一個協議模板可以反覆複用。**

## 協議請求不是普通訊息

這一點一定要講透。

郵箱裡雖然都叫“訊息”，但 `s16` 以後其實已經分成兩類：

### 1. 普通訊息

適合：

- 討論
- 提醒
- 補充說明

### 2. 協議訊息

適合：

- 審批
- 關機
- 交接
- 簽收

它至少要帶：

- `type`
- `request_id`
- `from`
- `to`
- `payload`

最簡單的記法是：

- 普通訊息解決“說了什麼”
- 協議訊息解決“這件事走到哪一步了”

## 如何接到團隊系統裡

這章真正補上的，不只是兩個新工具名，而是一條新的協作迴路：

```text
某個隊友 / lead 發起請求
  ->
寫入 RequestRecord
  ->
把 ProtocolEnvelope 投遞進對方 inbox
  ->
對方下一輪 drain inbox
  ->
按 request_id 更新請求狀態
  ->
必要時再回一條 response
  ->
請求方根據 approved / rejected 繼續後續動作
```

你可以把它理解成：

- `s15` 給了團隊“郵箱”
- `s16` 現在給郵箱裡的某些訊息加上“編號 + 狀態機 + 回執”

如果少了這條結構化迴路，團隊雖然能溝通，但無法穩定協作。

## MessageEnvelope、ProtocolEnvelope、RequestRecord、TaskRecord 的邊界

這 4 個物件很容易一起打結。最穩的記法是：

| 物件 | 它回答什麼問題 | 典型欄位 |
|---|---|---|
| `MessageEnvelope` | 誰跟誰說了什麼 | `from` / `to` / `content` |
| `ProtocolEnvelope` | 這是不是一條結構化請求或響應 | `type` / `request_id` / `payload` |
| `RequestRecord` | 這件協作流程現在走到哪一步 | `kind` / `status` / `from` / `to` |
| `TaskRecord` | 真正的工作項是什麼、誰在做、還卡著誰 | `subject` / `status` / `blockedBy` / `owner` |

一定要牢牢記住：

- 協議請求不是任務本身
- 請求狀態表也不是任務板
- 協議只負責“協作流程”
- 任務系統才負責“真正的工作推進”

## 這一章的教學邊界

教學版先只講 2 類協議就夠了：

- `shutdown`
- `plan_approval`

因為這兩類已經足夠把下面幾件事講清楚：

- 什麼是結構化訊息
- 什麼是 request_id
- 為什麼要有請求狀態表
- 為什麼協議不是自由文字

等這套模板學穩以後，你完全可以再擴充套件：

- 任務認領協議
- 交接協議
- 結果簽收協議

但這些都應該建立在本章的統一模板之上。

## 初學者最容易犯的錯

### 1. 沒有 `request_id`

沒有編號，多個請求同時存在時很快就會亂。

### 2. 收到請求以後只回一句自然語言

例如：

```text
好的，我知道了
```

人類可能看得懂，但系統很難穩定處理。

### 3. 沒有請求狀態表

如果系統不記錄 `pending` / `approved` / `rejected`，協議其實就沒有真正落地。

### 4. 把協議訊息和普通訊息混成一種結構

這樣後面一多，處理邏輯會越來越混。

## 學完這一章，你應該真正掌握什麼

學完以後，你應該能獨立複述下面幾件事：

1. 團隊協議的核心，是“請求-響應 + request_id + 狀態表”。
2. 協議訊息和普通聊天訊息不是一回事。
3. 關機協議和計劃審批雖然業務不同，但底層模板可以複用。
4. 團隊一旦進入結構化協作，就要靠協議，而不是隻靠自然語言。

如果這 4 點已經非常穩定，說明這一章真正學到了。

## 下一章學什麼

這一章解決的是：

> 團隊如何按規則協作。

下一章 `s17` 要解決的是：

> 如果沒有人每次都手動派活，隊友能不能在空閒時自己找任務、自己恢復工作。

也就是從“協議化協作”繼續走向“自治行為”。
