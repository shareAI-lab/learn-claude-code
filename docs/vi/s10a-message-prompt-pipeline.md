# Message-Prompt Pipeline

> *System prompt chỉ là một phần của input. Agent thật cần quản lý cả messages, tool results, compact summaries và runtime sections.*

## Các Nguồn Input

Model input thường đến từ nhiều nguồn:

- stable system rules
- conversation messages
- tool specs
- tool results
- memory entries
- todo/task state
- compact summaries
- runtime notifications

Pipeline quyết định thứ gì vào đâu và ở dạng nào.

## Messages Và Prompt Khác Gì

`messages` là conversation history model đọc theo lượt. Prompt sections là các khối hướng dẫn hoặc context được lắp trước/ngoài user message tùy API.

Cả hai đều ảnh hưởng reasoning. Nhưng chúng có lifecycle khác nhau.

## Quy Tắc Lắp

- stable rules đứng trước
- workspace/runtime state ngắn và cập nhật
- memory chỉ gồm fact liên quan
- tool results giữ ID và thứ tự
- summaries ghi rõ chúng là summary, không phải raw observation
- user request cuối phải không bị chôn trong noise

## Điểm Debug

Một harness tốt nên có cách preview input cuối:

```text
[role]
[workspace]
[memory]
[tools]
[messages]
[current request]
```

Nếu không thể xem model đã nhận gì, debugging prompt sẽ rất khó.

## Nối Với Các Chương

- `s06` tạo compact summary
- `s09` cấp memory context
- `s10` lắp prompt sections
- `s11` thêm recovery reason
- `s13` thêm notification từ runtime

Pipeline này là nơi các cơ chế gặp nhau trong input model.
