# Bản đồ module tham chiếu

> *Tài liệu này nối các cụm module trong một hệ agent thật với các chương học, để bạn thấy curriculum không phải tùy tiện.*

## Vì Sao Cần Map Này

Khi nhìn một codebase production, bạn thường không thấy các khái niệm được xếp gọn theo chương. Permissions, prompts, tools, memory và runtime có thể bị rải qua nhiều thư mục. Map này giúp bạn chuyển từ cách đọc giáo trình sang cách đọc hệ thống thật.

## Cụm Module Và Chương Tương Ứng

| Cụm cơ chế | Chương học | Câu hỏi cần giữ |
|---|---|---|
| Agent loop / message runner | `s01` | vòng gọi model và append result ở đâu? |
| Tool registry / dispatch | `s02` | schema cho model và handler thật tách thế nào? |
| Todo / plan state | `s03` | plan trong session khác durable task ra sao? |
| Subagent runner | `s04` | context con được tách và tóm tắt về cha thế nào? |
| Skill loader | `s05` | discovery rẻ và load sâu diễn ra ở đâu? |
| Context compaction | `s06` | detail được chuyển khỏi active context bằng record nào? |
| Permission gate | `s07` | intent bị allow, ask hoặc deny trước execution ở đâu? |
| Hooks | `s08` | lifecycle event được phát ở điểm nào? |
| Memory | `s09` | fact nào sống qua session và được reload ra sao? |
| Prompt builder | `s10` | input model được lắp từ section nào? |
| Recovery | `s11` | failure được phân loại và retry thế nào? |
| Task records | `s12` | durable work graph lưu dependency ra sao? |
| Runtime task slots | `s13` | job đang chạy khác task goal thế nào? |
| Scheduler | `s14` | time trigger đi vào cùng loop bằng cách nào? |
| Teams / protocols | `s15-s16` | teammate và protocol request được định danh thế nào? |
| Autonomy | `s17` | idle agent tự claim work theo policy nào? |
| Worktree lanes | `s18` | execution directory được bind vào task ra sao? |
| MCP / plugins | `s19` | external capability quay lại router chung thế nào? |

## Cách Đọc Production Code

Đừng bắt đầu bằng file lớn nhất. Hãy tìm các boundary trước:

- nơi model call được tạo
- nơi tool definitions được đưa cho model
- nơi tool call được dispatch
- nơi permission hoặc policy chặn execution
- nơi result được append lại
- nơi durable state được ghi

Sau đó mới đọc chi tiết handler.

## Cảnh Báo

Production code thường có nhiều glue code: telemetry, account, compatibility, feature flags. Những thứ đó có thể quan trọng nhưng không phải mainline. Khi bị nhiễu, quay lại câu hỏi: module này có quyết định agent có thể suy luận, hành động, tiếp tục hoặc phối hợp hay không?
