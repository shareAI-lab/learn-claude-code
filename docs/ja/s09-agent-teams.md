# s09: Agent Teams

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > [ s09 ] s10 > s11 > s12`

> *"一人で終わらないなら、チームメイトに任せる"* -- 永続チームメイト + 非同期メールボックス。
>
> **Harness 層**: チームメールボックス -- 複数モデルをファイルで協調。

## 問題

サブエージェント(s04)は使い捨てだ: 生成し、作業し、要約を返し、消滅する。アイデンティティもなく、呼び出し間の記憶もない。バックグラウンドタスク(s08)はシェルコマンドを実行するが、LLM誘導の意思決定はできない。

本物のチームワークには: (1)単一プロンプトを超えて存続する永続エージェント、(2)アイデンティティとライフサイクル管理、(3)エージェント間の通信チャネルが必要だ。

## 解決策

```
Teammate lifecycle:
  spawn -> WORKING -> IDLE -> WORKING -> ... -> SHUTDOWN

Communication:
  .team/
    config.json           <- team roster + statuses
    inbox/
      alice.jsonl         <- append-only, drain-on-read
      bob.jsonl
      lead.jsonl

              +--------+    send("alice","bob","...")    +--------+
              | alice  | -----------------------------> |  bob   |
              | loop   |    bob.jsonl << {json_line}    |  loop  |
              +--------+                                +--------+
                   ^                                         |
                   |        BUS.read_inbox("alice")          |
                   +---- alice.jsonl -> read + drain ---------+
```

## 仕組み

1. TeammateManagerがconfig.jsonでチーム名簿を管理する。

```python
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}
```

2. `spawn()`がチームメイトを作成し、そのエージェントループをスレッドで開始する。

```python
def spawn(self, name: str, role: str, prompt: str) -> str:
    member = {"name": name, "role": role, "status": "working"}
    self.config["members"].append(member)
    self._save_config()
    thread = threading.Thread(
        target=self._teammate_loop,
        args=(name, role, prompt), daemon=True)
    thread.start()
    return f"Spawned teammate '{name}' (role: {role})"
```

3. MessageBus: 追記専用のJSONLインボックス。`send()`がJSON行を追記し、`read_inbox()`がすべて読み取ってドレインする。

```python
class MessageBus:
    def send(self, sender, to, content, msg_type="message", extra=None):
        msg = {"type": msg_type, "from": sender,
               "content": content, "timestamp": time.time()}
        if extra:
            msg.update(extra)
        with open(self.dir / f"{to}.jsonl", "a") as f:
            f.write(json.dumps(msg) + "\n")

    def read_inbox(self, name):
        path = self.dir / f"{name}.jsonl"
        if not path.exists(): return "[]"
        msgs = [json.loads(l) for l in path.read_text(encoding="utf-8").strip().splitlines() if l]
        path.write_text("", encoding="utf-8")  # drain
        return json.dumps(msgs, indent=2)
```

4. 各チームメイトは各LLM呼び出しの前にインボックスを確認し、受信メッセージをコンテキストに注入する。

```python
def _teammate_loop(self, name, role, prompt):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(50):
        inbox = BUS.read_inbox(name)
        if inbox != "[]":
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
        response = client.messages.create(...)
        if response.stop_reason != "tool_use":
            break
        # execute tools, append results...
    self._find_member(name)["status"] = "idle"
```

## s08からの変更点

| Component      | Before (s08)     | After (s09)                |
|----------------|------------------|----------------------------|
| Tools          | 6                | 9 (+spawn/send/read_inbox) |
| Agents         | Single           | Lead + N teammates         |
| Persistence    | None             | config.json + JSONL inboxes|
| Threads        | Background cmds  | Full agent loops per thread|
| Lifecycle      | Fire-and-forget  | idle -> working -> idle    |
| Communication  | None             | message + broadcast        |

## 試してみる

```sh
cd learn-claude-code
python agents/s09_agent_teams.py
```

1. `Spawn alice (coder) and bob (tester). Have alice send bob a message.`
2. `Broadcast "status update: phase 1 complete" to all teammates`
3. `Check the lead inbox for any messages`
4. `/team`と入力してステータス付きのチーム名簿を確認する
5. `/inbox`と入力してリーダーのインボックスを手動確認する
