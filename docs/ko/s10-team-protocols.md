# s10: 팀 프로토콜

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > [ s10 ] s11 > s12`

> *"팀원에게는 공통 통신 규약이 필요하다"* -- 하나의 request-response 패턴이 모든 협상을 끌고 갑니다.
>
> **하네스 레이어**: 프로토콜(Protocols) -- 모델 간의 구조화된 핸드셰이크.

## 문제

s09에서는 팀원들이 일을 하고 통신도 하지만, 구조화된 조율 수단이 부족합니다.

**셧다운(Shutdown)**: 스레드를 강제로 죽이면 파일이 반쯤 쓰인 상태로 남고 config.json이 낡은 상태가 됩니다. 핸드셰이크가 필요합니다. 리더가 요청을 보내면 팀원이 승인(작업을 마치고 종료)하거나 거부(작업을 계속함)할 수 있어야 합니다.

**플랜 승인(Plan approval)**: 리더가 "auth 모듈을 리팩터링해라"라고 말하면 팀원은 즉시 작업을 시작합니다. 위험도가 높은 변경에 대해서는 리더가 먼저 플랜을 검토해야 합니다.

두 시나리오는 같은 구조를 공유합니다. 한쪽이 고유 ID가 담긴 요청을 보내면, 다른 쪽이 그 ID를 참조해 응답합니다.

## 해결책

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

Shared FSM:
  [pending] --approve--> [approved]
  [pending] --reject---> [rejected]

Trackers:
  shutdown_requests = {req_id: {target, status}}
  plan_requests     = {req_id: {from, plan, status}}
```

## 동작 원리

1. 리더가 request_id를 생성하고 inbox로 전송하여 셧다운을 시작합니다.

```python
shutdown_requests = {}

def handle_shutdown_request(teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    BUS.send("lead", teammate, "Please shut down gracefully.",
             "shutdown_request", {"request_id": req_id})
    return f"Shutdown request {req_id} sent (status: pending)"
```

2. 팀원은 요청을 받고 승인 또는 거부로 응답합니다.

```python
if tool_name == "shutdown_response":
    req_id = args["request_id"]
    approve = args["approve"]
    shutdown_requests[req_id]["status"] = "approved" if approve else "rejected"
    BUS.send(sender, "lead", args.get("reason", ""),
             "shutdown_response",
             {"request_id": req_id, "approve": approve})
```

3. 플랜 승인도 완전히 동일한 패턴을 따릅니다. 팀원이 플랜을 제출하면서 request_id를 생성하고, 리더가 같은 request_id를 참조해 검토합니다.

```python
plan_requests = {}

def handle_plan_review(request_id, approve, feedback=""):
    req = plan_requests[request_id]
    req["status"] = "approved" if approve else "rejected"
    BUS.send("lead", req["from"], feedback,
             "plan_approval_response",
             {"request_id": request_id, "approve": approve})
```

하나의 FSM (FSM — Finite State Machine, 유한 상태 기계), 두 가지 적용. 동일한 `pending -> approved | rejected` state machine이 어떤 request-response 프로토콜이든 처리합니다.

## s09에서 무엇이 바뀌었나

| 구성 요소       | 이전 (s09)        | 이후 (s10)                    |
|----------------|-------------------|-------------------------------|
| 도구           | 9개               | 12개 (+shutdown_req/resp +plan)|
| 셧다운         | 자연 종료만 가능   | request-response 핸드셰이크   |
| 플랜 게이팅    | 없음              | 제출/검토와 승인               |
| 상관관계       | 없음              | 요청별 request_id              |
| FSM            | 없음              | pending -> approved/rejected   |

## 실행해 보기

```sh
cd learn-claude-code
python agents/s10_team_protocols.py
```

1. `Spawn alice as a coder. Then request her shutdown.`
2. `List teammates to see alice's status after shutdown approval`
3. `Spawn bob with a risky refactoring task. Review and reject his plan.`
4. `Spawn charlie, have him submit a plan, then approve it.`
5. `/team` 을 입력해 상태를 모니터링합니다
