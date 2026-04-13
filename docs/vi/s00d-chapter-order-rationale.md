# Vì sao sắp chương như vậy

> *Thứ tự chương không phải danh sách tính năng. Nó là thứ tự mà một developer có thể xây lại hệ thống mà không bị thiếu nền.*

## Quy Tắc Sắp Thứ Tự

Một cơ chế chỉ nên xuất hiện sau khi người đọc đã có đủ nền để hiểu nó giải quyết vấn đề gì. Vì vậy repo đi từ loop nhỏ nhất, rồi mới thêm các lớp quanh nó.

Nếu đưa MCP, teams hoặc autonomy quá sớm, người đọc sẽ thấy nhiều object nhưng không biết chúng nối vào loop ở đâu. Nếu nói permission trước tool runtime, bạn chưa có action thật để gate. Nếu nói durable task trước todo, bạn chưa thấy sự khác nhau giữa plan trong phiên và work graph sống lâu.

## Bốn Pha

| Pha | Lý do phải đứng ở đây |
|---|---|
| `s01-s06` | cần một single-agent core trước khi thêm control plane |
| `s07-s11` | khi loop đã chạy, mới cần safety, hooks, memory, prompt và recovery |
| `s12-s14` | sau session planning mới hiểu durable task và background runtime |
| `s15-s19` | sau runtime mới có nền để nói teams, autonomy, worktree và MCP |

## Điều Gì Hỏng Nếu Đảo Thứ Tự

- Học `s12` trước `s03`: task graph dễ bị nhầm với todo list.
- Học `s08` trước `s02`: hook không có lifecycle tool execution để bám.
- Học `s10` trước `s09`: prompt pipeline thiếu nguồn durable context.
- Học `s18` trước `s12`: worktree bị nhầm là task thay vì execution lane.
- Học `s19` trước `s02`: MCP bị hiểu như “tool lạ” thay vì capability routing vào cùng bus.

## Cách Dùng Thứ Tự Này

Đọc mỗi chương như một upgrade nhỏ:

1. chương trước đã có gì?
2. chương này thêm capability nào?
3. state mới nằm ở đâu?
4. loop phải đổi ở điểm nào?
5. sau chương này có thể tự dựng phiên bản tối thiểu không?

Nếu câu trả lời chưa rõ, đừng vội nhảy chương. Quay lại bridge docs, data structures hoặc entity map.

## Mục Tiêu Của Thứ Tự

Đến cuối repo, bạn không chỉ biết nhiều thuật ngữ hơn. Bạn phải có thể tự dựng một harness theo từng lớp: loop, tools, planning, context, control plane, runtime, platform. Đó là lý do thứ tự này quan trọng.
