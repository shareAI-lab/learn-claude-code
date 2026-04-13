# Tool Execution Runtime

> *Khi một turn có nhiều tool call, runtime phải quyết định chạy song song hay tuần tự, giữ thứ tự result và gom observation đúng cách.*

## Vấn Đề

Model có thể yêu cầu nhiều tool call trong một lượt. Một số tool an toàn để chạy song song, một số phải chạy tuần tự:

- đọc nhiều file: thường có thể song song
- ghi cùng file: phải cẩn thận thứ tự
- shell command phá hủy: cần permission và isolation
- background job: không nên block loop mãi

## Runtime Phải Quản Gì

| Trách nhiệm | Câu hỏi |
|---|---|
| scheduling | tool nào chạy trước? |
| concurrency | tool nào có thể song song? |
| progress | user có cần biết đang chạy gì không? |
| ordering | result append theo thứ tự nào? |
| failure | một tool lỗi có làm dừng cả batch không? |
| context merge | nhiều result nhập lại messages ra sao? |

## Result Order

Model cần đọc result đúng với tool call ID. Vì vậy runtime không chỉ chạy nhanh. Nó phải trả result có identity rõ:

```text
tool_call_id=a -> result a
tool_call_id=b -> result b
```

Nếu thứ tự hoặc ID sai, vòng sau sẽ suy luận trên dữ liệu nhầm.

## Nối Với Các Chương Sau

- `s07`: permission chạy trước execution
- `s08`: hooks bám quanh pre/post tool
- `s13`: slow tool có thể thành background task
- `s19`: MCP tool cũng phải đi qua runtime tương tự

Tool execution runtime là nơi action thật được quản lý có kỷ luật.
