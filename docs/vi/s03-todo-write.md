# TodoWrite

> *Khi task có nhiều bước, plan nhìn thấy được giúp agent giữ hướng trong một session.*

## Vấn Đề

Một yêu cầu như “refactor module và cập nhật tests” không phải một action đơn. Nếu agent chỉ dựa vào messages, nó dễ quên bước, lặp lại việc đã làm hoặc kết thúc quá sớm.

TodoWrite thêm một planning state nhỏ cho session.

## Todo Là Gì

`TodoItem` thường có:

- id
- nội dung bước
- status: pending, in_progress, completed

`PlanState` giữ danh sách todo và nhắc agent bước nào đang active.

## Todo Không Phải Task System

Todo ở đây chỉ sống trong session. Nó không có dependency graph bền vững, không có owner dài hạn, không cần background runtime.

`TaskRecord` ở `s12` là khái niệm khác.

## Cách Nối Vào Loop

```text
user asks complex task
  -> agent writes todo list
  -> loop includes plan reminder
  -> agent marks one item in_progress
  -> tools run
  -> item becomes completed
  -> next item starts
```

Reminder giúp model luôn thấy kế hoạch hiện tại, thay vì tự nhớ trong hidden state không tồn tại.

## Thiết Kế Tối Thiểu

- thêm tool `todo_write`
- validate status của item
- chỉ cho một item `in_progress` tại một thời điểm nếu muốn đơn giản
- render plan reminder vào context
- update plan sau mỗi bước đáng kể

## Dừng Ở Đâu

Sau chương này, agent nên chia task lớn thành các bước theo dõi được. Đừng biến todo thành project management system. Durable task graph để dành cho `s12`.
