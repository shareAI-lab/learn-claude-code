# Vòng đời một request

> *Một request không kết thúc khi model trả lời. Nó kết thúc khi kết quả, trạng thái và lý do tiếp tục đã được ghi lại đủ để vòng sau hiểu chuyện gì vừa xảy ra.*

## Từ User Input Đến Next Turn

Một lượt agent đầy đủ thường đi qua các bước sau:

```text
1. user gửi yêu cầu
2. harness tạo hoặc cập nhật session state
3. prompt được lắp từ rules, tools, memory và task focus
4. model trả về text hoặc tool_use
5. harness chuẩn hóa tool intent
6. permission và hook kiểm tra intent
7. tool runtime thực thi action
8. tool_result được append vào messages
9. loop quyết định dừng hay tiếp tục
```

Điểm quan trọng là mỗi bước tạo ra bằng chứng cho bước sau. Model không tự biết shell command đã chạy ra sao nếu harness không append `tool_result`. Permission deny cũng phải được ghi lại để model đổi kế hoạch.

## Ba Dòng Trạng Thái

Trong một request, bạn thường thấy ba loại state:

| State | Sống ở đâu | Dùng để làm gì |
|---|---|---|
| Conversation state | `messages` | những gì model thấy trong lượt tiếp theo |
| Runtime state | task slot, background job, hook result | những gì hệ thống cần để chạy đúng |
| Durable state | memory, task record, schedule | những gì phải sống qua nhiều phiên |

Nhầm ba dòng này là nguồn gốc của rất nhiều bug kiến trúc.

## Write-Back Là Trung Tâm

Tool execution bên ngoài chỉ có giá trị khi kết quả quay lại được context. Vì vậy write-back không phải phần phụ. Nó là nơi action trở thành observation.

Ví dụ:

```text
tool_use(read_file) -> file content -> tool_result -> model reads content -> next action
```

Nếu thiếu write-back, agent chỉ đoán. Nếu write-back sai thứ tự, model đọc nhầm thực tế. Nếu write-back quá dài, context phình và cần compaction.

## Khi Nào Request Thật Sự Xong

Một request xong khi:

- người dùng đã nhận câu trả lời hoặc kế hoạch tiếp theo
- tool results quan trọng đã được append
- durable state cần thiết đã được ghi
- background work nếu có đã có notification path
- continuation reason rõ ràng: stop, continue, retry hoặc recover

Đọc theo vòng đời này giúp bạn thấy vì sao các chương không tách rời nhau.
