# s03: TodoWrite

`s01 > s02 > [ s03 ] s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Một agent không có kế hoạch sẽ bị mất phương hướng"* -- liệt kê các bước trước, sau đó mới thực hiện.
>
> **Lớp khung (Harness layer)**: Lập kế hoạch -- giữ cho mô hình đi đúng hướng mà không cần lập trình sẵn lộ trình.

## Vấn đề

Đối với các tác vụ nhiều bước, mô hình dễ bị mất dấu. Nó lặp lại công việc, bỏ sót các bước hoặc đi chệch hướng. Các cuộc hội thoại dài làm cho điều này tệ hơn -- system prompt bị mờ nhạt dần khi kết quả công cụ lấp đầy ngữ cảnh. Một công việc tái cấu trúc (refactoring) 10 bước có thể hoàn thành các bước 1-3, sau đó mô hình bắt đầu tự ý ứng biến vì nó đã quên các bước từ 4-10.

## Giải pháp

```
+--------+      +-------+      +-------------+
|  User  | ---> |  LLM  | ---> | Công cụ     |
| prompt |      |       |      | + todo      |
+--------+      +---+---+      +------+------+
                    ^                 |
                    |   tool_result   |
                    +-----------------+
                           |
               +-----------+-----------+
               | Trạng thái TodoManager|
               | [ ] tác vụ A          |
               | [>] tác vụ B <- đang làm |
               | [x] tác vụ C          |
               +-----------------------+
                           |
               nếu số_vòng_từ_khi_todo >= 3:
                 chèn <reminder> vào tool_result
```

## Cách hoạt động

1. TodoManager lưu trữ các mục với các trạng thái. Tại một thời điểm chỉ có một mục có thể ở trạng thái `in_progress` (đang thực hiện).

```python
class TodoManager:
    def update(self, items: list) -> str:
        validated, in_progress_count = [], 0
        for item in items:
            status = item.get("status", "pending")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item["id"], "text": item["text"],
                              "status": status})
        if in_progress_count > 1:
            raise ValueError("Chỉ một tác vụ có thể ở trạng thái in_progress")
        self.items = validated
        return self.render()
```

2. Công cụ `todo` được đưa vào bản đồ điều phối giống như bất kỳ công cụ nào khác.

```python
TOOL_HANDLERS = {
    # ...các công cụ cơ bản...
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

3. Một lời nhắc nhở (nag reminder) sẽ được chèn vào nếu mô hình trải qua 3+ vòng lặp mà không gọi `todo`.

```python
if rounds_since_todo >= 3 and messages:
    last = messages[-1]
    if last["role"] == "user" and isinstance(last.get("content"), list):
        last["content"].insert(0, {
            "type": "text",
            "text": "<reminder>Cập nhật các việc cần làm (todo) của bạn.</reminder>",
        })
```

Ràng buộc "chỉ một việc đang thực hiện tại một thời điểm" buộc agent phải tập trung tuần tự. Lời nhắc nhở tạo ra tính trách nhiệm.

## Những gì đã thay đổi so với s02

| Thành phần         | Trước (s02)          | Sau (s03)                      |
|--------------------|----------------------|--------------------------------|
| Công cụ            | 4                    | 5 (+todo)                      |
| Lập kế hoạch       | Không có             | TodoManager với các trạng thái |
| Chèn nhắc nhở      | Không có             | `<reminder>` sau 3 vòng lặp    |
| Vòng lặp Agent     | Điều phối đơn giản   | + bộ đếm số_vòng_từ_khi_todo   |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s03_todo_write.py
```

1. `Tái cấu trúc tệp hello.py: thêm gợi ý kiểu (type hints), chuỗi tài liệu (docstrings) và main guard`
2. `Tạo một gói Python với __init__.py, utils.py và tests/test_utils.py`
3. `Kiểm tra tất cả các tệp Python và sửa các lỗi phong cách trình bày (style issues)`
