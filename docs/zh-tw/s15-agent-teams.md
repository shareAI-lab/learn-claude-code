# s15: Agent Teams (智慧體團隊)

`s00 > s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > [ s15 ] > s16 > s17 > s18 > s19`

> *子 agent 適合一次性委派；團隊系統解決的是“有人長期線上、能繼續接活、能互相協作”。*

## 這一章要解決什麼問題

`s04` 的 subagent 已經能幫主 agent 拆小任務。

但 subagent 有一個很明顯的邊界：

```text
建立 -> 執行 -> 返回摘要 -> 消失
```

這很適合一次性的小委派。  
可如果你想做這些事，就不夠用了：

- 讓一個測試 agent 長期待命
- 讓兩個 agent 長期分工
- 讓某個 agent 未來收到新任務後繼續工作

也就是說，系統現在缺的不是“再開一個模型呼叫”，而是：

**一批有身份、能長期存在、能反覆協作的隊友。**

## 建議聯讀

- 如果你還在把 teammate 和 `s04` 的 subagent 混成一類，先回 [`entity-map.md`](./entity-map.md)。
- 如果你準備繼續讀 `s16-s18`，建議把 [`team-task-lane-model.md`](./team-task-lane-model.md) 放在手邊，它會把 teammate、protocol request、task、runtime slot、worktree lane 這五層一起拆開。
- 如果你開始懷疑“長期隊友”和“活著的執行槽位”到底是什麼關係，配合看 [`s13a-runtime-task-model.md`](./s13a-runtime-task-model.md)。

## 先把幾個詞講明白

### 什麼是隊友

這裡的 `teammate` 指的是：

> 一個擁有名字、角色、訊息入口和生命週期的持久 agent。

### 什麼是名冊

名冊就是團隊成員列表。

它回答的是：

- 現在隊伍裡有誰
- 每個人是什麼角色
- 每個人現在是空閒、工作中還是已關閉

### 什麼是郵箱

信箱就是每個隊友的收件匣。

別人把訊息發給它，  
它在自己的下一輪工作前先去收訊息。

## 最小心智模型

這一章最簡單的理解方式，是把每個隊友都想成：

> 一個有自己迴圈、自己收件箱、自己上下文的人。

```text
lead
  |
  +-- spawn alice (coder)
  +-- spawn bob (tester)
  |
  +-- send message --> alice inbox
  +-- send message --> bob inbox

alice
  |
  +-- 自己的 messages
  +-- 自己的 inbox
  +-- 自己的 agent loop

bob
  |
  +-- 自己的 messages
  +-- 自己的 inbox
  +-- 自己的 agent loop
```

和 `s04` 的最大區別是：

**subagent 是一次性執行單元，teammate 是長期存在的協作成員。**

## 關鍵資料結構

### 1. TeamMember

```python
member = {
    "name": "alice",
    "role": "coder",
    "status": "working",
}
```

教學版先只保留這 3 個欄位就夠了：

- `name`：名字
- `role`：角色
- `status`：狀態

### 2. TeamConfig

```python
config = {
    "team_name": "default",
    "members": [member1, member2],
}
```

它通常可以放在：

```text
.team/config.json
```

這份名冊讓系統重啟以後，仍然知道：

- 團隊裡曾經有誰
- 每個人當前是什麼角色

### 3. MessageEnvelope

```python
message = {
    "type": "message",
    "from": "lead",
    "content": "Please review auth module.",
    "timestamp": 1710000000.0,
}
```

`envelope` 這個詞本來是“信封”的意思。  
程式裡用它表示：

> 把訊息正文和元資訊一起包起來的一條記錄。

## 最小實現

### 第一步：先有一份隊伍名冊

```python
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.team_dir = team_dir
        self.config_path = team_dir / "config.json"
        self.config = self._load_config()
```

名冊是本章的起點。  
沒有名冊，就沒有真正的“團隊實體”。

### 第二步：spawn 一個持久隊友

```python
def spawn(self, name: str, role: str, prompt: str):
    member = {"name": name, "role": role, "status": "working"}
    self.config["members"].append(member)
    self._save_config()

    thread = threading.Thread(
        target=self._teammate_loop,
        args=(name, role, prompt),
        daemon=True,
    )
    thread.start()
```

這裡的關鍵不在於執行緒本身，而在於：

**隊友一旦被建立，就不只是一次性工具呼叫，而是一個有持續生命週期的成員。**

### 第三步：給每個隊友一個信箱

教學版最簡單的做法可以直接用 JSONL 檔案：

```text
.team/inbox/alice.jsonl
.team/inbox/bob.jsonl
```

發訊息時追加一行：

```python
def send(self, sender: str, to: str, content: str):
    with open(f"{to}.jsonl", "a") as f:
        f.write(json.dumps({
            "type": "message",
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }) + "\n")
```

收訊息時：

1. 讀出全部
2. 解析為訊息列表
3. 清空收件匣

### 第四步：隊友每輪先看郵箱，再繼續工作

```python
def teammate_loop(name: str, role: str, prompt: str):
    messages = [{"role": "user", "content": prompt}]

    while True:
        inbox = bus.read_inbox(name)
        for item in inbox:
            messages.append({"role": "user", "content": json.dumps(item)})

        response = client.messages.create(...)
        ...
```

這一步一定要講透。

因為它說明：

**隊友不是靠“被重新建立”來獲得新任務，而是靠“下一輪先檢查郵箱”來接收新工作。**

## 如何接到前面章節的系統裡

這章最容易出現的誤解是：

> 好像系統突然“多了幾個人”，但不知道這些人到底接在之前哪一層。

更準確的接法應該是：

```text
使用者目標 / lead 判斷需要長期分工
  ->
spawn teammate
  ->
寫入 .team/config.json
  ->
透過 inbox 分派訊息、摘要、任務線索
  ->
teammate 先 drain inbox
  ->
進入自己的 agent loop 和工具呼叫
  ->
把結果回送給 lead，或繼續等待下一輪工作
```

這裡要特別看清三件事：

1. `s12-s14` 已經給了你任務板、後臺執行、時間觸發這些“工作層”。
2. `s15` 現在補的是“長期執行者”，也就是誰長期線上、誰能反覆接活。
3. 本章還沒有進入“自己找活”或“自動認領”。

也就是說，`s15` 的預設工作方式仍然是：

- 由 lead 手動建立隊友
- 由 lead 透過郵箱分派事情
- 隊友在自己的迴圈裡持續處理

真正的自治認領，要到 `s17` 才展開。

## Teammate、Subagent、Runtime Task 到底怎麼區分

這是這一組章節裡最容易混的點。

可以直接記這張表：

| 機制 | 更像什麼 | 生命週期 | 關鍵邊界 |
|---|---|---|
| subagent | 一次性外包助手 | 幹完就結束 | 重點是“隔離一小段探索性上下文” |
| runtime task | 正在執行的後臺執行槽位 | 任務跑完或取消就結束 | 重點是“慢任務稍後回來”，不是長期身份 |
| teammate | 長期線上隊友 | 可以反覆接任務 | 重點是“有名字、有郵箱、有獨立迴圈” |

再換成更口語的話說：

- subagent 適合“幫我查一下再回來彙報”
- runtime task 適合“這件事你後臺慢慢跑，結果稍後通知我”
- teammate 適合“你以後長期負責測試方向”

## 這一章的教學邊界

本章先只把 3 件事講穩：

- 名冊
- 郵箱
- 獨立迴圈

這已經足夠把“長期隊友”這個實體立起來。

但它還沒有展開後面兩層能力：

### 第一層：結構化協議

也就是：

- 哪些訊息只是普通交流
- 哪些訊息是帶 `request_id` 的結構化請求

這部分放到下一章 `s16`。

### 第二層：自治認領

也就是：

- 隊友空閒時能不能自己找活
- 能不能自己恢復工作

這部分放到 `s17`。

## 初學者最容易犯的錯

### 1. 把隊友當成“名字不同的 subagent”

如果生命週期還是“執行完就銷燬”，那本質上還不是 teammate。

### 2. 隊友之間共用同一份 messages

這樣上下文會互相汙染。

每個隊友都應該有自己的對話狀態。

### 3. 沒有持久名冊

如果系統關掉以後完全不知道“團隊裡曾經有誰”，那就很難繼續做長期協作。

### 4. 沒有郵箱，靠共享變數直接喊話

教學上不建議一開始就這麼做。

因為它會把“隊友通訊”和“程序內部細節”綁得太死。

## 學完這一章，你應該真正掌握什麼

學完以後，你應該能獨立說清下面幾件事：

1. teammate 的核心不是“多一個模型呼叫”，而是“多一個長期存在的執行者”。
2. 團隊系統至少需要“名冊 + 郵箱 + 獨立迴圈”。
3. 每個隊友都應該有自己的 `messages` 和自己的 inbox。
4. subagent 和 teammate 的根本區別在生命週期，而不是名字。

如果這 4 點已經穩了，說明你已經真正理解了“多 agent 團隊”是怎麼從單 agent 演化出來的。

## 下一章學什麼

這一章解決的是：

> 團隊成員如何長期存在、互相發訊息。

下一章 `s16` 要解決的是：

> 當訊息不再只是自由聊天，而要變成可追蹤、可批准、可拒絕的協作流程時，該怎麼設計。

也就是從“有團隊”繼續走向“團隊協議”。
