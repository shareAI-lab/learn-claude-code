# Nạp skill (Skill Loading)

> *Skill nên được discover rẻ và load sâu chỉ khi cần, thay vì nhồi mọi tri thức vào prompt từ đầu.*

## Vấn Đề

Agent có thể cần nhiều tri thức chuyên biệt: cách review code, cách xử lý PDF, cách build MCP server. Nếu đưa toàn bộ vào system prompt, context phình và model bị nhiễu.

Skill loading tách hai bước:

1. discovery rẻ: biết skill nào tồn tại
2. load sâu: nạp nội dung skill khi task thật sự cần

## Cấu Trúc

| Record | Vai trò |
|---|---|
| `SkillMeta` | tên, mô tả ngắn, trigger |
| `SkillContent` | hướng dẫn đầy đủ |
| `SkillRegistry` | nơi tìm skill phù hợp |

Model ban đầu chỉ cần metadata. Khi thấy task khớp, harness hoặc agent nạp file skill vào context.

## Luồng

```text
user task
  -> inspect skill metadata
  -> choose relevant skill
  -> read skill content
  -> inject into prompt/context
  -> act with specialized instructions
```

## Quy Tắc

- metadata phải ngắn và rõ trigger
- content chỉ load khi có lý do
- skill không nên thay thế state thật từ workspace
- skill là hướng dẫn, không phải bằng chứng hiện tại

## Ví Dụ

Nếu user hỏi “review PR này”, metadata của `code-review` đủ để biết cần skill. Sau đó mới nạp hướng dẫn review chi tiết.

## Dừng Ở Đâu

Sau chương này, bạn nên làm được registry nhỏ đọc skill files từ disk, liệt kê mô tả ngắn và nạp nội dung đúng lúc. Đừng xây marketplace hay versioning phức tạp vội.
