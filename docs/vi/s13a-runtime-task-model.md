# Runtime Task Model

> *Stage 3 dễ nhầm vì từ “task” có hai nghĩa: mục tiêu bền vững và execution đang chạy.*

## Ba Lớp

| Lớp | Câu hỏi | Record |
|---|---|---|
| Task goal | cần làm gì? | `TaskRecord` |
| Runtime execution | đang chạy ra sao? | `RuntimeTaskState` |
| Notification | kết quả quay lại thế nào? | `Notification` |

## Ví Dụ

Task goal:

```text
Refactor payment adapter
```

Runtime execution:

```text
run tests for payment adapter, job id 42, status running
```

Notification:

```text
job 42 failed: 2 tests failing in adapter validation
```

Ba thứ liên quan nhưng không giống nhau.

## Vì Sao Phải Tách

- một task có thể có nhiều attempt
- runtime slot có thể fail mà task chưa fail hẳn
- notification là observation, không phải goal
- scheduler có thể tạo runtime slot mới từ task hoặc prompt

## Luồng

```text
TaskRecord created
  -> runtime slot started
  -> execution produces result
  -> notification delivered
  -> task status updated if appropriate
```

## Câu Hỏi Debug

Khi có bug, hỏi:

- goal có còn đúng không?
- slot nào đang chạy?
- result đã về chưa?
- notification có được append không?
- task status update có quá sớm không?

Giữ model này rõ sẽ giúp `s12-s14` dễ hiểu hơn nhiều.
