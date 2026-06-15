# Team Task Lane Model (隊友-任務-車道模型)

> 到了 `s15-s18`，讀者最容易混掉的，不是某個函式名，而是：
>
> **系統裡到底是誰在工作、誰在協調、誰在記錄目標、誰在提供執行目錄。**

## 這篇橋接文件解決什麼問題

如果你一路從 `s15` 看到 `s18`，腦子裡很容易把下面這些詞混在一起：

- teammate
- protocol request
- task
- runtime task
- worktree

它們都和“工作推進”有關。  
但它們不是同一層。

如果這層邊界不單獨講清，後面讀者會經常出現這些困惑：

- 隊友是不是任務本身？
- `request_id` 和 `task_id` 有什麼區別？
- worktree 是不是後臺任務的一種？
- 一個任務完成了，為什麼 worktree 還能保留？

這篇就是專門用來把這幾層拆開的。

## 建議怎麼聯讀

最推薦的讀法是：

1. 先看 [`s15-agent-teams.md`](./s15-agent-teams.md)，確認長期隊友在講什麼。
2. 再看 [`s16-team-protocols.md`](./s16-team-protocols.md)，確認請求-響應協議在講什麼。
3. 再看 [`s17-autonomous-agents.md`](./s17-autonomous-agents.md)，確認自治認領在講什麼。
4. 最後看 [`s18-worktree-task-isolation.md`](./s18-worktree-task-isolation.md)，確認隔離執行車道在講什麼。

如果你開始混：

- 回 [`entity-map.md`](./entity-map.md) 看模組邊界。
- 回 [`data-structures.md`](./data-structures.md) 看記錄結構。
- 回 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md) 看“目標任務”和“執行時執行槽位”的差別。

## 先給結論

先記住這一組最重要的區分：

```text
teammate
  = 誰在長期參與協作

protocol request
  = 團隊內部一次需要被追蹤的協調請求

task
  = 要做什麼

runtime task / execution slot
  = 現在有什麼執行單元正在跑

worktree
  = 在哪做，而且不和別人互相踩目錄
```

這五層裡，最容易混的是最後三層：

- `task`
- `runtime task`
- `worktree`

所以你必須反覆問自己：

- 這是“目標”嗎？
- 這是“執行中的東西”嗎？
- 這是“執行目錄”嗎？

## 一張最小清晰圖

```text
Team Layer
  teammate: alice (frontend)
  teammate: bob (backend)

Protocol Layer
  request_id=req_01
  kind=plan_approval
  status=pending

Work Graph Layer
  task_id=12
  subject="Implement login page"
  owner="alice"
  status="in_progress"

Runtime Layer
  runtime_id=rt_01
  type=in_process_teammate
  status=running

Execution Lane Layer
  worktree=login-page
  path=.worktrees/login-page
  status=active
```

你可以看到：

- `alice` 不是任務
- `request_id` 不是任務
- `runtime_id` 也不是任務
- `worktree` 更不是任務

真正表達“這件工作本身”的，只有 `task_id=12` 那層。

## 1. Teammate：誰在長期協作

這是 `s15` 開始建立的層。

它回答的是：

- 這個長期 worker 叫什麼
- 它是什麼角色
- 它當前是 working、idle 還是 shutdown
- 它有沒有獨立 inbox

最小例子：

```python
member = {
    "name": "alice",
    "role": "frontend",
    "status": "idle",
}
```

這層的核心不是“又多開一個 agent”。

而是：

> 系統開始有長期存在、可重複接活、可被點名協作的身份。

## 2. Protocol Request：誰在協調什麼

這是 `s16` 建立的層。

它回答的是：

- 有誰向誰發起了一個需要追蹤的請求
- 這條請求是什麼型別
- 它現在是 pending、approved 還是 rejected

最小例子：

```python
request = {
    "request_id": "a1b2c3d4",
    "kind": "plan_approval",
    "from": "alice",
    "to": "lead",
    "status": "pending",
}
```

這一層不要和普通聊天混。

因為它不是“發一條訊息就算完”，而是：

> 一條可以被繼續更新、繼續稽核、繼續恢復的協調記錄。

## 3. Task：要做什麼

這是 `s12` 的工作圖任務，也是 `s17` 自治認領的物件。

它回答的是：

- 目標是什麼
- 誰負責
- 是否有阻塞
- 當前進度如何

最小例子：

```python
task = {
    "id": 12,
    "subject": "Implement login page",
    "status": "in_progress",
    "owner": "alice",
    "blockedBy": [],
}
```

這層的關鍵詞是：

**目標**

不是目錄，不是協議，不是程序。

## 4. Runtime Task / Execution Slot：現在有什麼執行單元在跑

這一層在 `s13` 的橋接文件裡已經單獨解釋過，但到了 `s15-s18` 必須再提醒一次。

比如：

- 一個後臺 shell 正在跑
- 一個長期 teammate 正在工作
- 一個 monitor 正在觀察外部狀態

這些都更像：

> 正在執行的執行槽位

而不是“任務目標本身”。

最小例子：

```python
runtime = {
    "id": "rt_01",
    "type": "in_process_teammate",
    "status": "running",
    "work_graph_task_id": 12,
}
```

這裡最重要的邊界是：

- 一個任務可以派生多個 runtime task
- 一個 runtime task 通常只是“如何執行”的一個例項

## 5. Worktree：在哪做

這是 `s18` 建立的執行車道層。

它回答的是：

- 這份工作在哪個獨立目錄裡做
- 這條目錄車道對應哪個任務
- 這條車道現在是 active、kept 還是 removed

最小例子：

```python
worktree = {
    "name": "login-page",
    "path": ".worktrees/login-page",
    "task_id": 12,
    "status": "active",
}
```

這層的關鍵詞是：

**執行邊界**

它不是工作目標本身，而是：

> 讓這份工作在獨立目錄裡推進的執行車道。

## 這五層怎麼連起來

你可以把後段章節連成下面這條鏈：

```text
teammate
  透過 protocol request 協調
  認領 task
  作為一個 runtime execution slot 持續執行
  在某條 worktree lane 裡改程式碼
```

如果寫得更具體一點，會變成：

```text
alice (teammate)
  ->
收到或發起一個 request_id
  ->
認領 task #12
  ->
開始作為執行單元推進工作
  ->
進入 worktree "login-page"
  ->
在 .worktrees/login-page 裡執行命令和改檔案
```

## 一個最典型的混淆例子

很多讀者會把這句話說成：

> “alice 就是在做 login-page 這個 worktree 任務。”

這句話把三層東西混成了一句：

- `alice`：隊友
- `login-page`：worktree
- “任務”：工作圖任務

更準確的說法應該是：

> `alice` 認領了 `task #12`，並在 `login-page` 這條 worktree 車道里推進它。

一旦你能穩定地這樣表述，後面幾章就不容易亂。

## 初學者最容易犯的錯

### 1. 把 teammate 和 task 混成一個物件

隊友是執行者，任務是目標。

### 2. 把 `request_id` 和 `task_id` 混成一個 ID

一個負責協調，一個負責工作目標，不是同一層。

### 3. 把 runtime slot 當成 durable task

執行時執行單元會結束，但 durable task 還可能繼續存在。

### 4. 把 worktree 當成任務本身

worktree 只是執行目錄邊界，不是任務目標。

### 5. 只會講“系統能並行”，卻說不清每層物件各自負責什麼

這是最常見也最危險的模糊表達。

真正清楚的教學，不是說“這裡好多 agent 很厲害”，而是能把下面這句話講穩：

> 隊友負責長期協作，請求負責協調流程，任務負責表達目標，執行時槽位負責承載執行，worktree 負責隔離執行目錄。

## 讀完這篇你應該能自己說清楚

至少能完整說出下面這兩句話：

1. `s17` 的自治認領，認領的是 `s12` 的工作圖任務，不是 `s13` 的執行時槽位。
2. `s18` 的 worktree，繫結的是任務的執行車道，而不是把任務本身變成目錄。

如果這兩句你已經能穩定說清，`s15-s18` 這一大段主線就基本不會再擰巴了。
