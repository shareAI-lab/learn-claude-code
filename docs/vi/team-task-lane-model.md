# Teammate-Task-Lane Model

> *Từ `s15` đến `s18`, năm khái niệm dễ lẫn nhau nhất là teammate, protocol request, task, runtime slot và worktree lane.*

## Năm Lớp Khác Nhau

| Lớp | Trả lời câu hỏi | Ví dụ state |
|---|---|---|
| Teammate | ai có thể làm việc? | `TeamMember` |
| Protocol request | họ đang trao đổi điều gì? | `ProtocolEnvelope` |
| Task | mục tiêu bền vững là gì? | `TaskRecord` |
| Runtime slot | việc nào đang chạy? | `RuntimeTaskState` |
| Worktree lane | chạy ở đâu? | `WorktreeRecord` |

Nếu gộp các lớp này, hệ thống multi-agent sẽ khó debug. Một teammate không phải task. Một task không phải worktree. Một worktree không nói mục tiêu business là gì.

## Luồng Điển Hình

```text
team member scans task board
  -> claims a TaskRecord
  -> creates runtime slot
  -> enters or creates worktree lane
  -> executes tools
  -> sends protocol update / notification
  -> closes out task or lane
```

Mỗi bước update một loại state khác nhau.

## Các Nhầm Lẫn Phổ Biến

### Teammate vs Subagent

Subagent thường tạm thời, được tạo cho một delegated subtask. Teammate có role, identity và mailbox lâu dài.

### Task vs Protocol Request

Task là work goal. Protocol request là một message có ID để yêu cầu, approve, reject hoặc reply.

### Runtime Slot vs Worktree

Runtime slot nói process/job đang ở trạng thái nào. Worktree nói filesystem lane nào đang được dùng.

### Worktree vs Task

Task có thể đổi owner hoặc retry. Worktree có thể được giữ, đóng, merge hoặc bỏ. Chúng cần binding rõ ràng nhưng không phải một object.

## Quy Tắc Thiết Kế

- mỗi layer có ID riêng
- mỗi transition nên ghi rõ layer nào đổi state
- closeout của worktree không đồng nghĩa task done
- protocol response phải tham chiếu request ID
- autonomous claim phải kiểm tra task status và role policy

Giữ năm lớp này tách biệt là chìa khóa để `s15-s18` không biến thành mớ state khó hiểu.
