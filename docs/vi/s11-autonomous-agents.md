# s11: Agent Tự chủ

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > [ s11 ] s12`

> *"Các đồng đội tự quét bảng và nhận nhiệm vụ"* -- không cần lead phải giao từng cái một.
>
> **Lớp Harness**: Tính tự chủ (Autonomy) -- các mô hình tự tìm việc mà không cần được bảo.

## Vấn đề

Trong s09-s10, các đồng đội chỉ làm việc khi được bảo rõ ràng. Lead phải tạo từng người với một yêu cầu cụ thể. Có 10 nhiệm vụ chưa được nhận trên bảng? Lead phải giao từng cái một cách thủ công. Điều này không thể mở rộng (scale).

Tính tự chủ thực sự: các đồng đội tự quét bảng nhiệm vụ, nhận các nhiệm vụ chưa có người làm, thực hiện chúng, sau đó tìm kiếm thêm.

Một chi tiết nhỏ: sau khi nén ngữ cảnh (s06), agent có thể quên mình là ai. Việc tái chèn định danh (Identity re-injection) sẽ khắc phục điều này.

## Giải pháp

```
Vòng đời đồng đội với chu kỳ rảnh rỗi (idle cycle):

+-------+
| tạo   | (spawn)
+---+---+
    |
    v
+-------+   sử dụng công cụ  +-------+
|  LÀM  | <----------------- |  LLM  |
+---+---+                    +-------+
    |
    | stop_reason != tool_use (hoặc công cụ idle được gọi)
    v
+--------+
| RẢNH   |  kiểm tra mỗi 5 giây trong tối đa 60 giây
+---+----+
    |
    +---> kiểm tra inbox --> có tin nhắn? ----------> LÀM
    |
    +---> quét .tasks/ --> có task chưa nhận? ------> nhận -> LÀM
    |
    +---> hết 60 giây ------------------------------> TẮT MÁY
                                                     (SHUTDOWN)

Tái chèn định danh sau khi nén:
  nếu số lượng tin nhắn <= 3:
    chèn khối định danh (identity_block) vào đầu danh sách
```

## Cách hoạt động

1. Vòng lặp đồng đội có hai giai đoạn: LÀM (WORK) và RẢNH (IDLE). Khi LLM ngừng gọi các công cụ (hoặc gọi `idle`), đồng đội sẽ chuyển sang trạng thái RẢNH.

```python
def _loop(self, name, role, prompt):
    while True:
        # -- GIAI ĐOẠN LÀM VIỆC --
        messages = [{"role": "user", "content": prompt}]
        for _ in range(50):
            response = client.messages.create(...)
            if response.stop_reason != "tool_use":
                break
            # thực thi công cụ...
            if idle_requested:
                break

        # -- GIAI ĐOẠN RẢNH RỖI --
        self._set_status(name, "idle")
        resume = self._idle_poll(name, messages)
        if not resume:
            self._set_status(name, "shutdown")
            return
        self._set_status(name, "working")
```

2. Giai đoạn rảnh rỗi thăm dò hộp thư đến và bảng nhiệm vụ trong một vòng lặp.

```python
def _idle_poll(self, name, messages):
    for _ in range(IDLE_TIMEOUT // POLL_INTERVAL):  # 60s / 5s = 12
        time.sleep(POLL_INTERVAL)
        inbox = BUS.read_inbox(name)
        if inbox:
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
            return True
        unclaimed = scan_unclaimed_tasks()
        if unclaimed:
            claim_task(unclaimed[0]["id"], name)
            messages.append({"role": "user",
                "content": f"<auto-claimed>Task #{unclaimed[0]['id']}: "
                           f"{unclaimed[0]['subject']}</auto-claimed>"})
            return True
    return False  # hết hạn -> tắt máy
```

3. Quét bảng nhiệm vụ: tìm các nhiệm vụ đang chờ, chưa có chủ sở hữu, không bị chặn.

```python
def scan_unclaimed_tasks() -> list:
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        task = json.loads(f.read_text())
        if (task.get("status") == "pending"
                and not task.get("owner")
                and not task.get("blockedBy")):
            unclaimed.append(task)
    return unclaimed
```

4. Tái chèn định danh: khi ngữ cảnh quá ngắn (đã xảy ra quá trình nén), hãy chèn một khối định danh.

```python
if len(messages) <= 3:
    messages.insert(0, {"role": "user",
        "content": f"<identity>Bạn là '{name}', vai trò: {role}, "
                   f"nhóm: {team_name}. Tiếp tục công việc của bạn.</identity>"})
    messages.insert(1, {"role": "assistant",
        "content": f"Tôi là {name}. Đang tiếp tục."})
```

## Có gì thay đổi so với s10

| Thành phần        | Trước (s10)      | Sau (s11)                      |
|-------------------|------------------|--------------------------------|
| Công cụ           | 12               | 14 (+idle, +claim_task)        |
| Tính tự chủ       | Lead chỉ đạo     | Tự tổ chức                     |
| Giai đoạn rảnh    | Không có         | Thăm dò inbox + bảng nhiệm vụ  |
| Nhận nhiệm vụ     | Chỉ thủ công     | Tự động nhận task chưa có chủ  |
| Định danh         | System prompt    | + tái chèn sau khi nén         |
| Hết hạn (Timeout) | Không có         | Rảnh 60 giây -> tự động tắt    |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s11_autonomous_agents.py
```

1. `Create 3 tasks on the board, then spawn alice and bob. Watch them auto-claim.` (Tạo 3 nhiệm vụ trên bảng, sau đó tạo alice và bob. Xem họ tự động nhận việc.)
2. `Spawn a coder teammate and let it find work from the task board itself` (Tạo một đồng đội coder và để nó tự tìm việc từ bảng nhiệm vụ)
3. `Create tasks with dependencies. Watch teammates respect the blocked order.` (Tạo các nhiệm vụ có sự phụ thuộc. Xem các đồng đội tuân thủ thứ tự bị chặn.)
4. Gõ `/tasks` để xem bảng nhiệm vụ với những người sở hữu
5. Gõ `/team` để theo dõi ai đang làm việc so với ai đang rảnh
