# s08: Background Tasks

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > [ s08 ] s09 > s10 > s11 > s12`

> *"Запускай медленные операции в background; agent продолжает думать"* -- потоки-демоны выполняют команды и уведомляют о завершении.
>
> **Harness layer**: Фоновое выполнение -- model думает, пока harness ждёт.

## Проблема

Некоторые команды выполняются минутами: `npm install`, `pytest`, `docker build`. При блокирующем loop model простаивает в ожидании. Если пользователь просит «установи зависимости и пока они устанавливаются, создай конфигурационный файл», agent выполняет задачи последовательно, а не параллельно.

## Решение

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

## Как это работает

1. BackgroundManager отслеживает task с потокобезопасной очередью уведомлений.

```python
class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self._notification_queue = []
        self._lock = threading.Lock()
```

2. `run()` запускает поток-демон и немедленно возвращает управление.

```python
def run(self, command: str) -> str:
    task_id = str(uuid.uuid4())[:8]
    self.tasks[task_id] = {"status": "running", "command": command}
    thread = threading.Thread(
        target=self._execute, args=(task_id, command), daemon=True)
    thread.start()
    return f"Background task {task_id} started"
```

3. Когда подпроцесс завершается, его результат помещается в очередь уведомлений.

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

4. agent loop опустошает очередь уведомлений перед каждым вызовом LLM.

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

loop остаётся однопоточным. Параллелизируется только ввод-вывод подпроцессов.

## Что изменилось по сравнению с s07

| Компонент      | До (s07)         | После (s08)                |
|----------------|------------------|----------------------------|
| Tools          | 8                | 6 (base + background_run + check)|
| Выполнение     | Только блокирующее | Блокирующее + background-потоки|
| Уведомления    | Отсутствуют      | Очередь, опустошаемая за loop|
| Параллелизм    | Отсутствует      | Потоки-демоны              |

## Попробуй сам

```sh
cd learn-claude-code
python agents/s08_background_tasks.py
```

1. `Run "sleep 5 && echo done" in the background, then create a file while it runs`
2. `Start 3 background tasks: "sleep 2", "sleep 4", "sleep 6". Check their status.`
3. `Run pytest in the background and keep working on other things`
