# s01: Vòng lặp Agent (The Agent Loop)

`[ s01 ] s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Một vòng lặp & Bash là tất cả những gì bạn cần"* -- một công cụ + một vòng lặp = một agent.
>
> **Lớp Harness**: Vòng lặp -- kết nối đầu tiên của model với thế giới thực.

## Vấn đề (Problem)

Một mô hình ngôn ngữ có thể tư duy về code, nhưng nó không thể *chạm* vào thế giới thực -- không thể đọc file, chạy kiểm thử, hoặc kiểm tra lỗi. Nếu không có vòng lặp, mỗi lần gọi công cụ bạn lại phải copy-paste kết quả ngược trở lại một cách thủ công. Bạn chính là vòng lặp đó.

## Giải pháp (Solution)

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> |  Tool   |
| prompt |      |       |      | execute |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                    (vòng lặp cho đến khi stop_reason != "tool_use")
```

Một điều kiện thoát kiểm soát toàn bộ luồng. Vòng lặp chạy cho đến khi model dừng gọi các công cụ.

## Cách hoạt động (How It Works)

1. Prompt của người dùng trở thành tin nhắn đầu tiên.

```python
messages.append({"role": "user", "content": query})
```

2. Gửi các tin nhắn + định nghĩa công cụ tới LLM.

```python
response = client.messages.create(
    model=MODEL, system=SYSTEM, messages=messages,
    tools=TOOLS, max_tokens=8000,
)
```

3. Thêm phản hồi của trợ lý vào danh sách. Kiểm tra `stop_reason` -- nếu model không gọi công cụ, chúng ta đã hoàn thành.

```python
messages.append({"role": "assistant", "content": response.content})
if response.stop_reason != "tool_use":
    return
```

4. Thực thi từng yêu cầu gọi công cụ, thu thập kết quả, thêm vào danh sách dưới dạng tin nhắn của người dùng. Quay lại bước 2.

```python
results = []
for block in response.content:
    if block.type == "tool_use":
        output = run_bash(block.input["command"])
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
messages.append({"role": "user", "content": results})
```

Tất cả được gộp vào một hàm:

```python
def agent_loop(query):
    messages = [{"role": "user", "content": query}]
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_bash(block.input["command"])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

Đó là toàn bộ một agent trong chưa đầy 30 dòng code. Mọi thứ khác trong khóa học này sẽ được xây dựng chồng lên trên -- mà không thay đổi vòng lặp này.

## Những gì đã thay đổi (What Changed)

| Thành phần     | Trước     | Sau                             |
|----------------|-----------|---------------------------------|
| Vòng lặp Agent | (không có)| `while True` + stop_reason      |
| Công cụ        | (không có)| `bash` (một công cụ)            |
| Tin nhắn       | (không có)| Danh sách tích lũy              |
| Luồng điều khiển| (không có)| `stop_reason != "tool_use"`     |

## Dùng thử (Try It)

```sh
cd learn-claude-code
python agents/s01_agent_loop.py
```

1. `Tạo một file tên là hello.py in ra "Hello, World!"`
2. `Liệt kê tất cả các file Python trong thư mục này`
3. `Nhánh git hiện tại là gì?`
4. `Tạo một thư mục tên là test_output và ghi 3 file vào đó`
