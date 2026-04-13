# Hệ thống hook (Hook System)

> *Hook cho phép mở rộng hành vi quanh loop mà không viết lại loop.*

## Vấn Đề

Bạn có thể muốn log, audit, annotate, block hoặc notify ở các thời điểm cố định. Nếu nhét mọi extension vào core loop, loop sẽ rối và khó giữ invariant.

Hook system tạo lifecycle points.

## Lifecycle Points

Ví dụ:

- `before_model_call`
- `after_model_call`
- `pre_tool`
- `post_tool`
- `on_error`
- `on_session_end`

Loop vẫn sở hữu control flow. Hook chỉ nhận event và trả result có giới hạn.

## HookResult

Hook có thể:

- observe: ghi log, không đổi flow
- annotate: thêm metadata hoặc note
- block: chặn action với reason
- request follow-up: tạo signal cho control plane

Không nên để hook tự chạy loạn ngoài lifecycle.

## Vì Sao Tốt

- audit không cần sửa từng tool
- policy phụ có thể plug vào pre_tool
- tracing có cùng event format
- extension có ranh giới rõ

## Cảnh Báo

Hook không phải nơi đặt business logic chính. Nếu hook bắt đầu quyết định toàn bộ task flow, kiến trúc đang ngược: extension chiếm quyền của loop.

## Bài Tập Tối Thiểu

Tạo một hook manager:

1. đăng ký hook theo event name
2. emit event từ loop
3. collect hook results
4. nếu result block, dừng execution và append reason

Sau chương này, bạn có thể mở rộng quanh loop mà không biến loop thành đống callback tùy tiện.
