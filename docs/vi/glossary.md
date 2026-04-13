# Thuật ngữ

> *Khi thuật ngữ bắt đầu lẫn nhau, hãy quay lại đây để khóa lại ranh giới.*

| Thuật ngữ | Nghĩa trong repo này |
|---|---|
| Agent | model + harness + state + tools, không chỉ riêng model |
| Harness | phần code cung cấp môi trường làm việc cho model |
| Agent loop | chuỗi call model -> run tools -> append results -> continue |
| Message | đơn vị context model đọc được |
| `tool_use` | yêu cầu model muốn gọi một tool |
| `tool_result` | kết quả tool được append lại cho model đọc |
| Tool spec | mô tả tool đưa cho model |
| Tool handler | hàm code thật sự thực thi tool |
| Dispatch map | bảng route từ tool name sang handler |
| Todo | kế hoạch tạm trong một session |
| Task | work record bền vững, sống ngoài một chat turn |
| Runtime task | slot đang chạy của một task hoặc job cụ thể |
| Notification | kết quả runtime gửi lại khi công việc chạy nền xong |
| Subagent | agent con có context riêng cho một subtask |
| Skill | tri thức chuyên biệt được discover rẻ và load khi cần |
| Context compact | chuyển detail khỏi active context nhưng giữ continuity |
| Permission | gate kiểm tra intent trước execution |
| Hook | extension point ở lifecycle cố định |
| Memory | durable fact dùng qua nhiều session |
| Prompt assembly | pipeline lắp system input từ nhiều section |
| Recovery | nhánh tiếp tục khi tool hoặc plan thất bại |
| Team member | teammate tồn tại lâu dài, có role và mailbox |
| Protocol envelope | message có cấu trúc để request/response giữa teammates |
| Autonomy | cơ chế idle, scan, claim, resume có giới hạn |
| Worktree | thư mục/lane thực thi tách biệt cho parallel work |
| MCP | cơ chế đưa external capabilities vào capability bus |

## Các Cặp Dễ Nhầm

### Todo vs Task

`Todo` giúp agent đi qua vài bước trong một phiên. `Task` là record bền vững có status, dependency và có thể sống qua nhiều phiên.

### Task vs Runtime Task

`Task` nói cần làm gì. `RuntimeTaskState` nói việc đang chạy ở đâu, bởi ai, trạng thái execution hiện tại là gì.

### Subagent vs Teammate

Subagent thường là context tạm cho một subtask. Teammate trong team là thực thể tồn tại lâu dài, có identity và protocol.

### Worktree vs Task

Task là mục tiêu. Worktree là lane filesystem nơi một actor thực thi mục tiêu đó. Một task có thể được bind vào worktree, nhưng hai khái niệm không nên gộp.

### Tool vs Capability

Tool là interface cụ thể model gọi. Capability là năng lực rộng hơn có thể đến từ native code, plugin hoặc MCP server, rồi được route về tool/control plane.

## Quy Tắc Ghi Nhớ

Khi gặp thuật ngữ mới, hãy hỏi:

- nó là state, action hay policy?
- nó sống trong session, runtime hay durable store?
- model có nhìn thấy nó trực tiếp không?
- nó nối vào loop ở trước model call, trong execution hay sau result?
