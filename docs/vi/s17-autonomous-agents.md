# Agent tự chủ (Autonomous Agents)

> *Autonomy không phải phép màu. Nó là vòng idle, scan, claim và resume có policy rõ ràng.*

## Vấn Đề

Nếu teammate luôn phải chờ user hoặc parent gọi, platform không tự tiến triển. Nhưng nếu agent tự làm mọi thứ không policy, nó nguy hiểm.

Autonomy cần bounded mechanism.

## Chu Kỳ

```text
idle
  -> scan available tasks
  -> filter by role/policy
  -> claim one task
  -> load resume context
  -> work
  -> update status
  -> return to idle
```

## ClaimPolicy

Policy nên kiểm tra:

- task status có runnable không?
- dependency đã unlock chưa?
- role có phù hợp không?
- có ai đã claim chưa?
- risk có cần approval không?

## Resume Context

Khi autonomous agent tiếp tục task, nó cần context đúng:

- task goal
- recent updates
- relevant memory
- worktree/lane nếu có
- protocol messages liên quan

## Ranh Giới

Autonomous agent vẫn phải đi qua permissions, tool runtime và protocol. Autonomy chỉ quyết định khi nào nó tự bắt đầu hoặc resume work.

## Bài Tập Tối Thiểu

Tạo idle loop quét task board, claim một task phù hợp, chạy một bước nhỏ, update status. Đặt limit rõ để tránh loop vô hạn.
