# s16: Team Protocols — Teammates Need Agreements

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

s01 → ... → s14 → s15 → `s16` → [s17](../s17_autonomous_agents/) → s18 → s19 → s20
> *"Teammates need agreements"* — request-response pattern drives all negotiation.
>
> **Harness Layer**: Protocols — Structured handshakes between agents.

---

## The Problem

s15's teammates can work, but coordination is loose: Lead sends a message, teammate replies, no structured protocol. Two scenarios expose the gap:

**Shutdown**: Lead wants Alice to shut down. Killing the thread outright leaves half-written files on disk. A handshake is needed: Lead sends a request, Alice confirms after wrapping up.

**Plan approval**: Bob wants to refactor the auth module, a high-risk operation. Lead should review Bob's plan first, approve before Bob proceeds.

Both scenarios share the same structure: one side sends a request, the other replies, both linked by the same ID. A state machine tracks: pending → approved / rejected.

---

## The Solution

![Team Protocols Overview](images/team-protocols-overview.en.svg)

Teaching code continues the agent capability arc from earlier chapters and adds structured protocols on top of S15's team communication. To stay focused on the protocol mechanism, it omits full error recovery, memory, and skill systems. Added: **ProtocolState** (request state tracking), **dispatch_message** (routes incoming messages by type to handlers), **match_response** (correlates response to request via request_id, with type validation).

Two protocols, one mechanism:

| Protocol | Direction | Purpose |
|----------|-----------|---------|
| shutdown_request / response | Lead → Teammate | Graceful shutdown handshake |
| plan_approval_request / response | Teammate → Lead | Plan approval protocol example |

> Teaching version demonstrates the request-response message flow for plan approval, but does not implement execution gating (intercepting bash/write_file when not approved). Real CC has a permission gating mechanism for teammates.

---

## How It Works

### ProtocolState: Request State

Each protocol request creates a state record tracking who sent it, to whom, current status, and payload:

```python
@dataclass
class ProtocolState:
    request_id: str      # Unique ID, e.g. "req_004281"
    type: str            # "shutdown" | "plan_approval"
    sender: str          # Sender
    target: str          # Recipient
    status: str          # pending | approved | rejected
    payload: str         # Plan text or shutdown reason
    created_at: float    # Timestamp

pending_requests: dict[str, ProtocolState] = {}
```

A record is created when sending a request, found via `request_id` when receiving a response, and its status updated.

### Four-Step Protocol Flow

Using shutdown as an example, the full chain:

```
1. Lead sends request
   req_id = new_request_id()           # "req_004281"
   pending_requests[req_id] = ProtocolState(type="shutdown", status="pending", ...)
   BUS.send("lead", "alice", "shutdown_request", metadata={"request_id": req_id})

2. Teammate receives → dispatch
   inbox = BUS.read_inbox("alice")
   msg_type = msg["type"]              # "shutdown_request"
   → routed to handle_shutdown_request()

3. Teammate replies
   BUS.send("alice", "lead", "shutdown_response",
            metadata={"request_id": req_id, "approve": True})

4. Lead receives response → match
   match_response("shutdown_response", req_id, approve=True)
   pending_requests[req_id].status = "approved"
```

`request_id` is the correlation key across the entire chain: the request carries it out, the response carries it back.

### dispatch_message: Route by Type

A teammate's inbox receives both plain messages and protocol messages. `handle_inbox_message` dispatches by message type:

```python
def handle_inbox_message(name, msg, messages):
    msg_type = msg.get("type", "message")
    req_id = msg.get("metadata", {}).get("request_id", "")

    if msg_type == "shutdown_request":
        BUS.send(name, "lead", "Shutting down.", "shutdown_response",
                 {"request_id": req_id, "approve": True})
        return True   # Stop the loop

    if msg_type == "plan_approval_response":
        approve = msg["metadata"].get("approve", False)
        messages.append({"role": "user",
            "content": "[Plan approved]" if approve else "[Plan rejected]"})
    return False       # Continue
```

Adding a new protocol type means adding a new `if` branch.

### match_response: Type Validation

`match_response` doesn't just find state by `request_id`, it also validates that the response type matches the request type:

```python
def match_response(response_type, request_id, approve):
    state = pending_requests.get(request_id)
    if not state:
        return
    if state.type == "shutdown" and response_type != "shutdown_response":
        return  # type mismatch, skip
    if state.type == "plan_approval" and response_type != "plan_approval_response":
        return
    if state.status != "pending":
        return  # already resolved, skip duplicate
    state.status = "approved" if approve else "rejected"
```

A shutdown_response cannot accidentally approve a plan_approval request.

### Unified Inbox Consumer: consume_lead_inbox

Both the `check_inbox` tool and the main loop call the same `consume_lead_inbox()` function, routing protocol messages before returning remaining content. This prevents messages from being consumed without protocol state updates:

```python
def consume_lead_inbox(route_protocol=True) -> list[dict]:
    msgs = BUS.read_inbox("lead")
    if route_protocol:
        for msg in msgs:
            meta = msg.get("metadata", {})
            req_id = meta.get("request_id", "")
            msg_type = msg.get("type", "")
            if req_id and msg_type.endswith("_response"):
                match_response(msg_type, req_id, meta.get("approve", False))
    return msgs
```

The main loop also injects inbox messages into `history` so the LLM can see and react to them.

### Teammate Idle Loop: Wait Instead of Exit

s15's teammates exit after 10 rounds. s16's teammates enter idle waiting after the LLM returns a non-tool_use response: poll inbox, respond to shutdown_request and exit, or continue working on new messages.

```
LLM returns non-tool_use
  → idle: poll inbox every second
  → receives shutdown_request → reply shutdown_response → exit
  → receives new message → inject into messages → continue LLM turn
```

Teaching version omits idle_notification to Lead. Real CC sends `idle_notification` when idle, so Lead knows the teammate is free for new tasks.

### Putting It Together

```
1. Lead: "Have Alice create a file, then shut her down"
2. Lead → spawn_teammate("alice", "backend", "Create config.py")
3. alice thread starts → write_file("config.py", "...") → done → idle
4. Lead → request_shutdown("alice")
   → BUS.send("shutdown_request", {request_id: "req_000142"})
5. alice idle poll receives → handle_shutdown_request
   → BUS.send("shutdown_response", {request_id: "req_000142", approve: True})
6. Lead consume_lead_inbox → match_response("req_000142", approve=True)
   → pending_requests["req_000142"].status = "approved"
   → inbox message injected into history, LLM sees shutdown result
```

Shutdown handshake complete: request → confirm → shutdown. Every step tracked by `request_id`.

---

## Changes from s15

| Component | Before (s15) | After (s16) |
|-----------|-------------|-------------|
| Coordination | Loose text messages | Structured request-response protocol |
| Request tracking | None | ProtocolState + pending_requests dict |
| Message routing | All treated as text | dispatch_message routes by type |
| Shutdown | Natural exit or kill thread | request_id handshake mechanism |
| Plan approval | None | Message flow example (no execution gating) |
| New message types | message, result | + shutdown_request/response, plan_approval_request/response |
| Teammate lifecycle | Max 10 rounds | Idle loop (waits for inbox messages) |
| Lead inbox | check_inbox and main loop read separately | Unified consume_lead_inbox |
| Lead tools | 14 (s15) | 14 (core tool set plus request_shutdown, request_plan, review_plan) |
| Teammate tools | 4 (s15) | + submit_plan (5) |

---

## Try It

```sh
cd learn-claude-code
python s16_team_protocols/code.py
```

Try these prompts:

1. `Spawn alice as a backend dev. Ask her to create a file. Then request her shutdown.`
2. `Spawn bob with a refactoring task. Have him submit a plan first. Then review and approve it.`

What to observe: Is the shutdown handshake complete (request → confirm → shutdown)? Does `pending_requests` state transition correctly? Is `request_id` consistent between request and response? Can the idle teammate receive shutdown_request?

---

## What's Next

In s15-s16, Lead must assign tasks to each teammate. "Alice does this, Bob does that." With 10 unclaimed tasks on the board, Lead has to manually assign each one.

What if teammates could check the board and claim tasks themselves? Lead only needs to create tasks; teammates discover, claim, and complete them on their own.

s17 Autonomous Agents → Self-organizing teammates, no leader assignment needed.

<details>
<summary>Deep Dive into CC Source</summary>

CC's team protocol implementation (`teammateMailbox.ts`, 1184 lines) shares the same core structure as the teaching version: request_id + approve/reject request-response pattern. Differences:

**Shutdown protocol**: CC's shutdown is three-way communication (`teammateMailbox.ts:720-763`, `SendMessageTool.ts:268-430`). Lead sends `shutdown_request`, teammate replies `shutdown_approved` (or `shutdown_rejected` with reason), system sends `teammate_terminated` to notify all parties. After confirmation, system cleans up pane (tmux/iTerm2), unassigns tasks, removes member from team config (`useInboxPoller.ts:677-800`). Teaching version uses `shutdown_response` as a unified name; real source splits into `shutdown_approved` and `shutdown_rejected` as two separate message types.

**Plan approval**: In the real source, plan approval request is generated by `ExitPlanModeV2Tool.ts:263-312` when a plan-mode-required teammate exits plan mode. `useInboxPoller.ts:599-661` currently auto-writes approval and passes the request to Lead as context (regular message). `SendMessageTool.ts:434-518` retains explicit approve/reject response capability — approval can simultaneously set `permissionMode` (e.g. "approved but run in plan mode"), response can include `feedback` string for teammate to revise and resubmit. Not a simple "Lead manually uses review_plan tool" flow.

**Message format**: CC's protocol messages are structured JSON (with Zod schema validation), teaching version uses simple type + metadata dict. Field names are also inconsistent: permission uses `request_id` (`teammateMailbox.ts:453-462`), shutdown and plan approval use `requestId` (`teammateMailbox.ts:684-763`).

**Execution gating**: CC's teammates have full permission gating. Unapproved high-risk operations are intercepted, not optional. Teaching version only demonstrates the message flow without execution interception.

**Generality**: Teaching version's single FSM (pending → approved | rejected) maps to two protocols. This simplification is correct. CC's protocol messages all share the same request id correlation mechanism.

</details>

<!-- translation-sync: zh@v1, en@v1, ja@v1 -->
