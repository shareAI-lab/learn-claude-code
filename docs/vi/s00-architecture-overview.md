# Tổng quan kiến trúc

> *Muốn hiểu từng chương, trước hết cần thấy toàn bộ hệ thống lớn lên theo những phụ thuộc cơ chế nào.*

## Bức Tranh Lớn

Repo này xây một coding agent theo bốn giai đoạn có thứ tự phụ thuộc rõ ràng:

1. dựng một vòng lặp single-agent thật sự chạy được
2. làm cứng vòng lặp đó bằng safety, memory và recovery
3. biến công việc tạm trong một phiên thành runtime work bền vững
4. mở rộng executor đơn thành nền tảng multi-agent có lane tách biệt và external capability routing

Thứ tự này đi theo **phụ thuộc cơ chế**, không đi theo độ hào nhoáng của tính năng. Nếu chưa nắm chuỗi:

`user input -> model -> tools -> write-back -> next turn`

thì permissions, hooks, memory, tasks, teams, worktrees và MCP sẽ chỉ còn là một đống từ vựng rời rạc.

## Repo Này Đang Tái Dựng Gì

Repo không cố mô phỏng production code từng dòng. Nó tái dựng những phần quyết định một agent system có làm việc được hay không:

- module chính là gì
- các module cộng tác với nhau ra sao
- trạng thái sống ở đâu
- model nhìn thấy gì trong input
- tool result quay lại loop bằng đường nào
- khi nào cần nâng cấp từ cơ chế tối thiểu sang cơ chế bền hơn

Một agent tốt không phải chỉ là model mạnh. Model cần một harness biết cấp context, chạy tools, giữ state, giới hạn rủi ro và tiếp tục công việc qua nhiều lượt.

## Bốn Lớp Cơ Chế

| Lớp | Chương | Câu hỏi chính |
|---|---|---|
| Core loop | `s01-s06` | Một agent đơn làm việc được bằng cách nào? |
| Hardening | `s07-s11` | Làm sao để nó an toàn, mở rộng được và phục hồi được? |
| Runtime | `s12-s14` | Làm sao để công việc sống lâu hơn một chat turn? |
| Platform | `s15-s19` | Làm sao nhiều agent, nhiều lane và external tools cùng vào một control plane? |

## Luồng Cốt Lõi

Mọi chương đều quay lại một chuỗi nền:

```text
user request
  -> model call
  -> tool_use
  -> permission / hook / runtime control
  -> tool execution
  -> tool_result
  -> append back into messages
  -> next model call
```

`tool_result` là điểm nối quan trọng: nó biến hành động bên ngoài thành bằng chứng mà model có thể đọc ở lượt kế tiếp.

## Cách Đọc

Đừng đọc mỗi chương như một tính năng riêng. Hãy hỏi:

- cơ chế này thêm capability gì so với chương trước?
- trạng thái mới nằm trong record nào?
- nó can thiệp trước model call, trong tool execution hay sau result?
- nếu bỏ nó đi, agent sẽ hỏng theo kiểu nào?

Nếu trả lời được những câu đó, bạn đang học kiến trúc chứ không chỉ nhớ tên module.
