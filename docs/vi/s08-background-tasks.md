# s08: Tác vụ chạy nền (Background Tasks)

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > [ s08 ] s09 > s10 > s11 > s12`

> *"Chạy các hoạt động chậm ở chế độ nền; agent tiếp tục suy nghĩ"* -- các luồng daemon chạy lệnh, đưa thông báo vào khi hoàn thành.
>
> **Lớp điều khiển (Harness layer)**: Thực thi nền -- mô hình suy nghĩ trong khi lớp điều khiển chờ đợi.

## Vấn đề

Một số lệnh tốn hàng phút để hoàn thành: `npm install`, `pytest`, `docker build`. Với một vòng lặp chặn (blocking loop), mô hình sẽ ngồi không để chờ đợi. Nếu người dùng yêu cầu "cài đặt các phụ thuộc và trong khi nó đang chạy, hãy tạo tệp cấu hình," agent sẽ thực hiện chúng một cách tuần tự chứ không phải song song.

## Giải pháp

```
Luồng chính (Main thread)      Luồng nền (Background thread)
+-----------------+           +-----------------+
| vòng lặp agent  |           | tiến trình con  |
| ...             |           | ...             |
| [gọi LLM] <----+----------  | enqueue(kết quả)|
| ^lấy thông báo  |           +-----------------+
+-----------------+

Dòng thời gian:
Agent --[tạo A]--[tạo B]--[việc khác]----
           |        |
           v        v
        [A chạy] [B chạy]      (song song)
           |        |
           +-- kết quả được đưa vào trước lần gọi LLM tiếp theo --+
```

## Cách thức hoạt động

1. **BackgroundManager** theo dõi các tác vụ với một hàng đợi thông báo an toàn luồng (thread-safe).

```python
class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self._notification_queue = []
        self._lock = threading.Lock()
```

2. `run()` khởi chạy một luồng daemon và trả về kết quả ngay lập tức.

```python
def run(self, command: str) -> str:
    task_id = str(uuid.uuid4())[:8]
    self.tasks[task_id] = {"status": "running", "command": command}
    thread = threading.Thread(
        target=self._execute, args=(task_id, command), daemon=True)
    thread.start()
    return f"Tác vụ nền {task_id} đã bắt đầu"
```

3. Khi tiến trình con kết thúc, kết quả của nó được đưa vào hàng đợi thông báo.

```python
def _execute(self, task_id, command):
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
            capture_output=True, text=True, timeout=300)
        output = (r.stdout + r.stderr).strip()[:50000]
    except subprocess.TimeoutExpired:
        output = "Lỗi: Quá thời gian (300s)"
    with self._lock:
        self._notification_queue.append({
            "task_id": task_id, "result": output[:500]})
```

4. Vòng lặp agent lấy hết các thông báo trước mỗi lần gọi LLM.

```python
def agent_loop(messages: list):
    while True:
        notifs = BG.drain_notifications()
        if notifs:
            notif_text = "\n".join(
                f"[bg:{n['task_id']}] {n['result']}" for n in notifs)
            messages.append({"role": "user",
                "content": f"<background-results>\n{notif_text}\n"
                           f"</background-results>"})
        response = client.messages.create(...)
```

Vòng lặp vẫn duy trì đơn luồng. Chỉ có I/O của tiến trình con là được song song hóa.

## Những thay đổi so với s07

| Thành phần     | Trước (s07)      | Sau (s08)                  |
|----------------|------------------|----------------------------|
| Công cụ        | 8                | 6 (cơ bản + background_run + check)|
| Thực thi       | Chỉ chặn (blocking) | Chặn + luồng nền           |
| Thông báo      | Không            | Hàng đợi được làm trống mỗi vòng lặp|
| Tính đồng thời | Không            | Luồng daemon               |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s08_background_tasks.py
```

1. `Chạy "sleep 5 && echo done" ở chế độ nền, sau đó tạo một tệp trong khi nó đang chạy`
2. `Khởi chạy 3 tác vụ nền: "sleep 2", "sleep 4", "sleep 6". Kiểm tra trạng thái của chúng.`
3. `Chạy pytest ở chế độ nền và tiếp tục làm việc với các việc khác`
