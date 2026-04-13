# Tác vụ chạy nền (Background Tasks)

> *Background execution tách mục tiêu công việc khỏi slot đang chạy, để slow work không block toàn bộ agent loop.*

## Vấn Đề

Một số command mất lâu: test suite, build, indexing, crawl. Nếu loop chờ đồng bộ, agent bị kẹt. Background task cho phép chạy việc chậm và nhận kết quả sau.

## Hai Khái Niệm

| Khái niệm | Nghĩa |
|---|---|
| Task goal | việc cần hoàn thành |
| Runtime task slot | execution cụ thể đang chạy |

Đừng gộp hai thứ này. Một goal có thể retry bằng slot khác.

## RuntimeTaskState

Nên có:

- id
- command/action
- status: running, done, failed
- started_at / finished_at
- result hoặc result pointer
- notification target

## Notification

Khi background work xong, nó tạo notification để agent hoặc user biết có observation mới.

```text
start background job
  -> return job id
  -> loop continues
  -> job finishes
  -> notification appended or surfaced
```

## Ranh Giới

Background task không phải “agent thứ hai”. Nó là runtime lane. Model vẫn cần đọc result/notification để quyết định tiếp.

## Bài Tập Tối Thiểu

Tạo manager có:

- `start(command)`
- `check(id)`
- `collect_notifications()`

Sau chương này, slow work không cần block main loop nhưng vẫn có đường quay lại context.
