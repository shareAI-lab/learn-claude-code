# Hệ thống quyền (Permission System)

> *Ý định của model phải đi qua safety gate trước khi thành hành động thật.*

## Vấn Đề

Model có thể yêu cầu command nguy hiểm: xóa file, ghi đè cấu hình, chạy network call, sửa ngoài workspace. Harness không nên thực thi mù quáng.

Permission system biến raw tool intent thành decision rõ ràng.

## Pipeline

```text
tool intent
  -> hard deny rules
  -> mode check
  -> allow rules
  -> ask user if needed
  -> execute or return denial
```

Safety không phải boolean đơn. Nó là pipeline có thứ tự.

## Decision

`PermissionDecision` nên ghi:

- action
- target
- risk
- decision: allow, deny, ask
- reason
- optional user response

Decision này nên quay lại loop nếu nó ảnh hưởng kế hoạch. Deny cũng là observation.

## Ví Dụ

```text
intent: delete build/
risk: destructive filesystem mutation
mode: ask
decision: ask user
```

Nếu user deny, model cần thấy result để đề xuất cách an toàn hơn.

## Ranh Giới

Permission không nên nằm rải trong từng tool handler. Tool handler thực thi action; permission gate quyết định action có được tới handler không.

## Bài Tập Tối Thiểu

- tạo `PermissionRule`
- classify action risk
- deny một số pattern nguy hiểm
- allow read-only action
- ask user với mutation rủi ro
- append decision/result lại cho model

Sau chương này, agent không còn biến mọi model intent thành execution trực tiếp.
