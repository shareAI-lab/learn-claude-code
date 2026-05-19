# s06: Nén ngữ cảnh (Context Compact)

`s01 > s02 > s03 > s04 > s05 > [ s06 ] | s07 > s08 > s09 > s10 > s11 > s12`

> *"Ngữ cảnh sẽ bị lấp đầy; bạn cần một cách để tạo ra không gian"* -- chiến lược nén ba lớp cho các phiên làm việc vô tận.
>
> **Lớp điều khiển (Harness layer)**: Nén (Compression) -- dọn dẹp bộ nhớ cho các phiên làm việc vô tận.

## Vấn đề

Cửa sổ ngữ cảnh (context window) là hữu hạn. Một lệnh `read_file` duy nhất trên một tệp 1000 dòng tiêu tốn khoảng 4000 token. Sau khi đọc 30 tệp và chạy 20 lệnh bash, bạn sẽ chạm mức 100,000+ token. Agent không thể làm việc trên các cơ sở mã (codebase) lớn nếu không có cơ chế nén.

## Giải pháp

Ba lớp nén với mức độ quyết liệt tăng dần:

```
Mỗi lượt:
+--------------------------+
| Kết quả gọi công cụ      |
+--------------------------+
        |
        v
[Lớp 1: micro_compact]          (âm thầm, mỗi lượt)
  Thay thế tool_result cũ > 3 lượt
  bằng "[Trước đó: đã dùng {tool_name}]"
        |
        v
[Kiểm tra: token > 50000?]
   |               |
   không           có
   |               |
   v               v
tiếp tục    [Lớp 2: auto_compact]
              Lưu bản ghi vào .transcripts/
              LLM tóm tắt cuộc hội thoại.
              Thay thế tất cả tin nhắn bằng [tóm tắt].
                    |
                    v
            [Lớp 3: công cụ compact]
              Mô hình gọi công cụ compact một cách rõ ràng.
              Cùng cơ chế tóm tắt như auto_compact.
```

## Cách thức hoạt động

1. **Lớp 1 -- micro_compact**: Trước mỗi lần gọi LLM, thay thế các kết quả công cụ cũ bằng các trình giữ chỗ (placeholders).

```python
def micro_compact(messages: list) -> list:
    tool_results = []
    for i, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            for j, part in enumerate(msg["content"]):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    tool_results.append((i, j, part))
    if len(tool_results) <= KEEP_RECENT:
        return messages
    for _, _, part in tool_results[:-KEEP_RECENT]:
        if len(part.get("content", "")) > 100:
            part["content"] = f"[Trước đó: đã dùng {tool_name}]"
    return messages
```

2. **Lớp 2 -- auto_compact**: Khi số lượng token vượt quá ngưỡng, lưu bản ghi đầy đủ vào đĩa, sau đó yêu cầu LLM tóm tắt.

```python
def auto_compact(messages: list) -> list:
    # Lưu bản ghi để khôi phục khi cần
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    # LLM thực hiện tóm tắt
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Tóm tắt cuộc hội thoại này để đảm bảo tính liên tục..."
            + json.dumps(messages, default=str)[:80000]}],
        max_tokens=2000,
    )
    return [
        {"role": "user", "content": f"[Đã nén]\n\n{response.content[0].text}"},
    ]
```

3. **Lớp 3 -- nén thủ công (manual compact)**: Công cụ `compact` kích hoạt cùng một cơ chế tóm tắt theo yêu cầu.

4. Vòng lặp tích hợp cả ba:

```python
def agent_loop(messages: list):
    while True:
        micro_compact(messages)                        # Lớp 1
        if estimate_tokens(messages) > THRESHOLD:
            messages[:] = auto_compact(messages)       # Lớp 2
        response = client.messages.create(...)
        # ... thực thi công cụ ...
        if manual_compact:
            messages[:] = auto_compact(messages)       # Lớp 3
```

Các bản ghi (transcripts) bảo tồn toàn bộ lịch sử trên đĩa. Không có gì thực sự bị mất -- chúng chỉ được chuyển ra khỏi ngữ cảnh hoạt động.

## Những thay đổi so với s05

| Thành phần     | Trước (s05)      | Sau (s06)                  |
|----------------|------------------|----------------------------|
| Công cụ        | 5                | 5 (cơ bản + compact)       |
| Quản lý ngữ cảnh| Không            | Nén ba lớp                 |
| Micro-compact  | Không            | Kết quả cũ -> trình giữ chỗ|
| Auto-compact   | Không            | Kích hoạt khi vượt ngưỡng  |
| Bản ghi        | Không            | Lưu vào .transcripts/      |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s06_context_compact.py
```

1. `Đọc từng tệp Python trong thư mục agents/ một cách tuần tự` (quan sát micro-compact thay thế các kết quả cũ)
2. `Tiếp tục đọc các tệp cho đến khi quá trình nén tự động được kích hoạt`
3. `Sử dụng công cụ compact để nén cuộc hội thoại một cách thủ công`
