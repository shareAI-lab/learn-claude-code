# Entity Map

> *Entity map giúp bạn thấy mỗi khái niệm thuộc lớp nào, tránh gộp task, teammate, runtime slot và worktree thành một.*

## Bản Đồ Lớp

```text
User request
  -> Session / messages
  -> Agent loop
  -> Tool runtime / control plane
  -> Durable task runtime
  -> Team / worktree / external capability platform
```

Mỗi lớp có entity riêng. Một bug kiến trúc thường xuất hiện khi một entity bị bắt làm việc của lớp khác.

## Entity Chính

| Entity | Lớp | Không nên nhầm với |
|---|---|---|
| `messages` | session context | durable memory |
| `TodoItem` | session planning | `TaskRecord` |
| `ToolSpec` | model-facing contract | tool handler |
| `PermissionDecision` | control plane | tool result |
| `MemoryEntry` | durable context | current observation |
| `TaskRecord` | durable work graph | runtime process |
| `RuntimeTaskState` | execution runtime | task goal |
| `TeamMember` | platform actor | subagent tạm |
| `ProtocolEnvelope` | team communication | plain chat message |
| `WorktreeRecord` | execution lane | task itself |
| `CapabilityRoute` | external capability bus | one local tool |

## Quan Hệ Quan Trọng

- Agent loop đọc `messages` và tạo `tool_use`.
- Tool runtime nhận `tool_use`, đi qua permission/hook, rồi tạo `tool_result`.
- `tool_result` quay lại `messages` để model có observation mới.
- Todo giúp phiên hiện tại đi đúng hướng, nhưng task graph điều phối work lâu dài.
- Runtime task là nơi work đang chạy, không phải định nghĩa mục tiêu.
- Team member có mailbox/protocol; subagent chỉ là delegated context tạm.
- Worktree là nơi chạy việc, không phải lý do tồn tại của việc.
- MCP capability phải quay lại cùng routing và permission path như native tools.

## Cách Dùng Map

Khi đọc một đoạn code, hãy đánh nhãn nó:

1. session context
2. model input
3. tool execution
4. control plane
5. durable runtime
6. platform boundary

Nếu một đoạn vừa update durable task vừa quyết định prompt vừa chạy shell, hãy nghi ngờ nó đang gộp quá nhiều trách nhiệm.
