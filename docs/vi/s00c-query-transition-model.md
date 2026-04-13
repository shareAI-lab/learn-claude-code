# Query Transition Model

> *Một agent nhiều lượt cần biết vì sao nó đi sang lượt kế tiếp: tiếp tục bình thường, retry, recover, compact hay chờ runtime result.*

## Vì Sao Cần Transition Reason

Trong vòng lặp nhỏ, bạn có thể viết:

```python
while True:
    call_model()
    run_tools()
```

Nhưng hệ thật không nên tiếp tục một cách mơ hồ. Mỗi lần quay lại model cần một lý do:

- vừa có `tool_result` mới
- tool thất bại và cần retry
- context đã compact xong
- permission bị deny và cần đổi kế hoạch
- background task trả notification
- schedule vừa kích hoạt một run mới

Nếu không ghi lý do, recovery và debugging sẽ rất khó. Agent sẽ trông như đang “tự nhiên tiếp tục”, nhưng harness không biết nó đang tiếp tục vì điều gì.

## Các Kiểu Transition

| Transition | Khi nào dùng | Điều model cần thấy |
|---|---|---|
| `normal_continue` | tool chạy xong | result hoặc observation mới |
| `retry` | lỗi có thể thử lại | lỗi, attempt count, strategy |
| `recover` | đường cũ không ổn | failure class và kế hoạch an toàn hơn |
| `compact_resume` | context được nén | summary và markers quan trọng |
| `permission_denied` | user hoặc policy từ chối | deny reason và alternative path |
| `runtime_notification` | background work có kết quả | notification payload |

## Transition Không Phải Tool Result

`tool_result` là dữ liệu cụ thể trả về từ tool. Transition reason là lý do control plane gọi model thêm một lần nữa. Hai thứ liên quan nhưng không giống nhau.

Ví dụ tool timeout:

```text
tool_result = "timeout after 120s"
transition_reason = "retry_with_narrower_scope"
```

Model cần cả hai: biết chuyện gì xảy ra và biết hệ thống đang cho phép hướng tiếp theo nào.

## Dùng Khi Đọc Các Chương Sau

- `s06`: compaction tạo transition về một context mới gọn hơn
- `s07`: permission tạo transition khi allow, ask hoặc deny
- `s11`: recovery làm transition reason thành cơ chế chính
- `s13`: background task trả notification thay vì block loop
- `s17`: autonomous agent resume từ transition có role và task context

Luôn hỏi: vòng sau được gọi vì lý do nào, và lý do đó có được ghi vào state không?
