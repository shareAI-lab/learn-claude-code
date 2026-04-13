# Query Control Plane

> *Khi agent lớn lên, một request không còn đi thẳng từ user vào model rồi ra tool. Nó phải đi qua một control plane biết lắp context, áp policy, chạy hooks và quyết định vì sao vòng lặp tiếp tục.*

## Vì Sao Cần Control Plane

Vòng lặp ở `s01` có thể rất nhỏ: gửi messages cho model, chạy tool, append result, lặp lại. Nhưng sau vài chương, cùng một request bắt đầu cần nhiều quyết định hơn:

- có memory nào phải nạp không?
- prompt cần những section nào?
- tool call có được phép chạy không?
- hook nào cần quan sát hoặc chặn?
- lỗi này là dừng, retry hay recover?
- MCP capability có đi qua cùng đường với native tool không?

Control plane là lớp điều phối các quyết định đó. Nó không thay model suy luận. Nó quyết định **môi trường làm việc** mà model đang đứng trong đó.

## Một Query Đi Qua Những Gì

```text
incoming query
  -> load durable context
  -> assemble prompt / messages
  -> call model
  -> inspect requested actions
  -> apply permissions and hooks
  -> execute tools or route capabilities
  -> append results
  -> decide continuation reason
```

Mỗi bước giữ cho hệ thống rõ ràng hơn. Nếu mọi thứ bị nhét vào một hàm `run_agent()`, bạn sẽ rất khó biết lỗi đến từ prompt, permission, tool runtime hay recovery branch.

## Những Cơ Chế Nối Vào Đây

| Cơ chế | Vai trò trong control plane |
|---|---|
| Permission | chặn intent trước khi thành execution |
| Hook | quan sát, annotate hoặc block ở lifecycle point |
| Memory | nạp durable facts trước model call |
| Prompt assembly | dựng input có cấu trúc thay vì một chuỗi lớn |
| Error recovery | quyết định lý do tiếp tục sau failure |
| MCP routing | đưa external capability vào cùng tool path |

## Ranh Giới Quan Trọng

Control plane không phải business logic của task. Nó cũng không phải model reasoning. Nó là phần harness giữ cho request đi đúng đường, có policy, có observability và có trạng thái tiếp tục rõ ràng.

Khi đọc các chương giữa và cuối, hãy luôn hỏi: cơ chế này đang thêm một nhánh mới vào control plane hay chỉ là một tool handler mới?
