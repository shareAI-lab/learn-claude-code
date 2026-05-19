# s04: Subagent (Agent phụ)

`s01 > s02 > s03 > [ s04 ] s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Chia nhỏ các tác vụ lớn; mỗi tác vụ con nhận được một ngữ cảnh sạch"* -- các subagent sử dụng mảng messages[] độc lập, giữ cho cuộc hội thoại chính luôn gọn gàng.
>
> **Lớp khung (Harness layer)**: Cô lập ngữ cảnh (Context isolation) -- bảo vệ sự rõ ràng trong tư duy của mô hình.

## Vấn đề

Khi agent làm việc, mảng messages của nó sẽ tăng dần. Mỗi lần đọc tệp, mỗi đầu ra của bash đều lưu lại trong ngữ cảnh vĩnh viễn. Câu hỏi "Dự án này sử dụng khung kiểm thử (testing framework) nào?" có thể yêu cầu đọc 5 tệp, nhưng agent cha (parent agent) chỉ cần câu trả lời: "pytest."

## Giải pháp

```
Agent cha                       Subagent (Agent phụ)
+------------------+             +------------------+
| messages=[...]   |             | messages=[]      | <-- mới
|                  |  điều phối  |                  |
| công cụ: task    | ----------> | while tool_use:  |
|   prompt="..."   |             |   gọi công cụ    |
|                  |  tóm tắt    |   thêm kết quả   |
|   result = "..." | <---------- | trả về văn bản   |
+------------------+             +------------------+

Ngữ cảnh của cha được giữ sạch. Ngữ cảnh của subagent bị loại bỏ.
```

## Cách hoạt động

1. Agent cha có thêm công cụ `task`. Agent con có tất cả các công cụ cơ bản ngoại trừ `task` (để tránh việc khởi tạo đệ quy - recursive spawning).

```python
PARENT_TOOLS = CHILD_TOOLS + [
    {"name": "task",
     "description": "Khởi tạo một subagent với ngữ cảnh mới.",
     "input_schema": {
         "type": "object",
         "properties": {"prompt": {"type": "string"}},
         "required": ["prompt"],
      }},
]
```

2. Subagent bắt đầu với `messages=[]` và chạy vòng lặp của chính nó. Chỉ có văn bản cuối cùng được trả về cho agent cha.

```python
def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]
    for _ in range(30):  # giới hạn an toàn
        response = client.messages.create(
            model=MODEL, system=SUBAGENT_SYSTEM,
            messages=sub_messages,
            tools=CHILD_TOOLS, max_tokens=8000,
        )
        sub_messages.append({"role": "assistant",
                             "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input)
                results.append({"type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output)[:50000]})
        sub_messages.append({"role": "user", "content": results})
    return "".join(
        b.text for b in response.content if hasattr(b, "text")
    ) or "(không có tóm tắt)"
```

Toàn bộ lịch sử tin nhắn của agent con (có thể là hơn 30 lần gọi công cụ) sẽ bị loại bỏ. Agent cha chỉ nhận được một đoạn văn tóm tắt dưới dạng một `tool_result` thông thường.

## Những gì đã thay đổi so với s03

| Thành phần         | Trước (s03)          | Sau (s04)                      |
|--------------------|----------------------|--------------------------------|
| Công cụ            | 5                    | 5 (cơ bản) + task (cho cha)    |
| Ngữ cảnh           | Chia sẻ đơn nhất     | Cô lập Cha + Con               |
| Subagent           | Không có             | Hàm `run_subagent()`           |
| Giá trị trả về     | Không áp dụng        | Chỉ tóm tắt văn bản            |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s04_subagent.py
```

1. `Sử dụng một tác vụ con (subtask) để tìm xem dự án này sử dụng khung kiểm thử nào`
2. `Ủy quyền (Delegate): đọc tất cả các tệp .py và tóm tắt chức năng của từng tệp`
3. `Sử dụng một tác vụ (task) để tạo một mô-đun mới, sau đó kiểm tra nó từ đây`
