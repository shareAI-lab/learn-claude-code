# Tool Control Plane

> *Tool không chỉ là bảng lookup. Khi hệ thống lớn lên, tool call phải đi qua một control plane chung trước khi execution xảy ra.*

## Từ Dispatch Đến Control Plane

Ở `s02`, tool dispatch có thể là map đơn giản. Nhưng sau đó tool call cần thêm nhiều bước:

```text
tool_use
  -> normalize intent
  -> permission check
  -> pre_tool hooks
  -> runtime execution
  -> post_tool hooks
  -> result append
```

Đây là tool control plane.

## Vì Sao Quan Trọng

Nếu permission nằm trong từng handler, policy sẽ bị rải rác. Nếu hook tự gọi tool, loop mất quyền kiểm soát. Nếu MCP bypass dispatch map, external tool sẽ không có safety giống native tool.

Control plane giữ mọi action đi qua một đường chung.

## Các Thành Phần

| Thành phần | Vai trò |
|---|---|
| intent normalization | biến raw tool call thành object thống nhất |
| permission gate | allow, deny hoặc ask trước execution |
| hook events | quan sát hoặc annotate ở lifecycle point |
| executor | chạy handler hoặc external capability |
| result writer | append result đúng thứ tự |

## Quy Tắc

- tool handler không tự quyết định policy toàn cục
- hook không nên chiếm control flow của loop
- result luôn quay lại bằng format model đọc được
- native tool và external capability nên cùng đường kiểm soát

Đây là nền để hiểu `s07`, `s08` và `s19`.
