# Sử dụng công cụ (Tool Use)

> *Thêm tool không nên làm loop phức tạp hơn. Nó chỉ nên thêm một spec và một handler trong dispatch map.*

## Vấn Đề

Nếu mỗi tool được nhét trực tiếp vào loop bằng `if/else`, loop sẽ nhanh chóng phình to. Agent cần một mặt phẳng ổn định:

- model thấy danh sách tool specs
- model chọn tool bằng name và input
- harness route name đó sang handler thật
- result quay lại bằng `tool_result`

## Hai Mặt Của Tool

| Phần | Ai dùng | Vai trò |
|---|---|---|
| `ToolSpec` | model | mô tả name, input schema, ý nghĩa |
| handler | harness | code thực thi action |

Đừng nhầm schema với implementation. Schema là contract cho model. Handler là function chạy thật.

## Dispatch Map

```python
tools = {
    "read_file": read_file,
    "write_file": write_file,
    "run_shell": run_shell,
}
```

Khi model gọi `read_file`, loop không cần biết chi tiết đọc file. Nó chỉ route qua map, nhận result và append.

## Lợi Ích

- thêm tool mới không đổi loop
- permission/hook sau này có thể chặn trước dispatch
- MCP sau này cũng có thể route vào cùng capability path
- debug dễ hơn vì mọi tool đi qua một entry point

## Bài Tập Tối Thiểu

Tự thêm một tool `list_files`:

1. viết spec cho model
2. viết handler đọc thư mục
3. đăng ký vào dispatch map
4. để model gọi tool
5. append `tool_result`

Nếu làm được mà không sửa core loop, bạn đã hiểu chương này.
