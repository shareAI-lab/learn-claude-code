# s16: Team Protocols

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > [ s16 ] > s17 > s18 > s19`

## What You'll Learn
- How a request-response pattern with a tracking ID structures multi-agent negotiation
- How the shutdown protocol lets a lead gracefully stop a teammate
- How plan approval gates risky work behind a review step
- How one reusable FSM (a simple status tracker with defined transitions) covers both protocols

In s15 your teammates can send messages freely, but that freedom comes with chaos. One agent tells another "please stop," and the other ignores it. A teammate starts a risky database migration without asking first. The problem is not communication itself -- you solved that with inboxes -- but the lack of coordination rules. In this chapter you will add structured protocols: a standardized message wrapper with a tracking ID that turns loose messages into reliable handshakes.

## The Problem

Two coordination gaps become obvious once your team grows past toy examples:

**Shutdown.** Killing a teammate's thread leaves files half-written and the config roster stale. You need a handshake: the lead requests shutdown, and the teammate approves (finishes current work and exits cleanly) or rejects (keeps working because it has unfinished obligations).

**Plan approval.** When the lead says "refactor the auth module," the teammate starts immediately. But for high-risk changes, the lead should review the plan before any code gets written.

Both scenarios share an identical structure: one side sends a request carrying a unique ID, the other side responds referencing that same ID. That single pattern is enough to build any coordination protocol you need.

## The Solution

Both shutdown and plan approval follow one shape: send a request with a `request_id`, receive a response referencing that same `request_id`, and track the outcome through a simple status machine (`pending -> approved` or `pending -> rejected`).

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

## How It Works

**Step 1.** The lead initiates shutdown by generating a unique `request_id` and sending the request through the teammate's inbox. The request is tracked in a dictionary so the lead can check its status later.

```python
shutdown_requests = {}

def handle_shutdown_request(teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    BUS.send("lead", teammate, "Please shut down gracefully.",
             "shutdown_request", {"request_id": req_id})
    return f"Shutdown request {req_id} sent (status: pending)"
```

**Step 2.** The teammate receives the request in its inbox and responds with approve or reject. The response carries the same `request_id` so the lead can match it to the original request -- this is the correlation that makes the protocol reliable.

```python
if tool_name == "shutdown_response":
    req_id = args["request_id"]
    approve = args["approve"]
    shutdown_requests[req_id]["status"] = "approved" if approve else "rejected"
    BUS.send(sender, "lead", args.get("reason", ""),
             "shutdown_response",
             {"request_id": req_id, "approve": approve})
```

**Step 3.** Plan approval follows the identical pattern but in the opposite direction. The teammate submits a plan (generating a `request_id`), and the lead reviews it (referencing the same `request_id` to approve or reject).

```python
plan_requests = {}

def handle_plan_review(request_id, approve, feedback=""):
    req = plan_requests[request_id]
    req["status"] = "approved" if approve else "rejected"
    BUS.send("lead", req["from"], feedback,
             "plan_approval_response",
             {"request_id": request_id, "approve": approve})
```

In this teaching demo, one FSM shape covers both protocols. A production system might treat different protocol families differently, but the teaching version intentionally keeps one reusable template so you can see the shared structure clearly.

## Read Together

- If plain messages and protocol requests are starting to blur together, revisit [`glossary.md`](./glossary.md) and [`entity-map.md`](./entity-map.md) to see how they differ.
- If you plan to continue into s17 and s18, read [`team-task-lane-model.md`](./team-task-lane-model.md) first so autonomy and worktree lanes do not collapse into one idea.
- If you want to trace how a protocol request returns to the main system, pair this chapter with [`s00b-one-request-lifecycle.md`](./s00b-one-request-lifecycle.md).

## How It Plugs Into The Team System

The real upgrade in s16 is not "two new message types." It is a durable coordination path:

```text
requester starts a protocol action
  ->
write RequestRecord
  ->
send ProtocolEnvelope through inbox
  ->
receiver drains inbox on its next loop
  ->
update request status by request_id
  ->
send structured response
  ->
requester continues based on approved / rejected
```

That is the missing layer between "agents can chat" and "agents can coordinate reliably."

## Message vs Protocol vs Request vs Task

| Object | What question it answers | Typical fields |
|---|---|---|
| `MessageEnvelope` | who said what to whom | `from`, `to`, `content` |
| `ProtocolEnvelope` | is this a structured request / response | `type`, `request_id`, `payload` |
| `RequestRecord` | where is this coordination flow now | `kind`, `status`, `from`, `to` |
| `TaskRecord` | what actual work item is being advanced | `subject`, `status`, `blockedBy`, `owner` |

Do not collapse them:

- a protocol request is not the task itself
- the request store is not the task board
- protocols track coordination flow
- tasks track work progression

## What Changed From s15

| Component      | Before (s15)     | After (s16)                  |
|----------------|------------------|------------------------------|
| Tools          | 9                | 12 (+shutdown_req/resp +plan)|
| Shutdown       | Natural exit only| Request-response handshake   |
| Plan gating    | None             | Submit/review with approval  |
| Correlation    | None             | request_id per request       |
| FSM            | None             | pending -> approved/rejected |

## Try It

```sh
cd learn-claude-code
python agents/s16_team_protocols.py
```

1. `Spawn alice as a coder. Then request her shutdown.`
2. `List teammates to see alice's status after shutdown approval`
3. `Spawn bob with a risky refactoring task. Review and reject his plan.`
4. `Spawn charlie, have him submit a plan, then approve it.`
5. Type `/team` to monitor statuses

## What You've Mastered

At this point, you can:

- Build request-response protocols that use a unique ID for correlation
- Implement graceful shutdown through a two-step handshake
- Gate risky work behind a plan approval step
- Reuse a single FSM pattern (`pending -> approved/rejected`) for any new protocol you invent

## What's Next

Your team now has structure and rules, but the lead still has to babysit every teammate -- assigning tasks one by one, nudging idle workers. In s17, you will make teammates autonomous: they scan the task board themselves, claim unclaimed work, and resume after context compression without losing their identity.

## Key Takeaway

> A protocol request is a structured message with a tracking ID, and the response must reference that same ID -- that single pattern is enough to build any coordination handshake.
