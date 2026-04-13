# Đội agent (Agent Teams)

> *Khi hệ thống cần nhiều specialist tồn tại lâu dài, subagent tạm thời không còn đủ. Bạn cần teammates có identity và lifecycle.*

## Vấn Đề

Subagent tốt cho delegated subtask ngắn. Nhưng platform lớn có thể cần reviewer, implementer, researcher, tester lặp lại qua nhiều task.

Agent team thêm roster.

## TeamMember

Một teammate có:

- id/name
- role
- capabilities
- mailbox hoặc channel
- availability/status
- memory hoặc context riêng nếu cần

## Khác Subagent

| Subagent | Teammate |
|---|---|
| tạm thời | tồn tại lâu dài |
| context cho một subtask | identity và role ổn định |
| trả summary về parent | phối hợp qua protocol/mailbox |
| ít lifecycle | có claim, status, handoff |

## Luồng

```text
team roster exists
  -> task appears
  -> suitable teammate is selected or claims
  -> teammate works in its context/lane
  -> result/update sent back
```

## Ranh Giới

Team không có nghĩa mọi thứ chạy song song bừa bãi. Bạn cần protocol và task state rõ, nếu không nhiều agent sẽ giẫm lên nhau.

## Dừng Ở Đâu

Tối thiểu, tạo roster với role và mailbox. Cho một teammate nhận request và trả response. Protocol chi tiết để `s16`; autonomy để `s17`.
