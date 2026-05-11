# s11: 자율 에이전트 (Autonomous Agents)

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > [ s11 ] s12`

> *"팀원들이 보드를 스캔하고 태스크를 직접 가져간다"* -- 리더가 일일이 할당할 필요가 없습니다.
>
> **하네스 레이어**: 자율성(Autonomy) -- 지시받지 않아도 일을 찾아내는 모델.

## 문제

s09-s10에서는 팀원이 명시적으로 지시를 받았을 때만 일을 합니다. 리더가 매번 구체적인 프롬프트와 함께 팀원을 spawn해야 합니다. 보드에 미할당 태스크가 10개 있다면? 리더가 일일이 수동으로 할당해야 합니다. 확장성이 없습니다.

진짜 자율성은 이런 것입니다. 팀원이 직접 task board를 scan하고, 미할당 태스크를 claim하고, 그 일을 처리한 뒤 다음 일을 찾아 나섭니다.

한 가지 미묘한 문제가 있습니다. 컨텍스트 압축(s06) 이후 에이전트가 자기 정체성을 잊어버릴 수 있다는 것입니다. 정체성(identity) 재주입으로 이를 해결합니다.

## 해결책

```
Teammate lifecycle with idle cycle:

+-------+
| spawn |
+---+---+
    |
    v
+-------+   tool_use     +-------+
| WORK  | <------------- |  LLM  |
+---+---+                +-------+
    |
    | stop_reason != tool_use (or idle tool called)
    v
+--------+
|  IDLE  |  poll every 5s for up to 60s
+---+----+
    |
    +---> check inbox --> message? ----------> WORK
    |
    +---> scan .tasks/ --> unclaimed? -------> claim -> WORK
    |
    +---> 60s timeout ----------------------> SHUTDOWN

Identity re-injection after compression:
  if len(messages) <= 3:
    messages.insert(0, identity_block)
```

## 동작 원리

1. 팀원 루프는 두 단계로 구성됩니다. WORK와 IDLE입니다. LLM이 도구 호출을 멈추거나(또는 `idle` 도구를 호출하면), 팀원은 IDLE 상태로 들어갑니다.

```python
def _loop(self, name, role, prompt):
    while True:
        # -- WORK PHASE --
        messages = [{"role": "user", "content": prompt}]
        for _ in range(50):
            response = client.messages.create(...)
            if response.stop_reason != "tool_use":
                break
            # execute tools...
            if idle_requested:
                break

        # -- IDLE PHASE --
        self._set_status(name, "idle")
        resume = self._idle_poll(name, messages)
        if not resume:
            self._set_status(name, "shutdown")
            return
        self._set_status(name, "working")
```

2. idle 단계에서는 inbox와 task board를 루프 안에서 poll합니다.

```python
def _idle_poll(self, name, messages):
    for _ in range(IDLE_TIMEOUT // POLL_INTERVAL):  # 60s / 5s = 12
        time.sleep(POLL_INTERVAL)
        inbox = BUS.read_inbox(name)
        if inbox:
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
            return True
        unclaimed = scan_unclaimed_tasks()
        if unclaimed:
            claim_task(unclaimed[0]["id"], name)
            messages.append({"role": "user",
                "content": f"<auto-claimed>Task #{unclaimed[0]['id']}: "
                           f"{unclaimed[0]['subject']}</auto-claimed>"})
            return True
    return False  # timeout -> shutdown
```

3. task board 스캐닝: pending이면서 소유자가 없고 차단되지 않은 태스크를 찾습니다.

```python
def scan_unclaimed_tasks() -> list:
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        task = json.loads(f.read_text())
        if (task.get("status") == "pending"
                and not task.get("owner")
                and not task.get("blockedBy")):
            unclaimed.append(task)
    return unclaimed
```

4. 정체성 재주입: 컨텍스트가 지나치게 짧아졌다면(압축이 일어났다는 신호) 정체성 블록을 삽입합니다.

```python
if len(messages) <= 3:
    messages.insert(0, {"role": "user",
        "content": f"<identity>You are '{name}', role: {role}, "
                   f"team: {team_name}. Continue your work.</identity>"})
    messages.insert(1, {"role": "assistant",
        "content": f"I am {name}. Continuing."})
```

## s10에서 무엇이 바뀌었나

| 구성 요소       | 이전 (s10)        | 이후 (s11)                  |
|----------------|-------------------|-----------------------------|
| 도구           | 12개              | 14개 (+idle, +claim_task)   |
| 자율성         | 리더 주도          | 자기 조직화                  |
| idle 단계      | 없음              | inbox + task board를 poll   |
| 태스크 claim   | 수동만 가능        | 미할당 태스크를 자동 claim   |
| 정체성         | 시스템 프롬프트    | + 압축 이후 재주입           |
| timeout        | 없음              | 60초 idle -> 자동 셧다운     |

## 실행해 보기

```sh
cd learn-claude-code
python agents/s11_autonomous_agents.py
```

1. `Create 3 tasks on the board, then spawn alice and bob. Watch them auto-claim.`
2. `Spawn a coder teammate and let it find work from the task board itself`
3. `Create tasks with dependencies. Watch teammates respect the blocked order.`
4. `/tasks` 를 입력하면 소유자가 포함된 task board를 볼 수 있습니다
5. `/team` 을 입력해 누가 일하고 누가 idle 상태인지 모니터링합니다
