# s10: Giao thức Nhóm

`s01 > s02 > s03 > s04 > s05 > s06 | s07 > s08 > s09 > [ s10 ] s11 > s12`

> *"Các đồng đội cần các quy tắc giao tiếp chung"* -- một mô hình yêu cầu-phản hồi duy nhất thúc đẩy tất cả các cuộc thương lượng.
>
> **Lớp Harness**: Giao thức (Protocols) -- các lần bắt tay (handshakes) có cấu trúc giữa các mô hình.

## Vấn đề

Trong s09, các đồng đội làm việc và giao tiếp nhưng thiếu sự điều phối có cấu trúc:

**Tắt máy (Shutdown)**: Việc dừng một luồng (thread) đột ngột khiến các tệp chỉ được ghi một nửa và `config.json` bị lỗi. Bạn cần một cái bắt tay: lead yêu cầu, đồng đội chấp thuận (hoàn tất và thoát) hoặc từ chối (tiếp tục làm việc).

**Phê duyệt kế hoạch (Plan approval)**: Khi lead nói "tái cấu trúc mô-đun xác thực," đồng đội bắt đầu ngay lập tức. Đối với các thay đổi có rủi ro cao, lead nên xem xét kế hoạch trước.

Cả hai đều chia sẻ cùng một cấu trúc: một bên gửi yêu cầu với một ID duy nhất, bên kia phản hồi có tham chiếu đến ID đó.

## Giải pháp

```
Giao thức Tắt máy            Giao thức Phê duyệt Kế hoạch
==================           ============================

Lead             Đồng đội    Đồng đội           Lead
  |                 |           |                 |
  |--shutdown_req-->|           |--plan_req------>|
  | {req_id:"abc"}  |           | {req_id:"xyz"}  |
  |                 |           |                 |
  |<--shutdown_resp-|           |<--plan_resp-----|
  | {req_id:"abc",  |           | {req_id:"xyz",  |
  |  approve:true}  |           |  approve:true}  |

FSM chung:
  [pending] --approve--> [approved]
  [pending] --reject---> [rejected]

Trình theo dõi (Trackers):
  shutdown_requests = {req_id: {target, status}}
  plan_requests     = {req_id: {from, plan, status}}
```

## Cách hoạt động

1. Lead bắt đầu tắt máy bằng cách tạo một `request_id` và gửi qua hộp thư đến (inbox).

```python
shutdown_requests = {}

def handle_shutdown_request(teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    BUS.send("lead", teammate, "Vui lòng tắt máy một cách an toàn.",
             "shutdown_request", {"request_id": req_id})
    return f"Yêu cầu tắt máy {req_id} đã được gửi (trạng thái: pending)"
```

2. Đồng đội nhận yêu cầu và phản hồi bằng approve/reject.

```python
if tool_name == "shutdown_response":
    req_id = args["request_id"]
    approve = args["approve"]
    shutdown_requests[req_id]["status"] = "approved" if approve else "rejected"
    BUS.send(sender, "lead", args.get("reason", ""),
             "shutdown_response",
             {"request_id": req_id, "approve": approve})
```

3. Phê duyệt kế hoạch tuân theo mô hình tương tự. Đồng đội gửi một kế hoạch (tạo một `request_id`), lead xem xét (tham chiếu đến cùng một `request_id`).

```python
plan_requests = {}

def handle_plan_review(request_id, approve, feedback=""):
    req = plan_requests[request_id]
    req["status"] = "approved" if approve else "rejected"
    BUS.send("lead", req["from"], feedback,
             "plan_approval_response",
             {"request_id": request_id, "approve": approve})
```

Một FSM, hai ứng dụng. Cùng một máy trạng thái `pending -> approved | rejected` xử lý bất kỳ giao thức yêu cầu-phản hồi nào.

## Có gì thay đổi so với s09

| Thành phần     | Trước (s09)      | Sau (s10)                      |
|----------------|------------------|--------------------------------|
| Công cụ        | 9                | 12 (+shutdown_req/resp +plan)  |
| Tắt máy        | Chỉ thoát tự nhiên | Bắt tay yêu cầu-phản hồi       |
| Chốt kế hoạch  | Không có         | Gửi/xem xét với sự phê duyệt   |
| Sự tương quan  | Không có         | request_id cho mỗi yêu cầu     |
| FSM            | Không có         | pending -> approved/rejected   |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s10_team_protocols.py
```

1. `Spawn alice as a coder. Then request her shutdown.` (Tạo alice làm coder. Sau đó yêu cầu cô ấy tắt máy.)
2. `List teammates to see alice's status after shutdown approval` (Liệt kê đồng đội để xem trạng thái của alice sau khi phê duyệt tắt máy)
3. `Spawn bob with a risky refactoring task. Review and reject his plan.` (Tạo bob với nhiệm vụ tái cấu trúc rủi ro. Xem xét và từ chối kế hoạch của anh ấy.)
4. `Spawn charlie, have him submit a plan, then approve it.` (Tạo charlie, yêu cầu anh ấy gửi kế hoạch, sau đó phê duyệt nó.)
5. Gõ `/team` để theo dõi các trạng thái
