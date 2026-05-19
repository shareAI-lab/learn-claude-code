# s09: Nhóm Agent (Agent Teams)

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > [ s09 ] s10 > s11 > s12`

> *"Khi một tác vụ quá lớn đối với một người, hãy giao phó cho đồng đội"* -- đồng đội bền vững + hộp thư bất đồng bộ.
>
> **Lớp điều khiển (Harness layer)**: Hộp thư nhóm -- nhiều mô hình, được điều phối thông qua các tệp tin.

## Vấn đề

Các subagent (s04) mang tính chất dùng một lần: khởi tạo, làm việc, trả về bản tóm tắt, rồi kết thúc. Chúng không có danh tính, không có bộ nhớ giữa các lần gọi. Các tác vụ chạy nền (s08) chạy các lệnh shell nhưng không thể đưa ra các quyết định dựa trên hướng dẫn của LLM.

Làm việc nhóm thực sự cần: (1) các agent bền vững tồn tại lâu hơn một lời nhắc (prompt) duy nhất, (2) quản lý danh tính và vòng đời, (3) một kênh giao tiếp giữa các agent.

## Giải pháp

```
Vòng đời đồng đội:
  spawn -> ĐANG LÀM VIỆC -> ĐANG RẢNH -> ĐANG LÀM VIỆC -> ... -> TẮT

Giao tiếp:
  .team/
    config.json           <- danh sách thành viên + trạng thái
    inbox/
      alice.jsonl         <- chỉ thêm (append-only), làm trống khi đọc
      bob.jsonl
      lead.jsonl

              +--------+    send("alice","bob","...")    +--------+
              | alice  | -----------------------------> |  bob   |
              | loop   |    bob.jsonl << {json_line}    |  loop  |
              +--------+                                +--------+
                   ^                                         |
                   |        BUS.read_inbox("alice")          |
                   +---- alice.jsonl -> đọc + làm trống -----+
```

## Cách thức hoạt động

1. **TeammateManager** duy trì tệp `config.json` với danh sách thành viên nhóm.

```python
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}
```

2. `spawn()` tạo ra một đồng đội và khởi chạy vòng lặp agent của nó trong một luồng riêng.

```python
def spawn(self, name: str, role: str, prompt: str) -> str:
    member = {"name": name, "role": role, "status": "working"}
    self.config["members"].append(member)
    self._save_config()
    thread = threading.Thread(
        target=self._teammate_loop,
        args=(name, role, prompt), daemon=True)
    thread.start()
    return f"Đã khởi tạo đồng đội '{name}' (vai trò: {role})"
```

3. **MessageBus**: các hộp thư JSONL dạng chỉ thêm. `send()` thêm một dòng JSON; `read_inbox()` đọc tất cả và làm trống tệp.

```python
class MessageBus:
    def send(self, sender, to, content, msg_type="message", extra=None):
        msg = {"type": msg_type, "from": sender,
               "content": content, "timestamp": time.time()}
        if extra:
            msg.update(extra)
        with open(self.dir / f"{to}.jsonl", "a") as f:
            f.write(json.dumps(msg) + "\n")

    def read_inbox(self, name):
        path = self.dir / f"{name}.jsonl"
        if not path.exists(): return "[]"
        msgs = [json.loads(l) for l in path.read_text().strip().splitlines() if l]
        path.write_text("")  # làm trống (drain)
        return json.dumps(msgs, indent=2)
```

4. Mỗi đồng đội kiểm tra hộp thư của mình trước mỗi lần gọi LLM, đưa các tin nhắn nhận được vào ngữ cảnh.

```python
def _teammate_loop(self, name, role, prompt):
    messages = [{"role": "user", "content": prompt}]
    for _ in range(50):
        inbox = BUS.read_inbox(name)
        if inbox != "[]":
            messages.append({"role": "user",
                "content": f"<inbox>{inbox}</inbox>"})
        response = client.messages.create(...)
        if response.stop_reason != "tool_use":
            break
        # thực thi công cụ, thêm kết quả...
    self._find_member(name)["status"] = "idle"
```

## Những thay đổi so với s08

| Thành phần     | Trước (s08)      | Sau (s09)                  |
|----------------|------------------|----------------------------|
| Công cụ        | 6                | 9 (+spawn/send/read_inbox) |
| Agent          | Đơn lẻ           | Lead + N đồng đội          |
| Lưu trữ bền vững | Không          | config.json + hộp thư JSONL|
| Luồng          | Lệnh chạy nền    | Vòng lặp agent đầy đủ mỗi luồng|
| Vòng đời       | Gọi và quên      | idle -> working -> idle    |
| Giao tiếp      | Không            | message + broadcast        |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s09_agent_teams.py
```

1. `Khởi tạo alice (lập trình viên) và bob (kiểm thử viên). Yêu cầu alice gửi cho bob một tin nhắn.`
2. `Phát tin (broadcast) "status update: phase 1 complete" tới tất cả đồng đội`
3. `Kiểm tra hộp thư của lead để xem có tin nhắn nào không`
4. Gõ `/team` để xem danh sách thành viên nhóm cùng trạng thái của họ
5. Gõ `/inbox` để kiểm tra hộp thư của lead một cách thủ công
