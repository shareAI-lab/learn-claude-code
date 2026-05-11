# s09: 에이전트 팀

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > [ s09 ] s10 > s11 > s12`

> *"When the task is too big for one, delegate to teammates"* -- 영속적인 teammate + 비동기 mailbox (메일박스 — 에이전트가 메시지를 주고받는 파일 기반 큐).
>
> **Harness layer**: Team mailbox -- 여러 모델을 파일을 매개로 조율합니다.

## 문제

Subagent(s04)는 일회용입니다. spawn하고, 일을 하고, 요약을 반환한 뒤 사라집니다. 호출 사이에 정체성도, 기억도 남지 않습니다. Background task(s08)는 shell 명령을 돌릴 수는 있지만 LLM의 판단이 필요한 결정은 내리지 못합니다.

진짜 팀워크에는 다음이 필요합니다. (1) 하나의 prompt 수명을 넘어서 살아남는 영속적인 에이전트, (2) 정체성과 lifecycle 관리, (3) 에이전트 사이의 통신 채널.

## 해결책

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

## 동작 원리

1. TeammateManager는 team 명단을 담은 config.json을 관리합니다.

```python
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}
```

2. `spawn()`은 teammate를 생성하고 thread 위에서 그 에이전트 루프를 시작합니다.

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

3. MessageBus: append-only 방식의 JSONL (JSONL — 한 줄에 JSON 하나씩 적는 로그 포맷) inbox입니다. `send()`는 JSON 라인을 한 줄 추가하고, `read_inbox()`는 전부 읽은 뒤 비웁니다(drain).

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
        msgs = [json.loads(l) for l in path.read_text().strip().splitlines() if l]
        path.write_text("")  # drain
        return json.dumps(msgs, indent=2)
```

4. 각 teammate는 매 LLM 호출 직전에 자신의 inbox를 확인하고, 도착한 메시지를 context에 주입합니다.

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

## s08에서 무엇이 바뀌었나

| 구성 요소      | 이전 (s08)        | 이후 (s09)                       |
|----------------|-------------------|----------------------------------|
| Tools          | 6                 | 9 (+spawn/send/read_inbox)       |
| 에이전트       | 단일              | Lead + N teammate                |
| 영속성         | 없음               | config.json + JSONL inbox        |
| Thread         | Background 명령용 | thread당 전체 에이전트 루프      |
| Lifecycle      | 한 번 던지고 끝   | idle -> working -> idle          |
| 통신           | 없음               | message + broadcast              |

## 직접 해보기

```sh
cd learn-claude-code
python agents/s09_agent_teams.py
```

1. `Spawn alice (coder) and bob (tester). Have alice send bob a message.`
2. `Broadcast "status update: phase 1 complete" to all teammates`
3. `Check the lead inbox for any messages`
4. `/team`을 입력해 team roster와 status를 확인합니다.
5. `/inbox`를 입력해 lead의 inbox를 수동으로 확인합니다.
