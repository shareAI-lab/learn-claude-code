# Bộ lập lịch Cron (Cron Scheduler)

> *Scheduling không phải hệ riêng. Nó là một nguồn trigger đưa work vào cùng agent/runtime path theo thời gian.*

## Vấn Đề

Một số việc cần chạy theo lịch: kiểm tra dependency, tạo report, scan issue, nhắc review. Nếu scheduler bypass agent runtime, bạn sẽ có hai hệ execution khác nhau.

Scheduler nên tạo trigger cho cùng task/runtime system.

## ScheduleRecord

Một schedule cần:

- id
- prompt hoặc task template
- timing rule
- enabled/disabled
- last run
- next run
- target workspace hoặc scope

## Luồng

```text
timer ticks
  -> find due schedules
  -> create runtime task or agent run
  -> execute through normal loop
  -> record result/notification
  -> compute next run
```

## Ranh Giới

Scheduler không nên tự quyết định business logic. Nó chỉ trả lời “khi nào bắt đầu”. Agent/task runtime vẫn trả lời “làm gì và làm thế nào”.

## Với Background Tasks

Cron thường khởi tạo work có thể chạy nền. Vì vậy nó dựa vào `s13`: start slot, return notification, update state khi xong.

## Bài Tập Tối Thiểu

- tạo `ScheduleRecord`
- viết function `due(now)`
- khi due, tạo run mới
- ghi `last_run` và `next_run`
- gửi result về cùng notification path

Sau chương này, time trở thành một entry point của hệ thống, không phải một executor riêng.
