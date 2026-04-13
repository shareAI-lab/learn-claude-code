# Khôi phục lỗi (Error Recovery)

> *Nhiều lỗi không phải task thất bại thật. Chúng là tín hiệu để agent thử đường khác với state rõ ràng hơn.*

## Vấn Đề

Tool có thể timeout, file có thể thiếu, command có thể fail, permission có thể bị deny. Nếu harness chỉ ném exception hoặc trả text lỗi mơ hồ, model không biết nên làm gì tiếp.

Recovery biến failure thành branch có cấu trúc.

## RecoveryState

Nên ghi:

- failure type
- tool/action liên quan
- raw error ngắn
- attempt count
- strategy tiếp theo
- transition reason

## Các Chiến Lược

| Failure | Strategy |
|---|---|
| timeout | retry với scope nhỏ hơn |
| file missing | search path hoặc hỏi user |
| permission denied | chọn alternative an toàn |
| test failure | đọc failure, sửa targeted |
| malformed output | yêu cầu format lại hoặc parse fallback |

## Luồng

```text
tool fails
  -> classify failure
  -> update RecoveryState
  -> append error observation
  -> decide retry/recover/stop
  -> call model with reason
```

## Retry Có Giới Hạn

Recovery không có nghĩa retry vô hạn. Cần attempt limit và stop reason. Nếu không, agent sẽ loop mãi.

## Điều Model Cần Thấy

Model cần biết:

- lỗi thật là gì
- hệ thống đang retry hay recover
- đã thử mấy lần
- ràng buộc mới là gì

## Dừng Ở Đâu

Tối thiểu, classify timeout và command failure, cho retry một lần với strategy rõ, rồi stop nếu vẫn fail. Sau chương này, lỗi trở thành data trong loop, không phải crash bí ẩn.
