# MCP và Plugin

> *External capabilities không nên là đường vòng. Chúng phải quay lại cùng routing, permission và result append path như native tools.*

## Vấn Đề

Agent có thể cần năng lực ngoài process: database, browser, GitHub, file store, internal APIs. MCP và plugins đưa năng lực đó vào hệ thống.

Nhưng nếu external tools bypass control plane, bạn mất safety và observability.

## CapabilityRoute

Một route nên mô tả:

- capability name
- server/plugin source
- input schema
- permission scope
- handler/transport
- result format

## Luồng

```text
model requests capability
  -> route lookup
  -> permission check
  -> call MCP server/plugin/native handler
  -> normalize result
  -> append tool_result
```

## MCP Không Chỉ Là Tool List

MCP server có thể cung cấp resources, tools, prompts hoặc domain-specific capabilities. Harness cần biến chúng thành surface model hiểu được mà vẫn giữ policy chung.

## Native Tool vs External Capability

| Native tool | External capability |
|---|---|
| handler trong process | server/plugin bên ngoài |
| local permission đơn giản hơn | scope/auth/transport phức tạp hơn |
| result trực tiếp | cần normalize |

Cả hai vẫn phải vào cùng loop.

## Bài Tập Tối Thiểu

Tạo registry có native route và fake MCP route. Cho cả hai đi qua cùng permission + dispatch + result append. Nếu external route có thể bypass, thiết kế chưa xong.
