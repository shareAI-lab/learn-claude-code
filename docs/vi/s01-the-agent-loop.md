# Vòng lặp agent (Agent Loop)

> *Agent bắt đầu khi kết quả tool thật được đưa ngược lại cho model, không phải khi model chỉ trả lời một đoạn text.*

## Vấn Đề

Một chatbot chỉ sinh text. Coding agent phải hành động trong môi trường: đọc file, chạy lệnh, sửa code, rồi dùng kết quả thật để quyết định bước tiếp theo.

Vì vậy cơ chế tối thiểu là loop:

```text
messages -> model -> tool_use -> run tool -> tool_result -> messages -> model
```

## Thành Phần Tối Thiểu

- `messages`: lịch sử model đọc được
- model call: tạo text hoặc `tool_use`
- tool runner: thực thi action bên ngoài
- `tool_result`: observation append lại vào messages
- stop condition: biết khi nào trả lời user

## Vì Sao `tool_result` Quan Trọng

Nếu agent đọc file nhưng không append nội dung file lại, model không biết file chứa gì. Nếu shell command lỗi mà result không quay về, model sẽ tiếp tục dựa trên tưởng tượng.

`tool_result` là cầu nối giữa thế giới thật và reasoning của model.

## Minimal Loop

Pseudo-code:

```python
while True:
    response = call_model(messages)
    if response.is_final:
        return response.text
    for tool_call in response.tool_calls:
        result = run_tool(tool_call)
        messages.append(tool_result(tool_call.id, result))
```

Loop nhỏ nhưng đủ thật: model thấy observation mới sau mỗi action.

## Cần Dừng Ở Đâu

Sau chương này, bạn nên tự viết được một agent có thể:

1. nhận user request
2. gọi model
3. nhận một tool call đơn giản
4. chạy handler
5. append result
6. gọi model tiếp hoặc trả lời cuối

Đừng vội thêm permissions, memory hay subagent. Nếu core loop chưa chắc, mọi lớp sau sẽ mơ hồ.
