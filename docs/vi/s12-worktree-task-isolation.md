# s12: Worktree + Cô lập Nhiệm vụ

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > [ s12 ]`

> *"Mỗi người làm việc trong thư mục riêng của mình, không có sự can thiệp"* -- các nhiệm vụ quản lý mục tiêu, các worktree quản lý thư mục, được liên kết bởi ID.
>
> **Lớp Harness**: Cô lập thư mục -- các luồng thực thi song song không bao giờ xung đột.

## Vấn đề

Đến s11, các agent có thể tự động nhận và hoàn thành nhiệm vụ. Nhưng mọi nhiệm vụ đều chạy trong một thư mục chung. Hai agent tái cấu trúc các mô-đun khác nhau cùng một lúc sẽ bị xung đột: agent A sửa `config.py`, agent B sửa `config.py`, các thay đổi chưa được stage bị trộn lẫn và không ai có thể hoàn tác một cách sạch sẽ.

Bảng nhiệm vụ theo dõi *việc cần làm* nhưng không có ý kiến về *nơi thực hiện*. Giải pháp: cung cấp cho mỗi nhiệm vụ một thư mục git worktree riêng. Nhiệm vụ quản lý mục tiêu, worktree quản lý ngữ cảnh thực thi. Liên kết chúng bằng ID nhiệm vụ.

## Giải pháp

```
Mặt phẳng điều khiển (.tasks/)         Mặt phẳng thực thi (.worktrees/)
+-------------------+                +------------------------+
| task_1.json       |                | auth-refactor/         |
|   status: in_progress  <------>   |   branch: wt/auth-refactor
|   worktree: "auth-refactor"   |    |   task_id: 1           |
+-------------------+                +------------------------+
| task_2.json       |                | ui-login/              |
|   status: pending     <------>    |   branch: wt/ui-login  |
|   worktree: "ui-login"        |    |   task_id: 2           |
+-------------------+                +------------------------+
                                     |
                           index.json (sổ đăng ký worktree)
                           events.jsonl (nhật ký vòng đời)

Máy trạng thái:
  Nhiệm vụ (Task):  pending -> in_progress -> completed
  Worktree:         absent  -> active      -> removed | kept
```

## Cách hoạt động

1. **Tạo một nhiệm vụ.** Lưu giữ mục tiêu trước.

```python
TASKS.create("Triển khai tái cấu trúc xác thực")
# -> .tasks/task_1.json  status=pending  worktree=""
```

2. **Tạo một worktree và liên kết với nhiệm vụ.** Việc truyền `task_id` sẽ tự động chuyển nhiệm vụ sang trạng thái `in_progress`.

```python
WORKTREES.create("auth-refactor", task_id=1)
# -> git worktree add -b wt/auth-refactor .worktrees/auth-refactor HEAD
# -> index.json nhận mục mới, task_1.json nhận worktree="auth-refactor"
```

Việc liên kết ghi trạng thái vào cả hai phía:

```python
def bind_worktree(self, task_id, worktree):
    task = self._load(task_id)
    task["worktree"] = worktree
    if task["status"] == "pending":
        task["status"] = "in_progress"
    self._save(task)
```

3. **Chạy các lệnh trong worktree.** `cwd` trỏ đến thư mục bị cô lập.

```python
# cwd (current working directory) trỏ đến đường dẫn worktree
subprocess.run(command, shell=True, cwd=worktree_path,
               capture_output=True, text=True, timeout=300)
```

4. **Kết thúc.** Hai lựa chọn:
   - `worktree_keep(name)` -- giữ lại thư mục để dùng sau.
   - `worktree_remove(name, complete_task=True)` -- xóa thư mục, hoàn thành nhiệm vụ được liên kết, phát ra sự kiện. Một lệnh duy nhất xử lý việc thu dọn + hoàn thành.

```python
def remove(self, name, force=False, complete_task=False):
    self._run_git(["worktree", "remove", wt["path"]])
    if complete_task and wt.get("task_id") is not None:
        self.tasks.update(wt["task_id"], status="completed")
        self.tasks.unbind_worktree(wt["task_id"])
        self.events.emit("task.completed", ...)
```

5. **Luồng sự kiện (Event stream).** Mọi bước trong vòng đời đều được ghi vào `.worktrees/events.jsonl`:

```json
{
  "event": "worktree.remove.after",
  "task": {"id": 1, "status": "completed"},
  "worktree": {"name": "auth-refactor", "status": "removed"},
  "ts": 1730000000
}
```

Các sự kiện được phát ra: `worktree.create.before/after/failed`, `worktree.remove.before/after/failed`, `worktree.keep`, `task.completed`.

Sau khi gặp sự cố (crash), trạng thái được tái cấu trúc từ `.tasks/` + `.worktrees/index.json` trên ổ đĩa. Bộ nhớ hội thoại là tạm thời (volatile); trạng thái tệp là bền vững (durable).

## Có gì thay đổi so với s11

| Thành phần           | Trước (s11)               | Sau (s12)                                    |
|----------------------|---------------------------|----------------------------------------------|
| Sự điều phối         | Bảng task (chủ sở hữu/trạng thái) | Bảng task + liên kết worktree rõ ràng        |
| Phạm vi thực thi     | Thư mục chung             | Thư mục cô lập theo phạm vi nhiệm vụ         |
| Khả năng khôi phục   | Chỉ trạng thái nhiệm vụ   | Trạng thái nhiệm vụ + chỉ mục worktree       |
| Thu dọn (Teardown)   | Hoàn thành nhiệm vụ       | Hoàn thành nhiệm vụ + giữ/xóa rõ ràng        |
| Khả năng quan sát vòng đời | Ngầm định trong log | Các sự kiện rõ ràng trong `.worktrees/events.jsonl` |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s12_worktree_task_isolation.py
```

1. `Create tasks for backend auth and frontend login page, then list tasks.` (Tạo các nhiệm vụ cho backend auth và trang login frontend, sau đó liệt kê các nhiệm vụ.)
2. `Create worktree "auth-refactor" for task 1, then bind task 2 to a new worktree "ui-login".` (Tạo worktree "auth-refactor" cho nhiệm vụ 1, sau đó liên kết nhiệm vụ 2 với một worktree "ui-login" mới.)
3. `Run "git status --short" in worktree "auth-refactor".` (Chạy "git status --short" trong worktree "auth-refactor".)
4. `Keep worktree "ui-login", then list worktrees and inspect events.` (Giữ worktree "ui-login", sau đó liệt kê các worktree và kiểm tra các sự kiện.)
5. `Remove worktree "auth-refactor" with complete_task=true, then list tasks/worktrees/events.` (Xóa worktree "auth-refactor" với complete_task=true, sau đó liệt kê các task/worktree/sự kiện.)
