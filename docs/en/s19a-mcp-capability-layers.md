# s19a: MCP Capability Layers

> **Deep Dive** -- Best read alongside s19. It shows that MCP is more than just external tools.

### When to Read This

After reading s19's tools-first approach, when you're ready to see the full MCP capability stack.

---

> `s19` should still keep a tools-first mainline.
> This bridge note adds the second mental model:
>
> **MCP is not only external tool access. It is a stack of capability layers.**

## How to Read This with the Mainline

If you want to study MCP without drifting away from the teaching goal:

- read [`s19-mcp-plugin.md`](./s19-mcp-plugin.md) first and keep the tools-first path clear
- then you might find it helpful to revisit [`s02a-tool-control-plane.md`](./s02a-tool-control-plane.md) to see how external capability routes back into the unified tool bus
- if state records begin to blur, you might find it helpful to revisit [`data-structures.md`](./data-structures.md)
- if concept boundaries blur, you might find it helpful to revisit [`glossary.md`](./glossary.md) and [`entity-map.md`](./entity-map.md)

## Why This Deserves a Separate Bridge Note

For a teaching repo, keeping the mainline focused on external tools first is correct.

That is the easiest entry:

- connect an external server
- receive tool definitions
- call a tool
- bring the result back into the agent

But if you want the system shape to approach real high-completion behavior, you quickly meet deeper questions:

- is the server connected through stdio, HTTP, SSE, or WebSocket
- why are some servers `connected`, while others are `pending` or `needs-auth`
- where do resources and prompts fit relative to tools
- why does elicitation become a special kind of interaction
- where should OAuth or other auth flows be placed conceptually

Without a capability-layer map, MCP starts to feel scattered.

## Terms First

### What capability layers means

A capability layer is simply:

> one responsibility slice in a larger system

The point is to avoid mixing every MCP concern into one bag.

### What transport means

Transport is the connection channel between your agent and an MCP server:

- stdio (standard input/output, good for local processes)
- HTTP
- SSE (Server-Sent Events, a one-way streaming protocol over HTTP)
- WebSocket

### What elicitation means

This is one of the less familiar terms.

A simple teaching definition is:

> an interaction where the MCP server asks the user for more input before it can continue

So the system is no longer only:

> agent calls tool -> tool returns result

The server can also say:

> I need more information before I can finish

This turns a simple call-and-return into a multi-step conversation between the agent and the server.

## The Minimum Mental Model

A clear six-layer picture:

```text
1. Config Layer
   what the server configuration looks like

2. Transport Layer
   how the server connection is carried

3. Connection State Layer
   connected / pending / failed / needs-auth

4. Capability Layer
   tools / resources / prompts / elicitation

5. Auth Layer
   whether authentication is required and what state it is in

6. Router Integration Layer
   how MCP routes back into tool routing, permissions, and notifications
```

The key lesson is:

**tools are one layer, not the whole MCP story**

## Why the Mainline Should Still Stay Tools-First

This matters a lot for teaching.

Even though MCP contains multiple layers, the chapter mainline should still teach:

### Step 1: external tools first

Because that connects most naturally to everything you already learned:

- local tools
- external tools
- one shared router

### Step 2: show that more capability layers exist

For example:

- resources
- prompts
- elicitation
- auth

### Step 3: decide which advanced layers the repo should actually implement

That matches the teaching goal:

**build the similar system first, then add the heavier platform layers**

## Core Records

### 1. `ScopedMcpServerConfig`

Even a minimal teaching version should expose this idea:

```python
config = {
    "name": "postgres",
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "..."],
    "scope": "project",
}
```

`scope` matters because server configuration may come from different places (global user settings, project-level settings, or even per-workspace overrides).

### 2. MCP connection state

```python
server_state = {
    "name": "postgres",
    "status": "connected",   # pending / failed / needs-auth / disabled
    "config": {...},
}
```

### 3. `MCPToolSpec`

```python
tool = {
    "name": "mcp__postgres__query",
    "description": "...",
    "input_schema": {...},
}
```

### 4. `ElicitationRequest`

```python
request = {
    "server_name": "some-server",
    "message": "Please provide additional input",
    "requested_schema": {...},
}
```

The teaching point is not that you need to implement elicitation immediately.

The point is:

**MCP is not guaranteed to stay a one-way tool invocation forever**

## The Cleaner Platform Picture

```text
MCP Config
  |
  v
Transport
  |
  v
Connection State
  |
  +-- connected
  +-- pending
  +-- needs-auth
  +-- failed
  |
  v
Capabilities
  +-- tools
  +-- resources
  +-- prompts
  +-- elicitation
  |
  v
Router / Permission / Notification Integration
```

## Why Auth Should Not Dominate the Chapter Mainline

Auth is a real layer in the full platform.

But if the mainline falls into OAuth or vendor-specific auth flow details too early, beginners lose the actual system shape.

A better teaching order is:

- first explain that an auth layer exists
- then explain that `connected` and `needs-auth` are different connection states
- only later, in advanced platform work, expand the full auth state machine

That keeps the repo honest without derailing your learning path.

## How This Relates to `s19` and `s02a`

- the `s19` chapter keeps teaching the tools-first external capability path
- this note supplies the broader platform map
- `s02a` explains how MCP capability eventually reconnects to the unified tool control plane

Together, they teach the actual idea:

**MCP is an external capability platform, and tools are only the first face of it that enters the mainline**

## Common Beginner Mistakes

### 1. Treating MCP as only an external tool catalog

That makes resources, prompts, auth, and elicitation feel surprising later.

### 2. Diving into transport or OAuth details too early

That breaks the teaching mainline.

### 3. Letting MCP tools bypass permission checks

That opens a dangerous side door in the system boundary.

### 4. Mixing server config, connection state, and exposed capabilities into one blob

Those layers should stay conceptually separate.

## Key Takeaway

**MCP is a six-layer capability platform. Tools are the first layer you build, but resources, prompts, elicitation, auth, and router integration are all part of the full picture.**
