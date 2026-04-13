# Subagent

> *Subagent có giá trị vì nó tạo ranh giới context sạch cho subtask, không phải vì nó “gọi thêm model” nghe có vẻ hay.*

## Vấn Đề

Một số việc phụ cần nhiều context riêng: khảo sát code, đọc log dài, thử nhiều hướng. Nếu nhét tất cả vào parent context, parent agent dễ mất main goal.

Subagent cho phép tách exploratory work ra một message history riêng.

## Cơ Chế

```text
parent agent
  -> creates subtask prompt
  -> child messages start fresh
  -> child uses tools / reads context
  -> child returns summary
  -> parent appends summary, not all raw detail
```

Điểm chính là parent nhận lại phần chắt lọc, không phải toàn bộ transcript con.

## State Cần Có

- parent messages
- child messages
- subtask goal
- allowed tools hoặc scope
- returned summary

Child context có thể rất khác parent context. Nhưng result gửi về parent phải đủ để quyết định bước tiếp theo.

## Khi Nào Dùng

Dùng subagent khi:

- cần khảo sát một vùng code riêng
- cần phân tích dài nhưng chỉ cần summary
- muốn giảm nhiễu trong parent context
- subtask có thể hoàn thành độc lập

Không dùng subagent chỉ để làm mọi thứ trông “multi-agent”. Nếu task cần coordination lâu dài, sau này dùng teammates/protocols.

## Bài Tập Tối Thiểu

Tạo tool `delegate` nhận `task`. Handler tạo child loop với messages mới, cho child làm việc, rồi trả summary. Parent chỉ append summary.

Nếu parent vẫn giữ main goal rõ ràng sau khi child chạy, bạn đã dùng subagent đúng mục đích.
