# Thứ tự đọc code

> *Đọc code theo đúng thứ tự giúp bạn thấy hệ thống lớn lên từng lớp, thay vì bị chìm trong chi tiết.*

## Quy Tắc Chung

Mỗi file trong `agents/` là một lát hệ thống có thể chạy. Đừng đọc như một thư viện hoàn chỉnh. Hãy đọc như lịch sử tăng trưởng của harness.

Với mỗi chương, trước hết tìm:

1. state record mới
2. function hoặc class mới điều phối state đó
3. điểm nối vào agent loop
4. ví dụ tool result hoặc runtime result quay lại model

## Thứ Tự Nên Mở

| Bước | File | Nhìn gì trước |
|---|---|---|
| 1 | `s01_agent_loop.py` | `messages`, model call, `tool_result` |
| 2 | `s02_tool_use.py` | `ToolSpec`, dispatch map |
| 3 | `s03_todo_write.py` | `TodoItem`, plan reminder |
| 4 | `s04_subagent.py` | parent messages và child messages |
| 5 | `s05_skill_loading.py` | registry và load-on-demand |
| 6 | `s06_context_compact.py` | markers, summary, compact trigger |
| 7 | `s07_permission_system.py` | deny / allow / ask pipeline |
| 8 | `s08_hook_system.py` | lifecycle event |
| 9 | `s09_memory_system.py` | memory entry và reload path |
| 10 | `s10_system_prompt.py` | prompt sections |
| 11 | `s11_error_recovery.py` | recovery state và retry branch |
| 12 | `s12_task_system.py` | task record và dependency |
| 13 | `s13_background_tasks.py` | runtime slot và notification |
| 14 | `s14_cron_scheduler.py` | schedule record và trigger |
| 15 | `s15_agent_teams.py` | teammate lifecycle |
| 16 | `s16_team_protocols.py` | protocol envelope |
| 17 | `s17_autonomous_agents.py` | claim policy và resume context |
| 18 | `s18_worktree_task_isolation.py` | worktree record và closeout |
| 19 | `s19_mcp_plugin.py` | capability route |

## Cách Đọc Một File

Đừng bắt đầu từ mọi branch nhỏ. Đi theo thứ tự:

1. đọc data structures
2. đọc tool definitions
3. đọc loop hoặc runner
4. đọc nơi state được update
5. đọc demo path ở cuối file

Nếu file có nhiều helper, chỉ đọc helper sau khi biết nó phục vụ state nào.

## Khi Nào Đọc `s_full.py`

Đọc `s_full.py` sau cùng. Nó hữu ích để thấy các cơ chế nối lại trong một hình lớn, nhưng nếu đọc quá sớm bạn sẽ nhầm mainline với glue code.

Mục tiêu không phải nhớ mọi dòng. Mục tiêu là có thể chỉ vào từng phần và nói: phần này thuộc loop, tool runtime, control plane, durable task hay platform boundary.
