# s18: Worktree + Task Isolation (Worktree 任務隔離)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > s17 > [ s18 ] > s19`

> *任務板解決“做什麼”，worktree 解決“在哪做而不互相踩到”。*

## 這一章要解決什麼問題

到 `s17` 為止，系統已經可以：

- 拆任務
- 認領任務
- 讓多個 agent 並行推進不同工作

但如果所有人都在同一個工作目錄裡改檔案，很快就會出現這些問題：

- 兩個任務同時改同一個檔案
- 一個任務還沒做完，另一個任務的修改已經把目錄汙染了
- 想單獨回看某個任務的改動範圍時，很難分清

也就是說，任務系統已經回答了“誰做什麼”，卻還沒有回答：

**每個任務應該在哪個獨立工作空間裡執行。**

這就是 worktree 要解決的問題。

## 建議聯讀

- 如果你開始把 task、runtime slot、worktree lane 三層混成一個詞，先看 [`team-task-lane-model.md`](./team-task-lane-model.md)。
- 如果你想確認 worktree 記錄和任務記錄分別該儲存哪些欄位，回看 [`data-structures.md`](./data-structures.md)。
- 如果你想從“參考倉庫主幹”角度確認這一章為什麼必須晚於 tasks / teams，再看 [`s00e-reference-module-map.md`](./s00e-reference-module-map.md)。

## 先解釋幾個名詞

### 什麼是 worktree

如果你熟悉 git，可以把 worktree 理解成：

> 同一個倉庫的另一個獨立檢出目錄。

如果你還不熟悉 git，也可以先把它理解成：

> 一條屬於某個任務的獨立工作車道。

### 什麼叫隔離執行

隔離執行就是：

> 任務 A 在自己的目錄裡跑，任務 B 在自己的目錄裡跑，彼此預設不共享未提交改動。

### 什麼叫繫結

繫結的意思是：

> 把某個任務 ID 和某個 worktree 記錄明確關聯起來。

## 最小心智模型

最容易理解的方式，是把這一章拆成兩張表：

```text
任務板
  負責回答：做什麼、誰在做、狀態如何

worktree 登錄檔
  負責回答：在哪做、目錄在哪、對應哪個任務
```

兩者透過 `task_id` 連起來：

```text
.tasks/task_12.json
  {
    "id": 12,
    "subject": "Refactor auth flow",
    "status": "in_progress",
    "worktree": "auth-refactor"
  }

.worktrees/index.json
  {
    "worktrees": [
      {
        "name": "auth-refactor",
        "path": ".worktrees/auth-refactor",
        "branch": "wt/auth-refactor",
        "task_id": 12,
        "status": "active"
      }
    ]
  }
```

看懂這兩條記錄，這一章的主線就已經抓住了：

**任務記錄工作目標，worktree 記錄執行車道。**

## 關鍵資料結構

### 1. TaskRecord 不再只記錄 `worktree`

到當前教學程式碼這一步，任務記錄裡和車道相關的欄位已經不只一個：

```python
task = {
    "id": 12,
    "subject": "Refactor auth flow",
    "status": "in_progress",
    "owner": "alice",
    "worktree": "auth-refactor",
    "worktree_state": "active",
    "last_worktree": "auth-refactor",
    "closeout": None,
}
```

這 4 個欄位分別回答不同問題：

- `worktree`：當前還繫結著哪條車道
- `worktree_state`：這條繫結現在是 `active`、`kept`、`removed` 還是 `unbound`
- `last_worktree`：最近一次用過哪條車道
- `closeout`：最後一次收尾動作是什麼

為什麼要拆這麼細？

因為到多 agent 並行階段，系統已經不只需要知道“現在在哪做”，還需要知道：

- 這條車道現在是不是還活著
- 它最後是保留還是回收
- 之後如果恢復或排查，應該看哪條歷史車道

### 2. WorktreeRecord 不只是路徑對映

```python
worktree = {
    "name": "auth-refactor",
    "path": ".worktrees/auth-refactor",
    "branch": "wt/auth-refactor",
    "task_id": 12,
    "status": "active",
    "last_entered_at": 1710000000.0,
    "last_command_at": 1710000012.0,
    "last_command_preview": "pytest tests/auth -q",
    "closeout": None,
}
```

這裡也要特別注意：

worktree 記錄回答的不只是“目錄在哪”，還開始回答：

- 最近什麼時候進入過
- 最近跑過什麼命令
- 最後是怎麼收尾的

這就是為什麼這章講的是：

**可觀察的執行車道**

而不只是“多開一個目錄”。

### 3. CloseoutRecord

這一章在當前程式碼裡，一個完整的收尾記錄大致是：

```python
closeout = {
    "action": "keep",
    "reason": "Need follow-up review",
    "at": 1710000100.0,
}
```

這層記錄很重要，因為它把“結尾到底發生了什麼”顯式寫出來，而不是靠人猜：

- 是保留目錄，方便繼續追看
- 還是回收目錄，表示這條執行車道已經結束

### 4. EventRecord

```python
event = {
    "event": "worktree.closeout.keep",
    "task_id": 12,
    "worktree": "auth-refactor",
    "reason": "Need follow-up review",
    "ts": 1710000100.0,
}
```

為什麼還要事件記錄？

因為 worktree 的生命週期經常跨很多步：

- 建立
- 進入
- 執行命令
- 保留
- 刪除
- 刪除失敗

有顯式事件日誌，會比只看當前狀態更容易排查問題。

## 最小實現

### 第一步：先有任務，再有 worktree

不要先開目錄再回頭補任務。

更清楚的順序是：

1. 先建立任務
2. 再為這個任務分配 worktree

```python
task = tasks.create("Refactor auth flow")
worktrees.create("auth-refactor", task_id=task["id"])
```

### 第二步：建立 worktree 並寫入登錄檔

```python
def create(self, name: str, task_id: int):
    path = self.root / ".worktrees" / name
    branch = f"wt/{name}"

    run_git(["worktree", "add", "-b", branch, str(path), "HEAD"])

    record = {
        "name": name,
        "path": str(path),
        "branch": branch,
        "task_id": task_id,
        "status": "active",
    }
    self.index["worktrees"].append(record)
    self._save_index()
```

### 第三步：同時更新任務記錄，不只是寫一個 `worktree`

```python
def bind_worktree(task_id: int, name: str):
    task = tasks.load(task_id)
    task["worktree"] = name
    task["last_worktree"] = name
    task["worktree_state"] = "active"
    if task["status"] == "pending":
        task["status"] = "in_progress"
    tasks.save(task)
```

為什麼這一步很關鍵？

因為如果只更新 worktree 登錄檔，不更新任務記錄，系統就無法從任務板一眼看出“這個任務在哪個隔離目錄裡做”。

### 第四步：顯式進入車道，再在對應目錄裡執行命令

當前程式碼裡，進入和執行已經拆成兩步：

```python
worktree_enter("auth-refactor")
worktree_run("auth-refactor", "pytest tests/auth -q")
```

對應到底層，大致就是：

```python
def enter(self, name: str):
    self._update_entry(name, last_entered_at=time.time())
    self.events.emit("worktree.enter", ...)

def run(self, name: str, command: str):
    subprocess.run(command, cwd=worktree_path, ...)
```

```python
subprocess.run(command, cwd=worktree_path, ...)
```

這一行看起來普通，但它正是隔離的核心：

**同一個命令，在不同 `cwd` 裡執行，影響範圍就不一樣。**

為什麼還要單獨補一個 `worktree_enter`？

因為教學上你要讓讀者看見：

- “分配車道”是一回事
- “真正進入並開始在這條車道里工作”是另一回事

這層邊界一清楚，後面的觀察欄位才有意義：

- `last_entered_at`
- `last_command_at`
- `last_command_preview`

### 第五步：收尾時顯式走 `worktree_closeout`

不要讓收尾是隱式的。

當前更清楚的教學介面不是“分散記兩個命令”，而是統一成一個 closeout 動作：

```python
worktree_closeout(
    name="auth-refactor",
    action="keep",   # or "remove"
    reason="Need follow-up review",
    complete_task=False,
)
```

這樣讀者會更容易理解：

- 收尾一定要選動作
- 收尾可以帶原因
- 收尾會同時回寫任務記錄、車道記錄和事件日誌

當然，底層仍然保留：

- `worktree_keep(name)`
- `worktree_remove(name, reason=..., complete_task=True)`

但教學主線最好先把：

> `keep` 和 `remove` 看成同一個 closeout 決策的兩個分支

這樣讀者心智會更順。

## 為什麼 `worktree_state` 和 `status` 要分開

這也是一個很容易被忽略的細點。

很多初學者會想：

> “任務有 `status` 了，為什麼還要 `worktree_state`？”

因為這兩個狀態根本不是一層東西：

- 任務 `status` 回答：這件工作現在是 `pending`、`in_progress` 還是 `completed`
- `worktree_state` 回答：這條執行車道現在是 `active`、`kept`、`removed` 還是 `unbound`

舉個最典型的例子：

```text
任務已經 completed
  但 worktree 仍然 kept
```

這完全可能，而且很常見。  
比如你已經做完了，但還想保留目錄給 reviewer 看。

所以：

**任務狀態和車道狀態不能混成一個欄位。**

## 為什麼 worktree 不是“只是一個 git 小技巧”

很多初學者第一次看到這一章，會覺得：

> “這不就是多開幾個目錄嗎？”

這句話只說對了一半。

真正關鍵的不只是“多開目錄”，而是：

**把任務和執行目錄做顯式繫結，讓並行工作有清楚的邊界。**

如果沒有這層繫結，系統仍然不知道：

- 哪個目錄屬於哪個任務
- 收尾時該完成哪條任務
- 崩潰後該恢復哪條關係

## 如何接到前面章節裡

這章和前面幾章是強耦合的：

- `s12` 提供任務 ID
- `s15-s17` 提供隊友和認領機制
- `s18` 則給這些任務提供獨立執行車道

把三者連起來看，會變成：

```text
任務被建立
  ->
隊友認領任務
  ->
系統為任務分配 worktree
  ->
命令在對應目錄裡執行
  ->
任務完成時決定保留還是刪除 worktree
```

這條鏈一旦建立，多 agent 並行工作就會清楚很多。

## worktree 不是任務本身，而是任務的執行車道

這句話值得單獨再說一次。

很多讀者第一次學到這裡時，會把這兩個詞混著用：

- task
- worktree

但它們回答的其實不是同一個問題：

- task：做什麼
- worktree：在哪做

所以更完整、也更不容易混的表達方式是：

- 工作圖任務
- worktree 執行車道

如果你開始分不清：

- 任務
- 執行時任務
- worktree

建議回看：

- [`team-task-lane-model.md`](./team-task-lane-model.md)
- [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)
- [`entity-map.md`](./entity-map.md)

## 初學者最容易犯的錯

### 1. 有 worktree 登錄檔，但任務記錄裡沒有 `worktree`

這樣任務板就丟掉了最重要的一條執行資訊。

### 2. 有任務 ID，但命令仍然在主目錄執行

如果 `cwd` 沒切過去，worktree 形同虛設。

### 3. 只會 `worktree_remove`，不會解釋 closeout 的含義

這樣讀者最後只記住“刪目錄”這個動作，卻不知道系統真正想表達的是：

- 保留
- 回收
- 為什麼這麼做
- 是否同時完結對應任務

### 4. 刪除 worktree 前不看未提交改動

這是最危險的一類錯誤。

教學版也應該至少先建立一個原則：

**刪除前先檢查是否有髒改動。**

### 5. 沒有 `worktree_state` / `closeout` 這類顯式收尾狀態

這樣系統就會只剩下“現在目錄還在不在”，而沒有：

- 這條車道最後怎麼收尾
- 是主動保留還是主動刪除

### 6. 把 worktree 當成長期垃圾堆

如果從不清理，目錄會越來越多，狀態越來越亂。

### 7. 沒有事件日誌

一旦建立失敗、刪除失敗或任務關係錯亂，沒有事件日誌會很難排查。

## 教學邊界

這章先要講透的不是所有 worktree 運維細節，而是主幹分工：

- task 記錄“做什麼”
- worktree 記錄“在哪做”
- enter / execute / closeout 串起這條隔離執行車道

只要這條主幹清楚，教學目標就已經達成。

崩潰恢復、刪除安全檢查、全域性快取區、非 git 回退這些，都應該放在這條主幹之後。

## 試一試

```sh
cd learn-claude-code
python agents/s18_worktree_task_isolation.py
```

可以試試這些任務：

1. 為兩個不同任務各建一個 worktree，觀察任務板和登錄檔的對應關係。
2. 分別在兩個 worktree 裡執行 `git status`，感受目錄隔離。
3. 刪除一個 worktree，並確認對應任務是否被正確收尾。

讀完這一章，你應該能自己說清楚這句話：

**任務系統管“做什麼”，worktree 系統管“在哪做且互不干擾”。**
