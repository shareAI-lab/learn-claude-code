# s02: Sử dụng công cụ

`s01 > [ s02 ] s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Thêm một công cụ có nghĩa là thêm một trình xử lý (handler)"* -- vòng lặp vẫn giữ nguyên; các công cụ mới được đăng ký vào bản đồ điều phối (dispatch map).
>
> **Lớp khung (Harness layer)**: Điều phối công cụ -- mở rộng những gì mô hình có thể tiếp cận.

## Vấn đề

Chỉ với `bash`, agent phải thực hiện mọi thứ thông qua shell. `cat` cắt bớt nội dung một cách khó dự đoán, `sed` thất bại với các ký tự đặc biệt, và mỗi lần gọi bash là một bề mặt bảo mật không bị giới hạn. Các công cụ chuyên dụng như `read_file` và `write_file` cho phép bạn thực thi việc đóng gói đường dẫn (path sandboxing) ở cấp độ công cụ.

Điểm mấu chốt: thêm công cụ không yêu cầu thay đổi vòng lặp.

## Giải pháp

```
+--------+      +-------+      +-----------------------+
|  User  | ---> |  LLM  | ---> | Điều phối công cụ     |
| prompt |      |       |      | {                     |
+--------+      +---+---+      |   bash: run_bash      |
                    ^           |   read: run_read      |
                    |           |   write: run_wr       |
                    +-----------+   edit: run_edit      |
                    tool_result | }                     |
                                +-----------------------+

Bản đồ điều phối là một từ điển: {tool_name: handler_function}.
Một lần tra cứu thay thế bất kỳ chuỗi if/elif nào.
```

## Cách hoạt động

1. Mỗi công cụ có một hàm xử lý (handler function). Việc đóng gói đường dẫn (path sandboxing) ngăn chặn việc thoát khỏi không gian làm việc (workspace escape).

```python
def safe_path(p: str) -> Path:
    # Đảm bảo đường dẫn nằm trong WORKDIR
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Đường dẫn thoát khỏi không gian làm việc: {p}")
    return path

def run_read(path: str, limit: int = None) -> str:
    text = safe_path(path).read_text()
    lines = text.splitlines()
    if limit and limit < len(lines):
        lines = lines[:limit]
    return "\n".join(lines)[:50000]
```

2. Bản đồ điều phối liên kết tên công cụ với các trình xử lý.

```python
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

3. Trong vòng lặp, tra cứu trình xử lý theo tên. Thân vòng lặp không thay đổi so với s01.

```python
for block in response.content:
    if block.type == "tool_use":
        handler = TOOL_HANDLERS.get(block.name)
        output = handler(**block.input) if handler \
            else f"Công cụ không xác định: {block.name}"
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
```

Thêm một công cụ = thêm một trình xử lý + thêm một mục nhập lược đồ (schema entry). Vòng lặp không bao giờ thay đổi.

## Những gì đã thay đổi so với s01

| Thành phần         | Trước (s01)           | Sau (s02)                      |
|--------------------|-----------------------|--------------------------------|
| Công cụ            | 1 (chỉ bash)          | 4 (bash, read, write, edit)    |
| Điều phối          | Gọi bash được mã hóa cứng | Từ điển `TOOL_HANDLERS`      |
| An toàn đường dẫn  | Không có              | Sandbox `safe_path()`          |
| Vòng lặp Agent     | Không đổi             | Không đổi                      |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

1. `Đọc tệp requirements.txt`
2. `Tạo một tệp tên là greet.py với hàm greet(name)`
3. `Chỉnh sửa greet.py để thêm docstring vào hàm`
4. `Đọc greet.py để kiểm tra việc chỉnh sửa đã hoạt động`
