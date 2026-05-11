# s08: 백그라운드 태스크

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > [ s08 ] s09 > s10 > s11 > s12`

> *"Run slow operations in the background; the agent keeps thinking"* -- daemon thread (데몬 스레드 — 백그라운드에서 도는 보조 스레드)가 명령을 실행하고, 완료 시 notification을 주입합니다.
>
> **Harness layer**: Background 실행 -- harness가 기다리는 동안 모델은 계속 사고합니다.

## 문제

어떤 명령은 분 단위로 시간이 걸립니다. `npm install`, `pytest`, `docker build` 같은 것들이죠. 블로킹 루프에서는 모델이 그 시간 동안 멍하니 기다리기만 합니다. 사용자가 "의존성을 설치하고, 그게 도는 동안 config 파일을 만들어 줘"라고 요청하면, 에이전트는 이를 병렬이 아닌 순차적으로 처리해 버립니다.

## 해결책

```
Main thread                Background thread
+-----------------+        +-----------------+
| agent loop      |        | subprocess runs |
| ...             |        | ...             |
| [LLM call] <---+------- | enqueue(result) |
|  ^drain queue   |        +-----------------+
+-----------------+

Timeline:
Agent --[spawn A]--[spawn B]--[other work]----
             |          |
             v          v
          [A runs]   [B runs]      (parallel)
             |          |
             +-- results injected before next LLM call --+
```

## 동작 원리

1. BackgroundManager는 thread-safe한 notification queue로 task를 추적합니다.

```python
class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self._notification_queue = []
        self._lock = threading.Lock()
```

2. `run()`은 daemon thread를 시작한 뒤 즉시 반환합니다.

```python
def run(self, command: str) -> str:
    task_id = str(uuid.uuid4())[:8]
    self.tasks[task_id] = {"status": "running", "command": command}
    thread = threading.Thread(
        target=self._execute, args=(task_id, command), daemon=True)
    thread.start()
    return f"Background task {task_id} started"
```

3. subprocess가 종료되면, 그 결과가 notification queue로 들어갑니다.

```python
def _execute(self, task_id, command):
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
            capture_output=True, text=True, timeout=300)
        output = (r.stdout + r.stderr).strip()[:50000]
    except subprocess.TimeoutExpired:
        output = "Error: Timeout (300s)"
    with self._lock:
        self._notification_queue.append({
            "task_id": task_id, "result": output[:500]})
```

4. 에이전트 루프는 매 LLM 호출 직전에 notification을 비웁니다(drain).

```python
def agent_loop(messages: list):
    while True:
        notifs = BG.drain_notifications()
        if notifs:
            notif_text = "\n".join(
                f"[bg:{n['task_id']}] {n['result']}" for n in notifs)
            messages.append({"role": "user",
                "content": f"<background-results>\n{notif_text}\n"
                           f"</background-results>"})
        response = client.messages.create(...)
```

루프 자체는 single-thread를 유지합니다. 병렬화되는 것은 subprocess I/O 뿐입니다.

## s07에서 무엇이 바뀌었나

| 구성 요소      | 이전 (s07)       | 이후 (s08)                       |
|----------------|------------------|----------------------------------|
| Tools          | 8                | 6 (base + background_run + check)|
| 실행 방식      | 블로킹만          | 블로킹 + background thread      |
| Notification   | 없음              | 루프마다 queue를 drain          |
| 동시성         | 없음              | Daemon thread                    |

## 직접 해보기

```sh
cd learn-claude-code
python agents/s08_background_tasks.py
```

1. `Run "sleep 5 && echo done" in the background, then create a file while it runs`
2. `Start 3 background tasks: "sleep 2", "sleep 4", "sleep 6". Check their status.`
3. `Run pytest in the background and keep working on other things`
