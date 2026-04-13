# Phạm vi giảng dạy

> *Repo này chọn dạy xương sống thiết kế, không dạy mọi chi tiết có thể tồn tại trong production.*

## Mục Tiêu

Mục tiêu là giúp bạn tự dựng một coding-agent harness có cấu trúc rõ:

- model call và message loop
- tool definition và dispatch
- planning trong session
- context compaction
- permission, hook, memory, prompt assembly
- task runtime, background work, scheduler
- teams, protocols, autonomy, worktree isolation, MCP

Tài liệu ưu tiên cơ chế quyết định agent có thể làm việc đến nơi đến chốn hay không.

## Cố Ý Không Đặt Ở Trung Tâm

Repo không cố dạy mọi thứ trong một sản phẩm thật:

- packaging và release
- account, billing, enterprise policy
- telemetry chi tiết
- compatibility branch lịch sử
- UI product flow
- provider-specific auth edge cases
- tối ưu performance rất sâu

Những thứ đó quan trọng trong production, nhưng chúng không phải đường học 0-to-1.

## Nguyên Tắc Viết Tài Liệu

- giải thích concept trước khi dùng concept
- một khái niệm chính nên có một nơi giải thích đầy đủ
- đi từ problem -> concept -> minimal implementation -> state -> loop integration
- tránh buộc người mới ghép hệ thống từ quá nhiều fragment
- tách mainline khỏi side detail

## Khi Nào Một Chi Tiết Được Đưa Vào

Một chi tiết đáng đưa vào nếu nó trả lời một câu hỏi cốt lõi:

- model nhìn thấy gì?
- action được thực thi thế nào?
- state sống ở đâu?
- failure được recover ra sao?
- work sống qua session bằng cách nào?
- nhiều actor phối hợp thế nào?
- external capability đi qua safety/routing ra sao?

Nếu một chi tiết chỉ phục vụ product packaging hoặc môi trường cụ thể, nó nên đứng ngoài mainline.

## Cách Người Đọc Nên Dùng Scope Này

Khi thấy tài liệu bỏ qua một chi tiết bạn biết là có trong production, đừng vội xem là thiếu. Hãy hỏi: chi tiết đó có cần để tự dựng xương sống agent không? Nếu không, nó có thể được để dành cho tầng production hardening riêng.
