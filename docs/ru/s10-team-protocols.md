# s10: Team Protocols

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > [ s10 ] s11 > s12`

> *"Коллегам нужны общие правила коммуникации"* -- один паттерн запрос-ответ управляет всеми переговорами.
>
> **Harness layer**: Protocol-ы -- структурированные handshake-и между model-ями.

## Проблема

В s09 коллеги работают и общаются, но им не хватает структурированной координации:

**Завершение работы**: Принудительное завершение потока оставляет файлы недозаписанными, а config.json устаревшим. Нужен handshake: лид запрашивает, коллега соглашается (завершить и выйти) или отказывает (продолжать работу).

**Согласование плана**: Когда лид говорит «отрефакторь модуль аутентификации», коллега сразу приступает. Для высокорисковых изменений лид должен сначала проверить план.

Оба случая имеют одинаковую структуру: одна сторона отправляет запрос с уникальным ID, другая отвечает, ссылаясь на этот же ID.

## Решение

```
Shutdown Protocol            Plan Approval Protocol
==================           ======================

Lead             Teammate    Teammate           Lead
  |                 |           |                 |
  |--shutdown_req-->|           |--plan_req------>|
  | {req_id:"abc"}  |           | {req_id:"xyz"}  |
  |                 |           |                 |
  |<--shutdown_resp-|           |<--plan_resp-----|
  | {req_id:"abc",  |           | {req_id:"xyz",  |
  |  approve:true}  |           |  approve:true}  |

Общий FSM:
  [pending] --approve--> [approved]
  [pending] --reject---> [rejected]

Трекеры:
  shutdown_requests = {req_id: {target, status}}
  plan_requests     = {req_id: {from, plan, status}}
```

## Как это работает

1. Лид инициирует завершение работы, генерируя request_id и отправляя его через inbox.

```python
shutdown_requests = {}

def handle_shutdown_request(teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    BUS.send("lead", teammate, "Please shut down gracefully.",
             "shutdown_request", {"request_id": req_id})
    return f"Shutdown request {req_id} sent (status: pending)"
```

2. Коллега получает запрос и отвечает — approve или reject.

```python
if tool_name == "shutdown_response":
    req_id = args["request_id"]
    approve = args["approve"]
    shutdown_requests[req_id]["status"] = "approved" if approve else "rejected"
    BUS.send(sender, "lead", args.get("reason", ""),
             "shutdown_response",
             {"request_id": req_id, "approve": approve})
```

3. Согласование плана следует идентичному паттерну. Коллега отправляет план (генерируя request_id), лид проверяет (ссылаясь на тот же request_id).

```python
plan_requests = {}

def handle_plan_review(request_id, approve, feedback=""):
    req = plan_requests[request_id]
    req["status"] = "approved" if approve else "rejected"
    BUS.send("lead", req["from"], feedback,
             "plan_approval_response",
             {"request_id": request_id, "approve": approve})
```

Один FSM, два применения. Одна и та же машина состояний `pending -> approved | rejected` обслуживает любой protocol запрос-ответ.

## Что изменилось по сравнению с s09

| Компонент      | До (s09)         | После (s10)                  |
|----------------|------------------|------------------------------|
| Tool-ы         | 9                | 12 (+shutdown_req/resp +plan)|
| Завершение     | Естественный выход| Handshake запрос-ответ      |
| Контроль плана | Нет              | Отправка/проверка с согласованием|
| Корреляция     | Нет              | request_id для каждого запроса|
| FSM            | Нет              | pending -> approved/rejected |

## Попробуй сам

```sh
cd learn-claude-code
python agents/s10_team_protocols.py
```

1. `Spawn alice as a coder. Then request her shutdown.`
2. `List teammates to see alice's status after shutdown approval`
3. `Spawn bob with a risky refactoring task. Review and reject his plan.`
4. `Spawn charlie, have him submit a plan, then approve it.`
5. Введи `/team`, чтобы следить за статусами
