# Giao thức đội (Team Protocols)

> *Nhiều teammate chỉ phối hợp được khi message có cấu trúc, ID và luật response rõ ràng.*

## Vấn Đề

Nếu teammates chỉ gửi text tự do, bạn khó biết request nào đã được trả lời, ai đang chờ ai, và decision nào đã được approve.

Protocol envelope tạo khung chung.

## ProtocolEnvelope

Nên có:

- `id`
- `type`: request, response, approval, rejection, update
- `from`
- `to`
- `task_id` nếu liên quan
- `body`
- `reply_to` nếu là response

## Request-Response Rule

Response phải tham chiếu request ID. Đây là điều làm coordination traceable.

```text
request id=req-1
response reply_to=req-1
```

## Các Kiểu Message

| Type | Vai trò |
|---|---|
| request | yêu cầu teammate làm hoặc cung cấp gì đó |
| response | trả lời request |
| update | báo tiến độ |
| approval | cho phép hành động |
| rejection | từ chối với reason |

## Ranh Giới

Protocol không thay task system. Task là work goal; protocol là cách actors trao đổi về work đó.

## Bài Tập Tối Thiểu

Tạo mailbox nhận envelopes, function gửi request và function validate response có `reply_to`. Sau chương này, team communication có thể debug bằng IDs thay vì đọc log mơ hồ.
