# Nén ngữ cảnh (Context Compact)

> *Compaction không phải xóa lịch sử. Nó chuyển detail ra khỏi active context nhưng giữ continuity để agent tiếp tục làm việc.*

## Vấn Đề

Agent làm việc lâu sẽ tích lũy nhiều messages: file content, logs, tool output, intermediate reasoning. Nếu giữ tất cả trong active context, model sẽ tốn token, chậm và dễ lẫn.

Cần cơ chế compact.

## Ba Lớp

| Lớp | Vai trò |
|---|---|
| persisted output marker | lưu detail ngoài context và để lại marker |
| micro compact | nén một cụm result nhỏ |
| summary compact | tạo summary rộng cho đoạn lịch sử dài |

## Điều Phải Giữ

Compact tốt giữ lại:

- goal hiện tại
- quyết định đã đưa ra
- files đã đọc/sửa
- failures và recovery path
- todo/task state quan trọng
- pointer đến detail nếu cần mở lại

Nó có thể bỏ bớt raw logs hoặc output dài đã không còn cần nguyên văn.

## Luồng

```text
context grows
  -> detect pressure
  -> persist bulky detail if needed
  -> create compact summary
  -> replace old messages with summary/markers
  -> continue loop
```

## Rủi Ro

Compact sai có thể làm agent quên ràng buộc quan trọng hoặc mất bằng chứng. Vì vậy summary phải phân biệt:

- fact đã quan sát
- assumption
- pending work
- decision
- file/path liên quan

## Dừng Ở Đâu

Tối thiểu, hãy làm một summary compact có cấu trúc và marker cho output dài. Đừng cố xây memory system ở đây; memory là durable fact qua session và thuộc `s09`.
