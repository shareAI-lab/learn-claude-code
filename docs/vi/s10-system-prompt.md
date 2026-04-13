# Prompt hệ thống (System Prompt)

> *Model không nhìn thấy một chuỗi prompt ma thuật. Nó nhìn thấy input được lắp từ nhiều section có thứ tự.*

## Vấn Đề

Khi hệ thống có tools, permissions, memory, task focus và workspace state, prompt tĩnh sẽ khó quản lý. Bạn cần prompt assembly pipeline.

## PromptParts

Một input có thể gồm:

- role và behavior rules
- workspace state
- tool catalog
- permission mode
- memory context
- current plan/task focus
- compact summary
- user message

Mỗi phần có nguồn và mục đích riêng.

## Vì Sao Cần Section

- dễ kiểm tra model thật sự thấy gì
- dễ thay đổi một phần mà không phá toàn prompt
- memory và task focus có thể inject động
- permission hoặc runtime mode có thể hiển thị rõ

## Luồng

```text
collect stable rules
  -> collect runtime state
  -> load relevant memory
  -> add tool specs
  -> add current user/request context
  -> build final model input
```

## Ranh Giới

Prompt không nên chứa mọi dữ liệu thô. File content lớn nên đến từ tool result. Memory phải ngắn. Compact summary phải nói rõ fact, pending work và decisions.

## Bài Tập Tối Thiểu

Tạo `PromptParts` với các section có tên, rồi render thành system input. Thêm một debug function in ra prompt cuối để kiểm tra.

Sau chương này, prompt trở thành pipeline có thể lý giải, không phải string khó đoán.
