# Hệ thống memory (Memory System)

> *Memory chỉ nên lưu thứ còn đúng qua nhiều session và không dễ suy ra lại từ workspace hiện tại.*

## Vấn Đề

Agent cần nhớ một số fact bền vững: user thích `pnpm`, repo dùng test command nào, team có convention gì. Nhưng nếu lưu mọi đoạn chat vào memory, memory sẽ nhiễu và sai.

Memory cần type và policy.

## MemoryEntry

Một entry nên có:

- key hoặc scope
- value
- source / reason
- timestamp
- confidence nếu cần
- rule để update hoặc expire

## Current Observation vs Durable Memory

Observation hiện tại luôn thắng memory cũ. Nếu memory nói repo dùng npm nhưng `package.json` hiện tại có `pnpm-lock.yaml`, agent phải tin workspace.

Memory cho hướng đi; observation cho sự thật.

## Luồng

```text
before model call
  -> load relevant memory
  -> include concise memory context
agent works
  -> identify durable fact
  -> write/update memory
```

## Nên Lưu Gì

- user preference rõ ràng
- repo convention ổn định
- command thường dùng nếu đã xác nhận
- long-term project fact

## Không Nên Lưu Gì

- output tạm thời
- lỗi vừa xảy ra trong một run
- assumption chưa kiểm chứng
- nội dung file có thể đọc lại dễ dàng

## Dừng Ở Đâu

Tối thiểu, làm memory store key-value có load theo scope và write có reason. Đừng biến memory thành transcript database. Memory ít nhưng đúng hữu ích hơn memory nhiều nhưng nhiễu.
