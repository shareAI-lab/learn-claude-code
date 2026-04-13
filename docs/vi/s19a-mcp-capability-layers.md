# MCP Capability Layers

> *MCP nằm trong một capability stack rộng hơn: model surface, routing, permission, transport và result write-back.*

## Các Lớp

| Lớp | Câu hỏi |
|---|---|
| Model surface | model thấy capability dưới dạng gì? |
| Capability registry | capability được đăng ký ở đâu? |
| Routing | request đi đến native tool, plugin hay MCP server? |
| Permission | scope nào được phép? |
| Transport | gọi server bên ngoài bằng cách nào? |
| Normalization | result chuyển về format chung ra sao? |
| Write-back | model đọc result ở lượt sau thế nào? |

## Vì Sao Cần Stack

Nếu chỉ xem MCP là “thêm tool”, bạn sẽ bỏ qua auth, scope, result normalization và lifecycle. Nếu xem MCP là hệ riêng, bạn sẽ tạo hai đường execution khác nhau.

Stack giúp external capability gia nhập hệ thống mà không phá invariant của agent loop.

## Ví Dụ Luồng

```text
MCP tool spec exposed to model
  -> model emits tool_use
  -> capability router picks server
  -> permission checks scope
  -> transport sends request
  -> response normalized
  -> tool_result appended
```

## Ranh Giới

MCP server không nên tự quyết định toàn bộ task flow. Nó cung cấp capability. Harness vẫn điều phối model input, permission, runtime và result.

## Câu Hỏi Khi Thiết Kế

- capability này có schema rõ không?
- scope permission là gì?
- result có deterministic enough để model dùng không?
- failure có recovery path không?
- logs/debug có chỉ ra server nào được gọi không?

Trả lời được các câu này thì MCP mới nằm đúng trong platform boundary.
