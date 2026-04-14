# s17: Autonomous Agents (自治智慧體)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > [ s17 ] > s18 > s19`

> *一個團隊真正開始“自己運轉”，不是因為 agent 數量變多，而是因為空閒的隊友會自己去找下一份工作。*

## 這一章要解決什麼問題

到了 `s16`，團隊已經有：

- 持久隊友
- 郵箱
- 協議
- 任務板

但還有一個明顯瓶頸：

**很多事情仍然要靠 lead 手動分配。**

例如任務板上已經有 10 條可做任務，如果還要 lead 一個個點名：

- Alice 做 1
- Bob 做 2
- Charlie 做 3

那團隊規模一大，lead 就會變成瓶頸。

所以這一章要解決的核心問題是：

**讓空閒隊友自己掃描任務板，找到可做的任務並認領。**

## 建議聯讀

- 如果你開始把 teammate、task、runtime slot 三層一起講糊，先回 [`team-task-lane-model.md`](./team-task-lane-model.md)。
- 如果你讀到“auto-claim”時開始疑惑“活著的執行槽位”到底放在哪，繼續看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。
- 如果你開始忘記“長期隊友”和“一次性 subagent”最根本的區別，回看 [`entity-map.md`](./entity-map.md)。

## 先解釋幾個名詞

### 什麼叫自治

這裡的自治，不是完全沒人管。

這裡說的自治是：

> 在提前給定規則的前提下，隊友可以自己決定下一步接哪份工作。

### 什麼叫認領

認領，就是把一條原本沒人負責的任務，標記成“現在由我負責”。

### 什麼叫空閒階段

空閒階段不是關機，也不是消失。

它表示：

> 這個隊友當前手頭沒有活，但仍然活著，隨時準備接新活。

## 最小心智模型

最清楚的理解方式，是把每個隊友想成在兩個階段之間切換：

```text
WORK
  |
  | 當前輪工作做完，或者主動進入 idle
  v
IDLE
  |
  +-- 看郵箱，有新訊息 -> 回到 WORK
  |
  +-- 看任務板，有 ready task -> 認領 -> 回到 WORK
  |
  +-- 長時間什麼都沒有 -> shutdown
```

這裡的關鍵不是“讓它永遠不停想”，而是：

**空閒時，按規則檢查兩類新輸入：郵箱和任務板。**

## 關鍵資料結構

### 1. Claimable Predicate

和 `s12` 一樣，這裡最重要的是：

**什麼任務算“當前這個隊友可以安全認領”的任務。**

在當前教學程式碼裡，判定已經不是單純看 `pending`，而是：

```python
def is_claimable_task(task: dict, role: str | None = None) -> bool:
    return (
        task.get("status") == "pending"
        and not task.get("owner")
        and not task.get("blockedBy")
        and _task_allows_role(task, role)
    )
```

這 4 個條件缺一不可：

- 任務還沒開始
- 還沒人認領
- 沒有前置阻塞
- 當前隊友角色滿足認領策略

最後一條很關鍵。

因為現在任務可以帶：

- `claim_role`
- `required_role`

例如：

```python
task = {
    "id": 7,
    "subject": "Implement login page",
    "status": "pending",
    "owner": "",
    "blockedBy": [],
    "claim_role": "frontend",
}
```

這表示：

> 這條任務不是“誰空著誰就拿”，而是要先過角色條件。

### 2. 認領後的任務記錄

一旦認領成功，任務記錄至少會發生這些變化：

```python
{
    "id": 7,
    "owner": "alice",
    "status": "in_progress",
    "claimed_at": 1710000000.0,
    "claim_source": "auto",
}
```

這裡新增的兩個欄位很值得單獨記住：

- `claimed_at`：什麼時候被認領
- `claim_source`：這次認領是 `auto` 還是 `manual`

因為到這一步，系統開始不只是知道“任務現在有人做了”，還開始知道：

- 這是誰拿走的
- 是主動掃描拿走，還是手動點名拿走

### 3. Claim Event Log

除了回寫任務檔案，這章還會把認領動作追加到：

```text
.tasks/claim_events.jsonl
```

每條事件大致長這樣：

```python
{
    "event": "task.claimed",
    "task_id": 7,
    "owner": "alice",
    "role": "frontend",
    "source": "auto",
    "ts": 1710000000.0,
}
```

為什麼這層日誌重要？

因為它回答的是“自治系統剛剛做了什麼”。

只看最終任務檔案，你知道的是：

- 現在是誰 owner

而看事件日誌，你才能知道：

- 它是什麼時候被拿走的
- 是誰拿走的
- 是空閒時自動拿走，還是人工呼叫 `claim_task`

### 4. Durable Request Record

這章雖然重點是自治，但它**不能從 `s16` 退回到“協議請求只放記憶體裡”**。

所以當前程式碼裡仍然保留了持久化請求記錄：

```text
.team/requests/{request_id}.json
```

它儲存的是：

- shutdown request
- plan approval request
- 對應的狀態更新

這層邊界很重要，因為自治隊友並不是在“脫離協議系統另起爐灶”，而是：

> 在已有團隊協議之上，額外獲得“空閒時自己找活”的能力。

### 5. 身份塊

當上下文被壓縮後，隊友有時會“忘記自己是誰”。

最小補法是重新注入一段身份提示：

```python
identity = {
    "role": "user",
    "content": "<identity>You are 'alice', role: frontend, team: default. Continue your work.</identity>",
}
```

當前實現裡還會同時補一條很短的確認語：

```python
{"role": "assistant", "content": "I am alice. Continuing."}
```

這樣做的目的不是好看，而是為了讓恢復後的下一輪繼續知道：

- 我是誰
- 我的角色是什麼
- 我屬於哪個團隊

## 最小實現

### 第一步：讓隊友擁有 `WORK -> IDLE` 的迴圈

```python
while True:
    run_work_phase(...)
    should_resume = run_idle_phase(...)
    if not should_resume:
        break
```

### 第二步：在 IDLE 裡先看郵箱

```python
def idle_phase(name: str, messages: list) -> bool:
    inbox = bus.read_inbox(name)
    if inbox:
        messages.append({
            "role": "user",
            "content": json.dumps(inbox),
        })
        return True
```

這一步的意思是：

如果有人明確找我，那我優先處理“明確發給我的工作”。

### 第三步：如果郵箱沒訊息，再按“當前角色”掃描可認領任務

```python
    unclaimed = scan_unclaimed_tasks(role)
    if unclaimed:
        task = unclaimed[0]
        claim_result = claim_task(
            task["id"],
            name,
            role=role,
            source="auto",
        )
```

這裡當前程式碼有兩個很關鍵的升級：

- `scan_unclaimed_tasks(role)` 不是無差別掃任務，而是帶著角色過濾
- `claim_task(..., source="auto")` 會把“這次是自治認領”顯式寫進任務與事件日誌

也就是說，自治不是“空閒了就亂搶一條”，而是：

> 按當前隊友的角色、任務狀態和阻塞關係，挑出一條真正允許它接手的工作。

### 第四步：認領後先補身份，再把任務提示塞回主迴圈

```python
        ensure_identity_context(messages, name, role, team_name)
        messages.append({
            "role": "user",
            "content": f"<auto-claimed>Task #{task['id']}: {task['subject']}</auto-claimed>",
        })
        messages.append({
            "role": "assistant",
            "content": f"{claim_result}. Working on it.",
        })
        return True
```

這一步非常關鍵。

因為“認領成功”本身還不等於“隊友真的能順利繼續”。

還必須把兩件事接回上下文裡：

- 身份上下文
- 新任務提示

只有這樣，下一輪 `WORK` 才不是無頭蒼蠅，而是：

> 帶著明確身份和明確任務恢復工作。

### 第五步：長時間沒事就退出

```python
    time.sleep(POLL_INTERVAL)
    ...
    return False
```

為什麼需要這個退出路徑？

因為空閒隊友不一定要永遠佔著資源。  
教學版先做“空閒一段時間後關閉”就夠了。

## 為什麼認領必須是原子動作

“原子”這個詞第一次看到可能不熟。

這裡它的意思是：

> 認領這一步要麼完整成功，要麼不發生，不能一半成功一半失敗。

為什麼？

因為兩個隊友可能同時掃描到同一個可做任務。

如果沒有鎖，就可能發生：

- Alice 看見任務 3 沒主人
- Bob 也看見任務 3 沒主人
- 兩人都把自己寫成 owner

所以最小教學版也應該加一個認領鎖：

```python
with claim_lock:
    task = load(task_id)
    if task["owner"]:
        return "already claimed"
    task["owner"] = name
    task["status"] = "in_progress"
    save(task)
```

## 身份重注入為什麼重要

這是這章裡一個很容易被忽視，但很關鍵的點。

當上下文壓縮發生以後，隊友可能丟掉這些關鍵資訊：

- 我是誰
- 我的角色是什麼
- 我屬於哪個團隊

如果沒有這些資訊，隊友後續行為很容易漂。

所以一個很實用的做法是：

如果發現 messages 的開頭已經沒有身份塊，就把身份塊重新插回去。

這裡你可以把它理解成一條恢復規則：

> 任何一次從 idle 恢復、或任何一次壓縮後恢復，只要身份上下文可能變薄，就先補身份，再繼續工作。

## 為什麼 s17 不能從 s16 退回“記憶體協議”

這是一個很容易被漏講，但其實非常重要的點。

很多人一看到“自治”，就容易只盯：

- idle
- auto-claim
- 輪詢

然後忘了 `s16` 已經建立過的另一條主線：

- 請求必須可追蹤
- 協議狀態必須可恢復

所以現在教學程式碼裡，像：

- shutdown request
- plan approval

仍然會寫進：

```text
.team/requests/{request_id}.json
```

也就是說，`s17` 不是推翻 `s16`，而是在 `s16` 上繼續加一條新能力：

```text
協議系統繼續存在
  +
自治掃描與認領開始存在
```

這兩條線一起存在，團隊才會像一個真正的平臺，而不是一堆各自亂跑的 worker。

## 如何接到前面幾章裡

這一章其實是前面幾章第一次真正“串起來”的地方：

- `s12` 提供任務板
- `s15` 提供持久隊友
- `s16` 提供結構化協議
- `s17` 則讓隊友在沒有明確點名時，也能自己找活

所以你可以把 `s17` 理解成：

**從“被動協作”升級到“主動協作”。**

## 自治的是“長期隊友”，不是“一次性 subagent”

這層邊界如果不講清，讀者很容易把 `s04` 和 `s17` 混掉。

`s17` 裡的自治執行者，仍然是 `s15` 那種長期隊友：

- 有名字
- 有角色
- 有郵箱
- 有 idle 階段
- 可以反覆接活

它不是那種：

- 接一條子任務
- 做完返回摘要
- 然後立刻消失

的一次性 subagent。

同樣地，這裡認領的也是：

- `s12` 裡的工作圖任務

而不是：

- `s13` 裡的後臺執行槽位

所以這章其實是在兩條已存在的主線上再往前推一步：

- 長期隊友
- 工作圖任務

再把它們用“自治認領”連線起來。

如果你開始把下面這些詞混在一起：

- teammate
- protocol request
- task
- runtime task

建議回看：

- [`team-task-lane-model.md`](./team-task-lane-model.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)

## 初學者最容易犯的錯

### 1. 只看 `pending`，不看 `blockedBy`

如果一個任務雖然是 `pending`，但前置任務還沒完成，它就不應該被認領。

### 2. 只看狀態，不看 `claim_role` / `required_role`

這會讓錯誤的隊友接走錯誤的任務。

教學版雖然簡單，但從這一章開始，已經應該明確告訴讀者：

- 並不是所有 ready task 都適合所有隊友
- 角色條件本身也是 claim policy 的一部分

### 3. 沒有認領鎖

這會直接導致重複搶同一條任務。

### 4. 空閒階段只輪詢任務板，不看郵箱

這樣隊友會錯過別人明確發給它的訊息。

### 5. 認領了任務，但沒有寫 claim event

這樣最後你只能看到“任務現在被誰做”，卻看不到：

- 它是什麼時候被拿走的
- 是自動認領還是手動認領

### 6. 隊友永遠不退出

教學版裡，長時間無事可做時退出是合理的。  
否則讀者會更難理解資源何時釋放。

### 7. 上下文壓縮後不重注入身份

這很容易讓隊友後面的行為越來越不像“它本來的角色”。

## 教學邊界

這一章先只把自治主線講清楚：

**空閒檢查 -> 安全認領 -> 恢復工作。**

只要這條鏈路穩了，讀者就已經真正理解了“自治”是什麼。

更細的 claim policy、公平排程、事件驅動喚醒、長期保活，都應該建立在這條最小自治鏈之後，而不是搶在前面。

## 試一試

```sh
cd learn-claude-code
python agents/s17_autonomous_agents.py
```

可以試試這些任務：

1. 先建幾條 ready task，再生成兩個隊友，觀察它們是否會自動分工。
2. 建幾條被阻塞的任務，確認隊友不會錯誤認領。
3. 讓某個隊友進入 idle，再發一條訊息給它，觀察它是否會重新被喚醒。

這一章要建立的核心心智是：

**自治不是讓 agent 亂跑，而是讓它在清晰規則下自己接住下一份工作。**
