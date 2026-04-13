# Bản đồ cấu trúc dữ liệu

> *Nếu không biết state sống ở đâu, bạn sẽ không biết cơ chế thật sự làm gì.*

## Core Records

| Record | Chương | Vai trò |
|---|---|---|
| `LoopState` / `messages` | `s01` | giữ conversation context và tool results |
| `ToolSpec` | `s02` | mô tả tool cho model |
| `ToolDispatchMap` | `s02` | route tool name sang handler |
| `TodoItem` | `s03` | một bước trong plan session |
| `PlanState` | `s03` | tập todo và reminder hiện tại |
| `SubagentContext` | `s04` | messages riêng cho delegated subtask |
| `SkillMeta` | `s05` | metadata rẻ để discover skill |
| `SkillContent` | `s05` | nội dung skill nạp khi cần |
| `CompactSummary` | `s06` | summary giữ continuity sau compaction |
| `PersistedOutputMarker` | `s06` | marker chỉ nơi detail đã được lưu ngoài context |

## Control Plane Records

| Record | Chương | Vai trò |
|---|---|---|
| `PermissionRule` | `s07` | rule allow/deny/ask |
| `PermissionDecision` | `s07` | kết quả kiểm tra intent |
| `HookEvent` | `s08` | event tại lifecycle point |
| `HookResult` | `s08` | annotation hoặc block từ hook |
| `MemoryEntry` | `s09` | durable fact |
| `MemoryStore` | `s09` | nơi lưu và query memory |
| `PromptParts` | `s10` | các section trước khi lắp prompt |
| `RecoveryState` | `s11` | thông tin failure, retry, continuation |
| `TransitionReason` | `s11` | vì sao loop tiếp tục |

## Runtime Và Platform Records

| Record | Chương | Vai trò |
|---|---|---|
| `TaskRecord` | `s12` | work goal bền vững |
| `TaskStatus` | `s12` | pending, running, blocked, done |
| `RuntimeTaskState` | `s13` | execution slot đang chạy |
| `Notification` | `s13` | result từ background work |
| `ScheduleRecord` | `s14` | trigger theo thời gian |
| `TeamMember` | `s15` | teammate có role và mailbox |
| `ProtocolEnvelope` | `s16` | request/response có ID |
| `ClaimPolicy` | `s17` | luật tự nhận việc |
| `AutonomyState` | `s17` | idle/claimed/resumed state |
| `WorktreeRecord` | `s18` | execution lane tách biệt |
| `CapabilityRoute` | `s19` | route external capability vào bus |

## Câu Hỏi Cần Hỏi Với Mọi Record

- record này sống bao lâu?
- model có cần nhìn thấy toàn bộ record hay chỉ summary?
- record được update trước hay sau tool execution?
- record này có thể persist qua session không?
- record này khác record có tên gần giống ở điểm nào?

Nắm data structures trước, đọc code sau sẽ nhẹ hơn rất nhiều.
