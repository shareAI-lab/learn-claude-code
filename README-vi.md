[English](./README.md) | [中文](./README-zh.md) | [日本語](./README-ja.md) | [Tiếng Việt](./README-vi.md)

# Learn Claude Code

Kho tài liệu này dành cho người muốn tự xây một `coding-agent harness` từ con số 0: bắt đầu bằng vòng lặp agent nhỏ nhất, rồi dần thêm công cụ, kế hoạch, quyền hạn, bộ nhớ, tác vụ, đội agent và MCP.

Mục tiêu không phải là sao chép từng chi tiết của một hệ thống production. Mục tiêu là hiểu các cơ chế cốt lõi đủ rõ để bạn có thể tự dựng lại.

## Kho Này Dạy Gì

Một câu ngắn trước:

**Mô hình chịu trách nhiệm suy luận. Harness cung cấp môi trường làm việc cho mô hình.**

Môi trường đó gồm các phần chính:

- `Agent Loop`: gọi mô hình, chạy công cụ, đưa kết quả quay lại ngữ cảnh, rồi lặp tiếp
- `Tools`: tay của agent, như đọc file, sửa file, chạy lệnh, tìm kiếm
- `Planning`: cấu trúc nhỏ giúp việc nhiều bước không trôi khỏi mục tiêu
- `Context Management`: giữ ngữ cảnh đang hoạt động nhỏ và mạch lạc
- `Permissions`: chặn thao tác rủi ro trước khi biến ý định của mô hình thành hành động thật
- `Hooks`: mở rộng hành vi quanh vòng lặp mà không phải viết lại vòng lặp
- `Memory`: chỉ lưu các sự kiện bền vững cần sống qua nhiều phiên
- `Prompt Construction`: lắp đầu vào cho mô hình từ luật ổn định và trạng thái runtime
- `Tasks / Teams / Worktree / MCP`: đưa lõi một agent thành nền tảng làm việc lớn hơn

## Không Dạy Gì

Kho này cố ý không đặt các chi tiết sản phẩm ở trung tâm bài học:

- đóng gói, build, release
- lớp tương thích đa nền tảng
- wiring cho enterprise policy, telemetry, tài khoản
- nhánh tương thích lịch sử
- tên gọi hoặc glue code chỉ có ý nghĩa trong một môi trường nội bộ cụ thể

Các chi tiết đó có thể quan trọng trong production, nhưng không nên che mất đường học 0-to-1.

## Dành Cho Ai

Người đọc được giả định là:

- biết Python cơ bản
- hiểu hàm, lớp, list, dictionary
- có thể mới hoàn toàn với agent system

Vì vậy tài liệu cố gắng:

- giải thích khái niệm trước khi dùng
- giữ mỗi khái niệm chính ở một nơi đủ đầy
- đi từ "nó là gì", sang "vì sao cần", rồi đến "cài thế nào"
- tránh bắt người mới tự ghép hệ thống từ nhiều mảnh rời rạc

## Thứ Tự Đọc Đề Xuất

Bản `vi` giữ cùng cấu trúc chương, bridge docs và bản đồ cơ chế với các locale còn lại, để bạn có thể đi theo một tuyến đọc ổn định.

- Tổng quan: [`docs/vi/s00-architecture-overview.md`](./docs/vi/s00-architecture-overview.md)
- Thứ tự đọc code: [`docs/vi/s00f-code-reading-order.md`](./docs/vi/s00f-code-reading-order.md)
- Thuật ngữ: [`docs/vi/glossary.md`](./docs/vi/glossary.md)
- Phạm vi giảng dạy: [`docs/vi/teaching-scope.md`](./docs/vi/teaching-scope.md)
- Cấu trúc dữ liệu: [`docs/vi/data-structures.md`](./docs/vi/data-structures.md)

## Lần Đầu Vào Repo, Bắt Đầu Ở Đây

Đừng mở ngẫu nhiên từng chương.

Đường đi ổn định nhất là:

1. Đọc [`docs/vi/s00-architecture-overview.md`](./docs/vi/s00-architecture-overview.md) để nắm bản đồ toàn hệ thống.
2. Đọc [`docs/vi/s00d-chapter-order-rationale.md`](./docs/vi/s00d-chapter-order-rationale.md) để hiểu vì sao thứ tự chương được sắp như vậy.
3. Đọc [`docs/vi/s00f-code-reading-order.md`](./docs/vi/s00f-code-reading-order.md) để biết nên mở các file `agents/*.py` theo thứ tự nào.
4. Đi qua bốn giai đoạn: `s01-s06 -> s07-s11 -> s12-s14 -> s15-s19`.
5. Sau mỗi giai đoạn, dừng lại và tự dựng phiên bản nhỏ nhất trước khi đọc tiếp.

Nếu đến giữa hoặc cuối khóa mà các khái niệm bắt đầu lẫn vào nhau, quay lại theo thứ tự:

1. [`docs/vi/data-structures.md`](./docs/vi/data-structures.md)
2. [`docs/vi/entity-map.md`](./docs/vi/entity-map.md)
3. bridge doc gần nhất với chương đang kẹt
4. rồi trở lại thân chương

## Giao Diện Web

Bạn có thể chạy trang học trực quan có sẵn:

```sh
cd web
npm install
npm run dev
```

Các route hữu ích:

- `/vi`: điểm vào tiếng Việt
- `/vi/timeline`: xem toàn bộ tuyến học từ `s01` đến `s19`
- `/vi/layers`: xem ranh giới bốn giai đoạn
- `/vi/compare`: so sánh hai chương khi bắt đầu thấy mờ ranh giới

## Bridge Docs

Đây không phải chương chính mới. Chúng là tài liệu nối giúp các phần giữa và cuối dễ nắm hơn:

- Vì sao thứ tự chương như vậy: [`docs/vi/s00d-chapter-order-rationale.md`](./docs/vi/s00d-chapter-order-rationale.md)
- Thứ tự đọc code: [`docs/vi/s00f-code-reading-order.md`](./docs/vi/s00f-code-reading-order.md)
- Bản đồ module tham chiếu: [`docs/vi/s00e-reference-module-map.md`](./docs/vi/s00e-reference-module-map.md)
- Query control plane: [`docs/vi/s00a-query-control-plane.md`](./docs/vi/s00a-query-control-plane.md)
- Một vòng đời request: [`docs/vi/s00b-one-request-lifecycle.md`](./docs/vi/s00b-one-request-lifecycle.md)
- Query transition model: [`docs/vi/s00c-query-transition-model.md`](./docs/vi/s00c-query-transition-model.md)
- Tool control plane: [`docs/vi/s02a-tool-control-plane.md`](./docs/vi/s02a-tool-control-plane.md)
- Tool execution runtime: [`docs/vi/s02b-tool-execution-runtime.md`](./docs/vi/s02b-tool-execution-runtime.md)
- Message and prompt pipeline: [`docs/vi/s10a-message-prompt-pipeline.md`](./docs/vi/s10a-message-prompt-pipeline.md)
- Runtime task model: [`docs/vi/s13a-runtime-task-model.md`](./docs/vi/s13a-runtime-task-model.md)
- MCP capability layers: [`docs/vi/s19a-mcp-capability-layers.md`](./docs/vi/s19a-mcp-capability-layers.md)
- Team-task-lane model: [`docs/vi/team-task-lane-model.md`](./docs/vi/team-task-lane-model.md)
- Entity map: [`docs/vi/entity-map.md`](./docs/vi/entity-map.md)

## Bốn Giai Đoạn

1. `s01-s06`: dựng lõi single-agent hữu dụng
2. `s07-s11`: thêm an toàn, điểm mở rộng, memory, prompt assembly và recovery
3. `s12-s14`: biến kế hoạch tạm thời trong phiên thành runtime work bền vững
4. `s15-s19`: đi vào teams, protocols, autonomy, worktree isolation và external capability routing

## Các Chương Chính

| Chương | Chủ đề | Kết quả |
|---|---|---|
| `s00` | Architecture Overview | bản đồ toàn hệ thống, thuật ngữ, thứ tự học |
| `s01` | Agent Loop | vòng lặp agent nhỏ nhất có thể chạy |
| `s02` | Tool Use | lớp dispatch công cụ ổn định |
| `s03` | Todo / Planning | kế hoạch phiên có thể nhìn thấy |
| `s04` | Subagent | ngữ cảnh mới cho mỗi subtask được giao |
| `s05` | Skills | chỉ nạp tri thức chuyên biệt khi cần |
| `s06` | Context Compact | giữ active context nhỏ |
| `s07` | Permission System | cổng an toàn trước khi thực thi |
| `s08` | Hook System | điểm mở rộng quanh loop |
| `s09` | Memory System | thông tin dài hạn qua nhiều phiên |
| `s10` | System Prompt | lắp prompt theo từng section |
| `s11` | Error Recovery | nhánh tiếp tục và retry |
| `s12` | Task System | đồ thị tác vụ bền vững |
| `s13` | Background Tasks | thực thi không chặn |
| `s14` | Cron Scheduler | trigger theo thời gian |
| `s15` | Agent Teams | teammate tồn tại lâu dài |
| `s16` | Team Protocols | luật phối hợp chung |
| `s17` | Autonomous Agents | tự nhận việc và tự resume |
| `s18` | Worktree Isolation | lane thực thi tách biệt |
| `s19` | MCP & Plugin | routing năng lực bên ngoài |

## Quick Start

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env
```

Sau đó cấu hình `ANTHROPIC_API_KEY` hoặc endpoint tương thích trong `.env`, rồi chạy:

```sh
python agents/s01_agent_loop.py
python agents/s18_worktree_task_isolation.py
python agents/s19_mcp_plugin.py
python agents/s_full.py
```

## Cấu Trúc

```text
learn-claude-code/
├── agents/              # tham chiếu Python chạy được theo từng chương
├── docs/en/             # tài liệu tiếng Anh
├── docs/zh/             # tài liệu tiếng Trung
├── docs/ja/             # tài liệu tiếng Nhật
├── docs/vi/             # tài liệu tiếng Việt
├── skills/              # skill files dùng trong s05
├── web/                 # giao diện học web
└── requirements.txt
```

## Đích Cuối

Khi đọc xong, bạn nên trả lời được bằng lời của mình:

- trạng thái tối thiểu của một coding agent là gì
- vì sao `tool_result` là trung tâm của loop
- khi nào nên dùng subagent
- permissions, hooks, memory, prompt và task giải quyết vấn đề nào
- khi nào nên phát triển single agent thành tasks, teams, worktrees và MCP
