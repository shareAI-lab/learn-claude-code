# s07: Hệ thống tác vụ (Task System)

`s01 > s02 > s03 > s04 > s05 > s06 | [ s07 ] s08 > s09 > s10 > s11 > s12`

> *"Chia nhỏ các mục tiêu lớn thành các tác vụ nhỏ, sắp xếp thứ tự chúng, lưu trữ bền vững vào đĩa"* -- một đồ thị tác vụ dựa trên tệp với các phụ thuộc, đặt nền móng cho sự cộng tác đa agent.
>
> **Lớp điều khiển (Harness layer)**: Tác vụ bền vững (Persistent tasks) -- các mục tiêu tồn tại lâu hơn bất kỳ phiên hội thoại đơn lẻ nào.

## Vấn đề

TodoManager của s03 là một danh sách kiểm tra phẳng trong bộ nhớ: không có thứ tự, không có phụ thuộc, không có trạng thái nào khác ngoài việc xong hay chưa. Các mục tiêu thực tế luôn có cấu trúc -- tác vụ B phụ thuộc vào tác vụ A, tác vụ C và D có thể chạy song song, tác vụ E đợi cả C và D.

Nếu không có các mối quan hệ rõ ràng, agent không thể biết cái gì đã sẵn sàng, cái gì bị chặn, hoặc cái gì có thể chạy đồng thời. Và bởi vì danh sách chỉ nằm trong bộ nhớ, việc nén ngữ cảnh (s06) sẽ xóa sạch nó.

## Giải pháp

Nâng cấp danh sách kiểm tra thành một **đồ thị tác vụ (task graph)** được lưu trữ bền vững trên đĩa. Mỗi tác vụ là một tệp JSON chứa trạng thái và các phụ thuộc (`blockedBy`). Đồ thị này trả lời ba câu hỏi tại bất kỳ thời điểm nào:

- **Cái gì đã sẵn sàng?** -- các tác vụ có trạng thái `pending` và `blockedBy` trống.
- **Cái gì đang bị chặn?** -- các tác vụ đang chờ các phụ thuộc chưa hoàn thành.
- **Cái gì đã xong?** -- các tác vụ `completed`, việc hoàn thành chúng sẽ tự động gỡ chặn cho các tác vụ phụ thuộc.

```
.tasks/
  task_1.json  {"id":1, "status":"completed"}
  task_2.json  {"id":2, "blockedBy":[1], "status":"pending"}
  task_3.json  {"id":3, "blockedBy":[1], "status":"pending"}
  task_4.json  {"id":4, "blockedBy":[2,3], "status":"pending"}

Đồ thị tác vụ (DAG):
                 +----------+
            +--> | tác vụ 2 | --+
            |    | pending  |   |
+----------+     +----------+    +--> +----------+
| tác vụ 1 |                          | tác vụ 4 |
| completed| --> +----------+    +--> | bị chặn  |
+----------+     | tác vụ 3 | --+     +----------+
                 | pending  |
                 +----------+

Thứ tự:        tác vụ 1 phải xong trước 2 và 3
Song song:     tác vụ 2 và 3 có thể chạy cùng lúc
Phụ thuộc:     tác vụ 4 chờ cả 2 và 3
Trạng thái:    pending -> in_progress -> completed
```

Đồ thị tác vụ này trở thành khung xương điều phối cho mọi thứ sau s07: thực thi nền (s08), các nhóm đa agent (s09+), và cách ly không gian làm việc (s12) đều đọc từ và ghi vào cùng một cấu trúc này.

## Cách thức hoạt động

1. **TaskManager**: mỗi tác vụ một tệp JSON, thực hiện CRUD với đồ thị phụ thuộc.

```python
class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def create(self, subject, description=""):
        task = {"id": self._next_id, "subject": subject,
                "status": "pending", "blockedBy": [],
                "owner": ""}
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2)
```

2. **Giải quyết phụ thuộc**: khi hoàn thành một tác vụ, ID của nó sẽ được xóa khỏi danh sách `blockedBy` của mọi tác vụ khác, tự động gỡ chặn cho các tác vụ phụ thuộc.

```python
def _clear_dependency(self, completed_id):
    for f in self.dir.glob("task_*.json"):
        task = json.loads(f.read_text())
        if completed_id in task.get("blockedBy", []):
            task["blockedBy"].remove(completed_id)
            self._save(task)
```

3. **Kết nối trạng thái + phụ thuộc**: `update` xử lý các bước chuyển đổi và các cạnh phụ thuộc.

```python
def update(self, task_id, status=None,
           add_blocked_by=None, remove_blocked_by=None):
    task = self._load(task_id)
    if status:
        task["status"] = status
        if status == "completed":
            self._clear_dependency(task_id)
    if add_blocked_by:
        task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
    if remove_blocked_by:
        task["blockedBy"] = [x for x in task["blockedBy"] if x not in remove_blocked_by]
    self._save(task)
```

4. Bốn công cụ tác vụ được đưa vào bản đồ điều phối (dispatch map).

```python
TOOL_HANDLERS = {
    # ...các công cụ cơ bản...
    "task_create": lambda **kw: TASKS.create(kw["subject"]),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status")),
    "task_list":   lambda **kw: TASKS.list_all(),
    "task_get":    lambda **kw: TASKS.get(kw["task_id"]),
}
```

Từ s07 trở đi, đồ thị tác vụ là mặc định cho các công việc nhiều bước. Todo của s03 vẫn được giữ lại cho các danh sách kiểm tra nhanh trong một phiên làm việc duy nhất.

## Những thay đổi so với s06

| Thành phần     | Trước (s06)      | Sau (s07)                  |
|----------------|------------------|----------------------------|
| Công cụ        | 5                | 8 (`task_create/update/list/get`) |
| Mô hình lập kế hoạch | Danh sách phẳng (trong bộ nhớ) | Đồ thị tác vụ với các phụ thuộc (trên đĩa) |
| Mối quan hệ    | Không            | Các cạnh `blockedBy`       |
| Theo dõi trạng thái | Xong hoặc chưa | `pending` -> `in_progress` -> `completed` |
| Lưu trữ bền vững | Mất khi nén      | Tồn tại qua việc nén và khởi động lại |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s07_task_system.py
```

1. `Tạo 3 tác vụ: "Setup project", "Write code", "Write tests". Thiết lập chúng phụ thuộc lẫn nhau theo thứ tự.`
2. `Liệt kê tất cả các tác vụ và hiển thị đồ thị phụ thuộc`
3. `Hoàn thành tác vụ 1 và sau đó liệt kê các tác vụ để xem tác vụ 2 được gỡ chặn`
4. `Tạo một bảng tác vụ để tái cấu trúc mã (refactoring): parse -> transform -> emit -> test, trong đó transform và emit có thể chạy song song sau bước parse`
